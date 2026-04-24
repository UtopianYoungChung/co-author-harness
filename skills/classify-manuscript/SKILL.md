---
name: classify-manuscript
description: Establish paper type, P-stage (P0/P1/P2), venue, and tier before any review. Apply gating tables to determine component applicability and required steps. Mandatory first step. Trigger proactively when user begins review, classifies, asks feedback on a draft, or says "classify this paper" or "what review does this need?"
trigger: when the user asks to classify a manuscript, start a review, or determine review depth and gating before evaluation
version: 1.0
---
# Classify Manuscript

You are running the mandatory classification step for the Research and Academic Paper Writing Package. This implements `REVIEW_ORCHESTRATION.md §1` and `§3`. Classification must happen before any review step — it determines which files apply, which items to skip, and whether a G.4 sign-off is required.

## Step 1 — Locate and read the orchestration file

Find the Research and Academic Paper Writing Package. It contains `REVIEW_ORCHESTRATION.md`, `MASTER_research_and_paper_guidelines.md`, and other component files. The canonical Windows path is `B:\Agents\Paper\Package`; in a Cowork session, use Glob to locate `REVIEW_ORCHESTRATION.md` if the path differs.

Read `REVIEW_ORCHESTRATION.md` §1 (the four classification inputs and their options), §3.1 (applicability by paper type), §3.2 (applicability by P-stage), and §3.3 (required steps by review depth) before proceeding. Do not rely on memory of these tables — they evolve.

## Step 2 — Gather the four classification inputs

If the user has not provided all four inputs, ask for them in a single question. Present the options:

| Input | Options |
|---|---|
| **Paper type** | `theory` · `empirical` · `conceptual/survey` · `essay/positioning` · `response-letter` · `other` |
| **P-stage** | `P0` (phenomenon collection) · `P1` (characterization) · `P2` (research-problem definition) |
| **Venue** | journal or conference name, or `course essay`, `thesis chapter`, `cross-venue` |
| **Review depth** | *(retired at v0.5.0 — dispatch reads `tier:` directly; v0.4.x records parse under the transitional mapping below)* |
| **Tier** (default `T3`) | `T0` · `T1` · `T2` · `T3` · `T3R` · `T4` — full ladder active at v0.5.0 per `TIER_PROTOCOL.md §2`. Default `T3` unless the user requests otherwise. **Automatically recommend `T3R`** when `paper_type: response-letter`. **Automatically recommend `T4`** whenever a `submission-bound` trigger applies (see below). Legacy `review_depth` values in v0.4.x classification records are migrated on first read under the transitional mapping `quick↔T1, standard↔T3, submission-bound↔T4`; new classifications do not use `review_depth`. |
| **SD/SR required** (default `false`) | `true` · `false` — whether the Planner must author i\* Strategic Dependency and Strategic Rationale models at T1. Introduced at v0.7.1. Default `false`: SD/SR are **not** generated unless the user explicitly asks for them. Set to `true` only when the user wants GORE/AORE modelling as part of the manuscript. When `false`, T2's SD/SR read-prerequisite and the `E-T2-SD-UNGROUNDABLE` finding silently skip. |

**If the user declines to classify**, default to: `essay/positioning · P1 · cross-venue · T3 · sd_sr_required: false`.

**Apply `submission-bound` automatically** (and tell the user you did so and why) when the user describes: a final draft for journal/conference submission; a course paper marked *final*; a thesis chapter sent to committee or deposited; any resubmission after reviews; a response letter paired with a revised manuscript.

**Infer from context** where safe (e.g. "I'm submitting to JAIS" → venue = JAIS; "this is my thesis proposal" → P-stage = P2, paper type = essay/positioning), but confirm inferences with the user before producing the classification record.

## Step 3 — Apply the gating tables

Using the four inputs and the tables you read in Step 1, determine for each component file:

