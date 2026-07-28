#!/usr/bin/env python3
"""Focused synthetic controls for the governed product-gate adapter."""

from __future__ import annotations

import copy
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable

import run_product_gate as gate
from assignment_c4_fixture_support import exact_tree_state
from c2_evidence_fixture_support import build_activation_fixture
from c2_evidence_validation import canonical_bytes
from jsonschema import Draft202012Validator
from scholarly_assurance_fixture_support import (
    build_qualified_scholarly_from_authorities,
    prepare_synthetic_authorities,
)


ROOT = Path(__file__).resolve().parents[1]


def expect_refusal(project: Path, code: str, call: Callable[[], Any]) -> None:
    before = exact_tree_state(project)
    try:
        call()
    except gate.ProductGateError as exc:
        assert exc.code == code, (code, exc.code, str(exc))
        assert exact_tree_state(project) == before, code
        return
    raise AssertionError(f"expected {code}")


def rewrite_publication(paths: dict[str, Path], value: dict[str, Any]) -> None:
    paths["manifest"].write_bytes(canonical_bytes(value))
    publication = gate._publication(
        paths["manifest"], paths["manifest"].read_bytes(), value["run_id"]
    )
    paths["publication"].write_bytes(canonical_bytes(publication))
    paths["marker"].write_bytes(
        canonical_bytes(
            gate._marker(
                paths["publication"],
                paths["publication"].read_bytes(),
                value["run_id"],
            )
        )
    )


