#!/usr/bin/env python3
"""role_ledger - record platform role entry and exit with the session identity.

Master Governance 1.0.15 clause 1.11c: "A session takes and leaves a platform
role only through the platform's entry points, and the platform records each
entry and exit with the session identity." (FINDING-20260929-002)

WHAT IT RECORDS
---------------
One JSONL line per role transition, in an append-only ledger whose lines are
hash-chained (``prev_sha256`` is the sha256 of the previous line's text without
its newline; null for the first line):

  ts, host ("claude"|"codex"), session_id, event ("enter"|"exit"|"turn_end"),
  role, role_source ("subagent"|"command"|"skill"|"spawn_agent"), agent_id,
  agent_type, cwd, transcript_path, hook_event_name, prev_sha256, command

Claude Code
  SubagentStart / SubagentStop, agent_type ``co-author-harness:<role>``
      -> enter / exit, role ``<role>``, role_source "subagent".
      Other plugins' and the host's own subagents are ignored.
  UserPromptExpansion of a harness run command, or PreToolUse of the Skill
  tool naming one -> Planner enter on the main thread (role "planner",
  role_source "command" / "skill"). Ignored while a planner role is already
  open for the session, and ignored inside a subagent (payload carries
  agent_id).
  SessionEnd while a planner role is open for the session -> exit (role
  "planner", role_source "command"). A Planner holds the role for the whole
  session, so the exit is the end of the session, not the end of a turn. Stop
  (end of a turn) records nothing on Claude Code. A session that never ends
  cleanly leaves its planner entry open. run-generator-session is not a
  Planner command and is never recorded.
  Open planner roles are kept in ``state.json`` next to the ledger.

Codex (partial; Codex exposes no subagent-stop event, so exits are NOT recorded)
  PreToolUse spawn_agent -> enter, role "subagent[:<name>]", role_source
  "spawn_agent". Stop -> turn_end (an end-of-turn marker, not a role exit),
  written only for a session that has already recorded an entry.

LEDGER LOCATION
---------------
  hook cwd inside a governed Workbench work-id root
      ->  <work-id root>/reviews/.harness/roles/ledger.jsonl
      (the tool control plane; destination_capability must classify it as
      writable, otherwise nothing is written and a stderr note is emitted)
  every other case (non-governed project, cwd outside the package, no cwd)
      ->  $CLAUDE_PLUGIN_DATA (or $PLUGIN_DATA)/roles/ledger.jsonl
  neither  ->  the event is dropped with a stderr note.
A non-governed project never receives a ledger. A session whose cwd is outside
its governed package records to plugin data (the ledger is cwd-based).

FAIL MODE
---------
The hook never blocks. It ALWAYS exits 0; any failure (including a ledger lock
still held after 5 s, or no writable ledger location) goes to stderr as a note
and the event is dropped; the ledger is never written unlocked. It prints
nothing to stdout, so it never alters a decision made by another hook on the
same event. ``COAUTHOR_ROLE_LEDGER_DISABLE=1`` turns it off.

FIELD-NAME CAVEAT
-----------------
Common fields (session_id, transcript_path, cwd, hook_event_name) and
agent_id / agent_type on SubagentStart/SubagentStop are per the Claude Code
hooks docs. The docs name the UserPromptExpansion field ``command_name``; this
script also reads ``command`` and ``expansion_command``. The Skill tool's input
key is read from ``skill`` / ``skill_name`` / ``name`` / ``command``. Codex
spawn_agent payloads are read defensively (agent_type / agent_name / name /
role under tool_input). A subagent agent_type may arrive bare
(``co-author-harness:evaluator``) or as ``plugin:co-author-harness:evaluator``;
both are accepted.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PLUGIN_NAME = "co-author-harness"
PLANNER_ROLE = "planner"
# Fallback list; the live list is every skills/run-* directory plus these.
RUN_COMMANDS_FALLBACK = frozenset({
    "run-iterate", "run-draft", "run-finalize", "run-fast",
    "run-phase-1", "run-phase-2", "run-phase-3", "run-phase-3-stability",
    "run-phase-4", "run-reflection",
})
# Not a Planner entry point: it runs a Generator session, not the Planner role.
NOT_PLANNER_COMMANDS = frozenset({"run-generator-session"})
HOST_ENV = "COAUTHOR_ROLE_LEDGER_HOST"
LEDGER_NAME = "ledger.jsonl"
STATE_NAME = "state.json"

_HERE = Path(__file__).resolve()
PACKAGE_ROOT = _HERE.parent.parent.parent


def _warn(msg: str) -> None:
    print(f"role_ledger: {msg}", file=sys.stderr)


def run_commands() -> frozenset[str]:
    names = set(RUN_COMMANDS_FALLBACK)
    try:
        for entry in (PACKAGE_ROOT / "skills").iterdir():
            if entry.name.startswith("run-") and entry.is_dir():
                names.add(entry.name)
    except OSError:
        pass
    return frozenset(names - NOT_PLANNER_COMMANDS)


def _first_str(mapping: object, *keys: str) -> str:
    if isinstance(mapping, dict):
        for key in keys:
            value = mapping.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def normalize_command(raw: str) -> str:
    name = raw.strip().lstrip("/")
    if name.startswith("plugin:"):
        name = name[len("plugin:"):]
    if name.startswith(PLUGIN_NAME + ":"):
        name = name[len(PLUGIN_NAME) + 1:]
    return name


def subagent_role(agent_type: str) -> str | None:
    """Role after ``co-author-harness:``; None for any other agent type."""
    name = agent_type.strip()
    if name.startswith("plugin:"):
        name = name[len("plugin:"):]
    prefix = PLUGIN_NAME + ":"
    if not name.startswith(prefix):
        return None
    role = name[len(prefix):].strip()
    return role or None


def detect_host(payload: dict, argv: list[str]) -> str:
    if "--host" in argv:
        idx = argv.index("--host")
        if idx + 1 < len(argv) and argv[idx + 1] in ("claude", "codex"):
            return argv[idx + 1]
    declared = os.environ.get(HOST_ENV, "").strip().lower()
    if declared in ("claude", "codex"):
        return declared
    if str(payload.get("tool_name") or "") == "spawn_agent":
        return "codex"
    if os.environ.get("PLUGIN_ROOT") and not os.environ.get("CLAUDE_PLUGIN_ROOT"):
        return "codex"
    return "claude"


# --------------------------------------------------------------------------
# Ledger location

def _import_destination_capability():
    scripts = str(_HERE.parent.parent)
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import destination_capability as dc  # noqa: WPS433
    return dc


def _is_governed_work_id_root(dc, path: Path) -> bool:
    canon = dc._canon(path)
    for root in dc.governed_roots(path):
        if (root / dc._MANIFEST_REL).is_file() and dc._is_workbench_work_id_root(canon, root):
            return True
    return False


def locate_ledger(cwd: str) -> Path | None:
    """Return the ledger path for this cwd, or None when nothing may be written."""
    if cwd:
        start = Path(cwd).resolve()
        try:
            dc = _import_destination_capability()
        except Exception as exc:  # defensive: never fall back to an unclassified path
            _warn(f"cannot load destination_capability ({exc}); event dropped")
            return None
        governed = None
        for d in [start, *start.parents]:
            if _is_governed_work_id_root(dc, d):
                governed = d
                break
        if governed is not None:
            path = governed / "reviews" / ".harness" / "roles" / LEDGER_NAME
            try:
                dc.assert_writable(path, purpose="role ledger")
            except dc.DestinationRefused as exc:
                _warn(f"ledger not writable, event dropped: {exc}")
                return None
            return path
    data = os.environ.get("CLAUDE_PLUGIN_DATA") or os.environ.get("PLUGIN_DATA")
    if data:
        return Path(data) / "roles" / LEDGER_NAME
    _warn("no governed package for this cwd and CLAUDE_PLUGIN_DATA/PLUGIN_DATA "
          "is unset; event dropped")
    return None


# --------------------------------------------------------------------------
# Ledger IO

class _LockTimeout(Exception):
    """The ledger lock was not obtained in time."""


class _Lock:
    """Best-effort cross-process lock: O_EXCL lock file.

    Waits up to LOCK_WAIT seconds, then raises _LockTimeout (the caller drops
    the event; nothing is ever written unlocked). A lock file older than
    LOCK_STALE seconds is treated as abandoned and removed."""

    LOCK_WAIT = 5.0
    LOCK_STALE = 30.0

    def __init__(self, path: Path):
        self.path = path

    def __enter__(self):
        deadline = time.time() + self.LOCK_WAIT
        while True:
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                return self
            except FileExistsError:
                try:
                    if time.time() - self.path.stat().st_mtime > self.LOCK_STALE:
                        self.path.unlink()
                        continue
                except OSError:
                    pass
                if time.time() > deadline:
                    raise _LockTimeout(f"{self.path} still held after {self.LOCK_WAIT:g} s")
                time.sleep(0.05)

    def __exit__(self, *exc):
        try:
            self.path.unlink()
        except OSError:
            pass
        return False


def _last_line(path: Path) -> str | None:
    try:
        size = path.stat().st_size
    except OSError:
        return None
    if size == 0:
        return None
    with open(path, "rb") as fh:
        block = 4096
        data = b""
        pos = size
        while pos > 0:
            step = min(block, pos)
            pos -= step
            fh.seek(pos)
            data = fh.read(step) + data
            stripped = data.rstrip(b"\r\n")
            if b"\n" in stripped or pos == 0:
                break
    stripped = data.rstrip(b"\r\n")
    if not stripped:
        return None
    return stripped.split(b"\n")[-1].decode("utf-8", errors="replace").rstrip("\r")


def _read_state(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("open"), dict):
            return data
    except (OSError, ValueError):
        pass
    return {"open": {}}


def _write_state(path: Path, state: dict) -> None:
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=True, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def _session_id(payload: dict):
    """The payload's session id, or None when it is missing or empty. A
    missing id is recorded as JSON null and never becomes a state key."""
    value = payload.get("session_id")
    if value is None or not str(value).strip():
        return None
    return value


def _record(payload: dict, host: str, event: str, role: str | None, source: str | None,
            command: str | None = None) -> dict:
    return {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "host": host,
        "session_id": _session_id(payload),
        "event": event,
        "role": role,
        "role_source": source,
        "agent_id": payload.get("agent_id"),
        "agent_type": payload.get("agent_type"),
        "cwd": payload.get("cwd"),
        "transcript_path": payload.get("transcript_path"),
        "hook_event_name": payload.get("hook_event_name"),
        "prev_sha256": None,
        "command": command,
    }


def append(ledger: Path, record: dict, planner_open: str | None = None,
           planner_close: bool = False, mark_session: bool = False,
           require_session: bool = False) -> None:
    """Append one chained line; optionally update the open-planner sidecar.

    The open-planner check and the append happen under one lock: a planner
    entry is recorded only if none is open for the session, and a planner
    exit only if one is. ``mark_session`` notes the session in the sidecar
    (``seen``); ``require_session`` records the line only for a session so
    noted (Codex ``turn_end``)."""
    state_path = ledger.parent / STATE_NAME
    raw_sid = record.get("session_id")
    sid = None if raw_sid is None else str(raw_sid)
    if sid is None and (planner_close or require_session):
        _warn(f"{record.get('hook_event_name') or record.get('event')} without a session id "
              "skipped: no state can be keyed to it")
        return
    if (planner_close or require_session) and not state_path.is_file():
        return  # nothing can be open: leave a session that never entered untouched
    ledger.parent.mkdir(parents=True, exist_ok=True)
    try:
        with _Lock(ledger.parent / (LEDGER_NAME + ".lock")):
            if sid is not None and (planner_open or planner_close):
                is_open = sid in _read_state(state_path)["open"]
                if planner_open and is_open:
                    return
                if planner_close and not is_open:
                    return
            if require_session and sid not in _read_state(state_path).get("seen", {}):
                return
            prev = _last_line(ledger)
            record["prev_sha256"] = hashlib.sha256(prev.encode("utf-8")).hexdigest() if prev else None
            line = json.dumps(record, ensure_ascii=True, sort_keys=False)
            with open(ledger, "ab") as fh:
                fh.write(line.encode("utf-8") + b"\n")
            if sid is None:
                _warn(f"{record.get('event')} recorded without a session id "
                      "(session_id null; no state stored)")
            elif planner_open or planner_close:
                state = _read_state(state_path)
                if planner_open:
                    state["open"][sid] = {"role": PLANNER_ROLE, "command": planner_open,
                                          "ts": record["ts"]}
                else:
                    state["open"].pop(sid, None)
                _write_state(state_path, state)
            if mark_session and sid is not None:
                state = _read_state(state_path)
                state.setdefault("seen", {})[sid] = record["ts"]
                _write_state(state_path, state)
    except _LockTimeout as exc:
        _warn(f"ledger busy, event dropped: {exc}")


# --------------------------------------------------------------------------
# Event mapping

def handle(payload: dict, host: str) -> None:
    event = str(payload.get("hook_event_name") or "")
    if host == "codex":
        return _handle_codex(payload, event)
    in_subagent = bool(payload.get("agent_id"))

    if event in ("SubagentStart", "SubagentStop"):
        role = subagent_role(str(payload.get("agent_type") or ""))
        if role is None:
            return
        ledger = locate_ledger(str(payload.get("cwd") or ""))
        if ledger is None:
            return
        append(ledger, _record(payload, host, "enter" if event == "SubagentStart" else "exit",
                               role, "subagent"))
        return

    planner_command = None
    source = "command"
    if event == "UserPromptExpansion" and not in_subagent:
        planner_command = normalize_command(
            _first_str(payload, "command_name", "command", "expansion_command"))
    elif event == "PreToolUse" and str(payload.get("tool_name") or "") == "Skill" \
            and not in_subagent:
        planner_command = normalize_command(
            _first_str(payload.get("tool_input"), "skill", "skill_name", "name", "command"))
        source = "skill"
    if planner_command is not None:
        if planner_command not in run_commands():
            return
        ledger = locate_ledger(str(payload.get("cwd") or ""))
        if ledger is None:
            return
        append(ledger, _record(payload, host, "enter", PLANNER_ROLE, source, planner_command),
               planner_open=planner_command)
        return

    # The Planner holds its role until the session ends; a Stop (end of turn)
    # is not an exit.
    if event == "SessionEnd" and not in_subagent:
        ledger = locate_ledger(str(payload.get("cwd") or ""))
        if ledger is None:
            return
        append(ledger, _record(payload, host, "exit", PLANNER_ROLE, "command"),
               planner_close=True)


def _handle_codex(payload: dict, event: str) -> None:
    if event == "PreToolUse" and str(payload.get("tool_name") or "") == "spawn_agent":
        name = _first_str(payload.get("tool_input"),
                          "agent_type", "agent_name", "name", "role")
        record_payload = dict(payload)
        record_payload["agent_type"] = name or None
        role = f"subagent:{name}" if name else "subagent"
        ledger = locate_ledger(str(payload.get("cwd") or ""))
        if ledger is not None:
            append(ledger, _record(record_payload, "codex", "enter", role, "spawn_agent"),
                   mark_session=True)
    elif event == "Stop":
        ledger = locate_ledger(str(payload.get("cwd") or ""))
        if ledger is not None:
            append(ledger, _record(payload, "codex", "turn_end", None, None),
                   require_session=True)


def main(argv: list[str] | None = None, stdin_text: str | None = None) -> int:
    """Always returns 0."""
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        if os.environ.get("COAUTHOR_ROLE_LEDGER_DISABLE") == "1":
            return 0
        text = sys.stdin.read() if stdin_text is None else stdin_text
        payload = json.loads(text or "{}")
        if not isinstance(payload, dict):
            return 0
        handle(payload, detect_host(payload, argv))
    except BaseException as exc:  # noqa: BLE001 - a ledger fault must never block a session
        if isinstance(exc, KeyboardInterrupt):
            return 0
        _warn(f"{type(exc).__name__}: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