1. **Applicability:** Y (fully apply) / Partial (apply named sub-sections only) / N/A (skip, note reason)
2. **Active P-stage tags** for `project_writing_style_checklist.md` (which [P0]/[P1]/[P2] items are in scope, which are deferred, which should already be satisfied)
3. **Required review steps** from the depth table in §3.3
4. **G.4 sign-off required?** (yes for `submission-bound`)
5. **P-stage anti-patterns to watch** (from `project_writing_style_checklist.md` Part 0)

## Step 4 — Emit the classification record

Produce the classification record using this exact template:

```markdown
# Classification Record

**Piece:** [title or filename, or "untitled"]
**Date:** [ISO date]
**Classified by:** Claude

## Inputs
- Paper type: [type]
- P-stage: [P0 / P1 / P2]
- Venue: [venue]
- Tier: [T0 / T1 / T2 / T3 / T3R / T4 — default T3; recommend T3R for `response-letter`, T4 on submission-bound trigger]
- SD/SR required: [true / false — default false; set true only when the user explicitly asks for i* Strategic Dependency / Strategic Rationale modelling]

## Component file applicability

| File | Applies | Notes |
|---|---|---|
| general_research_project_guidelines.md | Y / Partial / N/A | [reason if not Y] |
| research_paper_writing_guidelines.md | Y / Partial / N/A | [sections if Partial] |
| baird_2021_writing_guidelines.md | Y / Partial / N/A | [e.g. "Skip — not IS-venue"] |
| bacon_2009_well_crafted_sentence_guidelines.md | Y / Partial / N/A | |
| Sexton_Fiction_to_Academic_Writing_Guide.md | Y / Partial / N/A | [sections if Partial] |
| project_writing_style_checklist.md | Y / Partial / N/A | [active P-stage tags: P0/P1/P2] |

## Required review steps
[Steps required for this depth, from REVIEW_ORCHESTRATION.md §3.3. List each by step number and file.]

## G.4 sign-off required?
[Yes / No — and why]

## P-stage anti-patterns to watch
[The anti-patterns from project_writing_style_checklist.md Part 0 that apply at this stage]

## Notes / conflicts
[Venue-specific overrides, advisor instructions mentioned by the user, or ambiguities requiring confirmation before review begins]
```

Save this record to `reviews/classification.md` in the project folder if a project folder path is known. If no project folder exists, present the record in the conversation and ask the user where to save it.

## Step 5 — Hand off to the review

After the user confirms the classification, tell them which skill or step to run next (tier-bound dispatch — v0.5.0+):
- `run-tier-standard` when the classification record declares `tier: T3` (the default)
- `run-tier-submission` when the classification record declares `tier: T4` (submission-bound)
- `run-tier-reflex` when the classification record declares `tier: T1` (diff-scoped reflex pass)
- `response-letter-review` when the classification record declares `tier: T3R` (response-letter mini-tier)
- For `tier: T0` (state probe only): terminate at the Planner Phase 0 survey; no manuscript-touching skill is dispatched.
- For `tier: T2` (local-scope): the Planner dispatches a scoped Evaluator pass directly; no separate skill entry point.

Archived v0.4.x classification records that carry `review_depth` without a `tier:` field are *not* silently migrated at v0.5.1+: the transitional read-path that mapped `quick ↔ T1`, `standard ↔ T3`, `submission-bound ↔ T4` was retired at v0.5.1. Re-run this skill on any such record to produce a fresh `tier:` field before dispatching. The legacy `/run-full-review` command was retired at v0.5.1.

## What you do NOT do

- **Do not begin the review itself.** Classification is a precondition. The review starts after the user confirms the classification record.
- **Do not infer paper type from a skim without asking.** Inference errors cascade through the entire review pipeline.
- **Do not skip asking about venue** even if it seems obvious — venue drives precedence overrides.
- **Do not report counts or table lookups from memory.** Read the gating tables in `REVIEW_ORCHESTRATION.md` in this session before applying them.
