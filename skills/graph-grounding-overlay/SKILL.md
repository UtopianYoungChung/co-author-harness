---
name: graph-grounding-overlay
user-invocable: false
description: Unavailable graph-grounding overlay. Returns GRAPH_GOVERNED_GENERATION_UNAVAILABLE even when graph files are fresh and structurally valid; performs no graph-derived review or Wiki mutation.
trigger: when the user asks to run a graph overlay or invoke Coupling E.2; return the fail-closed no-op only.
created_by: Reflector (Coupling E.2 pilot)
created_from: >-
  Synergy analysis 2026-04-16 — graphify produces 43 nodes / 53 edges / 7
  communities / confidence-tagged extractions / section-level provenance at
  `knowledge/LLM wiki/graphify-out/`, but no plugin file references it. SK-20 is the
  minimum-viable pilot: a single Evaluator pre-flight hook that converts graph
  topology into findings in the pipeline's native output format, preserving
  uncertainty inheritance through graph-specific source tags.
pattern_source: >-
  GROUNDING_PROTOCOL.md Rules 3 (Verify Before Reference), 4 (Quote Before
  Attribute), 5 (Mark Uncertainty); PROJECT_BOOTSTRAP.md §4 Four Couplings
  (graphify is the unspoken substrate beneath A/B/C/D); SK-18
  `advisor-escalation` structural precedent for external-source tag inheritance
  and grounding-audit category extension
version: 1.0
---

# Graph Grounding Overlay

## FAIL-CLOSED: Graph authority unavailable

Governed graph authority is **unavailable** (`GRAPH_GOVERNED_GENERATION_UNAVAILABLE`).
Run / consult `scripts/graph_authority_gate.py` (unconditional for this delta): `governed_available: false`.

**Immediate no-op.** Do not produce overlay findings, do not treat `graph.json` as authoritative evidence, and do not continue into Phase 1–N of this skill while the gate reports unavailability. Prefer reason code:

```json
{
  "skill": "SK-20",
  "status": "noop",
  "reason_code": "GRAPH_GOVERNED_GENERATION_UNAVAILABLE",
  "message": "Governed graph generation/activation unavailable; structural validity does not grant graph authority.",
  "failed_checks": ["graph_governed_available"],
  "timestamp": "YYYY-MM-DD"
}
```

Primary Research completion, approval, and release continue. Only governed graph-dependent overlay behavior is deferred.

Also run deterministic gate `scripts/sk20_preflight_gate.py` so readiness + no-op artifacts are emitted consistently. If `should_run_sk20` is false for any reason (including this graph-authority plane), SK-20 must no-op.

The remaining sections preserve the dormant Coupling E.2 design for a future
governed promotion. They are non-executable while the unconditional gate is in
force and cannot override the immediate no-op above.

## Preconditions

Before invoking this skill, verify all of the following. Abort with a clear `SK-20: no-op (<reason>)` message and return without producing findings if any fails — this is graceful degradation, not error.

Before these checks, run deterministic gate `scripts/sk20_preflight_gate.py` so readiness + no-op artifacts are emitted consistently. If `should_run_sk20` is false, SK-20 must no-op and use `reviews/sk20_noop_YYYY-MM-DD.json` as the authoritative reason record.

1. **Project is wiki-linked.** The project CLAUDE.md contains `wiki_linked: true`. If absent or false, this skill is a no-op.
2. **Graphify output exists.** Resolve `wiki_path` from the project CLAUDE.md (or deterministic gate overrides), then verify `${wiki_path}/graphify-out/` contains both `graph.json` and `GRAPH_REPORT.md`. If either is missing, no-op.
3. **Graph is not stale.** Compare the `captured_at` field in `graph.json` (or the date line in `GRAPH_REPORT.md`) against the most recent `Last updated:` date across the project's `references/REFERENCES.md` and `milestones/M4_complete_paper_draft.md`. If the graph is older than either, no-op with `SK-20: graph stale — last captured <date>, manuscript/references updated <date>. Re-run graphify before overlay.`
4. **Manuscript is classified.** `reviews/classification.md` exists (or the user has explicitly set P-stage and paper-type). The overlay uses the classification to tune thresholds (e.g., P0 vs P1 expectations on orphan-node density) — without it, the overlay runs but reports all findings at their raw severity with no P-stage adjustment.
5. **Manuscript cites at least one source.** If the manuscript has no in-text citations, no-op with `SK-20: no citations to overlay`.

