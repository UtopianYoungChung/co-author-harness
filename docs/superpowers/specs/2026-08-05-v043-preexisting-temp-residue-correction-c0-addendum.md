# v0.43 preexisting temp-residue correction C0 addendum

**Date:** 2026-08-05  
**Status:** Approved C0 correction authority; no qualification, version,
package, cache, shipment, host, consumer, research, activation, acceptance,
promotion, release, or canon claim  
**Run scope:** `adhoc_review`

## Parent authority and stop preservation

This correction is subordinate to the active Master Governance resolution and
the complete v0.43 C0 chain, especially:

- `docs/superpowers/specs/2026-08-05-v043-attempt-023-fixture-owner-red-c0-addendum.md`.

All parent single-branch, exact-byte, red-preservation, stream, process,
tested-population, evidence, review, and no-claim boundaries remain binding
except for the exact residue and retry corrections below.

The parent required zero residual `release-controller-smoke-*` directories at
attempt-024 postflight. Postflight instead observed the preexisting directory
`C:\Users\young\AppData\Local\Temp\release-controller-smoke-q7vjzhmm`.
Therefore attempt 025 did not start. The observation is a parent stop, not a
silently accepted exception.

Read-only inspection proves this directory predates attempt 024:

- root creation: `2026-08-03T07:51:45.8643569Z`;
- root last write: `2026-08-03T07:52:13.3779934Z`;
- latest entry last write: `2026-08-03T07:52:14.3954331Z`;
- attempt 024 root creation: `2026-08-05T10:23:24.7734889Z`;
- attempt 024 final root write: `2026-08-05T10:24:21.9372429Z`.

The residue contains 114 identities including its root: 34 directories and 80
files, zero discovered links, and 45,541 total file bytes. Its deterministic
inventory is 8,637 UTF-8 bytes, SHA-256
`3bd3e82ea9b0441ffb556aafa67d6a625dc376665889c6cc1bb18de8342e7f40`.
The inventory algorithm is the Windows PowerShell 5.1 algorithm used for this
freeze under culture `en-US`. It emits one row per identity relative to the
residue root, normalizes every relative path separator to `/`, renders every
file SHA-256 as lowercase hexadecimal, and renders: `D<TAB>path` for directories,
`F<TAB>path<TAB>byte_length<TAB>sha256` for files, and
`L<TAB>path<TAB>link_type<TAB>target` for links; the root path is `.`. Complete
rendered rows—not path keys—are ordered by Windows PowerShell
`Sort-Object -CaseSensitive` using `en-US` culture. The rows are joined with LF,
including one terminal LF after the final row, then encoded as UTF-8 without a
BOM before SHA-256. Ordinal sorting, another culture, native `\` separators,
uppercase digests, another sort key, CRLF, or a BOM is nonconforming.

The residue is frozen historical diagnostic state. It must not be deleted,
renamed, normalized, followed as authority, or modified. Its exact inventory,
counts, total file bytes, root timestamps, and maximum entry timestamp must be
recomputed and match before and after every remaining launch and before any
commit. No lifecycle, review, qualification, acceptance, or provenance claim
is inferred from its contents.

## Attempt 024 binding and limit

Attempt 024 at
`C:\Users\young\AppData\Local\Temp\coauthor-v043-qualification-20260805-attempt-024`
is an immutable terminal focused diagnostic success:

- state `succeeded`, controller diagnostic `null`, child exit `0`, finalized
  `2026-08-05T10:24:21.842063Z`;
- receipt 367,781 bytes, SHA-256
  `5f74b479859804e89ef1249035e58148f1cba412c968dd91e20a06bad641c028`;
- canonical intent SHA-256
  `11fd62af8f6be332cfacc6fb7e35b1852686ae9ac9b5f728fd1a0a0b514723d6`;
- request SHA-256
  `b3ab94f9023bb54e18e0fb7122b228b4449c6c817c36cd730b7d1ca703d65947`;
- stdout 134 bytes, SHA-256
  `224ca6676fb93ca7b4d392927b4d33f1a47ad5bfded6cbc4d951ce792588970b`,
  containing exactly the registered 53-case, 9-skip fixture-owner PASS line;
- child stderr, worker stdout, and worker stderr each 0 bytes at SHA-256
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`;
- six explicit inputs and one primary input root remained stable;
- worker PID 51364 and child PID 35348 are dead;
- retry-10 stayed clean and its 94,919-byte index remained SHA-256
  `41abeeba5cf8cbfa85ce54f43bf287f3aa8cb4655bd3df01ba9bd5fcc515ec48`;
