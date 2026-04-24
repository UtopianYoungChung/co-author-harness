#!/usr/bin/env python3
# migrate_convergence_log_v074.py
#
# Track B (v0.7.4) migration, Pass 2: split the legacy convergence-log
# contract into two artefacts, per P-4 of the v0.7.4 economic-efficiency
# package (see Ph.D. Research/CLAUDE.md §12.10 and §12.7).
#
# The split
# ---------
# Before v0.7.4 the file `reviews/convergence_log.md` carried two overlapping
# responsibilities at once:
#
#   (a) per-iteration mechanical state — cycle id, iteration index, convergence
#       metric, Check 8 aggregate verdict, accessibility-gate state, line-delta
#       footprint, timestamp;
#
#   (b) Trajectory-synthesis prose — the narrative that a human-reader follows
#       to understand how iteration N got there, what the user directive was,
#       which bundles were folded in, which DND artefacts were preserved, which
#       three-path choice was offered at the boundary checkpoint.
#
# v0.7.4 separates these concerns.  Per-iteration mechanical state migrates to
# `reviews/convergence_journal.jsonl` (one JSON line per iteration, one file
# per project, append-only within the round, frozen at Ph3 terminal signoff).
# `convergence_log.md` retains responsibility (b) only and is frozen as
# Trajectory-synthesis prose from the moment this migration completes.
#
# Journal row schema (P-4)
# ------------------------
# Each row of `convergence_journal.jsonl` has exactly the nine fields:
#
#   {
#     "cycle_id":                  str,
#     "iteration":                 int,
#     "convergence_metric":        float | null,
#     "check8_aggregate":          "PASS" | "BORDERLINE" | "MAJOR" | "BLOCKER" | null,
#     "manuscript_hash":           str | null,
#     "new_findings_count":        int | null,
#     "delta_lines":               int | null,
#     "accessibility_gate_state":  "CLEAN" | "BORDERLINE" | "BLOCKED" | null,
#     "timestamp":                 str (ISO-8601, UTC) | null
#   }
#
# Fields whose value the legacy prose did not record (manuscript_hash,
# new_findings_count on some iterations) are migrated as `null` and the
# migration report names them so the user / Reflector can backfill if needed.
#
# Legacy-file disposition
# -----------------------
#   * The raw legacy file is backed up verbatim to
#     `reviews/convergence_log.md.v073.bak` before any rewrite.
#   * `reviews/convergence_log.md` is rewritten with an updated frontmatter
#     (adding `journal_path`, `p4_contract_split_applied_at`, and flipping
#     `frozen_status: true`) plus a one-paragraph migration banner at the top
#     of the body.  The Trajectory-synthesis prose body is preserved byte-for-
#     byte below the banner; no iteration sections are deleted.
#   * Any v0.7.4-era tier-named references in the prose (T1/T2/T3/T4,
#     tier_state.json, TIER_PROTOCOL.md, etc.) are *not* rewritten by this
#     script — the Tier -> Phase rename is the job of
#     migrate_v073_to_v074_tier_to_phase.py (Pass 1).  Run Pass 1 first; then
#     run Pass 2.
#
# Idempotency
# -----------
#   * If `reviews/convergence_journal.jsonl` already exists, the script treats
#     Pass 2 as complete and re-emits the migration report with a note.  No
#     parse is re-run; no rows are rewritten.
#   * If `frozen_status: true` is already set in the frontmatter and the
#     banner is already present, the script leaves the legacy file alone.
#
# Usage
# -----
#   python migrate_convergence_log_v074.py --project-root /path/to/project
#   python migrate_convergence_log_v074.py --project-root /path --dry-run
#
# Exit codes
# ----------
#   0  success (migration ran or was already complete)
#   1  usage error
#   2  project-root missing or not a directory
#   3  reviews/ subdir not found
#   4  reviews/convergence_log.md not found (nothing to migrate)
#   5  write failure
#   6  parse failure (no iteration sections recognisable in the log)

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION_CONTRACT = "p4-v0.7.4"

