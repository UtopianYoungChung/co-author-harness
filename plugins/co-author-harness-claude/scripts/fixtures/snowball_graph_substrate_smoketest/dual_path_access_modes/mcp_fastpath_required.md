# `access_mode: mcp_fastpath`

## Setting

The skill is invoked with `access_mode: mcp_fastpath`. This is the require-MCP setting per SKILL.md §5 — used when the project's iteration design depends on embedding-driven semantic queries that lexical/Jaccard matching cannot approximate adequately, or when a benchmarking pass requires the fast-path comparator.

## Expected detection probe behaviour

The MCP-namespace probe runs at skill entry. Two outcomes are possible, but only one allows the skill to continue.

**Probe positive (MCP namespace present and reachable).** The skill proceeds with semantic queries routed through `/llm-wiki-query`. Behaviour from this point is identical to `auto` with a positive probe.

**Probe negative (MCP namespace absent).** The skill **refuses to run**. It emits a `SK-NEW-A: no-op (MCP_FASTPATH_UNAVAILABLE)` error per the no-op reason-code contract in SKILL.md §2 — though `MCP_FASTPATH_UNAVAILABLE` is not in the documented code set on line 51 and would need to be added in a future hardening pass. For the present S1.5 fixture, the documented behaviour is "refuse to run", with the specific error code as a documentary suggestion.

## Expected log row (probe positive)

```json
{
  "phase": "OPEN",
  "skill": "SK-NEW-A",
  "access_mode_setting": "mcp_fastpath",
  "wiki_access_mode": "mcp_fastpath",
  "probe_outcome": "mcp_namespace_present",
  "alignment_threshold": "embedding"
}
```

## Expected refusal (probe negative)

```json
{
  "skill": "SK-NEW-A",
  "status": "noop",
  "reason_code": "MCP_FASTPATH_UNAVAILABLE",
  "message": "access_mode: mcp_fastpath was requested but the mcp__llm-wiki__* namespace is not available in this session. Re-run with access_mode: auto to fall back to filesystem reads, or install the llm-wiki MCP plugin.",
  "failed_checks": ["mcp_namespace_probe"],
  "timestamp": "<ISO-8601>"
}
```

## Expected log row (mid-call MCP error after positive probe)

Under `access_mode: mcp_fastpath`, a mid-call MCP error is more serious than under `auto` — the operator explicitly opted in to the fast-path. The skill MUST NOT silently fall back to filesystem; instead it should log `wiki_access_mode: mcp_unreachable`, halt the iteration, and emit a MAJOR finding so the user can adjudicate whether to re-run with `access_mode: auto` (accepting filesystem fallback for the remainder) or to fix the MCP and retry. This behaviour is more conservative than the SKILL.md §5 fall-back-silently default; the fixture proposes it as the correct interpretation under the explicit-require setting.

```json
{
  "phase": "ITERATE",
  "skill": "SK-NEW-A",
  "access_mode_setting": "mcp_fastpath",
  "wiki_access_mode": "mcp_unreachable",
  "halt_reason": "mcp_call_errored_under_required_setting",
  "iteration": 2,
  "user_action_required": true
}
```

## What this scenario validates

The asymmetry between `auto` (silent fallback on mid-call error) and `mcp_fastpath` (halt + MAJOR finding on mid-call error). The architecture §5.5.6 prose does not distinguish the two failure paths explicitly, so a literal implementation might fall back silently in both cases. The fixture argues that the explicit-require setting carries an implicit "treat mid-call failure as a hard problem" semantic — otherwise the setting is operationally identical to `auto` and the parameter offers no leverage.

This is a documentary scenario; the SKILL.md §5 prose may be tightened in a later hardening pass to explicitly distinguish the two failure paths. For S1.5, the fixture flags the asymmetry as a contract gap to be considered.

## Cross-references

- `skills/seed-snowball-discovery/SKILL.md §5` — "require MCP; refuse to run if absent".
- `skills/seed-snowball-discovery/SKILL.md §2` — no-op reason-code contract (incomplete coverage of MCP-related codes).
- `docs/superpowers/plans/2026-04-26-snowball-reference-architecture.md §5.5.6` — architectural specification of the dual-path contract.
