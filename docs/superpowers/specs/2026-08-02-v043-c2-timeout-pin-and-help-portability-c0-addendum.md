# v0.43 C2 timeout pin and help-portability C0 addendum

**Status:** approved package-maintainer boundary for closing structural pin
drift and the Windows console help defect exposed after the attempt-003 timeout
repair. This addendum grants no package clearance, shipment, cache mutation,
consumer re-attestation, host qualification, activation, research mutation,
acceptance, promotion, release, or canon authority.

**Run scope:** `adhoc_review`.

**Parent authority:**
`docs/superpowers/specs/2026-08-02-v043-c2-attempt-003-timeout-observer-isolation-c0-addendum.md`.
All parent gates and the attempt-004 observer-isolation contract remain binding.

## Frozen state and reopened reds

- Timeout-repair commit:
  `48861e29a1b6041329088abf20b02eb2cbab16b3`.
- Timeout-repair tree:
  `20226ea9d90d7cfbf9fde2e5248b71024d164781`.
- `scripts/analysis/fixture_runner.py` postimage: 39,695 bytes, SHA-256
  `c456f6fb028a82ba55dd2ee945a0858f591bd07f71fa802a08d305f17757acaa`.
- Direct scholarly-evaluation proof: exit 0 in 817.941 seconds; 7 red/twin
  pairs, 38 attack/control cases, and 26 binding API cases; repository bytecode
  inventory stable at 180 files.
- Independent review: three separate B0/M0/m0 dispositions on the exact runner
  postimage.
- The subsequent 15-check structural sweep passed 14 checks and failed only
  `scripts/destination-coverage-check.py` with `PIN-DRIFT` for the runner.
- `references/destination_coverage_registry.json` and
  `references/contract_kernel.v1.json` still carry the old runner SHA-256
  `113d2cc1265bf297810e896791fd5922a7c50b67469ef3c47edfb8d05e700526`.
  Both are live machine authorities and must be deliberately re-pinned.
- On this host's CP949 console,
  `python -B scripts/destination-coverage-check.py --help` exits 1 with
  `UnicodeEncodeError` because the argparse description contains three em
  dashes. Validation mode itself remains functional. A maintainer help command
  that cannot render on a supported Windows console is a portability defect.
- Attempt 004 remains absent and forbidden until this closure is committed and
  the complete structural sweep is green.

## Exact authorized change surface

Only these paths may change:

| Action | Path | Bytes | SHA-256 / preimage |
|---|---|---:|---|
| CREATE | `docs/superpowers/specs/2026-08-02-v043-c2-timeout-pin-and-help-portability-c0-addendum.md` | 0 | `ABSENT` |
| MODIFY | `scripts/destination-coverage-check.py` | 6,715 | `b434ebce42806b532d857c2692b4062cf66f17193ecc79f218db176bcae9dc11` |
| MODIFY | `references/destination_coverage_registry.json` | 14,472 | `edefe6c2c0fb1b92b7691507791f81a362bfeaa69e113e4aadfc6b9d8b6068d7` |
| MODIFY | `references/contract_kernel.v1.json` | 37,242 | `e808320b79504a98f9260f4a754bb14bd768315ddf107fd616acf423ed49a15c` |

The void fixture-manifest deletion remains failed attempt-003 state and must
not enter either commit.

## Required closure

1. Commit this addendum alone.
2. Replace only the three em dashes in the destination-coverage checker
   description with ASCII-safe punctuation. Do not change validation, census,
   class, pin, exit, or write semantics.
3. Run the governed `--pin` operation once. It may update only the two stale
   `package_confined` hashes for the changed runner and checker in
   `references/destination_coverage_registry.json`.
4. Update only the `fixture-runner` SHA-256 in
   `references/contract_kernel.v1.json` to the exact runner postimage hash.
5. Require all of the following with `python -B` and a stable repository-wide
   bytecode census:
   - destination-coverage `--help` exits 0 under the ambient CP949 console;
   - destination-coverage validation exits 0 with 61 writers classified,
     43 guarded, zero unclassified, and zero drifted;
   - contract-kernel coherence smoke exits 0;
   - fixture-infrastructure check exits 0.
6. Obtain independent B0/M0/m0 review of the exact three-file postimage and
   commit only those three files.
7. Re-run all 15 root structural checks on committed bytes. Only after 15/15,
   stable bytecode, absent attempt-004 path, absent index lock, and final Git
   preflight may the parent attempt-004 transaction start.

No global timeout, registry membership, cache authority, destination class,
contract-kernel component membership, controller watch scope, or retry path is
widened here.
