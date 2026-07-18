---
name: grammar-mechanics-pass
description: 'Run a targeted Blue Book grammar-and-punctuation correctness pass on academic prose — mechanical scan (it''s/its, comma splices, that/which, Oxford comma, compound-modifier hyphenation, number style) plus a judgment pass on agreement and restrictiveness, emitting per-finding fixes. Use when: "copyedit", "grammar pass", "punctuation check", "Blue Book pass", "fix the mechanics", "proofread".'
trigger: when the user asks for a copyedit, grammar pass, punctuation check, Blue Book pass, proofread, or fix the mechanics
created_by: maintainer
created_from: Three-manuals integration, 2026-06-28 — docs/superpowers/plans/2026-06-28-three-manuals-integration.md §4
pattern_source: blue_book_grammar_guidelines.md §§1–7; turabian_chicago_guidelines.md §5 (Part III item map, Turabian sub-pass added v1.1, 2026-07-01)
version: 1.1
---
# Grammar-Mechanics Pass (Blue Book)

You are running a targeted **correctness** review on academic prose: grammar and punctuation mechanics, not rhetoric or rhythm. This skill draws on `blue_book_grammar_guidelines.md`.

**Prerequisite:** Read `blue_book_grammar_guidelines.md` in the package before proceeding. Do not rely on memory; rules and precedence may have changed. If the project declares a `citation_style` in `research_notes/directives.md`, note it — it governs venue-sensitive items (Oxford comma, number threshold). **When the declared style is Chicago/Turabian (`turabian_author_date` or `turabian_notes_bibliography`), also read `turabian_chicago_guidelines.md §5` including the §5.1 Part III item map** — it is the precedence authority for every mechanical item Part III legislates (numbers, possessives, compounds, serial comma, other punctuation, title capitalization, titles-of-works italic/quotation-mark treatment, and abbreviations), and the Blue Book yields to it on those items while remaining the source of the judgment heuristics (agreement, restrictiveness, who/whom). When a Turabian style is declared you run the **Phase 2.5 Turabian Part III sub-pass** below; when it is not, skip Phase 2.5 and use the Blue Book default throughout. On any conflict, emit `[CONFLICT]`; never silently choose.

---

## What you do

### Phase 1 — Mechanical scan (regex-detectable)

Run these counts on the manuscript (or the section the user specifies). These mirror the `DETERMINISTIC_CHECKS.md` grammar-mechanics work queue; if that pre-filter already ran this cycle, consume its output instead of re-scanning.

| Pattern | Tool | What to flag |
|---|---|---|
| `it's` occurrences | `rg "\bit's\b"` | Each — verify it means "it is"/"it has"; a possessive intent is an error (→ `its`) |
| `its` before a verb | `rg "\bits\b"` | Spot-check for "its is/was" contraction errors |
| Comma-splice candidates | scan: independent clause `, ` independent clause with no conjunction | Flag each for judgment in Phase 2 |
| `which` without a preceding comma | `rg ",?\s*which\b"` | Flag `which` clauses not set off by a comma (restrictiveness check) |
| Series without Oxford comma | scan `X, Y and Z` patterns | Flag per declared style; flag inconsistency always |
| Compound modifier before noun, unhyphenated | scan `well known`, `state of the art`, `X year old` before a noun | Flag candidate missing hyphens |
| `-ly` adverb + hyphen | `rg "\b\w+ly-\w+"` | Flag (incorrect: "highly-regarded") |
| Number style | scan sentence-initial digits; 4+ digit figures without commas; mixed spell-out/figure | Flag inconsistency and sentence-initial digits |
| Possessive plural `'s` / decade `'s` | `rg "\b\d{4}'s\b"`, `rg "s's\b"` | Flag `1990's`, stray possessives |

Record counts in the Phase 3 output block.

### Phase 2 — Judgment pass

Walk the manuscript sentence by sentence. Apply the checks the regex cannot decide:

| # | Check | Source | What to look for |
|---|---|---|---|
| **1** | **Subject–verb agreement** | Blue Book §1.2 | Agreement with the **true** subject across intervening phrases ("the set of results **is**"); `one of those who are` vs. `the only one who is`; indefinite-pronoun singulars (*each, either, neither, everyone*). |
| **2** | **That / which restrictiveness** | §1.4 | Is the clause **essential** (→ `that`, no commas) or **nonessential** (→ `which`, commas)? A wrong choice changes meaning → correctness, not taste. |
| **3** | **Who / whom case** | §1.3 | Subject vs. object; substitute *he/him*. |
| **4** | **Comma splice vs. intended semicolon/colon** | §2.1–2.3 | Two independent clauses joined by a bare comma → semicolon, conjunction, or period. Colon only after a complete clause. |
| **5** | **Semicolon licensing** | §2.2 | Semicolon between full clauses or in comma-laden series; not between a clause and a fragment. |
| **6** | **Coordinate vs. cumulative adjectives** | §2.1 | Comma only when adjective order is interchangeable. |
| **7** | **Hyphenation of compound modifiers** | §2.5 | Hyphen before the noun, not after; suspended hyphens for shared bases; no hyphen after `-ly` adverbs. |
| **8** | **Capitalization / number consistency** | §3–§4 | Title-before-name capitalization; manuscript-internal number-style consistency (defer threshold to declared style). |

