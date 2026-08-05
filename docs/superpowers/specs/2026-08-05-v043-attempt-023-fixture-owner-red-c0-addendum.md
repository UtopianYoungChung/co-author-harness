# v0.43 attempt-023 fixture-owner red recovery C0 addendum

**Date:** 2026-08-05  
**Status:** Approved C0 recovery authority; no qualification, version, package,
cache, shipment, host, consumer, research, activation, acceptance, promotion,
release, or canon claim  
**Run scope:** `adhoc_review`

## Authority and preserved red result

This record is subordinate to the active Master Governance resolution and the
existing v0.43 C0 chain, including:

- `docs/superpowers/specs/2026-08-05-v043-attempt-019-git-plane-isolation-c0-addendum.md`;
- `docs/superpowers/specs/2026-08-05-v043-worktree-admin-id-correction-c0-addendum.md`;
- `docs/superpowers/specs/2026-08-05-v043-postreceipt-index-observer-c0-addendum.md`.

All parent red-preservation, exact-byte, single-branch, sequencing, authority,
and no-claim boundaries remain binding except for the exact retry ledger below.
This addendum does not reinterpret or erase any earlier red, warning,
interruption, missing-marker, or observer-effect evidence.

Attempt 023 at
`C:\Users\young\AppData\Local\Temp\coauthor-v043-qualification-20260805-attempt-023`
is an immutable terminal `child_failed` transaction, not a pass:

- controller started `2026-08-05T08:40:02.332645Z`, child started
  `2026-08-05T08:40:04.278523Z`, child exited
  `2026-08-05T10:11:23.445889Z`, and the receipt finalized
  `2026-08-05T10:11:25.596851Z`;
- child return code `1`; controller diagnostic `null`;
- receipt 367,551 bytes, SHA-256
  `e6e00b5612cb4a23d75f5d1fd3bb529cab0d0d35f77b3d70508b1ffc88764d2f`;
- intent SHA-256
  `d7542e97f8660dedaa412e25c388a1f9373295a16eec21541e295b28b474442b`;
- request SHA-256
  `3d8a85a684006efc66791bcafe49ac70631d8268b5370583947e776f151544a4`;
- stdout 9,693 bytes, SHA-256
  `414a651e3ff58840d1665e98b624dc067c23ad099d4d871556895e89801f77a3`;
