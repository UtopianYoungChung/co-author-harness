# Expected iteration log — `ambiguous_edge_no_admit`

Scenario inputs: `graph.json` (3 nodes in the requirements-elicitation community; 3 edges, one of which carries `confidence: AMBIGUOUS`) and `seed_set.json` (1 graph-resident seed `goguen-linde-1993`, resolving to `n1` by primary keying).

## Iteration 1 expected behaviour

The single seed `goguen-linde-1993` resolves to node `n1` via `pdf_path = source_file = wiki/sources/goguen-linde-1993.md` (primary keying path per SKILL.md §3 Phase 2 lookup-keying contract). Graph-stub set is empty; no Scholar Gateway fall-through is invoked for this iteration.

Backward traversal of `n1` (papers `n1` cites) yields `∅` — the fixture has no outgoing edges from `n1`.

Forward traversal of `n1` (papers that cite `n1`) examines edges with `target = n1`. Two such edges exist in the fixture:

The first is `n2 → n1` with `confidence: EXTRACTED` and `confidence_score: 0.93`. This edge satisfies the `confidence_floor="EXTRACTED"` admission criterion in the SKILL.md §3 Phase 2 pseudocode (line 89) and admits `n2` to `forward_local`.

The second is `n3 → n1` with `confidence: AMBIGUOUS` and `confidence_score: 0.42`. This edge **does NOT admit** `n3` to `forward_local`. Per SKILL.md line 119 ("AMBIGUOUS edges are never auto-admitted; they surface as `[graph-ambiguous]` candidates in the snowball log for user review") and §9 not-doing rule 3 ("Do NOT auto-admit AMBIGUOUS graph edges. They surface as candidates for user review; admission requires explicit user opt-in via `admit_ambiguous_edges: true` in `classification.md`"), the candidate `n3` is logged but excluded from `new_admits`.

The candidate set therefore is `{n2}` (from forward EXTRACTED traversal). After per-claim filter and deduplication against `S_0 = {n1}`, `new_admits = {n2}`. The AMBIGUOUS candidate `n3` is preserved as a `[graph-ambiguous]` annotation in the snowball log for the user to adjudicate before iteration 2 (or to defer indefinitely).

## Expected log row

```json
{
  "phase": "ITERATE",
  "iteration": 1,
  "seed_set_size": 1,
  "new_admits": 1,
  "rate": 1.0,
  "saturation_signal": "continue",
  "graph_local_admits": 1,
  "external_admits": 0,
  "graph_stub_seeds": 0,
  "graph_ambiguous_candidates": ["n3"],
  "wiki_access_mode": "filesystem"
}
```

The optional `graph_ambiguous_candidates` field surfaces the deferred AMBIGUOUS candidates by node id. SKILL.md §3 Phase 2 does not mandate this exact field name, but the snowball log MUST preserve the `[graph-ambiguous]` annotations in some accessible form so the user can review and either opt them in (via `admit_ambiguous_edges: true`) or accept the exclusion. This fixture proposes the field name as a documentary suggestion for a future SKILL.md hardening; the logged form is up to implementation as long as the auditability invariant holds.

## What this fixture validates

The negative case for the edge confidence policy. A naïve implementation that admits every edge regardless of confidence would produce `new_admits = {n2, n3}` and a `rate` of 2.0 — twice the correct value — silently inflating the snowball pool with low-confidence admissions. The fixture's expected log row makes the correct exclusion explicit, so any future Python validator can assert the AMBIGUOUS edge target is absent from the admission set.

## Cross-references

- `skills/seed-snowball-discovery/SKILL.md §3 Phase 2 (Edge confidence policy)` and `§9 (not-doing rule 3)`.
- `skills/graph-grounding-overlay/SKILL.md` — confidence vocabulary `{EXTRACTED, INFERRED, AMBIGUOUS}` defined.
- `docs/superpowers/plans/2026-04-26-snowball-reference-architecture.md §5.5.1` — "AMBIGUOUS edges are never auto-admitted; they surface as `[graph-ambiguous]` candidates in the snowball log for user review."
