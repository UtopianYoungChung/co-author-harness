---
name: promote-lessons-to-wiki
description: 'Fail-closed Coupling C entry point. Canonical Wiki promotion of research_notes/lessons_learned.md is unavailable; returns a structured deferred result only.'
trigger: when the user asks to promote lessons to the wiki, close a reflection round with a wiki update, materialize Coupling C, or regenerate a lessons synthesis after L-xx append
created_by: Reflector (Coupling C pilot)
version: 1.1
---

# Promote Lessons to Wiki

## FAIL-CLOSED: Wiki mutation unavailable

Canonical Wiki create/overwrite/append/promote is **unavailable**.

On invocation:

1. Do **not** create, overwrite, or append any canonical Wiki page under `knowledge/LLM wiki/wiki/**`.
2. Do **not** mutate project-local success fields, back-pointers, or promotion receipts that claim Wiki write success (including `lessons_promoted_to_wiki`).
3. Do **not** write an `m5_wiki_ingest` success trigger.
4. Do **not** fabricate `wiki_page_key`.
5. Return / record only:

```yaml
status: deferred
reason_code: WIKI_WRITE_TRANSACTION_UNAVAILABLE
wiki_page_key: null
```

Primary Research completion, approval, and release are **not** blocked by this deferral. This skill performs no Wiki mutation and no project-local success/back-pointer mutation while the Wiki write transaction is unavailable.
