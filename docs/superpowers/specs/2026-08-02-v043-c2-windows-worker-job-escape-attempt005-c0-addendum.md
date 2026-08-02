# v0.43 C2 Windows worker Job-escape and attempt-005 C0 addendum

Date: 2026-08-02

## Fail-closed trigger

Attempt 004 is permanently terminal `evidence_incomplete`. Recovery found no
exit capsule or captured-stream binding and did not rerun the product:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `receipt.json` | 2,573 | `96f1c7180b72c2cbd4fd85b6722892f4555b1c84f27035eaf3acac1a8df2499a` |
| `intent.json` | 658,389 | `01008c164691baea3b72849b8f8f928459aa1a43b4ba194c2e25449600e19a80` |
| `journal.json` | 692 | `326d9f27a1ac37ea8ff787c3d690fab261b189e14274141430f6b3366adfd8d0` |
| `owner.json` | 113 | `4019b00cf111629d9466627f0562218142047a3b182ebf30ef594488e4c59ed0` |

The receipt proves abrupt worker/product loss, not its external cause. Live
Windows probes show the current host's immediate Job has limit flags `0x3000`
and that a controller-equivalent suspended child is already outside every Job
observable through `IsProcessInJob(child, NULL)`. The same child survives
ordinary tool-call return. Therefore this addendum does not assert that a
missing `CREATE_BREAKAWAY_FROM_JOB` flag caused attempt 004 and does not claim
that any source patch can defeat explicit privileged host PID termination.

## Exact writable ledger

| Action | Path | Preimage bytes | Preimage SHA-256 |
|---|---|---:|---|
| CREATE | `docs/superpowers/specs/2026-08-02-v043-c2-windows-worker-job-escape-attempt005-c0-addendum.md` | 0 | `ABSENT` |
| MODIFY | `scripts/release_qualification_controller.py` | 94,329 | `5e4f5778734de71b0fc581d71f290604c6a5aefc5b5ffc55ed01ad422e03ea01` |
| MODIFY | `scripts/release_qualification_controller_smoketest.py` | 136,024 | `3b098a2a9172f1788f38dc63b31d2f336fbe4ec6e23e822ba38f888fadb30635` |
| MODIFY | `references/contract_kernel.v1.json` | 37,242 | `dfc5a603e0a30fa857d2eeed0579a4d39cc3da222fc7aa7e825279e32e7d8bec` |
| MODIFY | `references/compatibility/shipment-v2/contract_kernel_projection.json` | 2,907 | `e6ffd32d42185520ffd63acfbb59f7294e619dd9a64a3bcf7efb9bc3609d951b` |
| MODIFY | `references/compatibility/shipment-v2/compatibility_profile.json` | 4,510 | `70d60553b0de171552f3956149a3ceda723b042fab8cfe96ef3cbd73fb304470` |
| CREATE TRANSIENT | `C:\Users\young\AppData\Local\Temp\coauthor-v043-qualification-20260802-attempt-005\` | 0 | `ABSENT` |
| FAILED OUTPUT / RETRY MAY WRITE | `docs/analysis/generated/fixture_manifest.json` | 0 | `ATTEMPT_004_VOID` |

No destination-registry edit is authorized. The controller is `guarded`, not
SHA-pinned, and its smoketest is test-pattern exempt. No schema, diagnostic
registry, CLI, cache, package, research, or host-registration path is writable.

## Authorized controller hardening

On Windows only:

1. Bind `IsProcessInJob` and inspect the launcher's immediate Job through the
   existing extended-limit query. An unjobbed launcher needs no breakaway flag;
   `SILENT_BREAKAWAY_OK` (`0x1000`) needs none;
   `BREAKAWAY_OK` (`0x0800`) requires `CREATE_BREAKAWAY_FROM_JOB`
   (`0x01000000`). Absence or API ambiguity refuses using the existing stable
   `RELEASE-CONTROLLER-PROCESS` diagnostic with exact durability detail.
2. Create only the detached worker suspended with the selected flag. Before
   assigning the controller supervisor Job or resuming the worker, require
   `IsProcessInJob(worker, NULL)` to be false. If true or unobservable,
   terminate/wait/close the exact suspended handles and refuse. Never retry
   without escape.
3. Preserve suspended-before-private-Job assignment, worker identity/readiness,
   the supervisor Job's `KILL_ON_JOB_CLOSE`, and product Job containment.
   `_spawn_product_process` must never receive breakaway behavior.
4. Preserve POSIX source behavior exactly.

The existing receipt schema and stable diagnostic vocabulary are sufficient;
no new diagnostic code is authorized.

## Required regression

Extend only the existing controller smoketest with Windows-only decision-table
and real Job fixtures covering: unjobbed, silent breakaway, explicit
breakaway, non-permissive refusal, API ambiguity, post-create inherited-Job
refusal, suspended-process cleanup, and no product execution on refusal.
Require the existing Windows and WSL/POSIX controller suites, pyc stability,
the root structural checks, and three independent B0/M0/m0 exact-diff reviews.

## Mechanical binding cascade

After the controller postimage is qualified:

1. Update only the `release-qualification-controller` component hash in
   `references/contract_kernel.v1.json`, using the kernel's CRLF-to-LF text
   normalization rule.
2. Bind the resulting raw kernel SHA-256 in only projection `kernel.sha256`.
3. Recompute the raw six-file canonical compatibility-kit aggregate and update
   only profile `contract_kernel.sha256` and `compatibility_kit.sha256`.

Any other field or path requires another committed C0 addendum.

## Attempt-005 transaction boundary

Attempt 005 may start only from a final clean preflight whose sole worktree
delta is the void manifest. During the transaction there may be no Git command,
repository audit, agent review, package/cache/research operation, or long-lived
shell `wait`. Monitoring is limited to short controller `status` calls,
controller-owned journal reads, OS PID/token observation, and non-shell
collaboration waits between observations. A user/task steer remains a stop-and-
recover event, never success evidence.

Attempt 005 must pass the authoritative 93-suite/97-case cache-off registry,
stable tested-input bindings, exact output scope, and zero-live-process checks.
Any warning, refusal, incomplete evidence, drift, or ambiguity remains STOP.

This addendum grants no C2 qualification, package clearance, shipment, cache
equality, host qualification, activation, release, promotion, acceptance,
research mutation, or canon.
