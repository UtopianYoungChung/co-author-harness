# v0.43 retry-24 process-trace access denial - C0 successor addendum

Status: proposed successor C0; non-operative until three independent exact-byte
B0/M0/m0 reviews and the isolated commit required below.
Date: 2026-08-05 America/Toronto (`2026-08-06` UTC at the incident).
Run scope: `full_lifecycle`, limited to v0.43 source qualification and its
source-local evidence.

## Governing chain and precedence

This instrument is subordinate to the finalized research-governance chain and
narrows the stopped source-qualification path:

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
  committed alone as `c9379ce5f79ccd07ddac0d050d34bcebbf7f4201`; and
- `docs/superpowers/specs/2026-08-05-v043-retry20-generation-preflight-red-c0-addendum.md`,
  committed alone at `88698ead0d39fe73c05d57c8c8165fdb497999ee`,
  53,293 bytes, SHA-256
  `662c03c4f37ef63bcac2eabd5fb8e315048228adb234a4ef56ec0c8aa668d6fa`.

The rejected Master Governance v1.0.10 candidate has no authority. If a binding
above is absent, draft, ambiguous, inconsistent, superseded, or conflicting,
this instrument fails closed. Parent requirements continue except where this
later instrument expressly replaces the consumed labels, WMI process-start
observation, capture-script path, population count, writable ledger, sequence,
or final C2 cardinality.

## Plane separation and claim ceiling

Source, primary Git/admin, startup catalog, CLI registration, archive/package,
installed cache/provenance, loaded paths, consumer evidence, shipment, host
qualification, research, and activation remain separate planes. This
instrument grants write authority only to the exact source-local and Git paths
enumerated below. It grants no push, tag, install, catalog/cache mutation,
archive/package creation, shipment, consumer attestation, research mutation,
host qualification, or activation.

Gate 6 remains closed. A green sequence below would establish only source
qualification. It cannot author, simulate, infer, or replace independently
governed v0.43 consumer evidence.

## Registered retry-24 terminal RED

After the predecessor C0 and capture candidate received three independent
exact-byte B0/M0/m0 reviews, the candidate was bound at 225,369 bytes, 3,246 LF
terminators, zero CRLF, terminal LF, and SHA-256
`31acaf22240be68a4243d1199ba55aeef0dac68f6d5e3758f8fa5dd28d83a6cb`.
Both the current host and a fresh `powershell.exe` child parsed the exact bytes
under Windows PowerShell 5.1 Desktop `5.1.26100.8875` as 36,319 tokens with zero
errors. Main was clean at the predecessor commit and tree
`de6682bc6da3e0de39e4ff12a685efc9ba584d46`; the reviewed pre-removal rebind
covered all fifteen C2 files, consumed retry-22/admin, the stale lock,
manifests, FIC, frozen residue, fresh-path absences, and zero related process.
Only retry-22/admin was then force-removed. Retry-24 was created clean and
detached at the predecessor commit.

The reviewed script ran `generation-structural` exactly once on retry-24. It
terminally published:

- `releases/verification/v0.43.0/C2/C2_STRUCTURAL_GENERATION_RETRY24_CAPSULE.json`,
  2,704,547 bytes, LF-only with terminal LF, SHA-256
  `91569a3b1b64832b83ff286d09e5eff04d191787feec5d913a678ca023758ad4`;
  started `2026-08-06T03:48:21.3202287Z`, ended
  `2026-08-06T03:49:37.2941657Z`, verdict RED, with exactly one error at
  `2026-08-06T03:49:27.1156471Z`, phase `preflight`, code `UNHANDLED`, and exact
  detail `Access denied `; and
- `C2_STRUCTURAL_GENERATION_RETRY24_CAPSULE.json.publication-preimage.json`,
  2,704,715 bytes, LF-only with terminal LF, SHA-256
  `51c014eb6ba511c839736bbb95bd48a5c991259b895b9053f540bceb96eac172`;
  ended `2026-08-06T03:49:37.0297841Z`, containing the same error plus the exact
  `CAPSULE-PUBLICATION-PENDING` marker at
  `2026-08-06T03:49:37.0127827Z`.

Normalizing only the target's top-level `ended_utc` and `errors` to the
publication-preimage values yields canonical SHA-256
`e806448ecc9d30fbad380016b1b1cd913a1c74cb1e77c276f307bf05d793425c`,
identical to the publication preimage's canonical hash. Both files bind the
predecessor C0 and reviewed script exactly.

