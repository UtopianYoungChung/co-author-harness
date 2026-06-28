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

## 5. Precedence and conflicts (Part III mechanics ↔ Blue Book)

Turabian Part III (chs. 20–26) and `blue_book_grammar_guidelines.md` both legislate mechanical style (punctuation, possessives, hyphenated compounds, number style, capitalization). They occasionally differ. To keep one authority per decidable item (the discipline-coherence rationale of `CITATION_DISCIPLINE.md §3`):

- **When the project's declared `citation_style` is Chicago/Turabian**, this file is the precedence authority for any mechanical item it legislates (number spell-out thresholds — Turabian 23.1 spells out whole numbers one through one hundred and round multiples; serial comma — Chicago *requires* the Oxford comma; possessives — 20.2; compounds — 20.3). The Blue Book yields on those items but remains the source of the **judgment heuristics** (subject–verb agreement across intervening phrases, that/which restrictiveness) that Turabian states more tersely.
- **When no Chicago/Turabian style is declared**, the Blue Book is the mechanics default and this file governs citation form only.
- A conflict between the declared style and a guideline default is emitted as `[CONFLICT]`, never silently resolved. `grammar-mechanics-pass` and `citation-format-pass` both honor this rule.

## 6. Paper format (Appendix) — pointers
- General format requirements (A.1), specific elements — title page, margins, pagination, headings, block quotations, tables/figures (A.2), and file-preparation/submission (A.3). Treat as a project-level checklist when the venue is thesis/dissertation or a Chicago-styled course paper; defer to explicit venue templates where they exist.
