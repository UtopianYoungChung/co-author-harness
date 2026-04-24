---
name: run-phase-3-stability
description: "Ph3 stability — byte-stable inheritance pass. S-0 hash-match gate. Run grounding + Check 8 counters only; skip Evaluator envelope, SAFEGUARD 1/4/5/7, Coupling E.2, verifiers. Escalate on finding (trigger 30). Does not satisfy MCR deep-pass requirement. Trigger: \"stability,\" \"byte-stable,\" or Planner."
trigger: when the user says "run a stability pass," "Ph3 stability check," "byte-stable iteration," "S-0 gate check," or when the Planner detects a byte-stable manuscript against the prior Ph3 close and proposes a reduced-envelope iteration
version: 0.8.0
---

# run-phase-3-stability — Ph3 Stability Sub-mode (P-2)

**Grounding basis:** `references/PHASE3_PHASE4_COMMON_ENVELOPE.md` (shared Ph3/Ph4 semantics — this skill inherits convergence-metric, [Ph3-STALE], SAFEGUARD Check 8 aggregation, and renamed surfaces from the common envelope, then overrides the Evaluator envelope to the reduced stability pass); `references/PHASE_PROTOCOL.md §§3.3.0, 3.3.2 (stability sub-mode), 3.3.4, 3.3.5, 3.4`; `references/ARTEFACT_FRONTMATTER_SCHEMA.md §7a`; `references/AGENT_CONTRACTS.md §2 (I-Planner-10)`; `references/DETERMINISTIC_CHECKS.md §9b`; `references/GROUNDING_PROTOCOL.md §Rule 1`; `references/phase_state_schema.md §2.1`; `agents/evaluator.md §Step 8.5`; `skills/run-phase-3/SKILL.md §4.5`; `phase_notifications.yaml §§3, 3.3.2`.

---

## 1. What this sub-mode does

The Ph3 stability sub-mode is a **byte-stable-manuscript inheritance pass**. When the manuscript's F1/F2/F3/F5 substrate SHA-256 matches the prior iteration's recorded `manuscript_hash` in `reviews/convergence_journal.jsonl`, the Evaluator does not need to re-run the seven-step judgment pass — the prior iteration's findings already apply, and the round's only legitimate audit work is to verify that the grounding substrate and the deterministic Check 8 counters have not silently drifted. Under those two audit clauses, the round admits inheritance of the prior iteration's full findings set, writes a compact iteration row, and closes.

The sub-mode exists because **a Ph3 round on a byte-stable manuscript is the paradigmatic cost-waste case**: the seven-step pass produces no new signal because the signal substrate has not changed. The mode narrows the envelope to the two things that can still diverge on a byte-stable pass — grounding-basis drift (a source read has shifted or been retracted) and deterministic-counter drift (a Check 8 pre-filter upgrade mid-round changes the counter for the same byte-identical prose).

**`check_profile` on the F6.** Stability rounds still carry F6 `check_profile` for ledger continuity, but **`stability_sub_mode_anticipated: true` overrides the §4.5 router** for this iteration: the Evaluator runs **only** §3.1–3.2 of this skill (grounding audit + Check 8 counters), not `refine` / `structural` / `deep` full envelopes. After trigger 30 escalation, the chained `run-phase-3` pass uses the **new** F6’s `check_profile` (typically `deep` when the Planner must clear `pre_mcr_deep_pass_completed` or re-establish full SAFEGUARD coverage).

The sub-mode is **not a replacement for full Ph3**. It is a fast-path that defers to the full pass on any surfaced finding, and it is structurally ineligible as the precondition to Ph4 — the MCR admission gate at §9.4 refuses a section whose most recent Ph3 pass was a stability pass. At least one full `run-phase-3` pass must appear in the section's Ph3 history between Ph2 exit and Ph4 entry. It also **does not** satisfy `pre_mcr_deep_pass_completed` (`phase_state_schema.md` §2.1) — only a closed **`check_profile: deep`** iteration does.

## 2. The S-0 gate (hash-match precondition)

Stability mode is admissible only when **all** of the following hold at Phase 0.5 (session-state cache warm):

