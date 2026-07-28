#!/usr/bin/env python3
"""Validate milestone feedback, bindings, lineage, and F9 handoffs.

The validator is read-only.  Its ``validate_document`` function is the shared
integration surface used by ``phase_state_validate.py`` so milestone semantics
remain in one implementation.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import stat
import sys
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
from reader_accessibility_policy import (
    PolicyError,
    recompute_check8,
    resolve_reader_profile,
    resolve_policy,
    resolve_unavailable_policy,
    validate_check8_evidence,
)
MILESTONE_SCHEMA_PATH = ROOT / "references" / "schemas" / "milestone_framework.schema.json"
F9_SCHEMA_PATH = ROOT / "references" / "schemas" / "f9_milestone_handoff.schema.json"
EXEMPLAR_REGISTRY_PATH = ROOT / "references" / "milestone_exemplars.json"
PLUGIN_MANIFEST_PATH = ROOT / ".claude-plugin" / "plugin.json"
EXEMPLAR_CLASSES = frozenset({"clean_lifecycle_exemplar", "legacy_migration_exemplar"})
EXEMPLAR_AUTHORITIES = frozenset({"user", "advisor", "instructor", "committee", "harness_maintainer", "portfolio_owner"})
EXEMPLAR_EVIDENCE_ROLES = {
    "clean_lifecycle_exemplar": frozenset({"milestone_validator", "phase_state_validator", "lifecycle_view", "release_gate", "independent_replay"}),
    "legacy_migration_exemplar": frozenset({"milestone_validator", "phase_state_validator", "migration_report", "migration_commit", "migration_manifest", "rollback_verification", "migration_approval"}),
}
REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
MILESTONES = ("M1", "M2", "M3", "M4", "M5")
TARGETS = (*MILESTONES, "Ph2", "Ph4")
GATE_BOUNDARIES = ("ph1_to_ph2", "ph4_admission", "ph4_terminal_close")
OVERRIDE_AUTHORITIES = frozenset({
    "user", "venue", "advisor", "instructor", "committee", "project_local_contract"
})
LEGACY_READER_PROFILE_HASHES = frozenset({
    # v0.28.1 package profile at ddf5618; accepted only for the bounded
    # continuing-cycle projection migration introduced by v0.29.0.
    "48400ad0881c54920ea43eebd53754ce3aff5763ef8d0a6f35cf1d4d73583e61",
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
    skipped_checks: tuple[dict[str, str], ...]

    def json_value(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome.value,
            "exit_permitted": self.exit_permitted,
            "target": self.target,
            "findings": [finding.json_value() for finding in self.findings],
            "evidence_bindings": list(self.evidence_bindings),
            "skipped_checks": list(self.skipped_checks),
        }


@dataclass(frozen=True)
class GateValidationResult:
    """Pre-transition milestone result; phases consume this without reimplementation."""

    boundary: str
    outcomes: dict[str, str]
    findings: tuple[Finding, ...]

    @property
    def exit_permitted(self) -> bool:
        return not self.findings


@dataclass(frozen=True)
class _GateValidationSession:
    project_root: Path
    document_sha256: str
    continuing: ValidationResult
    opening: ValidationResult


def _signed_status(path: Path) -> str | None:
    """Return one explicit positive signoff status, rejecting ambiguity/negation."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    statuses = [
        match.group(1).strip().upper()
        for line in text.splitlines()
        if (match := re.fullmatch(r"\s*status\s*:\s*([A-Za-z _-]+)\s*", line, re.IGNORECASE))
    ]
    if len(statuses) != 1 or statuses[0] not in {"PASS", "APPROVED", "SIGNED"}:
        return None
    return statuses[0]


_GATE_TARGETS = {
    "ph1_to_ph2": ("M1", "M2", "M3"),
    "ph4_admission": ("M4",),
    "ph4_terminal_close": ("M5",),
}


def _gate_boundary_findings(
    project_root: Path, document: Any, boundary: str,
) -> list[Finding]:
    """Evaluate only the transition-specific portion of one canonical gate."""

    if boundary not in GATE_BOUNDARIES:
        raise ValueError(f"unknown milestone gate boundary: {boundary}")
    if not isinstance(document, dict):
        return []
    framework = document.get("milestone_framework")
    milestones = framework.get("milestones") if isinstance(framework, dict) else None
    if not isinstance(milestones, dict):
        return []

    findings: list[Finding] = []
    if boundary == "ph1_to_ph2":
        for milestone in _GATE_TARGETS[boundary]:
            record = milestones.get(milestone)
            if not isinstance(record, dict) or record.get("applicability") == "not_applicable":
                continue
            handoff = record.get("handoff")
            if not isinstance(handoff, dict) or handoff.get("status") != "consumed":
                findings.append(_finding(
                    "MF-GATE-CHAIN", f"milestone_framework.milestones.{milestone}.handoff",
                    "Ph1 to Ph2 requires each applicable M1-M3 predecessor packet to be consumed",
                ))
    elif boundary == "ph4_admission":
        record = milestones.get("M4")
        approval = record.get("approval") if isinstance(record, dict) else None
        handoff = record.get("handoff") if isinstance(record, dict) else None
        if (
            not isinstance(record, dict)
            or record.get("status") != "accepted"
            or not isinstance(approval, dict)
            or approval.get("status") != "approved"
            or not isinstance(handoff, dict)
            or handoff.get("status") not in {"ready", "consumed"}
        ):
            findings.append(_finding(
                "MF-GATE-M4", "milestone_framework.milestones.M4",
                "Ph4 admission requires accepted M4 and a ready or transaction-consumed F9 handoff",
            ))
        if not (project_root / "reviews" / "ph3_convergence_signoff.md").is_file():
            findings.append(_finding(
                "MF-PHASE", "reviews/ph3_convergence_signoff.md",
                "Ph4 admission requires the canonical Ph3 convergence signoff; retired t3 paths are invalid",
            ))
    else:
        record = milestones.get("M5")
        approval = record.get("approval") if isinstance(record, dict) else None
        handoff = record.get("handoff") if isinstance(record, dict) else None
        if (
            not isinstance(record, dict)
            or record.get("status") != "accepted"
            or record.get("dependency_state") != "current"
            or not isinstance(approval, dict)
            or approval.get("status") != "approved"
            or not isinstance(handoff, dict)
            or handoff.get("status") not in {"ready", "consumed"}
        ):
            findings.append(_finding(
                "MF-GATE-M5", "milestone_framework.milestones.M5",
                "terminal close requires current-hash M5 approval, a ready F9 handoff, and no stale dependency",
            ))
        for upstream in ("M1", "M2", "M3", "M4"):
            upstream_record = milestones.get(upstream)
            upstream_approval = upstream_record.get("approval") if isinstance(upstream_record, dict) else None
            upstream_handoff = upstream_record.get("handoff") if isinstance(upstream_record, dict) else None
            if isinstance(upstream_record, dict) and (
                upstream_record.get("dependency_state") == "needs_revalidation"
                or upstream_record.get("status") == "reopened"
                or (isinstance(upstream_approval, dict) and upstream_approval.get("status") == "reopened")
                or (isinstance(upstream_handoff, dict) and upstream_handoff.get("status") == "needs_revalidation")
            ):
                findings.append(_finding(
                    "MF-GATE-M5", f"milestone_framework.milestones.{upstream}",
                    f"terminal close is blocked while upstream {upstream} is reopened or needs revalidation",
                ))
        for relative in ("reviews/G4_signoff.md", "reviews/ph4_ship_signoff.md"):
            path = project_root / relative
            if _signed_status(path) is None:
                findings.append(_finding(
                    "MF-GATE-M5", relative,
                    f"terminal close requires exactly one explicit `status: PASS|APPROVED|SIGNED` at {relative}",
                ))
    return findings


def _gate_document_sha256(document: Any) -> str:
    payload = json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _prepare_gate_validation_session(
    project_root: Path, document: Any,
) -> _GateValidationSession:
    """Build the two exact policy views shared by one gate invocation."""

    root = project_root.resolve()
    return _GateValidationSession(
        project_root=root,
        document_sha256=_gate_document_sha256(document),
        continuing=validate_document(root, document, opening_new_cycle=False),
        opening=validate_document(root, document, opening_new_cycle=True),
    )


def validate_gate(
    project_root: Path, document: Any, boundary: str,
    *, _session: _GateValidationSession | None = None,
) -> GateValidationResult:
    """Validate a pre-transition milestone boundary using canonical semantics."""
    if boundary not in GATE_BOUNDARIES:
        raise ValueError(f"unknown milestone gate boundary: {boundary}")
    root = project_root.resolve()
    session = _session or _prepare_gate_validation_session(root, document)
    if (
        session.project_root != root
        or session.document_sha256 != _gate_document_sha256(document)
    ):
        raise ValueError("gate validation session does not bind the supplied project and document")
    findings = list(session.continuing.findings)
    outcomes: dict[str, str] = {}
    framework = document.get("milestone_framework") if isinstance(document, dict) else None
    ledger = framework if isinstance(framework, dict) else None
    for milestone in _GATE_TARGETS[boundary]:
        target_findings = list(session.opening.findings)
        if ledger is not None:
            target_findings.extend(_milestone_target_findings(ledger, milestone))
        target_result = _result(
            milestone,
            ledger,
            target_findings,
            list(session.opening.evidence_bindings),
            list(session.opening.skipped_checks),
        )
        outcomes[milestone] = target_result.outcome.value
        findings.extend(target_result.findings)
    findings.extend(_gate_boundary_findings(root, document, boundary))
    return GateValidationResult(boundary, outcomes, tuple(dict.fromkeys(findings)))


def _finding(code: str, path: str, message: str, severity: Severity = Severity.BLOCKER) -> Finding:
    return Finding(code=code, severity=severity, path=path, message=message)


def _milestone_target_findings(
    ledger: dict[str, Any], target: str | None,
) -> list[Finding]:
    """Return only the target-specific readiness findings for one milestone."""

    if target not in MILESTONES:
        return []
    milestones = ledger.get("milestones")
    if not isinstance(milestones, dict):
        return []
    target_record = milestones.get(target)
    target_is_not_applicable = (
        isinstance(target_record, dict)
        and target_record.get("applicability") == "not_applicable"
    )
    completed_through = None
    if ledger.get("mode") == "legacy" and isinstance(ledger.get("migration_boundary"), dict):
        completed_through = ledger["migration_boundary"].get("completed_through")
    legacy_boundary_covers_target = (
        completed_through in MILESTONES
        and MILESTONES.index(target) <= MILESTONES.index(completed_through)
    )
    if target_is_not_applicable or legacy_boundary_covers_target:
        return []
    approval = target_record.get("approval") if isinstance(target_record, dict) else None
    handoff = target_record.get("handoff") if isinstance(target_record, dict) else None
    if (
        isinstance(target_record, dict)
        and target_record.get("status") == "accepted"
        and target_record.get("dependency_state") == "current"
        and isinstance(approval, dict)
        and approval.get("status") == "approved"
        and isinstance(handoff, dict)
        and handoff.get("status") in {"ready", "consumed"}
    ):
        return []
    return [_finding(
        "MF-HANDOFF", f"milestone_framework.milestones.{target}",
        f"{target} readiness requires accepted status, current dependency, "
        "approved evidence, and a ready or consumed F9 handoff; legacy coverage "
        f"ends at {completed_through or 'none'}",
    )]


def _trusted_path_migrations(
    project_root: Path,
    ledger: dict[str, Any],
    findings: list[Finding],
) -> dict[str, dict[str, Any]]:
    """Load only target-bound applied manifests signed by migration events."""
    mappings: dict[str, dict[str, Any]] = {}
    events = ledger.get("events")
    if not isinstance(events, list):
        return mappings
    for index, event in enumerate(events):
        if not isinstance(event, dict) or event.get("event_type") != "migration_accepted":
            continue
        base = f"milestone_framework.events[{index}].evidence_path"
        relative = event.get("evidence_path")
        expected_sha = event.get("evidence_sha256")
        candidate = _canonical_path(project_root, relative)
        if (
            candidate is None
            or not isinstance(relative, str)
            or not relative.startswith("reviews/.harness/path_migrations/")
            or not relative.endswith(".applied.json")
            or not candidate.is_file()
        ):
            findings.append(_finding("MF-EVENT", base, "migration manifest must be a contained applied path-migration manifest"))
            continue
        try:
            payload = candidate.read_bytes()
            manifest = json.loads(payload)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            findings.append(_finding("MF-EVENT", base, f"migration manifest is unreadable: {exc}"))
            continue
        actual_sha = hashlib.sha256(payload).hexdigest()
        migration_id = manifest.get("migration_id") if isinstance(manifest, dict) else None
        expected_name = f"{migration_id}.applied.json" if isinstance(migration_id, str) else None
        plan_payload = {
            "moves": manifest.get("moves") if isinstance(manifest, dict) else None,
            "receipts": manifest.get("receipt_inventory") if isinstance(manifest, dict) else None,
            "state": manifest.get("state") if isinstance(manifest, dict) else None,
        }
        plan_sha = hashlib.sha256(json.dumps(
            plan_payload, sort_keys=True, separators=(",", ":"),
        ).encode()).hexdigest()
        trusted = (
            isinstance(manifest, dict)
            and expected_sha == actual_sha
            and manifest.get("schema_version") == "1.0.0"
            and manifest.get("path_contract_version") == ledger.get("path_contract_version")
            and manifest.get("manifest_path") == relative
            and candidate.name == expected_name
            and manifest.get("project_root") == str(project_root.resolve())
            and manifest.get("applied_at") == event.get("timestamp")
            and manifest.get("plan_sha256") == plan_sha
            and isinstance(manifest.get("moves"), list)
        )
        if not trusted:
            findings.append(_finding("MF-EVENT", base, "migration manifest is unsigned, unknown, drifted, or not target-bound"))
            continue
        for move_index, move in enumerate(manifest["moves"]):
            if not isinstance(move, dict):
                findings.append(_finding("MF-EVENT", base, f"migration move {move_index} must be an object"))
                continue
            source = move.get("source")
            target = move.get("target")
            source_sha = move.get("sha256")
            if (
                not isinstance(source, str)
                or not isinstance(target, str)
                or not isinstance(source_sha, str)
                or re.fullmatch(r"[0-9a-f]{64}", source_sha) is None
                or _canonical_path(project_root, source) is None
                or _canonical_path(project_root, target) is None
                or source in mappings
            ):
                findings.append(_finding("MF-EVENT", base, f"migration move {move_index} is unsafe, malformed, or conflicting"))
                continue
            mappings[source] = {
                "target": target,
                "source_sha256": source_sha,
                "applied_sequence": event.get("sequence"),
                "manifest_path": relative,
            }
    return mappings


