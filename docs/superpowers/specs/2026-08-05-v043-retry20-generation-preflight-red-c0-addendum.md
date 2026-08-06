# v0.43 retry-20 generation preflight RED - C0 successor addendum

Status: proposed corrected exact C0 authority; non-operative until exact-byte
review and the isolated correction commit described below. Its predecessor
bytes remain preserved at commit `e936fc0c0f21fa10bb7f25b04c64860268e6dd05`,
but the population inconsistency registered below stops execution under those
bytes. Date: 2026-08-05 America/Toronto
(`2026-08-06` UTC at the incident). Run scope: `full_lifecycle`, limited to
v0.43 source qualification and its source-local evidence.

## Governing chain and precedence

This addendum is subordinate to the finalized research-governance chain and
narrows, rather than replaces, the committed parent C0:

- `B:\Agents\research\10_Governance\MASTER_GOVERNANCE.md`, Master Governance
  v1.0.9, 77,262 bytes, SHA-256
  `a55b56eee7d72b4aa8a7f2376cb023d987ee7c12e71611fef7a9b457d780e191`;
- its effective amendment, 12,436 bytes, SHA-256
  `201d9b68e9c050f0f1e937977833868dd8ec2e3c5d6395f044fc00103fc95afe`;
- its effective anchor, 1,114 bytes, SHA-256
  `7ae758e443f4360e9738094e6fd1080022b30fa60f8807d0baa1cf0640fb7ebc`,
  effective `2026-08-04T20:00:35.9192246-04:00`;
- finalized Overseer doctrine, 5,829 bytes, SHA-256
  `90edcde87d2ed36641a911265179eb0203165e701a48395fd49b201c0379e7b9`;
- Overseer status `clear`, 773 bytes, SHA-256
  `b6b2fddedf9f364308dd6d54375c4d3a58595c3b7f9ed332453605373d9f00f9`;
- `docs/superpowers/specs/2026-08-05-v043-c0-stop-prospective-source-requalification-c0-addendum.md`,
  46,890 bytes, SHA-256
  `086b0769e70ef2015cf751d503c74ca11fefb16e7ebe96c79719f9b824d20deb`,
  committed alone as `c9379ce5f79ccd07ddac0d050d34bcebbf7f4201`.

The rejected Master Governance v1.0.10 candidate has no authority. If any
binding above is absent, draft, ambiguous, inconsistent, superseded, or in
conflict, this addendum fails closed. Parent-C0 requirements continue except
where this document expressly replaces the stopped retry/attempt labels,
capture-file set, publication primitive, and post-RED sequence.

## Plane separation and claim ceiling

Source, Git/admin, startup catalog, CLI registration, archive, package,
cache/provenance, loaded paths, consumer evidence, shipment, host
qualification, research, and activation remain separate planes. This addendum
authorizes no push, tag, install, cache/catalog mutation, research mutation,
distributable/package archive creation, shipment, host qualification, or
activation. The exact local failed-script evidence duplicate below is the sole
non-distributable evidence-copy exception; it is not a package or archive
plane.

Gate 6 remains closed. No independently governed v0.43 consumer receipt is
present, and this source task may neither author nor simulate one. Even a fully
green source sequence below proves only source qualification. It is not
consumer compatibility, package clearance, shipment authorization, installed
provenance, startup-catalog registration, loaded-path identity, host
qualification, research acceptance, or activation.

## Registered stopped cohort and immutable evidence

The exact reviewed capture candidate
`releases/verification/v0.43.0/C2/C2_STRUCTURAL_CAPTURE.ps1` was 196,535 bytes,
2,913 lines, SHA-256
`c57bfe601a4f24005139ab1b161cbdd15bf8af047eebba847171e0c37feec517`.
Its `generation-structural` mode ran once against detached retry-20 and exited
1. It executed no structural suite. The durable local capsule
`releases/verification/v0.43.0/C2/C2_STRUCTURAL_GENERATION_CAPSULE.json` is
2,690,757 bytes, SHA-256
`af0a247a329439c12b50138dcb021f3a25f743b3aab08d30b41b30ffb670e1ea`.
It began `2026-08-06T01:36:05.6698654Z`, ended
`2026-08-06T01:36:44.7934801Z`, and is RED with exactly these two recorded
errors:

1. at `2026-08-06T01:36:37.6926246Z`, phase `preflight`, code `UNHANDLED`,
   detail `The property 'Count' cannot be found on this object. Verify that the
   property exists.`;
2. code `CAPSULE-PUBLICATION-PENDING`, detail `durable initial RED capsule;
   final verdict has not yet been atomically published`, UTC
   `2026-08-06T01:36:44.7809607Z`.

