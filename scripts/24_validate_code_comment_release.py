#!/usr/bin/env python3
"""Validate a prepared UBWSet code-comment release directory."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd


MAIN_FIELDS = {
    "record_id", "repository", "artifact_type", "file_path", "line_number",
    "line_number_at_collection", "introduction_commit", "matched_expression",
    "code_context", "introduced_at", "removed_at", "is_censored",
    "lifetime_days", "lifetime_commits", "repository_stars_at_collection",
    "repository_commits_at_screening", "primary_language", "source_url",
    "context_reconstructed", "context_contains_expression",
    "context_truncated_at_2000_chars", "context_sha256",
    "repositories_with_same_context",
}
VALIDATION_FIELDS = {
    "record_id", "sample_origin", "annotator_1_vote", "annotator_2_vote",
    "annotator_3_vote", "majority_is_ubw",
}
LEXICON_FIELDS = {"expression", "records_in_release"}
PERSONAL_FIELDS = {"author_name", "author_login", "author_email", "author_hash"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def parse_bool(series: pd.Series, field: str) -> pd.Series:
    normalized = series.astype(str).str.casefold()
    if not normalized.isin({"true", "false"}).all():
        fail(f"{field} contains values other than True/False")
    return normalized.eq("true")


def validate(release_dir: Path) -> dict[str, object]:
    manifest_path = release_dir / "manifest.json"
    if not manifest_path.exists():
        fail("manifest.json is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cutoff = pd.to_datetime(manifest["collection_cutoff"], utc=True, errors="raise")
    if not manifest["collection_cutoff"].endswith(("Z", "+00:00")):
        fail("collection_cutoff must include an explicit UTC offset")
    if Path(manifest["source_file"]).is_absolute():
        fail("manifest exposes an absolute source path")

    for name, metadata in manifest["files"].items():
        path = release_dir / name
        if not path.is_file():
            fail(f"manifested file is missing: {name}")
        if path.stat().st_size != metadata["bytes"]:
            fail(f"byte count differs for {name}")
        if sha256_file(path) != metadata["sha256"]:
            fail(f"SHA-256 differs for {name}")

    corpus = pd.read_csv(release_dir / "ubw_code_comments.csv", low_memory=False)
    validation = pd.read_csv(release_dir / "human_validation_379.csv", low_memory=False)
    lexicon = pd.read_csv(release_dir / "lexicon.csv", low_memory=False)
    dictionary = pd.read_csv(release_dir / "data_dictionary.csv", low_memory=False)

    if set(corpus.columns) != MAIN_FIELDS or len(corpus.columns) != 23:
        fail("main corpus schema differs from the documented 23 fields")
    if set(validation.columns) != VALIDATION_FIELDS:
        fail("human-validation schema differs from the expected fields")
    if set(lexicon.columns) != LEXICON_FIELDS:
        fail("lexicon schema differs from the expected fields")
    if PERSONAL_FIELDS.intersection(corpus.columns):
        fail("personal author fields are present in the public corpus")
    if corpus.record_id.duplicated().any():
        fail("record_id is not unique")
    if validation.record_id.duplicated().any():
        fail("validation record_id is not unique")
    if not set(validation.record_id).issubset(set(corpus.record_id)):
        fail("validation contains record_ids absent from the corpus")

    censored = parse_bool(corpus.is_censored, "is_censored")
    introduced = pd.to_datetime(corpus.introduced_at, utc=True, errors="raise")
    removed = pd.to_datetime(corpus.removed_at, utc=True, errors="coerce")
    lifetimes = pd.to_numeric(corpus.lifetime_days, errors="raise").astype(int)
    if removed[censored].notna().any():
        fail("a right-censored record has removed_at")
    if removed[~censored].isna().any():
        fail("an observed-removal record lacks removed_at")
    if (introduced > cutoff).any() or (removed.dropna() > cutoff).any():
        fail("an event occurs after the declared cutoff")
    expected_censored = (cutoff - introduced[censored]).dt.days.astype(int)
    if not (lifetimes[censored].to_numpy() == expected_censored.to_numpy()).all():
        fail("right-censored lifetime_days does not use the single declared cutoff")
    expected_observed = (removed[~censored] - introduced[~censored]).dt.days.astype(int)
    if not (lifetimes[~censored].to_numpy() == expected_observed.to_numpy()).all():
        fail("observed lifetime_days differs from introduction/removal timestamps")

    counts = corpus.matched_expression.value_counts().to_dict()
    published_counts = dict(zip(lexicon.expression, lexicon.records_in_release.astype(int)))
    if len(published_counts) != 25:
        fail("lexicon.csv must contain 25 expressions")
    if {key: counts.get(key, 0) for key in published_counts} != published_counts:
        fail("lexicon counts do not match the corpus")

    described = {
        file_name: set(group.field)
        for file_name, group in dictionary.groupby("file")
    }
    expected_schemas = {
        "ubw_code_comments.csv": MAIN_FIELDS,
        "human_validation_379.csv": VALIDATION_FIELDS,
        "lexicon.csv": LEXICON_FIELDS,
    }
    if described != expected_schemas:
        fail("data_dictionary.csv does not exactly cover all published CSV fields")

    majority = parse_bool(validation.majority_is_ubw, "majority_is_ubw")
    if len(corpus) != manifest["output_rows"]:
        fail("manifest output_rows differs from the corpus")
    if corpus.repository.nunique() != manifest["repositories"]:
        fail("manifest repository count differs from the corpus")
    if len(validation) != manifest["human_validation"]["n"]:
        fail("manifest validation n differs from the validation CSV")
    if int(majority.sum()) != manifest["human_validation"]["positives_by_majority"]:
        fail("manifest validation positives differ from the validation CSV")

    example = subprocess.run(
        [sys.executable, "example_usage.py"], cwd=release_dir,
        capture_output=True, text=True, check=False,
    )
    if example.returncode != 0:
        fail(f"example_usage.py failed: {example.stderr.strip()}")

    return {
        "status": "PASS",
        "release": manifest["release"],
        "records": len(corpus),
        "repositories": int(corpus.repository.nunique()),
        "validation_records": len(validation),
        "majority_positive": int(majority.sum()),
        "observed_removals": int((~censored).sum()),
        "right_censored": int(censored.sum()),
        "collection_cutoff": manifest["collection_cutoff"],
        "files_verified": len(manifest["files"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(args.release_dir), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
