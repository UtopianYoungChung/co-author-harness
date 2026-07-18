---
name: check-contradictions
description: 'Audit a manuscript for unacknowledged theoretical contradictions between co-invoked sources — covers ontological, agency, epistemological, methodological, and terminological conflict types. Use when: "check contradictions", "audit theoretical consistency", "are my sources compatible", before submission.'
trigger: when the user asks to check contradictions, audit theoretical consistency, or verify that co-invoked sources are compatible
created_by: Reflector
created_from: INF3001 Round 1 review, 2026-04-09 — Baumer/i* contradiction was the highest-value BLOCKER
pattern_source: SAFEGUARD_LAYER.md Check 4 (Contradiction Audit)
version: 1.0
---
# Check Contradictions

You are running a targeted contradiction audit on an academic manuscript. This skill implements SAFEGUARD_LAYER Check 4 as a standalone, user-invocable check.

## What you do

1. **Read the manuscript** (`manuscript/main.md` or the file the user specifies) in full.

2. **List every theoretical source that does load-bearing work.** A source is load-bearing if its concepts, frameworks, or vocabulary are used in the argument (not merely cited for context). Produce this list explicitly before checking pairs.

3. **For each pair of co-invoked sources, test for foundational conflicts:**

   | Conflict type | Example |
   |---|---|
   | **Ontological** | Source A assumes entities are stable and bounded; Source B assumes entities are constituted through interaction |
   | **Agency** | Source A defines agency as a property of entities; Source B defines agency as a relation |
   | **Epistemological** | Source A requires intentionality as a condition; Source B dissolves intentionality into situated practice |
   | **Methodological** | Source A uses fixed-schema modeling (stable actor nodes); Source B argues actors are provisional stabilizations |
   | **Terminological** | Source A and Source B use the same term (e.g. "emergence," "delegation") with incompatible definitions |

4. **For each detected conflict, check whether the manuscript:**
   - **(a) Acknowledges** the tension explicitly
   - **(b) Resolves** the tension (reconciliation, reframing, or principled scoping)
   - **(c) Explains** why the conflict does not apply in this context
   - If **none of (a), (b), (c):** flag as **[BLOCKER]** — "unacknowledged theoretical contradiction"
   - If **(a) only** (named but unresolved): flag as **[MAJOR]** — "tension named but unresolved"
   - If **(a) + (b) or (c):** flag as **PASS**

5. **Check project directives.** Read `research_notes/directives.md` and `reviews/DO_NOT_DISTURB.md`. If a contradiction has been deliberately left unresolved as a project decision (e.g. "the paper maps the contradiction rather than resolving it" — Vidal-cartographer register), the finding is PASS provided the manuscript explicitly acknowledges the tension.

## What you output

```markdown
## Contradiction Audit Results

**File:** <path>
**Date:** <date>
**Load-bearing sources identified:** <count>

### Source pairs examined

1. **[Source A] x [Source B]**
   - Conflict type: [ontological / agency / epistemological / methodological / terminological / none]
   - Nature: [one sentence describing the conflict]
   - Acknowledged in manuscript: [yes at §X / no]
   - Resolved or scoped: [yes at §X / no]
   - Verdict: [PASS / MAJOR / BLOCKER]

2. ...

### Summary
- Pairs examined: [n]
- Contradictions found: [n]
- Unacknowledged (BLOCKER): [n]
- Named but unresolved (MAJOR): [n]
- Clean (PASS): [n]
```

## What you do NOT do

- **Do not fix the contradictions.** Report them. The Generator fixes; the Evaluator verifies.
- **Do not flag tensions that the manuscript deliberately maps.** If the project is in a Vidal-cartographer register and the contradiction is the contribution, that is a PASS, not a BLOCKER. Check the directives.
- **Do not check sources that are merely cited for context.** Only audit sources whose concepts do analytical work in the manuscript.
