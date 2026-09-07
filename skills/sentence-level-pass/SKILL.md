---
name: sentence-level-pass
description: 'Run a targeted Bacon sentence-craft pass on academic prose — a concept-introduction priority gate plus a 10-point checklist covering focus, semantic predication, balance, modification, variety, and rhythm, emitting per-sentence findings with rewrites. Use when: "line editing", "sentence-level feedback", "prose polish", "Bacon pass", "tighten the prose".'
trigger: when the user asks for line editing, sentence-level feedback, prose polish, Bacon pass, fix the sentences, or tighten the prose
created_by: Reflector
created_from: Tier 2 skill build, 2026-04-11 — bacon_2009_well_crafted_sentence_guidelines.md had no standalone entry point
pattern_source: bacon_2009_well_crafted_sentence_guidelines.md §§2–9 + §10 Quick Revision Checklist; voice_preservation_guidelines.md (C-7 idiolect carve-out); EMDASH_BUNDLE_DISCIPLINE.md §1 (B4–B7 jurisdiction boundary)
version: 1.5
---

Rule paths below are package-relative (`references/`), not relative to the input folder. Record the selected rules separately from files read only for context.


## Ordinary task routing

For a bounded read-only pass on pasted text or a file, declare `adhoc_review`
and follow `references/PROJECT_INDEPENDENT_WORKFLOW.md`. Resolve rules from
this package, read the requested input, perform this skill's actual checks,
and return locator-bound findings, counts, rule hashes and limitations.
No project, assignment contract, graph or four-role loop is required.
Optional venue instructions refine the relevant rule. An explicitly supplied
invalid authoritative project binding is a binding error, never silent fallback.
A proposal in findings does not authorize editing the original input.


# Sentence-Level Pass (Bacon)

You are running a targeted sentence-craft review on academic prose. This skill implements Step 4 of the review pipeline as a standalone pass, drawing on `bacon_2009_well_crafted_sentence_guidelines.md`.

**C-8 rhythm guard.** Do not flag C-8/M-4 demonstrative anaphora or C-8/M-5 cadential verdicts as monotony or rhythm defects when they are performing their analytic function. This guard belongs to the sentence/rhythm pass; it does not grant an automatic Sub-check A cadence turn-point.

**Prerequisite:** Read `bacon_2009_well_crafted_sentence_guidelines.md` in the package before proceeding. Do not rely on memory; rules may have changed.

---

## What you do

### Phase 1 — Mechanical scan

Run these counts on the manuscript (or the section the user specifies):

| Pattern | Tool | Threshold |
|---|---|---|
| Sentences > 60 words | grep/count | 0 (each is a finding) |
| Average sentence length | compute | ~15–20 for technical; ~25 for prestige/essay; flag if > 30 |
| Max sentence length | compute | flag if > 50 |
| Consecutive sentences of similar length (±3 words, 3+ in a row) | scan | flag clusters as monotony **unless the pattern recurs in the author's baseline (C-7 idiolect — see carve-out below)**. **Do not assign a numeric burstiness/CV verdict here** — dispersion belongs to B4 (`DETERMINISTIC_CHECKS.md` §4b), which carries no absolute threshold; report the local cluster, not a document statistic |
| Em-dash (U+2014 `—` and LaTeX `---` in body prose) | `rg` count; per-paragraph if needed | **Total** in scope; any paragraph with **2+** em-dashes or **increase** vs. prior version if available → [MINOR] candidate (`research_paper_writing_guidelines.md` §7, `DETERMINISTIC_CHECKS.md` §3). **Rewrites must not** swap commas for em-dashes for “emphasis.” |
| Dummy subjects (*it is*, *there is*, *there are*, *there remain*) | grep | flag each; not all are violations, but each must earn its place |
| Passive voice clusters (3+ consecutive passive clauses) | scan | flag the cluster |

Record counts in the output block (Phase 3).

### Phase 2 — 10-point judgment pass

Walk the manuscript paragraph by paragraph. For each paragraph, check these ten points (derived from Bacon §10 Quick Revision Checklist, with the semantic-predication integrity extension in §3.6):

#### Priority gate — concept introduction and derivation continuity

Run this gate **before** accepting grammatical clarity, rhythm, or semantic predication. A sentence that defines a term fluently can still fail because the term arrives without a reason for appearing.

- **Introduction-provenance test:** For every newly introduced analytical term, category, unit, or field-level generalization, ask: *Where did this term come from?* The preceding prose must identify the problem, entity, distinction, or modelling need that makes the term necessary.
- **Derivation-continuity test:** State the transformation that carries the reader from the prior concept to the new one. When moving from world-level parties to model-level actors, name the modelling operation and its author; do not jump directly to a definition.
- **Scope-authority test:** Reject unsupported formulations such as “the field's working unit,” “the basic unit,” or “the central mechanism” unless the manuscript has established that scope or a source warrants it.
- **Reader reconstruction test:** A careful reader should not have to invent the missing bridge. If the natural response is “Where did that come from?”, the gate fails even when every sentence is grammatical.

