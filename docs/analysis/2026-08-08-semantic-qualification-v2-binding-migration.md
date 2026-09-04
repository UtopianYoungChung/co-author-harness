# Fresh semantic qualification and reader-profile-v2 migration

## Decision scope

This design reopens the 2026-07-25 semantic-reconcile decision only for two
new transactions:

1. qualify a fresh semantic composite from the current reader-policy semantic
   inventory; and
2. migrate one project from a graph-independent reader-profile-v2 binding to
   that qualified semantic composite through a separate Planner application.

The archived 290-page stabilization artifacts are historical evidence only.
No command in this design reads them as transaction input or writes beneath
their directory. The live structural graph remains unchanged.

## Transaction A: semantic qualification

The current contract covers `wiki/sources`, `wiki/concepts`, `wiki/entities`,
`wiki/syntheses`, and the named root page. The full structural graph is retained
in the composite. Its separately held-out `wiki/meta` navigation pages remain
mechanical and do not receive model-produced semantics.

`B:/Agents/knowledge/LLM wiki/scripts/semantic_qualification.py` owns four
explicit stages:

- `plan` snapshots the exact current inventory and structural graph into a new
  `graphify-out/semantic-qualifications/semq-.../` directory and emits bounded
  model prompts. The manifest binds the producer role, exact model identity,
  and every request and prompt hash.
- `candidate` admits only page-bound model outputs with explicit
  `model-textual` or `model-inferential` warrants. It preserves every
  structural node community and writes a separate candidate composite.
- `audit-plan` chooses the deterministic audit sample and requires an auditor
  identity different from the producer identity; the audit binds its distinct
  model identity as well.
- `apply` requires every sampled edge to be independently supported, rechecks
  all input and candidate hashes, publishes the qualified composite, and writes
  the terminal receipt last.

Every stage is current-inventory bound. The base graph and the archived
stabilization directory are preimage/postimage invariants. The rollback record
states that neither protected graph was a mutation target.
Every command also holds the shared Wiki graph-write lock for its complete
read/validate/publish interval.

## Transaction B: package re-pin and project request

`reader_accessibility_policy.py --repin --semantic-graph-path ...` accepts only
paths of the form:

`knowledge/LLM wiki/graphify-out/semantic-qualifications/semq-<UTC>-<nonce>/qualified.graph.json`

The loader fully resolves the qualified graph, verifies its transaction-local
manifest, prompts, requests, outputs, audit submission, audit, rollback record,
receipt, complete transaction inventory, model identities, edge warrants, and seed coverage, and classifies a graph-path
change as a `corpus` delta. A real package profile mutation still requires the
existing explicit confirmation. With `--project-root`, the only project write
is `reviews/repin_rebind_request.json`. That request binds the exact phase-state
preimage, prior v2 binding and resolver, profile and pins, qualified graph,
qualification receipt, exact re-pin ledger bytes, exact canonical event bytes,
and exact package snapshot bytes. A semantic dry run never emits a project
request.

The repin producer does not write `phase_state.json`.

## Transaction C: separate Planner application

The public command is:

`python scripts/assignment_milestone_checkpoint.py activate-reader-semantic --project-root <project-root>`

It refuses an open review round, a non-v2 current binding, any M2-M5 lifecycle
history, malformed or stale request bytes, a mismatched re-pin ledger event, or
qualification-receipt drift. It resolves the semantic policy again, publishes
the resolver artifact first, validates a proposed ledger in memory, and
publishes phase state last. Milestone records and transition history are copied
unchanged. Its applied receipt records prior/current hashes and rollback
preimages. On failure it restores only its exact owned postimages; conflicting
external bytes are preserved and reported as a recovery conflict.
The same owned-postimage rule protects qualification publication and package
re-pin rollback; no rollback overwrites or deletes bytes that no longer equal
the transaction's intended postimage.

The contract suite includes an end-to-end producer-to-resolver-to-Planner test
whose proposed binding is checked by the canonical milestone validator against
a temporary copy of the Paper 2 package.

Qualification, independent audit, package re-pin, and Planner application are
four separate authority moments. None implies the next.

## Out of scope

These transactions do not modify a manuscript, lifecycle state before the
separate Planner command, F9, promotion, delivery, canon, or the live structural
graph. They do not establish that centroid review has run; they only create the
governed capability and evidence path required before such a review can become
eligible.