1. The prior iteration's journal row exists at `reviews/convergence_journal.jsonl` with a populated `manuscript_hash` field (not null, not absent).
2. The current iteration's `manuscript_hash` — computed as `SHA-256(canonical_yaml(F1_substrate) || canonical_yaml(F2_substrate) || canonical_yaml(F3_substrate) || canonical_yaml(F5_substrate))` per `PHASE_PROTOCOL.md §3.3.4` — matches the prior iteration's recorded value byte-for-byte.
3. The section is currently at `current_phase: Ph3` (stability mode does not apply at Ph1, Ph2, or Ph4; a Ph4-demoted section that returned to Ph3 via EG-1 may run stability mode once the re-admission row is written).
4. No `[Ph3-STALE]` flag is computed true for this section (staleness blocks the stability fast-path — stale sections must run a full-Ph3 pass on re-engagement to reconfirm the review substrate).

If any clause fails, the Planner does not open a stability-mode row at all — it drops through to full `run-phase-3` on the section, and the user sees the normal full-envelope round. Clause-failure cases:

- `hash_missing_prior_iteration` — the prior iteration did not record `manuscript_hash` (e.g., pre-v0.7.4 row, migration-backfill incomplete). Drop through to full Ph3; populate `manuscript_hash` on the full-Ph3 iteration row.
- `hash_mismatch` — the manuscript has changed. Drop through to full Ph3.
- `section_not_in_ph3` — the section is at Ph1 / Ph2 / Ph4 / Ph3_converged. Drop through; stability mode is a Ph3-only construct.
- `section_stale` — `[Ph3-STALE]` is computed true. Drop through to full Ph3.

Partial inheritance (some F-families hash-match, others diverge) is NOT admitted — the gate is all-families-match or drop-through. This is stricter than strictly necessary (partial inheritance would be efficiency-positive) but it is defensible on audit-integrity grounds: a round that inherits some families and re-runs others has ambiguous provenance.

## 3. The reduced Evaluator envelope

Under stability mode the Evaluator runs **only** these two check classes:

### 3.1 Grounding audit (Rule 1 full-file read)

The Evaluator runs the `skills/grounding-audit/SKILL.md` probe over the section's `grounding_basis` — the list of source paths inherited from the prior iteration's F5 artefact. Full-file reads are mandatory (Rule 1 applies; the tier-gated digest exception is retired at v0.7.4). The probe verifies:

- Every cited source path in the section's citations is still readable at its declared location.
- No source has been retracted or moved (a moved source with a declared new path is a grounding-basis update event, not a stability-pass inheritance).
- Every in-prose author-year citation still resolves to an entry in `references/REFERENCES.md`.
- No new citations have been introduced (a new citation on byte-identical prose is impossible by definition; if the grounding audit surfaces one, the S-0 hash-match was spoofed and the round escalates).

Any `R-Refl-GR-*` finding class surfaced by the grounding audit triggers escalation — the stability pass closes with trigger 30 and the section enters a full-Ph3 round.

### 3.2 Check 8 deterministic pre-filter counters

The Evaluator runs **only** the `DETERMINISTIC_CHECKS §9b` Check 8 pre-filter: the three deterministic counters `cadence_flag_count`, `signpost_flag_count`, and `jargon_density_flag_count`. The judgment-layer `accessibility-overlay` skill is NOT dispatched; the six Sub-check A–F severity findings are inherited by hash-reference from the prior iteration's F1 artefact.

The current-iteration counters are compared against the prior-iteration counters for the same section (retrieved from the prior F2 artefact). A divergence on byte-identical manuscript indicates one of three conditions, all of which escalate:

- The Check 8 pre-filter code was upgraded mid-round (a new counter threshold, a new regex pattern) and the same prose now scores differently. Legitimate, but requires a full-Ph3 re-pass because the judgment-layer overlay may also have moved.
- The prior-iteration counters were miscomputed and the current iteration is the correct value. Recoverable only under a full-Ph3 pass.
- The F2 substrate hash-match was spoofed (the manuscript bytes match but the F2 artefact was regenerated with different counters). This is a frontmatter-schema integrity failure; the stability pass escalates AND the Reflector files an `R-Refl-FM-*` finding on the F2 drift.

