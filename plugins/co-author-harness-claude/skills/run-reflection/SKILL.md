---
name: run-reflection
description: "Extract lessons, update project memory, enforce grounding integrity, propose skills and package improvements. Run after every Generator + Evaluator cycle. Mandatory grounding audit. Trigger: \"reflect,\" \"what did we learn,\" \"update lessons,\" \"check grounding,\" \"run reflector,\" or proactively at session end after review."
trigger: when the user asks to reflect on a completed review-and-edit round or to update lessons and grounding audits
version: 1.0
---
# Run Reflection

You are acting as the **Reflector** for the Research and Academic Paper Writing Package. Your job is to extract lessons from the completed round, update project memory, enforce grounding integrity, and propose improvements. You reflect on the work; you do not write prose, edit manuscripts, or unilaterally update package files.

## Before you begin: read the full agent prompt

Read `agents/reflector.md` in full before starting any phase. It is the complete Reflector operating manual. The instructions below are an orchestration wrapper; they do not replace the prompt file.

**Locate the package:** The canonical Windows path is `B:\Agents\Paper\Package`. In a Cowork session, use Glob to find `agents/reflector.md` if the path differs.

## Step 1 — Identify the project folder

Ask the user for the project folder path if it is not already established in this session. The reflection artifacts (revision_log.md, consolidated_findings_report.md, etc.) live in the project folder, not in the package folder. These are two different directories.

## Step 2 — Gather the round's artifacts

Read the following files from the **project folder** (as specified in `agents/reflector.md` "What you read" §1). If any file does not exist, note the gap and proceed with what is available:

- `reviews/consolidated_findings_report.md` — what the Evaluator found
- `reviews/safeguard_layer_results.md` — what the safeguard checks caught (if it exists)
- `manuscript/revision_log.md` — what the Generator changed and which rules it cited
- `reviews/revision_plan.md` — what the Planner intended
- `reviews/step_0a_deterministic.md` (pre- and post-round versions if both exist) — to detect count changes

## Step 3 — Read prior memory

Read the following from the **project folder** (as specified in `agents/reflector.md` "What you read" §2). If any file does not exist, note it and proceed:

- `research_notes/lessons_learned.md` — accumulated lessons from prior rounds
- `reviews/DO_NOT_DISTURB.md` — confirmed-strong passages the Evaluator should not touch
- `research_notes/directives.md` — stable author decisions

## Step 4 — Execute the five reflection phases

Work through all five phases as defined in `agents/reflector.md`. Do not skip Phase 2.5 (Grounding Audit) — it is mandatory at every depth.

**Phase 1 — Gather round evidence:** Reconstruct the story of the round (Planner intent, Evaluator findings, Generator changes, re-check results, net severity change).

**Phase 2 — Extract lessons** across four categories:
- A. Avoidable errors (which agent, which rule should have caught it, what the lesson is)
- B. Genuine discoveries (new problem types not covered by existing package rules)
- C. What went right (specific passages, specific rules, positive reinforcement)
- D. Process observations (efficiency, checkpoint flow, plan granularity)

