#!/usr/bin/env python3
"""Behavioral contract for mandatory centroid and writing-policy evidence.

Hermetic: fixtures live below a temporary project root.  The test intentionally
does not depend on the workspace Wiki or on a pre-existing milestone artifact.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "draft_governance.py"
POLICY = ROOT / "references" / "policies" / "draft_governance.v1.json"
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
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def binding(path: Path) -> dict[str, str]:
    return {"path": str(path.resolve()), "sha256": sha(path)}


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
        "status": "ready",
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
    target: str = "M2",
) -> None:
    value = {
        "schema_version": "1.0.0",
        "receipt_type": "centroid_semantic_execution",
        "target": target,
        "phase": phase,
        "role": role,
        "actor_id": actor_id,
        "dispatch_id": dispatch_id,
        "artifact": binding(artifact),
        "centroid_packet": binding(packet),
        "passages": [{
            "source_key": "fixture-source",
            "use_scope": use_scope,
            "source": binding(source),
            "locator": "p. 1",
            "extract": binding(extract),
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
    return {
        "schema_version": "1.0.0",
        "phase": phase,
        "role": role,
        "contract_sha256": sha(contract_path),
        "artifact": {"path": str(artifact.resolve()), "sha256": sha(artifact)},
        "obligations": [
            {
                "id": row["id"],
                "status": "applied",
                "evidence": [binding(
                    semantic_path if row["id"] == centroid_id else generic_evidence
                )],
                "rationale": "fixture evidence",
            }
            for row in contract["obligations"]
            if phase in row["phases"]
        ],
    }


def main() -> int:
    require(POLICY.is_file(), "draft-governance policy is missing")
    require(SCRIPT.is_file(), "draft-governance executable is missing")
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    require(policy["schema_version"] == "1.0.0", "unexpected policy version")
    require(set(policy["targets"]) == set(TARGETS), "policy must cover M1-M4 and FINAL")
    require(REQUIRED_IDS <= {row["id"] for row in policy["obligations"]},
            "governing policy bundle is incomplete")

    with tempfile.TemporaryDirectory(prefix="draft-governance-") as td:
        project = Path(td) / "project"
        project.mkdir()
        (project / "reviews").mkdir()
        (project / "research_notes").mkdir()
        (project / "research_notes" / "directives.md").write_text(
            "d_style_profile:\n  citation_style: apa\n",
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
        artifact.write_text("# Draft\n\nA governed sentence.\n", encoding="utf-8")
        for target in TARGETS:
            for phase in ("generation", "evaluation"):
                contract = prepare(project, artifact, target, phase)
                require(contract["centroid"]["required"] is True,
                        f"centroid must be mandatory for {target}/{phase}")
                require(REQUIRED_IDS <= {row["id"] for row in contract["obligations"]},
                        f"missing obligations for {target}/{phase}")

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
        generation_envelope = project / "generation.verified.json"
        write_json(generation_envelope, json.loads(generated.stdout))

        generic_centroid = json.loads(json.dumps(generation_receipt))
        for row in generic_centroid["obligations"]:
            if row["id"] == "centroid-generation":
                row["evidence"] = [binding(evidence)]
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

    print("draft_governance_smoketest: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
