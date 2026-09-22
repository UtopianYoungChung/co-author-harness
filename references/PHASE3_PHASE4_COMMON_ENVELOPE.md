# PHASE3_PHASE4_COMMON_ENVELOPE — Shared Evaluator/Planner Envelope for Ph3 and Ph4

**Status.** This file is a **roll-up**, not a new authority source. Every normative claim cites the authoritative file. When this file conflicts with a cited source, the cited source wins.

**Scope.** Semantics shared across `run-phase-3` (full), `run-phase-3-stability` (reduced), and `run-phase-4`. The Evaluator and Planner read this file once on entry to any Ph3 or Ph4 round instead of re-deriving the shared contract from three separate SKILL files. SKILL-specific gates (MCR admission, G.4 sign-off, S-0 hash-match, `check_profile` dispatch, TerminalSignoffRow/ReengagementSignoffRow) remain in their respective SKILLs and are not duplicated here.

**Grounding basis.** `PHASE_PROTOCOL.md §§3, 3.2.1, 3.3, 3.3.0, 3.3.1, 3.3.1a, 3.3.3, 3.3.4, 5, 7, 8, 9, 14`; `REVIEW_ORCHESTRATION.md §§Steps 0a–8.5`; `SAFEGUARD_LAYER.md` (all nine checks); `DETERMINISTIC_CHECKS.md`; `AGENT_CONTRACTS.md`; `agents/evaluator.md §Step 8.5`; `phase_state_schema.md §§2, 2.1, 3.1, 6.1`; `ARTEFACT_FRONTMATTER_SCHEMA.md §7a`.

---

## 1. Seven-step judgment-pass structure

The Evaluator dispatch at Ph3 (full) and Ph4 follows `REVIEW_ORCHESTRATION.md`:

| Step | Activity | Authority |
|---|---|---|
| 0a | Deterministic pre-flight (`DETERMINISTIC_CHECKS.md`) | `REVIEW_ORCHESTRATION.md` Step 0a |
| 0.2 | Coupling E.2 graph-grounding overlay | `skills/graph-grounding-overlay/SKILL.md`; optional at Ph3, **required** at Ph4 |
| 0b | External-verifier probes | `EXTERNAL_VERIFIERS.md`; optional at Ph3, **required** at Ph4 |
| 1--7 | Judgment pass on section body | `REVIEW_ORCHESTRATION.md` Steps 1--7 |
| 8 | Consolidated findings synthesis | `REVIEW_ORCHESTRATION.md` Step 8 |
| 8.5 | SAFEGUARD layer audit (all nine checks) | `SAFEGUARD_LAYER.md`; `agents/evaluator.md §Step 8.5` |

**Stability sub-mode reduction.** Under `run-phase-3-stability`, Steps 1--7, 0.2, 0b, and SAFEGUARD checks 1/4/5/7 are skipped; only the grounding audit and Check 8 deterministic counters execute (`run-phase-3-stability` §3).

---

## 2. SAFEGUARD layer invocation

All nine checks run at Ph3 (full) and Ph4 (`SAFEGUARD_LAYER.md`); Check 9 also runs at Ph1 and Ph2. At Ph3 stability, only the Check 8 deterministic pre-filter executes (`DETERMINISTIC_CHECKS.md §9b`).

**Check 8 aggregation rule.** A Check 8 BLOCKER blocks the TerminalSignoffRow write at Ph3 (`PHASE_PROTOCOL.md §3.3.3`) and blocks G.4 sign-off at Ph4. The Planner refuses the write with `E-Ph3-ACCESSIBILITY-BLOCKER-AT-SIGNOFF` (`phase_state_schema.md §6.1`). Refused writes do not consume iteration budget.

**Severity floor escalation at Ph4.** Findings that are MAJOR at Ph3 are BLOCKER at Ph4 per the Reflector Phase 2.5.1 Ph4 severity-floor column (`PHASE_PROTOCOL.md §3.4`).

---

## 3. Convergence metric and journal contract

Authority: `PHASE_PROTOCOL.md §§3.3, 3.3.1a, 3.3.4`.

- **Legacy scalar:** `float in [0, 1]` (line-diff ratio). Preserved inside a P-12 object as `legacy_scalar` after migration (`scripts/migrate_convergence_journal_v075.py` *[retired from tree]*).
- **v0.8.0 P-12 object:** four components (`grounding_clean`, `check8_aggregate_ok`, `findings_count_delta`, `line_delta`) plus optional `legacy_scalar`.
- **Journal location:** `reviews/convergence_journal.jsonl` (per-iteration mechanical-state log). The Planner is sole writer. Each row carries `cycle_id`, `convergence_metric`, `manuscript_hash`, and optional `paragraph_hash_map`.

### 3.1 [CONVERGENCE-STABLE] surface

- **Object-shaped rows (v0.8.0):** emitted after **three consecutive** iterations satisfying all §3.3.1a component tests AND no live Check 8 BLOCKER (`PHASE_PROTOCOL.md §3.3.3`).
- **Legacy scalar rows:** emitted after **two consecutive** iterations below the project's stability threshold AND no live Check 8 BLOCKER.
- Notification: `W-CONVERGENCE-STABLE` per `phase_notifications.yaml §3`. Stability is informational; the user controls termination.

---

## 4. [Ph3-STALE] computation

Authority: `PHASE_PROTOCOL.md §3.3.1` (Option A — computed, no schema field).

