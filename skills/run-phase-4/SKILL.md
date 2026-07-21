---
name: run-phase-4
user-invocable: false
description: "Compatibility body for the public /run-finalize stage. Ph4 Finalize & Close requires MCR admission, external verification, G.4, and Reflector-full close-out."
trigger: when the user says "Ph4 finalize-and-close," "run phase 4," "ship this," "submission-bound pass," "G.4 sign-off," or when the Planner advances after MCR admission
version: 0.8.0
---

# run-phase-4 — Ph4 Finalize & Close

**Compatibility surface.** New user-facing guidance and dispatch should use
`/run-finalize`. This file remains the full Ph4 implementation body so legacy
`/run-phase-4` invocations resolve without semantic drift.



## Wiki write deferral (Research Truth Phase 0/1)

Coupling C/D canonical Wiki mutation is **unavailable**
(`reason_code: WIKI_WRITE_TRANSACTION_UNAVAILABLE`).

- Block only the Wiki mutation.
- Do **not** block Research completion, approval, or release.
- Project-local REFERENCES, lessons, reports, manuscripts, and reflection
  outputs continue normally.
- On deferral record: `status: deferred`,
  `reason_code: WIKI_WRITE_TRANSACTION_UNAVAILABLE`, `wiki_page_key: null`.
- Do **not** write `m5_wiki_ingest` as a success trigger and do **not**
  fabricate `wiki_page_key` or `lessons_promoted_to_wiki` success values.
- Automatic callers treat the deferred result as a visible non-blocking
  downstream deferral. Phase 4 / G.4 completion does not depend on Wiki write
  availability.

**Grounding basis:** `references/PHASE3_PHASE4_COMMON_ENVELOPE.md` (shared Ph3/Ph4 envelope — judgment-pass structure, SAFEGUARD invocation + Ph4 severity floor escalation, convergence metric, [Ph3-STALE], Coupling E.2, Reflector dispatch, ESCALATED handling, renamed surfaces, agent composition, approval patterns); `references/PHASE_PROTOCOL.md §§3.4 (Ph4 charter; pre-MCR deep gate), 7 (EG-1, EG-7), 8 (G.4 sign-off), 9 (MCR)`; `references/MASTER_research_and_paper_guidelines.md §G.4`; `references/EXTERNAL_VERIFIERS.md`; `references/phase_state_schema.md §§2, 2.1, 3.1, 3a.2, 6.1`; `skills/run-phase-3/SKILL.md §4.5`; `agents/reflector-closeout.md`; `skills/ingest-m5-to-wiki/SKILL.md`; `phase_notifications.yaml §§1, 7`.

## Output Profile

Default profile: `final_report`.

Ph4 is the primary **final round report** assembly locus: the Planner synthesizes `reviews/final_round_report_<round_id>.md` from F7 evidence, revision logs, and `phase_state.json` per `references/OUTPUT_ECONOMY_PROTOCOL.md`. Human-facing checkpoints still use `decision_checkpoint` or `exception_report` when gates block.

---

## 1. What this stage does

Ph4 is the **Finalize & Close** stage of the Lifecycle-Phase Ladder — the terminal stage and the submission gate. It governs the final paper represented by the backward-compatible M5 framework slot; it does not assert that the controlling assignment names a fifth milestone. Ph4 is a **strict superset of Ph3** with four additions:

1. **External verifiers move from optional to REQUIRED.** Zotero MCP citation probe, Scholar Gateway render-contract audit, Coupling E.2 overlay, and register-specific passes are gating at Ph4 (advisory at Ph3).
2. **G.4 sign-off artefact is mandatory.** Row 8.5 (SAFEGUARD layer outcome) must be CLEAN; a partial G.4 blocks ship.
3. **Reflector-full runs at close-out.** The full Reflector pipeline runs — Phase 2b aggregated confirmation-failed history audit (NEW-H-4), Phase 3 lessons synthesis, Phase 4 skill-development proposals (formalised by the Planner via the `plugin_update_proposed_by_planner` trigger), Phase 5 memory updates (`lessons_learned.md`, `DO_NOT_DISTURB.md`).
4. **Coupling D M5 wiki ingest (deferred).** At Ph4 close, SK-17 `ingest-m5-to-wiki` is attempted but currently returns `status: deferred` / `reason_code: WIKI_WRITE_TRANSACTION_UNAVAILABLE` / `wiki_page_key: null`. Do **not** write an `m5_wiki_ingest` success trigger. Phase 4 completion does not depend on Wiki write availability.

