---
name: backfill-source-stubs-from-references
description: >-
  Generate wiki source-page stubs in batch from a project's `references/REFERENCES.md`,
  populating `LLM wiki/wiki/sources/` so concept pages can be grounded under the Grounding
  Protocol. Each stub is marked `grounding_status - stub` pending direct read-through.
trigger: when the user asks to backfill wiki sources from a project's REFERENCES, populate the wiki source corpus, unblock Coupling B (concept-page grounding), or materialize Coupling A-revised
created_by: Reflector (Coupling A-revised automation)
created_from: Research↔Wiki diagnostic audit 2026-04-13 — Finding F1 (wiki holds zero external scholarly sources; the wiki and the pipeline are complementary, not redundant); pilot retrofit of `concepts/humanness.md` showed that stub-first is a workable grounding instrument provided `grounding_status` frontmatter carries the audit trail
pattern_source: Research-root CLAUDE.md §6 + §11 (cross-project consistency, lessons compounding); GROUNDING_PROTOCOL.md Rule 4 (every theoretical claim must be citable); LLM wiki CLAUDE.md Operations §Ingest
version: 1.0
---

# Backfill Source Stubs from References

You are executing **Coupling A-revised** — the pipeline → wiki back-propagation of external scholarly sources. This skill reads a project's `references/REFERENCES.md`, enumerates every citation key, and produces a minimal but groundable `wiki/sources/<key>.md` stub for each one that does not already have a wiki page. The goal is to unblock Coupling B (concept-page grounding) by populating the external-source layer the wiki currently lacks.

## Preconditions

1. **Wiki exists** at the path declared by the workspace CLAUDE.md (expected: `LLM wiki/wiki/` with subfolders `sources/`, `concepts/`, `entities/`, `syntheses/`).
2. **Project has a REFERENCES file** at `<project>/references/REFERENCES.md` in the format established by INF3006Y_AgencyDelegation (source-root aliases + core corpus table + snowball table + cited-via table).
3. **The REFERENCES file is current.** Check the `Last updated:` footer. If older than the latest manuscript revision, ask the user whether to proceed with a potentially stale corpus.
4. **The wiki has at least one existing source page.** If the wiki is empty, this is a bootstrap run; proceed, but flag to the user that Coupling D (self-ingestion) has not been codified yet.

## What you do

### Phase 1 — Enumerate

1. Read `<project>/references/REFERENCES.md`.
2. Extract every row from the **core corpus** and **snowball** tables. Produce an explicit enumeration: `[(project_key, wiki_key, authors, year, title, venue, pdf_path), ...]`.
   - `project_key` is the citation key in REFERENCES (e.g. `haslam2013`).
   - `wiki_key` is the wiki-style key: `author-year-keyword` (e.g. `haslam-2013-humanness`). Pick the keyword from the most semantically load-bearing noun in the title, not from the venue.
3. **Do NOT enumerate "cited but not read directly" rows** unless the user explicitly asks for them. Those citations are indirection-marked in the manuscript (per the read-via convention) and should not get their own wiki pages until they are read directly.
4. Read `LLM wiki/wiki/index.md` to identify which wiki keys already exist. Produce a **delta list**: new keys to create vs. existing keys to skip.

### Phase 2 — Classify grounding priority

For each new key, tag a priority:

| Priority | Criterion | Purpose |
|---|---|---|
| **P1 — Anchor** | The source is the canonical anchor for an existing wiki concept page (e.g. haslam2013 → `concepts/humanness.md`) | Stub is needed immediately to unblock Coupling B |
| **P2 — Corpus** | The source is in the project's core/snowball corpus but not yet anchoring any concept page | Stub is useful but not urgent |
| **P3 — Contextual** | The source supports only §1 / §2 motivation; not load-bearing in the argument | Defer unless the user requests |

Produce the priority table explicitly before writing any file.

### Phase 3 — Generate stubs

For each key flagged P1 or P2 (or P3 if the user opted in), write `LLM wiki/wiki/sources/<wiki-key>.md` using this template:

```markdown
---
type: source
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
tags: [<domain tags inferred from title + the concept pages this source anchors>]
source_key: <wiki-key>
grounding_status: stub — bibliographic extracted from <project> REFERENCES; claims inferred from title and role in the corpus; direct PDF verification pending
---

# <Full title>

| Field | Value |
|---|---|
| **Authors** | <authors> |
| **Year** | <year> |
| **Venue / In** | <venue> |
| **Citation key** | `<wiki-key>` (wiki) / `<project-key>` (in `<project path>/references/REFERENCES.md`) |
| **Source PDF** | `<pdf_path>` (per <project> REFERENCES) |

## Stub notice

This page was created on <date> by skill SK-15 (`backfill-source-stubs-from-references`) as part of **Coupling A-revised**. The bibliographic fields are authoritative (taken from the project REFERENCES table). The claims summarized below are **inferred** from the paper's title, venue, and role in the corpus; a direct read-through should replace this stub with a full summary. High-stakes invocations should mark claims `(stub-grounded — verify)` until the direct read is logged.

## Why this source grounds <concepts it anchors>

<One paragraph naming which wiki concept page(s) this source is the expected anchor for, and what analytical move it enables. If unknown, write: "Candidate anchor for [concepts TBD after direct read]; inbound concept-page retrofits should reference this page once the read is complete.">

## Key claims (inferred — verify)

1. <claim from title / venue positioning>
2. <claim from role in the argument, per manuscript section references if available>
3. <claim from what the paper is cited-for in adjacent sources>

## Inbound references (wiki)

- [[concepts/...]] — expected grounding target (pending retrofit)
- [[sources/...]] — co-invoked sources in the research program (if any)

## Inbound references (Research/)

- `<project path>/references/REFERENCES.md` → `<project-key>`, <core/snowball> corpus
- `<project path>/manuscript/main.md` — deployment context (section references if known)
```

