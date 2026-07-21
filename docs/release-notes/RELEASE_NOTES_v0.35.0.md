# v0.35.0 — Semantic re-pin and Planner rebind hardening

## Outcome

The semantic-register workflow is now closed from graph audit through project
binding. A real epoch-7 re-pin was produced from the stabilized semantic graph,
and the package now includes the previously missing production transaction by
which Planner verifies and applies the resulting project request.

## Semantic graph contract

- Codex and Claude Code are accepted semantic-audit reviewers under the same
  exact provenance, count, and row-lineage checks.
- Single-reviewer legacy artifacts and multi-reviewer artifacts remain
  compatible without discarding reviewer identity.
- Derived normalized labels are recomputed and verified.
- Valid undirected endpoint orientation no longer creates false drift.
- Legacy graph writers refuse governed semantic graph states.

The applied live graph contains 2,044 nodes and 2,900 links. Its stabilization
receipt records 361 fully supported sampled semantic relations, zero unclear or
unsupported samples, zero missing sources, zero retired paths, and zero endpoint
divergence.

## Re-pin and project rebind

The profile is pinned at epoch 7. The re-pin writer still cannot edit
`phase_state.json`; it publishes a pending request only. Planner applies that
request with:

```text
python scripts/assignment_milestone_checkpoint.py rebind-reader-policy --project-root <project-root>
```

The transaction refuses open rounds and malformed requests, verifies profile
and ledger identity, writes resolver bytes before authoritative state, preserves
G/H/VE transitions, detects concurrent changes, and archives the request only
after state read-back succeeds.

## Compatibility

The public plugin command menu is unchanged. Existing old-epoch rounds retain
their evidence; a pending request blocks only a new-cycle opening. Project-local
milestone or handoff blockers remain visible after rebind and are not silently
rewritten by the policy transaction.
