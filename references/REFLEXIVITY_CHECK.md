# REFLEXIVITY CHECK — Authorship Identity Instrumentation

**Purpose.** This file specifies a per-round procedure that surfaces the boundary between *augmentation* (Generator-as-tool) and *substitution* (Generator-as-author) in agent-assisted academic writing. The check exists because the very phenomenon this research program theorises — how delegated AI agency reshapes professional identity — is operative in the author's own use of the harness. Without instrumentation, the substitution boundary is invisible, which makes it impossible to either (a) defend the authorship claim in print or (b) study the phenomenon empirically from the inside.

**Scope.** Run by the Reflector at Phase 2.7 of every reflection round. Mandatory at submission-bound depth; recommended at standard depth.

**Why this is in the package.** The harness is itself an instance of delegated AI agency in knowledge work. Operating it without a reflexivity instrument would be a category mistake — the harness would silently demonstrate the failure mode the research program is meant to address. The check converts that liability into a methodological asset: every round produces a recorded instance of the substitution-vs-augmentation distinction, usable both as authorship discipline and as research material.

---

## 1. Two concepts in tension

| Concept | Definition |
|---|---|
| **Augmentation** | The Generator produces prose that the author has substantively shaped — through plan, prompt, revision, or rejection — and that the author can defend on intellectual grounds the author already held |
| **Substitution** | The Generator produces prose whose substantive direction the author did not shape, and which the author retains primarily because it sounds plausible or saves time |

The distinction is not about word-counts or who typed which character; it is about *whose intentionality* is operative behind a passage. A heavily-edited author-typed paragraph can be substitution (if the editing chased a model suggestion the author did not understand). A model-drafted paragraph can be augmentation (if it discharges an argument the author had already specified at outline level).

---

## 2. The per-round questions

After every Generator round, the Reflector poses the following questions and records the author's answers in `reviews/reflexivity_check.md`. The questions are deliberately concrete; they are not invitations to philosophy.

```markdown
# Reflexivity Check — Round <N>
**Date:** <ISO date>
**Manuscript revision:** <revision number or commit>

## Q1 — Generator-led passages
List passages (by section + first 5 words) where the Generator produced substantive new content rather than executing a plan-specified action.

| Passage | Section | Generator-led? | Author shaped at: |
|---|---|---|---|
| "We argue that..." | §3.1 | YES | outline / prompt / post-hoc edit / not shaped |
| ... | | | |

## Q2 — Substitution flags
For each Generator-led passage, answer:
- Could you defend this passage's specific claims to a reviewer who pressed you on them, **without re-reading the passage**?
- Did this passage assert any commitment you had not previously specified?
- If both Q2.a is "no" and Q2.b is "yes" → mark as **SUBSTITUTION FLAG**.

## Q3 — Resolution actions
For each SUBSTITUTION FLAG, choose one:
- [ ] **Adopt** — the passage articulates a commitment I now endorse on inspection; record the commitment in `research_notes/directives.md`
- [ ] **Revise** — re-write so the commitment matches what I actually hold
- [ ] **Remove** — the commitment is not mine; cut the passage

A round cannot close while any SUBSTITUTION FLAG remains in state "neither adopted nor revised nor removed."

## Q4 — Trajectory metric
- Generator-led passages this round: <n>
- Substitution flags raised: <n>
- Substitution rate (flags / generator-led): <%>
- Resolution mix: adopt = <n>, revise = <n>, remove = <n>

## Q5 — Free-text observation (optional)
What did this round teach you about your own working boundary with the Generator? One paragraph.
```

---

## 3. Trajectory tracking

The Reflector appends one line per round to `.paper-package/REFLEXIVITY_LOG.md` (append-only; created on first run):

```
2026-04-13  R3  generator_led=12  flags=4  rate=33%  adopt=2  revise=1  remove=1
```

A *rising* substitution rate over rounds is a warning signal: the harness may be drifting from augmentation toward substitution. A *falling* rate is also informative — it can mean the author has internalised the model's voice, which is itself a form of identity reshaping worth noting.

---

## 4. Integration with the manuscript

For projects in which the substitution-vs-augmentation distinction is research-relevant (notably Joseph's research program on identity-sensitive RE for human-AI collaboration), `reviews/reflexivity_check.md` becomes a *primary research artifact*, not just a workflow record. The methods section of any paper that uses the harness in its production should disclose:

- That a reflexivity check was run each round
- The aggregate trajectory metric
- A representative example of an adopted commitment, a revised commitment, and a removed commitment

This converts the check from authorship hygiene into reportable methodological transparency.

---

## 5. What this prohibits

- **Silent substitution.** The author may not retain Generator-led passages they could not defend without re-reading. Either the passage is intellectually owned or it is not in the manuscript.
- **Performative reflexivity.** Marking every passage as "augmentation" without engaging Q2 honestly is itself a violation. The Reflector should spot-check by asking the author to defend a randomly-chosen Generator-led passage from memory. If the defence collapses, the rate is wrong.
- **Outsourcing the check to the Generator.** The reflexivity check cannot be performed by the same agent it audits, for the reasons developed in `EXTERNAL_VERIFIERS.md` §1. The author or a separate agent must perform it.

---

## 6. Connection to the research program

This file's procedure operationalises a question the program already studies in others: what does it mean to *author* something when an agent has materially contributed? By making the question concrete and answerable round-over-round, the harness produces an instance of identity-sensitive practice that can be examined alongside the empirical work on PR-lifecycle partitioning (`chung-2026-aiware`) and the i\* modelling of identity dependencies (`chung-2026-identity-req`). The check is therefore both *a control* on the author's own practice *and* *a data source* for the research it serves.

---

*Created 2026-04-13 as part of the package-tightening pass. Addresses recommendation #4 of `wiki/syntheses/paper-package-evaluation-2026-04-13.md`. The recursive identity problem identified in §4.6 of that evaluation is the most consequential gap this file closes.*
