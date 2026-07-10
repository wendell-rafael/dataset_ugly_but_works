"""Schema de coleta (Tabela 3.5 do plano) e critérios de inclusão (Seção 2).

Fonte única de verdade para nomes/ordem de colunas do dataset — os três
scripts de coleta importam daqui para garantir que os CSVs tenham
exatamente o mesmo schema.
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, fields
from typing import Optional

# Critérios de inclusão de repositórios (Seção 2.2)
MIN_STARS = 100
MIN_COMMITS = 100
MIN_CONTRIBUTORS = 3
MAX_DAYS_SINCE_LAST_COMMIT = 730  # ~2 anos
REQUIRE_ISSUES_ENABLED = True
REQUIRE_PULLS_ENABLED = True
EXCLUDE_FORKS = True

# Threshold de inclusão no subconjunto de RQ2 (Seção 2.4); RQ1 usa o corpus
# inteiro. Reduzido de 5 para 3 (fallback previsto na Seção 2.4) — ver
# RESULTADOS_PILOTO.md Seção 9 para o histórico da decisão.
MIN_OCCURRENCES_FOR_RQ2 = 3
PREVIOUS_MIN_OCCURRENCES_FOR_RQ2 = 5
THRESHOLD_EXCLUSION_ALERT_RATIO = 0.40

# Tipos de artefato (Tabela 3.5 / Li et al., 2023)
ARTIFACT_TYPES = ("code_comment", "commit_message", "issue_body", "pr_body")

# Schema de coleta (Tabela 3.5)

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

# Identidade do autor da INTRODUÇÃO do registro — só introdução, remoção não
# é rastreada. Dado bruto (nome/login/e-mail) fica no dataset de trabalho
# para permitir contato numa survey futura; `author_hash` (SHA-256 sem salt,
# pseudonimização, não anonimização formal — reidentificável com uma lista
# de candidatos) é o campo a usar na versão publicada, removendo os brutos.
#
# Disponibilidade por artefato: commit_message tem name+email sempre (vêm do
# commit) e login se a conta GitHub estiver vinculada; issue_body/pr_body só
# têm login (Search API não expõe e-mail); code_comment tem name+email do
# commit de introdução, sem login (git não sabe o usuário GitHub do autor).


def compute_author_hash(name: Optional[str], login: Optional[str], email: Optional[str]) -> Optional[str]:
    """SHA-256 do identificador mais forte disponível (e-mail > login >
    nome). Normaliza case/espaço para o mesmo autor gerar sempre o mesmo
    hash; retorna None se não houver identificador.
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
        return {col: row.get(col) for col in COLLECTION_SCHEMA_COLUMNS}


def fieldnames() -> list[str]:
    return list(COLLECTION_SCHEMA_COLUMNS)


assert [f.name for f in fields(UBWRecord)] == COLLECTION_SCHEMA_COLUMNS, (
    "UBWRecord fora de sincronia com COLLECTION_SCHEMA_COLUMNS (Tabela 3.5)"
)


# Schema do CSV de repositórios triados (saída do script 01)

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
