---
name: check-abstract-body
description: 'Verify every promise in the abstract and title is paid off in the body, and every construct introduced early is deployed later — catches abstract/body drift and orphaned constructs. Use when: "check abstract-body consistency", "verify title payoff", "did I deliver what the abstract promised", before submission.'
trigger: when the user asks to check abstract-body consistency, verify title payoff, or audit construct deployment
created_by: Reflector
created_from: INF3001 Round 1 review, 2026-04-09 — Haslam taxonomy defined but never operationalized on the loan-officer case
pattern_source: SAFEGUARD_LAYER.md Check 3 (Abstract-Body Consistency)
version: 1.0
---
# Check Abstract-Body Consistency

You are running a targeted consistency check between the abstract/title/opening and the manuscript body. This skill implements SAFEGUARD_LAYER Check 3 as a standalone check.

## What you do

### Part A — Title and Abstract Promises

1. **Read the title.** Extract the key question or claim it implies. (E.g. "Whose Humanness Is Encoded?" implies the paper will answer *whose* humanness, using a specific framework for *humanness*.)

2. **Read the abstract.** Extract 3–5 specific commitments:
   - Methods or approaches named (e.g. "i* modeling," "course materials and cross-talk")
   - Concepts named (e.g. "humanness," "identity-sensitive requirements")
   - Analytical moves promised (e.g. "I trace three tensions," "I show how each bears on an accountability gap")
   - Scope claims (e.g. "problem-setting survey," "disciplinary and analytical contribution")

3. **For each commitment, search the body for its resolution:**
   - **Method/approach:** Does the body actually *use* the method, or only *name* it?
     - "i* modeling" → is there at least one construct mapping (agent, role, dependency) applied to a case?
     - "course materials" → are specific readings named and analytically engaged, not just listed?
   - **Concept:** Is the concept *deployed* on a case or example, or only *defined*?
     - "humanness" with a two-sense taxonomy → are both senses explicitly applied to a specific scenario?
   - **Analytical move:** Is the move actually *performed* in the body?
     - "I trace three tensions" → are three distinct tensions identified, each with evidence?
   - **Scope claim:** Does the body stay within the claimed scope?
     - "problem-setting survey" → does the body avoid P2 vocabulary (resolution, answers, numbered RQs)?

4. **Verdict per commitment:**
   - Resolved (method used, concept deployed, move performed, scope respected): **PASS**
   - Named but not operationalized (defined in §1–2 but vanishes in §§3–5): **BLOCKER** — "title/abstract promise not paid off"
   - Partially resolved (used once but not developed): **MAJOR** — "apparatus under-deployed"

### Part B — Construct Deployment Audit

1. **Extract every formally introduced construct from §§1–2.** A construct is formally introduced if it is:
   - Italicized or bolded and accompanied by a definition
   - Attributed to a specific source with a citation
   - Given a label the paper will use going forward (e.g. "what I call *identity-sensitive requirements*")

2. **For each construct, trace its appearance through the body:**
   - Does it appear in the analytical sections (§§3–5 or equivalent)?
   - Does it do *analytical work* (applied to a case, used to distinguish positions, used to generate a finding)?
   - Or does it appear only in the definition paragraph and the conclusion (a "bookend" pattern)?

3. **Verdict per construct:**
   - Deployed and load-bearing: **PASS**
   - Defined but vanishes (never appears in the analytical sections): **BLOCKER** — "unused apparatus"
   - Bookend only (appears in definition and conclusion but not in the middle): **MAJOR** — "construct not earning its keep in the argument"

### Part C — Roadmap Alignment (if present)

If the introduction includes a section roadmap ("§2 does X, §3 does Y, …"):

1. Compare each roadmap entry to the actual section heading and content.
2. Flag mismatches (roadmap says "§3 develops the modeling apparatus" but §3 is titled "Implications").
3. Verdict: **MINOR** for each mismatch.

## What you output

```markdown
## Abstract-Body Consistency Results

**File:** <path>
**Date:** <date>

### Part A — Title and Abstract Promises
| # | Commitment (from abstract) | Resolved at | Verdict |
|---|---|---|---|
| 1 | [commitment] | [§X / NOT resolved] | [PASS / BLOCKER / MAJOR] |
| 2 | ... | ... | ... |

### Part B — Construct Deployment
| # | Construct (from §§1–2) | Source | Deployed at | Analytical work? | Verdict |
|---|---|---|---|---|---|
| 1 | [construct] | [citation] | [§X / not found] | [yes/no] | [PASS / BLOCKER / MAJOR] |
| 2 | ... | ... | ... | ... | ... |

### Part C — Roadmap Alignment
| Roadmap entry | Actual section | Match? |
|---|---|---|
| [entry] | [heading + content summary] | [yes / MINOR mismatch] |

### Summary
- Abstract commitments: [n total, n resolved, n BLOCKER, n MAJOR]
- Constructs: [n total, n deployed, n unused BLOCKER, n bookend MAJOR]
- Roadmap: [aligned / n mismatches]
```

## What you do NOT do

- **Do not fix the gaps.** Report them. The Generator resolves; the Evaluator verifies.
- **Do not flag constructs that are explicitly deferred.** If a construct is introduced with "developed in future work" or "reserved for P2," that is an intentional deferral, not an unused apparatus. Check the P-stage classification.
- **Do not require every sentence of the abstract to have a body counterpart.** Scope framing ("this paper is a problem-setting survey") is a commitment about register, not about a specific analytical move.