The v0.7.0 structural change from v0.6.0 is the **MCR replaces the LCR** (the renamed admission gate), the **Ph4_ready → Ph3_converged enum rename**, and the **[Ph3-STALE] block** on MCR admission. At v0.8.0 (β-P-9a), MCR admission adds **`pre_mcr_deep_pass_completed: true` on every in-scope section** before the Planner may assemble a passing MCR (`PHASE_PROTOCOL.md §3.4`, `phase_state_schema.md` §2.1).

## 2. Manuscript Convergence Report (MCR) — admission gate

The MCR is the Planner's admission artefact for Ph4. Its purpose is twofold: (a) make the manuscript-wide readiness state legible to the user in one place, and (b) propose a climb plan that brings every unready section up to `Ph3_converged` before Ph4 admission. The MCR **replaces** the v0.6.0 Laggard Clearance Report (LCR); the rename is documented in `PHASE_PROTOCOL.md §14`.

### 2.1 MCR admission conditions

Ph4 admission requires, simultaneously:

1. **Every section has `current_phase == "Ph3_converged"`** OR **`ceiling_locked == true` at its `applicable_ceiling`** (a section legitimately terminated at a lower ceiling is not an unready section).
2. **No section carries a computed `[Ph3-STALE] == true` flag.** A stale section blocks admission with `E-MCR-BLOCKED-Ph3-STALE` per `phase_state_schema.md §6.1`.
3. **Every ESCALATED finding in `convergence_log.md` is resolved or has a named owner with a documented transfer rationale (if transferred).** Linear-Accountability defence per `PHASE_PROTOCOL.md §3.2.1`.
4. **Every section has `pre_mcr_deep_pass_completed == true` in `reviews/phase_state.json`.** Absent field is treated as `false` at the MCR gate (`phase_state_schema.md` §2.1). Violation refuses MCR assembly with **`E-MCR-PRE-DEEP-PASS-REQUIRED`** (`phase_state_schema.md` §6.1). Remedy: run at least one full `run-phase-3` iteration whose F6 carried `check_profile: deep` and closed under Phase 5.5 so the Planner flips the bool (`skills/run-phase-3/SKILL.md` §4.5, §5 step 13).

### 2.2 MCR contents

A compact table with one row per section:

```
| heading_path | current_phase | iteration_count | per-phase budget | +50% reserve | applicable_ceiling | [Ph3-STALE] | pre_mcr_deep_pass_completed | status |
```

Plus a climb plan section that enumerates, for each unready or stale section:

- the next required rung (for unready sections),
- the required `ReengagementSignoffRow` (for stale sections),
- the required **`check_profile: deep`** full Ph3 pass (for sections still at `pre_mcr_deep_pass_completed: false`),
- the number of iterations estimated to reach `Ph3_converged` at the remaining iteration reserve,
- any `section_ceiling_override` that would affect the target (R-02 caps the target at `default_final_phase`; an override that pins a section below Ph4 is respected).

### 2.3 MCR triggers

The Planner emits the MCR when:

- The user invokes this skill and any section is below `Ph3_converged` or any section is `[Ph3-STALE]`.
- A section exhausts its per-phase iteration budget + 50% reserve and the Planner detects that the section is blocking Ph4 admission.
- The user asks the Planner to raise a ceiling and the new ceiling affects the MCR's pass/fail status.

### 2.4 MCR approval paths

The user may:

- **A — Approve MCR auto-climb.** Planner walks each unready section rung-by-rung per `PHASE_PROTOCOL.md §9`.
- **B — Raise specific ceilings before climbing** through a section-scoped Planner intent.
- **C — Re-engage stale sections** through a section-scoped Planner intent — required before Ph4 admission when `[Ph3-STALE]` is computed true.
- **D — Cancel the climb** through the Planner's cancel-climb intent and ship at current mixed-ceiling.

### 2.5 Iteration reserve (NEW-H-7)

Each section carries a +50% reserve on top of its per-stage default iteration budget. A section still rejecting at `1.5× default` surfaces the iteration-exhaustion warning and the Planner prompts for `section_ceiling_override`, an extension grant, or retraction.

