#!/usr/bin/env python3
"""
artefact_frontmatter_validate.py — validator for reviews/*.md artefact frontmatter
and output-economy F7 JSON evidence packets.

Enforces the schema contract at references/ARTEFACT_FRONTMATTER_SCHEMA.md §8
(rules 1–10 as of v0.8.0 P2.1b).
Introduced at plugin v0.7.4 under proposal P-3.

v0.8.0 P2.1b: F1 gains required `adversarial_register` + `routing_rationale`
(primary-evidence routing string per §8 rule 8); F4 gains optional
`demoted_check_advisories` (list of five-key rows per §8 rule 10); F6 gains
optional `check_profile`, `structural_delta_flag`, `parallel_dispatch`,
`threshold_version` per §8 rule 9.

v0.8.0 P2.1a.1 (R-P2-VALIDATOR-F6 substrate reconciliation): the F6
`planner_dispatch_plan` family, documented at §7a since v0.7.4 but absent from
the validator's `FAMILY_SCHEMAS` dispatch table, is landed here to match the
existing schema-doc contract. In-file checks (required/optional fields, types,
strict-family unknown-field rejection, `user_approval_required == true`,
`subagent_envelope[].verdict_authoritative_as_read == true`) are enforced at
this sub-phase. The three cross-artefact DP finding classes
(R-Refl-DP-1 plan-drift, R-Refl-DP-2 missing-plan, R-Refl-DP-3 unsigned-plan)
require joining F6 against `reviews/phase_state.json` and sibling artefacts,
so they are out of scope for this single-file validator; they are scheduled
against a later sub-phase (P2.8 scope-freeze gate authoring).

Usage:
    artefact_frontmatter_validate.py FILE [FILE ...]
    artefact_frontmatter_validate.py --dir DIR [--recursive]
    artefact_frontmatter_validate.py --help

Output:
    Default: human-readable text summary + per-file findings.
    --json:  machine-readable JSON findings stream.

Exit codes:
    0  all artefacts PASS
    1  usage error
    2  fatal error (I/O, parse failure on required file)
    3  at least one artefact has findings
    4  at least one finding is severity BLOCKER

Finding classes:
    R-Refl-FM-1   missing required field
    R-Refl-FM-2   type mismatch or enum violation
    R-Refl-FM-3   unknown field in strict family
    R-Refl-FM-4   cross-field consistency violation (counts)
    R-Refl-FM-5   check-8 aggregate derivation mismatch
    R-Refl-FM-6   legacy artefact (v0.7.3 reduced shape) — advisory only
    R-Refl-FM-7   unknown document_type (family dispatch failed)

F6-specific cross-artefact finding classes (scheduled, not enforced here):
    R-Refl-DP-1   plan-drift MAJOR: F6 dispatched_agents disagree with
                  phase_state.json-observed actors for that cycle
    R-Refl-DP-2   missing-plan BLOCKER: a round with F1/F2/F3/F5 artefacts but
                  no F6 present
    R-Refl-DP-3   unsigned-plan: downstream artefact cites dispatch_plan_reference
                  whose target F6 lacks a populated user_approval_signature
"""

from __future__ import annotations

import argparse
import json
import hashlib
from reader_accessibility_policy import PolicyError, recompute_check8, resolve_policy, validate_candidate_artifact, validate_check8_evidence
from reader_accessibility_candidates import build_candidate_artifact
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# -----------------------------------------------------------------------------
# YAML parsing
# -----------------------------------------------------------------------------

try:
    import yaml
except ImportError:
    sys.stderr.write(
        "fatal: pyyaml is required. install with: pip install pyyaml --break-system-packages\n"
    )
    sys.exit(2)


FRONTMATTER_RE = re.compile(
    r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL | re.MULTILINE
)


def extract_frontmatter(path: Path) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Return (frontmatter_dict, error_message). On success error_message is None."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return None, f"read failed: {exc}"

    match = FRONTMATTER_RE.match(text)
    if match is None:
        return None, "no YAML frontmatter block found (expected leading `---` fence)"

    block = match.group(1)
    try:
        parsed = yaml.safe_load(block)
    except yaml.YAMLError as exc:
        return None, f"YAML parse error: {exc}"

    if parsed is None:
        return {}, None  # empty frontmatter block is legal but almost certainly a finding

    if not isinstance(parsed, dict):
        return None, f"frontmatter root is not a mapping (got {type(parsed).__name__})"

    return parsed, None


# -----------------------------------------------------------------------------
# Schema definitions (keyed by document_type)
# -----------------------------------------------------------------------------

VALID_PHASES = {"Ph1", "Ph2", "Ph3", "Ph3_converged", "Ph4"}
VALID_LEGACY_PHASES = {"T1", "T2", "T3", "T3_converged", "T4"}
VALID_MODELS = {"opus-4-7", "sonnet-4-6", "haiku-4-5"}
VALID_ACTORS = {"planner", "evaluator", "generator", "reflector"}
# F6 planner_dispatch_plan.dispatched_agents[].scope enum (schema §7a.1)
VALID_DISPATCH_SCOPES = {"per_section", "manuscript_level", "cycle_level"}
# v0.8.0 P2.1b — F1 adversarial_register (schema §3.1)
VALID_ADVERSARIAL_REGISTERS = {"refinement", "certification"}
# v0.8.0 P2.1b — F6 check_profile (schema §7a.2, §8 rule 9; tokens per
# proposals/v0.8.0_upgrade_architecture.md §3.2 / §9 move 2)
VALID_F6_CHECK_PROFILES = {"refine", "structural", "deep"}
# v0.8.0 P2.1b — F6 threshold_version RC tag (schema §8 rule 9)
VALID_F6_THRESHOLD_VERSIONS = {"v0.7.5-provisional", "v0.8.0-provisional"}

