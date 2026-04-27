---
manuscript_id: v090-to-v100-block-invalid-json
default_final_phase: Ph3
wiki_linked: false
---

# Classification — invalid-json-state

The phase_state.json deliberately omits a comma after the manuscript_id
value (between `"v090-to-v100-block-invalid-json"` and `"default_final_phase"`).
Migration should fail with exit code 4 (JSON parse error).
