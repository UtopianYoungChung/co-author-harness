---
name: p-stage-checker
description: 'Verify a manuscript''s vocabulary, structure, and contribution claims match its declared P-stage (P0 phenomenon collection / P1 characterization / P2 research-problem definition) and flag P2 vocabulary in P1 conclusions. Use when: "P-stage check", "is my P-stage right", "am I writing like a P1 paper", stage drift.'
trigger: when the user asks for P-stage check, stage verification, is my P-stage right, am I writing like a P1 paper, or when register feels mismatched
created_by: Reflector
created_from: Tier 3 skill build, 2026-04-11 — P-stage verification was buried inside the full pipeline with no standalone entry point
pattern_source: project_writing_style_checklist.md Part 0 + REVIEW_ORCHESTRATION.md §3.2
version: 1.0
---
# P-Stage Checker

You are verifying that a manuscript's vocabulary, argument arc, contribution claims, and structural register match its declared P-stage. This skill implements the P-stage gating logic from `project_writing_style_checklist.md` Part 0 and `REVIEW_ORCHESTRATION.md` §3.2 as a standalone check.

**Prerequisite:** Read `project_writing_style_checklist.md` Part 0 (Anti-patterns) and `REVIEW_ORCHESTRATION.md` §3.2 (P-stage gating table) before proceeding.

---

## What you do

### Step 1 — Determine the declared P-stage

Read `reviews/classification.md` if it exists. If not, ask the user. The three stages:

| Stage | Purpose | Output artifact |
|---|---|---|
| **P0** | Collected readings on the problem phenomenon | Bib corpus + bullet points + tags |
| **P1** | Characterization of the problem phenomenon | Synthesis, digest, classification map, tensions |
| **P2** | Definition of research problems / questions / objectives | Specific technical problems (q1, q11, q21…), tradeoffs |

### Step 2 — Vocabulary audit

Scan the manuscript for stage-inappropriate vocabulary. These are the anti-patterns from Part 0:

#### If declared P0 or P1 — check for P2 vocabulary leaking in:

| Pattern | Where to look | Severity |
|---|---|---|
| **Numbered RQs** (RQ1, RQ2, or "Research Question 1:…") in §1 or anywhere | Introduction, Conclusion | [BLOCKER] — premature RQ framing |
| **"Resolution"** as a noun describing the paper's contribution | Conclusion, Abstract | [BLOCKER] — P2 vocabulary in P0/P1 |
| **"Answers"** to research questions | Conclusion, Discussion | [BLOCKER] — P2 vocabulary in P0/P1 |
| **"Research questions" / "research objectives"** as a framing device | Introduction | [MAJOR] — use "problem statement" or "characterization lens" instead |
| **Absence of forward-pointing handoff** | Conclusion | [BLOCKER] — P0/P1 must hand candidate questions forward |
| **Application guidelines** framed as definitive steps | Discussion/Conclusion | [MAJOR] — defer to P2 |

#### If declared P2 — check for P0/P1 vocabulary lingering:

| Pattern | Where to look | Severity |
|---|---|---|
| **No RQs at all** — paper reads as characterization without convergence | Introduction | [BLOCKER] — P2 must commit to specific research problems |
| **"Future work will define the research questions"** | Conclusion | [BLOCKER] — the P2 stage IS the definition |
| **Contribution framed as "a characterization" or "a survey"** without adding resolution | Abstract, Conclusion | [MAJOR] — underclaming at P2 |
| **Missing boundary conditions** | Discussion | [MAJOR] — P2 must specify when the theory applies |

### Step 3 — Argument arc audit

Check whether the paper's arc matches its declared stage:

| Stage | Expected arc | Anti-pattern |
|---|---|---|
| **P0** | Phenomenon → Corpus → Tags + Bullet points → Handoff | Trying to resolve; trying to theorize |
| **P1** | Phenomenon → Characterization lenses → Classification map → Tensions → Forward-pointing handoff (q-α, q-β, q-γ candidates) | Premature resolution; answer-demanding RQs |
| **P2** | Problem → Analysis → RQ answers with tradeoffs → Boundary conditions → Guidelines | Stopping at characterization; vague future-work ending |

### Step 4 — Forward-pointing handoff check (P0/P1 only)

If the manuscript is P0 or P1:
1. Does the conclusion include candidate q-items (q-α, q-β, q-γ or similar forward-pointing notation)?
2. Are the candidates framed as *open questions for later stages*, not as *definitive research questions*?
3. Is the register appropriate? ("These candidate questions will guide the next phase of inquiry" — not "We will answer these questions.")
4. If the handoff is missing entirely, this is a **[BLOCKER]**.

### Step 5 — Contribution framing audit

| Stage | Expected contribution framing | Misframing |
|---|---|---|
| **P0** | "This paper assembles and tags a corpus of…" / "We identify N candidate problem facets…" | Overclaiming resolution or theoretical contribution |
| **P1** | "This paper characterizes the problem of X through lenses A, B, C" / "We surface N tensions…" | Overclaiming resolution; underclaiming (no intellectual contribution beyond collecting) |
| **P2** | "This paper defines research problems q1…qN and demonstrates [approach]" / "We resolve tension T by…" | Underclaiming (characterization without convergence); overclaiming (claims not supported by evidence) |

### Step 6 — Output

```markdown
## P-Stage Verification Results

**File:** <path>
**Date:** <date>
**Declared P-stage:** <P0 | P1 | P2>

### Vocabulary Audit
| # | Pattern found | Location | Expected at | Severity |
|---|---|---|---|---|
| 1 | <e.g., "RQ1" in §1> | <line/section> | P2 only | [BLOCKER] |
| ... | ... | ... | ... | ... |

### Argument Arc
- **Expected arc:** <P-stage expected arc from Step 3>
- **Actual arc:** <what the manuscript actually does>
- **Match:** YES / PARTIAL / NO
- **Findings:** <what breaks the match>

### Forward-Pointing Handoff (P0/P1 only)
- **Present:** YES / NO
- **Register appropriate:** YES / NO
- **Candidate q-items:** <listed or absent>
- **Verdict:** PASS / [BLOCKER]

### Contribution Framing
- **Declared:** <how the paper frames its contribution>
- **Expected for stage:** <what the P-stage demands>
- **Match:** YES / OVERCLAIM / UNDERCLAIM
- **Verdict:** PASS / [MAJOR] / [BLOCKER]

### Summary
- BLOCKERs: <n>
- MAJORs: <n>
- Recommendation: <"Stage is correctly reflected" | "Manuscript reads as P[X] but is declared P[Y] — reclassify or revise">
```

---

## What you do NOT do

- **Do not evaluate theory content.** This skill checks P-stage register, not theoretical adequacy. For theory checks, use `/IS-theory-pass`.
- **Do not propose sentence-level edits.** Report vocabulary findings; the Generator fixes.
- **Do not unilaterally reclassify the manuscript.** If the manuscript reads as a different P-stage, report the discrepancy and let the user or the Planner decide.
- **Do not run this check on response letters.** Response letters do not have P-stages.
