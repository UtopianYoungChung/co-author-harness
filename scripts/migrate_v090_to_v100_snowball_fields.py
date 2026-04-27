#!/usr/bin/env python3
# migrate_v090_to_v100_snowball_fields.py
#
# v0.10.0 SectionStateObject migration: extend the 16-field schema (v0.8.0
# β-P-9a) to 18 fields with the snowball-driven reference-scaffolding
# additions specified in `docs/superpowers/plans/2026-04-26-snowball-
# reference-architecture.md §5.4` and the implementation strategy
# `docs/superpowers/plans/2026-04-26-snowball-implementation-strategy.md §3.3`.
#
# **Status: S2 implementation** — the four S2-scoped functions are now
# implemented; the S4 deliverable (`add_last_coverage_score_field`) is held
# as a stage-gated no-op so the field count remains at {16, 17} until S4
# lands the default-null value. The invariant check tolerates {16, 17, 18}.
#
# Scope (filled at S2)
# --------------------
#   * reviews/phase_state.json
#       - field additions to every SectionStateObject:
#           references_initialized: bool           (default False)  [S2]
#           last_coverage_score: float | null      (default null)   [S4]
#       - SectionStateObject field count: 16 -> 17 (S2) -> 18 (S4)
#       - 30-trigger enum extended to 31 (adds seed_snowball_signed = 31)
#       - schema_version: "0.7.4"  ->  "0.10.0"  (per phase_state_schema.md
#         §1.1 "remains 0.7.4 at the ledger surface until the v0.8.0 RC
#         vocabulary roll" — v0.10.0 is the natural roll point)
#
#   * reviews/classification.md
#       - frontmatter additions:
#           claim_coverage_threshold: 0.8           (S1, deferred — see note)
#           auto_redlink_snowball: false            (S4.5)
#           red_link_cap_per_round: 5               (S4.5)
#           inherit_snowball: <true|false>           (S6, default true if
#                                                    wiki_linked: true)
#           pre_seed_cap: 10                        (S6)
#       - **S2 deviation note:** strategy §3.4 assigned `claim_coverage_threshold`
#         to S1, but S1 closed without the addition. SK-NEW-B (which consumes
#         the threshold) ships at S3, so the threshold is added by this
#         migration at S2 to keep the consumer/producer ordering correct.
#         The four S4.5/S6 fields are left untouched at S2.
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
# Usage
# -----
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
import re
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

# S2 implements the `claim_coverage_threshold` addition to classification.md
# (per the strategy §3.4 deviation note above). The four S4.5/S6 fields are
# left for their own stages.
S2_CLASSIFICATION_FIELDS = ("claim_coverage_threshold",)

# Legal SectionStateObject field counts during the v0.9.0 -> v0.10.0 migration
# rollout. 16 = pre-migration (v0.9.0); 17 = post-S2 (this migration);
# 18 = post-S4 (when last_coverage_score lands).
LEGAL_SECTION_FIELD_COUNTS = (16, 17, 18)

