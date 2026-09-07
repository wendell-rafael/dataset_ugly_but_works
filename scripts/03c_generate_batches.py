#!/usr/bin/env python3
"""Fase 1c — Geração dos *batches* de anotação a partir das pools da amostra
final (`03b_final_sampling.py`), sem vazar `llm_label` nem a estratégia de
amostragem para o(a) anotador(a) (Agente B, `validation/B_PLANO_AUDITORIA_FP.md`,
Seção 3).

Duas garantias centrais:

1. **Nunca vaza sinal do LLM.** As pools de `03b` vêm de candidatos
   PRÉ-triagem LLM (Seção 5.1 do plano: a amostra de precisão é extraída
   antes do LLM rodar), então normalmente não há `llm_label` para vazar —
   mas o filtro de colunas abaixo é aplicado de forma defensiva mesmo
   assim, para o caso de alguém acidentalmente unir a saída de
   `llm-triage` ao pool antes de gerar os batches.
2. **Nunca vaza a estratégia de amostragem.** As colunas internas
   `sample_stratum` (de qual pool o item veio: amostra principal, censo C,
   sobre-amostragem por raridade, near-miss adversarial) e
   `near_miss_flags` (qual heurística disparou) NUNCA aparecem no CSV que o
   anotador vê — saber que um item foi escolhido a dedo como "provável
   near-miss" enviesaria a decisão. Essas colunas ficam só no arquivo
   interno de rastreio (`_internal_stratum_map_*.csv`), usado depois pelo
   relatório de precisão (`03d_precision_report.py`).

Subcomandos:
    build     gera os batches iniciais (calibração + anotação plena) para
              N anotadores primários, ordem randomizada por anotador
    resolve   a partir de dois CSVs de anotação plena já preenchidos,
              identifica divergências (Seção 7 do guideline, regra 4) e
              gera o batch cego do 3º anotador (desempate)

Exemplo:
    python 03c_generate_batches.py build \
        --pools-dir ../validation/sample_final --label oficial \
        --annotators ana,bruno --out-dir ../validation/batches_final

    python 03c_generate_batches.py resolve \
        --annotator-a ../validation/batches_final/batch_ana_oficial_FILLED.csv \
        --annotator-b ../validation/batches_final/batch_bruno_oficial_FILLED.csv \
        --out ../validation/batches_final/batch_desempate_oficial.csv
"""
from __future__ import annotations

import argparse
import json
import logging
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ubw.generate_batches")

# Colunas que NUNCA podem chegar ao anotador (sinal do LLM ou da estratégia
# de amostragem). Removidas de forma defensiva, mesmo que normalmente já
# não estejam presentes nas pools de 03b (Seção 5.1: amostra é pré-LLM).
FORBIDDEN_COLUMNS = {
    "llm_label", "llm_rationale", "requires_human_review", "human_review_reason",
    "sample_stratum", "near_miss_flags",
}

CANDIDATE_KEY_COLS = ("repo_full_name", "artifact_type", "artifact_id", "matched_expression")

VISIBLE_COLUMNS = [
    "item_id", "repo_full_name", "artifact_type", "matched_expression",
    "category_ubw", "body_text", "created_at", "url",
]

BLANK_ANNOTATION_COLUMNS = ["is_ubw", "category_confirmed", "confidence", "observacao"]

# A partir da reunião de 2026-07-29, categoria semântica deixou de ser
# dimensão analítica validada (Seção 2 do plano) — não é mais tarefa do
# anotador confirmar `category_confirmed`. `build-v2` usa esta lista, sem
# categoria; `build` (desenho antigo) continua com a lista original acima,
# para não quebrar a reprodutibilidade da rodada já documentada.
BLANK_ANNOTATION_COLUMNS_V2 = ["is_ubw", "confidence", "observacao"]

POOL_FILES = ("calibration", "census_c", "watch", "near_miss", "main")


def _item_id(row: pd.Series) -> str:
    return "|".join(str(row.get(c, "")) for c in CANDIDATE_KEY_COLS)


