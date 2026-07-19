#!/usr/bin/env python3
"""Adversarial checks for the canonical lifecycle and role/output contracts."""

from __future__ import annotations

import importlib.util
import copy
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from lifecycle_contract import contract_coherence_errors, load_contract, states, transition_allowed


def _load_validator():
    path = SCRIPTS / "phase_state_validate.py"
    spec = importlib.util.spec_from_file_location("phase_state_validate", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _row(previous: object, new: str, trigger: str) -> dict:
    return {
        "prev_phase": previous,
        "new_phase": new,
        "trigger": trigger,
        "actor": "planner",
        "notes": "contract test",
        "timestamp": "2026-07-19T00:00:00Z",
        "model_used": None,
    }


def _codes(log: list[dict]) -> set[str]:
    module = _load_validator()
    findings: list = []
    module._validate_monotonicity(log, "log", findings)
    return {finding.code for finding in findings}


def main() -> int:
    assert states() == ["Ph1", "Ph2", "Ph3", "Ph3_converged", "Ph4"]

    assert transition_allowed("initial_dispatch", None, "Ph1")
    assert transition_allowed("user_approval", "Ph1", "Ph1")
    assert transition_allowed("user_approval", "Ph1", "Ph2")
    assert transition_allowed("user_approval", "Ph2", "Ph3")
    assert transition_allowed(
        "ph3_convergence_signoff_terminal", "Ph3", "Ph3_converged"
    )
    assert transition_allowed("mcr_admission", "Ph3_converged", "Ph4")
    assert transition_allowed("eg1_ph4_downgrade_to_ph3", "Ph4", "Ph3")
    assert transition_allowed(
        "eg7_mcr_readmission_after_class_change", "Ph4", "Ph3"
    )

    assert not transition_allowed("user_approval", "Ph1", "Ph4")
    assert not transition_allowed("user_approval", "Ph3", "Ph4")
    assert not transition_allowed("eg1_ph4_downgrade_to_ph3", "Ph4", "Ph1")
    assert transition_allowed("retraction", "Ph4", "Ph3")
    assert transition_allowed("retraction", "Ph3_converged", "Ph3")
    assert transition_allowed("retraction", "Ph3", "Ph2")
    assert transition_allowed("retraction", "Ph2", "Ph1")
    assert not transition_allowed("retraction", "Ph4", "Ph1")
    assert not transition_allowed("user_approval", "Ph3", "Ph3")
    assert not transition_allowed("user_approval", "Ph3", "Ph4")
    assert not transition_allowed("invented_trigger", "Ph2", "Ph3")

    incoherent = copy.deepcopy(load_contract())
    incoherent["monotonicity_exemptions"].remove("retraction")
    assert any("monotonicity exemptions disagree" in error for error in contract_coherence_errors(incoherent))

    missing_target = copy.deepcopy(load_contract())
    missing_target["transitions"][2]["to_by_from"].pop("Ph2")
    assert any("missing to_by_from target" in error for error in contract_coherence_errors(missing_target))

    valid = [
        _row(None, "Ph1", "initial_dispatch"),
        _row("Ph1", "Ph2", "user_approval"),
        _row("Ph2", "Ph3", "user_approval"),
        _row("Ph3", "Ph3_converged", "ph3_convergence_signoff_terminal"),
        _row("Ph3_converged", "Ph4", "mcr_admission"),
        _row("Ph4", "Ph3", "eg1_ph4_downgrade_to_ph3"),
    ]
    assert _codes(valid) == set()

    assert "ILLEGAL_LIFECYCLE_TRANSITION" in _codes(
        [_row(None, "Ph1", "initial_dispatch"), _row("Ph1", "Ph4", "user_approval")]
    )
    assert "MONOTONICITY_VIOLATION" in _codes(
        [_row(None, "Ph1", "initial_dispatch"), _row("Ph1", "Ph2", "user_approval"),
         _row("Ph2", "Ph1", "invented_trigger")]
    )
    assert "LIFECYCLE_LOG_DISCONTINUITY" in _codes(
        [_row(None, "Ph1", "initial_dispatch"), _row("Ph2", "Ph3", "user_approval")]
    )

    role_contract = json.loads(
        (ROOT / "references" / "role_output_contract.v1.json").read_text(encoding="utf-8")
    )
    expected = {
        "M1": ("research_notes/project_memo.md", ["Ph1"], "forbidden"),
        "M2": ("research_notes/annotated_references.md", ["Ph1"], "forbidden"),
        "M3": ("manuscript/outline.md", ["Ph1"], "forbidden"),
        "M4": ("manuscript/main.md", ["Ph1", "Ph2", "Ph3"], "required-from-Ph2"),
    }
    for milestone, (path, write_states, evaluator) in expected.items():
        row = role_contract["milestones"][milestone]
        assert row["deliverable_writer"] == "generator"
        assert row["deliverable_path"] == path
        assert row["write_states"] == write_states
        assert row["evaluator_engagement"] == evaluator
        assert row["approval_recorded_by"] == "planner"

    assert role_contract["milestones"]["M3"]["content_scope"] == "structured-outline-only"
    assert role_contract["milestones"]["M4"]["initial_assembly_state"] == "Ph1"
    assert role_contract["milestones"]["M4"]["acceptance_readiness"] == "Ph3_converged"

    print("lifecycle_contract_smoketest: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