# Heuristic for the references_initialized default-set: REFERENCES.md exists
# and has at least one row in either the core corpus table or the snowball
# table. A row is detected as a markdown-table row whose first cell is
# non-empty and is not the header separator (---). The headers themselves
# are recognised as `## Core corpus` / `## Snowball` (plus a few synonyms
# to tolerate the existing INF3006Y_AgencyDelegation format).
CORE_TABLE_HEADERS = (
    re.compile(r"^##+\s+core\s+corpus\b", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^##+\s+core\s+pool\b", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^##+\s+read\s+directly\b", re.IGNORECASE | re.MULTILINE),
)
SNOWBALL_TABLE_HEADERS = (
    re.compile(r"^##+\s+snowball\b", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^##+\s+snowball\s+admissions\b", re.IGNORECASE | re.MULTILINE),
)
# A markdown table row that carries content (not the header separator).
# Matches lines that start with `|`, contain at least one further `|`, and
# whose first cell is not pure dashes/colons (which is the table separator).
TABLE_ROW = re.compile(r"^\|\s*([^|\s][^|]*?)\s*\|", re.MULTILINE)
TABLE_SEPARATOR = re.compile(r"^\|[\s:\-|]+\|\s*$", re.MULTILINE)


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------


def _iso_now() -> str:
    """Return UTC now in ISO 8601 with second precision."""
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def _iter_sections(state: dict) -> dict:
    """Return the sections dict from a phase_state document.

    The v0.7.4+ shape always carries a top-level `sections` key; if absent,
    return an empty dict so the caller can no-op cleanly.
    """
    sections = state.get("sections")
    if not isinstance(sections, dict):
        return {}
    return sections


def _table_has_row(text: str, header_patterns: tuple[re.Pattern[str], ...]) -> bool:
    """Return True if `text` contains a section under any header pattern with
    at least one *data* (non-header, non-separator) markdown-table row.

    The scan reads from each header match to the next `## ` heading (or EOF),
    isolates that segment, finds the table-separator line (the `|---|---|`
    row), and checks for at least one TABLE_ROW *after* that separator.
    The column-header row sits before the separator, so anything after the
    separator is by definition a data row.
    """
    for pat in header_patterns:
        for m in pat.finditer(text):
            start = m.end()
            next_heading = re.search(r"^##+\s+\S", text[start:], re.MULTILINE)
            end = start + next_heading.start() if next_heading else len(text)
            segment = text[start:end]
            sep_match = TABLE_SEPARATOR.search(segment)
            if not sep_match:
                # No separator means no well-formed table; skip.
                continue
            after_sep = segment[sep_match.end():]
            if TABLE_ROW.search(after_sep):
                return True
    return False


def _references_md_has_content(references_md: Path) -> bool:
    """Heuristic: REFERENCES.md exists AND has at least one row in either the
    core corpus table or the snowball table.

    Returns True / False; raises ValueError if the file exists but is not in a
    recognised format (no recognised section headers at all). The caller maps
    the ValueError to exit code 8.
    """
    if not references_md.is_file():
        return False
    try:
        text = references_md.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"failed to read {references_md}: {exc}") from exc

    has_core_header = any(p.search(text) for p in CORE_TABLE_HEADERS)
    has_snowball_header = any(p.search(text) for p in SNOWBALL_TABLE_HEADERS)
    if not (has_core_header or has_snowball_header):
        raise ValueError(
            f"REFERENCES.md format unrecognised at {references_md}: "
            f"no '## Core corpus' / '## Snowball' headers found "
            f"(heuristic for references_initialized cannot decide)"
        )

    return _table_has_row(text, CORE_TABLE_HEADERS) or _table_has_row(
        text, SNOWBALL_TABLE_HEADERS
    )


# ----------------------------------------------------------------------------
# Migration steps
# ----------------------------------------------------------------------------


def add_references_initialized_field(sections: dict, project_root: Path) -> dict:
    """Add `references_initialized: bool` to every SectionStateObject.

    Heuristic for the default value:
        - True if `<project_root>/references/REFERENCES.md` exists AND has
          at least one row in the core corpus table or the snowball table.
        - False otherwise.

    Idempotent: sections that already carry the field are skipped.
    Raises ValueError if REFERENCES.md exists but is not in a recognised
    format (caller maps to exit 8).
    """
    references_md = project_root / "references" / "REFERENCES.md"
    # Compute the heuristic value once for the whole document. The field is
    # per-section but the source of truth is project-level, so every section
    # gets the same value on first migration.
    default_value = _references_md_has_content(references_md)

    out: dict = {}
    for path, section in sections.items():
        if not isinstance(section, dict):
            out[path] = section
            continue
        if "references_initialized" in section:
            # Idempotent skip.
            out[path] = section
            continue
        new_section = dict(section)
        new_section["references_initialized"] = default_value
        out[path] = new_section
    return out


def add_last_coverage_score_field(sections: dict) -> dict:
    """S4 deliverable — at S2 this is a no-op pass-through.

    The field is not added at S2; the field count therefore stays at 17 after
    S2 migration (16 + references_initialized). At S4 this function will be
    rewritten to add `last_coverage_score: None` to every SectionStateObject
    that does not already carry the field, raising the count to 18.

    Returning sections unchanged is the contract that lets `main()` call this
    unconditionally without scope-gating logic in the caller.
    """
    # S4 will replace this with the actual default-null implementation.
    return sections


def update_schema_version(state: dict) -> dict:
    """Bump top-level `schema_version` from 0.7.4 to 0.10.0.

    Per phase_state_schema.md §1.1: the schema_version surface "remains
    `0.7.4` at the ledger surface until the v0.8.0 RC vocabulary roll".
    v0.10.0 is the named roll point.

    Idempotent: if already at 0.10.0, return state unchanged.
    """
    current = state.get("schema_version")
    if current == SCHEMA_TO:
        return state
    out = dict(state)
    out["schema_version"] = SCHEMA_TO
    return out


# ----------------------------------------------------------------------------
# classification.md migration (S2 portion only — see header note)
# ----------------------------------------------------------------------------


FRONTMATTER_DELIM = re.compile(r"^---\s*$", re.MULTILINE)


def _split_frontmatter(text: str) -> tuple[str, str, str] | None:
    """Return (head, frontmatter_body, rest) tuple or None if no frontmatter.

    `head` is the opening `---\\n`; `frontmatter_body` is the YAML between
    the two `---` markers (excluding them); `rest` is everything from the
    second `---` onward (including it).
    """
    matches = list(FRONTMATTER_DELIM.finditer(text))
    if len(matches) < 2:
        return None
    head_end = matches[0].end()
    fm_end = matches[1].start()
    return text[:head_end], text[head_end:fm_end], text[fm_end:]


def extend_classification_md(classification_path: Path, wiki_linked: bool) -> str:
    """Add the S2-scoped fields to `reviews/classification.md` frontmatter.

    At S2 this only adds `claim_coverage_threshold: 0.8` (per the header
    deviation note: the strategy assigned this field to S1, but S1 closed
    without it; SK-NEW-B consumes the threshold at S3, so it lands at S2).

    The `wiki_linked` parameter is reserved for the S6 `inherit_snowball`
    addition, which is gated to wiki-linked projects. At S2 the parameter is
    accepted but not consumed.

    Idempotent: existing values are preserved; missing S2 fields are appended.
    Returns the new file text. Raises ValueError if frontmatter is unparseable
    (caller maps to exit 7).
    """
    if not classification_path.is_file():
        # No classification.md to extend; treat as out-of-scope no-op (the
        # migration touches phase_state.json regardless of classification.md
        # presence).
        return ""

    try:
        text = classification_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"failed to read {classification_path}: {exc}") from exc

    parts = _split_frontmatter(text)
    if parts is None:
        raise ValueError(
            f"classification.md frontmatter not parseable at {classification_path}: "
            f"expected two `---` delimiters bracketing YAML frontmatter"
        )
    head, fm_body, rest = parts

    # Scan existing keys at top level (no nested-key support; the S2 fields
    # are flat scalars).
    new_lines = list(fm_body.splitlines())
    existing_keys = set()
    for line in new_lines:
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:", line)
        if m:
            existing_keys.add(m.group(1))

    # Append S2 fields if absent. Preserves trailing-blank-line discipline.
    appended: list[str] = []
    for key in S2_CLASSIFICATION_FIELDS:
        if key in existing_keys:
            continue
        default = CLASSIFICATION_DEFAULTS[key]
        appended.append(f"{key}: {_yaml_scalar(default)}")

    if not appended:
        return text

    # Strip trailing blank lines from fm_body, append new keys, then re-add a
    # trailing newline so the closing `---` is on its own line.
    while new_lines and new_lines[-1].strip() == "":
        new_lines.pop()
    new_lines.extend(appended)
    new_fm = "\n".join(new_lines) + "\n"

    return head + new_fm + rest


