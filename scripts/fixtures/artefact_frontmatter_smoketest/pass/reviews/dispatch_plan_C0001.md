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
  - agent: generator
    phase: Ph3
    model_allocation: opus-4-7
    scope: per_section
    purpose: "address evaluator findings via Planner-curated check menu"
  - agent: reflector
    phase: Ph3
    model_allocation: sonnet-4-6
    scope: cycle_level
    purpose: "Phase 2f log audit + grounding audit post-generation"
checks_scheduled:
  - safeguard_1
  - safeguard_8
  - grounding_audit
  - deterministic_step_0a
user_approval_required: true
subagent_envelope:
  - dispatching_agent: evaluator
    subagent_type: check8_aggregator
    verdict_authoritative_as_read: true
stability_sub_mode_anticipated: false
ceiling_lock_anticipated: false
mcr_admission_anticipated: false
notes: "first round on 1. Introduction; standard full-pass envelope under MODEL_ALLOCATION.md defaults."
user_approval_signature:
  approved_at: "2026-04-22T09:05:00Z"
  approved_by: "user"
  modifications_recorded: false
check_profile: refine
structural_delta_flag: false
parallel_dispatch: true
threshold_version: v0.7.5-provisional
---

# Dispatch plan — cycle C0001

This fixture is authored against `references/ARTEFACT_FRONTMATTER_SCHEMA.md §7a`
and is exercised by `scripts/release-gate.sh` to assert that
`scripts/artefact_frontmatter_validate.py` returns exit code `0` on a
well-formed F6 `planner_dispatch_plan` artefact. The body below the YAML
fence is not validated; it is present purely to make the fixture a legal
Markdown document.

## Dispatch envelope

- Round scope: `1. Introduction` (one section).
- Agents: evaluator (Ph2), generator (Ph3), reflector (Ph3).
- Subagent delegation: `check8_aggregator` under `I-SubAgent-1`.
- User approval: recorded above with `modifications_recorded: false`.