### No-op reason codes (machine-readable)

When SK-20 no-ops, write:

```json
{
  "skill": "SK-20",
  "status": "noop",
  "reason_code": "<code>",
  "message": "<human readable>",
  "failed_checks": ["<check-key>"],
  "timestamp": "YYYY-MM-DD"
}
```

Use one of these reason codes:

- `NOT_WIKI_LINKED`
- `COUPLING_E_DISABLED`
- `GRAPH_OUTPUT_MISSING`
- `GRAPH_STALE`
- `CLASSIFICATION_MISSING`
- `NO_CITATIONS`
- `GRAPH_JSON_UNREADABLE`
- `GRAPH_SCHEMA_INVALID`
- `GRAPH_GOVERNED_GENERATION_UNAVAILABLE`

When `reviews/coupling_readiness_YYYY-MM-DD.json` exists, prefer its `recommended_noop_reason_code` and `failed_checks` values to avoid reason drift between deterministic gate output and SK-20 logging.

## What you do

### Phase 1 — Load the graph

1. Read `${wiki_path}/graphify-out/graph.json`. Record: total node count, total edge count, edge confidence distribution (EXTRACTED / INFERRED / AMBIGUOUS counts).
2. Read `${wiki_path}/graphify-out/GRAPH_REPORT.md`. Extract: god-nodes list, community hubs, suggested questions, knowledge-gap isolated-node list, hyperedges.
3. Build two in-memory indexes:
   - `nodes_by_source_file` — maps `raw/corpus/<file>.pdf` to the list of node IDs extracted from that source, with each node's `source_location` field preserved.
   - `edges_by_source_pair` — maps (source_file_A, source_file_B) to the list of edges between their nodes, with each edge's `confidence`, `confidence_score`, and `relation` preserved.

### Phase 2 — Enumerate the manuscript's citation set

1. Read `milestones/M4_complete_paper_draft.md` (or `main.tex`). Enumerate every in-text citation using the same pattern set as SK-16 `retrofit-concept-grounding` Phase 1 (Author YYYY, Author et al. YYYY, parenthetical, in-table). Produce `cites = [(author, year, citation_key_if_resolvable, text_location), ...]`.
2. Read `references/REFERENCES.md` and resolve each citation to a `raw/corpus/<file>.pdf` path if one exists. Produce `resolved_cites = [(author, year, citation_key, pdf_path, text_location), ...]` and `unresolved_cites = [(author, year, text_location, reason), ...]`.
3. For each `resolved_cites` entry, look up the corresponding node set in `nodes_by_source_file`. Record `cited_sources_with_nodes` vs `cited_sources_without_nodes` (the latter are sources that graphify has not processed yet).

### Phase 3 — Generate the three finding types

**MANDATORY — READ ENTIRE FILE.** Before generating findings, you MUST read [`references/AGENT_ORCHESTRATION.md`](references/AGENT_ORCHESTRATION.md) completely from start to finish and locate §8.6 (Coupling E.2). That section carries the full spec for Finding A (graph-stub citations — cited sources absent from the graph), Finding B (section-location mismatches — three-tier matcher with Jaccard thresholds 0.25 / bigram / 0.30), and Finding C (missing-citation candidates — graphify edges between cited and uncited sources). **NEVER set any range limits when reading this file.** The threshold numerics, severity-by-P-stage mappings, and the match-tier annotation format (`(match-tier: 2)`, `(match-tier: 3)`) are load-bearing for grounding-audit Category 8 downstream consumption.

