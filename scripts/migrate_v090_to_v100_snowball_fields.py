#!/usr/bin/env python3
# migrate_v090_to_v100_snowball_fields.py
#
# v0.10.0 SectionStateObject migration: extend the 16-field schema (v0.8.0
# β-P-9a) to 18 fields with the snowball-driven reference-scaffolding
# additions specified in `docs/superpowers/plans/2026-04-26-snowball-
# reference-architecture.md §5.4` and the implementation strategy
# `docs/superpowers/plans/2026-04-26-snowball-implementation-strategy.md §3.3`.
#
# **Status: SKELETON** — Stage S0 deliverable. The body of each migration
# step is `raise NotImplementedError(...)` until Stage S2 lands the schema
# additions in `references/phase_state_schema.md`. The skeleton exists at
# S0 so the strategy's pre-flight gate (release-gate.sh entry point) can
# confirm the file is in place; the actual migration logic is authored at
# S2 alongside the schema additions.
#
# Scope (filled at S2)
# --------------------
#   * reviews/phase_state.json
#       - field additions to every SectionStateObject:
#           references_initialized: bool           (default False)
#           last_coverage_score: float | null      (default null)
#       - SectionStateObject field count: 16 -> 18
#       - 30-trigger enum extended to 31 (adds seed_snowball_signed = 31)
#       - schema_version: "0.7.4"  ->  "0.10.0"  (per phase_state_schema.md
#         §1.1 "remains 0.7.4 at the ledger surface until the v0.8.0 RC
#         vocabulary roll" — v0.10.0 is the natural roll point)
#
#   * reviews/classification.md
#       - frontmatter additions:
#           claim_coverage_threshold: 0.8           (S1)
#           auto_redlink_snowball: false            (S4.5)
#           red_link_cap_per_round: 5               (S4.5)
#           inherit_snowball: <true|false>           (S6, default true if
#                                                    wiki_linked: true)
#           pre_seed_cap: 10                        (S6)
#       - the four classification additions land per stage, not all at once;
#         this migration tolerates absence of any of them (sets defaults)
#
# Idempotency
# -----------
#   * If `references_initialized` is already present on a section, leave it.
#     The heuristic-based default-set (true if REFERENCES.md has a non-empty
#     core/snowball table; else false) only fires on first migration.
#   * If `last_coverage_score` is already present, leave it (preserves
#     historical scores from a prior v0.10.0 run that may have been rolled
#     back and re-migrated).
#   * If `schema_version` is already "0.10.0", emit a "migration already
#     complete" report and exit 0 without writing.
#
# Out of scope
# ------------
#   * Skill file additions (skills/seed-snowball-discovery/, etc.) are
#     plugin-level, not project-level, and ship inside the v0.10.0 release zip.
#   * REFERENCES.md format changes (core / snowball / cited-via tables): the
#     format already exists per SK-15; v0.10.0 does not modify the table
#     shape.
#   * external_verification_log.md row format: unchanged from v0.9.0.
#
# Usage (at S2)
# -------------
#   python migrate_v090_to_v100_snowball_fields.py --project-root /path/to/project
#   python migrate_v090_to_v100_snowball_fields.py --project-root /path --dry-run
#   python migrate_v090_to_v100_snowball_fields.py --validate scripts/fixtures/phase_state_smoketest/v090_to_v100/
#
# Exit codes
# ----------
#   0  success (migration ran or was already complete)
#   1  usage error
#   2  project-root missing or not a directory
#   3  reviews/ subdir not found
#   4  JSON parse error on phase_state.json
#   5  write failure
#   6  invariant violation (SectionStateObject field count out of {16, 17, 18})
#   7  classification.md not parseable (YAML frontmatter)
#   8  references/REFERENCES.md format unrecognised (heuristic for
#       references_initialized default-set fails)

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any

# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------

SCHEMA_FROM = "0.7.4"   # v0.8.0 ledger surface still reads 0.7.4 per
                         # phase_state_schema.md §1.1; v0.10.0 is the roll.
SCHEMA_TO = "0.10.0"

NEW_TRIGGER_ID = 31
NEW_TRIGGER_NAME = "seed_snowball_signed"

CLASSIFICATION_DEFAULTS = {
    "claim_coverage_threshold": 0.8,
    "auto_redlink_snowball": False,
    "red_link_cap_per_round": 5,
    "inherit_snowball": True,   # only set when wiki_linked: true; else False
    "pre_seed_cap": 10,
}


# ----------------------------------------------------------------------------
# Migration steps (skeleton — implemented at S2)
# ----------------------------------------------------------------------------


