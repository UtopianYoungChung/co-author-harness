#!/usr/bin/env python3
"""
SAFEGUARD_LAYER.md Check 8 Sub-check H — calibration-log aggregator.

Reads `reviews/h_calibration_<cycle_id>.md` files in the target project root
and emits `reviews/h_calibration_aggregate.md` with descriptive per-cycle and
across-cycle false-positive-rate (FPR) telemetry. It never decides, recommends,
or records transition retirement. Profile `transitions.H` owns meaning;
policy-binding Planner events own live state.

## Calibration-log format (canonical at v0.10.2)

Each `reviews/h_calibration_<cycle_id>.md` carries the user's adjudicated
view of the cycle's H findings. The format is Markdown with a
machine-parseable findings table:

    # H Calibration log — <cycle_id>

    Cycle: <cycle_id>
    Date: YYYY-MM-DD
    register_class_resolved: <technical | mixed | non-technical>

    ## Findings

    | id | locator | severity | false_positive_candidate | inherited_from_pre_h | reviewer_note |
    |---|---|---|---|---|---|
    | h001 | signpost_orienting_§3_line_42 | MINOR | false | false | confirmed |
    | h002 | vignette_§5_line_120 | MAJOR | true | false | over-fired on construct count |
    | ...

The columns are positional (the parser matches by header text rather than
column index, so reordering is tolerated). Boolean values accept any of
`true`, `false`, `yes`, `no`, `1`, `0` (case-insensitive). The
`reviewer_note` column is optional and free-form.

## Computed metrics

For each cycle, the aggregator computes:
- `total_findings` — count of all rows.
- `inherited_findings` — provenance count for rows inherited from earlier logs.
- `eligible_findings` — all findings; provenance never changes telemetry eligibility.
- `false_positive_count` — all rows with `false_positive_candidate: true`.
- `cycle_fpr` — `false_positive_count / eligible_findings` (zero-eligible
  cycles report `n/a`).

Across-cycle aggregate:
- `cumulative_eligible` — sum of `eligible_findings` across all cycles.
- `cumulative_fp` — sum of `false_positive_count` across all cycles.
- `aggregate_fpr` — `cumulative_fp / cumulative_eligible`.

Per Q2 adjudication 2026-04-27, the aggregator emits a single
`reviews/h_calibration_aggregate.md` per project. Cross-project roll-up is
deferred to v0.10.3.

Usage:
    python scripts/aggregate_h_calibration.py [project_root]

If `project_root` is omitted, the current working directory is used.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# -------- format primitives -----------------------------------------------

_TRUE_TOKENS = frozenset({"true", "yes", "1", "t", "y"})
_FALSE_TOKENS = frozenset({"false", "no", "0", "f", "n"})

_RE_CYCLE_ID = re.compile(r"^Cycle:\s*(\S+)\s*$", re.MULTILINE)
_RE_DATE = re.compile(r"^Date:\s*(\d{4}-\d{2}-\d{2})\s*$", re.MULTILINE)
_RE_REGISTER = re.compile(
    r"^(?:passage_scope_class_resolved|register_class_resolved):\s*(technical|mixed|non-technical)\s*$",
    re.MULTILINE,
)
_RE_TABLE_LINE = re.compile(r"^\s*\|.*\|\s*$")


def _parse_bool(token: str) -> Optional[bool]:
    """Tolerant boolean parser; returns None on unrecognised input."""
    t = token.strip().lower()
    if t in _TRUE_TOKENS:
        return True
    if t in _FALSE_TOKENS:
        return False
    return None


@dataclass
class Finding:
    finding_id: str
    locator: str
    severity: str
    false_positive_candidate: bool
    inherited_from_pre_h: bool
    reviewer_note: str = ""


@dataclass
class CycleReport:
    cycle_id: str
    date: str
    register_class_resolved: str
    findings: List[Finding] = field(default_factory=list)
    parse_warnings: List[str] = field(default_factory=list)

    @property
    def total_findings(self) -> int:
        return len(self.findings)

    @property
    def inherited_findings(self) -> int:
        return sum(1 for f in self.findings if f.inherited_from_pre_h)

    @property
    def eligible_findings(self) -> int:
        return self.total_findings

    @property
    def false_positive_count(self) -> int:
        return sum(
            1
            for f in self.findings
            if f.false_positive_candidate
        )

    @property
    def cycle_fpr(self) -> Optional[float]:
        if self.eligible_findings == 0:
            return None
        return self.false_positive_count / self.eligible_findings


# -------- parsing ---------------------------------------------------------

_REQUIRED_COLUMNS = {
    "id",
    "locator",
    "severity",
    "false_positive_candidate",
    "inherited_from_pre_h",
}


def _parse_findings_table(text: str) -> Tuple[List[Finding], List[str]]:
    """Parse the `## Findings` Markdown table; return (findings, warnings)."""
    warnings: List[str] = []
    findings: List[Finding] = []

    table_lines = [ln for ln in text.splitlines() if _RE_TABLE_LINE.match(ln)]
    if len(table_lines) < 2:
        warnings.append("no findings table found")
        return findings, warnings

    # First line is the header. Second is the separator (`|---|---|`).
    header_cells = [c.strip().lower() for c in table_lines[0].strip("|").split("|")]
    missing = _REQUIRED_COLUMNS - set(header_cells)
    if missing:
        warnings.append(
            f"findings table missing required columns: {sorted(missing)}"
        )
        return findings, warnings

    # Map column name to index.
    col = {name: idx for idx, name in enumerate(header_cells)}

    # Lines after the separator are data rows.
    data_lines = table_lines[2:]
    for ln in data_lines:
        cells = [c.strip() for c in ln.strip("|").split("|")]
        if len(cells) < len(header_cells):
            warnings.append(f"row has too few cells; skipping: {ln[:80]}")
            continue
        fpc = _parse_bool(cells[col["false_positive_candidate"]])
        inh = _parse_bool(cells[col["inherited_from_pre_h"]])
        if fpc is None or inh is None:
            warnings.append(
                f"row has unparseable boolean; skipping: "
                f"{cells[col.get('id', 0)][:32]}"
            )
            continue
        findings.append(
            Finding(
                finding_id=cells[col["id"]],
                locator=cells[col["locator"]],
                severity=cells[col["severity"]].upper(),
                false_positive_candidate=fpc,
                inherited_from_pre_h=inh,
                reviewer_note=cells[col["reviewer_note"]]
                if "reviewer_note" in col and len(cells) > col["reviewer_note"]
                else "",
            )
        )
    return findings, warnings


def parse_calibration_log(path: Path) -> CycleReport:
    """Parse one `reviews/h_calibration_<cycle_id>.md` file."""
    text = path.read_text(encoding="utf-8")

    cyc = _RE_CYCLE_ID.search(text)
    dat = _RE_DATE.search(text)
    reg = _RE_REGISTER.search(text)

    cycle_id = cyc.group(1) if cyc else path.stem.replace("h_calibration_", "")
    date_str = dat.group(1) if dat else "0000-00-00"
    register = reg.group(1) if reg else "technical"

    findings, warnings = _parse_findings_table(text)

    return CycleReport(
        cycle_id=cycle_id,
        date=date_str,
        register_class_resolved=register,
        findings=findings,
        parse_warnings=warnings,
    )


# -------- aggregation -----------------------------------------------------

@dataclass
class AggregateReport:
    cycles: List[CycleReport]

    @property
    def cycles_observed(self) -> int:
        return len(self.cycles)

    @property
    def cumulative_eligible(self) -> int:
        return sum(c.eligible_findings for c in self.cycles)

    @property
    def cumulative_fp(self) -> int:
        return sum(c.false_positive_count for c in self.cycles)

    @property
    def aggregate_fpr(self) -> Optional[float]:
        if self.cumulative_eligible == 0:
            return None
        return self.cumulative_fp / self.cumulative_eligible

def emit_aggregate(report: AggregateReport, out_path: Path) -> None:
    """Write the aggregate report to `reviews/h_calibration_aggregate.md`."""
    today = dt.datetime.now().strftime("%Y-%m-%d")

    lines: List[str] = []
    lines.append("# Sub-check H Calibration Aggregate")
    lines.append("")
    lines.append(f"**Generated:** {today}")
    lines.append(
        f"**Source:** {report.cycles_observed} calibration log "
        f"file{'s' if report.cycles_observed != 1 else ''}"
    )
    lines.append("")
    lines.append("## Per-cycle metrics")
    lines.append("")
    lines.append(
        "| Cycle | Date | Register | Total | Inherited | Eligible | "
        "False-Positive | Cycle FPR |"
    )
    lines.append(
        "|---|---|---|---|---|---|---|---|"
    )
    for c in report.cycles:
        fpr_str = f"{c.cycle_fpr:.4f}" if c.cycle_fpr is not None else "n/a"
        lines.append(
            f"| {c.cycle_id} | {c.date} | {c.register_class_resolved} | "
            f"{c.total_findings} | {c.inherited_findings} | "
            f"{c.eligible_findings} | {c.false_positive_count} | {fpr_str} |"
        )
    lines.append("")
    lines.append("## Cumulative metrics")
    lines.append("")
    lines.append(f"- **Cycles observed:** {report.cycles_observed}")
    lines.append(
        f"- **Cumulative eligible findings:** {report.cumulative_eligible}"
    )
    lines.append(f"- **Cumulative false positives:** {report.cumulative_fp}")
    agg = report.aggregate_fpr
    agg_str = f"{agg:.4f}" if agg is not None else "n/a"
    lines.append(f"- **Aggregate FPR:** {agg_str}")
    lines.append("")
    lines.append("## Transition authority")
    lines.append("")
    lines.append("This report is descriptive telemetry only. It cannot advance a counter or retire H; only validated Planner events under the reader-accessibility policy binding can do so.")
    lines.append("")
    lines.append("## Parse diagnostics")
    lines.append("")
    any_warnings = False
    for c in report.cycles:
        if c.parse_warnings:
            any_warnings = True
            lines.append(f"- **{c.cycle_id}:**")
            for w in c.parse_warnings:
                lines.append(f"  - {w}")
    if not any_warnings:
        lines.append("- No parse warnings.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "Per Q2 adjudication 2026-04-27, this aggregator emits a single "
        "per-project report. Cross-project FPR roll-up is deferred to v0.10.3."
    )
    out_path.write_text("\n".join(lines), encoding="utf-8")


# -------- main ------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument(
        "project_root",
        type=Path,
        nargs="?",
        default=Path.cwd(),
        help="Project root containing reviews/ subdirectory (default: cwd)",
    )
    args = ap.parse_args(argv)

    from destination_capability import DestinationRefused, guard_project_root
    try:
        guard_project_root(args.project_root)
    except DestinationRefused as exc:
        print(f"[BLOCKER] {exc}", file=sys.stderr)
        return 4

    reviews_dir = args.project_root / "reviews"
    if not reviews_dir.is_dir():
        print(
            f"ERROR: {reviews_dir} does not exist (no reviews/ subdir under "
            f"{args.project_root})",
            file=sys.stderr,
        )
        return 2

    log_files = sorted(reviews_dir.glob("h_calibration_*.md"))
    log_files = [
        p for p in log_files if p.name != "h_calibration_aggregate.md"
    ]
    if not log_files:
        print(
            f"ERROR: no h_calibration_<cycle_id>.md files in {reviews_dir}",
            file=sys.stderr,
        )
        return 3

    cycles = [parse_calibration_log(p) for p in log_files]
    cycles.sort(key=lambda c: (c.date, c.cycle_id))
    report = AggregateReport(cycles=cycles)

    out_path = reviews_dir / "h_calibration_aggregate.md"
    emit_aggregate(report, out_path)

    print(f"Wrote {out_path}")
    print(
        f"Cycles: {report.cycles_observed}; "
        f"Aggregate FPR: "
        f"{report.aggregate_fpr if report.aggregate_fpr is not None else 'n/a'}; transition state: not evaluated"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
