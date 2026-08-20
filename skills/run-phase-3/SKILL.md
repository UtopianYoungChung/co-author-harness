---
name: run-phase-3
user-invocable: false
description: "Parked paper-specific compatibility body for /run-iterate. Not a public 0.50 coordinator. Kept on disk for old slash history."
trigger: when the user says "Ph3 iterate-and-converge," "run phase 3," "another iteration," "converge this section," or when the Planner advances after Ph2 approval
version: 0.8.0
---

# run-phase-3 — Ph3 Iterate & Converge


**Parked 0.50 compatibility body.** This skill stays on disk as a
paper-specific compatibility body. It is **not** a public 0.50 coordinator.
Public names are `/run-draft`, `/run-iterate`, `/run-finalize`, and
`/run-reflection`. Do not advertise this parked name as a live public command.


**Grounding basis:** `references/PHASE3_PHASE4_COMMON_ENVELOPE.md` (shared Ph3/Ph4 envelope — convergence metric, [CONVERGENCE-STABLE], [Ph3-STALE], SAFEGUARD invocation, Coupling E.2, Reflector dispatch, ESCALATED handling, renamed surfaces, agent composition, approval patterns); `references/PHASE_PROTOCOL.md §§3.3 (Ph3 charter), 3.3.0 (check_profile / halo_scope), 3.3.1a (P-12 vector), 3.3.3 (Check 8 gate), 3.3.4 (convergence_journal.jsonl), 5 (review pipeline), 7 (escalation gates), 9 (MCR; §3.4 pre-MCR deep pass)`; `references/REVIEW_ORCHESTRATION.md §§Steps 0a/0.2/0b/1–7/8/8.5`; `references/SAFEGUARD_LAYER.md`; `references/DETERMINISTIC_CHECKS.md` (authoritative halo_scope matrix for P-10); `references/ARTEFACT_FRONTMATTER_SCHEMA.md §7a (F6 check_profile)`; `references/phase_state_schema.md §§2, 2.1, 3.1, 3a.2, 3a.3, 4.3`; `agents/evaluator.md §Step 8.5`; `phase_notifications.yaml §§1, 3`; `migrate_convergence_journal_v075.py` (removed from the package tree at v0.7.5 RC; see `CHANGELOG.md`); `scripts/paragraph_hash_map.py`.

## PR-3b.4 Compatibility

The public stage surface is now `/run-iterate`. This file remains the
compatibility body for the full iterate workflow. Legacy `/run-phase-2`
invocations route to `/run-iterate` with `profile: refine`, and legacy
`/run-phase-3-stability` invocations route to `/run-iterate` with
`profile: stability`. Do not advertise Ph2 as a separate public stage in new
guidance.

## Output Profile

**Runtime binding.** Before acting, resolve
`../../references/_snippets/output-profile.md` relative to this `SKILL.md`,
read it in full, and treat it as part of this skill contract. Its canonical
plugin-root identity is `references/_snippets/output-profile.md`. Do not rely
on build-time include expansion.

---

## 1. What this stage does

Ph3 is the **Iterate & Converge** stage of the Lifecycle-Phase Ladder. It governs revision/readiness and does not rename or subdivide the orthogonal M1–M5 deliverable milestones; milestone details live in `MILESTONE_FEEDBACK_HANDOFF_PROTOCOL.md`. Unlike Ph1 and Ph2, Ph3 is an **unbounded loop**: the Generator drafts, the Evaluator runs the envelope selected by the round’s F6 **`check_profile`** (full seven-step pass for `deep`; narrowed passes for `refine` / `structural` per §4.5), the Planner tracks `convergence_metric` (scalar or P-12 object in `convergence_journal.jsonl`), and the cycle repeats until the `[CONVERGENCE-STABLE]` criteria in **§3.2** are met **and** the user appends a `TerminalSignoffRow` to `reviews/ph3_convergence_signoff.md`.

The stage **does not auto-advance on user approval at the iteration boundary.** Approval at the iteration boundary records a `ph3_iteration_round` row (trigger 17) and opens the next iteration. The only structural exit is the terminal signoff row, which carries `is_terminal: true`, flips `current_phase: Ph3 → Ph3_converged`, freezes `convergence_log.md` for the section, and resets `iteration_count_at_current_phase` and `cumulative_drift_lines_since_approval` to `0`.

