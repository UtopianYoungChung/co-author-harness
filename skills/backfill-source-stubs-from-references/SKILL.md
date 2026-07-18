---
name: backfill-source-stubs-from-references
description: >-
  Fail-closed Coupling A-revised entry point. Canonical wiki source-stub generation
  from references/REFERENCES.md is unavailable; returns a structured deferred result only.
trigger: when the user asks to backfill wiki sources from a project's REFERENCES, populate the wiki source corpus, unblock Coupling B (concept-page grounding), or materialize Coupling A-revised
created_by: Reflector (Coupling A-revised automation)
version: 1.1
---

# Backfill Source Stubs from References

## FAIL-CLOSED: Wiki mutation unavailable

Canonical Wiki create/overwrite/append/promote is **unavailable**.

On invocation:

1. Do **not** create, overwrite, or append any canonical Wiki page under `knowledge/LLM wiki/wiki/**`.
2. Do **not** generate canonical source stubs in `wiki/sources/`.
3. Do **not** write an `m5_wiki_ingest` success trigger.
4. Do **not** fabricate `wiki_page_key`.
5. Return / record only:

```yaml
status: deferred
reason_code: WIKI_WRITE_TRANSACTION_UNAVAILABLE
wiki_page_key: null
```

Primary Research completion, approval, and release are **not** blocked by this deferral. This skill performs no canonical stub generation while the Wiki write transaction is unavailable.