The pair contains a complete pre-state, 16 successful read-only Git probes,
and exactly nine first-attempt successful `preflight_read_evidence` rows for
the authority, five frozen C2 records, primary HEAD/ref, and retry-24 admin
HEAD. It contains no typed preflight-read or assertion error, readiness state,
result, structural suite, qualification transaction, watcher, readiness
marker, state-capture attempt, governed launch, observed process, process-trace
root, or process-trace event. The trace source is null, inactive, and unclosed.

The last governed byte read completed at
`2026-08-06T03:49:27.0124313Z`, 103.2158 milliseconds before the error. Source
order proves commit-topology returned; otherwise its boundary would have added
a typed error. The conservative failing interval is the generation-only
consumed-root absence test followed by `Start-ProcessStartTrace`; the first
external operation there is
`Register-WmiEvent -Class Win32_ProcessStartTrace`. The timing, exact access
message, and null trace state strongly localize the denial to registration, but
the capsule did not record exception type/HResult or a pre-call marker. The
particular denied provider/object must not be invented.

Retry-24 is consumed and preserved. Retry-25 and attempts 039/040, including
their transaction and transient labels, are retired absent because their
predecessor gates never opened. No file in this RED pair is a suite result,
qualification receipt, consumer evidence, or success.

## Frozen live state

At successor drafting:

- main is tracked-clean at `88698ead0d39fe73c05d57c8c8165fdb497999ee`
  and tree `de6682bc6da3e0de39e4ff12a685efc9ba584d46`;
- retry-24 is clean/detached at the same commit/tree, with 931 identities
  (174 directories, 757 files), 10,883,304 file bytes, 102,921 inventory bytes,
  and inventory SHA-256
  `94868c072252aad409d4263e9d34081bc7181a5f718ad3cc1840fee17e579726`;
- retry-24 admin has eight identities (two directories, six files), 96,123
  file bytes, 493 inventory bytes, inventory SHA-256
  `f41576f1268e85efc2da26d90e3a75c1f1292a46f97378d9faa463bf664fb070`,
  a 95,847-byte index at SHA-256
  `9969c7c3502781b763f744ed2fdbb2ea7c9f9d1d87d6965273669088bf742f37`,
  and absent `index.lock`;
- primary and retry-24 manifests are each 54,255 bytes at SHA-256
  `c0421d9b1e3dac989bebd8bc11f702f3260ac5b695e08ed90efd5311827f4950`;
- the stale retry-19 lock remains 66 bytes at SHA-256
  `146809515519be1654ae43d9f21916d10a8558ab4c1005650dd84beb160986a0`;
  PID 43052 is dead and exclusive open succeeds;
- FIC remains 5,097 identities, 67,092,968 file bytes, 600,192 inventory bytes,
  and SHA-256
  `5d7242130166ab4adfa8743c9256264a2f0d9c108a50c76f117f5c097f5bab9d`;
- the frozen Aug-3 residue remains 114 identities, 34 directories, 80 files,
  zero links, 45,541 file bytes, 8,637 inventory bytes, and SHA-256
  `3bd3e82ea9b0441ffb556aafa67d6a625dc376665889c6cc1bb18de8342e7f40`;
- C2 contains exactly 17 files totaling 19,643,277 bytes; the prior fifteen
  bindings are unchanged and the only additions are the retry-24 RED pair;
- the primary input-root inventory contains 1,879 identities, 315 directories,
  1,564 files, 122,796,765 file bytes, 217,260 inventory bytes, and SHA-256
  `48ecb0189c04f5cf568ebed5e034f2f8ad39ea3ca6106d38800eb0d196517b54`;
  and
- retry-24 mode temp, provenance, RMNC, attempt 039/040, retry-25, and all their
  transients are absent; related processes, event subscribers, and queued trace
  events are zero.

All these bytes and paths remain read-only until a later exact sequence row
expressly permits one change.

## Exact process-ownership replacement

