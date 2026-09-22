---
name: narrative-structure-pass
description: 'Run a targeted Sexton narrative-structure pass — 10-item arc check covering central need, forward drive, show-then-tell, cause-and-effect, voice, and title. Use when: "structural feedback", "narrative review", "arc check", "does the paper have a through-line", "Sexton pass".'
trigger: when the user asks for structural feedback, narrative review, arc check, opening rewrite, does the paper have a through-line, or Sexton pass
created_by: Reflector
created_from: Tier 2 skill build, 2026-04-11 — Sexton_Fiction_to_Academic_Writing_Guide.md had no standalone entry point
pattern_source: Sexton_Fiction_to_Academic_Writing_Guide.md §§1–10 (Checklist for an Impactful Academic Paper); voice_preservation_guidelines.md (C-7 idiolect carve-out)
version: 1.1
---
# Narrative-Structure Pass (Sexton)

You are running a targeted narrative-structure review on an academic paper. This skill implements Step 5 of the review pipeline as a standalone pass, drawing on `Sexton_Fiction_to_Academic_Writing_Guide.md`.

**Prerequisite:** Read `Sexton_Fiction_to_Academic_Writing_Guide.md` in the package before proceeding.

---

## What you do

### Phase 1 — Read the piece end-to-end

Read the full manuscript (or the sections the user specifies). Do not stop at the abstract — the arc can only be assessed by reading the whole piece.

### Phase 2 — 10-point arc check

For each item, assess the manuscript and assign a verdict: **PASS**, **PARTIAL**, or **FAIL**.

| # | Check | Source | What to look for | Fail = |
|---|---|---|---|---|
| **1** | **One clear "need"** | Sexton §1 | Is the central need (problem, gap, or question) stated early, concretely, and specifically — not as a vague gesture? | [BLOCKER] if no discernible central need by end of §1 |
| **2** | **Forward drive** | Sexton §1 | After stating the need, does each subsequent section advance toward resolution (or toward a refined problem statement at P0/P1)? Or do sections feel episodic and disconnected? | [BLOCKER] if 2+ sections lack forward connection |
| **3** | **Open with impact** | Sexton §6 | Does the opening paragraph use a concrete scenario, a striking gap, or a hook — or does it begin with generic background ("In today's rapidly evolving…")? | [MAJOR] if opening is generic or takes > 2 paragraphs to reach the problem |
| **4** | **Show then tell** | Sexton §2 | For each major claim, is there a concrete illustration within 2 paragraphs? Are long runs of unsupported abstraction avoided? | [MAJOR] per claim lacking concrete grounding |
| **5** | **Concrete and specific** | Sexton §3 | Are methods, constructs, and sources named specifically (not "our approach," "the method," "some scholars")? Are verbs precise (not "addresses," "looks at," "deals with")? | [MINOR] per vague instance |
| **6** | **Cause and effect** | Sexton §4 | Are logical links explicit ("therefore," "because," "as a result")? Do design choices follow from analysis, or do they appear unmotivated? | [MAJOR] per unmotivated jump |
| **7** | **Consistent voice** | Sexton §5 | Is formality level consistent? Is there melodrama ("revolutionary," "completely changes")? Is sentence length varied? **C-7 carve-out:** a feature that recurs in the author's idiolect baseline (flat affect, deliberate repetition, a characteristic length signature) is *consistency*, not a break — do not flag it; name it C-7 idiolect. Flag only genuine *inconsistency* (register that shifts mid-piece) or unearned melodrama. Two guards: protect only *disciplined* idiolect (a recurring genuine weakness is still a finding, not voice), and treat a baseline drawn only from the current draft as *provisional* (note rather than suppress; confirm with the author). | [MINOR] per consistency break (not per idiolect feature) |
| **8** | **Title and roadmap** | Sexton §6 | Is the title informative and specific? Does the introduction include a structural roadmap after the contribution statement? | [MINOR] if title is generic; [MINOR] if roadmap is missing |
| **9** | **Sufficient development** | Sexton §7 | Is the core of the paper (theory, mapping, analysis, example) substantial (~80% of content), or is it thin with a long "future work" section? | [MAJOR] if middle is thin relative to intro+conclusion |
| **10** | **Theme through structure** | Sexton §8 | Does the main contribution emerge organically from the evidence and argument, or is it only declared in the introduction and conclusion (a "bookend" pattern)? | [MAJOR] if contribution is bookend-only |

