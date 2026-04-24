# Legacy — rule-digest scripts (v0.5.3 → v0.6.0, retired at v0.7.0)

## What this is

This directory preserves `scripts/build_rule_digest.py` and `scripts/verify_rule_digest.py` exactly as they shipped at v0.6.0. Both scripts were added at v0.5.3 (Phase D.2) to close the integrity contract declared by `GROUNDING_PROTOCOL.md` Rule 1's tier-gated digest exception: agents dispatching at T1 (and at v0.5.5 also at T2) could consult a pre-computed rule-digest instead of reading the full rule-files, provided the digest's hash verified against the source files at release time. The release-gate's Phase 0.65 build-and-verify block was the closing half of that contract.

## Why it was retired

v0.7.0 retires the tier-gated digest exception wholesale. The reasons are recorded in `CHANGELOG.md` v0.7.0, `RELEASE_NOTES_v0.7.0.md`, and `references/TIER_PROTOCOL.md §11`:

- The two-law grounding regime (digest-at-T1, full-file-elsewhere) bifurcated every Evaluator rule citation and produced a class of handoff-time hallucinations at the T1→T2 seam.
- Full-file reads at every rung are a simpler, safer, single-code-path grounding floor.
- With no live consumer for the digest, the build-and-verify release-gate phase became a dead limb.

## What v0.7.0 ships instead

- `references/GROUNDING_PROTOCOL.md §§38–50` — Rule 1 is rewritten to declare full-file reads the universal floor; the tier-gated exception is removed.
- `scripts/release-gate.sh` Phase 0.65 is preserved as a no-op placeholder (`[SKIP]`) to keep the phase-number contract stable across release-gate invocations.
- Agents' Phase 3a (Digest Integrity) in the Reflector is retired; see `agents/reflector.md`.

## Keeping the scripts readable

The two archived scripts are left executable and unmodified. They import only the Python standard library, so a maintainer auditing the v0.5.3 → v0.6.0 contract can still `python3 build_rule_digest.py --help` and `python3 verify_rule_digest.py --help` to inspect the CLI surface and the digest format.
