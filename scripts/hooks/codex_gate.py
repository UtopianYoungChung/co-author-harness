#!/usr/bin/env python3
"""Translate Codex hook events to the existing harness gate, without writing.

Only the documented apply_patch/command and spawn_agent/message shapes are
adapted. This does not guard shell writes, arbitrary MCP writes, or host paths
that skip hooks. Host hook trust and per-run scope/session binding are required.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
from pathlib import Path

try:
    import full_run_pretooluse_gate as gate
except Exception as exc:
    # Codex treats exit 2 as blocking; other launch failures may fail open.
    print(f'[FRC-CODEX-HOOK-ERROR] cannot load the authoritative gate: {exc}', file=sys.stderr)
    raise SystemExit(2) from exc


def patch_paths(command: str) -> list[str]:
    """Collect every add/update/delete/move target; never inspect hunk contents."""
    if not isinstance(command, str):
        raise ValueError('apply_patch requires tool_input.command text')
    lines = command.strip().splitlines()
    if len(lines) < 2 or lines[0] != '*** Begin Patch' or lines[-1] != '*** End Patch':
        raise ValueError('unrecognized patch envelope')
    paths = []
    for line in lines[1:-1]:
        for prefix in ('*** Add File: ', '*** Update File: ', '*** Delete File: ', '*** Move to: '):
            if line.startswith(prefix):
                path = line[len(prefix):].strip()
                if not path or '\x00' in path:
                    raise ValueError('empty or invalid patch target')
                paths.append(path)
                break
    if not paths:
        raise ValueError('patch has no file targets')
    return list(dict.fromkeys(paths))


def invoke(payload: dict) -> dict:
    """Capture legacy output so one multi-file call emits exactly one decision."""
    previous = sys.stdin
    output = io.StringIO()
    try:
        sys.stdin = io.StringIO(json.dumps(payload))
        with contextlib.redirect_stdout(output):
            gate.main()
    finally:
        sys.stdin = previous
    return json.loads(output.getvalue()) if output.getvalue().strip() else {}


def evaluate(payload: dict) -> dict:
    if os.environ.get('FRC_GATE_HOOK_DISABLE'):
        return {}
    if not isinstance(payload, dict):
        raise ValueError('hook payload must be an object')
    if payload.get('hook_event_name') == 'Stop':
        return invoke(payload)
    tool = payload.get('tool_name')
    data = payload.get('tool_input') or {}
    if tool == 'apply_patch':
        paths = patch_paths(data.get('command'))
        cwd = Path(payload.get('cwd') or os.getcwd())
        for path in paths:
            # Check the normalized target, including moves and deletes.
            target = Path(path)
            target = (cwd / target).resolve() if not target.is_absolute() else target.resolve()
            decision = invoke({**payload, 'tool_name': 'Write', 'tool_input': {'file_path': str(target)}})
            if decision:
                return decision
        return {}
    if tool == 'spawn_agent':
        message = data.get('message')
        if not isinstance(message, str) or not message.strip():
            raise ValueError('spawn_agent requires a nonempty message')
        return invoke({**payload, 'tool_name': 'Agent', 'tool_input': {'prompt': message}})
    return invoke(payload)


def main() -> int:
    payload = {}
    try:
        payload = json.load(sys.stdin)
        decision = evaluate(payload)
    except Exception as exc:
        reason = f'[FRC-CODEX-HOOK-ERROR] {type(exc).__name__}: {exc}'
        if isinstance(payload, dict) and payload.get('hook_event_name') == 'Stop':
            decision = {'decision': 'block', 'reason': reason}
        else:
            decision = {'hookSpecificOutput': {'hookEventName': 'PreToolUse',
                        'permissionDecision': 'deny', 'permissionDecisionReason': reason}}
    # Codex Stop requires JSON even when the legacy hook allows with no output.
    print(json.dumps(decision))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