Any counter divergence triggers escalation via trigger 30.

### 3.2a Sub-check G advisory-only treatment (D-G-3, v0.8.1)

Under the stability sub-mode, SAFEGUARD Check 8 **Sub-check G** (Cumulative Cognitive Load / Consolidation Anchors) runs **advisory-only**, regardless of the `advisory_until: next_manuscript_at_ph3` transitional flag state declared in `READER_ACCESSIBILITY.md §13.5`. This is the authoritative statement of the D-G-3 decision (2026-04-23); the rule shipped in the v0.8.0+ stability sub-mode and is anchored here in the v0.8.1 unpacked tree so that `SAFEGUARD_LAYER.md` Check 8 Sub-check G's "Stability sub-mode interaction" paragraph can defer to this subsection rather than carry the full text.

The rationale is that Sub-check G is judgment-heavy and has no deterministic pre-filter analogue at v0.8.1 (the §9d manuscript-scale pre-filter at `DETERMINISTIC_CHECKS.md §9d` locates candidate boundaries but does not produce a hash-comparable severity counter). Inheritance by hash-reference is therefore not defined for Sub-check G the way it is for Sub-checks A–F (which inherit from the prior iteration's F1 artefact under §3.3's skip-list rule). Rather than escalate every stability round to a full-Ph3 pass on Sub-check G's behalf — which would defeat the sub-mode's economic purpose — or silently suppress Sub-check G entirely, the advisory-only path preserves G's recurrence trail while maintaining byte-identical-pass economics.

**Operational rules under stability mode:**

