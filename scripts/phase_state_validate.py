#!/usr/bin/env python3
# phase_state_validate.py
#
# Dual-read validator for reviews/phase_state.json (v0.7.4) and, during the
# v0.7.4 minor, the legacy reviews/tier_state.json (v0.7.3).
#
# Replaces scripts/tier_state_validate.py.  The tier-named read path is
# deprecated at v0.7.4 and will be removed at v0.7.5 RC; during v0.7.4 a dual
# read is supported so that projects migrating at their own cadence are not
# broken.
#
# Validation surface
# ------------------
# For every SectionStateObject (value of the top-level sections map):
#   1. Required top-level fields are present.
#   2. current_phase is one of the legal phase codes.
#   3. phase_entry_log is a non-empty list.
#   4. Every log row matches the v0.7.4 seven-field shape (model_used
#      may be null).
#   5. Legal tier codes at v0.7.4 are {Ph1, Ph2, Ph3, Ph3_converged, Ph4}.
#   6. Phase-ladder monotonicity is enforced along the log:
#           Ph1 <= Ph2 <= Ph3 <= Ph3_converged <= Ph4
#      Three exemptions are recognized; any other downward transition
#      emits MONOTONICITY_VIOLATION.
#   7. v0.8.0 P2.1a (beta-P-9a) soft type-check: if the additive sixteenth
#      field `pre_mcr_deep_pass_completed` is present on a section, it
#      must be a bool; otherwise emit SECTION_BAD_PRE_MCR_DEEP_PASS_TYPE
#      (MINOR).  Absence is tolerated; the MCR admission gate at
#      pre_phase_advance_check.py clause (f) treats absent as false.
#
# Monotonicity exemptions
# -----------------------
#   * retraction                              (human-initiated demotion)
#   * eg1_ph4_downgrade_to_ph3                (T4->T3 grounding demotion,
#                                              renamed from eg1_t4_downgrade_to_t3)
#   * eg7_mcr_readmission_after_class_change  (T4->T3 re-admission after
#                                              classification change)
#
# Dual-read behaviour
# -------------------
#   * If phase_state.json exists: validate at v0.7.4 shape.
#   * Else if tier_state.json exists: emit a DEPRECATION_WARNING finding
#     at severity MINOR, then translate field names in-memory
#     (tier_*  -> phase_*, prev_tier -> prev_phase, etc.) and validate.
#   * If both exist: prefer phase_state.json and emit MIXED_STATE warning.
#
# Legal trigger enum
# ------------------
# The validator does NOT enforce trigger names — that is the Planner's
# responsibility (the authoritative enum lives in TIER_PROTOCOL.md ->
# PHASE_PROTOCOL.md at v0.7.4).  The validator only checks that `trigger`
# is a non-empty string.  Two triggers receive special handling because
# they license downward transitions (see monotonicity exemptions above).
#
# Exit codes
# ----------
#   0  PASS
#   1  usage error
#   2  file I/O or parse error
#   3  validation findings (any severity)
#   4  BLOCKER findings present

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

SUPPORTED_SCHEMA_VERSION = "0.7.4"

# Phase-ladder ordering.  Indices encode the legal progression.
PHASE_ORDER = ["Ph1", "Ph2", "Ph3", "Ph3_converged", "Ph4"]
PHASE_INDEX = {p: i for i, p in enumerate(PHASE_ORDER)}

# Required SectionStateObject top-level fields (v0.7.4 15-field schema).
REQUIRED_SECTION_FIELDS = {
    "current_phase",
    "phase_entry_log",
}

# Required log row fields (v0.7.4 7-field shape).
REQUIRED_LOG_FIELDS = {
    "prev_phase", "new_phase", "trigger", "actor", "notes", "timestamp",
    "model_used",
}

LEGAL_ACTORS = {"planner", "evaluator", "generator", "reflector", "user"}

