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
SEMANTIC_RECEIPT_TYPE = "centroid_semantic_execution"


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
        "status": "binding_resolved",
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


def _binding(row: Any, code: str) -> Path:
    if not isinstance(row, dict) or set(row) != {"path", "sha256"}:
        raise ContractError(code, "evidence binding must contain path and sha256")
    try:
        path = Path(row["path"]).resolve(strict=True)
    except (OSError, TypeError) as exc:
        raise ContractError(code, f"evidence path is unreadable: {row.get('path')}") from exc
    if not path.is_file() or row.get("sha256") != _sha(path):
        raise ContractError(code, f"evidence binding is stale: {path}")
    return path


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(_nonempty(item) for item in value)


def _load_semantic_receipt(paths: list[Path]) -> tuple[Path, dict[str, Any]]:
    matches: list[tuple[Path, dict[str, Any]]] = []
    for path in paths:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if isinstance(value, dict) and value.get("receipt_type") == SEMANTIC_RECEIPT_TYPE:
            matches.append((path, value))
    if len(matches) != 1:
        raise ContractError(
            "DRAFT-POLICY-CENTROID-EVIDENCE",
            "centroid obligation requires exactly one role-produced semantic execution receipt",
        )
    return matches[0]


def _load_product_assurance(paths: list[Path], semantic_path: Path,
                            artifact_path: Path, artifact_sha: str,
                            phase: str) -> tuple[Path, dict[str, Any]]:
    matches: list[tuple[Path, dict[str, Any]]] = []
    for path in paths:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if isinstance(value, dict) and value.get("report_type") == "product_assurance":
            matches.append((path, value))
    if len(matches) != 1:
        raise ContractError(
            "DRAFT-POLICY-PRODUCT-ASSURANCE",
            "centroid evidence must contain exactly one product-assurance report",
        )
    path, report = matches[0]
    artifact = report.get("artifact")
    semantic = report.get("semantic_receipt")
    dimensions = report.get("dimensions")
    if (
        report.get("schema_version") != "1.0.0"
        or report.get("status") not in (
            {"passed", "needs_adjudication"} if phase == "generation" else {"passed"}
        )
        or not isinstance(artifact, dict)
        or artifact.get("path") != str(artifact_path)
        or artifact.get("sha256") != artifact_sha
        or not isinstance(semantic, dict)
        or Path(str(semantic.get("path", ""))).resolve(strict=False) != semantic_path
        or semantic.get("sha256") != _sha(semantic_path)
        or not isinstance(dimensions, dict)
        or any(dimensions.get(key) != "passed" for key in ("quotation", "citation"))
        or (phase == "evaluation" and any(
            dimensions.get(key) != "passed" for key in ("grounding", "register")
        ))
        or (phase == "evaluation" and report.get("findings") != [])
    ):
        raise ContractError(
            "DRAFT-POLICY-PRODUCT-ASSURANCE",
            "product assurance does not pass all dimensions for the exact semantic receipt and artifact",
        )
    return path, report


def _packet_members(packet: dict[str, Any]) -> dict[str, dict[str, Any]]:
    members = packet.get("policy", {}).get("members")
    if not isinstance(members, list):
        raise ContractError("DRAFT-POLICY-CENTROID-EVIDENCE", "centroid packet lacks members")
    by_key: dict[str, dict[str, Any]] = {}
    for row in members:
        key = row.get("source_key") if isinstance(row, dict) else None
        if not _nonempty(key) or key in by_key:
            raise ContractError(
                "DRAFT-POLICY-CENTROID-EVIDENCE",
                "centroid packet member keys are missing or duplicated",
            )
        by_key[key] = row
    return by_key


