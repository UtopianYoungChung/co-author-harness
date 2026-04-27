---
manuscript_id: v090-to-v100-pass-idempotent-rerun
default_final_phase: Ph3
wiki_linked: true
sd_sr_required: false
claim_coverage_threshold: 0.8
coverage_regression_floor: 0.05
max_parallel_extend_snowball: 8
synthesis_alignment_threshold_cosine: 0.6
synthesis_alignment_threshold_jaccard: 0.3
auto_redlink_snowball: false
red_link_cap_per_round: 5
---

# Classification — idempotent-rerun

The project is already at v0.10.0 shape. Re-running the migration should
emit "already complete" and write the report only (no changes to
phase_state.json or classification.md).
