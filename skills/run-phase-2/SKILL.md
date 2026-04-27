---
name: run-phase-2
description: "Ph2 Review & Revise — first Evaluator engagement. Run full local-scope pass (Steps 1–3 + checklist + SAFEGUARD 1/4/5/8). When sd_sr_required=true, read i* SD/SR models first. Produces ph2_review_completion.md. Full-file reads mandatory. Trigger: \"Ph2,\" \"review pass,\" \"run phase 2,\" \"first evaluator pass,\" or after Ph1 approval."
trigger: when the user says "Ph2 review-and-revise," "run phase 2," "first evaluator pass," or when the Planner auto-advances after Ph1 approval
version: 0.7.4
---

# run-phase-2 — Ph2 Review & Revise

**Grounding basis:** `references/PHASE_PROTOCOL.md §§3 (lifecycle), 3.1.2 (SD/SR opt-in gate — v0.7.1), 3.2 (Ph2 charter), 5.3 (Evaluator Ph2 read-contract, conditional on sd_sr_required), 7 (escalation gates; EG-3 cross-scope)`; `references/GROUNDING_PROTOCOL.md §Rule 1 full-file reads (phase-gated digest exception retired at v0.7.4)`; `references/phase_state_schema.md §2 (15-field section object), §3.1 (30-trigger enum), §3a.1 (PhaseEntryLogRow shape), §6.1 failure codes including E-Ph2-SD-UNGROUNDABLE (conditional) / E-PSTAGE-REQUIRED-AT-Ph2`; `agents/evaluator.md`; `phase_notifications.yaml §1 (ph2_entry, ph2_exit_signed)`.

---

## 1. What this stage does

Ph2 is the **Review & Revise** stage of the Lifecycle-Phase Ladder and absorbs the activities formerly scoped under milestone M4a. It is the first stage at which the Evaluator engages — the Evaluator reads the Ph1 draft and the declared P-stage, and produces a local-scope findings report. **When `sd_sr_required: true` in `reviews/classification.md`** (v0.7.1 opt-in — see `PHASE_PROTOCOL.md §3.1.2`), the Evaluator additionally opens the SD/SR models as a read-prerequisite before the prose read; when the flag is absent or `false` (the v0.7.1 default), the read-prerequisite silently skips. The Generator applies fixes; the Evaluator re-checks; the cycle closes with a user-signed `ph2_review_completion.md` artefact.

The full-file read contract is mandatory at every phase (the Rule 1 phase-gated digest exception was **retired at v0.7.4** — no diff-scoping shortcut remains at any rung). Evaluator **Confirmation Mode is retired at v0.7.0** (`PHASE_PROTOCOL.md §11 item 3`): there is no shortcut path, no self-Ph1-verdict eligibility probe, and no `confirmation_failed` emission. Every Ph2 entry runs the full local pass.

Approval at Ph2 auto-advances the section to Ph3 unless the applicable ceiling is Ph2, in which case approval ceiling-locks the section at Ph2.

## 2. Preconditions enforced at Ph2 entry

`pre_phase_advance_check.py` (clauses (a), (b), (d), (g)) runs at Ph2 entry *in addition to* the Ph1-exit check. Failures refuse Ph2 admission:

| Precondition | Failure code | Source |
|---|---|---|
| `reviews/ph1_draft_completion.md` exists with YAML frontmatter `phase: "Ph1"` | `E-MISSING-Ph1-SIGNOFF` | clause (a) |
| 15-field `SectionStateObject` populated; `phase_goal_declared` / `phase_deliverable_path` non-empty | `SECTION_MISSING_FIELD` | clause (b) |
| `ph1_pstage_declaration` is non-null | `E-PSTAGE-REQUIRED-AT-Ph2` | clause (d) |
| i\* structural-completeness validator passed at Ph1 (`imodel_structural_validation_signed` row in log) — **conditional on `sd_sr_required: true`** | `E-IMODEL-STRUCTURALLY-INCOMPLETE` | clause (e); trivially passes when `sd_sr_required` is absent or `false` |
| SD/SR models are groundable by the Evaluator (readable, non-empty, well-formed) — **conditional on `sd_sr_required: true`** | `E-Ph2-SD-UNGROUNDABLE` | clause (e) + Evaluator read-contract; precondition silently skips when `sd_sr_required` is absent or `false` |
| Row-shape conformance on the last 100 `phase_entry_log` rows | `E-ROW-SHAPE-VIOLATION` | clause (g) |

If any precondition fails, the Planner refuses dispatch and surfaces the failure via `phase_notifications.yaml §4 (t1_t2_signoff)`.

