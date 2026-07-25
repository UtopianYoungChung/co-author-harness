#!/usr/bin/env python3
"""Shared product recomputation boundary for draft evidence.

C3 transaction publication is layered on this kernel. This module never
accepts a role-supplied product report as an input or as proof of its result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft202012Validator

from c2_evidence_validation import (
    EvidenceValidationError,
    canonical_bytes,
    load_canonical_document,
)
from destination_capability import DestinationRefused, assert_writable
from evidence_publication import (
    EvidencePublicationError,
    publish_committed,
    recover_committed,
    validate_committed,
)
from product_assurance import (
    AssuranceError,
    DETECTOR_NAME,
    DETECTOR_VERSION,
    build as build_product_assurance,
)


ROOT = Path(__file__).resolve().parent.parent
REQUIRED_SEMANTICS_MEMBERS = (
    "references/policies/draft_governance.v1.json",
    "references/schemas/assignment_dispatch_claim.schema.json",
    "references/schemas/assignment_dispatch_issuance.schema.json",
    "references/schemas/assignment_dispatch_kernel_authorization.schema.json",
    "references/schemas/assignment_dispatch_consumption.schema.json",
    "references/schemas/assignment_host_attestation.schema.json",
    "references/schemas/assignment_mutation_anchor.schema.json",
    "references/schemas/assignment_mutation_genesis.schema.json",
    "references/schemas/assignment_mutation_state.schema.json",
    "references/schemas/lifecycle_verifier_binding.schema.json",
    "references/schemas/canonical_bibliography_snapshot.schema.json",
    "references/schemas/canonical_extract_receipt.schema.json",
    "references/schemas/centroid_semantic_execution.schema.json",
    "references/schemas/centroid_semantic_execution.v3.schema.json",
    "references/schemas/evidence_publication_claim.schema.json",
    "references/schemas/evidence_publication_journal.schema.json",
    "references/schemas/product_assurance.schema.json",
    "references/schemas/product_assurance.v2.schema.json",
    "references/schemas/semantics_manifest.schema.json",
    "references/schemas/verifier_blocker.schema.json",
    "references/schemas/verifier_commit_marker.schema.json",
    "references/schemas/verifier_publication_manifest.schema.json",
    "references/schemas/verifier_transaction.schema.json",
    "scripts/assignment_dispatch_claim.py",
    "scripts/assignment_mutation_anchor.py",
    "scripts/assignment_receipt_transaction.py",
    "scripts/c2_evidence_validation.py",
    "scripts/canonical_bibliography.py",
    "scripts/destination_capability.py",
    "scripts/draft_evidence_verifier.py",
    "scripts/evidence_publication.py",
    "scripts/product_assurance.py",
    "scripts/source_extract.py",
)


class VerifierError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def recompute_product_assurance(
    *,
    artifact: Path,
    semantic_receipt: Path,
    phase: str,
    project_root: Path | None = None,
    wiki_root: Path | None = None,
) -> dict[str, Any]:
    """Recompute diagnostics in memory from exact current evidence bytes."""
    try:
        report = build_product_assurance(
            artifact,
            semantic_receipt,
            project_root=project_root,
            wiki_root=wiki_root,
        )
    except AssuranceError as exc:
        raise VerifierError(exc.code, exc.message) from exc
    allowed = {"passed", "needs_adjudication"} if phase == "generation" else {"passed"}
    if report.get("status") not in allowed:
        findings = report.get("findings")
        first = findings[0] if isinstance(findings, list) and findings else None
        if isinstance(first, dict) and isinstance(first.get("code"), str):
            raise VerifierError(
                first["code"],
                str(first.get("evidence", "product assurance did not qualify")),
            )
        raise VerifierError(
            "PRODUCT-ASSURANCE-BLOCKED",
            "recomputed product assurance did not qualify the exact evidence",
        )
    return report


def report_payload_sha256(report: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(report)).hexdigest()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _schema(name: str, *, harness_root: Path) -> Draft202012Validator:
    path = harness_root / "references" / "schemas" / name
    value = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(value)
    return Draft202012Validator(value)


def _project_root_descriptor(
    project_root: Path, declared: dict[str, Any]
) -> dict[str, Any]:
    if not isinstance(declared, dict):
        raise VerifierError("EVIDENCE-ROOT-MISMATCH", "project root descriptor is invalid")
    discovery = declared.get("discovery")
    if (
        declared.get("kind") != "project"
        or not isinstance(discovery, str)
        or not discovery.startswith("explicit:")
    ):
        raise VerifierError("EVIDENCE-ROOT-MISMATCH", "project root descriptor is invalid")
    relative = discovery.removeprefix("explicit:")
    manifest = (project_root / relative).resolve(strict=True)
    if not manifest.is_relative_to(project_root):
        raise VerifierError("EVIDENCE-ROOT-MISMATCH", "project manifest escapes root")
    value = json.loads(manifest.read_text(encoding="utf-8"))
    expected = {
        "kind": "project",
        "identity": value["identity"],
        "discovery": discovery,
        "manifest_sha256": _sha(manifest),
    }
    if declared != expected:
        raise VerifierError("EVIDENCE-ROOT-MISMATCH", "project root descriptor is stale")
    return expected


def _harness_root_descriptor(harness_root: Path) -> dict[str, Any]:
    manifest = harness_root / ".claude-plugin" / "plugin.json"
    value = json.loads(manifest.read_text(encoding="utf-8"))
    return {
        "kind": "harness",
        "identity": value["name"],
        "discovery": "explicit:.claude-plugin/plugin.json",
        "manifest_sha256": _sha(manifest),
    }


def _binding(
    path: Path,
    *,
    root: Path,
    descriptor: dict[str, Any],
    evidence_type: str,
    digest: str | None = None,
) -> dict[str, Any]:
    return {
        "root": descriptor,
        "path": path.resolve().relative_to(root.resolve()).as_posix(),
        "sha256": digest if digest is not None else _sha(path),
        "evidence_type": evidence_type,
    }


def _validate_semantics_manifest(
    *,
    harness_root: Path,
    semantics_manifest: Path,
) -> tuple[dict[str, Any], str, list[tuple[Path, str]]]:
    harness_root = harness_root.resolve(strict=True)
    semantics_manifest = semantics_manifest.resolve(strict=True)
    try:
        value, raw = load_canonical_document(
            semantics_manifest,
            schema_code="SEMANTICS-DIGEST-MISMATCH",
            canonical_code="SEMANTICS-DIGEST-MISMATCH",
        )
        _schema("semantics_manifest.schema.json", harness_root=harness_root).validate(value)
    except Exception as exc:
        raise VerifierError("SEMANTICS-DIGEST-MISMATCH", str(exc)) from exc
    members = value.get("members")
    by_path = {
        row.get("path"): row
        for row in members
        if isinstance(row, dict) and isinstance(row.get("path"), str)
    } if isinstance(members, list) else {}
    if (
        not isinstance(members, list)
        or len(members) != len(REQUIRED_SEMANTICS_MEMBERS)
        or len(by_path) != len(REQUIRED_SEMANTICS_MEMBERS)
        or set(by_path) != set(REQUIRED_SEMANTICS_MEMBERS)
    ):
        raise VerifierError(
            "SEMANTICS-DIGEST-MISMATCH",
            "semantics manifest member inventory is incomplete or expanded",
        )
    plugin_manifest = harness_root / ".claude-plugin" / "plugin.json"
    plugin = json.loads(plugin_manifest.read_text(encoding="utf-8"))
    if value.get("harness_identity") != plugin.get("name"):
        raise VerifierError("SEMANTICS-DIGEST-MISMATCH", "harness identity differs")
    preconditions: list[tuple[Path, str]] = [
        (semantics_manifest, hashlib.sha256(raw).hexdigest()),
        (plugin_manifest, _sha(plugin_manifest)),
    ]
    for relative in REQUIRED_SEMANTICS_MEMBERS:
        try:
            path = (harness_root / relative).resolve(strict=True)
            current_digest = _sha(path)
        except OSError as exc:
            raise VerifierError(
                "SEMANTICS-DIGEST-MISMATCH",
                f"semantics member is unavailable: {relative}",
            ) from exc
        if not path.is_relative_to(harness_root) or current_digest != by_path[relative]["sha256"]:
            raise VerifierError(
                "SEMANTICS-DIGEST-MISMATCH",
                f"semantics member is stale: {relative}",
            )
        preconditions.append((path, by_path[relative]["sha256"]))
    digest = hashlib.sha256(canonical_bytes({
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "members": members,
    })).hexdigest()
    return value, digest, preconditions


def _portable_input_binding(
    path: Path,
    *,
    project_root: Path,
    harness_root: Path,
    project_descriptor: dict[str, Any],
    harness_descriptor: dict[str, Any],
    evidence_type: str,
) -> dict[str, Any]:
    resolved = path.resolve(strict=True)
    if resolved.is_relative_to(project_root):
        return _binding(
            resolved, root=project_root, descriptor=project_descriptor,
            evidence_type=evidence_type,
        )
    if resolved.is_relative_to(harness_root):
        return _binding(
            resolved, root=harness_root, descriptor=harness_descriptor,
            evidence_type=evidence_type,
        )
    raise VerifierError(
        "EVIDENCE-ROOT-MISMATCH",
        f"input is outside the declared project and harness roots: {resolved}",
    )


def _load_current_semantic_receipt(
    semantic_receipt: Path,
    *,
    phase: str,
) -> dict[str, Any]:
    try:
        value, _raw = load_canonical_document(
            semantic_receipt,
            schema_code="EVIDENCE-SCHEMA-INVALID",
            canonical_code="EVIDENCE-CANONICALIZATION-INVALID",
        )
    except EvidenceValidationError as exc:
        raise VerifierError(exc.code, exc.message) from exc
    if value.get("schema_version") != "3.0.0":
        raise VerifierError(
            "EVIDENCE-VERSION-INELIGIBLE",
            "only semantic execution receipt 3.0.0 can issue a verifier transaction",
        )
    if value.get("phase") != phase:
        raise VerifierError(
            "EVIDENCE-SCHEMA-INVALID",
            "semantic execution phase does not match the verifier transaction phase",
        )
    return value


def _build_product_report(
    *,
    artifact: Path,
    semantic_receipt: Path,
    phase: str,
    project_root: Path,
    wiki_root: Path,
    project_descriptor: dict[str, Any],
    semantics_digest: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    semantic_value = _load_current_semantic_receipt(
        semantic_receipt,
        phase=phase,
    )
    kernel_report = recompute_product_assurance(
        artifact=artifact,
        semantic_receipt=semantic_receipt,
        phase=phase,
        project_root=project_root,
        wiki_root=wiki_root,
    )
    artifact_binding = _binding(
        artifact,
        root=project_root,
        descriptor=project_descriptor,
        evidence_type="governed_artifact",
    )
    semantic_binding = _binding(
        semantic_receipt,
        root=project_root,
        descriptor=project_descriptor,
        evidence_type="semantic_execution_receipt",
    )
    disposition = "evaluation_ready" if phase == "generation" else "product_qualified"
    return {
        "schema_version": "2.0.0",
        "report_type": "product_assurance",
        "status": kernel_report["status"],
        "qualification_mode": "governed_v3",
        "product_disposition": disposition,
        "artifact": artifact_binding,
        "semantic_receipt": semantic_binding,
        "corpus_binding_sha256": semantic_value["corpus_digest"],
        "semantics_digest": semantics_digest,
        "detector": {"name": DETECTOR_NAME, "version": DETECTOR_VERSION},
        "dimensions": kernel_report["dimensions"],
        "findings": kernel_report["findings"],
        "adjudications": kernel_report["adjudications"],
        "kernel_output_sha256": report_payload_sha256(kernel_report),
    }, semantic_value


def publish_verifier_transaction(
    *,
    artifact: Path,
    semantic_receipt: Path,
    phase: str,
    project_root: Path,
    wiki_root: Path,
    harness_root: Path,
    semantics_manifest: Path,
    out_dir: Path,
    requested_independence_level: str,
    _under_claim_hook: Callable[[], None] | None = None,
) -> dict[str, Any]:
    project_root = project_root.resolve(strict=True)
    harness_root = harness_root.resolve(strict=True)
    artifact = artifact.resolve(strict=True)
    semantic_receipt = semantic_receipt.resolve(strict=True)
    semantics_manifest = semantics_manifest.resolve(strict=True)
    out_dir = out_dir.resolve()
    if requested_independence_level != "none":
        raise VerifierError(
            "INDEPENDENCE_UNVERIFIED",
            "C3 has no trusted dispatch or host-attestation authority",
        )
    if not out_dir.is_relative_to(project_root):
        raise VerifierError("EVIDENCE-ROOT-MISMATCH", "verifier output escapes project root")
    outputs = {
        "product_assurance": out_dir / "product-assurance.json",
        "transaction": out_dir / "verifier-transaction.json",
        "publication_manifest": out_dir / "publication-manifest.json",
        "commit_marker": out_dir / "commit-marker.json",
    }
    try:
        for path in outputs.values():
            assert_writable(path, purpose="shared verifier transaction publication")
    except DestinationRefused as exc:
        raise VerifierError(exc.code, str(exc)) from exc
    _manifest, semantics_digest, semantics_preconditions = _validate_semantics_manifest(
        harness_root=harness_root,
        semantics_manifest=semantics_manifest,
    )
    semantic_value = _load_current_semantic_receipt(
        semantic_receipt,
        phase=phase,
    )
    project_descriptor = _project_root_descriptor(
        project_root, semantic_value["artifact"]["root"]
    )
    harness_descriptor = _harness_root_descriptor(harness_root)
    product_report, semantic_value = _build_product_report(
        artifact=artifact,
        semantic_receipt=semantic_receipt,
        phase=phase,
        project_root=project_root,
        wiki_root=wiki_root,
        project_descriptor=project_descriptor,
        semantics_digest=semantics_digest,
    )
    artifact_binding = product_report["artifact"]
    semantic_binding = product_report["semantic_receipt"]
    artifact_digest = artifact_binding["sha256"]
    semantic_digest = semantic_binding["sha256"]
    qualification_mode = product_report["qualification_mode"]
    disposition = product_report["product_disposition"]
    manifest_binding = _portable_input_binding(
        semantics_manifest,
        project_root=project_root,
        harness_root=harness_root,
        project_descriptor=project_descriptor,
        harness_descriptor=harness_descriptor,
        evidence_type="semantics_manifest",
    )
    _schema("product_assurance.v2.schema.json", harness_root=harness_root).validate(product_report)
    product_bytes = canonical_bytes(product_report)
    product_binding = _binding(
        outputs["product_assurance"], root=project_root,
        descriptor=project_descriptor, evidence_type="product_assurance_v2",
        digest=hashlib.sha256(product_bytes).hexdigest(),
    )
    dependency_hashes = [
        {"path": path.resolve().relative_to(harness_root).as_posix(), "sha256": digest}
        for path, digest in semantics_preconditions[2:]
    ]
    transaction_seed = {
        "artifact": artifact_digest,
        "semantic_receipt": semantic_digest,
        "semantics_digest": semantics_digest,
        "phase": phase,
        "requested_independence_level": requested_independence_level,
        "out_dir": out_dir.relative_to(project_root).as_posix(),
    }
    transaction_id = "verifier-" + hashlib.sha256(
        canonical_bytes(transaction_seed)
    ).hexdigest()[:16]
    transaction = {
        "schema_version": "1.0.0",
        "transaction_type": "draft_evidence_verifier",
        "transaction_id": transaction_id,
        "state": "prepared",
        "phase": phase,
        "qualification_mode": qualification_mode,
        "product_disposition": disposition,
        "requested_independence_level": requested_independence_level,
        "achieved_independence_level": "none",
        "artifact": artifact_binding,
        "semantic_receipt": semantic_binding,
        "product_assurance": product_binding,
        "semantics_manifest": manifest_binding,
        "semantics_digest": semantics_digest,
        "dependency_hashes": dependency_hashes,
    }
    _schema("verifier_transaction.schema.json", harness_root=harness_root).validate(transaction)
    transaction_bytes = canonical_bytes(transaction)
    transaction_binding = _binding(
        outputs["transaction"], root=project_root,
        descriptor=project_descriptor, evidence_type="verifier_transaction",
        digest=hashlib.sha256(transaction_bytes).hexdigest(),
    )
    publication = {
        "schema_version": "1.0.0",
        "transaction_id": transaction_id,
        "mode": "committed",
        "state": "prepared",
        "inputs": [artifact_binding, semantic_binding, manifest_binding],
        "semantics_digest": semantics_digest,
        "intended_outputs": [product_binding, transaction_binding],
    }
    publication_bytes = canonical_bytes(publication)
    _schema(
        "verifier_publication_manifest.schema.json", harness_root=harness_root
    ).validate(publication)
    publication_binding = _binding(
        outputs["publication_manifest"], root=project_root,
        descriptor=project_descriptor, evidence_type="verifier_publication_manifest",
        digest=hashlib.sha256(publication_bytes).hexdigest(),
    )
    marker = {
        "schema_version": "1.0.0",
        "transaction_id": transaction_id,
        "mode": "committed",
        "state": "committed",
        "manifest": publication_binding,
        "final_output_hashes": [product_binding, transaction_binding, publication_binding],
    }
    marker_bytes = canonical_bytes(marker)
    _schema("verifier_commit_marker.schema.json", harness_root=harness_root).validate(
        marker
    )
    captured = [
        (artifact, artifact_digest),
        (semantic_receipt, semantic_digest),
        *semantics_preconditions,
    ]

    def validate_under_claim() -> None:
        if _under_claim_hook is not None:
            _under_claim_hook()
        for path, expected in captured:
            if not path.is_file() or _sha(path) != expected:
                raise EvidencePublicationError("verifier input changed under claim")

    try:
        publish_committed(
            project_root=project_root,
            transaction_id=transaction_id,
            preconditions=captured,
            inventory_preconditions=[],
            outputs=[
                (outputs["product_assurance"], product_bytes),
                (outputs["transaction"], transaction_bytes),
                (outputs["publication_manifest"], publication_bytes),
            ],
            marker=(outputs["commit_marker"], marker_bytes),
            under_claim_validator=validate_under_claim,
        )
    except EvidencePublicationError as exc:
        code = (
            "EVIDENCE-TOCTOU"
            if "changed under claim" in str(exc)
            else "VERIFIER-TRANSACTION-INCOMPLETE"
        )
        raise VerifierError(code, str(exc)) from exc
    return {"transaction_id": transaction_id, **outputs}


def _resolve_project_binding(
    value: dict[str, Any],
    *,
    project_root: Path,
    expected_path: Path,
    code: str,
) -> None:
    if not isinstance(value, dict):
        raise VerifierError(code, f"binding is invalid: {expected_path}")
    descriptor = _project_root_descriptor(project_root, value.get("root", {}))
    if (
        value.get("root") != descriptor
        or value.get("path") != expected_path.resolve().relative_to(project_root).as_posix()
        or value.get("sha256") != _sha(expected_path)
    ):
        raise VerifierError(code, f"binding is not exact: {expected_path}")


def _validate_publication_state_schemas(
    *,
    project_root: Path,
    transaction_id: str,
    harness_root: Path,
) -> None:
    lane = project_root / ".harness-evidence-transactions" / transaction_id
    try:
        claim, _claim_raw = load_canonical_document(
            lane / "claim.json",
            schema_code="VERIFIER-TRANSACTION-INCOMPLETE",
            canonical_code="VERIFIER-TRANSACTION-INCOMPLETE",
        )
        journal, _journal_raw = load_canonical_document(
            lane / "journal.json",
            schema_code="VERIFIER-TRANSACTION-INCOMPLETE",
            canonical_code="VERIFIER-TRANSACTION-INCOMPLETE",
        )
        _schema(
            "evidence_publication_claim.schema.json", harness_root=harness_root
        ).validate(claim)
        _schema(
            "evidence_publication_journal.schema.json", harness_root=harness_root
        ).validate(journal)
    except Exception as exc:
        raise VerifierError("VERIFIER-TRANSACTION-INCOMPLETE", str(exc)) from exc


def _derive_verifier_intent(
    *,
    transaction: Path,
    publication_manifest: Path,
    commit_marker: Path,
    artifact: Path,
    semantic_receipt: Path,
    project_root: Path,
    wiki_root: Path,
    harness_root: Path,
    semantics_manifest: Path,
    require_marker: bool,
) -> dict[str, Any]:
    project_root = project_root.resolve(strict=True)
    harness_root = harness_root.resolve(strict=True)
    transaction = transaction.resolve(strict=True)
    publication_manifest = publication_manifest.resolve(strict=True)
    artifact = artifact.resolve(strict=True)
    semantic_receipt = semantic_receipt.resolve(strict=True)
    semantics_manifest = semantics_manifest.resolve(strict=True)
    commit_marker = commit_marker.resolve()
    if require_marker and not commit_marker.is_file():
        raise VerifierError(
            "VERIFIER-TRANSACTION-INCOMPLETE", "verifier commit marker is absent"
        )
    try:
        transaction_value, transaction_raw = load_canonical_document(
            transaction, schema_code="ASSURANCE-FORGED",
            canonical_code="ASSURANCE-FORGED",
        )
        publication_value, publication_raw = load_canonical_document(
            publication_manifest,
            schema_code="VERIFIER-TRANSACTION-INCOMPLETE",
            canonical_code="VERIFIER-TRANSACTION-INCOMPLETE",
        )
        marker_value = marker_raw = None
        if require_marker:
            marker_value, marker_raw = load_canonical_document(
                commit_marker,
                schema_code="VERIFIER-TRANSACTION-INCOMPLETE",
                canonical_code="VERIFIER-TRANSACTION-INCOMPLETE",
            )
        _schema("verifier_transaction.schema.json", harness_root=harness_root).validate(
            transaction_value
        )
        _schema(
            "verifier_publication_manifest.schema.json", harness_root=harness_root
        ).validate(publication_value)
        if require_marker:
            _schema(
                "verifier_commit_marker.schema.json", harness_root=harness_root
            ).validate(marker_value)
    except VerifierError:
        raise
    except Exception as exc:
        raise VerifierError("VERIFIER-TRANSACTION-INCOMPLETE", str(exc)) from exc
    transaction_id = transaction_value["transaction_id"]
    expected_dir = transaction.parent
    expected_paths = {
        "product": expected_dir / "product-assurance.json",
        "transaction": expected_dir / "verifier-transaction.json",
        "publication": expected_dir / "publication-manifest.json",
        "marker": expected_dir / "commit-marker.json",
    }
    if transaction != expected_paths["transaction"]:
        raise VerifierError("ASSURANCE-FORGED", "verifier envelope occupies a lookalike path")
    if publication_manifest != expected_paths["publication"] or commit_marker != expected_paths["marker"]:
        raise VerifierError(
            "VERIFIER-TRANSACTION-INCOMPLETE", "publication files occupy unexpected paths"
        )
    _semantics_value, semantics_digest, semantics_preconditions = _validate_semantics_manifest(
        harness_root=harness_root,
        semantics_manifest=semantics_manifest,
    )
    if transaction_value.get("semantics_digest") != semantics_digest:
        raise VerifierError("SEMANTICS-DIGEST-MISMATCH", "transaction semantics are stale")
    _resolve_project_binding(
        transaction_value["artifact"], project_root=project_root,
        expected_path=artifact, code="EVIDENCE-TOCTOU",
    )
    _resolve_project_binding(
        transaction_value["semantic_receipt"], project_root=project_root,
        expected_path=semantic_receipt, code="EVIDENCE-TOCTOU",
    )
    product = expected_paths["product"].resolve(strict=True)
    _resolve_project_binding(
        transaction_value["product_assurance"], project_root=project_root,
        expected_path=product, code="ASSURANCE-FORGED",
    )
    product_value, product_raw = load_canonical_document(
        product, schema_code="ASSURANCE-FORGED", canonical_code="ASSURANCE-FORGED"
    )
    project_descriptor = _project_root_descriptor(
        project_root, transaction_value["artifact"]["root"]
    )
    harness_descriptor = _harness_root_descriptor(harness_root)
    expected_manifest_binding = _portable_input_binding(
        semantics_manifest,
        project_root=project_root,
        harness_root=harness_root,
        project_descriptor=project_descriptor,
        harness_descriptor=harness_descriptor,
        evidence_type="semantics_manifest",
    )
    expected_product, semantic_value = _build_product_report(
        artifact=artifact,
        semantic_receipt=semantic_receipt,
        phase=transaction_value["phase"],
        project_root=project_root,
        wiki_root=wiki_root,
        project_descriptor=project_descriptor,
        semantics_digest=semantics_digest,
    )
    try:
        _schema("product_assurance.v2.schema.json", harness_root=harness_root).validate(
            product_value
        )
    except Exception as exc:
        raise VerifierError("ASSURANCE-FORGED", str(exc)) from exc
    if product_value != expected_product or product_raw != canonical_bytes(expected_product):
        raise VerifierError(
            "ASSURANCE-FORGED",
            "published product assurance differs from live verifier recomputation",
        )
    product_binding = _binding(
        product, root=project_root, descriptor=project_descriptor,
        evidence_type="product_assurance_v2",
    )
    transaction_binding = _binding(
        transaction, root=project_root, descriptor=project_descriptor,
        evidence_type="verifier_transaction",
    )
    publication_binding = _binding(
        publication_manifest, root=project_root, descriptor=project_descriptor,
        evidence_type="verifier_publication_manifest",
    )
    dependency_hashes = [
        {"path": path.resolve().relative_to(harness_root).as_posix(), "sha256": digest}
        for path, digest in semantics_preconditions[2:]
    ]
    transaction_seed = {
        "artifact": _sha(artifact),
        "semantic_receipt": _sha(semantic_receipt),
        "semantics_digest": semantics_digest,
        "phase": transaction_value["phase"],
        "requested_independence_level": transaction_value["requested_independence_level"],
        "out_dir": expected_dir.relative_to(project_root).as_posix(),
    }
    expected_transaction_id = "verifier-" + hashlib.sha256(
        canonical_bytes(transaction_seed)
    ).hexdigest()[:16]
    expected_transaction = {
        "schema_version": "1.0.0",
        "transaction_type": "draft_evidence_verifier",
        "transaction_id": expected_transaction_id,
        "state": "prepared",
        "phase": transaction_value["phase"],
        "qualification_mode": "governed_v3",
        "product_disposition": expected_product["product_disposition"],
        "requested_independence_level": transaction_value["requested_independence_level"],
        "achieved_independence_level": "none",
        "artifact": expected_product["artifact"],
        "semantic_receipt": expected_product["semantic_receipt"],
        "product_assurance": product_binding,
        "semantics_manifest": expected_manifest_binding,
        "semantics_digest": semantics_digest,
        "dependency_hashes": dependency_hashes,
    }
    if (
        transaction_value != expected_transaction
        or transaction_raw != canonical_bytes(expected_transaction)
    ):
        raise VerifierError(
            "ASSURANCE-FORGED",
            "verifier transaction differs from the live authoritative result",
        )
    expected_publication = {
        "schema_version": "1.0.0",
        "transaction_id": expected_transaction_id,
        "mode": "committed",
        "state": "prepared",
        "inputs": [
            expected_product["artifact"],
            expected_product["semantic_receipt"],
            expected_manifest_binding,
        ],
        "semantics_digest": semantics_digest,
        "intended_outputs": [product_binding, transaction_binding],
    }
    if (
        publication_value != expected_publication
        or publication_raw != canonical_bytes(expected_publication)
    ):
        raise VerifierError(
            "VERIFIER-TRANSACTION-INCOMPLETE",
            "publication manifest is inconsistent",
        )
    expected_marker = {
        "schema_version": "1.0.0",
        "transaction_id": expected_transaction_id,
        "mode": "committed",
        "state": "committed",
        "manifest": publication_binding,
        "final_output_hashes": [product_binding, transaction_binding, publication_binding],
    }
    if marker_raw != canonical_bytes(expected_marker) or marker_value != expected_marker:
        if require_marker:
            raise VerifierError(
                "VERIFIER-TRANSACTION-INCOMPLETE", "commit marker does not bind exact outputs"
            )
    captured = [
        (artifact, _sha(artifact)),
        (semantic_receipt, _sha(semantic_receipt)),
        *semantics_preconditions,
    ]
    return {
        "project_root": project_root,
        "transaction_id": expected_transaction_id,
        "transaction_value": transaction_value,
        "preconditions": captured,
        "outputs": [
            (product, canonical_bytes(expected_product)),
            (transaction, canonical_bytes(expected_transaction)),
            (publication_manifest, canonical_bytes(expected_publication)),
        ],
        "marker": (commit_marker, canonical_bytes(expected_marker)),
    }


def validate_verifier_transaction(
    *,
    transaction: Path,
    publication_manifest: Path,
    commit_marker: Path,
    artifact: Path,
    semantic_receipt: Path,
    project_root: Path,
    wiki_root: Path,
    harness_root: Path,
    semantics_manifest: Path,
) -> dict[str, Any]:
    intent = _derive_verifier_intent(
        transaction=transaction,
        publication_manifest=publication_manifest,
        commit_marker=commit_marker,
        artifact=artifact,
        semantic_receipt=semantic_receipt,
        project_root=project_root,
        wiki_root=wiki_root,
        harness_root=harness_root,
        semantics_manifest=semantics_manifest,
        require_marker=True,
    )
    _validate_publication_state_schemas(
        project_root=intent["project_root"],
        transaction_id=intent["transaction_id"],
        harness_root=harness_root.resolve(strict=True),
    )
    try:
        validate_committed(
            project_root=intent["project_root"],
            transaction_id=intent["transaction_id"],
            preconditions=intent["preconditions"],
            inventory_preconditions=[],
            outputs=intent["outputs"],
            marker=intent["marker"],
        )
    except EvidencePublicationError as exc:
        raise VerifierError("VERIFIER-TRANSACTION-INCOMPLETE", str(exc)) from exc
    return intent["transaction_value"]


def validate_lifecycle_verifier_binding(
    *,
    locator: Path,
    artifact: Path,
    project_root: Path,
    harness_root: Path,
    expected_phase: str,
    expected_disposition: str,
) -> dict[str, Any]:
    """Validate the exact shared verifier transaction consumed by lifecycle gates."""
    project_root = project_root.resolve(strict=True)
    harness_root = harness_root.resolve(strict=True)
    locator = locator.resolve(strict=True)
    artifact = artifact.resolve(strict=True)
    if not locator.is_relative_to(project_root) or not artifact.is_relative_to(project_root):
        raise VerifierError("LIFECYCLE-EVIDENCE-ROOT-MISMATCH", "lifecycle evidence escapes the project root")
    try:
        value = json.loads(locator.read_text(encoding="utf-8"))
        _schema(
            "lifecycle_verifier_binding.schema.json", harness_root=harness_root
        ).validate(value)
    except Exception as exc:
        raise VerifierError("LIFECYCLE-EVIDENCE-INVALID", str(exc)) from exc
    if (
        value.get("phase") != expected_phase
        or value.get("product_disposition") != expected_disposition
    ):
        raise VerifierError(
            "LIFECYCLE-EVIDENCE-DISPOSITION",
            "lifecycle verifier phase or disposition differs from the gate",
        )

    def resolve(row: dict[str, Any], expected_root: str) -> Path:
        if row.get("root") != expected_root:
            raise VerifierError("LIFECYCLE-EVIDENCE-ROOT-MISMATCH", "binding root differs")
        base = project_root if expected_root == "project" else harness_root
        path = (base / Path(row["path"])).resolve()
        if not path.is_relative_to(base) or not path.is_file() or _sha(path) != row.get("sha256"):
            raise VerifierError("LIFECYCLE-EVIDENCE-STALE", f"binding is stale: {row.get('path')}")
        return path

    transaction = resolve(value["transaction"], "project")
    publication_manifest = resolve(value["publication_manifest"], "project")
    commit_marker = resolve(value["commit_marker"], "project")
    semantic_receipt = resolve(value["semantic_receipt"], "project")
    dispatch_claim = resolve(value["dispatch_claim"], "project")
    dispatch_consumption = resolve(value["dispatch_consumption"], "project")
    semantics_manifest = resolve(value["semantics_manifest"], "harness")
    wiki_binding = value["wiki_root"]
    wiki_base = project_root if wiki_binding["root"] == "project" else harness_root
    wiki_root = (wiki_base / Path(wiki_binding["path"])).resolve()
    wiki_manifest = wiki_root / "manifest.json"
    if (
        not wiki_root.is_relative_to(wiki_base)
        or not wiki_root.is_dir()
        or not wiki_manifest.is_file()
        or _sha(wiki_manifest) != wiki_binding["manifest_sha256"]
    ):
        raise VerifierError("LIFECYCLE-EVIDENCE-ROOT-MISMATCH", "wiki root is unavailable")
    transaction_value = validate_verifier_transaction(
        transaction=transaction,
        publication_manifest=publication_manifest,
        commit_marker=commit_marker,
        artifact=artifact,
        semantic_receipt=semantic_receipt,
        project_root=project_root,
        wiki_root=wiki_root,
        harness_root=harness_root,
        semantics_manifest=semantics_manifest,
    )
    if (
        transaction_value.get("phase") != expected_phase
        or transaction_value.get("product_disposition") != expected_disposition
    ):
        raise VerifierError(
            "LIFECYCLE-EVIDENCE-DISPOSITION",
            "committed verifier transaction does not qualify this lifecycle gate",
        )
    try:
        from assignment_dispatch_claim import validate_consumed_claim_for_context
        from assignment_receipt_transaction import ReceiptTransactionError

        claim_value = json.loads(dispatch_claim.read_text(encoding="utf-8"))
        validate_consumed_claim_for_context(
            project_root,
            dispatch_claim,
            dispatch_consumption,
            expected_role="generator" if expected_phase == "generation" else "evaluator",
            expected_target=value["target"],
            expected_receipt_id=value["receipt_id"],
            expected_artifact_sha256=_sha(artifact),
            expected_generation_transaction_id=value["generation_verifier_transaction_id"],
        )
    except ReceiptTransactionError as exc:
        raise VerifierError("LIFECYCLE-EVIDENCE-CLAIM", f"{exc.code}: {exc.message}") from exc
    if claim_value.get("claim_kind") != expected_phase:
        raise VerifierError("LIFECYCLE-EVIDENCE-CLAIM", "dispatch claim phase differs")

    dependencies: list[dict[str, str]] = []
    paths = {
        locator,
        artifact,
        transaction,
        publication_manifest,
        commit_marker,
        semantic_receipt,
        dispatch_claim,
        dispatch_consumption,
        semantics_manifest,
        dispatch_claim.parent / "publication_manifest.json",
        dispatch_claim.parent / "commit_marker.json",
        dispatch_consumption.parent / "publication_manifest.json",
        dispatch_consumption.parent / "commit_marker.json",
        project_root / "project_manifest.json",
        harness_root / ".claude-plugin" / "plugin.json",
        wiki_manifest,
    }
    for row in transaction_value.get("dependency_hashes", []):
        paths.add((harness_root / Path(row["path"])).resolve())
    product = transaction_value.get("product_assurance", {})
    if isinstance(product.get("path"), str):
        paths.add((project_root / Path(product["path"])).resolve())
    for path in sorted(paths, key=lambda item: str(item)):
        if not path.is_file():
            raise VerifierError("LIFECYCLE-EVIDENCE-STALE", f"dependency is missing: {path}")
        dependencies.append({"path": str(path.resolve()), "sha256": _sha(path)})
    return {
        "locator": value,
        "transaction": transaction_value,
        "dependencies": dependencies,
    }


def recover_verifier_transaction(
    *,
    transaction: Path,
    publication_manifest: Path,
    commit_marker: Path,
    artifact: Path,
    semantic_receipt: Path,
    project_root: Path,
    wiki_root: Path,
    harness_root: Path,
    semantics_manifest: Path,
    acknowledgement: str,
) -> str:
    intent = _derive_verifier_intent(
        transaction=transaction,
        publication_manifest=publication_manifest,
        commit_marker=commit_marker,
        artifact=artifact,
        semantic_receipt=semantic_receipt,
        project_root=project_root,
        wiki_root=wiki_root,
        harness_root=harness_root,
        semantics_manifest=semantics_manifest,
        require_marker=False,
    )
    _validate_publication_state_schemas(
        project_root=intent["project_root"],
        transaction_id=intent["transaction_id"],
        harness_root=harness_root.resolve(strict=True),
    )

    def validate_destination(path: Path) -> None:
        try:
            assert_writable(path, purpose="shared verifier inspected recovery")
        except DestinationRefused as exc:
            raise EvidencePublicationError(f"{exc.code}: {exc}") from exc

    try:
        return recover_committed(
            project_root=intent["project_root"],
            transaction_id=intent["transaction_id"],
            acknowledgement=acknowledgement,
            preconditions=intent["preconditions"],
            inventory_preconditions=[],
            outputs=intent["outputs"],
            marker=intent["marker"],
            destination_validator=validate_destination,
        )
    except EvidencePublicationError as exc:
        raise VerifierError("VERIFIER-TRANSACTION-INCOMPLETE", str(exc)) from exc


def _path(value: str) -> Path:
    return Path(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    publish_parser = sub.add_parser("publish")
    publish_parser.add_argument("--artifact", type=_path, required=True)
    publish_parser.add_argument("--semantic-receipt", type=_path, required=True)
    publish_parser.add_argument("--phase", choices=("generation", "evaluation"), required=True)
    publish_parser.add_argument("--project-root", type=_path, required=True)
    publish_parser.add_argument("--wiki-root", type=_path, required=True)
    publish_parser.add_argument("--harness-root", type=_path, default=ROOT)
    publish_parser.add_argument(
        "--semantics-manifest",
        type=_path,
        default=ROOT / "references" / "semantics_manifest.v1.json",
    )
    publish_parser.add_argument("--out-dir", type=_path, required=True)
    publish_parser.add_argument(
        "--requested-independence-level",
        choices=("none", "dispatch_separation", "host_attested_independence"),
        default="none",
    )

    validate_parser = sub.add_parser("validate")
    validate_parser.add_argument("--transaction", type=_path, required=True)
    validate_parser.add_argument("--publication-manifest", type=_path, required=True)
    validate_parser.add_argument("--commit-marker", type=_path, required=True)
    validate_parser.add_argument("--artifact", type=_path, required=True)
    validate_parser.add_argument("--semantic-receipt", type=_path, required=True)
    validate_parser.add_argument("--project-root", type=_path, required=True)
    validate_parser.add_argument("--wiki-root", type=_path, required=True)
    validate_parser.add_argument("--harness-root", type=_path, default=ROOT)
    validate_parser.add_argument(
        "--semantics-manifest",
        type=_path,
        default=ROOT / "references" / "semantics_manifest.v1.json",
    )

    recover_parser = sub.add_parser("recover")
    recover_parser.add_argument("--transaction", type=_path, required=True)
    recover_parser.add_argument("--publication-manifest", type=_path, required=True)
    recover_parser.add_argument("--commit-marker", type=_path, required=True)
    recover_parser.add_argument("--artifact", type=_path, required=True)
    recover_parser.add_argument("--semantic-receipt", type=_path, required=True)
    recover_parser.add_argument("--project-root", type=_path, required=True)
    recover_parser.add_argument("--wiki-root", type=_path, required=True)
    recover_parser.add_argument("--harness-root", type=_path, default=ROOT)
    recover_parser.add_argument(
        "--semantics-manifest",
        type=_path,
        default=ROOT / "references" / "semantics_manifest.v1.json",
    )
    recover_parser.add_argument(
        "--acknowledgement",
        required=True,
        help="must be inspected-evidence-state-and-journal",
    )

    args = parser.parse_args(argv)
    try:
        if args.command == "publish":
            result = publish_verifier_transaction(
                artifact=args.artifact,
                semantic_receipt=args.semantic_receipt,
                phase=args.phase,
                project_root=args.project_root,
                wiki_root=args.wiki_root,
                harness_root=args.harness_root,
                semantics_manifest=args.semantics_manifest,
                out_dir=args.out_dir,
                requested_independence_level=args.requested_independence_level,
            )
            payload = {
                "schema_version": "1.0.0",
                "report_type": "verifier_publication",
                "status": "committed",
                **{
                    key: str(value) if isinstance(value, Path) else value
                    for key, value in result.items()
                },
            }
        elif args.command == "validate":
            transaction = validate_verifier_transaction(
                transaction=args.transaction,
                publication_manifest=args.publication_manifest,
                commit_marker=args.commit_marker,
                artifact=args.artifact,
                semantic_receipt=args.semantic_receipt,
                project_root=args.project_root,
                wiki_root=args.wiki_root,
                harness_root=args.harness_root,
                semantics_manifest=args.semantics_manifest,
            )
            payload = {
                "schema_version": "1.0.0",
                "report_type": "verifier_validation",
                "status": "verified",
                "transaction": transaction,
            }
        else:
            recovery_state = recover_verifier_transaction(
                transaction=args.transaction,
                publication_manifest=args.publication_manifest,
                commit_marker=args.commit_marker,
                artifact=args.artifact,
                semantic_receipt=args.semantic_receipt,
                project_root=args.project_root,
                wiki_root=args.wiki_root,
                harness_root=args.harness_root,
                semantics_manifest=args.semantics_manifest,
                acknowledgement=args.acknowledgement,
            )
            payload = {
                "schema_version": "1.0.0",
                "report_type": "verifier_recovery",
                "status": recovery_state,
                "transaction_id": json.loads(
                    args.transaction.read_text(encoding="utf-8")
                )["transaction_id"],
            }
    except VerifierError as exc:
        payload = {
            "schema_version": "1.0.0",
            "report_type": "verifier_blocker",
            "status": "blocked",
            "reason_code": exc.code,
            "detail": exc.message,
        }
        print(json.dumps(payload, ensure_ascii=False))
        return 4
    except (OSError, KeyError, TypeError, ValueError) as exc:
        payload = {
            "schema_version": "1.0.0",
            "report_type": "verifier_blocker",
            "status": "blocked",
            "reason_code": "VERIFIER-TRANSACTION-INCOMPLETE",
            "detail": str(exc),
        }
        print(json.dumps(payload, ensure_ascii=False))
        return 4
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
