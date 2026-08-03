# v0.43 C2 detached-facade bytecode closure and retry C0 addendum

**Status:** approved package-maintainer boundary for closing the release-gate
bootstrap bytecode defect exposed by refused detached replay 008 and for one
new source-root qualification followed by one new detached no-write replay.
This addendum grants no package clearance, shipment, cache mutation, consumer
re-attestation, host qualification, activation, research mutation, acceptance,
promotion, release, or canon authority.

**Run scope:** `adhoc_review`.

**Parent authority:**
`docs/superpowers/specs/2026-08-02-v043-c2-windows-worker-job-escape-attempt005-c0-addendum.md`.
All parent prohibitions and later gates remain binding. Any path not enumerated
here or in the parent ledgers requires another committed addendum before it is
created or changed.

## Frozen qualified source and refused detached state

- Repository: `B:\Agents\platform\co-author-harness`.
- Branch: `main`, the only permitted branch.
- Commit: `f9b8d7f7d16bd1dadd7c5dcc0926c159eca2360b`.
- Tree: `8777bf6652255b48f909c1b2cd285c9b16c1f99b`.
- Source-root attempt 005 succeeded under its controller receipt: 93 suites /
  97 executed cases, cache off, zero cache hits, stable 717-file canonical and
  raw tested-input digests, manifest publication, exit zero, empty stderr, and
  zero live worker/product processes. Its `receipt.json` is 3,162 bytes,
  SHA-256
  `312937fca4cb50b80cc198751a25a52b70cc7f43d4c432a261e029417c2ca2ac`.
- The resulting committed manifest is 54,252 bytes, SHA-256
  `bd9f3f1beb882813bf7717c49202d76ee97f48dd10f2806c499fc174d48bfc19`.
- Detached replay 008 is permanently terminal `refused` with
  `RELEASE-CONTROLLER-OUTPUT-SCOPE`. All 93 suites / 97 cases exited zero,
  cache hits were zero, canonical and raw inputs were stable, and `--no-write`
  preserved committed evidence, but those facts do not override the refusal.
- Attempt-008 `receipt.json` is 2,671 bytes, SHA-256
  `d53dff8e3ef230d529b4ebcf9cad740a7b1350427b219f7651c9181614e16c77`.
  Its `stdout.bin` is 9,643 bytes, SHA-256
  `5d60483dd829ff6b3b1b628a2011b69fc910b3fe913f1a506d83c7fd3c145e8b`;
  `stderr.bin` is empty with the canonical empty SHA-256.
