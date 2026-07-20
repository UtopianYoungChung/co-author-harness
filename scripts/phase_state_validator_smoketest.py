#!/usr/bin/env python3
"""Registered PASS/BLOCK fixtures for phase_state_validate.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
VALIDATOR = ROOT / "scripts" / "phase_state_validate.py"
FIXTURES = ROOT / "scripts" / "fixtures" / "phase_state_smoketest"


def main() -> int:
    cases = (("pass", 0), ("block", 4))
    failures: list[str] = []
    for name, expected in cases:
        proc = subprocess.run(
            [sys.executable, str(VALIDATOR), "--project-root", str(FIXTURES / name)],
            capture_output=True,
            check=False,
        )
        if proc.returncode != expected:
            tail = (proc.stdout + proc.stderr).decode("utf-8", errors="replace")[-800:]
            failures.append(f"{name}: exit {proc.returncode}, expected {expected}: {tail}")
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print("PASS: phase-state validator PASS/BLOCK fixtures")
    return 0


if __name__ == "__main__":
    sys.exit(main())
