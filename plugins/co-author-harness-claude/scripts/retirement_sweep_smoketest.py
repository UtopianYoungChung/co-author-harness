#!/usr/bin/env python3
"""Focused line-semantic cases for retired milestone split detection."""

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("retirement-sweep-check.py")
SPEC = importlib.util.spec_from_file_location("retirement_sweep_check", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
retired_milestone_split_findings = MODULE.retired_milestone_split_findings


def main() -> int:
    markers = ["retired", "historical", "archival", "formerly"]
    cases = [
        (Path("references/PHASE_PROTOCOL.md"), "Current mapping: M4a -> Ph2.", 1),
        (Path("references/phase_state_schema.md"), "Current shape emits M4b.", 1),
        (Path("references/SKILL_REGISTRY.md"), "M4a remains the current milestone.", 1),
        (Path("agents/generator.md"), "Historical note: M4a was retired.", 0),
        (Path("skills/run-phase-3/SKILL.md"), "Formerly called M4b; no current emission.", 0),
        (Path("docs/archive/old.md"), "Current mapping M4a -> Ph2.", 0),
        (Path("references/history/old.md"), "Current mapping M4b -> Ph3.", 0),
        (Path("agents/evaluator.md"), "No retired split token here.", 0),
    ]
    for path, line, expected in cases:
        actual = len(retired_milestone_split_findings(path, line, markers))
        assert actual == expected, (path, line, expected, actual)
    print(f"PASS: {len(cases)} line-semantic retirement cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
