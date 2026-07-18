# Design Spec: Model Prose Corpus — Accessibility Example Cases (v0.12.0)

**Date:** 2026-04-27  
**Status:** Approved — proceeding to implementation plan  
**Author:** Brainstorming session (Joseph Chung + Claude)  
**Target version:** v0.12.0  

---

## 1. Problem Statement

The `accessibility-overlay` skill (Sub-checks A–H of SAFEGUARD Check 8) currently has an example coverage gap that degrades both human readability of the protocols and Evaluator calibration accuracy:

- Sub-checks A–G have **zero worked examples** anywhere in the package. An Evaluator encountering Sub-check A (cadence) for the first time has no positive anchor for what a CLEAN pass looks like.
- The four worked examples in `READER_ACCESSIBILITY.md §13.4` and the five paraphrase entries in `lay_term_lexicons.md §4` cover **Sub-check H only**, and all nine entries come from a **single manuscript** (INF3006Y) in a **single domain** (i*/GORE). This produces domain overfitting: an Evaluator calibrated exclusively on identity-sensitive requirements engineering prose mis-calibrates on labor sociology, workplace studies, or any other domain the harness encounters.
- A new protocol user reading `READER_ACCESSIBILITY.md` to understand what each check requires finds narrative for Sub-checks A–G but no illustrative prose — a comprehension friction that the addition of examples directly resolves.

**Goal:** Achieve at least a 50% improvement in accessibility-protocol effectiveness, operationally defined as: (a) new protocol users can identify what each Sub-check requires without re-reading the harness governance files; and (b) the Evaluator can adjudicate borderline A–G findings against positive calibration anchors drawn from two domain-diverse model authors.

---

## 2. Theoretical Frame

The design applies Sweller's extraneous-load taxonomy to the protocols themselves. A protocol user who reads Sub-check A's specification ("a paragraph is flagged if it exceeds 150 words and contains no internal turn-point…") must construct a mental model of what a turn-point looks like in real prose. Without a concrete anchor, that construction consumes working memory — extraneous load on the protocol itself. A worked example reduces extraneous load by handing the reader a pre-built mental model they can verify against the specification. The same principle governs the Evaluator: an abstract criterion specification plus a calibration example produces more reliable adjudication than the specification alone.

The model prose selection principle: **Vidal (2022) and Suchman (2007)** are chosen because both authors write complex sociotechnical argument in accessible prose — dense disciplinary content carried in daily-English register. This is the target the harness accessibility criteria are designed to produce. Both texts are in the user's Zotero library and their corpus content has been extracted and verified in this session.

---

## 3. Design: Four Components

### 3.1 Component 1 — `references/examples/model_prose_corpus.md` (new file)

The canonical home for all model-prose calibration examples. Organized by Sub-check A–H. Each Sub-check section has the following four-part structure:

```
## Sub-check [X] — [Name]
**Property being calibrated:** [one-line statement of the specific criterion property]

### Vidal (2022) — Management Divided: Contradictions of Labor Management
**Location:** [chapter + approximate character offset]
**Verbatim passage:**
> [50–120 word verbatim quote]
**Marker audit:** [which criterion property fires, and the exact textual feature that triggers it]
**Annotation:** [1–2 sentences for human readers on why this counts as CLEAN]

### Suchman (2007) — Human-Machine Reconfigurations: Plans and Situated Actions
[same four-part structure]

**Calibration note:** [one sentence: what the two examples together demonstrate that neither alone demonstrates — the contrastive insight]
```

**Versioning discipline:** The file carries a frontmatter block with `version`, `date`, and `source_items` — recording both the Zotero parent item key and the PDF attachment key for each source (Vidal: parent `QH8Y3FE6`, attachment `TKH5M6RK`; Suchman: parent `TJUP6UCB`, attachment `NT26F6GS`). The attachment key is the one used for full-text extraction; the parent key is used for bibliographic lookup. Future additions of model authors append new sub-sections without disturbing existing entries; the Sub-check heading structure is the stable organizing axis.

**Extensibility.** The corpus is designed to grow. When a future project produces an especially clean A–G example, it is appended to the relevant Sub-check section under a `### [Project] ([year])` heading. The Reflector's Phase 4 cross-project recurrence audit is the natural source for new corpus entries: a pattern that fires CLEAN across two or more projects is a corpus-entry candidate.

---

### 3.2 Component 2 — `accessibility-overlay/SKILL.md` amendment

One new MANDATORY instruction added directly after the existing mandatory load block for `READER_ACCESSIBILITY.md`:

```
**MANDATORY — LOAD MODEL PROSE CORPUS.** After loading `READER_ACCESSIBILITY.md`, 
load `references/examples/model_prose_corpus.md`. The corpus provides one CLEAN 
example per Sub-check A–H from Vidal (2022) and Suchman (2007). Use them as 
positive calibration anchors when adjudicating borderline findings: if a passage 
is structurally similar to a corpus example and the criterion property is present, 
default toward CLEAN; if the passage lacks the property clearly present in the 
corpus example, escalate toward MAJOR.
```

This is a single addition, co-located with the existing mandatory load, so it is encountered on every overlay invocation without any routing change.

