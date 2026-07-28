#!/usr/bin/env python3
"""Focused hostile/control test for C7 evaluator-chain identity."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile

from milestone_framework_validate import validate_scholarly_authority_chain


ROOT = Path(__file__).resolve().parents[1]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def _binding(project: Path, path: Path) -> dict[str, object]:
    return {
        "path": path.relative_to(project).as_posix(),
        "sha256": _sha(path),
        "byte_length": path.stat().st_size,
    }


def main() -> int:
    cases = 0
    with tempfile.TemporaryDirectory(
        prefix="scholarly-authority-chain-", dir=ROOT
    ) as raw:
        project = Path(raw)
        generation_claim = project / "authority/generation/claim.json"
        evaluator_claim = project / "authority/evaluator-original/claim.json"
        foreign_claim = project / "authority/evaluator-foreign/claim.json"
        for path, claim_id in (
            (generation_claim, "generation-original"),
            (evaluator_claim, "evaluator-original"),
            (foreign_claim, "evaluator-foreign"),
        ):
            _write(path, {"claim_id": claim_id, "receipt_id": "same-receipt"})
        evaluation = project / "evidence/scholarly-evaluation.json"
        _write(evaluation, {
            "evaluation_dispatch": {"claim": _binding(project, evaluator_claim)}
        })
        dependencies = [
            {"path": str(path.resolve()), "sha256": _sha(path),
             "byte_length": path.stat().st_size}
            for path in (generation_claim, evaluator_claim, foreign_claim, evaluation)
        ]
        scholarly = {
            "evaluation_path": evaluation,
            "dependencies": dependencies,
        }

        def results(selected: Path) -> dict[str, dict[str, object]]:
            return {
                "draft_generation": {
                    "locator": {
                        "receipt_id": "same-receipt",
                        "dispatch_claim": {
                            "root": "project",
                            "path": generation_claim.relative_to(project).as_posix(),
                            "sha256": _sha(generation_claim),
                        },
                    },
                    "transaction": {"transaction_id": "verifier-0123456789abcdef"},
                },
                "draft_evaluation": {
                    "locator": {
                        "receipt_id": "same-receipt",
                        "generation_verifier_transaction_id": "verifier-0123456789abcdef",
                        "dispatch_claim": {
                            "root": "project",
                            "path": selected.relative_to(project).as_posix(),
                            "sha256": _sha(selected),
                        },
                    },
                    "transaction": {"transaction_id": "verifier-fedcba9876543210"},
                },
            }

        validate_scholarly_authority_chain(
            project, results(evaluator_claim), scholarly, "same-receipt"
        )
        cases += 1
        try:
            validate_scholarly_authority_chain(
                project, results(foreign_claim), scholarly, "same-receipt"
            )
        except ValueError as exc:
            assert "another Evaluator claim" in str(exc), exc
        else:
            raise AssertionError("same-receipt foreign Evaluator chain was accepted")
        cases += 1

    print(f"scholarly_authority_chain_smoketest: PASS ({cases} cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
