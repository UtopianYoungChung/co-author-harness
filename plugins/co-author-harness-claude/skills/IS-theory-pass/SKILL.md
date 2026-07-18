---
name: IS-theory-pass
description: 'Run a targeted Baird IS-theory pass — five-element model (constructs, propositions, logic, boundary, exemplar), nine-step compliance, reviewer lenses, rookie mistakes, red-thread and hourglass structure. Use when: "IS review", "Baird pass", "theory paper check", "IS-venue feedback", theoretical tension.'
trigger: when the user asks for IS review, Baird pass, theory paper check, IS-venue feedback, check the theoretical tension, or five-element check
created_by: Reflector
created_from: Tier 2 skill build, 2026-04-11 — baird_2021_writing_guidelines.md had no standalone entry point
pattern_source: baird_2021_writing_guidelines.md §§2–5 + project_writing_style_checklist.md Part 4 §§10–15
version: 1.0
---
# IS-Theory Pass (Baird)

You are running a targeted IS-theory review on an academic paper. This skill implements Step 3 of the review pipeline as a standalone pass, drawing on `baird_2021_writing_guidelines.md` and the IS-specific sections of `project_writing_style_checklist.md` (Part 4).

**Prerequisite:** Read `baird_2021_writing_guidelines.md` and `project_writing_style_checklist.md` Part 4 (§§10–15) before proceeding.

**Applicability gate:** This skill is designed for papers targeting IS venues (JAIS, MISQ, ISR, ICIS, ECIS, HICSS, or other IS outlets). For non-IS papers (CS, HCI, SE), skip this skill unless the user explicitly requests it. If unsure, ask.

---

## What you do

### Phase 1 — Five-element model check (Baird §2)

Verify that the manuscript communicates all five elements of an IS theory paper. For each element, assess: **PRESENT**, **PARTIAL**, or **ABSENT**.

| # | Element | What to look for | Fail condition |
|---|---|---|---|
| **1** | **Area of theoretical focus** | Is the target IS subcommunity specified? Is there a statement of why this audience should find the topic helpful and interesting? | [MAJOR] if subcommunity is "the IS field" without narrowing |
| **2** | **Relevant background (common ground)** | Does the paper start from what the subcommunity already knows? Does it establish consensus before introducing tension? | [MAJOR] if background is disconnected from the tension |
| **3** | **Theoretical tension** | Is there a clear statement of why new theory (or new characterization at P0/P1) is needed? Does the paper use **assumption challenging** (not just gap-spotting)? | [BLOCKER] if no tension is identifiable |
| **4** | **Resolution of theoretical tension** | Is it clear what the theorizing objective is, what approach is used, and under what boundary conditions the theory holds? | [BLOCKER] at P2 if absent; deferred at P0/P1 |
| **5** | **Guidelines for application** | Does the paper provide concrete steps for future researchers to apply the work? Are future research questions linked to discarded options (not a laundry list)? | [MAJOR] at P2 if absent; deferred at P0/P1 (replaced by forward-pointing handoff) |

### Phase 2 — Nine-step process compliance (Baird §4)

For empirical papers, check each step of the generalized process:

| Step | What to check | Finding if missing |
|---|---|---|
| 1. Core message (five areas) | Are the five areas present even in abbreviated form in the introduction? | [MAJOR] |
| 2. Outline matches target journal | Does the section structure match the first-choice venue's conventions? | [MINOR] |
| 3. Introduction bullets/paragraphs | Does the introduction have approximately one paragraph per area? | [MINOR] |
| 4. Literature synthesis table | Is the lit review structured as synthesis (not inventory)? String citations for consensus? Both classics and recent work? | [MAJOR] if laundry-list lit review |
| 5. Results tables/figures | Are primary results finalized before the narrative? Any **surprise constructs** first appearing in Results? | [BLOCKER] if surprise constructs |
| 6. Discussion outline | Does the discussion address contributions, limitations, and future research? Terminology consistent — no new near-synonyms? | [MAJOR] if new terms appear late |
| 7. Draft body (middle out) | Is the core of the paper (background + theory + results) substantive? | Assessed via narrative-structure-pass; skip here |
| 8. Abstract/Introduction | Do they function as executive summaries that get to the point quickly? Not a mystery novel? | [MAJOR] if contribution is hidden |
| 9. Full tightening pass | Red thread intact? Extraneous text removed? Reader effort manageable? | Assessed in separate passes; skip here |

For **theory papers**, steps 4–5 are replaced by theory-building-approach and new-theory-development checks.

### Phase 3 — Reviewer lenses (Baird §3)