WMI process-start observation is not retried and is superseded only for the
fresh modes below. Polling alone is not equivalent and cannot justify a tree-
closure claim. Fresh structural commands instead use the tracked supervisor
`scripts/analysis/fixture_process_supervisor.py`, currently 80,213 bytes at
SHA-256 `4fb7c90cb43eb77d2303b2ff65cfa52d514dc37badfa2aa140bef8216618e1f1`.
Its Windows `run_owned` path creates the exact target suspended, proves the
requested executable image, assigns and proves membership in a private Job
before resume, sets `KILL_ON_JOB_CLOSE` with no breakaway, applies one tree-
inclusive deadline, requires the direct exit, and requires two consecutive
empty Job membership scans. Any spawn, membership, image, timeout, survivor,
cleanup, stream, or handle ambiguity is RED; there is no unsupervised fallback.

This supervisor may wrap only the fifteen structural commands. It must not wrap
the release controller: the controller's default `run` path intentionally
creates its worker detached, and its own contract refuses that topology when
placed inside a no-breakaway outer Job. Attempt 041/042 controller processes
therefore launch directly on the bare host exactly as before, while the
controller's own worker/product Job, intent/journal/exit/receipt, exact PID
bindings, raw streams, dead terminal PIDs, independent post-state census, and
zero related-process fixed point remain mandatory. Direct controller launch is
not relabeled as supervisor evidence.

The recovery script must contain one fixed inline Python adapter, hash and bind
its exact UTF-8 bytes, and invoke the configured absolute Python with
`-I -S -B` after exact runtime/import compatibility review.
The adapter receives one canonical JSON request through standard input binding
the target argv, cwd, tree-inclusive timeout, exact supervisor path/binding,
and exact ownership-temp capability root. It must read and hash the supervisor
bytes, require the exact binding above, compile/execute only those read bytes in
an isolated module namespace, and call `run_owned` with the adapter's effective
environment. It emits exactly one canonical compact ASCII JSON object followed
by one LF and no stderr. Success contains schema/method, target return code,
base64 target
stdout/stderr, request SHA-256, supervisor binding, runtime binding, and an
explicit tree-closed result. A typed supervisor error contains its exact
code/detail and captured base64 streams and is RED. Any adapter nonzero exit,
stderr byte, malformed/extra stdout, binding mismatch, or missing field is RED.
Supervisor success and target exit zero are separate gates: `run_owned` may
return normally with a nonzero target return code, which remains structural
RED.

The configured runtime is
`C:\Users\young\AppData\Local\Python\pythoncore-3.14-64\python.exe`, Python
`3.14.0rc2`, 105,464 bytes, SHA-256
`ab60df0d679ed8c1150a9fe8ea38b99a2b9838807127f17a166f993bc5403f62`.
Its `Lib\tempfile.py` is 33,852 bytes at SHA-256
`6f1189b884e2cc3b06d3c8796cea60569934a43c51798204e8699b7e90b4ea0d`.
The adapter must rebind both before every structural launch, prove
`TemporaryFile is NamedTemporaryFile`, template `tmp`, and random alphabet
`abcdefghijklmnopqrstuvwxyz0123456789_`, and set `tempfile.tempdir` to the exact
fresh ownership-temp capability root. Target `TEMP`, `TMP`, and `TMPDIR` remain
the separate mode-temp root.

Each successfully entered Windows supervisor invocation creates exactly two
distinct simultaneous direct-child capture files in the ownership-temp root.
Their only admitted leaf grammar is `^tmp[a-z0-9_]{8}$`; only file
create/write/delete events during that exact launch interval are allowed.
Watcher `Changed` notifications may duplicate or coalesce, so no exact event
count is claimed. The closed path/action registry must identify only those two
ordinary-file identities, include their required create/delete lifecycle under
the existing watcher semantics, reject watcher error/overflow and every other
path/type/action, and prove the root empty after return. Fewer identities caused
by setup failure remain RED, not success. After all fifteen structural launches
are green, watcher-quiet post-empty proof precedes exact nonrecursive removal of
the ownership-temp root and parent-watcher deletion proof. A nonempty or
inaccessible root on failure is preserved and never blindly removed.

The top-level `process_start_trace` field is absent from fresh capsules and is
replaced by a tagged-union `process_ownership_evidence`. Structural capsules
use method `windows-suspended-private-job-v1`. Their ordered
`structural_owned_launches` array is the exact actually attempted adapter-launch
prefix, from zero through fifteen records, with no record for an unlaunched
adapter. Each extant record separates adapter process facts from logical target
facts and binds purpose, target argv/cwd/environment, deadline, canonical
request, adapter bytes/hash, Python/tempfile/supervisor bytes/hash, wrapper
PID/exit/raw streams, target exit/raw streams, ownership-temp watcher interval,
and post-empty proof to the extent actually reached. A structural RED publishes
the exact failed/incomplete prefix without synthesizing later fields.
Structural PASS alone requires exactly fifteen successful, tree-closed,
target-exit-zero records and `all_structural_jobs_empty = true`.

