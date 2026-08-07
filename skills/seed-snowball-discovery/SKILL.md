---
name: seed-snowball-discovery
description: "Ph1 entry skill — assemble references/REFERENCES.md from a section's claim register via Wohlin-style snowball saturation. Current operating mode: external-verifier-only while graph authority unavailable; SK-36 Phase 0 is an immediate no-op; Class 1 verifier fall-through; read-only Wiki page consultation; dual-path access (filesystem / mcp_fastpath). Stops on rate < ε (default 0.05) or 4 iterations. Trigger: /seed-snowball-discovery, fresh section, or references_initialized:false."
trigger: when the user invokes /seed-snowball-discovery, when run-phase-1 Step 4.5 dispatches the seed-snowball gate on a fresh section, when references/REFERENCES.md is absent, or when classification.md carries references_initialized:false
version: 1.0
---

# seed-snowball-discovery — Ph1 Entry Reference Scaffolding



## FAIL-CLOSED: Canonical Wiki mutation unavailable

Before any canonical Wiki mutation is re-enabled, resolve this exact tuple:

```python
resolve("co_author_harness", "curate", "knowledge_graph", "wiki_page")
```

Use only the returned `destination_path`; do not substitute a literal Wiki
path. The installed manifest resolves this tuple to WIKI_CURATED, but route
declaration is destination-only and does not enable mutation. `RoutingError` is
a hard stop. Read-only Wiki consultation may continue under the existing rules,
but it does not authorize writes. While the governed transaction is unavailable,
retain the structured deferred result below.

Canonical Wiki create/overwrite/append/promote is **unavailable**.

For any path that would mutate `knowledge/LLM wiki/wiki/**` (including retired
`wiki/index.md` / `wiki/log.md` targets), or that would report Wiki write success:

1. Do **not** create, overwrite, or append any canonical Wiki page or stub.
2. Do **not** write an `m5_wiki_ingest` success trigger.
3. Do **not** fabricate `wiki_page_key` or Wiki success fields.
4. Continue project-local outputs: `references/REFERENCES.md`, `reviews/snowball_log.md`,
   `reviews/external_verification_log.md`, and related project-local artifacts.
5. Read-only Wiki **page** consultation remains allowed (not graph-as-authority).
6. For the Wiki-mutation portion of the skill, record:

```yaml
status: deferred
reason_code: WIKI_WRITE_TRANSACTION_UNAVAILABLE
wiki_page_key: null
```

Research completion, approval, and release remain available.

## FAIL-CLOSED: Graph authority unavailable (external-verifier-only)

Governed graph authority is **unavailable**
(`GRAPH_GOVERNED_GENERATION_UNAVAILABLE`). Graph-independent reader-profile v2
keeps the semantic centroid dormant; mechanical digests supply no warrant.
While `governed_available: false`:

1. **External-verifier-only iteration.** No graph-local auto-admission.
2. Graph topology is not seed/snowball authority.
3. Do **not** apply any “graph wins” disagreement rule against Class 1 verifiers.
4. SK-36 pre-seed is a no-op under the same gate; do not load graph-derived `pre_seed.json` as authority.
5. Read-only Wiki **page** consultation may continue; graph-as-authority must not.
6. No graph edge—`EXTRACTED`, `INFERRED`, or `AMBIGUOUS`—may be surfaced as an admission candidate or admitted; ignore any legacy `admit_ambiguous_edges` setting.
7. Record `graph_authority_reason: GRAPH_GOVERNED_GENERATION_UNAVAILABLE` in `reviews/snowball_log.md`.

Project-local research and external-verification artifacts continue.

