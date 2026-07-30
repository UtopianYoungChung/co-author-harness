# Release notes - v0.41.0

## Outcome

This release introduces a governed laboratory-iteration scope for private,
proposal-only experimentation and a derived milestone-handoff policy that does
not make F9 a universal prerequisite for acceptance. The release preserves the
existing audited path and does not migrate existing project bytes implicitly.

## Three invocation scopes

- `adhoc_review` remains read-only and cannot authorize prose production,
  lifecycle mutation, F9, or terminal claims.
- `lab_iteration` requires an existing governed project, resolved assignment
  contract, and resolved staging or private-shipment destination. It may produce
  transient proposals and receipts only; it cannot alter authoritative research
  state, consume handoffs, accept milestones, or publish final deliverables.
- `full_lifecycle` retains the complete project, assignment, user-approval,
  scholarly, milestone, and terminal-proof contract.

Scope declarations are inherited exactly by child briefs. Narrowing, widening,
or omission fails closed rather than being guessed from prose.

## Derived and audited handoff policy

Milestone framework contract 1.1.0 adds explicit `handoff_policy` values
`derived` and `audited` while leaving `mode: native|legacy` unchanged. Valid
1.0.0 ledgers remain byte-compatible and resolve to effective audited policy.
New native bootstrap defaults to explicit derived policy, with explicit audited
bootstrap still supported.

Under derived policy, accepted current milestone state can authorize the next
milestone without F9. If optional F9 is explicitly requested, its exact bytes
are validated and preserved as non-gating, non-consumed evidence. Under audited
policy, the existing exact F9 publication and consumption chain remains
load-bearing.

## Explicit migration and recovery

Existing projects move to derived policy only through
`lab-iteration-derived-handoff-v1`. The migration is dry-run first and binds
preimage, proposed bytes, authority, claim, receipt, journal, verification, and
rollback. It refuses stale or concurrent claims, protected destinations,
tampered receipts, invalid evidence graphs, and unsupported ledger states.
Interrupted apply and rollback recover only from revalidated exact prepared
bytes; they do not publish an unvalidated prepared manifest.

## Qualification and boundaries

Synthetic qualification exercises derived and audited transactions,
laboratory non-effects, legacy compatibility, optional-F9 preservation,
bootstrap, rendering, scholarly lifecycle integration, protected destinations,
and migration tamper/recovery paths. No active research project or Paper 2
state was used or changed.

This release note is historical release metadata, not the current-version
authority. `.claude-plugin/plugin.json` remains authoritative. A versioned
source candidate is not automatically `PACKAGE_CLEARED`, `SHIPPED`, or
`HOST_QUALIFIED`; release packaging, installed-cache qualification, fresh-task
observation, remote push, tags, and uploads retain their separate gates.
