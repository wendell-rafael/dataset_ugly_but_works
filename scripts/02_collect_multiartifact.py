#!/usr/bin/env python3
"""Fase 1 — Coleta multi-artefato do léxico UBW (Seção 3.3 / Tabela 3.5).

Lê `repos_to_mine.csv` (saída do script 01) e coleta ocorrências do léxico
UBW (Seção 3.2) em quatro tipos de artefato:

    - issue_body      -> GitHub Search API (/search/issues, type:issue)
    - pr_body         -> GitHub Search API (/search/issues, type:pr)
    - commit_message  -> GitHub Search API (/search/commits)
    - code_comment    -> clonagem local + `git log -S` (pickaxe) + `git show`

Todos os registros são mapeados para o schema da Tabela 3.5
(`ubw.schema.UBWRecord`) e a operacionalização de "remoção" segue
exatamente a Seção 4 do plano (por tipo de artefato).

Saídas (em --out-dir):
    ubw_collected_full.csv          -> todos os registros, todos os repos (RQ1)
    ubw_collected_rq2_subset.csv    -> apenas repos com >= threshold ocorrências (RQ2, Seção 2.4)
    repo_occurrence_counts.csv      -> contagem de ocorrências por repositório
    collection_state.json           -> checkpoint para retomada em caso de interrupção

Uso típico:
    export GITHUB_TOKEN=ghp_xxx
    python 02_collect_multiartifact.py \
        --repos-csv ../data/repos_to_mine.csv \
        --out-dir ../data \
        --clone-dir ../data/clones

Retomada após interrupção: basta rodar o mesmo comando novamente — o
script pula automaticamente (repo, artifact_type) já concluídos, conforme
`collection_state.json`.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ubw import lexicon, schema  # noqa: E402
from ubw.envutil import load_dotenv  # noqa: E402
from ubw.github_api import GitHubAPIError, GitHubClient  # noqa: E402
from ubw.schema import UBWRecord  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ubw.collect")

# Cada expressão do léxico dispara sua própria chamada `git log -S`, então
# o teto é por (repo, expressão) — 300s dá margem para repositórios grandes
# sem travar um worker por horas num caso patológico.
GIT_TIMEOUT_SECONDS = 300
GIT_CLONE_TIMEOUT_SECONDS = 900

# Fixada uma única vez no início da execução, usada para todo cálculo de
# censura/tempo até evento (Seção 3.4 — reprodutibilidade).
COLLECTION_CUTOFF = dt.datetime.now(dt.timezone.utc)


# Utilitários gerais

def parse_iso_datetime(value: Optional[str]) -> Optional[dt.datetime]:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed
    except ValueError:
        return None


def days_between(start: Optional[dt.datetime], end: Optional[dt.datetime]) -> Optional[int]:
    if start is None or end is None:
        return None
    return max(0, (end - start).days)


class CheckpointState:
    """Registra pares (repo_full_name, artifact_type) já coletados, para
    permitir retomar a coleta após interrupção (rate limit, crash, etc.)
    sem duplicar registros no CSV de saída.

    Thread-safe: o pool de workers de `code_comment` (Seção "Paralelização"
    abaixo) chama `mark_done` concorrentemente com o loop principal da API.
    """

    def __init__(self, path: Path):
        self.path = path
        self.completed: set[tuple[str, str]] = set()
        self._lock = threading.Lock()
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            self.completed = {tuple(pair) for pair in data.get("completed", [])}
            logger.info("Checkpoint carregado: %d combinações (repo, artefato) já concluídas.", len(self.completed))

    def is_done(self, repo: str, artifact_type: str) -> bool:
        with self._lock:
            return (repo, artifact_type) in self.completed

    def mark_done(self, repo: str, artifact_type: str) -> None:
        with self._lock:
            self.completed.add((repo, artifact_type))
            self._save()

    def _save(self) -> None:
        # Chamado sempre com self._lock já adquirido.
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"completed": sorted(list(p) for p in self.completed)}, indent=2), encoding="utf-8"
        )


class CSVAppender:
    """Escreve UBWRecords incrementalmente em um CSV (schema Tabela 3.5),
    escrevendo o cabeçalho apenas na primeira vez.

    Thread-safe pelo mesmo motivo do CheckpointState: múltiplos workers de
    `code_comment` escrevem no mesmo arquivo concorrentemente com o loop
    principal da API.
    """

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        write_header = not path.exists() or path.stat().st_size == 0
        self._fh = path.open("a", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._fh, fieldnames=schema.fieldnames())
        self._lock = threading.Lock()
        if write_header:
            self._writer.writeheader()
            self._fh.flush()

    def write(self, records: Iterable[UBWRecord]) -> int:
        records = list(records)
        with self._lock:
            for rec in records:
                self._writer.writerow(rec.to_row())
            self._fh.flush()
        return len(records)

    def close(self) -> None:
        self._fh.close()


def load_repos(csv_path: Path) -> list[dict]:
    with csv_path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def to_int(value) -> Optional[int]:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


# Coleta via Search API (issues, PRs, commit messages) — batched por repo.
#
# A Search API aceita múltiplos qualificadores `repo:` na mesma query, com
# semântica de OR e atribuição do resultado ao repositório de origem. Em vez
# de 1 query por (expressão, repo), a coleta faz 1 query por (expressão,
# LOTE de repos), respeitando o teto de 256 caracteres de `q` — reduz o
# número de requisições em ~8x nessa fase, que domina o tempo total (30
# req/min é limite do servidor, inviolável por paralelismo).

MAX_SEARCH_QUERY_CHARS = 256


def _max_query_prefix_len() -> int:
    """Comprimento do maior prefixo de query possível (expressão mais longa
    + qualificadores fixos mais longos, o caso `in:body type:issue`).
    Usado para montar lotes de repos que valem para TODAS as expressões,
    de modo que o mesmo lote (e portanto o mesmo checkpoint) sirva para a
    coleta inteira.
    """
    return max(
        len(f'"{entry.expression}" in:body type:issue ')
        for entry in lexicon.iter_lexicon()
    )


def build_repo_batches(repos: list[dict]) -> list[list[dict]]:
    """Agrupa repositórios em lotes cujo conjunto de qualificadores
    `repo:...` cabe no teto de 256 caracteres junto do maior prefixo de
    query possível.
    """
    prefix_len = _max_query_prefix_len()
    batches: list[list[dict]] = []
    current: list[dict] = []
    current_len = prefix_len
    for repo in repos:
        qualifier_len = len("repo:") + len(repo["repo_full_name"]) + 1  # +1: espaço separador
        if current and current_len + qualifier_len > MAX_SEARCH_QUERY_CHARS:
            batches.append(current)
            current = []
            current_len = prefix_len
        current.append(repo)
        current_len += qualifier_len
    if current:
        batches.append(current)
    return batches


def _repo_lookup(repo_batch: list[dict]) -> dict[str, dict]:
    """Mapa nome->linha do CSV, case-insensitive (a API preserva o case
    canônico do repositório, que pode diferir do case gravado no CSV)."""
    return {r["repo_full_name"].lower(): r for r in repo_batch}


def _repo_qualifiers(repo_batch: list[dict]) -> str:
    return " ".join(f'repo:{r["repo_full_name"]}' for r in repo_batch)


def _drop_as_path_false_positive(expression: str, text: str) -> bool:
    """Filtro de falso positivo de path (expressões de palavra única, ex:
    "stopgap" em "/Tools/stopGap/gClient.py") — ver lexicon.match_is_path_only.
    """
    return (
        expression in lexicon.PATH_SENSITIVE_EXPRESSIONS
        and lexicon.match_is_path_only(text, expression)
    )


# Artefatos de bots (dependabot/renovate) citam o CHANGELOG de uma
# dependência de terceiro no body — a "admissão" é do autor da dependência,
# não do time do repositório, mesma classe de contaminação do vendoring.
_BOT_LOGIN_EXACT = {"dependabot", "renovate", "github-actions", "greenkeeper", "snyk-bot", "pull"}


def _is_bot_login(login: Optional[str]) -> bool:
    if not login:
        return False
    lowered = login.lower()
    return "[bot]" in lowered or lowered in _BOT_LOGIN_EXACT


def _passes_content_filters(expression: str, text: str, author_login: Optional[str],
                            artifact_type: str, artifact_ref: str, repo_full_name: str) -> bool:
    """Aplica os filtros de precisão da rodada final a um item da Search
    API, com log do motivo do descarte:

    1. autor bot (dependabot etc.) — discurso de terceiro, não do time;
    2. frase do léxico ausente do corpo (a API casa com stemming e com
       conteúdo truncado de changelog) — ver lexicon.expression_in_text;
    3. todas as ocorrências em contexto de path (expressões de 1 palavra).
    """
    if _is_bot_login(author_login):
        logger.info("  [%s] descartado (autor bot %s) em %s %s", artifact_type, author_login, repo_full_name, artifact_ref)
        return False
    if not lexicon.expression_in_text(expression, text):
        logger.info(
            "  [%s] descartado (frase '%s' não literal no corpo; match frouxo da API) em %s %s",
            artifact_type, expression, repo_full_name, artifact_ref,
        )
        return False
    if _drop_as_path_false_positive(expression, text):
        logger.info("  [%s] descartado (FP de path, '%s') em %s %s", artifact_type, expression, repo_full_name, artifact_ref)
        return False
    return True


# Teto de resultados da Search API (100/página x 10 páginas) — usado para
# detectar truncamento silencioso das queries batched abaixo.
SEARCH_API_CAP = 1000


def _build_issue_pr_record(
    item: dict, repo: dict, expression: str, category: str, is_pr: bool, artifact_type: str
) -> Optional[UBWRecord]:
    """Constrói um UBWRecord a partir de UM item da Search API de issues/PRs
    já resolvido para seu repo, aplicando os filtros de conteúdo (retorna
    None se descartado). Compartilhado entre o caminho batched e o fallback
    per-repo do teto de 1000 resultados, para não duplicar essa lógica.
    """
    body = (item.get("body") or "").strip()
    author_login = (item.get("user") or {}).get("login")
    if not _passes_content_filters(
        expression, body, author_login,
        artifact_type, f"#{item.get('number')}", repo["repo_full_name"],
    ):
        return None

    created_at = parse_iso_datetime(item.get("created_at"))
    if is_pr:
        merged_at = parse_iso_datetime(item.get("pull_request", {}).get("merged_at"))
        resolved_at = merged_at or (
            parse_iso_datetime(item.get("closed_at")) if item.get("state") == "closed" else None
        )
    else:
        resolved_at = parse_iso_datetime(item.get("closed_at")) if item.get("state") == "closed" else None

    is_censored = 0 if resolved_at else 1
    effective_end = resolved_at or COLLECTION_CUTOFF

    return UBWRecord(
        repo_full_name=repo["repo_full_name"],
        artifact_type=artifact_type,
        artifact_id=str(item.get("number")),
        matched_expression=expression,
        category_ubw=category,
        body_text=body,
        created_at=created_at.isoformat() if created_at else None,
        removed_at=resolved_at.isoformat() if resolved_at else None,
        is_censored=is_censored,
        time_to_event_days=days_between(created_at, effective_end),
        time_to_event_commits=None,  # não aplicável a issues/PRs
        repo_stars=to_int(repo.get("stars")),
        repo_age_days=None,  # preenchido em enrich_repo_age
        repo_commits=to_int(repo.get("commits")),
        primary_language=repo.get("primary_language"),
        url=item.get("html_url", ""),
        # A Search API de issues/PRs não expõe e-mail do autor
        # (só o login) — ver nota em ubw/schema.py.
        author_name=None,
        author_login=author_login,
        author_email=None,
        author_hash=schema.compute_author_hash(None, author_login, None),
    )


def _build_commit_record(item: dict, repo: dict, expression: str, category: str) -> Optional[UBWRecord]:
    """Análogo a `_build_issue_pr_record`, para itens da Search API de commits."""
    commit_info = item.get("commit", {})
    committer_date = parse_iso_datetime(commit_info.get("committer", {}).get("date"))
    message = commit_info.get("message", "").strip()
    author_login = (item.get("author") or {}).get("login")
    if not _passes_content_filters(
        expression, message, author_login,
        "commit_message", f"@{(item.get('sha') or '')[:10]}", repo["repo_full_name"],
    ):
        return None

    # Commits são imutáveis (Seção 3.3): sempre censurado; o
    # "tempo até evento" é medido até a data de corte da coleta,
    # conforme a nota "(ou data de corte)" da Tabela 3.5.
    return UBWRecord(
        repo_full_name=repo["repo_full_name"],
        artifact_type="commit_message",
        artifact_id=item.get("sha", ""),
        matched_expression=expression,
        category_ubw=category,
        body_text=message,
        created_at=committer_date.isoformat() if committer_date else None,
        removed_at=None,
        is_censored=1,
        time_to_event_days=days_between(committer_date, COLLECTION_CUTOFF),
        time_to_event_commits=None,  # não aplicável (não há "remoção" de commit)
        repo_stars=to_int(repo.get("stars")),
        repo_age_days=None,
        repo_commits=to_int(repo.get("commits")),
        primary_language=repo.get("primary_language"),
        url=item.get("html_url", ""),
        author_name=commit_info.get("author", {}).get("name"),
        author_login=author_login,
        author_email=commit_info.get("author", {}).get("email"),
        author_hash=schema.compute_author_hash(
            commit_info.get("author", {}).get("name"),
            author_login,
            commit_info.get("author", {}).get("email"),
        ),
    )


def collect_issue_or_pr_records_batched(
    client: GitHubClient, repo_batch: list[dict], is_pr: bool
) -> dict[str, list[UBWRecord]]:
    """Coleta issue_body OU pr_body para um LOTE de repositórios: uma query
    por expressão do léxico, cobrindo o lote inteiro. Retorna registros
    agrupados por repo_full_name (como consta no CSV de entrada), para que
    o chamador enriqueça e marque checkpoint por repositório.

    A Search API tem teto de 1000 resultados por query; como a query
    batched cobre ~8 repos com `repo:` OR, eles COMPARTILHAM esse orçamento,
    e com `order=asc` os resultados mais recentes são descartados em
    silêncio se uma expressão comum estourar o teto no lote. Detectamos
    isso (contagem de itens == SEARCH_API_CAP) e refazemos a busca dessa
    expressão um repo de cada vez, substituindo os resultados truncados.
    """
    artifact_type = "pr_body" if is_pr else "issue_body"
    type_qualifier = "pr" if is_pr else "issue"
    lookup = _repo_lookup(repo_batch)
    by_repo: dict[str, list[UBWRecord]] = {r["repo_full_name"]: [] for r in repo_batch}
    qualifiers = _repo_qualifiers(repo_batch)

    for entry in lexicon.iter_lexicon():
        query = f'"{entry.expression}" in:body type:{type_qualifier} {qualifiers}'
        try:
            items = list(client.search_issues_query(query))
        except GitHubAPIError as exc:
            logger.error(
                "Falha ao buscar %s no lote [%s...] (%s): %s",
                artifact_type, repo_batch[0]["repo_full_name"], entry.expression, exc,
            )
            continue

        if len(items) >= SEARCH_API_CAP:
            logger.warning(
                "Teto de %d resultados da Search API atingido para a expressão '%s' no lote "
                "[%s..., %d repos] (%s). Resultados batched descartados; refazendo por "
                "repositório individual para recuperar recall.",
                SEARCH_API_CAP, entry.expression, repo_batch[0]["repo_full_name"],
                len(repo_batch), artifact_type,
            )
            for repo in repo_batch:
                try:
                    repo_items = list(client.search_issues(entry.expression, repo["repo_full_name"], is_pr))
                except GitHubAPIError as exc:
                    logger.error(
                        "Falha ao buscar %s per-repo em %s (%s): %s",
                        artifact_type, repo["repo_full_name"], entry.expression, exc,
                    )
                    continue
                if len(repo_items) >= SEARCH_API_CAP:
                    logger.warning(
                        "Repositório %s sozinho já atinge o teto de %d resultados para '%s' "
                        "(%s) — truncamento inerente à Search API, não recuperável sem "
                        "particionar a query por data.",
                        repo["repo_full_name"], SEARCH_API_CAP, entry.expression, artifact_type,
                    )
                for item in repo_items:
                    record = _build_issue_pr_record(
                        item, repo, entry.expression, entry.category, is_pr, artifact_type
                    )
                    if record is not None:
                        by_repo[repo["repo_full_name"]].append(record)
            continue  # expressão já tratada via fallback per-repo

        for item in items:
            origin = item.get("repository_url", "").split("/repos/", 1)[-1]
            repo = lookup.get(origin.lower())
            if repo is None:
                logger.warning(
                    "Resultado de %s atribuído a repo fora do lote (%s) — ignorado.",
                    artifact_type, origin,
                )
                continue
            record = _build_issue_pr_record(
                item, repo, entry.expression, entry.category, is_pr, artifact_type
            )
            if record is not None:
                by_repo[repo["repo_full_name"]].append(record)

    return by_repo


def collect_commit_message_records_batched(
    client: GitHubClient, repo_batch: list[dict]
) -> dict[str, list[UBWRecord]]:
    """Coleta commit_message para um LOTE de repositórios (ver
    collect_issue_or_pr_records_batched, inclusive o fallback de
    truncamento no teto de 1000 resultados)."""
    lookup = _repo_lookup(repo_batch)
    by_repo: dict[str, list[UBWRecord]] = {r["repo_full_name"]: [] for r in repo_batch}
    qualifiers = _repo_qualifiers(repo_batch)

    for entry in lexicon.iter_lexicon():
        query = f'"{entry.expression}" {qualifiers}'
        try:
            items = list(client.search_commits_query(query))
        except GitHubAPIError as exc:
            logger.error(
                "Falha ao buscar commit_message no lote [%s...] (%s): %s",
                repo_batch[0]["repo_full_name"], entry.expression, exc,
            )
            continue

        if len(items) >= SEARCH_API_CAP:
            logger.warning(
                "Teto de %d resultados da Search API atingido para a expressão '%s' no lote de "
                "commit_message [%s..., %d repos]. Resultados batched descartados; refazendo "
                "por repositório individual para recuperar recall.",
                SEARCH_API_CAP, entry.expression, repo_batch[0]["repo_full_name"], len(repo_batch),
            )
            for repo in repo_batch:
                try:
                    repo_items = list(client.search_commits(entry.expression, repo["repo_full_name"]))
                except GitHubAPIError as exc:
                    logger.error(
                        "Falha ao buscar commit_message per-repo em %s (%s): %s",
                        repo["repo_full_name"], entry.expression, exc,
                    )
                    continue
                if len(repo_items) >= SEARCH_API_CAP:
                    logger.warning(
                        "Repositório %s sozinho já atinge o teto de %d resultados para '%s' "
                        "(commit_message) — truncamento inerente à Search API, não recuperável "
                        "sem particionar a query por data.",
                        repo["repo_full_name"], SEARCH_API_CAP, entry.expression,
                    )
                for item in repo_items:
                    record = _build_commit_record(item, repo, entry.expression, entry.category)
                    if record is not None:
                        by_repo[repo["repo_full_name"]].append(record)
            continue  # expressão já tratada via fallback per-repo

        for item in items:
            origin = (item.get("repository") or {}).get("full_name", "")
            repo = lookup.get(origin.lower())
            if repo is None:
                logger.warning(
                    "Resultado de commit_message atribuído a repo fora do lote (%s) — ignorado.",
                    origin,
                )
                continue
            record = _build_commit_record(item, repo, entry.expression, entry.category)
            if record is not None:
                by_repo[repo["repo_full_name"]].append(record)

    return by_repo


# Coleta: Comentários de código (clone local + git pickaxe)

def git_run(repo_dir: Path, args: list[str], check: bool = False, timeout: int = GIT_TIMEOUT_SECONDS) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_dir)] + args,
        capture_output=True, text=True, errors="replace", timeout=timeout,
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} falhou em {repo_dir}: {result.stderr[:500]}")
    return result.stdout


GIT_CLONE_MAX_RETRIES = 4
GIT_CLONE_BACKOFF_BASE_SECONDS = 5.0


# O clone é SEMPRE completo (sem --depth): a Seção 4 precisa do histórico
# inteiro para achar o commit de introdução do comentário, que pode ser bem
# mais antigo que os últimos N commits — um clone raso quebraria o cálculo
# de time_to_event. `--filter=blob:limit=1m` faz clonagem parcial (árvores/
# commits completos, blobs >1MB sob demanda — nenhum arquivo de código-fonte
# real passa disso) para reduzir volume transferido em repos com muito
# asset binário no histórico; não é garantia (repo com muitos arquivos
# pequenos ainda pode estourar o timeout), daí a captura de TimeoutExpired
# abaixo para falhar limpo em vez de deixar clone parcial pra trás.
GIT_CLONE_BLOB_SIZE_LIMIT = "1m"


def clone_repo(clone_url: str, dest_dir: Path) -> bool:
    if dest_dir.exists():
        logger.info("Clone já existe em %s, reutilizando.", dest_dir)
        return True
    dest_dir.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(1, GIT_CLONE_MAX_RETRIES + 1):
        logger.info("Clonando %s (tentativa %d/%d) ...", clone_url, attempt, GIT_CLONE_MAX_RETRIES)
        try:
            result = subprocess.run(
                ["git", "clone", "--quiet", f"--filter=blob:limit={GIT_CLONE_BLOB_SIZE_LIMIT}",
                 clone_url, str(dest_dir)],
                capture_output=True, text=True, timeout=GIT_CLONE_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            # Sem capturar aqui, o diretório parcial nunca é limpo e uma
            # retomada futura reaproveitaria um clone corrompido cegamente
            # (`if dest_dir.exists(): reutiliza`, sem checar integridade).
            shutil.rmtree(dest_dir, ignore_errors=True)
            # Repositório genuinamente grande vai estourar de novo com o
            # mesmo teto — falha direto em vez de gastar as retries.
            logger.error(
                "Clone de %s estourou %ds mesmo com --filter=blob:limit=%s "
                "(repositório provavelmente muito grande). Desistindo; ficará "
                "pendente para uma retomada com timeout maior, se necessário.",
                clone_url, GIT_CLONE_TIMEOUT_SECONDS, GIT_CLONE_BLOB_SIZE_LIMIT,
            )
            return False

        if result.returncode == 0:
            return True

        # Limpa clone parcial antes de tentar de novo, senão o próximo
        # `git clone` falha por o diretório de destino já existir.
        shutil.rmtree(dest_dir, ignore_errors=True)

        stderr_lower = result.stderr.lower()
        transient = any(
            marker in stderr_lower
            for marker in ("could not resolve host", "temporary failure", "timed out",
                            "connection reset", "unable to access", "recv failure")
        )
        if not transient or attempt == GIT_CLONE_MAX_RETRIES:
            logger.error("Falha ao clonar %s: %s", clone_url, result.stderr[:500])
            return False

        wait = GIT_CLONE_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
        logger.warning("Falha transitória ao clonar %s: %s. Aguardando %.0fs.",
                        clone_url, result.stderr.strip()[:200], wait)
        time.sleep(wait)

    return False


def get_first_commit_date(repo_dir: Path) -> Optional[dt.datetime]:
    out = git_run(repo_dir, ["log", "--reverse", "--pretty=format:%aI", "-1"])
    return parse_iso_datetime(out.strip()) if out.strip() else None


def commit_count_between(repo_dir: Path, sha_a: str, sha_b: str, path: str) -> Optional[int]:
    out = git_run(repo_dir, ["rev-list", "--count", f"{sha_a}..{sha_b}", "--", path])
    return to_int(out.strip()) if out.strip() else None


_DIFF_FILE_RE = re.compile(r"^diff --git a/(.+) b/(.+)$", re.MULTILINE)


_HUNK_HEADER_RE = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def parse_diff_hunks(diff_text: str) -> list[tuple[str, list[tuple[str, str, int]]]]:
    """Faz o parsing de uma saída de `git show --unified=0` em blocos por
    arquivo, retornando (path, [(sinal, texto_da_linha, numero_da_linha), ...]).

    O número da linha é lido do cabeçalho do hunk (`@@ -a,b +c,d @@`) e
    incrementado a cada linha do lado correspondente (old/new) — é isto que
    alimenta `artifact_id = filepath:line` (Tabela 3.5), em vez de um
    identificador sem número de linha.

    Heurística de regex sobre texto de diff — não é um parser completo do
    formato unified diff (não trata renomes com similarity index, por
    exemplo), mas é suficiente para localizar linhas adicionadas/removidas
    que contêm uma expressão do léxico.
    """
    matches = list(_DIFF_FILE_RE.finditer(diff_text))
    blocks: list[tuple[str, list[tuple[str, str, int]]]] = []
    for i, m in enumerate(matches):
        path = m.group(2)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(diff_text)
        body = diff_text[start:end]
        lines: list[tuple[str, str, int]] = []
        old_line = new_line = 0
        for line in body.splitlines():
            hunk_match = _HUNK_HEADER_RE.match(line)
            if hunk_match:
                old_line = int(hunk_match.group(1))
                new_line = int(hunk_match.group(2))
                continue
            if line.startswith("+++") or line.startswith("---"):
                continue
            if line.startswith("+"):
                lines.append(("+", line[1:], new_line))
                new_line += 1
            elif line.startswith("-"):
                lines.append(("-", line[1:], old_line))
                old_line += 1
        blocks.append((path, lines))
    return blocks


class RawEvent:
    __slots__ = ("path", "sha", "date", "sign", "expression", "category", "text", "line_no",
                 "author_name", "author_email")

    def __init__(self, path, sha, date, sign, expression, category, text, line_no,
                 author_name=None, author_email=None):
        self.path = path
        self.sha = sha
        self.date = date
        self.sign = sign
        self.expression = expression
        self.category = category
        self.text = text
        self.line_no = line_no
        self.author_name = author_name
        self.author_email = author_email


def find_raw_events_for_expression(
    repo_dir: Path, expression: str, category: str, pathspecs: list[str]
) -> list[RawEvent]:
    """Localiza, em todo o histórico (todas as branches), commits onde a
    contagem de ocorrências da expressão mudou (`git log -S`), e extrai as
    linhas adicionadas/removidas correspondentes via `git show`.

    Autor (nome/e-mail) vem junto no mesmo `git log` — dado local, sem
    custo de API extra (Seção "identidade do autor", 2026-07-08). Usa
    "\\x1f" (unit separator) em vez de "|" para separar os campos: nome de
    commit pode conter "|" (raro, mas possível), "\\x1f" nunca aparece em
    texto digitado por humano.
    """
    log_out = git_run(
        repo_dir,
        ["log", "--all", "--pretty=format:%H%x1f%aI%x1f%an%x1f%ae", "-S", expression, "--", *pathspecs],
        timeout=GIT_TIMEOUT_SECONDS,
    )
    events: list[RawEvent] = []
    commit_lines = [ln for ln in log_out.splitlines() if ln.strip()]

    for line in commit_lines:
        parts = line.split("\x1f")
        if len(parts) != 4:
            continue
        sha, date_str, author_name, author_email = parts
        date = parse_iso_datetime(date_str)
        if date is None:
            continue
        diff_out = git_run(
            repo_dir, ["show", sha, "--unified=0", "--pretty=format:", "--", *pathspecs],
            timeout=GIT_TIMEOUT_SECONDS,
        )
        for path, changed_lines in parse_diff_hunks(diff_out):
            if lexicon.is_vendored_path(path):
                continue
            extension = "." + path.rsplit(".", 1)[-1] if "." in path else ""
            for sign, text, line_no in changed_lines:
                # expression_in_text tem fronteira de palavra (evita, ex.,
                # "stopgap" casando dentro de "histopgap"); `text` aqui é
                # sempre uma única linha de diff, checagem por linha não perde nada.
                if not lexicon.expression_in_text(expression, text):
                    continue
                if not lexicon.looks_like_comment(text, extension):
                    continue
                # FP de path em expressão de palavra única (ex: comentário
                # citando "tools/stopgap/x.py") — ver lexicon.match_is_path_only.
                if _drop_as_path_false_positive(expression, text):
                    continue
                events.append(RawEvent(path, sha, date, sign, expression, category, text.strip()[:500], line_no,
                                        author_name=author_name, author_email=author_email))

    return events


def get_context_window(repo_dir: Path, sha: str, path: str, line_no: int, context: int = 3) -> str:
    """Janela de +/-`context` linhas ao redor de `line_no`, lida do
    conteúdo do arquivo no commit `sha` (Tabela 3.5: "janela de +/-3 linhas
    para code_comment"). `line_no` é 1-indexado, como nos hunks de diff.

    Usa o conteúdo no commit de introdução (não em HEAD), para que o
    contexto capturado seja estável mesmo que o arquivo mude depois —
    consistente com `created_at` vindo do mesmo commit.
    """
    result = subprocess.run(
        ["git", "-C", str(repo_dir), "show", f"{sha}:{path}"],
        capture_output=True, text=True, errors="replace", timeout=GIT_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        return ""
    file_lines = result.stdout.splitlines()
    start = max(0, line_no - 1 - context)
    end = min(len(file_lines), line_no + context)
    return "\n".join(file_lines[start:end])[:2000]


def pair_events_into_records(
    repo_dir: Path, repo: dict, events: list[RawEvent]
) -> list[UBWRecord]:
    """Agrupa eventos brutos por (arquivo, expressão), ordena
    cronologicamente e casa pares adição->remoção em registros do schema
    (Tabela 3.5), seguindo a operacionalização da Seção 4:

    - o primeiro '+' cronológico é a introdução;
    - o '-' subsequente é a remoção (evento observado, is_censored=0);
    - se ainda "aberto" ao final do histórico, verifica-se HEAD: se o
      arquivo foi deletado ou o repositório está sem a string por motivo
      não capturado no diff, o registro é censurado (não tratado como
      remoção "real"), alinhado com Zampetti et al. (2018).
    """
    repo_full_name = repo["repo_full_name"]
    groups: dict[tuple[str, str], list[RawEvent]] = {}
    for ev in events:
        groups.setdefault((ev.path, ev.expression), []).append(ev)

    records: list[UBWRecord] = []

    for (path, expression), group in groups.items():
        group.sort(key=lambda e: e.date)
        category = group[0].category
        open_event: Optional[RawEvent] = None

        for ev in group:
            if ev.sign == "+":
                if open_event is None:
                    open_event = ev
                # '+' repetido enquanto já aberto: ignora (mesma introdução).
            else:  # '-'
                if open_event is not None:
                    commits_between = commit_count_between(repo_dir, open_event.sha, ev.sha, path)
                    context = get_context_window(repo_dir, open_event.sha, path, open_event.line_no)
                    records.append(
                        UBWRecord(
                            repo_full_name=repo_full_name,
                            artifact_type="code_comment",
                            artifact_id=f"{path}:{open_event.line_no}",
                            matched_expression=expression,
                            category_ubw=category,
                            body_text=context or open_event.text,
                            created_at=open_event.date.isoformat(),
                            removed_at=ev.date.isoformat(),
                            is_censored=0,
                            time_to_event_days=days_between(open_event.date, ev.date),
                            time_to_event_commits=commits_between,
                            repo_stars=to_int(repo.get("stars")),
                            repo_age_days=None,
                            repo_commits=to_int(repo.get("commits")),
                            primary_language=repo.get("primary_language"),
                            # Permalink no SHA de introdução (não HEAD): estável mesmo
                            # que o arquivo mude ou seja apagado depois — Seção 3.4.
                            url=f"https://github.com/{repo_full_name}/blob/{open_event.sha}/{path}#L{open_event.line_no}",
                            # Autor da INTRODUÇÃO (open_event), não da remoção — git
                            # não sabe o username GitHub do autor, só nome/e-mail do commit.
                            author_name=open_event.author_name,
                            author_login=None,
                            author_email=open_event.author_email,
                            author_hash=schema.compute_author_hash(
                                open_event.author_name, None, open_event.author_email
                            ),
                        )
                    )
                    open_event = None
                # '-' sem introdução conhecida: string já existia antes do
                # início da janela de histórico observável. Sem uma data de
                # introdução confiável, o par é descartado (conservador).

        if open_event is not None:
            # Arquivo deletado ou string ausente sem evento de remoção
            # capturado -> censura (Seção 4), nunca remoção fabricada.
            is_censored = 1
            effective_end = COLLECTION_CUTOFF
            context = get_context_window(repo_dir, open_event.sha, path, open_event.line_no)

            records.append(
                UBWRecord(
                    repo_full_name=repo_full_name,
                    artifact_type="code_comment",
                    artifact_id=f"{path}:{open_event.line_no}",
                    matched_expression=expression,
                    category_ubw=category,
                    body_text=context or open_event.text,
                    created_at=open_event.date.isoformat(),
                    removed_at=None,
                    is_censored=is_censored,
                    time_to_event_days=days_between(open_event.date, effective_end),
                    time_to_event_commits=None,
                    repo_stars=to_int(repo.get("stars")),
                    repo_age_days=None,
                    repo_commits=to_int(repo.get("commits")),
                    primary_language=repo.get("primary_language"),
                    url=f"https://github.com/{repo_full_name}/blob/{open_event.sha}/{path}#L{open_event.line_no}",
                    author_name=open_event.author_name,
                    author_login=None,
                    author_email=open_event.author_email,
                    author_hash=schema.compute_author_hash(
                        open_event.author_name, None, open_event.author_email
                    ),
                )
            )

    return records


# Exclusão em nível de git (pathspec magic `:(exclude,glob)`) para pastas de
# vendoring convencionais — evita gastar um `git show` por commit nesses
# caminhos, em vez de só descartar o resultado depois. Padrões sem nome
# convencional (ex: "rocksdb-8.1.1/") não dá pra expressar como glob de
# pathspec, então continuam filtrados em find_raw_events_for_expression via
# lexicon.is_vendored_path.
_VENDOR_PATHSPEC_EXCLUDES = [
    f":(exclude,glob){folder}**"
    for folder in (
        "vendor/", "node_modules/", "third_party/", "thirdparty/",
        "external/", "extern/", "deps/", "Godeps/", "*/site-packages/",
        "*/dist-packages/", ".venv/", "bower_components/",
        "*/src/golang.org/", "*/src/github.com/",
    )
]


def collect_code_comment_records(repo_dir: Path, repo: dict) -> list[UBWRecord]:
    pathspecs = [f"*{ext}" for ext in lexicon.CODE_EXTENSIONS] + _VENDOR_PATHSPEC_EXCLUDES
    all_events: list[RawEvent] = []
    for entry in lexicon.iter_lexicon():
        try:
            all_events.extend(find_raw_events_for_expression(repo_dir, entry.expression, entry.category, pathspecs))
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            logger.error("Falha ao buscar code_comment em %s (%s): %s", repo["repo_full_name"], entry.expression, exc)
    return pair_events_into_records(repo_dir, repo, all_events)


# Pós-processamento: idade do repositório + threshold (Seção 2.4)

def enrich_repo_age(records: list[UBWRecord], repo_age_days: Optional[int]) -> None:
    for rec in records:
        rec.repo_age_days = repo_age_days


# Paralelização de code_comment (ver main())

def process_repo_code_comment(
    repo: dict, clone_root: Path, keep_clones: bool, appender: CSVAppender, state: CheckpointState
) -> None:
    """Executado em worker thread do pool: clona e coleta code_comment de
    UM repositório. Independente entre repositórios (cada um usa seu
    próprio diretório de clone), então é seguro rodar vários em paralelo.
    """
    repo_full_name = repo["repo_full_name"]
    clone_url = repo.get("clone_url") or f"https://github.com/{repo_full_name}.git"
    repo_dir = clone_root / repo_full_name.replace("/", "__")

    cloned_ok = clone_repo(clone_url, repo_dir)
    if not cloned_ok:
        logger.error(
            "Pulando code_comment de %s nesta execução (clone falhou); "
            "será tentado novamente na próxima retomada.", repo_full_name,
        )
        return

    try:
        first_commit = get_first_commit_date(repo_dir)
        repo_created_at = parse_iso_datetime(repo.get("created_at"))
        repo_age_days = (
            days_between(first_commit, COLLECTION_CUTOFF) if first_commit is not None
            else days_between(repo_created_at, COLLECTION_CUTOFF)
        )
        records = collect_code_comment_records(repo_dir, repo)
        enrich_repo_age(records, repo_age_days)
        n = appender.write(records)
        logger.info("  [code_comment] %s: %d registros", repo_full_name, n)
    finally:
        if not keep_clones:
            shutil.rmtree(repo_dir, ignore_errors=True)

    # Só marca como concluído se clone + coleta tiveram sucesso — se
    # qualquer etapa lançar exceção, o par (repo, code_comment) fica
    # pendente e é retomado na próxima execução, em vez de perder o
    # artefato de vez.
    state.mark_done(repo_full_name, "code_comment")


def apply_threshold_and_split(full_csv: Path, out_dir: Path) -> None:
    """Implementa o filtro de threshold da Seção 2.4: um repositório entra
    no subconjunto de RQ2 apenas se tiver >= MIN_OCCURRENCES_FOR_RQ2
    ocorrências em pelo menos um tipo de artefato. RQ1 usa sempre o
    dataset completo (todos os repositórios, inclusive com zero
    ocorrências, como denominador — Seção 2.4).
    """
    with full_csv.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    counts_by_repo_artifact: dict[tuple[str, str], int] = {}
    for row in rows:
        key = (row["repo_full_name"], row["artifact_type"])
        counts_by_repo_artifact[key] = counts_by_repo_artifact.get(key, 0) + 1

    max_by_repo: dict[str, int] = {}
    for (repo, _artifact), count in counts_by_repo_artifact.items():
        max_by_repo[repo] = max(max_by_repo.get(repo, 0), count)

    threshold = schema.MIN_OCCURRENCES_FOR_RQ2
    repos_with_occurrences = [r for r, c in max_by_repo.items() if c > 0]
    repos_meeting = {r for r, c in max_by_repo.items() if c >= threshold}
    excluded_ratio = (
        1 - (len(repos_meeting) / len(repos_with_occurrences)) if repos_with_occurrences else 0.0
    )

    if excluded_ratio > schema.THRESHOLD_EXCLUSION_ALERT_RATIO:
        logger.warning(
            "Threshold >= %d exclui %.1f%% dos repositórios com ocorrências (> %.0f%%). "
            "Esse já é o valor mínimo previsto no plano (Seção 2.4, ex-fallback de %d); "
            "não há um próximo degrau automático. Se persistir, é decisão do orientador: "
            "expandir o corpus, revisar o léxico de novo, ou aceitar a exclusão como "
            "característica do fenômeno.",
            threshold, excluded_ratio * 100, schema.THRESHOLD_EXCLUSION_ALERT_RATIO * 100,
            schema.PREVIOUS_MIN_OCCURRENCES_FOR_RQ2,
        )

    subset_path = out_dir / "ubw_collected_rq2_subset.csv"
    with subset_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=schema.fieldnames())
        writer.writeheader()
        for row in rows:
            if row["repo_full_name"] in repos_meeting:
                writer.writerow(row)
    logger.info(
        "RQ2 subset: %d/%d repositórios com >= %d ocorrências -> %s",
        len(repos_meeting), len(max_by_repo), threshold, subset_path,
    )

    counts_path = out_dir / "repo_occurrence_counts.csv"
    with counts_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["repo_full_name", "max_occurrences_single_artifact", "meets_rq2_threshold"])
        for repo, count in sorted(max_by_repo.items(), key=lambda kv: -kv[1]):
            writer.writerow([repo, count, repo in repos_meeting])
    logger.info("Contagens por repositório salvas em %s", counts_path)


# Orquestração principal

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repos-csv", default="../data/repos_to_mine.csv")
    parser.add_argument("--out-dir", default="../data")
    parser.add_argument("--clone-dir", default="../data/clones")
    parser.add_argument("--state-file", default="../data/collection_state.json")
    parser.add_argument("--github-token", default=None, help="Padrão: variável de ambiente GITHUB_TOKEN.")
    parser.add_argument(
        "--github-tokens", default=None,
        help="Vários tokens separados por vírgula, para rotação (multiplica o throughput de "
             "30 req/min da Search API por token). Padrão: variável de ambiente GITHUB_TOKENS. "
             "Tem prioridade sobre --github-token/GITHUB_TOKEN se ambos forem informados.",
    )
    parser.add_argument(
        "--artifact-types", nargs="+", default=list(schema.ARTIFACT_TYPES),
        choices=list(schema.ARTIFACT_TYPES), help="Subconjunto de tipos de artefato a coletar.",
    )
    parser.add_argument("--keep-clones", action="store_true", help="Não apaga o clone local após processar o repo.")
    parser.add_argument("--max-repos", type=int, default=None, help="Limite para testes locais.")
    parser.add_argument(
        "--parallel-workers", type=int, default=6,
        help="Nº de repositórios processados em paralelo para code_comment (clone + git grep/log -S). "
             "Não afeta issue_body/pr_body/commit_message: cada token da Search API tem um teto de "
             "throughput (30 req/min) imposto pelo servidor; use --github-tokens para multiplicar "
             "esse teto em vez de paralelismo (que não furaria o limite de um único token).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    clone_root = Path(args.clone_dir)

    tokens_arg = args.github_tokens or os.environ.get("GITHUB_TOKENS")
    tokens = [t.strip() for t in tokens_arg.split(",") if t.strip()] if tokens_arg else None
    client = GitHubClient(token=args.github_token, tokens=tokens)
    state = CheckpointState(Path(args.state_file))
    appender = CSVAppender(out_dir / "ubw_collected_full.csv")

    repos = load_repos(Path(args.repos_csv))
    if args.max_repos is not None:
        repos = repos[: args.max_repos]
    logger.info("Carregados %d repositórios de %s", len(repos), args.repos_csv)

    # A Search API tem teto de throughput do servidor que threads não
    # furam, então issue_body/pr_body/commit_message ficam num loop
    # sequencial. code_comment (clone + git) não tem esse limite: roda em
    # pool de threads em paralelo com o loop da API, disparado antes dele.
    #
    # Trade-off: repo_age_days de issue_body/pr_body/commit_message usa
    # sempre o created_at do SEART-GHS, não o primeiro commit local (que só
    # fica pronto quando o worker de code_comment termina o clone, sem
    # ordem garantida entre os dois loops) — aceitável porque é variável de
    # confusão (Tabela 3.5), não métrica primária; code_comment continua
    # usando a data real do primeiro commit, calculada dentro do worker.
    executor: Optional[ThreadPoolExecutor] = None
    code_comment_futures = []
    if "code_comment" in args.artifact_types:
        pending = [r for r in repos if not state.is_done(r["repo_full_name"], "code_comment")]
        logger.info(
            "Disparando %d workers para code_comment em %d repositórios (em paralelo com o loop da API).",
            args.parallel_workers, len(pending),
        )
        executor = ThreadPoolExecutor(max_workers=args.parallel_workers)
        code_comment_futures = [
            executor.submit(process_repo_code_comment, repo, clone_root, args.keep_clones, appender, state)
            for repo in pending
        ]

    # Loop da API por LOTES de repositórios (ver comentário de otimização
    # em "Coleta via Search API"): 1 query por (expressão, lote) em vez de
    # 1 por (expressão, repo). O checkpoint continua por (repo, artefato):
    # dentro de cada lote, só entram na query os repos ainda pendentes, e
    # cada um é marcado como concluído individualmente após a escrita.
    api_collectors = {
        "issue_body": lambda batch: collect_issue_or_pr_records_batched(client, batch, is_pr=False),
        "pr_body": lambda batch: collect_issue_or_pr_records_batched(client, batch, is_pr=True),
        "commit_message": lambda batch: collect_commit_message_records_batched(client, batch),
    }
    api_types = [t for t in ("issue_body", "pr_body", "commit_message") if t in args.artifact_types]

    try:
        if api_types:
            batches = build_repo_batches(repos)
            logger.info(
                "Coleta via Search API em %d lotes de repositórios (~%.1f repos/lote).",
                len(batches), len(repos) / len(batches),
            )
            for bi, batch in enumerate(batches, start=1):
                for artifact_type in api_types:
                    pending = [r for r in batch if not state.is_done(r["repo_full_name"], artifact_type)]
                    if not pending:
                        continue
                    logger.info(
                        "[lote %d/%d] %s: %d repositórios pendentes", bi, len(batches), artifact_type, len(pending),
                    )
                    by_repo = api_collectors[artifact_type](pending)
                    for repo in pending:
                        repo_full_name = repo["repo_full_name"]
                        records = by_repo.get(repo_full_name, [])
                        # repo_age_days aqui vem do created_at do SEART-GHS
                        # (ver comentário de paralelização acima) — os
                        # registros de code_comment recebem separadamente a
                        # data do primeiro commit local, calculada dentro do
                        # worker de process_repo_code_comment.
                        repo_created_at = parse_iso_datetime(repo.get("created_at"))
                        enrich_repo_age(records, days_between(repo_created_at, COLLECTION_CUTOFF))
                        n = appender.write(records)
                        state.mark_done(repo_full_name, artifact_type)
                        if n:
                            logger.info("  %s %s: %d registros", artifact_type, repo_full_name, n)

    finally:
        if executor is not None:
            logger.info(
                "Loop da API concluído. Aguardando os workers de code_comment que ainda "
                "estiverem rodando em segundo plano..."
            )
            for fut in as_completed(code_comment_futures):
                exc = fut.exception()
                if exc is not None:
                    logger.error("Worker de code_comment terminou com erro: %s", exc)
            executor.shutdown(wait=True)
        appender.close()

    apply_threshold_and_split(out_dir / "ubw_collected_full.csv", out_dir)
    logger.info("Coleta concluída. Data de corte: %s", COLLECTION_CUTOFF.isoformat())


if __name__ == "__main__":
    main()
