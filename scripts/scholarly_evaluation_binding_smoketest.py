#!/usr/bin/env python3
"""Focused contract checks for the lifecycle-facing C6 adapter."""

from __future__ import annotations

from pathlib import Path
import tempfile

import scholarly_evaluation
import scholarly_evaluation_binding as adapter


def _expect(code: str, action: object) -> None:
    try:
        action()  # type: ignore[operator]
    except adapter.ScholarlyBindingError as exc:
        assert exc.code == code, (exc.code, code)
    else:
        raise AssertionError(f"expected {code}")


def main() -> int:
    original = scholarly_evaluation.validate_scholarly_evaluation_binding
    with tempfile.TemporaryDirectory(prefix="scholarly-binding-adapter-") as raw:
        project = Path(raw).resolve()
        artifact = project / "artifact.md"
        artifact.write_text("synthetic\n", encoding="utf-8")

        _expect(
            adapter.MISSING,
            lambda: adapter.validate_scholarly_binding(
                project_root=project, artifact=artifact, binding=None
            ),
        )
        _expect(
            adapter.STALE,
            lambda: adapter.validate_scholarly_binding(
                project_root=project, artifact=artifact, binding="present"
            ),
        )

        def refuse(*_args: object, **_kwargs: object) -> dict[str, object]:
            raise scholarly_evaluation.EvaluationRefusal(
                scholarly_evaluation.SET_BINDING_MISSING, "present evidence is missing"
            )

        scholarly_evaluation.validate_scholarly_evaluation_binding = refuse
        try:
            _expect(
                adapter.STALE,
                lambda: adapter.validate_scholarly_binding(
                    project_root=project,
                    artifact=artifact,
                    binding={"evidence_path": "missing.json", "evidence_sha256": "0" * 64},
                ),
            )

            scholarly_evaluation.validate_scholarly_evaluation_binding = (
                lambda *_args, **_kwargs: {
                    "status": "qualified",
                    "judgment_truth_certified": False,
                }
            )
            _expect(
                adapter.STALE,
                lambda: adapter.validate_scholarly_binding(
                    project_root=project,
                    artifact=artifact,
                    binding={"evidence_path": "present.json", "evidence_sha256": "1" * 64},
                ),
            )

            evaluation = project / "reviews" / "evaluation.json"
            evaluation.parent.mkdir(parents=True)
            evaluation.write_text("{}\n", encoding="utf-8")
            dependency = project / "source.md"
            dependency.write_text("source\n", encoding="utf-8")

            def qualify(*_args: object, **_kwargs: object) -> dict[str, object]:
                return {
                    "binding": {
                        "evidence_path": "reviews/evaluation.json",
                        "evidence_sha256": "1" * 64,
                    },
                    "artifact": {
                        "path": "artifact.md",
                        "sha256": "2" * 64,
                        "byte_length": artifact.stat().st_size,
                    },
                    "evaluation_id": "SET-ADAPTER-001",
                    "status": "qualified",
                    "judgment_truth_certified": False,
                    "dependencies": [
                        {
                            "path": str(dependency.resolve()),
                            "sha256": "3" * 64,
                            "byte_length": dependency.stat().st_size,
                        }
                    ],
                }

            scholarly_evaluation.validate_scholarly_evaluation_binding = qualify
            result = adapter.validate_scholarly_binding(
                project_root=project,
                artifact=artifact,
                binding={"evidence_path": "reviews/evaluation.json", "evidence_sha256": "1" * 64},
            )
            assert result["evaluation_path"] == evaluation.resolve()
            assert result["artifact_path"] == artifact.resolve()
            assert result["dependency_paths"] == [dependency.resolve()]
            assert result["dependencies"][0]["path"] == str(dependency.resolve())
        finally:
            scholarly_evaluation.validate_scholarly_evaluation_binding = original

    print("scholarly_evaluation_binding_smoketest: PASS (5 adapter contract cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
