#!/usr/bin/env python3
"""Baselines clássicos — Seção 4.2.2 do PLANO_EXPERIMENTO_LLM.md.

TF-IDF + regressão logística e TF-IDF + XGBoost, como referência de comparação
para o painel de LLMs. Não são candidatos ao painel: entram para responder "um
classificador de texto treinado do zero, sem nenhum conhecimento de mundo,
chegaria perto?".

**Avaliação por validação cruzada dentro dos 200, nunca no conjunto de teste.**
O plano descreve "treinar no desenvolvimento e avaliar no teste", mas o teste é
recurso de uso único, reservado para a configuração congelada do painel. Gastá-lo
com baseline seria desperdiçar a única medida independente que temos. A
alternativa aqui — `RepeatedStratifiedKFold` sobre os 200 — é a mesma que o
plano já prevê para o agregador treinado, e dá estimativa honesta sem consumir o
teste.

**Limitação declarada, e é grave.** São 27 exemplos negativos em 200. Com 5
folds, cada fold de validação tem 5 ou 6 negativos. Nenhuma estimativa de
desempenho na classe negativa — que é justamente a classe de interesse — tem
precisão útil nesse regime. Os intervalos reportados são largos de propósito: o
número existe para ser comparado com os LLMs na mesma escala, não para sustentar
afirmação isolada sobre os baselines.

Uso:
    python 09_classical_baselines.py --set gold_dev_200
"""
from __future__ import annotations

import argparse
import importlib.util
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PANEL_DIR = ROOT / "validation" / "panel"
ANALYSIS_DIR = PANEL_DIR / "analysis"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ubw.classical_baselines")

N_SPLITS = 5
N_REPEATS = 5
RANDOM_SEED = 42


