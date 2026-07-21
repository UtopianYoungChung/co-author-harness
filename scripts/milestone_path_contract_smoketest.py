#!/usr/bin/env python3
"""Regression contract for canonical milestone paths and alias rejection."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from milestone_path_contract import (  # noqa: E402
    CanonicalPathError,
    canonical_deliverable,
    handoff_path,
    snapshot_path,
    validate_project_path_surface,
)


EXPECTED = {
    "M1": "milestones/M1_project_memo.md",
    "M2": "milestones/M2_annotated_references.md",
    "M3": "milestones/M3_argument_evidence_outline.md",
    "M4": "milestones/M4_complete_paper_draft.md",
    "M5": "milestones/M5_final_paper.md",
}


def _expect_block(project: Path) -> None:
    try:
        validate_project_path_surface(project)
    except CanonicalPathError:
        return
    raise AssertionError("unsafe or ambiguous milestone surface was accepted")


def main() -> int:
    authority_path = ROOT / "references" / "role_output_contract.json"
    authority = json.loads(authority_path.read_text(encoding="utf-8"))
    assert authority["schema_version"] == "2.0.0"
    assert authority["contract_id"] == "role-output-contract"
    assert authority["path_contract_version"] == "2.0.0"
    assert {key: row["deliverable_path"] for key, row in authority["milestones"].items()} == EXPECTED
    assert canonical_deliverable("FINAL") == EXPECTED["M5"]
    assert handoff_path("M4") == "reviews/.harness/handoffs/M4_to_M5.json"
    assert handoff_path("FINAL") == "reviews/.harness/handoffs/M5_terminal.json"
    assert snapshot_path("M4", "a" * 64) == f"reviews/.harness/snapshots/M4/{'a' * 64}.md"

    with tempfile.TemporaryDirectory(prefix="milestone-path-contract-") as directory:
        project = Path(directory)
        for relative in EXPECTED.values():
            path = project / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(relative + "\n", encoding="utf-8")
        validate_project_path_surface(project)

        legacy = project / "manuscript" / "main.md"
        legacy.parent.mkdir(parents=True)
        legacy.write_text("alias\n", encoding="utf-8")
        _expect_block(project)
        legacy.unlink()

        alias = project / "manuscript" / "final.md"
        alias.parent.mkdir(parents=True, exist_ok=True)
        try:
            alias.symlink_to(project / EXPECTED["M5"])
        except OSError:
            # Windows may deny symlink creation. A hard link still proves that
            # a second writable name for the same deliverable is forbidden.
            alias.hardlink_to(project / EXPECTED["M5"])
        _expect_block(project)

    print("milestone_path_contract_smoketest: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
