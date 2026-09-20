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
    audit_source_locators,
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
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert result.returncode == 1, (
        f"expected exit 1 on bad fixture, got {result.returncode}; "
        f"stderr: {result.stderr}"
    )


def test_cli_exits_0_on_good_fixture() -> None:
    result = subprocess.run(
        [sys.executable, str(HERE / "audit_citations.py"), str(KNOWN_GOOD),
         "--quiet"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert result.returncode == 0, (
        f"expected exit 0 on good fixture, got {result.returncode}; "
        f"stderr: {result.stderr}"
    )


def test_source_locators_are_unverified_without_a_checks_file() -> None:
    import os
    import tempfile

    with tempfile.TemporaryDirectory(prefix="source-locators-") as tmp:
        root = Path(tmp)
        (root / "manuscript").mkdir()
        plain = root / "manuscript" / "plain.md"
        plain.write_text("A sentence with no citation.", encoding="utf-8")
        assert audit_source_locators(plain.read_text(encoding="utf-8"), plain) == []

        cited = root / "manuscript" / "cited.md"
        cited.write_text("Actors depend on one another (Yu, 2024, p. 211).", encoding="utf-8")
        found = audit_source_locators(cited.read_text(encoding="utf-8"), cited)
        assert [f.check_id for f in found] == ["CIT-LOC-000"], found
        assert found[0].category == "citation" and "UNVERIFIED" in found[0].evidence

        (root / "reviews").mkdir()
        (root / "reviews" / "citation_checks.json").write_text("{}", encoding="utf-8")

        import audit_citations as ac
        import pathlib
        previous = os.environ.get("CITATION_GATE_TOOLS")
        original_home, original_bundled = pathlib.Path.home, ac.BUNDLED_GATE_TOOLS
        os.environ["CITATION_GATE_TOOLS"] = str(root / "no-tools-here")
        pathlib.Path.home = staticmethod(lambda: root / "no-home")
        ac.BUNDLED_GATE_TOOLS = root / "no-bundle"
        try:
            found = audit_source_locators(cited.read_text(encoding="utf-8"), cited)
        finally:
            pathlib.Path.home, ac.BUNDLED_GATE_TOOLS = original_home, original_bundled
            if previous is None:
                os.environ.pop("CITATION_GATE_TOOLS", None)
            else:
                os.environ["CITATION_GATE_TOOLS"] = previous
        by_id = {f.check_id: f for f in found}
        assert set(by_id) == {"CIT-LOC-001", "CIT-LOC-002"}, found
        assert by_id["CIT-LOC-001"].severity == "default", (
            "the environment diagnosis stays advisory: an author cannot fix a missing gate by "
            f"citing better, got {by_id['CIT-LOC-001'].severity}"
        )
        assert by_id["CIT-LOC-002"].severity == "inviolable", (
            "a gate that never executed clears nothing, so the consequence blocks; "
            f"got {by_id['CIT-LOC-002'].severity}"
        )


VERIFY_OK = "checks: 3 bound / 0 failed / 3 total\n"
VALIDATE_OK = "validation (item 9/10): 2 sources\n"


def _stub_tools(root: Path, *, verify=(VERIFY_OK, 0), validate=(VALIDATE_OK, 0)) -> Path:
    """A fake gate-tool directory. Each tool is controlled SEPARATELY.

    The first version of this helper gave both tools identical output, which is exactly why
    the suite missed a validation-only crash: the review of 2026-09-20 reproduced a
    `validate_sources.py` collapse that produced zero findings while verification succeeded.
    Any stub that cannot express an asymmetric failure cannot test for one.
    """
    tools = root / "stub-tools"
    tools.mkdir(exist_ok=True)
    for name, (stdout, code) in (("verify_locators.py", verify), ("validate_sources.py", validate)):
        (tools / name).write_text(
            "import sys\n"
            "sys.argv and None\n"
            f"sys.stdout.write({stdout!r})\n"
            f"raise SystemExit({code})\n",
            encoding="utf-8",
        )
    return tools


def _fixture(root: Path, body: str = "Actors depend on one another (Yu, 2024, p. 211).",
             checks: str | None = '{"sources":{},"checks":[],"claims":[]}') -> Path:
    (root / "manuscript").mkdir(exist_ok=True)
    cited = root / "manuscript" / "cited.md"
    cited.write_text(body, encoding="utf-8")
    if checks is not None:
        (root / "reviews").mkdir(exist_ok=True)
        (root / "reviews" / "citation_checks.json").write_text(checks, encoding="utf-8")
    return cited


def _run(root: Path, cited: Path, **stub_kwargs) -> list:
    import os
    previous = os.environ.get("CITATION_GATE_TOOLS")
    os.environ["CITATION_GATE_TOOLS"] = str(_stub_tools(root, **stub_kwargs))
    try:
        return audit_source_locators(cited.read_text(encoding="utf-8"), cited)
    finally:
        if previous is None:
            os.environ.pop("CITATION_GATE_TOOLS", None)
        else:
            os.environ["CITATION_GATE_TOOLS"] = previous


def test_absent_evidence_blocks_exactly_like_failed_evidence() -> None:
    """Symmetry: skipping the gate must cost what failing it costs (2026-09-19)."""
    import tempfile

    with tempfile.TemporaryDirectory(prefix="gate-symmetry-") as tmp:
        root = Path(tmp)
        cited = _fixture(root)
        text = cited.read_text(encoding="utf-8")

        # (a) no checks file at all
        (root / "reviews" / "citation_checks.json").unlink()
        found = audit_source_locators(text, cited)
        assert [f.check_id for f in found] == ["CIT-LOC-000"], found
        assert found[0].severity == "inviolable", found[0].severity
        _fixture(root)

        # (b) the checks file is unreadable, so the verifier crashes without a verdict
        found = _run(root, cited, verify=("", 1))
        assert {f.check_id for f in found} == {"CIT-LOC-002"}, found
        assert all(f.severity == "inviolable" for f in found), found

        # (c) the gate exits 0 having bound nothing
        found = _run(root, cited, verify=("checks: 0 bound / 0 failed / 0 total\n", 0))
        assert [f.check_id for f in found] == ["CIT-LOC-002"], found
        assert "no checks at all" in found[0].evidence, found[0].evidence

        # (d) a gate that actually bound checks stays clean
        assert _run(root, cited) == [], _run(root, cited)

        # (d2) checks that all FAILED are CIT-LOC-010, never "no checks at all"
        found = _run(root, cited, verify=("checks: 0 bound / 26 failed / 26 total\nFAIL H1 [x]\n", 1))
        assert {f.check_id for f in found} == {"CIT-LOC-010"}, found

        # (e) an UNSUPPORTED element is a disclosed gap, not a skipped gate
        found = _run(root, cited, verify=(VERIFY_OK + "UNSUPPORTED [E1] - no bound quote\n", 0))
        assert {f.check_id for f in found} == {"CIT-LOC-011"}, found
        assert all(f.severity == "default" for f in found), found


def test_a_crash_in_either_tool_blocks_on_its_own() -> None:
    """Reviewer P1, 2026-09-20: a validation-only crash produced zero findings.

    `validate_sources.py` carries Rule 3 items 9-12 — identity, retraction, empty-reference
    and counter-evidence. Its exit status was ignored unless stdout happened to contain a
    recognised finding, so a corrupt field or an incompatible tool version silently cleared
    all four while quote verification succeeded.
    """
    import tempfile

    with tempfile.TemporaryDirectory(prefix="gate-crash-") as tmp:
        root = Path(tmp)
        cited = _fixture(root)

        # validation collapses, verification succeeds
        found = _run(root, cited, validate=("", 1))
        assert [f.check_id for f in found] == ["CIT-LOC-002"], found
        assert found[0].severity == "inviolable", found[0].severity
        assert "validate_sources.py" in found[0].evidence, found[0].evidence

        # and the mirror case, so neither tool can be the silent one
        found = _run(root, cited, verify=("", 3))
        assert [f.check_id for f in found] == ["CIT-LOC-002"], found
        assert "verify_locators.py" in found[0].evidence, found[0].evidence

        # a tool that exits non-zero but DID reach a verdict is not a crash
        found = _run(root, cited, verify=(VERIFY_OK + "UNSUPPORTED [E1] - x\n", 1))
        assert {f.check_id for f in found} == {"CIT-LOC-011"}, found


def test_validation_runs_before_verification() -> None:
    """Rule 3 item 9: validation is a separate gate and it runs first."""
    from audit_citations import GATE_TOOLS

    assert GATE_TOOLS[0] == "validate_sources.py", GATE_TOOLS
    assert GATE_TOOLS[1] == "verify_locators.py", GATE_TOOLS


def test_verifier_is_bound_to_the_audited_manuscript() -> None:
    """Reviewer P1, 2026-09-20: evidence for another document cleared this one.

    The tools read only the checks file, so a checks set built for a different manuscript
    passed unchallenged. The auditor now names the target on the verifier's command line.
    """
    import tempfile

    with tempfile.TemporaryDirectory(prefix="gate-bind-") as tmp:
        root = Path(tmp)
        cited = _fixture(root)
        tools = _stub_tools(root)
        # a stub that reports back the argv it was handed
        (tools / "verify_locators.py").write_text(
            "import sys\n"
            "sys.stdout.write('checks: 1 bound / 0 failed / 1 total\\n')\n"
            "sys.stdout.write('REVIEW argv=' + ' '.join(sys.argv[1:]) + '\\n')\n"
            "raise SystemExit(0)\n",
            encoding="utf-8",
        )
        import os
        previous = os.environ.get("CITATION_GATE_TOOLS")
        os.environ["CITATION_GATE_TOOLS"] = str(tools)
        try:
            found = audit_source_locators(cited.read_text(encoding="utf-8"), cited)
        finally:
            if previous is None:
                os.environ.pop("CITATION_GATE_TOOLS", None)
            else:
                os.environ["CITATION_GATE_TOOLS"] = previous
        argv = " ".join(f.evidence for f in found)
        assert "--citing-document" in argv, found
        assert str(cited) in argv, found


def test_undated_citations_are_still_citations() -> None:
    """Reviewer P2, 2026-09-20: (Author, n.d.) was invisible to the auditor.

    A manuscript whose citations are all undated presented no citation at all, so the
    inviolable CIT-LOC-000 never fired — a one-keystroke bypass of the symmetry fix.
    """
    import tempfile

    with tempfile.TemporaryDirectory(prefix="gate-undated-") as tmp:
        root = Path(tmp)
        cited = _fixture(root, body="Asserted without evidence (Tester, n.d.).", checks=None)
        found = audit_source_locators(cited.read_text(encoding="utf-8"), cited)
        assert [f.check_id for f in found] == ["CIT-LOC-000"], found
        assert found[0].severity == "inviolable", found[0].severity

        # a manuscript with no citation at all is still silent
        plain = root / "manuscript" / "plain.md"
        plain.write_text("A sentence with no citation.", encoding="utf-8")
        assert audit_source_locators(plain.read_text(encoding="utf-8"), plain) == []



def test_gate_tools_are_bundled_with_the_harness() -> None:
    """Reviewer, 2026-09-20: the archive shipped none of the three gate tools.

    An installation without them emitted an advisory CIT-LOC-001 and zero inviolable
    findings, so the citation gate was a property of the author's machine rather than of the
    harness. Resolution order is CITATION_GATE_TOOLS, then the author's working copy, then
    the bundled copy.
    """
    import json
    import os
    from audit_citations import BUNDLED_GATE_TOOLS, GATE_TOOLS, _gate_tools_dir

    for name in GATE_TOOLS:
        assert (BUNDLED_GATE_TOOLS / name).is_file(), f"{name} is not bundled"

    provenance = json.loads((BUNDLED_GATE_TOOLS / "PROVENANCE.json").read_text(encoding="utf-8"))
    import hashlib
    for name, recorded in provenance["sha256"].items():
        live = hashlib.sha256((BUNDLED_GATE_TOOLS / name).read_bytes()).hexdigest()
        assert live == recorded, (
            f"{name} differs from PROVENANCE.json; re-vendor and update the record together"
        )

    import tempfile
    from audit_citations import _resolve_gate_tools

    previous = os.environ.get("CITATION_GATE_TOOLS")
    with tempfile.TemporaryDirectory(prefix="gate-precedence-") as tmp:
        root = Path(tmp)
        complete = _stub_tools(root)                       # a COMPLETE override wins outright
        os.environ["CITATION_GATE_TOOLS"] = str(complete)
        try:
            chosen, problem = _resolve_gate_tools()
            assert chosen == complete, chosen
            assert problem is None, problem

            # An INCOMPLETE override must not disable the gate. Before 2026-09-20 it won
            # anyway and the gate went unexecuted, so one environment variable turned
            # citation checking off; the fallback is now reported, not silent.
            empty = root / "empty-override"
            empty.mkdir()
            os.environ["CITATION_GATE_TOOLS"] = str(empty)
            chosen, problem = _resolve_gate_tools()
            assert chosen != empty, chosen
            assert all((chosen / name).is_file() for name in GATE_TOOLS), chosen
            assert problem and "CITATION_GATE_TOOLS" in problem and "fell back" in problem, problem
        finally:
            if previous is None:
                os.environ.pop("CITATION_GATE_TOOLS", None)
            else:
                os.environ["CITATION_GATE_TOOLS"] = previous

    import pathlib
    original_home = pathlib.Path.home
    os.environ.pop("CITATION_GATE_TOOLS", None)
    pathlib.Path.home = staticmethod(lambda: pathlib.Path("C:/no-such-home"))
    try:
        assert _gate_tools_dir() == BUNDLED_GATE_TOOLS, _gate_tools_dir()
    finally:
        pathlib.Path.home = original_home
        if previous is not None:
            os.environ["CITATION_GATE_TOOLS"] = previous


def test_an_unexecuted_gate_names_the_environment_and_still_blocks() -> None:
    """A missing PyMuPDF is an environment fault, and it clears nothing either way.

    The diagnosis stays separate from a citation error - an author cannot fix a missing
    dependency by citing better - but the reviewer's point on 2026-09-20 stands: a gate that
    did not execute cannot authorise clearance. So CIT-LOC-001 explains the machine and
    CIT-LOC-003 blocks. Before this, GATE_UNAVAILABLE produced advisory findings only.
    """
    import tempfile

    with tempfile.TemporaryDirectory(prefix="gate-unavailable-") as tmp:
        root = Path(tmp)
        cited = _fixture(root)
        found = _run(root, cited,
                     verify=("GATE_UNAVAILABLE: PyMuPDF (fitz) is not installed\n", 3))
        by_id = {f.check_id: f for f in found}
        assert set(by_id) == {"CIT-LOC-001", "CIT-LOC-003"}, found
        assert by_id["CIT-LOC-001"].severity == "default", by_id["CIT-LOC-001"].severity
        assert "environment fault" in by_id["CIT-LOC-001"].evidence, by_id["CIT-LOC-001"].evidence
        assert by_id["CIT-LOC-003"].severity == "inviolable", by_id["CIT-LOC-003"].severity
        assert "clears nothing" in by_id["CIT-LOC-003"].evidence, by_id["CIT-LOC-003"].evidence

        # a crash with no marker still blocks
        found = _run(root, cited, verify=("", 3))
        assert [f.check_id for f in found] == ["CIT-LOC-002"], found
        assert found[0].severity == "inviolable", found[0].severity


def test_uncovered_citations_are_relayed_and_block() -> None:
    """Reviewer R1, 2026-09-20: the verifier printed UNCOVERED and nobody read it.

    A cited sentence no check covers is a citation with no evidence — the same state
    CIT-LOC-000 describes for a whole manuscript — so it blocks for the same reason. Before
    this the verifier exited 1 reporting UNCOVERED and the auditor returned no finding at all,
    which made the whole coverage inventory decorative at the harness layer.
    """
    import tempfile

    with tempfile.TemporaryDirectory(prefix="gate-uncovered-") as tmp:
        root = Path(tmp)
        cited = _fixture(root)
        found = _run(root, cited, verify=(
            VERIFY_OK + "UNCOVERED L2: A second claim nobody checked (Other, 2025, p. 9).\n", 1))
        by_id = {f.check_id: f for f in found}
        assert set(by_id) == {"CIT-LOC-014"}, found
        assert by_id["CIT-LOC-014"].severity == "inviolable", by_id["CIT-LOC-014"].severity
        assert "UNCOVERED" in by_id["CIT-LOC-014"].evidence, by_id["CIT-LOC-014"].evidence


def test_exit_status_and_reported_outcome_must_agree() -> None:
    """A summary line proves the tool had an opinion, not that the opinion was understood.

    The auditor relays a tool's conclusions. If the tool says something went wrong and the
    relay finds nothing to report, or the tool exits clean while reporting a failure, the two
    disagree and the run is not evidence of anything.
    """
    import tempfile

    with tempfile.TemporaryDirectory(prefix="gate-agreement-") as tmp:
        root = Path(tmp)
        cited = _fixture(root)

        # non-zero exit, nothing the auditor recognises
        found = _run(root, cited, verify=(VERIFY_OK, 1))
        assert [f.check_id for f in found] == ["CIT-LOC-002"], found
        assert found[0].severity == "inviolable", found[0].severity
        assert "disagree" in found[0].evidence, found[0].evidence

        # the same asymmetry on the validation side
        found = _run(root, cited, validate=(VALIDATE_OK, 1))
        assert [f.check_id for f in found] == ["CIT-LOC-002"], found
        assert "validate_sources.py" in found[0].evidence, found[0].evidence

        # clean exit while reporting a failure
        found = _run(root, cited, verify=(VERIFY_OK + "FAIL H1 [x]\n", 0))
        by_id = {f.check_id for f in found}
        assert by_id == {"CIT-LOC-010", "CIT-LOC-002"}, found
        agreement = [f for f in found if f.check_id == "CIT-LOC-002"][0]
        assert agreement.severity == "inviolable", agreement.severity
        assert "exited 0" in agreement.evidence, agreement.evidence

        # a clean run that reports only advisory results is not a disagreement
        found = _run(root, cited, verify=(VERIFY_OK + "DISCLOSE MAPPED [E1] via C1\n", 0))
        assert [f.check_id for f in found] == ["CIT-LOC-012"], found

        # REVIEW-only validation legitimately exits 2
        found = _run(root, cited, validate=(VALIDATE_OK + "REVIEW 10 x: no retraction lookup\n", 2))
        assert [f.check_id for f in found] == ["CIT-LOC-013"], found


def test_citation_syntax_agrees_between_auditor_and_verifier() -> None:
    """Reviewer R4, 2026-09-20: the two inventories admitted different citation forms.

    The auditor recognised numeric and LaTeX citations; the verifier's coverage inventory saw
    only parenthetical author-year and n.d. forms. A manuscript could therefore be "cited" as
    far as the auditor was concerned while the citation was invisible to coverage, and an
    unsupported numeric claim passed. Whatever one admits, the other must admit.
    """
    import importlib.util

    from audit_citations import BUNDLED_GATE_TOOLS, SOURCE_CITATION_RE

    spec = importlib.util.spec_from_file_location("vl", BUNDLED_GATE_TOOLS / "verify_locators.py")
    vl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vl)

    forms = [
        "Actors depend on one another (Yu, 2024, p. 211).",
        "A claim with no date (Tester, n.d.).",
        "A grouped one (Yu, 2024; Ratto et al., 2026, pp. 2-3).",
        "A numeric one [3].",
        "A numeric range [3-5].",
        "A numeric list [3,4].",
        r"A latex one \citep{yu2024}.",
        r"A latex variant \cite{yu2024,ratto2026}.",
    ]
    for text in forms:
        auditor = bool(SOURCE_CITATION_RE.search(text))
        verifier = bool(vl.CITATION_RE.search(text))
        assert auditor == verifier, (
            f"citation syntax disagreement on {text!r}: auditor={auditor}, verifier={verifier}. "
            "A form only one of them sees is a citation that can escape coverage"
        )

    # and neither may fire on prose that carries no citation
    for text in ["A sentence with no citation at all.", "A year mentioned in 2024 without brackets."]:
        assert not SOURCE_CITATION_RE.search(text), text
        assert not vl.CITATION_RE.search(text), text


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
        test_source_locators_are_unverified_without_a_checks_file,
        test_absent_evidence_blocks_exactly_like_failed_evidence,
        test_a_crash_in_either_tool_blocks_on_its_own,
        test_validation_runs_before_verification,
        test_verifier_is_bound_to_the_audited_manuscript,
        test_undated_citations_are_still_citations,
        test_gate_tools_are_bundled_with_the_harness,
        test_an_unexecuted_gate_names_the_environment_and_still_blocks,
        test_uncovered_citations_are_relayed_and_block,
        test_exit_status_and_reported_outcome_must_agree,
        test_citation_syntax_agrees_between_auditor_and_verifier,
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
