---
name: turabian-format-pass
description: 'Run a Turabian/Chicago document-FORMAT conformance pass against Appendix A (Paper Format and Submission) — heading-level hierarchy and per-level consistency, front-matter presence and order, title-page elements, table/figure numbering + caption + placement, and the physical-layout checklist (margins, spacing, pagination) deferred to the manual and any venue template. Orthogonal to citation form and grammar mechanics. Use when: "Turabian format check", "does this follow Turabian layout", "check my headings/front matter", "thesis format pass", "Appendix A check".'
trigger: when the user asks to check document/paper format, layout, headings, front matter, title page, or table/figure placement against Turabian/Chicago (Appendix A) — a thesis, dissertation, or Chicago-styled course paper with no overriding venue template
created_by: maintainer
created_from: 2026-07-01 D-STYLE/Turabian presentation-coverage audit — closes the Appendix A gap identified in turabian_chicago_guidelines.md §6 (format demoted to "pointers"; no skill enforced it)
pattern_source: turabian_chicago_guidelines.md §6 (Paper format — Appendix A); Turabian, A Manual for Writers, Appendix (Paper Format and Submission), §§A.1–A.3
version: 1.0
---
# Turabian Document-Format Pass (Appendix A)

You are running a document **format** conformance review: the physical presentation of the paper — heading hierarchy, front matter, title page, and the placement and labelling of tables and figures — against Turabian's Appendix A (Paper Format and Submission). You are **not** checking citation form, grammar mechanics, or prose accessibility. Those are three separate passes (see "What you do NOT do").

**Prerequisite reads:**
1. `turabian_chicago_guidelines.md §6` — the Appendix A pointer set (A.1 general format; A.2 title page, margins, pagination, headings, block quotations, tables/figures; A.3 file preparation and submission). This file is your grounded authority for *which* elements Appendix A governs.
2. The project's `research_notes/directives.md` — the `d_style_profile` block. Read two fields:
   - `harness_profile` — **the applicability gate.** This pass is in scope for `thesis_qe` and for any Chicago/Turabian-styled course paper. Under `venue_submission`, **the venue template overrides Turabian format**; run only the venue-independent checks and mark the rest `[DEFERRED — venue template governs]` (the `venue_template_precedence` obligation, `d_style_profile_check.py`).
   - `citation_style` — `turabian_notes_bibliography` or `turabian_author_date` confirms Turabian is the declared style. If a non-Turabian style is declared, report that Appendix A may not be the governing format authority and ask before flagging.

**Grounding boundary — structure and consistency, not invented values.** Exact physical values (margin width, point size, line spacing, page-number position) are set by the manual and, above it, by the institution or venue. The harness operates on the Markdown manuscript, which cannot express most of them. So this pass audits **structural presence, ordering, and internal consistency** — the things the source *can* express — and defers absolute values to the manual and venue template rather than asserting numbers. Never emit a specific measurement as a Turabian requirement unless you have read it in the manual or the project's venue template; cite it when you do.

---

## What you do

### Phase 0 — Applicability

1. Resolve `harness_profile`. If `venue_submission`, announce that venue-template precedence is active and scope the pass to venue-independent structure only.
2. Confirm the declared `citation_style` is a Turabian variant. If not, report and ask.
3. If neither is declared, infer that this is a Turabian-format request from the user's phrasing, note the absence, and proceed with the structural checks only.

### Phase 1 — Heading hierarchy (A.2, subheads)

