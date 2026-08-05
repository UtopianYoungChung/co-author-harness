# v0.43 attempt-029 environment-delta rejection C0 addendum

**Date:** 2026-08-05  
**Status:** Approved C0 correction authority when these exact bytes receive
three independent B0/M0/m0 reviews; no qualification, version, package, cache,
consumer, shipment, host, research, activation, acceptance, promotion, release,
or canon claim  
**Run scope:** `adhoc_review`

## Parent authority and preserved rejection

This correction is subordinate to the active Master Governance resolution and
the complete committed v0.43 C0 chain, especially the exact-byte reviewed and
committed parent:

- `docs/superpowers/specs/2026-08-05-v043-postqualification-structural-index-refresh-c0-addendum.md`;
- commit `82dffdd500b22caa5429abba93fd2dc104df5ee8`, tree
  `5ddafc5034c7de7c4deeac1b8fc95d2ace04365a`;
- parent bytes 14,546, SHA-256
  `ad40e2edb8a1b60b6e28be973e656ab8b94bbdcf492f6e37ae74c88030309cd7`;
- independent parent review result B0/M0/m0 from each of three reviewers.

Every parent single-branch, exact-byte, structural, inventory, index,
transient-lock, process, stream, tested-population, residue, evidence, review,
consumer, and no-claim boundary remains binding except for the exact attempt
labels, launcher correction, population, and transient paths below.

After the parent commit, retry-13 and its admin subtree were removed through
Git worktree management and proved absent; attempt 028 remains preserved.
Retry-14 was created detached at the parent commit. Its 15-command structural
batch passed 15/15. The first 14 stderr streams were zero bytes; the sole
fixture-infrastructure stderr was the exact registered 805-byte negative-test
stream at SHA-256
`9cd7690903b6b91f5a6183083883ffe9dadd4241bed165e6b2ca386416059ee2`.
Retry-14 remained clean at the parent HEAD/tree; its 927-entry full inventory
remained SHA-256
`0e7ed1978a39c4c83b37678eb046b5bd1824a1a5c6c60717dfc644134bcbd3c3`;
its 95,231-byte index remained SHA-256
`008df3b1bf7e047303f533e537bcc49d3fa45837057c00b729998facfa7e6c3e`;
the primary 1,862-entry input-root inventory remained SHA-256
`32b7991260080b831113eb6a1a10d55b275aa339d8965ed916236160545f1c91`;
all other inputs, topology, manifest, lock, residue, and fresh paths remained
stable. The resulting 745-file tested population was canonical SHA-256
`e05c6ff73d80fd66980544429cb6b4f9e79b0e244cfe679af1bed90fe6693d90`
and raw SHA-256
`c28033bc8501cf1290b44d32d1333bc1f7802f6a0af92df4a68908e596546cb1`.

The attempt-029 launcher then incorrectly supplied
`--env PYTHONDONTWRITEBYTECODE=1`. The controller refused before transaction
creation with state `refused`, code `QUALIFICATION-ENV-DELTA`, and detail
`QUALIFICATION-ENV-DELTA: caller may not inject Python controls:
PYTHONDONTWRITEBYTECODE`; the observed controller CLI exit was `2`. No durable
separated console capture was created. The semantic stdout observed in the
console was this sorted JSON object:

```text
{"code": "QUALIFICATION-ENV-DELTA", "detail": "QUALIFICATION-ENV-DELTA: caller may not inject Python controls: PYTHONDONTWRITEBYTECODE", "state": "refused"}
```

No byte length, newline encoding, or stream SHA-256 is claimed: source-level LF
and Windows text-stream CRLF reconstructions differ, and no durable capture can
resolve which bytes crossed this console boundary. The exact source routes the
caught-refusal JSON to stdout and returns `2`, but no durable separated stdout
or stderr capture exists. The attempt-029 path remains absent. No intent,
owner, journal, exit capsule, receipt, worker stream, child process, product
process, output, manifest change, index change, or qualification evidence was
created. This console refusal is preserved as a pretransaction invocation
rejection. Label 029 is consumed and must not be reused or upgraded.

