# v0.43 C2 controller-review bytecode cleanup C0 addendum

**Status:** approved package-maintainer boundary for removing exactly two
review-emitted ignored bytecode files and repeating the focused repair proof.
This addendum grants no package clearance, shipment, cache mutation, consumer
re-attestation, host qualification, activation, research mutation, acceptance,
promotion, release, or canon authority.

**Run scope:** `adhoc_review`.

**Parent authority:**
`docs/superpowers/specs/2026-08-03-v043-c2-registered-worktree-observation-c0-addendum.md`.
All parent ledgers and prohibitions remain binding.

## Frozen state and provenance

- Repository: `B:\Agents\platform\co-author-harness`.
- Branch: `main`, the only permitted branch.
- HEAD: `324e7bb000dbe1956b5c406c191fc5b7174a3cdf`.
- HEAD tree: `3e81376e0df4561ac1de1a99086eaf0d8ffe12cb`.
- The authorized five-file repair remains uncommitted. Its controller is
  102,880 bytes, SHA-256
  `91581fcfad19ad17577d949e100ced89536691833b4bcc150f67b23dae5c2eb1`;
  Windows passed 46 cases with 9 platform skips and POSIX passed 51 cases with
  zero platform skips.
- The kernel is bound to
  `4ed83a20c4f01706fc84a011d82be6879d108ea37cce94daa8b3be1877239e0e`
  and the compatibility-kit aggregate to
  `1521145d9c8e853fa15e47b7dbe7202e1ef1e4bac4179ef5511875482948973e`.
- The fixture manifest remains 54,250 bytes, SHA-256
  `d40f27708a307b9b5fc84994b7c3e386728f03767054de2bd1f4198621682739`.
- Independent review accidentally executed
  `python -m py_compile scripts/release_qualification_controller.py
  scripts/release_qualification_controller_smoketest.py` without `-B` or
  `PYTHONDONTWRITEBYTECODE`. The reviewer personally reported that command as
  the emitter. It created exactly the two files below at
  `2026-08-03T08:06:23Z`.
- No matching release-controller smoke or qualification process is live and
  `.git/index.lock` is absent. Detached-retry-2 remains clean with zero
  bytecode files and zero `__pycache__` directories.

## Exact cleanup ledger

Only the following actions are authorized:

| Action | Path | Frozen bytes | Frozen SHA-256 |
|---|---|---:|---|
| CREATE | `docs/superpowers/specs/2026-08-03-v043-c2-controller-review-bytecode-cleanup-c0-addendum.md` | 0 | `ABSENT` |
| GUARDED REMOVE | `scripts/__pycache__/release_qualification_controller.cpython-314.pyc` | 155,256 | `290b60dbc4b0a7af7822ec60c1a5e4cd77a36b375b14dd867a2e807f4c1c334d` |
| GUARDED REMOVE | `scripts/__pycache__/release_qualification_controller_smoketest.cpython-314.pyc` | 195,723 | `1a24760eae04c0e6668d32d7de0dde2544a90c78d6f84edea05809c247ea6a9b` |

Before removal, re-observe both exact size/hash identities, the absence of live
controller/product identities, the clean detached worktree, and the absence of
`.git/index.lock`. Remove only those two literal paths. Recursive, globbed,
directory-wide, changed-hash, missing-file, or best-effort cleanup is forbidden.

## Closure proof

After guarded removal:

1. Prove the primary inventory equals the attempt-011 governed baseline exactly:
   180 bytecode files, four `__pycache__` directories, and no changed, added, or
   missing bytecode identities. Prove detached-retry-2 remains zero/zero.
2. Repeat the Windows and POSIX controller smokes with both `-B` and
   `PYTHONDONTWRITEBYTECODE=1`; require 46/9 and 51/0 respectively.
3. Repeat schema-runtime, fixture-infrastructure, subprocess-text,
   kernel-coherence, shell-syntax, and parent mechanical checks with explicit
   bytecode suppression. Do not run the full fixture corpus in this cleanup
   slice.
4. Re-prove the exact governed bytecode inventory, unchanged tracked five-file
   repair, unchanged manifest, zero live identities, and independent B0/M0/m0
   review before committing the repair.

C2 and every later package, cache, shipment, host, consumer, activation,
research, acceptance, promotion, release, and canon claim remain closed.