External verifiers (Zotero MCP citation probe, Scholar Gateway, register-specific passes) are **optional at Ph3 and required at Ph4**. The Coupling E.2 graph-grounding overlay always runs at Step 0.2.

## 2. Renamed surfaces

See `references/PHASE3_PHASE4_COMMON_ENVELOPE.md §8` for the full v0.6.0 → v0.7.0 → v0.7.4 vocabulary rename table.

## 3. Ph3-loop semantics

### 3.1 Convergence metric, [CONVERGENCE-STABLE], and [Ph3-STALE]

The shared convergence-metric contract (scalar vs P-12 object, journal shape, `[CONVERGENCE-STABLE]` window rules) and the `[Ph3-STALE]` computation are specified in `references/PHASE3_PHASE4_COMMON_ENVELOPE.md §§3–4`. This skill adds the following Ph3-specific behaviours:

**[CONVERGENCE-BLOCKED-ACCESSIBILITY].** If the line-diff metric is stable but canonical Check 8 evidence recomputes to BLOCKER, the Planner emits `[CONVERGENCE-BLOCKED-ACCESSIBILITY]`. A–H membership and G/H inclusion are derived from the profile and validated transition event projection. VE never contributes. No prose flag or classification date changes the gate.

**[CONVERGENCE-BORDERLINE-ACCESSIBILITY].** If the line-diff metric is stable and Check 8 carries MAJORs but no BLOCKERs, the Planner emits `[CONVERGENCE-BORDERLINE-ACCESSIBILITY]` on a terminal-signoff election: the write succeeds, but the user is prompted to confirm the open MAJORs have been reviewed and accepted. The MAJOR list is captured in the `TerminalSignoffRow`’s `notes` field for audit trail.

**`paragraph_hash_map`** on journal rows is optional at v0.8.0 (P-10); when present it comes from `scripts/paragraph_hash_map.py` at Planner Phase 0.6 per protocol.

### 3.2 Drift threshold demotion at Ph3

At Ph1 / Ph2, `cumulative_drift_lines_since_approval > tolerant_drift_threshold` triggers `fingerprint_reset` and forces re-review. At Ph3 the same exceedance is **demoted** to `W-Ph3-DRIFT-EXCEEDED-TOLERANT` (warning, not demotion of phase) per `phase_state_schema.md §4.3`. Ph3's unbounded-loop contract is preserved.

### 3.3 ESCALATED finding handling

See `references/PHASE3_PHASE4_COMMON_ENVELOPE.md §7` for the shared Linear-Accountability contract (triggers 15/16, ownership transfer, MCR admission prerequisites).

## 4. Agent composition at Ph3

See `references/PHASE3_PHASE4_COMMON_ENVELOPE.md §9` for the shared four-agent integrity guarantee. Ph3-specific roles:

| Agent | Role at Ph3 | Surfaces |
|---|---|---|
| **Planner** | Orchestrates each iteration; authors F6 with `check_profile`; tracks `convergence_metric` + journal rows; sets `pre_mcr_deep_pass_completed` when a `deep` iteration closes (§2.1); computes `[Ph3-STALE]` on every bootstrap; opens / freezes `convergence_log.md`; writes all `phase_entry_log` rows; runs `pre_phase_advance_check.py`. | `reviews/convergence_log.md`, `reviews/ph3_convergence_signoff.md`, `reviews/dispatch_plan_<cycle_id>.md`, `reviews/convergence_journal.jsonl` |
| **Evaluator** | Runs the **F6-selected** envelope (§4.5): full seven-step pass + all `§8.5` items when `check_profile: deep`; narrowed deterministic / judgment / SAFEGUARD scope when `refine` or `structural`. Coupling E.2 at Step 0.2 when scheduled. Emits consolidated findings. Rule 1 full-file reads apply where the protocol binds them. | `reviews/ph3_findings_<cycle_id>.md`, `reviews/consolidated_findings_report.md`, `reviews/safeguard_layer_results.md`, `reviews/graph_overlay_<date>.md` |
| **Generator** | Applies fixes per the consolidated findings; logs the iteration. Does NOT emit a Self-Ph1 Verdict (retired). | `manuscript/*.md`, `manuscript/revision_log.md` |
| **Reflector-lightweight** | Optional integrity probe per iteration. The aggregated `Phase 2b` audit and lessons-synthesis are deferred to Ph4 (Reflector-full). | `reviews/ph3_reflector_probe_<cycle_id>.md` (optional) |