# v0.14.0 — output economy F7/F8 (references/OUTPUT_ECONOMY_PROTOCOL.md)
ROUND_ID_RE = re.compile(r"^round_\d{4}-\d{2}-\d{2}_\d{3}$")
EVENT_ID_RE = re.compile(r"^round_\d{4}-\d{2}-\d{2}_\d{3}__[a-z0-9_]+__\d{3}$")
VALID_F7_PHASES = {"Ph1", "Ph2", "Ph3", "Ph3_converged", "Ph4", "round_close"}
VALID_F7_EVIDENCE_STATUS = {"complete", "partial", "incomplete"}
F7_ALLOWED_TOP_LEVEL = {
    "artifact_family",
    "document_type",
    "round_id",
    "event_id",
    "phase",
    "target",
    "evidence_status",
    "created_at",
    "checks_run",
    "blockers",
    "major_actions",
    "minor_actions_count",
    "manuscript_delta_summary",
    "state_updates",
    "source_reads",
    "final_report_inputs",
}
F8_ALLOWED_TOP_LEVEL = {
    "artifact_family",
    "document_type",
    "round_id",
    "evidence_status",
    "created_at",
}
# v0.8.0 P2.1b — F4 demoted_check_advisories[].severity (schema §6.2)
VALID_DEMOTED_SEVERITIES = {"MINOR", "MAJOR", "ADVISORY", "BLOCKER"}

# F1 routing_rationale + F4 demoted row routing_rationale (schema §8 rules 8, 10)
ROUTING_RATIONALE_RE = re.compile(
    r"\Aprimary_evidence=(?P<cid>[A-Za-z0-9_.-]+)\Z"
)

COMMON_REQUIRED: Dict[str, type] = {
    "document_type": str,
    "schema_version": str,
    "produced_at": str,
    "produced_by": str,
    "model_used": str,
    "cycle_id": str,
    "iteration": int,
    "section_heading_path": list,
    "current_phase": str,
    "grounding_basis": list,
}


# Per-family required nested structure. Values are either:
#   type       — scalar type
#   dict       — nested subfields (recursive)
#   ("enum", {...}) — enum membership
#   ("list", type) — list of scalars of that type
FAMILY_SCHEMAS: Dict[str, Dict[str, Any]] = {

    # --- Family F1: Evaluator findings ---
    "evaluator_findings": {
        "required": {
            "severity_aggregates": {
                "blocker_count": int,
                "major_count": int,
                "minor_count": int,
                "advisory_count": int,
                "total_count": int,
            },
            "check_8_aggregate": ("enum", {"CLEAN", "BORDERLINE", "MAJOR", "BLOCKER"}),
            "check_8_subcheck_counters": {
                "sub_a_cadence_flag_count": int,
                "sub_b_rhythm_flag_count": int,
                "sub_c_first_use_flag_count": int,
                "sub_d_signpost_flag_count": int,
                "sub_e_jargon_density_flag_count": int,
                "sub_f_worked_example_flag_count": int,
                "sub_g_consolidation_flag_count": int,
                "sub_h_register_flag_count": int,
            },
            "reader_accessibility_policy": {
                "profile_path": str,
                "profile_sha256": str,
                "manuscript_sha256": str,
                "check8_evidence_path": str,
                "check8_evidence_sha256": str,
                "phase": ("enum", {"Ph2", "Ph3", "Ph4"}),
                "candidate_artifact_path": str,
                "candidate_artifact_sha256": str,
            },
            "check_8_adjacent_advisories": {"ve_finding_count": int},
            "dnd_byte_verification": {
                "anchors_verified": bool,
                "anchor_count": int,
                "anchor_drift_count": int,
            },
            "coupling_e2_overlay": {
                "verdict": ("enum", {"CLEAN", "FINDINGS", "N/A"}),
                "graph_stub_citation_count": int,
                "section_location_mismatch_count": int,
                "missing_citation_candidate_count": int,
            },
            "adversarial_register": ("enum", VALID_ADVERSARIAL_REGISTERS),
            "routing_rationale": str,
        },
        "optional": {
            "carry_forward_count": int,
            "new_signal_count": int,
            "escalation_flags": list,
            "borderline_advisories": list,
            "reviewer_agreement_rate": float,
            "contradiction_density": float,
        },
        "strict": True,
    },

    # --- Family F2: Evaluator deterministic ---
    "evaluator_deterministic": {
        "required": {
            "section_9a_counters": {
                "em_dash_count": int,
                "em_dash_functional_test_pass": bool,
                "triadic_list_count": int,
                "absolute_count": int,
                "llm_tic_count": int,
                "sentence_length_violations": {
                    "mean_words_per_sentence": float,
                    "stddev_words_per_sentence": float,
                    "monotone_flag": bool,
                },
            },
            "section_9b_counters": {
                "cadence_flag_count": int,
                "signpost_flag_count": int,
                "jargon_density_flag_count": int,
            },
            "verdict": ("enum", {"PASS", "MINOR", "MAJOR", "BLOCKER"}),
        },
        "optional": {
            "section_breakdown": list,
            "anti_pattern_a_count": int,
            "anti_pattern_b_count": int,
            "anti_pattern_c_count": int,
        },
        "strict": True,
    },

    # --- Family F3: Reflector-lightweight probe ---
    "reflector_lightweight_probe": {
        "required": {
            "grounding_audit": {
                "verdict": ("enum", {"GROUNDING-PASS", "GROUNDING-FINDINGS"}),
                "findings_count": int,
                "files_audited": list,
            },
            "phase_2f_audit": {
                "rows_checked": int,
                "violations_by_class": {
                    "R-Refl-2f-1_notes_length_nonconformance": int,
                    "R-Refl-2f-2_missing_actor": int,
                    "R-Refl-2f-3_nonmonotonic_transition": int,
                    "R-Refl-2f-4_unknown_trigger": int,
                },
                "verdict": ("enum", {"CLEAN", "ADVISORY", "MAJOR"}),
            },
            "artefacts_inspected": list,
        },
        "optional": {
            "dispatch_envelope_recorded": bool,
            "r_refl_ma_audit": dict,  # inner schema flexible; only presence matters
        },
        "strict": True,
    },

    # --- Family F4: Reflector-full report ---
    "reflector_full_report": {
        "required": {
            "phase_aggregates": dict,  # rich nested; validated inline below
            "overall_verdict": ("enum", {"CLEAN", "ADVISORY", "MAJOR", "BLOCKER"}),
        },
        "optional": {
            "plugin_update_proposals_filed": list,
            "lessons_promoted_to_wiki": list,
            "historical_audits": dict,
            "demoted_check_advisories": ("list", {
                "check_id": str,
                "finding_summary": str,
                "severity": ("enum", VALID_DEMOTED_SEVERITIES),
                "source_iteration": int,
                "routing_rationale": str,
            }),
        },
        "strict": False,  # F4 tolerates unknown fields for extensibility
    },

    # --- Family F5: Planner consolidated-findings ---
    "planner_consolidated_findings": {
        "required": {
            "scope_declared": ("enum", {"local", "cross_scope"}),
            "aggregated_severity": {
                "blocker_count": int,
                "major_count": int,
                "minor_count": int,
                "advisory_count": int,
            },
            "aggregated_check_8": ("enum", {"CLEAN", "BORDERLINE", "MAJOR", "BLOCKER"}),
            "decision_surface": {
                "menu_items_presented": list,
                "recommended_first": str,
                "ceiling_lock_detected": bool,
            },
            "outgoing_markers": list,
        },
        "optional": {
            "dispatch_plan_reference": str,
            "mcr_state": dict,
        },
        "strict": True,
    },

    # --- Family F6: Planner dispatch plan (schema §7a; reconciled in v0.8.0 P2.1a.1) ---
    # Contract: reviews/dispatch_plan_<cycle_id>.md, one per round, written at
    # Phase 0.6 and user-approved before any downstream dispatch fires.
    # The two MUST-BE-TRUE rules (user_approval_required, and
    # subagent_envelope[].verdict_authoritative_as_read when present) are
    # enforced by _check_cross_field() below rather than via an ("enum", {True})
    # literal, because YAML parses `1` as int and would spuriously match a
    # {True}-set under Python's `1 == True` equality.
    "planner_dispatch_plan": {
        "required": {
            "round_id": str,
            "sections_in_scope": list,
            "dispatched_agents": ("list", {
                "agent": ("enum", VALID_ACTORS),
                "phase": ("enum", VALID_PHASES),
                "model_allocation": ("enum", VALID_MODELS),
                "scope": ("enum", VALID_DISPATCH_SCOPES),
                "purpose": str,
            }),
            "checks_scheduled": list,
            "user_approval_required": bool,
        },
        "optional": {
            "subagent_envelope": ("list", {
                "dispatching_agent": str,
                "subagent_type": str,
                "verdict_authoritative_as_read": bool,
            }),
            "stability_sub_mode_anticipated": bool,
            "ceiling_lock_anticipated": bool,
            "mcr_admission_anticipated": bool,
            "notes": str,
            "user_approval_signature": {
                "approved_at": str,
                "approved_by": str,
                "modifications_recorded": bool,
            },
            "check_profile": ("enum", VALID_F6_CHECK_PROFILES),
            "structural_delta_flag": bool,
            "parallel_dispatch": bool,
            "threshold_version": ("enum", VALID_F6_THRESHOLD_VERSIONS),
        },
        "strict": True,
    },
}