# -----------------------------------------------------------------------------
# Iteration-block parser
# -----------------------------------------------------------------------------
#
# Legacy iteration blocks follow the pattern (whitespace flexible):
#
#   ## Iteration N — <subtitle> (<YYYY-MM-DD>)
#   ...
#   **Cycle id.** `<cycle_id>`.
#   ...
#   **Convergence metric — iteration N.** `<float>` (<optional delta prose>).
#   ...
#   **Check 8 aggregate — iteration N.** **<PASS|BORDERLINE|MAJOR|BLOCKER>** ...
#   ...
#   **Accessibility gate precondition ...**
#
# The regexes below are tolerant: they capture best-effort and fall back to
# null when a field isn't present in the legacy prose.

_RE_ITER_HEADER = re.compile(
    r"^##\s+Iteration\s+(?P<iter>\d+)\s+—\s+(?P<subtitle>.+?)(?:\s+\((?P<date>\d{4}-\d{2}-\d{2})\))?\s*$",
    re.MULTILINE,
)

_RE_CYCLE_ID = re.compile(
    r"\*\*Cycle\s+id\.\*\*\s*`(?P<cycle_id>[^`]+)`",
    re.IGNORECASE,
)

_RE_CONVERGENCE_METRIC = re.compile(
    r"\*\*Convergence\s+metric\s+—\s+iteration\s+\d+\.\*\*\s*`(?P<metric>[0-9.]+)`",
    re.IGNORECASE,
)

_RE_CHECK8 = re.compile(
    r"\*\*Check\s+8\s+aggregate\s+—\s+iteration\s+\d+\.\*\*\s*\*\*(?P<verdict>PASS|BORDERLINE|MAJOR|BLOCKER)\*\*",
    re.IGNORECASE,
)

_RE_DELTA_LINES = re.compile(
    r"line[- ]?(?:delta|churn delta|delta)\s*(?:≈|=|is)?\s*([+\-]?\d+)",
    re.IGNORECASE,
)


def _iso_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def _verdict_to_gate_state(verdict: str | None) -> str | None:
    """Map legacy Check 8 verdict to v0.7.2+ accessibility_gate_state vocabulary."""
    if verdict is None:
        return None
    v = verdict.upper()
    if v == "PASS":
        return "CLEAN"
    if v == "BORDERLINE":
        return "BORDERLINE"
    if v in ("MAJOR", "BLOCKER"):
        return "BLOCKED"
    return None


def _parse_iteration_blocks(text: str) -> list[dict[str, Any]]:
    """Walk the legacy log and produce one dict per iteration block."""
    # Split on every '## Iteration ...' header to get per-iteration body slices.
    headers = list(_RE_ITER_HEADER.finditer(text))
    if not headers:
        return []

    rows: list[dict[str, Any]] = []
    for idx, m in enumerate(headers):
        start = m.end()
        end = headers[idx + 1].start() if idx + 1 < len(headers) else len(text)
        block = text[start:end]

        iteration_num = int(m.group("iter"))
        date = m.group("date")

        cycle_m = _RE_CYCLE_ID.search(block)
        cycle_id = cycle_m.group("cycle_id") if cycle_m else None

        metric_m = _RE_CONVERGENCE_METRIC.search(block)
        metric = float(metric_m.group("metric")) if metric_m else None

        check8_m = _RE_CHECK8.search(block)
        check8 = check8_m.group("verdict").upper() if check8_m else None

        delta_m = _RE_DELTA_LINES.search(block)
        delta_lines: int | None = None
        if delta_m:
            try:
                delta_lines = int(delta_m.group(1))
            except ValueError:
                delta_lines = None

        timestamp: str | None = None
        if date is not None:
            # Convert YYYY-MM-DD to an ISO-8601 UTC midnight for JSONL
            # consumers that want to sort on timestamp.  We do not invent time-
            # of-day precision the legacy prose never recorded.
            timestamp = f"{date}T00:00:00Z"

        row = {
            "cycle_id": cycle_id,
            "iteration": iteration_num,
            "convergence_metric": metric,
            "check8_aggregate": check8,
            "manuscript_hash": None,
            "new_findings_count": None,
            "delta_lines": delta_lines,
            "accessibility_gate_state": _verdict_to_gate_state(check8),
            "timestamp": timestamp,
        }
        rows.append(row)

    return rows


# -----------------------------------------------------------------------------
# Legacy-file disposition: frontmatter rewrite + banner
# -----------------------------------------------------------------------------

