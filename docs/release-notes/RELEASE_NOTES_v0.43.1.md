# Release notes - v0.43.1

## Outcome

This patch corrects shipment-v2 membership validation for governed `modify`
transactions and closes two qualification-coverage gaps. It records the
versioned source identity and release history only. The resulting commit still
requires the ordered versioned qualification and a fresh independent consumer
observation before any package-clearance decision.

## Shipment-v2 membership and recovery

`inputs/` members are immutable evidence and preimage carriers. Operation
artifacts remain confined to `work/`, `state/`, and `evidence/`, and proposed
operations must be bijective with that operation-bearing inventory. Inputs are
therefore neither required to have operations nor permitted to serve as
operation artifacts.

When a preimage supplies `recoverable_copy`, the referenced path must be an
inventoried `inputs/...` member and its SHA-256 must equal the declared
preimage digest. Traversal, collision, containment, member, seal, retry,
recovery, and receipt checks remain fail closed.

## Qualification coverage

The package-completeness controls now emit the declared
`RUNTIME-PLANE-MISSING` diagnostic for missing archive and cache suites, so the
v0.43.0 two-case consumer carve-out does not carry forward. The static
`output_economy_check.py` guard is also part of the versioned qualification
suite, and the required shipment-v2 phrase is restored in the Phase 4 skill.

The token-budget baseline is ratcheted to the immutable reviewed source commit
after an exact closed-world comparison: six previously committed decreases
and the authorized six-token Phase 4 restoration, with no additional drift.

## Compatibility and status boundary

The contract kernel and shipment-v2 compatibility projection bind the repaired
source and the versioned token policy. A fresh independently authored consumer
round remains required against the eventual qualified candidate.

This file does not claim source qualification, consumer compatibility,
`PACKAGE_CLEARED`, `SHIPPED`, installed-cache provenance, `HOST_QUALIFIED`,
research acceptance, activation, push, tag, or upload. Each remains a distinct
ordered gate. `.claude-plugin/plugin.json` is the authoritative current-version
plane; this release note is historical release metadata.
