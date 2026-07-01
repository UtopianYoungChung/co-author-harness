---
name: definition-derivation-check
description: 'Run a focused Abbott M-1 pass — for each load-bearing / contested term, decide whether it is derived from the theory''s questions or stipulated by fiat, with the C-6 upfront-glossary carve-in (keys-only glossaries pass; glossaries that pre-state a derived construct''s payoff are flagged). P2-gated. Use when: "definition-derivation check", "did I stipulate or derive this", "M-1 pass", "is my central construct earned", "check my definitions table".'
trigger: when the user asks whether a term was stipulated or derived, for an M-1 pass, whether a central construct is earned, or to check a definitions table / glossary against theory-derivation
created_by: Reflector
created_from: v0.21.0 skill build, 2026-07-01 — the C-8 seven-move pass bundled M-1; the 2026-07-01 QE2026 live-run showed M-1 (upfront-glossary vs. derivation) is a distinct, high-frequency question worth an isolated pass
pattern_source: analytic_construction_guidelines.md §2 M-1 (definitional deferral + C-6 interaction) + §5 (P-stage gating); Abbott 1988
version: 1.0
---
# Definition-Derivation Check (Abbott M-1)

You are running the **single move M-1 (definitional deferral)** from commitment C-8 as an isolated pass. The question is narrow and answerable: **for each load-bearing or contested term, was it *derived* from the theory's questions/framework, or *stipulated* by fiat?** Abbott's rule: "Definitions, then, must follow from theoretical questions" — a derived definition shows its work and stays falsifiable; a stipulated one smuggles the conclusion into the premises.

**Prerequisite:** Read `analytic_construction_guidelines.md §2 M-1` before proceeding — it carries the operational test, the citation-import nuance, and the C-6↔M-1 glossary interaction this skill turns on.

**P-stage gate (check first).** M-1 is a **P2-stage move**. Read the declared P-stage (`reviews/classification.md` or `50_Review/phase_state/classification.md`, or the manuscript frontmatter). If the piece is **P0 or P1**, stop and report: "Out of scope — M-1 (definitional deferral) is a P2 move; deriving vs. stipulating a contested construct is premature at P0/P1, where terms are legitimately still being characterized. See `analytic_construction_guidelines.md §5`." Do not fire M-1 against a phenomenon-collection or characterization piece. If the P-stage is unknown, resolve it (`/classify-manuscript` or ask) before proceeding.

---

## What you do

### Phase 1 — Enumerate the load-bearing terms

Identify the terms the argument actually leans on: the central object/construct, any coined or redefined term, and any term the contribution claim depends on. Ignore ordinary vocabulary. If the piece has an upfront glossary or "terms" preamble, list its entries too — they are the primary M-1 surface.

### Phase 2 — Classify each term's introduction

For each term, decide how it enters the argument:

| Introduction mode | Cue | M-1 verdict |
|---|---|---|
| **Derived** | The term is forced by a stated question/framework/phenomenon ("the questions imply…", "what the case forces is…", "X follows from…", derived through a stated procedure such as a demotion ladder) | ✓ M-1 satisfied — the reader can see *why this definition* |
| **Imported (cited)** | Taken from a settled external source and cited (a standard term borrowed from the literature) | ◐ Acceptable **if** the piece shows *why the case forces this import* rather than a neighbouring one; flag if the import is load-bearing and unmotivated |
| **Stipulated** | Declared by fiat ("We define X as…", "By X we mean…", a bare glossary line for a *contested* construct) with no derivation and no motivating case | ✗ M-1 finding — severity by how central/contested the term is |

### Phase 3 — Apply the C-6 glossary carve-in

An upfront glossary is **not** an M-1 failure per se — a project may run C-6 "one word, one meaning." Apply the rule from `analytic_construction_guidelines.md §2 M-1`:

- **Keys-only glossary entry** (states the single *sense* of the term, defers argument to the body) → **compatible**, no finding.
- **Payoff-pre-stating entry** (defines the very construct the argument exists to *earn* as "= [the conclusion]", so the body's derivation is deflated) → **[MINOR — C-6↔C-8/M-1 interaction]**: recommend demoting the entry to keys-only and letting the body earn the derived content. Name the interaction so the author can adjudicate between the two commitments rather than treating either as neutral.

### Phase 4 — Output

```markdown
## Definition-Derivation Check Results (Abbott M-1)

**File:** <path>
**P-stage:** P2 (confirmed)
**Date:** <date>

### Term-by-term

| Term | Where introduced | Mode (derived / imported / stipulated) | Verdict | Severity | Fix |
|---|---|---|---|---|---|
| <term> | §X / glossary | stipulated | contested central construct declared by fiat; body never derives it | [MAJOR] | Derive from the §X questions; show why this definition is forced |
| <term> | glossary line | keys-only | single sense stated, argument deferred to body | ✓ | — |
| <term> | glossary line | payoff-pre-stated | glossary defines the earned construct as "= [conclusion]" | [MINOR — C-6↔M-1] | Demote to keys-only; let the body earn the derivation |

### Summary
- Derived (✓): <n>   Imported-motivated (◐✓): <n>   Stipulated / unmotivated (✗): <n>
- MAJORs: <n>   MINORs (incl. C-6↔M-1): <n>
- Central-construct verdict: <derived | imported-motivated | STIPULATED — the spine term is not earned>
```

---

## What you do NOT do

- **Do not audit the other six moves.** M-2…M-7 belong to `analytic-move-audit` (the full C-8 pass). If you spot a dissolution or verdict problem, note "out of scope — see `/analytic-move-audit`" and move on.
- **Do not fire below P2.** M-1 presupposes a research problem sharp enough that a contested construct must be earned; at P0/P1 that is premature.
- **Do not treat every glossary as a violation.** The C-6 carve-in is the point of this skill — flag payoff-pre-stating entries, not keys-only ones.
- **Do not rewrite.** Report findings and propose derivations. The Generator rewrites; the Evaluator verifies.
- **Do not present M-1 as neutral hygiene.** Name it (`[MAJOR — C-8/M-1]` or `[MINOR — C-6↔C-8/M-1]`) so the author can dispute the commitment.

## When to escalate

If the **central construct** is stipulated with no derivation, recommend the full pass: "The spine term is not earned — run `/analytic-move-audit` to check whether the surrounding moves (dissolution, verdict) rest on the same un-derived footing."
