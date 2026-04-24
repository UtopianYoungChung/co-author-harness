#!/usr/bin/env python3
# migrate_v073_to_v074_tier_to_phase.py
#
# Track B (v0.7.4) migration: rename the *Tier* lexicon to the *Phase* lexicon
# across a project's review artefacts, and widen the SectionStateObject log row
# from six fields to seven (adding an absent-means-null `model_used` field).
#
# Scope
# -----
#   * reviews/tier_state.json  ->  reviews/phase_state.json
#       - field renames:
#           current_tier           ->  current_phase
#           tier_goal_declared     ->  phase_goal_declared
#           tier_deliverable_path  ->  phase_deliverable_path
#           tier_entry_log         ->  phase_entry_log
#       - value renames (strings only; not regexed into free-form notes):
#           T1|T2|T3|T4            ->  Ph1|Ph2|Ph3|Ph4
#           T3_converged           ->  Ph3_converged
#           t1_*|t2_*|t3_*|t4_*    ->  ph1_*|ph2_*|ph3_*|ph4_*  (trigger enum)
#           eg1_t4_downgrade_to_t3 ->  eg1_ph4_downgrade_to_ph3
#       - log row shape widen: 6 fields -> 7 fields (absent-means-null model_used)
#
#   * reviews/classification.md
#       - rename field `default_final_tier` -> `default_final_phase`
#       - rename values T1/T2/T3/T4 -> Ph1/Ph2/Ph3/Ph4 within that field only
#       - append `user_confirmed_migration_report_at: <pending>` to frontmatter
#         if not already present (will be set by the user after review)
#
#   * reviews/t{1,2,3}_*_completion.md  ->  reviews/ph{1,2,3}_*_completion.md
#       (file rename only; contents are not rewritten)
#
#   * reviews/migration_report_v073_to_v074.md
#       - a new report summarizing every change made, per-file, for user review
#
# Idempotency
# -----------
#   * If `reviews/phase_state.json` already exists, the script treats the
#     migration as complete and only re-emits the report (with a note).
#   * If any log row already has 7 fields, it is left untouched.
#   * If `default_final_phase` is already set in classification frontmatter,
#     no rename is attempted.
#
# Exemptions preserved
# --------------------
#   * Legacy `confirmation_failed` log rows keep their `[v0.7.0-READ-ONLY]`
#     marker untouched. Only the T3_converged / tier-prefix surface is rewritten.
#
# Out of scope
# ------------
#   * Convergence-log splits (P-4) are handled by migrate_convergence_log_v074.py.
#   * Skill file renames (run-tier-{1..4} -> run-phase-{1..4}) are plugin-level,
#     not project-level, and are shipped inside the v0.7.4 release zip.
#   * Agent prompt rewrites are plugin-level, not project-level.
#
# Usage
# -----
#   python migrate_v073_to_v074_tier_to_phase.py --project-root /path/to/project
#   python migrate_v073_to_v074_tier_to_phase.py --project-root /path --dry-run
#
# Exit codes
# ----------
#   0  success (migration ran or was already complete)
#   1  usage error
#   2  project-root missing or not a directory
#   3  reviews/ subdir not found
#   4  JSON parse error on tier_state.json
#   5  write failure
#   6  invariant violation (log row is neither 6 nor 7 fields wide)

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

SCHEMA_VERSION_BEFORE = "0.7.3"
SCHEMA_VERSION_AFTER = "0.7.4"

TIER_FIELD_RENAMES = {
    # Top-level SectionStateObject fields (v0.7.0 15-field schema, minus the
    # already-phase-named fields like convergence_metric).
    "current_tier": "current_phase",
    "tier_goal_declared": "phase_goal_declared",
    "tier_deliverable_path": "phase_deliverable_path",
    "tier_entry_log": "phase_entry_log",
    "t1_pstage_declaration": "ph1_pstage_declaration",
    "t3_last_activity_at": "ph3_last_activity_at",
    # Defensive renames in case a project carried the legacy v0.6.0 names.
    "t4_ready": "ph4_ready",
    "tier_state": "phase_state",
}