## 3. Agent composition at Ph2

| Agent | Role at Ph2 | Surfaces |
|---|---|---|
| **Planner** | Orchestrates the round; reads the Ph1 exit artefact; dispatches the Evaluator; runs `pre_phase_advance_check.py`; writes all `phase_entry_log` rows. | `reviews/ph2_review_completion.md` |
| **Evaluator** | **First engagement.** Runs `REVIEW_ORCHESTRATION.md` Steps 1–3 + integrated checklist; scans for cross-scope references; runs the SAFEGUARD subset (checks 1, 4, 5, and — new at v0.7.2 — 8) per `SAFEGUARD_LAYER.md` Step 8.5; emits findings with BLOCKER/MAJOR/MINOR severities. Full-file reads mandatory. **When `sd_sr_required: true`** (`PHASE_PROTOCOL.md §3.1.2`), additionally reads SD/SR models before the prose (mandatory read-contract per `§5.3`); when the flag is absent or `false` (the v0.7.1 default), the SD/SR read silently skips. | `reviews/ph2_findings_<YYYY-MM-DD>_<cycle_id>.md`, `reviews/ph2_safeguard_<YYYY-MM-DD>_<cycle_id>.md` |
| **Generator** | Applies fixes against consolidated findings; logs edits. **Does NOT emit a Self-Ph1 Verdict** (retired; Ph1 or otherwise). | `manuscript/*.md`, `manuscript/revision_log.md` |
| **Reflector-lightweight** | Optional integrity probe. No `lessons_learned.md` write. Phase 2.5.1 grounding subset only. | `reviews/ph2_reflector_probe_<cycle_id>.md` (optional) |

## 4. Dispatch sequence

