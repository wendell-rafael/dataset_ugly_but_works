"""Cliente HTTP para a API REST do GitHub com tratamento de rate limit.

Implementa os dois regimes de limite descritos na Seção 3.3 do plano:

    | Endpoint      | Limite (PAT autenticado) | Observação                    |
    |---------------|---------------------------|-------------------------------|
    | /search/*     | 30 req/min                | intervalo mínimo de 2s entre chamadas |
    | REST geral    | 5.000 req/h               | usado para enriquecimento de metadados |

Também trata o "secondary rate limit" (abuse detection) do GitHub via
`Retry-After` e faz paginação genérica via header `Link`.

Rotação de múltiplos tokens (2026-07-03, escala para o corpus completo):
    O limite de 30 req/min do endpoint de busca é por token, não por IP/
    aplicação. `GitHubClient` aceita uma LISTA de tokens e round-robina
    entre eles a cada chamada de busca, multiplicando o throughput
    efetivo por len(tokens) sem violar o limite de nenhum token
    individualmente. Cada token mantém seu próprio estado de rate limit
    (`RateLimitState`), já que os tetos são independentes por token.
"""
from __future__ import annotations

import itertools
import logging
import os
import time
from dataclasses import dataclass
from typing import Iterator, Optional

import requests

logger = logging.getLogger("ubw.github_api")

GITHUB_API_ROOT = "https://api.github.com"

# Intervalo mínimo obrigatório entre chamadas de busca (Seção 3.3).
SEARCH_MIN_INTERVAL_SECONDS = 2.0

# Número máximo de tentativas em caso de erro transitório (5xx, timeout,
# falha de DNS/conexão). Ambientes de execução em contêiner podem ter
# blips de resolução de DNS de 1-2 minutos; o teto de backoff (30s) e um
# número maior de tentativas dão margem para isso sem desistir cedo demais.
MAX_RETRIES = 8
BACKOFF_BASE_SECONDS = 2.0
BACKOFF_CAP_SECONDS = 30.0


class GitHubAPIError(RuntimeError):
    """Erro não recuperável (após esgotar retries) na API do GitHub."""


@dataclass
class RateLimitState:
    remaining: int = 1
    reset_epoch: float = 0.0


class _TokenSlot:
    """Sessão HTTP + estado de rate limit de UM token. Cada token do
    GitHub tem tetos independentes (30 req/min busca, 5000 req/h core),
    então o estado não pode ser compartilhado entre slots.
    """

    def __init__(self, token: str):
        self.token = token
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "ubw-dataset-collector/1.0",
            }
        )
        self.last_search_call = 0.0
        self.core_state = RateLimitState()
        self.search_state = RateLimitState()


