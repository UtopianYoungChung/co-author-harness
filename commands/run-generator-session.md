---
description: Session-sourced Generator — apply the current session's agreed revision instructions to manuscript/* under the real current_phase from reviews/phase_state.json
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/run-generator-session/SKILL.md` and follow it as the binding instruction set for this invocation. Treat that file as the authority for trigger conditions, gates, finding format, and exit conditions.

If `${CLAUDE_PLUGIN_ROOT}` does not resolve in this host, fall back to `skills/run-generator-session/SKILL.md` from the workspace root the user opened.
