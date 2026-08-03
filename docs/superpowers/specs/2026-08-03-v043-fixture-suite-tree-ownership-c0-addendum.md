# v0.43 fixture-suite process-tree ownership C0 addendum

**Status:** approved package-maintainer boundary for repairing the independent
per-suite process-ownership defect exposed during the attempt-016 review. This
supplements, and does not replace, the Windows executable-alias containment
repair. It grants no C2 qualification, version, package clearance, shipment,
cache mutation, consumer re-attestation, host qualification, activation,
research mutation, acceptance, promotion, release, or canon authority.

**Run scope:** `adhoc_review`.

**Parent authority:**
`docs/superpowers/specs/2026-08-03-v043-c2-windows-alias-containment-c0-addendum.md`.
All parent ledgers, fresh attempt paths, and stop gates remain binding.

## Frozen independent defect

`scripts/analysis/fixture_runner.py` is the authoritative registry executor,
but each registered suite is currently launched with direct
`subprocess.run(...)` ownership only. A timeout kills only that direct process;
an early-exiting suite can also leave a descendant alive. The runner can then
compute its post-input digest, publish a case result, or return while a suite-
owned process can still mutate state. The outer release controller provides a
second containment layer during governed release qualification, but the root
maintainer contract also exposes direct runner invocation, and the runner's own
claim says every registered suite completed in its run. The missing per-suite
tree closure is therefore an independent infrastructure defect, not a reason
to reinterpret attempt 016.

## Exact additional writable ledger

| Action | Path | Preimage bytes | Preimage SHA-256 |
|---|---|---:|---|
| CREATE | `docs/superpowers/specs/2026-08-03-v043-fixture-suite-tree-ownership-c0-addendum.md` | 0 | `ABSENT` |
| CREATE | `scripts/analysis/fixture_process_supervisor.py` | 0 | `ABSENT` |
| MODIFY | `scripts/analysis/fixture_runner.py` | 39,695 | `c456f6fb028a82ba55dd2ee945a0858f591bd07f71fa802a08d305f17757acaa` |
| MODIFY | `scripts/analysis/fixture_infrastructure_check.py` | 34,650 | `0a08c1ff8e36e1a3e65351cb5417ecf8079dfe8cc3d969a7a8ffbdbccb14fa20` |
| MODIFY | `references/contract_kernel.v1.json` | 37,242 | `d3ca3dbf3b9e67445ac78ff393d3db5caf1c940a95c959f22dbe5bb866053d84` |
| MODIFY | `references/compatibility/shipment-v2/contract_kernel_projection.json` | 2,907 | `28026ca439d31d20f7fbb2a1f44b63dd65b1d672d523b12bd13759ba3e2fd2ee` |
| MODIFY | `references/compatibility/shipment-v2/compatibility_profile.json` | 4,510 | `19c5fd05d703ca49ab7f1d25106c9458d1c3d78efe7e99556bf04ab1aece632b` |
| QUALIFICATION OUTPUT ONLY | `docs/analysis/generated/fixture_manifest.json` | 54,247 | `7e25595be68fedbdc7759d6fd61f3e98116191c9ac672107f918c4acd88c01c0` |

The controller and controller-smoketest modifications remain authorized by the
parent ledger. No other tracked path is writable. Adding the new helper to the
kernel is authorized; the kernel must bind both the modified runner and the new
supervisor, while preserving every unrelated component byte-for-byte.

## Required supervisor contract

1. Every suite must start inside a runner-owned process-tree boundary before
   any suite instruction executes. Windows uses a private Job with
   `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, suspended creation, assignment and
   membership proof before resume, and no breakaway permission. Linux/WSL uses
   a child-subreaper supervisor with dynamic descendant rescans and reaping;
   process-group-only cleanup is insufficient. Unsupported platforms refuse.
2. One monotonic case deadline covers direct execution and tree cleanup.
   Normal completion requires the direct exit status plus two consecutive
   empty-tree observations. Timeout, owner loss, interruption, spawn failure,
   or a surviving descendant makes the run void with exit 2.
3. Every failure path terminates and reaps the complete owned tree in `finally`.
   An unrelated control process must survive. No cache staging or manifest
   publication may occur until suite-tree closure is proven.
4. Preserve byte capture and deterministic UTF-8 replacement decoding. The
   existing manifest schema and direct observed exit remain unchanged; tree
   closure is an infrastructure precondition bound by the runner/supervisor
   hashes.
5. Add focused infrastructure regressions for direct exit with a blocked
   descendant, timeout with child/grandchild, a descendant created during
   teardown, unrelated-process survival, no delayed mutation, lock reuse, and
   absence of manifest/cache publication after refusal. Add nested controller
   coverage on Windows and equivalent WSL/POSIX coverage.

After the controller, runner, supervisor, and tests are frozen, update the
controller and fixture-runner kernel component hashes and add the supervisor
component; then update the projection kernel hash and the profile kernel/kit
hashes mechanically. Run focused Windows and WSL/POSIX tests, subprocess text
policy, kernel coherence, shell syntax, all root structural checks, exact
bytecode censuses, and independent B0/M0/m0 review before committing repair
bytes.

The already-reserved, still-absent attempt 017, attempt 018, and retry-5 paths
remain the only fresh qualification paths. Attempt 017 may start only after
both this repair and the parent Windows-alias repair are committed and reviewed.
Any warning, unsupported topology, residue, missing empty-tree proof, failed or
skipped required case, cache activity, binding drift, or reviewer finding is a
stop. All later lifecycle and shipment claims remain closed.
