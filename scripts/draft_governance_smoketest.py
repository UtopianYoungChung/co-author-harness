#!/usr/bin/env python3
"""Behavioral contract for mandatory centroid and writing-policy evidence.

Hermetic: fixtures live below a temporary project root.  The test intentionally
does not depend on the workspace Wiki or on a pre-existing milestone artifact.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "draft_governance.py"
POLICY = ROOT / "references" / "policies" / "draft_governance.v1.json"
OBLIGATION_REGISTRY = (
    ROOT / "references" / "policies" / "obligation_result_registry.v1.json"
)
sys.path.insert(0, str(ROOT / "scripts"))
from assignment_c4_fixture_support import DeterministicFixtureAdapter  # noqa: E402
from d_style_profile_check import build_report as build_dstyle_report  # noqa: E402
from obligation_result import finding_fingerprint  # noqa: E402
from product_assurance import build as build_product_assurance  # noqa: E402
TARGETS = ("M1", "M2", "M3", "M4", "FINAL")
REQUIRED_IDS = {
    "grounding-protocol",
    "d-style-profile",
    "centroid-generation",
    "centroid-evaluation",
    "reader-accessibility",
    "style-commitments",
    "grammar-mechanics",
    "citation-discipline",
    "emdash-bundle",
    "deterministic-audit",
    "safeguard-layer",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*args: str) -> subprocess.CompletedProcess[str]:
    # v0.50.0: Tests need to mark temp workspaces as governed roots
    # Extract project-root from args if present
    env = os.environ.copy()
    try:
        project_idx = args.index("--project-root")
        if project_idx + 1 < len(args):
            project_root = Path(args[project_idx + 1])
            # For research/60_Workbench/<work-id>/ structure, add the workspace root
            # (3 levels up: work-id -> 60_Workbench -> research -> workspace)
            if len(project_root.parts) >= 3 and project_root.parts[-3:-1] == ("research", "60_Workbench"):
                workspace_root = str(project_root.parents[2])
            else:
                workspace_root = str(project_root)
            # Add workspace as a governed root for destination capability
            existing = env.get("COAUTHOR_EXTRA_GOVERNED_ROOTS", "")
            roots = [r for r in existing.split(os.pathsep) if r]
            if workspace_root not in roots:
                roots.append(workspace_root)
            env["COAUTHOR_EXTRA_GOVERNED_ROOTS"] = os.pathsep.join(roots)
    except ValueError:
        pass  # No --project-root arg
    
    return subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "__fixture_cli__", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )


def run_production(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def prepare(project: Path, artifact: Path, target: str, phase: str) -> dict:
    role = {"generation": "generator", "evaluation": "evaluator"}[phase]
    result = run(
        "prepare",
        "--project-root", str(project),
        "--artifact", str(artifact),
        "--target", target,
        "--phase", phase,
        "--role", role,
    )
    require(result.returncode == 0, result.stdout + result.stderr)
    return json.loads(result.stdout)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def binding(path: Path) -> dict[str, str]:
    return {"path": str(path.resolve()), "sha256": sha(path)}


def exact_binding(path: Path, project: Path) -> dict[str, str | int]:
    resolved = path.resolve(strict=True)
    return {
        "path": resolved.relative_to(project.resolve(strict=True)).as_posix(),
        "sha256": sha(resolved),
        "byte_length": resolved.stat().st_size,
    }


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def fixture_authority_envelope(
    project: Path,
    *,
    receipt_type: str,
    authority: str,
    subject: dict[str, Any],
    token: str,
) -> dict[str, str | int]:
    adapter = DeterministicFixtureAdapter()
    unsigned = {
        "schema_version": "1.0.0",
        "receipt_type": receipt_type,
        "authority_mode": "fixture_hmac",
        "authority": authority,
        "subject": subject,
    }
    envelope = {
        **unsigned,
        "authenticator": {
            "issuer": adapter.issuer,
            "tool": adapter.tool,
            "version": adapter.version,
            "digest": adapter.digest(unsigned),
        },
    }
    path = project / "reviews" / ".harness" / "obligation-authority" / f"{receipt_type}-{token}.json"
    write_json(path, envelope)
    return exact_binding(path, project)


def dstyle_evidence_identity(finding: dict[str, Any]) -> str:
    return hashlib.sha256(
        canonical_bytes({
            "field": finding.get("field"),
            "locator": finding.get("locator"),
            "message": finding.get("message"),
        })
    ).hexdigest()


def bind_adjudication_authority(
    project: Path,
    adjudication: dict[str, Any],
) -> None:
    payload = {
        key: value for key, value in adjudication.items()
        if key != "authority_receipt"
    }
    subject = {
        "schema_version": "1.0.0",
        "subject_type": "obligation_adjudication_authorization",
        "authority": adjudication["authority"],
        "adjudication_payload_sha256": hashlib.sha256(
            canonical_bytes(payload)
        ).hexdigest(),
        "obligation_id": adjudication["obligation_id"],
        "finding_fingerprint": adjudication["finding_fingerprint"],
        "artifact": adjudication["artifact"],
    }
    token = hashlib.sha256(canonical_bytes(subject)).hexdigest()[:16]
    subject_path = (
        project
        / "reviews"
        / ".harness"
        / "obligation-authority"
        / f"adjudication-subject-{token}.json"
    )
    write_json(subject_path, subject)
    adjudication["authority_receipt"] = fixture_authority_envelope(
        project,
        receipt_type="obligation_adjudication_authority",
        authority=adjudication["authority"],
        subject=exact_binding(subject_path, project),
        token=token,
    )


def mutate_typed_result(
    receipt: dict,
    obligation_id: str,
    project: Path,
    mutator: Any,
) -> None:
    row = next(item for item in receipt["obligations"] if item["id"] == obligation_id)
    result_path = project / row["result"]["path"]
    value = json.loads(result_path.read_text(encoding="utf-8"))
    mutator(value)
    write_json(result_path, value)
    row["result"] = exact_binding(result_path, project)


def centroid_packet(
    path: Path,
    contract: dict,
    manuscript: Path,
    *,
    member_scope: str = "both",
    derivation: str = "write",
) -> None:
    write_json(path, {
        "schema_version": "1.0.0",
        "capability": "centroid-pass",
        "status": "binding_resolved",
        "reason_code": None,
        "read_only": True,
        "writes_performed": False,
        "public_activation": "active",
        "binding_provenance": contract["centroid"]["binding_provenance"],
        "manuscript": {
            "path": str(manuscript.resolve()),
            "sha256": sha(manuscript),
            "scope": {"kind": "full_manuscript", "sha256": sha(manuscript)},
        },
        "policy": {
            "derivation": derivation,
            "profile_sha256": contract["centroid"]["profile_sha256"],
            "attestation_view_pin": contract["centroid"]["attestation_view_pin"],
            "exemplar_view_pin": contract["centroid"]["exemplar_view_pin"],
            "members": [{
                "source_key": "fixture-source",
                "role": "centroid",
                "grounding": "full-read",
                "warrant_scope": member_scope,
            }],
        },
        "analysis_contract": {"discipline": "fixture semantic dispatch"},
        "scope_metrics": {},
        "semantic_findings": [],
        "limitations": ["role performs semantic judgment"],
    })


def semantic_receipt(
    path: Path,
    *,
    phase: str,
    role: str,
    actor_id: str,
    dispatch_id: str,
    artifact: Path,
    packet: Path,
    source: Path,
    extract: Path,
    generation_envelope: Path | None = None,
    use_scope: str = "surface",
    source_key: str = "fixture-source",
    target: str = "M2",
) -> None:
    value = {
        "schema_version": "2.0.0",
        "receipt_type": "centroid_semantic_execution",
        "target": target,
        "phase": phase,
        "role": role,
        "actor_id": actor_id,
        "dispatch_id": dispatch_id,
        "artifact": binding(artifact),
        "centroid_packet": binding(packet),
        "passages": [{
            "source_key": source_key,
            "use_scope": use_scope,
            "source": binding(source),
            "locator": "p. 1",
            "extract": binding(extract),
            "extraction": {"method": "text-direct", "tool": "utf-8", "canonical": True},
            "quote": "A grounded fixture source passage.",
            "citation": {
                "authors": ["Fixture, F."],
                "year": 2026,
                "title": "Fixture source",
                "label": "2026",
            },
            "use": "Condition the fixture register and argument.",
        }],
        "semantic_assessment": {
            "summary": "Fixture passage was used for the semantic pass.",
            "strengths": ["bounded register"],
            "deviations": [],
            "warrant_limits": ["fixture only"],
            "actionable_findings": [],
        },
    }
    if generation_envelope is not None:
        value["generation_envelope"] = binding(generation_envelope)
        value["adjudications"] = []
    write_json(path, value)


def obligation_receipt(
    contract: dict,
    contract_path: Path,
    artifact: Path,
    phase: str,
    semantic_path: Path,
    generic_evidence: Path,
) -> dict:
    role = {"generation": "generator", "evaluation": "evaluator"}[phase]
    centroid_id = f"centroid-{phase}"
    project = Path(contract["project_root"]).resolve(strict=True)
    registry = json.loads(OBLIGATION_REGISTRY.read_text(encoding="utf-8"))
    result_rows: list[dict] = []
    for row in contract["obligations"]:
        if phase not in row["phases"]:
            continue
        evidence_path = semantic_path if row["id"] == centroid_id else generic_evidence
        if row.get("typed_result_required") is True:
            adapter = registry["obligations"][row["id"]]
            result = {
                "schema_version": "1.0.0",
                "obligation_id": row["id"],
                "adapter_version": row["result_adapter"]["adapter_version"],
                "artifact": exact_binding(artifact, project),
                "policy": exact_binding(contract_path, project),
                "activation": row["activation"],
                "execution_status": "completed",
                "legacy_execution_evidence": {
                    "status": "applied",
                    "evidence": [exact_binding(evidence_path, project)],
                    "rationale": "The fixture adapter executed; this does not substitute for its clean outcome.",
                },
                "outcome": "clean",
                "findings": [],
                "diagnostic_only": row["result_adapter"]["diagnostic_only"],
                "created_at": "2026-07-26T00:00:00Z",
                "adjudications": [],
            }
            report_path = (
                project
                / "reviews"
                / ".harness"
                / "obligation-reports"
                / phase
                / f"{row['id']}.json"
            )
            if row["id"] == "d-style-profile":
                report = build_dstyle_report(
                    project,
                    project / "research_notes" / "directives.md",
                    artifact,
                )
                actionable = []
                for finding in report["findings"]:
                    severity = finding.get("severity")
                    if severity not in {"ADVISORY", "MINOR", "MAJOR", "BLOCKER"}:
                        continue
                    evidence_identity = dstyle_evidence_identity(finding)
                    actionable.append({
                        "code": finding["code"],
                        "severity": severity,
                        "evidence_identity": evidence_identity,
                        "fingerprint": finding_fingerprint(
                            row["id"],
                            finding["code"],
                            severity,
                            evidence_identity,
                            result["artifact"]["sha256"],
                        ),
                        "disposition": "open",
                    })
                result["outcome"] = "findings" if actionable else "clean"
                result["findings"] = actionable
                write_json(report_path, report)
                result["report"] = exact_binding(report_path, project)
            else:
                report = {
                    "schema_version": "1.0.0",
                    "report_type": "obligation_adapter_report",
                    "adapter_id": adapter["adapter_id"],
                    "adapter_version": result["adapter_version"],
                    "obligation_id": result["obligation_id"],
                    "artifact": result["artifact"],
                    "policy": result["policy"],
                    "activation": result["activation"],
                    "execution_status": result["execution_status"],
                    "outcome": result["outcome"],
                    "findings": result["findings"],
                    "diagnostic_only": result["diagnostic_only"],
                    "created_at": result["created_at"],
                }
                write_json(report_path, report)
                result["report"] = exact_binding(report_path, project)
                token = hashlib.sha256(canonical_bytes(report)).hexdigest()[:16]
                result["verifier_receipt"] = fixture_authority_envelope(
                    project,
                    receipt_type="obligation_verifier_authority",
                    authority=adapter["authorized_adjudicators"][0],
                    subject=result["report"],
                    token=token,
                )
            result_path = (
                project
                / "reviews"
                / ".harness"
                / "obligation-results"
                / phase
                / f"{row['id']}.json"
            )
            write_json(result_path, result)
            result_rows.append({"id": row["id"], "result": exact_binding(result_path, project)})
        else:
            result_rows.append(
                {
                    "id": row["id"],
                    "status": "applied",
                    "evidence": [binding(evidence_path)],
                    "rationale": "fixture evidence",
                }
            )
    # v0.50.0: Add required transaction metadata
    version_path = ROOT / "version.json"
    version_data = json.loads(version_path.read_text(encoding="utf-8"))
    return {
        "schema_version": "1.0.0",
        "phase": phase,
        "role": role,
        "contract_sha256": sha(contract_path),
        "artifact": {"path": str(artifact.resolve()), "sha256": sha(artifact)},
        "obligations": result_rows,
        "host_identity": "test",
        "package_identity": {
            "name": version_data["name"],
            "version": version_data["version"],
            "path": str(version_path.relative_to(ROOT)),
            "sha256": sha(version_path),
        },
        "input_bindings": [
            {"path": str(POLICY.relative_to(ROOT)), "sha256": sha(POLICY)},
            {"path": str(OBLIGATION_REGISTRY.relative_to(ROOT)), "sha256": sha(OBLIGATION_REGISTRY)},
        ],
    }


def main() -> int:
    require(POLICY.is_file(), "draft-governance policy is missing")
    require(OBLIGATION_REGISTRY.is_file(), "obligation-result registry is missing")
    require(SCRIPT.is_file(), "draft-governance executable is missing")
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    obligation_registry = json.loads(OBLIGATION_REGISTRY.read_text(encoding="utf-8"))
    require(policy["schema_version"] == "1.0.0", "unexpected policy version")
    require(set(policy["targets"]) == set(TARGETS), "policy must cover M1-M4 and FINAL")
    require(
        set(obligation_registry["obligations"]) == {row["id"] for row in policy["obligations"]},
        "obligation-result registry must cover the complete draft-governance policy",
    )
    require(REQUIRED_IDS <= {row["id"] for row in policy["obligations"]},
            "governing policy bundle is incomplete")
    intended_red: list[str] = []

    with tempfile.TemporaryDirectory(prefix="draft-governance-") as td:
        # v0.50.0: Create project at research/60_Workbench/<work-id>/ to match shipment path requirements
        workspace_root = Path(td)
        project = workspace_root / "research" / "60_Workbench" / "test-work"
        project.mkdir(parents=True)
        (project / "reviews").mkdir()
        (project / "research_notes").mkdir()
        write_json(
            project / "project_manifest.json",
            {
                "identity": "draft-governance-c4-synthetic-project",
                "synthetic_fixture": "c4",
                "production_authority": False,
            },
        )
        (project / "research_notes" / "directives.md").write_text(
            """d_style_profile:
  question_type: conceptual
  citation_style: turabian_author_date
  source_role_policy: strict_role_classification
  evidence_display_policy: standard
  assistance_disclosure_policy: project_local
  harness_profile: standard_research_review
