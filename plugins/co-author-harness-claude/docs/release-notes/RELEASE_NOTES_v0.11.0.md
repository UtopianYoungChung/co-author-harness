# Release Notes — co-author-harness-claude v0.11.0

**Date:** 2026-04-27
**Branch:** `release/v0.11.0`
**Tag:** `v0.11.0`
**Predecessor:** v0.10.2 (merge-commit `88739b2`)

---

## Headline

**Architectural cut + structural anti-drift posture.** v0.11.0 deletes
machinery that was not delivering, adds structural validators that
hard-fail drift recurrence, and registers the small set of facts the
plugin repeats across files in a single source of truth. The release
responds to the v0.10.2 audit finding that governance-trailer drift had
become the load-bearing source of the maintainer's "does the plugin
deliver what it promised?" worry.

## Substrate changes

### Retired

- **i\* SD/SR machinery.** The v0.7.1 opt-in machinery is removed in
  full: `sd_sr_required` field, `imodel_structural_validation_signed`
  trigger, `E-IMODEL-STRUCTURALLY-INCOMPLETE` and
  `E-Ph2-SD-UNGROUNDABLE` finding classes, the §3.1.1 structural-
  completeness validator, the Ph1 SD/SR authoring sub-phase, and the
  Ph2 read-prerequisite gate. Cumulative diff: 25 files modified,
  ~440 lines net deleted across c1a + c1b + c1c.

- **SK-21 `graph-contradiction-sweep`.** Phantom roadmap reference
  retired. Coupling E.3 was never built; the existing
  `check-contradictions` skill is the established contradiction-sweep
  surface.

- **Eight superseded scripts.** `migrate_convergence_log_v074.py`,
  `migrate_v055_to_v060.py`, `migrate_v060_to_v070.py`,
  `migrate_v073_to_v074_tier_to_phase.py`,
  `migrate_convergence_journal_v075.py`, `tier_state_canonicalize.py`,
  `tier_state_validate.py`, `tier_notifications_loader.py`. Replaced
  by phase-named successors (`phase_state_validate.py`,
  `phase_notifications_loader.py`) or simply outlived their migration
  windows.

- **Asserted skill counts in manifest descriptions.** The "Ships 32
  skills" tagline is gone from both `plugin.json` and `marketplace.json`.
  Descriptions are now narrative-only; the filesystem is the
  authoritative source for the count, surfaced at validate-time.

### Added

- **`scripts/manifest-coherence-check.py`** — five checks: description
  ≤300 chars, keywords ≤12, every keyword resolves to a substrate
  token, no asserted skill counts, plugin.json/marketplace.json
  description parity.

- **`scripts/ssot-check.py` + `.claude-plugin/ssot.yaml`** — Single
  Source of Truth registry. Four facts registered (`skill_count`,
  `command_count`, `manifest_version`, `manifest_description`); each
  fact's authority and consumers declared in YAML. The validator
  enforces fact-consumer parity at release-gate time.

- **`scripts/end_to_end_smoketest.py` + fixture** at
  `scripts/fixtures/end_to_end_ladder_smoketest/`. Pragmatic-scope
  harness exercising the validator chain plus
  `pre_phase_advance_check.py` against a single-section synthetic
  fixture. A future c10.5 will tighten the harness to a full
  Ph1->Ph2->Ph3 agent-dispatch simulation.

- **`scripts/migrate_v0100_to_v0110_drop_sd_sr.py`** — the
  v0.10.0->v0.11.0 migration helper. Idempotent; advisory output
  only; recognises both bulleted-Inputs and YAML-frontmatter forms of
  the field declaration.

### Extended

- **`scripts/version-check.py`** gains `check_no_version_trailers_in_prose`
  to enforce the v0.11.0 c7 trailer-strip invariant on active prose
  surfaces.

- **`scripts/path-hygiene-check.py`** gains a README-orphan rule
  (every relative link target must resolve) and an
  untracked-files-in-tracked-directories rule (releases/, tmp/ stay
  free of working files). Closes the forensic §4 Gap 3.

