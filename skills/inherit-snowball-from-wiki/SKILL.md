---
name: inherit-snowball-from-wiki
user-invocable: false
description: Hidden unavailable pre-seed inheritance. Returns GRAPH_GOVERNED_GENERATION_UNAVAILABLE; does not traverse communities or emit pre_seed authority.
trigger: auto-invoked by seed-snowball-discovery (SK-33) as a pre-seed step when wiki_linked and inherit_snowball are set; immediately no-op with GRAPH_GOVERNED_GENERATION_UNAVAILABLE. Not a public command.
version: 1.0
---

# inherit-snowball-from-wiki — Cross-Project Pre-Seed Inheritance

## FAIL-CLOSED: Graph authority unavailable

Governed graph authority is **unavailable**
(`GRAPH_GOVERNED_GENERATION_UNAVAILABLE`); `scripts/graph_authority_gate.py`
returns false. Graph-independent reader-profile v2 keeps the semantic centroid
dormant; topology and mechanical digests supply no semantic warrant.

**Immediate no-op.** Do not traverse communities or produce pre-seed evidence while unavailable. Write `reviews/sk36_noop_YYYY-MM-DD.json` with:

```json
{
  "skill": "SK-36",
  "status": "noop",
  "reason_code": "GRAPH_GOVERNED_GENERATION_UNAVAILABLE",
  "message": "Governed graph generation/activation unavailable; structural validity does not grant pre-seed authority.",
  "failed_checks": ["graph_governed_available"],
  "timestamp": "YYYY-MM-DD"
}
```

SK-33 continues without wiki-community pre-seed. Primary Research completion is not blocked.

**Grounding basis:** `docs/superpowers/plans/2026-04-26-snowball-reference-architecture.md §§5.5.5 (skill spec), 6.8 (S6 deliverable), 7 R-13 (pre-seed cap rationale)`; `docs/superpowers/plans/2026-04-26-snowball-implementation-strategy.md §5.6`; `skills/graph-grounding-overlay/SKILL.md` (SK-20; Coupling E.2 graph schema and `captured_at` staleness precondition — SK-36 reuses the identical check); `skills/seed-snowball-discovery/SKILL.md` (SK-33; Phase 0 caller — SK-36 must emit `pre_seed.json` in the shape SK-33's `SEED_FROM_CLAIMS` input expects); `references/AGENT_ORCHESTRATION.md §8.6 Coupling E.1` (SK-36 is referenced as the pre-seed step invoked by SK-33 when `inherit_snowball: true`); `references/GROUNDING_PROTOCOL.md §§Rule 5 (mark uncertainty), Rule 6 (no gap-filling)`.

---

## 1. What this skill does

`inherit-snowball-from-wiki` is the **Ph1 pre-seed step** for wiki-linked projects that have accumulated community structure from prior projects. It runs **before** SK-33's own seed phase, traversing `${wiki_path}/graphify-out/graph.json` to identify graphify communities *adjacent* to the current section's classification, then extracting those communities' source membership as a pre-seeded starting pool.

The pre-seed is **additive**: it is unioned with SK-33's claim-derived seeds, never substituted for them. SK-33's per-claim verification step (Phase 3) prunes any pre-seeded paper that does not resolve at least one of the section's actual claims, so over-seeding self-corrects without user intervention (architecture §7 R-13 mitigation).

On a wiki with no adjacent communities, SK-36 no-ops cleanly — it writes no `pre_seed.json` and leaves SK-33's seed_set unmodified.

The skill does **not** run snowball iterations. It does not call external verifiers. It does not modify manuscript prose, REFERENCES.md, or graphify's output. Its scope is strictly bounded to the pre-seed list production at Ph1 entry.

---

## 2. Preconditions

Before invoking this skill, verify all of the following. On any failure, no-op with the matching reason code and return without producing artefacts. **This is graceful degradation, not error** — SK-33 continues in normal seed mode when SK-36 no-ops.

0. **Graph authority is available.** If `graph_authority_gate` reports `GRAPH_GOVERNED_GENERATION_UNAVAILABLE` / `governed_available: false`: immediate no-op with that reason. Do not continue to community traversal.

1. **Project is wiki-linked.** The project AGENTS.md contains `wiki_linked: true`. If absent or false: `NOT_WIKI_LINKED`.

2. **Opt-in is active.** `reviews/classification.md` carries `inherit_snowball: true` (or the field is absent and the project AGENTS.md confirms `wiki_linked: true`, in which case the default is `true`). If explicitly `inherit_snowball: false`: `INHERIT_SNOWBALL_DISABLED`.

3. **Graph output exists.** Resolve `wiki_path` from project AGENTS.md. Verify `${wiki_path}/graphify-out/` contains both `graph.json` and `GRAPH_REPORT.md`. If either is missing: `GRAPH_OUTPUT_MISSING`.

4. **Graph is not stale.** Following the same pattern as SK-20 Precondition 3: compare the `captured_at` field in `graph.json` against the most recent `Last updated:` date across the project's `references/REFERENCES.md` (if it exists) and `manuscript/<section>.md`. (SK-36 is section-scoped so it checks the section file rather than SK-20's `milestones/M4_complete_paper_draft.md`; the staleness logic is otherwise identical.) If the graph is older: `GRAPH_STALE`. (Contrast SK-33, which demotes to `[graph-stale]` warning and continues; SK-36 is a pre-seed step and its entire value depends on graph freshness — a stale pre-seed can propagate stale corpus assumptions into iteration 1.)