### 2.6 Target cap (R-02)

The MCR's climb target for every section is capped at `default_final_phase` (read from the top-level field in `phase_state.json`). The MCR never proposes climbing a section above its declared ceiling.

## 3. Agent composition at Ph4 (full four-agent loop)

See `references/PHASE3_PHASE4_COMMON_ENVELOPE.md §9` for the shared four-agent integrity guarantee. Ph4-specific roles:

| Agent | Role at Ph4 | Surfaces |
|---|---|---|
| **Planner** | Runs the MCR; orchestrates admission; dispatches the full Evaluator pass; writes every `phase_entry_log` row; runs the terminal `pre_phase_advance_check.py`; formalises plugin-update proposals from Reflector-full. | `reviews/mcr_<YYYY-MM-DD>.md`, `reviews/plugin_proposals/<cycle_id>.md` |
| **Evaluator** | Runs the full seven-step judgment pass at Ph4 severity floors; required external-verifier probes; Step 8.5 SAFEGUARD all-eight audit; authors the G.4 sign-off artefact. | `reviews/ph4_findings_<cycle_id>.md`, `reviews/safeguard_layer_results.md`, `reviews/g4_signoff_<YYYY-MM-DD>.md`, `reviews/ph4_external_verifier_<cycle_id>.md` |
| **Generator** | Applies fixes per the consolidated findings; logs edits. No Self-Ph1 Verdict. | `manuscript/*.md`, `manuscript/revision_log.md` |
| **Reflector-full** | Runs at close-out. Phase 2b aggregated confirmation-failed history audit (NEW-H-4, scans full `phase_state.json` history including retired-but-migrated `confirmation_failed` rows); Phase 2.5.1 full grounding audit at Ph4 severity floors; Phase 3 lessons synthesis; Phase 4 skill proposals; Phase 5 memory updates. | `reviews/reflection_report.md`, `research_notes/lessons_learned.md`, `reviews/DO_NOT_DISTURB.md` |

## 4. Dispatch sequence

0. **Assignment-process FINAL receipt gate.** Read `references/ASSIGNMENT_MILESTONE_PROCESS.md`. After accepted M4 and Ph4 admission, run `python scripts/assignment_milestone_checkpoint.py begin --project-root <project-root> --milestone FINAL`, then run `python scripts/assignment_process_gate.py --project-root <project-root> --stage final --emit-receipt reviews/.harness/assignment/ready/gate_receipt_FINAL_<utc>.json`; add `--exemplar-conditioning` when the approved final dispatch uses domain-native exemplars. Planner runs `python scripts/assignment_dispatch_preflight.py --project-root <project-root> --receipt <ready-path> --expected-target FINAL --consumer planner --write-path milestones/M5_final_paper.md --write-path submission_bundle/final_manuscript.md`, then puts the returned reserved path in `assignment_gate_receipt: <reserved-path>` and `assignment_gate_target: FINAL`. Generator stages exactly both receipt-scoped outputs and publishes through `assignment_writer_commit.py`; there is no second preflight or direct final-path write. Planner then records public FINAL and closes it only through checkpoint `accept --milestone FINAL --terminal-evidence <path>`. Any non-zero result blocks final-paper drafting and Ph4 Generator dispatch. The gate requires accepted M1-M4, M5 in progress, all in-scope sections at Ph4, and current/non-stale wiki grounding (or an authorized opt-out). Exemplar conditioning remains allowed, with Yu as surface centroid and Dennett as argument-only, never a surface-emulation target. Cancellation or pre-commit abort invokes `assignment_receipt_invalidate.py`.

1. **Planner Phase 0 (preflight, MCR gate).** Read `reviews/phase_state.json` top-level fields and every section. Compute `[Ph3-STALE]` for every Ph3 section. Assert all of:
   - every section's `current_phase == "Ph3_converged"` OR `ceiling_locked == true` at its `applicable_ceiling`;
   - no section carries computed `[Ph3-STALE] == true`;
   - every section has `pre_mcr_deep_pass_completed == true` (absent reads as false at the gate).

   If any condition fails, emit the MCR per §2 and halt. Do not proceed to Ph4 dispatch until the MCR clears. A stale section blocks with `E-MCR-BLOCKED-Ph3-STALE` and the `[MCR-BLOCKED-Ph3-STALE]` notification; the user must ask the Planner to append a `ReengagementSignoffRow` on each stale section before the MCR can replay. A section missing the deep-pass flip blocks with **`E-MCR-PRE-DEEP-PASS-REQUIRED`** — schedule a `check_profile: deep` `/run-iterate` pass per §2.1 item 4.