def _verify_semantic_execution(
    evidence_paths: list[Path],
    contract: dict[str, Any],
    artifact_path: Path,
    artifact_sha: str,
    phase: str,
    role: str,
) -> dict[str, Any]:
    semantic_path, semantic = _load_semantic_receipt(evidence_paths)
    base_fields = {
        "schema_version", "receipt_type", "target", "phase", "role", "actor_id",
        "dispatch_id", "artifact", "centroid_packet", "passages", "semantic_assessment",
    }
    expected_fields = base_fields | (
        {"generation_envelope", "adjudications"} if phase == "evaluation" else set()
    )
    if set(semantic) != expected_fields or semantic.get("schema_version") != "2.0.0":
        raise ContractError(
            "DRAFT-POLICY-CENTROID-EVIDENCE",
            "semantic execution receipt fields or version are invalid",
        )
    if (
        semantic.get("target") != contract.get("target")
        or semantic.get("phase") != phase
        or semantic.get("role") != role
        or not _nonempty(semantic.get("actor_id"))
        or not _nonempty(semantic.get("dispatch_id"))
    ):
        raise ContractError(
            "DRAFT-POLICY-CENTROID-EVIDENCE",
            "semantic execution target, phase, role, actor, or dispatch is invalid",
        )

    semantic_artifact = _binding(
        semantic.get("artifact"), "DRAFT-POLICY-CENTROID-EVIDENCE"
    )
    if semantic_artifact != artifact_path or semantic["artifact"].get("sha256") != artifact_sha:
        raise ContractError(
            "DRAFT-POLICY-ARTIFACT-STALE",
            "semantic execution receipt does not bind the exact artifact bytes",
        )

    packet_path = _binding(
        semantic.get("centroid_packet"), "DRAFT-POLICY-CENTROID-EVIDENCE"
    )
    packet = _load(packet_path, "DRAFT-POLICY-CENTROID-EVIDENCE")
    if (
        packet.get("capability") != "centroid-pass"
        or packet.get("status") != "binding_resolved"
        or packet.get("read_only") is not True
        or packet.get("writes_performed") is not False
        or packet.get("semantic_findings") != []
    ):
        raise ContractError(
            "DRAFT-POLICY-CENTROID-EVIDENCE",
            "semantic receipt does not bind a deterministic binding-resolved centroid packet",
        )
    centroid = contract.get("centroid")
    policy = packet.get("policy")
    if not isinstance(centroid, dict) or not isinstance(policy, dict):
        raise ContractError("DRAFT-POLICY-CENTROID-EVIDENCE", "centroid bindings are invalid")
    if packet.get("binding_provenance") != centroid.get("binding_provenance") or any(
        policy.get(key) != centroid.get(key) for key in SHA_KEYS
    ):
        raise ContractError(
            "DRAFT-POLICY-CENTROID-EVIDENCE",
            "centroid packet does not match the prepared profile and pins",
        )
    expected_derivation = centroid.get(
        "generation_derivation" if phase == "generation" else "evaluation_derivation"
    )
    if policy.get("derivation") != expected_derivation:
        raise ContractError(
            "DRAFT-POLICY-CENTROID-EVIDENCE",
            f"centroid packet derivation must be {expected_derivation!r} for {phase}",
        )
    packet_manuscript = packet.get("manuscript")
    if phase == "evaluation" and (
        not isinstance(packet_manuscript, dict)
        or packet_manuscript.get("sha256") != artifact_sha
        or Path(str(packet_manuscript.get("path", ""))).resolve(strict=False) != artifact_path
    ):
        raise ContractError(
            "DRAFT-POLICY-ARTIFACT-STALE",
            "evaluation centroid packet does not bind the exact artifact bytes",
        )

    members = _packet_members(packet)
    passages = semantic.get("passages")
    if not isinstance(passages, list) or not passages:
        raise ContractError(
            "DRAFT-POLICY-CENTROID-EVIDENCE", "semantic execution records no passages"
        )
    passage_fields = {
        "source_key", "use_scope", "source", "locator", "extract", "extraction",
        "quote", "citation", "use",
    }
    seen: set[tuple[str, str, str, str]] = set()
    surface_count = 0
    source_keys: list[str] = []
    for passage in passages:
        if not isinstance(passage, dict) or set(passage) != passage_fields:
            raise ContractError(
                "DRAFT-POLICY-CENTROID-EVIDENCE", "passage record fields are invalid"
            )
        key = passage.get("source_key")
        use_scope = passage.get("use_scope")
        member = members.get(key)
        if member is None or use_scope not in {"surface", "argument"}:
            raise ContractError(
                "DRAFT-POLICY-CENTROID-EVIDENCE",
                "passage source or use scope is not admitted by the centroid packet",
            )
        warrant = member.get("warrant_scope")
        allowed = (
            warrant in {"both", use_scope}
            or (use_scope == "argument" and warrant == "argument-only")
        )
        if not allowed:
            raise ContractError(
                "DRAFT-POLICY-CENTROID-WARRANT",
                f"{key} lacks {use_scope} warrant",
            )
        source_path = _binding(passage.get("source"), "DRAFT-POLICY-CENTROID-EVIDENCE")
        extract_path = _binding(passage.get("extract"), "DRAFT-POLICY-CENTROID-EVIDENCE")
        extraction = passage.get("extraction")
        citation = passage.get("citation")
        if (
            not extract_path.read_bytes()
            or not _nonempty(passage.get("locator"))
            or not _nonempty(passage.get("quote"))
            or not _nonempty(passage.get("use"))
            or not isinstance(extraction, dict)
            or extraction.get("canonical") is not True
            or not isinstance(citation, dict)
        ):
            raise ContractError(
                "DRAFT-POLICY-CENTROID-EVIDENCE",
                "passage extract, extraction, quote, citation, locator, and use must be complete",
            )
        identity = (str(key), str(use_scope), str(source_path), passage["extract"]["sha256"])
        if identity in seen:
            raise ContractError(
                "DRAFT-POLICY-CENTROID-EVIDENCE", "duplicate passage record"
            )
        seen.add(identity)
        source_keys.append(str(key))
        surface_count += int(use_scope == "surface")
    if surface_count == 0:
        raise ContractError(
            "DRAFT-POLICY-CENTROID-WARRANT",
            "semantic execution requires at least one surface-warranted passage",
        )

    assessment = semantic.get("semantic_assessment")
    assessment_fields = {
        "summary", "strengths", "deviations", "warrant_limits", "actionable_findings"
    }
    if (
        not isinstance(assessment, dict)
        or set(assessment) != assessment_fields
        or not _nonempty(assessment.get("summary"))
        or any(not _string_list(assessment.get(key)) for key in assessment_fields - {"summary"})
    ):
        raise ContractError(
            "DRAFT-POLICY-CENTROID-EVIDENCE", "semantic assessment is incomplete"
        )

    assurance_path, _ = _load_product_assurance(
        evidence_paths, semantic_path, artifact_path, artifact_sha, phase
    )
    result = {
        "actor_id": semantic["actor_id"],
        "dispatch_id": semantic["dispatch_id"],
        "semantic_receipt_sha256": _sha(semantic_path),
        "centroid_packet_sha256": _sha(packet_path),
        "passage_count": len(passages),
        "passage_source_keys": sorted(set(source_keys)),
        "product_assurance_sha256": _sha(assurance_path),
    }
    if phase == "evaluation":
        generation_path = _binding(
            semantic.get("generation_envelope"), "DRAFT-POLICY-EVALUATOR-INDEPENDENCE"
        )
        generation = _load(generation_path, "DRAFT-POLICY-EVALUATOR-INDEPENDENCE")
        if (
            generation.get("status") != "verified"
            or generation.get("phase") != "generation"
            or generation.get("role") != "generator"
            or generation.get("target") != contract.get("target")
            or generation.get("artifact_sha256") != artifact_sha
            or not _nonempty(generation.get("actor_id"))
            or not _nonempty(generation.get("dispatch_id"))
            or generation.get("actor_id") == semantic.get("actor_id")
            or generation.get("dispatch_id") == semantic.get("dispatch_id")
        ):
            raise ContractError(
                "DRAFT-POLICY-EVALUATOR-INDEPENDENCE",
                "evaluation is not independent of the verified generation dispatch",
            )
        result["generation_envelope_sha256"] = _sha(generation_path)
    return result