**Grounding basis:** `docs/superpowers/plans/2026-04-26-snowball-reference-architecture.md §§4 (mechanised procedure), 5.1 (skill specification), 5.5.1 (graph substrate), 5.5.2 (deferred Wiki write-back (`WIKI_WRITE_TRANSACTION_UNAVAILABLE`)), 5.5.6 (dual-path access)`; `references/GROUNDING_PROTOCOL.md §§Rule 4 (quote-before-attribute), Rule 6 (no gap-filling), Rule 7a (external verification)`; `references/EXTERNAL_VERIFIERS.md §§1.5 (wiki-first discovery ordering), 2 (Class 1/1.5/2/3 verifier registry), 3.1 (Scholar Gateway render contract)`; `skills/graph-grounding-overlay/SKILL.md` (SK-20; Coupling E.2 graph schema and graph-staleness precondition pattern); `skills/backfill-source-stubs-from-references/SKILL.md` (SK-15; the deferred Wiki write-back (`WIKI_WRITE_TRANSACTION_UNAVAILABLE`) inherits SK-15's stub template and atomic-rename pattern); Wohlin 2014 (`10.1145/2601248.2601268`; methodological anchor; PDF in Zotero `FXJ6M8ED`).

---

## 1. What this stage does

`seed-snowball-discovery` is the **Ph1 entry skill** for projects whose `references/REFERENCES.md` does not yet exist or is not yet populated for the section under draft. It assembles a saturated reference pool from the section's claim register via a mechanised version of the snowball method (Wohlin 2014) — a seed phase that consults the wiki-first discovery order (`EXTERNAL_VERIFIERS.md §1.5`), an iterate phase that traverses backward and forward citations until saturation, and a verify phase that emits a Rule 7a verification log row for every admitted paper.

The skill is the **operationalisation** of `EXTERNAL_VERIFIERS.md §1.5`, which mandates the wiki → Zotero → Class 1 ordering for *discovery* but does not name an executor. SK-33 is the named executor.

Output: a populated `references/REFERENCES.md` with three tables (`core corpus`, `snowball`, `cited-via`) per the format established by SK-15's input contract; an append-only procedure trace at `reviews/snowball_log.md`; and rows appended to `reviews/external_verification_log.md` for every Class-1-fall-through admission.

The skill does **not** edit manuscript prose. It does not run at Ph2 or later (SK-35 handles incremental extension at Ph2). It does not promote `wiki/sources/` stubs to `grounding_status: full-read` (that is SK-17's job at M5).

## 2. Preconditions

Before invoking this skill, verify all of the following. On any failure that is not gracefully degradable, abort with a clear `SK-33: no-op (<reason>)` message and return without producing artefacts.

1. **`reviews/classification.md` exists and is parseable.** Reads `paper_type`, `p_stage`, `venue`, and (when present) the new v0.10.0 fields `claim_coverage_threshold`, `inherit_snowball`, `pre_seed_cap`. If absent or unparseable: no-op with `CLASSIFICATION_MISSING`. The user must run `/classify-manuscript` first.

2. **A claim register is resolvable for the target section.** Either (a) `reviews/revision_plan.md` declares the section's planned claims in its outline, OR (b) `manuscript/<section>.md` exists with at least one heading whose body contains drafted claims. If neither: no-op with `NO_CLAIM_REGISTER` — the user must declare the section's intended claims before snowball can seed.

   *Process-readiness note (Abbott, 2026-06-28).* The snowball is the **midphase, narrowed** search regime where Abbott licenses brute force (`references/abbott_2014_research_process_guidelines.md §§3–4`). It presupposes the **preliminary** work is done: a stabilized design/question and an orienting bibliography for the section. A resolvable claim register is the harness's proxy for that readiness — a snowball seeded on an unstabilized question saturates on a poorly-chosen seed. If the claims read as still-exploratory, prefer browsing/bibliography first and record the gap rather than forcing saturation.

3. **At least one Class 1 verifier is reachable.** Probe Scholar Gateway via a whoami-class call (a minimal `semanticSearch` query with `topN: 1`). If unreachable AND no wiki is linked AND Zotero is unreachable, no-op with `NO_REACHABLE_VERIFIER` — the seed phase has no source. If Scholar Gateway is unreachable but Zotero is reachable, proceed in degraded mode (Zotero-only seed; Class 1 fall-through deferred until verifier returns).

4. **Idempotency check.** Read `reviews/phase_state.json` for the target section. If `references_initialized: true` and `references/REFERENCES.md` exists with non-empty core corpus and snowball tables, no-op with `ALREADY_INITIALIZED`. The user must explicitly delete the field or invoke `/extend-snowball-incremental` (SK-35) to extend the existing pool.

5. **Optional graph-file age note (when `wiki_linked: true`).** Resolve `wiki_path` from the project CLAUDE.md. If `${wiki_path}/graphify-out/graph.json` exists, compare its `captured_at` against `references/REFERENCES.md` and `manuscript/<section>.md` `Last updated:` markers. If the file is older, emit a `[graph-stale]` warning into `reviews/snowball_log.md`'s opening row. Proceed with **external-verifier-only** iteration regardless; do not treat the graph file as admission authority. Re-running graphify remains a user decision.

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

### Phase 0 — Pre-seed inheritance (inert while graph authority unavailable)

While `GRAPH_GOVERNED_GENERATION_UNAVAILABLE` / `governed_available: false`, SK-36
`inherit-snowball-from-wiki` is an **immediate no-op**. Do not invoke SK-36 as a live
seed-authority path. Do not load `reviews/pre_seed.json` (or any graph-derived pre-seed
list) as authority for the initial `seed_set`.

Proceed into Phase 1 with an empty `seed_set` and append a Phase 0 row to
`reviews/snowball_log.md`: `phase_0_invoked: false`, `pre_seed_count: 0`,
`sk36_noop_reason: GRAPH_GOVERNED_GENERATION_UNAVAILABLE`, plus
`[phase-0: no-pre-seed]`.

## Future — Phase 4+ only (inert)

Wiki-community pre-seed inheritance via SK-36 is reserved for a future Phase-4+
activation. No executable unlock steps are defined in this skill while graph authority
is unavailable.

### Phase 1 — Seed assembly

Per `EXTERNAL_VERIFIERS.md §1.5`, the seed phase consults sources in strict order. The Class 1 verifier ordering inside the external tier is Scholar Gateway first, then Consensus for cross-check on contested claims (per architecture plan §10 open-question Q3 default).

1. Extract the **claim register** for the target section. From `reviews/revision_plan.md` (preferred) or `manuscript/<section>.md`:
   - Each claim is a proposition that requires evidence (existential, comparison, mechanism, result, theoretical commitment).
   - Output: `claims = [(claim_text, claim_kind, section_locus), ...]`.

2. **Wiki-first consultation (when `wiki_linked: true`).** Per `EXTERNAL_VERIFIERS.md §1.5` step 1: read relevant `${wiki_path}/wiki/sources/*.md`, `wiki/concepts/*.md`, and `wiki/syntheses/*.md`. Admit any grounded Wiki **page** that resolves at least one claim into the seed set with provenance `[seed: wiki]`. Do **not** admit from graph-report community/hub structure as authority. Log a `Wiki-first` line in `reviews/revision_plan.md` per `EXTERNAL_VERIFIERS.md §3 Planner clause`.

3. **Zotero library consultation.** Per §1.5 step 2: invoke `mcp__zotero__zotero_semantic_search` with each claim's text as the natural-language query. Admit returns above the library-relevance threshold (default 0.6) with provenance `[seed: zotero]`. The Zotero ledger is a Class 2 verifier here (the user already curated it); admissions become Class 1 only when a subsequent iteration step's external probe corroborates them.

4. **External Class 1 fall-through.** Per §1.5 step 3, only when (2) and (3) yield fewer than `min_seed_per_claim` (default 3) admits per claim: invoke Scholar Gateway (the host's **Scholar Gateway** `semanticSearch` tool — UUID-namespaced per host; resolve the live namespace at session start via tool search, never hardcode it). The `interaction_id` UUID is generated **once per snowball iteration** and reused across all sub-queries within that iteration. Each external admit gets provenance `[seed: scholar-gateway]` and immediately triggers a verification-log row.

5. **Cross-check on contested claims (optional).** When the section's classification carries `p_stage: P2` (the most rigorous register), every claim with only a single Class 1 hit is cross-checked against Consensus (the host's **Consensus** `search` tool — UUID-namespaced per host; resolve the live namespace at session start via tool search, never hardcode it). A CONTESTED return surfaces in `snowball_log.md` as a Phase 1 contention marker; the claim continues into the iterate phase but with an annotation that the Generator must surface the contestation in prose at Ph1 drafting.

### Phase 2 — Iterate (external-verifier-only while graph authority unavailable)

While `GRAPH_GOVERNED_GENERATION_UNAVAILABLE` / `governed_available: false`, iteration uses
**external Class 1 verifiers only**. Do not compute topology-based backward/forward admits,
do not maintain stub-seed admission channels from graph files, and do not auto-admit from
graph edge files.

```
SNOWBALL ITERATION (external-only):
  S_0 = seed_set  (from Phase 1; no graph-authority pre-seed)
  I = 0

  while True:
    I = I + 1
    backward_external, forward_external = empty, empty
    for s in S_{I-1}:
      backward_external += SCHOLAR_GATEWAY_BACKWARD(s)
      forward_external  += SCHOLAR_GATEWAY_FORWARD(s)

    candidates = backward_external union forward_external
    new_admits = {c in candidates : c resolves at least one open claim} minus S_{I-1}
    rate = |new_admits| / max(1, |S_{I-1}|)
    log(ITERATE, I, |new_admits|, rate, mode=external_verifier_only,
        graph_authority_reason=GRAPH_GOVERNED_GENERATION_UNAVAILABLE)

    if rate < epsilon or I >= max_iterations:
      break
    S_I = S_{I-1} union new_admits
```

**Per-iteration `interaction_id`.** Every Scholar Gateway sub-query within iteration `I` uses the same UUID, generated once at the iteration entry. Iteration `I+1` generates a new UUID.

### Phase 3 — Verify and log

For every paper admitted across Phases 1 and 2 that fell through to a Class 1 verifier:

1. Append a row to `reviews/external_verification_log.md` per `EXTERNAL_VERIFIERS.md §5`. Date / Agent / Claim (short) / Verifier / Query (verbatim from `provenance.query_as_executed`) / Returned ID (DOI) / Returned title / Result (MATCH / CONTESTED / NOT FOUND / UNREACHABLE).

2. Run Class 3 retraction check (`mcp__zotero__scite_check_retractions`) on every admitted paper. A `retracted: true` result is binding under Rule 7a — the paper is removed from the snowball pool and the finding is logged as a BLOCKER. If Scite is unreachable, log `[VERIFIER UNREACHABLE — Scite]` in the verification row's Result column and re-attempt at Ph2 entry.

3. Honour the Scholar Gateway render contract per `EXTERNAL_VERIFIERS.md §3.1`: every Scholar-Gateway-derived row carries the per-search provenance line; the snowball log file carries the `<!-- scholar-gateway-contract: v0.1 -->` top-of-file marker **written only if the file is being created for the first time** (if `reviews/snowball_log.md` already exists from a prior SK-36 Phase 4 no-op row, do not write the header again); the session footer is rendered once per snowball pass at the end of `snowball_log.md`.

### Phase 4 — REFERENCES.md emission

Author or rewrite `references/REFERENCES.md` per the SK-15 input format:

- **Core corpus.** Papers admitted in Phase 1 with provenance `[seed: wiki]` or `[seed: zotero]` (i.e., already in the user's curated or wiki page layer). While graph authority is unavailable, Phase 0 contributes no SK-36 pre-seed rows.
- **Snowball.** Papers admitted in Phase 2 (any iteration), grouped by iteration depth (`Iteration 1`, `Iteration 2`, ...). While graph authority is unavailable, Phase 2 does not perform graph traversal admits. Snowball rows come from external-verifier admits only.
- **Cited-via.** Papers referenced from inside read sources but not directly verified — these are flagged for a follow-up direct read; SK-33 does not auto-stub them.

Each table row carries the canonical fields per SK-15: `project_key`, `wiki_key` (if `wiki_linked`), `authors`, `year`, `title`, `venue`, `pdf_path` (when Zotero PDF is attached), `provenance_tag`.

## 4. Canonical Wiki write-back — deleted

In-loop canonical source-page stub creation, atomic rename into the Wiki vault,
and Wiki operations-log appends are **removed**. Record the structured deferred
result from the FAIL-CLOSED section. Do not retain stub frontmatter templates or
success reporting for Wiki mutation.

## 5. Dual-path access contract (read-only)


Per architecture plan §5.5.6, all wiki-side **reads** resolve through a dual-path contract that lets the implementation behave identically whether the optional `llm-wiki` MCP plugin is connected.

**Default — filesystem reads.** Use `Read`, `Glob`, and `Grep` over `${wiki_path}/wiki/{sources,concepts,syntheses}/*.md` (directory listing; retired `wiki/index.md` / `wiki/log.md` are not write targets). Semantic queries fall back to lexical/Jaccard matching at the alignment-threshold default (0.3). Graph-report / graph.json files are not operational seed inputs while graph authority is unavailable.

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

- **`reviews/snowball_log.md`** — append-only procedure trace. Per-iteration rows: `iteration_index`, `seed_set_size`, `backward_admits`, `forward_admits`, `new_admits`, `rate`, `saturation_signal`, `wiki_access_mode`, `graph_authority_reason`. Opening row records `seed_phase_admits`, ε, max_iterations, the per-iteration `interaction_id` UUIDs. Closing row records the final pool size and per-table breakdown (core / snowball / cited-via). The file carries the `<!-- scholar-gateway-contract: v0.1 -->` top-of-file marker per §3 Phase 3.

- **`reviews/external_verification_log.md`** — rows appended per Phase 3 step 1; canonical Rule 7a row shape per `EXTERNAL_VERIFIERS.md §5`.

- **Canonical Wiki pages** — none. Wiki mutation returns `status: deferred` / `WIKI_WRITE_TRANSACTION_UNAVAILABLE` / `wiki_page_key: null`.

### State updates (via the Planner, not directly)

- `reviews/phase_state.json` — Planner writes `references_initialized: true` to the target section after SK-33's clean exit, and appends a `seed_snowball_signed` row (trigger 31) to the section's `phase_entry_log`.

- `reviews/classification.md` — Planner writes `references_initialized: true` to the project-level frontmatter on first-section completion (per architecture plan §5.2 Edit-1).

## 8. Failure modes

| Failure | Detection | Handling |
| --- | --- | --- |
| Scholar Gateway returns `unique_articles: 0` for an iteration's queries | Phase 2 zero-admit | Log as `EXTERNAL_RECALL_ZERO`; iteration's `rate` is 0; saturation triggers immediately. The user is informed that the section's claim register may be too narrow or in a niche field; SK-35 escalates to MAJOR-finding when the Generator drafts ungrounded claims. |
| Scite unreachable for retraction check | Phase 3 step 2 | Per `EXTERNAL_VERIFIERS.md §7` failure-mode contract: log `[VERIFIER UNREACHABLE — Scite]` in the verification log row's Result column. Do NOT silently fall back to memory. Re-attempt at Ph2 entry. |
| Wiki-graph contradicts a Class 1 finding | N/A while graph authority unavailable | Do **not** apply a “graph wins” rule. Prefer Class 1 / external verification. Log `[graph-authority-unavailable]` if a stale graph is consulted read-only for curiosity; it must not admit evidence. |
| Admitted paper is later flagged as retracted at re-check | Phase 3 step 2 (or later round) | Remove from REFERENCES.md; emit BLOCKER finding via the Evaluator's Step 8 register. |
| Concurrent SK-33 invocations on the same project's REFERENCES.md | Phase 4 lock contention | Single-writer convention: SK-33 writes `references/REFERENCES.md.tmp` then atomic-rename per the existing `phase_state_schema.md §5` pattern. Second invocation blocks on the lock; retries on release. |

## 9. What you do NOT do

1. **Do NOT edit manuscript prose.** SK-33 is read-only against `manuscript/`. The Generator at Ph1 Step 6 reads the populated REFERENCES.md and drafts against it.

2. **Do NOT create or promote canonical `wiki/sources/` pages.** Wiki mutation is unavailable; record the structured deferred result only.

3. **Do NOT admit or surface graph edges while graph authority is unavailable.** While `GRAPH_GOVERNED_GENERATION_UNAVAILABLE` / `governed_available: false`, no graph edge—whether `EXTRACTED`, `INFERRED`, or `AMBIGUOUS`—may be surfaced as an admission candidate or admitted. Any legacy `admit_ambiguous_edges` setting, including `true`, is ignored under the same gate.

4. **Do NOT exceed `max_iterations`.** Even if `rate ≥ ε` at iteration 4, halt and surface the cap-firing. The user decides whether to relax.

5. **Do NOT silently fall back to training memory when a verifier is unreachable.** Per Rule 7a failure-mode contract, log `[VERIFIER UNREACHABLE]` and proceed in degraded mode; never substitute training-data recall for a Class 1 hit.

6. **Do NOT re-run graphify.** If the graph is stale, log `[graph-stale]` and proceed with external-only iteration (graceful degradation per §Preconditions clause 5). Re-running graphify is the user's decision because it modifies the wiki.

7. **Do NOT modify `${wiki_path}/wiki/**`.** Read-only consultation only. Project-local writes are limited to REFERENCES, snowball logs, and external-verification artifacts.

8. **Do NOT skip the per-iteration `interaction_id` regeneration.** Each iteration is a distinct Scholar Gateway "episode" per the tool's contract; reusing a UUID across iterations violates `EXTERNAL_VERIFIERS.md §2`.

## 10. Trigger vocabulary

- "Ph1 seed" · "snowball discovery" · "build references" · "seed the corpus" · "/seed-snowball-discovery"
- Auto-invoked by `run-phase-1` Step 4.5 when the section's `references_initialized` is `false` or absent and `references/REFERENCES.md` does not exist (per architecture plan §5.2 Edit-1).
- NOT triggered for incremental extension at Ph2; that is SK-35 `extend-snowball-incremental`.

## 11. Sibling skills

- **Pre-seed predecessor:** `SK-36 inherit-snowball-from-wiki` — while graph authority is unavailable, SK-36 is an immediate no-op (`GRAPH_GOVERNED_GENERATION_UNAVAILABLE`). SK-33 does not depend on SK-36 output for seeding; claim-derived snowball starts from an empty Phase-0 pool.
- **Downstream consumers:** `SK-15 backfill-source-stubs-from-references` (fail-closed; Wiki stub generation deferred); `SK-34 claim-coverage-audit` (Ph2 entry; reads REFERENCES.md against the Ph1 draft); `SK-35 extend-snowball-incremental` (Ph2 in-loop; extends the snowball pool on uncovered claims).
- **Audit:** `skills/grounding-audit` Phase 2.5 Category 7 (Rule 7a annotations) spot-checks SK-33's verification log rows. Category 8 (graph-grounding) does not apply while graph authority is unavailable; do not claim admission traces back to graph nodes.

## Notes on tier and scope

**Package-tier skill.** Applies to any project under the harness with `wiki_linked: true | false`; the dual-path contract preserves portability for non-wiki-linked projects. Calibrator tier: **executor** (Sonnet — Generator-class structured output, per `MODEL_ALLOCATION.md §2`).
