#!/usr/bin/env python3
"""Fail-closed gate for assignment-derived academic drafting."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from typing import Any
import uuid


ROOT = Path(__file__).resolve().parents[1]
PROFILE_REL = Path("references/policies/course_essay_milestones.v1.json")
ROLE_OUTPUT_REL = Path("references/role_output_contract.json")
EXPECTED_SEQUENCE = ["M1", "M2", "M3", "M4", "FINAL"]
EXPECTED_MAPPING = {"M1": "M1", "M2": "M2", "M3": "M3", "M4": "M4", "FINAL": "M5"}
COPY_POLICY = "author_controlled_unless_explicitly_requested"
PREDECESSORS = {
    "M1": (),
    "M2": ("M1",),
    "M3": ("M1", "M2"),
    "M4": ("M1", "M2", "M3"),
    "FINAL": ("M1", "M2", "M3", "M4"),
}
RECEIPT_SCHEMA_VERSION = "2.1.0"
RECEIPT_FIELDS = {
    "schema_version",
    "receipt_id",
    "reservation_id",
    "stage",
    "target_milestone",
    "authorized_role",
    "authorized_paths",
    "authorized_writes",
    "primary_deliverable_path",
    "project_root_name",
    "project_root_resolved",
    "produced_at",
    "authority",
    "gate_command",
    "gate_exit_code",
    "gate_stdout_sha256",
    "assignment_contract_sha256",
    "phase_state_sha256",
    "profile_sha256",
    "role_output_contract_sha256",
    "exemplar_conditioning",
    "active_lineage_id",
}

from milestone_path_contract import (
    canonical_deliverable,
    load_role_output_contract,
    released_export,
    validate_project_path_surface,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _text_sha256(lines: list[str]) -> str:
    rendered = "".join(f"{line}\n" for line in lines)
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _is_link_or_reparse(path: Path) -> bool:
    """Detect symlinks and Windows junctions on Python 3.11 and newer."""
    if path.is_symlink():
        return True
    try:
        attributes = getattr(os.lstat(path), "st_file_attributes", 0)
    except OSError:
        return False
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400)
    return bool(attributes & reparse_flag)


def _atomic_write_json(path: Path, record: dict[str, Any]) -> None:
    if path.parent.exists() and _is_link_or_reparse(path.parent):
        raise OSError(f"receipt parent is linked or reparse-backed: {path.parent}")
    path.parent.mkdir(parents=True, exist_ok=True)
    if _is_link_or_reparse(path.parent):
        raise OSError(f"receipt parent is linked or reparse-backed: {path.parent}")
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        data = (json.dumps(record, indent=2) + "\n").encode("utf-8")
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        # Hard-link creation is atomic and refuses an existing destination on
        # both NTFS and POSIX filesystems. Unlike replace(), it cannot silently
        # overwrite a receipt emitted by a concurrent process.
        if _is_link_or_reparse(path.parent):
            raise OSError(f"receipt parent changed to a linked or reparse-backed path: {path.parent}")
        os.link(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _load_json(path: Path, code: str, findings: list[tuple[str, str]]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        findings.append((code, f"missing required file: {path}"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        findings.append((code, f"cannot read valid JSON from {path}: {exc}"))
    return None


def _project_path(project: Path, raw_path: Any) -> Path | None:
    if not isinstance(raw_path, str) or not raw_path:
        return None
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = project / candidate
    try:
        resolved = candidate.resolve()
        resolved.relative_to(project.resolve())
    except (OSError, ValueError):
        return None
    return resolved


def _source_path(project: Path, raw_path: Any) -> Path | None:
    if not isinstance(raw_path, str) or not raw_path:
        return None
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = project / candidate
    try:
        return candidate.resolve()
    except OSError:
        return None


def _wiki_grounding_findings(
    project: Path, milestone_framework: dict[str, Any]
) -> list[tuple[str, str]]:
    milestones = milestone_framework.get("milestones", {})
    m3 = milestones.get("M3") if isinstance(milestones, dict) else None
    policy = m3.get("policy_evidence") if isinstance(m3, dict) else None
    policy = policy if isinstance(policy, dict) else {}
    binding = policy.get("wiki_grounding")
    opt_out = policy.get("wiki_grounding_opt_out")

    if not isinstance(binding, dict):
        if opt_out is None:
            return [("APG-WIKI-GROUNDING-MISSING", "M4/FINAL requires current wiki-first grounding evidence or an authorized opt-out")]
        if not isinstance(opt_out, dict):
            return [("APG-WIKI-OPT-OUT-INVALID", "wiki-grounding opt-out must be an evidence-bound object")]
        authority = opt_out.get("authority")
        reason = opt_out.get("reason")
        evidence_path = _project_path(project, opt_out.get("evidence_path"))
        expected_hash = opt_out.get("evidence_sha256")
        valid = (
            authority in {"user", "advisor", "instructor"}
            and isinstance(reason, str)
            and bool(reason.strip())
            and evidence_path is not None
            and evidence_path.is_file()
            and isinstance(expected_hash, str)
            and _sha256(evidence_path) == expected_hash
        )
        if not valid:
            return [("APG-WIKI-OPT-OUT-INVALID", "opt-out requires user/advisor/instructor authority, a reason, and current evidence")]
        return []

    evidence_path = _project_path(project, binding.get("evidence_path"))
    expected_evidence_hash = binding.get("evidence_sha256")
    if evidence_path is None or not evidence_path.is_file():
        return [("APG-WIKI-GROUNDING-STALE", "bound wiki-grounding evidence path is missing or escapes the project")]
    if not isinstance(expected_evidence_hash, str) or _sha256(evidence_path) != expected_evidence_hash:
        return [("APG-WIKI-GROUNDING-STALE", "wiki-grounding evidence binding hash is missing or stale")]
    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [("APG-WIKI-GROUNDING-STALE", f"wiki-grounding evidence is not valid JSON: {exc}")]
    if not isinstance(evidence, dict):
        return [("APG-WIKI-GROUNDING-STALE", "wiki-grounding evidence must be an object")]

    required_text = ("lineage_id", "produced_at", "wiki_path", "references_path", "references_sha256", "graph_path", "graph_sha256_provenance", "authority", "notes")
    if evidence.get("schema_version") != "1.0.0" or any(
        not isinstance(evidence.get(key), str) or not evidence[key].strip()
        for key in required_text
    ):
        return [("APG-WIKI-GROUNDING-STALE", "wiki-grounding evidence is missing required schema fields")]
    try:
        datetime.fromisoformat(evidence["produced_at"].replace("Z", "+00:00"))
    except ValueError:
        return [("APG-WIKI-GROUNDING-STALE", "wiki-grounding produced_at must be RFC3339")]
    active_lineage = milestone_framework.get(
        "primary_lineage", milestone_framework.get("primary_lineage_id", "live")
    )
    if evidence["lineage_id"] != active_lineage:
        return [("APG-WIKI-GROUNDING-STALE", "wiki-grounding evidence does not bind the active lineage")]
    skills = evidence.get("skills_invoked")
    sources = evidence.get("sources_consulted")
    if (
        evidence.get("wiki_first_resources") is not True
        or evidence.get("authority") != "planner"
        or not isinstance(skills, list)
        or not skills
        or any(not isinstance(item, str) or not item.strip() for item in skills)
        or not isinstance(sources, list)
        or not sources
    ):
        return [("APG-WIKI-GROUNDING-STALE", "wiki-first execution, Planner authority, skills, and consulted sources must be recorded")]
    wiki_path = _source_path(project, evidence["wiki_path"])
    if wiki_path is None or not wiki_path.is_dir():
        return [("APG-WIKI-GROUNDING-STALE", "declared wiki_path is missing")]

    references_path = _project_path(project, evidence["references_path"])
    if (
        references_path is None
        or not references_path.is_file()
        or _sha256(references_path) != evidence["references_sha256"]
    ):
        return [("APG-WIKI-GROUNDING-STALE", "declared references_path is missing, escapes the project, or hash-stale")]

    graph_path = _source_path(project, evidence["graph_path"])
    try:
        if graph_path is None:
            raise ValueError
        graph_path.relative_to(wiki_path.resolve())
    except (OSError, ValueError):
        return [("APG-WIKI-GROUNDING-STALE", "declared graph_path is missing or escapes wiki_path")]
    if not graph_path.is_file() or _sha256(graph_path) != evidence["graph_sha256_provenance"]:
        return [("APG-WIKI-GROUNDING-STALE", "declared graph_path is missing or hash-stale")]

    for index, source in enumerate(sources):
        path = _source_path(project, source.get("path") if isinstance(source, dict) else None)
        digest = source.get("sha256") if isinstance(source, dict) else None
        try:
            if path is None:
                raise ValueError
            path.relative_to(wiki_path.resolve())
        except (OSError, ValueError):
            return [("APG-WIKI-GROUNDING-STALE", f"sources_consulted[{index}] is missing or escapes wiki_path")]
        if not path.is_file() or not isinstance(digest, str) or _sha256(path) != digest:
            return [("APG-WIKI-GROUNDING-STALE", f"sources_consulted[{index}] is missing or hash-stale")]
    return []


def _exemplar_requested(contract: dict[str, Any], cli_requested: bool) -> bool:
    dispatch = contract.get("dispatch")
    return (
        cli_requested
        or contract.get("exemplar_conditioning") is True
        or (isinstance(dispatch, dict) and dispatch.get("exemplar_conditioning") is True)
    )


def _ready_lines(
    project: Path,
    stage: str,
    target: str,
    exemplar_conditioning: bool,
) -> list[str]:
    lines: list[str] = []
    contract_path = project / "reviews" / "assignment_contract.json"
    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        contract = {}
    if (
        target in {"M4", "FINAL"}
        and isinstance(contract, dict)
        and _exemplar_requested(contract, exemplar_conditioning)
        and contract.get("dennett_exemplar_status") == "pending"
    ):
        lines.append(
            "[ADVISORY] APG-EXEMPLAR-DENNETT-PENDING: "
            "Dennett remains unavailable until grounded; Yu surface conditioning may proceed"
        )
    lines.append(f"READY assignment-process stage={stage} target={target}")
    return lines


def _receipt_path_finding(project: Path, path: Path, target: str) -> tuple[str, str] | None:
    assignment_dir = Path(os.path.abspath(project / "reviews" / ".harness" / "assignment"))
    lexical = Path(os.path.abspath(path))
    expected_prefix = f"gate_receipt_{target}_"
    if (
        lexical.parent.parent != assignment_dir
        or lexical.parent.name not in {"ready", "reserved", "consumed", "invalidated"}
        or not lexical.name.startswith(expected_prefix)
        or lexical.suffix != ".json"
    ):
        return (
            "APG-RECEIPT-INVALID",
            "receipt path must match reviews/.harness/assignment/"
            f"<ready|reserved|consumed|invalidated>/gate_receipt_{target}_<utc>.json",
        )
    control_paths = [
        project / "reviews",
        project / "reviews" / ".harness",
        assignment_dir,
        lexical.parent,
    ]
    for control_path in control_paths:
        if control_path.exists() and (
            not control_path.is_dir()
            or _is_link_or_reparse(control_path)
        ):
            return (
                "APG-RECEIPT-PATH-INVALID",
                f"receipt control path is not a plain directory: {control_path}",
            )
    return None


def _resolve_receipt_path(project: Path, path: Path) -> Path:
    candidate = path if path.is_absolute() else project / path
    # Preserve the lexical control-tree path so validation can see a symlink or
    # junction instead of resolving it away before the check.
    return Path(os.path.abspath(candidate))


def derive_receipt_authority(target: str) -> tuple[str, list[dict[str, str]], str]:
    """Re-derive receipt writer authority from the live role contract."""
    role_contract = load_role_output_contract()
    milestone = EXPECTED_MAPPING[target]
    milestone_row = role_contract["milestones"][milestone]
    role = milestone_row["deliverable_writer"]
    primary_path = canonical_deliverable(target)
    writes = [{"path": primary_path, "mode": "replace"}]
    export_path = milestone_row.get("released_export_path")
    if isinstance(export_path, str) and export_path:
        writes.append({"path": export_path, "mode": "replace"})
    for row in role_contract.get("common_generator_outputs", []):
        if not isinstance(row, dict):
            continue
        path = row.get("path")
        mode = row.get("mode")
        if isinstance(path, str) and mode in {"create", "replace", "append"}:
            if all(item["path"] != path for item in writes):
                writes.append({"path": path, "mode": mode})
    return role, writes, primary_path


def derive_released_export_path(target: str) -> str | None:
    """Return the live role contract's released-export path, when declared."""
    return released_export(target)


