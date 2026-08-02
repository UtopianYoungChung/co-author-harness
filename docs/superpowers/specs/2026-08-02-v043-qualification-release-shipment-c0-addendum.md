# v0.43 qualification, release, and shipment C0 addendum

**Status:** approved package-maintainer execution boundary for qualification,
version integration, package construction, cache qualification, package
clearance, and shipment in that order. This file grants no academic lifecycle,
research mutation, consumer acceptance, promotion, canon, advisor delivery, or
activation authority.

**Run scope:** `adhoc_review`.

**Parent authority:**
`docs/superpowers/specs/2026-07-31-qualification-architecture-repair-c0.md`.
This addendum narrows the remaining work to the exact paths and gates below.
Any path not enumerated here or in the parent C0 requires another committed C0
addendum before it is created or changed.

## Frozen source baseline

- Repository: `B:\Agents\platform\co-author-harness`.
- Branch: `main`, the only permitted branch.
- Commit: `9f2a5bd84e36a8b746ac3fd8814ccf929f086ab3`.
- Tree: `f915b72e8131fda3e61d953105445ad3a5a49835`.
- Local `origin/main`: `67be86bc33127cf711084e717403b5e399191ab5`;
  source is 47 commits ahead and zero behind.
- Source state: clean; one worktree; no controller or fixture-runner process
  observed.
- Preserved stashes:
  `4cab725415f1aa92482c2568f9dacb54dba1806c` and
  `e9fb3df15939faca4c08e8fb65985adbeee38146`; neither may be applied.
- Package version: `0.42.0` until the gated mechanical version step.
- Persistent lock: `.git/coauthor-fixture-runner.lock`, 57 bytes, SHA-256
  `5e6c81484ae376e9e22844daf83865bd9ebc34cd9d21bfb7dabb3708d9b2fefb`;
  it names dead PID 16060 and is not authority to reuse an active run.
- Source topology excluding `.git`: 1,810 entries, digest
  `4ecfd3e10f54259aa7bcfd1f9f0eabb14b28605fa95484d0f2aa13bcc47786fe`.

The controller repair is committed at the frozen baseline. Its final source
bytes are:

| Path | Bytes | SHA-256 |
|---|---:|---|
| `scripts/release_qualification_controller.py` | 94,329 | `5e4f5778734de71b0fc581d71f290604c6a5aefc5b5ffc55ed01ad422e03ea01` |
| `scripts/release_qualification_controller_smoketest.py` | 130,220 | `eb944a1a5b4025391722761c1d78a3f2537a62969b3d905a03718568108c73ee` |

On these exact bytes, two Windows replays passed 40 cases with nine explicit
POSIX skips, two WSL/Ubuntu replays passed all 49 cases with zero skips, schema
runtime checks passed, and independent Windows and POSIX reviews each returned
B0/M0/m0. The controller is fail-closed if its POSIX subreaper supervisor is
itself killed: it reports incomplete evidence and does not bind mutable output
or guess descendant PIDs. That is not general crash-containment authority.

## Distinct observed planes

The following observations are deliberately not collapsed into one state:

- Source manifest: `.claude-plugin/plugin.json`, 674 bytes, SHA-256
  `25f801100daecb1539208b78cf550e99c200dadfb1344c083386b5e306d1fa60`,
  version `0.42.0`.
- Marketplace manifest: `.claude-plugin/marketplace.json`, 1,425 bytes,
  SHA-256
  `69a330f66b9561b98f55b08d81999a777a3a13430d888d33de31cfd21d1a3055`.
- CLI registration: `codex plugin list` reports the local plugin enabled at
  version `0.42.0` and resolves its path through the local-marketplace source
  junction, not through the installed cache.
- Local-marketplace descriptor:
  `C:\Users\young\.codex\local-marketplaces\joseph-chung-co-author-harness-local\.agents\plugins\marketplace.json`,
  748 bytes, SHA-256
  `478389a5f646a0b6e7e2d4210e46450ad6e726e60ffd8e2ade99b91667f2f9cb`,
  declares stale version `0.37.1`. It is observation-only in this transaction.
