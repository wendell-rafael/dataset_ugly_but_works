#!/usr/bin/env python3
"""Fase 1 — Triagem de repositórios via SEART-GHS (Seção 2.2 do plano).

Consulta a API pública do SEART-GHS (https://seart-ghs.si.usi.ch) e salva
os repositórios que satisfazem os critérios de inclusão em
`data/repos_to_mine.csv`, no schema de `ubw.schema.REPOS_TO_MINE_COLUMNS`.

Critérios (Seção 2.2):
    - estrelas >= 100
    - commits totais >= 100
    - contribuidores >= 3
    - último commit <= 2 anos atrás
    - issues e PRs habilitados
    - não é fork
    - sem restrição de linguagem

IMPORTANTE — sobre os nomes de parâmetro da API do SEART-GHS
--------------------------------------------------------------
O SEART-GHS é um serviço acadêmico de terceiros (USI) cujo schema de query
pode mudar. Os nomes de parâmetro usados abaixo (`starsMin`, `commitsMin`,
`contributorsMin`, `committedMin`, `excludeForks`, `hasIssues`, `hasPulls`,
paginação `page`/`size`) foram confirmados batendo diretamente o form HTML
de busca em https://seart-ghs.si.usi.ch/ (não há Swagger público exposto
nesse domínio). O envelope de resposta usa a chave `items` (não `content`),
conforme `js/search.js` do próprio site. Antes de rodar a coleta em escala,
execute novamente esta verificação caso o site mude:

    python 01_screening_seart.py --verify-only

Isso faz uma única chamada de teste e imprime a resposta bruta. Se os
nomes de parâmetro tiverem mudado, ajuste apenas `build_query_params()`
e `normalize_repo()` abaixo — o resto do script não precisa mudar.

NOTA SOBRE TLS: o servidor seart-ghs.si.usi.ch não envia o certificado
intermediário durante o handshake TLS (bug de configuração do lado
deles — confirmado via `openssl s_client -showcerts`, que mostra apenas
o certificado-folha). Isso quebra a verificação padrão de `requests`.
O script contorna isso via `ubw.tls_fix`, que baixa o intermediário
faltante pela extensão AIA do certificado (o mesmo mecanismo que um
navegador usa) e monta um bundle de CA combinado — a verificação de
cadeia nunca é desativada.

Uso:
    export SEART_BASE_URL=https://seart-ghs.si.usi.ch/api/r/search  # opcional
    python 01_screening_seart.py --out ../data/repos_to_mine.csv
    python 01_screening_seart.py --min-stars 50 --min-contributors 2  # flexibilização (Seção 2.3)
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import logging
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ubw import schema  # noqa: E402
from ubw.envutil import load_dotenv  # noqa: E402
from ubw.tls_fix import get_verify_bundle_for_host  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ubw.screening")

SEART_BASE_URL = "https://seart-ghs.si.usi.ch/api/r/search"
PAGE_SIZE = 200
REQUEST_TIMEOUT_SECONDS = 60
MAX_RETRIES = 5
BACKOFF_BASE_SECONDS = 3.0


def build_query_params(
    min_stars: int,
    min_commits: int,
    min_contributors: int,
    max_days_since_last_commit: int,
    require_issues: bool,
    require_pulls: bool,
    exclude_forks: bool,
    page: int,
    page_size: int,
) -> dict:
    """Único ponto de edição caso o schema de query do SEART-GHS mude.

    Mapeamento para a notação ilustrativa do plano (Seção 3.3):
        gt:stars=100        -> starsMin=100
        gt:commits=100      -> commitsMin=100
        gt:contributors=3   -> contributorsMin=3
        gt:lastCommit=730d  -> committedMin=<hoje - 730 dias>
        is:fork=false       -> excludeForks=true
        has:issues=true     -> hasIssues=true (+ hasPulls=true, Seção 2.2)
    """
    committed_min = (dt.date.today() - dt.timedelta(days=max_days_since_last_commit)).isoformat()
    params = {
        "starsMin": min_stars,
        "commitsMin": min_commits,
        "contributorsMin": min_contributors,
        "committedMin": committed_min,
        "excludeForks": str(exclude_forks).lower(),
        "hasIssues": str(require_issues).lower(),
        "hasPulls": str(require_pulls).lower(),
        "page": page,
        "size": page_size,
    }
    return params


def fetch_page(session: requests.Session, base_url: str, params: dict) -> dict:
    """Executa uma chamada com retry/backoff para erros transitórios."""
    last_exc: Optional[Exception] = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(base_url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            last_exc = exc
            wait = BACKOFF_BASE_SECONDS * attempt
            logger.warning("Erro de rede (tentativa %d/%d): %s. Aguardando %.0fs.", attempt, MAX_RETRIES, exc, wait)
            time.sleep(wait)
            continue

        if resp.status_code == 200:
            return resp.json()

        if resp.status_code == 429:
            retry_after = float(resp.headers.get("Retry-After", BACKOFF_BASE_SECONDS * attempt))
            logger.warning("HTTP 429 do SEART-GHS. Aguardando %.0fs.", retry_after)
            time.sleep(retry_after)
            continue

        if 500 <= resp.status_code < 600:
            wait = BACKOFF_BASE_SECONDS * attempt
            logger.warning("HTTP %d do SEART-GHS (tentativa %d/%d). Aguardando %.0fs.",
                            resp.status_code, attempt, MAX_RETRIES, wait)
            time.sleep(wait)
            continue

        raise RuntimeError(
            f"HTTP {resp.status_code} inesperado do SEART-GHS: {resp.text[:500]}\n"
            "O schema da API pode ter mudado — verifique build_query_params() "
            "contra https://seart-ghs.si.usi.ch/swagger-ui.html"
        )

    raise RuntimeError(f"Esgotadas {MAX_RETRIES} tentativas contra o SEART-GHS: {last_exc}")


def normalize_repo(raw: dict) -> dict:
    """Mapeia um objeto de repositório do SEART-GHS para REPOS_TO_MINE_COLUMNS.

    O SEART-GHS já retorna campos separados de owner/name em algumas
    versões da API e um único "name" completo (owner/repo) em outras.
    Tratamos ambos os casos defensivamente.
    """
    full_name = raw.get("name") or raw.get("fullName") or raw.get("nameWithOwner")
    if full_name and "/" in str(full_name):
        owner, name = full_name.split("/", 1)
    else:
        owner = raw.get("owner") or raw.get("ownerLogin") or ""
        name = raw.get("name") or raw.get("repoName") or ""
        full_name = f"{owner}/{name}" if owner and name else (name or full_name or "")

    # totalIssues/totalPullRequests são usados como proxy de "habilitado",
    # já que o item retornado pela API não traz um booleano hasIssues/
    # hasPulls explícito (confirmado inspecionando a resposta real).
    return {
        "repo_full_name": full_name,
        "owner": owner,
        "name": name,
        "stars": raw.get("stargazers") or raw.get("stars") or raw.get("starsCount"),
        "forks": raw.get("forks") or raw.get("forksCount"),
        "commits": raw.get("commits") or raw.get("commitsCount"),
        "contributors": raw.get("contributors") or raw.get("contributorsCount"),
        "primary_language": raw.get("mainLanguage") or raw.get("language"),
        "last_commit_date": raw.get("lastCommit") or raw.get("lastCommitDate"),
        "created_at": raw.get("createdAt") or raw.get("creationDate"),
        "has_issues": raw.get("hasIssues", (raw.get("totalIssues") or 0) > 0),
        "has_pulls": raw.get("hasPullRequests", raw.get("hasPulls", (raw.get("totalPullRequests") or 0) > 0)),
        "is_fork": raw.get("isFork", False),
        "html_url": raw.get("url") or (f"https://github.com/{full_name}" if full_name else None),
        "clone_url": raw.get("cloneUrl") or (f"https://github.com/{full_name}.git" if full_name else None),
    }


def screen_repositories(
    base_url: str,
    min_stars: int,
    min_commits: int,
    min_contributors: int,
    max_days_since_last_commit: int,
    require_issues: bool,
    require_pulls: bool,
    exclude_forks: bool,
    page_size: int,
    max_repos: Optional[int],
    raw_archive_path: Optional[Path],
    allow_expired_cert_pin: bool = False,
    out_path: Optional[Path] = None,
    resume_from_page: int = 0,
) -> list[dict]:
    """Coleta paginada com checkpoint incremental: se `out_path` for
    informado, o CSV é escrito (append + flush) a cada página, e o arquivo
    bruto vira JSONL (uma página por linha) em vez de um único JSON montado
    no final — uma rodada sem `--max-repos` pode levar horas, e sem isso
    uma interrupção no meio perde tudo. `resume_from_page` permite retomar
    manualmente de uma página conhecida; a query é stateless por página,
    seguro desde que os critérios não mudem entre execuções.
    """
    session = requests.Session()
    session.headers.update({"Accept": "application/json", "User-Agent": "ubw-dataset-collector/1.0"})
    host = urlparse(base_url).hostname
    if allow_expired_cert_pin:
        # Certificado de seart-ghs.si.usi.ch venceu (não é cadeia incompleta,
        # que get_verify_bundle_for_host já cobre) — usa fixação de
        # impressão digital em vez de desabilitar TLS por completo. REMOVER
        # esta flag do uso normal assim que o certificado for renovado.
        from ubw.tls_fix import get_session_trusting_pinned_cert
        session = get_session_trusting_pinned_cert(host)
        session.headers.update({"Accept": "application/json", "User-Agent": "ubw-dataset-collector/1.0"})
    else:
        session.verify = get_verify_bundle_for_host(host)

    results: list[dict] = []
    page = resume_from_page

    csv_file = None
    csv_writer = None
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        write_header = resume_from_page == 0 or not out_path.exists()
        csv_file = out_path.open("a" if not write_header else "w", newline="", encoding="utf-8")
        csv_writer = csv.DictWriter(csv_file, fieldnames=schema.REPOS_TO_MINE_COLUMNS)
        if write_header:
            csv_writer.writeheader()

    raw_file = None
    if raw_archive_path is not None:
        raw_archive_path.parent.mkdir(parents=True, exist_ok=True)
        raw_file = raw_archive_path.open("a" if resume_from_page else "w", encoding="utf-8")

    try:
        while True:
            params = build_query_params(
                min_stars, min_commits, min_contributors, max_days_since_last_commit,
                require_issues, require_pulls, exclude_forks, page, page_size,
            )
            logger.info("Buscando página %d (%d repositórios coletados até agora)...", page, len(results))
            payload = fetch_page(session, base_url, params)

            if raw_file is not None:
                raw_file.write(json.dumps(payload, ensure_ascii=False))
                raw_file.write("\n")
                raw_file.flush()

            content = payload.get("items", payload.get("content", []))
            if not isinstance(content, list):
                raise RuntimeError(
                    f"Formato de resposta inesperado do SEART-GHS (sem 'items'/'content'): "
                    f"chaves={list(payload.keys())}. Verifique o schema da API."
                )

            page_rows = [normalize_repo(raw) for raw in content]
            if max_repos is not None:
                remaining = max_repos - len(results)
                page_rows = page_rows[:remaining]
            results.extend(page_rows)
            if csv_writer is not None:
                for row in page_rows:
                    csv_writer.writerow({col: row.get(col) for col in schema.REPOS_TO_MINE_COLUMNS})
                csv_file.flush()

            if max_repos is not None and len(results) >= max_repos:
                break

            is_last = payload.get("last", True) if "last" in payload else (len(content) < page_size)
            if is_last or not content:
                break
            page += 1
    finally:
        if csv_file is not None:
            csv_file.close()
        if raw_file is not None:
            raw_file.close()

    if out_path is not None:
        logger.info("Checkpoint incremental gravado em %s (%d repositórios).", out_path, len(results))
    if raw_archive_path is not None:
        logger.info("Respostas brutas arquivadas (JSONL) em %s (Seção 3.4 — reprodutibilidade).", raw_archive_path)

    return results


def verify_api_schema(base_url: str) -> None:
    """Faz uma chamada mínima e imprime a resposta bruta para inspeção manual."""
    session = requests.Session()
    session.headers.update({"Accept": "application/json", "User-Agent": "ubw-dataset-collector/1.0"})
    session.verify = get_verify_bundle_for_host(urlparse(base_url).hostname)
    params = build_query_params(
        schema.MIN_STARS, schema.MIN_COMMITS, schema.MIN_CONTRIBUTORS,
        schema.MAX_DAYS_SINCE_LAST_COMMIT, schema.REQUIRE_ISSUES_ENABLED,
        schema.REQUIRE_PULLS_ENABLED, schema.EXCLUDE_FORKS, page=0, page_size=1,
    )
    logger.info("Chamada de verificação: GET %s params=%s", base_url, params)
    payload = fetch_page(session, base_url, params)
    print(json.dumps(payload, ensure_ascii=False, indent=2)[:4000])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default=SEART_BASE_URL, help="Endpoint de busca do SEART-GHS.")
    parser.add_argument("--out", default="../data/repos_to_mine.csv", help="Caminho do CSV de saída.")
    parser.add_argument("--min-stars", type=int, default=schema.MIN_STARS)
    parser.add_argument("--min-commits", type=int, default=schema.MIN_COMMITS)
    parser.add_argument("--min-contributors", type=int, default=schema.MIN_CONTRIBUTORS)
    parser.add_argument("--max-days-since-last-commit", type=int, default=schema.MAX_DAYS_SINCE_LAST_COMMIT)
    parser.add_argument("--no-require-issues", action="store_true", help="Não exigir issues habilitadas.")
    parser.add_argument("--no-require-pulls", action="store_true", help="Não exigir PRs habilitados.")
    parser.add_argument("--include-forks", action="store_true", help="Não excluir forks.")
    parser.add_argument("--page-size", type=int, default=PAGE_SIZE)
    parser.add_argument("--max-repos", type=int, default=None, help="Limite para testes locais.")
    parser.add_argument(
        "--archive-raw", default="../data/seart_raw_responses.jsonl",
        help="Onde arquivar as páginas brutas, uma por linha (JSONL, Seção 3.4). Use '' para desabilitar.",
    )
    parser.add_argument(
        "--resume-from-page", type=int, default=0,
        help="Retoma a partir desta página (0-indexed), anexando ao CSV/JSONL existentes em vez de "
             "sobrescrever. Use o número de página do último log antes de uma interrupção.",
    )
    parser.add_argument(
        "--verify-only", action="store_true",
        help="Faz apenas uma chamada de teste e imprime a resposta, sem coletar nada.",
    )
    parser.add_argument(
        "--allow-expired-cert-pin", action="store_true",
        help="Uso temporário (achado de 2026-07-08): o certificado TLS de seart-ghs.si.usi.ch "
             "está vencido. Em vez de desabilitar a verificação TLS por completo, esta flag usa "
             "fixação de impressão digital (ubw/tls_fix.py) — só aceita a conexão se o "
             "certificado bater exatamente com o capturado manualmente, ignorando apenas a "
             "data de validade. Decisão explícita do usuário; remover do uso normal assim que "
             "o certificado for renovado.",
    )
    return parser.parse_args()


def _count_csv_data_rows(csv_path: Path) -> int:
    """Conta as linhas de dados (exclui o cabeçalho) de um CSV no disco.

    Usado para `total_repositories` no meta.json: numa retomada via
    `--resume-from-page`, `screen_repositories()` retorna só as linhas
    coletadas nesta invocação, então `len(rows)` subestimaria o total real
    do CSV. Retorna 0 se o arquivo não existir ou estiver vazio.
    """
    if not csv_path.exists():
        return 0
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        try:
            next(reader)  # cabeçalho
        except StopIteration:
            return 0  # arquivo vazio
        return sum(1 for _ in reader)


def main() -> None:
    args = parse_args()

    if args.verify_only:
        verify_api_schema(args.base_url)
        return

    raw_archive_path = Path(args.archive_raw) if args.archive_raw else None
    out_path = Path(args.out)
    rows = screen_repositories(
        base_url=args.base_url,
        min_stars=args.min_stars,
        min_commits=args.min_commits,
        min_contributors=args.min_contributors,
        max_days_since_last_commit=args.max_days_since_last_commit,
        require_issues=not args.no_require_issues,
        require_pulls=not args.no_require_pulls,
        exclude_forks=not args.include_forks,
        page_size=args.page_size,
        max_repos=args.max_repos,
        raw_archive_path=raw_archive_path,
        allow_expired_cert_pin=args.allow_expired_cert_pin,
        out_path=out_path,
        resume_from_page=args.resume_from_page,
    )

    if not rows:
        logger.warning(
            "Nenhum repositório retornado. Rode com --verify-only para inspecionar a "
            "resposta bruta e confirmar que os parâmetros da query estão corretos."
        )

    # O CSV já foi gravado incrementalmente por screen_repositories(); não
    # reescrevemos aqui para não perder a propriedade de checkpoint (uma
    # reescrita completa exigiria manter `rows` inteiro em memória e só
    # gravaria no final, reintroduzindo o mesmo risco que motivou o checkpoint).

    cutoff_note = out_path.with_suffix(".meta.json")
    with cutoff_note.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "collection_cutoff_date": dt.datetime.now(dt.timezone.utc).isoformat(),
                "criteria": {
                    "min_stars": args.min_stars,
                    "min_commits": args.min_commits,
                    "min_contributors": args.min_contributors,
                    "max_days_since_last_commit": args.max_days_since_last_commit,
                    "require_issues": not args.no_require_issues,
                    "require_pulls": not args.no_require_pulls,
                    "exclude_forks": not args.include_forks,
                },
                # Total real do CSV em disco, não len(rows) — ver docstring de _count_csv_data_rows.
                "total_repositories": _count_csv_data_rows(out_path),
            },
            f, ensure_ascii=False, indent=2,
        )
    logger.info("Metadados de reprodutibilidade salvos em %s (Seção 3.4).", cutoff_note)


if __name__ == "__main__":
    main()