2. **`pre_phase_advance_check.py` (terminal run, all seven clauses).** Runs the full guardrail per `PHASE_PROTOCOL.md §7.3`, with clause (f) (MCR clearance including the ceiling-lock disjunction and `[Ph3-STALE] = false` on every section at admission time) in its manuscript-wide mode. Any failure refuses admission.
3. **MCR admission (`mcr_admission` trigger).** Planner writes an `mcr_admission` row (trigger 6) to the manuscript-scope log. Ph4 admission is granted.
4. **Ph4 full Evaluator pass.** Dispatch the Evaluator for the Ph4 pass. Runs the Ph3 dispatch sequence (`skills/run-phase-3/SKILL.md §5`, steps 4–12 — the **`deep`** envelope) with three modifications:
   - **External verifiers move from optional to required** (§5 below). A verifier probe failure that was advisory at Ph3 is blocking at Ph4.
   - **Precision budget tightens.** Every Reflector Phase 2.5.1 audit item runs at the Ph4 severity floor. Findings that were MAJOR at Ph3 are BLOCKER at Ph4 per the floor column.
   - **All register-specific passes run** if the project's classification triggers them (IS-theory, Suchman, Sexton, public-interest-accountability).
5. **Generator fix cycle (if BLOCKERs exist).** Standard Generator dispatch under the consolidated findings report. No Self-Ph1 Verdict.
6. **Evaluator re-check.** Confirm every BLOCKER is resolved. A remaining BLOCKER blocks G.4 sign-off entirely.
7. **G.4 sign-off artefact (mandatory).** Evaluator produces the G.4 sign-off per `MASTER_research_and_paper_guidelines.md §G.4`. Row 8.5 (SAFEGUARD layer outcome) must be CLEAN. Written to `reviews/g4_signoff_<YYYY-MM-DD>.md`.
8. **Reflector-full dispatch (close-out).** Dispatch `/run-reflection mode: full` and follow `agents/reflector-closeout.md`. Reflector-full:
   - scans the entire `phase_state.json` history (including retired-but-migrated `confirmation_failed` rows) for aggregated patterns (NEW-H-4);
   - runs the full Phase 2.5.1 grounding audit at Ph4 severity floors;
   - synthesises lessons learned (Phase 3);
   - proposes skill-development actions (Phase 4);
   - updates memory files (Phase 5): `research_notes/lessons_learned.md` and `reviews/DO_NOT_DISTURB.md`.
9. **Planner formalisation of plugin proposals.** Any skill-development proposals from Reflector-full Phase 4 are formalised by the Planner into `reviews/plugin_proposals/<cycle_id>.md`, emitting a `plugin_update_proposed_by_planner` row (trigger 26). User approves before package release.
10. **User checkpoint on G.4 + Reflector report.** Planner presents the G.4 artefact and the Reflector-full report to the user for explicit sign-off. Approval here is the terminal approval — the manuscript ships.
11. **Coupling D M5 wiki ingest (deferred).** On terminal approval, the Planner may dispatch SK-17 `ingest-m5-to-wiki`, which returns a deferred structured result (`WIKI_WRITE_TRANSACTION_UNAVAILABLE`). Do **not** write an `m5_wiki_ingest` success row and do **not** fabricate a Wiki source page. Primary ship/approval proceeds.
12. **Terminal state write.** Planner writes the final `user_approval` row (trigger 2) with `new_tier: "Ph4"`. `terminal_tier_reached: true` is set at manuscript scope.

## 5. External verifiers — required at Ph4

The three external-verifier classes move from optional at Ph3 to required at Ph4:

