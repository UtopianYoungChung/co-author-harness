# v0.34.0 — Native command-surface cleanup

## Outcome

The plugin now has one command implementation surface: native skills. The
legacy `commands/*.md` redirect files were removed because current Claude Code
loads both forms as skills and gives the same-named native skill precedence,
which made the redirect population redundant and duplicated the installed
inventory.

The user-facing menu contains only supported commands. Hidden capabilities are
still installed and model-invocable when orchestration needs them:

- legacy lifecycle bodies preserve old automation and routing;
- maintainer operations remain available to package maintenance flows;
- unavailable graph, Wiki-write, and centroid contracts retain deterministic
  fail-closed behavior without advertising unusable menu choices.

## Public routing

The lifecycle surface is `/run-draft`, `/run-iterate`, and `/run-finalize`.
Response-letter work uses `/response-letter-review`. Review, cancel-climb,
raise-ceiling, re-engagement, and terminal-signoff language is handled as
Planner intent or checkpoint input when it is not backed by a native skill.

The full public list is generated from native skill visibility and displayed by
`/plugin-commands`.

## Enforcement

- `references/policies/command_surface.v1.json` classifies every shipped skill.
- `scripts/command_surface_check.py` refuses duplicate command shims,
  unclassified skills, invalid `user-invocable` values, and catalog drift.
- `scripts/command_surface_smoketest.py` uses synthetic fixtures to prove the
  duplicate, visibility, and hidden-catalog failure modes.
- `scripts/skill-check.py`, `scripts/catalog-check.py`, alias parity, loader
  compatibility, release packaging, and live documentation were aligned to the
  native-skill contract.

## Compatibility

The five `run-phase-*` skills remain present as hidden compatibility bodies.
Their execution semantics are unchanged. Removing the redirect files does not
remove native skill resolution on current Claude Code hosts; custom commands
and skills share the same invocation mechanism, and same-name skills take
precedence.

Because this is a pre-1.0 package, the intentional menu cleanup is released as
a minor version. Users who relied on directly typing a hidden legacy name
should use `/run-draft`, `/run-iterate`, or `/run-finalize`; orchestration can
still resolve the retained legacy bodies internally.