- Local-marketplace source path:
  `C:\Users\young\.codex\local-marketplaces\joseph-chung-co-author-harness-local\plugins\co-author-harness-claude`
  is a junction to the repository.
- Installed cache:
  `C:\Users\young\.codex\plugins\cache\joseph-chung-co-author-harness-local\co-author-harness-claude\0.42.0`
  is a regular directory with 2,125 files and 125,414,055 bytes including
  `.git`; excluding `.git` it has 1,810 topology entries and digest
  `231a8cbd3bffc7e247dd5de43faba644c2e15f398202c81d69f413392e8eb84a`.
  It contains no `PROVENANCE.json`; it is therefore not a qualified cache.
- Candidate archive: absent until the package-build gate.
- Cache receipt: absent until archive-derived installation and qualification.
- Startup catalog and actually loaded paths: recorded separately below.

No observation above proves cache equality, startup equality, loaded-path
equality, host qualification, or activation.

## Startup catalog and loaded paths for this task

At task startup, the co-author plugin catalog advertised 43 skill entrypoints
under
`C:\Users\young\.codex\plugins\cache\joseph-chung-co-author-harness-local\co-author-harness-claude\0.42.0\skills`:

`accessibility-overlay`, `advisor-escalation`, `analytic-move-audit`,
`backfill-source-stubs-from-references`, `centroid-pass`,
`check-abstract-body`, `check-contradictions`, `citation-format-pass`,
`claim-coverage-audit`, `classify-manuscript`,
`definition-derivation-check`, `dissolution-move-check`,
`extend-snowball-incremental`, `grammar-mechanics-pass`,
`graph-grounding-overlay`, `grounding-audit`, `ingest-m5-to-wiki`,
`inherit-snowball-from-wiki`, `IS-theory-pass`,
`narrative-structure-pass`, `plugin-commands`, `promote-lessons-to-wiki`,
`p-stage-checker`, `public-interest-accountability-pass`,
`quick-deterministic`, `repin-register`, `response-letter-review`,
`retrofit-concept-grounding`, `run-draft`, `run-finalize`,
`run-generator-session`, `run-iterate`, `run-phase-1`, `run-phase-2`,
`run-phase-3`, `run-phase-3-stability`, `run-phase-4`, `run-reflection`,
`seed-snowball-discovery`, `sentence-level-pass`,
`suchman-register-audit`, `tool-contract-roundtrip`, and
`turabian-format-pass`.

Every advertised entrypoint is the corresponding `<name>\SKILL.md` under that
root. No co-author-harness skill or plugin `SKILL.md` path has actually been
loaded by this task. The separately loaded
`C:\Users\young\.agents\skills\commit-work\SKILL.md` is not a co-author plugin
path.

## Prior fresh-host evidence: fail closed

The delegated receipt named frozen evidence under
`C:\Users\young\AppData\Local\Temp\coauthor-fresh-host-f25a2c7\fresh-task-019fc058-20260802T025106Z-attempt-001`.
Fresh observation at this baseline found that the supplied hashes do not match
the current files and the supplied root-level transaction filename is absent:

| Observation | Current value |
|---|---|
| `evidence-index.json` | 50,985 bytes; SHA-256 `52e9d9dd1f5f330d9e157ee7b395731dd75dd2533e6b18292fd43083c7540a91` |
| `freeze-marker.json` | 2,225 bytes; SHA-256 `332285b211b71139ca19d412b515438cd8e7a19743aa98f5800fcd9160d6d717` |
| delegated `host-qualification-transaction.json` | absent at the supplied root |
| present governed transaction | `releases\verification\fresh-host-019fc058\host-qualification.json` |
| present transaction ID | `host-qualification:834374dd3a944ed4cbd4990622067032` |
| present disposition | `HOST_QUALIFICATION_FAILED / HOST-CORE-PROBE-FAILED` |

This is a mismatch, not a repaired receipt and not a pass. The prior evidence
is excluded from v0.43 package clearance and may not be refreshed or mutated by
this task. Fresh-host qualification remains a separate new-task transaction
after shipment.

