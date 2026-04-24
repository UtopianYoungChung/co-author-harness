#!/usr/bin/env python3
"""migrate_classification_to_tier.py — v0.5.5 (Phase F.1)

Migration helper for the Incremental Tier Protocol's v0.4.x → v0.5.x
classification-vocabulary transition. Rewrites `reviews/classification.md` in a
project root so that a legacy `review_depth: {quick|standard|submission-bound}`
field is replaced with a `tier: {T1|T3|T4}` field per the retired transitional
read-path:

    quick            → T1
    standard         → T3
    submission-bound → T4

The helper recognises two source forms:

    1. YAML-lite frontmatter field — the canonical form. Rewrites in place.
    2. Narrative-markdown table cell of the form
           | **Review depth** | `standard` | <reason> |
       (with tolerance for emphasis, backticks, case, and underscore variants).
       This fallback prepends a minimal frontmatter block carrying the
       derived `tier:` without mutating the original table row.

Discipline:

    * stdlib-only (no pip install required)
    * idempotent (second run is a no-op once `tier:` is present)
    * backup-emitting (writes a `.bak` sibling before any mutation)
    * preserves the original `review_depth:` line as a commented reference
      (frontmatter path); leaves the table row untouched (fallback path)
    * refuses to guess: ambiguous, duplicated, or unknown-value table cells
      trigger WARN, not a silent rewrite
    * exit codes mirror the Marshal: 0 = PASS (migrated or no-op),
      1 = WARN (something unexpected but non-blocking), 2 = BLOCK (cannot
      migrate — ambiguous value, missing frontmatter AND no table cell, etc.)

Usage:
    python3 scripts/migrate_classification_to_tier.py --project-root /path/to/project
    python3 scripts/migrate_classification_to_tier.py --project-root . --dry-run

The `--dry-run` flag prints the intended edit and the would-be backup path
without writing anything. Useful for pre-flighting a migration across many
project roots.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

EXIT_PASS = 0
EXIT_WARN = 1
EXIT_BLOCK = 2

REVIEW_DEPTH_TO_TIER = {
    "quick": "T1",
    "standard": "T3",
    "submission-bound": "T4",
    "submission_bound": "T4",  # defensive: underscore variant
}

REVIEW_DEPTH_RE = re.compile(
    r"^review_depth\s*:\s*(?P<value>[A-Za-z\-_]+)\s*$",
    re.MULTILINE,
)
TIER_RE = re.compile(
    r"^tier\s*:\s*(?P<value>T[0-4]R?)\s*$",
    re.MULTILINE,
)
FRONTMATTER_FENCE = re.compile(r"^---\s*$", re.MULTILINE)

# Table-cell fallback. Matches a markdown-table row whose first cell is a
# "review depth" label (with optional bold emphasis, either spelling) and whose
# second cell is one of the legal legacy values (with optional backticks and
# the underscore variant). Third-cell reason text is ignored.
#
# Examples matched:
#     | **Review depth** | `standard`        | Not submission-bound ... |
#     | Review depth     | submission-bound  | Journal-bound revision.  |
#     | review_depth     | quick             | Triage pass.             |
REVIEW_DEPTH_CELL_RE = re.compile(
    r"^\|\s*\*{0,2}\s*review[\s_\-]?depth\s*\*{0,2}\s*\|"
    r"\s*`?\s*(?P<value>quick|standard|submission[-_]bound)\s*`?\s*\|",
    re.MULTILINE | re.IGNORECASE,
)


def _find_frontmatter(text: str) -> tuple[int, int] | None:
    """Return (start, end) character offsets of the frontmatter body (between
    the two `---` fences), or None if no frontmatter is present."""
    fences = [m for m in FRONTMATTER_FENCE.finditer(text)]
    if len(fences) < 2:
        return None
    # Frontmatter body is between end-of-first-fence-line and start-of-second.
    start = fences[0].end()
    end = fences[1].start()
    if start >= end:
        return None
    return start, end


def _locate_classification(project_root: Path) -> Path:
    """Resolve the classification record within the project root.

    Canonical location: <project_root>/reviews/classification.md.
    """
    return project_root / "reviews" / "classification.md"


def _write_backup(target: Path) -> Path:
    """Copy `target` to `target.with_suffix(target.suffix + '.bak')`, without
    clobbering an existing backup. If a `.bak` already exists, suffix with
    `.bak.1`, `.bak.2`, etc., until a free slot is found."""
    backup = target.with_suffix(target.suffix + ".bak")
    if not backup.exists():
        backup.write_bytes(target.read_bytes())
        return backup
    i = 1
    while True:
        candidate = target.with_suffix(target.suffix + f".bak.{i}")
        if not candidate.exists():
            candidate.write_bytes(target.read_bytes())
            return candidate
        i += 1


def _table_cell_fallback(
    target: Path, text: str, *, dry_run: bool
) -> tuple[int, str] | None:
    """Attempt the markdown-table-cell migration path.

    Returns (exit_code, message) on hit (PASS or WARN), or None if the
    fallback is not applicable (no matching row found). Called from the two
    sites where the frontmatter path produced no `tier:` — either because the
    file has no frontmatter at all or because its frontmatter carries neither
    `tier:` nor `review_depth:`.
    """
    matches = list(REVIEW_DEPTH_CELL_RE.finditer(text))
    if not matches:
        return None
    if len(matches) > 1:
        values = sorted({m.group("value").lower() for m in matches})
        return (
            EXIT_WARN,
            f"{target} carries {len(matches)} 'Review depth' table rows "
            f"(values: {values}); refusing to guess which is authoritative. "
            "Remove duplicate rows or add a tier: frontmatter block by hand.",
        )
    match = matches[0]
    legacy_value = match.group("value").lower().replace("_", "-")
    new_tier = REVIEW_DEPTH_TO_TIER.get(legacy_value) or REVIEW_DEPTH_TO_TIER.get(
        legacy_value.replace("-", "_")
    )
    if new_tier is None:
        # Regex already restricted to legal values, so this is a defensive path.
        return (
            EXIT_BLOCK,
            f"{target} table-cell value '{legacy_value}' is not one of "
            "{quick, standard, submission-bound}.",
        )

    # Synthesize a minimal frontmatter block to prepend. The original table row
    # is left intact as narrative evidence.
    prepend = (
        "---\n"
        f"tier: {new_tier}\n"
        f"# [migrated via table-cell fallback at v0.5.5 — derived from "
        f"\"Review depth | {legacy_value}\" row; table row preserved below]\n"
        "---\n\n"
    )

    if dry_run:
        return (
            EXIT_PASS,
            f"Dry-run: would prepend frontmatter block to {target} "
            f"(tier:{new_tier} via table-cell fallback; "
            f"backup would land at {target}.bak). "
            "Original table row preserved.",
        )

    backup = _write_backup(target)
    target.write_text(prepend + text, encoding="utf-8")
    return (
        EXIT_PASS,
        f"Migrated {target} via table-cell fallback: "
        f"Review depth={legacy_value} → tier:{new_tier}. "
        f"Prepended frontmatter block; original table row preserved. "
        f"Backup at {backup}.",
    )


def migrate(
    project_root: Path,
    *,
    dry_run: bool = False,
) -> tuple[int, str]:
    """Perform the migration. Returns (exit_code, message)."""
    target = _locate_classification(project_root)
    if not target.exists():
        return (
            EXIT_BLOCK,
            f"classification record not found at {target}. "
            "Expected <project_root>/reviews/classification.md.",
        )

    text = target.read_text(encoding="utf-8")
    frontmatter_bounds = _find_frontmatter(text)
    if frontmatter_bounds is None:
        # Fallback: look for a "| Review depth | <value> |" markdown-table row.
        fallback = _table_cell_fallback(target, text, dry_run=dry_run)
        if fallback is not None:
            return fallback
        return (
            EXIT_BLOCK,
            f"{target} does not carry YAML-lite frontmatter (missing --- fences) "
            "and no 'Review depth | <value>' markdown-table row was found. "
            "Cannot migrate without at least one structural anchor.",
        )

    fm_start, fm_end = frontmatter_bounds
    frontmatter_body = text[fm_start:fm_end]

    tier_match = TIER_RE.search(frontmatter_body)
    depth_match = REVIEW_DEPTH_RE.search(frontmatter_body)

    # Idempotent: tier: present, review_depth: absent → no-op PASS.
    if tier_match is not None and depth_match is None:
        return (
            EXIT_PASS,
            f"{target} already carries tier:{tier_match.group('value')}; "
            "no migration needed (idempotent no-op).",
        )

    # Idempotent but noisy: both tier: and review_depth: present → remove
    # review_depth and WARN about the duplicated field (a previous partial
    # migration or a human edit).
    if tier_match is not None and depth_match is not None:
        if dry_run:
            return (
                EXIT_WARN,
                f"{target} carries both tier:{tier_match.group('value')} "
                f"and review_depth:{depth_match.group('value')}. "
                "Dry-run: would remove the review_depth line.",
            )
        backup = _write_backup(target)
        new_fm = (
            frontmatter_body[: depth_match.start()]
            + f"# review_depth:{depth_match.group('value')}  "
              "# [migrated to tier: at v0.5.5 — preserved as comment]\n"
            + frontmatter_body[depth_match.end() :]
        )
        # Remove the original review_depth line and leave the commented form.
        # Simpler: just comment the review_depth line in place.
        commented = (
            frontmatter_body[: depth_match.start()]
            + f"# review_depth: {depth_match.group('value')}  "
              "# [superseded by tier: at v0.5.5]"
            + frontmatter_body[depth_match.end() :]
        )
        new_text = text[:fm_start] + commented + text[fm_end:]
        target.write_text(new_text, encoding="utf-8")
        return (
            EXIT_WARN,
            f"{target} carried both tier: and review_depth:; the legacy "
            f"review_depth line has been commented out. Backup at {backup}.",
        )

    # The interesting case: review_depth: present, tier: absent → migrate.
    if depth_match is not None and tier_match is None:
        legacy_value = depth_match.group("value").lower()
        new_tier = REVIEW_DEPTH_TO_TIER.get(legacy_value)
        if new_tier is None:
            return (
                EXIT_BLOCK,
                f"{target} carries review_depth:{legacy_value} which is not "
                "one of the legal legacy values {quick, standard, "
                "submission-bound}. Cannot migrate without user decision.",
            )
        replacement = (
            f"tier: {new_tier}\n"
            f"# review_depth: {legacy_value}  "
            "# [migrated to tier: at v0.5.5 — preserved as comment]"
        )
        if dry_run:
            return (
                EXIT_PASS,
                f"Dry-run: would migrate {target} "
                f"review_depth:{legacy_value} → tier:{new_tier} "
                f"(backup would land at {target}.bak).",
            )
        backup = _write_backup(target)
        new_fm = (
            frontmatter_body[: depth_match.start()]
            + replacement
            + frontmatter_body[depth_match.end() :]
        )
        new_text = text[:fm_start] + new_fm + text[fm_end:]
        target.write_text(new_text, encoding="utf-8")
        return (
            EXIT_PASS,
            f"Migrated {target}: review_depth:{legacy_value} → tier:{new_tier}. "
            f"Backup at {backup}.",
        )

    # Neither frontmatter field present: try the table-cell fallback before
    # declaring the record incomplete. This covers records whose frontmatter
    # holds other metadata (title, date, authors) but whose classification
    # inputs live in a narrative table.
    fallback = _table_cell_fallback(target, text, dry_run=dry_run)
    if fallback is not None:
        return fallback

    # Still nothing. WARN rather than BLOCK — the Marshal will pick this up
    # at P-2 if it matters for the next round.
    return (
        EXIT_WARN,
        f"{target} carries neither tier: nor review_depth: in frontmatter, "
        "and no 'Review depth | <value>' markdown-table row was found. "
        "Nothing to migrate; the classification record may be incomplete.",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Migrate legacy review_depth: classification to v0.5.x tier: "
            "field. Stdlib-only, idempotent, backup-emitting."
        )
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        required=True,
        help="Project root (contains reviews/classification.md).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the intended edit without writing anything.",
    )
    args = parser.parse_args(argv)

    project_root = args.project_root.expanduser().resolve()
    if not project_root.is_dir():
        print(
            f"[migrate_classification_to_tier] BLOCK: project root "
            f"{project_root} is not a directory.",
            file=sys.stderr,
        )
        return EXIT_BLOCK

    exit_code, message = migrate(project_root, dry_run=args.dry_run)
    stream = sys.stdout if exit_code == EXIT_PASS else sys.stderr
    label = {EXIT_PASS: "PASS", EXIT_WARN: "WARN", EXIT_BLOCK: "BLOCK"}[exit_code]
    print(f"[migrate_classification_to_tier] {label}: {message}", file=stream)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
