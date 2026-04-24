# EVAL METHODOLOGY — Skill Benchmark Disclosure

**Purpose.** This file documents the methodology behind the benchmark scores reported in `skills/SKILL_REGISTRY.md` for SK-07 through SK-12. Without this disclosure, those scores cannot be cited as evidence of skill efficacy; they are at best internal-confidence indicators. The package's own `research_paper_writing_guidelines.md` §3 would flag undocumented benchmarks as over-claim, and that standard must apply to the package itself.

**Status.** As of 2026-04-13 the existing benchmark numbers in `SKILL_REGISTRY.md` are reclassified from *evidence* to **internal-confidence indicators (ICI)** until this file is populated with the disclosures specified below. Package documentation must reference these scores with the `[ICI — see EVAL_METHODOLOGY.md]` tag.

---

## 1. What an external evidence claim requires

For a benchmark score to function as evidence (not merely confidence), the following must be disclosed:

| Disclosure | Why it matters |
|---|---|
| **Eval set composition** | Number of items, source of items (real manuscripts vs synthetic), domain coverage, P-stage distribution, paper-type distribution |
| **Ground truth construction** | Who labelled the eval items, by what procedure, with what inter-rater agreement (when ≥2 labellers) |
| **Blinding procedure** | Was the labeller blind to the skill's prompt? Was the evaluating model run with and without the skill independently, or comparatively? |
| **Independence between skills** | If multiple skills share the same eval set or the same scoring rubric, this must be stated; correlated scores are not independent evidence |
| **Test-train separation** | Was the eval set used to develop the skill prompt, or held out? Skills tuned on their own eval set produce inflated scores |
| **Random seed / model version** | Which model was used (claude-opus-4-6, claude-sonnet-4-5, etc.); was temperature varied; how many runs averaged |
| **Failure-mode analysis** | What kinds of items did the skill miss? Are there systematic blind spots? |
| **Replication procedure** | A third party should be able to reproduce the score from the disclosed procedure |

Until these are filled in for SK-07–SK-12, the scores in `SKILL_REGISTRY.md` remain **ICI**.

---

## 2. Current benchmark status (as of 2026-04-13)

| Skill | Reported score | Disclosure status | Reclassified as |
|---|---|---|---|
| SK-07 sentence-level-pass | with: 95.2% / without: 42.8% / Δ +0.52 | UNDISCLOSED | ICI |
| SK-08 narrative-structure-pass | with: 95.2% / without: 42.8% / Δ +0.52 | UNDISCLOSED | ICI (note: identical figures to SK-07 — likely shared eval set) |
| SK-09 IS-theory-pass | with: 95.2% / without: 42.8% / Δ +0.52 | UNDISCLOSED | ICI (same as above) |
| SK-10 p-stage-checker | with: 100.0% / without: 41.1% / Δ +0.59 | UNDISCLOSED | ICI |
| SK-11 response-letter-review | with: 100.0% / without: 41.1% / Δ +0.59 | UNDISCLOSED | ICI (likely shared eval set with SK-10) |
| SK-12 grounding-audit | with: 100.0% / without: 41.1% / Δ +0.59 | UNDISCLOSED | ICI (same as above) |

The clustering of identical scores across skills strongly suggests either (a) a shared, small eval set with low ceiling, or (b) a scoring rubric that is too coarse to discriminate between skills. Either possibility limits what these numbers can support.

---

## 3. Required disclosures (to be filled in per skill)

For each skill, complete the following template and store at `skills/packaged/evals/<skill-name>.eval.md`:

```markdown
# Eval Disclosure — <skill-name>

## Eval set
- **Source:** <real manuscripts from project X / synthetic items / mixed>
- **Item count:** <n>
- **Domain coverage:** <list domains and counts>
- **P-stage distribution:** P0 = <n>, P1 = <n>, P2 = <n>
- **Paper-type distribution:** theory = <n>, empirical = <n>, ...

## Ground truth
- **Labeller(s):** <author / second reader / consensus>
- **Procedure:** <how were correct outputs determined>
- **Inter-rater agreement (if ≥2 labellers):** <Cohen's κ or % agreement>
- **Disputed items:** <how were ties broken>

## Blinding
- **Was the labeller blind to the skill prompt?** Yes / No
- **Were with-skill and without-skill runs independent?** Yes / No (if no, explain confound)

## Test-train separation
- **Was this eval set used during skill prompt development?** Yes / No
- **If yes, what fraction was held out for the reported score?** <%>

## Model and runtime
- **Model:** <claude-opus-4-6 / etc.>
- **Temperature:** <value>
- **Runs averaged:** <n>
- **Date of eval run:** <ISO date>

## Independence from other skills
- **Shared eval items with which other skills:** <list>
- **Shared scoring rubric with which other skills:** <list>
- **If shared, what does the per-skill score actually measure?** <explain>

## Score
- **with_skill:** <%>
- **without_skill:** <%>
- **Δ:** <signed delta>
- **95% CI (if computable):** <interval>

## Failure-mode analysis
- **Items missed by the skill:** <pattern>
- **Items the skill incorrectly flagged:** <pattern>
- **Known blind spots:** <list>

## Replication procedure
- **Eval items location:** <path>
- **Scoring script:** <path or procedure>
- **Reproducibility check:** <date last reproduced, by whom>
```

---

## 4. Until disclosure is complete

`SKILL_REGISTRY.md` entries for SK-07 through SK-12 must be edited to:
- Replace `**Eval benchmark:** with_skill X% vs without_skill Y% (Δ +Z)`
- With `**Eval benchmark:** [ICI — see EVAL_METHODOLOGY.md] with_skill X% vs without_skill Y% (Δ +Z)`

This makes the epistemic status of the figures visible at the point of citation. Authors who consult the registry are alerted that the numbers are confidence indicators, not evidence.

---

## 5. Why this matters

The package's own rules forbid presenting unverified claims as verified (`GROUNDING_PROTOCOL.md` Rule 5) and require empirical claims to disclose sample sizes and threats to validity (`research_paper_writing_guidelines.md` §3). Internal benchmark numbers reported without methodology *while the package critiques manuscripts that do the same thing* is the kind of self-exempting move the harness exists to catch. Closing this gap is therefore not optional — it is a coherence requirement.

---

*Created 2026-04-13 as part of the package-tightening pass. Addresses recommendation #2 of `wiki/syntheses/paper-package-evaluation-2026-04-13.md`.*
