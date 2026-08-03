# v0.43 C2 second PID-handoff smoke repair C0 addendum

**Status:** approved package-maintainer authority to close the one remaining
raw PID-handoff read found by independent adversarial review. This record must
be committed alone before the affected test byte is edited. It grants no
full-corpus, package, shipment, cache, catalog, fresh-host, consumer, research,
acceptance, promotion, release, activation, or canon authority.

**Run scope:** `adhoc_review`.

**Parent authority:**
`docs/superpowers/specs/2026-08-03-v043-c2-partial-pid-handoff-c0-addendum.md`.
All parent path, retry, sequencing, red-preservation, and no-claim boundaries
remain binding.

## Review finding and exact authority

The first partial-handoff repair passed bare-host Windows, fixture-owner
Windows, controlled parallel Windows stress, WSL/POSIX, text-policy, structural,
kernel, projection, and compatibility checks. Those passes are provisional,
not qualification or shipment authority.

Independent exact-byte review then found one remaining instance of the same
race class: the launch-handle cleanup regression waited only for
`launch-close-descendant.ready` to exist and then parsed it directly with
`int(read_text(...))`. A created-but-empty or partially written file could
therefore make the test nondeterministic. No failure was relabeled and no
qualification transaction was started.

Authority is limited to replacing that exact existence-only loop and direct
parse in `scripts/release_qualification_controller_smoketest.py` with the
already-reviewed `_wait_for_positive_pid(..., timeout_s=5)` helper. The frozen
preimage is 197,576 bytes, SHA-256
`e17be269724cb6b344bf75b4365598efb4aaf8790f585b9f9206e9e565474d70`.
No other source, binding, manifest, package, cache, or consumer byte may change.

Before source attempt 019 opens, mechanically prove there are no remaining raw
existence-then-integer PID handoff reads, rerun the focused Windows sequential
and parallel modes, WSL/POSIX, native/WSL text-policy and structural/binding
gates, prove exact bytecode/process cleanliness, and obtain three clean
independent exact-byte reviews. Any further finding is another stop.
