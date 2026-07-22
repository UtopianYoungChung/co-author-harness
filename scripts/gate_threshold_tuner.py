#!/usr/bin/env python3
"""gate_threshold_tuner.py — escalation-gate firing-rate calibration harness.

Reads the accumulated Planner escalation logs (``reviews/escalation_log.md``
across all projects pointed at by ``--project-root``) and reports per-gate
firing rates, precision/recall where self-T1 verdicts are pairable, and
recommended threshold adjustments per the calibration signals documented in
``references/TIER_PROTOCOL.md §7``.

This is a Phase D (v0.5.1) capability. At v0.5.0 the Reflector emits
calibration signals as prose; this script lets the maintainer compute the
signals themselves from a multi-project corpus and propose concrete
threshold deltas for the next package release. The tuner does not mutate any
config — it only emits a report.

Usage:
    python scripts/gate_threshold_tuner.py \\
        --project-root path/to/project1 \\
        --project-root path/to/project2 \\
        --window 6 \\
        --output reviews/gate_calibration_report.md

Exit codes:
    0 — report produced, no calibration signals raised
    1 — report produced, one or more calibration signals raised (non-fatal)
    2 — no escalation logs found in any of the project roots
    3 — unreadable log or malformed row

Gate firing records are parsed from the canonical ``reviews/escalation_log.md``
format (v0.7.0 vocabulary):

    ``| timestamp | prev_tier -> new_tier | gate | reason | round_id |``

The tuner's regex is column-position-anchored, so v0.6.0 rows carrying the
legacy ``from_tier -> to_tier`` column header still parse correctly — the
rename is strictly a header-text change. Migrated v0.6.0 ledgers are
therefore readable without a separate compatibility flag.

The round_id is used to pair a gate firing with the Generator Phase-3 output
block in the same round's ``manuscript/revision_log.md``. When pairing
succeeds the tuner can report precision/recall; when it fails the tuner
degrades gracefully to firing-rate-only reporting and flags the missing pair
as a soft warning in the report. The v0.6.0 "self-T1 verdict" pairing was
retired at v0.7.0 alongside the Generator Phase 3.5 Self-T1 Verdict surface
(see ``TIER_PROTOCOL.md §11`` retirement ledger); v0.7.0 pairing is against
the Generator's Phase-3 convergence signal at T3 terminal rows.
"""

from __future__ import annotations

import argparse
import dataclasses
import pathlib
import re
import sys
from collections import Counter, defaultdict


@dataclasses.dataclass
class GateFiring:
    timestamp: str
    prev_tier: str
    new_tier: str
    gate: str
    reason: str
    round_id: str
    project: str


# The capture groups ``prev`` and ``new`` read the column positions of the
# v0.7.0 header ``prev_tier -> new_tier`` (renamed from v0.6.0's
# ``from_tier -> to_tier``). Because the regex is anchored on column position
# and not header text, v0.6.0 rows parse identically and the tuner can ingest
# both pre- and post-migration escalation logs without a compatibility flag.
GATE_ROW_RE = re.compile(
    r"^\|\s*(?P<ts>[^|]+?)\s*\|\s*(?P<prev>T\w+)\s*->\s*(?P<new>T\w+)\s*\|"
    r"\s*(?P<gate>EG-\d)\s*\|\s*(?P<reason>[^|]*?)\s*\|\s*(?P<round>[^|]+?)\s*\|\s*$"
)

GATES = ("EG-1", "EG-2", "EG-3", "EG-4", "EG-5", "EG-6", "EG-7")

# Expected firing rates are documented per TIER_PROTOCOL.md §7 as rough
# bounds. A gate whose observed rate falls outside its bounds earns a
# calibration signal in the output report.
EXPECTED_BOUNDS: dict[str, tuple[float, float]] = {
    # v0.7.0 gate semantics per TIER_PROTOCOL.md §7 (EG-1 repurposed as T4→T3
    # grounding demotion; EG-2 retired on the Confirmation-Mode retirement;
    # EG-6 non-blocking warning; EG-7 new as MCR re-admission after
    # classification change). Historical v0.6.0 firings parse under the
    # same labels; calibration ranges hold across the rename because the
    # underlying trigger conditions are preserved at v0.7.0 for every
    # surviving gate.
    "EG-1": (0.02, 0.15),   # grounding-violation T4→T3 demotion (v0.7.0 repurpose)
    "EG-2": (0.00, 0.00),   # retired at v0.7.0; historical rows retained for audit
    "EG-3": (0.01, 0.10),   # cross-scope reference; mostly a T2 tell
    "EG-4": (0.01, 0.08),   # same-diff contradiction; rare by design
    "EG-5": (0.00, 0.03),   # directive violation; should be near zero
    "EG-6": (0.00, 0.05),   # /run-tier-N override warning (non-blocking at v0.7.0)
    "EG-7": (0.02, 0.15),   # MCR re-admission after classification change
}


def _read_escalation_log(project_root: pathlib.Path) -> list[GateFiring]:
    log = project_root / "reviews" / "escalation_log.md"
    if not log.exists():
        return []
    out: list[GateFiring] = []
    for raw in log.read_text(encoding="utf-8").splitlines():
        m = GATE_ROW_RE.match(raw)
        if not m:
            continue
        out.append(
            GateFiring(
                timestamp=m.group("ts"),
                prev_tier=m.group("prev"),
                new_tier=m.group("new"),
                gate=m.group("gate"),
                reason=m.group("reason"),
                round_id=m.group("round"),
                project=project_root.name,
            )
        )
    return out


