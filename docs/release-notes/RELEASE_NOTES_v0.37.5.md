# Release notes — v0.37.5

## Outcome

This patch makes centroid execution auditable at passage level. A resolved
policy packet is no longer enough to satisfy generation or evaluation: the
responsible role must preserve a semantic receipt that identifies the exact
passages used and binds their source, extract, locator, warrant, and use to the
artifact under review.

## Independent evaluation contract

Generation accepts only a `write`-derived centroid packet. Evaluation accepts
only a `review`-derived packet over the exact prepared bytes and must bind the
verified generation envelope. Generator and Evaluator actor and dispatch
identities must differ. Generic evidence, a post-prepare artifact mutation, or
self-evaluation fails closed.

Milestone transactions and the terminal full-run check consume the enriched
envelopes and verify that evaluation points back to the exact generation
envelope. These receipts prove execution and provenance; they do not imply
semantic quality, grounding completeness, user acceptance, or lifecycle
promotion.

## Verification contract

The release is built from the committed `main` tip. Before shipment, a clean
detached checkout must pass the root structural battery and all 59 registered
fixture suites with `--no-write`. The installed plugin cache must then match the
built v0.37.5 package for the verifier, centroid skill, and semantic-receipt
schema, followed by an installed-runtime draft-governance smoke test.