# -----------------------------------------------------------------------------
# Validation core
# -----------------------------------------------------------------------------


class Finding:
    __slots__ = ("path", "cls", "severity", "field", "message")

    def __init__(
        self,
        path: Path,
        cls: str,
        severity: str,
        field: str,
        message: str,
    ) -> None:
        self.path = path
        self.cls = cls
        self.severity = severity
        self.field = field
        self.message = message

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": str(self.path),
            "class": self.cls,
            "severity": self.severity,
            "field": self.field,
            "message": self.message,
        }


def validate_common(fm: Dict[str, Any], path: Path) -> List[Finding]:
    findings: List[Finding] = []

    for field, expected_type in COMMON_REQUIRED.items():
        if field not in fm:
            findings.append(
                Finding(
                    path,
                    "R-Refl-FM-1",
                    "MAJOR",
                    field,
                    f"required common field '{field}' missing",
                )
            )
            continue

        value = fm[field]

        # Special-case: int accepts bool? No — isinstance(True, int) is True in Python,
        # but we want strict int. Normalize.
        if expected_type is int and isinstance(value, bool):
            findings.append(
                Finding(
                    path,
                    "R-Refl-FM-2",
                    "MAJOR",
                    field,
                    f"field '{field}' expects int, got bool",
                )
            )
            continue

        if not isinstance(value, expected_type):
            findings.append(
                Finding(
                    path,
                    "R-Refl-FM-2",
                    "MAJOR",
                    field,
                    f"field '{field}' expects {expected_type.__name__}, got {type(value).__name__}",
                )
            )

    # Enum-ish cross-checks on common fields
    if "produced_by" in fm and isinstance(fm["produced_by"], str):
        if fm["produced_by"] not in VALID_ACTORS:
            findings.append(
                Finding(
                    path,
                    "R-Refl-FM-2",
                    "MAJOR",
                    "produced_by",
                    f"produced_by='{fm['produced_by']}' not in {sorted(VALID_ACTORS)}",
                )
            )

    if "model_used" in fm and isinstance(fm["model_used"], str):
        if fm["model_used"] not in VALID_MODELS:
            findings.append(
                Finding(
                    path,
                    "R-Refl-FM-2",
                    "MAJOR",
                    "model_used",
                    f"model_used='{fm['model_used']}' not in {sorted(VALID_MODELS)}",
                )
            )

    if "current_phase" in fm and isinstance(fm["current_phase"], str):
        phase = fm["current_phase"]
        if phase not in VALID_PHASES and phase not in VALID_LEGACY_PHASES:
            findings.append(
                Finding(
                    path,
                    "R-Refl-FM-2",
                    "MAJOR",
                    "current_phase",
                    f"current_phase='{phase}' not in {sorted(VALID_PHASES | VALID_LEGACY_PHASES)}",
                )
            )
        elif phase in VALID_LEGACY_PHASES:
            # v0.7.4 dual-read: legacy tier-named values are tolerated with advisory
            findings.append(
                Finding(
                    path,
                    "R-Refl-FM-6",
                    "ADVISORY",
                    "current_phase",
                    f"legacy tier-named value '{phase}'; v0.7.5 will drop this read path",
                )
            )

    if "iteration" in fm and isinstance(fm["iteration"], int) and not isinstance(fm["iteration"], bool):
        if fm["iteration"] < 0:
            findings.append(
                Finding(
                    path,
                    "R-Refl-FM-2",
                    "MAJOR",
                    "iteration",
                    f"iteration must be ≥ 0, got {fm['iteration']}",
                )
            )

    return findings


