#!/usr/bin/env python3
"""Estimate the survey population of UBW code-comment authors.

Code-comment-only variant of `survey_population.py`, which it reuses for
loading, author identity, bot detection, and usable e-mail. The consolidated
corpus is the only source: no annotation sample, release file, or other
repository file is read. Read-only: prints aggregate counts; no e-mail
address, name, or login is printed or written.

Occurrence date: `created_at`, the author date of the commit that introduced
the comment. Windows end at the collection cutoff (23 July 2026).

Validated-only counts are reported only if the corpus itself has a validation
or label column; otherwise the script says so and estimates nothing.

Usage:
    python analysis/survey_population_code_comment.py [--corpus PATH]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from survey_population import COLLECTION_CUTOFF, DEFAULT_CORPUS, ROOT, load_corpus  # noqa: E402

WINDOW_MONTHS = (12, 18, 24)
VALIDATION_COLUMN_RE = re.compile(r"is_ubw|label|valid|gold|llm|judge|verdict|annot", re.IGNORECASE)


def unique_authors(df: pd.DataFrame) -> int:
    return df.author[df.author != ""].nunique()


def summarize(df: pd.DataFrame) -> dict:
    humans = df[~df.bot]
    emailed = humans[humans.email_ok]
    return {
        "occurrences": len(df),
        **{f"occurrences category {c}": int((df.category_ubw == c).sum()) for c in "ABC"},
        "present": int((df.is_censored == 1).sum()),
        "removed": int((df.is_censored == 0).sum()),
        "unique authors excl. bots": unique_authors(humans),
        "unique authors with usable e-mail": unique_authors(emailed),
        **{f"  ... category {c}": unique_authors(emailed[emailed.category_ubw == c]) for c in "ABC"},
        "  ... with a comment still present": unique_authors(emailed[emailed.is_censored == 1]),
        "  ... with a comment removed": unique_authors(emailed[emailed.is_censored == 0]),
    }


def print_table(title: str, rows: dict[str, dict]) -> None:
    columns = list(rows)
    print(f"\n## {title}\n")
    print("| metric | " + " | ".join(columns) + " |")
    print("|---|" + "---|" * len(columns))
    for metric in next(iter(rows.values())):
        print(f"| {metric} | " + " | ".join(str(rows[c][metric]) for c in columns) + " |")


def windows_of(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    windows = {
        f"{m} months": df[(df.created > COLLECTION_CUTOFF - pd.DateOffset(months=m))
                          & (df.created <= COLLECTION_CUTOFF)]
        for m in WINDOW_MONTHS
    }
    windows["full corpus"] = df
    return windows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    args = parser.parse_args()

    header = pd.read_csv(args.corpus, nrows=0).columns
    validation_columns = [c for c in header if VALIDATION_COLUMN_RE.search(c)]

    df = load_corpus(args.corpus)
    df = df[df.artifact_type == "code_comment"]
    print(f"corpus: {args.corpus.relative_to(ROOT)} | code comments: {len(df)} | cutoff: {COLLECTION_CUTOFF}")

    print_table("windows ending at the collection cutoff (code comments)",
                {name: summarize(w) for name, w in windows_of(df).items()})

    if not validation_columns:
        print("\nvalidation: the corpus has no validation or label column; no validated-only counts.")
        return
    # Reached only if a future corpus version adds a label column.
    print(f"\nvalidation columns found: {validation_columns}; review before use.")


if __name__ == "__main__":
    main()