_RE_FRONTMATTER = re.compile(r"^---\s*\n(?P<fm>.*?)\n---\s*\n", re.DOTALL)

_BANNER_MARKER = "<!-- P-4 convergence-log contract split — v0.7.4 migration banner -->"

_BANNER_TEMPLATE = f"""{_BANNER_MARKER}

> **P-4 contract split applied at v0.7.4.** Per-iteration mechanical state
> (convergence_metric, Check 8 aggregate, accessibility_gate_state, etc.) now
> lives in `reviews/convergence_journal.jsonl`, one JSON line per iteration.
> This file retains responsibility for Trajectory-synthesis prose only —
> iteration bodies below are preserved as narrative record of how each
> iteration got there, what the user directive was, which bundles were folded
> in, and which three-path boundary choice was offered at the checkpoint.
> The mechanical state above has been extracted verbatim; any drift between
> the prose and the journal is a Reflector Phase 2f `[P4-SPLIT-DRIFT]` finding.
>
> The legacy raw file is preserved at `reviews/convergence_log.md.v073.bak`.
"""


def _rewrite_legacy_frontmatter(
    original_text: str,
    journal_rel_path: str,
    applied_at: str,
) -> str:
    """Return the legacy file with updated frontmatter + top-of-body banner.

    Preserves the prose body byte-for-byte below the banner.
    """
    fm_match = _RE_FRONTMATTER.match(original_text)
    if not fm_match:
        # No frontmatter — synthesize a minimal one.
        new_fm = (
            f"---\n"
            f"artefact: convergence_log\n"
            f"frozen_status: true\n"
            f"journal_path: {journal_rel_path}\n"
            f"p4_contract_split_applied_at: {applied_at}\n"
            f"---\n\n"
        )
        return new_fm + _BANNER_TEMPLATE + "\n" + original_text

    fm_text = fm_match.group("fm")
    body = original_text[fm_match.end():]

    # Parse frontmatter as simple key: value pairs.  We do not pull in PyYAML
    # because the harness's scripts/ directory deliberately runs on the
    # CPython stdlib only.
    lines = fm_text.splitlines()
    fm_dict: dict[str, str] = {}
    ordered_keys: list[str] = []
    for ln in lines:
        if ":" in ln and not ln.lstrip().startswith("#"):
            k, _, v = ln.partition(":")
            k = k.strip()
            v = v.strip()
            fm_dict[k] = v
            ordered_keys.append(k)

    # Flip / inject the v0.7.4 fields.
    fm_dict["frozen_status"] = "true"
    if "frozen_status" not in ordered_keys:
        ordered_keys.append("frozen_status")
    fm_dict["journal_path"] = journal_rel_path
    if "journal_path" not in ordered_keys:
        ordered_keys.append("journal_path")
    fm_dict["p4_contract_split_applied_at"] = applied_at
    if "p4_contract_split_applied_at" not in ordered_keys:
        ordered_keys.append("p4_contract_split_applied_at")

    new_fm_lines = [f"{k}: {fm_dict[k]}" for k in ordered_keys]
    new_fm = "---\n" + "\n".join(new_fm_lines) + "\n---\n\n"

    # Idempotency: if banner already present, don't insert a second one.
    if _BANNER_MARKER in body:
        return new_fm + body

    return new_fm + _BANNER_TEMPLATE + "\n" + body


# -----------------------------------------------------------------------------
# Migration report
# -----------------------------------------------------------------------------


