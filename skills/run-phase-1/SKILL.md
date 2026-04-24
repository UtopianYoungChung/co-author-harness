---
name: run-phase-1
description: "Ph1 Plan & Draft — bootstrap section state, record P-stage, dispatch Generator draft, run Reflector audit. If sd_sr_required=true, author i* SD/SR models. No Evaluator. Exit: ph1_draft_completion.md. Trigger: \"Ph1,\" \"draft pass,\" \"phase 1,\" \"start ladder,\" new section."
trigger: when the user says "Ph1 plan-and-draft," "draft pass," "run phase 1," "start the ladder," begins a new section, or when the Planner bootstraps section state for a fresh section
version: 0.7.4
---

# run-phase-1 — Ph1 Plan & Draft

**Grounding basis:** `references/PHASE_PROTOCOL.md §§3 (lifecycle), 3.1 (Ph1 charter), 3.1.1 (i\* structural-completeness validator), 6.3 (trigger enum), 7 (escalation gates)`; `references/GROUNDING_PROTOCOL.md §Rule 1 full-file reads (phase-gated digest exception retired at v0.7.4)`; `references/phase_state_schema.md §2 (15-field section object), §3.1 (30-trigger enum), §3a.1 (PhaseEntryLogRow shape)`; `AGENT_ORCHESTRATION.md §3 (agent-role matrix — Reflector-lightweight at Ph1, no Evaluator)`; `phase_notifications.yaml §1 (ph1_entry, ph1_exit_signed, imodel_validation_signed)`.

---

## 1. What this stage does

Ph1 is the **Plan & Draft** stage of the v0.7.0 Lifecycle-Phase Ladder. It absorbs the activities formerly scoped as milestones M1 (problem statement), M2 (theoretical framework), M3 (methodology outline), and the first draft pass of prose. Its design intent is **authorial foundation-laying**: the user, the Planner, and the Generator establish (a) the claim-maturity stage the manuscript sits at (P0 / P1 / P2), (b) first-pass prose that will be handed to Ph2 Review & Revise, and (c) **when `sd_sr_required: true` in `reviews/classification.md`** (v0.7.1 opt-in — see `PHASE_PROTOCOL.md §3.1.2`), the intentionality backbone under the GORE/AORE framing via i* SD/SR models. When `sd_sr_required` is absent or `false` (the v0.7.1 default), the i*-modelling sub-phase silently skips and Ph1 proceeds as a prose-only plan-and-draft stage.

At **v0.7.4 the Rule 1 phase-gated digest exception is retired** — full-file reads are the universal grounding floor at every phase, Ph1 included. The deterministic-check mandatory subset and Rule 1 scope verification run against the full file at every rung; the prior Ph1-only diff-scoping exception no longer applies.

Approval at Ph1 auto-advances the section to Ph2 unless the section's applicable ceiling is Ph1 (i.e. `min(default_final_phase, section_ceiling_override) == "Ph1"`), in which case approval locks the ceiling and writes a `ceiling_locked` row to the section's `phase_entry_log`.

## 2. Agent composition at Ph1

| Agent | Role at Ph1 | Surfaces |
|---|---|---|
| **Planner** | Bootstraps section state; records `ph1_pstage_declaration`; writes all `phase_entry_log` rows; runs the pre-advance check. **When `sd_sr_required: true`** in `reviews/classification.md` (`PHASE_PROTOCOL.md §3.1.2`), additionally authors SD/SR models and runs the §3.1.1 i\* structural-completeness validator. | `ph1_draft_completion.md` (unconditional); `reviews/sd_model.md`, `reviews/sr_model.md` (conditional on `sd_sr_required: true`) |
| **Generator** | Drafts prose under the declared P-stage register; applies the deterministic-check mandatory subset to the diff; produces the revision log entry. | `manuscript/*.md`, `manuscript/revision_log.md` |
| **Reflector-lightweight** | Grounding audit subset only (no aggregated `Phase 2b`, no `lessons_learned.md` write, no skill-proposal emission). Integrity probe against the Ph1 deliverables. | `reviews/ph1_reflector_probe_<cycle_id>.md` (optional) |
| **Evaluator** | **Not dispatched at Ph1.** First engagement is at Ph2. Any Ph1 invocation of the Evaluator is a `SAFEGUARD Check 1 (scope drift)` violation. | — |