The exact source contract proves the corrected launcher must omit `--env`.
`controlled_environment()` internally records the safe child delta
`PYTHONDONTWRITEBYTECODE=1` when `--allow-user-site` is selected; a caller may
not inject any key beginning with `PYTHON`. This correction changes only that
launcher construction. It does not change product code or reinterpret the
rejection.

## Frozen state and retired labels

- Repository `B:\Agents\platform\co-author-harness`, branch `main` only.
- Current HEAD/tree before this candidate:
  `82dffdd500b22caa5429abba93fd2dc104df5ee8` /
  `5ddafc5034c7de7c4deeac1b8fc95d2ace04365a`.
- Primary worktree: clean before this untracked candidate.
- Retry-14/admin: present, detached, clean, exact bindings above.
- Manifest: 54,260 bytes, SHA-256
  `1f6eb7fd26f1b0417c6af946a5ddfcf4800e268097ace6831ed4ad62c44f9f2a`.
- Shared runner lock: 66 bytes, SHA-256
  `e178159f0a844e1afbf4dff513f7ad31bf639bc33929cc592f572ef320d73cac`,
  still naming dead attempt-028 child PID 62320 and removed retry-13.
- Frozen Aug-3 residue: unchanged 8,637-byte inventory, SHA-256
  `3bd3e82ea9b0441ffb556aafa67d6a625dc376665889c6cc1bb18de8342e7f40`;
  it remains the sole `release-controller-smoke-*` directory.
- Attempt 029 path: absent; related worker/product processes: zero.
- Retry-15/admin and attempt 030 never started. They are retired, remain absent,
  and carry no execution, transaction, or evidence claim.
- This candidate, retry-16/admin, attempt 031, retry-17/admin, and attempt 032
  were absent at freeze.

## Exact writable and transient ledger

| Action | Path | Preimage bytes | Preimage SHA-256 |
|---|---|---:|---|
| CREATE AND COMMIT ALONE | `docs/superpowers/specs/2026-08-05-v043-attempt-029-env-delta-rejection-c0-addendum.md` | absent | not applicable |
| GENERATION OUTPUT; REPLACE AND COMMIT ALONE AFTER ATTEMPT 031 SUCCESS ONLY | `docs/analysis/generated/fixture_manifest.json` | 54,260 | `1f6eb7fd26f1b0417c6af946a5ddfcf4800e268097ace6831ed4ad62c44f9f2a` |

The five registered C2 files remain ignored/local evidence under the governing
v0.43 C0. They may be updated only after all gates pass and must never be
staged, force-added, or committed.

Ordinary Git objects, the primary index, the `main` reflog, and
`refs/heads/main` may change only as Git-managed effects of exactly two commits:
this addendum alone and the later manifest alone. Record each SHA, tree, exact
changed-path set, and primary-index pre/post digest. No other Git mutation is
authorized.

After the addendum-only commit, Git-managed removal is authorized only for
clean retry-14 and its exact admin subtree. These are the only new transient or
durable paths authorized:

- `B:\Agents\.coauthor-v043-c2-detached-retry-16`;
- `B:\Agents\platform\co-author-harness\.git\worktrees\-coauthor-v043-c2-detached-retry-16`;
- `C:\Users\young\AppData\Local\Temp\coauthor-v043-qualification-20260805-attempt-031`;
- `B:\Agents\.coauthor-v043-c2-detached-retry-17`;
- `B:\Agents\platform\co-author-harness\.git\worktrees\-coauthor-v043-c2-detached-retry-17`;
- `C:\Users\young\AppData\Local\Temp\coauthor-v043-qualification-20260805-attempt-032`.

