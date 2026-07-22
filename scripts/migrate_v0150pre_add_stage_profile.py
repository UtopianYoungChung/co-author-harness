#!/usr/bin/env python3
"""v0.15.0-pre PR-3b.1 — additive stage/profile shadow-field migration.

Derives `stage` and `profile` for every section in `reviews/phase_state.json`
from the existing `current_phase` (and `check_profile` if present), without
mutating `current_phase`, `schema_version`, or any other existing field.

Idempotent: re-running on an already-migrated ledger is a no-op.

This is purely additive — it does not change behaviour, MCR keying, or
vocabulary. Behaviour wiring is deferred to PR-3b.2. The migration exists so
3b.2 can target a real, stable schema surface instead of a moving idea.

Derivation rules (single source of truth — kept here, not in markdown):
    Ph1            -> stage="draft",    profile=None
    Ph2            -> stage="iterate",  profile="refine"
    Ph3            -> stage="iterate",  profile=<check_profile if a legal
                                                 value, else "refine">
    Ph3_converged  -> stage="iterate",  profile="refine"
    Ph4            -> stage="finalize", profile=None

Usage:
    python scripts/migrate_v0150pre_add_stage_profile.py --path reviews/phase_state.json
    python scripts/migrate_v0150pre_add_stage_profile.py --path ... --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Tuple

PHASE_TO_STAGE_PROFILE = {
    "Ph1": ("draft", None),
    "Ph2": ("iterate", "refine"),
    "Ph3": ("iterate", "refine"),  # profile may be overridden by check_profile
    "Ph3_converged": ("iterate", "refine"),
    "Ph4": ("finalize", None),
}

LEGAL_PROFILES = {"refine", "structural", "deep", "stability"}


def derive(section: dict) -> Tuple[str | None, str | None]:
    """Return (stage, profile) derived from section's current_phase.
    If current_phase is missing or unknown, return (None, None) — the caller
    should leave the section untouched so the validator can surface it."""
    cp = section.get("current_phase")
    if cp not in PHASE_TO_STAGE_PROFILE:
        return None, None
    stage, default_profile = PHASE_TO_STAGE_PROFILE[cp]
    if cp == "Ph3":
        cp_check = section.get("check_profile")
        if isinstance(cp_check, str) and cp_check in LEGAL_PROFILES:
            return stage, cp_check
    return stage, default_profile


def migrate_doc(doc: dict) -> Tuple[dict, int, int]:
    """Mutate doc in place; return (doc, sections_updated, sections_skipped).
    A section is 'skipped' iff both shadow fields are already set."""
    updated = 0
    skipped = 0
    sections = doc.get("sections", {})
    if not isinstance(sections, dict):
        return doc, 0, 0
    for _path, section in sections.items():
        if not isinstance(section, dict):
            continue
        has_stage = "stage" in section
        has_profile = "profile" in section
        if has_stage and has_profile:
            skipped += 1
            continue
        stage, profile = derive(section)
        if stage is None:
            continue  # validator will surface a bad current_phase elsewhere
        if not has_stage:
            section["stage"] = stage
        if not has_profile:
            section["profile"] = profile
        updated += 1
    return doc, updated, skipped


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--path", type=Path, required=True,
                        help="reviews/phase_state.json to migrate in place")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the migrated doc to stdout, do not write")
    args = parser.parse_args(argv)

    from destination_capability import DestinationRefused, guard_project_root
    try:
        guard_project_root(args.path)
    except DestinationRefused as exc:
        print(f"[BLOCKER] {exc}", file=sys.stderr)
        return 4

    if not args.path.is_file():
        print(f"[BLOCKER] not a file: {args.path}", file=sys.stderr)
        return 2
    try:
        doc = json.loads(args.path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[BLOCKER] {args.path} is not valid JSON: {exc}", file=sys.stderr)
        return 2

    migrated, updated, skipped = migrate_doc(doc)

    if args.dry_run:
        print(json.dumps(migrated, indent=2, ensure_ascii=False))
    else:
        args.path.write_text(
            json.dumps(migrated, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    print(
        f"OK migrate_v0150pre_add_stage_profile — "
        f"updated {updated} section(s), skipped {skipped} already-migrated"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
