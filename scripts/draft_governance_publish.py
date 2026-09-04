#!/usr/bin/env python3
"""Publish graph-independent draft-governance evidence without inventing judgment."""

from __future__ import annotations

import hashlib
import json
import argparse
import re
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import draft_governance
import assignment_dispatch_claim as dispatch
import obligation_result
from evidence_publication import publish_committed, validate_committed
from draft_governance_lifecycle import (
    INVENTORY as LIFECYCLE_INVENTORY,
    validate_lifecycle_draft_governance_binding,
)


_SAFE_LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_MILESTONES = {"M1", "M2", "M3", "M4", "FINAL"}
_PHASES = {"generation", "evaluation"}


class DraftGovernancePublicationError(RuntimeError):
    """Refuse an unsafe or unverifiable draft-governance publication."""


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _binding(project: Path, path: Path) -> dict[str, Any]:
    resolved = path.resolve(strict=True)
    return {
        "path": resolved.relative_to(project).as_posix(),
        "sha256": _file_digest(resolved),
        "byte_length": resolved.stat().st_size,
    }


def _root_binding(root: Path, path: Path, root_name: str) -> dict[str, str]:
    resolved = path.resolve(strict=True)
    return {
        "root": root_name,
        "path": resolved.relative_to(root.resolve(strict=True)).as_posix(),
        "sha256": _file_digest(resolved),
    }


def publication_lane(
    project_root: Path,
    *,
    milestone: str,
    phase: str,
    evidence_label: str,
) -> Path:
    project = project_root.resolve()
    if milestone not in _MILESTONES:
        raise DraftGovernancePublicationError("unsupported milestone")
    if phase not in _PHASES:
        raise DraftGovernancePublicationError("unsupported phase")
    if not _SAFE_LABEL.fullmatch(evidence_label):
        raise DraftGovernancePublicationError("unsafe evidence label")
    lane = (
        project
        / "reviews"
        / ".harness"
        / "evidence"
        / "draft-governance"
        / milestone.lower()
        / phase
        / evidence_label
    ).resolve()
    if not lane.is_relative_to(project):
        raise DraftGovernancePublicationError("publication lane escapes project root")
    return lane


def prepare_contract(
    *,
    project_root: Path,
    artifact: Path,
    milestone: str,
    phase: str,
    role: str,
    evidence_label: str,
) -> dict[str, Any]:
    """Resolve and durably publish the current contract before external review."""

    project = project_root.resolve(strict=True)
    artifact_path = artifact.resolve(strict=True)
    if not artifact_path.is_file() or not artifact_path.is_relative_to(project):
        raise DraftGovernancePublicationError(
            "artifact is absent, linked, or outside the project root"
        )
    lane = publication_lane(
        project,
        milestone=milestone,
        phase=phase,
        evidence_label=evidence_label,
    )
    args = SimpleNamespace(
        project_root=str(project),
        artifact=str(artifact_path),
        target=milestone,
        phase=phase,
        role=role,
    )
    try:
        contract = draft_governance.prepare(args)
    except Exception as exc:
        raise DraftGovernancePublicationError(
            f"draft-governance resolution refused: {exc}"
        ) from exc
    contract_data = _canonical(contract)
    contract_path = lane / "contract.json"
    transaction_id = f"draft-governance-prepare-{_digest(contract_data)[:16]}"
    marker_value = {
        "schema_version": "1.0.0",
        "publication_type": "draft_governance_contract",
        "state": "committed",
        "transaction_id": transaction_id,
        "contract": {
            "path": contract_path.relative_to(project).as_posix(),
            "sha256": _digest(contract_data),
            "byte_length": len(contract_data),
        },
    }
    marker_path = lane / "contract-commit-marker.json"
    marker_data = _canonical(marker_value)
    artifact_digest = _file_digest(artifact_path)

    def current_contract() -> None:
        if draft_governance.prepare(args) != contract:
            raise DraftGovernancePublicationError(
                "draft-governance contract changed under publication claim"
            )

    try:
        publish_committed(
            project_root=project,
            transaction_id=transaction_id,
            preconditions=[(artifact_path, artifact_digest)],
            inventory_preconditions=[],
            outputs=[(contract_path, contract_data)],
            marker=(marker_path, marker_data),
            under_claim_validator=current_contract,
        )
    except Exception as exc:
        if isinstance(exc, DraftGovernancePublicationError):
            raise
        raise DraftGovernancePublicationError(
            f"contract publication refused: {exc}"
        ) from exc
    validation = {
        "project_root": project,
        "transaction_id": transaction_id,
        "preconditions": [(artifact_path, artifact_digest)],
        "inventory_preconditions": [],
        "outputs": [(contract_path, contract_data)],
        "marker": (marker_path, marker_data),
    }
    validate_prepared_contract(**validation)
    return {
        "contract": contract,
        "contract_path": contract_path,
        "commit_marker": marker_path,
        "transaction_id": transaction_id,
        "validation": validation,
    }


