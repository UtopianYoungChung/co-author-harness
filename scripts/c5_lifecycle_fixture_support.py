#!/usr/bin/env python3
"""Synthetic-only C5 lifecycle evidence builder for semantic gate fixtures."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import uuid

import assignment_dispatch_claim as claims
import draft_evidence_verifier as verifier
from assignment_receipt_transaction import (
    _assignment_root,
    _mutation_row_hash,
    load_mutation_ledger,
)
from c2_evidence_fixture_support import build_activation_fixture


ROOT = Path(__file__).resolve().parents[1]
SEMANTICS = ROOT / "references" / "semantics_manifest.v1.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def write_receipt_transition(path: Path, value: dict[str, str]) -> None:
    """Write the exact canonical kernel-ledger event used by this synthetic fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(value, sort_keys=True).encode("utf-8") + b"\n")


def _binding(project: Path, path: Path, root: str) -> dict[str, str]:
    base = project if root == "project" else ROOT
    return {
        "root": root,
        "path": path.resolve().relative_to(base.resolve()).as_posix(),
        "sha256": sha(path),
    }


def _snapshot(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {"exists": False, "sha256": None, "size": 0}
    return {"exists": True, "sha256": sha(path), "size": path.stat().st_size}


def _append_mutation(
    project: Path, *, receipt_id: str, reservation_id: str,
    target: str, preimage: dict[str, object],
) -> dict[str, object]:
    rows = load_mutation_ledger(project)
    artifact = project / Path(target)
    row: dict[str, object] = {
        "schema_version": "1.0.0",
        "sequence": len(rows) + 1,
        "prior_row_sha256": rows[-1]["row_sha256"] if rows else None,
        "receipt_id": receipt_id,
        "reservation_id": reservation_id,
        "target_path": target,
        "mode": "replace" if preimage["exists"] else "create",
        "preimage": preimage,
        "postimage": _snapshot(artifact),
    }
    row["row_sha256"] = _mutation_row_hash(row)
    ledger = _assignment_root(project) / "mutation_ledger.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("ab") as handle:
        handle.write(json.dumps(row, sort_keys=True).encode("utf-8") + b"\n")
    return row


def _locator(
    project: Path, *, lane: Path, phase: str, target: str, receipt_id: str,
    paths: dict[str, object], semantic_receipt: Path, wiki_root: Path,
    claim: Path, consumption: Path, generation_id: str | None,
) -> dict[str, str]:
    locator = lane / f"{phase}.lifecycle.json"
    write_json(locator, {
        "schema_version": "1.0.0",
        "binding_type": "lifecycle_verifier_transaction",
        "phase": phase,
        "product_disposition": (
            "evaluation_ready" if phase == "generation" else "product_qualified"
        ),
        "target": target,
        "receipt_id": receipt_id,
        "transaction": _binding(project, paths["transaction"], "project"),
        "publication_manifest": _binding(
            project, paths["publication_manifest"], "project"
        ),
        "commit_marker": _binding(project, paths["commit_marker"], "project"),
        "semantic_receipt": _binding(project, semantic_receipt, "project"),
        "wiki_root": {
            "root": "harness",
            "path": wiki_root.resolve().relative_to(ROOT).as_posix(),
            "manifest_sha256": sha(wiki_root / "manifest.json"),
        },
        "semantics_manifest": _binding(project, SEMANTICS, "harness"),
        "dispatch_claim": _binding(project, claim, "project"),
        "dispatch_consumption": _binding(project, consumption, "project"),
        "generation_verifier_transaction_id": generation_id,
    })
    return {
        "evidence_path": locator.relative_to(project).as_posix(),
        "evidence_sha256": sha(locator),
    }


def build_existing_artifact_pair(
    project: Path, *, artifact_relative: str, public_milestone: str, label: str,
) -> dict[str, object]:
    """Replace a synthetic artifact and issue a fully replayable C5 pair."""
    project = project.resolve()
    artifact = project / Path(artifact_relative)
    preimage = _snapshot(artifact)
    manifest = project / "project_manifest.json"
    if not manifest.is_file():
        write_json(manifest, {
            "schema_version": "synthetic-nonqualifying-1.0.0",
            "identity": "c5-terminal-lifecycle-fixture",
            "fixture_id": "c5-terminal-lifecycle-fixture",
            "production_authority": False,
        })
    activation = build_activation_fixture(
        project,
        artifact_relative=artifact_relative,
        evidence_relative=f"reviews/.harness/fixtures/{label}",
    )
    activation.mutate_artifact(
        lambda text: f"{text}\n\nSynthetic lifecycle target {label}.\n"
    )

    receipt_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"c5:{label}:receipt"))
    reservation_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"c5:{label}:reservation"))
    assignment = _assignment_root(project)
    reserved = assignment / "reserved" / f"gate_receipt_{public_milestone}_{label}.json"
    consumed = assignment / "consumed" / reserved.name
    receipt = {
        "schema_version": "2.1.0",
        "receipt_id": receipt_id,
        "reservation_id": reservation_id,
        "stage": "final" if public_milestone == "FINAL" else "draft",
        "target_milestone": public_milestone,
        "authorized_role": "generator",
        "authorized_paths": [artifact_relative],
        "authorized_writes": [{"path": artifact_relative, "mode": "replace"}],
        "primary_deliverable_path": artifact_relative,
    }
    write_json(reserved, receipt)
    write_json(consumed, receipt)
    reservation = assignment / "reservations" / f"{receipt_id}.json"
    write_json(reservation, {
        "schema_version": "1.0.0",
        "receipt_id": receipt_id,
        "receipt_sha256": sha(reserved),
        "reservation_id": reservation_id,
        "role": "generator",
        "target_milestone": public_milestone,
        "writes": [{
            "mode": "replace" if preimage["exists"] else "create",
            "path": artifact_relative,
            "preimage": preimage,
        }],
    })
    write_receipt_transition(
        assignment / "ledger" / f"{reserved.name}.jsonl",
        {
            "state": "reserved",
            "receipt_id": receipt_id,
            "reservation_id": reservation_id,
        },
    )
    mutation = _append_mutation(
        project, receipt_id=receipt_id, reservation_id=reservation_id,
        target=artifact_relative, preimage=preimage,
    )

    generation, generation_path, _ = claims.issue_generation_claim(
        project,
        reserved,
        policy_path=activation.wiki_root / "policy.json",
        bibliography_snapshot=activation.bibliography_snapshot,
        nonce=hashlib.sha256(f"{label}:generation".encode()).hexdigest()[:32],
        issuer_transaction_id=f"assignment-reserve-{public_milestone}",
        issued_at="2026-07-25T12:00:00Z",
    )
    generation_consumption, generation_consumption_path, _ = (
        claims.consume_dispatch_claim(
            project, generation_path, role="generator",
            consumer_transaction_id=f"assignment-write-{public_milestone}",
            target_paths=[artifact_relative], consumed_at="2026-07-25T12:00:01Z",
        )
    )
    lane = project / "reviews/.harness/verifier" / label
    generation_paths = verifier.publish_verifier_transaction(
        artifact=artifact, semantic_receipt=activation.receipt,
        phase="generation", project_root=project, wiki_root=activation.wiki_root,
        harness_root=ROOT, semantics_manifest=SEMANTICS,
        out_dir=lane / "generation", requested_independence_level="none",
    )
    evaluation, evaluation_path, _ = claims.issue_evaluation_claim(
        project,
        generation_path,
        generation_consumption=generation_consumption_path,
        artifact=artifact,
        generation_transaction=generation_paths["transaction"],
        generation_publication_manifest=generation_paths["publication_manifest"],
        generation_commit_marker=generation_paths["commit_marker"],
        generation_semantic_receipt=activation.receipt,
        wiki_root=activation.wiki_root,
        semantics_manifest=SEMANTICS,
        nonce=hashlib.sha256(f"{label}:evaluation".encode()).hexdigest()[:32],
        issuer_transaction_id=f"assignment-evaluation-{public_milestone}",
        issued_at="2026-07-25T12:00:02Z",
    )
    evaluation_consumption, evaluation_consumption_path, _ = (
        claims.consume_dispatch_claim(
            project, evaluation_path, role="evaluator",
            consumer_transaction_id=f"evaluation-{public_milestone}",
            target_paths=[artifact_relative], consumed_at="2026-07-25T12:00:03Z",
        )
    )
    evaluation_semantic = lane / "evaluation-semantic.json"
    evaluation_value = json.loads(activation.receipt.read_text(encoding="utf-8"))
    evaluation_value["phase"] = "evaluation"
    evaluation_value["role"] = "evaluator"
    write_json(evaluation_semantic, evaluation_value)
    evaluation_paths = verifier.publish_verifier_transaction(
        artifact=artifact, semantic_receipt=evaluation_semantic,
        phase="evaluation", project_root=project, wiki_root=activation.wiki_root,
        harness_root=ROOT, semantics_manifest=SEMANTICS,
        out_dir=lane / "evaluation", requested_independence_level="none",
    )
    generation_id = json.loads(
        generation_paths["transaction"].read_text(encoding="utf-8")
    )["transaction_id"]
    policy = {
        "draft_generation": _locator(
            project, lane=lane, phase="generation", target=artifact_relative,
            receipt_id=receipt_id, paths=generation_paths,
            semantic_receipt=activation.receipt, wiki_root=activation.wiki_root,
            claim=generation_path, consumption=generation_consumption_path,
            generation_id=None,
        ),
        "draft_evaluation": _locator(
            project, lane=lane, phase="evaluation", target=artifact_relative,
            receipt_id=receipt_id, paths=evaluation_paths,
            semantic_receipt=evaluation_semantic, wiki_root=activation.wiki_root,
            claim=evaluation_path, consumption=evaluation_consumption_path,
            generation_id=generation_id,
        ),
    }
    return {
        "policy_evidence": policy,
        "artifact_sha256": sha(artifact),
        "artifact_bytes": artifact.stat().st_size,
        "old_artifact_sha256": preimage["sha256"],
        "mutation_row": mutation,
        "generation_claim": generation,
        "generation_consumption": generation_consumption,
        "evaluation_claim": evaluation,
        "evaluation_consumption": evaluation_consumption,
    }
