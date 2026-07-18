# Implementation Strategy — Snowball-Driven Reference Architecture (v0.10.0)

> **Status.** Build-to-release strategy for the architecture defined in `docs/superpowers/plans/2026-04-26-snowball-reference-architecture.md`. No skill files, agent files, or scripts are modified by this strategy document; the strategy is the *contract* under which the implementation patches will be written and released.
>
> **Author:** Drafted under the v0.9.0 maintenance session, 2026-04-26.
> **Companion:** `2026-04-26-snowball-reference-architecture.md` (the WHAT) — this file is the HOW.
> **Substrate:** v0.9.0 → v0.10.0 (single bundled minor release).
> **Adopted parameters** (per user adjudication, 2026-04-26):
> - Branching: per-stage worktrees via `unified-superkit:using-git-worktrees`.
> - Quality cadence: full `unified-superkit:run-plugin-calibration-loop` at every stage close.
> - Version cadence: bundle all eight stages into a single v0.10.0 ship.
> - Pre-flight: Wohlin 2014 direct read resolved before S1 ships.

---

## 1. Problem Statement

The architecture plan commits the harness to eight sequenced stages (S1, S1.5, S2, S3, S4, S4.5, S5, S6), four new skills, two edits to existing skills, six wiki-coupling extensions, a SectionStateObject schema bump (16 → 18 fields), and a new trigger-enum value (30 → 31). Shipping work of this surface area into a single v0.10.0 minor release without a build-to-release strategy invites three predictable failure modes: (a) **drift accumulation**, where each stage's deviation from the architecture compounds because the next stage builds against the deviated version; (b) **rollback inability**, where a late-stage failure cannot be undone without unwinding earlier stages whose work has already been mainlined; and (c) **regression invisibility**, where each stage's local validation passes but the cross-stage integration is exercised only at the v0.10.0 RC gate, with insufficient time for fix-and-re-test before the user's release window.

This strategy commits to a build-to-release process that prevents each of those failure modes by isolation (per-stage worktrees), confidence (full calibration loop per stage close), and bounded scope (no main-line merge before stage gate passes).

## 2. Theoretical Framing — SR Model of the Build Process

The build process is itself a softgoal-driven workflow. The actors and their dependencies, in i\* SR form, are:

```
Actor: User (Joseph)
  Softgoal: ShipQuality       — the v0.10.0 release behaves at least as
                                well as v0.9.0 across every existing
                                project, and adds the new capabilities
                                without behavioural regression.
  Softgoal: ShipPredictability — the rollout completes within an
                                estimable time window with intermediate
                                checkpoints the user can inspect.
  Softgoal: RollbackSafety    — every stage close is an independently
                                shippable point; failure at stage N
                                does not block re-shipping the v0.9.0
                                state or the most recent green stage.

Actor: Implementing agent (this session, or a successor)
  Task: Per-stage worktree + branch
  Task: Per-stage calibration loop
  Task: Stage merge to integration branch
  Task: v0.10.0 RC assembly + release-gate
  Resource: unified-superkit calibration tooling
  Resource: harness scripts/release-gate.sh + 5 validation scripts
  Dependency on User: stage-close approval (the human-in-the-loop gate)

Actor: Pilot project (TBD)
  Resource: a real Ph1 / Ph2 manuscript section with claim register,
            classification.md, and ideally wiki_linked: true
  Task: end-to-end probe at every stage close
  Dependency on Implementing agent: stable interface contracts at each
            stage so the pilot's pass/fail at stage N is informative
            about stage N's correctness specifically.
```

The strategy operationalises every softgoal as a measurable gate, every task as a procedural step, and every dependency as a checkpoint requiring explicit signoff.

---

## 3. Pre-flight Stage S0 (must complete before S1 begins)

Five preconditions land before the first worktree opens. None are optional.

### 3.1 Wohlin 2014 direct read + verification log row

Resolve the inherited-tier citation flagged in §11 of the architecture plan. Two equivalent paths:

**Path A (Zotero first, per §1.5 ordering).** `mcp__zotero__zotero_add_by_doi` with the Wohlin 2014 DOI; then `mcp__zotero__zotero_get_item_fulltext` to confirm read-availability; then `mcp__zotero__scite_check_retractions` for Class 3.

**Path B (Scholar Gateway probe).** `mcp__70599628-...__semanticSearch` with `query: "Wohlin 2014 guidelines for snowballing in systematic literature studies and a replication in software engineering"` and `inferred_intent: "direct read of the methodological anchor cited inherited-tier in the snowball architecture plan"`. The returned passages provide quote-grade text for any citation in subsequent SKILL.md authoring.

Either path appends one row to `reviews/external_verification_log.md` (project-side; the harness itself does not have this file — it is a project-level artefact). The row format is the canonical Rule 7a row per `EXTERNAL_VERIFIERS.md §5`. Estimated time: 30 minutes.

**Gate.** S1 cannot open until this row exists in the pilot project's `external_verification_log.md`. The `unified-superkit:verification-before-completion` skill enforces evidence-before-claims at each stage close; the pre-flight applies the same discipline to the architecture's own load-bearing citation.

### 3.2 Pilot project selection + readiness

