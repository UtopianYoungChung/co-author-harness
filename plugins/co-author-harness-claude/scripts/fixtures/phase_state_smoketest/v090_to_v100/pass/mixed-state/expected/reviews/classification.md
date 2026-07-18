---
manuscript_id: v090-to-v100-pass-mixed-state
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
inherit_snowball: true
pre_seed_cap: 10
---

# Classification — mixed-state

Mixed-state fixture: section 1 already carries `references_initialized` from
a prior partial migration; section 2 does not. The migration should skip
section 1 (idempotent) and add the field to section 2.
