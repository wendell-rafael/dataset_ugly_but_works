from __future__ import annotations

import datetime as dt
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ubw.temporal import resolve_collection_cutoff


def load_script(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


release = load_script("release_preparation", "22_prepare_code_comment_release.py")


class CollectionCutoffTest(unittest.TestCase):
    def test_cutoff_is_persisted_and_reused(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            first = resolve_collection_cutoff(out, "2026-07-23T23:59:59Z")
            second = resolve_collection_cutoff(out, None)
            self.assertEqual(first, second)
            self.assertEqual(first, dt.datetime(2026, 7, 23, 23, 59, 59, tzinfo=dt.timezone.utc))

    def test_conflicting_resume_cutoff_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            resolve_collection_cutoff(out, "2026-07-23T23:59:59Z")
            with self.assertRaises(SystemExit):
                resolve_collection_cutoff(out, "2026-07-24T23:59:59Z")

    def test_censored_lifetimes_share_one_cutoff(self):
        frame = pd.DataFrame({
            "created_at": ["2026-07-20T12:00:00Z", "2026-07-21T12:00:00Z"],
            "removed_at": [None, None],
            "is_censored": [1, 1],
            "time_to_event_days": [0, 99],
        })
        fixed, changed = release.recompute_censored_lifetimes(
            frame, release.parse_utc("2026-07-23T23:59:59Z")
        )
        self.assertEqual(fixed.time_to_event_days.tolist(), [3, 2])
        self.assertEqual(changed, 2)

    def test_observed_lifetime_is_validated_and_preserved(self):
        frame = pd.DataFrame({
            "created_at": ["2026-07-20T12:00:00Z"],
            "removed_at": ["2026-07-22T13:00:00Z"],
            "is_censored": [0],
            "time_to_event_days": [2],
        })
        fixed, changed = release.recompute_censored_lifetimes(
            frame, release.parse_utc("2026-07-23T23:59:59Z")
        )
        self.assertEqual(fixed.time_to_event_days.tolist(), [2])
        self.assertEqual(changed, 0)


if __name__ == "__main__":
    unittest.main()
