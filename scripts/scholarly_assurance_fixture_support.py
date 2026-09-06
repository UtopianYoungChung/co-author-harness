#!/usr/bin/env python3
"""Reusable synthetic C2-C6 evidence built through production verifiers.

This module is test support only.  It creates no live-research content and
keeps its synthetic project beneath the caller-provided root.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import assignment_dispatch_claim as dispatch
import d_style_profile_check as dstyle
import draft_evidence_verifier as verifier
import obligation_result as obligations
import scholarly_claim_register as claim_register
import scholarly_evaluation
from assignment_receipt_transaction import _assignment_root
from c2_evidence_fixture_support import ActivationFixture, build_activation_fixture
from c5_lifecycle_fixture_support import _append_mutation, _snapshot, write_receipt_transition


ROOT = Path(__file__).resolve().parents[1]
SEMANTICS = ROOT / "references/semantics_manifest.v1.json"
REGISTRY = ROOT / "references/policies/obligation_result_registry.v1.json"
CASES = ROOT / "scripts/fixtures/scholarly_evaluation_profile/cases.json"


@dataclass(frozen=True)
class ScholarlyAssuranceFixture:
    project: Path
    artifact: Path
    activation: ActivationFixture
    evaluation: Path
    binding: dict[str, str]
    verified: dict[str, Any]
    semantics_manifest: Path
    generation_verifier: dict[str, Path]
    evaluation_consumption: Path
    evaluation_semantic_receipt: Path | None
    evaluation_verifier: dict[str, Path]


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def binding(project: Path, path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    return {
        "path": path.resolve().relative_to(project.resolve()).as_posix(),
        "sha256": sha256_bytes(payload),
        "byte_length": len(payload),
    }


def _fresh_semantics(project: Path, label: str) -> Path:
    value = json.loads(SEMANTICS.read_text(encoding="utf-8"))
    for row in value["members"]:
        row["sha256"] = sha256(ROOT / row["path"])
    path = project / "reviews/.harness/fixtures" / label / "semantics-manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(verifier.canonical_bytes(value))
    return path


def fresh_semantics_manifest(project: Path, label: str) -> Path:
    """Publish a synthetic exact-current semantics manifest for fixture APIs."""

    return _fresh_semantics(project.resolve(), label)


def _prepare_dispatch(
    project: Path,
    *,
    artifact_relative: str,
    text: str,
    label: str,
    activation: ActivationFixture | None = None,
    mutate_artifact: bool = True,
) -> dict[str, Any]:
    artifact = project / artifact_relative
    preimage = _snapshot(artifact)
    if activation is None:
        activation = build_activation_fixture(
            project,
            artifact_relative=artifact_relative,
            evidence_relative=f"reviews/.harness/fixtures/{label}",
        )
    elif activation.artifact.resolve() != artifact.resolve():
        raise ValueError("activation artifact differs from requested artifact_relative")
    if mutate_artifact:
        activation.mutate_artifact(
            lambda original: f"{original.rstrip()}\n\n# Synthetic analysis\n\n{text}\n"
        )
    elif text not in artifact.read_text(encoding="utf-8"):
        raise ValueError("already-current artifact does not contain the exact claim text")
    semantics = _fresh_semantics(project, label)
    manifest = project / "project_manifest.json"
    if not manifest.is_file():
        write_json(
            manifest,
            {
                "schema_version": "synthetic-nonqualifying-1.0.0",
                "identity": "scholarly-assurance-fixture",
                "fixture_id": "scholarly-assurance-fixture",
                "production_authority": False,
            },
        )
    receipt_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"assurance:{label}:receipt"))
    reservation_id = str(
        uuid.uuid5(uuid.NAMESPACE_URL, f"assurance:{label}:reservation")
    )
    assignment = _assignment_root(project)
    reserved = assignment / "reserved" / f"gate_receipt_M1_{label}.json"
    consumed = assignment / "consumed" / reserved.name
    receipt = {
        "schema_version": "2.1.0",
        "receipt_id": receipt_id,
        "reservation_id": reservation_id,
        "stage": "draft",
        "target_milestone": "M1",
        "authorized_role": "generator",
        "authorized_paths": [artifact_relative],
        "authorized_writes": [
            {
                "path": artifact_relative,
                "mode": "replace" if preimage["exists"] else "create",
            }
        ],
        "primary_deliverable_path": artifact_relative,
    }
    write_json(reserved, receipt)
    write_json(consumed, receipt)
    reservation = assignment / "reservations" / f"{receipt_id}.json"
    write_json(
        reservation,
        {
            "schema_version": "1.0.0",
            "receipt_id": receipt_id,
            "receipt_sha256": sha256(reserved),
            "reservation_id": reservation_id,
            "role": "generator",
            "target_milestone": "M1",
            "writes": [
                {
                    "mode": "replace" if preimage["exists"] else "create",
                    "path": artifact_relative,
                    "preimage": preimage,
                }
            ],
        },
    )
    write_receipt_transition(
        assignment / "ledger" / f"{reserved.name}.jsonl",
        {"state": "reserved", "receipt_id": receipt_id, "reservation_id": reservation_id},
    )
    _append_mutation(
        project,
        receipt_id=receipt_id,
        reservation_id=reservation_id,
        target=artifact_relative,
        preimage=preimage,
    )
    generation, generation_path, _ = dispatch.issue_generation_claim(
        project,
        reserved,
        policy_path=activation.wiki_root / "policy.json",
        bibliography_snapshot=activation.bibliography_snapshot,
        nonce=hashlib.sha256(f"{label}:generation".encode()).hexdigest()[:32],
        issuer_transaction_id="assignment-reserve-M1",
        issued_at="2026-07-26T00:00:00Z",
    )
    _, generation_consumption, _ = dispatch.consume_dispatch_claim(
        project,
        generation_path,
        role="generator",
        consumer_transaction_id="assignment-write-M1",
        target_paths=[artifact_relative],
        consumed_at="2026-07-26T00:00:01Z",
    )
    verifier_root = project / "reviews/.harness/verifier" / label
    generation_paths = verifier.publish_verifier_transaction(
        artifact=artifact,
        semantic_receipt=activation.receipt,
        phase="generation",
        project_root=project,
        wiki_root=activation.wiki_root,
        harness_root=ROOT,
        semantics_manifest=semantics,
        out_dir=verifier_root / "generation",
        requested_independence_level="none",
    )
    evaluator, evaluator_path, _ = dispatch.issue_evaluation_claim(
        project,
        generation_path,
        generation_consumption=generation_consumption,
        artifact=artifact,
        generation_transaction=generation_paths["transaction"],
        generation_publication_manifest=generation_paths["publication_manifest"],
        generation_commit_marker=generation_paths["commit_marker"],
        generation_semantic_receipt=activation.receipt,
        wiki_root=activation.wiki_root,
        semantics_manifest=semantics,
        nonce=hashlib.sha256(f"{label}:evaluation".encode()).hexdigest()[:32],
        issuer_transaction_id="assignment-evaluation-M1",
        issued_at="2026-07-26T00:00:02Z",
    )
    return {
        "artifact": artifact,
        "artifact_relative": artifact_relative,
        "receipt_id": receipt_id,
        "reservation_id": reservation_id,
        "activation": activation,
        "semantics": semantics,
        "generation": generation,
        "generation_path": generation_path,
        "generation_consumption": generation_consumption,
        "generation_paths": generation_paths,
        "evaluator": evaluator,
        "evaluator_path": evaluator_path,
    }


def _span(artifact: Path, text: str) -> dict[str, Any]:
    payload = artifact.read_bytes()
    needle = text.encode("utf-8")
    start = payload.find(needle)
    if start < 0 or payload.find(needle, start + 1) >= 0:
        raise AssertionError("synthetic claim span must occur exactly once")
    return {
        "sha256": sha256_bytes(needle),
        "byte_start": start,
        "byte_end": start + len(needle),
        "line": payload[:start].count(b"\n") + 1,
        "section": claim_register._nearest_section(payload, start),
    }


def _profile(
    registry: dict[str, Any], *, obligation_ids: list[str] | None = None
) -> dict[str, Any]:
    fixture = json.loads(CASES.read_text(encoding="utf-8"))
    mapping = {
        "provenance": "provenance_integrity",
        "admission_use": "admission_use",
        "argument_leg": "argument_leg",
        "warrant_relation": "warrant_logic",
        "modal_force": "modal_consistency",
    }
    checks = {
        key: {}
        for key in (
            "milestone_criteria",
            "claim_register",
            "scope_quantifier",
            "provenance_integrity",
            "admission_use",
            "argument_leg",
            "warrant_logic",
            "modal_consistency",
            "grounding_citation",
            "d_style",
            "reader_accessibility",
            "active_overlays",
        )
    }
    for case in fixture["cases"]:
        checks[mapping[case["changed_field"]]][case["expected_scholarly_code"]] = "MAJOR"
    return {
        "schema_version": "1.0.0",
        "profile_id": "scholarly-evaluation-v1",
        "checks": [
            {
                "check_id": check_id,
                "allowed_omission_codes": [] if check_id != "active_overlays" else ["not_applicable"],
                "finding_severity_floor": floors,
            }
            for check_id, floors in checks.items()
        ],
        "obligation_registry": registry,
        "obligations": obligation_ids or [],
    }


def _dstyle_result(
    project: Path, artifact: Path, lane: Path, *, label: str
) -> Path:
    policy = lane / f"{label}-dstyle-policy.json"
    write_json(policy, {"schema_version": "1.0.0", "policy": "synthetic-only"})
    report_value = dstyle.build_report(
        project,
        project / "research_notes/directives.md",
        artifact,
    )
    report = lane / f"{label}-dstyle-report.json"
    write_json(report, report_value)
    artifact_binding = binding(project, artifact)
    findings: list[dict[str, Any]] = []
    for observed in report_value["findings"]:
        severity = observed["severity"]
        if severity not in {"BLOCKER", "MAJOR", "MINOR", "ADVISORY"}:
            continue
        evidence_identity = obligations._dstyle_evidence_identity(observed)
        findings.append(
            {
                "code": observed["code"],
                "severity": severity,
                "evidence_identity": evidence_identity,
                "fingerprint": obligations.finding_fingerprint(
                    "d-style-profile",
                    observed["code"],
                    severity,
                    evidence_identity,
                    artifact_binding["sha256"],
                ),
                "disposition": "open",
            }
        )
    result = lane / f"{label}-dstyle-result.json"
    write_json(
        result,
        {
            "schema_version": "1.0.0",
            "obligation_id": "d-style-profile",
            "adapter_version": "1.0.0",
            "artifact": artifact_binding,
            "policy": binding(project, policy),
            "report": binding(project, report),
            "activation": "always",
            "execution_status": "completed",
            "outcome": "findings" if findings else "clean",
            "findings": findings,
            "diagnostic_only": False,
            "created_at": "2026-07-26T00:00:03Z",
            "adjudications": [],
        },
    )
    return result


def _adjudicate_dstyle_result(
    project: Path,
    result_path: Path,
    prepared: dict[str, Any],
    *,
    label: str,
) -> list[dict[str, Any]]:
    """Resolve current D-STYLE blockers through a separate Evaluator dispatch."""

    result = json.loads(result_path.read_text(encoding="utf-8"))
    blocking = [
        row
        for row in result["findings"]
        if row["severity"] in {"BLOCKER", "MAJOR"}
    ]
    identities: list[dict[str, Any]] = []
    for index, finding in enumerate(blocking, start=1):
        token = f"{label}-dstyle-resolution-{index}"
        claim, claim_path, _ = dispatch.issue_evaluation_claim(
            project,
            prepared["generation_path"],
            generation_consumption=prepared["generation_consumption"],
            artifact=prepared["artifact"],
            generation_transaction=prepared["generation_paths"]["transaction"],
            generation_publication_manifest=prepared["generation_paths"]["publication_manifest"],
            generation_commit_marker=prepared["generation_paths"]["commit_marker"],
            generation_semantic_receipt=prepared["activation"].receipt,
            wiki_root=prepared["activation"].wiki_root,
            semantics_manifest=prepared["semantics"],
            nonce=hashlib.sha256(token.encode()).hexdigest()[:32],
            issuer_transaction_id="assignment-evaluation-M1",
            issued_at="2026-07-26T00:00:05Z",
        )
        artifact_binding = binding(project, prepared["artifact"])
        adjudication_without_receipt = {
            "schema_version": "1.0.0",
            "adjudication_id": token,
            "obligation_id": "d-style-profile",
            "finding_fingerprint": finding["fingerprint"],
            "artifact": artifact_binding,
            "disposition": "resolved",
            "authority": "independent-evaluator",
            "rationale": "A separately dispatched Evaluator rechecked the exact current synthetic bytes.",
            "resolution_verification": {
                "artifact_sha256": artifact_binding["sha256"],
                "artifact_byte_length": artifact_binding["byte_length"],
                "finding_fingerprint": finding["fingerprint"],
                "verified": True,
            },
            "created_at": "2026-07-26T00:00:06Z",
        }
        subject = {
            "schema_version": "1.0.0",
            "subject_type": "obligation_adjudication_authorization",
            "authority": "independent-evaluator",
            "adjudication_payload_sha256": sha256_bytes(
                canonical_bytes(adjudication_without_receipt)
            ),
            "obligation_id": "d-style-profile",
            "finding_fingerprint": finding["fingerprint"],
            "artifact": artifact_binding,
        }
        subject_path = result_path.with_name(f"{token}-subject.json")
        write_json(subject_path, subject)
        subject_relative = subject_path.relative_to(project).as_posix()
        _append_mutation(
            project,
            receipt_id=prepared["receipt_id"],
            reservation_id=prepared["reservation_id"],
            target=subject_relative,
            preimage={"exists": False, "sha256": None, "size": 0},
        )
        _, consumption_path, _ = dispatch.consume_dispatch_claim(
            project,
            claim_path,
            role="evaluator",
            consumer_transaction_id=f"obligation-adjudication:{token}",
            target_paths=[prepared["artifact_relative"], subject_relative],
            consumed_at="2026-07-26T00:00:07Z",
        )
        receipt_path = result_path.with_name(f"{token}-authority.json")
        write_json(
            receipt_path,
            {
                "schema_version": "1.0.0",
                "receipt_type": "obligation_adjudication_authority",
                "authority_mode": "assignment_dispatch",
                "authority": "independent-evaluator",
                "subject": binding(project, subject_path),
                "claim": binding(project, claim_path),
                "consumption": binding(project, consumption_path),
            },
        )
        adjudication = {
            **adjudication_without_receipt,
            "authority_receipt": binding(project, receipt_path),
        }
        result["adjudications"].append(adjudication)
        canonical = canonical_bytes(adjudication)
        identities.append(
            {
                "adjudication_id": adjudication["adjudication_id"],
                "canonical_sha256": sha256_bytes(canonical),
                "canonical_byte_length": len(canonical),
            }
        )
    write_json(result_path, result)
    return identities


def build_qualified_scholarly_fixture(
    project: Path,
    *,
    artifact_relative: str = "final.md",
    label: str = "qualified",
    claim_text: str = "A bounded synthetic claim remains qualified.",
    activation: ActivationFixture | None = None,
    mutate_artifact: bool = True,
    authorities: dict[str, Any] | None = None,
    include_dstyle: bool = False,
    adjudicate_dstyle: bool = False,
    allow_blocked: bool = False,
    legacy_semantic_evidence: bool = True,
) -> ScholarlyAssuranceFixture:
    """Build and verify one clean C2-C6 synthetic evaluation transaction."""

    project = project.resolve()
    if authorities is None:
        artifact_before = (
            (project / artifact_relative).read_bytes()
            if not mutate_artifact
            else None
        )
        prepared = _prepare_dispatch(
            project,
            artifact_relative=artifact_relative,
            text=claim_text,
            label=label,
            activation=activation,
            mutate_artifact=mutate_artifact,
        )
    else:
        required = {
            "artifact",
            "artifact_relative",
            "receipt_id",
            "reservation_id",
            "activation",
            "semantics",
            "generation",
            "generation_path",
            "generation_consumption",
            "generation_paths",
            "evaluator",
            "evaluator_path",
        }
        missing = sorted(required - set(authorities))
        if missing:
            raise ValueError(f"prepared scholarly authorities are incomplete: {missing}")
        prepared = dict(authorities)
        if prepared["artifact_relative"] != artifact_relative:
            raise ValueError("prepared authority target differs from artifact_relative")
        if prepared["artifact"].resolve() != (project / artifact_relative).resolve():
            raise ValueError("prepared authority artifact path is split")
        if prepared["activation"].artifact.resolve() != prepared["artifact"].resolve():
            raise ValueError("prepared C2 activation binds another artifact")
        if prepared["generation"].get("receipt_id") != prepared["receipt_id"]:
            raise ValueError("Generation claim receipt_id is split")
        if prepared["evaluator"].get("receipt_id") != prepared["receipt_id"]:
            raise ValueError("Evaluator claim receipt_id is split")
        artifact_before = prepared["artifact"].read_bytes()
    artifact = prepared["artifact"]
    lane = artifact.parent
    envelope = lane / f"{label}-generator-envelope.json"
    write_json(
        envelope,
        {
            "schema_version": "1.0.0",
            "envelope_type": "generator_envelope",
            "dispatch_id": prepared["generation"]["claim_id"],
            "role": "generator",
            "artifact": binding(project, artifact),
        },
    )
    criteria = lane / f"{label}-milestone-criteria.json"
    write_json(
        criteria,
        {
            "schema_version": "1.0.0",
            "milestone": "M1",
            "criteria": ["The synthetic claim remains bounded."],
        },
    )
    registry = project / f"policies/{label}-obligation-registry.json"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_bytes(REGISTRY.read_bytes())
    obligation_ids: list[str] = []
    obligation_results: list[dict[str, Any]] = []
    if include_dstyle:
        directives = project / "research_notes/directives.md"
        if not directives.is_file():
            directives.parent.mkdir(parents=True, exist_ok=True)
            directives.write_text(
                """d_style_profile:
  question_type: conceptual
  citation_style: venue_template
  source_role_policy: strict_role_classification
  evidence_display_policy: standard
  assistance_disclosure_policy: project_local
  harness_profile: standard_research_review