The capsule contains 16 read-only Git-probe spawn records, zero state-capture
attempts, zero watcher events, no readiness state, no structural result, no
bracketed red post-state, and no PASS. Its preimage binds main and retry-20 at
`c9379ce5f79ccd07ddac0d050d34bcebbf7f4201`; retry-20 had 930 identities,
10,830,011 file bytes, a 102,761-byte inventory, and inventory SHA-256
`fcf98c585705c90a59de0bb4012c14dd0e5583db8287e2705538fff6f2f61baf`.
The retry-20 admin index is now 95,695 bytes at SHA-256
`26b5855e3029cd0a56a16d2309171873144b223d3b4c737ab525f90bb1f6955c`;
its semantic stage/flags and worktree remain clean and detached at the C0
commit. Raw-index transition is only captured evidence and is not a pass.

The shared `B:\Agents\platform\co-author-harness\.git\coauthor-fixture-runner.lock`
remains the exact 66-byte stale retry-19 lock at SHA-256
`146809515519be1654ae43d9f21916d10a8558ab4c1005650dd84beb160986a0`,
raw UTF-8 `pid=43052 worktree=B:\Agents\.coauthor-v043-c2-detached-retry-19\r\n`;
PID 43052 is dead and exclusive open succeeds. The generation temp root and
attempt-035/036 roots are absent. Retry-21 was never created. Related live
process count is zero. Both primary and retry-20 manifests remain 54,255 bytes
at SHA-256
`c0421d9b1e3dac989bebd8bc11f702f3260ac5b695e08ed90efd5311827f4950`.

Two same-directory publication remnants are also immutable RED evidence:

- `C2_STRUCTURAL_GENERATION_CAPSULE.json.e44091d0-64c0-4d12-959c-7639e4defdc8.tmp`,
  2,690,787 bytes, SHA-256
  `27b44c3d31327d75d8a6488f6748e5ef0bfc381efe3360ce73bd4824bb9d4ac7`,
  valid RED JSON with the `UNHANDLED` error and the exact
  `CAPSULE-PUBLICATION` illegal-path failure; and
- `C2_STRUCTURAL_GENERATION_CAPSULE.json.f9108673-5eae-42ad-b8aa-a50406195f5b.tmp`,
  2,690,589 bytes, SHA-256
  `ed66e19c2846418ac8c32fdfbf58787188a4bf03d09807e44c574b6ee55032dd`,
  valid RED JSON with the original `UNHANDLED` error.

Each remnant binds the same 16 spawns and has zero state attempts, watcher
events, or markers; null result/readiness/bracketed-red state; and no PASS.
They are the only surviving bytes that record the failed final-publication
progression. They join the named RED capsule and failed-script preimage as
permanent local evidence. None may be cleaned as an atomic temporary sibling.

Retry-20 is consumed by this RED and must never be reused. Retry-21 and attempts
035/036 are retired absent because their predecessor gate failed. The failed
script bytes, RED capsule, and both registered publication remnants are
immutable historical evidence and may never be deleted, overwritten,
relabeled, terminalized, or described as a completed publication,
qualification pass, or terminal transaction.

## Successor writable and transient ledger

This section expressly supersedes the complete parent-C0 `Exact writable and
transient ledger` section, lines 246-510, for all work after
this successor's isolated commit. No old prospective retry-20/21,
attempt-035/036, ten-file, or unnamed atomic-sibling row remains executable.
The sole persistent paths permitted to change, in the sequence below, are:

1. primary Git objects, `refs/heads/main`, `.git/logs/HEAD`,
   `.git/logs/refs/heads/main`, primary index, and `.git/COMMIT_EDITMSG` for
   exactly this addendum-only commit and the later manifest-only commit;
2. retry-20 worktree/admin removal through Git worktree management;
3. the ignored/local working candidate
   `releases/verification/v0.43.0/C2/C2_STRUCTURAL_CAPTURE.ps1`;
4. fresh retry-22 and retry-23 worktree/admin paths, including only each admin
   `index` as an equality or stat-cache-only transition;
5. the shared `.git/coauthor-fixture-runner.lock`, only at the exact deletion,
   creation/metadata, and final deletion points below;
6. exact fresh attempt-037 and attempt-038 transaction directories;
7. only retry-22's `docs/analysis/generated/fixture_manifest.json`, its exact
   writer sibling
   `fixture_manifest.<attempt-037-manifest-run-id-UUID>.tmp`, and then the
   primary manifest through the manifest-only commit;
