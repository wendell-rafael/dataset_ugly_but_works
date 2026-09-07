#!/usr/bin/env python3
"""Fase 1e — Junta os batches preenchidos pelos anotadores (formato largo,
um arquivo por pessoa) no formato longo que `03d_precision_report.py` espera
(uma linha por item × anotador, com `sample_stratum` anexado).

Não substitui validação humana nem decide rótulo nenhum — só empilha e
confere. Roda depois que os anotadores devolverem os CSVs preenchidos
(is_ubw, category_confirmed, confidence, observacao) e antes do 03d.

Uso:
    python 03e_merge_annotations.py \
        --plena ../validation/batches_final/batch_A1_plena_oficial_FILLED.csv \
        --plena ../validation/batches_final/batch_A2_plena_oficial_FILLED.csv \
        --plena ../validation/batches_final/batch_A3_desempate_FILLED.csv \
        --stratum-map ../validation/batches_final/_internal_stratum_map_oficial.csv \
        --out ../validation/annotations_long_final.csv

Passe --plena uma vez por arquivo preenchido (2 anotadores primários +,
se houver, o(s) arquivo(s) de desempate gerados por
`03c_generate_batches.py resolve`). Calibração não entra aqui — nunca é
usada no cálculo de precisão (guideline, Seção 3).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402

REQUIRED_FILLED_COLS = {"item_id", "annotator_id", "is_ubw", "category_confirmed", "confidence"}
VALID_IS_UBW = {"True", "False", "true", "false", True, False}
VALID_CONFIDENCE = {"certain", "likely", "uncertain"}


def load_and_validate(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = REQUIRED_FILLED_COLS - set(df.columns)
    if missing:
        raise SystemExit(f"{path}: faltam colunas obrigatórias: {sorted(missing)}")

    empty_is_ubw = df["is_ubw"].isna().sum()
    if empty_is_ubw:
        print(f"AVISO {path.name}: {empty_is_ubw} linha(s) com is_ubw vazio — "
              f"anotador não terminou? Essas linhas ficarão sem par no merge.", file=sys.stderr)

    bad_is_ubw = df[~df["is_ubw"].isin(VALID_IS_UBW) & df["is_ubw"].notna()]
    if len(bad_is_ubw):
        raise SystemExit(f"{path.name}: valores inválidos em is_ubw (esperado True/False): "
                          f"{bad_is_ubw['is_ubw'].unique().tolist()}")

    bad_conf = df[df["confidence"].notna() & ~df["confidence"].isin(VALID_CONFIDENCE)]
    if len(bad_conf):
        print(f"AVISO {path.name}: valores fora do vocabulário esperado em confidence "
              f"({sorted(VALID_CONFIDENCE)}): {bad_conf['confidence'].unique().tolist()}", file=sys.stderr)

    dup_ids = df["item_id"][df["item_id"].duplicated()]
    if len(dup_ids):
        raise SystemExit(f"{path.name}: item_id duplicado dentro do próprio arquivo: "
                          f"{dup_ids.unique().tolist()[:10]}")

    return df


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--plena", action="append", required=True, dest="plena_files",
                   help="Caminho de um CSV de anotação plena preenchido. Repita a flag por arquivo.")
    p.add_argument("--stratum-map", required=True, help="_internal_stratum_map_*.csv de 03c_generate_batches.py.")
    p.add_argument("--out", required=True)
    args = p.parse_args()

    frames = [load_and_validate(Path(fp)) for fp in args.plena_files]
    long_df = pd.concat(frames, ignore_index=True)

    annotators = sorted(long_df["annotator_id"].unique())
    print(f"Anotadores encontrados: {annotators} ({len(long_df)} linhas ao todo)")

    stratum_map = pd.read_csv(args.stratum_map)
    stratum_cols = [c for c in ["item_id", "sample_stratum", "near_miss_flags"] if c in stratum_map.columns]
    merged = long_df.merge(stratum_map[stratum_cols].drop_duplicates("item_id"), on="item_id", how="left")

    missing_stratum = merged["sample_stratum"].isna().sum()
    if missing_stratum:
        print(f"AVISO: {missing_stratum} linha(s) sem sample_stratum correspondente no mapa interno — "
              f"item_id não bate com a amostra oficial? Verifique antes de rodar o 03d.", file=sys.stderr)

    counts_per_item = merged.groupby("item_id")["annotator_id"].nunique()
    single_annotator_items = (counts_per_item == 1).sum()
    if single_annotator_items:
        print(f"Nota: {single_annotator_items} item(ns) com só 1 anotador registrado até agora "
              f"(normal se o desempate ainda não rodou, ou se um anotador não terminou).")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(args.out, index=False)
    print(f"Gravado: {args.out} ({len(merged)} linhas, {merged['item_id'].nunique()} itens únicos)")


if __name__ == "__main__":
    main()