def _yaml_scalar(value: Any) -> str:
    """Render a Python scalar as a YAML scalar (no quoting unless necessary)."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    return str(value)


# ----------------------------------------------------------------------------
# Invariant check
# ----------------------------------------------------------------------------


def _check_section_field_counts(state: dict, where: str) -> None:
    """Raise ValueError if any section's field count is outside {16, 17, 18}.

    Mapped to exit code 6 by the caller.
    """
    for path, section in _iter_sections(state).items():
        if not isinstance(section, dict):
            continue
        n = len(section)
        if n not in LEGAL_SECTION_FIELD_COUNTS:
            raise ValueError(
                f"section '{path}' at {where} has {n} fields; "
                f"expected one of {LEGAL_SECTION_FIELD_COUNTS}"
            )


# ----------------------------------------------------------------------------
# Migration report
# ----------------------------------------------------------------------------


REPORT_TEMPLATE = """---
document_type: migration_report
schema_version: "1.0"
produced_at: {ts}
produced_by: migrate_v090_to_v100_snowball_fields.py
schema_from: "{schema_from}"
schema_to: "{schema_to}"
sections_migrated_count: {sections_migrated_count}
fields_added: {fields_added_yaml}
triggers_added: {triggers_added_yaml}
user_confirmed_migration_report_at: null
---

