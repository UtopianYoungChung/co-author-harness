# `access_mode: auto` (default)

## Setting

The skill is invoked with `access_mode: auto` (or the parameter is omitted, since `auto` is the default per SKILL.md §5).

## Expected detection probe behaviour

At skill entry, SK-NEW-A probes the available toolset for the `mcp__llm-wiki__*` namespace. The probe runs once per invocation. Two outcomes are possible:

**Probe positive (MCP namespace present and reachable).** Semantic queries route through `/llm-wiki-query`. The skill writes `wiki_access_mode: mcp_fastpath` to the snowball log opening row. If a subsequent call into the MCP errors mid-iteration, the skill falls back silently to filesystem reads and the `wiki_access_mode` field is updated to `mcp_unreachable` for the remainder of the round. The fall-back is silent — no user-facing prompt — because the architecture §5.5.6 specifies graceful degradation, not an interactive choice.

**Probe negative (MCP namespace absent).** Semantic queries fall back to lexical/Jaccard matching at the alignment-threshold default (0.3). The skill writes `wiki_access_mode: filesystem` to the snowball log opening row. No retry of the probe occurs within the same skill invocation — a once-per-invocation probe is the contract.

## Expected log row (probe positive)

```json
{
  "phase": "OPEN",
  "skill": "SK-NEW-A",
  "access_mode_setting": "auto",
  "wiki_access_mode": "mcp_fastpath",
  "probe_outcome": "mcp_namespace_present",
  "alignment_threshold": "embedding"
}
```

## Expected log row (probe negative)

```json
{
  "phase": "OPEN",
  "skill": "SK-NEW-A",
  "access_mode_setting": "auto",
  "wiki_access_mode": "filesystem",
  "probe_outcome": "mcp_namespace_absent",
  "alignment_threshold": 0.3
}
```

## Expected log row (mid-call MCP error after positive probe)

```json
{
  "phase": "OPEN",
  "skill": "SK-NEW-A",
  "access_mode_setting": "auto",
  "wiki_access_mode": "mcp_unreachable",
  "probe_outcome": "mcp_namespace_present",
  "fallback_at_iteration": 2,
  "fallback_reason": "mcp_call_errored",
  "alignment_threshold": 0.3
}
```

## What this scenario validates

The three-state vocabulary of `wiki_access_mode` and the distinction between `access_mode_setting` (the user/parameter-supplied value) and `wiki_access_mode` (the detected runtime value). A correct implementation logs both — the setting documents the operator's intent; the runtime value documents what actually happened.