- the shared runner lock remained 65 bytes at SHA-256
  `24f866592b176429714bb136f0d8adc7ad8574f499ed5ba7f34fb8a92d00c0ab`.

The current durable residue identity, timestamps, and bytes predate attempt
024, and no durable postflight evidence attributes them to attempt 024.
Because no pre-attempt inventory of this path was captured, historical
interaction or touch-and-restoration cannot be proven or excluded. This
correction freezes only the currently observed state and makes no stronger
negative claim. Attempt 024's focused result is diagnostic only. It does not
erase attempt 023, qualify source, or authorize
version, package, cache, shipment, host, consumer, research, or activation
claims.

## Frozen repository and exact tracked ledger

- Repository: `B:\Agents\platform\co-author-harness`; branch: `main` only.
- Pre-correction HEAD:
  `63266c6e747343767f26aa4bb94e63f7274e4f4b`.
- Pre-correction HEAD tree:
  `dbd411f2f19189c621cd075f13fbc93988d7ae74`.
- Primary tracked worktree is clean before this untracked correction.
- Committed manifest: 54,260 bytes, SHA-256
  `6baf186f2760b41980df98de86e7797dadcb82d5582c89120872bbed13ead38e`.

Only these tracked paths are writable:

| Authority | Path | Preimage bytes | Preimage SHA-256 |
|---|---|---:|---|
| CREATE AND COMMIT ALONE | `docs/superpowers/specs/2026-08-05-v043-preexisting-temp-residue-correction-c0-addendum.md` | absent | not applicable |
| QUALIFICATION OUTPUT REPLACEMENT ONLY | `docs/analysis/generated/fixture_manifest.json` | 54,260 | `6baf186f2760b41980df98de86e7797dadcb82d5582c89120872bbed13ead38e` |
| MODIFY AFTER GENERATION AND CLEAN REPLAY SUCCESS ONLY | `releases/verification/v0.43.0/C2/C2_SOURCE_QUALIFICATION.md` | 2,034 | `cae9a2ef7bc88f0ee02e4c79c2b108888894b1a5f5d16def6a0afbd9e889d243` |
| MODIFY AFTER GENERATION AND CLEAN REPLAY SUCCESS ONLY | `releases/verification/v0.43.0/C2/C2_STRUCTURAL_RESULTS.json` | 634 | `5556b373de0cfa7f209a0afa915620569e33515079f5bf5c00f1f8310f82998e` |
| MODIFY AFTER GENERATION AND CLEAN REPLAY SUCCESS ONLY | `releases/verification/v0.43.0/C2/C2_REGISTRY_RESULTS.json` | 2,254 | `957a91428ef875097678d62590c58baae86988732d2c3a7be54b13c35b0ce9de` |
| MODIFY AFTER GENERATION AND CLEAN REPLAY SUCCESS ONLY | `releases/verification/v0.43.0/C2/C2_DETACHED_REPLAY.json` | 2,590 | `38862b17278643de65e6784bb166f22998c6f6c9f5db35a3e74da38d0061cb49` |
| CREATE AFTER GENERATION AND CLEAN REPLAY SUCCESS ONLY | `releases/verification/v0.43.0/C2/C2_READ_ONLY_REVIEW.md` | absent | not applicable |

This correction must be committed alone on `main` before retry-10 removal or
fresh-path creation. Ordinary Git object, primary index, reflog, and
`refs/heads/main` changes are authorized only as Git-managed consequences of
the correction-only commit, a later manifest-only commit after attempt-027
success, and a later C2-evidence-only commit after three exact-byte B0/M0/m0
reviews. Record each commit SHA, tree, and exact changed-path set. No product
source, version, package, archive, cache, catalog, startup, host, consumer,
research, shipment, or activation byte is writable.

## Superseded and fresh transient ledger

Attempts 025 and 026 never started. Their transaction roots are absent. Retry-11
and its admin subtree are absent. Those unused labels and paths are retired and
must remain absent; they carry no intent, execution, receipt, or evidence.

After attempt-024 evidence and the frozen residue are rebound, Git-managed
removal is authorized only for the clean retry-10 worktree and its exact admin
subtree:

- `B:\Agents\.coauthor-v043-c2-detached-retry-10`;
- `B:\Agents\platform\co-author-harness\.git\worktrees\-coauthor-v043-c2-detached-retry-10`.

Only these fresh durable or governed paths may be created:

- generation worktree `B:\Agents\.coauthor-v043-c2-detached-retry-12`;
- generation admin subtree
  `B:\Agents\platform\co-author-harness\.git\worktrees\-coauthor-v043-c2-detached-retry-12`;
