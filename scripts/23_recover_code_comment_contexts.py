#!/usr/bin/env python3
"""Reconstrói contextos de code_comment em que o match não ficou visível.

Baixa somente o arquivo no commit de introdução, localiza a ocorrência mais
próxima da linha registrada e grava um CSV incremental de reparos. O corpus de
trabalho permanece intacto; o script de publicação aplica os reparos pelo
``record_id`` estável.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ubw.lexicon import expression_in_text

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS = ROOT / "data/full_run/ubw_collected_consolidated.csv"
DEFAULT_OUT = ROOT / "validation/code_comment_context_repairs.csv"
FIELDS = [
    "record_id", "repository", "artifact_id", "matched_expression",
    "introduction_commit", "file_path", "line_number", "status",
    "resolved_line_number", "original_context_sha256", "repaired_body_text",
    "detail",
]
_local = threading.local()


def stable_record_id(row: pd.Series) -> str:
    identity = "\x1f".join([
        str(row.repo_full_name), str(row.artifact_id),
        str(row.matched_expression), str(row.created_at),
    ])
    return "ubwcc_" + hashlib.sha256(identity.encode()).hexdigest()[:24]


def visible(expression: str, text: str) -> bool:
    return expression_in_text(expression, text) or expression.casefold() in text.casefold()


def session() -> requests.Session:
    if not hasattr(_local, "session"):
        s = requests.Session()
        s.headers.update({"User-Agent": "ubw-context-recovery/1.0"})
        token = os.environ.get("GITHUB_TOKEN", "").strip()
        if token:
            s.headers.update({"Authorization": f"Bearer {token}"})
        _local.session = s
    return _local.session


@lru_cache(maxsize=32)
def fetch_file(repo: str, sha: str, path: str) -> tuple[str | None, str]:
    url = f"https://raw.githubusercontent.com/{repo}/{sha}/{quote(path, safe='/')}"
    last = ""
    for attempt in range(3):
        try:
            response = session().get(url, timeout=(15, 90))
            if response.status_code == 200:
                if len(response.content) > 100 * 1024 * 1024:
                    return None, "arquivo maior que 100 MB"
                response.encoding = response.encoding or "utf-8"
                return response.text, ""
            last = f"HTTP {response.status_code}"
            if response.status_code in (404, 410):
                break
        except requests.RequestException as exc:
            last = type(exc).__name__
        time.sleep(2 ** attempt)
    return None, last


def expression_pattern(expression: str) -> re.Pattern[str]:
    words = re.findall(r"[a-z0-9]+", expression.casefold())
    return re.compile(r"[^a-z0-9]+".join(map(re.escape, words)), re.IGNORECASE)


def rebuild_context(content: str, expression: str, expected_line: int) -> tuple[str | None, int | None]:
    lines = content.splitlines()
    pattern = expression_pattern(expression)
    candidates: list[tuple[int, re.Match[str]]] = []
    for index, line in enumerate(lines):
        match = pattern.search(line)
        if match or expression.casefold() in line.casefold():
            if match is None:
                start = line.casefold().find(expression.casefold())
                match = re.compile(re.escape(expression), re.IGNORECASE).search(line, start)
            if match is not None:
                candidates.append((index, match))
    if not candidates:
        return None, None

    index, line_match = min(candidates, key=lambda pair: abs((pair[0] + 1) - expected_line))
    start_line = max(0, index - 3)
    end_line = min(len(lines), index + 4)
    window_lines = lines[start_line:end_line]
    window = "\n".join(window_lines)
    if len(window) <= 2000 and visible(expression, window):
        return window, index + 1

    before = sum(len(line) + 1 for line in lines[start_line:index])
    center = before + line_match.start() + max(1, line_match.end() - line_match.start()) // 2
    left = max(0, center - 1000)
    right = min(len(window), left + 2000)
    left = max(0, right - 2000)
    excerpt = window[left:right]
    return (excerpt, index + 1) if visible(expression, excerpt) else (None, index + 1)


def recover(row: dict) -> dict:
    content, detail = fetch_file(row["repo_full_name"], row["sha"], row["path"])
    result = {
        "record_id": row["record_id"], "repository": row["repo_full_name"],
        "artifact_id": row["artifact_id"], "matched_expression": row["matched_expression"],
        "introduction_commit": row["sha"], "file_path": row["path"],
        "line_number": row["line_number"], "status": "fetch_failed",
        "resolved_line_number": "", "original_context_sha256": row["original_hash"],
        "repaired_body_text": "", "detail": detail,
    }
    if content is None:
        return result
    context, resolved_line = rebuild_context(content, row["matched_expression"], row["line_number"])
    result["resolved_line_number"] = resolved_line or ""
    if context is None:
        result["status"] = "match_not_found"
        result["detail"] = "expressão não localizada no arquivo recuperado"
    else:
        result["status"] = "recovered"
        result["repaired_body_text"] = context
        result["detail"] = ""
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--max-workers", type=int, default=8)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    raw = pd.read_csv(args.corpus, low_memory=False)
    cc = raw.loc[raw.artifact_type.eq("code_comment")].copy()
    missing = ~pd.Series([
        visible(str(expr), str(text))
        for expr, text in zip(cc.matched_expression, cc.body_text)
    ], index=cc.index)
    targets = cc.loc[missing].copy()
    targets["record_id"] = targets.apply(stable_record_id, axis=1)
    parsed = targets.url.str.extract(
        r"^https://github\.com/([^/]+/[^/]+)/blob/([0-9a-f]{40})/(.+)#L(\d+)$"
    )
    targets["sha"] = parsed[1]
    targets["path"] = parsed[2]
    targets["line_number"] = parsed[3].astype(int)
    targets["original_hash"] = targets.body_text.astype(str).map(
        lambda x: hashlib.sha256(x.encode()).hexdigest()
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    completed: set[str] = set()
    if out.exists() and out.stat().st_size:
        previous = pd.read_csv(out, low_memory=False)
        completed = set(previous.loc[previous.status.eq("recovered"), "record_id"])
    pending = targets.loc[~targets.record_id.isin(completed)]
    if args.limit is not None:
        pending = pending.head(args.limit)
    rows = pending.to_dict("records")
    print(f"alvos={len(targets)} concluídos={len(completed)} pendentes={len(rows)}")
    if not rows:
        return

    write_lock = threading.Lock()
    header = not out.exists() or out.stat().st_size == 0
    counts: dict[str, int] = {}
    with out.open("a", encoding="utf-8", newline="") as handle:
        with ThreadPoolExecutor(max_workers=args.max_workers) as pool:
            futures = [pool.submit(recover, row) for row in rows]
            for number, future in enumerate(as_completed(futures), 1):
                result = future.result()
                with write_lock:
                    pd.DataFrame([result], columns=FIELDS).to_csv(handle, index=False, header=header)
                    handle.flush()
                    header = False
                counts[result["status"]] = counts.get(result["status"], 0) + 1
                if number % 50 == 0 or number == len(rows):
                    print(f"processados={number}/{len(rows)} resultado={counts}")

    # Uma retomada pode substituir uma falha transitória por sucesso. Mantém
    # apenas o resultado mais recente de cada ocorrência no log final.
    consolidated = pd.read_csv(out, low_memory=False).drop_duplicates(
        subset=["record_id"], keep="last"
    )
    consolidated.to_csv(out, index=False)


if __name__ == "__main__":
    main()
