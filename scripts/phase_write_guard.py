#!/usr/bin/env python3
"""
PreToolUse hook: warn when phase_state.json or .harness/ artefacts are
written without going through the proper subagent dispatch.

This is a non-blocking reminder. The agent sees the stderr message before
the write proceeds, surfacing the grounding obligation without hard-blocking
legitimate subagent writes.

To enforce blocking: change sys.exit(0) to sys.exit(1) and update the
message to explain why the write was blocked.
"""
import json
import sys

# Normalise to forward slashes before matching so Windows backslash paths
# (e.g. "reviews\\.harness\\evidence\\x.json") match correctly.
GUARDED_PATTERNS = [
    "phase_state.json",
    "reviews/.harness/evidence",
    "reviews/.harness/events.jsonl",
]

REMINDER = """
[HARNESS-GUARD] Writing to a guarded harness artefact: '{path}'

Before proceeding, confirm:
  1. This write is from a dispatched co-author-harness-claude:evaluator or
     co-author-harness-claude:planner subagent - not the main conversation loop.
  2. The following files were read in-session (Grounding Protocol Rule 1):
       references/GROUNDING_PROTOCOL.md
       references/REVIEW_ORCHESTRATION.md
       references/PHASE_PROTOCOL.md
       references/SAFEGUARD_LAYER.md
       agents/evaluator.md  (full read)
  3. If this is a Ph3 iterate/converge round: reviews/convergence_journal.jsonl
     has a fresh entry for this round. (Not required for Ph1/Ph2 or Planner
     Phase 0 preflight writes.)

If checks 1-2 are not satisfied, void this round and re-dispatch via the
proper co-author-harness-claude:planner -> co-author-harness-claude:evaluator
subagent chain. See CLAUDE.md "Agent dispatch guardrail" section.
""".strip()


def main() -> None:
    try:
        tool_call = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    params = tool_call.get("tool_input", {})
    raw_path = str(params.get("file_path", "") or params.get("path", ""))
    normalised = raw_path.replace("\\", "/")

    if any(pattern in normalised for pattern in GUARDED_PATTERNS):
        print(REMINDER.format(path=raw_path), file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