8. exactly four fresh terminal C2 targets:
   `C2_STRUCTURAL_GENERATION_RETRY22_CAPSULE.json`,
   `C2_ATTEMPT_037_CAPSULE.json`,
   `C2_STRUCTURAL_REPLAY_RETRY23_CAPSULE.json`, and
   `C2_ATTEMPT_038_CAPSULE.json`;
9. exactly four provisional publication preimages, one per fresh target,
    named by appending `.publication-preimage.json`, preserved on any RED and
    otherwise retained through all three pre-cleanup live-state reviews;
10. retry-22/retry-23 worktree/admin removal, the four exact provisional
    publication-preimage deletions, and final shared-runner-lock deletion only
    after the live-state reviews approve; and
11. only after cleanup postflight, the five existing C2 records
    `C2_SOURCE_QUALIFICATION.md`, `C2_STRUCTURAL_RESULTS.json`,
    `C2_REGISTRY_RESULTS.json`, `C2_DETACHED_REPLAY.json`, and
    `C2_READ_ONLY_REVIEW.md`.

Permitted transient paths are closed to: same-directory capsule siblings named
exactly `<fresh-target>.<lowercase-GUID>.tmp` for initial and final publication;
controller-published transaction temporary siblings; primary `.git/index.lock`
during each exact commit workflow; retry admin `index.lock`; ordinary Git
object/ref locks and temporary objects for those commits/worktree operations;
controller/fixture-runner OS lock primitives; the exact manifest writer sibling
above; the four exact mode temp roots named below; the exact parent-C0
provenance and FIC capability roots and their already closed child patterns;
and the inherited 17 retry-root rows after substituting retry-22/23. No
registered failed `.tmp` evidence file is transient. Attempt-mode temp roots
are exactly the attempt transaction names plus `-transients`. Green removes
only an empty owned capability root; RED preserves every nonempty residue.

Every other parent-C0 restriction remains binding. The five frozen C2 records
are read-only except at the one expressly ordered update point above. The three
registered RED JSON files, failed-script evidence duplicate, FIC, Aug-3
residue, and old transactions are unconditionally read-only. Cache/catalog,
archive/package, research, host, and activation planes are also
unconditionally read-only.

## Exact defect and bounded repair

The preflight defect is Windows PowerShell 5.1 pipeline unrolling under strict
mode. `Get-DirtyStatusLines` has seven invocations across six source lines. Six
unsafe invocations across five source lines dereference an unwrapped zero- or
singleton result: lines 1285, 1286, 1293, both invocations on line 1682, and
line 2562 of the failed candidate. The seventh invocation, on line 1683, is
already wrapped in `@(...)` and must remain wrapped.
The repaired candidate must wrap every call result with `@(...)` before count
or indexing, including primary/retry clean checks, ignored-state checks,
prior-state clean boundaries, and attempt-output cardinality. Reviewers must
search the complete script for every other function whose caller assumes array
identity and reject any remaining zero/singleton unrolling hazard.

The publication defect is the Windows PowerShell 5.1/.NET Framework rejection
of `[IO.File]::Replace($temp, $Target, $null)`. The repaired candidate must use
a same-directory legal backup path named exactly
`<target>.publication-preimage.json`. Before initial publication it must prove
the target, temporary file, and backup path absent. It first move-publishes the
durable initial RED target. Final RED or PASS publication must call
`[IO.File]::Replace($temp, $Target, $backup)` exactly once. The backup thereby
preserves the initial RED publication. For PASS, that replacement remains the
last fallible operation; there is no target read, verification, deletion, or
other operation after it. A successful mode exits zero. For RED, both target
and backup are preserved and the sequence stops. A failed replacement leaves
all extant bytes untouched and stops.

Under the `e936fc0c0f21fa10bb7f25b04c64860268e6dd05` predecessor authority,
the failed candidate was already duplicated byte-for-byte through the local
patch mechanism as
`releases/verification/v0.43.0/C2/C2_STRUCTURAL_CAPTURE_RETRY20_FAILED_PREIMAGE.ps1`.
The live duplicate is 196,535 bytes at SHA-256
`c57bfe601a4f24005139ab1b161cbdd15bf8af047eebba847171e0c37feec517`
and its creation is a completed historical fact, not prospective authority.
It must be rebound read-only and byte-equal before the working candidate may
change; recreation, replacement, or overwrite is forbidden. The RED capsule,
both registered RED remnants, evidence duplicate, and all pre-existing C2 files remain
ignored/local and must never be staged,
force-added, or committed.

## Rejected repaired candidate and population correction

