# `artefact_frontmatter_smoketest/` — release-gate fixtures for `artefact_frontmatter_validate.py`

These fixtures are exercised by `scripts/release-gate.sh` Phase 0.68 to assert that
the artefact-frontmatter validator matches the schema contract in
`references/ARTEFACT_FRONTMATTER_SCHEMA.md §8` (rules 1–10 as of v0.8.0 P2.1b).

**P2.1a.1** (R-P2-VALIDATOR-F6) landed the F6 `planner_dispatch_plan` family in
`scripts/artefact_frontmatter_validate.py` per `proposals/v0.8.0_upgrade_architecture.md §9.3`.

**P2.1b** landed v0.8.0 field-adds on F1, F4, and F6 per the same document §9
move 2: F1 `adversarial_register` + `routing_rationale` (with §8 rule 8 string
shape); F4 optional `demoted_check_advisories`; F6 optional `check_profile` /
`structural_delta_flag` / `parallel_dispatch` / `threshold_version`.

F2, F3, and F5 do not yet have dedicated fixtures (optional future sub-phase
hardening).

## Layout

```
artefact_frontmatter_smoketest/
├── README.md
├── pass/reviews/
│   ├── dispatch_plan_C0001.md              # F6 PASS (P2.1a.1 + P2.1b fields)
│   ├── ph3_findings_p21b_2026-04-22_iter0.md   # F1 PASS
│   └── reflector_full_p21b_2026-04-22.md       # F4 PASS
└── block/reviews/
    ├── dispatch_plan_C0002.md                    # F6 BLOCK (user_approval_required)
    ├── dispatch_plan_p21b_block_bad_check_profile.md  # F6 BLOCK (check_profile enum)
    ├── ph3_findings_p21b_bad_routing_rationale.md     # F1 BLOCK (§8 rule 8)
    └── reflector_full_p21b_bad_demoted_severity.md   # F4 BLOCK (severity enum)
```

## Rules

- All fixtures are **static** (read-only for the release gate).
- Each BLOCK file documents its **single** intended malformation in the fixture
  body so the expected `R-Refl-FM-*` finding is unambiguous.

## Exit expectations

| Role | Files | Expected exit |
|---|---|---|
| PASS | all under `pass/reviews/` above | `0` |
| BLOCK | all under `block/reviews/` above | `3` |

Exit `3` means at least one MAJOR (or MINOR/ADVISORY) finding and **no** in-file
BLOCKER from the `R-Refl-FM-1`…`R-Refl-FM-6` taxonomy on the happy path; the
single-file validator uses exit `4` only for `R-Refl-FM-7` BLOCKER-style paths
(parse / family-dispatch / author-bug), not exercised here.

## Per-file notes

| File | Family | Intent |
|---|---|---|
| `dispatch_plan_C0001.md` | F6 | Full §7a.1 + optional §7a.2 including P2.1b profile/budget fields; `schema_version: "1.1"`. |
| `ph3_findings_p21b_2026-04-22_iter0.md` | F1 | Minimal legal F1 with `adversarial_register: refinement` and `routing_rationale: primary_evidence=sentence-level-pass`. |
| `reflector_full_p21b_2026-04-22.md` | F4 | Minimal `phase_aggregates: {}` + `demoted_check_advisories` one-row block (F4 remains non-strict on unknown top-level keys). |
| `dispatch_plan_C0002.md` | F6 | `user_approval_required: false` → §8 rule 7 cross-field. |
| `dispatch_plan_p21b_block_bad_check_profile.md` | F6 | `check_profile: Ph3-refine` (illegal token; legal set is `refine` / `structural` / `deep`). |
| `ph3_findings_p21b_bad_routing_rationale.md` | F1 | `routing_rationale` prose not matching `primary_evidence=<check_id>`. |
| `reflector_full_p21b_bad_demoted_severity.md` | F4 | `demoted_check_advisories[0].severity` not in the four-value enum. |

## Rebuilding

Extend fixtures in lockstep with `ARTEFACT_FRONTMATTER_SCHEMA.md`. If a new
required field lands on a family that has a PASS fixture, update that PASS file
first, then adjust BLOCK files so each still surfaces exactly one intended
finding.
