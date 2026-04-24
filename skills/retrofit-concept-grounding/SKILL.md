---
name: retrofit-concept-grounding
description: >-
  Retrofit wiki concept pages with grounding citations to existing source pages. Converts
  in-prose author-year references into wikilinks to `sources/` pages, updates frontmatter
  `sources` and `grounding_status`, and appends a grounding footer. Performs surgical edits
  only — does not rewrite page content.
trigger: when the user asks to ground concept pages, retrofit wikilinks after a batch source-stub run, materialize Coupling B, or close the grounding loop after SK-15
created_by: Reflector (Coupling B codification)
created_from: Research↔Wiki diagnostic audit 2026-04-13 — Finding F3 (concept pages assert claims without grounding citations); pilot on `concepts/humanness.md` 2026-04-13 demonstrated that retrofit works when (a) source stubs exist (SK-15) and (b) the retrofit is surgical (preserves existing prose) rather than a rewrite
pattern_source: GROUNDING_PROTOCOL.md Rule 4 (every theoretical claim must be citable); LLM wiki CLAUDE.md §Wikilinks ("link to existing concept/entity pages when mentioning key terms")
version: 1.0
---

# Retrofit Concept Grounding

You are executing **Coupling B** — the concept-page grounding retrofit that closes the loop between the wiki's external-source layer (populated by SK-15) and the concept pages that cite those sources in prose without wikilinks. The retrofit is **surgical**: you convert in-prose citations into wikilinks, update frontmatter, and append a grounding footer. You do NOT rewrite the page's argument, reorder its sections, or alter its claims.

## Preconditions

1. **Target concept page exists** at `LLM wiki/wiki/concepts/<name>.md` with existing prose content.
2. **Relevant source stubs exist** in `LLM wiki/wiki/sources/` — if the page cites sources that have no wiki page, the retrofit reports them as **red-link candidates** and does not fabricate links.
3. **Source pages' `source_key` frontmatter resolves** — the skill uses the `source_key` field to construct wikilinks, not the filename (though they should match).
4. **The page is not currently under live edit** — check for a conflicting modification timestamp; if the page was updated in the last hour by another agent, ask the user whether to proceed.

## What you do

### Phase 1 — Inventory citations

1. Read the target concept page.
2. Enumerate every in-prose author-year citation. Use the pattern: `Author (YYYY)`, `Author et al. (YYYY)`, `(Author YYYY)`, `(Author et al. YYYY)`, or in-table cells like `(Bandura 2001)`.
3. For each citation, attempt to resolve it to a `wiki/sources/<key>.md` page by matching author + year against the source pages' frontmatter (`source_key`) and first-line author field.
4. Produce two lists:
   - **Resolvable citations** — (author, year, target source_key)
   - **Red-link citations** — (author, year, *no source page exists yet*)

### Phase 2 — Plan edits

For each resolvable citation, plan a wikilink replacement:
- In-prose: `Suchman (2006)` → `[[sources/suchman-2006-reconfigurations|Suchman 2006]]`
- Parenthetical: `(Haslam et al. 2013)` → `([[sources/haslam-2013-humanness|Haslam et al. 2013]])`
- In-table: `(Bandura 2001)` → leave if no source page exists; retrofit if it does

Do NOT replace a citation that is already a wikilink. Do NOT replace citations inside code blocks or frontmatter.

### Phase 3 — Execute edits

1. **Update frontmatter `sources:`** to include every resolved `source_key` not already listed.
2. **Add `grounding_status: retrofit <YYYY-MM-DD>`** to frontmatter (or update the date if the field exists).
3. **Replace in-prose citations with wikilinks** using the plan from Phase 2. Preserve surrounding punctuation and capitalization exactly.
4. **Append a "Grounding sources" footer section** if one does not exist, or update it if it does:
   ```markdown
   ## Grounding sources

   | Source | Role on this page |
   |---|---|
   | [[sources/<key>]] | <one-line role — e.g., "foundational two-sense model (§1)", "Position A anchor (§3)"> |
   | ... | ... |

   *Grounding retrofit: <YYYY-MM-DD>. Status of each source (stub vs. direct-read) can be checked on its page.*
   ```