def _later_authorized_baseline(
    events: list[Any], index: int, event: dict[str, Any], binding_type: Any,
) -> bool:
    if binding_type not in {"artifact", "feedback", "handoff_packet"}:
        return False
    milestone = event.get("milestone")
    lineage = event.get("lineage_id")
    for later in events[index + 1:]:
        if not isinstance(later, dict) or later.get("lineage_id") != lineage:
            continue
        if later.get("milestone") == milestone and later.get("event_type") in {
            "milestone_reopened", "milestone_superseded", "authorized_override", "downstream_stale",
        }:
            return True
    return False


def _validate_event_binding(
    project_root: Path,
    events: list[Any],
    event_index: int,
    event: dict[str, Any],
    binding: dict[str, Any],
    binding_path: str,
    migrations: dict[str, dict[str, Any]],
    findings: list[Finding],
    evidence: list[dict[str, Any]],
) -> None:
    relative = binding.get("path")
    expected_sha = binding.get("sha256")
    migration = migrations.get(relative) if isinstance(relative, str) else None
    resolved = migration.get("target") if isinstance(migration, dict) else relative
    candidate = _canonical_path(project_root, resolved)
    if candidate is None:
        findings.append(_finding("MF-CANON", binding_path, "path must be non-empty and remain inside the project root"))
        return
    if not candidate.is_file():
        findings.append(_finding("MF-CANON", binding_path, f"canonical path does not exist: {relative!r}"))
        return
    if isinstance(migration, dict) and expected_sha == migration.get("source_sha256"):
        return
    if _later_authorized_baseline(events, event_index, event, binding.get("binding_type")):
        return
    _file_binding(
        project_root, resolved, expected_sha, None, binding_path,
        findings, evidence, "MF-EVENT",
    )


