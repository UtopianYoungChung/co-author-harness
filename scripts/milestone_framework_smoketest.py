#!/usr/bin/env python3
"""Smoke-test the milestone-framework and F9 JSON Schema contracts.

Task 3 owns the production semantic validator.  This test intentionally uses a
small standard-library JSON Schema evaluator for only the keywords exercised by
the two real schemas created in Task 2.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MILESTONE_SCHEMA = ROOT / "references" / "schemas" / "milestone_framework.schema.json"
F9_SCHEMA = ROOT / "references" / "schemas" / "f9_milestone_handoff.schema.json"
F9_TEMPLATE = ROOT / "references" / "templates" / "f9_milestone_handoff.json"
VALIDATOR = ROOT / "scripts" / "milestone_framework_validate.py"
PHASE_VALIDATOR = ROOT / "scripts" / "phase_state_validate.py"

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
}

REAL_CASES = {
    "valid_native_chain": ("READY", 0, None, None),
    "valid_ph2_target": ("READY", 0, "Ph2", None),
    "valid_ph4_target": ("READY", 0, "Ph4", None),
    "valid_ph4_before_closure": ("READY", 0, "Ph4", None),
    "valid_ph4_ceiling_locked": ("READY", 0, "Ph4", None),
    "valid_approved_legacy_migration": ("LEGACY_READY", 0, None, None),
    "authorized_not_applicable": ("NOT_APPLICABLE", 0, "M4", None),
    "absent_namespace": ("MISCONFIGURED", 4, None, "MF-STRUCTURE"),
    "missing_purpose_real": ("MISCONFIGURED", 4, None, "MF-STRUCTURE"),
    "m4_plan_only_real": ("MISCONFIGURED", 4, "M4", "MF-ROLE"),
    "m5_checklist_only_real": ("MISCONFIGURED", 4, "M5", "MF-ROLE"),
    "missing_feedback_provenance_real": ("MISCONFIGURED", 4, None, "MF-FEEDBACK"),
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
    "rejected_generator_override": ("MISCONFIGURED", 4, "M4", "MF-OVERRIDE"),
    "allowed_advisor_override": ("NOT_APPLICABLE", 0, "M4", None),
    "reordered_artifacts_feedback_lineage": ("READY", 0, None, None),
    "active_multi_lineage": ("MISCONFIGURED", 4, None, "MF-LINEAGE"),
    "superseded_multi_lineage": ("READY", 0, None, None),
    "ph4_without_mcr_admission": ("MISCONFIGURED", 4, "Ph4", "MF-PHASE"),
    "ph4_retracted_mcr_admission": ("MISCONFIGURED", 4, "Ph4", "MF-PHASE"),
    "export_source_mismatch": ("MISCONFIGURED", 4, None, "MF-EXPORT"),
    "terminal_f9_export_mismatch": ("MISCONFIGURED", 4, None, "MF-EXPORT"),
    "list_shaped_sections": ("MISCONFIGURED", 4, None, "MF-STRUCTURE"),
    "list_shaped_milestones": ("MISCONFIGURED", 4, None, "MF-STRUCTURE"),
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
        "rule": "references/MILESTONE_FEEDBACK_HANDOFF_PROTOCOL.md#3-authority-and-precedence",
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
    incomplete["authorized_override"] = _override(["M3"], ["M3_to_M4"])
    del incomplete["authorized_override"]["rule"]

    cases["not_applicable_status_without_override"]["milestones"]["M3"]["status"] = "not_applicable"
    cases["export_without_source_binding"]["milestones"]["M5"]["artifacts"].append({
        **_artifact("M5"),
        "role": "export",
        "artifact_kind": "released_manuscript_export",
    })
    return cases


def _write_bound_file(project: Path, relative: str, content: str) -> tuple[str, int]:
    path = project / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = content.encode("utf-8")
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest(), len(payload)


def _phase_document(ledger: dict[str, Any], current_phase: str = "Ph4") -> dict[str, Any]:
    if current_phase == "Ph4":
        previous_phase = "Ph3_converged"
        trigger = "mcr_admission"
    else:
        previous_phase = "Ph1"
        trigger = "user_approval"
    return {
        "schema_version": "0.7.4",
        "terminal_phase_reached": True,
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
        _write_bound_file(project, record["approval"]["evidence_path"], f"{milestone} approved\n")

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
    return ledger


def _rewrite_packet(project: Path, ledger: dict[str, Any], milestone: str, mutate: Any) -> None:
    handoff = ledger["milestones"][milestone]["handoff"]
    packet_path = project / handoff["packet_path"]
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    mutate(packet)
    payload = (json.dumps(packet, indent=2) + "\n").encode("utf-8")
    packet_path.write_bytes(payload)
    handoff["packet_sha256"] = hashlib.sha256(payload).hexdigest()


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


def _write_real_case(case: str, project: Path) -> None:
    ledger = _materialize_native_project(project)
    milestones = ledger["milestones"]

    document_phase = "Ph4"
    if case == "valid_ph2_target":
        document_phase = "Ph2"
        milestones["M4"]["status"] = "in_progress"
        milestones["M4"]["approval"] = {"status": "pending", "authority": None, "evidence_path": None, "approved_at": None}
        milestones["M4"]["handoff"] = {"status": "not_ready", "packet_path": None, "packet_sha256": None}
        _reset_milestone(milestones["M5"])
    elif case == "valid_approved_legacy_migration":
        evidence_hash, _ = _write_bound_file(project, "reviews/migration_approval.md", "migration approved\n")
        report_hash, _ = _write_bound_file(project, "reviews/migration_report.md", "migration report\n")
        ledger["mode"] = "legacy"
        ledger["migration_boundary"] = {
            "authority": "user",
            "evidence_path": "reviews/migration_approval.md",
            "evidence_sha256": evidence_hash,
            "approved_at": "2026-07-13T18:00:00Z",
            "completed_through": "M5",
            "report_path": "reviews/migration_report.md",
            "report_sha256": report_hash,
        }
    elif case in {"authorized_not_applicable", "allowed_advisor_override", "rejected_generator_override"}:
        target = milestones["M4"]
        target.update({
            "status": "not_applicable", "applicability": "not_applicable",
            "artifacts": [], "feedback_records": [],
            "approval": {"status": "not_applicable", "authority": None, "evidence_path": None, "approved_at": None},
            "handoff": {"status": "not_applicable", "packet_path": None, "packet_sha256": None},
            "dependency_state": "not_applicable",
            "authorized_override": _override(["M4"], ["M4_to_M5"]),
        })
        _write_bound_file(project, target["authorized_override"]["substitute_evidence"], "authorized N/A\n")
        if case == "allowed_advisor_override":
            target["authorized_override"]["authority"] = "advisor"
        elif case == "rejected_generator_override":
            target["authorized_override"]["authority"] = "generator"
        milestones["M5"].update({
            "status": "not_started", "artifacts": [], "feedback_records": [],
            "approval": {"status": "pending", "authority": None, "evidence_path": None, "approved_at": None},
            "handoff": {"status": "not_ready", "packet_path": None, "packet_sha256": None},
        })
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
    elif case == "stale_deliverable_hash":
        (project / milestones["M3"]["artifacts"][0]["path"]).write_text("drifted bytes\n", encoding="utf-8")
    elif case == "stale_f9_packet_hash":
        (project / milestones["M3"]["handoff"]["packet_path"]).write_text("{}\n", encoding="utf-8")
    elif case == "reopened_upstream_current_downstream":
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
    elif case == "reordered_artifacts_feedback_lineage":
        evidence_hash, evidence_bytes = _write_bound_file(project, "reviews/reordered_evidence.md", "supporting evidence\n")
        milestones["M3"]["artifacts"].insert(0, {
            "role": "evidence", "artifact_kind": "review",
            "path": "reviews/reordered_evidence.md", "sha256": evidence_hash, "bytes": evidence_bytes,
            "verified_at": "2026-07-13T18:00:00Z", "lineage_id": "alternate",
        })
    elif case in {"active_multi_lineage", "superseded_multi_lineage"}:
        record = milestones["M3"]
        alternate = copy.deepcopy(record["artifacts"][0])
        alternate["lineage_id"] = "alternate"
        alternate["path"] = "research_notes/m3_alternate.md"
        alternate["sha256"], alternate["bytes"] = _write_bound_file(project, alternate["path"], "alternate M3\n")
        record["artifacts"].append(alternate)
        record["status"] = "in_progress" if case == "active_multi_lineage" else "superseded"
        record["approval"] = {"status": "pending", "authority": None, "evidence_path": None, "approved_at": None}
        record["handoff"] = {"status": "not_ready", "packet_path": None, "packet_sha256": None}
        _reset_milestone(milestones["M4"])
        _reset_milestone(milestones["M5"])
    elif case == "ph4_without_mcr_admission":
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

    document: Any = _phase_document(ledger, document_phase)
    if case == "absent_namespace":
        del document["milestone_framework"]
    elif case == "list_shaped_sections":
        document["sections"] = []
    elif case == "ph4_without_mcr_admission":
        document["sections"]["1. Test"]["phase_entry_log"][0]["trigger"] = "user_approval"
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
    reviews = project / "reviews"
    reviews.mkdir(parents=True, exist_ok=True)
    (reviews / "phase_state.json").write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def _run_real_validator(project: Path, target: str | None) -> tuple[int, dict[str, Any], str]:
    command = [sys.executable, str(VALIDATOR), "--project-root", str(project), "--json"]
    if target:
        command.extend(["--target", target])
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        payload = {}
    return result.returncode, payload, result.stderr


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

        for name, (expected_outcome, expected_exit, target, expected_code) in REAL_CASES.items():
            project = directory / f"real-{name}"
            project.mkdir()
            _write_real_case(name, project)
            actual_exit, payload, stderr = _run_real_validator(project, target)
            codes = {finding.get("code") for finding in payload.get("findings", [])}
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
            if "Traceback" in stderr:
                failures.append(f"real/{name} emitted a traceback")

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

    if failures:
        print("FAIL: " + "; ".join(failures))
        return 1
    print("OK milestone_framework_smoketest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
