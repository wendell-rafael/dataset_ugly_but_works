#!/usr/bin/env python3
"""Mineração exploratória de novos candidatos a expressão UBW via padrões
estruturais (regex), em vez de frases fixas.

NÃO faz parte da coleta oficial (script 02) e NÃO altera
`ubw_collected_full.csv` nem o léxico fechado (`ubw/lexicon.py`, Seção 3.1
do plano). É uma ferramenta de descoberta: roda os padrões de
`ubw/patterns.py` sobre uma amostra de repositórios, e produz:

    data/pattern_mining_candidates.csv     -> trechos candidatos, para
                                               checagem manual de precisão
                                               (mesmo espírito da Seção 3.1)
    data/pattern_mining_frequency_report.json -> frequência de "o que vem
                                               antes de works" / "o que vem
                                               depois de but", para ajudar a
                                               propor NOVAS frases literais
                                               ao léxico oficial

Uso típico (amostra de 20 repos, mesmo tamanho do piloto original — Seção 3.1):
    export GITHUB_TOKEN=ghp_xxx
    python 04_pattern_mining.py --repos-csv ../data/repos_to_mine.csv --sample-size 20

Limitação tratada explicitamente: a GitHub Search API não suporta regex.
Para issue/PR/commit, a query é alargada para os `api_keywords` do padrão
(busca por co-ocorrência de palavras, sem exigir adjacência), e o regex
Python preciso é aplicado localmente sobre o `body_text` já baixado. Para
`code_comment`, usa-se regex de verdade via `git grep -E` (filtro frouxo) +
o regex Python (filtro fino), sobre um clone local temporário.
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import random
import re
import shutil
import subprocess
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ubw import lexicon  # noqa: E402
from ubw.envutil import load_dotenv  # noqa: E402
from ubw.github_api import GitHubAPIError, GitHubClient  # noqa: E402
from ubw.patterns import PATTERN_TEMPLATES, extract_slots, find_matches, looks_like_path_context  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ubw.pattern_mining")

GIT_TIMEOUT_SECONDS = 60
GIT_CLONE_TIMEOUT_SECONDS = 600
MAX_API_CANDIDATES_PER_QUERY = 30  # amostra por query, não a coleta inteira


def load_repos(csv_path: Path) -> list[dict]:
    with csv_path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def git_run(repo_dir: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_dir)] + args,
        capture_output=True, text=True, errors="replace", timeout=GIT_TIMEOUT_SECONDS,
    )
    return result.stdout if result.returncode == 0 else ""


def clone_repo(clone_url: str, dest_dir: Path) -> bool:
    if dest_dir.exists():
        return True
    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            ["git", "clone", "--quiet", "--depth", "200", "--filter=blob:limit=1m",
             clone_url, str(dest_dir)],
            capture_output=True, text=True, timeout=GIT_CLONE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        # Sem isto, a exceção escapa sem limpar o clone parcial.
        shutil.rmtree(dest_dir, ignore_errors=True)
        logger.warning("Clone de %s estourou %ds; pulando.", clone_url, GIT_CLONE_TIMEOUT_SECONDS)
        return False
    return result.returncode == 0


# Mineração em code_comment (regex de verdade via git)

_GIT_GREP_MATCH_LINE_RE = re.compile(r"^(.+?):\d+:")


def mine_code_comments(repo_dir: Path, repo_full_name: str) -> list[dict]:
    pathspecs = [f"*{ext}" for ext in lexicon.CODE_EXTENSIONS]
    candidates: list[dict] = []

    for template in PATTERN_TEMPLATES:
        out = git_run(
            repo_dir,
            ["grep", "-n", "-i", "-E", "-C", "1", template.git_ere, "--", *pathspecs],
        )
        if not out.strip():
            continue

        for block in out.split("--\n"):
            lines = [ln for ln in block.splitlines() if ln.strip()]
            if not lines:
                continue
            # A linha do match usa separador ":" (path:lineno:conteúdo); as
            # linhas de contexto ao redor (de -C 1) usam "-" (path-lineno-
            # conteúdo). Quando o match tem uma linha de contexto ANTES
            # dele, lines[0] é uma linha de contexto, não a do match — por
            # isso é preciso procurar a linha certa em vez de assumir a
            # primeira.
            path = None
            for ln in lines:
                m = _GIT_GREP_MATCH_LINE_RE.match(ln)
                if m:
                    path = m.group(1)
                    break
            if path is None:
                continue
            if lexicon.is_vendored_path(path):
                continue

            block_text = "\n".join(lines)
            for span in find_matches(block_text, template):
                if template.kind == "literal_candidate":
                    phrase = template.name.split("::", 1)[1]
                    if looks_like_path_context(span, phrase):
                        continue
                slots = extract_slots(span)
                candidates.append({
                    "repo_full_name": repo_full_name,
                    "artifact_type": "code_comment",
                    "pattern_name": template.name,
                    "matched_span": span,
                    "pre_but": slots.get("pre_but"),
                    "pre_works": slots.get("pre_works"),
                    "post_but": slots.get("post_but"),
                    "context": block_text[:400],
                    "url": f"https://github.com/{repo_full_name}",
                })

    return candidates


# Mineração em issue/PR/commit (query alargada + filtro local)

MAX_SEARCH_QUERY_CHARS = 256


def _max_query_prefix_len() -> int:
    """Maior prefixo de query possível entre os templates (keywords +
    qualificadores fixos), para dimensionar o lote de repositórios —
    mesma técnica de scripts/02_collect_multiartifact.py."""
    return max(
        len(f'{" ".join(t.api_keywords)} in:body type:issue ')
        for t in PATTERN_TEMPLATES
    )


def _repo_lookup(repo_batch: list[dict]) -> dict[str, dict]:
    return {r["repo_full_name"].lower(): r for r in repo_batch}


def _repo_qualifiers(repo_batch: list[dict]) -> str:
    return " ".join(f'repo:{r["repo_full_name"]}' for r in repo_batch)


def build_repo_batches(repos: list[dict]) -> list[list[dict]]:
    """Agrupa repositórios em lotes cujo conjunto de qualificadores
    `repo:...` cabe no teto de 256 caracteres junto do maior prefixo de
    query possível — idêntico em espírito ao script 02, mas dimensionado
    para os templates de ubw/patterns.py em vez do léxico oficial.
    """
    prefix_len = _max_query_prefix_len()
    batches: list[list[dict]] = []
    current: list[dict] = []
    current_len = prefix_len
    for repo in repos:
        qualifier_len = len("repo:") + len(repo["repo_full_name"]) + 1
        if current and current_len + qualifier_len > MAX_SEARCH_QUERY_CHARS:
            batches.append(current)
            current = []
            current_len = prefix_len
        current.append(repo)
        current_len += qualifier_len
    if current:
        batches.append(current)
    return batches


def mine_api_artifact_batched(
    client: GitHubClient, repo_batch: list[dict], is_pr: Optional[bool], is_commit: bool
) -> list[dict]:
    """Minera issue/PR/commit para um LOTE de repositórios — 1 query por
    template cobrindo o lote inteiro, em vez de 1 query por (template,
    repo). Mesma otimização já aplicada em scripts/02_collect_multiartifact.py
    (Seção "Otimização final", 2026-07-03): reduz o número de requisições
    de busca em ~7x, e essa é a fase que domina o tempo total da mineração
    (a Search API tem um teto de throughput por token, imposto pelo
    servidor, que paralelismo não fura).
    """
    candidates: list[dict] = []
    artifact_type = "commit_message" if is_commit else ("pr_body" if is_pr else "issue_body")
    lookup = _repo_lookup(repo_batch)
    qualifiers = _repo_qualifiers(repo_batch)

    for template in PATTERN_TEMPLATES:
        keywords = " ".join(template.api_keywords)
        if is_commit:
            query = f"{keywords} {qualifiers}"
            endpoint, items_key = "/search/commits", "items"
        else:
            type_qualifier = "pr" if is_pr else "issue"
            query = f"{keywords} in:body type:{type_qualifier} {qualifiers}"
            endpoint, items_key = "/search/issues", "items"

        try:
            # client.paginate() é um generator — o request HTTP só acontece
            # quando ele é iterado, então o `for item in ...` precisa estar
            # dentro do try, senão GitHubAPIError escapa sem ser capturado.
            items = client.paginate(
                endpoint, params={"q": query, "per_page": 30},
                is_search=True, items_key=items_key, max_items=MAX_API_CANDIDATES_PER_QUERY,
            )
            for item in items:
                if is_commit:
                    origin = (item.get("repository") or {}).get("full_name", "")
                    body = item.get("commit", {}).get("message", "")
                    url = item.get("html_url", "")
                    artifact_id = item.get("sha", "")
                else:
                    origin = item.get("repository_url", "").split("/repos/", 1)[-1]
                    body = item.get("body") or ""
                    url = item.get("html_url", "")
                    artifact_id = str(item.get("number"))

                repo = lookup.get(origin.lower())
                if repo is None:
                    logger.warning(
                        "Resultado de %s atribuído a repo fora do lote (%s) — ignorado.",
                        artifact_type, origin,
                    )
                    continue
                repo_full_name = repo["repo_full_name"]

                for span in find_matches(body, template):
                    if template.kind == "literal_candidate":
                        phrase = template.name.split("::", 1)[1]
                        if looks_like_path_context(span, phrase):
                            continue
                    slots = extract_slots(span)
                    candidates.append({
                        "repo_full_name": repo_full_name,
                        "artifact_type": artifact_type,
                        "pattern_name": template.name,
                        "matched_span": span,
                        "pre_but": slots.get("pre_but"),
                        "pre_works": slots.get("pre_works"),
                        "post_but": slots.get("post_but"),
                        "context": body[:400].replace("\n", " "),
                        "url": url,
                        "artifact_id": artifact_id,
                    })
        except GitHubAPIError as exc:
            logger.warning(
                "Falha na mineração no lote [%s...] (%s, %s): %s",
                repo_batch[0]["repo_full_name"], artifact_type, template.name, exc,
            )
            continue

    return candidates


def mine_repo_code_comment_worker(repo: dict, clone_root: Path, keep_clones: bool) -> list[dict]:
    """Executado em worker thread do pool: clona e minera code_comment de UM
    repositório. Retorna a lista de candidatos (sem estado compartilhado
    mutável — cada worker devolve os próprios resultados, mesclados no
    thread principal), mesma lógica de paralelização do script 02
    (clone/git grep não têm rate limit externo, ao contrário da Search API).
    """
    repo_full_name = repo["repo_full_name"]
    clone_url = repo.get("clone_url") or f"https://github.com/{repo_full_name}.git"
    repo_dir = clone_root / repo_full_name.replace("/", "__")

    if not clone_repo(clone_url, repo_dir):
        logger.warning("Clone falhou para %s; pulando code_comment na mineração.", repo_full_name)
        return []

    try:
        return mine_code_comments(repo_dir, repo_full_name)
    finally:
        if not keep_clones:
            shutil.rmtree(repo_dir, ignore_errors=True)


# Orquestração

def build_frequency_report(candidates: list[dict]) -> dict:
    by_pattern: dict[str, dict] = {}
    for template in PATTERN_TEMPLATES:
        rows = [c for c in candidates if c["pattern_name"] == template.name]
        pre_but_counter = Counter(c["pre_but"] for c in rows if c.get("pre_but"))
        pre_counter = Counter(c["pre_works"] for c in rows if c.get("pre_works"))
        post_counter = Counter(c["post_but"] for c in rows if c.get("post_but"))
        by_pattern[template.name] = {
            "description": template.description,
            "total_candidates": len(rows),
            "top_pre_but": pre_but_counter.most_common(20),
            "top_pre_works": pre_counter.most_common(20),
            "top_post_but": post_counter.most_common(20),
        }
    return by_pattern


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repos-csv", default="../data/repos_to_mine.csv")
    parser.add_argument("--out-dir", default="../data")
    parser.add_argument("--clone-dir", default="../data/pattern_mining_clones")
    parser.add_argument("--sample-size", type=int, default=20, help="Nº de repositórios (Seção 3.1: piloto = 20).")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--keep-clones", action="store_true")
    parser.add_argument("--github-token", default=None)
    parser.add_argument(
        "--github-tokens", default=None,
        help="Vários tokens separados por vírgula, para rotação (mesma opção do script 02). "
             "Padrão: variável de ambiente GITHUB_TOKENS. Tem prioridade sobre --github-token.",
    )
    parser.add_argument(
        "--parallel-workers", type=int, default=6,
        help="Nº de repositórios minerados em paralelo para code_comment (clone + git grep). "
             "Mesma lógica do script 02: a Search API tem teto de 30 req/min imposto pelo "
             "servidor, então issue/PR/commit continuam sequenciais no thread principal.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    clone_root = Path(args.clone_dir)

    repos = load_repos(Path(args.repos_csv))
    rng = random.Random(args.seed)
    sample = rng.sample(repos, min(args.sample_size, len(repos)))
    logger.info("Amostra de mineração: %d repositórios (seed=%d).", len(sample), args.seed)

    tokens_arg = args.github_tokens or os.environ.get("GITHUB_TOKENS")
    tokens = [t.strip() for t in tokens_arg.split(",") if t.strip()] if tokens_arg else None
    client = GitHubClient(token=args.github_token, tokens=tokens)
    all_candidates: list[dict] = []

    # code_comment (clone + git grep/log) roda em pool de threads, em
    # paralelo com o loop sequencial da API abaixo — mesma estratégia do
    # script 02 (ver seu comentário de "Paralelização" em main()).
    logger.info(
        "Disparando %d workers para code_comment em %d repositórios (em paralelo com o loop da API).",
        args.parallel_workers, len(sample),
    )
    executor = ThreadPoolExecutor(max_workers=args.parallel_workers)
    code_comment_futures = [
        executor.submit(mine_repo_code_comment_worker, repo, clone_root, args.keep_clones)
        for repo in sample
    ]

    candidates_path = out_dir / "pattern_mining_candidates.csv"
    fieldnames = ["repo_full_name", "artifact_type", "pattern_name", "matched_span",
                  "pre_but", "pre_works", "post_but", "context", "url", "artifact_id"]

    def _save_candidates() -> None:
        # Chamado tanto no caminho normal quanto no finally: um erro
        # inesperado em qualquer repositório não deve fazer perder os
        # candidatos já coletados dos demais (todo o resto do script
        # coleta em memória e só grava no fim).
        with candidates_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for c in all_candidates:
                writer.writerow({k: c.get(k, "") for k in fieldnames})
        logger.info("%d candidatos salvos em %s", len(all_candidates), candidates_path)

    try:
        batches = build_repo_batches(sample)
        logger.info(
            "Mineração via API em %d lotes de repositórios (~%.1f repos/lote).",
            len(batches), len(sample) / len(batches),
        )
        for i, batch in enumerate(batches, start=1):
            logger.info("[lote %d/%d] Minerando (API) %d repositórios", i, len(batches), len(batch))
            all_candidates.extend(mine_api_artifact_batched(client, batch, is_pr=False, is_commit=False))
            all_candidates.extend(mine_api_artifact_batched(client, batch, is_pr=True, is_commit=False))
            all_candidates.extend(mine_api_artifact_batched(client, batch, is_pr=None, is_commit=True))
            # Grava a cada lote, não só no finally: um kill externo do
            # processo (não uma exceção Python) não passa pelo finally, e o
            # custo de reescrever o CSV inteiro é desprezível nesse volume.
            _save_candidates()

        logger.info("Loop da API concluído. Aguardando workers de code_comment...")
        for fut in as_completed(code_comment_futures):
            exc = fut.exception()
            if exc is not None:
                logger.error("Worker de code_comment terminou com erro: %s", exc)
            else:
                all_candidates.extend(fut.result())
            _save_candidates()
    finally:
        executor.shutdown(wait=True, cancel_futures=True)
        _save_candidates()

    report = build_frequency_report(all_candidates)
    report_path = out_dir / "pattern_mining_frequency_report.json"
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    logger.info("Relatório de frequência salvo em %s", report_path)

    for name, data in report.items():
        logger.info("Padrão '%s': %d candidatos", name, data["total_candidates"])


if __name__ == "__main__":
    main()
