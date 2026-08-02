# v0.43 C2 repair and retry C0 addendum

**Status:** approved package-maintainer boundary for repairing the three defects
exposed by the refused C2 source-qualification transaction and for one new
controller-owned retry. This addendum grants no package clearance, shipment,
cache mutation, consumer re-attestation, host qualification, activation,
research mutation, acceptance, promotion, release, or canon authority.

**Run scope:** `adhoc_review`.

**Parent authority:**
`docs/superpowers/specs/2026-08-02-v043-qualification-release-shipment-c0-addendum.md`.
All parent prohibitions and later gates remain binding. Any path not enumerated
here or in the parent authority requires another committed addendum before it
is created or changed.

## Frozen refused state

- Repository: `B:\Agents\platform\co-author-harness`.
- Branch: `main`, the only permitted branch.
- Commit: `ed3e04e5c60dc74b75125b9a9e6168132155353d`.
- Tree: `ab68fccef21a8a0c02873e735bb4cb404a62e2f9`.
- The worktree differs from that tree only because
  `docs/analysis/generated/fixture_manifest.json` is intentionally absent.
  Its committed preimage was 54,243 bytes, SHA-256
  `25af2a5577a71c27f37cc9579e0bb0c644fe67c9979b9df93abcb1c82043881c`.
  The refused authoritative transaction voided that manifest before running;
  it must not be restored from stale bytes.
- Refused attempt, frozen and never reusable:
  `C:\Users\young\AppData\Local\Temp\coauthor-v043-qualification-20260802-attempt-001`.
- The complete cache-off registry ran 93 suites and 97 cases but did not pass:
  two cases failed and the controller independently refused an unauthorized
  `.pyc` output. No replacement manifest was published.

The refused attempt's bound controller evidence is:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `receipt.json` | 3,312 | `4a42c08005fd91b3387ed20c0936d3063171401b523cedab41b85bc3e9a60ddc` |
| `exit.json` | 756 | `10c84aa3defd4fe62f7dd4eee07a8243350cce96e7591cc7ba56a6d8feba6b17` |
| `journal.json` | 765 | `b83d8a6293dc71b50ddce2fa71838a936b40056f2d2d1f3fce2190308d7787ec` |
| `owner.json` | 114 | `69e54fe9dfffa4ddbe56b285553cf80ee17da9b3c6015ab24b280dd8f985ac8b` |
| `stdout.bin` | 10,091 | `dc4a5be28d38561694e90ee131dfc91b54aa2d73590947e0d680e040421912a6` |
| `stderr.bin` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

The unauthorized output was
`scripts/__pycache__/graph_authority_gate.cpython-314.pyc`, 2,060 bytes,
SHA-256
`211c6c57430d316d222c4fd7a7fd0a6c48fc65c475e4e0bf6c3dd1586ffc0251`.
It was hash-bound before guarded removal and is now absent.

## Authorized repair paths

Only these tracked paths may change in this repair slice:

| Action | Path | Bytes | SHA-256 / preimage |
|---|---|---:|---|
| CREATE | `docs/superpowers/specs/2026-08-02-v043-c2-repair-retry-c0-addendum.md` | 0 | `ABSENT` |
| MODIFY | `scripts/release_qualification_controller_smoketest.py` | 130,220 | `eb944a1a5b4025391722761c1d78a3f2537a62969b3d905a03718568108c73ee` |
| MODIFY | `scripts/milestone_framework_smoketest.py` | 153,789 | `47602995a239f7e81b04368155f1de0c3bab5fc3948e5e7bbbf1afd2ad4fefb9` |
| MODIFY | `references/contract_kernel.v1.json` | 37,242 | `4f6ad0814f3fb4d374dee2f410f49554faf26bae1ec1f4303b5cd1d9ac5899a4` |
| MODIFY | `references/compatibility/shipment-v2/contract_kernel_projection.json` | 2,907 | `2a74d7a576f414de667003fde6a29427de58008df81b4a9b6bbaee8e18ed19a0` |
| MODIFY | `references/compatibility/shipment-v2/compatibility_profile.json` | 4,510 | `41d16d37f0c52251ff4215786ef5946ce7c408bac17e0f26b204f346c1a53ee0` |
| CREATE | `docs/analysis/generated/fixture_manifest.json` | 0 | `ABSENT_AFTER_GOVERNED_VOID` |

The pre-existing ignored C2 evidence files authorized by the parent may be
updated to bind the repair and retry results. No new evidence filename is
authorized here.

## Required red-to-green repairs

1. Preserve the refused attempt and focused red results. The existing
   `contract_kernel_coherence_smoketest.py` and
   `subprocess_text_policy_smoketest.py` are the regression tests; no duplicate
   test surface is authorized.
2. Rebind only the live `release-qualification-controller` component hash in
   `contract_kernel.v1.json`, then mechanically rebind the kernel projection
   and compatibility profile aggregate. Historical controller hashes in the
   controller smoketest remain immutable.
3. Add explicit `encoding="utf-8"` and `errors="strict"` to the three Git
   subprocess probes identified by the text-policy red in the controller
   smoketest.
4. Add `-B` to all 12 nested isolated Python invocations in
   `milestone_framework_smoketest.py`. The outer fixture runner and controller
   already suppress bytecode; each isolated child must independently do so
   because `-I` ignores `PYTHONDONTWRITEBYTECODE`.
5. Run the focused kernel, subprocess-text, controller Windows, controller
   WSL/POSIX, schema-runtime, and `integration-sk20` checks. Prove no new
   `.pyc` beneath the repository and obtain read-only review before committing
   the repair.

The failed full-registry transaction is the governed red for output-scope
containment. A focused `integration-sk20` replay plus a before/after residue
census is required green evidence before the corpus may run again.

## Authorized retry path and gates

The only new transient qualification path is:

`C:\Users\young\AppData\Local\Temp\coauthor-v043-qualification-20260802-attempt-002`

It must be absent before creation, receive a controller owner marker, and use
the same cache-off full-registry request as attempt 001 on the committed repair
bytes. Attempt 001 remains immutable. Attempt 002 may publish the fixture
manifest only if all suites and cases pass, cache hits are zero, tested inputs
are stable, process closure is complete, and the controller observes no
unauthorized output. The manifest, controller receipt, exit record, journal,
stdout, stderr, request, owner, intent, and pre/post censuses must be hash-bound
before any cleanup or pass claim.

After a green source-root transaction, run the parent-authorized detached
read-only replay and obtain independent B0/M0/m0 review. Any ambiguity,
additional output, new failing case, incomplete process evidence, source drift,
or unledgered path is a stop. The version, package, cache, clearance, remote,
and fresh-host gates remain closed until C2 is green and committed.
