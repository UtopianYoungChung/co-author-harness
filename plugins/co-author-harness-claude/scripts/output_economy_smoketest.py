#!/usr/bin/env python3
"""
output_economy_smoketest.py — fixture-backed smoke test for the v0.14.0 output
economy (F7 evidence packet, events.jsonl, F8 final round report).

Validates only artefact-shaped paths (F7 JSON + F8 Markdown). The fixture tree
also contains classification.md and phase_state.json for path-hygiene
realism; those are not passed to artefact_frontmatter_validate.py.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def plugin_root() -> Path:
    return Path(__file__).resolve().parent.parent


def main() -> int:
    root = plugin_root()
    fx = root / "scripts/fixtures/output_economy_smoketest"
    reviews = fx / "reviews"
    evidence = reviews / ".harness" / "evidence" / "round_2026-05-04_001__ph2__001.json"
    f8 = reviews / "final_round_report_round_2026-05-04_001.md"
    events = reviews / ".harness" / "events.jsonl"
    pointer = reviews / "consolidated_findings_report.md"

    for p in (evidence, f8, events, pointer):
        if not p.is_file():
            sys.stderr.write(f"smoketest: missing fixture file: {p}\n")
            return 2

    # No routine per-phase Markdown findings artefact
    bad = reviews / "ph2_findings_round_2026-05-04_001__ph2__001.md"
    if bad.exists():
        sys.stderr.write(f"smoketest: unexpected file (remove for clean fixture): {bad}\n")
        return 2

    # events.jsonl must reference F7 path and ids
    line = events.read_text(encoding="utf-8").strip().splitlines()[0]
    ev = json.loads(line)
    if ev.get("round_id") != "round_2026-05-04_001":
        sys.stderr.write("smoketest: events.jsonl round_id mismatch\n")
        return 2
    if ev.get("event_id") != "round_2026-05-04_001__ph2__001":
        sys.stderr.write("smoketest: events.jsonl event_id mismatch\n")
        return 2

    val = root / "scripts" / "artefact_frontmatter_validate.py"
    proc = subprocess.run(
        [sys.executable, str(val), str(evidence), str(f8)],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout or "")
        sys.stderr.write(proc.stderr or "")
        sys.stderr.write(
            f"smoketest: artefact_frontmatter_validate.py exit {proc.returncode}\n"
        )
        return proc.returncode or 3

    body = pointer.read_text(encoding="utf-8")
    if "final_round_report_round_2026-05-04_001" not in body:
        sys.stderr.write("smoketest: compatibility pointer missing canonical path\n")
        return 2

    print(
        "output_economy_smoketest: PASS "
        "(F7+F8 validated; events.jsonl ids OK; compatibility pointer present)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
