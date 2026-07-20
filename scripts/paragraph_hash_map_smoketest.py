#!/usr/bin/env python3
"""Registered determinism fixture for paragraph_hash_map.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "paragraph_hash_map.py"
PROJECT = ROOT / "scripts" / "fixtures" / "paragraph_hash_map_smoketest" / "minimal_project"


def _run() -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--project-root", str(PROJECT)],
        capture_output=True,
        check=False,
    )


def main() -> int:
    first, second = _run(), _run()
    if first.returncode or second.returncode:
        detail = (first.stderr + second.stderr).decode("utf-8", errors="replace")[-1200:]
        print(
            f"paragraph_hash_map failed: exits {first.returncode}/{second.returncode}: {detail}",
            file=sys.stderr,
        )
        return 1
    if first.stdout != second.stdout:
        print("paragraph_hash_map output is not byte-deterministic", file=sys.stderr)
        return 1
    print("PASS: paragraph_hash_map output is byte-deterministic")
    return 0


if __name__ == "__main__":
    sys.exit(main())
