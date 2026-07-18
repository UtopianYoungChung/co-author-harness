---
document_type: reflector_full_report
schema_version: "1.1"
produced_at: "2026-04-22T11:00:00Z"
produced_by: reflector
model_used: sonnet-4-6
cycle_id: "P21B-F4-BLOCK"
iteration: 0
section_heading_path: []
current_phase: Ph4
grounding_basis:
  - "reviews/phase_state.json"
phase_aggregates: {}
overall_verdict: CLEAN
demoted_check_advisories:
  - check_id: foo
    finding_summary: "bar"
    severity: NOT_A_SEVERITY
    source_iteration: 0
    routing_rationale: primary_evidence=foo
---

# F4 P2.1b BLOCK fixture

Single intended violation: `demoted_check_advisories[0].severity` is not one
of {MINOR, MAJOR, ADVISORY, BLOCKER}. Expected exit 3 (R-Refl-FM-2 MAJOR).
