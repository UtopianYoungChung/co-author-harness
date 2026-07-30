#!/usr/bin/env python3
"""C1 red-first tests for role/output contract 3.0.0.

This focused program intentionally exits 1 against the unchanged C0 product.
Each ``EXPECTED_RED`` line is a frozen missing/refusal behavior, not an
unexpected test error.  It does not invoke the fixture registry or write any
authoritative manifest.
"""

from __future__ import annotations

import copy
import importlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = ROOT / "references" / "role_output_contract.json"

RED_IDS = (
    "population-fixed-triggered-confusion",
    "trigger-unknown",
    "class-unknown",
    "occurrence-duplicate",
    "occurrence-closure-missing",
    "occurrence-state-contradictory",
    "context-scope-mismatch",
    "cardinality-violation",
    "order-violation",
)

EXPECTED_CODES = {
    "population-fixed-triggered-confusion": "OUTPUT-POPULATION-MISMATCH",
    "trigger-unknown": "TRIGGER-UNKNOWN",
    "class-unknown": "CLASS-UNKNOWN",
    "occurrence-duplicate": "OCCURRENCE-DUPLICATE",
    "occurrence-closure-missing": "OCCURRENCE-CLOSURE-MISSING",
    "occurrence-state-contradictory": "OCCURRENCE-STATE-CONTRADICTORY",
    "context-scope-mismatch": "CONTEXT-SCOPE-MISMATCH",
    "cardinality-violation": "CARDINALITY-VIOLATION",
    "order-violation": "ORDER-VIOLATION",
}


def base_document() -> dict[str, Any]:
    return {
        "contract_id": "role-output-contract",
        "contract_version": "3.0.0",
        "invocation_scope": "full_lifecycle",
        "context": {"kind": "round", "round_id": "round-01"},
        "trigger_occurrences": [
            {
                "occurrence_id": "a" * 64,
                "population": "triggered_class",
                "class_id": "F7_evidence_packet",
                "trigger_id": "check_evidence_recorded",
                "ordinal": 1,
            }
        ],
        "closures": [
            {
                "occurrence_id": "a" * 64,
                "state": "emitted",
                "artifact": {
                    "path": "reviews/.harness/evidence/event-01.json",
                    "payload_schema": "references/schemas/f7_evidence_packet.schema.json",
                    "bytes": 2,
                    "sha256": "b" * 64,
                },
            }
        ],
    }


def mutated(case_id: str) -> dict[str, Any]:
    doc = base_document()
    occurrence = doc["trigger_occurrences"][0]
    closure = doc["closures"][0]
    if case_id == "population-fixed-triggered-confusion":
        occurrence.update(population="fixed_role", class_id="F7_evidence_packet")
    elif case_id == "trigger-unknown":
        occurrence["trigger_id"] = "unknown-trigger"
    elif case_id == "class-unknown":
        occurrence["class_id"] = "F99_unknown"
    elif case_id == "occurrence-duplicate":
        doc["trigger_occurrences"].append(copy.deepcopy(occurrence))
    elif case_id == "occurrence-closure-missing":
        doc["closures"] = []
    elif case_id == "occurrence-state-contradictory":
        closure["suppression_reason"] = "POLICY_SUPPRESSED"
    elif case_id == "context-scope-mismatch":
        doc["invocation_scope"] = "lab_iteration"
        occurrence.update(class_id="F9_milestone_handoff", trigger_id="milestone_approved")
        doc["context"] = {"kind": "round", "round_id": "round-01"}
    elif case_id == "cardinality-violation":
        occurrence.update(class_id="F8_final_round_report", trigger_id="round_close_report")
        second = copy.deepcopy(occurrence)
        second.update(occurrence_id="c" * 64, ordinal=2)
        doc["trigger_occurrences"].append(second)
        second_closure = copy.deepcopy(closure)
        second_closure["occurrence_id"] = "c" * 64
        doc["closures"].append(second_closure)
    elif case_id == "order-violation":
        occurrence.update(class_id="F8_final_round_report", trigger_id="round_close_report")
        doc["observed_order"] = ["F8_final_round_report", "F4_reflector_full_report"]
    else:  # pragma: no cover - frozen table prevents this
        raise KeyError(case_id)
    return doc


def production_errors(document: dict[str, Any]) -> list[str]:
    """Call the frozen v3 validator interface when production supplies it."""
    try:
        module = importlib.import_module("output_contract")
    except ModuleNotFoundError:
        return ["OUTPUT-CONTRACT-VALIDATOR-MISSING"]
    validator = getattr(module, "validate_output_transaction", None)
    if not callable(validator):
        return ["OUTPUT-CONTRACT-VALIDATOR-MISSING"]
    try:
        result = validator(CONTRACT_PATH, document)
    except Exception as exc:  # noqa: BLE001 - a stable refusal is required
        return [f"OUTPUT-CONTRACT-VALIDATOR-RAISED {type(exc).__name__}: {exc}"]
    return [str(item) for item in result]


def has_code(errors: list[str], code: str) -> bool:
    return any(error == code or error.startswith(code + " ") for error in errors)


def main() -> int:
    sys.path.insert(0, str(ROOT / "scripts"))
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    controls = {
        "control-current-contract-readable": isinstance(contract, dict),
        "control-legacy-milestone-paths-distinct": len({
            row["deliverable_path"] for row in contract.get("milestones", {}).values()
        }) == len(contract.get("milestones", {})),
        "control-no-file-presence-specialization":
            contract.get("specialization", {}).get("file_presence_never_specializes") is True,
    }
    unexpected: list[str] = []
    for control_id, passed in controls.items():
        print(f"{'CONTROL_PASS' if passed else 'CONTROL_FAIL'} {control_id}")
        if not passed:
            unexpected.append(control_id)

    expected_reds: list[str] = []
    unexpected_passes: list[str] = []
    for case_id in RED_IDS:
        errors = production_errors(mutated(case_id))
        expected_code = EXPECTED_CODES[case_id]
        if has_code(errors, expected_code):
            print(f"UNEXPECTED_PASS {case_id} code={expected_code}")
            unexpected_passes.append(case_id)
        else:
            print(f"EXPECTED_RED {case_id} missing={expected_code} observed={errors[:2]}")
            expected_reds.append(case_id)

    summary = {
        "program": "output_contract_smoketest",
        "expected_red_ids": expected_reds,
        "unexpected_pass_ids": unexpected_passes,
        "unexpected_failures": unexpected,
        "passing_controls": [name for name, ok in controls.items() if ok],
    }
    print("C1_RED_SUMMARY " + json.dumps(summary, sort_keys=True))
    return 1 if expected_reds or unexpected else 0


if __name__ == "__main__":
    raise SystemExit(main())