Attempt capsules use method `release-controller-owned-transaction-v1`.
`controller_launch` is absent or null only when failure occurs before its launch
boundary; once launch begins it contains exactly one actual record, preserving
the exact reached state without invented terminal fields. Attempt PASS alone
requires that one record to bind the complete terminal transaction and the
controller's own worker/product Job evidence, plus
`controller_transaction_terminal_and_dead = true`; it must not populate or
reuse the structural tree-closed field. Every fresh capsule records the exact
publication-time related-process census and count. Zero related processes is a
PASS requirement only; RED records every survivor and must not synthesize or
erase it. Prior-capsule validation must revalidate every field and exact
predecessor binding. Old WMI fields are predecessor-only and may not be copied,
null-populated, or used as fresh PASS evidence.

The exact controller source is
`scripts/release_qualification_controller.py`, 117,171 bytes at SHA-256
`89458f876beb086e476d22fa3d3a9bee4bc6530a68e049c7541e7623620f3701`.
Attempt success requires terminal receipt state `succeeded`, diagnostic null,
exit zero, `recovered = false`, exact intent/request/journal/exit/stream
bindings, dead controller/worker/product identities and creation tokens, no held
run lock, and the complete post-state gates. Its Job-closure conclusion is an
exact-code/terminal-projection inference, not a raw membership log or WMI event
claim.

Structural target deadlines are exactly 1,800 seconds each. Controller
deadline semantics remain the controller's existing governed transaction
contract; the outer capture imposes no shorter timeout. No host wrapper may
terminate a fresh mode earlier than its own reviewed deadlines.

The structural deadline bounds target tree execution and cleanup, not the
post-closure reread of unbounded capture streams or adapter base64/JSON
serialization; no disk-size quota is inferred. The adapter has no outer
`Process.Kill` watchdog: abrupt death in the suspended-create/pre-Job-assignment
window could strand a suspended process holding inherited temporary handles.
The helper's own finite deadline and fail-closed cleanup remain authoritative;
any outer-host interruption, nested-Job assignment failure, retained handle,
or temp residue is RED with no fallback. Fresh runs bind Windows build
`10.0.26200.8875`; drift requires new review rather than inference.

All predecessor watcher, fixed-point, raw-stream, exact-command, 17 retry-route,
provenance, FIC, environment, topology, manifest, transaction, publication,
and claim-limit checks remain mandatory, plus the ownership-temp route above.

## Recovery-script assembly and repair boundary

The failed reviewed script at
`releases/verification/v0.43.0/C2/C2_STRUCTURAL_CAPTURE.ps1` is now immutable
retry-24 evidence. It must never be edited, deleted, renamed, staged,
force-added, committed, packaged, or executed again. Repair occurs only at the
fresh absent path
`releases/verification/v0.43.0/C2/C2_STRUCTURAL_CAPTURE_RETRY24_RECOVERY.ps1`.

The recovery path is first assembled as an exact copy of the failed script by
`apply_patch` only. The unique 79-byte LF-terminated sentinel is
`# COAUTHOR_RETRY24_RECOVERY_ASSEMBLY_SENTINEL_7A9F6C20D41E4B6A8C3375E9F0124D8B`.
It occurs zero times in the source and registered RED pair. Step 1 requires the
destination absent and add-publishes its chunk plus sentinel. Steps 2-15 replace
the sole exact sentinel with the next chunk plus sentinel. Step 16 replaces the
sole sentinel with its chunk and no sentinel. Before each step the exact prior
state must match; after each step byte length/hash and sentinel cardinality must
match this table:

| Step | Source lines | Chunk bytes | Chunk SHA-256 | State bytes | State SHA-256 | Sentinel |
|---:|---:|---:|---|---:|---|---:|
| 1 | 1-203 | 9,197 | `474ee35335731a902a489e74d20cdd139c03c57f3711a91e6026b7eb22e17f6f` | 9,276 | `c6d0cfee6b5cb1d6a2d399b8c550529488bfb528358b4c9a993302c0e5ca7e21` | 1 |
| 2 | 204-406 | 7,834 | `35f98a419ab1949a0001ca2e3d0c8ad62ccf0b5efff166d0e23d38513b945996` | 17,110 | `f17d15afe8cf3c31e29c8fc70a8a9891e2881b41dfb7918ca6bde233a3d517d6` | 1 |
| 3 | 407-609 | 8,188 | `88fcc27b19d1baf527fe0528581e5e2c9d89580f0a27acd4aa3fea9123e289bd` | 25,298 | `c0fd5de1327beffd5a467f0d7087f0ada294b4154ae092c64a6731d9187ac309` | 1 |
| 4 | 610-812 | 9,716 | `fe46fda709e07c43f90e7ed19d17fa7eec8769bdbae12fcdb2520f06425ed049` | 35,014 | `f88fbd88ff1ec0bbe6aba2945e4d2e82a5f15b48ba35d5aa166ab7968ce6c890` | 1 |
| 5 | 813-1015 | 8,016 | `3b373fe353a3e670a399cc3fc8d39017791c5e1eab2fc39f9ec51e54972797ba` | 43,030 | `faae090ea5f55dca4eda688fe7e9c3cb58c8fb10b5187fd1f662375660a264c4` | 1 |
| 6 | 1016-1218 | 9,610 | `22215685fdf066ec199da3b5d60d81ad5359d68dc8fc0c3d8dff5236f1d24790` | 52,640 | `c71c7f41f637baaf78ad698ec37ae6049fe95d5c8eff5788de037d67956df427` | 1 |
| 7 | 1219-1421 | 10,616 | `2706241ec992bc61f009d78951c79c8befa8ba48502d21ca208f8e187528f25b` | 63,256 | `74cc84365fcb671986c404f7600fb590f994eaa6a6414a87ab5219529b3b9f84` | 1 |
| 8 | 1422-1624 | 19,309 | `ab1de5fb21daa7aab85120fb232341689c463f30016e92eff5cf1b23b3d2174d` | 82,565 | `e71997f0582e08bacb8e0ea59f88594df00641fb7e99ab6cb54fd63a48602893` | 1 |
| 9 | 1625-1827 | 15,986 | `8018ca2f4d231a9719e81eda53a9c41b4744f7d625f5847b6fccac73d276bfc9` | 98,551 | `508e02555941a7d55e940819d89fb2766fe1c73983b9c58d969faba420bae237` | 1 |
| 10 | 1828-2030 | 21,393 | `1df4c817f5f4a0b73eafd101cdff2d57188446019010a9c343795cfc3fdca419` | 119,944 | `9292377ee9670fbac3ad56563c04a128c52833cd16c051ff65c20689a49ef096` | 1 |
| 11 | 2031-2233 | 25,950 | `b58053e20be6d05ab9afb9f62e0e11dc5819eab62cb97fb2199bc321b675cb93` | 145,894 | `5562adb5b54116340d62b8bd1b4d5b0b12ee8bb6101a18af6a896fe690f94899` | 1 |
| 12 | 2234-2436 | 20,558 | `1facbca01fa7380bde19d3625aa18de4cd3a08f8e34a6b68c0a0591a3f81e44f` | 166,452 | `10719948d5229d98ad4e820baa89b001286790a99f5a639b137bb049775d2fe8` | 1 |
| 13 | 2437-2639 | 13,465 | `cea764ac34b481e28f672e3fbce06cf33a4d9478a1bc9dc6484a9276129079da` | 179,917 | `418300c3539d543bc46dbae6a7e9e3d2490f00351ecd5264c42db8348e69c0f1` | 1 |
| 14 | 2640-2842 | 13,871 | `988a49d03ed2acaadf31beb5307d3e0a752425b575ed70ca259fc49f24eaf669` | 193,788 | `c336333afdf4c537c34db624a1ffa9503191d0b6c400c2eaad67ecd5db27595d` | 1 |
| 15 | 2843-3045 | 15,875 | `254b0acf64a6e7f7693decbea4418a933be16a0c384c54705e42a367c8361d06` | 209,663 | `58974968022e22b20b5d664d27f5a951ca1734be1d0427bcb2e41374e3241419` | 1 |
| 16 | 3046-3246 | 15,785 | `8c7d2bb3d19ce38b6f5fba87b0a8cff5c8ab5bda481667e9e5df7b54e3524ca2` | 225,369 | `31acaf22240be68a4243d1199ba55aeef0dac68f6d5e3758f8fa5dd28d83a6cb` | 0 |

