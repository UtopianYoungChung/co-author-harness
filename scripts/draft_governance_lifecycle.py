#!/usr/bin/env python3
"""Validate graph-independent draft-governance evidence for lifecycle consumers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from jsonschema import Draft202012Validator
from milestone_path_contract import canonical_deliverable


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "references" / "schemas" / "lifecycle_draft_governance_binding.schema.json"
INVENTORY = ROOT / "references" / "draft_governance_lifecycle_inventory.v1.json"


class DraftGovernanceLifecycleError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve(root: Path, row: Any, expected_root: str) -> Path:
    if not isinstance(row, dict) or row.get("root") != expected_root:
        raise DraftGovernanceLifecycleError("LIFECYCLE-DRAFT-GOVERNANCE-ROOT", "binding root differs")
    try:
        path = (root / Path(row["path"])).resolve(strict=True)
    except (KeyError, TypeError, OSError) as exc:
        raise DraftGovernanceLifecycleError("LIFECYCLE-DRAFT-GOVERNANCE-STALE", "binding is unavailable") from exc
    if not path.is_relative_to(root) or not path.is_file() or _sha(path) != row.get("sha256"):
        raise DraftGovernanceLifecycleError("LIFECYCLE-DRAFT-GOVERNANCE-STALE", f"binding is stale: {row.get('path')}")
    return path


def _validate_inventory(path: Path) -> list[Path]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DraftGovernanceLifecycleError(
            "LIFECYCLE-DRAFT-GOVERNANCE-INVENTORY", str(exc)
        ) from exc
    if (
        not isinstance(value, dict)
        or set(value) != {"schema_version", "inventory_type", "semantic_usage", "members"}
        or value.get("schema_version") != "1.0.0"
        or value.get("inventory_type") != "graph_independent_draft_governance_lifecycle"
        or value.get("semantic_usage") != "not_invoked"
        or not isinstance(value.get("members"), list)
    ):
        raise DraftGovernanceLifecycleError(
            "LIFECYCLE-DRAFT-GOVERNANCE-INVENTORY", "inventory envelope is malformed"
        )
    expected = {
        "scripts/draft_governance_lifecycle.py",
        "references/schemas/lifecycle_draft_governance_binding.schema.json",
    }
    members: list[Path] = []
    observed: set[str] = set()
    for row in value["members"]:
        if not isinstance(row, dict) or set(row) != {"path", "sha256"}:
            raise DraftGovernanceLifecycleError(
                "LIFECYCLE-DRAFT-GOVERNANCE-INVENTORY", "inventory member is malformed"
            )
        relative = row.get("path")
        if not isinstance(relative, str):
            raise DraftGovernanceLifecycleError(
                "LIFECYCLE-DRAFT-GOVERNANCE-INVENTORY", "inventory member path is malformed"
            )
        member = (ROOT / relative).resolve()
        if (
            not member.is_relative_to(ROOT)
            or not member.is_file()
            or _sha(member) != row.get("sha256")
        ):
            raise DraftGovernanceLifecycleError(
                "LIFECYCLE-DRAFT-GOVERNANCE-INVENTORY", f"inventory member is stale: {relative}"
            )
        observed.add(relative)
        members.append(member)
    if observed != expected:
        raise DraftGovernanceLifecycleError(
            "LIFECYCLE-DRAFT-GOVERNANCE-INVENTORY", "inventory membership is incomplete"
        )
    return members


def validate_lifecycle_draft_governance_binding(
    *, locator: Path, artifact: Path, project_root: Path,
    expected_phase: str, expected_role: str,
    expected_milestone: str,
    expected_receipt_id: str,
    expected_dispatch_claim: Path,
    expected_dispatch_consumption: Path,
    expected_generation_result: dict[str, Any] | None = None,
    _test_authority_adapter: Any | None = None,
) -> dict[str, Any]:
    """Replay current v2 policy resolution and bind its exact role evidence."""
    project = project_root.resolve(strict=True)
    locator = locator.resolve(strict=True)
    artifact = artifact.resolve(strict=True)
    if not locator.is_relative_to(project) or not artifact.is_relative_to(project):
        raise DraftGovernanceLifecycleError("LIFECYCLE-DRAFT-GOVERNANCE-ROOT", "evidence escapes the project root")
    try:
        value = json.loads(locator.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise TypeError("locator root must be an object")
        Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(value)
    except Exception as exc:
        raise DraftGovernanceLifecycleError("LIFECYCLE-DRAFT-GOVERNANCE-INVALID", str(exc)) from exc
    if value.get("phase") != expected_phase or value.get("role") != expected_role:
        raise DraftGovernanceLifecycleError("LIFECYCLE-DRAFT-GOVERNANCE-DISPOSITION", "phase or role differs from the gate")

    contract_path = _resolve(project, value["contract"], "project")
    receipt_path = _resolve(project, value["obligation_receipt"], "project")
    envelope_path = _resolve(project, value["verified_envelope"], "project")
    dispatch_claim = _resolve(project, value["dispatch_claim"], "project")
    dispatch_consumption = _resolve(project, value["dispatch_consumption"], "project")
    inventory_path = _resolve(ROOT, value["lifecycle_inventory"], "harness")
    if inventory_path != INVENTORY.resolve(strict=True):
        raise DraftGovernanceLifecycleError(
            "LIFECYCLE-DRAFT-GOVERNANCE-INVENTORY",
            "lifecycle inventory path differs from the canonical inventory",
        )
    inventory_members = _validate_inventory(inventory_path)
    expected_dispatch_claim = expected_dispatch_claim.resolve(strict=True)
    expected_dispatch_consumption = expected_dispatch_consumption.resolve(strict=True)
    if (
        dispatch_claim != expected_dispatch_claim
        or dispatch_consumption != expected_dispatch_consumption
        or value.get("receipt_id") != expected_receipt_id
    ):
        raise DraftGovernanceLifecycleError(
            "LIFECYCLE-DRAFT-GOVERNANCE-DISPATCH",
            "locator dispatch or receipt identity differs from the expected authority",
        )
    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DraftGovernanceLifecycleError("LIFECYCLE-DRAFT-GOVERNANCE-INVALID", str(exc)) from exc

    expected_id = "draft-governance-" + _sha(envelope_path)[:16]
    if value.get("evidence_id") != expected_id:
        raise DraftGovernanceLifecycleError("LIFECYCLE-DRAFT-GOVERNANCE-STALE", "evidence identity differs from the verified envelope")
    try:
        import draft_governance
        public_target = contract["target"]
        canonical_target = canonical_deliverable(expected_milestone)
        artifact_relative = artifact.relative_to(project).as_posix()
        if (
            public_target != expected_milestone
            or value.get("target") != canonical_target
            or artifact_relative != canonical_target
        ):
            raise DraftGovernanceLifecycleError(
                "LIFECYCLE-DRAFT-GOVERNANCE-DISPOSITION",
                "contract milestone, locator target, and canonical artifact path differ",
            )
        fresh = draft_governance.prepare(SimpleNamespace(
            project_root=str(project), target=public_target, phase=expected_phase,
            role=expected_role, artifact=str(artifact),
        ))
    except DraftGovernanceLifecycleError:
        raise
    except Exception as exc:
        raise DraftGovernanceLifecycleError("LIFECYCLE-DRAFT-GOVERNANCE-STALE", f"current policy resolution failed: {exc}") from exc
    if fresh != contract:
        raise DraftGovernanceLifecycleError("LIFECYCLE-DRAFT-GOVERNANCE-STALE", "resolved contract differs from current v2 policy")
    centroid = contract.get("centroid")
    obligation_ids = sorted(
        row["id"] for row in contract.get("obligations", [])
        if isinstance(row, dict) and expected_phase in row.get("phases", [])
    )
    receipt_ids = sorted(
        row.get("id") for row in receipt.get("obligations", []) if isinstance(row, dict)
    )
    artifact_sha = _sha(artifact)
    if (
        not isinstance(centroid, dict)
        or centroid.get("required") is not False
        or centroid.get("semantic_usage") != "not_invoked"
        or value.get("semantic_usage") != "not_invoked"
        or envelope.get("status") != "verified"
        or envelope.get("phase") != expected_phase
        or envelope.get("role") != expected_role
        or envelope.get("target") != public_target
        or envelope.get("contract_sha256") != _sha(contract_path)
        or envelope.get("artifact_sha256") != artifact_sha
        or envelope.get("semantic_usage") != "not_invoked"
        or envelope.get("centroid") != centroid
        or envelope.get("obligation_ids") != obligation_ids
        or receipt.get("phase") != expected_phase
        or receipt.get("role") != expected_role
        or receipt.get("contract_sha256") != _sha(contract_path)
        or receipt.get("artifact", {}).get("sha256") != artifact_sha
        or receipt_ids != obligation_ids
    ):
        raise DraftGovernanceLifecycleError("LIFECYCLE-DRAFT-GOVERNANCE-STALE", "verified envelope, receipt, artifact, or current policy differs")
    try:
        replayed = draft_governance.verify(
            SimpleNamespace(
                contract=str(contract_path), receipt=str(receipt_path),
                artifact=str(artifact), phase=expected_phase, role=expected_role,
                wiki_root=None, verifier_out_dir=None,
                semantics_manifest=str(ROOT / "references" / "semantics_manifest.v1.json"),
                requested_independence_level="none",
            ),
            _test_authority_adapter=_test_authority_adapter,
        )
    except Exception as exc:
        raise DraftGovernanceLifecycleError(
            "LIFECYCLE-DRAFT-GOVERNANCE-STALE", f"draft-governance replay refused: {exc}"
        ) from exc
    if replayed != envelope:
        raise DraftGovernanceLifecycleError(
            "LIFECYCLE-DRAFT-GOVERNANCE-STALE", "stored verified envelope differs from fresh replay"
        )

    try:
        from assignment_dispatch_claim import (
            binding as dispatch_binding,
            validate_consumed_claim_for_context,
        )
        validate_consumed_claim_for_context(
            project,
            dispatch_claim,
            dispatch_consumption,
            expected_role=expected_role,
            expected_target=value["target"],
            expected_receipt_id=value["receipt_id"],
            expected_artifact_sha256=artifact_sha,
            expected_generation_evidence_id=(
                expected_generation_result["locator"]["evidence_id"]
                if expected_phase == "evaluation" and expected_generation_result is not None
                else None
            ),
        )
        claim_value = json.loads(dispatch_claim.read_text(encoding="utf-8"))
    except Exception as exc:
        code = getattr(exc, "code", "LIFECYCLE-DRAFT-GOVERNANCE-DISPATCH")
        message = getattr(exc, "message", str(exc))
        raise DraftGovernanceLifecycleError(
            "LIFECYCLE-DRAFT-GOVERNANCE-DISPATCH", f"{code}: {message}"
        ) from exc
    if claim_value.get("claim_kind") != expected_phase:
        raise DraftGovernanceLifecycleError(
            "LIFECYCLE-DRAFT-GOVERNANCE-DISPATCH", "dispatch claim phase differs"
        )

    if expected_phase == "evaluation":
        if expected_generation_result is None:
            raise DraftGovernanceLifecycleError(
                "LIFECYCLE-DRAFT-GOVERNANCE-DISPATCH",
                "evaluation replay lacks the complete generation authority",
            )
        expected_identity = expected_generation_result.get("identity")
        authority = claim_value.get("generation_draft_governance")
        if not isinstance(expected_identity, dict) or not isinstance(authority, dict):
            raise DraftGovernanceLifecycleError(
                "LIFECYCLE-DRAFT-GOVERNANCE-DISPATCH",
                "evaluation generation authority is malformed",
            )
        if (
            authority.get("evidence_id")
            != expected_generation_result["locator"].get("evidence_id")
            or authority.get("binding") != expected_identity.get("locator")
            or claim_value.get("generation_claim") != expected_identity.get("dispatch_claim")
            or claim_value.get("generation_consumption")
            != expected_identity.get("dispatch_consumption")
            or claim_value.get("receipt_id")
            != expected_generation_result["locator"].get("receipt_id")
        ):
            raise DraftGovernanceLifecycleError(
                "LIFECYCLE-DRAFT-GOVERNANCE-DISPATCH",
                "evaluation does not reuse the exact generation locator, claim, consumption, and receipt",
            )

    dependencies = []
    for path in sorted({
        locator, artifact, contract_path, receipt_path, envelope_path,
        dispatch_claim, dispatch_consumption, inventory_path, *inventory_members,
    }, key=str):
        dependencies.append({"path": str(path), "sha256": _sha(path)})
    return {
        "locator": value,
        "envelope": envelope,
        "dependencies": dependencies,
        "identity": {
            "locator": dispatch_binding(
                project, locator, "lifecycle_draft_governance"
            ),
            "dispatch_claim": dispatch_binding(
                project, dispatch_claim,
                "assignment_generation_claim"
                if expected_phase == "generation"
                else "assignment_evaluation_claim",
            ),
            "dispatch_consumption": dispatch_binding(
                project, dispatch_consumption, "assignment_dispatch_consumption"
            ),
        },
    }


__all__ = [
    "DraftGovernanceLifecycleError",
    "validate_lifecycle_draft_governance_binding",
]
