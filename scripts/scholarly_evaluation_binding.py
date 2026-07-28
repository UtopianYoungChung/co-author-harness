#!/usr/bin/env python3
"""Lifecycle-facing error mapping for the authoritative C6 binding API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import scholarly_evaluation


class ScholarlyBindingError(RuntimeError):
    """Typed internal failure mapped to each consumer's frozen refusal code."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        cause_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.cause_code = cause_code
        self.details = dict(details or {})


MISSING = "SCHOLARLY-EVIDENCE-MISSING"
STALE = "SCHOLARLY-EVIDENCE-STALE"


def validate_scholarly_binding(
    *, project_root: Path, artifact: Path, binding: Any
) -> dict[str, Any]:
    """Delegate exact verification and dependency discovery to C6."""

    if binding is None:
        raise ScholarlyBindingError(MISSING, "scholarly_evaluation binding is absent")
    if not isinstance(binding, dict):
        raise ScholarlyBindingError(
            STALE,
            "scholarly_evaluation binding is present but malformed",
            cause_code=scholarly_evaluation.SET_SCHEMA,
        )
    try:
        result = scholarly_evaluation.validate_scholarly_evaluation_binding(
            project_root,
            artifact,
            binding,
        )
    except scholarly_evaluation.EvaluationRefusal as exc:
        raise ScholarlyBindingError(
            STALE,
            f"{exc.code}: {exc}",
            cause_code=exc.code,
            details=exc.details,
        ) from exc
    if (
        result.get("status") != "qualified"
        or result.get("judgment_truth_certified") is not False
    ):
        raise ScholarlyBindingError(
            STALE,
            "scholarly evaluation is not lifecycle-qualified",
            cause_code=scholarly_evaluation.SET_SCHEMA,
        )
    try:
        normalized_binding = dict(result["binding"])
        normalized_artifact = dict(result["artifact"])
        dependencies = [dict(row) for row in result["dependencies"]]
        root = project_root.resolve()
        evaluation_path = (root / normalized_binding["evidence_path"]).resolve()
        artifact_path = (root / normalized_artifact["path"]).resolve()
        evaluation_path.relative_to(root)
        artifact_path.relative_to(root)
        if any(not Path(row["path"]).is_absolute() for row in dependencies):
            raise ValueError("dependency path is not absolute")
    except (KeyError, TypeError, ValueError, OSError) as exc:
        raise ScholarlyBindingError(
            STALE,
            f"scholarly evaluation returned a malformed lifecycle result: {exc}",
            cause_code=scholarly_evaluation.SET_SCHEMA,
        ) from exc
    return {
        **result,
        "binding": normalized_binding,
        "artifact": normalized_artifact,
        "evaluation_path": evaluation_path,
        "artifact_path": artifact_path,
        "dependencies": dependencies,
        "dependency_paths": [Path(row["path"]) for row in dependencies],
    }


__all__ = [
    "MISSING",
    "STALE",
    "ScholarlyBindingError",
    "validate_scholarly_binding",
]