### Phase 4 — Update the wiki index and log

1. Append a new row to the Sources table in `LLM wiki/wiki/index.md` for each new stub:
   `| <wiki-key> | <Title> (stub) | <Authors short> | <Year> | [[sources/<wiki-key>]] |`
   Preserve the existing ordering convention; place stubs after already-present non-stub entries.
2. Append one consolidated entry to `LLM wiki/wiki/log.md`:
   ```
   ## [<YYYY-MM-DD>] backfill | Coupling A-revised — <project> REFERENCES → wiki sources

   Ran SK-15 against `<project path>/references/REFERENCES.md`. Created <N> source stubs:
   <bulleted list of wiki keys with one-line scope>. All marked `grounding_status: stub` pending
   direct PDF read. Delta: <M> keys already existed in the wiki (skipped). Unblocks Coupling B
   retrofits on concept pages: <list>.
   ```

### Phase 5 — Verify

1. **File count.** Confirm N new files exist in `wiki/sources/`.
2. **Index registration.** Each new key appears exactly once in `index.md`.
3. **Log registration.** Exactly one backfill entry was appended to `log.md`.
4. **Frontmatter consistency.** Every stub has `grounding_status: stub` in frontmatter.
5. **No duplicate keys.** The delta list correctly skipped pre-existing wiki pages; no key is duplicated.
6. **No edits to existing pages.** Only new files were written and the index + log were appended. Confirm no concept page or existing source page was modified.

## What you output

```markdown
## SK-15 Backfill Report — <project>

**REFERENCES file:** <path>
**Date:** <YYYY-MM-DD>

### Enumeration
- Core corpus rows: <n>
- Snowball rows: <n>
- Cited-via rows: <n> (skipped — read-via indirection)

### Delta
- New wiki keys to create: <n>
- Pre-existing wiki keys (skipped): <n>

### Priority table
| Wiki key | Project key | Priority | Anchor concept(s) |
|---|---|---|---|
| ... | ... | P1/P2/P3 | ... |

### Files written
<bulleted list of `sources/<key>.md` paths>

### Files edited
- `LLM wiki/wiki/index.md` — <n> new Sources rows
- `LLM wiki/wiki/log.md` — 1 backfill entry

### Unblocked Coupling B retrofits
<list of concept pages that can now cite newly-stubbed sources, with the proposed source→concept mapping>

### Verification
- [ ] <n> new files exist
- [ ] <n> new index rows
- [ ] 1 log entry
- [ ] All stubs carry `grounding_status: stub`
- [ ] No existing files modified
```

## What you do NOT do

- **Do NOT invent bibliographic details.** Every field in the stub must come from the project REFERENCES table. If a field is missing (e.g. DOI), write `—` rather than fabricating.
- **Do NOT generate a full summary.** The stub is a bounded commitment: minimal bibliographic anchor + inferred claims + expected concept anchors. A full summary requires a direct read and should be written on the next ingest pass.
- **Do NOT create stubs for "cited but not read directly" rows** unless explicitly asked. The read-via indirection is a correctness commitment; stubbing these would create false provenance.
- **Do NOT edit existing concept pages in this skill.** Retrofitting concept pages to cite new stubs is Coupling B's job (a separate skill or manual pass).
- **Do NOT delete or modify existing wiki source pages.** If a key already exists (e.g. the `haslam-2013-humanness` stub from the 2026-04-13 pilot), skip it — do not overwrite.
- **Do NOT promote stubs to non-stub status.** Only a direct-read pass removes `grounding_status: stub` from a page; this skill never does.

## Regeneration behavior

If this skill is invoked again on the same project and REFERENCES has grown, the skill processes only the delta — new keys are stubbed; existing stubs (whether still stubs or now non-stubs) are left alone. The log entry records the incremental run. Existing stubs are never overwritten.

## Notes on tier and scope

**Package-tier skill.** Applies to any project under `Research/` with a REFERENCES file in the standard format. Does not apply to non-academic projects. The `wiki-key` convention (`author-year-keyword`) is enforced to match the existing wiki's naming pattern; deviations should be justified by the Reflector if the target wiki uses a different convention.

## Sibling skill

SK-14 `promote-lessons-to-wiki` is the downstream sibling: once sources are stubbed by this skill, SK-14 can promote project lessons into syntheses that link cleanly to the newly-populated source layer without red-link candidates for external works.
