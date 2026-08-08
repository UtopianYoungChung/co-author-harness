# Release notes - v0.43.0

## Outcome

This version slice integrates the graph-independent reader-policy refresh and
the governed release-qualification architecture into the `0.43.0` candidate.
It records package identity and history only; the exact versioned source still
requires the ordered full qualification and a fresh independent consumer
observation before any package-clearance decision.

## Graph-independent reader policy

Reader-profile v2 distinguishes a structural graph from a governed semantic
binding. When semantic authority is unavailable, the profile records
`semantic_usage: not_invoked` and routes reader-accessibility obligations
without activating graph-derived generation. Existing project-binding,
migration, approval, and lifecycle gates remain fail closed.

The refresh is an atomic transaction against an exact project preimage. It does
not rewrite assignment contracts, infer research authority, or treat mechanical
graph availability as semantic eligibility.

## Durable source qualification

The release controller provides immutable, receipt-authoritative terminal
evidence for exact source and input bindings, controlled launch environment,
process ownership, complete fixture execution, output scope, and generation to
replay continuity. A journal deliberately held at `finalizing` is terminal only
when an independently validated immutable receipt is present.

Qualification is performed from detached worktrees with the fixture cache off,
explicit residue censuses, exact runtime and source pins, and fresh independent
B0/M0/m0 review of the qualification procedure. Failures are preserved rather
than reinterpreted as passes.

## Compatibility and status boundary

The shipment-v2 compatibility kit remains an observational contract between
the producer and a separately governed consumer. Consumer evidence must bind
the exact final versioned commit and cannot carry forward from a pre-slice
candidate.

This file does not claim source qualification, consumer compatibility,
`PACKAGE_CLEARED`, `SHIPPED`, installed-cache provenance, `HOST_QUALIFIED`,
research acceptance, activation, push, tag, or upload. Each remains a distinct
ordered gate. `.claude-plugin/plugin.json` is the authoritative current-version
plane; this release note is historical release metadata.
