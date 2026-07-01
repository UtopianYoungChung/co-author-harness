---
name: dissolution-move-check
description: 'Run a focused Abbott M-2 pass — for each place the argument engages a rival view, check the three-part move: charitable reconstruction, a named buried assumption, and dissolution (reframing the dispute away) rather than mere contradiction or strawman. P2-gated. Use when: "dissolution check", "M-2 pass", "did I strawman this", "am I contradicting or dissolving", "check how I handle rival views".'
trigger: when the user asks whether a rival position was dissolved or merely contradicted, for an M-2 pass, whether an objection was strawmanned, or to check how the argument engages competing views
created_by: Reflector
created_from: v0.21.0 skill build, 2026-07-01 — the C-8 seven-move pass bundled M-2; reconstruct-then-dissolve is the highest-value and most-often-botched theory move, warranting an isolated pass
pattern_source: analytic_construction_guidelines.md §2 M-2 (reconstruct → buried assumption → dissolve) + §5 (P-stage gating); Abbott 1988
version: 1.0
---
# Dissolution-Move Check (Abbott M-2)

You are running the **single move M-2 (reconstruct → locate buried assumption → dissolve)** from commitment C-8 as an isolated pass. Abbott's signature dialectical move: state a rival **charitably and in full**, name the single unexamined assumption it rests on, and **dissolve** the dispute by relocating the question one level up — rather than contradicting the rival head-on. Head-on contradiction produces a standoff (the reader must pick a side on authority); dissolution shows the dispute was ill-posed.

**Prerequisite:** Read `analytic_construction_guidelines.md §2 M-2` before proceeding — it carries the operational test and the charity-is-load-bearing rule (a strawman cannot be dissolved, only knocked over).

**P-stage gate (check first).** M-2 is a **P2-stage move**. Read the declared P-stage (`reviews/classification.md` or `50_Review/phase_state/classification.md`, or the frontmatter). If the piece is **P0 or P1**, stop and report: "Out of scope — M-2 (reconstruct-then-dissolve) is a P2 move. At P0/P1 a piece legitimately *maps* rival positions without resolving them (deliberate non-convergence); demanding dissolution there is a stage error. See `analytic_construction_guidelines.md §5`." **This gate is load-bearing:** a P1 piece that holds two framings open (e.g., an A/B position kept undecided) is doing correct P1 work, not failing M-2. If the P-stage is unknown, resolve it (`/classify-manuscript` or ask) first.

---

## What you do

### Phase 1 — Find every rival-engagement site

Locate each place the argument takes up a competing view, objection, or alternative account — anywhere it says, in effect, "one might think X, but…", rejects a criterion, or positions itself against a default picture. List them.

### Phase 2 — Score the three-part move at each site

For each rival-engagement site, check the three components in order:

| Component | Test | Failure |
|---|---|---|
| **(a) Charitable reconstruction** | Is the rival stated in a form its own proponents would accept — its strongest version, not a caricature? | **Strawman** → the whole move is void; a strawman cannot be dissolved. **[MAJOR]** |
| **(b) Named buried assumption** | Is a *specific* unexamined assumption the rival rests on identified (not just "this is wrong")? | Assumption not named; only the conclusion is denied → weak move. **[MINOR]** |
| **(c) Dissolution vs. contradiction** | Is the dispute *dissolved* — reframed (moved up a level) so it no longer arises — or merely *contradicted* (asserted false)? | Contradiction-without-dissolution of a genuinely contested point → **[MINOR]**; if the point is central, **[MAJOR]** |

**The exemplar to score against** (`analytic_construction_guidelines.md §2 M-2`): a rival is reconstructed at full strength, its buried assumption named, and the dispute dissolved by relocating it into a higher-level variable (Abbott dissolves "claims vs. functions" by recalling that professional structure matters through its effect on survival in a competing system). Reward sites that reach that shape; flag sites that stop at contradiction.

### Phase 3 — Output

```markdown
## Dissolution-Move Check Results (Abbott M-2)

**File:** <path>
**P-stage:** P2 (confirmed)
**Date:** <date>

### Rival-engagement sites

| # | Location | (a) Charity | (b) Assumption named | (c) Dissolved vs. contradicted | Severity | Fix |
|---|---|---|---|---|---|---|
| 1 | §X | strawman — rival stated in weakest form | n/a | n/a | [MAJOR] | Restate the rival at full strength before engaging it |
| 2 | §Y | ✓ charitable | ✗ not named | contradicted only | [MINOR] | Name the buried assumption, then reframe so the dispute dissolves |
| 3 | §Z | ✓ | ✓ | ✓ dissolved (moved up a level) | ✓ strength | — protect this move |

### Summary
- Sites: <n>   Full dissolutions (✓): <n>   Contradiction-only: <n>   Strawmen: <n>
- MAJORs: <n>   MINORs: <n>
- Strongest move: <location — the cleanest reconstruct-then-dissolve>
```

---

## What you do NOT do

- **Do not audit the other six moves.** M-1 and M-3…M-7 belong to `analytic-move-audit` (or `definition-derivation-check` for M-1). Note "out of scope" and move on.
- **Do not fire below P2.** A P1 piece that maps rival positions without resolving them is doing correct non-convergence work — not failing M-2.
- **Do not demand dissolution where contradiction is genuinely warranted.** Some rivals are simply false and a counterexample (M-3) settles them; dissolution is the move for *ill-posed* disputes, not every disagreement. Flag contradiction-only when the point is contested and dissolvable, not when it is decisively refuted.
- **Do not rewrite.** Report findings and propose the reframing. The Generator rewrites; the Evaluator verifies.
- **Do not present M-2 as neutral hygiene.** Name it (`[MAJOR — C-8/M-2: strawman]`, `[MINOR — C-8/M-2: contradicted, not dissolved]`) so the author can dispute the commitment.

## When to escalate

If **2+ sites are strawmen or contradiction-only**, the argument wins by assertion rather than by dissolving its rivals. Recommend the full pass: "Run `/analytic-move-audit` — the rival-handling pattern suggests the definitional (M-1) and verdict (M-5) moves may be resting on the same assert-don't-earn footing."
