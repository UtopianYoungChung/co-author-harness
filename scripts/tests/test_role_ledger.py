"""Tests for scripts/hooks/role_ledger.py (MG 1.0.15 clause 1.11c)."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))
import role_ledger as rl  # noqa: E402

SCRIPT = HOOKS / "role_ledger.py"
MANIFEST = Path("governance") / "output-routing" / "output_routing.yaml"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in ("COAUTHOR_ROLE_LEDGER_DISABLE", "COAUTHOR_ROLE_LEDGER_HOST",
                 "CLAUDE_PLUGIN_DATA", "PLUGIN_DATA", "PLUGIN_ROOT", "COAUTHOR_EXTRA_GOVERNED_ROOTS"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(HOOKS.parents[1]))


@pytest.fixture
def data(tmp_path, monkeypatch):
    """The plugin data dir: where every non-governed session records."""
    path = tmp_path / "data"
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(path))
    return path


@pytest.fixture
def ledger(data):
    return data / "roles" / "ledger.jsonl"


@pytest.fixture
def project(tmp_path, data):
    root = tmp_path / "proj"
    (root / "reviews").mkdir(parents=True)
    (root / "reviews" / "phase_state.json").write_text("{}", encoding="utf-8")
    return root


@pytest.fixture
def governed(tmp_path):
    ws = tmp_path / "ws"
    (ws / MANIFEST).parent.mkdir(parents=True)
    (ws / MANIFEST).write_text("routes: []\n", encoding="utf-8")
    wid = ws / "research" / "60_Workbench" / "work-1"
    (wid / "reviews").mkdir(parents=True)
    (wid / "reviews" / "phase_state.json").write_text("{}", encoding="utf-8")
    return wid


def fire(payload, cwd, **extra):
    payload = dict(payload, cwd=str(cwd), session_id=payload.get("session_id", "S1"))
    payload.update(extra)
    assert rl.main([], json.dumps(payload)) == 0


def read(ledger: Path):
    return [json.loads(x) for x in ledger.read_text(encoding="utf-8").splitlines()]


def test_subagent_enter_exit(project, ledger):
    fire({"hook_event_name": "SubagentStart", "agent_type": "co-author-harness:evaluator",
          "agent_id": "a1"}, project)
    fire({"hook_event_name": "SubagentStop", "agent_type": "co-author-harness:evaluator",
          "agent_id": "a1"}, project)
    rows = read(ledger)
    assert [(r["event"], r["role"], r["role_source"]) for r in rows] == [
        ("enter", "evaluator", "subagent"), ("exit", "evaluator", "subagent")]
    assert rows[0]["host"] == "claude" and rows[0]["session_id"] == "S1"
    assert rows[0]["agent_id"] == "a1" and rows[0]["agent_type"] == "co-author-harness:evaluator"


def test_plugin_prefixed_agent_type_accepted(project, ledger):
    fire({"hook_event_name": "SubagentStart", "agent_type": "plugin:co-author-harness:generator",
          "agent_id": "a2"}, project)
    assert read(ledger)[0]["role"] == "generator"


@pytest.mark.parametrize("agent_type", ["Explore", "other-plugin:reviewer", "", None])
def test_non_harness_subagent_ignored(project, data, agent_type):
    fire({"hook_event_name": "SubagentStart", "agent_type": agent_type, "agent_id": "x"}, project)
    fire({"hook_event_name": "SubagentStop", "agent_type": agent_type, "agent_id": "x"}, project)
    assert not data.exists()


@pytest.mark.parametrize("field,value", [
    ("command_name", "run-iterate"),
    ("command_name", "co-author-harness:run-draft"),
    ("command", "/run-finalize"),
])
def test_planner_enter_on_command_then_exit_on_session_end(project, ledger, field, value):
    fire({"hook_event_name": "UserPromptExpansion", field: value}, project)
    fire({"hook_event_name": "UserPromptExpansion", "command_name": "run-draft"}, project)  # dedupe
    fire({"hook_event_name": "Stop"}, project)  # end of a turn: not an exit
    assert len(read(ledger)) == 1
    fire({"hook_event_name": "SessionEnd", "reason": "other"}, project)
    fire({"hook_event_name": "SessionEnd", "reason": "other"}, project)  # nothing open: records nothing
    rows = read(ledger)
    assert [(r["event"], r["role"], r["role_source"]) for r in rows] == [
        ("enter", "planner", "command"), ("exit", "planner", "command")]
    assert rows[0]["command"] == rl.normalize_command(value)
    assert rows[1]["hook_event_name"] == "SessionEnd"


def test_stop_never_exits_planner_and_new_entry_after_exit_records(project, ledger):
    fire({"hook_event_name": "UserPromptExpansion", "command_name": "run-iterate"}, project)
    for _ in range(3):
        fire({"hook_event_name": "Stop"}, project)
    assert [r["event"] for r in read(ledger)] == ["enter"]
    fire({"hook_event_name": "SessionEnd"}, project)
    fire({"hook_event_name": "UserPromptExpansion", "command_name": "run-iterate"}, project)
    assert [r["event"] for r in read(ledger)] == ["enter", "exit", "enter"]


def test_run_generator_session_is_not_a_planner_entry(project, data):
    assert "run-generator-session" not in rl.run_commands()
    fire({"hook_event_name": "UserPromptExpansion", "command_name": "run-generator-session"}, project)
    fire({"hook_event_name": "PreToolUse", "tool_name": "Skill",
          "tool_input": {"skill": "co-author-harness:run-generator-session"}}, project)
    assert not data.exists()


def test_planner_enter_on_skill_tool(project, ledger):
    fire({"hook_event_name": "PreToolUse", "tool_name": "Skill",
          "tool_input": {"skill": "co-author-harness:run-iterate"}}, project)
    rows = read(ledger)
    assert rows[0]["role_source"] == "skill" and rows[0]["command"] == "run-iterate"


def test_non_run_command_and_subagent_thread_ignored(project, data):
    fire({"hook_event_name": "UserPromptExpansion", "command_name": "plugin-commands"}, project)
    fire({"hook_event_name": "PreToolUse", "tool_name": "Skill",
          "tool_input": {"skill": "run-phase-3"}}, project, agent_id="sub1")
    fire({"hook_event_name": "Stop"}, project)
    fire({"hook_event_name": "SessionEnd"}, project)
    assert not data.exists()


def test_session_end_without_open_planner_records_nothing(project, data):
    fire({"hook_event_name": "SessionEnd"}, project)
    assert not data.exists()


def test_planner_state_is_per_session(project, ledger):
    fire({"hook_event_name": "UserPromptExpansion", "command_name": "run-iterate",
          "session_id": "A"}, project)
    fire({"hook_event_name": "SessionEnd", "session_id": "B"}, project)
    assert len(read(ledger)) == 1
    fire({"hook_event_name": "SessionEnd", "session_id": "A"}, project)
    assert len(read(ledger)) == 2


def test_non_governed_project_is_never_written(project, data):
    fire({"hook_event_name": "SubagentStart", "agent_type": "co-author-harness:evaluator",
          "agent_id": "e"}, project)
    fire({"hook_event_name": "UserPromptExpansion", "command_name": "run-iterate"}, project)
    assert not (project / ".harness").exists()
    assert (data / "roles" / "ledger.jsonl").is_file()


def test_governed_planner_exit_on_session_end(governed):
    fire({"hook_event_name": "UserPromptExpansion", "command_name": "run-iterate"}, governed)
    fire({"hook_event_name": "Stop"}, governed)
    fire({"hook_event_name": "SessionEnd"}, governed)
    rows = read(governed / "reviews" / ".harness" / "roles" / "ledger.jsonl")
    assert [r["event"] for r in rows] == ["enter", "exit"]


def test_hash_chain(project, ledger):
    for i in range(3):
        fire({"hook_event_name": "SubagentStart", "agent_type": "co-author-harness:reflector",
              "agent_id": f"a{i}"}, project)
    text = ledger.read_text(encoding="utf-8")
    lines = text.splitlines()
    rows = [json.loads(x) for x in lines]
    assert rows[0]["prev_sha256"] is None
    for prev_line, row in zip(lines, rows[1:]):
        assert row["prev_sha256"] == hashlib.sha256(prev_line.encode("utf-8")).hexdigest()


def test_governed_work_id_root_uses_control_plane(governed):
    fire({"hook_event_name": "SubagentStart", "agent_type": "co-author-harness:generator",
          "agent_id": "g1"}, governed)
    assert len(read(governed / "reviews" / ".harness" / "roles" / "ledger.jsonl")) == 1
    assert not (governed / ".harness").exists()


def test_governed_work_id_from_subdirectory_without_phase_state(governed):
    (governed / "reviews" / "phase_state.json").unlink()
    sub = governed / "manuscript"
    sub.mkdir()
    fire({"hook_event_name": "SubagentStart", "agent_type": "co-author-harness:generator",
          "agent_id": "g1"}, sub)
    assert (governed / "reviews" / ".harness" / "roles" / "ledger.jsonl").is_file()


def test_project_inside_governed_tree_but_not_work_id_is_skipped(tmp_path, data):
    ws = tmp_path / "ws"
    (ws / MANIFEST).parent.mkdir(parents=True)
    (ws / MANIFEST).write_text("routes: []\n", encoding="utf-8")
    proj = ws / "research" / "40_Other" / "p"
    (proj / "reviews").mkdir(parents=True)
    (proj / "reviews" / "phase_state.json").write_text("{}", encoding="utf-8")
    fire({"hook_event_name": "SubagentStart", "agent_type": "co-author-harness:generator",
          "agent_id": "g1"}, proj)
    assert not (proj / ".harness").exists()
    assert not any(ws.rglob("ledger.jsonl"))


def test_no_project_uses_plugin_data_else_drops_with_note(tmp_path, monkeypatch, capsys):
    cwd = tmp_path / "bare"
    cwd.mkdir()
    payload = {"hook_event_name": "SubagentStart", "agent_type": "co-author-harness:evaluator",
               "agent_id": "e"}
    fire(payload, cwd)
    assert not any(tmp_path.rglob("ledger.jsonl"))
    captured = capsys.readouterr()
    assert "event dropped" in captured.err and captured.out == ""
    data = tmp_path / "data"
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(data))
    fire(payload, cwd)
    assert (data / "roles" / "ledger.jsonl").is_file()


def test_codex_spawn_agent_and_turn_end(project, ledger, monkeypatch):
    monkeypatch.setenv("COAUTHOR_ROLE_LEDGER_HOST", "codex")
    fire({"hook_event_name": "PreToolUse", "tool_name": "spawn_agent",
          "tool_input": {"message": "m", "agent_type": "worker"}}, project)
    fire({"hook_event_name": "Stop"}, project)
    rows = read(ledger)
    assert [(r["host"], r["event"], r["role"], r["role_source"]) for r in rows] == [
        ("codex", "enter", "subagent:worker", "spawn_agent"), ("codex", "turn_end", None, None)]


def test_codex_stop_without_prior_entry_records_nothing(project, data, monkeypatch):
    monkeypatch.setenv("COAUTHOR_ROLE_LEDGER_HOST", "codex")
    fire({"hook_event_name": "Stop"}, project)
    assert not data.exists()
    # another session's entry does not license this session's turn_end
    fire({"hook_event_name": "PreToolUse", "tool_name": "spawn_agent",
          "tool_input": {"agent_type": "worker"}}, project, session_id="S2")
    fire({"hook_event_name": "Stop"}, project, session_id="S1")
    assert [r["event"] for r in read(data / "roles" / "ledger.jsonl")] == ["enter"]


def test_codex_never_records_exit(project, data, monkeypatch):
    monkeypatch.setenv("COAUTHOR_ROLE_LEDGER_HOST", "codex")
    fire({"hook_event_name": "SubagentStop", "agent_type": "co-author-harness:evaluator"}, project)
    fire({"hook_event_name": "SessionEnd"}, project)
    assert not data.exists()


@pytest.mark.parametrize("stdin", ["", "not json", "[1,2]", "null", "{\"hook_event_name\": 5}"])
def test_malformed_stdin_exits_zero_and_silent(stdin):
    proc = subprocess.run([sys.executable, "-B", str(SCRIPT)], input=stdin, text=True,
                          capture_output=True, encoding="utf-8", errors="replace")
    assert proc.returncode == 0
    assert proc.stdout == ""


def test_unwritable_ledger_never_blocks(project, data):
    data.write_text("a file where a directory is needed", encoding="utf-8")
    fire({"hook_event_name": "SubagentStart", "agent_type": "co-author-harness:evaluator",
          "agent_id": "e"}, project)


def test_disable_switch(project, data, monkeypatch):
    monkeypatch.setenv("COAUTHOR_ROLE_LEDGER_DISABLE", "1")
    fire({"hook_event_name": "SubagentStart", "agent_type": "co-author-harness:evaluator",
          "agent_id": "e"}, project)
    assert not data.exists()


def test_held_lock_drops_event_with_note_never_writes_unlocked(project, ledger, monkeypatch, capsys):
    monkeypatch.setattr(rl._Lock, "LOCK_WAIT", 0.2)
    ledger.parent.mkdir(parents=True)
    lock = ledger.parent / (rl.LEDGER_NAME + ".lock")
    lock.write_text("", encoding="utf-8")
    fire({"hook_event_name": "SubagentStart", "agent_type": "co-author-harness:evaluator",
          "agent_id": "e"}, project)
    assert not ledger.exists()
    assert "ledger busy, event dropped" in capsys.readouterr().err
    assert lock.exists()  # a live lock is left alone


def test_stale_lock_is_broken_after_30_seconds(project, ledger):
    ledger.parent.mkdir(parents=True)
    lock = ledger.parent / (rl.LEDGER_NAME + ".lock")
    lock.write_text("", encoding="utf-8")
    old = time.time() - 31
    os.utime(lock, (old, old))
    fire({"hook_event_name": "SubagentStart", "agent_type": "co-author-harness:evaluator",
          "agent_id": "e"}, project)
    assert len(read(ledger)) == 1 and not lock.exists()


def test_state_tmp_name_carries_pid_and_is_cleaned(project, ledger, monkeypatch):
    tmp_names = []
    real_replace = os.replace

    def spy(src, dst):
        tmp_names.append(Path(src).name)
        return real_replace(src, dst)

    monkeypatch.setattr(rl.os, "replace", spy)
    fire({"hook_event_name": "UserPromptExpansion", "command_name": "run-iterate"}, project)
    assert tmp_names == [f"{rl.STATE_NAME}.{os.getpid()}.tmp"]
    assert not list(ledger.parent.glob("*.tmp"))
    assert (ledger.parent / rl.STATE_NAME).is_file()


def test_hooks_json_wiring():
    hooks = json.loads((HOOKS.parent.parent / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    def mentions(entries):
        return any("role_ledger.py" in a for e in entries for h in e["hooks"] for a in h.get("args", []))
    for event in ("SubagentStart", "SubagentStop", "UserPromptExpansion", "SessionEnd"):
        assert mentions(hooks[event]), event
    # Stop is end-of-turn: the ledger is not wired there (the Planner exits at SessionEnd).
    assert not mentions(hooks["Stop"])
    assert any("full_run_pretooluse_gate.py" in a for e in hooks["Stop"]
               for h in e["hooks"] for a in h.get("args", []))
    skill = [e for e in hooks["PreToolUse"] if e.get("matcher") == "Skill"]
    assert skill and mentions(skill)
    # The existing gate entries are untouched.
    assert any("full_run_pretooluse_gate.py" in a for e in hooks["PreToolUse"]
               for h in e["hooks"] for a in h.get("args", []))
    codex = json.loads((HOOKS.parent.parent / "hooks" / "codex.json").read_text(encoding="utf-8"))["hooks"]
    assert any("role_ledger.py" in h["command"] for e in codex["PreToolUse"] for h in e["hooks"])
    assert any("role_ledger.py" in h["command"] for e in codex["Stop"] for h in e["hooks"])


def _state_keys(data):
    path = data / "roles" / rl.STATE_NAME
    if not path.is_file():
        return set()
    state = json.loads(path.read_text(encoding="utf-8"))
    keys = set(state.get("open", {})) | set(state.get("seen", {}))
    assert "None" not in keys and "" not in keys
    assert "None" not in path.read_text(encoding="utf-8")
    return keys


@pytest.mark.parametrize("missing", [None, "", "   "])
def test_subagent_enter_without_session_id_records_null_and_no_state(
        project, data, ledger, capsys, missing):
    fire({"hook_event_name": "SubagentStart", "agent_type": "co-author-harness:evaluator",
          "agent_id": "a1"}, project, session_id=missing)
    rows = read(ledger)
    assert len(rows) == 1 and rows[0]["session_id"] is None and rows[0]["event"] == "enter"
    assert _state_keys(data) == set()
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "without a session id" in captured.err and len(captured.err.strip().splitlines()) == 1


def test_planner_enter_and_session_end_without_session_id_store_no_state(
        project, data, ledger, capsys):
    fire({"hook_event_name": "UserPromptExpansion", "command_name": "run-draft"},
         project, session_id=None)
    rows = read(ledger)
    assert [(r["event"], r["session_id"]) for r in rows] == [("enter", None)]
    assert _state_keys(data) == set()
    capsys.readouterr()
    fire({"hook_event_name": "SessionEnd"}, project, session_id=None)
    assert len(read(ledger)) == 1  # the exit records nothing
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "without a session id" in captured.err and len(captured.err.strip().splitlines()) == 1
    # a real session is unaffected and never shares a key with the id-less one
    fire({"hook_event_name": "UserPromptExpansion", "command_name": "run-draft"}, project)
    assert _state_keys(data) == {"S1"}
    fire({"hook_event_name": "SessionEnd"}, project)
    assert [r["event"] for r in read(ledger)] == ["enter", "enter", "exit"]


def test_codex_spawn_and_stop_without_session_id_write_no_turn_end(
        project, data, ledger, monkeypatch, capsys):
    monkeypatch.setenv("COAUTHOR_ROLE_LEDGER_HOST", "codex")
    fire({"hook_event_name": "PreToolUse", "tool_name": "spawn_agent",
          "tool_input": {"agent_type": "worker"}}, project, session_id=None)
    fire({"hook_event_name": "Stop"}, project, session_id=None)
    rows = read(ledger)
    assert [(r["event"], r["session_id"]) for r in rows] == [("enter", None)]
    assert _state_keys(data) == set()
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.count("without a session id") == 2
    # a Stop with an id still needs an entry noted under that same id
    fire({"hook_event_name": "Stop"}, project, session_id="S1")
    assert [r["event"] for r in read(ledger)] == ["enter"]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
