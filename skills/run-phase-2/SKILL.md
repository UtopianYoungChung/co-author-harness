---
name: run-phase-2
description: "Ph2 Review & Revise — first Evaluator engagement. Runs Step 0.5 preflight (snowball-gate re-test + claim-coverage audit dispatch with auto extension on uncovered claims; non-blocking) then a full local-scope pass (Steps 1–3 + checklist + SAFEGUARD 1/4/5/8). Produces reviews/ph2_review_completion.md. Full-file reads mandatory."
trigger: when the user says "Ph2 review-and-revise," "run phase 2," "first evaluator pass," or when the Planner auto-advances after Ph1 approval
version: 0.7.4
---

# run-phase-2 — Ph2 Review & Revise

**Grounding basis:** `references/PHASE_PROTOCOL.md §§3 (lifecycle), 3.2 (Ph2 charter), 7 (escalation gates; EG-3 cross-scope)`; `references/GROUNDING_PROTOCOL.md §Rule 1 full-file reads (phase-gated digest exception retired at v0.7.4)`; `references/phase_state_schema.md §2 (18-field section object at v0.10.0 S4 — `references_initialized` at S2, `last_coverage_score` at S4), §3.1 (31-trigger enum at v0.10.0 S2 — `seed_snowball_signed` added), §3a.1 (PhaseEntryLogRow shape), §6.1 failure codes including E-PSTAGE-REQUIRED-AT-Ph2`; `agents/evaluator.md`; `agents/planner.md §Phase 3.8` (canonical Ph2 Step 0.5 dispatch contract — three-outcome handler authoritative); `references/phase_notifications.yaml §§1 (ph2_entry, ph2_exit_signed), 4 (W-COVERAGE-BELOW-THRESHOLD, E-COVERAGE-AUDIT-FAILED at v0.10.0 S4; W-SNOWBALL-PRECONDITION-UNMET, E-SNOWBALL-MID-RUN-FAILURE at v0.10.0 S2)`; `skills/claim-coverage-audit/SKILL.md` (SK-34, S3 deliverable — Step 0.5 Part (b) dispatches this skill); `skills/extend-snowball-incremental/SKILL.md` (SK-35, S4 deliverable — auto-dispatched per uncovered claim from SK-34's BELOW_THRESHOLD verdict).

---

## 1. What this stage does

Ph2 is the **Review & Revise** stage of the Lifecycle-Phase Ladder and absorbs the activities formerly scoped under milestone M4a. It is the first stage at which the Evaluator engages — the Evaluator reads the Ph1 draft and the declared P-stage, and produces a local-scope findings report. The Generator applies fixes; the Evaluator re-checks; the cycle closes with a user-signed `ph2_review_completion.md` artefact.

The full-file read contract is mandatory at every phase (the Rule 1 phase-gated digest exception was **retired at v0.7.4** — no diff-scoping shortcut remains at any rung). Evaluator **Confirmation Mode is retired at v0.7.0** (`PHASE_PROTOCOL.md §11 item 3`): there is no shortcut path, no self-Ph1-verdict eligibility probe, and no `confirmation_failed` emission. Every Ph2 entry runs the full local pass.

Approval at Ph2 auto-advances the section to Ph3 unless the applicable ceiling is Ph2, in which case approval ceiling-locks the section at Ph2.

## 2. Preconditions enforced at Ph2 entry

`pre_phase_advance_check.py` (clauses (a), (b), (d), (g)) runs at Ph2 entry *in addition to* the Ph1-exit check. Failures refuse Ph2 admission:

| Precondition | Failure code | Source |
|---|---|---|
| `reviews/ph1_draft_completion.md` exists with YAML frontmatter `phase: "Ph1"` | `E-MISSING-Ph1-SIGNOFF` | clause (a) |
| 15-field `SectionStateObject` populated; `phase_goal_declared` / `phase_deliverable_path` non-empty | `SECTION_MISSING_FIELD` | clause (b) |
| `ph1_pstage_declaration` is non-null | `E-PSTAGE-REQUIRED-AT-Ph2` | clause (d) |
| Row-shape conformance on the last 100 `phase_entry_log` rows | `E-ROW-SHAPE-VIOLATION` | clause (g) |

If any precondition fails, the Planner refuses dispatch and surfaces the failure via `phase_notifications.yaml §4 (t1_t2_signoff)`.

## 3. Agent composition at Ph2

| Agent | Role at Ph2 | Surfaces |
|---|---|---|
| **Planner** | Orchestrates the round; reads the Ph1 exit artefact; dispatches the Evaluator; runs `pre_phase_advance_check.py`; writes all `phase_entry_log` rows. | `reviews/ph2_review_completion.md` |
| **Evaluator** | **First engagement.** Runs `REVIEW_ORCHESTRATION.md` Steps 1–3 + integrated checklist; scans for cross-scope references; runs the SAFEGUARD subset (checks 1, 4, 5, and — new at v0.7.2 — 8) per `SAFEGUARD_LAYER.md` Step 8.5; emits findings with BLOCKER/MAJOR/MINOR severities. Full-file reads mandatory. | `reviews/ph2_findings_<YYYY-MM-DD>_<cycle_id>.md`, `reviews/ph2_safeguard_<YYYY-MM-DD>_<cycle_id>.md` |
| **Generator** | Applies fixes against consolidated findings; logs edits. **Does NOT emit a Self-Ph1 Verdict** (retired; Ph1 or otherwise). | `manuscript/*.md`, `manuscript/revision_log.md` |
| **Reflector-lightweight** | Optional integrity probe. No `lessons_learned.md` write. Phase 2.5.1 grounding subset only. | `reviews/ph2_reflector_probe_<cycle_id>.md` (optional) |

## 4. Dispatch sequence

0.5. **Planner: snowball-gate re-test + claim-coverage audit dispatch (v0.10.0 S4).** Two-part Ph2-entry preflight that runs **after Step 1 (Planner Phase 0 preflight, which validates `phase_state.json` shape and confirms `current_phase: "Ph2"`) and before Step 3 (Evaluator Step 0a deterministic checks)** per architecture §5.2 Edit-2. The numerical label `0.5` is preserved from the S2 placeholder for stable cross-references, but the *executional placement* is between Step 1 and Step 3 in the dispatch sequence — Phase 0 must complete first so Step 0.5's `phase_state.json` reads operate on a validated file. The canonical contract for both parts is `agents/planner.md §Phase 3.8` (the Planner-side authority); this Step 0.5 references that contract rather than duplicating it.

   **Part (a) — snowball-gate re-test (carry-forward from S2).** Re-read the section's `references_initialized` field from `reviews/phase_state.json`. If `false` or absent, emit the `W-SNOWBALL-PRECONDITION-UNMET` warning per `phase_notifications.yaml §4` as a re-emission — the `notes` field references the prior Ph1-side emission's `cycle_id` if any (resolvable from the Ph1 `phase_entry_log` rows). The warning is **non-blocking**: the audit in Part (b) runs even when `references_initialized: false`, and the audit's no-op pathway (`EMPTY_REFERENCES_POOL`) handles the case where REFERENCES.md is absent / unpopulated. Rationale: Ph2's Generator work is reactive (review-and-revise against the Ph1 draft) rather than fresh-prose authoring, so the absence of a populated `references/REFERENCES.md` is acceptable for Ph2's local-scope pass; the Ph2 Evaluator may flag missing citations under Rule 7a, but that surfaces as a separate finding rather than a Ph2-admission refusal.

   **Part (b) — claim-coverage audit dispatch (NEW at S4).** Dispatch SK-NEW-B `claim-coverage-audit` (SK-34 per `references/SKILL_REGISTRY.md`) for the section. The skill reads `manuscript/<section>.md` and `references/REFERENCES.md` and produces `reviews/claim_coverage_<YYYY-MM-DD>_<cycle_id>.md` with a CLEAN or BELOW_THRESHOLD verdict against `claim_coverage_threshold` from `reviews/classification.md` (default 0.8). The Planner's three-outcome handling is canonical at `agents/planner.md §Phase 3.8`; the contract surfaces here are:

   - **Clean exit (CLEAN verdict, score ≥ threshold).** Planner writes `last_coverage_score: <score_ratio>` to the section's SectionStateObject (the v0.10.0 S4 schema-addition field per `phase_state_schema.md §2`); no notification emitted; no SK-NEW-C auto-dispatch. Ph2 proceeds to Step 0a deterministic checks reading against the unchanged REFERENCES.md.
   - **Coverage below threshold (BELOW_THRESHOLD verdict, score < threshold).** Planner writes `last_coverage_score: <score_ratio>`; emits non-blocking `W-COVERAGE-BELOW-THRESHOLD` per `phase_notifications.yaml §4`; **auto-dispatches SK-NEW-C `extend-snowball-incremental`** (SK-35 per `references/SKILL_REGISTRY.md`) for each uncovered claim listed in the audit's `## Uncovered` table, in parallel with the rest of the Ph2 Evaluator pass. SK-NEW-C writes its admits to REFERENCES.md via the atomic-rename pattern (`phase_state_schema.md §5`) so the Evaluator's Step 4 read sees a coherent snapshot — either the pre-extension pool or the post-extension pool, never an inconsistent intermediate state. Race semantics: claims SK-NEW-C resolves before the Evaluator's Step 4 reaches them are read against the extended pool; claims SK-NEW-C cannot resolve in time surface as MAJOR Evaluator findings carrying the `propose_extend_snowball` remediation hint (Generator can defer the missing source to a subsequent round, downgrade the claim to Indirect tier per `GROUNDING_PROTOCOL.md` Rule 4, or remove the claim).
   - **Audit failure (E-COVERAGE-AUDIT-FAILED).** Planner emits `E-COVERAGE-AUDIT-FAILED` per `phase_notifications.yaml §4`; does NOT update `last_coverage_score`; does NOT auto-dispatch SK-NEW-C; **proceeds to Step 0a regardless** (Ph2 admission is NOT blocked — the audit is advisory). The user adjudicates the audit failure at cycle close per the notification's recommended-action guidance. This non-halting semantics is the load-bearing distinction from Ph1 Step 4.5's outcome (iii), which DOES halt; the asymmetry is anchored at `agents/planner.md §Phase 3.8` and reflects the architecture §5.2 Edit-2 contract that Step 0.5 is advisory at the admission layer.

   The eight `pre_phase_advance_check.py` admission-rule clauses are unchanged at S4 — the audit's verdict feeds the Evaluator's Step 4 / Step 8 reads as a discovery-layer signal, not as a binding admission gate. **What this step still does NOT do at S4:** it does NOT block Ph2 admission on a sub-threshold score (per architecture §5.2 Edit-2 paragraph 4); it does NOT modify the manuscript or any `core corpus` REFERENCES.md row (SK-NEW-C admits land in the `snowball` table only); it does NOT re-audit after SK-NEW-C admits (re-auditing happens at the next Ph2 entry, typically the next round after a Generator fix). The synthesis-alignment fast-path (architecture §5.5.3, fourth coverage-set `synthesis-covered`) and the SK-16 red-link auto-trigger (architecture §5.5.4) are deferred to S4.5 and are out of scope at S4.
1. **Planner Phase 0 (preflight).** Read `reviews/phase_state.json`. Confirm `current_phase: "Ph2"` (advanced from Ph1 by the prior cycle's `user_approval` + `ph1_draft_completion_signed` rows). Confirm `applicable_ceiling >= "Ph2"`. Read the Ph1 exit artefact. Re-confirm the preconditions in §2. On any failure, refuse dispatch.
2. **Evaluator Step 0a (DETERMINISTIC_CHECKS full-file).** Run the full deterministic-check mandatory subset on the **entire section body**, not just the diff. Results to `reviews/ph2_deterministic_<YYYY-MM-DD>_<cycle_id>.md`.
3. **Evaluator Steps 1–3 (local-scope judgment pass).** Run `REVIEW_ORCHESTRATION.md` Steps 1–3 plus the `§2.5.1` audit items marked "must run" at Ph2 in `agents/reflector.md`. Full-file reads for every cited rule (Rule 1 digest exception does not apply).
4. **Evaluator cross-scope scan (EG-3 gate).** Scan for findings or proposed fixes that reference material outside the section's `heading_path`. If any are detected, fire **EG-3 (cross-scope reference mismatch)** per `PHASE_PROTOCOL.md §7` — the section's review escalates to Ph3. Planner records the trigger and the dependent section in `notes`; advancement to Ph3 is permitted only after Ph3 resolves the cross-scope dependency.
4a. **Evaluator SAFEGUARD subset at Ph2 (Step 8.5, scoped to checks 1, 4, 5, 8).** Run `SAFEGUARD_LAYER.md` Check 1 (Regression Guard), Check 4 (Contradiction Audit), Check 5 (Judgment-Call Transparency), and — **new at v0.7.2** — Check 8 (Reader-Experience / Prose Architecture). Check 8 at Ph2 reads the six Sub-checks A–F (paragraph cadence, sentence-length distribution, first-use definition, section-transition signposting, jargon discipline, worked examples at density spikes) and emits an aggregate verdict (CLEAN / BORDERLINE / MAJOR / BLOCKER) against the section. Save the subset results as `reviews/ph2_safeguard_<YYYY-MM-DD>_<cycle_id>.md` and append them as §6a of the findings report. Ph2 Check 8 findings are advisory on Ph2 admission but carry forward to Ph3 where they bind the TerminalSignoffRow accessibility gate (`PHASE_PROTOCOL.md §3.3.3`) — a BLOCKER surfaced here should be resolved during the Ph2 → Ph3 Generator pass rather than deferred.
5. **Evaluator findings report.** Write `reviews/ph2_findings_<YYYY-MM-DD>_<cycle_id>.md` with BLOCKER/MAJOR/MINOR severities, each finding carrying an `Independent reasoning:` note (Reflector §8a compliance) and rule citations.
6. **Generator dispatch (if BLOCKERs or MAJORs exist).** Planner dispatches the Generator with the consolidated findings as the fix plan. Generator edits under `agents/generator.md` Phase 2 against the P-stage register. No Self-Ph1 Verdict is emitted (retired).
7. **Evaluator re-check.** After the Generator cycle, the Evaluator re-runs the affected steps on the fixed paragraphs and emits a short re-check confirming resolution or documenting remaining issues.
8. **Reflector-lightweight probe (optional).** Integrity subset only; no skill proposals; no memory writes. Planner-gated.
9. **Ph2 exit artefact authoring.** Planner writes `reviews/ph2_review_completion.md` naming (i) the findings report path, (ii) the Generator revision log reference, (iii) the re-check report, (iv) the cross-scope dependency resolution status (if EG-3 fired), (v) any Reflector-lightweight probe. User reviews and signs.
10. **`pre_phase_advance_check.py` (Planner phase 5.5).** Seven-clause guardrail (`phase_state_schema.md §6.2`; clause (e) retired at v0.11.0). Clause (c) (ESCALATED-owner linearity) activates here if the Evaluator opened any ESCALATED findings during the round. Clause (h) (Check 8 accessibility gate) does **not** fire at Ph2 — it binds only on `TerminalSignoffRow` writes at Ph3.
11. **User approval checkpoint.** Planner presents the ph2_review_completion artefact, the diff, and the findings + re-check to the user. User Approves or Rejects.

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
- **No external-verifier probing AT THE JUDGMENT LAYER (Zotero / Scholar Gateway / register-specific passes during Steps 1–7).** Ph3 (optional) and Ph4 (required) own the judgment-layer external-verifier passes. **Qualified at v0.10.0 S4** per architecture §5.2 Edit-2 paragraph 4: SK-NEW-B (`claim-coverage-audit`, SK-34) and SK-NEW-C (`extend-snowball-incremental`, SK-35), dispatched at Step 0.5, DO invoke external verifiers — but at the **discovery layer** (audit pre-pass / on-uncovered-claim micro-iteration), not at the **judgment layer** where the Steps 1–7 prohibition applies. The two layers are distinct under the framing introduced at `references/EXTERNAL_VERIFIERS.md §1.5` (wiki-first discovery ordering, named Ph2 operationaliser per architecture §5.6). The Ph3/Ph4 judgment-layer prohibition this bullet originally ring-fenced remains intact at S4.
- **No Coupling E.2 graph-grounding overlay.** Ph3 only.

## 10. Trigger vocabulary

- "Ph2" · "phase 2" · "review & revise" · "review pass" · "second stage" · "revise this section"
- Auto-invoked by Planner when a section receives `user_approval` + `ph1_draft_completion_signed` at Ph1 and auto-advances.
- Legacy: "standard review" (disambiguated by Planner — routes to Ph2 if the section is at Ph1 and ready to advance, to Ph3 if the section is already at Ph2 or deeper).

---

*This skill is the entry point for the Ph2 stage only. To proceed past Ph2, the user must sign `ph2_review_completion.md` and approve at the checkpoint in §4 step 12, which auto-advances the section to Ph3 (SK `run-phase-3`) unless ceiling-locked.*