MONOTONICITY_EXEMPTIONS = {
    "retraction",
    "eg1_ph4_downgrade_to_ph3",
    "eg7_mcr_readmission_after_class_change",
}

# Legacy v0.7.3 field names we translate in-memory when dual-reading.
LEGACY_FIELD_RENAMES_SECTION = {
    "current_tier": "current_phase",
    "tier_goal_declared": "phase_goal_declared",
    "tier_deliverable_path": "phase_deliverable_path",
    "tier_entry_log": "phase_entry_log",
    "t1_pstage_declaration": "ph1_pstage_declaration",
    "t3_last_activity_at": "ph3_last_activity_at",
}
LEGACY_FIELD_RENAMES_LOG = {
    "prev_tier": "prev_phase",
    "new_tier": "new_phase",
}
LEGACY_VALUE_RENAMES = {
    "T1": "Ph1", "T2": "Ph2", "T3": "Ph3", "T4": "Ph4",
    "T3_converged": "Ph3_converged", "T4_ready": "Ph4_ready",
}


class Severity(str, Enum):
    MINOR = "MINOR"
    MAJOR = "MAJOR"
    BLOCKER = "BLOCKER"


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    path: str   # dotted JSON path for a human to locate the violation
    message: str


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _xlate_legacy(doc: dict) -> tuple[dict, list[Finding]]:
    """Translate a v0.7.3-shaped tier_state.json into v0.7.4 shape in memory.
    Returns (translated_doc, findings) where findings carries a DEPRECATION
    notice at severity MINOR."""
    findings: list[Finding] = [
        Finding(
            code="DEPRECATION_WARNING",
            severity=Severity.MINOR,
            path="$",
            message=(
                "Read-through of reviews/tier_state.json under the v0.7.4 "
                "dual-read path; will be removed at v0.7.5 RC.  Run "
                "scripts/migrate_v073_to_v074_tier_to_phase.py to upgrade."
            ),
        )
    ]

    def _xlate_log_row(row: dict) -> dict:
        out = {}
        for k, v in row.items():
            new_key = LEGACY_FIELD_RENAMES_LOG.get(k, k)
            if isinstance(v, str) and v in LEGACY_VALUE_RENAMES:
                v = LEGACY_VALUE_RENAMES[v]
            out[new_key] = v
        if "model_used" not in out:
            out["model_used"] = None
        return out

    def _xlate_section(sec: dict) -> dict:
        out = {}
        for k, v in sec.items():
            new_key = LEGACY_FIELD_RENAMES_SECTION.get(k, k)
            if new_key == "phase_entry_log" and isinstance(v, list):
                out[new_key] = [_xlate_log_row(r) for r in v]
            elif isinstance(v, str) and v in LEGACY_VALUE_RENAMES:
                out[new_key] = LEGACY_VALUE_RENAMES[v]
            else:
                out[new_key] = v
        return out

    out_doc: dict = {}
    if "sections" in doc and isinstance(doc["sections"], dict):
        out_doc = {k: v for k, v in doc.items() if k != "sections"}
        out_doc["sections"] = {
            path: _xlate_section(s) for path, s in doc["sections"].items()
        }
    else:
        for path, sec in doc.items():
            out_doc[path] = _xlate_section(sec) if isinstance(sec, dict) else sec
    return out_doc, findings


