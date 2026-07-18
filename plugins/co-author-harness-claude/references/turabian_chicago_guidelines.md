# Turabian / Chicago: Citation Form & Mechanical Style — Extracted Guidelines

**Source:** Turabian, K. L. *A Manual for Writers of Research Papers, Theses, and Dissertations: Chicago Style for Students and Researchers* (rev. Booth, Colomb, Williams, Bizup, FitzGerald). University of Chicago Press. Part II (Source Citation, chs. 15–19), Part III (Style, chs. 20–26), Appendix (Paper Format and Submission).

**Note:** This file distills citation *form* and mechanical *style* for academic prose. It is **not** a substitute for the full manual's source-type templates (chs. 17 and 19 cover dozens of specific source types). Rules were summarized from the plain-text extraction for reuse in copyediting and citation conformance.

**Raw extraction:** `references/resources/turabian_chicago_extract.txt`.

**Read by:** the `citation-format-pass` skill (prerequisite); the Evaluator at Step 4 (citation precision) alongside `CITATION_DISCIPLINE.md`; the Generator before any citation-formatting fix.

**Scope boundary — the critical orthogonality.** This file governs the **form** of a citation: which style, which fields, what punctuation and ordering. It does **not** govern **whether** to cite — that judgment (engagement-cite vs. demarcation-cite) is owned by `CITATION_DISCIPLINE.md` and must stay separate. `CITATION_DISCIPLINE` decides *that a citation belongs*; this file decides *how it is rendered*. It also does **not** own grammar mechanics shared with the Blue Book — see "Precedence and conflicts" (§5).

---

## 1. The two citation styles (ch. 15.3) — choose one, apply consistently

Turabian/Chicago offers **two** systems; a paper uses exactly one throughout (15.3): 

- **Notes-Bibliography (NB)** — humanities and some social sciences. Superscript note numbers point to footnotes/endnotes; a bibliography lists sources at the end.
- **Author-Date (AD)** — most social, natural, and physical sciences. Parenthetical in-text citations point to an end-of-paper reference list.

"Within a specific paper, however, always follow a single style consistently." The project's declared `citation_style` in `research_notes/directives.md` selects the system; the pass flags any mixing.

## 2. Notes-Bibliography basic form (ch. 16.1)

All notes share one general form. First (full) note, shortened subsequent note, and bibliography entry differ in form:

- **Full note (N):** `1. Jaron Lanier, You Are Not a Gadget: A Manifesto (New York: Alfred A. Knopf, 2010), 5.`
- **Shortened subsequent note (N):** `5. Lanier, Not a Gadget, 133–34.` — author last name, short title, page. Use for every citation after the first to the same source.
- **Bibliography entry (B):** `Lanier, Jaron. You Are Not a Gadget: A Manifesto. New York: Alfred A. Knopf, 2010.` — same information as the full note, but author surname-first, period-delimited, no parentheses around publication facts.

