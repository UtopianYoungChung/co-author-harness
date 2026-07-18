#!/usr/bin/env python3
"""
A8 (P-R-3) — Pre-write sanity: section deliverable paths in phase_state.json resolve.

Run from project root before Planner appends a ledger row that cites manuscript
or exit-artifact paths. Does not validate hashes; existence-only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _walk_section_paths(obj: Any, out: set[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "phase_deliverable_path" and isinstance(v, str) and v.strip():
                out.add(v.strip())
            _walk_section_paths(v, out)
    elif isinstance(obj, list):
        for item in obj:
            _walk_section_paths(item, out)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Verify repo-relative paths in phase_state.json exist (A8)."
    )
    ap.add_argument("--project-root", required=True, type=Path)
    args = ap.parse_args()
    root = args.project_root.resolve()
    ps = root / "reviews" / "phase_state.json"
    if not ps.is_file():
        print(f"provenance_prewrite_check: no file {ps} (skip)")
        return 0

    data = json.loads(ps.read_text(encoding="utf-8"))
    paths: set[str] = set()
    _walk_section_paths(data, paths)

    bad: list[str] = []
    for rel in sorted(paths):
        target = (root / rel).resolve()
        if not target.is_file():
            bad.append(rel)

    if bad:
        for rel in bad:
            print(f"[BLOCKER] phase_deliverable_path not found: {rel}")
        return 1
    print(
        f"[OK] provenance_prewrite_check: {len(paths)} path(s) resolve under {root}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