Only after exact step-16 byte equality, 3,246 LF terminators, zero CRLF,
terminal LF, and zero sentinel may that recovery path be edited. Every unknown,
partial, nonmatching, duplicate-sentinel, or failed patch state stops and is
preserved. Shell writers, copy/concatenation commands, alternate contexts, and
editing the failed source are forbidden.

Repair only the recovery script to implement this instrument, bind this new C0
commit/path/bytes/hash, use fresh labels below, validate the immutable retry-24
RED pair and all older evidence before setup, and retain exactly one guarded
`File.Replace` with immediate return and no catch-path republish. Both
PowerShell parser invocations must report zero errors. Three independent
exact-byte B0/M0/m0 reviews must approve the repaired recovery script, including
adapter/supervisor/controller separation, all 93 suites/97 cases, 17 retry
routes plus ownership-temp, publication closure, 750-path population closure,
and semantic validation of every preserved RED pair. Any byte change
invalidates those reviews.

## Fresh labels and writable/transient ledger

The verified-absent fresh generation label is retry-26 at
`B:\Agents\.coauthor-v043-c2-detached-retry-26`; its capsule is
`C2_STRUCTURAL_GENERATION_RETRY26_CAPSULE.json`. Qualification is attempt 041 at
`C:\Users\young\AppData\Local\Temp\coauthor-v043-qualification-20260805-attempt-041`
with capsule `C2_ATTEMPT_041_CAPSULE.json`. Replay is retry-27 at
`B:\Agents\.coauthor-v043-c2-detached-retry-27` with capsule
`C2_STRUCTURAL_REPLAY_RETRY27_CAPSULE.json`; no-write qualification is attempt
042 at the matching `coauthor-v043-qualification-20260805-attempt-042` path and
capsule `C2_ATTEMPT_042_CAPSULE.json`. The controller `--run-root` remains the
common parent `C:\Users\young\AppData\Local\Temp` because it appends run ID.

The four exact mode-temp roots are
`C:\Users\young\AppData\Local\Temp\coauthor-v043-structural-20260805-retry-26-transients`,
`C:\Users\young\AppData\Local\Temp\coauthor-v043-structural-20260805-retry-27-transients`,
`C:\Users\young\AppData\Local\Temp\coauthor-v043-qualification-20260805-attempt-041-transients`,
and
`C:\Users\young\AppData\Local\Temp\coauthor-v043-qualification-20260805-attempt-042-transients`.
The two exact structural ownership-temp roots are
`C:\Users\young\AppData\Local\Temp\coauthor-v043-structural-20260805-retry-26-owned-launch-transients`
and
`C:\Users\young\AppData\Local\Temp\coauthor-v043-structural-20260805-retry-27-owned-launch-transients`.
Attempt modes do not create ownership-temp roots because their controllers are
not wrapped by the structural supervisor.

The sole persistent paths permitted to change, in order, are:

1. this new C0 path plus primary Git objects/ref/log/index/COMMIT_EDITMSG for
   its isolated commit, then the later manifest-only commit;
2. the recovery script path and only its registered assembly/repair states;
3. retry-24 worktree/admin removal only after the post-review rebind below;
4. fresh retry-26/retry-27 worktree/admin paths, including only their admin
   indexes as equality/stat-cache transitions;
5. the four exact mode-temp roots, two structural ownership-temp roots, and
   exact transient children admitted above;
6. provenance base/children and every predecessor-registered transient after
   exact fresh-label substitution;
7. the stale shared runner lock only at the generation-PASS deletion,
   attempt-owned creation/metadata transitions, and final reviewed deletion;
8. exact attempt-041/042 transaction directories;
9. only retry-26's manifest and its exact writer sibling, then the primary
   manifest through the manifest-only commit;
10. the four fresh terminal capsule targets and their four same-directory
    provisional publication preimages;
11. green-only deletion of those four provisional preimages, retry-26/27 and
    admins, empty mode/ownership/provenance roots as registered, and the final
    shared runner lock after pre-cleanup approvals; and
12. after cleanup postflight only, updates to the five existing C2 records.