Bibliography ordering: alphabetical by author surname. For two or more works by the same individual, arrange alphabetically by title (ignoring *a*/*the*) and replace the repeated name with a **3-em dash** in entries after the first (16.2; 21.7.3).

## 3. Author-Date basic form (ch. 18)

- **Parenthetical (in text):** author + year + page — `(Lanier 2010, 5)`. Placed next to the reference, before the sentence's terminal punctuation for a run-in quotation.
- **Reference list entry:** author surname-first, year directly after the author — `Lanier, Jaron. 2010. You Are Not a Gadget: A Manifesto. New York: Alfred A. Knopf.`
- The reference list includes every source cited parenthetically (and sometimes others consulted).

## 4. Quotations (ch. 25)

- **Run-in quotation:** integrated into the sentence with quotation marks; the parenthetical citation precedes the closing period (AD) or the note number follows the closing punctuation (NB).
- **Block quotation:** longer prose set off without quotation marks; **the parenthetical citation follows the terminal punctuation mark** — `… after the revolution itself and what will remain after it. (Tocqueville 2000, 673)`. Note the period precedes the parenthesis in a block quote (the opposite of a run-in quote).
- Quote accurately; mark modifications with brackets and ellipses (25.3); avoid plagiarism by attributing paraphrase as well as exact words (15.2.1: cite when you quote, when you paraphrase a source-specific idea, and when you use any idea, data, or method attributable to a source).

## 5. Mechanical style — precedence and the Part III item map (Part III ↔ Blue Book)

Turabian Part III (chs. 20–26) and `blue_book_grammar_guidelines.md` both legislate mechanical style (punctuation, possessives, hyphenated compounds, number style, capitalization, titles, abbreviations). They occasionally differ. To keep one authority per decidable item (the discipline-coherence rationale of `CITATION_DISCIPLINE.md §3`):

- **When the project's declared `citation_style` is Chicago/Turabian**, this file is the precedence authority for any mechanical item Part III legislates (see the §5.1 map). The Blue Book yields on those items but remains the source of the **judgment heuristics** (subject–verb agreement across intervening phrases, that/which restrictiveness, who/whom case) that Turabian states more tersely or leaves to general usage.
- **When no Chicago/Turabian style is declared**, the Blue Book is the mechanics default and this file governs citation form only.
- A conflict between the declared style and a guideline default is emitted as `[CONFLICT]`, never silently resolved. `grammar-mechanics-pass` and `citation-format-pass` both honor this rule.

### 5.1 Part III item map — the mechanical items Turabian owns when declared

This map is the grounded authority `grammar-mechanics-pass` consults for its Turabian Part III sub-pass. Each row gives the Turabian locus, the **headline rule** (only rules verified against the manual/extract are stated as rules; finer edge cases are marked *confirm ch. N*), and the precedence disposition. Sub-section numbers are cited only where verified; chapter-level citations are used otherwise, per the Grounding Protocol (no invented numbers).

| Domain | Turabian locus | Headline rule | Disposition when Turabian is declared |
|---|---|---|---|
| **Numbers** | ch. 23 (23.1) | Spell out whole numbers one through one hundred and round multiples; use figures otherwise; be internally consistent. Percentages, dates, and inclusive/elided ranges — *confirm ch. 23*. | Turabian precedence over the Blue Book spell-out threshold. |
| **Possessives** | ch. 20 (20.2) | Turabian/Chicago possessive formation, including singular nouns ending in *s*. | Turabian-owned. |
| **Compounds / hyphenation** | ch. 20 (20.3) | Turabian compound-modifier rules; no hyphen after an *-ly* adverb (shared with Blue Book §2.5). | Turabian precedence on any divergence; hyphen-after-*-ly* is a shared rule, not a conflict. |
| **Serial (Oxford) comma** | ch. 21 | Chicago **requires** the serial comma. | Turabian precedence — resolves the Blue Book's "flag per declared style" to *required*. |
| **Other punctuation** | ch. 21 | Chicago punctuation conventions. | Shared surface; Turabian precedence on any legislated divergence, Blue Book keeps the judgment heuristics. |
| **Title capitalization** | ch. 22 (22.3.1) | Headline style for English-language titles; sentence style for foreign-language titles; proper nouns capitalized. | Turabian-owned for titles of works (distinct from title-before-name capitalization, a shared prose rule). |
| **Titles of works: italic vs. quotation marks** | ch. 22 (22.3) | Larger works (books, journals) in italics; smaller works (articles, chapters, poems) in quotation marks. | Turabian-owned. Already applied to citation form in §§2–3; this row extends the same rule to **in-prose** title mentions. |
| **Abbreviations** | ch. 24 | Turabian abbreviation form (e.g., *ed.*/*trans.*; spelled out when introducing a name, abbreviated when concluding; no plural *-s* when the abbreviation already ends in *s*). Latin abbreviations, units, and degrees — *confirm ch. 24*. | Turabian-owned. |
| **Quotations (mechanics)** | ch. 25 (25.1–25.3) | Accurate quotation; run-in vs. block set-off; brackets and ellipses for permissible modifications. | Covered in **§4** above — cross-reference, do not duplicate. |
| **Tables / figures (mechanics)** | ch. 26 | Table-note and figure conventions. | Numbering, caption, and placement are owned by `turabian-format-pass` (§6); the *wording form* of a source/note follows ch. 26. Cross-reference §6. |

**Boundary reminder.** This map governs mechanical **style** under a declared Turabian style. It does not touch *whether* to cite (`CITATION_DISCIPLINE.md`), the *form* of a reference entry (§§1–4), document *layout* (§6), em-dash policy (`EMDASH_BUNDLE_DISCIPLINE.md`), or sentence *craft* (`sentence-level-pass`).

## 6. Paper format (Appendix A) — operationalized by `turabian-format-pass`

Appendix A governs the paper's **physical presentation**: general format requirements (A.1); specific elements — title page, margins, pagination, headings, block quotations, tables/figures (A.2); and file-preparation/submission (A.3). This is the *format* layer, distinct from the citation *form* of §§1–4 and the mechanical *style* of §5.

**Enforcing skill.** `skills/turabian-format-pass/SKILL.md` (SK-45) runs this Appendix as a conformance pass. It audits **structure, ordering, and internal consistency** — heading-level hierarchy and per-level consistency, front-matter presence and order, title-page elements, and table/figure numbering + caption + in-text call-out + source placement — and emits a **deferred checklist** for the physical values the Markdown source cannot carry (margins, spacing, pagination, submission format). By design it does **not** assert absolute measurements as Turabian requirements; those are set by the manual and, above it, by the institution or venue.

**Applicability and precedence.** The pass is gated on `d_style_profile.harness_profile`: in scope for `thesis_qe` and Chicago/Turabian course papers. Under `venue_submission`, the `venue_template_precedence` obligation (`scripts/d_style_profile_check.py`) makes the venue template the format authority — the pass shrinks to venue-independent structure. Treat Appendix A as the fallback when no venue or institution format spec exists.

**Style selection.** The D-STYLE `citation_style` enum carries both Turabian systems — `turabian_author_date` and `turabian_notes_bibliography` (the latter added 2026-07-01) — so a notes-bibliography project can now declare its style and have both `citation-format-pass` (§§1–4) and `turabian-format-pass` (§6) resolve against it.
