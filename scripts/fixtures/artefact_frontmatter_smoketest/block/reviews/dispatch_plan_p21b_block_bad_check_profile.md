---
document_type: planner_dispatch_plan
schema_version: "1.1"
produced_at: "2026-04-22T09:00:00Z"
produced_by: planner
model_used: opus-4-7
cycle_id: "C0001"
iteration: 1
section_heading_path: []
current_phase: Ph1
grounding_basis:
  - "reviews/phase_state.json"
  - "references/ARTEFACT_FRONTMATTER_SCHEMA.md"
round_id: "C0001"
sections_in_scope:
  - "1. Introduction"
dispatched_agents:
  - agent: evaluator
    phase: Ph2
    model_allocation: sonnet-4-6
    scope: per_section
    purpose: "deterministic step-0a + safeguard 1-8 evaluation on 1. Introduction"
checks_scheduled:
  - safeguard_1
  - safeguard_8
user_approval_required: true
check_profile: Ph3-refine
---

# F6 P2.1b BLOCK fixture (invalid check_profile)

Matches the well-formed shell of `pass/dispatch_plan_C0001.md` but uses a
**non-enum** `check_profile` value (`Ph3-refine` — the β proposal’s naming)
instead of the v0.8.0 P2.1b short tokens `{refine, structural, deep}` per
`proposals/v0.8.0_upgrade_architecture.md` §3.2. Single intended finding:
R-Refl-FM-2 MAJOR on `check_profile`. Expected exit 3.
