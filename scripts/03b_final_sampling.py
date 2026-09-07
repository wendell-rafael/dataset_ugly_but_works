#!/usr/bin/env python3
"""Fase 1b — Amostra final de validação sobre o corpus CONSOLIDADO.

Não altera `03_metrics_llm_triage.py`; importa `stratified_sample` de lá e
adiciona o que falta (Agente B, `validation/B_PLANO_AUDITORIA_FP.md`, Seção 1-2):

1. **Censo da categoria C** (não amostra proporcional) — com um teto de
   segurança (`--census-cap`) para não estourar o orçamento humano se o
   consolidado A+B trouxer uma Categoria C muito maior do que a observada
   até agora.
2. **Sobre-amostragem por RARIDADE DE EXPRESSÃO** (piso mínimo), não por uma
   lista fixa de nomes de expressão. Duas condições disparam o piso:
   (a) a expressão está em `ubw.lexicon.HIGH_RISK_EXPRESSIONS` (hoje vazio,
       mas o código respeita automaticamente se o léxico for alterado no
       futuro com aval do orientador);
   (b) a contagem total da expressão no corpus consolidado é menor que
       `--watch-rarity-threshold` (default 50) — captura expressões raras
       mesmo em categorias "seguras" (ex.: Categoria A tem `terrible but
       works` com 4 candidatos na fatia A parcial; `magic number` e
       `don't touch`, citadas no mandato original do Agente B, foram
       REMOVIDAS do léxico em 2026-07-01 — ver LEXICO.md — portanto não há
       mais nada para sobre-amostrar com esses nomes especificamente).
   Categoria C já é 100% censo, então o piso de raridade só se aplica a A/B.
3. **Pool de near-miss adversarial**, extraído por heurísticas mecânicas a
   partir dos exemplos NEGATIVOS do `ANNOTATION_GUIDELINE.md` (Seção 6):
   string de teste/fixture, citação de terceiro, negação, remoção/undo,
   diretiva de tooling/arquivo gerado, uso não-técnico.
4. **Correção de população finita** aplicada quando o frame de amostragem
   (N total do corpus consolidado) for menor que 5.000 (Bavota & Russo,
   2016; insumo do Agente A, P2).
5. **Pesos de reponderação** por estrato, gravados em CSV separado, para que
   a precisão global reportada não fique enviesada pela sobre-amostragem
   (insumo do Agente A, P6; Risco 4 do `PLANO_VALIDACAO_COWORK.md`).

GUARDA-CORPO: por padrão o script recusa a rodar com `--label oficial` a
menos que `--confirm-consolidated` seja passado literalmente com o texto
exigido — fricção deliberada para impedir que uma amostra "oficial" seja
gerada por engano sobre um corpus provisório (Risco 2 do plano de
validação: `data/full_run/` ainda não tem `COLLECTION_COMPLETE`).

Subcomandos:
    build   gera as pools de amostra (calibração, censo C, watch-list,
            near-miss, amostra principal A/B) + pesos + manifest

Exemplo (uso real, só depois de consolidar fatia A + fatia B):
    python 03b_final_sampling.py build \
        --candidates ../data/consolidated/ubw_consolidated.csv \
        --label oficial --confirm-consolidated "SIM, A+B consolidados" \
        --out-dir ../validation/sample_final

Exemplo (dry-run / calibração de processo, NUNCA usar como amostra oficial):
    python 03b_final_sampling.py build \
        --candidates ../data/full_run/ubw_collected_full.csv \
        --label calibracao_processo --out-dir ../validation
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import random
import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402

import importlib.util as _ilu  # noqa: E402


def _load_script03():
    """Importa 03_metrics_llm_triage.py por caminho (nome começa com dígito,
    não é importável como módulo normal) sem duplicar sua lógica."""
    path = Path(__file__).resolve().parent / "03_metrics_llm_triage.py"
    spec = _ilu.spec_from_file_location("ubw_script03", path)
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


m03 = _load_script03()

try:
    from ubw.lexicon import HIGH_RISK_EXPRESSIONS  # léxico oficial, hoje vazio
except Exception:  # pragma: no cover - fallback se import falhar
    HIGH_RISK_EXPRESSIONS: set[str] = set()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ubw.final_sampling")

RANDOM_SEED = 42
CONFIRM_TEXT = "SIM, A+B consolidados"

CANDIDATE_KEY_COLS = ("repo_full_name", "artifact_type", "artifact_id", "matched_expression")


def _candidate_key(row: pd.Series) -> str:
    return "|".join(str(row.get(c, "")) for c in CANDIDATE_KEY_COLS)


def finite_population_correction(n: int, N: int) -> int:
    """n_adj = n / (1 + (n-1)/N). Aplicada quando N < 5000 (Seção 5.2 do
    plano; insumo do Agente A, P2; Bavota & Russo, 2016)."""
    if N >= 5000 or N <= 0:
        return n
    n_adj = n / (1 + (n - 1) / N)
    return max(1, min(n, math.ceil(n_adj)))


# --- 1. Near-miss adversarial: heurísticas mecânicas a partir dos negativos
#         do guideline (ANNOTATION_GUIDELINE.md, Seção 6) --------------------

NEAR_MISS_PATTERNS: dict[str, re.Pattern] = {
    # 6.1/6.3 — string de teste, fixture, docstring de terceiros
    "string_teste_fixture": re.compile(r"\b(def\s+test_|assert\s|pytest|fixture|mock)\b", re.I),
    # 6.1 — citação de terceiro ("revisor comentou", "said", "reported")
    "citacao_terceiro": re.compile(
        r"\b(said|commented|reviewer|reopened|reported|according to|called it|revisor comentou)\b", re.I
    ),
    # 6.4 (regra geral, Seção 4 cond. 4) — negação
    "negacao": re.compile(r"\b(not\s+a|isn't\s+a|n't\s+a|never\s+a|no longer\s+a|not really\s+a|não é\s)\b", re.I),
    # 6.2 — remoção/undo do workaround/hack (oposto de manter)
    "remocao_undo": re.compile(
        r"\b(remove[sd]?|deleted?|delete this|root cause fixed|no longer needed|refactor.*remove)\b", re.I
    ),
    # 6.3 — diretiva de tooling / arquivo gerado (ex-"don't touch" removido do léxico, mas o
    # PADRÃO continua existindo em outras expressões, ex. "temp fix" em changelog de bot)
    "tooling_generated": re.compile(r"(AUTO-GENERATED|auto-generated|DO NOT EDIT|codegen|generated by)", re.I),
    # 6.3 — uso não-técnico / organizacional, sem referência a código
    "nao_tecnico": re.compile(r"\b(onboarding|process|workflow|meeting|roadmap|HR)\b", re.I),
}


def flag_near_miss(body_text: object) -> list[str]:
    if not isinstance(body_text, str):
        return []
    return [name for name, pat in NEAR_MISS_PATTERNS.items() if pat.search(body_text)]


def build_near_miss_pool(pool: pd.DataFrame, n_target: int, seed: int) -> pd.DataFrame:
    """Aplica as heurísticas de near-miss e sorteia `n_target` itens,
    distribuindo o alvo por heurística disparada para não deixar uma
    heurística dominar o pool (ex.: 'remocao_undo' é a mais frequente).
    As heurísticas são deliberadamente permissivas (alto recall, baixa
    precisão) — o objetivo é ENRIQUECER o pool candidato a near-miss para
    julgamento humano, não decidir sozinhas; um item flagado pode ser, na
    leitura completa, um verdadeiro positivo que por acaso usa a palavra
    'removed' em outro sentido. Isso é esperado e não é um bug.
    """
    rng = random.Random(seed)
    work = pool.copy()
    work["_near_miss_flags"] = work["body_text"].apply(flag_near_miss)
    flagged = work[work["_near_miss_flags"].map(len) > 0]
    if flagged.empty:
        logger.warning("Nenhum candidato bateu heurística de near-miss adversarial.")
        return flagged.drop(columns=["_near_miss_flags"])

    per_heuristic_target = max(1, n_target // len(NEAR_MISS_PATTERNS))
    picked_idx: set = set()
    for name in NEAR_MISS_PATTERNS:
        subset = flagged[flagged["_near_miss_flags"].apply(lambda fl: name in fl)]
        subset = subset[~subset.index.isin(picked_idx)]
        k = min(per_heuristic_target, len(subset))
        if k <= 0:
            continue
        idx = list(subset.index)
        rng.shuffle(idx)
        picked_idx.update(idx[:k])

    remaining_needed = n_target - len(picked_idx)
    if remaining_needed > 0:
        leftover = flagged[~flagged.index.isin(picked_idx)]
        idx = list(leftover.index)
        rng.shuffle(idx)
        picked_idx.update(idx[:remaining_needed])

    result = flagged.loc[sorted(picked_idx)].copy()
    result["near_miss_flags"] = result["_near_miss_flags"].apply(lambda fl: ";".join(fl))
    result = result.drop(columns=["_near_miss_flags"])
    logger.info("Near-miss adversarial: %d itens selecionados (alvo=%d) de %d flagados.",
                len(result), n_target, len(flagged))
    return result


# --- 2. Sobre-amostragem por raridade de expressão --------------------------

def watch_list_expressions(df: pd.DataFrame, rarity_threshold: int, high_risk: set) -> list[str]:
    """Expressões que merecem piso mínimo próprio: alto risco declarado no
    léxico OU raras no corpus (< rarity_threshold candidatos totais),
    restrito às categorias A/B (C já é censo integral)."""
    ab = df[df["category_ubw"].isin(["A", "B"])]
    counts = ab["matched_expression"].value_counts()
    watch = set(high_risk) & set(counts.index)
    watch |= set(counts[counts < rarity_threshold].index)
    return sorted(watch)


def build_watch_pool(df: pd.DataFrame, expressions: list[str], floor: int, seed: int) -> pd.DataFrame:
    rng = random.Random(seed)
    frames = []
    for expr in expressions:
        sub = df[df["matched_expression"] == expr]
        if len(sub) <= floor:
            frames.append(sub)  # mini-censo: pega tudo
        else:
            idx = list(sub.index)
            rng.shuffle(idx)
            frames.append(sub.loc[idx[:floor]])
    if not frames:
        return df.iloc[0:0]
    return pd.concat(frames)


# --- 3. Orquestração ---------------------------------------------------------

def build_all_pools(
    candidates: pd.DataFrame,
    main_n: int = 385,
    watch_floor: int = 30,
    watch_rarity_threshold: int = 50,
    census_cap: int = 500,
    near_miss_n: int = 100,
    calibration_per_artifact: int = 50,
    seed: int = RANDOM_SEED,
) -> dict[str, pd.DataFrame]:
    df = candidates.copy()
    df["_key"] = df.apply(_candidate_key, axis=1)
    n_total_frame = len(df)

    # 1) Calibração: 50/artefato, sorteada do frame INTEIRO (Seção 3 do
    #    guideline), removida do pool antes de tudo o mais para garantir que
    #    nenhum item apareça em dois lugares do desenho.
    rng = random.Random(seed)
    calib_frames = []
    for artifact_type, group in df.groupby("artifact_type"):
        idx = list(group.index)
        rng.shuffle(idx)
        k = min(calibration_per_artifact, len(idx))
        calib_frames.append(group.loc[idx[:k]])
    calibration = pd.concat(calib_frames) if calib_frames else df.iloc[0:0]
    remaining = df[~df.index.isin(calibration.index)]

    # 2) Censo da categoria C (com teto de segurança).
    census_c_full = remaining[remaining["category_ubw"] == "C"]
    if len(census_c_full) > census_cap:
        logger.warning(
            "Categoria C tem %d itens no consolidado, acima do teto de censo (%d). "
            "Aplicando amostra de %d itens com correção de população finita em vez de "
            "censo integral — decisão registrada, não silenciosa (ver Seção 2 do relatório B).",
            len(census_c_full), census_cap, census_cap,
        )
        n_c = finite_population_correction(census_cap, len(census_c_full))
        idx = list(census_c_full.index)
        rng.shuffle(idx)
        census_c = census_c_full.loc[idx[:n_c]]
        census_c_is_full_census = False
    else:
        census_c = census_c_full
        census_c_is_full_census = True
    remaining = remaining[~remaining.index.isin(census_c.index)]

    # 3) Watch-list (piso mínimo por expressão rara / alto risco), só em A/B.
    watch_exprs = watch_list_expressions(remaining, watch_rarity_threshold, HIGH_RISK_EXPRESSIONS)
    watch_pool = build_watch_pool(remaining, watch_exprs, watch_floor, seed)
    remaining = remaining[~remaining.index.isin(watch_pool.index)]

    # 4) Near-miss adversarial, sobre o pool remanescente (qualquer categoria).
    near_miss = build_near_miss_pool(remaining, near_miss_n, seed)
    remaining = remaining[~remaining.index.isin(near_miss.index)]

    # 5) Amostra principal representativa A/B (proporcional, Seção 5.2 do
    #    plano) — reusa a função já validada do script 03, sem alterá-la.
    ab_pool = remaining[remaining["category_ubw"].isin(["A", "B"])]
    main_n_adj = finite_population_correction(main_n, n_total_frame)
    if main_n_adj != main_n:
        logger.info("Correção de população finita aplicada: N=%d -> n=%d (alvo original %d).",
                     n_total_frame, main_n_adj, main_n)
    main_sample = m03.stratified_sample(ab_pool, total_n=main_n_adj, seed=seed)

    for name, frame in (
        ("calibration", calibration), ("census_c", census_c),
        ("watch", watch_pool), ("near_miss", near_miss), ("main", main_sample),
    ):
        logger.info("Pool '%s': %d itens.", name, len(frame))

    return {
        "calibration": calibration.drop(columns=["_key"], errors="ignore"),
        "census_c": census_c.drop(columns=["_key"], errors="ignore"),
        "watch": watch_pool.drop(columns=["_key"], errors="ignore"),
        "near_miss": near_miss.drop(columns=["_key"], errors="ignore"),
        "main": main_sample.drop(columns=["_key"], errors="ignore"),
        "_meta": {
            "watch_expressions": watch_exprs,
            "census_c_is_full_census": census_c_is_full_census,
            "n_total_frame": n_total_frame,
            "main_n_adjusted": main_n_adj,
        },
    }


def watch_list_expressions_v2(df: pd.DataFrame, rarity_threshold: int, high_risk: set) -> list[str]:
    """Igual a `watch_list_expressions`, mas sobre o léxico inteiro (A, B e
    C), não só A/B — a partir de 2026-07-29 a Categoria C deixou de ter censo
    separado (categoria não é mais dimensão analítica validada, Seção 2 do
    plano), então o piso de raridade por expressão precisa cobrir também as
    expressões que antes ficavam só na Categoria C."""
    counts = df["matched_expression"].value_counts()
    watch = set(high_risk) & set(counts.index)
    watch |= set(counts[counts < rarity_threshold].index)
    return sorted(watch)


def build_all_pools_v2(
    candidates: pd.DataFrame,
    main_n: int = 385,
    watch_floor: int = 30,
    watch_rarity_threshold: int = 50,
    near_miss_n: int = 100,
    calibration_n: int = 200,
    exclude_artifact_types: tuple[str, ...] = ("issue_body",),
    seed: int = RANDOM_SEED,
) -> dict[str, pd.DataFrame]:
    """Reamostragem pós-decisão de reunião de 2026-07-29 com o orientador:
    `issue_body` sai da análise (mediana de tamanho 4x maior que
    `code_comment`, dilui o sinal em texto conversacional — Seção 4.2 da
    Metodologia), e a categoria semântica (A/B/C) deixa de ser dimensão
    analítica validada (a fronteira entre as três famílias não se mostrou
    discriminável de forma confiável nem entre os próprios pesquisadores —
    Seção 2 do plano). Por isso: sem censo separado de Categoria C, sem
    estratificação por categoria em nenhuma pool, estratificação só por tipo
    de artefato. Usa `_key` (não o índice do pandas) para excluir itens já
    sorteados de uma pool do restante, porque `stratified_sample` (script 03)
    reseta o índice ao retornar."""
    df = candidates.copy()
    if exclude_artifact_types:
        n_before = len(df)
        df = df[~df["artifact_type"].isin(exclude_artifact_types)].copy()
        logger.info("Excluídos %d registros de %s (decisão de reunião 2026-07-29).",
                     n_before - len(df), list(exclude_artifact_types))
    df["_key"] = df.apply(_candidate_key, axis=1)
    n_total_frame = len(df)

    # 1) Calibração: agora estratificada por tipo de artefato (proporcional
    #    ao corpus), não mais 50 fixos por artefato — o total 200 vem do
    #    protocolo combinado na reunião (Seção 5.4/Validação da Coleta).
    calibration = m03.stratified_sample(df, total_n=calibration_n, strata_cols=("artifact_type",), seed=seed)
    remaining = df[~df["_key"].isin(calibration["_key"])]

    # 2) Watch-list, agora sobre A, B e C juntos (ver watch_list_expressions_v2).
    watch_exprs = watch_list_expressions_v2(remaining, watch_rarity_threshold, HIGH_RISK_EXPRESSIONS)
    watch_pool = build_watch_pool(remaining, watch_exprs, watch_floor, seed)
    remaining = remaining[~remaining["_key"].isin(watch_pool["_key"])]

    # 3) Near-miss adversarial, sobre o pool remanescente (qualquer categoria).
    near_miss = build_near_miss_pool(remaining, near_miss_n, seed)
    remaining = remaining[~remaining["_key"].isin(near_miss["_key"])]

    # 4) Amostra principal, estratificada só por tipo de artefato (Seção 5.2).
    main_n_adj = finite_population_correction(main_n, n_total_frame)
    if main_n_adj != main_n:
        logger.info("Correção de população finita aplicada: N=%d -> n=%d (alvo original %d).",
                     n_total_frame, main_n_adj, main_n)
    main_sample = m03.stratified_sample(remaining, total_n=main_n_adj, strata_cols=("artifact_type",), seed=seed)

    for name, frame in (
        ("calibration", calibration), ("watch", watch_pool), ("near_miss", near_miss), ("main", main_sample),
    ):
        logger.info("Pool '%s': %d itens.", name, len(frame))

    return {
        "calibration": calibration.drop(columns=["_key"], errors="ignore"),
        "watch": watch_pool.drop(columns=["_key"], errors="ignore"),
        "near_miss": near_miss.drop(columns=["_key"], errors="ignore"),
        "main": main_sample.drop(columns=["_key"], errors="ignore"),
        "_meta": {
            "watch_expressions": watch_exprs,
            "n_total_frame": n_total_frame,
            "main_n_adjusted": main_n_adj,
            "excluded_artifact_types": list(exclude_artifact_types),
        },
    }


def compute_stratum_weights_v2(df_full: pd.DataFrame, exclude_artifact_types: tuple[str, ...]) -> pd.DataFrame:
    """Pesos de reponderação por tipo de artefato (categoria não é mais
    estrato, ver `build_all_pools_v2`). w_h = N_h / N sobre o corpus sem os
    artefatos excluídos."""
    df = df_full[~df_full["artifact_type"].isin(exclude_artifact_types)]
    n_total = len(df)
    rows = []
    for artifact, group in df.groupby("artifact_type"):
        rows.append({"stratum": artifact, "N_population": len(group), "weight": len(group) / n_total})
    return pd.DataFrame(rows)


def compute_stratum_weights(df_full: pd.DataFrame, pools: dict) -> pd.DataFrame:
    """Pesos de reponderação para a precisão global (insumo do Agente A, P6):
    w_h = N_h / N, onde N_h é o tamanho REAL do estrato no corpus e N é o
    total do corpus (excluindo apenas a calibração, que não integra a
    estimativa de precisão por quebra de independência).

    Estratos: cada (category_ubw, artifact_type) para A/B (cobertos pela
    amostra 'main'), mais um estrato único 'C' (censo/quase-censo). O pool
    'watch' e 'near_miss' NÃO entram na reponderação da precisão global —
    são diagnósticos (precisão por expressão rara / especificidade), não
    representativos da população; teriam que ser removidos do denominador
    populacional para não inflar artificialmente a contagem de estratos raros.
    """
    df = df_full[df_full["category_ubw"].isin(["A", "B", "C"])]
    n_total = len(df)
    rows = []
    for (cat, artifact), group in df[df["category_ubw"].isin(["A", "B"])].groupby(
        ["category_ubw", "artifact_type"]
    ):
        rows.append({"stratum": f"{cat}|{artifact}", "N_population": len(group), "weight": len(group) / n_total})
    n_c = len(df[df["category_ubw"] == "C"])
    rows.append({"stratum": "C|censo", "N_population": n_c, "weight": n_c / n_total})
    return pd.DataFrame(rows)


# CLI

def cmd_build(args: argparse.Namespace) -> None:
    if args.label == "oficial" and args.confirm_consolidated != CONFIRM_TEXT:
        raise SystemExit(
            f"Recusado: --label oficial exige --confirm-consolidated \"{CONFIRM_TEXT}\" "
            "(confirmação explícita de que fatia A + fatia B já foram consolidadas — "
            "ver Risco 2 do PLANO_VALIDACAO_COWORK.md). Use --label calibracao_processo "
            "para uma rodada de teste da mecânica."
        )

    candidates = pd.read_csv(args.candidates, low_memory=False)
    pools = build_all_pools(
        candidates, main_n=args.main_n, watch_floor=args.watch_floor,
        watch_rarity_threshold=args.watch_rarity_threshold, census_cap=args.census_cap,
        near_miss_n=args.near_miss_n, calibration_per_artifact=args.calibration_per_artifact,
        seed=args.seed,
    )
    meta = pools.pop("_meta")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"_{args.label}"
    for name, frame in pools.items():
        frame = frame.copy()
        frame["sample_stratum"] = name
        frame.to_csv(out_dir / f"sample_{name}{suffix}.csv", index=False)

    weights = compute_stratum_weights(candidates, pools)
    weights.to_csv(out_dir / f"sampling_weights{suffix}.csv", index=False)

    manifest = {
        "label": args.label,
        "seed": args.seed,
        "candidates_file": str(args.candidates),
        "n_total_frame": meta["n_total_frame"],
        "main_n_adjusted": meta["main_n_adjusted"],
        "watch_expressions": meta["watch_expressions"],
        "census_c_is_full_census": meta["census_c_is_full_census"],
        "pool_sizes": {name: len(frame) for name, frame in pools.items()},
        "params": vars(args),
    }
    manifest["params"] = {k: str(v) for k, v in manifest["params"].items()}
    with (out_dir / f"sampling_manifest{suffix}.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    logger.info("Pools + pesos + manifest gravados em %s (label=%s)", out_dir, args.label)


def cmd_build_v2(args: argparse.Namespace) -> None:
    if args.label == "oficial" and args.confirm_consolidated != CONFIRM_TEXT:
        raise SystemExit(
            f"Recusado: --label oficial exige --confirm-consolidated \"{CONFIRM_TEXT}\"."
        )

    candidates = pd.read_csv(args.candidates, low_memory=False)
    exclude = tuple(a.strip() for a in args.exclude_artifact_types.split(",") if a.strip())
    pools = build_all_pools_v2(
        candidates, main_n=args.main_n, watch_floor=args.watch_floor,
        watch_rarity_threshold=args.watch_rarity_threshold, near_miss_n=args.near_miss_n,
        calibration_n=args.calibration_n, exclude_artifact_types=exclude, seed=args.seed,
    )
    meta = pools.pop("_meta")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"_{args.label}"
    for name, frame in pools.items():
        frame = frame.copy()
        frame["sample_stratum"] = name
        frame.to_csv(out_dir / f"sample_{name}{suffix}.csv", index=False)

    weights = compute_stratum_weights_v2(candidates, exclude)
    weights.to_csv(out_dir / f"sampling_weights{suffix}.csv", index=False)

    manifest = {
        "label": args.label,
        "seed": args.seed,
        "candidates_file": str(args.candidates),
        "methodology_version": "v2_2026-07-29",
        "n_total_frame": meta["n_total_frame"],
        "main_n_adjusted": meta["main_n_adjusted"],
        "watch_expressions": meta["watch_expressions"],
        "excluded_artifact_types": meta["excluded_artifact_types"],
        "category_stratification": False,
        "pool_sizes": {name: len(frame) for name, frame in pools.items()},
        "params": {k: str(v) for k, v in vars(args).items()},
    }
    with (out_dir / f"sampling_manifest{suffix}.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    logger.info("Pools v2 + pesos + manifest gravados em %s (label=%s)", out_dir, args.label)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("build", help="Gera as pools de amostra final.")
    p.add_argument("--candidates", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--label", choices=["oficial", "calibracao_processo"], required=True)
    p.add_argument("--confirm-consolidated", default=None,
                    help=f'Exigido literalmente igual a "{CONFIRM_TEXT}" quando --label oficial.')
    p.add_argument("--main-n", type=int, default=385)
    p.add_argument("--watch-floor", type=int, default=30)
    p.add_argument("--watch-rarity-threshold", type=int, default=50)
    p.add_argument("--census-cap", type=int, default=500)
    p.add_argument("--near-miss-n", type=int, default=100)
    p.add_argument("--calibration-per-artifact", type=int, default=50)
    p.add_argument("--seed", type=int, default=RANDOM_SEED)
    p.set_defaults(func=cmd_build)

    p2 = sub.add_parser(
        "build-v2",
        help="Amostra pós-decisão 2026-07-29: sem issue_body, sem estratificação por categoria.",
    )
    p2.add_argument("--candidates", required=True)
    p2.add_argument("--out-dir", required=True)
    p2.add_argument("--label", choices=["oficial", "calibracao_processo"], required=True)
    p2.add_argument("--confirm-consolidated", default=None,
                     help=f'Exigido literalmente igual a "{CONFIRM_TEXT}" quando --label oficial.')
    p2.add_argument("--main-n", type=int, default=385)
    p2.add_argument("--watch-floor", type=int, default=30)
    p2.add_argument("--watch-rarity-threshold", type=int, default=50)
    p2.add_argument("--near-miss-n", type=int, default=100)
    p2.add_argument("--calibration-n", type=int, default=200)
    p2.add_argument("--exclude-artifact-types", default="issue_body")
    p2.add_argument("--seed", type=int, default=RANDOM_SEED)
    p2.set_defaults(func=cmd_build_v2)

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
