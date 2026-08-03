# v0.43 C2 registered-worktree observation closure C0 addendum

**Status:** approved package-maintainer boundary for repairing the exact
registered-worktree observation refusal exposed before attempt 012 and for one
final source transaction plus one final multi-root detached transaction. This
addendum grants no package clearance, shipment, cache mutation, consumer
re-attestation, host qualification, activation, research mutation, acceptance,
promotion, release, or canon authority.

**Run scope:** `adhoc_review`.

**Parent authority:**
`docs/superpowers/specs/2026-08-03-v043-c2-cross-worktree-output-scope-c0-addendum.md`.
All parent prohibitions and earlier evidence remain binding. Any path not
enumerated here or in the parent ledgers requires another committed addendum
before it is created or changed.

## Frozen state and governed red

- Repository: `B:\Agents\platform\co-author-harness`.
- Branch: `main`, the only permitted branch.
- Commit: `e379644562ad72372bcbb51739af0c164bf20b91`.
- Tree: `3feadc638d128515ae57d8b6b6cff100dc1d508f`.
- Source-root attempt 011 terminally succeeded with 93 suites / 97 direct
  cases, cache off, zero cache hits, stable 720-file canonical and raw
  tested-input digests, manifest publication, exact 180-file governed
  bytecode postflight, exit zero, empty stderr, and zero live identities. Its
  receipt is 2,419 bytes, SHA-256
  `28353dccbf444b7f4d92189c129f97d72dd9653fca78b5f98f4f502d9a266dba`.
- The committed manifest is 54,250 bytes, SHA-256
  `d40f27708a307b9b5fc84994b7c3e386728f03767054de2bd1f4198621682739`.
- The primary and detached-retry-2 tracked worktrees are clean at the exact
  commit above. The primary bytecode census is 180 files with digest
  `08c6740aab85ac2b73162dd0bb7c792815e2ba871dacb0decc3a070363085f2b`;
  detached-retry-2 has zero bytecode files and zero `__pycache__` directories.
- Attempt-012 preflight proved both baselines and both exact heads, then invoked
  the detached controller with both registered worktree roots as repeated
  `--watch-root` values. Before run-directory creation or child execution,
  `destination_capability.assert_writable` rejected the primary worktree with
  `DEST-PROTECTED`. The exact attempt-012 path remains absent. Its label is a
  pretransaction rejection and will not be reused.

The controller currently applies write-destination authority to every output
watch root. That conflates two different powers: permission to write an
allowed output and permission to read a pre/post inventory for refusal. A
detached controller must be able to observe another exact registered worktree
of the same Git repository without thereby granting the child or controller
write authority there. Arbitrary directories, unregistered siblings,
subdirectories merely contained by a registered root, reparse roots, missing
roots, and different-repository worktrees remain forbidden unless separately
writable under the existing destination policy.

## Exact writable ledger

Only these tracked paths may change in this repair slice:

| Action | Path | Preimage bytes | Preimage SHA-256 |
|---|---|---:|---|
| CREATE | `docs/superpowers/specs/2026-08-03-v043-c2-registered-worktree-observation-c0-addendum.md` | 0 | `ABSENT` |
| MODIFY | `scripts/release_qualification_controller.py` | 97,587 | `390988a9fe5ff645147bebe870a704b30726699304825fc5c1c3cb3f7e69a033` |
| MODIFY | `scripts/release_qualification_controller_smoketest.py` | 147,038 | `5af4e5c0e46546ddd9db2056938828f4778c73b49235d89725ebd8c7622e1849` |
| MODIFY | `references/contract_kernel.v1.json` | 37,242 | `3d36e50a7ca9fa0edbf1d19d139356f0d00ab1d4f2267c3a2bcd59bf2118f979` |
| MODIFY | `references/compatibility/shipment-v2/contract_kernel_projection.json` | 2,907 | `9cc7cfbac81157801e5445784f90c24e9b96cd6d30b48e8f5d7795e5200c1745` |
| MODIFY | `references/compatibility/shipment-v2/compatibility_profile.json` | 4,510 | `750a46f92230e0e6f679187e5655c9f8d5a496730d38f15ab02a94300536eaac` |
| QUALIFICATION OUTPUT ONLY | `docs/analysis/generated/fixture_manifest.json` | 54,250 | `d40f27708a307b9b5fc84994b7c3e386728f03767054de2bd1f4198621682739` |

The already-authorized ignored C1/C2 evidence paths may be updated. No version,
package, cache, registration, research, or remote path is writable here.

## Required repair and regression

1. Preserve `assert_writable` for every allowed output and every watch root
   that is missing and must be created. Observation authority must never create
   or authorize bytes.
2. For an existing watch root that destination policy does not make writable,
   permit observation only when the path is the exact root of a worktree
   registered by Git for the controller source repository and resolves to the
   exact same Git common directory. Reparse roots and discovery ambiguity fail
   closed with the existing output-topology diagnostic.
3. Add deterministic regressions proving:
   - an exact registered same-repository protected sibling is watchable;
   - the same sibling is still refused as an allowed output;
   - an unregistered sibling and a subdirectory of a registered sibling remain
     refused;
   - registry/common-directory discovery failure remains a refusal; and
   - multiple watched roots still detect output in either root.
4. Rebind only the controller component hash in the contract kernel, then the
   raw kernel hash in the compatibility projection, then the raw six-file kit
   aggregate in the profile.
5. Run the Windows and WSL/POSIX controller suites, schema, fixture-
   infrastructure, subprocess-text, kernel-coherence, shell-syntax, exact
   bytecode censuses, and all mechanical root checks. Obtain independent
   B0/M0/m0 review before committing the repair.

## Final transaction paths and gates

The preserved detached-retry-2 worktree may be removed only after its clean
head and zero-bytecode state are re-observed. The only new paths are:

- source-root attempt 013:
  `C:\Users\young\AppData\Local\Temp\coauthor-v043-qualification-20260803-attempt-013`;
- detached replay attempt 014:
  `C:\Users\young\AppData\Local\Temp\coauthor-v043-qualification-20260803-attempt-014`;
- detached worktree:
  `B:\Agents\.coauthor-v043-c2-detached-retry-3`.

Each path must be absent before creation. Attempt 013 must run the complete
authoritative cache-off registry under the durable controller and may replace
the manifest only on terminal success. That exact manifest must be committed
before attempt 014.

Attempt 014 must run the exact committed tree with
`--tier full --no-write --cache-mode off`, watch both the new detached root and
the primary root, and ignore only the existing shared
`.git/coauthor-fixture-runner.lock`. It permits no package output. All external
Git/worktree/cache activity must remain quiescent. Require primary bytecode
180 files at the governed digest and four directories before and after;
require detached bytecode and `__pycache__` counts both zero before and after.
Any Git-administration drift, package output, warning, refusal, incomplete
evidence, failed case, cache hit, missing process closure, or review finding is
a stop.

C2, version, package, cache, clearance, remote, shipment, fresh-host,
startup-catalog, loaded-path, consumer, activation, research, acceptance,
promotion, and canon claims remain closed until their separate gates pass.