# Value substitutions, applied in order.  Order matters: longer patterns first
# so that, e.g., `T3_converged` is rewritten before a naked `T3` rule runs.
VALUE_SUBSTITUTIONS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bT3_converged\b"), "Ph3_converged"),
    (re.compile(r"\bT4_ready\b"), "Ph4_ready"),  # legacy v0.6.0 carryover
    (re.compile(r"\bT3_ready\b"), "Ph3_ready"),  # legacy carryover
    (re.compile(r"\beg1_t4_downgrade_to_t3\b"), "eg1_ph4_downgrade_to_ph3"),
    # Word-boundary tier codes.  Matches T1..T4 and t1..t4 at word boundaries.
    # Must run AFTER the more-specific rules above.
    (re.compile(r"\bT([1-4])\b"), r"Ph\1"),
    (re.compile(r"\bt([1-4])_"), r"ph\1_"),   # trigger prefix: t1_foo -> ph1_foo
    (re.compile(r"(?<=_)t([1-4])_"), r"ph\1_"),  # mid-word t-prefix: eg_t3_bar -> eg_ph3_bar
    # [T3-STALE] and [T4-STALE] bracketed markers
    (re.compile(r"\[T([1-4])-STALE\]"), r"[Ph\1-STALE]"),
]

# The log row widens from 6 -> 7 fields.  The seventh field is model_used, which
# defaults to null under absent-means-null semantics.
LOG_ROW_FIELDS_V073 = {
    "prev_tier", "new_tier", "trigger", "actor", "notes", "timestamp",
}
LOG_ROW_FIELDS_V074 = {
    "prev_phase", "new_phase", "trigger", "actor", "notes", "timestamp",
    "model_used",
}
# Field renames inside a log row object.
LOG_ROW_FIELD_RENAMES = {
    "prev_tier": "prev_phase",
    "new_tier": "new_phase",
}


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _iso_now() -> str:
    """Return UTC now in ISO 8601 with second precision."""
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def _apply_value_subs(s: str) -> str:
    """Apply every VALUE_SUBSTITUTIONS rule in order to a string."""
    out = s
    for pat, repl in VALUE_SUBSTITUTIONS:
        out = pat.sub(repl, out)
    return out


def _migrate_value(v: Any) -> Any:
    """Recursively rewrite T-* surface vocabulary inside a JSON value."""
    if isinstance(v, str):
        return _apply_value_subs(v)
    if isinstance(v, list):
        return [_migrate_value(x) for x in v]
    if isinstance(v, dict):
        return {k: _migrate_value(x) for k, x in v.items()}
    return v


def _migrate_log_row(row: dict, report_lines: list[str]) -> dict:
    """Rewrite a single log row: rename fields, widen to 7 fields, rewrite
    values."""
    # Already-migrated row detection.
    keys = set(row.keys())
    if keys <= LOG_ROW_FIELDS_V074 and "new_phase" in keys:
        # Already at v0.7.4 shape — only apply value subs defensively.
        out = {k: _migrate_value(v) for k, v in row.items()}
        if "model_used" not in out:
            out["model_used"] = None
        return out

    if keys <= LOG_ROW_FIELDS_V073 | {"prev_phase", "new_phase", "model_used"}:
        out: dict = {}
        for k, v in row.items():
            new_key = LOG_ROW_FIELD_RENAMES.get(k, k)
            out[new_key] = _migrate_value(v)
        # Widen: add model_used if absent.
        if "model_used" not in out:
            out["model_used"] = None
            report_lines.append(
                f"    + widened log row at timestamp={out.get('timestamp', '?')} "
                f"(added model_used=null)"
            )
        return out

    # Unknown log row shape.  Fail loud.
    raise ValueError(
        f"log row has unexpected field set: {sorted(keys)}  "
        f"(expected subset of v0.7.3 {sorted(LOG_ROW_FIELDS_V073)} "
        f"or v0.7.4 {sorted(LOG_ROW_FIELDS_V074)})"
    )


def _migrate_section_state(section: dict, report_lines: list[str]) -> dict:
    """Rewrite a single SectionStateObject (a value inside the top-level map)."""
    out: dict = {}
    for k, v in section.items():
        new_key = TIER_FIELD_RENAMES.get(k, k)
        if new_key == "phase_entry_log" and isinstance(v, list):
            out[new_key] = [_migrate_log_row(row, report_lines) for row in v]
        else:
            out[new_key] = _migrate_value(v)
    return out


def _migrate_tier_state(doc: dict, report_lines: list[str]) -> dict:
    """Rewrite the whole tier_state.json document at v0.7.4 shape."""
    out: dict = {}
    # Top-level may be a flat map of section-heading-path -> SectionStateObject,
    # or may carry a `sections` container and top-level metadata.  Handle both.
    if "sections" in doc and isinstance(doc["sections"], dict):
        out = {k: v for k, v in doc.items() if k != "sections"}
        out["sections"] = {
            path: _migrate_section_state(sec, report_lines)
            for path, sec in doc["sections"].items()
        }
    else:
        # Flat map.  Migrate each value as a SectionStateObject.
        for path, sec in doc.items():
            if isinstance(sec, dict):
                out[path] = _migrate_section_state(sec, report_lines)
            else:
                out[path] = _migrate_value(sec)
    # Bump schema_version if present at top.
    if isinstance(out.get("schema_version"), str):
        out["schema_version"] = SCHEMA_VERSION_AFTER
    return out


