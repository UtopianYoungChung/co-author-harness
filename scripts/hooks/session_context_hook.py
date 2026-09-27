#!/usr/bin/env python3
"""session_context_hook - put the grounding floor into every harness context.

WHERE THIS FIRES
----------------
Claude Code runs it on ``SessionStart`` (startup, resume, clear and compact)
and on ``SubagentStart``. Claude Code does not load a plugin's ``AGENTS.md``,
so without this hook ``references/GROUNDING_PROTOCOL.md`` reaches a session
only when a model decides to read it.

WHAT IT ADDS
------------
It prints hook JSON whose ``additionalContext`` carries:

  * the package root, and the rule that ``scripts/...`` and ``references/...``
    paths in the package's own files resolve against it, not the project;
  * the protocol's quick reference card, read from the protocol file on every
    run so the injected text cannot drift from it;
  * for a harness subagent only, the ``agent_id`` the host assigned. A child
    cannot otherwise see it, and a project-independent result must report it
    as ``agent_execution_id`` (``references/CLAUDE_CODE_HOST.md``);
  * for the main session, the drafting coordinator's host object, built from
    the ``transcript_path`` the host reports. A model cannot otherwise know
    where its own session log is, and a live run that guessed wrong gave up
    on certification altogether.

Subagents of other plugins, and the host's own, receive nothing.
``COAUTHOR_SESSION_CONTEXT_DISABLE=1`` turns the hook off.

The hook never blocks: a session must start even if the protocol file is
unreadable. It then injects a pointer to the file instead of the card and
reports the fault on stderr.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PLUGIN_NAME = "co-author-harness"
PROTOCOL_REL = "references/GROUNDING_PROTOCOL.md"
CARD_HEADING = "## Quick reference card"


def package_root() -> Path:
    declared = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if declared:
        return Path(declared)
    return Path(__file__).resolve().parent.parent.parent


def quick_reference_card(root: Path) -> str | None:
    """Return the protocol's quick reference card, or None if it cannot be read."""
    try:
        text = (root / PROTOCOL_REL).read_text(encoding="utf-8")
    except OSError:
        return None
    start = text.find(CARD_HEADING)
    if start < 0:
        return None
    body = text[text.index("\n", start) + 1:]
    end = body.find("\n---")
    card = (body if end < 0 else body[:end]).strip()
    return card or None


def context_for(event: str, payload: dict, root: Path) -> str | None:
    agent_id = None
    if event == "SubagentStart":
        agent_type = str(payload.get("agent_type") or "")
        if not agent_type.startswith(PLUGIN_NAME + ":"):
            return None
        agent_id = payload.get("agent_id")
    elif event != "SessionStart":
        return None

    parts = [
        f"{PLUGIN_NAME} package root: {root}",
        "Paths such as `scripts/...` and `references/...` in this package's skills, "
        "agents and references resolve against that root, not the project: run "
        f'package scripts as `python "{root}/scripts/..."` from the project directory.',
    ]
    card = quick_reference_card(root)
    if card is None:
        print(f"session_context_hook: could not read the quick reference card in {root / PROTOCOL_REL}",
              file=sys.stderr)
        parts.append(
            "Grounding floor: whenever you draft, review or cite academic prose with this "
            f"package, read {root / PROTOCOL_REL} in full first; its rules are absolute."
        )
    else:
        parts.append(
            "Grounding floor, absolute whenever you draft, review or cite academic prose "
            f"with this package ({PROTOCOL_REL}; read it in full before any citation verdict):\n"
            + card
        )
    if agent_id:
        parts.append(
            f"Host execution identity: your agentId is {agent_id}. When a request asks for "
            "your own agent_execution_id, report exactly this value."
        )
    transcript = payload.get("transcript_path")
    if event == "SessionStart" and isinstance(transcript, str) and transcript.endswith(".jsonl"):
        host = {"adapter": "claude-code-jsonl", "subagents_available": True,
                "logs_root": str(Path(transcript).parent), "parent_log": transcript}
        parts.append(
            "Drafting coordinator host object for this session (`piw_coordinator.py start` "
            "`request.host`; references/CLAUDE_CODE_HOST.md): "
            + json.dumps(host)
            + ". Set subagents_available to false if this session has no Agent tool."
        )
    return "\n\n".join(parts)


def main() -> int:
    if os.environ.get("COAUTHOR_SESSION_CONTEXT_DISABLE") == "1":
        return 0
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    event = str(payload.get("hook_event_name") or "")
    context = context_for(event, payload, package_root())
    if context is None:
        return 0
    json.dump({"hookSpecificOutput": {"hookEventName": event, "additionalContext": context}},
              sys.stdout, ensure_ascii=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
