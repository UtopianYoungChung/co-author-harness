"""Smoketest for the audit suite.

Runs run_all against the known-bad fixture and asserts that every check_id
class fires at least once. If a future refactor silently drops a detector,
this test fails.
"""

from __future__ import annotations

import sys
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

    print(
        f"OK audit smoketest — {len(report.findings)} findings across "
        f"{len(fired)} distinct check classes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
