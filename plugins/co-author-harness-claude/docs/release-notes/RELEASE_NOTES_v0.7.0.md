# Release Notes — research-writing-harness-claude v0.7.0

**Release date:** 2026-04-20
**Theme:** the Lifecycle-Stage Ladder — four rungs reframed as lifecycle stages (Plan & Draft / Review & Revise / Iterate & Converge / Finalize & Close), with tier-conditioned agent engagement, full-file reads as the universal grounding floor, and a Manuscript Convergence Report (MCR) admission gate that models iterative convergence rather than single-shot readiness.
**Verdict:** CLEARED-WITH-WARNINGS (pending the Reflector full-mode close-out pass; all invariant and smoketest gates clean; `plugin.json.description` at 348 chars, inside the 350-char conservative envelope).

---

## One-paragraph summary

v0.7.0 is a framing redesign. The v0.6.0 Progressive Approval Staircase (four rungs framed as successive *review depths* — Draft / Review / Verify / Ship — with `T4_ready` as a terminal enum value, Rule 1's tier-gated digest exception preserved at T1, and Evaluator Confirmation Mode paired with Generator Self-T1 Verdict at T2 entry) is replaced by a **Lifecycle-Stage Ladder** whose rungs are lifecycle stages, not review depths: **T1 Plan & Draft** (absorbs retired milestones M1+M2+M3), **T2 Review & Revise** (absorbs M4a), **T3 Iterate & Converge** (absorbs M4b, unbounded iteration toward a declared convergence metric), **T4 Finalize & Close** (absorbs M5, terminal with G.4 sign-off). The per-section ledger widens from a 10-field `SectionStateObject` to a 15-field schema with five net-new fields; the row shape changes from five fields to six with a required `actor`; the trigger enum reaches 27 values with three monotonicity exemptions; the `T4_ready` state is renamed `T3_converged`; the admission artefact is renamed Laggard Clearance Report → **Manuscript Convergence Report (MCR)**. The grounding regime is unified — full-file reads become the universal floor at every rung, retiring Rule 1's tier-gated digest exception wholesale. The Evaluator Confirmation Mode + Generator Self-T1 Verdict + EG-2 triad is retired in favour of tier-conditioned agent engagement (Evaluator dormant at T1; joins at T2 with SD/SR read-prerequisites; full engagement at T3/T4). The Reflector splits into lightweight mode (T1/T2/T3 ad-hoc integrity probe, Phases 1, 2.5, 2.6, 2f, 3 — memory-only) and full mode (T4 close-out, all five phases + new audit phases 2d/2e/2f). The Planner adds a three-filter gatekeeper role over `reviews/plugin_update_proposals.md`. The T3R response-letter sibling ladder is retired; `response-letter-review` dispatches as a manuscript-class on the main ladder.

## Headline change — the Lifecycle-Stage Ladder

```
   T1 Plan & Draft  →  T2 Review & Revise  →  T3 Iterate & Converge  →  T4 Finalize & Close
   (M1+M2+M3)          (M4a)                   (M4b, unbounded)          (M5, terminal)
        │                     │                        │                        │
   Generator-led        Evaluator joins          Full four-agent           G.4 sign-off
   no Self-T1           SD/SR read-prereq        loop + convergence        required
   Evaluator dormant    E-T2-SD-UNGROUNDABLE     trajectory                Reflector full mode
                                                 T3_converged ↑
                                                 (terminal sign-off)
                                                        │
                                                 MCR admission ───→ T4
                                                 (every section T3_converged;
                                                  +50% iteration reserve;
                                                  climb target capped at
                                                  default_final_tier)
```

- Each rung is a **lifecycle stage**, not a review depth. T1 is the plan-and-draft stage; T2 is first-review-and-revision; T3 is unbounded iteration toward a declared `convergence_metric`; T4 is close-out and submission.
- **Agent engagement is tier-conditioned.** Evaluator is dormant at T1 (Generator-led; no Self-T1 Verdict; no Confirmation Mode). Evaluator joins at T2 with SD/SR read-prerequisites declared in `reviews/classification.md` — missing SD/SR artefacts at T2 entry raise the net-new finding class `E-T2-SD-UNGROUNDABLE`. T3 runs the full four-agent loop with unbounded iteration feeding `reviews/convergence_log.md`; the terminal sign-off row flips the section to `current_tier: T3_converged`. T4 is terminal with G.4 sign-off required.
- **T4 admission is MCR-gated.** Every section must reach `current_tier: T3_converged`; the Manuscript Convergence Report (`references/TIER_PROTOCOL.md §7`) identifies any laggard sections, the iteration budget needed to clear them (with the +50% reserve preserved from NEW-H-7), and the climb target (capped at `default_final_tier`). The flag is renamed `laggard_clearance_approved` → `mcr_admission`.
- **Monotonicity remains an invariant** with three documented exemptions: `retraction` (human-initiated demotion, inherited from v0.6.0), `eg1_t4_downgrade_to_t3` (T4→T3 grounding-demotion gate; repurposed EG-1), and `eg7_mcr_readmission_after_class_change` (re-admission after a mid-review manuscript-class change; net-new EG-7).

## What retires

- **Evaluator Confirmation Mode** (v0.6.0 T2-entry short-circuit). The mechanism paired with Generator Self-T1 Verdict to skip a full Evaluator pass when a `CLEAN` verdict was recorded; in practice it created a self-grading loop whose failure mode (EG-2 mismatch) was recorded *after* the verdict had already shaped the next round. Retired wholesale. Agents file Evaluator passes unconditionally at T2.
- **Generator Self-T1 Verdict (Phase 3.5).** `CLEAN | SUSPECT | DIRTY` self-grading at T1 close is retired. T1 no longer emits a verdict; the next-rung Evaluator (at T2) reads the T1 deliverable directly.
- **EG-2 (Self-T1 verdict mismatch).** Gate-level retirement consequent to the Confirmation Mode + Self-T1 Verdict retirement.
- **T3R response-letter sibling ladder.** `response-letter-review` no longer runs as a sibling rung; it dispatches as a manuscript-class on the main Lifecycle-Stage Ladder. The `/review-letter` slash command is preserved but routes through standard ladder semantics.
- **Rule 1 tier-gated digest exception.** The `{T1}`-scoped digest read-path inherited from v0.6.0 is retired. Full-file reads become the universal grounding floor at every rung. Rationale: the two-law grounding regime (digest-at-T1, full-file-elsewhere) bifurcated every Evaluator rule citation and invited hallucination at the handoff; a single code path is safer.
- **`scripts/verify_rule_digest.py`.** Archived under `legacy/`. The release-gate Phase 0.67 no longer builds or verifies a rule digest.
- **`eygp-framework-checker` (SK-28).** Retired under criterion R5 (User directive, release-gate WARN). Migration path: SK-10 `p-stage-checker` for the P-axis.
- **Reflector Phase 3a (Digest Integrity).** Retired in consequence of the rule-digest retirement.

## What is net-new

- **Lifecycle-Stage Ladder framing.** Four rungs as lifecycle stages. See `references/TIER_PROTOCOL.md §§1–6` and the revised `references/TIER_PROTOCOL_SR.mermaid`.
- **15-field `SectionStateObject`** — five new fields:
  - `tier_goal_declared` — explicit climb intent at classification time.
  - `tier_deliverable_path` — per-stage deliverable pointer (where the stage's output lives in the project tree).
  - `convergence_metric` — T3's declared unbounded-iteration metric (e.g., reviewer-agreement rate, contradiction-density ceiling, or user-declared narrative-stability threshold).
  - `t1_pstage_declaration` — P0/P1/P2 declared at T1 entry; downstream skills read this in place of probing the manuscript.
  - `t3_last_activity_at` — T3 re-engagement refresh timestamp; stalled sections surface under the new `[T3-STALE]` Reflector audit phase.
- **Six-field row shape** — `{prev_tier, new_tier, trigger, actor, notes (≤280 chars), timestamp}`. `actor` is required and must be one of `{planner, evaluator, generator, reflector, user}`. Legacy v0.6.0 `scope` / `cycle_id` / `detail` fields are folded into the canonical `notes` string by the migrator.
- **27-trigger enum** — six triggers retired in the Confirmation/Self-T1 sweep; lifecycle-stage triggers including `t3_convergence_reached`, `mcr_admission`, `eg1_t4_downgrade_to_t3`, `eg7_mcr_readmission_after_class_change` are net-new. `confirmation_failed` is preserved read-only for historical audit; no v0.7.0 agent emits it. Three monotonicity-exempt triggers enumerated above.
- **Manuscript Convergence Report (MCR).** Renamed from Laggard Clearance Report. The audit artefact produced by the Planner at T4 admission time. `mcr_admission` flag replaces `laggard_clearance_approved`. +50% iteration reserve preserved (NEW-H-7); climb target capped at `default_final_tier` (R-02).
- **Tier-conditioned agent engagement** — Evaluator dormant at T1; joins at T2 with SD/SR read-prerequisites; full engagement at T3/T4.
- **`E-T2-SD-UNGROUNDABLE` finding class.** Fires when the Evaluator enters T2 and cannot locate declared SD/SR artefacts. Blocks T2 → T3 advancement until cleared.
- **Reflector dispatch split.**
  - *Lightweight mode* — Phases 1, 2.5, 2.6, 2f, 3 only. Runs at T1/T2/T3 as an ad-hoc integrity probe. Memory-only; no skill-development phase.
  - *Full mode* — all five phases + new audit phases 2d/2e/2f. Runs at T4 close-out.
- **Three new audit phases:**
  - 2d — T3 convergence trajectory audit against `reviews/convergence_log.md`.
  - 2e — `[T3-STALE]` catalog + MCR volatility check.
  - 2f — tier-row contract audit against the six-field row shape, 27-trigger enum, three monotonicity exemptions, and 15-field SectionStateObject.
- **EG-1 repurposed.** Formerly "Confirmation Mode digest mismatch at T1"; now the **T4→T3 grounding-demotion gate** (monotonicity-exempt via `eg1_t4_downgrade_to_t3`). Fires when a T4-admitted section fails a G.4-late grounding probe and must be returned to T3 for further convergence.
- **EG-6 degraded** to a non-blocking warning (was blocking at v0.6.0).
- **EG-7 — net-new gate.** `eg7_mcr_readmission_after_class_change`. Fires when a manuscript class changes after MCR admission, triggering re-admission through a fresh MCR cycle. Monotonicity-exempt.
- **Planner three-filter gatekeeper over `reviews/plugin_update_proposals.md`.** Every Reflector-filed proposal must pass: (i) evidence-adequacy (≥2 rounds or ≥2 projects cited), (ii) non-duplication (must not restate an active or retired skill), (iii) tier-appropriateness (must declare which tier(s) the proposed skill/rule would operate at). Failed proposals are routed back to the Reflector with a remediation note.
- **`reviews/convergence_log.md`** — per-section T3 iteration ledger. Captures each iteration's reviewer verdicts, deltas against the declared `convergence_metric`, and the Generator's response. The terminal sign-off row flips `current_tier: T3_converged`.
- **`scripts/migrate_v060_to_v070.py`** — one-way v0.6.0 → v0.7.0 project migrator. Widens `SectionStateObject` from 10 fields to 15, rewrites every row to the six-field shape, renames `T4_ready` → `T3_converged` and `laggard_clearance_approved` → `mcr_admission`, emits `reviews/migration_report_v060_to_v070.md`. Idempotent.
- **`references/tier_notifications.yaml`** — `config_version` 2.0 → 3.0.

## Breaking changes

- `plugin.json.version` → `0.7.0`; `description` rewritten for the Lifecycle-Stage Ladder.
- `references/tier_notifications.yaml` `config_version` 2.0 → 3.0.
- `SectionStateObject` widens 10 → 15 fields (validator rejects 10-field rows at `SCHEMA_VERSION_UNKNOWN`-adjacent codes).
- Row shape changes from five-field to six-field with required `actor` (`{planner, evaluator, generator, reflector, user}`). Legacy `scope` / `cycle_id` / `detail` folded into `notes` (≤280 chars; longer strings truncated with a `[…]` marker).
- `T4_ready` and `laggard_clearance_approved` vocabulary retired; consumers must read `T3_converged` and `mcr_admission`.
- `scripts/verify_rule_digest.py` archived — workflows that invoked it must switch to full-file reads.
- `/review-letter` no longer dispatches T3R — dispatches as a manuscript-class on the main ladder.
- Confirmation Mode + Self-T1 Verdict + EG-2 no longer fire. Workflows that depended on the `CLEAN` verdict shortcut must file a full T2 Evaluator pass unconditionally.
- Grounding Rule 1 tier-gated digest exception retired — full-file reads mandatory at every rung.
- Monotonicity invariant: three documented exemptions (`retraction`, `eg1_t4_downgrade_to_t3`, `eg7_mcr_readmission_after_class_change`); any other downward transition is a `MONOTONICITY_VIOLATION`.
- Single-writer invariant on `tier_state.json` preserved from v0.6.0.
- Skill count 25 → 24 (`eygp-framework-checker` retired under R5).

## Migration

The migration is one-way (rollback requires the preserved `research-writing-harness-claude-v0.6.0/` tree). Recommended sequence:

```bash
# 1. Dry-run to inspect warnings and mapped rows without writing.
python3 scripts/migrate_v060_to_v070.py \
    --project-root <project> \
    --dry-run

# 2. Real run.
python3 scripts/migrate_v060_to_v070.py \
    --project-root <project>

# 3. Review reviews/migration_report_v060_to_v070.md (§§1–3).
# 4. Append the confirmation line to reviews/classification.md frontmatter:
#      user_confirmed_migration_report_at: 2026-04-20T00:00:00Z
# 5. Invoke /review or /review --section <path>; Planner Phase 0 clears the hold.
```

The migrator handles: `T4_ready` → `T3_converged` rename across every ledger; `laggard_clearance_approved` → `mcr_admission` rename; five-field → six-field row rewrite with `actor` populated from the writer-of-record (`planner` for user-approval rows, `evaluator` for gate-firing rows, etc.); legacy `scope` / `cycle_id` / `detail` fold into `notes` with truncation markers where the concatenation exceeds 280 chars; net-new field defaults for `tier_goal_declared` (`default_final_tier`), `tier_deliverable_path` (empty, user-populated), `convergence_metric` (empty, user-populated at T3 entry), `t1_pstage_declaration` (probed from `reviews/classification.md`), `t3_last_activity_at` (latest T3-band row timestamp); `confirmation_failed` rows preserved read-only with a `[v0.7.0-READ-ONLY]` marker appended to `notes`.

Three script exit codes to know: 1 missing inputs, 2 schema validation failure post-write, 3 output collision without `--force`, 4 bad invocation.

## Files changed (summary)

**Normative (rewritten):**
- `references/TIER_PROTOCOL.md` — full rewrite for the Lifecycle-Stage Ladder + MCR + tier-conditioned agent engagement + three monotonicity exemptions.
- `references/tier_state_schema.md` — rewritten for 15-field SectionStateObject + six-field row + 27-trigger enum + three monotonicity exemptions.
- `references/AGENT_ORCHESTRATION.md §§3, 8.2a, 8.2b, 10` — escalation log revised for six-field rows; §8.2a documents EG-1 repurposing and EG-7 net-new; §8.2b documents Reflector dispatch split; §10 updates the agent-I/O matrix for tier-conditioned engagement.
- `references/REVIEW_ORCHESTRATION.md` — rewritten for the Lifecycle-Stage Ladder; T3R sibling-ladder section retired.
- `references/GROUNDING_PROTOCOL.md §§38–50` — Rule 1 tier-gated digest exception retired; full-file reads declared universal floor; Rule 5 / Rule 7a updated to match.
- `references/SKILL_REGISTRY.md` — swept for v0.7.0; v0.7.0 vocabulary banner added; SK-28 retirement filed; SK-25/SK-26/SK-27/SK-29 rewritten bodies (identifiers preserved).
- `references/tier_notifications.yaml` — `config_version` 3.0 block.

**Agents (rewritten):**
- `agents/planner.md` — three-filter gatekeeper role net-new; MCR authoring section; Reflector dispatch-mode selection; single-writer responsibility over `tier_state.json`.
- `agents/evaluator.md` — Confirmation Mode retired; T2 entry rewritten with SD/SR read-prerequisite + `E-T2-SD-UNGROUNDABLE` finding class; tier-conditioned engagement (dormant at T1; joins at T2; full at T3/T4).
- `agents/generator.md` — Phase 3.5 Self-T1 Verdict retired; T1 deliverable now hands off directly to the next-rung Evaluator.
- `agents/reflector.md` — lightweight/full mode split; Phase 3a (Digest Integrity) retired; new audit phases 2d (T3 convergence trajectory), 2e (`[T3-STALE]` + MCR volatility), 2f (tier-row contract).

**Skills (rewritten; SK-NN identifiers preserved):**
- `skills/run-tier-1/SKILL.md` (SK-25) — T1 Plan & Draft; Evaluator dormant; Generator-led; no Self-T1; no digest exception.
- `skills/run-tier-2/SKILL.md` (SK-29) — T2 Review & Revise; SD/SR read-prereq; `E-T2-SD-UNGROUNDABLE`.
- `skills/run-tier-3/SKILL.md` (SK-26) — T3 Iterate & Converge; unbounded iteration; `convergence_log.md`; terminal sign-off row → `T3_converged`.
- `skills/run-tier-4/SKILL.md` (SK-27) — T4 Finalize & Close; MCR admission gate; EG-1 / EG-7; Reflector full-mode dispatch.
- `skills/run-reflection/SKILL.md` (SK-06) — lightweight vs. full mode pattern.
- `skills/response-letter-review/SKILL.md` (SK-11) — reframed as manuscript-class on main ladder (T3R retired).
- `skills/plugin-commands/SKILL.md` (SK-23) — command table refreshed for the Lifecycle-Stage Ladder.

**Skills (retired):**
- `skills/eygp-framework-checker/SKILL.md` (SK-28) — retired under R5; migration path SK-10 `p-stage-checker`.

**Scripts (new / rewritten):**
- `scripts/migrate_v060_to_v070.py` — net-new one-shot migrator.
- `scripts/tier_state_validate.py` — rewritten to enforce 15-field schema + six-field row + 27-trigger enum + three monotonicity exemptions.
- `scripts/tier_notifications_loader.py` — rewritten for `config_version` 3.0.
- `scripts/tier_state_canonicalize.py` — header comments updated.
- `scripts/gate_threshold_tuner.py` — docstring examples updated for EG-1 repurposing + EG-7.
- `scripts/fixtures/tier_state_smoketest/{pass,block}/reviews/tier_state.json` — rewritten for the v0.7.0 shape.

**Scripts (retired → legacy/):**
- `scripts/verify_rule_digest.py` — archived consequent to Rule 1 digest exception retirement.

**Release-gate changes:**
- `scripts/release-gate.sh` Phase 0.67 rewrites the PASS/BLOCK fixture assertions for the v0.7.0 row contract.
- Phase 0.7 `py_compile` list adds `migrate_v060_to_v070.py`; drops `verify_rule_digest.py`.

## Known gaps (deferred)

- **Live-project migration sweep.** The migrator passes both smoketest fixtures (`scripts/fixtures/tier_state_smoketest/{pass,block}`); live-project migrations are user-initiated and reviewed against the migration report.
- **Convergence-metric defaults catalogue.** T3's `convergence_metric` is user-populated at T3 entry; v0.7.0 ships with no default catalogue. The v0.7.1 roadmap includes a seed catalogue keyed to paper-type (empirical / theoretical / design-research / response-letter / position).

## Lessons (for the reflection ledger)

- `L-2026-04-20-07` — lifecycle stages beat review depths. Framing rungs as stages absorbs the iterative T3 use-case (unbounded revision against a declared convergence metric) that the Staircase framing could not; the same four-rung count carries different semantics under the new frame.
- `L-2026-04-20-08` — T3 is the center of gravity. Under the Lifecycle-Stage Ladder, T3 Iterate & Converge absorbs the bulk of real work; T4 is close-out. Release-gate and Reflector dispatch weights should reflect this balance (Reflector full-mode is T4-scoped; lightweight mode is T1/T2/T3-scoped).
- `L-2026-04-20-09` — single grounding code path. Full-file reads are the universal floor; the Rule 1 tier-gated digest exception was a hallucination vector disguised as an optimization. Unifying the grounding regime at T1/T2/T3/T4 simplifies every Evaluator rule citation and removes a class of handoff-time mismatches.
- `L-2026-04-20-10` — Reflector two modes. Lightweight ad-hoc (memory-only integrity probe at T1/T2/T3) vs. full close-out (T4-scoped five-phase + audit-phase pass) is the right dispatch shape. The v0.6.0 uniform dispatch was either too heavy (at T1/T2) or too light (at T4).
- `L-2026-04-20-11` — proposals need a gatekeeper. The v0.6.0 `plugin_update_proposals.md` ledger accumulated Reflector-filed proposals without a filter; the v0.7.0 Planner three-filter gatekeeper (evidence-adequacy / non-duplication / tier-appropriateness) keeps the skill registry from drifting under reflection pressure.

---

*Populated in Phase 9; see `CHANGELOG.md` for the per-phase rollout notes and `references/TIER_PROTOCOL.md` for the authoritative protocol text.*
