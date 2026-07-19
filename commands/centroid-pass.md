---
name: centroid-pass
description: On-demand single-centroid Eric-Yu domain-native register pass (write/review/revise) run against a manuscript scope outside the automatic phase/milestone path. Advisory dry-run by default; --apply commits write/revise through the Generator. Overrides the M1–M3 assignment-scope fence with an explicit APG-EXEMPLAR-M4-FENCE-BYPASSED advisory. Falls back to the package-pinned centroid when the project is unbound; never re-pins and never writes phase_state.json.
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/centroid-pass/SKILL.md` and follow it as the binding instruction set for this invocation. Treat that file as the authority for invocation syntax, mode semantics (write / review / revise / all), the milestone override-with-warning posture, the advisory-default / `--apply` output contract, the package-default binding fallback, the C-7 fence and argument-only invariants, and the output artefact format.

If `${CLAUDE_PLUGIN_ROOT}` does not resolve in this host, fall back to `skills/centroid-pass/SKILL.md` from the workspace root the user opened.