# -----------------------------------------------------------------------------
# classification.md migration
# -----------------------------------------------------------------------------


FRONTMATTER_DELIM = re.compile(r"^---\s*$", re.MULTILINE)
DEFAULT_FINAL_TIER_LINE = re.compile(
    r"^(?P<indent>\s*)default_final_tier(?P<sep>\s*:\s*)(?P<val>.+?)\s*$",
    re.MULTILINE,
)


def _migrate_classification_md(text: str, report_lines: list[str]) -> str:
    """Rename default_final_tier -> default_final_phase inside the YAML
    frontmatter, and rewrite its value (T1..T4 -> Ph1..Ph4). Append a pending
    user_confirmed_migration_report_at marker if absent."""
    # Isolate frontmatter.
    matches = list(FRONTMATTER_DELIM.finditer(text))
    if len(matches) < 2:
        report_lines.append("    (no YAML frontmatter found; leaving file untouched)")
        return text
    fm_start = matches[0].end()
    fm_end = matches[1].start()
    fm = text[fm_start:fm_end]
    body = text[fm_end:]
    head = text[: matches[0].end()]

    already_migrated = re.search(r"^\s*default_final_phase\s*:", fm, re.MULTILINE)

    def _rename_line(m: re.Match[str]) -> str:
        old_val = m.group("val").strip()
        new_val = _apply_value_subs(old_val)
        report_lines.append(
            f"    - renamed default_final_tier -> default_final_phase "
            f"(value: {old_val} -> {new_val})"
        )
        return f"{m.group('indent')}default_final_phase{m.group('sep')}{new_val}"

    if already_migrated:
        report_lines.append(
            "    (default_final_phase already present; no field rename applied)"
        )
        new_fm = fm
    else:
        new_fm, n = DEFAULT_FINAL_TIER_LINE.subn(_rename_line, fm)
        if n == 0:
            report_lines.append(
                "    (default_final_tier not found in frontmatter; nothing to rename)"
            )

    # Append pending confirmation marker if not already present.
    if not re.search(
        r"^\s*user_confirmed_migration_report_at\s*:", new_fm, re.MULTILINE
    ):
        marker = "\nuser_confirmed_migration_report_at: <pending-user-review>\n"
        new_fm = new_fm.rstrip() + "\n" + marker.lstrip()
        report_lines.append(
            "    + appended user_confirmed_migration_report_at: <pending-user-review> "
            "to frontmatter"
        )
    else:
        report_lines.append(
            "    (user_confirmed_migration_report_at already present; untouched)"
        )

    return head + new_fm + body


# -----------------------------------------------------------------------------
# Completion-artefact file renames
# -----------------------------------------------------------------------------


COMPLETION_FILE_RENAMES = {
    "t1_draft_completion.md": "ph1_draft_completion.md",
    "t2_review_completion.md": "ph2_review_completion.md",
    "t3_convergence_signoff.md": "ph3_convergence_signoff.md",
}


def _rename_completion_files(
    reviews_dir: Path, report_lines: list[str], dry_run: bool
) -> None:
    for old, new in COMPLETION_FILE_RENAMES.items():
        old_path = reviews_dir / old
        new_path = reviews_dir / new
        if not old_path.exists():
            continue
        if new_path.exists():
            report_lines.append(
                f"    (both {old} and {new} exist; leaving as-is — manual review)"
            )
            continue
        if dry_run:
            report_lines.append(f"    - would rename {old} -> {new}  (dry-run)")
        else:
            old_path.rename(new_path)
            report_lines.append(f"    - renamed {old} -> {new}")


# -----------------------------------------------------------------------------
# Report writer
# -----------------------------------------------------------------------------


REPORT_HEADER = """---
document_type: migration_report
schema_version: "1.0"
produced_at: {ts}
produced_by: migrate_v073_to_v074_tier_to_phase.py
from_version: "0.7.3"
to_version: "0.7.4"
idempotent: true
---

# v0.7.3 -> v0.7.4 migration report

This report enumerates every surface that the Tier -> Phase migration touched
in this project.  Review it, then append the following line to the
`reviews/classification.md` YAML frontmatter to clear the Planner's Phase-0
hold on the next v0.7.4 invocation:

    user_confirmed_migration_report_at: {ts}

Migration is idempotent: re-running the script on an already-migrated project
is safe and re-emits this report.

"""


