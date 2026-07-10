#!/usr/bin/env python3
"""Fase 1 — Canonicalização do corpus de repositórios (pré-passo da coleta).

Problema (achado do piloto de 140 repositórios, 2026-07-01/02):
    O snapshot do SEART-GHS guarda o nome do repositório na época da
    indexação. Quando a organização/repositório é renomeado depois disso:

    1. o qualificador `repo:` da Search API NÃO segue o redirect e devolve
       HTTP 422 — 13/140 repositórios ficaram com os artefatos de API
       bloqueados no piloto por isso;
    2. o mesmo repositório pode aparecer DUAS vezes no corpus (nome antigo
       + nome novo), inflando o denominador de RQ1 — pelo menos 4 pares
       duplicados foram identificados no corpus do piloto.

    `git clone` e a REST API (`GET /repos/{owner}/{name}`) seguem o
    redirect normalmente, então dá para resolver o nome canônico atual com
    1 requisição core (5000/h) por repositório, sem tocar na Search API.

Este script lê o CSV de triagem (saída do script 01), resolve o nome
canônico de cada repositório, deduplica pelo nome canônico e grava um CSV
novo com o MESMO schema (ubw.schema.REPOS_TO_MINE_COLUMNS) — os metadados
numéricos do snapshot SEART (stars, commits, etc.) são preservados para
manter a comparabilidade com os critérios de triagem da Seção 2.2; apenas
os campos de identidade (repo_full_name, owner, name, html_url, clone_url)
são atualizados.

Uso:
    export GITHUB_TOKEN=ghp_xxx
    python 05_canonicalize_repos.py \
        --repos-csv ../data/repos_to_mine.csv \
        --out-csv ../data/repos_to_mine_canonical.csv

Saídas:
    repos_to_mine_canonical.csv     -> corpus canônico e deduplicado
    canonicalization_report.json    -> renomeações, duplicatas e mortos
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ubw import schema  # noqa: E402
from ubw.envutil import load_dotenv  # noqa: E402
from ubw.github_api import GitHubAPIError, GitHubClient  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ubw.canonicalize")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repos-csv", default="../data/repos_to_mine.csv")
    parser.add_argument("--out-csv", default="../data/repos_to_mine_canonical.csv")
    parser.add_argument("--report-json", default="../data/canonicalization_report.json")
    parser.add_argument("--github-token", default=None, help="Padrão: variável de ambiente GITHUB_TOKEN.")
    parser.add_argument(
        "--github-tokens", default=None,
        help="Vários tokens separados por vírgula, para rotação (endpoint /repos usa o teto REST "
             "geral de 5000 req/h por token). Padrão: variável de ambiente GITHUB_TOKENS.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tokens_arg = args.github_tokens or os.environ.get("GITHUB_TOKENS")
    tokens = [t.strip() for t in tokens_arg.split(",") if t.strip()] if tokens_arg else None
    client = GitHubClient(token=args.github_token, tokens=tokens)

    with Path(args.repos_csv).open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    logger.info("Carregados %d repositórios de %s", len(rows), args.repos_csv)

    renamed: list[dict] = []
    dead: list[dict] = []
    resolved: list[tuple[str, dict]] = []  # (nome canônico, linha atualizada)

    for i, row in enumerate(rows, start=1):
        original = row["repo_full_name"]
        try:
            live = client.get_repo(original)
        except GitHubAPIError as exc:
            # 404 (apagado/privado), 451 (DMCA), 403 sem rate limit etc.
            logger.warning("[%d/%d] %s inacessível: %s", i, len(rows), original, exc)
            dead.append({"repo_full_name": original, "error": str(exc)[:200]})
            continue

        canonical = live["full_name"]
        if canonical != original:
            logger.info("[%d/%d] RENOMEADO: %s -> %s", i, len(rows), original, canonical)
            renamed.append({"from": original, "to": canonical})
            row = dict(row)
            row["repo_full_name"] = canonical
            row["owner"] = live["owner"]["login"]
            row["name"] = live["name"]
            row["html_url"] = live["html_url"]
            row["clone_url"] = live["clone_url"]
        else:
            logger.info("[%d/%d] ok: %s", i, len(rows), original)
        resolved.append((canonical, row))

    # Deduplicação pelo nome canônico (case-insensitive): mantém a PRIMEIRA
    # ocorrência cujo nome original já era o canônico (linha "nativa"); se
    # nenhuma for nativa, mantém a primeira resolvida.
    by_canonical: dict[str, list[dict]] = {}
    order: list[str] = []
    for canonical, row in resolved:
        key = canonical.lower()
        if key not in by_canonical:
            order.append(key)
        by_canonical.setdefault(key, []).append(row)

    duplicates: list[dict] = []
    final_rows: list[dict] = []
    for key in order:
        group = by_canonical[key]
        if len(group) > 1:
            duplicates.append({
                "canonical": group[0]["repo_full_name"],
                "merged_rows": len(group),
            })
            logger.info(
                "Duplicata no corpus: %s aparecia %d vezes (nomes antigo+novo); mantida 1 linha.",
                group[0]["repo_full_name"], len(group),
            )
        final_rows.append(group[0])

    out_path = Path(args.out_csv)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=schema.REPOS_TO_MINE_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(final_rows)

    report = {
        "input_rows": len(rows),
        "output_rows": len(final_rows),
        "renamed": renamed,
        "duplicates_merged": duplicates,
        "dead": dead,
    }
    Path(args.report_json).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    logger.info(
        "Canonicalização concluída: %d -> %d repositórios (%d renomeados, %d duplicatas fundidas, "
        "%d inacessíveis). Corpus canônico em %s; relatório em %s",
        len(rows), len(final_rows), len(renamed), len(duplicates), len(dead), out_path, args.report_json,
    )


if __name__ == "__main__":
    main()
