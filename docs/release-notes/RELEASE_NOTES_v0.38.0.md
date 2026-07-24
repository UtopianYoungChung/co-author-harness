# Release notes — v0.38.0

## Outcome

This release relocates the fail-closed boundary from proof that a workflow ran
to evidence about the exact product. The centroid resolver now reports
`binding_resolved`; conditioning requires canonical extracts, passage-level
receipts, a product-assurance report, and independent evaluation.

## Product-assurance contract

- PDF evidence is extracted through the canonical `pdftotext` adapter and
  bound by source/output hashes. A single library extraction cannot support a
  hard quotation verdict.
- Every used passage records its verbatim quote, locator, source and extract
  hashes, warrant, use, and citation identity.
- Quote containment and same-author/year title-label mapping are hard gates.
- Coinage, corpus-absent high-frequency register, insider-term negation, and
  uncited empirical generalizations are deterministic candidates. Evaluation
  must dispose current candidates by exact code and locator; they are not
  silently auto-edited.
- Grounding and register remain separate dimensions: owned synthesis does not
  become centroid vocabulary merely because it is legitimate.

The canonical `scripts/audit/run_all.py` command accepts the semantic receipt
and explicit wiki/workspace roots, emitting both mechanics findings and the
exact product report in one invocation.

## Mutation and state contract

`assignment_writer_commit.py` now appends every sanctioned write to a
project-wide preimage/postimage hash-chain. Publication results bind the row
hashes; milestone record and terminal FINAL verification refuse unjournaled
live-byte drift. Direct manuscript edits therefore become detectable state,
not a convention violation discoverable only by chance.

When current canon differs from a project binding and a pending request makes
the operation routine, centroid resolution returns
`PROJECT_BINDING_REBIND_AVAILABLE` plus the exact Planner-owned command.
Conflicts remain distinct fail-closed states.

## Verification contract

Shipment requires the structural battery, the complete registered fixture
corpus, release packaging, packaged-source parity, and a clean installed-cache
runtime probe. Source, built package, local marketplace resolution, and active
cache must identify the same v0.38.0 bytes before the release is reported as
operational.
