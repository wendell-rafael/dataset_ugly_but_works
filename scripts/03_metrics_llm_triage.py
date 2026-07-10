#!/usr/bin/env python3
"""Fase 1 — Métricas de concordância inter-anotadores e pré-triagem LLM.

Implementa dois pedaços independentes do plano:

1. Seção 5.5 — Métricas de concordância: Cohen's Kappa e Gwet's AC1,
   calculados separadamente para a tarefa binária `is_ubw` e para a
   classificação de categoria (restrita aos verdadeiros positivos),
   quebrados por tipo de artefato.

2. Seção 5.6 — Pré-triagem por LLM: classifica candidatos coletados como
   `UBW-verdadeiro` / `não-UBW` / `incerto` antes da anotação humana, com
   as regras de roteamento definidas no plano (itens `incerto` sempre vão
   para anotação humana; 15% dos demais também).

Também inclui um utilitário de amostragem estratificada (Seção 5.2, ~385
itens) usado para gerar a amostra que alimenta a validação manual.

Subcomandos:
    sample       gera a amostra estratificada para validação manual
    llm-triage   roda a pré-triagem LLM sobre os candidatos coletados
    metrics      calcula kappa e AC1 a partir de um CSV de anotações

Exemplos:
    python 03_metrics_llm_triage.py sample \
        --candidates ../data/ubw_collected_full.csv --n 385 \
        --out ../data/manual_validation_sample.csv

    python 03_metrics_llm_triage.py llm-triage \
        --candidates ../data/ubw_collected_full.csv \
        --out ../data/llm_triage_results.csv

    python 03_metrics_llm_triage.py metrics \
        --annotations ../data/annotations_long.csv \
        --out ../data/agreement_report.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import random
import sys
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402

from ubw.envutil import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ubw.metrics_llm")

LANDIS_KOCH_MIN_ACCEPTABLE_KAPPA = 0.61  # Seção 5.5
LLM_HUMAN_AUDIT_SAMPLE_RATIO = 0.15  # Seção 5.6
LLM_KAPPA_DISCARD_THRESHOLD = 0.61  # Seção 5.6

RANDOM_SEED = 42  # reprodutibilidade da amostragem (Seção 3.4)


# =============================================================================
# 1. Métricas de concordância (Seção 5.5): Cohen's Kappa e Gwet's AC1
# =============================================================================

def cohens_kappa(ratings_a: list, ratings_b: list) -> float:
    """Cohen's Kappa para dois anotadores (Landis & Koch, 1977).

    kappa = (p_o - p_e) / (1 - p_e), onde p_o é a proporção observada de
    concordância e p_e é a concordância esperada ao acaso, calculada a
    partir das distribuições marginais de cada anotador.
    """
    if len(ratings_a) != len(ratings_b):
        raise ValueError("As duas listas de rótulos devem ter o mesmo tamanho.")
    n = len(ratings_a)
    if n == 0:
        return float("nan")

    categories = sorted(set(ratings_a) | set(ratings_b))
    if len(categories) < 2:
        return 1.0  # sem variabilidade -> concordância trivial e completa

    po = sum(1 for a, b in zip(ratings_a, ratings_b) if a == b) / n

    count_a = {c: ratings_a.count(c) for c in categories}
    count_b = {c: ratings_b.count(c) for c in categories}
    pe = sum((count_a[c] / n) * (count_b[c] / n) for c in categories)

    if pe == 1.0:
        return 1.0
    return (po - pe) / (1 - pe)


def gwets_ac1(ratings_a: list, ratings_b: list) -> float:
    """Gwet's AC1 (Gwet, 2008), robusto ao "paradoxo do kappa" em classes
    desbalanceadas (Wongpakaran et al., 2013).

    AC1 = (p_o - pi_e) / (1 - pi_e), onde
        pi_e = 1/(q-1) * sum_k[ pi_k * (1 - pi_k) ]
    e pi_k é a proporção média de uso da categoria k pelos dois anotadores
    (em vez do produto das marginais, como no kappa clássico).
    """
    if len(ratings_a) != len(ratings_b):
        raise ValueError("As duas listas de rótulos devem ter o mesmo tamanho.")
    n = len(ratings_a)
    if n == 0:
        return float("nan")

    categories = sorted(set(ratings_a) | set(ratings_b))
    q = len(categories)
    if q < 2:
        return 1.0

    po = sum(1 for a, b in zip(ratings_a, ratings_b) if a == b) / n

    count_a = {c: ratings_a.count(c) for c in categories}
    count_b = {c: ratings_b.count(c) for c in categories}
    pi_k = {c: (count_a[c] + count_b[c]) / (2 * n) for c in categories}

    pi_e = sum(pi_k[c] * (1 - pi_k[c]) for c in categories) / (q - 1)

    if pi_e == 1.0:
        return 1.0
    return (po - pi_e) / (1 - pi_e)


def interpret_kappa(value: float) -> str:
    """Escala de Landis & Koch (1977), citada na Seção 5.5."""
    if pd.isna(value):
        return "indefinido"
    if value < 0:
        return "sem concordância"
    if value < 0.20:
        return "leve"
    if value < 0.40:
        return "razoável"
    if value < 0.60:
        return "moderada"
    if value < 0.80:
        return "substancial"
    return "excelente (quase perfeita)"


def _first_two_annotators(df: pd.DataFrame) -> list[str]:
    annotators = sorted(df["annotator_id"].unique())
    if len(annotators) < 2:
        raise ValueError(
            f"São necessários >= 2 anotadores independentes (Seção 5.3); encontrados: {annotators}"
        )
    if len(annotators) > 2:
        logger.info(
            "Encontrados %d anotadores (%s); usando os dois primeiros (%s, %s) como par "
            "primário. O(s) demais são tratados como desempate (Seção 5.3), não entram no kappa.",
            len(annotators), annotators, annotators[0], annotators[1],
        )
    return annotators[:2]


def _pivot_pair(df: pd.DataFrame, item_col: str, value_col: str, annotator_a: str, annotator_b: str) -> pd.DataFrame:
    wide = df.pivot_table(index=item_col, columns="annotator_id", values=value_col, aggfunc="first")
    wide = wide.dropna(subset=[annotator_a, annotator_b])
    return wide[[annotator_a, annotator_b]]


def agreement_report(annotations: pd.DataFrame, item_col: str = "artifact_id") -> pd.DataFrame:
    """Calcula kappa e AC1 para `is_ubw` (todos os itens) e para
    `category_confirmed` (restrito aos verdadeiros positivos, ou seja,
    itens em que AMBOS os anotadores marcaram is_ubw=True), quebrado por
    tipo de artefato e no agregado geral (Seção 5.5 e Entregável #4).
    """
    required_cols = {"artifact_id", "artifact_type", "annotator_id", "is_ubw", "category_confirmed"}
    missing = required_cols - set(annotations.columns)
    if missing:
        raise ValueError(f"CSV de anotações sem as colunas obrigatórias: {sorted(missing)}")

    annotator_a, annotator_b = _first_two_annotators(annotations)
    rows = []

    def _add_row(scope: str, task: str, wide: pd.DataFrame) -> None:
        if wide.empty:
            rows.append({"scope": scope, "task": task, "n_items": 0, "kappa": float("nan"),
                         "kappa_interpretation": "sem dados", "gwet_ac1": float("nan")})
            return
        a = wide[annotator_a].tolist()
        b = wide[annotator_b].tolist()
        k = cohens_kappa(a, b)
        ac1 = gwets_ac1(a, b)
        rows.append({
            "scope": scope, "task": task, "n_items": len(wide),
            "kappa": round(k, 4), "kappa_interpretation": interpret_kappa(k),
            "gwet_ac1": round(ac1, 4),
        })

    # -- is_ubw: geral + por tipo de artefato -----------------------------
    wide_ubw = _pivot_pair(annotations, item_col, "is_ubw", annotator_a, annotator_b)
    _add_row("geral", "is_ubw", wide_ubw)

    for artifact_type, group in annotations.groupby("artifact_type"):
        wide = _pivot_pair(group, item_col, "is_ubw", annotator_a, annotator_b)
        _add_row(artifact_type, "is_ubw", wide)

    # -- category_confirmed: restrito aos verdadeiros positivos -----------
    both_true_ids = wide_ubw[(wide_ubw[annotator_a] == True) & (wide_ubw[annotator_b] == True)].index  # noqa: E712
    tp_annotations = annotations[annotations[item_col].isin(both_true_ids)]

    wide_cat = _pivot_pair(tp_annotations, item_col, "category_confirmed", annotator_a, annotator_b)
    _add_row("geral", "category_confirmed (TP)", wide_cat)

    for artifact_type, group in tp_annotations.groupby("artifact_type"):
        wide = _pivot_pair(group, item_col, "category_confirmed", annotator_a, annotator_b)
        _add_row(artifact_type, "category_confirmed (TP)", wide)

    report = pd.DataFrame(rows)

    below_threshold = report[(report["task"] == "category_confirmed (TP)") & (report["scope"] == "geral")
                              & (report["kappa"] < LANDIS_KOCH_MIN_ACCEPTABLE_KAPPA)]
    if not below_threshold.empty:
        logger.warning(
            "Kappa geral de category_confirmed abaixo de %.2f (Landis & Koch, 1977). "
            "Seção 5.5: 'Se esse kappa vier baixo, a contribuição central do estudo "
            "fica fragilizada.' Revisar a taxonomia A/B/C ou o guideline de anotação.",
            LANDIS_KOCH_MIN_ACCEPTABLE_KAPPA,
        )

    return report


# =============================================================================
# 2. Amostragem estratificada para validação manual (Seção 5.2)
# =============================================================================

def stratified_sample(
    candidates: pd.DataFrame,
    total_n: int = 385,
    strata_cols: tuple[str, ...] = ("category_ubw", "artifact_type"),
    seed: int = RANDOM_SEED,
) -> pd.DataFrame:
    """Amostra estratificada por categoria e tipo de artefato.

    total_n=385 é o tamanho padrão para 95% de confiança / 5% de margem de
    erro em populações > 5000 (Seção 5.2; Bavota & Russo, 2016; Pham et
    al., 2025). A alocação é proporcional ao tamanho de cada estrato,
    com um mínimo de 1 item por estrato não-vazio.
    """
    rng = random.Random(seed)
    n_total = len(candidates)
    if n_total == 0:
        return candidates.copy()

    strata = candidates.groupby(list(strata_cols), dropna=False)
    allocations = {}
    remaining = total_n
    strata_sizes = {key: len(group) for key, group in strata}

    for key, size in strata_sizes.items():
        share = round(total_n * size / n_total)
        allocations[key] = max(1, min(share, size))

    # Ajusta para não estourar/faltar por causa de arredondamento.
    diff = total_n - sum(allocations.values())
    keys_by_size = sorted(strata_sizes, key=lambda k: -strata_sizes[k])
    idx = 0
    while diff != 0 and keys_by_size:
        key = keys_by_size[idx % len(keys_by_size)]
        if diff > 0 and allocations[key] < strata_sizes[key]:
            allocations[key] += 1
            diff -= 1
        elif diff < 0 and allocations[key] > 1:
            allocations[key] -= 1
            diff += 1
        idx += 1
        if idx > 10_000:  # salvaguarda contra loop infinito em casos degenerados
            break

    sampled_frames = []
    for key, group in strata:
        k = allocations.get(key, 0)
        if k <= 0:
            continue
        indices = list(group.index)
        rng.shuffle(indices)
        sampled_frames.append(group.loc[indices[:k]])

    sample = pd.concat(sampled_frames) if sampled_frames else candidates.iloc[0:0]
    logger.info("Amostra estratificada: %d itens (alvo: %d) em %d estratos.", len(sample), total_n, len(allocations))
    return sample.reset_index(drop=True)


# =============================================================================
# 3. Pré-triagem LLM (Seção 5.6)
# =============================================================================

LLM_TRIAGE_SYSTEM_PROMPT = """Você é um assistente de pesquisa em engenharia de software \
empírica, auxiliando na pré-triagem de candidatos a "Ugly But It Works" (UBW): trechos de \
issues, pull requests, mensagens de commit ou comentários de código em que um(a) \
desenvolvedor(a) admite, de forma explícita, ter aceitado uma solução tecnicamente \
subótima (feia, um workaround, um hack) porque ela funciona.

Você NÃO substitui a anotação humana. Sua tarefa é apenas reduzir o volume de candidatos \
óbvios que precisam de revisão manual, sinalizando os casos ambíguos para revisão \
obrigatória. Erre para o lado de marcar como "incerto" sempre que houver dúvida razoável."""

LLM_TRIAGE_USER_PROMPT_TEMPLATE = """Classifique o candidato abaixo em EXATAMENTE uma das \
três categorias:

- "UBW-verdadeiro": o trecho expressa claramente resignação funcional — a pessoa autora \
  sabe/admite que a solução é feia, um hack ou um workaround, e a manteve porque funciona. \
  O contexto confirma que a expressão-gatilho está sendo usada nesse sentido (não em uma \
  string literal, dado de teste, citação de terceiros ou sentido não-técnico).
- "não-UBW": a expressão-gatilho aparece, mas o contexto NÃO indica resignação funcional \
  (ex.: é parte de uma string de teste, de um nome de variável, de uma citação, de uma \
  negação como "isto NÃO é um hack sujo", ou de um sentido genérico não relacionado a \
  dívida técnica).
- "incerto": não é possível decidir com confiança a partir do contexto disponível — \
  encaminhe para anotação humana.

Contexto do candidato:
- Repositório: {repo_full_name}
- Tipo de artefato: {artifact_type}
- Categoria léxica atribuída automaticamente: {category_ubw}
- Expressão que disparou a coleta: "{matched_expression}"
- Trecho (com contexto, quando aplicável):
\"\"\"
{body_text}
\"\"\"

Responda ESTRITAMENTE em JSON, sem texto fora do JSON, no formato:
{{"label": "UBW-verdadeiro" | "não-UBW" | "incerto", "rationale": "<justificativa em até 2 frases>"}}
"""


def build_llm_triage_prompt(candidate: dict) -> tuple[str, str]:
    """Retorna (system_prompt, user_prompt) para um candidato do schema Tabela 3.5."""
    user_prompt = LLM_TRIAGE_USER_PROMPT_TEMPLATE.format(
        repo_full_name=candidate.get("repo_full_name", ""),
        artifact_type=candidate.get("artifact_type", ""),
        category_ubw=candidate.get("category_ubw", ""),
        matched_expression=candidate.get("matched_expression", ""),
        body_text=(candidate.get("body_text") or "")[:2000],
    )
    return LLM_TRIAGE_SYSTEM_PROMPT, user_prompt


VALID_LLM_LABELS = {"UBW-verdadeiro", "não-UBW", "incerto"}


def _parse_llm_json_label(raw_text: str) -> dict:
    """Faz o parsing tolerante do JSON de rótulo esperado (compartilhado entre
    provedores) e valida o vocabulário. Levanta exceção em qualquer
    inconsistência, para que o chamador aplique o fail-safe "incerto".
    """
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`").lstrip("json").strip()
    parsed = json.loads(raw_text)
    label = parsed.get("label")
    if label not in VALID_LLM_LABELS:
        raise ValueError(f"Label fora do vocabulário esperado: {label!r}")
    return {"label": label, "rationale": parsed.get("rationale", "")}


def classify_candidate_with_anthropic(client, candidate: dict, model: str, max_retries: int = 3) -> dict:
    """Chama a API da Anthropic para classificar um único candidato.

    Retorna {"label": ..., "rationale": ...}. Em caso de resposta
    malformada ou erro persistente, o label cai em "incerto" (fail-safe:
    prefere mandar para revisão humana a descartar silenciosamente).
    """
    system_prompt, user_prompt = build_llm_triage_prompt(candidate)

    for attempt in range(1, max_retries + 1):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=300,
                temperature=0,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return _parse_llm_json_label(response.content[0].text)
        except Exception as exc:  # noqa: BLE001 — qualquer falha aqui deve degradar para "incerto"
            logger.warning("Tentativa %d/%d falhou na triagem LLM (Anthropic): %s", attempt, max_retries, exc)
            time.sleep(2 * attempt)

    logger.error("Triagem LLM esgotou tentativas para artifact_id=%s; marcando como 'incerto'.",
                 candidate.get("artifact_id"))
    return {"label": "incerto", "rationale": "falha técnica na triagem automática"}


# ---------------------------------------------------------------------------
# Backend alternativo: OpenRouter (API compatível com o formato OpenAI Chat
# Completions), para custo mínimo em orçamentos pequenos — ex. DeepSeek via
# OpenRouter custa uma fração de centavo para os ~108 registros do dataset
# final. Não faz parte do plano original; adicionado como opção de execução,
# mantendo a MESMA lógica de fail-safe e roteamento humano (Seção 5.6).
#
# Verifique o slug exato do modelo e o preço atual em https://openrouter.ai/models
# antes de rodar — nomes/preços de modelo mudam com frequência e não são
# rastreados aqui.
# ---------------------------------------------------------------------------

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


def classify_candidate_with_openrouter(candidate: dict, model: str, api_key: str, max_retries: int = 3) -> dict:
    """Mesma tarefa de classify_candidate_with_anthropic, via OpenRouter."""
    import requests

    system_prompt, user_prompt = build_llm_triage_prompt(candidate)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "temperature": 0,
        "max_tokens": 300,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["choices"][0]["message"]["content"]
            return _parse_llm_json_label(raw_text)
        except Exception as exc:  # noqa: BLE001 — mesmo fail-safe do backend Anthropic
            logger.warning("Tentativa %d/%d falhou na triagem LLM (OpenRouter): %s", attempt, max_retries, exc)
            time.sleep(2 * attempt)

    logger.error("Triagem LLM (OpenRouter) esgotou tentativas para artifact_id=%s; marcando como 'incerto'.",
                 candidate.get("artifact_id"))
    return {"label": "incerto", "rationale": "falha técnica na triagem automática"}


def _build_classifier(provider: str, model: str, openrouter_api_key: Optional[str]):
    """Resolve o provedor e retorna a função `classify(candidate) -> dict`
    usada tanto por run_llm_triage quanto por run_llm_triage_incremental.
    """
    if provider == "anthropic":
        try:
            import anthropic
        except ImportError as exc:
            raise RuntimeError(
                "O pacote 'anthropic' não está instalado. Rode `pip install anthropic` "
                "ou defina ANTHROPIC_API_KEY apenas se for usar `llm-triage`."
            ) from exc
        client = anthropic.Anthropic()  # lê ANTHROPIC_API_KEY do ambiente

        def classify(candidate: dict) -> dict:
            return classify_candidate_with_anthropic(client, candidate, model=model)

    elif provider == "openrouter":
        api_key = openrouter_api_key or os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY não definido. Exporte-o ou passe --openrouter-api-key."
            )

        def classify(candidate: dict) -> dict:
            return classify_candidate_with_openrouter(candidate, model=model, api_key=api_key)

    else:
        raise ValueError(f"Provedor desconhecido: {provider!r} (use 'anthropic' ou 'openrouter')")

    return classify


def _apply_audit_sampling(out: pd.DataFrame, audit_ratio: float, seed: int) -> pd.DataFrame:
    """Passo final comum aos dois modos (run_llm_triage e a versão
    incremental): itens "incerto" -> revisão obrigatória; amostra
    aleatória de `audit_ratio` dos demais também vai para revisão
    (Seção 5.6). Roda sobre o conjunto COMPLETO (retomado + novo), nunca
    por item — precisa ver o universo inteiro pra sortear a amostra.
    """
    rng = random.Random(seed)
    out = out.reset_index(drop=True)
    out["requires_human_review"] = out["llm_label"] == "incerto"

    non_uncertain_idx = out.index[~out["requires_human_review"]].tolist()
    audit_n = round(len(non_uncertain_idx) * audit_ratio)
    audit_idx = set(rng.sample(non_uncertain_idx, audit_n)) if audit_n > 0 else set()
    out.loc[list(audit_idx), "requires_human_review"] = True
    out["human_review_reason"] = out.apply(
        lambda r: "incerto" if r["llm_label"] == "incerto"
        else ("auditoria_15pct" if r.name in audit_idx else "nao_requer"),
        axis=1,
    )

    n_uncertain = (out["llm_label"] == "incerto").sum()
    logger.info(
        "Triagem LLM concluída: %d candidatos | %d 'incerto' (obrigatório) | "
        "%d na auditoria de %.0f%% | %d aceitos direto do LLM.",
        len(out), n_uncertain, len(audit_idx), audit_ratio * 100,
        len(out) - out["requires_human_review"].sum(),
    )
    return out


def run_llm_triage(
    candidates: pd.DataFrame,
    provider: str = "anthropic",
    model: str = "claude-fable-5",
    openrouter_api_key: Optional[str] = None,
    audit_ratio: float = LLM_HUMAN_AUDIT_SAMPLE_RATIO,
    seed: int = RANDOM_SEED,
) -> pd.DataFrame:
    """Implementa o fluxo completo da Seção 5.6, tudo em memória (sem
    checkpoint) — ver run_llm_triage_incremental para a versão tolerante
    a falhas, recomendada para rodadas grandes.

    1. léxico já gerou N candidatos (entrada `candidates`);
    2. LLM classifica cada um;
    3. itens "incerto" -> `requires_human_review = True` (obrigatório);
    4. amostra aleatória de `audit_ratio` (15%) dos demais também recebe
       `requires_human_review = True`;
    5. os restantes ficam com o rótulo do LLM e `requires_human_review = False`.
    """
    classify = _build_classifier(provider, model, openrouter_api_key)

    labels, rationales = [], []
    for _, row in candidates.iterrows():
        result = classify(row.to_dict())
        labels.append(result["label"])
        rationales.append(result["rationale"])

    out = candidates.copy()
    out["llm_label"] = labels
    out["llm_rationale"] = rationales
    return _apply_audit_sampling(out, audit_ratio, seed)


def _candidate_key(row: dict) -> str:
    """Chave estável de um candidato, usada pra saber (na retomada) quais
    já foram classificados — mesmo espírito da chave usada na purga de
    2026-07-06 (repo + tipo de artefato + id + expressão)."""
    return "|".join(str(row.get(k, "")) for k in
                     ("repo_full_name", "artifact_type", "artifact_id", "matched_expression"))


def run_llm_triage_incremental(
    candidates: pd.DataFrame,
    out_path: Path,
    provider: str = "anthropic",
    model: str = "claude-fable-5",
    openrouter_api_key: Optional[str] = None,
    audit_ratio: float = LLM_HUMAN_AUDIT_SAMPLE_RATIO,
    seed: int = RANDOM_SEED,
    log_every: int = 10,
) -> pd.DataFrame:
    """Mesmo fluxo de run_llm_triage (Seção 5.6), mas tolerante a falhas.

    Achado de 2026-07-08: os scripts 02 (coleta) e 04 (mineração) já
    tinham gravação incremental (o 04 só depois de perder uma rodada
    inteira de ~1h para uma interrupção externa do processo); o 03 nunca
    teve — uma rodada de ~1000 candidatos já levou mais de 2h sem
    nenhuma visibilidade de progresso nem possibilidade de retomada.

    Cada candidato classificado é imediatamente acrescentado a
    `out_path`. O próprio arquivo funciona como checkpoint: ao rodar de
    novo com o mesmo `out_path`, candidatos cuja chave (repo, tipo de
    artefato, id, expressão) já aparece no arquivo são pulados. As
    colunas de amostragem de auditoria (`requires_human_review`,
    `human_review_reason`) só são calculadas no final, sobre o conjunto
    completo — não dá pra sortear a amostra de 15% incrementalmente, tem
    que ver o universo inteiro. Por isso, enquanto a rodada está em
    andamento (ou foi interrompida no meio), o arquivo em disco tem só
    `llm_label`/`llm_rationale`; as colunas de revisão são adicionadas e
    o arquivo é reescrito completo somente quando todos os candidatos
    pendentes terminam de ser classificados.
    """
    classify = _build_classifier(provider, model, openrouter_api_key)

    base_fieldnames = list(candidates.columns)
    fieldnames = base_fieldnames + ["llm_label", "llm_rationale"]

    done_keys: set[str] = set()
    done_rows: list[dict] = []
    if out_path.exists() and out_path.stat().st_size > 0:
        existing = pd.read_csv(out_path)
        if "llm_label" in existing.columns:
            for _, r in existing.iterrows():
                row_dict = r.to_dict()
                done_keys.add(_candidate_key(row_dict))
                done_rows.append({k: row_dict.get(k) for k in fieldnames})
            logger.info("Retomando de %s: %d candidatos já classificados.", out_path, len(done_rows))

    pending = [row.to_dict() for _, row in candidates.iterrows() if _candidate_key(row.to_dict()) not in done_keys]
    logger.info("Triagem LLM: %d pendentes de %d totais (%d já feitos).",
                len(pending), len(candidates), len(done_rows))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not (out_path.exists() and out_path.stat().st_size > 0)
    with out_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        for i, candidate in enumerate(pending, start=1):
            result = classify(candidate)
            row_out = {**{k: candidate.get(k) for k in base_fieldnames},
                       "llm_label": result["label"], "llm_rationale": result["rationale"]}
            writer.writerow(row_out)
            f.flush()
            done_rows.append(row_out)
            if i % log_every == 0 or i == len(pending):
                logger.info("[%d/%d] classificado nesta execução (label=%s)", i, len(pending), result["label"])

    out = pd.DataFrame(done_rows)
    out = _apply_audit_sampling(out, audit_ratio, seed)
    # Reescreve o arquivo completo, agora com as colunas de revisão —
    # só chega aqui se TODOS os pendentes foram classificados com sucesso
    # (interrupção no meio do loop acima deixa o arquivo sem essas colunas,
    # sinal de que uma próxima execução ainda tem trabalho pendente).
    out.to_csv(out_path, index=False)
    return out


def validate_llm_against_human(llm_labels: list[str], human_labels: list[bool]) -> float:
    """Seção 5.6: "Se o kappa entre LLM e anotadores ficar abaixo de 0,61,
    a triagem automática é descartada e a anotação é feita integralmente
    por humanos." `human_labels` é a decisão humana is_ubw (bool);
    `llm_labels` é reduzido para binário (UBW-verdadeiro -> True, resto -> False)
    para ficar na mesma escala do julgamento humano nesta checagem.
    """
    llm_binary = [label == "UBW-verdadeiro" for label in llm_labels]
    kappa = cohens_kappa(llm_binary, human_labels)
    if kappa < LLM_KAPPA_DISCARD_THRESHOLD:
        logger.warning(
            "Kappa LLM-humano = %.3f < %.2f. Seção 5.6: a triagem automática deve ser "
            "DESCARTADA; toda a anotação passa a ser 100%% humana.",
            kappa, LLM_KAPPA_DISCARD_THRESHOLD,
        )
    else:
        logger.info("Kappa LLM-humano = %.3f >= %.2f. Triagem automática validada.",
                     kappa, LLM_KAPPA_DISCARD_THRESHOLD)
    return kappa


# =============================================================================
# CLI
# =============================================================================

def cmd_sample(args: argparse.Namespace) -> None:
    candidates = pd.read_csv(args.candidates)
    sample = stratified_sample(candidates, total_n=args.n, seed=args.seed)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(args.out, index=False)
    logger.info("Amostra salva em %s", args.out)


def cmd_llm_triage(args: argparse.Namespace) -> None:
    candidates = pd.read_csv(args.candidates)
    if args.max_candidates:
        candidates = candidates.head(args.max_candidates)
    model = args.model or ("claude-fable-5" if args.provider == "anthropic" else "deepseek/deepseek-v4-flash")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    if args.no_resume:
        result = run_llm_triage(
            candidates, provider=args.provider, model=model,
            openrouter_api_key=args.openrouter_api_key,
            audit_ratio=args.audit_ratio, seed=args.seed,
        )
        result.to_csv(args.out, index=False)
    else:
        result = run_llm_triage_incremental(
            candidates, out_path=Path(args.out), provider=args.provider, model=model,
            openrouter_api_key=args.openrouter_api_key,
            audit_ratio=args.audit_ratio, seed=args.seed, log_every=args.log_every,
        )
    logger.info("Resultado da triagem LLM salvo em %s", args.out)

    review_queue_path = Path(args.out).with_name(Path(args.out).stem + "_human_review_queue.csv")
    result[result["requires_human_review"]].to_csv(review_queue_path, index=False)
    logger.info("Fila de revisão humana (%d itens) salva em %s",
                result["requires_human_review"].sum(), review_queue_path)


def cmd_metrics(args: argparse.Namespace) -> None:
    annotations = pd.read_csv(args.annotations)
    # is_ubw pode vir como string "True"/"False" de CSV; normaliza para bool.
    if annotations["is_ubw"].dtype == object:
        annotations["is_ubw"] = annotations["is_ubw"].map(
            {"True": True, "False": False, "true": True, "false": False, True: True, False: False}
        )
    report = agreement_report(annotations)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(args.out, index=False)
    print(report.to_string(index=False))
    logger.info("Relatório de concordância salvo em %s", args.out)

    if args.llm_labels_col and args.llm_labels_col in annotations.columns:
        merged = annotations.drop_duplicates(subset=["artifact_id"])
        validate_llm_against_human(
            merged[args.llm_labels_col].tolist(), merged["is_ubw"].tolist()
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_sample = sub.add_parser("sample", help="Amostragem estratificada para validação manual (Seção 5.2).")
    p_sample.add_argument("--candidates", required=True)
    p_sample.add_argument("--out", required=True)
    p_sample.add_argument("--n", type=int, default=385)
    p_sample.add_argument("--seed", type=int, default=RANDOM_SEED)
    p_sample.set_defaults(func=cmd_sample)

    p_llm = sub.add_parser("llm-triage", help="Pré-triagem LLM (Seção 5.6).")
    p_llm.add_argument("--candidates", required=True)
    p_llm.add_argument("--out", required=True)
    p_llm.add_argument(
        "--provider", choices=["anthropic", "openrouter"], default="anthropic",
        help="Backend de LLM. 'openrouter' usa a API compatível com OpenAI da OpenRouter "
             "(ex: modelos DeepSeek, custo muito menor) — requer OPENROUTER_API_KEY. "
             "Confira o slug exato e o preço do modelo em https://openrouter.ai/models antes de rodar.",
    )
    p_llm.add_argument(
        "--model", default=None,
        help="Padrão: 'claude-fable-5' (provider=anthropic) ou 'deepseek/deepseek-v4-flash' (provider=openrouter, "
             "$0.09/$0.18 por 1M tokens in/out, confirmado em openrouter.ai/models em 2026-07-06).",
    )
    p_llm.add_argument("--openrouter-api-key", default=None, help="Padrão: variável de ambiente OPENROUTER_API_KEY.")
    p_llm.add_argument("--audit-ratio", type=float, default=LLM_HUMAN_AUDIT_SAMPLE_RATIO)
    p_llm.add_argument("--seed", type=int, default=RANDOM_SEED)
    p_llm.add_argument("--max-candidates", type=int, default=None, help="Limite para testes locais.")
    p_llm.add_argument(
        "--no-resume", action="store_true",
        help="Roda tudo em memória, sem gravação incremental nem retomada (comportamento antigo). "
             "Por padrão a triagem é incremental: cada candidato é gravado assim que classificado, e "
             "rodar de novo com o mesmo --out pula os já feitos.",
    )
    p_llm.add_argument(
        "--log-every", type=int, default=10,
        help="A cada quantos candidatos classificados imprime uma linha de progresso (modo incremental).",
    )
    p_llm.set_defaults(func=cmd_llm_triage)

    p_metrics = sub.add_parser("metrics", help="Cohen's Kappa e Gwet's AC1 (Seção 5.5).")
    p_metrics.add_argument("--annotations", required=True,
                            help="CSV longo: artifact_id, artifact_type, annotator_id, is_ubw, category_confirmed.")
    p_metrics.add_argument("--out", required=True)
    p_metrics.add_argument("--llm-labels-col", default=None,
                            help="Coluna opcional com o label do LLM, para validar contra o humano (Seção 5.6).")
    p_metrics.set_defaults(func=cmd_metrics)

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
