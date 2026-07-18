# CITATION DISCIPLINE — When to Cite a Term-of-Art Invocation

**Purpose.** This file makes explicit the citation discipline that has been operating implicitly across the harness's manuscripts. The discipline distinguishes **engagement-cite** (a term-of-art invoked because the paper develops arguments specifically about its source-author's claims, or because the term recurs substantively in the paper) from **demarcation-cite** (a term-of-art invoked illustratively to mark a register or tradition the paper does not enter, where the term represents a class rather than a specific construction the paper engages). The two cases call for different citation behaviour.

**Status.** Read by the Generator before any citation-bearing prose action. Read by the Evaluator at Step 4 (citation precision) and at Step 8.5 Sub-check H when the H finding intersects a term-of-art invocation. Cross-referenced from `MASTER_research_and_paper_guidelines.md` (citation-precision rule) and from `READER_ACCESSIBILITY.md` (Sub-check H register-boundary aside guidance).

**Provenance.** Authored 2026-04-30 (v0.13.0) per `docs/superpowers/plans/2026-04-30-voice-and-h-lessons.md` cluster 3.4. Surfaced from the INF3006Y v0.13.0 §2 closing-aside revision where "contract-net protocol coordinating a fleet of warehouse robots" was held to the demarcation-no-cite standard rather than the engagement-cite standard, on the discipline-coherence rationale documented in §3 below.

**Relationship to citation FORM (added 2026-06-28).** This file decides **whether** a citation belongs (engagement vs. demarcation). It does **not** decide **how** the citation is rendered — that is `turabian_chicago_guidelines.md` (style selection, note/bibliography/reference-list form, parenthetical and block-quote placement) and its `citation-format-pass` skill. The two surfaces are orthogonal and both run at Evaluator Step 4: this file first (does the cite belong?), then citation-form conformance (is the existing cite correctly formed?). A missing citation that is a *judgment* question routes here; a malformed *existing* citation routes to `turabian_chicago_guidelines.md`.

---

## 1. The two-question test

A two-question test for any term-of-art invocation in academic prose:

1. **Engagement test.** Will the paper develop arguments specifically about this term's source-author's claims, or will the term recur substantively in the paper across multiple sites? If yes → **engagement-cite**.
2. **Demarcation test.** Is the invocation's purpose to mark a register or tradition the paper does not enter, where the term is illustrative of a class rather than a specific construction the paper engages? If yes → **no cite** (demarcation pattern).

The two tests should be mutually exclusive in practice. A term cannot be both engaged-substantively and merely-illustrative. Borderline cases (the term is engaged once and dropped without further development) lean toward engagement-cite to preserve the principle of "name → cite," at the cost of one extra reference list entry per ambiguous case.

## 2. The two patterns illustrated

### 2.1 Engagement-cite pattern

The §1 / §2 invocation of the term-of-art `tool calls (Schick et al., 2023)` in the INF3006Y manuscript is the canonical case. The phrase "tool calls" is borrowed from a specific source (Schick et al.'s Toolformer paper); the paper engages the underlying argument about how language models invoke external tools; the term appears in the paper's framing of the redistributed-initiative phenomenon and recurs at later sites. Citation at first use anchors the engagement.

The pattern: `[term-of-art] (Author et al., Year)` or `\citep{key}` in LaTeX. Citation at first use; subsequent uses can drop the parenthetical citation since the anchor is established.

### 2.2 Demarcation pattern (no cite)

The §3 invocation of `*incentive-incompatibility*` and the §2 invocation of `contract-net protocol coordinating a fleet of warehouse robots` in the INF3006Y manuscript are the canonical cases. Both are formal-MAS terms-of-art used to mark the tradition the paper does not enter. The paper does not develop arguments about Smith 1980's contract-net construction or about any specific incentive-incompatibility result; the terms are illustrative of a class — the formal-MAS register — rather than a specific construction.

The pattern: italicise the term-of-art (signals term-of-art status per `lay_term_lexicons.md §3.2`); do not cite. The italicisation alone signals the reader that the term is being used in its disciplinary sense without committing the paper to engaging the source.

## 3. Why the distinction matters

The cost of incorrect citation behaviour is asymmetric.

**Citing an illustrative invocation overstates engagement.** If the paper cites Smith 1980 for "contract-net protocol" but does not engage Smith's specific construction, the citation invites a reader-objection: "you cited Smith but did not engage his argument; what was the citation doing?" The over-citation also bloats the reference list with sources the paper does not substantively work with, dilutes the engagement-cite signal, and can mislead a reviewer into expecting more substantive treatment than the paper delivers.

**Failing to cite a substantive engagement-cite under-attributes a load-bearing source.** If the paper invokes "tool calls" without citing Schick et al., a reader cannot trace the term's provenance, the paper appears to be coining a phrase it borrowed, and the engagement with the source is invisible to the bibliometric record.

**The discipline-coherence rationale.** A manuscript should adopt one stance per term-of-art invocation. Mixing patterns (cite some illustrative invocations, leave others un-cited) produces an arbitrary-looking citation surface and signals that the citation discipline is not load-bearing in the paper's argument.

## 4. Edge cases

### 4.1 Engaged-once-and-dropped

When a term appears once, is glossed in passing, and never recurs, the engagement test is borderline. Default behaviour: engagement-cite, unless the term is plainly illustrative (the surrounding prose explicitly demarcates a register the paper does not enter).

### 4.2 Multiple terms-of-art in a single sentence

A sentence that names three or more terms-of-art (e.g., "the formal-MAS literature uses *delegation*, *autonomy*, and *emergence* as stipulated constructs") can apply the demarcation pattern uniformly — cite the cluster as a class, not the individual terms. Acceptable cluster-cite forms: "(see, e.g., Smith 1980; Wooldridge 2002)" at the cluster level rather than per-term.

### 4.3 Recurrence triggered by reviewer revision

A term that started as illustrative (no cite) but became engaged through reviewer revision (the paper now develops an argument about the source) should be retroactively engagement-cited. The Evaluator's Step 4 should flag terms that recurred 3+ times across the manuscript without a citation as engagement-cite candidates.

### 4.4 Cross-reference-only invocations

A term invoked solely to cross-reference another section in the same manuscript ("recall the *configuration* / *intra-action* distinction from §4.3") is neither engagement-cite nor demarcation — it is an in-text cross-reference. Use the section-reference apparatus (`§N`, `Sec. N`, `\ref{label}`) without citing the original source unless the source is being engaged at the cross-reference site.

## 5. Interaction with Sub-check H

When Sub-check H closes a finding on a register-boundary aside (e.g., the §2 / §5 twin-paragraph pattern documented in `lay_term_lexicons.md §5`), the citation behaviour at that aside should be audited as part of the H finding-close. Specifically: if the aside contains terms-of-art and the H suggested-fix introduces or modifies term-of-art invocations, the engagement-vs-demarcation test should be applied to each invocation. The default for register-boundary asides is the demarcation pattern (no cite), per the v0.13.0 INF3006Y precedent.

## 6. Versioning

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-04-30 (v0.13.0) | Initial authoring per source memo `docs/superpowers/plans/2026-04-30-voice-and-h-lessons.md` cluster 3.4. Two-question test, two illustrated patterns, four edge cases, Sub-check H interaction note. |

**Note.** This file is the canonical home for citation-discipline rules. Cross-references in `MASTER_research_and_paper_guidelines.md` and `READER_ACCESSIBILITY.md` should resolve here rather than re-state the rules in prose.