- **Zotero MCP citation verification.** Every citation must be resolvable via Zotero search/fetch or explicitly marked `[UNVERIFIED]`. Rule 7a BLOCKER floor at Ph4.
- **Scholar Gateway render-contract compliance.** If Scholar Gateway output was consumed in any prior cycle, the render-contract audit (Reflector §Phase 2.5.1 item 9a) must pass. Missing session footer is a BLOCKER at Ph4.
- **Coupling E.2 graph-grounding overlay.** Always required (same as Ph3). The echo-detector rate threshold at Ph4 is stricter: ≥15% ECHO+SHALLOW fires `[COUPLING-E.2 DEGRADED]` (vs 30% at Ph3).

Register-specific passes are required conditionally: a Suchman-register project runs the Suchman register audit; an IS-theory project runs the IS-theory pass; a policy-critical project runs the public-interest-accountability pass.

## 6. G.4 sign-off

The G.4 sign-off is a single-page structured artefact specified in `MASTER_research_and_paper_guidelines.md §G.4`. Rows cover: contribution claim stability, abstract/body correspondence, citation integrity, deterministic-pattern clean state, SAFEGUARD outcome, register conformance, external-verifier outcomes, Coupling E.2 compliance, and final Evaluator sign-off. Row 8.5 — the SAFEGUARD layer outcome — must be filled in full; a partial or placeholder G.4 8.5 row blocks sign-off.

## 7. Verdict and approval handling

See `references/PHASE3_PHASE4_COMMON_ENVELOPE.md §10` for shared Approve/Reject/Retraction patterns. Ph4-specific verdicts:

- **G.4 CLEAN + user Approve.** Planner writes a final `user_approval` row with `new_tier: "Ph4"` (promoting every section from `Ph3_converged` to `Ph4`). The manuscript ships. The Reflector-full close-out report is preserved as the terminal reflection. `terminal_tier_reached: true`.
- **G.4 has a BLOCKER row.** Approval is not offered. Planner dispatches a follow-up Generator cycle targeted at the blocking row. Ph4 cannot ship with an unresolved G.4 BLOCKER.
- **G.4 has a MAJOR row.** User may explicitly override with a documented rationale (e.g., "venue deadline; MAJOR will be addressed in camera-ready"). The override is recorded as a `notes` field on the `user_approval` row with the rationale.
- **User Reject at G.4 checkpoint.** Section stays at `Ph3_converged`. Planner writes `user_rejection`. Follow-up cycle may be dispatched or the user may retract.
- **Retraction from Ph4 or Ph3_converged.** User-initiated. Drops the section back to the user's chosen rung and all subsequent cycles re-climb the ladder.

## 8. Ph4 → Ph3 demotion paths (EG-1 and EG-7)

Two legal demotion paths exist at Ph4:

### 8.1 EG-1 (Ph4 → Ph3 on grounding violation)

Fires when a Rule 1–7 grounding violation surfaces at the terminal rung. The section is DEMOTED `Ph4 → Ph3` (trigger `eg1_ph4_downgrade_to_ph3`, trigger 23). `last_approved_phase` mutates to Ph3. The MCR will re-admit once the section reaches a new `TerminalSignoffRow`. Prior Ph4 audit rows are preserved.

### 8.2 EG-7 (Ph4 → Ph3 re-admission after class change)

Fires when the manuscript's (or a section's) classification changes during Ph4 Finalize & Close — e.g., venue switch, P-stage promotion, or Class-1 verifier set change. The section is DEMOTED `Ph4 → Ph3` (trigger `eg7_mcr_readmission_after_class_change`, trigger 22). At least one Ph3 iteration must run before the MCR is replayed for re-admission.

## 9. Required outputs

- `reviews/final_round_report_<round_id>.md` — F8 human-facing synthesis (Planner assembly).
- F7 evidence packets for Ph4 verifier and safeguard passes under `reviews/.harness/evidence/<event_id>.json` with `events.jsonl` rows.
- `reviews/mcr_<YYYY-MM-DD>.md` — the MCR admission artefact.
- Updated `reviews/phase_state.json` reflecting terminal transitions and wiki ingest triggers.

### Exception report surfaces

Additional Markdown artefacts at Ph4 severity floors (see `skills/run-phase-3/SKILL.md` exception list where the full Ph3 stack is replayed), plus:

- `reviews/ph4_external_verifier_<cycle_id>.md` — required-verifier probe results.
- `reviews/reflection_report.md` — Ph4 close-out Reflector-full output; includes Phase 2b aggregated confirmation-failed history audit per NEW-H-4.
- `reviews/g4_signoff_<YYYY-MM-DD>.md` — G.4 sign-off artefact.
- `reviews/plugin_proposals/<cycle_id>.md` — Planner-formalised plugin proposals from Reflector-full Phase 4.
- Updated `research_notes/lessons_learned.md` and `reviews/DO_NOT_DISTURB.md` from Reflector-full Phase 5 memory updates.
- Updated `reviews/phase_state.json` — terminal `user_approval` row (`new_tier: "Ph4"`), `terminal_tier_reached: true` at manuscript scope. Do **not** write `m5_wiki_ingest` on deferral.
- LLM wiki source page for the manuscript (Coupling D) — **not written** while `WIKI_WRITE_TRANSACTION_UNAVAILABLE`; record deferred status instead.

## 10. Escalation paths

- **MCR cannot clear (sections permanently stuck).** User decides: apply ceiling overrides to exclude stuck sections from Ph4 (R-02 respects overrides), retract stuck sections for substantial redrafting, or adjust `default_final_phase` to a rung every section can reach.
- **MCR blocked by [Ph3-STALE].** User signs `ReengagementSignoffRow` on each stale section through the Planner's re-engagement intent. MCR replays automatically on the next `/run-iterate`.
- **MCR blocked by `E-MCR-PRE-DEEP-PASS-REQUIRED`.** User runs a full `run-phase-3` iteration with F6 `check_profile: deep` on each affected section; Planner flips `pre_mcr_deep_pass_completed` on close (`phase_state_schema.md` §2.1). MCR replays when all sections read `true`.
- **G.4 BLOCKER after two resolution cycles.** Planner presents the structural issue and prompts for retraction to Ph3 for more substantial repair.
- **External verifier reachability failure.** Gate for Ph4 — Planner notifies the user and holds dispatch until the verifier is reachable or the user explicitly waives the requirement with a documented rationale.
- **EG-1 (grounding violation at Ph4).** Demotes Ph4 → Ph3 (see §8.1).
- **EG-7 (classification change at Ph4).** Demotes Ph4 → Ph3 (see §8.2).

## 11. Renamed surfaces

See `references/PHASE3_PHASE4_COMMON_ENVELOPE.md §8` for the full v0.6.0 → v0.7.0 → v0.7.4 vocabulary rename table. Ph4-specific note: `run-tier-4` → `run-phase-4` skill rename; tier-named alias removed at v0.8.0 (v0.7.5 RC target absorbed per upgrade architecture D-1/D-2).

## 12. What this stage does NOT do

- **No auto-advance past Ph4.** Ph4 is terminal. Approval at Ph4 ships the manuscript; no Ph5 exists.
- **No bypass of the MCR.** The MCR is a structural gate — the Planner rejects a direct Ph4 invocation on an un-cleared manuscript.
- **No optional external verifiers.** All three classes move to required.
- **No Generator Self-Ph1 Verdict.** Retired at v0.7.0.
- **No Confirmation Mode.** Retired at v0.7.0.
- **No T4R response-letter work.** T4R (renamed from T3R at v0.7.0; preserved at v0.7.4) is a sibling ladder of Ph3 / Ph4 (see SK-11 `response-letter-review`); rebuttal/response documents follow their own artefact contract and do not flow through this skill.

## 13. Trigger vocabulary

- "Ph4" · "phase 4" · "finalize & close" · "ship stage" · "terminal stage" · "finalize"
- "submission review" · "final review" · "pre-submission check" · "submission-bound review" · "resubmission review" (all legacy; routed through MCR-first at v0.7.0)
- "prepare for the journal" · "prepare for conference" · "thesis submission" · "camera-ready"
- Auto-invoked by Planner after a clean MCR when every section reaches `Ph3_converged` (or ceiling-locked) and no section is `[Ph3-STALE]`.

---

*This skill is the terminal stage of the ladder. Approval here ships the manuscript. After ship, the Reflector-full close-out report is archived. Coupling D Wiki ingest via SK-17 is deferred (`WIKI_WRITE_TRANSACTION_UNAVAILABLE`) and does not block ship. `terminal_tier_reached: true` is set at manuscript scope in `reviews/phase_state.json`.*