# v0.9.0 -> v0.10.0 migration report

## 1. Summary

This migration extended the SectionStateObject schema from {schema_from}
({fields_before} fields) to {schema_to} ({fields_after} fields per section)
and added trigger {trigger_id} (`{trigger_name}`) to the trigger enum. The
top-level `schema_version` was bumped from `{schema_from}` to `{schema_to}`.
{sections_migrated_count} section(s) were migrated; {idempotent_count}
section(s) were already at the v0.10.0 shape and were skipped.

The migration is the user-blocking gate for any subsequent SK-NEW-A /
SK-NEW-B / SK-NEW-C / SK-NEW-D dispatch: the Planner refuses to dispatch a
new round until the user signs this report by replacing
`user_confirmed_migration_report_at: null` with an ISO-8601 UTC timestamp
in the frontmatter above.

## 2. Per-section detail

{per_section_table}

## 3. User confirmation gate

Append the current UTC timestamp to the `user_confirmed_migration_report_at`
field in the frontmatter of this file to release the Planner's hold:

```yaml
user_confirmed_migration_report_at: {ts}
```

Until that line is set to a non-null value, the Planner refuses every
SK-NEW-* dispatch with `[BLOCKER] migration report unsigned`.
"""


def write_migration_report(project_root: Path, summary: dict) -> Path:
    """Author `reviews/migration_report_v090_to_v100.md` per the §7 convention.

    `summary` is a dict carrying:
        sections_migrated_count: int
        idempotent_count: int
        per_section: list[dict]   # each: {path, fields_touched, default_set}
        fields_added: list[str]
        triggers_added: list[str]
        fields_before: int
        fields_after: int
        already_complete: bool
    """
    report_path = project_root / "reviews" / "migration_report_v090_to_v100.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    per_section_lines = [
        "| Section | Fields touched | Default-set values |",
        "|---|---|---|",
    ]
    for row in summary.get("per_section", []):
        fields_touched = ", ".join(row.get("fields_touched", [])) or "(none)"
        default_set = ", ".join(
            f"{k}={_yaml_scalar(v)}" for k, v in row.get("default_set", {}).items()
        ) or "(none)"
        per_section_lines.append(
            f"| `{row['path']}` | {fields_touched} | {default_set} |"
        )
    if len(per_section_lines) == 2:
        per_section_lines.append("| _(no sections migrated)_ | | |")

    fields_added = summary.get("fields_added", [])
    triggers_added = summary.get("triggers_added", [])
    body = REPORT_TEMPLATE.format(
        ts=_iso_now(),
        schema_from=SCHEMA_FROM,
        schema_to=SCHEMA_TO,
        sections_migrated_count=summary.get("sections_migrated_count", 0),
        idempotent_count=summary.get("idempotent_count", 0),
        fields_before=summary.get("fields_before", 16),
        fields_after=summary.get("fields_after", 17),
        trigger_id=NEW_TRIGGER_ID,
        trigger_name=NEW_TRIGGER_NAME,
        fields_added_yaml=json.dumps(fields_added),
        triggers_added_yaml=json.dumps(triggers_added),
        per_section_table="\n".join(per_section_lines),
    )
    report_path.write_text(body, encoding="utf-8")
    return report_path


# ----------------------------------------------------------------------------
# Migration driver (single project)
# ----------------------------------------------------------------------------


def _read_classification_wiki_linked(classification_path: Path) -> bool:
    """Return the value of `wiki_linked:` from classification.md frontmatter.

    Defaults to False if absent. Returns False (rather than raising) on
    parse failures because the wiki_linked flag is only consumed by the S6
    inherit_snowball default; S2 does not need it.
    """
    if not classification_path.is_file():
        return False
    try:
        text = classification_path.read_text(encoding="utf-8")
    except OSError:
        return False
    parts = _split_frontmatter(text)
    if parts is None:
        return False
    _, fm_body, _ = parts
    m = re.search(r"^wiki_linked\s*:\s*(\S+)", fm_body, re.MULTILINE)
    if not m:
        return False
    return m.group(1).strip().lower() in ("true", "yes", "1")


def _run_migration(project_root: Path, dry_run: bool) -> int:
    """Run the migration on a single project root. Returns the exit code."""
    reviews = project_root / "reviews"
    if not reviews.is_dir():
        print(
            f"[ENV ERROR] reviews/ subdir not found under {project_root}",
            file=sys.stderr,
        )
        return 3

    state_path = reviews / "phase_state.json"
    if not state_path.is_file():
        print(
            f"[ENV ERROR] reviews/phase_state.json not found under {project_root}",
            file=sys.stderr,
        )
        return 3

    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(
            f"[ENV ERROR] JSON parse failed on {state_path}: {exc}",
            file=sys.stderr,
        )
        return 4
    except OSError as exc:
        print(f"[ENV ERROR] failed to read {state_path}: {exc}", file=sys.stderr)
        return 5

    # Pre-migration invariant: every section must have one of {16, 17, 18}
    # fields.
    try:
        _check_section_field_counts(state, where="pre-migration")
    except ValueError as exc:
        print(f"[INVARIANT VIOLATION] {exc}", file=sys.stderr)
        return 6

    pre_schema = state.get("schema_version")
    pre_sections = _iter_sections(state)

    # Ledger-inconsistency BLOCKER: schema_version is already at the v0.10.0
    # roll point, but at least one section is still at the 16-field shape
    # (i.e., missing `references_initialized`). The schema bump is supposed
    # to be atomic with the field addition; partial state means a prior
    # migration was interrupted between the schema bump and the field
    # backfill. Refuse rather than guess.
    if pre_schema == SCHEMA_TO:
        for path, section in pre_sections.items():
            if isinstance(section, dict) and "references_initialized" not in section:
                print(
                    f"[INVARIANT VIOLATION] schema_version is '{SCHEMA_TO}' but "
                    f"section '{path}' is missing 'references_initialized' "
                    f"(field count {len(section)}); ledger inconsistency — refuse to migrate.",
                    file=sys.stderr,
                )
                return 6

    # Idempotent already-complete short-circuit.
    if pre_schema == SCHEMA_TO and all(
        isinstance(s, dict) and "references_initialized" in s
        for s in pre_sections.values()
    ):
        summary = {
            "sections_migrated_count": 0,
            "idempotent_count": len(pre_sections),
            "per_section": [
                {"path": p, "fields_touched": [], "default_set": {}}
                for p in pre_sections
            ],
            "fields_added": [],
            "triggers_added": [],
            "fields_before": 17,
            "fields_after": 17,
            "already_complete": True,
        }
        if dry_run:
            print("[OK] migration already complete; no changes (dry-run)")
            print(json.dumps(summary, indent=2))
            return 0
        write_migration_report(project_root, summary)
        print("[OK] migration already complete; report re-emitted")
        return 0

    # Apply field additions. Wrap the heuristic call so REFERENCES.md format
    # errors map to exit 8.
    try:
        new_sections = add_references_initialized_field(pre_sections, project_root)
    except ValueError as exc:
        print(f"[ENV ERROR] {exc}", file=sys.stderr)
        return 8
    new_sections = add_last_coverage_score_field(new_sections)  # S4 no-op
    new_state = dict(state)
    new_state["sections"] = new_sections
    new_state = update_schema_version(new_state)

    # classification.md extension (S2 fields only).
    classification_path = reviews / "classification.md"
    wiki_linked = _read_classification_wiki_linked(classification_path)
    classification_after: str | None = None
    classification_changed = False
    if classification_path.is_file():
        try:
            classification_after = extend_classification_md(
                classification_path, wiki_linked
            )
        except ValueError as exc:
            print(f"[ENV ERROR] {exc}", file=sys.stderr)
            return 7
        classification_before = classification_path.read_text(encoding="utf-8")
        classification_changed = classification_after != classification_before

    # Build per-section summary for the report.
    per_section_rows: list[dict] = []
    fields_touched_global: set[str] = set()
    sections_migrated = 0
    idempotent_count = 0
    for path, before in pre_sections.items():
        if not isinstance(before, dict):
            continue
        after = new_sections.get(path, before)
        touched: list[str] = []
        defaults: dict = {}
        for key in ("references_initialized",):
            if key not in before and key in after:
                touched.append(key)
                defaults[key] = after[key]
        if touched:
            sections_migrated += 1
            fields_touched_global.update(touched)
        else:
            idempotent_count += 1
        per_section_rows.append(
            {"path": path, "fields_touched": touched, "default_set": defaults}
        )

    # Post-migration invariant.
    try:
        _check_section_field_counts(new_state, where="post-migration")
    except ValueError as exc:
        print(f"[INVARIANT VIOLATION] {exc}", file=sys.stderr)
        return 6

    summary = {
        "sections_migrated_count": sections_migrated,
        "idempotent_count": idempotent_count,
        "per_section": per_section_rows,
        "fields_added": sorted(fields_touched_global),
        "triggers_added": [NEW_TRIGGER_NAME] if sections_migrated else [],
        "fields_before": 16,
        "fields_after": 17,
        "already_complete": False,
        "classification_changed": classification_changed,
    }

    if dry_run:
        print("[OK] dry-run; no files written. Migration delta:")
        print(json.dumps(summary, indent=2))
        return 0

    # Write order: phase_state.json -> classification.md (if changed) -> report.
    try:
        state_path.write_text(
            json.dumps(new_state, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"[ENV ERROR] failed to write {state_path}: {exc}", file=sys.stderr)
        return 5

    if classification_changed and classification_after is not None:
        try:
            classification_path.write_text(classification_after, encoding="utf-8")
        except OSError as exc:
            print(
                f"[ENV ERROR] failed to write {classification_path}: {exc}",
                file=sys.stderr,
            )
            return 5

    report_path = write_migration_report(project_root, summary)
    print(f"[OK] migration complete. Report: {report_path}")
    return 0


# ----------------------------------------------------------------------------
# --validate harness
# ----------------------------------------------------------------------------


# Documented exit-code expectations for each block-case fixture, by slug.
BLOCK_EXPECTED_EXIT = {
    "invalid-json-state": 4,
    "unparseable-classification-frontmatter": 7,
    "unrecognised-references-format": 8,
    "schema-already-100-but-16-fields": 6,
}


def _diff_dirs(expected_dir: Path, actual_dir: Path) -> list[str]:
    """Return a list of relative-path strings that differ between the two
    directories. Used by --validate to compare a dry-run delta against the
    expected post-migration tree.

    The dry-run path doesn't actually write files, so we instead re-run the
    migration into a tempdir copy and diff against expected/. Returns an
    empty list if the trees match.
    """
    diffs: list[str] = []
    for expected_file in expected_dir.rglob("*"):
        if not expected_file.is_file():
            continue
        rel = expected_file.relative_to(expected_dir)
        actual_file = actual_dir / rel
        if not actual_file.is_file():
            diffs.append(f"missing: {rel}")
            continue
        # For the migration_report file, do a relaxed match: just check the
        # frontmatter has the right schema_from/schema_to. Timestamps differ
        # per run.
        if rel.name == "migration_report_v090_to_v100.md":
            txt = actual_file.read_text(encoding="utf-8")
            if f'schema_from: "{SCHEMA_FROM}"' not in txt:
                diffs.append(f"report missing schema_from: {rel}")
            if f'schema_to: "{SCHEMA_TO}"' not in txt:
                diffs.append(f"report missing schema_to: {rel}")
            continue
        # JSON: deep-equal compare.
        if rel.suffix == ".json":
            try:
                exp = json.loads(expected_file.read_text(encoding="utf-8"))
                act = json.loads(actual_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                diffs.append(f"parse failed on {rel}: {exc}")
                continue
            if exp != act:
                diffs.append(f"json differs: {rel}")
            continue
        # Text: byte-equal compare with line-end normalisation.
        exp_text = expected_file.read_text(encoding="utf-8").replace("\r\n", "\n")
        act_text = actual_file.read_text(encoding="utf-8").replace("\r\n", "\n")
        if exp_text != act_text:
            diffs.append(f"text differs: {rel}")
    return diffs


def _copy_fixture(src: Path, dst: Path) -> None:
    """Recursively copy fixture inputs (excluding `expected/`) into a tempdir."""
    import shutil

    for item in src.iterdir():
        if item.name == "expected":
            continue
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)


def _run_validate(fixture_root: Path) -> int:
    """Run the validation harness. Exits 0 if all pass-fixture migrations
    match `expected/` and all block-fixture migrations exit with the
    documented code; non-zero with a summary otherwise.
    """
    import shutil
    import tempfile

    if not fixture_root.is_dir():
        print(
            f"[ENV ERROR] --validate path is not a directory: {fixture_root}",
            file=sys.stderr,
        )
        return 2

    pass_root = fixture_root / "pass"
    block_root = fixture_root / "block"

    pass_results: list[tuple[str, str, list[str]]] = []  # (slug, status, diffs)
    block_results: list[tuple[str, str]] = []  # (slug, status)

    if pass_root.is_dir():
        for case_dir in sorted(pass_root.iterdir()):
            if not case_dir.is_dir():
                continue
            slug = case_dir.name
            with tempfile.TemporaryDirectory() as td:
                workdir = Path(td) / slug
                workdir.mkdir()
                _copy_fixture(case_dir, workdir)
                rc = _run_migration(workdir, dry_run=False)
                if rc != 0:
                    pass_results.append((slug, "ERROR", [f"exit code {rc}"]))
                    continue
                expected = case_dir / "expected"
                if not expected.is_dir():
                    pass_results.append(
                        (slug, "ERROR", ["expected/ subdir missing in fixture"])
                    )
                    continue
                diffs = _diff_dirs(expected, workdir)
                pass_results.append(
                    (slug, "PASS" if not diffs else "FAIL", diffs)
                )

    if block_root.is_dir():
        for case_dir in sorted(block_root.iterdir()):
            if not case_dir.is_dir():
                continue
            slug = case_dir.name
            expected_exit = BLOCK_EXPECTED_EXIT.get(slug)
            if expected_exit is None:
                block_results.append(
                    (slug, f"UNKNOWN (no expected exit code mapped for slug)")
                )
                continue
            with tempfile.TemporaryDirectory() as td:
                workdir = Path(td) / slug
                workdir.mkdir()
                _copy_fixture(case_dir, workdir)
                rc = _run_migration(workdir, dry_run=False)
                if rc == expected_exit:
                    block_results.append((slug, "PASS"))
                else:
                    block_results.append(
                        (
                            slug,
                            f"FAIL (exit {rc}, expected {expected_exit})",
                        )
                    )

    # Aggregate and print.
    failures = 0
    print("=== pass/ fixtures ===")
    for slug, status, diffs in pass_results:
        print(f"  [{status}] {slug}")
        for d in diffs:
            print(f"      - {d}")
        if status != "PASS":
            failures += 1
    print("=== block/ fixtures ===")
    for slug, status in block_results:
        print(f"  [{status}] {slug}")
        if not status.startswith("PASS"):
            failures += 1

    total = len(pass_results) + len(block_results)
    if failures:
        print(f"\n[FAIL] {failures}/{total} fixture(s) failed.")
        return 1
    print(f"\n[OK] all {total} fixture(s) passed.")
    return 0


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="v0.9.0 -> v0.10.0 SectionStateObject migration: extend "
                    "the 16-field schema to 17 fields (S2; 18 at S4) with the "
                    "snowball-driven reference-scaffolding additions.",
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
        return _run_validate(args.validate.resolve())

    if args.project_root is None:
        parser.error("--project-root is required (unless --validate is given)")

    project_root = args.project_root.resolve()
    if not project_root.is_dir():
        print(f"[ENV ERROR] project root not a directory: {project_root}", file=sys.stderr)
        return 2

    return _run_migration(project_root, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
