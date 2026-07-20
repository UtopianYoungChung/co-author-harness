---
name: run-finalize
description: Public finalize-stage entrypoint; legacy /run-phase-4 remains a compatibility route.
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/run-finalize/SKILL.md` and follow it as the binding public router. It delegates the full Ph4 implementation to the legacy-compatible `skills/run-phase-4/SKILL.md` body.

If `${CLAUDE_PLUGIN_ROOT}` does not resolve in this host, fall back to `skills/run-finalize/SKILL.md` from the workspace root the user opened.
