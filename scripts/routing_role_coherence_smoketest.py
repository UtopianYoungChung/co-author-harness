#!/usr/bin/env python3
"""Pin lifecycle vocabulary and M1-M4 role routing across prose surfaces."""

from __future__ import annotations

import sys
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def main() -> int:
    role_contract = json.loads(read("references/role_output_contract.v1.json"))
    expected_paths = {
        "M1": "research_notes/project_memo.md",
        "M2": "research_notes/annotated_references.md",
        "M3": "manuscript/outline.md",
        "M4": "manuscript/main.md",
    }
    for milestone, path in expected_paths.items():
        row = role_contract["milestones"][milestone]
        assert row["deliverable_writer"] == "generator"
        assert row["deliverable_path"] == path
        assert row["approval_recorded_by"] == "planner"

    routing = read("references/ROUTING_SPINE.md")
    routing_flat = " ".join(routing.split())
    assert "derived intent routing" in routing_flat.lower()
    assert "never persisted as lifecycle state" in routing_flat
    assert "M1, M2, and M3 are separately presented" in routing_flat
    assert "M4 begins with initial manuscript assembly in Ph1" in routing_flat
    assert "M4 initial assembly in Ph1 | Planner dispatches Generator" in routing_flat
    assert "Evaluator is dormant for M1–M3 and throughout Ph1" in routing_flat
    assert "seven phases, mapped" not in routing_flat
    assert "every request lands on exactly one phase" not in routing_flat

    contracts = read("references/AGENT_CONTRACTS.md")
    for path in (
        "research_notes/project_memo.md",
        "research_notes/annotated_references.md",
        "manuscript/outline.md",
        "manuscript/main.md",
    ):
        assert path in contracts
    assert "Never writes to `reviews/*` except receipt-scoped staged content" in contracts
    assert "Live deliverables are published only by `assignment_writer_commit.py`" in contracts
    assert "the exact deliverable path authorized by the receipt" in contracts

    generator = read("agents/generator.md")
    assert "sole writer of academic deliverables" in generator
    evaluator = read("agents/evaluator.md")
    assert "E-EVALUATOR-PH1-DORMANT" in evaluator
    assert "ph1_noop_" not in evaluator

    phase1 = read("skills/run-phase-1/SKILL.md")
    assert "User approves M1, M2, or M3 → milestone-only" in phase1
    assert "current_phase` stays `Ph1`" in phase1
    assert "M4 Ph1 exit" in phase1

    schema = read("references/phase_state_schema.md")
    assert "`Ph1 → Ph1` (milestone-only)" in schema
    assert "never Ph3 → Ph4" in schema

    orchestration = read("references/AGENT_ORCHESTRATION.md")
    milestone_table = orchestration.split("### 10.1", 1)[1].split("### 10.2", 1)[0]
    for milestone, path in expected_paths.items():
        matching_rows = [line for line in milestone_table.splitlines() if f"**{milestone} " in line]
        assert len(matching_rows) == 1, (milestone, matching_rows)
        assert path in matching_rows[0]
        assert "Generator" in matching_rows[0]
    forbidden_planner_content = re.compile(r"Planner\s+(?:authors|curates|drafts|writes)\b", re.IGNORECASE)
    assert not forbidden_planner_content.search(milestone_table)
    assert "Ph1 initial assembly" in milestone_table and "Ph2 Review & Revise" in milestone_table

    print("routing_role_coherence_smoketest: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