## 4.5 v0.8.0 — `check_profile` dispatch (F6 → Evaluator envelope)

Each full Ph3 iteration is opened under a fresh F6 `planner_dispatch_plan` (`ARTEFACT_FRONTMATTER_SCHEMA.md §7a`) that declares **`check_profile`** ∈ {`refine`, `structural`, `deep`} per `PHASE_PROTOCOL.md §3.3.0`. The Evaluator **does not** assume a single static envelope: it reads `check_profile` (and the F6 `checks_scheduled[]` list, `structural_delta_flag`, `parallel_dispatch`, `threshold_version` where present) and dispatches as follows.

| `check_profile` | Evaluator contract (normative summary) |
|---|---|
| **`deep`** | **Full Ph3 parity** with the pre-v0.8.0 ladder: Steps 0a (full deterministic set on the section), 0.2 (Coupling E.2), 0b (optional external verifiers at Ph3), Steps 1–7 on the full section body, Step 8, Step 8.5 (all eight SAFEGUARD checks). This profile satisfies the **pre-MCR Ph3-deep pass** safety net (`phase_state_schema.md` §2.1 `pre_mcr_deep_pass_completed`; Planner flips the bool on the Phase 5.5 log-write that closes an iteration whose F6 carried `check_profile: deep`). |
| **`refine`** | **P-10 diff-scoped tightening:** deterministic checks, SAFEGUARD invocations, and judgment steps run on the **diff + declared `halo_scope`** for each scheduled check (`paragraph` \| `immediate_neighbour` \| `containing_section`) per the authoritative matrix in `DETERMINISTIC_CHECKS.md` + `SAFEGUARD_LAYER.md`. Rule 1 full-file grounding floor still applies where the protocol binds it. Steps 0.2 / 0b / 1–7 / 8 / 8.5 execute **only** for checks the F6 `checks_scheduled[]` enumerates; do not silently expand scope beyond the dispatch plan. |
| **`structural`** | **Section-structure pass:** heading/boundary/anchor-class edits; broader than `refine` when `structural_delta_flag: true` on the F6 row. Envelope is still **F6-driven** — default expectation is full-body structural verification (Steps 1–7 on affected headings) plus Step 0a on structural-risk checks and Step 8.5 on all eight SAFEGUARD checks unless the F6 explicitly narrows `checks_scheduled[]` under user-approved modification. |
| **`stability`** | **Byte-stable inheritance pass:** route through `skills/run-iterate/SKILL.md`'s stability profile. It preserves the old S-0 gate and reduced grounding + deterministic Check 8 counter envelope from legacy `run-phase-3-stability`, escalates via trigger 30 on any finding, and never satisfies `pre_mcr_deep_pass_completed`. |

**User override** of `check_profile` at the F6 approval checkpoint is recorded in F6 `notes` (`PHASE_PROTOCOL.md §3.3.0`).

**Relationship to `run-phase-3-stability`:** `run-phase-3-stability` is a legacy compatibility command for `/run-iterate --profile stability`. A stability-mode round (`stability_sub_mode_anticipated: true` or `profile: stability`) always runs the reduced grounding + Check-8-counter envelope; on trigger 30 escalation, the chained full iterate pass picks up `check_profile` from the new F6 the Planner emits for the escalated round (often `deep` if the escalation was structural or verifier-drift).

## 5. Dispatch sequence (per iteration)

