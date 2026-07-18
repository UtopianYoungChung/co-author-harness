# v0.9.0 → v0.10.0 Migration Smoketest Fixture

**Status: SKELETON** — Stage S0 deliverable. Fixture content is filled in at Stage S2 alongside the schema additions in `references/phase_state_schema.md`.

## Layout

```
v090_to_v100/
├── README.md            (this file)
├── pass/                (fixtures the migration should accept and transform cleanly)
│   ├── reviews/         (v0.9.0-shape phase_state.json + classification.md)
│   ├── references/      (REFERENCES.md exemplars for the references_initialized
│   │                     heuristic — wiki-linked-with-corpus and
│   │                     wiki-linked-without-corpus and not-wiki-linked cases)
│   └── expected/        (post-migration v0.10.0-shape exemplars; the
│                         migration's output is diffed against these)
└── block/               (fixtures the migration should refuse with a specific
    │                     non-zero exit code per the §Exit codes table in
    │                     migrate_v090_to_v100_snowball_fields.py)
    ├── invalid-json-state/
    ├── unparseable-classification-frontmatter/
    └── unrecognised-references-format/
```

## Test cases to add at S2

Per the strategy §3.3, the fixture must cover at least these cases:

### pass/

1. **Wiki-linked with populated REFERENCES.md.**
   - `references_initialized` should default to `true`.
   - `inherit_snowball` should default to `true`.
   - `last_coverage_score` should default to `null`.

2. **Wiki-linked with empty REFERENCES.md.**
   - `references_initialized` should default to `false`.
   - `inherit_snowball` should default to `true`.

3. **Not-wiki-linked.**
   - `inherit_snowball` should default to `false` (the wiki-coupling skills no-op when the wiki is absent).

4. **Idempotent re-run.**
   - A v0.10.0-shape `phase_state.json` re-run through the migration emits "already complete" and exits 0 without writing.

5. **Mixed state — some sections already migrated.**
   - Sections with `references_initialized` already present are skipped; sections without it are migrated.

### block/

1. **Invalid JSON in `phase_state.json`.** — Exit code 4.
2. **Unparseable YAML in `classification.md`.** — Exit code 7.
3. **REFERENCES.md present but format unrecognised.** — Exit code 8 (the `references_initialized` heuristic cannot decide; user must intervene).
4. **`schema_version` already at `0.10.0` but section count carries 16 fields.** — Exit code 6 (invariant violation; ledger inconsistency).

## Validation invocation (used by release-gate.sh at v0.10.0 RC)

```bash
python scripts/migrate_v090_to_v100_snowball_fields.py \
    --validate scripts/fixtures/phase_state_smoketest/v090_to_v100/
```

The validation runs each `pass/` fixture through the migration, diffs the output against `pass/expected/`, and confirms each `block/` fixture exits with the documented code. Any deviation is a v0.10.0 RC blocker.
