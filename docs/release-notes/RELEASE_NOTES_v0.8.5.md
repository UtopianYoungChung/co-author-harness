# Release Notes — co-author-harness-claude v0.8.5

**Date:** 2026-04-24

## Summary

Adds **wiki-first resource order** for wiki-linked projects: peer `LLM wiki/` (sources, concepts, syntheses, graph report, optional `/llm-wiki-query`) before new Zotero PDFs and external discovery tools, with a logged **Wiki-first** trace in `reviews/revision_plan.md` / `manuscript/revision_log.md`. Grounding Rule 7a **resolution** order for existing citations is unchanged; **§1.5** governs **discovery** only. See `CHANGELOG.md` §v0.8.5.

## Build

```bash
./scripts/build-release-zip.sh /path/to/co-author-harness 0.8.5
```

Output: `releases/co-author-harness-claude-v0.8.5.zip` (Claude / Cowork plugin loader format).

## Upgrade / migration

- No schema or `phase_state.json` change. Opt out per project with `wiki_first_resources: false` in the Wiki linkage section (`PROJECT_BOOTSTRAP.md` §3 Step 5).