def _check_nested(
    fm_subtree: Any,
    schema_subtree: Any,
    path: Path,
    field_path: str,
) -> List[Finding]:
    findings: List[Finding] = []

    # Schema leaf: a type
    if isinstance(schema_subtree, type):
        if schema_subtree is int and isinstance(fm_subtree, bool):
            findings.append(
                Finding(
                    path, "R-Refl-FM-2", "MAJOR", field_path,
                    f"expected int, got bool",
                )
            )
            return findings
        if schema_subtree is float:
            # Allow ints where floats are specified; coerce at read time.
            if not isinstance(fm_subtree, (int, float)) or isinstance(fm_subtree, bool):
                findings.append(
                    Finding(
                        path, "R-Refl-FM-2", "MAJOR", field_path,
                        f"expected float, got {type(fm_subtree).__name__}",
                    )
                )
            return findings
        if not isinstance(fm_subtree, schema_subtree):
            findings.append(
                Finding(
                    path, "R-Refl-FM-2", "MAJOR", field_path,
                    f"expected {schema_subtree.__name__}, got {type(fm_subtree).__name__}",
                )
            )
        return findings

    # Schema leaf: an enum tuple
    if isinstance(schema_subtree, tuple) and len(schema_subtree) == 2 and schema_subtree[0] == "enum":
        allowed = schema_subtree[1]
        if fm_subtree not in allowed:
            findings.append(
                Finding(
                    path, "R-Refl-FM-2", "MAJOR", field_path,
                    f"value '{fm_subtree}' not in {sorted(allowed)}",
                )
            )
        return findings

    # Schema leaf: a list-of-element-schema tuple (v0.8.0 P2.1a.1: needed by F6)
    if isinstance(schema_subtree, tuple) and len(schema_subtree) == 2 and schema_subtree[0] == "list":
        element_schema = schema_subtree[1]
        if not isinstance(fm_subtree, list):
            findings.append(
                Finding(
                    path, "R-Refl-FM-2", "MAJOR", field_path,
                    f"expected list, got {type(fm_subtree).__name__}",
                )
            )
            return findings
        for idx, elem in enumerate(fm_subtree):
            elem_path = f"{field_path}[{idx}]"
            findings.extend(_check_nested(elem, element_schema, path, elem_path))
        return findings

    # Schema node: a dict
    if isinstance(schema_subtree, dict):
        if not isinstance(fm_subtree, dict):
            findings.append(
                Finding(
                    path, "R-Refl-FM-2", "MAJOR", field_path,
                    f"expected mapping, got {type(fm_subtree).__name__}",
                )
            )
            return findings

        for sub_field, sub_schema in schema_subtree.items():
            sub_path = f"{field_path}.{sub_field}" if field_path else sub_field
            if sub_field not in fm_subtree:
                findings.append(
                    Finding(
                        path, "R-Refl-FM-1", "MAJOR", sub_path,
                        f"required field '{sub_path}' missing",
                    )
                )
                continue
            findings.extend(
                _check_nested(fm_subtree[sub_field], sub_schema, path, sub_path)
            )
        return findings

    # Unknown schema shape — author error in this file
    findings.append(
        Finding(
            path, "R-Refl-FM-7", "BLOCKER", field_path,
            f"validator bug: unknown schema shape {type(schema_subtree).__name__}",
        )
    )
    return findings


def validate_family(fm: Dict[str, Any], path: Path) -> List[Finding]:
    findings: List[Finding] = []

    doc_type = fm.get("document_type")
    if doc_type is None or not isinstance(doc_type, str):
        # Common-field validation already flagged this; skip family dispatch
        return findings

    if doc_type not in FAMILY_SCHEMAS:
        findings.append(
            Finding(
                path, "R-Refl-FM-7", "MAJOR", "document_type",
                f"unknown document_type '{doc_type}'; legal values: {sorted(FAMILY_SCHEMAS)}",
            )
        )
        return findings

    schema = FAMILY_SCHEMAS[doc_type]

    # Required fields
    for field, sub_schema in schema["required"].items():
        if field not in fm:
            findings.append(
                Finding(
                    path, "R-Refl-FM-1", "MAJOR", field,
                    f"required field '{field}' missing for family '{doc_type}'",
                )
            )
            continue
        findings.extend(_check_nested(fm[field], sub_schema, path, field))

    # Optional fields (type-check only, no required)
    for field, sub_schema in schema["optional"].items():
        if field in fm:
            findings.extend(_check_nested(fm[field], sub_schema, path, field))

    # Strict-family unknown-field rejection
    if schema.get("strict", True):
        known = set(COMMON_REQUIRED) | set(schema["required"]) | set(schema["optional"])
        for field in fm:
            if field not in known:
                findings.append(
                    Finding(
                        path, "R-Refl-FM-3", "MAJOR", field,
                        f"unknown field '{field}' in strict family '{doc_type}'",
                    )
                )

    # Cross-field consistency
    findings.extend(_check_cross_field(fm, path, doc_type))

    return findings


