#!/usr/bin/env python3
"""Focused synthetic controls for the C5 product-gate adapter."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable

import draft_evidence_verifier as verifier
import run_product_gate as gate
from assignment_c4_fixture_support import exact_tree_state
from c2_evidence_fixture_support import build_activation_fixture
from c2_evidence_validation import canonical_bytes
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SEMANTICS = ROOT / "references" / "semantics_manifest.v1.json"


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def expect_refusal(
    project: Path,
    code: str,
    call: Callable[[], Any],
) -> None:
    before = exact_tree_state(project)
    try:
        call()
    except gate.ProductGateError as exc:
        assert exc.code == code, (code, exc.code)
        assert exact_tree_state(project) == before, code
        return
    raise AssertionError(f"expected {code}")


def main() -> int:
    schema = json.loads(gate.SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    with tempfile.TemporaryDirectory(prefix="run-product-gate-c5-", dir=ROOT) as temporary:
        project = Path(temporary) / "project"
        activation = build_activation_fixture(project, artifact_relative="final.md")
        shutil.copyfile(activation.project_manifest, project / "project_manifest.json")
        semantics = project / "semantics_manifest.v1.json"
        shutil.copyfile(SEMANTICS, semantics)

        mechanics = gate.run_gate(
            mode="mechanics",
            project_root=project,
            artifact=activation.artifact,
            out_dir=project / "product-gate-mechanics",
            requested_checks=["deterministic-audit-suite"],
        )
        mechanics_value = gate.validate_run_manifest(mechanics["manifest"])
        assert mechanics_value["mode"] == "mechanics"
        assert mechanics_value["lifecycle_eligible"] is False
        expect_refusal(
            project,
            "PRODUCT-GATE-MODE-MISMATCH",
            lambda: gate.validate_run_manifest(
                mechanics["manifest"], require_lifecycle=True
            ),
        )

        expect_refusal(
            project,
            "PRODUCT-GATE-EVIDENCE-REQUIRED",
            lambda: gate.run_gate(
                mode="governed-product",
                project_root=project,
                artifact=activation.artifact,
                out_dir=project / "missing-evidence",
                requested_checks=["semantic-product-verifier"],
            ),
        )
        expect_refusal(
            project,
            "PRODUCT-GATE-CHECK-UNKNOWN",
            lambda: gate.run_gate(
                mode="governed-product",
                project_root=project,
                artifact=activation.artifact,
                out_dir=project / "unknown-check",
                requested_checks=["unimplemented-check"],
            ),
        )
        expect_refusal(
            project,
            "PRODUCT-GATE-MODE-MISMATCH",
            lambda: gate.run_gate(
                mode="governed-product",
                project_root=project,
                artifact=activation.artifact,
                out_dir=project / "missing-required-check",
                requested_checks=["deterministic-audit-suite"],
            ),
        )

        generation_paths = verifier.publish_verifier_transaction(
            artifact=activation.artifact,
            semantic_receipt=activation.receipt,
            phase="generation",
            project_root=project,
            wiki_root=activation.wiki_root,
            harness_root=ROOT,
            semantics_manifest=semantics,
            out_dir=project / "reviews/.harness/verifier/generation-control",
            requested_independence_level="none",
        )
        verifier.validate_verifier_transaction(
            transaction=generation_paths["transaction"],
            publication_manifest=generation_paths["publication_manifest"],
            commit_marker=generation_paths["commit_marker"],
            artifact=activation.artifact,
            semantic_receipt=activation.receipt,
            project_root=project,
            wiki_root=activation.wiki_root,
            harness_root=ROOT,
            semantics_manifest=semantics,
        )
        expect_refusal(
            project,
            "PRODUCT-GATE-EVIDENCE-REQUIRED",
            lambda: gate.run_gate(
                mode="governed-product",
                project_root=project,
                artifact=activation.artifact,
                out_dir=project / "evaluation-ready-only",
                requested_checks=["semantic-product-verifier"],
                wiki_root=activation.wiki_root,
                semantic_receipt=activation.receipt,
                verifier_transaction=generation_paths["transaction"],
                verifier_publication_manifest=generation_paths["publication_manifest"],
                verifier_commit_marker=generation_paths["commit_marker"],
            ),
        )

        evaluation_receipt = project / "semantic-execution-evaluation-3.json"
        evaluation_value = json.loads(activation.receipt.read_text(encoding="utf-8"))
        evaluation_value["phase"] = "evaluation"
        evaluation_value["role"] = "evaluator"
        write_json(evaluation_receipt, evaluation_value)
        evaluation_paths = verifier.publish_verifier_transaction(
            artifact=activation.artifact,
            semantic_receipt=evaluation_receipt,
            phase="evaluation",
            project_root=project,
            wiki_root=activation.wiki_root,
            harness_root=ROOT,
            semantics_manifest=semantics,
            out_dir=project / "reviews/.harness/verifier/evaluation-control",
            requested_independence_level="none",
        )
        verifier.validate_verifier_transaction(
            transaction=evaluation_paths["transaction"],
            publication_manifest=evaluation_paths["publication_manifest"],
            commit_marker=evaluation_paths["commit_marker"],
            artifact=activation.artifact,
            semantic_receipt=evaluation_receipt,
            project_root=project,
            wiki_root=activation.wiki_root,
            harness_root=ROOT,
            semantics_manifest=semantics,
        )

        governed_kwargs = {
            "mode": "governed-product",
            "project_root": project,
            "artifact": activation.artifact,
            "requested_checks": ["semantic-product-verifier"],
            "wiki_root": activation.wiki_root,
            "semantic_receipt": evaluation_receipt,
            "verifier_transaction": evaluation_paths["transaction"],
            "verifier_publication_manifest": evaluation_paths["publication_manifest"],
            "verifier_commit_marker": evaluation_paths["commit_marker"],
            "semantics_manifest": semantics,
        }
        governed = gate.run_gate(
            **governed_kwargs,
            out_dir=project / "product-gate-governed",
        )
        governed_value = gate.validate_run_manifest(
            governed["manifest"], require_lifecycle=True
        )
        assert governed_value["terminal_state"] == "product_qualified"
        assert governed_value["verifier_transaction"]["transaction_id"] == evaluation_paths["transaction_id"]

        partial_dir = project / "product-gate-partial"
        partial = gate.run_gate(
            **governed_kwargs,
            out_dir=partial_dir,
            _stop_before_marker=True,
        )
        assert partial["manifest"].is_file()
        assert partial["publication"].is_file()
        assert not partial["marker"].exists()
        expect_refusal(
            project,
            "PRODUCT-GATE-TRANSACTION-INCOMPLETE",
            lambda: gate.validate_run_manifest(partial["manifest"]),
        )
        expect_refusal(
            project,
            "PRODUCT-GATE-RECOVERY-REQUIRED",
            lambda: gate.run_gate(
                **{**governed_kwargs, "requested_checks": [
                    "semantic-product-verifier", "deterministic-audit-suite"
                ]},
                out_dir=partial_dir,
                recover=True,
            ),
        )
        recovered = gate.run_gate(
            **governed_kwargs,
            out_dir=partial_dir,
            recover=True,
        )
        assert recovered["marker"].is_file()
        gate.validate_run_manifest(recovered["manifest"], require_lifecycle=True)

        # Every exact governed input is live evidence, not a historical claim.
        # A post-commit byte change must invalidate lifecycle consumption even
        # when the product-gate publication wrapper itself remains intact.
        for row in governed_value["inputs"]:
            input_path = Path(row["path"])
            original = input_path.read_bytes()
            input_path.write_bytes(original + b" ")
            try:
                expect_refusal(
                    project,
                    "PRODUCT-GATE-EVIDENCE-STALE",
                    lambda: gate.validate_run_manifest(
                        governed["manifest"], require_lifecycle=True
                    ),
                )
            finally:
                input_path.write_bytes(original)
            gate.validate_run_manifest(governed["manifest"], require_lifecycle=True)

        # A self-consistent publication wrapper cannot conceal unaccounted
        # requested work.
        manifest_path = governed["manifest"]
        publication_path = governed["publication"]
        marker_path = governed["marker"]
        manifest_bytes = manifest_path.read_bytes()
        publication_bytes = publication_path.read_bytes()
        marker_bytes = marker_path.read_bytes()
        forged = json.loads(manifest_bytes)
        forged["requested_checks"].append("deterministic-audit-suite")
        manifest_path.write_bytes(canonical_bytes(forged))
        publication = gate._publication(
            manifest_path, manifest_path.read_bytes(), forged["run_id"]
        )
        publication_path.write_bytes(canonical_bytes(publication))
        marker_path.write_bytes(canonical_bytes(gate._marker(
            publication_path, publication_path.read_bytes(), forged["run_id"]
        )))
        expect_refusal(
            project,
            "PRODUCT-GATE-CHECK-ACCOUNTING",
            lambda: gate.validate_run_manifest(
                manifest_path, require_lifecycle=True
            ),
        )
        manifest_path.write_bytes(manifest_bytes)
        publication_path.write_bytes(publication_bytes)
        marker_path.write_bytes(marker_bytes)
        gate.validate_run_manifest(manifest_path, require_lifecycle=True)

    print("run_product_gate_smoketest: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
