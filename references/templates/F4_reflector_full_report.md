---
# =========================================================================
# F4 Reflector-full report — v0.7.4 P-3 frontmatter contract
# Canonical filename: reviews/reflector_full_<YYYY-MM-DD>.md
# Schema: references/ARTEFACT_FRONTMATTER_SCHEMA.md §6
# Validator: scripts/artefact_frontmatter_validate.py
# Produced by: Reflector in full mode (Phases 1–6 + audit phases 2d/2e/2f/2g/2.5/2.5.1/2.6)
# Dispatch: EXACTLY ONCE per Ph4 close-out; never inherited; never re-run within a cycle
# NOTE: F4 is NON-STRICT — the validator permits unknown top-level fields for
#       extensibility. Prefer nesting new fields under historical_audits.
# =========================================================================

document_type: reflector_full_report
schema_version: "1.0"
produced_at: "2026-04-21T00:00:00Z"
produced_by: reflector
model_used: opus-4-7                 # Reflector-full-Ph4 is one of the four Opus-4.7 floor slots per MODEL_ALLOCATION.md §2
cycle_id: "TEMPLATE-PLACEHOLDER"     # the cycle that just closed at Ph4
iteration: 0                         # final iteration number within the Ph4 cycle
section_heading_path: []             # always [] at Ph4 close-out (manuscript-scoped)
current_phase: Ph4
grounding_basis: []

# -------------------------------------------------------------------------
# Phase aggregates (required) — one entry per reflector phase
# -------------------------------------------------------------------------
phase_aggregates:
  phase_1_evidence_gathering:
    artefacts_read: 0
    verdict: "CLEAN"                 # short attestation string; "CLEAN" | "ADVISORY" | "MAJOR" | "BLOCKER"
  phase_2_a_grounding:
    verdict: "CLEAN"
    findings_count: 0
  phase_2_d_t3_convergence:
    sections_audited: 0
    stale_sections: 0                # number of sections carrying [Ph3-STALE] at close-out
    verdict: "CLEAN"
  phase_2_e_mcr_volatility:
    volatility_score: 0.0            # manuscript-convergence-report volatility score; ≥ 0.0
    verdict: "CLEAN"
  phase_2_f_row_contract:
    rows_audited: 0
    violations: 0
    verdict: "CLEAN"
  phase_2_g_accessibility:           # v0.7.2+ accessibility-recurrence audit
    recurring_flags: []              # list of sub-check letters that recurred across rounds
    cross_project_patterns: []       # list of project keys where the same pattern appeared
    verdict: "CLEAN"
  phase_2_5_self_audit:
    verdict: "CLEAN"
  phase_2_5_1_hallucination:
    instances: 0
    verdict: "CLEAN"
  phase_2_6_protocol_self:
    verdict: "CLEAN"
  phase_3_memory_update:
    lessons_added: 0
    lessons_merged: 0
  phase_4_skill_proposals:
    new_proposals: 0
    filed_at: "reviews/plugin_update_proposals.md"
  phase_5_wiki_ingest:               # Coupling D: M5 → wiki source-page ingest
    status: "N/A"                    # "INGESTED" | "SKIPPED-NOT-M5" | "N/A"
    wiki_page_key: ""
  phase_6_session_close:
    verdict: "CLEAN"

# -------------------------------------------------------------------------
# Overall verdict (required)
# -------------------------------------------------------------------------
overall_verdict: CLEAN               # one of {CLEAN, ADVISORY, MAJOR, BLOCKER}

# -------------------------------------------------------------------------
# Optional fields
# -------------------------------------------------------------------------
# plugin_update_proposals_filed: []  # list of proposal-file paths; routed through the Planner's three-filter gatekeeper
# lessons_promoted_to_wiki: []       # list of wiki page keys (Coupling C)
# historical_audits:                 # retroactive audit blocks
#   confirmation_failed_migration:   # aggregated audit of pre-v0.7.0 confirmation_failed rows
#     rows_retouched: 0
#     verdict: "CLEAN"
---

<!-- =====================================================================
     F4 Reflector-full report — prose body
     Full-mode Reflector runs exactly once per Ph4 close-out. The prose
     narrates each of the audit phases, extracts lessons, proposes skills
     (filed to reviews/plugin_update_proposals.md, NOT emitted directly),
     and closes the session. See AGENT_CONTRACTS.md §Reflector and
     skills/run-reflection/ for the authoritative five-phase contract.
     ===================================================================== -->

# Reflector full report — {{cycle_id}} Ph4 close-out

## Phase 1 — evidence gathering

<narrate which artefacts were read and what the aggregate evidence base looks like>

## Phase 2 — audit blocks

### 2a Grounding audit (Rules 1–7a)

### 2d Ph3 convergence audit (renamed from T3 at v0.7.4)

### 2e [Ph3-STALE] / MCR volatility audit

### 2f Tier-row contract audit (including R-Refl-MA-* and R-Refl-FM-* classes)

### 2g Accessibility-recurrence audit (v0.7.2+)

### 2.5 / 2.5.1 / 2.6 Self-audit blocks

## Phase 3 — memory update

<narrate lesson-file updates, consolidations, and prunes>

## Phase 4 — skill proposals (filed to Planner gatekeeper)

<list proposals filed; do NOT surface proposals directly to user — Planner three-filter gate is binding>

## Phase 5 — wiki ingest (Coupling D)

<when M5 + Ph4 close-out: narrate the ingest target and verify bidirectional wikilinks>

## Phase 6 — session close

<final attestation: grounding integrity, row-contract integrity, memory integrity>
