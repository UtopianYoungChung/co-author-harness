#!/usr/bin/env python3
"""Smoke-test deterministic lifecycle-state rendering and drift detection."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "scripts" / "native_project_bootstrap.py"
RENDERER = ROOT / "scripts" / "render_lifecycle_state.py"
FIXED_TIME = "2026-07-13T18:00:00Z"


def _run(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", "-S", str(script), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _assert_ok(result: subprocess.CompletedProcess[str], label: str) -> None:
    if result.returncode != 0:
        raise AssertionError(f"{label} failed ({result.returncode}):\n{result.stdout}{result.stderr}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="lifecycle-render-") as directory:
        project = Path(directory) / "native-project"
        _assert_ok(_run(
            BOOTSTRAP,
            "--project-root", str(project),
            "--project-name", "native-project",
            "--title", "Native Project",
            "--intended-reader", "requirements engineering researchers",
            "--created-at", "2026-07-13T17:00:00Z",
        ), "native bootstrap")

        view = project / "reviews" / "lifecycle_state.md"
        missing = _run(RENDERER, "--project-root", str(project), "--generated-at", FIXED_TIME, "--check")
        if missing.returncode != 4 or "MF-DERIVED" not in missing.stdout + missing.stderr:
            raise AssertionError(f"missing view was not reported as MF-DERIVED: {missing!r}")
        if view.exists():
            raise AssertionError("--check wrote a missing lifecycle view")

        _assert_ok(_run(RENDERER, "--project-root", str(project), "--generated-at", FIXED_TIME), "render")
        first = view.read_bytes()
        text = first.decode("utf-8")
        for expected in (
            "generated: true",
            "derived_from: reviews/phase_state.json#milestone_framework",
            "source_sha256:",
            f"generated_at: {FIXED_TIME}",
            "| M1 | Establish the project's focus",
            "| in_progress | none | applicable | current | pending | not_ready |",
        ):
            if expected not in text:
                raise AssertionError(f"generated lifecycle view omitted {expected!r}")

        _assert_ok(_run(RENDERER, "--project-root", str(project), "--generated-at", FIXED_TIME), "rerender")
        if view.read_bytes() != first:
            raise AssertionError("fixed inputs and generated_at did not produce byte-identical output")

        edited = text.replace("| in_progress | none |", "| accepted | none |", 1).encode("utf-8")
        view.write_bytes(edited)
        check = _run(RENDERER, "--project-root", str(project), "--generated-at", FIXED_TIME, "--check")
        if check.returncode != 4 or "MF-DERIVED" not in check.stdout + check.stderr:
            raise AssertionError(f"manual edit was not reported as MF-DERIVED: {check!r}")
        if view.read_bytes() != edited:
            raise AssertionError("--check modified a manually edited lifecycle view")

        _assert_ok(_run(RENDERER, "--project-root", str(project), "--generated-at", FIXED_TIME), "repair render")
        if view.read_bytes() != first:
            raise AssertionError("rerender did not repair the exact derived view")
        _assert_ok(
            _run(RENDERER, "--project-root", str(project), "--generated-at", FIXED_TIME, "--check"),
            "exact check",
        )

    print("render_lifecycle_state_smoketest: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
