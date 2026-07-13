#!/usr/bin/env python3
"""Smoke-test the milestone-framework and F9 JSON Schema contracts.

Task 3 owns the production semantic validator.  This test intentionally uses a
small standard-library JSON Schema evaluator for only the keywords exercised by
the two real schemas created in Task 2.
"""

from __future__ import annotations

import copy
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MILESTONE_SCHEMA = ROOT / "references" / "schemas" / "milestone_framework.schema.json"
F9_SCHEMA = ROOT / "references" / "schemas" / "f9_milestone_handoff.schema.json"
F9_TEMPLATE = ROOT / "references" / "templates" / "f9_milestone_handoff.json"

CASES = {
    "valid_native_chain": 0,
    "valid_native_bootstrap": 0,
    "valid_not_applicable_empty_records": 0,
    "missing_milestone_purpose": 4,
    "m4_plan_as_deliverable": 4,
    "m5_checklist_as_deliverable": 4,
    "missing_feedback_provenance": 4,
    "two_primary_lineages": 4,
    "handoff_without_approval": 4,
    "ready_with_null_approval_evidence": 4,
    "consumed_with_null_approval_evidence": 4,
    "ready_with_null_packet_binding": 4,
    "consumed_with_null_packet_binding": 4,
    "legacy_without_migration_boundary": 4,
    "accepted_m1_without_deliverable": 4,
    "accepted_m2_without_deliverable": 4,
    "accepted_m3_without_deliverable": 4,
    "not_applicable_without_authority": 4,
    "not_applicable_incomplete_override": 4,
    "not_applicable_status_without_override": 4,
}


class SchemaError(ValueError):
    """Raised when an instance fails the bounded smoke-test evaluator."""


def _is_type(value: Any, expected: str) -> bool:
    checks = {
        "object": lambda item: isinstance(item, dict),
        "array": lambda item: isinstance(item, list),
        "string": lambda item: isinstance(item, str),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
        "boolean": lambda item: isinstance(item, bool),
        "null": lambda item: item is None,
    }
    return checks[expected](value)


def _resolve_ref(root_schema: dict[str, Any], reference: str) -> dict[str, Any]:
    if not reference.startswith("#/"):
        raise RuntimeError(f"smoke evaluator supports local references only: {reference}")
    value: Any = root_schema
    for token in reference[2:].split("/"):
        value = value[token.replace("~1", "/").replace("~0", "~")]
    return value