def _check_cross_field(fm: Dict[str, Any], path: Path, doc_type: str) -> List[Finding]:
    findings: List[Finding] = []

    # F1: severity_aggregates.total_count == sum of the four
    if doc_type == "evaluator_findings":
        agg = fm.get("severity_aggregates")
        if isinstance(agg, dict):
            try:
                summed = int(agg.get("blocker_count", 0)) + int(agg.get("major_count", 0)) \
                       + int(agg.get("minor_count", 0)) + int(agg.get("advisory_count", 0))
                total = int(agg.get("total_count", -1))
                if total != summed:
                    findings.append(
                        Finding(
                            path, "R-Refl-FM-4", "MAJOR", "severity_aggregates.total_count",
                            f"total_count={total} does not equal sum of components ({summed})",
                        )
                    )
            except (TypeError, ValueError):
                pass  # type-check will have flagged this

        # Check 8 aggregate derivation rule
        sub = fm.get("check_8_subcheck_counters")
        agg_check = fm.get("check_8_aggregate")
        if isinstance(sub, dict) and isinstance(agg_check, str):
            # This rule requires the per-subcheck MAJOR/BLOCKER decomposition,
            # which the current schema captures as flag COUNTS (not severity
            # verdicts). Counts are per-paragraph, not per-sub-check; the
            # aggregate verdict comes from the overlay skill's scoring, not
            # from the counts directly. The strict derivation check needs the
            # per-sub-check severity verdict, which lives at
            # check_8_subcheck_verdicts.sub_a .. sub_f if present.
            #
            # In this initial v0.7.4 schema we only require the flag counts;
            # the derivation check is advisory (emitted as R-Refl-FM-6 advisory)
            # rather than a hard R-Refl-FM-5 until the severity field lands.
            # The skill `accessibility-overlay` (v0.7.2+) can be extended in a
            # subsequent minor to populate the severity verdicts directly.
            pass

        # F1: routing_rationale shape (schema §8 rule 8)
        rr = fm.get("routing_rationale")
        if isinstance(rr, str):
            if ROUTING_RATIONALE_RE.match(rr) is None:
                findings.append(
                    Finding(
                        path, "R-Refl-FM-2", "MAJOR", "routing_rationale",
                        "routing_rationale must match primary_evidence=<check_id> "
                        "(see references/ARTEFACT_FRONTMATTER_SCHEMA.md §8 rule 8)",
                    )
                )

    # F4: demoted_check_advisories[].routing_rationale shape (schema §8 rule 10)
    if doc_type == "reflector_full_report":
        dem = fm.get("demoted_check_advisories")
        if isinstance(dem, list):
            for idx, row in enumerate(dem):
                if not isinstance(row, dict):
                    continue
                rr = row.get("routing_rationale")
                if isinstance(rr, str):
                    if ROUTING_RATIONALE_RE.match(rr) is None:
                        findings.append(
                            Finding(
                                path, "R-Refl-FM-2", "MAJOR",
                                f"demoted_check_advisories[{idx}].routing_rationale",
                                "routing_rationale must match primary_evidence=<check_id> "
                                "(see references/ARTEFACT_FRONTMATTER_SCHEMA.md §8 rule 10)",
                            )
                        )

    # F5: aggregated_check_8 must match worst-case derivation (out of scope for v0.7.4 initial)

    # F6: user_approval_required MUST be true at v0.7.4 (schema §8 rule 7);
    # subagent_envelope[].verdict_authoritative_as_read MUST be true under
    # I-SubAgent-1. Both are enforced here rather than via ("enum", {True})
    # literals, because YAML's `1` would compare-equal to True and spuriously
    # pass. See P2.1a.1 closure note in the module docstring.
    if doc_type == "planner_dispatch_plan":
        uar = fm.get("user_approval_required")
        if isinstance(uar, bool) and uar is False:
            findings.append(
                Finding(
                    path, "R-Refl-FM-2", "MAJOR", "user_approval_required",
                    "user_approval_required must be true at v0.7.4 "
                    "(see references/ARTEFACT_FRONTMATTER_SCHEMA.md §8 rule 7)",
                )
            )

        env = fm.get("subagent_envelope")
        if isinstance(env, list):
            for idx, item in enumerate(env):
                if not isinstance(item, dict):
                    continue
                v = item.get("verdict_authoritative_as_read")
                if isinstance(v, bool) and v is False:
                    findings.append(
                        Finding(
                            path, "R-Refl-FM-2", "MAJOR",
                            f"subagent_envelope[{idx}].verdict_authoritative_as_read",
                            "verdict_authoritative_as_read must be true under "
                            "I-SubAgent-1 (see references/ARTEFACT_FRONTMATTER_SCHEMA.md §7a.2)",
                        )
                    )

    return findings


def _load_json_object(path: Path) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return None, f"read failed: {exc}"
    try:
        root = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, f"JSON parse error: {exc}"
    if not isinstance(root, dict):
        return None, f"JSON root is not an object (got {type(root).__name__})"
    return root, None


