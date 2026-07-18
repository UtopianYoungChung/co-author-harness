# Release Notes — co-author-harness-claude v0.8.6

**Date:** 2026-04-25

## Summary

- **Advisor MCP** — `references/ADVISOR_MCP.md` defines EP-1 (post-Ph2, pre-Ph3) and EP-2 (post-Ph3_converged, pre-MCR/Ph4) for plugin-bridged external feedback; `advisor-escalation` and `PHASE_PROTOCOL` updated accordingly.
- **Em-dash** — `agents/generator.md` applies the same discipline to **fix-application** rounds as to new writing; `MASTER` / `research_paper_writing_guidelines` / `sentence-level-pass` aligned.
- **Release gate** — `scripts/plugin_calibrator_audit.py` supplies `audit-package-speed --json` when the external `plugin-calibrator` CLI is absent; `accessibility-overlay` `SKILL.md` `description` trimmed under the 500-char gate.

See `CHANGELOG.md` §v0.8.6.

## Build

```bash
./scripts/build-release-zip.sh /path/to/co-author-harness 0.8.6
```

Output: `releases/co-author-harness-claude-v0.8.6.zip` (Claude / Cowork plugin loader format).

## Upgrade / migration

- No `phase_state.json` or trigger-enum change.
