---
name: run-phase-1
user-invocable: false
description: "Compatibility body for the public /run-draft stage. Ph1 bootstraps state, records P-stage, and requires binding-derived Generator drafting plus a bounded independent Evaluator policy pass; centroid work is capability-triggered."
trigger: when the user says "Ph1 plan-and-draft," "draft pass," "run phase 1," "start the ladder," begins a new section, or when the Planner bootstraps section state for a fresh section
version: 0.7.4
---

# run-phase-1 — Ph1 Plan & Draft

**Compatibility surface.** New user-facing guidance and dispatch should use
`/run-draft`. This file remains the full Ph1 implementation body so legacy
`/run-phase-1` invocations resolve without semantic drift.

**Grounding basis:** `references/PHASE_PROTOCOL.md §§3, 3.1, 6.3, 7`; `references/GROUNDING_PROTOCOL.md` full-file rules; `references/phase_state_schema.md`; `AGENT_ORCHESTRATION.md §3` (bounded Evaluator all-drafts policy pass plus Reflector-lightweight at Ph1); `phase_notifications.yaml`; and `skills/seed-snowball-discovery/SKILL.md`.

## Output Profile

**Runtime binding.** Before acting, resolve
`../../references/_snippets/output-profile.md` relative to this `SKILL.md`,
read it in full, and treat it as part of this skill contract. Its canonical
plugin-root identity is `references/_snippets/output-profile.md`. Do not rely
on build-time include expansion.

---

## 1. What this stage does

Ph1 is the **Plan & Draft** stage of the v0.8.0 Lifecycle-Phase Ladder. It supplies drafting and review maturity for early assignment-derived deliverables without redefining their jobs. Under the four-milestone course-essay profile, M1 is an exploratory memo, M2 is annotated references, and M3 is a structured outline. Its design intent is **authorial foundation-laying**: the user, the Planner, and the Generator establish (a) the claim-maturity stage the manuscript sits at (P0 / P1 / P2), and (b) the assigned early deliverables that will support the complete M4 draft.

At **v0.7.4 the Rule 1 phase-gated digest exception is retired** — full-file reads are the universal grounding floor at every phase, Ph1 included. The deterministic-check mandatory subset and Rule 1 scope verification run against the full file at every rung; the prior Ph1-only diff-scoping exception no longer applies.

Milestone approval for M1, M2, or M3 advances only the assignment milestone chain and the project remains in Ph1. After M1-M3 are accepted and M4 initial assembly is complete, a separate Ph1 exit approval advances the section to Ph2 unless the applicable ceiling is Ph1, in which case the phase-exit approval locks the ceiling.

## 2. Agent composition at Ph1

| Agent | Role at Ph1 | Surfaces |
|---|---|---|
| **Planner** | Bootstraps section state; records `ph1_pstage_declaration`; writes all `phase_entry_log` rows; runs the pre-advance check. **Dispatches SK-NEW-A `seed-snowball-discovery` at Step 4.5** as part of pre-draft setup when the section's `references_initialized` is `false` or absent and `references/REFERENCES.md` is missing (per architecture plan §5.2 Edit-1). | `ph1_draft_completion.md`; SK-NEW-A artefacts at Step 4.5 (see §6) |
| **Generator** | Drafts prose under the declared P-stage register; applies the deterministic-check mandatory subset to the diff; produces the revision log entry. | `manuscript/*.md`, `manuscript/revision_log.md` |
| **Reflector-lightweight** | Grounding audit subset only (no aggregated `Phase 2b`, no `lessons_learned.md` write, no skill-proposal emission). Integrity probe against the Ph1 deliverables. | `reviews/ph1_reflector_probe_<cycle_id>.md` (optional) |
| **Evaluator** | Runs the bounded all-drafts governing-policy evaluation after every Generator publication, including centroid review only when enabled by the authoritative reader binding. Full revision-maturity review begins at Ph2. | Current-byte evaluation envelope and findings |

## 3. Dispatch sequence

The Planner reservation boundary is `assignment_dispatch_preflight.py`; no Generator dispatch precedes its successful reservation.

