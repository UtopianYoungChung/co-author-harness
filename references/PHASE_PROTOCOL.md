# PHASE_PROTOCOL — v0.8.0 Lifecycle-Phase Ladder (canonical)

*Normative source of phase semantics for the v0.8.0 composed-release Research and Academic Paper Writing Package. Historical authoring context for the v0.8.0 “wip0” phase is recorded in `proposals/v0.8.0_upgrade_architecture.md` (D-8); the optional local `unpacked/` mirror is not retained in this tree. This file is the single authority every agent, skill, and script routes to when resolving phase-dependent behaviour. All references to phase semantics elsewhere in the package (`AGENT_ORCHESTRATION.md` §§3 / 8.2a / 8.2b / 10, `REVIEW_ORCHESTRATION.md`, `GROUNDING_PROTOCOL.md` Rule 1 full-file floor, `SKILL_REGISTRY.md`, the four `run-phase-N` skills, `ROUTING_SPINE.md`) defer to this document. Renamed from `TIER_PROTOCOL.md` at v0.7.4 under the cross-cutting Tier → Phase terminology rename; the legacy path shipped as a forwarding copy through the v0.7.4 minor. v0.8.0 adds the β Ph3 refinement-loop surfaces in §§3.3.0, 3.3.1a, 3.3.4 (paragraph-hash extension), and §3.4 (pre-MCR deep-pass gate) on top of the v0.7.4 economic-efficiency bundle (P-1–P-8), which remains binding.*

*Grounding basis.* Every normative claim in this file derives from `TIER_REDESIGN_v0.7-draft-5.md`, the v0.7.4 economic-efficiency proposal bundle (P-1 through P-8), and the v0.8.0 composed-release authoring order (`proposals/v0.8.0_upgrade_architecture.md` §3.2 Phase 2.2, `proposals/v0.7.5_phase3_refinement_loop_proposal.md` §§P-9–P-12); section references below cite the source §. The legacy `research-writing-harness-claude-v0.6.0/references/TIER_PROTOCOL.md` and the v0.7.0–v0.7.3 `TIER_PROTOCOL.md` at each minor are preserved for rollback and are **not authoritative** for v0.7.4+ rounds.

