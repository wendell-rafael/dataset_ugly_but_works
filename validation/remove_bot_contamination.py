#!/usr/bin/env python3
"""Limpeza retroativa do vazamento de filtro de bot (achado da auditoria de
validação, 2026-07-27): `_is_bot_login` só pegava `[bot]` e uma lista fechada
de nomes, deixando passar 715 registros (0,97% do corpus parcial), 277 só de
`pyup-bot`. O fix em `scripts/02_collect_multiartifact.py` (sufixo -bot/-robot
+ checagem também de `author_name`) só vale para coletas futuras — este
script aplica o mesmo critério, em pós-processamento, sobre um CSV já
coletado, sem re-clonar nem re-minerar nada.

Uso:
    python3 validation/remove_bot_contamination.py <csv_de_entrada> [--apply]

Sem --apply: só relata quantas linhas seriam removidas (dry-run, não
escreve nada). Com --apply: escreve <entrada>.bak (cópia do original) e
sobrescreve o CSV com as linhas de bot removidas.

Não rode --apply em um CSV que está sendo escrito por uma coleta em
andamento — rode só depois que o processo daquele arquivo tiver parado.
"""
from __future__ import annotations

import argparse
import csv
import shutil
import sys
from pathlib import Path

csv.field_size_limit(10_000_000)  # mesmo limite de scripts/02_collect_multiartifact.py

_BOT_LOGIN_EXACT = {"dependabot", "renovate", "github-actions", "greenkeeper", "snyk-bot", "pull"}
_BOT_LOGIN_SUFFIXES = ("-bot", "-robot")


def is_bot(value: str | None) -> bool:
    if not value:
        return False
    lowered = value.lower()
    return "[bot]" in lowered or lowered in _BOT_LOGIN_EXACT or lowered.endswith(_BOT_LOGIN_SUFFIXES)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--apply", action="store_true", help="Escreve o CSV limpo (com backup). Sem isso, só relata.")
    args = parser.parse_args()

    if not args.csv_path.exists():
        print(f"Arquivo não encontrado: {args.csv_path}", file=sys.stderr)
        sys.exit(1)

    with args.csv_path.open("rb") as f:
        raw = f.read().replace(b"\x00", b"")
    rows = list(csv.DictReader(raw.decode("utf-8", errors="replace").splitlines()))

    kept, dropped = [], []
    dropped_by_id: dict[str, int] = {}
    for row in rows:
        login = row.get("author_login")
        name = row.get("author_name")
        bot_id = login if is_bot(login) else (name if is_bot(name) else None)
        if bot_id:
            dropped.append(row)
            dropped_by_id[bot_id] = dropped_by_id.get(bot_id, 0) + 1
        else:
            kept.append(row)

    print(f"Total de linhas: {len(rows)}")
    print(f"Linhas de bot detectadas: {len(dropped)} ({len(dropped) / max(len(rows), 1):.2%})")
    print("Top 10 identificadores de bot por volume:")
    for bot_id, count in sorted(dropped_by_id.items(), key=lambda kv: -kv[1])[:10]:
        print(f"  {bot_id}: {count}")

    if not args.apply:
        print("\nDry-run — nada foi escrito. Rode com --apply para aplicar.")
        return

    backup_path = args.csv_path.with_suffix(args.csv_path.suffix + ".bak_botfilter")
    shutil.copy2(args.csv_path, backup_path)
    print(f"\nBackup do original salvo em: {backup_path}")

    fieldnames = list(rows[0].keys()) if rows else []
    with args.csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(kept)
    print(f"CSV limpo escrito em: {args.csv_path} ({len(kept)} linhas mantidas)")


if __name__ == "__main__":
    main()
