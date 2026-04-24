# Release Notes — co-author-harness-claude v0.8.3

**Date:** 2026-04-24

## Summary

This point release **rebrands** the package and repository only. The plugin manifest `name` is now `co-author-harness-claude` (replacing `research-writing-harness-claude`). The canonical checkout directory is `co-author-harness/`. Release zips built with `scripts/build-release-zip.sh` are named `co-author-harness-claude-v<version>.zip`.

There are **no** changes to skills, agents, schemas, slash commands, or runtime behaviour relative to v0.8.2.

## Upgrade / migration

- **Folder on disk:** Rename your local clone from `research-writing-harness` to `co-author-harness` when convenient (close editors holding the folder first).
- **Claude Code / Cowork:** Install or update using the new plugin id `co-author-harness-claude` and the v0.8.3 zip if your environment keys off manifest `name`.
- **Historical zips** (`research-writing-harness-claude-v0.8.2.zip`, etc.) remain valid artifacts; this release does not invalidate their contents, but new builds use the new filename pattern.

## Build

```bash
./scripts/build-release-zip.sh /path/to/co-author-harness 0.8.3
```

See `CHANGELOG.md` §v0.8.3 for the full entry.
