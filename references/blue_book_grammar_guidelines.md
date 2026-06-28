# Blue Book (Kaufman & Straus): Grammar & Punctuation Mechanics — Extracted Guidelines

**Source:** Kaufman, L., & Straus, J. *The Blue Book of Grammar and Punctuation.* Jossey-Bass/Wiley. Chapters 1–5 (Grammar; Punctuation; Capitalization; Writing Numbers; Confusing Words and Homonyms).

**Note:** This file distills actionable, mechanics-level guidance for academic prose. It is **not** a substitute for the full book, its examples, or its quizzes. Rules were summarized from the plain-text extraction for reuse in copyediting and revision. Where a rule is venue-sensitive (number style, serial comma), the project's declared style governs — see "Precedence and conflicts."

**Raw extraction:** `references/resources/blue_book_grammar_extract.txt`.

**Read by:** the `grammar-mechanics-pass` skill (prerequisite); the Generator before any mechanical/copyedit fix (`AGENT_CONTRACTS.md`); the Evaluator at the copyedit step. Mechanical, regex-detectable items are pre-filtered by `DETERMINISTIC_CHECKS.md`.

**Scope boundary.** This file governs **correctness** (agreement, restrictiveness, punctuation licensing, hyphenation, number style). It does **not** govern rhetoric, rhythm, or sentence craft — that is `bacon_2009_well_crafted_sentence_guidelines.md` / `sentence-level-pass`. It does **not** own em-dash policy — that is `EMDASH_BUNDLE_DISCIPLINE.md` and `DETERMINISTIC_CHECKS.md §3`. On any overlap, defer to those files.

---

## 1. Grammar (Chapter 1)

### 1.1 Finding subject and verb
- Find the **verb** first, then ask **who or what** performs it to find the subject (Rule 1). The subject is not always the noun nearest the verb ("From the ceiling hung the chandelier" — subject is *chandelier*, not *ceiling*).
- A sentence may have multiple subjects and/or verbs (Rule 2). An infinitive (`to` + verb) is **not** the main verb (Rule 3); find the main verb before or after it.

### 1.2 Subject–verb agreement (the highest-value academic check)
- Singular subject → singular verb; plural subject → plural verb. The trap is **intervening phrases**: agreement is with the true subject, not the nearest noun.
- `who`, `that`, `which` take a singular or plural verb depending on their referent (Rule 5): "He is the only one of those men **who is** always on time" (*who* = one) vs. "He is one of those men **who are** always on time" (*who* = men).
- Indefinite pronouns that are singular — *each, either, neither, everyone, everybody, anyone, anybody, no one, nobody, someone, somebody* — take **singular** verbs (Rule 6).

### 1.3 Pronoun case — who vs. whom, whoever vs. whomever
- `who`/`whoever` = subject (nominative); `whom`/`whomever` = object. Test: substitute *he/she* (→ who) vs. *him/her* (→ whom).

### 1.4 That vs. which — restrictive vs. nonrestrictive (load-bearing for meaning)
- **`that`** introduces an **essential (restrictive/defining)** clause — needed to identify the noun; **no commas**.
- **`which`** introduces a **nonessential (nonrestrictive/nondefining)** clause — supplementary information; **set off by commas** (Rule 2b). "Essential clauses do not have commas …; nonessential clauses are introduced or surrounded by commas."
- A wrong choice here changes meaning, so this is a correctness check, not a style preference.

### 1.5 Adjectives, adverbs, prepositions
- Use adverbs (not adjectives) to modify verbs ("she did **well**," not "good"). Watch *good/well*, *bad/badly* after linking vs. action verbs.
- A preposition's object is in the objective case ("between you and **me**").

---

## 2. Punctuation (Chapter 2)