**Do NOT auto-promote findings to BLOCKER.** The overlay's function is to surface candidates; severity escalation beyond MAJOR requires the Evaluator's normal seven-step judgment in a subsequent pass.

### Phase 4 — P-stage adjustment

Before emitting the findings, apply P-stage sanity:

- **P0:** Demote all Finding-A entries to `[MINOR]`. A P0 draft is allowed to have ungrounded citation placeholders.
- **P1:** Default severities apply.
- **P2:** Promote Finding-C `semantically_similar_to` at EXTRACTED confidence from `[MINOR]` to `[MAJOR]` — a P2 paper is expected to have closed most surface-level citation gaps, so any such candidate is a stronger signal.

Record the P-stage and the thresholds applied in the output header, so grounding-audit Category 8 can verify the adjustment was correct.

### Phase 5 — Emit the overlay report

Write the overlay to `reviews/graph_overlay_YYYY-MM-DD.md` using the template below. The report is a **pre-flight input** to the Evaluator's Step 1 classification gating, not a replacement for any step. The Evaluator reads this file, incorporates the findings into its Step 1–7 judgment, and escalates severities based on its native criteria.

```markdown
# Graph Overlay Report

**Artifact overlaid:** milestones/M4_complete_paper_draft.md
**Date:** <YYYY-MM-DD>
**Graph captured:** <captured_at from graph.json>
**P-stage:** <P0 | P1 | P2>
**Paper type:** <from classification.md>

## Graph inventory
- Total nodes: <n>
- Total edges: <n>  (EXTRACTED: <n> · INFERRED: <n> · AMBIGUOUS: <n>)
- God-nodes: <list of top-5 highest-centrality>
- Communities: <n>  (cohesion range: <low>–<high>)
- Isolated nodes: <n>

## Citation alignment
- Total citations: <n>
- Resolved to pdf: <n>
- Unresolved: <n>  (listed in §Unresolved)
- Cited sources with graph nodes: <n>
- Cited sources without graph nodes: <n>

## Findings

### Finding type A — Graph-stub citations
<list, or "None" if empty>

### Finding type B — Section-location mismatches
<list, or "None" if empty>

### Finding type C — Missing-citation candidates
<list, or "None" if empty>

## P-stage adjustments applied
<explicit statement of which severities were demoted or promoted per Phase 4>

## Unresolved citations
<list — these bypass graph overlay entirely and should be flagged for REFERENCES.md update>

## Handback
- Findings emitted: <n>  (BLOCKER: 0 · MAJOR: <n> · MINOR: <n>)
- Next step: Evaluator Step 1 classification gating (this report is pre-flight input)
- Grounding-audit Category 8 target: this file
```

### Phase 6 — Append to revision log

Append a single line to `manuscript/revision_log.md`:

```
<YYYY-MM-DD> — SK-20 graph-overlay run — <n> findings (A: <n> · B: <n> · C: <n>) · graph <captured_at>
```

## What you do NOT do

1. **Do not modify the manuscript.** The overlay is read-only against `manuscript/`.
2. **Do not modify graphify output.** The overlay is read-only against `${wiki_path}/graphify-out/`.
3. **Do not escalate findings beyond MAJOR.** BLOCKER is reserved for the Evaluator's judgment pass; the overlay produces candidates, not convictions.
4. **Do not suppress INFERRED edges.** Carry the confidence score through to the finding; let the Evaluator decide.
5. **Do not fabricate edges or nodes.** If the graph lacks a node for a cited source, that absence is a Finding-A entry, not an imputation.
6. **Do not re-run graphify.** If the graph is stale, no-op with a clear message; re-running graphify is the user's decision because it may be costly and modifies the wiki.
7. **Do not consume graph output without carrying its uncertainty tags.** Every finding MUST be tagged `[source: graph-extracted]`, `[source: graph-inferred]`, or `[source: graph-stub]` so grounding-audit Category 8 can trace it back.
8. **Do not run if the project is not wiki-linked.** Coupling E, like Couplings A–D, fires only when `wiki_linked: true` in the project CLAUDE.md.

