#!/usr/bin/env python3
"""migrate_v0100_to_v0110_drop_sd_sr.py — v0.10.x -> v0.11.0 migration helper.

Removes the retired ``sd_sr_required`` field from ``reviews/classification.md``
of a consuming project. v0.11.0 retired the entire i* SD/SR opt-in machinery
(see ``docs/release-notes/RELEASE_NOTES_v0.11.0.md``); fresh ledgers should not
declare or assert the field. Migrated v0.10.x rows carrying
``imodel_structural_validation_signed`` triggers remain readable but are no
longer emitted by v0.11.0 write paths.

Posture (plan §2.1 explicit):
    - No BLOCKER, no rollback, no ledger writes.
    - Idempotent: a second run is a no-op.
    - Advisory output only: emits an INFO line on stdout naming the path
      and whether a field was removed.

Usage
    migrate_v0100_to_v0110_drop_sd_sr.py --classification <path>

Exit codes
    0  Migration completed cleanly (field removed OR already absent).
    1  Bad invocation (missing path, unreadable file).
    2  Migration encountered an unexpected I/O error during write-back.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List


# Recognise both YAML-frontmatter form and bulleted-Inputs form. The
# classify-manuscript v0.7.1+ template surfaces the field as a bullet
# under ``## Inputs``; PROJECT_BOOTSTRAP.md historically used a YAML
# frontmatter field on the same name.
_BULLET_PREFIXES = ("- ", "* ", "+ ")


def _is_bullet_sd_sr_line(line: str) -> bool:
    """True if the line is a bulleted SD/SR field declaration.

    Tolerant of:
      - ``- SD/SR required: true``
      - ``- **SD/SR required:** false``
      - ``* SD/SR required: false``
      - ``-   sd/sr required: true`` (extra whitespace)
    Rejects anything that does not lead with a bullet marker so that
    paragraph prose mentioning ``sd_sr_required`` (e.g., a CHANGELOG
    line copied into a notes section) is left untouched.
    """
    stripped = line.lstrip()
    if not any(stripped.startswith(p) for p in _BULLET_PREFIXES):
        return False
    payload = stripped[2:].lstrip()
    # Strip leading markdown emphasis markers (``**``, ``*``, ``__``)
    # before the field name.
    while payload.startswith(("**", "__", "*", "_")):
        for marker in ("**", "__", "*", "_"):
            if payload.startswith(marker):
                payload = payload[len(marker):]
                break
    payload_lower = payload.lower()
    return payload_lower.startswith("sd/sr required") or payload_lower.startswith(
        "sd_sr_required"
    )


def _is_yaml_sd_sr_line(line: str) -> bool:
    """True if the line is a YAML-frontmatter SD/SR field declaration.

    Matches ``sd_sr_required: true`` (any whitespace, any value) at the
    start of the line. Used to strip the field from frontmatter blocks
    in PROJECT_BOOTSTRAP-style classification.md files.
    """
    stripped = line.lstrip()
    return stripped.startswith("sd_sr_required:") or stripped.startswith(
        "sd_sr_required :"
    )


def remove_sd_sr_lines(text: str) -> tuple[str, int]:
    """Return (rewritten_text, removed_line_count).

    Splits on lines, drops any line that matches either the bulleted-Inputs
    form or the YAML-frontmatter form. Does not collapse adjacent blank
    lines created by the removal — readability post-migration is the
    operator's responsibility, not the migration's.
    """
    out: List[str] = []
    removed = 0
    for line in text.splitlines(keepends=True):
        if _is_bullet_sd_sr_line(line) or _is_yaml_sd_sr_line(line):
            removed += 1
            continue
        out.append(line)
    return "".join(out), removed


def migrate(classification_path: Path) -> int:
    """Apply the v0.10.0 -> v0.11.0 SD/SR-drop migration.

    Args:
        classification_path: Path to the project's
            ``reviews/classification.md``. Must exist and be readable.

    Returns:
        Exit code: 0 on success (any state); 1 on bad invocation;
        2 on unexpected I/O error during write-back.
    """
    if not classification_path.exists():
        print(
            f"ERROR: classification file not found: {classification_path}",
            file=sys.stderr,
        )
        return 1
    if not classification_path.is_file():
        print(
            f"ERROR: classification path is not a regular file: {classification_path}",
            file=sys.stderr,
        )
        return 1

    try:
        original = classification_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: unable to read {classification_path}: {exc}", file=sys.stderr)
        return 1

    rewritten, removed = remove_sd_sr_lines(original)

    if removed == 0:
        # Idempotent path: already migrated (or never had the field).
        # No write-back; advisory line only.
        print(
            f"INFO: no sd_sr_required field present in {classification_path} "
            f"(v0.10.0 -> v0.11.0 migration: no-op)"
        )
        return 0

    try:
        classification_path.write_text(rewritten, encoding="utf-8")
    except OSError as exc:
        print(
            f"ERROR: unable to write {classification_path}: {exc}", file=sys.stderr
        )
        return 2

    print(
        f"INFO: dropped sd_sr_required field from {classification_path} "
        f"(v0.10.0 -> v0.11.0 migration; {removed} line"
        f"{'s' if removed != 1 else ''} removed)"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Drop the retired sd_sr_required field from a project's "
            "reviews/classification.md as part of the v0.10.0 -> v0.11.0 "
            "migration. Idempotent; advisory output only; no rollback path."
        )
    )
    parser.add_argument(
        "--classification",
        type=Path,
        required=True,
        help="Path to reviews/classification.md of the consuming project.",
    )
    args = parser.parse_args()
    from destination_capability import DestinationRefused, guard_project_root
    try:
        guard_project_root(args.classification)
    except DestinationRefused as exc:
        print(f"[BLOCKER] {exc}", file=sys.stderr)
        return 4
    return migrate(args.classification)


if __name__ == "__main__":
    sys.exit(main())
