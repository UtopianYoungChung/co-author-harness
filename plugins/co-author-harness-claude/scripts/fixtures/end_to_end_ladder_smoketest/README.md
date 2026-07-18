# end-to-end ladder smoketest fixture (v0.11.0 c10)

Pragmatic-scope smoketest fixture authored at v0.11.0 c10 per the
definitive-architectural-plan §3.5. Represents a single-section
manuscript at Ph1 entry; the assertion harness at
`scripts/end_to_end_smoketest.py` exercises the validator chain
against this fixture.

## Layout

```
end_to_end_ladder_smoketest/
├── README.md                           (this file)
├── manuscript/
│   └── section_1_introduction.md       (≈200-word stub)
└── reviews/
    ├── classification.md               (theory · P2 · cross-venue · Ph3)
    ├── phase_state.json                (one section seeded at Ph1)
    └── ph1_draft_completion.md         (synthetic Ph1 exit signature)
```

## What the harness asserts

1. **Fixture well-formed.** Required files exist and parse against the
   v0.7.4 schema (classification.md, phase_state.json with current_phase
   in the legal enum, ph1_draft_completion.md with valid frontmatter,
   manuscript section).
2. **Plugin-level validator chain.** The six maintainer validators
   (skill-check, version-check, catalog-check, path-hygiene-check,
   manifest-coherence-check, ssot-check) return 0 BLOCKER against the
   plugin root.
3. **pre_phase_advance_check runs against fixture.** Advisory-only at
   c10 scope: the harness checks that the script runs against the
   fixture without crashing. A future c10.5 will tighten this to an
   exit-0 assertion once the fixture is fleshed out enough to satisfy
   every clause.

## What the harness does NOT yet do

- Full agent dispatch simulation (Planner -> Generator -> Evaluator ->
  Reflector). Plan §3.5 reserves this for c10.5.
- Multi-section fixture (this fixture has one section; ladder traversal
  Ph1 -> Ph2 -> Ph3 is exercised on a single heading_path only).
- Wiki-linked or graphify-coupling smoketest scenarios.

## Field absences worth knowing

- The `sd_sr_required` field is intentionally absent from
  `classification.md`: v0.11.0 c1 retired the SD/SR opt-in machinery; the
  field does not exist in v0.11.0 ledgers.