---

### 3.3 Component 3 — `accessibility-overlay/references/sub_checks.md` per-sub-check cross-references

At the end of each Sub-check definition (A through H), one line is appended:

```
> *Model examples → `references/examples/model_prose_corpus.md §Sub-check [X]`*
```

This ensures the calibration anchor is visible at the exact decision point — the Evaluator reading the Sub-check B specification while adjudicating a rhythm finding sees the pointer to the two rhythm examples without requiring a separate file-load decision.

**No content is duplicated.** The pointer is a reference, not a copy. `sub_checks.md` remains the authoritative operational specification; the corpus remains the authoritative example source.

---

### 3.4 Component 4 — `READER_ACCESSIBILITY.md §13.4` pointer paragraph

A short paragraph inserted at the top of the existing §13.4 section, before the current four worked H examples:

```
**Sub-check A–G examples.** The four worked examples below cover Sub-check H 
(Register Appropriateness) only. Worked examples for Sub-checks A–G — paragraph 
cadence, sentence rhythm, first-use definition, section signposting, jargon 
discipline, worked-example placement, and consolidation anchors — are collected 
in `references/examples/model_prose_corpus.md`, organized by Sub-check with 
passages from Vidal (2022) and Suchman (2007). Read that file when you need a 
positive model for any A–G check.
```

This closes the comprehension gap for human readers: a new protocol user who opens `READER_ACCESSIBILITY.md` to find out what each check requires is immediately directed to the example resource rather than finding only H coverage.

---

## 4. Corpus Content (pre-verified)

The following passages were extracted from the Zotero full-text corpus (Vidal key `TKH5M6RK`; Suchman key `NT26F6GS`) in the design session and verified against the Sub-check criteria. These are the entries that populate the corpus file at implementation.

### Sub-check A — Paragraph Cadence

**Vidal:** Ch.1 ~offset 15,600. "Across a wide range of sectors, managers today face conflicting pressures…" Discipline-pole then empowerment-pole, pivoting at "On the other hand." Turn-point is structural and symmetrical.

**Suchman:** Ch.5 ~offset 195,800. Abstract-view passage pivoting at "So, for example" into the canoe-rapids vignette. Turn-point is a register shift from theoretical declarative to first-person narrative.

**Calibration note:** Both are CLEAN; one uses structural symmetry, the other uses a register-shift pivot — demonstrating that multiple surface forms satisfy the cadence criterion.

### Sub-check B — Sentence-Length Variation

**Vidal:** Ch.2 ~offset 140,400. Milkman/GM Linden passage: 26-word framing → 30-word embedded citation with direct quote → blunt 28-word conclusion. The quoted phrase "relentless and dehumanizing" acts as a short emphatic pulse inside the long sentence.

**Suchman:** Ch.1 ~offset 31,200. Xerox copier origin: three long accumulation sentences (40–50 words each) then "It seemed that customers were refuting this message, however" (12 words) — length drop enacts the ironic reversal.

**Calibration note:** Vidal's variation is intra-sentence (the embedded quote creates a short pulse); Suchman's is inter-sentence (full-length drop). Both satisfy rhythm; the Evaluator should not over-specify the surface form.

### Sub-check C — First-Use Definition

**Vidal:** Ch.3 ~offset 190,300. "The valorization process is about the production and appropriation of surplus labor — output beyond that necessary to cover a worker's wages." Plain-English gloss via em-dash, on the same sentence as first use.

**Suchman:** Ch.7 ~offset 210,000. "Indexical" introduced only after two sentences explain situated significance vs. conventional meaning — the concept arrives before the label.

**Calibration note:** Vidal's model is definition-in-sentence (gloss embedded via em-dash); Suchman's is definition-before-term (concept pre-loaded before the label). Both are CLEAN; the criterion does not require a particular syntactic form.

### Sub-check D — Section-Opening Signpost

**Vidal:** Ch.2 ~offset 120,100. Names two camps (boosters vs. critics), announces Vidal's own conclusion up front, then maps the internal chapter sequence. Reader finishes knowing the destination and the route.

**Suchman:** Ch.5 ~offset 144,000. "This chapter and the next discuss two alternative views of action." Names both views, locates them across chapters, assigns each chapter's function explicitly.

**Calibration note:** Vidal's signpost is argumentative (announces a conclusion); Suchman's is structural (assigns chapter roles). Both satisfy D; a signpost need not announce a conclusion — assigning function is sufficient.

### Sub-check E — Jargon Discipline

**Vidal:** Ch.1 ~offset 25,200. Management-contradiction paragraph: two domain terms ("labor discipline," "abstract cognitive labor power"), both immediately glossed; all other vocabulary plain English. Complexity is structural (three-part parallel), not lexical.

**Suchman:** Ch.6 ~offset 202,200. Normative-sociology paragraph: two domain terms ("social facts" / "received norms"; "normative sociology"), first glossed immediately. Latin "vis-à-vis" is used as a preposition, not a term of art.

**Calibration note:** Both paragraphs make complex theoretical points with only two new terms. The Evaluator should audit term count, not sentence-level density.

