---
# =========================================================================
# F5 Planner consolidated-findings — v0.7.4 P-3 frontmatter contract
# Canonical filename: reviews/consolidated_findings_report_<YYYY-MM-DD>_iter<N>.md
# Schema: references/ARTEFACT_FRONTMATTER_SCHEMA.md §7
# Validator: scripts/artefact_frontmatter_validate.py
# Produced by: Planner (per-round aggregation across Evaluator F1 artefacts)
# =========================================================================

document_type: planner_consolidated_findings
schema_version: "1.0"
produced_at: "2026-04-21T00:00:00Z"
produced_by: planner
model_used: sonnet-4-6               # Planner orchestration default per MODEL_ALLOCATION.md §2
cycle_id: "TEMPLATE-PLACEHOLDER"
iteration: 0
section_heading_path: []             # [] when aggregating across sections; populated when scoped to one section
current_phase: Ph3
grounding_basis: []                  # F1 artefact paths the Planner aggregated

# -------------------------------------------------------------------------
# Scope declaration (required)
# -------------------------------------------------------------------------
scope_declared: local                # one of {local, cross_scope}; EG-3 fires on cross_scope at Ph2

# -------------------------------------------------------------------------
# Aggregated severity (required) — sum across all F1 artefacts this round
# -------------------------------------------------------------------------
aggregated_severity:
  blocker_count: 0
  major_count: 0
  minor_count: 0
  advisory_count: 0

# -------------------------------------------------------------------------
# Aggregated Check 8 (required) — worst-case across F1 per-section aggregates
# -------------------------------------------------------------------------
aggregated_check_8: CLEAN            # one of {CLEAN, BORDERLINE, MAJOR, BLOCKER}

# -------------------------------------------------------------------------
# Decision surface (required) — menu of next-move options presented to user
# -------------------------------------------------------------------------
decision_surface:
  menu_items_presented: []           # public slash commands or named checkpoint intents, e.g. ["/run-iterate", "terminal-signoff intent"]
  recommended_first: ""              # the first-ranked menu item; "" when no recommendation is defensible
  ceiling_lock_detected: false       # v0.7.4 P-8 ceiling-lock marker

# -------------------------------------------------------------------------
# Outgoing markers (required) — state-change flags propagated into notes
# -------------------------------------------------------------------------
outgoing_markers: []                 # e.g. [[CONVERGENCE-STABLE], [CEILING-LOCK-STABLE], [CONVERGENCE-BORDERLINE-ACCESSIBILITY]]

# -------------------------------------------------------------------------
# Optional fields
# -------------------------------------------------------------------------
# dispatch_plan_reference: "reviews/dispatch_plan_<cycle_id>.md"   # present when P-1 Phase 0.6 ran this round
# mcr_state:                         # present only when preparing MCR admission to Ph4
#   lagging_sections: []             # list of section_heading_path entries still below Ph3_converged
#   total_iteration_budget: 0        # integer; includes the +50% iteration reserve from NEW-H-7
#   mcr_admission_granted: false
---

<!-- =====================================================================
     F5 Planner consolidated-findings — prose body
     Aggregates Evaluator F1 artefacts into a single user-facing summary
     and surfaces the decision menu. Prose narrates the rationale behind
     the recommended-first menu item and any outgoing_markers.
     ===================================================================== -->

# Consolidated findings — {{cycle_id}} iteration {{iteration}}

## 1. Round summary

<one-paragraph thematic claim: what this round did, scope_declared, aggregated_severity at a glance>

## 2. Per-section rollup

<tabulate or list per-section severity from the F1 artefacts; cite by path>

## 3. Check 8 aggregate

<one-paragraph synthesis: aggregated_check_8, the dominant sub-check(s) driving it, whether the §3.3.3 Ph3 accessibility gate is in play>

## 4. Recommended next move

<narrate the decision: why recommended_first is the right call, what alternative menu items would deliver, whether ceiling_lock_detected changes the default>

## 5. Outgoing markers

<for each marker in outgoing_markers: one-line explanation of what downstream agents should do when they see this marker in notes>
