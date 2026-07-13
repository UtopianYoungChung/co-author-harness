#!/usr/bin/env python3
# =============================================================================
# pre_phase_advance_check.py — authoritative pre-advance guardrail (v0.7.4+).
#
# Operates against the phase-named ledger `reviews/phase_state.json` under the
# Lifecycle-Phase Ladder (Ph1/Ph2/Ph3/Ph4). The clause implementations retain
# their stable T-coded internal API; `load_ledger` translates the Ph-coded
# ledger in memory (field names, enum values, and the eight renamed triggers).
# The retired tier-named surface (`reviews/tier_state.json`,
# `pre_tier_advance_check.py`) is never read or written.
#
# Internal T-code map (identifiers below only; never an on-disk surface):
#   T1/T2/T3/T4              <- Ph1/Ph2/Ph3/Ph4
#   current_tier             <- current_phase
#   T3_converged             <- Ph3_converged
#   [T3-STALE]               <- [Ph3-STALE]
#   default_final_tier       <- default_final_phase
#   eg1_t4_downgrade_to_t3   <- eg1_ph4_downgrade_to_ph3
#   t{1,2,3}_* triggers      <- ph{1,2,3}_* triggers (see load_ledger trigger_map)
# =============================================================================
"""pre_phase_advance_check.py — mandatory pre-flight guardrail before any section phase advance.

Grounding:
  - references/PHASE_PROTOCOL.md §§3.2.1, 3.3.1 (escalation-ownership carryforward,
    [Ph3-STALE] dual-state semantics).
  - references/PHASE_PROTOCOL.md §6.3a (structured row schemas — contract for clause g).
  - references/PHASE_PROTOCOL.md §9 (Manuscript Convergence Report — contract for clause f).
  - references/phase_state_schema.md §6 (failure codes, validator handoff).
  - TIER_REDESIGN_v0.7-draft-5.md §7.3 (script specification, clauses a–d, f, g).

Usage
    pre_phase_advance_check.py
        --project-root <path>
        --section <heading-path-json>     # e.g., '["3. Theory"]'
        --target-tier <Ph1|Ph2|Ph3|Ph4>   # phase the advance is moving *into*
                                          # (T1–T4 accepted as legacy aliases)

Optional
    --t3-staleness-budget-days <int>      Override default 14-day budget for the
                                          [T3-STALE] clearance check (clause f).
    --json                                Emit findings as JSON (machine-readable).
    --strict-clause-f                     Treat MCR clearance failures as hard
                                          errors even on single-section advances
                                          below T4 (default: clause (f) activates
                                          only when target_tier == T4).

Reads
    reviews/phase_state.json                  the phase-named ledger (schema_version 0.7.4).
    reviews/ph1_draft_completion.md           exit artefact for Ph1.
    reviews/ph2_review_completion.md          exit artefact for Ph2.
    reviews/ph3_convergence_signoff.md        cumulative Ph3 signoff file.
    reviews/ph4_ship_signoff.md               exit artefact for Ph4.
    reviews/convergence_log.md                escalation ownership ledger.

Exit codes
    0  all clauses pass; advance may proceed.
    1  one or more clauses failed; see stdout/stderr for the named codes.
    2  bad invocation (unknown phase, unreadable file, etc.).

Clauses (reference: draft-5 §7.3)
    (a) exit-artefact present and well-formed for the prior phase.
    (b) required SectionStateObject fields populated for the target phase.
    (c) ESCALATED-finding owner assigned; every transferred_to carries non-empty
        transfer_rationale (Linear-Accountability defence).
    (d) ph1_pstage_declaration populated before Ph2 admission.
    (f) MCR clearance for Ph4 admission, including the ceiling-lock disjunction
        (§9.4) and computed [Ph3-STALE] = false on every in-scope section
        (§3.3.1, §9.3).
    (g) row-shape conformance of every row in phase_entry_log and
        ph3_convergence_signoff.md against the §6.3a schemas.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import milestone_framework_validate as milestone_validator


# ----------------------------------------------------------------- constants

SCHEMA_VERSION_EXPECTED = "0.7.4"
TIER_ENUM_CURRENT = ("T1", "T2", "T3", "T3_converged", "T4")
TIER_ENUM_APPROVED = ("T1", "T2", "T3", "T4")  # T3_converged is never a last_approved_tier
TIER_ENUM_TARGET = ("T1", "T2", "T3", "T4")  # target tier of an advance
ACTOR_ENUM = ("planner", "evaluator", "generator", "reflector", "user")
DEFAULT_T3_STALENESS_BUDGET_DAYS = 14

# Canonical trigger enum replicated (in internal T-coded form) from
# phase_state_schema.md §3.1. Migrated
# rows may still reference the retired `confirmation_failed` trigger; it is
# accepted on read but never emitted by v0.7.0 write paths.
VALID_TRIGGERS = frozenset({
    "initial_dispatch",
    "user_approval",
    "user_rejection",
    "user_defer",
    "fingerprint_reset",
    "mcr_admission",
    "laggard_clearance_cancelled",
    "ceiling_locked",
    "ceiling_raised",
    "override_applied",
    "retraction",
    "t1_draft_completion_signed",
    # imodel_structural_validation_signed — RETIRED at v0.11.0; was tied to the
    # i* SD/SR opt-in gate. Migrated rows in v0.10.x → v0.11.0 projects are
    # preserved read-only by scripts/migrate_v0100_to_v0110_drop_sd_sr.py for
    # audit continuity but never appear in fresh ledgers.
    "t2_review_completion_signed",
    "escalation_owner_transferred",
    "escalation_named_owner_assigned",
    "t3_iteration_round",
    "t3_convergence_signoff_row",
    "t3_stale_reengagement_signoff",
    "t3_convergence_signoff_terminal",
    "mcr_blocked_t3_stale",
    "eg7_mcr_readmission_after_class_change",
    "eg1_t4_downgrade_to_t3",
    "eg6_override_inconsistency_warning",
    "m5_wiki_ingest",
    "plugin_update_proposed_by_planner",
    "v0_7_state_rename",
    # Retired but migration-compatible: v0.6.0 ledgers with existing rows may
    # still carry this trigger; pre-advance check tolerates it on read.
    "confirmation_failed",
    # LCR audit-continuity alias: laggard_clearance_cancelled retained.
    "laggard_clearance_approved",  # accepted on read (pre-migration); v0.7.0 writes mcr_admission
    # v0.10.0 S2 — snowball-driven reference scaffolding (architecture
    # 2026-04-26-snowball-reference-architecture.md §6.3 row 6 of the §6.0
    # coupling checklist; Planner writes this row at run-phase-1 §3 Step 4.5
    # / agents/planner.md Phase 3.7 on SK-NEW-A clean exit). Within-phase
    # artefact-completion trigger that fires at SK-NEW-A clean exit, not at
    # Phase 5.5. Per phase_state_schema.md §3.1 line 193 (Sub-B's S2 edit). Without this
    # entry, every Ph1->Ph2 advance with a trigger-31 row would fail clause (g)
    # row-shape conformance with TRIGGER_UNKNOWN.
    "seed_snowball_signed",
    # v0.7.2 accessibility gate (trigger 28), v0.7.4 P-7 manuscript-level
    # batching (trigger 29), and v0.7.4 P-2 stability escalation (trigger 30).
    # All three were introduced with phase-era names and have no tier-coded
    # alias in load_ledger's trigger_map — accepted verbatim.
    "ph3_accessibility_blocker_surfaced",
    "ph3_iteration_round_manuscript",
    "stability_mode_escalated_to_full_ph3",
})

# v0.10.0 S2 — Non-blocking advisory on the v0.10.0 references_initialized
# field at Ph1->Ph2 advance. Per architecture §6.3 row 6 of the §6.0 coupling
# checklist, this clause SURFACES (does not enforce) the field's state at the
# advance boundary. Blocking enforcement defers to Step 0.5 placeholder in
# skills/run-phase-2/SKILL.md (also non-blocking) and to the eventual S3/S4
# wiring of full Ph2-side dispatch. Returns an advisory string for the report
# section, or None if not applicable / field is true.
def references_initialized_advisory(
    section_state: dict, target_tier: str
) -> str | None:
    """v0.10.0 S2 advisory: surface references_initialized: false at Ph1->Ph2.

    Args:
        section_state: the SectionStateObject dict (per phase_state_schema.md §2).
        target_tier: the tier the section is advancing into.

    Returns:
        Advisory string if (a) target is Ph2/T2 AND (b) references_initialized
        is false or absent; None otherwise. The advisory is informational only
        and does not cause clause failure; pre-advance check still permits the
        advance. Step 0.5 of run-phase-2 re-emits W-SNOWBALL-PRECONDITION-UNMET
        on the same condition at Ph2 entry, which is the user-visible signal.
    """
    # Field name uses v0.10.0 naming. Tier name uses script's existing T*
    # vocabulary; "T2" maps to "Ph2" in the phase-named vocabulary.
    if target_tier not in ("T2", "Ph2"):
        return None
    # Local variable named `value` (not `field`) to avoid shadowing the
    # `dataclasses.field` symbol imported at module scope.
    value = section_state.get("references_initialized")
    if value is True:
        return None  # field is set; SK-NEW-A has run cleanly
    return (
        "[ADVISORY v0.10.0 S2] references_initialized is "
        f"{value!r} at Ph1->Ph2 advance. Section can proceed; SK-NEW-A "
        "(seed-snowball-discovery) was not signed at Ph1. Consider running "
        "/seed-snowball-discovery <section> from Ph2 to populate "
        "references/REFERENCES.md before the Evaluator's Step 4 read. "
        "Per architecture §6.3 row 6, this advisory does not refuse the "
        "advance; Step 0.5 of run-phase-2 re-emits W-SNOWBALL-PRECONDITION-UNMET."
    )

# Exit-artefact path per target tier. The prior tier's artefact is the one
# checked by clause (a) before advancing *into* target.
PRIOR_TIER_FOR_TARGET: dict[str, str] = {
    "T2": "T1",
    "T3": "T2",
    "T4": "T3",
}
ARTEFACT_PATH: dict[str, str] = {
    "T1": "reviews/ph1_draft_completion.md",
    "T2": "reviews/ph2_review_completion.md",
    "T3": "reviews/ph3_convergence_signoff.md",
    "T4": "reviews/ph4_ship_signoff.md",
}


# ----------------------------------------------------------------- datatypes


@dataclass
class Finding:
    code: str          # e.g., E-ROW-SHAPE-VIOLATION
    clause: str        # "a".."g" or "boot"
    section: str       # heading_path joined as " > " or "<manuscript>"
    message: str

    def as_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "clause": self.clause,
            "section": self.section,
            "message": self.message,
        }


@dataclass
class CheckContext:
    project_root: Path
    target_tier: str
    target_section_key: str
    target_section: dict[str, Any]
    ledger: dict[str, Any]
    t3_staleness_budget_days: int
    strict_clause_f: bool
    findings: list[Finding] = field(default_factory=list)
    now_utc: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )


@dataclass(frozen=True)
class MilestoneGateResult:
    """Read-only milestone result consumed by the phase guardrail."""

    outcomes: dict[str, str]
    findings: tuple[milestone_validator.Finding, ...]


def check_milestone_gate(
    project_root: Path,
    document: Any,
    target_phase: str,
    terminal_close: bool = False,
) -> MilestoneGateResult:
    """Select a shared pre-transition gate; no milestone predicate lives here."""
    boundary = (
        "ph1_to_ph2" if target_phase == "Ph2"
        else "ph4_terminal_close" if terminal_close
        else "ph4_admission" if target_phase == "Ph4"
        else None
    )
    if boundary is None:
        return MilestoneGateResult({}, ())
    result = milestone_validator.validate_gate(project_root, document, boundary)
    return MilestoneGateResult(result.outcomes, result.findings)


# ----------------------------------------------------------------- helpers


def _heading_key(heading_path: list[str]) -> str:
    return " > ".join(heading_path) if heading_path else "<no heading>"


def _parse_iso(ts: str | None) -> datetime.datetime | None:
    if not ts or not isinstance(ts, str):
        return None
    try:
        # Accept both "...Z" and "...+00:00".
        if ts.endswith("Z"):
            return datetime.datetime.fromisoformat(ts[:-1] + "+00:00")
        return datetime.datetime.fromisoformat(ts)
    except ValueError:
        return None


def _read_text_or_none(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


# ----------------------------------------------------------------- ledger bootstrap


def load_ledger(ctx_args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load phase_state.json and expose its phase-native ledger to the guardrail.

    Returns (ledger, section). Exits code 2 on any structural failure encountered
    before the clause checks can even be reached.
    """
    phase_state_path: Path = ctx_args.project_root / "reviews" / "phase_state.json"
    if not phase_state_path.exists():
        sys.stderr.write(
            f"[pre_phase_advance_check] error: {phase_state_path} not found.\n"
        )
        sys.exit(2)
    try:
        phase_ledger = json.loads(phase_state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(
            f"[pre_phase_advance_check] error: failed to read or parse "
            f"{phase_state_path}: {exc}\n"
        )
        sys.exit(2)
    if phase_ledger.get("schema_version") != SCHEMA_VERSION_EXPECTED:
        sys.stderr.write(
            f"[pre_phase_advance_check] error: ledger schema_version "
            f"{phase_ledger.get('schema_version')!r} is not {SCHEMA_VERSION_EXPECTED!r}.\n"
        )
        sys.exit(2)

    # The clause implementations retain their stable T-coded internal API.
    # Translate the authoritative Ph-coded ledger in memory; never create or
    # read the retired tier_state.json surface.
    phase_to_tier = {
        "Ph1": "T1", "Ph2": "T2", "Ph3": "T3",
        "Ph3_converged": "T3_converged", "Ph4": "T4",
    }
    field_map = {
        "current_phase": "current_tier",
        "last_approved_phase": "last_approved_tier",
        "iteration_count_at_current_phase": "iteration_count_at_current_tier",
        "phase_goal_declared": "tier_goal_declared",
        "phase_deliverable_path": "tier_deliverable_path",
        "ph1_pstage_declaration": "t1_pstage_declaration",
        "ph3_last_activity_at": "t3_last_activity_at",
        "phase_entry_log": "tier_entry_log",
    }
    trigger_map = {
        "ph1_draft_completion_signed": "t1_draft_completion_signed",
        "ph2_review_completion_signed": "t2_review_completion_signed",
        "ph3_iteration_round": "t3_iteration_round",
        "ph3_convergence_signoff_row": "t3_convergence_signoff_row",
        "ph3_stale_reengagement_signoff": "t3_stale_reengagement_signoff",
        "ph3_convergence_signoff_terminal": "t3_convergence_signoff_terminal",
        "mcr_blocked_ph3_stale": "mcr_blocked_t3_stale",
        "eg1_ph4_downgrade_to_ph3": "eg1_t4_downgrade_to_t3",
    }
    ledger = dict(phase_ledger)
    ledger["default_final_tier"] = phase_to_tier.get(
        phase_ledger.get("default_final_phase"), "T3"
    )
    translated_sections: list[dict[str, Any]] = []
    for raw in phase_ledger.get("sections", {}).values():
        section_copy = dict(raw)
        for source, target in field_map.items():
            if source in raw:
                section_copy[target] = raw[source]
        for key in ("current_tier", "last_approved_tier"):
            section_copy[key] = phase_to_tier.get(section_copy.get(key), section_copy.get(key))
        translated_log = []
        for raw_row in raw.get("phase_entry_log", []):
            row = dict(raw_row)
            row["prev_tier"] = phase_to_tier.get(row.pop("prev_phase", None), row.get("prev_tier"))
            row["new_tier"] = phase_to_tier.get(row.pop("new_phase", None), row.get("new_tier"))
            row["trigger"] = trigger_map.get(row.get("trigger"), row.get("trigger"))
            translated_log.append(row)
        section_copy["tier_entry_log"] = translated_log
        translated_sections.append(section_copy)
    ledger["sections"] = translated_sections

    try:
        heading_path = json.loads(ctx_args.section)
        if not isinstance(heading_path, list) or not all(
            isinstance(x, str) for x in heading_path
        ):
            raise ValueError("not a JSON list of strings")
    except (ValueError, json.JSONDecodeError) as exc:
        sys.stderr.write(
            f"[pre_phase_advance_check] error: --section must be a JSON list of "
            f"strings (e.g., '[\"3. Theory\"]'): {exc}\n"
        )
        sys.exit(2)

    target_key = _heading_key(heading_path)
    section: dict[str, Any] | None = None
    for s in ledger.get("sections", []):
        if s.get("heading_path") == heading_path:
            section = s
            break
    if section is None:
        sys.stderr.write(
            f"[pre_phase_advance_check] error: section {target_key!r} not found "
            "in phase_state.json.\n"
        )
        sys.exit(2)
    return ledger, section


# ----------------------------------------------------------------- clause (a)


_FRONTMATTER_RE = re.compile(r"^---\s*\n(?P<body>.*?)\n---\s*\n", re.DOTALL)


def check_clause_a(ctx: CheckContext) -> None:
    """(a) Prior tier's exit artefact exists and is well-formed.

    Well-formed = exists, non-empty, begins with a YAML frontmatter block
    carrying at minimum a `tier:` field matching the prior tier. For T4 target,
    the prior-tier artefact is `ph3_convergence_signoff.md` and the additional
    requirement is that the terminal row is present (checked inline here by a
    cheap scan for `is_terminal: true`; the full §6.3a row-shape check lives
    in clause (g)).
    """
    prior_tier = PRIOR_TIER_FOR_TARGET.get(ctx.target_tier)
    if prior_tier is None:  # target == T1: no prior artefact required
        return
    artefact_path = ctx.project_root / ARTEFACT_PATH[prior_tier]
    text = _read_text_or_none(artefact_path)
    if not text:
        ctx.findings.append(
            Finding(
                code="E-MISSING-T1-SIGNOFF" if prior_tier == "T1" else "E-ARTEFACT-MISSING",
                clause="a",
                section=ctx.target_section_key,
                message=f"Prior-tier exit artefact {artefact_path} is missing or empty.",
            )
        )
        return
    m = _FRONTMATTER_RE.match(text)
    if not m:
        ctx.findings.append(
            Finding(
                code="E-ARTEFACT-MALFORMED",
                clause="a",
                section=ctx.target_section_key,
                message=(
                    f"Prior-tier exit artefact {artefact_path} has no YAML "
                    "frontmatter; the tier: field cannot be verified."
                ),
            )
        )
        return
    prior_phase = prior_tier.replace("T", "Ph", 1)
    if (f"tier: {prior_tier}" not in m.group("body") and
            f"phase: {prior_phase}" not in m.group("body")):
        ctx.findings.append(
            Finding(
                code="E-ARTEFACT-TIER-MISMATCH",
                clause="a",
                section=ctx.target_section_key,
                message=(
                    f"Prior-tier exit artefact {artefact_path} does not declare "
                    f"`phase: {prior_phase}` in its frontmatter."
                ),
            )
        )
        return
    # For T4 target, require at least one is_terminal: true line in the T3 file.
    if ctx.target_tier == "T4":
        if "is_terminal: true" not in text:
            ctx.findings.append(
                Finding(
                    code="E-T3-TERMINAL-ROW-MISSING",
                    clause="a",
                    section=ctx.target_section_key,
                    message=(
                        f"{artefact_path} has no row with `is_terminal: true`; "
                        "the section has not yet reached T3_converged."
                    ),
                )
            )


# ----------------------------------------------------------------- clause (b)


REQUIRED_SECTION_FIELDS = (
    "heading_path",
    "current_tier",
    "last_approved_tier",
    "ceiling_locked",
    "section_ceiling_override",
    "iteration_count_at_current_tier",
    "last_scope_fingerprint",
    "fingerprint_computed_at",
    "cumulative_drift_lines_since_approval",
    "tier_goal_declared",
    "tier_deliverable_path",
    "convergence_metric",
    "t1_pstage_declaration",
    "t3_last_activity_at",
    "tier_entry_log",
)


def check_clause_b(ctx: CheckContext) -> None:
    """(b) Required SectionStateObject fields populated for the target tier.

    All 15 fields must be present (per phase_state_schema.md §2 invariant). The
    tier-dependent requirement is that `tier_goal_declared` and
    `tier_deliverable_path` must be non-empty, and `convergence_metric` must be
    a float (not null) when the target tier is T4 (i.e., the section is
    climbing out of T3_converged into T4).
    """
    section = ctx.target_section
    missing = [f for f in REQUIRED_SECTION_FIELDS if f not in section]
    if missing:
        ctx.findings.append(
            Finding(
                code="SECTION_MISSING_FIELD",
                clause="b",
                section=ctx.target_section_key,
                message=f"SectionStateObject missing required field(s): {', '.join(missing)}.",
            )
        )
        return
    # tier_goal_declared and tier_deliverable_path should always be non-empty
    # once initial_dispatch has fired.
    if not section.get("tier_goal_declared"):
        ctx.findings.append(
            Finding(
                code="SECTION_FIELD_EMPTY",
                clause="b",
                section=ctx.target_section_key,
                message="`tier_goal_declared` is empty; Planner should populate it on tier advance.",
            )
        )
    if not section.get("tier_deliverable_path"):
        ctx.findings.append(
            Finding(
                code="SECTION_FIELD_EMPTY",
                clause="b",
                section=ctx.target_section_key,
                message="`tier_deliverable_path` is empty; Planner should populate it on tier advance.",
            )
        )
    # convergence_metric non-null on T4 admission.
    if ctx.target_tier == "T4" and section.get("convergence_metric") is None:
        ctx.findings.append(
            Finding(
                code="E-T3-CONVERGENCE-NULL-AT-SIGNOFF",
                clause="b",
                section=ctx.target_section_key,
                message=(
                    "Section is admitting to T4 but `convergence_metric` is null; "
                    "the T3 terminal signoff row must carry a float value."
                ),
            )
        )


# ----------------------------------------------------------------- clause (c)


_CONVERGENCE_LOG_ESCALATED_RE = re.compile(
    r"^-\s*finding_id:\s*(?P<fid>[A-Za-z0-9_\-]+).*?$",
    re.MULTILINE,
)


def _parse_convergence_log_blocks(text: str) -> list[dict[str, str]]:
    """Parse convergence_log.md as a sequence of YAML-ish blocks.

    A minimal parser: split on top-level "- finding_id:" markers, then for each
    block gather key: value pairs. This is not a full YAML parser — it is
    the minimum viable to surface E-ESCALATION-WITHOUT-OWNER and
    E-OWNERSHIP-TRANSFER-WITHOUT-RATIONALE at the correct granularity.
    """
    blocks: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- finding_id:"):
            if current:
                blocks.append(current)
            current = {"finding_id": stripped.split(":", 1)[1].strip()}
            continue
        if ":" in stripped and not stripped.startswith("#"):
            key, val = stripped.split(":", 1)
            current[key.strip().lstrip("- ").strip()] = val.strip()
    if current:
        blocks.append(current)
    return blocks


def check_clause_c(ctx: CheckContext) -> None:
    """(c) ESCALATED-finding owner present; transferred_to paired with transfer_rationale.

    Implements the Linear-Accountability defence (TIER_PROTOCOL.md §3.2.1 and
    phase_state_schema.md §6.1 codes E-ESCALATION-WITHOUT-OWNER /
    E-OWNERSHIP-TRANSFER-WITHOUT-RATIONALE).
    """
    log_path = ctx.project_root / "reviews" / "convergence_log.md"
    text = _read_text_or_none(log_path)
    if text is None:
        # At T2 target with no convergence log yet, this is acceptable — the log
        # is first created on T3 entry. Skip silently.
        return
    blocks = _parse_convergence_log_blocks(text)
    for b in blocks:
        fid = b.get("finding_id", "?")
        status = b.get("status", "")
        if status.upper() != "ESCALATED":
            continue
        owner = b.get("current_owner") or b.get("owner")
        if not owner:
            ctx.findings.append(
                Finding(
                    code="E-ESCALATION-WITHOUT-OWNER",
                    clause="c",
                    section=ctx.target_section_key,
                    message=(
                        f"Finding {fid} has status: ESCALATED but no current_owner / owner."
                    ),
                )
            )
        if "transferred_to" in b:
            rationale = b.get("transfer_rationale", "").strip()
            if not rationale:
                ctx.findings.append(
                    Finding(
                        code="E-OWNERSHIP-TRANSFER-WITHOUT-RATIONALE",
                        clause="c",
                        section=ctx.target_section_key,
                        message=(
                            f"Finding {fid} carries a transferred_to field but "
                            "empty transfer_rationale (required by the Linear-"
                            "Accountability defence)."
                        ),
                    )
                )


# ----------------------------------------------------------------- clause (d)


def check_clause_d(ctx: CheckContext) -> None:
    """(d) t1_pstage_declaration set + classification.md present before T2 admission.

    Fires only when target_tier == T2. Two sub-checks:

    (d.1) classification.md presence (added at v0.11.0 c11). The Ph1->Ph2
    advance reads `reviews/classification.md` for paper type, P-stage,
    venue, and default_final_phase. Without this file the Planner
    cannot dispatch a Ph2 Evaluator pass against the right register —
    the SAFEGUARD checks, the deterministic-check mandatory subset, and
    the Reflector-lightweight integrity probe all read it. Missing
    classification.md is a hard BLOCKER (E-CLASSIFICATION-MISSING-AT-T2).

    (d.2) t1_pstage_declaration. A null pstage on T2 admission surfaces
    W-PSTAGE-UNAVAILABLE (warning, not error) unless the section has a
    non-null last_approved_tier (i.e., the T2 advance is not a first-time
    pass), in which case the null is treated as a hard error because the
    P-Stage Checker cannot run.
    """
    if ctx.target_tier != "T2":
        return
    section = ctx.target_section

    # (d.1) classification.md presence — v0.11.0 c11.
    classification_path = ctx.project_root / "reviews" / "classification.md"
    if not classification_path.exists():
        ctx.findings.append(
            Finding(
                code="E-CLASSIFICATION-MISSING-AT-T2",
                clause="d",
                section=ctx.target_section_key,
                message=(
                    f"reviews/classification.md is missing at T2 admission. "
                    f"The Ph1->Ph2 advance requires classification (paper type, "
                    f"P-stage, venue, default_final_phase) before the Evaluator "
                    f"can dispatch. Run /classify-manuscript or hand-author the "
                    f"file at {classification_path}."
                ),
            )
        )

    # (d.2) t1_pstage_declaration populated.
    if section.get("t1_pstage_declaration") is None:
        if section.get("last_approved_tier") is None:
            # First-time T2 admission with no prior approval history;
            # surface as warning only. Tolerate-and-log.
            ctx.findings.append(
                Finding(
                    code="W-PSTAGE-UNAVAILABLE",
                    clause="d",
                    section=ctx.target_section_key,
                    message=(
                        "t1_pstage_declaration is null at T2 admission. P-Stage "
                        "Checker will be inert until populated."
                    ),
                )
            )
        else:
            ctx.findings.append(
                Finding(
                    code="E-PSTAGE-REQUIRED-AT-T2",
                    clause="d",
                    section=ctx.target_section_key,
                    message=(
                        "Section has prior approval history but no "
                        "t1_pstage_declaration; P-Stage Checker cannot run."
                    ),
                )
            )


# ----------------------------------------------------------------- clause (e)
#
# RETIRED at v0.11.0. Was the Cold-Start defence tied to the i* SD/SR
# opt-in gate (TIER_PROTOCOL.md §3.1.1 / §3.1.2). v0.11.0 removed the
# entire opt-in surface; no clause-(e) check runs in fresh ledgers.
# Migrated rows in v0.10.x → v0.11.0 projects are preserved read-only
# by scripts/migrate_v0100_to_v0110_drop_sd_sr.py for audit continuity.

# ----------------------------------------------------------------- clause (f)


def _is_mcr_cleared(section: dict[str, Any], default_final_tier: str) -> bool:
    """Return True iff the section satisfies the v0.7.0 MCR admission disjunction.

    Per TIER_PROTOCOL.md §9.4: cleared iff either (i) current_tier ==
    T3_converged, or (ii) ceiling_locked == True AND last_approved_tier ==
    applicable_ceiling.
    """
    if section.get("current_tier") == "T3_converged":
        return True
    override = section.get("section_ceiling_override")
    ceilings = [default_final_tier]
    if override:
        ceilings.append(override)
    # min_by_tier: lower tier ordinal wins.
    order = {"T1": 1, "T2": 2, "T3": 3, "T4": 4}
    applicable = min(ceilings, key=lambda t: order.get(t, 99))
    last_approved = section.get("last_approved_tier")
    return bool(section.get("ceiling_locked")) and last_approved == applicable


# v0.15.0-pre PR-3b.2 — deterministic convergence evidence at the MCR
# boundary. This helper produces an *advisory* signal only. It does not
# substitute for the human terminal signoff that flips Ph3 -> Ph3_converged
# (planner.md §3 TerminalSignoffRow); `_is_mcr_cleared` is intentionally
# untouched and `E-MCR-NOT-CLEARED` continues to gate admission. The signal
# exists so future readers can align with a mechanical convergence test
# instead of inspecting the convergence_log by eye.
_NON_REFINE_PROFILES = frozenset({"deep", "structural", "stability"})

_CONV_LOG_ROW_RE = re.compile(
    r"^\s*-\s*iteration_index:\s*(?P<idx>\d+)\s*$", re.MULTILINE
)


def _parse_convergence_log_iteration_rows(text: str) -> list[dict[str, str]]:
    """Parse the iteration-row form of convergence_log.md.

    Each row is a YAML-ish block starting with `- iteration_index: <int>`.
    We collect the immediately-following key: value lines until the next
    iteration_index marker. Unknown keys are preserved verbatim — the helper
    is consumer-shaped, not validator-shaped.

    Returns rows in file order (oldest first).
    """
    rows: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        m = re.match(r"^\s*-\s*iteration_index:\s*(\d+)\s*$", line)
        if m:
            if current is not None:
                rows.append(current)
            current = {"iteration_index": m.group(1)}
            continue
        if current is None:
            continue
        # Stop accumulating once we hit a non-key-value line that signals a
        # different block type (defensive — convergence_log is mixed-content).
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- finding_id:"):
            # A different block shape — flush current and stop reading.
            rows.append(current)
            current = None
            continue
        if ":" in stripped and not stripped.startswith("-"):
            key, val = stripped.split(":", 1)
            current[key.strip()] = val.strip()
    if current is not None:
        rows.append(current)
    return rows


def _row_section_key(row: dict[str, str]) -> str | None:
    """Return the normalized section key carried by a convergence-log row.

    Historical rows may omit a section key entirely. PR-3b.2 treats such rows
    as project-scoped for backward compatibility. When a row does carry a
    section key, the advisory must only fire for the matching section.
    """
    for field in ("section", "Section", "heading_path", "section_heading_path"):
        value = row.get(field)
        if value:
            return value.strip().strip("[]").replace("/", " > ")
    return None


def _compute_mcr_convergence_evidence(
    section: dict[str, Any], convergence_log_text: str | None
) -> bool:
    """Return True iff the last two iteration rows in convergence_log.md
    satisfy the strict non-refine stability definition:

        * both rows carry an explicit `profile:` field in
          {deep, structural, stability} — `refine` and missing both disqualify
        * both rows carry `findings_count_delta: 0`
        * both rows carry the SAME non-null `convergence_metric` value

    Strict semantics by design: a missing `profile` field is treated as
    "no advisory evidence available," NOT as a finding. The advisory is
    purely additive; absence does not block anything.

    If convergence-log rows carry a section key, the last two relevant rows
    must match the section under review. Rows without a section key are treated
    as project-scoped for backward compatibility with older logs.
    """
    if not convergence_log_text:
        return False
    rows = _parse_convergence_log_iteration_rows(convergence_log_text)
    section_key = _heading_key(section.get("heading_path", []))
    matching_rows: list[dict[str, str]] = []
    for row in rows:
        row_key = _row_section_key(row)
        if row_key is None or row_key == section_key:
            matching_rows.append(row)
    rows = matching_rows
    if len(rows) < 2:
        return False
    last_two = rows[-2:]
    for row in last_two:
        profile = row.get("profile")
        if profile not in _NON_REFINE_PROFILES:
            return False
        if row.get("findings_count_delta") != "0":
            return False
    metric_a = last_two[0].get("convergence_metric")
    metric_b = last_two[1].get("convergence_metric")
    if not metric_a or not metric_b or metric_a in ("null", "None"):
        return False
    return metric_a == metric_b


def _is_t3_stale(section: dict[str, Any], budget_days: int, now: datetime.datetime) -> bool:
    """Compute [T3-STALE] per Option A (TIER_PROTOCOL.md §3.3.1)."""
    if section.get("current_tier") != "T3":
        return False
    last_activity = _parse_iso(section.get("t3_last_activity_at"))
    if last_activity is None:
        return False
    delta = now - last_activity
    return delta > datetime.timedelta(days=budget_days)


def check_clause_f(ctx: CheckContext) -> None:
    """(f) MCR clearance before T4 admission; [T3-STALE] = false on every section.

    When target_tier == T4 (manuscript-wide admission), every in-scope section
    must satisfy the MCR disjunction in §9.4 and have [T3-STALE] = false.

    When target_tier != T4 and --strict-clause-f is not supplied, clause (f)
    is inactive. When --strict-clause-f is supplied on a target < T4 (e.g., a
    single-section T3 climb), the clause applies only to the target section.
    """
    if ctx.target_tier != "T4" and not ctx.strict_clause_f:
        return

    default_final_tier = ctx.ledger.get("default_final_tier", "T3")
    sections = (
        ctx.ledger.get("sections", [])
        if ctx.target_tier == "T4"
        else [ctx.target_section]
    )
    stale_sections: list[str] = []
    unadmitted_sections: list[str] = []
    missing_deep_pass: list[str] = []
    for s in sections:
        key = _heading_key(s.get("heading_path", []))
        if not _is_mcr_cleared(s, default_final_tier):
            unadmitted_sections.append(key)
        if _is_t3_stale(s, ctx.t3_staleness_budget_days, ctx.now_utc):
            stale_sections.append(key)
        if s.get("pre_mcr_deep_pass_completed") is not True:
            missing_deep_pass.append(key)
    if unadmitted_sections:
        ctx.findings.append(
            Finding(
                code="E-MCR-NOT-CLEARED",
                clause="f",
                section="<manuscript>",
                message=(
                    "Sections not at T3_converged and not ceiling-lock-terminal: "
                    + ", ".join(unadmitted_sections)
                ),
            )
        )
    if stale_sections:
        ctx.findings.append(
            Finding(
                code="E-MCR-BLOCKED-T3-STALE",
                clause="f",
                section="<manuscript>",
                message=(
                    f"Sections with computed [T3-STALE] = true (> "
                    f"{ctx.t3_staleness_budget_days} days): "
                    + ", ".join(stale_sections)
                    + ". User must sign a re-engagement row on each before MCR admission."
                ),
            )
        )
    if missing_deep_pass:
        ctx.findings.append(
            Finding(
                code="E-MCR-PRE-DEEP-PASS-REQUIRED",
                clause="f",
                section="<manuscript>",
                message=("Sections missing a completed deep pre-MCR pass: "
                         + ", ".join(missing_deep_pass)),
            )
        )

    # v0.15.0-pre PR-3b.2 — advisory convergence-evidence emission. This is
    # additive: it does not change `_is_mcr_cleared`, does not affect the
    # exit code (W- prefix routes to warnings per main()), and does not
    # substitute for the TerminalSignoffRow that authorizes Ph3 -> Ph3_converged.
    log_path = ctx.project_root / "reviews" / "convergence_log.md"
    log_text = _read_text_or_none(log_path)
    if log_text:
        for s in sections:
            key = _heading_key(s.get("heading_path", []))
            if _compute_mcr_convergence_evidence(s, log_text):
                ctx.findings.append(
                    Finding(
                        code="W-MCR-CONVERGENCE-EVIDENCE",
                        clause="f",
                        section=key,
                        message=(
                            "Last two convergence_log iteration rows show "
                            "stability under a non-refine profile (deep / "
                            "structural / stability). Evidence-only — does "
                            "NOT authorize MCR admission; the terminal "
                            "signoff in ph3_convergence_signoff.md is the "
                            "authority. See phase_state_schema.md §2.2 "
                            "and PR-3b.2 release notes."
                        ),
                    )
                )


# ----------------------------------------------------------------- clause (g)


_T3_SIGNOFF_BLOCK_SPLIT_RE = re.compile(r"^(?:-{3,}|- )\s*$", re.MULTILINE)


def _parse_t3_signoff_rows(text: str) -> list[dict[str, str]]:
    """Parse ph3_convergence_signoff.md rows as loose YAML-ish blocks.

    We expect each row to be a YAML block delimited by `---` markers or by
    top-level "- row_timestamp:" entries. This parser tolerates both layouts
    and emits one dict per row. Values are captured verbatim as strings.
    """
    rows: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- row_timestamp:"):
            if current:
                rows.append(current)
            current = {"row_timestamp": stripped.split(":", 1)[1].strip()}
            continue
        if stripped.startswith("row_timestamp:"):
            if current:
                rows.append(current)
            current = {"row_timestamp": stripped.split(":", 1)[1].strip()}
            continue
        if current is None:
            continue
        if ":" in stripped and not stripped.startswith("#"):
            key, val = stripped.split(":", 1)
            current[key.strip().lstrip("- ").strip()] = val.strip()
    if current:
        rows.append(current)
    return rows


def _check_tier_entry_log_row(
    ctx: CheckContext, row: dict[str, Any], idx: int
) -> list[Finding]:
    """Validate one row against the §3a.1 TierEntryLogRow schema."""
    findings: list[Finding] = []
    required = ("timestamp", "trigger", "prev_tier", "new_tier", "actor")
    for field_ in required:
        if field_ not in row:
            findings.append(
                Finding(
                    code="E-ROW-SHAPE-VIOLATION",
                    clause="g",
                    section=ctx.target_section_key,
                    message=f"tier_entry_log[{idx}] missing required field `{field_}`.",
                )
            )
    trig = row.get("trigger")
    if trig is not None and trig not in VALID_TRIGGERS:
        findings.append(
            Finding(
                code="TRIGGER_UNKNOWN",
                clause="g",
                section=ctx.target_section_key,
                message=f"tier_entry_log[{idx}] has unknown trigger {trig!r}.",
            )
        )
    actor = row.get("actor")
    if actor is not None and actor not in ACTOR_ENUM:
        findings.append(
            Finding(
                code="E-ROW-SHAPE-VIOLATION",
                clause="g",
                section=ctx.target_section_key,
                message=f"tier_entry_log[{idx}] has illegal actor {actor!r}.",
            )
        )
    for field_ in ("prev_tier", "new_tier"):
        v = row.get(field_)
        if v is not None and v not in TIER_ENUM_CURRENT:
            findings.append(
                Finding(
                    code="E-ROW-SHAPE-VIOLATION",
                    clause="g",
                    section=ctx.target_section_key,
                    message=(
                        f"tier_entry_log[{idx}] has illegal `{field_}` value {v!r}."
                    ),
                )
            )
    notes = row.get("notes")
    if notes is not None and isinstance(notes, str) and len(notes) > 280:
        findings.append(
            Finding(
                code="E-ROW-SHAPE-VIOLATION",
                clause="g",
                section=ctx.target_section_key,
                message=(
                    f"tier_entry_log[{idx}] `notes` exceeds 280-char bound "
                    f"({len(notes)} chars)."
                ),
            )
        )
    return findings


def _check_signoff_row(
    ctx: CheckContext, row: dict[str, str], idx: int
) -> list[Finding]:
    """Validate one row from ph3_convergence_signoff.md against §3a.2 / §3a.3."""
    findings: list[Finding] = []
    is_terminal = row.get("is_terminal", "").lower() == "true"
    is_reengagement = row.get("is_reengagement", "").lower() == "true"
    if is_terminal and is_reengagement:
        findings.append(
            Finding(
                code="E-ROW-SHAPE-VIOLATION",
                clause="g",
                section=ctx.target_section_key,
                message=(
                    f"ph3_convergence_signoff.md row[{idx}] has both "
                    "`is_terminal: true` and `is_reengagement: true`; mutually exclusive."
                ),
            )
        )
    if not is_terminal and not is_reengagement:
        findings.append(
            Finding(
                code="E-ROW-SHAPE-VIOLATION",
                clause="g",
                section=ctx.target_section_key,
                message=(
                    f"ph3_convergence_signoff.md row[{idx}] has neither "
                    "`is_terminal: true` nor `is_reengagement: true`; exactly one required."
                ),
            )
        )
        return findings
    common = ("row_timestamp", "iteration_number", "user_signature", "user_signed_at")
    for field_ in common:
        if field_ not in row:
            findings.append(
                Finding(
                    code="E-ROW-SHAPE-VIOLATION",
                    clause="g",
                    section=ctx.target_section_key,
                    message=(
                        f"ph3_convergence_signoff.md row[{idx}] missing "
                        f"required field `{field_}`."
                    ),
                )
            )
    if is_terminal:
        for field_ in ("convergence_metric_value", "t3_verdict", "final_owner_state"):
            if field_ not in row:
                findings.append(
                    Finding(
                        code="E-ROW-SHAPE-VIOLATION",
                        clause="g",
                        section=ctx.target_section_key,
                        message=(
                            f"ph3_convergence_signoff.md terminal row[{idx}] missing "
                            f"required field `{field_}`."
                        ),
                    )
                )
        # Non-null convergence metric on the terminal row.
        cmv = row.get("convergence_metric_value", "").strip().lower()
        if cmv in ("", "null", "none"):
            findings.append(
                Finding(
                    code="E-T3-CONVERGENCE-NULL-AT-SIGNOFF",
                    clause="g",
                    section=ctx.target_section_key,
                    message=(
                        f"ph3_convergence_signoff.md terminal row[{idx}] has "
                        "null/empty convergence_metric_value."
                    ),
                )
            )
        verdict = row.get("t3_verdict", "")
        if verdict and verdict not in ("CONVERGING", "CONTESTED", "DIVERGING"):
            findings.append(
                Finding(
                    code="E-ROW-SHAPE-VIOLATION",
                    clause="g",
                    section=ctx.target_section_key,
                    message=(
                        f"ph3_convergence_signoff.md terminal row[{idx}] has "
                        f"illegal t3_verdict {verdict!r}."
                    ),
                )
            )
    if is_reengagement:
        if "cleared_stale_at" not in row:
            findings.append(
                Finding(
                    code="E-ROW-SHAPE-VIOLATION",
                    clause="g",
                    section=ctx.target_section_key,
                    message=(
                        f"ph3_convergence_signoff.md re-engagement row[{idx}] "
                        "missing required field `cleared_stale_at`."
                    ),
                )
            )
        # t3_verdict MUST NOT appear on a re-engagement row.
        if "t3_verdict" in row:
            findings.append(
                Finding(
                    code="E-ROW-SHAPE-VIOLATION",
                    clause="g",
                    section=ctx.target_section_key,
                    message=(
                        f"ph3_convergence_signoff.md re-engagement row[{idx}] "
                        "carries `t3_verdict` (only legal on terminal rows)."
                    ),
                )
            )
    notes = row.get("notes")
    if notes is not None and isinstance(notes, str) and len(notes) > 560:
        findings.append(
            Finding(
                code="E-ROW-SHAPE-VIOLATION",
                clause="g",
                section=ctx.target_section_key,
                message=(
                    f"ph3_convergence_signoff.md row[{idx}] `notes` exceeds "
                    f"560-char bound ({len(notes)} chars)."
                ),
            )
        )
    return findings


def check_clause_g(ctx: CheckContext) -> None:
    """(g) Row-shape conformance in tier_entry_log and ph3_convergence_signoff.md.

    Iterates the last 100 rows of tier_entry_log (for performance; Reflector-
    full at T4 does a full scan per phase_state_schema.md §3a.4) and every row
    in ph3_convergence_signoff.md.
    """
    log = ctx.target_section.get("tier_entry_log", [])
    tail = log[-100:]
    for i, row in enumerate(tail):
        ctx.findings.extend(_check_tier_entry_log_row(ctx, row, i))

    signoff_path = ctx.project_root / "reviews" / "ph3_convergence_signoff.md"
    text = _read_text_or_none(signoff_path)
    if text:
        rows = _parse_t3_signoff_rows(text)
        for i, row in enumerate(rows):
            ctx.findings.extend(_check_signoff_row(ctx, row, i))


# ----------------------------------------------------------------- entry point


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Mandatory pre-flight guardrail before any section phase advance. "
            "Runs the seven-clause check from PHASE_PROTOCOL.md §7.3."
        ),
    )
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--section", type=str, required=True)
    parser.add_argument(
        "--target-tier",
        "--target-phase",
        dest="target_tier",
        type=str,
        required=True,
        choices=TIER_ENUM_TARGET + ("Ph1", "Ph2", "Ph3", "Ph4"),
    )
    parser.add_argument(
        "--t3-staleness-budget-days",
        type=int,
        default=DEFAULT_T3_STALENESS_BUDGET_DAYS,
    )
    parser.add_argument("--strict-clause-f", action="store_true")
    parser.add_argument(
        "--terminal-close",
        action="store_true",
        help="validate the Ph4 terminal-close boundary (M5 + G.4) instead of Ph4 admission",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    target_phase = args.target_tier.replace("T", "Ph", 1)
    if args.terminal_close and target_phase != "Ph4":
        parser.error("--terminal-close is legal only with --target-phase Ph4 (or T4)")

    # Normalize phase-named targets to the stable T-coded internal API.
    args.target_tier = {"Ph1": "T1", "Ph2": "T2", "Ph3": "T3", "Ph4": "T4"}.get(
        args.target_tier, args.target_tier
    )

    args.project_root = args.project_root.resolve()
    if not args.project_root.is_dir():
        sys.stderr.write(
            f"[pre_phase_advance_check] error: --project-root {args.project_root} "
            "is not a directory.\n"
        )
        return 2

    phase_path = args.project_root / "reviews" / "phase_state.json"
    try:
        phase_document = json.loads(phase_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"[pre_phase_advance_check] error: failed to read {phase_path}: {exc}\n")
        return 2
    milestone_gate = check_milestone_gate(
        args.project_root, phase_document, target_phase, args.terminal_close
    )
    if milestone_gate.findings:
        if args.json:
            print(json.dumps({
                "target_phase": target_phase,
                "milestone_outcomes": milestone_gate.outcomes,
                "errors": [finding.json_value() for finding in milestone_gate.findings],
                "warnings": [],
            }, indent=2))
        else:
            for milestone, outcome in milestone_gate.outcomes.items():
                sys.stderr.write(f"[pre_phase_advance_check] milestone {milestone}: {outcome}\n")
            for finding in milestone_gate.findings:
                sys.stderr.write(f"[pre_phase_advance_check] [ERROR] ({finding.code}, milestone, {finding.path}) {finding.message}\n")
        return 1
    if not args.json:
        for milestone, outcome in milestone_gate.outcomes.items():
            sys.stdout.write(f"[pre_phase_advance_check] milestone {milestone}: {outcome}\n")
    if args.terminal_close:
        if args.json:
            print(json.dumps({
                "target_phase": target_phase,
                "boundary": "ph4_terminal_close",
                "milestone_outcomes": milestone_gate.outcomes,
                "errors": [],
                "warnings": [],
            }, indent=2))
        return 0

    ledger, section = load_ledger(args)

    ctx = CheckContext(
        project_root=args.project_root,
        target_tier=args.target_tier,
        target_section_key=_heading_key(section.get("heading_path", [])),
        target_section=section,
        ledger=ledger,
        t3_staleness_budget_days=args.t3_staleness_budget_days,
        strict_clause_f=args.strict_clause_f,
    )

    check_clause_a(ctx)
    check_clause_b(ctx)
    check_clause_c(ctx)
    check_clause_d(ctx)
    # check_clause_e — RETIRED at v0.11.0 (i* SD/SR Cold-Start defence)
    check_clause_f(ctx)
    check_clause_g(ctx)

    # v0.10.0 S2 — non-blocking advisory on references_initialized at Ph1->Ph2
    # advance. Per architecture §6.3 row 6 of the §6.0 coupling checklist; does
    # NOT cause clause failure (does not append to ctx.findings as an error);
    # surfaces as a stderr advisory line for user awareness. Step 0.5 of
    # run-phase-2 re-emits W-SNOWBALL-PRECONDITION-UNMET as the user-visible
    # signal at Ph2 entry; this script's role is to surface it pre-advance.
    advisory_msg = references_initialized_advisory(section, ctx.target_tier)
    if advisory_msg:
        sys.stderr.write(advisory_msg + "\n")

    # Emit findings. Warnings (codes beginning with W-) do not affect exit code.
    errors = [f for f in ctx.findings if not f.code.startswith("W-")]
    warnings = [f for f in ctx.findings if f.code.startswith("W-")]

    if args.json:
        print(
            json.dumps(
                {
                    "target_tier": ctx.target_tier,
                    "target_section": ctx.target_section_key,
                    "errors": [f.as_dict() for f in errors],
                    "warnings": [f.as_dict() for f in warnings],
                },
                indent=2,
            )
        )
    else:
        for f in errors:
            sys.stderr.write(
                f"[pre_phase_advance_check] [ERROR] ({f.code}, clause {f.clause}, {f.section}) {f.message}\n"
            )
        for f in warnings:
            sys.stdout.write(
                f"[pre_phase_advance_check] [WARN] ({f.code}, clause {f.clause}, {f.section}) {f.message}\n"
            )
        if not errors and not warnings:
            sys.stdout.write(
                f"[pre_phase_advance_check] all seven clauses pass for "
                f"section {ctx.target_section_key} → {ctx.target_tier}.\n"
            )

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
