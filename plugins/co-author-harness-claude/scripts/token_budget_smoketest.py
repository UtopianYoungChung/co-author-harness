#!/usr/bin/env python3
"""Smoketest for v0.15.0-pre PR-4d — token_budget_check.

Asserts:
  (1) tiktoken is available and the cl100k_base encoder loads.
  (2) The `classify` function returns the correct band at each threshold.
  (3) `build_report` produces a non-trivial report against the live tree
      (>=1 file in every class, finite token counts, always-loaded floor
      is a positive integer).
  (4) The CLI exit code is 0 even when many files breach (the warn-only
      invariant — PR-4d does not block release-gate on budget breaches).
  (5) The top-10 list is sorted by token count descending.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from token_budget_check import (  # noqa: E402
    FILE_CLASSES,
    build_report,
    classify,
    _get_encoder,
)


def test_tiktoken_loads() -> None:
    enc = _get_encoder()
    assert len(enc.encode("hello world")) > 0


def test_classify_thresholds() -> None:
    # warn=120, fail=250 (skills class)
    assert classify(50, 120, 250) == "ok"
    assert classify(120, 120, 250) == "ok"  # exactly at threshold → ok
    assert classify(121, 120, 250) == "warn"
    assert classify(250, 120, 250) == "warn"
    assert classify(251, 120, 250) == "fail"
    assert classify(10000, 120, 250) == "fail"


def test_report_covers_every_class() -> None:
    report = build_report()
    assert report.total_files > 0, "expected non-empty file inventory"
    # Every defined class must appear in by_class
    for cls in FILE_CLASSES:
        assert cls.name in report.by_class, (
            f"class {cls.name!r} missing from report.by_class"
        )
        summary = report.by_class[cls.name]
        # Every class should have at least one file (post-PR-4b minimum)
        assert summary["total"] >= 1, (
            f"class {cls.name!r} has zero files — did the tree shape change?"
        )


def test_always_loaded_floor_is_positive() -> None:
    report = build_report()
    assert report.always_loaded_floor_tokens > 0, (
        "always-loaded floor should sum to a positive token count "
        "(GROUNDING_PROTOCOL.md + CLAUDE.md + MANIFEST.md)"
    )


def test_top10_is_sorted_descending() -> None:
    report = build_report()
    assert len(report.top10_largest) <= 10
    counts = [f.tokens for f in report.top10_largest]
    assert counts == sorted(counts, reverse=True), (
        f"top10_largest not sorted descending: {counts}"
    )


def test_cli_always_exits_zero_warn_only() -> None:
    """The warn-only invariant: even with many breaches, the CLI exits 0
    so release-gate.sh treats it as informational, not blocking."""
    result = subprocess.run(
        [sys.executable, str(HERE / "token_budget_check.py"), "--quiet"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 0, (
        f"warn-only invariant violated: expected exit 0, got "
        f"{result.returncode}; stderr: {result.stderr}"
    )


def test_breaches_carry_threshold_metadata() -> None:
    report = build_report()
    for breach in report.breaches:
        assert breach.warn_threshold > 0
        assert breach.fail_threshold > breach.warn_threshold
        assert breach.status in {"warn", "fail"}, breach.status
        # The status must agree with the token count vs thresholds
        if breach.status == "warn":
            assert breach.warn_threshold < breach.tokens <= breach.fail_threshold
        else:
            assert breach.tokens > breach.fail_threshold


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    tests = [
        test_tiktoken_loads,
        test_classify_thresholds,
        test_report_covers_every_class,
        test_always_loaded_floor_is_positive,
        test_top10_is_sorted_descending,
        test_cli_always_exits_zero_warn_only,
        test_breaches_carry_threshold_metadata,
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
    print(f"OK token_budget_smoketest — {len(tests)}/{len(tests)} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