Each must be proved absent before creation. The applicable retry admin `index`
is the sole persistent byte allowed to transition during a structural batch;
only its same-admin `index.lock` may exist transiently, and it must be absent
pre/post. Every other admin transient or residue is a stop. No version, package,
archive, cache, catalog, startup, host, consumer, research, shipment, or
activation byte is writable.

## Corrected recovery sequence

1. Obtain three independent exact-byte B0/M0/m0 reviews of this addendum.
2. Rebind every frozen plane and path absence; commit this addendum alone on
   `main`; record exact Git effects.
3. Rebind clean retry-14 and remove only it and its admin subtree through Git
   worktree management. Preserve the absent attempt-029 path and its rejection.
4. Create retry-16 detached at the exact addendum commit. Apply the parent's
   complete preflight and 15-command structural-batch gates, including full
   ignored-inclusive worktree and primary inventories, all six explicit inputs,
   index/index.lock, topology, manifest/source, runner lock, exact stderr
   allowlist, frozen residue, smoke set, process census, and fresh-path set.
   Require 15/15 exit zero and freeze the post-structural index.
5. Start attempt 031 with the exact parent generation launcher except that no
   `--env` argument is present. Controller and child use exact Python with `-B`;
   `--allow-user-site` is present; the five forbidden ambient Python controls
   remain absent; the controller receipt must record exactly the internally
   produced environment delta `{"PYTHONDONTWRITEBYTECODE":"1"}` and no other
   environment-delta key.
   Use primary as sole input root, the six rebound explicit inputs, retry-16 as
   sole watch root, retry-16 manifest as sole allowed output, and child:

   ```text
   <python> -B <retry-16>\scripts\analysis\fixture_runner.py
     --tier full --cache-mode off
   ```

6. Attempt 031 must meet every parent generation success gate over the now
   746-file population: terminal success, diagnostic null, exit zero, 93/93
   suites, 97/97 cases, exact order, 93/93 source hashes, zero warnings/failures
   and cache hits, stable full canonical/raw digests, stable inputs/root/index,
   exactly the manifest changed, exact stream/receipt bindings, lock transition,
   residue equality, no new smoke residue, and zero owned processes.
7. Copy only the exact generated manifest to primary, prove equality, commit it
   alone, record exact Git effects, then force-remove dirty retry-16/admin only
   after the manifest is preserved and committed. Preserve attempt 031.
8. Create retry-17 at the exact manifest commit. Repeat the complete structural
   batch and freeze its post-structural index under the same gates.
9. Start attempt 032 with the same corrected no-`--env` controller launcher,
   no allowed output, retry-17 as sole watch root, and child:

   ```text
   <python> -B <retry-17>\scripts\analysis\fixture_runner.py
     --tier full --cache-mode off --no-write
   ```

   Its receipt must likewise record exactly
   `{"PYTHONDONTWRITEBYTECODE":"1"}` and no other environment-delta key.

10. Attempt 032 must reproduce attempt 031's exact 746-file canonical/raw
    digests, manifest case order, and 93/93 source hashes; pass every non-output
    gate; create no output; preserve retry-17 index and clean status; and leave
    zero owned processes. Any rejection, warning, mismatch, ambiguity, output,
    residue, or survivor is red and stops.
11. Only then update and exact-byte review the five ignored/local C2 evidence
    paths. Preserve every prior red, refusal, interruption, warning, historical
    success, attempt 028, the postqualification index stop, and attempt-029
    invocation rejection. Attempt 032 is the current clean replay. Require three
    independent B0/M0/m0 reviews; do not stage or commit C2 evidence; then remove
    clean retry-17/admin and preserve attempts 031 and 032.

Attempt-032 success authorizes only C2 completion and the next pre-existing
v0.43 C0 gate. Gate 6 remains closed absent separately governed v0.43 consumer
evidence. Package/archive/cache work, package clearance, push/tag/assets,
shipment, fresh-host qualification, research mutation, and activation remain
closed.