def _write_report(
    reviews_dir: Path, report_lines: list[str], dry_run: bool
) -> Path:
    path = reviews_dir / "migration_report_v073_to_v074.md"
    body = REPORT_HEADER.format(ts=_iso_now()) + "\n".join(report_lines) + "\n"
    if dry_run:
        # In dry-run mode still print the report to stderr; do not write it.
        sys.stderr.write("\n--- migration report (dry-run; not written) ---\n")
        sys.stderr.write(body)
        sys.stderr.write("--- end report ---\n")
        return path
    path.write_text(body, encoding="utf-8")
    return path


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="Migrate a project's reviews/ artefacts from v0.7.3 "
        "(Tier lexicon) to v0.7.4 (Phase lexicon)."
    )
    ap.add_argument(
        "--project-root",
        required=True,
        type=Path,
        help="Absolute path to the project root (the dir containing reviews/).",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write any files; emit the report to stderr instead.",
    )
    args = ap.parse_args(argv)

    project_root: Path = args.project_root
    if not project_root.is_dir():
        sys.stderr.write(
            f"error: --project-root is not a directory: {project_root}\n"
        )
        return 2

    reviews_dir = project_root / "reviews"
    if not reviews_dir.is_dir():
        sys.stderr.write(f"error: reviews/ not found under {project_root}\n")
        return 3

    report_lines: list[str] = []

    # --- tier_state.json / phase_state.json ---
    tier_path = reviews_dir / "tier_state.json"
    phase_path = reviews_dir / "phase_state.json"

    if phase_path.exists() and not tier_path.exists():
        report_lines.append(
            "- reviews/phase_state.json already present and tier_state.json absent; "
            "migration previously completed (idempotent no-op)."
        )
    elif not tier_path.exists() and not phase_path.exists():
        report_lines.append(
            "- neither reviews/tier_state.json nor reviews/phase_state.json found; "
            "nothing to migrate at the ledger surface."
        )
    else:
        # Prefer tier_state.json as the source; if phase_state.json also exists
        # (partial prior run), prefer it.
        source = phase_path if phase_path.exists() else tier_path
        report_lines.append(f"- reading ledger source: {source.name}")

        try:
            doc = json.loads(source.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            sys.stderr.write(f"error: JSON parse failed on {source}: {exc}\n")
            return 4

        try:
            migrated = _migrate_tier_state(doc, report_lines)
        except ValueError as exc:
            sys.stderr.write(f"error: invariant violation: {exc}\n")
            return 6

        if args.dry_run:
            report_lines.append(
                f"    (dry-run: would write reviews/phase_state.json "
                f"({len(json.dumps(migrated))} bytes))"
            )
        else:
            # Atomic-ish write: write phase_state.json first, then remove
            # tier_state.json only after success.
            try:
                phase_path.write_text(
                    json.dumps(migrated, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
            except OSError as exc:
                sys.stderr.write(f"error: failed to write {phase_path}: {exc}\n")
                return 5
            if tier_path.exists() and tier_path != phase_path:
                # Move the old file to a .bak so a round-trip has history.
                backup = tier_path.with_suffix(".json.v073.bak")
                try:
                    shutil.move(str(tier_path), str(backup))
                    report_lines.append(
                        f"    - moved tier_state.json -> {backup.name} (backup)"
                    )
                except OSError as exc:
                    sys.stderr.write(
                        f"warning: failed to back up {tier_path}: {exc}\n"
                    )
            report_lines.append(
                f"    + wrote reviews/phase_state.json (schema_version="
                f"{SCHEMA_VERSION_AFTER})"
            )

    # --- classification.md ---
    class_path = reviews_dir / "classification.md"
    if class_path.exists():
        report_lines.append("- rewriting reviews/classification.md frontmatter:")
        try:
            before = class_path.read_text(encoding="utf-8")
        except OSError as exc:
            sys.stderr.write(f"error: failed to read {class_path}: {exc}\n")
            return 5
        after = _migrate_classification_md(before, report_lines)
        if before == after:
            report_lines.append("    (no changes required)")
        elif args.dry_run:
            report_lines.append("    (dry-run: would write classification.md)")
        else:
            try:
                class_path.write_text(after, encoding="utf-8")
            except OSError as exc:
                sys.stderr.write(f"error: failed to write {class_path}: {exc}\n")
                return 5
    else:
        report_lines.append(
            "- reviews/classification.md not found; skipping frontmatter rewrite."
        )

    # --- completion-artefact file renames ---
    report_lines.append("- completion-artefact file renames:")
    _rename_completion_files(reviews_dir, report_lines, args.dry_run)

    # --- report ---
    report_path = _write_report(reviews_dir, report_lines, args.dry_run)
    if not args.dry_run:
        sys.stdout.write(f"migration report written: {report_path}\n")
    else:
        sys.stdout.write(f"dry-run complete; no files written.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
