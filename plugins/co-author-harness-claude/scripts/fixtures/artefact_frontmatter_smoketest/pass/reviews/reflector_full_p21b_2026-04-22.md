---
document_type: reflector_full_report
schema_version: "1.1"
produced_at: "2026-04-22T11:00:00Z"
produced_by: reflector
model_used: sonnet-4-6
cycle_id: "P21B-F4"
iteration: 0
section_heading_path: []
current_phase: Ph4
grounding_basis:
  - "reviews/phase_state.json"
phase_aggregates: {}
overall_verdict: CLEAN
demoted_check_advisories:
  - check_id: accessibility_overlay
    finding_summary: "incidental demoted-class pattern noticed under check-8 sweep"
    severity: ADVISORY
    source_iteration: 2
    routing_rationale: primary_evidence=accessibility_overlay
---

# F4 P2.1b PASS fixture

Minimal F4 with optional `demoted_check_advisories` carrying one legal row.
