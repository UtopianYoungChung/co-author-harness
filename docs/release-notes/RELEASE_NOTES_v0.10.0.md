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
<!-- TODO@S1-close. Should record:
     - skills/seed-snowball-discovery/SKILL.md frontmatter and final description-length
     - commands/seed-snowball-discovery.md shim
     - SKILL_REGISTRY.md SK-33 entry
     - Pilot probe outcome (REFERENCES.md populated; snowball_log.md generated)
     - Calibrator economics axis result vs. v0.9.0 baseline ($5.87)
     - Any architecture-plan deviation. -->

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
