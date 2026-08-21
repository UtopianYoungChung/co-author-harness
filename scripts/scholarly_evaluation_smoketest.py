#!/usr/bin/env python3
"""Synthetic C6 qualification for the scholarly evaluation transaction."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

import assignment_dispatch_claim as dispatch
import d_style_profile_check as dstyle
import draft_evidence_verifier as verifier
import obligation_result as obligations
import scholarly_evaluation as evaluation
from assignment_receipt_transaction import _assignment_root
from c2_evidence_fixture_support import build_activation_fixture
from c5_lifecycle_fixture_support import _append_mutation, _snapshot, write_receipt_transition


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "scholarly_evaluation.py"
SCHEMA = ROOT / "references" / "schemas" / "scholarly_evaluation.schema.json"
CASES = ROOT / "scripts" / "fixtures" / "scholarly_evaluation_profile" / "cases.json"
SEMANTICS = ROOT / "references" / "semantics_manifest.v1.json"
REGISTRY = ROOT / "references" / "policies" / "obligation_result_registry.v1.json"


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _binding(project: Path, path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {
        "path": path.resolve().relative_to(project.resolve()).as_posix(),
        "sha256": _sha_bytes(raw),
        "byte_length": len(raw),
    }


def _fresh_semantics(project: Path, label: str) -> Path:
    """Freeze current harness semantics for one uncommitted synthetic case."""

    value = json.loads(SEMANTICS.read_text(encoding="utf-8"))
    for row in value["members"]:
        row["sha256"] = _sha_bytes((ROOT / row["path"]).read_bytes())
    path = project / "reviews/.harness/fixtures" / label / "semantics-manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(verifier.canonical_bytes(value))
    return path


def _span(artifact: Path, text: str) -> dict[str, Any]:
    raw = artifact.read_bytes()
    needle = text.encode("utf-8")
    start = raw.find(needle)
    if start < 0 or raw.find(needle, start + 1) >= 0:
        raise AssertionError(f"span must occur exactly once: {text!r}")
    return {
        "text": text,
        "sha256": _sha_bytes(needle),
        "byte_start": start,
        "byte_end": start + len(needle),
        "locator": {
            "section": "Synthetic analysis",
            "line": raw[:start].count(b"\n") + 1,
        },
    }


def _evidence_span(path: Path, register: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {
        "path": path.relative_to(register.parent).as_posix(),
        "sha256": _sha_bytes(raw),
        "byte_start": 0,
        "byte_end": len(raw),
        "span_sha256": _sha_bytes(raw),
    }


def _claim_register(
    artifact: Path,
    register: Path,
    claim_text: str,
    profile: dict[str, str],
    evaluator_id: str,
    sources: tuple[Path, Path],
) -> dict[str, Any]:
    span = _span(artifact, claim_text)
    claim: dict[str, Any] = {
        "claim_id": "C-001",
        "text": claim_text,
        "span_sha256": span["sha256"],
        "locator": {
            "section": span["locator"]["section"],
            "line": span["locator"]["line"],
            "byte_start": span["byte_start"],
            "byte_end": span["byte_end"],
        },
        "load_bearing": True,
        **profile,
    }
    if profile["provenance"] == "direct_source":
        claim["evidence_locator"] = [_evidence_span(sources[0], register)]
    elif profile["provenance"] == "cross_source_comparison":
        claim["evidence_locator"] = [
            _evidence_span(sources[0], register),
            _evidence_span(sources[1], register),
        ]
    return {
        "schema_version": "1.0.0",
        "register_id": "SCR-SYNTHETIC-EVAL-001",
        "artifact": {
            "path": artifact.relative_to(register.parent).as_posix(),
            "sha256": _sha_bytes(artifact.read_bytes()),
            "byte_length": artifact.stat().st_size,
        },
        "review_dispatch": {"dispatch_id": evaluator_id, "role": "evaluator"},
        "claims": [claim],
        "generator_inventory": ["C-001"],
        "evaluator_additions": [],
        "evaluator_omissions": [],
        "coverage_disposition": "complete",
        "created_at": "2026-07-26T00:00:00Z",
    }


def _prepare_dispatch(
    project: Path, *, artifact_relative: str, text: str, label: str
) -> dict[str, Any]:
    """Issue a real synthetic Generator/Evaluator pair; leave Evaluator unconsumed."""

    artifact = project / artifact_relative
    preimage = _snapshot(artifact)
    activation = build_activation_fixture(
        project,
        artifact_relative=artifact_relative,
        evidence_relative=f"reviews/.harness/fixtures/{label}",
    )
    activation.mutate_artifact(
        lambda original: f"{original.rstrip()}\n\n# Synthetic analysis\n\n{text}\n"
    )
    semantics = _fresh_semantics(project, label)
    manifest = project / "project_manifest.json"
    if not manifest.is_file():
        _write_json(
            manifest,
            {
                "schema_version": "synthetic-nonqualifying-1.0.0",
                "identity": "c6-scholarly-evaluation-fixture",
                "fixture_id": "c6-scholarly-evaluation-fixture",
                "production_authority": False,
            },
        )
    receipt_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"c6:{label}:receipt"))
    reservation_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"c6:{label}:reservation"))
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
        "authorized_writes": [{"path": artifact_relative, "mode": "create"}],
        "primary_deliverable_path": artifact_relative,
    }
    _write_json(reserved, receipt)
    _write_json(consumed, receipt)
    reservation = assignment / "reservations" / f"{receipt_id}.json"
    _write_json(
        reservation,
        {
            "schema_version": "1.0.0",
            "receipt_id": receipt_id,
            "receipt_sha256": _sha_bytes(reserved.read_bytes()),
            "reservation_id": reservation_id,
            "role": "generator",
            "target_milestone": "M1",
            "writes": [{"mode": "create", "path": artifact_relative, "preimage": preimage}],
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
    _, generation_consumption_path, _ = dispatch.consume_dispatch_claim(
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
        out_dir=verifier_root,
        requested_independence_level="none",
    )
    evaluator_claim, evaluator_path, _ = dispatch.issue_evaluation_claim(
        project,
        generation_path,
        generation_consumption=generation_consumption_path,
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
        "generation_claim": generation,
        "generation_path": generation_path,
        "generation_consumption_path": generation_consumption_path,
        "generation_paths": generation_paths,
        "activation": activation,
        "semantics": semantics,
        "evaluator_claim": evaluator_claim,
        "evaluator_path": evaluator_path,
    }


def _additional_evaluator(
    project: Path, prepared: dict[str, Any], label: str
) -> dict[str, Any]:
    claim, path, _ = dispatch.issue_evaluation_claim(
        project,
        prepared["generation_path"],
        generation_consumption=prepared["generation_consumption_path"],
        artifact=prepared["artifact"],
        generation_transaction=prepared["generation_paths"]["transaction"],
        generation_publication_manifest=prepared["generation_paths"]["publication_manifest"],
        generation_commit_marker=prepared["generation_paths"]["commit_marker"],
        generation_semantic_receipt=prepared["activation"].receipt,
        wiki_root=prepared["activation"].wiki_root,
        semantics_manifest=prepared["semantics"],
        nonce=hashlib.sha256(f"{label}:evaluation".encode()).hexdigest()[:32],
        issuer_transaction_id="assignment-evaluation-M1",
        issued_at="2026-07-26T00:00:02Z",
    )
    return {**prepared, "evaluator_claim": claim, "evaluator_path": path}


def _consume_evaluator(project: Path, prepared: dict[str, Any], extra: list[str] | None = None) -> Path:
    _, path, _ = dispatch.consume_dispatch_claim(
        project,
        prepared["evaluator_path"],
        role="evaluator",
        consumer_transaction_id=f"evaluation-M1-{prepared['evaluator_claim']['claim_id']}",
        target_paths=[prepared["artifact_relative"], *(extra or [])],
        consumed_at="2026-07-26T00:00:03Z",
    )
    return path


def _profile(cases: list[dict[str, Any]], registry_binding: dict[str, Any], obligations_: list[str] | None = None) -> dict[str, Any]:
    mapping = {
        "provenance": "provenance_integrity",
        "admission_use": "admission_use",
        "argument_leg": "argument_leg",
        "warrant_relation": "warrant_logic",
        "modal_force": "modal_consistency",
    }
    checks: dict[str, dict[str, str]] = {
        "milestone_criteria": {},
        "claim_register": {},
        "scope_quantifier": {},
        "provenance_integrity": {},
        "admission_use": {},
        "argument_leg": {},
        "warrant_logic": {},
        "modal_consistency": {},
        "grounding_citation": {},
        "d_style": {},
        "reader_accessibility": {},
        "active_overlays": {},
    }
    for case in cases:
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
        "obligation_registry": registry_binding,
        "obligations": obligations_ or [],
    }


def _base_evaluation(
    project: Path,
    prepared: dict[str, Any],
    register: Path,
    envelope: Path,
    criteria: Path,
    profile: Path,
    evaluation_id: str,
) -> dict[str, Any]:
    artifact_binding = _binding(project, prepared["artifact"])
    check_ids = [row["check_id"] for row in json.loads(profile.read_text(encoding="utf-8"))["checks"]]
    return {
        "schema_version": "1.0.0",
        "evaluation_id": evaluation_id,
        "artifact": artifact_binding,
        "generator_envelope": _binding(project, envelope),
        "evaluation_dispatch": {
            "claim": _binding(project, prepared["evaluator_path"]),
            "consumer_transaction_id": f"scholarly-evaluation:{evaluation_id}",
        },
        "claim_register": _binding(project, register),
        "milestone_criteria": _binding(project, criteria),
        "scholarly_profile": _binding(project, profile),
        "findings": [],
        "omitted_checks": [],
        "obligation_results": [],
        "dispatch_separation": {
            "generator_claim_id": prepared["generation_claim"]["claim_id"],
            "evaluator_claim_id": prepared["evaluator_claim"]["claim_id"],
            "separate": True,
            "independence_level": "dispatch_separation",
        },
        "verdict": {
            "status": "qualified",
            "check_results": [
                {
                    "check_id": check_id,
                    "status": "pass",
                    "evidence": [artifact_binding],
                    "reasoning": "The independent synthetic Evaluator recorded a bounded pass.",
                }
                for check_id in check_ids
            ],
        },
        "created_at": "2026-07-26T00:00:04Z",
    }


def _publish_evaluation(
    project: Path,
    prepared: dict[str, Any],
    value: dict[str, Any],
    path: Path,
) -> Path:
    """Write final bytes, then consume the public dispatch over manuscript+product."""

    _write_json(path, value)
    relative = path.relative_to(project).as_posix()
    _append_mutation(
        project,
        receipt_id=prepared["receipt_id"],
        reservation_id=prepared["reservation_id"],
        target=relative,
        preimage={"exists": False, "sha256": None, "size": 0},
    )
    _, consumption, _ = dispatch.consume_dispatch_claim(
        project,
        prepared["evaluator_path"],
        role="evaluator",
        consumer_transaction_id=value["evaluation_dispatch"]["consumer_transaction_id"],
        target_paths=[prepared["artifact_relative"], relative],
        consumed_at="2026-07-26T00:00:03Z",
    )
    return consumption


def _coherent_evaluation_variant(
    project: Path, evaluation_path: Path
) -> dict[Path, tuple[bytes, bytes]]:
    """Build a complete A/B replacement for one committed evaluation lane."""

    original_evaluation = evaluation_path.read_bytes()
    evaluation_value = json.loads(original_evaluation.decode("utf-8", errors="strict"))
    old_transaction = evaluation_value["evaluation_dispatch"]["consumer_transaction_id"]
    evaluation_value["evaluation_id"] = "SET-PROBE-B"
    evaluation_value["evaluation_dispatch"]["consumer_transaction_id"] = (
        "scholarly-evaluation:SET-PROBE-B"
    )
    replacement_evaluation = (
        json.dumps(evaluation_value, indent=2, sort_keys=True, ensure_ascii=False)
        + " \n"
    ).encode("utf-8")

    consumption_matches: list[Path] = []
    consumption_root = project / "reviews/.harness/assignment/dispatch/consumptions"
    for path in consumption_root.glob("*/consumption.json"):
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("consumer_transaction_id") == old_transaction:
            consumption_matches.append(path)
    if len(consumption_matches) != 1:
        raise AssertionError("coherent replacement requires one evaluation consumption")
    consumption_path = consumption_matches[0]
    publication_path = consumption_path.parent / "publication_manifest.json"
    marker_path = consumption_path.parent / "commit_marker.json"
    original_consumption = consumption_path.read_bytes()
    original_publication = publication_path.read_bytes()
    original_marker = marker_path.read_bytes()

    consumption_value = json.loads(original_consumption.decode("utf-8", errors="strict"))
    consumption_value["consumer_transaction_id"] = "scholarly-evaluation:SET-PROBE-B"
    evaluation_relative = evaluation_path.relative_to(project).as_posix()
    product = next(
        row for row in consumption_value["postimages"]
        if row["path"] == evaluation_relative
    )
    product["sha256"] = _sha_bytes(replacement_evaluation)
    product["size"] = len(replacement_evaluation)
    replacement_consumption = dispatch._json_bytes(consumption_value)

    publication_value = json.loads(original_publication.decode("utf-8", errors="strict"))
    publication_value["products"][0]["sha256"] = _sha_bytes(replacement_consumption)
    replacement_publication = dispatch._json_bytes(publication_value)
    marker_value = json.loads(original_marker.decode("utf-8", errors="strict"))
    marker_value["publication_manifest_sha256"] = _sha_bytes(replacement_publication)
    replacement_marker = dispatch._json_bytes(marker_value)
    return {
        evaluation_path: (original_evaluation, replacement_evaluation),
        consumption_path: (original_consumption, replacement_consumption),
        publication_path: (original_publication, replacement_publication),
        marker_path: (original_marker, replacement_marker),
    }


def _install_variant(images: dict[Path, tuple[bytes, bytes]], index: int) -> None:
    for path, pair in images.items():
        path.write_bytes(pair[index])


def _add_finding(value: dict[str, Any], finding: dict[str, Any], artifact: Path, register_value: dict[str, Any]) -> None:
    row = copy.deepcopy(finding)
    row["span"] = _span(artifact, register_value["claims"][0]["text"])
    row["current_fingerprint"] = evaluation.finding_fingerprint(
        artifact_sha256=value["artifact"]["sha256"],
        claim_register_sha256=value["claim_register"]["sha256"],
        finding=row,
    )
    value["findings"].append(row)
    owner = next(
        check["check_id"]
        for check in json.loads((Path(value["_profile_path"])).read_text(encoding="utf-8"))["checks"]
        if row["code"] in check["finding_severity_floor"]
    )
    value["verdict"]["check_results"] = [
        result for result in value["verdict"]["check_results"] if result["check_id"] != owner
    ]
    value["verdict"]["status"] = "blocked"


def _generator_envelope(project: Path, prepared: dict[str, Any], path: Path) -> None:
    _write_json(
        path,
        {
            "schema_version": "1.0.0",
            "envelope_type": "generator_envelope",
            "dispatch_id": prepared["generation_claim"]["claim_id"],
            "role": "generator",
            "artifact": _binding(project, prepared["artifact"]),
        },
    )


def _run(project: Path, artifact: Path, register: Path, evaluation_path: Path) -> tuple[int, dict[str, Any]]:
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--project-root",
            str(project),
            "--artifact",
            str(artifact),
            "--claim-register",
            str(register),
            "--evaluation",
            str(evaluation_path),
        ],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    try:
        return completed.returncode, json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"non-JSON output: {completed.stdout!r} stderr={completed.stderr!r}") from exc


def _expect(run: tuple[int, dict[str, Any]], *, rc: int, codes: set[str], label: str, failures: list[str]) -> None:
    actual_codes = {row.get("code") for row in run[1].get("findings", [])}
    if run[0] != rc or actual_codes != codes:
        failures.append(f"{label}: rc={run[0]} codes={sorted(str(x) for x in actual_codes)} expected rc={rc} codes={sorted(codes)}")


def _obligation_result(
    project: Path,
    prepared: dict[str, Any],
    *,
    outcome: str,
) -> tuple[Path, Path]:
    """Create a production-verifiable C4 result with assignment-dispatch authority."""

    lane = prepared["artifact"].parent
    policy = lane / f"obligation-policy-{outcome}.json"
    _write_json(policy, {"schema_version": "1.0.0", "policy": "synthetic-only"})
    artifact_binding = _binding(project, prepared["artifact"])
    policy_binding = _binding(project, policy)
    findings: list[dict[str, Any]] = []
    if outcome == "findings":
        fingerprint = obligations.finding_fingerprint(
            "grounding-protocol",
            "SYNTHETIC-OBLIGATION-MAJOR",
            "MAJOR",
            "synthetic-current-evidence",
            artifact_binding["sha256"],
        )
        findings = [
            {
                "code": "SYNTHETIC-OBLIGATION-MAJOR",
                "severity": "MAJOR",
                "evidence_identity": "synthetic-current-evidence",
                "fingerprint": fingerprint,
                "disposition": "open",
            }
        ]
    report = lane / f"obligation-report-{outcome}.json"
    report_value = {
        "schema_version": "1.0.0",
        "report_type": "obligation_adapter_report",
        "adapter_id": "grounding-protocol-result",
        "adapter_version": "1.0.0",
        "obligation_id": "grounding-protocol",
        "artifact": artifact_binding,
        "policy": policy_binding,
        "activation": "always",
        "execution_status": "completed",
        "outcome": outcome,
        "findings": findings,
        "diagnostic_only": False,
        "created_at": "2026-07-26T00:00:03Z",
    }
    _write_json(report, report_value)
    report_relative = report.relative_to(project).as_posix()
    _append_mutation(
        project,
        receipt_id=prepared["receipt_id"],
        reservation_id=prepared["reservation_id"],
        target=report_relative,
        preimage={"exists": False, "sha256": None, "size": 0},
    )
    consumption = _consume_evaluator(project, prepared, [report_relative])
    receipt = lane / f"obligation-authority-{outcome}.json"
    _write_json(
        receipt,
        {
            "schema_version": "1.0.0",
            "receipt_type": "obligation_verifier_authority",
            "authority_mode": "assignment_dispatch",
            "authority": "independent-evaluator",
            "subject": _binding(project, report),
            "claim": _binding(project, prepared["evaluator_path"]),
            "consumption": _binding(project, consumption),
        },
    )
    result = lane / f"obligation-result-{outcome}.json"
    result_value = {
        "schema_version": "1.0.0",
        "obligation_id": "grounding-protocol",
        "adapter_version": "1.0.0",
        "artifact": artifact_binding,
        "policy": policy_binding,
        "report": _binding(project, report),
        "verifier_receipt": _binding(project, receipt),
        "activation": "always",
        "execution_status": "completed",
        "outcome": outcome,
        "findings": findings,
        "diagnostic_only": False,
        "created_at": "2026-07-26T00:00:03Z",
        "adjudications": [],
    }
    _write_json(result, result_value)
    return result, consumption


def _native_dstyle_result(
    project: Path, prepared: dict[str, Any], *, label: str
) -> Path:
    """Create a package-native D-STYLE result from current synthetic bytes."""

    lane = prepared["artifact"].parent
    policy = lane / f"dstyle-policy-{label}.json"
    _write_json(policy, {"schema_version": "1.0.0", "policy": "synthetic-only"})
    artifact_binding = _binding(project, prepared["artifact"])
    report_value = dstyle.build_report(
        project,
        project / "research_notes/directives.md",
        prepared["artifact"],
    )
    report = lane / f"dstyle-report-{label}.json"
    _write_json(report, report_value)
    findings: list[dict[str, Any]] = []
    for observed in report_value["findings"]:
        severity = observed["severity"]
        if severity not in {"BLOCKER", "MAJOR", "MINOR", "ADVISORY"}:
            continue
        evidence_identity = _sha_bytes(
            _canonical(
                {
                    "field": observed.get("field"),
                    "locator": observed.get("locator"),
                    "message": observed.get("message"),
                }
            )
        )
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
    result = lane / f"dstyle-result-{label}.json"
    _write_json(
        result,
        {
            "schema_version": "1.0.0",
            "obligation_id": "d-style-profile",
            "adapter_version": "1.0.0",
            "artifact": artifact_binding,
            "policy": _binding(project, policy),
            "report": _binding(project, report),
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


def _native_dstyle_evaluation(
    project: Path,
    *,
    cases: list[dict[str, Any]],
    criteria: Path,
    registry: Path,
    label: str,
) -> tuple[Path, Path, dict[str, Any]]:
    """Publish one native D-STYLE evaluation over a synthetic artifact."""

    text = (
        "This paper argues a bounded claim because evidence supports the warrant "
        "and explains the stakes. However, a limitation defines the scope and an "
        "alternative explanation. AI-assisted work is disclosed."
    )
    prepared = _prepare_dispatch(
        project,
        artifact_relative=f"dstyle/{label}.md",
        text=text,
        label=f"dstyle-{label}",
    )
    lane = prepared["artifact"].parent
    envelope = lane / f"{label}-generator-envelope.json"
    _generator_envelope(project, prepared, envelope)
    source_a = lane / f"{label}-source-a.txt"
    source_b = lane / f"{label}-source-b.txt"
    source_a.write_text("Synthetic Source A.\n", encoding="utf-8", newline="\n")
    source_b.write_text("Synthetic Source B.\n", encoding="utf-8", newline="\n")
    register = lane / f"{label}-claim-register.json"
    _write_json(
        register,
        _claim_register(
            prepared["artifact"],
            register,
            text,
            {
                "viewpoint": "author_analysis",
                "provenance": "author_derivation",
                "admission_use": "derivation_only",
                "argument_leg": "composition",
                "modal_force": "qualified",
                "warrant_relation": "candidate",
            },
            prepared["evaluator_claim"]["claim_id"],
            (source_a, source_b),
        ),
    )
    profile = project / f"policy/dstyle-profile-{label}.json"
    _write_json(
        profile,
        _profile(cases, _binding(project, registry), ["d-style-profile"]),
    )
    result = _native_dstyle_result(project, prepared, label=label)
    value = _base_evaluation(
        project,
        prepared,
        register,
        envelope,
        criteria,
        profile,
        f"SET-DSTYLE-{label.upper()}",
    )
    value["obligation_results"] = [
        {"result": _binding(project, result), "adjudications": []}
    ]
    evaluation_path = lane / f"{label}-evaluation.json"
    _publish_evaluation(project, prepared, value, evaluation_path)
    return prepared["artifact"], evaluation_path, value


def _resolved_obligation_result(
    project: Path, prepared: dict[str, Any]
) -> tuple[Path, set[Path]]:
    """Create one production-authorized resolved MAJOR with nested evidence."""

    result_path, _ = _obligation_result(
        project, prepared, outcome="findings"
    )
    result = json.loads(result_path.read_text(encoding="utf-8"))
    finding = result["findings"][0]
    adjudicator = _additional_evaluator(
        project, prepared, "resolved-obligation-adjudicator"
    )
    adjudication = {
        "schema_version": "1.0.0",
        "adjudication_id": "synthetic-grounding-resolution",
        "obligation_id": result["obligation_id"],
        "finding_fingerprint": finding["fingerprint"],
        "artifact": result["artifact"],
        "disposition": "resolved",
        "authority": "independent-evaluator",
        "rationale": "The exact synthetic finding fingerprint was independently resolved.",
        "resolution_verification": {
            "artifact_sha256": result["artifact"]["sha256"],
            "artifact_byte_length": result["artifact"]["byte_length"],
            "finding_fingerprint": finding["fingerprint"],
            "verified": True,
        },
        "created_at": "2026-07-26T00:00:04Z",
    }
    subject = result_path.parent / "obligation-adjudication-subject.json"
    subject_value = {
        "schema_version": "1.0.0",
        "subject_type": "obligation_adjudication_authorization",
        "authority": adjudication["authority"],
        "adjudication_payload_sha256": _sha_bytes(_canonical(adjudication)),
        "obligation_id": result["obligation_id"],
        "finding_fingerprint": finding["fingerprint"],
        "artifact": result["artifact"],
    }
    _write_json(subject, subject_value)
    subject_relative = subject.relative_to(project).as_posix()
    _append_mutation(
        project,
        receipt_id=adjudicator["receipt_id"],
        reservation_id=adjudicator["reservation_id"],
        target=subject_relative,
        preimage={"exists": False, "sha256": None, "size": 0},
    )
    consumption = _consume_evaluator(project, adjudicator, [subject_relative])
    authority_receipt = result_path.parent / "obligation-adjudication-authority.json"
    _write_json(
        authority_receipt,
        {
            "schema_version": "1.0.0",
            "receipt_type": "obligation_adjudication_authority",
            "authority_mode": "assignment_dispatch",
            "authority": adjudication["authority"],
            "subject": _binding(project, subject),
            "claim": _binding(project, adjudicator["evaluator_path"]),
            "consumption": _binding(project, consumption),
        },
    )
    adjudication["authority_receipt"] = _binding(project, authority_receipt)
    result["adjudications"] = [adjudication]
    _write_json(result_path, result)
    return result_path, {subject, consumption, authority_receipt, result_path}


def main() -> int:
    fixture = json.loads(CASES.read_text(encoding="utf-8"))
    cases = fixture["cases"]
    assert fixture["provenance"]["live_research_material"] is False
    assert len(cases) == 7
    assert len({case["id"] for case in cases}) == 7
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    schema_validator = Draft202012Validator(schema, format_checker=FormatChecker())
    failures: list[str] = []
    semantic_pairs = 0
    attack_cases = 0
    api_cases = 0
    missing_c6 = {"claim_register", "admission_use", "warrant_logic", "grounding_citation"} - set(
        evaluation.PROFILE_MINIMUM
    )
    if missing_c6:
        failures.append(f"c6-quality-kernel-missing: {sorted(missing_c6)}")
    else:
        api_cases += 1

    # No workspace routing manifest in this install. A dummy extra governed
    # root makes OS temp projects classify as external, not DEST-UNGOVERNED.
    dummy_governed = Path(tempfile.mkdtemp(prefix="c6-dummy-governed-"))
    extra_roots = [
        item
        for item in os.environ.get("COAUTHOR_EXTRA_GOVERNED_ROOTS", "").split(os.pathsep)
        if item
    ]
    extra_roots.append(str(dummy_governed))
    os.environ["COAUTHOR_EXTRA_GOVERNED_ROOTS"] = os.pathsep.join(extra_roots)

    with tempfile.TemporaryDirectory(prefix="scholarly-evaluation-c6-") as td:
        project = Path(td) / "synthetic-project"
        project.mkdir()
        dest_safe_stamp = project / "dest-safe-info-stamp.json"
        _write_json(
            dest_safe_stamp,
            {
                "schema_version": "1.0.0",
                "evaluation_id": "dest-safe-impersonation",
                "execution_status": "completed",
                "outcome": "findings",
                "findings": [
                    {
                        "finding_id": "grounding-protocol-evaluation-lane-fired",
                        "severity": "INFO",
                        "message": "fired; requires evaluator dispatch for full check",
                    }
                ],
            },
        )
        import assignment_process_gate as process_gate

        def _process_gate_must_not_run(*_args: object, **_kwargs: object) -> list:
            raise AssertionError(
                "scholarly_evaluation must not consult assignment_process_gate"
            )

        original_validate = process_gate.validate
        process_gate.validate = _process_gate_must_not_run  # type: ignore[method-assign]
        try:
            evaluation.validate_scholarly_evaluation_binding(
                project,
                dest_safe_stamp,
                {
                    "evidence_path": dest_safe_stamp.relative_to(project).as_posix(),
                    "evidence_sha256": _sha_bytes(dest_safe_stamp.read_bytes()),
                },
            )
        except evaluation.EvaluationRefusal:
            api_cases += 1
        except AssertionError as exc:
            failures.append(str(exc))
        else:
            failures.append(
                "dest-safe INFO stamp must not qualify as C6 scholarly evaluation"
            )
        finally:
            process_gate.validate = original_validate
        registry_copy = project / "policies/obligation-result-registry.json"
        registry_copy.parent.mkdir(parents=True)
        registry_copy.write_bytes(REGISTRY.read_bytes())
        criteria = project / "policy/milestone-criteria.json"
        _write_json(
            criteria,
            {
                "schema_version": "1.0.0",
                "milestone": "M1",
                "criteria": ["Synthetic claims remain bounded to their exact evidence."],
            },
        )
        profile_path = project / "policy/scholarly-profile.json"
        _write_json(profile_path, _profile(cases, _binding(project, registry_copy)))

        saved_clean: tuple[dict[str, Any], Path, Path, Path, dict[str, Any], Path] | None = None
        saved_red: tuple[dict[str, Any], Path, Path, Path, dict[str, Any], Path] | None = None
        saved_cross_source: tuple[
            dict[str, Any], Path, Path, Path, dict[str, Any], Path, Path, Path
        ] | None = None
        for case_index, case in enumerate(cases):
            for kind in ("clean", "red"):
                text = case[f"{kind}_claim_text"]
                label = f"{case_index:02d}-{kind}"
                artifact_relative = f"cases/{case['id']}/{kind}.md"
                prepared = _prepare_dispatch(
                    project,
                    artifact_relative=artifact_relative,
                    text=text,
                    label=label,
                )
                lane = prepared["artifact"].parent
                envelope = lane / f"{kind}-generator-envelope.json"
                _generator_envelope(project, prepared, envelope)
                source_a = lane / "synthetic-source-a.txt"
                source_b = lane / "synthetic-source-b.txt"
                source_a.write_text("Synthetic Source A states a bounded observation.\n", encoding="utf-8", newline="\n")
                source_b.write_text("Synthetic Source B states a distinct bounded observation.\n", encoding="utf-8", newline="\n")
                register_path = lane / f"{kind}-claim-register.json"
                register_value = _claim_register(
                    prepared["artifact"],
                    register_path,
                    text,
                    case[f"{kind}_claim_profile"],
                    prepared["evaluator_claim"]["claim_id"],
                    (source_a, source_b),
                )
                _write_json(register_path, register_value)
                value = _base_evaluation(
                    project,
                    prepared,
                    register_path,
                    envelope,
                    criteria,
                    profile_path,
                    f"SET-{case_index:02d}-{kind.upper()}",
                )
                value["_profile_path"] = str(profile_path)
                if kind == "red":
                    _add_finding(
                        value,
                        case["red_change"]["value"],
                        prepared["artifact"],
                        register_value,
                    )
                del value["_profile_path"]
                errors = list(schema_validator.iter_errors(value))
                if errors:
                    failures.append(f"{case['id']}/{kind}: fixture schema failure: {errors[0].message}")
                    continue
                evaluation_path = lane / f"{kind}-evaluation.json"
                _publish_evaluation(project, prepared, value, evaluation_path)
                run = _run(project, prepared["artifact"], register_path, evaluation_path)
                if kind == "clean":
                    _expect(run, rc=0, codes=set(), label=f"{case['id']}/clean", failures=failures)
                    if case_index == 0:
                        saved_clean = (
                            value,
                            prepared["artifact"],
                            register_path,
                            evaluation_path,
                            prepared,
                            envelope,
                        )
                    if case_index == 5:
                        saved_cross_source = (
                            value,
                            prepared["artifact"],
                            register_path,
                            evaluation_path,
                            prepared,
                            envelope,
                            source_a,
                            source_b,
                        )
                else:
                    _expect(
                        run,
                        rc=1,
                        codes={"SET-FINDING-UNRESOLVED"},
                        label=f"{case['id']}/red",
                        failures=failures,
                    )
                    rows = run[1].get("findings", [])
                    if not any(
                        row.get("scholarly_code") == case["expected_scholarly_code"]
                        and row.get("current_fingerprint") == value["findings"][0]["current_fingerprint"]
                        for row in rows
                    ):
                        failures.append(f"{case['id']}/red: outer refusal did not bind code and fingerprint")
                    if case_index == 0:
                        saved_red = (
                            value,
                            prepared["artifact"],
                            register_path,
                            evaluation_path,
                            prepared,
                            envelope,
                        )
            semantic_pairs += 1

        assert saved_clean is not None and saved_red is not None and saved_cross_source is not None
        clean_value, clean_artifact, clean_register, clean_evaluation, clean_prepared, clean_envelope = saved_clean
        red_value, red_artifact, red_register, red_evaluation, red_prepared, red_envelope = saved_red
        attacks = project / "attacks"
        attacks.mkdir()

        (
            _,
            cross_artifact,
            _,
            cross_evaluation,
            _,
            _,
            cross_source_a,
            cross_source_b,
        ) = saved_cross_source
        cross_binding = {
            "evidence_path": cross_evaluation.relative_to(project).as_posix(),
            "evidence_sha256": _sha_bytes(cross_evaluation.read_bytes()),
        }
        cross_api = evaluation.validate_scholarly_evaluation_binding(
            project, cross_artifact, cross_binding
        )
        cross_dependency_paths = {
            row["path"] for row in cross_api["dependencies"]
        }
        expected_cross_dependencies = {
            str(cross_source_a.resolve()),
            str(cross_source_b.resolve()),
            str(evaluation.claim_register.SCHEMA_PATH.resolve()),
        }
        missing_cross_dependencies = sorted(
            expected_cross_dependencies - cross_dependency_paths
        )
        if missing_cross_dependencies:
            failures.append(
                "binding-api-cross-source-inventory: "
                f"missing={missing_cross_dependencies}"
            )
        api_cases += 1

        cross_source_original = cross_source_b.read_bytes()
        original_register_api = evaluation.claim_register.validate_register_with_dependencies

        def mutate_after_register_validation(*args: Any, **kwargs: Any) -> dict[str, Any]:
            result = original_register_api(*args, **kwargs)
            cross_source_b.write_bytes(cross_source_original + b" ")
            return result

        evaluation.claim_register.validate_register_with_dependencies = (
            mutate_after_register_validation
        )
        try:
            try:
                evaluation.validate_scholarly_evaluation_binding(
                    project, cross_artifact, cross_binding
                )
            except evaluation.EvaluationRefusal as exc:
                if exc.code != "SET-ARTIFACT-STALE":
                    failures.append(
                        "binding-api-cross-source-mutation: "
                        f"code={exc.code} expected=SET-ARTIFACT-STALE"
                    )
            else:
                failures.append(
                    "binding-api-cross-source-mutation: subordinate source change returned normally"
                )
        finally:
            evaluation.claim_register.validate_register_with_dependencies = (
                original_register_api
            )
            cross_source_b.write_bytes(cross_source_original)
        api_cases += 1

        def expect_api_refusal(
            label: str, binding: dict[str, Any], expected_code: str
        ) -> None:
            nonlocal api_cases
            try:
                evaluation.validate_scholarly_evaluation_binding(
                    project, clean_artifact, binding
                )
            except evaluation.EvaluationRefusal as exc:
                if exc.code != expected_code:
                    failures.append(
                        f"{label}: code={exc.code} expected={expected_code}"
                    )
            else:
                failures.append(f"{label}: controlled binding unexpectedly qualified")
            api_cases += 1

        clean_binding = {
            "evidence_path": clean_evaluation.relative_to(project).as_posix(),
            "evidence_sha256": _sha_bytes(clean_evaluation.read_bytes()),
        }
        api_result = evaluation.validate_scholarly_evaluation_binding(
            project, clean_artifact, clean_binding
        )
        if (
            api_result.get("binding") != clean_binding
            or api_result.get("artifact") != _binding(project, clean_artifact)
            or api_result.get("evaluation_id") != clean_value["evaluation_id"]
            or api_result.get("status") != "qualified"
            or api_result.get("judgment_truth_certified") is not False
        ):
            failures.append(f"binding-api-qualified: unexpected result {api_result!r}")
        legacy_result = evaluation.verify_evaluation(
            project, clean_artifact, clean_register, clean_evaluation
        )
        if "artifact" in legacy_result:
            failures.append(
                "legacy verify_evaluation result unexpectedly exposed artifact binding"
            )
        api_cases += 1

        stale_state = project / "reviews" / "phase_state.json"
        stale_state.parent.mkdir(parents=True, exist_ok=True)
        _write_json(
            stale_state,
            {
                "milestone_framework": {
                    "mode": "native",
                    "milestones": {
                        "M1": {"status": "in_progress"},
                        "M2": {"status": "not_started"},
                        "M3": {"status": "not_started"},
                        "M4": {"status": "not_started"},
                        "M5": {"status": "not_started"},
                    },
                }
            },
        )
        stale_c6 = evaluation.verify_evaluation(
            project, clean_artifact, clean_register, clean_evaluation
        )
        if stale_c6.get("status") not in {"qualified", "blocked"}:
            failures.append(
                "c6-stale-phase-state: scholarly evaluate must still run when "
                f"predecessors are not accepted: {stale_c6!r}"
            )
        else:
            api_cases += 1
        stale_binding = evaluation.validate_scholarly_evaluation_binding(
            project, clean_artifact, clean_binding
        )
        if stale_binding.get("status") != "qualified":
            failures.append(
                "c6-stale-phase-state-binding: C6 binding must not consult "
                f"assignment_process_gate sequence: {stale_binding!r}"
            )
        else:
            api_cases += 1

        red_binding = {
            "evidence_path": red_evaluation.relative_to(project).as_posix(),
            "evidence_sha256": _sha_bytes(red_evaluation.read_bytes()),
        }
        try:
            evaluation.validate_scholarly_evaluation_binding(
                project, red_artifact, red_binding
            )
        except evaluation.EvaluationRefusal as exc:
            blockers = exc.details.get("blockers")
            if (
                exc.code != "SET-FINDING-UNRESOLVED"
                or not isinstance(blockers, list)
                or not any(
                    row.get("current_fingerprint")
                    == red_value["findings"][0]["current_fingerprint"]
                    for row in blockers
                    if isinstance(row, dict)
                )
            ):
                failures.append(
                    "binding-api-unresolved-major: "
                    f"code={exc.code} blockers={blockers!r}"
                )
        else:
            failures.append(
                "binding-api-unresolved-major: authenticated blocker returned normally"
            )
        api_cases += 1

        coherent_variant = _coherent_evaluation_variant(project, clean_evaluation)
        try:
            _install_variant(coherent_variant, 1)
            coherent_b = _run(
                project, clean_artifact, clean_register, clean_evaluation
            )
        finally:
            _install_variant(coherent_variant, 0)
        if (
            coherent_b[0] != 0
            or coherent_b[1].get("evaluation_id") != "SET-PROBE-B"
            or coherent_b[1].get("status") != "qualified"
        ):
            failures.append(
                f"binding-api-coherent-replacement-control: B did not qualify {coherent_b!r}"
            )
        api_cases += 1

        original_transaction = evaluation._verify_evaluation_transaction

        def replace_a_with_b(*args: Any, **kwargs: Any) -> Any:
            _install_variant(coherent_variant, 1)
            return original_transaction(*args, **kwargs)

        evaluation._verify_evaluation_transaction = replace_a_with_b
        try:
            try:
                mismatched = evaluation.validate_scholarly_evaluation_binding(
                    project, clean_artifact, clean_binding
                )
            except evaluation.EvaluationRefusal as exc:
                if exc.code != "SET-ARTIFACT-STALE":
                    failures.append(
                        "binding-api-coherent-replacement-attack: "
                        f"code={exc.code} expected=SET-ARTIFACT-STALE"
                    )
            else:
                failures.append(
                    "binding-api-coherent-replacement-attack: mismatched A binding "
                    f"returned normally as {mismatched!r}"
                )
        finally:
            evaluation._verify_evaluation_transaction = original_transaction
            _install_variant(coherent_variant, 0)
        api_cases += 1

        dependency_rows = api_result.get("dependencies", [])
        dependency_by_path = {
            row.get("path"): row for row in dependency_rows if isinstance(row, dict)
        }
        if len(dependency_by_path) != len(dependency_rows):
            failures.append("binding-api-inventory: dependency paths are not unique")
        assignment_root = project / "reviews/.harness/assignment"
        expected_assignment_files = {
            str(path.resolve())
            for path in assignment_root.rglob("*")
            if path.is_file() and not path.is_symlink()
        }
        explicit_files = {
            clean_evaluation,
            clean_artifact,
            clean_register,
            clean_envelope,
            criteria,
            profile_path,
            registry_copy,
            clean_prepared["evaluator_path"],
            clean_prepared["generation_path"],
            *evaluation.STATIC_DEPENDENCY_PATHS,
        }
        expected_paths = expected_assignment_files | {
            str(path.resolve()) for path in explicit_files
        }
        missing_dependencies = sorted(expected_paths - set(dependency_by_path))
        stale_dependencies = sorted(
            path
            for path, row in dependency_by_path.items()
            if not isinstance(path, str)
            or not Path(path).is_file()
            or row.get("sha256") != _sha_bytes(Path(path).read_bytes())
            or row.get("byte_length") != Path(path).stat().st_size
        )
        if missing_dependencies or stale_dependencies:
            failures.append(
                "binding-api-inventory: "
                f"missing={missing_dependencies} stale={stale_dependencies}"
            )
        api_cases += 1

        directives = project / "research_notes/directives.md"
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
        assistance_paths = (
            project / "research_notes/assistance_log.md",
            project / "research_notes/disclosure.md",
            project / "reviews/assistance_log.md",
        )

        absent_artifact, absent_evaluation, _ = _native_dstyle_evaluation(
            project,
            cases=cases,
            criteria=criteria,
            registry=registry_copy,
            label="assistance-absent",
        )
        absent_binding = {
            "evidence_path": absent_evaluation.relative_to(project).as_posix(),
            "evidence_sha256": _sha_bytes(absent_evaluation.read_bytes()),
        }
        absent_api = evaluation.validate_scholarly_evaluation_binding(
            project, absent_artifact, absent_binding
        )
        if absent_api.get("artifact") != _binding(project, absent_artifact):
            failures.append(
                "binding-api-dstyle-absent-artifact: normalized artifact mismatch"
            )
        absent_dependency_paths = {
            row["path"] for row in absent_api.get("dependencies", [])
        }
        unexpected_absent_dependencies = sorted(
            str(path.resolve())
            for path in assistance_paths
            if str(path.resolve()) in absent_dependency_paths
        )
        if unexpected_absent_dependencies:
            failures.append(
                "binding-api-dstyle-absent-inventory: unexpectedly bound "
                f"{unexpected_absent_dependencies}"
            )
        api_cases += 1

        def expect_dstyle_transition_refusal(
            label: str,
            artifact: Path,
            binding: dict[str, Any],
            mutate: Any,
            restore: Any,
        ) -> None:
            nonlocal api_cases
            original_verify = evaluation.obligations.verify_obligation_result
            mutated = False

            def mutate_after_dstyle(*args: Any, **kwargs: Any) -> dict[str, Any]:
                nonlocal mutated
                verified = original_verify(*args, **kwargs)
                if not mutated:
                    mutate()
                    mutated = True
                return verified

            evaluation.obligations.verify_obligation_result = mutate_after_dstyle
            try:
                try:
                    evaluation.validate_scholarly_evaluation_binding(
                        project, artifact, binding
                    )
                except evaluation.EvaluationRefusal as exc:
                    if exc.code != "SET-ARTIFACT-STALE":
                        failures.append(
                            f"{label}: code={exc.code} expected=SET-ARTIFACT-STALE"
                        )
                else:
                    failures.append(f"{label}: transition returned normally")
            finally:
                evaluation.obligations.verify_obligation_result = original_verify
                restore()
            api_cases += 1

        for assistance_path in assistance_paths:
            def create_absent(path: Path = assistance_path) -> None:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    "Synthetic assistance record created during verification.\n",
                    encoding="utf-8",
                    newline="\n",
                )

            expect_dstyle_transition_refusal(
                f"binding-api-dstyle-absent-created-{assistance_path.parent.name}-{assistance_path.name}",
                absent_artifact,
                absent_binding,
                create_absent,
                lambda path=assistance_path: path.unlink(missing_ok=True),
            )

        assistance_payloads: dict[Path, bytes] = {}
        for index, assistance_path in enumerate(assistance_paths, start=1):
            payload = f"Synthetic assistance record {index}.\n".encode("utf-8")
            assistance_path.parent.mkdir(parents=True, exist_ok=True)
            assistance_path.write_bytes(payload)
            assistance_payloads[assistance_path] = payload

        present_artifact, present_evaluation, _ = _native_dstyle_evaluation(
            project,
            cases=cases,
            criteria=criteria,
            registry=registry_copy,
            label="assistance-present",
        )
        present_binding = {
            "evidence_path": present_evaluation.relative_to(project).as_posix(),
            "evidence_sha256": _sha_bytes(present_evaluation.read_bytes()),
        }
        present_api = evaluation.validate_scholarly_evaluation_binding(
            project, present_artifact, present_binding
        )
        if present_api.get("artifact") != _binding(project, present_artifact):
            failures.append(
                "binding-api-dstyle-present-artifact: normalized artifact mismatch"
            )
        present_dependencies = {
            row["path"]: row for row in present_api.get("dependencies", [])
        }
        for assistance_path, payload in assistance_payloads.items():
            dependency = present_dependencies.get(str(assistance_path.resolve()))
            expected_dependency = {
                "path": str(assistance_path.resolve()),
                "sha256": _sha_bytes(payload),
                "byte_length": len(payload),
            }
            if dependency != expected_dependency:
                failures.append(
                    "binding-api-dstyle-present-inventory: "
                    f"path={assistance_path} observed={dependency!r} "
                    f"expected={expected_dependency!r}"
                )
        api_cases += 1

        for assistance_path, payload in assistance_payloads.items():
            restore = lambda path=assistance_path, raw=payload: path.write_bytes(raw)
            expect_dstyle_transition_refusal(
                f"binding-api-dstyle-present-removed-{assistance_path.parent.name}-{assistance_path.name}",
                present_artifact,
                present_binding,
                lambda path=assistance_path: path.unlink(),
                restore,
            )
            expect_dstyle_transition_refusal(
                f"binding-api-dstyle-present-mutated-{assistance_path.parent.name}-{assistance_path.name}",
                present_artifact,
                present_binding,
                lambda path=assistance_path, raw=payload: path.write_bytes(raw + b" "),
                restore,
            )

        expect_api_refusal(
            "binding-api-missing",
            {
                "evidence_path": "reviews/.harness/missing-evaluation.json",
                "evidence_sha256": "0" * 64,
            },
            "SET-BINDING-MISSING",
        )
        expect_api_refusal(
            "binding-api-stale",
            {**clean_binding, "evidence_sha256": "0" * 64},
            "SET-ARTIFACT-STALE",
        )
        expect_api_refusal(
            "binding-api-unsafe",
            {
                "evidence_path": "../copied-evaluation.json",
                "evidence_sha256": clean_binding["evidence_sha256"],
            },
            "SET-SCHEMA",
        )

        copied_evaluation = attacks / "copied-evaluation.json"
        copied_evaluation.write_bytes(clean_evaluation.read_bytes())
        expect_api_refusal(
            "binding-api-copy-path",
            {
                "evidence_path": copied_evaluation.relative_to(project).as_posix(),
                "evidence_sha256": _sha_bytes(copied_evaluation.read_bytes()),
            },
            "SET-DISPATCH-SEPARATION",
        )

        duplicate_evaluation = attacks / "duplicate-binding-evaluation.json"
        duplicate_bytes = clean_evaluation.read_bytes().replace(
            b"{", b'{"schema_version":"1.0.0",', 1
        )
        duplicate_evaluation.write_bytes(duplicate_bytes)
        expect_api_refusal(
            "binding-api-duplicate-json",
            {
                "evidence_path": duplicate_evaluation.relative_to(project).as_posix(),
                "evidence_sha256": _sha_bytes(duplicate_bytes),
            },
            "SET-SCHEMA",
        )

        criteria_bytes = criteria.read_bytes()
        criteria.write_bytes(criteria_bytes + b" ")
        expect_api_refusal(
            "binding-api-nested-dependency-mutation",
            clean_binding,
            "SET-ARTIFACT-STALE",
        )
        criteria.write_bytes(criteria_bytes)

        def authenticated_attack(
            label: str,
            template: dict[str, Any],
            artifact: Path,
            register: Path,
            prepared: dict[str, Any],
            mutate: Any,
            code: str,
        ) -> tuple[dict[str, Any], Path, Path, dict[str, Any]]:
            nonlocal attack_cases
            current = _additional_evaluator(project, prepared, f"attack-{label}")
            register_value = json.loads(register.read_text(encoding="utf-8"))
            register_value["review_dispatch"] = {
                "dispatch_id": current["evaluator_claim"]["claim_id"],
                "role": "evaluator",
            }
            current_register = register.parent / f"attack-{label}-claim-register.json"
            _write_json(current_register, register_value)
            value = copy.deepcopy(template)
            value["evaluation_id"] = f"SET-ATTACK-{label}"
            value["claim_register"] = _binding(project, current_register)
            value["evaluation_dispatch"] = {
                "claim": _binding(project, current["evaluator_path"]),
                "consumer_transaction_id": f"scholarly-evaluation:SET-ATTACK-{label}",
            }
            value["dispatch_separation"]["evaluator_claim_id"] = current["evaluator_claim"]["claim_id"]
            for finding in value["findings"]:
                finding["current_fingerprint"] = evaluation.finding_fingerprint(
                    artifact_sha256=value["artifact"]["sha256"],
                    claim_register_sha256=value["claim_register"]["sha256"],
                    finding=finding,
                )
            path = attacks / f"{label}.json"
            mutate(value, current_register, current, path)
            _publish_evaluation(project, current, value, path)
            _expect(
                _run(project, artifact, current_register, path),
                rc=1,
                codes={code},
                label=label,
                failures=failures,
            )
            attack_cases += 1
            return value, path, current_register, current

        authenticated_attack("forged-separation", clean_value, clean_artifact, clean_register, clean_prepared, lambda value, *_: value["dispatch_separation"].update({"generator_claim_id": "dispatch-0000000000000000"}), "SET-DISPATCH-SEPARATION")
        authenticated_attack("forged-dispatch", clean_value, clean_artifact, clean_register, clean_prepared, lambda value, *_: value["evaluation_dispatch"].update({"claim": value["generator_envelope"]}), "SET-DISPATCH-SEPARATION")

        def forbidden_omission(value: dict[str, Any], *_: Any) -> None:
            value["verdict"]["check_results"] = value["verdict"]["check_results"][1:]
            value["omitted_checks"] = [{"check_id": "milestone_criteria", "omission_code": "source_unavailable", "rationale": "Synthetic forbidden omission.", "evidence": [value["artifact"]]}]

        authenticated_attack("forbidden-omission", clean_value, clean_artifact, clean_register, clean_prepared, forbidden_omission, "SET-OMITTED-CHECK-INVALID")
        authenticated_attack("omitted-without-record", clean_value, clean_artifact, clean_register, clean_prepared, lambda value, *_: value["verdict"].update({"check_results": value["verdict"]["check_results"][1:]}), "SET-COVERAGE-INCOMPLETE")
        authenticated_attack("finding-fingerprint", red_value, red_artifact, red_register, red_prepared, lambda value, *_: value["findings"][0].update({"current_fingerprint": "0" * 64}), "SET-ARTIFACT-STALE")

        def severity_downgrade(value: dict[str, Any], *_: Any) -> None:
            value["findings"][0]["severity"] = "MINOR"
            value["findings"][0]["current_fingerprint"] = evaluation.finding_fingerprint(
                artifact_sha256=value["artifact"]["sha256"],
                claim_register_sha256=value["claim_register"]["sha256"],
                finding=value["findings"][0],
            )
            value["verdict"]["status"] = "qualified"

        authenticated_attack("severity-downgrade", red_value, red_artifact, red_register, red_prepared, severity_downgrade, "SET-SCHEMA")

        schema_abuse = copy.deepcopy(clean_value)
        schema_abuse["self_declared_truth"] = True
        path = attacks / "schema-extra-field.json"
        _write_json(path, schema_abuse)
        _expect(_run(project, clean_artifact, clean_register, path), rc=1, codes={"SET-SCHEMA"}, label="schema-extra-field", failures=failures)
        attack_cases += 1

        duplicate_path = attacks / "duplicate-json-key.json"
        duplicate_raw = json.dumps(clean_value, sort_keys=True)
        duplicate_raw = duplicate_raw.replace(
            '"schema_version": "1.0.0"',
            '"schema_version": "1.0.0", "schema_version": "1.0.0"',
            1,
        )
        duplicate_path.write_text(duplicate_raw, encoding="utf-8", newline="\n")
        _expect(
            _run(project, clean_artifact, clean_register, duplicate_path),
            rc=1,
            codes={"SET-SCHEMA"},
            label="duplicate-json-key",
            failures=failures,
        )
        attack_cases += 1

        input_abuse = copy.deepcopy(clean_value)
        input_abuse["artifact"]["path"] = "../escape.md"
        path = attacks / "unsafe-input-path.json"
        _write_json(path, input_abuse)
        _expect(_run(project, clean_artifact, clean_register, path), rc=1, codes={"SET-SCHEMA"}, label="unsafe-input-path", failures=failures)
        attack_cases += 1

        def profile_attack(label: str, transform: Any, expected: str) -> None:
            def mutate(value: dict[str, Any], _register: Path, _prepared: dict[str, Any], evaluation_path: Path) -> None:
                profile_value = json.loads(profile_path.read_text(encoding="utf-8"))
                transform(profile_value, value)
                candidate = evaluation_path.with_name(f"{label}-profile.json")
                _write_json(candidate, profile_value)
                value["scholarly_profile"] = _binding(project, candidate)

            authenticated_attack(
                label,
                clean_value,
                clean_artifact,
                clean_register,
                clean_prepared,
                mutate,
                expected,
            )

        def arbitrary_profile(profile_value: dict[str, Any], value: dict[str, Any]) -> None:
            profile_value["profile_id"] = "arbitrary-one-check"
            profile_value["checks"] = [{"check_id": "invented_check", "allowed_omission_codes": [], "finding_severity_floor": {}}]
            value["verdict"]["check_results"] = [{"check_id": "invented_check", "status": "pass", "evidence": [value["artifact"]], "reasoning": "Invented fixture pass."}]

        profile_attack("profile-arbitrary-one-check", arbitrary_profile, "SET-SCHEMA")
        profile_attack("profile-missing-check", lambda profile_value, _value: profile_value.update({"checks": profile_value["checks"][1:]}), "SET-COVERAGE-INCOMPLETE")

        def renamed_profile(profile_value: dict[str, Any], value: dict[str, Any]) -> None:
            old = profile_value["checks"][0]["check_id"]
            profile_value["checks"][0]["check_id"] = "renamed_milestone_check"
            for row in value["verdict"]["check_results"]:
                if row["check_id"] == old:
                    row["check_id"] = "renamed_milestone_check"

        profile_attack("profile-renamed-check", renamed_profile, "SET-COVERAGE-INCOMPLETE")

        def weakened_profile(profile_value: dict[str, Any], _value: dict[str, Any]) -> None:
            row = next(item for item in profile_value["checks"] if item["check_id"] == "provenance_integrity")
            row["finding_severity_floor"]["SCHOLARLY-CONSTRUCTED-SYNTHESIS-AS-DIRECT-SOURCE"] = "MINOR"

        profile_attack("profile-weakened-floor", weakened_profile, "SET-SCHEMA")

        def widened_profile(profile_value: dict[str, Any], _value: dict[str, Any]) -> None:
            row = next(item for item in profile_value["checks"] if item["check_id"] == "milestone_criteria")
            row["allowed_omission_codes"] = ["source_unavailable"]

        profile_attack("profile-widened-omission", widened_profile, "SET-OMITTED-CHECK-INVALID")

        reused = copy.deepcopy(clean_value)
        reused["evaluation_id"] = "SET-REUSED-CONSUMPTION"
        reused["evaluation_dispatch"]["consumer_transaction_id"] = "scholarly-evaluation:SET-REUSED-CONSUMPTION"
        reused_path = attacks / "reused-consumption-new-id.json"
        _write_json(reused_path, reused)
        _expect(
            _run(project, clean_artifact, clean_register, reused_path),
            rc=1,
            codes={"SET-DISPATCH-SEPARATION"},
            label="reused-consumption-new-id",
            failures=failures,
        )
        attack_cases += 1

        copied_path = attacks / "reused-consumption-new-path.json"
        copied_path.write_bytes(saved_clean[3].read_bytes())
        _expect(
            _run(project, clean_artifact, clean_register, copied_path),
            rc=1,
            codes={"SET-DISPATCH-SEPARATION"},
            label="reused-consumption-new-path",
            failures=failures,
        )
        attack_cases += 1

        # Even byte-identical products with the same evaluation_id cannot share
        # one consumption: the product set must contain exactly one evaluation.
        twin_prepared = _additional_evaluator(
            project, clean_prepared, "twin-path-same-id"
        )
        twin_register_value = json.loads(clean_register.read_text(encoding="utf-8"))
        twin_register_value["review_dispatch"] = {
            "dispatch_id": twin_prepared["evaluator_claim"]["claim_id"],
            "role": "evaluator",
        }
        twin_register = clean_register.parent / "twin-path-claim-register.json"
        _write_json(twin_register, twin_register_value)
        twin_value = copy.deepcopy(clean_value)
        twin_value["evaluation_id"] = "SET-TWIN-PATH-SAME-ID"
        twin_value["claim_register"] = _binding(project, twin_register)
        twin_value["evaluation_dispatch"] = {
            "claim": _binding(project, twin_prepared["evaluator_path"]),
            "consumer_transaction_id": "scholarly-evaluation:SET-TWIN-PATH-SAME-ID",
        }
        twin_value["dispatch_separation"]["evaluator_claim_id"] = twin_prepared["evaluator_claim"]["claim_id"]
        twin_a = attacks / "twin-path-a.json"
        twin_b = attacks / "twin-path-b.json"
        _write_json(twin_a, twin_value)
        twin_b.write_bytes(twin_a.read_bytes())
        for twin_path in (twin_a, twin_b):
            relative = twin_path.relative_to(project).as_posix()
            _append_mutation(
                project,
                receipt_id=twin_prepared["receipt_id"],
                reservation_id=twin_prepared["reservation_id"],
                target=relative,
                preimage={"exists": False, "sha256": None, "size": 0},
            )
        dispatch.consume_dispatch_claim(
            project,
            twin_prepared["evaluator_path"],
            role="evaluator",
            consumer_transaction_id=twin_value["evaluation_dispatch"]["consumer_transaction_id"],
            target_paths=[
                twin_prepared["artifact_relative"],
                twin_a.relative_to(project).as_posix(),
                twin_b.relative_to(project).as_posix(),
            ],
            consumed_at="2026-07-26T00:00:03Z",
        )
        for label, twin_path in (
            ("twin-path-same-id-a", twin_a),
            ("twin-path-same-id-b", twin_b),
        ):
            _expect(
                _run(project, clean_artifact, twin_register, twin_path),
                rc=1,
                codes={"SET-DISPATCH-SEPARATION"},
                label=label,
                failures=failures,
            )
            attack_cases += 1

        def publish_identity_product(tag: str, evaluation_id: str) -> tuple[Path, Path]:
            candidate = _additional_evaluator(
                project, clean_prepared, f"identity-{tag}"
            )
            register_value = json.loads(clean_register.read_text(encoding="utf-8"))
            register_value["review_dispatch"] = {
                "dispatch_id": candidate["evaluator_claim"]["claim_id"],
                "role": "evaluator",
            }
            register_path = clean_register.parent / f"identity-{tag}-claim-register.json"
            _write_json(register_path, register_value)
            value = copy.deepcopy(clean_value)
            value["evaluation_id"] = evaluation_id
            value["claim_register"] = _binding(project, register_path)
            value["evaluation_dispatch"] = {
                "claim": _binding(project, candidate["evaluator_path"]),
                "consumer_transaction_id": f"scholarly-evaluation:{evaluation_id}",
            }
            value["dispatch_separation"]["evaluator_claim_id"] = candidate["evaluator_claim"]["claim_id"]
            path = attacks / f"identity-{tag}.json"
            _publish_evaluation(project, candidate, value, path)
            return path, register_path

        # Global identity collision: two legitimate claims cannot each publish
        # a product under the same evaluation transaction identity.
        collision_a, collision_register_a = publish_identity_product(
            "collision-a", "SET-CROSS-CLAIM-COLLISION"
        )
        collision_b, collision_register_b = publish_identity_product(
            "collision-b", "SET-CROSS-CLAIM-COLLISION"
        )
        for label, path, register_path in (
            ("cross-claim-same-id-a", collision_a, collision_register_a),
            ("cross-claim-same-id-b", collision_b, collision_register_b),
        ):
            _expect(
                _run(project, clean_artifact, register_path, path),
                rc=1,
                codes={"SET-DISPATCH-SEPARATION"},
                label=label,
                failures=failures,
            )
            attack_cases += 1

        distinct_a, distinct_register_a = publish_identity_product(
            "distinct-a", "SET-CROSS-CLAIM-DISTINCT-A"
        )
        distinct_b, distinct_register_b = publish_identity_product(
            "distinct-b", "SET-CROSS-CLAIM-DISTINCT-B"
        )
        for label, path, register_path in (
            ("cross-claim-distinct-id-a", distinct_a, distinct_register_a),
            ("cross-claim-distinct-id-b", distinct_b, distinct_register_b),
        ):
            _expect(
                _run(project, clean_artifact, register_path, path),
                rc=0,
                codes=set(),
                label=label,
                failures=failures,
            )
            attack_cases += 1

        # Stale bytes: copy an otherwise qualified transaction, then alter the
        # bound artifact.  Restore it immediately because later cases share it.
        original = clean_artifact.read_bytes()
        clean_artifact.write_bytes(original + b"stale")
        _expect(
            _run(project, clean_artifact, clean_register, saved_clean[3]),
            rc=1,
            codes={"SET-ARTIFACT-STALE"},
            label="stale-artifact-bytes",
            failures=failures,
        )
        clean_artifact.write_bytes(original)
        attack_cases += 1

        # C4 obligation integration: a clean authenticated result qualifies and
        # an authenticated current MAJOR result produces the outer blocker.
        obligation_profile = project / "policy/scholarly-profile-obligation.json"
        _write_json(
            obligation_profile,
            _profile(cases, _binding(project, registry_copy), ["grounding-protocol"]),
        )
        obligation_clean_context: tuple[Path, Path, Path, Path] | None = None
        for outcome in ("clean", "findings", "resolved"):
            label = f"obligation-{outcome}"
            prepared = _prepare_dispatch(
                project,
                artifact_relative=f"obligations/{outcome}.md",
                text="This synthetic obligation claim remains bounded.",
                label=label,
            )
            lane = prepared["artifact"].parent
            source_a = lane / "source-a.txt"
            source_b = lane / "source-b.txt"
            source_a.write_text("A\n", encoding="utf-8", newline="\n")
            source_b.write_text("B\n", encoding="utf-8", newline="\n")
            register_path = lane / "claim-register.json"
            register_value = _claim_register(
                prepared["artifact"],
                register_path,
                "This synthetic obligation claim remains bounded.",
                {"viewpoint": "author_analysis", "provenance": "author_derivation", "admission_use": "derivation_only", "argument_leg": "composition", "modal_force": "qualified", "warrant_relation": "candidate"},
                prepared["evaluator_claim"]["claim_id"],
                (source_a, source_b),
            )
            _write_json(register_path, register_value)
            authority_prepared = _additional_evaluator(
                project, prepared, f"{label}-obligation-authority"
            )
            nested_obligation_paths: set[Path] = set()
            if outcome == "resolved":
                result_path, nested_obligation_paths = _resolved_obligation_result(
                    project, authority_prepared
                )
            else:
                result_path, _ = _obligation_result(
                    project, authority_prepared, outcome=outcome
                )
            envelope = lane / "generator-envelope.json"
            _generator_envelope(project, prepared, envelope)
            value = _base_evaluation(
                project,
                prepared,
                register_path,
                envelope,
                criteria,
                obligation_profile,
                f"SET-OBLIGATION-{outcome.upper()}",
            )
            value["obligation_results"] = [{"result": _binding(project, result_path), "adjudications": []}]
            if outcome == "resolved":
                resolved_result = json.loads(result_path.read_text(encoding="utf-8"))
                resolved_adjudication = resolved_result["adjudications"][0]
                canonical_adjudication = _canonical(resolved_adjudication)
                value["obligation_results"][0]["adjudications"] = [
                    {
                        "adjudication_id": resolved_adjudication["adjudication_id"],
                        "canonical_sha256": _sha_bytes(canonical_adjudication),
                        "canonical_byte_length": len(canonical_adjudication),
                    }
                ]
            if outcome == "findings":
                value["verdict"]["status"] = "blocked"
            evaluation_path = lane / "evaluation.json"
            _publish_evaluation(project, prepared, value, evaluation_path)
            expected_codes = (
                {"SET-FINDING-UNRESOLVED"} if outcome == "findings" else set()
            )
            _expect(
                _run(project, prepared["artifact"], register_path, evaluation_path),
                rc=1 if outcome == "findings" else 0,
                codes=expected_codes,
                label=label,
                failures=failures,
            )
            if outcome == "clean":
                obligation_clean_context = (
                    prepared["artifact"],
                    register_path,
                    evaluation_path,
                    result_path,
                )
            if outcome == "resolved":
                resolved_api = evaluation.validate_scholarly_evaluation_binding(
                    project,
                    prepared["artifact"],
                    {
                        "evidence_path": evaluation_path.relative_to(project).as_posix(),
                        "evidence_sha256": _sha_bytes(evaluation_path.read_bytes()),
                    },
                )
                resolved_dependencies = {
                    row["path"] for row in resolved_api["dependencies"]
                }
                result_value = json.loads(result_path.read_text(encoding="utf-8"))
                report_path = project / result_value["report"]["path"]
                policy_path = project / result_value["policy"]["path"]
                expected_nested = {
                    str(path.resolve())
                    for path in nested_obligation_paths | {report_path, policy_path}
                }
                missing_nested = sorted(expected_nested - resolved_dependencies)
                if missing_nested or resolved_api.get("status") != "qualified":
                    failures.append(
                        "binding-api-obligation-inventory: "
                        f"missing={missing_nested} status={resolved_api.get('status')}"
                    )
                api_cases += 1
            if outcome != "resolved":
                attack_cases += 1

        # A resolved scholarly finding is replayable only while its exact
        # resolution document remains current.
        resolved_prepared = _additional_evaluator(
            project, red_prepared, "resolved-finding-control"
        )
        resolved_register_value = json.loads(red_register.read_text(encoding="utf-8"))
        resolved_register_value["review_dispatch"] = {
            "dispatch_id": resolved_prepared["evaluator_claim"]["claim_id"],
            "role": "evaluator",
        }
        resolved_register = red_register.parent / "resolved-claim-register.json"
        _write_json(resolved_register, resolved_register_value)
        resolved_value = copy.deepcopy(red_value)
        resolved_value["evaluation_id"] = "SET-RESOLVED-FINDING"
        resolved_value["claim_register"] = _binding(project, resolved_register)
        resolved_value["evaluation_dispatch"] = {
            "claim": _binding(project, resolved_prepared["evaluator_path"]),
            "consumer_transaction_id": "scholarly-evaluation:SET-RESOLVED-FINDING",
        }
        resolved_value["dispatch_separation"]["evaluator_claim_id"] = resolved_prepared["evaluator_claim"]["claim_id"]
        resolved_value["findings"][0]["disposition"] = "resolved"
        resolved_value["findings"][0]["current_fingerprint"] = evaluation.finding_fingerprint(
            artifact_sha256=resolved_value["artifact"]["sha256"],
            claim_register_sha256=resolved_value["claim_register"]["sha256"],
            finding=resolved_value["findings"][0],
        )
        resolution_path = red_artifact.parent / "resolved-finding-verification.json"
        _write_json(
            resolution_path,
            {
                "schema_version": "1.0.0",
                "artifact_sha256": resolved_value["artifact"]["sha256"],
                "finding_fingerprint": resolved_value["findings"][0]["current_fingerprint"],
                "verified": True,
            },
        )
        resolved_value["findings"][0]["resolution"] = _binding(project, resolution_path)
        resolved_value["verdict"]["status"] = "qualified"
        resolved_path = red_artifact.parent / "resolved-evaluation.json"
        _publish_evaluation(project, resolved_prepared, resolved_value, resolved_path)
        _expect(
            _run(project, red_artifact, resolved_register, resolved_path),
            rc=0,
            codes=set(),
            label="resolved-finding-control",
            failures=failures,
        )
        resolved_api = evaluation.validate_scholarly_evaluation_binding(
            project,
            red_artifact,
            {
                "evidence_path": resolved_path.relative_to(project).as_posix(),
                "evidence_sha256": _sha_bytes(resolved_path.read_bytes()),
            },
        )
        resolved_dependency_paths = {
            row["path"] for row in resolved_api["dependencies"]
        }
        if (
            resolved_api.get("status") != "qualified"
            or resolved_api.get("judgment_truth_certified") is not False
            or str(resolution_path.resolve()) not in resolved_dependency_paths
        ):
            failures.append(
                "binding-api-resolved-major-control: "
                f"status={resolved_api.get('status')} "
                f"resolution_inventory={str(resolution_path.resolve()) in resolved_dependency_paths}"
            )
        api_cases += 1
        attack_cases += 1

        def mutation_probe(
            label: str,
            artifact: Path,
            register: Path,
            evaluation_path: Path,
            target: Path,
            owner: Any,
            attribute: str,
        ) -> None:
            nonlocal attack_cases
            original_target = target.read_bytes()
            original_function = getattr(owner, attribute)
            mutated = False

            def wrapper(*args: Any, **kwargs: Any) -> Any:
                nonlocal mutated
                result = original_function(*args, **kwargs)
                if not mutated:
                    target.write_bytes(original_target + b" ")
                    mutated = True
                return result

            setattr(owner, attribute, wrapper)
            try:
                try:
                    evaluation.verify_evaluation(project, artifact, register, evaluation_path)
                except evaluation.EvaluationRefusal as exc:
                    if exc.code != "SET-ARTIFACT-STALE":
                        failures.append(f"{label}: mutation refusal {exc.code}, expected SET-ARTIFACT-STALE")
                else:
                    failures.append(f"{label}: controlled mutation still qualified")
            finally:
                setattr(owner, attribute, original_function)
                target.write_bytes(original_target)
            attack_cases += 1

        clean_document = json.loads(saved_clean[3].read_text(encoding="utf-8"))
        clean_claim_path = project / clean_document["evaluation_dispatch"]["claim"]["path"]
        clean_claim_value = json.loads(clean_claim_path.read_text(encoding="utf-8"))
        consumption_candidates = [
            path
            for path in (project / "reviews/.harness/assignment/dispatch/consumptions").glob("*/consumption.json")
            if json.loads(path.read_text(encoding="utf-8")).get("claim_id") == clean_claim_value["claim_id"]
            and json.loads(path.read_text(encoding="utf-8")).get("consumer_transaction_id")
            == clean_document["evaluation_dispatch"]["consumer_transaction_id"]
        ]
        assert len(consumption_candidates) == 1
        clean_consumption = consumption_candidates[0]
        generation_claim_path = project / clean_claim_value["generation_claim"]["path"]
        issuance_ledger = project / "reviews/.harness/assignment/dispatch/issuance/ledger.jsonl"
        replay_targets = [
            ("replay-evaluation-input", saved_clean[3]),
            ("replay-evaluator-claim", clean_claim_path),
            ("replay-consumption", clean_consumption),
            ("replay-consumption-manifest", clean_consumption.parent / "publication_manifest.json"),
            ("replay-consumption-marker", clean_consumption.parent / "commit_marker.json"),
            ("replay-issuance-ledger", issuance_ledger),
            ("replay-generation-claim", generation_claim_path),
            ("replay-artifact-control", clean_artifact),
        ]
        for label, target in replay_targets:
            mutation_probe(
                label,
                clean_artifact,
                clean_register,
                saved_clean[3],
                target,
                evaluation,
                "_verify_generator_envelope",
            )

        mutation_probe(
            "replay-finding-resolution",
            red_artifact,
            resolved_register,
            resolved_path,
            resolution_path,
            evaluation,
            "_verify_obligations",
        )
        assert obligation_clean_context is not None
        mutation_probe(
            "replay-obligation-result",
            obligation_clean_context[0],
            obligation_clean_context[1],
            obligation_clean_context[2],
            obligation_clean_context[3],
            obligations,
            "verify_obligation_result",
        )
        obligation_result_value = json.loads(
            obligation_clean_context[3].read_text(encoding="utf-8")
        )
        for label, key in (
            ("replay-obligation-report", "report"),
            ("replay-obligation-authority", "verifier_receipt"),
        ):
            mutation_probe(
                label,
                obligation_clean_context[0],
                obligation_clean_context[1],
                obligation_clean_context[2],
                project / obligation_result_value[key]["path"],
                obligations,
                "verify_obligation_result",
            )

    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        print(f"scholarly_evaluation_smoketest: FAIL ({len(failures)} mismatch(es))")
        return 1
    print(
        "scholarly_evaluation_smoketest: PASS "
        f"({semantic_pairs} red/twin pairs; {attack_cases} attack/control cases; "
        f"{api_cases} binding API cases; judgment truth not inferred)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
