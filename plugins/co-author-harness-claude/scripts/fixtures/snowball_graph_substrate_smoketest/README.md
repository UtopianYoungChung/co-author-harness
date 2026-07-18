# `snowball_graph_substrate_smoketest/` — scenario fixtures for SK-NEW-A graph-substrate iteration

These fixtures exercise the graph-substrate variant of the snowball iteration step described in `skills/seed-snowball-discovery/SKILL.md §3 Phase 2` and architecturally specified in `docs/superpowers/plans/2026-04-26-snowball-reference-architecture.md §§5.5.1, 5.5.2, 5.5.6`. Unlike `artefact_frontmatter_smoketest/` and `phase_state_smoketest/`, these fixtures are not yet exercised by a Python validator — they are **scenario-based reference fixtures** that document expected SK-NEW-A behaviour for a future automated harness and for human review during the v0.10.0 rollout.

**Stage of origin:** v0.10.0 Stage S1.5 (hardening pass over the §5.5.1/§5.5.2/§5.5.6 content absorbed into S1's `f9411d5` / `5fbc0c7`). See `docs/release-notes/RELEASE_NOTES_v0.10.0.md §2.S1.5` for the audit table that motivated this fixture set.

## Layout

```
snowball_graph_substrate_smoketest/
├── README.md
├── basic_graph_traversal/
│   ├── graph.json                      # mock graphify output (4 nodes, 5 edges)
│   ├── seed_set.json                   # 3 seeds: 2 graph-resident, 1 graph-stub
│   └── expected_iteration_log.md       # expected per-iteration log fields
├── ambiguous_edge_no_admit/
│   ├── graph.json                      # 3 nodes, 3 edges incl. 1 AMBIGUOUS
│   ├── seed_set.json                   # 1 graph-resident seed
│   └── expected_iteration_log.md       # AMBIGUOUS target NOT admitted
└── dual_path_access_modes/
    ├── README.md                       # access-mode contract walk-through
    ├── auto_default.md                 # access_mode: auto (detect-and-prefer)
    ├── filesystem_forced.md            # access_mode: filesystem (force-fs)
    └── mcp_fastpath_required.md        # access_mode: mcp_fastpath (refuse-on-absent)
```

## What each scenario validates

**`basic_graph_traversal/`** — the load-bearing happy path. Validates that with a mixed seed set (some seeds graph-resident, others graph-stub), the iteration admits via graph-local traversal first and only falls through to Scholar Gateway for graph-stub seeds. Confirms the `graph_local_admits`, `external_admits`, and `graph_stub_seeds` log fields populate as the SKILL.md §3 Phase 2 pseudocode specifies. This is the canonical fixture that any future Python validator must reproduce.

**`ambiguous_edge_no_admit/`** — the negative case for SKILL.md §3 Phase 2 edge confidence policy. Validates that an AMBIGUOUS-confidence edge does NOT auto-admit its target into the iteration's `new_admits` set, and that the candidate surfaces as a `[graph-ambiguous]` annotation in the snowball log. Cross-references SKILL.md §9 not-doing rule 3 ("Do NOT auto-admit AMBIGUOUS graph edges").

**`dual_path_access_modes/`** — the access-mode contract. Three companion scenarios document expected `wiki_access_mode` log values under each of the three explicit access settings (`auto`, `filesystem`, `mcp_fastpath`). No graph.json needed; the scenarios document the access-mode probe and detection contract per SKILL.md §5.

## Rules

All fixtures are **static** (read-only). Each `expected_iteration_log.md` documents the load-bearing assertions in narrative form, with a JSON-shaped block at the bottom showing the literal expected log row for any future automated validator. Scenarios that exercise multiple SKILL.md sections cite the section number inline so the audit trail is preserved.

The two `graph.json` files conform to the SK-20 schema per `skills/graph-grounding-overlay/SKILL.md` Phase 1 — node fields `id, label, source_file, source_location, author, captured_at, community, norm_label`; edge fields `relation, confidence, confidence_score, source_file, source_location, weight, source, target`. Confidence values are drawn from the SK-20 vocabulary `{EXTRACTED, INFERRED, AMBIGUOUS}`.

## Out of scope (deferred to later passes)

A Python validator script that executes the iteration logic against these fixtures and asserts the expected outputs. The validator's authoring cost was not justified by reuse at S1.5; reconsider when SK-NEW-C lands at S4 and a second consumer of the same iteration logic exists.

Atomic-rename collision fixtures for the in-loop wiki write-back (SKILL.md §4). These would require a multi-process Python harness; deferred indefinitely.

Synthesis-alignment fixtures for SK-NEW-B's coverage fast-path. Those belong to S4.5 per the architecture plan §6.6 and are out of scope for SK-NEW-A's hardening.

End-to-end pilot probes against a real wiki + real Scholar Gateway. Those belong to the v0.10.0 RC integration replay per strategy §6.3.

## Rebuilding

If SK-NEW-A's iteration step changes (e.g., a new admission filter is introduced or the per-iteration log fields are renamed), update the affected `expected_iteration_log.md` in lockstep with the SKILL.md edit. The fixtures are part of the SKILL.md's contract surface — drift between them is a hardening regression.
