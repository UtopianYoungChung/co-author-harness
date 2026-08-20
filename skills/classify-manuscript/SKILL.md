---
name: classify-manuscript
description: Establish paper type, P-stage (P0/P1/P2), venue, and default final lifecycle phase before review. Emit the machine-readable classification keys consumed by lifecycle and snowball skills. Mandatory first step.
trigger: when the user asks to classify a manuscript, start a review, or determine review depth and gating before evaluation
version: 1.0
---
# Classify Manuscript

You are running the mandatory classification step for the Research and Academic Paper Writing Package. This implements `REVIEW_ORCHESTRATION.md §1` and `§3`. Classification must happen before any review step — it determines which files apply, which items to skip, and whether a G.4 sign-off is required.

## Step 1 — Locate and read the orchestration file

Resolve the Research and Academic Paper Writing Package beneath
`${CLAUDE_PLUGIN_ROOT}`. If that variable is unavailable, locate
`references/REVIEW_ORCHESTRATION.md` from the workspace root the user opened.

Read `references/REVIEW_ORCHESTRATION.md` §1 (the four classification inputs and their options), §3.1 (applicability by paper type), §3.2 (applicability by P-stage), and §3.3 (required steps by lifecycle phase) before proceeding. Do not rely on memory of these tables — they evolve.

## Step 2 — Gather the four classification inputs

If the user has not provided all four inputs, ask for them in a single question. Present the options:

| Input | Options |
|---|---|
| **Paper type** | `theory` · `empirical` · `conceptual/survey` · `essay/positioning` · `response-letter` · `other` |
| **P-stage** | `P0` (phenomenon collection) · `P1` (characterization) · `P2` (research-problem definition) — stage definitions and the wider P/R/K/S/T/V vocabulary: `references/GROUND_TRUTH.md` (binding) |
| **Venue** | journal or conference name, or `course essay`, `thesis chapter`, `cross-venue` |
| **Default final phase** (default `Ph3`) | `Ph1` · `Ph2` · `Ph3` · `Ph4`, per `PHASE_PROTOCOL.md`. Use `Ph3` for ordinary iterative work and `Ph4` when a submission-bound trigger applies. Response letters are a manuscript class within `Ph3`, not a separate tier. |

**If the user declines to classify**, default to: `essay/positioning · P1 · cross-venue · Ph3`.

**Apply `submission-bound` automatically** (and tell the user you did so and why) when the user describes: a final draft for journal/conference submission; a course paper marked *final*; a thesis chapter sent to committee or deposited; any resubmission after reviews; a response letter paired with a revised manuscript.

**Infer from context** where safe (e.g. "I'm submitting to JAIS" → venue = JAIS; "this is my thesis proposal" → P-stage = P2, paper type = essay/positioning), but confirm inferences with the user before producing the classification record.

## Step 3 — Apply the gating tables

Using the four inputs and the tables you read in Step 1, determine for each component file:

1. **Applicability:** Y (fully apply) / Partial (apply named sub-sections only) / N/A (skip, note reason)
2. **Active P-stage tags** for `project_writing_style_checklist.md` (which [P0]/[P1]/[P2] items are in scope, which are deferred, which should already be satisfied)
3. **Required review steps** from the phase table in §3.3
4. **G.4 sign-off required?** (yes when `default_final_phase: Ph4`)
5. **P-stage anti-patterns to watch** (from `project_writing_style_checklist.md` Part 0)

## Step 4 — Emit the classification record

Produce the classification record using this exact template:

```markdown
---
paper_type: [theory | empirical | conceptual/survey | essay/positioning | response-letter | other]
p_stage: [P0 | P1 | P2]
venue: [venue]
default_final_phase: [Ph1 | Ph2 | Ph3 | Ph4]
claim_coverage_threshold: 0.8
inherit_snowball: false
pre_seed_cap: 10
---

# Classification Record

**Piece:** [title or filename, or "untitled"]
**Date:** [ISO date]
**Classified by:** Claude

## Inputs
- `paper_type`: [type]
- `p_stage`: [P0 / P1 / P2]
- `venue`: [venue]
- `default_final_phase`: [Ph1 / Ph2 / Ph3 / Ph4]

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
[Steps required for this lifecycle phase, from REVIEW_ORCHESTRATION.md §3.3. List each by step number and file.]

## G.4 sign-off required?
[Yes / No — and why]

## P-stage anti-patterns to watch
[The anti-patterns from project_writing_style_checklist.md Part 0 that apply at this stage]

## Notes / conflicts
[Venue-specific overrides, advisor instructions mentioned by the user, or ambiguities requiring confirmation before review begins]
```

Save this record to `reviews/classification.md` in the project folder if a project folder path is known. If no project folder exists, present the record in the conversation and ask the user where to save it.

## Step 5 — Hand off to the review

After the user confirms the classification, tell them which skill or step to run next (classification-bound dispatch; skill names phase-named at v0.7.4):
- `run-draft` when the active section is entering `Ph1`.
- `run-iterate --profile refine` for `Ph2` review/revision and ordinary `Ph3` convergence work.
- `run-finalize` when `default_final_phase: Ph4` and the MCR admission requirements are satisfied.
- `response-letter-review` when `paper_type: response-letter`; it runs as a manuscript class within `Ph3`.

Records that carry only retired `review_depth`, `tier`, or display labels such as `Paper type:` / `P-stage:` do not satisfy the machine contract. Re-run this skill to emit the YAML frontmatter above; do not silently infer the missing keys.

## What you do NOT do

- **Do not begin the review itself.** Classification is a precondition. The review starts after the user confirms the classification record.
- **Do not infer paper type from a skim without asking.** Inference errors cascade through the entire review pipeline.
- **Do not skip asking about venue** even if it seems obvious — venue drives precedence overrides.
- **Do not report counts or table lookups from memory.** Read the gating tables in `REVIEW_ORCHESTRATION.md` in this session before applying them.