## 3. Dispatch sequence

1. **Planner Phase 0 (preflight).** Read `reviews/phase_state.json`. If the target section's entry is missing, create it under `phase_state_schema.md §2` with the 15-field invariant: `current_phase: "Ph1"`, `last_approved_phase: null`, `iteration_count_at_current_phase: 0`, empty `phase_entry_log`, `phase_goal_declared` and `phase_deliverable_path` populated from the `§2.1` lookup tables keyed by Ph1, `convergence_metric: null`, `ph1_pstage_declaration: null`, `ph3_last_activity_at: null`. Compute `applicable_ceiling`. If `applicable_ceiling == "Ph1"` the section will ceiling-lock on approval; the Planner notes this in the user template.
2. **Planner: i\* SD/SR authoring (conditional).** **Only when `sd_sr_required: true` in `reviews/classification.md`** (`PHASE_PROTOCOL.md §3.1.2`), author (or refresh) `reviews/sd_model.md` and `reviews/sr_model.md` per the GORE/AORE framing: actors, softgoals, tasks, resources, dependencies. The Strategic Dependency (SD) model names the dependencies between human agents and software agents; the Strategic Rationale (SR) model deconstructs each agent's internal goal structure. When the flag is absent or `false` (the v0.7.1 default), this sub-phase silently skips — no `sd_model.md` / `sr_model.md` is authored.
3. **Planner: §3.1.1 structural-completeness validator (conditional).** **Only when `sd_sr_required: true`**, run the validator on the SD/SR pair authored in sub-phase 2. Check for orphan actors (no dependencies), unreferenced softgoals (no contributing tasks), dangling dependencies (a `depender` with no `dependee` in scope), and unreachable goals. On CLEAN, write an `imodel_structural_validation_signed` row to the section's `phase_entry_log`. On FAIL, refuse the Ph1 exit and surface `E-IMODEL-STRUCTURALLY-INCOMPLETE` per `phase_notifications.yaml §4`. When the flag is absent or `false`, this sub-phase silently skips — no validator run, no `imodel_structural_validation_signed` row, no `E-IMODEL-STRUCTURALLY-INCOMPLETE` emission.
4. **Planner: P-stage declaration.** Read `reviews/classification.md` for the P-stage (P0 / P1 / P2). Write the value to `sections[].ph1_pstage_declaration`. If the classification is missing, emit `W-PSTAGE-UNAVAILABLE` and leave the field null; the user must update the classification before Ph1 exit is signed.
5. **Planner: diff scoping.** Identify the diff-scoped paragraphs for this cycle — the set of paragraphs the Generator intends to edit or has just edited. The deterministic subset and the Rule 1 scope check run only on this set.
6. **Generator dispatch.** Planner hands the Generator the revision plan, the diff scope, and the declared P-stage. **When `sd_sr_required: true`**, the handoff additionally includes the SD/SR contextual briefing authored in sub-phase 2; when the flag is absent or `false`, the briefing is omitted and the Generator drafts against the P-stage vocabulary register alone. Generator drafts under `agents/generator.md` Phase 2 (Execute the Plan).
7. **Deterministic mandatory subset (on diff scope).** Em-dash, absolute-language, LLM-tic, and sentence-length patterns from `references/DETERMINISTIC_CHECKS.md §Mandatory subset`. Write results to `reviews/ph1_deterministic_<YYYY-MM-DD>_<cycle_id>.md`.
8. **Rule 1 full-file scope check.** Verify that every rule citation the Generator used is accompanied by a full-source read marker. **At v0.7.4 the Ph1-only digest exception is retired**; no citation may rest on a digest alone at any phase. This step runs on the full file, not the diff scope.
9. **Reflector-lightweight grounding audit (optional, Planner-gated).** Integrity-probe subset of `agents/reflector.md §Phase 2.5.1`. No `lessons_learned.md` write. Writes `reviews/ph1_reflector_probe_<cycle_id>.md` if invoked.
10. **Ph1 exit artefact authoring.** Planner writes `reviews/ph1_draft_completion.md` naming (i) the declared P-stage, (ii) the deterministic-check summary, (iii) the Rule 1 scope verdict, (iv) the Generator's revision log reference, (v) any Reflector-lightweight findings, and (vi) **when `sd_sr_required: true`**, the SD/SR model paths. When `sd_sr_required` is absent or `false`, the SD/SR-path line is silently omitted. The user reviews and signs.
11. **`pre_phase_advance_check.py` (Planner phase 5.5).** Runs the seven-clause guardrail from `PHASE_PROTOCOL.md §7.3`: (a) exit-artefact presence and well-formedness, (b) 15-field `SectionStateObject` populated, (c) ESCALATED-owner linearity (no ESCALATEDs yet at Ph1, trivially passes), (d) `ph1_pstage_declaration` non-null for the Ph2 admission (checked at Ph2 entry; also surfaced at Ph1 exit as a warning), (e) i\* structural-completeness validator passing — **evaluated only when `sd_sr_required: true`** (enforced by the `imodel_structural_validation_signed` row); when the flag is absent or `false`, this clause trivially passes, (f) MCR not applicable at Ph1 exit, (g) row-shape conformance of `phase_entry_log` rows per `phase_state_schema.md §3a.1`. Any failure blocks the advance.
12. **User approval checkpoint.** Planner presents the ph1_draft_completion artefact, the diff, and the deterministic report to the user. User Approves or Rejects.

