---
document_type: planner_dispatch_plan
schema_version: "1.0"
produced_at: "2026-04-22T09:00:00Z"
produced_by: planner
model_used: opus-4-7
cycle_id: "C0002"
iteration: 1
section_heading_path: []
current_phase: Ph1
grounding_basis:
  - "reviews/phase_state.json"
  - "references/ARTEFACT_FRONTMATTER_SCHEMA.md"
round_id: "C0002"
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
user_approval_required: false
---

# Dispatch plan — cycle C0002 (deliberately malformed)

This fixture is exercised by `scripts/release-gate.sh` to assert that
`scripts/artefact_frontmatter_validate.py` catches a v0.7.4 F6 dispatch-plan
consent violation. The single intended failure is:

- `user_approval_required: false`, which violates
  `references/ARTEFACT_FRONTMATTER_SCHEMA.md §8 rule 7` and fires
  `R-Refl-FM-2` MAJOR via the F6 cross-field check in
  `artefact_frontmatter_validate.py::_check_cross_field`.

Expected exit code is `3` (MAJOR findings present, no BLOCKER). The F6
finding-class taxonomy does not contain any BLOCKER-severity in-file
finding; cross-artefact BLOCKER classes (R-Refl-DP-1/2/3) are scheduled
against a later sub-phase and are out of scope for this single-file
validator.