**Severity assignment:**
- Wrong that/which changing meaning, subject–verb disagreement, comma splice, or its/it's error → **[MAJOR]**.
- Missing/!inconsistent Oxford comma against declared style, compound-modifier hyphen, capitalization slip → **[MINOR]**.
- Venue-sensitive item where the declared style differs from the Blue Book default → **[CONFLICT]**: flag both, do not silently choose (per `blue_book_grammar_guidelines.md §6`).

### Phase 2.5 — Turabian Part III sub-pass (only when a Turabian style is declared)

Run this phase **only** if `citation_style` is `turabian_author_date` or `turabian_notes_bibliography`. Apply the `turabian_chicago_guidelines.md §5.1` item map. For each item the map assigns to Turabian, Turabian is the authority; where the Blue Book default in Phases 1–2 differs, keep the Turabian rule and emit `[CONFLICT]` naming both so the record shows the divergence was resolved by declared style, not silently.

| # | Item (§5.1) | What to check | Typical severity |
|---|---|---|---|
| **T1** | Numbers (ch. 23, 23.1) | Whole numbers one–one hundred and round multiples spelled out; figures otherwise; internally consistent. Flag threshold violations and mixed style. Percentages/dates/ranges → note "confirm ch. 23" rather than asserting an edge rule. | [MINOR]; [CONFLICT] if it contradicts a Blue Book flag |
| **T2** | Possessives (ch. 20, 20.2) | Turabian possessive formation, including singular nouns ending in *s*. | [MINOR] |
| **T3** | Compounds / hyphenation (ch. 20, 20.3) | Turabian compound rules; no hyphen after *-ly* (shared — not a conflict). | [MINOR] |
| **T4** | Serial comma (ch. 21) | Chicago **requires** it — a missing serial comma is a [MINOR] error here, not a style-preference flag. | [MINOR] |
| **T5** | Title capitalization (ch. 22, 22.3.1) | Headline style for English titles; sentence style for foreign-language titles. Applies to titles of works in prose and captions. | [MINOR] |
| **T6** | Titles of works: italic vs. quotation marks (ch. 22, 22.3) | Larger works (books, journals) italic; smaller works (articles, chapters, poems) in quotation marks — **in prose**, not only in the reference list. Flag a title mention that uses the wrong treatment or is left unformatted. | [MINOR] |
| **T7** | Abbreviations (ch. 24) | Turabian abbreviation form (e.g., *ed.*/*trans.* usage; no plural *-s* when the abbreviation already ends in *s*). Latin abbreviations/units/degrees → note "confirm ch. 24". | [MINOR] |

Do **not** re-adjudicate quotation mechanics (ch. 25 → `citation-format-pass` §4) or table/figure numbering and placement (ch. 26 → `turabian-format-pass`); if you notice an issue there, flag "out of scope — see [that pass]" and move on. The judgment heuristics of Phase 2 (agreement, that/which, who/whom) stay Blue Book-owned even under a Turabian style.

### Phase 3 — Output

```markdown
## Grammar-Mechanics Pass Results (Blue Book)

**File:** <path>
**Scope:** <full file | §§X–Y | lines N–M>
**Declared style:** <citation_style from directives.md | none>
**Date:** <date>

### Mechanical counts
- it's occurrences: <n> (verified contractions: <n>; errors: <n>)
- Comma-splice candidates: <n>
- which-without-comma: <n>
- Series missing/!inconsistent Oxford comma: <n>
- Compound-modifier hyphen candidates: <n>
- Number-style flags: <n>

### Findings (by location)

| # | Location | Check # | Finding | Severity | Proposed fix |
|---|---|---|---|---|---|
| 1 | §X ¶N (line L) | 2 | Nonrestrictive clause introduced with "that", no commas | [MAJOR] | Change to ", which …," or recast |
| 2 | ... | ... | ... | ... | ... |

### Turabian Part III sub-pass (only if a Turabian style is declared)
- Ran: <yes — turabian_author_date | turabian_notes_bibliography | no — non-Turabian/none declared>
- Items flagged: T1 numbers <n>; T2 possessives <n>; T3 compounds <n>; T4 serial comma <n>; T5 title caps <n>; T6 title italic/quotes <n>; T7 abbreviations <n>
- Deferred to manual (edge cases): <list or none>

### Summary
- MAJORs: <n>  MINORs: <n>  CONFLICTs: <n>
- Declared-style conflicts surfaced (not auto-resolved): <list or none>
```

---

## What you do NOT do

- **Do not touch em-dashes.** Em-dash policy is owned by `EMDASH_BUNDLE_DISCIPLINE.md` and `DETERMINISTIC_CHECKS.md §3`. Never propose a new em-dash; if you find an em-dash issue, note "out of scope — see em-dash discipline" and move on.
- **Do not do sentence craft.** Rhythm, focus, voice, and rhetorical structure are `sentence-level-pass` (Bacon). If the prose is grammatically correct but clunky, flag "out of scope — see sentence-level-pass" and stop.
- **Do not legislate citation form.** Reference formatting is `turabian_chicago_guidelines.md` / `citation-format-pass` (when landed); whether to cite is `CITATION_DISCIPLINE.md`.
- **Do not silently resolve venue-sensitive conflicts.** Emit a [CONFLICT] finding and let the declared style or the author decide.
- **Do not rewrite prose wholesale.** Report findings and propose fixes; the Generator applies them, the Evaluator verifies.

---

## When to escalate

If you find **8+ MAJORs** in mechanics, the draft likely needs a full copyedit round rather than a spot pass — recommend running it as part of `/run-iterate --profile refine` so the fixes are logged and re-verified, not applied ad hoc.
