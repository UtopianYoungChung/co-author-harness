#!/usr/bin/env python3
# migrate_convergence_journal_v075.py — v0.8.0 P2.1d
#
# Backfills legacy scalar `convergence_metric` rows in
# `reviews/convergence_journal.jsonl` (P-4 nine-field core plus optional
# v0.8.0 keys per PHASE_PROTOCOL.md §3.3.4) to the β P-12 four-component stability shape
# described in proposals/v0.7.5_phase3_refinement_loop_proposal.md §P-12 and
# proposals/v0.8.0_upgrade_architecture.md §3.2 Phase 2.1.
#
# Reconstruction policy (journal-only pass — no F1/F2 artefact crawl at P2.1d):
#
#   * `legacy_scalar` — preserved float or null from the pre-migration field.
#   * `grounding_clean` — not recoverable from the journal row alone; set to
#     the sentinel string "[v0.8.0-BACKFILL-N/A]" (same token as §3.2).
#   * `check8_aggregate_ok` — bool: True when `check8_aggregate` is PASS or
#     BORDERLINE; False when MAJOR or BLOCKER; sentinel when aggregate is null.
#   * `findings_count_delta` — int (current `new_findings_count` minus prior
#     row's) when both are int; else sentinel on the first row or when either
#     side is non-int.
#   * `line_delta` — int from `delta_lines` when int; else sentinel when null.
#
# Idempotency: rows whose `convergence_metric` is already an object carrying
# `_v080_p12 == "journal-scalar-backfill-1"` are left unchanged. Re-running the
# migration on an already-migrated file is a no-op (byte-stable if each line is
# emitted with sort_keys + compact separators).
#
# Usage:
#   python3 migrate_convergence_journal_v075.py --project-root /path/to/project
#   python3 migrate_convergence_journal_v075.py --project-root /path --dry-run
#
# Exit: 0 success, 1 usage, 2 bad project-root, 3 journal missing, 4 JSON parse error

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

MIGRATION_TAG = "journal-scalar-backfill-1"
BACKFILL = "[v0.8.0-BACKFILL-N/A]"
REPORT_NAME = "migration_report_convergence_journal_v075.md"


def _die(msg: str, code: int) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _already_migrated(cm: Any) -> bool:
    return isinstance(cm, dict) and cm.get("_v080_p12") == MIGRATION_TAG


def _check8_ok(aggregate: Any) -> Any:
    if aggregate is None:
        return BACKFILL
    v = str(aggregate).strip().upper()
    if v in ("PASS", "BORDERLINE"):
        return True
    if v in ("MAJOR", "BLOCKER"):
        return False
    return BACKFILL


def _findings_delta(cur: dict[str, Any], prev: dict[str, Any] | None) -> Any:
    if prev is None:
        return BACKFILL
    a = cur.get("new_findings_count")
    b = prev.get("new_findings_count")
    if isinstance(a, int) and isinstance(b, int):
        return a - b
    return BACKFILL


def _line_delta(row: dict[str, Any]) -> Any:
    dl = row.get("delta_lines")
    if isinstance(dl, int):
        return dl
    return BACKFILL


def _legacy_scalar(cm: Any) -> float | None:
    if cm is None:
        return None
    if _is_number(cm):
        return float(cm)
    return None


def migrate_row(row: dict[str, Any], prev: dict[str, Any] | None) -> tuple[dict[str, Any], str]:
    """Return (new_row, status) where status is skipped|migrated."""
    cm = row.get("convergence_metric")
    if _already_migrated(cm):
        return row, "skipped"
    if isinstance(cm, dict):
        # Forward-unknown dict shape — do not overwrite.
        return row, "skipped"

    if cm is not None and not _is_number(cm):
        _die(
            f"ERROR: convergence_metric must be null, number, or migrated dict; got {type(cm).__name__}",
            4,
        )

    legacy = _legacy_scalar(cm)
    new_cm: dict[str, Any] = {
        "_v080_p12": MIGRATION_TAG,
        "check8_aggregate_ok": _check8_ok(row.get("check8_aggregate")),
        "findings_count_delta": _findings_delta(row, prev),
        "grounding_clean": BACKFILL,
        "legacy_scalar": legacy,
        "line_delta": _line_delta(row),
    }
    out = dict(row)
    out["convergence_metric"] = new_cm
    return out, "migrated"