Check whether the manuscript answers the six reviewer questions:

| Lens | Question | Finding if unanswered |
|---|---|---|
| **Who / What** | Who is the target subcommunity? What is the message to them? | [MAJOR] |
| **Why** | Why this focus, this framework, this construct? Why sufficiently new? Are trade-offs surfaced at major decision points? | [MAJOR] |
| **When / Where** | Boundary conditions: when does the theory apply / not apply? Tied to assumptions challenged? | [MAJOR] at P2; [MINOR] at P0/P1 |
| **How** | How should the framework be applied? Guidelines + examples? | [MAJOR] at P2; deferred at P0/P1 |

### Phase 4 — Rookie mistake scan (Baird §5)

Check for the five rookie mistakes Baird identifies:

| Mistake | Indicator | Severity |
|---|---|---|
| **Laundry-list lit review** | Background section reads as study summaries without tying them to the objective and tension | [MAJOR] |
| **Surprise constructs in Results** | New terms, relationships, or constructs appear for the first time in Results/Discussion | [BLOCKER] |
| **Disconnected future-research list** | Future research section is a laundry list disconnected from the paper's design choices and discarded options | [MAJOR] |
| **Cliffhanger introduction** | Introduction withholds the contribution until the end, treating the paper as a mystery | [MAJOR] |
| **Synonyms as enemy** | New near-synonym labels for established constructs appear in later sections (especially Discussion) | [MAJOR] |

### Phase 5 — Red thread and hourglass (Baird §1 + Checklist §10)

| Check | Source | What to look for | Severity |
|---|---|---|---|
| **Red thread** | Baird §1; Checklist §10 | Is the line of reasoning continuously connected from start to finish without fraying? | [BLOCKER] if the thread breaks |
| **Hourglass** | Baird §1; Checklist §10 | Broad (consensus) → Narrow (tension + resolution) → Broad (applications + generalizations)? | [MAJOR] if the shape is absent |
| **Enjoyable but not taxing** | Checklist §10 | Would a reader find the paper cognitively manageable? | [MAJOR] if structure forces excessive effort |

### Phase 6 — Output

```markdown
## IS-Theory Pass Results (Baird)

**File:** <path>
**Date:** <date>
**Paper type:** <theory | empirical>
**Venue:** <target venue>
**P-stage:** <P0 | P1 | P2>

### Five-Element Model
| # | Element | Status | Evidence | Severity |
|---|---|---|---|---|
| 1 | Area of focus | PRESENT/PARTIAL/ABSENT | <where/how> | — / [MAJOR] |
| 2 | Background | PRESENT/PARTIAL/ABSENT | <where/how> | — / [MAJOR] |
| 3 | Tension | PRESENT/PARTIAL/ABSENT | <where/how> | — / [BLOCKER] |
| 4 | Resolution | PRESENT/PARTIAL/ABSENT/DEFERRED | <where/how> | — / [BLOCKER] |
| 5 | Guidelines | PRESENT/PARTIAL/ABSENT/DEFERRED | <where/how> | — / [MAJOR] |

### Nine-Step Compliance (applicable steps)
| Step | Status | Finding | Severity |
|---|---|---|---|
| ... | ... | ... | ... |

### Reviewer Lenses
| Lens | Answered? | Evidence | Severity |
|---|---|---|---|
| ... | ... | ... | ... |

### Rookie Mistakes
| Mistake | Found? | Location | Severity |
|---|---|---|---|
| ... | ... | ... | ... |

### Red Thread and Hourglass
| Check | Verdict | Evidence | Severity |
|---|---|---|---|
| Red thread | INTACT/FRAYED/BROKEN | <where it breaks> | — / [BLOCKER] |
| Hourglass | PRESENT/ABSENT | <shape description> | — / [MAJOR] |
| Cognitive load | LOW/MODERATE/HIGH | <assessment> | — / [MAJOR] |

### Summary
- BLOCKERs: <n>
- MAJORs: <n>
- MINORs: <n>
- Strengths: <what the paper does well from an IS-theory perspective>
```

---

## What you do NOT do

- **Do not check sentence craft.** That is `/sentence-level-pass`.
- **Do not check narrative arc (Sexton).** That is `/narrative-structure-pass`. However, the red thread and hourglass are IS-specific structural checks that overlap with Sexton §1; report them here and note the overlap.
- **Do not run deterministic checks.** This is a judgment-based theory review.
- **Do not check P-stage vocabulary drift.** That is `/p-stage-checker`. If you notice a drift, flag it as "out of scope — see `/p-stage-checker`."
- **Do not apply this skill to non-IS papers** unless the user explicitly requests it.
