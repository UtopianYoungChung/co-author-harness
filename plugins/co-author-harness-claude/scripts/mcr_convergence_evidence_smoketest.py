#!/usr/bin/env python3
"""Smoketest for v0.15.0-pre PR-3b.2 — MCR convergence evidence advisory.

Asserts:
  (1) `_is_mcr_cleared` behaviour is UNCHANGED in every fixture (identity
      against a hand-computed expectation table — no implicit reference
      to the old implementation).
  (2) `W-MCR-CONVERGENCE-EVIDENCE` fires iff the last two convergence_log
      iteration rows show stability AND both rows carry a non-refine profile.
  (3) The advisory is non-blocking: the exit-code split in main() routes
      W- codes to warnings, so behaviour-identity tests (1) also cover
      "no new BLOCKER from 3b.2."
  (4) Missing / old-schema `profile` produces no advisory and no finding.
  (5) Two-round REFINE stability does NOT fire the advisory (gaming guard).
  (6) Convergence_log row parser handles both pure-iteration logs and
      mixed logs that also contain `- finding_id:` blocks.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from pre_phase_advance_check import (  # noqa: E402
    _compute_mcr_convergence_evidence,
    _is_mcr_cleared,
    _parse_convergence_log_iteration_rows,
)


# ---------------------------------------------------------------------------
# Behaviour-identity expectations for _is_mcr_cleared.
# A hand-built table — does not depend on the function under test. If a
# future refactor regresses _is_mcr_cleared semantics, this fails closed.
# ---------------------------------------------------------------------------

MCR_CLEARED_CASES = [
    # (label, section, default_final_tier, expected)
    ("t3_converged_clears", {"current_tier": "T3_converged"}, "T4", True),
    ("t3_not_locked_blocks", {"current_tier": "T3", "ceiling_locked": False}, "T4", False),
    (
        "ceiling_lock_terminal_clears",
        {
            "current_tier": "T3",
            "ceiling_locked": True,
            "last_approved_tier": "T3",
            "section_ceiling_override": "T3",
        },
        "T4",
        True,
    ),
    (
        "ceiling_lock_but_below_ceiling_blocks",
        {
            "current_tier": "T3",
            "ceiling_locked": True,
            "last_approved_tier": "T2",
            "section_ceiling_override": "T3",
        },
        "T4",
        False,
    ),
    (
        "ceiling_locked_at_manuscript_ceiling",
        {"current_tier": "T2", "ceiling_locked": True, "last_approved_tier": "T2"},
        "T2",
        True,
    ),
]


def test_is_mcr_cleared_behaviour_identity() -> None:
    for label, section, default, expected in MCR_CLEARED_CASES:
        got = _is_mcr_cleared(section, default)
        assert got == expected, f"{label}: expected {expected}, got {got}"


# ---------------------------------------------------------------------------
# Convergence-log parser
# ---------------------------------------------------------------------------

LOG_PURE_ITERATIONS = """
- iteration_index: 0
  profile: deep
  convergence_metric: 0.42
  findings_count_delta: 3
- iteration_index: 1
  profile: structural
  convergence_metric: 0.42
  findings_count_delta: 0
- iteration_index: 2
  profile: structural
  convergence_metric: 0.42
  findings_count_delta: 0
"""

LOG_MIXED_WITH_FINDING_BLOCKS = """
- iteration_index: 0
  profile: deep
  convergence_metric: 0.42
  findings_count_delta: 0
- iteration_index: 1
  profile: deep
  convergence_metric: 0.42
  findings_count_delta: 0
- finding_id: ABC-123
  status: ESCALATED
  current_owner: evaluator
"""

LOG_REFINE_ONLY_STABILITY = """
- iteration_index: 0
  profile: refine
  convergence_metric: 0.99
  findings_count_delta: 0
- iteration_index: 1
  profile: refine
  convergence_metric: 0.99
  findings_count_delta: 0
"""

LOG_MISSING_PROFILE = """
- iteration_index: 0
  convergence_metric: 0.99
  findings_count_delta: 0
- iteration_index: 1
  convergence_metric: 0.99
  findings_count_delta: 0
"""

LOG_SECTION_SCOPED = """
- iteration_index: 0
  section: 1. Introduction
  profile: deep
  convergence_metric: 0.42
  findings_count_delta: 0
- iteration_index: 1
  section: 1. Introduction
  profile: deep
  convergence_metric: 0.42
  findings_count_delta: 0
- iteration_index: 0
  section: 2. Background
  profile: deep
  convergence_metric: 0.99
  findings_count_delta: 0
