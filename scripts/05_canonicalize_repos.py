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

from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ubw import schema  # noqa: E402
from ubw.envutil import load_dotenv  # noqa: E402
from ubw.github_api import GitHubAPIError, GitHubClient  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

class _TqdmLoggingHandler(logging.Handler):
    """Log via tqdm.write() — sem isso, cada linha de log quebra a barra
    de progresso no meio."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            tqdm.write(self.format(record))
        except Exception:
            self.handleError(record)


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                     handlers=[_TqdmLoggingHandler()])
logger = logging.getLogger("ubw.canonicalize")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repos-csv", default="../data/repos_to_mine.csv")
    parser.add_argument("--out-csv", default="../data/repos_to_mine_canonical.csv")
    parser.add_argument("--report-json", default="../data/canonicalization_report.json")
    parser.add_argument(
        "--checkpoint-file", default=None,
        help="Log append-only de resoluções já feitas (retomada). Padrão: <out-csv>.checkpoint.jsonl",
    )
    parser.add_argument("--github-token", default=None, help="Padrão: variável de ambiente GITHUB_TOKEN.")
    parser.add_argument(
        "--github-tokens", default=None,
        help="Vários tokens separados por vírgula, para rotação (endpoint /repos usa o teto REST "
             "geral de 5000 req/h por token). Padrão: variável de ambiente GITHUB_TOKENS.",
    )
    return parser.parse_args()


def _load_checkpoint(checkpoint_path: Path) -> dict[str, dict]:
    """Carrega resoluções já feitas em execuções anteriores, indexadas pelo
    nome original. Cada linha do checkpoint tem o resultado completo
    (canonical + row atualizada, OU erro se inacessível)."""
    done: dict[str, dict] = {}
    if checkpoint_path.exists():
        with checkpoint_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                done[entry["original"]] = entry
    return done


def main() -> None:
    args = parse_args()
    tokens_arg = args.github_tokens or os.environ.get("GITHUB_TOKENS")
    tokens = [t.strip() for t in tokens_arg.split(",") if t.strip()] if tokens_arg else None
    client = GitHubClient(token=args.github_token, tokens=tokens)

    with Path(args.repos_csv).open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    logger.info("Carregados %d repositórios de %s", len(rows), args.repos_csv)

    checkpoint_path = Path(args.checkpoint_file) if args.checkpoint_file else Path(args.out_csv + ".checkpoint.jsonl")
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    done = _load_checkpoint(checkpoint_path)
    if done:
        logger.info("Checkpoint carregado: %d repositórios já resolvidos em execuções anteriores.", len(done))

    renamed: list[dict] = []
    dead: list[dict] = []
    resolved: list[tuple[str, dict]] = []  # (nome canônico, linha atualizada)

    with checkpoint_path.open("a", encoding="utf-8") as checkpoint_fh:
        for row in tqdm(rows, desc="canonicalização", unit="repo"):
            original = row["repo_full_name"]

            entry = done.get(original)
            if entry is None:
                try:
                    live = client.get_repo(original)
                except GitHubAPIError as exc:
                    # 404 (apagado/privado), 451 (DMCA), 403 sem rate limit etc.
                    entry = {"original": original, "dead": True, "error": str(exc)[:200]}
                else:
                    canonical = live["full_name"]
                    updated_row = dict(row)
                    if canonical != original:
                        updated_row["repo_full_name"] = canonical
                        updated_row["owner"] = live["owner"]["login"]
                        updated_row["name"] = live["name"]
                        updated_row["html_url"] = live["html_url"]
                        updated_row["clone_url"] = live["clone_url"]
                    entry = {"original": original, "dead": False, "canonical": canonical, "row": updated_row}
                checkpoint_fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
                checkpoint_fh.flush()

            if entry["dead"]:
                dead.append({"repo_full_name": original, "error": entry["error"]})
                continue

            canonical = entry["canonical"]
            if canonical != original:
                if not any(r["from"] == original for r in renamed):
                    logger.info("RENOMEADO: %s -> %s", original, canonical)
                    renamed.append({"from": original, "to": canonical})
            resolved.append((canonical, entry["row"]))

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
