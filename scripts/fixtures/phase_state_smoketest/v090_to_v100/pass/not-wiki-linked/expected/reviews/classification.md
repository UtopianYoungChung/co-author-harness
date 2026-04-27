---
manuscript_id: v090-to-v100-pass-not-wiki-linked
default_final_phase: Ph3
wiki_linked: false
sd_sr_required: false
claim_coverage_threshold: 0.8
coverage_regression_floor: 0.05
max_parallel_extend_snowball: 8
synthesis_alignment_threshold_cosine: 0.6
synthesis_alignment_threshold_jaccard: 0.3
auto_redlink_snowball: false
red_link_cap_per_round: 5
---

# Classification — not-wiki-linked

The project is not wiki-linked and `references/REFERENCES.md` does not
exist. The migration should still run cleanly; `references_initialized`
defaults to `false`.
