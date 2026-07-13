---
document_type: evaluator_findings
schema_version: "1.1"
produced_at: "2026-04-22T10:00:00Z"
produced_by: evaluator
model_used: opus-4-7
cycle_id: "P21B-F1-BLOCK"
iteration: 0
section_heading_path:
  - "1. Introduction"
current_phase: Ph3
grounding_basis:
  - "manuscript/main.tex"
severity_aggregates:
  blocker_count: 0
  major_count: 0
  minor_count: 0
  advisory_count: 0
  total_count: 0
check_8_aggregate: CLEAN
check_8_subcheck_counters:
  sub_a_cadence_flag_count: 0
  sub_b_rhythm_flag_count: 0
  sub_c_first_use_flag_count: 0
  sub_d_signpost_flag_count: 0
  sub_e_jargon_density_flag_count: 0
  sub_f_worked_example_flag_count: 0
  sub_g_consolidation_flag_count: 0
  sub_h_register_flag_count: 0
reader_accessibility_policy:
  profile_path: reviews/reader_accessibility_resolved.json
  profile_sha256: "0000000000000000000000000000000000000000000000000000000000000000"
  manuscript_sha256: "0000000000000000000000000000000000000000000000000000000000000000"
  check8_evidence_path: reviews/safeguard_check8.md
  check8_evidence_sha256: "0000000000000000000000000000000000000000000000000000000000000000"
  phase: Ph3
  candidate_artifact_path: reviews/reader_accessibility_candidates.json
  candidate_artifact_sha256: "0000000000000000000000000000000000000000000000000000000000000000"
check_8_adjacent_advisories:
  ve_finding_count: 0
dnd_byte_verification:
  anchors_verified: true
  anchor_count: 0
  anchor_drift_count: 0
coupling_e2_overlay:
  verdict: "N/A"
  graph_stub_citation_count: 0
  section_location_mismatch_count: 0
  missing_citation_candidate_count: 0
adversarial_register: refinement
routing_rationale: "not a primary_evidence= token"
---

# F1 P2.1b BLOCK fixture

Single intended violation: `routing_rationale` does not match
`primary_evidence=<check_id>` (schema §8 rule 8). Expected exit 3
(R-Refl-FM-2 MAJOR).