An unintroduced construct or unsupported field-level scope claim that changes the analytical frame is **[MAJOR]**. A missing bridge for a secondary, already familiar term is **[MINOR]**. This is a **priority gate**: do not downgrade a failure to style merely because the subsequent definition is accurate.

**Regression example:**

> How those parties enter the analysis is a further step. The field's working unit is the *actor*: a unit constructed within a model and represented as capable of intentional participation.

This fails because *actor* is asserted as the field's unit without being derived from the preceding parties or from a modelling operation. Prefer:

> The next step is to represent those parties in a requirements model. The modeler does so by constructing *actors*: units represented as capable of intentional participation.

| # | Check | Source | What to look for |
|---|---|---|---|
| **1** | **Clarity of focus** | Bacon §3.1–3.2 | In each clause, does the **subject** deserve the spotlight? Are there dummy *it/there* constructions that obscure the real actor? Could a concrete or human subject replace an abstract one? |
| **2** | **Actor/action alignment** | Bacon §3.3–3.4 | Is active vs. passive voice chosen **deliberately** for topic continuity and agency, not by default? Is the agent made explicit when agency matters? |
| **3** | **Parallelism** | Bacon §4.2 | In every series and correlative (*both/and*, *not only/but also*, *either/or*): same grammar, same slot? Are series items of comparable weight? |
| **4** | **Modification quality** | Bacon §5.2–5.3 | Are modifiers (early, medial, cumulative tail) adding precision, or are they dangling? Could a cumulative tail replace a new sentence to tighten the paragraph? |
| **5** | **Post-noun modifiers** | Bacon §6.1–6.7 | Are restrictive vs. nonrestrictive relative clauses punctuated correctly? Could any *who is/which is* be reduced for concision? |
| **6** | **Verbal phrases** | Bacon §7.2–7.4 | Are -ing, -ed, and to- verbals attached clearly? Any dangling modifiers? Any comma-attachment ambiguities? |
| **7** | **Appositives and absolutes** | Bacon §8.1–8.3 | Are there opportunities to define, list, or zoom across details using appositives or absolutes that are currently missed? Are heavy lists serving as subjects? |
| **8** | **Emphasis devices** | Bacon §9.1–9.4 | Are clefts, inversions, or fragments used only where genre and moment support them? Are they absent where they would strengthen a key claim? |
| **9** | **Variety and rhythm** | Bacon §9.5 | Read the paragraph "aloud" (simulate auditory processing). Is there monotonous length or structure? Does the paragraph mix short and long sentences? Is there at least one structural shift (e.g., cumulative after a series of SVO)? |
| **10** | **Semantic-predication integrity** | Bacon §3.6 extension | Apply five tests: **Bearer test** — is the predicate true of the grammatical subject, or only of an ascription, representation, model, or treatment of it? **Contrast-set test** — does a restrictive *that/who* clause imply an unintended class of contrasting cases? **Domain-collocation test** — does the noun phrase name the established domain concept rather than a grammatically possible but misleading state? **Transformation-continuity test** — if the preceding sentence introduces a modelling or analytic act, does this sentence keep that act, rather than the world-level entity, as the bearer of the abstraction? **Conceptual-debt test** — does an image, analogy, example, or figurative phrase create a misleading implication that nearby prose must retract, disclaim, or repair? If so, state the distinction directly and remove the device. |

Classify the use before assigning severity. A clearly rhetorical personification may pass when it is local, recognizable, and carries no definition or inference. The same wording in an analytical, definitional, or model-interpreting claim must pass all five tests; rhetorical license cannot repair a category error in a load-bearing claim.

For research prose, **precision and clarification outrank vividness**. An illustrative phrase does not earn its space merely by being understandable. It must reduce the reader's inferential burden without weakening, widening, or temporarily falsifying the claim. A phrase that creates conceptual debt is a finding even when the following clause successfully repays that debt.

**Severity assignment:**
- Dangling modifier, broken parallelism in a series, or wrong restrictive/nonrestrictive punctuation that changes meaning → **[MAJOR]**
- Dummy-subject pileup (3+ in one paragraph), passive cluster (3+ consecutive), or sentence > 60 words → **[MAJOR]**
- A failed bearer test or conceptual-debt test that changes the sentence's ontological or analytical claim → **[MAJOR]**. A misleading contrast set, domain collocation, or non-load-bearing illustrative detour is **[MINOR]** unless it changes the argument, in which case it is **[MAJOR]**.
- Monotonous rhythm, missed appositive opportunity, or suboptimal active/passive choice → **[MINOR]**
- Genre-sensitive: if a passive or dummy subject is justified by topic continuity or academic convention, it is **not a finding** (Bacon §3.4).

**Regression example (all four tests):**

> The hospital that wants safe patients is a modelling abstraction, not a claim that the institution has the same kind of inner life as a nurse.

Do not clear this sentence merely because *hospital* is a concrete subject. The hospital is world-level; the modelling abstraction is the ascription of wanting. The restrictive *that wants* creates an unintended contrast class, and *safe patients* does not name the domain objective *patient safety*. Prefer:

> Saying that a hospital wants patient safety is a modelling abstraction, not a claim that the institution has the same kind of inner life as a nurse.

