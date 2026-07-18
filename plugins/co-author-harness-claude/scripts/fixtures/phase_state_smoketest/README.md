# `phase_state_smoketest/` — release-gate fixtures for `phase_state_validate.py`

These fixtures are exercised by `scripts/release-gate.sh` (Phase 0.67) to assert that
the v0.7.4 validator correctly distinguishes a well-formed Lifecycle-Phase ledger
from a malformed one. The smoketest is a regression guard for the schema-enforcement
contract declared in `references/phase_state_schema.md §6.1` (the v0.7.4 finding-code
taxonomy).

Renamed at v0.8.0 from `tier_state_smoketest/` per `proposals/v0.8.0_upgrade_architecture.md §9.1`
(R-P0-SCHEMA-3 closure). The v0.7.0-shape fixtures previously under the legacy directory
name failed the v0.7.4 validator because (a) `sections` was an array rather than a dict
and (b) log rows carried the v0.7.3 six-field shape without `model_used`. At v0.8.0 P2.1a
the fixtures additionally exercise the sixteenth `SectionStateObject` field
`pre_mcr_deep_pass_completed` (β-P-9a safety-net flag; default `false`).

## Layout

```
phase_state_smoketest/
├── README.md               (this file)
├── pass/
│   └── reviews/
│       └── phase_state.json  — well-formed v0.7.4 ledger; validator MUST return exit 0
└── block/
    └── reviews/
        └── phase_state.json  — deliberately malformed ledger; validator MUST return exit 4
```

## Rules

- Both fixtures are **static**. The release gate reads them; it does not write to them.
- `pass/` and `block/` each contain a complete minimal ledger — one section, the smallest
  `phase_entry_log` that still exercises a non-trivial invariant path.
- The `block/` fixture's malformation is **documented in this README**, not inline —
  the validator enforces the seven-field log-row shape exactly (extras fire
  `LOG_ROW_UNKNOWN_FIELD` MAJOR), so the single intended failure is the one declared below.

## What each fixture asserts

### `pass/reviews/phase_state.json`

- `schema_version == "0.7.4"` and `phase_vocabulary == "lifecycle_v0.7.4"`.
- `milestone_assignment` matches the default mapping (`M1/M2/M3 → Ph1, M4a → Ph2, M4b → Ph3, M5 → Ph4`).
- `sections` is a JSON object keyed by heading-path slug (validator requires dict, not array).
- Single section under key `"1. Introduction"`; `heading_path = ["1. Introduction"]`.
- All sixteen `SectionStateObject` fields present (per v0.8.0 P2.1a β-P-9a widening);
  `ph1_pstage_declaration == "P1"`; `convergence_metric` and `ph3_last_activity_at`
  are `null` (legal at Ph2); `pre_mcr_deep_pass_completed == false` (section has not
  yet reached Ph3, so no deep pass could have been run; `false` is the sensible
  default and also exercises the validator's `SECTION_BAD_PRE_MCR_DEEP_PASS_TYPE`
  MINOR check against a legal boolean value).
- Two `phase_entry_log` rows under the seven-field v0.7.4 shape
  (`timestamp, trigger, prev_phase, new_phase, actor, notes, model_used`):
  `initial_dispatch (planner) → Ph1`, then `user_approval (user) Ph1 → Ph2`.
  The first row carries `model_used: null` (planner-authored bootstrap); the second
  carries `model_used: "claude-sonnet-4-6"` (non-null exercises the string branch of
  the `LOG_ROW_BAD_MODEL_USED` MINOR check).
- `current_phase == "Ph2"`, `last_approved_phase == "Ph2"` (reconciles with the last
  log row's `new_phase`, satisfying the `SECTION_CURRENT_PHASE_DIVERGENT` MAJOR check).
- Monotonicity holds (Ph1 → Ph2 under `user_approval`).
- **Expected exit code:** `0` (zero findings).

### `block/reviews/phase_state.json`

- Same v0.7.4+P2.1a shell as `pass/` (sixteen-field `SectionStateObject` including
  `pre_mcr_deep_pass_completed: false`), but the second row violates monotonicity:
  `prev_phase == "Ph2"`, `new_phase == "Ph1"`, `trigger == "user_rejection"`
  (not one of the monotonicity-exempt triggers
  `retraction`, `eg1_ph4_downgrade_to_ph3`, `eg7_mcr_readmission_after_class_change`).
- `user_rejection` is chosen deliberately: it carries no additional contract check
  against the `(prev_phase, new_phase)` pair beyond monotonicity, so the fixture
  surfaces exactly one BLOCKER and the exit code is cleanly `4`.
- `current_phase: "Ph1"` reconciles with the last log row's `new_phase: "Ph1"`,
  so the fixture does not also fire `SECTION_CURRENT_PHASE_DIVERGENT` (MAJOR).
- Expected validator finding code: `MONOTONICITY_VIOLATION` (BLOCKER severity).
- **Expected exit code:** `4` — `MONOTONICITY_VIOLATION` is BLOCKER severity in the
  v0.7.4 validator, and `phase_state_validate.py` maps any BLOCKER finding to exit 4.

## Exit-code convention (v0.7.4)

The v0.7.4 validator's exit-code map is stricter than the v0.7.0 convention preserved
in the pre-rename README:

| Exit code | Meaning |
|---|---|
| 0 | PASS (no findings) |
| 1 | usage error |
| 2 | file I/O or JSON parse error |
| 3 | validation findings at MINOR or MAJOR severity only |
| 4 | BLOCKER findings present |

The release gate consumes exit 0 on PASS and exit 4 on BLOCK. Any other value on
either fixture is a regression against this README.

## Rebuilding

These fixtures are hand-crafted so a single-run copy-paste can regenerate them.
If the v0.7.4 validator adds a required log-row field, extend both fixtures in
lockstep; the `block/` fixture's deliberate monotonicity violation must remain
the **only** BLOCKER it fires. If a future version adds a new monotonicity-exempt
trigger or adds a contract check that clashes with `user_rejection`, swap the
BLOCK trigger to another non-exempt, phase-changing trigger that produces exactly
one BLOCKER finding.
