---
name: run-phase-1
description: Legacy compatibility route to public /run-draft; preserves the full Ph1 implementation body.
---

Compatibility entrypoint: read `${CLAUDE_PLUGIN_ROOT}/skills/run-phase-1/SKILL.md`, follow its binding Ph1 implementation, and present `/run-draft` as the public stage name.

If `${CLAUDE_PLUGIN_ROOT}` does not resolve in this host, fall back to `skills/run-phase-1/SKILL.md` from the workspace root the user opened.
