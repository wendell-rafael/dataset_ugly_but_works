#!/usr/bin/env python3
"""Estimate the population of UBW comment authors for a survey.

Read-only: loads the working corpus and the human annotation files and prints
aggregate counts. No e-mail address, name, or login is printed or written.

Occurrence date: `created_at`, the only per-record date in the corpus. It is
the author date of the introduction commit (code_comment), the commit date
(commit_message), or the creation date (issue_body, pr_body).

Usage:
    python analysis/survey_population.py [--corpus PATH] [--today YYYY-MM-DD]
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS = ROOT / "data/full_run/ubw_collected_consolidated.csv"
COLLECTION_CUTOFF = pd.Timestamp("2026-07-23T23:59:59Z")  # release manifest.json

# Human labels, joined to the corpus by (repo_full_name, url).
LABEL_FILES = {
    "calibration_200": (ROOT / "validation/panel/gold_dev_200.csv", "is_ubw_gold"),
    "multi_artifact_385": (ROOT / "validation/resultado_final/consenso_385.csv", "is_ubw_final"),
    "code_comment_269": (ROOT / "validation/sample_code_comment/analise/gold_code_comment_269.csv", "gold_is_ubw"),
}

BOT_RE = re.compile(
    r"\[bot\]|dependabot|renovate|github-actions|greenkeeper|snyk-bot|codecov|imgbot"
    r"|allcontributors|semantic-release|pre-commit-ci|mergify|copilot|(^|[-_.])bot($|[-_@.])|robot$"
)
NOREPLY_GITHUB_RE = re.compile(r"^(?:\d+\+)?([^@]+)@users\.noreply\.github\.com$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def norm(value) -> str:
    return "" if pd.isna(value) else str(value).strip().lower()


def author_key(row) -> str:
    """Best-effort identity: GitHub login when derivable, else e-mail, else name."""
    email, login, name = norm(row.author_email), norm(row.author_login), norm(row.author_name)
    match = NOREPLY_GITHUB_RE.match(email)
    if match:
        return "login:" + match.group(1)
    if email:
        return "email:" + email
    if login:
        return "login:" + login
    return "name:" + name if name else ""


def is_bot(row) -> bool:
    return any(BOT_RE.search(norm(v)) for v in (row.author_name, row.author_login, row.author_email))


def usable_email(email: str) -> bool:
    return bool(email) and EMAIL_RE.match(email) is not None and "noreply" not in email and "no-reply" not in email


def load_corpus(path: Path) -> pd.DataFrame:
    cols = ["repo_full_name", "artifact_type", "category_ubw", "created_at", "is_censored",
            "url", "author_name", "author_login", "author_email"]
    df = pd.read_csv(path, usecols=cols, low_memory=False)
    df["created"] = pd.to_datetime(df.created_at, utc=True, errors="coerce")
    df["author"] = df.apply(author_key, axis=1)
    df["bot"] = df.apply(is_bot, axis=1)
    df["email_norm"] = df.author_email.map(norm)
    df["email_ok"] = df.email_norm.map(usable_email)
    return df


def load_labels(df: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for source, (path, column) in LABEL_FILES.items():
        labels = pd.read_csv(path, usecols=["repo_full_name", "url", column])
        labels = labels.rename(columns={column: "is_ubw"}).assign(label_source=source)
        labels["is_ubw"] = labels.is_ubw.astype(str).str.lower().isin(["true", "1"])
        frames.append(labels)
    labels = pd.concat(frames).drop_duplicates(["repo_full_name", "url"], keep="last")
    return df.merge(labels, on=["repo_full_name", "url"], how="left")


def summarize(df: pd.DataFrame) -> dict:
    humans = df[~df.bot]
    return {
        "occurrences": len(df),
        "occurrences_without_author_identity": int((df.author == "").sum()),
        "occurrences_by_bots": int(df.bot.sum()),
        "by_category": df.category_ubw.value_counts().sort_index().to_dict(),
        "by_artifact": df.artifact_type.value_counts().to_dict(),
        # is_censored means different things per artifact: code_comment = still in the
        # code; issue/PR = still open (0 = closed or merged); commit_message = always 1.
        "code_comment_still_present": int(((cc := df.artifact_type == "code_comment") & (df.is_censored == 1)).sum()),
        "code_comment_removed": int((cc & (df.is_censored == 0)).sum()),
        "issue_pr_open": int(((ip := df.artifact_type.isin(["issue_body", "pr_body"])) & (df.is_censored == 1)).sum()),
        "issue_pr_closed_or_merged": int((ip & (df.is_censored == 0)).sum()),
        "unique_authors": df.author[df.author != ""].nunique(),
        "unique_authors_excl_bots": humans.author[humans.author != ""].nunique(),
        "unique_authors_with_usable_email": humans.author[humans.email_ok].nunique(),
        "unique_usable_emails": humans.email_norm[humans.email_ok].nunique(),
    }


def print_summary(title: str, summary: dict) -> None:
    print(f"\n## {title}\n")
    print("| metric | value |\n|---|---|")
    for key, value in summary.items():
        print(f"| {key} | {value} |")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--today", default="2026-10-14")
    args = parser.parse_args()

    df = load_labels(load_corpus(args.corpus))
    today = pd.Timestamp(args.today, tz="UTC") + pd.Timedelta(hours=23, minutes=59, seconds=59)
    print(f"corpus: {args.corpus.relative_to(ROOT)} ({len(df)} rows)")
    print(f"max created_at: {df.created.max()} | collection cutoff: {COLLECTION_CUTOFF}")
    print(f"days between cutoff and today: {(today - COLLECTION_CUTOFF).days}")
    print(f"rows with a human label: {df.label_source.notna().sum()} "
          f"({df.label_source.value_counts().to_dict()})")

    windows = {
        "window: 12 months before collection cutoff": COLLECTION_CUTOFF,
        "window: 12 months before today": today,
    }
    for title, end in windows.items():
        start = end - pd.DateOffset(months=12)
        in_window = df[(df.created > start) & (df.created <= end)]
        print_summary(f"{title} ({start.date()} to {end.date()})", summarize(in_window))
        validated = in_window[in_window.is_ubw == True]  # noqa: E712
        print_summary(f"{title}, human-validated UBW only", summarize(validated))

    print_summary("full corpus", summarize(df))
    print_summary("full corpus, human-validated UBW only", summarize(df[df.is_ubw == True]))  # noqa: E712

    start = COLLECTION_CUTOFF - pd.DateOffset(months=24)
    recent = df[(df.created > start) & (df.created <= COLLECTION_CUTOFF)]
    monthly = recent.groupby([recent.created.dt.strftime("%Y-%m"), "artifact_type"]).size().unstack(fill_value=0)
    monthly["total"] = monthly.sum(axis=1)
    print("\n## occurrences per month, last 24 months before cutoff\n")
    header = ["month", *monthly.columns]
    print("| " + " | ".join(header) + " |\n|" + "---|" * len(header))
    for month, row in monthly.iterrows():
        print("| " + " | ".join([month, *(str(v) for v in row)]) + " |")


if __name__ == "__main__":
    main()