def _load_analysis_module():
    """Reaproveita kappa, MCC e Wilson do script 08, para que os baselines sejam
    medidos exatamente com as mesmas fórmulas que os juízes LLM."""
    path = Path(__file__).resolve().parent / "08_panel_analysis.py"
    spec = importlib.util.spec_from_file_location("ubw_panel_analysis", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_pa = _load_analysis_module()
cohens_kappa = _pa.cohens_kappa
matthews_corrcoef = _pa.matthews_corrcoef
wilson_ci = _pa.wilson_ci


def build_models():
    """Os dois baselines do plano. `class_weight`/`scale_pos_weight` existem
    porque a classe negativa é 13,5% do conjunto: sem reponderar, os dois
    modelos aprendem a responder "positivo" para tudo e o alerta nunca dispara."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from xgboost import XGBClassifier

    def vectorizer():
        # Mesma configuração do pool de exemplos em panel_prompts.py: palavra com
        # bigramas. O sinal aqui é lexical, e o corpus de treino tem 200 documentos.
        return TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=2,
                               sublinear_tf=True, max_features=20_000)

    return {
        "tfidf+logreg": Pipeline([
            ("tfidf", vectorizer()),
            ("clf", LogisticRegression(max_iter=2000, class_weight="balanced",
                                       random_state=RANDOM_SEED)),
        ]),
        "tfidf+xgboost": Pipeline([
            ("tfidf", vectorizer()),
            ("clf", XGBClassifier(
                n_estimators=200, max_depth=3, learning_rate=0.1,
                subsample=0.8, colsample_bytree=0.8,
                # 173/27 ≈ 6,4 — sem isso o XGBoost ignora a classe negativa
                scale_pos_weight=1 / 6.4,
                eval_metric="logloss", random_state=RANDOM_SEED, n_jobs=4)),
        ]),
    }


def evaluate(name, pipeline, texts: np.ndarray, gold: np.ndarray) -> dict:
    """Validação cruzada repetida, com as métricas calculadas POR REPETIÇÃO.

    Calcular kappa sobre o pool de todas as predições fora-de-fold misturaria
    repetições e subestimaria a variância. Aqui cada repetição produz um conjunto
    completo de predições fora-de-fold, gera seu próprio kappa/MCC, e o que se
    reporta é a média com o desvio entre repetições — que é a medida honesta de
    quão instável o baseline é neste tamanho de amostra.
    """
    from sklearn.model_selection import StratifiedKFold

    per_repeat = []
    pooled_pred = np.zeros(len(gold), dtype=bool)

    for repeat in range(N_REPEATS):
        splitter = StratifiedKFold(n_splits=N_SPLITS, shuffle=True,
                                   random_state=RANDOM_SEED + repeat)
        pred = np.zeros(len(gold), dtype=bool)
        for train_idx, test_idx in splitter.split(texts, gold):
            pipeline.fit(texts[train_idx], gold[train_idx])
            pred[test_idx] = pipeline.predict(texts[test_idx]).astype(bool)

        per_repeat.append({
            "kappa": cohens_kappa(pred.tolist(), gold.tolist()),
            "mcc": matthews_corrcoef(pred.tolist(), gold.tolist()),
        })
        if repeat == 0:
            pooled_pred = pred.copy()

    kappas = [r["kappa"] for r in per_repeat]
    mccs = [r["mcc"] for r in per_repeat]

    # Matriz de confusão e precisão do alerta vêm da primeira repetição, para que
    # as contagens sejam inteiros de um experimento real e não médias fracionárias.
    alert = ~pooled_pred                     # "alerta" = classificou como não-UBW
    is_negative = ~gold
    n_alerts = int(alert.sum())
    confirmed = int((alert & is_negative).sum())
    prec_lo, prec_hi = wilson_ci(confirmed, n_alerts)

    return {
        "modelo": name,
        "kappa_medio": float(np.mean(kappas)),
        "kappa_desvio": float(np.std(kappas)),
        "mcc_medio": float(np.mean(mccs)),
        "alertas": n_alerts,
        "alertas_confirmados": confirmed,
        "precisao_alerta": confirmed / n_alerts if n_alerts else float("nan"),
        "precisao_wilson_low": prec_lo,
        "precisao_wilson_high": prec_hi,
        "cobertura": confirmed / int(is_negative.sum()) if is_negative.any() else float("nan"),
        "tp": int((pooled_pred & gold).sum()),
        "fn": int((~pooled_pred & gold).sum()),
        "fp": int((pooled_pred & ~gold).sum()),
        "tn": int((~pooled_pred & ~gold).sum()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--set", default="gold_dev_200")
    args = parser.parse_args()

    gold_path = PANEL_DIR / f"{args.set}.csv"
    if not gold_path.exists():
        raise SystemExit(f"conjunto não encontrado: {gold_path}")
    data = pd.read_csv(gold_path).fillna({"body_text": ""})

    texts = data["body_text"].astype(str).to_numpy()
    gold = data["is_ubw_gold"].astype(bool).to_numpy()
    n_neg = int((~gold).sum())
    logger.info("%s: %d itens, %d positivos / %d negativos",
                args.set, len(gold), int(gold.sum()), n_neg)
    if n_neg < N_SPLITS * 2:
        logger.warning("apenas %d negativos para %d folds — cada fold de validação "
                       "terá cerca de %.1f negativos; as estimativas na classe de "
                       "interesse são pouco informativas", n_neg, N_SPLITS, n_neg / N_SPLITS)

    rows = [evaluate(name, pipe, texts, gold) for name, pipe in build_models().items()]
    table = pd.DataFrame(rows)

    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    out = ANALYSIS_DIR / f"{args.set}__classical_baselines.csv"
    table.to_csv(out, index=False)

    show = ["modelo", "kappa_medio", "kappa_desvio", "mcc_medio",
            "alertas", "precisao_alerta", "cobertura"]
    print(table[show].to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    logger.info("gravado em %s", out)


if __name__ == "__main__":
    main()
