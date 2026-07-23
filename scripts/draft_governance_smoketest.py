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
    result = run(
        "prepare",
        "--project-root", str(project),
        "--artifact", str(artifact),
        "--target", target,
        "--phase", phase,
    )
    require(result.returncode == 0, result.stdout + result.stderr)
    return json.loads(result.stdout)


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

        contract = prepare(project, artifact, "M2", "evaluation")
        contract_path = project / "contract.json"
        contract_path.write_text(json.dumps(contract, sort_keys=True), encoding="utf-8")
        evidence = project / "evidence.txt"
        evidence.write_text("verified\n", encoding="utf-8")
        receipt = {
            "schema_version": "1.0.0",
            "phase": "evaluation",
            "role": "evaluator",
            "contract_sha256": sha(contract_path),
            "artifact": {"path": str(artifact.resolve()), "sha256": sha(artifact)},
            "obligations": [
                {
                    "id": row["id"],
                    "status": "applied",
                    "evidence": [{"path": str(evidence.resolve()), "sha256": sha(evidence)}],
                    "rationale": "fixture evidence",
                }
                for row in contract["obligations"]
                if "evaluation" in row["phases"]
            ],
        }
        receipt_path = project / "receipt.json"
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        verified = run(
            "verify", "--contract", str(contract_path), "--receipt", str(receipt_path),
            "--artifact", str(artifact), "--phase", "evaluation", "--role", "evaluator",
        )
        require(verified.returncode == 0, verified.stdout + verified.stderr)
        require(json.loads(verified.stdout)["status"] == "verified", "receipt did not verify")

        receipt["obligations"] = receipt["obligations"][1:]
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
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