### 2.1 Commas
- **Oxford (serial) comma** (Rule 1): the comma before *and*/*or* in a series. Newspapers often drop it; "fiction and nonfiction books generally prefer" it. **Clarity demands it** where omission causes misreading ("coffee, cheese and crackers, and grapes"). Pick one policy and do not switch — except to add it where omission would confuse.
- Use a comma between **coordinate adjectives** when their order is interchangeable ("a strong, healthy man"); no comma for cumulative adjectives.
- Comma + coordinating conjunction joins two independent clauses; a comma **alone** joining two independent clauses is a **comma splice** (use a semicolon, a conjunction, or a period).

### 2.2 Semicolons
- **Rule 1:** join two closely related independent clauses without a conjunction ("Although they tried, they failed" takes a comma; two full clauses take a semicolon).
- **Rule 2:** use a semicolon before *however, therefore, namely, that is, i.e., for example, e.g., for instance* when they introduce a complete sentence (comma after the connector is preferred).
- **Rule 3:** separate series units when one or more units already contain commas ("Moscow, Idaho; Springfield, California; …").

### 2.3 Colons
- Use a colon to introduce a list, explanation, or amplification after a complete independent clause. Do not split a verb/preposition from its object with a colon.

### 2.4 Apostrophes and possessives
- Possessive of singular nouns: add `'s`; plural nouns ending in *s*: add only `'`.
- **`its`** = possessive; **`it's`** = "it is"/"it has." This is the single most frequent mechanical error and is regex-detectable — Phase 1 flags every `it's`.
- Do not use an apostrophe to form a plural (including decades: *1990s*, not *1990's*).

### 2.5 Hyphens (compound modifiers)
- **Rule 1:** hyphenate a compound adjective **before** the noun ("off-campus apartment," "state-of-the-art design"); usually no hyphen when it **follows** the noun ("the apartment is off campus") unless the compound is always hyphenated.
- **Rule 1b — suspended hyphens** for two or more compounds sharing a base ("latex- and phthalate-free gloves"; "a three- to four-week delay").
- Do not hyphenate an *-ly* adverb + adjective ("a highly regarded scholar," not "highly-regarded").

### 2.6 Dashes
- The book treats em-dashes and en-dashes; **in this harness, em-dash policy is owned by `EMDASH_BUNDLE_DISCIPLINE.md` and `DETERMINISTIC_CHECKS.md §3`.** This file defers entirely. The pass does not propose new em-dashes.

---

## 3. Capitalization (Chapter 3)
- Capitalize proper nouns and proper adjectives; do not capitalize common nouns for emphasis. Capitalize a title before a name, lowercase after ("President Lincoln" vs. "Lincoln, the president"). Follow the project's venue style for headline vs. sentence case in titles/headings.

## 4. Writing numbers (Chapter 4)
- **Rule 1:** spell out any number **beginning a sentence** (or recast the sentence).
- **Rule 2a:** hyphenate compound numbers *twenty-one* through *ninety-nine*; **2b:** hyphenate written-out fractions (*two-thirds*), but not *a third*/*a half*.
- **Rule 3a:** use commas in figures of four or more digits (grouping by threes).
- The spell-out-vs-figures threshold (e.g., one-through-nine vs. one-through-ninety-nine) is **venue-dependent**; defer to the project's declared style (Chicago/Turabian, APA, etc.). The pass flags inconsistency within a manuscript rather than imposing one threshold.

## 5. Confusing words and homonyms (Chapter 5)
- A glossary of commonly confused pairs (*affect/effect*, *lay/lie*, *advice/advise*, *their/there/they're*, *complement/compliment*, *principal/principle*, etc.). Use as a lookup target for Phase-1 homonym flags. Not reproduced here; consult the raw extract or the source.

---

## 6. Precedence and conflicts
- Where the project declares a **citation/style** (`directives.md` `citation_style`) whose manual legislates a conflicting mechanical rule (notably Turabian/Chicago Part III on serial comma, number style, hyphenation), **the declared style governs** and this file yields. The `grammar-mechanics-pass` **flags** such conflicts rather than silently choosing.
- Where no style is declared, this file is the default authority for general academic mechanics and is always the source of the **judgment** heuristics (agreement across intervening phrases, that/which restrictiveness) that terser style manuals state without worked tests.

## 7. Academic-register scoping (what to enforce vs. defer)
- **Always enforce (correctness):** subject–verb agreement, who/whom case, that/which restrictiveness, comma splices, semicolon licensing, its/it's, possessive apostrophes, compound-modifier hyphenation.
- **Enforce for consistency, not absolutely (venue-sensitive):** Oxford comma policy, number spell-out threshold, capitalization of titles/headings — flag *inconsistency* within the manuscript; defer the *choice* to declared style.
- **Do not touch here:** em-dash usage (`EMDASH_BUNDLE_DISCIPLINE.md`), sentence rhythm/voice (`bacon_2009_*`), citation *form* (`turabian_chicago_guidelines.md`, once landed), citation *judgment* (`CITATION_DISCIPLINE.md`).
