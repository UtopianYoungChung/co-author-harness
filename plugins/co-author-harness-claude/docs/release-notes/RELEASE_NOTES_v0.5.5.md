# Release Notes — research-writing-harness-claude v0.5.5

**Release date:** 2026-04-19
**Theme:** Phase F.1 — Tier Marshal advisory rollout
**Verdict:** CLEARED-WITH-WARNINGS (0 blockers, 5 pre-existing soft warnings)

## One-paragraph summary

v0.5.5 introduces the package's fifth agent — the **Tier Marshal** — as a hard-gate norm-compliance check bracketing every review round. At F.1 the Marshal ships in advisory-only mode: all thirteen preflight predicates (P-1..P-13) and eleven postflight predicates (Q-1..Q-11) run and their verdicts are recorded, but BLOCK severities are downgraded to WARN so no active project is interrupted. Phase F.2 at v0.5.6 will flip BLOCK active once the calibration evidence from the F.1 cycle is in hand.

## What ships

**Architectural additions (three)**
- New fifth agent — Tier Marshal (hard-gate norm-compliance under PARALLEL_CONDUCTOR §7).
- Preflight predicate battery P-1..P-13.
- Postflight predicate battery Q-1..Q-11.

**New artefacts (six)**
- `scripts/marshal_preflight.py` — stdlib-only preflight runner.
- `scripts/marshal_postflight.py` — stdlib-only postflight runner.
- `scripts/_marshal_common.py` — shared helpers (no runtime deps).
- `references/TIER_MARSHAL_CONTRACT.md` — agent I/O contract and rollout plan.
- `research_notes/tier_marshal_design_v1.md` — fourteen-section design spec.
- `scripts/fixtures/marshal_smoketest/` — PASS and BLOCK fixtures for CI.

**Migration helper**
- `scripts/migrate_classification_to_tier.py` — idempotent, backup-emitting migrator from legacy `review_depth:` to `tier:`, with v0.5.5 late-add table-cell fallback for classification records whose inputs live in a markdown table rather than frontmatter.

**Surface integrations**
- `.claude-plugin/plugin.json` version bump 0.5.4 → 0.5.5.
- `CHANGELOG.md` v0.5.5 entry (theme, changes, lessons L-2026-04-19-20/21/22).
- `README.md` §Version 0.5.5 entry.
- `references/tier_notifications.yaml` `marshal:` section (3 keys); `config_version` 1.1 → 1.2.
- `references/AGENT_ORCHESTRATION.md §8.3` forward-reference paragraph.
- `scripts/release-gate.sh` Phase 0.65 (Marshal smoketest) + Phase 0.7 (py_compile) wiring.

## Phase F rollout plan

| Phase | Version | Marshal behaviour | Actions to take |
|---|---|---|---|
| F.0 | pre-v0.5.5 | absent | — |
| **F.1** | **v0.5.5 (this)** | **Advisory only: BLOCK→WARN** | **Run migration helper against active projects; review WARN messages in preflight/postflight artefacts** |
| F.2 | v0.5.6 | Active: BLOCK gates rounds | None (transition handled at v0.5.6 ship) |
| F.3 | v0.5.7+ | Paste §8.3 inline; deprecate TIER_MARSHAL_CONTRACT.md as stand-alone | — |

## Live-project F.1 calibration evidence

Two live projects were smoke-tested at F.1 (2026-04-19). Report: `research_notes/marshal_f1_live_smoketest_2026-04-19.md`.

- **INF3006Y_AgencyDelegation** — passes all blocking checks (P-1/P-2/P-3/P-6/P-8/P-12/P-13); a single advisory P-7 WARN ("no `tier_decisions_log.md` yet — bootstrap exemption for first Phase 5.5 election"). No action needed before F.2.
- **milestone4_Darlington** — carries no `reviews/classification.md`; preflight returns WARN on P-1 with a clean remediation path (run `/classify-manuscript` or author by hand). Action needed before F.2: produce a classification record.

Neither finding is a false positive; both are the F.2-intended catchment.

## Pre-F.2 user checklist

Before v0.5.6 ships and flips BLOCK active, the user should:

1. **Run the migration helper against every active project root.**
   ```bash
   python3 scripts/migrate_classification_to_tier.py \
     --project-root <project> --dry-run
   # then, if PASS:
   python3 scripts/migrate_classification_to_tier.py \
     --project-root <project>
   ```
   The helper handles two source forms: YAML-lite frontmatter carrying `review_depth:`, and markdown-table rows of the form `| **Review depth** | standard |`. It is idempotent, backup-emitting (`.bak` sibling), and stdlib-only.

2. **Author `reviews/classification.md` for any project that lacks one.**
   Minimum frontmatter block:
   ```
   ---
   paper_type: <type>
   p_stage: <stage>
   venue: <venue>
   tier: <T0|T1|T2|T3|T3R|T4>
   last_confirmed: <YYYY-MM-DD>
   ---
   ```

3. **Run `marshal_preflight.py --advisory-only` against each active project.** Read the generated `reviews/marshal_preflight_<round>_<date>.md` and resolve any WARN tagged "would BLOCK at F.2".

4. **File anything surprising.** If a predicate fires a false-positive in your active projects, open a note under `research_notes/` so F.2's thresholds can absorb the calibration.

## Known warnings (non-regression)

The release-gate reports 5 warnings. All five are pre-existing:

- 1× SKILL_REGISTRY historical entry (`eygp-framework-checker`) — retained for lineage.
- 4× SKILL.md description-length soft signals — noted under v0.5.4's CHANGELOG as expected.

None of these are v0.5.5 regressions. 0 blockers.

## Integrity

- Archive: `research-writing-harness-claude-v0.5.5.zip`
- File count: 201 files (excludes `__pycache__`, `.pyc`, `.DS_Store`)
- Version parity: `plugin.json` 0.5.5 = `README.md` §Version 0.5.5 = `CHANGELOG.md` top 0.5.5
- Release gate: CLEARED-WITH-WARNINGS

*Shipped by Young Jo(seph) Chung on 2026-04-19.*
