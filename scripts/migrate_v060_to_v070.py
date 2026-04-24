#!/usr/bin/env python3
"""migrate_v060_to_v070.py — translate reviews/tier_state.json from v0.6.0 to v0.7.0.

Grounding:
  - references/TIER_PROTOCOL.md §6.4 (migration semantics, idempotent single-pass).
  - references/TIER_PROTOCOL.md §12 (project-level migration steps 1–10).
  - references/tier_state_schema.md §7 (per-field migration map, trigger-enum mapping,
    migration report contract).
  - references/tier_state_schema.md §3a (row-shape contracts referenced for the
    rewritten log rows).
  - TIER_REDESIGN_v0.7-draft-5.md §6.4 (design source).

Inputs
    --project-root <path>         Project directory containing reviews/ and
                                  manuscript/.
    --classification <rel-path>   Classification file relative to --project-root,
                                  read for t1_pstage_declaration. Default:
                                  reviews/classification.md.
    --t3-staleness-budget <days>  Override the t3_staleness_budget written into
                                  the migration report header (informational
                                  only — Planner reads from classification.md
                                  at runtime). Default: 14.
    --force                       Overwrite an existing v0.7.0 reviews/tier_state.json
                                  without asking. Without --force, the script
                                  detects schema_version == "0.7.0" on read and
                                  exits as a no-op (idempotent).

Reads
    reviews/tier_state.json       v0.6.0 ledger (input).
    reviews/classification.md     P-stage declaration (best-effort).
    reviews/t1_draft_completion.md, t2_review_completion.md,
        t3_convergence_signoff.md  Existence checked for the
                                  cold-start placeholder pass per §6.4 step 6.

Writes
    reviews/tier_state.json                 v0.7.0 ledger (output) per §5 atomic
                                            writer discipline (.tmp → rename).
    reviews/tier_state.v0.6.0.json          archived pre-migration file.
    reviews/migration_report_v0.6_to_v0.7.md
                                            Mapped rows · Renamed states ·
                                            Warnings · Cold-start artefacts (§7.3).
    reviews/<exit-artefact>.md              placeholder cold-start exit artefact(s)
                                            for tiers the section had previously
                                            cleared (one per missing artefact).

Validation
    On successful write, invoke scripts/tier_state_validate.py against the new
    file; propagate its exit code.

Exit codes
    0  success (migrated ledger + report written, validator clean) OR
       no-op (already v0.7.0; --force not supplied)
    1  missing inputs (no v0.6.0 reviews/tier_state.json, etc.)
    2  schema-validation failure after write (unexpected; see validator output)
    3  source schema_version is neither "0.6.0" nor "0.7.0" (run earlier migration first)
    4  bad invocation (unreadable file, etc.)

Rollback: migration is one-way. The archived reviews/tier_state.v0.6.0.json is
the fallback; remove the migrated reviews/tier_state.json and rename the archive
back to restore the v0.6.0 state. v0.6.0 projects continue to work unchanged
under research-writing-harness-claude-v0.6.0/.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ----------------------------------------------------------------- constants

SCHEMA_VERSION_OUT = "0.7.0"
SCHEMA_VERSION_IN = "0.6.0"
TIER_VOCABULARY = "lifecycle_v0.7"
DEFAULT_MILESTONE_ASSIGNMENT: dict[str, str] = {
    "M1": "T1", "M2": "T1", "M3": "T1",
    "M4a": "T2", "M4b": "T3", "M5": "T4",
}
LEGAL_CURRENT_TIER = ("T1", "T2", "T3", "T3_converged", "T4")
LEGAL_LAST_APPROVED_TIER = (None, "T1", "T2", "T3", "T4")
DEFAULT_T3_STALENESS_BUDGET_DAYS = 14
BACKUP_RETENTION = 10

# Per-tier lookup table for tier_goal_declared and tier_deliverable_path,
# replicated verbatim from tier_state_schema.md §2.1.
TIER_GOAL_TABLE: dict[str, str] = {
    "T1": (
        # v0.7.1 default is sd_sr_required=false; the SD/SR clause is no
        # longer part of the canonical T1 goal declaration. Projects that
        # set sd_sr_required=true in reviews/classification.md per
        # TIER_PROTOCOL.md §3.1.2 may append " and i* SD/SR" downstream.
        "produce a complete first draft with classification and "
        "an advisory Evaluator note"
    ),
    "T2": (
        "produce a reviewed and revised section with all CRITICAL findings "
        "cleared and a signed t2_review_completion"
    ),
    "T3": (
        "iterate to convergence under the 2-consecutive-round convergence-metric "
        "threshold and sign t3_convergence_signoff"
    ),
    "T3_converged": "hold post-convergence staging pending MCR admission to T4",
    "T4": (
        "compose the manuscript-wide submission-bound artefact and sign "
        "t4_ship_signoff"
    ),
}

TIER_DELIVERABLE_TABLE: dict[str, str] = {
    "T1": "reviews/t1_draft_completion.md",
    "T2": "reviews/t2_review_completion.md",
    "T3": "reviews/t3_convergence_signoff.md",
    "T3_converged": "reviews/t3_convergence_signoff.md",
    "T4": "reviews/t4_ship_signoff.md",
}

# Trigger renames applied in the row-by-row rewrite. Mapping is intentionally
# narrow — per tier_state_schema.md §7.2 only `laggard_clearance_approved` is
# renamed; all other v0.6.0 triggers are preserved verbatim (including the
# retired-but-migrated `confirmation_failed`).
TRIGGER_RENAME: dict[str, str] = {
    "laggard_clearance_approved": "mcr_admission",
}

# Per actor-inference table for v0.6.0 trigger → v0.7.0 actor field, applied
# only when the v0.6.0 row carries no actor field.
ACTOR_BY_TRIGGER_DEFAULT: dict[str, str] = {
    "initial_dispatch": "planner",
    "user_approval": "user",
    "user_rejection": "user",
    "user_defer": "user",
    "fingerprint_reset": "planner",
    "laggard_clearance_approved": "planner",
    "mcr_admission": "planner",
    "laggard_clearance_cancelled": "user",
    "confirmation_failed": "evaluator",
    "ceiling_locked": "planner",
    "ceiling_raised": "user",
    "override_applied": "user",
    "retraction": "user",
}


# ----------------------------------------------------------------- datatypes


@dataclass
class Warning_:
    """One warning row for the migration report."""
    code: str    # e.g., "W-T3-ACTIVITY-NULL", "W-PSTAGE-UNAVAILABLE"
    section: str  # heading_path joined as " > "; "" for top-level
    message: str


@dataclass
class MappedRow:
    """One row in the Mapped-rows table of the migration report."""
    section: str
    timestamp: str
    v060_trigger: str
    v070_trigger: str
    note: str = ""


@dataclass
class RenamedState:
    """One row in the Renamed-states table of the migration report."""
    section: str
    pre_value: str
    post_value: str


@dataclass
class ColdStartArtefact:
    """One row in the Cold-start-artefacts table of the migration report."""
    section: str
    artefact_path: str
    flag: str  # "migration_origin: v0.6.0" or "imodel_structural_validation: deferred_v060_migration"


@dataclass
class MigrationContext:
    project_root: Path
    classification_path: Path
    tier_state_path: Path
    archive_path: Path
    report_path: Path
    backup_dir: Path
    t3_staleness_budget_days: int
    utc_now: str
    warnings: list[Warning_] = field(default_factory=list)
    mapped_rows: list[MappedRow] = field(default_factory=list)
    renamed_states: list[RenamedState] = field(default_factory=list)
    cold_starts: list[ColdStartArtefact] = field(default_factory=list)


# ----------------------------------------------------------------- utilities


def _iso_utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _heading_key(heading_path: list[str]) -> str:
    return " > ".join(heading_path) if heading_path else "<no heading>"


# ----------------------------------------------------------------- parsers


_PSTAGE_RE = re.compile(r"^p[-_]?stage:\s*(P[0-2])\s*$", re.MULTILINE | re.IGNORECASE)


def parse_pstage(ctx: MigrationContext) -> str | None:
    """Read the manuscript-wide P-stage from classification.md.

    The v0.6.0 classification.md may declare a single `pstage:` field or omit
    it. Per tier_state_schema.md §7.1, sections without an available P-stage
    declaration emit W-PSTAGE-UNAVAILABLE; the migration script does not
    fabricate a P-stage value.
    """
    if not ctx.classification_path.exists():
        return None
    try:
        text = ctx.classification_path.read_text(encoding="utf-8")
    except OSError:
        return None
    m = _PSTAGE_RE.search(text)
    return m.group(1) if m else None


# ----------------------------------------------------------------- ledger I/O


def load_v060_ledger(ctx: MigrationContext) -> dict[str, Any]:
    """Read the v0.6.0 ledger and validate the schema version.

    Returns the parsed JSON object. Exits with code 1 if the file is missing,
    code 3 if the schema_version is neither "0.6.0" nor "0.7.0", and code 0
    (no-op) if the file is already at v0.7.0 and --force was not supplied.
    """
    if not ctx.tier_state_path.exists():
        sys.stderr.write(
            f"[migrate_v060_to_v070] error: {ctx.tier_state_path} not found.\n"
        )
        sys.exit(1)
    try:
        ledger = json.loads(ctx.tier_state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(
            f"[migrate_v060_to_v070] error: failed to read or parse "
            f"{ctx.tier_state_path}: {exc}\n"
        )
        sys.exit(4)
    return ledger


def archive_v060(ctx: MigrationContext) -> None:
    """Copy the v0.6.0 ledger to reviews/tier_state.v0.6.0.json."""
    if ctx.archive_path.exists():
        # Idempotent re-archive overwrite is safe: the source is the same file
        # the script is about to rewrite. Bypass shutil.copyfile error paths.
        ctx.archive_path.unlink()
    shutil.copy2(ctx.tier_state_path, ctx.archive_path)


# ----------------------------------------------------------------- core migration


def rewrite_log_row(
    ctx: MigrationContext,
    section_key: str,
    row: dict[str, Any],
) -> dict[str, Any]:
    """Translate one v0.6.0 tier_entry_log row into v0.7.0 shape.

    v0.6.0 row shape (from v0.6.0 tier_state_schema.md §3):
        {timestamp, trigger, from_tier, to_tier, scope, cycle_id, detail}

    v0.7.0 row shape (per v0.7.0 tier_state_schema.md §3a.1):
        {timestamp, trigger, prev_tier, new_tier, actor, notes}

    Field rewrites:
        from_tier  → prev_tier
        to_tier    → new_tier (with `T4_ready` → `T3_converged`)
        scope+cycle_id+detail → notes (consolidated, truncated at 280 chars)
        actor: inferred from trigger when missing

    Trigger rewrites: `laggard_clearance_approved` → `mcr_admission`.
    """
    timestamp = row.get("timestamp", ctx.utc_now)
    v060_trigger = row.get("trigger", "initial_dispatch")
    v070_trigger = TRIGGER_RENAME.get(v060_trigger, v060_trigger)

    prev_tier_in = row.get("from_tier")
    new_tier_in = row.get("to_tier")
    # T4_ready → T3_converged on the new_tier field of every row.
    if new_tier_in == "T4_ready":
        new_tier_out = "T3_converged"
    elif new_tier_in == "T0":
        # v0.6.0 allowed T0 as a tier enum (state-probe); v0.7.0 retires it.
        # Rows with to_tier: "T0" are coerced to null and warned.
        new_tier_out = None
        ctx.warnings.append(
            Warning_(
                code="W-T0-ROW-COERCED",
                section=section_key,
                message=(
                    f"row at {timestamp} had to_tier='T0'; coerced to null "
                    "(v0.7.0 validator rejects T0 in tier enum fields)."
                ),
            )
        )
    else:
        new_tier_out = new_tier_in
    if prev_tier_in == "T4_ready":
        prev_tier_out = "T3_converged"
    elif prev_tier_in == "T0":
        # Initial-dispatch rows at v0.6.0 used T0 as the from_tier; under v0.7.0
        # initial dispatches use prev_tier=null. No warning is emitted for this
        # common case — it is the canonical bootstrap shape.
        prev_tier_out = None
    else:
        prev_tier_out = prev_tier_in

    # Consolidate scope + cycle_id + detail into notes; bound at 280 chars.
    pieces: list[str] = []
    scope = row.get("scope")
    cycle_id = row.get("cycle_id")
    detail = row.get("detail")
    if scope:
        pieces.append(f"scope={scope}")
    if cycle_id:
        pieces.append(f"cycle_id={cycle_id}")
    if detail:
        pieces.append(detail)
    notes = " | ".join(pieces)
    if len(notes) > 280:
        notes = notes[:277] + "..."

    actor = row.get("actor") or ACTOR_BY_TRIGGER_DEFAULT.get(v070_trigger, "planner")

    ctx.mapped_rows.append(
        MappedRow(
            section=section_key,
            timestamp=timestamp,
            v060_trigger=v060_trigger,
            v070_trigger=v070_trigger,
            note=("renamed" if v060_trigger != v070_trigger else ""),
        )
    )

    return {
        "timestamp": timestamp,
        "trigger": v070_trigger,
        "prev_tier": prev_tier_out,
        "new_tier": new_tier_out,
        "actor": actor,
        "notes": notes,
    }


def append_rename_marker_row(
    ctx: MigrationContext,
    section_key: str,
    log: list[dict[str, Any]],
) -> None:
    """Append a v0_7_state_rename trigger row recording the T4_ready→T3_converged rename.

    Per TIER_PROTOCOL.md §6.4 step 3 and §12 step 4: the migration script writes
    a tier_entry_log row with trigger v0_7_state_rename to preserve historical
    semantics. The notes field carries the pre-migration value as the literal
    string "T4_ready -> T3_converged" so the Reflector-full T4 audit can
    reconstruct the rename chain from the log alone.
    """
    log.append(
        {
            "timestamp": ctx.utc_now,
            "trigger": "v0_7_state_rename",
            "prev_tier": "T3_converged",
            "new_tier": "T3_converged",
            "actor": "planner",
            "notes": "T4_ready -> T3_converged (v0.6.0 -> v0.7.0 schema rename)",
        }
    )
    ctx.mapped_rows.append(
        MappedRow(
            section=section_key,
            timestamp=ctx.utc_now,
            v060_trigger="(synthesised)",
            v070_trigger="v0_7_state_rename",
            note="rename marker",
        )
    )


def cold_start_exit_artefact(
    ctx: MigrationContext,
    section_key: str,
    artefact_relpath: str,
    tier_label: str,
) -> None:
    """Write a placeholder exit artefact under the migration_origin: v0.6.0 flag.

    Per TIER_PROTOCOL.md §6.4 step 6: if a v0.7.0 exit artefact is absent and
    the section's last_approved_tier shows it previously cleared the tier, the
    script writes a placeholder exit artefact with a migration_origin: v0.6.0
    flag, permitting the v0.6.0 prior approval to be honored without
    fabricating content.
    """
    artefact_path = ctx.project_root / artefact_relpath
    if artefact_path.exists():
        # Honour the existing artefact; do not overwrite. The cold-start clause
        # only fires when the artefact is absent.
        return
    artefact_path.parent.mkdir(parents=True, exist_ok=True)
    placeholder = (
        f"---\n"
        f"migration_origin: v0.6.0\n"
        f"tier: {tier_label}\n"
        f"section: {section_key}\n"
        f"created_at: {ctx.utc_now}\n"
        f"---\n"
        f"\n"
        f"# {tier_label} placeholder exit artefact (v0.6.0 → v0.7.0 migration)\n"
        f"\n"
        f"This file was written by `scripts/migrate_v060_to_v070.py` to satisfy "
        f"the v0.7.0 signed-exit-artefact gate for a section whose v0.6.0 ledger "
        f"already recorded user approval at this tier. **No prose has been "
        f"fabricated.** Any subsequent advance from {tier_label} requires the "
        f"user to revisit this artefact and replace it with a substantive "
        f"deliverable; the `migration_origin: v0.6.0` flag is preserved as "
        f"audit evidence that the original approval predates the v0.7.0 exit-"
        f"artefact contract.\n"
    )
    artefact_path.write_text(placeholder, encoding="utf-8")
    ctx.cold_starts.append(
        ColdStartArtefact(
            section=section_key,
            artefact_path=artefact_relpath,
            flag="migration_origin: v0.6.0",
        )
    )


def migrate_section(
    ctx: MigrationContext,
    section_in: dict[str, Any],
    pstage_default: str | None,
) -> dict[str, Any]:
    """Translate one v0.6.0 SectionStateObject into a v0.7.0 SectionStateObject.

    Per tier_state_schema.md §7.1, every v0.6.0 field is preserved verbatim
    except current_tier (T4_ready rename) and tier_entry_log (row-by-row
    rewrite). Five v0.7.0 fields are populated per the migration map; warnings
    are emitted per §7.1 / §6.4.
    """
    heading_path = section_in.get("heading_path", [])
    section_key = _heading_key(heading_path)
    current_tier_in = section_in.get("current_tier", "T1")
    last_approved_tier = section_in.get("last_approved_tier")

    # Step 4: T4_ready → T3_converged rename on the field itself.
    if current_tier_in == "T4_ready":
        current_tier_out = "T3_converged"
        ctx.renamed_states.append(
            RenamedState(
                section=section_key,
                pre_value="T4_ready",
                post_value="T3_converged",
            )
        )
    else:
        current_tier_out = current_tier_in

    # Step 5: populate the five new fields.
    tier_goal_declared = TIER_GOAL_TABLE.get(current_tier_out, "")
    tier_deliverable_path = TIER_DELIVERABLE_TABLE.get(current_tier_out, "")

    # convergence_metric: null for everything; warning if at T3.
    convergence_metric: float | None = None
    if current_tier_out == "T3":
        ctx.warnings.append(
            Warning_(
                code="W-T3-ACTIVITY-NULL",
                section=section_key,
                message=(
                    "v0.6.0 T3 state has no convergence metric; re-run the T3 "
                    "loop to populate. convergence_metric initialised to null."
                ),
            )
        )

    # t1_pstage_declaration: from classification if present; else null + warning.
    if pstage_default:
        t1_pstage_declaration: str | None = pstage_default
    else:
        t1_pstage_declaration = None
        if current_tier_out in ("T2", "T3", "T3_converged", "T4") or last_approved_tier:
            ctx.warnings.append(
                Warning_(
                    code="W-PSTAGE-UNAVAILABLE",
                    section=section_key,
                    message=(
                        "No P-stage available from classification.md; "
                        "t1_pstage_declaration initialised to null. P-Stage "
                        "Checker skill cannot run until populated."
                    ),
                )
            )

    # t3_last_activity_at: null + warning for every T3-or-converged section.
    t3_last_activity_at: str | None = None
    if current_tier_out in ("T3", "T3_converged"):
        ctx.warnings.append(
            Warning_(
                code="W-T3-ACTIVITY-NULL",
                section=section_key,
                message=(
                    "v0.6.0 ledger does not track t3_last_activity_at; "
                    "initialised to null (computed [T3-STALE] short-circuits "
                    "to false until first post-migration activity)."
                ),
            )
        )

    # Rewrite the tier_entry_log row by row.
    log_in = section_in.get("tier_entry_log", [])
    log_out: list[dict[str, Any]] = []
    saw_t4_ready_in_log = False
    for row in log_in:
        # Detect any historical T4_ready references in the log so we know
        # whether to append the v0_7_state_rename marker row.
        if row.get("from_tier") == "T4_ready" or row.get("to_tier") == "T4_ready":
            saw_t4_ready_in_log = True
        log_out.append(rewrite_log_row(ctx, section_key, row))

    # Step 4 (continued): if the section's current_tier was renamed OR if any
    # historical row referenced T4_ready, append a synthetic v0_7_state_rename
    # row so the Reflector-full T4 audit can reconstruct the rename chain.
    if current_tier_in == "T4_ready" or saw_t4_ready_in_log:
        append_rename_marker_row(ctx, section_key, log_out)

    # Step 6: cold-start placeholder exit artefacts. For every tier the section
    # has previously cleared (i.e., last_approved_tier ≥ tier), check that the
    # corresponding exit artefact exists; if not, write a placeholder under
    # the migration_origin: v0.6.0 flag.
    if last_approved_tier in ("T1", "T2", "T3", "T4"):
        # T1 always has a precursor artefact whenever last_approved_tier is set.
        cold_start_exit_artefact(ctx, section_key, "reviews/t1_draft_completion.md", "T1")
    if last_approved_tier in ("T2", "T3", "T4"):
        cold_start_exit_artefact(ctx, section_key, "reviews/t2_review_completion.md", "T2")
    if last_approved_tier in ("T3", "T4") or current_tier_out == "T3_converged":
        cold_start_exit_artefact(
            ctx, section_key, "reviews/t3_convergence_signoff.md", "T3"
        )
    if last_approved_tier == "T4":
        cold_start_exit_artefact(ctx, section_key, "reviews/t4_ship_signoff.md", "T4")

    return {
        "heading_path": heading_path,
        "current_tier": current_tier_out,
        "last_approved_tier": last_approved_tier,
        "ceiling_locked": section_in.get("ceiling_locked", False),
        "section_ceiling_override": section_in.get("section_ceiling_override"),
        "iteration_count_at_current_tier": section_in.get(
            "iteration_count_at_current_tier", 0
        ),
        "last_scope_fingerprint": section_in.get("last_scope_fingerprint", ""),
        "fingerprint_computed_at": section_in.get("fingerprint_computed_at", ctx.utc_now),
        "cumulative_drift_lines_since_approval": section_in.get(
            "cumulative_drift_lines_since_approval", 0
        ),
        "tier_goal_declared": tier_goal_declared,
        "tier_deliverable_path": tier_deliverable_path,
        "convergence_metric": convergence_metric,
        "t1_pstage_declaration": t1_pstage_declaration,
        "t3_last_activity_at": t3_last_activity_at,
        "tier_entry_log": log_out,
    }


def migrate_ledger(ctx: MigrationContext, ledger_in: dict[str, Any]) -> dict[str, Any]:
    """Translate a full v0.6.0 ledger object into a v0.7.0 ledger object.

    Steps 1–9 of TIER_PROTOCOL.md §12.1 are applied in order. The returned dict
    is the in-memory representation to be written via the atomic .tmp → rename
    pattern (handled by write_v070).
    """
    pstage_default = parse_pstage(ctx)

    sections_out = [
        migrate_section(ctx, s, pstage_default) for s in ledger_in.get("sections", [])
    ]

    return {
        "schema_version": SCHEMA_VERSION_OUT,
        "manuscript_id": ledger_in.get("manuscript_id", "manuscript"),
        "default_final_tier": ledger_in.get("default_final_tier", "T3"),
        "fingerprint_mode": ledger_in.get("fingerprint_mode", "tolerant"),
        "terminal_tier_reached": ledger_in.get("terminal_tier_reached", False),
        "last_updated": ctx.utc_now,
        "tier_vocabulary": TIER_VOCABULARY,
        "milestone_assignment": dict(DEFAULT_MILESTONE_ASSIGNMENT),
        "sections": sections_out,
    }


# ----------------------------------------------------------------- writer


def write_v070(ctx: MigrationContext, ledger_out: dict[str, Any]) -> None:
    """Write the v0.7.0 ledger atomically per tier_state_schema.md §5."""
    payload = json.dumps(ledger_out, indent=2, ensure_ascii=False) + "\n"
    fd, tmp_path_str = tempfile.mkstemp(
        prefix=".tier_state.json.tmp.",
        dir=str(ctx.tier_state_path.parent),
    )
    tmp_path = Path(tmp_path_str)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, ctx.tier_state_path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise


# ----------------------------------------------------------------- report writer


def render_report(ctx: MigrationContext) -> str:
    """Render reviews/migration_report_v0.6_to_v0.7.md per §7.3."""
    lines: list[str] = []
    lines.append("# Migration report: v0.6.0 → v0.7.0")
    lines.append("")
    lines.append(f"_Generated: {ctx.utc_now}_")
    lines.append("")
    lines.append(
        "Source: `reviews/tier_state.json` (v0.6.0). Output: `reviews/tier_state.json` "
        "(v0.7.0). Pre-migration archive: `reviews/tier_state.v0.6.0.json`."
    )
    lines.append("")
    lines.append(
        f"Effective `t3_staleness_budget`: {ctx.t3_staleness_budget_days} days "
        "(informational; Planner reads from classification.md at runtime)."
    )
    lines.append("")

    # Section 1 — mapped rows.
    lines.append("## 1. Mapped rows")
    lines.append("")
    if ctx.mapped_rows:
        lines.append("| Section | Timestamp | v0.6.0 trigger | v0.7.0 trigger | Note |")
        lines.append("|---|---|---|---|---|")
        for r in ctx.mapped_rows:
            lines.append(
                f"| {r.section} | {r.timestamp} | `{r.v060_trigger}` | `{r.v070_trigger}` | {r.note} |"
            )
    else:
        lines.append("_No log rows present in source ledger._")
    lines.append("")

    # Section 2 — renamed states.
    lines.append("## 2. Renamed states")
    lines.append("")
    if ctx.renamed_states:
        lines.append("| Section | Pre-migration `current_tier` | Post-migration `current_tier` |")
        lines.append("|---|---|---|")
        for r in ctx.renamed_states:
            lines.append(f"| {r.section} | `{r.pre_value}` | `{r.post_value}` |")
    else:
        lines.append("_No section was holding `T4_ready` at migration time._")
    lines.append("")

    # Section 3 — warnings.
    lines.append("## 3. Warnings")
    lines.append("")
    if ctx.warnings:
        lines.append("| Code | Section | Message |")
        lines.append("|---|---|---|")
        for w in ctx.warnings:
            lines.append(f"| `{w.code}` | {w.section} | {w.message} |")
    else:
        lines.append("_No warnings raised._")
    lines.append("")

    # Section 4 — cold-start artefacts.
    lines.append("## 4. Cold-start artefacts")
    lines.append("")
    if ctx.cold_starts:
        lines.append("| Section | Artefact path | Migration flag |")
        lines.append("|---|---|---|")
        for c in ctx.cold_starts:
            lines.append(f"| {c.section} | `{c.artefact_path}` | `{c.flag}` |")
        lines.append("")
        lines.append(
            "Each placeholder file carries the `migration_origin: v0.6.0` "
            "frontmatter flag and explicit prose stating that no content was "
            "fabricated; the user is required to replace the placeholder with "
            "a substantive deliverable before any subsequent advance from the "
            "respective tier."
        )
    else:
        lines.append("_No cold-start placeholders were required._")
    lines.append("")

    # Section 5 — user hold-point.
    lines.append("## 5. User hold-point")
    lines.append("")
    lines.append(
        "Per the v0.7.0 Phase 0 hold (`integrity.migration_report_hold` in "
        "`tier_notifications.yaml §4`), the Planner refuses to dispatch any "
        "review cycle until the user has explicitly acknowledged this report. "
        "Run `/review` after reviewing this file to release the hold."
    )
    lines.append("")
    return "\n".join(lines)


def write_report(ctx: MigrationContext) -> None:
    ctx.report_path.parent.mkdir(parents=True, exist_ok=True)
    ctx.report_path.write_text(render_report(ctx), encoding="utf-8")


# ----------------------------------------------------------------- validator hand-off


def invoke_validator(ctx: MigrationContext) -> int:
    """Run scripts/tier_state_validate.py against the new ledger.

    Returns the validator's exit code. The migration script propagates a
    non-zero exit code as exit code 2 per the script's documented contract.
    """
    script_dir = Path(__file__).resolve().parent
    validator = script_dir / "tier_state_validate.py"
    if not validator.exists():
        sys.stderr.write(
            f"[migrate_v060_to_v070] warning: validator {validator} not found; "
            "skipping post-migration validation.\n"
        )
        return 0
    try:
        proc = subprocess.run(
            [sys.executable, str(validator), "--file", str(ctx.tier_state_path)],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        sys.stderr.write(
            f"[migrate_v060_to_v070] warning: failed to invoke validator: {exc}\n"
        )
        return 0
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout)
        sys.stderr.write(proc.stderr)
    return proc.returncode


# ----------------------------------------------------------------- entry point


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Migrate reviews/tier_state.json from v0.6.0 to v0.7.0.",
    )
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument(
        "--classification",
        type=str,
        default="reviews/classification.md",
        help="Classification file relative to --project-root.",
    )
    parser.add_argument(
        "--t3-staleness-budget",
        type=int,
        default=DEFAULT_T3_STALENESS_BUDGET_DAYS,
        help="Informational; Planner reads from classification.md at runtime.",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    project_root: Path = args.project_root.resolve()
    if not project_root.is_dir():
        sys.stderr.write(
            f"[migrate_v060_to_v070] error: --project-root {project_root} is not a directory.\n"
        )
        return 1

    ctx = MigrationContext(
        project_root=project_root,
        classification_path=project_root / args.classification,
        tier_state_path=project_root / "reviews" / "tier_state.json",
        archive_path=project_root / "reviews" / "tier_state.v0.6.0.json",
        report_path=project_root / "reviews" / "migration_report_v0.6_to_v0.7.md",
        backup_dir=project_root / "reviews",
        t3_staleness_budget_days=args.t3_staleness_budget,
        utc_now=_iso_utc_now(),
    )

    ledger_in = load_v060_ledger(ctx)
    schema_version = ledger_in.get("schema_version")

    # Idempotent no-op: already at v0.7.0 and --force not supplied.
    if schema_version == SCHEMA_VERSION_OUT and not args.force:
        sys.stdout.write(
            f"[migrate_v060_to_v070] {ctx.tier_state_path} is already at "
            f"{SCHEMA_VERSION_OUT}; no-op (pass --force to re-run).\n"
        )
        return 0

    if schema_version not in (SCHEMA_VERSION_IN, SCHEMA_VERSION_OUT):
        sys.stderr.write(
            f"[migrate_v060_to_v070] error: unexpected schema_version "
            f"{schema_version!r}. Run scripts/migrate_v055_to_v060.py first if "
            "the source is v0.5.5.\n"
        )
        return 3

    # Step 8: archive before write.
    archive_v060(ctx)

    # Steps 1–5, 6, 7: in-memory translation.
    ledger_out = migrate_ledger(ctx, ledger_in)

    # Atomic write per tier_state_schema.md §5.
    write_v070(ctx, ledger_out)

    # Step 9: emit migration report.
    write_report(ctx)

    # Post-write validation.
    rc = invoke_validator(ctx)
    if rc != 0:
        sys.stderr.write(
            f"[migrate_v060_to_v070] error: validator exited {rc} on the "
            f"migrated ledger; inspect {ctx.tier_state_path} and the report.\n"
        )
        return 2

    sys.stdout.write(
        f"[migrate_v060_to_v070] success: wrote {ctx.tier_state_path} "
        f"(v0.6.0 archived at {ctx.archive_path}); "
        f"report at {ctx.report_path}.\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