def add_references_initialized_field(sections: dict, project_root: Path) -> dict:
    """Add `references_initialized: bool` to every SectionStateObject.

    Heuristic for the default value:
        - True if `<project_root>/references/REFERENCES.md` exists AND has
          at least one row in the core corpus table or the snowball table
          (regex match on `^| <citation_key> |` row pattern under each
          table header).
        - False otherwise.

    Idempotent: sections that already carry the field are skipped.
    """
    raise NotImplementedError("S2 deliverable: implement after schema additions land in phase_state_schema.md")


def add_last_coverage_score_field(sections: dict) -> dict:
    """Add `last_coverage_score: float | null` to every SectionStateObject.

    Always defaults to None (no historical data to backfill at v0.9.0 -> v0.10.0).
    Idempotent: sections that already carry the field are skipped.
    """
    raise NotImplementedError("S2 deliverable: implement after schema additions land in phase_state_schema.md")


def update_schema_version(state: dict) -> dict:
    """Bump top-level `schema_version` from 0.7.4 to 0.10.0.

    Per phase_state_schema.md §1.1: the schema_version surface "remains
    `0.7.4` at the ledger surface until the v0.8.0 RC vocabulary roll".
    v0.10.0 is the named roll point.
    """
    raise NotImplementedError("S2 deliverable: implement after schema additions land in phase_state_schema.md")


def extend_classification_md(classification_path: Path, wiki_linked: bool) -> str:
    """Add the five new fields to `reviews/classification.md` frontmatter.

    Defaults per CLASSIFICATION_DEFAULTS, with the special rule that
    `inherit_snowball` is True only when `wiki_linked: true` is present;
    else False.

    Idempotent: existing values are preserved; missing fields are appended
    with defaults; the YAML frontmatter is re-emitted in canonical key order.
    """
    raise NotImplementedError("S2 deliverable: implement at S2 (claim_coverage_threshold), S4.5 (auto_redlink_snowball, red_link_cap_per_round), S6 (inherit_snowball, pre_seed_cap)")


# ----------------------------------------------------------------------------
# Migration report
# ----------------------------------------------------------------------------


def write_migration_report(project_root: Path, summary: dict) -> Path:
    """Author `reviews/migration_report_v090_to_v100.md` per the §7 convention
    (analogue of migrate_convergence_log_v074's report-emission discipline).

    The report is the user-blocking gate: the Planner refuses any new
    SK-NEW-A / SK-NEW-B / SK-NEW-C / SK-NEW-D dispatch until the user
    signs the report by appending `user_confirmed_migration_report_at`
    to the report frontmatter.
    """
    raise NotImplementedError("S2 deliverable: implement after schema additions land")


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="v0.9.0 -> v0.10.0 SectionStateObject migration: extend "
                    "the 16-field schema to 18 fields with the snowball-driven "
                    "reference-scaffolding additions.",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        help="Path to the project root (the directory containing reviews/, references/, manuscript/).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute the migration delta but do not write any files. "
             "Emits the report to stdout instead of reviews/migration_report_v090_to_v100.md.",
    )
    parser.add_argument(
        "--validate",
        type=Path,
        help="Validate against a smoketest fixture directory (containing pass/ and block/ subdirs). "
             "Exits 0 if all pass-fixture migrations succeed and all block-fixture migrations refuse.",
    )
    args = parser.parse_args(argv)

    if args.validate:
        # Fixture-validation path (used by release-gate.sh at v0.10.0 RC).
        raise NotImplementedError(
            "S2 deliverable: implement fixture-validation harness against "
            "scripts/fixtures/phase_state_smoketest/v090_to_v100/"
        )

    if args.project_root is None:
        parser.error("--project-root is required (unless --validate is given)")

    project_root = args.project_root.resolve()
    if not project_root.is_dir():
        print(f"[ENV ERROR] project root not a directory: {project_root}", file=sys.stderr)
        return 2

    reviews = project_root / "reviews"
    if not reviews.is_dir():
        print(f"[ENV ERROR] reviews/ subdir not found under {project_root}", file=sys.stderr)
        return 3

    # S2 deliverable: wire up the four migration steps + report emission.
    raise NotImplementedError(
        "S0 skeleton: full migration body lands at S2. The skeleton ensures "
        "the file exists for the v0.10.0 pre-flight gate. Re-author at S2 "
        "alongside the phase_state_schema.md §2 schema additions."
    )


if __name__ == "__main__":
    sys.exit(main())