The Planner computes `[Ph3-STALE]` on every Phase 0 bootstrap: `wall-clock now - ph3_last_activity_at > ph3_staleness_budget_days` (default 14). No ledger rollback. Clearance requires a ReengagementSignoffRow (`phase_state_schema.md §3a.3`), which refreshes `ph3_last_activity_at`.

- **Null-handling.** `ph3_last_activity_at == null` short-circuits to `false`; emits `W-Ph3-ACTIVITY-NULL`.
- **MCR impact.** A stale section blocks Ph4 admission with `E-MCR-BLOCKED-Ph3-STALE` (`phase_state_schema.md §6.1`).
- **Stability sub-mode impact.** Staleness blocks the S-0 gate; stale sections must run a full Ph3 pass.

---

## 5. Coupling E.2 overlay dispatch

Authority: `skills/graph-grounding-overlay/SKILL.md`; `PHASE_PROTOCOL.md §5`.

- **Ph3 full:** dispatched when the F6 schedule includes it (always for `deep`; for `refine` only if scheduled).
- **Ph4:** always required. Echo-detector threshold tightens: >=15% ECHO+SHALLOW fires `[COUPLING-E.2 DEGRADED]` (vs 30% at Ph3).
- **Stability sub-mode:** skipped (the overlay is an external artefact read; stability inherits from the prior iteration).

The Evaluator treats graphify as a courier, not an authority: every severity assignment carries an `Independent reasoning:` note (Reflector §8a compliance).

---

## 6. Reflector dispatch contract

Authority: `skills/run-reflection/SKILL.md` mode router,
`agents/reflector-probe.md` / `agents/reflector-closeout.md` mode procedures,
and `PHASE_PROTOCOL.md §§1, 5`.

| Context | Reflector mode | Scope |
|---|---|---|
| Ph3 iteration (full) | Lightweight (optional) | Grounding audit, frontmatter-contract audit |
| Ph3 stability pass | Lightweight (reduced) | Grounding-audit integrity + FM-family checks only; SA-family skipped |
| Ph4 close-out | **Full** | Phase 2b aggregated history audit, Phase 2.5.1 grounding at Ph4 floors, Phase 3 lessons, Phase 4 skill proposals, Phase 5 memory updates |

The Reflector-full pipeline runs only at Ph4 close-out. Ad-hoc Reflector-lightweight invocations at Ph3 are permitted but not scheduled.

---

## 7. ESCALATED finding handling and Linear-Accountability

Authority: `PHASE_PROTOCOL.md §3.2.1`; `phase_state_schema.md §§3.1, 6.1`.

Any ESCALATED finding requires a named owner. The Planner writes an `escalation_named_owner_assigned` row (trigger 16). Ownership transfer requires an `escalation_owner_transferred` row (trigger 15) with a non-empty `transfer_rationale`; an empty rationale fails with `E-OWNERSHIP-TRANSFER-WITHOUT-RATIONALE`.

At Ph4 MCR admission, every ESCALATED finding must be resolved or carry a named owner with a documented transfer rationale.

---

## 8. Renamed surfaces (v0.6.0 to v0.7.4)

Authority: `PHASE_PROTOCOL.md §14`. Key renames: `Ph4_ready` -> `Ph3_converged`; LCR -> MCR; `laggard_clearance_approved` -> `mcr_admission`; `tier_state.json` -> `phase_state.json`; `run-tier-N` -> `run-phase-N`; `eg1_t4_downgrade_to_t3` -> `eg1_ph4_downgrade_to_ph3`; `default_final_tier` -> `default_final_phase`. Migrated rows carry `v0_7_state_rename` markers; v0.6.0 trigger names are rewritten on read.

---

## 9. Agent composition (shared structure)

Authority: `AGENT_CONTRACTS.md`; `PHASE_PROTOCOL.md §5`. The Planner orchestrates and sole-writes `phase_state.json`; the Evaluator runs the judgment-pass envelope (§1) and emits findings; the Generator is the sole manuscript writer; the Reflector runs lightweight at Ph3 and full at Ph4 close-out (§6). The Generator never evaluates its own output; the Evaluator never writes prose.

---

## 10. Approval handling (shared patterns)

Authority: `PHASE_PROTOCOL.md §§8.1, 8.5`.

- **Approve (non-terminal, Ph3 only).** `ph3_iteration_round` row (trigger 17); loop continues.
- **Approve (terminal).** Ph3: TerminalSignoffRow flips `Ph3 -> Ph3_converged`. Ph4: final `user_approval` row; `terminal_tier_reached: true`; manuscript ships.
- **Reject.** `user_rejection` row; iteration increments at Ph3; section stays at `Ph3_converged` at Ph4.
- **Defer (Ph3 only).** `user_defer` row; no iteration increment; `ph3_last_activity_at` NOT refreshed.
- **Retraction.** Ph3: drops to Ph2/Ph1 as directed. Ph4: drops to Ph3 or lower; re-climb required.
- **BLOCKER present.** Approval refused at Ph3; G.4 sign-off blocked at Ph4.

---

*Authored at v0.8.0 Phase 3.2 (alpha-C2). Shared semantics extracted from three source SKILLs: `skills/run-phase-3/SKILL.md` (v0.8.0), `skills/run-phase-3-stability/SKILL.md` (v0.8.0), `skills/run-phase-4/SKILL.md` (v0.8.0). This file is a roll-up; the cited sources are authoritative.*
