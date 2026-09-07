#!/usr/bin/env python3
"""Fase 2 do experimento de validação por LLM — análise do painel e escolha da regra.

Consome os votos gravados por `07_judge_panel.py` e executa o protocolo da Seção
3.3 do PLANO_EXPERIMENTO_LLM.md, na ordem em que ele foi fixado antes de qualquer
execução:

    Passo 1  eliminatória: juiz com kappa < 0,40 contra o gabarito humano sai
    Passo 2  diagnóstico de correlação de erro e votos efetivamente independentes
    Passo 3  escolha da regra de agregação, condicionada ao que o Passo 2 mostrou
    Passo 4  detectores externos de SATD entram como flag, nunca como voto

Métrica principal: precisão do alerta (dos itens que o juiz marcou como provável
falso positivo, que fração o humano confirma). Acurácia é reportada mas não
decide nada — com 86,5% de positivos, responder "é UBW" para tudo já acerta
86,5% com kappa zero.

Convenções:
    alerta      o juiz respondeu "não-UBW" (marcou o item como falso positivo)
    abstenção   o juiz respondeu "incerto"; conta como ausência de alerta na
                agregação, e é reportada à parte

Subcomandos:
    report    métricas por juiz, matriz de concordância, diagnóstico e regras
    apply     aplica uma regra já congelada a um conjunto de votos

Exemplos:
    python 08_panel_analysis.py report --set gold_dev_200
    python 08_panel_analysis.py apply --set gold_test_385 --rule majority \
        --judges deepseek_deepseek_v3_2_exp__zero_shot qwen_qwen3_coder__zero_shot
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import sys
from pathlib import Path
from typing import Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PANEL_DIR = ROOT / "validation" / "panel"
RUNS_DIR = PANEL_DIR / "runs"
ANALYSIS_DIR = PANEL_DIR / "analysis"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ubw.panel_analysis")

# Passo 1. A barra é 0,75, na faixa dos kappa observados entre os anotadores
# humanos (0,844 a 0,925). O fallback está pré-registrado no plano, e não é
# hipótese remota: as duas únicas configurações já medidas contra este gabarito
# ficaram em 0,408 e 0,611. Se ninguém passar de 0,75, o painel usa os três
# melhores acima de 0,40 (limiar de "moderado" de Landis e Koch) e o relatório
# declara que opera abaixo da barra pretendida.
KAPPA_ELIMINATION_THRESHOLD = 0.75
KAPPA_FALLBACK_THRESHOLD = 0.40
FALLBACK_PANEL_SIZE = 3
EFFECTIVE_VOTES_FLOOR = 2.0  # Passo 3: abaixo disso o painel é redundante
KAPPA_SPREAD_TOLERANCE = 0.15  # Passo 3: o que conta como "confiabilidade parecida"
MAX_PANEL_SIZE = 5  # Kohli (2026): cinco juízes já capturam ~90% da independência
BOOTSTRAP_ITERATIONS = 2000
RANDOM_SEED = 42
# Fração mínima do conjunto que um juiz precisa cobrir para entrar no relatório.
# Protege contra execução em andamento: um juiz medido em 11 de 200 itens pode
# ter kappa alto por acaso e deslocar o líder do ranking.
MIN_COVERAGE = 0.98

ALERT_LABEL = "não-UBW"
ABSTAIN_LABEL = "incerto"
ANNOTATORS = ("Wendell", "Bruno", "Miguel")


def _load_triage_module():
    """Reaproveita kappa, AC1 e a leitura de Landis-Koch já implementados no
    script 03, em vez de reimplementar as mesmas fórmulas."""
    path = Path(__file__).resolve().parent / "03_metrics_llm_triage.py"
    spec = importlib.util.spec_from_file_location("ubw_triage_metrics", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_triage = _load_triage_module()
cohens_kappa = _triage.cohens_kappa
gwets_ac1 = _triage.gwets_ac1
interpret_kappa = _triage.interpret_kappa


# ---------------------------------------------------------------------------
# Carga
# ---------------------------------------------------------------------------


def load_panel(set_name: str, judges: Optional[list[str]] = None) -> tuple[pd.DataFrame, list[str]]:
    """Devolve (tabela larga, nomes dos juízes). Uma linha por item, uma coluna
    `label__<juiz>` por juiz, mais o gabarito humano."""
    gold_path = PANEL_DIR / f"{set_name}.csv"
    if not gold_path.exists():
        raise SystemExit(f"conjunto não encontrado: {gold_path} (rode 07_judge_panel.py build-gold)")
    gold = pd.read_csv(gold_path)
    gold["item_id"] = gold["item_id"].astype(str)

    run_dir = RUNS_DIR / set_name
    if not run_dir.exists():
        raise SystemExit(f"nenhuma execução em {run_dir}")

    wide = gold.copy()
    found: list[str] = []
    incomplete: list[tuple[str, int]] = []
    for run_path in sorted(run_dir.glob("*.jsonl")):
        name = run_path.stem
        if judges and name not in judges:
            continue
        records = [json.loads(line) for line in run_path.read_text(encoding="utf-8").splitlines()
                   if line.strip()]
        votes = pd.DataFrame(records)
        votes["item_id"] = votes["item_id"].astype(str)
        votes = votes.drop_duplicates(subset="item_id", keep="last")

        # Registros com `ok: False` são fail-safe de falha técnica (rate limit,
        # 402, timeout) e trazem label "incerto" com a justificativa "falha
        # técnica na chamada". Não são julgamento: contá-los como abstenção
        # atribuiria ao modelo uma prudência que foi da rede. Viram ausência de
        # voto, que o resto do script já trata (e derrubam a cobertura, então uma
        # execução majoritariamente falha é descartada pelo filtro abaixo).
        if "ok" in votes.columns:
            n_failed = int((~votes["ok"].fillna(True).astype(bool)).sum())
            if n_failed:
                votes = votes[votes["ok"].fillna(True).astype(bool)]
                logger.warning("juiz %s: %d registros com falha técnica descartados",
                               name, n_failed)

        coverage = votes["item_id"].isin(wide["item_id"]).sum()
        if coverage < len(wide) * MIN_COVERAGE:
            # Execução ainda em andamento (ou interrompida). Entra no ranking, um
            # juiz medido em 11 de 200 itens pode ter kappa alto por puro acaso e
            # deslocar o líder — então fica de fora até completar.
            logger.warning("juiz %s IGNORADO: cobre só %d de %d itens (execução incompleta)",
                           name, coverage, len(wide))
            incomplete.append((name, int(coverage)))
            continue
        if coverage < len(wide):
            logger.warning("juiz %s cobre %d de %d itens do conjunto", name, coverage, len(wide))
        wide = wide.merge(
            votes[["item_id", "label"]].rename(columns={"label": f"label__{name}"}),
            on="item_id", how="left",
        )
        found.append(name)

    if incomplete:
        logger.info("%d juízes fora do relatório por execução incompleta: %s",
                    len(incomplete), ", ".join(f"{n} ({c})" for n, c in incomplete))
    if not found:
        raise SystemExit(f"nenhum juiz carregado de {run_dir}")
    return wide, found


def _alert_series(wide: pd.DataFrame, judge: str) -> pd.Series:
    """1 quando o juiz sinalizou falso positivo. Abstenção e ausência de voto
    contam como 0: a coluna publicada é uma marcação positiva de suspeita, e não
    ter opinião não é suspeitar."""
    return wide[f"label__{judge}"].eq(ALERT_LABEL).astype(int)


# ---------------------------------------------------------------------------
# Métricas por juiz
# ---------------------------------------------------------------------------


def _bootstrap_ci(hits: np.ndarray, iterations: int = BOOTSTRAP_ITERATIONS) -> tuple[float, float]:
    """IC 95% percentil para uma proporção. Bootstrap porque os denominadores
    aqui são pequenos (dezenas de alertas) e a aproximação normal é ruim nessa
    faixa."""
    if len(hits) == 0:
        return float("nan"), float("nan")
    rng = np.random.default_rng(RANDOM_SEED)
    draws = rng.choice(hits, size=(iterations, len(hits)), replace=True).mean(axis=1)
    return float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))


def wilson_ci(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """IC de Wilson para uma proporção (Seção 3.2 do plano).

    Wilson e não Wald: os denominadores aqui são pequenos (28 negativos no
    conjunto de teste) e as proporções ficam perto de 0 ou de 1, faixa em que o
    intervalo de Wald escapa de [0, 1] e subcobre.
    """
    if total == 0:
        return float("nan"), float("nan")
    p = successes / total
    denom = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    half = z * np.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def matthews_corrcoef(pred: Sequence[bool], gold: Sequence[bool]) -> float:
    """MCC entre o rótulo do modelo e o humano.

    Escolhido porque usa as quatro células da matriz de confusão e não infla com
    prevalência desbalanceada: no nosso regime (92,7% de positivos), acurácia e
    F1 premiam quem responde "sim" para tudo, e o MCC não.
    """
    pred = np.asarray(pred, dtype=bool)
    gold = np.asarray(gold, dtype=bool)
    tp = int((pred & gold).sum())
    tn = int((~pred & ~gold).sum())
    fp = int((pred & ~gold).sum())
    fn = int((~pred & gold).sum())
    denom = np.sqrt(float(tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return float("nan") if denom == 0 else (tp * tn - fp * fn) / denom


def _predicted_penalizing_abstention(labels: pd.Series) -> pd.Series:
    """Rótulo previsto sobre TODOS os itens, sem excluir abstenção.

    `incerto` é recodificado como "UBW-verdadeiro" (isto é, como não-alerta).
    Não é uma escolha arbitrária: é a mesma leitura que `_alert_series` já usa
    no resto do script — abstenção conta como ausência de sinalização de falso
    positivo. Do ponto de vista de quem consome a coluna `n_judges_flagged_fp`,
    um juiz que abstém e um juiz que decide "UBW-verdadeiro" produzem o mesmo
    efeito prático: nenhum alerta. A diferença para o kappa "nos decididos" é
    que aqui o item continua no denominador, então abster num item negativo
    conta como erro (o juiz deixou passar o falso positivo), exatamente como
    contaria se ele tivesse dito "UBW-verdadeiro" errado.
    """
    return labels.eq("UBW-verdadeiro") | labels.eq(ABSTAIN_LABEL)


def confusion_2x2(wide: pd.DataFrame, judge: str) -> dict:
    """Matriz de confusão sobre os itens decididos. Positivo = UBW-verdadeiro,
    que é a classe positiva do gabarito humano."""
    gold = wide["is_ubw_gold"].astype(bool)
    labels = wide[f"label__{judge}"]
    decided = labels.isin(["UBW-verdadeiro", ALERT_LABEL])
    pred = labels[decided].eq("UBW-verdadeiro")
    g = gold[decided]
    return {
        "tp": int((pred & g).sum()), "fn": int((~pred & g).sum()),
        "fp": int((pred & ~g).sum()), "tn": int((~pred & ~g).sum()),
    }


def judge_metrics(wide: pd.DataFrame, judges: list[str]) -> pd.DataFrame:
    gold = wide["is_ubw_gold"].astype(bool)
    n_negatives = int((~gold).sum())
    rows = []
    for judge in judges:
        labels = wide[f"label__{judge}"]
        alert = _alert_series(wide, judge).astype(bool)
        decided = labels.isin(["UBW-verdadeiro", ALERT_LABEL])

        confirmed = (~gold)[alert]
        precision = float(confirmed.mean()) if alert.any() else float("nan")
        lo, hi = _bootstrap_ci(confirmed.to_numpy().astype(float)) if alert.any() else (np.nan, np.nan)

        pred_decided = labels[decided].eq("UBW-verdadeiro").tolist()
        gold_decided = gold[decided].tolist()

        # Concordância nas duas direções, com Wilson. São as duas proporções que
        # a Seção 3.2 pede explicitamente: dos que os humanos aceitaram, quantos
        # o juiz aceita; dos que rejeitaram, quantos o juiz rejeita. Reportadas
        # separadas porque a segunda tem denominador de dezenas e é onde tudo se
        # decide neste regime de prevalência.
        cm = confusion_2x2(wide, judge)
        pos_total, neg_total = cm["tp"] + cm["fn"], cm["tn"] + cm["fp"]
        pos_lo, pos_hi = wilson_ci(cm["tp"], pos_total)
        neg_lo, neg_hi = wilson_ci(cm["tn"], neg_total)

        rows.append({
            "juiz": judge,
            "n": len(wide),
            "sem_voto": int(labels.isna().sum()),
            "abstencoes": int(labels.eq(ABSTAIN_LABEL).sum()),
            "alertas": int(alert.sum()),
            "taxa_positivos": float(pd.Series(pred_decided).mean()) if pred_decided else float("nan"),
            "precisao_alerta": precision,
            "ic95_low": lo,
            "ic95_high": hi,
            "cobertura": float(confirmed.sum() / n_negatives) if n_negatives else float("nan"),
            "tp": cm["tp"], "fn": cm["fn"], "fp": cm["fp"], "tn": cm["tn"],
            "conc_positivos": cm["tp"] / pos_total if pos_total else float("nan"),
            "conc_pos_wilson_low": pos_lo, "conc_pos_wilson_high": pos_hi,
            "conc_negativos": cm["tn"] / neg_total if neg_total else float("nan"),
            "conc_neg_wilson_low": neg_lo, "conc_neg_wilson_high": neg_hi,
            "mcc": matthews_corrcoef(pred_decided, gold_decided) if pred_decided else float("nan"),
            "acuracia_decididos": float(np.mean([p == g for p, g in zip(pred_decided, gold_decided)]))
            if pred_decided else float("nan"),
            "kappa": cohens_kappa(pred_decided, gold_decided) if pred_decided else float("nan"),
            "ac1": gwets_ac1(pred_decided, gold_decided) if pred_decided else float("nan"),
            # Mesmo kappa, mas sobre os 200 itens inteiros: abstenção não some do
            # denominador, conta como "não-UBW" quando o gabarito é negativo (o
            # juiz deixou passar) e como acerto quando o gabarito é positivo. Sem
            # isso, quem abstém nos casos difíceis parece concordar mais do que
            # de fato concorda — foi o que inverteu o 1º e o 2º lugar da tabela
            # medida em 2026-08-31/09-01 (deepseek-chat com 48 abstenções liderava
            # no kappa "nos decididos" e cai para trás do kimi-k2.5 aqui).
            "kappa_penalizado": cohens_kappa(
                _predicted_penalizing_abstention(labels).tolist(), gold.tolist()),
        })
    out = pd.DataFrame(rows)
    out["kappa_leitura"] = out["kappa"].map(lambda v: interpret_kappa(v) if pd.notna(v) else "")
    return out.sort_values("precisao_alerta", ascending=False, na_position="last")


def metrics_by_dimension(wide: pd.DataFrame, judges: list[str], column: str,
                         min_items: int = 10) -> pd.DataFrame:
    """QP1: o mesmo desempenho, quebrado por tipo de artefato ou por expressão.

    Estratos com menos de `min_items` são agrupados em "(outros)". Sem isso a
    tabela por expressão vira uma lista de células com dois ou três itens, em que
    a concordância só pode dar 0%, 50% ou 100% e nada disso significa nada —
    lembrando que o gabarito cobre 15 das 25 expressões no desenvolvimento e 16
    no teste.
    """
    counts = wide[column].value_counts()
    keep = set(counts[counts >= min_items].index)
    stratum = wide[column].where(wide[column].isin(keep), "(outros)")

    rows = []
    for judge in judges:
        for value, idx in wide.groupby(stratum).groups.items():
            block = wide.loc[idx]
            gold = block["is_ubw_gold"].astype(bool)
            labels = block[f"label__{judge}"]
            decided = labels.isin(["UBW-verdadeiro", ALERT_LABEL])
            pred = labels[decided].eq("UBW-verdadeiro")
            g = gold[decided]
            n_neg = int((~gold).sum())
            rows.append({
                "juiz": judge,
                column: value,
                "n": len(block),
                "negativos_humanos": n_neg,
                "decididos": int(decided.sum()),
                "acuracia": float((pred == g).mean()) if len(pred) else float("nan"),
                "conc_negativos": float((~pred[~g]).mean()) if (~g).any() else float("nan"),
                "mcc": matthews_corrcoef(pred.tolist(), g.tolist()) if len(pred) else float("nan"),
                "kappa": cohens_kappa(pred.tolist(), g.tolist()) if len(pred) else float("nan"),
            })
    return pd.DataFrame(rows)


def kappa_vs_each_annotator(wide: pd.DataFrame, judges: list[str]) -> pd.DataFrame:
    """Kappa de cada juiz contra CADA anotador individual, não só contra a
    maioria dos três.

    `is_ubw_gold` já é o voto majoritário — comparar o LLM contra ele mede algo
    mais fácil do que o que os 0,844-0,925 reportados entre os humanos medem,
    porque a maioria absorve o ruído de um anotador isolado. Os κ humano-humano
    são par a par (Wendell×Bruno, Wendell×Miguel, Bruno×Miguel); para colocar o
    LLM na mesma régua, ele precisa ser comparado par a par também. As colunas
    `vote__<anotador>` sobrevivem em `gold_dev_200.csv`/`gold_test_385.csv`
    desde a extensão de `GOLD_COLUMNS` em 07_judge_panel.py.

    Também calcula, como referência na mesma linha, o kappa humano-humano médio
    restrito aos itens em que aquele par de humanos e o juiz têm voto — para que
    a comparação não misture denominadores diferentes.
    """
    vote_cols = {a: f"vote__{a}" for a in ANNOTATORS if f"vote__{a}" in wide.columns}
    if not vote_cols:
        logger.warning("nenhuma coluna vote__<anotador> encontrada; rode "
                       "07_judge_panel.py build-gold com a versão atual")
        return pd.DataFrame()

    rows = []
    for judge in judges:
        labels = wide[f"label__{judge}"]
        decided = labels.isin(["UBW-verdadeiro", ALERT_LABEL])
        pred = labels.eq("UBW-verdadeiro")
        pred_penalized = _predicted_penalizing_abstention(labels)  # cobre os 200 inteiros

        per_annotator, per_annotator_penalized = {}, {}
        for annotator, col in vote_cols.items():
            has_vote = wide[col].notna()
            mask = decided & has_vote
            per_annotator[annotator] = (
                cohens_kappa(pred[mask].tolist(), wide.loc[mask, col].astype(bool).tolist())
                if mask.sum() else float("nan")
            )
            per_annotator_penalized[annotator] = (
                cohens_kappa(pred_penalized[has_vote].tolist(),
                            wide.loc[has_vote, col].astype(bool).tolist())
                if has_vote.sum() else float("nan")
            )

        row = {"juiz": judge, **{f"kappa_vs_{a}": v for a, v in per_annotator.items()}}
        vals = [v for v in per_annotator.values() if pd.notna(v)]
        row["kappa_vs_anotador_medio"] = float(np.mean(vals)) if vals else float("nan")
        row["kappa_vs_maioria"] = cohens_kappa(
            pred[decided].tolist(), wide.loc[decided, "is_ubw_gold"].astype(bool).tolist())

        # Mesmas três comparações, mas penalizando abstenção (ver
        # `_predicted_penalizing_abstention`): denominador fixo em todos os
        # itens com voto do anotador, sem excluir quem o juiz não decidiu.
        vals_pen = [v for v in per_annotator_penalized.values() if pd.notna(v)]
        row["kappa_vs_anotador_medio_penalizado"] = float(np.mean(vals_pen)) if vals_pen else float("nan")
        row["kappa_vs_maioria_penalizado"] = cohens_kappa(
            pred_penalized.tolist(), wide["is_ubw_gold"].astype(bool).tolist())
        rows.append(row)
    return pd.DataFrame(rows)


def annotator_pairwise_kappa(wide: pd.DataFrame) -> pd.DataFrame:
    """Kappa humano-humano, par a par, nos mesmos 200/385 itens — a régua de
    referência contra a qual `kappa_vs_each_annotator` deve ser lida."""
    vote_cols = {a: f"vote__{a}" for a in ANNOTATORS if f"vote__{a}" in wide.columns}
    rows = []
    names = list(vote_cols)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            mask = wide[vote_cols[a]].notna() & wide[vote_cols[b]].notna()
            k = cohens_kappa(wide.loc[mask, vote_cols[a]].astype(bool).tolist(),
                             wide.loc[mask, vote_cols[b]].astype(bool).tolist())
            rows.append({"par": f"{a}×{b}", "n": int(mask.sum()), "kappa": k})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Passo 2 — correlação de erro e votos efetivos
# ---------------------------------------------------------------------------


def judge_agreement_matrix(wide: pd.DataFrame, judges: list[str]) -> pd.DataFrame:
    """Kappa juiz-juiz sobre o alerta. Reportado separado do kappa juiz-humano,
    como o OLAF (Mia e Zaman, 2025) recomenda: concordância alta entre modelos
    com concordância baixa contra o humano é viés compartilhado, não acerto."""
    matrix = pd.DataFrame(index=judges, columns=judges, dtype=float)
    for a in judges:
        for b in judges:
            if a == b:
                matrix.loc[a, b] = 1.0
                continue
            matrix.loc[a, b] = cohens_kappa(
                _alert_series(wide, a).astype(bool).tolist(),
                _alert_series(wide, b).astype(bool).tolist(),
            )
    return matrix


def error_correlation(wide: pd.DataFrame, judges: list[str]) -> tuple[pd.DataFrame, float, float]:
    """Correlação entre os vetores de ERRO dos juízes e o número de votos
    efetivamente independentes.

    O erro de um juiz é o indicador de discordar do gabarito humano (abstenção
    conta como erro quando o gabarito é negativo, porque deixou passar um falso
    positivo). O número efetivo sai da fórmula de efeito de desenho
    N_eff = k / (1 + (k-1) * rho), com rho igual à correlação média par a par:
    com erros independentes rho = 0 e N_eff = k; com erros idênticos rho = 1 e
    N_eff = 1, isto é, k juízes valendo um só. É a operacionalização do
    diagnóstico de Kohli (2026), que mediu 2,2 votos efetivos num painel de nove.
    """
    gold = wide["is_ubw_gold"].astype(bool)
    errors = {}
    for judge in judges:
        predicted_ubw = wide[f"label__{judge}"].ne(ALERT_LABEL)  # abstenção = não alertou
        errors[judge] = (predicted_ubw != gold).astype(int)
    err = pd.DataFrame(errors)

    corr = err.corr()
    pairs = [corr.loc[a, b] for i, a in enumerate(judges) for b in judges[i + 1:]]
    pairs = [p for p in pairs if pd.notna(p)]
    rho = float(np.mean(pairs)) if pairs else 0.0
    k = len(judges)
    effective = k / (1 + (k - 1) * rho) if (1 + (k - 1) * rho) > 0 else float(k)
    return corr, rho, float(effective)


# ---------------------------------------------------------------------------
# Passo 3 — regras de agregação
# ---------------------------------------------------------------------------


def _score_alerts(alerts: np.ndarray, gold: np.ndarray) -> dict:
    n_neg = int((~gold).sum())
    flagged = alerts.astype(bool)
    confirmed = (~gold)[flagged]
    return {
        "alertas": int(flagged.sum()),
        "precisao_alerta": float(confirmed.mean()) if flagged.any() else float("nan"),
        "cobertura": float(confirmed.sum() / n_neg) if n_neg else float("nan"),
    }


def _xgboost_aggregator(wide: pd.DataFrame, judges: list[str]) -> Optional[dict]:
    """Agregador treinado sobre os votos, avaliado por validação cruzada
    estratificada interna ao conjunto de desenvolvimento.

    Variáveis: o voto de cada juiz (alerta / neutro / abstenção) mais metadados
    que existem em TODO o corpus (tipo de artefato, expressão do léxico,
    comprimento do texto). Nada que dependa de anotação humana entra aqui — um
    modelo que usasse a justificativa do anotador funcionaria no desenvolvimento
    e não teria como rodar nos 90.873 itens sem rótulo.
    """
    try:
        from sklearn.model_selection import StratifiedKFold
        from xgboost import XGBClassifier
    except ImportError:
        logger.warning("xgboost/sklearn indisponíveis; agregador treinado não avaliado")
        return None

    features = pd.DataFrame(index=wide.index)
    for judge in judges:
        labels = wide[f"label__{judge}"]
        features[f"vote__{judge}"] = np.select(
            [labels.eq(ALERT_LABEL), labels.eq("UBW-verdadeiro")], [1, -1], default=0
        )
    features["n_alertas"] = features[[f"vote__{j}" for j in judges]].eq(1).sum(axis=1)
    features["body_len"] = wide["body_text"].astype(str).str.len()
    for col in ("artifact_type", "matched_expression"):
        features[col] = wide[col].astype("category").cat.codes

    target = (~wide["is_ubw_gold"].astype(bool)).astype(int).to_numpy()  # alvo = é falso positivo
    if target.sum() < 10:
        logger.warning("negativos demais poucos (%d) para validação cruzada", int(target.sum()))
        return None

    predictions = np.zeros(len(target), dtype=int)
    splitter = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
    for train_idx, test_idx in splitter.split(features, target):
        model = XGBClassifier(
            n_estimators=200, max_depth=3, learning_rate=0.1,
            subsample=0.9, colsample_bytree=0.9, eval_metric="logloss",
            scale_pos_weight=float((target == 0).sum() / max(target.sum(), 1)),
            random_state=RANDOM_SEED,
        )
        model.fit(features.iloc[train_idx], target[train_idx])
        predictions[test_idx] = model.predict(features.iloc[test_idx])

    result = _score_alerts(predictions, wide["is_ubw_gold"].astype(bool).to_numpy())
    result["regra"] = "xgboost (CV 5 folds)"
    return result


def aggregation_rules(wide: pd.DataFrame, judges: list[str],
                      best_judge: str) -> pd.DataFrame:
    gold = wide["is_ubw_gold"].astype(bool).to_numpy()
    votes = np.column_stack([_alert_series(wide, j).to_numpy() for j in judges])
    n_alerts = votes.sum(axis=1)

    rows = [
        {"regra": f"melhor juiz sozinho ({best_judge})",
         **_score_alerts(_alert_series(wide, best_judge).to_numpy(), gold)},
        {"regra": "maioria simples", **_score_alerts((n_alerts * 2 > len(judges)).astype(int), gold)},
        {"regra": "ao menos 2 juízes", **_score_alerts((n_alerts >= 2).astype(int), gold)},
        {"regra": "unanimidade", **_score_alerts((n_alerts == len(judges)).astype(int), gold)},
    ]
    trained = _xgboost_aggregator(wide, judges)
    if trained:
        rows.append(trained)
    return pd.DataFrame(rows)[["regra", "alertas", "precisao_alerta", "cobertura"]]


def choose_rule(metrics: pd.DataFrame, rules: pd.DataFrame, effective_votes: float,
                best_judge: str) -> tuple[str, str]:
    """Aplica a tabela do Passo 3. Retorna (regra escolhida, justificativa)."""
    kappas = metrics["kappa"].dropna()
    spread = float(kappas.max() - kappas.min()) if len(kappas) > 1 else 0.0
    best_row = rules[rules["regra"].str.startswith("melhor juiz")].iloc[0]

    if effective_votes < EFFECTIVE_VOTES_FLOOR:
        return (
            f"melhor juiz sozinho ({best_judge})",
            f"votos efetivos = {effective_votes:.2f}, abaixo de {EFFECTIVE_VOTES_FLOOR:.0f}: "
            "os juízes erram nos mesmos itens e o painel é redundante. Agregar seria cosmético.",
        )

    if spread <= KAPPA_SPREAD_TOLERANCE:
        return (
            "maioria simples",
            f"amplitude de kappa entre juízes = {spread:.3f} (≤ {KAPPA_SPREAD_TOLERANCE}), "
            f"confiabilidade parecida, e {effective_votes:.2f} votos efetivos.",
        )

    trained_rows = rules[rules["regra"].str.startswith("xgboost")]
    if len(trained_rows):
        trained = trained_rows.iloc[0]
        if trained["precisao_alerta"] > best_row["precisao_alerta"]:
            return (
                str(trained["regra"]),
                f"confiabilidade desigual (amplitude de kappa = {spread:.3f}) e o agregador "
                f"treinado supera o melhor juiz sozinho na precisão do alerta "
                f"({trained['precisao_alerta']:.3f} contra {best_row['precisao_alerta']:.3f}).",
            )
    return (
        f"melhor juiz sozinho ({best_judge})",
        f"confiabilidade desigual (amplitude de kappa = {spread:.3f}) e nenhum agregador "
        "superou o melhor juiz sozinho na precisão do alerta.",
    )


# ---------------------------------------------------------------------------
# Relatório
# ---------------------------------------------------------------------------


def _fmt(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False, floatfmt=".3f")


def cmd_report(args: argparse.Namespace) -> None:
    wide, judges = load_panel(args.set, args.judges)
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

    metrics = judge_metrics(wide, judges)
    metrics.to_csv(ANALYSIS_DIR / f"{args.set}__judges.csv", index=False)

    # Seleção do painel pelo kappa PENALIZADO, não pelo kappa "nos decididos".
    # Medido em 2026-08-31/09-01: as duas configurações que passavam do corte de
    # 0,60 no kappa não-penalizado eram justamente as de maior abstenção do
    # conjunto (48 e 54 de 200) — abster nos casos difíceis os tirava do
    # denominador e inflava o número. O kappa penalizado mantém os 200 itens
    # fixos no denominador (Seção "abstenção" do plano), então não recompensa
    # quem se recusa a decidir.
    RANK_COLUMN = "kappa_penalizado"
    ranked = metrics.sort_values(RANK_COLUMN, ascending=False, na_position="last")
    survivors = ranked[ranked[RANK_COLUMN] >= KAPPA_ELIMINATION_THRESHOLD]["juiz"].tolist()
    fallback_used = False
    if survivors:
        panel_cap = MAX_PANEL_SIZE
        corte_txt = f"kappa penalizado ≥ {KAPPA_ELIMINATION_THRESHOLD:.2f}"
    else:
        fallback_used = True
        survivors = ranked[ranked[RANK_COLUMN] >= KAPPA_FALLBACK_THRESHOLD]["juiz"].tolist()
        panel_cap = FALLBACK_PANEL_SIZE
        corte_txt = (f"FALLBACK: nenhum juiz atingiu kappa penalizado ≥ {KAPPA_ELIMINATION_THRESHOLD:.2f}, "
                     f"então o painel usa os {FALLBACK_PANEL_SIZE} melhores acima de "
                     f"{KAPPA_FALLBACK_THRESHOLD:.2f}")
        logger.warning("fallback de kappa acionado — nenhum juiz atingiu %.2f",
                       KAPPA_ELIMINATION_THRESHOLD)
        if len(survivors) < FALLBACK_PANEL_SIZE:
            logger.error("nem %d juízes atingiram kappa ≥ %.2f: pelo plano, o experimento "
                         "é reportado como resultado negativo e nenhuma coluna é publicada",
                         FALLBACK_PANEL_SIZE, KAPPA_FALLBACK_THRESHOLD)

    if not survivors:
        raise SystemExit("nenhum juiz acima do limiar de fallback; nada a agregar")

    eliminated = [j for j in judges if j not in survivors]
    panel = survivors[:panel_cap]
    dropped_by_size = survivors[panel_cap:]

    # Kappa contra cada anotador individual, sobre TODOS os juízes (não só o
    # painel): é a mesma régua usada para reportar 0,844-0,925 entre os
    # humanos, e mudar a régua pode reordenar quem passa no corte do Passo 1.
    vs_annotators = kappa_vs_each_annotator(wide, judges)
    if not vs_annotators.empty:
        vs_annotators = vs_annotators.sort_values(
            "kappa_vs_anotador_medio_penalizado", ascending=False)
        vs_annotators.to_csv(ANALYSIS_DIR / f"{args.set}__vs_annotators.csv", index=False)
    human_pairs = annotator_pairwise_kappa(wide)
    human_pairs.to_csv(ANALYSIS_DIR / f"{args.set}__human_pairwise_kappa.csv", index=False)

    # QP1: desempenho por tipo de artefato e por expressão do léxico, restrito ao
    # painel para que a tabela caiba na leitura.
    by_artifact = metrics_by_dimension(wide, panel, "artifact_type")
    by_artifact.to_csv(ANALYSIS_DIR / f"{args.set}__by_artifact.csv", index=False)
    by_expression = metrics_by_dimension(wide, panel, "matched_expression")
    by_expression.to_csv(ANALYSIS_DIR / f"{args.set}__by_expression.csv", index=False)

    agreement = judge_agreement_matrix(wide, panel)
    agreement.to_csv(ANALYSIS_DIR / f"{args.set}__judge_agreement.csv")
    err_corr, rho, effective = error_correlation(wide, panel)
    err_corr.to_csv(ANALYSIS_DIR / f"{args.set}__error_correlation.csv")

    best_judge = metrics[metrics["juiz"].isin(panel)].iloc[0]["juiz"]
    rules = aggregation_rules(wide, panel, best_judge)
    rules.to_csv(ANALYSIS_DIR / f"{args.set}__rules.csv", index=False)
    chosen, reason = choose_rule(metrics[metrics["juiz"].isin(panel)], rules, effective, best_judge)

    gold = wide["is_ubw_gold"].astype(bool)
    lines = [
        f"# Painel de juízes — {args.set}",
        "",
        f"{len(wide)} itens, {int(gold.sum())} positivos e {int((~gold).sum())} negativos "
        f"no gabarito humano (prevalência de positivos: {gold.mean():.1%}).",
        f"{len(judges)} configurações de juiz carregadas de `validation/panel/runs/{args.set}/`.",
        "",
        "## Passo 1 — desempenho individual",
        "",
        _fmt(metrics),
        "",
        f"Corte: {corte_txt}. "
        + (f"Eliminados: {', '.join(eliminated)}." if eliminated else "Nenhum juiz eliminado."),
    ]
    if fallback_used:
        lines += [
            "",
            "> **O painel opera abaixo da barra pretendida.** A barra de kappa ≥ "
            f"{KAPPA_ELIMINATION_THRESHOLD:.2f} foi fixada na faixa dos anotadores humanos "
            "(0,844 a 0,925) e nenhum juiz a alcançou. O fallback estava pré-registrado no "
            "plano antes desta execução. Toda leitura das colunas publicadas precisa "
            "carregar essa ressalva.",
        ]
    if dropped_by_size:
        lines.append(
            f"Teto de {MAX_PANEL_SIZE} juízes (Kohli, 2026), então ficaram de fora: "
            f"{', '.join(dropped_by_size)}."
        )
    lines += [
        f"Painel: {', '.join(panel)}.",
        "",
        "### Kappa contra cada anotador individual",
        "",
        "`is_ubw_gold` já é o voto majoritário dos três — comparar o juiz contra "
        "ele é uma régua mais fácil do que a usada para reportar 0,844 a 0,925 "
        "entre os humanos, que é par a par. Abaixo, o mesmo cálculo par a par "
        "aplicado a cada juiz, ordenado pela média das três comparações "
        "individuais (não pelo kappa contra a maioria).",
        "",
        "Referência — kappa humano-humano, par a par, neste conjunto:",
        "",
        human_pairs.to_markdown(index=False, floatfmt=".3f") if not human_pairs.empty else "(sem votos individuais)",
        "",
        _fmt(vs_annotators) if not vs_annotators.empty else "(sem colunas vote__<anotador> — rode build-gold atualizado)",
        "",
        "### Desempenho por tipo de artefato (QP1)",
        "",
        _fmt(by_artifact),
        "",
        "### Desempenho por expressão do léxico (QP1)",
        "",
        "Estratos com menos de 10 itens agrupados em `(outros)`: o gabarito cobre "
        "apenas parte das 25 expressões, e células de dois ou três itens não "
        "sustentam leitura.",
        "",
        _fmt(by_expression),
        "",
        "## Passo 2 — correlação e votos efetivos",
        "",
        "Kappa juiz-juiz sobre o alerta:",
        "",
        agreement.to_markdown(floatfmt=".3f"),
        "",
        f"Correlação média entre os vetores de erro: {rho:.3f}. "
        f"Votos efetivamente independentes: **{effective:.2f}** de {len(panel)}.",
        "",
        "## Passo 3 — regras de agregação",
        "",
        _fmt(rules),
        "",
        f"**Regra escolhida: {chosen}.** {reason}",
        "",
        "## Passo 4 — detectores externos",
        "",
        "DebtHunter e MT-MoE-BERT não entram na votação: o voto deles é assimétrico "
        "(\"não é SATD\" é evidência forte de falso positivo, \"é SATD\" é evidência fraca). "
        "Saem como coluna própria e como variável do agregador, quando houver.",
        "",
    ]

    # Baselines clássicos, se o script 09 já rodou. Ficam no mesmo relatório para
    # que a comparação "LLM contra classificador de texto puro" seja lida junto
    # com o resto, e não num arquivo separado que ninguém abre.
    baselines_path = ANALYSIS_DIR / f"{args.set}__classical_baselines.csv"
    if baselines_path.exists():
        baselines = pd.read_csv(baselines_path)
        best_kappa = metrics[RANK_COLUMN].max()
        lines += [
            "## Referência — baselines clássicos (Seção 4.2.2 do plano)",
            "",
            "TF-IDF + regressão logística e TF-IDF + XGBoost, treinados do zero por "
            "validação cruzada estratificada repetida dentro deste conjunto. Não são "
            "candidatos ao painel: existem para responder se um classificador de texto "
            "sem conhecimento de mundo chegaria perto dos LLMs.",
            "",
            _fmt(baselines[["modelo", "kappa_medio", "kappa_desvio", "mcc_medio",
                            "alertas", "precisao_alerta", "cobertura"]]),
            "",
            f"Melhor LLM neste conjunto: kappa penalizado **{best_kappa:.3f}**. "
            f"Melhor baseline clássico: **{baselines['kappa_medio'].max():.3f}**. "
            "A diferença é o que justifica usar LLM em vez de um modelo simples.",
            "",
            "Ressalva: com poucos exemplos negativos, cada fold de validação fica com "
            "meia dúzia deles, e a estimativa na classe de interesse é instável. Os números "
            "servem para comparação na mesma escala, não isoladamente.",
            "",
        ]
    report = "\n".join(lines)
    report_path = ANALYSIS_DIR / f"{args.set}__relatorio.md"
    report_path.write_text(report, encoding="utf-8")
    print(report)
    logger.info("relatório em %s", report_path)

    (ANALYSIS_DIR / f"{args.set}__config.json").write_text(json.dumps({
        "conjunto": args.set,
        "juizes_carregados": judges,
        "eliminados_por_kappa": eliminated,
        "painel": panel,
        "melhor_juiz": best_judge,
        "rho_erro_medio": rho,
        "votos_efetivos": effective,
        "regra_escolhida": chosen,
        "justificativa": reason,
    }, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_apply(args: argparse.Namespace) -> None:
    """Aplica uma regra já congelada. É o que roda no conjunto de teste e depois
    no corpus, sem reabrir nenhuma escolha."""
    wide, judges = load_panel(args.set, args.judges)
    votes = np.column_stack([_alert_series(wide, j).to_numpy() for j in judges])
    n_alerts = votes.sum(axis=1)

    if args.rule == "majority":
        alerts = (n_alerts * 2 > len(judges)).astype(int)
    elif args.rule == "unanimity":
        alerts = (n_alerts == len(judges)).astype(int)
    elif args.rule == "at_least_2":
        alerts = (n_alerts >= 2).astype(int)
    elif args.rule == "best_judge":
        if len(judges) != 1:
            raise SystemExit("a regra best_judge exige exatamente um --judges")
        alerts = votes[:, 0]
    else:  # pragma: no cover — argparse já restringe
        raise SystemExit(f"regra desconhecida: {args.rule}")

    out = wide[["item_id"]].copy()
    out["n_judges_flagged_fp"] = n_alerts
    out["flagged_fp"] = alerts.astype(bool)
    out["llm_rationale"] = ""
    out.to_csv(args.out, index=False)
    logger.info("%d de %d itens sinalizados -> %s", int(alerts.sum()), len(out), args.out)

    if "is_ubw_gold" in wide.columns and wide["is_ubw_gold"].notna().all():
        score = _score_alerts(alerts, wide["is_ubw_gold"].astype(bool).to_numpy())
        logger.info("contra o gabarito: precisão do alerta %.3f, cobertura %.3f (%d alertas)",
                    score["precisao_alerta"], score["cobertura"], score["alertas"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_report = sub.add_parser("report", help="protocolo completo da Seção 3.3")
    p_report.add_argument("--set", default="gold_dev_200")
    p_report.add_argument("--judges", nargs="*", help="restringe aos juízes nomeados")

    p_apply = sub.add_parser("apply", help="aplica uma regra congelada")
    p_apply.add_argument("--set", required=True)
    p_apply.add_argument("--judges", nargs="*", required=True)
    p_apply.add_argument("--rule", required=True,
                         choices=["majority", "unanimity", "at_least_2", "best_judge"])
    p_apply.add_argument("--out", required=True)

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    {"report": cmd_report, "apply": cmd_apply}[args.command](args)


if __name__ == "__main__":
    main()
