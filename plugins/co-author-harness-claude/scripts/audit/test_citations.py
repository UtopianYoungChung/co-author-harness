#!/usr/bin/env python3
"""Smoketest for v0.15.0-pre PR-4a — citation auditor.

Asserts:
  (1) The auditor finds and uses the live anchor set from
      references/GROUNDING_PROTOCOL.md (rules 1–7 and 7a per PR-3a).
  (2) known_good.md produces ZERO inviolable findings (resolution OK
      for prose, short, and multi-rule list forms).
  (3) known_bad.md produces inviolable findings for every cited
      bogus rule (99, 42b) across all three citation forms.
  (4) The unqualified "Rule 99 of the international standard" form
      does NOT fire — precision-over-recall on prose false positives.
  (5) Every finding carries severity=inviolable and category=citation
      (the v0.15.0 two-tier vocabulary's truth class).
  (6) The CLI's exit code is 1 when any inviolable finding exists, 0
      otherwise.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from audit_citations import (  # noqa: E402
    audit_file,
    audit_tree,
    load_valid_anchors,
    GP_PATH_DEFAULT,
)

FIXTURES = HERE / "fixtures" / "citations"
KNOWN_GOOD = FIXTURES / "known_good.md"
KNOWN_BAD = FIXTURES / "known_bad.md"


def test_anchors_load_from_live_gp() -> None:
    anchors = load_valid_anchors(GP_PATH_DEFAULT)
    expected_minimum = {"1", "2", "3", "4", "5", "6", "7", "7a"}
    missing = expected_minimum - anchors
    assert not missing, f"live GP missing anchors: {missing}"


def test_known_good_has_no_inviolable_findings() -> None:
    anchors = load_valid_anchors(GP_PATH_DEFAULT)
    findings = audit_file(KNOWN_GOOD, anchors)
    inviolable = [f for f in findings if f.severity == "inviolable"]
    assert not inviolable, (
        f"known_good.md should produce zero inviolable findings, "
        f"got {[(f.locator, f.evidence) for f in inviolable]}"
    )


def test_known_bad_fires_on_every_bogus_citation() -> None:
    anchors = load_valid_anchors(GP_PATH_DEFAULT)
    findings = audit_file(KNOWN_BAD, anchors)
    inviolable = [f for f in findings if f.severity == "inviolable"]
    # Bogus rule IDs in the fixture: 99 and 42b. Each appears in three
    # citation contexts (prose single, short, prose multi-rule). The exact
    # count depends on how multi-rule list expands — the floor is 2*3 = 6
    # findings (each rule cited once per form), but the multi-rule form
    # expands to 2 citations on one line, so we expect ≥ 6 findings.
    cited_rules = {f.rule_ref.split("#gp-")[-1] for f in inviolable}
    assert cited_rules == {"99", "42b"}, (
        f"expected {{99, 42b}}, got {cited_rules}"
    )
    assert len(inviolable) >= 6, (
        f"expected at least 6 inviolable findings across three citation "
        f"forms, got {len(inviolable)}"
    )


def test_findings_carry_correct_severity_and_category() -> None:
    anchors = load_valid_anchors(GP_PATH_DEFAULT)
    findings = audit_file(KNOWN_BAD, anchors)
    for f in findings:
        assert f.severity == "inviolable", (
            f"citation findings must be severity=inviolable, "
            f"got {f.severity} for {f.evidence}"
        )
        assert f.category == "citation", (
            f"citation findings must be category=citation, got {f.category}"
        )


def test_unqualified_rule_n_does_not_false_positive() -> None:
    """The fixture deliberately contains the line 'Rule 99 of the
    international standard'. That must NOT trigger a finding — only
    citations qualified with `GROUNDING_PROTOCOL.md` or `[GP §N]` are
    matched."""
    anchors = load_valid_anchors(GP_PATH_DEFAULT)
    findings = audit_file(KNOWN_GOOD, anchors)
    # The good fixture's bogus line is "Rule 99 of the international
    # standard"; if any finding mentions just that token without the
    # `GROUNDING_PROTOCOL.md` qualifier, that's a false positive.
    for f in findings:
        assert "international" not in f.evidence.lower(), (
            f"false positive on unqualified 'Rule N' prose: {f.evidence}"
        )


def test_audit_tree_skips_grounding_protocol_self() -> None:
    """The auditor must not audit GROUNDING_PROTOCOL.md against itself.
    GROUNDING_PROTOCOL.md is the resolution source; auditing it would
    surface every legitimate Rule heading as a citation candidate."""
    anchors = load_valid_anchors(GP_PATH_DEFAULT)
    references_dir = GP_PATH_DEFAULT.parent
    report = audit_tree(references_dir, anchors)
    for f in report.findings:
        assert "GROUNDING_PROTOCOL.md" not in f.locator, (
            f"audit_tree should skip GROUNDING_PROTOCOL.md, found "
            f"finding at {f.locator}"
        )


def test_cli_exits_1_on_bad_fixture() -> None:
    """End-to-end: invoke the CLI against known_bad.md and confirm
    the process exits non-zero."""
    result = subprocess.run(
        [sys.executable, str(HERE / "audit_citations.py"), str(KNOWN_BAD),
         "--quiet"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 1, (
        f"expected exit 1 on bad fixture, got {result.returncode}; "
        f"stderr: {result.stderr}"
    )


def test_cli_exits_0_on_good_fixture() -> None:
    result = subprocess.run(
        [sys.executable, str(HERE / "audit_citations.py"), str(KNOWN_GOOD),
         "--quiet"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 0, (
        f"expected exit 0 on good fixture, got {result.returncode}; "
        f"stderr: {result.stderr}"
    )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    tests = [
        test_anchors_load_from_live_gp,
        test_known_good_has_no_inviolable_findings,
        test_known_bad_fires_on_every_bogus_citation,
        test_findings_carry_correct_severity_and_category,
        test_unqualified_rule_n_does_not_false_positive,
        test_audit_tree_skips_grounding_protocol_self,
        test_cli_exits_1_on_bad_fixture,
        test_cli_exits_0_on_good_fixture,
    ]
    failures = []
    for t in tests:
        try:
            t()
            print(f"  OK  {t.__name__}")
        except AssertionError as exc:
            failures.append(f"{t.__name__}: {exc}")
            print(f"  FAIL {t.__name__}: {exc}", file=sys.stderr)
    if failures:
        print(f"[BLOCKER] {len(failures)} test(s) failed", file=sys.stderr)
        return 1
    print(f"OK test_citations — {len(tests)}/{len(tests)} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