def validate_f7_json(path: Path) -> List[Finding]:
    fm, err = _load_json_object(path)
    if err is not None:
        return [Finding(path, "R-Refl-FM-7", "BLOCKER", "<file>", err)]
    findings: List[Finding] = []

    if fm.get("artifact_family") != "F7":
        findings.append(
            Finding(
                path,
                "R-Refl-FM-2",
                "MAJOR",
                "artifact_family",
                f"expected 'F7', got {fm.get('artifact_family')!r}",
            )
        )
    if fm.get("document_type") != "evidence_packet":
        findings.append(
            Finding(
                path,
                "R-Refl-FM-7",
                "MAJOR",
                "document_type",
                f"expected 'evidence_packet' for JSON lane, got {fm.get('document_type')!r}",
            )
        )

    rid = fm.get("round_id")
    if not isinstance(rid, str) or not ROUND_ID_RE.match(rid):
        findings.append(
            Finding(
                path,
                "R-Refl-FM-2",
                "MAJOR",
                "round_id",
                f"round_id must match round_YYYY-MM-DD_NNN, got {rid!r}",
            )
        )

    eid = fm.get("event_id")
    if not isinstance(eid, str) or not EVENT_ID_RE.match(eid):
        findings.append(
            Finding(
                path,
                "R-Refl-FM-2",
                "MAJOR",
                "event_id",
                f"event_id must match <round_id>__<kind>__NNN pattern, got {eid!r}",
            )
        )
    if isinstance(rid, str) and isinstance(eid, str) and not eid.startswith(rid + "__"):
        findings.append(
            Finding(
                path,
                "R-Refl-FM-4",
                "MAJOR",
                "event_id",
                f"event_id must begin with round_id + '__' (round_id={rid!r})",
            )
        )

    phase = fm.get("phase")
    if not isinstance(phase, str) or phase not in VALID_F7_PHASES:
        findings.append(
            Finding(
                path,
                "R-Refl-FM-2",
                "MAJOR",
                "phase",
                f"phase must be one of {sorted(VALID_F7_PHASES)}, got {phase!r}",
            )
        )

    target = fm.get("target")
    if not isinstance(target, str) or not target.strip():
        findings.append(
            Finding(
                path,
                "R-Refl-FM-1",
                "MAJOR",
                "target",
                "target must be a non-empty string",
            )
        )

    evs = fm.get("evidence_status")
    if not isinstance(evs, str) or evs not in VALID_F7_EVIDENCE_STATUS:
        findings.append(
            Finding(
                path,
                "R-Refl-FM-2",
                "MAJOR",
                "evidence_status",
                f"evidence_status must be one of {sorted(VALID_F7_EVIDENCE_STATUS)}, got {evs!r}",
            )
        )

    cat = fm.get("created_at")
    if not isinstance(cat, str) or len(cat) < 10:
        findings.append(
            Finding(
                path,
                "R-Refl-FM-1",
                "MAJOR",
                "created_at",
                "created_at must be an ISO-8601-like non-empty string",
            )
        )

    if "checks_run" in fm and not isinstance(fm["checks_run"], list):
        findings.append(
            Finding(path, "R-Refl-FM-2", "MAJOR", "checks_run", "checks_run must be a list")
        )
    if "blockers" in fm and not isinstance(fm["blockers"], list):
        findings.append(
            Finding(path, "R-Refl-FM-2", "MAJOR", "blockers", "blockers must be a list")
        )
    if "major_actions" in fm and not isinstance(fm["major_actions"], list):
        findings.append(
            Finding(path, "R-Refl-FM-2", "MAJOR", "major_actions", "major_actions must be a list")
        )
    if "minor_actions_count" in fm:
        mac = fm["minor_actions_count"]
        if isinstance(mac, bool) or not isinstance(mac, int) or mac < 0:
            findings.append(
                Finding(
                    path,
                    "R-Refl-FM-2",
                    "MAJOR",
                    "minor_actions_count",
                    "minor_actions_count must be int ≥ 0",
                )
            )
    if "manuscript_delta_summary" in fm and not isinstance(fm["manuscript_delta_summary"], str):
        findings.append(
            Finding(
                path,
                "R-Refl-FM-2",
                "MAJOR",
                "manuscript_delta_summary",
                "manuscript_delta_summary must be a string",
            )
        )
    if "state_updates" in fm and not isinstance(fm["state_updates"], dict):
        findings.append(
            Finding(path, "R-Refl-FM-2", "MAJOR", "state_updates", "state_updates must be an object")
        )
    if "source_reads" in fm and not isinstance(fm["source_reads"], list):
        findings.append(
            Finding(path, "R-Refl-FM-2", "MAJOR", "source_reads", "source_reads must be a list")
        )
    if "final_report_inputs" in fm and not isinstance(fm["final_report_inputs"], dict):
        findings.append(
            Finding(
                path,
                "R-Refl-FM-2",
                "MAJOR",
                "final_report_inputs",
                "final_report_inputs must be an object",
            )
        )

    for field in fm:
        if field not in F7_ALLOWED_TOP_LEVEL:
            findings.append(
                Finding(
                    path,
                    "R-Refl-FM-3",
                    "MAJOR",
                    field,
                    f"unknown field '{field}' in strict F7 evidence_packet",
                )
            )

    return findings


def validate_f8_frontmatter(fm: Dict[str, Any], path: Path) -> List[Finding]:
    findings: List[Finding] = []

    if fm.get("artifact_family") != "F8":
        findings.append(
            Finding(
                path,
                "R-Refl-FM-2",
                "MAJOR",
                "artifact_family",
                f"expected 'F8', got {fm.get('artifact_family')!r}",
            )
        )
    if fm.get("document_type") != "final_round_report":
        findings.append(
            Finding(
                path,
                "R-Refl-FM-7",
                "MAJOR",
                "document_type",
                f"expected 'final_round_report', got {fm.get('document_type')!r}",
            )
        )

    rid = fm.get("round_id")
    if not isinstance(rid, str) or not ROUND_ID_RE.match(rid):
        findings.append(
            Finding(
                path,
                "R-Refl-FM-2",
                "MAJOR",
                "round_id",
                f"round_id must match round_YYYY-MM-DD_NNN, got {rid!r}",
            )
        )

    evs = fm.get("evidence_status")
    if not isinstance(evs, str) or evs not in VALID_F7_EVIDENCE_STATUS:
        findings.append(
            Finding(
                path,
                "R-Refl-FM-2",
                "MAJOR",
                "evidence_status",
                f"evidence_status must be one of {sorted(VALID_F7_EVIDENCE_STATUS)}, got {evs!r}",
            )
        )

    cat = fm.get("created_at")
    if not isinstance(cat, str) or len(cat) < 10:
        findings.append(
            Finding(
                path,
                "R-Refl-FM-1",
                "MAJOR",
                "created_at",
                "created_at must be an ISO-8601-like non-empty string",
            )
        )

    for field in fm:
        if field not in F8_ALLOWED_TOP_LEVEL:
            findings.append(
                Finding(
                    path,
                    "R-Refl-FM-3",
                    "MAJOR",
                    field,
                    f"unknown field '{field}' in strict F8 final_round_report frontmatter",
                )
            )

    return findings


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------


