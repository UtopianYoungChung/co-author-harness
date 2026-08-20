#!/usr/bin/env python3
"""Resolve and verify the all-drafts centroid and policy-obligation contract."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from draft_evidence_verifier import (
    VerifierError,
    publish_verifier_transaction,
    recompute_product_assurance,
    report_payload_sha256,
    validate_verifier_transaction,
)
from datetime import datetime, timezone

from destination_capability import DestinationRefused, assert_writable
from obligation_result import (
    ObligationResultRefusal,
    _dstyle_evidence_identity,
    _dstyle_report_from_snapshots,
    finding_fingerprint,
    validate_obligation_registry,
    verify_obligation_result,
)


ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = ROOT / "references" / "policies" / "draft_governance.v1.json"
OBLIGATION_REGISTRY_PATH = (
    ROOT / "references" / "policies" / "obligation_result_registry.v1.json"
)
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


def _resolved_obligation_registry(
    policy: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    registry = _load(OBLIGATION_REGISTRY_PATH, "DRAFT-POLICY-OBLIGATION-SCHEMA")
    try:
        adapters = validate_obligation_registry(registry)
    except ObligationResultRefusal as exc:
        raise ContractError(exc.code, exc.detail) from exc
    policy_rows = {
        row.get("id"): row
        for row in policy.get("obligations", [])
        if isinstance(row, dict) and isinstance(row.get("id"), str)
    }
    if set(policy_rows) != set(adapters):
        raise ContractError(
            "DRAFT-POLICY-OBLIGATION-UNKNOWN",
            "draft-governance policy and obligation registry IDs differ",
        )
    for obligation_id, policy_row in policy_rows.items():
        adapter = adapters[obligation_id]
        if (
            adapter.get("activation") != policy_row.get("activation")
            or adapter.get("phases") != policy_row.get("phases")
        ):
            raise ContractError(
                "DRAFT-POLICY-OBLIGATION-SCHEMA",
                f"registry activation or phases split from policy: {obligation_id}",
            )
    return registry, adapters


def _contract_obligations(
    policy: dict[str, Any],
    adapters: dict[str, dict[str, Any]],
    phase: str,
) -> list[dict[str, Any]]:
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
        adapter = adapters.get(row.get("id"))
        if adapter is None:
            raise ContractError(
                "DRAFT-POLICY-OBLIGATION-UNKNOWN",
                f"obligation is absent from the closed registry: {row.get('id')}",
            )
        obligations.append({
            "id": row.get("id"),
            "phases": row.get("phases"),
            "activation": row.get("activation"),
            "required_this_phase": phase in row.get("phases", []),
            "sources": paths,
            "typed_result_required": True,
            "result_adapter": {
                key: adapter[key]
                for key in (
                    "adapter_id",
                    "adapter_version",
                    "report_schema",
                    "adjudication_schema",
                    "blocking_threshold",
                    "diagnostic_only",
                )
            },
        })
    return obligations


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
    state_path = project / "reviews" / "phase_state.json"
    if state_path.is_file():
        state = _load(state_path, "DRAFT-POLICY-CENTROID")
        project_binding = (
            state.get("milestone_framework", {})
            .get("policy_bindings", {})
            .get("reader_accessibility")
        )
        if (
            isinstance(project_binding, dict)
            and project_binding.get("binding_version") == "2.0.0"
            and project_binding.get("semantic_usage") == "not_invoked"
        ):
            return {
                "required": False,
                "binding_provenance": "project",
                "binding_version": "2.0.0",
                "profile_path": project_binding.get("profile_path"),
                "profile_sha256": project_binding.get("profile_sha256"),
                "resolved_sha256": project_binding.get("resolved_sha256"),
                "semantic_usage": "not_invoked",
                "unavailable_code": "GRAPH_GOVERNED_GENERATION_UNAVAILABLE",
                "generation_derivation": "not_invoked",
                "evaluation_derivation": "not_invoked",
                "revision_derivation": "not_invoked",
                "c7_identity_fence_required": True,
            }
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


def _effective_obligations(
    policy: dict[str, Any], adapters: dict[str, Any], phase: str, *, centroid_required: bool,
) -> list[dict[str, Any]]:
    obligations = _contract_obligations(policy, adapters, phase)
    if centroid_required:
        return obligations
    return [row for row in obligations if row.get("id") != f"centroid-{phase}"]


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
    registry, adapters = _resolved_obligation_registry(policy)
    target_policy = policy.get("targets", {}).get(args.target)
    if not isinstance(target_policy, dict) or not all(
        target_policy.get(key) is True
        for key in ("centroid_generation_required", "centroid_evaluation_required")
    ):
        raise ContractError("DRAFT-POLICY-TARGET", f"target is not fully governed: {args.target}")
    centroid = _centroid_binding(project)
    obligations = _effective_obligations(
        policy, adapters, args.phase, centroid_required=centroid.get("required") is True,
    )
    return {
        "schema_version": "1.0.0",
        "status": "binding_resolved",
        "policy": {
            "path": str(POLICY_PATH),
            "sha256": _sha(POLICY_PATH),
            "policy_id": policy.get("policy_id"),
        },
        "obligation_registry": {
            "path": str(OBLIGATION_REGISTRY_PATH),
            "sha256": _sha(OBLIGATION_REGISTRY_PATH),
            "byte_length": OBLIGATION_REGISTRY_PATH.stat().st_size,
            "registry_id": registry.get("registry_id"),
        },
        "project_root": str(project),
        "target": args.target,
        "phase": args.phase,
        "required_role": PHASE_ROLE[args.phase],
        "artifact": _artifact(args.artifact or str(project / TARGET_PATHS[args.target])),
        "artifact_presence_rule": policy.get("artifact_presence_rule"),
            "centroid": centroid,
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


def _typed_result_binding(row: Any, project: Path) -> Path:
    code = "DRAFT-POLICY-OBLIGATION-STALE"
    if not isinstance(row, dict) or set(row) != {"path", "sha256", "byte_length"}:
        raise ContractError(code, "typed result binding must contain path, sha256, and byte_length")
    raw = row.get("path")
    if not isinstance(raw, str) or not raw:
        raise ContractError(code, "typed result path is missing")
    source = Path(raw)
    if not source.is_absolute():
        source = project / source
    if source.is_symlink():
        raise ContractError(code, f"typed result path cannot be a link: {source}")
    try:
        path = source.resolve(strict=True)
        path.relative_to(project.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise ContractError(code, f"typed result path is outside the project or unreadable: {source}") from exc
    if (
        not path.is_file()
        or row.get("sha256") != _sha(path)
        or row.get("byte_length") != path.stat().st_size
    ):
        raise ContractError(code, f"typed result binding is stale: {path}")
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


def _reject_supplied_product_assurance(paths: list[Path]) -> None:
    for path in paths:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if isinstance(value, dict) and value.get("report_type") == "product_assurance":
            raise ContractError(
                "ASSURANCE-FORGED",
                "role-supplied product assurance cannot prove its own result",
            )


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

    _reject_supplied_product_assurance(evidence_paths)
    try:
        assurance = recompute_product_assurance(
            artifact=artifact_path,
            semantic_receipt=semantic_path,
            phase=phase,
        )
    except VerifierError as exc:
        raise ContractError(exc.code, exc.message) from exc
    result = {
        "actor_id": semantic["actor_id"],
        "dispatch_id": semantic["dispatch_id"],
        "semantic_receipt_sha256": _sha(semantic_path),
        "centroid_packet_sha256": _sha(packet_path),
        "passage_count": len(passages),
        "passage_source_keys": sorted(set(source_keys)),
        "product_assurance_sha256": report_payload_sha256(assurance),
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


def _verify_current_semantic_transaction(
    *,
    args: argparse.Namespace,
    semantic_path: Path,
    semantic: dict[str, Any],
    evidence_paths: list[Path],
    contract: dict[str, Any],
    artifact_path: Path,
    artifact_sha: str,
) -> dict[str, Any]:
    _reject_supplied_product_assurance(evidence_paths)
    if (
        semantic.get("schema_version") != "3.0.0"
        or semantic.get("target") != contract.get("target")
        or semantic.get("phase") != args.phase
        or semantic.get("role") != args.role
        or semantic.get("artifact", {}).get("sha256") != artifact_sha
    ):
        raise ContractError(
            "DRAFT-POLICY-CENTROID-EVIDENCE",
            "current semantic receipt does not match the draft-governance context",
        )
    if not args.wiki_root or not args.verifier_out_dir:
        raise ContractError(
            "DRAFT-POLICY-CENTROID-EVIDENCE",
            "semantic receipt 3.0.0 requires --wiki-root and --verifier-out-dir",
        )
    project_root = Path(str(contract.get("project_root", ""))).resolve(strict=True)
    semantics_manifest = Path(args.semantics_manifest).resolve(strict=True)
    try:
        published = publish_verifier_transaction(
            artifact=artifact_path,
            semantic_receipt=semantic_path,
            phase=args.phase,
            project_root=project_root,
            wiki_root=Path(args.wiki_root),
            harness_root=ROOT,
            semantics_manifest=semantics_manifest,
            out_dir=Path(args.verifier_out_dir),
            requested_independence_level=args.requested_independence_level,
        )
        transaction = validate_verifier_transaction(
            transaction=published["transaction"],
            publication_manifest=published["publication_manifest"],
            commit_marker=published["commit_marker"],
            artifact=artifact_path,
            semantic_receipt=semantic_path,
            project_root=project_root,
            wiki_root=Path(args.wiki_root),
            harness_root=ROOT,
            semantics_manifest=semantics_manifest,
        )
    except VerifierError as exc:
        raise ContractError(exc.code, exc.message) from exc
    return {
        "semantic_receipt_sha256": _sha(semantic_path),
        "product_assurance_sha256": _sha(published["product_assurance"]),
        "verifier_transaction_id": transaction["transaction_id"],
        "verifier_transaction_path": str(published["transaction"]),
        "verifier_transaction_sha256": _sha(published["transaction"]),
        "verifier_commit_marker_path": str(published["commit_marker"]),
        "verifier_commit_marker_sha256": _sha(published["commit_marker"]),
        "product_disposition": transaction["product_disposition"],
        "requested_independence_level": transaction["requested_independence_level"],
        "achieved_independence_level": transaction["achieved_independence_level"],
    }


def verify(
    args: argparse.Namespace,
    *,
    _test_authority_adapter: Any | None = None,
) -> dict[str, Any]:
    contract_path = Path(args.contract).resolve(strict=True)
    receipt_path = Path(args.receipt).resolve(strict=True)
    artifact_path = Path(args.artifact).resolve(strict=True)
    contract = _load(contract_path, "DRAFT-POLICY-CONTRACT")
    receipt = _load(receipt_path, "DRAFT-POLICY-RECEIPT")
    project = Path(str(contract.get("project_root", ""))).resolve(strict=True)
    try:
        artifact_rel = artifact_path.relative_to(project).as_posix()
        contract_rel = contract_path.relative_to(project).as_posix()
    except ValueError as exc:
        raise ContractError(
            "DRAFT-POLICY-OBLIGATION-STALE",
            "artifact and resolved contract must remain below the bound project root",
        ) from exc
    current_policy = _load(POLICY_PATH, "DRAFT-POLICY-CONTRACT")
    registry, adapters = _resolved_obligation_registry(current_policy)
    policy_binding = contract.get("policy")
    if (
        not isinstance(policy_binding, dict)
        or policy_binding.get("path") != str(POLICY_PATH)
        or policy_binding.get("sha256") != _sha(POLICY_PATH)
        or policy_binding.get("policy_id") != current_policy.get("policy_id")
    ):
        raise ContractError("DRAFT-POLICY-CONTRACT-STALE", "bound draft-governance policy is stale")
    registry_binding = contract.get("obligation_registry")
    if (
        not isinstance(registry_binding, dict)
        or set(registry_binding) != {"path", "sha256", "byte_length", "registry_id"}
        or registry_binding.get("path") != str(OBLIGATION_REGISTRY_PATH)
        or registry_binding.get("sha256") != _sha(OBLIGATION_REGISTRY_PATH)
        or registry_binding.get("byte_length") != OBLIGATION_REGISTRY_PATH.stat().st_size
        or registry_binding.get("registry_id") != registry.get("registry_id")
    ):
        raise ContractError(
            "DRAFT-POLICY-OBLIGATION-STALE",
            "bound obligation registry is stale",
        )
    if contract.get("status") != "binding_resolved" or contract.get("phase") != args.phase:
        raise ContractError("DRAFT-POLICY-CONTRACT", "contract phase or status is invalid")
    centroid_contract = contract.get("centroid")
    centroid_required = isinstance(centroid_contract, dict) and centroid_contract.get("required") is True
    if contract.get("obligations") != _effective_obligations(
        current_policy, adapters, args.phase, centroid_required=centroid_required,
    ):
        raise ContractError(
            "DRAFT-POLICY-OBLIGATION-STALE",
            "contract obligation set or adapter bindings differ from current policy bytes",
        )
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
    if any(not isinstance(row, dict) or not isinstance(row.get("id"), str) for row in rows):
        raise ContractError("DRAFT-POLICY-RECEIPT", "every obligation row needs one string id")
    row_ids = [row["id"] for row in rows]
    if len(set(row_ids)) != len(row_ids):
        raise ContractError("DRAFT-POLICY-RECEIPT", "duplicate obligation result id")
    by_id = {row["id"]: row for row in rows}
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
    extra = sorted(set(by_id) - set(required))
    if extra:
        raise ContractError(
            "DRAFT-POLICY-OBLIGATION-UNKNOWN",
            "receipt includes obligations outside the phase contract: " + ", ".join(extra),
        )
    centroid_evidence_paths: list[Path] = []
    typed_obligation_ids: list[str] = []
    lifecycle_clearing_obligation_ids: list[str] = []
    diagnostic_obligation_ids: list[str] = []
    deferred_obligation_ids: list[str] = []
    for obligation_id, contract_row in required.items():
        row = by_id[obligation_id]
        adapter = adapters.get(obligation_id)
        if adapter is None:
            raise ContractError(
                "DRAFT-POLICY-OBLIGATION-UNKNOWN",
                f"obligation is absent from current registry: {obligation_id}",
            )
        if contract_row.get("typed_result_required") is True:
            if set(row) != {"id", "result"}:
                raise ContractError(
                    "DRAFT-POLICY-OBLIGATION-SCHEMA",
                    f"governed obligation requires one typed result binding: {obligation_id}",
                )
            result_path = _typed_result_binding(row.get("result"), project)
            result = _load(result_path, "DRAFT-POLICY-OBLIGATION-SCHEMA")
            if result.get("obligation_id") != obligation_id:
                raise ContractError(
                    "DRAFT-POLICY-OBLIGATION-UNKNOWN",
                    f"typed result identity differs from receipt row: {obligation_id}",
                )
            result_artifact = result.get("artifact")
            result_policy = result.get("policy")
            if (
                not isinstance(result_artifact, dict)
                or result_artifact.get("path") != artifact_rel
                or result_artifact.get("sha256") != artifact_sha
                or result_artifact.get("byte_length") != artifact_path.stat().st_size
                or not isinstance(result_policy, dict)
                or result_policy.get("path") != contract_rel
                or result_policy.get("sha256") != _sha(contract_path)
                or result_policy.get("byte_length") != contract_path.stat().st_size
            ):
                raise ContractError(
                    "DRAFT-POLICY-OBLIGATION-STALE",
                    f"typed result does not bind the receipt artifact and resolved contract: {obligation_id}",
                )
            if result.get("execution_status") == "not_run":
                _accept_generation_not_run(
                    result,
                    obligation_id=obligation_id,
                    adapter=adapter,
                    phase=args.phase,
                    project=project,
                )
                typed_obligation_ids.append(obligation_id)
                deferred_obligation_ids.append(obligation_id)
                continue
            try:
                verified_result = verify_obligation_result(
                    result,
                    registry,
                    root=project,
                    _test_authority_adapter=_test_authority_adapter,
                )
            except ObligationResultRefusal as exc:
                raise ContractError(exc.code, exc.detail) from exc
            if adapter.get("diagnostic_only") is True:
                if verified_result.get("lifecycle_eligible") is not False:
                    raise ContractError(
                        "DRAFT-POLICY-OBLIGATION-SCHEMA",
                        f"diagnostic adapter claimed lifecycle clearance: {obligation_id}",
                    )
                diagnostic_obligation_ids.append(obligation_id)
            elif verified_result.get("lifecycle_eligible") is not True:
                raise ContractError(
                    "DRAFT-POLICY-OBLIGATION-BLOCKING-OUTCOME",
                    f"typed result is diagnostic-only or non-clearing: {obligation_id}",
                )
            else:
                lifecycle_clearing_obligation_ids.append(obligation_id)
            typed_obligation_ids.append(obligation_id)
            if obligation_id == f"centroid-{args.phase}":
                legacy = result.get("legacy_execution_evidence")
                evidence = legacy.get("evidence") if isinstance(legacy, dict) else None
                if not isinstance(evidence, list) or not evidence:
                    raise ContractError(
                        "DRAFT-POLICY-OBLIGATION-SCHEMA",
                        f"centroid typed result lacks semantic execution evidence: {obligation_id}",
                    )
                centroid_evidence_paths = [
                    _typed_result_binding(binding, project) for binding in evidence
                ]
            continue
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
    if not centroid_required:
        return {
            "schema_version": "1.0.0",
            "status": "verified",
            "phase": args.phase,
            "role": args.role,
            "target": contract.get("target"),
            "contract_sha256": _sha(contract_path),
            "artifact_sha256": artifact_sha,
            "centroid": centroid_contract,
            "obligation_ids": sorted(required),
            "typed_obligation_result_ids": sorted(typed_obligation_ids),
            "lifecycle_clearing_obligation_result_ids": sorted(lifecycle_clearing_obligation_ids),
            "diagnostic_obligation_result_ids": sorted(diagnostic_obligation_ids),
            "deferred_obligation_result_ids": sorted(deferred_obligation_ids),
            "semantic_usage": "not_invoked",
            "graph_capability": "GRAPH_GOVERNED_GENERATION_UNAVAILABLE",
        }
    semantic_path, semantic_value = _load_semantic_receipt(centroid_evidence_paths)
    semantic = (
        _verify_current_semantic_transaction(
            args=args,
            semantic_path=semantic_path,
            semantic=semantic_value,
            evidence_paths=centroid_evidence_paths,
            contract=contract,
            artifact_path=artifact_path,
            artifact_sha=artifact_sha,
        )
        if semantic_value.get("schema_version") == "3.0.0"
        else _verify_semantic_execution(
            centroid_evidence_paths,
            contract,
            artifact_path,
            artifact_sha,
            args.phase,
            args.role,
        )
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
        "typed_obligation_result_ids": sorted(typed_obligation_ids),
        "lifecycle_clearing_obligation_result_ids": sorted(
            lifecycle_clearing_obligation_ids
        ),
        "diagnostic_obligation_result_ids": sorted(diagnostic_obligation_ids),
        "deferred_obligation_result_ids": sorted(deferred_obligation_ids),
        **semantic,
    }


DSTYLE_REPORT_SCHEMA_REL = "scripts/d_style_profile_check.py"
REASON_PROMPT_MEDIATED = "PROMPT-MEDIATED-NOT-DEST-SAFE"
REASON_GRAPH_UNAVAILABLE = "GRAPH_GOVERNED_GENERATION_UNAVAILABLE"
REASON_CENTROID_RECEIPT_ABSENT = "CENTROID-SEMANTIC-RECEIPT-ABSENT"


def _exact_binding(path: Path, project: Path) -> dict[str, str | int]:
    resolved = path.resolve(strict=True)
    rel = resolved.relative_to(project.resolve(strict=True)).as_posix()
    payload = resolved.read_bytes()
    return {"path": rel, "sha256": _sha_bytes(payload), "byte_length": len(payload)}


def _write_json(path: Path, value: dict[str, Any]) -> dict[str, str | int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    path.write_text(payload, encoding="utf-8", newline="\n")
    return {
        "path": path.name,
        "sha256": _sha_bytes(payload.encode("utf-8")),
        "byte_length": path.stat().st_size,
    }


def _accept_generation_not_run(
    result: dict[str, Any],
    *,
    obligation_id: str,
    adapter: dict[str, Any],
    phase: str,
    project: Path,
) -> None:
    """Allow honest generation deferral. Never a scholarly clean."""
    if phase != "generation":
        raise ContractError(
            "DRAFT-POLICY-OBLIGATION-BLOCKING-OUTCOME",
            f"not_run is not allowed at evaluation: {obligation_id}",
        )
    if adapter.get("report_schema", {}).get("path") == DSTYLE_REPORT_SCHEMA_REL:
        raise ContractError(
            "DRAFT-POLICY-OBLIGATION-SCHEMA",
            "d-style-profile cannot be deferred; run the mechanical checker",
        )
    if (
        result.get("execution_status") != "not_run"
        or result.get("outcome") != "error"
        or result.get("findings") != []
        or result.get("verifier_receipt") is not None
        or result.get("diagnostic_only") is not adapter.get("diagnostic_only")
        or result.get("activation") != adapter.get("activation")
        or result.get("adapter_version") != adapter.get("adapter_version")
    ):
        raise ContractError(
            "DRAFT-POLICY-OBLIGATION-SCHEMA",
            f"not_run result is not an honest deferral: {obligation_id}",
        )
    report_path = _typed_result_binding(result.get("report"), project)
    report = _load(report_path, "DRAFT-POLICY-OBLIGATION-SCHEMA")
    expected = {
        "schema_version": result.get("schema_version"),
        "report_type": "obligation_adapter_report",
        "adapter_id": adapter.get("adapter_id"),
        "adapter_version": result.get("adapter_version"),
        "obligation_id": obligation_id,
        "artifact": result.get("artifact"),
        "policy": result.get("policy"),
        "activation": result.get("activation"),
        "execution_status": "not_run",
        "outcome": "error",
        "findings": [],
        "diagnostic_only": result.get("diagnostic_only"),
        "created_at": result.get("created_at"),
    }
    if report != expected:
        raise ContractError(
            "DRAFT-POLICY-OBLIGATION-STALE",
            f"not_run report does not mirror the typed result: {obligation_id}",
        )


def _scaffold_out_dir(args: argparse.Namespace, project: Path) -> Path:
    if args.out_dir and args.shipment_id:
        raise ContractError(
            "DRAFT-POLICY-RECEIPT",
            "pass --out-dir or --shipment-id, not both",
        )
    if args.shipment_id:
        dest = (
            project
            / "reviews"
            / ".harness"
            / "shipments"
            / args.shipment_id
        )
    elif args.out_dir:
        dest = Path(args.out_dir)
    else:
        raise ContractError(
            "DRAFT-POLICY-RECEIPT",
            "scaffold-receipt needs --shipment-id (package shipment lane) or a dest-safe --out-dir",
        )
    dest = dest.resolve()
    assert_writable(dest, purpose="draft-governance scaffold-receipt")
    dest.mkdir(parents=True, exist_ok=True)
    return dest


def _build_dstyle_typed_result(
    *,
    project: Path,
    artifact_path: Path,
    contract_path: Path,
    artifact_rel: str,
    artifact_sha: str,
    created_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    import d_style_profile_check as dstyle

    directives_path = project / "research_notes" / "directives.md"
    directives_exists = directives_path.is_file()
    artifact_text = artifact_path.read_text(encoding="utf-8")
    directives_text = (
        directives_path.read_text(encoding="utf-8") if directives_exists else None
    )
    report = _dstyle_report_from_snapshots(
        dstyle,
        project,
        directives_path,
        directives_exists,
        directives_text,
        artifact_path,
        artifact_text,
    )
    findings: list[dict[str, Any]] = []
    for finding in report.get("findings", []):
        severity = finding.get("severity")
        if severity not in {"ADVISORY", "MINOR", "MAJOR", "BLOCKER"}:
            continue
        evidence_identity = _dstyle_evidence_identity(finding)
        findings.append(
            {
                "code": finding.get("code"),
                "severity": severity,
                "evidence_identity": evidence_identity,
                "fingerprint": finding_fingerprint(
                    "d-style-profile",
                    str(finding.get("code")),
                    severity,
                    evidence_identity,
                    artifact_sha,
                ),
                "disposition": "open",
            }
        )
    result = {
        "schema_version": "1.0.0",
        "obligation_id": "d-style-profile",
        "adapter_version": "1.0.0",
        "artifact": {
            "path": artifact_rel,
            "sha256": artifact_sha,
            "byte_length": artifact_path.stat().st_size,
        },
        "policy": {
            "path": contract_path.relative_to(project).as_posix()
            if contract_path.is_relative_to(project)
            else str(contract_path),
            "sha256": _sha(contract_path),
            "byte_length": contract_path.stat().st_size,
        },
        "activation": "always",
        "execution_status": "completed",
        "outcome": "findings" if findings else "clean",
        "findings": findings,
        "diagnostic_only": False,
        "created_at": created_at,
        "adjudications": [],
    }
    return result, report



def _sanitize_finding_code(raw: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "._:-" else "-" for ch in raw).strip("-")
    if not cleaned or not cleaned[0].isalnum():
        cleaned = "X" + cleaned
    return cleaned[:80]


def _fail_closed_pair(
    *,
    obligation_id: str,
    adapter: dict[str, Any],
    artifact_rel: str,
    artifact_sha: str,
    artifact_bytes: int,
    contract_path: Path,
    project: Path,
    created_at: str,
    reason_code: str,
    reason_detail: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Honest evaluation fail-closed. Never a scholarly CLEAN."""
    finding = {
        "code": reason_code,
        "severity": "MAJOR",
        "evidence_identity": reason_detail,
        "fingerprint": finding_fingerprint(
            obligation_id,
            reason_code,
            "MAJOR",
            reason_detail,
            artifact_sha,
        ),
        "disposition": "open",
    }
    result = {
        "schema_version": "1.0.0",
        "obligation_id": obligation_id,
        "adapter_version": adapter["adapter_version"],
        "artifact": {
            "path": artifact_rel,
            "sha256": artifact_sha,
            "byte_length": artifact_bytes,
        },
        "policy": {
            "path": contract_path.relative_to(project).as_posix(),
            "sha256": _sha(contract_path),
            "byte_length": contract_path.stat().st_size,
        },
        "activation": adapter["activation"],
        "execution_status": "failed",
        "outcome": "error",
        "findings": [finding],
        "diagnostic_only": adapter["diagnostic_only"],
        "created_at": created_at,
        "adjudications": [],
    }
    report = {
        "schema_version": "1.0.0",
        "report_type": "obligation_adapter_report",
        "adapter_id": adapter["adapter_id"],
        "adapter_version": adapter["adapter_version"],
        "obligation_id": obligation_id,
        "artifact": result["artifact"],
        "policy": result["policy"],
        "activation": result["activation"],
        "execution_status": "failed",
        "outcome": "error",
        "findings": [finding],
        "diagnostic_only": result["diagnostic_only"],
        "created_at": created_at,
    }
    return result, report