5. **Classification is parseable.** `reviews/classification.md` exists and is parseable. Reads: `p_stage`, `paper_type`, `claim_coverage_threshold`, `pre_seed_cap` (default 10); and optionally `p_stage_anchors` (list of citation keys; used by Condition B — absence means Condition B evaluates false for all communities, not an error) and `key_references` (same role as `p_stage_anchors`; checked if `p_stage_anchors` absent). If absent or unparseable: `CLASSIFICATION_MISSING`.

6. **Graph is schema-valid.** `graph.json` is well-formed JSON with top-level keys `nodes`, `links` (edges), and `hyperedges` (may be empty). If schema validation fails: `GRAPH_SCHEMA_INVALID`.

### No-op reason codes

When SK-36 no-ops, write `reviews/sk36_noop_YYYY-MM-DD.json`:

```json
{
  "skill": "SK-36",
  "status": "noop",
  "reason_code": "<code>",
  "message": "<human readable>",
  "failed_checks": ["<check-key>"],
  "timestamp": "YYYY-MM-DD"
}
```

Codes: `GRAPH_GOVERNED_GENERATION_UNAVAILABLE`, `NOT_WIKI_LINKED`, `INHERIT_SNOWBALL_DISABLED` (opt-out via `inherit_snowball: false`), `PRE_SEED_CAP_ZERO` (cap explicitly set to 0 — increase `pre_seed_cap` to re-enable), `GRAPH_OUTPUT_MISSING`, `GRAPH_STALE`, `CLASSIFICATION_MISSING`, `GRAPH_SCHEMA_INVALID`, `NO_ADJACENT_COMMUNITIES` (all preconditions pass but adjacency check finds zero qualifying communities — this is a clean no-op, not a failure).

---

## 3. Procedure

### Phase 1 — Load graph and extract community structure