*Supersession clause (v0.7.0 lifecycle reframe).* v0.7.0 reframes the four-rung ladder from a *depth-of-review* progression (Ph1–Ph4 as escalating rigor applied to homogeneous review activity) into a *lifecycle-stage* progression (Ph1–Ph4 as distinct phases of the manuscript's life, each with a named goal, a mandatory exit artefact, and a reassigned agent configuration). The behavioural and schema consequences of that reframing are enumerated below. Three constructs are retired outright (Confirmation Mode, the Generator Self-Ph1 Verdict, EG-2); one artefact is renamed (Laggard Clearance Report → Manuscript Convergence Report); one enum value is renamed (`Ph4_ready → Ph3_converged`); the sixteen-field `SectionStateObject` invariant (v0.8.0; fifteen fields at v0.7.0–v0.7.4) replaces v0.6.0's ten-field commitment.

*Supersession clause (v0.7.4 Tier → Phase rename + economic-efficiency bundle).* v0.7.4 retires the "tier" vocabulary layer and renames every surface that previously named *review depth* under the tier taxonomy to name *lifecycle phase* instead. The ladder is renamed Lifecycle-**Phase** Ladder; the ledger is renamed `reviews/phase_state.json`; the top-level fields are renamed (`current_tier` → `current_phase`, `tier_goal_declared` → `phase_goal_declared`, `tier_deliverable_path` → `phase_deliverable_path`, `tier_entry_log` → `phase_entry_log`, `t1_pstage_declaration` → `ph1_pstage_declaration`, `t3_last_activity_at` → `ph3_last_activity_at`, `default_final_tier` → `default_final_phase`); the log-row shape is widened **6 → 7 fields** (absent-means-null `model_used`); the trigger enum is extended **28 → 30** (trigger 29 `ph3_iteration_round_manuscript` per P-7, trigger 30 `stability_mode_escalated_to_full_ph3` per P-2); the `eg1_t4_downgrade_to_t3` trigger is renamed `eg1_ph4_downgrade_to_ph3`. One mechanism is retired outright: the Rule 1 phase-gated digest exception (§10 below) — full-file reads are now the universal grounding floor at every phase. One invariant is added: **I-SubAgent-1** — subagent-returned verdicts are authoritative-as-read; the dispatching agent may not re-adjudicate. The eight economic-efficiency proposals (P-1 through P-8) introduce a round-scoped dispatch plan (P-1), a Ph3 stability sub-mode (P-2), artefact YAML frontmatter (P-3), a convergence-log contract split (P-4), subagent-delegation contracts (P-5), session-state caching (P-6), manuscript-level Ph3 iteration batching (P-7), and ceiling-lock termination ranking (P-8). The T4R sibling ladder for response letters is preserved (not renamed) because it does not participate in the main Ph1–Ph4 advancement.

*Supersession clause (v0.8.0 β Ph3 refinement-loop on the v0.7.4.1 substrate).* v0.8.0 lands the Ph3 package described in `proposals/v0.7.5_phase3_refinement_loop_proposal.md` (P-9 through P-16 where not deferred) and summarised in `proposals/v0.8.0_upgrade_architecture.md` §3.2 Phase 2.2. Contract highlights wired in this revision: **§3.3.0** — `check_profile` enum (`refine` \| `structural` \| `deep`) on the F6 dispatch plan plus the `halo_scope` vocabulary for diff-scoped reads (P-10); **§3.3.1a** — four-component convergence signature with a **three-round** stability window (P-12); **§3.3.4** — paragraph-level hash map alongside whole-manuscript `manuscript_hash`; **§3.4** — MCR refusal `E-MCR-PRE-DEEP-PASS-REQUIRED` until `pre_mcr_deep_pass_completed: true` on every in-scope section (`phase_state_schema.md` §2.1, β-P-9a). The v0.7.4 P-1–P-8 surfaces are not retired by this clause.

---

## 1. The ladder (overview)

v0.7.0 replaces the v0.6.0 Progressive Approval Staircase (four rungs of progressively deeper review on homogeneous prose) with a **four-stage lifecycle ladder** plus a T4R sibling ladder. Each stage is a distinct phase of the manuscript's life; each stage has a named phase goal, a mandatory exit artefact, and a reassigned agent configuration.

- **Ph1 Plan & Draft** — Planner + Generator only. Produce a complete first draft articulating a coherent research intentionality. Exit artefact: user-signed `reviews/ph1_draft_completion.md`. Absorbs milestones M1, M2, M3. Evaluator dormant. Reflector lightweight (grounding audit only). Rule 1 digest exception applies, narrowly (§10).
- **Ph2 Review & Revise** — Planner + Evaluator + Generator + Reflector-lightweight. Produce an externally-reviewable draft that has survived one full-file Evaluator pass. Exit artefact: user-approved `reviews/ph2_review_completion.md`. Absorbs milestone M4a. Confirmation Mode retired; Ph2 entry is gated by the signed Ph1 exit artefact.
- **Ph3 Iterate & Converge** — Full four-agent loop (Reflector-lightweight). Converge on a draft the human researcher actively declares satisfactory. User-gated unbounded iteration loop with a cumulative signoff file. Exit artefact: terminal row appended to `reviews/ph3_convergence_signoff.md` bearing `is_terminal: true`, which flips `current_phase: Ph3 → Ph3_converged`. Absorbs milestone M4b.
- **Ph4 Finalize & Close** — Full four-agent loop (Reflector-full). Ship a submission-bound artefact and close the institutional-learning loop. MCR-gated admission (§9). Exit artefact: `reviews/ph4_ship_signoff.md` + G.4 sign-off. Absorbs milestone M5.
- **T4R Response-Letter Sibling** — renamed from T3R at v0.7.0 to reflect its terminal-artefact nature. Entered independently via `/review-letter`; does **not** interact with the main ladder or consume `phase_state.json`.

**Advisor MCP (optional external feedback — plugin-bridged).** For projects that want **submission-defensibility–oriented** external consultation, the package recommends two **scheduled** `advisor-escalation` moments (see `references/ADVISOR_MCP.md`): **EP-1** after Ph2 review completion, before deep Ph3 iteration; **EP-2** after all in-scope sections reach `Ph3_converged`, before MCR clearance and Ph4. The co-author-harness **plugin** exposes `/advisor-escalation`; the **host** must connect the **advisor** MCP server so the `consult_advisor` tool is available. Filed `reviews/advisor_consultation_*.md` artefacts are auditable; they do **not** replace user approval on the ladder, `EXTERNAL_VERIFIERS` citation checks, or MCR/Ph4 gates.

Each Ph2 / Ph3 / Ph4 stage runs the `review → plan → generate → human approval` cycle appropriate to its lifecycle role. Ph1 runs a truncated `plan → draft → lightweight-grounding` cycle (no Evaluator). User approval at a phase advances the section per §8.1. The monotonicity invariant survives from v0.6.0: **a section's `last_approved_phase` is non-decreasing within a session except for explicit user-initiated phase-down** (§8.5) or a fingerprint demotion (§8.6).

**Retired at v0.7.0.** Depth-of-review tier vocabulary, Confirmation Mode at Ph2 entry, the Generator Self-Ph1 Verdict (CLEAN / SUSPECT / DIRTY), escalation gate EG-2 (Self-Ph1 verdict mismatch), the "Laggard Clearance Report" name, the `Ph4_ready` enum value, and `AGENT_ORCHESTRATION.md §10.1`'s artefact-anchored milestone definitions (superseded by §4 here). See §11 for the full retirement ledger.

**Preserved from v0.6.0.** The four-agent architecture (Planner / Evaluator / Generator / Reflector), the EYgp P-stage vocabulary (P0 / P1 / P2), the fingerprint policy (strict / tolerant / off), the monotonicity invariant on `last_approved_phase`, the `/run-phase-N` override surface (EG-6), the `/cancel-climb` and `/raise-ceiling` entry points, the external-verifier class contract (Class 1 / 1.5 / 2 / 3), the SAFEGUARD Layer's six v0.5.x checks (extended to eight at v0.7.2 with Check 7 Inter-Sentential Logical Connective Audit and Check 8 Reader-Experience / Prose Architecture Audit; see `SAFEGUARD_LAYER.md` and `docs/release-notes/RELEASE_NOTES_v0.7.2.md`), and the v0.6.0 `phase_entry_log` audit discipline (extended with the §6.3 trigger-enum additions and the §6.3a row-shape contracts).

**Reflector re-expansion — explicit reversal of v0.6.0 §9.2.** v0.6.0 scoped the scheduled Reflector to Ph4-only, calling this a "real capability reduction at intermediate phases" and deferring re-expansion to v0.6.1. v0.7.0 reverses this deferral and reinstates the Reflector in *lightweight* mode at Ph1, Ph2, and Ph3, reserving *full* mode for Ph4. The grounding-integrity, divergence, drift, and reflexivity checks that a lightweight Reflector performs are now stage-specific safety surfaces that cannot be deferred to Ph4 without compromising the lifecycle handoffs. Cost consequence: Reflector-lightweight invocation adds 60–120 seconds per round per section on the grounding-audit path; `TOKEN_BUDGET_PROTOCOL.md` absorbs this overhead.

**Output economy clause (v0.14.0).** The Lifecycle-Phase Ladder certifies paper movement, not report volume. Ph1–Ph3 default to compact evidence packets plus decision checkpoints. Human-facing per-phase reports are required only when a phase gate blocks, a verifier fails, an unsafe edit condition appears, or the user explicitly requests the report. Ph4 or explicit round close assembles the final human-facing report from evidence packets, revision logs, and `reviews/phase_state.json`. Normative contract: `references/OUTPUT_ECONOMY_PROTOCOL.md`.

---

## 2. Theoretical framing

*Source: draft-5 §2.* This section names the four-phase ladder, its rationale, and its relation to P-stages.

### 2.1 Phase ladder rationale

The top-level hard goal is **"produce a submission-ready research paper grounded in reviewed literature."** Each of the four phases owns one sub-goal, and each phase declares its own dependency contract between the human researcher and the agent society — the agent set is not the same across phases, only the human depender is. **Ph1 (Plan & Draft)** produces a complete first draft with explicit problem statement, theoretical framework, methodology, analysis, and synthesis arc; every section declares its P-stage per EYgp. **Ph2 (Review & Revise)** produces an externally-reviewable draft that has survived an independent Evaluator pass; every BLOCKER and every MAJOR finding is RESOLVED, ACKNOWLEDGED with rationale, or ESCALATED with a named owner of record (softgoals: argumentative rigor, grounding integrity, register compliance). **Ph3 (Iterate & Converge)** converges on a draft the human researcher has actively declared satisfactory through user-gated unbounded review–revise rounds; staleness is monitored within Ph3 and gates re-admission at MCR (§3.3.1, §9.3) (softgoals: voice consistency, theoretical contradiction resolution, stakeholder alignment, narrative drive). **Ph4 (Finalize & Close)** ships a submission-bound artefact and closes the knowledge-production loop; external verifiers are exhausted, the Reflector runs its full meta-learning pass, and wiki ingestion plus plugin-update proposals route to the Planner as sole gatekeeper (softgoals: provenance integrity, reproducibility, institutional learning). The per-phase agent-society contract — who depends on whom for what at each phase — is enumerated in §5.

*(§2.2 reserved — heading removed in an earlier revision; number retained so §2.3+ citations stay stable.)*

### 2.3 Relation to P-stages (unchanged) and milestones (superseded)

Under v0.7.0, phases absorb milestones M1–M5 but preserve the EYgp P-stages (P0 / P1 / P2). The axes reduce from three (Ph × P × M) to two (Ph × P). The P-stage remains the vocabulary-and-claim-maturity axis per `EYgp_Research_process_and_artifacts.md` (P0 = collected phenomenon readings, P1 = phenomenon characterization, P2 = research-question definition). The milestone axis is absorbed into the phase axis by the supersession clause in §4, which explicitly supersedes `AGENT_ORCHESTRATION.md §10.1`'s artefact-anchored milestone definitions with declared reason.

---

## 3. Per-phase specification

*Source: draft-5 §3.* Per-phase specifications below are normative; the cross-phase matrix in §5 is their synthesis for agent orchestration.

### 3.1 Ph1 — Plan & Draft

| Property | Value |
|---|---|
| **Phase goal** | Produce a complete first draft articulating a coherent research intentionality. |
| **Primary deliverables** | `manuscript/main.md` at prose-completeness; `reviews/classification.md` (advisory at Ph1 entry, required at Ph1 exit). |
| **Exit artefact** | `reviews/ph1_draft_completion.md` — Planner-signed declaration that every section has prose, every in-text citation has a `wiki/sources/` stub (via the new incremental SK-16 sibling), every placeholder is explicit. |
| **Absorbs milestones** | M1, M2, M3 (all three map to Ph1 per the §4 supersession). |
| **Active agents** | Planner, Generator. |
| **Evaluator** | **Dormant** — no adversarial review at draft stage. |
| **Reflector mode** | Lightweight: grounding audit only (Rule 1 read-before-cite); non-blocking. |
| **Deterministic checks** | `DETERMINISTIC_CHECKS.md` mandatory subset only (em-dashes, absolutes, LLM tics, sentence-length outliers). |
| **Rule 1 digest exception** | Applies, but *scoped to prose drafting only*. Sections classified as M2 literature-review must run a full-file `grounding-audit` regardless — the exception does not cover literature-work prose (§10, Q-E resolution). |
| **`p-stage-checker` discipline** | High-priority at the Ph1 declaration point; blocking at Ph2 entry if declaration is absent or malformed; drift-only thereafter. |
| **Classification** | Advisory at Ph1 entry (warning if absent); required at Ph1 exit (blocks `ph1_draft_completion.md`) — Q-B resolution. |
| **User-gated exit** | User approves `ph1_draft_completion.md`; section auto-advances to Ph2, or remains at Ph1 if `applicable_ceiling == Ph1` (see §9.4 for Ph1-ceiling terminal-artefact semantics). |
| **Wall-clock target** | Variable. The phase imposes no wall-clock budget; only artefact completeness. |

**SD contract at Ph1.** The human researcher depends on the Planner for orchestration (P-stage declaration, classification, draft sequencing) and on the Generator for prose. No Evaluator contract exists at Ph1, because prose is not yet externalizable. The Reflector's lightweight contract at Ph1 is a *safety* dependency (grounding integrity), not an *evaluation* dependency.

### 3.2 Ph2 — Review & Revise

| Property | Value |
|---|---|
| **Phase goal** | Produce an externally-reviewable draft that has survived one full-file Evaluator pass. |
| **Primary deliverables** | `reviews/evaluator_findings_t2.md`; revised `manuscript/main.md`. |
| **Exit artefact** | `reviews/ph2_review_completion.md` — Generator-signed per-finding disposition record. Every finding carries `disposition: RESOLVED / ACKNOWLEDGED / ESCALATED`; every `ESCALATED` finding carries a `named_owner` field **and is bound to the Ph2→Ph3 transition contract specified in §3.2.1**. |
| **Absorbs milestone** | M4a (first reviewed-and-revised pass — plan-originated subdivision per §4). |
| **Active agents** | Planner, Evaluator, Generator, Reflector-lightweight. |
| **Reflector mode** | Lightweight: grounding-integrity safety; non-blocking. |
| **Deterministic checks** | `DETERMINISTIC_CHECKS.md` full content. |
| **Rule 1 digest exception** | Does **not** apply. Full-file reads mandatory from Ph2 upward. |
| **Skills invoked** | `sentence-level-pass` (Bacon), `narrative-structure-pass` (Sexton), `grounding-audit` (full), `check-abstract-body`, `check-contradictions`, `p-stage-checker` (drift-only). |
| **Confirmation Mode** | **Retired at v0.7.0** (see §11 item 3). Ph2 entry is gated by the user-signed `ph1_draft_completion.md`, a stronger signal than any Generator self-report. |
| **User-gated exit** | User approves disposition of every BLOCKER and every MAJOR (ESCALATED findings must have a named owner); section auto-advances to Ph3, or remains at Ph2 if `applicable_ceiling == Ph2`. |
| **Wall-clock target** | 30–90 min per section-group for a manuscript-sized draft. |

#### 3.2.1 Escalation-ownership carryforward into Ph3 (Linear-Accountability defence)

The user's mandatory safety constraint (Linear Accountability) requires that the named owner of an `ESCALATED` finding is preserved across the Ph2→Ph3 transition, with explicit provision for ownership transfer when the finding's resolution moves into a different domain. The mechanism:

- At Ph2 sign-off, every `ESCALATED` finding's `named_owner` field is copied into the matching row of `convergence_log.md` at Ph3 entry, in a new `current_owner` field.
- When the Generator proposes a fix in Ph3 that requires a different owner (e.g., "the issue is now in [Researcher B]'s domain"), the `convergence_log.md` row is extended with two fields:
  - `transferred_to: <Researcher B>` — the new owner.
  - `transfer_rationale: "<one-sentence explanation>"` — required, non-empty, ≤ 280 characters.
- The transfer is recorded as a `phase_entry_log` row with trigger `escalation_owner_transferred` (§6.3).
- `pre_phase_advance_check.py` enforces: any `convergence_log.md` row with a `transferred_to` field must also have a non-empty `transfer_rationale`. Violation fails with `E-OWNERSHIP-TRANSFER-WITHOUT-RATIONALE`.

The contract preserves linear accountability across the cyclical Ph3 loop: every `ESCALATED` finding has, at any point in time, exactly one named owner, and every transition between owners is recorded with rationale. This pattern is plan-originated.

### 3.3 Ph3 — Iterate & Converge

| Property | Value |
|---|---|
| **Phase goal** | Converge on a draft the human researcher actively declares satisfactory. |
| **Primary deliverable (contract-split at v0.7.4, P-4; amended v0.8.0 P-10 / P-12)** | A **two-file** artefact set: `reviews/convergence_log.md` retains responsibility for **Trajectory-synthesis prose only** — append-only per-iteration narrative of what the user directive was at each boundary, which bundles were folded in, which DND artefacts were verified, which three-path choice was offered; named-owner status on any still-`ESCALATED` finding (including `current_owner` / `transferred_to` / `transfer_rationale` per §3.2.1) continues to live in the prose. `reviews/convergence_journal.jsonl` carries the **per-iteration mechanical state** — one JSON line per iteration under the **P-4 core nine keys** `{cycle_id, iteration, convergence_metric, check8_aggregate, manuscript_hash, new_findings_count, delta_lines, accessibility_gate_state, timestamp}` plus **optional v0.8.0 keys** (`paragraph_hash_map` per §3.3.4) — see §3.3.4. Both files become append-frozen at the terminal signoff. |
| **Exit artefact** | `reviews/ph3_convergence_signoff.md` — **cumulative** signoff artefact with a new row per iteration. Each row is a machine-readable structured entry consumed by the Ph4 Reflector-full pass. Two row sub-types: **terminal** rows (`is_terminal: true`, flips `Ph3 → Ph3_converged`) and **re-engagement** rows (`is_reengagement: true`, used to clear `[Ph3-STALE]` per §3.3.1). Full row contracts in §6.3a. |
| **Absorbs milestone** | M4b (iterative revision cycles — plan-originated subdivision per §4). |
| **Active agents** | Full four-agent loop (Planner, Evaluator, Generator, Reflector-lightweight). |
| **Reflector mode** | Lightweight: confirmation-failed history tracking, drift check, reflexivity check. Lessons extraction is deferred to Ph4. |
| **Iteration bound** | None. Ph3 is a user-gated unbounded loop. |
| **Convergence metric** | **v0.8.0 — P-12 vector.** Per iteration, `reviews/convergence_journal.jsonl` carries a **four-component** `convergence_metric` object (see §3.3.1a) after migration via `scripts/migrate_convergence_journal_v075.py`; the prior scalar `diff_lines_vs_previous_round / total_section_lines` is preserved inside that object as `legacy_scalar` for audit. Pre-migration rows remain scalar until the migration runs. The vector is **observational for components (1)(3)(4)**; component (2) aligns with §3.3.3. Accessibility remains **gating** at terminal signoff. |
| **Convergence warning threshold** | **v0.8.0.** For journal rows in the **object** shape, `[CONVERGENCE-STABLE]` requires **three consecutive** iterations each satisfying **all** tests in §3.3.1a **and** no live Check 8 BLOCKER (§3.3.3). For rows still in the **legacy scalar** shape, the historical rule remains: scalar `convergence_metric < stability_threshold` (default `0.01`) for **two** consecutive rounds **and** no live Check 8 BLOCKER. If the line-diff scalar is stable but a Check 8 BLOCKER remains live, the Planner emits `[CONVERGENCE-BLOCKED-ACCESSIBILITY]` instead. The warning does not force closure. |
| **Staleness warning** | The field `ph3_last_activity_at` is tracked per section. `[Ph3-STALE]` is a **purely-computed flag** derived from the delta between `ph3_last_activity_at` and wall-clock `now`; no schema field stores the flag (§6.0 invariant preservation). **Within Ph3 the computed flag is advisory; at the MCR boundary it is gating** — see §3.3.1 for the dual-state semantics. When the delta exceeds `ph3_staleness_budget` (default 90 days), the Planner surfaces `[Ph3-STALE]`: "This section has been at Ph3 for <N> days without activity; re-engagement may be needed to maintain current relevance." A null `ph3_last_activity_at` short-circuits the computation to *not stale*. |
| **External verifiers** | Optional at classification's discretion. |
| **Skills invoked** | Everything in Ph2 plus `IS-theory-pass` (Baird), `suchman-register-audit`, `grounding-audit` (full), `accessibility-overlay` (Step 0.2 companion to Check 8, optional at Ph3), `SAFEGUARD_LAYER.md` (all 8 checks), `DRIFT_CHECK`, `REFLEXIVITY_CHECK`, `public-interest-accountability-pass` (if classification flagged). |
| **User-gated exit** | Explicit signed *terminal* row in `ph3_convergence_signoff.md`. The final row of the cumulative file bearing `is_terminal: true` flips `current_phase: Ph3 → Ph3_converged` **subject to the §3.3.3 accessibility convergence gate** — the Planner refuses to write the flip while any live Check 8 BLOCKER exists. |
| **Wall-clock per iteration** | 15–45 min. Total Ph3 wall-clock is unbounded. |

#### 3.3.0 Ph3 evaluation profiles, diff-scope halo, and dispatch parity (v0.8.0, β P-9 / P-10 / P-11)

New at v0.8.0. Each Ph3 round's F6 `planner_dispatch_plan` artefact carries **`check_profile`**, selecting which Evaluator envelope applies:

| `check_profile` | Role |
|---|---|
| `refine` | Default iterative tightening — diff-scoped reads with a **context halo** per P-10 (`proposals/v0.7.5_phase3_refinement_loop_proposal.md` §P-10). |
| `structural` | Section-structure edits (boundary moves, heading renames, anchor-dependent changes); selected when the Planner's `structural_delta_flag: true` on the same F6 row. |
| `deep` | Full seven-step Evaluator envelope parity with pre-v0.8.0 Ph3; satisfies the **pre-MCR Ph3-deep pass** safety net (β-P-9a, §3.4). |

**`halo_scope` (P-10).** Each scheduled check carries **`halo_scope` ∈ {`paragraph`, `immediate_neighbour`, `containing_section`}**, declaring how far beyond the literal diff the Evaluator may read while still honouring the Rule 1 full-file grounding floor. **Normative per-check assignments** are published in `references/DETERMINISTIC_CHECKS.md` and `references/SAFEGUARD_LAYER.md`; those files are the authoritative matrix — this protocol imports them by reference and does not duplicate the full check-id cross-product here.

**User override.** The user may override `check_profile` at the F6 approval checkpoint; the Planner records the override in the dispatch-plan `notes` (§P-11).

#### 3.3.1 `[Ph3-STALE]` dual-state semantics (Workflow Failure-Point defence)

The user's mandatory safety constraint (Workflow Failure-Point) requires that staleness gate MCR admission, even though it remains advisory within Ph3. `[Ph3-STALE]` is a **purely-computed flag** derived from `ph3_last_activity_at` versus wall-clock `now`; no schema field stores the flag itself (Option A resolution — see §6.0 for the invariant-preservation rationale). The dual-state contract:

- **Within Ph3 (advisory).** When the Planner's computed staleness delta exceeds `ph3_staleness_budget`, `[Ph3-STALE]` surfaces as an advisory. It does not interrupt iteration, force closure, or block any Ph3 round.
- **At MCR (gating).** When the MCR pipeline runs (§9 admission gate), it recomputes `[Ph3-STALE]` for every section. If any section evaluates stale, MCR pauses and emits `E-MCR-BLOCKED-Ph3-STALE` listing the affected sections. Admission cannot proceed until every stale section's recomputed value drops below threshold.
- **Clearance mechanism.** A stale section's flag is cleared by appending a *re-engagement signoff row* to its `ph3_convergence_signoff.md` (`is_reengagement: true`, `cleared_stale_at: <ISO-8601>`, signed by the user — see §6.3a for the full required-field contract). The act of recording the row updates `ph3_last_activity_at` to the signoff timestamp, which mechanically drops the computed staleness delta below `ph3_staleness_budget`, which means the next Planner recomputation returns `[Ph3-STALE] = false`. The re-engagement row does **not** flip `current_phase` to `Ph3_converged`; it only refreshes the activity timestamp. The terminal signoff (whose `is_terminal: true` is the closure trigger) is independent of the re-engagement row, and the user remains free to issue further Ph3 iterations after re-engagement.
- **Distinction from forced closure.** The re-engagement requirement does not force the user to close Ph3 for the section — the user may iterate further after issuing the re-engagement row. What it forces is *active acknowledgment* that the section remains viable, which protects the MCR pipeline against stale convergence records being used as proof of submission-readiness.
- **Cold-start case.** A section with `ph3_last_activity_at: null` (e.g., a section freshly migrated from v0.6.0 per §12 step 7) short-circuits to `not stale`. The first post-migration Planner pass populates the field, at which point normal staleness computation resumes.

This dual-state behaviour is plan-originated. Option A (purely-computed) semantics are locked in at v0.7.0; the alternative (Option B, a persisted `[Ph3-STALE]` boolean on `SectionStateObject`) was rejected to preserve the §6.0 field-count discipline (now **sixteen** top-level section fields at v0.8.0 including `pre_mcr_deep_pass_completed` per `phase_state_schema.md` §2 — still no separate staleness boolean).

#### 3.3.1a Multi-signal convergence vector and three-round window (v0.8.0, β P-12)

New at v0.8.0 as **P-12** (`proposals/v0.7.5_phase3_refinement_loop_proposal.md` §P-12; `proposals/v0.8.0_upgrade_architecture.md` §3.2 Phase 2.2). The line-diff scalar alone is insufficient to separate lexical churn from structural churn; the journal therefore records a **four-component stability signature** on `convergence_metric` (migration from legacy scalars: `scripts/migrate_convergence_journal_v075.py`). For **closure advisories**, the Planner uses a **three-round** window: `[CONVERGENCE-STABLE]` may be emitted only when **three consecutive** journal rows for the section each satisfy **all** of:

1. **`grounding_clean`:** `true` — no open `R-Refl-GR-*` grounding-audit finding on the iteration's declared scope.
2. **`check8_aggregate_ok` (or equivalent):** the Check 8 aggregate is not `MAJOR` and not `BLOCKER` (BORDERLINE is permitted under the same semantics as §3.3.3's MAJOR/BLOCKER split for advisories vs. terminal gate). Migrated journal objects surface this as the boolean `check8_aggregate_ok`; native v0.8.0 writers may record the aggregate string plus a derived flag — either representation must agree on pass/fail of this test.
3. **`findings_count_delta` (Check-8-excluded):** absolute change in **non–Check-8** finding count versus the prior row ≤ **1** (decorrelation patch A-OR-1 in §P-12).
4. **`line_delta`:** absolute line churn versus the prior row ≤ **0.5 %** of the section's authored line count (provisional threshold — same caveat as §P-12).

**Threshold caveat.** Numeric thresholds in (3) and (4) ship **`v0.7.5-provisional` / `v0.8.0-provisional`** pending empirical derivation (`proposals/v0.7.5_threshold_derivation.md`).

**§3.3.3 unchanged.** Terminal `TerminalSignoffRow` writes remain **Check-8 BLOCKER–gated**; the vector does not relax that gate.

**Legacy scalar rows.** Until migrated, the Ph3 table's historical two-round scalar rule applies; after migration, use this subsection. Rows partially backfilled by the migration script may carry `"[v0.8.0-BACKFILL-N/A]"` on individual components — those components cannot pass until human or artefact backfill replaces the sentinel.

#### 3.3.2 Ph3 stability sub-mode (v0.7.4, P-2)

The Ph3 **stability sub-mode** is a reduced-envelope iteration that runs when the manuscript under review is byte-stable against the prior Ph3 close. It is the P-2 response to the failure mode iter-7 of INF3006Y surfaced: a Ph3 round consumed the full seven-step Evaluator envelope on a manuscript whose bytes had not changed since the prior Ph3 close, producing no new findings but consuming full-pass cost (n=1; see Ph.D.-root CLAUDE.md §12.10 for the evidentiary caveat). The sub-mode replaces the full pass with a narrow audit envelope — grounding audit plus Check 8 deterministic counters — and escalates back to the full Ph3 envelope via **trigger 30** `stability_mode_escalated_to_full_ph3` whenever the reduced pass surfaces any finding that cannot be confidently ruled as an inheritance pass.

**S-0 gate — the hash-match precondition.** A stability-mode pass is admissible only when the current iteration's manuscript is byte-stable against the prior iteration's recorded `manuscript_hash` (SHA-256 of the F1/F2/F3/F5 substrate per §3.3.4). The Planner computes the current hash at Phase 0.5 (session-state cache warm) and compares it against the journal's most-recent row for the same section. A hash match admits stability mode; a hash mismatch forces drop-through to full `run-phase-3`. Partial inheritance (some F-families unchanged, others changed) is NOT admitted — the gate is all-families-match or drop-through.

**The reduced Evaluator envelope.** Under stability mode the Evaluator runs **only** (a) the grounding audit (Rule 1 full-file read; R-Refl-GR-* finding classes remain live), and (b) the `DETERMINISTIC_CHECKS §9b` Check 8 pre-filter counters (`cadence_flag_count`, `signpost_flag_count`, `jargon_density_flag_count`). The seven-step judgment pass is skipped; SAFEGUARD checks 1/4/5/7 are skipped; Coupling E.2 graph-grounding overlay (Step 0.2) is skipped. Step 0b external verifier probes are also skipped — stability-mode is an inheritance audit, not an independent review.

**Admission, escalation, and close.** A stability-mode pass has three possible outcomes:

- **Clean — inheritance admitted.** Grounding audit passes (no `R-Refl-GR-*` findings), and the Check 8 counters are byte-identical to the prior iteration's counters for the same section. The Planner writes a `ph3_iteration_round` row (trigger 17) with `stability_mode: true` in `notes`, refreshes `ph3_last_activity_at`, and admits the round. No new findings are surfaced; the F1/F2/F3/F5 inheritance substrate from the prior iteration is cited by hash-reference in the new iteration's F5 consolidated-findings artefact rather than re-computed.
- **Finding — escalate to full Ph3.** The grounding audit surfaces a finding, or Check 8 counters diverge from the prior iteration's recorded counters despite byte-identical manuscript (a prior iteration's counter miscount, a sub-check pre-filter upgrade mid-round, a deterministic-check false-negative being corrected). The Planner writes a `stability_mode_escalated_to_full_ph3` row (trigger 30) with `notes` naming the triggering finding class, then immediately opens a full `run-phase-3` pass on the same section. The escalated full-Ph3 round that follows may itself be manuscript-level if the resulting revision directive touches multiple sections; in that case the escalated round's rows use `ph3_iteration_round_manuscript` (trigger 29) per §3.3.5. Iteration budget is charged for the full-Ph3 round only; the refused stability pass does not consume budget.
- **Hash-match failure.** The S-0 gate returns `hash_mismatch`. The Planner does not open a stability-mode row at all — it drops through to full `run-phase-3` immediately, no `stability_mode_escalated_to_full_ph3` row, no `stability_mode: true` notes marker. The full-Ph3 round opens under trigger 17 (or trigger 29 under batching) as normal.

**Scope constraints.** Stability mode is:

- **Section-scoped.** A stability-mode pass is always over a single section; P-7 manuscript-level batching does NOT apply to stability-mode rounds per §3.3.5. A manuscript-level stability pass would require hash-match across every in-scope section simultaneously, which is both unlikely and audit-ambiguous; the section-scoped rule sidesteps the ambiguity.
- **Not inheritance-admissible for the F6 dispatch-plan artefact.** Each stability-mode round authors a fresh F6 under Phase 0.6 per invariant I-Planner-10 (§5.2a) with `stability_sub_mode_anticipated: true` and the reduced `checks_scheduled[]` list (grounding_audit + deterministic_step_0a_subset_check8 only). F6 inheritance is never admitted (§7a.4); P-2's inheritance admission applies to F1/F2/F3/F5 only.
- **Not a substitute for Ph4 external-verifier internalization.** A section that enters Ph4 must have been through at least one full `run-phase-3` pass; a section that has only seen stability passes since Ph2 cannot be admitted to Ph4 because the external-verifier probes that Ph4's G.4 signoff depends on have never run. The Planner refuses Ph4 admission for a section whose most recent Ph3 row was a stability pass; the user must run one full-Ph3 pass before MCR admission.
- **Reflector-lightweight runs at reduced scope.** The Reflector-lightweight probe at stability-mode round close skips the tier-row contract audit (Phase 2f step 6.5 SA-family) if no subagent was dispatched — stability mode is a Planner-plus-Evaluator pass with no subagent envelope. The grounding-audit integrity check and the frontmatter contract audit (P-3 FM-family findings) continue to run.

**Skill surface.** The stability sub-mode is invoked via `skills/run-phase-3-stability/SKILL.md`. The skill is a thin peer of `run-phase-3` that implements the S-0 gate and the reduced envelope; on escalation it hands control back to `run-phase-3` with the trigger 30 row already written.

**Absent-means-noncompliant migration.** Projects on v0.7.3 have no stability-mode history and no `manuscript_hash` field populated in the convergence log. The first post-migration iteration under v0.7.4 cannot run stability mode — there is no prior hash to compare against. The stability-mode gate returns `hash_missing_prior_iteration` and drops through to full `run-phase-3`; the iteration populates `manuscript_hash` and subsequent iterations may qualify for stability mode.

#### 3.3.3 Check 8 accessibility convergence gate (Reader-Experience defence)

New at v0.7.2. The Ph.D. Research-root `CLAUDE.md §13` binds the Generator to reader-accessibility at every P-stage and phase. Until v0.7.2 the convergence metric (`diff_lines_vs_previous_round / total_section_lines`) was the sole determinant of `[CONVERGENCE-STABLE]`; a section could therefore settle into line-diff stability while carrying open §13.3 violations — the metric would fire its stability advisory for prose that was inaccessible at first read. The accessibility convergence gate closes that loophole by coupling the terminal signoff flip to the SAFEGUARD Check 8 result.

The contract:

- **Gate trigger.** On every `TerminalSignoffRow` write attempt (`is_terminal: true`), the Planner queries the most recent `reviews/safeguard_layer_results.md` for the Check 8 aggregate verdict. If the aggregate verdict is `BLOCKER` — i.e., at least one Sub-check A–H finding carries BLOCKER severity — the Planner refuses the write and emits failure code **`E-Ph3-ACCESSIBILITY-BLOCKER-AT-SIGNOFF`** (see `phase_state_schema.md §6.1`). The section remains at `current_phase: Ph3`; iteration resumes on the next Planner pass. **Sub-check G transitional exception (2026-04-23).** A Sub-check G BLOCKER under an active `advisory_until: next_manuscript_at_ph3` flag (per `READER_ACCESSIBILITY.md §13.5` and `SAFEGUARD_LAYER.md` Check 8 Sub-check G) is recorded in the aggregate but does **not** fire the gate: the Planner reads the A–F (and A–H once H's flag has retired) aggregate alone for the terminal-signoff decision while the flag is active. The flag retires automatically on the first Ph3 entry of a manuscript whose Ph1 classification postdates 2026-04-23, at which point Sub-check G contributes at full severity without further action. **Sub-check H transitional exception (2026-04-27 v0.10.1).** A Sub-check H BLOCKER under an active `advisory_until: H_two_revision_cycles` flag (per `READER_ACCESSIBILITY.md §13.5` and `SAFEGUARD_LAYER.md` Check 8 Sub-check H) is recorded in the aggregate but does **not** fire the gate: the Planner reads the A–G aggregate alone for the terminal-signoff decision while the H flag is active. The H flag is cycle-counting (rather than manuscript-scoped as G's is) and retires after `h_advisory_cycles_observed >= 2` in `reviews/classification.md`, at which point Sub-check H contributes at full severity without further action.
- **Gate scope.** Only Check 8 BLOCKERs block the flip. Check 8 MAJORs produce a `[CONVERGENCE-BORDERLINE-ACCESSIBILITY]` advisory on the terminal signoff attempt but do not block the write; the Planner surfaces the advisory to the user, who may still proceed. MINORs do not interact with the gate.
- **Clearance mechanism.** A BLOCKER is cleared by a Generator iteration that resolves the cited finding and an Evaluator re-check that confirms the finding no longer appears in the re-run Check 8 output. The re-check is a normal Ph3 iteration; no special dispatch is required. Once the re-checked Check 8 no longer emits the BLOCKER, the next `TerminalSignoffRow` write attempt succeeds.
- **Iteration accounting.** A refused terminal signoff write does **not** consume an iteration budget (`iteration_count_at_current_phase` is not incremented). The subsequent Generator + Evaluator round that clears the BLOCKER *does* consume an iteration. This avoids penalizing the user for the gate's protective action.
- **Logging.** When the gate fires, the Planner writes a row to `phase_entry_log` with trigger **`ph3_accessibility_blocker_surfaced`** (see `phase_state_schema.md §6`, new trigger). The row's `notes` field names the failing Check 8 sub-check(s) (A/B/C/D/E/F/G/H) and the affected locator(s); a Sub-check G finding logged under an active `advisory_until: next_manuscript_at_ph3` flag, or a Sub-check H finding logged under an active `advisory_until: H_two_revision_cycles` flag, carries the `advisory_under_flag: true` annotation so the Reflector Phase 2g recurrence audit can separate advisory G/H findings from gate-firing A–F BLOCKERs. When the gate clears, the successful terminal signoff row's `notes` field documents that the accessibility BLOCKER is resolved ("Check 8 aggregate: PASS at terminal signoff").
- **Independence from line-diff stability.** Check 8 can fire BLOCKER while the line-diff metric is stable (the paradigmatic case the gate exists to catch) and the line-diff metric can be unstable while Check 8 passes. Both dimensions must resolve for `[CONVERGENCE-STABLE]` to issue and for the `TerminalSignoffRow` to write.

The gate is plan-originated and is the architectural commitment that makes Ph3 the Lifecycle-Phase Ladder's genuine locus for reader-accessibility work. The alternative designs considered — a parallel float metric summed into the line-diff score, a soft advisory that did not block the flip, deferring all accessibility audit to Ph4 — were rejected because (i) a composite metric obscures which dimension is failing, (ii) a soft advisory reproduces the pre-v0.7.2 loophole, and (iii) deferring to Ph4 mixes submission-bound certification with accessibility repair, raising the cost of accessibility fixes and risking EG-1 demotion cascades.

#### 3.3.4 P-4 convergence-log contract split (v0.7.4)

New at v0.7.4 as proposal **P-4** of the v0.7.4 economic-efficiency package (see Ph.D. Research-root `CLAUDE.md §12.10`). Before v0.7.4 the file `reviews/convergence_log.md` carried two overlapping responsibilities: **per-iteration mechanical state** (cycle id, convergence metric, Check 8 aggregate verdict, accessibility-gate state, line-delta footprint, timestamp) and **Trajectory-synthesis prose** (the narrative that tells a human-reader how iteration N got there, what the user directive was, which bundles were folded in, which DND artefacts were verified, which three-path choice was offered at the boundary checkpoint). The overlap meant the Planner re-parsed prose on every round to extract the mechanical fields — the iter-7 diagnostic attributed roughly 11% of the observed cost overrun to this re-parse — and it meant that drift between the prose and the mechanical fields had no machine-checkable locus.

The split, materialized at v0.7.4:

- **`reviews/convergence_log.md` — Trajectory-synthesis prose only.** The file retains its role as the narrative record; each iteration remains a Markdown `## Iteration N` block. New iteration bodies continue to be written as narrative. The file is append-frozen at the terminal signoff as before. At migration time a migration banner is inserted at the top of the body and `frozen_status: true`, `journal_path`, and `p4_contract_split_applied_at` are added to the frontmatter.
- **`reviews/convergence_journal.jsonl` — per-iteration mechanical state.** One JSON line per iteration under the **P-4 nine-field core** (extended at v0.8.0 with optional `paragraph_hash_map` and with `convergence_metric` widened to object per §3.3.1a):

  ```jsonc
  {
    "cycle_id":                  "<str>",                   // e.g. "ph3_iter4_batch_2026-04-20"
    "iteration":                 <int>,                     // 1-indexed, strictly increasing within a Ph3 round
    "convergence_metric":        "<float|null|object>",     // v0.7.4: scalar diff_lines/total_section_lines. v0.8.0 P-12: four-component object (see §3.3.1a; migration: scripts/migrate_convergence_journal_v075.py [retired from tree]).
    "check8_aggregate":          "<PASS|BORDERLINE|MAJOR|BLOCKER|null>",
    "manuscript_hash":           "<str|null>",              // SHA-256 of the F1/F2/F3/F5 substrate; enables P-2 stability-mode
    "paragraph_hash_map":        "<object|null>",           // v0.8.0 P-10: optional { "p-0000": "<sha256-hex>", ... } from scripts/paragraph_hash_map.py — writer lands when Planner Phase 0.6 emits the map; null until then
    "new_findings_count":        <int|null>,
    "delta_lines":               <int|null>,
    "accessibility_gate_state":  "<CLEAN|BORDERLINE|BLOCKED|null>",
    "timestamp":                 "<ISO-8601 UTC|null>"
  }
  ```

- **Writer contract.** The Planner is the sole writer of the journal. The Evaluator and Reflector are readers. Appends are append-only within a Ph3 round and the file becomes append-frozen at the terminal signoff (mirroring `convergence_log.md`'s freeze semantics). Iteration indices must be strictly increasing within the file; gaps, reuse, or regression are a Reflector Phase 2f finding. Unknown top-level keys beyond the P-4 core plus the v0.8.0 optional keys declared in §3.3.4 are a Reflector Phase 2f contract drift unless the row carries an explicit forward-compatibility note agreed at scope-freeze.
- **Migration.** Projects on v0.7.3 or earlier run `scripts/migrate_convergence_log_v074.py --project-root <project>` to backfill the journal from the legacy log, back up the legacy file to `convergence_log.md.v073.bak`, insert the migration banner, flip `frozen_status: true`, and emit `reviews/migration_report_convergence_log_v074.md`. Migration is idempotent: a pre-existing journal short-circuits the re-parse and only the report is re-emitted. Fields that the legacy prose did not record (`manuscript_hash`, `new_findings_count`) migrate as `null`; the migration report names the null-field counts so the user and the Reflector can see what was not recoverable.
- **Drift-check contract.** The Reflector's Phase 2f audit compares each JSONL row against the corresponding prose iteration block; divergence — a metric in the prose that does not match the journal, a check8 verdict in the prose that does not match the journal, a missing row on either side — is filed as `[P4-SPLIT-DRIFT]` (MAJOR by default; BLOCKER on resubmission).
- **Downstream consumers.** P-2 (Ph3 stability sub-mode) uses `manuscript_hash` from the prior iteration's journal row to decide whether to run the reduced Evaluator pass; the §3.3.3 Check 8 accessibility convergence gate consumes `check8_aggregate` and `accessibility_gate_state` from the current row. P-10 diff-scoping consumes `paragraph_hash_map` when present (from `scripts/paragraph_hash_map.py`, Planner Phase 0.6). The `[CONVERGENCE-STABLE]` surface (§3.3 convergence-warning-threshold row) consumes **either** two consecutive scalar rows with `convergence_metric < stability_threshold` **or** three consecutive rows satisfying §3.3.1a when `convergence_metric` is the object shape.

The split does not change the convergence semantics of Ph3 and is not a ceiling change; it is a contract refactor that lets the Planner read one JSONL line instead of parsing N prose blocks per round, and that gives the Reflector a machine-checkable drift locus.

#### 3.3.5 Manuscript-level Ph3 iteration batching (v0.7.4, P-7)

New at v0.7.4 as proposal **P-7** of the v0.7.4 economic-efficiency package (see Ph.D. Research-root `CLAUDE.md §12.10`). Before v0.7.4 every Ph3 iteration appended one `ph3_iteration_round` row per section it touched, and each row carried a distinct `cycle_id`. A single revision directive that touched six sections therefore produced six independent rows with six cycle_ids, even though the underlying Generator pass was one revision round. The per-row overhead — Planner lookup, ledger append, F5 aggregation — was linear in section count, not in iteration count, and the iter-7 diagnostic attributed roughly 9% of the observed cost overrun to this pattern when the manuscript was substantially revised across many sections in a single round.

The batching contract, materialized at v0.7.4:

- **When to batch.** A manuscript-level Ph3 iteration is one in which a single Generator dispatch produced edits to two or more sections under a single revision directive. Single-section iterations continue to use the legacy `ph3_iteration_round` trigger and receive one row with one `cycle_id`. When N ≥ 2 sections are touched in one dispatch, the Planner emits **N rows** — one per affected section — all carrying `trigger: ph3_iteration_round_manuscript` and all sharing a **single `cycle_id`** of shape `ph3_iter<M>_batch_<YYYY-MM-DD>` where `<M>` is the manuscript-level iteration index (increments across all sections touched in this round, not per-section).
- **Per-section monotonicity preservation.** Each row still records `prev_phase` and `new_phase` for its section, and the §7 monotonicity check still applies row-by-row. A manuscript-level iteration cannot regress a section from `Ph3_converged` back to `Ph3` (that would require an EG-1 or EG-7 trigger, per §7); the batching trigger only authorises forward motion within Ph3 or a no-op Ph3 → Ph3 iteration row for the affected sections.
- **Row-group integrity rule.** All rows in a single manuscript-level batch must be emitted as a contiguous run in each affected section's `phase_entry_log[]` (no interleaving with rows from other triggers) and must carry the same `cycle_id`. A batch with a split `cycle_id` across its member rows is a Reflector Phase 2f finding (`R-Refl-Batch-1` MAJOR).
- **Cycle-id uniqueness.** The `cycle_id` must be unique across all batches in the manuscript's lifetime. Re-use is a Reflector Phase 2f finding (`R-Refl-Batch-2` MAJOR). The Planner checks for collisions at batch-write time by scanning prior `cycle_id` values in all sections' `phase_entry_log[]` under the session-state cache (§0.5 / P-6).
- **Relationship to `convergence_journal.jsonl`.** The journal (§3.3.4) carries one row per manuscript-level iteration whose `cycle_id` matches the shared `cycle_id` written into the N section rows. The many-to-one relationship between section rows and journal rows is the audit surface: a journal row without matching section rows is a `[P7-BATCH-ORPHAN]` finding; N section rows without a journal row is a `[P7-JOURNAL-MISSING]` finding. Both are Reflector Phase 2f MAJORs.
- **F5 consolidated-findings aggregation.** The Planner's F5 artefact for a manuscript-level iteration reports the batch once (naming the shared `cycle_id`) and lists the N affected sections under its `per-section rollup` body section. Per-section severity counts sum to the batch's `aggregated_severity` block; the F5 `iteration` frontmatter field carries `<M>` (the manuscript-level iteration index).
- **Interaction with P-2 stability sub-mode.** A stability-mode pass is always section-scoped and never triggers `ph3_iteration_round_manuscript`. If a stability-mode pass escalates via `stability_mode_escalated_to_full_ph3` (trigger 30), the escalated full-Ph3 round that follows may itself be manuscript-level if the resulting revision directive touches multiple sections; in that case the escalated round's rows use `ph3_iteration_round_manuscript` as normal.
- **Backward compatibility.** Pre-v0.7.4 projects carry only `ph3_iteration_round` rows (legacy section-scoped pattern); those rows are grandfathered and the Reflector does not retroactively file `R-Refl-Batch-*` findings against them. Post-v0.7.4 rounds use `ph3_iteration_round_manuscript` when N ≥ 2, `ph3_iteration_round` when N = 1.

The batching contract preserves the full per-section audit trail while collapsing the ledger-write overhead from `O(N_sections_touched)` to `O(1)` per manuscript-level iteration. It does not change convergence semantics — every section's iteration count still increments per batch it participates in.

#### 3.3.6 Ceiling-lock termination ranking (v0.7.4, P-8)

New at v0.7.4 as proposal **P-8** of the v0.7.4 economic-efficiency package (see Ph.D. Research-root `CLAUDE.md §12.10`). §9.4 already defines the MCR admission disjunction — a section is MCR-cleared if either `current_phase == Ph3_converged` or (`ceiling_locked == true` AND `last_approved_phase == applicable_ceiling`). What §9.4 does not specify is *when the Planner should propose that a section enter the ceiling-locked state* versus continuing to iterate. Before v0.7.4 the decision was implicit: a section kept iterating until the user manually escalated a `/cancel-climb` or the `convergence_metric` crossed the stability threshold on its own. The iter-7 diagnostic attributed roughly 7% of the observed cost overrun (n=1) to rounds that continued iterating on a section within a narrow band of the stability threshold while a single BORDERLINE advisory persisted unresolved — budget spent on diminishing returns rather than on material convergence.

P-8 materialises a **termination-ranking and proposal** contract. The contract does **not** change the §9.4 admission rule (the disjunction is unchanged) and does **not** add a new monotonicity-exempt trigger. It defines a Planner-authored pre-admission mechanism that surfaces ceiling-lock candidates to the user at iteration boundaries, ranked by distance-to-ceiling.

- **Tension-detection rule.** At every Ph3 iteration boundary (Planner's Phase 5.5 approval resolution), the Planner evaluates each in-scope section for *iteration-budget tension*. A section enters tension state when **both** conditions hold simultaneously at the iteration just closed:
  - The section carries an unresolved BORDERLINE-severity advisory from the most recent Evaluator pass — either a SAFEGUARD Check 8 `[CONVERGENCE-BORDERLINE-ACCESSIBILITY]` propagated into the row's `notes` per §3.3.3, or an equivalent severity aggregate returned as BORDERLINE by the Evaluator's consolidated-findings F1 artefact. A BLOCKER is not a tension state (Ph3 close is structurally refused via `E-Ph3-ACCESSIBILITY-BLOCKER-AT-SIGNOFF`); a CLEAN is not a tension state (the section can close via `Ph3_converged` on the user's normal terminal-signoff path); BORDERLINE is the unique severity that leaves the section sitting on the close/iterate boundary.
  - The section's **line-diff scalar** has remained within a **±0.01 band** of the stability threshold for at least **two consecutive iterations** without crossing it. Read `legacy_scalar` when `convergence_metric` is the v0.8.0 object shape (§3.3.1a); otherwise use the scalar `convergence_metric` directly. The band is symmetric around `stability_threshold` (default 0.03 per §3.3), so the tension band is `[0.02, 0.04]`; a section whose metric oscillates inside this band for two rounds has exhausted the near-linear convergence region and further iterations are unlikely to move it without a change in the revision directive.
  Both conditions must hold on the closing iteration; a single-round BORDERLINE with a fresh metric trajectory is not tension (iterate once more). The two-round window is plan-originated and is deliberately shorter than the three-round `[CONVERGENCE-STABLE]` advisory window (§3.3) because tension is about budget exhaustion, not convergence achievement.

- **Distance-to-ceiling metric.** For every section in tension state, the Planner computes `distance_to_ceiling(S) = abs(line_diff_scalar(S) − stability_threshold)` as a scalar in `[0, 0.01]` bounded by the tension band, where `line_diff_scalar(S)` is the journal's line-diff ratio (`legacy_scalar` when `convergence_metric` is an object, else the scalar field). Sections with the *lowest* distance rank highest in the ceiling-lock proposal (they are closest to closing and cheapest to terminate). Ties resolve by `iteration_count_at_current_phase` descending (the section that has spent more budget ranks higher, surfacing long-iterating sections preferentially). The metric is a *ranking signal*, not a phase-advancement gate; it does not by itself activate ceiling-lock.

- **Proposal artefact.** When at least one section enters tension state at an iteration boundary, the Planner writes `reviews/ceiling_lock_proposal_<YYYY-MM-DD>.md` under the P-3 frontmatter family **F5** (`planner_consolidated_findings`) extended with the **optional field `ceiling_lock_detected: true`** in frontmatter. The artefact body presents: (a) every tension-state section ranked by distance-to-ceiling (lowest first), (b) per-section evidence rows — the BORDERLINE advisory ID, the two-round metric trajectory as `[iter_N: metric_N, iter_N+1: metric_N+1]`, the iteration count consumed, the `applicable_ceiling` — (c) two disjunctive options per section presented to the user: **Option C (ceiling-lock)** activates `ceiling_locked: true` at the section's current `applicable_ceiling` and accepts the current state as terminal under §9.4's second disjunct; **Option I (iterate)** continues normal Ph3 iteration with the next round's Generator dispatch targeting the BORDERLINE finding directly. The artefact closes with a user-gated signoff line per option per section.

- **Approval semantics and the `[CEILING-LOCK-STABLE]` marker.** On user approval of Option C for a section, the Planner (i) sets `ceiling_locked(S) ← true` and `last_approved_phase(S) ← applicable_ceiling(S)`, (ii) appends a `TerminalSignoffRow` to `reviews/ph3_convergence_signoff.md` carrying `is_terminal: true` and the inline marker `[CEILING-LOCK-STABLE]` in the row's `notes` alongside the proposal-artefact path, (iii) writes a corresponding row to `phase_entry_log[]` using the **existing** trigger `user_approved_ph3_convergence_signoff` (no new trigger is added at v0.7.4 for P-8) with `notes` containing both `ceiling_locked:true` and `[CEILING-LOCK-STABLE]`, and (iv) flips `current_phase: Ph3 → Ph3_converged`. The section is now MCR-clearable via §9.4's second disjunct; no further iteration is performed unless EG-1 or EG-7 fires. On user approval of Option I, the Planner appends a normal `ph3_iteration_round` row (or `ph3_iteration_round_manuscript` under P-7 batching rules if the subsequent dispatch is manuscript-level) and re-dispatches; the proposal artefact is preserved under `reviews/` as audit trail.

- **Budget semantics.** A ceiling-lock approval consumes **one** `user_approved_ph3_convergence_signoff` row per section (per P-7 batching rules if multiple sections approve Option C in the same boundary), but does **not** consume the §9.7 +50% iteration reserve — the reserve carries forward to Ph4 intact. An Option I election also consumes one iteration row (per normal Ph3 semantics); the reserve accounting is identical.

- **Relationship to §9.4.** §9.4 defines *when* a ceiling-locked section is MCR-admissible (the disjunction rule, unchanged at v0.7.4). §3.3.6 defines *how* a section legally enters the ceiling-locked state mid-Ph3 via a user-gated proposal rather than via a silent Planner election. Together they close the surface: no Planner may raise `ceiling_locked(S) ← true` at Ph3 without a corresponding approved ceiling-lock proposal artefact (Reflector Phase 2f `R-Refl-Ceil-1` BLOCKER).

- **Relationship to P-2 stability sub-mode.** A section in Ph3 stability sub-mode (`run-phase-3-stability`) is *not* eligible for ceiling-lock proposal emission in the same round — stability-mode passes do not produce a fresh BORDERLINE advisory (by P-2 contract the pass is grounding + deterministic-counter only) and therefore cannot satisfy the tension-detection rule's first condition. Tension detection runs on the *full-Ph3 round that follows* a stability-mode escalation (trigger 30), not on the stability-mode pass itself.

- **Relationship to `[CONVERGENCE-STABLE]`.** `[CONVERGENCE-STABLE]` (§3.3, three-round sub-threshold) and the P-8 tension rule (two-round in-band plus BORDERLINE) are orthogonal signals. A section can receive `[CONVERGENCE-STABLE]` without ever entering tension (CLEAN verdicts throughout), and can enter tension without ever receiving `[CONVERGENCE-STABLE]` (metric inside the band but never strictly sub-threshold). When both fire simultaneously (three consecutive sub-threshold iterations, the last two of which also sit inside the tension band with a BORDERLINE advisory), the Planner surfaces both advisories in the same Phase 5.5 presentation and the user elects between a normal `Ph3_converged` close and a ceiling-lock close; the two paths differ in `ceiling_locked` state but both are MCR-admissible via §9.4.

- **Backward compatibility.** Pre-v0.7.4 projects carry no `ceiling_lock_proposal_*.md` artefacts and no `[CEILING-LOCK-STABLE]` markers in historical rows. The Reflector does not retroactively file `R-Refl-Ceil-*` findings against pre-v0.7.4 rows; migration is *absent-means-compliant*. Projects that entered `ceiling_locked: true` state under pre-v0.7.4 paths (explicit user `/cancel-climb` plus classification edit) remain valid under §9.4 without a retrofit proposal artefact.

The termination-ranking contract preserves user agency (ceiling-lock is *always* a user-gated election) while closing the budget surface: a BORDERLINE-plus-in-band section no longer silently consumes iteration budget until the user intervenes. The Planner surfaces the termination candidate explicitly, and the user's active election becomes the audit trail.

### 3.4 Ph4 — Finalize & Close

| Property | Value |
|---|---|
| **Phase goal** | Ship a submission-bound artefact and close the institutional-learning loop. |
| **Primary deliverables** | `submission_bundle/` (final manuscript, response letter if applicable, supplementary materials, cover letter); `reviews/lessons_learned_final.md` (Reflector-full extraction); `wiki/ingest_report_m5.md` (Coupling D); `reviews/plugin_update_proposals.md` (routed through the Planner). |
| **Exit artefact** | `reviews/ph4_ship_signoff.md` — G.4 sign-off plus user acknowledgment that the submission bundle is complete. Flipping `terminal_tier_reached: true` is irreversible. |
| **Absorbs milestone** | M5. |
| **Active agents** | Full four-agent loop (Planner, Evaluator, Generator, Reflector-full). |
| **Reflector mode** | **Full.** Lessons extraction, wiki ingest (Coupling D), concept-page retrofit (Coupling B), incremental stub backfill reconciliation against the Ph4 authoritative SK-16 pass (Coupling A-revised), lessons-to-wiki promotion (Coupling C), skill-retirement proposals under R1–R5, skill-addition proposals under the A1–A5 set (§5.4), tool-contract roundtrip probe. |
| **Planner as gatekeeper** | The Reflector emits raw proposal candidates; the Planner is the sole agent authorized to formalize them into `plugin_update_proposals.md`. No Reflector-emitted proposal lands directly in the artefact. (§5.2.) |
| **Admission gate** | Manuscript Convergence Report (MCR — renamed from Laggard Clearance Report per Q-D). Every section must read `current_phase: Ph3_converged`, with the amended ceiling-lock disjunction specified in §9.4. **Pre-MCR Ph3-deep pass (v0.8.0, β-P-9a):** every in-scope section must carry `pre_mcr_deep_pass_completed: true` in `reviews/phase_state.json` (`phase_state_schema.md` §2.1). If any section is `false`, MCR assembly refuses with **`E-MCR-PRE-DEEP-PASS-REQUIRED`** (`phase_state_schema.md` §2.1, §6.1 "Contracts enforced elsewhere"; enforcement wiring is the Planner MCR-assembly path and the pre-advance guardrail clause (f) in `scripts/pre_phase_advance_check.py` per `phase_state_schema.md` §7). **Additional admission requirement:** no section may compute to `[Ph3-STALE] = true` at admission time (§3.3.1); admission pauses with `E-MCR-BLOCKED-Ph3-STALE` until every stale section issues a re-engagement signoff row that refreshes its `ph3_last_activity_at`. **EG-7 re-admission semantics:** when EG-7 (size-class change) fires at Ph4, the affected section drops to `current_phase: Ph3` for at least one iteration before re-running MCR — the existing convergence record was written against a different review contract and cannot be reused against the new class. Invocation with any section below the admission state is rejected with an MCR-first response. |
| **External verifiers** | Required (Class 1 / 1.5 / 2 / 3 per `EXTERNAL_VERIFIERS.md`). |
| **Skills invoked** | Everything in Ph3 plus `ingest-m5-to-wiki`, `retrofit-concept-grounding`, `backfill-source-stubs-from-references` (the authoritative Ph4 pass that reconciles Ph1 incremental stubs), `promote-lessons-to-wiki`, `tool-contract-roundtrip`, `graph-grounding-overlay` (final pass). |
| **User-gated exit** | Signed G.4 + `ph4_ship_signoff.md`. |
| **Wall-clock target** | 90 min – several sessions depending on manuscript size. |

### 3.5 T4R — Response-Letter Sibling (renamed from T3R)

The response-letter sibling ladder, called T3R in v0.6.0, is renamed **T4R** at v0.7.0 to reflect its terminal-artefact nature. A response letter is a finalization artefact by definition. The skill (`response-letter-review`) retains its entry point (`/review-letter`), does **not** consume the main manuscript's `phase_state.json`, and runs a compressed four-stage pass: draft → review → iterate → finalize, packaged in a single skill invocation. The Reflector-full responsibilities are invoked at T4R close: lessons from the review round, optional Coupling D ingestion of the rebuttal.

### 3.6 Terminal-phase (Ph4) composition — normative skill list

*Source: draft-5 §§3.4, 7.1.* A Ph4 run that omits any applicable row is structurally incomplete; the Reflector flags the omission as a Category 6 violation.

| Skill / agent | Role at Ph4 | Loaded at Ph3? |
|---|---|---|
| `classify-manuscript` | Re-verify classification if stale | no |
| Planner | Orchestration, MCR admission, Reflector gatekeeping | yes |
| Evaluator (full seven-step) | Terminal judgment pass | yes |
| `quick-deterministic` | Pre-flight mechanics | yes |
| `IS-theory-pass` (Baird) | IS-venue compliance | yes (since Ph3) |
| `sentence-level-pass` (Bacon) | Sentence craft | yes (since Ph2) |
| `narrative-structure-pass` (Sexton) | Narrative arc | yes (since Ph2) |
| `suchman-register-audit` | Register audit | yes (since Ph3) |
| `p-stage-checker` | P-stage vocabulary (drift-only) | yes (drift-only) |
| `check-contradictions` | Co-invoked-source contradictions | yes (since Ph2) |
| `check-abstract-body` | Abstract–body consistency | yes (since Ph2) |
| `grounding-audit` | Grounding Protocol compliance | yes (full since Ph2) |
| `public-interest-accountability-pass` | Policy-critical framing | yes if flagged |
| SAFEGUARD Layer (8 checks) | Integrity audit | subset {1,4,5,8} since Ph2; all eight since Ph3 (Check 8 convergence-gating at Ph3 per §3.3.3) |
| DRIFT_CHECK | Theoretical drift | yes (since Ph3) |
| REFLEXIVITY_CHECK | Positionality audit | yes (since Ph3) |
| EXTERNAL_VERIFIERS | Class 1 / 1.5 / 2 / 3 | **required at Ph4; optional at Ph3** |
| `graph-grounding-overlay` | Wiki coupling | **Ph4 final pass** |
| `backfill-source-stubs-from-references` (SK-16) | Authoritative wiki stub pass reconciling Ph1 incrementals | **Ph4 authoritative** |
| `retrofit-concept-grounding` | Wiki grounding retrofit | **Ph4 mandatory** |
| `tool-contract-roundtrip` | Verifier-MCP sanity | **Ph4 mandatory** |
| Generator | Submission-bundle assembly | yes |
| `advisor-escalation` | Strategic consult | if flagged (available at any phase) |
| G.4 sign-off | Submission closure | **Ph4 terminal** |
| Reflector-full (`run-reflection`) | Lessons extraction, Couplings A-revised / B / C / D closure, R1–R5 retirement proposals, A1–A5 addition proposals | **Ph4 terminal** |
| `ingest-m5-to-wiki` | Coupling D ingestion | **Ph4 terminal** |
| `promote-lessons-to-wiki` | Coupling C closure | **Ph4 terminal** |

---

## 4. Milestone supersession (replaces `AGENT_ORCHESTRATION.md §10.1`)

*Source: draft-5 §4.*

### 4.1 Supersession clause

This section supersedes `AGENT_ORCHESTRATION.md §10.1`'s definition of M1–M5. The v0.6.0 definitions bind M1 to *Project Memo*, M2 to *Annotated References*, M3 to *Structured Outline*, M4 to *Paper Draft* (single milestone), and M5 to *Final Paper*. Under v0.7.0, the milestone axis is absorbed into the phase axis, and the milestone labels are repurposed to name the *workflow activities* each phase owns. The pre-drafting milestones (M1–M3) collapse into Ph1 because the absence of an Evaluator at Ph1 makes subdividing them procedurally inert; the drafting milestone (M4) is split into M4a (first review) and M4b (iteration) because those activities differ in kind, not merely in rigor.

The declared reason for supersession is that the v0.6.0 definitions describe *artefacts* (memo, references, outline, draft, paper), while the v0.7.0 definitions describe *activities* (ideation, lit review, method, first review, iteration). Under the lifecycle framing the activity axis is primary; the artefact axis is subsumed into the per-phase exit-artefact contracts in §§3.1–3.4. The v0.6.0 artefact names are preserved as recommended outputs within Ph1 (memo under `research_notes/project_memo.md`, annotated references under `research_notes/annotated_references.md`, outline under `manuscript/outline.md`), but they are no longer milestone-defining.

### 4.2 M1–M5 under v0.7.0

| Milestone (v0.7.0) | Phase | Activity | Recommended v0.6.0 artefact (not milestone-defining) |
|---|---|---|---|
| **M1 — Concept / ideation / problem framing** | Ph1 | Problem statement drafted. | `research_notes/project_memo.md` |
| **M2 — Literature review / theoretical framing** | Ph1 | Generator drafts literature-review prose; incremental SK-16 sibling produces wiki source stubs. Full `grounding-audit` required (Q-E exception). | `research_notes/annotated_references.md` |
| **M3 — Method + early draft** | Ph1 | Method and initial analysis sections drafted to prose-completeness. | `manuscript/outline.md` (as scaffolding within `main.md`) |
| **M4a — First reviewed-and-revised pass** | Ph2 | First Evaluator engagement; BLOCKER/MAJOR disposition; named-owner records for ESCALATED. | `manuscript/main.md` at first-reviewed state |
| **M4b — Iterative revision cycles** | Ph3 | Cumulative signoff-row iteration; user-gated unbounded loop. | `manuscript/main.md` at convergence state |
| **M5 — Submission-bound final** | Ph4 | Submission bundle; Reflector-full; institutional learning. | `manuscript/main.md` at submission-bound depth |

### 4.3 Downstream consequence

Because §4.1 supersedes `AGENT_ORCHESTRATION.md §10.1`, the reduced-loop dispatch for M1–M3 specified in `AGENT_ORCHESTRATION.md §10.2` must be rewritten to fire within Ph1 under the new semantics. The rewrite reassigns §10.2's M1-specific pre-drafting loop to a new Ph1 sub-phase with the Planner and Generator as its only active agents. This is a rewrite target tracked in the v0.7.0 release notes.

---

## 5. Agent role matrix

*Source: draft-5 §5.* This matrix is the normative per-phase agent-role assignment; `AGENT_ORCHESTRATION.md §3` must be rewritten to match.

### 5.1 The matrix

| Agent | Ph1 Plan & Draft | Ph2 Review & Revise | Ph3 Iterate & Converge | Ph4 Finalize & Close |
|---|---|---|---|---|
| **Planner** | Bootstrap ledger, orchestrate drafting, freeze P-stage declaration. | Orchestrate Evaluator/Generator handoff, fire `p-stage-checker` (drift-only), track named owners of ESCALATED findings, **carry `named_owner` into Ph3 entry per §3.2.1**. | Orchestrate iteration loop, write cumulative signoff rows, track `ph3_last_activity_at`, emit convergence-stable and staleness warnings, **enforce `transfer_rationale` non-emptiness on ownership transfers**, gate on signed terminal row. | Orchestrate MCR admission (including `[Ph3-STALE]` clearance and EG-7 re-admission), coordinate terminal-phase composition, **formalize Reflector-emitted plugin proposals into `plugin_update_proposals.md`** (sole gatekeeper), **emit override-inconsistency warning on EG-6 fires**. |
| **Evaluator** | **Dormant.** | Full first-pass review (seven-step judgment, deterministic full, grounding audit, abstract–body, contradictions, SAFEGUARD, Bacon, Sexton). | Re-review per iteration; re-engagement on unresolved findings plus fresh surfaces exposed by Generator revisions. | Terminal review: verify `submission_bundle/` against `main.md`, render-contract drift, external-verifier internalization. |
| **Generator** | Primary active: drafting from lit anchors. | Respond to findings: per-finding RESOLVED / ACKNOWLEDGED / ESCALATED (with named owner); no new substantive claims. | Iterative response; per-round self-verdict `Ph3-verdict: CONVERGING / CONTESTED / DIVERGING`; **propose ownership transfer with rationale when escalated finding moves domain (§3.2.1)**. | Final polish: assemble submission bundle, cover letter, response letter; no new substantive claims. |
| **Reflector** | **Lightweight:** grounding audit (Rule 1). | **Lightweight:** grounding integrity. | **Lightweight:** confirmation-failed history, drift, reflexivity. | **Full:** lessons extraction, Coupling A-revised reconciliation, Coupling B retrofit, Coupling C promotion, Coupling D ingest, skill-retirement proposals (R1–R5), skill-addition proposals (A1–A5, §5.3), tool-contract roundtrip. |

### 5.2 The Planner as gatekeeper

The Planner's Ph4 role is elevated at v0.7.0 to formal gatekeeper of Reflector output. Reflector-full emits *raw proposal candidates* — lessons, wiki-ingest records, skill proposals — into an internal draft buffer. The Planner reads this buffer and produces the user-facing `plugin_update_proposals.md` artefact after applying three filters: (a) proposals must cite the grounding evidence the Reflector produced; (b) proposals must name the skill or package affected; (c) proposals must declare the R- or A-code they invoke. Proposals do not float as Reflector-internal thoughts; they become formal engineering artefacts only after Planner formalization.

### 5.2a Round dispatch plan (v0.7.4, P-1)

The Planner's round-entry responsibilities at v0.7.4 include authoring an F6 `planner_dispatch_plan` artefact at Phase 0.6 of every round under invariant I-Planner-10 (`AGENT_CONTRACTS.md §2 Planner`). The artefact lives at `reviews/dispatch_plan_<cycle_id>.md`, conforms to `ARTEFACT_FRONTMATTER_SCHEMA.md §7a`, and is presented to the user as a blocking checkpoint — no downstream Evaluator, Generator, or Reflector dispatch fires until `user_approval_signature` is populated. The plan declares `sections_in_scope`, `dispatched_agents[]` (each with `agent`, `phase`, `model_allocation`, `scope`, `purpose`), `checks_scheduled[]`, and any `subagent_envelope[]` entries. The Planner's subsequent Phase 4.5 (model allocation) and Phase 4.6 (subagent envelope) become *consumers* of Phase 0.6's pre-authored plan rather than independent resolvers; plan drift between Phase 0.6 and execution is audited by Reflector Phase 2f at step 6.9 (R-Refl-DP-1 MAJOR, R-Refl-DP-2 BLOCKER, R-Refl-DP-3 BLOCKER). The F6 is strict-family, is NOT inherited under P-2 stability sub-mode, and does not itself consume iteration budget. See `agents/planner.md` Phase 0.6 for the authoring procedure.

### 5.3 Proposal and retirement criteria

v0.6.0's `SKILL_REGISTRY.md` defined R1–R5 as *retirement* criteria only:

- **R1 Superseded**
- **R2 Absorbed into pipeline**
- **R3 Pattern extinct**
- **R4 Eval regression**
- **R5 User directive**

v0.7.0 introduces the parallel **A1–A5 addition-criteria set** closing the v0.6.0 gap:

- **A1 Recurring pattern.** A workflow pattern has recurred across two or more rounds and at least two projects, per the Reflector's confirmation-failed history.
- **A2 Unoperationalized softgoal.** An existing softgoal (e.g., grounding, register, contradictions) lacks a dedicated check and the Evaluator repeatedly fires against it manually.
- **A3 External-verifier coverage gap.** A verifier class (1 / 1.5 / 2 / 3) is referenced but no skill currently exercises it.
- **A4 Coupling surface.** A cross-package coupling (e.g., Coupling E.2) is present but has no dedicated skill formalizing its data-flow contract.
- **A5 User directive.** The user has directly requested the capability.

Addition proposals at Ph4 cite one of A1–A5; retirement proposals cite one of R1–R5. This mirrors the severity discipline already used for findings. The A1–A5 set is a v0.7.0 proposal; `SKILL_REGISTRY.md` is updated to codify it alongside the existing R1–R5.

---

## 6. `phase_state.json` schema delta — v0.7.0

*Source: draft-5 §6.* Full normative schema lives in `references/phase_state_schema.md`; this section enumerates the canonical fields and invariants.

### 6.0 Explicit invariant lift

`phase_state_schema.md §1` (v0.6.0) states: "Top-level shape is fixed: no additional top-level keys are permitted." §2 (v0.6.0) states: "Every element of the `sections` array is an object with **exactly** the following ten fields (no extras permitted, no omissions tolerated — Planner validation rejects either)."

v0.7.0 **lifts both invariants simultaneously with the `schema_version` bump to `"0.7.0"`.** The new invariants are:

- **Top-level invariant (v0.7.0).** The object has *at most* the set of v0.6.0 top-level keys plus `{tier_vocabulary, milestone_assignment}`. Additional top-level keys remain rejected.
- **Section-level invariant (v0.7.0).** Every element of `sections` has *exactly* the v0.6.0 ten fields plus the v0.7.0 five-field extension listed in §6.2. **Fifteen fields total, no extras, no omissions.**

The sixteen-field `SectionStateObject` count (v0.8.0 widens from fifteen with `pre_mcr_deep_pass_completed` per `phase_state_schema.md` §2) is a deliberate design commitment. The Option A resolution of the `[Ph3-STALE]` representation (see §3.3.1) explicitly preserves this invariant: the staleness flag is computed from `ph3_last_activity_at` on each Planner pass rather than stored as a separate persisted boolean. The `TierEntryLogRow` and the two `ph3_convergence_signoff.md` row shapes are structured payloads *within* the existing `phase_entry_log` array and the existing signoff file, not new top-level or section-level fields; their required-field contracts are specified in §6.3a.

The validator (`scripts/phase_state_validate.py`) is updated to enforce the new invariants, rejecting both v0.6.0 shape (pre-migration) and v0.7.1+ shape (forward-incompatibility). The migration script (§6.4) is responsible for the shape change.

### 6.1 Top-level additions

```diff
 {
   "schema_version": "0.7.0",
   "manuscript_id":  "<project-slug>",
   "default_final_phase": "Ph1" | "Ph2" | "Ph3" | "Ph4",
   "fingerprint_mode":   "strict" | "tolerant" | "off",
   "terminal_tier_reached": false | true,
   "last_updated":          "<ISO-8601 UTC>",
+  "tier_vocabulary":       "lifecycle_v0.7",
+  "milestone_assignment":  {
+    "M1": "Ph1", "M2": "Ph1", "M3": "Ph1",
+    "M4a": "Ph2", "M4b": "Ph3", "M5": "Ph4"
+  },
   "sections": [ <SectionStateObject>, ... ]
 }
```

### 6.2 `SectionStateObject` additions

```diff
 {
   "heading_path": ["1. Introduction"],
-  "current_phase": "Ph1",     // enum: Ph1 / Ph2 / Ph3 / Ph4_ready / Ph4
+  "current_phase": "Ph1",     // enum: Ph1 / Ph2 / Ph3 / Ph3_converged / Ph4
   "last_approved_phase": null,
   "ceiling_locked": false,
   "section_ceiling_override": null,
   "iteration_count_at_current_phase": 0,
   "last_scope_fingerprint": "<sha256 hex>",
   "fingerprint_computed_at": "<ISO-8601 UTC>",
   "cumulative_drift_lines_since_approval": 0,
+  "phase_goal_declared": "produce a complete first draft...",
+  "phase_deliverable_path": "reviews/ph1_draft_completion.md",
+  "convergence_metric": null,
+  "ph1_pstage_declaration": "P2",
+  "ph3_last_activity_at": null,
   "phase_entry_log": [ <TierEntryLogRow>, ... ]
 }
```

The `milestone_scope` field proposed in earlier drafts is dropped because the `tier_vocabulary` top-level key plus the per-section `phase_goal_declared` together encode the same information more economically.

### 6.3 `TierEntryLogRow` trigger-enum additions

The v0.6.0 trigger enum (12 values) is preserved; v0.7.0 adds the following:

- `ph1_draft_completion_signed` — records the user's signed `ph1_draft_completion.md`.
- `ph2_review_completion_signed` — records the signed `ph2_review_completion.md`.
- `escalation_owner_transferred` — records a `transferred_to` event in `convergence_log.md` (§3.2.1).
- `escalation_named_owner_assigned` — records every ESCALATED-finding owner assignment at Ph2 / Ph3.
- `ph3_iteration_round` — records one iteration within the Ph3 unbounded loop.
- `ph3_convergence_signoff_row` — records one appended row in the cumulative `ph3_convergence_signoff.md` (not necessarily terminal).
- `ph3_stale_reengagement_signoff` — records a re-engagement row that clears `[Ph3-STALE]` (§3.3.1).
- `ph3_convergence_signoff_terminal` — records the terminal row bearing `is_terminal: true`, which flips `current_phase: Ph3 → Ph3_converged`.
- `mcr_admission` — records MCR admission to Ph4 (renamed from `lcr_admission`).
- `mcr_blocked_t3_stale` — records an MCR pause due to one or more stale sections (§3.3.1).
- `eg7_mcr_readmission_after_class_change` — records the Ph3-iteration-then-MCR-replay path for an EG-7 fire at Ph4 (§7).
- `eg1_ph4_downgrade_to_ph3` — records a Rule 1–7 grounding violation forcing a Ph4-→-Ph3 return (§7).
- `eg6_override_inconsistency_warning` — records the Planner's warning on an inconsistent `/run-phase-N` override target (§7).
- `m5_wiki_ingest` — records Coupling D ingestion at Ph4 close.
- `plugin_update_proposed_by_planner` — records Planner-formalized plugin proposals (not Reflector-raw).
- `v0_7_state_rename` — records the v0.6.0 → v0.7.0 migration rename `Ph4_ready → Ph3_converged` (§6.4 step 3).

**v0.7.4 additions (trigger 29 and trigger 30):**

- `ph3_iteration_round_manuscript` (trigger 29, P-7) — records **one manuscript-level Ph3 iteration that touches N sections**. Per-section monotonicity is preserved via one row per affected section, but all N rows share a single `cycle_id` in their `notes` field (e.g., `cycle_id:ph3_iter4_batch_2026-04-20`). The trigger replaces the cost-inefficient pattern of N independent `ph3_iteration_round` rows with N independent cycle_ids when a single revision directive actually touched N sections in one pass. Rows carrying this trigger must also carry `trigger_scope:manuscript` as a second notes-field pair so the Reflector Phase 2f boundary-write audit can distinguish manuscript-level rows from the legacy section-scoped `ph3_iteration_round` trigger. See §3.3.5 for the batching contract and §6.3a for the row-group integrity rule.
- `stability_mode_escalated_to_full_ph3` (trigger 30, P-2) — records the automatic escalation from a Ph3 **stability sub-mode** pass back to a full Ph3 round when the reduced-scope stability check surfaces a finding the sub-mode is not authorised to resolve. The row is written on the section whose stability pass failed; the `notes` field names the finding class that triggered escalation (typically a grounding-audit Rule 1–7a violation or a Check 8 BLOCKER). The escalated full-Ph3 round that follows consumes a normal `ph3_iteration_round` row; the escalation trigger itself is bookkeeping for the cost-accounting audit in Reflector Phase 2g. See the P-2 contract (implemented in `run-phase-3-stability` — Task #11) for the reduced-scope boundary.

### 6.3a Structured row schemas

Three structured row shapes are consumed by tooling across v0.7.0. Their full-schema contracts are specified here so the `phase_state_schema.md` rewrite, the Reflector-full Phase 2b ingest contract at Ph4, and `pre_phase_advance_check.py` all read against a stable shape. All fields are required unless flagged optional.

#### `TierEntryLogRow` (an element of the `SectionStateObject.phase_entry_log` array)

| Field | Type | Notes |
|---|---|---|
| `timestamp` | string (ISO-8601 UTC) | Monotonically non-decreasing across rows in the same array. |
| `trigger` | enum | One of the trigger values enumerated in §6.3. |
| `prev_phase` | enum \| null | One of `Ph1` / `Ph2` / `Ph3` / `Ph3_converged` / `Ph4`, or `null` for the initial row. |
| `new_phase` | enum \| null | Same enum; `null` when the trigger records a non-phase-changing event (e.g., `eg6_override_inconsistency_warning`). |
| `actor` | enum | One of `planner` / `evaluator` / `generator` / `reflector` / `user`. |
| `notes` | string (≤ 280 chars) | Optional. Free-text trace for the Reflector; validator bounds the length. |

#### `TerminalSignoffRow` (a row in `reviews/ph3_convergence_signoff.md`)

| Field | Type | Notes |
|---|---|---|
| `row_timestamp` | string (ISO-8601 UTC) | Appended-only. |
| `is_terminal` | boolean | `true` for a terminal row; mutually exclusive with `is_reengagement`. |
| `iteration_number` | integer | The Ph3-iteration count this row closes on. |
| `convergence_metric_value` | float | The `diff_lines_vs_previous_round / total_section_lines` value at this iteration (§3.3). Persisted for Reflector-full drift analysis. |
| `ph3_verdict` | enum | One of `CONVERGING` / `CONTESTED` / `DIVERGING` (Generator self-verdict grammar, §5.1; required on the terminal row only). |
| `user_signature` | string | User identifier at signoff time. |
| `user_signed_at` | string (ISO-8601 UTC) | Matches or follows `row_timestamp`. |
| `final_owner_state` | object | Snapshot of `convergence_log.md` ownership per still-`ESCALATED` finding at closure time: `{finding_id: current_owner, ...}`. Empty object if no ESCALATED findings remain. |
| `notes` | string (≤ 560 chars) | Optional. |

**Effect of appending a `TerminalSignoffRow`:** flips `current_phase: Ph3 → Ph3_converged`, writes a `ph3_convergence_signoff_terminal` trigger into `phase_entry_log`, and freezes `convergence_log.md` against further appends.

#### `ReengagementSignoffRow` (a row in `reviews/ph3_convergence_signoff.md`)

| Field | Type | Notes |
|---|---|---|
| `row_timestamp` | string (ISO-8601 UTC) | Appended-only. |
| `is_reengagement` | boolean | `true`. Mutually exclusive with `is_terminal`; a row carries exactly one of the two. |
| `cleared_stale_at` | string (ISO-8601 UTC) | The timestamp of the Planner pass that recorded `[Ph3-STALE] = true`. Retained as audit evidence that the re-engagement was not procedural. |
| `iteration_number` | integer | Carries the same value as the last prior row (re-engagement does not advance the iteration counter). |
| `user_signature` | string | User identifier at signoff time. |
| `user_signed_at` | string (ISO-8601 UTC) | Matches or follows `row_timestamp`. |
| `notes` | string (≤ 560 chars) | Optional. |

**Effect of appending a `ReengagementSignoffRow`:** updates the section's `ph3_last_activity_at` to `row_timestamp`, which mechanically drops the computed `[Ph3-STALE]` to `false` on the next Planner pass (Option A semantics, §3.3.1); writes a `ph3_stale_reengagement_signoff` trigger into `phase_entry_log`. Does **not** flip `current_phase`.

**Row-shape enforcement.** `pre_phase_advance_check.py` clause (g) at §7.3 (script-level) validates every row in `phase_entry_log` and in `ph3_convergence_signoff.md` against these schemas. Rows missing required fields, carrying disallowed field combinations (e.g., both `is_terminal: true` and `is_reengagement: true`), or violating length bounds fail with `E-ROW-SHAPE-VIOLATION`.

### 6.4 Migration semantics (`scripts/migrate_v060_to_v070.py [retired from tree]`)

Idempotent single-pass migration:

1. Bump `schema_version` from `0.6.0` to `0.7.0`.
2. Insert `tier_vocabulary: "lifecycle_v0.7"` and `milestone_assignment` with the default mapping from §4.2.
3. Translate `current_phase: "Ph4_ready"` → `"Ph3_converged"` in every section. Preserve historical semantics by writing a `phase_entry_log` row with trigger `v0_7_state_rename` noting the pre-migration state.
4. Populate `phase_goal_declared` and `phase_deliverable_path` per `current_phase` from the fixed lookup table derived from §§3.1–3.4.
5. Leave `convergence_metric: null` unless the section is at Ph3 (in which case emit a warning: "v0.6.0 Ph3 state has no convergence metric; re-run the Ph3 loop to populate").
6. Populate `ph1_pstage_declaration` from the manuscript classification if available; else `null` with a migration warning coded `W-PSTAGE-UNAVAILABLE`.
7. Leave `ph3_last_activity_at: null` — v0.6.0 did not track this field. Under the Option A (purely-computed) semantics specified in §3.3.1, a null `ph3_last_activity_at` short-circuits the staleness computation to `[Ph3-STALE] = false`; no separate `not_yet_evaluated` migration flag is required. The migration report nonetheless emits `W-Ph3-ACTIVITY-NULL` for every migrated Ph3 section so the Planner records the first post-migration activity timestamp on the next pass.
8. Archive the pre-migration file at `reviews/tier_state.v0.6.0.json`.
9. Emit `reviews/migration_report_v0.6_to_v0.7.md` listing every translated section and every warning raised.

A second run is a no-op (verified by `schema_version == "0.7.0"`).

**Migration test discipline.** Before release, the migration script is tested against deliberately corrupted inputs, including a v0.6.0 file where the pre-v0.7.0 exit artefacts (`ph1_draft_completion.md` etc.) cannot exist because they are v0.7.0 inventions. The script handles this as a *graceful cold-start* on the exit-artefact contract, not a hard failure. Specifically: on a migrating section, if a v0.7.0 exit artefact is absent *and* the section's `last_approved_phase` shows it previously cleared the phase, the script writes a *placeholder* exit artefact with a `migration_origin: v0.6.0` flag, permitting the v0.6.0 prior approval to be honored without fabricating content.

---

## 7. Escalation gates (EG-1 … EG-7)

*Source: draft-5 §8.3.* Gate semantics are defined canonically here; other files (`evaluator.md`, `AGENT_ORCHESTRATION.md`) name gates but do not redefine firing conditions.

| Gate | Firing condition | v0.7.0 behaviour |
|---|---|---|
| **EG-1** Grounding threat | Evaluator detects a Grounding Protocol Rule 1–7 violation | **Preserved.** Auto-escalates *into the Ph3 iteration loop* rather than to a "Ph3 review depth." **At Ph4 during submission prep, an EG-1 fire forces the section to drop to `current_phase: Ph3` for at least one iteration, with re-admission via MCR on the next pass** — the Ph4-→-Ph3 downgrade path is plan-originated. Logged via trigger `eg1_ph4_downgrade_to_ph3`. |
| **EG-2** Self-Ph1 verdict mismatch | (v0.6.0 only) | **Retired at v0.7.0.** The Self-Ph1 Verdict is retired; Confirmation Mode is retired; the entire triggering apparatus is removed. §11 item 4. |
| **EG-3** Cross-scope reference | A Ph2 finding cites a `location:` outside the containing section | **Fires into Ph3 iteration** as a new-round trigger appended to `convergence_log.md`, not a phase-up escalation. If fired at Ph2, the section still advances to Ph3 (as in v0.6.0) — the difference is that Ph3 is a loop to be entered, not a deeper review to be escalated to. |
| **EG-4** Contradiction surface | `check-contradictions` finds an unacknowledged conflict between co-invoked theoretical sources | **Fires into Ph3 iteration** as a new-round trigger (at Ph2 entry to Ph3 or at Ph3 iteration). Same semantics as EG-3. |
| **EG-5** Directive violation | Generator edit touches a `DO_NOT_DISTURB.md` passage | **Preserved as directive-violation escalation.** The target is the Ph3 iteration loop rather than a Ph3 depth-pass; on fire at Ph1, the section still promotes to Ph3 entry (this is unchanged behaviour — it was already a phase-jump in v0.6.0). At Ph4, a fire forces return to Ph3. |
| **EG-6** User override | User invokes `/run-phase-N` explicitly | **Preserved**, with a plan-originated extension: the Planner now also warns if the override target is inconsistent with the section's `current_phase` or `applicable_ceiling` (e.g., requesting `/run-phase-2` on a section already at `Ph3_converged`, or on a ceiling-locked Ph1 section). The warning is non-blocking — the override still applies — but it is logged via trigger `eg6_override_inconsistency_warning`. |
| **EG-7** Size-class change | Word-count threshold crosses a classification boundary | **Preserved, with the Ph4 target reinterpreted** as "drops the section to `current_phase: Ph3` for at least one iteration before re-running MCR" — the existing convergence record was written against a different review contract and cannot be reused against the new class. The fire still reports through `phase_notifications.yaml`; the Planner handles the Ph3-iteration-then-MCR-replay path. Logged via trigger `eg7_mcr_readmission_after_class_change`. |

The re-mapping reflects the lifecycle reality: v0.6.0's "escalate to Ph3" language was a depth-of-review jump; under v0.7.0, "Ph3" is a loop-entry event. EG-3 and EG-4 become iteration triggers within Ph3, which is a semantic demotion, not a retirement. EG-1 retains its bypass-the-ladder behaviour because grounding integrity is the one surface that cannot be stage-deferred. EG-6 and EG-7 acquire plan-originated lifecycle extensions.

---

## 8. Approval semantics

*Source: draft-5 §8.1 and v0.6.0 §6 (preserved with §6.4 phase-down broadening to §8.5 below).*

### 8.1 Advance rule (pseudocode)

```
on approval of section S at phase Ph:
    last_approved_phase(S) ← T
    ac ← applicable_ceiling(S)
    if T >= ac and ac < Ph4:
        current_phase(S) ← T
        ceiling_locked(S) ← true
        log `ceiling_locked` row
    else:
        if T == Ph3:
            current_phase(S) ← Ph3_converged
        else:
            current_phase(S) ← next_tier(T)
        ceiling_locked(S) ← false
    iteration_count_at_current_phase(S) ← 0
    cumulative_drift_lines_since_approval(S) ← 0
    log `user_approval` row
```

where:

- `applicable_ceiling(S) := min_by_tier(default_final_phase, section_ceiling_override(S))`
- `next_tier(Ph1) := Ph2`, `next_tier(Ph2) := Ph3`. `next_tier(Ph3)` resolves to `Ph3_converged` via the terminal signoff row on `ph3_convergence_signoff.md`, not via a flat advance.
- Phase ordering: `Ph1 < Ph2 < Ph3 < Ph4`. `Ph3_converged` is not a phase; it is a staging state atop Ph3, admissible to Ph4 via MCR (§9).

### 8.2 Rejection and defer

- **Rejection.** Writes a `user_rejection` row; `iteration_count_at_current_phase += 1`; `current_phase` unchanged. The Planner re-dispatches the Generator with the rejection findings. A per-phase soft cap of **5 consecutive rejections** at the same phase surfaces a Planner advisory suggesting the user reconsider scope or ceiling; the cap is not a hard block.
- **Defer.** User pauses the climb. Writes a `user_defer` row; `current_phase` unchanged. A subsequent `/review` invocation resumes at the deferred section.

### 8.3 Auto-chaining

Approval of a cycle **auto-invokes** the next cycle in two contexts:

1. **MCR climb** within the Manuscript Convergence Report (§9): each phase cycle's approval auto-invokes the next cycle in the declared sequence.
2. **Single-section climb** with `--chain`: if the user passed `/review --chain`, approval at phase Ph for section S auto-invokes `/review` at the next phase for the same section.

Outside these contexts, approval **mutates state** (advances the ledger) but does **not** auto-invoke the next cycle. The user must re-invoke `/review` explicitly.

### 8.4 Ph3 iteration-count semantics

Under the unbounded Ph3 loop, `iteration_count_at_current_phase` functions as the Ph3 iteration counter. It increments on every Generator re-dispatch within Ph3, resets only on the terminal signoff row's `current_phase` flip to `Ph3_converged`, and is never resettable via mid-Ph3 rejection.

### 8.5 Explicit phase-down

*Replaces v0.6.0 §6.4.* A user may explicitly phase-down a section via `/review --section S --phase-down` or by editing `classification.md` to set `section_ceiling_override` below `current_phase`. The Planner:

1. Sets `current_phase ← override` (or previous `last_approved_phase`, whichever is higher).
2. Sets `last_approved_phase ← override - 1` (if `override - 1` ≥ null; otherwise null).
3. Writes a `retraction` row with the explicit user action recorded.

If the override target is `Ph3` and the section is currently `Ph3_converged`, the phase-down writes `current_phase ← Ph3`, preserves `last_approved_phase`, and unfreezes `convergence_log.md` for further appends — the user re-enters the iteration loop.

Monotonicity is broken only by this path or by a `fingerprint_reset` (§8.6).

### 8.6 Fingerprint policy

Preserved from v0.6.0 unchanged in principle; the mode enum (`strict` / `tolerant` / `off`) and the `per_edit_threshold` / `cumulative_threshold` formulas are unchanged. One consequence changes at v0.7.0:

**Under Ph3's unbounded loop, `tolerant_drift_threshold` is demoted to a *warning threshold* rather than a forced re-review, because forcing re-review would conflict with the unbounded-loop contract.** The validator code path for `tolerant` mode at Ph3 is updated; failure code `W-Ph3-DRIFT-EXCEEDED-TOLERANT` is added to `scripts/phase_state_validate.py`'s v0.7.0 taxonomy.

The `cumulative_drift_lines_since_approval` counter *accumulates* across Ph3 iterations and resets *only* on the terminal signoff row (i.e., when `current_phase` flips to `Ph3_converged`). This preserves the drift defence across the unbounded loop while keeping the counter semantics compatible with the v0.6.0 fingerprint-mode enum.

### 8.7 Persistence contract and concurrency

Preserved from v0.6.0 §5.5 unchanged:

- **Atomic writes.** Every `phase_state.json` mutation uses the `phase_state.json.tmp` → `rename` pattern.
- **`last_updated` invariant.** Every mutation writes `last_updated` ≥ all `phase_entry_log` rows' timestamps written in the same session.
- **Concurrency.** Single-writer optimistic ledger with mtime + hash checks. Advisory lockfile (`reviews/.tier_state.lock`) is best-effort.
- **Reconciliation.** Divergent mtime + hash surfaces the `[CONCURRENCY-DETECTED]` prompt; no silent overwrite.

---

## 9. Manuscript Convergence Report (MCR — Ph4 admission gate)

*Source: draft-5 §§3.4, 8.4, Q-D.* Renamed from "Laggard Clearance Report" at v0.7.0 per Q-D.

### 9.1 Target phase

When `/run-phase-N` for N ≥ 3 or `/ship` is invoked and `phase_state.json` shows sections below the target phase, the Planner builds a **Manuscript Convergence Report (MCR)**. The MCR's target is **the maximum phase permitted by the project's applicable ceilings**, not unconditionally Ph4:

- `/ship` or `/run-phase-4` invoked and every section has `applicable_ceiling(S) == Ph4` → target = Ph4.
- `/ship` or `/run-phase-4` invoked and any section has `applicable_ceiling(S) < Ph4` → return error **before** building the plan: `"Ship target unavailable: §{S} has a sub-Ph4 ceiling. Raise the ceiling or run /run-phase-3 against section-group scope."`
- `/run-phase-3` invoked with laggards → target = Ph3; sections with `applicable_ceiling(S) < Ph3` are excluded with a note.

### 9.2 Structure (user-presented)

```
[MANUSCRIPT CONVERGENCE REPORT]

Target: {target_tier} on {scope: whole manuscript | section-group G}.
Applicable ceilings respected: {listed per section if non-uniform}.

Prerequisite: every in-scope section admitted at ({target_tier == Ph4 ? "Ph3_converged" : target_tier}).
Additional prerequisite (Ph4 target only): no section carries a computed [Ph3-STALE] = true.

Current ledger state (sections below target):

  §3 (theory)       current: Ph2       needs: Ph3 → terminal-signoff   est: 20 min  (reserve: +10 min)
  §4 (analysis)     current: Ph1       needs: Ph2 → Ph3 → terminal      est: 45 min  (reserve: +23 min)
  §5 (analysis)     current: Ph1       needs: Ph2 → Ph3 → terminal      est: 45 min  (reserve: +23 min)
  §7 (discussion)   current: Ph2       needs: Ph3 → terminal-signoff   est: 20 min  (reserve: +10 min)

Excluded from climb (ceiling-locked below target):
  (none in this example)

Sections blocked by [Ph3-STALE] (Ph4 target only):
  (none in this example; list populates with cleared_stale_at requirements)

Total climb sequence: 6 phase-cycles across 4 sections.
Nominal wall-clock: ~130 min (climb) + ~75 min (target phase) = ~205 min.
Iteration reserve (+50% per cycle): ~66 min climb + ~38 min target = ~104 min.
Total budget (nominal + reserve): ~309 min.

Plan:
  1. §3 Ph3 (section-group: theory)
  2. §4 Ph2 (section §4)
  3. §5 Ph2 (section §5)
  4. §4 + §5 Ph3 (section-group: analysis)
  5. §7 Ph3 (section-group: discussion)
  6. Whole manuscript {target_tier}

Approval semantics for this run:
  - Approving this convergence plan enrols the climb into auto-advance: each phase
    cycle's approval immediately auto-invokes the next cycle in the sequence.
  - Each cycle still presents a binary approval gate. Rejecting any cycle halts
    the climb and returns control to you.
  - You may cancel the climb mid-sequence with /cancel-climb; phase_state.json
    records the partial progress.
```

### 9.3 `[Ph3-STALE]` admission pause

MCR admission pauses with `E-MCR-BLOCKED-Ph3-STALE` if any section carries a computed `[Ph3-STALE] = true` at admission time. The block clears only when the affected section issues a *re-engagement signoff row* per §3.3.1, which refreshes its `ph3_last_activity_at` and mechanically drops the computed flag below threshold on the next Planner pass. The pause-and-re-engage requirement is plan-originated.

### 9.4 Ceiling-lock disjunction (amended admission rule)

The MCR admission rule at v0.7.0 is **amended** from the strict v0.6.0 §7.1 rule: a section is MCR-cleared if *either*

- `current_phase == Ph3_converged`, *or*
- (`ceiling_locked == true` AND `last_approved_phase == applicable_ceiling`).

The second clause **relaxes** the v0.6.0 hard-error rule. The relaxation is justified because without it, sections with `applicable_ceiling = Ph1` (or Ph2) can never satisfy MCR under the new terminal-phase vocabulary (since `Ph4_ready` no longer exists as an enum value and the ceiling-locked terminal artefact *is* the section's terminal state). The relaxation is plan-originated.

A section with `applicable_ceiling = Ph1` terminates on the signed `ph1_draft_completion.md`. The artefact *is* the terminal artefact for that section. No further phase advancement is possible; no Ph2, Ph3, or Ph4 exit artefacts are produced. `current_phase` remains `Ph1`, `last_approved_phase` is set to `Ph1`, `ceiling_locked: true`, and the section is included in MCR's "cleared at ceiling" tally at Ph4 admission time. Analogous semantics apply to sections with `applicable_ceiling = Ph2` or `applicable_ceiling = Ph3`.

### 9.5 EG-7 re-admission

When EG-7 (size-class change) fires at Ph4, the affected section drops to `current_phase: Ph3` for at least one iteration before re-running MCR. The drop-to-Ph3 choice (rather than re-MCR-without-iteration) is justified because the existing convergence record was written against a different review contract. This re-admission path is plan-originated. Logged via trigger `eg7_mcr_readmission_after_class_change`.

### 9.6 Approval paths

- **Approve** → `mcr_admission` row is written. The climb begins; subsequent cycle approvals auto-invoke the next cycle.
- **Reject** → no auto-invocation. User returns to an empty `/review` prompt to run cycles manually.
- **Modify** → user deselects laggards (temporarily defer a section, set a `section_ceiling_override` down to the section's `current_phase` to remove it from the clearance target, etc.). Deferrals are logged.

### 9.7 Iteration reserve

Every wall-clock estimate in the MCR carries a **+50 % per-cycle iteration reserve** surfaced explicitly. Rationale: one rejection per cycle is within the normal operating envelope; the reserve keeps users solvent on budget when iteration happens. The reserve is additive, not multiplicative across cycles (cycle-level iteration, not full-climb re-runs).

---

## 10. Rule 1 full-file reads at every phase (phase-gated digest exception retired at v0.7.4)

*Retired at v0.7.4.* The phase-gated (formerly tier-gated) Rule 1 digest exception that v0.7.0 carried forward at narrow Ph1 scope is **retired outright** at v0.7.4. Full-file reads are the universal grounding floor at every phase of the Lifecycle-Phase Ladder, at the T4R sibling ladder, and at every agent-dispatch path. No phase-conditioned shortcut exists.

**v0.7.4 contract.** At every phase — **Ph1 (Plan & Draft)**, **Ph2 (Review & Revise)**, **Ph3 (Iterate & Converge)**, **Ph4 (Finalize & Close)**, and **T4R (Letter, sibling ladder)** — an agent satisfying Rule 1 for a citation into package rule-files must read the source file. Rule-digest artefacts are not a legal substitute. `GROUNDING_PROTOCOL.md` Rule 1 carries the rule body; this file carries the phase-scope (universal).

**Rationale for the retirement.** The Ph1 exception was originally motivated by the cost of full-file reads during bounded-scope drafting; the v0.7.3 review-round telemetry on INF3006Y iter-7 surfaced a cost-overrun of a different character (ledger-write storm, re-read storm, orphan Ph3 on byte-stable manuscript), which the eight-part economic-efficiency package (P-1 through P-8) addresses directly. Retaining a Ph1 digest exception in addition to the P-6 session-state cache would be redundant instrumentation with no additional cost leverage. Retiring it closes a narrow grounding attack surface without adding round-scoped cost.

**Historical record (v0.7.0–v0.7.3).** The exception permitted an agent at Ph1 to satisfy Rule 1 for citations into package rule-files by reading the rule-digest for the current plugin version instead of the source file, subject to every condition enumerated in `GROUNDING_PROTOCOL.md` Rule 1, and further narrowed by an M2 literature-review carve-out (M2-classified Ph1 prose had to run full-file `grounding-audit` regardless). The Reflector's Phase 3a digest-integrity check at Ph4 verified that the exception had been applied only at Ph1 across the round's history.

**v0.7.4 consequence list.**

- `scripts/verify_rule_digest.py` is archived under `legacy/rule-digest-v060-retired/`; the release-gate Phase 0.67 no longer builds or verifies a rule digest.
- The Reflector's Phase 3a digest-integrity check is retired (§11 retirement ledger entry #9).
- Agent-prompt surfaces that previously documented the Ph1 digest-read shortcut are rewritten to state full-file reads at every phase (Task #8).
- The M2 carve-out is subsumed by the universal full-file rule and is no longer a named construct.
- Projects that previously relied on rule-digest reads at Ph1 experience a modest cost increase at Ph1 entry, offset by the P-6 session-state cache for within-round re-reads.

**Migration.** Absent-means-compliant: any existing project proceeding under v0.7.4 automatically reads source files at Ph1 because the digest-read path is no longer exercised. No migration artefact is required.

---

## 11. Retired constructs

*Source: draft-5 §10.* Enumerated here for audit clarity.

1. **Depth-of-review tier vocabulary** (v0.6.0) — replaced by lifecycle-stage vocabulary (§§3.1–3.4).
2. **Generator Self-Ph1 Verdict** (v0.6.0; CLEAN / SUSPECT / DIRTY) — subsumed by signed `ph1_draft_completion.md`. The Verdict row is dropped from the `manuscript/revision_log.md` template. Generator output at Ph1 is the signed deliverable, not a verdict grammar.
3. **Confirmation Mode at Ph2 entry** (v0.6.0) — subsumed by the signed exit-artefact gate. Ph2 entry is gated by a user-signed `ph1_draft_completion.md`, which is a stronger signal than any Generator self-report: the user has actively approved the Ph1 deliverable. The signed exit artefact subsumes Confirmation Mode's shortcut function. `run-phase-2` loses its Confirmation-Mode branching.
4. **Escalation gate EG-2** (v0.6.0; Self-Ph1 verdict mismatch) — retired because its triggering condition (the Self-Ph1 Verdict) is retired. EG-1 is **NOT** retired — it is preserved as an in-loop auto-escalation to Ph3 iteration with the additional Ph4-→-Ph3 downgrade path (§7).
5. **"Laggard Clearance Report" terminology** (v0.6.0) — renamed to "Manuscript Convergence Report" (§9, Q-D).
6. **`Ph4_ready` enum value of `current_phase`** (v0.6.0) — renamed to `Ph3_converged`. Migration handled in §6.4 step 3.
7. **v0.6.0 §9.2's Reflector-Ph4-only restriction** — reversed at v0.7.0. Reflector-lightweight runs at Ph1, Ph2, and Ph3; Reflector-full at Ph4. See §1 Reflector re-expansion note.
8. **Silent redefinition of M1–M5 without supersession** (v0.6.0 implicit) — replaced by the explicit supersession clause in §4.1.
9. **Rule 1 phase-gated (formerly tier-gated) digest exception** (v0.6.0–v0.7.3) — retired at v0.7.4 in favour of universal full-file reads at every phase; see §10.
10. **Reflector Phase 3a Digest Integrity** (v0.5.x–v0.7.3) — retired at v0.7.4 because the digest mechanism it audited is itself retired (see item 9).
11. **`scripts/verify_rule_digest.py`** (v0.5.x–v0.7.3) — archived at v0.7.4 under `legacy/rule-digest-v060-retired/`; the release-gate Phase 0.67 no longer builds or verifies a rule digest.
12. **`TIER_PROTOCOL.md` filename** (v0.6.0–v0.7.3) — renamed `PHASE_PROTOCOL.md` at v0.7.4; the legacy path ships as a forwarding copy with a one-line deprecation banner through the v0.7.4 minor and is removed at v0.7.5 RC.
13. **Top-level field names under the tier taxonomy** (v0.6.0–v0.7.3) — renamed under the v0.7.4 Tier → Phase rename: `current_tier` → `current_phase`; `tier_goal_declared` → `phase_goal_declared`; `tier_deliverable_path` → `phase_deliverable_path`; `tier_entry_log` → `phase_entry_log`; `t1_pstage_declaration` → `ph1_pstage_declaration`; `t3_last_activity_at` → `ph3_last_activity_at`; `default_final_tier` → `default_final_phase`.
14. **Six-field log-row contract** (v0.6.0–v0.7.3) — widened to seven fields at v0.7.4, adding absent-means-null `model_used` for capability-inversion auditing (see Ph.D. Research CLAUDE.md §12.9).
9. **The v0.6.0 §7.1 strict "every section at terminal-convergence" MCR admission rule** — relaxed by the disjunctive ceiling-lock clause in §9.4 *and* extended by the `[Ph3-STALE]` admission-pause clause in §3.3.1 / §9.3 (both plan-originated).
10. **Depth-of-review framing of escalations "to Ph3"** (v0.6.0 §4) — demoted to iteration-entry triggers within Ph3's loop. EG-3 and EG-4 become new-round triggers, not phase-up escalations (§7).
11. **T3R "response-letter" label** (v0.6.0 §2.5) — renamed to T4R (§3.5).

---

## 12. Migration from v0.6.0

*Source: draft-5 §6.4.* Cross-reference: `scripts/migrate_v060_to_v070.py [retired from tree]`.

### 12.1 Project-level migration

Per project under `Ph.D. Research/` (or equivalent portfolio root):

1. **Detect migration necessity.** Read `reviews/phase_state.json`; if `schema_version == "0.7.0"` → no-op (idempotent second-run case). If `schema_version == "0.6.0"` → proceed. Any other version → migration error; run `migrate_v055_to_v060.py` first.
2. **Bump `schema_version`** from `"0.6.0"` to `"0.7.0"`.
3. **Insert `tier_vocabulary: "lifecycle_v0.7"` and `milestone_assignment`** at the top level per the default mapping in §4.2.
4. **Translate `current_phase: "Ph4_ready" → "Ph3_converged"`** in every section. Preserve historical semantics by writing a `phase_entry_log` row with trigger `v0_7_state_rename`.
5. **Populate the five new per-section fields** per §6.2:
   - `phase_goal_declared` — from the fixed lookup table derived from §§3.1–3.4 keyed by `current_phase`.
   - `phase_deliverable_path` — same table.
   - `convergence_metric` — `null` unless `current_phase == Ph3`, in which case emit warning "v0.6.0 Ph3 state has no convergence metric; re-run the Ph3 loop to populate."
   - `ph1_pstage_declaration` — from `reviews/classification.md` if available; else `null` with warning `W-PSTAGE-UNAVAILABLE`.
   - `ph3_last_activity_at` — `null`. Emit `W-Ph3-ACTIVITY-NULL` for every migrated Ph3 section.
6. **Exit-artefact cold-start.** On a migrating section, if a v0.7.0 exit artefact is absent *and* the section's `last_approved_phase` shows it previously cleared the phase, the script writes a *placeholder* exit artefact with a `migration_origin: v0.6.0` flag, permitting the v0.6.0 prior approval to be honored without fabricating content.
7. **Archive the pre-migration file** at `reviews/tier_state.v0.6.0.json`.
8. **Emit `reviews/migration_report_v0.6_to_v0.7.md`** listing every translated section and every warning raised.
9. **Preserve v0.6.0 artefacts.** `reviews/tier_state.v0.6.0.json` is retained in the repository; the Reflector's Ph4 digest-integrity audit reads both the migration report and the archived v0.6.0 state to verify the rename chain.

### 12.2 Compatibility envelope

v0.7.0 does **not** read v0.5.5 `tier_decisions_log.md` or v0.5.5 Marshal pre/post-flight artefacts at runtime; v0.6.0's migration handled those. The v0.7.0 migration script reads v0.6.0 `phase_state.json` solely to produce the v0.7.0 file.

v0.6.0 projects that want to stay on v0.6.0 continue to work unchanged; v0.7.0 lives in `research-writing-harness-claude-v0.7.0/` and does not interfere with `research-writing-harness-claude-v0.6.0/`.

Migration is **one-way.** Rollback to v0.6.0 requires the archived `reviews/tier_state.v0.6.0.json`; there is no automated v0.7.0 → v0.6.0 downgrade.

---

## 13. Success metrics

*Source: draft-5 §12 and v0.6.0 §11.* These are the operational definitions the Reflector audits at Ph4 close.

1. **Lifecycle coherence.** Each phase's exit artefact (`ph1_draft_completion.md`, `ph2_review_completion.md`, `ph3_convergence_signoff.md` terminal row, `ph4_ship_signoff.md`) exists and is user-signed before the next phase's admission fires. The Reflector's Phase 2b audit verifies this chain.
2. **Invariant preservation.** Top-level keys conform to §6.0's amended invariant; every `SectionStateObject` is exactly sixteen fields at v0.8.0 (fifteen at v0.7.0–v0.7.4 before `pre_mcr_deep_pass_completed`; see `phase_state_schema.md` §2). The validator's `E-INVARIANT-VIOLATION-V07` code surfaces any violation.
3. **Grounding integrity preserved (modulo §10 simplification).** Grounding Protocol Rules 1–7 fire unchanged except that the Rule 1 exception applies at Ph1 only with the M2 carve-out. Reflector's Phase 3a digest-integrity check passes on every Ph4 close.
4. **Approval gate honoured (auditable).** For every `user_approval` row, a preceding explicit user action is present in the log within the same session. At Ph3, the terminal signoff row is the preceding action; at Ph2 and Ph1, the signed exit artefact is the preceding action.
5. **Fingerprint mode honoured (mode-parameterized).**
   - `strict`: zero silent re-basings. Every mismatch produces a `fingerprint_reset` row.
   - `tolerant` (default): silent re-basings occur only when per-edit < `per_edit_threshold`, no citations introduced, and cumulative + diff < `cumulative_threshold`. At Ph3, `tolerant_drift_threshold` exceedance produces `W-Ph3-DRIFT-EXCEEDED-TOLERANT` (warning, not demotion).
   - `off`: no resets; `fingerprint_drift_advisory` rows only.
6. **Concurrency contract honoured.** No `phase_state.json` overwrite occurs against a divergent mtime + hash without explicit user resolution via the §8.7 prompt.
7. **Linear-Accountability defence honoured.** Every `ESCALATED` finding has, at any point in time, exactly one named owner. Every ownership transfer carries a non-empty `transfer_rationale`. `E-OWNERSHIP-TRANSFER-WITHOUT-RATIONALE` fires on violation.
8. **Workflow Failure-Point defence honoured.** No Ph4 admission proceeds while any section carries a computed `[Ph3-STALE] = true`. `E-MCR-BLOCKED-Ph3-STALE` fires on violation.
9. **Row-shape contract honoured.** Every row in `phase_entry_log` and every row in `ph3_convergence_signoff.md` conforms to the §6.3a schemas. `E-ROW-SHAPE-VIOLATION` fires on violation.
10. **Reflector re-expansion productive.** Reflector-lightweight at Ph1/Ph2/Ph3 fires zero false-positive blocks across the round. (Soft metric; Reflector-full audits the lightweight's log at Ph4.)

---

## 14. Invocation entry points

The seven first-class commands that route through this protocol are defined in `ROUTING_SPINE.md §2`:

- `/review` — **default entry.** Planner-resident smart dispatch; reads `phase_state.json`; advances per §8.1 or triggers the MCR per §9.
- `/run-phase-1`, `/run-phase-2`, `/run-phase-3`, `/run-phase-4` — **explicit phase entry** (EG-6 override). Logs `override_applied`; the Planner additionally logs `eg6_override_inconsistency_warning` if the target is inconsistent with the section's current state (§7).
- `/ship` — alias for `/run-phase-4` with extra validation that every section has `applicable_ceiling(S) == Ph4`.
- `/review-letter` — **T4R sibling ladder entry.** Invokes `response-letter-review` on a response-letter document.
- `/cancel-climb` — **mid-climb escape.** Writes `laggard_clearance_cancelled` (name preserved for audit continuity across the LCR→MCR rename); halts auto-advance at the next cycle boundary.
- `/raise-ceiling` — **per-section ceiling raise.** Writes `ceiling_raised`; unlocks `ceiling_locked` if set.

`/review --subsection` overrides the default top-level section resolution for a specific invocation.

`/review --chain` enrols a single section into auto-advance mode (cycle-to-cycle auto-invocation within one section).

---

## 15. Appendix — inference rules and open calibration residuals

### 15.1 Section-group inference

When `classification.md` has no `section_groups:` field, the Planner infers from heading patterns:

- Headings matching `/^(introduction|related work|background)/i` → group `intro`.
- Headings matching `/^(theory|conceptual|framework|model)/i` → group `theory`.
- Headings matching `/^(methods?|analysis|results?|findings?|case)/i` → group `analysis`.
- Headings matching `/^(discussion|conclusion|implications?|future work)/i` → group `discussion`.
- Unrecognized headings → own single-section group with a `# inferred unmatched` advisory.

The inferred grouping is written back to `classification.md` with a `# inferred` comment and surfaced to the user at next `/review`.

### 15.2 Plan-originated constants (reproduced from draft-5 §11)

| Constant | Default | Section | Notes |
|---|---|---|---|
| `stability_threshold` | 0.01 | §3.3 | Configurable per project via `classification.md`. |
| `ph3_staleness_budget` | 90 days | §3.3 | Configurable per project; default is deliberately generous. |
| `transfer_rationale` max length | 280 chars | §3.2.1 | Hard-coded in validator; not configurable. |
| `TerminalSignoffRow.notes` max length | 560 chars | §6.3a | Hard-coded in validator. |
| `ReengagementSignoffRow.notes` max length | 560 chars | §6.3a | Hard-coded in validator. |
| `TierEntryLogRow.notes` max length | 280 chars | §6.3a | Hard-coded in validator. |
| MCR iteration reserve | +50% per cycle | §9.7 | Preserved from v0.6.0 §7.5. |
| Soft rejection cap | 5 consecutive | §8.2 | Preserved from v0.6.0 §6.2. |

### 15.3 Open calibration residuals

- **R-01.** Fingerprint thresholds (`max(3, 5 %)` per-edit, `max(10, 15 %)` cumulative) are heuristic. Formal calibration is forward work.
- **R-02.** The 90-day `ph3_staleness_budget` is plan-originated and not yet calibrated against observed Ph3 iteration cadence across multiple projects.
- **R-03.** The `stability_threshold = 0.01` for `[CONVERGENCE-STABLE]` advisory is plan-originated and not yet calibrated.
- **R-04.** The `diff_lines_vs_previous_round / total_section_lines` convergence-metric formula is plan-originated. Alternatives — Levenshtein-distance ratio, semantic-diff via embedding cosine, manual user-scored convergence rating — remain candidate replacements if telemetry rejects the line-diff formula.

These do **not** block the v0.7.0 release; they are tracked as forward work.

---

*Normative status.* This file is the single source of truth for phase semantics at v0.7.4. Other package files (`AGENT_ORCHESTRATION.md`, `REVIEW_ORCHESTRATION.md`, `GROUNDING_PROTOCOL.md`, `SKILL_REGISTRY.md`, `ROUTING_SPINE.md`, the four `run-phase-N` skills) name and apply phase concepts but do not redefine them. Any conflict between this file and another package file is resolved in favour of this file unless the other file is explicitly `GROUNDING_PROTOCOL.md` (which sits outside the precedence ladder; see project CLAUDE.md §5).

*Grounding trail.* Every section above derives from `TIER_REDESIGN_v0.7-draft-5.md` (for the lifecycle-reframe substrate) and from the v0.7.4 economic-efficiency proposal bundle (for the Tier → Phase rename and the P-1 through P-8 additions): §1 ← draft-5 §§1, 2.2, 10 + v0.7.4 supersession clause; §2 ← draft-5 §2; §3 ← draft-5 §3 (with §§3.2.1, 3.3.1 as the plan-originated mandatory safety constraints; the v0.7.0 §3.1.1 i\* structural-completeness contract was retired at v0.11.0 with the SD/SR machinery cut); §4 ← draft-5 §4; §5 ← draft-5 §5; §6 ← draft-5 §6 (including §6.3a row schemas, widened to seven fields at v0.7.4 with `model_used` per Ph.D. Research CLAUDE.md §12.9); §7 ← draft-5 §8.3; §8 ← draft-5 §8.1 and v0.6.0 §6 (preserved with phase-down broadening); §9 ← draft-5 §§3.4, 8.4, Q-D; §10 ← v0.7.4 retirement (the draft-5 §§3.1, 9 Q-E exception is retired outright at v0.7.4); §11 ← draft-5 §10 + v0.7.4 retirement items 9–14; §12 ← draft-5 §6.4; §13 ← draft-5 §12 + v0.6.0 §11; §14 ← draft-5 §14 (inferred from v0.6.0 §12 with renaming); §15 ← draft-5 §11 (plan-originated constants table inferred from the narrative).

*Last updated.* 2026-04-21 — v0.7.4 rename pass. Renamed from `TIER_PROTOCOL.md` under the cross-cutting Tier → Phase terminology rename; retired §10's phase-gated digest exception in favour of universal full-file reads at every phase; retired Reflector Phase 3a Digest Integrity; extended §11 retirement ledger with items 9–14; added the v0.7.4 supersession clause at the top covering the lifecycle-phase ladder rename, the 15-field `SectionStateObject` field renames, the 6 → 7 log-row widening with absent-means-null `model_used`, the 28 → 30 trigger enum extension (trigger 29 `ph3_iteration_round_manuscript` per P-7, trigger 30 `stability_mode_escalated_to_full_ph3` per P-2), the `eg1_t4_downgrade_to_t3` → `eg1_ph4_downgrade_to_ph3` trigger rename, the I-SubAgent-1 invariant, and the eight economic-efficiency proposals P-1 through P-8. Previous: 2026-04-19 — Phase 1 of v0.7.0 rollout. Supersedes the v0.6.0 `TIER_PROTOCOL.md` as the normative source.