""",
            encoding="utf-8",
        )

        missing = project / "milestones" / "M1_project_memo.md"
        missing_contract = prepare(project, missing, "M1", "generation")
        require(missing_contract["artifact"]["state"] == "absent",
                "a missing milestone artifact must still produce a governance contract")
        require(missing_contract["centroid"]["required"] is True,
                "centroid generation must be mandatory at M1")

        wrong_role = run(
            "prepare",
            "--project-root", str(project),
            "--artifact", str(missing),
            "--target", "M1",
            "--phase", "generation",
            "--role", "evaluator",
        )
        require(
            wrong_role.returncode == 4
            and "DRAFT-POLICY-ROLE" in wrong_role.stdout,
            "prepare must reject a role that does not match the requested phase",
        )

        artifact = project / "milestones" / "artifact.md"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text(
            """# Draft

This paper argues a bounded claim because the synthetic case exposes a
coordination gap. The evidence quotes "A grounded fixture source passage."
The warrant is that the quoted observation supports only this narrow claim;
this matters because stronger generalization would exceed the evidence. A
limitation is that the example is synthetic. Assistance: automated review
checked the wording, while the author retained responsibility for the claim.
""",
            encoding="utf-8",
        )
        for target in TARGETS:
            for phase in ("generation", "evaluation"):
                contract = prepare(project, artifact, target, phase)
                require(contract["centroid"]["required"] is True,
                        f"centroid must be mandatory for {target}/{phase}")
                require(REQUIRED_IDS <= {row["id"] for row in contract["obligations"]},
                        f"missing obligations for {target}/{phase}")
                require(
                    all(row["typed_result_required"] is True for row in contract["obligations"]),
                    f"every governed obligation must use typed results for {target}/{phase}",
                )

        source = project / "corpus" / "fixture-source.txt"
        source.parent.mkdir(parents=True)
        source.write_text("A grounded fixture source passage.\n", encoding="utf-8")
        extract = project / "reviews" / "fixture-source-p1.txt"
        extract.write_text("A grounded fixture source passage.\n", encoding="utf-8")
        evidence = project / "evidence.txt"
        evidence.write_text("generic evidence\n", encoding="utf-8")

        generation_contract = prepare(project, artifact, "M2", "generation")
        generation_contract_path = project / "generation-contract.json"
        write_json(generation_contract_path, generation_contract)
        generation_packet = project / "generation-centroid-packet.json"
        centroid_packet(generation_packet, generation_contract, artifact)
        generation_semantic = project / "generation-semantic.json"
        semantic_receipt(
            generation_semantic,
            phase="generation", role="generator", actor_id="generator-A",
            dispatch_id="generation-1", artifact=artifact, packet=generation_packet,
            source=source, extract=extract,
        )
        generation_receipt = obligation_receipt(
            generation_contract, generation_contract_path, artifact, "generation",
            generation_semantic, evidence,
        )
        generation_receipt_path = project / "generation-receipt.json"
        write_json(generation_receipt_path, generation_receipt)
        generated = run(
            "verify", "--contract", str(generation_contract_path),
            "--receipt", str(generation_receipt_path), "--artifact", str(artifact),
            "--phase", "generation", "--role", "generator",
        )
        require(generated.returncode == 0, generated.stdout + generated.stderr)
        production_fixture_refusal = run_production(
            "verify", "--contract", str(generation_contract_path),
            "--receipt", str(generation_receipt_path), "--artifact", str(artifact),
            "--phase", "generation", "--role", "generator",
        )
        require(
            production_fixture_refusal.returncode != 0
            and "DRAFT-POLICY-OBLIGATION-STALE" in production_fixture_refusal.stdout,
            "production draft governance must not expose the test authority adapter",
        )
        generated_value = json.loads(generated.stdout)
        require(
            "deterministic-audit" in generated_value["diagnostic_obligation_result_ids"]
            and "deterministic-audit" not in generated_value[
                "lifecycle_clearing_obligation_result_ids"
            ],
            "run_all-backed deterministic audit must remain diagnostic-only",
        )
        generation_envelope = project / "generation.verified.json"
        write_json(generation_envelope, generated_value)

        generic_centroid = json.loads(json.dumps(generation_receipt))
        mutate_typed_result(
            generic_centroid,
            "centroid-generation",
            project,
            lambda value: value["legacy_execution_evidence"].update(
                {"evidence": [exact_binding(evidence, project)]}
            ),
        )
        generic_path = project / "generic-centroid-receipt.json"
        write_json(generic_path, generic_centroid)
        generic_result = run(
            "verify", "--contract", str(generation_contract_path),
            "--receipt", str(generic_path), "--artifact", str(artifact),
            "--phase", "generation", "--role", "generator",
        )
        require(
            generic_result.returncode != 0
            and "DRAFT-POLICY-CENTROID-EVIDENCE" in generic_result.stdout,
            "generic path/hash evidence must not satisfy centroid semantic execution",
        )

        wrong_derivation_packet = project / "wrong-derivation-centroid-packet.json"
        centroid_packet(
            wrong_derivation_packet, generation_contract, artifact, derivation="review"
        )
        wrong_derivation_semantic = project / "wrong-derivation-semantic.json"
        semantic_receipt(
            wrong_derivation_semantic,
            phase="generation", role="generator", actor_id="generator-A",
            dispatch_id="generation-wrong-derivation", artifact=artifact,
            packet=wrong_derivation_packet, source=source, extract=extract,
        )
        wrong_derivation_receipt = obligation_receipt(
            generation_contract, generation_contract_path, artifact, "generation",
            wrong_derivation_semantic, evidence,
        )
        wrong_derivation_path = project / "wrong-derivation-receipt.json"
        write_json(wrong_derivation_path, wrong_derivation_receipt)
        wrong_derivation_result = run(
            "verify", "--contract", str(generation_contract_path),
            "--receipt", str(wrong_derivation_path), "--artifact", str(artifact),
            "--phase", "generation", "--role", "generator",
        )
        require(
            wrong_derivation_result.returncode != 0
            and "DRAFT-POLICY-CENTROID-EVIDENCE" in wrong_derivation_result.stdout,
            "generation must reject a review-derived centroid packet",
        )

        stale_contract = prepare(project, artifact, "M2", "evaluation")
        stale_contract_path = project / "stale-evaluation-contract.json"
        write_json(stale_contract_path, stale_contract)
        original = artifact.read_text(encoding="utf-8")
        artifact.write_text(original + "A post-prepare mutation.\n", encoding="utf-8")
        stale_packet = project / "stale-review-centroid-packet.json"
        centroid_packet(stale_packet, stale_contract, artifact, derivation="review")
        stale_semantic = project / "stale-evaluation-semantic.json"
        semantic_receipt(
            stale_semantic,
            phase="evaluation", role="evaluator", actor_id="evaluator-B",
            dispatch_id="evaluation-stale", artifact=artifact, packet=stale_packet,
            source=source, extract=extract, generation_envelope=generation_envelope,
        )
        stale_receipt = obligation_receipt(
            stale_contract, stale_contract_path, artifact, "evaluation",
            stale_semantic, evidence,
        )
        stale_path = project / "stale-contract-receipt.json"
        write_json(stale_path, stale_receipt)
        stale_result = run(
            "verify", "--contract", str(stale_contract_path),
            "--receipt", str(stale_path), "--artifact", str(artifact),
            "--phase", "evaluation", "--role", "evaluator",
        )
        require(
            stale_result.returncode != 0
            and "DRAFT-POLICY-CONTRACT-ARTIFACT-STALE" in stale_result.stdout,
            "verify must reject artifact bytes changed after prepare",
        )
        artifact.write_text(original, encoding="utf-8")

        contract = prepare(project, artifact, "M2", "evaluation")
        contract_path = project / "evaluation-contract.json"
        write_json(contract_path, contract)
        review_packet = project / "review-centroid-packet.json"
        centroid_packet(review_packet, contract, artifact, derivation="review")
        evaluation_semantic = project / "evaluation-semantic.json"
        semantic_receipt(
            evaluation_semantic,
            phase="evaluation", role="evaluator", actor_id="evaluator-B",
            dispatch_id="evaluation-1", artifact=artifact, packet=review_packet,
            source=source, extract=extract, generation_envelope=generation_envelope,
        )
        receipt = obligation_receipt(
            contract, contract_path, artifact, "evaluation", evaluation_semantic, evidence
        )
        receipt_path = project / "receipt.json"
        write_json(receipt_path, receipt)
        verified = run(
            "verify", "--contract", str(contract_path), "--receipt", str(receipt_path),
            "--artifact", str(artifact), "--phase", "evaluation", "--role", "evaluator",
        )
        require(verified.returncode == 0, verified.stdout + verified.stderr)
        require(json.loads(verified.stdout)["status"] == "verified", "receipt did not verify")

        # C1 red specification: a hand-authored green assurance object with
        # current hashes must never qualify itself.  v0.38 accepts it because
        # draft_governance shape-checks the supplied report instead of invoking
        # the product kernel or validating a verifier-issued transaction.
        forged_assurance_path = project / "forged-green-assurance.json"
        write_json(
            forged_assurance_path,
            build_product_assurance(artifact, evaluation_semantic),
        )
        forged_receipt = json.loads(json.dumps(receipt))
        mutate_typed_result(
            forged_receipt,
            "centroid-evaluation",
            project,
            lambda value: value["legacy_execution_evidence"].update(
                {
                    "evidence": [
                        exact_binding(evaluation_semantic, project),
                        exact_binding(forged_assurance_path, project),
                    ]
                }
            ),
        )
        forged_receipt_path = project / "forged-green-receipt.json"
        write_json(forged_receipt_path, forged_receipt)
        forged_result = run(
            "verify", "--contract", str(contract_path),
            "--receipt", str(forged_receipt_path), "--artifact", str(artifact),
            "--phase", "evaluation", "--role", "evaluator",
        )
        if not (
            forged_result.returncode != 0 and "ASSURANCE-FORGED" in forged_result.stdout
        ):
            intended_red.append(
                "ASSURANCE-FORGED: hand-authored green assurance with current hashes "
                f"returned {forged_result.returncode}"
            )

        # C1 red specification: one halo surface passage cannot stand in for a
        # centroid-role surface passage.  The future per-argument-member
        # rationale is a separate C2 interface-blocked case.
        coverage_contract = prepare(project, artifact, "M2", "generation")
        coverage_contract_path = project / "coverage-contract.json"
        write_json(coverage_contract_path, coverage_contract)
        coverage_packet = project / "coverage-centroid-packet.json"
        centroid_packet(coverage_packet, coverage_contract, artifact)
        coverage_packet_value = json.loads(coverage_packet.read_text(encoding="utf-8"))
        coverage_packet_value["policy"]["members"].append({
            "source_key": "fixture-halo",
            "role": "halo",
            "grounding": "full-read",
            "warrant_scope": "both",
        })
        write_json(coverage_packet, coverage_packet_value)
        coverage_semantic = project / "coverage-semantic.json"
        semantic_receipt(
            coverage_semantic,
            phase="generation", role="generator", actor_id="generator-coverage",
            dispatch_id="generation-coverage", artifact=artifact,
            packet=coverage_packet, source=source, extract=extract,
            source_key="fixture-halo",
        )
        coverage_receipt = obligation_receipt(
            coverage_contract, coverage_contract_path, artifact, "generation",
            coverage_semantic, evidence,
        )
        coverage_receipt_path = project / "coverage-receipt.json"
        write_json(coverage_receipt_path, coverage_receipt)
        coverage_result = run(
            "verify", "--contract", str(coverage_contract_path),
            "--receipt", str(coverage_receipt_path), "--artifact", str(artifact),
            "--phase", "generation", "--role", "generator",
        )
        if not (
            coverage_result.returncode != 0
            and "CENTROID-COVERAGE-INCOMPLETE" in coverage_result.stdout
        ):
            intended_red.append(
                "CENTROID-COVERAGE-INCOMPLETE: halo-only surface evidence "
                f"returned {coverage_result.returncode}"
            )

        semantic_receipt(
            evaluation_semantic,
            phase="evaluation", role="evaluator", actor_id="generator-A",
            dispatch_id="evaluation-self", artifact=artifact, packet=review_packet,
            source=source, extract=extract, generation_envelope=generation_envelope,
        )
        self_receipt = obligation_receipt(
            contract, contract_path, artifact, "evaluation", evaluation_semantic, evidence
        )
        self_path = project / "self-evaluation-receipt.json"
        write_json(self_path, self_receipt)
        self_result = run(
            "verify", "--contract", str(contract_path), "--receipt", str(self_path),
            "--artifact", str(artifact), "--phase", "evaluation", "--role", "evaluator",
        )
        require(
            self_result.returncode != 0
            and "DRAFT-POLICY-EVALUATOR-INDEPENDENCE" in self_result.stdout,
            "the generation actor must not self-certify evaluation",
        )

        receipt["obligations"] = receipt["obligations"][1:]
        write_json(receipt_path, receipt)
        rejected = run(
            "verify", "--contract", str(contract_path), "--receipt", str(receipt_path),
            "--artifact", str(artifact), "--phase", "evaluation", "--role", "evaluator",
        )
        require(rejected.returncode != 0 and "DRAFT-POLICY-OBLIGATION-MISSING" in rejected.stdout,
                "an incomplete governing-policy receipt must fail closed")

        # C4 integration: an always-on D-STYLE row must be a typed result;
        # legacy `applied` evidence cannot clear it, and a current MAJOR finding
        # clears only through an exact authorized resolution.
        semantic_receipt(
            evaluation_semantic,
            phase="evaluation", role="evaluator", actor_id="evaluator-B",
            dispatch_id="evaluation-c4", artifact=artifact, packet=review_packet,
            source=source, extract=extract, generation_envelope=generation_envelope,
        )
        typed_receipt = obligation_receipt(
            contract, contract_path, artifact, "evaluation", evaluation_semantic, evidence
        )
        downgraded_contract = json.loads(json.dumps(contract))
        next(
            row for row in downgraded_contract["obligations"]
            if row["id"] == "d-style-profile"
        )["typed_result_required"] = False
        downgraded_contract_path = project / "downgraded-dstyle-contract.json"
        write_json(downgraded_contract_path, downgraded_contract)
        downgraded_result = run(
            "verify", "--contract", str(downgraded_contract_path),
            "--receipt", str(receipt_path), "--artifact", str(artifact),
            "--phase", "evaluation", "--role", "evaluator",
        )
        require(
            downgraded_result.returncode != 0
            and "DRAFT-POLICY-OBLIGATION-STALE" in downgraded_result.stdout,
            "an always-on typed obligation must not be downgraded in a copied contract",
        )
        legacy_dstyle = json.loads(json.dumps(typed_receipt))
        for index, row in enumerate(legacy_dstyle["obligations"]):
            if row["id"] == "d-style-profile":
                legacy_dstyle["obligations"][index] = {
                    "id": "d-style-profile",
                    "status": "applied",
                    "evidence": [binding(evidence)],
                    "rationale": "legacy mechanics executed",
                }
        legacy_dstyle_path = project / "legacy-dstyle-receipt.json"
        write_json(legacy_dstyle_path, legacy_dstyle)
        legacy_dstyle_result = run(
            "verify", "--contract", str(contract_path), "--receipt", str(legacy_dstyle_path),
            "--artifact", str(artifact), "--phase", "evaluation", "--role", "evaluator",
        )
        require(
            legacy_dstyle_result.returncode != 0
            and "DRAFT-POLICY-OBLIGATION-SCHEMA" in legacy_dstyle_result.stdout,
            "legacy applied evidence must not clear always-on D-STYLE",
        )

        legacy_conditional = json.loads(json.dumps(typed_receipt))
        for index, row in enumerate(legacy_conditional["obligations"]):
            if row["id"] == "is-paper-architecture":
                legacy_conditional["obligations"][index] = {
                    "id": "is-paper-architecture",
                    "status": "not_applicable",
                    "evidence": [],
                    "rationale": "caller asserts the predicate is false",
                }
        legacy_conditional_path = project / "legacy-conditional-receipt.json"
        write_json(legacy_conditional_path, legacy_conditional)
        legacy_conditional_result = run(
            "verify", "--contract", str(contract_path),
            "--receipt", str(legacy_conditional_path), "--artifact", str(artifact),
            "--phase", "evaluation", "--role", "evaluator",
        )
        require(
            legacy_conditional_result.returncode != 0
            and "DRAFT-POLICY-OBLIGATION-SCHEMA" in legacy_conditional_result.stdout,
            "a rationale-only false activation must not bypass typed proof",
        )

        c4_artifact = project / "milestones" / "c4-dstyle-major.md"
        c4_artifact.write_text(
            '# Draft\n\nA bare claim quotes "A grounded fixture source passage."\n',
            encoding="utf-8",
        )
        c4_contract = prepare(project, c4_artifact, "M2", "generation")
        c4_contract_path = project / "c4-dstyle-contract.json"
        write_json(c4_contract_path, c4_contract)
        c4_packet = project / "c4-dstyle-centroid-packet.json"
        centroid_packet(c4_packet, c4_contract, c4_artifact)
        c4_semantic = project / "c4-dstyle-semantic.json"
        semantic_receipt(
            c4_semantic,
            phase="generation", role="generator", actor_id="generator-C4",
            dispatch_id="generation-c4-dstyle", artifact=c4_artifact,
            packet=c4_packet, source=source, extract=extract,
        )
        typed_receipt = obligation_receipt(
            c4_contract, c4_contract_path, c4_artifact, "generation",
            c4_semantic, evidence,
        )
        dstyle_row = next(
            row for row in typed_receipt["obligations"]
            if row["id"] == "d-style-profile"
        )
        dstyle_result_path = project / dstyle_row["result"]["path"]
        dstyle_result = json.loads(dstyle_result_path.read_text(encoding="utf-8"))
        require(
            dstyle_result["outcome"] == "findings"
            and any(row["severity"] == "MAJOR" for row in dstyle_result["findings"]),
            "the synthetic D-STYLE proving artifact must produce a real MAJOR report",
        )
        typed_receipt_path = project / "typed-dstyle-receipt.json"
        write_json(typed_receipt_path, typed_receipt)
        blocked_dstyle = run(
            "verify", "--contract", str(c4_contract_path),
            "--receipt", str(typed_receipt_path), "--artifact", str(c4_artifact),
            "--phase", "generation", "--role", "generator",
        )
        require(
            blocked_dstyle.returncode != 0
            and "DRAFT-POLICY-OBLIGATION-BLOCKING-OUTCOME" in blocked_dstyle.stdout,
            "an applied D-STYLE MAJOR finding must remain lifecycle-blocking",
        )

        adjudications = []
        for index, finding in enumerate(dstyle_result["findings"], start=1):
            adjudication = {
                "schema_version": "1.0.0",
                "adjudication_id": f"fixture-dstyle-resolution-{index}",
                "obligation_id": "d-style-profile",
                "finding_fingerprint": finding["fingerprint"],
                "artifact": exact_binding(c4_artifact, project),
                "disposition": "resolved",
                "authority": "independent-evaluator",
                "authority_receipt": {
                    "path": "pending",
                    "sha256": "0" * 64,
                    "byte_length": 0,
                },
                "rationale": "The current synthetic artifact bytes were independently rechecked.",
                "resolution_verification": {
                    "artifact_sha256": sha(c4_artifact),
                    "artifact_byte_length": c4_artifact.stat().st_size,
                    "finding_fingerprint": finding["fingerprint"],
                    "verified": True,
                },
                "created_at": "2026-07-26T00:01:00Z",
            }
            bind_adjudication_authority(project, adjudication)
            adjudications.append(adjudication)
        dstyle_result["adjudications"] = adjudications
        write_json(dstyle_result_path, dstyle_result)
        dstyle_row["result"] = exact_binding(dstyle_result_path, project)
        write_json(typed_receipt_path, typed_receipt)
        resolved_dstyle = run(
            "verify", "--contract", str(c4_contract_path),
            "--receipt", str(typed_receipt_path), "--artifact", str(c4_artifact),
            "--phase", "generation", "--role", "generator",
        )
        require(
            resolved_dstyle.returncode == 0,
            "current exact-byte D-STYLE resolution did not clear: "
            + resolved_dstyle.stdout
            + resolved_dstyle.stderr,
        )

        write_json(
            project / "reviews" / "phase_state.json",
            {
                "schema_version": "0.7.4",
                "milestone_framework": {
                    "policy_bindings": {
                        "reader_accessibility": {
                            "binding_version": "2.0.0",
                            "semantic_usage": "not_invoked",
                            "profile_path": "references/policies/reader_accessibility.v1.json",
                            "profile_sha256": "0" * 64,
                            "resolved_sha256": "1" * 64,
                        }
                    }
                },
            },
        )
        lane = run(
            "evaluation-lane",
            "--project-root", str(project),
            "--artifact", str(artifact),
            "--target", "M3",
            "--shipment-id", "smoketest-evaluation-lane",
        )
        require(lane.returncode == 0, lane.stdout + lane.stderr)
        lane_note = json.loads(lane.stdout)
        require(
            lane_note.get("status") == "evaluated"
            and lane_note.get("status") != "scaffolded",
            "evaluation-lane must not remain scaffolded after dest-safe obligations ran",
        )
        require(
            "verify_is_not_complete" not in lane_note,
            "verify_is_not_complete is no longer the honest evaluation-lane label",
        )
        require(
            lane_note.get("dest_protected_stays") is True,
            "evaluation-lane must keep dest_protected_stays",
        )
        require(
            "d-style-profile" in lane_note.get("ran_obligation_ids", []),
            "d-style-profile must actually run on the evaluation lane",
        )
        require(
            "deterministic-audit" in lane_note.get("ran_obligation_ids", []),
            "deterministic-audit must actually run dest-safe on the evaluation lane",
        )
        # v0.50.0: Scholarly obligations are deferred (not_run), not fail-closed
        deferred = lane_note.get("deferred_obligation_ids", [])
        require(
            isinstance(deferred, list) and len(deferred) > 0,
            "evaluation-lane must defer prompt-mediated scholarly obligations",
        )
        require(
            lane_note.get("centroid_graph", {}).get("status") == "fail_closed"
            and lane_note.get("centroid_graph", {}).get("reason_code")
            == "GRAPH_GOVERNED_GENERATION_UNAVAILABLE",
            "centroid/graph must fail-closed when semantic_usage=not_invoked",
        )
        ship = project / "reviews" / ".harness" / "shipments" / "smoketest-evaluation-lane"
        result_dir = ship / "obligation-results" / "evaluation"
        deferred_results = []
        cleaned = []
        mechanical = []
        for result_path in sorted(result_dir.glob("*.json")):
            value = json.loads(result_path.read_text(encoding="utf-8"))
            obligation_id = value.get("obligation_id")
            if value.get("execution_status") == "not_run" and value.get("outcome") == "error":
                deferred_results.append(obligation_id)
            if value.get("outcome") == "clean" and obligation_id != "d-style-profile":
                cleaned.append(obligation_id)
            if obligation_id in ("d-style-profile", "deterministic-audit"):
                mechanical.append(obligation_id)
        # v0.50.0: Scholarly obligations are deferred (not_run), not fail-closed
        require(
            len(deferred_results) > 0,
            "evaluation-lane must defer prompt-mediated scholarly obligations (not_run shells)",
        )
        require(not cleaned, "evaluation-lane must not mint scholarly CLEAN: " + ", ".join(cleaned))
        # Mechanical obligations should still run
        require(
            len(mechanical) >= 2,
            "d-style-profile and deterministic-audit must run mechanically",
        )
        grounding = json.loads((result_dir / "grounding-protocol.json").read_text(encoding="utf-8"))
        require(
            grounding.get("execution_status") == "not_run"
            and grounding.get("outcome") == "error"
            and grounding.get("findings") == [],
            "prompt-mediated scholarly rows must be deferred (not_run) shells, not fail-closed",
        )
        dstyle = json.loads((result_dir / "d-style-profile.json").read_text(encoding="utf-8"))
        require(
            dstyle.get("execution_status") == "completed"
            and dstyle.get("outcome") in {"findings", "clean"},
            "d-style-profile must remain a real mechanical result",
        )
        if dstyle.get("outcome") == "findings":
            require(
                all(row.get("disposition") == "open" for row in dstyle.get("findings", [])),
                "d-style findings must stay findings",
            )

        require(
            not intended_red,
            "C1 intended-red trust-boundary regressions remain open:\n- "
            + "\n- ".join(intended_red),
        )

    print("draft_governance_smoketest: PASS")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "__fixture_cli__":
        from draft_governance import main as draft_governance_main

        raise SystemExit(
            draft_governance_main(
                sys.argv[2:],
                _test_authority_adapter=DeterministicFixtureAdapter(),
            )
        )
    raise SystemExit(main())
