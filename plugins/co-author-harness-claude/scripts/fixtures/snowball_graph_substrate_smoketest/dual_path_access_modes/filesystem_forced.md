# `access_mode: filesystem`

## Setting

The skill is invoked with `access_mode: filesystem`. This is the explicit-force-filesystem setting per SKILL.md §5 — used for testing reproducibility, for projects that require deterministic access patterns, or as a manual override when the MCP fast-path is misbehaving.

## Expected detection probe behaviour

The MCP-namespace probe is **not run**. The setting unconditionally selects filesystem reads regardless of MCP availability. The detection contract is short-circuited at skill entry.

Semantic queries fall back to lexical/Jaccard matching at the alignment-threshold default (0.3) per SKILL.md §5 default-path clause. The wiki paths read are `${wiki_path}/wiki/{sources,concepts,syntheses}/*.md`, `${wiki_path}/wiki/{index,log}.md`, and `${wiki_path}/graphify-out/{graph.json,GRAPH_REPORT.md}`.

## Expected log row

```json
{
  "phase": "OPEN",
  "skill": "SK-NEW-A",
  "access_mode_setting": "filesystem",
  "wiki_access_mode": "filesystem",
  "probe_outcome": "skipped_per_setting",
  "alignment_threshold": 0.3
}
```

## What this scenario validates

The forced-filesystem path bypasses the MCP probe entirely. A correct implementation does NOT run the probe under `access_mode: filesystem` — running it would be a small efficiency penalty and a small correctness liability (the probe could spuriously succeed against a stale MCP registration and cause downstream confusion).

The `wiki_access_mode` field equals the `access_mode_setting` field under this setting; a future implementation could collapse the two if it preferred a single field, but the architecture's auditability invariant is satisfied either way.

## Cross-references

- `skills/seed-snowball-discovery/SKILL.md §5` — "force filesystem reads even if MCP detected".
- `docs/superpowers/plans/2026-04-26-snowball-reference-architecture.md §5.5.6` — the explicit modes are for testing and for projects that want deterministic behaviour.
