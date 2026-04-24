#!/usr/bin/env python3
"""migrate_v055_to_v060.py — synthesize reviews/tier_state.json from v0.5.5 residual state.

Grounding:
  - references/tier_state_schema.md §7 (per-field migration map, trigger mapping,
    report format).
  - references/TIER_PROTOCOL.md §10 (v0.5.5 → v0.6.0 migration map).
  - references/tier_state_schema.md §5 (atomic .tmp → rename writer discipline).
  - TIER_REDESIGN_v0.6-draft-3.md §§4.1, 10; TIER_REDESIGN_v0.6_phase_2_audit.md §4.3.

Inputs
    --project-root <path>         Project directory containing reviews/ and
                                  manuscript/.
    --manuscript <rel-path>       Manuscript file relative to --project-root.
                                  Default: manuscript/main.md.
    --default-final-tier <T1..T4> Override for default_final_tier. If omitted,
                                  inherit from classification.md `tier:` field
                                  (T0 → T3 with MIGRATION_WARN per §7.1).
    --fingerprint-mode            strict | tolerant | off. Default: tolerant.
    --opaque-env <name>           Extra opaque env for canonicalization
                                  (repeatable; passed to tier_state_canonicalize).
    --cycle-id <int>              Synthetic cycle_id for the initial dispatch
                                  row. Default: 1.
    --force                       Overwrite an existing reviews/tier_state.json
                                  without asking (default: refuse if present).

Reads
    reviews/classification.md     tier: → initial current_tier + default_final_tier
    reviews/escalation_log.md     initial-tier row → first tier_entry_log row
    reviews/tier_decisions_log.md choice column → synthesized user_approval /
                                  user_rejection / retraction rows
    manuscript/main.md            section AST → heading_path list + fingerprint
                                  body-per-section

Writes
    reviews/tier_state.json                 per §5 atomic writer discipline.
    reviews/tier_state.json.bak.<timestamp> backup copy if an existing file was
                                            overwritten under --force.
    reviews/migration_report_v055_to_v060.md  Mapped rows · Warnings · User
                                              hold-point (§7.3).

Validation
    On successful write, invoke scripts/tier_state_validate.py against the new
    file; propagate its exit code.

Exit codes
    0  success (fresh ledger + report written, validator clean)
    1  missing inputs (no classification.md, no manuscript, etc.)
    2  schema-validation failure after write (unexpected; see validator output)
    3  output collision (--force not supplied and reviews/tier_state.json exists)
    4  bad invocation (unknown tier, unreadable file, etc.)

Rollback: migration is one-way. The v0.5.4 tree is the fallback; re-init a
v0.5.5 project against that tree and re-run migration once the source is fixed.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Co-located canonicalizer. Migration must compute fingerprints the same way as
# Phase 3.5 drift reporting and Confirmation Mode so that the first Planner
# Phase 0 read of a freshly-migrated ledger sees fingerprint_staleness = 0.
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import tier_state_canonicalize as tsc  # noqa: E402 — path adjustment above.


# ----------------------------------------------------------------- constants

SCHEMA_VERSION = "0.6.0"
TIER_ENUM = ("T1", "T2", "T3", "T4_ready", "T4")
# default_final_tier may only be a target rung, not the T4_ready sentinel.
DEFAULT_FINAL_TIER_ENUM = ("T1", "T2", "T3", "T4")
FINGERPRINT_MODE_ENUM = ("strict", "tolerant", "off")
BACKUP_RETENTION = 10


# ----------------------------------------------------------------- datatypes


@dataclass
class Warning_:
    """One warning row for the migration report."""

    category: str  # e.g., "T0_DEFAULT_COERCED", "STAY_TO_REJECTION", "MISSING_ARTEFACT"
    message: str


@dataclass
class MappedRow:
    """One row in the Mapped-rows table of the migration report."""

    source_artefact: str
    source_fragment: str
    v060_trigger: str | None  # None = dropped
    note: str = ""


@dataclass
class MigrationContext:
    project_root: Path
    manuscript_path: Path
    classification_path: Path
    escalation_log_path: Path
    tier_decisions_log_path: Path
    tier_state_path: Path
    backup_dir: Path
    report_path: Path
    default_final_tier: str
    fingerprint_mode: str
    opaque_envs: list[str]
    cycle_id: str
    warnings: list[Warning_] = field(default_factory=list)
    mapped_rows: list[MappedRow] = field(default_factory=list)
    utc_now: str = ""


# ----------------------------------------------------------------- utilities


def _iso_utc_now() -> str:
    # Second precision matches the seed template in §8. Sub-second precision is
    # not required by the schema and would make diffs noisier.
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _slugify(name: str) -> str:
    # lower-kebab-case per §7.1 for manuscript_id.
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-").lower()
    return slug or "manuscript"


# ----------------------------------------------------------------- parsers


_CLASSIFICATION_TIER_RE = re.compile(r"^tier:\s*(T[0-4])\s*$", re.MULTILINE)


def parse_classification(ctx: MigrationContext) -> str | None:
    """Return the `tier:` value from classification.md frontmatter.

    Returns None if the file exists but has no tier field. Raises FileNotFoundError
    if the file is missing."""
    text = ctx.classification_path.read_text(encoding="utf-8")
    m = _CLASSIFICATION_TIER_RE.search(text)
    if not m:
        ctx.warnings.append(
            Warning_(
                "MISSING_FIELD",
                "classification.md has no `tier:` frontmatter field; migration "
                "cannot infer default_final_tier. Pass --default-final-tier.",
            )
        )
        return None
    tier = m.group(1)
    ctx.mapped_rows.append(
        MappedRow(
            "classification.md",
            f"tier: {tier}",
            "initial_dispatch",
            f"Used as default_final_tier seed (may be coerced if T0).",
        )
    )
    return tier


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


def parse_manuscript_sections(ctx: MigrationContext) -> list[tuple[list[str], str]]:
    """Parse manuscript heading AST and return [(heading_path, body), ...].

    Heading strategy: choose the dominant section level by counting per-level
    hits. Sections are split at that level; their bodies are the content up to
    the next heading at the same or higher level. heading_path is single-element
    at the dominant level. If any sub-headings (level + 1) appear inside a
    section's body, the first heading is promoted to the heading_path root so
    nesting is preserved in a best-effort way.

    Returns an empty list if the manuscript has no headings at all (migration
    will emit one synthetic `body` section so the ledger is non-empty per §1).
    """
    text = ctx.manuscript_path.read_text(encoding="utf-8")
    headings: list[tuple[int, str, int]] = []  # (level, text, start_offset)
    for m in _HEADING_RE.finditer(text):
        level = len(m.group(1))
        headings.append((level, m.group(2).strip(), m.start()))

    if not headings:
        ctx.warnings.append(
            Warning_(
                "NO_HEADINGS",
                "Manuscript contains no markdown headings; a single synthetic "
                "'body' section was created.",
            )
        )
        return [(["body"], text)]

    # Dominant level = the level with the most headings, ties broken by shallowest.
    level_counts: dict[int, int] = {}
    for lvl, _, _ in headings:
        level_counts[lvl] = level_counts.get(lvl, 0) + 1
    max_count = max(level_counts.values())
    dominant = min(lvl for lvl, c in level_counts.items() if c == max_count)

    # Slice the text into sections at the dominant level.
    dominant_positions = [(lvl, t, off) for (lvl, t, off) in headings if lvl <= dominant]
    sections: list[tuple[list[str], str]] = []

    # Prepend a fake end-of-file sentinel so the last slice terminates.
    boundaries = [(lvl, t, off) for (lvl, t, off) in dominant_positions]
    boundaries.append((0, "", len(text)))

    for i, (lvl, title, off) in enumerate(boundaries[:-1]):
        if lvl != dominant:
            # A level above dominant (e.g. the manuscript title) — skip as the
            # heading_path root; its body is distributed to the next sections.
            continue
        _, _, next_off = boundaries[i + 1]
        body = text[off:next_off]
        sections.append(([title], body))

    # Heading-path uniqueness: §7.1 requires distinct heading_path lists. If the
    # manuscript has duplicate headings at the dominant level (e.g. two "Introduction"
    # sections), disambiguate with an ordinal suffix and record a warning.
    seen: dict[str, int] = {}
    dedup: list[tuple[list[str], str]] = []
    for path, body in sections:
        key = " > ".join(path)
        if key in seen:
            seen[key] += 1
            disambiguated = [f"{path[-1]} ({seen[key]})"]
            ctx.warnings.append(
                Warning_(
                    "HEADING_PATH_DUPLICATE",
                    f"Heading '{key}' appears multiple times; renamed to "
                    f"'{disambiguated[-1]}'. Review and rename in manuscript.",
                )
            )
            dedup.append((disambiguated, body))
        else:
            seen[key] = 1
            dedup.append((path, body))

    return dedup


_ESCALATION_ROW_RE = re.compile(
    r"^\|\s*(?P<ts>[^|]+?)\s*\|\s*(?P<from>T[0-4])\s*(?:->|→)\s*(?P<to>T[0-4])\s*"
    r"\|\s*(?P<gate>[^|]+?)\s*\|\s*(?P<reason>[^|]+?)\s*\|\s*(?P<round>\d+)\s*\|\s*$",
    re.MULTILINE,
)


def parse_escalation_log(ctx: MigrationContext) -> list[dict[str, str]]:
    """Return [{timestamp, from_tier, to_tier, gate, reason, round_id}, ...]."""
    if not ctx.escalation_log_path.exists():
        ctx.warnings.append(
            Warning_(
                "MISSING_ARTEFACT",
                "reviews/escalation_log.md not found; no initial_dispatch row "
                "will be synthesized from a log. A default initial_dispatch row "
                "is still written.",
            )
        )
        return []
    text = ctx.escalation_log_path.read_text(encoding="utf-8")
    rows: list[dict[str, str]] = []
    for m in _ESCALATION_ROW_RE.finditer(text):
        rows.append(
            {
                "timestamp": m.group("ts").strip(),
                "from_tier": m.group("from"),
                "to_tier": m.group("to"),
                "gate": m.group("gate").strip(),
                "reason": m.group("reason").strip(),
                "round_id": m.group("round"),
            }
        )
        ctx.mapped_rows.append(
            MappedRow(
                "escalation_log.md",
                f"{m.group('from')} -> {m.group('to')} / {m.group('gate').strip()}",
                "initial_dispatch" if "initial" in m.group("gate").lower() else None,
                "Dropped (non-initial gate; no v0.6.0 analog)."
                if "initial" not in m.group("gate").lower()
                else "",
            )
        )
    return rows


_DECISIONS_ROW_RE = re.compile(
    r"^\|\s*(?P<round>\d+)\s*\|\s*(?P<from>T[0-4])\s*\|\s*(?P<choice>Up|Down|Stay|Done)\s*"
    r"\|\s*(?P<to>T[0-4])\s*\|\s*(?P<ratchet>true|false)\s*\|\s*(?P<advisories>[^|]*?)\s*\|\s*$",
    re.MULTILINE,
)


def parse_tier_decisions_log(ctx: MigrationContext) -> list[dict[str, str]]:
    """Return [{round, from_tier, choice, to_tier, ...}, ...] in file order.

    Records a MappedRow per decisions-log row (once per migration, not once
    per section; the per-section synthesis later replays the same mapping)."""
    if not ctx.tier_decisions_log_path.exists():
        ctx.warnings.append(
            Warning_(
                "MISSING_ARTEFACT",
                "reviews/tier_decisions_log.md not found; no user_approval / "
                "user_rejection rows will be synthesized. Ledger starts at "
                "current_tier with no approval history.",
            )
        )
        return []
    text = ctx.tier_decisions_log_path.read_text(encoding="utf-8")
    rows: list[dict[str, str]] = []
    for m in _DECISIONS_ROW_RE.finditer(text):
        rows.append(
            {
                "round": m.group("round"),
                "from_tier": m.group("from"),
                "choice": m.group("choice"),
                "to_tier": m.group("to"),
                "ratchet_respected": m.group("ratchet"),
                "advisories": m.group("advisories").strip(),
            }
        )
        trigger, note = map_choice_to_trigger(m.group("choice"))
        ctx.mapped_rows.append(
            MappedRow(
                "tier_decisions_log.md",
                f"round {m.group('round')}: {m.group('from')} "
                f"{m.group('choice')} {m.group('to')}",
                trigger if trigger else None,
                note
                + (
                    " Replayed against each section."
                    if trigger and note == ""
                    else (" Replayed against each section." if trigger else "")
                ),
            )
        )
    return rows


# ----------------------------------------------------------------- migration


def coerce_default_final_tier(
    ctx: MigrationContext, classification_tier: str | None, cli_override: str | None
) -> str:
    """Choose default_final_tier per §7.1.

    CLI override wins. Otherwise take classification tier; T0 coerces to T3 with
    MIGRATION_WARN. A missing / unparseable tier defaults to T3 with a warning.
    """
    if cli_override is not None:
        if cli_override not in DEFAULT_FINAL_TIER_ENUM:
            raise SystemExit(
                f"[BAD-INVOCATION] --default-final-tier={cli_override!r} not in "
                f"{DEFAULT_FINAL_TIER_ENUM}"
            )
        return cli_override
    if classification_tier is None:
        ctx.warnings.append(
            Warning_(
                "T0_DEFAULT_COERCED",
                "classification.md had no tier: field; default_final_tier "
                "coerced to T3.",
            )
        )
        return "T3"
    if classification_tier == "T0":
        ctx.warnings.append(
            Warning_(
                "T0_DEFAULT_COERCED",
                "classification.md tier=T0 is retired at v0.6.0; "
                "default_final_tier coerced to T3.",
            )
        )
        return "T3"
    return classification_tier


def map_choice_to_trigger(choice: str) -> tuple[str, str]:
    """Return (trigger, note) per §7.2."""
    choice = choice.strip()
    if choice == "Up":
        return ("user_approval", "")
    if choice == "Done":
        return ("user_approval", "choice=Done mapped to user_approval")
    if choice == "Down":
        return ("retraction", "")
    if choice == "Stay":
        return (
            "user_rejection",
            "choice=Stay mapped to user_rejection (best-effort heuristic).",
        )
    # Unrecognized choices are dropped; the migration report records this.
    return ("", f"choice={choice!r} has no v0.6.0 analog; dropped")


def synthesize_tier_entry_log(
    ctx: MigrationContext,
    escalation_rows: list[dict[str, str]],
    decisions_rows: list[dict[str, str]],
    initial_tier: str,
) -> tuple[list[dict[str, Any]], str | None, int, str]:
    """Build the tier_entry_log for a section.

    Returns (rows, last_approved_tier, iteration_count_at_current_tier, final_tier).

    Invariants:
      - from_tier always equals the running state before the row fires, which
        is the to_tier of the prior row (or `initial_tier` if no prior row).
        This means we do NOT propagate `dr["from_tier"]` raw — v0.5.5 did not
        know about T4_ready, so we coerce consistently on replay.
      - `user_approval` to T4 is coerced to T4_ready (v0.5.5 had no LCR).
      - `retraction` coerces `last_approved_tier` down to the new running tier.
        §2.1 says "last_approved preserved" across retraction, but the validator
        rejects that state as LAST_APPROVED_TIER_ABOVE_CURRENT (§6). Migration
        resolves the conflict conservatively: retract also erases the approval
        record, and a warning records the lossy step.
      - `user_rejection` (Stay) leaves both from_tier and to_tier at the running
        tier and increments iteration_count.
    """
    rows: list[dict[str, Any]] = []
    cycle = ctx.cycle_id

    # Row 1: initial_dispatch. Derived from escalation_log first row if present;
    # otherwise synthesized from classification.
    if escalation_rows:
        first = escalation_rows[0]
        timestamp = _normalize_timestamp(first["timestamp"])
        detail = (
            f"Migrated from escalation_log row 1 ({first['gate']}: {first['reason']})."
        )
    else:
        timestamp = ctx.utc_now
        detail = (
            "Initial dispatch synthesized at migration time "
            "(no escalation_log.md row to derive from)."
        )
    rows.append(
        {
            "timestamp": timestamp,
            "trigger": "initial_dispatch",
            "from_tier": None,
            "to_tier": initial_tier,
            "scope": "section",
            "cycle_id": cycle,
            "detail": detail,
        }
    )

    # Synthesize approval / rejection / retraction rows from decisions log.
    last_approved: str | None = None
    running_tier = initial_tier
    iter_at_current = 0

    for dr in decisions_rows:
        trigger, note = map_choice_to_trigger(dr["choice"])
        if not trigger:
            # Mapped-row note already recorded at parse time.
            continue

        # from_tier is ALWAYS the running state; we never trust the v0.5.5 log
        # to be internally consistent across T4_ready coercion.
        from_tier_eff = running_tier

        # Compute to_tier_eff based on trigger semantics.
        raw_to = dr["to_tier"]
        if trigger == "user_approval":
            if raw_to == "T4":
                to_tier_eff = "T4_ready"
                ctx.warnings.append(
                    Warning_(
                        "T4_REQUIRES_LCR",
                        f"round {dr['round']} advanced to T4 under v0.5.5 (no "
                        "LCR); migrated as user_approval → T4_ready. The "
                        "Planner will gate final T4 admission via the Laggard "
                        "Clearance Report.",
                    )
                )
            else:
                to_tier_eff = raw_to
            # Guard against approvals that would decrement — v0.5.5 never did
            # this, but a malformed log could. Validator's MONOTONICITY_VIOLATION
            # would catch it anyway; we defend at migration time.
            if _tier_rank(to_tier_eff) < _tier_rank(from_tier_eff):
                ctx.warnings.append(
                    Warning_(
                        "APPROVAL_DOWNWARD",
                        f"round {dr['round']}: choice=Up/Done but to_tier "
                        f"{raw_to!r} ≤ running tier {from_tier_eff!r}. Row "
                        "dropped to avoid monotonicity violation.",
                    )
                )
                continue
        elif trigger == "user_rejection":
            # Stay: both sides pinned to running_tier.
            to_tier_eff = from_tier_eff
        elif trigger == "retraction":
            # Down: demote. We compute the new tier as the nearest legal rung
            # strictly below from_tier_eff; the raw `to_tier` in v0.5.5 is our
            # hint. If the raw value is >= running_tier, we step down by one.
            if _tier_rank(raw_to) < _tier_rank(from_tier_eff):
                to_tier_eff = raw_to
            else:
                # Step down one rung in the v0.6.0 staircase.
                order = ["T1", "T2", "T3", "T4_ready", "T4"]
                idx = order.index(from_tier_eff)
                to_tier_eff = order[max(idx - 1, 0)]
        else:
            to_tier_eff = from_tier_eff  # Defensive default.

        rows.append(
            {
                "timestamp": ctx.utc_now,
                "trigger": trigger,
                "from_tier": from_tier_eff,
                "to_tier": to_tier_eff,
                "scope": "section",
                "cycle_id": cycle,
                "detail": (
                    f"Migrated from tier_decisions_log round {dr['round']}: "
                    f"choice={dr['choice']}. {note}"
                ).strip(),
            }
        )

        # Update running state.
        if trigger == "user_approval":
            if last_approved is None or _tier_rank(to_tier_eff) > _tier_rank(last_approved):
                last_approved = to_tier_eff
            if _tier_rank(to_tier_eff) > _tier_rank(running_tier):
                running_tier = to_tier_eff
                iter_at_current = 0
        elif trigger == "user_rejection":
            iter_at_current += 1
        elif trigger == "retraction":
            # Conservative: erase the approval record down to the new running
            # tier. The validator rejects "last_approved > current", so we
            # cannot preserve the v0.5.5 semantic in full.
            if _tier_rank(to_tier_eff) < _tier_rank(running_tier):
                running_tier = to_tier_eff
                if last_approved is not None and _tier_rank(last_approved) > _tier_rank(
                    running_tier
                ):
                    ctx.warnings.append(
                        Warning_(
                            "RETRACTION_LOSSY",
                            f"round {dr['round']} was a Down/retraction; "
                            f"last_approved_tier reset from {last_approved} to "
                            f"{running_tier or 'null'}. v0.5.5 preserved approval "
                            "history across retraction; v0.6.0 validator "
                            "rejects that state.",
                        )
                    )
                    last_approved = running_tier if _tier_rank(running_tier) >= 1 else None
                iter_at_current = 0

    return rows, last_approved, iter_at_current, running_tier


def _tier_rank(t: str | None) -> int:
    if t is None:
        return 0
    return {"T1": 1, "T2": 2, "T3": 3, "T4_ready": 4, "T4": 5}.get(t, 0)


def _normalize_timestamp(raw: str) -> str:
    """Coerce a v0.5.5 timestamp (plain ISO, no Z) into the §1 format."""
    raw = raw.strip()
    # Accept 'YYYY-MM-DDTHH:MM:SS', optionally suffixed with Z or +00:00.
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", raw):
        return raw
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", raw):
        return raw + "Z"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00", raw):
        return raw[:-6] + "Z"
    # Unparseable: fall back to UTC-now; the caller already tags this with a
    # mapped-row note.
    return _iso_utc_now()


def build_section_state(
    ctx: MigrationContext,
    heading_path: list[str],
    body: str,
    escalation_rows: list[dict[str, str]],
    decisions_rows: list[dict[str, str]],
    classification_tier: str,
) -> dict[str, Any]:
    """Assemble a single SectionStateObject per §2."""
    try:
        fp = tsc.fingerprint(body, mode=ctx.fingerprint_mode, opaque_envs=ctx.opaque_envs)
    except tsc.CanonicalizationError as exc:
        # Canonicalizer refuses unterminated verbatim — surface as a warning and
        # fall back to strict mode for this section only (byte-level hash).
        ctx.warnings.append(
            Warning_(
                "CANONICALIZATION_FAILED",
                f"Section '{ ' > '.join(heading_path) }': "
                f"{exc}. Fell back to strict-mode fingerprint for this section.",
            )
        )
        fp = tsc.fingerprint(body, mode="strict")

    # Seed current_tier from classification (§7.1), then let the decisions-log
    # replay in synthesize_tier_entry_log advance running_tier if the log shows
    # the section reached higher. The FINAL running_tier wins — this makes the
    # ledger internally consistent (a precondition for the validator) even when
    # classification.md and tier_decisions_log.md disagree.
    seed_tier = classification_tier if classification_tier != "T0" else "T1"

    entry_log, last_approved, iter_count, final_tier = synthesize_tier_entry_log(
        ctx, escalation_rows, decisions_rows, initial_tier=seed_tier
    )

    if final_tier != seed_tier:
        ctx.warnings.append(
            Warning_(
                "CURRENT_TIER_FROM_LOG",
                f"Section '{' > '.join(heading_path)}': classification seed "
                f"was {seed_tier}, but tier_decisions_log replay ended at "
                f"{final_tier}. current_tier set to {final_tier} for internal "
                "consistency.",
            )
        )

    current_tier = final_tier

    # ceiling_locked per §7.1: true iff current_tier == default_final_tier AND
    # default_final_tier < T4. The T4 case is never ceiling-locked (T4 is the
    # top of the staircase). T4_ready is also not a locking state (it's a
    # sentinel between T3 approval and T4 admission).
    ceiling_locked = (
        current_tier == ctx.default_final_tier
        and ctx.default_final_tier not in ("T4",)
    )

    return {
        "heading_path": heading_path,
        "current_tier": current_tier,
        "last_approved_tier": last_approved,
        "ceiling_locked": ceiling_locked,
        "section_ceiling_override": None,
        "iteration_count_at_current_tier": iter_count,
        "last_scope_fingerprint": fp,
        "fingerprint_computed_at": ctx.utc_now,
        "cumulative_drift_lines_since_approval": 0,
        "tier_entry_log": entry_log,
    }


# ----------------------------------------------------------------- writer


def atomic_write(ctx: MigrationContext, payload: dict[str, Any]) -> None:
    """Write reviews/tier_state.json per §5 atomic contract.

    On a fresh migration there is no prior mtime/sha256 to compare against, so
    the full 6-step contract collapses to lockfile acquisition + .tmp write +
    rename. If a prior file exists and --force is in effect, it is backed up to
    reviews/tier_state.json.bak.<timestamp> before rename.
    """
    target = ctx.tier_state_path
    target.parent.mkdir(parents=True, exist_ok=True)

    lockfile = target.with_suffix(target.suffix + ".lock")
    # POSIX advisory lockfile: O_CREAT|O_EXCL so a concurrent Planner write
    # aborts cleanly rather than races with us.
    try:
        lock_fd = os.open(str(lockfile), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise SystemExit(
            "[LOCK-HELD] reviews/tier_state.json.lock exists; another writer is "
            "active. Remove the lockfile manually if you are sure no process "
            "holds it, then re-run."
        )
    try:
        if target.exists():
            bak = ctx.backup_dir / f"tier_state.json.bak.{ctx.utc_now.replace(':', '')}"
            ctx.backup_dir.mkdir(parents=True, exist_ok=True)
            bak.write_bytes(target.read_bytes())
            _prune_backups(ctx.backup_dir, BACKUP_RETENTION)

        # Write to a temp file in the same directory so rename() is same-fs atomic.
        fd, tmp_name = tempfile.mkstemp(
            dir=str(target.parent), prefix=".tier_state.", suffix=f".tmp.{os.getpid()}"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, ensure_ascii=False)
                fh.write("\n")
            os.replace(tmp_name, str(target))
        except BaseException:
            # Best-effort cleanup on failure.
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise
    finally:
        os.close(lock_fd)
        try:
            os.unlink(str(lockfile))
        except OSError:
            pass


def _prune_backups(backup_dir: Path, retention: int) -> None:
    """Keep only the newest `retention` backups by mtime."""
    if not backup_dir.exists():
        return
    backups = sorted(
        (p for p in backup_dir.glob("tier_state.json.bak.*") if p.is_file()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for stale in backups[retention:]:
        try:
            stale.unlink()
        except OSError:
            pass


# ----------------------------------------------------------------- report


def write_migration_report(ctx: MigrationContext, payload: dict[str, Any]) -> None:
    """Write reviews/migration_report_v055_to_v060.md per §7.3."""
    lines: list[str] = []
    lines.append("# v0.5.5 → v0.6.0 Migration Report")
    lines.append("")
    lines.append(f"*Generated: {ctx.utc_now}*")
    lines.append(f"*Project root: `{ctx.project_root}`*")
    lines.append(f"*Schema version written: `{SCHEMA_VERSION}`*")
    lines.append(f"*Default final tier: `{ctx.default_final_tier}`*")
    lines.append(f"*Fingerprint mode: `{ctx.fingerprint_mode}`*")
    lines.append(f"*Sections migrated: {len(payload['sections'])}*")
    lines.append("")

    # ---------- Mapped rows ----------
    lines.append("## 1. Mapped rows")
    lines.append("")
    lines.append("Every v0.5.5 row the migrator inspected, and its v0.6.0 equivalent.")
    lines.append("A v0.6.0 trigger of `—` means the row had no analog and was dropped.")
    lines.append("")
    lines.append("| Source artefact | Source fragment | v0.6.0 trigger | Note |")
    lines.append("|---|---|---|---|")
    if not ctx.mapped_rows:
        lines.append("| — | — | — | (no v0.5.5 rows found; see Warnings) |")
    for row in ctx.mapped_rows:
        trig = row.v060_trigger if row.v060_trigger else "—"
        lines.append(
            f"| `{row.source_artefact}` | {row.source_fragment} | `{trig}` | "
            f"{row.note or ''} |"
        )
    lines.append("")

    # ---------- Warnings ----------
    lines.append("## 2. Warnings")
    lines.append("")
    if not ctx.warnings:
        lines.append("No warnings raised during migration.")
    else:
        # Dedup by (category, collapsed-message) to keep the table readable —
        # manuscript-wide events like T4_REQUIRES_LCR fire once per section
        # internally, but the user only needs to see them once, tallied with
        # an occurrence count.
        counts: dict[tuple[str, str], int] = {}
        order: list[tuple[str, str]] = []
        for w in ctx.warnings:
            msg = " ".join(w.message.split())
            key = (w.category, msg)
            if key not in counts:
                order.append(key)
                counts[key] = 0
            counts[key] += 1
        lines.append("| Category | Occurrences | Message |")
        lines.append("|---|---|---|")
        for cat, msg in order:
            n = counts[(cat, msg)]
            occurrences = "1" if n == 1 else f"{n}"
            lines.append(f"| `{cat}` | {occurrences} | {msg} |")
    lines.append("")

    # ---------- User hold-point ----------
    lines.append("## 3. User hold-point (M-4 success metric)")
    lines.append("")
    lines.append(
        "Per `references/tier_state_schema.md §7.3`, the Planner will refuse to "
        "accept `/review` against this project until the user has confirmed this "
        "report. Planner Phase 0 treats the presence of "
        "`reviews/migration_report_v055_to_v060.md` without a corresponding "
        "`user_confirmed_migration_report_at:` entry in `reviews/classification.md` "
        "as a blocking hold (per `tier_notifications.yaml §4 "
        "integrity.migration_report_hold`)."
    )
    lines.append("")
    lines.append("**To clear the hold:**")
    lines.append("")
    lines.append(
        "1. Review §§1–2 of this report. Every row in §1 should correspond to an "
        "intended semantic; every warning in §2 should either be understood or "
        "hand-corrected in the ledger."
    )
    lines.append(
        "2. Append a line to `reviews/classification.md` frontmatter: "
        "`user_confirmed_migration_report_at: <ISO-8601 UTC>`."
    )
    lines.append(
        "3. Invoke `/review` or `/review --section <path>`. Planner Phase 0 will "
        "re-read the classification and clear the hold."
    )
    lines.append("")
    lines.append(
        "Rollback path: migration is one-way. If the ledger is incorrect, delete "
        "`reviews/tier_state.json` and the migration report, re-init the project "
        "from the preserved `research-writing-harness-claude-v0.5.4/` tree, fix "
        "the v0.5.5 source, and re-run this script."
    )
    lines.append("")

    ctx.report_path.write_text("\n".join(lines), encoding="utf-8")


# ----------------------------------------------------------------- validator


def run_validator(ctx: MigrationContext) -> int:
    """Invoke scripts/tier_state_validate.py against the new file; return its exit code."""
    validator = _SCRIPT_DIR / "tier_state_validate.py"
    if not validator.exists():
        ctx.warnings.append(
            Warning_(
                "VALIDATOR_ABSENT",
                f"{validator} not found; skipping post-migration validation.",
            )
        )
        return 0
    try:
        proc = subprocess.run(
            [sys.executable, str(validator), "--file", str(ctx.tier_state_path)],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        ctx.warnings.append(
            Warning_("VALIDATOR_ERRORED", f"Could not invoke validator: {exc}")
        )
        return 0
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    return proc.returncode


# ----------------------------------------------------------------- main


def build_context(args: argparse.Namespace) -> MigrationContext:
    root = Path(args.project_root).resolve()
    if not root.is_dir():
        raise SystemExit(f"[BAD-INVOCATION] --project-root {root} is not a directory")
    manuscript_path = root / args.manuscript
    if not manuscript_path.is_file():
        raise SystemExit(
            f"[MISSING-INPUT] manuscript {manuscript_path} does not exist; "
            "pass --manuscript if it lives elsewhere."
        )
    reviews_dir = root / "reviews"
    classification = reviews_dir / "classification.md"
    if not classification.is_file():
        raise SystemExit(
            f"[MISSING-INPUT] {classification} does not exist. "
            "A v0.5.5 project without classification.md cannot be migrated; "
            "create it by hand with a single `tier:` frontmatter field."
        )
    return MigrationContext(
        project_root=root,
        manuscript_path=manuscript_path,
        classification_path=classification,
        escalation_log_path=reviews_dir / "escalation_log.md",
        tier_decisions_log_path=reviews_dir / "tier_decisions_log.md",
        tier_state_path=reviews_dir / "tier_state.json",
        backup_dir=reviews_dir,
        report_path=reviews_dir / "migration_report_v055_to_v060.md",
        default_final_tier="",  # filled in below
        fingerprint_mode=args.fingerprint_mode,
        opaque_envs=list(args.opaque_env),
        cycle_id=f"cycle-{args.cycle_id}",
        utc_now=_iso_utc_now(),
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--project-root", required=True, help="Project directory")
    ap.add_argument(
        "--manuscript",
        default="manuscript/main.md",
        help="Manuscript file relative to project root (default: manuscript/main.md)",
    )
    ap.add_argument(
        "--default-final-tier",
        choices=DEFAULT_FINAL_TIER_ENUM,
        default=None,
        help="Override for default_final_tier (else inherit from classification.md)",
    )
    ap.add_argument(
        "--fingerprint-mode",
        choices=FINGERPRINT_MODE_ENUM,
        default="tolerant",
    )
    ap.add_argument("--opaque-env", action="append", default=[])
    ap.add_argument(
        "--cycle-id", type=int, default=1, help="Synthetic cycle_id (default: 1)"
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing reviews/tier_state.json (backing it up first).",
    )
    args = ap.parse_args(argv)

    try:
        ctx = build_context(args)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        if "[BAD-INVOCATION]" in str(exc):
            return 4
        return 1

    # Output collision.
    if ctx.tier_state_path.exists() and not args.force:
        print(
            f"[COLLISION] {ctx.tier_state_path} already exists. Pass --force to "
            "overwrite (backup will be kept).",
            file=sys.stderr,
        )
        return 3

    # Parse v0.5.5 artefacts.
    classification_tier = parse_classification(ctx)
    ctx.default_final_tier = coerce_default_final_tier(
        ctx, classification_tier, args.default_final_tier
    )
    # The effective classification_tier is the one used to seed each section's
    # current_tier. If T0, we coerce to T1 — it is the entry rung of the v0.6.0
    # staircase and the safest starting point.
    effective_initial_tier = (
        "T1" if classification_tier in (None, "T0") else classification_tier
    )
    if effective_initial_tier not in ("T1", "T2", "T3", "T4"):
        print(
            f"[BAD-INVOCATION] classification tier {classification_tier!r} is "
            "not recognized",
            file=sys.stderr,
        )
        return 4
    # T4 cannot be both initial and ceiling — the ceiling must be strictly
    # above the current tier unless the section is ceiling-locked. Sections
    # starting at T4 can only do so under the LCR, which the migrator does not
    # replay. Downgrade silently to T4_ready and record a warning.
    if effective_initial_tier == "T4":
        ctx.warnings.append(
            Warning_(
                "T4_INITIAL_COERCED",
                "Classification tier T4 coerced to T4_ready at migration. The "
                "Planner will run a Laggard Clearance Report cycle to complete "
                "the climb.",
            )
        )
        effective_initial_tier = "T4_ready"

    sections_ast = parse_manuscript_sections(ctx)
    escalation_rows = parse_escalation_log(ctx)
    decisions_rows = parse_tier_decisions_log(ctx)

    # Assemble per-section state.
    section_states: list[dict[str, Any]] = []
    for heading_path, body in sections_ast:
        section_states.append(
            build_section_state(
                ctx,
                heading_path=heading_path,
                body=body,
                escalation_rows=escalation_rows,
                decisions_rows=decisions_rows,
                classification_tier=effective_initial_tier,
            )
        )

    # Top-level payload.
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "manuscript_id": _slugify(ctx.project_root.name),
        "default_final_tier": ctx.default_final_tier,
        "fingerprint_mode": ctx.fingerprint_mode,
        "terminal_tier_reached": False,
        "last_updated": ctx.utc_now,
        "sections": section_states,
    }

    # Write.
    try:
        atomic_write(ctx, payload)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 4

    # Report.
    write_migration_report(ctx, payload)

    # Validate.
    rc = run_validator(ctx)
    if rc != 0:
        print(
            f"[VALIDATION-FAILED] tier_state_validate exited {rc}. The file was "
            "written, but you should inspect the validator output above before "
            "using it. The migration report is still at "
            f"{ctx.report_path}.",
            file=sys.stderr,
        )
        return 2

    print(f"Migration complete. Ledger: {ctx.tier_state_path}")
    print(f"                    Report: {ctx.report_path}")
    if ctx.warnings:
        print(
            f"                    Warnings: {len(ctx.warnings)} (see report §2).",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
