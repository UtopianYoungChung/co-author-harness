# v0.43 C2 kernel-projection rebind C0 addendum

Date: 2026-08-02

## Observed blocker

After the authorized contract-kernel component repairs, the 15-command
structural sweep is 14/15. `python -B scripts/schema_runtime_check.py` refuses
with `SCHEMA-RUNTIME-UNAVAILABLE` and detail
`compatibility-kit kernel projection hash drift`.

The live kernel is now 37,242 bytes with raw SHA-256
`dfc5a603e0a30fa857d2eeed0579a4d39cc3da222fc7aa7e825279e32e7d8bec`.
The compatibility projection and profile are mechanical downstream bindings;
neither is consumer acceptance or application evidence.

## Exact writable ledger

| Action | Path | Preimage bytes | Preimage SHA-256 |
|---|---|---:|---|
| CREATE | `docs/superpowers/specs/2026-08-02-v043-c2-kernel-projection-rebind-c0-addendum.md` | 0 | `ABSENT` |
| MODIFY | `references/compatibility/shipment-v2/contract_kernel_projection.json` | 2,907 | `4a96f9d685be22d35a590b58a364c7fbf6be462c6282aa675791ac1ef0b9c5ab` |
| MODIFY | `references/compatibility/shipment-v2/compatibility_profile.json` | 4,510 | `302fc74ba70822f098ce02c67a55f613b4fd830a114e5ef21c7d5f3597b6385d` |

No other path is writable under this addendum.

## Mechanical postimage

1. In `contract_kernel_projection.json`, update only `kernel.sha256` to
   `dfc5a603e0a30fa857d2eeed0579a4d39cc3da222fc7aa7e825279e32e7d8bec`.
   The expected file SHA-256 is
   `e6ffd32d42185520ffd63acfbb59f7294e619dd9a64a3bcf7efb9bc3609d951b`.
2. In `compatibility_profile.json`, update only `contract_kernel.sha256` to the
   same kernel hash and `compatibility_kit.sha256` to
   `51d635e368d66a66872621ab7b3ad3082c22e28b603ce77102a922f929baf08b`.
   The expected file SHA-256 is
   `70d60553b0de171552f3956149a3ceda723b042fab8cfe96ef3cbd73fb304470`.

The aggregate is computed by the canonical algorithm already enforced in
`scripts/schema_runtime_check.py`; no algorithm or checker change is
authorized.

## Closure gates

Require schema runtime, contract-kernel coherence, destination coverage, the
other root structural checks, and the tracked Python-bytecode stability census
to pass. Require independent exact-diff review at B0/M0/m0 before the repair
commit. The generated fixture manifest remains void until a successful
governed full-registry transaction.

This addendum grants no package clearance, shipment, cache, host qualification,
activation, release, promotion, acceptance, research mutation, or canon.
