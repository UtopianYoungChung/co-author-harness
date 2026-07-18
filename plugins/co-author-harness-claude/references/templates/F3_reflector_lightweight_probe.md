---
# =========================================================================
# F3 Reflector-lightweight probe — v0.7.4 P-3 frontmatter contract
# Canonical filename: reviews/reflector_lightweight_<YYYY-MM-DD>_iter<N>.md
# Schema: references/ARTEFACT_FRONTMATTER_SCHEMA.md §5
# Validator: scripts/artefact_frontmatter_validate.py
# Produced by: Reflector in lightweight mode (Phases 1, 2.5, 2.6, 2f, 3 only)
# Dispatch phases: Ph1, Ph2, Ph3 (end-of-round probe; Phase 4 uses F4 instead)
# =========================================================================

document_type: reflector_lightweight_probe
schema_version: "1.0"
produced_at: "2026-04-21T00:00:00Z"
produced_by: reflector
model_used: sonnet-4-6               # lightweight Reflector default; pilot slot for Haiku 4.5 per MODEL_ALLOCATION.md §2 hazard H-MA-2
cycle_id: "TEMPLATE-PLACEHOLDER"
iteration: 0
section_heading_path: []
current_phase: Ph3
grounding_basis: []                  # files the Phase 1 grounding audit read

# -------------------------------------------------------------------------
# Phase 1 — grounding audit (required)
# -------------------------------------------------------------------------
grounding_audit:
  verdict: GROUNDING-PASS            # one of {GROUNDING-PASS, GROUNDING-FINDINGS}
  findings_count: 0                  # number of grounding rule violations detected
  files_audited: []                  # subset of grounding_basis actually read; usually equal

# -------------------------------------------------------------------------
# Phase 2f — tier-row contract audit (required)
# -------------------------------------------------------------------------
phase_2f_audit:
  rows_checked: 0                    # number of phase_entry_log rows examined this probe
  violations_by_class:
    R-Refl-2f-1_notes_length_nonconformance: 0   # notes > 280 chars without [...] truncation marker
    R-Refl-2f-2_missing_actor: 0                 # actor field missing or out of {planner, evaluator, generator, reflector, user}
    R-Refl-2f-3_nonmonotonic_transition: 0       # phase demotion without a monotonicity-exempt trigger
    R-Refl-2f-4_unknown_trigger: 0               # trigger outside the v0.7.4 31-trigger enum
  verdict: CLEAN                     # one of {CLEAN, ADVISORY, MAJOR}

# -------------------------------------------------------------------------
# Artefacts this probe inspected (required)
# -------------------------------------------------------------------------
artefacts_inspected: []              # list of paths (relative to project root); typically includes reviews/phase_state.json

# -------------------------------------------------------------------------
# Optional fields
# -------------------------------------------------------------------------
# dispatch_envelope_recorded: false  # true when the probe was dispatched via Task under subagent_type; I-SubAgent-1 applies
# r_refl_ma_audit:                   # present only when P-1 model-allocation audit ran
#   dispatch_plan_violation_count: 0 # R-Refl-MA-4 occurrences (model_used disagrees with dispatch_plan)
#   capability_inversion_refused: false
---

<!-- =====================================================================
     F3 Reflector-lightweight probe — prose body
     Lightweight mode is a memory-only integrity probe — no skill proposals,
     no plugin-update proposals, no wiki ingest. Narrate only what the
     counters cannot express.
     ===================================================================== -->

# Reflector lightweight probe — {{cycle_id}} iteration {{iteration}}

## 1. Grounding audit (Phase 1)

<when GROUNDING-PASS: single-line attestation; when GROUNDING-FINDINGS: list findings with grounding-rule number and file reference>

## 2. Tier-row contract audit (Phase 2f)

<when CLEAN: single-line attestation; when ADVISORY or MAJOR: list the offending rows with their row-level shape and the violated rule>

## 3. Probe-level notes

<optional: observations worth carrying into the next round's full Reflector (Phase 4 only); otherwise omit>
