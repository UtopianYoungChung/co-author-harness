---
name: citation-format-pass
description: 'Run a Turabian/Chicago citation-FORM conformance pass — verify single-style consistency (notes-bibliography vs. author-date), note/bibliography/reference-list form, shortened-note discipline, parenthetical placement, and block-quote citation placement. Use when: "check my citations", "Turabian pass", "Chicago format", "fix the bibliography", "are my references formatted right".'
trigger: when the user asks to check citation formatting, run a Turabian/Chicago pass, fix the bibliography or reference list, or verify citation form
created_by: maintainer
created_from: Three-manuals integration PR-2, 2026-06-28 — docs/superpowers/plans/2026-06-28-three-manuals-integration.md §5
pattern_source: turabian_chicago_guidelines.md §§1–6
version: 1.0
---
# Citation-Format Pass (Turabian / Chicago)

You are running a citation **form** conformance review: which style, which fields, what punctuation and ordering. You are **not** deciding whether a citation belongs — that judgment is `CITATION_DISCIPLINE.md`, and you must not duplicate or override it.

**Prerequisite:** Read `turabian_chicago_guidelines.md` before proceeding. Read the project's `research_notes/directives.md` `citation_style` field — it selects notes-bibliography (NB) vs. author-date (AD). If no style is declared, report that and ask before flagging style-specific items.

---

## What you do

### Phase 1 — Style identification and consistency

1. Determine the declared style (NB or AD) from `directives.md`. If absent, infer from the manuscript's dominant pattern and flag the absence.
2. Scan for **mixing**: superscript notes + parenthetical `(Author Year, page)` in the same paper is a [MAJOR] consistency violation (`turabian §1`). One style throughout.

### Phase 2 — Form conformance (style-conditioned)

**If NB:**

| Check | Source | What to verify |
|---|---|---|
| First (full) note form | turabian §2 | `N: Firstname Lastname, Title: Subtitle (Place: Publisher, Year), page.` |
| Shortened subsequent note | §2 | After first citation to a source: `Lastname, Short Title, page.` — flag full notes repeated where a short form is required. |
| Bibliography entry form | §2 | Surname-first, period-delimited, no parentheses around publication facts; alphabetical by surname. |
| Repeated-author 3-em dash | §2 | Multiple works by one author: 3-em dash for entries after the first, ordered by title. |

**If AD:**

| Check | Source | What to verify |
|---|---|---|
| Parenthetical form | turabian §3 | `(Lastname Year, page)`; year present; page where a specific passage is cited. |
| Reference-list entry form | §3 | Surname-first, year immediately after author. |
| List completeness | §3 | Every parenthetical resolves to a reference-list entry and vice versa (orphan check). |

**Both styles — quotations (turabian §4):**
- Run-in quotation: citation before the terminal period (AD) / note number after closing punctuation (NB).
- Block quotation: parenthetical **after** the terminal punctuation mark.

### Phase 3 — Output

```markdown
## Citation-Format Pass Results (Turabian/Chicago)

**File:** <path>
**Declared style:** <NB | AD | none-declared>
**Date:** <date>

### Consistency
- Style mixing detected: <none | list of locations>

### Form findings (by location)

| # | Location | Check | Finding | Severity | Proposed fix |
|---|---|---|---|---|---|
| 1 | note 12 | shortened-note | Full note repeated; short form required after first | [MINOR] | Shorten to `Lanier, Not a Gadget, 133–34.` |

### Orphans (AD)
- Parentheticals with no reference-list entry: <list>
- Reference-list entries never cited: <list>

### Summary
- MAJORs: <n>  MINORs: <n>  CONFLICTs: <n>
```

---

## What you do NOT do

- **Do not decide whether to cite.** Engagement-cite vs. demarcation-cite is `CITATION_DISCIPLINE.md`. If you find a missing citation that is a *judgment* question (should this term-of-art be cited at all?), flag "out of scope — see CITATION_DISCIPLINE" and stop. You only verify that *existing* citations are correctly *formed*, and that parenthetical/reference-list sets are mutually complete.
- **Do not verify source existence or claim accuracy.** That is the Evaluator's grounding/external-verifier path (`EXTERNAL_VERIFIERS.md`, `GROUNDING_PROTOCOL.md`).
- **Do not legislate shared mechanics blindly.** Where Turabian Part III and the Blue Book differ (serial comma, number threshold), apply the declared-style precedence rule (`turabian_chicago_guidelines.md §5`); emit `[CONFLICT]` rather than silently choosing.
- **Do not touch sentence craft or grammar correctness** — those are `sentence-level-pass` and `grammar-mechanics-pass`.

---

## When to escalate

If the manuscript mixes NB and AD throughout (not a slip but a systemic inconsistency), recommend the author settle the style in `directives.md` first; a format pass cannot proceed coherently against an undeclared, mixed target.