def _validate_log_row(
    row: dict, row_path: str, findings: list[Finding]
) -> None:
    if not isinstance(row, dict):
        findings.append(Finding(
            code="LOG_ROW_NOT_OBJECT",
            severity=Severity.BLOCKER,
            path=row_path,
            message=f"log row is not a JSON object: {type(row).__name__}",
        ))
        return

    keys = set(row.keys())
    missing = REQUIRED_LOG_FIELDS - keys
    extra = keys - REQUIRED_LOG_FIELDS
    if missing:
        findings.append(Finding(
            code="LOG_ROW_MISSING_FIELD",
            severity=Severity.BLOCKER,
            path=row_path,
            message=f"missing field(s): {sorted(missing)}  "
                    f"(expected v0.7.4 7-field shape)",
        ))
    if extra:
        findings.append(Finding(
            code="LOG_ROW_UNKNOWN_FIELD",
            severity=Severity.MAJOR,
            path=row_path,
            message=f"unknown field(s): {sorted(extra)}",
        ))

    # Type/value checks on fields that are present.
    if "prev_phase" in row and row["prev_phase"] is not None:
        if row["prev_phase"] not in PHASE_INDEX:
            findings.append(Finding(
                code="LOG_ROW_BAD_PREV_PHASE",
                severity=Severity.MAJOR,
                path=f"{row_path}.prev_phase",
                message=f"not a legal phase code: {row['prev_phase']!r}  "
                        f"(legal: {PHASE_ORDER})",
            ))
    if "new_phase" in row and row["new_phase"] not in PHASE_INDEX:
        findings.append(Finding(
            code="LOG_ROW_BAD_NEW_PHASE",
            severity=Severity.BLOCKER,
            path=f"{row_path}.new_phase",
            message=f"not a legal phase code: {row.get('new_phase')!r}  "
                    f"(legal: {PHASE_ORDER})",
        ))
    if "trigger" in row:
        if not isinstance(row["trigger"], str) or not row["trigger"].strip():
            findings.append(Finding(
                code="LOG_ROW_EMPTY_TRIGGER",
                severity=Severity.MAJOR,
                path=f"{row_path}.trigger",
                message="trigger must be a non-empty string",
            ))
    if "actor" in row:
        if row["actor"] not in LEGAL_ACTORS:
            findings.append(Finding(
                code="LOG_ROW_BAD_ACTOR",
                severity=Severity.MAJOR,
                path=f"{row_path}.actor",
                message=f"actor {row['actor']!r} not in {sorted(LEGAL_ACTORS)}",
            ))
    if "notes" in row:
        if isinstance(row["notes"], str) and len(row["notes"]) > 280:
            findings.append(Finding(
                code="LOG_ROW_NOTES_OVER_280",
                severity=Severity.MINOR,
                path=f"{row_path}.notes",
                message=f"notes length {len(row['notes'])} exceeds 280-char "
                        f"ceiling (truncate with [...])",
            ))
    if "model_used" in row:
        mu = row["model_used"]
        if mu is not None and not isinstance(mu, str):
            findings.append(Finding(
                code="LOG_ROW_BAD_MODEL_USED",
                severity=Severity.MINOR,
                path=f"{row_path}.model_used",
                message=f"model_used must be string or null (got "
                        f"{type(mu).__name__})",
            ))


def _validate_monotonicity(
    log: list[dict], log_path: str, findings: list[Finding]
) -> None:
    for i, row in enumerate(log):
        if not isinstance(row, dict):
            continue
        prev = row.get("prev_phase")
        new = row.get("new_phase")
        trigger = row.get("trigger", "")
        if prev is None:
            continue  # bootstrap row
        if prev not in PHASE_INDEX or new not in PHASE_INDEX:
            continue  # already flagged as bad_phase
        if PHASE_INDEX[new] >= PHASE_INDEX[prev]:
            continue  # non-downward transition is fine
        # Downward transition.  Must be exempt.
        if trigger not in MONOTONICITY_EXEMPTIONS:
            findings.append(Finding(
                code="MONOTONICITY_VIOLATION",
                severity=Severity.BLOCKER,
                path=f"{log_path}[{i}]",
                message=(
                    f"downward transition {prev!r} -> {new!r} is not licensed "
                    f"by trigger {trigger!r}.  Legal downgrade triggers: "
                    f"{sorted(MONOTONICITY_EXEMPTIONS)}"
                ),
            ))