def _receipt_record(
    project: Path,
    stage: str,
    target: str,
    exemplar_conditioning: bool,
    ready_lines: list[str],
) -> dict[str, Any]:
    phase_state_path = project / "reviews" / "phase_state.json"
    phase_state = json.loads(phase_state_path.read_text(encoding="utf-8"))
    framework = phase_state.get("milestone_framework", {})
    lineage = (
        framework.get("primary_lineage", framework.get("primary_lineage_id", "live"))
        if isinstance(framework, dict) else "live"
    )
    authorized_role, authorized_writes, primary_path = derive_receipt_authority(target)
    authorized_paths = [row["path"] for row in authorized_writes]
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "receipt_id": str(uuid.uuid4()),
        "reservation_id": str(uuid.uuid4()),
        "stage": stage,
        "target_milestone": target,
        "authorized_role": authorized_role,
        "authorized_paths": authorized_paths,
        "authorized_writes": authorized_writes,
        "primary_deliverable_path": primary_path,
        "project_root_name": project.name,
        "project_root_resolved": str(project.resolve()),
        "produced_at": _timestamp(),
        "authority": "planner",
        "gate_command": [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]],
        "gate_exit_code": 0,
        "gate_stdout_sha256": _text_sha256(ready_lines),
        "assignment_contract_sha256": _sha256(
            project / "reviews" / "assignment_contract.json"
        ),
        "phase_state_sha256": _sha256(phase_state_path),
        "profile_sha256": _sha256(ROOT / PROFILE_REL),
        "role_output_contract_sha256": _sha256(ROOT / ROLE_OUTPUT_REL),
        "exemplar_conditioning": exemplar_conditioning,
        "active_lineage_id": lineage,
    }


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return True


