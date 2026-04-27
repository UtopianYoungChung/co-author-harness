---
manuscript_id: v090-to-v100-pass-mixed-state
default_final_phase: Ph3
wiki_linked: true
sd_sr_required: false
claim_coverage_threshold: 0.8
---

# Classification — mixed-state

Mixed-state fixture: section 1 already carries `references_initialized` from
a prior partial migration; section 2 does not. The migration should skip
section 1 (idempotent) and add the field to section 2.
