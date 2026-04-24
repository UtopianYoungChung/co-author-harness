# Marshal smoketest fixtures

Two minimal project trees consumed by `scripts/release-gate.sh` Phase 0.65
to exercise the Tier Marshal preflight and postflight runners before
shipping a release.

## Layout

```
marshal_smoketest/
├── README.md               (this file)
├── pass/                   PASS fixture — every predicate should return PASS
│   ├── reviews/
│   │   ├── classification.md
│   │   ├── revision_log.md
│   │   ├── tier_decisions_log.md
│   │   ├── escalation_log.md
│   │   ├── tier_closeout_001_2026-04-19.md
│   │   ├── consolidated_findings_report.md
│   │   └── manuscript_diff_001.patch
│   └── manuscript/
│       └── draft.md
└── block/                  BLOCK fixture — classification absent, should BLOCK
    ├── reviews/
    │   └── revision_log.md       (intentionally no classification.md)
    └── manuscript/
        └── draft.md
```

## Expected runner behaviour

* `marshal_preflight.py --project-root pass/ --tier T3 --round 001 --date 2026-04-19`
  → exit 0 (PASS). Every P-predicate either passes or is N/A for the tier.

* `marshal_preflight.py --project-root block/ --tier T3 --round 001 --date 2026-04-19`
  → exit 2 (BLOCK) under default mode; exit 1 (WARN) with `--advisory-only`.
  P-1 (classification exists) fails as the single BLOCKER.

* `marshal_postflight.py --project-root pass/ --tier T3 --round 001 --date 2026-04-19`
  → exit 0 (PASS).

* `marshal_postflight.py --project-root block/ --tier T3 --round 001 --date 2026-04-19`
  → exit 2 (BLOCK); exit 1 with `--advisory-only`. Q-2 (closeout emitted) and
  others fail.

## Discipline

The fixtures are minimal by design. They exist to exercise the predicate
batteries in the release gate, not to be realistic project records. Any
cross-project testing should happen on live project roots outside the
package — see `scripts/migrate_classification_to_tier.py` for the
migration path for active projects.
