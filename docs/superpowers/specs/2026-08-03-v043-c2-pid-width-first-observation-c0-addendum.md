# v0.43 C2 PID-width and first-observation C0 addendum

**Status:** approved package-maintainer authority for two strict-reader boundary
defects found by final adversarial review. Commit this record alone before the
affected smoketest byte is edited. It grants no full-corpus, package, shipment,
cache, catalog, fresh-host, consumer, research, acceptance, promotion, release,
activation, or canon authority.

**Run scope:** `adhoc_review`.

**Parent authority:**
`docs/superpowers/specs/2026-08-03-v043-c2-atomic-pid-handoff-c0-addendum.md`.
All parent sequencing, path, retry, red-preservation, and no-claim boundaries
remain binding.

## Exact finding and authority

The atomic two-producer/two-consumer protocol and ordinary invalid inputs were
clean, but independent review reproduced two adversarial edges:

1. Python 3.14 can raise its own `ValueError` when converting a published
   thousands-of-digits ASCII value, bypassing the required path/raw diagnostic.
2. A sub-millisecond diagnostic timeout could be preempted before the loop's
   first read, yielding no actual first observation.

Authority is limited to `scripts/release_qualification_controller_smoketest.py`
at the frozen preimage 198,184 bytes, SHA-256
`26d1793fcc96717bc3094200c1ce8ed121bf1bff2a4f982a8c6552397ffb31bb`.
The helper must always attempt at least one read, reject more than ten PID
digits before integer conversion, reject values outside the unsigned 32-bit
Windows PID surface, and retain the exact path/raw bytes in every published
invalid-value refusal. The regression must include an overlong digit-only
value. No other source, binding, manifest, package, cache, or consumer byte may
change.

Afterward rerun strict-helper probes, sequential and parallel Windows modes,
WSL/POSIX, native/WSL text policy, binding/structural checks as affected, exact
residue checks, and three final exact-byte reviews. Any new finding is a stop;
source attempt 019 remains closed until the reviewed six-path repair commit.