def main() -> int:
    schema = json.loads(gate.SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    cases = 0
    with tempfile.TemporaryDirectory(
        prefix="run-product-gate-c7-", dir=ROOT
    ) as temporary:
        project = Path(temporary) / "project"
        claim_text = (
            "This paper argues a bounded claim because evidence supports the "
            "warrant and explains the stakes. However, a limitation defines "
            "the scope and an alternative explanation. AI-assisted work is disclosed."
        )
        activation = build_activation_fixture(project, artifact_relative="final.md")
        activation.mutate_artifact(
            lambda original: f"{original.rstrip()}\n\n# Synthetic analysis\n\n{claim_text}\n"
        )
        artifact_before = activation.artifact.read_bytes()
        authorities = prepare_synthetic_authorities(
            project,
            activation=activation,
            artifact_relative="final.md",
            label="product-gate-authority",
            claim_text=claim_text,
        )
        fixture = build_qualified_scholarly_from_authorities(
            project,
            authorities=authorities,
            label="product-gate",
            claim_text=claim_text,
            include_dstyle=True,
        )
        assert fixture.artifact.read_bytes() == artifact_before
        assert all(
            not path.exists()
            for path in (
                project / "research_notes/assistance_log.md",
                project / "research_notes/disclosure.md",
                project / "reviews/assistance_log.md",
            )
        )

        mechanics = gate.run_gate(
            mode="mechanics",
            project_root=project,
            artifact=fixture.artifact,
            out_dir=project / "product-gate-mechanics",
            requested_checks=[gate.CHECK_DETERMINISTIC],
        )
        mechanics_value = gate.validate_run_manifest(mechanics["manifest"])
        assert mechanics_value["mode"] == "mechanics"
        assert mechanics_value["lifecycle_eligible"] is False
        assert mechanics_value["scholarly_evaluation"] is None
        expect_refusal(
            project,
            "PRODUCT-GATE-MODE-MISMATCH",
            lambda: gate.validate_run_manifest(
                mechanics["manifest"], require_lifecycle=True
            ),
        )
        cases += 1

        common = {
            "mode": "governed-product",
            "project_root": project,
            "artifact": fixture.artifact,
            "requested_checks": [gate.CHECK_SEMANTIC],
            "wiki_root": fixture.activation.wiki_root,
            "semantic_receipt": fixture.evaluation_semantic_receipt,
            "verifier_transaction": fixture.evaluation_verifier["transaction"],
            "verifier_publication_manifest": fixture.evaluation_verifier[
                "publication_manifest"
            ],
            "verifier_commit_marker": fixture.evaluation_verifier["commit_marker"],
            "semantics_manifest": fixture.semantics_manifest,
        }
        expect_refusal(
            project,
            gate.SCHOLARLY_REQUIRED,
            lambda: gate.run_gate(
                **common,
                out_dir=project / "missing-scholarly",
            ),
        )
        cases += 1

        expect_refusal(
            project,
            "PRODUCT-GATE-EVIDENCE-REQUIRED",
            lambda: gate.run_gate(
                **{
                    **common,
                    "semantic_receipt": fixture.activation.receipt,
                    "verifier_transaction": fixture.generation_verifier["transaction"],
                    "verifier_publication_manifest": fixture.generation_verifier[
                        "publication_manifest"
                    ],
                    "verifier_commit_marker": fixture.generation_verifier[
                        "commit_marker"
                    ],
                    "scholarly_evaluation": fixture.evaluation,
                },
                out_dir=project / "generation-semantic-only",
            ),
        )
        cases += 1

        governed_kwargs = {**common, "scholarly_evaluation": fixture.evaluation}
        governed = gate.run_gate(
            **governed_kwargs,
            out_dir=project / "product-gate-governed",
        )
        governed_value = gate.validate_run_manifest(
            governed["manifest"], require_lifecycle=True
        )
        scholarly = governed_value["scholarly_evaluation"]
        assert set(scholarly) == gate.SCHOLARLY_CORE_FIELDS
        assert scholarly == {
            key: fixture.verified[key] for key in gate.SCHOLARLY_CORE_FIELDS
        }
        assert governed_value["terminal_state"] == "product_qualified"
        assert governed_value["verifier_transaction"]["transaction_id"] == (
            fixture.evaluation_verifier["transaction_id"]
        )
        assert "--scholarly-evaluation" in governed_value["recovery_command"]
        cases += 1

        original_evaluation = fixture.evaluation.read_bytes()
        fixture.evaluation.write_bytes(original_evaluation + b" ")
        try:
            expect_refusal(
                project,
                gate.SCHOLARLY_REQUIRED,
                lambda: gate.run_gate(
                    **governed_kwargs,
                    out_dir=project / "stale-scholarly",
                ),
            )
        finally:
            fixture.evaluation.write_bytes(original_evaluation)
        cases += 1

        original_adapter = gate.validate_scholarly_binding

        def unqualified_adapter(**_: Any) -> dict[str, Any]:
            return {
                **fixture.verified,
                "status": "blocked",
                "evaluation_path": fixture.evaluation,
                "artifact_path": fixture.artifact,
                "dependency_paths": [],
            }

        gate.validate_scholarly_binding = unqualified_adapter
        try:
            expect_refusal(
                project,
                gate.SCHOLARLY_REQUIRED,
                lambda: gate.run_gate(
                    **governed_kwargs,
                    out_dir=project / "unqualified-scholarly",
                ),
            )
        finally:
            gate.validate_scholarly_binding = original_adapter
        cases += 1

        toctou_dir = project / "product-gate-scholarly-toctou"
        assistance_path = project / "research_notes/assistance_log.md"
        assert not assistance_path.exists()

        def mutate_before_marker() -> None:
            assistance_path.write_text(
                "Created during the pre-marker window.\n",
                encoding="utf-8",
                newline="\n",
            )

        try:
            try:
                gate.run_gate(
                    **governed_kwargs,
                    out_dir=toctou_dir,
                    _before_marker=mutate_before_marker,
                )
            except gate.ProductGateError as exc:
                assert exc.code == gate.SCHOLARLY_REQUIRED, exc.code
            else:
                raise AssertionError("pre-marker scholarly drift unexpectedly committed")
        finally:
            assistance_path.unlink(missing_ok=True)
        assert (toctou_dir / "run-manifest.json").is_file()
        assert (toctou_dir / "publication-manifest.json").is_file()
        assert not (toctou_dir / "commit-marker.json").exists()
        recovered_toctou = gate.run_gate(
            **governed_kwargs,
            out_dir=toctou_dir,
            recover=True,
        )
        assert recovered_toctou["marker"].is_file()
        cases += 1

        # The marker boundary must also replay evidence outside the C6
        # dependency closure.  The project manifest is a governed-product
        # input, but deliberately is not a scholarly-evaluation dependency.
        non_c6_dir = project / "product-gate-non-c6-toctou"
        project_manifest = project / "project_manifest.json"
        assert str(project_manifest.resolve()) not in {
            row["path"] for row in fixture.verified["dependencies"]
        }
        project_manifest_bytes = project_manifest.read_bytes()

        def mutate_non_c6_before_marker() -> None:
            project_manifest.write_bytes(project_manifest_bytes + b" ")

        try:
            try:
                gate.run_gate(
                    **governed_kwargs,
                    out_dir=non_c6_dir,
                    _before_marker=mutate_non_c6_before_marker,
                )
            except gate.ProductGateError as exc:
                assert exc.code == "PRODUCT-GATE-EVIDENCE-STALE", exc.code
            else:
                raise AssertionError("pre-marker non-C6 drift unexpectedly committed")
        finally:
            project_manifest.write_bytes(project_manifest_bytes)
        assert (non_c6_dir / "run-manifest.json").is_file()
        assert (non_c6_dir / "publication-manifest.json").is_file()
        assert not (non_c6_dir / "commit-marker.json").exists()
        prepared_manifest = (non_c6_dir / "run-manifest.json").read_bytes()
        prepared_publication = (non_c6_dir / "publication-manifest.json").read_bytes()
        recovered_non_c6 = gate.run_gate(
            **governed_kwargs,
            out_dir=non_c6_dir,
            recover=True,
        )
        assert recovered_non_c6["marker"].is_file()
        assert (non_c6_dir / "run-manifest.json").read_bytes() == prepared_manifest
        assert (
            non_c6_dir / "publication-manifest.json"
        ).read_bytes() == prepared_publication
        gate.validate_run_manifest(
            recovered_non_c6["manifest"], require_lifecycle=True
        )
        cases += 1

        partial_dir = project / "product-gate-partial"
        partial = gate.run_gate(
            **governed_kwargs,
            out_dir=partial_dir,
            _stop_before_marker=True,
        )
        assert partial["manifest"].is_file() and partial["publication"].is_file()
        assert not partial["marker"].exists()
        expect_refusal(
            project,
            "PRODUCT-GATE-TRANSACTION-INCOMPLETE",
            lambda: gate.validate_run_manifest(partial["manifest"]),
        )
        partial_value = json.loads(partial["manifest"].read_text(encoding="utf-8"))
        recovery = subprocess.run(
            partial_value["recovery_command"],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
        assert recovery.returncode == 0, recovery.stdout + recovery.stderr
        assert partial["marker"].is_file()
        gate.validate_run_manifest(partial["manifest"], require_lifecycle=True)
        cases += 1

        # Top-level exact inputs remain independently replayed.  Scholarly
        # evaluation/artifact staleness maps to the frozen C7 refusal; the old
        # semantic verifier retains its own stale-evidence code.
        scholarly_dependency_paths = {
            row["path"] for row in scholarly["dependencies"]
        }
        for row in governed_value["inputs"]:
            input_path = Path(row["path"])
            original = input_path.read_bytes()
            input_path.write_bytes(original + b" ")
            expected = (
                gate.SCHOLARLY_REQUIRED
                if row["path"] in scholarly_dependency_paths
                else "PRODUCT-GATE-EVIDENCE-STALE"
            )
            try:
                expect_refusal(
                    project,
                    expected,
                    lambda: gate.validate_run_manifest(
                        governed["manifest"], require_lifecycle=True
                    ),
                )
            finally:
                input_path.write_bytes(original)
            gate.validate_run_manifest(governed["manifest"], require_lifecycle=True)
            cases += 1

        top_level_paths = {row["path"] for row in governed_value["inputs"]}
        nested = next(
            row
            for row in scholarly["dependencies"]
            if row["path"] not in top_level_paths
            and Path(row["path"]).is_relative_to(project)
            and "scholarly-profile" in Path(row["path"]).name
        )
        nested_path = Path(nested["path"])
        nested_bytes = nested_path.read_bytes()
        nested_path.write_bytes(nested_bytes + b" ")
        try:
            expect_refusal(
                project,
                gate.SCHOLARLY_REQUIRED,
                lambda: gate.validate_run_manifest(
                    governed["manifest"], require_lifecycle=True
                ),
            )
        finally:
            nested_path.write_bytes(nested_bytes)
        gate.validate_run_manifest(governed["manifest"], require_lifecycle=True)
        cases += 1

        # A self-consistent wrapper cannot remove or alter the C6 record.
        original_manifest = json.loads(governed["manifest"].read_text(encoding="utf-8"))
        for label, transform in (
            ("missing", lambda value: value.pop("scholarly_evaluation")),
            (
                "dependency",
                lambda value: value["scholarly_evaluation"]["dependencies"][0].update(
                    {"sha256": "0" * 64}
                ),
            ),
        ):
            forged = copy.deepcopy(original_manifest)
            transform(forged)
            rewrite_publication(governed, forged)
            expect_refusal(
                project,
                gate.SCHOLARLY_REQUIRED,
                lambda: gate.validate_run_manifest(
                    governed["manifest"], require_lifecycle=True
                ),
            )
            rewrite_publication(governed, original_manifest)
            gate.validate_run_manifest(governed["manifest"], require_lifecycle=True)
            cases += 1

    print(f"run_product_gate_smoketest: PASS ({cases} focused cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