def _validate(instance: Any, schema: dict[str, Any], root: dict[str, Any], path: str = "$") -> None:
    if "$ref" in schema:
        _validate(instance, _resolve_ref(root, schema["$ref"]), root, path)
        return

    for subschema in schema.get("allOf", []):
        _validate(instance, subschema, root, path)

    if "anyOf" in schema:
        if not any(_accepts(instance, option, root, path) for option in schema["anyOf"]):
            raise SchemaError(f"{path}: did not satisfy anyOf")
    if "oneOf" in schema:
        matches = sum(_accepts(instance, option, root, path) for option in schema["oneOf"])
        if matches != 1:
            raise SchemaError(f"{path}: expected exactly one oneOf match, got {matches}")
    if "if" in schema:
        branch = "then" if _accepts(instance, schema["if"], root, path) else "else"
        if branch in schema:
            _validate(instance, schema[branch], root, path)

    expected = schema.get("type")
    if expected is not None:
        allowed = [expected] if isinstance(expected, str) else expected
        if not any(_is_type(instance, item) for item in allowed):
            raise SchemaError(f"{path}: expected type {allowed}, got {type(instance).__name__}")
    if "const" in schema and instance != schema["const"]:
        raise SchemaError(f"{path}: expected constant {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        raise SchemaError(f"{path}: {instance!r} is outside enum")

    if isinstance(instance, dict):
        required = schema.get("required", [])
        missing = [key for key in required if key not in instance]
        if missing:
            raise SchemaError(f"{path}: missing required properties {missing}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extra = sorted(set(instance) - set(properties))
            if extra:
                raise SchemaError(f"{path}: additional properties forbidden: {extra}")
        for key, subschema in properties.items():
            if key in instance:
                _validate(instance[key], subschema, root, f"{path}.{key}")

    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            raise SchemaError(f"{path}: too few items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            raise SchemaError(f"{path}: too many items")
        if schema.get("uniqueItems") and len({json.dumps(v, sort_keys=True) for v in instance}) != len(instance):
            raise SchemaError(f"{path}: items must be unique")
        if "items" in schema:
            for index, value in enumerate(instance):
                _validate(value, schema["items"], root, f"{path}[{index}]")
        if "contains" in schema:
            matches = sum(_accepts(value, schema["contains"], root, f"{path}[{index}]") for index, value in enumerate(instance))
            if matches < schema.get("minContains", 1):
                raise SchemaError(f"{path}: contains matched too few items")
            if "maxContains" in schema and matches > schema["maxContains"]:
                raise SchemaError(f"{path}: contains matched too many items")

    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            raise SchemaError(f"{path}: string is too short")
        if "pattern" in schema and re.fullmatch(schema["pattern"], instance) is None:
            raise SchemaError(f"{path}: string does not match {schema['pattern']!r}")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            raise SchemaError(f"{path}: value is below minimum")


def _accepts(instance: Any, schema: dict[str, Any], root: dict[str, Any], path: str) -> bool:
    try:
        _validate(instance, schema, root, path)
    except SchemaError:
        return False
    return True


def _artifact(milestone: str) -> dict[str, Any]:
    kinds = {"M1": "project_memo", "M2": "annotated_references", "M3": "structured_outline", "M4": "manuscript", "M5": "manuscript"}
    return {
        "role": "deliverable",
        "artifact_kind": kinds[milestone],
        "path": f"research_notes/{milestone.lower()}_deliverable.md",
        "sha256": "0" * 64,
        "bytes": 1,
        "verified_at": "2026-07-13T18:00:00Z",
        "lineage_id": "main",
    }


def _feedback(milestone: str) -> dict[str, Any]:
    return {
        "feedback_id": f"feedback-{milestone.lower()}-1",
        "evidence_class": "harness_review_evidence",
        "source_path": f"reviews/{milestone.lower()}_review.md",
        "source_sha256": "1" * 64,
        "source_actor": "planner",
        "source_milestone": milestone,
        "target_milestone": milestone,
        "received_at": "2026-07-13T18:00:00Z",
        "lineage_id": "main",
        "blocking": False,
        "disposition": "informational",
        "rationale": "No blocking findings.",
        "successor_effect": "none",
    }


def _override(milestones: list[str], handoffs: list[str]) -> dict[str, Any]:
    return {
        "authority": "user",
        "reason": "The higher-authority project contract excludes this milestone.",
        "scope": "Milestone deliverable and handoff",
        "timestamp": "2026-07-13T18:00:00Z",
        "affected_milestones": milestones,
        "affected_handoffs": handoffs,
        "substitute_evidence": "reviews/not_applicable_approval.md",
        "revalidation_obligations": ["Revalidate if the project contract changes."],
        "event_type": "authorized_override",
    }


def _valid_ledger() -> dict[str, Any]:
    milestones: dict[str, Any] = {}
    for milestone in ("M1", "M2", "M3", "M4", "M5"):
        milestones[milestone] = {
            "purpose": f"Produce the {milestone} contract deliverable.",
            "status": "accepted",
            "applicability": "applicable",
            "required_inputs": [],
            "exit_criteria": ["Deliverable and evidence are bound."],
            "artifacts": [_artifact(milestone)],
            "feedback_records": [_feedback(milestone)],
            "approval": {
                "status": "approved",
                "authority": "user",
                "evidence_path": f"reviews/{milestone.lower()}_approval.md",
                "approved_at": "2026-07-13T18:00:00Z",
            },
            "handoff": {
                "status": "consumed" if milestone != "M5" else "ready",
                "packet_path": f"reviews/.harness/milestones/{milestone}_packet.json",
                "packet_sha256": "2" * 64,
            },
            "dependency_state": "current",
            "authorized_override": None,
        }
    return {
        "contract_version": "1.0.0",
        "mode": "native",
        "primary_lineage": "main",
        "milestones": milestones,
    }


def _case_ledgers() -> dict[str, dict[str, Any]]:
    cases = {name: copy.deepcopy(_valid_ledger()) for name in CASES}
    bootstrap = cases["valid_native_bootstrap"]["milestones"]
    for milestone in ("M1", "M2", "M3", "M4", "M5"):
        bootstrap[milestone]["status"] = "in_progress" if milestone == "M1" else "not_started"
        bootstrap[milestone]["artifacts"] = []
        bootstrap[milestone]["feedback_records"] = []
        bootstrap[milestone]["approval"] = {
            "status": "pending",
            "authority": None,
            "evidence_path": None,
            "approved_at": None,
        }
        bootstrap[milestone]["handoff"] = {
            "status": "not_ready",
            "packet_path": None,
            "packet_sha256": None,
        }

    for milestone in ("M4", "M5"):
        target = cases["valid_not_applicable_empty_records"]["milestones"][milestone]
        target["status"] = "not_applicable"
        target["applicability"] = "not_applicable"
        target["artifacts"] = []
        target["feedback_records"] = []
        target["approval"] = {"status": "not_applicable", "authority": None, "evidence_path": None, "approved_at": None}
        target["handoff"] = {"status": "not_applicable", "packet_path": None, "packet_sha256": None}
        target["dependency_state"] = "not_applicable"
        target["authorized_override"] = _override([milestone], [f"{milestone}_terminal" if milestone == "M5" else f"{milestone}_to_next"])

    del cases["missing_milestone_purpose"]["milestones"]["M2"]["purpose"]
    cases["m4_plan_as_deliverable"]["milestones"]["M4"]["artifacts"][0]["artifact_kind"] = "plan"
    cases["m5_checklist_as_deliverable"]["milestones"]["M5"]["artifacts"][0]["artifact_kind"] = "checklist"
    del cases["missing_feedback_provenance"]["milestones"]["M3"]["feedback_records"][0]["source_sha256"]
    cases["two_primary_lineages"]["primary_lineage"] = ["main", "alternate"]
    cases["handoff_without_approval"]["milestones"]["M2"]["approval"]["status"] = "pending"

    for name, status in (
        ("ready_with_null_approval_evidence", "ready"),
        ("consumed_with_null_approval_evidence", "consumed"),
    ):
        target = cases[name]["milestones"]["M2"]
        target["handoff"]["status"] = status
        target["approval"]["authority"] = None
        target["approval"]["evidence_path"] = None
        target["approval"]["approved_at"] = None

    for name, status in (
        ("ready_with_null_packet_binding", "ready"),
        ("consumed_with_null_packet_binding", "consumed"),
    ):
        target = cases[name]["milestones"]["M2"]
        target["handoff"]["status"] = status
        target["handoff"]["packet_path"] = None
        target["handoff"]["packet_sha256"] = None

    cases["legacy_without_migration_boundary"]["mode"] = "legacy"

    for milestone in ("M1", "M2", "M3"):
        target = cases[f"accepted_{milestone.lower()}_without_deliverable"]["milestones"][milestone]
        target["artifacts"] = [
            {
                **_artifact(milestone),
                "role": "transition_control",
                "artifact_kind": "plan",
            },
            {
                **_artifact(milestone),
                "role": "evidence",
                "artifact_kind": "review",
            },
            {
                **_artifact(milestone),
                "role": "derived_view",
                "artifact_kind": "status_view",
            },
            {
                **_artifact(milestone),
                "role": "export",
                "artifact_kind": "rendered_export",
            },
        ]

    target = cases["not_applicable_without_authority"]["milestones"]["M3"]
    target["status"] = "not_applicable"
    target["applicability"] = "not_applicable"
    target["approval"] = {"status": "not_applicable", "authority": None, "evidence_path": None, "approved_at": None}
    target["handoff"] = {"status": "not_applicable", "packet_path": None, "packet_sha256": None}
    target["dependency_state"] = "not_applicable"

    incomplete = cases["not_applicable_incomplete_override"]["milestones"]["M3"]
    incomplete["status"] = "not_applicable"
    incomplete["applicability"] = "not_applicable"
    incomplete["approval"] = {"status": "not_applicable", "authority": None, "evidence_path": None, "approved_at": None}
    incomplete["handoff"] = {"status": "not_applicable", "packet_path": None, "packet_sha256": None}
    incomplete["dependency_state"] = "not_applicable"
    incomplete["authorized_override"] = {
        "authority": "user",
        "reason": "The milestone is excluded.",
        "scope": "M3",
        "substitute_evidence": "reviews/not_applicable_approval.md",
        "event_type": "authorized_override",
    }

    cases["not_applicable_status_without_override"]["milestones"]["M3"]["status"] = "not_applicable"
    return cases


def main() -> int:
    required_files = (MILESTONE_SCHEMA, F9_SCHEMA, F9_TEMPLATE)
    missing = [str(path.relative_to(ROOT)) for path in required_files if not path.is_file()]
    if missing:
        print("MISCONFIGURED: missing Task 2 schema/template files: " + ", ".join(missing))
        return 4

    milestone_schema = json.loads(MILESTONE_SCHEMA.read_text(encoding="utf-8"))
    f9_schema = json.loads(F9_SCHEMA.read_text(encoding="utf-8"))
    f9_template = json.loads(F9_TEMPLATE.read_text(encoding="utf-8"))
    _validate(f9_template, f9_schema, f9_schema)

    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="milestone-framework-") as temp_dir:
        directory = Path(temp_dir)
        for name, ledger in _case_ledgers().items():
            ledger_path = directory / f"{name}.json"
            ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
            loaded = json.loads(ledger_path.read_text(encoding="utf-8"))
            try:
                _validate(loaded, milestone_schema, milestone_schema)
                actual = 0
            except SchemaError:
                actual = 4
            expected = CASES[name]
            print(f"{name}: expected={expected} actual={actual}")
            if actual != expected:
                failures.append(f"{name} expected {expected}, got {actual}")

    if failures:
        print("FAIL: " + "; ".join(failures))
        return 1
    print("OK milestone_framework_smoketest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