Every other path is read-only. In particular, retry-24/admin and its RED pair,
the failed script, all retry-22 and older RED evidence, both failed retry-22
assembly artifacts, both producer duplicates, FIC/residue, cache/catalog,
archive/package, shipment, research, host, consumer, and activation planes are
read-only except retry-24/admin's one authorized Git removal point.

This new tracked C0 adds exactly one included path. Its isolated commit must
contain 757 tracked paths, exclude zero `.plugin`/`.zip`, exactly six
`scripts/analysis/` paths, and the one manifest, leaving exactly 750 included
population paths. The Python-Unicode-sorted LF path payload without terminal LF
must be 39,190 bytes at SHA-256
`a18ed7b014c4fd24cb81cc81aff80d5cbed30cde0404e8251c37bf8441ee48fa`.
The commit reviews must bind fresh canonical clean-filter and checkout-raw
digests; they must not reuse predecessor content digests.

## Authorized successor sequence

1. Obtain three independent exact-byte B0/M0/m0 reviews of this C0. Repair and
   re-review every finding. Commit this path alone on clean main and bind
   commit/tree/parent, file bytes/hash, and the exact 757/750 population above.
2. Assemble the recovery script through all sixteen exact states, prove final
   equality, then repair only that path. Obtain both-parser zero errors and
   three exact-byte B0/M0/m0 reviews of the final candidate and all closure
   requirements. No capture mode runs before all approvals.
3. Rebind main, all eighteen C2 files, retry-24/admin, stale lock, manifests,
   FIC/residue, fresh absences, subscribers/events, and zero related process.
   Then force-remove only retry-24/admin through Git worktree management and
   prove every other plane unchanged.
4. Create retry-26 detached at the C0 commit and run the reviewed recovery
   script in `generation-structural`. Require terminal PASS, 15 supervised
   structural launches, exact streams/counts/hashes, ownership-temp closure,
   clean retry, stale-lock equality, transient closure, and zero process. Any
   RED or incomplete state stops and preserves all evidence.
5. Only after generation PASS, delete the exact stale retry-19 lock and prove
   absence. Run attempt 041 with common-parent `--run-root`. Require complete
   terminal succeeded receipt, controller-owned transaction evidence, exact
   93/97 evidence, only the retry manifest changed, dead owner/child PIDs,
   stream/transient closure, and zero process.
6. After attempt 041 PASS, patch-copy only its exact generated manifest bytes to
   primary, prove equality, stage only that file, and commit it alone on main.
   Preserve retry-26 and the complete attempt-041 transaction.
7. Create retry-27 detached at the manifest commit. Run structural replay and
   attempt 042. Require supervised structural closure, no-write equality,
   population/case-order identity with attempt 041, terminal transaction
   evidence, clean retry state, exact lock semantics, transient closure, and
   zero process.
8. After all four fresh modes PASS, freeze their terminal capsules and
   provisional preimages, all older RED evidence, both live retries/admins,
   transactions, lock, main, manifests, FIC/residue, runtime/supervisor bytes,
   and process census. Obtain three independent pre-cleanup live-state
   B0/M0/m0 reviews. Any finding stops before cleanup.
9. Only after approvals, delete the four fresh provisional preimages,
   force-remove only retry-26/retry-27 and admins, remove only registered empty
   capability roots, and delete only the exact final shared runner lock. Prove
   all cleanup targets absent and preserved evidence unchanged.
10. Update the five existing C2 records. Final ignored/local C2 is exactly 22
    files: the five updated records plus seventeen retained evidence files.
    Those seventeen are the failed retry-24 script and its recovery successor,
    retry-20 producer duplicate, three retry-22 copy/assembly artifacts, the
    original RED capsule and two RED temporary remnants, retry-22 RED target and
    publication preimage, retry-24 RED target and publication preimage, and the
    four fresh terminal capsules. Obtain three independent exact-byte B0/M0/m0
    reviews of all 22. Never stage, force-add, or commit C2.

Any failure stops and preserves every extant byte. No nonempty cleanup, label
reuse, recovery/cancel/ordinary-status controller command, alternate assembly,
fallback launch, or advancement by inference is authorized.

## Downstream limit

Successful completion closes only v0.43 source qualification under the exact
reviewed evidence. Gate 6 still stops the run until an independently governed
consumer supplies exact v0.43 consumer evidence through its own authority.
Only that evidence may open later package/shipment consideration; it does not
itself authorize package creation, shipping, installation, cache/catalog
mutation, host qualification, research mutation, or activation.