def _validate_section(
    section_path: str, section: dict, findings: list[Finding]
) -> None:
    if not isinstance(section, dict):
        findings.append(Finding(
            code="SECTION_NOT_OBJECT",
            severity=Severity.BLOCKER,
            path=f"sections[{section_path!r}]",
            message=f"not a JSON object: {type(section).__name__}",
        ))
        return

    missing = REQUIRED_SECTION_FIELDS - set(section.keys())
    for m in sorted(missing):
        findings.append(Finding(
            code="SECTION_MISSING_FIELD",
            severity=Severity.BLOCKER,
            path=f"sections[{section_path!r}]",
            message=f"missing required field: {m}",
        ))

    cp = section.get("current_phase")
    if cp is not None and cp not in PHASE_INDEX:
        findings.append(Finding(
            code="SECTION_BAD_CURRENT_PHASE",
            severity=Severity.BLOCKER,
            path=f"sections[{section_path!r}].current_phase",
            message=f"not a legal phase code: {cp!r}  (legal: {PHASE_ORDER})",
        ))

    log = section.get("phase_entry_log")
    if not isinstance(log, list):
        findings.append(Finding(
            code="SECTION_LOG_NOT_LIST",
            severity=Severity.BLOCKER,
            path=f"sections[{section_path!r}].phase_entry_log",
            message=f"phase_entry_log must be a list (got "
                    f"{type(log).__name__})",
        ))
        return
    if not log:
        findings.append(Finding(
            code="SECTION_LOG_EMPTY",
            severity=Severity.MAJOR,
            path=f"sections[{section_path!r}].phase_entry_log",
            message="phase_entry_log is empty; section is unbootstrapped",
        ))
        return

    log_path = f"sections[{section_path!r}].phase_entry_log"
    for i, row in enumerate(log):
        _validate_log_row(row, f"{log_path}[{i}]", findings)

    _validate_monotonicity(log, log_path, findings)

    # current_phase must reconcile with last log row.
    if isinstance(log[-1], dict) and cp is not None:
        last = log[-1].get("new_phase")
        if last is not None and last != cp:
            findings.append(Finding(
                code="SECTION_CURRENT_PHASE_DIVERGENT",
                severity=Severity.MAJOR,
                path=f"sections[{section_path!r}]",
                message=f"current_phase {cp!r} does not match last log row's "
                        f"new_phase {last!r}",
            ))

    # v0.8.0 P2.1a (beta-P-9a): soft type-check on the pre-MCR Ph3-deep
    # safety-net flag.  The field is additive at v0.8.0; a ledger that omits
    # it is shape-valid and treated as false by the MCR admission gate at
    # pre_phase_advance_check.py clause (f).  If present, it must be a bool.
    if "pre_mcr_deep_pass_completed" in section:
        pmdp = section["pre_mcr_deep_pass_completed"]
        if not isinstance(pmdp, bool):
            findings.append(Finding(
                code="SECTION_BAD_PRE_MCR_DEEP_PASS_TYPE",
                severity=Severity.MINOR,
                path=f"sections[{section_path!r}].pre_mcr_deep_pass_completed",
                message=(
                    f"pre_mcr_deep_pass_completed must be a boolean (got "
                    f"{type(pmdp).__name__}); see references/"
                    f"phase_state_schema.md section 2.1"
                ),
            ))


def _validate_doc(doc: dict, findings: list[Finding]) -> None:
    if not isinstance(doc, dict):
        findings.append(Finding(
            code="DOC_NOT_OBJECT",
            severity=Severity.BLOCKER,
            path="$",
            message=f"top-level JSON is not an object: {type(doc).__name__}",
        ))
        return

    sections = doc.get("sections")
    if sections is None:
        # Flat-map layout: top-level keys are section-heading-paths.
        sections = {k: v for k, v in doc.items() if isinstance(v, dict)}
        if not sections:
            findings.append(Finding(
                code="DOC_NO_SECTIONS",
                severity=Severity.MAJOR,
                path="$",
                message="no sections found at top-level or under 'sections' key",
            ))
            return

    if not isinstance(sections, dict):
        findings.append(Finding(
            code="DOC_SECTIONS_NOT_OBJECT",
            severity=Severity.BLOCKER,
            path="sections",
            message=f"sections is not a JSON object: "
                    f"{type(sections).__name__}",
        ))
        return

    for path, section in sections.items():
        _validate_section(path, section, findings)


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