0. **Assignment-process receipt gate and executable checkpoint derivation.** Read `references/ASSIGNMENT_MILESTONE_PROCESS.md` and the controlling brief in full; require a resolved `reviews/assignment_contract.json`. Run `assignment_milestone_checkpoint.py derive` and obey its exact target/action. Emit the target receipt; the authoritative reader binding determines whether centroid conditioning applies. Reader-profile v2 with `semantic_usage: not_invoked` omits centroid work while retaining all non-graph obligations. Prepare the generation policy contract, reserve the receipt, dispatch the Generator, publish through `assignment_writer_commit.py`, then prepare and complete the independent Evaluator contract over the exact bytes. Planner may call `record` only with both verified envelopes. Only project-local explicit approval permits `accept`. Any non-zero result halts. `APG-SEQUENCE-LEGACY` requires migration/acceptance work, never synthesized acceptance.

1. **Planner Phase 0 (preflight).** Read `reviews/phase_state.json`. If the target section's entry is missing, create it under `phase_state_schema.md §2` with the full 18-field invariant (`phase_state_schema.md §2`, 18 fields as of v0.10.0): `current_phase: "Ph1"`, `last_approved_phase: null`, `iteration_count_at_current_phase: 0`, empty `phase_entry_log`, `phase_goal_declared` and `phase_deliverable_path` populated from the `§2.1` lookup tables keyed by Ph1, `convergence_metric: null`, `ph1_pstage_declaration: null`, `ph3_last_activity_at: null`. Compute `applicable_ceiling`. If `applicable_ceiling == "Ph1"` the section will ceiling-lock on approval; the Planner notes this in the user template.
2. **Planner: P-stage declaration.** Read `reviews/classification.md` for the P-stage (P0 / P1 / P2). Write the value to `sections[].ph1_pstage_declaration`. If the classification is missing, emit `W-PSTAGE-UNAVAILABLE` and leave the field null; the user must update the classification before Ph1 exit is signed.
3. **Planner: seed-snowball gate (conditional).** **OR-conjunctive outer guard** per architecture `2026-04-26-snowball-reference-architecture.md §5.2 Edit-1`: dispatch SK-NEW-A `seed-snowball-discovery` when the section's `references_initialized` is `false` or absent **OR** `references/REFERENCES.md` does not exist. The OR-conjunction (NOT AND) is load-bearing: it catches both inconsistent-state windows that an AND-guard would silently skip — (a) `references_initialized: false` AND REFERENCES.md present-but-populated (manually authored or interrupted prior run), and (b) `references_initialized: true` AND REFERENCES.md missing (file deleted post-init or atomic-rename failed mid-write). With the OR-guard, either inconsistent state triggers SK-NEW-A; the skill's own §Phase 4 reconciliation logic (append-or-overwrite per the file state) handles the recovery. SK-NEW-A is the v0.10.0 reference-pipeline entry skill (`skills/seed-snowball-discovery/SKILL.md`); it assembles a saturated reference pool from the section's claim register via the wiki-first → Zotero → Class 1 ordering of `EXTERNAL_VERIFIERS.md §1.5`, emits `references/REFERENCES.md` (three-table format: core corpus / snowball / cited-via), an append-only `reviews/snowball_log.md` procedure trace, and rows in `reviews/external_verification_log.md`. **The Planner's three-outcome-branch handling is authoritative in `agents/planner.md`** at the Phase that mirrors this Step's placement (between P-stage declaration and diff scoping); the summary below is for skill-reader reference, the canonical contract is the Planner agent file:

  *(i) Clean exit.* Planner sets `references_initialized: true` in `reviews/phase_state.json` (the field lives in the SectionStateObject per `phase_state_schema.md §2`) and appends a `seed_snowball_signed` row (trigger 31, per `phase_state_schema.md §3.1`) to `phase_entry_log`. The skill's idempotency guard at its `§4` precondition clause 4 ensures that re-running on an already-fully-initialised section (field=true AND tables populated) emits `ALREADY_INITIALIZED` no-op — partial-state windows (field-vs-file divergence) are caught by SK-NEW-A's `§Phase 4` reconciliation, NOT by the precondition clause; the OR-guard ensures dispatch in those windows so the reconciliation can run.

  *(ii) Precondition no-op.* If SK-NEW-A's preconditions are unmet beyond the idempotency clause (e.g., `wiki_path` unresolvable on a `wiki_linked: true` project, no reachable Class 1 verifier, missing claim register) the skill no-ops with the corresponding reason code per its `§2`; the Planner surfaces a non-blocking `W-SNOWBALL-PRECONDITION-UNMET` warning (declared at `phase_notifications.yaml §4`), defers escalation to SK-NEW-A's own clauses, and Ph1 proceeds to Step 5 without ledger writes for trigger 31.

  *(iii) Partial failure (mid-run).* If SK-NEW-A enters its procedure phases but fails partway — `WRITE_FAILURE` on the in-loop wiki write-back or `GRAPH_VS_EXTERNAL_DISAGREEMENT` per its `§8` failure-mode register — the Planner does NOT flip `references_initialized` to `true`, does NOT write the trigger 31 row, emits `E-SNOWBALL-MID-RUN-FAILURE` (declared at `phase_notifications.yaml §4`), and **HALTS the Ph1 cycle pending user adjudication** (matching `agents/planner.md` Phase 3.7 outcome class (iii) — the canonical contract). Generator dispatch (Step 6) does NOT proceed for this section this cycle. The partial `references/REFERENCES.md` is preserved on disk for user adjudication; the user can retry SK-NEW-A directly or manually flip the flag after inspection. Ph1 resumes on the next user invocation.

  Ph2 entry will re-test the gate at its own Step 0.5 (placeholder at S2; full Ph2-side dispatch of SK-NEW-A / SK-NEW-B lands at S3/S4 per the implementation strategy §5.4 / §5.5 — Stage S3 ships SK-NEW-B and Stage S4 inserts run-phase-2 Step 0.5's full body).
4. **Planner: diff scoping.** Identify the diff-scoped paragraphs for this cycle — the set of paragraphs the Generator intends to edit or has just edited. The deterministic subset and the Rule 1 scope check run only on this set.
5. **Generator dispatch.** Planner hands the Generator the revision plan, diff scope, declared P-stage, reserved `assignment_gate_receipt`, and `assignment_gate_target`. Generator stages only beneath `reviews/.harness/assignment/staged/<receipt_id>/` and uses `assignment_writer_commit.py` to validate, consume, and publish the scoped write plan. Cancellation or pre-commit abort uses `assignment_receipt_invalidate.py`; there is no second preflight or direct final-path write. Generator drafts under `agents/generator.md` Phase 2 (Execute the Plan).
6. **Deterministic mandatory subset (on diff scope).** Em-dash, absolute-language, LLM-tic, and sentence-length patterns from `references/DETERMINISTIC_CHECKS.md §Mandatory subset`. Write results to `reviews/ph1_deterministic_<YYYY-MM-DD>_<cycle_id>.md`.
7. **Rule 1 full-file scope check.** Verify that every rule citation the Generator used is accompanied by a full-source read marker. **At v0.7.4 the Ph1-only digest exception is retired**; no citation may rest on a digest alone at any phase. This step runs on the full file, not the diff scope.
8. **Reflector-lightweight grounding audit (optional, Planner-gated).** Dispatch `/run-reflection mode: lightweight`, which loads `agents/reflector-probe.md` and its Phase 2.5.1-gated integrity subset. No `lessons_learned.md` write. Writes `reviews/ph1_reflector_probe_<cycle_id>.md` if invoked.
9. **Assignment milestone branch (native M1-M3).** After the target deliverable's feedback has been recorded and adjudicated under `MILESTONE_FEEDBACK_HANDOFF_PROTOCOL.md`, stop for explicit user approval of that milestone. Only explicit approval authorizes the Planner to finalize the F9 packet and atomically write `accepted` state. On M3, the M3→M4 packet must also bind current wiki-grounding evidence or an authorized opt-out. End the invocation after the transaction with `current_phase: Ph1`; do not write a Ph1 exit artefact and do not run a phase-advance check. The next `/run-draft` derives the successor target.
10. **Ph1 exit branch (M4 initial assembly only).** After M1-M3 are accepted and the Generator has assembled the complete M4 manuscript, the Planner writes `reviews/ph1_draft_completion.md` naming (i) the declared P-stage, (ii) the deterministic-check summary, (iii) the Rule 1 scope verdict, (iv) the Generator's revision log reference, and (v) any Reflector-lightweight findings. Writing it while M1-M3 remain open is a protocol violation.
11. **`pre_phase_advance_check.py` (M4 branch only).** Run the Ph1 exit guardrail from `PHASE_PROTOCOL.md §7.3`. Any failure blocks phase movement.
12. **Separate phase-exit checkpoint (M4 branch only).** Present `ph1_draft_completion.md`, the M4 diff, and deterministic evidence. Explicit approval licenses `Ph1 → Ph2`; it is not inferred from M4 deliverable acceptance.

## 4. Approval handling (advance rule)

The advance rule is canonically specified in `references/PHASE_PROTOCOL.md §4` and applies only at a phase-exit checkpoint. M1-M3 milestone approvals never invoke it. At the M4 Ph1 exit, `next_phase = min(current_phase + 1, applicable_ceiling)`; if `next_phase == current_phase`, approval sets `ceiling_locked: true`.

- **User approves M1, M2, or M3 → milestone-only.** Planner commits the authorized F9 and accepted milestone transaction; `current_phase` stays `Ph1`. No `ph1_draft_completion_signed` row is written.
- **User approves the M4 Ph1 exit → advance to Ph2.** Planner writes a `ph1_draft_completion_signed` evidence row, then a phase-changing `user_approval` row in the same writer session. `current_phase: Ph2`, `last_approved_phase: Ph1`, `iteration_count_at_current_phase := 0`.
- **User Approve with `applicable_ceiling == "Ph1"` → ceiling-lock.** Planner writes a `ph1_draft_completion_signed` row, a `user_approval` row, and a `ceiling_locked` row. `ceiling_locked: true`; no advance.
- **User Reject → section stays at Ph1.** Planner writes a `user_rejection` row with the user's reason in the `notes` field (≤ 280 chars per `§3a.1`). `iteration_count_at_current_phase += 1`. If the counter exceeds `per_phase_budget × 1.5` (NEW-H-7), Planner surfaces the iteration-exhaustion warning and asks whether to apply `section_ceiling_override` or proceed.
- **User Defer → no movement.** Planner writes a `user_defer` row; no iteration increment; the section resumes on the next `/run-draft` or matching lifecycle invocation.
- **Retraction.** The only way to move the phase backward at Ph1 is `retraction`. At Ph1 this is rare — usually the user is starting fresh rather than rolling back.

## 5. Retired surfaces at v0.7.0 (previously visible at Ph1)

| Surface | Status | Notes |
|---|---|---|
| **Generator Self-Ph1 Verdict (Phase 3.5)** | **RETIRED** | The verdict block is no longer emitted. The Generator does not self-score at Ph1. The independent Evaluator runs the bounded Ph1 pass required by `references/policies/phase_engagement.v1.json`; a full local revision-maturity pass begins at Ph2. |
| **Evaluator Confirmation Mode eligibility flag** | **RETIRED** | Confirmation Mode itself is retired (`PHASE_PROTOCOL.md §11 item 3`); no Ph1 output feeds a Ph2 shortcut. |
| **`confirmation_failed` trigger** | **RETIRED (read-only)** | v0.6.0-migrated rows preserve the trigger for audit; no v0.7.0 write emits it. |
| **EG-2 (self-Ph1 verdict mismatch at Ph2 entry)** | **RETIRED** | EG-2 is removed from the escalation-gate register at v0.7.0. EG-numbering preserves EG-1/3/4/5/6/7 for continuity. |

Any Ph1 artefact or revision-log entry that attempts to emit a Self-Ph1 Verdict block is logged by the Planner as a `SAFEGUARD Check 1 (scope drift)` violation and discarded.

## 6. Required outputs

- Manuscript delta or approved no-change rationale.
- Compact entry in `manuscript/revision_log.md`.
- State update in `reviews/phase_state.json` when the phase gate changes.
- Evidence packet at `reviews/.harness/evidence/<event_id>.json` (and matching `events.jsonl` row) capturing deterministic summary, Rule-1 scope, and snowball outcomes for this cycle.
- Human-facing exception report only when an escalation rule fires.

### Exception report surfaces

Legacy Markdown paths may still be written when SK-NEW-A, deterministic tooling, or probes require human-readable artefacts:

- `references/REFERENCES.md` — populated three-table reference pool (core corpus, snowball, cited-via), **produced by SK-NEW-A dispatched at Step 4.5** when `references_initialized` is `false` or absent and the file does not yet exist. Idempotent re-runs emit `ALREADY_INITIALIZED` no-op and do not regenerate the file.
- `reviews/snowball_log.md` — append-only snowball procedure trace, **produced by SK-NEW-A at Step 4.5** (per its §6); records seed-phase admits, per-iteration backward/forward admits (graph-local vs. external split), saturation signal, and the per-iteration `interaction_id` UUIDs.
- `reviews/external_verification_log.md` — Rule 7a verification rows appended by SK-NEW-A at Step 4.5 for every Class-1-fall-through admission.
- `reviews/ph1_deterministic_<YYYY-MM-DD>_<cycle_id>.md` — deterministic mandatory-subset report on the diff scope.
- `reviews/ph1_reflector_probe_<cycle_id>.md` — Reflector-lightweight probe (optional).
- `reviews/ph1_draft_completion.md` — the signed Ph1 exit artefact (required for the Ph1 → Ph2 advance).
- Appended section(s) of `manuscript/<section>.md` — the Generator's draft.
- Appended entry in `manuscript/revision_log.md` — edit log **without** a Self-Ph1 Verdict block (retired).
- Updated `reviews/phase_state.json` — single-writer Planner atomic `.tmp → rename` update per `phase_state_schema.md §5`, with the new `phase_entry_log` rows (`ph1_draft_completion_signed`, `user_approval` | `user_rejection` | `user_defer` | `ceiling_locked`, plus `seed_snowball_signed` (trigger 31) **only when SK-NEW-A exited cleanly at Step 4.5**).

## 7. What this stage does NOT do

- **Bounded Evaluator engagement is mandatory.** Every Ph1 milestone draft receives independent evaluation against the complete capability-applicable policy bundle; centroid review is included only when enabled by the authoritative reader binding. The full Ph2 review remains distinct.
- **No full seven-step judgment pass.** That lives at Ph2 (Steps 1–3 + integrated checklist) and Ph3 (the full seven-step loop).
- **No convergence metric.** `convergence_metric` is Ph3-only; at Ph1 it is `null`.
- **No MCR.** The Manuscript Convergence Report is a Ph4-admission artefact.
- **No G.4 sign-off.** Ph4 only.
- **No Self-Ph1 Verdict block.** Retired at v0.7.0 (see §5).

## 8. Escalation paths visible at Ph1

- **EG-5 (DETERMINISTIC_CHECKS threshold breach).** Can fire at any phase, including Ph1. Breach is MINOR unless an absolute-or-cannot claim is implicated (then MAJOR).
- **W-PSTAGE-UNAVAILABLE.** Non-blocking at Ph1, blocking at Ph2 entry. Prompts the user to update `classification.md`.

## 9. Trigger vocabulary

- "Ph1" · "phase 1" · "plan & draft" · "draft pass" · "first draft" · "start the ladder" · "first pass on this section" · "draft this section"
- "seed references" · "snowball this section" · "build references" — user-facing phrases that route into the Step 4.5 SK-NEW-A dispatch when the section meets the gate condition (per SK-NEW-A §10).
- Invoked on Planner bootstrap when a new section is encountered.

---

*This skill is the entry point for the Ph1 stage only. To proceed past Ph1, the user must sign `ph1_draft_completion.md` and approve at the checkpoint in §3 step 12, which auto-advances the section to Ph2 (SK `run-phase-2`) unless ceiling-locked.*
