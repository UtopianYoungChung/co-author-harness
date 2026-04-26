<!-- scholar-gateway-contract: v0.1 -->

# Release Notes — co-author-harness-claude v0.10.0

**Release date:** TBD (pending RC gate)
**Theme:** **Snowball-driven reference scaffolding** for Phase 1 / Phase 2 of the Lifecycle-Phase Ladder, with five wiki-coupling deepenings that materialise the previously-unimplemented Coupling E.1 (`graph-read-at-planner`).
**Verdict:** TBD (pending RC gate)
**Status:** SCAFFOLD — Stage S0 deliverable. Sections below carry `<!-- TODO@SX -->` markers indicating which stage fills each subsection. The §1 one-paragraph summary is authored at the v0.10.0 RC gate after all stages close.

---

## 1. One-paragraph summary

<!-- TODO@RC: Author at v0.10.0 RC gate after all stages close. -->
<!-- Draft slot for the headline summary. Architecture lives in:
     docs/superpowers/plans/2026-04-26-snowball-reference-architecture.md
     Strategy lives in:
     docs/superpowers/plans/2026-04-26-snowball-implementation-strategy.md -->

## 2. Stage-by-stage rollout

### Stage S0 — Pre-flight
<!-- TODO@S0-close: Fill in once S0 closes. Should record:
     - Wohlin 2014 verification (Zotero key FXJ6M8ED, DOI 10.1145/2601248.2601268)
     - Pilot project nomination
     - Migration script skeleton location
     - This release-notes scaffold creation date
     - Any deviation from the strategy's S0 spec. -->

### Stage S1 — Discovery layer skill (SK-NEW-A `seed-snowball-discovery`)

**Closed:** 2026-04-26 on branch `stage/v0.10.0-S1` (in-place stage branch — see deviation note at §5).

**Files landed:**
- `skills/seed-snowball-discovery/SKILL.md` — frontmatter description 413 chars (≤500 WARN threshold); body 246 lines covering grounding basis, preconditions with no-op reason codes, three-phase procedure (seed/iterate/verify) with the graph-substrate variant pseudocode, in-loop wiki write-back contract, dual-path access contract (filesystem / mcp_fastpath / auto), saturation criterion (ε = 0.05 default; field-conditioned overrides), seven failure modes, eight not-doing rules, sibling-skill register.
- `commands/seed-snowball-discovery.md` — UI loadability shim per v0.9.0 convention.
- `references/SKILL_REGISTRY.md` — SK-33 entry registered.
- `skills/plugin-commands/SKILL.md` — Command catalog row + Command routing entry added.
- `README.md` — skill count 28 → 29.
- `.plugin-efficiency.json` — `seed-snowball-discovery` registered as `executor` in `role_overrides`; baseline annotations for two known-false-positive metrics (max_subagent_chain_depth, parallelisable_fraction) and the S1 cost rebase record.

**Validation gate (per implementation strategy §7.1):**
- `python scripts/skill-check.py` — PASS (29 skills discovered; 0 blockers; 0 warnings).
- `python scripts/version-check.py` — PASS (manifest 0.9.0; v0.10.0 bump deferred to RC per §8.4).
- `python scripts/catalog-check.py` — PASS (29 skills, 13 commands; prefix-parity OK).
- `python scripts/path-hygiene-check.py` — PASS.
- `python scripts/phase_state_validate.py` — N/A in meta-pilot context (operates on project-side `phase_state.json`; harness has none).

