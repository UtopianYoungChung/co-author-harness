# Release notes — v0.39.0

## Outcome

This release closes the assurance-provenance boundary identified after v0.38.
Lifecycle acceptance now depends on kernel-issued authority and exact
current-byte evidence, not actor strings, role-authored green JSON, or a
successful process label.

## Authority and evidence

- Generation and evaluation receive role-scoped, one-time dispatch authority
  issued by the transaction kernel and bound to the exact candidate,
  publication, and reservation transition.
- Claim consumption, manuscript mutation, milestone acceptance, handoff, and
  terminal close share verifier transactions and reject stale, partial,
  replayed, truncated, or rewritten evidence.
- Canonical extraction, citation identity, passage use, conditioning versus
  quotation, product-assurance candidates, and evaluation issuance are bound
  in the same evidence graph.
- Host attestation and externally authorized legacy mutation remain distinct
  trust roots. The standard dispatch path does not claim cryptographic host
  identity.

## Executable qualification

The registered synthetic protocol fixture records a complete M1-to-FINAL walk
through the production authorities and rejects targeted tamper variants. It is
protocol-conformance evidence only: it does not claim human-quality semantic
judgment or host-attested separate agents.

The governed product gate distinguishes mechanics-only diagnostics from
lifecycle-eligible qualification. Runtime-plane receipts preserve exact,
CRLF-only, semantic, missing, and foreign-file classifications across source,
unpacked archive, and loader-managed cache planes.

## Packaging and state labels

Release tooling now inspects an archive's complete central directory before
member-by-member extraction, runs the bundled runtime probe with isolated
imports, publishes and re-reads a canonical SHA-256 sidecar, and builds
immutable hash-bound package and release evidence indices. The human shipment
report is rendered from the final index.

`PACKAGE_CLEARED`, `SHIPPED`, and `HOST_QUALIFIED` are separate states. A
reviewed package may be shipped while live Cowork upload and fresh-task proof
remain pending; that pending host state does not erase package clearance.
