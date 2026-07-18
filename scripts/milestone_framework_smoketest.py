#!/usr/bin/env python3
"""Smoke-test the milestone-framework and F9 JSON Schema contracts.

Task 3 owns the production semantic validator.  This test intentionally uses a
small standard-library JSON Schema evaluator for only the keywords exercised by
the two real schemas created in Task 2.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MILESTONE_SCHEMA = ROOT / "references" / "schemas" / "milestone_framework.schema.json"
F9_SCHEMA = ROOT / "references" / "schemas" / "f9_milestone_handoff.schema.json"
F9_TEMPLATE = ROOT / "references" / "templates" / "f9_milestone_handoff.json"
EVENT_TEMPLATE = ROOT / "references" / "templates" / "milestone_event.json"
VALIDATOR = ROOT / "scripts" / "milestone_framework_validate.py"
LIFECYCLE_RENDERER = ROOT / "scripts" / "render_lifecycle_state.py"
EXEMPLAR_REGISTRY = ROOT / "references" / "milestone_exemplars.json"
PHASE_VALIDATOR = ROOT / "scripts" / "phase_state_validate.py"
SK20_GATE = ROOT / "scripts" / "sk20_preflight_gate.py"
PLUGIN_VERSION = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]

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
    "export_without_source_binding": 4,
    "missing_events": 4,
    "event_missing_reason": 4,
}

REAL_CASES = {
    "valid_native_chain": ("READY", 0, None, None),
    "re_manuscript_bound_chain": ("READY", 0, None, None),
    "re_m5_manuscript_changed": ("MISCONFIGURED", 4, None, "MF-BINDING"),
    "re_m2_reopened_blocks_m5": ("MISCONFIGURED", 4, None, "MF-REOPEN"),
    "valid_ph2_target": ("READY", 0, "Ph2", None),
    "valid_ph4_target": ("READY", 0, "Ph4", None),
    "valid_ph4_before_closure": ("READY", 0, "Ph4", None),
    "valid_ph4_ceiling_locked": ("READY", 0, "Ph4", None),
    "valid_approved_legacy_migration": ("LEGACY_READY", 0, None, None),
    "native_m5_not_started_target": ("MISCONFIGURED", 4, "M5", "MF-HANDOFF"),
    "legacy_m3_boundary_target": ("LEGACY_READY", 0, "M3", None),
    "legacy_m3_boundary_m5_target": ("MISCONFIGURED", 4, "M5", "MF-HANDOFF"),
    "authorized_not_applicable": ("NOT_APPLICABLE", 0, "M4", None),
    "absent_namespace": ("MISCONFIGURED", 4, None, "MF-STRUCTURE"),
    "missing_purpose_real": ("MISCONFIGURED", 4, None, "MF-STRUCTURE"),
    "m4_plan_only_real": ("MISCONFIGURED", 4, "M4", "MF-ROLE"),
    "m5_checklist_only_real": ("MISCONFIGURED", 4, "M5", "MF-ROLE"),
    "missing_feedback_provenance_real": ("MISCONFIGURED", 4, None, "MF-FEEDBACK"),
    "stale_feedback_contemporaneity_evidence": ("MISCONFIGURED", 4, None, "MF-FEEDBACK"),
    "two_primary_lineages_real": ("MISCONFIGURED", 4, None, "MF-LINEAGE"),
    "artifact_lineage_mismatch": ("MISCONFIGURED", 4, None, "MF-LINEAGE"),
    "successor_without_consumed_handoff": ("MISCONFIGURED", 4, None, "MF-HANDOFF"),
    "na_without_complete_override": ("MISCONFIGURED", 4, "M4", "MF-OVERRIDE"),
    "stale_deliverable_hash": ("MISCONFIGURED", 4, None, "MF-BINDING"),
    "stale_f9_packet_hash": ("MISCONFIGURED", 4, None, "MF-BINDING"),
    "reopened_upstream_current_downstream": ("MISCONFIGURED", 4, None, "MF-REOPEN"),
    "malformed_derived_claim": ("MISCONFIGURED", 4, None, "MF-DERIVED"),
    "manual_status_claims_authority": ("MISCONFIGURED", 4, None, "MF-STATUS"),
    "list_shaped_approval": ("MISCONFIGURED", 4, None, "MF-HANDOFF"),
    "fabricated_f9_authority": ("MISCONFIGURED", 4, None, "MF-HANDOFF"),
    "fabricated_matching_authority": ("MISCONFIGURED", 4, None, "MF-HANDOFF"),
    "missing_approval_evidence": ("MISCONFIGURED", 4, None, "MF-HANDOFF"),
    "mismatched_f9_approval_evidence": ("MISCONFIGURED", 4, None, "MF-HANDOFF"),
    "forged_f9_project_identity": ("MISCONFIGURED", 4, None, "MF-HANDOFF"),
    "forged_f9_from_milestone": ("MISCONFIGURED", 4, None, "MF-HANDOFF"),
    "forged_f9_to_milestone": ("MISCONFIGURED", 4, None, "MF-HANDOFF"),
    "native_missing_project_identity": ("MISCONFIGURED", 4, None, "MF-HANDOFF"),
    "project_identity_disagreement": ("MISCONFIGURED", 4, None, "MF-HANDOFF"),
    "legacy_handoffs_without_project_identity": ("MISCONFIGURED", 4, None, "MF-HANDOFF"),
    "rejected_generator_override": ("MISCONFIGURED", 4, "M4", "MF-OVERRIDE"),
    "allowed_advisor_override": ("NOT_APPLICABLE", 0, "M4", None),
    "reordered_artifacts_feedback_lineage": ("READY", 0, None, None),
    "active_distinct_lineages": ("READY", 0, None, None),
    "active_duplicate_lineage": ("MISCONFIGURED", 4, None, "MF-LINEAGE"),
    "implicit_supersession": ("MISCONFIGURED", 4, None, "MF-LINEAGE"),
    "explicit_supersession": ("READY", 0, None, None),
    "cyclic_supersession": ("MISCONFIGURED", 4, None, "MF-LINEAGE"),
    "accepted_primary_supersedes_preserved": ("READY", 0, None, None),
    "accepted_unsuperseded_nonprimary": ("MISCONFIGURED", 4, None, "MF-LINEAGE"),
    "ph4_without_mcr_admission": ("MISCONFIGURED", 4, "Ph4", "MF-PHASE"),
    "inf_unlocked_ph3_sibling_blocks_ph4": ("MISCONFIGURED", 4, "Ph4", "MF-PHASE"),
    "ph4_retracted_mcr_admission": ("MISCONFIGURED", 4, "Ph4", "MF-PHASE"),
    "ph4_empty_sections": ("MISCONFIGURED", 4, "Ph4", "MF-PHASE"),
    "ph4_nonobject_section": ("MISCONFIGURED", 4, "Ph4", "MF-PHASE"),
    "ph4_list_ceiling_override": ("MISCONFIGURED", 4, "Ph4", "MF-PHASE"),
    "ph4_dict_ceiling_override": ("MISCONFIGURED", 4, "Ph4", "MF-PHASE"),
    "export_source_mismatch": ("MISCONFIGURED", 4, None, "MF-EXPORT"),
    "terminal_f9_export_mismatch": ("MISCONFIGURED", 4, None, "MF-EXPORT"),
    "valid_project_local_override": ("NOT_APPLICABLE", 0, "M4", None),
    "missing_project_local_override": ("MISCONFIGURED", 4, "M4", "MF-OVERRIDE"),
    "outside_project_local_override": ("MISCONFIGURED", 4, "M4", "MF-OVERRIDE"),
    "absolute_project_local_override": ("MISCONFIGURED", 4, "M4", "MF-OVERRIDE"),
    "stale_override_evidence": ("MISCONFIGURED", 4, "M4", "MF-OVERRIDE"),
    "list_shaped_sections": ("MISCONFIGURED", 4, None, "MF-STRUCTURE"),
    "list_shaped_milestones": ("MISCONFIGURED", 4, None, "MF-STRUCTURE"),
    "missing_accepted_event": ("MISCONFIGURED", 4, None, "MF-EVENT"),
    "valid_deliverable_recorded_event": ("READY", 0, None, None),
    "missing_deliverable_recorded_event": ("MISCONFIGURED", 4, None, "MF-EVENT"),
    "deliverable_record_binding_mismatch": ("MISCONFIGURED", 4, None, "MF-EVENT"),
    "unordered_events": ("MISCONFIGURED", 4, None, "MF-EVENT"),
    "stale_without_event": ("MISCONFIGURED", 4, None, "MF-EVENT"),
    "stale_bad_cause": ("MISCONFIGURED", 4, None, "MF-EVENT"),
    "obsolete_acceptance_event": ("MISCONFIGURED", 4, None, "MF-EVENT"),
    "event_artifact_binding_mismatch": ("MISCONFIGURED", 4, None, "MF-EVENT"),
    "event_f9_binding_mismatch": ("MISCONFIGURED", 4, None, "MF-EVENT"),
    "invalid_event_timestamp": ("MISCONFIGURED", 4, None, "MF-EVENT"),
    "invalid_event_date_z": ("MISCONFIGURED", 4, None, "MF-EVENT"),
    "invalid_event_offset": ("MISCONFIGURED", 4, None, "MF-EVENT"),
    "invalid_event_naive": ("MISCONFIGURED", 4, None, "MF-EVENT"),
    "invalid_event_malformed": ("MISCONFIGURED", 4, None, "MF-EVENT"),
    "accepted_to_in_progress_old_events": ("MISCONFIGURED", 4, None, "MF-EVENT"),
    "valid_reopen_restart_transition": ("READY", 0, None, None),
    "feedback_wrong_milestone_binding": ("MISCONFIGURED", 4, None, "MF-EVENT"),
    "cross_subject_revalidation": ("MISCONFIGURED", 4, None, "MF-EVENT"),
    "retired_milestone_assignment": ("MISCONFIGURED", 4, None, "MF-STRUCTURE"),
    "policy_hash_drift": ("MISCONFIGURED", 4, None, "MF-POLICY"),
    "policy_missing_m1_intent": ("MISCONFIGURED", 4, None, "MF-POLICY"),
    "policy_missing_m3_profile": ("MISCONFIGURED", 4, None, "MF-POLICY"),
    "policy_missing_m4_current_hash": ("MISCONFIGURED", 4, None, "MF-POLICY"),
    "policy_native_binding_omitted": ("MISCONFIGURED", 4, None, "MF-POLICY"),
    "policy_valid_bootstrap": ("READY", 0, None, None),
    "policy_valid_m1_started": ("READY", 0, None, None),
    "policy_valid_m3_started": ("READY", 0, None, None),
    "policy_retired_without_events": ("MISCONFIGURED", 4, None, "MF-POLICY"),
    "policy_valid_retired_transition": ("READY", 0, None, None),
    "policy_forged_check8_content": ("MISCONFIGURED", 4, None, "MF-POLICY"),
    "policy_forged_other_round": ("MISCONFIGURED", 4, None, "MF-POLICY"),
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
        "source_authority": "project_local_contract",
        "source_milestone": milestone,
        "target_milestone": milestone,
        "received_at": "2026-07-13T18:00:00Z",
        "contemporaneity_evidence_path": f"reviews/{milestone.lower()}_receipt.md",
        "contemporaneity_evidence_sha256": "1" * 64,
        "lineage_id": "main",
        "blocking": False,
        "disposition": "informational",
        "rationale": "No blocking findings.",
        "successor_effect": "none",
    }


def _override(milestones: list[str], handoffs: list[str]) -> dict[str, Any]:
    return {
        "rule": "references/MILESTONE_FEEDBACK_HANDOFF_PROTOCOL.md#3-authority-and-precedence",
        "authority": "user",
        "reason": "The higher-authority project contract excludes this milestone.",
        "scope": "Milestone deliverable and handoff",
        "timestamp": "2026-07-13T18:00:00Z",
        "affected_milestones": milestones,
        "affected_handoffs": handoffs,
        "substitute_evidence": "reviews/not_applicable_approval.md",
        "substitute_evidence_sha256": "3" * 64,
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
    events = []
    sequence = 1
    for milestone in ("M1", "M2", "M3", "M4", "M5"):
        for event_type in (("milestone_started", "feedback_recorded", "feedback_adjudicated", "milestone_accepted", "handoff_ready", "handoff_consumed") if milestone != "M5" else ("milestone_started", "feedback_recorded", "feedback_adjudicated", "milestone_accepted", "handoff_ready")):
            events.append({
                "sequence": sequence, "event_type": event_type, "timestamp": f"2026-07-13T18:{sequence:02d}:00Z",
                "milestone": milestone, "lineage_id": "main", "actor": "planner", "authority": "user",
                "reason": f"Recorded {event_type} for {milestone}.", "evidence_path": None,
                "evidence_sha256": None, "caused_by_sequence": None, "bindings": [],
            })
            sequence += 1
    return {
        "contract_version": "1.0.0",
        "mode": "native",
        "primary_lineage": "main",
        "milestones": milestones,
        "events": events,
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
    cases["valid_native_bootstrap"]["events"] = [copy.deepcopy(cases["valid_native_bootstrap"]["events"][0])]

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
        cases["valid_not_applicable_empty_records"]["events"].append({
            "sequence": len(cases["valid_not_applicable_empty_records"]["events"]) + 1,
            "event_type": "authorized_override", "timestamp": "2026-07-13T19:00:00Z", "milestone": milestone, "lineage_id": "main",
            "actor": "planner", "authority": "user", "reason": f"Authorized {milestone} N/A.",
            "evidence_path": "reviews/not_applicable_approval.md", "evidence_sha256": "3" * 64, "caused_by_sequence": None, "bindings": [],
        })

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
    incomplete["authorized_override"] = _override(["M3"], ["M3_to_M4"])
    del incomplete["authorized_override"]["rule"]

    cases["not_applicable_status_without_override"]["milestones"]["M3"]["status"] = "not_applicable"
    cases["export_without_source_binding"]["milestones"]["M5"]["artifacts"].append({
        **_artifact("M5"),
        "role": "export",
        "artifact_kind": "released_manuscript_export",
    })
    del cases["missing_events"]["events"]
    del cases["event_missing_reason"]["events"][0]["reason"]
    return cases


def _write_bound_file(project: Path, relative: str, content: str) -> tuple[str, int]:
    path = project / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = content.encode("utf-8")
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest(), len(payload)


def _assert_synthetic_fixture(project: Path, sandbox: Path) -> None:
    """Fail closed before a smoke test can aim a mutating helper at a live project."""
    project_root = project.resolve()
    sandbox_root = sandbox.resolve()
    if project_root == sandbox_root or not project_root.is_relative_to(sandbox_root):
        raise AssertionError(f"fixture escaped its temporary sandbox: {project_root}")


def _bind_re_manuscript_chain(project: Path, ledger: dict[str, Any]) -> None:
    """Model the observed RE correction without copying project prose or live files."""
    milestones = ledger["milestones"]
    manuscript_path = "manuscript/First-Principles_RE_Essay.md"
    manuscript_hash, manuscript_bytes = _write_bound_file(
        project, manuscript_path, "Synthetic manuscript used by both M4 and M5.\n"
    )
    manuscript = {
        "role": "deliverable", "artifact_kind": "manuscript", "path": manuscript_path,
        "sha256": manuscript_hash, "bytes": manuscript_bytes,
        "verified_at": "2026-07-13T18:00:00Z", "lineage_id": "main",
    }
    for milestone, support_path, support_kind in (
        ("M4", "milestones/M4_Revision_Plan.md", "plan"),
        ("M5", "milestones/M5_Convergence_Checklist.md", "checklist"),
    ):
        support_hash, support_bytes = _write_bound_file(
            project, support_path, f"Synthetic {support_kind}; transition control only.\n"
        )
        exports = [item for item in milestones[milestone]["artifacts"] if item.get("role") == "export"]
        milestones[milestone]["artifacts"] = [
            copy.deepcopy(manuscript),
            {
                "role": "transition_control", "artifact_kind": support_kind,
                "path": support_path, "sha256": support_hash, "bytes": support_bytes,
                "verified_at": "2026-07-13T18:00:00Z", "lineage_id": "main",
            },
            *exports,
        ]
        accepted = next(
            event for event in ledger["events"]
            if event["milestone"] == milestone and event["event_type"] == "milestone_accepted"
        )
        accepted["bindings"] = [{
            "binding_type": "artifact", "path": manuscript_path, "sha256": manuscript_hash,
        }]
        evidence = milestones[milestone]["policy_evidence"]
        sidecar_path = project / evidence["check8_path"]
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        sidecar["manuscript_path"] = manuscript_path
        sidecar["manuscript_sha256"] = manuscript_hash
        evidence["manuscript_sha256"] = manuscript_hash
        evidence["check8_sha256"], _ = _write_bound_file(
            project, evidence["check8_path"], json.dumps(sidecar, indent=2) + "\n"
        )

    export = next(item for item in milestones["M5"]["artifacts"] if item.get("role") == "export")
    export["source_path"] = manuscript_path
    export["source_sha256"] = manuscript_hash
    predecessor = {
        "path": milestones["M3"]["handoff"]["packet_path"],
        "sha256": milestones["M3"]["handoff"]["packet_sha256"],
    }
    for milestone in ("M4", "M5"):
        evidence = milestones[milestone]["policy_evidence"]
        released_export = None
        if milestone == "M5":
            released_export = {
                key: export[key]
                for key in ("role", "path", "sha256", "bytes", "source_path", "source_sha256")
            }
        _rewrite_packet(
            project, ledger, milestone,
            lambda packet, predecessor=predecessor, evidence=evidence,
            released_export=released_export: packet.update({
                "predecessor_packet": predecessor,
                "deliverable": {
                    key: manuscript[key] for key in ("role", "path", "sha256", "bytes")
                },
                "released_export": released_export,
                "policy_evidence": evidence,
            }),
        )
        predecessor = {
            "path": milestones[milestone]["handoff"]["packet_path"],
            "sha256": milestones[milestone]["handoff"]["packet_sha256"],
        }


def _assert_re_chain_contract(project: Path) -> None:
    document = json.loads((project / "reviews/phase_state.json").read_text(encoding="utf-8"))
    milestones = document["milestone_framework"]["milestones"]
    assert milestones["M4"]["artifacts"][0]["path"] == "manuscript/First-Principles_RE_Essay.md"
    assert milestones["M5"]["artifacts"][0]["path"] == "manuscript/First-Principles_RE_Essay.md"
    assert any(item["role"] == "transition_control" and item["artifact_kind"] == "plan" for item in milestones["M4"]["artifacts"])
    assert any(item["role"] == "transition_control" and item["artifact_kind"] == "checklist" for item in milestones["M5"]["artifacts"])
    predecessor = None
    for milestone in ("M1", "M2", "M3", "M4", "M5"):
        handoff = milestones[milestone]["handoff"]
        assert handoff["status"] == ("ready" if milestone == "M5" else "consumed")
        packet_path = project / handoff["packet_path"]
        payload = packet_path.read_bytes()
        assert hashlib.sha256(payload).hexdigest() == handoff["packet_sha256"]
        packet = json.loads(payload)
        assert packet["predecessor_packet"] == predecessor
        predecessor = {"path": handoff["packet_path"], "sha256": handoff["packet_sha256"]}


def _phase_document(ledger: dict[str, Any], current_phase: str = "Ph4") -> dict[str, Any]:
    if current_phase == "Ph4":
        previous_phase = "Ph3_converged"
        trigger = "mcr_admission"
    else:
        previous_phase = "Ph1"
        trigger = "user_approval"
    return {
        "schema_version": "0.7.4",
        "manuscript_id": "smoke-project",
        "terminal_phase_reached": True,
        # Written atomically with terminal_phase_reached by the Planner at
        # terminal close; the two are a biconditional in phase_state_validate.
        "terminal_round_id": "round_2026-07-17_001",
        "sections": {
            "1. Test": {
                "current_phase": current_phase,
                "pre_mcr_deep_pass_completed": current_phase == "Ph4",
                "phase_entry_log": [{
                    "prev_phase": previous_phase,
                    "new_phase": current_phase,
                    "trigger": trigger,
                    "actor": "user",
                    "notes": "Fixture reached terminal state.",
                    "timestamp": "2026-07-13T18:00:00Z",
                    "model_used": None,
                }],
            }
        },
        "milestone_framework": ledger,
    }


def _materialize_native_project(project: Path) -> dict[str, Any]:
    ledger = _valid_ledger()
    previous_packet: dict[str, str] | None = None
    for index, milestone in enumerate(("M1", "M2", "M3", "M4", "M5")):
        record = ledger["milestones"][milestone]
        artifact = record["artifacts"][0]
        artifact_hash, artifact_bytes = _write_bound_file(
            project, artifact["path"], f"{milestone} canonical deliverable\n"
        )
        artifact["sha256"] = artifact_hash
        artifact["bytes"] = artifact_bytes

        feedback = record["feedback_records"][0]
        feedback_hash, _ = _write_bound_file(
            project, feedback["source_path"], f"{milestone} feedback evidence\n"
        )
        feedback["source_sha256"] = feedback_hash
        receipt_hash, _ = _write_bound_file(
            project, feedback["contemporaneity_evidence_path"], f"{milestone} feedback receipt evidence\n"
        )
        feedback["contemporaneity_evidence_sha256"] = receipt_hash
        for event_type in ("feedback_recorded", "feedback_adjudicated"):
            feedback_event = next(event for event in ledger["events"] if event["milestone"] == milestone and event["event_type"] == event_type)
            feedback_event.update({
                "evidence_path": feedback["source_path"], "evidence_sha256": feedback_hash,
                "bindings": [{"binding_type": "feedback", "path": feedback["source_path"], "sha256": feedback_hash}],
            })
        approval_hash, _ = _write_bound_file(project, record["approval"]["evidence_path"], f"{milestone} approved\n")
        accepted_event = next(event for event in ledger["events"] if event["milestone"] == milestone and event["event_type"] == "milestone_accepted")
        accepted_event.update({
            "evidence_path": record["approval"]["evidence_path"], "evidence_sha256": approval_hash,
            "bindings": [{"binding_type": "artifact", "path": artifact["path"], "sha256": artifact_hash}],
        })

        next_milestone = ("M2", "M3", "M4", "M5", None)[index]
        packet = {
            "artifact_family": "F9",
            "contract_version": "1.0.0",
            "project": "smoke-project",
            "lineage_id": "main",
            "from_milestone": milestone,
            "to_milestone": next_milestone,
            "predecessor_packet": previous_packet,
            "deliverable": {
                "role": "deliverable",
                "path": artifact["path"],
                "sha256": artifact_hash,
                "bytes": artifact_bytes,
            },
            "released_export": None,
            "inputs_consumed": [],
            "decisions_frozen": [],
            "feedback_dispositions": [{
                "feedback_id": feedback["feedback_id"],
                "disposition": feedback["disposition"],
                "rationale": feedback["rationale"],
            }],
            "open_debts": [],
            "next_milestone_instructions": [],
            "approval": {
                "authority": "user",
                "evidence_path": record["approval"]["evidence_path"],
                "approved_at": record["approval"]["approved_at"],
            },
        }
        packet_path = f"reviews/.harness/milestones/{milestone}_packet.json"
        packet_hash, _ = _write_bound_file(
            project, packet_path, json.dumps(packet, indent=2) + "\n"
        )
        record["handoff"]["packet_path"] = packet_path
        record["handoff"]["packet_sha256"] = packet_hash
        for event_type in ("handoff_ready", "handoff_consumed"):
            event = next((item for item in ledger["events"] if item["milestone"] == milestone and item["event_type"] == event_type), None)
            if event is not None:
                event["bindings"] = [{"binding_type": "handoff_packet", "path": packet_path, "sha256": packet_hash}]
        previous_packet = {"path": packet_path, "sha256": packet_hash}

    manuscript = ledger["milestones"]["M5"]["artifacts"][0]
    export_path = "exports/final-paper.pdf"
    export_hash, export_bytes = _write_bound_file(project, export_path, "released export\n")
    ledger["milestones"]["M5"]["artifacts"].append({
        "role": "export",
        "artifact_kind": "released_manuscript_export",
        "path": export_path,
        "sha256": export_hash,
        "bytes": export_bytes,
        "verified_at": "2026-07-13T18:00:00Z",
        "lineage_id": manuscript["lineage_id"],
        "source_path": manuscript["path"],
        "source_sha256": manuscript["sha256"],
    })
    export = ledger["milestones"]["M5"]["artifacts"][-1]
    _rewrite_packet(
        project,
        ledger,
        "M5",
        lambda packet: packet.update({
            "released_export": {
                key: export[key]
                for key in ("role", "path", "sha256", "bytes", "source_path", "source_sha256")
            }
        }),
    )
    _write_bound_file(
        project,
        "reviews/ph3_convergence_signoff.md",
        "---\nphase: Ph3\n---\nis_terminal: true\napproved_by: user\n",
    )
    _install_reader_accessibility_policy(project, ledger)
    return ledger


def _rewrite_packet(project: Path, ledger: dict[str, Any], milestone: str, mutate: Any) -> None:
    handoff = ledger["milestones"][milestone]["handoff"]
    packet_path = project / handoff["packet_path"]
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    mutate(packet)
    payload = (json.dumps(packet, indent=2) + "\n").encode("utf-8")
    packet_path.write_bytes(payload)
    handoff["packet_sha256"] = hashlib.sha256(payload).hexdigest()
    for event in ledger.get("events", []):
        if event.get("milestone") == milestone and event.get("event_type") in {"handoff_ready", "handoff_consumed"}:
            event["bindings"] = [{
                "binding_type": "handoff_packet", "path": handoff["packet_path"], "sha256": handoff["packet_sha256"],
            }]


def _install_reader_accessibility_policy(project: Path, ledger: dict[str, Any]) -> None:
    """Install a real resolver artifact and exact progressive policy evidence."""
    import reader_accessibility_policy as policy
    resolved = policy.resolve_policy(project)
    resolved_path = project / "reviews/.harness/policy/reader_accessibility_resolved.json"
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path.write_text(json.dumps(resolved, indent=2) + "\n", encoding="utf-8")
    binding = policy.phase_state_binding(resolved, resolved_path, project)
    ledger["policy_bindings"] = {"reader_accessibility": binding}
    milestones = ledger["milestones"]
    milestones["M1"]["policy_evidence"] = {"reader_model": resolved["resolved_profile"]["domain_native_register"]["reader_model"]}
    milestones["M3"]["policy_evidence"] = {"profile_path": binding["resolved_path"], "profile_sha256": binding["profile_sha256"], "resolved_sha256": binding["resolved_sha256"], "attestation_view_pin": binding["attestation_view_pin"], "exemplar_view_pin": binding["exemplar_view_pin"]}
    for milestone, phase in (("M4", "Ph3"), ("M5", "Ph4")):
        manuscript = milestones[milestone]["artifacts"][0]
        subchecks = {key: {"findings": []} for key in "ABCDEFGH"}
        transition_snapshot = {key: binding["transitions"][key]["state"] for key in ("G", "H", "VE")}
        computed = policy.recompute_check8({"subchecks": subchecks, "ve": {"aggregate_member": False, "gate_contribution": "none", "findings": []}}, binding["transitions"])
        sidecar = {
            "schema_version": "check8_evidence.v1", "cycle_id": f"{milestone}-policy-round", "profile_path": binding["resolved_path"],
            "profile_sha256": binding["profile_sha256"], "attestation_view_pin": binding["attestation_view_pin"], "exemplar_view_pin": binding["exemplar_view_pin"], "manuscript_path": manuscript["path"],
            "manuscript_sha256": manuscript["sha256"], "phase": phase,
            "transition_snapshot": transition_snapshot, "subchecks": subchecks,
            "subcheck_verdicts": computed["subcheck_verdicts"],
            "ve": {"aggregate_member": False, "gate_contribution": "none", "findings": []},
            "aggregate_verdict": computed["aggregate_verdict"],
        }
        check_path = f"reviews/.harness/policy/{milestone.lower()}_check8.json"
        check_hash, _ = _write_bound_file(project, check_path, json.dumps(sidecar, indent=2) + "\n")
        evidence = {"profile_path": binding["resolved_path"], "profile_sha256": binding["profile_sha256"], "resolved_sha256": binding["resolved_sha256"], "attestation_view_pin": binding["attestation_view_pin"], "exemplar_view_pin": binding["exemplar_view_pin"], "manuscript_sha256": manuscript["sha256"], "cycle_id": sidecar["cycle_id"], "check8_path": check_path, "check8_sha256": check_hash, "aggregate_verdict": "CLEAN", "phase": phase}
        milestones[milestone]["policy_evidence"] = evidence
    predecessor = None
    for milestone in ("M1", "M2", "M3", "M4", "M5"):
        evidence = milestones[milestone].get("policy_evidence")
        _rewrite_packet(project, ledger, milestone, lambda packet, evidence=evidence, predecessor=predecessor: packet.update({"policy_evidence": evidence, "predecessor_packet": predecessor}))
        handoff = milestones[milestone]["handoff"]
        predecessor = {"path": handoff["packet_path"], "sha256": handoff["packet_sha256"]}


def _reset_milestone(record: dict[str, Any], status: str = "not_started") -> None:
    record.update({
        "status": status,
        "artifacts": [],
        "feedback_records": [],
        "approval": {"status": "pending", "authority": None, "evidence_path": None, "approved_at": None},
        "handoff": {"status": "not_ready", "packet_path": None, "packet_sha256": None},
        "dependency_state": "current",
        "authorized_override": None,
    })
    record.pop("policy_evidence", None)


def _resequence_events(ledger: dict[str, Any]) -> None:
    for sequence, event in enumerate(ledger["events"], 1):
        event["sequence"] = sequence
        event["timestamp"] = f"2026-07-13T18:{sequence:02d}:00Z"


def _drop_milestone_events(ledger: dict[str, Any], *milestones: str) -> None:
    ledger["events"] = [event for event in ledger["events"] if event["milestone"] not in set(milestones)]
    _resequence_events(ledger)


def _append_deliverable_recorded(
    ledger: dict[str, Any], milestone: str, *, digest: str | None = None,
) -> None:
    record = ledger["milestones"][milestone]
    deliverable = next(
        artifact for artifact in record["artifacts"]
        if artifact["role"] == "deliverable"
        and artifact["lineage_id"] == ledger["primary_lineage"]
    )
    ledger["events"].append({
        "sequence": len(ledger["events"]) + 1,
        "event_type": "deliverable_recorded",
        "timestamp": "2026-07-13T19:32:00Z",
        "milestone": milestone,
        "lineage_id": ledger["primary_lineage"],
        "actor": "planner",
        "authority": None,
        "reason": f"Recorded the current {milestone} deliverable.",
        "evidence_path": None,
        "evidence_sha256": None,
        "caused_by_sequence": None,
        "bindings": [{
            "binding_type": "artifact",
            "path": deliverable["path"],
            "sha256": digest or deliverable["sha256"],
        }],
    })


def _write_real_case(case: str, project: Path) -> None:
    ledger = _materialize_native_project(project)
    milestones = ledger["milestones"]

    if case.startswith("re_"):
        _bind_re_manuscript_chain(project, ledger)

    document_phase = "Ph4"
    if case == "valid_ph2_target":
        document_phase = "Ph2"
        milestones["M4"]["status"] = "in_progress"
        milestones["M4"]["approval"] = {"status": "pending", "authority": None, "evidence_path": None, "approved_at": None}
        milestones["M4"]["handoff"] = {"status": "not_ready", "packet_path": None, "packet_sha256": None}
        _reset_milestone(milestones["M5"])
        next_sequence = len(ledger["events"]) + 1
        ledger["events"].extend([
            {"sequence": next_sequence, "event_type": "milestone_reopened", "timestamp": "2026-07-13T19:30:00Z", "milestone": "M4", "lineage_id": "main", "actor": "planner", "authority": "user", "reason": "M4 reopened for Ph2 work.", "evidence_path": None, "evidence_sha256": None, "caused_by_sequence": None, "bindings": []},
            {"sequence": next_sequence + 1, "event_type": "milestone_started", "timestamp": "2026-07-13T19:31:00Z", "milestone": "M4", "lineage_id": "main", "actor": "planner", "authority": "user", "reason": "M4 restarted in Ph2.", "evidence_path": None, "evidence_sha256": None, "caused_by_sequence": None, "bindings": []},
        ])
        _append_deliverable_recorded(ledger, "M4")
        _drop_milestone_events(ledger, "M5")
    elif case in {
        "valid_approved_legacy_migration", "legacy_handoffs_without_project_identity",
        "legacy_m3_boundary_target", "legacy_m3_boundary_m5_target",
    }:
        evidence_hash, _ = _write_bound_file(project, "reviews/migration_approval.md", "status: APPROVED\nauthority: user\n")
        report_hash, _ = _write_bound_file(project, "reviews/migration_report.md", '{"adjudication_outcome":"approved","authority":"user"}\n')
        ledger["mode"] = "legacy"
        ledger["migration_boundary"] = {
            "authority": "user",
            "evidence_path": "reviews/migration_approval.md",
            "evidence_sha256": evidence_hash,
            "approved_at": "2026-07-13T18:00:00Z",
            "completed_through": "M3" if case.startswith("legacy_m3_boundary") else "M5",
            "report_path": "reviews/migration_report.md",
            "report_sha256": report_hash,
        }
        if case == "legacy_handoffs_without_project_identity":
            predecessor = None
            for milestone in ("M1", "M2", "M3", "M4", "M5"):
                _rewrite_packet(
                    project, ledger, milestone,
                    lambda packet, predecessor=predecessor: packet.update({
                        "project": "forged-legacy-project",
                        "predecessor_packet": predecessor,
                    }),
                )
                handoff = milestones[milestone]["handoff"]
                predecessor = {"path": handoff["packet_path"], "sha256": handoff["packet_sha256"]}
        if case.startswith("legacy_m3_boundary"):
            _reset_milestone(milestones["M4"])
            _reset_milestone(milestones["M5"])
            _drop_milestone_events(ledger, "M4", "M5")
    elif case == "native_m5_not_started_target":
        _reset_milestone(milestones["M5"])
        _drop_milestone_events(ledger, "M5")
    elif case in {
        "authorized_not_applicable", "allowed_advisor_override", "rejected_generator_override",
        "valid_project_local_override", "missing_project_local_override", "outside_project_local_override",
        "absolute_project_local_override", "stale_override_evidence",
    }:
        target = milestones["M4"]
        target.update({
            "status": "not_applicable", "applicability": "not_applicable",
            "artifacts": [], "feedback_records": [],
            "approval": {"status": "not_applicable", "authority": None, "evidence_path": None, "approved_at": None},
            "handoff": {"status": "not_applicable", "packet_path": None, "packet_sha256": None},
            "dependency_state": "not_applicable",
            "authorized_override": _override(["M4"], ["M4_to_M5"]),
        })
        target.pop("policy_evidence", None)
        override_hash, _ = _write_bound_file(
            project, target["authorized_override"]["substitute_evidence"], "authorized N/A\n"
        )
        target["authorized_override"]["substitute_evidence_sha256"] = override_hash
        ledger["events"].append({
            "sequence": len(ledger["events"]) + 1, "event_type": "authorized_override",
            "timestamp": "2026-07-13T19:00:00Z", "milestone": "M4", "lineage_id": "main", "actor": "planner",
            "authority": "user", "reason": "Authorized M4 as not applicable.",
            "evidence_path": target["authorized_override"]["substitute_evidence"],
            "evidence_sha256": override_hash, "caused_by_sequence": None, "bindings": [],
        })
        if case == "allowed_advisor_override":
            target["authorized_override"]["authority"] = "advisor"
        elif case == "rejected_generator_override":
            target["authorized_override"]["authority"] = "generator"
        elif case in {
            "valid_project_local_override", "missing_project_local_override", "outside_project_local_override",
            "absolute_project_local_override",
        }:
            target["authorized_override"]["authority"] = "project_local_contract"
            if case == "valid_project_local_override":
                _write_bound_file(project, "directives.md", "## Override authority\n\nProject-local exception.\n")
                target["authorized_override"]["rule"] = "directives.md#override-authority"
            elif case == "missing_project_local_override":
                target["authorized_override"]["rule"] = "missing-directives.md#override-authority"
            else:
                if case == "outside_project_local_override":
                    _write_bound_file(project.parent, "outside-directives.md", "## Override authority\n")
                    target["authorized_override"]["rule"] = "../outside-directives.md#override-authority"
                else:
                    _write_bound_file(project, "directives.md", "## Override authority\n")
                    target["authorized_override"]["rule"] = f"{project / 'directives.md'}#override-authority"
        if case == "stale_override_evidence":
            (project / target["authorized_override"]["substitute_evidence"]).write_text(
                "changed authorization evidence\n", encoding="utf-8"
            )
        override_event = next(event for event in ledger["events"] if event["milestone"] == "M4" and event["event_type"] == "authorized_override")
        override_event["authority"] = target["authorized_override"]["authority"]
        ledger["events"] = [
            event for event in ledger["events"]
            if event["milestone"] != "M4" or event["event_type"] in {"milestone_started", "authorized_override"}
        ]
        _resequence_events(ledger)
        milestones["M5"].update({
            "status": "not_started", "artifacts": [], "feedback_records": [],
            "approval": {"status": "pending", "authority": None, "evidence_path": None, "approved_at": None},
            "handoff": {"status": "not_ready", "packet_path": None, "packet_sha256": None},
        })
        milestones["M5"].pop("policy_evidence", None)
        _drop_milestone_events(ledger, "M5")
    elif case == "absent_namespace":
        pass
    elif case == "missing_purpose_real":
        del milestones["M2"]["purpose"]
    elif case == "m4_plan_only_real":
        milestones["M4"]["artifacts"][0]["artifact_kind"] = "plan"
    elif case == "m5_checklist_only_real":
        milestones["M5"]["artifacts"][0]["artifact_kind"] = "checklist"
    elif case == "missing_feedback_provenance_real":
        del milestones["M3"]["feedback_records"][0]["source_sha256"]
    elif case == "stale_feedback_contemporaneity_evidence":
        receipt_path = milestones["M3"]["feedback_records"][0]["contemporaneity_evidence_path"]
        (project / receipt_path).write_text("drifted receipt evidence\n", encoding="utf-8")
    elif case == "two_primary_lineages_real":
        ledger["primary_lineage"] = ["main", "alternate"]
    elif case == "artifact_lineage_mismatch":
        milestones["M3"]["artifacts"][0]["lineage_id"] = "alternate"
    elif case == "successor_without_consumed_handoff":
        milestones["M2"]["handoff"]["status"] = "ready"
    elif case == "na_without_complete_override":
        target = milestones["M4"]
        target["status"] = "not_applicable"
        target["applicability"] = "not_applicable"
        target["authorized_override"] = None
    elif case in {"stale_deliverable_hash", "re_m5_manuscript_changed"}:
        target_milestone = "M5" if case.startswith("re_") else "M3"
        (project / milestones[target_milestone]["artifacts"][0]["path"]).write_text("drifted bytes\n", encoding="utf-8")
    elif case == "stale_f9_packet_hash":
        (project / milestones["M3"]["handoff"]["packet_path"]).write_text("{}\n", encoding="utf-8")
    elif case in {"reopened_upstream_current_downstream", "re_m2_reopened_blocks_m5"}:
        milestones["M2"]["status"] = "reopened"
        milestones["M2"]["approval"]["status"] = "reopened"
    elif case == "malformed_derived_claim":
        view_hash, view_bytes = _write_bound_file(project, "reviews/lifecycle_view.md", "generated: true\n")
        milestones["M5"]["artifacts"].append({
            "role": "derived_view", "artifact_kind": "lifecycle_status_view",
            "path": "reviews/lifecycle_view.md", "sha256": view_hash, "bytes": view_bytes,
            "verified_at": "2026-07-13T18:00:00Z", "lineage_id": "main",
        })
    elif case == "manual_status_claims_authority":
        status_hash, status_bytes = _write_bound_file(
            project, "reviews/manual_status.md", "Authoritative lifecycle status: M5 accepted.\n"
        )
        milestones["M5"]["artifacts"].append({
            "role": "evidence", "artifact_kind": "manual_status",
            "path": "reviews/manual_status.md", "sha256": status_hash, "bytes": status_bytes,
            "verified_at": "2026-07-13T18:00:00Z", "lineage_id": "main",
        })
    elif case == "list_shaped_approval":
        milestones["M2"]["approval"] = []
    elif case == "fabricated_f9_authority":
        _rewrite_packet(project, ledger, "M5", lambda packet: packet["approval"].update({"authority": "generator"}))
    elif case == "fabricated_matching_authority":
        milestones["M5"]["approval"]["authority"] = "generator"
        _rewrite_packet(project, ledger, "M5", lambda packet: packet["approval"].update({"authority": "generator"}))
    elif case == "missing_approval_evidence":
        (project / milestones["M5"]["approval"]["evidence_path"]).unlink()
    elif case == "mismatched_f9_approval_evidence":
        _write_bound_file(project, "reviews/fabricated_approval.md", "fabricated approval\n")
        _rewrite_packet(
            project, ledger, "M5",
            lambda packet: packet["approval"].update({"evidence_path": "reviews/fabricated_approval.md"}),
        )
    elif case == "forged_f9_project_identity":
        _rewrite_packet(project, ledger, "M5", lambda packet: packet.update({"project": "other-project"}))
    elif case == "forged_f9_from_milestone":
        _rewrite_packet(
            project, ledger, "M5",
            lambda packet: packet.update({
                "from_milestone": "M4", "to_milestone": "M5", "released_export": None,
            }),
        )
    elif case == "forged_f9_to_milestone":
        export = next(item for item in milestones["M5"]["artifacts"] if item["role"] == "export")
        _rewrite_packet(
            project, ledger, "M4",
            lambda packet: packet.update({
                "from_milestone": "M5",
                "to_milestone": None,
                "released_export": {
                    key: export[key]
                    for key in ("role", "path", "sha256", "bytes", "source_path", "source_sha256")
                },
            }),
        )
        m4_handoff = milestones["M4"]["handoff"]
        _rewrite_packet(
            project, ledger, "M5",
            lambda packet: packet.update({
                "predecessor_packet": {
                    "path": m4_handoff["packet_path"], "sha256": m4_handoff["packet_sha256"],
                }
            }),
        )
    elif case == "reordered_artifacts_feedback_lineage":
        evidence_hash, evidence_bytes = _write_bound_file(project, "reviews/reordered_evidence.md", "supporting evidence\n")
        milestones["M3"]["artifacts"].insert(0, {
            "role": "evidence", "artifact_kind": "review",
            "path": "reviews/reordered_evidence.md", "sha256": evidence_hash, "bytes": evidence_bytes,
            "verified_at": "2026-07-13T18:00:00Z", "lineage_id": "alternate",
        })
    elif case in {
        "active_distinct_lineages", "active_duplicate_lineage", "implicit_supersession", "explicit_supersession",
        "cyclic_supersession",
    }:
        record = milestones["M3"]
        alternate = copy.deepcopy(record["artifacts"][0])
        alternate["lineage_id"] = "main" if case == "active_duplicate_lineage" else "alternate"
        alternate["path"] = "research_notes/m3_alternate.md"
        alternate["sha256"], alternate["bytes"] = _write_bound_file(project, alternate["path"], "alternate M3\n")
        record["artifacts"].append(alternate)
        record["status"] = "in_progress" if case in {"active_distinct_lineages", "active_duplicate_lineage"} else "superseded"
        ledger["events"] = [event for event in ledger["events"] if event["milestone"] != "M3" or event["event_type"] in {"milestone_started", "feedback_recorded", "feedback_adjudicated"}]
        if case in {"active_distinct_lineages", "active_duplicate_lineage"}:
            _append_deliverable_recorded(ledger, "M3")
        if case == "explicit_supersession":
            alternate["supersedes_lineage_id"] = "main"
            ledger["events"].append({
                "sequence": 1, "event_type": "milestone_superseded", "timestamp": "2026-07-13T19:00:00Z",
                "milestone": "M3", "lineage_id": "main", "actor": "planner", "authority": "user",
                "reason": "Alternate lineage explicitly superseded the prior M3 lineage.", "evidence_path": None,
                "evidence_sha256": None, "caused_by_sequence": None,
                "bindings": [{"binding_type": "current_content", "path": alternate["path"], "sha256": alternate["sha256"]}],
            })
        elif case == "cyclic_supersession":
            alternate["supersedes_lineage_id"] = "main"
            record["artifacts"][0]["supersedes_lineage_id"] = "alternate"
        record["approval"] = {"status": "pending", "authority": None, "evidence_path": None, "approved_at": None}
        record["handoff"] = {"status": "not_ready", "packet_path": None, "packet_sha256": None}
        _reset_milestone(milestones["M4"])
        _reset_milestone(milestones["M5"])
        _drop_milestone_events(ledger, "M4", "M5")
        _resequence_events(ledger)
    elif case in {"accepted_primary_supersedes_preserved", "accepted_unsuperseded_nonprimary"}:
        record = milestones["M5"]
        primary = next(item for item in record["artifacts"] if item["role"] == "deliverable")
        alternate = copy.deepcopy(primary)
        alternate["lineage_id"] = "alternate"
        alternate["path"] = "research_notes/m5_preserved_alternate.md"
        alternate["sha256"], alternate["bytes"] = _write_bound_file(
            project, alternate["path"], "preserved alternate M5 manuscript\n"
        )
        record["artifacts"].append(alternate)
        if case == "accepted_primary_supersedes_preserved":
            primary["supersedes_lineage_id"] = "alternate"
    elif case == "ph4_without_mcr_admission":
        pass
    elif case == "inf_unlocked_ph3_sibling_blocks_ph4":
        pass
    elif case == "ph4_retracted_mcr_admission":
        pass
    elif case == "export_source_mismatch":
        export = next(item for item in milestones["M5"]["artifacts"] if item["role"] == "export")
        export["source_sha256"] = "f" * 64
    elif case == "terminal_f9_export_mismatch":
        _rewrite_packet(
            project, ledger, "M5",
            lambda packet: packet["released_export"].update({"sha256": "e" * 64}),
        )
    elif case == "list_shaped_milestones":
        ledger["milestones"] = []
    elif case == "missing_accepted_event":
        ledger["events"] = [event for event in ledger["events"] if not (event["milestone"] == "M3" and event["event_type"] == "milestone_accepted")]
    elif case in {
        "valid_deliverable_recorded_event",
        "missing_deliverable_recorded_event",
        "deliverable_record_binding_mismatch",
    }:
        record = milestones["M3"]
        record["status"] = "in_progress"
        record["feedback_records"] = []
        record["approval"] = {
            "status": "pending", "authority": None,
            "evidence_path": None, "approved_at": None,
        }
        record["handoff"] = {
            "status": "not_ready", "packet_path": None, "packet_sha256": None,
        }
        for downstream in ("M4", "M5"):
            _reset_milestone(milestones[downstream])
        ledger["events"] = [
            event for event in ledger["events"]
            if event["milestone"] in {"M1", "M2"}
            or (
                event["milestone"] == "M3"
                and event["event_type"] == "milestone_started"
            )
        ]
        if case != "missing_deliverable_recorded_event":
            digest = (
                "f" * 64
                if case == "deliverable_record_binding_mismatch"
                else None
            )
            _append_deliverable_recorded(ledger, "M3", digest=digest)
        _resequence_events(ledger)
    elif case == "unordered_events":
        ledger["events"][1]["sequence"] = ledger["events"][0]["sequence"]
    elif case == "stale_without_event":
        ledger["milestones"]["M4"]["dependency_state"] = "needs_revalidation"
    elif case == "stale_bad_cause":
        ledger["milestones"]["M4"]["dependency_state"] = "needs_revalidation"
        ledger["events"].append({
            "sequence": len(ledger["events"]) + 1, "event_type": "downstream_stale", "timestamp": "2026-07-13T19:30:00Z",
            "milestone": "M4", "lineage_id": "main", "actor": "planner", "authority": "user", "reason": "M4 stale.",
            "evidence_path": None, "evidence_sha256": None, "caused_by_sequence": 1, "bindings": [],
        })
    elif case == "obsolete_acceptance_event":
        ledger["events"].append({
            "sequence": len(ledger["events"]) + 1, "event_type": "milestone_reopened", "timestamp": "2026-07-13T19:30:00Z",
            "milestone": "M3", "lineage_id": "main", "actor": "planner", "authority": "user", "reason": "M3 reopened.",
            "evidence_path": None, "evidence_sha256": None, "caused_by_sequence": None, "bindings": [],
        })
    elif case == "event_artifact_binding_mismatch":
        event = next(item for item in ledger["events"] if item["milestone"] == "M3" and item["event_type"] == "milestone_accepted")
        event["bindings"][0]["sha256"] = "f" * 64
    elif case == "event_f9_binding_mismatch":
        event = next(item for item in ledger["events"] if item["milestone"] == "M3" and item["event_type"] == "handoff_consumed")
        event["bindings"][0]["sha256"] = "f" * 64
    elif case == "invalid_event_timestamp":
        ledger["events"][0]["timestamp"] = "2026-07-13 18:00"
    elif case == "invalid_event_date_z":
        ledger["events"][0]["timestamp"] = "2026-07-13Z"
    elif case == "invalid_event_offset":
        ledger["events"][0]["timestamp"] = "2026-07-13T18:00:00+00:00"
    elif case == "invalid_event_naive":
        ledger["events"][0]["timestamp"] = "2026-07-13T18:00:00"
    elif case == "invalid_event_malformed":
        ledger["events"][0]["timestamp"] = "not-a-time"
    elif case == "accepted_to_in_progress_old_events":
        ledger["milestones"]["M3"]["status"] = "in_progress"
        ledger["milestones"]["M3"]["approval"] = {"status": "pending", "authority": None, "evidence_path": None, "approved_at": None}
        ledger["milestones"]["M3"]["handoff"] = {"status": "not_ready", "packet_path": None, "packet_sha256": None}
    elif case == "valid_reopen_restart_transition":
        record = ledger["milestones"]["M3"]
        record["status"] = "in_progress"
        record["approval"] = {"status": "pending", "authority": None, "evidence_path": None, "approved_at": None}
        record["handoff"] = {"status": "not_ready", "packet_path": None, "packet_sha256": None}
        ledger["events"].extend([
            {"sequence": len(ledger["events"]) + 1, "event_type": "milestone_reopened", "timestamp": "2026-07-13T19:30:00Z", "milestone": "M3", "lineage_id": "main", "actor": "planner", "authority": "user", "reason": "M3 reopened.", "evidence_path": None, "evidence_sha256": None, "caused_by_sequence": None, "bindings": []},
            {"sequence": len(ledger["events"]) + 2, "event_type": "milestone_started", "timestamp": "2026-07-13T19:31:00Z", "milestone": "M3", "lineage_id": "main", "actor": "planner", "authority": "user", "reason": "M3 restarted.", "evidence_path": None, "evidence_sha256": None, "caused_by_sequence": None, "bindings": []},
        ])
        _append_deliverable_recorded(ledger, "M3")
        _reset_milestone(ledger["milestones"]["M4"]); _reset_milestone(ledger["milestones"]["M5"])
        ledger["events"] = [event for event in ledger["events"] if event["milestone"] not in {"M4", "M5"}]
        _resequence_events(ledger)
    elif case == "feedback_wrong_milestone_binding":
        source = ledger["milestones"]["M2"]["feedback_records"][0]
        event = next(item for item in ledger["events"] if item["milestone"] == "M3" and item["event_type"] == "feedback_recorded")
        event.update({"evidence_path": source["source_path"], "evidence_sha256": source["source_sha256"], "bindings": [{"binding_type": "feedback", "path": source["source_path"], "sha256": source["source_sha256"]}]})
    elif case == "cross_subject_revalidation":
        cause = len(ledger["events"]) + 1
        ledger["events"].extend([
            {"sequence": cause, "event_type": "milestone_reopened", "timestamp": "2026-07-13T19:30:00Z", "milestone": "M2", "lineage_id": "main", "actor": "planner", "authority": "user", "reason": "M2 reopened.", "evidence_path": None, "evidence_sha256": None, "caused_by_sequence": None, "bindings": []},
            {"sequence": cause + 1, "event_type": "downstream_stale", "timestamp": "2026-07-13T19:31:00Z", "milestone": "M3", "lineage_id": "main", "actor": "planner", "authority": "user", "reason": "M3 stale.", "evidence_path": None, "evidence_sha256": None, "caused_by_sequence": cause, "bindings": []},
            {"sequence": cause + 2, "event_type": "downstream_revalidated", "timestamp": "2026-07-13T19:32:00Z", "milestone": "M4", "lineage_id": "main", "actor": "planner", "authority": "user", "reason": "Wrong subject revalidation.", "evidence_path": None, "evidence_sha256": None, "caused_by_sequence": cause + 1, "bindings": []},
        ])

    if case.startswith("policy_"):
        binding = ledger["policy_bindings"]["reader_accessibility"]
        if case == "policy_hash_drift":
            binding["profile_sha256"] = "0" * 64
        if case == "policy_missing_m1_intent":
            milestones["M1"].pop("policy_evidence")
        elif case == "policy_missing_m3_profile":
            milestones["M3"].pop("policy_evidence")
        elif case == "policy_missing_m4_current_hash":
            milestones["M4"]["policy_evidence"].pop("manuscript_sha256")
        elif case == "policy_native_binding_omitted":
            ledger.pop("policy_bindings")
        elif case == "policy_valid_bootstrap":
            for record in milestones.values(): _reset_milestone(record)
            ledger["events"] = []
        elif case == "policy_valid_m1_started":
            intended = milestones["M1"]["policy_evidence"]
            _reset_milestone(milestones["M1"], "in_progress")
            milestones["M1"]["policy_evidence"] = intended
            for name in ("M2", "M3", "M4", "M5"): _reset_milestone(milestones[name])
            ledger["events"] = [event for event in ledger["events"] if event["milestone"] == "M1" and event["event_type"] == "milestone_started"]
            _resequence_events(ledger)
        elif case == "policy_valid_m3_started":
            profile_evidence = milestones["M3"]["policy_evidence"]
            _reset_milestone(milestones["M3"], "in_progress")
            milestones["M3"]["policy_evidence"] = profile_evidence
            for name in ("M4", "M5"): _reset_milestone(milestones[name])
            ledger["events"] = [event for event in ledger["events"] if event["milestone"] in {"M1", "M2"} or (event["milestone"] == "M3" and event["event_type"] == "milestone_started")]
            _resequence_events(ledger)
        elif case == "policy_retired_without_events":
            binding["transitions"]["H"] = {"state": "retired", "observed_count": 0, "last_event_sequence": None, "events": []}
        elif case == "policy_valid_retired_transition":
            event_hash, _ = _write_bound_file(project, "reviews/.harness/policy/h_transition.md", "Planner-approved H observations.\n")
            common = {"actor": "planner", "authority": "user", "approved": True, "evidence_path": "reviews/.harness/policy/h_transition.md", "evidence_sha256": event_hash}
            binding["transitions"]["H"] = {"state": "retired", "observed_count": 2, "last_event_sequence": 3, "events": [
                {**common, "sequence": 1, "event": "policy_transition_observed", "observed_count": 1, "cycle_id":"h-1", "manuscript_sha256":"1"*64, "content_sha256":"2"*64},
                {**common, "sequence": 2, "event": "policy_transition_observed", "observed_count": 2, "cycle_id":"h-2", "manuscript_sha256":"1"*64, "content_sha256":"3"*64},
                {**common, "sequence": 3, "event": "planner_transition_approved", "observed_count": 2, "cycle_id":"h-retire", "manuscript_sha256":"1"*64, "content_sha256":"4"*64},
            ]}
            import reader_accessibility_policy as ra_policy
            for name in ("M4", "M5"):
                evidence = milestones[name]["policy_evidence"]; sidecar_path = project / evidence["check8_path"]
                sidecar = json.loads(sidecar_path.read_text(encoding="utf-8")); sidecar["transition_snapshot"]["H"] = "retired"
                computed = ra_policy.recompute_check8(sidecar, binding["transitions"])
                sidecar["subcheck_verdicts"] = computed["subcheck_verdicts"]; sidecar["aggregate_verdict"] = computed["aggregate_verdict"]
                new_hash, _ = _write_bound_file(project, evidence["check8_path"], json.dumps(sidecar, indent=2) + "\n")
                evidence["check8_sha256"] = new_hash; evidence["aggregate_verdict"] = computed["aggregate_verdict"]
            predecessor = {"path": milestones["M3"]["handoff"]["packet_path"], "sha256": milestones["M3"]["handoff"]["packet_sha256"]}
            for name in ("M4", "M5"):
                evidence = milestones[name]["policy_evidence"]
                _rewrite_packet(project, ledger, name, lambda packet, evidence=evidence, predecessor=predecessor: packet.update({"policy_evidence": evidence, "predecessor_packet": predecessor}))
                predecessor = {"path": milestones[name]["handoff"]["packet_path"], "sha256": milestones[name]["handoff"]["packet_sha256"]}
        elif case == "policy_forged_check8_content":
            evidence = milestones["M4"]["policy_evidence"]
            sidecar_path = project / evidence["check8_path"]
            sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
            sidecar["subchecks"]["A"]["findings"] = [{"finding_id":"forged-a","severity":"BLOCKER","independence_group":"forged"}]
            forged_hash, _ = _write_bound_file(project, evidence["check8_path"], json.dumps(sidecar, indent=2) + "\n")
            evidence["check8_sha256"] = forged_hash
            _rewrite_packet(project, ledger, "M4", lambda packet: packet.update({"policy_evidence": evidence}))
        elif case == "policy_forged_other_round":
            evidence = milestones["M4"]["policy_evidence"]
            sidecar_path = project / evidence["check8_path"]
            sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
            sidecar["cycle_id"] = "FORGED-OTHER-ROUND"
            forged_hash, _ = _write_bound_file(project, evidence["check8_path"], json.dumps(sidecar, indent=2) + "\n")
            evidence["check8_sha256"] = forged_hash
            _rewrite_packet(project, ledger, "M4", lambda packet: packet.update({"policy_evidence": evidence}))

    document: Any = _phase_document(ledger, document_phase)
    if case == "absent_namespace":
        del document["milestone_framework"]
    elif case == "retired_milestone_assignment":
        document["milestone_assignment"] = {"M4a": "Ph2", "M4b": "Ph3"}
    elif case == "list_shaped_sections":
        document["sections"] = []
    elif case == "ph4_without_mcr_admission":
        document["sections"]["1. Test"]["phase_entry_log"][0]["trigger"] = "user_approval"
    elif case == "inf_unlocked_ph3_sibling_blocks_ph4":
        document["sections"]["milestone5_v2_coauthor_layperson"] = {
            "current_phase": "Ph3",
            "last_approved_phase": "Ph2",
            "ceiling_locked": False,
            "applicable_ceiling": "Ph4",
            "pre_mcr_deep_pass_completed": True,
            "phase_entry_log": [{
                "prev_phase": "Ph2", "new_phase": "Ph3", "trigger": "user_approval",
                "actor": "user", "notes": "Synthetic unlocked sibling fixture.",
                "timestamp": "2026-07-13T18:01:00Z", "model_used": None,
            }],
        }
    elif case == "valid_ph4_before_closure":
        document["terminal_phase_reached"] = False
    elif case == "valid_ph4_ceiling_locked":
        section = document["sections"]["1. Test"]
        section.update({
            "current_phase": "Ph2",
            "ceiling_locked": True,
            "last_approved_phase": "Ph2",
            "section_ceiling_override": "Ph2",
            "pre_mcr_deep_pass_completed": False,
            "phase_entry_log": [{
                "prev_phase": "Ph1", "new_phase": "Ph2", "trigger": "user_approval",
                "actor": "user", "notes": "Approved at explicit ceiling.",
                "timestamp": "2026-07-13T18:00:00Z", "model_used": None,
            }],
        })
    elif case == "ph4_retracted_mcr_admission":
        section = document["sections"]["1. Test"]
        section["phase_entry_log"].extend([
            {
                "prev_phase": "Ph4", "new_phase": "Ph3", "trigger": "retraction",
                "actor": "user", "notes": "Retracted admission.",
                "timestamp": "2026-07-13T18:01:00Z", "model_used": None,
            },
            {
                "prev_phase": "Ph3", "new_phase": "Ph4", "trigger": "user_approval",
                "actor": "user", "notes": "Invalid direct return.",
                "timestamp": "2026-07-13T18:02:00Z", "model_used": None,
            },
        ])
    elif case == "ph4_empty_sections":
        document["sections"] = {}
    elif case == "ph4_nonobject_section":
        document["sections"] = {"1. Test": ["not", "an", "object"]}
    elif case == "ph4_list_ceiling_override":
        document["sections"]["1. Test"]["section_ceiling_override"] = ["Ph2"]
    elif case == "ph4_dict_ceiling_override":
        document["sections"]["1. Test"]["section_ceiling_override"] = {"phase": "Ph2"}
    elif case == "native_missing_project_identity":
        document.pop("manuscript_id", None)
    elif case == "project_identity_disagreement":
        document["milestone_framework"]["policy_bindings"]["reader_accessibility"]["project_identity"] = "other-project"
    elif case == "legacy_handoffs_without_project_identity":
        document.pop("manuscript_id", None)
        document["milestone_framework"]["policy_bindings"]["reader_accessibility"]["project_identity"] = None
    reviews = project / "reviews"
    reviews.mkdir(parents=True, exist_ok=True)
    (reviews / "phase_state.json").write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def _run_real_validator(
    project: Path, target: str | None, registry: Path | None = None,
) -> tuple[int, dict[str, Any], str]:
    command = [sys.executable, str(VALIDATOR), "--project-root", str(project), "--json"]
    if target:
        command.extend(["--target", target])
    if registry is not None:
        command.extend(["--exemplar-registry", str(registry)])
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        payload = {}
    return result.returncode, payload, result.stderr


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_exemplar_registry(
    project: Path, registry: Path, exemplar_class: str, *, duplicate: bool = False,
) -> None:
    evidence_dir = project / "reviews" / "exemplar"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    approval = evidence_dir / "approval.md"
    approval.write_text("status: APPROVED\nauthority: user\n", encoding="utf-8")
    milestone_result = evidence_dir / "milestone_validation.json"
    milestone_result.write_text(
        json.dumps({"validator_version": PLUGIN_VERSION, "outcome": "READY" if exemplar_class == "clean_lifecycle_exemplar" else "LEGACY_READY"}) + "\n",
        encoding="utf-8",
    )
    phase_result = evidence_dir / "phase_validation.json"
    phase_result.write_text(json.dumps({"outcome": "PASS"}) + "\n", encoding="utf-8")
    evidence = [
        {"role": "milestone_validator", "path": "reviews/exemplar/milestone_validation.json", "sha256": _hash_file(milestone_result)},
        {"role": "phase_state_validator", "path": "reviews/exemplar/phase_validation.json", "sha256": _hash_file(phase_result)},
    ]
    if exemplar_class == "clean_lifecycle_exemplar":
        rendered = subprocess.run(
            [sys.executable, str(LIFECYCLE_RENDERER), "--project-root", str(project), "--generated-at", "2026-07-14T00:00:00Z"],
            capture_output=True, text=True, check=False,
        )
        assert rendered.returncode == 0, rendered.stderr
        for role, name, content in (
            ("release_gate", "release_gate.txt", "status: PASS\n"),
            ("independent_replay", "independent_replay.txt", "status: PASS\n"),
        ):
            path = evidence_dir / name
            path.write_text(content, encoding="utf-8")
            evidence.append({"role": role, "path": f"reviews/exemplar/{name}", "sha256": _hash_file(path)})
        lifecycle = project / "reviews" / "lifecycle_state.md"
        evidence.append({"role": "lifecycle_view", "path": "reviews/lifecycle_state.md", "sha256": _hash_file(lifecycle)})
    else:
        boundary = json.loads((project / "reviews" / "phase_state.json").read_text(encoding="utf-8"))["milestone_framework"]["migration_boundary"]
        phase_sha = _hash_file(project / "reviews" / "phase_state.json")
        manifest_relative = "reviews/exemplar/rollback_manifest.json"
        manifest = project / manifest_relative
        manifest.write_text(json.dumps({"manifest_version": "1.0.0", "replacement_path": "reviews/phase_state.json", "replacement_sha256": phase_sha, "report_sha256": boundary["report_sha256"]}) + "\n", encoding="utf-8")
        commit_relative = "reviews/exemplar/migration_commit.json"
        commit = project / commit_relative
        commit.write_text(json.dumps({"transaction_state": "committed", "replacement_sha256": phase_sha, "report_sha256": boundary["report_sha256"], "manifest_sha256": _hash_file(manifest)}) + "\n", encoding="utf-8")
        rollback_relative = "reviews/exemplar/rollback_verification.txt"
        rollback = project / rollback_relative
        rollback.write_text("status: PASS\n", encoding="utf-8")
        evidence.extend([
            {"role": "migration_commit", "path": commit_relative, "sha256": _hash_file(commit)},
            {"role": "migration_manifest", "path": manifest_relative, "sha256": _hash_file(manifest)},
            {"role": "rollback_verification", "path": rollback_relative, "sha256": _hash_file(rollback)},
        ])
        evidence.extend([
            {"role": "migration_report", "path": boundary["report_path"], "sha256": boundary["report_sha256"]},
            {"role": "migration_approval", "path": boundary["evidence_path"], "sha256": boundary["evidence_sha256"]},
        ])
    phase_state = project / "reviews" / "phase_state.json"
    entry = {
        "project_path": project.resolve().as_posix(),
        "exemplar_class": exemplar_class,
        "approval_authority": "user",
        "approval_evidence_path": "reviews/exemplar/approval.md",
        "approval_evidence_sha256": _hash_file(approval),
        "validator_version": PLUGIN_VERSION,
        "validator_outcome": "READY" if exemplar_class == "clean_lifecycle_exemplar" else "LEGACY_READY",
        "validator_evidence": evidence,
        "registered_at": "2026-07-14T00:01:00Z",
        "phase_state_sha256": _hash_file(phase_state),
    }
    entries = [entry, copy.deepcopy(entry)] if duplicate else [entry]
    registry.write_text(json.dumps({"schema_version": "1.0.0", "entries": entries}, indent=2) + "\n", encoding="utf-8")


def _rebind_legacy_registry(project: Path, registry: Path) -> None:
    """Rehash a complete legacy chain so semantic rejection cannot hide behind stale hashes."""
    phase_path = project / "reviews" / "phase_state.json"
    document = json.loads(phase_path.read_text(encoding="utf-8"))
    boundary = document["milestone_framework"]["migration_boundary"]
    boundary["report_sha256"] = _hash_file(project / boundary["report_path"])
    boundary["evidence_sha256"] = _hash_file(project / boundary["evidence_path"])
    phase_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    phase_sha = _hash_file(phase_path)
    manifest = project / "reviews" / "exemplar" / "rollback_manifest.json"
    manifest.write_text(json.dumps({"manifest_version": "1.0.0", "replacement_path": "reviews/phase_state.json", "replacement_sha256": phase_sha, "report_sha256": boundary["report_sha256"]}) + "\n", encoding="utf-8")
    commit = project / "reviews" / "exemplar" / "migration_commit.json"
    commit.write_text(json.dumps({"transaction_state": "committed", "replacement_sha256": phase_sha, "report_sha256": boundary["report_sha256"], "manifest_sha256": _hash_file(manifest)}) + "\n", encoding="utf-8")
    payload = json.loads(registry.read_text(encoding="utf-8"))
    entry = payload["entries"][0]
    entry["phase_state_sha256"] = phase_sha
    role_paths = {item["role"]: item for item in entry["validator_evidence"]}
    for role in ("migration_report", "migration_approval", "migration_manifest", "migration_commit"):
        item = role_paths[role]
        item["sha256"] = _hash_file(project / item["path"])
    registry.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _run_exemplar_cases(directory: Path, failures: list[str]) -> None:
    def run(name: str, project: Path, registry: Path, expected_exit: int, expected_code: str | None = None) -> dict[str, Any]:
        actual_exit, payload, stderr = _run_real_validator(project, None, registry)
        codes = {row.get("code") for row in payload.get("findings", [])}
        print(f"exemplar/{name}: expected={expected_exit}/{expected_code or '-'} actual={actual_exit}/{sorted(code for code in codes if code)}")
        if actual_exit != expected_exit or (expected_code and expected_code not in codes):
            failures.append(f"exemplar/{name} expected {expected_exit}/{expected_code}, got {actual_exit}/{codes}; stderr={stderr!r}")
        if "Traceback" in stderr:
            failures.append(f"exemplar/{name} emitted a traceback")
        return payload

    ordinary = directory / "exemplar-ordinary"
    ordinary.mkdir(); _write_real_case("valid_native_chain", ordinary)
    (ordinary / "research_notes" / "ordinary_usage.md").write_text("This method is a useful reference implementation.\n", encoding="utf-8")
    (ordinary / "reviews" / "ordinary_review.md").write_text("The cited article is a portfolio exemplar.\n", encoding="utf-8")
    empty = directory / "empty-exemplar-registry.json"
    empty.write_text('{"schema_version":"1.0.0","entries":[]}\n', encoding="utf-8")
    run("absent_claim_without_registration", ordinary, empty, 0)

    phase_path = ordinary / "reviews" / "phase_state.json"
    phase_document = json.loads(phase_path.read_text(encoding="utf-8"))
    original_purpose = phase_document["milestone_framework"]["milestones"]["M1"]["purpose"]
    phase_document["milestone_framework"]["milestones"]["M1"]["purpose"] = "reference implementation"
    phase_path.write_text(json.dumps(phase_document, indent=2) + "\n", encoding="utf-8")
    run("ledger_analytical_scalar", ordinary, empty, 0)
    phase_document["milestone_framework"]["milestones"]["M1"]["purpose"] = original_purpose
    phase_path.write_text(json.dumps(phase_document, indent=2) + "\n", encoding="utf-8")

    identity_project = directory / "INF3130"
    identity_project.mkdir(); _write_real_case("valid_native_chain", identity_project)
    declaration_surface = identity_project / "CLAUDE.md"
    positive_claims = (
        "INF3130 is a reference implementation.",
        "This project has been designated as a clean lifecycle exemplar.",
        "This project serves as the reference implementation.",
        "**Status:** portfolio exemplar",
        "| **Status:** | portfolio exemplar |",
        "The project remains the legacy migration exemplar.",
    )
    for index, claim in enumerate(positive_claims):
        declaration_surface.write_text(f"# Project\n\n{claim}\n", encoding="utf-8")
        run(f"claim_evasion_{index}", identity_project, empty, 4, "MF-EXEMPLAR")
    for index, claim in enumerate((
        "inf3130 is a clean lifecycle exemplar.",
        "SMOKE-PROJECT remains the reference implementation.",
    )):
        declaration_surface.write_text(f"# Project\n\n{claim}\n", encoding="utf-8")
        run(f"claim_identity_alias_{index}", identity_project, empty, 4, "MF-EXEMPLAR")
    negative_mentions = (
        "This project is not a portfolio exemplar.",
        "Is INF3130 a reference implementation?",
        "The review asks whether this project serves as the reference implementation.",
        "The phrase `portfolio exemplar` is an analytical category here.",
        "We do not claim that this project is a portfolio exemplar.",
        "The validator is a reference implementation.",
        "This method is the portfolio exemplar.",
    )
    for index, mention in enumerate(negative_mentions):
        declaration_surface.write_text(f"# Project\n\n{mention}\n", encoding="utf-8")
        run(f"claim_false_positive_{index}", identity_project, empty, 0)
    declaration_surface.unlink()

    (ordinary / "AGENTS.md").write_text("# Reference implementation\n", encoding="utf-8")
    run("agents_self_declaration", ordinary, empty, 4, "MF-EXEMPLAR")
    (ordinary / "AGENTS.md").unlink()
    (ordinary / "reviews" / "lifecycle_state.md").write_text("status: clean_lifecycle_exemplar\n", encoding="utf-8")
    run("lifecycle_self_declaration", ordinary, empty, 4, "MF-EXEMPLAR")
    (ordinary / "reviews" / "lifecycle_state.md").unlink()
    phase_document = json.loads(phase_path.read_text(encoding="utf-8"))
    phase_document["milestone_framework"]["exemplar_status"] = "portfolio exemplar"
    phase_path.write_text(json.dumps(phase_document, indent=2) + "\n", encoding="utf-8")
    run("ledger_self_declaration", ordinary, empty, 4, "MF-EXEMPLAR")
    del phase_document["milestone_framework"]["exemplar_status"]
    phase_path.write_text(json.dumps(phase_document, indent=2) + "\n", encoding="utf-8")

    claimed = directory / "exemplar-inf-shaped-claim"
    claimed.mkdir(); _write_real_case("valid_native_chain", claimed)
    (claimed / "CLAUDE.md").write_text("# Project status\n\nThis project is the portfolio exemplar.\n", encoding="utf-8")
    run("inf_prose_self_declaration", claimed, empty, 4, "MF-EXEMPLAR")

    clean = directory / "exemplar-clean"
    clean.mkdir(); _write_real_case("valid_native_chain", clean)
    clean_registry = directory / "clean-registry.json"
    _write_exemplar_registry(clean, clean_registry, "clean_lifecycle_exemplar")
    run("clean_registered", clean, clean_registry, 0)
    extra = clean / "reviews" / "exemplar" / "unknown.txt"
    extra.write_text("status: PASS\n", encoding="utf-8")
    extra_registry = directory / "extra-role-registry.json"
    extra_payload = json.loads(clean_registry.read_text(encoding="utf-8"))
    extra_payload["entries"][0]["validator_evidence"].append({"role": "unknown_but_hash_valid", "path": "reviews/exemplar/unknown.txt", "sha256": _hash_file(extra)})
    extra_registry.write_text(json.dumps(extra_payload, indent=2) + "\n", encoding="utf-8")
    run("unknown_evidence_role", clean, extra_registry, 4, "MF-EXEMPLAR")
    lifecycle = clean / "reviews" / "lifecycle_state.md"
    lifecycle_original = lifecycle.read_bytes()
    lifecycle.write_bytes(lifecycle_original + b"\nThis project is the portfolio exemplar.\n")
    edited_payload = run("edited_generated_self_claim", clean, clean_registry, 4, "MF-EXEMPLAR")
    if "MF-DERIVED" not in {row.get("code") for row in edited_payload.get("findings", [])}:
        failures.append("exemplar/edited_generated_self_claim missing exact-byte MF-DERIVED finding")
    lifecycle.write_bytes(lifecycle_original)
    (clean / "reviews" / "exemplar" / "release_gate.txt").write_text("status: FAIL\n", encoding="utf-8")
    run("stale_evidence_hash", clean, clean_registry, 4, "MF-EXEMPLAR")
    (clean / "reviews" / "exemplar" / "release_gate.txt").write_text("status: PASS\n", encoding="utf-8")
    (clean / "reviews" / "phase_state.json").write_text(
        (clean / "reviews" / "phase_state.json").read_text(encoding="utf-8") + " ", encoding="utf-8"
    )
    run("stale_ledger_hash", clean, clean_registry, 4, "MF-EXEMPLAR")

    legacy = directory / "exemplar-legacy"
    legacy.mkdir(); _write_real_case("valid_approved_legacy_migration", legacy)
    legacy_registry = directory / "legacy-registry.json"
    _write_exemplar_registry(legacy, legacy_registry, "legacy_migration_exemplar")
    run("legacy_registered", legacy, legacy_registry, 0)
    separate_registry = directory / "legacy-separate-authorities-registry.json"
    separate_payload = json.loads(legacy_registry.read_text(encoding="utf-8"))
    separate_approval = legacy / "reviews" / "exemplar" / "approval-advisor.md"
    separate_approval.write_text("status: APPROVED\nauthority: advisor\n", encoding="utf-8")
    separate_entry = separate_payload["entries"][0]
    separate_entry["approval_authority"] = "advisor"
    separate_entry["approval_evidence_path"] = "reviews/exemplar/approval-advisor.md"
    separate_entry["approval_evidence_sha256"] = _hash_file(separate_approval)
    separate_registry.write_text(json.dumps(separate_payload, indent=2) + "\n", encoding="utf-8")
    run("legacy_separate_allowed_authorities", legacy, separate_registry, 0)
    rejected_report = legacy / "reviews" / "migration_report.md"
    rejected_report.write_text('{"adjudication_outcome":"rejected","authority":"nobody"}\n', encoding="utf-8")
    _rebind_legacy_registry(legacy, legacy_registry)
    run("legacy_rejected_report_rehashed", legacy, legacy_registry, 4, "MF-EXEMPLAR")

    legacy_approval = directory / "exemplar-legacy-approval"
    legacy_approval.mkdir(); _write_real_case("valid_approved_legacy_migration", legacy_approval)
    legacy_approval_registry = directory / "legacy-approval-registry.json"
    _write_exemplar_registry(legacy_approval, legacy_approval_registry, "legacy_migration_exemplar")
    (legacy_approval / "reviews" / "migration_approval.md").write_text("status: REJECTED\nauthority: nobody\n", encoding="utf-8")
    _rebind_legacy_registry(legacy_approval, legacy_approval_registry)
    run("legacy_rejected_approval_rehashed", legacy_approval, legacy_approval_registry, 4, "MF-EXEMPLAR")

    legacy_nobody = directory / "exemplar-legacy-nobody-authority"
    legacy_nobody.mkdir(); _write_real_case("valid_approved_legacy_migration", legacy_nobody)
    legacy_nobody_registry = directory / "legacy-nobody-registry.json"
    _write_exemplar_registry(legacy_nobody, legacy_nobody_registry, "legacy_migration_exemplar")
    nobody_phase_path = legacy_nobody / "reviews" / "phase_state.json"
    nobody_document = json.loads(nobody_phase_path.read_text(encoding="utf-8"))
    nobody_document["milestone_framework"]["migration_boundary"]["authority"] = "nobody"
    nobody_phase_path.write_text(json.dumps(nobody_document, indent=2) + "\n", encoding="utf-8")
    (legacy_nobody / "reviews" / "migration_report.md").write_text('{"adjudication_outcome":"approved","authority":"nobody"}\n', encoding="utf-8")
    (legacy_nobody / "reviews" / "migration_approval.md").write_text("status: APPROVED\nauthority: nobody\n", encoding="utf-8")
    _rebind_legacy_registry(legacy_nobody, legacy_nobody_registry)
    run("legacy_nobody_authority_rehashed", legacy_nobody, legacy_nobody_registry, 4, "MF-EXEMPLAR")

    duplicate = directory / "exemplar-duplicate"
    duplicate.mkdir(); _write_real_case("valid_native_chain", duplicate)
    duplicate_registry = directory / "duplicate-registry.json"
    _write_exemplar_registry(duplicate, duplicate_registry, "clean_lifecycle_exemplar", duplicate=True)
    run("duplicate_registration", duplicate, duplicate_registry, 4, "MF-EXEMPLAR")
    conflict_payload = json.loads(duplicate_registry.read_text(encoding="utf-8"))
    conflict_payload["entries"][1]["exemplar_class"] = "legacy_migration_exemplar"
    conflict_payload["entries"][1]["validator_outcome"] = "LEGACY_READY"
    duplicate_registry.write_text(json.dumps(conflict_payload, indent=2) + "\n", encoding="utf-8")
    run("conflicting_registration", duplicate, duplicate_registry, 4, "MF-EXEMPLAR")

    malformed = directory / "malformed-registry.json"
    malformed.write_text('{"schema_version":"1.0.0","entries":"wrong"}\n', encoding="utf-8")
    run("malformed_registry", ordinary, malformed, 4, "MF-EXEMPLAR")

    spec = importlib.util.spec_from_file_location("milestone_framework_validate_exemplar_race_test", VALIDATOR)
    assert spec is not None and spec.loader is not None
    validator_module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = validator_module
    spec.loader.exec_module(validator_module)

    race_project = directory / "exemplar-race"
    race_project.mkdir(); _write_real_case("valid_native_chain", race_project)
    race_registry = directory / "race-registry.json"
    _write_exemplar_registry(race_project, race_registry, "clean_lifecycle_exemplar")
    race_document = json.loads((race_project / "reviews" / "phase_state.json").read_text(encoding="utf-8"))
    fired = False
    def registry_swap(stage: str, role: str, path: Path) -> None:
        nonlocal fired
        if not fired and stage == "after_path_check" and role == "registry":
            replacement = path.with_suffix(".replacement")
            replacement.write_text('{"schema_version":"1.0.0","entries":[]}\n', encoding="utf-8")
            os.replace(replacement, path); fired = True
    try:
        raced = validator_module.validate_document(race_project, race_document, exemplar_registry_path=race_registry, _exemplar_snapshot_hook=registry_swap)
        if "MF-EXEMPLAR" not in {row.code for row in raced.findings}:
            failures.append("exemplar/registry_after_check_swap was not rejected")
    except Exception as exc:
        failures.append(f"exemplar/registry_after_check_swap escaped controlled validation: {exc!r}")

    read_project = directory / "exemplar-during-read-race"
    read_project.mkdir(); _write_real_case("valid_native_chain", read_project)
    read_registry = directory / "during-read-registry.json"
    _write_exemplar_registry(read_project, read_registry, "clean_lifecycle_exemplar")
    read_document = json.loads((read_project / "reviews" / "phase_state.json").read_text(encoding="utf-8"))
    fired = False
    def evidence_swap(stage: str, role: str, path: Path) -> None:
        nonlocal fired
        if not fired and stage == "during_read" and role == "release_gate":
            replacement = path.with_suffix(".replacement")
            replacement.write_text("status: FAIL\n", encoding="utf-8")
            os.replace(replacement, path); fired = True
    try:
        raced = validator_module.validate_document(read_project, read_document, exemplar_registry_path=read_registry, _exemplar_snapshot_hook=evidence_swap)
        if "MF-EXEMPLAR" not in {row.code for row in raced.findings}:
            failures.append("exemplar/evidence_during_read_swap was not rejected")
    except Exception as exc:
        failures.append(f"exemplar/evidence_during_read_swap escaped controlled validation: {exc!r}")


def _write_sk20_project(project: Path, claude_fields: dict[str, str], directive_fields: dict[str, str] | None = None, *, graph: bool = True) -> None:
    project.mkdir()
    (project / "reviews").mkdir()
    (project / "manuscript").mkdir()
    (project / "references").mkdir()
    (project / "research_notes").mkdir()
    wiki = project / "wiki"
    (wiki / "graphify-out").mkdir(parents=True)

    def table(fields: dict[str, str]) -> str:
        rows = ["| Field | Value |", "|---|---|"]
        rows.extend(f"| `{key}` | `{value}` |" for key, value in fields.items())
        return "\n".join(rows) + "\n"

    (project / "CLAUDE.md").write_text("# Project\n\n" + table(claude_fields), encoding="utf-8")
    directives = "# Directives\n\n"
    if directive_fields is not None:
        directives += "## SK-20 applicability override\n\n" + table(directive_fields)
    (project / "research_notes" / "directives.md").write_text(directives, encoding="utf-8")
    (project / "reviews" / "classification.md").write_text("# Classification\n", encoding="utf-8")
    (project / "manuscript" / "main.md").write_text(
        "Last updated: 2026-07-13\n\nA grounded claim (Smith 2026).\n", encoding="utf-8"
    )
    (project / "references" / "REFERENCES.md").write_text("Last updated: 2026-07-13\n", encoding="utf-8")
    if graph:
        payload = {
            "nodes": [{"id": "n1", "captured_at": "2026-07-13T12:00:00Z"}],
            "links": [],
        }
        (wiki / "graphify-out" / "graph.json").write_text(json.dumps(payload), encoding="utf-8")
        (wiki / "graphify-out" / "GRAPH_REPORT.md").write_text("# Graph report\n", encoding="utf-8")


def _run_sk20_gate_cases(directory: Path, failures: list[str]) -> None:
    base = {
        "wiki_linked": "true",
        "wiki_path": "wiki",
        "coupling_e_on_review": "true",
    }
    na = {
        "coupling_e_on_review": "false",
        "sk20_not_applicable_authority": "user",
        "sk20_not_applicable_reason": "The user excluded graph overlay for this project.",
        "sk20_not_applicable_scope": "Coupling E.2 / SK-20",
        "sk20_not_applicable_substitute_evidence": "research_notes/directives.md",
    }
    cases: list[tuple[str, dict[str, str], dict[str, str] | None, bool, str, int, list[str]]] = [
        ("enabled_ready", base, None, True, "READY", 0, []),
        ("claude_authorized_disabled", {**base, **na, "sk20_not_applicable_substitute_evidence": "CLAUDE.md"}, None, False, "NOT_APPLICABLE", 0, []),
        ("directive_authorized_disabled", base, na, False, "NOT_APPLICABLE", 0, []),
        ("directive_partial_cannot_inherit_claude_authorization", {**base, **na, "sk20_not_applicable_substitute_evidence": "CLAUDE.md"}, {"coupling_e_on_review": "false"}, False, "MISCONFIGURED", 4, []),
        ("cli_complete_authorized_disabled", base, None, False, "NOT_APPLICABLE", 0, ["--coupling-e-on-review", "false", "--sk20-not-applicable-authority", "user", "--sk20-not-applicable-reason", "CLI user decision.", "--sk20-not-applicable-scope", "SK-20", "--sk20-not-applicable-substitute-evidence", "CLAUDE.md"]),
        ("cli_partial_cannot_inherit_file_authorization", {**base, **na, "sk20_not_applicable_substitute_evidence": "CLAUDE.md"}, None, False, "MISCONFIGURED", 4, ["--coupling-e-on-review", "false"]),
        ("silent_absence", {"wiki_path": "wiki"}, None, True, "MISCONFIGURED", 4, []),
        ("false_like_string", {**base, "coupling_e_on_review": "off"}, None, True, "MISCONFIGURED", 4, []),
        ("contradictory_flags", {**base, "wiki_linked": "false", "coupling_e_on_review": "true", **{key: value for key, value in na.items() if key != "coupling_e_on_review"}}, None, False, "MISCONFIGURED", 4, []),
        ("disabled_missing_reason", {**base, **{key: value for key, value in na.items() if key != "sk20_not_applicable_reason"}}, None, False, "MISCONFIGURED", 4, []),
        ("disabled_invalid_authority", {**base, **na, "sk20_not_applicable_authority": "generator"}, None, False, "MISCONFIGURED", 4, []),
        ("disabled_unrelated_scope", {**base, **na, "sk20_not_applicable_scope": "citation formatting"}, None, False, "MISCONFIGURED", 4, []),
        ("disabled_outside_evidence", {**base, **na, "sk20_not_applicable_substitute_evidence": "../outside.md"}, None, False, "MISCONFIGURED", 4, []),
        ("enabled_missing_wiki_resources", base, None, False, "MISCONFIGURED", 4, []),
        ("disabled_missing_wiki_resources", {**base, **na, "sk20_not_applicable_substitute_evidence": "CLAUDE.md"}, None, False, "NOT_APPLICABLE", 0, []),
    ]
    for name, claude_fields, directive_fields, graph, expected_outcome, expected_exit, extra_args in cases:
        project = directory / f"sk20-{name}"
        _write_sk20_project(project, claude_fields, directive_fields, graph=graph)
        result = subprocess.run(
            [sys.executable, "-I", "-S", str(SK20_GATE), "--project-root", str(project), "--date", "2026-07-13", "--strict-exit", *extra_args],
            capture_output=True, text=True, check=False,
        )
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            payload = {}
        actual_outcome = payload.get("outcome")
        print(f"sk20/{name}: expected={expected_outcome}/{expected_exit} actual={actual_outcome}/{result.returncode}")
        if result.returncode != expected_exit or actual_outcome != expected_outcome:
            failures.append(
                f"sk20/{name} expected {expected_outcome}/{expected_exit}, got "
                f"{actual_outcome}/{result.returncode}; stderr={result.stderr.strip()!r}"
            )
        if "Traceback" in result.stderr:
            failures.append(f"sk20/{name} emitted a traceback")
        readiness_path = project / "reviews" / "coupling_readiness_2026-07-13.json"
        if not readiness_path.is_file():
            failures.append(f"sk20/{name} did not write readiness evidence")
        else:
            readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
            if readiness.get("outcome") != expected_outcome:
                failures.append(f"sk20/{name} readiness evidence outcome is not truthful")
            if expected_outcome == "NOT_APPLICABLE":
                expected_source = "CLI" if name.startswith("cli_") else (
                    "research_notes/directives.md" if name.startswith("directive_") else "project CLAUDE.md"
                )
                if readiness.get("metadata", {}).get("authorization_source") != expected_source:
                    failures.append(f"sk20/{name} did not record exact authorization source {expected_source}")
        noop_path = project / "reviews" / "sk20_noop_2026-07-13.json"
        if expected_outcome == "READY" and noop_path.exists():
            failures.append(f"sk20/{name} retained a no-op artifact for READY")
        if expected_outcome != "READY":
            if not noop_path.is_file():
                failures.append(f"sk20/{name} did not write no-op evidence")
            else:
                noop = json.loads(noop_path.read_text(encoding="utf-8"))
                if noop.get("outcome") != expected_outcome or noop.get("status") != "noop":
                    failures.append(f"sk20/{name} no-op evidence does not preserve outcome")

    for label, invalid_value in (("invalid_calendar_date", "2026-02-30"), ("invalid_date_shape", "2026-7-13")):
        invalid_date_project = directory / f"sk20-{label}"
        _write_sk20_project(invalid_date_project, base)
        invalid_date = subprocess.run(
            [sys.executable, "-I", "-S", str(SK20_GATE), "--project-root", str(invalid_date_project), "--date", invalid_value, "--strict-exit"],
            capture_output=True, text=True, check=False,
        )
        print(f"sk20/{label}: expected=1 actual={invalid_date.returncode}")
        if invalid_date.returncode != 1 or list((invalid_date_project / "reviews").glob(f"*{invalid_value}*")):
            failures.append(f"sk20/{label} must exit 1 and write nothing")
        if "Traceback" in invalid_date.stderr:
            failures.append(f"sk20/{label} emitted a traceback")

    file_root = directory / "sk20-file-root"
    file_root.write_text("not a directory", encoding="utf-8")
    file_root_result = subprocess.run(
        [sys.executable, "-I", "-S", str(SK20_GATE), "--project-root", str(file_root), "--date", "2026-07-13", "--strict-exit"],
        capture_output=True, text=True, check=False,
    )
    print(f"sk20/file_root: expected=2 actual={file_root_result.returncode}")
    if file_root_result.returncode != 2 or "Traceback" in file_root_result.stderr:
        failures.append("sk20/file_root must be a controlled I/O failure")

    missing_root_result = subprocess.run(
        [sys.executable, "-I", "-S", str(SK20_GATE), "--project-root", str(directory / "missing-root"), "--date", "2026-07-13", "--strict-exit"],
        capture_output=True, text=True, check=False,
    )
    print(f"sk20/missing_root: expected=2 actual={missing_root_result.returncode}")
    if missing_root_result.returncode != 2 or "Traceback" in missing_root_result.stderr:
        failures.append("sk20/missing_root must be a controlled I/O failure")

    malformed_project = directory / "sk20-malformed-config"
    _write_sk20_project(malformed_project, base)
    (malformed_project / "CLAUDE.md").write_bytes(b"\xff\xfe\x00")
    malformed = subprocess.run(
        [sys.executable, "-I", "-S", str(SK20_GATE), "--project-root", str(malformed_project), "--date", "2026-07-13", "--strict-exit"],
        capture_output=True, text=True, check=False,
    )
    print(f"sk20/malformed_config: expected=2 actual={malformed.returncode}")
    if malformed.returncode != 2 or "Traceback" in malformed.stderr:
        failures.append("sk20/malformed_config must be a controlled parse failure")

    atomic_project = directory / "sk20-atomic-preservation"
    _write_sk20_project(atomic_project, base, graph=False)
    readiness = atomic_project / "reviews" / "coupling_readiness_2026-07-13.json"
    readiness.write_text("SENTINEL", encoding="utf-8")
    (atomic_project / "reviews" / "sk20_noop_2026-07-13.json").mkdir()
    atomic = subprocess.run(
        [sys.executable, "-I", "-S", str(SK20_GATE), "--project-root", str(atomic_project), "--date", "2026-07-13", "--strict-exit"],
        capture_output=True, text=True, check=False,
    )
    print(f"sk20/atomic_preservation: expected=2 actual={atomic.returncode}")
    if atomic.returncode != 2 or readiness.read_text(encoding="utf-8") != "SENTINEL" or "Traceback" in atomic.stderr:
        failures.append("sk20/atomic_preservation must preserve prior evidence on output failure")

    if os.name == "nt":
        junction_project = directory / "sk20-reviews-junction"
        _write_sk20_project(junction_project, base)
        outside_reviews = directory / "outside-reviews"
        outside_reviews.mkdir()
        shutil.rmtree(junction_project / "reviews")
        link = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(junction_project / "reviews"), str(outside_reviews)],
            capture_output=True, text=True, check=False,
        )
        if link.returncode == 0:
            junction = subprocess.run(
                [sys.executable, "-I", "-S", str(SK20_GATE), "--project-root", str(junction_project), "--date", "2026-07-13", "--strict-exit"],
                capture_output=True, text=True, check=False,
            )
            print(f"sk20/reviews_junction: expected=2 actual={junction.returncode}")
            if junction.returncode != 2 or any(outside_reviews.iterdir()) or "Traceback" in junction.stderr:
                failures.append("sk20/reviews_junction must refuse without outside writes")

        evidence_project = directory / "sk20-evidence-junction"
        evidence_fields = {**base, **na, "sk20_not_applicable_substitute_evidence": "evidence/decision.md"}
        _write_sk20_project(evidence_project, evidence_fields, graph=False)
        outside_evidence = directory / "outside-evidence"
        outside_evidence.mkdir()
        (outside_evidence / "decision.md").write_text("# Decision\n", encoding="utf-8")
        evidence_link = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(evidence_project / "evidence"), str(outside_evidence)],
            capture_output=True, text=True, check=False,
        )
        if evidence_link.returncode == 0:
            evidence_result = subprocess.run(
                [sys.executable, "-I", "-S", str(SK20_GATE), "--project-root", str(evidence_project), "--date", "2026-07-13", "--strict-exit"],
                capture_output=True, text=True, check=False,
            )
            try:
                evidence_payload = json.loads(evidence_result.stdout)
            except json.JSONDecodeError:
                evidence_payload = {}
            print(f"sk20/evidence_junction: expected=MISCONFIGURED/4 actual={evidence_payload.get('outcome')}/{evidence_result.returncode}")
            if evidence_result.returncode != 4 or evidence_payload.get("outcome") != "MISCONFIGURED" or "Traceback" in evidence_result.stderr:
                failures.append("sk20/evidence_junction must be a controlled semantic refusal")

        output_project = directory / "sk20-output-symlink"
        output_fields = {**base, **na, "sk20_not_applicable_substitute_evidence": "CLAUDE.md"}
        _write_sk20_project(output_project, output_fields, graph=False)
        outside_output = directory / "outside-noop.json"
        outside_output.write_text("OUTSIDE-SENTINEL", encoding="utf-8")
        output_link = subprocess.run(
            ["cmd", "/c", "mklink", str(output_project / "reviews" / "sk20_noop_2026-07-13.json"), str(outside_output)],
            capture_output=True, text=True, check=False,
        )
        if output_link.returncode == 0:
            output_result = subprocess.run(
                [sys.executable, "-I", "-S", str(SK20_GATE), "--project-root", str(output_project), "--date", "2026-07-13", "--strict-exit"],
                capture_output=True, text=True, check=False,
            )
            print(f"sk20/output_symlink: expected=2 actual={output_result.returncode}")
            if output_result.returncode != 2 or outside_output.read_text(encoding="utf-8") != "OUTSIDE-SENTINEL" or "Traceback" in output_result.stderr:
                failures.append("sk20/output_symlink must refuse without outside mutation")

        internal_evidence_project = directory / "sk20-internal-evidence-junction"
        internal_evidence_fields = {**base, **na, "sk20_not_applicable_substitute_evidence": "evidence-alias/decision.md"}
        _write_sk20_project(internal_evidence_project, internal_evidence_fields, graph=False)
        internal_evidence = internal_evidence_project / "internal-evidence"
        internal_evidence.mkdir()
        (internal_evidence / "decision.md").write_text("# Internal decision\n", encoding="utf-8")
        internal_link = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(internal_evidence_project / "evidence-alias"), str(internal_evidence)],
            capture_output=True, text=True, check=False,
        )
        if internal_link.returncode == 0:
            internal_result = subprocess.run(
                [sys.executable, "-I", "-S", str(SK20_GATE), "--project-root", str(internal_evidence_project), "--date", "2026-07-13", "--strict-exit"],
                capture_output=True, text=True, check=False,
            )
            try:
                internal_payload = json.loads(internal_result.stdout)
            except json.JSONDecodeError:
                internal_payload = {}
            print(f"sk20/internal_evidence_junction: expected=MISCONFIGURED/4 actual={internal_payload.get('outcome')}/{internal_result.returncode}")
            if internal_result.returncode != 4 or internal_payload.get("outcome") != "MISCONFIGURED":
                failures.append("sk20/internal_evidence_junction must reject a raw-path reparse alias")

    external_project = directory / "sk20-absolute-external-inputs"
    _write_sk20_project(external_project, base)
    external_inputs = directory / "external-read-inputs"
    external_inputs.mkdir()
    external_manuscript = external_inputs / "manuscript.md"
    external_references = external_inputs / "REFERENCES.md"
    external_classification = external_inputs / "classification.md"
    external_manuscript.write_text("Last updated: 2026-07-13\n\nExternal grounded claim (Smith 2026).\n", encoding="utf-8")
    external_references.write_text("Last updated: 2026-07-13\n", encoding="utf-8")
    external_classification.write_text("# External classification\n", encoding="utf-8")
    external_before = {path: path.read_bytes() for path in external_inputs.iterdir()}
    external_result = subprocess.run(
        [
            sys.executable, "-I", "-S", str(SK20_GATE), "--project-root", str(external_project),
            "--date", "2026-07-13", "--strict-exit",
            "--manuscript-path", str(external_manuscript),
            "--references-path", str(external_references),
            "--classification-path", str(external_classification),
        ],
        capture_output=True, text=True, check=False,
    )
    try:
        external_payload = json.loads(external_result.stdout)
    except json.JSONDecodeError:
        external_payload = {}
    print(f"sk20/absolute_external_inputs: expected=READY/0 actual={external_payload.get('outcome')}/{external_result.returncode}")
    external_after = {path: path.read_bytes() for path in external_inputs.iterdir()}
    if external_result.returncode != 0 or external_payload.get("outcome") != "READY" or external_after != external_before:
        failures.append("sk20/absolute_external_inputs must remain compatible and read-only")

    spec = importlib.util.spec_from_file_location("sk20_preflight_gate_transaction_test", SK20_GATE)
    if spec is None or spec.loader is None:
        failures.append("sk20/backup_cleanup_injection could not load gate module")
    else:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        transaction_project = directory / "sk20-backup-cleanup-injection"
        transaction_project.mkdir()
        transaction_reviews = transaction_project / "reviews"
        transaction_reviews.mkdir()
        readiness_target = transaction_reviews / "coupling_readiness_2026-07-13.json"
        noop_target = transaction_reviews / "sk20_noop_2026-07-13.json"
        readiness_target.write_text('{"old":"readiness"}\n', encoding="utf-8")
        noop_target.write_text('{"old":"noop"}\n', encoding="utf-8")
        cleanup_count = 0

        def injected_cleanup(path: Path) -> None:
            nonlocal cleanup_count
            cleanup_count += 1
            if cleanup_count == 2:
                raise PermissionError("injected second-backup cleanup refusal")
            path.unlink()

        try:
            warnings = module._commit_outputs(
                transaction_project,
                {readiness_target: {"new": "readiness"}, noop_target: {"new": "noop"}},
                [],
                remove_backup=injected_cleanup,
            )
            transaction_ok = (
                json.loads(readiness_target.read_text(encoding="utf-8"))["new"] == "readiness"
                and json.loads(noop_target.read_text(encoding="utf-8"))["new"] == "noop"
                and bool(warnings)
            )
            module._commit_outputs(
                transaction_project,
                {readiness_target: {"next": "readiness"}, noop_target: {"next": "noop"}},
                [],
            )
            transaction_ok = transaction_ok and not list(transaction_reviews.glob(".*.bak"))
        except Exception as exc:
            transaction_ok = (
                cleanup_count >= 2
                and
                readiness_target.read_text(encoding="utf-8") == '{"old":"readiness"}\n'
                and noop_target.read_text(encoding="utf-8") == '{"old":"noop"}\n'
            )
            if not transaction_ok:
                failures.append(f"sk20/backup_cleanup_injection returned error plus partial loss: {exc}")
        print(f"sk20/backup_cleanup_injection: coherent={transaction_ok}")
        if not transaction_ok:
            failures.append("sk20/backup_cleanup_injection must produce complete new or exact old state")


def main() -> int:
    required_files = (MILESTONE_SCHEMA, F9_SCHEMA, F9_TEMPLATE, EVENT_TEMPLATE)
    missing = [str(path.relative_to(ROOT)) for path in required_files if not path.is_file()]
    if missing:
        print("MISCONFIGURED: missing Task 2 schema/template files: " + ", ".join(missing))
        return 4
    if EXEMPLAR_REGISTRY.read_bytes() != b'{"schema_version":"1.0.0","entries":[]}\n':
        print("MISCONFIGURED: milestone exemplar registry seed bytes are not exact")
        return 4

    milestone_schema = json.loads(MILESTONE_SCHEMA.read_text(encoding="utf-8"))
    f9_schema = json.loads(F9_SCHEMA.read_text(encoding="utf-8"))
    f9_template = json.loads(F9_TEMPLATE.read_text(encoding="utf-8"))
    _validate(f9_template, f9_schema, f9_schema)
    event_template = json.loads(EVENT_TEMPLATE.read_text(encoding="utf-8"))
    _validate(event_template, milestone_schema["$defs"]["milestone_event"], milestone_schema)

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

        for name, (expected_outcome, expected_exit, target, expected_code) in REAL_CASES.items():
            project = directory / f"real-{name}"
            _assert_synthetic_fixture(project, directory)
            project.mkdir()
            _write_real_case(name, project)
            if name.startswith("re_"):
                _assert_re_chain_contract(project)
            fixture_document = json.loads((project / "reviews/phase_state.json").read_text(encoding="utf-8"))
            if name == "re_m5_manuscript_changed":
                m5 = fixture_document["milestone_framework"]["milestones"]["M5"]
                current_hash = hashlib.sha256((project / m5["artifacts"][0]["path"]).read_bytes()).hexdigest()
                assert m5["approval"]["status"] == "approved"
                assert m5["artifacts"][0]["sha256"] != current_hash
            elif name == "re_m2_reopened_blocks_m5":
                fixture_ledger = fixture_document["milestone_framework"]
                assert fixture_ledger["milestones"]["M2"]["status"] == "reopened"
                assert fixture_ledger["milestones"]["M5"]["dependency_state"] == "current"
                assert not any(event["event_type"] == "downstream_revalidated" for event in fixture_ledger["events"])
            elif name == "inf_unlocked_ph3_sibling_blocks_ph4":
                sibling = fixture_document["sections"]["milestone5_v2_coauthor_layperson"]
                assert sibling["current_phase"] == "Ph3"
                assert sibling["last_approved_phase"] == "Ph2"
                assert sibling["ceiling_locked"] is False
                assert sibling["applicable_ceiling"] == "Ph4"
            actual_exit, payload, stderr = _run_real_validator(project, target)
            codes = {finding.get("code") for finding in payload.get("findings", [])}
            named_findings = [
                finding for finding in payload.get("findings", []) if isinstance(finding, dict)
            ]
            if name == "re_m5_manuscript_changed":
                assert any(
                    finding.get("code") == "MF-BINDING"
                    and finding.get("path") == "milestone_framework.milestones.M5.artifacts[0].path"
                    and "current" in finding.get("message", "")
                    for finding in named_findings
                )
            elif name == "re_m2_reopened_blocks_m5":
                assert fixture_document["milestone_framework"]["milestones"]["M5"]["handoff"]["status"] == "ready"
                assert any(
                    finding.get("code") == "MF-REOPEN"
                    and finding.get("path") == "milestone_framework.milestones.M5.dependency_state"
                    and "upstream M2 reopened" in finding.get("message", "")
                    for finding in named_findings
                )
            elif name == "inf_unlocked_ph3_sibling_blocks_ph4":
                assert any(
                    finding.get("code") == "MF-PHASE"
                    and finding.get("path") == "sections['milestone5_v2_coauthor_layperson'].current_phase"
                    and "non-ceiling-locked" in finding.get("message", "")
                    for finding in named_findings
                )
            actual_outcome = payload.get("outcome")
            print(
                f"real/{name}: expected={expected_outcome}/{expected_exit} "
                f"actual={actual_outcome}/{actual_exit} codes={sorted(code for code in codes if code)}"
            )
            if actual_exit != expected_exit or actual_outcome != expected_outcome:
                failures.append(
                    f"real/{name} expected {expected_outcome}/{expected_exit}, "
                    f"got {actual_outcome}/{actual_exit}; stderr={stderr.strip()!r}"
                )
            if expected_code and expected_code not in codes:
                failures.append(f"real/{name} missing expected finding {expected_code}")
            if name == "missing_project_local_override":
                messages = [finding.get("message", "") for finding in payload.get("findings", [])]
                if not any("authority-appropriate" in message for message in messages):
                    failures.append(
                        "real/missing_project_local_override diagnostic must describe authority-appropriate resolution"
                    )
            if "Traceback" in stderr:
                failures.append(f"real/{name} emitted a traceback")

        _run_exemplar_cases(directory, failures)

        integration_project = directory / "phase-integration"
        integration_project.mkdir()
        _write_real_case("valid_native_chain", integration_project)
        integration = subprocess.run(
            [sys.executable, str(PHASE_VALIDATOR), "--project-root", str(integration_project), "--json"],
            capture_output=True, text=True, check=False,
        )
        print(f"phase_state_integration: expected=0 actual={integration.returncode}")
        if integration.returncode != 0:
            failures.append(
                f"phase_state integration expected 0, got {integration.returncode}: "
                f"{integration.stdout.strip()} {integration.stderr.strip()}"
            )

        invalid_integration_project = directory / "phase-integration-invalid"
        invalid_integration_project.mkdir()
        _write_real_case("stale_deliverable_hash", invalid_integration_project)
        invalid_integration = subprocess.run(
            [sys.executable, str(PHASE_VALIDATOR), "--project-root", str(invalid_integration_project), "--json"],
            capture_output=True, text=True, check=False,
        )
        try:
            invalid_findings = json.loads(invalid_integration.stdout)
        except json.JSONDecodeError:
            invalid_findings = []
        invalid_codes = {finding.get("code") for finding in invalid_findings if isinstance(finding, dict)}
        print(
            f"phase_state_invalid_namespace: expected=4/MF-BINDING "
            f"actual={invalid_integration.returncode}/{sorted(code for code in invalid_codes if code)}"
        )
        if invalid_integration.returncode != 4 or "MF-BINDING" not in invalid_codes:
            failures.append(
                "phase_state invalid namespace did not reuse milestone semantic validation: "
                f"exit={invalid_integration.returncode}, codes={sorted(code for code in invalid_codes if code)}"
            )

        usage = subprocess.run(
            [sys.executable, str(VALIDATOR), "--project-root", str(integration_project), "--target", "M6"],
            capture_output=True, text=True, check=False,
        )
        print(f"cli_usage_error: expected=1 actual={usage.returncode}")
        if usage.returncode != 1:
            failures.append(f"CLI usage error expected 1, got {usage.returncode}")

        parse_project = directory / "parse-failure"
        (parse_project / "reviews").mkdir(parents=True)
        (parse_project / "reviews" / "phase_state.json").write_text("{\n", encoding="utf-8")
        parse_failure = subprocess.run(
            [sys.executable, str(VALIDATOR), "--project-root", str(parse_project)],
            capture_output=True, text=True, check=False,
        )
        print(f"json_parse_error: expected=2 actual={parse_failure.returncode}")
        if parse_failure.returncode != 2:
            failures.append(f"JSON parse error expected 2, got {parse_failure.returncode}")

        for isolated_script in (VALIDATOR, PHASE_VALIDATOR):
            isolated = subprocess.run(
                [sys.executable, "-I", "-S", str(isolated_script), "--project-root", str(integration_project), "--json"],
                capture_output=True, text=True, check=False,
            )
            print(f"stdlib_isolation/{isolated_script.name}: expected=0 actual={isolated.returncode}")
            if isolated.returncode != 0 or "ModuleNotFoundError" in isolated.stderr:
                failures.append(
                    f"stdlib isolation failed for {isolated_script.name}: "
                    f"exit={isolated.returncode}, stderr={isolated.stderr.strip()!r}"
                )

        _run_sk20_gate_cases(directory, failures)

    if failures:
        print("FAIL: " + "; ".join(failures))
        return 1
    print("OK milestone_framework_smoketest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
