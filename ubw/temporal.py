"""Shared temporal helpers for reproducible collection and release building."""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Optional


def parse_iso_datetime(value: Optional[str]) -> Optional[dt.datetime]:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed
    except ValueError:
        return None


def days_between(start: Optional[dt.datetime], end: Optional[dt.datetime]) -> Optional[int]:
    if start is None or end is None:
        return None
    return max(0, (end - start).days)


def resolve_collection_cutoff(out_dir: Path, explicit: Optional[str]) -> dt.datetime:
    """Return one persisted cutoff shared by every resumed collection run."""
    cutoff_path = out_dir / "COLLECTION_CUTOFF"
    requested = parse_iso_datetime(explicit) if explicit else None
    if explicit and requested is None:
        raise SystemExit(f"--collection-cutoff inválido: {explicit!r}")

    if cutoff_path.exists():
        stored_text = cutoff_path.read_text(encoding="utf-8").strip()
        stored = parse_iso_datetime(stored_text)
        if stored is None:
            raise SystemExit(f"data de corte inválida em {cutoff_path}: {stored_text!r}")
        if requested is not None and requested != stored:
            raise SystemExit(
                "a data de corte solicitada diverge da já registrada em "
                f"{cutoff_path}: {requested.isoformat()} != {stored.isoformat()}"
            )
        return stored

    cutoff = requested or dt.datetime.now(dt.timezone.utc)
    cutoff = cutoff.astimezone(dt.timezone.utc)
    cutoff_path.write_text(cutoff.isoformat() + "\n", encoding="utf-8")
    return cutoff
