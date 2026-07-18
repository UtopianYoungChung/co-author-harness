# Expected iteration log — `basic_graph_traversal`

Scenario inputs: `graph.json` (4 nodes covering the snowballing-methodology + systematic-literature-review communities, 5 EXTRACTED edges) and `seed_set.json` (3 seeds: 2 graph-resident, 1 graph-stub).

## Iteration 1 expected behaviour

`lookup_node_by_doi_or_pdf_path` resolves seeds against `graph.json` nodes per the SKILL.md §3 Phase 2 lookup-keying contract. Resolution outcomes:

The seed `wohlin-2014` has `pdf_path: wiki/sources/wohlin-2014.md`, which matches `n1.source_file` exactly — the primary keying path resolves it to node `n1`. The seed `barros-justo-2021` resolves to `n2` by the same primary path. The seed `kuhn-1962-structure-of-scientific-revolutions` has `pdf_path: null` and no graph node carries an `(author, year) = (Kuhn, 1962)` pair — neither the primary nor the fallback keying resolves it, so it joins the `graph_stub_seeds` set.

Graph-local traversal proceeds for the resolved seeds. Backward traversal of `n1` (papers `n1` cites) yields `{n4}` via the `n1 → n4` EXTRACTED edge. Forward traversal of `n1` (papers that cite `n1`) yields `{n2, n3}` via the `n2 → n1` and `n3 → n1` EXTRACTED edges. Backward traversal of `n2` yields `{n1, n3}` via the `n2 → n1` and `n2 → n3` edges. Forward traversal of `n2` yields `∅` (no edges in the fixture point at `n2`). Aggregating across both resolved seeds and deduplicating: `backward_local ∪ forward_local = {n1, n2, n3, n4}`.

External fall-through is invoked only for the graph-stub seed `kuhn-1962-...`. The fixture does not stub Scholar Gateway responses; for the purposes of this log, assume the call returns one paper-shaped admission, denoted `external_kuhn_1`, and one verification-log row is appended for it.

The per-claim admission filter then prunes the candidate set to those resolving at least one open claim from `seed_set.json`'s claim register. For this fixture both `n3` (Felizardo — methodologically adjacent) and `n4` (Kitchenham — SLR foundation) plausibly resolve at least one claim about saturation behaviour; `n1` and `n2` are already in the seed set and thus excluded by the `\ S_{I-1}` operator. The `external_kuhn_1` admission's claim relevance depends on the live Scholar Gateway result and is left abstract here.

The expected `new_admits` set after deduplication and seed exclusion is `{n3, n4} ∪ {external_kuhn_1}`.

## Expected log row

```json
{
  "phase": "ITERATE",
  "iteration": 1,
  "seed_set_size": 3,
  "new_admits": 3,
  "rate": 1.0,
  "saturation_signal": "continue",
  "graph_local_admits": 2,
  "external_admits": 1,
  "graph_stub_seeds": 1,
  "wiki_access_mode": "filesystem"
}
```

`rate = |new_admits| / max(1, |S_{I-1}|) = 3/3 = 1.0`, well above the default `ε = 0.05`, so the iteration continues. `wiki_access_mode` is logged as `filesystem` because the fixture exercises the default access path (the `dual_path_access_modes/` scenario covers the alternative settings explicitly).

## Cross-references

- `skills/seed-snowball-discovery/SKILL.md §3 Phase 2` — pseudocode and lookup-keying contract.
- `skills/graph-grounding-overlay/SKILL.md` — graph.json schema (node + edge fields).
- `docs/superpowers/plans/2026-04-26-snowball-reference-architecture.md §5.5.1` — architectural specification of the iteration step.
- `docs/release-notes/RELEASE_NOTES_v0.10.0.md §2.S1.5` — audit table mapping this fixture to the architecture sub-clauses it validates.