1. The Evaluator does **not** dispatch the `accessibility-overlay` skill in its A–G judgment configuration. Sub-checks A–F are hash-inherited from the prior iteration's F1 artefact per §3.3 skip-list rule. Sub-check G is evaluated via a narrow pass that reads the prior iteration's Sub-check G finding list (from the prior F1's `safeguard_check8_<date>.md` block) and re-emits each finding **with the `stability_advisory: true` annotation and the `advisory_until_flag_state` snapshot inherited**. No fresh construct-accumulation analysis is performed on the byte-identical manuscript.
2. Any Sub-check G finding emitted under stability mode carries `stability_advisory: true` in the Check 8 output and does **not** contribute to the aggregate verdict the Planner reads for the §3.3.3 accessibility-gate decision. A Sub-check G BLOCKER under stability mode therefore does **not** force `E-Ph3-ACCESSIBILITY-BLOCKER-AT-SIGNOFF`; the Planner reads the A–F aggregate only.
3. The finding is handed to the Planner for routing to the Reflector's Phase 2g recurrence-accounting pass at round close. A manuscript that accumulates Sub-check G advisory findings across multiple stability rounds surfaces as a Phase 2g recurrence candidate at Reflector close-out, even though no individual stability round fires the gate.
4. The advisory path does **not** short-circuit the full-Ph3 escalation under other triggers. If the grounding audit (§3.1) or the Check 8 A–F deterministic counters (§3.2) surface a finding, the stability round escalates via trigger 30 regardless of Sub-check G's advisory state; once inside the chained full-Ph3 pass, Sub-check G runs at its native severity per the `advisory_until` flag and the §3.3.3 gate.

**Interaction with the `advisory_until: next_manuscript_at_ph3` flag.** The two advisory paths — the transitional flag and the stability-mode rule — are independent and additive. A Sub-check G finding on a section whose `advisory_until` flag is active AND whose current round is a stability pass is advisory on **both** grounds; the Check 8 output carries both annotations. When the `advisory_until` flag retires (the first Ph3 entry of a manuscript whose Ph1 classification postdates 2026-04-23), the stability-mode advisory rule persists — it is not a transition-only construct but the permanent D-G-3 rule for the sub-mode's economics.

**Interaction with escalation (trigger 30).** A Sub-check G finding alone does **not** trigger escalation under stability mode (that is the whole point of the advisory path). Only a §3.1 grounding finding or a §3.2 Check 8 A–F counter divergence escalates. Once escalation has opened the chained `run-phase-3` round, Sub-check G runs at native severity and the §3.3.3 gate reads the A–G aggregate (subject to the `advisory_until` flag) on the chained round's TerminalSignoffRow attempt. The escalated round is where a Sub-check G BLOCKER can actually block closure; the stability round itself cannot.

### 3.3 What the stability envelope does NOT run

Explicit skip list — these are all run on a full `run-phase-3` pass but are skipped under stability mode:

- **REVIEW_ORCHESTRATION Steps 1–7** (the seven-step judgment pass). Findings from the prior iteration's F1 artefact are inherited by hash-reference.
- **SAFEGUARD layer checks 1, 4, 5, 7** (the non-Check-8 SAFEGUARD subset at Ph3). Inheritance is admitted because checks 1/4/5/7 are byte-driven and the manuscript is byte-stable.
- **Coupling E.2 graph-grounding overlay (Step 0.2).** The graphify layer's output is an external artefact read; stability mode does not re-query it.
- **External-verifier probes (Step 0b).** Zotero MCP citation probe, Scholar Gateway render-contract check, register-specific passes (IS-theory, Suchman, Sexton, public-interest-accountability) — all skipped under stability. These are the verifiers Ph4 requires; stability mode is a Ph3-only inheritance audit.
- **`accessibility-overlay` judgment layer (A–F).** Only the `§9b` deterministic pre-filter runs; the judgment-layer Sub-check A–F findings are inherited by hash-reference from the prior iteration's F1 artefact.
- **`accessibility-overlay` judgment layer (G).** Sub-check G is NOT run at full severity under stability mode; instead, it runs in the advisory-only configuration specified at §3.2a above. A Sub-check G finding under stability mode carries `stability_advisory: true`, does not contribute to the A–G aggregate verdict, and does not fire the §3.3.3 accessibility gate. The finding is routed to Reflector Phase 2g for recurrence accounting.

## 4. Dispatch sequence

1. **Planner Phase 0 (preflight).** Read `reviews/phase_state.json`. Confirm `current_phase: "Ph3"` and `applicable_ceiling >= "Ph3"`. Compute `[Ph3-STALE]` for this section. If stale, drop through to full `run-phase-3` (clause 4 of the S-0 gate).
2. **Planner Phase 0.5 (session-state cache + manuscript hash).** Warm the session-state cache per invariant I-Planner-7. Compute the current `manuscript_hash` over the F1/F2/F3/F5 substrate. Read the prior iteration's journal row from `reviews/convergence_journal.jsonl` and extract its `manuscript_hash`.
3. **Planner S-0 gate.** Compare current hash against prior. If all four S-0 clauses hold, proceed; otherwise drop through to full `run-phase-3` and log the drop-through reason in the Planner's Phase 0.6 artefact (the F6 will declare `stability_sub_mode_anticipated: false` with a notes-line naming the clause that failed).
4. **Planner Phase 0.6 (round dispatch plan — F6).** Author the F6 dispatch-plan artefact at `reviews/dispatch_plan_<cycle_id>.md` per invariant I-Planner-10. The F6 declares `stability_sub_mode_anticipated: true`, a reduced `checks_scheduled[]` list (`grounding_audit` and `deterministic_step_0a_subset_check8` only — no SAFEGUARD 1/4/5/7, no Coupling E.2, no external verifiers), a single `dispatched_agents[]` entry for the Evaluator at Ph3 on the project's declared model, and the user-approval signature block pending. Present the F6 to the user as a blocking checkpoint.
5. **User approval of F6.** On approval, populate `user_approval_signature` and proceed. On modification (the user wants a full pass even though stability is admissible), re-emit the F6 with `stability_sub_mode_anticipated: false` and hand off to `run-phase-3`. On rejection, the round does not open.
6. **Evaluator stability pass — the reduced envelope.** The Evaluator runs the grounding audit (3.1) and the Check 8 deterministic pre-filter (3.2). No seven-step pass, no SAFEGUARD 1/4/5/7, no Step 0.2, no Step 0b. Total wall-clock is a fraction of a full Ph3 round (typical: 3–8 minutes versus 15–45 for full Ph3).
7. **Outcome routing.**
   - **Clean.** Grounding audit yields no `R-Refl-GR-*` findings; Check 8 counters match the prior iteration byte-for-byte. The Planner writes a `ph3_iteration_round` row (trigger 17) with `stability_mode: true` in `notes`, refreshes `ph3_last_activity_at`, and cites the prior iteration's F1 artefact by `manuscript_hash` in the new F5 rather than re-computing findings. Return control to the user with `[STABILITY-ADMITTED]` notice.
   - **Finding.** Grounding audit yields a finding OR Check 8 counters diverge. The Planner writes a `stability_mode_escalated_to_full_ph3` row (trigger 30) with `notes` naming the triggering finding class (e.g., `escalation_reason: grounding_R-Refl-GR-3` or `escalation_reason: check8_counter_drift_signpost_flag_count`). The escalated row consumes no iteration budget on its own. Immediately hand off to `run-phase-3` on the same section; the full-Ph3 round opens with trigger 17 (or trigger 29 under batching if the user's revision directive spans multiple sections).
8. **Reflector-lightweight probe (reduced scope).** On close, the Reflector-lightweight runs only the grounding-audit integrity check (Phase 2 step 3) and the frontmatter-contract audit (Phase 2f FM-family checks). The SA-family audit (Phase 2f step 6.5) is skipped — no subagent envelope is authored under stability mode because the Evaluator runs the reduced envelope directly. The Ceil-family audit (step 6.8) and DP-family audit (step 6.9) continue to run per their normal contract.

## 5. Iteration-budget treatment

Stability mode has a distinctive budget treatment:

- **A clean stability pass counts as one iteration** against `iteration_count_at_current_phase` and consumes one unit of MCR reserve (per `PHASE_PROTOCOL.md §9.7` +50% reserve) if the round is inside an MCR climb. The cost on the user's bill is small because the envelope is narrow, but the accounting is one iteration.
- **An escalated stability pass consumes no iteration budget on its own.** The `stability_mode_escalated_to_full_ph3` row (trigger 30) does not increment `iteration_count_at_current_phase`; the subsequent full-Ph3 round that the escalation opened consumes the iteration. Rationale: the escalated pass produced no findings that advanced the review — it produced a signal that a full pass was required, which the full pass then provided. Charging twice for one logical review unit would double-count cost.
- **A drop-through (S-0 gate fail without a stability-mode row ever being written) has the same budget treatment as a normal full-Ph3 open.** The full `run-phase-3` round opens and is charged one iteration. The drop-through itself costs only the F6 authoring at Phase 0.6, which the user saw and approved.
- **Refused stability-pass writes at the `TerminalSignoffRow` do not apply.** A stability pass cannot write a terminal signoff — the terminal signoff requires an accessibility-gate check at §3.3.3 that a stability pass does not run (only the deterministic pre-filter runs, not the judgment layer). To close a section at Ph3 the user must run at least one full-Ph3 pass after the last stability pass; the full pass is the one that writes the terminal row.

## 6. Composition with other v0.7.4 invariants

- **P-1 (F6 dispatch plan).** Every stability-mode round authors a fresh F6 under Phase 0.6 with `stability_sub_mode_anticipated: true` and the reduced `checks_scheduled[]` list. F6 is never inherited under P-2 per `ARTEFACT_FRONTMATTER_SCHEMA.md §7a.4`; each round gets its own consent artefact.
- **P-3 (frontmatter schema).** The F1 / F2 / F3 / F5 inheritance substrate is hash-addressed by the `manuscript_hash` field on the prior iteration's journal row. The strict-family contract at `ARTEFACT_FRONTMATTER_SCHEMA.md §8 rule 3` applies normally — a stability pass that produces a new F2 artefact with drifted counters is flagged by the frontmatter validator before the Planner compares.
- **P-4 (convergence-log split).** Stability mode reads `manuscript_hash` from `reviews/convergence_journal.jsonl` (the per-iteration mechanical-state log), NOT from `reviews/convergence_log.md` (the Trajectory-synthesis prose). The journal is the single source of truth for hash comparison.
- **P-5 (subagent invariants).** Stability mode does not dispatch subagents under its default envelope. If a project directive lifts stability mode to dispatch a grounding-audit subagent (non-default), the I-SubAgent-1/2/3 invariants apply unconditionally and the F6's `subagent_envelope[]` must declare the delegation.
- **P-6 (session-state cache).** The Planner's cache of `reviews/phase_state.json`, `reviews/classification.md`, and `research_notes/directives.md` is required for S-0 gate efficiency — repeated reads on the prior iteration's journal row hit the cache.
- **P-7 (manuscript-level batching).** Stability mode is section-scoped only and never triggers `ph3_iteration_round_manuscript`. See `PHASE_PROTOCOL.md §3.3.5` interaction note. An escalated stability pass whose revision directive ends up touching multiple sections opens a full-Ph3 batch round under trigger 29 as normal.
- **P-8 (ceiling-lock termination ranking).** Stability mode is excluded from P-8 tension detection per `PHASE_PROTOCOL.md §3.3.6` — a section whose most recent iteration was a stability pass does not qualify as a tension-state section for the ceiling-lock proposal. The tension-detection window is computed from full-Ph3 iterations only.

## 7. When NOT to use this skill

Do not invoke `run-phase-3-stability` when:

- The manuscript has changed since the prior Ph3 close (the S-0 gate will drop through anyway; but users sometimes invoke the stability skill intending to get a full pass — that's a full-`run-phase-3` call).
- The section is at Ph2 and the user is preparing for Ph3 entry (stability mode is Ph3-only; a fresh Ph3 entry from Ph2 always runs the full envelope).
- The section is the precondition to an imminent Ph4 admission (MCR admission at §9.4 refuses sections whose most recent Ph3 pass was a stability pass; run at least one full `run-phase-3` before invoking `/run-phase-4`).
- The user has explicitly requested a full review (honor the request even if stability mode is technically admissible; the user's explicit instruction outranks the package per precedence level 1).
- The section carries a live Check 8 BLOCKER from the prior iteration (the Planner refused the prior `TerminalSignoffRow` with `E-Ph3-ACCESSIBILITY-BLOCKER-AT-SIGNOFF`; the next round must be a full Ph3 that addresses the BLOCKER — inheritance is not admissible on a live BLOCKER state).
- The prior iteration was itself a stability pass that surfaced nothing AND the user is seeking to escalate for external-verifier probing (at that point the user wants the full Ph3 envelope explicitly; a second stability pass would just re-confirm inheritance without adding the signal the user wants).

## 8. Exit artefacts

- **On clean admission:** a new row in `reviews/ph3_convergence_signoff.md` (non-terminal, per-iteration), a new journal line in `reviews/convergence_journal.jsonl` with `cycle_id` unique to this stability pass, and a new F5 consolidated-findings artefact at `reviews/consolidated_findings_<date>_stability.md` that cites the prior iteration's F1 by `manuscript_hash` rather than re-authoring findings.
- **On escalation:** a `stability_mode_escalated_to_full_ph3` row (trigger 30) in `reviews/phase_state.json log[]`, a short `reviews/stability_escalation_<date>.md` artefact (F3 family, `reflector_lightweight_probe` document_type with the specific escalation-reason), and then the downstream full-Ph3 artefacts produced by the chained `run-phase-3` dispatch.
- **On S-0 drop-through (never entered stability mode):** no stability-specific artefact. The F6 authored at Phase 0.6 records the drop-through reason in `notes` for the Reflector's Phase 2f DP-family audit.

---

*Normative status.* This skill implements the Ph3 stability sub-mode specified at `PHASE_PROTOCOL.md §3.3.2`. It is a thin peer of `run-phase-3`: the stability envelope is the only divergence; all other Ph3 semantics (convergence metric / P-12 journal shape, `[Ph3-STALE]`, `[CONVERGENCE-STABLE]`, ESCALATED ownership) are inherited from `run-phase-3` except where this file explicitly overrides (`stability_sub_mode_anticipated` envelope; no `pre_mcr_deep_pass_completed` flip). When this skill's specification conflicts with `PHASE_PROTOCOL.md §3.3.2`, the protocol file wins.

*Created 2026-04-21 (v0.7.4, P-2). v0.8.0 P2.3: aligned with `check_profile` dispatch + pre-MCR deep-pass cross-refs. Composes with P-1 / P-3 / P-4 / P-5 / P-6 / P-7 / P-8 per §6 above.*
