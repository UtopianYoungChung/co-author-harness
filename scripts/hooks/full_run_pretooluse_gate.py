#!/usr/bin/env python3
"""full_run_pretooluse_gate - scoped hook enforcement of FULL_RUN_CONTRACT.

WHERE THIS FIRES
----------------
This hook is honoured by the Claude Code CLI and the Claude Agent SDK, where
plugin-scoped PreToolUse hooks run. Cowork and Cursor coverage are not claimed.

ACTIVATION
----------
The driver must declare the parent scope in ``FRC_PARENT_SCOPE``.
Known scopes: adhoc_review, project_independent, lab_iteration, full_lifecycle.
The hook process inherits the host's environment, so the scope is set before
the host starts (for Claude Code, the ``env`` block of ``settings.json`` or the
launching shell); a model cannot declare it mid-session.

A missing or unknown scope is not permission to write argument-bearing
paths inside harness territory: a native project (an ancestor holding
``reviews/phase_state.json`` or ``reviews/assignment_contract.json``) or a
governed workspace root discovered by ``destination_capability``. Outside
that territory a folder name is not evidence of a lifecycle, so ordinary
writes proceed even when a path happens to contain ``research`` or
``milestones``.

``FRC_REQUIRE_SCOPE=1`` is an opt-in that refuses every event when no valid
scope is declared. Any other value, including ``0`` or unset, is the default
passthrough policy. ``FRC_GATE_HOOK_DISABLE`` remains the higher-priority
explicit off switch.

WHAT IT DOES
------------
It reads hook JSON on stdin and delegates in-scope decisions to
``scripts/full_run_contract_check.py``:

  Write / Edit / MultiEdit into a lifecycle artefact (manuscript/,
  milestones/, submission_bundle/)
        -> `authorize --run-scope <declared>` for the enclosing project.
           adhoc_review is read-only, so its authorization always refuses.
           An argument-bearing path inside a governed root but outside the
           staging and private-shipment lanes is DEST-PROTECTED under any scope.

  Task / Agent (subagent dispatch; host naming varies)
        -> `scope --parent-scope <declared parent> --child-brief <the prompt>`.

  Stop (terminal language, or structured terminal_phase_reached)
        -> `terminal --project-root <current project>`.

Without a known scope, argument-bearing Write/Edit paths inside harness
territory are denied, Agent/Task briefs that name run-generator-session are
denied, and briefs that name manuscript are denied when the session's cwd is
inside harness territory. Everything else without a scope is allowed so a
user-scoped plugin does not freeze ordinary coding sessions; each such
passthrough emits one stderr notice tagged ``[FRC-SCOPE-PASSTHROUGH]``.

Terminal markers match as whole words, so "fig.4" is not "G.4". When the host
reports ``stop_hook_active`` (it is re-invoking Stop after an earlier block),
structured state alone does not block again: the model cannot repair
lifecycle state inside the same turn, and a repeated block would only loop.
A fresh terminal claim in the new message still blocks.

A single explicit run_scope: adhoc_review declaration permits read/review
dispatch without a parent scope. run-generator-session still requires a
parent scope; this exemption does not authorize argument-bearing writes.

BLOCK CONTRACT
--------------
On a refusal it prints, per the Claude Code hooks spec:
  {"hookSpecificOutput": {"hookEventName": "PreToolUse",
    "permissionDecision": "deny", "permissionDecisionReason": "<gate finding>"}}
and exits 0 (the decision travels in the JSON, not the exit code).

FAIL MODE
---------
Missing or unknown FRC_PARENT_SCOPE fails closed for argument-bearing
Write/Edit paths in harness territory and for the Agent/Task briefs named
above, except for the explicit read/review-only adhoc_review dispatch.
Internal errors, a payload that is not a JSON object, and a missing
gate fail closed when a valid scope is active or FRC_REQUIRE_SCOPE=1.
Default-unset errors may pass only with a loud stderr diagnostic.
FRC_GATE_HOOK_DISABLE remains an explicit off switch.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
import destination_capability as destination  # noqa: E402
import invocation_scope as invocation  # noqa: E402

_PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT")
if _PLUGIN_ROOT:
    GATE = Path(_PLUGIN_ROOT) / "scripts" / "full_run_contract_check.py"
else:
    GATE = Path(__file__).resolve().parents[1] / "full_run_contract_check.py"

ACTIVE_SCOPE_ENV = "FRC_PARENT_SCOPE"
REQUIRE_SCOPE_ENV = "FRC_REQUIRE_SCOPE"
SCOPES = set(invocation.SCOPES)
MANUSCRIPT_DIR = "manuscript"
# Path segments that hold lifecycle artefacts: the manuscript tree, the M1-M5
# deliverables (references/role_output_contract.json), and the M5 export.
LIFECYCLE_ARTIFACT_SEGMENTS = (MANUSCRIPT_DIR, "milestones", "submission_bundle")
# Lifecycle artefacts plus the governed research tree.
ARGUMENT_SEGMENTS = LIFECYCLE_ARTIFACT_SEGMENTS + ("research", "60_workbench")
# destination_capability classes that lie inside a governed workspace root.
GOVERNED_KINDS = frozenset({"staging", "shipment", "repin", "instrument", "protected"})
TERMINAL_MARKERS = (
    "ladder complete", "terminal pass", "lifecycle complete",
    "terminal_phase_reached", "g.4", "converged", "shipped",
)
_TERMINAL_MARKER_RES = tuple(
    re.compile(r"(?<![\w.])" + re.escape(marker) + r"(?!\w)")
    for marker in TERMINAL_MARKERS
)


def _allow() -> int:
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


def _raw_scope() -> str:
    return os.environ.get(ACTIVE_SCOPE_ENV, "").strip()


def _require_scope() -> bool:
    return os.environ.get(REQUIRE_SCOPE_ENV) == "1"


def _passthrough_notice(event: str, tool: str = "") -> None:
    tool_bit = f" tool={tool}" if tool else ""
    print(
        f"[FRC-SCOPE-PASSTHROUGH] event={event}{tool_bit} "
        f"FRC_PARENT_SCOPE is unset",
        file=sys.stderr,
    )


def _hook_error_notice(reason: str) -> None:
    print(f"full_run_pretooluse_gate: {reason}", file=sys.stderr)


def _scope_required_reason(kind: str) -> str:
    return (
        f"[FRC-SCOPE-REQUIRED] {kind} refused without FRC_PARENT_SCOPE "
        "in {adhoc_review, project_independent, lab_iteration, full_lifecycle}"
    )


def _scope_unknown_reason(kind: str) -> str:
    return (
        "[FRC-SCOPE-UNKNOWN] FRC_PARENT_SCOPE is set but is not "
        f"adhoc_review, project_independent, lab_iteration, or full_lifecycle; refusing {kind}"
    )


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
    normalized = path_str.replace("\\", "/")
    path = Path(normalized)
    if not path.is_absolute() and cwd:
        path = Path(cwd) / path
    return path


def _segments(path_str: str) -> list[str]:
    return [part.casefold() for part in path_str.replace("\\", "/").split("/")]


def _is_lifecycle_artifact_path(path_str: str) -> bool:
    parts = _segments(path_str)
    return any(segment in parts for segment in LIFECYCLE_ARTIFACT_SEGMENTS)


def _is_argument_path(path_str: str) -> bool:
    parts = _segments(path_str)
    return any(segment in parts for segment in ARGUMENT_SEGMENTS)


def _destination_kind(path: Path) -> str:
    try:
        return destination.classify(path)
    except Exception:
        return "unresolved"


def _in_harness_territory(path: Path, *, is_dir: bool = False) -> bool:
    """True inside a native project or a governed workspace root.

    An unresolvable classification counts as inside: absence of a verdict is
    not evidence that the path is ordinary.
    """
    start = path if is_dir else path.parent
    if _find_project_root(start) is not None:
        return True
    kind = _destination_kind(path)
    return kind in GOVERNED_KINDS or kind == "unresolved"


def _has_terminal_marker(folded_message: str) -> bool:
    return any(rx.search(folded_message) for rx in _TERMINAL_MARKER_RES)


def _terminal_phase_reached(root: Path) -> bool:
    path = root / "reviews" / "phase_state.json"
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    return isinstance(data, dict) and data.get("terminal_phase_reached") is True


def _handle_write(tool_input: dict, *, cwd: str | None = None,
                  tool_name: str = "Write") -> int:
    raw = os.environ.get(ACTIVE_SCOPE_ENV, "").strip().lower()
    scope = _active_parent_scope()
    path_str = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if _require_scope() and scope is None:
        if raw:
            return _deny(_scope_unknown_reason("write"))
        return _deny(_scope_required_reason("write"))
    if raw and scope is None:
        return _deny(
            "[FRC-SCOPE-UNKNOWN] FRC_PARENT_SCOPE is set but is not "
            "adhoc_review, project_independent, lab_iteration, or full_lifecycle; refusing write"
        )
    if scope is None:
        if path_str and _is_argument_path(path_str) and \
                _in_harness_territory(_path_from_input(path_str, cwd)):
            return _deny(
                "[FRC-SCOPE-REQUIRED] argument-bearing write inside a harness project "
                "or governed workspace refused without FRC_PARENT_SCOPE in "
                "{adhoc_review, project_independent, lab_iteration, full_lifecycle}"
            )
        _passthrough_notice("PreToolUse", tool_name)
        return _allow()
    if not path_str:
        return _allow()
    p = _path_from_input(path_str, cwd)
    if scope == invocation.PROJECT_INDEPENDENT:
        import piw_session
        session_path = os.environ.get("FRC_PIW_SESSION", "")
        if not session_path:
            return _deny("[FRC-PIW-SESSION-REQUIRED] standalone writes require the bound task session")
        try:
            bound = piw_session.validate_session(session_path)
            staging = Path(bound["staging_root"]).resolve()
            # Scope labels never bypass governed destinations or task confinement.
            piw_session.assert_output(p)
            p.resolve().relative_to(staging)
        except (OSError, ValueError) as exc:
            return _deny(f"[{getattr(exc, 'code', 'PIW-OUTPUT-SCOPE')}] {exc}")
        return _allow()
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
    if not _is_argument_path(path_str):
        return _allow()
    if _destination_kind(p) == "protected":
        return _deny(
            f"[{destination.DEST_PROTECTED}] {path_str!r} lies inside a governed "
            "workspace root outside the harness staging and private-shipment lanes; "
            "no run scope grants the harness write authority there"
        )
    if not _is_lifecycle_artifact_path(path_str):
        return _allow()
    root = _find_project_root(p.parent if p.parent != p else p)
    if root is None:
        rc, out = _run_gate("authorize", "--project-root", str(p.parent),
                            "--run-scope", scope)
        return _deny(_first_finding(out)) if rc != 0 else _allow()
    rc, out = _run_gate("authorize", "--project-root", str(root),
                        "--run-scope", scope)
    return _deny(_first_finding(out)) if rc != 0 else _allow()


def _read_review_only_brief(brief: str) -> bool:
    """Conservative dispatch screen; actual write authority remains separate."""
    declaration = invocation.parse_scope_declaration(brief)
    if (declaration["declared_scope"] != invocation.ADHOC_REVIEW
            or declaration["result"] != "DECLARED"):
        return False
    if "run-generator-session" in brief.casefold():
        return False
    # Match affirmative action clauses, not nouns ("read the draft") or
    # prohibitions ("do not write/edit"). Ambiguous requests retain the guard.
    mutation = re.compile(
        r"(?im)(?:^|[.;!?:]\s*|\b(?:and|then)\s+)"
        r"(?:please\s+)?"
        r"(?:(?:use|ask|have|tell|instruct|dispatch)\s+(?:the\s+)?"
        r"(?:generator|agent)\s+(?:to\s+)?|"
        r"(?:the\s+)?(?:generator|agent)\s+(?:must|shall|should|will)\s+)?"
        r"(?:write|draft|generate|rewrite|revise|edit|modify|update|replace|"
        r"apply|commit|publish|delete|remove|save|create|make\s+changes)\b"
    )
    return mutation.search(brief) is None


def _handle_agent(tool_input: dict, *, cwd: str | None = None) -> int:
    parent_scope = _active_parent_scope()
    brief = tool_input.get("prompt") or tool_input.get("description") or ""
    if parent_scope is None:
        if _require_scope():
            if _raw_scope():
                return _deny(_scope_unknown_reason("Agent/Task"))
            return _deny(_scope_required_reason("Agent/Task"))
        # Reading/review is not a manuscript-write grant. Reuse the canonical
        # declaration parser instead of treating a resource name as an action.
        declared = invocation.parse_scope_declaration(brief)
        if (not _raw_scope() and declared["declared_scope"] == invocation.ADHOC_REVIEW
                and declared["result"] == "DECLARED"):
            if not _read_review_only_brief(brief):
                return _deny("[FRC-PROSE-FORBIDDEN] adhoc_review dispatch contains "
                             "an affirmative mutation or generator request; use "
                             "the authorized parent scope for that action")
            _passthrough_notice("PreToolUse", "Agent/Task adhoc_review")
            return _allow()
        low = brief.casefold()
        if "run-generator-session" in low:
            return _deny(
                "[FRC-SCOPE-REQUIRED] Agent/Task that names run-generator-session "
                "refused without FRC_PARENT_SCOPE"
            )
        if "manuscript" in low and \
                _in_harness_territory(Path(cwd or os.getcwd()), is_dir=True):
            return _deny(
                "[FRC-SCOPE-REQUIRED] Agent/Task that names manuscript from inside a "
                "harness project or governed workspace refused without FRC_PARENT_SCOPE. "
                "For read/review-only manuscript work without mutation requests, declare exactly one "
                "run_scope: adhoc_review in the child brief; generation and "
                "argument-bearing writes require their authorized parent scope."
            )
        _passthrough_notice("PreToolUse", "Agent")
        return _allow()
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
    raw = _raw_scope()
    scope = _active_parent_scope()
    if scope is None:
        if _require_scope() or raw:
            if raw:
                return _block_stop(_scope_unknown_reason("Stop"))
            return _block_stop(_scope_required_reason("Stop"))
        _passthrough_notice("Stop")
        return _allow()
    message = payload.get("last_assistant_message") or ""
    low = " ".join(message.casefold().split())
    has_marker = _has_terminal_marker(low)
    cwd = payload.get("cwd") or os.getcwd()
    root = _find_project_root(Path(cwd)) or Path(cwd)
    structured = _terminal_phase_reached(root)
    if structured and not has_marker and payload.get("stop_hook_active") is True:
        # The host is re-invoking Stop after an earlier block. Structured state
        # cannot be repaired inside this turn, so blocking again would loop.
        print(
            "full_run_pretooluse_gate: [FRC-STOP-REENTRY] terminal_phase_reached "
            f"remains unverified at {root}; not re-blocking a host re-invoked Stop",
            file=sys.stderr,
        )
        structured = False
    if scope == invocation.PROJECT_INDEPENDENT:
        if has_marker or structured:
            return _block_stop(
                "[FRC-PIW-NON-TERMINAL] task completion does not authorize lifecycle terminal or promotion"
            )
        return _allow()
    if scope == invocation.LAB_ITERATION:
        if has_marker:
            return _block_stop(
                "[FRC-LAB-TERMINAL-FORBIDDEN] lab_iteration cannot make a terminal, "
                "shipment, convergence, or lifecycle-complete claim"
            )
        return _allow()
    if not has_marker and not structured:
        return _allow()
    rc, out = _run_gate("terminal", "--project-root", str(root))
    return _block_stop(_first_finding(out)) if rc != 0 else _allow()


def main() -> int:
    if os.environ.get("FRC_GATE_HOOK_DISABLE"):
        return _allow()
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError(f"expected a JSON object, got {type(payload).__name__}")
    except Exception as e:
        reason = f"[FRC-HOOK-ERROR] unreadable hook payload: {e}"
        _hook_error_notice(reason)
        if _require_scope():
            return _deny(reason)
        if _active_parent_scope() is None and not _raw_scope():
            _passthrough_notice("PreToolUse")
            return _allow()
        return _deny(reason)
    if not GATE.is_file():
        reason = f"[FRC-GATE-UNAVAILABLE] authoritative gate missing at {GATE}"
        print(f"full_run_pretooluse_gate: {reason}", file=sys.stderr)
        if payload.get("hook_event_name") == "Stop":
            return _block_stop(reason)
        return _deny(reason)
    try:
        if payload.get("hook_event_name") == "Stop":
            return _handle_stop(payload)
        tool = payload.get("tool_name", "")
        tool_input = payload.get("tool_input", {}) or {}
        if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
            return _handle_write(tool_input, cwd=payload.get("cwd"), tool_name=tool)
        if tool in ("Task", "Agent"):
            return _handle_agent(tool_input, cwd=payload.get("cwd"))
        if _require_scope() and _active_parent_scope() is None:
            if _raw_scope():
                return _deny(_scope_unknown_reason(tool or "event"))
            return _deny(_scope_required_reason(tool or "event"))
        if _active_parent_scope() is None and not _raw_scope():
            _passthrough_notice("PreToolUse", tool or "unknown")
        return _allow()
    except Exception as e:
        reason = f"[FRC-HOOK-ERROR] internal hook error: {e}"
        _hook_error_notice(reason)
        event_stop = payload.get("hook_event_name") == "Stop"
        if _require_scope():
            return _block_stop(reason) if event_stop else _deny(reason)
        if _active_parent_scope() is None and not _raw_scope():
            _passthrough_notice("Stop" if event_stop else "PreToolUse")
            return _allow()
        return _block_stop(reason) if event_stop else _deny(reason)


if __name__ == "__main__":
    sys.exit(main())