| Check | What to verify |
|---|---|
| Level integrity | Heading levels descend without skipping (no Level 1 → Level 3 jump). In Markdown source, `#`/`##`/`###` depth is the proxy for Turabian subhead level. |
| Per-level consistency | Every heading at a given level is rendered the same way throughout (Turabian assigns a fixed treatment to each subhead level; the manuscript must not vary it). Flag any level whose formatting or capitalization drifts between instances. |
| Level count discipline | Flag runaway nesting (more distinct levels than the document's structure warrants); Turabian expects a small, consistent set of subhead levels. |
| Numbered-heading consistency | If sections are numbered, numbering is consistent and gap-free; if unnumbered, none carry stray numbers. |

*Note the boundary with `accessibility-overlay` (C-5): that pass judges whether headings **signpost** for the reader (rhetorical function). This pass judges whether the heading **hierarchy is well-formed** (Turabian structural form). Report a heading issue under only one of the two.*

### Phase 2 — Front matter presence and order (A.1, A.2.1)

For a thesis/dissertation (`thesis_qe`), verify the expected front-matter elements are present and in Appendix A order (title page → any copyright/abstract → contents → any lists of tables/figures → body). Flag missing or out-of-order elements. For a course paper, verify at minimum a title block. Do **not** invent required elements the manual or the institution has not specified — report presence/order of what Appendix A enumerates and mark institution-specific items `[CONFIRM — institution front-matter spec]`.

### Phase 3 — Title-page elements (A.2.1)

Verify the title page (or title block) carries the elements Appendix A enumerates: title, author, and the course/degree/date identifying block. Flag missing elements. Exact placement and spacing are `[CONFIRM — manual/venue]`.

### Phase 4 — Tables and figures (A.2, tables/figures)

| Check | What to verify |
|---|---|
| Numbering | Tables and figures are each numbered consecutively (Table 1, Table 2…; Figure 1, Figure 2…), in their own sequences, in order of first mention. |
| Caption presence | Every table and figure has a caption/title. |
| In-text reference | Every numbered table/figure is referred to in the text before it appears (call-out precedes object); flag orphans (present but never referenced) and dangling references (referenced but absent). |
| Source/note placement | Where a table/figure carries a source or note, it is attached to the object (this is *placement*, not citation form — citation *wording* is `citation-format-pass`). |

### Phase 5 — Physical-layout checklist (A.1, A.3) — deferred by design

Emit these as a checklist for the author to confirm at typesetting, **not** as source-level BLOCKERs (the Markdown source cannot carry them): margins, line spacing, page-number presence and position, and file-preparation/submission format (A.3). Each item is `[CHECKLIST — confirm against manual/venue template]`. If a venue template exists, point to it as the governing authority.

### Phase 6 — Output

```markdown
## Turabian Document-Format Pass (Appendix A)

**File:** <path>
**Applicability:** harness_profile=<thesis_qe | venue_submission | course-paper | undeclared>; citation_style=<turabian_notes_bibliography | turabian_author_date | other | none>
**Venue-template precedence:** <active — scoped to structure | not active>
**Date:** <date>

### Findings (by location)

| # | Location | Element (Appendix A) | Finding | Severity | Proposed fix |
|---|---|---|---|---|---|
| 1 | §3 headings | heading hierarchy | Level 1 → Level 3 skip at "Method" | [MAJOR] | Insert a Level 2 heading or promote "Method" to Level 2 |
| 2 | Figure 2 | figure numbering | Referenced in text as "Figure 3"; object labelled "Figure 2" | [MAJOR] | Reconcile label and call-out |

### Deferred / confirm items
- [CHECKLIST — manual/venue]: margins, spacing, page-number position, submission file format (A.1/A.3)
- [CONFIRM — institution spec]: <front-matter items the institution sets>

### Summary
- BLOCKERs: <n>  MAJORs: <n>  MINORs: <n>  Deferred: <n>
```

---

## What you do NOT do

- **Do not check citation form.** Note/bibliography/reference-list form, shortened notes, parenthetical placement, and the 3-em dash are `citation-format-pass`. If you notice a citation-form issue, flag "out of scope — see citation-format-pass" and move on.
- **Do not check grammar or mechanical style.** Punctuation, number style, capitalization-as-grammar, and the serial comma are `grammar-mechanics-pass`. Heading *capitalization consistency* is in scope here only as a per-level format-consistency question, not as a mechanics judgment.
- **Do not judge reader accessibility.** Whether a heading orients the reader, paragraph cadence, and signposting are `accessibility-overlay` (C-5). This pass judges only whether the heading *hierarchy is structurally well-formed*.
- **Do not assert physical measurements as Turabian requirements** unless read from the manual or the venue template, with a citation. Defer values; audit structure.
- **Do not override a venue template.** Under `venue_submission`, the template wins on every item it covers; your job shrinks to venue-independent structure and a pointer to the template.

## When to escalate

If `harness_profile` is `venue_submission` **and** no venue template is on file, the governing format authority is undetermined — report that and ask the author to supply the template or confirm Turabian Appendix A governs before flagging format items. If the manuscript is a thesis/dissertation with an institution-specific format spec (common for `thesis_qe`), that spec sits above Turabian; ask for it and treat Appendix A as the fallback.