- The exact refused outputs in
  `B:\Agents\.coauthor-v043-c2-detached\scripts\__pycache__\` are:

  | File | Bytes | SHA-256 |
  |---|---:|---|
  | `destination_capability.cpython-314.pyc` | 18,545 | `c3648cd48f9f8001b394fc22ec876335e623f24ad97ec6adabcc2213062feb22` |
  | `qualification_environment.cpython-314.pyc` | 5,474 | `b505456ab902d4ceb2626b97c05158e35e187564af97986bf8e8fc2cde7b189a` |

Labels `attempt-006` and `attempt-007` were used only for invocations refused
before run-directory creation. Both exact paths remain absent. They produced no
intent, owner, journal, exit capsule, receipt, child execution, manifest
output, or repository mutation; they are not qualification transactions and
the labels may not be reused.

## Proven architectural cause

The outer controller and fixture runner both applied explicit `-B`. The
controller smoketest's ambient-facade case intentionally removed every
`PYTHON*` variable and invoked `release-gate.sh --help`. The gate then executed
the controller through `python3` without `-B`. The controller's top-level
imports of `destination_capability` and `qualification_environment` occurred
before its controlled child environment and output preimage could exist, so
the facade interpreter wrote the two observed bytecode files. Their creation
timestamps fall inside that facade case and their marshalled filenames bind
them to the exact detached source paths.

The defect is the release-gate bootstrap argv, not an output-policy exception.
Ignoring `__pycache__`, preserving a helpful ambient Python variable, deleting
outputs after the fact, or redirecting them outside observation is forbidden.

## Exact writable ledger

Only these tracked paths may change in this repair slice:

| Action | Path | Preimage bytes | Preimage SHA-256 |
|---|---|---:|---|
| CREATE | `docs/superpowers/specs/2026-08-02-v043-c2-detached-facade-bytecode-retry-c0-addendum.md` | 0 | `ABSENT` |
| MODIFY | `scripts/release-gate.sh` | 54,831 | `0753642c86fce5f0a26f18c9577a44eb56204bade8ccae984029fada2454b1f3` |
| MODIFY | `scripts/release_qualification_controller_smoketest.py` | 145,528 | `60274392eb6e0416a78779c53d76ba4db79b880bf8c950c44b8e547bdc2f4c1b` |
| MODIFY | `references/contract_kernel.v1.json` | 37,242 | `1f7b8769ccbb42c51187795c08af930864128870199caed43599fb9773df59c9` |
| MODIFY | `references/compatibility/shipment-v2/contract_kernel_projection.json` | 2,907 | `3eefe778c84ad9885c825f3268bbe035c871e294e85c82d3ab9fd87f5f45e971` |
| MODIFY | `references/compatibility/shipment-v2/compatibility_profile.json` | 4,510 | `c8b75bfb26e6ba484bf1653e6e8c59fa1b91cff41da4ea76bf0f558f8fab33a9` |
| QUALIFICATION OUTPUT ONLY | `docs/analysis/generated/fixture_manifest.json` | 54,252 | `bd9f3f1beb882813bf7717c49202d76ee97f48dd10f2806c499fc174d48bfc19` |

The already-authorized ignored C2 evidence paths may be updated to bind
attempts 005, 008, 009, and 010. No controller source, destination registry,
schema, diagnostic map, version, package, cache, registration, research, or
remote path is writable in this slice.

## Required red-to-green repair

1. Preserve attempt 008 and its output-scope refusal. Product success is not
   detached qualification.
2. Add explicit `-B` to both `release-gate.sh` controller invocations: the
   attested `verify-child` path and the primary controller `run` path.
3. Preserve the smoketest's Python-stripped facade environment. Strengthen its
   regression to bind both gate argv surfaces, require the nested facade
   receipt to be terminal `succeeded` with null diagnostic and quiescent owned
   processes, and prove no new, changed, or removed package bytecode or
   `__pycache__` topology.
4. Run the focused Windows controller suite, the WSL/POSIX controller suite,
   fixture-infrastructure and subprocess-policy checks, exact package-wide
   bytecode censuses, and the mechanical structural checks required by the
   parent. Obtain independent B0/M0/m0 review before committing the repair.
5. Rebind only the normalized `release-gate` component hash in the contract
   kernel, then the raw kernel hash in the compatibility projection, then the
   raw six-file compatibility-kit aggregate in the profile.

## Guarded cleanup and retry transactions

After this addendum is committed and zero live attempt-008 processes are
re-observed, only the two exact hash/size-bound `.pyc` files above may be
removed, followed by their exact parent directory only if it is empty. Broad
or recursive bytecode cleanup is forbidden. The preserved detached worktree
may then be removed through `git worktree remove` only after its tracked state
is clean and the refusal artifacts above remain available at their frozen run
path.

The only new transaction paths are:

- source-root attempt 009:
  `C:\Users\young\AppData\Local\Temp\coauthor-v043-qualification-20260802-attempt-009`;
- detached replay attempt 010:
  `C:\Users\young\AppData\Local\Temp\coauthor-v043-qualification-20260802-attempt-010`;
- detached retry worktree:
  `B:\Agents\.coauthor-v043-c2-detached-retry`.

Each path must be absent before creation, receive controller-owned identity and
receipt binding where applicable, and be quiescent before cleanup. Attempt 009
must qualify the committed repair with the complete authoritative cache-off
registry and may replace the manifest only on terminal success. That manifest
must then be committed before attempt 010. Attempt 010 must run the exact
committed tree with `--tier full --no-write --cache-mode off`, permit no package
output, and finish terminal `succeeded`. Attempts 005 and 008 remain immutable.

Any warning, refusal, incomplete evidence, drift, cache hit, new output,
unledgered path, failed case, missing process closure, or review finding is a
stop requiring new authority. C2, version, package, cache, clearance, remote,
shipment, fresh-host, startup-catalog, loaded-path, consumer, activation,
research, acceptance, promotion, and canon claims remain closed until their
separate gates are satisfied.
