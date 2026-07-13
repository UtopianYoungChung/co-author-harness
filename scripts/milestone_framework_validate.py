#!/usr/bin/env python3
"""Validate milestone feedback, bindings, lineage, and F9 handoffs.

The validator is read-only.  Its ``validate_document`` function is the shared
integration surface used by ``phase_state_validate.py`` so milestone semantics
remain in one implementation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MILESTONE_SCHEMA_PATH = ROOT / "references" / "schemas" / "milestone_framework.schema.json"
F9_SCHEMA_PATH = ROOT / "references" / "schemas" / "f9_milestone_handoff.schema.json"
MILESTONES = ("M1", "M2", "M3", "M4", "M5")
TARGETS = (*MILESTONES, "Ph2", "Ph4")
OVERRIDE_AUTHORITIES = frozenset({
    "user", "venue", "advisor", "instructor", "committee", "project_local_contract"
})
ACTIVE_MILESTONE_STATUSES = frozenset({
    "in_progress", "feedback_pending", "revision_required", "accepted", "reopened"
})


class Outcome(str, Enum):
    READY = "READY"
    LEGACY_READY = "LEGACY_READY"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    MISCONFIGURED = "MISCONFIGURED"


class UsageArgumentParser(argparse.ArgumentParser):
    """Argparse variant matching the harness-wide usage exit contract."""

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(1, f"{self.prog}: error: {message}\n")


class Severity(str, Enum):
    MAJOR = "MAJOR"
    BLOCKER = "BLOCKER"


class SchemaViolation(ValueError):
    """One deterministic violation from the bounded Draft 2020-12 evaluator."""

    def __init__(self, path: list[Any], message: str) -> None:
        super().__init__(message)
        self.path = path
        self.message = message


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    path: str
    message: str

    def json_value(self) -> dict[str, str]:
        value = asdict(self)
        value["severity"] = self.severity.value
        return value


@dataclass(frozen=True)
class ValidationResult:
    outcome: Outcome
    exit_permitted: bool
    target: str | None
    findings: tuple[Finding, ...]
    evidence_bindings: tuple[dict[str, Any], ...]

    def json_value(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome.value,
            "exit_permitted": self.exit_permitted,
            "target": self.target,
            "findings": [finding.json_value() for finding in self.findings],
            "evidence_bindings": list(self.evidence_bindings),
        }


def _finding(code: str, path: str, message: str, severity: Severity = Severity.BLOCKER) -> Finding:
    return Finding(code=code, severity=severity, path=path, message=message)


def _schema_code(path: list[Any], message: str) -> str:
    tokens = {str(token) for token in path}
    if "authorized_override" in tokens or "migration_boundary" in tokens:
        return "MF-OVERRIDE"
    if "feedback_records" in tokens:
        return "MF-FEEDBACK"
    if "primary_lineage" in tokens or "lineage_id" in tokens:
        return "MF-LINEAGE"
    if "approval" in tokens or "handoff" in tokens:
        return "MF-HANDOFF"
    if tokens.intersection({"M4", "M5"}) and "artifacts" in tokens and "manuscript" in message:
        return "MF-ROLE"
    return "MF-STRUCTURE"


def _json_path(prefix: str, path: list[Any]) -> str:
    suffix = "".join(f"[{token}]" if isinstance(token, int) else f".{token}" for token in path)
    return prefix + suffix


def _schema_type(value: Any, expected: str) -> bool:
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


def _schema_ref(root: dict[str, Any], reference: str) -> dict[str, Any]:
    if not reference.startswith("#/"):
        raise RuntimeError(f"only local schema references are supported: {reference}")
    value: Any = root
    for token in reference[2:].split("/"):
        value = value[token.replace("~1", "/").replace("~0", "~")]
    return value


def _schema_accepts(instance: Any, schema: dict[str, Any], root: dict[str, Any], path: list[Any]) -> bool:
    try:
        _validate_schema(instance, schema, root, path)
    except SchemaViolation:
        return False
    return True


def _validate_schema(
    instance: Any,
    schema: dict[str, Any],
    root: dict[str, Any],
    path: list[Any] | None = None,
) -> None:
    """Evaluate only the Draft 2020-12 keywords used by the Task 2 schemas."""
    path = [] if path is None else path
    if "$ref" in schema:
        _validate_schema(instance, _schema_ref(root, schema["$ref"]), root, path)
        return
    for subschema in schema.get("allOf", []):
        _validate_schema(instance, subschema, root, path)
    if "anyOf" in schema and not any(
        _schema_accepts(instance, option, root, path) for option in schema["anyOf"]
    ):
        raise SchemaViolation(path, "did not satisfy anyOf")
    if "oneOf" in schema:
        matches = sum(
            _schema_accepts(instance, option, root, path) for option in schema["oneOf"]
        )
        if matches != 1:
            raise SchemaViolation(path, f"expected exactly one oneOf match, got {matches}")
    if "if" in schema:
        branch = "then" if _schema_accepts(instance, schema["if"], root, path) else "else"
        if branch in schema:
            _validate_schema(instance, schema[branch], root, path)

    expected = schema.get("type")
    if expected is not None:
        allowed = [expected] if isinstance(expected, str) else expected
        if not any(_schema_type(instance, item) for item in allowed):
            raise SchemaViolation(path, f"expected type {allowed}, got {type(instance).__name__}")
    if "const" in schema and instance != schema["const"]:
        raise SchemaViolation(path, f"expected constant {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        raise SchemaViolation(path, f"{instance!r} is outside enum")

    if isinstance(instance, dict):
        missing = [key for key in schema.get("required", []) if key not in instance]
        if missing:
            raise SchemaViolation(path, f"missing required properties {missing}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extra = sorted(set(instance) - set(properties))
            if extra:
                raise SchemaViolation(path, f"additional properties forbidden: {extra}")
        for key, subschema in properties.items():
            if key in instance:
                _validate_schema(instance[key], subschema, root, [*path, key])

    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            raise SchemaViolation(path, "too few items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            raise SchemaViolation(path, "too many items")
        if schema.get("uniqueItems") and len({json.dumps(value, sort_keys=True) for value in instance}) != len(instance):
            raise SchemaViolation(path, "items must be unique")
        if "items" in schema:
            for index, value in enumerate(instance):
                _validate_schema(value, schema["items"], root, [*path, index])
        if "contains" in schema:
            matches = sum(
                _schema_accepts(value, schema["contains"], root, [*path, index])
                for index, value in enumerate(instance)
            )
            if matches < schema.get("minContains", 1):
                raise SchemaViolation(path, "contains matched too few items")
            if "maxContains" in schema and matches > schema["maxContains"]:
                raise SchemaViolation(path, "contains matched too many items")

    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            raise SchemaViolation(path, "string is too short")
        if "pattern" in schema and re.fullmatch(schema["pattern"], instance) is None:
            raise SchemaViolation(path, f"string does not match {schema['pattern']!r}")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            raise SchemaViolation(path, "value is below minimum")


def _schema_findings(instance: Any, schema: dict[str, Any], prefix: str) -> list[Finding]:
    try:
        _validate_schema(instance, schema, schema)
    except SchemaViolation as error:
        return [_finding(_schema_code(error.path, error.message), _json_path(prefix, error.path), error.message)]
    return []


def _load_schema(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_path(project_root: Path, relative: Any) -> Path | None:
    if not isinstance(relative, str) or not relative.strip():
        return None
    candidate = (project_root / relative).resolve()
    try:
        candidate.relative_to(project_root.resolve())
    except ValueError:
        return None
    return candidate


def _override_rule_resolves(rule: Any) -> bool:
    if not isinstance(rule, str) or "#" not in rule:
        return False
    relative, anchor = rule.split("#", 1)
    if not relative.startswith("references/") or not anchor:
        return False
    source = (ROOT / relative).resolve()
    try:
        source.relative_to((ROOT / "references").resolve())
        text = source.read_text(encoding="utf-8")
    except (ValueError, OSError, UnicodeError):
        return False
    anchors = set()
    for line in text.splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
        if not match:
            continue
        slug = re.sub(r"[^a-z0-9\s-]", "", match.group(1).lower())
        anchors.add(re.sub(r"[\s-]+", "-", slug).strip("-"))
    return anchor in anchors


def _file_binding(
    project_root: Path,
    relative: Any,
    expected_sha: Any,
    expected_bytes: Any | None,
    path: str,
    findings: list[Finding],
    evidence: list[dict[str, Any]],
    code: str = "MF-BINDING",
) -> bytes | None:
    candidate = _canonical_path(project_root, relative)
    if candidate is None:
        findings.append(_finding("MF-CANON", path, "path must be non-empty and remain inside the project root"))
        return None
    if not candidate.is_file():
        findings.append(_finding("MF-CANON", path, f"canonical path does not exist: {relative!r}"))
        return None
    try:
        payload = candidate.read_bytes()
    except OSError as exc:
        findings.append(_finding(code, path, f"could not read bound file: {exc}"))
        return None
    actual_sha = hashlib.sha256(payload).hexdigest()
    mismatch: list[str] = []
    if expected_sha != actual_sha:
        mismatch.append(f"sha256 expected {expected_sha!r}, current {actual_sha!r}")
    if expected_bytes is not None and expected_bytes != len(payload):
        mismatch.append(f"bytes expected {expected_bytes!r}, current {len(payload)}")
    if mismatch:
        findings.append(_finding(code, path, "; ".join(mismatch)))
    else:
        evidence.append({"path": str(relative), "sha256": actual_sha, "bytes": len(payload)})
    return payload


def _validate_feedback(
    project_root: Path,
    milestone: str,
    record: dict[str, Any],
    primary_lineage: Any,
    findings: list[Finding],
    evidence: list[dict[str, Any]],
) -> None:
    feedback_records = record.get("feedback_records")
    if not isinstance(feedback_records, list):
        return
    for index, feedback in enumerate(feedback_records):
        path = f"milestone_framework.milestones.{milestone}.feedback_records[{index}]"
        if not isinstance(feedback, dict):
            continue
        _file_binding(
            project_root, feedback.get("source_path"), feedback.get("source_sha256"), None,
            f"{path}.source_path", findings, evidence, "MF-FEEDBACK",
        )
        artifacts = record.get("artifacts")
        primary_deliverable = next((
            artifact for artifact in artifacts
            if isinstance(artifact, dict)
            and artifact.get("role") == "deliverable"
            and artifact.get("lineage_id") == primary_lineage
        ), None) if isinstance(artifacts, list) else None
        if primary_deliverable is not None and feedback.get("lineage_id") != primary_deliverable.get("lineage_id"):
            findings.append(_finding("MF-LINEAGE", f"{path}.lineage_id", "feedback lineage does not match the milestone deliverable lineage"))
        if feedback.get("blocking") is True and feedback.get("disposition") in {None, "pending"}:
            findings.append(_finding("MF-FEEDBACK", f"{path}.disposition", "blocking feedback must be adjudicated before handoff"))


def _validate_artifacts(
    project_root: Path,
    milestone: str,
    record: dict[str, Any],
    primary_lineage: Any,
    findings: list[Finding],
    evidence: list[dict[str, Any]],
) -> dict[str, Any] | None:
    artifacts = record.get("artifacts")
    if not isinstance(artifacts, list):
        return None
    deliverables = [item for item in artifacts if isinstance(item, dict) and item.get("role") == "deliverable"]
    primary = [item for item in deliverables if item.get("lineage_id") == primary_lineage]
    active_lineages = {
        item.get("lineage_id") for item in deliverables
        if isinstance(item.get("lineage_id"), str) and item.get("lineage_id")
    }
    if record.get("status") in ACTIVE_MILESTONE_STATUSES and len(active_lineages) > 1:
        findings.append(_finding(
            "MF-LINEAGE", f"milestone_framework.milestones.{milestone}.artifacts",
            "active milestone has concurrently current deliverables on distinct lineages",
        ))
    if record.get("status") == "accepted" and len(primary) != 1:
        findings.append(_finding("MF-LINEAGE", f"milestone_framework.milestones.{milestone}.artifacts", "accepted milestone must have exactly one deliverable on the primary lineage"))
    deliverable = primary[0] if primary else (deliverables[0] if deliverables else None)
    if milestone in {"M4", "M5"} and record.get("status") == "accepted":
        if deliverable is None or deliverable.get("artifact_kind") != "manuscript":
            findings.append(_finding("MF-ROLE", f"milestone_framework.milestones.{milestone}.artifacts", f"{milestone} primary deliverable must be a manuscript artifact"))
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            continue
        artifact_path = f"milestone_framework.milestones.{milestone}.artifacts[{index}]"
        if artifact.get("lineage_id") != primary_lineage and artifact.get("role") == "deliverable" and record.get("status") == "accepted":
            findings.append(_finding("MF-LINEAGE", f"{artifact_path}.lineage_id", "accepted deliverable is outside the declared primary lineage"))
        if record.get("status") == "accepted":
            payload = _file_binding(
                project_root, artifact.get("path"), artifact.get("sha256"), artifact.get("bytes"),
                f"{artifact_path}.path", findings, evidence,
            )
            if payload is not None and artifact.get("role") == "derived_view":
                view = payload.decode("utf-8", errors="replace").lower()
                required_claims = ("do not edit", "derived_from", "source_sha256")
                if any(claim not in view for claim in required_claims):
                    findings.append(_finding(
                        "MF-DERIVED", f"{artifact_path}.path",
                        "derived view must carry a do-not-edit marker, derived_from, and source_sha256 binding",
                        Severity.MAJOR,
                    ))
            if payload is not None and "status" in str(artifact.get("artifact_kind", "")).lower() and artifact.get("role") != "derived_view":
                status_text = payload.decode("utf-8", errors="replace").lower()
                if "authoritative lifecycle status" in status_text or "source of truth" in status_text:
                    findings.append(_finding(
                        "MF-STATUS", f"{artifact_path}.path",
                        "manual status document claims lifecycle-state authority",
                        Severity.MAJOR,
                    ))
    return deliverable


def _validate_packet(
    project_root: Path,
    milestone: str,
    record: dict[str, Any],
    deliverable: dict[str, Any] | None,
    primary_lineage: Any,
    predecessor: dict[str, str] | None,
    f9_schema: dict[str, Any],
    findings: list[Finding],
    evidence: list[dict[str, Any]],
) -> dict[str, str] | None:
    handoff = record.get("handoff")
    if not isinstance(handoff, dict) or handoff.get("status") not in {"ready", "consumed"}:
        return None
    base = f"milestone_framework.milestones.{milestone}.handoff"
    approval = record.get("approval")
    if not isinstance(approval, dict) or approval.get("status") != "approved":
        findings.append(_finding("MF-HANDOFF", base, "ready or consumed handoff requires approved milestone evidence"))
    payload = _file_binding(
        project_root, handoff.get("packet_path"), handoff.get("packet_sha256"), None,
        f"{base}.packet_path", findings, evidence,
    )
    if payload is None:
        return None
    try:
        packet = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        findings.append(_finding("MF-HANDOFF", f"{base}.packet_path", f"F9 packet is not valid UTF-8 JSON: {exc}"))
        return None
    findings.extend(_schema_findings(packet, f9_schema, f"{base}.packet"))
    if not isinstance(packet, dict):
        return None
    if packet.get("lineage_id") != primary_lineage:
        findings.append(_finding("MF-LINEAGE", f"{base}.packet.lineage_id", "F9 packet lineage does not match primary lineage"))
    if packet.get("predecessor_packet") != predecessor:
        findings.append(_finding("MF-HANDOFF", f"{base}.packet.predecessor_packet", "F9 predecessor binding does not match the prior packet"))
    if deliverable is not None:
        packet_deliverable = packet.get("deliverable")
        expected = {key: deliverable.get(key) for key in ("role", "path", "sha256", "bytes")}
        if packet_deliverable != expected:
            findings.append(_finding("MF-BINDING", f"{base}.packet.deliverable", "F9 deliverable binding does not match the ledger deliverable"))
    if milestone == "M5":
        artifacts = record.get("artifacts")
        ledger_export = next((
            artifact for artifact in artifacts
            if isinstance(artifact, dict)
            and artifact.get("role") == "export"
            and artifact.get("lineage_id") == primary_lineage
        ), None) if isinstance(artifacts, list) else None
        expected_export = {
            key: ledger_export.get(key)
            for key in ("role", "path", "sha256", "bytes", "source_sha256")
        } if isinstance(ledger_export, dict) else None
        if isinstance(expected_export, dict) and ledger_export.get("source_path") is not None:
            expected_export["source_path"] = ledger_export["source_path"]
        if packet.get("released_export") != expected_export:
            findings.append(_finding(
                "MF-EXPORT", f"{base}.packet.released_export",
                "terminal F9 released-export binding must match the canonical M5 export record",
            ))
    ledger_approval = record.get("approval")
    packet_approval = packet.get("approval")
    if isinstance(ledger_approval, dict) and isinstance(packet_approval, dict):
        ledger_identity = {
            key: ledger_approval.get(key)
            for key in ("authority", "evidence_path", "approved_at")
        }
        if packet_approval != ledger_identity:
            findings.append(_finding(
                "MF-HANDOFF", f"{base}.packet.approval",
                "F9 approval authority, evidence path, and time must exactly match milestone approval state",
            ))
    return {"path": handoff.get("packet_path"), "sha256": handoff.get("packet_sha256")}


def validate_document(project_root: Path, document: Any, target: str | None = None) -> ValidationResult:
    """Validate the additive namespace in an already-parsed phase document."""
    findings: list[Finding] = []
    evidence: list[dict[str, Any]] = []
    if not isinstance(document, dict):
        findings.append(_finding("MF-STRUCTURE", "$", "phase state must be a JSON object"))
        return _result(target, None, findings, evidence)
    if "sections" in document and not isinstance(document["sections"], dict):
        findings.append(_finding("MF-STRUCTURE", "sections", "sections must be a JSON object"))
    if "milestone_framework" not in document:
        findings.append(_finding("MF-STRUCTURE", "milestone_framework", "required milestone_framework namespace is absent"))
        return _result(target, None, findings, evidence)
    ledger = document.get("milestone_framework")
    milestone_schema = _load_schema(MILESTONE_SCHEMA_PATH)
    f9_schema = _load_schema(F9_SCHEMA_PATH)
    findings.extend(_schema_findings(ledger, milestone_schema, "milestone_framework"))
    if not isinstance(ledger, dict):
        return _result(target, None, findings, evidence)
    milestones = ledger.get("milestones")
    if not isinstance(milestones, dict):
        return _result(target, ledger, findings, evidence)

    primary_lineage = ledger.get("primary_lineage")
    predecessor: dict[str, str] | None = None
    deliverables: dict[str, dict[str, Any] | None] = {}
    for index, milestone in enumerate(MILESTONES):
        record = milestones.get(milestone)
        if not isinstance(record, dict):
            continue
        deliverable = _validate_artifacts(project_root, milestone, record, primary_lineage, findings, evidence)
        deliverables[milestone] = deliverable
        _validate_feedback(project_root, milestone, record, primary_lineage, findings, evidence)
        approval = record.get("approval")
        if (
            isinstance(approval, dict)
            and approval.get("status") == "approved"
            and approval.get("authority") not in OVERRIDE_AUTHORITIES
        ):
            findings.append(_finding(
                "MF-HANDOFF", f"milestone_framework.milestones.{milestone}.approval.authority",
                f"approval authority must be one of {sorted(OVERRIDE_AUTHORITIES)}",
            ))
        if isinstance(approval, dict) and approval.get("evidence_path"):
            approval_path = approval["evidence_path"]
            candidate = _canonical_path(project_root, approval_path)
            if candidate is None or not candidate.is_file():
                findings.append(_finding("MF-HANDOFF", f"milestone_framework.milestones.{milestone}.approval.evidence_path", "approval evidence path must exist inside the project"))
        packet = _validate_packet(
            project_root, milestone, record, deliverable, primary_lineage, predecessor,
            f9_schema, findings, evidence,
        )
        if packet is not None:
            predecessor = packet

        if index > 0 and record.get("status") not in {"not_started", "not_applicable"}:
            previous = milestones.get(MILESTONES[index - 1], {})
            previous_approval = previous.get("approval") if isinstance(previous, dict) else None
            previous_handoff = previous.get("handoff") if isinstance(previous, dict) else None
            if not isinstance(previous_approval, dict) or previous_approval.get("status") != "approved" or not isinstance(previous_handoff, dict) or previous_handoff.get("status") != "consumed":
                findings.append(_finding("MF-HANDOFF", f"milestone_framework.milestones.{milestone}", "successor work started before predecessor approval and consumed handoff"))

    for index, milestone in enumerate(MILESTONES[:-1]):
        record = milestones.get(milestone)
        if not isinstance(record, dict):
            continue
        approval = record.get("approval")
        reopened = record.get("status") == "reopened" or (isinstance(approval, dict) and approval.get("status") == "reopened")
        if reopened:
            for downstream in MILESTONES[index + 1:]:
                dependent = milestones.get(downstream)
                if isinstance(dependent, dict) and dependent.get("status") not in {"not_started", "not_applicable"} and dependent.get("dependency_state") == "current":
                    findings.append(_finding("MF-REOPEN", f"milestone_framework.milestones.{downstream}.dependency_state", f"{downstream} remains current after upstream {milestone} reopened"))

    if ledger.get("mode") == "legacy" and isinstance(ledger.get("migration_boundary"), dict):
        boundary = ledger["migration_boundary"]
        for label, sha_label in (("evidence_path", "evidence_sha256"), ("report_path", "report_sha256")):
            _file_binding(
                project_root, boundary.get(label), boundary.get(sha_label), None,
                f"milestone_framework.migration_boundary.{label}", findings, evidence, "MF-OVERRIDE",
            )

    for milestone, record in milestones.items():
        if not isinstance(record, dict) or record.get("applicability") != "not_applicable":
            continue
        override = record.get("authorized_override")
        if not isinstance(override, dict):
            findings.append(_finding("MF-OVERRIDE", f"milestone_framework.milestones.{milestone}.authorized_override", "not-applicable state requires a complete authorized override"))
            continue
        if override.get("authority") not in OVERRIDE_AUTHORITIES:
            findings.append(_finding(
                "MF-OVERRIDE", f"milestone_framework.milestones.{milestone}.authorized_override.authority",
                f"override authority must be one of {sorted(OVERRIDE_AUTHORITIES)}",
            ))
        if not _override_rule_resolves(override.get("rule")):
            findings.append(_finding(
                "MF-OVERRIDE", f"milestone_framework.milestones.{milestone}.authorized_override.rule",
                "override rule must resolve to a named heading anchor in a package reference",
            ))
        substitute = override.get("substitute_evidence")
        candidate = _canonical_path(project_root, substitute)
        if candidate is None or not candidate.is_file():
            findings.append(_finding("MF-OVERRIDE", f"milestone_framework.milestones.{milestone}.authorized_override.substitute_evidence", "substitute evidence must exist inside the project"))

    m5 = milestones.get("M5")
    if isinstance(m5, dict) and m5.get("status") == "accepted":
        artifacts = m5.get("artifacts")
        exports = [item for item in artifacts if isinstance(item, dict) and item.get("role") == "export" and item.get("lineage_id") == primary_lineage] if isinstance(artifacts, list) else []
        if not exports:
            findings.append(_finding("MF-EXPORT", "milestone_framework.milestones.M5.artifacts", "accepted M5 requires a released export on the primary lineage"))
        manuscript = deliverables.get("M5")
        if isinstance(manuscript, dict):
            for index, export in enumerate(exports):
                if (
                    export.get("source_sha256") != manuscript.get("sha256")
                    or (
                        export.get("source_path") is not None
                        and export.get("source_path") != manuscript.get("path")
                    )
                ):
                    findings.append(_finding(
                        "MF-EXPORT", f"milestone_framework.milestones.M5.artifacts[{index}]",
                        "released export source binding must match the accepted manuscript path and SHA-256",
                    ))

    if target in {"Ph2", "Ph4"}:
        sections = document.get("sections")
        expected_milestone = "M4" if target == "Ph2" else "M5"
        acceptable_phases = {"Ph2", "Ph3", "Ph3_converged", "Ph4"}
        if target == "Ph2" and (
            not isinstance(sections, dict)
            or not sections
            or any(
                not isinstance(section, dict) or section.get("current_phase") not in acceptable_phases
                for section in sections.values()
            )
        ):
            findings.append(_finding("MF-PHASE", "sections", f"{target} target is inconsistent with current section phases"))
        expected_record = milestones.get(expected_milestone)
        if not isinstance(expected_record, dict) or expected_record.get("status") not in {"in_progress", "feedback_pending", "revision_required", "accepted"}:
            findings.append(_finding("MF-PHASE", f"milestone_framework.milestones.{expected_milestone}.status", f"{target} target requires active or accepted {expected_milestone}"))
        if target == "Ph4" and isinstance(sections, dict):
            phase_order = {"Ph1": 1, "Ph2": 2, "Ph3": 3, "Ph3_converged": 3, "Ph4": 4}
            default_ceiling = document.get("default_final_phase", "Ph4")
            requires_terminal_signoff = False
            for section_name, section in sections.items():
                if not isinstance(section, dict):
                    continue
                ceilings = [default_ceiling]
                if section.get("section_ceiling_override"):
                    ceilings.append(section["section_ceiling_override"])
                applicable_ceiling = min(ceilings, key=lambda phase: phase_order.get(phase, 99))
                ceiling_clear = (
                    section.get("ceiling_locked") is True
                    and section.get("last_approved_phase") == applicable_ceiling
                )
                if ceiling_clear:
                    continue
                requires_terminal_signoff = True
                if section.get("current_phase") != "Ph4":
                    findings.append(_finding(
                        "MF-PHASE", f"sections[{section_name!r}].current_phase",
                        "non-ceiling-locked section must be in Ph4 after MCR admission",
                    ))
                log = section.get("phase_entry_log")
                transitions = [
                    row for row in log
                    if isinstance(row, dict) and row.get("prev_phase") != row.get("new_phase")
                ] if isinstance(log, list) else []
                last_transition = transitions[-1] if transitions else {}
                admitted = (
                    last_transition.get("trigger") == "mcr_admission"
                    and last_transition.get("prev_phase") == "Ph3_converged"
                    and last_transition.get("new_phase") == "Ph4"
                )
                if not admitted:
                    findings.append(_finding(
                        "MF-PHASE", f"sections[{section_name!r}].phase_entry_log",
                        "Ph4 target requires an explicit Ph3_converged to Ph4 mcr_admission row",
                    ))
                if section.get("pre_mcr_deep_pass_completed") is not True:
                    findings.append(_finding(
                        "MF-PHASE", f"sections[{section_name!r}].pre_mcr_deep_pass_completed",
                        "Ph4 MCR continuity requires the pre-MCR deep pass to be complete",
                    ))
            if requires_terminal_signoff:
                signoff = _canonical_path(project_root, "reviews/ph3_convergence_signoff.md")
                try:
                    signoff_text = signoff.read_text(encoding="utf-8") if signoff and signoff.is_file() else ""
                except (OSError, UnicodeError):
                    signoff_text = ""
                if "is_terminal: true" not in signoff_text:
                    findings.append(_finding(
                        "MF-PHASE", "reviews/ph3_convergence_signoff.md",
                        "Ph4 MCR continuity requires current terminal Ph3 convergence signoff evidence",
                    ))

    return _result(target, ledger, findings, evidence)


def _result(
    target: str | None,
    ledger: dict[str, Any] | None,
    findings: list[Finding],
    evidence: list[dict[str, Any]],
) -> ValidationResult:
    unique = tuple(dict.fromkeys(findings))
    if unique:
        outcome = Outcome.MISCONFIGURED
    elif (
        target in MILESTONES
        and ledger
        and isinstance(ledger.get("milestones"), dict)
        and isinstance(ledger["milestones"].get(target), dict)
        and ledger["milestones"][target].get("applicability") == "not_applicable"
    ):
        outcome = Outcome.NOT_APPLICABLE
    elif ledger and ledger.get("mode") == "legacy":
        outcome = Outcome.LEGACY_READY
    else:
        outcome = Outcome.READY
    return ValidationResult(
        outcome=outcome,
        exit_permitted=outcome is not Outcome.MISCONFIGURED,
        target=target,
        findings=unique,
        evidence_bindings=tuple(evidence),
    )


def _render_text(result: ValidationResult) -> str:
    lines = [f"{result.outcome.value} target={result.target or 'all'} exit_permitted={str(result.exit_permitted).lower()}"]
    for finding in result.findings:
        lines.append(f"[{finding.severity.value}] {finding.code} @ {finding.path}: {finding.message}")
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    parser = UsageArgumentParser(description="Validate milestone feedback and F9 handoff state.")
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--target", choices=TARGETS)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    project_root = args.project_root
    if not project_root.is_dir():
        parser.error(f"--project-root is not a directory: {project_root}")
    phase_path = project_root / "reviews" / "phase_state.json"
    try:
        document = json.loads(phase_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"error: could not read {phase_path}: {exc}\n")
        return 2
    result = validate_document(project_root, document, args.target)
    if args.json:
        sys.stdout.write(json.dumps(result.json_value(), indent=2) + "\n")
    else:
        sys.stdout.write(_render_text(result))
    return 0 if result.exit_permitted else 4


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
