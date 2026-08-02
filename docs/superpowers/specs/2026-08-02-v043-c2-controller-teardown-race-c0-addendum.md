# v0.43 C2 controller teardown-race C0 addendum

**Status:** approved package-maintainer boundary for repairing the exact-handle
Windows teardown race observed after the isolated-Python closure. This
addendum grants no C2 pass, package clearance, shipment, cache mutation,
consumer re-attestation, host qualification, activation, research mutation,
acceptance, promotion, release, or canon authority.

**Run scope:** `adhoc_review`.

**Parent authority:**
`docs/superpowers/specs/2026-08-02-v043-c2-isolated-python-retry-c0-addendum.md`.
All parent prohibitions and gates remain binding. Any path not enumerated here
or in the parent ledgers requires another committed addendum before change.

## Frozen state

- Repository: `B:\Agents\platform\co-author-harness`.
- Branch: `main`, the only permitted branch.
- Commit: `d84599a302a1929f035d171ae7d2ac4edef876c7`.
- Tree: `90b1d2adde03c15fa787f04d82dcd3b61af2c7c7`.
- The isolated-Python closure is committed at that exact commit. Its policy
  file is 40,306 bytes, SHA-256
  `e45d8b800c10e36b36e7a1cfc4df57fb5a0b10c8676f1931eeac64648d7cb8df`.
  The focused matrix passed, its 48 embedded detector cases passed, and all
  17 governed `-B` removal mutations were independently detected. The
  repository bytecode census remained 180 files with exact inventory digest
  `08c6740aab85ac2b73162dd0bb7c792815e2ba871dacb0decc3a070363085f2b`.
- The failed attempt-002 fixture manifest remains modified and uncommitted at
  54,252 bytes, SHA-256
  `74b978da52643fdf0cbd22f3a7e4a5e32cddfb4f7125ad34632e636e05c34fa7`.
  It remains failed-transaction output and may not enter this repair commit.
- The only authorized retry path remains absent:
  `C:\Users\young\AppData\Local\Temp\coauthor-v043-qualification-20260802-attempt-003`.

## Reopened red and architectural cause

A broader Windows run of
`scripts/release_qualification_controller_smoketest.py` reached the
same-exact-handle cleanup helper and failed at its unconditional
`TerminateProcess(handle, 1223)` assertion for PID 88640. The process had
naturally exited in the narrow interval after the helper's second
`WAIT_TIMEOUT` observation and before `TerminateProcess`. The PID was absent
after refusal, and the repository bytecode census remained exact-stable at
180 files and the digest above.

This is a test-harness race, not permission to weaken product process
identity. The helper already opens and retains the exact Windows process
handle, verifies its creation token, and rechecks the same handle before
termination. Windows may reject `TerminateProcess` once that exact process has
exited. Treating every such rejection as a live-process failure makes the
qualification test nondeterministic; accepting a rejection without proving
the same exact handle signaled would weaken fail-closed teardown.

## Authorized tracked paths

Only these tracked paths may change in this slice:

| Action | Path | Bytes | SHA-256 / preimage |
|---|---|---:|---|
| CREATE | `docs/superpowers/specs/2026-08-02-v043-c2-controller-teardown-race-c0-addendum.md` | 0 | `ABSENT` |
| MODIFY | `scripts/release_qualification_controller_smoketest.py` | 130,353 | `df13ca57e6900cd65970a850e51e236690f5e459b8f0bf4c3b1d9281be6f5705` |

The failed manifest is preserved but excluded from this repair commit. No
new evidence filename, transient path, package path, cache path, tag, branch,
worktree, or research path is authorized by this addendum.

## Required red-to-green repair

1. Preserve exact PID-plus-creation-token and exact-handle validation. Do not
   fall back to PID-only lookup, broad process matching, or best-effort kill.
2. Immediately capture the Windows error if `TerminateProcess` rejects the
   exact retained handle. Accept that rejection only if a bounded wait on the
   same exact handle returns `WAIT_OBJECT_0`. Do not add the naturally exited
   identity to the helper's `signalled` result. Any timeout, wait failure,
   token ambiguity, handle ambiguity, or still-live exact handle remains a
   hard assertion with the captured Windows error.
3. Add a deterministic Windows regression that forces the exact retained
   process handle to become signaled immediately before the helper's
   termination call, then proves the helper closes the handle, returns without
   a false failure, reports no self-signalled identity, and leaves no process.
4. Prove the ordinary forced-termination path still returns the exact
   PID/token identity and waits for the same retained handle to signal.
5. Run `python -B scripts/release_qualification_controller_smoketest.py` on
   Windows at least twice after the focused race case; require exit 0, 40
   passed cases, and 9 declared platform skips on the current registry. Run
   the exact POSIX slice through WSL from `/mnt/b/Agents/platform/co-author-harness`
   as `env PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B
   scripts/release_qualification_controller_smoketest.py`; require exit 0, 49
   passed cases, and 0 platform skips. Wrap both hosts in repository-wide
   pre/post `.pyc` census and require zero created, changed, or removed
   bytecode. A missing WSL/Python capability is a stop, not a skip.
6. Obtain independent B0/M0/m0 review and commit the exact repair before any
   structural sweep or attempt-003 transaction.

After the repair commit, rerun all root structural checks required by the
parent C2 ledger. Attempt 003 remains forbidden until those checks are green,
process closure is re-observed, and the committed source bytes are stable.
Any new output, intermittent failure, incomplete exact-handle proof, source
drift, or unledgered path is a stop. Later version, package, shipment, cache,
remote, fresh-host, consumer, and activation gates remain closed.