## Allocation and review separation

- Root integrator owns the ledger, qualification orchestration, version
  integration, archive/cache transaction, package evidence, and all commits.
- Windows/RunLock reviewer owns focused process-ownership replays and read-only
  review; it may not change version, package, cache, or remote state.
- POSIX reviewer owns WSL process-closure replays and read-only review; it may
  not change Windows, package, cache, or remote state.
- Release reviewer owns independent package/evidence inspection only after the
  producing lane is quiescent; it cannot manufacture consumer evidence or
  promote a warning or failure to a pass.
- Long-running registry work runs through the durable qualification controller,
  not through an unowned shell process. Parallel review is allowed only for
  non-overlapping, read-only observations of identical frozen bytes.

## Authorized tracked paths

The parent C0 already authorizes these integration paths. Their current
preimages are frozen here; only the described release work may change them.

| Action | Path | Bytes | SHA-256 / preimage |
|---|---|---:|---|
| MODIFY | `scripts/release_qualification_controller.py` | 94,329 | `5e4f5778734de71b0fc581d71f290604c6a5aefc5b5ffc55ed01ad422e03ea01` |
| MODIFY | `scripts/release_qualification_controller_smoketest.py` | 130,220 | `eb944a1a5b4025391722761c1d78a3f2537a62969b3d905a03718568108c73ee` |
| MODIFY | `docs/analysis/generated/fixture_manifest.json` | 54,243 | `25af2a5577a71c27f37cc9579e0bb0c644fe67c9979b9df93abcb1c82043881c` |
| MODIFY | `references/MANIFEST.md` | 28,152 | `b3f418111de6143c83447463cc18567b887cb5ccdd0559449ada48ba3a412a41` |
| MODIFY | `references/DETERMINISTIC_CHECKS.md` | 46,537 | `c8e03ccb129e8e40de2ce51f96306895000c96181d3457ac55208364e3da4cf1` |
| MODIFY | `references/contract_kernel.v1.json` | 37,242 | `4f6ad0814f3fb4d374dee2f410f49554faf26bae1ec1f4303b5cd1d9ac5899a4` |
| MODIFY | `references/compatibility/shipment-v2/contract_kernel_projection.json` | 2,907 | `2a74d7a576f414de667003fde6a29427de58008df81b4a9b6bbaee8e18ed19a0` |
| MODIFY | `references/compatibility/shipment-v2/compatibility_profile.json` | 4,510 | `41d16d37f0c52251ff4215786ef5946ce7c408bac17e0f26b204f346c1a53ee0` |
| MODIFY | `CHANGELOG.md` | 390,689 | `eee78a4eb0edb693f44350e71052e3c40ca44fbf299b8c73e10cbeb8552a478c` |
| MODIFY | `README.md` | 39,512 | `8f6b62302dae0303db8964d5c47d9b92aee0212ac76719a230ab14a3b5adda23` |
| MODIFY | `.claude-plugin/plugin.json` | 674 | `25f801100daecb1539208b78cf550e99c200dadfb1344c083386b5e306d1fa60` |
| MODIFY | `.claude-plugin/marketplace.json` | 1,425 | `69a330f66b9561b98f55b08d81999a777a3a13430d888d33de31cfd21d1a3055` |
| CREATE | `docs/release-notes/RELEASE_NOTES_v0.43.0.md` | 0 | `ABSENT` |
| CREATE | `docs/superpowers/specs/2026-08-02-v043-qualification-release-shipment-c0-addendum.md` | 0 | `ABSENT` |

## Authorized ignored/local evidence paths

Only these release outputs may be created:

- `releases/co-author-harness-claude-v0.43.0.zip`
- `releases/co-author-harness-claude-v0.43.0.sha256`
- `releases/verification/v0.43.0/C0/C0_ADDENDUM_FREEZE.md`
- `releases/verification/v0.43.0/C0/C0_PATH_LEDGER.md`
- `releases/verification/v0.43.0/C0/C0_READ_ONLY_REVIEW.md`
- `releases/verification/v0.43.0/C1/C1_CONTROLLER_REPAIR.md`
- `releases/verification/v0.43.0/C1/C1_FOCUSED_RESULTS.json`
- `releases/verification/v0.43.0/C1/C1_READ_ONLY_REVIEW.md`
- `releases/verification/v0.43.0/C2/C2_SOURCE_QUALIFICATION.md`
- `releases/verification/v0.43.0/C2/C2_STRUCTURAL_RESULTS.json`
- `releases/verification/v0.43.0/C2/C2_REGISTRY_RESULTS.json`
- `releases/verification/v0.43.0/C2/C2_DETACHED_REPLAY.json`
- `releases/verification/v0.43.0/C2/C2_READ_ONLY_REVIEW.md`
- `releases/verification/v0.43.0/C3/C3_VERSION_HISTORY_SLICE.md`
- `releases/verification/v0.43.0/C4/C4_VERSIONED_QUALIFICATION.md`
- `releases/verification/v0.43.0/C4/C4_STRUCTURAL_RESULTS.json`
- `releases/verification/v0.43.0/C4/C4_REGISTRY_RESULTS.json`
- `releases/verification/v0.43.0/C4/C4_DETACHED_REPLAY.json`
- `releases/verification/v0.43.0/C4/C4_READ_ONLY_REVIEW.md`
- `releases/verification/v0.43.0/C5/C5_PACKAGE_CACHE_PLANES.md`
- `releases/verification/v0.43.0/C5/source-runtime-receipt.json`
- `releases/verification/v0.43.0/C5/archive-runtime-receipt.json`
- `releases/verification/v0.43.0/C5/unpacked-runtime-receipt.json`
- `releases/verification/v0.43.0/C5/installed-cache-runtime-receipt.json`
- `releases/verification/v0.43.0/C5/qualification-plane-topology-receipt.json`
- `releases/verification/v0.43.0/package_evidence_index.json`
- `releases/verification/v0.43.0/C6/C6_PACKAGE_QUALIFICATION_REVIEW.md`
- `releases/verification/v0.43.0/C6/C6_FINAL_INDEX_REVIEW.md`
- `releases/verification/v0.43.0/release_evidence_index.json`
- `releases/verification/v0.43.0/VERIFICATION_REPORT.md`
- `releases/verification/v0.43.0/C7/shipment_push.json`
- `releases/verification/v0.43.0/C7/C7_SHIPMENT_REVIEW.md`

Fresh-host C8 evidence is intentionally absent from this task's ledger.

## Authorized transient attempt paths

- `B:\Agents\.coauthor-v043-c2-detached`
- `B:\Agents\.coauthor-v043-c4-detached`
- `B:\Agents\.coauthor-v043-c5-build`
- `C:\Users\young\AppData\Local\Temp\coauthor-v043-qualification-20260802-attempt-001`
- `C:\Users\young\AppData\Local\Temp\coauthor-v043-unpacked-20260802-attempt-001`

Each path must be absent before creation, must receive an owner marker and
receipt binding, and must be quiescent before removal. A second attempt requires
a newly enumerated path in a committed addendum.

## Authorized cache and remote targets

The CLI-managed cache transaction has this exact mutable ledger:

- Selector:
  `co-author-harness-claude@joseph-chung-co-author-harness-local`, currently
  installed and enabled at version `0.42.0`.
- Existing cache allowed to be removed by `codex plugin remove` only:
  `C:\Users\young\.codex\plugins\cache\joseph-chung-co-author-harness-local\co-author-harness-claude\0.42.0`.
- Candidate cache allowed to be created by `codex plugin add` only:
  `C:\Users\young\.codex\plugins\cache\joseph-chung-co-author-harness-local\co-author-harness-claude\0.43.0`.
- CLI registration file:
  `C:\Users\young\.codex\config.toml`, currently 17,338 bytes, SHA-256
  `939dc07cee6476fdac4d14927500b54b9308d9b10da9152f3fa70c0bf7e42f84`.
  Only the supported remove/add commands may mutate it. The final file must be
  byte-identical to this preimage and the selector must again be installed and
  enabled; otherwise stop without a manual edit.
