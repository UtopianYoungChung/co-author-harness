#!/usr/bin/env python3
"""Resolve and verify the all-drafts centroid and policy-obligation contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = ROOT / "references" / "policies" / "draft_governance.v1.json"
READER_PROFILE = ROOT / "references" / "policies" / "reader_accessibility.v1.json"
TARGETS = {"M1", "M2", "M3", "M4", "FINAL"}
PHASE_ROLE = {"generation": "generator", "evaluation": "evaluator"}
TARGET_PATHS = {
    "M1": "milestones/M1_project_memo.md",
    "M2": "milestones/M2_annotated_references.md",
    "M3": "milestones/M3_argument_evidence_outline.md",
    "M4": "milestones/M4_complete_paper_draft.md",
    "FINAL": "milestones/M5_final_paper.md",
}
SHA_KEYS = ("profile_sha256", "attestation_view_pin", "exemplar_view_pin")


class ContractError(RuntimeError):
    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


def _sha_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def _load(path: Path, code: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError(code, f"cannot read valid JSON at {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ContractError(code, f"JSON root must be an object: {path}")
    return data


def _safe_root(path: str) -> Path:
    try:
        root = Path(path).resolve(strict=True)
    except OSError as exc:
        raise ContractError("DRAFT-POLICY-PROJECT", f"project root is unreadable: {exc}") from exc
    if not root.is_dir():
        raise ContractError("DRAFT-POLICY-PROJECT", "project root is not a directory")
    return root


def _artifact(path: str) -> dict[str, Any]:
    target = Path(path).resolve(strict=False)
    if not target.exists():
        return {"path": str(target), "state": "absent", "sha256": None, "bytes": 0}
    if not target.is_file():
        raise ContractError("DRAFT-POLICY-ARTIFACT", f"artifact is not a regular file: {target}")
    payload = target.read_bytes()
    return {"path": str(target), "state": "present", "sha256": _sha_bytes(payload), "bytes": len(payload)}


def _centroid_binding(project: Path) -> dict[str, Any]:
    profile = _load(READER_PROFILE, "DRAFT-POLICY-CENTROID")
    model = profile.get("domain_native_register")
    if not isinstance(model, dict):
        raise ContractError("DRAFT-POLICY-CENTROID", "reader profile lacks domain_native_register")
    expected = model.get("expected_verification")
    if not isinstance(expected, dict):
        raise ContractError("DRAFT-POLICY-CENTROID", "reader profile lacks expected_verification")
    binding = {
        "required": True,
        "binding_provenance": "package-default",
        "profile_path": str(READER_PROFILE),
        "profile_sha256": _sha(READER_PROFILE),
        "attestation_view_pin": expected.get("attestation_view_pin"),
        "exemplar_view_pin": expected.get("exemplar_view_pin"),
        "generation_derivation": "write",
        "evaluation_derivation": "review",
        "revision_derivation": "revise",
        "c7_identity_fence_required": True,
    }
    state_path = project / "reviews" / "phase_state.json"
    if state_path.is_file():
        state = _load(state_path, "DRAFT-POLICY-CENTROID")
        project_binding = (
            state.get("milestone_framework", {})
            .get("policy_bindings", {})
            .get("reader_accessibility")
        )
        if isinstance(project_binding, dict):
            missing = [key for key in SHA_KEYS if not isinstance(project_binding.get(key), str)]
            if missing:
                raise ContractError(
                    "DRAFT-POLICY-CENTROID",
                    "project centroid binding lacks: " + ", ".join(missing),
                )
            binding.update({key: project_binding[key] for key in SHA_KEYS})
            binding["binding_provenance"] = "project"
    if any(not isinstance(binding.get(key), str) or len(binding[key]) != 64 for key in SHA_KEYS):
        raise ContractError("DRAFT-POLICY-CENTROID", "centroid profile or pins are invalid")
    return binding


def prepare(args: argparse.Namespace) -> dict[str, Any]:
    project = _safe_root(args.project_root)
    if args.target not in TARGETS:
        raise ContractError("DRAFT-POLICY-TARGET", f"unsupported target: {args.target}")
    if args.phase not in PHASE_ROLE:
        raise ContractError("DRAFT-POLICY-PHASE", f"unsupported phase: {args.phase}")
    if args.role != PHASE_ROLE[args.phase]:
        raise ContractError(
            "DRAFT-POLICY-ROLE",
            f"role {args.role!r} does not satisfy phase {args.phase!r}",
        )
    policy = _load(POLICY_PATH, "DRAFT-POLICY-CONTRACT")
    target_policy = policy.get("targets", {}).get(args.target)
    if not isinstance(target_policy, dict) or not all(
        target_policy.get(key) is True
        for key in ("centroid_generation_required", "centroid_evaluation_required")
    ):
        raise ContractError("DRAFT-POLICY-TARGET", f"target is not fully governed: {args.target}")
    obligations: list[dict[str, Any]] = []
    for row in policy.get("obligations", []):
        if not isinstance(row, dict):
            raise ContractError("DRAFT-POLICY-CONTRACT", "obligation row must be an object")
        paths = []
        for rel in row.get("paths", []):
            source = (ROOT / rel).resolve()
            if not source.is_file():
                raise ContractError("DRAFT-POLICY-PATH", f"governing path is missing: {rel}")
            paths.append({"path": rel, "sha256": _sha(source)})
        obligations.append({
            "id": row.get("id"),
            "phases": row.get("phases"),
            "activation": row.get("activation"),
            "required_this_phase": args.phase in row.get("phases", []),
            "sources": paths,
        })
    return {
        "schema_version": "1.0.0",
        "status": "ready",
        "policy": {
            "path": str(POLICY_PATH),
            "sha256": _sha(POLICY_PATH),
            "policy_id": policy.get("policy_id"),
        },
        "project_root": str(project),
        "target": args.target,
        "phase": args.phase,
        "required_role": PHASE_ROLE[args.phase],
        "artifact": _artifact(args.artifact or str(project / TARGET_PATHS[args.target])),
        "artifact_presence_rule": policy.get("artifact_presence_rule"),
        "centroid": _centroid_binding(project),
        "obligations": obligations,
    }


def _binding(row: Any, code: str) -> None:
    if not isinstance(row, dict) or set(row) != {"path", "sha256"}:
        raise ContractError(code, "evidence binding must contain path and sha256")
    try:
        path = Path(row["path"]).resolve(strict=True)
    except (OSError, TypeError) as exc:
        raise ContractError(code, f"evidence path is unreadable: {row.get('path')}") from exc
    if not path.is_file() or row.get("sha256") != _sha(path):
        raise ContractError(code, f"evidence binding is stale: {path}")


def verify(args: argparse.Namespace) -> dict[str, Any]:
    contract_path = Path(args.contract).resolve(strict=True)
    receipt_path = Path(args.receipt).resolve(strict=True)
    artifact_path = Path(args.artifact).resolve(strict=True)
    contract = _load(contract_path, "DRAFT-POLICY-CONTRACT")
    receipt = _load(receipt_path, "DRAFT-POLICY-RECEIPT")
    if contract.get("status") != "ready" or contract.get("phase") != args.phase:
        raise ContractError("DRAFT-POLICY-CONTRACT", "contract phase or status is invalid")
    if contract.get("required_role") != args.role or PHASE_ROLE.get(args.phase) != args.role:
        raise ContractError("DRAFT-POLICY-ROLE", "role does not satisfy the contract")
    required_receipt = {
        "schema_version", "phase", "role", "contract_sha256", "artifact", "obligations"
    }
    if set(receipt) != required_receipt or receipt.get("schema_version") != "1.0.0":
        raise ContractError("DRAFT-POLICY-RECEIPT", "receipt fields or version are invalid")
    if receipt.get("phase") != args.phase or receipt.get("role") != args.role:
        raise ContractError("DRAFT-POLICY-ROLE", "receipt phase or role is invalid")
    if receipt.get("contract_sha256") != _sha(contract_path):
        raise ContractError("DRAFT-POLICY-CONTRACT-STALE", "receipt does not bind the current contract")
    artifact = receipt.get("artifact")
    if not isinstance(artifact, dict) or artifact.get("path") != str(artifact_path):
        raise ContractError("DRAFT-POLICY-ARTIFACT", "receipt artifact path is invalid")
    artifact_sha = _sha(artifact_path)
    if artifact.get("sha256") != artifact_sha:
        raise ContractError("DRAFT-POLICY-ARTIFACT-STALE", "receipt artifact hash is stale")
    rows = receipt.get("obligations")
    if not isinstance(rows, list):
        raise ContractError("DRAFT-POLICY-RECEIPT", "obligations must be an array")
    by_id = {row.get("id"): row for row in rows if isinstance(row, dict)}
    required = {
        row["id"]: row for row in contract.get("obligations", [])
        if isinstance(row, dict) and args.phase in row.get("phases", [])
    }
    missing = sorted(set(required) - set(by_id))
    if missing:
        raise ContractError(
            "DRAFT-POLICY-OBLIGATION-MISSING",
            "receipt omits: " + ", ".join(missing),
        )
    for obligation_id, contract_row in required.items():
        row = by_id[obligation_id]
        if set(row) != {"id", "status", "evidence", "rationale"}:
            raise ContractError("DRAFT-POLICY-RECEIPT", f"invalid obligation row: {obligation_id}")
        status = row.get("status")
        if status not in {"applied", "not_applicable"}:
            raise ContractError("DRAFT-POLICY-RECEIPT", f"invalid status for {obligation_id}")
        if status == "not_applicable" and contract_row.get("activation") == "always":
            raise ContractError(
                "DRAFT-POLICY-OBLIGATION-MISSING",
                f"always-on obligation cannot be waived: {obligation_id}",
            )
        if not isinstance(row.get("rationale"), str) or not row["rationale"].strip():
            raise ContractError("DRAFT-POLICY-RECEIPT", f"missing rationale for {obligation_id}")
        evidence = row.get("evidence")
        if status == "applied" and (not isinstance(evidence, list) or not evidence):
            raise ContractError("DRAFT-POLICY-RECEIPT", f"missing evidence for {obligation_id}")
        for item in evidence if isinstance(evidence, list) else []:
            _binding(item, "DRAFT-POLICY-EVIDENCE-STALE")
    return {
        "schema_version": "1.0.0",
        "status": "verified",
        "phase": args.phase,
        "role": args.role,
        "target": contract.get("target"),
        "contract_sha256": _sha(contract_path),
        "artifact_sha256": artifact_sha,
        "centroid": contract.get("centroid"),
        "obligation_ids": sorted(required),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("--project-root", required=True)
    prepare_parser.add_argument("--artifact")
    prepare_parser.add_argument("--target", choices=sorted(TARGETS), required=True)
    prepare_parser.add_argument("--phase", choices=sorted(PHASE_ROLE), required=True)
    prepare_parser.add_argument(
        "--role", choices=sorted(set(PHASE_ROLE.values())), required=True
    )
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("--contract", required=True)
    verify_parser.add_argument("--receipt", required=True)
    verify_parser.add_argument("--artifact", required=True)
    verify_parser.add_argument("--phase", choices=sorted(PHASE_ROLE), required=True)
    verify_parser.add_argument("--role", choices=sorted(set(PHASE_ROLE.values())), required=True)
    args = parser.parse_args(argv)
    try:
        result = prepare(args) if args.command == "prepare" else verify(args)
    except (ContractError, OSError) as exc:
        code = exc.code if isinstance(exc, ContractError) else "DRAFT-POLICY-IO"
        detail = exc.detail if isinstance(exc, ContractError) else str(exc)
        print(json.dumps({"status": "blocked", "reason_code": code, "detail": detail}, ensure_ascii=False))
        return 4
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