## 4. Approval handling (advance rule)

The advance rule is canonically specified in `references/PHASE_PROTOCOL.md §4`. In summary: `next_tier = min(current_phase + 1, applicable_ceiling)`. If `next_tier == current_phase` after the min, approval sets `ceiling_locked: true` and emits a `ceiling_locked` row.

- **User Approve → auto-advance to Ph2.** Planner writes a `ph1_draft_completion_signed` row (trigger 12), then a `user_approval` row (trigger 2) in the same writer session. `current_phase: Ph2`, `last_approved_phase: Ph1`, `iteration_count_at_current_phase := 0`. The Ph2 entry notification fires per `phase_notifications.yaml §1 ph2_entry`.
- **User Approve with `applicable_ceiling == "Ph1"` → ceiling-lock.** Planner writes a `ph1_draft_completion_signed` row, a `user_approval` row, and a `ceiling_locked` row. `ceiling_locked: true`; no advance.
- **User Reject → section stays at Ph1.** Planner writes a `user_rejection` row with the user's reason in the `notes` field (≤ 280 chars per `§3a.1`). `iteration_count_at_current_phase += 1`. If the counter exceeds `per_phase_budget × 1.5` (NEW-H-7), Planner surfaces the iteration-exhaustion warning and asks whether to apply `section_ceiling_override` or proceed.
- **User Defer → no movement.** Planner writes a `user_defer` row; no iteration increment; the section resumes on the next `/review`.
- **Retraction.** The only way to move the phase backward at Ph1 is `retraction`. At Ph1 this is rare — usually the user is starting fresh rather than rolling back.

## 5. Retired surfaces at v0.7.0 (previously visible at Ph1)

