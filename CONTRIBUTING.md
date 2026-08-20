# Contributing

Use the repository's existing governance before changing behavior:

- Read `AGENTS.md` and the relevant files it routes to.
- Keep changes scoped to the requested plugin, skill, reference, script, or documentation surface.
- Use `docs/agent-instructions/change-to-check-map.md` to run the focused
  validator and direct smoketest for the changed surface; reserve the full
  fixture corpus for the gates and infrastructure changes named there.
- This package's official validation plane is the `scripts/*` checks in
  `AGENTS.md` and the fixture registry, not a generic linter, type checker,
  formatter, or repository-root test command.
- Do not update release archives by hand; build them through the release process.
- Do not fabricate citations, claims, or validation evidence.

For workspace-level routing or policy changes, update the owning workspace governance files under `B:\Agents` and verify persisted bytes with a fresh shell read-back.
