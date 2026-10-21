#!/usr/bin/env python3
"""Prepara o candidato de publicação do dataset UBW em comentários de código.

O script não altera o corpus de trabalho. Ele seleciona `code_comment`, remove
campos pessoais e campos sem interpretação confiável, explicita dados antes
codificados em `artifact_id` e `url`, mascara PII no contexto e liga o corpus ao
gabarito humano de 379 itens por um identificador estável.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ubw.lexicon import all_expressions, expression_in_text

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS = ROOT / "data/full_run/ubw_collected_consolidated.csv"
DEFAULT_GOLD = ROOT / "validation/panel/cc/human_gold_379.csv"
DEFAULT_REPAIRS = ROOT / "validation/code_comment_context_repairs.csv"
# Janelas refeitas com quebras de linha (scripts/23 --all). A coleta do
# full_run gravou os contextos sem separadores de linha.
DEFAULT_LINEBREAKS = ROOT / "validation/code_comment_context_linebreaks.csv"
SAMPLE_ORIGIN_LABELS = {"amostra_269": "new_draw", "teste_385": "earlier_round"}
RELEASE_VERSION = "1.0.1"
COLLECTION_CUTOFF = "2026-07-23T23:59:59Z"
RELEASE_ASSETS = ROOT / "release_assets/ubw-code-comments"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def parse_utc(value: str) -> pd.Timestamp:
    parsed = pd.to_datetime(value, utc=True, errors="raise")
    if not isinstance(parsed, pd.Timestamp):
        raise ValueError(f"data ISO 8601 inválida: {value!r}")
    return parsed


def recompute_censored_lifetimes(
    frame: pd.DataFrame, cutoff: pd.Timestamp
) -> tuple[pd.DataFrame, int]:
    """Recalcula apenas durações censuradas usando uma única data de corte."""
    result = frame.copy()
    introduced = pd.to_datetime(result.created_at, utc=True, errors="raise")
    removed = pd.to_datetime(result.removed_at, utc=True, errors="coerce")
    censored = result.is_censored.astype(int).eq(1)

    if removed[censored].notna().any():
        raise SystemExit("há registros censurados com removed_at preenchido")
    if removed[~censored].isna().any():
        raise SystemExit("há registros não censurados sem removed_at")
    if (introduced > cutoff).any():
        raise SystemExit("há introduções posteriores à data de corte declarada")
    if (removed.dropna() > cutoff).any():
        raise SystemExit("há remoções posteriores à data de corte declarada")

    expected_observed = (removed[~censored] - introduced[~censored]).dt.days
    source_observed = pd.to_numeric(
        result.loc[~censored, "time_to_event_days"], errors="raise"
    ).astype(int)
    if not (expected_observed.to_numpy() == source_observed.to_numpy()).all():
        raise SystemExit("duração de registros removidos diverge das datas observadas")

    previous = pd.to_numeric(
        result.loc[censored, "time_to_event_days"], errors="raise"
    ).astype(int)
    fixed = (cutoff - introduced[censored]).dt.days.astype(int)
    result.loc[censored, "time_to_event_days"] = fixed.to_numpy()
    changed = int((previous.to_numpy() != fixed.to_numpy()).sum())
    return result, changed


def load_masker():
    path = ROOT / "scripts/06_export_publishable.py"
    spec = importlib.util.spec_from_file_location("ubw_export_publishable", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.apply_pii_masking


def stable_record_id(row: pd.Series) -> str:
    identity = "\x1f".join([
        str(row.repo_full_name), str(row.artifact_id),
        str(row.matched_expression), str(row.created_at),
    ])
    return "ubwcc_" + sha256_text(identity)[:24]


def prepare_corpus(
    source: Path,
    repairs_path: Path | None = None,
    collection_cutoff: str = COLLECTION_CUTOFF,
    linebreaks_path: Path | None = None,
) -> tuple[pd.DataFrame, dict]:
    raw = pd.read_csv(source, low_memory=False)
    cc = raw.loc[raw.artifact_type.eq("code_comment")].copy()
    cutoff = parse_utc(collection_cutoff)
    cc, censored_lifetimes_recomputed = recompute_censored_lifetimes(cc, cutoff)

    path_line = cc.artifact_id.str.extract(r"^(.*):(\d+)$")
    url_parts = cc.url.str.extract(
        r"^https://github\.com/([^/]+/[^/]+)/blob/([0-9a-f]{40})/(.+)#L(\d+)$"
    )
    if path_line.isna().any().any() or url_parts.isna().any().any():
        raise SystemExit("artifact_id ou URL fora do formato esperado")
    if not (url_parts[0].to_numpy() == cc.repo_full_name.to_numpy()).all():
        raise SystemExit("repositório da URL diverge de repo_full_name")
    if not (url_parts[2].to_numpy() == path_line[0].to_numpy()).all():
        raise SystemExit("caminho da URL diverge de artifact_id")
    if not (url_parts[3].to_numpy() == path_line[1].to_numpy()).all():
        raise SystemExit("linha da URL diverge de artifact_id")

    cc["record_id"] = cc.apply(stable_record_id, axis=1)
    if cc.record_id.duplicated().any():
        raise SystemExit("record_id duplicado")

    cc["context_reconstructed"] = False
    cc["resolved_line_number"] = path_line[1].astype(int).to_numpy()
    cc["_line_breaks_restored"] = False
    if linebreaks_path is not None and linebreaks_path.exists():
        # Só janelas centradas na linha registrada: não mudam a localização.
        windows = pd.read_csv(linebreaks_path, low_memory=False)
        windows = windows.loc[windows.status.eq("recovered")]
        if windows.record_id.duplicated().any():
            raise SystemExit("record_id duplicado no arquivo de quebras de linha")
        replacement = windows.set_index("record_id").repaired_body_text
        selected = cc.record_id.isin(replacement.index)
        cc.loc[selected, "body_text"] = cc.loc[selected, "record_id"].map(replacement)
        cc.loc[selected, "_line_breaks_restored"] = True
    if repairs_path is not None and repairs_path.exists():
        repairs = pd.read_csv(repairs_path, low_memory=False)
        repairs = repairs.loc[repairs.status.eq("recovered")].copy()
        if repairs.record_id.duplicated().any():
            raise SystemExit("record_id duplicado no arquivo de reparos")
        replacement = repairs.set_index("record_id").repaired_body_text
        selected = cc.record_id.isin(replacement.index)
        cc.loc[selected, "body_text"] = cc.loc[selected, "record_id"].map(replacement)
        resolved = repairs.set_index("record_id").resolved_line_number.astype(int)
        cc.loc[selected, "resolved_line_number"] = cc.loc[selected, "record_id"].map(resolved)
        cc.loc[selected, "context_reconstructed"] = True
        cc.loc[selected, "_line_breaks_restored"] = True

    cc["context_truncated_at_2000_chars"] = cc.body_text.str.len().eq(2000)

    masker = load_masker()
    masked, masking_by_row = [], []
    for text in cc.body_text.astype(str):
        clean, counts, _ = masker(text, mask_mentions=True)
        masked.append(clean)
        masking_by_row.append(counts)
    cc["code_context"] = masked
    cc["_masking_counts"] = masking_by_row
    # Mede o texto efetivamente publicado. A união cobre tanto as variações
    # aceitas pelo léxico (por exemplo, pontuação entre palavras) quanto frases
    # literais coladas ao token seguinte em arquivos minificados.
    cc["context_contains_expression"] = [
        expression_in_text(expr, text)
        or str(expr).casefold() in str(text).casefold()
        for expr, text in zip(cc.matched_expression, cc.code_context)
    ]
    cc["context_sha256"] = cc.code_context.map(sha256_text)

    # O release só mantém linhas em que o gatilho pode ser conferido no texto
    # publicado. Exclusões causadas pelo mascaramento ficam contabilizadas no
    # manifesto, sem alterar o corpus de trabalho.
    excluded_without_visible_expression = int((~cc.context_contains_expression).sum())
    keep = cc.context_contains_expression
    cc = cc.loc[keep].copy()
    path_line = path_line.loc[keep]
    url_parts = url_parts.loc[keep]

    # Duplicação e totais de mascaramento descrevem apenas as linhas e o texto
    # efetivamente publicados.
    cluster_repos = cc.groupby("code_context").repo_full_name.nunique()
    cc["repositories_with_same_context"] = cc.code_context.map(cluster_repos).astype(int)
    pii_counts: dict[str, int] = {}
    for counts in cc._masking_counts:
        for label, count in counts.items():
            pii_counts[label] = pii_counts.get(label, 0) + count

    out = pd.DataFrame({
        "record_id": cc.record_id,
        "repository": cc.repo_full_name,
        "artifact_type": "code_comment",
        "file_path": path_line[0].to_numpy(),
        "line_number": cc.resolved_line_number.astype(int),
        "line_number_at_collection": path_line[1].astype(int).to_numpy(),
        "introduction_commit": url_parts[1].to_numpy(),
        "matched_expression": cc.matched_expression,
        "code_context": cc.code_context,
        "introduced_at": cc.created_at,
        "removed_at": cc.removed_at,
        "is_censored": cc.is_censored.astype(bool),
        "lifetime_days": cc.time_to_event_days.astype(int),
        "lifetime_commits": cc.time_to_event_commits.astype("Int64"),
        "repository_stars_at_collection": cc.repo_stars.astype(int),
        "repository_commits_at_screening": cc.repo_commits.astype(int),
        "primary_language": cc.primary_language,
        "source_url": [
            f"https://github.com/{repo}/blob/{sha}/{path}#L{line}"
            for repo, sha, path, line in zip(
                cc.repo_full_name, url_parts[1], path_line[0], cc.resolved_line_number.astype(int)
            )
        ],
        "_source_url_at_collection": cc.url,
        "context_reconstructed": cc.context_reconstructed,
        "context_contains_expression": cc.context_contains_expression,
        "context_truncated_at_2000_chars": cc.context_truncated_at_2000_chars,
        "context_sha256": cc.context_sha256,
        "repositories_with_same_context": cc.repositories_with_same_context,
    })

    stats = {
        "source_rows": len(raw),
        "output_rows": len(out),
        "repositories": int(out.repository.nunique()),
        "languages": int(out.primary_language.nunique()),
        "expressions_observed": int(out.matched_expression.nunique()),
        "excluded_without_visible_expression": excluded_without_visible_expression,
        "contexts_reconstructed": int(out.context_reconstructed.sum()),
        "locations_corrected": int(
            out.line_number.ne(out.line_number_at_collection).sum()
        ),
        "contexts_without_visible_expression": int((~out.context_contains_expression).sum()),
        "contexts_truncated_at_2000_chars": int(out.context_truncated_at_2000_chars.sum()),
        "contexts_with_line_breaks_restored": int(cc._line_breaks_restored.sum()),
        "contexts_without_line_breaks": int((~cc._line_breaks_restored).sum()),
        "rows_with_context_seen_in_multiple_repositories": int(
            out.repositories_with_same_context.gt(1).sum()
        ),
        "pii_masked_counts": dict(sorted(pii_counts.items())),
        "censored_lifetimes_recomputed": censored_lifetimes_recomputed,
    }
    return out, stats


def prepare_gold(gold_path: Path, corpus: pd.DataFrame) -> pd.DataFrame:
    gold = pd.read_csv(gold_path, low_memory=False)
    lookup = corpus.set_index(["_source_url_at_collection", "matched_expression"])["record_id"]
    keys = list(zip(gold.url, gold.matched_expression))
    record_ids = [lookup.get(key) for key in keys]
    if any(pd.isna(x) for x in record_ids):
        raise SystemExit("há itens do gabarito humano sem correspondência no corpus")

    return pd.DataFrame({
        "record_id": record_ids,
        "sample_origin": gold.origem.map(SAMPLE_ORIGIN_LABELS),
        "annotator_1_vote": gold.vote__Wendell.astype(bool),
        "annotator_2_vote": gold.vote__Bruno.astype(bool),
        "annotator_3_vote": gold.vote__Miguel.astype(bool),
        "majority_is_ubw": gold.gold.astype(bool),
    })


FIELD_DESCRIPTIONS = [
    ("record_id", "string", "Stable identifier of this occurrence."),
    ("repository", "string", "GitHub repository as owner/name."),
    ("artifact_type", "string", "Artifact type; always code_comment in this release."),
    ("file_path", "string", "File path at the introduction commit."),
    ("line_number", "integer", "1-based line of the expression at the introduction commit."),
    ("line_number_at_collection", "integer", "Line recorded during collection; kept to trace location corrections."),
    ("introduction_commit", "string", "SHA of the commit that introduced the occurrence."),
    ("matched_expression", "string", "Lexicon expression that retrieved the occurrence."),
    ("code_context", "string", "Matched line with up to three lines before and after it, separated by line breaks, limited to 2,000 characters, with personal information masked."),
    ("introduced_at", "datetime", "Author date of the introduction commit, ISO 8601."),
    ("removed_at", "datetime", "Date on which the expression ceased to appear; empty for censored observations."),
    ("is_censored", "boolean", "True when no removal was observed before the collection cutoff."),
    ("lifetime_days", "integer", "Days from introduction to removal, or to the collection cutoff if censored."),
    ("lifetime_commits", "integer", "Commits between introduction and removal; empty when censored."),
    ("repository_stars_at_collection", "integer", "Repository stars observed during collection."),
    ("repository_commits_at_screening", "integer", "Repository commit count recorded at screening."),
    ("primary_language", "string", "Primary repository language reported by GitHub (repository level, not file level)."),
    ("source_url", "string", "Permalink to the file, introduction commit, and line of the expression."),
    ("context_reconstructed", "boolean", "True when the context was rebuilt from the file at the introduction commit because the collected context did not contain the expression."),
    ("context_contains_expression", "boolean", "True when the expression can be verified in the published context."),
    ("context_truncated_at_2000_chars", "boolean", "True when the context reached the 2,000-character limit."),
    ("context_sha256", "string", "SHA-256 of the published context, useful to detect copies."),
    ("repositories_with_same_context", "integer", "Number of repositories with an identical published context."),
]

LEXICON_FIELD_DESCRIPTIONS = [
    ("expression", "string", "English expression used for lexical retrieval."),
    ("records_in_release", "integer", "Number of published records retrieved by the expression."),
]

VALIDATION_FIELD_DESCRIPTIONS = [
    ("record_id", "string", "Identifier linking the item to the main corpus."),
    ("sample_origin", "string", "Sampling round: earlier_round (110 items) or new_draw (269 items)."),
    ("annotator_1_vote", "boolean", "Independent binary decision of annotator 1."),
    ("annotator_2_vote", "boolean", "Independent binary decision of annotator 2."),
    ("annotator_3_vote", "boolean", "Independent binary decision of annotator 3."),
    ("majority_is_ubw", "boolean", "Label given by the majority of the three votes."),
]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    p.add_argument("--gold", default=str(DEFAULT_GOLD))
    p.add_argument("--repairs", default=str(DEFAULT_REPAIRS))
    p.add_argument("--linebreaks", default=str(DEFAULT_LINEBREAKS))
    p.add_argument(
        "--out-dir",
        default=None,
        help="Padrão: release/ubw-code-comments-v<release-version>.",
    )
    p.add_argument("--release-version", default=RELEASE_VERSION)
    p.add_argument("--collection-cutoff", default=COLLECTION_CUTOFF)
    args = p.parse_args()

    out_dir = (
        Path(args.out_dir)
        if args.out_dir
        else ROOT / f"release/ubw-code-comments-v{args.release_version}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    repairs_path = Path(args.repairs) if args.repairs else None
    linebreaks_path = Path(args.linebreaks) if args.linebreaks else None
    corpus, stats = prepare_corpus(
        Path(args.corpus), repairs_path, collection_cutoff=args.collection_cutoff,
        linebreaks_path=linebreaks_path,
    )
    gold = prepare_gold(Path(args.gold), corpus)
    corpus = corpus.drop(columns=["_source_url_at_collection"])

    corpus_path = out_dir / "ubw_code_comments.csv"
    gold_path = out_dir / "human_validation_379.csv"
    dictionary_path = out_dir / "data_dictionary.csv"
    lexicon_path = out_dir / "lexicon.csv"
    corpus.to_csv(corpus_path, index=False)
    gold.to_csv(gold_path, index=False)
    dictionary_rows = [
        ("ubw_code_comments.csv", *row) for row in FIELD_DESCRIPTIONS
    ] + [
        ("human_validation_379.csv", *row) for row in VALIDATION_FIELD_DESCRIPTIONS
    ] + [
        ("lexicon.csv", *row) for row in LEXICON_FIELD_DESCRIPTIONS
    ]
    pd.DataFrame(
        dictionary_rows, columns=["file", "field", "type", "description"]
    ).to_csv(dictionary_path, index=False)
    expression_counts = corpus.matched_expression.value_counts()
    pd.DataFrame({
        "expression": all_expressions(),
        "records_in_release": [int(expression_counts.get(x, 0)) for x in all_expressions()],
    }).to_csv(lexicon_path, index=False)

    # English translation for the release; the Portuguese original, as used by the
    # annotators, ships unchanged for provenance.
    shutil.copyfile(RELEASE_ASSETS / "ANNOTATION_GUIDELINE.md", out_dir / "ANNOTATION_GUIDELINE.md")
    shutil.copyfile(ROOT / "ANNOTATION_GUIDELINE.md", out_dir / "ANNOTATION_GUIDELINE.pt.md")
    shutil.copyfile(
        ROOT / "validation/sample_code_comment/manifest.json",
        out_dir / "sampling_manifest.json",
    )
    for name in (
        "README.md",
        "LICENSE_DATA",
        "CITATION.cff",
        "CHANGELOG.md",
        "zenodo_metadata.json",
        "example_usage.py",
    ):
        source_asset = RELEASE_ASSETS / name
        if not source_asset.exists():
            raise SystemExit(f"arquivo obrigatório de release ausente: {source_asset}")
        text = source_asset.read_text(encoding="utf-8")
        text = text.replace("{{RELEASE_VERSION}}", args.release_version)
        text = text.replace("{{COLLECTION_CUTOFF}}", args.collection_cutoff)
        (out_dir / name).write_text(text, encoding="utf-8")

    manifest = {
        "release": args.release_version,
        "collection_status": "complete",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_file": Path(args.corpus).name,
        "source_sha256": sha256_file(Path(args.corpus)),
        "context_repairs_sha256": (
            sha256_file(repairs_path) if repairs_path is not None and repairs_path.exists() else None
        ),
        "context_linebreaks_sha256": (
            sha256_file(linebreaks_path) if linebreaks_path is not None and linebreaks_path.exists() else None
        ),
        "collection_cutoff": args.collection_cutoff,
        "scope": "code_comment",
        **stats,
        "human_validation": {
            "n": len(gold),
            "positives_by_majority": int(gold.majority_is_ubw.sum()),
            "negatives_by_majority": int((~gold.majority_is_ubw).sum()),
            "precision": float(gold.majority_is_ubw.mean()),
        },
        "files": {},
    }
    release_files = [
        path for path in out_dir.iterdir()
        if path.is_file() and path.name != "manifest.json"
    ]
    for path in sorted(release_files):
        manifest["files"][path.name] = {
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