### Phase 3 — Output

```markdown
## Sentence-Level Pass Results (Bacon)

**File:** <path>
**Scope:** <full file | §§X–Y | lines N–M>
**Date:** <date>

### Mechanical counts
- Total sentences: <n>
- Average sentence length: <n> words [target: <venue norm>]
- Max sentence length: <n> words at line <L>
- Sentences > 60 words: <n>
- Dummy subjects (it is/there is/there are): <n>
- Passive clusters (3+ consecutive): <n>
- Monotonous-length clusters: <n>
- Em-dashes (— / `---`) in scope: <n> (paragraphs with 2+ flagged in findings)

### Findings (by location)

| # | Location | Check # | Finding | Severity | Proposed fix |
|---|---|---|---|---|---|
| 1 | §X ¶N (line L) | 3 | Broken parallelism in correlative: "not only X but Y" where X is a noun and Y is a clause | [MAJOR] | Recast Y as a noun phrase to match X |
| 2 | ... | ... | ... | ... | ... |

### Summary
- MAJORs: <n>
- MINORs: <n>
- Strengths noted: <any paragraphs with excellent craft — strong cumulative tails, effective inversions, varied rhythm>
```

---

## What you do NOT do

- **Do not restructure the argument.** This skill checks sentence craft, not argument arc. If the arc is broken, flag it as "out of scope — see narrative-structure-pass" and move on.
- **Do not apply rules mechanically against genre.** Bacon §3.4 explicitly notes that academic prose has higher passive-voice and abstract-subject norms than narrative. A passive verb in a methods section is not a finding.
- **Do not rewrite sentences.** Report findings and propose fixes. The Generator rewrites; the Evaluator verifies.
- **Do not run safeguard checks.** This is a craft pass, not a post-review integrity check.
- **Do not flag items already handled by DETERMINISTIC_CHECKS.md** (em-dashes, LLM tics, absolutes). Those are mechanical; this skill is judgment-based. If both overlap, note the overlap and skip the item here.
- **Do not adjudicate B4–B7.** The dispersion bundle (`DETERMINISTIC_CHECKS.md` §4b, `EMDASH_BUNDLE_DISCIPLINE.md` §1) owns document-level rhythm (B4), clause-depth uniformity (B5), circular paragraph closure (B6), and undischarged complexity claims (B7). Report a *local* craft observation if you have one, but do not issue a burstiness verdict, and do not restate a B6/B7 finding as a Check 9 rhythm defect. Where your judgment and a B-rule disagree, say so rather than silently overriding either.

### B5 and Bacon §§5–8 (use the craft, don't duplicate the count)

B5 measures how often material sits between a subject and its predicate. It is a
*count*; the remedy is exactly the craft this skill already teaches — appositives
(Check 7), relative clauses (Check 5), verbal phrases (Check 6), cumulative and
medial modification (Check 4). When a B5 finding arrives with the manuscript, treat
it as a pointer into those checks rather than a separate defect: prose whose subjects
sit adjacent to their verbs throughout is prose that is declining the constructions
Bacon §§5–8 exist to supply. Propose the specific construction at specific sentences;
never propose "add variety."

### C-7 idiolect carve-out (when C-7 is applicable)

Before flagging **monotony**, a **passive cluster**, or a **long sentence** as a craft defect, check it against the author's idiolect baseline (prior accepted prose, or the least-revised passages of the current draft; see `voice_preservation_guidelines.md` §5 and `SAFEGUARD_LAYER.md` Check 6 Step 0):

- **Average, not maximum, governs length.** Per Moran, "average sentence length, not some arbitrary maximum, is what counts. Long sentences and long words are fine so long as they bump up against short ones." Do not impose a per-sentence ceiling; flag length only when the *average* runs high or a long sentence is not relieved by short ones nearby.
- **Repetition can be signature.** "How much a writer tolerates repetition comprises a key part of his voice." Repetition that recurs in the baseline and is not a comprehension defect is idiolect, not monotony.
- A pattern that matches the baseline and carries no comprehension (C-5) cost is **reported as a strength or [INFO]**, not [MINOR] — and named as C-7 ("baseline idiolect, not a defect") so the author can dispute it. Only flag it if it *also* triggers an independent C-5 accessibility defect, and say so explicitly.
- **Two guards on the carve-out.** (1) *Disciplined idiolect only:* recurrence does not protect a genuine defect. A recurring mechanical error (its/it's, dangling-modifier habit) or a surviving LLM tic is still flagged — the carve-out shields a signature the author would defend, not a slip the author would concede. (2) *Provisional baselines don't fully suppress:* if the baseline is drawn only from the least-revised current draft (no accepted prior prose), do not silently suppress the flag — **note** it ("possible baseline idiolect; baseline provisional — confirm with author") and leave it at [MINOR] for the author's judgment.

---

## When to escalate

If you find **5+ MAJORs** in sentence craft, the manuscript likely needs a full review (not just sentence polish). Recommend: "Consider running `/run-tier-standard` (or `/run-tier-submission` if the draft is submission-bound) before investing in sentence-level fixes — structural issues may invalidate the sentences you polish."