- generation transaction
  `C:\Users\young\AppData\Local\Temp\coauthor-v043-qualification-20260805-attempt-027`;
- clean replay worktree `B:\Agents\.coauthor-v043-c2-detached-retry-13`;
- clean replay admin subtree
  `B:\Agents\platform\co-author-harness\.git\worktrees\-coauthor-v043-c2-detached-retry-13`;
- clean replay transaction
  `C:\Users\young\AppData\Local\Temp\coauthor-v043-qualification-20260805-attempt-028`.

Each fresh path must be proved absent before creation. Any different canonical
admin ID or unlisted durable/governed path is a stop. Attempts 017, 019, 021,
022, 023, and 024 remain immutable evidence.

Process-owned package-independent OS-temp scratch already classified by the
frozen fixture corpus remains ephemeral and must clean itself. Apart from the
one exact frozen Aug 3 residue above, the set of `release-controller-smoke-*`
directories must be empty before and after attempts 027 and 028. No new residue
or modification of the frozen residue is permitted.

## Frozen launcher and success gates

Attempts 027 and 028 use exact interpreter
`C:\Users\young\AppData\Local\Python\pythoncore-3.14-64\python.exe` with `-B`
for controller and child. `PYTHONUTF8`, `PYTHONPATH`, `PYTHONHOME`,
`PYTHONWARNINGS`, and `PYTHONOPTIMIZE` must be absent. Each launch passes
`--allow-user-site`, no `--ignored-output`, the primary checkout as the sole
`--input-root`, primary `.git\HEAD` and `.git\refs\heads\main`, and the
applicable detached admin `HEAD`, `index`, `commondir`, and `gitdir` as six
explicit inputs. The applicable detached worktree is the sole watch root.

Every status observation is
`git --no-optional-locks -C <worktree> status --porcelain=v1 --untracked-files=all`,
with index bytes and SHA-256 recorded immediately before and after. Any index
change is a stop.

Attempt 027 uses retry-12 detached at the exact correction commit. Its sole
allowed output is the retry-12 manifest; its child is:

```text
<python> -B <retry-12>\scripts\analysis\fixture_runner.py
  --tier full --cache-mode off
```

Attempt 027 must terminally succeed with child exit 0, diagnostic null, 93/93
suites, 97/97 cases, no warning rows, stable tested inputs and all explicit
inputs, exactly the manifest changed, unchanged detached index, a separately
bound runner-lock transition, frozen residue equality, no other temp residue,
and zero surviving owned processes. Receipt, child stdout/stderr, and worker
stdout/stderr are each bound by path, byte length, and SHA-256. Child stderr
and both worker streams must be zero bytes at SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
Only then may the generated manifest replace primary and be committed alone
after exact byte equality is proved.

After complete attempt-027 evidence capture, force-remove dirty retry-12 and
its exact admin subtree. Create retry-13 detached at the exact manifest commit.
Attempt 028 uses no allowed output and child:

```text
<python> -B <retry-13>\scripts\analysis\fixture_runner.py
  --tier full --cache-mode off --no-write
```

Attempt 028 must meet the same non-output gates, with zero output changes and
clean retry-13. Any failure, warning, ambiguity, input drift, residue mismatch,
additional temp residue, index rewrite, process residue, output mismatch, or
unlisted path is red and stops.

## Exact execution sequence and downstream limit

1. Obtain three independent B0/M0/m0 reviews of these exact approved bytes.
2. Rebind main, retry-10, attempt 024, lock, frozen residue, and unused/fresh
   path absences; commit this correction alone and record SHA/tree/path set.
3. Rebind retry-10 clean status/index, remove it, and prove its worktree/admin
   paths absent while preserving attempt 024.
4. Create retry-12 detached at the exact correction commit; bind HEAD, tree,
   canonical admin path, four admin inputs, index, clean status, environment,
   refs, lock, primary input root, residue, and path absences.
5. Run attempt 027. Only after every gate passes may its exact manifest replace
   primary and be committed alone. Capture evidence and remove retry-12/admin.
6. Create retry-13 detached at the exact manifest commit, bind the same
   preflight planes, and run attempt 028. Only after every gate passes may the
   five C2 evidence paths be updated.
7. Obtain three independent exact-byte B0/M0/m0 reviews of C2 evidence, commit
   only those paths, then remove clean retry-13/admin and prove absence.

C2 success, if reached, authorizes only the next pre-existing v0.43 C0 gate.
Gate 6 remains closed absent a separately governed v0.43 consumer receipt.
This task may not author or simulate that receipt. ZIP/cache work, package
clearance, push/tag/assets, shipment, fresh-host qualification, research
mutation, and activation remain closed.
