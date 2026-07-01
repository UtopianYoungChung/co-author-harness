---
name: analytic-move-audit
description: 'Run a targeted Abbott analytic-construction pass on theory-building prose — audits the seven M-moves (definitional deferral, reconstruct-then-dissolve, counterexample-as-demolition, anaphoric demonstration, cadential verdict, calibrated confidence, meta-reflexivity) that assemble a claim, emitting per-move findings with rewrites. Use when: "analytic-move audit", "Abbott pass", "is my argument earned", "did I stipulate or derive this", "check my theory-building", theory-contribution review.'
trigger: when the user asks for an analytic-move audit, an Abbott pass, whether the argument is earned rather than asserted, whether a definition is derived or stipulated, or a theory-construction review
created_by: Reflector
created_from: v0.20.0 skill build, 2026-07-01 — analytic_construction_guidelines.md (C-8) had no standalone entry point; the analytic-move layer between Bacon (C-2) and Baird (C-4) had no reviewer
pattern_source: analytic_construction_guidelines.md §2 (M-1…M-7) + §5 (P-stage gating, severity); Abbott 1988, The System of Professions
version: 1.0
---
# Analytic-Move Audit (Abbott)

You are running a targeted **analytic-construction** review on theory-building prose. This skill implements commitment **C-8** as a standalone pass. It audits the layer between the sentence (Bacon / `sentence-level-pass`) and the whole-piece arc (Sexton / `narrative-structure-pass`), and between the theory's static anatomy (Baird / `IS-theory-pass`) and its voice (Suchman / C-7): **the rhetoric of the individual analytic move — how a single claim is won.**

**Prerequisite:** Read `analytic_construction_guidelines.md` in the package before proceeding. Do not rely on memory; the seven moves, their operational tests, and the P-stage gating are defined there.

**Applicability gate (check first).** C-8 applies to any piece that **builds or extends a theory or a conceptual argument** — including advisor-facing conceptual **briefs and working drafts toward a proposal** that stake a theoretical position. **The genre label does not decide this**: a "memo" or "brief" that builds a conceptual argument is in scope; the presence of the argument decides, not the filename. Stop and report out of scope only for a *pure logistics/status memo*, a *methods note*, an *empirical-results section that reports rather than argues*, a *response letter*, or a *P0/P1 phenomenon-collection piece*: "Out of scope for C-8 — this piece does not build a theoretical argument. See `analytic_construction_guidelines.md` §5." If the P-stage is unknown, read the project `reviews/classification.md` (or `50_Review/phase_state/classification.md`), run `/classify-manuscript`, or ask before proceeding. A conceptual brief that deliberately holds positions open is in scope but is audited only on the stage-neutral moves (M-3/M-5/M-6) per the P-stage gate.

---

## What you do

### Phase 0 — P-stage gate

Read the declared P-stage (from `reviews/classification.md` or the frontmatter). Then restrict the move set:

| P-stage | Moves in scope |
|---|---|
| P0 / P1 (phenomenon / characterization) | M-3, M-5, M-6 only (stage-neutral). M-1, M-2, M-7 are **premature** — firing them is itself a stage error. |
| P2 (research-problem / theory contribution) | All of M-1 … M-7. |

If the piece is P2 but a section is doing P1 work (a characterization passage), scope that section down accordingly and say so.

### Phase 1 — Move-by-move judgment pass

Walk the manuscript. For each analytic move (each place a claim is being established), apply the operational test from `analytic_construction_guidelines.md §2`:

| Move | What to look for | Failure condition |
|---|---|---|
| **M-1 Definitional deferral** | Each load-bearing / contested term: is it **derived** from a stated question or framework, or **stipulated** ("We define X as…")? An upfront terminological glossary is fine if **keys-only**; flag only entries that pre-state a *derived* construct's payoff (C-6↔M-1 interaction — see `analytic_construction_guidelines.md §2 M-1`). | A contested central construct stipulated by fiat with no derivation → **[MAJOR]**; a glossary that pre-announces a derived construct's conclusion → **[MINOR — C-6↔C-8/M-1]** |
| **M-2 Reconstruct → dissolve** | At each engagement with a rival view: (a) charitable reconstruction? (b) named buried assumption? (c) dissolved (reframed away) vs. merely contradicted? | Strawman reconstruction → **[MAJOR]**; contradiction-without-dissolution of a genuinely contested point → **[MINOR]** |
| **M-3 Counterexample as demolition** | Where a rival category/criterion is rejected, is there a **specific** case it mis-sorts, or only abstract objection? | Rejection on abstraction alone where a counterexample was available → **[MINOR]** |
| **M-4 Anaphoric demonstration** | Parallel-framed instances after a general claim ("Thus X… Thus Y… Thus Z…") — treat as **argumentative structure** | Flag **only** if instances do not support the generalization (evidential defect). **Never** flag the repetition as monotony — protect it (see carve-out) |
| **M-5 Cadential verdict** | Does each completed move close on a short, unqualified declarative that lands the point? | Move trails off into further qualification with no verdict → **[MINOR]** |
| **M-6 Calibrated confidence** | Is confidence **graded to the evidence** and are judgment calls marked as decisions? | Uniform confidence across claims of visibly different warrant (over-claiming the weak / under-claiming the strong) → **[MAJOR]** |
| **M-7 Meta-reflexivity** | (P2 only) Does the apparatus examine its own assumptions at least once? | Total absence of reflexivity in a theory-building piece → **[MINOR]** (ADVISORY below P2) |