The pilot project must satisfy three properties: (a) it is at Ph1 (a fresh section is acceptable; an in-flight Ph1 is ideal — the new SK-NEW-A's idempotency guard is exercised by the in-flight case); (b) `wiki_linked: true` in its `CLAUDE.md` so the wiki-coupling stages have a real wiki to read against; (c) the project is owned by the user (the one running the rollout) so stage-close signoff is direct rather than mediated.

**Selection criterion.** A working list of candidate projects under the user's research portfolio is expected — the implementing agent should ask the user to nominate the pilot before S1 opens. The strategy document does not name a pilot, deliberately: nominating a specific project here would couple the strategy to a moving target. The implementing agent's first action at S1 is to confirm the pilot's identity with the user.

### 3.3 Migration-script scaffolding

The SectionStateObject schema bump (16 → 18 fields) requires a v0.9.0 → v0.10.0 migration. The script lives at `scripts/migrate_v090_to_v100_*.py`, following the existing convention (`scripts/migrate_v073_to_v074_tier_to_phase.py`, `scripts/migrate_v060_to_v070.py`, etc., all present in the repo). The script must:

1. Read each section's `phase_state.json`.
2. Set `references_initialized: true` on sections whose `references/REFERENCES.md` has at least one row in the core corpus or snowball table (heuristic: file exists and has a non-empty table); else `false`.
3. Set `last_coverage_score: null` on all sections (no historical data to backfill).
4. Append `schema_version: "0.7.4" → schema_version: "0.10.0"` to the top-level metadata if the harness retains the `schema_version` surface (per `phase_state_schema.md §1.1` v0.8.0 note that the field "remains `0.7.4` at the ledger surface until the v0.8.0 RC vocabulary roll" — v0.10.0 is the natural roll point).
5. Produce `reviews/migration_report_v090_to_v100.md` for user review per the §7 migration convention.

The script is authored at S2 (when the schema additions land) but its skeleton plus a smoke-test fixture under `scripts/fixtures/phase_state_smoketest/v090_to_v100/` are scaffolded at S0. The fixture pattern matches the existing `scripts/fixtures/phase_state_smoketest/{pass,block}/` shape.

### 3.4 `classification.md` template additions

The architecture introduces four new classification fields (`references_initialized`, `claim_coverage_threshold`, `auto_redlink_snowball`, `inherit_snowball`, `pre_seed_cap`, `red_link_cap_per_round`). Two of these are SectionStateObject fields (covered by §3.3); the rest are project-level classification fields. The Planner's classification-mode template (per `agents/planner.md` and `references/PROJECT_BOOTSTRAP.md §Step 4`) is amended in lockstep at the stage where the consuming skill ships:

- S1: `claim_coverage_threshold` (default 0.8) — read by SK-NEW-B.
- S1.5: nothing in classification.md; the dual-path mode and `pre_seed_cap` are inferred at runtime.
- S4.5: `auto_redlink_snowball` (default `false`); `red_link_cap_per_round` (default 5).
- S6: `inherit_snowball` (default `true` for `wiki_linked` projects); `pre_seed_cap` (default 10).

The classification template documentation update is part of each respective stage, not a separate S0 line.

### 3.5 v0.10.0 release-notes scaffold

Create `docs/release-notes/RELEASE_NOTES_v0.10.0.md` as an empty scaffold at S0 with §1 (one-paragraph summary placeholder), §2 (per-stage section headings with TODO markers), §3 (file-level diff table empty), §4 (validation block empty), §5 (migration / back-compat block empty). Each stage close fills in its own §2 subsection and updates §3. The §1 paragraph is finalised at the v0.10.0 RC gate. This pattern matches the v0.8.7 → v0.9.0 release-notes precedent.

### 3.6 Pre-flight gate

S0 closes when:

- `reviews/external_verification_log.md` (in the pilot project) has the Wohlin 2014 row.
- The pilot project is named and confirmed by the user.
- `scripts/migrate_v090_to_v100_<topic>.py` skeleton exists with at least the file header docstring.
- `scripts/fixtures/phase_state_smoketest/v090_to_v100/` exists with `pass/` and `block/` subdirs (empty fixture files acceptable; the fixture content is filled in at S2).
- `docs/release-notes/RELEASE_NOTES_v0.10.0.md` scaffold exists.

The `release-gate.sh` is **not** run at S0 close — there is no shippable artefact. The next gate is S1 close.

---

## 4. Per-Stage Build Cadence (applies to every S1–S6 stage)

Every stage executes the same five-step cadence. The cadence is the procedural backbone; stage-specific work is layered on top per §5.

### 4.1 Step 1 — Open worktree

```bash
# From harness root on main (assumed clean).
git worktree add ../co-author-harness-S<N> -b stage/v0.10.0-S<N>
cd ../co-author-harness-S<N>
```

The worktree is named `../co-author-harness-S<N>` (sibling of the main checkout), branch `stage/v0.10.0-S<N>`. Worktrees are sequenced: `S<N>` branches off the **prior closed stage's** branch HEAD (not main), so each stage builds against the exact state the prior stage shipped. The `unified-superkit:using-git-worktrees` skill governs this step verbatim.

### 4.2 Step 2 — Implement stage-specific work

Per §5. The implementing agent uses `unified-superkit:executing-plans` (single-session) or `unified-superkit:subagent-driven-development` (parallel sub-agents for independent tasks within the stage) as the work-pattern skill. `unified-superkit:test-driven-development` applies to every Python script (migration scripts, validation extensions); markdown skills are TDD-exempt but their description-length and frontmatter-parity gates run on every save.

### 4.3 Step 3 — Stage-local validation

```bash
# Inside the worktree.
python scripts/skill-check.py             # frontmatter + registry parity
python scripts/version-check.py           # version-string consistency
python scripts/catalog-check.py           # README + commands/ parity
python scripts/path-hygiene-check.py      # absolute-path leakage
python scripts/phase_state_validate.py    # SectionStateObject shape
# Stage-specific scripts as appropriate, e.g. for S2:
python scripts/migrate_v090_to_v100_<topic>.py --dry-run scripts/fixtures/phase_state_smoketest/v090_to_v100/pass/
```

Any failure here is a hard stop; the implementing agent must fix-in-place before proceeding.

### 4.4 Step 4 — Full plugin-calibrator loop (per user-adopted cadence)

```bash
# Five-stage calibration loop per unified-superkit:run-plugin-calibration-loop:
#   test → analyze → calibrate/fix → retest → recalibrate
```

The calibration loop is invoked via the `unified-superkit:run-plugin-calibration-loop` skill, parameterised against the worktree path. The loop produces `artifacts/efficiency/<timestamp>/report.json` in the worktree. The economics axis must show:

- `projected_cost_per_invocation_usd`: ≤ v0.9.0 baseline ($5.87) **at the close of every stage**. Stages that add new skills will increase the artefact count and may transiently raise cost; the calibrator's `assumed_invocations_per_run` retune (or a follow-up role_overrides edit) must hold the projection at or below the baseline before stage close. **An increase above the baseline is a stage-close blocker.**
- `subagent_dispatch_multiplier`: ≤ 9.57 (the v0.9.0 actual). New skills introduce dispatch references; the per-stage calibrator run measures whether the multiplier creep is acceptable.
- Quality axis: 0 BLOCKERs, 0 MAJORs.
- Speed axis: chain depth ≤ 15 (the threshold per `.plugin-efficiency.json`).

In addition to the calibrator's own loop, run the semantic-review pass at major stages (S2, S4, S5):

```bash
# unified-superkit:run-semantic-review dispatches:
#   md-reviewer (markdown skill bodies vs. their stated contracts)
#   promise-reviewer (frontmatter description vs. body delivery)
#   orchestrator-critic (dispatch-graph audit)
```

Semantic-review verdicts are advisory at S1, S1.5, S3, S4.5, S6; binding at S2, S4, S5 (the structural-change stages).

### 4.5 Step 5 — Stage close: merge + tag

```bash
# From the worktree.
git checkout main
git merge --no-ff stage/v0.10.0-S<N>     # preserve stage boundary in history
git tag v0.10.0-S<N>                      # immutable stage marker
git worktree remove ../co-author-harness-S<N>
```

The merge is `--no-ff` so the per-stage branch boundary is preserved in main's commit graph (rollback granularity per `unified-superkit:finishing-a-development-branch`). The tag is the rollback target if a later stage fails. The next stage's worktree branches off this tag.

A stage-close release-notes update is appended to `docs/release-notes/RELEASE_NOTES_v0.10.0.md` §2 in the same commit that closes the stage.

---

## 5. Stage-by-Stage Sequencing

Each stage's content is specified in the architecture plan §6.1–§6.8. The implementation parameters (key files, parallelism opportunities, estimated effort) are below. Effort estimates are session-time estimates, not wall-clock — they assume the implementing agent is working without interruption.

### 5.1 Stage S1 — `seed-snowball-discovery` (SK-NEW-A, no harness wiring)

**Worktree:** `../co-author-harness-S1`, branched off main.

**Key files created:** `skills/seed-snowball-discovery/SKILL.md`; `commands/seed-snowball-discovery.md` (UI shim per v0.9.0 convention); `references/SKILL_REGISTRY.md` updated with SK-32 entry (the next available SK-NN id; SK-32 was used at v0.9.0 for `run-generator-session` per `2026-04-25-run-generator-session.md`, so SK-NEW-A becomes **SK-33**).

**Parallelism:** none — the skill is the only deliverable. `unified-superkit:executing-plans` single-session pattern.

**Stage-close gate:** all five validation scripts pass; full calibrator loop passes; pilot project runs `/seed-snowball-discovery <pilot-section>` end-to-end and produces a populated `references/REFERENCES.md` with three tables and ≥1 snowball iteration in `reviews/snowball_log.md`.

**Effort:** ~3 hours (SKILL.md authoring + shim + registry + pilot probe).

### 5.2 Stage S1.5 — Wiki-graph substrate + write-back inside SK-NEW-A

**Worktree:** `../co-author-harness-S1.5`, branched off `v0.10.0-S1`.

**Key files modified:** `skills/seed-snowball-discovery/SKILL.md` (the iteration step rewrite per architecture §5.5.1; the in-loop wiki write-back per §5.5.2; the dual-path access contract per §5.5.6).

**Parallelism:** the three sub-changes (graph traversal, write-back, dual-path) are *not* independent — they share the SKILL.md body and must land in a single coherent edit. Single-session execution.

**Stage-close gate:** as above, plus the pilot project's pilot section is re-run; the snowball log shows non-zero `graph_local_admits` (assuming the pilot's wiki has any relevant graphify nodes); the wiki source-page count grows by exactly the snowball-admission count; `wiki_access_mode` is logged correctly across all three explicit settings (`auto`, `filesystem`, `mcp_fastpath`).

