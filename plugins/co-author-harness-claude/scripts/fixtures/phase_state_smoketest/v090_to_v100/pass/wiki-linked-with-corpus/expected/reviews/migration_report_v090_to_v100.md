---
document_type: migration_report
schema_version: "1.0"
schema_from: "0.7.4"
schema_to: "0.10.0"
---

Relaxed-match placeholder. The validator only checks `schema_from` and
`schema_to` are present in the actual report's frontmatter; timestamps,
sections_migrated_count, and per-section table content vary per run.
