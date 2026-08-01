#!/usr/bin/env python3
"""Smoketest for v0.15.0-pre PR-4d — token_budget_check.

Asserts:
  (1) tiktoken is available and the cl100k_base encoder loads.
  (2) The `classify` function returns the correct band at each threshold.
  (3) `build_report` produces a non-trivial report against the live tree
      (>=1 file in every class, finite token counts, always-loaded floor
      is a positive integer).
  (4) The CLI exits 0 for the unchanged immutable baseline; ratchet blockers
      are independently exercised and require non-zero release behavior.
  (5) The top-10 list is sorted by token count descending.
"""

from __future__ import annotations

import subprocess
import sys
from copy import deepcopy
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


def test_cli_accepts_unchanged_baseline() -> None:
    """Historical debt is allowed only when it does not grow."""
    result = subprocess.run(
        [sys.executable, str(HERE / "token_budget_check.py"), "--quiet"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert result.returncode == 0, (
        f"unchanged baseline should pass: expected exit 0, got "
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


def test_ratchet_contract_is_present() -> None:
    import token_budget_check as module
    required = {
        "immutable_baseline", "new_breach_refused", "existing_breach_growth_refused",
        "always_loaded_floor_growth_refused", "unknown_policy_refused",
        "encoder_load_graph_mismatch_refused", "expired_exception_refused",
        "ownerless_exception_refused",
    }
    advertised = set(getattr(module, "RATCHET_CONTRACT", ()))
    assert required <= advertised, f"missing ratchet contracts: {sorted(required-advertised)}"


def test_ratchet_refusals_are_behavioral() -> None:
    import token_budget_check as module
    policy = module._load_policy()
    baseline = {
        "skills/new/SKILL.md": module.FileReport(
            "skills/new/SKILL.md", "skills", 120, 120, 250, "ok"
        ),
        "skills/debt/SKILL.md": module.FileReport(
            "skills/debt/SKILL.md", "skills", 300, 120, 250, "fail"
        ),
    }
    report = module.BudgetReport(
        files=[
            module.FileReport("skills/new/SKILL.md", "skills", 121, 120, 250, "warn"),
            module.FileReport("skills/debt/SKILL.md", "skills", 301, 120, 250, "fail"),
        ],
        always_loaded_floor_tokens=15275,
    )
    original = module._baseline_reports
    module._baseline_reports = lambda _policy, _encoder: (baseline, 15274)
    try:
        blockers = module._ratchet_blockers(report, policy, object())
    finally:
        module._baseline_reports = original
    assert {row["code"] for row in blockers} == {
        "TOKEN-BUDGET-NEW-BREACH",
        "TOKEN-BUDGET-DEBT-GROWTH",
        "TOKEN-BUDGET-FLOOR-GROWTH",
    }
    for owner, expiry, code in (
        ("", "2099-01-01T00:00:00Z", "TOKEN-BUDGET-EXCEPTION-OWNER-MISSING"),
        ("skill owners", "2000-01-01T00:00:00Z", "TOKEN-BUDGET-EXCEPTION-EXPIRED"),
    ):
        bad = deepcopy(policy)
        bad["exceptions"] = [{
            "path": "skills/debt/SKILL.md", "owner": owner,
            "expires_at": expiry, "max_tokens": 400, "reason": "fixture",
        }]
        try:
            module._validated_exceptions(bad)
        except module.TokenBudgetError as exc:
            assert code in str(exc), exc
        else:
            raise AssertionError(f"{code} was accepted")
    schema = module.json.loads(module.POLICY_SCHEMA_PATH.read_text(encoding="utf-8"))
    for mutate, code in (
        (lambda value: value.update(schema_version="token-budget-policy/999"),
         "TOKEN-BUDGET-POLICY-UNKNOWN"),
        (lambda value: value["classes"].update({"unknown surface": {"warn_tokens": 1, "fail_tokens": 2}}),
         "TOKEN-BUDGET-POLICY-UNKNOWN"),
        (lambda value: value["ownership"].append({"prefix": "skills/", "owner": "another owner"}),
         "TOKEN-BUDGET-POLICY-UNKNOWN"),
        (lambda value: value.update(ownership=[
            row for row in value["ownership"] if row["prefix"] != "__always_loaded_floor__"
        ]), "TOKEN-BUDGET-POLICY-UNKNOWN"),
        (lambda value: value["encoder"].update(version="0.11.0"),
         "TOKEN-BUDGET-ENCODER-MISMATCH"),
        (lambda value: value["load_graph"].update(always_loaded=["references/CLAUDE.md"]),
         "TOKEN-BUDGET-LOAD-GRAPH-MISMATCH"),
    ):
        bad = deepcopy(policy)
        mutate(bad)
        try:
            module._validate_policy_value(bad, schema)
        except module.TokenBudgetError as exc:
            assert code in str(exc), exc
        else:
            raise AssertionError(f"{code} was accepted")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    tests = [
        test_tiktoken_loads,
        test_classify_thresholds,
        test_report_covers_every_class,
        test_always_loaded_floor_is_positive,
        test_top10_is_sorted_descending,
        test_cli_accepts_unchanged_baseline,
        test_breaches_carry_threshold_metadata,
        test_ratchet_contract_is_present,
        test_ratchet_refusals_are_behavioral,
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
