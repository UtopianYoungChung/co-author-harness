---
name: ingest-m5-to-wiki
user-invocable: false
description: Fail-closed Coupling D entry point. Canonical Wiki ingestion of an M5 manuscript is unavailable; returns a structured deferred result only.
trigger: when the user asks to ingest an M5 paper into the wiki, close out a project with a wiki source entry, materialize Coupling D, or finalize the wiki record for a completed manuscript after G.4 sign-off
created_by: Reflector (Coupling D formalization)
version: 1.1
---

# Ingest M5 to Wiki

## Output-routing preflight (future activation only)

Before any canonical Wiki mutation is re-enabled, resolve this exact tuple:

```python
resolve("co_author_harness", "curate", "knowledge_graph", "wiki_page")
```

Use only the returned `destination_path`; do not substitute a literal Wiki
path. The installed manifest resolves this tuple to WIKI_CURATED, but route
declaration is destination-only and does not enable mutation. `RoutingError` is
a hard stop. While the governed write transaction is unavailable, retain the
structured deferred result below.

## FAIL-CLOSED: Wiki mutation unavailable

Canonical Wiki create/overwrite/append/promote is **unavailable**.

On invocation:

1. Do **not** create, overwrite, or append any canonical Wiki page under `knowledge/LLM wiki/wiki/**`.
2. Do **not** mutate project-local success fields or ingestion receipts that claim Wiki write success.
3. Do **not** write an `m5_wiki_ingest` success trigger.
4. Do **not** fabricate `wiki_page_key`.
5. Return / record only:

```yaml
status: deferred
reason_code: WIKI_WRITE_TRANSACTION_UNAVAILABLE
wiki_page_key: null
```

Primary Research completion, approval, and release are **not** blocked by this deferral. This skill performs no Wiki mutation and no project-local success mutation while the Wiki write transaction is unavailable.
