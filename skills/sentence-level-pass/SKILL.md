---
name: sentence-level-pass
description: 'Run a targeted Bacon sentence-craft pass on academic prose — 9-point checklist covering focus, balance, modification, variety, and rhythm, emitting per-sentence findings with rewrites. Use when: "line editing", "sentence-level feedback", "prose polish", "Bacon pass", "tighten the prose".'
trigger: when the user asks for line editing, sentence-level feedback, prose polish, Bacon pass, fix the sentences, or tighten the prose
created_by: Reflector
created_from: Tier 2 skill build, 2026-04-11 — bacon_2009_well_crafted_sentence_guidelines.md had no standalone entry point
pattern_source: bacon_2009_well_crafted_sentence_guidelines.md §§2–9 + §10 Quick Revision Checklist; voice_preservation_guidelines.md (C-7 idiolect carve-out)
version: 1.2
---
# Sentence-Level Pass (Bacon)

You are running a targeted sentence-craft review on academic prose. This skill implements Step 4 of the review pipeline as a standalone pass, drawing on `bacon_2009_well_crafted_sentence_guidelines.md`.

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
| Consecutive sentences of similar length (±3 words, 3+ in a row) | scan | flag clusters as monotony **unless the pattern recurs in the author's baseline (C-7 idiolect — see carve-out below)** |
| Em-dash (U+2014 `—` and LaTeX `---` in body prose) | `rg` count; per-paragraph if needed | **Total** in scope; any paragraph with **2+** em-dashes or **increase** vs. prior version if available → [MINOR] candidate (`research_paper_writing_guidelines.md` §7, `DETERMINISTIC_CHECKS.md` §3). **Rewrites must not** swap commas for em-dashes for “emphasis.” |
| Dummy subjects (*it is*, *there is*, *there are*, *there remain*) | grep | flag each; not all are violations, but each must earn its place |
| Passive voice clusters (3+ consecutive passive clauses) | scan | flag the cluster |

Record counts in the output block (Phase 3).

### Phase 2 — 9-point judgment pass

Walk the manuscript paragraph by paragraph. For each paragraph, check these nine points (derived from Bacon §10 Quick Revision Checklist):

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

**Severity assignment:**
- Dangling modifier, broken parallelism in a series, or wrong restrictive/nonrestrictive punctuation that changes meaning → **[MAJOR]**
- Dummy-subject pileup (3+ in one paragraph), passive cluster (3+ consecutive), or sentence > 60 words → **[MAJOR]**
- Monotonous rhythm, missed appositive opportunity, or suboptimal active/passive choice → **[MINOR]**
- Genre-sensitive: if a passive or dummy subject is justified by topic continuity or academic convention, it is **not a finding** (Bacon §3.4).

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

### C-7 idiolect carve-out (when C-7 is applicable)

Before flagging **monotony**, a **passive cluster**, or a **long sentence** as a craft defect, check it against the author's idiolect baseline (prior accepted prose, or the least-revised passages of the current draft; see `voice_preservation_guidelines.md` §5 and `SAFEGUARD_LAYER.md` Check 6 Step 0):

- **Average, not maximum, governs length.** Per Moran, "average sentence length, not some arbitrary maximum, is what counts. Long sentences and long words are fine so long as they bump up against short ones." Do not impose a per-sentence ceiling; flag length only when the *average* runs high or a long sentence is not relieved by short ones nearby.
- **Repetition can be signature.** "How much a writer tolerates repetition comprises a key part of his voice." Repetition that recurs in the baseline and is not a comprehension defect is idiolect, not monotony.
- A pattern that matches the baseline and carries no comprehension (C-5) cost is **reported as a strength or [INFO]**, not [MINOR] — and named as C-7 ("baseline idiolect, not a defect") so the author can dispute it. Only flag it if it *also* triggers an independent C-5 accessibility defect, and say so explicitly.
- **Two guards on the carve-out.** (1) *Disciplined idiolect only:* recurrence does not protect a genuine defect. A recurring mechanical error (its/it's, dangling-modifier habit) or a surviving LLM tic is still flagged — the carve-out shields a signature the author would defend, not a slip the author would concede. (2) *Provisional baselines don't fully suppress:* if the baseline is drawn only from the least-revised current draft (no accepted prior prose), do not silently suppress the flag — **note** it ("possible baseline idiolect; baseline provisional — confirm with author") and leave it at [MINOR] for the author's judgment.

---

## When to escalate

If you find **5+ MAJORs** in sentence craft, the manuscript likely needs a full review (not just sentence polish). Recommend: "Consider running `/run-tier-standard` (or `/run-tier-submission` if the draft is submission-bound) before investing in sentence-level fixes — structural issues may invalidate the sentences you polish."
