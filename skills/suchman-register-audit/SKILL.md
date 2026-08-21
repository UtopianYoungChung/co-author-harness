---
name: suchman-register-audit
description: 'Two-layer audit of Suchman register compliance — seven-move inventory (situated action, plans-as-resources, asymmetric design deployment) plus theoretical-adequacy check for plans/situated action and asymmetric framing. Use when: "Suchman register check", "Suchman-dominant register", Suchman (2007) cited in RE or design work.'
trigger: when a manuscript declares a Suchman-interlocutor or Suchman-dominant register, or when Suchman (2007) is cited in an RE or design paper
created_by: Reflector
created_from: INF3001H Round 4 (2026-04-11)
pattern_source: INF3001H review revealed that Suchman could be cited without the plans/situated action distinction being deployed — a register mis-citation that passes voice audit but fails theoretical adequacy
version: 1.0
---
# Suchman Register Audit

**Purpose.** This skill runs a two-layer evaluation of Suchman register compliance. Layer 1 audits the seven register moves defined in `suchman_writing_style.md §5`. Layer 2 checks theoretical adequacy: whether the Suchman citation is doing load-bearing philosophical work or is merely decorative.

**When to run.** Invoke after any Generator pass on a paper that (a) declares a Suchman-interlocutor register, or (b) cites Suchman (2007) in an RE, HCI, or design paper. Run before SAFEGUARD_LAYER Check 6 (Humanness Voice Audit) — this skill sharpens the Suchman-specific inputs to that check.

**Do not use this skill as a substitute for Check 6.** It is a pre-check that feeds into Check 6, not a replacement for the full voice audit.

---

## Layer 1: Seven-Move Register Inventory

Read `suchman_writing_style.md §5` (Evaluator register summary table). For each of the seven moves, locate the passage in the manuscript where it is (or should be) instantiated.

| Move | What to look for | Verdict |
|---|---|---|
| Move 1 — Interlocutory pivot | Does each section introducing new apparatus open by naming a prior position being refined? | Present / Absent / Partial |
| Move 2 — Hedged-but-committed I | Does "I want to argue/suggest" appear at the argumentative hinge — not sprinkled, not absent? | Present / Absent |
| Move 3 — Cumulative-to-claim architecture | Does qualifying material in long sentences precede and earn a precise main clause? | Present / Absent |
| Move 4 — Principled passive | Are passive constructions used for distributed agency, not deflection? | Present / Weak passive found / N/A |
| Move 5 — "Rather than" reframing | Is there at least one "rather than" pivot at a genuine conceptual reframing? | Present / Absent |
| Move 6 — We/I alternation | Is "we" used for shared epistemic moves and "I" for authorial positions? | Present / Absent / Uniform (flag) |
| Move 7 — Forward-opening paragraph close | Do major paragraphs close with a question or reframing rather than a synthesis announcement? | Present / Absent |

**Output.** List each move with its verdict and the line or passage location. Moves marked Absent are MINOR findings unless they were declared as deferred in the project's AGENTS.md (in which case: note the deferral and do not flag).

---

## Layer 2: Theoretical Adequacy Check

Suchman citation is necessary but not sufficient for Suchman register. A paper can cite Suchman (2007) for "situated action" as background and never deploy the specific theoretical distinction that makes the citation load-bearing.

Run the following two checks:

### Check A — Plans/situated action distinction

**Pattern.** Suchman's core argument is that plans are not programs for action but resources that practitioners interpret and work around in situated practice. A paper that cites Suchman without deploying this distinction is citing her for atmosphere, not argument.

**Procedure.**
1. Search the manuscript for every Suchman citation (any form: `\hyperlink{suchman2007}`, `(Suchman, 2007)`, etc.).
2. For each citation occurrence, read the surrounding passage (± 2 sentences).
3. Ask: does the passage invoke the plans-as-resources-not-programs distinction? Is there explicit engagement with what a plan is versus what it does in situated practice?
4. If yes at least once: mark PASS. If no citation deploys the distinction: mark FAIL with citation locations.

**Severity.** MAJOR if the paper's argument depends on Suchman as a theoretical source (not background citation). MINOR if Suchman is cited only for situated action as a concept without being deployed as a theoretical framework.

### Check B — Asymmetric design argument

**Pattern.** Suchman's analysis of design as an asymmetric relation — where designers project a model of use that cannot be corrected before deployment because situated practice is not available from the design position — is a specific diagnostic claim about the limits of specification. Papers in RE or design that cite Suchman should engage with this asymmetry if they are using her to critique specification-centered approaches.

**Procedure.**
1. Identify whether the paper uses Suchman to critique specification or requirements-centered approaches.
2. If yes: check whether the asymmetric design argument is explicitly invoked — i.e., the paper names the design position and the situated use position as structurally separated, not merely different perspectives.
3. If the paper critiques specification but does not invoke the asymmetry: mark MINOR (missed strengthening argument).
4. If the paper invokes the asymmetry correctly: mark PASS.
5. If the paper does not use Suchman to critique specification: mark N/A.

**Severity.** MINOR (missed opportunity, not an error) unless the paper claims a Suchman-grounded critique of specification without invoking the asymmetry — in which case the claim is unsupported: MAJOR.

---

## Output format

```
## Suchman Register Audit

### Layer 1: Seven-Move Inventory
| Move | Verdict | Location |
|---|---|---|
| Move 1 — Interlocutory pivot | [verdict] | [§X, line N / not found] |
| Move 2 — Hedged-but-committed I | [verdict] | [§X, line N / not found] |
| Move 3 — Cumulative-to-claim | [verdict] | [§X, line N / not found] |
| Move 4 — Principled passive | [verdict] | [§X, line N / not found] |
| Move 5 — "Rather than" pivot | [verdict] | [§X, line N / not found] |
| Move 6 — We/I alternation | [verdict] | [§X, line N / not found] |
| Move 7 — Forward-opening close | [verdict] | [§X, line N / not found] |

Moves absent / partial: [list or none]
Deferred moves (per AGENTS.md): [list or none]
Layer 1 verdict: [All present / N absent — list]

### Layer 2: Theoretical Adequacy
- Check A (plans/situated action): [PASS / FAIL at §X, line N] — [severity if fail]
- Check B (asymmetric design): [PASS / MINOR / MAJOR / N/A] — [reason]

### Overall verdict
- Layer 1: [PASS / N MINORs]
- Layer 2: [PASS / MAJOR / MINOR / N/A]
- Feed to SAFEGUARD_LAYER Check 6: [first-person at hinges = Move 2 result; interlocutory opening = Move 1 result]
```
