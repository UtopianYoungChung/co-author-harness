# v0.43 C2 attempt-003 timeout and observer-isolation C0 addendum

**Status:** approved package-maintainer boundary for closing the two defects
exposed by refused C2 attempt 003 and for one new controller-owned retry. This
addendum grants no package clearance, shipment, cache mutation, consumer
re-attestation, host qualification, activation, research mutation, acceptance,
promotion, release, or canon authority.

**Run scope:** `adhoc_review`.

**Parent authority:**
`docs/superpowers/specs/2026-08-02-v043-c2-controller-teardown-race-c0-addendum.md`.
All parent prohibitions and later gates remain binding. Any path not enumerated
here or in the parent ledgers requires another committed addendum before it is
created or changed.

## Frozen refused transaction and source state

- Source branch: `main` only.
- Source HEAD:
  `58af6ff78fe7966294761e9a090084b73ed60d43`.
- Source tree:
  `3a4d9b18c97f171556a7ee477351cf51cdef5d8d`.
- Refused run:
  `C:\Users\young\AppData\Local\Temp\coauthor-v043-qualification-20260802-attempt-003`.
- Attempt-003 controller receipt: 3,325 bytes, SHA-256
  `fde11e03054fc3a6043c23fbc38457bb0ce789b5de79127c7f00eb9ec6159e70`.
- Attempt-003 journal: 762 bytes, SHA-256
  `a44f393e444734b0cff385b394daf1677d1f102bdb3468528ec3d9511df1b8fc`.
- Attempt-003 exit capsule: 757 bytes, SHA-256
  `ae0783b1c1525dbcd944600ebcc73ba2df258f0321cdf9b073533d5fcaf56b58`.
- Attempt-003 stdout: 8,329 bytes, SHA-256
  `7ddfe416da2196c70c23663eb59dc7ca3d28321848c4d2c2996ee337bb889b31`.
- Attempt-003 stderr: 284 bytes, SHA-256
  `6e6bb761c888b901f70e5925537da127333d6eea338794d7847d41ee24ba26e2`.
- Attempt-003 is permanently `refused`: child exit 2 and controller diagnostic
  `RELEASE-CONTROLLER-OUTPUT-SCOPE` for `.git/index` and `.git/index.lock`.
  It may never be reused or reclassified as green evidence.
- The authoritative runner passed all recorded cases preceding
  `scripts/scholarly_evaluation_smoketest.py`, then that suite reached the
  exact 900-second registry timeout. Attempt 002 had passed the same suite in
  831.94 seconds, leaving only 68.06 seconds of slow-host margin.
- The canonical fixture manifest was voided at attempt-003 start and is now
  absent. Its tracked deletion remains failed-transaction state. It must not be
  restored from attempts 001 or 002 and may be republished only by a new green
  authoritative run.
- A zero-byte `.git/index.lock` was created at
  `2026-08-02T11:12:15.7100075-04:00` while parallel read-only audit lanes ran
  Git observations during the transaction. Its SHA-256 is
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
  No repository Git process owns it after attempt-003 closure.
- The current `.git/index` is 89,983 bytes, SHA-256
  `bb83d546ea8c8853350545291db874b82d09a5755646917e008e951c6a9b65a5`.
  Its mutation is transaction interference, not source qualification evidence.

## Reopened reds and architectural causes

1. **Slow-host timeout envelope.** The global 900-second default is too narrow
   for the registered scholarly-evaluation suite: a prior green run consumed
   92.4% of the envelope and the next run reached the boundary. This is an
   environment void, never a subject PASS or FAIL.
2. **Observer effect on the watched Git administration plane.** Git status and
   related read-only Git operations may refresh `.git/index` and transiently
   create `.git/index.lock`. Those bytes are correctly watched by the durable
   controller, so parallel Git observers make the transaction non-isolated.
   The controller refusal must stand; the remedy is observer isolation, not a
   broader ignore rule.

## Exact authorized change surface

Only these paths/actions are authorized in this repair slice:

| Action | Path | Bytes | SHA-256 / preimage |
|---|---|---:|---|
| CREATE | `docs/superpowers/specs/2026-08-02-v043-c2-attempt-003-timeout-observer-isolation-c0-addendum.md` | 0 | `ABSENT` |
| MODIFY | `scripts/analysis/fixture_runner.py` | 39,667 | `113d2cc1265bf297810e896791fd5922a7c50b67469ef3c47edfb8d05e700526` |
| GUARDED REMOVE | `.git/index.lock` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| FAILED OUTPUT / RETRY MAY WRITE | `docs/analysis/generated/fixture_manifest.json` | absent | `ATTEMPT_003_VOID` |
| CREATE TRANSIENT RUN | `C:\Users\young\AppData\Local\Temp\coauthor-v043-qualification-20260802-attempt-004` | 0 | `ABSENT` |

The existing ignored C2 evidence paths authorized by the parent may later be
updated to bind attempts 001-004 and the final result. No new C2 evidence
filename is authorized here.

## Required red-to-green repair

1. After proving attempt 003 terminal, no matching controller/runner process,
   and no repository Git process, remove only the exact zero-byte stale
   `.git/index.lock` above. Refuse if its path, size, digest, or ownership state
   differs.
2. Commit this addendum alone before editing the runner.
3. In `scripts/analysis/fixture_runner.py`, give only
   `scripts/scholarly_evaluation_smoketest.py` an explicit 1,200-second timeout.
   Do not widen the global default or any other suite.
4. Prove the registry still contains exactly 93 suites and 97 cases, and the
   only timeout-contract delta is the scholarly-evaluation default case from
   900 to 1,200 seconds.
5. Run the scholarly-evaluation suite directly with `python -B` under a
   repository-wide pre/post `.pyc` census. Require exit 0, measured runtime
   below 1,200 seconds, and zero created, changed, or removed bytecode.
6. Run the fixture-infrastructure check, independent B0/M0/m0 review, and
   commit the exact runner repair before another full registry.
7. Re-run the 15 root structural checks on the committed repair bytes and
   require a stable repository-wide `.pyc` census.

## Attempt-004 observer-isolation contract

The only authorized new full-registry retry path is:

`C:\Users\young\AppData\Local\Temp\coauthor-v043-qualification-20260802-attempt-004`

It must be absent before creation and use the same durable, cache-off,
controller-owned full-registry request as attempt 003, with no caller-injected
Python environment controls. From the final preflight census through terminal
receipt finalization:

- no Git command may run in or against this repository, including `status`,
  `diff`, `show`, `rev-parse`, `worktree`, `stash`, or read-only review probes;
- no parallel audit/review agent may inspect repository state;
- monitoring is limited to the controller `status`/`wait` interface, the run
  journal, and operating-system process identity/liveness observations;
- `.git/index` and `.git/index.lock` remain watched and must not be added to an
  ignore list;
- no package, cache, version, build, archive, tag, remote, research, or second
  corpus work may run concurrently.

Green requires controller state `succeeded`, child exit 0, exactly 93 suites
and 97 executed passing cases, zero cache hits, stable tested-input digests,
only the authorized manifest output, stable Git-administration and bytecode
censuses, process closure, and no diagnostic. Any ambiguity, timeout,
unauthorized output, or observer mutation remains STOP.

After a green attempt 004, the parent C2 evidence-binding, manifest-publication,
detached `--no-write` replay, and independent review gates resume. C2 remains
closed until all of them complete.