### Phase 3 — Structural diagnosis

After the 10-point check, write a short structural diagnosis (3–5 sentences):
- What is the dominant structural pattern? (e.g., "The paper has a strong need but episodic development," or "The arc is intact but the opening is buried under two pages of background.")
- Where does the arc break, if it breaks?
- What is the single highest-leverage fix? (The one change that would most improve the paper's readability.)

### Phase 4 — Output

```markdown
## Narrative-Structure Pass Results (Sexton)

**File:** <path>
**Date:** <date>

### 10-Point Arc Check

| # | Check | Verdict | Evidence | Severity |
|---|---|---|---|---|
| 1 | One clear "need" | PASS/PARTIAL/FAIL | <where the need appears, or where it's missing> | — / [BLOCKER] |
| 2 | Forward drive | PASS/PARTIAL/FAIL | <which sections connect and which don't> | — / [BLOCKER] |
| 3 | Open with impact | PASS/PARTIAL/FAIL | <what the opening does> | — / [MAJOR] |
| 4 | Show then tell | PASS/PARTIAL/FAIL | <claims lacking concrete grounding> | — / [MAJOR] |
| 5 | Concrete and specific | PASS/PARTIAL/FAIL | <vague instances> | — / [MINOR] |
| 6 | Cause and effect | PASS/PARTIAL/FAIL | <unmotivated jumps> | — / [MAJOR] |
| 7 | Consistent voice | PASS/PARTIAL/FAIL | <consistency breaks> | — / [MINOR] |
| 8 | Title and roadmap | PASS/PARTIAL/FAIL | <title quality + roadmap presence> | — / [MINOR] |
| 9 | Sufficient development | PASS/PARTIAL/FAIL | <core vs. peripheral ratio> | — / [MAJOR] |
| 10 | Theme through structure | PASS/PARTIAL/FAIL | <how contribution emerges> | — / [MAJOR] |

### Structural Diagnosis

<3–5 sentences: dominant pattern, where the arc breaks, single highest-leverage fix>

### Summary
- BLOCKERs: <n>
- MAJORs: <n>
- MINORs: <n>
- Strengths: <what the paper does well structurally>
```

---

## What you do NOT do

- **Do not edit prose or fix sentences.** This skill checks structure, not sentence craft. For sentence-level issues, recommend `/sentence-level-pass`.
- **Do not check IS-theory elements** (five-element model, nine-step process). Those belong to `/IS-theory-pass`.
- **Do not run deterministic checks.** This is a judgment-based structural review.
- **Do not apply P-stage-specific rules.** If you notice a P-stage mismatch (e.g., P2 vocabulary in a P1 paper), flag it as "out of scope — see `/p-stage-checker`."

## Argument coherence is a narrower question

This pass checks the *document* arc across ten items. It does not check, paragraph by
paragraph, whether each sentence advances the paragraph it sits in, or whether an
edit disconnected an untouched neighbour. Item 2 (forward drive) and item 6 (cause
and effect) are the closest, and both operate at section scale. The paragraph- and
sentence-scale obligation is `SAFEGUARD_LAYER.md` Check 9 under
`references/ARGUMENT_COHERENCE.md`, which runs with a coverage denominator rather
than a ten-item verdict. A PASS on items 2 and 6 is not a coherence result and must
not be reported as one.

## P-stage sensitivity

The Sexton checks apply at all P-stages, but with register adjustments:
- At **P0/P1**: the "resolution" (Check 1) is a **refined problem statement**, not RQ answers. Forward drive means moving toward characterization, not toward answers.
- At **P2**: full resolution with tradeoffs is expected.

If the classification is available in `reviews/classification.md`, read it before starting. If not, ask the user for the P-stage.