def migrate_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    out: list[dict[str, Any]] = []
    counts = {"migrated": 0, "skipped": 0}
    prev: dict[str, Any] | None = None
    for row in rows:
        new_row, st = migrate_row(row, prev)
        counts[st] += 1
        out.append(new_row)
        prev = row
    return out, counts


def rows_to_digest(rows: list[dict[str, Any]]) -> str:
    lines = [
        json.dumps(r, sort_keys=True, separators=(",", ":")).encode("utf-8")
        for r in rows
    ]
    h = hashlib.sha256()
    for ln in lines:
        h.update(ln)
        h.update(b"\n")
    return h.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            _die(f"ERROR: JSON parse failure at {path}:{lineno}: {e}", 4)
        if not isinstance(obj, dict):
            _die(f"ERROR: line {lineno} is not a JSON object", 4)
        rows.append(obj)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    text = "\n".join(
        json.dumps(r, sort_keys=True, separators=(",", ":")) for r in rows
    )
    text += "\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    tmp.replace(path)


def build_report_md(
    project_root: Path,
    journal_rel: str,
    counts: dict[str, int],
    digest: str,
    dry_run: bool,
) -> str:
    lines = [
        "---",
        "artefact: migration_report_convergence_journal_v075",
        f"dry_run: {'true' if dry_run else 'false'}",
        f"digest_sha256: {digest}",
        f"rows_migrated: {counts.get('migrated', 0)}",
        f"rows_skipped: {counts.get('skipped', 0)}",
        "---",
        "",
        "# Migration report — `migrate_convergence_journal_v075.py` (P-12 backfill)",
        "",
        f"Project root: `{project_root}`.",
        f"Journal: `{journal_rel}`.",
        "",
        "Scalar `convergence_metric` values were replaced with a four-component "
        f"object tagged `_v080_p12: {MIGRATION_TAG!r}` per v0.8.0 P2.1d. "
        f"`grounding_clean` is always `{BACKFILL!r}` on this journal-only pass.",
        "",
        "## Counts",
        "",
        f"- Migrated rows: **{counts.get('migrated', 0)}**",
        f"- Skipped rows (already migrated or non-scalar dict): **{counts.get('skipped', 0)}**",
        "",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="P-12 backfill: scalar convergence_metric → four-component object in journal JSONL."
    )
    ap.add_argument("--project-root", required=True, help="Project root (contains reviews/).")
    ap.add_argument(
        "--journal",
        default="reviews/convergence_journal.jsonl",
        help="Path relative to project root (default: reviews/convergence_journal.jsonl).",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse, migrate in memory, print summary JSON; write no files.",
    )
    args = ap.parse_args(argv)

    root = Path(args.project_root).resolve()
    if not root.is_dir():
        _die(f"ERROR: --project-root is not a directory: {root}", 2)

    journal_path = (root / args.journal).resolve()
    if not journal_path.is_file():
        _die(f"ERROR: journal not found: {journal_path}", 3)

    rows = load_jsonl(journal_path)
    new_rows, counts = migrate_rows(rows)
    digest = rows_to_digest(new_rows)

    summary = {
        "digest_sha256": digest,
        "dry_run": bool(args.dry_run),
        "journal": args.journal.strip().replace("\\", "/"),
        "rows_migrated": counts.get("migrated", 0),
        "rows_skipped": counts.get("skipped", 0),
        "rows_total": len(rows),
    }
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))

    if args.dry_run:
        return 0

    write_jsonl(journal_path, new_rows)
    report_path = root / "reviews" / REPORT_NAME
    report_path.write_text(
        build_report_md(root, args.journal, counts, digest, dry_run=False),
        encoding="utf-8",
        newline="\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