- Mutable marketplace source junction:
  `C:\Users\young\.codex\local-marketplaces\joseph-chung-co-author-harness-local\plugins\co-author-harness-claude`.
  Its preimage is `Junction` targeting
  `B:\Agents\platform\co-author-harness`. After the archive is extracted and
  qualified, a guarded transaction may remove this junction non-recursively,
  recreate it temporarily with the exact target
  `C:\Users\young\AppData\Local\Temp\coauthor-v043-unpacked-20260802-attempt-001`,
  run `codex plugin add`, and then restore the junction to the exact preimage
  target in a `finally` block. The restored type and resolved target must be
  re-observed before any cache claim.
- The marketplace descriptor remains observation-only at
  `C:\Users\young\.codex\local-marketplaces\joseph-chung-co-author-harness-local\.agents\plugins\marketplace.json`,
  748 bytes, SHA-256
  `478389a5f646a0b6e7e2d4210e46450ad6e726e60ffd8e2ade99b91667f2f9cb`.
  It may not change.

The transaction order is: freeze all preimages; prove the extraction and
target path; `codex plugin remove`; retarget the exact junction; `codex plugin
add`; restore the junction in `finally`; re-observe config, selector, cache,
descriptor, and junction; then qualify the installed cache against the exact
archive. Manual cache, config, registration, marketplace, descriptor, manifest,
or installed-metadata edits are forbidden.

Remote mutation remains closed until package clearance. After clearance, the
only authorized remote targets are:

- repository `https://github.com/UtopianYoungChung/co-author-harness.git`;
- `refs/heads/main`;
- `refs/tags/v0.43.0`;
- release assets `co-author-harness-claude-v0.43.0.zip` and
  `co-author-harness-claude-v0.43.0.sha256`.

## Ordered gates

1. Preserve a clean committed controller repair, focused green results, and
   independent B0/M0/m0 reviews.
2. Commit this addendum before creating any new evidence, archive, cache, or
   transient path.
3. Run all 15 root structural checks, the complete cache-off fixture registry,
   stable process/residue censuses, and a clean detached replay. Require
   independent B0/M0/m0 review of the exact source commit.
4. Mechanically bump both manifests to `0.43.0` through
   `scripts/update_version_manifests.py`; add coherent changelog, release notes,
   manifest, deterministic-check, and contract-kernel history on the authorized
   paths; commit the integration.
5. Repeat the exact versioned structural, complete-registry, residue, and
   detached qualifications and obtain an independent B0/M0/m0 review.
6. Require a separately governed v0.43 consumer compatibility receipt. This
   task cannot author or simulate it, and the historical v0.42 receipt cannot
   carry forward.
7. Build the ZIP, prove member and provenance equality, probe source/archive/
   unpacked/cache runtime planes, and qualify the archive-derived CLI cache.
   Run `release-gate.sh` against the existing ZIP with `--ship-intent` and the
   frozen qualification specification; do not rebuild inside that gate.
8. Record `IMPLEMENTED`, obtain independent package/evidence review, record
   `PACKAGE_CLEARED`, and obtain final-index B0/M0/m0 review. A green suite alone
   is not package clearance.
9. Only then push `main`, prove local/remote equality, create and verify
   `v0.43.0`, upload and verify the two assets, and record `SHIPPED`.
10. Stop. Fresh-host qualification requires a separate new task and cannot
    retroactively change package clearance or shipment.

## Stop and claim gates

Stop on dirty or concurrent source, an active or unowned lock, an unledgered or
retry path, source drift, incomplete corpus, any fixture cache hit, schema/
runtime divergence, package/member/provenance mismatch, a cache not derived
from the candidate archive, an unresolved reviewer finding, a required hand
edit to a generated version plane, remote mismatch, or missing explicit
authority. Never turn a warning or failure into a pass.

This transaction may not claim research acceptance/application, lifecycle or
F9 advancement, promotion, canon, advisor delivery, package clearance before
Gate 8, shipment before Gate 9, fresh-host qualification, startup-catalog
agreement, loaded-path agreement, consumer re-attestation, or activation.
