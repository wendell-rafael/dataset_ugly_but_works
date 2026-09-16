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
RELEASE_VERSION = "1.0.0"
COLLECTION_CUTOFF = "2026-07-23"
DEFAULT_OUT = ROOT / "release/ubw-code-comments-v1.0.0"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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


def prepare_corpus(source: Path, repairs_path: Path | None = None) -> tuple[pd.DataFrame, dict]:
    raw = pd.read_csv(source, low_memory=False)
    cc = raw.loc[raw.artifact_type.eq("code_comment")].copy()

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
        "rows_with_context_seen_in_multiple_repositories": int(
            out.repositories_with_same_context.gt(1).sum()
        ),
        "pii_masked_counts": dict(sorted(pii_counts.items())),
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
        "sample_origin": gold.origem,
        "annotator_1_vote": gold.vote__Wendell.astype(bool),
        "annotator_2_vote": gold.vote__Bruno.astype(bool),
        "annotator_3_vote": gold.vote__Miguel.astype(bool),
        "majority_is_ubw": gold.gold.astype(bool),
    })


FIELD_DESCRIPTIONS = [
    ("record_id", "string", "Identificador estável desta ocorrência."),
    ("repository", "string", "Repositório GitHub no formato owner/name."),
    ("artifact_type", "string", "Tipo do artefato; constante code_comment nesta versão."),
    ("file_path", "string", "Caminho do arquivo no commit de introdução."),
    ("line_number", "integer", "Linha da expressão no commit de introdução, indexada a partir de 1."),
    ("line_number_at_collection", "integer", "Linha registrada durante a coleta; preservada para rastrear correções de localização."),
    ("introduction_commit", "string", "SHA do commit em que a ocorrência foi introduzida."),
    ("matched_expression", "string", "Expressão do léxico que originou a coleta."),
    ("code_context", "string", "Janela de até três linhas antes/depois da linha encontrada, limitada a 2.000 caracteres e com PII mascarada."),
    ("introduced_at", "datetime", "Data do commit de introdução em ISO 8601."),
    ("removed_at", "datetime", "Data em que a expressão deixou de aparecer; vazia para observações censuradas."),
    ("is_censored", "boolean", "True quando a expressão ainda estava presente ou não houve remoção observável até o corte."),
    ("lifetime_days", "integer", "Dias entre introdução e remoção, ou entre introdução e data de corte se censurada."),
    ("lifetime_commits", "integer", "Commits entre introdução e remoção; vazio quando censurada."),
    ("repository_stars_at_collection", "integer", "Estrelas observadas durante a coleta."),
    ("repository_commits_at_screening", "integer", "Contagem de commits registrada na triagem do repositório."),
    ("primary_language", "string", "Linguagem principal informada pelo GitHub."),
    ("source_url", "string", "Permalink para arquivo, commit e linha confirmada da expressão."),
    ("context_reconstructed", "boolean", "Indica que o contexto foi reconstruído do arquivo no commit de introdução durante a preparação da publicação."),
    ("context_contains_expression", "boolean", "Indica se a expressão é verificável no contexto armazenado."),
    ("context_truncated_at_2000_chars", "boolean", "Indica que o contexto atingiu o limite de 2.000 caracteres."),
    ("context_sha256", "string", "Hash SHA-256 do contexto publicado, útil para detectar cópias."),
    ("repositories_with_same_context", "integer", "Número de repositórios com contexto textual idêntico."),
]

VALIDATION_FIELD_DESCRIPTIONS = [
    ("record_id", "string", "Identificador que liga o item ao corpus principal."),
    ("sample_origin", "string", "Origem do item dentro do desenho amostral."),
    ("annotator_1_vote", "boolean", "Decisão binária independente do anotador 1."),
    ("annotator_2_vote", "boolean", "Decisão binária independente do anotador 2."),
    ("annotator_3_vote", "boolean", "Decisão binária independente do anotador 3."),
    ("majority_is_ubw", "boolean", "Gabarito definido pela maioria dos três votos."),
]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    p.add_argument("--gold", default=str(DEFAULT_GOLD))
    p.add_argument("--repairs", default=str(DEFAULT_REPAIRS))
    p.add_argument("--out-dir", default=str(DEFAULT_OUT))
    args = p.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    repairs_path = Path(args.repairs) if args.repairs else None
    corpus, stats = prepare_corpus(Path(args.corpus), repairs_path)
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
    ]
    pd.DataFrame(
        dictionary_rows, columns=["file", "field", "type", "description"]
    ).to_csv(dictionary_path, index=False)
    expression_counts = corpus.matched_expression.value_counts()
    pd.DataFrame({
        "expression": all_expressions(),
        "records_in_release": [int(expression_counts.get(x, 0)) for x in all_expressions()],
    }).to_csv(lexicon_path, index=False)

    shutil.copyfile(ROOT / "ANNOTATION_GUIDELINE.md", out_dir / "ANNOTATION_GUIDELINE.md")
    shutil.copyfile(
        ROOT / "validation/sample_code_comment/manifest.json",
        out_dir / "sampling_manifest.json",
    )

    manifest = {
        "release": RELEASE_VERSION,
        "collection_status": "complete",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_file": str(Path(args.corpus)),
        "source_sha256": sha256_file(Path(args.corpus)),
        "context_repairs_sha256": (
            sha256_file(repairs_path) if repairs_path is not None and repairs_path.exists() else None
        ),
        "collection_cutoff": COLLECTION_CUTOFF,
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
