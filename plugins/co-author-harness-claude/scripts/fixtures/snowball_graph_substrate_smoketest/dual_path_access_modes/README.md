# `dual_path_access_modes/` — access-mode contract scenarios for SK-NEW-A

These three scenarios document the expected `wiki_access_mode` log values under each of the three explicit `access_mode` settings the SKILL.md §5 dual-path access contract supports. Unlike the `basic_graph_traversal/` and `ambiguous_edge_no_admit/` fixtures, these scenarios do not carry mock graph or seed data — the access-mode contract is orthogonal to graph traversal and exercises the MCP-namespace probe at skill entry.

The three settings are `auto` (the default — detect-and-prefer-fast-path), `filesystem` (force filesystem reads even if MCP detected), and `mcp_fastpath` (require MCP; refuse to run if absent). Each scenario file documents the expected logged value, the expected detection probe behaviour at skill entry, and any failure paths.

## What this fixture validates

The detection-rule clause of SKILL.md §5 — that `wiki_access_mode` is logged once per skill invocation in the snowball log opening row, with one of three possible values: `filesystem`, `mcp_fastpath`, or `mcp_unreachable`. The third value is the fall-back state when the MCP was detected but errored mid-call; it is reachable from `auto` and from `mcp_fastpath` but never from `filesystem`.

A naïve implementation that does not log `wiki_access_mode` at all, or that logs the per-skill `access_mode` parameter rather than the detected mode (the two are different — `access_mode: auto` may resolve to `wiki_access_mode: filesystem` or `mcp_fastpath` depending on probe outcome), would silently lose the auditability the architecture §5.5.6 requires for cross-mode admission-rate comparison in Reflector Phase 2.5.

## Cross-references

- `skills/seed-snowball-discovery/SKILL.md §5` — dual-path access contract.
- `docs/superpowers/plans/2026-04-26-snowball-reference-architecture.md §5.5.6` — architectural specification.
- `references/EXTERNAL_VERIFIERS.md §1.5` — the contract-bound pass clause that authorises the MCP fast-path.