0.5. **Planner: snowball-gate re-test (placeholder, S2).** Re-read the section's `references_initialized` field from `reviews/phase_state.json`. If `false` or absent, emit the `W-SNOWBALL-PRECONDITION-UNMET` warning per `phase_notifications.yaml §4` as a re-emission — the `notes` field references the prior Ph1-side emission's `cycle_id` if any (resolvable from the Ph1 `phase_entry_log` rows). The warning is **non-blocking**: Ph2 dispatch proceeds to Step 1 regardless. Rationale: Ph2's Generator work is reactive (review-and-revise against the Ph1 draft) rather than fresh-prose authoring, so the absence of a populated `references/REFERENCES.md` is acceptable for Ph2's local-scope pass; the Ph2 Evaluator may flag missing citations under Rule 7a, but that surfaces as a separate finding rather than a Ph2-admission refusal. **What this step does NOT do at S2:** it does NOT dispatch SK-NEW-A directly, and it does NOT dispatch SK-NEW-B (`claim-coverage-audit`). The Ph2-side dispatch of SK-NEW-A or SK-NEW-B lands at S3/S4 per the implementation strategy §5.4 (S3 ships SK-NEW-B `claim-coverage-audit`) / §5.5 (S4 inserts the full Ph2-side wiring including SK-NEW-C); this Step 0.5 is purely a re-test placeholder that prevents the silent Ph1 → Ph2 advance the prior `references_initialized: false` window would otherwise mask.
1. **Planner Phase 0 (preflight).** Read `reviews/phase_state.json`. Confirm `current_phase: "Ph2"` (advanced from Ph1 by the prior cycle's `user_approval` + `ph1_draft_completion_signed` rows). Confirm `applicable_ceiling >= "Ph2"`. Read the Ph1 exit artefact. Re-confirm the preconditions in §2. On any failure, refuse dispatch.
2. **Planner: Evaluator read-contract staging (conditional).** **Only when `sd_sr_required: true` in `reviews/classification.md`** (`PHASE_PROTOCOL.md §3.1.2`), confirm `reviews/sd_model.md` and `reviews/sr_model.md` are present, non-empty, and parseable. If the Evaluator cannot ground against the SD/SR pair (missing file, malformed YAML frontmatter, validator output stale), emit `E-Ph2-SD-UNGROUNDABLE` and refuse dispatch. The Ph1 validator must re-run (the user returns to Ph1 for the fix). When `sd_sr_required` is absent or `false` (the v0.7.1 default), this sub-step silently skips — no file-presence probe, no `E-Ph2-SD-UNGROUNDABLE` emission, and Ph2 dispatch proceeds directly to the deterministic-checks step.
3. **Evaluator Step 0a (DETERMINISTIC_CHECKS full-file).** Run the full deterministic-check mandatory subset on the **entire section body**, not just the diff. Results to `reviews/ph2_deterministic_<YYYY-MM-DD>_<cycle_id>.md`.
4. **Evaluator Steps 1–3 (local-scope judgment pass).** Run `REVIEW_ORCHESTRATION.md` Steps 1–3 plus the `§2.5.1` audit items marked "must run" at Ph2 in `agents/reflector.md`. Full-file reads for every cited rule (Rule 1 digest exception does not apply).
5. **Evaluator cross-scope scan (EG-3 gate).** Scan for findings or proposed fixes that reference material outside the section's `heading_path`. If any are detected, fire **EG-3 (cross-scope reference mismatch)** per `PHASE_PROTOCOL.md §7` — the section's review escalates to Ph3. Planner records the trigger and the dependent section in `notes`; advancement to Ph3 is permitted only after Ph3 resolves the cross-scope dependency.
5a. **Evaluator SAFEGUARD subset at Ph2 (Step 8.5, scoped to checks 1, 4, 5, 8).** Run `SAFEGUARD_LAYER.md` Check 1 (Regression Guard), Check 4 (Contradiction Audit), Check 5 (Judgment-Call Transparency), and — **new at v0.7.2** — Check 8 (Reader-Experience / Prose Architecture). Check 8 at Ph2 reads the six Sub-checks A–F (paragraph cadence, sentence-length distribution, first-use definition, section-transition signposting, jargon discipline, worked examples at density spikes) and emits an aggregate verdict (CLEAN / BORDERLINE / MAJOR / BLOCKER) against the section. Save the subset results as `reviews/ph2_safeguard_<YYYY-MM-DD>_<cycle_id>.md` and append them as §6a of the findings report. Ph2 Check 8 findings are advisory on Ph2 admission but carry forward to Ph3 where they bind the TerminalSignoffRow accessibility gate (`PHASE_PROTOCOL.md §3.3.3`) — a BLOCKER surfaced here should be resolved during the Ph2 → Ph3 Generator pass rather than deferred.
6. **Evaluator findings report.** Write `reviews/ph2_findings_<YYYY-MM-DD>_<cycle_id>.md` with BLOCKER/MAJOR/MINOR severities, each finding carrying an `Independent reasoning:` note (Reflector §8a compliance) and rule citations.
7. **Generator dispatch (if BLOCKERs or MAJORs exist).** Planner dispatches the Generator with the consolidated findings as the fix plan. Generator edits under `agents/generator.md` Phase 2 against the P-stage register. No Self-Ph1 Verdict is emitted (retired).
8. **Evaluator re-check.** After the Generator cycle, the Evaluator re-runs the affected steps on the fixed paragraphs and emits a short re-check confirming resolution or documenting remaining issues.
9. **Reflector-lightweight probe (optional).** Integrity subset only; no skill proposals; no memory writes. Planner-gated.
10. **Ph2 exit artefact authoring.** Planner writes `reviews/ph2_review_completion.md` naming (i) the findings report path, (ii) the Generator revision log reference, (iii) the re-check report, (iv) the cross-scope dependency resolution status (if EG-3 fired), (v) any Reflector-lightweight probe. User reviews and signs.
11. **`pre_phase_advance_check.py` (Planner phase 5.5).** Eight-clause guardrail (`phase_state_schema.md §6.2`). Clause (c) (ESCALATED-owner linearity) activates here if the Evaluator opened any ESCALATED findings during the round. Clause (h) (Check 8 accessibility gate) does **not** fire at Ph2 — it binds only on `TerminalSignoffRow` writes at Ph3.
12. **User approval checkpoint.** Planner presents the ph2_review_completion artefact, the diff, and the findings + re-check to the user. User Approves or Rejects.

## 5. Approval handling

- **User Approve → auto-advance to Ph3.** Planner writes a `ph2_review_completion_signed` row (trigger 14), then a `user_approval` row (trigger 2) in the same writer session. `current_phase: "Ph3"`, `last_approved_phase: "Ph2"`, `iteration_count_at_current_phase := 0`. `ph3_last_activity_at` is set to the writer timestamp (Ph3 clock starts). The Ph3 entry notification fires per `phase_notifications.yaml §1 ph3_entry`.
- **User Approve with `applicable_ceiling == "Ph2"` → ceiling-lock.** Planner writes `ph2_review_completion_signed`, `user_approval`, and `ceiling_locked` rows; no advance.
- **User Reject → section stays at Ph2.** Planner writes a `user_rejection` row; `iteration_count_at_current_phase += 1`. Iteration-reserve (NEW-H-7) surfaces at `per_phase_budget × 1.5` exhaustion.
- **User Approve attempted with unresolved BLOCKER.** Not permitted. Planner blocks advancement and presents the BLOCKER list. A Ph2 BLOCKER cannot be waived by approval.
- **EG-3 fire.** Cross-scope reference detected. Planner records the trigger; advancement to Ph3 is still possible, but the Evaluator's Ph3 pass must resolve the cross-scope dependency before the Generator's Ph3 iteration terminates.

## 6. Retired surfaces at v0.7.0 (previously visible at Ph2)

| Surface | Status | Notes |
|---|---|---|
| **Evaluator Confirmation Mode (all six steps)** | **RETIRED** | No Ph2-entry shortcut. Every Ph2 entry runs the full local pass. |
| **EG-2 (self-Ph1 verdict mismatch at Ph2 entry)** | **RETIRED** | Removed from the escalation-gate register. Migrated log rows preserved. |
| **`confirmation_failed` trigger** | **RETIRED (read-only)** | v0.6.0-migrated rows preserved; no v0.7.0 write emits it. |
| **Two-column canonical-body diagnostic diff (R-03)** | **RETIRED** | No Confirmation Mode → no diagnostic. Evaluator's local-pass findings report replaces it. |

## 7. Artefacts produced

- `reviews/ph2_deterministic_<YYYY-MM-DD>_<cycle_id>.md` — full-file deterministic subset report.
- `reviews/ph2_findings_<YYYY-MM-DD>_<cycle_id>.md` — Evaluator Steps 1–3 + integrated checklist.
- `reviews/ph2_recheck_<YYYY-MM-DD>_<cycle_id>.md` — Evaluator re-check after Generator fixes.
- `reviews/ph2_reflector_probe_<cycle_id>.md` — optional Reflector-lightweight probe.
- `reviews/ph2_review_completion.md` — signed Ph2 exit artefact (required for Ph2 → Ph3 advance).
- Appended `manuscript/revision_log.md` entries for each Generator cycle (no Self-Ph1 Verdict block).
- Updated `reviews/phase_state.json` — atomic writer with new rows: `ph2_review_completion_signed`, `user_approval` | `user_rejection` | `user_defer` | `ceiling_locked`. On approval, `ph3_last_activity_at` is set to the writer timestamp.

## 8. Escalation paths at Ph2

- **EG-1 (grounding threat).** BLOCKER in Rule 1–7 grounding at Ph2 does not drop the section; it remains at Ph2 for re-review. Re-cycle the Generator fix plan.
- **EG-3 (cross-scope reference).** Fired on any reference outside the section envelope. Block advance until Ph3 resolves the dependency.
- **EG-4 (contradiction surface).** Not available at Ph2 (EG-4 fires only at Ph3/Ph4). If a contradiction is surfaced at Ph2, the finding is recorded as MAJOR and deferred to Ph3.
- **EG-5 (DETERMINISTIC_CHECKS threshold breach).** Any-phase. Breach is MINOR unless an absolute-or-cannot claim is implicated.
- **Iteration exhaustion.** At `per_phase_budget × 1.5`, Planner surfaces the exhaustion warning and prompts the user for `section_ceiling_override`, an extension grant, or retraction.

## 9. What this stage does NOT do

- **No full seven-step judgment pass.** That lives at Ph3. Ph2's pass is Steps 1–3 + integrated checklist.
- **No convergence metric.** Ph3-only; at Ph2, `convergence_metric` remains `null`.
- **No MCR.** Ph4 admission artefact.
- **No G.4 sign-off.** Ph4 only.
- **No cumulative Ph3 signoff rows.** The `ph3_convergence_signoff.md` file is opened only at Ph3 entry.
- **No external-verifier probing (Zotero / Scholar Gateway / register-specific passes).** Ph3 (optional) and Ph4 (required).
- **No Coupling E.2 graph-grounding overlay.** Ph3 only.

## 10. Trigger vocabulary

- "Ph2" · "phase 2" · "review & revise" · "review pass" · "second stage" · "revise this section"
- Auto-invoked by Planner when a section receives `user_approval` + `ph1_draft_completion_signed` at Ph1 and auto-advances.
- Legacy: "standard review" (disambiguated by Planner — routes to Ph2 if the section is at Ph1 and ready to advance, to Ph3 if the section is already at Ph2 or deeper).

---

*This skill is the entry point for the Ph2 stage only. To proceed past Ph2, the user must sign `ph2_review_completion.md` and approve at the checkpoint in §4 step 12, which auto-advances the section to Ph3 (SK `run-phase-3`) unless ceiling-locked.*