| Surface | Status | Notes |
|---|---|---|
| **Generator Self-Ph1 Verdict (Phase 3.5)** | **RETIRED** | The verdict block is no longer emitted. The Generator does not self-score at Ph1. The Evaluator joins at Ph2 and runs a full local pass on the prose as drafted. |
| **Evaluator Confirmation Mode eligibility flag** | **RETIRED** | Confirmation Mode itself is retired (`PHASE_PROTOCOL.md §11 item 3`); no Ph1 output feeds a Ph2 shortcut. |
| **`confirmation_failed` trigger** | **RETIRED (read-only)** | v0.6.0-migrated rows preserve the trigger for audit; no v0.7.0 write emits it. |
| **EG-2 (self-Ph1 verdict mismatch at Ph2 entry)** | **RETIRED** | EG-2 is removed from the escalation-gate register at v0.7.0. EG-numbering preserves EG-1/3/4/5/6/7 for continuity. |

Any Ph1 artefact or revision-log entry that attempts to emit a Self-Ph1 Verdict block is logged by the Planner as a `SAFEGUARD Check 1 (scope drift)` violation and discarded.

## 6. Artefacts produced

- `reviews/sd_model.md`, `reviews/sr_model.md` — the i\* Strategic Dependency and Strategic Rationale models (authored or refreshed). **Produced only when `sd_sr_required: true` in `reviews/classification.md`** (`PHASE_PROTOCOL.md §3.1.2`); when the flag is absent or `false` (the v0.7.1 default), these artefacts are not produced.
- `reviews/ph1_deterministic_<YYYY-MM-DD>_<cycle_id>.md` — deterministic mandatory-subset report on the diff scope.
- `reviews/ph1_reflector_probe_<cycle_id>.md` — Reflector-lightweight probe (optional).
- `reviews/ph1_draft_completion.md` — the signed Ph1 exit artefact (required for the Ph1 → Ph2 advance).
- Appended section(s) of `manuscript/<section>.md` — the Generator's draft.
- Appended entry in `manuscript/revision_log.md` — edit log **without** a Self-Ph1 Verdict block (retired).
- Updated `reviews/phase_state.json` — single-writer Planner atomic `.tmp → rename` update per `phase_state_schema.md §5`, with the new `phase_entry_log` rows (`ph1_draft_completion_signed`, `user_approval` | `user_rejection` | `user_defer` | `ceiling_locked`, plus `imodel_structural_validation_signed` **only when `sd_sr_required: true`**).

## 7. What this stage does NOT do

- **No Evaluator engagement.** The Evaluator joins at Ph2. Any Ph1 dispatch of the Evaluator is a scope violation.
- **No full seven-step judgment pass.** That lives at Ph2 (Steps 1–3 + integrated checklist) and Ph3 (the full seven-step loop).
- **No convergence metric.** `convergence_metric` is Ph3-only; at Ph1 it is `null`.
- **No MCR.** The Manuscript Convergence Report is a Ph4-admission artefact.
- **No G.4 sign-off.** Ph4 only.
- **No Self-Ph1 Verdict block.** Retired at v0.7.0 (see §5).

## 8. Escalation paths visible at Ph1

- **EG-5 (DETERMINISTIC_CHECKS threshold breach).** Can fire at any phase, including Ph1. Breach is MINOR unless an absolute-or-cannot claim is implicated (then MAJOR).
- **W-PSTAGE-UNAVAILABLE.** Non-blocking at Ph1, blocking at Ph2 entry. Prompts the user to update `classification.md`.
- **E-IMODEL-STRUCTURALLY-INCOMPLETE.** Blocks Ph1 exit signing. Planner refuses to write `ph1_draft_completion_signed` until the validator passes.

## 9. Trigger vocabulary

- "Ph1" · "phase 1" · "plan & draft" · "draft pass" · "first draft" · "start the ladder" · "first pass on this section" · "draft this section"
- Invoked on Planner bootstrap when a new section is encountered.

---

*This skill is the entry point for the Ph1 stage only. To proceed past Ph1, the user must sign `ph1_draft_completion.md` and approve at the checkpoint in §3 step 12, which auto-advances the section to Ph2 (SK `run-phase-2`) unless ceiling-locked.*