## Grounding-protocol integration

SK-20 extends the grounding audit with **Category 8** — graph-sourced claims — in the same shape Category 7 extended it for advisor-sourced claims:

- Every `[source: graph-extracted]` finding must trace back to a node in `graph.json` with matching `source_file` and `source_location`.
- Every `[source: graph-inferred]` finding must trace back to an edge in `graph.json` with matching endpoints, relation, and `confidence: INFERRED` or `AMBIGUOUS`.
- Every `[source: graph-stub]` finding must trace back to a cited source in the manuscript that has zero nodes in `graph.json`.

A grounding-audit Category 8 violation (e.g., a `[source: graph-extracted]` finding with no matching graph node) is a BLOCKER — it means the overlay fabricated a finding rather than reading the graph.

## Dependencies and siblings

- **Upstream:** graphify toolchain (runs externally; produces `graph.json` and `GRAPH_REPORT.md`). This skill does not invoke graphify; it reads graphify's outputs.
- **Upstream:** SK-15 `backfill-source-stubs-from-references` populates `wiki/sources/` stubs, which provides the mapping between citation keys and `raw/corpus/*.pdf` paths that Phase 2 relies on.
- **Downstream:** `grounding-audit` skill (Category 8 validates SK-20's output).
- **Sibling:** SK-18 `advisor-escalation` is structurally analogous — both skills bridge an external source of claims (advisor MCP; graphify graph) into the pipeline with tag-preserved uncertainty inheritance. SK-18 extends grounding-audit with Category 7; SK-20 extends it with Category 8.
- **Coupling E.1 — now implemented:** The `SK-19 graph-read-at-planner` placeholder is **retired**. Coupling E.1 is materialised at v0.10.0 via **SK-33 `seed-snowball-discovery`**'s graph-substrate iterate phase — see `references/AGENT_ORCHESTRATION.md §8.6 Coupling E.1`. The `graph-read-at-planner` token is preserved only as the coupling's historical identifier in the roadmap.
- **Coupling E.3 — retired at v0.11.0:** the originally roadmapped `SK-21 graph-contradiction-sweep` was retired with the c4 phantom-roadmap cleanup. If a contradiction-sweep need re-emerges, the existing `check-contradictions` skill is the established surface.

## Failure modes and mitigations

| Failure | Detection | Mitigation |
|---|---|---|
| Graphify output stale | `captured_at` < manuscript/references `Last updated:` | No-op with explicit message (Precondition 3). User re-runs graphify. |
| Graph has no nodes for cited sources | `cited_sources_without_nodes` is non-empty | Finding type A reports them; not a skill failure. |
| Manuscript uses non-standard citation format SK-16's regex misses | Phase 2 `unresolved_cites` count spikes | Overlay report §Unresolved lists them; skill does not attempt to parse further — this is a REFERENCES.md / citation-format issue. |
| graph.json malformed or unreadable | JSON parse error on Phase 1 step 1 | No-op with `SK-20: graph.json unreadable — <error>`. Do not proceed on partial data. |
| Hyperedges reference nodes not in the `nodes` list | Phase 1 step 3 finds dangling refs in `hyperedges` | Log the dangling refs; proceed with overlay on the coherent subset. |
| Graphify INFERRED edges dominate (> 40%) | Phase 1 step 1 distribution check | Emit a warning at the top of the overlay report; the Evaluator should weight Finding-C severities more cautiously. |

## Contract version gate

This skill targets graphify output format observed on **2026-04-13** (schema: `directed`, `multigraph`, `graph`, `nodes`, `links`, `hyperedges` top-level keys; nodes carry `id`, `label`, `source_file`, `source_location`, `author`, `captured_at`, `community`, `norm_label`; edges carry `relation`, `confidence`, `confidence_score`, `source_file`, `source_location`, `weight`, `source`, `target`). If graphify's output schema changes, this skill's Phase 1 step 3 will fail to build its indexes cleanly — update the skill rather than silently producing incomplete findings.