### Sub-check F — Worked Example at Density Spike

**Vidal:** Ch.2 ~offset 140,700. GM Linden, New Jersey plant (named, attributed to Milkman 1997) appears within two sentences of the abstract causation claim about work intensification preceding lean.

**Suchman:** Ch.4 ~offset 134,800. ELIZA/DOCTOR programs (named, Weizenbaum's lab) appear immediately after abstract claims about intentional explanation and machine intelligence. Specific role (Rogerian therapist) and specific mechanism (keyword scanning) are named.

**Calibration note:** Both examples name specific institutions/artifacts. A gestural reference ("as seen in workplace studies…") would be MINOR; named specificity is what makes an example do argumentative work rather than illustrative decoration.

### Sub-check G — Consolidation Anchor

**Vidal:** Ch.3 ~offset 210,300. Five-move forward anchor: "I begin with… Next… Following this… Finally…" Names the theory-building moves ahead; functions as forward consolidation at the review-to-theory boundary.

**Suchman:** Ch.5 ~offset 143,800. Opening paragraph simultaneously closes Ch.4's argument, names both alternative views, and assigns Ch.5–6 roles. Functions as both backward (names what was established) and forward (assigns next two chapters).

**Calibration note:** Vidal's anchor is purely forward (maps next moves); Suchman's is bidirectional (closes prior and maps next). The criterion requires only the two functions — naming accumulated material AND signalling next move — not a specific syntactic form.

### Sub-check H — Register Appropriateness

**Vidal:** Preface ~offset 4,800. Managers cross-training workers, workers participating in problem solving. All agents act on concrete things; plain connectives ("To be sure… but"); no nominalised stack.

**Suchman:** Ch.1 ~offset 30,200. PARC origin story: named year (1979), named institution, real agents (customer service managers, doctoral student), plain connectives ("began when," "in response to"). No passive abstractions.

**Calibration note:** Vidal's passage is a theoretical reframing (explaining what the research found that didn't fit existing theory) delivered in daily English; Suchman's is a research-history narrative. Both non-technical passage roles satisfy H via concrete agents acting on concrete things.

---

## 5. File-Change Surface

| File | Change type | Scope |
|---|---|---|
| `references/examples/model_prose_corpus.md` | New file | ~350 lines |
| `accessibility-overlay/SKILL.md` | Append to mandatory block | 6 lines |
| `accessibility-overlay/references/sub_checks.md` | Append one pointer per Sub-check | 8 lines (one per A–H) |
| `READER_ACCESSIBILITY.md` | Insert pointer paragraph at §13.4 top | 7 lines |

Total new content: ~371 lines. No existing lines are deleted; all changes are strictly additive.

---

## 6. Success Criteria

A 50% improvement in accessibility-protocol effectiveness is operationally measurable at two levels:

**Human-reader level:** A new user of the harness, reading the protocol files without prior context, can correctly identify one CLEAN example for each Sub-check A–H without escalating to the full governance documentation. Currently achievable for H only (four worked examples exist); after implementation, achievable for all eight.

**Evaluator calibration level:** On a manuscript outside the i*/GORE domain (e.g., a labor-sociology or workplace-studies manuscript), the Evaluator's first-pass Sub-check adjudications are consistent with the criterion specification without requiring human correction on Sub-checks A–G. Currently the Evaluator has no positive anchor for A–G in non-GORE domains; after implementation, it has two per check.

---

## 7. Constraints and Non-Goals

- **Not a content dilution.** The corpus examples are drawn from PhD-register books on complex sociotechnical topics. They demonstrate that accessible prose and intellectual density are compatible — exactly the distinction `READER_ACCESSIBILITY.md §13.4` makes between dilution and register craft.
- **Not a style guide override.** The corpus is calibration material, not a replacement for `bacon_2009`, `suchman_writing_style.md`, or `baird_2021`. Those govern Generator production; the corpus governs Evaluator adjudication.
- **No new Sub-checks, no threshold changes.** This design is purely additive. The Sub-check A–H operational specifications in `sub_checks.md` are not modified; only cross-reference pointers are added.
- **No per-project override mechanism.** That is deferred to v0.10.3 per the Q4 adjudication in `lay_term_lexicons.md`. The corpus is package-tier, not project-tier.

---

## 8. Relationship to Existing Package

| Existing component | Relationship |
|---|---|
| `READER_ACCESSIBILITY.md §13.4` | Gains a pointer paragraph directing A–G readers to the corpus; its H examples are unchanged |
| `lay_term_lexicons.md §4` | Unchanged; its INF3006Y paraphrase table remains the canonical H-marker transformation reference |
| `accessibility-overlay/SKILL.md` | Gains one MANDATORY load instruction for the corpus |
| `accessibility-overlay/references/sub_checks.md` | Gains eight one-line cross-reference pointers |
| `references/examples/INF3001_walkthrough.md` | Unchanged; the corpus is a calibration reference, not a walkthrough |
| `references/examples/CAiSE_Rev01_walkthrough.md` | Unchanged; same rationale |

---

*Spec authored during brainstorming session 2026-04-27. Implementation plan to follow via `writing-plans` skill.*