def _receipt_shape_finding(receipt: Any) -> tuple[str, str] | None:
    if not isinstance(receipt, dict) or set(receipt) != RECEIPT_FIELDS:
        return ("APG-RECEIPT-INVALID", f"receipt fields do not match schema version {RECEIPT_SCHEMA_VERSION}")
    try:
        uuid.UUID(receipt["receipt_id"])
        uuid.UUID(receipt["reservation_id"])
    except (AttributeError, TypeError, ValueError):
        return ("APG-RECEIPT-INVALID", "receipt_id must be a UUID")
    hashes = (
        "gate_stdout_sha256",
        "assignment_contract_sha256",
        "phase_state_sha256",
        "profile_sha256",
        "role_output_contract_sha256",
    )
    valid = (
        receipt["schema_version"] == RECEIPT_SCHEMA_VERSION
        and receipt["stage"] in {"draft", "final"}
        and receipt["target_milestone"] in EXPECTED_SEQUENCE
        and (receipt["stage"] != "final" or receipt["target_milestone"] == "FINAL")
        and receipt["authorized_role"] == "generator"
        and isinstance(receipt["authorized_paths"], list)
        and bool(receipt["authorized_paths"])
        and all(isinstance(path, str) and path for path in receipt["authorized_paths"])
        and isinstance(receipt["authorized_writes"], list)
        and bool(receipt["authorized_writes"])
        and all(
            isinstance(row, dict)
            and set(row) == {"path", "mode"}
            and isinstance(row["path"], str)
            and bool(row["path"])
            and row["mode"] in {"create", "replace", "append"}
            for row in receipt["authorized_writes"]
        )
        and receipt["authorized_paths"] == [row["path"] for row in receipt["authorized_writes"]]
        and receipt["primary_deliverable_path"] in receipt["authorized_paths"]
        and isinstance(receipt["project_root_name"], str)
        and bool(receipt["project_root_name"])
        and isinstance(receipt["project_root_resolved"], str)
        and bool(receipt["project_root_resolved"])
        and _valid_timestamp(receipt["produced_at"])
        and receipt["authority"] == "planner"
        and isinstance(receipt["gate_command"], list)
        and bool(receipt["gate_command"])
        and all(isinstance(item, str) and item for item in receipt["gate_command"])
        and receipt["gate_exit_code"] == 0
        and all(
            isinstance(receipt[key], str)
            and len(receipt[key]) == 64
            and all(character in "0123456789abcdef" for character in receipt[key])
            for key in hashes
        )
        and isinstance(receipt["exemplar_conditioning"], bool)
        and isinstance(receipt["active_lineage_id"], str)
        and bool(receipt["active_lineage_id"])
    )
    if not valid:
        return ("APG-RECEIPT-INVALID", f"receipt values do not satisfy schema version {RECEIPT_SCHEMA_VERSION}")
    return None


