#!/usr/bin/env python3
"""Validate and create a reproducible ZIP for a UBWSet release directory."""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import zipfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release_dir", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    release_dir = args.release_dir.resolve()
    validator = Path(__file__).with_name("24_validate_code_comment_release.py")
    subprocess.run([sys.executable, str(validator), str(release_dir)], check=True)
    output = (
        args.output or release_dir.parent / f"{release_dir.name}.zip"
    ).resolve()

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(release_dir.iterdir(), key=lambda item: item.name):
            if not path.is_file():
                continue
            info = zipfile.ZipInfo(f"{release_dir.name}/{path.name}")
            info.date_time = (2026, 9, 23, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())

    checksum = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_name(f"{output.name}.sha256").write_text(
        f"{checksum}  {output.name}\n", encoding="utf-8"
    )
    print(output)


if __name__ == "__main__":
    main()
