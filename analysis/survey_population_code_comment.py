#!/usr/bin/env python3
"""Estimate the survey population of UBW code-comment authors.

Code-comment-only variant of `survey_population.py`, which it reuses for
loading, author identity, bot detection, usable e-mail, and human labels.
Read-only: prints aggregate counts; no e-mail address, name, or login is
printed or written.

Occurrence date: `created_at`, the author date of the commit that introduced
the comment. Windows end at the collection cutoff (23 July 2026).

The corpus records only the author of the introduction commit, so removers
cannot be counted.

Usage:
    python analysis/survey_population_code_comment.py [--corpus PATH]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from survey_population import (  # noqa: E402
    COLLECTION_CUTOFF,
    DEFAULT_CORPUS,
    ROOT,
    load_corpus,
    load_labels,
)

WINDOW_MONTHS = (12, 18, 24)
# Majority-vote precision on 379 code comments, with its 95% Wilson interval.
PRECISION, PRECISION_LOW, PRECISION_HIGH = 0.926, 0.895, 0.948

EXTENSION_LANGUAGE = {
    ".py": "Python", ".java": "Java", ".js": "JavaScript", ".jsx": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".c": "C", ".h": "C/C++ header",
    ".cpp": "C++", ".cc": "C++", ".hpp": "C++", ".go": "Go", ".rb": "Ruby",
}


def unique_authors(df: pd.DataFrame) -> int:
    return df.author[df.author != ""].nunique()


def summarize(df: pd.DataFrame) -> dict:
    humans = df[~df.bot]
    emailed = humans[humans.email_ok]
    present, removed = df.is_censored == 1, df.is_censored == 0
    summary = {
        "occurrences": len(df),
        **{f"occurrences category {c}": int((df.category_ubw == c).sum()) for c in "ABC"},
        "present": int(present.sum()),
        "removed": int(removed.sum()),
        "unique authors excl. bots": unique_authors(humans),
        "unique authors with usable e-mail": unique_authors(emailed),
        **{f"  ... category {c}": unique_authors(emailed[emailed.category_ubw == c]) for c in "ABC"},
        "  ... with a comment still present": unique_authors(emailed[emailed.is_censored == 1]),
        "  ... with a comment removed": unique_authors(emailed[emailed.is_censored == 0]),
    }
    return summary


def print_table(title: str, rows: dict[str, dict]) -> None:
    columns = list(rows)
    print(f"\n## {title}\n")
    print("| metric | " + " | ".join(columns) + " |")
    print("|---|" + "---|" * len(columns))
    for metric in next(iter(rows.values())):
        print(f"| {metric} | " + " | ".join(str(rows[c][metric]) for c in columns) + " |")


def print_counts(title: str, counts: pd.Series) -> None:
    print(f"\n## {title}\n")
    print("| value | occurrences | share |\n|---|---|---|")
    for key, value in counts.items():
        print(f"| {key} | {value} | {value / counts.sum():.1%} |")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    args = parser.parse_args()

    corpus = load_corpus(args.corpus)
    # load_corpus keeps the base columns; attach the language by row order before merging labels.
    corpus["primary_language"] = pd.read_csv(args.corpus, usecols=["primary_language"]).primary_language
    df = load_labels(corpus)
    df = df[df.artifact_type == "code_comment"].copy()
    print(f"corpus: {args.corpus.relative_to(ROOT)} | code comments: {len(df)} | cutoff: {COLLECTION_CUTOFF}")
    print("removers: not available (the corpus stores only the introduction author)")

    windows = {
        f"{m} months": df[(df.created > COLLECTION_CUTOFF - pd.DateOffset(months=m))
                          & (df.created <= COLLECTION_CUTOFF)]
        for m in WINDOW_MONTHS
    }
    windows["full corpus"] = df
    print_table("windows ending at the collection cutoff (code comments)",
                {name: summarize(w) for name, w in windows.items()})

    validated = {}
    for name, w in windows.items():
        labeled = w[w.label_source.notna()]
        validated[name] = {
            "labeled occurrences": len(labeled),
            "validated UBW": int((labeled.is_ubw == True).sum()),  # noqa: E712
            "validated UBW authors excl. bots": unique_authors(labeled[(labeled.is_ubw == True) & ~labeled.bot]),  # noqa: E712
            "estimated UBW occurrences (92.6%)": round(len(w) * PRECISION),
            "  95% interval": f"{round(len(w) * PRECISION_LOW)}-{round(len(w) * PRECISION_HIGH)}",
        }
    print_table("human-validated UBW and estimated population (code comments)", validated)

    print_counts("primary repository language, top 10 (full corpus)",
                 df.primary_language.fillna("unknown").value_counts().head(10))
    extension = df.url.str.extract(r"(\.[A-Za-z0-9]+)#L\d+$")[0].str.lower()
    print_counts("file language from extension (full corpus)",
                 extension.map(EXTENSION_LANGUAGE).fillna("other").value_counts())

    start = COLLECTION_CUTOFF - pd.DateOffset(months=24)
    recent = df[(df.created > start) & (df.created <= COLLECTION_CUTOFF)]
    monthly = recent.groupby(recent.created.dt.strftime("%Y-%m")).agg(
        occurrences=("created", "size"),
        present=("is_censored", lambda s: int((s == 1).sum())),
        removed=("is_censored", lambda s: int((s == 0).sum())),
    )
    print("\n## occurrences per month, last 24 months before cutoff (first and last months are partial)\n")
    print("| month | occurrences | present | removed |\n|---|---|---|---|")
    for month, row in monthly.iterrows():
        print(f"| {month} | {row.occurrences} | {row.present} | {row.removed} |")


if __name__ == "__main__":
    main()