def _render_text(findings: list[Finding]) -> str:
    if not findings:
        return "PASS  (no findings)\n"
    out: list[str] = []
    blockers = [f for f in findings if f.severity == Severity.BLOCKER]
    majors = [f for f in findings if f.severity == Severity.MAJOR]
    minors = [f for f in findings if f.severity == Severity.MINOR]
    out.append(
        f"FINDINGS  (blockers: {len(blockers)}, majors: {len(majors)}, "
        f"minors: {len(minors)})"
    )
    for f in findings:
        out.append(f"  [{f.severity.value}] {f.code}  @ {f.path}")
        out.append(f"           {f.message}")
    return "\n".join(out) + "\n"


def _render_json(findings: list[Finding]) -> str:
    return json.dumps(
        [
            {
                "code": f.code,
                "severity": f.severity.value,
                "path": f.path,
                "message": f.message,
            }
            for f in findings
        ],
        indent=2,
    ) + "\n"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="Validate reviews/phase_state.json (v0.7.4) with "
        "dual-read support for legacy reviews/tier_state.json (v0.7.3).",
    )
    ap.add_argument(
        "--project-root",
        required=True,
        type=Path,
        help="Path to project root (containing reviews/ subdir).",
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="Emit findings as JSON instead of human-readable text.",
    )
    ap.add_argument(
        "--quiet",
        action="store_true",
        help="On PASS, emit nothing to stdout; still return exit 0.",
    )
    args = ap.parse_args(argv)

    project_root: Path = args.project_root
    if not project_root.is_dir():
        sys.stderr.write(
            f"error: --project-root is not a directory: {project_root}\n"
        )
        return 1

    reviews_dir = project_root / "reviews"
    if not reviews_dir.is_dir():
        sys.stderr.write(f"error: reviews/ not found under {project_root}\n")
        return 2

    phase_path = reviews_dir / "phase_state.json"
    tier_path = reviews_dir / "tier_state.json"

    findings: list[Finding] = []
    source_path: Path
    if phase_path.exists() and tier_path.exists():
        findings.append(Finding(
            code="MIXED_STATE",
            severity=Severity.MAJOR,
            path="$",
            message=(
                "both reviews/phase_state.json and reviews/tier_state.json "
                "are present; preferring phase_state.json.  Remove the "
                "legacy file or run the migration to clean up."
            ),
        ))
        source_path = phase_path
    elif phase_path.exists():
        source_path = phase_path
    elif tier_path.exists():
        source_path = tier_path
    else:
        sys.stderr.write(
            f"error: neither phase_state.json nor tier_state.json found "
            f"under {reviews_dir}\n"
        )
        return 2

    try:
        text = source_path.read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"error: read failed on {source_path}: {exc}\n")
        return 2

    try:
        doc = json.loads(text)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"error: JSON parse failed on {source_path}: {exc}\n")
        return 2

    if source_path == tier_path:
        doc, dual_read_findings = _xlate_legacy(doc)
        findings.extend(dual_read_findings)

    _validate_doc(doc, findings)

    # Render.
    if args.json:
        sys.stdout.write(_render_json(findings))
    elif findings:
        sys.stdout.write(_render_text(findings))
    elif not args.quiet:
        sys.stdout.write(_render_text(findings))

    # Exit code.
    if any(f.severity == Severity.BLOCKER for f in findings):
        return 4
    if findings:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