The first repaired working candidate was 207,598 bytes at SHA-256
`2f345413b765740bc8bdb659226bd98cb28e325a9777d1bb693e2f0cbfb0fff3`.
It parsed under Windows PowerShell 5.1 with zero errors but was rejected
`B2/M0/m0` before execution. It was never run. Preserve that exact review fact;
the working candidate may change under this corrected authority.

Blocker one was publication control. The final RED branch performed fallible
target verification after replacement, and the outer catch could call the
replacement path again. The corrected working candidate must set a
replacement-attempt guard immediately before `File.Replace`, call
`File.Replace` exactly once, and return immediately after that call for both
RED and PASS. The outer publication catch must never republish after initial
publication or after replacement begins. A failed replacement records the
console/error outcome in the invoking process, leaves all extant target,
temporary, and sidecar bytes untouched, and stops.

Blocker two was the tested-population count inherited from the parent C0. At
commit `e936fc0c0f21fa10bb7f25b04c64860268e6dd05`, `git ls-tree -r HEAD
--name-only` contains exactly 756 tracked paths. The governed clean-filter
enumeration excludes zero `.plugin`/`.zip` paths, exactly six paths beneath
`scripts/analysis/`, and exactly
`docs/analysis/generated/fixture_manifest.json`, leaving exactly 749 included
paths. Their Python-Unicode-sorted LF payload without terminal LF is 39,100
bytes at SHA-256
`2be399ca20c686a511a9cf4767cd572532fc948bd6c0a576bdbee2fcd5479474`.
The path-plus-clean-filter-object canonical digest is
`2262c6fc5b073fdca3c8a03b74d5ed867272f26064d8761dc06f25e8ff7bfafa`;
the path-plus-checkout-raw-SHA-256 digest is
`e42d83dd295c4dc4b8a30f808b1904e9125ce7fe59b5254ef7bb63009dc4d244`.
All 749 `git hash-object --stdin-paths` rows were returned with zero stderr.

This correction modifies the existing successor-C0 path rather than adding a
new tracked path, so the correction commit must still contain exactly 756
tracked paths and reproduce the same exclusion cardinalities and 749 included
paths. Its C0 blob change will legitimately change the two content digests;
the repaired capture script and eventual receipt must compute and bind those
fresh digests rather than reuse the diagnostic digests above. The exact
qualification population requirement is therefore 749, superseding every
parent or predecessor reference to 748. Any other count is RED. No manifest,
retry, attempt, C2, lock, package, or other plane may change in the correction
commit.

The repaired script stays at
`releases/verification/v0.43.0/C2/C2_STRUCTURAL_CAPTURE.ps1`; it must bind this
addendum's isolated commit and exact bytes. Its fresh labels are:

- generation worktree retry-22, temp root
  `C:\Users\young\AppData\Local\Temp\coauthor-v043-structural-20260805-retry-22-transients`,
  capsule `C2_STRUCTURAL_GENERATION_RETRY22_CAPSULE.json`;
- generation attempt 037, transaction
  `C:\Users\young\AppData\Local\Temp\coauthor-v043-qualification-20260805-attempt-037`,
  temp root with the same name plus `-transients`, capsule
  `C2_ATTEMPT_037_CAPSULE.json`;
- replay worktree retry-23, temp root
  `C:\Users\young\AppData\Local\Temp\coauthor-v043-structural-20260805-retry-23-transients`,
  capsule `C2_STRUCTURAL_REPLAY_RETRY23_CAPSULE.json`;
- no-write attempt 038, transaction
  `C:\Users\young\AppData\Local\Temp\coauthor-v043-qualification-20260805-attempt-038`,
  temp root with the same name plus `-transients`, capsule
  `C2_ATTEMPT_038_CAPSULE.json`.

All hard-coded retry20/21 and attempt035/036 prospective bindings in the
working candidate must become retry22/23 and attempt037/038. Historical
retry-20/21 and attempt-035/036 identifiers remain only in a dedicated
preserved-predecessor binding for the immutable RED capsule and failed-script
evidence duplicate and may not
be accepted as a green prior capsule. The candidate must validate the failed
capsule's exact bytes, top-level RED state, exact two errors, script binding,
preimage bindings, 16-spawn Git multiset, absence of readiness/result/events,
and live preservation before setup. It must not embed the 2.69 MB predecessor
recursively in each new capsule; an exact path/length/SHA and semantic validation
record is sufficient.