- **`scripts/catalog-check.py`** (landed at c2.6, ahead of plan c8
  schedule): inverts the skill-count contract. README is no longer
  required to assert a skill count; asserted counts now BLOCKER.

- **`scripts/pre_phase_advance_check.py`** clause (d) extended with
  classification.md presence check at T2 admission
  (`E-CLASSIFICATION-MISSING-AT-T2`).

## Migration path

Operators upgrading a v0.10.x project run:

```
python scripts/migrate_v0100_to_v0110_drop_sd_sr.py \
    --classification path/to/your-project/reviews/classification.md
```

The migration is idempotent. Safe to run on already-migrated projects;
emits a no-op INFO line.

Migrated `phase_entry_log` rows carrying the
`imodel_structural_validation_signed` trigger remain readable. v0.11.0+
write paths never emit the trigger, but the validator tolerates it on
read for audit-trail continuity.

## What did NOT change

- The four-agent contract (Planner / Evaluator / Generator / Reflector).
- The Lifecycle-Phase Ladder (Ph1 -> Ph2 -> Ph3 -> Ph4).
- The Grounding Protocol — full-file reads at every phase.
- The convergence-metric two-round stability test at Ph3.
- The MCR admission contract at Ph4.
- SAFEGUARD checks 1-8 (including the Reader-Experience Check 8
  introduced at v0.7.2).
- The snowball-driven reference-scaffolding bundle from v0.10.0.
- The 32 shipped skills and 16 commands.

## Known follow-ups

- **c10.5: full agent-dispatch smoketest.** The c10 harness asserts
  validator-chain greenness against the fixture; the next iteration
  tightens it to assert exit-0 from `pre_phase_advance_check.py` and
  to exercise actual Planner -> Generator -> Evaluator dispatch.

- **TIER_PROTOCOL.md / tier_notifications.yaml deletion.** Both files
  carry the v0.7.4 tier-named state alongside the phase-named state.
  The rename completed at v0.7.5 RC; these files are slated for
  deletion in a future cleanup commit. Left in place at v0.11.0 to
  avoid a sprawling rename PR alongside the architectural cut.

- **Substrate-doc references to retired scripts.** The CHANGELOG,
  RELEASE_NOTES_*, PHASE_PROTOCOL.md, and AGENT_ORCHESTRATION.md still
  name the eight scripts deleted at c5. Those references serve as
  audit-trail breadcrumbs documenting the historical migration paths;
  they were intentionally not swept. If operator confusion surfaces, a
  c8.5 follow-up can add a "no broken script reference in active
  substrate" validator rule.

## Verification at HEAD

All seven maintainer scripts return 0 BLOCKER:

| Validator | Result |
|---|---|
| skill-check.py | 32 skills, 0 blockers |
| version-check.py | manifest=0.11.0, README=0.11.0, CHANGELOG=0.11.0, marketplace=0.11.0 |
| catalog-check.py | 32 skills, 16 commands, README skills count `<missing>` (c2.6 contract) |
| path-hygiene-check.py | 0 blockers |
| manifest-coherence-check.py | description=259 chars, keywords=10, parity OK |
| ssot-check.py | 4 facts, 8 consumers, 0 blockers |
| end_to_end_smoketest.py | 0 blockers, 1 advisory (c10 scope) |

## Acknowledgements

This release was authored across multiple sessions. The plan
(`docs/superpowers/plans/2026-04-27-v0.11.0-definitive-architectural-plan.md`)
and the forensic re-read
(`reviews/v0110_session_forensic_2026-04-27.md`) are the binding
artefacts that anchored the architectural decisions. The
manifest/repository hygiene work in c2.5 / c2.6 closed the
SSOT-inconsistency tail surfaced by the forensic pass; the c8/c9
validator and registry work makes those decisions structurally durable
rather than operator-memory-dependent.
