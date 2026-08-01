#!/usr/bin/env python3
"""Shared fail-closed environment policy for qualification subprocesses."""

from __future__ import annotations

import os
from collections.abc import Mapping


FORBIDDEN_AMBIENT = frozenset({
    "PYTHONUTF8",
    "PYTHONPATH",
    "PYTHONHOME",
    "PYTHONWARNINGS",
    "PYTHONOPTIMIZE",
})
SAFE_PYTHON_ENVIRONMENT = {
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONNOUSERSITE": "1",
}


class QualificationEnvironmentRefusal(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def assert_ambient_clean(environment: Mapping[str, str] | None = None) -> None:
    """Refuse interpreter-routing and optimization controls before spawn."""

    source = os.environ if environment is None else environment
    present = sorted(
        key for key in source
        if key.upper() in FORBIDDEN_AMBIENT
    )
    if present:
        raise QualificationEnvironmentRefusal(
            "QUALIFICATION-ENV-AMBIENT",
            "forbidden ambient controls are present: " + ", ".join(present),
        )


def controlled_environment(
    environment: Mapping[str, str] | None = None,
    delta: Mapping[str, str | None] | None = None,
    dependency_paths: tuple[str, ...] | list[str] | None = None,
    allow_user_site: bool = False,
) -> tuple[dict[str, str], dict[str, str | None]]:
    """Return the child environment and its exact, canonical recorded delta."""

    source = dict(os.environ if environment is None else environment)
    assert_ambient_clean(source)
    requested = {} if delta is None else dict(delta)
    forbidden_delta = sorted(
        key for key in requested
        if key.upper().startswith("PYTHON")
    )
    if forbidden_delta:
        raise QualificationEnvironmentRefusal(
            "QUALIFICATION-ENV-DELTA",
            "caller may not inject Python controls: " + ", ".join(forbidden_delta),
        )
    scrubbed_python = sorted(key for key in source if key.upper().startswith("PYTHON"))
    child = {
        key: value for key, value in source.items()
        if not key.upper().startswith("PYTHON")
    }
    recorded: dict[str, str | None] = {key: None for key in scrubbed_python}
    for key, value in sorted(SAFE_PYTHON_ENVIRONMENT.items()):
        if allow_user_site and key == "PYTHONNOUSERSITE":
            continue
        child[key] = value
        recorded[key] = value
    if dependency_paths is not None:
        qualified = os.pathsep.join(str(value) for value in dependency_paths)
        child["PYTHONPATH"] = qualified
        recorded["PYTHONPATH"] = qualified
    for key, value in sorted(requested.items()):
        if value is None:
            child.pop(key, None)
        else:
            if not isinstance(value, str):
                raise QualificationEnvironmentRefusal(
                    "QUALIFICATION-ENV-DELTA", f"environment value for {key} is not text"
                )
            child[key] = value
        recorded[key] = value
    return child, recorded


__all__ = [
    "FORBIDDEN_AMBIENT",
    "QualificationEnvironmentRefusal",
    "assert_ambient_clean",
    "controlled_environment",
]
