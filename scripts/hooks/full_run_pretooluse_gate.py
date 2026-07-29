#!/usr/bin/env python3
"""full_run_pretooluse_gate - scoped hook enforcement of FULL_RUN_CONTRACT.

WHERE THIS FIRES
----------------
This hook is honoured by the Claude Code CLI and the Claude Agent SDK, where
plugin-scoped PreToolUse hooks run. Cowork support is not claimed: an earlier
desktop build was observed spawning the CLI with ``--setting-sources user``
and not discovering plugin hooks (anthropics/claude-code#27398). Use the
DETECTION path there unless the current host is verified independently:
``scripts/full_run_completeness_report.py``.

ACTIVATION
----------
The driver must declare the parent scope in ``FRC_PARENT_SCOPE``.  Without that
declaration this hook is inert; a global plugin hook cannot infer whether an
ordinary coding subagent call belongs to an academic lifecycle.  The CLI/SDK
driver that starts a full run sets ``FRC_PARENT_SCOPE=full_lifecycle`` (or
``adhoc_review``).  Scope is never guessed from the child brief.

WHAT IT DOES
------------
It reads hook JSON on stdin and, while an explicit parent scope is active,
delegates decisions to ``scripts/full_run_contract_check.py``:

  Write / Edit / MultiEdit into a manuscript/ tree
        -> `authorize --run-scope full_lifecycle` for the enclosing project.
           A refusal (e.g. FRC-NO-PROJECT) denies the write. This is the exact
           "essay written with no project" failure of 2026-07-17/18.

  Task / Agent (subagent dispatch; host naming varies)
        -> `scope --parent-scope <declared parent> --child-brief <the prompt>`.
           A scope-downgrade / undeclared brief is denied (FRC-SCOPE-*).

  Stop (terminal language in the final response)
        -> `terminal --project-root <current project>`.  An unearned terminal
           claim blocks the stop and returns the authoritative finding.

Everything else is allowed. The hook never re-implements contract logic; it
composes the authoritative gate and passes its finding through as the reason.

BLOCK CONTRACT
--------------
On a refusal it prints, per the Claude Code hooks spec:
  {"hookSpecificOutput": {"hookEventName": "PreToolUse",
    "permissionDecision": "deny", "permissionDecisionReason": "<gate finding>"}}
and exits 0 (the decision travels in the JSON, not the exit code).

FAIL MODE
---------
When no scope is active, internal errors fail open because this plugin also runs
in ordinary coding sessions.  Once a scope is explicitly active, a missing gate
or internal error fails closed: absence of a verdict is not permission to write
academic prose or claim terminal completion.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
import destination_capability as destination  # noqa: E402
import invocation_scope as invocation  # noqa: E402

# Resolve the authoritative gate: prefer the plugin root the host injects.
_PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT")
if _PLUGIN_ROOT:
    GATE = Path(_PLUGIN_ROOT) / "scripts" / "full_run_contract_check.py"
else:
    GATE = Path(__file__).resolve().parents[1] / "full_run_contract_check.py"

ACTIVE_SCOPE_ENV = "FRC_PARENT_SCOPE"
SCOPES = set(invocation.SCOPES)
MANUSCRIPT_DIR = "manuscript"
TERMINAL_MARKERS = (
    "ladder complete", "terminal pass", "lifecycle complete",
    "terminal_phase_reached", "g.4", "converged", "shipped",
)


def _allow() -> int:
    # Silence = allow. Exit 0, no JSON.
    return 0


def _deny(reason: str) -> int:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}))
    return 0


def _block_stop(reason: str) -> int:
    print(json.dumps({"decision": "block", "reason": reason}))
    return 0


def _active_parent_scope() -> str | None:
    scope = os.environ.get(ACTIVE_SCOPE_ENV, "").strip().lower()
    return scope if scope in SCOPES else None


def _first_finding(gate_stdout: str) -> str:
    try:
        data = json.loads(gate_stdout)
        f = (data.get("findings") or [{}])[0]
        code = f.get("code", "FRC-REFUSED")
        msg = f.get("message", "full-run contract refusal")
        return f"[{code}] {msg}"
    except Exception:
        return gate_stdout.strip() or "full-run contract refusal"


def _run_gate(*gate_args: str) -> tuple[int, str]:
    proc = subprocess.run([sys.executable, str(GATE), *gate_args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode, proc.stdout or proc.stderr


def _find_project_root(start: Path) -> Path | None:
    for d in [start, *start.parents]:
        if (d / "reviews" / "phase_state.json").is_file() or \
           (d / "reviews" / "assignment_contract.json").is_file():
            return d
    return None


def _path_from_input(path_str: str, cwd: str | None = None) -> Path:
    """Resolve tool paths without making slash spelling part of enforcement."""
    normalized = path_str.replace("\\", "/")
    path = Path(normalized)
    if not path.is_absolute() and cwd:
        path = Path(cwd) / path
    return path


def _is_manuscript_path(path_str: str) -> bool:
    parts = [part.casefold() for part in path_str.replace("\\", "/").split("/")]
    return MANUSCRIPT_DIR in parts


def _handle_write(tool_input: dict, *, cwd: str | None = None) -> int:
    scope = _active_parent_scope()
    if scope is None:
        return _allow()
    path_str = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not path_str:
        return _allow()
    p = _path_from_input(path_str, cwd)
    if scope == invocation.LAB_ITERATION:
        try:
            destination_kind = destination.classify(p)
        except (OSError, RuntimeError, ValueError):
            destination_kind = "unresolved"
        if destination_kind in {"staging", "shipment"}:
            return _allow()
        return _deny(
            "[FRC-LAB-LIFECYCLE-FORBIDDEN] lab_iteration is proposal-only; "
            "direct writes are permitted only in governed staging or an exact "
            "private shipment lane"
        )
    if not _is_manuscript_path(path_str):
        return _allow()  # ordinary code/config writes are out of scope
    root = _find_project_root(p.parent if p.parent != p else p)
    if root is None:
        # manuscript prose with no enclosing project -> the canonical failure
        rc, out = _run_gate("authorize", "--project-root", str(p.parent),
                            "--run-scope", scope)
        return _deny(_first_finding(out)) if rc != 0 else _allow()
    rc, out = _run_gate("authorize", "--project-root", str(root),
                        "--run-scope", scope)
    return _deny(_first_finding(out)) if rc != 0 else _allow()


def _handle_agent(tool_input: dict) -> int:
    parent_scope = _active_parent_scope()
    if parent_scope is None:
        return _allow()
    brief = tool_input.get("prompt") or tool_input.get("description") or ""
    if not brief.strip():
        return _deny("[FRC-SCOPE-UNDECLARED] active lifecycle subagent dispatch "
                     "has no prompt carrying a run_scope declaration")
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                     encoding="utf-8") as fh:
        fh.write(brief)
        brief_path = fh.name
    try:
        rc, out = _run_gate("scope", "--parent-scope", parent_scope,
                            "--child-brief", brief_path)
    finally:
        try:
            os.unlink(brief_path)
        except OSError:
            pass
    return _deny(_first_finding(out)) if rc != 0 else _allow()


def _handle_stop(payload: dict) -> int:
    scope = _active_parent_scope()
    if scope is None:
        return _allow()
    message = payload.get("last_assistant_message") or ""
    low = " ".join(message.casefold().split())
    if not any(marker in low for marker in TERMINAL_MARKERS):
        return _allow()
    if scope == invocation.LAB_ITERATION:
        return _block_stop(
            "[FRC-LAB-TERMINAL-FORBIDDEN] lab_iteration cannot make a terminal, "
            "shipment, convergence, or lifecycle-complete claim"
        )
    cwd = payload.get("cwd") or os.getcwd()
    root = _find_project_root(Path(cwd)) or Path(cwd)
    rc, out = _run_gate("terminal", "--project-root", str(root))
    return _block_stop(_first_finding(out)) if rc != 0 else _allow()


def main() -> int:
    if os.environ.get("FRC_GATE_HOOK_DISABLE"):
        return _allow()
    active_scope = _active_parent_scope()
    try:
        payload = json.load(sys.stdin)
    except Exception as e:
        reason = f"[FRC-HOOK-ERROR] unreadable hook payload: {e}"
        print(f"full_run_pretooluse_gate: {reason}", file=sys.stderr)
        return _allow() if active_scope is None else _deny(reason)
    if not GATE.is_file():
        reason = f"[FRC-GATE-UNAVAILABLE] authoritative gate missing at {GATE}"
        print(f"full_run_pretooluse_gate: {reason}", file=sys.stderr)
        if active_scope is None:
            return _allow()
        if payload.get("hook_event_name") == "Stop":
            return _block_stop(reason)
        return _deny(reason)
    try:
        if payload.get("hook_event_name") == "Stop":
            return _handle_stop(payload)
        tool = payload.get("tool_name", "")
        tool_input = payload.get("tool_input", {}) or {}
        if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
            return _handle_write(tool_input, cwd=payload.get("cwd"))
        if tool in ("Task", "Agent"):
            return _handle_agent(tool_input)
        return _allow()
    except Exception as e:
        reason = f"[FRC-HOOK-ERROR] internal hook error: {e}"
        print(f"full_run_pretooluse_gate: {reason}", file=sys.stderr)
        if active_scope is None:
            return _allow()
        if payload.get("hook_event_name") == "Stop":
            return _block_stop(reason)
        return _deny(reason)


if __name__ == "__main__":
    sys.exit(main())
