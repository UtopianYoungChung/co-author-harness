#!/usr/bin/env python3
"""Registered PASS/BLOCK fixtures for artefact_frontmatter_validate.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from semantic_graph_fixture_support import semantic_graph_fixture_environment


ROOT = Path(__file__).resolve().parent.parent
VALIDATOR = ROOT / "scripts" / "artefact_frontmatter_validate.py"
FIXTURES = ROOT / "scripts" / "fixtures" / "artefact_frontmatter_smoketest"
CASES = (
    ("pass/reviews/dispatch_plan_C0001.md", 0),
    ("pass/reviews/ph3_findings_p21b_2026-04-22_iter0.md", 0),
    ("pass/reviews/reflector_full_p21b_2026-04-22.md", 0),
    ("block/reviews/dispatch_plan_C0002.md", 3),
    ("block/reviews/dispatch_plan_p21b_block_bad_check_profile.md", 3),
    ("block/reviews/ph3_findings_p21b_bad_routing_rationale.md", 3),
    ("block/reviews/reflector_full_p21b_bad_demoted_severity.md", 3),
)


def main() -> int:
    failures: list[str] = []
    for rel, expected in CASES:
        proc = subprocess.run(
            [sys.executable, str(VALIDATOR), str(FIXTURES / rel)],
            capture_output=True,
            check=False,
        )
        if proc.returncode != expected:
            tail = (proc.stdout + proc.stderr).decode("utf-8", errors="replace")[-800:]
            failures.append(f"{rel}: exit {proc.returncode}, expected {expected}: {tail}")
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print(f"PASS: artefact-frontmatter validator {len(CASES)} fixtures")
    return 0


if __name__ == "__main__":
    with semantic_graph_fixture_environment():
        sys.exit(main())