def verify_receipt(
    project: Path, path: Path, *, allow_consumed: bool = False
) -> list[tuple[str, str]]:
    if not path.is_file():
        return [("APG-RECEIPT-MISSING", f"missing assignment gate receipt: {path}")]
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [("APG-RECEIPT-INVALID", f"cannot read valid receipt JSON from {path}: {exc}")]
    shape_finding = _receipt_shape_finding(receipt)
    if shape_finding is not None:
        return [shape_finding]
    path_finding = _receipt_path_finding(
        project, path, receipt["target_milestone"]
    )
    if path_finding is not None:
        return [path_finding]
    if path.parent.name == "consumed" and not allow_consumed:
        return [("APG-RECEIPT-CONSUMED", "assignment gate receipt has already been consumed")]
    if path.parent.name == "invalidated":
        return [("APG-RECEIPT-INVALID", "assignment gate receipt has been invalidated")]
    if receipt["project_root_name"] != project.name:
        return [("APG-RECEIPT-INVALID", "receipt is bound to a different project root")]
    if receipt["project_root_resolved"] != str(project.resolve()):
        return [("APG-RECEIPT-INVALID", "receipt is bound to a different project instance")]

    try:
        role, writes, primary = derive_receipt_authority(receipt["target_milestone"])
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return [("APG-RECEIPT-STALE", f"cannot re-derive live writer authority: {exc}")]
    expected_paths = [row["path"] for row in writes]
    if (
        receipt["authorized_role"] != role
        or receipt["authorized_writes"] != writes
        or receipt["authorized_paths"] != expected_paths
        or receipt["primary_deliverable_path"] != primary
    ):
        return [("APG-RECEIPT-STALE", "receipt writer authority differs from the live role contract")]

    contract_path = project / "reviews" / "assignment_contract.json"
    if not contract_path.is_file():
        return [("APG-CONTRACT-MISSING", f"missing required file: {contract_path}")]
    live_paths = {
        "assignment_contract_sha256": contract_path,
        "phase_state_sha256": project / "reviews" / "phase_state.json",
        "profile_sha256": ROOT / PROFILE_REL,
        "role_output_contract_sha256": ROOT / ROLE_OUTPUT_REL,
    }
    for field, live_path in live_paths.items():
        try:
            live_hash = _sha256(live_path)
        except OSError:
            return [("APG-RECEIPT-STALE", f"receipt-bound file is missing: {live_path}")]
        if receipt[field] != live_hash:
            return [("APG-RECEIPT-STALE", f"receipt hash is stale for {live_path}")]

    stage = receipt["stage"]
    target = receipt["target_milestone"]
    exemplar_conditioning = receipt["exemplar_conditioning"]
    gate_findings = validate(project, stage, target, exemplar_conditioning)
    if gate_findings:
        return gate_findings
    expected_stdout_hash = _text_sha256(
        _ready_lines(project, stage, target, exemplar_conditioning)
    )
    if receipt["gate_stdout_sha256"] != expected_stdout_hash:
        return [("APG-RECEIPT-INVALID", "gate stdout digest does not match the READY result")]
    return []


