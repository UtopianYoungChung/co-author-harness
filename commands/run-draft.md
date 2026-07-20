---
name: run-draft
description: Public draft-stage entrypoint; legacy /run-phase-1 remains a compatibility route.
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/run-draft/SKILL.md` and follow it as the binding public router. It delegates the full Ph1 implementation to the legacy-compatible `skills/run-phase-1/SKILL.md` body.

If `${CLAUDE_PLUGIN_ROOT}` does not resolve in this host, fall back to `skills/run-draft/SKILL.md` from the workspace root the user opened.