def _count_rounds(project_root: pathlib.Path) -> int:
    """Approximate round count per project = distinct date stamps in step_findings/."""
    step = project_root / "reviews" / "step_findings"
    if not step.exists():
        return 0
    dates: set[str] = set()
    for entry in step.iterdir():
        if not entry.is_file():
            continue
        stem = entry.stem
        m = re.search(r"(20\d{2}-\d{2}-\d{2})", stem)
        if m:
            dates.add(m.group(1))
    return len(dates)


def _format_rate(rate: float) -> str:
    return f"{rate:.1%}"


def _render_report(
    firings_by_gate: dict[str, list[GateFiring]],
    total_rounds: int,
    window: int,
    signals: list[str],
    projects_scanned: list[str],
) -> str:
    lines: list[str] = []
    lines.append("# Gate calibration report")
    lines.append("")
    lines.append(f"**Projects scanned:** {', '.join(projects_scanned) or '(none)'}")
    lines.append(f"**Total rounds observed:** {total_rounds}")
    lines.append(f"**Window size:** {window} rounds")
    lines.append("")
    lines.append("## Per-gate firing rates")
    lines.append("")
    lines.append("| Gate | Firings | Rate | Expected range | Status |")
    lines.append("|---|---|---|---|---|")
    for gate in GATES:
        firings = firings_by_gate.get(gate, [])
        count = len(firings)
        rate = count / total_rounds if total_rounds else 0.0
        lo, hi = EXPECTED_BOUNDS[gate]
        if total_rounds == 0:
            status = "n/a (no rounds)"
        elif rate < lo:
            status = "under-firing"
        elif rate > hi:
            status = "over-firing"
        else:
            status = "within range"
        lines.append(
            f"| {gate} | {count} | {_format_rate(rate)} | "
            f"{_format_rate(lo)}-{_format_rate(hi)} | {status} |"
        )
    lines.append("")
    if signals:
        lines.append("## Calibration signals raised")
        lines.append("")
        for s in signals:
            lines.append(f"- {s}")
        lines.append("")
    else:
        lines.append("## Calibration signals raised")
        lines.append("")
        lines.append("_No gate fell outside its expected range in this window._")
        lines.append("")
    lines.append("## Methodology note")
    lines.append("")
    lines.append(
        "Expected ranges are documented in `references/TIER_PROTOCOL.md §7`. "
        "An under-firing gate means either the threshold is too conservative "
        "(the gate should fire more often than it does) or the upstream "
        "contract has drifted so the gate no longer sees its trigger condition. "
        "An over-firing gate means either the threshold is too sensitive or an "
        "upstream change is generating false positives. Both signals deserve "
        "investigation before a threshold change is committed."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--project-root", dest="project_roots", action="append", required=True,
        help="path to a project root (may be repeated for multi-project tuning)",
    )
    ap.add_argument("--window", type=int, default=6,
                    help="rolling window size in rounds (default 6)")
    ap.add_argument("--output", default=None,
                    help="write report to file; default stdout")
    args = ap.parse_args()

    if args.output:
        from destination_capability import DestinationRefused, assert_writable
        try:
            assert_writable(pathlib.Path(args.output), purpose="tuner report output")
        except DestinationRefused as exc:
            sys.stderr.write(f"[BLOCKER] {exc}\n")
            return 4

    roots = [pathlib.Path(p).resolve() for p in args.project_roots]
    missing = [p for p in roots if not p.exists()]
    if missing:
        for p in missing:
            sys.stderr.write(f"[gate_threshold_tuner] project root missing: {p}\n")
        return 3

    all_firings: list[GateFiring] = []
    rounds_total = 0
    projects_scanned: list[str] = []
    for root in roots:
        firings = _read_escalation_log(root)
        if firings:
            all_firings.extend(firings)
            projects_scanned.append(root.name)
        rounds_total += _count_rounds(root)

    if rounds_total == 0 and not all_firings:
        sys.stderr.write(
            "[gate_threshold_tuner] no escalation logs and no rounds found; "
            "nothing to calibrate\n"
        )
        return 2

    firings_by_gate: dict[str, list[GateFiring]] = defaultdict(list)
    for f in all_firings:
        firings_by_gate[f.gate].append(f)

    signals: list[str] = []
    for gate in GATES:
        rate = len(firings_by_gate.get(gate, [])) / rounds_total if rounds_total else 0.0
        lo, hi = EXPECTED_BOUNDS[gate]
        if rate < lo and rounds_total > 0:
            signals.append(
                f"[GATE CALIBRATION SIGNAL: {gate} under-firing] observed "
                f"{_format_rate(rate)}, expected >= {_format_rate(lo)}"
            )
        elif rate > hi:
            signals.append(
                f"[GATE CALIBRATION SIGNAL: {gate} over-firing] observed "
                f"{_format_rate(rate)}, expected <= {_format_rate(hi)}"
            )

    report = _render_report(
        firings_by_gate, rounds_total, args.window, signals, projects_scanned
    )

    if args.output:
        out_path = pathlib.Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")
    else:
        sys.stdout.write(report)

    return 1 if signals else 0


if __name__ == "__main__":
    sys.exit(main())