- iteration_index: 1
  section: 2. Background
  profile: refine
  convergence_metric: 0.99
  findings_count_delta: 0
"""

LOG_NON_ZERO_DELTA = """
- iteration_index: 0
  profile: deep
  convergence_metric: 0.42
  findings_count_delta: 0
- iteration_index: 1
  profile: deep
  convergence_metric: 0.42
  findings_count_delta: 1
"""

LOG_DIVERGENT_METRIC = """
- iteration_index: 0
  profile: deep
  convergence_metric: 0.42
  findings_count_delta: 0
- iteration_index: 1
  profile: deep
  convergence_metric: 0.51
  findings_count_delta: 0
"""

LOG_ONLY_ONE_ROW = """
- iteration_index: 0
  profile: deep
  convergence_metric: 0.42
  findings_count_delta: 0
"""


def test_parser_pure_iterations() -> None:
    rows = _parse_convergence_log_iteration_rows(LOG_PURE_ITERATIONS)
    assert len(rows) == 3, rows
    assert rows[-1]["profile"] == "structural"
    assert rows[-1]["convergence_metric"] == "0.42"


def test_parser_handles_finding_block_separator() -> None:
    rows = _parse_convergence_log_iteration_rows(LOG_MIXED_WITH_FINDING_BLOCKS)
    assert len(rows) == 2
    # The finding_id block must not leak into the iteration row dict
    for r in rows:
        assert "finding_id" not in r
        assert "status" not in r


# ---------------------------------------------------------------------------
# Evidence helper
# ---------------------------------------------------------------------------


def test_evidence_fires_on_non_refine_two_round_stability() -> None:
    assert _compute_mcr_convergence_evidence({}, LOG_PURE_ITERATIONS) is True


def test_evidence_fires_with_mixed_log() -> None:
    assert _compute_mcr_convergence_evidence({}, LOG_MIXED_WITH_FINDING_BLOCKS) is True


def test_evidence_does_not_fire_on_refine_only_stability() -> None:
    """Gaming guard: two stable refine rounds must not authorize evidence."""
    assert _compute_mcr_convergence_evidence({}, LOG_REFINE_ONLY_STABILITY) is False


def test_missing_profile_is_no_evidence_not_finding() -> None:
    assert _compute_mcr_convergence_evidence({}, LOG_MISSING_PROFILE) is False


def test_section_scoped_log_only_fires_for_matching_section() -> None:
    intro = {"heading_path": ["1. Introduction"]}
    background = {"heading_path": ["2. Background"]}
    assert _compute_mcr_convergence_evidence(intro, LOG_SECTION_SCOPED) is True
    assert _compute_mcr_convergence_evidence(background, LOG_SECTION_SCOPED) is False


def test_non_zero_delta_blocks_evidence() -> None:
    assert _compute_mcr_convergence_evidence({}, LOG_NON_ZERO_DELTA) is False


def test_divergent_metric_blocks_evidence() -> None:
    assert _compute_mcr_convergence_evidence({}, LOG_DIVERGENT_METRIC) is False


def test_one_row_is_no_evidence() -> None:
    assert _compute_mcr_convergence_evidence({}, LOG_ONLY_ONE_ROW) is False


def test_empty_log_is_no_evidence() -> None:
    assert _compute_mcr_convergence_evidence({}, "") is False
    assert _compute_mcr_convergence_evidence({}, None) is False


def test_w_prefix_is_required_for_non_blocking() -> None:
    """Belt-and-braces: confirm the code we emit starts with W- so the
    exit-code split in main() routes it to warnings, not errors."""
    from pre_phase_advance_check import check_clause_f  # noqa: F401
    import inspect
    src = inspect.getsource(check_clause_f)
    assert "W-MCR-CONVERGENCE-EVIDENCE" in src, (
        "expected the advisory code to be W-prefixed in check_clause_f source"
    )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    tests = [
        test_is_mcr_cleared_behaviour_identity,
        test_parser_pure_iterations,
        test_parser_handles_finding_block_separator,
        test_evidence_fires_on_non_refine_two_round_stability,
        test_evidence_fires_with_mixed_log,
        test_evidence_does_not_fire_on_refine_only_stability,
        test_missing_profile_is_no_evidence_not_finding,
        test_section_scoped_log_only_fires_for_matching_section,
        test_non_zero_delta_blocks_evidence,
        test_divergent_metric_blocks_evidence,
        test_one_row_is_no_evidence,
        test_empty_log_is_no_evidence,
        test_w_prefix_is_required_for_non_blocking,
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
    print(
        f"OK mcr_convergence_evidence_smoketest — {len(tests)}/{len(tests)} passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