def _validate_events(
    project_root: Path,
    ledger: dict[str, Any],
    milestones: dict[str, Any],
    findings: list[Finding],
    evidence: list[dict[str, Any]],
    migrations: dict[str, dict[str, Any]],
) -> None:
    events = ledger.get("events")
    if not isinstance(events, list):
        return
    sequences = [event.get("sequence") for event in events if isinstance(event, dict)]
    if sequences != list(range(1, len(events) + 1)):
        findings.append(_finding("MF-EVENT", "milestone_framework.events", "event sequence must be append-only, unique, and contiguous from 1"))
    parsed_times: list[datetime.datetime] = []
    for index, event in enumerate(events):
        timestamp = event.get("timestamp") if isinstance(event, dict) else None
        try:
            if not isinstance(timestamp, str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z", timestamp) is None:
                raise ValueError
            parsed = datetime.datetime.fromisoformat(timestamp[:-1] + "+00:00")
        except ValueError:
            findings.append(_finding("MF-EVENT", f"milestone_framework.events[{index}].timestamp", "event timestamp must be strict ISO-8601 UTC ending in Z"))
            continue
        parsed_times.append(parsed)
    if len(parsed_times) == len(events) and parsed_times != sorted(parsed_times):
        findings.append(_finding("MF-EVENT", "milestone_framework.events", "event timestamps must be nondecreasing in sequence order"))
    observed: dict[str, list[dict[str, Any]]] = {milestone: [] for milestone in MILESTONES}
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            continue
        milestone = event.get("milestone")
        event_type = event.get("event_type")
        if milestone in observed and isinstance(event_type, str):
            observed[milestone].append(event)
        if event.get("lineage_id") != ledger.get("primary_lineage") and event_type not in {"milestone_superseded"}:
            findings.append(_finding("MF-EVENT", f"milestone_framework.events[{index}].lineage_id", "current-state event lineage must match primary_lineage"))
        base = f"milestone_framework.events[{index}]"
        path = event.get("evidence_path")
        digest = event.get("evidence_sha256")
        if path is not None or digest is not None:
            _file_binding(project_root, path, digest, None, f"{base}.evidence_path", findings, evidence, "MF-EVENT")
        bindings = event.get("bindings")
        if isinstance(bindings, list):
            for binding_index, binding in enumerate(bindings):
                if isinstance(binding, dict):
                    _validate_event_binding(
                        project_root, events, index, event, binding,
                        f"{base}.bindings[{binding_index}]", migrations, findings, evidence,
                    )
        cause = event.get("caused_by_sequence")
        if event_type in {"downstream_stale", "downstream_revalidated"}:
            expected_type = "milestone_reopened" if event_type == "downstream_stale" else "downstream_stale"
            cause_event = events[cause - 1] if isinstance(cause, int) and 0 < cause <= len(events) and cause < event.get("sequence", 0) else None
            if not isinstance(cause_event, dict) or cause_event.get("event_type") != expected_type:
                findings.append(_finding("MF-EVENT", f"{base}.caused_by_sequence", f"{event_type} must causally reference an earlier {expected_type} event"))
            elif cause_event.get("lineage_id") != event.get("lineage_id"):
                findings.append(_finding("MF-EVENT", f"{base}.caused_by_sequence", f"{event_type} cause must share the affected lineage"))
            elif event_type == "downstream_stale" and (
                cause_event.get("milestone") not in MILESTONES
                or milestone not in MILESTONES
                or MILESTONES.index(cause_event["milestone"]) >= MILESTONES.index(milestone)
            ):
                findings.append(_finding("MF-EVENT", f"{base}.caused_by_sequence", "downstream_stale must reference a genuinely upstream reopened milestone"))
            elif event_type == "downstream_revalidated" and cause_event.get("milestone") != milestone:
                findings.append(_finding("MF-EVENT", f"{base}.caused_by_sequence", "downstream_revalidated must reference the stale event for the same milestone and lineage"))
        elif cause is not None:
            findings.append(_finding("MF-EVENT", f"{base}.caused_by_sequence", "caused_by_sequence is reserved for downstream stale/revalidated causality"))
    for milestone, record in milestones.items():
        if not isinstance(record, dict) or milestone not in observed:
            continue
        milestone_events = observed[milestone]
        event_types = {event.get("event_type") for event in milestone_events}
        required: set[str] = set()
        status = record.get("status")
        handoff = record.get("handoff")
        approval = record.get("approval")
        if status == "in_progress":
            required.add("milestone_started")
        if status == "accepted":
            required.add("milestone_accepted")
        feedback_records = record.get("feedback_records")
        if isinstance(feedback_records, list) and feedback_records:
            required.add("feedback_recorded")
            if all(isinstance(item, dict) and item.get("disposition") for item in feedback_records):
                required.add("feedback_adjudicated")
            for feedback in feedback_records:
                if not isinstance(feedback, dict):
                    continue
                expected_feedback = {
                    "binding_type": "feedback",
                    "path": feedback.get("source_path"),
                    "sha256": feedback.get("source_sha256"),
                }
                for event_type in ("feedback_recorded", "feedback_adjudicated"):
                    matching = [event for event in milestone_events if event.get("event_type") == event_type]
                    if not any(expected_feedback in event.get("bindings", []) for event in matching):
                        findings.append(_finding("MF-EVENT", "milestone_framework.events", f"{milestone} {event_type} must bind current feedback path and hash"))
        artifacts = record.get("artifacts")
        primary_deliverables = [
            artifact for artifact in artifacts
            if isinstance(artifact, dict)
            and artifact.get("role") == "deliverable"
            and artifact.get("lineage_id") == ledger.get("primary_lineage")
        ] if isinstance(artifacts, list) else []
        if (
            status in {"in_progress", "feedback_pending", "revision_required", "reopened"}
            and record.get("dependency_state") != "needs_revalidation"
        ):
            recorded = [
                event for event in milestone_events
                if event.get("event_type") == "deliverable_recorded"
            ]
            for deliverable in primary_deliverables:
                expected_deliverable = {
                    "binding_type": "artifact",
                    "path": deliverable.get("path"),
                    "sha256": deliverable.get("sha256"),
                }
                if not any(
                    expected_deliverable in event.get("bindings", [])
                    for event in recorded
                ):
                    findings.append(_finding(
                        "MF-EVENT",
                        "milestone_framework.events",
                        f"{milestone} current primary-lineage deliverable requires a "
                        "deliverable_recorded event binding its path and hash",
                    ))
        if status == "reopened" or (isinstance(approval, dict) and approval.get("status") == "reopened"):
            required.add("milestone_reopened")
        if status == "superseded":
            required.add("milestone_superseded")
        if record.get("applicability") == "not_applicable":
            required.add("authorized_override")
        if isinstance(handoff, dict) and handoff.get("status") in {"ready", "consumed"}:
            required.add("handoff_ready")
        if isinstance(handoff, dict) and handoff.get("status") == "consumed":
            required.add("handoff_consumed")
        if record.get("dependency_state") == "needs_revalidation" or (isinstance(handoff, dict) and handoff.get("status") == "needs_revalidation"):
            required.add("downstream_stale")
        for event_type in sorted(required - event_types):
            findings.append(_finding(
                "MF-EVENT", f"milestone_framework.events",
                f"{milestone} state requires an append-only {event_type} event",
            ))
        if record.get("applicability") == "not_applicable":
            override = record.get("authorized_override")
            override_event = next((event for event in reversed(milestone_events) if event.get("event_type") == "authorized_override"), None)
            if isinstance(override, dict) and isinstance(override_event, dict) and (
                override_event.get("authority") != override.get("authority")
                or override_event.get("evidence_path") != override.get("substitute_evidence")
                or override_event.get("evidence_sha256") != override.get("substitute_evidence_sha256")
            ):
                findings.append(_finding("MF-EVENT", "milestone_framework.events", f"current {milestone} override event must bind its authority and substitute evidence"))
        lifecycle = [event for event in milestone_events if event.get("event_type") in {"milestone_started", "milestone_accepted", "milestone_reopened", "milestone_superseded", "authorized_override", "migration_hold"}]
        allowed_latest = {
            "not_started": {"migration_hold"},
            "in_progress": {"milestone_started"},
            "not_applicable": {"authorized_override"},
            "accepted": {"milestone_accepted"},
            "reopened": {"milestone_reopened"},
            "superseded": {"milestone_superseded"},
        }.get(status, set())
        latest_lifecycle = lifecycle[-1] if lifecycle else None
        if status == "not_started" and lifecycle and latest_lifecycle.get("event_type") not in allowed_latest:
            findings.append(_finding("MF-EVENT", "milestone_framework.events", f"not-started {milestone} cannot retain unexplained prior lifecycle events"))
        elif status != "not_started" and (not isinstance(latest_lifecycle, dict) or latest_lifecycle.get("event_type") not in allowed_latest):
            findings.append(_finding("MF-EVENT", "milestone_framework.events", f"latest lifecycle event for {milestone} is inconsistent with state {status}"))
        if status == "accepted":
            accepted = next((event for event in reversed(milestone_events) if event.get("event_type") == "milestone_accepted"), None)
            deliverable = next((item for item in artifacts if isinstance(item, dict) and item.get("role") == "deliverable" and item.get("lineage_id") == ledger.get("primary_lineage")), None) if isinstance(artifacts, list) else None
            approval_state = record.get("approval")
            if isinstance(accepted, dict) and isinstance(deliverable, dict):
                expected_binding = {"binding_type": "artifact", "path": deliverable.get("path"), "sha256": deliverable.get("sha256")}
                if expected_binding not in accepted.get("bindings", []):
                    findings.append(_finding("MF-EVENT", "milestone_framework.events", f"current {milestone} acceptance event must bind the accepted deliverable hash"))
                if isinstance(approval_state, dict) and accepted.get("evidence_path") != approval_state.get("evidence_path"):
                    findings.append(_finding("MF-EVENT", "milestone_framework.events", f"current {milestone} acceptance event must bind approval evidence"))
        if isinstance(handoff, dict) and handoff.get("status") in {"ready", "consumed"}:
            expected_handoff = "handoff_consumed" if handoff.get("status") == "consumed" else "handoff_ready"
            handoff_events = [event for event in milestone_events if event.get("event_type") in {"handoff_ready", "handoff_consumed"}]
            current_event = handoff_events[-1] if handoff_events else None
            if not isinstance(current_event, dict) or current_event.get("event_type") != expected_handoff:
                findings.append(_finding("MF-EVENT", "milestone_framework.events", f"latest handoff event for {milestone} must be {expected_handoff}"))
            elif {"binding_type": "handoff_packet", "path": handoff.get("packet_path"), "sha256": handoff.get("packet_sha256")} not in current_event.get("bindings", []):
                findings.append(_finding("MF-EVENT", "milestone_framework.events", f"current {milestone} handoff event must bind the current F9 hash"))
        elif isinstance(handoff, dict) and handoff.get("status") in {"not_ready", "not_applicable"}:
            handoff_events = [event for event in milestone_events if event.get("event_type") in {"handoff_ready", "handoff_consumed"}]
            if handoff_events and (
                not isinstance(latest_lifecycle, dict)
                or latest_lifecycle.get("sequence", 0) <= handoff_events[-1].get("sequence", 0)
                or latest_lifecycle.get("event_type") not in {"milestone_started", "milestone_reopened", "authorized_override", "migration_hold"}
            ):
                findings.append(_finding("MF-EVENT", "milestone_framework.events", f"{milestone} {handoff.get('status')} handoff requires a later reset-authorizing lifecycle event"))
        stale_events = [event for event in milestone_events if event.get("event_type") in {"downstream_stale", "downstream_revalidated"}]
        if record.get("dependency_state") == "current" and stale_events and stale_events[-1].get("event_type") == "downstream_stale":
            findings.append(_finding("MF-EVENT", "milestone_framework.events", f"{milestone} cannot be current while its latest dependency event is downstream_stale"))


def _schema_code(path: list[Any], message: str) -> str:
    tokens = {str(token) for token in path}
    if "authorized_override" in tokens or "migration_boundary" in tokens:
        return "MF-OVERRIDE"
    if "feedback_records" in tokens:
        return "MF-FEEDBACK"
    if "events" in tokens:
        return "MF-EVENT"
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


def _document_anchors(text: str) -> set[str]:
    anchors = set(re.findall(r"<a\s+id=[\"']([^\"']+)[\"']\s*>", text, re.IGNORECASE))
    for line in text.splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
        if not match:
            continue
        slug = re.sub(r"[^a-z0-9\s-]", "", match.group(1).lower())
        anchors.add(re.sub(r"[\s-]+", "-", slug).strip("-"))
    return anchors


def _override_rule_resolves(project_root: Path, rule: Any, authority: Any) -> bool:
    if not isinstance(rule, str) or "#" not in rule:
        return False
    relative, anchor = rule.split("#", 1)
    if not relative or not anchor:
        return False
    if authority == "project_local_contract":
        locator = Path(relative)
        if locator.is_absolute() or ".." in locator.parts:
            return False
        source = _canonical_path(project_root, relative)
        if source is None:
            return False
    else:
        if not relative.startswith("references/"):
            return False
        source = (ROOT / relative).resolve()
        try:
            source.relative_to((ROOT / "references").resolve())
        except ValueError:
            return False
    try:
        text = source.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    return anchor in _document_anchors(text)


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
        _file_binding(
            project_root,
            feedback.get("contemporaneity_evidence_path"),
            feedback.get("contemporaneity_evidence_sha256"),
            None,
            f"{path}.contemporaneity_evidence_path",
            findings,
            evidence,
            "MF-FEEDBACK",
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
    active_lineages = [
        item.get("lineage_id") for item in deliverables
        if isinstance(item.get("lineage_id"), str) and item.get("lineage_id")
    ]
    if len(active_lineages) != len(set(active_lineages)):
        findings.append(_finding(
            "MF-LINEAGE", f"milestone_framework.milestones.{milestone}.artifacts",
            "simultaneous active deliverable candidates must have distinct lineage IDs",
        ))
    explicit_supersessions = 0
    known_lineages = set(active_lineages)
    supersession_edges: dict[str, str] = {}
    for index, item in enumerate(deliverables):
        superseded = item.get("supersedes_lineage_id")
        if superseded is None:
            continue
        if superseded == item.get("lineage_id") or superseded not in known_lineages:
            findings.append(_finding(
                "MF-LINEAGE", f"milestone_framework.milestones.{milestone}.artifacts[{index}].supersedes_lineage_id",
                "supersedes_lineage_id must name a different deliverable lineage in the same milestone",
            ))
        else:
            explicit_supersessions += 1
            supersession_edges[item["lineage_id"]] = superseded
    for origin in supersession_edges:
        visited: set[str] = set()
        cursor = origin
        while cursor in supersession_edges:
            if cursor in visited:
                findings.append(_finding(
                    "MF-LINEAGE", f"milestone_framework.milestones.{milestone}.artifacts",
                    "deliverable supersession links must be acyclic",
                ))
                break
            visited.add(cursor)
            cursor = supersession_edges[cursor]
    if record.get("status") == "superseded" and explicit_supersessions == 0:
        findings.append(_finding(
            "MF-LINEAGE", f"milestone_framework.milestones.{milestone}.artifacts",
            "superseded milestone state requires an explicit artifact-level supersedes_lineage_id link",
        ))
    if record.get("status") == "accepted":
        superseded_targets = set(supersession_edges.values())
        unsuperseded = [
            item for item in deliverables if item.get("lineage_id") not in superseded_targets
        ]
        if len(unsuperseded) != 1 or unsuperseded[0].get("lineage_id") != primary_lineage:
            findings.append(_finding(
                "MF-LINEAGE", f"milestone_framework.milestones.{milestone}.artifacts",
                "accepted milestone must have exactly one unsuperseded deliverable on the primary lineage",
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


def validate_scholarly_authority_chain(
    project_root: Path,
    draft_results: dict[str, dict[str, Any]],
    scholarly: dict[str, Any],
    expected_receipt_id: str,
) -> None:
    """Cross-bind C6 to the exact consumed assignment and draft authorities."""

    generation = draft_results["draft_generation"]
    evaluation = draft_results["draft_evaluation"]
    generation_locator = generation["locator"]
    evaluation_locator = evaluation["locator"]
    receipt_ids = {
        generation_locator.get("receipt_id"),
        evaluation_locator.get("receipt_id"),
        expected_receipt_id,
    }
    if len(receipt_ids) != 1 or None in receipt_ids:
        raise ValueError(
            "draft and scholarly authority do not share the consumed assignment receipt"
        )
    generation_id = generation["transaction"].get("transaction_id")
    if (
        not isinstance(generation_id, str)
        or evaluation_locator.get("generation_verifier_transaction_id") != generation_id
    ):
        raise ValueError(
            "evaluation authority does not bind the qualified generation transaction"
        )
    try:
        evaluation_value = json.loads(
            Path(scholarly["evaluation_path"]).read_text(encoding="utf-8")
        )
        c6_evaluator_claim = evaluation_value["evaluation_dispatch"]["claim"]
    except (KeyError, TypeError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(
            f"qualified scholarly evaluation does not expose its evaluator claim: {exc}"
        ) from exc
    selected_evaluator_claim = evaluation_locator.get("dispatch_claim")
    if (
        not isinstance(c6_evaluator_claim, dict)
        or set(c6_evaluator_claim) != {"path", "sha256", "byte_length"}
        or not isinstance(selected_evaluator_claim, dict)
        or selected_evaluator_claim.get("root") != "project"
        or selected_evaluator_claim.get("path") != c6_evaluator_claim.get("path")
        or selected_evaluator_claim.get("sha256") != c6_evaluator_claim.get("sha256")
    ):
        raise ValueError(
            "draft_evaluation selects another Evaluator claim than the C6 evaluation transaction"
        )
    selected_claim_path = _canonical_path(
        project_root, selected_evaluator_claim.get("path")
    )
    if (
        selected_claim_path is None
        or not selected_claim_path.is_file()
        or selected_claim_path.stat().st_size != c6_evaluator_claim.get("byte_length")
    ):
        raise ValueError("the exact C6 evaluator claim binding is unavailable or stale")
    dependency_inventory = {
        str(Path(row["path"]).resolve()): (row["sha256"], row["byte_length"])
        for row in scholarly["dependencies"]
    }
    for key, result in draft_results.items():
        binding = result["locator"].get("dispatch_claim")
        if not isinstance(binding, dict) or binding.get("root") != "project":
            raise ValueError(f"{key} dispatch claim has no exact project binding")
        claim = _canonical_path(project_root, binding.get("path"))
        if claim is None or not claim.is_file():
            raise ValueError(f"{key} dispatch claim is unavailable")
        expected = (binding.get("sha256"), claim.stat().st_size)
        if dependency_inventory.get(str(claim.resolve())) != expected:
            raise ValueError(
                f"scholarly evaluation does not reuse the exact {key} dispatch claim"
            )


def _validate_scholarly_policy(
    project_root: Path,
    milestone: str,
    record: dict[str, Any],
    deliverable: dict[str, Any] | None,
    findings: list[Finding],
    evidence: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Replay the sole C6 predicate and cross-bind immutable ledger snapshots."""

    if milestone not in {"M1", "M2", "M3", "M4"}:
        return None
    if deliverable is None or record.get("status") in {
        "not_started", "not_applicable", "legacy_unverified",
    }:
        return None
    base = f"milestone_framework.milestones.{milestone}.policy_evidence.scholarly_evaluation"
    policy = record.get("policy_evidence")
    binding = policy.get("scholarly_evaluation") if isinstance(policy, dict) else None
    if binding is None:
        findings.append(_finding(
            "AMC-SCHOLARLY-EVALUATION-MISSING", base,
            "recorded milestone lacks a current independent scholarly evaluation",
        ))
        return None
    # The native bootstrap deliberately runs this validator under ``-I -S``.
    # Keep the jsonschema-backed scholarly verifier off that blank-project path;
    # recorded lifecycle evidence still loads and executes the sole C6 API.
    from scholarly_evaluation_binding import (
        ScholarlyBindingError,
        validate_scholarly_binding,
    )
    try:
        if not isinstance(binding, dict):
            raise ValueError("binding is not an object")
        evaluation_path = _canonical_path(project_root, binding.get("evidence_path"))
        if evaluation_path is None or not evaluation_path.is_file():
            raise ValueError("evaluation path is absent or outside the project")
        value = json.loads(evaluation_path.read_text(encoding="utf-8"))
        artifact_binding = value.get("artifact") if isinstance(value, dict) else None
        artifact_path = _canonical_path(
            project_root,
            artifact_binding.get("path") if isinstance(artifact_binding, dict) else None,
        )
        if artifact_path is None:
            raise ValueError("evaluation artifact path is absent or outside the project")
        scholarly = validate_scholarly_binding(
            project_root=project_root,
            artifact=artifact_path,
            binding=binding,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, ScholarlyBindingError) as exc:
        detail = exc.message if isinstance(exc, ScholarlyBindingError) else str(exc)
        cause = (
            f"{exc.cause_code}: "
            if isinstance(exc, ScholarlyBindingError) and exc.cause_code
            else ""
        )
        findings.append(_finding(
            "AMC-SCHOLARLY-EVALUATION-STALE", base, f"{cause}{detail}",
        ))
        return None
    if (
        deliverable.get("sha256") != scholarly["artifact"]["sha256"]
        or deliverable.get("bytes") != scholarly["artifact"]["byte_length"]
    ):
        findings.append(_finding(
            "AMC-SCHOLARLY-EVALUATION-STALE", base,
            "qualified scholarly artifact bytes differ from the ledger deliverable",
        ))
        return None
    try:
        from draft_evidence_verifier import (
            VerifierError,
            validate_lifecycle_verifier_binding,
        )

        assignment = policy.get("assignment_receipt") if isinstance(policy, dict) else None
        if (
            not isinstance(assignment, dict)
            or set(assignment) != {"receipt_id", "evidence_path", "evidence_sha256"}
            or not isinstance(assignment.get("receipt_id"), str)
            or not assignment["receipt_id"]
        ):
            raise ValueError("recorded assignment-receipt binding is absent or malformed")
        receipt_path = _canonical_path(project_root, assignment.get("evidence_path"))
        if receipt_path is None or not receipt_path.is_file() or receipt_path.parent.name != "consumed":
            raise ValueError("recorded assignment receipt is unavailable outside the consumed lane")
        receipt_payload = receipt_path.read_bytes()
        if hashlib.sha256(receipt_payload).hexdigest() != assignment.get("evidence_sha256"):
            raise ValueError("recorded assignment receipt hash is stale")
        receipt_value = json.loads(receipt_payload)
        if not isinstance(receipt_value, dict) or receipt_value.get("receipt_id") != assignment["receipt_id"]:
            raise ValueError("recorded assignment receipt identity is stale")
        draft_results: dict[str, dict[str, Any]] = {}
        for key, phase_name, disposition in (
            ("draft_generation", "generation", "evaluation_ready"),
            ("draft_evaluation", "evaluation", "product_qualified"),
        ):
            locator_binding = policy.get(key) if isinstance(policy, dict) else None
            if (
                not isinstance(locator_binding, dict)
                or set(locator_binding) != {"evidence_path", "evidence_sha256"}
            ):
                raise ValueError(f"{key} binding is absent or malformed")
            locator = _canonical_path(project_root, locator_binding.get("evidence_path"))
            if locator is None or not locator.is_file():
                raise ValueError(f"{key} locator is unavailable")
            if hashlib.sha256(locator.read_bytes()).hexdigest() != locator_binding.get("evidence_sha256"):
                raise ValueError(f"{key} locator hash is stale")
            draft_results[key] = validate_lifecycle_verifier_binding(
                locator=locator,
                artifact=scholarly["artifact_path"],
                project_root=project_root,
                harness_root=ROOT,
                expected_phase=phase_name,
                expected_disposition=disposition,
            )
        validate_scholarly_authority_chain(
            project_root, draft_results, scholarly, assignment["receipt_id"],
        )
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError, VerifierError) as exc:
        findings.append(_finding(
            "AMC-SCHOLARLY-EVALUATION-STALE", base,
            f"scholarly lifecycle authority is stale: {exc}",
        ))
        return None
    for row in scholarly["dependencies"]:
        evidence.append({
            "kind": "scholarly_evaluation_dependency",
            "path": row["path"],
            "sha256": row["sha256"],
            "bytes": row["byte_length"],
        })
    return scholarly


def _validate_packet(
    project_root: Path,
    milestone: str,
    record: dict[str, Any],
    deliverable: dict[str, Any] | None,
    primary_lineage: Any,
    predecessor: dict[str, str] | None,
    project_identity: str | None,
    f9_schema: dict[str, Any],
    findings: list[Finding],
    evidence: list[dict[str, Any]],
    scholarly: dict[str, Any] | None,
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
    expected_successor = {"M1": "M2", "M2": "M3", "M3": "M4", "M4": "M5", "M5": None}[milestone]
    if packet.get("from_milestone") != milestone:
        findings.append(_finding(
            "MF-HANDOFF", f"{base}.packet.from_milestone",
            "F9 source milestone must match the ledger milestone that binds the packet",
        ))
    if packet.get("to_milestone") != expected_successor:
        findings.append(_finding(
            "MF-HANDOFF", f"{base}.packet.to_milestone",
            "F9 destination milestone must be the adjacent successor bound by the ledger position",
        ))
    if project_identity is not None and packet.get("project") != project_identity:
        findings.append(_finding(
            "MF-HANDOFF", f"{base}.packet.project",
            "F9 project identity must match the authoritative phase-state project identity",
        ))
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
    record_policy = record.get("policy_evidence")
    if record_policy is not None and packet.get("policy_evidence") != record_policy:
        findings.append(_finding(
            "MF-POLICY", f"{base}.packet.policy_evidence",
            "F9 policy evidence must exactly match milestone policy evidence",
        ))
    return {"path": handoff.get("packet_path"), "sha256": handoff.get("packet_sha256")}


def reader_policy_staleness_codes(binding: dict[str, Any], current: dict[str, Any], *, opening_new_cycle: bool) -> list[str]:
    """Return independent MF-POLICY stale reasons in deterministic order."""
    checks = (
        ("profile_sha256", "MF-POLICY-PROFILE-STALE"),
        ("attestation_view_pin", "MF-POLICY-ATTESTATION-PIN-STALE"),
        ("exemplar_view_pin", "MF-POLICY-EXEMPLAR-PIN-STALE"),
    )
    codes = [code for key, code in checks if binding.get(key) != current.get(key)]
    if opening_new_cycle and isinstance(binding.get("pin_epoch"), int) and isinstance(current.get("pin_epoch"), int) and binding["pin_epoch"] < current["pin_epoch"]:
        codes.append("MF-POLICY-PIN-EPOCH-STALE")
    return codes


def policy_epoch_findings(binding: dict[str, Any], profile_epoch: int, request: dict[str, Any] | None, *, opening_new_cycle: bool, current_profile_sha256: str | None = None) -> list[str]:
    """Apply epoch softening: only a newly opened cycle is held for rebind."""
    pending = (
        isinstance(request, dict)
        and request.get("status") == "pending"
        and request.get("pin_epoch") == profile_epoch
        and (current_profile_sha256 is None or request.get("profile_sha256") == current_profile_sha256)
    )
    stale = isinstance(binding.get("pin_epoch"), int) and binding["pin_epoch"] < profile_epoch
    return ["MF-POLICY-PIN-EPOCH-STALE"] if opening_new_cycle and (stale or pending) else []


def _validate_unavailable_reader_accessibility(
    project_root: Path,
    binding: dict[str, Any],
    milestones: dict[str, Any],
    deliverables: dict[str, dict[str, Any] | None],
    findings: list[Finding],
    evidence: list[dict[str, Any]],
    skipped_checks: list[dict[str, str]],
) -> None:
    """Validate an M1-only, fail-closed binding to a structural base graph."""
    base = "milestone_framework.policy_bindings.reader_accessibility"
    try:
        resolve_policy(project_root)
    except PolicyError as exc:
        reason = str(exc)
        if not reason.startswith("GRAPH-SEMANTIC-INELIGIBLE:"):
            findings.append(_finding(
                "MF-POLICY", base,
                f"cannot re-derive unavailable reader policy: {exc}",
            ))
            return
        try:
            expected = resolve_unavailable_policy(project_root, reason)
        except PolicyError as unavailable_exc:
            findings.append(_finding(
                "MF-POLICY", base,
                f"cannot bind the structural graph observation: {unavailable_exc}",
            ))
            return
    else:
        findings.append(_finding(
            "MF-POLICY-REBIND-REQUIRED", base,
            "the semantic graph is eligible again; Planner must apply a governed reader-policy rebind",
        ))
        return

    skipped_checks.append({
        "check": "reader_accessibility_policy_semantic_rederivation",
        "mode": "m1-only-structural-fallback",
        "reason": reason,
        "status": f"SKIPPED({reason})",
    })
    resolved_bytes = _file_binding(
        project_root,
        binding.get("resolved_path"),
        binding.get("resolved_sha256"),
        None,
        f"{base}.resolved_path",
        findings,
        evidence,
        "MF-POLICY",
    )
    try:
        recorded = json.loads(resolved_bytes) if resolved_bytes is not None else None
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        findings.append(_finding(
            "MF-POLICY", f"{base}.resolved_path",
            f"unavailable policy artifact must be valid JSON: {exc}",
        ))
        return
    if recorded != expected:
        findings.append(_finding(
            "MF-POLICY", f"{base}.resolved_path",
            "unavailable policy artifact differs from the current structural graph and policy inputs",
        ))
    expected_binding = {
        "availability": "semantic_graph_unavailable",
        "profile_path": expected["profile_path"],
        "profile_sha256": expected["profile_sha256"],
        "resolved_path": binding.get("resolved_path"),
        "resolved_sha256": binding.get("resolved_sha256"),
        "source_bindings": expected["source_bindings"],
        "project_identity": expected.get("project_identity"),
        "blocker": expected["blocker"],
        "transitions": {
            key: {"state": "active", "observed_count": 0, "last_event_sequence": None, "events": []}
            for key in ("G", "H", "VE")
        },
    }
    if binding != expected_binding:
        findings.append(_finding(
            "MF-POLICY", base,
            "unavailable binding does not exactly project the current policy and graph observation",
        ))

    m1 = milestones.get("M1")
    m1_policy = m1.get("policy_evidence") if isinstance(m1, dict) else None
    if not isinstance(m1_policy, dict) or m1_policy.get("reader_model") != expected["resolved_profile"]["domain_native_register"]["reader_model"]:
        findings.append(_finding(
            "MF-POLICY", "milestone_framework.milestones.M1.policy_evidence",
            "M1 must retain the canonical reader model while graph semantics are unavailable",
        ))
    if isinstance(m1, dict) and (
        m1.get("status") != "in_progress"
        or m1.get("approval", {}).get("status") != "pending"
        or m1.get("handoff", {}).get("status") != "not_ready"
    ):
        findings.append(_finding(
            "MF-POLICY-SEMANTIC-UNAVAILABLE", "milestone_framework.milestones.M1",
            "M1 may be planned and researched, but cannot be accepted or handed off until semantic reader policy is rebound",
        ))
    for milestone in ("M2", "M3", "M4", "M5"):
        record = milestones.get(milestone)
        if isinstance(record, dict) and record.get("status") not in {"not_started", "not_applicable"}:
            findings.append(_finding(
                "MF-POLICY-SEMANTIC-UNAVAILABLE",
                f"milestone_framework.milestones.{milestone}",
                f"{milestone} cannot start while the semantic reader-policy binding is unavailable",
            ))


def _validate_reader_profile_binding(
    project_root: Path,
    ledger: dict[str, Any],
    binding: dict[str, Any],
    milestones: dict[str, Any],
    deliverables: dict[str, dict[str, Any] | None],
    findings: list[Finding],
    evidence: list[dict[str, Any]],
) -> None:
    """Validate graph-independent reader policy without invoking Graphify."""
    base = "milestone_framework.policy_bindings.reader_accessibility"
    try:
        expected = resolve_reader_profile(project_root)
    except PolicyError as exc:
        findings.append(_finding("MF-POLICY", base, f"cannot re-derive reader profile: {exc}"))
        return
    resolved_bytes = _file_binding(
        project_root, binding.get("resolved_path"), binding.get("resolved_sha256"), None,
        f"{base}.resolved_path", findings, evidence, "MF-POLICY",
    )
    try:
        recorded = json.loads(resolved_bytes) if resolved_bytes is not None else None
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        findings.append(_finding("MF-POLICY", f"{base}.resolved_path", f"reader-profile artifact must be valid JSON: {exc}"))
        return
    if recorded != expected:
        findings.append(_finding(
            "MF-POLICY", f"{base}.resolved_path",
            "reader-profile artifact differs from current package/project policy sources",
        ))
    projected = {
        "binding_version": "2.0.0",
        "binding_kind": "reader_profile",
        "semantic_usage": "not_invoked",
        "profile_path": expected["profile_path"],
        "profile_sha256": expected["profile_sha256"],
        "resolved_path": binding.get("resolved_path"),
        "resolved_sha256": binding.get("resolved_sha256"),
        "source_bindings": expected["source_bindings"],
        "project_identity": expected.get("project_identity"),
        "transitions": binding.get("transitions"),
    }
    if binding != projected:
        findings.append(_finding("MF-POLICY", base, "v2 reader-profile binding is stale or malformed"))
    for index, source in enumerate(binding.get("source_bindings", [])):
        if not isinstance(source, dict):
            continue
        owner = ROOT if source.get("scope") == "package" else project_root
        candidate = (owner / str(source.get("path"))).resolve()
        try:
            candidate.relative_to(owner.resolve())
        except ValueError:
            findings.append(_finding("MF-POLICY", f"{base}.source_bindings[{index}]", "source binding escapes declared root"))
            continue
        if not candidate.is_file() or hashlib.sha256(candidate.read_bytes()).hexdigest() != source.get("sha256"):
            findings.append(_finding("MF-POLICY", f"{base}.source_bindings[{index}]", "reader-profile source is missing or stale"))

    def started(name: str) -> bool:
        record = milestones.get(name)
        return isinstance(record, dict) and record.get("status") not in {"not_started", "not_applicable", "legacy_unverified"}

    reader_model = expected["resolved_profile"]["domain_native_register"]["reader_model"]
    m1_policy = milestones.get("M1", {}).get("policy_evidence") if isinstance(milestones.get("M1"), dict) else None
    if started("M1") and (
        not isinstance(m1_policy, dict)
        or (ledger.get("mode") == "native" and m1_policy.get("reader_model") != reader_model)
    ):
        findings.append(_finding("MF-POLICY", "milestone_framework.milestones.M1.policy_evidence", "native M1 must record the canonical domain-native reader_model"))

    stable = {
        "profile_path": binding.get("resolved_path"),
        "profile_sha256": binding.get("profile_sha256"),
        "resolved_sha256": binding.get("resolved_sha256"),
        "semantic_usage": "not_invoked",
    }
    for milestone in ("M3", "M4", "M5"):
        if not started(milestone):
            continue
        policy = milestones[milestone].get("policy_evidence")
        if not isinstance(policy, dict) or any(policy.get(key) != value for key, value in stable.items()):
            findings.append(_finding(
                "MF-POLICY", f"milestone_framework.milestones.{milestone}.policy_evidence",
                f"{milestone} must bind the current reader profile and declare semantic_usage not_invoked",
            ))
        if isinstance(policy, dict) and any(key in policy for key in ("attestation_view_pin", "exemplar_view_pin")):
            findings.append(_finding(
                "GRAPH_GOVERNED_GENERATION_UNAVAILABLE",
                f"milestone_framework.milestones.{milestone}.policy_evidence",
                "semantic graph pins cannot be asserted by a graph-independent reader-profile binding",
            ))
        if milestone not in {"M4", "M5"} or not isinstance(policy, dict):
            continue
        record = milestones[milestone]
        deliverable = deliverables.get(milestone)
        accepted = record.get("status") in {"accepted", "superseded"} or record.get("handoff", {}).get("status") in {"ready", "consumed"}
        required = list(stable)
        if isinstance(deliverable, dict):
            required.extend(("manuscript_sha256", "phase", "cycle_id"))
        if accepted:
            required.extend(("check8_path", "check8_sha256", "aggregate_verdict"))
        if any(policy.get(key) is None for key in required):
            findings.append(_finding(
                "MF-POLICY", f"milestone_framework.milestones.{milestone}.policy_evidence",
                f"{milestone} reader-profile evidence is incomplete for its current lifecycle state",
            ))
            continue
        if not accepted:
            continue
        check8_bytes = _file_binding(
            project_root, policy.get("check8_path"), policy.get("check8_sha256"), None,
            f"milestone_framework.milestones.{milestone}.policy_evidence.check8_path",
            findings, evidence, "MF-POLICY",
        )
        try:
            check8 = json.loads(check8_bytes) if check8_bytes is not None else None
            if not isinstance(check8, dict):
                raise PolicyError("Check 8 evidence must be an object")
            validate_check8_evidence(check8)
        except (UnicodeDecodeError, json.JSONDecodeError, PolicyError) as exc:
            findings.append(_finding(
                "MF-POLICY", f"milestone_framework.milestones.{milestone}.policy_evidence.check8_path",
                f"invalid graph-independent Check 8 evidence: {exc}",
            ))
            continue
        expected_phase = "Ph3" if milestone == "M4" else "Ph4"
        transition_snapshot = {
            key: binding.get("transitions", {}).get(key, {}).get("state")
            for key in ("G", "H", "VE")
        }
        expected_check8 = {
            "schema_version": "check8_evidence.v2",
            "semantic_usage": "not_invoked",
            "profile_path": binding.get("resolved_path"),
            "profile_sha256": binding.get("profile_sha256"),
            "manuscript_sha256": deliverable.get("sha256") if isinstance(deliverable, dict) else None,
            "phase": expected_phase,
            "cycle_id": policy.get("cycle_id"),
            "transition_snapshot": transition_snapshot,
        }
        mismatched_check8 = [
            key for key, value in expected_check8.items() if check8.get(key) != value
        ]
        if mismatched_check8:
            findings.append(_finding(
                "MF-POLICY", f"milestone_framework.milestones.{milestone}.policy_evidence.check8_path",
                "Check 8 v2 does not bind the current reader profile, manuscript, phase, cycle, and transitions; "
                f"mismatched fields: {mismatched_check8}",
            ))
        _file_binding(
            project_root, check8.get("manuscript_path"), check8.get("manuscript_sha256"), None,
            f"milestone_framework.milestones.{milestone}.policy_evidence.check8_path.manuscript_path",
            findings, evidence, "MF-POLICY",
        )
        try:
            recomputed = recompute_check8(check8, binding.get("transitions", {}))
        except PolicyError as exc:
            findings.append(_finding("MF-POLICY", f"milestone_framework.milestones.{milestone}.policy_evidence.check8_path", str(exc)))
            continue
        if (
            check8.get("subcheck_verdicts") != recomputed["subcheck_verdicts"]
            or check8.get("aggregate_verdict") != recomputed["aggregate_verdict"]
            or policy.get("aggregate_verdict") != recomputed["aggregate_verdict"]
        ):
            findings.append(_finding(
                "MF-POLICY", f"milestone_framework.milestones.{milestone}.policy_evidence.check8_path",
                "Check 8 v2 verdicts do not match deterministic recomputation",
            ))


def _validate_reader_accessibility_policy(
    project_root: Path,
    ledger: dict[str, Any],
    milestones: dict[str, Any],
    deliverables: dict[str, dict[str, Any] | None],
    findings: list[Finding],
    evidence: list[dict[str, Any]],
    skipped_checks: list[dict[str, str]],
    opening_new_cycle: bool,
) -> None:
    bindings = ledger.get("policy_bindings")
    if not isinstance(bindings, dict) or "reader_accessibility" not in bindings:
        if ledger.get("mode") == "native":
            findings.append(_finding("MF-POLICY", "milestone_framework.policy_bindings.reader_accessibility", "native projects must initialize the reader-accessibility binding at bootstrap"))
        return
    binding = bindings.get("reader_accessibility")
    base = "milestone_framework.policy_bindings.reader_accessibility"
    if not isinstance(binding, dict):
        findings.append(_finding("MF-POLICY", base, "reader-accessibility policy binding must be an object"))
        return
    if binding.get("binding_version") == "2.0.0":
        _validate_reader_profile_binding(
            project_root, ledger, binding, milestones, deliverables, findings, evidence,
        )
        return
    if binding.get("availability") == "semantic_graph_unavailable":
        _validate_unavailable_reader_accessibility(
            project_root, binding, milestones, deliverables, findings, evidence, skipped_checks,
        )
        return
    resolved_bytes: bytes | None = None
    resolved_payload: Any = None
    try:
        expected_resolved = resolve_policy(project_root)
    except PolicyError as exc:
        reason = str(exc)
        if not reason.startswith("GRAPH-SEMANTIC-INELIGIBLE:"):
            findings.append(_finding("MF-POLICY", base, f"cannot re-derive resolved policy: {exc}"))
            return
        skipped_checks.append({
            "check": "reader_accessibility_policy_semantic_rederivation",
            "mode": "structural-fallback",
            "reason": reason,
            "status": f"SKIPPED({reason})",
        })
        resolved_bytes = _file_binding(
            project_root, binding.get("resolved_path"), binding.get("resolved_sha256"), None,
            f"{base}.resolved_path", findings, evidence, "MF-POLICY",
        )
        try:
            resolved_payload = json.loads(resolved_bytes) if resolved_bytes is not None else None
        except (UnicodeDecodeError, json.JSONDecodeError) as parse_exc:
            findings.append(_finding("MF-POLICY", f"{base}.resolved_path", f"resolved policy artifact must be valid JSON: {parse_exc}"))
            return
        if not isinstance(resolved_payload, dict):
            findings.append(_finding("MF-POLICY", f"{base}.resolved_path", "structural fallback requires a valid bound resolved policy object"))
            return
        expected_resolved = resolved_payload
    for index, source in enumerate(binding.get("source_bindings", [])):
        if not isinstance(source, dict) or source.get("scope") not in {"package", "project"} or not isinstance(source.get("path"), str):
            findings.append(_finding("MF-POLICY", f"{base}.source_bindings[{index}]", "malformed scoped source binding")); return
        owner = ROOT if source["scope"] == "package" else project_root
        candidate = (owner / source["path"]).resolve()
        try: candidate.relative_to(owner.resolve())
        except ValueError:
            findings.append(_finding("MF-POLICY", f"{base}.source_bindings[{index}]", "source binding escapes declared root")); return
    canonical = ROOT / "references" / "policies" / "reader_accessibility.v1.json"
    expected_path = "references/policies/reader_accessibility.v1.json"
    canonical_hash = hashlib.sha256(canonical.read_bytes()).hexdigest() if canonical.is_file() else None
    profile_expected = expected_resolved.get("resolved_profile", {}).get("domain_native_register", {}).get("expected_verification", {})
    current_policy = {"profile_sha256": canonical_hash, "attestation_view_pin": expected_resolved.get("attestation_view_pin"), "exemplar_view_pin": expected_resolved.get("exemplar_view_pin"), "pin_epoch": profile_expected.get("pin_epoch")}
    epoch_gap = isinstance(binding.get("pin_epoch"), int) and isinstance(profile_expected.get("pin_epoch"), int) and binding["pin_epoch"] < profile_expected["pin_epoch"]
    recorded_register = binding.get("register_provenance")
    legacy_projection = isinstance(recorded_register, dict) and any(
        key not in recorded_register
        for key in ("exemplar_members", "surface_exemplar_members", "argument_exemplar_members")
    )
    continuing_semantic_compatibility = (
        not opening_new_cycle
        and legacy_projection
        and binding.get("profile_sha256") in LEGACY_READER_PROFILE_HASHES
        and binding.get("attestation_view_pin") == current_policy["attestation_view_pin"]
        and binding.get("exemplar_view_pin") == current_policy["exemplar_view_pin"]
    )
    if binding.get("profile_path") != expected_path or not canonical.is_file():
        findings.append(_finding("MF-POLICY-PROFILE-STALE", f"{base}.profile_path", "profile path must bind the canonical package profile"))
    elif not (epoch_gap or continuing_semantic_compatibility):
        messages = {
            "MF-POLICY-PROFILE-STALE": ("profile_sha256", "stored policy hash differs from the current package profile"),
            "MF-POLICY-ATTESTATION-PIN-STALE": ("attestation_view_pin", "attestation semantic view changed; deliberate versioned repin required"),
            "MF-POLICY-EXEMPLAR-PIN-STALE": ("exemplar_view_pin", "exemplar semantic view changed; deliberate versioned repin required"),
        }
        for code in reader_policy_staleness_codes(binding, current_policy, opening_new_cycle=False):
            field, message = messages[code]
            findings.append(_finding(code, f"{base}.{field}", message))
    request_path = project_root / "reviews/repin_rebind_request.json"
    request = None
    if request_path.is_file():
        try:
            request = json.loads(request_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            request = {"status": "pending"}
    if isinstance(profile_expected.get("pin_epoch"), int):
        for code in policy_epoch_findings(binding, profile_expected["pin_epoch"], request, opening_new_cycle=opening_new_cycle, current_profile_sha256=canonical_hash):
            findings.append(_finding(code, f"{base}.pin_epoch", "binding epoch predates the current profile epoch; Planner must apply the pending rebind before opening a new cycle"))
    if resolved_bytes is None:
        resolved_bytes = _file_binding(project_root, binding.get("resolved_path"), binding.get("resolved_sha256"), None, f"{base}.resolved_path", findings, evidence, "MF-POLICY")
        try:
            resolved_payload = json.loads(resolved_bytes) if resolved_bytes is not None else None
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            findings.append(_finding("MF-POLICY", f"{base}.resolved_path", f"resolved policy artifact must be valid JSON: {exc}"))
            resolved_payload = None
    stable_keys = ("profile_path", "profile_sha256", "source_bindings", "project_identity", "register_class", "passage_scope_class", "resolved_profile", "attestation_view_pin", "exemplar_view_pin")
    if not isinstance(resolved_payload, dict) or (not (epoch_gap or continuing_semantic_compatibility) and any(resolved_payload.get(key) != expected_resolved.get(key) for key in stable_keys)):
        findings.append(_finding("MF-POLICY", f"{base}.resolved_path", "resolved policy gate projection differs from fresh resolver output"))
    recorded_provenance = binding.get("register_provenance")
    fresh_provenance = expected_resolved.get("register_provenance")
    invariant_keys = ("register_class", "attestation_view_pin", "exemplar_view_pin", "seed_resolution_map", "seed_resolution_ties", "unresolved_seed_ids", "primary_communities", "attestation_member_ids", "exemplar_hash_lines", "exemplar_members", "surface_exemplar_members", "argument_exemplar_members", "warnings")
    def provenance_paths(value: Any) -> list[tuple[Any, Any, Any]]:
        if not isinstance(value, dict) or not isinstance(value.get("provenance"), list): return []
        return sorted((entry.get("role"), entry.get("path"), entry.get("sha256")) for entry in value["provenance"] if isinstance(entry, dict) and entry.get("role") != "graph_provenance_only")
    if not isinstance(recorded_provenance, dict) or (not (epoch_gap or continuing_semantic_compatibility) and (not isinstance(fresh_provenance, dict) or any(recorded_provenance.get(key) != fresh_provenance.get(key) for key in invariant_keys) or provenance_paths(recorded_provenance) != provenance_paths(fresh_provenance))):
        findings.append(_finding("MF-POLICY-PROVENANCE", f"{base}.register_provenance", "semantic register provenance projection is incomplete or inconsistent with the fresh resolver"))
    for index, source in enumerate(binding.get("source_bindings", [])):
        if not isinstance(source, dict):
            continue
        relative = source.get("path")
        scope = source.get("scope")
        if scope == "package":
            package_source = (ROOT / str(relative)).resolve()
            try: package_source.relative_to(ROOT.resolve())
            except ValueError:
                findings.append(_finding("MF-POLICY", f"{base}.source_bindings[{index}]", "package policy contributor escapes package root"))
                continue
            if not package_source.is_file() or (not (epoch_gap or continuing_semantic_compatibility) and hashlib.sha256(package_source.read_bytes()).hexdigest() != source.get("sha256")):
                findings.append(_finding("MF-POLICY", f"{base}.source_bindings[{index}]", "package policy contributor is missing or stale"))
        elif scope == "project":
            _file_binding(project_root, relative, source.get("sha256"), None, f"{base}.source_bindings[{index}]", findings, evidence, "MF-POLICY")
        else:
            findings.append(_finding("MF-POLICY", f"{base}.source_bindings[{index}].scope", "policy source binding must declare package or project scope"))
    try:
        profile = json.loads(canonical.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        profile = {"transitions": {}}
    for key in ("G", "H", "VE"):
        state = binding.get("transitions", {}).get(key, {})
        required_count = profile.get("transitions", {}).get(key, {}).get("required_observed_count")
        events = state.get("events", []) if isinstance(state, dict) else []
        for event_index, event in enumerate(events):
            if isinstance(event, dict):
                _file_binding(project_root, event.get("evidence_path"), event.get("evidence_sha256"), None, f"{base}.transitions.{key}.events[{event_index}].evidence_path", findings, evidence, "MF-POLICY")
        sequences = [event.get("sequence") for event in events if isinstance(event, dict)]
        if sequences != sorted(set(sequences)):
            findings.append(_finding("MF-POLICY", f"{base}.transitions.{key}.events", "transition events must be append-only with unique increasing sequence"))
        observed_events = [event for event in events if isinstance(event, dict) and event.get("event") == "policy_transition_observed" and event.get("approved") is True]
        expected_counts = list(range(1, len(observed_events) + 1))
        observed_counts = [event.get("observed_count") for event in observed_events]
        cycle_ids = [event.get("cycle_id") for event in observed_events]
        manuscript_ids = [event.get("manuscript_sha256") for event in observed_events]
        content_ids = [(event.get("manuscript_sha256"), event.get("content_sha256")) for event in observed_events]
        distinct_observations = len(cycle_ids) == len(set(cycle_ids))
        if key == "G":
            distinct_observations = distinct_observations and len(manuscript_ids) == len(set(manuscript_ids))
        else:
            distinct_observations = distinct_observations and len(content_ids) == len(set(content_ids))
        if observed_counts != expected_counts or not distinct_observations:
            findings.append(_finding("MF-POLICY", f"{base}.transitions.{key}.events", "observations must advance one count per distinct cycle and use distinct bound manuscript/content evidence"))
        observed_count = len(observed_events)
        if state.get("observed_count") != observed_count:
            findings.append(_finding("MF-POLICY", f"{base}.transitions.{key}.observed_count", "transition counter must derive from approved Planner observation events"))
        expected_last = sequences[-1] if sequences else None
        if state.get("last_event_sequence") != expected_last:
            findings.append(_finding("MF-POLICY", f"{base}.transitions.{key}.last_event_sequence", "last event sequence must exactly project the append-only event stream"))
        if state.get("state") == "retired":
            retirement = [event for event in events if isinstance(event, dict) and event.get("event") == "planner_transition_approved" and event.get("approved") is True and event.get("observed_count") == required_count]
            after_observations = bool(retirement and observed_events and retirement[-1].get("sequence", 0) > observed_events[-1].get("sequence", 0) and retirement[-1] is events[-1])
            if state.get("observed_count") != required_count or len(retirement) != 1 or not after_observations:
                findings.append(_finding("MF-POLICY", f"{base}.transitions.{key}", "retirement requires the profile count and matching Planner-owned approval evidence"))
        elif any(isinstance(event, dict) and event.get("event") == "planner_transition_approved" for event in events):
            findings.append(_finding("MF-POLICY", f"{base}.transitions.{key}", "active transition cannot contain a retirement approval event"))
    def started(name: str) -> bool:
        record = milestones.get(name)
        return isinstance(record, dict) and record.get("status") not in {"not_started", "not_applicable", "legacy_unverified"}
    m1 = milestones.get("M1", {}).get("policy_evidence") if isinstance(milestones.get("M1"), dict) else None
    expected_reader = expected_resolved["resolved_profile"]["domain_native_register"]["reader_model"]
    if started("M1") and (not isinstance(m1, dict) or (ledger.get("mode") == "native" and m1.get("reader_model") != expected_reader) or (ledger.get("mode") != "native" and not (m1.get("reader_model") or m1.get("intended_readers")))):
        findings.append(_finding("MF-POLICY", "milestone_framework.milestones.M1.policy_evidence", "native M1 must record the canonical domain-native reader_model"))
    m3 = milestones.get("M3", {}).get("policy_evidence") if isinstance(milestones.get("M3"), dict) else None
    if started("M3") and (not isinstance(m3, dict) or m3.get("profile_path") != binding.get("resolved_path") or m3.get("profile_sha256") != binding.get("profile_sha256") or m3.get("resolved_sha256") != binding.get("resolved_sha256") or m3.get("attestation_view_pin") != binding.get("attestation_view_pin") or m3.get("exemplar_view_pin") != binding.get("exemplar_view_pin")):
        findings.append(_finding("MF-POLICY", "milestone_framework.milestones.M3.policy_evidence", "M3 must bind profile, resolved configuration, and both semantic register pins"))
    for milestone in ("M4", "M5"):
        record = milestones.get(milestone)
        if not started(milestone):
            if isinstance(record, dict) and record.get("policy_evidence") is not None:
                findings.append(_finding("MF-POLICY", f"milestone_framework.milestones.{milestone}.policy_evidence", "future not-started milestones must not fabricate policy evidence"))
            continue
        policy = record.get("policy_evidence") if isinstance(record, dict) else None
        deliverable = deliverables.get(milestone)
        path = f"milestone_framework.milestones.{milestone}.policy_evidence"
        accepted = record.get("status") in {"accepted", "superseded"} or record.get("handoff", {}).get("status") in {"ready", "consumed"}
        stable_required = (
            "profile_path", "profile_sha256", "resolved_sha256",
            "attestation_view_pin", "exemplar_view_pin",
        )
        # M4 begins before its first manuscript bytes exist. At that boundary
        # the Planner can bind only stable profile/register pins. The first
        # deliverable_recorded transaction must add all manuscript-bound fields
        # atomically. M5 likewise starts by consuming M4's F9, then binds its
        # distinct FINAL manuscript on the first scoped publication record.
        manuscript_required = ("manuscript_sha256", "phase", "cycle_id")
        has_deliverable = isinstance(deliverable, dict)
        required = stable_required
        if has_deliverable:
            required += manuscript_required
        if accepted:
            required += ("check8_path", "check8_sha256", "aggregate_verdict")
        if not isinstance(policy, dict) or any(policy.get(key) is None for key in required):
            findings.append(_finding("MF-POLICY", path, f"{milestone} must carry complete current-manuscript Check 8 policy evidence"))
            continue
        if milestone == "M4" and not has_deliverable and set(policy) != set(stable_required):
            findings.append(_finding(
                "MF-POLICY", path,
                "M4 before its first deliverable must carry exactly the five stable policy pins and no manuscript-bound fields",
            ))
        if accepted and milestone == "M4" and (
            policy.get("phase") != "Ph3"
            or policy.get("aggregate_verdict") not in {"CLEAN", "BORDERLINE"}
        ):
            findings.append(_finding(
                "MF-POLICY", path,
                "accepted M4 requires phase Ph3 and a CLEAN or BORDERLINE Check 8 aggregate",
            ))
        if accepted and milestone == "M5" and (
            policy.get("phase") != "Ph4"
            or policy.get("aggregate_verdict") not in {"CLEAN", "BORDERLINE"}
        ):
            findings.append(_finding(
                "MF-POLICY", path,
                "accepted M5 requires phase Ph4 and a CLEAN or BORDERLINE Check 8 aggregate",
            ))
        if policy.get("profile_path") != binding.get("resolved_path") or policy.get("profile_sha256") != binding.get("profile_sha256") or policy.get("resolved_sha256") != binding.get("resolved_sha256") or policy.get("attestation_view_pin") != binding.get("attestation_view_pin") or policy.get("exemplar_view_pin") != binding.get("exemplar_view_pin"):
            findings.append(_finding("MF-POLICY", path, f"{milestone} resolved policy binding is stale or differently configured"))
        if has_deliverable and policy.get("manuscript_sha256") != deliverable.get("sha256"):
            findings.append(_finding("MF-POLICY", path, f"{milestone} Check 8 evidence is not bound to the current manuscript hash"))
        if accepted:
            check_bytes = _file_binding(project_root, policy.get("check8_path"), policy.get("check8_sha256"), None, f"{path}.check8_path", findings, evidence, "MF-POLICY")
            try:
                sidecar = json.loads(check_bytes) if check_bytes is not None else None
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                findings.append(_finding("MF-POLICY", f"{path}.check8_path", f"Check 8 sidecar must be canonical JSON: {exc}"))
                continue
            if sidecar is None:
                continue
            try:
                validate_check8_evidence(sidecar)
                recomputed = recompute_check8(sidecar, binding.get("transitions", {}))
            except PolicyError as exc:
                findings.append(_finding("MF-POLICY", f"{path}.check8_path", f"invalid structured Check 8 evidence: {exc}")); continue
            expected_sidecar = {"cycle_id": policy.get("cycle_id"), "profile_path": policy.get("profile_path"), "profile_sha256": policy.get("profile_sha256"), "attestation_view_pin": policy.get("attestation_view_pin"), "exemplar_view_pin": policy.get("exemplar_view_pin"), "manuscript_sha256": policy.get("manuscript_sha256"), "phase": policy.get("phase"), "aggregate_verdict": policy.get("aggregate_verdict")}
            transition_snapshot = {key: binding.get("transitions", {}).get(key, {}).get("state") for key in ("G", "H", "VE")}
            if any(sidecar.get(key) != value for key, value in expected_sidecar.items()) or sidecar.get("aggregate_verdict") != recomputed["aggregate_verdict"] or sidecar.get("subcheck_verdicts") != recomputed["subcheck_verdicts"] or sidecar.get("transition_snapshot") != transition_snapshot:
                findings.append(_finding("MF-POLICY", f"{path}.check8_path", "Check 8 content does not match evidence fields or recomputed A-H aggregate"))


def _is_reparse(path: Path) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    return path.is_symlink() or bool(getattr(info, "st_file_attributes", 0) & REPARSE_POINT)


def _stamp(info: os.stat_result) -> tuple[int, int, int, int]:
    # Opening a file can advance st_ctime_ns on Windows; descriptor identity,
    # size, and modification time remain stable and catch path replacement.
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def _descriptor_stamp(info: os.stat_result) -> tuple[int, int, int, int, int]:
    return (*_stamp(info), info.st_ctime_ns)


class _SnapshotError(RuntimeError):
    """Controlled refusal for an unstable or unsafe exemplar input."""


@dataclass(frozen=True)
class _StableSnapshot:
    path: Path
    role: str
    data: bytes
    stamp: tuple[int, int, int, int]


class _StableSnapshotReader:
    """Capture each input once while binding raw path and open descriptor identity."""

    def __init__(self, hook: Callable[[str, str, Path], None] | None = None):
        self._hook = hook
        self._items: dict[Path, _StableSnapshot] = {}

    @staticmethod
    def _raw_components(path: Path) -> list[Path]:
        current = path.absolute()
        components = [current]
        while current.parent != current:
            current = current.parent
            components.append(current)
        return list(reversed(components))

    @classmethod
    def _check_raw_path(cls, path: Path) -> None:
        for component in cls._raw_components(path):
            try:
                if _is_reparse(component):
                    raise _SnapshotError(f"reparse component is forbidden in exemplar input: {component}")
            except OSError as exc:
                raise _SnapshotError(f"unsafe exemplar path component: {component}: {exc}") from exc

    def _notify(self, stage: str, role: str, path: Path) -> None:
        if self._hook is None:
            return
        try:
            self._hook(stage, role, path)
        except Exception as exc:
            raise _SnapshotError(f"exemplar snapshot hook failed at {stage}: {role}: {path}: {exc}") from exc

    def capture(self, path: Path, role: str) -> _StableSnapshot:
        lexical = path.absolute()
        cached = self._items.get(lexical)
        if cached is not None:
            self._verify(cached)
            return cached
        try:
            self._check_raw_path(lexical)
            pre_path = lexical.stat()
            if not stat.S_ISREG(pre_path.st_mode):
                raise _SnapshotError(f"exemplar input is not a regular file: {lexical}")
            pre_stamp = _stamp(pre_path)
            resolved = lexical.resolve(strict=True)
            self._notify("after_path_check", role, lexical)
            with lexical.open("rb") as stream:
                before = os.fstat(stream.fileno())
                if not stat.S_ISREG(before.st_mode) or _stamp(before) != pre_stamp:
                    raise _SnapshotError(f"exemplar input changed after path check: {role}: {lexical}")
                self._notify("during_read", role, lexical)
                data = stream.read()
                after = os.fstat(stream.fileno())
            if _descriptor_stamp(before) != _descriptor_stamp(after) or len(data) != before.st_size:
                raise _SnapshotError(f"exemplar input changed during read: {role}: {lexical}")
            self._check_raw_path(lexical)
            if lexical.resolve(strict=True) != resolved or _stamp(lexical.stat()) != pre_stamp:
                raise _SnapshotError(f"exemplar path identity changed during validation: {role}: {lexical}")
            snapshot = _StableSnapshot(lexical, role, data, pre_stamp)
            self._items[lexical] = snapshot
            return snapshot
        except _SnapshotError:
            raise
        except (OSError, RuntimeError) as exc:
            raise _SnapshotError(f"exemplar input is unreadable or unstable: {role}: {lexical}: {exc}") from exc

    def _verify(self, snapshot: _StableSnapshot) -> None:
        try:
            self._check_raw_path(snapshot.path)
            if _stamp(snapshot.path.stat()) != snapshot.stamp:
                raise _SnapshotError(f"exemplar input changed after capture: {snapshot.role}: {snapshot.path}")
        except _SnapshotError:
            raise
        except OSError as exc:
            raise _SnapshotError(f"exemplar input changed after capture: {snapshot.role}: {snapshot.path}: {exc}") from exc

    def verify_all(self) -> None:
        for snapshot in self._items.values():
            self._verify(snapshot)


def _has_reparse_component(path: Path) -> bool:
    current = path.absolute()
    parts = [current]
    while current.parent != current:
        current = current.parent
        parts.append(current)
    return any(part.exists() and _is_reparse(part) for part in reversed(parts))


def _strict_utc(value: Any) -> bool:
    if not isinstance(value, str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z", value) is None:
        return False
    try:
        datetime.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return True


def _project_evidence(
    project_root: Path, relative: Any, expected_sha: Any, field: str,
    findings: list[Finding], evidence: list[dict[str, Any]], snapshots: _StableSnapshotReader,
) -> bytes | None:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
        findings.append(_finding("MF-EXEMPLAR", field, "evidence path must be a relative path contained by the registered project"))
        return None
    lexical = project_root / relative
    candidate = _canonical_path(project_root, relative)
    if candidate is None or _has_reparse_component(lexical) or not candidate.is_file():
        findings.append(_finding("MF-EXEMPLAR", field, "evidence path must resolve to a regular non-reparse file inside the registered project"))
        return None
    try:
        payload = snapshots.capture(lexical, Path(relative).stem).data
    except _SnapshotError as exc:
        findings.append(_finding("MF-EXEMPLAR", field, str(exc)))
        return None
    actual = hashlib.sha256(payload).hexdigest()
    if not isinstance(expected_sha, str) or re.fullmatch(r"[0-9a-f]{64}", expected_sha) is None or actual != expected_sha:
        findings.append(_finding("MF-EXEMPLAR", field, "exemplar evidence hash does not match current bytes"))
        return payload
    evidence.append({"path": relative, "sha256": actual, "bytes": len(payload)})
    return payload


def _ledger_exemplar_claims(
    value: Any, path: str = "milestone_framework", identities: tuple[str, ...] = (),
) -> list[str]:
    claims: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if re.fullmatch(r"(?:exemplar_(?:status|class)|portfolio_exemplar|reference_implementation)", str(key), re.IGNORECASE):
                claims.append(child_path)
            claims.extend(_ledger_exemplar_claims(child, child_path, identities))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            claims.extend(_ledger_exemplar_claims(child, f"{path}[{index}]", identities))
    elif isinstance(value, str) and _contains_normative_exemplar_claim(value, identities):
        claims.append(path)
    return claims


def _contains_normative_exemplar_claim(text: str, identities: tuple[str, ...] = ()) -> bool:
    credential = r"(?:clean[ _-]lifecycle[ _-]exemplar|legacy[ _-]migration[ _-]exemplar|portfolio\s+exemplar|reference\s+implementation)"
    aliases = [re.escape(item) for item in identities if isinstance(item, str) and item.strip()]
    subject_parts = [r"this\s+project", r"the\s+project", *aliases]
    subject = r"(?:" + "|".join(subject_parts) + r")"
    verb = r"(?:is|remains|serves\s+as|has\s+been\s+designated\s+as|is\s+designated\s+as|is\s+registered\s+as)"
    declaration = re.compile(rf"(?i)\b{subject}\s+{verb}\s+(?:an?\s+|the\s+)?{credential}\b")
    heading = re.compile(rf"(?i)^\s*#{{1,6}}\s*{credential}\s*$")
    status = re.compile(rf"(?i)^\s*(?:status|exemplar(?:[ _]status|[ _]class)?|portfolio[ _]status)\s*:\s*{credential}\s*$")
    table = re.compile(rf"(?i)^\s*\|\s*status\s*:?\s*\|\s*{credential}\s*\|?\s*$")
    for raw_line in text.splitlines() or [text]:
        line = re.sub(r"(?:\*\*|__|`)", "", raw_line).strip()
        if not line:
            continue
        if heading.fullmatch(line) or status.fullmatch(line) or table.fullmatch(line):
            return True
        if line.endswith("?"):
            continue
        match = declaration.search(line)
        if match is None:
            continue
        prefix = line[:match.start()].lower()
        if re.search(r"\b(?:not|never|false|whether|asks?|question(?:s|ed)?|discuss(?:es|ed)?|consider(?:s|ed)?)\b", prefix):
            continue
        return True
    return False


def _project_prose_exemplar_claims(
    project_root: Path, findings: list[Finding], identities: tuple[str, ...],
) -> None:
    # These are the declared project authority/status surfaces only.  Broad
    # manuscript/review scanning would confuse ordinary uses of "exemplar"
    # with a lifecycle credential.
    surfaces = ("AGENTS.md", "CLAUDE.md", "reviews/lifecycle_state.md")
    for relative in surfaces:
        candidate = _canonical_path(project_root, relative)
        if candidate is None or not candidate.is_file():
            continue
        try:
            text = candidate.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            findings.append(_finding("MF-EXEMPLAR", relative, f"could not inspect declared project status surface: {exc}"))
            continue
        if _contains_normative_exemplar_claim(text, identities):
            findings.append(_finding("MF-EXEMPLAR", relative, "project-local prose cannot grant or self-declare milestone exemplar status"))


def _validate_exemplar_registry(
    project_root: Path, document: dict[str, Any], registry_path: Path,
    findings: list[Finding], evidence: list[dict[str, Any]],
    snapshot_hook: Callable[[str, str, Path], None] | None = None,
) -> None:
    snapshots = _StableSnapshotReader(snapshot_hook)
    ledger = document.get("milestone_framework")
    aliases: list[str] = [project_root.resolve().name]
    manuscript_id = document.get("manuscript_id")
    if isinstance(manuscript_id, str) and manuscript_id.strip():
        aliases.append(manuscript_id.strip())
    identities = tuple(dict.fromkeys(alias for alias in aliases if alias))
    if isinstance(ledger, dict):
        for claim_path in _ledger_exemplar_claims(ledger, identities=identities):
            findings.append(_finding("MF-EXEMPLAR", claim_path, "project ledger cannot grant or self-declare milestone exemplar status"))
    _project_prose_exemplar_claims(project_root, findings, identities)

    if not registry_path.is_absolute():
        registry_path = (ROOT / registry_path).absolute()
    try:
        registry_snapshot = snapshots.capture(registry_path, "registry")
        registry = json.loads(registry_snapshot.data.decode("utf-8", errors="strict"))
    except (_SnapshotError, UnicodeError, json.JSONDecodeError) as exc:
        findings.append(_finding("MF-EXEMPLAR", str(registry_path), f"exemplar registry is not valid UTF-8 JSON: {exc}"))
        return
    if not isinstance(registry, dict) or set(registry) != {"schema_version", "entries"} or registry.get("schema_version") != "1.0.0" or not isinstance(registry.get("entries"), list):
        findings.append(_finding("MF-EXEMPLAR", str(registry_path), "registry must have exactly schema_version 1.0.0 and an entries array"))
        return

    required = {
        "project_path", "exemplar_class", "approval_authority", "approval_evidence_path",
        "approval_evidence_sha256", "validator_version", "validator_outcome",
        "validator_evidence", "registered_at", "phase_state_sha256",
    }
    canonical_project = project_root.resolve().as_posix()
    matching: list[tuple[int, dict[str, Any]]] = []
    identities: dict[str, list[tuple[int, str]]] = {}
    structurally_valid: set[int] = set()
    for index, entry in enumerate(registry["entries"]):
        base = f"{registry_path}:entries[{index}]"
        if not isinstance(entry, dict) or set(entry) != required:
            findings.append(_finding("MF-EXEMPLAR", base, "registry entry has missing or unknown fields"))
            continue
        exemplar_class = entry.get("exemplar_class")
        project_path = entry.get("project_path")
        if not isinstance(project_path, str) or not Path(project_path).is_absolute() or Path(project_path).resolve().as_posix() != project_path.replace("\\", "/"):
            findings.append(_finding("MF-EXEMPLAR", f"{base}.project_path", "project_path must be an absolute canonical path identity"))
            continue
        if exemplar_class not in EXEMPLAR_CLASSES:
            findings.append(_finding("MF-EXEMPLAR", f"{base}.exemplar_class", "unknown milestone exemplar class"))
            continue
        if entry.get("approval_authority") not in EXEMPLAR_AUTHORITIES:
            findings.append(_finding("MF-EXEMPLAR", f"{base}.approval_authority", "approval authority is not permitted to grant exemplar status"))
            continue
        expected_outcome = "READY" if exemplar_class == "clean_lifecycle_exemplar" else "LEGACY_READY"
        if entry.get("validator_outcome") != expected_outcome or not _strict_utc(entry.get("registered_at")):
            findings.append(_finding("MF-EXEMPLAR", base, "validator outcome or registration timestamp is invalid for the exemplar class"))
            continue
        if not isinstance(entry.get("validator_version"), str) or not entry["validator_version"]:
            findings.append(_finding("MF-EXEMPLAR", f"{base}.validator_version", "validator_version must be explicit"))
            continue
        validator_evidence = entry.get("validator_evidence")
        if not isinstance(validator_evidence, list) or not validator_evidence:
            findings.append(_finding("MF-EXEMPLAR", f"{base}.validator_evidence", "validator_evidence must be a non-empty array"))
            continue
        valid_items = True
        roles: list[str] = []
        for item_index, item in enumerate(validator_evidence):
            if not isinstance(item, dict) or set(item) != {"role", "path", "sha256"} or not isinstance(item.get("role"), str) or not item["role"]:
                findings.append(_finding("MF-EXEMPLAR", f"{base}.validator_evidence[{item_index}]", "evidence item must contain exactly role, path, and sha256"))
                valid_items = False
            else:
                roles.append(item["role"])
        expected_roles = EXEMPLAR_EVIDENCE_ROLES[exemplar_class]
        if not valid_items or len(roles) != len(set(roles)) or set(roles) != expected_roles:
            findings.append(_finding("MF-EXEMPLAR", f"{base}.validator_evidence", f"evidence roles must be unique and exactly {sorted(expected_roles)}"))
            continue
        structurally_valid.add(index)
        identities.setdefault(project_path.casefold(), []).append((index, exemplar_class))
        if project_path.casefold() == canonical_project.casefold():
            matching.append((index, entry))

    for identity, registrations in identities.items():
        if len(registrations) > 1:
            classes = {item[1] for item in registrations}
            kind = "conflicting" if len(classes) > 1 else "duplicate"
            findings.append(_finding("MF-EXEMPLAR", identity, f"{kind} exemplar registrations exist for one canonical project identity"))
    if not matching:
        return
    if len(matching) != 1:
        return

    index, entry = matching[0]
    if index not in structurally_valid or not isinstance(ledger, dict):
        return
    base = f"{registry_path}:entries[{index}]"
    try:
        current_version = json.loads(PLUGIN_MANIFEST_PATH.read_text(encoding="utf-8"))["version"]
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError):
        current_version = None
    if entry["validator_version"] != current_version:
        findings.append(_finding("MF-EXEMPLAR", f"{base}.validator_version", "registration validator version is stale relative to the package manifest"))
    phase_state = _project_evidence(project_root, "reviews/phase_state.json", entry.get("phase_state_sha256"), f"{base}.phase_state_sha256", findings, evidence, snapshots)
    if phase_state is not None:
        try:
            if json.loads(phase_state.decode("utf-8", errors="strict")) != document:
                findings.append(_finding("MF-EXEMPLAR", f"{base}.phase_state_sha256", "registered ledger snapshot differs from the document under validation"))
        except (UnicodeError, json.JSONDecodeError):
            findings.append(_finding("MF-EXEMPLAR", f"{base}.phase_state_sha256", "registered ledger snapshot is not valid UTF-8 JSON"))
    approval_payload = _project_evidence(project_root, entry.get("approval_evidence_path"), entry.get("approval_evidence_sha256"), f"{base}.approval_evidence_path", findings, evidence, snapshots)
    if approval_payload is not None:
        try:
            approval_text = approval_payload.decode("utf-8", errors="strict")
        except UnicodeError:
            approval_text = ""
        expected_authority = re.escape(entry["approval_authority"])
        if re.search(r"(?im)^\s*status\s*:\s*approved\s*$", approval_text) is None or re.search(rf"(?im)^\s*authority\s*:\s*{expected_authority}\s*$", approval_text) is None:
            findings.append(_finding("MF-EXEMPLAR", f"{base}.approval_evidence_path", "approval evidence must explicitly attest APPROVED and the registered authority"))
    evidence_by_role: dict[str, tuple[dict[str, Any], bytes | None]] = {}
    for item_index, item in enumerate(entry["validator_evidence"]):
        payload = _project_evidence(project_root, item["path"], item["sha256"], f"{base}.validator_evidence[{item_index}]", findings, evidence, snapshots)
        if (
            item["role"] == "lifecycle_view"
            and payload is not None
            and hashlib.sha256(payload).hexdigest() != item["sha256"]
        ):
            findings.append(_finding(
                "MF-DERIVED", item["path"],
                "generated lifecycle view bytes differ from the externally registered derived view",
                Severity.MAJOR,
            ))
        evidence_by_role[item["role"]] = (item, payload)
    required_roles = EXEMPLAR_EVIDENCE_ROLES[entry["exemplar_class"]]
    if set(evidence_by_role) != required_roles:
        findings.append(_finding("MF-EXEMPLAR", f"{base}.validator_evidence", f"class requires exactly evidence roles {sorted(required_roles)}"))
    milestone_payload = evidence_by_role.get("milestone_validator", ({}, None))[1]
    try:
        validator_record = json.loads(milestone_payload) if milestone_payload is not None else {}
    except (UnicodeError, json.JSONDecodeError):
        validator_record = {}
    if validator_record.get("outcome") != entry["validator_outcome"] or validator_record.get("validator_version") != entry["validator_version"]:
        findings.append(_finding("MF-EXEMPLAR", f"{base}.validator_evidence", "milestone validator evidence does not attest the registered version and outcome"))
    phase_payload = evidence_by_role.get("phase_state_validator", ({}, None))[1]
    try:
        phase_record = json.loads(phase_payload) if phase_payload is not None else {}
    except (UnicodeError, json.JSONDecodeError):
        phase_record = {}
    if phase_record.get("outcome") != "PASS":
        findings.append(_finding("MF-EXEMPLAR", f"{base}.validator_evidence", "phase-state validator evidence must attest PASS"))

    milestones = ledger.get("milestones")
    if entry["exemplar_class"] == "clean_lifecycle_exemplar":
        if ledger.get("mode") != "native" or not isinstance(milestones, dict) or any(
            not isinstance(milestones.get(name), dict)
            or milestones[name].get("status") != "accepted"
            or milestones[name].get("dependency_state") != "current"
            or not isinstance(milestones[name].get("approval"), dict)
            or milestones[name]["approval"].get("status") != "approved"
            or not isinstance(milestones[name].get("handoff"), dict)
            or milestones[name]["handoff"].get("status") not in ({"ready", "consumed"} if name == "M5" else {"consumed"})
            for name in MILESTONES
        ):
            findings.append(_finding("MF-EXEMPLAR", base, "clean lifecycle exemplar requires a native accepted M1-M5 chain, consumed predecessor handoffs, and a ready terminal M5 packet"))
        lifecycle_payload = evidence_by_role.get("lifecycle_view", ({}, None))[1]
        phase_digest = hashlib.sha256(phase_state).hexdigest() if phase_state is not None else None
        if lifecycle_payload is None or phase_digest is None or re.search(rb"(?m)^generated: true$", lifecycle_payload) is None or re.search(rb"(?m)^DO NOT EDIT: generated lifecycle view$", lifecycle_payload) is None or re.search(rb"(?m)^source_sha256: " + phase_digest.encode("ascii") + rb"$", lifecycle_payload) is None:
            findings.append(_finding("MF-EXEMPLAR", f"{base}.validator_evidence", "clean exemplar lifecycle view is not a current derived projection of phase_state.json"))
        for role in ("release_gate", "independent_replay"):
            payload = evidence_by_role.get(role, ({}, None))[1]
            if payload is None or re.search(rb"(?im)^\s*status\s*:\s*PASS\s*$", payload) is None:
                findings.append(_finding("MF-EXEMPLAR", f"{base}.validator_evidence", f"{role} evidence must explicitly attest PASS"))
    else:
        boundary = ledger.get("migration_boundary")
        if ledger.get("mode") != "legacy" or not isinstance(boundary, dict):
            findings.append(_finding("MF-EXEMPLAR", base, "legacy migration exemplar requires an approved legacy migration boundary"))
        else:
            for role, path_key, sha_key in (("migration_report", "report_path", "report_sha256"), ("migration_approval", "evidence_path", "evidence_sha256")):
                item = evidence_by_role.get(role, ({}, None))[0]
                if item.get("path") != boundary.get(path_key) or item.get("sha256") != boundary.get(sha_key):
                    findings.append(_finding("MF-EXEMPLAR", f"{base}.validator_evidence", f"{role} does not bind the approved migration boundary"))
            report_payload = evidence_by_role.get("migration_report", ({}, None))[1]
            migration_approval_payload = evidence_by_role.get("migration_approval", ({}, None))[1]
            try:
                report_record = json.loads(report_payload) if report_payload is not None else {}
            except (UnicodeError, json.JSONDecodeError):
                report_record = {}
            boundary_authority = boundary.get("authority")
            if boundary_authority not in EXEMPLAR_AUTHORITIES:
                findings.append(_finding("MF-EXEMPLAR", f"{base}.validator_evidence", "migration boundary authority is not permitted to approve an exemplar migration"))
            if report_record.get("adjudication_outcome") != "approved" or report_record.get("authority") != boundary_authority:
                findings.append(_finding("MF-EXEMPLAR", f"{base}.validator_evidence", "migration report must attest an approved adjudication by the boundary authority"))
            try:
                migration_approval_text = migration_approval_payload.decode("utf-8", errors="strict") if migration_approval_payload is not None else ""
            except UnicodeError:
                migration_approval_text = ""
            authority_pattern = re.escape(boundary_authority) if isinstance(boundary_authority, str) else r"(?!)"
            if re.search(r"(?im)^\s*status\s*:\s*approved\s*$", migration_approval_text) is None or re.search(rf"(?im)^\s*authority\s*:\s*{authority_pattern}\s*$", migration_approval_text) is None:
                findings.append(_finding("MF-EXEMPLAR", f"{base}.validator_evidence", "migration approval evidence must explicitly attest APPROVED and the boundary authority"))
            commit_payload = evidence_by_role.get("migration_commit", ({}, None))[1]
            manifest_payload = evidence_by_role.get("migration_manifest", ({}, None))[1]
            try:
                commit = json.loads(commit_payload) if commit_payload is not None else {}
                manifest = json.loads(manifest_payload) if manifest_payload is not None else {}
            except (UnicodeError, json.JSONDecodeError):
                commit, manifest = {}, {}
            phase_digest = hashlib.sha256(phase_state).hexdigest() if phase_state is not None else None
            manifest_digest = hashlib.sha256(manifest_payload).hexdigest() if manifest_payload is not None else None
            if (
                commit.get("transaction_state") != "committed"
                or commit.get("replacement_sha256") != phase_digest
                or commit.get("report_sha256") != boundary.get("report_sha256")
                or commit.get("manifest_sha256") != manifest_digest
                or manifest.get("manifest_version") != "1.0.0"
                or manifest.get("replacement_path") != "reviews/phase_state.json"
                or manifest.get("replacement_sha256") != phase_digest
                or manifest.get("report_sha256") != boundary.get("report_sha256")
            ):
                findings.append(_finding("MF-EXEMPLAR", f"{base}.validator_evidence", "migration commit and manifest do not bind the current ledger and approved report"))
            rollback_payload = evidence_by_role.get("rollback_verification", ({}, None))[1]
            if rollback_payload is None or re.search(rb"(?im)^\s*status\s*:\s*PASS\s*$", rollback_payload) is None:
                findings.append(_finding("MF-EXEMPLAR", f"{base}.validator_evidence", "rollback verification evidence must explicitly attest PASS"))
    try:
        snapshots.verify_all()
    except _SnapshotError as exc:
        findings.append(_finding("MF-EXEMPLAR", str(registry_path), str(exc)))


def _historically_authorized_successor_start(
    ledger: dict[str, Any], predecessor: str, successor: str,
) -> bool:
    """Recognize a valid handoff consumed before a later authorized reopen."""
    events = ledger.get("events")
    milestones = ledger.get("milestones")
    if not isinstance(events, list) or not isinstance(milestones, dict):
        return False
    dependent = milestones.get(successor)
    if not isinstance(dependent, dict) or dependent.get("dependency_state") != "needs_revalidation":
        return False
    for start in events:
        if not isinstance(start, dict) or start.get("milestone") != successor or start.get("event_type") != "milestone_started":
            continue
        sequence = start.get("sequence")
        lineage = start.get("lineage_id")
        if not isinstance(sequence, int):
            continue
        before = [
            event for event in events
            if isinstance(event, dict)
            and event.get("lineage_id") == lineage
            and isinstance(event.get("sequence"), int)
            and event["sequence"] < sequence
        ]
        accepted = [event for event in before if event.get("milestone") == predecessor and event.get("event_type") == "milestone_accepted"]
        consumed = [event for event in before if event.get("milestone") == predecessor and event.get("event_type") == "handoff_consumed"]
        if not accepted or not consumed or consumed[-1]["sequence"] < accepted[-1]["sequence"]:
            continue
        later_reopens = [
            event for event in events
            if isinstance(event, dict)
            and event.get("milestone") == predecessor
            and event.get("lineage_id") == lineage
            and event.get("event_type") == "milestone_reopened"
            and isinstance(event.get("sequence"), int)
            and event["sequence"] > sequence
        ]
        for reopened in later_reopens:
            if any(
                isinstance(event, dict)
                and event.get("milestone") == successor
                and event.get("lineage_id") == lineage
                and event.get("event_type") == "downstream_stale"
                and event.get("caused_by_sequence") == reopened.get("sequence")
                for event in events
            ):
                return True
    return False


def validate_document(
    project_root: Path, document: Any, target: str | None = None,
    exemplar_registry_path: Path | None = None,
    _exemplar_snapshot_hook: Callable[[str, str, Path], None] | None = None,
    opening_new_cycle: bool = False,
) -> ValidationResult:
    """Validate the additive namespace in an already-parsed phase document."""
    findings: list[Finding] = []
    evidence: list[dict[str, Any]] = []
    skipped_checks: list[dict[str, str]] = []
    if not isinstance(document, dict):
        findings.append(_finding("MF-STRUCTURE", "$", "phase state must be a JSON object"))
        return _result(target, None, findings, evidence)
    _validate_exemplar_registry(
        project_root, document, exemplar_registry_path or EXEMPLAR_REGISTRY_PATH,
        findings, evidence, _exemplar_snapshot_hook,
    )
    if "milestone_assignment" in document:
        findings.append(_finding("MF-STRUCTURE", "milestone_assignment", "retired M4a/M4b milestone_assignment is archival input only and forbidden in current ledgers"))
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
    migrations = _trusted_path_migrations(project_root, ledger, findings)
    _validate_events(project_root, ledger, milestones, findings, evidence, migrations)

    primary_lineage = ledger.get("primary_lineage")
    phase_identity = document.get("manuscript_id")
    binding = ledger.get("policy_bindings", {}).get("reader_accessibility", {}) if isinstance(ledger.get("policy_bindings"), dict) else {}
    policy_identity = binding.get("project_identity") if isinstance(binding, dict) else None
    phase_identity = phase_identity if isinstance(phase_identity, str) and phase_identity.strip() else None
    policy_identity = policy_identity if isinstance(policy_identity, str) and policy_identity.strip() else None
    if phase_identity is not None and policy_identity is not None and phase_identity != policy_identity:
        findings.append(_finding(
            "MF-HANDOFF", "manuscript_id",
            "phase-state manuscript_id and resolved reader-accessibility project_identity disagree",
        ))
    project_identity = phase_identity or policy_identity
    identity_required = any(
        isinstance(record, dict)
        and isinstance(record.get("handoff"), dict)
        and (
            record["handoff"].get("packet_path") is not None
            or record["handoff"].get("status") in {"ready", "consumed"}
        )
        for record in milestones.values()
    )
    if identity_required and project_identity is None:
        findings.append(_finding(
            "MF-HANDOFF", "manuscript_id",
            "ledger-bound F9 handoffs require an authoritative project identity",
        ))
    predecessor: dict[str, str] | None = None
    deliverables: dict[str, dict[str, Any] | None] = {}
    for index, milestone in enumerate(MILESTONES):
        record = milestones.get(milestone)
        if not isinstance(record, dict):
            continue
        deliverable = _validate_artifacts(project_root, milestone, record, primary_lineage, findings, evidence)
        deliverables[milestone] = deliverable
        scholarly = _validate_scholarly_policy(
            project_root, milestone, record, deliverable, findings, evidence,
        )
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
            project_identity, f9_schema, findings, evidence, scholarly,
        )
        if packet is not None:
            predecessor = packet

        if index > 0 and record.get("status") not in {"not_started", "not_applicable"}:
            previous = milestones.get(MILESTONES[index - 1], {})
            previous_approval = previous.get("approval") if isinstance(previous, dict) else None
            previous_handoff = previous.get("handoff") if isinstance(previous, dict) else None
            current_chain_ready = (
                isinstance(previous_approval, dict)
                and previous_approval.get("status") == "approved"
                and isinstance(previous_handoff, dict)
                and previous_handoff.get("status") == "consumed"
            )
            historically_ready = _historically_authorized_successor_start(
                ledger, MILESTONES[index - 1], milestone,
            )
            if not current_chain_ready and not historically_ready:
                findings.append(_finding("MF-HANDOFF", f"milestone_framework.milestones.{milestone}", "successor work started before predecessor approval and consumed handoff"))

    _validate_reader_accessibility_policy(
        project_root, ledger, milestones, deliverables, findings, evidence, skipped_checks,
        opening_new_cycle=opening_new_cycle,
    )

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
        if not _override_rule_resolves(project_root, override.get("rule"), override.get("authority")):
            findings.append(_finding(
                "MF-OVERRIDE", f"milestone_framework.milestones.{milestone}.authorized_override.rule",
                "override rule must resolve in the authority-appropriate package reference or contained project-local contract",
            ))
        _file_binding(
            project_root,
            override.get("substitute_evidence"),
            override.get("substitute_evidence_sha256"),
            None,
            f"milestone_framework.milestones.{milestone}.authorized_override.substitute_evidence",
            findings,
            evidence,
            "MF-OVERRIDE",
        )

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

    findings.extend(_milestone_target_findings(ledger, target))

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
            valid_proof_surfaces = 0
            if not sections:
                findings.append(_finding(
                    "MF-PHASE", "sections",
                    "Ph4 target requires at least one section with a valid MCR or ceiling-lock proof surface",
                ))
            if not isinstance(default_ceiling, str) or default_ceiling not in phase_order:
                findings.append(_finding(
                    "MF-PHASE", "default_final_phase",
                    "default_final_phase must be a legal phase string for Ph4 validation",
                ))
                default_ceiling = "Ph4"
            for section_name, section in sections.items():
                if not isinstance(section, dict):
                    findings.append(_finding(
                        "MF-PHASE", f"sections[{section_name!r}]",
                        "Ph4 section proof surface must be a JSON object",
                    ))
                    continue
                ceilings = [default_ceiling]
                override = section.get("section_ceiling_override")
                if override is not None:
                    if not isinstance(override, str) or override not in phase_order:
                        findings.append(_finding(
                            "MF-PHASE", f"sections[{section_name!r}].section_ceiling_override",
                            "section_ceiling_override must be null or a legal phase string",
                        ))
                        continue
                    ceilings.append(override)
                applicable_ceiling = min(ceilings, key=lambda phase: phase_order.get(phase, 99))
                ceiling_clear = (
                    section.get("ceiling_locked") is True
                    and section.get("last_approved_phase") == applicable_ceiling
                )
                if ceiling_clear:
                    valid_proof_surfaces += 1
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
                else:
                    valid_proof_surfaces += 1
                if section.get("pre_mcr_deep_pass_completed") is not True:
                    findings.append(_finding(
                        "MF-PHASE", f"sections[{section_name!r}].pre_mcr_deep_pass_completed",
                        "Ph4 MCR continuity requires the pre-MCR deep pass to be complete",
                    ))
            if sections and valid_proof_surfaces == 0:
                findings.append(_finding(
                    "MF-PHASE", "sections",
                    "Ph4 target has no valid unretracted MCR admission or ceiling-lock proof surface",
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

    return _result(target, ledger, findings, evidence, skipped_checks)


def _result(
    target: str | None,
    ledger: dict[str, Any] | None,
    findings: list[Finding],
    evidence: list[dict[str, Any]],
    skipped_checks: list[dict[str, str]] | None = None,
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
        boundary = ledger.get("migration_boundary")
        completed_through = boundary.get("completed_through") if isinstance(boundary, dict) else None
        if target in MILESTONES and completed_through in MILESTONES and MILESTONES.index(target) > MILESTONES.index(completed_through):
            outcome = Outcome.READY
        else:
            outcome = Outcome.LEGACY_READY
    else:
        outcome = Outcome.READY
    return ValidationResult(
        outcome=outcome,
        exit_permitted=outcome is not Outcome.MISCONFIGURED,
        target=target,
        findings=unique,
        evidence_bindings=tuple(evidence),
        skipped_checks=tuple(skipped_checks or ()),
    )


def _render_text(result: ValidationResult) -> str:
    lines = [f"{result.outcome.value} target={result.target or 'all'} exit_permitted={str(result.exit_permitted).lower()}"]
    for finding in result.findings:
        lines.append(f"[{finding.severity.value}] {finding.code} @ {finding.path}: {finding.message}")
    for check in result.skipped_checks:
        lines.append(f"{check['check']}: {check['status']}")
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    parser = UsageArgumentParser(description="Validate milestone feedback and F9 handoff state.")
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--target", choices=TARGETS)
    parser.add_argument("--opening-new-cycle", action="store_true", help="enforce dispatch-bound pin epoch; target readiness alone does not open a cycle")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--exemplar-registry", type=Path, default=EXEMPLAR_REGISTRY_PATH,
        help="external milestone exemplar registry (test/maintenance injection; defaults to package registry)",
    )
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
    result = validate_document(project_root, document, args.target, args.exemplar_registry, opening_new_cycle=args.opening_new_cycle)
    if args.json:
        sys.stdout.write(json.dumps(result.json_value(), indent=2) + "\n")
    else:
        sys.stdout.write(_render_text(result))
    return 0 if result.exit_permitted else 4


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