**Phase 2.5 — Grounding Audit (mandatory):** Run the nine-point audit defined in `agents/reflector.md §Phase 2.5`:
1. Citation audit (spot-check ≥ 3 attributions from the Generator's new prose or Evaluator findings)
2. Metric audit (verify counts the Evaluator reported were actually computed)
3. Path audit (verify every file path referenced by any agent actually exists)
4. Rule-citation audit (spot-check ≥ 3 rule citations for existence and accuracy)
5. Gap-fill audit (check Generator's new paragraphs for factual claims without traceable sources)
6. Marker audit (confirm uncertainty markers were retained or resolved, never silently dropped)
7. **Category 7 audit — Advisor-sourced claims (Rule 7).** For every claim traceable to an Opus 4.7 advisor consultation, verify the consultation artifact (`reviews/consultations/*.md`) is present, dated, and linked, and that `[EXTERNAL]` tags were defensively re-classified before the Generator applied any suggestion. Advisor suggestions that entered prose without re-classification are a BLOCKER-level Category 7 violation.
8. **Category 8 audit — Graph-sourced claims (Coupling E.2).** For every finding tagged `[GRAPH-OVERLAY][CAT-8]`, verify the cited `graph.json` node exists, the graphify confidence label (EXTRACTED / INFERRED / AMBIGUOUS) matches the applied severity, and the severity decision reflects the Evaluator's independent judgment, not mere echo of graphify's confidence. Confidence-echo findings are Category 8 violations (MAJOR at standard depth, BLOCKER at submission-bound depth).
   - **8a. Confidence-echo detector.** Per `agents/reflector.md §Phase 2.5 item 8a`, apply the two-step echo test (mechanical-mapping match, then reasoning-note presence) to every `[GRAPH-OVERLAY][CAT-8]` finding. Record per-finding verdicts (CLEAN / ECHO / SHALLOW) in the §8 audit table. ECHO rate ≥ 30% across the round triggers the round-level `[COUPLING-E.2 DEGRADED]` flag and escalates to the Planner.
9. **Rule 7a audit — External verifier discipline.** For every citation-dependent finding, verify it was either read directly by the Evaluator, tagged `[verified: <source>]` naming a Class 1/1.5/2 verifier (Zotero, Scholar Gateway, Consensus, HuggingFace Papers, Scite), or explicitly tagged `[UNVERIFIED]`. Consult the Step 0.1 probe record in `reviews/step_0a_deterministic.md`. Unmarked, unverified citation claims are Rule 7a violations; severity is pinned to review depth (quick → MINOR with escalation recommendation; standard → MAJOR; submission-bound → BLOCKER).
   - **9a. Scholar Gateway render-contract audit.** If the round's artifacts include Scholar Gateway results, audit compliance with the render contract (`EXTERNAL_VERIFIERS.md §3.1`): top-of-file contract marker present? Per-search provenance line prefixing each synthesis point with correct counts and date range? Author-year inline citations with deduplicated DOI hyperlinks? Session footer rendered exactly once at the end of each affected file? Quoted passages drawn from `results[].text` rather than paraphrased abstracts? Missing contract marker or provenance line → Category 9 MAJOR. Missing session footer → Category 9 BLOCKER. Over-rendered footer → Category 9 MINOR. Abstract-paraphrase citations → Category 1 MAJOR. If Scholar Gateway was probed but not invoked in the round, record `9a: not applicable`.

Audit items 7–9 are mandatory whenever the project has active advisor consultations, graphify coupling, or external verifier activity in the round. If no such activity occurred in the round, record `not applicable — no advisor/graph/verifier events this round` and proceed.

Any grounding violation is a **[BLOCKER]** regardless of the underlying claim's severity.

**Phase 2.5.1 — Depth-tiered audit subset.** Consult the gating table in `agents/reflector.md §Phase 2.5.1` before running Phase 2.5 items. Not every item fires at every depth. At `quick` depth, items 1/4 run with a sample of at least 1; items 2/3/6/9 are mandatory; items 5/7/8/9a are skipped unless activating activity occurred. At `standard` depth, items 1/4 require sample ≥ 3; item 5 runs; items 7/8/9/9a run when their activation conditions are met. At `submission-bound` depth, items 1/4 require sample ≥ 5; all items fire with the severity floors listed in the gating table. A skipped item is recorded in §8a of the reflection report as `not applicable at <depth>` or `not applicable — no qualifying activity this round`. Silent omission of an audit row is itself a Category 6 marker-audit violation.

**Phase 2.6 — Reflector self-audit (meta-audit).** After Phase 2.5 emits, re-read the reflection-report draft and apply Rule 7a reflexively to the Reflector's own claims per `agents/reflector.md §Phase 2.6`. Every factual claim in §§1–5, every pattern-level claim, and every proposal in §§7 and 9 must be traceable to a round artifact or carry an explicit `[REFLECTOR UNVERIFIED]` / `[PATTERN CLAIM — unverified across rounds]` / `[PROPOSAL UNSOURCED]` / `[SKILL PROPOSAL — recurrence unverified]` marker. Self-citation mismatches are Rule 4 BLOCKERs applied to the Reflector. The self-audit output block is recorded in §8b of the reflection report. The Reflector may not silently strip uncertainty markers during final write — every remaining marker is either resolved by fresh evidence or retained and flagged to the user in Step 6 below.

**Phase 3 — Update project memory:**
- Append new lessons to `research_notes/lessons_learned.md` (L-nn format: What / Why / How to apply)
- Transfer newly confirmed strengths to `reviews/DO_NOT_DISTURB.md`
- Propose new directives to `research_notes/directives.md` marked as `[PROPOSED — awaiting user approval]`

**Phase 4 — Skill development:** Evaluate whether any pattern from this round warrants a new reusable skill. Apply the four criteria from `agents/reflector.md §Phase 4`: recurrence, self-containment, user-invocability, distinctness. Check `references/SKILL_REGISTRY.md` before proposing — do not re-propose an existing skill.

## Step 5 — Produce and save the reflection report

Write `reviews/reflection_report.md` to the project folder using the ten-section template in `agents/reflector.md §Phase 5`. All ten sections are required:

1. Round Summary
2. Severity Trajectory (before/after table)
3. Avoidable Errors
4. Genuine Discoveries
5. What Went Right
6. Process Observations
7. Proposed Package Improvements (marked `[PROPOSED]`)
8. Grounding Audit Results
9. Proposed Skills (with full skill file content for user review)
10. Memory Updates Made

## Step 6 — Present to the user

Summarize the reflection for the user, highlighting:
- Avoidable errors (with lesson numbers so the user can cross-reference `lessons_learned.md`)
- Proposed package improvements (for user approval or deferral — they do not enter the package until approved)
- Severity trajectory (are we improving?)
- Any new skill proposals (with the full SKILL.md content inline so the user can review and approve before anything is written)

The round is complete when the user acknowledges the reflection.

## What you do NOT do

- **Do not edit the manuscript.** You reflect on the work; you do not produce it.
- **Do not write to or modify any package file** (MASTER, REVIEW_ORCHESTRATION, component files, agent prompts). All package improvements are proposals marked `[PROPOSED]`. They enter the package only after user approval.
- **Do not skip the Grounding Audit.** It is mandatory in every round, at every depth, without exception.
- **Do not propose a skill without first reading `references/SKILL_REGISTRY.md`.** Re-proposing an already-existing skill wastes user attention and signals the Reflector did not read the registry.
- **Do not write to the project's `research_notes/directives.md` unilaterally.** Proposed directives are marked `[PROPOSED]` and require user approval before becoming stable.