- stderr 0 bytes, SHA-256
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`;
- 96 of 97 cases passed; the sole red case was
  `scripts/release_qualification_controller_smoketest.py::fixture-owner`,
  which exited 1 after 19.891 seconds with a captured trailing
  `AssertionError`;
- tested inputs remained stable at 742 files, canonical prefix
  `2c9dbeea4bf0`, raw prefix `d5534b92e465`;
- `--no-write` preserved the committed manifest and retry-9 remained clean.

The receipt-bound worker PID 16252 and product PID 39716 are dead. The shared
runner lock now contains exactly
`pid=39716 worktree=B:\Agents\.coauthor-v043-c2-detached-retry-9`, 65 bytes,
SHA-256
`24f866592b176429714bb136f0d8adc7ad8574f499ed5ba7f34fb8a92d00c0ab`;
its recorded PID is dead. This stale terminal lock is evidence. Manual deletion
or normalization is forbidden. It must remain byte-identical through attempt
024; only the separately authorized and exact pre/post-bound attempt-025 and
attempt-026 runner transitions may later replace its bytes.

## Frozen repository and exact writable ledger

- Repository: `B:\Agents\platform\co-author-harness`; branch: `main` only.
- Pre-addendum HEAD:
  `a758e67a63cf31304c1b384022f7b5fe5a3c1efd`.
- Pre-addendum HEAD tree:
  `4dccb3c34a9d1b02c05841bfc7c3f339a73169f3`.
- Primary tracked worktree is clean before this untracked addendum.
- Committed manifest: 54,260 bytes, SHA-256
  `6baf186f2760b41980df98de86e7797dadcb82d5582c89120872bbed13ead38e`.
- Retry-9 detached index: 94,767 bytes, SHA-256
  `1fe8123d6c74a7869cdfd5dd3627d4ff626045220ba09ec9ad6145ec334d9ddc`
  before and after the required no-optional-locks postflight status; retry-9
  status has zero rows.

Only these tracked paths are writable:

| Authority | Path | Preimage bytes | Preimage SHA-256 |
|---|---|---:|---|
| CREATE AND COMMIT ALONE | `docs/superpowers/specs/2026-08-05-v043-attempt-023-fixture-owner-red-c0-addendum.md` | absent | not applicable |
| QUALIFICATION OUTPUT REPLACEMENT ONLY | `docs/analysis/generated/fixture_manifest.json` | 54,260 | `6baf186f2760b41980df98de86e7797dadcb82d5582c89120872bbed13ead38e` |
| MODIFY AFTER FRESH GENERATION AND CLEAN REPLAY SUCCESS ONLY | `releases/verification/v0.43.0/C2/C2_SOURCE_QUALIFICATION.md` | 2,034 | `cae9a2ef7bc88f0ee02e4c79c2b108888894b1a5f5d16def6a0afbd9e889d243` |
| MODIFY AFTER FRESH GENERATION AND CLEAN REPLAY SUCCESS ONLY | `releases/verification/v0.43.0/C2/C2_STRUCTURAL_RESULTS.json` | 634 | `5556b373de0cfa7f209a0afa915620569e33515079f5bf5c00f1f8310f82998e` |
| MODIFY AFTER FRESH GENERATION AND CLEAN REPLAY SUCCESS ONLY | `releases/verification/v0.43.0/C2/C2_REGISTRY_RESULTS.json` | 2,254 | `957a91428ef875097678d62590c58baae86988732d2c3a7be54b13c35b0ce9de` |
| MODIFY AFTER FRESH GENERATION AND CLEAN REPLAY SUCCESS ONLY | `releases/verification/v0.43.0/C2/C2_DETACHED_REPLAY.json` | 2,590 | `38862b17278643de65e6784bb166f22998c6f6c9f5db35a3e74da38d0061cb49` |
| CREATE AFTER FRESH GENERATION AND CLEAN REPLAY SUCCESS ONLY | `releases/verification/v0.43.0/C2/C2_READ_ONLY_REVIEW.md` | absent | not applicable |

No product source, controller, smoketest, schema, compatibility profile,
version, package, archive, cache, catalog, startup, host, consumer, research,
shipment, or activation byte is writable. A reproduced focused failure or any
need to repair product source is a stop requiring a separately reviewed C0
source-repair addendum.

This addendum must be committed alone on `main` before retry-9 removal or any
fresh-path creation. Ordinary Git object, primary index, reflog, and
`refs/heads/main` changes are authorized only as the Git-managed consequences
of: (1) that addendum-only commit, (2) the later manifest-only commit after
attempt-025 success, and (3) the later C2-evidence-only commit after three
independent B0/M0/m0 reviews. Each commit's exact SHA, tree, and changed-path
set must be recorded. No other Git mutation is authorized.

## Exact transient ledger

Attempt 023 and all older transaction roots remain immutable evidence and may
not be deleted, renamed, reused, or rewritten.

This addendum authorizes Git-managed removal of the already-bound clean retry-9
worktree and only its exact administrative subtree:

- `B:\Agents\.coauthor-v043-c2-detached-retry-9`;
- `B:\Agents\platform\co-author-harness\.git\worktrees\-coauthor-v043-c2-detached-retry-9`.

Only these fresh durable or governed paths may then be created:

- focused diagnostic and manifest-generation worktree
  `B:\Agents\.coauthor-v043-c2-detached-retry-10`;
- its Git-managed admin subtree
  `B:\Agents\platform\co-author-harness\.git\worktrees\-coauthor-v043-c2-detached-retry-10`;
- focused transaction
  `C:\Users\young\AppData\Local\Temp\coauthor-v043-qualification-20260805-attempt-024`;
- manifest-generation transaction
  `C:\Users\young\AppData\Local\Temp\coauthor-v043-qualification-20260805-attempt-025`;
- final clean replay worktree
  `B:\Agents\.coauthor-v043-c2-detached-retry-11`;
- its Git-managed admin subtree
  `B:\Agents\platform\co-author-harness\.git\worktrees\-coauthor-v043-c2-detached-retry-11`;
- final clean replay transaction
  `C:\Users\young\AppData\Local\Temp\coauthor-v043-qualification-20260805-attempt-026`.

Each fresh path must be proved absent before creation. A different canonical
Git admin ID is a stop. Git may create/remove only the exact registered
worktree and corresponding admin subtree. Transaction roots remain preserved
after finalization. Worktree removal happens only after all necessary evidence
is captured and verified.

This durable-path ledger does not prohibit process-owned, package-independent,
self-cleaning scratch beneath the operating-system temporary directory that the
already-frozen fixture corpus creates through `tempfile` or equivalent runtime
APIs. Such scratch remains ephemeral rather than evidence, may not target any
governed root, and must leave zero residual paths when the applicable child
exits. Attempt 024's focused scratch uses the source-defined
`release-controller-smoke-*` prefix. Any durable scratch, governed-root scratch,
unexpected prefix/output classification, or residual temp path is a stop.

## Frozen launcher and isolation contract

All three launches use exact interpreter
`C:\Users\young\AppData\Local\Python\pythoncore-3.14-64\python.exe` with `-B`
for both controller and child. `PYTHONUTF8`, `PYTHONPATH`, `PYTHONHOME`,
`PYTHONWARNINGS`, and `PYTHONOPTIMIZE` must be absent before launch. Every
launch passes `--allow-user-site`, no `--ignored-output`, the primary checkout
as the sole `--input-root`, the exact primary `.git\HEAD` and
`.git\refs\heads\main`, and the applicable detached admin `HEAD`, `index`,
`commondir`, and `gitdir` as six explicit `--input` values. The applicable
detached worktree is the sole `--watch-root`.

Every detached status observation uses only:

```text
git --no-optional-locks -C <exact-worktree> status --porcelain=v1 --untracked-files=all
```

The detached index byte length and SHA-256 are recorded immediately before and
after. Any index change is a stop.

Attempt 024 is a focused diagnostic only, with no allowed output:

```text
<python> -B <retry-10>\scripts\release_qualification_controller.py start
  --run-root C:\Users\young\AppData\Local\Temp
  --run-id coauthor-v043-qualification-20260805-attempt-024
  --cwd <retry-10>
  --input-root B:\Agents\platform\co-author-harness
  --input <primary-.git-HEAD> --input <primary-main-ref>
  --input <retry-10-admin-HEAD> --input <retry-10-admin-index>
  --input <retry-10-admin-commondir> --input <retry-10-admin-gitdir>
  --watch-root <retry-10> --allow-user-site --
  <python> -B <retry-10>\scripts\release_qualification_controller_smoketest.py
  --fixture-owner