""",
                encoding="utf-8",
                newline="\n",
            )
        obligation_ids.append("d-style-profile")
        dstyle_result = _dstyle_result(project, artifact, lane, label=label)
        adjudication_identities = (
            _adjudicate_dstyle_result(
                project, dstyle_result, prepared, label=label
            )
            if adjudicate_dstyle
            else []
        )
        obligation_results.append(
            {
                "result": binding(project, dstyle_result),
                "adjudications": adjudication_identities,
            }
        )
    profile_path = lane / f"{label}-scholarly-profile.json"
    write_json(
        profile_path,
        _profile(binding(project, registry), obligation_ids=obligation_ids),
    )
    register = lane / f"{label}-claim-register.json"
    span = _span(artifact, claim_text)
    write_json(
        register,
        {
            "schema_version": "1.0.0",
            "register_id": f"SCR-{label.upper().replace('-', '_')}",
            "artifact": {
                "path": artifact.relative_to(register.parent).as_posix(),
                "sha256": sha256(artifact),
                "byte_length": artifact.stat().st_size,
            },
            "review_dispatch": {
                "dispatch_id": prepared["evaluator"]["claim_id"],
                "role": "evaluator",
            },
            "claims": [
                {
                    "claim_id": "C-001",
                    "text": claim_text,
                    "span_sha256": span["sha256"],
                    "locator": {
                        "section": span["section"],
                        "line": span["line"],
                        "byte_start": span["byte_start"],
                        "byte_end": span["byte_end"],
                    },
                    "load_bearing": True,
                    "viewpoint": "project_position",
                    "provenance": "author_derivation",
                    "admission_use": "working_position",
                    "argument_leg": "composition",
                    "modal_force": "qualified",
                    "warrant_relation": "candidate",
                }
            ],
            "generator_inventory": ["C-001"],
            "evaluator_additions": [],
            "evaluator_omissions": [],
            "coverage_disposition": "complete",
            "created_at": "2026-07-26T00:00:03Z",
        },
    )
    register_result = claim_register.validate_register(artifact, register)
    if register_result.get("status") != "qualified":
        raise AssertionError(
            "synthetic claim register did not qualify before C6 assembly: "
            f"{register_result!r}"
        )
    artifact_binding = binding(project, artifact)
    evaluation_id = f"SET-{label.upper().replace('-', '_')}"
    evaluation_path = lane / f"{label}-scholarly-evaluation.json"
    unresolved_obligation = any(
        row["severity"] in {"BLOCKER", "MAJOR"}
        for entry in obligation_results
        for row in json.loads(
            (project / entry["result"]["path"]).read_text(encoding="utf-8")
        )["findings"]
    ) and not adjudicate_dstyle
    evaluation_value = {
        "schema_version": "1.0.0",
        "evaluation_id": evaluation_id,
        "artifact": artifact_binding,
        "generator_envelope": binding(project, envelope),
        "evaluation_dispatch": {
            "claim": binding(project, prepared["evaluator_path"]),
            "consumer_transaction_id": f"scholarly-evaluation:{evaluation_id}",
        },
        "claim_register": binding(project, register),
        "milestone_criteria": binding(project, criteria),
        "scholarly_profile": binding(project, profile_path),
        "findings": [],
        "omitted_checks": [],
        "obligation_results": obligation_results,
        "dispatch_separation": {
            "generator_claim_id": prepared["generation"]["claim_id"],
            "evaluator_claim_id": prepared["evaluator"]["claim_id"],
            "separate": True,
            "independence_level": "dispatch_separation",
        },
        "verdict": {
            "status": "blocked" if unresolved_obligation else "qualified",
            "check_results": [
                {
                    "check_id": row["check_id"],
                    "status": "pass",
                    "evidence": [artifact_binding],
                    "reasoning": "The independent synthetic Evaluator recorded a bounded pass.",
                }
                for row in json.loads(profile_path.read_text(encoding="utf-8"))["checks"]
            ],
        },
        "created_at": "2026-07-26T00:00:04Z",
    }
    write_json(evaluation_path, evaluation_value)
    evaluation_relative = evaluation_path.relative_to(project).as_posix()
    _append_mutation(
        project,
        receipt_id=prepared["receipt_id"],
        reservation_id=prepared["reservation_id"],
        target=evaluation_relative,
        preimage={"exists": False, "sha256": None, "size": 0},
    )
    _, evaluation_consumption, _ = dispatch.consume_dispatch_claim(
        project,
        prepared["evaluator_path"],
        role="evaluator",
        consumer_transaction_id=f"scholarly-evaluation:{evaluation_id}",
        target_paths=[artifact_relative, evaluation_relative],
        consumed_at="2026-07-26T00:00:05Z",
    )
    evaluation_semantic = None
    evaluation_verifier = {}
    if legacy_semantic_evidence:
        evaluation_semantic = project / f"reviews/.harness/verifier/{label}/evaluation-semantic.json"
        semantic_value = json.loads(prepared["activation"].receipt.read_text(encoding="utf-8"))
        semantic_value["phase"] = "evaluation"
        semantic_value["role"] = "evaluator"
        evaluation_semantic.parent.mkdir(parents=True, exist_ok=True)
        evaluation_semantic.write_bytes(verifier.canonical_bytes(semantic_value))
        evaluation_verifier = verifier.publish_verifier_transaction(
            artifact=artifact,
            semantic_receipt=evaluation_semantic,
            phase="evaluation",
            project_root=project,
            wiki_root=prepared["activation"].wiki_root,
            harness_root=ROOT,
            semantics_manifest=prepared["semantics"],
            out_dir=project / f"reviews/.harness/verifier/{label}/evaluation-product",
            requested_independence_level="none",
        )
    scholarly_binding = {
        "evidence_path": evaluation_relative,
        "evidence_sha256": sha256(evaluation_path),
    }
    try:
        verified = scholarly_evaluation.validate_scholarly_evaluation_binding(
            project,
            artifact,
            scholarly_binding,
        )
    except scholarly_evaluation.EvaluationRefusal as exc:
        if not (allow_blocked and exc.code == scholarly_evaluation.SET_FINDING_UNRESOLVED):
            raise
        verified = scholarly_evaluation.verify_evaluation(
            project, artifact, register, evaluation_path
        )
    if verified.get("status") not in ({"qualified", "blocked"} if allow_blocked else {"qualified"}):
        raise AssertionError(f"synthetic scholarly fixture did not qualify: {verified!r}")
    if artifact_before is not None and artifact.read_bytes() != artifact_before:
        raise AssertionError("already-current artifact changed while constructing C3-C6 evidence")
    return ScholarlyAssuranceFixture(
        project=project,
        artifact=artifact,
        activation=prepared["activation"],
        evaluation=evaluation_path,
        binding=scholarly_binding,
        verified=verified,
        semantics_manifest=prepared["semantics"],
        generation_verifier=prepared["generation_paths"],
        evaluation_consumption=evaluation_consumption,
        evaluation_semantic_receipt=evaluation_semantic,
        evaluation_verifier=evaluation_verifier,
    )


def build_qualified_scholarly_from_authorities(
    project: Path,
    *,
    authorities: dict[str, Any],
    label: str,
    claim_text: str,
    include_dstyle: bool = False,
    adjudicate_dstyle: bool = False,
    allow_blocked: bool = False,
    legacy_semantic_evidence: bool = True,
) -> ScholarlyAssuranceFixture:
    """Bind C3-C6 to one already-current, unconsumed Evaluator chain."""

    return build_qualified_scholarly_fixture(
        project,
        artifact_relative=authorities["artifact_relative"],
        label=label,
        claim_text=claim_text,
        activation=authorities["activation"],
        mutate_artifact=False,
        authorities=authorities,
        include_dstyle=include_dstyle,
        adjudicate_dstyle=adjudicate_dstyle,
        allow_blocked=allow_blocked,
        legacy_semantic_evidence=legacy_semantic_evidence,
    )


def prepare_synthetic_authorities(
    project: Path,
    *,
    activation: ActivationFixture,
    artifact_relative: str,
    label: str,
    claim_text: str,
) -> dict[str, Any]:
    """Prepare one synthetic same-receipt chain with Evaluator unconsumed."""

    return _prepare_dispatch(
        project.resolve(),
        artifact_relative=artifact_relative,
        text=claim_text,
        label=label,
        activation=activation,
        mutate_artifact=False,
    )


__all__ = [
    "ScholarlyAssuranceFixture",
    "binding",
    "build_qualified_scholarly_from_authorities",
    "build_qualified_scholarly_fixture",
    "canonical_bytes",
    "fresh_semantics_manifest",
    "prepare_synthetic_authorities",
    "sha256",
    "write_json",
]