def _build_report(
    project_root: Path,
    legacy_path: Path,
    journal_path: Path,
    rows: list[dict[str, Any]],
    applied_at: str,
    dry_run: bool,
    already_migrated: bool,
) -> str:
    lines: list[str] = []
    lines.append("---")
    lines.append("artefact: migration_report_convergence_log_v074")
    lines.append(f"applied_at: {applied_at}")
    lines.append(f"schema_contract: {SCHEMA_VERSION_CONTRACT}")
    lines.append(f"dry_run: {'true' if dry_run else 'false'}")
    lines.append(f"already_migrated: {'true' if already_migrated else 'false'}")
    lines.append("---")
    lines.append("")
    lines.append("# Migration Report — `migrate_convergence_log_v074.py` (P-4 Pass 2)")
    lines.append("")
    lines.append(
        "This report records what the P-4 convergence-log contract split did to "
        f"`{legacy_path.relative_to(project_root)}` on {applied_at}."
    )
    lines.append("")
    if already_migrated:
        lines.append(
            "> **Idempotent re-run.** `convergence_journal.jsonl` was already "
            "present at invocation time; no rows were re-parsed and the legacy "
            "file was not rewritten.  This report is a diagnostic echo only."
        )
        lines.append("")

    lines.append("## Extraction summary")
    lines.append("")
    lines.append(f"- Iterations recognised in legacy log: **{len(rows)}**")
    lines.append(f"- Journal path: `{journal_path.relative_to(project_root)}`")
    lines.append(f"- Legacy backup: `{legacy_path.name}.v073.bak`")
    lines.append("")

    # Per-row diagnostic table.
    if rows:
        lines.append("## Per-iteration extraction diagnostic")
        lines.append("")
        lines.append(
            "| iter | cycle_id | metric | check8 | gate | Δlines | timestamp |"
        )
        lines.append(
            "|------|----------|--------|--------|------|--------|-----------|"
        )
        for r in rows:
            lines.append(
                "| {iter} | `{cycle}` | {metric} | {c8} | {gate} | {delta} | {ts} |".format(
                    iter=r["iteration"],
                    cycle=r["cycle_id"] if r["cycle_id"] else "—",
                    metric=r["convergence_metric"] if r["convergence_metric"] is not None else "null",
                    c8=r["check8_aggregate"] if r["check8_aggregate"] else "null",
                    gate=r["accessibility_gate_state"] if r["accessibility_gate_state"] else "null",
                    delta=r["delta_lines"] if r["delta_lines"] is not None else "null",
                    ts=r["timestamp"] if r["timestamp"] else "null",
                )
            )
        lines.append("")

    # Null-field audit so the user can see what the migration couldn't recover.
    null_counts = {
        "cycle_id": sum(1 for r in rows if r["cycle_id"] is None),
        "convergence_metric": sum(1 for r in rows if r["convergence_metric"] is None),
        "check8_aggregate": sum(1 for r in rows if r["check8_aggregate"] is None),
        "manuscript_hash": sum(1 for r in rows if r["manuscript_hash"] is None),
        "new_findings_count": sum(1 for r in rows if r["new_findings_count"] is None),
        "delta_lines": sum(1 for r in rows if r["delta_lines"] is None),
        "timestamp": sum(1 for r in rows if r["timestamp"] is None),
    }
    lines.append("## Null-field audit")
    lines.append("")
    lines.append(
        "The following counts show how many rows carry `null` in each field "
        "because the legacy prose did not record it.  The Reflector may "
        "backfill these at its next Phase 2d audit."
    )
    lines.append("")
    for field, count in null_counts.items():
        lines.append(f"- `{field}`: **{count}** / {len(rows)} rows are null.")
    lines.append("")

    lines.append("## Contract expectations going forward")
    lines.append("")
    lines.append(
        "- `reviews/convergence_journal.jsonl` is append-only within a Ph3 "
        "round and is frozen at the terminal signoff.  The Planner is the "
        "sole writer; Evaluator and Reflector are readers.\n"
        "- `reviews/convergence_log.md` retains Trajectory-synthesis prose "
        "only.  New iteration bodies should continue to be written as "
        "narrative; the mechanical fields live in the journal.\n"
        "- Drift between the two artefacts is a Reflector Phase 2f "
        "`[P4-SPLIT-DRIFT]` finding (MAJOR by default)."
    )
    lines.append("")
    lines.append("## Next step")
    lines.append("")
    lines.append(
        "After reviewing this report, the user should append "
        "`user_confirmed_p4_split_at: <ISO timestamp>` to "
        "`reviews/classification.md` frontmatter to clear the Planner's "
        "Phase-0 hold on P-4 migration for this project."
    )
    lines.append("")

    return "\n".join(lines) + "\n"


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="P-4 Pass 2: split convergence_log into prose + journal."
    )
    p.add_argument(
        "--project-root",
        required=True,
        help="Path to the project root (the folder containing reviews/).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and report only; write no files.",
    )
    args = p.parse_args(argv)

    project_root = Path(args.project_root).resolve()
    if not project_root.is_dir():
        print(f"[error] --project-root is not a directory: {project_root}", file=sys.stderr)
        return 2

    reviews_dir = project_root / "reviews"
    if not reviews_dir.is_dir():
        print(f"[error] reviews/ subdirectory not found under {project_root}", file=sys.stderr)
        return 3

    legacy_path = reviews_dir / "convergence_log.md"
    if not legacy_path.is_file():
        print(
            f"[error] {legacy_path.relative_to(project_root)} not found; nothing to migrate.",
            file=sys.stderr,
        )
        return 4

    journal_path = reviews_dir / "convergence_journal.jsonl"
    report_path = reviews_dir / "migration_report_convergence_log_v074.md"
    backup_path = reviews_dir / "convergence_log.md.v073.bak"
    applied_at = _iso_now()

    already_migrated = journal_path.is_file()

    # Parse iterations regardless — we want the report diagnostic either way.
    legacy_text = legacy_path.read_text(encoding="utf-8")
    rows = _parse_iteration_blocks(legacy_text)

    if not rows:
        print(
            "[error] No iteration sections recognised in convergence_log.md. "
            "The file may already be frozen prose-only, or the schema has "
            "drifted from the v0.7.0–v0.7.3 heading convention.",
            file=sys.stderr,
        )
        return 6

    if args.dry_run:
        # Dry-run: emit the report only; do not touch any files on disk.
        report_text = _build_report(
            project_root=project_root,
            legacy_path=legacy_path,
            journal_path=journal_path,
            rows=rows,
            applied_at=applied_at,
            dry_run=True,
            already_migrated=already_migrated,
        )
        print(report_text)
        print(f"[dry-run] Would have written {len(rows)} rows to {journal_path}.")
        print(f"[dry-run] Would have backed up legacy file to {backup_path.name}.")
        return 0

    if already_migrated:
        # Idempotent: re-emit the report only; do not re-parse or rewrite.
        try:
            report_text = _build_report(
                project_root=project_root,
                legacy_path=legacy_path,
                journal_path=journal_path,
                rows=rows,
                applied_at=applied_at,
                dry_run=False,
                already_migrated=True,
            )
            report_path.write_text(report_text, encoding="utf-8")
        except OSError as e:
            print(f"[error] Could not write report: {e}", file=sys.stderr)
            return 5
        print(
            f"[idempotent] convergence_journal.jsonl already present; "
            f"re-emitted report at {report_path.name}."
        )
        return 0

    # --- Fresh migration path ---

    # 1. Write the journal.
    try:
        with journal_path.open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    except OSError as e:
        print(f"[error] Could not write journal: {e}", file=sys.stderr)
        return 5

    # 2. Back up the legacy file verbatim.
    try:
        shutil.copy2(legacy_path, backup_path)
    except OSError as e:
        print(f"[error] Could not back up legacy file: {e}", file=sys.stderr)
        # If backup fails, do NOT rewrite the legacy file.
        return 5

    # 3. Rewrite the legacy file's frontmatter + insert the banner.
    try:
        new_legacy_text = _rewrite_legacy_frontmatter(
            original_text=legacy_text,
            journal_rel_path=str(journal_path.relative_to(project_root)),
            applied_at=applied_at,
        )
        legacy_path.write_text(new_legacy_text, encoding="utf-8")
    except OSError as e:
        print(f"[error] Could not rewrite legacy file: {e}", file=sys.stderr)
        return 5

    # 4. Emit the migration report.
    try:
        report_text = _build_report(
            project_root=project_root,
            legacy_path=legacy_path,
            journal_path=journal_path,
            rows=rows,
            applied_at=applied_at,
            dry_run=False,
            already_migrated=False,
        )
        report_path.write_text(report_text, encoding="utf-8")
    except OSError as e:
        print(f"[error] Could not write report: {e}", file=sys.stderr)
        return 5

    print(
        f"[ok] Wrote {len(rows)} rows to {journal_path.name}; "
        f"legacy file frozen as Trajectory-synthesis prose; "
        f"backup at {backup_path.name}; "
        f"report at {report_path.name}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