def validate_prepared_contract(**validation: Any) -> None:
    """Replay the marker-last publication transaction for one prepared contract."""

    try:
        validate_committed(**validation)
    except Exception as exc:
        raise DraftGovernancePublicationError(
            f"prepared contract does not validate: {exc}"
        ) from exc


def publish_obligation_results(
    *,
    project_root: Path,
    artifact: Path,
    contract_path: Path,
    phase: str,
    role: str,
    milestone: str,
    evidence_label: str,
    obligation_claim: Path,
    adapter_reports: dict[str, Path],
    created_at: str,
) -> dict[str, Any]:
    """Publish supplied reports and deterministic typed-result wrappers.

    The caller supplies every non-mechanical adapter report.  This function
    mirrors those judgments, authenticates their exact bytes through the
    narrow obligation Evaluator claim, and never creates scholarly findings.
    """

    project = project_root.resolve(strict=True)
    artifact_path = artifact.resolve(strict=True)
    contract_file = contract_path.resolve(strict=True)
    claim_path = obligation_claim.resolve(strict=True)
    if any(
        not path.is_relative_to(project)
        for path in (artifact_path, contract_file, claim_path)
    ):
        raise DraftGovernancePublicationError("obligation publication escapes project")
    try:
        contract = json.loads(contract_file.read_text(encoding="utf-8"))
        claim = json.loads(claim_path.read_text(encoding="utf-8"))
        registry = json.loads(
            draft_governance.OBLIGATION_REGISTRY_PATH.read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DraftGovernancePublicationError(
            f"obligation publication inputs are unreadable: {exc}"
        ) from exc
    if (
        claim.get("claim_kind") != "obligation_evaluation"
        or claim.get("role") != "evaluator"
        or claim.get("authority_scope") != "obligation_results"
        or claim.get("target_milestone") != milestone
        or claim.get("target_path") != artifact_path.relative_to(project).as_posix()
        or claim.get("artifact", {}).get("sha256") != _file_digest(artifact_path)
        or contract.get("phase") != phase
        or contract.get("required_role") != role
        or contract.get("target") != milestone
    ):
        raise DraftGovernancePublicationError(
            "obligation claim, contract, role, milestone, or artifact is split"
        )
    current = draft_governance.prepare(
        SimpleNamespace(
            project_root=str(project),
            artifact=str(artifact_path),
            target=milestone,
            phase=phase,
            role=role,
        )
    )
    if current != contract:
        raise DraftGovernancePublicationError("prepared contract is no longer current")
    active = [
        row
        for row in contract.get("obligations", [])
        if isinstance(row, dict)
        and phase in row.get("phases", [])
        and row.get("typed_result_required") is True
    ]
    active_ids = {row["id"] for row in active}
    generic_ids = {
        row["id"]
        for row in active
        if registry["obligations"][row["id"]]["report_schema"]["path"]
        == obligation_result.GENERIC_REPORT_SCHEMA_REL
    }
    if set(adapter_reports) != generic_ids:
        missing = sorted(generic_ids - set(adapter_reports))
        extra = sorted(set(adapter_reports) - generic_ids)
        raise DraftGovernancePublicationError(
            f"adapter report coverage differs; missing={missing}, extra={extra}"
        )
    lane = publication_lane(
        project,
        milestone=milestone,
        phase=phase,
        evidence_label=evidence_label,
    )
    report_outputs: list[tuple[Path, bytes]] = []
    report_values: dict[str, dict[str, Any]] = {}
    artifact_binding = _binding(project, artifact_path)
    policy_binding = _binding(project, contract_file)
    for row in active:
        obligation_id = row["id"]
        adapter = registry["obligations"][obligation_id]
        if obligation_id == "d-style-profile":
            import d_style_profile_check as dstyle
            report = dstyle.build_report(
                project,
                project / "research_notes" / "directives.md",
                artifact_path,
            )
        else:
            supplied = adapter_reports[obligation_id].resolve(strict=True)
            if not supplied.is_relative_to(project) or not supplied.is_file():
                raise DraftGovernancePublicationError(
                    f"supplied report escapes the project: {obligation_id}"
                )
            try:
                report = json.loads(supplied.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise DraftGovernancePublicationError(
                    f"supplied report is unreadable: {obligation_id}: {exc}"
                ) from exc
            expected_common = {
                "schema_version": "1.0.0",
                "report_type": "obligation_adapter_report",
                "adapter_id": adapter["adapter_id"],
                "adapter_version": adapter["adapter_version"],
                "obligation_id": obligation_id,
                "artifact": artifact_binding,
                "policy": policy_binding,
                "activation": adapter["activation"],
                "execution_status": report.get("execution_status"),
                "outcome": report.get("outcome"),
                "findings": report.get("findings"),
                "diagnostic_only": adapter["diagnostic_only"],
                "created_at": report.get("created_at"),
            }
            if report != expected_common:
                raise DraftGovernancePublicationError(
                    f"supplied report does not exactly bind its adapter: {obligation_id}"
                )
        report_values[obligation_id] = report
        report_outputs.append((lane / "reports" / f"{obligation_id}.json", _canonical(report)))
    report_tx = "obligation-reports-" + _digest(
        b"".join(data for _, data in report_outputs)
    )[:16]
    report_marker = lane / "reports" / "commit-marker.json"
    report_marker_data = _canonical(
        {
            "schema_version": "1.0.0",
            "publication_type": "obligation_report_batch",
            "state": "committed",
            "transaction_id": report_tx,
            "obligation_ids": sorted(active_ids),
        }
    )
    preconditions = [
        (artifact_path, _file_digest(artifact_path)),
        (contract_file, _file_digest(contract_file)),
        (claim_path, _file_digest(claim_path)),
    ]
    publish_committed(
        project_root=project,
        transaction_id=report_tx,
        preconditions=preconditions,
        inventory_preconditions=[],
        outputs=report_outputs,
        marker=(report_marker, report_marker_data),
    )
    _, consumption_path, _ = dispatch.consume_evidence_dispatch_claim(
        project,
        claim_path,
        role="evaluator",
        consumer_transaction_id=f"obligation-results:{report_tx}",
        artifact=artifact_path,
        publication_transaction_id=report_tx,
        product_paths=[path for path, _ in report_outputs],
        commit_marker=report_marker,
        consumed_at=created_at,
        recover_exact=True,
    )
    result_outputs: list[tuple[Path, bytes]] = []
    result_paths: dict[str, Path] = {}
    receipt_rows: list[dict[str, Any]] = []
    for row in active:
        obligation_id = row["id"]
        adapter = registry["obligations"][obligation_id]
        report_path = lane / "reports" / f"{obligation_id}.json"
        report = report_values[obligation_id]
        if obligation_id == "d-style-profile":
            findings: list[dict[str, Any]] = []
            for finding in report.get("findings", []):
                severity = finding.get("severity")
                if severity not in obligation_result.SEVERITY_RANK:
                    continue
                identity = _digest(
                    json.dumps(
                        {
                            "field": finding.get("field"),
                            "locator": finding.get("locator"),
                            "message": finding.get("message"),
                        },
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=False,
                    ).encode("utf-8")
                )
                findings.append(
                    {
                        "code": finding.get("code"),
                        "severity": severity,
                        "evidence_identity": identity,
                        "fingerprint": obligation_result.finding_fingerprint(
                            obligation_id,
                            finding.get("code"),
                            severity,
                            identity,
                            artifact_binding["sha256"],
                        ),
                        "disposition": "open",
                    }
                )
            execution_status = "completed"
            outcome = "findings" if findings else "clean"
            result_created_at = created_at
        else:
            findings = report["findings"]
            execution_status = report["execution_status"]
            outcome = report["outcome"]
            result_created_at = report["created_at"]
        result: dict[str, Any] = {
            "schema_version": "1.0.0",
            "obligation_id": obligation_id,
            "adapter_version": adapter["adapter_version"],
            "artifact": artifact_binding,
            "policy": policy_binding,
            "report": _binding(project, report_path),
            "activation": adapter["activation"],
            "execution_status": execution_status,
            "outcome": outcome,
            "findings": findings,
            "diagnostic_only": adapter["diagnostic_only"],
            "created_at": result_created_at,
            "adjudications": [],
        }
        if obligation_id != "d-style-profile":
            envelope = {
                "schema_version": "1.0.0",
                "receipt_type": "obligation_verifier_authority",
                "authority_mode": "assignment_dispatch",
                "authority": "dispatch-separated-evaluator",
                "subject": result["report"],
                "claim": _binding(project, claim_path),
                "consumption": _binding(project, consumption_path),
            }
            envelope_path = lane / "authority" / f"{obligation_id}.json"
            result_outputs.append((envelope_path, _canonical(envelope)))
            result["verifier_receipt"] = {
                "path": envelope_path.relative_to(project).as_posix(),
                "sha256": _digest(_canonical(envelope)),
                "byte_length": len(_canonical(envelope)),
            }
        result_path = lane / "results" / f"{obligation_id}.json"
        result_data = _canonical(result)
        result_outputs.append((result_path, result_data))
        result_paths[obligation_id] = result_path
        receipt_rows.append(
            {
                "id": obligation_id,
                "result": {
                    "path": result_path.relative_to(project).as_posix(),
                    "sha256": _digest(result_data),
                    "byte_length": len(result_data),
                },
            }
        )
    result_tx = "obligation-results-" + _digest(
        b"".join(data for _, data in result_outputs)
    )[:16]
    result_marker = lane / "results" / "commit-marker.json"
    result_marker_data = _canonical(
        {
            "schema_version": "1.0.0",
            "publication_type": "typed_obligation_result_batch",
            "state": "committed",
            "transaction_id": result_tx,
            "obligation_ids": sorted(active_ids),
        }
    )
    publish_committed(
        project_root=project,
        transaction_id=result_tx,
        preconditions=[
            *preconditions,
            (consumption_path, _file_digest(consumption_path)),
            *[(path, _file_digest(path)) for path, _ in report_outputs],
        ],
        inventory_preconditions=[],
        outputs=result_outputs,
        marker=(result_marker, result_marker_data),
    )
    statuses: dict[str, str] = {}
    for obligation_id, result_path in result_paths.items():
        result = json.loads(result_path.read_text(encoding="utf-8"))
        try:
            obligation_result.verify_obligation_result(
                result, registry, root=project
            )
            statuses[obligation_id] = "verified"
        except obligation_result.ObligationResultRefusal as exc:
            if exc.code != obligation_result.BLOCKING_OUTCOME:
                raise DraftGovernancePublicationError(
                    f"published result does not validate: {obligation_id}: {exc.code}: {exc}"
                ) from exc
            statuses[obligation_id] = "blocking"
    index_value = {
        "schema_version": "1.0.0",
        "publication_type": "typed_obligation_publication",
        "phase": phase,
        "role": role,
        "milestone": milestone,
        "artifact": artifact_binding,
        "contract": policy_binding,
        "obligation_claim": _binding(project, claim_path),
        "obligation_consumption": _binding(project, consumption_path),
        "receipt_rows": receipt_rows,
        "result_paths": {
            obligation_id: _binding(project, path)
            for obligation_id, path in result_paths.items()
        },
        "statuses": statuses,
        "report_transaction_id": report_tx,
        "result_transaction_id": result_tx,
    }
    index_path = lane / "obligation-publication.json"
    index_data = _canonical(index_value)
    index_tx = "obligation-index-" + _digest(index_data)[:16]
    index_marker = lane / "obligation-publication-commit-marker.json"
    index_marker_data = _canonical(
        {
            "schema_version": "1.0.0",
            "publication_type": "typed_obligation_publication_index",
            "state": "committed",
            "transaction_id": index_tx,
            "index_sha256": _digest(index_data),
        }
    )
    publish_committed(
        project_root=project,
        transaction_id=index_tx,
        preconditions=[
            (artifact_path, _file_digest(artifact_path)),
            (contract_file, _file_digest(contract_file)),
            (claim_path, _file_digest(claim_path)),
            (consumption_path, _file_digest(consumption_path)),
            *[(path, _file_digest(path)) for path in result_paths.values()],
        ],
        inventory_preconditions=[],
        outputs=[(index_path, index_data)],
        marker=(index_marker, index_marker_data),
    )
    return {
        "receipt_rows": receipt_rows,
        "result_paths": result_paths,
        "statuses": statuses,
        "obligation_claim": claim_path,
        "obligation_consumption": consumption_path,
        "report_transaction_id": report_tx,
        "result_transaction_id": result_tx,
        "report_commit_marker": report_marker,
        "result_commit_marker": result_marker,
        "index": index_path,
        "index_commit_marker": index_marker,
    }


def load_obligation_publication(
    project_root: Path, index_path: Path
) -> dict[str, Any]:
    """Load the exact durable handoff needed by the finalizer."""

    project = project_root.resolve(strict=True)
    path = index_path.resolve(strict=True)
    if not path.is_relative_to(project):
        raise DraftGovernancePublicationError("obligation index escapes project")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DraftGovernancePublicationError(f"obligation index is unreadable: {exc}") from exc
    if (
        not isinstance(value, dict)
        or value.get("schema_version") != "1.0.0"
        or value.get("publication_type") != "typed_obligation_publication"
        or not isinstance(value.get("receipt_rows"), list)
        or not isinstance(value.get("result_paths"), dict)
    ):
        raise DraftGovernancePublicationError("obligation index is malformed")
    result_paths: dict[str, Path] = {}
    for obligation_id, binding in value["result_paths"].items():
        if not isinstance(binding, dict) or not isinstance(binding.get("path"), str):
            raise DraftGovernancePublicationError("obligation index result binding is malformed")
        result_path = (project / binding["path"]).resolve(strict=True)
        if (
            not result_path.is_relative_to(project)
            or _binding(project, result_path) != binding
        ):
            raise DraftGovernancePublicationError("obligation index result binding is stale")
        result_paths[obligation_id] = result_path
    return {
        "receipt_rows": value["receipt_rows"],
        "result_paths": result_paths,
        "statuses": value.get("statuses", {}),
        "obligation_claim": (
            project / value["obligation_claim"]["path"]
        ).resolve(strict=True),
        "obligation_consumption": (
            project / value["obligation_consumption"]["path"]
        ).resolve(strict=True),
        "index": path,
    }


def finalize_evidence(
    *,
    project_root: Path,
    artifact: Path,
    contract_path: Path,
    obligation_publication: dict[str, Any],
    phase: str,
    role: str,
    milestone: str,
    evidence_label: str,
    receipt_id: str,
    dispatch_claim: Path,
    dispatch_consumption: Path,
    expected_generation_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Verify and marker-last publish the receipt, envelope, and locator."""

    project = project_root.resolve(strict=True)
    artifact_path = artifact.resolve(strict=True)
    contract_file = contract_path.resolve(strict=True)
    claim_path = dispatch_claim.resolve(strict=True)
    consumption_path = dispatch_consumption.resolve(strict=True)
    lane = publication_lane(
        project,
        milestone=milestone,
        phase=phase,
        evidence_label=evidence_label,
    )
    try:
        contract = json.loads(contract_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DraftGovernancePublicationError(
            f"prepared contract is unreadable: {exc}"
        ) from exc
    result_paths = obligation_publication.get("result_paths")
    receipt_rows = obligation_publication.get("receipt_rows")
    if not isinstance(result_paths, dict) or not isinstance(receipt_rows, list):
        raise DraftGovernancePublicationError(
            "typed-obligation publication result is malformed"
        )
    expected_ids = sorted(
        row["id"]
        for row in contract.get("obligations", [])
        if isinstance(row, dict) and phase in row.get("phases", [])
    )
    if sorted(result_paths) != expected_ids or sorted(
        row.get("id") for row in receipt_rows if isinstance(row, dict)
    ) != expected_ids:
        raise DraftGovernancePublicationError(
            "typed-obligation publication does not cover the phase contract"
        )
    receipt_value = {
        "schema_version": "1.0.0",
        "phase": phase,
        "role": role,
        "contract_sha256": _file_digest(contract_file),
        "artifact": {
            "path": str(artifact_path),
            "sha256": _file_digest(artifact_path),
        },
        "obligations": receipt_rows,
    }
    receipt_path = lane / "obligation-receipt.json"
    receipt_data = _canonical(receipt_value)
    receipt_tx = "draft-governance-receipt-" + _digest(receipt_data)[:16]
    receipt_marker = lane / "obligation-receipt-commit-marker.json"
    receipt_marker_data = _canonical(
        {
            "schema_version": "1.0.0",
            "publication_type": "draft_governance_obligation_receipt",
            "state": "committed",
            "transaction_id": receipt_tx,
            "receipt_sha256": _digest(receipt_data),
        }
    )
    receipt_preconditions = [
        (artifact_path, _file_digest(artifact_path)),
        (contract_file, _file_digest(contract_file)),
        (claim_path, _file_digest(claim_path)),
        (consumption_path, _file_digest(consumption_path)),
        *[
            (Path(path), _file_digest(Path(path)))
            for path in result_paths.values()
        ],
    ]
    publish_committed(
        project_root=project,
        transaction_id=receipt_tx,
        preconditions=receipt_preconditions,
        inventory_preconditions=[],
        outputs=[(receipt_path, receipt_data)],
        marker=(receipt_marker, receipt_marker_data),
    )
    try:
        envelope = draft_governance.verify(
            SimpleNamespace(
                contract=str(contract_file),
                receipt=str(receipt_path),
                artifact=str(artifact_path),
                phase=phase,
                role=role,
                wiki_root=None,
                verifier_out_dir=None,
                semantics_manifest=str(
                    draft_governance.ROOT
                    / "references"
                    / "semantics_manifest.v1.json"
                ),
                requested_independence_level="none",
            )
        )
    except Exception as exc:
        raise DraftGovernancePublicationError(
            f"draft-governance verification refused: {exc}"
        ) from exc
    envelope_path = lane / "verified-envelope.json"
    envelope_data = _canonical(envelope)
    evidence_id = "draft-governance-" + _digest(envelope_data)[:16]
    locator_value = {
        "schema_version": "1.0.0",
        "binding_type": "lifecycle_draft_governance",
        "evidence_id": evidence_id,
        "phase": phase,
        "role": role,
        "target": artifact_path.relative_to(project).as_posix(),
        "receipt_id": receipt_id,
        "semantic_usage": "not_invoked",
        "contract": _root_binding(project, contract_file, "project"),
        "obligation_receipt": {
            "root": "project",
            "path": receipt_path.relative_to(project).as_posix(),
            "sha256": _digest(receipt_data),
        },
        "verified_envelope": {
            "root": "project",
            "path": envelope_path.relative_to(project).as_posix(),
            "sha256": _digest(envelope_data),
        },
        "dispatch_claim": _root_binding(project, claim_path, "project"),
        "dispatch_consumption": _root_binding(
            project, consumption_path, "project"
        ),
        "lifecycle_inventory": _root_binding(
            draft_governance.ROOT,
            LIFECYCLE_INVENTORY,
            "harness",
        ),
    }
    locator_path = lane / "lifecycle.json"
    locator_data = _canonical(locator_value)
    final_tx = "draft-governance-finalize-" + _digest(
        envelope_data + locator_data
    )[:16]
    final_marker = lane / "finalize-commit-marker.json"
    final_marker_data = _canonical(
        {
            "schema_version": "1.0.0",
            "publication_type": "lifecycle_draft_governance",
            "state": "committed",
            "transaction_id": final_tx,
            "evidence_id": evidence_id,
        }
    )
    publish_committed(
        project_root=project,
        transaction_id=final_tx,
        preconditions=[
            *receipt_preconditions,
            (receipt_path, _file_digest(receipt_path)),
        ],
        inventory_preconditions=[],
        outputs=[
            (envelope_path, envelope_data),
            (locator_path, locator_data),
        ],
        marker=(final_marker, final_marker_data),
    )
    try:
        validated = validate_lifecycle_draft_governance_binding(
            locator=locator_path,
            artifact=artifact_path,
            project_root=project,
            expected_phase=phase,
            expected_role=role,
            expected_milestone=milestone,
            expected_receipt_id=receipt_id,
            expected_dispatch_claim=claim_path,
            expected_dispatch_consumption=consumption_path,
            expected_generation_result=expected_generation_result,
        )
    except Exception as exc:
        raise DraftGovernancePublicationError(
            f"published lifecycle locator does not replay: {exc}"
        ) from exc
    return {
        "contract": contract_file,
        "obligation_receipt": receipt_path,
        "verified_envelope": envelope_path,
        "locator": locator_path,
        "commit_marker": final_marker,
        "evidence_id": evidence_id,
        "validated": validated,
    }


__all__ = [
    "DraftGovernancePublicationError",
    "finalize_evidence",
    "load_obligation_publication",
    "prepare_contract",
    "publish_obligation_results",
    "publication_lane",
    "validate_prepared_contract",
]


def _path(value: str) -> Path:
    return Path(value)


def _generation_result(project: Path, locator: Path, artifact: Path) -> dict[str, Any]:
    value = json.loads(locator.read_text(encoding="utf-8"))
    claim = (project / value["dispatch_claim"]["path"]).resolve(strict=True)
    consumption = (
        project / value["dispatch_consumption"]["path"]
    ).resolve(strict=True)
    return validate_lifecycle_draft_governance_binding(
        locator=locator,
        artifact=artifact,
        project_root=project,
        expected_phase="generation",
        expected_role="generator",
        expected_milestone=json.loads(
            (project / value["contract"]["path"]).read_text(encoding="utf-8")
        )["target"],
        expected_receipt_id=value["receipt_id"],
        expected_dispatch_claim=claim,
        expected_dispatch_consumption=consumption,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--project-root", type=_path, required=True)
    prepare.add_argument("--artifact", type=_path, required=True)
    prepare.add_argument("--milestone", required=True)
    prepare.add_argument("--phase", choices=sorted(_PHASES), required=True)
    prepare.add_argument("--role", choices=("generator", "evaluator"), required=True)
    prepare.add_argument("--evidence-label", required=True)
    publish = sub.add_parser("publish-obligations")
    publish.add_argument("--project-root", type=_path, required=True)
    publish.add_argument("--artifact", type=_path, required=True)
    publish.add_argument("--contract", type=_path, required=True)
    publish.add_argument("--phase", choices=sorted(_PHASES), required=True)
    publish.add_argument("--role", choices=("generator", "evaluator"), required=True)
    publish.add_argument("--milestone", required=True)
    publish.add_argument("--evidence-label", required=True)
    publish.add_argument("--obligation-claim", type=_path, required=True)
    publish.add_argument("--adapter-report", action="append", default=[])
    publish.add_argument("--created-at", required=True)
    finalize = sub.add_parser("finalize")
    finalize.add_argument("--project-root", type=_path, required=True)
    finalize.add_argument("--artifact", type=_path, required=True)
    finalize.add_argument("--contract", type=_path, required=True)
    finalize.add_argument("--obligation-index", type=_path, required=True)
    finalize.add_argument("--phase", choices=sorted(_PHASES), required=True)
    finalize.add_argument("--role", choices=("generator", "evaluator"), required=True)
    finalize.add_argument("--milestone", required=True)
    finalize.add_argument("--evidence-label", required=True)
    finalize.add_argument("--receipt-id", required=True)
    finalize.add_argument("--dispatch-claim", type=_path, required=True)
    finalize.add_argument("--dispatch-consumption", type=_path, required=True)
    finalize.add_argument("--generation-locator", type=_path)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare_contract(
                project_root=args.project_root,
                artifact=args.artifact,
                milestone=args.milestone,
                phase=args.phase,
                role=args.role,
                evidence_label=args.evidence_label,
            )
            output = {
                "status": "prepared",
                "contract": str(result["contract_path"]),
                "commit_marker": str(result["commit_marker"]),
                "transaction_id": result["transaction_id"],
            }
        elif args.command == "publish-obligations":
            reports: dict[str, Path] = {}
            for item in args.adapter_report:
                obligation_id, separator, raw_path = item.partition("=")
                if not separator or not obligation_id or obligation_id in reports:
                    raise DraftGovernancePublicationError(
                        "adapter reports must be unique ID=PATH values"
                    )
                reports[obligation_id] = Path(raw_path)
            result = publish_obligation_results(
                project_root=args.project_root,
                artifact=args.artifact,
                contract_path=args.contract,
                phase=args.phase,
                role=args.role,
                milestone=args.milestone,
                evidence_label=args.evidence_label,
                obligation_claim=args.obligation_claim,
                adapter_reports=reports,
                created_at=args.created_at,
            )
            output = {
                "status": "published",
                "obligation_index": str(result["index"]),
                "obligation_consumption": str(result["obligation_consumption"]),
                "statuses": result["statuses"],
            }
        else:
            project = args.project_root.resolve(strict=True)
            obligation_publication = load_obligation_publication(
                project, args.obligation_index
            )
            expected_generation = None
            if args.phase == "evaluation":
                if args.generation_locator is None:
                    raise DraftGovernancePublicationError(
                        "evaluation finalization requires --generation-locator"
                    )
                expected_generation = _generation_result(
                    project,
                    args.generation_locator.resolve(strict=True),
                    args.artifact.resolve(strict=True),
                )
            result = finalize_evidence(
                project_root=project,
                artifact=args.artifact,
                contract_path=args.contract,
                obligation_publication=obligation_publication,
                phase=args.phase,
                role=args.role,
                milestone=args.milestone,
                evidence_label=args.evidence_label,
                receipt_id=args.receipt_id,
                dispatch_claim=args.dispatch_claim,
                dispatch_consumption=args.dispatch_consumption,
                expected_generation_result=expected_generation,
            )
            output = {
                "status": "verified",
                "locator": str(result["locator"]),
                "evidence_id": result["evidence_id"],
                "commit_marker": str(result["commit_marker"]),
            }
    except (DraftGovernancePublicationError, OSError, ValueError, KeyError) as exc:
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "reason_code": "DRAFT-GOVERNANCE-PUBLICATION-REFUSED",
                    "detail": str(exc),
                },
                ensure_ascii=False,
            )
        )
        return 4
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