```

It must terminally succeed with child exit 0, empty stderr, stable inputs,
zero output changes, clean no-optional-locks status, unchanged index, exact
fixture-owner PASS output, and zero surviving owned processes. Any other result
is red and stops before attempt 025. A focused pass is diagnostic only; it does
not qualify the source or erase attempt 023.

For attempt 024, the shared runner lock must be 65 bytes at SHA-256
`24f866592b176429714bb136f0d8adc7ad8574f499ed5ba7f34fb8a92d00c0ab`
both immediately before launch and after terminal finalization. Its raw bytes
must remain the attempt-023 dead-PID value above. The child stdout must contain
exactly this source-defined line plus its terminal newline and no other bytes:

```text
release_qualification_controller_smoketest: PASS (53 behavioral cases; 9 platform skips; posix_evidence=not-run; mode=fixture-owner)
```

The receipt, child stdout, child stderr, worker stdout, and worker stderr must
each be bound by path, byte length, and SHA-256. Child stderr and both worker
streams must be zero bytes at SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

Only after attempt 024 passes, attempt 025 repeats the parent attempt-022
manifest-generating topology at retry-10/addendum HEAD. Its sole allowed output
is `<retry-10>\docs\analysis\generated\fixture_manifest.json`; its child is:

```text
<python> -B <retry-10>\scripts\analysis\fixture_runner.py
  --tier full --cache-mode off