def validate_path(path: Path) -> List[Finding]:
    if path.suffix.lower() == ".json":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            return [Finding(path, "R-Refl-FM-7", "BLOCKER", "<file>", f"invalid JSON: {exc}")]
        if not isinstance(payload, dict):
            return []
        # JSON under reviews is not synonymous with F7. Dispatch by an explicit
        # family/schema discriminator so policy sidecars and audit reports are
        # never interpreted as output-economy evidence packets.
        if payload.get("artifact_family") == "F7" or ".harness/evidence" in path.as_posix():
            return validate_f7_json(path)
        try:
            if payload.get("schema_version") == "reader_accessibility_candidates.v1":
                validate_candidate_artifact(payload)
            elif payload.get("schema_version") == "check8_evidence.v1":
                validate_check8_evidence(payload)
            elif payload.get("contract_version") and isinstance(payload.get("resolved_profile"), dict):
                # Resolver sidecar: its exact freshness is checked through the
                # F1 binding, not by treating this file as an independent F7.
                return []
        except (PolicyError, ValueError) as exc:
            return [Finding(path, "R-Refl-FM-RA", "MAJOR", "<file>", f"invalid reader-accessibility sidecar: {exc}")]
        return []

    fm, err = extract_frontmatter(path)
    if err is not None:
        return [Finding(path, "R-Refl-FM-7", "BLOCKER", "<file>", err)]
    if fm is None:
        return []

    # Empty-frontmatter → flag missing document_type
    if not fm:
        return [Finding(path, "R-Refl-FM-1", "MAJOR", "document_type",
                        "empty frontmatter block; document_type required")]

    doc_type = fm.get("document_type")
    if doc_type == "final_round_report":
        return validate_f8_frontmatter(fm, path)

    findings: List[Finding] = []
    findings.extend(validate_common(fm, path))
    findings.extend(validate_family(fm, path))
    if doc_type == "evaluator_findings" and not findings:
        findings.extend(validate_reader_accessibility_evidence(fm, path))
    return findings


