---
name: seed-snowball-discovery
description: "Ph1 entry skill — assemble references/REFERENCES.md from a section's claim register via Wohlin-style snowball saturation. Optional SK-36 pre-seed step at Phase 0 (wiki-community inheritance). Wiki-graph substrate first (Coupling E.1); Class 1 verifier fall-through; in-loop wiki/sources/ stub write-back; dual-path access (filesystem / mcp_fastpath). Stops on rate < ε (default 0.05) or 4 iterations. Trigger: /seed-snowball-discovery, fresh section, or references_initialized:false."
trigger: when the user invokes /seed-snowball-discovery, when run-phase-1 Step 4.5 dispatches the seed-snowball gate on a fresh section, when references/REFERENCES.md is absent, or when classification.md carries references_initialized:false
version: 1.0
---

# seed-snowball-discovery — Ph1 Entry Reference Scaffolding

**Grounding basis:** `docs/superpowers/plans/2026-04-26-snowball-reference-architecture.md §§4 (mechanised procedure), 5.1 (skill specification), 5.5.1 (graph substrate), 5.5.2 (in-loop write-back), 5.5.6 (dual-path access)`; `references/GROUNDING_PROTOCOL.md §§Rule 4 (quote-before-attribute), Rule 6 (no gap-filling), Rule 7a (external verification)`; `references/EXTERNAL_VERIFIERS.md §§1.5 (wiki-first discovery ordering), 2 (Class 1/1.5/2/3 verifier registry), 3.1 (Scholar Gateway render contract)`; `skills/graph-grounding-overlay/SKILL.md` (SK-20; Coupling E.2 graph schema and graph-staleness precondition pattern); `skills/backfill-source-stubs-from-references/SKILL.md` (SK-15; the in-loop write-back inherits SK-15's stub template and atomic-rename pattern); Wohlin 2014 (`10.1145/2601248.2601268`; methodological anchor; PDF in Zotero `FXJ6M8ED`).

---

## 1. What this stage does

`seed-snowball-discovery` is the **Ph1 entry skill** for projects whose `references/REFERENCES.md` does not yet exist or is not yet populated for the section under draft. It assembles a saturated reference pool from the section's claim register via a mechanised version of the snowball method (Wohlin 2014) — a seed phase that consults the wiki-first discovery order (`EXTERNAL_VERIFIERS.md §1.5`), an iterate phase that traverses backward and forward citations until saturation, and a verify phase that emits a Rule 7a verification log row for every admitted paper.

The skill is the **operationalisation** of `EXTERNAL_VERIFIERS.md §1.5`, which mandates the wiki → Zotero → Class 1 ordering for *discovery* but does not name an executor. SK-33 is the named executor.

Output: a populated `references/REFERENCES.md` with three tables (`core corpus`, `snowball`, `cited-via`) per the format established by SK-15's input contract; an append-only procedure trace at `reviews/snowball_log.md`; and rows appended to `reviews/external_verification_log.md` for every Class-1-fall-through admission.

The skill does **not** edit manuscript prose. It does not run at Ph2 or later (SK-35 handles incremental extension at Ph2). It does not promote `wiki/sources/` stubs to `grounding_status: full` (that is SK-17's job at M5).

## 2. Preconditions

Before invoking this skill, verify all of the following. On any failure that is not gracefully degradable, abort with a clear `SK-33: no-op (<reason>)` message and return without producing artefacts.

1. **`reviews/classification.md` exists and is parseable.** Reads `paper_type`, `p_stage`, `venue`, and (when present) the new v0.10.0 fields `claim_coverage_threshold`, `inherit_snowball`, `pre_seed_cap`. If absent or unparseable: no-op with `CLASSIFICATION_MISSING`. The user must run `/classify-manuscript` first.

2. **A claim register is resolvable for the target section.** Either (a) `reviews/revision_plan.md` declares the section's planned claims in its outline, OR (b) `manuscript/<section>.md` exists with at least one heading whose body contains drafted claims. If neither: no-op with `NO_CLAIM_REGISTER` — the user must declare the section's intended claims before snowball can seed.

3. **At least one Class 1 verifier is reachable.** Probe Scholar Gateway via a whoami-class call (a minimal `semanticSearch` query with `topN: 1`). If unreachable AND no wiki is linked AND Zotero is unreachable, no-op with `NO_REACHABLE_VERIFIER` — the seed phase has no source. If Scholar Gateway is unreachable but Zotero is reachable, proceed in degraded mode (Zotero-only seed; Class 1 fall-through deferred until verifier returns).

4. **Idempotency check.** Read `reviews/phase_state.json` for the target section. If `references_initialized: true` and `references/REFERENCES.md` exists with non-empty core corpus and snowball tables, no-op with `ALREADY_INITIALIZED`. The user must explicitly delete the field or invoke `/extend-snowball-incremental` (SK-35) to extend the existing pool.

5. **Wiki-graph staleness check (when `wiki_linked: true`).** Resolve `wiki_path` from the project CLAUDE.md. If `${wiki_path}/graphify-out/graph.json` exists, compare its `captured_at` against `references/REFERENCES.md` and `manuscript/<section>.md` `Last updated:` markers. If the graph is older, emit a `[graph-stale]` warning into `reviews/snowball_log.md`'s opening row and proceed with **external-verifier-only** iteration (the graph-substrate variant of §5 is degraded to a no-op for this run; user is asked to re-run graphify before the next snowball pass). This mirrors `SK-20 Precondition 3` graceful-degradation discipline.

### No-op reason codes

```json
{
  "skill": "SK-33",
  "status": "noop",
  "reason_code": "<code>",
  "message": "<human readable>",
  "failed_checks": ["<check-key>"],
  "timestamp": "YYYY-MM-DDTHH:MM:SSZ"
}
```

Codes: `CLASSIFICATION_MISSING`, `NO_CLAIM_REGISTER`, `NO_REACHABLE_VERIFIER`, `ALREADY_INITIALIZED`, `WIKI_PATH_UNRESOLVABLE`, `GRAPH_STALE` (warning, not no-op), `GRAPH_JSON_UNREADABLE`, `INSUFFICIENT_SEEDS_AFTER_PHASE` (seed phase yielded zero candidates across all configured verifiers).

## 3. Procedure

### Phase 0 — Pre-seed inheritance (when `wiki_linked: true` and `inherit_snowball: true`)

Before assembling claim-derived seeds, check whether SK-36 `inherit-snowball-from-wiki` should run. This step is a no-op for non-wiki-linked projects or when `inherit_snowball: false` in `reviews/classification.md`.

**Conditions for auto-invocation (all three must hold):**
1. `wiki_linked: true` in project CLAUDE.md.
2. `inherit_snowball: true` in `reviews/classification.md` (or field absent, which defaults to `true` for wiki-linked projects).
3. `${wiki_path}/graphify-out/graph.json` exists and its `captured_at` is fresh per SK-20 Precondition 3.

**If all three hold:** Invoke SK-36 `inherit-snowball-from-wiki`. On clean exit (SK-36 produced `reviews/pre_seed.json`), read `pre_seed.json` and load its `pre_seed_list` as the **initial `seed_set`** passed into Phase 1. The pre-seeded papers are tagged with their `provenance_tag` fields (e.g., `[pre-seed: wiki-community-<id>]`) so Phase 3's verification log can distinguish them from claim-derived seeds.

**If SK-36 no-ops** (any reason code, including `NO_ADJACENT_COMMUNITIES`) or if `reviews/pre_seed.json` is absent after invocation: proceed with an empty `seed_set` and log `[phase-0: no-pre-seed]` in `reviews/snowball_log.md`. This is normal — pre-seeding is opportunistic.

**Pre-seed union rule.** The pre-seed is **additive**: Phase 1 adds claim-derived seeds to the pre-seeded pool. Phase 3's per-claim admission filter prunes any pre-seeded paper that does not resolve at least one of the section's actual claims. Over-seeding self-corrects without user intervention (architecture §7 R-13 mitigation).

**Field mapping note.** Each entry in `pre_seed_list` carries a `source_file` field (e.g., `raw/papers/<file>.pdf`). This field maps to the `pdf_path` slot used by Phase 2's `lookup_node_by_doi_or_pdf_path` resolver — the two field names differ, but the path values are identical. Phase 2's resolver handles the look-up transparently.

**Log row.** Append a Phase 0 row to `reviews/snowball_log.md` recording: `phase_0_invoked: <true|false>`, `pre_seed_count: <k>`, `sk36_noop_reason: <code|null>`.

### Phase 1 — Seed assembly

Per `EXTERNAL_VERIFIERS.md §1.5`, the seed phase consults sources in strict order. The Class 1 verifier ordering inside the external tier is Scholar Gateway first, then Consensus for cross-check on contested claims (per architecture plan §10 open-question Q3 default).

1. Extract the **claim register** for the target section. From `reviews/revision_plan.md` (preferred) or `manuscript/<section>.md`:
   - Each claim is a proposition that requires evidence (existential, comparison, mechanism, result, theoretical commitment).
   - Output: `claims = [(claim_text, claim_kind, section_locus), ...]`.

2. **Wiki-first consultation (when `wiki_linked: true`).** Per `EXTERNAL_VERIFIERS.md §1.5` step 1: read relevant `${wiki_path}/wiki/sources/*.md`, `wiki/concepts/*.md`, `wiki/syntheses/*.md`, and `${wiki_path}/graphify-out/GRAPH_REPORT.md` (community structure, hubs). Admit any wiki source that resolves at least one claim into the seed set with provenance `[seed: wiki]`. Log a `Wiki-first` line in `reviews/revision_plan.md` per `EXTERNAL_VERIFIERS.md §3 Planner clause`.

3. **Zotero library consultation.** Per §1.5 step 2: invoke `mcp__zotero__zotero_semantic_search` with each claim's text as the natural-language query. Admit returns above the library-relevance threshold (default 0.6) with provenance `[seed: zotero]`. The Zotero ledger is a Class 2 verifier here (the user already curated it); admissions become Class 1 only when a subsequent iteration step's external probe corroborates them.

4. **External Class 1 fall-through.** Per §1.5 step 3, only when (2) and (3) yield fewer than `min_seed_per_claim` (default 3) admits per claim: invoke Scholar Gateway (`mcp__70599628-...__semanticSearch`). The `interaction_id` UUID is generated **once per snowball iteration** and reused across all sub-queries within that iteration. Each external admit gets provenance `[seed: scholar-gateway]` and immediately triggers a verification-log row.

5. **Cross-check on contested claims (optional).** When the section's classification carries `p_stage: P2` (the most rigorous register), every claim with only a single Class 1 hit is cross-checked against Consensus (`mcp__a28b93ab-...__search`). A CONTESTED return surfaces in `snowball_log.md` as a Phase 1 contention marker; the claim continues into the iterate phase but with an annotation that the Generator must surface the contestation in prose at Ph1 drafting.

### Phase 2 — Iterate (graph-substrate variant)

Per architecture plan §5.5.1, the iteration step computes admissions **first against the graphify graph** (when reachable), then through external verifiers only for graph-stub seeds. Pseudocode:

```
SNOWBALL ITERATION:
  S_0 = seed_set  (from Phase 1)
  I = 0

  while True:
    I = I + 1

    # Graph-local traversal (zero external API cost)
    backward_local, forward_local = ∅, ∅
    for s in S_{I-1}:
      graph_node = lookup_node_by_doi_or_pdf_path(s, graph.json)
      if graph_node:
        backward_local += traverse_edges(graph_node, "backward",
                                         confidence_floor="EXTRACTED")
        forward_local  += traverse_edges(graph_node, "forward",
                                         confidence_floor="EXTRACTED")

    # External fall-through ONLY for graph-stub seeds
    backward_external, forward_external = ∅, ∅
    graph_stub_seeds = S_{I-1} \ {s : lookup_node_by_doi_or_pdf_path(s, graph.json)}
    for s in graph_stub_seeds:
      backward_external += SCHOLAR_GATEWAY_BACKWARD(s)
      forward_external  += SCHOLAR_GATEWAY_FORWARD(s)

    # Per-claim admission filter (prunes the recall-biased pool)
    candidates = backward_local ∪ forward_local ∪
                 backward_external ∪ forward_external
    new_admits = {c ∈ candidates : c resolves at least one open claim}
                 \ S_{I-1}

    rate = |new_admits| / max(1, |S_{I-1}|)
    log(ITERATE, I, |new_admits|, rate,
        graph_local_admits = |backward_local|+|forward_local|,
        external_admits    = |backward_external|+|forward_external|,
        graph_stub_seeds   = |graph_stub_seeds|)

    if rate < ε or I >= max_iterations:
      saturation_signal = "ε-met" if rate < ε else "max-iter-reached"
      break

    S_I = S_{I-1} ∪ new_admits
```

**Lookup keying.** `lookup_node_by_doi_or_pdf_path(s, graph.json)` resolves seeds against graph nodes primarily by `source_file` (matched against REFERENCES.md's `pdf_path` column), falling back to `(author, year)` heuristics when no `pdf_path` resolves. The two-tier resolution accommodates both Zotero-derived seeds (carrying `pdf_path`) and Scholar-Gateway-derived seeds (carrying author/year only).

**Edge confidence policy.** AMBIGUOUS edges are never auto-admitted; they surface as `[graph-ambiguous]` candidates in the snowball log for user review. INFERRED edges are admitted only when the iteration's external-cost budget warrants the lower-confidence path (parameter `admit_inferred_edges: false` by default; surfaced in `classification.md`).

**Per-iteration `interaction_id`.** Every Scholar Gateway sub-query within iteration `I` uses the same UUID, generated once at the iteration entry. Iteration `I+1` generates a new UUID. This satisfies the Scholar Gateway "parallel/follow-up searches in the same episode" contract per `EXTERNAL_VERIFIERS.md §2`.

### Phase 3 — Verify and log

For every paper admitted across Phases 1 and 2 that fell through to a Class 1 verifier (i.e., not the graph-local subset):

1. Append a row to `reviews/external_verification_log.md` per `EXTERNAL_VERIFIERS.md §5`. Date / Agent / Claim (short) / Verifier / Query (verbatim from `provenance.query_as_executed`) / Returned ID (DOI) / Returned title / Result (MATCH / CONTESTED / NOT FOUND / UNREACHABLE).

2. Run Class 3 retraction check (`mcp__zotero__scite_check_retractions`) on every admitted paper. A `retracted: true` result is binding under Rule 7a — the paper is removed from the snowball pool and the finding is logged as a BLOCKER. If Scite is unreachable, log `[VERIFIER UNREACHABLE — Scite]` in the verification row's Result column and re-attempt at Ph2 entry.

3. Honour the Scholar Gateway render contract per `EXTERNAL_VERIFIERS.md §3.1`: every Scholar-Gateway-derived row carries the per-search provenance line; the snowball log file carries the `<!-- scholar-gateway-contract: v0.1 -->` top-of-file marker **written only if the file is being created for the first time** (if `reviews/snowball_log.md` already exists from a prior SK-36 Phase 4 no-op row, do not write the header again); the session footer is rendered once per snowball pass at the end of `snowball_log.md`.

### Phase 4 — REFERENCES.md emission

Author or rewrite `references/REFERENCES.md` per the SK-15 input format:

- **Core corpus.** Papers admitted in Phase 0 (pre-seeded by SK-36, provenance `[pre-seed: wiki-community-<id>]`) OR in Phase 1 with provenance `[seed: wiki]` or `[seed: zotero]` (i.e., already in the user's curated or wiki layer). Pre-seeded papers are first-class seeds; they are assigned to the Core corpus table because they originate from the wiki layer of a prior project.
- **Snowball.** Papers admitted in Phase 2 (any iteration), grouped by iteration depth (`Iteration 1`, `Iteration 2`, ...). If a pre-seeded paper is independently re-admitted via Phase 2 graph traversal (because it appears in the graph as a graph-local hit), Phase 2's admit entry takes precedence over the Phase 0 pre-seed entry, and the paper is listed under Snowball (Iteration 1) with both provenance tags recorded.
- **Cited-via.** Papers referenced from inside read sources but not directly verified — these are flagged for a follow-up direct read; SK-33 does not auto-stub them.

Each table row carries the canonical fields per SK-15: `project_key`, `wiki_key` (if `wiki_linked`), `authors`, `year`, `title`, `venue`, `pdf_path` (when Zotero PDF is attached), `provenance_tag`.

## 4. In-loop wiki write-back (when `wiki_linked: true`)

Per architecture plan §5.5.2, every paper SK-33 admits triggers an immediate `${wiki_path}/wiki/sources/<key>.md` stub creation, calling SK-15's stub-template logic *inline* rather than batching for a post-snowball SK-15 invocation.

**Atomic-write contract.** Borrowed verbatim from SK-15 §Phase 4: write `<wiki_path>/wiki/sources/<key>.md.tmp`, then atomic-rename. Concurrent SK-33 invocations across sections in the same project serialise on `wiki/index.md` via OS-level file locking.

**Provenance preservation.** Each in-loop stub's frontmatter carries:

```yaml
grounding_status: stub — created by SK-33 iteration <i> from snowball seed <seed_doi> on <YYYY-MM-DD>
```

This is distinct from SK-15's terminal-stage stub provenance (`stub — bibliographic extracted from <project> REFERENCES`); the Reflector's Phase 2.5 Category 7 audit can therefore distinguish proactive (snowball) vs. reactive (SK-15 backfill) stub origins. The two populations have different verification-debt profiles.

**Skip condition.** If a `wiki/sources/<key>.md` page already exists with `grounding_status: full`, SK-33 does NOT overwrite — it logs the skip in `snowball_log.md` and continues. SK-15's regeneration discipline applies here verbatim.

## 5. Dual-path access contract

Per architecture plan §5.5.6, all wiki-side operations resolve through a dual-path contract that lets the implementation behave identically whether the optional `llm-wiki` MCP plugin is connected.

**Default — filesystem reads.** Use `Read`, `Glob`, and `Grep` over `${wiki_path}/wiki/{sources,concepts,syntheses}/*.md`, `${wiki_path}/wiki/{index,log}.md`, and `${wiki_path}/graphify-out/{graph.json,GRAPH_REPORT.md}`. Semantic queries fall back to lexical/Jaccard matching at the alignment-threshold default (0.3).

**Fast-path — `mcp__llm-wiki__*` when available.** Probe the MCP namespace at skill entry. If detected, semantic queries route through `/llm-wiki-query` per `EXTERNAL_VERIFIERS.md §1.5` "contract-bound pass". The user-facing artefacts are identical; only the query mechanism differs.

**Detection rule.** Tool-namespace detection runs once per skill invocation. The result is logged in the `snowball_log.md` opening row as `wiki_access_mode: filesystem | mcp_fastpath | mcp_unreachable`. The third value indicates the MCP was detected but errored mid-call; the skill falls back to filesystem reads silently for the remainder of the round.

**Per-skill access-mode parameter.** The skill accepts an optional `access_mode` argument: `auto` (default; detect-and-prefer-fast-path), `filesystem` (force filesystem reads even if MCP detected), `mcp_fastpath` (require MCP; refuse to run if absent). The default `auto` matches §1.5's portability contract.

## 6. Saturation criterion

The stop rule is `rate < ε`, with ε surfaced in `classification.md` as `snowball_epsilon` (default 0.05). The default is anchored on Barros-Justo et al. 2021 (`10.1002/smr.2370`), which reported a forward-snowball trace of `3039 → 601 → 26` papers across three iterations on a 38-paper seed (per-iteration admission ratios 0.198 → 0.043; the third-iteration ratio falls below 0.05).

**Field-conditioned overrides** (project sets in `classification.md` if defaults are inappropriate):
- ε = 0.02 — theoretical-stable subfields with low citation churn.
- ε = 0.05 — default; stable peer-reviewed empirical fields.
- ε = 0.10 — fast-moving ML/HCI subfields with high citation churn.

**Hard cap:** `max_iterations = 4`. On `max-iter-reached` saturation signal, the snowball log records the cap-firing and the user can decide whether to re-invoke with a relaxed cap or accept the recall ceiling.

## 7. Outputs

### Files written

- **`references/REFERENCES.md`** — populated three-table format per Phase 4. Append-or-overwrite per the idempotency contract (§Preconditions clause 4): empty file → write fresh; partial file → refuse with `ALREADY_INITIALIZED`.

- **`reviews/snowball_log.md`** — append-only procedure trace. Per-iteration rows: `iteration_index`, `seed_set_size`, `backward_admits` (split: `_local` / `_external`), `forward_admits` (same split), `new_admits`, `rate`, `saturation_signal`, `wiki_access_mode`, `graph_stub_seeds`. Opening row records `seed_phase_admits`, ε, max_iterations, the per-iteration `interaction_id` UUIDs. Closing row records the final pool size and per-table breakdown (core / snowball / cited-via). The file carries the `<!-- scholar-gateway-contract: v0.1 -->` top-of-file marker per §3 Phase 3.

- **`reviews/external_verification_log.md`** — rows appended per Phase 3 step 1; canonical Rule 7a row shape per `EXTERNAL_VERIFIERS.md §5`.

- **`${wiki_path}/wiki/sources/<key>.md`** stubs — when `wiki_linked: true`, one per snowball admission (§4).

- **`${wiki_path}/wiki/log.md`** — single appended entry summarising the snowball pass and listing the new stubs.

### State updates (via the Planner, not directly)

- `reviews/phase_state.json` — Planner writes `references_initialized: true` to the target section after SK-33's clean exit, and appends a `seed_snowball_signed` row (trigger 31) to the section's `phase_entry_log`.

- `reviews/classification.md` — Planner writes `references_initialized: true` to the project-level frontmatter on first-section completion (per architecture plan §5.2 Edit-1).

## 8. Failure modes

| Failure | Detection | Handling |
| --- | --- | --- |
| Scholar Gateway returns `unique_articles: 0` for an iteration's queries | Phase 2 zero-admit | Log as `EXTERNAL_RECALL_ZERO`; iteration's `rate` is 0; saturation triggers immediately. The user is informed that the section's claim register may be too narrow or in a niche field; SK-35 escalates to MAJOR-finding when the Generator drafts ungrounded claims. |
| Scite unreachable for retraction check | Phase 3 step 2 | Per `EXTERNAL_VERIFIERS.md §7` failure-mode contract: log `[VERIFIER UNREACHABLE — Scite]` in the verification log row's Result column. Do NOT silently fall back to memory. Re-attempt at Ph2 entry. |
| Wiki-graph contradicts a Class 1 finding (e.g., graph asserts paper A cites paper B, but Scholar Gateway returns no such edge) | Phase 2 cross-check | Log as `GRAPH_VS_EXTERNAL_DISAGREEMENT`; the higher-confidence layer wins (Class 1 over graph if graph confidence is INFERRED; graph wins if graph confidence is EXTRACTED and Scholar Gateway returned an UNCERTAIN result). The disagreement is preserved as a `[graph-disagrees]` annotation in `snowball_log.md` for later audit. |
| Admitted paper is later flagged as retracted at re-check | Phase 3 step 2 (or later round) | Remove from REFERENCES.md; emit BLOCKER finding via the Evaluator's Step 8 register. |
| In-loop wiki write fails (disk error, permission, conflicting edit) | Phase 4 atomic-rename | Roll back the partial stub; log `WRITE_FAILURE` in `snowball_log.md`; the snowball pool itself is preserved (the wiki stub is downstream of pool admission). User can re-run SK-15 manually to backfill the missing stubs. |
| Concurrent SK-33 invocations on the same project's REFERENCES.md | Phase 4 lock contention | Single-writer convention: SK-33 writes `references/REFERENCES.md.tmp` then atomic-rename per the existing `phase_state_schema.md §5` pattern. Second invocation blocks on the lock; retries on release. |

## 9. What you do NOT do

1. **Do NOT edit manuscript prose.** SK-33 is read-only against `manuscript/`. The Generator at Ph1 Step 6 reads the populated REFERENCES.md and drafts against it.

2. **Do NOT promote `wiki/sources/` stubs to `grounding_status: full`.** Only a direct-read pass (SK-17 at M5) does that. The in-loop write-back (§4) creates `stub` entries only.

3. **Do NOT auto-admit AMBIGUOUS graph edges.** They surface as candidates for user review; admission requires explicit user opt-in via `admit_ambiguous_edges: true` in `classification.md`.

4. **Do NOT exceed `max_iterations`.** Even if `rate ≥ ε` at iteration 4, halt and surface the cap-firing. The user decides whether to relax.

5. **Do NOT silently fall back to training memory when a verifier is unreachable.** Per Rule 7a failure-mode contract, log `[VERIFIER UNREACHABLE]` and proceed in degraded mode; never substitute training-data recall for a Class 1 hit.

6. **Do NOT re-run graphify.** If the graph is stale, log `[graph-stale]` and proceed with external-only iteration (graceful degradation per §Preconditions clause 5). Re-running graphify is the user's decision because it modifies the wiki.

7. **Do NOT modify `${wiki_path}/wiki/concepts/` or `wiki/syntheses/`.** Concept-page retrofit is SK-16's job. Synthesis authoring is SK-14's job. SK-33 only writes to `wiki/sources/` (stubs) and `wiki/{index,log}.md` (append-only).

8. **Do NOT skip the per-iteration `interaction_id` regeneration.** Each iteration is a distinct Scholar Gateway "episode" per the tool's contract; reusing a UUID across iterations violates `EXTERNAL_VERIFIERS.md §2`.

## 10. Trigger vocabulary

- "Ph1 seed" · "snowball discovery" · "build references" · "seed the corpus" · "/seed-snowball-discovery"
- Auto-invoked by `run-phase-1` Step 4.5 when the section's `references_initialized` is `false` or absent and `references/REFERENCES.md` does not exist (per architecture plan §5.2 Edit-1).
- NOT triggered for incremental extension at Ph2; that is SK-35 `extend-snowball-incremental`.

## 11. Sibling skills

- **Pre-seed predecessor:** `SK-36 inherit-snowball-from-wiki` — auto-invoked at Phase 0 when `wiki_linked: true`, `inherit_snowball: true`, and `graph.json` is fresh. SK-36 pre-populates `seed_set` with adjacent-community papers from prior projects; SK-33 then saturates via claim-derived snowball from that starting pool. SK-36 is a no-op on first-run wikis with no accumulated community structure.
- **Downstream consumers:** `SK-15 backfill-source-stubs-from-references` (consumes the populated REFERENCES.md for terminal-stage wiki backfill); `SK-34 claim-coverage-audit` (Ph2 entry; reads REFERENCES.md against the Ph1 draft); `SK-35 extend-snowball-incremental` (Ph2 in-loop; extends the snowball pool on uncovered claims).
- **Audit:** `skills/grounding-audit` Phase 2.5 Category 7 (Rule 7a annotations) spot-checks SK-33's verification log rows; Category 8 (graph-grounding) traces graph-local admissions back to `graph.json` nodes.

## Notes on tier and scope

**Package-tier skill.** Applies to any project under the harness with `wiki_linked: true | false`; the dual-path contract preserves portability for non-wiki-linked projects. Calibrator tier: **executor** (Sonnet — Generator-class structured output, per `MODEL_ALLOCATION.md §2`).