class GitHubClient:
    """Cliente HTTP fino sobre a REST API do GitHub, com:

    - autenticação via Personal Access Token(s) (env var GITHUB_TOKEN, ou
      GITHUB_TOKENS separados por vírgula para rotação — ver docstring do
      módulo);
    - respeito ao rate limit primário (via headers X-RateLimit-*);
    - respeito ao rate limit secundário (via Retry-After / mensagens 403);
    - intervalo mínimo de 2s entre chamadas aos endpoints de busca (por token);
    - paginação automática via header `Link`;
    - retry com backoff exponencial para erros transitórios.
    """

    def __init__(self, token: Optional[str] = None, tokens: Optional[list[str]] = None,
                 session: Optional[requests.Session] = None):
        if tokens is None:
            # GITHUB_TOKENS (múltiplos) tem prioridade sobre GITHUB_TOKEN (único) —
            # consistente com o comportamento documentado no .env e nos scripts
            # 02/05, que resolvem essa mesma prioridade antes de instanciar o
            # cliente. Corrigido em 2026-07-06: a ordem estava invertida aqui,
            # fazendo `GitHubClient()` sem argumentos ignorar GITHUB_TOKENS
            # sempre que GITHUB_TOKEN também estivesse definido.
            raw = token or os.environ.get("GITHUB_TOKENS") or os.environ.get("GITHUB_TOKEN")
            if not raw:
                raise GitHubAPIError(
                    "Nenhum token definido. Exporte GITHUB_TOKEN (um token) ou "
                    "GITHUB_TOKENS (vários, separados por vírgula) com escopo "
                    "'repo' (ou 'public_repo') antes de rodar a coleta."
                )
            tokens = [t.strip() for t in raw.split(",") if t.strip()]
        if not tokens:
            raise GitHubAPIError("Lista de tokens vazia.")

        self.token = tokens[0]  # retrocompatibilidade (código que lê client.token)
        self._slots = [_TokenSlot(t) for t in tokens]
        self._search_cycle = itertools.cycle(self._slots)
        self._core_cycle = itertools.cycle(self._slots)
        if session is not None:
            # Uso legado com sessão externa (ex: testes): força 1 slot só.
            self._slots = [self._slots[0]]
            self._slots[0].session = session
            self._search_cycle = itertools.cycle(self._slots)
            self._core_cycle = itertools.cycle(self._slots)
        if len(self._slots) > 1:
            logger.info("GitHubClient com %d tokens em rotação (throughput de busca efetivo: ~%d req/min).",
                        len(self._slots), 30 * len(self._slots))

    # -- infraestrutura de baixo nível -----------------------------------

    def _throttle_search(self, slot: _TokenSlot) -> None:
        elapsed = time.monotonic() - slot.last_search_call
        if elapsed < SEARCH_MIN_INTERVAL_SECONDS:
            time.sleep(SEARCH_MIN_INTERVAL_SECONDS - elapsed)

    def _update_rate_state(self, resp: requests.Response, slot: _TokenSlot, is_search: bool) -> None:
        state = slot.search_state if is_search else slot.core_state
        try:
            state.remaining = int(resp.headers.get("X-RateLimit-Remaining", state.remaining))
            state.reset_epoch = float(resp.headers.get("X-RateLimit-Reset", state.reset_epoch))
        except (TypeError, ValueError):
            pass

    def _wait_for_rate_limit(self, slot: _TokenSlot, is_search: bool) -> None:
        state = slot.search_state if is_search else slot.core_state
        if state.remaining <= 0 and state.reset_epoch > 0:
            wait_seconds = max(0.0, state.reset_epoch - time.time()) + 1.0
            logger.warning(
                "Rate limit (%s, token ...%s) esgotado. Aguardando %.0fs até o reset.",
                "search" if is_search else "core", slot.token[-4:], wait_seconds,
            )
            time.sleep(wait_seconds)

    def request(
        self,
        method: str,
        path_or_url: str,
        params: Optional[dict] = None,
        is_search: bool = False,
        **kwargs,
    ) -> requests.Response:
        """Executa uma requisição HTTP com retry, backoff e rate limiting.

        `path_or_url` pode ser um path relativo (ex: "/repos/o/n") ou uma URL
        absoluta (usada ao seguir o header `Link` de paginação). Cada
        chamada usa o PRÓXIMO token do round-robin (ver docstring do
        módulo) — múltiplas chamadas concorrentes (ex: threads de
        code_comment não usam este cliente, mas chamadas paralelas
        hipotéticas de busca) naturalmente se distribuem entre tokens.
        """
        url = path_or_url if path_or_url.startswith("http") else f"{GITHUB_API_ROOT}{path_or_url}"
        slot = next(self._search_cycle if is_search else self._core_cycle)

        for attempt in range(1, MAX_RETRIES + 1):
            if is_search:
                self._wait_for_rate_limit(slot, is_search=True)
                self._throttle_search(slot)
            else:
                self._wait_for_rate_limit(slot, is_search=False)

            try:
                resp = slot.session.request(method, url, params=params, timeout=30, **kwargs)
            except requests.RequestException as exc:
                wait = min(BACKOFF_CAP_SECONDS, BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))
                logger.warning(
                    "Erro de rede (%s), tentativa %d/%d: %s. Aguardando %.0fs.",
                    url, attempt, MAX_RETRIES, exc, wait,
                )
                time.sleep(wait)
                continue

            if is_search:
                slot.last_search_call = time.monotonic()
            self._update_rate_state(resp, slot, is_search)

            if resp.status_code == 200:
                return resp

            if resp.status_code in (403, 429):
                retry_after = resp.headers.get("Retry-After")
                if retry_after is not None:
                    wait_seconds = float(retry_after) + 1.0
                    logger.warning(
                        "Secondary rate limit atingido em %s. Aguardando %.0fs (Retry-After).",
                        url,
                        wait_seconds,
                    )
                    time.sleep(wait_seconds)
                    continue
                remaining = resp.headers.get("X-RateLimit-Remaining")
                if remaining == "0":
                    reset_epoch = float(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
                    wait_seconds = max(0.0, reset_epoch - time.time()) + 1.0
                    logger.warning("Rate limit primário esgotado. Aguardando %.0fs.", wait_seconds)
                    time.sleep(wait_seconds)
                    continue
                # Fix 2026-07-09: 403 sem Retry-After e sem remaining==0 pode
                # ainda ser o rate limit SECUNDÁRIO (abuse detection) do
                # GitHub, que às vezes omite o header Retry-After. Os docs do
                # GitHub dizem para aguardar pelo menos 60s nesse caso antes
                # de tentar de novo. Sem essa checagem, um 403 transitório de
                # abuse detection matava a coleta inteira como se fosse
                # permissão negada.
                body_text = ""
                try:
                    body_text = resp.text or ""
                except Exception:
                    body_text = ""
                if "secondary rate limit" in body_text.lower():
                    wait_seconds = max(60.0, BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))
                    logger.warning(
                        "Secondary rate limit (sem Retry-After) em %s. Aguardando %.0fs.",
                        url, wait_seconds,
                    )
                    time.sleep(wait_seconds)
                    continue
                # 403 sem indicação de rate limit: provavelmente permissão negada.
                raise GitHubAPIError(f"HTTP 403 em {url}: {resp.text[:300]}")

            if resp.status_code == 422:
                # Query malformada (ex: sintaxe de busca inválida) — não adianta retry.
                raise GitHubAPIError(f"HTTP 422 (query inválida) em {url}: {resp.text[:300]}")

            if 500 <= resp.status_code < 600:
                wait_seconds = min(BACKOFF_CAP_SECONDS, BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))
                logger.warning(
                    "Erro de servidor %d em %s, tentativa %d/%d. Aguardando %.0fs.",
                    resp.status_code, url, attempt, MAX_RETRIES, wait_seconds,
                )
                time.sleep(wait_seconds)
                continue

            raise GitHubAPIError(f"HTTP {resp.status_code} inesperado em {url}: {resp.text[:300]}")

        raise GitHubAPIError(f"Esgotadas {MAX_RETRIES} tentativas para {url}")

    def paginate(
        self,
        path_or_url: str,
        params: Optional[dict] = None,
        is_search: bool = False,
        items_key: Optional[str] = None,
        max_items: Optional[int] = None,
    ) -> Iterator[dict]:
        """Segue o header `Link` (rel="next") e produz itens um a um.

        `items_key`: para endpoints de busca, os itens estão em
        `resp.json()["items"]`; para endpoints REST de listagem, a resposta
        já é uma lista.
        """
        url: Optional[str] = path_or_url
        current_params = dict(params or {})
        yielded = 0

        while url:
            resp = self.request("GET", url, params=current_params if url == path_or_url else None, is_search=is_search)
            payload = resp.json()
            items = payload[items_key] if items_key else payload
            if not isinstance(items, list):
                raise GitHubAPIError(f"Resposta inesperada (não é lista) em {url}: {type(items)}")

            for item in items:
                yield item
                yielded += 1
                if max_items is not None and yielded >= max_items:
                    return

            url = resp.links.get("next", {}).get("url")
            current_params = None  # já embutidos na URL "next"

    # -- endpoints de busca (Seção 3.3) -----------------------------------

    def search_issues_query(self, query: str) -> Iterator[dict]:
        """GET /search/issues com uma query arbitrária.

        A Search API do GitHub limita resultados a 1000 itens (100/página x
        10 páginas), mesmo que `total_count` seja maior. Isso é uma
        limitação conhecida e documentada (Seção 3.3: "evitando o teto de
        1.000 resultados" é justamente por isso que comentários de código
        usam clonagem local em vez desta API).

        A query aceita múltiplos qualificadores `repo:` (semântica de OR,
        verificada ao vivo em 2026-07-03) — usado pela coleta batched do
        script 02 para reduzir o número de requisições em ~8x. O teto de q
        é 256 caracteres; quem monta a query é responsável por respeitá-lo.
        """
        params = {"q": query, "sort": "created", "order": "asc", "per_page": 100}
        yield from self.paginate("/search/issues", params=params, is_search=True, items_key="items", max_items=1000)

    def search_commits_query(self, query: str) -> Iterator[dict]:
        """GET /search/commits com uma query arbitrária (mesmas observações
        de search_issues_query: teto de 1000 itens, múltiplos `repo:` OK).
        """
        params = {"q": query, "sort": "committer-date", "order": "asc", "per_page": 100}
        yield from self.paginate("/search/commits", params=params, is_search=True, items_key="items", max_items=1000)

    def search_issues(self, expression: str, repo_full_name: str, is_pr: bool) -> Iterator[dict]:
        """Busca de UMA expressão em UM repositório (forma single usada pela
        mineração exploratória, script 04). A coleta oficial usa a forma
        batched via search_issues_query.
        """
        type_qualifier = "pr" if is_pr else "issue"
        yield from self.search_issues_query(f'"{expression}" in:body type:{type_qualifier} repo:{repo_full_name}')

    def search_commits(self, expression: str, repo_full_name: str) -> Iterator[dict]:
        """Forma single de search_commits_query (ver search_issues)."""
        yield from self.search_commits_query(f'"{expression}" repo:{repo_full_name}')

    # -- endpoints REST gerais (enriquecimento de metadados) --------------

    def get_repo(self, repo_full_name: str) -> dict:
        resp = self.request("GET", f"/repos/{repo_full_name}")
        return resp.json()

    def get_repo_commit_count(self, repo_full_name: str) -> Optional[int]:
        """Estima o total de commits do branch padrão via paginação `Link`.

        Trick padrão: pedir 1 commit por página e ler o número da última
        página no header Link (rel="last"). Se o repositório tiver <=1
        commit, o header `last` não existe e assumimos len(items).
        """
        resp = self.request(
            "GET", f"/repos/{repo_full_name}/commits", params={"per_page": 1}
        )
        last_url = resp.links.get("last", {}).get("url")
        if not last_url:
            return len(resp.json())
        # A URL contém "&page=N"; extrai N sem depender de parsing de URL complexo.
        try:
            page_param = [p for p in last_url.split("?", 1)[1].split("&") if p.startswith("page=")][0]
            return int(page_param.split("=", 1)[1])
        except (IndexError, ValueError):
            return None
