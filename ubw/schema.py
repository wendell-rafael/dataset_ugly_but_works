"""Schema de coleta (Tabela 3.5 do plano) e critérios de inclusão (Seção 2).

Fonte única de verdade para nomes/ordem de colunas do dataset coletado.
Os três scripts (`01_screening_seart.py`, `02_collect_multiartifact.py`,
`03_metrics_llm_triage.py`) importam daqui para garantir que o CSV
intermediário e o CSV final tenham exatamente o mesmo schema.
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, fields
from typing import Optional

# ---------------------------------------------------------------------------
# Critérios de inclusão de repositórios (Seção 2.2)
# ---------------------------------------------------------------------------

MIN_STARS = 100
MIN_COMMITS = 100
MIN_CONTRIBUTORS = 3
MAX_DAYS_SINCE_LAST_COMMIT = 730  # ~2 anos
REQUIRE_ISSUES_ENABLED = True
REQUIRE_PULLS_ENABLED = True
EXCLUDE_FORKS = True

# Threshold de inclusão no corpus final (Seção 2.4). Aplicado só ao
# subconjunto de sobrevivência (RQ2); RQ1 usa o corpus inteiro.
#
# 2026-07-01: reduzido de 5 para 3 (o fallback já previsto na Seção 2.4),
# por decisão do orientador. Gatilho: nas duas rodadas do piloto, o
# threshold de 5 excluiu 83% dos repositórios com pelo menos 1 ocorrência
# — bem acima dos 40% que o plano definia como limite para acionar a
# redução. Ver RESULTADOS_PILOTO.md, Seção 9.
MIN_OCCURRENCES_FOR_RQ2 = 3
# Valor anterior, mantido só como referência histórica (não é mais usado
# como fallback automático, já que o threshold ativo já é o valor mínimo
# previsto pelo plano).
PREVIOUS_MIN_OCCURRENCES_FOR_RQ2 = 5
THRESHOLD_EXCLUSION_ALERT_RATIO = 0.40

# ---------------------------------------------------------------------------
# Tipos de artefato (Tabela 3.5 / Li et al., 2023)
# ---------------------------------------------------------------------------

ARTIFACT_TYPES = ("code_comment", "commit_message", "issue_body", "pr_body")

# ---------------------------------------------------------------------------
# Schema de coleta (Tabela 3.5)
# ---------------------------------------------------------------------------

COLLECTION_SCHEMA_COLUMNS: list[str] = [
    "repo_full_name",
    "artifact_type",
    "artifact_id",
    "matched_expression",
    "category_ubw",
    "body_text",
    "created_at",
    "removed_at",
    "is_censored",
    "time_to_event_days",
    "time_to_event_commits",
    "repo_stars",
    "repo_age_days",
    "repo_commits",
    "primary_language",
    "url",
    "author_name",
    "author_login",
    "author_email",
    "author_hash",
]

# ---------------------------------------------------------------------------
# Identidade do autor da INTRODUÇÃO do registro (Seção 2026-07-08, decisão do
# usuário: só introdução, não remoção — remoção não é rastreada por ora).
#
# Motivação: o pesquisador pretende contatar autores para uma survey futura,
# então o dado bruto (nome/login/e-mail) é mantido no dataset de trabalho.
# `author_hash` é um pseudônimo estável (SHA-256, sem salt) do identificador
# mais forte disponível — pensado para a VERSÃO COMPARTILHADA/PUBLICADA do
# dataset, onde os campos brutos devem ser removidos antes de publicar.
#
# LIMITAÇÃO reconhecida: hash sem salt é pseudonimização, não anonimização
# de verdade — qualquer pessoa com uma lista de e-mails/logins candidatos
# pode testar cada um contra o hash e reidentificar. Suficiente para reduzir
# exposição casual (o hash não é reversível por inspeção), mas não é uma
# garantia formal de privacidade. Se o dataset for publicado, os campos
# `author_name`/`author_login`/`author_email` devem ser removidos, mantendo
# só `author_hash`.
#
# Disponibilidade por tipo de artefato:
#   - commit_message: author_name e author_email vêm do commit em si
#     (sempre presentes, é metadado do git); author_login só existe se o
#     e-mail do commit estiver vinculado a uma conta GitHub (pode ser None).
#   - issue_body / pr_body: só author_login (a Search API não expõe e-mail;
#     pegar isso exigiria uma chamada extra por usuário a /users/{login},
#     e mesmo assim só funciona para quem tornou o e-mail público).
#   - code_comment: author_name e author_email do commit que introduziu o
#     comentário (git log --format, sem custo de API extra); sem
#     author_login (git não sabe o usuário GitHub do autor).
# ---------------------------------------------------------------------------


def compute_author_hash(name: Optional[str], login: Optional[str], email: Optional[str]) -> Optional[str]:
    """Pseudônimo estável do autor: SHA-256 do identificador mais forte
    disponível, nessa ordem de preferência (e-mail > login > nome), pois
    e-mail e login tendem a ser mais estáveis/únicos que nome de exibição.
    Normaliza case/espaço nas bordas para o mesmo autor sempre gerar o
    mesmo hash. Retorna None se não houver nenhum identificador.
    """
    identifier = (email or login or name or "").strip().lower()
    if not identifier:
        return None
    return hashlib.sha256(identifier.encode("utf-8")).hexdigest()


@dataclass
class UBWRecord:
    """Um registro do schema de coleta (Tabela 3.5)."""

    repo_full_name: str
    artifact_type: str  # code_comment | commit_message | issue_body | pr_body
    artifact_id: str  # SHA, número da issue/PR, ou "filepath:line"
    matched_expression: str
    category_ubw: str  # A | B | C
    body_text: str
    created_at: Optional[str]  # ISO 8601
    removed_at: Optional[str]  # ISO 8601 ou None
    is_censored: int  # 1 = ainda presente na data de corte; 0 = evento observado
    time_to_event_days: Optional[int]
    time_to_event_commits: Optional[int]
    repo_stars: Optional[int]
    repo_age_days: Optional[int]
    repo_commits: Optional[int]
    primary_language: Optional[str]
    url: str
    author_name: Optional[str]  # autor da INTRODUÇÃO do registro (nome de exibição)
    author_login: Optional[str]  # username do GitHub, quando disponível
    author_email: Optional[str]  # e-mail do commit, quando disponível (não aplicável a issue/PR)
    author_hash: Optional[str]  # pseudônimo estável — ver nota acima; usar este campo ao publicar/compartilhar

    def to_row(self) -> dict:
        row = asdict(self)
        # Garante ordem e presença de todas as colunas do schema.
        return {col: row.get(col) for col in COLLECTION_SCHEMA_COLUMNS}


def fieldnames() -> list[str]:
    return list(COLLECTION_SCHEMA_COLUMNS)


assert [f.name for f in fields(UBWRecord)] == COLLECTION_SCHEMA_COLUMNS, (
    "UBWRecord fora de sincronia com COLLECTION_SCHEMA_COLUMNS (Tabela 3.5)"
)


# ---------------------------------------------------------------------------
# Schema do CSV de repositórios triados (saída do script 01)
# ---------------------------------------------------------------------------

REPOS_TO_MINE_COLUMNS: list[str] = [
    "repo_full_name",
    "owner",
    "name",
    "stars",
    "forks",
    "commits",
    "contributors",
    "primary_language",
    "last_commit_date",
    "created_at",
    "has_issues",
    "has_pulls",
    "is_fork",
    "html_url",
    "clone_url",
]