1. Read `${wiki_path}/graphify-out/graph.json`. Build the following in-memory structures:
   - `communities` — map from community ID → list of node IDs in that community (from each node's `community` field).
   - `god_nodes` — the highest-centrality nodes per community. Derive by counting in-degree + out-degree per node within its community; take the top-3 per community as god-node candidates. (Note: if `GRAPH_REPORT.md` explicitly lists god-nodes under a "Community hubs" or equivalent section, use those verbatim and skip the in-degree derivation.)
   - `source_file_by_node` — map from node ID → `source_file` field (e.g., `raw/corpus/<file>.pdf`).

2. Read `${wiki_path}/graphify-out/GRAPH_REPORT.md`. Extract:
   - **Community labels** — the human-readable label or topic description per community ID.
   - **God-node list** — if present as a named section, use it to override the derived `god_nodes` from step 1.
   - **Isolated nodes** — log the count; do not attempt adjacency over isolated-node communities.

3. Record edge confidence distribution (EXTRACTED / INFERRED / AMBIGUOUS counts) from `graph.json`. If INFERRED edges exceed 40% of total, emit a `[high-inferred-fraction]` annotation in the `snowball_log.md` row (consumers should weight the adjacency result more cautiously).

### Phase 2 — Identify adjacent communities

A graphify community is **adjacent** to the current section if **either** of the following conditions holds:

**Condition A — Label token overlap above synthesis-alignment threshold.**
1. Tokenise the community label from `GRAPH_REPORT.md` (normalise: lowercase, strip punctuation, remove stopwords).
2. Tokenise the section's claim register: extract all noun phrases and key terms from `reviews/revision_plan.md` (planned claims section) or `manuscript/<section>.md` (headings + first sentence per paragraph).
3. Compute Jaccard similarity between the community-label token set and the section claim-register token set.
4. Community is adjacent under Condition A if Jaccard ≥ `synthesis_alignment_threshold_jaccard` from `classification.md` (default 0.3, per architecture plan §5.5.3).

**Condition B — God-node is a P-stage anchor.**
1. Resolve the god-nodes of the community to their `source_file` fields (e.g., `raw/corpus/wohlin_2014.pdf`).
2. Read `reviews/classification.md` for any explicit P-stage anchors: citation keys in the `p_stage_anchors` list or `key_references` field, if present. These are BibTeX-style identifiers (e.g., `Wohlin2014`).
3. For each god-node `source_file`, resolve to a citation key using the following lookup chain:
   - **REFERENCES.md lookup (preferred when file exists).** Search `references/REFERENCES.md` for a row whose `pdf_path` column matches `source_file`. Read that row's `wiki_key` or `project_key` column as the citation key.
   - **Wiki stub lookup (fallback).** If no REFERENCES.md match, check whether `${wiki_path}/wiki/sources/<stem>.md` exists (where `<stem>` is the `source_file` base name without extension). If the stub exists, read its frontmatter `source_key` field as the citation key.
   - **Base-stem heuristic (last resort).** If neither lookup resolves, use the `source_file` base name without extension, lowercased with underscores and hyphens stripped, as a fuzzy token match against the `p_stage_anchors` values (case-insensitive token overlap). A match requires at least one author-name token and the year to overlap.
4. If the resolved citation key matches any value in the `p_stage_anchors` or `key_references` list, the community is adjacent under Condition B. If `p_stage_anchors` and `key_references` are both absent from `classification.md`, Condition B evaluates to false for all communities (not an error).

A community qualifies for pre-seeding if it satisfies **A OR B**. Record each qualifying community with its condition (A / B / both) and its similarity score (for Condition A) in the Phase 3 log entry.

### Phase 3 — Extract and cap the pre-seed list

1. For each adjacent community (in descending Jaccard similarity order for Condition A; in alphabetical community ID order for Condition B only), collect all `source_file` values for the community's nodes where `source_file` resolves to a `raw/corpus/*.pdf` path.

2. Deduplicate across communities: if the same `source_file` appears in multiple adjacent communities, count it once.

3. **Apply cap.** Take the top `pre_seed_cap` (default 10) entries from the deduplicated list. Order: Condition A communities first (highest similarity), Condition B communities second, ties broken by god-node centrality (higher degree first). If the deduplicated list has fewer entries than `pre_seed_cap`, the cap is not binding — record actual count.

4. For each pre-seeded paper, build a `pre_seed_entry` with:
   - `source_file` — the `raw/corpus/*.pdf` path from the node.
   - `community_id` — the originating community.
   - `adjacency_condition` — `"A"` / `"B"` / `"both"`.
   - `jaccard_score` — the label-token Jaccard score (null for Condition-B-only entries).
   - `confidence_floor` — `"EXTRACTED"` / `"INFERRED"` / `"AMBIGUOUS"` from the node's edges with the highest in-community connectivity.
   - `provenance_tag` — `"[pre-seed: wiki-community-<community_id>]"`.

5. Emit `reviews/pre_seed.json`:

```json
{
  "skill": "SK-36",
  "timestamp": "YYYY-MM-DD",
  "section": "<section-id or filename>",
  "wiki_path": "<resolved wiki_path>",
  "graph_captured_at": "<captured_at from graph.json>",
  "adjacent_communities": [
    {
      "community_id": "<id>",
      "community_label": "<label>",
      "adjacency_condition": "A|B|both",
      "jaccard_score": 0.0,
      "qualifying_sources": ["raw/corpus/<file>.pdf", ...]
    }
  ],
  "pre_seed_list": [
    {
      "source_file": "raw/corpus/<file>.pdf",
      "community_id": "<id>",
      "adjacency_condition": "A|B|both",
      "jaccard_score": 0.0,
      "confidence_floor": "EXTRACTED|INFERRED|AMBIGUOUS",
      "provenance_tag": "[pre-seed: wiki-community-<id>]"
    }
  ],
  "pre_seed_count": 0,
  "cap_applied": false,
  "cap_value": 10,
  "high_inferred_fraction": false
}
```

If `NO_ADJACENT_COMMUNITIES` — all preconditions passed but adjacency step found zero qualifying communities — write the no-op JSON (§2) and return. Do **not** emit `pre_seed.json` with an empty list; the file's absence is the canonical signal to SK-33 that SK-36 found no pre-seeds.

### Phase 4 — Append snowball_log.md row

Append a single structured row to `reviews/snowball_log.md` (creating the file with the `<!-- scholar-gateway-contract: v0.1 -->` header **only if the file does not yet exist**; if the file already exists with that header, do not write the header again):

```
<YYYY-MM-DD> — SK-36 pre-seed — communities evaluated: <n> · adjacent: <n> · pre-seeded: <k>/<pre_seed_cap> · cap_applied: <true|false> · adjacency_conditions: A:<nA> B:<nB> both:<nBoth> · graph_captured: <captured_at>
```

If SK-36 no-oped for any reason (including `NO_ADJACENT_COMMUNITIES`), append:

```
<YYYY-MM-DD> — SK-36 pre-seed — noop: <reason_code>
```

---

## 4. Outputs

### Files written

- **`reviews/pre_seed.json`** — the pre-seed list consumed by SK-33 as input to its `SEED_FROM_CLAIMS` procedure. Written on successful pre-seed (≥1 adjacent community with ≥1 qualifying source). Absent on no-op (SK-33 interprets absence as "no pre-seed available; proceed with claim-derived seeds only").

- **`reviews/sk36_noop_YYYY-MM-DD.json`** — written on any no-op (§2 reason codes). Machine-readable for downstream gate scripts.

- **`reviews/snowball_log.md`** — one row appended per invocation (success or no-op).

### Files NOT written

- **`references/REFERENCES.md`** — SK-36 does not modify REFERENCES.md. That is SK-33's job after it unions the pre-seed with claim-derived seeds.
- **`${wiki_path}/wiki/sources/`** — SK-36 does not create wiki stubs. SK-33's in-loop write-back (§4) handles stub creation after the union pool is assembled.
- **Any manuscript file** — SK-36 is read-only against `manuscript/`.
- **`${wiki_path}/graphify-out/`** — SK-36 is read-only against graphify outputs.

---

## 5. What you do NOT do

1. **Do NOT run snowball iterations.** SK-36 extracts a pre-seed list; saturation is SK-33's responsibility.
2. **Do NOT call external verifiers.** The pre-seed is graph-derived only; Class 1 verification runs inside SK-33's Phase 3 when the pre-seeded papers are admitted.
3. **Do NOT over-write the `pre_seed.json` cap.** If `pre_seed_cap` is reached, stop. Excess community members are silently omitted — they are not deferred-discovery candidates.
4. **Do NOT emit `pre_seed.json` with an empty list.** Absence is the no-op signal; an empty `pre_seed_list` array could be mistakenly read as "zero findings" rather than "did not run."
5. **Do NOT substitute for SK-33's seed phase.** The pre-seed is unioned with, not a replacement for, claim-derived seeds. Even with a full `pre_seed_cap` list, SK-33 must still execute its own Phase 1 (wiki, Zotero, Scholar Gateway) to ensure claim-level coverage.
6. **Do NOT admit AMBIGUOUS graph edges into the pre-seed.** Include only nodes whose primary community edges carry `confidence: EXTRACTED` or `confidence: INFERRED`. Flag AMBIGUOUS-sourced candidates with `confidence_floor: AMBIGUOUS` in the `pre_seed_entry` — SK-33 applies its own `admit_inferred_edges` policy before accepting them.
7. **Do NOT re-run graphify.** If the graph is stale, no-op with `GRAPH_STALE`. Re-running graphify is the user's decision because it modifies the wiki.
8. **Do NOT run if `wiki_linked: false`.** Coupling E (graph substrate) fires only when the project is wiki-linked.

---

## 6. Trigger vocabulary

- `"inherit-snowball"` · `"pre-seed from wiki"` · `"cross-project seed"` · `"/inherit-snowball-from-wiki"`
- **Auto-invoked** by SK-33 `seed-snowball-discovery` Phase 0 when:
  - `wiki_linked: true` in project AGENTS.md
  - `inherit_snowball: true` in `reviews/classification.md` (default `true` for wiki-linked projects)
  - `${wiki_path}/graphify-out/graph.json` exists and is fresh per SK-20 Precondition 3
- **Manually invokable** for inspection without a live SK-33 session (e.g., to preview which communities would pre-seed a section before committing to a full snowball run).

---

## 7. Sibling skills

- **Upstream:** none. SK-36 is the entry point of SK-33's pre-seed step; it reads graphify output (produced externally) and classification.md (written by the user at project bootstrap).
- **Downstream:** SK-33 `seed-snowball-discovery` — SK-36 hands off `pre_seed.json`; SK-33 unions it with claim-derived seeds and runs the full snowball iteration. SK-33's per-claim verification step prunes any pre-seeded paper that does not resolve a claim.
- **Graph source:** SK-20 `graph-grounding-overlay` (Coupling E.2) — both SK-36 and SK-20 read `graph.json` and `GRAPH_REPORT.md`. SK-36 extracts community source membership for pre-seeding; SK-20 extracts citation-topology signals for grounding overlay. They are independent — neither invokes the other.
- **Adjacent:** SK-34 `claim-coverage-audit` — at Ph2, SK-34 audits whether the pool SK-33 assembled (including any SK-36 pre-seed contribution) resolves the section's claims. SK-36 has no direct coupling to SK-34.
- **Not a replacement for:** SK-33 `seed-snowball-discovery` (SK-36 pre-seeds; SK-33 saturates — SK-36 cannot replace the per-claim snowball iteration).

---

## 8. Failure modes

| Failure | Detection | Handling |
|---|---|---|
| `graph.json` malformed or unreadable | Phase 1 JSON parse error | No-op with `GRAPH_SCHEMA_INVALID`. Do not proceed on partial data. |
| Community labels absent or empty in `GRAPH_REPORT.md` | Phase 1 extraction | Fall back to using node labels from `graph.json` `label` field for tokenisation. If still empty, that community is skipped; it is not eligible for Condition A. |
| P-stage anchors absent from `classification.md` | Phase 2 Condition B | Condition B evaluates to false for all communities; Condition A alone drives adjacency. Not an error. |
| Pre-seed cap is 0 in `classification.md` | Phase 3 | No-op with `PRE_SEED_CAP_ZERO` — a cap of 0 is equivalent to disabling pre-seeding. Log the cap value in the no-op JSON. (Distinct from `INHERIT_SNOWBALL_DISABLED`, which reflects the explicit flag; remediation differs: increase `pre_seed_cap` vs. toggle the flag.) |
| `pre_seed.json` already exists from a prior same-day run | Phase 3 emit | Overwrite. The file is a transient artefact produced per invocation; idempotency is not a hard requirement here (SK-33's idempotency check guards against re-running the full snowball on an already-initialised section). |
| Wiki MCP fast-path unavailable | Phase 1/2 reads | Use filesystem reads silently; log `wiki_access_mode: filesystem` in the snowball_log row. The pre-seed quality is identical — the adjacency criterion is graph-topology-based, not MCP-dependent. |
| Graph has nodes with no `source_file` field | Phase 3 extraction | Skip those nodes; they cannot be mapped to a pre-seedable paper. Log count of skipped nodes in the snowball_log row. |

---

## Notes on tier and scope

**Package-tier skill.** Applies to any project under the harness with `wiki_linked: true` where the wiki has accumulated graphify community structure from ≥1 prior project. On a fresh wiki with no prior content (or a wiki with no `graphify-out/` directory), SK-36 no-ops under `GRAPH_OUTPUT_MISSING` without any visible effect on SK-33's operation. Calibrator tier: **executor** (Sonnet — structured graph traversal, on-disk reads only; no external API calls, per `MODEL_ALLOCATION.md §2`).
