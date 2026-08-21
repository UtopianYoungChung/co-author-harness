#!/usr/bin/env python3
"""Regression contract for one fixture authority across every gate surface."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
RUNNER_REL = "scripts/analysis/fixture_runner.py"
INFRA_REL = "scripts/analysis/fixture_infrastructure_check.py"


def _load_registry() -> set[str]:
    path = ROOT / RUNNER_REL
    spec = importlib.util.spec_from_file_location("fixture_runner_authority", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return set(module.REGISTRY)


def _require_invocation(text: str, rel: str, surface: str, *, no_write: bool) -> None:
    name = re.escape(Path(rel).name)
    pattern = rf"python(?:3)?[^\n]*{name}[^\n]*"
    matches = re.findall(pattern, text)
    assert matches, f"{surface} does not invoke {rel}"
    if no_write:
        assert any("--no-write" in match for match in matches), (
            f"{surface} must run the corpus without rewriting committed evidence"
        )


def main() -> int:
    registry = _load_registry()
    assert "scripts/fixture_authority_smoketest.py" in registry
    for required in (
        "scripts/phase_state_validator_smoketest.py",
        "scripts/artefact_frontmatter_smoketest.py",
        "scripts/paragraph_hash_map_smoketest.py",
        "scripts/subprocess_text_policy_smoketest.py",
    ):
        assert required in registry, f"fixture registry missing {required}"

    docs = {
        "AGENTS.md": (ROOT / "AGENTS.md").read_text(encoding="utf-8"),
        "README.md": (ROOT / "README.md").read_text(encoding="utf-8"),
    }
    for name, text in docs.items():
        _require_invocation(text, INFRA_REL, name, no_write=False)
        _require_invocation(text, RUNNER_REL, name, no_write=False)

    surfaces = {
        "CI": (ROOT / ".github/workflows/structural-checks.yml").read_text(
            encoding="utf-8"
        ),
        "release gate": (ROOT / "scripts/release-gate.sh").read_text(
            encoding="utf-8"
        ),
    }
    for name, text in surfaces.items():
        _require_invocation(text, INFRA_REL, name, no_write=False)
        _require_invocation(text, RUNNER_REL, name, no_write=True)
        duplicates = sorted(
            rel for rel in registry
            if Path(rel).name in text and rel != "scripts/fixture_authority_smoketest.py"
        )
        assert not duplicates, f"{name} duplicates registry-owned suites: {duplicates}"

    release = surfaces["release gate"]
    for retired_inline in (
        "PS_FIXTURE_PASS=",
        "AF_PASS=(",
        "PHM_TMP1=",
        "MILESTONE_FRAMEWORK_TESTS=(",
    ):
        assert retired_inline not in release, (
            f"release gate still owns inline fixture logic: {retired_inline}"
        )

    capability_check = (ROOT / "scripts/capability-contract-check.py").read_text(
        encoding="utf-8"
    )
    assert "fixture_registry =" not in capability_check, (
        "capability evidence still uses a source-text registry surrogate"
    )
    assert "registered_fixture_paths" in capability_check, (
        "capability evidence is not bound to structured registry membership"
    )

    print(f"PASS: one registry drives local, CI, and release ({len(registry)} suites)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