def load_pools(pools_dir: Path, label: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Carrega e concatena as pools de 03b. Retorna (frame_completo_interno,
    frame_visivel_ao_anotador) — o primeiro guarda sample_stratum/near_miss_flags
    para uso interno; o segundo é o que efetivamente vira o CSV do anotador."""
    frames = []
    for name in POOL_FILES:
        path = pools_dir / f"sample_{name}_{label}.csv"
        if not path.exists():
            raise FileNotFoundError(
                f"Pool '{name}' não encontrada em {path}. Rode 03b_final_sampling.py build primeiro."
            )
        df = pd.read_csv(path, low_memory=False)
        df["sample_stratum"] = name  # garante mesmo se a coluna já vier da pool
        frames.append(df)
    full = pd.concat(frames, ignore_index=True)
    full["item_id"] = full.apply(_item_id, axis=1)

    dup = full[full.duplicated("item_id", keep=False)]
    if not dup.empty:
        raise ValueError(
            f"{dup['item_id'].nunique()} item_id duplicados entre pools de 03b — "
            "isso não deveria acontecer (03b remove cada item do pool remanescente "
            "antes de sortear o próximo). Investigar antes de gerar batches."
        )

    visible_cols = [c for c in VISIBLE_COLUMNS if c in full.columns]
    visible = full[visible_cols].copy()
    forbidden_present = FORBIDDEN_COLUMNS & set(full.columns)
    if forbidden_present:
        logger.warning(
            "Colunas proibidas encontradas na pool de entrada e REMOVIDAS antes de "
            "gerar o batch do anotador: %s", sorted(forbidden_present),
        )
    return full, visible


def make_annotator_batch(
    visible: pd.DataFrame, annotator_id: str, seed: int,
    blank_columns: list[str] = BLANK_ANNOTATION_COLUMNS,
) -> pd.DataFrame:
    rng = random.Random(seed)
    idx = list(visible.index)
    rng.shuffle(idx)
    batch = visible.loc[idx].copy().reset_index(drop=True)
    batch.insert(0, "annotator_id", annotator_id)
    for col in blank_columns:
        batch[col] = ""
    assert not (FORBIDDEN_COLUMNS & set(batch.columns)), "vazamento de coluna proibida detectado"
    return batch


POOL_FILES_V2 = ("calibration", "watch", "near_miss", "main")


def load_pools_v2(pools_dir: Path, label: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Igual a `load_pools`, mas sem `census_c` — a partir da reamostragem de
    2026-07-29 (`03b_final_sampling.py build-v2`) não existe censo separado
    de Categoria C."""
    frames = []
    for name in POOL_FILES_V2:
        path = pools_dir / f"sample_{name}_{label}.csv"
        if not path.exists():
            raise FileNotFoundError(
                f"Pool '{name}' não encontrada em {path}. Rode 03b_final_sampling.py build-v2 primeiro."
            )
        df = pd.read_csv(path, low_memory=False)
        df["sample_stratum"] = name
        frames.append(df)
    full = pd.concat(frames, ignore_index=True)
    full["item_id"] = full.apply(_item_id, axis=1)

    dup = full[full.duplicated("item_id", keep=False)]
    if not dup.empty:
        raise ValueError(
            f"{dup['item_id'].nunique()} item_id duplicados entre pools de 03b — investigar."
        )

    visible_cols = [c for c in VISIBLE_COLUMNS if c in full.columns]
    visible = full[visible_cols].copy()
    forbidden_present = FORBIDDEN_COLUMNS & set(full.columns)
    if forbidden_present:
        logger.warning(
            "Colunas proibidas encontradas na pool de entrada e REMOVIDAS antes de "
            "gerar o batch do anotador: %s", sorted(forbidden_present),
        )
    return full, visible


def cmd_build_v2(args: argparse.Namespace) -> None:
    """Protocolo combinado na reunião de 2026-07-29: calibração (todos, com
    discussão depois, fora deste script) -> medição (todos, independente,
    é onde kappa/AC1 valem) -> paralelização (cada anotador cobre um pedaço
    diferente e sem sobreposição, junto com watch/near-miss, que continuam
    diagnósticos e nunca tiveram checagem cruzada mesmo no desenho antigo)."""
    pools_dir = Path(args.pools_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    annotators = [a.strip() for a in args.annotators.split(",") if a.strip()]
    if len(annotators) < 3:
        raise SystemExit("build-v2 exige os 3 anotadores do protocolo combinado na reunião.")

    full, visible = load_pools_v2(pools_dir, args.label)

    calib_visible = visible[full["sample_stratum"] == "calibration"]

    main_mask = full["sample_stratum"] == "main"
    main_ids = list(full.loc[main_mask, "item_id"])
    rng = random.Random(args.seed)
    rng.shuffle(main_ids)
    medicao_ids = set(main_ids[: args.medicao_n])
    paralelizacao_ids = set(main_ids[args.medicao_n:])

    # sample_stratum interno diferencia medição (checagem cruzada, todos
    # anotam) de paralelização (cobertura individual, sem checagem cruzada) —
    # 03d_precision_report.py já sabe separar por sample_stratum.
    full = full.copy()
    full.loc[full["item_id"].isin(medicao_ids), "sample_stratum"] = "main_medicao"
    full.loc[full["item_id"].isin(paralelizacao_ids), "sample_stratum"] = "main_paralelizacao"

    medicao_visible = visible[full["item_id"].isin(medicao_ids)]

    # Decisão do usuário (2026-08-10): sem fatiar. Os 3 anotam os MESMOS 385
    # (200 medição + 185 paralelização, pool 'main' inteiro) — total
    # redundância, não mais 1 anotador por item. watch/near_miss seguem fora
    # dos batches de anotação (pools diagnósticas separadas).
    paralelizacao_visible = visible[full["item_id"].isin(paralelizacao_ids)]

    manifest = {
        "label": args.label, "annotators": annotators, "seed": args.seed,
        "protocolo": "calibracao_medicao_paralelizacao_redundante_2026-08-10",
        "medicao_n": len(medicao_ids), "paralelizacao_n": len(paralelizacao_ids),
        "files": {},
    }
    for i, ann in enumerate(annotators):
        seed_i = args.seed + i + 1
        calib_batch = make_annotator_batch(calib_visible, ann, seed_i, blank_columns=BLANK_ANNOTATION_COLUMNS_V2)

        plena_pool = pd.concat([medicao_visible, paralelizacao_visible], ignore_index=True)
        plena_batch = make_annotator_batch(plena_pool, ann, seed_i + 1000, blank_columns=BLANK_ANNOTATION_COLUMNS_V2)

        calib_path = out_dir / f"batch_{ann}_calibracao_{args.label}.csv"
        plena_path = out_dir / f"batch_{ann}_plena_{args.label}.csv"
        calib_batch.to_csv(calib_path, index=False)
        plena_batch.to_csv(plena_path, index=False)
        manifest["files"][ann] = {
            "calibracao": str(calib_path), "plena": str(plena_path),
            "n_medicao_compartilhado": len(medicao_visible), "n_paralelizacao_compartilhado": len(paralelizacao_visible),
        }
        logger.info("Batch de %s: %d calibração + %d plena (%d medição + %d paralelização, mesmos itens p/ todos).",
                     ann, len(calib_batch), len(plena_batch), len(medicao_visible), len(paralelizacao_visible))

    internal_path = out_dir / f"_internal_stratum_map_{args.label}.csv"
    full[["item_id", "sample_stratum"] + (["near_miss_flags"] if "near_miss_flags" in full.columns else [])].to_csv(
        internal_path, index=False
    )
    manifest["internal_stratum_map"] = str(internal_path)
    manifest["n_calibracao"] = len(calib_visible)

    with (out_dir / f"batches_manifest_{args.label}.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    logger.info("Batches v2 gerados para %d anotadores. Arquivo interno (NÃO enviar): %s",
                 len(annotators), internal_path)


def cmd_build(args: argparse.Namespace) -> None:
    pools_dir = Path(args.pools_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    annotators = [a.strip() for a in args.annotators.split(",") if a.strip()]
    if len(annotators) < 2:
        raise SystemExit("Mínimo de 2 anotadores primários (Seção 5.3 do plano).")

    non_calib_pools = [p for p in POOL_FILES if p != "calibration"]
    if args.pool_assignment:
        with open(args.pool_assignment, encoding="utf-8") as f:
            pool_assignment: dict[str, list[str]] = json.load(f)
        unknown_pools = set(pool_assignment) - set(non_calib_pools)
        if unknown_pools:
            raise SystemExit(f"--pool-assignment cita pool(s) inexistente(s): {sorted(unknown_pools)}")
        uncovered = set(non_calib_pools) - set(pool_assignment)
        if uncovered:
            raise SystemExit(
                f"--pool-assignment não cobre todas as pools de anotação plena: faltam {sorted(uncovered)}. "
                "Toda pool precisa de dono explícito (sem fallback silencioso)."
            )
        for pool, anns in pool_assignment.items():
            if len(anns) < 2 and pool in ("main", "census_c"):
                logger.warning(
                    "Pool '%s' tem só %d anotador(es) — sem dupla independente não dá para "
                    "calcular concordância nem resolver consenso nela (só diagnóstica é aceitável).",
                    pool, len(anns),
                )
    else:
        # Default retrocompatível: todo anotador cobre toda pool de anotação plena.
        pool_assignment = {pool: list(annotators) for pool in non_calib_pools}

    full, visible = load_pools(pools_dir, args.label)

    # Batch de calibração: mesmo item set para TODOS os anotadores (mesmo os que
    # depois só cobrem uma fração da anotação plena), ordem própria por
    # anotador, sessão de discussão é feita depois, fora deste script
    # (Seção 3 do guideline — alinhar critério antes de dividir o trabalho).
    calib_visible = visible[full["sample_stratum"] == "calibration"]

    manifest = {
        "label": args.label, "annotators": annotators, "seed": args.seed,
        "pool_assignment": pool_assignment, "files": {},
    }
    for i, ann in enumerate(annotators):
        seed_i = args.seed + i + 1
        calib_batch = make_annotator_batch(calib_visible, ann, seed_i)

        ann_pools = [pool for pool, anns in pool_assignment.items() if ann in anns]
        ann_visible = visible[full["sample_stratum"].isin(ann_pools)]
        full_batch = make_annotator_batch(ann_visible, ann, seed_i + 1000)

        calib_path = out_dir / f"batch_{ann}_calibracao_{args.label}.csv"
        full_path = out_dir / f"batch_{ann}_plena_{args.label}.csv"
        calib_batch.to_csv(calib_path, index=False)
        full_batch.to_csv(full_path, index=False)
        manifest["files"][ann] = {
            "calibracao": str(calib_path), "plena": str(full_path), "pools_plena": ann_pools,
        }
        logger.info("Batch de %s: %d itens de calibração + %d de anotação plena (pools: %s).",
                     ann, len(calib_batch), len(full_batch), ", ".join(ann_pools))

    # Arquivo interno de rastreio — NÃO entregar ao anotador.
    internal_path = out_dir / f"_internal_stratum_map_{args.label}.csv"
    full[["item_id", "sample_stratum"] + (["near_miss_flags"] if "near_miss_flags" in full.columns else [])].to_csv(
        internal_path, index=False
    )
    manifest["internal_stratum_map"] = str(internal_path)
    manifest["n_calibration"] = len(calib_visible)
    manifest["n_plena_por_pool"] = {
        pool: int((full["sample_stratum"] == pool).sum()) for pool in non_calib_pools
    }

    with (out_dir / f"batches_manifest_{args.label}.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    logger.info(
        "Batches gerados para %d anotadores. Arquivo interno de rastreio (NÃO enviar "
        "ao anotador): %s", len(annotators), internal_path,
    )


def cmd_resolve(args: argparse.Namespace) -> None:
    a = pd.read_csv(args.annotator_a)
    b = pd.read_csv(args.annotator_b)
    a["is_ubw"] = a["is_ubw"].astype(str)
    b["is_ubw"] = b["is_ubw"].astype(str)

    merged = a.merge(b, on="item_id", suffixes=("_a", "_b"))
    disagree_binary = merged["is_ubw_a"] != merged["is_ubw_b"]
    both_true = (merged["is_ubw_a"] == "True") & (merged["is_ubw_b"] == "True")
    disagree_category = both_true & (merged["category_confirmed_a"] != merged["category_confirmed_b"])
    needs_tiebreak = merged[disagree_binary | disagree_category]

    logger.info(
        "Divergência binária (is_ubw): %d itens. Divergência de categoria (ambos TP): %d "
        "itens. Total para desempate (Seção 7, regra 4): %d.",
        disagree_binary.sum(), disagree_category.sum(), len(needs_tiebreak),
    )

    visible_cols = [c for c in VISIBLE_COLUMNS if c in a.columns]
    tiebreak_batch = needs_tiebreak[visible_cols].copy()
    rng = random.Random(args.seed)
    idx = list(tiebreak_batch.index)
    rng.shuffle(idx)
    tiebreak_batch = tiebreak_batch.loc[idx].reset_index(drop=True)
    tiebreak_batch.insert(0, "annotator_id", args.third_annotator)
    for col in BLANK_ANNOTATION_COLUMNS:
        tiebreak_batch[col] = ""
    # O 3º anotador NUNCA vê os rótulos anteriores (Seção 7, regra 4).
    assert not any(c.endswith(("_a", "_b")) for c in tiebreak_batch.columns)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    tiebreak_batch.to_csv(args.out, index=False)
    logger.info("Batch de desempate (%d itens, cego) salvo em %s", len(tiebreak_batch), args.out)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_build = sub.add_parser("build", help="Gera os batches de calibração + anotação plena.")
    p_build.add_argument("--pools-dir", required=True)
    p_build.add_argument("--label", choices=["oficial", "calibracao_processo"], required=True)
    p_build.add_argument("--out-dir", required=True)
    p_build.add_argument("--annotators", default="A1,A2", help="IDs separados por vírgula, mínimo 2.")
    p_build.add_argument("--pool-assignment", default=None,
                          help="JSON opcional {pool: [anotadores]} para dividir a anotação plena por "
                               "pool em vez de todo anotador cobrir tudo. Toda pool de 03b precisa de "
                               "dono explícito. Sem isso, comportamento antigo (todos cobrem tudo).")
    p_build.add_argument("--seed", type=int, default=42)
    p_build.set_defaults(func=cmd_build)

    p_build_v2 = sub.add_parser(
        "build-v2",
        help="Protocolo 2026-07-29: calibração + medição (todos) + paralelização (individual).",
    )
    p_build_v2.add_argument("--pools-dir", required=True)
    p_build_v2.add_argument("--label", choices=["oficial", "calibracao_processo"], required=True)
    p_build_v2.add_argument("--out-dir", required=True)
    p_build_v2.add_argument("--annotators", required=True, help="Exatamente os 3 IDs, separados por vírgula.")
    p_build_v2.add_argument("--medicao-n", type=int, default=200,
                             help="Quantos itens do pool 'main' vão para a etapa de medição (todos anotam).")
    p_build_v2.add_argument("--seed", type=int, default=42)
    p_build_v2.set_defaults(func=cmd_build_v2)

    p_resolve = sub.add_parser("resolve", help="Gera o batch de desempate (3º anotador).")
    p_resolve.add_argument("--annotator-a", required=True)
    p_resolve.add_argument("--annotator-b", required=True)
    p_resolve.add_argument("--out", required=True)
    p_resolve.add_argument("--third-annotator", default="A3")
    p_resolve.add_argument("--seed", type=int, default=7)
    p_resolve.set_defaults(func=cmd_resolve)

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
