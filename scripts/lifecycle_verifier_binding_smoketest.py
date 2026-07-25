#!/usr/bin/env python3
"""Focused C5 lifecycle consumption of C3/C4 verifier transactions."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from pathlib import Path

import draft_evidence_verifier as verifier
from assignment_dispatch_claim_smoketest import build_control


ROOT = Path(__file__).resolve().parents[1]
SEMANTICS = ROOT / "references" / "semantics_manifest.v1.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def binding(project: Path, path: Path, root: str = "project") -> dict[str, str]:
    base = project if root == "project" else ROOT
    return {"root": root, "path": path.resolve().relative_to(base).as_posix(), "sha256": sha(path)}


def write_locator(project: Path, facts: dict, phase: str) -> Path:
    generation = phase == "generation"
    transaction = project / (
        facts["generation_transaction"] if generation else facts["evaluation_phase_transaction"]
    )
    publication = project / (
        facts["generation_manifest"] if generation else facts["evaluation_phase_manifest"]
    )
    marker = project / (
        facts["generation_marker"] if generation else facts["evaluation_phase_marker"]
    )
    semantic = project / (
        facts["semantic_receipt"] if generation else facts["evaluation_phase_semantic"]
    )
    claim = project / (facts["generation_claim"] if generation else facts["evaluation_claim"])
    consumption = project / (
        facts["generation_consumption"] if generation else facts["evaluation_consumption"]
    )
    wiki_root = Path(facts["wiki_root"]).resolve()
    wiki_base = project if wiki_root.is_relative_to(project) else ROOT
    wiki_kind = "project" if wiki_base == project else "harness"
    locator = project / "reviews/.harness/lifecycle" / f"{phase}.json"
    locator.parent.mkdir(parents=True, exist_ok=True)
    value = {
        "schema_version": "1.0.0",
        "binding_type": "lifecycle_verifier_transaction",
        "phase": phase,
        "product_disposition": "evaluation_ready" if generation else "product_qualified",
        "target": facts["target"],
        "receipt_id": facts["receipt_id"],
        "transaction": binding(project, transaction),
        "publication_manifest": binding(project, publication),
        "commit_marker": binding(project, marker),
        "semantic_receipt": binding(project, semantic),
        "wiki_root": {
            "root": wiki_kind,
            "path": wiki_root.relative_to(wiki_base).as_posix(),
            "manifest_sha256": sha(wiki_root / "manifest.json"),
        },
        "semantics_manifest": binding(project, SEMANTICS, "harness"),
        "dispatch_claim": binding(project, claim),
        "dispatch_consumption": binding(project, consumption),
        "generation_verifier_transaction_id": (
            None if generation else facts["generation_claim_value"].get("claim_id")
        ),
    }
    if not generation:
        generation_value = json.loads((project / facts["generation_transaction"]).read_text(encoding="utf-8"))
        value["generation_verifier_transaction_id"] = generation_value["transaction_id"]
    locator.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return locator


def expect(code: str, call) -> None:
    try:
        call()
    except verifier.VerifierError as exc:
        assert exc.code == code, (code, exc.code, str(exc))
    else:
        raise AssertionError(f"expected {code}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="c5-lifecycle-verifier-") as td:
        base = Path(td)
        control = base / "control" / "project"
        facts = build_control(control)
        generation = write_locator(control, facts, "generation")
        evaluation = write_locator(control, facts, "evaluation")
        for locator, phase, disposition in (
            (generation, "generation", "evaluation_ready"),
            (evaluation, "evaluation", "product_qualified"),
        ):
            result = verifier.validate_lifecycle_verifier_binding(
                locator=locator,
                artifact=control / facts["artifact"],
                project_root=control,
                harness_root=ROOT,
                expected_phase=phase,
                expected_disposition=disposition,
            )
            assert result["transaction"]["product_disposition"] == disposition
            assert len(result["dependencies"]) >= 15

        stale = base / "stale" / "project"
        shutil.copytree(control, stale)
        (stale / facts["artifact"]).write_bytes(b"stale artifact\n")
        expect(
            "EVIDENCE-TOCTOU",
            lambda: verifier.validate_lifecycle_verifier_binding(
                locator=stale / generation.relative_to(control), artifact=stale / facts["artifact"],
                project_root=stale, harness_root=ROOT, expected_phase="generation",
                expected_disposition="evaluation_ready",
            ),
        )

        missing_marker = base / "missing-marker" / "project"
        shutil.copytree(control, missing_marker)
        (missing_marker / facts["generation_marker"]).unlink()
        expect(
            "LIFECYCLE-EVIDENCE-STALE",
            lambda: verifier.validate_lifecycle_verifier_binding(
                locator=missing_marker / generation.relative_to(control),
                artifact=missing_marker / facts["artifact"], project_root=missing_marker,
                harness_root=ROOT, expected_phase="generation",
                expected_disposition="evaluation_ready",
            ),
        )

        wrong = base / "wrong-disposition" / "project"
        shutil.copytree(control, wrong)
        locator = wrong / evaluation.relative_to(control)
        value = json.loads(locator.read_text(encoding="utf-8"))
        value["product_disposition"] = "evaluation_ready"
        locator.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        expect(
            "LIFECYCLE-EVIDENCE-INVALID",
            lambda: verifier.validate_lifecycle_verifier_binding(
                locator=locator, artifact=wrong / facts["artifact"], project_root=wrong,
                harness_root=ROOT, expected_phase="evaluation",
                expected_disposition="product_qualified",
            ),
        )

    print("lifecycle_verifier_binding_smoketest: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