def _print_findings(findings: list[tuple[str, str]]) -> None:
    print("MISCONFIGURED")
    for code, message in findings:
        print(f"[BLOCKER] {code}: {message}")


def validate(
    project: Path,
    stage: str,
    target_milestone: str | None = None,
    exemplar_conditioning: bool = False,
) -> list[tuple[str, str]]:
    findings: list[tuple[str, str]] = []
    contract = _load_json(project / "reviews" / "assignment_contract.json", "APG-CONTRACT-MISSING", findings)
    if not isinstance(contract, dict):
        # `mode` selects the milestone-framework state model; it is not an
        # assignment-applicability flag.  Keep the gate fail-closed and make
        # that distinction explicit so a generic native scaffold is not
        # mistaken for authorization to bypass the controlling brief.
        contract_path = project / "reviews" / "assignment_contract.json"
        state_path = project / "reviews" / "phase_state.json"
        if not contract_path.exists() and state_path.is_file():
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                state = None
            framework = state.get("milestone_framework") if isinstance(state, dict) else None
            if isinstance(framework, dict) and framework.get("mode") == "native":
                code = findings[0][0]
                findings[:] = [
                    (
                        code,
                        f"missing required file: {contract_path}; mode:native does not "
                        "make the assignment process NOT_APPLICABLE. Resolve the "
                        "controlling assignment contract or use a workflow whose "
                        "governing contract explicitly authorizes N/A.",
                    )
                ]
        return findings
    try:
        validate_project_path_surface(project, require_all=False)
    except ValueError as exc:
        findings.append(("APG-MILESTONE-PATH-CONTRACT", str(exc)))
        return findings
    if contract.get("contract_version") != "1.0.0" or contract.get("status") != "resolved":
        findings.append(("APG-CONTRACT-UNRESOLVED", "assignment contract must be version 1.0.0 with status resolved"))

    profile_path = ROOT / PROFILE_REL
    profile = _load_json(profile_path, "APG-PROFILE-MISSING", findings)
    if isinstance(profile, dict):
        if contract.get("profile_id") != profile.get("profile_id"):
            findings.append(("APG-PROFILE-ID", "project profile_id does not match the package profile"))
        if contract.get("profile_path") != PROFILE_REL.as_posix():
            findings.append(("APG-PROFILE-PATH", f"profile_path must be {PROFILE_REL.as_posix()}"))
        if contract.get("profile_sha256") != _sha256(profile_path):
            findings.append(("APG-PROFILE-HASH", "package milestone profile hash is missing or stale"))
        deliverables = profile.get("deliverables")
        if not isinstance(deliverables, dict) or set(deliverables.keys()) != set(EXPECTED_SEQUENCE):
            findings.append(("APG-PROFILE-FUNCTIONS", "profile must define M1-M4 followed by a separate FINAL deliverable"))

    source = contract.get("assignment_source")
    if not isinstance(source, dict) or source.get("authority") not in {"user", "advisor", "instructor", "committee", "venue"}:
        findings.append(("APG-SOURCE-AUTHORITY", "assignment source requires a recognized higher authority"))
    else:
        raw_path = source.get("path")
        source_path = Path(raw_path) if isinstance(raw_path, str) and raw_path else None
        if source_path is not None and not source_path.is_absolute():
            source_path = project / source_path
        if source_path is None or not source_path.is_file():
            findings.append(("APG-SOURCE-MISSING", "the controlling assignment source does not exist"))
        elif source.get("sha256") != _sha256(source_path):
            findings.append(("APG-SOURCE-HASH", "the controlling assignment source hash is missing or stale"))

    if contract.get("assigned_sequence") != EXPECTED_SEQUENCE:
        findings.append(("APG-SEQUENCE", "assigned_sequence must preserve M1, M2, M3, M4, then FINAL"))
    if contract.get("framework_mapping") != EXPECTED_MAPPING:
        findings.append(("APG-MAPPING", "framework mapping must keep FINAL separate while binding it to terminal slot M5"))
    if contract.get("professor_copy_policy") != COPY_POLICY:
        findings.append(("APG-PROFESSOR-COPY-AUTHORITY", "professor-copy production remains author-controlled unless explicitly requested"))

    target = "FINAL" if stage == "final" else target_milestone
    if stage != "final" and target == "FINAL":
        findings.append(("APG-SEQUENCE-TARGET", "FINAL drafting requires --stage final (omit --target-milestone)"))
        return findings
    if target is None:
        findings.append(("APG-SEQUENCE-TARGET", "draft stage requires an explicit --target-milestone"))
        return findings

    if target in {"M1", "M2", "M3"} and _exemplar_requested(contract, exemplar_conditioning):
        findings.append(
            (
                "APG-EXEMPLAR-SCOPE",
                f"{target} forbids domain-native exemplar retrieval conditioning; ordinary scholarly citation remains allowed",
            )
        )

    state = _load_json(project / "reviews" / "phase_state.json", "APG-PHASE-STATE-MISSING", findings)
    milestone_framework = state.get("milestone_framework", {}) if isinstance(state, dict) else {}
    mode = milestone_framework.get("mode", "legacy") if isinstance(milestone_framework, dict) else "legacy"
    if mode != "native":
        findings.append(
            (
                "APG-SEQUENCE-LEGACY",
                "legacy assignment state requires explicit migration and milestone acceptance work before sequence dispatch",
            )
        )
        return findings

    milestones = milestone_framework.get("milestones", {}) if isinstance(milestone_framework, dict) else {}
    unmet: list[str] = []
    for key in PREDECESSORS[target]:
        record = milestones.get(key)
        status = record.get("status") if isinstance(record, dict) else None
        if status != "accepted":
            unmet.append(f"{key}={status!r}")
    if unmet:
        findings.append(
            (
                f"APG-SEQUENCE-{target}",
                f"{target} drafting requires accepted predecessors; observed {', '.join(unmet)}",
            )
        )

    if target in {"M4", "FINAL"} and isinstance(milestone_framework, dict):
        findings.extend(_wiki_grounding_findings(project, milestone_framework))

    if stage == "final":
        for key in ("M1", "M2", "M3", "M4"):
            record = milestones.get(key)
            status = record.get("status") if isinstance(record, dict) else None
            if status != "accepted":
                findings.append((f"APG-PREREQUISITE-{key}", f"final-paper drafting requires accepted {key}; observed {status!r}"))
        m5 = milestones.get("M5")
        m5_status = m5.get("status") if isinstance(m5, dict) else None
        if m5_status != "in_progress":
            findings.append(("APG-FINAL-STATE", f"FINAL publication requires ledger M5 in_progress; observed {m5_status!r}"))
        if state.get("terminal_phase_reached") is not False or state.get("terminal_round_id") is not None:
            findings.append(("APG-FINAL-TERMINAL", "FINAL publication is refused after terminal close until an authorized reopen clears both terminal fields"))
        sections = state.get("sections")
        if not isinstance(sections, dict) or not sections or any(
            not isinstance(row, dict) or row.get("current_phase") != "Ph4"
            for row in sections.values()
        ):
            findings.append(("APG-FINAL-PHASE", "FINAL publication requires every in-scope section at Ph4"))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--stage", choices=("draft", "final"))
    parser.add_argument("--target-milestone", choices=EXPECTED_SEQUENCE)
    parser.add_argument("--exemplar-conditioning", action="store_true")
    receipt_mode = parser.add_mutually_exclusive_group()
    receipt_mode.add_argument("--emit-receipt", type=Path)
    receipt_mode.add_argument("--verify-receipt", type=Path)
    args = parser.parse_args()
    project = args.project_root.resolve()

    if args.verify_receipt is not None:
        if args.stage is not None or args.target_milestone is not None or args.exemplar_conditioning:
            _print_findings(
                [
                    (
                        "APG-RECEIPT-INVALID",
                        "--verify-receipt derives stage, target, and conditioning from the receipt",
                    )
                ]
            )
            return 4
        receipt_path = _resolve_receipt_path(project, args.verify_receipt)
        findings = verify_receipt(project, receipt_path)
        if findings:
            _print_findings(findings)
            return 4
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        print(
            "VERIFIED assignment-process receipt "
            f"target={receipt['target_milestone']} path={receipt_path}"
        )
        return 0

    if args.stage is None:
        parser.error("--stage is required unless --verify-receipt is used")
    findings = validate(project, args.stage, args.target_milestone, args.exemplar_conditioning)
    if findings:
        _print_findings(findings)
        return 4
    target = "FINAL" if args.stage == "final" else args.target_milestone
    assert target is not None
    ready_lines = _ready_lines(project, args.stage, target, args.exemplar_conditioning)
    if args.emit_receipt is not None:
        receipt_path = _resolve_receipt_path(project, args.emit_receipt)
        path_finding = _receipt_path_finding(project, receipt_path, target)
        if path_finding is not None:
            _print_findings([path_finding])
            return 4
        if receipt_path.parent.name != "ready":
            _print_findings(
                [("APG-RECEIPT-INVALID", "new receipts must be emitted into the ready directory")]
            )
            return 4
        assignment_root = receipt_path.parent.parent
        collisions = [
            assignment_root / state / receipt_path.name
            for state in ("ready", "reserved", "consumed", "invalidated")
            if (assignment_root / state / receipt_path.name).exists()
        ]
        if collisions:
            _print_findings(
                [("APG-RECEIPT-INVALID", f"refusing duplicate receipt basename: {collisions[0]}")]
            )
            return 4
        try:
            _atomic_write_json(
                receipt_path,
                _receipt_record(
                    project,
                    args.stage,
                    target,
                    args.exemplar_conditioning,
                    ready_lines,
                ),
            )
        except (OSError, UnicodeError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            _print_findings(
                [("APG-RECEIPT-INVALID", f"cannot emit assignment gate receipt: {exc}")]
            )
            return 4
        print(f"RECEIPT assignment-process path={receipt_path}")
    for line in ready_lines:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
