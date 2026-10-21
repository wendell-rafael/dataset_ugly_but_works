#!/usr/bin/env python3
"""Small dependency-free UBWSet loading and integrity example."""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def main() -> None:
    records = read_csv("ubw_code_comments.csv")
    validation = read_csv("human_validation_379.csv")
    votes_by_id = {row["record_id"]: row for row in validation}
    validated = [row for row in records if row["record_id"] in votes_by_id]

    assert len(records) == 26_030
    assert len({row["record_id"] for row in records}) == len(records)
    assert len(validation) == 379
    assert len(validated) == 379

    removals = sum(row["is_censored"].lower() == "false" for row in records)
    censored = len(records) - removals
    positives = sum(row["majority_is_ubw"].lower() == "true" for row in validation)
    top_expressions = Counter(row["matched_expression"] for row in records).most_common(5)

    print(f"Records: {len(records):,}")
    print(f"Observed removals: {removals:,}")
    print(f"Right-censored: {censored:,}")
    print(f"Validated records: {len(validation)} ({positives} majority-positive)")
    print("Top expressions:")
    for expression, count in top_expressions:
        print(f"  {expression}: {count:,}")


if __name__ == "__main__":
    main()