5. **Do NOT touch** existing sections (Core, Three Dimensions, etc.) except to convert citations within them to wikilinks.

### Phase 4 — Report red-links

Any citation that could not be resolved becomes a **red-link candidate** in the report. Common cases:

- The source is cited-but-not-read-directly in the project REFERENCES (per the Agency convention) and was correctly skipped by SK-15. Propose no action; note that the retrofit cannot ground it until it is read directly.
- The source is an external work not yet in any project's REFERENCES. Propose an ad-hoc stub or flag for user attention.
- The author-year string is ambiguous (e.g., "Leonardi (2023)" could map to one of several Leonardi papers). Report ambiguity; do not guess.

### Phase 5 — Verify

1. **Frontmatter integrity.** The `sources:` list is valid YAML; `grounding_status` is present.
2. **Wikilink resolution.** `grep` each new wikilink in the page; confirm each points to an existing `sources/*.md` file.
3. **Prose preservation.** Diff the page against its prior state; confirm that no sentence was deleted or reordered. Only citation-span substitutions and frontmatter additions should appear.
4. **Footer consistency.** The grounding footer matches the `sources:` frontmatter exactly (no source in footer but not in frontmatter, or vice versa).

## What you output

```markdown
## Coupling B Retrofit — <concept page>

**Page:** `wiki/concepts/<name>.md`
**Date:** <YYYY-MM-DD>

### Citations inventory
- In-prose: <n>
- In-table: <n>
- Already-linked (skipped): <n>

### Resolution
| Citation | Resolution | Source page |
|---|---|---|
| Suchman (2006) | resolved | [[sources/suchman-2006-reconfigurations]] |
| Bandura (2001) | red-link | (no source page — cited-via in REFERENCES) |
| ... | ... | ... |

### Edits applied
- Frontmatter: `sources:` list grew from <a> to <b>; `grounding_status: retrofit <date>` added
- Wikilinks inserted: <n>
- Grounding footer appended (<n> rows)

### Red-link candidates
<list with proposed disposition: "read-directly needed", "ad-hoc stub", "ambiguous — ask user">

### Verification
- [ ] Frontmatter valid
- [ ] All new wikilinks resolve
- [ ] No prose deleted or reordered (diff shows citation-span substitutions only)
- [ ] Footer matches frontmatter
```

## What you do NOT do

- **Do NOT rewrite the page.** No reordering sections, no consolidating paragraphs, no "improving" prose. The skill is surgical.
- **Do NOT invent source pages.** Red-links are reported, not created. Creating source pages is SK-15's job.
- **Do NOT fabricate claims.** If the page asserts a claim without a citation nearby, do not invent one. Flag it as `ungrounded-claim` in the report and leave the prose untouched.
- **Do NOT replace already-wikilinked citations.** A citation like `[[sources/chung-2026-redistributing|chung-2026-redistributing]]` is already grounded; skip it.
- **Do NOT propagate edits to other concept pages.** Each invocation handles one page; cross-page consistency is a separate audit.
- **Do NOT upgrade `grounding_status: stub` to `full`.** Only a direct-read pass does that; this skill only touches the concept page's status, not the source page's.

## Regeneration behavior

If invoked a second time on the same page after SK-15 has added more source stubs, the skill re-inventories and retrofits only the *new* resolvable citations. Existing wikilinks are preserved. The `grounding_status` date is updated.

## Notes on tier and scope

Package-tier skill. Applies to any concept page in `LLM wiki/wiki/concepts/` following the wiki's standard schema. The G/P/L/D classification used by SK-14 does not apply here; concept grounding is uniformly surgical.

## Sibling skills

- **Upstream:** SK-15 `backfill-source-stubs-from-references` — populates the source layer this skill depends on.
- **Downstream:** none directly. Once concept pages are grounded, the next-higher audit is at the synthesis level (cross-page consistency), which should be its own skill (SK-17 candidate, TBD).