def verify(args: argparse.Namespace) -> dict[str, Any]:
    contract_path = Path(args.contract).resolve(strict=True)
    receipt_path = Path(args.receipt).resolve(strict=True)
    artifact_path = Path(args.artifact).resolve(strict=True)
    contract = _load(contract_path, "DRAFT-POLICY-CONTRACT")
    receipt = _load(receipt_path, "DRAFT-POLICY-RECEIPT")
    if contract.get("status") != "binding_resolved" or contract.get("phase") != args.phase:
        raise ContractError("DRAFT-POLICY-CONTRACT", "contract phase or status is invalid")
    if contract.get("required_role") != args.role or PHASE_ROLE.get(args.phase) != args.role:
        raise ContractError("DRAFT-POLICY-ROLE", "role does not satisfy the contract")
    contract_artifact = contract.get("artifact")
    if not isinstance(contract_artifact, dict) or Path(
        str(contract_artifact.get("path", ""))
    ).resolve(strict=False) != artifact_path:
        raise ContractError("DRAFT-POLICY-ARTIFACT", "contract artifact path is invalid")
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
    if args.phase == "evaluation" and (
        contract_artifact.get("state") != "present"
        or contract_artifact.get("sha256") != artifact_sha
        or contract_artifact.get("bytes") != artifact_path.stat().st_size
    ):
        raise ContractError(
            "DRAFT-POLICY-CONTRACT-ARTIFACT-STALE",
            "evaluation artifact changed after draft-governance prepare",
        )
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
    centroid_evidence_paths: list[Path] = []
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
        bound_paths = [
            _binding(item, "DRAFT-POLICY-EVIDENCE-STALE")
            for item in evidence if isinstance(evidence, list)
        ]
        if obligation_id == f"centroid-{args.phase}":
            centroid_evidence_paths = bound_paths
    semantic = _verify_semantic_execution(
        centroid_evidence_paths, contract, artifact_path, artifact_sha, args.phase, args.role
    )
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
        **semantic,
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
