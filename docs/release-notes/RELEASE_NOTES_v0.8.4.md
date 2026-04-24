# Release Notes — co-author-harness-claude v0.8.4

**Date:** 2026-04-24

## Summary

Closes the **v0.8.1 plugin-update proposals (A6–A9)**: **§9d** deterministic prefilter (`scripts/check8_g_prefilter.py`), **A8** path resolution (`scripts/provenance_prewrite_check.py` + Planner §3a), **A6** Reflector **§2g.1a** (§9d G-candidate scale), **A7** `references/ADVISORY_UNTIL_SCOPING.md`, plus documentation (`phase_notifications` canonical name), full `.plugin-efficiency.json` `role_overrides`, and `### Skills (27)` README catalog parity. See `CHANGELOG.md` §v0.8.4.

## Build

```bash
./scripts/build-release-zip.sh /path/to/co-author-harness 0.8.4
```

Output: `releases/co-author-harness-claude-v0.8.4.zip` (Claude / Cowork plugin loader format).

## Upgrade / migration

- No schema or `phase_state.json` change. Adopt the new scripts when you run full-manuscript Ph3/Ph4 accessibility passes (run §9d before `accessibility-overlay` Sub-check G when you want the deterministic seed).
- `reviews/plugin_update_proposals.md` v0.8.4 section records A6–A9 **IMPLEMENTED** for this cut.
