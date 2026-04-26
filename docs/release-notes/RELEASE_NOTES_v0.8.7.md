# Release Notes — co-author-harness-claude v0.8.7

**Date:** 2026-04-25

## Summary

- **`/run-generator-session`** — SK-32: apply current-session chat as revision instructions under real `reviews/phase_state.json` + `reviews/classification.md`; Generator authority per `agents/generator.md`; writes `manuscript/*` and `manuscript/revision_log.md` only. Design: `docs/superpowers/specs/2026-04-25-generator-session-revision-design.md`.

See `CHANGELOG.md` §v0.8.7.

## Build

```bash
./scripts/build-release-zip.sh /path/to/co-author-harness 0.8.7
```

Output: `releases/co-author-harness-claude-v0.8.7.zip` (Claude / Cowork plugin loader format).

## Upgrade / migration

- No `phase_state.json` or trigger-enum change.
