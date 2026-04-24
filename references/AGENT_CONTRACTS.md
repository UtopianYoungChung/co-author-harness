# AGENT_CONTRACTS — Per-Agent I/O Contracts

**Purpose.** This file sharpens the four-agent role definitions by stating, for each agent, the declarative contract it honors: **preconditions** (what must be true to invoke), **inputs** (files the agent reads), **outputs** (files the agent writes), **invariants** (properties the agent promises not to violate), and **done criteria** (predicates that certify the agent's task is complete). It is deliberately terse and mechanical; the prose-level operating instructions remain in `agents/<role>.md`.

**Why contracts.** `AGENT_ORCHESTRATION.md` §4 already states read/write permissions. Contracts extend that with *functional obligations* — not just "what the agent can touch" but "what the agent owes the system." This is the Agent-Oriented Requirements Engineering (AORE) move: treating each agent as an autonomous party whose behaviour is bounded by an explicit protocol rather than implicit convention. The gstack analogue is the per-skill `SKILL.md` contract (inputs, outputs, exit criteria); here that pattern is pulled up to the agent level.

**Design influence — autoresearch scope budgets.** The autoresearch project (Karpathy, 2025) demonstrates that constraining each autonomous agent dispatch to a *fixed scope budget* prevents runaway experiments and makes results comparable across iterations. The contracts below incorporate this principle: each agent has a declared scope ceiling per dispatch. The ceiling is advisory (agents may exceed it with declared justification) but the Reflector audits overruns.

**Precedence.** On any conflict between this file and an `agents/<role>.md` prompt, the contract wins on *obligations* (what must be done) and the prompt wins on *method* (how to do it).

---

## 1. Planner Contract

**Role metaphor.** Session quarterback and phase-dispatcher. Does not write prose. Does not evaluate prose. Decides *what happens next* and *who does it*.

**Preconditions for invocation.**
- Project directory exists (or the user has just requested bootstrapping, in which case Planner's first act is to dispatch `PROJECT_BOOTSTRAP.md`).
- At least one of: user utterance, prior round's reflection report, or outstanding `revision_plan.md`.

**Inputs (read).**
- User utterance (current conversation).
- `round_program.md` if present (the user-authored control file for this round — see `AGENT_ORCHESTRATION.md` §8).
- `ROUTING_SPINE.md` §2 (dispatch table) and §3 (exit gates, including primary indicators).
- `reviews/classification.md` if present.
- `research_notes/directives.md` if present.
- Prior `reviews/reflection_report.md` if a prior round exists.

**Outputs (write).**
- `reviews/classification.md` (create or update).
- `reviews/revision_plan.md` (create or update, prioritized). During re-check mode, the Planner appends a **retain/revert addendum** to this file, categorizing each Generator change as RETAIN, REVERT, or PARTIAL per the Retain/Revert Protocol (`AGENT_ORCHESTRATION.md` §7).
- Dispatch instructions to other agents (via Agent tool or parent-session handoff).

**Invariants.**
- I-Planner-1: Never writes to `manuscript/*`.
- I-Planner-2: Never writes to `reviews/step_findings/*` or `reviews/consolidated_findings_report.md`.
- I-Planner-3: Every agent dispatch declares (a) the phase per `ROUTING_SPINE.md`, (b) the exit gate, (c) the entry artifact.
- I-Planner-4: Every user checkpoint names the current phase and the next-expected phase.
- I-Planner-5 (v0.7.3): Resolves the Claude model each dispatched subagent runs on from `MODEL_ALLOCATION.md §2`, passes the resolved string as the Agent tool's `model` parameter, and records the dispatch in `reviews/phase_state.json` `phase_entry_log[].notes` as `model_dispatch:{agent}:={model}` (or `model_override:{agent}-{tier}:={model}` under an active project directive). Refuses any round that would produce a capability inversion (Evaluator below Generator on `{Haiku 4.5} ≺ {Sonnet 4.6} ≺ {Opus 4.7}`) with `E-MA-CAPABILITY-INVERSION`. No per-agent frontmatter `model:` field is authoritative; if present on any agent definition, it is ignored in favour of the `MODEL_ALLOCATION.md` lookup.
- I-Planner-6 (v0.7.4): When the Planner delegates a Check 8 aggregation, a grounding-audit probe, or a deterministic-counter pass to a subagent (via the Agent tool under an explicit `subagent_type`), invariants I-SubAgent-1..3 of §4.5 apply unconditionally. The Planner records the dispatch envelope in its consolidated-findings artefact (F5 frontmatter optional field `dispatch_plan_reference` plus an inline envelope block in the prose body), cites the subagent's own artefact by path, and does not re-adjudicate the returned verdict. A delegation without an envelope is a contract violation even when the verdict itself is correct.
- I-Planner-7 (v0.7.4, P-6): The Planner maintains a hash-keyed in-memory session-state cache over `reviews/phase_state.json`, `reviews/classification.md`, and `research_notes/directives.md` for the duration of a single round. On first read of each file within a round, the Planner records `sha256(file_bytes)` as the cache key and stores the parsed content; subsequent reads within the same round return the cached parse without re-opening the file, *provided* the key matches. The cache is invalidated unconditionally on any Planner write to the keyed file (write-through, not write-back), on round close, on a user-initiated file edit signalled by a stale cache-key match-check at round entry, and on any dispatch that the Planner's own Phase 4.6 envelope names as touching one of the three files. The cache is scoped per-round — it never crosses a user-checkpoint boundary that closes a round, and it is never persisted across sessions. Reflector Phase 2f files `R-Refl-Cache-1` **MAJOR** if a round's F5 artefact's `grounding_basis` lists a file path whose cache-key-at-end-of-round does not match the key recorded at round entry without an intervening write-through (stale read), and `R-Refl-Cache-2` **MINOR** if the round's log-row count for file reads exceeds the round's distinct-file count by a factor implausible under a correctly-invalidated cache (a re-read storm). The invariant exists to close the ~18% overrun attributed to re-read storms on INF3006Y iter-7 (n=1; see Ph.D.-root CLAUDE.md §12.10 for the evidentiary caveat).
- I-Planner-8 (v0.7.4, P-7): The Planner is the sole writer of Ph3-iteration ledger rows and is bound to the manuscript-level batching contract at `PHASE_PROTOCOL.md §3.3.5`. When a single Generator dispatch touches N ≥ 2 sections under one revision directive, the Planner emits N rows — one per affected section — all carrying `trigger: ph3_iteration_round_manuscript`, `trigger_scope:manuscript` in notes, and a single shared `cycle_id` of shape `ph3_iter<M>_batch_<YYYY-MM-DD>` where `<M>` is the manuscript-level iteration index. The Planner enforces `cycle_id` uniqueness across the manuscript's lifetime by scanning prior values via the session-state cache (I-Planner-7) before the batch write; a collision blocks the write with failure code `E-P7-CYCLEID-COLLISION` until a fresh `<M>` resolves it. Single-section iterations (N = 1) continue to use the legacy `ph3_iteration_round` trigger. A corresponding single row is appended to `reviews/convergence_journal.jsonl` per batch; the many-to-one relationship between section rows and the journal row is the audit surface Reflector Phase 2f queries under `R-Refl-Batch-1`..`R-Refl-Batch-4`. The invariant exists to close the ~9% overrun attributed to per-section iteration-row multiplication on INF3006Y iter-7 (n=1; see Ph.D.-root CLAUDE.md §12.10 for the evidentiary caveat).
- I-Planner-9 (v0.7.4, P-8; v0.8.0 scalar read): The Planner is bound to the ceiling-lock termination-ranking contract at `PHASE_PROTOCOL.md §3.3.6`. At every Ph3 iteration boundary in Phase 5.5, the Planner evaluates each in-scope section against the two-part tension-detection rule (unresolved BORDERLINE advisory AND two consecutive iterations within the ±0.01 band around `stability_threshold` on the section's **line-diff scalar** — read `legacy_scalar` when `convergence_metric` is the v0.8.0 object shape per §3.3.6; otherwise use the scalar field); for every tension-state section, it computes `distance_to_ceiling = abs(line_diff_scalar − stability_threshold)` and emits `reviews/ceiling_lock_proposal_<YYYY-MM-DD>.md` under the F5 frontmatter family (P-3) with the optional field `ceiling_lock_detected: true`. The proposal ranks candidate sections by ascending distance-to-ceiling, ties resolving on descending `iteration_count_at_current_phase`. **v0.8.0.** The F5 artefact carries `menu_items_presented` where applicable and surfaces `/ph3-terminate` beside Option C when `[CONVERGENCE-STABLE]` and tension overlap, per `agents/planner.md` Phase 5.5 and `references/phase_notifications.yaml` → `ph3_loop`. Presentation is user-gated: on Option C approval the Planner sets `ceiling_locked(S) ← true`, appends a `TerminalSignoffRow` carrying `[CEILING-LOCK-STABLE]` in `notes`, writes a corresponding `user_approved_ph3_convergence_signoff` row to `phase_entry_log[]` (no new trigger added at v0.7.4 for P-8), and flips `current_phase: Ph3 → Ph3_converged`; on Option I approval the Planner appends a normal `ph3_iteration_round` (or P-7 batched) row and re-dispatches. The Planner MUST NOT set `ceiling_locked(S) ← true` at Ph3 absent an approved ceiling-lock proposal artefact — silent ceiling-lock escalation is the failure mode Reflector Phase 2f `R-Refl-Ceil-1` BLOCKER closes. The Planner MUST NOT emit a ceiling-lock proposal absent the tension-detection rule being satisfied — unjustified proposals waste the user's attention and are `R-Refl-Ceil-2` MAJOR. The invariant exists to close the ~7% overrun attributed to budget-on-BORDERLINE iteration on INF3006Y iter-7 (n=1; see Ph.D.-root CLAUDE.md §12.10 for the evidentiary caveat).
- I-Planner-10 (v0.7.4, P-1): The Planner is bound to the round-dispatch-plan contract and is the sole writer of `reviews/dispatch_plan_<cycle_id>.md` (F6 frontmatter family per `ARTEFACT_FRONTMATTER_SCHEMA.md §7a`). On Phase 0.6 of every round — after the session-state cache of Phase 0.5 (I-Planner-7) is warm and before the model-allocation resolution of Phase 4.5 (I-Planner-5) consumes it — the Planner authors an F6 artefact that declares `sections_in_scope`, the full `dispatched_agents[]` list (each entry carrying `agent`, `phase`, `model_allocation`, `scope`, and a ≤140-char `purpose`), and the `checks_scheduled[]` envelope. **v0.8.0 (§7a.2).** When any dispatched row runs at `phase: Ph3`, the Planner also authors the optional profile quartet — `check_profile`, `structural_delta_flag`, `parallel_dispatch`, `threshold_version` — per `ARTEFACT_FRONTMATTER_SCHEMA.md §7a.2` / §7a.3 defaults, so downstream Evaluator / Generator / journal consumers read a single approved envelope. The Planner presents the plan to the user as a blocking checkpoint and MUST NOT dispatch any downstream agent (Evaluator, Generator, Reflector) until the F6's `user_approval_signature` block is populated with `approved_at`, `approved_by`, and `modifications_recorded`. User-initiated modifications to the plan are re-emitted as a fresh F6 artefact whose `user_approval_signature.modifications_recorded: true`; the superseded artefact is NOT deleted — both persist in the audit trail. The Planner's subsequent Phase 4.5 (model allocation) and Phase 4.6 (subagent envelope) no longer *resolve* dispatch from `MODEL_ALLOCATION.md §2` *de novo* — they *consume* the values pre-authored in Phase 0.6's F6 and pass them into dispatch unchanged. The Planner MUST NOT dispatch an agent / model / phase combination that does not appear in the approved F6 — such a divergence is Reflector Phase 2f `R-Refl-DP-1` MAJOR (plan drift). A round that produces F1 / F2 / F3 / F5 artefacts without a corresponding F6 present at `reviews/dispatch_plan_<cycle_id>.md` is `R-Refl-DP-2` BLOCKER (missing plan). A round whose downstream artefacts cite a `dispatch_plan_reference` whose target F6 lacks a populated `user_approval_signature` is `R-Refl-DP-3` BLOCKER (unapproved plan). The invariant exists to close the cost-opacity failure mode observed when rounds dispatched subagents under implicit allocation — the user saw the bill after the round closed, not before it began.
- I-Planner-11 (v0.8.0, P-16): The Planner owns **ceiling-aware iteration budget surfacing** at the user checkpoint: on Phase 0.6 (`agents/planner.md`) the Planner MUST include, for every in-scope section at `current_phase: Ph3` with `ceiling_locked: false`, iteration telemetry (`iteration_count_at_current_phase`, `applicable_ceiling`), the `PHASE_PROTOCOL.md §8.4` soft advisory at five consecutive rejections at the same phase, and — when the round touches MCR or Ph4 climb planning — the `PHASE_PROTOCOL.md §9.7` +50% per-cycle iteration reserve on wall-clock estimates. When `ceiling_lock_anticipated: true` or P-8 tension is pending, the Planner MUST contrast **`/ph3-terminate`** (normal `[CONVERGENCE-STABLE]` terminal path) with **Option C** (ceiling-lock). On Phase 6 MCR assembly, the Planner MUST list sections with `applicable_ceiling(S) == Ph4` and `pre_mcr_deep_pass_completed(S) != true` (absent as false) and prescribe the `check_profile: deep` remediation path per `phase_state_schema.md §2.1` / `agents/planner.md` Phase 6. This invariant is the normative hook for the prose landed at P2.6 in `agents/planner.md`; executable refusal `E-MCR-PRE-DEEP-PASS-REQUIRED` remains documented at `pre_phase_advance_check.py` clause (f) when that script ships on the workspace.

**Done criteria.**
- Classification file is current (matches the manuscript state).
- Revision plan's top action is un-ambiguous and single-agent-dispatchable.
- User has been presented with the plan and has approved, modified, or rejected.

**Scope budget per dispatch.**
- Maximum 1 classification + 1 revision plan per dispatch.
- If the Planner determines that the scope of work exceeds one round (e.g., the manuscript needs structural revision AND line edits), it must split into multiple rounds and present the multi-round plan to the user.
- If `round_program.md` constrains the focus (e.g., "this round: fix the Introduction only"), the Planner must not dispatch agents on out-of-scope work.

**Failure modes and recovery.**
- *Mis-classification.* The Evaluator's findings diverge sharply from the plan → Planner re-classifies and re-issues the plan; Reflector records the divergence.
- *Over-dispatch.* Planner dispatches Generator before Review is complete → invariant I-Planner-3 flags this; Planner retracts and reorders.

---

## 2. Evaluator Contract

**Role metaphor.** Independent reviewer. Treats the manuscript as unfamiliar text. Does not write prose. Does not know how any given passage came to be the way it is, and does not care; only reads what is there.

**Preconditions for invocation.**
- An artifact of the correct type exists at the expected path (memo for M1 review, references for M2, outline for M3, `main.md` for M4–M5).
- `reviews/classification.md` exists (dispatched by Planner) OR Evaluator is invoked in test-only mode against `DETERMINISTIC_CHECKS.md` / `SAFEGUARD_LAYER.md`.

**Inputs (read).**
- The target artifact.
- `REVIEW_ORCHESTRATION.md` + the component files it references for the applicable phase.
- `DETERMINISTIC_CHECKS.md`, `SAFEGUARD_LAYER.md`, `DRIFT_CHECK.md`, `REFLEXIVITY_CHECK.md`, `EXTERNAL_VERIFIERS.md` as dictated by phase (Review, Test, Ship).
- `reviews/DO_NOT_DISTURB.md` (to respect frozen rules).
- `research_notes/directives.md` (to respect author overrides).

**Outputs (write).**
- `reviews/step_0a_deterministic.md` (Test phase).
- `reviews/step_findings/step_N_*.md` for N ∈ {1…7} (Review phase).
- `reviews/consolidated_findings_report.md`.
- `reviews/safeguard_layer_results.md`, `reviews/drift_check.md`, `reviews/reflexivity_check.md` (Test phase).
- `reviews/G4_signoff.md` (Ship phase only).
- `reviews/DO_NOT_DISTURB.md` (append only, only on user-approved freeze).

**Invariants.**
- I-Eval-1: Never writes to `manuscript/*`.
- I-Eval-2: Every finding cites (a) location in the artifact, (b) rule source (file + line/section), (c) severity, (d) proposed fix or explicit "accept as-is" rationale.
- I-Eval-3: Never silently carries findings across phases. Each phase's output stands alone.
- I-Eval-4: At submission-bound depth, every cited claim is verified per `EXTERNAL_VERIFIERS.md` Rule 7a or flagged as unverified-and-blocking.
- I-Eval-5: Does not adjudicate between its own findings and user overrides — flags the conflict for the Planner.
- I-Eval-6 (v0.7.3): Runs on the Planner-dispatched model per `MODEL_ALLOCATION.md §2`; does not override the model at dispatch time or reason about its own capability assignment. A dormant-at-T1 invocation (trigger-absent row for an Evaluator `actor` at a T1 row) is a dispatch-contract violation; the Reflector Phase 2f audit flags it as `E-MA-DORMANT-ACTOR-ENGAGED`.
- I-Eval-7 (v0.7.4): When the Evaluator delegates a sub-pass (a SAFEGUARD Check 8 sub-check run, a graph-grounding overlay, or a targeted deterministic-counter probe) to a subagent, invariants I-SubAgent-1..3 of §4.5 apply. The Evaluator's F1 findings artefact cites the subagent's F2/F3 artefact by path; the verdict is consumed as-returned and is not re-derived from the subagent's raw counters. If the Evaluator disagrees with a subagent verdict on audit-integrity grounds, the permitted move is `refuse-and-redispatch` (recorded as a fresh dispatch envelope) — never silent re-adjudication.
- I-Eval-8 (v0.8.0, P-13): **Parallel subagent dispatch is F6-gated.** Before launching more than one sub-pass concurrently at Ph3 or Ph4, the Evaluator reads the round's approved F6 `reviews/dispatch_plan_<cycle_id>.md` (via `dispatch_plan_reference` on the Evaluator's F1 artefact when present, or the active round plan otherwise). Per `ARTEFACT_FRONTMATTER_SCHEMA.md §7a.3`, **`parallel_dispatch` absent → `true`** (parallelism allowed when checks are independent). If the approved F6 sets **`parallel_dispatch: false`**, sub-passes MUST run **strictly sequentially** (`PHASE_PROTOCOL.md` §3.0 A-OT-3; `agents/evaluator.md` §3.0). When **`parallel_dispatch: true`** and sub-passes are independent, the Evaluator may parallelize compatible delegations and MUST log **`parallel_dispatch_cost_multiplier`** in the consolidated findings whenever parallelism was used (A-OT-2). The Evaluator MUST NOT override `parallel_dispatch` without a superseding user-approved F6 (`modifications_recorded: true`). Violations are audit-surfaced as MAJOR plan drift in the P-13 channel (compose with `R-Refl-DP-1` when the execution envelope contradicts the approved F6).

**Done criteria.**
- All phase-mandated files written.
- Exit gate from `ROUTING_SPINE.md` §3 evaluates to TRUE or the failure is documented with a specific, named cause.

**Scope budget per dispatch.**
- At `quick` depth: maximum 1 step (typically Step 0a deterministic checks).
- At `standard` depth: maximum Steps 0a–8.5 on a single manuscript version.
- At `submission-bound` depth: same as standard plus external verifiers. The Evaluator does not re-run Steps 1–7 on the same text twice in the same round; if the Generator edits, the Evaluator runs a re-check (SAFEGUARD Check 1 + spot-checks), not a full re-pass.
- If `round_program.md` narrows the scope (e.g., "evaluate §3 only"), the Evaluator limits findings to the specified scope and declares the constraint in the findings report header.

**Failure modes and recovery.**
- *Missed defect* (caught later by Reflector). Evaluator receives a delta in the next round's dispatch; Reflector proposes a new deterministic check or skill.
- *False positive* (user disputes a finding). Planner records the dispute; Reflector considers adding the case to `research_notes/directives.md`.

---

## 3. Generator Contract

**Role metaphor.** Prose writer and sole author of the manuscript. The only agent with write access to `manuscript/main.md`. Operates against a revision plan it did not produce; does not self-evaluate at the conceptual level.

**Preconditions for invocation.**
- `reviews/revision_plan.md` exists with at least one action tagged to the Generator.
- The Evaluator's findings (if any) have been merged into the plan by the Planner.

**Inputs (read).**
- `reviews/revision_plan.md`.
- `reviews/consolidated_findings_report.md` (for context on why each action exists).
- The relevant rule files cited by the plan (e.g., `bacon_2009_well_crafted_sentence_guidelines.md` for line-edits, `Sexton_Fiction_to_Academic_Writing_Guide.md` for structural openings).
- `STYLE_COMMITMENTS.md` to know which commitments (C-1…C-4) are in force.
- `GROUNDING_PROTOCOL.md` (binding — applied on every write).
- `manuscript/main.md` and prior `manuscript/revision_log.md` entries.

**Outputs (write).**
- `manuscript/main.md` (edits and new content).
- `manuscript/revision_log.md` (append-only per-round entry using the **structured experiment log format** — see template below).

**Structured experiment log format** (inspired by autoresearch's hypothesis→change→result→verdict logging):

```markdown
## Round <N> — <date>

**Round program focus:** <from round_program.md, or "none — full scope">
**Hypothesis:** <why we expect this change to improve the manuscript — ties to revision_plan action>
**Scope:** <which sections/paragraphs were modified>
**Changes:**
- [location] → [what changed] → [rule cited]
- ...
**Self-check result:** <Generator's deterministic check output — CLEAN or list of remaining hits>
**Verdict:** <RETAIN — improvement confirmed | REVERT — regression detected (see re-check) | PARTIAL — some changes retained, some reverted>
**Carried forward:** <any unresolved items deferred to next round>
```

The `Hypothesis` field is the critical addition: it forces the Generator to articulate *why* each change should help before making it, creating an auditable record that the Reflector uses to assess whether the harness's theory of improvement is sound.

**Invariants.**
- I-Gen-1: Never writes to `reviews/*` or `research_notes/*`.
- I-Gen-2: Every edit traces to a specific action in `revision_plan.md` OR is logged as a "discretionary edit" with rationale.
- I-Gen-3: Honors `GROUNDING_PROTOCOL.md` on every claim introduction: read-before-cite, compute-before-report, verify-before-reference, quote-before-attribute, mark-uncertainty, no-gap-filling.
- I-Gen-4: Runs deterministic self-check patterns before signaling completion (the mechanical subset of `DETERMINISTIC_CHECKS.md` that does not require a full pass).
- I-Gen-5: Does not introduce new citations, numerical claims, or quotations without the source file being readable from the project or from a registered verifier.
- I-Gen-6 (v0.7.3): Runs on the Planner-dispatched model per `MODEL_ALLOCATION.md §2` (T4 Generator is fix-only-no-new-prose and dispatches under Sonnet 4.6); does not override the model at dispatch time or request an uplift outside the directive channel. Fix-only scope violations at T4 — introducing new prose rather than applying Evaluator-surfaced fixes — are recorded as `Carried forward` in the experiment log and flagged to the Planner.
- I-Gen-7 (v0.7.4): The Generator does not delegate prose authorship under any circumstances — the sole-writer guarantee (I-Gen-1) forbids it. The Generator may consume a subagent-returned verdict only when the verdict is about non-prose state (e.g., a grounding audit over the existing draft, a deterministic-counter probe). When it does consume such a verdict, I-SubAgent-1..3 apply as read-only: the Generator cites the subagent artefact path in `manuscript/revision_log.md` and never re-derives the verdict. A subagent that attempts to return prose to the Generator is refused at the dispatch boundary.

**Done criteria.**
- Every action tagged to Generator in `revision_plan.md` is addressed (executed, or deferred with named cause).
- `revision_log.md` has a complete entry for the round.
- Deterministic self-check is clean, or remaining hits are flagged for Evaluator attention.

**Scope budget per dispatch.**
- Maximum scope per dispatch: the actions assigned to Generator in `revision_plan.md` for this round.
- Discretionary edits (changes not in the plan) must not exceed 20% of the round's total edits **by word count modified** (sum of words added, deleted, or replaced). If they would, the Generator signals the Planner for a scope-expansion approval.
- If `round_program.md` constrains the scope (e.g., "only touch §3 and §4"), the Generator must not edit outside those sections, even if the revision plan contains actions elsewhere. Out-of-scope actions are deferred, not silently skipped — log them as `Carried forward` in the experiment log.

**Failure modes and recovery.**
- *Regression introduced.* Evaluator's re-check catches it; Planner re-dispatches Generator with a narrowed plan. The experiment log entry records a `REVERT` verdict for the regressed changes.
- *Ungrounded claim.* Reflector's `GROUNDING_PROTOCOL.md` audit flags it; claim is either sourced or retracted before round close.
- *Scope creep.* Discretionary edits exceed 20% of round changes → Planner flags and asks whether scope has shifted.

---

## 4. Reflector Contract

**Role metaphor.** Cross-round memory keeper and package-level self-annealer. Never touches the manuscript. Reads everything. Proposes changes to rules, skills, and directives, but implements only within its own permission surface.

**Preconditions for invocation.**
- A round has completed (all phases the round attempted have closed, or the round was explicitly terminated by the user).
- All round artifacts are present in `reviews/`.

**Inputs (read).**
- Every artifact the round produced.
- `research_notes/lessons_learned.md` (prior lessons, to check for recurrence).
- `skills/SKILL_REGISTRY.md` (to check for duplicate-skill proposals).
- All package files (authoritative-read access).

**Outputs (write).**
- `reviews/reflection_report.md` (new, per round).
- `research_notes/lessons_learned.md` (append).
- `reviews/DO_NOT_DISTURB.md` (append only, with user approval).
- `research_notes/directives.md` (propose only — marked `[PROPOSED]` until user accepts).
- `skills/*.md` (new skill files, with user approval).
- `skills/SKILL_REGISTRY.md` (append on skill creation).

**Invariants.**
- I-Refl-1: Never writes to `manuscript/*` or to Planner/Evaluator review artifacts (those are frozen on reflection entry).
- I-Refl-2: Every proposed directive cites the round evidence that justifies it.
- I-Refl-3: Runs `DRIFT_CHECK.md` Phase 2.6 and `REFLEXIVITY_CHECK.md` Phase 2.7 on every round; submission-bound rounds cannot close without both resolved.
- I-Refl-4: Proposes a new skill only when all five skill-creation gates in `AGENT_ORCHESTRATION.md` §9 are met.
- I-Refl-5: Does not re-litigate findings the Evaluator already dispositioned unless new evidence has emerged.
- I-Refl-6 (v0.7.3): Runs on the Planner-dispatched model per `MODEL_ALLOCATION.md §2` — Haiku 4.5 in lightweight mode (30-day pilot under H-MA-2), Opus 4.7 in full mode at T4 close-out. The Phase 2f audit is extended to verify model-selection consistency against the allocation table: flags `E-MA-DORMANT-ACTOR-ENGAGED` (invariant I-MA-1), `R-Refl-MA-1` capability-inversion (invariant I-MA-2, BLOCKER), and `R-Refl-MA-3` orphan-override (invariant I-MA-3, MAJOR). Lightweight-mode telemetry is appended to `reviews/reflection_report.md` under the `model_dispatch_audit` heading on every run.
- I-Refl-7 (v0.7.4): The Phase 2f audit is extended to enforce the subagent-delegation invariants of §4.5. For every `dispatch_envelope` block in F1 / F5 artefacts and for every `dispatch_envelope_recorded: true` flag in F3 artefacts, the Reflector verifies (a) the cited subagent artefact exists and validates against its declared frontmatter family, (b) the returned verdict matches the verdict that propagated into the dispatcher's artefact (no silent re-adjudication), and (c) the dispatch envelope contains the required fields (`subagent_type`, `model_used`, `dispatched_at`, `artefact_path`, `verdict_consumed`). The audit files `R-Refl-SA-1` (BLOCKER; re-adjudication of a subagent verdict), `R-Refl-SA-2` (MAJOR; missing or malformed envelope), and `R-Refl-SA-3` (MAJOR; inline verdict without backing artefact). The Reflector never re-adjudicates a subagent verdict itself — doing so would violate I-SubAgent-1 in the audit surface.

**Done criteria.**
- Reflection report written with at minimum: round summary, patterns observed, proposed directives, proposed skills (or empty), drift check verdict, reflexivity check verdict.
- Lessons appended.
- User has been presented with the report and has approved/rejected any proposed writes that require approval.

**Scope budget per dispatch.**
- Maximum 5 new lessons per round. If more than 5 patterns are identified, the Reflector consolidates related patterns into higher-level lessons.
- Maximum 1 new skill proposal per round (unless the round uncovered a genuinely novel, cross-project pattern).
- The Reflector's audit of experiment log verdicts (RETAIN/REVERT/PARTIAL from Generator's structured log) must be completed before lessons are extracted. This ensures lessons are grounded in observed outcomes, not in speculative pattern-matching.

**Failure modes and recovery.**
- *Lesson noise.* If `lessons_learned.md` grows by >3 entries per round on average, Reflector pauses and proposes a consolidation pass instead of additional entries.
- *Skill proliferation.* If >1 skill per round is proposed for three consecutive rounds, the bar for the fourth is raised to "demonstrated cross-project recurrence."

---

## 4.5 SubAgent delegation invariants (v0.7.4 — P-5)

**Why this subsection exists.** v0.7.4's P-5 proposal legalizes a mechanism the v0.7.0–v0.7.3 package had left implicit: the four-agent Planner / Evaluator / Generator / Reflector may each dispatch *subagents* — Agent-tool invocations under a declared `subagent_type` — to run bounded, verdict-returning tasks (a SAFEGUARD Check 8 aggregation, a grounding-audit probe over a bounded file set, a deterministic-counter pass). The mechanism is narrow and its integrity property is load-bearing: without it, the four-agent contract degrades because a dispatcher could silently re-do the work the subagent returned, inflating round cost and erasing the audit trail. The invariants below make the delegation surface auditable by the Reflector's Phase 2f audit; they sit alongside the four-agent contract, not above or below it.

**Shared invariants.** The following invariants bind every agent that dispatches a subagent. Per-agent pointers at I-Planner-6, I-Eval-7 / I-Eval-8, I-Gen-7, and I-Refl-7 incorporate them by reference.

- **I-SubAgent-1 (authoritative-as-read; the core invariant).** A subagent-returned verdict is *authoritative-as-read*: the dispatching agent may neither re-adjudicate the verdict, re-compute it from the subagent's raw inputs, nor overwrite it with a different verdict. The only permitted moves after receipt are *cite-and-consume* (the dispatcher propagates the verdict into its own artefact with provenance) or *refuse-and-redispatch* (the dispatcher rejects the round and issues a fresh dispatch with a new envelope). Silent re-adjudication is a Reflector Phase 2f `R-Refl-SA-1` BLOCKER.

- **I-SubAgent-2 (dispatch envelope; auditability).** Every subagent dispatch records a *dispatch envelope* in the dispatching agent's output artefact. The envelope must include, at minimum: `subagent_type` (the Agent-tool parameter), `model_used` (resolved from `MODEL_ALLOCATION.md §2`), `dispatched_at` (ISO 8601 timestamp), `artefact_path` (relative path to the subagent's written artefact under `reviews/`), and `verdict_consumed` (the verdict string that propagated into the dispatcher's artefact). An F3 artefact records the envelope via the `dispatch_envelope_recorded: true` optional field; F1 / F5 artefacts carry the envelope block inline in the prose body under a `## Subagent dispatch envelope` heading. A delegation without an envelope is audit-invisible and is flagged `R-Refl-SA-2` MAJOR.

- **I-SubAgent-3 (artefact contract).** The subagent writes its own artefact under `reviews/`, conforming to exactly one of the F1–F5 frontmatter families per `ARTEFACT_FRONTMATTER_SCHEMA.md`. The dispatching agent cites the subagent artefact by path; the dispatcher never transcribes the subagent's verdict inline as though the dispatcher had computed it. An inline verdict without a backing artefact is flagged `R-Refl-SA-3` MAJOR. When the subagent is a lightweight probe (e.g., a single grounding audit), family F3 is appropriate; when the subagent runs a deterministic-counter sweep, family F2 is appropriate; when the subagent runs a judgment-layer Check 8 aggregation, family F1 is appropriate.

**What a legal dispatch looks like.** The Planner (or Evaluator) calls the Agent tool with `subagent_type` set to one of the registered subagent types (`grounding-audit`, `accessibility-overlay`, `quick-deterministic`), and the resolved `model` parameter from `MODEL_ALLOCATION.md §2`. The subagent receives a narrowly-scoped prompt (no open-ended authority), produces its artefact under `reviews/`, and returns the verdict string to the caller. The caller records the envelope, propagates the verdict, and moves on. The caller does not re-read the subagent's `grounding_basis` files to "check the work" — that re-read is precisely the re-adjudication move I-SubAgent-1 forbids.

**What the Reflector does with this.** At every round close (lightweight or full), the Reflector's Phase 2f audit collects the envelopes, verifies the cited artefacts exist and validate, compares the verdicts propagated into the dispatcher artefacts against the verdicts written in the subagent artefacts themselves, and files `R-Refl-SA-1..3` findings where the three invariants are violated. `R-Refl-SA-1` is a BLOCKER because re-adjudication corrupts the audit trail in a way that cannot be recovered post hoc. `R-Refl-SA-2` and `R-Refl-SA-3` are MAJOR because the audit-trail is recoverable (a missing envelope can be reconstructed from session transcripts; an inline verdict can be back-filled into an artefact) but the next round must not ship until the envelope is written.

**Relationship to I-MA-*.** The I-SubAgent-* invariants and the I-MA-* model-allocation invariants compose: every dispatch envelope records `model_used`, and the Reflector Phase 2f audit cross-checks it against both the subagent allocation (I-MA-1..3) and the I-SubAgent-1 verdict integrity. A round that records a correct envelope and records the wrong model still fails I-MA-2; a round that records the right model but silently re-adjudicates still fails I-SubAgent-1. The two invariant families are orthogonal.

---

## 5. Inter-Agent Dependencies (AORE dependency model)

Expressing the four agents as an i\*-style Strategic Dependency (SD) fragment:

- **Planner depends on Evaluator** for: task-level *findings* (a resource dependency); *freedom from defect* as a softgoal.
- **Planner depends on Generator** for: task-level *prose realization of the revision plan*; *timeliness* as a softgoal.
- **Planner depends on User** for: *approval at checkpoints* (a task dependency) and *authority on precedence conflicts* (a goal dependency).
- **Evaluator depends on Generator** for: *manuscript availability in a readable state*.
- **Evaluator depends on Planner** for: *classification accuracy* and *plan coherence*.
- **Generator depends on Planner** for: *unambiguous, single-agent-dispatchable actions*.
- **Generator depends on Evaluator** for: *post-edit re-check* (closes the loop).
- **Reflector depends on all three** for: *completed round artifacts*.
- **All three depend on Reflector** for: *memory persistence across rounds* and *package evolution*.

The dependencies are deliberately asymmetric. The Planner is the hub; the Reflector is the cross-round rail. The Evaluator and Generator are mutually dependent but never exchange directly — they exchange through files mediated by the Planner. This preserves the *separation of concerns* that makes the system auditable.

---

## 6. Contract verification

At the close of every round, the Reflector verifies contract compliance with a lightweight audit:

| Check | Agent | Source of truth |
|-------|-------|-----------------|
| Did Planner dispatch any agent without a phase+gate declaration? | Planner | Dispatch records in `revision_plan.md` |
| Did Evaluator write to `manuscript/*`? | Evaluator | Git diff / file mtime |
| Did Generator introduce an ungrounded claim? | Generator | `GROUNDING_PROTOCOL.md` Rule 7a audit |
| Did Reflector write to `reviews/*` beyond `reflection_report.md`? | Reflector | File-write log |
| Did any agent bypass a user checkpoint? | All | Checkpoint log in session transcript |
| Did any agent write to an **immutable-layer** file? (see `AGENT_ORCHESTRATION.md` §8.1) | All | File-write log; immutable layer = `GROUNDING_PROTOCOL.md`, `REVIEW_ORCHESTRATION.md`, `DETERMINISTIC_CHECKS.md`, `SAFEGUARD_LAYER.md`, `AGENT_CONTRACTS.md`, `ROUTING_SPINE.md`, `DO_NOT_DISTURB.md` |
| Did Generator exceed the 20% discretionary edit budget (by word count modified)? | Generator | `manuscript/revision_log.md` experiment log entries vs. `reviews/revision_plan.md` actions |
| Did any agent act outside `round_program.md` scope constraints (if present)? | All | `round_program.md` constraints vs. actual file writes |
| Did the round dispatch a subagent on a model that does not match `MODEL_ALLOCATION.md §2` for the section's `current_phase`? | Planner (dispatch); Reflector (audit) | `reviews/phase_state.json` `phase_entry_log[].notes` `model_dispatch:...` entries vs. `MODEL_ALLOCATION.md §2` |
| Did the round produce a capability inversion (Evaluator below Generator on the family ordering)? | Planner | Resolved model strings per dispatched agent in the round |
| Does every `model_override:...` entry correspond to an active `D-NN: Model dispatch override` directive? | Reflector (Phase 2f) | `research_notes/directives.md` vs. `reviews/phase_state.json` `phase_entry_log[].notes` |
| Did any agent silently re-adjudicate a subagent-returned verdict (I-SubAgent-1 violation)? | Planner, Evaluator, Generator | Dispatcher artefact's propagated verdict vs. subagent artefact's written verdict (`R-Refl-SA-1` BLOCKER) |
| Did any subagent dispatch run without a recorded dispatch envelope (I-SubAgent-2 violation)? | Planner, Evaluator, Generator | F3 `dispatch_envelope_recorded: false` or absent `## Subagent dispatch envelope` block in F1 / F5 prose body (`R-Refl-SA-2` MAJOR) |
| Did any agent inline a subagent verdict without citing a backing subagent artefact (I-SubAgent-3 violation)? | Planner, Evaluator | Dispatcher artefact citing a verdict with no artefact-path pointer to `reviews/` (`R-Refl-SA-3` MAJOR) |
| Did the session-state cache serve a stale parse at round close (I-Planner-7 violation)? | Planner | End-of-round `sha256(file_bytes)` for the three cached paths vs. round-entry hash recorded at Phase 0.5, absent a documented write-through or external-invalidation advisory (`R-Refl-Cache-1` MAJOR) |
| Did the round exhibit a re-read storm on cached files (I-Planner-7 storm threshold)? | Planner | Per-round read count for `reviews/phase_state.json` / `reviews/classification.md` / `research_notes/directives.md` vs. `3 × |cached_files_this_round|` threshold (`R-Refl-Cache-2` MINOR) |
| Did a manuscript-level Ph3 batch carry a split `cycle_id` across its member rows (I-Planner-8 / P-7 cohesion rule)? | Planner | All rows sharing a `cycle_id` must also carry `trigger: ph3_iteration_round_manuscript` and `trigger_scope:manuscript` (`R-Refl-Batch-1` MAJOR) |
| Did a `cycle_id` value re-appear in a second batch (I-Planner-8 uniqueness rule)? | Planner | Cross-section scan of all `phase_entry_log[]` arrays for duplicate `cycle_id` occurrences (`R-Refl-Batch-2` MAJOR) |
| Does every manuscript-level batch have a matching `convergence_journal.jsonl` row with the same `cycle_id`? | Planner | Journal row count per `cycle_id` must equal 1; batch row count per `cycle_id` must be ≥ 2 (`[P7-BATCH-ORPHAN]` / `[P7-JOURNAL-MISSING]` MAJOR) |
| Did the Planner raise `ceiling_locked(S) ← true` at Ph3 without a corresponding approved ceiling-lock proposal artefact (I-Planner-9 / P-8 gate rule)? | Planner | `reviews/ceiling_lock_proposal_<date>.md` must exist with matching section S and approved Option C signoff line; absence is `R-Refl-Ceil-1` BLOCKER |
| Did the Planner emit a ceiling-lock proposal absent the tension-detection rule (BORDERLINE + two-round in-band on the **line-diff scalar**, per `PHASE_PROTOCOL.md` §3.3.6) being satisfied (I-Planner-9 justification rule)? | Planner | Proposal body must cite the BORDERLINE advisory ID and the two-round **scalar** trajectory; missing evidence is `R-Refl-Ceil-2` MAJOR |
| Did the Evaluator parallelize subagent delegations when the approved F6 carried `parallel_dispatch: false` (I-Eval-8 / P-13 A-OT-3)? | Evaluator; Reflector (Phase 2f) | Approved F6 `parallel_dispatch` vs. envelope timestamps / concurrency evidence in F1 prose or session log |
| Did the Evaluator omit `parallel_dispatch_cost_multiplier` after using parallel sub-passes while `parallel_dispatch: true` (I-Eval-8 / P-13 A-OT-2)? | Evaluator; Reflector (Phase 2f) | Consolidated findings deterministic summary or dedicated line vs. subagent dispatch count > 1 concurrent |
| Does every ceiling-lock proposal artefact carry `ceiling_lock_detected: true` in frontmatter (P-3/P-8 frontmatter contract)? | Planner | F5 frontmatter `ceiling_lock_detected` field present and set to `true`; absence is `R-Refl-Ceil-3` MAJOR |
| Does every Option-C approval row carry the `[CEILING-LOCK-STABLE]` marker in `phase_state.json log[].notes`? | Planner | `user_approved_ph3_convergence_signoff` rows with `ceiling_locked:true` in notes must also carry `[CEILING-LOCK-STABLE]`; absence is `R-Refl-Ceil-4` MINOR |
| Did the Planner dispatch an agent / model / phase combination that does not appear in the approved F6 dispatch plan (I-Planner-10 / P-1 plan-drift rule)? | Planner | `reviews/dispatch_plan_<cycle_id>.md` `dispatched_agents[]` entries vs. actors / phases / model strings observed in `phase_state.json log[]` for the same `cycle_id` (`R-Refl-DP-1` MAJOR) |
| Did a round produce F1 / F2 / F3 / F5 artefacts without a corresponding F6 dispatch-plan artefact present (I-Planner-10 / P-1 plan-presence rule)? | Planner | Per-cycle `reviews/dispatch_plan_<cycle_id>.md` existence check; absence with any downstream artefact in the same cycle is `R-Refl-DP-2` BLOCKER |
| Did any downstream artefact cite a `dispatch_plan_reference` whose target F6 lacks a populated `user_approval_signature` (I-Planner-10 / P-1 consent rule)? | Planner | F5 / F1 `dispatch_plan_reference` pointer dereferenced; target F6's `user_approval_signature.approved_at` must be non-empty; absence is `R-Refl-DP-3` BLOCKER |

Violations are recorded in `reviews/reflection_report.md` §6 (Contract Audit) and, if recurrent, escalated to `DO_NOT_DISTURB.md` as frozen corrective rules.

---

*Created 2026-04-13. Operationalizes the AORE framing announced in `CLAUDE.md`: each agent is an autonomous party bound by an explicit protocol. Paired with `ROUTING_SPINE.md` (phase dispatch) and `PARALLEL_CONDUCTOR.md` (multi-project concurrency). Updated 2026-04-13: autoresearch-inspired additions — scope budgets per agent dispatch (§§1–4), `round_program.md` as Planner input (§1), structured experiment log format for Generator output (§3), Reflector audit of experiment verdicts (§4). Updated 2026-04-21 (v0.7.3): added I-Planner-5 (Planner-resolved model dispatch from `MODEL_ALLOCATION.md`, capability-inversion refusal), I-Eval-6 (no-override-at-dispatch; dormant-at-T1 invariant), I-Gen-6 (no-override; T4 fix-only under Sonnet), I-Refl-6 (Phase 2f model-selection audit; lightweight-mode telemetry); extended §6 contract-verification table with three new model-dispatch audit rows. Updated 2026-04-21 (v0.7.4, P-5): added §4.5 SubAgent delegation invariants (shared I-SubAgent-1 authoritative-as-read, I-SubAgent-2 dispatch envelope, I-SubAgent-3 artefact contract), added per-agent pointers I-Planner-6 / I-Eval-7 / I-Gen-7 / I-Refl-7, extended §6 contract-verification table with three subagent-delegation audit rows (R-Refl-SA-1 BLOCKER, R-Refl-SA-2 / R-Refl-SA-3 MAJOR). Composes with I-MA-* orthogonally. Updated 2026-04-21 (v0.7.4, P-6): added I-Planner-7 (session-state cache invariant; hash-keyed write-through round-scoped cache over `reviews/phase_state.json`, `reviews/classification.md`, `research_notes/directives.md`); extended §6 contract-verification table with R-Refl-Cache-1 (MAJOR stale-key round-close) and R-Refl-Cache-2 (MINOR re-read storm). Orthogonal to both I-SubAgent-* and I-MA-*. Updated 2026-04-21 (v0.7.4, P-7): added I-Planner-8 (manuscript-level Ph3 batching contract per `PHASE_PROTOCOL.md §3.3.5`; N rows under `trigger: ph3_iteration_round_manuscript` with one shared `cycle_id` per batch); extended §6 contract-verification table with three new P-7 audit rows (`R-Refl-Batch-1` MAJOR cohesion, `R-Refl-Batch-2` MAJOR uniqueness, `[P7-BATCH-ORPHAN]` / `[P7-JOURNAL-MISSING]` MAJOR journal correspondence). Composes orthogonally with cache-, SA-, and MA-family invariants. Updated 2026-04-21 (v0.7.4, P-8): added I-Planner-9 (ceiling-lock termination-ranking contract per `PHASE_PROTOCOL.md §3.3.6`; Planner tension-detection rule, distance-to-ceiling ranking metric, F5 proposal artefact with `ceiling_lock_detected: true` frontmatter, `[CEILING-LOCK-STABLE]` marker on approval rows, reuse of existing `user_approved_ph3_convergence_signoff` trigger); extended §6 contract-verification table with four new P-8 audit rows (`R-Refl-Ceil-1` BLOCKER silent ceiling-lock, `R-Refl-Ceil-2` MAJOR unjustified proposal, `R-Refl-Ceil-3` MAJOR missing frontmatter marker, `R-Refl-Ceil-4` MINOR missing `[CEILING-LOCK-STABLE]` on approval). Composes orthogonally with Batch-, Cache-, SA-, and MA-family invariants; complements §9.4's MCR admission disjunction by defining the pre-admission mechanism that legitimately raises `ceiling_locked: true` mid-Ph3. Updated 2026-04-21 (v0.7.4, P-1): added I-Planner-10 (round-dispatch-plan contract; Planner sole-writer of F6 `reviews/dispatch_plan_<cycle_id>.md` at Phase 0.6, blocking user-checkpoint on approval signature, Phase 4.5 / Phase 4.6 consume pre-authored F6 rather than re-resolving); extended §6 contract-verification table with three new P-1 audit rows (`R-Refl-DP-1` MAJOR plan-drift, `R-Refl-DP-2` BLOCKER missing plan, `R-Refl-DP-3` BLOCKER unapproved plan). The F6 family is strict-family per `ARTEFACT_FRONTMATTER_SCHEMA.md §8` and is NOT inherited under P-2 stability sub-mode — every round authors a fresh F6. Composes orthogonally with Ceil-, Batch-, Cache-, SA-, and MA-family invariants; precedes MA-family consumption at Phase 4.5. Updated 2026-04-22 (v0.8.0 P2.7): **I-Planner-10** extended — F6 §7a.2 profile quartet when any `dispatched_agents[]` row is at `phase: Ph3`; **I-Planner-9** amended — line-diff scalar (`legacy_scalar` when object-shaped) for tension + distance; F5 `menu_items_presented` and `/ph3-terminate` surfacing; **I-Planner-11** (P-16 ceiling-aware iteration budget + Phase 6 MCR `pre_mcr_deep_pass_completed` narrative; hook to `agents/planner.md` P2.6); **I-Eval-8** (P-13 — F6 `parallel_dispatch` gates parallel subagent work, A-OT-2 multiplier when parallel); **I-Planner-5** log path corrected to `reviews/phase_state.json`; §6 verification table — `current_phase` + `reviews/phase_state.json` notes paths, I-Planner-9 scalar wording, two P-13 audit rows; §4.5 shared-invariants pointer includes I-Eval-8.*
