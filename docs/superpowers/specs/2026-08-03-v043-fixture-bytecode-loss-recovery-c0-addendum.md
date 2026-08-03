# v0.43 fixture bytecode-loss recovery C0 addendum

**Status:** approved package-maintainer recovery boundary for one exact ignored
bytecode identity accidentally removed during authorized review. This record
does not retroactively make the deletion authorized. It grants no C2
qualification, version, package clearance, shipment, cache mutation, consumer
re-attestation, host qualification, activation, research mutation, acceptance,
promotion, release, or canon authority.

**Run scope:** `adhoc_review`.

**Parent authorities:**

- `docs/superpowers/specs/2026-08-03-v043-c2-controller-review-bytecode-cleanup-c0-addendum.md`;
- `docs/superpowers/specs/2026-08-03-v043-linux-kernel-containment-c0-addendum.md`.

## Frozen incident

During the final Linux-containment repair, an agent ran `py_compile` on the
modified supervisor and infrastructure check, then removed both emitted cache
files. The supervisor cache was newly created. The infrastructure cache had
already existed in the governed primary baseline; compiling overwrote it and
removal then deleted the path. That deletion was outside the exact cleanup
ledger and is preserved as a review-process defect.

The immutable attempt-016 intent at
`C:\Users\young\AppData\Local\Temp\coauthor-v043-qualification-20260803-attempt-016\intent.json`
records the 180-file primary bytecode preimage. Exact comparison against the
current primary tree proves:

- baseline: 180 `.pyc` files and four `__pycache__` directories;
- current: 179 `.pyc` files and the same four directories;
- added identities: zero;
- changed identities: zero;
- missing identities: exactly one:
  `scripts/analysis/__pycache__/fixture_infrastructure_check.cpython-314.pyc`,
  46,647 bytes, SHA-256
  `89e91f8e620b227c969610749e1298a109517f9406d36ca933fd85dc7327718d`.

The lost bytes are an ignored interpreter cache for an older source postimage,
not source, package, fixture evidence, qualification evidence, or release
content. No exact copy exists under `B:\Agents`; synthesizing a different `.pyc`
and presenting it as the frozen identity is forbidden.

## Recovery disposition

The exact remaining 179 identities and four directories become the governed
primary bytecode baseline for this repair. This is a one-identity subtraction,
not permission to regenerate caches or normalize other ignored state. All
future pre/post checks must prove zero added, changed, or removed identities
against the attempt-016 inventory minus the one exact row above. Python tests
must continue to use both `-B` and ambient `PYTHONDONTWRITEBYTECODE=1`.

## Exact writable ledger

| Action | Path | Preimage bytes | Preimage SHA-256 |
|---|---|---:|---|
| CREATE | `docs/superpowers/specs/2026-08-03-v043-fixture-bytecode-loss-recovery-c0-addendum.md` | 0 | `ABSENT` |

No bytecode creation, deletion, or modification is authorized by this
addendum. Before the final repair commit and every qualification transaction,
recompare the live tree to the frozen attempt-016 inventory minus the one row,
require exact 179/4 equality, and require zero live fixture/controller/systemd
identities. Any further bytecode drift is a stop. All later gates remain closed.
