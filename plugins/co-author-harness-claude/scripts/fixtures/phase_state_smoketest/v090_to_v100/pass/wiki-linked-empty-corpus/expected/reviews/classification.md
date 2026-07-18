---
manuscript_id: v090-to-v100-pass-wiki-linked-empty-corpus
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

# Classification — wiki-linked-empty-corpus

REFERENCES.md exists with the three required headers but no content rows;
migration should set `references_initialized: false`.
