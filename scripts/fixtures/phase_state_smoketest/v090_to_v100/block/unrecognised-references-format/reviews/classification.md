---
manuscript_id: v090-to-v100-block-unrecognised-references
default_final_phase: Ph3
wiki_linked: true
sd_sr_required: false
---

# Classification — unrecognised-references-format

The migration must abort with exit code 8 because REFERENCES.md exists but
carries none of the recognised section headers, so the
`references_initialized` heuristic cannot decide.
