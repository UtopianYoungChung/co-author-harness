# v0.43 exceptional tree-closure C0 addendum

**Status:** approved package-maintainer boundary for repairing the exact
fail-closed defects found by the independent final reviewers. This grants no
C2 qualification, version, package clearance, shipment, cache mutation,
consumer re-attestation, host qualification, activation, research mutation,
acceptance, promotion, release, or canon authority.

**Run scope:** `adhoc_review`.

**Parent authority:**
`docs/superpowers/specs/2026-08-03-v043-destination-kernel-rebind-c0-addendum.md`.

The Windows review reported two moderate exceptional-cleanup defects: a
`BaseException` after suspended process creation can bypass exact containment,
and untyped handle-close failures can mask the governed refusal. The POSIX
review reported one blocker and two moderate defects: terminal error or owner
interruption can return before proven descendant closure; the controlled
environment is serialized into the command line; and cache refusal assertions
are vacuous in cache-off mode. The unsupported-platform assertion is also to
be made mechanical. All later gates remain closed.

## Exact writable ledger

| Action | Path | Preimage bytes | Preimage SHA-256 |
|---|---|---:|---|
| CREATE | `docs/superpowers/specs/2026-08-03-v043-exceptional-tree-closure-c0-addendum.md` | 0 | `ABSENT` |
| MODIFY | `scripts/release_qualification_controller.py` | 109,912 | `9e7478a598753545d02380ff4b104f1bffc8205e634abb6ff5f0b8a9e9a49245` |
| MODIFY | `scripts/release_qualification_controller_smoketest.py` | 165,345 | `4e3a405f62f7c03e974686acaf3816356037500020f1b63e49bbc42c4eaa98cd` |
| MODIFY | `scripts/analysis/fixture_process_supervisor.py` | 35,570 | `a6b6cf034d28a186f3da70ec859d712f6179f5a3c8ef100933799c63954d5343` |
| MODIFY | `scripts/analysis/fixture_infrastructure_check.py` | 49,352 | `a86b3b1b8a6d791cf11ace837b7c51bb9224b03b48d4cae92ef127a1d519f126` |
| MODIFY | `references/destination_coverage_registry.json` | 14,472 | `2ddbac2856694dcf26d270723639fd44f8ac056b36baabfbadbf7ce58d3d4ab3` |
| MODIFY | `references/contract_kernel.v1.json` | 37,588 | `df30185977ca34ed05ac63c0756636260cce54f2aaf97e5f964e302c2ce839da` |
| MODIFY | `references/compatibility/shipment-v2/contract_kernel_projection.json` | 2,907 | `d5791be77af4b5bbb26a17631dd023a72d81e8eda9c727ec199947900031b1a0` |
| MODIFY | `references/compatibility/shipment-v2/compatibility_profile.json` | 4,510 | `74212467fa79a0bb199a97fb1240eb6490bc13879f188e405369045ac73cc0df` |

The controller repair must catch and re-raise `BaseException` only after
bounded exact suspended-process cleanup. Every handle close must either be
proven or become a typed `RELEASE-CONTROLLER-PROCESS` refusal without skipping
other cleanup. Add injected `BaseException` and close-failure regressions.

The POSIX repair must retain ownership on every path until two empty descendant
scans are proven. Cleanup failure overrides an earlier diagnostic; parent
interruption closes the control channel, joins synchronously, uses the frozen
identity fallback when needed, and only then re-raises. Pass the environment
through `Popen(env=...)`, never through argv. Add a cache-assisted refusal test
that reaches neither staging nor publication and a mechanical unsupported-host
refusal test.

After exact source postimages pass focused Windows and WSL tests, refresh only
the changed destination pins through the supported operation, then bind only
changed kernel component hashes, the raw kernel projection hash, and the
profile's raw kernel and canonical kit hashes. Freeze all exact postimages and
obtain fresh B0/M0/m0 reviews before corpus work. Any new path, diagnostic,
authority claim, or behavioral scope is a stop.
