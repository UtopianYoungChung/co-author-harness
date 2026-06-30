"""Smoketest for the audit suite.

Runs run_all against the known-bad fixture and asserts that every check_id
class fires at least once. If a future refactor silently drops a detector,
this test fails.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from run_all import audit_target  # noqa: E402

REQUIRED_CHECK_IDS = {
    "ABS-001",  # absolutes
    "EMD-001",  # em-dash density
    "TIC-001",  # not X but Y
    "TIC-002",  # hedged transitions
    "TIC-003",  # demonstrative pivots
    "TIC-004",  # third-person self-reference
    "TIC-005",  # forward-pointer
    "VOI-001",  # there is / there are
    "VOI-002",  # overclaiming verbs
    "VOI-003",  # standard X
    "VOI-004",  # first-class
    "LEN-001",  # sentence length > 60 words
    "PAS-001",  # passive voice
}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    fixture = HERE / "fixtures" / "known_bad.md"
    if not fixture.is_file():
        print(f"[BLOCKER] missing fixture: {fixture}", file=sys.stderr)
        return 1

    report = audit_target(fixture)
    fired = {f.check_id for f in report.findings}
    missing = REQUIRED_CHECK_IDS - fired

    if missing:
        print(f"[BLOCKER] audit suite did not fire expected checks: {sorted(missing)}", file=sys.stderr)
        return 1

    # Locator-fidelity check: LEN-001 must point to the actual long-sentence
    # paragraph in the fixture, not paragraph 1 (a sign the offset bookkeeping
    # is undercounting newlines consumed by the sentence splitter).
    fixture_text = fixture.read_text(encoding="utf-8")
    expected_long_line = next(
        (i + 1 for i, line in enumerate(fixture_text.splitlines())
         if "exceeds the sixty-word threshold" in line),
        None,
    )
    if expected_long_line is None:
        print("[BLOCKER] fixture missing the long-sentence anchor", file=sys.stderr)
        return 1
    len_findings = [f for f in report.findings if f.check_id == "LEN-001"]
    for f in len_findings:
        reported_line = int(f.locator.rsplit(":", 1)[-1])
        if reported_line != expected_long_line:
            print(
                f"[BLOCKER] LEN-001 locator off: reported line {reported_line}, "
                f"expected {expected_long_line} (locator: {f.locator})",
                file=sys.stderr,
            )
            return 1

    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        directives_dir = project_root / "research_notes"
        directives_dir.mkdir(parents=True)
        (directives_dir / "directives.md").write_text(
            "\n".join(
                [
                    "d_style_profile:",
                    "  question_type: conceptual",
                    "  citation_style: turabian_author_date",
                    "  source_role_policy: strict_role_classification",
                    "  evidence_display_policy: standard",
                    "  assistance_disclosure_policy: project_local",
                    "  harness_profile: thesis_qe",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        findings_out = project_root / "reviews" / "findings.json"
        result = subprocess.run(
            [
                sys.executable,
                str(HERE / "run_all.py"),
                str(fixture),
                "--out",
                str(findings_out),
                "--project-root",
                str(project_root),
                "--date",
                "2026-06-29",
            ],
            capture_output=True,
            encoding="utf-8",
            text=True,
        )
        if result.returncode != 0:
            print(f"[BLOCKER] canonical pre-flight failed: {result.stderr}", file=sys.stderr)
            return 1
        profile_out = project_root / "reviews" / "d_style_profile_2026-06-29.json"
        if not findings_out.is_file() or not profile_out.is_file():
            print("[BLOCKER] canonical pre-flight did not write both review artifacts", file=sys.stderr)
            return 1
        profile = json.loads(profile_out.read_text(encoding="utf-8"))
        if profile["resolved_profile"]["harness_profile"] != "thesis_qe":
            print("[BLOCKER] canonical pre-flight lost the declared D-STYLE profile", file=sys.stderr)
            return 1

    print(
        f"OK audit smoketest — {len(report.findings)} findings across "
        f"{len(fired)} distinct check classes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
