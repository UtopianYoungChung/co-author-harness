# Release notes — v0.37.4

## Outcome

This patch ships the project-neutral centroid semantic freeze and closes the
remaining ambiguity in the harness's producer boundary.

The centroid is bound to a 290-page inventory snapshot, with Yu, Giorgini, and
Maiden (2011), *Social Modeling for Requirements Engineering*, as its primary
reference. Missing pinned pages and pinned-path hash mismatches remain hard
failures. Pages added to the live Wiki after the freeze are advisory enrichment
candidates, so ordinary knowledge-base growth does not invalidate the frozen
semantic receipt.

## Producer boundary

The harness does not govern research projects and no individual project
governs the harness. Project work is staged only beneath a governed workspace
root at `outputs/co-author-harness/staging/<work-id>/<run-id>/`; private Stage
shipments remain restricted to an active package's exact governed shipment
lane. The similarly named path inside this repository is invalid and is now
refused as `DEST-MISROUTED`.

## Verification contract

The release is built from the committed `main` tip. Before shipment, the clean
detached checkout must pass the root structural checks and all 59 registered
fixture suites with `--no-write`. The loader-native `.plugin` archive and the
requested `.zip` transport copy must be byte-identical and must report the same
commit and v0.37.4 manifest in their embedded provenance.