1. **Planner Phase 0 (preflight).** Read `reviews/phase_state.json`. Confirm `current_phase: "Ph3"`. Confirm `applicable_ceiling >= "Ph3"`. Compute `[Ph3-STALE]` for this section. If stale, surface the warning and prompt the user to append a `ReengagementSignoffRow` before continuing — the iteration may proceed, but Ph4 admission is blocked while staleness is computed true.
2. **Planner Phase 0.6 (F6 dispatch plan).** Author or consume the round’s F6; read **`check_profile`** and **`checks_scheduled[]`**. If absent, treat as **`deep`** for safety (full envelope) until the Planner repairs the F6 — do not invent a narrower profile without user-approved F6 text.
3. **Branch on `check_profile` (Evaluator entry).** Execute **§4.5** envelope for `refine` \| `structural` \| `deep` before continuing to numbered steps — the steps below spell out the **`deep`** default; **`refine`** / **`structural`** substitute diff-scoped or structural-scoped work per §4.5 and the F6 list.
4. **Evaluator Step 0a (DETERMINISTIC_CHECKS).** For **`deep`:** full set on the entire section body. For **`refine`:** scoped per P-10 + F6. For **`structural`:** as F6 schedules (structural-risk subset minimum).
5. **Evaluator Step 0.2 (Coupling E.2 graph-grounding overlay).** Dispatch `graph-grounding-overlay` when the F6 schedule includes it (always for **`deep`**; for **`refine`** only if scheduled). The Evaluator treats graphify as a courier, not an authority — every severity assignment carries an `Independent reasoning:` note (Reflector §8a compliance). Severity floors per Reflector Phase 2.5.1 Ph3 column.
6. **Evaluator Step 0b (external-verifier probes, optional at Ph3).** When scheduled (default on **`deep`**). Probe Zotero MCP for citation-dependent findings; probe Scholar Gateway for Class-1 citation render-contract checks; probe register-specific passes per the project's classification (IS-theory, Suchman, Sexton-narrative, public-interest-accountability). Record reachability; do not block on failures (failure at Ph3 is advisory; Ph4 raises these to required).
7. **Evaluator Steps 1–7 (judgment pass).** For **`deep`:** run every step of `REVIEW_ORCHESTRATION.md` Steps 1–7 on the section body. For **`refine` / `structural`:** run only on the scoped body per §4.5. Full-file reads mandatory where Rule 1 binds regardless of profile.
8. **Evaluator Step 8 (consolidated findings synthesis).** Synthesize across the executed steps and emit BLOCKER / MAJOR / MINOR severity assignments. Output to `reviews/consolidated_findings_report.md`.
9. **Evaluator Step 8.5 (SAFEGUARD audit — all eight checks).** Per `agents/evaluator.md §Step 8.5` on the checks the F6 schedule includes (all eight for **`deep`** and default **`structural`** unless F6 narrows). Check 8 BLOCKERs feed the §3.3.3 terminal gate — the Planner cannot write a `TerminalSignoffRow` while a Check 8 BLOCKER is open (`PHASE_PROTOCOL.md §3.3.3`).
10. **ESCALATED finding handling.** Any finding the Evaluator marks ESCALATED is appended to `convergence_log.md` with a named owner. The Planner writes an `escalation_named_owner_assigned` row. Transfers (if any) emit an `escalation_owner_transferred` row with a non-empty rationale.
11. **Generator dispatch (if BLOCKERs or MAJORs exist).** Generator applies fixes per `agents/generator.md §Phase 2`. No Self-Ph1 Verdict.
12. **Evaluator re-check.** Confirm flagged findings are resolved or document remaining issues in a short re-check report.
13. **Planner: convergence-metric + journal update.** Populate `reviews/convergence_journal.jsonl` per §3.3.4 (P-12 object when the v0.8.0 writer is active; scalar or migrated object per migration state). Update `sections[].convergence_metric` for the section ledger. Record Check 8 aggregate and accessibility trajectory. Optionally attach `paragraph_hash_map` when Planner Phase 0.6 ran `paragraph_hash_map.py`. Append a `ph3_convergence_signoff_row` (non-terminal) to `reviews/ph3_convergence_signoff.md` if the user signs the iteration. Refresh `ph3_last_activity_at`. **`pre_mcr_deep_pass_completed`:** the Planner sets `sections[].pre_mcr_deep_pass_completed: true` on the Phase 5.5 log-write that **closes** a Ph3 iteration whose F6 declared `check_profile: deep` (`phase_state_schema.md` §2.1); `refine` / `structural` / stability sub-mode iterations do **not** satisfy that safety net.
14. **Stable check.** Apply §3.2 (three-round object rule vs two-round legacy scalar rule). Surface `[CONVERGENCE-STABLE]` when the window is satisfied. The user may ask the Planner to append a `TerminalSignoffRow` for `<heading_path>`.
15. **Iteration boundary.** Planner writes a `ph3_iteration_round` row (trigger 17). The next iteration starts; the loop is unbounded.

## 6. Termination — `TerminalSignoffRow`

The user appends a `TerminalSignoffRow` (`§3a.2`) to `reviews/ph3_convergence_signoff.md` with:

- `is_terminal: true` (mutually exclusive with `is_reengagement: true`)
- `iteration_number` (the iteration this row closes on)
- `convergence_metric_value` (must be non-null; `null` fails with `E-Ph3-CONVERGENCE-NULL-AT-SIGNOFF`)
- `ph3_verdict` (one of `"CONVERGING"` / `"CONTESTED"` / `"DIVERGING"` per Generator self-verdict grammar)
- `user_signature`, `user_signed_at`
- `final_owner_state` (snapshot of ESCALATED-finding owners; empty `{}` if none remain)

**Gate precondition — Check 8 accessibility (§3.3.3).** Before writing the terminal row, the Planner queries `reviews/safeguard_layer_results.md` for the most recent Check 8 aggregate verdict. If the verdict is `BLOCKER`, the Planner **refuses the write** and emits `E-Ph3-ACCESSIBILITY-BLOCKER-AT-SIGNOFF` per `phase_state_schema.md §6.1`. A row with trigger `ph3_accessibility_blocker_surfaced` is appended to `phase_entry_log` naming the failing Sub-check(s) (A/B/C/D/E/F) and locator(s). The section remains at `current_phase: Ph3`; the refused write does not consume an iteration budget.

**Effects of the terminal row (gate precondition met):**

1. `current_phase` flips `Ph3 → Ph3_converged`.
2. A `ph3_convergence_signoff_terminal` row (trigger 20) is written to `phase_entry_log`. Its `notes` field documents that Check 8 passed at signoff ("Check 8 aggregate: PASS" or "Check 8 aggregate: BORDERLINE with N MAJOR(s) acknowledged").
3. `convergence_log.md` is frozen for this section against further appends.
4. `cumulative_drift_lines_since_approval` resets to `0`.
5. `iteration_count_at_current_phase` resets to `0`.

The section is now eligible for Ph4 admission — but Ph4 admission is a **manuscript-wide** decision gated on the MCR.

## 7. Re-engagement — `ReengagementSignoffRow`

If the Planner computes `[Ph3-STALE] = true`, the user clears the stale flag by appending a `ReengagementSignoffRow` (`§3a.3`) with:

- `is_reengagement: true` (mutually exclusive with `is_terminal: true`)
- `cleared_stale_at` (the timestamp of the Planner pass that recorded the stale flag)
- `iteration_number` (carries the same value as the last prior row — re-engagement does NOT advance the iteration)
- `user_signature`, `user_signed_at`

**Effects of the re-engagement row:**

1. `ph3_last_activity_at` updates to `row_timestamp`. The next Planner pass mechanically computes `[Ph3-STALE] = false`.
2. A `ph3_stale_reengagement_signoff` row (trigger 19) is written to `phase_entry_log`.
3. `current_phase` does NOT flip.
4. `iteration_count_at_current_phase` and `cumulative_drift_lines_since_approval` are PRESERVED.

## 8. Approval handling (per iteration)

See `references/PHASE3_PHASE4_COMMON_ENVELOPE.md §10` for the shared Approve/Reject/Defer/Retraction patterns. Ph3-specific additions:

- **User Approve + TerminalSignoffRow appended.** Planner writes the `ph3_convergence_signoff_terminal` row; `current_phase: Ph3_converged`; section eligible for MCR-driven Ph4 admission.
- **User Approve with `applicable_ceiling == "Ph3"` → ceiling-lock.** Approval can ceiling-lock at Ph3 if the section's ceiling is Ph3; no flip to `Ph3_converged` is required — the section terminates at Ph3 with `ceiling_locked: true`.
- **User Defer.** `ph3_last_activity_at` is NOT refreshed by a defer row, so deferral can accumulate staleness.

## 9. Required outputs

- Manuscript delta or approved no-change rationale per iteration.
- Compact entries in `manuscript/revision_log.md`.
- State updates in `reviews/phase_state.json` when gates fire.
- Evidence packet(s) at `reviews/.harness/evidence/<event_id>.json` (and `events.jsonl` rows) per iteration capturing deterministic, findings envelope, safeguard, and convergence signals.
- Human-facing exception report only when an escalation rule fires.

### Exception report surfaces

Legacy Markdown stacks may still be emitted on exception paths or when the user requests full prose artefacts:

- `reviews/ph3_deterministic_<YYYY-MM-DD>_<cycle_id>.md` — full Step 0a output.
- `reviews/graph_overlay_<YYYY-MM-DD>.md` — Coupling E.2 overlay findings.
- `reviews/ph3_findings_<YYYY-MM-DD>_<cycle_id>.md` — Steps 1–7 raw findings.
- `reviews/consolidated_findings_report.md` — Step 8 synthesis (exception or explicit request).
- `reviews/safeguard_layer_results.md` — Step 8.5 all-eight-check audit.
- `reviews/ph3_recheck_<YYYY-MM-DD>_<cycle_id>.md` — Evaluator re-check after Generator fixes.
- `reviews/convergence_log.md` — ESCALATED-finding ownership; appended on every escalation, frozen by the terminal signoff row.
- `reviews/ph3_convergence_signoff.md` — cumulative signoff file: non-terminal rows per iteration, terminal row at closure, re-engagement rows on staleness clearance.
- `reviews/ph3_reflector_probe_<cycle_id>.md` — optional Reflector-lightweight probe.
- Appended `manuscript/revision_log.md` entries per Generator iteration.
- Updated `reviews/phase_state.json` — atomic writer with the appropriate trigger row per event (`ph3_iteration_round`, `ph3_convergence_signoff_row`, `ph3_convergence_signoff_terminal`, `ph3_stale_reengagement_signoff`, `escalation_named_owner_assigned`, `escalation_owner_transferred`, `user_approval`, `user_rejection`, `user_defer`, `ceiling_locked`).

## 10. Escalation paths at Ph3

- **EG-1 (grounding threat).** BLOCKER in Rule 1–7 grounding at Ph3 forces a re-cycle of the iteration. Persistent BLOCKER through two iterations escalates to retraction-or-redraft.
- **EG-3 (cross-scope reference).** Inherited from Ph2. Ph3 is the rung at which cross-scope dependencies must be resolved.
- **EG-4 (contradiction surface).** Fires when SAFEGUARD Check 4 surfaces an unacknowledged contradiction. Section held at Ph3 until the author either acknowledges the contradiction or revises the co-invocation.
- **EG-5 (DETERMINISTIC_CHECKS threshold breach).** Any-phase; MINOR unless an absolute-or-cannot claim is implicated.
- **EG-6 (override inconsistency warning).** Non-blocking. Fires if the user's `/run-phase-N` override target is inconsistent with `current_phase` or `applicable_ceiling`.

## 11. Relationship to T3R (response-letter manuscript-class)

**Disposition settled 2026-07-07 (aligning with the SKILL_REGISTRY v0.14.0 retirement banner):** the former independent T3R sibling ladder is **retired**; response-letter review is a **manuscript-class within Ph3**, entered via `/response-letter-review`. `T3R` survives only as the historical label of that entry point. A response letter or rebuttal document still follows its own artefact contract (opening strength, discipline provenance, tone a A response letter or rebuttal document follows a different artefact contract (opening strength, discipline provenance, tone audit, coverage completeness, scope hedging, SAFEGUARD integrity checks) and does not feed the staircase's main Ph1→Ph2→Ph3→Ph3_converged→Ph4 advancement. Dispatch T3R via SK-11 directly; do not route through this skill.

## 12. What this stage does NOT do

- **No automatic Ph4 admission.** A `TerminalSignoffRow` produces `Ph3_converged`, not Ph4. The manuscript-wide MCR gates Ph4 admission (`run-phase-4`).
- **No G.4 sign-off.** Ph4 only.
- **No mandatory external verifiers.** Optional at Ph3; required at Ph4.
- **No Generator Self-Ph1 Verdict.** Retired at v0.7.0.
- **No Confirmation Mode.** Retired at v0.7.0.
- **No scheduled Reflector dispatch.** Reflector-full runs only at Ph4 close-out at v0.7.0. Ad-hoc Reflector-lightweight invocations at Ph3 are permitted.

## 13. Trigger vocabulary

- "Ph3" · "phase 3" · "iterate & converge" · "iterate-until-stable" · "Ph3 round" · "third stage"
- "full review" · "run the package" · "comprehensive review" · "standard review" (legacy; routed to Ph3 when the section is at Ph2 and ready to advance)
- Auto-invoked by Planner when a section receives `user_approval` + `ph2_review_completion_signed` at Ph2 and auto-advances.

---

*This skill is the entry point for the Ph3 stage only. To reach Ph4 Finalize & Close, the section must (a) be at `Ph3_converged` (or its ceiling lock at a lower rung), and (b) the manuscript-wide MCR must clear (every section ≥ Ph3_converged or ceiling-locked, no `[Ph3-STALE]` flags computed true). See SK `run-phase-4`.*
