# v0.43 C2 atomic PID-handoff smoke repair C0 addendum

**Status:** approved package-maintainer authority to replace polling over
non-atomic test PID publication with a complete atomic handoff protocol. This
record must be committed alone before the affected smoketest byte is edited.
It grants no full-corpus, package, shipment, cache, catalog, fresh-host,
consumer, research, acceptance, promotion, release, activation, or canon
authority.

**Run scope:** `adhoc_review`.

**Parent authorities:**

- `docs/superpowers/specs/2026-08-03-v043-c2-partial-pid-handoff-c0-addendum.md`;
- `docs/superpowers/specs/2026-08-03-v043-c2-second-pid-handoff-c0-addendum.md`.

All parent path, retry, sequencing, red-preservation, and no-claim boundaries
remain binding.

## Independent-review blocker

The shared strict PID reader removed both raw existence-then-parse sites, but
independent review correctly rejected the remaining protocol: retrying a
noncanonical value could mask a corrupt publication, while a canonical digit
prefix could be accepted before a non-atomic `Path.write_text` completed.
Polling stability is not completion evidence. No source qualification or
shipment action was started and no prior red was relabeled.

## Exact authority

Authority is limited to `scripts/release_qualification_controller_smoketest.py`
at the frozen preimage 197,326 bytes, SHA-256
`f840b38de26d42a6b6f6951709f565f6d44a69f51fd72eed481b677d0a34da1d`.
The two affected synthetic child programs must write canonical positive PID
ASCII to a same-directory temporary sibling and atomically replace the final
handoff path. The reader may retry only final-path absence until its fixed
monotonic deadline. Once the final path exists, any other `OSError`, non-ASCII
byte, empty value, zero, sign, whitespace, leading zero, punctuation, or other
noncanonical content must fail immediately and report the exact raw observation
where available. A canonical positive integer may then return immediately
because atomic publication is the completion boundary.

No production controller, fixture supervisor, runner, registry, kernel,
projection, profile, schema, manifest, package, cache, or consumer byte may
change. Focused tests must prove missing-path timeout, immediate invalid-byte
refusal, canonical acceptance, both real atomic handoffs, sequential and
parallel Windows modes, WSL/POSIX behavior, and zero residue. Three independent
exact-byte reviews must return clean before the six-path repair commit and
source attempt 019.