All parent-C0 watcher, process-trace, fixed-point, raw-stream, exact command,
17 retry-route, provenance, FIC, environment, topology, manifest, transaction,
and claim-limit requirements remain binding with only the fresh label
substitutions above. Both PowerShell parsers must report zero errors. Three
independent reviewers must approve the repaired exact bytes B0/M0/m0 before
execution. Any byte change invalidates all reviews.

## Authorized successor sequence

1. Obtain three independent exact-byte B0/M0/m0 reviews of this corrected
   addendum. Repair and re-review any finding. Commit only this same addendum
   path on clean main; bind commit, tree, parent, file bytes, SHA-256, exactly
   756 tracked paths, the exact exclusion cardinalities, and 749 included
   population paths. No C2 file is committed.
2. Rebind the existing failed-script evidence duplicate read-only and prove its
   exact byte equality. Repair only the rejected 207,598-byte ignored/local
   working capture script as specified. Obtain three
   independent exact-byte B0/M0/m0 script reviews, including fresh closure of
   all 93 suites/97 cases, 17 retry routes, helpers, publication sidecars,
   watchers, process trace, label substitution, and preserved RED semantics.
3. Rebind retry-20/admin, the RED capsule and failed-script evidence duplicate,
   stale lock, main, manifests,
   C2, frozen FIC/residue, temp/attempt absence, and zero related process.
   Force-remove only retry-20/admin through Git worktree management. Prove
   absence and all other planes unchanged. Retry-21 requires no removal because
   it is absent.
4. Create retry-22 detached at the exact addendum commit and repeat the full
   parent-C0 preflight. Run repaired `generation-structural`. It executes the
   same exact 15 structural commands and requires the same streams, counts,
   hashes, index semantics, clean state, stale-lock equality, transient
   closure, and zero-process postflight as parent step 5. Preserve its
   publication-preimage sidecar.
5. Only after a PASS generation capsule, delete the exact stale retry-19 runner
   lock and prove absence. Run attempt 037 with the parent step-6 controller
   command after substituting retry-22/attempt-037 paths and labels. Require the
   complete terminal succeeded receipt, exact 93/97 evidence, manifest-only
   retry change, transaction/stream closure, dead PIDs, and zero live process.
   A red or incomplete attempt stops and preserves all evidence.
6. After attempt 037 PASS, copy only its exact generated manifest bytes to the
   primary manifest through the patch mechanism, stage only that file, and
   commit it alone on main. Bind pre/post index and commit/tree/parent. Any
   other diff stops. Preserve retry-22 and attempt 037.
7. Create retry-23 detached at the exact manifest commit. Run the same 15-command
   structural replay and then attempt 038 with the parent step-10 command after
   substituting retry-23/attempt-038. Require no-write equality, population and
   case-order identity with attempt 037, terminal transaction evidence, clean
   retry state, exact lock semantics, transient closure, and zero process.
8. After all four fresh modes PASS, freeze the four terminal capsules, their
   four publication-preimage sidecars, the failed RED capsule and failed-script
   evidence duplicate, both
   worktrees/admin paths, both transaction directories, runner lock, main,
   manifests, FIC/residue, and process census. Obtain three independent
   pre-cleanup live-state B0/M0/m0 reviews. Those reviews also bind both
   registered retry-20 publication remnants. Any finding stops before cleanup.
9. Only after those approvals, delete the four exact publication-preimage
   sidecars, force-remove only retry-22/retry-23 and admins, and delete only the
   exact final shared runner lock. Prove all named cleanup targets absent and
   every preserved evidence plane unchanged.
10. Update the five existing C2 records and retain nine additional local
    evidence files: the failed-script evidence duplicate, failed RED capsule,
    both registered RED publication remnants, repaired capture script, and four
    terminal capsules. The final ignored/local C2 review set is therefore
    exactly fourteen files. It must preserve every historical red, refusal,
    interruption, and success required by the parent C0; register this cohort;
    bind all exact bytes, reviews, commits, receipts, streams, transactions,
    inventories, locks, and cleanup absences; and state the source-only claim
    ceiling. Obtain three independent exact-byte B0/M0/m0 reviews of all fourteen
    files. Never stage, force-add, or commit them.

Any failure at any step is RED and stops that sequence. No cleanup of nonempty
failure residue, no label reuse, no recovery/cancel/ordinary-status controller
subcommand, and no advancement by inference is authorized.

## Downstream limit

Successful completion closes only v0.43 source qualification under the exact
reviewed evidence. Gate 6 still stops the run until an independently governed
consumer supplies exact v0.43 consumer evidence through its own authority.
Only that independent evidence may open later package/shipment consideration;
it does not itself authorize package creation, shipping, installation,
catalog/cache mutation, host qualification, research mutation, or activation.