```

Attempt 025 must terminally succeed with 93/93 suites, 97/97 cases, no warning
rows, stable tested inputs and explicit inputs, exactly the registered manifest
changed, unchanged detached index under no-optional-locks status, a separately
bound runner-lock transition, and zero surviving owned processes. Its receipt,
child stdout, child stderr, worker stdout, and worker stderr must each be bound
by path, byte length, and SHA-256. Child stderr and both worker streams must be
zero bytes at the empty SHA-256 above. Only then may its exact manifest replace
the primary manifest and be committed alone on `main` after byte equality is
proved.

After the manifest-only commit and complete attempt-024/025 evidence capture,
force-remove dirty retry-10 and its exact admin subtree. Create retry-11
detached at the manifest commit. Attempt 026 repeats the same topology with
retry-11 substitutions, no `--allowed-output`, and child:

```text
<python> -B <retry-11>\scripts\analysis\fixture_runner.py
  --tier full --cache-mode off --no-write
```

Attempt 026 must terminally succeed with the same 93/93 and 97/97 requirements,
empty stderr, no output changes, stable tested and explicit inputs, clean
no-optional-locks status, unchanged index, a bound runner-lock transition, and
zero surviving owned processes. Its receipt, child stdout, child stderr, worker
stdout, and worker stderr must each be bound by path, byte length, and SHA-256;
child stderr and both worker streams must be zero bytes at the empty SHA-256
above. Any mismatch, warning, additional output,
ambiguous receipt, source drift, process residue, index rewrite, or unlisted
path is red and stops.

## Exact execution sequence

1. Obtain three independent B0/M0/m0 reviews of these exact approved bytes.
2. Revalidate the frozen main/retry-9/attempt-023/lock state, stage only this
   file, and commit it alone on `main`. Record the addendum commit SHA, tree,
   sole changed path, and clean primary status.
3. Revalidate retry-9 with no-optional-locks status and unchanged index; remove
   the clean retry-9 through `git worktree remove`; prove its exact worktree and
   admin subtree absent while preserving attempt 023.
4. Create retry-10 with `git worktree add --detach` at the exact recorded
   addendum commit SHA. Require its detached HEAD and tree to equal that commit
   and tree; bind its canonical admin path and exact `HEAD`, `index`,
   `commondir`, and `gitdir` bytes; prove clean no-optional-locks status and
   unchanged index; then complete the frozen environment/input/lock/path
   preflight.
5. Run attempt 024 exactly as specified. If and only if every focused gate
   passes, revalidate all bindings and proceed to attempt 025 at the same exact
   retry-10/addendum commit subject.
6. If and only if attempt 025 passes every gate, bind its manifest, copy exactly
   those bytes to primary, prove equality, and commit only the primary manifest.
   Capture all retry-10 evidence, then force-remove dirty retry-10 and prove its
   worktree/admin paths absent.
7. Create retry-11 with `git worktree add --detach` at the exact manifest commit
   SHA. Bind its HEAD, tree, canonical admin path, four admin input files, clean
   no-optional-locks status, unchanged index, environment, primary refs, sole
   input root, lock, and transient-path preflight before attempt 026.
8. Run attempt 026 exactly as specified. Only after every gate passes may the
   five C2 evidence paths be updated, independently reviewed, and committed
   alone. Then remove clean retry-11 and prove its worktree/admin paths absent.

## Evidence, review, and downstream stop

Only after attempts 024, 025, and 026 satisfy every requirement may the five
registered C2 evidence paths be updated. They must preserve attempts 017, 019,
and 023 as red evidence; preserve attempt 021 as historical successful evidence
with its later observer effect; distinguish attempt 022's earlier manifest
generation from the current attempt-025 generation; and bind the exact
attempt-024/025/026 receipts, outputs, source commits, manifests, tested-input
digests, Git inputs, indices, status results, process results, and claim limits.

Three independent exact-byte reviews must return B0/M0/m0 before the C2 evidence
paths are committed on `main`. C2 success, if reached, authorizes only the next
pre-existing v0.43 C0 gate. Gate 6 remains closed absent a separately governed
v0.43 consumer receipt. This task may not author or simulate that receipt.
ZIP/cache work, package clearance, push/tag/assets, shipment, fresh-host
qualification, research mutation, and activation remain closed.
