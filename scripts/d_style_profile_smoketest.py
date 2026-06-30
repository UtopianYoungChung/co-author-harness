#!/usr/bin/env python3
"""Smoketest for the D-STYLE profile routing check."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHECK = HERE / "d_style_profile_check.py"


def run_check(project_root: Path, *, strict: bool = False) -> tuple[int, dict]:
    cmd = [
        sys.executable,
        str(CHECK),
        "--project-root",
        str(project_root),
        "--date",
        "2026-06-29",
    ]
    if strict:
        cmd.append("--strict-exit")
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"stdout was not JSON: {result.stdout!r}") from exc
    return result.returncode, payload


def write_directives(project_root: Path, body: str) -> None:
    directives = project_root / "research_notes" / "directives.md"
    directives.parent.mkdir(parents=True, exist_ok=True)
    directives.write_text(body, encoding="utf-8")


def test_valid_thesis_qe_profile_routes_obligations() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        write_directives(
            project,
            """# Directives

d_style_profile:
  question_type: mixed
  citation_style: turabian_author_date
  source_role_policy: strict_role_classification
  evidence_display_policy: visual_ethics_required
  assistance_disclosure_policy: project_local
  harness_profile: thesis_qe
""",
        )
        code, payload = run_check(project)
        assert code == 0
        assert payload["verdict"] == "CLEAN"
        assert payload["profile_declared"] is True
        ids = set(payload["active_obligation_ids"])
        assert "candidate_vs_canonical_status" in ids
        assert "advisor_committee_constraints" in ids
        assert "visual_evidence_ethics" in ids
        report = project / "reviews" / "d_style_profile_2026-06-29.json"
        data = json.loads(report.read_text(encoding="utf-8"))
        assert data["resolved_profile"]["harness_profile"] == "thesis_qe"


def test_absent_profile_inherits_defaults() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        code, payload = run_check(project)
        assert code == 0
        assert payload["verdict"] == "ADVISORY"
        assert payload["profile_declared"] is False
        assert payload["resolved_profile"]["harness_profile"] == "standard_research_review"
        ids = set(payload["active_obligation_ids"])
        assert "claim_reason_evidence_warrant" in ids


def test_bad_enum_is_strict_blocker() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        write_directives(
            project,
            """# Directives

d_style_profile:
  question_type: mystical
  citation_style: turabian_author_date
  source_role_policy: strict_role_classification
  evidence_display_policy: standard
  assistance_disclosure_policy: project_local
  harness_profile: thesis_qe
""",
        )
        code, payload = run_check(project, strict=True)
        assert code == 2
        assert payload["verdict"] == "BLOCKER"
        report = project / "reviews" / "d_style_profile_2026-06-29.json"
        data = json.loads(report.read_text(encoding="utf-8"))
        codes = {finding["code"] for finding in data["findings"]}
        assert "DSTYLE_PROFILE_BAD_ENUM" in codes


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    tests = [
        test_valid_thesis_qe_profile_routes_obligations,
        test_absent_profile_inherits_defaults,
        test_bad_enum_is_strict_blocker,
    ]
    failures: list[str] = []
    for test in tests:
        try:
            test()
            print(f"  OK  {test.__name__}")
        except AssertionError as exc:
            failures.append(f"{test.__name__}: {exc}")
            print(f"  FAIL {test.__name__}: {exc}", file=sys.stderr)
    if failures:
        print(f"[BLOCKER] {len(failures)} test(s) failed", file=sys.stderr)
        return 1
    print(f"OK d_style_profile_smoketest - {len(tests)}/{len(tests)} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