**Calibrator economics gate:**
- `projected_cost_per_invocation_usd`: $6.0793 (was $5.8686 at v0.9.0 close). Cost-decomposition: executor count growth +2 (SK-NEW-A SKILL.md + shim); executor token growth +6,048 tokens; expected feature-cost delta $0.2107; actual delta $0.2107; **unaccounted bloat $0.00**. The increase is fully feature-attributed; the new $6.0793 baseline is established for the S1.5 close gate per `.plugin-efficiency.json baseline.projected_cost_per_invocation_usd_S1_rebase`.
- `subagent_dispatch_multiplier`: 9.217 (improved from v0.9.0's 9.568).
- Quality: 0 findings; 0 BLOCKER; 0 MAJOR.
- Speed (chain depth, parallelisable fraction): documented as known-false-positive (bash-environment calibrator does not pick up `scripts/protocol_constants.py`); inherited posture from v0.9.0; not a stage-close blocker.

**Meta-pilot probe (§6.1):** SK-NEW-A is shipped as the manually-invokable entry point only at S1; the auto-dispatch hook from `run-phase-1` Step 4.5 lands at S2. The meta-pilot probe at this stage exercises only the SKILL.md as a documentation artefact (per the §3.5 "the architecture/strategy plans supply the claim register" framing); a runtime probe of the SK-NEW-A iteration logic against the architecture plan's claims is deferred to S2 close (when the Planner can dispatch SK-NEW-A through Step 4.5).

**Architecture-plan deviation:** none at S1. The skill's body matches §5.1 + §5.5.1 + §5.5.2 + §5.5.6 of the architecture plan; the only structural choice not in the architecture is the placement of the `Phase 1 / Phase 2 / Phase 3 / Phase 4` numbered sections inside §3 Procedure (a presentational decision; does not affect contract).

**Deviation from implementation strategy:** the strategy specified per-stage worktrees via `git worktree add ../co-author-harness-S<N>`. This Cowork session's filesystem-tool access is scoped to the harness root only; sibling worktrees are not file-tool-accessible. S1 used **stage branches in-place** (`stage/v0.10.0-S1` on the existing checkout) instead. The eight-stage sequence is linear by design, so the worktree pattern's parallel-work benefit is not lost; rollback granularity is preserved via per-stage tags. This deviation will repeat at S1.5 → S6.

### Stage S1.5 — Wiki-graph substrate + write-back inside SK-NEW-A
<!-- TODO@S1.5-close. Should record:
     - SK-NEW-A iteration step rewrite (graph-substrate variant)
     - In-loop wiki/sources/ stub creation
     - Dual-path access contract (auto / filesystem / mcp_fastpath)
     - Coupling E.1 materialised note
     - Pilot probe outcome (graph_local_admits non-zero on a wiki-resident seed)
     - Calibrator economics axis result. -->

### Stage S2 — Phase-1 wiring (Edit-1)
<!-- TODO@S2-close. Should record:
     - skills/run-phase-1/SKILL.md Step 4.5 insertion
     - phase_state_schema.md additions (references_initialized field; trigger 31)
     - migrate_v090_to_v100_snowball_fields.py body authored
     - Smoketest fixture authored
     - Semantic-review verdict (binding at S2)
     - Calibrator economics + chain-depth. -->

### Stage S3 — Coverage audit skill (SK-NEW-B `claim-coverage-audit`)
<!-- TODO@S3-close. Should record:
     - skills/claim-coverage-audit/SKILL.md
     - commands/claim-coverage-audit.md shim
     - SKILL_REGISTRY.md SK-34 entry
     - Pilot probe outcome (claim_coverage_*.md emitted; reproducibility within ±5pp)
     - Calibrator economics. -->

### Stage S4 — Phase-2 wiring + SK-NEW-C (`extend-snowball-incremental`)
<!-- TODO@S4-close. Should record:
     - skills/run-phase-2/SKILL.md Step 0.5 insertion + §9 amendment
     - skills/extend-snowball-incremental/SKILL.md
     - commands/extend-snowball-incremental.md shim
     - SKILL_REGISTRY.md SK-35 entry
     - phase_state_schema.md last_coverage_score addition
     - Pilot probe outcome (auto-dispatch SK-NEW-B → SK-NEW-C exercised)
     - Semantic-review verdict (binding at S4)
     - Calibrator economics. -->

### Stage S4.5 — Wiki synthesis fast-path + red-link triggers
<!-- TODO@S4.5-close. Should record:
     - skills/claim-coverage-audit/SKILL.md synthesis-alignment fast-path
     - skills/retrofit-concept-grounding/SKILL.md red-link auto-trigger
     - Pilot probe outcome (synthesis-covered count non-zero;
       per-claim Scholar Gateway probe count drop ≥30% vs. S4 baseline;
       red_link_cap_per_round rate-limit functional)
     - Calibrator economics. -->

### Stage S5 — Documentation amendments
<!-- TODO@S5-close. Should record:
     - references/EXTERNAL_VERIFIERS.md §1.5 named-executor lines
     - references/AGENT_ORCHESTRATION.md §8.6 Coupling E.1 retired/re-registered
     - references/SKILL_REGISTRY.md final SK-NEW-A/B/C/D entries
     - Semantic-review verdict (binding at S5)
     - skill-check + catalog-check pass. -->

### Stage S6 — Cross-project seed inheritance (SK-NEW-D `inherit-snowball-from-wiki`)
<!-- TODO@S6-close. Should record:
     - skills/inherit-snowball-from-wiki/SKILL.md
     - commands/inherit-snowball-from-wiki.md shim
     - SKILL_REGISTRY.md SK-36 entry
     - SK-NEW-A pre-seed dispatch wiring
     - Pilot probe outcome (≥1 admission on adjacent-community wiki;
       no-op on absent-adjacency wiki)
     - Calibrator economics. -->

## 3. File-level change summary

<!-- TODO@RC: Aggregate from each stage's close-notes into a single table. -->

| File | Stage | Action |
|---|---|---|
| (TBD — populated as stages close) |  |  |

## 4. Validation — at-release

<!-- TODO@RC: After all stage gates pass and the v0.10.0 RC integration is run.
     Per the strategy §12, the RC gate is the union of:
     - Stage-aggregate green re-verification on main
     - Clean-room replay on a fresh project
     - Migration round-trip
     - bash scripts/release-gate.sh --ship-intent
     - Description-length empirical-distribution probe -->

- `python scripts/skill-check.py` — TBD
- `python scripts/version-check.py` — TBD
- `python scripts/catalog-check.py` — TBD
- `python scripts/path-hygiene-check.py` — TBD
- `python scripts/phase_state_validate.py` — TBD
- `python scripts/migrate_v090_to_v100_snowball_fields.py --validate scripts/fixtures/phase_state_smoketest/v090_to_v100/` — TBD
- `bash scripts/release-gate.sh --ship-intent` — TBD
- Pilot integration replay — TBD

## 5. Migration / back-compat

<!-- TODO@RC. Should record:
     - phase_state.json migration via migrate_v090_to_v100_snowball_fields.py
     - schema_version surface bump 0.7.4 → 0.10.0
     - SectionStateObject 16 → 18 fields
     - Trigger enum 30 → 31 (adds seed_snowball_signed)
     - classification.md frontmatter additions (5 fields)
     - No agent-prompt change
     - No retirement of any v0.9.0 surface
     - llm-wiki MCP plugin remains optional; dual-path contract preserves
       portability for projects that do not install it -->

## 6. Authorship

<!-- TODO@RC. Reference:
     - 2026-04-26-snowball-reference-architecture.md (the WHAT)
     - 2026-04-26-snowball-implementation-strategy.md (the HOW)
     - The user's adjudicated parameters: per-stage worktrees; full calibration
       loop per stage close; bundled v0.10.0 ship; Wohlin 2014 read before S1. -->

---

**Open scaffolding tags audit (run before RC).** Every `<!-- TODO@... -->` marker above must be either filled in or explicitly retired with a brief note before the v0.10.0 ship. A grep for `TODO@` against this file at the RC gate should return zero hits.
