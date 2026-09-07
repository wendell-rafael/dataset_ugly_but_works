#!/usr/bin/env python3
"""Fase 2 — Export do dataset publicável (Agente D, PLANO_VALIDACAO_COWORK.md).

Implementa o princípio 3 da Seção 2 do plano de validação: existem DOIS
datasets — o **de trabalho** (com `author_name/author_login/author_email`
brutos, necessário para RQ3 contatar autores) e o **publicável** (sem esses
campos brutos). Este script gera o segundo a partir do primeiro; o CSV de
trabalho nunca deve ser publicado.

O que este script faz (e o que NÃO decide):
    1. Remove `author_name`, `author_login`, `author_email` do CSV de saída.
       `author_hash` (ver `ubw/schema.py::compute_author_hash`) é mantido —
       é o pseudônimo estável a usar na versão publicada.
    2. Mascara PII estrutural em `body_text` (e-mails, tokens/segredos
       conhecidos, URLs com credenciais embutidas, trailers
       Co-authored-by/Signed-off-by, e opcionalmente @menções) — ver
       `apply_pii_masking()`.
    3. Opcionalmente RE-CALCULA `author_hash` com `--salt` ou `--hmac-key`.
       Isso é MECANISMO, não decisão: por padrão nenhum dos dois é usado e
       `author_hash` é herdado do dataset de trabalho sem alteração (SHA-256
       sem salt, pseudonimização declarada — ver nota em `ubw/schema.py`).
       A escolha entre manter sem salt, salgar, ou usar HMAC com chave
       secreta é uma decisão de política (ética/LGPD para RQ3), documentada
       em `validation/D1_EXPORT_PII_FINDINGS.md` SEM ser tomada aqui.
    4. Escreve um manifesto (`--manifest-json`) com contagens de entrada/
       saída, colunas removidas, hash SHA-256 do CSV de entrada, contagens
       de PII mascarada em `body_text` por categoria, e a versão do script.

Subcomandos:
    export      gera o dataset publicável + manifesto
    scan        varredura de PII em body_text (quantifica; não escreve CSV)
    self-test   roda o teste rápido embutido e sai (não precisa de dados)

Exemplos:
    python 06_export_publishable.py export \
        --candidates ../data/full_run/ubw_collected_full.csv \
        --out-csv ../data/full_run/ubw_publishable.csv \
        --manifest-json ../data/full_run/ubw_publishable_manifest.json

    # com HMAC (decisão de política, não o padrão):
    python 06_export_publishable.py export --candidates ... --out-csv ... \
        --hmac-key "$UBW_HMAC_KEY"

    python 06_export_publishable.py scan \
        --candidates ../data/full_run/ubw_collected_full.csv \
        --out-json ../validation/pii_scan_full_run.json

    python 06_export_publishable.py self-test
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import hmac
import json
import logging
import re
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ubw import schema  # noqa: E402

# Mesmo achado do script 02 (campo > 128KB, ex. changelog colado num PR body).
csv.field_size_limit(10_000_000)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ubw.export_publishable")

SCRIPT_VERSION = "1.0.0"

# Colunas brutas de PII removidas na versão publicável (Seção 2, princípio 3
# do plano de validação). `author_hash` NÃO entra aqui — é o campo a manter.
RAW_PII_COLUMNS: list[str] = ["author_name", "author_login", "author_email"]

PUBLISHABLE_COLUMNS: list[str] = [c for c in schema.COLLECTION_SCHEMA_COLUMNS if c not in RAW_PII_COLUMNS]


# 1. Detecção/mascaramento de PII estrutural em body_text

# Chave privada embutida (ex: alguém colou um .pem inteiro num PR de config).
_PRIVATE_KEY_RE = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z0-9 ]*PRIVATE KEY-----"
)

# scheme://user:senha@host — credencial embutida em URL (ex: string de conexão colada em issue).
_URL_CREDENTIAL_RE = re.compile(
    r"\b[a-zA-Z][a-zA-Z0-9+.\-]*://[^\s'\"<>]+:[^\s'\"<>@]+@[^\s'\"<>/]+"
)

# Trailers de commit que carregam NOME + E-MAIL reais em texto livre (não só
# @handle) — comuns em commit_message e frequentemente perdidos por um
# detector que só procura endereço de e-mail isolado, porque aqui o nome de
# exibição completo também é PII. Mascarados como linha inteira, antes do
# regex de e-mail genérico, para não sobrar o nome exposto com só o e-mail
# redigido no meio da linha.
_COAUTHOR_TRAILER_RE = re.compile(r"(?im)^\s*Co-authored-by:\s*.+$")
_SIGNEDOFF_TRAILER_RE = re.compile(r"(?im)^\s*Signed-off-by:\s*.+$")

# Tokens/segredos com prefixo reconhecível — cada entrada é (rótulo, regex).
# Cobertura deliberadamente restrita a formatos com prefixo estruturado
# (baixo risco de falso positivo); segredos genéricos tipo `password = "x"`
# não são cobertos (ver limitações no relatório).
_TOKEN_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("github_pat_classic", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,255}\b")),
    ("github_pat_fine_grained", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("aws_access_key_id", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,72}\b")),
    ("stripe_key", re.compile(r"\bsk_(?:live|test)_[A-Za-z0-9]{10,99}\b")),
    ("npm_token", re.compile(r"\bnpm_[A-Za-z0-9]{36}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\b")),
    ("generic_bearer", re.compile(r"\bBearer\s+[A-Za-z0-9\-_.=]{12,}\b")),
]

# Sem `\b` no fim de propósito. Com ele, e-mail real vazava sempre que o
# caractere seguinte era de palavra — e isso é comum aqui, porque `body_text`
# vem com as quebras de linha removidas, então o endereço fica colado no texto
# da linha seguinte. Casos reais que escaparam no export de 2026-09-07:
# `dpranke@chromium.org` + `CQ_INCLUDE_TRYBOTS`, `pabs@debian.org` + `pep8`,
# `jeff.paul@10up.com` + `3:`, e `_nicolai.stange@zmaw.de` seguido do `_` de
# ênfase em Markdown. O `\b` inicial fica: evita casar o sufixo de coisas como
# `...@gmail.com` (endereço já elidido no texto original).
#
# O custo é mascarar alguns identificadores que têm forma de e-mail sem serem
# (nome de algoritmo SSH como `chacha20-poly1305@openssh.com`, versão de pacote
# npm). Já eram mascarados de forma inconsistente antes — quando o `\b` final
# calhava de casar — e sub-mascarar endereço de pessoa é o erro mais caro.
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# @handle — possível autor/terceiro mencionado. group(1) é o handle sem '@'.
_MENTION_RE = re.compile(r"(?<![\w@./])@([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))\b")

# Anotações/decorators/tags de doc que TAMBÉM casam com "@palavra" mas não
# são menção a pessoa (Java/JS annotations, Python decorators, Javadoc/JSDoc
# tags). Lista best-effort curada manualmente — não exaustiva; residual
# entra como falso positivo na contagem "menções" (ver limitações).
_MENTION_BLOCKLIST: set[str] = {
    # Javadoc / JSDoc / docstring tags
    "param", "return", "returns", "throws", "exception", "see", "code",
    "link", "author", "since", "version", "deprecated", "inheritdoc",
    "todo", "note", "warning", "override",
    # Java / Spring / JPA annotations
    "test", "component", "autowired", "inject", "requestmapping",
    "getmapping", "postmapping", "putmapping", "deletemapping", "entity",
    "column", "table", "id", "generatedvalue", "suppresswarnings",
    "jsonproperty", "jsonignore", "jsoninclude", "before", "after",
    "beforeeach", "aftereach", "beforeclass", "afterclass", "mock",
    "injectmocks", "data", "builder", "slf4j", "restcontroller",
    "controller", "service", "repository", "configuration", "bean",
    "value", "qualifier", "transactional", "valid", "notnull", "notempty",
    "size", "min", "max", "pattern", "getter", "setter",
    "noargsconstructor", "allargsconstructor", "requiredargsconstructor",
    "equalsandhashcode", "tostring", "functionalinterface", "safevarargs",
    "nullable", "nonnull", "visiblefortesting", "produces", "consumes",
    "pathvariable", "requestparam", "requestbody", "responsebody",
    # Python decorators
    "property", "staticmethod", "classmethod", "abstractmethod",
    "dataclass", "wraps", "lru_cache", "pytest", "fixture", "app",
    "click", "task",
    # JS/TS/Angular
    "injectable", "input", "output", "hostlistener", "viewchild",
    "ngmodule", "directive", "pipe", "component",
}

# Ordem de aplicação: cada estágio só varre o que sobrou depois do anterior
# ser mascarado, então nada é contado/mostrado em duplicidade (ex: o e-mail
# de dentro de um trailer Co-authored-by já mascarado não é recontado como
# "email" isolado).
_ORDERED_STAGES: list[tuple[str, re.Pattern]] = [
    ("private_key", _PRIVATE_KEY_RE),
    ("url_credential", _URL_CREDENTIAL_RE),
    ("coauthor_trailer", _COAUTHOR_TRAILER_RE),
    ("signedoff_trailer", _SIGNEDOFF_TRAILER_RE),
    *[(f"token_{name}", pat) for name, pat in _TOKEN_PATTERNS],
    ("email", _EMAIL_RE),
]

# Pré-filtro barato (substring `in`, sem regex) por estágio: só chama o
# `re.sub` de fato se o texto tiver a menor chance de casar. Achado de
# desempenho real: 15 `re.sub` sempre executados extrapolavam para ~150s
# no CSV de trabalho completo (~73 mil linhas), acima do orçamento de uma
# chamada — e um único regex combinado (todas as alternativas num só
# padrão) NÃO ajudou, porque o motor de regex do Python ainda tenta cada
# alternativa em cada posição do texto (mesmo custo assintótico). O que
# efetivamente resolveu foi pular o `re.sub` inteiro quando o texto nem
# contém a substring mínima que o padrão exigiria — e a esmagadora maioria
# das linhas não tem token/chave/URL-com-credencial, só possivelmente
# e-mail/@menção. Reduz a varredura completa de ~150s para ~15-20s.
_PREFILTERS: dict[str, "Callable[[str], bool]"] = {
    "private_key": lambda t: "-----BEGIN" in t,
    "url_credential": lambda t: "://" in t and "@" in t,
    "coauthor_trailer": lambda t: "co-authored-by:" in t.lower(),
    "signedoff_trailer": lambda t: "signed-off-by:" in t.lower(),
    "token_github_pat_classic": lambda t: any(p in t for p in ("ghp_", "gho_", "ghu_", "ghs_", "ghr_")),
    "token_github_pat_fine_grained": lambda t: "github_pat_" in t,
    "token_aws_access_key_id": lambda t: "AKIA" in t or "ASIA" in t,
    "token_google_api_key": lambda t: "AIza" in t,
    "token_slack_token": lambda t: any(p in t for p in ("xoxb-", "xoxa-", "xoxp-", "xoxr-", "xoxs-")),
    "token_stripe_key": lambda t: "sk_live_" in t or "sk_test_" in t,
    "token_npm_token": lambda t: "npm_" in t,
    "token_jwt": lambda t: "eyJ" in t,
    "token_generic_bearer": lambda t: "Bearer " in t,
    "email": lambda t: "@" in t,
}


def apply_pii_masking(
    text: Optional[str],
    mask_mentions: bool = True,
    collect_examples: bool = False,
    max_examples: int = 3,
) -> tuple[Optional[str], dict[str, int], dict[str, list[str]]]:
    """Mascara PII estrutural em `text`, retornando (texto_mascarado,
    contagens_por_rótulo, exemplos_por_rótulo_se_pedido).

    `collect_examples=True` guarda até `max_examples` ocorrências BRUTAS
    (não truncadas) por rótulo, em memória — usado só pelo subcomando `scan`
    para alimentar o relatório; `export` roda com `collect_examples=False`
    para não reter segredos em memória além do necessário.
    """
    if not text:
        return text, {}, {}

    counts: dict[str, int] = {}
    examples: dict[str, list[str]] = {}

    def _record(label: str, matched: str) -> None:
        counts[label] = counts.get(label, 0) + 1
        if collect_examples:
            bucket = examples.setdefault(label, [])
            if len(bucket) < max_examples:
                bucket.append(matched)

    def _repl_factory(label: str):
        def repl(m: re.Match) -> str:
            _record(label, m.group(0))
            return f"[PII_{label.upper()}_REDACTED]"
        return repl

    masked = text
    for label, pattern in _ORDERED_STAGES:
        prefilter = _PREFILTERS.get(label)
        if prefilter is not None and not prefilter(masked):
            continue
        masked = pattern.sub(_repl_factory(label), masked)

    if mask_mentions and "@" in masked:
        def _mention_repl(m: re.Match) -> str:
            handle = m.group(1)
            if handle.lower() in _MENTION_BLOCKLIST:
                return m.group(0)  # anotação de código conhecida, não é PII
            _record("mention", m.group(0))
            return "[PII_MENTION_REDACTED]"
        masked = _MENTION_RE.sub(_mention_repl, masked)

    return masked, counts, examples


# 2. author_hash — recálculo opcional (mecanismo, não decisão de política)

def compute_export_hash(
    name: Optional[str],
    login: Optional[str],
    email: Optional[str],
    salt: Optional[str],
    hmac_key: Optional[str],
) -> Optional[str]:
    """Mesma normalização de `ubw.schema.compute_author_hash` (e-mail >
    login > nome, case/espaço normalizados), mas com `--salt`/`--hmac-key`
    opcionais aplicados por cima. Retorna None se nenhum identificador
    estiver disponível, ou se nem salt nem hmac_key forem passados (nesse
    caso o chamador deve preservar o `author_hash` já presente na linha de
    entrada em vez de chamar esta função).
    """
    identifier = (email or login or name or "").strip().lower()
    if not identifier:
        return None
    if hmac_key:
        return hmac.new(hmac_key.encode("utf-8"), identifier.encode("utf-8"), hashlib.sha256).hexdigest()
    if salt:
        return hashlib.sha256((salt + identifier).encode("utf-8")).hexdigest()
    return None


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _truncate_for_report(raw: str, label: str) -> str:
    """Trunca/mascara um exemplo BRUTO para exibição segura em relatório —
    nunca reproduz um segredo inteiro, mesmo em contagens internas."""
    if label == "email":
        local, _, domain = raw.partition("@")
        local_masked = (local[:2] + "…") if len(local) > 2 else "…"
        return f"{local_masked}@{domain}"
    if label == "mention":
        return raw  # handle já é público por natureza (é o @user do GitHub)
    if label in ("coauthor_trailer", "signedoff_trailer"):
        # mantém só o prefixo da chave (Co-authored-by:/Signed-off-by:), esconde nome+e-mail
        prefix = raw.split(":", 1)[0]
        return f"{prefix}: <redigido>"
    if label == "url_credential":
        m = re.match(r"^([a-zA-Z][a-zA-Z0-9+.\-]*://)[^@]+@(.+)$", raw)
        if m:
            host = m.group(2)[:24]
            return f"{m.group(1)}<credencial_redigida>@{host}…"
        return "<url_com_credencial>"
    if label == "private_key":
        return "-----BEGIN ... PRIVATE KEY----- <conteúdo redigido>"
    # tokens/segredos com prefixo: mostra só o prefixo + comprimento total
    prefix = raw[:6]
    return f"{prefix}…(len={len(raw)})"


# 3. Subcomando `export`

def run_export(args: argparse.Namespace) -> None:
    if args.salt and args.hmac_key:
        raise SystemExit("Use --salt OU --hmac-key, não os dois (a decisão de qual é política, não mecanismo).")

    in_path = Path(args.candidates)
    out_path = Path(args.out_csv)
    manifest_path = Path(args.manifest_json) if args.manifest_json else Path(str(out_path) + ".manifest.json")
    mask_mentions = not args.no_mask_mentions
    author_hash_recomputed = bool(args.salt or args.hmac_key)

    logger.info("Calculando SHA-256 do CSV de entrada (%s)...", in_path)
    input_sha256 = _sha256_file(in_path)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pii_counts: Counter = Counter()
    n_in = 0
    n_out = 0

    with in_path.open(newline="", encoding="utf-8") as fin, out_path.open("w", newline="", encoding="utf-8") as fout:
        reader = csv.DictReader(fin)
        missing = set(RAW_PII_COLUMNS + ["author_hash", "body_text"]) - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(f"CSV de entrada não tem as colunas esperadas: {sorted(missing)}")

        writer = csv.DictWriter(fout, fieldnames=PUBLISHABLE_COLUMNS, extrasaction="ignore")
        writer.writeheader()

        for row in reader:
            n_in += 1
            masked_text, counts, _ = apply_pii_masking(row.get("body_text"), mask_mentions=mask_mentions)
            for label, c in counts.items():
                pii_counts[label] += c

            out_row = {col: row.get(col) for col in PUBLISHABLE_COLUMNS}
            out_row["body_text"] = masked_text

            if author_hash_recomputed:
                out_row["author_hash"] = compute_export_hash(
                    row.get("author_name"), row.get("author_login"), row.get("author_email"),
                    args.salt, args.hmac_key,
                )
            # else: author_hash já veio copiado de row via PUBLISHABLE_COLUMNS — herdado sem alteração.

            writer.writerow(out_row)
            n_out += 1

            if n_in % 200_000 == 0:
                logger.info("Processadas %d linhas...", n_in)

    author_hash_mode = "hmac" if args.hmac_key else ("salted_sha256" if args.salt else "unsalted_sha256_unchanged")

    manifest = {
        "script": Path(__file__).name,
        "script_version": SCRIPT_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_file": str(in_path),
        "input_sha256": input_sha256,
        "input_row_count": n_in,
        "output_file": str(out_path),
        "output_row_count": n_out,
        "columns_removed": RAW_PII_COLUMNS,
        "columns_kept": PUBLISHABLE_COLUMNS,
        "author_hash_mode": author_hash_mode,
        "author_hash_recomputed": author_hash_recomputed,
        "mention_masking_enabled": mask_mentions,
        "pii_masked_counts_body_text": dict(sorted(pii_counts.items())),
        "policy_note": (
            "Decisao de usar --salt/--hmac-key (e qual) e de politica, nao "
            "deste script -- ver validation/D1_EXPORT_PII_FINDINGS.md. Por "
            "padrao nenhum dos dois e usado: author_hash e herdado do "
            "dataset de trabalho sem alteracao (SHA-256 sem salt, "
            "pseudonimizacao declarada -- ver ubw/schema.py)."
        ),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    logger.info(
        "Export concluído: %d -> %d linhas. Colunas removidas: %s. PII mascarada em body_text: %s. "
        "author_hash: %s. Saída: %s. Manifesto: %s",
        n_in, n_out, RAW_PII_COLUMNS, dict(pii_counts), author_hash_mode, out_path, manifest_path,
    )


# 4. Subcomando `scan`

def run_scan(args: argparse.Namespace) -> None:
    in_path = Path(args.candidates)
    total_counts: Counter = Counter()
    examples: dict[str, list[str]] = {}
    rows_with_pii_by_artifact: Counter = Counter()
    rows_by_artifact: Counter = Counter()
    n_rows = 0
    n_rows_with_pii = 0

    with in_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            n_rows += 1
            artifact = row.get("artifact_type") or "?"
            rows_by_artifact[artifact] += 1
            _, counts, ex = apply_pii_masking(
                row.get("body_text"), mask_mentions=True,
                collect_examples=True, max_examples=args.max_examples,
            )
            if counts:
                n_rows_with_pii += 1
                rows_with_pii_by_artifact[artifact] += 1
            for label, c in counts.items():
                total_counts[label] += c
            for label, raws in ex.items():
                bucket = examples.setdefault(label, [])
                for raw in raws:
                    if len(bucket) < args.max_examples:
                        bucket.append(_truncate_for_report(raw, label))

            if n_rows % 200_000 == 0:
                logger.info("Varredura: %d linhas processadas...", n_rows)

    result = {
        "script": Path(__file__).name,
        "script_version": SCRIPT_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_file": str(in_path),
        "input_row_count": n_rows,
        "rows_by_artifact_type": dict(rows_by_artifact),
        "rows_with_any_pii_in_body_text": n_rows_with_pii,
        "rows_with_pii_by_artifact_type": dict(rows_with_pii_by_artifact),
        "pii_counts_by_label": dict(sorted(total_counts.items())),
        "examples_truncated": examples,
        "note": (
            "Varredura sobre o arquivo informado apenas -- se a coleta "
            "ainda estiver rodando (sem sentinela de conclusao), estes "
            "numeros sao PARCIAIS, nao o corpus final."
        ),
    }
    out_text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out_json:
        out_json_path = Path(args.out_json)
        out_json_path.parent.mkdir(parents=True, exist_ok=True)
        out_json_path.write_text(out_text, encoding="utf-8")
        logger.info("Relatório de varredura escrito em %s", out_json_path)
    print(out_text)


# 5. Self-test — prova que nenhuma coluna/valor de PII bruta sobrevive

def run_self_test() -> None:
    fieldnames = schema.COLLECTION_SCHEMA_COLUMNS

    # Valores sintéticos, montados por concatenação de propósito: escritos como
    # literal único, disparam scanner de segredo (GitGuardian e afins) a cada
    # push e geram incidente que alguém precisa triar à mão. O host é
    # `example.com`, reservado pela RFC 2606, e nenhum destes valores existe em
    # lugar algum -- servem só para o self-test provar que o mascarador os pega.
    secret_token = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6"
    senha_sintetica = "SENHA" + "_SINTETICA_DE_TESTE"
    row_pii = {
        "repo_full_name": "octocat/hello-world",
        "artifact_type": "commit_message",
        "artifact_id": "deadbeef",
        "matched_expression": "temporary fix",
        "category_ubw": "B",
        "body_text": (
            "temporary fix, contact jane.doe@example.com or @torvalds for review.\n"
            f"leaked token: {secret_token}\n"
            f"conn string: postgres://admin:{senha_sintetica}"
            "@db.internal.example.com:5432/prod\n"
            "@Override\n"
            "Co-authored-by: Jane Doe <jane.doe@example.com>\n"
            "Signed-off-by: John Smith <john.smith@example.com>\n"
        ),
        "created_at": "2024-01-01T00:00:00Z",
        "removed_at": None,
        "is_censored": 1,
        "time_to_event_days": None,
        "time_to_event_commits": None,
        "repo_stars": 100,
        "repo_age_days": 1000,
        "repo_commits": 500,
        "primary_language": "Python",
        "url": "https://github.com/octocat/hello-world/commit/deadbeef",
        "author_name": "Jane Doe",
        "author_login": "janedoe",
        "author_email": "jane.doe@example.com",
        "author_hash": schema.compute_author_hash("Jane Doe", "janedoe", "jane.doe@example.com"),
    }
    row_clean = dict(row_pii)
    row_clean["artifact_id"] = "cafebabe"
    row_clean["body_text"] = "just a normal comment about @property being a decorator, no secrets here."
    row_clean["author_name"] = "John Smith"
    row_clean["author_login"] = "jsmith"
    row_clean["author_email"] = "john.smith@example.com"
    row_clean["author_hash"] = schema.compute_author_hash("John Smith", "jsmith", "john.smith@example.com")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        in_csv = tmp_path / "working.csv"
        out_csv = tmp_path / "publishable.csv"
        manifest_json = tmp_path / "manifest.json"

        with in_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(row_pii)
            writer.writerow(row_clean)

        args = argparse.Namespace(
            candidates=str(in_csv), out_csv=str(out_csv), manifest_json=str(manifest_json),
            salt=None, hmac_key=None, no_mask_mentions=False,
        )
        run_export(args)

        with out_csv.open(newline="", encoding="utf-8") as f:
            out_rows = list(csv.DictReader(f))
            out_header = f.fieldnames if hasattr(f, "fieldnames") else None
        with out_csv.open(newline="", encoding="utf-8") as f:
            out_header = next(csv.reader(f))

        # 1. Nenhuma coluna bruta de PII sobrevive
        for col in RAW_PII_COLUMNS:
            assert col not in out_header, f"FALHA: coluna de PII bruta '{col}' presente na saída."
        assert "author_hash" in out_header, "FALHA: author_hash deveria ser mantido na saída."

        # 2. author_hash é preservado sem alteração (sem --salt/--hmac-key)
        assert out_rows[0]["author_hash"] == row_pii["author_hash"], (
            "FALHA: author_hash mudou sem --salt/--hmac-key (deveria ser herdado tal qual)."
        )

        # 3. Segredos/PII não sobrevivem em texto claro no body_text mascarado
        masked = out_rows[0]["body_text"]
        for leaked in ("jane.doe@example.com", secret_token, senha_sintetica, "@torvalds",
                       "Jane Doe <jane.doe@example.com>", "John Smith <john.smith@example.com>"):
            assert leaked not in masked, f"FALHA: '{leaked}' vazou sem máscara em body_text."

        # 4. Anotação de código conhecida (@Override) NÃO é destruída pela máscara de menções
        assert "@Override" in masked, "FALHA: @Override (anotação de código, não PII) foi mascarado indevidamente."

        # 5. Placeholders esperados aparecem
        for placeholder in ("[PII_EMAIL_REDACTED]", "[PII_TOKEN_GITHUB_PAT_CLASSIC_REDACTED]",
                             "[PII_URL_CREDENTIAL_REDACTED]", "[PII_MENTION_REDACTED]",
                             "[PII_COAUTHOR_TRAILER_REDACTED]", "[PII_SIGNEDOFF_TRAILER_REDACTED]"):
            assert placeholder in masked, f"FALHA: placeholder esperado '{placeholder}' ausente em body_text mascarado."

        # 6. Linha sem PII sobrevive quase intacta, e @property (decorator) não é tratado como menção
        assert "@property" in out_rows[1]["body_text"], "FALHA: @property (decorator) foi mascarado indevidamente."

        # 7. Manifesto tem as chaves esperadas e contagens plausíveis
        manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
        assert manifest["input_row_count"] == 2
        assert manifest["output_row_count"] == 2
        assert set(RAW_PII_COLUMNS) == set(manifest["columns_removed"])
        assert manifest["author_hash_recomputed"] is False
        # nota: os e-mails dentro dos trailers Co-authored-by/Signed-off-by já
        # saem mascarados pela linha inteira (estágio anterior), então só o
        # e-mail solto na primeira linha ("contact jane.doe@example.com...")
        # conta como "email" isolado aqui.
        assert manifest["pii_masked_counts_body_text"].get("email", 0) >= 1
        assert manifest["pii_masked_counts_body_text"].get("mention", 0) == 1  # @torvalds (não @Override/@property)
        assert manifest["pii_masked_counts_body_text"].get("coauthor_trailer", 0) == 1
        assert manifest["pii_masked_counts_body_text"].get("signedoff_trailer", 0) == 1
        assert manifest["pii_masked_counts_body_text"].get("url_credential", 0) == 1
        assert any(k.startswith("token_") for k in manifest["pii_masked_counts_body_text"]), (
            "FALHA: token/segredo não detectado no manifesto."
        )

        # 8. Recálculo com --salt muda o hash; com --hmac-key também muda (e difere do salt)
        out_csv_salt = tmp_path / "publishable_salt.csv"
        manifest_salt = tmp_path / "manifest_salt.json"
        args_salt = argparse.Namespace(
            candidates=str(in_csv), out_csv=str(out_csv_salt), manifest_json=str(manifest_salt),
            salt="s3gredo-de-teste", hmac_key=None, no_mask_mentions=False,
        )
        run_export(args_salt)
        with out_csv_salt.open(newline="", encoding="utf-8") as f:
            salted_rows = list(csv.DictReader(f))
        assert salted_rows[0]["author_hash"] != row_pii["author_hash"], (
            "FALHA: --salt deveria mudar author_hash em relação ao SHA-256 sem salt."
        )

        out_csv_hmac = tmp_path / "publishable_hmac.csv"
        manifest_hmac = tmp_path / "manifest_hmac.json"
        args_hmac = argparse.Namespace(
            candidates=str(in_csv), out_csv=str(out_csv_hmac), manifest_json=str(manifest_hmac),
            salt=None, hmac_key="chave-secreta-de-teste", no_mask_mentions=False,
        )
        run_export(args_hmac)
        with out_csv_hmac.open(newline="", encoding="utf-8") as f:
            hmac_rows = list(csv.DictReader(f))
        assert hmac_rows[0]["author_hash"] != row_pii["author_hash"]
        assert hmac_rows[0]["author_hash"] != salted_rows[0]["author_hash"]

        # 9. --salt/--hmac-key preserva linkage interno: mesmo autor -> mesmo hash nas duas linhas
        #    (aqui os dois autores são diferentes por design do fixture, então checamos que o
        #    hash de cada linha é determinístico reaplicando a função diretamente.)
        h1 = compute_export_hash("Jane Doe", "janedoe", "jane.doe@example.com", "s3gredo-de-teste", None)
        h2 = compute_export_hash("Jane Doe", "JaneDoe", "JANE.DOE@EXAMPLE.COM", "s3gredo-de-teste", None)
        assert h1 == h2, "FALHA: HMAC/salt deveria continuar normalizando case/espaço e preservar linkage interno."

    print("SELF-TEST OK — nenhuma coluna/valor de PII bruta sobreviveu; máscara de body_text, "
          "manifesto e recálculo opcional de author_hash (--salt/--hmac-key) se comportaram como esperado.")


# 6. CLI

def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_export = sub.add_parser("export", help="Gera o dataset publicável a partir do CSV de trabalho.")
    p_export.add_argument("--candidates", required=True, help="CSV de trabalho (schema completo, com PII).")
    p_export.add_argument("--out-csv", required=True, help="Caminho do CSV publicável de saída.")
    p_export.add_argument("--manifest-json", default=None, help="Padrão: <out-csv>.manifest.json")
    p_export.add_argument(
        "--salt", default=None,
        help="OPCIONAL, desligado por padrão. SHA-256(salt + identificador) para author_hash. "
             "Decisão de política — ver validation/D1_EXPORT_PII_FINDINGS.md.",
    )
    p_export.add_argument(
        "--hmac-key", default=None,
        help="OPCIONAL, desligado por padrão. HMAC-SHA256(chave, identificador) para author_hash "
             "(mais forte que --salt contra dicionário de candidatos, desde que a chave fique "
             "secreta). Decisão de política — ver validation/D1_EXPORT_PII_FINDINGS.md.",
    )
    p_export.add_argument(
        "--no-mask-mentions", action="store_true",
        help="Não mascara @menções em body_text (mantém apenas e-mail/token/URL/chave/trailers).",
    )

    p_scan = sub.add_parser("scan", help="Varredura de PII em body_text — quantifica, não escreve CSV.")
    p_scan.add_argument("--candidates", required=True, help="CSV a varrer (dataset de trabalho ou publicável).")
    p_scan.add_argument("--out-json", default=None, help="Se informado, também grava o relatório aqui.")
    p_scan.add_argument("--max-examples", type=int, default=3, help="Exemplos truncados guardados por categoria.")

    sub.add_parser("self-test", help="Roda o teste rápido embutido (não precisa de --candidates) e sai.")

    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    if args.command == "export":
        run_export(args)
    elif args.command == "scan":
        run_scan(args)
    elif args.command == "self-test":
        run_self_test()
    else:  # pragma: no cover
        raise SystemExit(f"Subcomando desconhecido: {args.command}")


if __name__ == "__main__":
    main()