**Effort:** ~4 hours (the iteration rewrite is the load-bearing change; the dual-path detection is non-trivial; the in-loop write-back hooks into SK-15's stub-template logic and needs careful testing).

### 5.3 Stage S2 — Phase-1 wiring (Edit-1) — full enumeration per architecture §6.0 coupling checklist

**Worktree:** `../co-author-harness-S2`, branched off `v0.10.0-S1.5`. (In-place stage branch in Cowork-Windows environments per the S1 deviation precedent.)

**Key files modified — document layer (the original §5.3 scope):**
- `skills/run-phase-1/SKILL.md` (insert Step 4.5 with OR-conjunctive outer guard per architecture §5.2 Edit-1)
- `references/phase_state_schema.md` (add `references_initialized` field to §2; add trigger 31 `seed_snowball_signed` to §3.1)
- `scripts/migrate_v090_to_v100_snowball_fields.py` (flesh out S0 skeleton; smoketest fixtures under `scripts/fixtures/phase_state_smoketest/v090_to_v100/`)

**Key files modified — orchestration co-mutations (added per architecture §6.0 coupling checklist; surfaced at v0.10.0 S2 close 2026-04-27):**
- `agents/planner.md` (register SK-NEW-A dispatch responsibility at the Planner phase that mirrors run-phase-1 §3 Step 4.5's placement — Phase 4 / 4.5 / 4.6 region, NOT Phase 5; three-outcome-branch handling authoritative here)
- `references/phase_notifications.yaml` (declare `W-SNOWBALL-PRECONDITION-UNMET` and `E-SNOWBALL-MID-RUN-FAILURE` codes in §4)
- `scripts/pre_phase_advance_check.py` (add `seed_snowball_signed` to `VALID_TRIGGERS`; add non-blocking advisory clause for `references_initialized: false` at Ph1→Ph2 advance)
- `skills/run-phase-2/SKILL.md` (insert non-blocking Step 0.5 placeholder that re-tests the gate at Ph2 entry; full Ph2-side dispatch defers to S3/S4)

**Parallelism:** the document-layer files (run-phase-1, schema, migration) are independent and parallelisable per `unified-superkit:dispatching-parallel-agents` (3 sub-agents). The orchestration co-mutations have **interdependencies** that preclude full parallelisation: planner.md placement constrains how run-phase-1 references it; partial-failure halt-vs-continue must be reconciled across both files; Step 0.5 in run-phase-2 must reference the W-* code declared in phase_notifications.yaml. Recommended: dispatch document-layer in parallel; sequence orchestration co-mutations.

**Stage-close gate:** five validation scripts (skill-check, version-check, catalog-check, path-hygiene-check; phase_state_validate is N/A in meta-pilot context — harness has no project-side phase_state.json); migration script `--validate` returns exit 0 on all 9 smoketest fixtures (5 pass + 4 block); plugin-calibrator economics axis pass with feature-attributed deltas tolerated; **semantic-review (binding at S2)** returns CLEAR — md-reviewer reads `run-phase-1`, `run-phase-2`, AND `2026-04-26-snowball-reference-architecture.md` (the architecture doc itself becomes a review target at S2 per the §6.0 coupling-checklist amendment); promise-reviewer reads `run-phase-1` + `run-phase-2` frontmatter; orchestrator-critic reviews the dispatch graph including the four co-mutations.

**Effort:** ~8-12 hours (5h document layer + 4-6h orchestration co-mutations + ~30 min architecture/strategy doc amendments). The original ~5h estimate did not anticipate the §6.0 coupling-checklist scope.

### 5.4 Stage S3 — `claim-coverage-audit` (SK-NEW-B, no Ph2 wiring)

**Worktree:** `../co-author-harness-S3`, branched off `v0.10.0-S2`.

**Key files created:** `skills/claim-coverage-audit/SKILL.md`; `commands/claim-coverage-audit.md`; `references/SKILL_REGISTRY.md` SK-34 entry.

**Parallelism:** none.

**Stage-close gate:** as above; pilot project runs `/claim-coverage-audit` against a Ph1-completed section and emits a four-set `claim_coverage_*.md`; the score is reproducible across two consecutive runs (deterministic claim extraction).

**Effort:** ~3 hours.

### 5.5 Stage S4 — Phase-2 wiring + `extend-snowball-incremental` (SK-NEW-C)

**Worktree:** `../co-author-harness-S4`, branched off `v0.10.0-S3`.

**Key files created:** `skills/extend-snowball-incremental/SKILL.md`; `commands/extend-snowball-incremental.md`; `references/SKILL_REGISTRY.md` SK-35 entry.

**Key files modified:** `skills/run-phase-2/SKILL.md` (insert Step 0.5; amend §9 `What this stage does NOT do`); `references/phase_state_schema.md` (add `last_coverage_score` field).

**Parallelism:** SK-NEW-C SKILL.md and the run-phase-2 edit can be authored in parallel via two sub-agents; the schema doc is a third parallel task. `unified-superkit:dispatching-parallel-agents`.

**Stage-close gate:** as above, plus full semantic-review (binding at this stage); pilot project runs Ph2 with a section that has at least one ungrounded claim, and SK-NEW-C lands a resolving source within the round; the auto-dispatch chain SK-NEW-B → SK-NEW-C executes correctly.

**Effort:** ~6 hours (Ph2 dispatch logic is sensitive; the chain is exercised end-to-end).

**Binding decisions (S4 surface; SOT at `agents/planner.md §Phase 3.8`; architecture mirrors landed in v0.10.1 hardening per `CHANGELOG.md` "Deferred to v0.10.1+").** S4 implementation surfaced four Planner-side decisions whose authoritative spec lives in `agents/planner.md §Phase 3.8` rather than in the consumed `run-phase-2/SKILL.md §4 Step 0.5` (per architecture §6.0 row 4 single-source-of-truth):

1. **Four-outcome handler** for SK-NEW-B `claim-coverage-audit` dispatch — `CLEAN` / `BELOW_THRESHOLD` / `AUDIT_FAILED` / `IDEMPOTENT_HIT`. IDEMPOTENT_HIT is clean-exit-equivalent (no notification, prior `last_coverage_score` preserved); the asymmetric notification treatment vs. AUDIT_FAILED is the load-bearing rationale for four outcomes rather than three. Architecture mirror: §5.2 Edit-2.
2. **Inline parallel-fanout cap** of 8 SK-NEW-C invocations per Ph2 cycle (`max_parallel_extend_snowball`, default 8 in `reviews/classification.md`; surfaced at S4.5 R2). Excess uncovered claims rank by Rule-7a-criticality and defer with non-blocking `W-COVERAGE-FANOUT-CAPPED`. Architecture mirror: §7 R-14.
3. **Cross-round coverage-regression hook** consuming `last_coverage_score` (`coverage_regression_floor`, default 0.05; surfaced at S4.5 R2). Non-gating; surfaces `W-COVERAGE-REGRESSION-OBSERVED` on `prior_score - new_score > regression_floor` for user adjudication. Consumer wiring lands at S4.5 R2; runs at every Ph2 entry that lands outcome (i) or (ii); skipped on outcomes (iii) and (iv). Architecture mirror: §5.2 Edit-2 closing prose.
4. **Halt-vs-continue asymmetry** between Phase 3.7 outcome (iii) HALT (SK-NEW-A substrate failure — REFERENCES.md is the substrate the Generator drafts against, partial population is worse than none) and Phase 3.8 outcome (iii) CONTINUE (SK-NEW-B advisory failure — the audit signal informs downstream reads but is not the substrate, missing it widens the verification surface but does not corrupt anything). Architecture mirror: §6.0 closing paragraph (canonical example for row 4 of the coupling checklist).

### 5.6 Stage S4.5 — Wiki synthesis fast-path + red-link triggers

**Worktree:** `../co-author-harness-S4.5`, branched off `v0.10.0-S4`.

**Key files modified:** `skills/claim-coverage-audit/SKILL.md` (synthesis-alignment fast-path per architecture §5.5.3); `skills/retrofit-concept-grounding/SKILL.md` (red-link auto-trigger per §5.5.4).

**Parallelism:** the two SKILL.md edits are independent; two parallel sub-agents.

**Stage-close gate:** as above, plus pilot project's `wiki/syntheses/` is exercised — at least one drafted claim resolves via synthesis alignment and is annotated `[via-synthesis: <key>]`; the red-link auto-trigger fires and is rate-limited at `red_link_cap_per_round`.

**Effort:** ~4 hours.

**S4 carry-overs (R2; surface for S4 binding decisions (b) and (c)).** S4.5 R2 surfaces in `reviews/classification.md` the two parameters that materialise S4 binding decisions (b) inline parallel-fanout cap and (c) cross-round coverage-regression hook (see §5.5 binding-decisions paragraph and architecture §6.6 R2 enumeration): `max_parallel_extend_snowball` (default 8) and `coverage_regression_floor` (default 0.05). The consumer wiring for the regression hook lands here in `agents/planner.md §Phase 3.8` (delivers the S4 round-2 fix's "S4.5-deferred consumer" promise; introduces `W-COVERAGE-REGRESSION-OBSERVED` per the baseline code-registration contract). The `extend_classification_md` migration step populates both defaults during v0.9.0 → v0.10.0 migration so post-migration projects always carry the explicit values.

### 5.7 Stage S5 — Documentation amendments

**Worktree:** `../co-author-harness-S5`, branched off `v0.10.0-S4.5`.

**Key files modified:** `references/EXTERNAL_VERIFIERS.md` §1.5 (named-executor lines per architecture §5.6); `references/AGENT_ORCHESTRATION.md` §8.6 (Coupling E.1 retired-and-re-registered note); `references/SKILL_REGISTRY.md` (final SK-NEW-A/B/C/D registrations).

**Parallelism:** three documentation files; three parallel sub-agents.

**Stage-close gate:** documentation-only, but full semantic-review (binding at S5); md-reviewer must confirm every named cross-reference resolves; promise-reviewer must confirm frontmatter descriptions match the `plugin-commands` SKILL catalog.

**Effort:** ~2 hours.

### 5.8 Stage S6 — `inherit-snowball-from-wiki` (SK-NEW-D)

**Worktree:** `../co-author-harness-S6`, branched off `v0.10.0-S5`.

**Key files created:** `skills/inherit-snowball-from-wiki/SKILL.md`; `commands/inherit-snowball-from-wiki.md`; `references/SKILL_REGISTRY.md` SK-36 entry.

**Key files modified:** `skills/seed-snowball-discovery/SKILL.md` (insert SK-NEW-D pre-seed dispatch as the first sub-step of the seed phase; conditional on `inherit_snowball: true`).

**Parallelism:** SK-NEW-D + the seed-snowball-discovery edit can be done in parallel by two sub-agents.

**Stage-close gate:** as above; pilot project's wiki has at least two prior projects' communities; SK-NEW-D pre-seed yields ≥1 admission; on a clean wiki (no adjacent communities), SK-NEW-D no-ops without modifying SK-NEW-A's seed_set.

**Effort:** ~4 hours.

### 5.9 Cumulative effort

Sum: ~31 hours of focused implementation time, plus pilot-probe time at each gate (~30 min each, total ~4 hours). Including the calibration loops (~20 min each), semantic reviews (~30 min at S2/S4/S5), and stage-close release-notes updates (~15 min each), total session time is **~38–42 hours**. At a sustainable cadence of 4 focused hours per day, this is roughly **two weeks of wall-clock time**; at 8 hours per day, one week.

---

## 6. Cross-Stage Integration

### 6.1 The pilot section probe

A single pilot section (selected at S0) is the integration vehicle. After every stage close, the pilot section is re-run from a known starting state (a checkpoint commit captured at S0). The pilot's `phase_state.json`, `references/REFERENCES.md`, `manuscript/<section>.md`, and `reviews/` artefacts are diffed against the prior stage's pilot output. **A diff that exceeds the stage's declared scope is a regression.**

This is the harness analogue of regression testing without an automated CI; the user is the test runner. The probe is documented per stage in `docs/release-notes/RELEASE_NOTES_v0.10.0.md §4 (validation)` as the rollout proceeds.

### 6.2 Regression matrix

Maintained as `reviews/v0.10.0_regression_matrix.md` (project-side, not harness-side; the harness ships the *pattern*, the project fills in the rows). Columns: stage, pilot section state pre-stage, pilot section state post-stage, diff summary, regression Y/N, mitigation. Rows accumulate with each stage close. The matrix is the user-readable summary that proves the rollout did not break anything between stages.

### 6.3 v0.10.0 RC integration

After S6 closes, a final integration run is conducted on `main` (post-merge). The RC integration is a **clean-room replay**: a fresh project is bootstrapped from scratch, taken through Ph1 → Ph2 with all eight stages active, against a real wiki and real Class 1 verifiers. Any failure here is a v0.10.0-blocker; the failing stage is identified and a hot-fix patch issues against the corresponding stage tag.

---

## 7. Quality Gates — Concrete Commands

The harness's own gates are reused; no new gates are introduced.

### 7.1 Per-stage gate (every S<N> close)

```bash
cd <worktree>
python scripts/skill-check.py             && \
python scripts/version-check.py           && \
python scripts/catalog-check.py           && \
python scripts/path-hygiene-check.py      && \
python scripts/phase_state_validate.py    && \
echo "--- five-script gate PASS ---"
# Calibrator loop:
PYTHONPATH=/sessions/.../mnt/.remote-plugins/plugin_01Q7iXHRyKL2TPd9xCgb4j2p \
  python3 -c "from plugin_calibrator.efficiency import audit_plugin, write_report; \
              from pathlib import Path; \
              r = audit_plugin(Path.cwd().resolve()); \
              write_report(Path.cwd().resolve(), r)"
# (CLI workaround per the v0.9.0 truncated-main bug; see RELEASE_NOTES_v0.9.0_addendum.md §Method)
```

The calibrator output is read by an inspector script (to be written at S0, scaffolded as `scripts/check-stage-economics.py`) that asserts the four conditions listed in §4.4. A red on any condition is a stage-close blocker.

### 7.2 Stage-major gate (S2, S4, S5 — semantic review binding)

```bash
# Dispatched via unified-superkit:run-semantic-review against the changed-files set:
#   md-reviewer       — markdown body vs. declared contract
#   promise-reviewer  — frontmatter description vs. body delivery
#   orchestrator-critic — dispatch graph
```

Verdict aggregation: any md-reviewer or promise-reviewer MAJOR is a blocker; orchestrator-critic findings are advisory unless they concern the changed dispatch logic, in which case binding.

### 7.3 v0.10.0 RC gate

```bash
bash scripts/release-gate.sh --ship-intent
# Steps 1-13 per the script header.
# Additional v0.10.0-specific:
python scripts/migrate_v090_to_v100_<topic>.py --validate scripts/fixtures/phase_state_smoketest/v090_to_v100/
# Pilot integration replay (per §6.3) — manual.
```

The `--ship-intent` flag activates the calibrator placeholder block (`input_tokens_per_second` placeholder check) per `release-gate.sh §10a`. v0.10.0 must pass this with a real measured `input_tokens_per_second` value, not the 2000 placeholder. This was settled at v0.8.0 with the 16,897.1 figure (per `.plugin-efficiency.json _comment`); v0.10.0 inherits the value unless the calibrator's measurement protocol is re-run.

---

## 8. Versioning, CHANGELOG, Release Notes

### 8.1 Single v0.10.0 ship

Per user adjudication. v0.9.0 → v0.10.0 is a minor-version bump (additive: new skills, new fields, new triggers; no surface retirements; no breaking changes to existing skills' behaviour from a project's perspective). The migration script handles the `phase_state.json` schema bump deterministically.

### 8.2 CHANGELOG cadence

Each stage close appends one bullet to `CHANGELOG.md` under a `## v0.10.0 (unreleased)` heading. The heading is finalised to `## v0.10.0 — YYYY-MM-DD` at the v0.10.0 RC gate. This matches the v0.8.x → v0.9.0 cadence the user shipped under.

### 8.3 Release notes

Single file: `docs/release-notes/RELEASE_NOTES_v0.10.0.md`, scaffolded at S0, accumulated stage-by-stage. Final §1 (one-paragraph summary) is authored at the RC gate. The release notes have eight §2 subsections (one per stage) plus a summary table of all SK-NEW-A/B/C/D registrations.

### 8.4 Plugin manifest

`.claude-plugin/plugin.json` `version` field is bumped at the v0.10.0 RC gate, not per stage. Stage tags (`v0.10.0-S<N>`) carry the `version: "0.10.0"` value across all eight stages; the plugin is technically v0.10.0-in-development across the rollout. Users installing during the rollout from a stage tag get the in-development plugin and should be cautioned (a `v0.10.0-RC` annotation in the plugin description for the duration of the rollout).

### 8.5 The `description` field

Per `release-gate.sh` step 1 and the v0.9.0 contract, the `plugin.json.description` must be ≤ 400 characters and the empirical-distribution probe must report OK. v0.10.0 description should be re-authored at the RC gate to surface the snowball pipeline as the headline feature. Draft text (subject to length-trim at RC):

> "Research-writing harness — Ph1–Ph4 lifecycle ladder, four-agent loop, GROUNDING_PROTOCOL Rule 7a chain-of-verification. v0.10.0 adds snowball-driven reference scaffolding: SK-NEW-A seeds and saturates the corpus at Ph1, SK-NEW-B audits claim coverage at Ph2, SK-NEW-C extends incrementally on uncovered claims, SK-NEW-D inherits from peer-LLM-wiki communities. Run `/plugin-commands` for the slash catalog."

The string above is 478 chars and will need a trim. Final length-tune at RC.

---

## 9. Rollback / Abort Criteria

### 9.1 Per-stage abort

A stage is aborted (worktree deleted, branch deleted, no merge to main) if any of:

- The five-script gate red.
- The calibrator economics axis shows `projected_cost_per_invocation_usd > $5.87` and the role_overrides retune cannot restore it within the stage's effort budget × 1.5.
- The semantic-review (at S2/S4/S5) returns a MAJOR on the changed surface.
- The pilot probe regresses against the prior stage's output beyond the stage's declared scope.

Aborted stage's worktree is removed; the implementing agent re-plans and re-opens a fresh worktree.

### 9.2 Mid-rollout rollback to a prior stage

If a stage close exposes a defect in a prior stage (cross-stage integration revealed only at the integration probe), the rollback target is the prior stage's tag (`v0.10.0-S<N-1>`). Rollback procedure:

```bash
git checkout main
git reset --hard v0.10.0-S<N-1>     # destructive; only acceptable before any v0.10.0 user has installed
git push --force-with-lease         # if the stage closes have already been pushed
```

The defective stage and all subsequent stages re-implement against the rolled-back state. This is the cost of the bundled-ship strategy: any rollback unwinds work.

### 9.3 Full v0.10.0 abort

If the v0.10.0 RC gate (§7.3) fails irrecoverably, the v0.10.0 cut is abandoned. Two paths:

**Path A — patch v0.9.x.** Cherry-pick the safe stages' changes back to a `v0.9.x` series (e.g., v0.9.1 ships the SK-NEW-A skill manually-invokable; v0.9.2 ships SK-NEW-B; etc.). This is the v0.9-series rescue; it shifts the version cadence from Bundle to Staged ex post.

**Path B — reset to v0.9.0.** Force-reset main to v0.9.0; close the v0.10.0 plan as failed; learn-and-replan. The architecture plan is preserved but no v0.10.0 ships.

The strategy commits to neither path in advance — the choice is made at abort-time based on which stages were green and which were red.

### 9.4 The user's standing override

The user (Joseph) has standing authority to abort the entire rollout at any stage close, for any reason, without justification. A stage close is a checkpoint, not a commitment to continue. The strategy's worktree pattern means an abort-here-and-now leaves main on the most-recent green stage tag with no cleanup needed.

---

## 10. Implementation-Time Risk Register (distinct from architecture risks)

Architecture risks (R-1 through R-13 in the architecture plan §7) are about the deployed system. The risks below are about the build-to-release process itself.

| ID | Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- | --- |
| IR-1 | Stage scope creep — a stage absorbs work from the next stage to "save time" | Medium | High (loses the per-stage-shippability invariant; rollback granularity collapses) | Per-stage scope is the architecture plan §6 text verbatim; the implementing agent does not modify scope without re-planning the strategy. The `unified-superkit:executing-plans` skill enforces task-by-task discipline. |
| IR-2 | Calibrator economics axis fails at S1.5 because the wiki write-back stubs inflate the artefact count | Medium | Medium (stage-close blocker; needs role_overrides retune within S1.5) | Wiki stubs land under `<wiki_path>/wiki/sources/`, not under the harness's own `skills/` — they do not count against the harness's artefact_count. Verify this assumption at S1.5 entry; if wrong, retune `assumed_invocations_per_run` to absorb the count growth. |
| IR-3 | Semantic-review verdict is unstable across runs — md-reviewer flags different MAJORs on consecutive runs of the same skill | Low | Medium (stage close blocked by reviewer noise) | Run semantic-review twice on stage close; treat any finding present in both runs as binding, single-run findings as advisory. The unified-superkit calibration loop already includes a similar deterministic-vs-probabilistic distinction. |
| IR-4 | The pilot project is unavailable mid-rollout (user is not at this machine; project file disappears) | Low | High (stage probes cannot complete) | At S0, the pilot project's identity is recorded in the strategy's `pilot_record.md` (a project-side file); the strategy commits to running with at most one pilot change mid-rollout, which forces a regression-matrix re-baseline but is recoverable. A second-choice pilot is named in the same record. |
| IR-5 | Worktree hygiene: orphaned worktrees, orphaned branches, ambiguous HEAD | Low | Low (annoying, recoverable) | At every stage close, run `git worktree list` and `git branch -av` to confirm only main + the active stage's worktree+branch are live. The `unified-superkit:using-git-worktrees` skill includes the cleanup discipline. |
| IR-6 | The Wohlin 2014 direct read at S0 surfaces a contradiction with the Barros-Justo 2021 saturation figures (i.e., Wohlin 2014 reports a different ε default that the architecture cited via Barros-Justo) | Low | Medium (forces a saturation-criterion revision in the architecture plan; cascades to SK-NEW-A's default) | The architecture plan explicitly anchors ε on Barros-Justo's empirical trace, not on Wohlin's recommendation; a Wohlin-vs-Barros-Justo divergence is documentary, not contradictory, and is logged in the architecture plan's §11 citation-provenance disclosure. The default remains Barros-Justo's; Wohlin's recommendation, if different, becomes an alternative documented in `classification.md` for project-side adoption. |
| IR-7 | Calibrator CLI truncation bug (per `RELEASE_NOTES_v0.9.0_addendum.md`) is unfixed at the unified-superkit side; every stage's calibrator invocation goes through the audit_plugin/write_report direct call workaround | Medium | Low (extra two lines of Python per invocation) | Strategy adopts the workaround verbatim (§7.1); a side-bar issue is filed against unified-superkit asking the maintainer to ship the missing tail of `efficiency.py:main`. The fix-from-our-side is minor; we don't block the v0.10.0 rollout on it. |
| IR-8 | A stage close lands on a Friday; the next stage's worktree opens on a Monday with stale memory of the prior stage's context | Medium | Low | The stage-close release-notes update is the recovery surface — it's the implementing agent's note-to-self for the next stage's context. The `session-handoff` skill is the canonical longer-form rescue if context-loss is severe. |

---

## 11. Sequencing Chart

```
S0 (pre-flight, ~1 hour)
  ├── Wohlin 2014 read          ─┐
  ├── Pilot selection            ├─→ all four must close
  ├── Migration scaffold         │
  ├── Release-notes scaffold     ─┘
  │
  ▼
S1 — SK-NEW-A SKILL.md (worktree off main, ~3h)
  │
  ▼
S1.5 — Wiki-graph + write-back (worktree off S1, ~4h)
  │
  ▼
S2 — Phase-1 wiring + migration script (worktree off S1.5, ~5h, **semantic-review binding**)
  │
  ▼
S3 — SK-NEW-B SKILL.md (worktree off S2, ~3h)
  │
  ▼
S4 — Phase-2 wiring + SK-NEW-C (worktree off S3, ~6h, **semantic-review binding**)
  │
  ▼
S4.5 — Synthesis fast-path + red-link triggers (worktree off S4, ~4h)
  │
  ▼
S5 — Documentation amendments (worktree off S4.5, ~2h, **semantic-review binding**)
  │
  ▼
S6 — SK-NEW-D + SK-NEW-A wiring (worktree off S5, ~4h)
  │
  ▼
v0.10.0 RC integration (clean-room replay on main, ~3h)
  │
  ▼
v0.10.0 ship (release-gate.sh --ship-intent, manifest version bump, .zip build, tag)
```

The graph is linear by design — per-stage worktrees branch off the prior closed stage, not main, so parallelism within a stage is the only parallelism available. Cross-stage parallelism (e.g., S3 and S1.5 in parallel) was rejected because the SectionStateObject schema bump at S2 mediates between them and a parallel approach would force a costly merge-conflict pass.

---

## 12. v0.10.0 RC Validation (definitive ship gate)

The v0.10.0 RC validation is the union of every stage's validation plus three integration-only checks:

**Stage-aggregate.** Every stage tag (`v0.10.0-S1` through `v0.10.0-S6`) carries a green per-stage gate (§7.1) record in `docs/release-notes/RELEASE_NOTES_v0.10.0.md §4`. Re-running the per-stage gate on the merged main HEAD must reproduce green on all eight; a stage gate that was green at stage close but is red on main HEAD is a cross-stage integration regression and is a v0.10.0 blocker.

**Clean-room replay.** A fresh project is bootstrapped from scratch on a clean machine (or a clean worktree off main) and taken through Ph1 → Ph2 with all eight stages active. The pilot's regression matrix from §6.2 should reproduce; deviations are investigated.

**Migration round-trip.** A v0.9.0 `phase_state.json` from a real prior project is migrated forward via `scripts/migrate_v090_to_v100_<topic>.py`, validated under `phase_state_validate.py`, and the resulting state is round-tripped (forward-migrated, then read by the v0.10.0 Planner, then written, then re-read). The round-trip must be a no-op modulo the new fields. Round-trip failure is a v0.10.0 blocker.

**Release-gate.sh.** `bash scripts/release-gate.sh --ship-intent` returns OK on every step including the calibrator economics gate (step 10a) at the user's measured `input_tokens_per_second` value (16,897.1 inherited from v0.8.0 unless re-measured).

**Description-length probe.** The empirical-distribution probe (release-gate.sh step 2) measures the v0.10.0 `plugin.json.description` against the peer-plugin distribution and reports OK or WARN. BLOCKER on description length is a v0.10.0 blocker.

When all five validation gates pass, the v0.10.0 ship proceeds: bump `plugin.json.version` to `"0.10.0"`, finalise `CHANGELOG.md` heading and `RELEASE_NOTES_v0.10.0.md §1`, run `release-gate.sh` once more for the bundled `.zip`, tag `v0.10.0` on main, push.

---

## 13. Out of Scope (deliberately deferred to post-v0.10.0)

- **Automated CI on the harness repo.** The strategy assumes manual gate execution by the implementing agent. CI integration is a separate workstream.
- **Cross-project pilot fleet.** A single pilot is the integration vehicle for v0.10.0. A fleet of pilots (validating the snowball pipeline against multiple disciplines simultaneously) is a v0.11.0 candidate.
- **Calibrator schema tri-tier extension** (per `RELEASE_NOTES_v0.9.0_addendum.md §F4/F8 verdict`). Not required for v0.10.0; F4/F8 conservative-keep is honoured throughout.
- **Coupling E.3 (`graph-contradiction-sweep`).** Architecture plan §9 explicitly out-of-scope; no change here.
- **`/llm-wiki-query` MCP plugin authoring.** The dual-path contract (§5.5.6 of the architecture) supports the MCP fast-path *if available*; whether the user installs the optional `llm-wiki` MCP is a separate decision orthogonal to the v0.10.0 ship.

---

## 14. Authorship and Provenance

Drafted under the v0.9.0 maintenance session, 2026-04-26. The strategy's parameters were adopted by user adjudication on 2026-04-26: per-stage worktrees, full calibration loop per stage close, single bundled v0.10.0 ship, Wohlin 2014 read before S1.

**Provenance.** Tooling references (`scripts/release-gate.sh`, the five validation scripts, the unified-superkit calibration and worktree skills, the semantic-review skill, the migration-script naming convention) are grounded in direct file reads against the harness's `scripts/` and the unified-superkit's `skills/` in this session — not from training memory. The harness's own GROUNDING_PROTOCOL Rule 1 (read-before-cite) applies to this strategy document as it does to any artefact: every command-line invocation in §7 was either read verbatim from `release-gate.sh` or constructed from the script-level `argparse` definitions also read this session. The unified-superkit skill names (`run-plugin-calibration-loop`, `run-semantic-review`, `using-git-worktrees`, `executing-plans`, `subagent-driven-development`, `dispatching-parallel-agents`, `verification-before-completion`, `finishing-a-development-branch`, `test-driven-development`) are listed verbatim from the session's available-skills register.

The eight-stage cadence and effort estimates are this strategy's contribution; they are not extracted from any prior plan.