**Opening check (M-1 support).** Read the section/piece opening: does the **phenomenon drive the theory** (situated case → question → framework, the Abbott/Manteno move), or is the theory announced and then illustrated (definition-first / literature-review-first cold open)? Report the latter as an M-1 opening weakness, cross-referencing C-3 (Sexton show-then-tell).

### Phase 2 — Output

```markdown
## Analytic-Move Audit Results (Abbott / C-8)

**File:** <path>
**Scope:** <full file | §§X–Y>
**P-stage:** <P0 | P1 | P2>  → moves in scope: <list>
**Date:** <date>

### Findings (by move)

| # | Location | Move | Finding | Severity | Proposed fix |
|---|---|---|---|---|---|
| 1 | §X ¶N | M-1 | Central construct "X" stipulated ("We define X as…") with no derivation from the stated questions | [MAJOR] | Derive X from the §1 questions, as `analytic_construction_guidelines.md §2 M-1`: show why the framework forces this criterion |
| 2 | §Y ¶M | M-2 | Rival view stated only to be contradicted ("but this is wrong because…") — no buried assumption named, dispute not dissolved | [MINOR] | Reconstruct the rival charitably, name its assumption, reframe so the dispute dissolves |
| ... | ... | ... | ... | ... | ... |

### Strengths noted
<moves executed well — a clean dissolution, a well-chosen counterexample, a landed verdict, graded confidence — named so the Generator does not "improve" them away>

### Summary
- MAJORs: <n>
- MINORs: <n>
- ADVISORY: <n>
- Moves out of scope (P-stage gated): <list>
```

---

## What you do NOT do

- **Do not audit sentence craft.** Focus, parallelism, modification, and clause-level rhythm belong to `sentence-level-pass` (C-2). If the prose is broken below the move level, note "out of scope — see sentence-level-pass" and move on.
- **Do not audit the theory's static anatomy.** Whether the five-element model (phenomenon → artefact → mechanism → outcome → contribution) is complete belongs to `IS-theory-pass` (C-4). C-8 audits how the moves *assemble* those elements, not whether the elements are present.
- **Do not audit the whole-piece arc.** The red thread and section-to-section drive belong to `narrative-structure-pass` (C-3).
- **Do not rewrite.** Report findings and propose fixes. The Generator rewrites; the Evaluator verifies.
- **Do not fire P2 moves against a P0/P1 piece.** M-1, M-2, M-7 presuppose a research problem sharp enough to argue; firing them early is a stage error (cf. `p-stage-checker`).
- **Do not present C-8 as neutral hygiene.** Name the move in every finding (`[MAJOR — C-8/M-1: …]`) so the author can dispute the commitment, not just the finding. C-8 is a suspendable methodological stance (`analytic_construction_guidelines.md §5`).

### M-4 / M-5 carve-outs (protect argumentative features)

C-8 protects two features the mechanical craft checks can mis-read — the mirror image of C-7's idiolect carve-out:

- **M-4 demonstrative anaphora is not monotony.** Parallel-framed instances ("Thus… Thus… Thus…") that support a general claim are *evidence*, not a rhythm defect. If `sentence-level-pass` flagged them, overturn that flag here and record the anaphora as a strength. Flag only an **evidential** failure (the instances don't support the claim).
- **M-5 cadential verdict is not clutter.** A short declarative resolving a long qualifying period is doing argumentative work. A "concision" or accessibility edit that merges it back into the period or deletes it must cite an independent warrant — otherwise it is an M-5 regression. If a prior pass removed a verdict, flag the removal.

---

## When to escalate

If you find **3+ M-1/M-2/M-6 MAJORs**, the manuscript's argument is under-built, not just under-polished. Recommend: "The claims are asserted rather than earned — consider a `/run-iterate` structural pass before line-level work, and confirm the P-stage with `/classify-manuscript`; polishing un-earned claims wastes the polish."
