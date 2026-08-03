# v0.43 destination-kernel rebind C0 addendum

**Status:** approved package-maintainer boundary for the mechanical contract
binding exposed after the authorized destination-registry refresh. This grants
no C2 qualification, version, package clearance, shipment, cache mutation,
consumer re-attestation, host qualification, activation, research mutation,
acceptance, promotion, release, or canon authority.

**Run scope:** `adhoc_review`.

**Parent authority:**
`docs/superpowers/specs/2026-08-03-v043-cross-worktree-supervisor-pin-c0-addendum.md`.

After the supported registry pin completed and destination coverage passed,
`scripts/contract-kernel-check.py` correctly stopped at
`destination-coverage-registry: content hash drift`. The registry's exact
14,472-byte postimage is
`2ddbac2856694dcf26d270723639fd44f8ac056b36baabfbadbf7ce58d3d4ab3`.
No other kernel component requires a change.

## Exact writable ledger

| Action | Path | Preimage bytes | Preimage SHA-256 | Authorized postimage SHA-256 |
|---|---|---:|---|---|
| CREATE | `docs/superpowers/specs/2026-08-03-v043-destination-kernel-rebind-c0-addendum.md` | 0 | `ABSENT` | fixed by this commit |
| MODIFY | `references/contract_kernel.v1.json` | 37,588 | `383b2e088adb2b60fa9d7946ddf8d9131d73b94a1c6f236cf8e5cc15f88aebc2` | `df30185977ca34ed05ac63c0756636260cce54f2aaf97e5f964e302c2ce839da` |
| MODIFY | `references/compatibility/shipment-v2/contract_kernel_projection.json` | 2,907 | `72322f55c34ef2b16a0f58a38b1e33e3b4063383817328b61a44179bf579cf75` | `d5791be77af4b5bbb26a17631dd023a72d81e8eda9c727ec199947900031b1a0` |
| MODIFY | `references/compatibility/shipment-v2/compatibility_profile.json` | 4,510 | `53afb147f9b8a567a0bb65728020d4633be5caae135db67e3714b5da1438d166` | `74212467fa79a0bb199a97fb1240eb6490bc13879f188e405369045ac73cc0df` |

After this addendum is committed, replace only the registry component hash in
the kernel, then the raw kernel hash in the projection, then the profile's raw
kernel hash and canonical six-file kit aggregate. The exact resulting kernel
hash is `df30185977ca34ed05ac63c0756636260cce54f2aaf97e5f964e302c2ce839da`;
the exact kit aggregate is
`480f3abed604889a14c76836ec2c7af3974ae6ec60b9de54136b262449a67767`.
Any other semantic or formatting change is a stop. Re-run all binding and
structural checks. All qualification and later shipment gates remain closed.
