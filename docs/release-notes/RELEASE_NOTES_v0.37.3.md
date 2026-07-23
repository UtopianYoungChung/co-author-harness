# Release notes — v0.37.3

## Outcome

This patch makes the mandatory centroid path executable after the canonical
Wiki semantic refresh. A Planner rebind can now update a read-only lifecycle
state file without leaving it writable, and the destination boundary admits
only the exact re-pin artifacts needed for that transaction.

The live `2026-07-19_first-principles-prism-intake` project was rebound to
reader-policy epoch 8. `centroid_service.py --mode write` on M3 and
`centroid_service.py --mode review` on the current M4 both return `ready` with
the current profile, attestation, and exemplar pins.

## Truth boundary

The repair does not convert the existing M4 into a centroid-generated draft.
Its prior generation provenance remains invalid because the earlier write-mode
service call failed and no current-byte generation envelope exists. A fresh
M4 generation/evaluation round still requires canonical lifecycle catch-up;
the project ledger currently derives `accept M2`, while later M3/M4 bytes and
user-acceptance evidence exist outside that state.

## Semantic binding

- Graph SHA-256: `587d07c48c11d86e71005ebda660af5e296c81c98ed1889c34d4795ecf194f03`
- Attestation view: `00133e506e399db25cd8a182a97f0d82e9c6a1140b0cfef115da2331c0aa7f5e`
- Exemplar view: `5b7fcb501ca76e21d92ab187be9a7db7494d2ba4f72bf931516227b12c888344`
- Profile SHA-256: `02dfc1f2abf31c3a14c5654e0a74b443a54279f61192e3d06817d99da3c4d719`

## Verification

- `assignment_milestone_checkpoint_smoketest.py`: PASS, including read-only
  rebind preservation and hash-bound stale-request recovery.
- `repin_register_smoketest.py`: 12/12 PASS.
- Destination capability and coverage checks: PASS.
- Contract kernel and accessibility fixture regressions: PASS.
- Authoritative fixture registry: 59/59 PASS with `--no-write`.

The `.plugin` and loader-compatible `.zip` archives are built only from the
approved committed `main` tip so their embedded provenance can identify the
exact shipped bytes.