def _build_audit_typed_result(
    *,
    artifact_path: Path,
    contract_path: Path,
    project: Path,
    artifact_rel: str,
    artifact_sha: str,
    created_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run dest-safe deterministic-audit. Diagnostic-only; never scholarly CLEAN."""
    audit_path = Path(__file__).resolve().parent / "audit" / "run_all.py"
    spec = importlib.util.spec_from_file_location("draft_gov_run_all", audit_path)
    if spec is None or spec.loader is None:
        raise ContractError(
            "DRAFT-POLICY-OBLIGATION-SCHEMA",
            "deterministic-audit instrument is missing",
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    instrument = module.audit_target(artifact_path)
    findings: list[dict[str, Any]] = []
    for row in instrument.findings:
        severity = "MAJOR" if getattr(row, "severity", "") == "inviolable" else "MINOR"
        code = _sanitize_finding_code(f"AUDIT-{getattr(row, 'check_id', 'finding')}")
        evidence_identity = f"{getattr(row, 'locator', '')}|{getattr(row, 'evidence', '')}"
        findings.append(
            {
                "code": code,
                "severity": severity,
                "evidence_identity": evidence_identity,
                "fingerprint": finding_fingerprint(
                    "deterministic-audit",
                    code,
                    severity,
                    evidence_identity,
                    artifact_sha,
                ),
                "disposition": "open",
            }
        )
    if not findings:
        evidence_identity = "deterministic-audit ran dest-safe; no scholarly CLEAN"
        findings.append(
            {
                "code": "DETERMINISTIC-AUDIT-COMPLETED",
                "severity": "ADVISORY",
                "evidence_identity": evidence_identity,
                "fingerprint": finding_fingerprint(
                    "deterministic-audit",
                    "DETERMINISTIC-AUDIT-COMPLETED",
                    "ADVISORY",
                    evidence_identity,
                    artifact_sha,
                ),
                "disposition": "open",
            }
        )
    result = {
        "schema_version": "1.0.0",
        "obligation_id": "deterministic-audit",
        "adapter_version": "1.0.0",
        "artifact": {
            "path": artifact_rel,
            "sha256": artifact_sha,
            "byte_length": artifact_path.stat().st_size,
        },
        "policy": {
            "path": contract_path.relative_to(project).as_posix()
            if contract_path.is_relative_to(project)
            else str(contract_path),
            "sha256": _sha(contract_path),
            "byte_length": contract_path.stat().st_size,
        },
        "activation": "always",
        "execution_status": "completed",
        "outcome": "findings",
        "findings": findings,
        "diagnostic_only": True,
        "created_at": created_at,
        "adjudications": [],
    }
    report = {
        "schema_version": "1.0.0",
        "report_type": "obligation_adapter_report",
        "adapter_id": "deterministic-audit-result",
        "adapter_version": "1.0.0",
        "obligation_id": "deterministic-audit",
        "artifact": result["artifact"],
        "policy": result["policy"],
        "activation": result["activation"],
        "execution_status": result["execution_status"],
        "outcome": result["outcome"],
        "findings": result["findings"],
        "diagnostic_only": True,
        "created_at": created_at,
    }
    return result, report


def scaffold_receipt(args: argparse.Namespace) -> dict[str, Any]:
    """Emit dest-safe typed-result shells. Does not invent scholarly CLEAN."""
    if PHASE_ROLE.get(args.phase) != args.role:
        raise ContractError("DRAFT-POLICY-ROLE", "role does not satisfy the phase")
    contract_path = Path(args.contract).resolve(strict=True)
    artifact_path = Path(args.artifact).resolve(strict=True)
    contract = _load(contract_path, "DRAFT-POLICY-CONTRACT")
    project = Path(str(contract.get("project_root", ""))).resolve(strict=True)
    out_dir = _scaffold_out_dir(args, project)
    try:
        out_dir.relative_to(project)
    except ValueError as exc:
        raise ContractError(
            "DRAFT-POLICY-OBLIGATION-STALE",
            "scaffold out-dir must stay under the bound project so verify can bind it; "
            "use --shipment-id for the dest-allowed reviews/.harness/shipments/<id>/ lane",
        ) from exc
    current_policy = _load(POLICY_PATH, "DRAFT-POLICY-CONTRACT")
    _, adapters = _resolved_obligation_registry(current_policy)
    if contract.get("status") != "binding_resolved" or contract.get("phase") != args.phase:
        raise ContractError("DRAFT-POLICY-CONTRACT", "contract phase or status is invalid")
    if contract.get("required_role") != args.role:
        raise ContractError("DRAFT-POLICY-ROLE", "role does not satisfy the contract")
    artifact_rel = artifact_path.relative_to(project).as_posix()
    artifact_sha = _sha(artifact_path)
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    required = [
        row
        for row in contract.get("obligations", [])
        if isinstance(row, dict) and args.phase in row.get("phases", [])
    ]
    results_dir = out_dir / "obligation-results" / args.phase
    reports_dir = out_dir / "obligation-reports" / args.phase
    rows: list[dict[str, Any]] = []
    deferred: list[str] = []
    mechanical: list[str] = []
    fail_closed: list[str] = []
    fail_closed_reasons: dict[str, str] = {}
    centroid = contract.get("centroid") if isinstance(contract.get("centroid"), dict) else {}
    artifact_bytes = artifact_path.stat().st_size
    for row in required:
        obligation_id = row["id"]
        adapter = adapters[obligation_id]
        if adapter.get("report_schema", {}).get("path") == DSTYLE_REPORT_SCHEMA_REL:
            result, report = _build_dstyle_typed_result(
                project=project,
                artifact_path=artifact_path,
                contract_path=contract_path,
                artifact_rel=artifact_rel,
                artifact_sha=artifact_sha,
                created_at=created_at,
            )
            mechanical.append(obligation_id)
        elif args.phase == "evaluation" and obligation_id == "deterministic-audit":
            try:
                result, report = _build_audit_typed_result(
                    artifact_path=artifact_path,
                    contract_path=contract_path,
                    project=project,
                    artifact_rel=artifact_rel,
                    artifact_sha=artifact_sha,
                    created_at=created_at,
                )
                mechanical.append(obligation_id)
            except Exception as exc:
                result, report = _fail_closed_pair(
                    obligation_id=obligation_id,
                    adapter=adapter,
                    artifact_rel=artifact_rel,
                    artifact_sha=artifact_sha,
                    artifact_bytes=artifact_bytes,
                    contract_path=contract_path,
                    project=project,
                    created_at=created_at,
                    reason_code="DETERMINISTIC-AUDIT-INSTRUMENT-FAILED",
                    reason_detail=f"dest-safe deterministic-audit failed closed: {exc}",
                )
                fail_closed.append(obligation_id)
                fail_closed_reasons[obligation_id] = "DETERMINISTIC-AUDIT-INSTRUMENT-FAILED"
        elif args.phase == "evaluation":
            if obligation_id.startswith("centroid-") and (
                centroid.get("semantic_usage") == "not_invoked"
                or centroid.get("required") is not True
            ):
                reason_code = str(
                    centroid.get("unavailable_code") or REASON_GRAPH_UNAVAILABLE
                )
                reason_detail = (
                    "package semantic_usage=not_invoked; "
                    "graph/centroid cannot run dest-safe"
                )
            elif obligation_id.startswith("centroid-"):
                reason_code = REASON_CENTROID_RECEIPT_ABSENT
                reason_detail = (
                    "centroid semantic receipt is not dest-safe to invent; "
                    "fail-closed rather than a silent not_run shell"
                )
            else:
                reason_code = REASON_PROMPT_MEDIATED
                reason_detail = (
                    "prompt-mediated scholarly obligation cannot run dest-safe; "
                    "Reviewer/Joseph attach assignment_dispatch via attach-verifier-receipt"
                )
            result, report = _fail_closed_pair(
                obligation_id=obligation_id,
                adapter=adapter,
                artifact_rel=artifact_rel,
                artifact_sha=artifact_sha,
                artifact_bytes=artifact_bytes,
                contract_path=contract_path,
                project=project,
                created_at=created_at,
                reason_code=reason_code,
                reason_detail=reason_detail,
            )
            fail_closed.append(obligation_id)
            fail_closed_reasons[obligation_id] = reason_code
        else:
            result = {
                "schema_version": "1.0.0",
                "obligation_id": obligation_id,
                "adapter_version": adapter["adapter_version"],
                "artifact": {
                    "path": artifact_rel,
                    "sha256": artifact_sha,
                    "byte_length": artifact_bytes,
                },
                "policy": {
                    "path": contract_path.relative_to(project).as_posix(),
                    "sha256": _sha(contract_path),
                    "byte_length": contract_path.stat().st_size,
                },
                "activation": adapter["activation"],
                "execution_status": "not_run",
                "outcome": "error",
                "findings": [],
                "diagnostic_only": adapter["diagnostic_only"],
                "created_at": created_at,
                "adjudications": [],
            }
            report = {
                "schema_version": "1.0.0",
                "report_type": "obligation_adapter_report",
                "adapter_id": adapter["adapter_id"],
                "adapter_version": adapter["adapter_version"],
                "obligation_id": obligation_id,
                "artifact": result["artifact"],
                "policy": result["policy"],
                "activation": result["activation"],
                "execution_status": "not_run",
                "outcome": "error",
                "findings": [],
                "diagnostic_only": result["diagnostic_only"],
                "created_at": created_at,
            }
            deferred.append(obligation_id)
        report_path = reports_dir / f"{obligation_id}.json"
        result_path = results_dir / f"{obligation_id}.json"
        result["report"] = None  # filled after report bytes land
        _write_json(report_path, report)
        result["report"] = _exact_binding(report_path, project)
        _write_json(result_path, result)
        rows.append({"id": obligation_id, "result": _exact_binding(result_path, project)})
    receipt = {
        "schema_version": "1.0.0",
        "phase": args.phase,
        "role": args.role,
        "contract_sha256": _sha(contract_path),
        "artifact": {"path": str(artifact_path), "sha256": artifact_sha},
        "obligations": rows,
    }
    receipt_path = out_dir / f"draft_governance_receipt_{args.role}.json"
    _write_json(receipt_path, receipt)
    evaluated = args.phase == "evaluation" and bool(mechanical or fail_closed)
    note = {
        "schema_version": "1.0.0",
        "status": "evaluated" if evaluated else "scaffolded",
        "phase": args.phase,
        "role": args.role,
        "out_dir": str(out_dir),
        "receipt_path": str(receipt_path),
        "mechanical_obligation_ids": mechanical,
        "ran_obligation_ids": mechanical,
        "fail_closed_obligation_ids": fail_closed,
        "fail_closed_reasons": fail_closed_reasons,
        "deferred_obligation_ids": deferred,
        "dest_protected_stays": True,
        "who_writes": {
            "harness": "reviews/.harness/shipments/<id>/ only",
            "writer": "may copy into the package; must not invent scholarly CLEAN",
            "joseph": "D-STYLE profile in research_notes/directives.md or MAJOR adjudications; evaluation-phase scholarly verifier_receipts as research-governance",
        },
        "next_verify": [
            "python scripts/draft_governance.py",
            "verify",
            "--contract",
            str(contract_path),
            "--receipt",
            str(receipt_path),
            "--artifact",
            str(artifact_path),
            "--phase",
            args.phase,
            "--role",
            args.role,
        ],
        "still_requires_joseph": [
            "d-style-profile MAJOR while the profile is undeclared: Joseph or Writer declare the profile in directives.md (harness will not write it), then re-run scaffold-receipt; or Joseph/Evaluator adjudicate the open MAJOR findings",
            "evaluation-phase generic scholarly obligations still need independent-evaluator or research-governance verifier_receipts; generation not_run is an honest deferral, not a CLEAN",
        ],
    }
    _write_json(out_dir / "SCAFFOLD-NOTE.json", note)
    return note



def attach_verifier_receipt(args: argparse.Namespace) -> dict[str, Any]:
    """Bind a Reviewer/Joseph envelope onto a dest-safe typed result.

    Does not change outcome to CLEAN. fixture_hmac is refused in production.
    """
    project = _safe_root(args.project_root)
    result_path = Path(args.result).resolve(strict=True)
    envelope_path = Path(args.envelope).resolve(strict=True)
    try:
        result_path.relative_to(project)
        envelope_path.relative_to(project)
    except ValueError as exc:
        raise ContractError(
            "DRAFT-POLICY-OBLIGATION-STALE",
            "result and envelope must stay under the bound project",
        ) from exc
    assert_writable(result_path, purpose="draft-governance attach-verifier-receipt")
    result = _load(result_path, "DRAFT-POLICY-OBLIGATION-SCHEMA")
    envelope = _load(envelope_path, "DRAFT-POLICY-OBLIGATION-SCHEMA")
    if envelope.get("authority_mode") == "fixture_hmac":
        raise ContractError(
            "DRAFT-POLICY-OBLIGATION-SCHEMA",
            "fixture_hmac is test-only; Reviewer/Joseph must use assignment_dispatch",
        )
    if envelope.get("authority_mode") != "assignment_dispatch":
        raise ContractError(
            "DRAFT-POLICY-OBLIGATION-SCHEMA",
            "verifier_receipt must be assignment_dispatch from independent-evaluator or research-governance",
        )
    authority = envelope.get("authority")
    if authority not in {"independent-evaluator", "research-governance"}:
        raise ContractError(
            "DRAFT-POLICY-ROLE",
            f"envelope authority {authority!r} is not allowed to bind a scholarly receipt",
        )
    if result.get("outcome") == "clean":
        raise ContractError(
            "DRAFT-POLICY-OBLIGATION-SCHEMA",
            "Harness will not bind a CLEAN outcome; Reviewer/Joseph fill the report first",
        )
    result["verifier_receipt"] = _exact_binding(envelope_path, project)
    binding = _write_json(result_path, result)
    return {
        "schema_version": "1.0.0",
        "status": "bound",
        "obligation_id": result.get("obligation_id"),
        "result": _exact_binding(result_path, project),
        "authority": authority,
        "outcome": result.get("outcome"),
        "note": "envelope bound; outcome unchanged; evaluate verify still fail-closes without scholarly judgment",
    }


def evaluation_lane(args: argparse.Namespace) -> dict[str, Any]:
    """Prepare + dest-safe evaluation run. Not a verified CLEAN path."""
    prepare_args = argparse.Namespace(
        project_root=args.project_root,
        artifact=args.artifact,
        target=args.target,
        phase="evaluation",
        role="evaluator",
    )
    contract = prepare(prepare_args)
    project = Path(contract["project_root"]).resolve(strict=True)
    dest = (
        project / "reviews" / ".harness" / "shipments" / args.shipment_id
    ).resolve()
    assert_writable(dest, purpose="draft-governance evaluation-lane")
    dest.mkdir(parents=True, exist_ok=True)
    contract_path = dest / "draft_governance_prepare_evaluator.json"
    _write_json(contract_path, contract)
    artifact = Path(args.artifact or str(project / TARGET_PATHS[args.target])).resolve(strict=True)
    scaffold_args = argparse.Namespace(
        contract=str(contract_path),
        artifact=str(artifact),
        phase="evaluation",
        role="evaluator",
        out_dir=None,
        shipment_id=args.shipment_id,
    )
    note = scaffold_receipt(scaffold_args)
    note["lane"] = "evaluation"
    note["contract_path"] = str(contract_path)
    note["status"] = "evaluated"
    note.pop("verify_is_not_complete", None)
    note["verify_still_requires_reviewer_bind"] = (
        "Runnable dest-safe obligations ran. Scholarly obligations fail-closed "
        "with an explicit reason_code. attach-verifier-receipt is the only way a "
        "Reviewer binds a receipt; the harness still refuses CLEAN bind."
    )
    note["dest_protected_stays"] = True
    centroid = contract.get("centroid") if isinstance(contract.get("centroid"), dict) else {}
    if centroid.get("semantic_usage") == "not_invoked" or centroid.get("required") is not True:
        note["centroid_graph"] = {
            "status": "fail_closed",
            "reason_code": centroid.get("unavailable_code") or REASON_GRAPH_UNAVAILABLE,
            "semantic_usage": centroid.get("semantic_usage", "not_invoked"),
            "required": centroid.get("required"),
            "omitted_from_contract": True,
        }
    _write_json(dest / "EVALUATION-LANE.json", note)
    return note


def main(
    argv: list[str] | None = None,
    *,
    _test_authority_adapter: Any | None = None,
) -> int:
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
    verify_parser.add_argument("--wiki-root")
    verify_parser.add_argument("--verifier-out-dir")
    verify_parser.add_argument(
        "--semantics-manifest",
        default=str(ROOT / "references" / "semantics_manifest.v1.json"),
    )
    verify_parser.add_argument(
        "--requested-independence-level",
        choices=("none", "dispatch_separation", "host_attested_independence"),
        default="none",
    )
    scaffold_parser = sub.add_parser("scaffold-receipt")
    scaffold_parser.add_argument("--contract", required=True)
    scaffold_parser.add_argument("--artifact", required=True)
    scaffold_parser.add_argument("--phase", choices=sorted(PHASE_ROLE), required=True)
    scaffold_parser.add_argument(
        "--role", choices=sorted(set(PHASE_ROLE.values())), required=True
    )
    scaffold_parser.add_argument("--out-dir")
    scaffold_parser.add_argument("--shipment-id")
    eval_parser = sub.add_parser("evaluation-lane")
    eval_parser.add_argument("--project-root", required=True)
    eval_parser.add_argument("--artifact")
    eval_parser.add_argument("--target", choices=sorted(TARGETS), required=True)
    eval_parser.add_argument("--shipment-id", required=True)
    attach_parser = sub.add_parser("attach-verifier-receipt")
    attach_parser.add_argument("--project-root", required=True)
    attach_parser.add_argument("--result", required=True)
    attach_parser.add_argument("--envelope", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(args)
        elif args.command == "scaffold-receipt":
            result = scaffold_receipt(args)
        elif args.command == "evaluation-lane":
            result = evaluation_lane(args)
        elif args.command == "attach-verifier-receipt":
            result = attach_verifier_receipt(args)
        else:
            result = verify(args, _test_authority_adapter=_test_authority_adapter)
    except DestinationRefused as exc:
        print(json.dumps({"status": "blocked", "reason_code": exc.code, "detail": str(exc)}, ensure_ascii=False))
        return 4
    except (ContractError, OSError) as exc:
        code = exc.code if isinstance(exc, ContractError) else "DRAFT-POLICY-IO"
        detail = exc.detail if isinstance(exc, ContractError) else str(exc)
        print(json.dumps({"status": "blocked", "reason_code": code, "detail": detail}, ensure_ascii=False))
        return 4
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
