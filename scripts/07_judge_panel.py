#!/usr/bin/env python3
"""Fase 1 do experimento de validação por LLM — execução do painel de juízes.

Implementa o Procedimento 1 do PLANO_EXPERIMENTO_LLM.md: rodar cada combinação
de (modelo, estratégia de prompt) sobre um conjunto rotulado e guardar os votos
para a análise da Fase 2 (`08_panel_analysis.py`).

Cada combinação vira um arquivo JSONL em `validation/panel/runs/<conjunto>/`,
uma linha por item. A execução é retomável: itens já presentes no arquivo são
pulados, então interromper e rodar de novo continua de onde parou. O mesmo
comando serve para a aplicação ao corpus completo (Procedimento 4), bastando
apontar `--input` para o CSV do corpus — o gabarito é opcional.

Subcomandos:
    build-gold      monta os conjuntos de desenvolvimento (200) e teste (385)
    verify-judges   confere slug, contexto e preço dos modelos na OpenRouter
    run             roda um juiz (modelo + estratégia) sobre um conjunto
    import-legacy   traz as rodadas antigas de 2026-07/08 para o formato do painel
    status          lista o que já foi rodado e quanto falta

Exemplos:
    python 07_judge_panel.py build-gold

    python 07_judge_panel.py run \
        --input ../validation/panel/gold_dev_200.csv \
        --model deepseek/deepseek-v3.2-exp --strategy zero_shot

    python 07_judge_panel.py run \
        --input ../validation/panel/gold_dev_200.csv \
        --model qwen/qwen3-coder --strategy fewshot_retrieved --k 3
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import logging
import os
import re
import sys
import threading
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd  # noqa: E402

import panel_prompts  # noqa: E402
from ubw.envutil import load_dotenv  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ubw.judge_panel")

PANEL_DIR = ROOT / "validation" / "panel"
RUNS_DIR = PANEL_DIR / "runs"
BATCHES_DIR = ROOT / "validation" / "batches_3anotadores"
FINAL_DIR = ROOT / "validation" / "resultado_final"
SAMPLE_DIR = ROOT / "validation" / "sample_final_v2"

ANNOTATORS = ("Wendell", "Bruno", "Miguel")

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

GOLD_COLUMNS = [
    "item_id", "repo_full_name", "artifact_type", "matched_expression",
    "category_ubw", "body_text", "url", "n_true", "n_votes", "is_ubw_gold",
    "unanime", "rationale_human",
    # Voto individual de cada anotador, preservado ao lado do gabarito por
    # maioria. Sem isso só dá para medir "LLM contra a maioria dos 3", que não é
    # a mesma régua usada para reportar o kappa ENTRE os humanos (0,844-0,925),
    # que é par a par. Com estas colunas dá para calcular kappa(LLM, Wendell),
    # kappa(LLM, Bruno), kappa(LLM, Miguel) e comparar na régua certa.
    "vote__Wendell", "vote__Bruno", "vote__Miguel",
]


# ---------------------------------------------------------------------------
# build-gold — conjuntos de desenvolvimento e teste
# ---------------------------------------------------------------------------


def _first_rationale(row: pd.Series, gold: bool) -> str:
    """Justificativa humana para servir de exemplo few-shot. Prefere a de um
    anotador que votou igual ao gabarito: uma justificativa que defende o rótulo
    oposto ensinaria o critério errado."""
    aligned = [c for c in ANNOTATORS if bool(row.get(f"vote__{c}")) == gold]
    for annotator in aligned + list(ANNOTATORS):
        text = row.get(f"obs__{annotator}")
        if isinstance(text, str) and text.strip():
            return text.strip()
    return ""


def _majority(votes: list) -> tuple[Optional[bool], int, int]:
    """Voto majoritário sobre os votos não nulos. Retorna (gold, n_true, n_votes)."""
    clean = [bool(v) for v in votes if pd.notna(v)]
    if not clean:
        return None, 0, 0
    n_true = sum(clean)
    return (n_true * 2 > len(clean)), n_true, len(clean)


def _assemble_gold(per_annotator: dict[str, pd.DataFrame], label_col: str) -> pd.DataFrame:
    """Junta as anotações dos três e resolve o gabarito por maioria."""
    base = None
    for name, df in per_annotator.items():
        keep = df[["item_id", label_col, "observacao"]].rename(
            columns={label_col: f"vote__{name}", "observacao": f"obs__{name}"}
        )
        meta_cols = [c for c in ("repo_full_name", "artifact_type", "matched_expression",
                                 "category_ubw", "body_text", "url") if c in df.columns]
        if base is None:
            base = df[["item_id"] + meta_cols].merge(keep, on="item_id", how="left")
        else:
            base = base.merge(keep, on="item_id", how="left")
    assert base is not None

    resolved = base.apply(
        lambda r: _majority([r.get(f"vote__{a}") for a in ANNOTATORS]),
        axis=1, result_type="expand",
    )
    base["is_ubw_gold"] = resolved[0]
    base["n_true"] = resolved[1]
    base["n_votes"] = resolved[2]
    # Unanimidade é "todos votaram igual", nas duas direções. Comparação
    # elemento a elemento, não `isin`: uma Series dentro da lista do `isin` não é
    # hashável e é descartada em silêncio, o que deixaria só os unânimes
    # negativos (era o bug que marcava 21 dos 188 unânimes do desenvolvimento).
    base["unanime"] = (
        ((base["n_true"] == 0) | (base["n_true"] == base["n_votes"]))
        & (base["n_votes"] > 0)
    )
    base["rationale_human"] = base.apply(
        lambda r: _first_rationale(r, bool(r["is_ubw_gold"])), axis=1
    )

    missing = base["is_ubw_gold"].isna().sum()
    if missing:
        logger.warning("%d itens sem nenhum voto válido — removidos do gabarito", missing)
        base = base[base["is_ubw_gold"].notna()].copy()
    for col in GOLD_COLUMNS:
        if col not in base.columns:
            base[col] = ""
    return base[GOLD_COLUMNS]


def _attach_category(df: pd.DataFrame) -> pd.DataFrame:
    """`category_ubw` não sobrevive em todos os batches, mas o prompt v1 usa esse
    campo e a categoria é dimensão de reporte. Deriva do léxico: a categoria é
    função determinística da expressão que casou, então não precisa de join com
    a amostra original (o `item_id` dos batches é uma chave composta, e não bate
    com o `artifact_id` dos CSVs de amostragem)."""
    from ubw.lexicon import expression_to_category

    missing = df["category_ubw"].astype(str).str.strip().eq("") | df["category_ubw"].isna()
    if not missing.any():
        return df
    derived = df["matched_expression"].astype(str).map(
        lambda expr: expression_to_category(expr) or ""
    )
    df["category_ubw"] = df["category_ubw"].astype(str).where(~missing, derived)
    still_empty = int(df["category_ubw"].str.strip().eq("").sum())
    if still_empty:
        logger.warning("%d itens sem categoria derivável do léxico", still_empty)
    return df


def cmd_build_gold(args: argparse.Namespace) -> None:
    PANEL_DIR.mkdir(parents=True, exist_ok=True)

    # Desenvolvimento: os 200 da calibração, direto dos batches preenchidos.
    dev_sources = {
        name: pd.read_csv(BATCHES_DIR / f"batch_{name}_calibracao_oficial_PREENCHIDO.csv")
        for name in ANNOTATORS
    }
    dev = _attach_category(_assemble_gold(dev_sources, label_col="is_ubw"))
    dev_path = PANEL_DIR / "gold_dev_200.csv"
    dev.to_csv(dev_path, index=False)

    # Teste: o consenso já fechado dos 385, com as observações vindas dos
    # arquivos individuais (o consenso guarda só os votos).
    consenso = pd.read_csv(FINAL_DIR / "consenso_385.csv")
    test = consenso.rename(columns={"is_ubw_final": "is_ubw_gold"}).copy()
    test["n_votes"] = test[list(ANNOTATORS)].notna().sum(axis=1)
    test["unanime"] = test["unanime"].astype(str).str.lower().isin(["sim", "true", "1"])
    for name in ANNOTATORS:
        obs = pd.read_csv(FINAL_DIR / f"anotacao_{name}_385.csv")[["item_id", "observacao"]]
        test = test.merge(obs.rename(columns={"observacao": f"obs__{name}"}), on="item_id", how="left")
        test[f"vote__{name}"] = test[name]
    test["rationale_human"] = test.apply(
        lambda r: _first_rationale(r, bool(r["is_ubw_gold"])), axis=1
    )
    for col in GOLD_COLUMNS:
        if col not in test.columns:
            test[col] = ""
    test = _attach_category(test[GOLD_COLUMNS])
    test_path = PANEL_DIR / "gold_test_385.csv"
    test.to_csv(test_path, index=False)

    for label, df, path in (("desenvolvimento", dev, dev_path), ("teste", test, test_path)):
        pos = int(df["is_ubw_gold"].astype(bool).sum())
        rationales = int(df["rationale_human"].astype(str).str.strip().ne("").sum())
        logger.info("%s: %d itens (%d positivos / %d negativos), %d com justificativa humana -> %s",
                    label, len(df), pos, len(df) - pos, rationales, path)


# ---------------------------------------------------------------------------
# verify-judges — confere os slugs contra a API antes de gastar execução
# ---------------------------------------------------------------------------


def cmd_verify_judges(args: argparse.Namespace) -> None:
    import requests

    resp = requests.get(OPENROUTER_MODELS_URL, timeout=30)
    resp.raise_for_status()
    catalog = {m["id"]: m for m in resp.json()["data"]}

    rows = []
    for slug in args.model:
        entry = catalog.get(slug)
        if entry is None:
            near = [k for k in catalog if slug.split("/")[-1][:12] in k][:3]
            rows.append({"model": slug, "existe": False, "prompt_usd_mtok": "",
                         "completion_usd_mtok": "", "context": "",
                         "sugestoes": ", ".join(near)})
            continue
        pricing = entry.get("pricing", {})
        rows.append({
            "model": slug,
            "existe": True,
            "prompt_usd_mtok": round(float(pricing.get("prompt", 0)) * 1e6, 3),
            "completion_usd_mtok": round(float(pricing.get("completion", 0)) * 1e6, 3),
            "context": entry.get("context_length", ""),
            "sugestoes": "",
        })
    table = pd.DataFrame(rows)
    print(table.to_string(index=False))
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        table.to_csv(args.out, index=False)
        logger.info("catálogo conferido gravado em %s", args.out)


# ---------------------------------------------------------------------------
# pick-providers — fixa UM endpoint por modelo, para que o juiz seja reproduzível
# ---------------------------------------------------------------------------

# Por que existe: a OpenRouter roteia cada requisição para o endpoint que julgar
# melhor no momento. Num teste de 40 chamadas ao gpt-oss-120b saíram DEZ
# provedores distintos, e os endpoints desse modelo incluem bf16, fp4 e
# quantização não declarada AO MESMO PREÇO. Ou seja: sem fixar, "o juiz
# gpt-oss-120b" não é um classificador, é uma mistura de vários. Temperatura zero
# não corrige isso, porque a diferença está no peso, não na amostragem.
#
# Política de escolha: maior precisão numérica disponível, desempate por preço.
# `unknown` fica por último — não é necessariamente ruim, mas não é auditável, e
# o pacote de replicação precisa declarar em que peso o número foi produzido.

PROVIDERS_PATH = PANEL_DIR / "providers.csv"
_QUANT_RANK = {"bf16": 0, "fp16": 0, "fp8": 1, "int8": 1, "fp6": 2,
               "fp4": 3, "int4": 3, "unknown": 9, None: 9}


def cmd_pick_providers(args: argparse.Namespace) -> None:
    import requests

    rows = []
    for slug in args.model:
        url = f"https://openrouter.ai/api/v1/models/{slug}/endpoints"
        endpoints = requests.get(url, timeout=30).json()["data"].get("endpoints", [])
        if not endpoints:
            logger.warning("%s: nenhum endpoint listado", slug)
            continue
        ranked = sorted(
            endpoints,
            key=lambda e: (
                _QUANT_RANK.get(e.get("quantization"), 9),
                float(e["pricing"]["prompt"]) + float(e["pricing"]["completion"]),
            ),
        )
        best = ranked[0]
        rows.append({
            "model": slug,
            "provider": best.get("provider_name"),
            "quantization": best.get("quantization") or "unknown",
            "prompt_usd_mtok": round(float(best["pricing"]["prompt"]) * 1e6, 3),
            "completion_usd_mtok": round(float(best["pricing"]["completion"]) * 1e6, 3),
            "context": best.get("context_length"),
            "n_endpoints": len(endpoints),
            "quantizacoes_disponiveis": ",".join(
                sorted({str(e.get("quantization") or "unknown") for e in endpoints})),
        })
    table = pd.DataFrame(rows)
    print(table.to_string(index=False))
    PROVIDERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(PROVIDERS_PATH, index=False)
    logger.info("escolha de provedores gravada em %s", PROVIDERS_PATH)


def load_pinned_provider(model: str) -> Optional[str]:
    if not PROVIDERS_PATH.exists():
        return None
    table = pd.read_csv(PROVIDERS_PATH)
    match = table[table.model == model]
    return None if match.empty else str(match.iloc[0]["provider"])


# ---------------------------------------------------------------------------
# run — execução de um juiz sobre um conjunto
# ---------------------------------------------------------------------------


def judge_slug(model: str, strategy: str, k: Optional[int],
               reasoning_effort: Optional[str] = None,
               drop_category: bool = False,
               center_window: bool = False) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", f"{model}__{strategy}".lower()).strip("_")
    if strategy == "fewshot_retrieved" and k:
        base = f"{base}_k{k}"
    if reasoning_effort:
        # Sufixo próprio: um mesmo modelo com esforço de raciocínio diferente é
        # um juiz diferente, e os votos não podem cair no mesmo arquivo.
        base = f"{base}_r{reasoning_effort}"
    if drop_category:
        base = f"{base}_nocat"  # braço de ablação, arquivo separado
    if center_window:
        base = f"{base}_win"    # recorte centrado na expressão
    return base


def _call_openrouter(system_prompt: str, user_prompt: str, model: str, api_key: str,
                     max_retries: int = 4, provider: Optional[str] = None,
                     reasoning_effort: Optional[str] = None) -> dict:
    """Uma chamada, com o mesmo fail-safe do script 03: falha persistente vira
    'incerto' em vez de derrubar a execução ou sumir com o item."""
    import requests

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "temperature": 0,
        # Orçamento TOTAL da resposta, raciocínio incluído — e é só teto, não
        # reserva: cobra-se o que for gerado. Medido na matriz do desenvolvimento
        # (8.400 respostas), a saída média por modelo vai de 55 tokens
        # (deepseek-chat, que não raciocina) a 757 (kimi-k2.5, p95 = 977). Com o
        # teto anterior de 1.000 o kimi truncava em 199 dos 200 itens de uma
        # estratégia, e cada truncamento virava `incerto` de fail-safe: abstenção
        # fabricada por orçamento, não dúvida do modelo. 2.500 dá folga sobre o
        # pior p95 observado sem custar nada a quem gera pouco.
        "max_tokens": 2500,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    if provider:
        # `allow_fallbacks: false` é o ponto: sem isso a OpenRouter cai para outro
        # endpoint quando o escolhido está ocupado, e a fixação vira decorativa.
        # Falhar é o comportamento desejado — a retomada reprocessa `ok: False`.
        payload["provider"] = {"order": [provider], "allow_fallbacks": False}
    if reasoning_effort:
        # Medido no gpt-oss-120b sobre 12 itens do desenvolvimento: `high` gasta
        # 488 tokens de saída e concorda 88% com o humano; `medium` (o default do
        # provedor) gasta 218 e concorda 92%; `low` gasta 114, concorda 92% e não
        # abstém nenhuma vez. Como a saída custa cerca de 4,6x a entrada por token
        # nesses modelos, é a maior alavanca de custo do experimento — e, por
        # mudar o comportamento do juiz, é parâmetro de configuração congelado
        # junto com o prompt, nunca ajuste silencioso.
        payload["reasoning"] = {"effort": reasoning_effort}

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=90)
            resp.raise_for_status()
            data = resp.json()
            choice = data["choices"][0]
            usage = data.get("usage") or {}
            reasoning_tokens = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens")

            # Erros explícitos em vez de AttributeError/JSONDecodeError crípticos:
            # o log precisa distinguir "modelo respondeu mal" de "faltou orçamento".
            if choice.get("finish_reason") == "length":
                raise ValueError(
                    f"resposta truncada por max_tokens (raciocínio: {reasoning_tokens} tokens)")
            content = choice["message"].get("content")
            if not content:
                raise ValueError(
                    f"content vazio; o modelo gastou o orçamento em raciocínio "
                    f"({reasoning_tokens} tokens)")

            parsed = panel_prompts.parse_llm_json_label(content)
            parsed["prompt_tokens"] = usage.get("prompt_tokens")
            parsed["completion_tokens"] = usage.get("completion_tokens")
            parsed["reasoning_tokens"] = reasoning_tokens
            parsed["provider"] = data.get("provider")
            parsed["ok"] = True
            return parsed
        except Exception as exc:  # noqa: BLE001 — degrada para 'incerto', nunca perde o item
            logger.warning("tentativa %d/%d falhou (%s): %s", attempt, max_retries, model, exc)
            # Backoff exponencial, e mais longo em 429. Com endpoint fixo e sem
            # fallback, rate limit é a falha dominante (1.599 ocorrências na
            # matriz do desenvolvimento) e não adianta reperguntar em 2 segundos:
            # não há capacidade, há fila. Respeita `Retry-After` quando o
            # provedor manda.
            delay = 2 ** attempt
            response = getattr(exc, "response", None)
            if response is not None and response.status_code == 429:
                delay = max(delay, 15)
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    try:
                        delay = max(delay, float(retry_after))
                    except ValueError:
                        pass
            time.sleep(delay)
    return {"label": "incerto", "rationale": "falha técnica na chamada", "ok": False,
            "failed_condition": None, "prompt_tokens": None, "completion_tokens": None,
            "reasoning_tokens": None, "provider": None}


def _load_done(path: Path) -> set[str]:
    """Itens já julgados COM SUCESSO, que a retomada pode pular.

    Registros com `ok: False` não contam. Eles são o fail-safe de falha técnica
    (rede caída, rate limit, 402 sem crédito) e trazem label `incerto` com a
    justificativa "falha técnica na chamada" — não são julgamento nenhum. Contá-los
    como feitos transformaria uma indisponibilidade momentânea da API em rótulo
    permanente, e num corpus que roda por horas isso contamina em silêncio. A
    retomada reprocessa essas linhas; `read_run` fica com a última ocorrência de
    cada item.
    """
    if not path.exists():
        return set()
    done = set()
    failed = 0
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                if record.get("ok", True):
                    done.add(record["item_id"])
                else:
                    failed += 1
            except (json.JSONDecodeError, KeyError):
                logger.warning("linha inválida ignorada em %s", path)
    if failed:
        logger.info("%s: %d itens com falha técnica serão reprocessados", path.name, failed)
    return done


def cmd_run(args: argparse.Namespace) -> None:
    api_key = args.openrouter_api_key or os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY não definido (exporte ou passe --openrouter-api-key)")

    items = pd.read_csv(args.input)
    if "item_id" not in items.columns and "artifact_id" in items.columns:
        items = items.rename(columns={"artifact_id": "item_id"})
    if args.limit:
        items = items.head(args.limit)

    slug = judge_slug(args.model, args.strategy, args.k, args.reasoning_effort,
                      args.drop_category, args.center_window)
    set_name = Path(args.input).stem
    out_path = RUNS_DIR / set_name / f"{slug}.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    provider = args.provider or load_pinned_provider(args.model)
    if provider:
        logger.info("provedor fixado: %s (sem fallback)", provider)
    else:
        logger.warning("SEM provedor fixado para %s — a OpenRouter vai rotear livremente, "
                       "e o juiz deixa de ser reproduzível. Rode `pick-providers` antes.",
                       args.model)

    pool = None
    # Só as duas estratégias few-shot precisam de exemplos. `zero_shot_nodef` e
    # `zero_shot` não: exigir pool delas quebraria a aplicação ao corpus, que não
    # tem a coluna `is_ubw_gold`.
    if args.strategy.startswith("fewshot"):
        pool_path = Path(args.pool) if args.pool else Path(args.input)
        pool_df = pd.read_csv(pool_path)
        if "is_ubw_gold" not in pool_df.columns:
            raise SystemExit(f"o pool {pool_path} não tem coluna is_ubw_gold")
        pool = panel_prompts.ExemplarPool(pool_df.to_dict("records"), seed=args.seed)
        logger.info("pool de exemplos: %s (%d itens)", pool_path, len(pool_df))

    done = _load_done(out_path)
    pending = [r for r in items.to_dict("records") if str(r["item_id"]) not in done]
    logger.info("juiz %s | conjunto %s | %d já feitos, %d pendentes",
                slug, set_name, len(done), len(pending))
    if not pending:
        return

    write_lock = threading.Lock()
    counter = {"n": 0}

    def process(row: dict) -> None:
        candidate = dict(row)
        candidate["item_id"] = str(candidate["item_id"])
        exemplars = pool.exemplars_for(candidate, args.strategy, args.k) if pool else []
        system_prompt, user_prompt = panel_prompts.build_prompt(
            candidate, args.strategy, exemplars, drop_category=args.drop_category,
            center_window=args.center_window)
        result = _call_openrouter(system_prompt, user_prompt, args.model, api_key,
                                  provider=provider,
                                  reasoning_effort=args.reasoning_effort)
        record = {
            "item_id": candidate["item_id"],
            "model": args.model,
            "strategy": args.strategy,
            "k": args.k if args.strategy == "fewshot_retrieved" else None,
            "reasoning_effort": args.reasoning_effort,
            "drop_category": args.drop_category,
            "center_window": args.center_window,
            "label": result["label"],
            "rationale": result.get("rationale", ""),
            "ok": result.get("ok", False),
            "prompt_tokens": result.get("prompt_tokens"),
            "completion_tokens": result.get("completion_tokens"),
            # Quanto da saída foi raciocínio, e por qual provedor a OpenRouter
            # roteou: o primeiro mede o custo real dos modelos de raciocínio, o
            # segundo é o que o manifest precisa para a ameaça de determinismo.
            "reasoning_tokens": result.get("reasoning_tokens"),
            "provider": result.get("provider"),
            "exemplar_ids": [e["item_id"] for e in exemplars],
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        with write_lock:
            with out_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            counter["n"] += 1
            if counter["n"] % 25 == 0:
                logger.info("  %d/%d", counter["n"], len(pending))

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool_exec:
        list(pool_exec.map(process, pending))

    logger.info("concluído: %s", out_path)
    _print_run_summary(out_path, items)


def _print_run_summary(out_path: Path, items: pd.DataFrame) -> None:
    votes = read_run(out_path)
    dist = votes["label"].value_counts().to_dict()
    logger.info("distribuição de rótulos: %s", dist)
    if "is_ubw_gold" in items.columns:
        merged = items[["item_id", "is_ubw_gold"]].astype({"item_id": str}).merge(votes, on="item_id")
        decided = merged[merged["label"] != "incerto"]
        if len(decided):
            pred = decided["label"].eq("UBW-verdadeiro")
            gold = decided["is_ubw_gold"].astype(bool)
            logger.info("acurácia nos decididos: %.1f%% (%d itens)",
                        100 * (pred == gold).mean(), len(decided))


# ---------------------------------------------------------------------------
# import-legacy — aproveita as rodadas que já foram pagas
# ---------------------------------------------------------------------------

# Rodadas anteriores sobre os MESMOS 200 itens de calibração, feitas antes de o
# painel existir. Trazê-las para cá evita repetir chamada já paga e já dá dois
# juízes reais na Fase 1. O prompt v1 dessas rodadas é exatamente a estratégia
# zero_shot; o v2 (experimento reprovado, ver 03_metrics_llm_triage.py) entra
# como configuração à parte, porque continua sendo um ponto de comparação
# legítimo do painel.
LEGACY_SOURCES = [
    {
        "path": ROOT / "validation" / "experimentos_prompt" / "calib_prompt_v1.csv",
        "id_col": "item_id",
        "strategy": "zero_shot",
        "columns": {
            "llm_label__openrouter_deepseek_deepseek_v3_2_exp": "deepseek/deepseek-v3.2-exp",
            "llm_label__openrouter_qwen_qwen3_coder": "qwen/qwen3-coder",
        },
    },
    {
        "path": ROOT / "validation" / "experimentos_prompt" / "calib_prompt_v2.csv",
        "id_col": "item_id",
        "strategy": "checklist_v2",
        "columns": {
            "llm_label__openrouter_deepseek_deepseek_v3_2_exp": "deepseek/deepseek-v3.2-exp",
            "llm_label__openrouter_qwen_qwen3_coder": "qwen/qwen3-coder",
        },
    },
]


def cmd_import_legacy(args: argparse.Namespace) -> None:
    set_name = args.set
    gold_path = PANEL_DIR / f"{set_name}.csv"
    known_ids = set(pd.read_csv(gold_path)["item_id"].astype(str))

    for source in LEGACY_SOURCES:
        if not source["path"].exists():
            logger.warning("fonte ausente, pulando: %s", source["path"])
            continue
        df = pd.read_csv(source["path"])
        id_col = source["id_col"] if source["id_col"] in df.columns else "artifact_id"
        for label_col, model in source["columns"].items():
            if label_col not in df.columns:
                logger.warning("%s não tem a coluna %s", source["path"].name, label_col)
                continue
            rationale_col = label_col.replace("llm_label__", "llm_rationale__")
            slug = judge_slug(model, source["strategy"], None)
            out_path = RUNS_DIR / set_name / f"{slug}.jsonl"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            if out_path.exists() and not args.overwrite:
                logger.info("já existe, pulando (use --overwrite): %s", out_path)
                continue
            written = 0
            with out_path.open("w", encoding="utf-8") as handle:
                for row in df.to_dict("records"):
                    item_id = str(row[id_col])
                    if item_id not in known_ids:
                        continue
                    label = row.get(label_col)
                    if not isinstance(label, str) or label not in panel_prompts.VALID_LLM_LABELS:
                        continue
                    handle.write(json.dumps({
                        "item_id": item_id,
                        "model": model,
                        "strategy": source["strategy"],
                        "k": None,
                        "label": label,
                        "rationale": row.get(rationale_col, ""),
                        "ok": True,
                        "prompt_tokens": None,
                        "completion_tokens": None,
                        "exemplar_ids": [],
                        "source": source["path"].name,
                    }, ensure_ascii=False) + "\n")
                    written += 1
            logger.info("%s: %d itens -> %s", model, written, out_path)


def read_run(path: Path) -> pd.DataFrame:
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    df = pd.DataFrame(records)
    df["item_id"] = df["item_id"].astype(str)
    return df.drop_duplicates(subset="item_id", keep="last")


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


def cmd_status(args: argparse.Namespace) -> None:
    if not RUNS_DIR.exists():
        print("nenhuma execução ainda.")
        return
    rows = []
    for set_dir in sorted(RUNS_DIR.iterdir()):
        if not set_dir.is_dir():
            continue
        total = None
        gold_path = PANEL_DIR / f"{set_dir.name}.csv"
        if gold_path.exists():
            total = len(pd.read_csv(gold_path))
        for run_path in sorted(set_dir.glob("*.jsonl")):
            votes = read_run(run_path)
            rows.append({
                "conjunto": set_dir.name,
                "juiz": run_path.stem,
                "itens": len(votes),
                "faltam": (total - len(votes)) if total else "",
                "incerto": int(votes["label"].eq("incerto").sum()),
                "falhas": int((~votes["ok"].astype(bool)).sum()) if "ok" in votes else 0,
            })
    if not rows:
        print("nenhuma execução ainda.")
        return
    print(pd.DataFrame(rows).to_string(index=False))


# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("build-gold", help="monta gold_dev_200.csv e gold_test_385.csv")

    p_verify = sub.add_parser("verify-judges", help="confere slugs e preços na OpenRouter")
    p_verify.add_argument("--model", action="append", required=True,
                          help="slug do modelo (repetir para vários)")
    p_verify.add_argument("--out", help="CSV opcional com o resultado")

    p_pick = sub.add_parser("pick-providers",
                            help="fixa um endpoint por modelo (maior precisão, desempate por preço)")
    p_pick.add_argument("--model", action="append", required=True,
                        help="slug OpenRouter; repita a flag para vários")

    p_run = sub.add_parser("run", help="roda um juiz sobre um conjunto")
    p_run.add_argument("--input", required=True, help="CSV com os itens a julgar")
    p_run.add_argument("--model", required=True, help="slug OpenRouter do modelo")
    p_run.add_argument("--strategy", choices=panel_prompts.STRATEGIES, default="zero_shot")
    p_run.add_argument("--pool", help="CSV com os exemplos rotulados (default: o próprio --input)")
    p_run.add_argument("--k", type=int, default=panel_prompts.DEFAULT_RETRIEVED_K,
                       help="número de exemplos recuperados (só para fewshot_retrieved)")
    p_run.add_argument("--workers", type=int, default=8)
    p_run.add_argument("--limit", type=int, help="corta o conjunto (para teste de fumaça)")
    p_run.add_argument("--seed", type=int, default=42)
    p_run.add_argument("--openrouter-api-key")
    p_run.add_argument("--provider", help="fixa o endpoint (default: o escolhido em "
                                          "validation/panel/providers.csv)")
    p_run.add_argument("--reasoning-effort", choices=("low", "medium", "high"),
                       help="esforço de raciocínio; só faz efeito em modelos que raciocinam. "
                            "Omitido = default do provedor (equivale a medium)")
    p_run.add_argument("--center-window", action="store_true",
                       help="recorta o corpo em torno da expressão-gatilho em vez do prefixo; "
                            "corrige os itens em que o corte de 2000 caracteres escondia a "
                            "expressão do juiz")
    p_run.add_argument("--drop-category", action="store_true",
                       help="braço de ablação: remove do prompt a linha da categoria léxica "
                            "já atribuída pelo pipeline (Seção 4.3.2 do plano)")

    p_legacy = sub.add_parser("import-legacy", help="importa as rodadas antigas de 2026-07/08")
    p_legacy.add_argument("--set", default="gold_dev_200")
    p_legacy.add_argument("--overwrite", action="store_true")

    sub.add_parser("status", help="mostra o que já foi rodado")

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    {
        "build-gold": cmd_build_gold,
        "verify-judges": cmd_verify_judges,
        "pick-providers": cmd_pick_providers,
        "run": cmd_run,
        "import-legacy": cmd_import_legacy,
        "status": cmd_status,
    }[args.command](args)


if __name__ == "__main__":
    main()