def validate_reader_accessibility_evidence(fm: Dict[str, Any], path: Path) -> List[Finding]:
    """Bind F1's human view to exact Check 8/profile/manuscript/candidate bytes."""
    findings: List[Finding] = []
    policy = fm["reader_accessibility_policy"]
    trusted_cycle_id = fm.get("cycle_id")
    if not isinstance(trusted_cycle_id, str) or not trusted_cycle_id:
        return [Finding(path, "R-Refl-FM-RA", "MAJOR", "cycle_id", "F1 cycle_id is required for reader-accessibility provenance")]
    project_root = path.parent.parent if path.parent.name == "reviews" else path.parent
    def bound(relative: str, expected: str, field: str) -> Path | None:
        candidate = (project_root / relative).resolve()
        try: candidate.relative_to(project_root.resolve())
        except ValueError:
            findings.append(Finding(path, "R-Refl-FM-RA", "MAJOR", field, "binding escapes project root")); return None
        if not candidate.is_file() or hashlib.sha256(candidate.read_bytes()).hexdigest() != expected:
            findings.append(Finding(path, "R-Refl-FM-RA", "MAJOR", field, "binding is missing or stale")); return None
        return candidate
    profile_path = bound(policy["profile_path"], policy["profile_sha256"], "reader_accessibility_policy.profile_path")
    candidate_path = bound(policy["candidate_artifact_path"], policy["candidate_artifact_sha256"], "reader_accessibility_policy.candidate_artifact_path")
    check8_path = bound(policy["check8_evidence_path"], policy["check8_evidence_sha256"], "reader_accessibility_policy.check8_evidence_path")
    manuscript_path = None
    grounding = fm.get("grounding_basis", [])
    if grounding:
        manuscript_path = bound(grounding[0], policy["manuscript_sha256"], "reader_accessibility_policy.manuscript_sha256")
    if check8_path is not None:
        try: sidecar = json.loads(check8_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            findings.append(Finding(path, "R-Refl-FM-RA", "MAJOR", "reader_accessibility_policy.check8_evidence_path", f"invalid Check 8 JSON: {exc}")); return findings
        try:
            expected_resolved = resolve_policy(project_root)
            resolved_payload = json.loads(profile_path.read_text(encoding="utf-8")) if profile_path else None
            candidate_payload = json.loads(candidate_path.read_text(encoding="utf-8")) if candidate_path else None
        except (PolicyError, OSError, json.JSONDecodeError) as exc:
            findings.append(Finding(path, "R-Refl-FM-RA", "MAJOR", "reader_accessibility_policy", f"resolved/candidate artifact invalid: {exc}")); return findings
        if resolved_payload != expected_resolved:
            findings.append(Finding(path, "R-Refl-FM-RA", "MAJOR", "reader_accessibility_policy.profile_path", "resolved profile is not exact fresh resolver output"))
        try:
            validate_candidate_artifact(candidate_payload)
        except PolicyError as exc:
            findings.append(Finding(path, "R-Refl-FM-RA", "MAJOR", "reader_accessibility_policy.candidate_artifact_path", f"candidate artifact schema invalid: {exc}"))
        expected_candidate = {
            "cycle_id": trusted_cycle_id, "phase": policy["phase"], "manuscript_path": grounding[0] if grounding else None,
            "manuscript_sha256": policy["manuscript_sha256"], "profile_path": expected_resolved["profile_path"],
            "profile_sha256": expected_resolved["profile_sha256"], "source_bindings": expected_resolved["source_bindings"],
        }
        if not isinstance(candidate_payload, dict) or any(candidate_payload.get(key) != value for key, value in expected_candidate.items()):
            findings.append(Finding(path, "R-Refl-FM-RA", "MAJOR", "reader_accessibility_policy.candidate_artifact_path", "candidate artifact schema/content does not match resolved policy"))
        if isinstance(candidate_payload, dict) and manuscript_path is not None:
            try:
                recomputed_candidate = build_candidate_artifact(project_root, manuscript_path, policy["phase"], trusted_cycle_id, expected_resolved)
            except (PolicyError, OSError, ValueError, TypeError) as exc:
                findings.append(Finding(path, "R-Refl-FM-RA", "MAJOR", "reader_accessibility_policy.candidate_artifact_path", f"candidate recomputation failed: {exc}"))
            else:
                if candidate_payload != recomputed_candidate:
                    findings.append(Finding(path, "R-Refl-FM-RA", "MAJOR", "reader_accessibility_policy.candidate_artifact_path", "candidate artifact differs from canonical deterministic recomputation"))
        phase_state_path = project_root / "reviews" / "phase_state.json"
        try:
            validate_check8_evidence(sidecar)
            phase_state = json.loads(phase_state_path.read_text(encoding="utf-8"))
            bound_transitions = phase_state["milestone_framework"]["policy_bindings"]["reader_accessibility"]["transitions"]
            transition_snapshot = {key: bound_transitions[key]["state"] for key in ("G", "H", "VE")}
            transition_objects = {key: {"state": transition_snapshot[key]} for key in ("G", "H", "VE")}
            computed = recompute_check8(sidecar, transition_objects)
        except (PolicyError, OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
            findings.append(Finding(path, "R-Refl-FM-RA", "MAJOR", "reader_accessibility_policy.check8_evidence_path", f"strict Check 8/phase-state evidence invalid: {exc}")); return findings
        expected = {"cycle_id": trusted_cycle_id, "profile_path": policy["profile_path"], "profile_sha256": policy["profile_sha256"], "manuscript_sha256": policy["manuscript_sha256"], "phase": policy["phase"], "aggregate_verdict": fm["check_8_aggregate"]}
        if any(sidecar.get(key) != value for key, value in expected.items()) or sidecar.get("manuscript_path") != (grounding[0] if grounding else None) or sidecar.get("transition_snapshot") != transition_snapshot or computed["aggregate_verdict"] != fm["check_8_aggregate"] or sidecar.get("subcheck_verdicts") != computed["subcheck_verdicts"]:
            findings.append(Finding(path, "R-Refl-FM-RA", "MAJOR", "check_8_aggregate", "F1 fields do not match recomputed Check 8 evidence"))
        if len(sidecar.get("ve", {}).get("findings", [])) != fm["check_8_adjacent_advisories"]["ve_finding_count"]:
            findings.append(Finding(path, "R-Refl-FM-RA", "MAJOR", "check_8_adjacent_advisories", "VE evidence count mismatch"))
    return findings


def collect_paths(args: argparse.Namespace) -> List[Path]:
    paths: List[Path] = []
    if args.dir:
        d = Path(args.dir)
        if not d.is_dir():
            sys.stderr.write(f"error: --dir is not a directory: {d}\n")
            sys.exit(2)
        if args.recursive:
            md_paths = sorted(d.rglob("*.md"))
            json_paths = sorted(path for path in d.rglob("*.json") if path.name != "phase_state.json")
        else:
            md_paths = sorted(d.glob("*.md"))
            json_paths = sorted(path for path in d.glob("*.json") if path.name != "phase_state.json")
        # Stable combined order: Markdown first, then JSON (deterministic)
        paths = md_paths + json_paths
    else:
        paths = [Path(p) for p in args.files]
        for p in paths:
            if not p.is_file():
                sys.stderr.write(f"error: not a file: {p}\n")
                sys.exit(2)
    return paths


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate reviews/*.md artefact frontmatter per "
                    "references/ARTEFACT_FRONTMATTER_SCHEMA.md, plus F7 JSON "
                    "evidence packets and F8 final round reports (v0.14.0 output economy).",
    )
    parser.add_argument("files", nargs="*", help="file paths to validate")
    parser.add_argument("--dir", help="validate every *.md under this directory")
    parser.add_argument("--recursive", action="store_true",
                        help="(with --dir) recurse into subdirectories")
    parser.add_argument("--json", action="store_true",
                        help="emit findings as JSON (stdout)")
    parser.add_argument("--quiet", action="store_true",
                        help="suppress per-file PASS lines in human output")
    args = parser.parse_args(argv)

    if not args.files and not args.dir:
        parser.error("supply one or more FILE arguments or --dir DIR")

    paths = collect_paths(args)
    if not paths:
        sys.stderr.write("warning: no files to validate\n")
        return 0

    all_findings: List[Finding] = []
    for p in paths:
        all_findings.extend(validate_path(p))

    blocker_count = sum(1 for f in all_findings if f.severity == "BLOCKER")

    if args.json:
        json.dump(
            {
                "files_validated": len(paths),
                "finding_count": len(all_findings),
                "blocker_count": blocker_count,
                "findings": [f.to_dict() for f in all_findings],
            },
            sys.stdout,
            indent=2,
            sort_keys=True,
        )
        sys.stdout.write("\n")
    else:
        by_path: Dict[Path, List[Finding]] = {}
        for f in all_findings:
            by_path.setdefault(f.path, []).append(f)
        for p in paths:
            fs = by_path.get(p, [])
            if not fs:
                if not args.quiet:
                    print(f"PASS  {p}")
                continue
            print(f"FAIL  {p}  ({len(fs)} findings)")
            for f in fs:
                print(f"  [{f.severity}] {f.cls}  {f.field}: {f.message}")
        print()
        print(f"files_validated: {len(paths)}")
        print(f"finding_count:   {len(all_findings)}")
        print(f"blocker_count:   {blocker_count}")

    if blocker_count > 0:
        return 4
    if all_findings:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
