#!/usr/bin/env python3
"""Regression contract for the full-run enforcement entry surfaces.

This suite is intentionally synthetic.  It does not touch a live essay tree,
does not depend on the domain corpus, and does not decide lifecycle truth.  It
pins only the wrappers around ``full_run_contract_check.py``:

* full-run regressions belong to the authoritative fixture registry and the
  release gate invokes that registry once, rather than maintaining a second
  suite list;
* Claude Code's observed subagent tool name (``Task``), plus the SDK/forward
  compatible ``Agent`` spelling, must be intercepted only when a parent run
  scope is explicitly active;
* path spelling must not bypass a manuscript write refusal;
* malformed hook payloads must fail closed while a parent scope is active;
* the post-hoc report must preserve the authoritative gate's no-verdict state;
* discovery must recognize either native project scaffold marker, while callers
  may still name an expected loose run root in a mixed tree.

Run:  python scripts/full_run_enforcement_surfaces_smoketest.py
Exit: 0 all checks pass; 1 one or more checks fail.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import re
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FAILURES: list[str] = []
CHECK_COUNT = 0
# 34 existing checks plus 20 R-6/R-7 checks, plus 12 adhoc_review dispatch
# checks. No platform split.
EXPECTED_CHECKS = 84


def check(name: str, ok: bool, detail: str = "") -> None:
    global CHECK_COUNT
    CHECK_COUNT += 1
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{(' - ' + detail) if detail else ''}")
    if not ok:
        FAILURES.append(name)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def case_release_gate_uses_fixture_authority() -> None:
    text = (ROOT / "scripts" / "release-gate.sh").read_text(encoding="utf-8")
    runner = load_module(
        "fixture_runner_full_run_surface",
        ROOT / "scripts" / "analysis" / "fixture_runner.py",
    )
    required = {
        "scripts/full_run_contract_smoketest.py",
        "scripts/full_run_semantic_bypass_smoketest.py",
        "scripts/full_run_enforcement_surfaces_smoketest.py",
        "scripts/corpus_root_portability_smoketest.py",
    }
    check("all full-run enforcement suites are registry-owned",
          required <= set(runner.REGISTRY),
          repr(sorted(required - set(runner.REGISTRY))))
    check("release gate invokes the authoritative registry in non-writing mode",
          'fixture_runner.py" --no-write' in text)
    check("release gate has no independent full-run suite list",
          not any(Path(rel).name in text for rel in required))


def case_current_agent_interface_and_scope_activation() -> None:
    config = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    matcher = config["hooks"]["PreToolUse"][0]["matcher"]
    tokens = set(matcher.split("|"))
    check("observed Claude Code Task tool is matched", "Task" in tokens, matcher)
    check("Agent compatibility tool is matched", "Agent" in tokens, matcher)
    check("MultiEdit manuscript writes are matched", "MultiEdit" in tokens, matcher)
    check("NotebookEdit writes are matched", "NotebookEdit" in tokens, matcher)

    hook = load_module(
        "full_run_pretooluse_gate",
        ROOT / "scripts" / "hooks" / "full_run_pretooluse_gate.py",
    )
    handler = getattr(hook, "_handle_agent", None)
    check("hook exposes the Agent handler", callable(handler))
    if not callable(handler):
        return

    old = os.environ.pop("FRC_PARENT_SCOPE", None)
    try:
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = handler({"prompt": "Fix the parser and run tests."})
        check("ordinary subagent dispatch is unaffected without an active run scope",
              rc == 0 and not out.getvalue().strip(), out.getvalue().strip())

        os.environ["FRC_PARENT_SCOPE"] = "full_lifecycle"
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = handler({"prompt": "run_scope: adhoc_review\nReturn findings only."})
        decision = json.loads(out.getvalue()) if out.getvalue().strip() else {}
        check("active full run refuses a narrowed subagent brief",
              rc == 0
              and decision.get("hookSpecificOutput", {}).get("permissionDecision") == "deny",
              out.getvalue().strip())

        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Task",
            "tool_input": {"prompt": "run_scope: adhoc_review\nReturn findings only."},
        }
        old_stdin = hook.sys.stdin
        hook.sys.stdin = io.StringIO(json.dumps(payload))
        try:
            with contextlib.redirect_stdout(io.StringIO()) as out:
                rc = hook.main()
        finally:
            hook.sys.stdin = old_stdin
        decision = json.loads(out.getvalue()) if out.getvalue().strip() else {}
        check("observed Task host spelling routes through scope enforcement",
              rc == 0
              and decision.get("hookSpecificOutput", {}).get("permissionDecision") == "deny",
              out.getvalue().strip())

        with tempfile.TemporaryDirectory() as td:
            payload = {
                "hook_event_name": "PreToolUse",
                "tool_name": "MultiEdit",
                "cwd": td,
                "tool_input": {
                    "file_path": "manuscript/essay.md",
                    "edits": [{"old_string": "a", "new_string": "b"}],
                },
            }
            old_stdin = hook.sys.stdin
            hook.sys.stdin = io.StringIO(json.dumps(payload))
            try:
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    rc = hook.main()
            finally:
                hook.sys.stdin = old_stdin
            decision = json.loads(out.getvalue()) if out.getvalue().strip() else {}
            check("MultiEdit routes through manuscript authorization",
                  rc == 0
                  and decision.get("hookSpecificOutput", {}).get("permissionDecision") == "deny",
                  out.getvalue().strip())
    finally:
        if old is None:
            os.environ.pop("FRC_PARENT_SCOPE", None)
        else:
            os.environ["FRC_PARENT_SCOPE"] = old


def case_lab_hook_public_router_and_role_propagation() -> None:
    """C1 red boundary across the hook, public router, and role briefs."""
    hook = load_module(
        "full_run_pretooluse_gate_lab_scope",
        ROOT / "scripts" / "hooks" / "full_run_pretooluse_gate.py",
    )
    check(
        "hook scope vocabulary is exactly the four declared scopes",
        set(getattr(hook, "SCOPES", set()))
        == {"adhoc_review", "project_independent", "lab_iteration", "full_lifecycle"},
        repr(getattr(hook, "SCOPES", None)),
    )
    old = os.environ.get("FRC_PARENT_SCOPE")
    os.environ["FRC_PARENT_SCOPE"] = "lab_iteration"
    try:
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = hook._handle_agent({
                "prompt": (
                    "run_scope: lab_iteration\n"
                    "Inspect synthetic evidence and return a proposal only.\n"
                )
            })
        check(
            "hook permits exact lab child propagation without a deny decision",
            hook._active_parent_scope() == "lab_iteration"
            and rc == 0
            and not out.getvalue().strip(),
            out.getvalue().strip(),
        )

        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = hook._handle_agent({
                "prompt": "run_scope: full_lifecycle\nAdvance the lifecycle.\n"
            })
        decision = json.loads(out.getvalue()) if out.getvalue().strip() else {}
        reason = decision.get("hookSpecificOutput", {}).get(
            "permissionDecisionReason", ""
        )
        check(
            "hook refuses lab-to-full escalation with the authoritative code",
            rc == 0
            and decision.get("hookSpecificOutput", {}).get("permissionDecision")
            == "deny"
            and "FRC-SCOPE-ESCALATION" in reason,
            out.getvalue().strip(),
        )

        with tempfile.TemporaryDirectory() as td:
            with contextlib.redirect_stdout(io.StringIO()) as out:
                rc = hook._handle_stop({
                    "cwd": td,
                    "last_assistant_message": "Laboratory run shipped; terminal PASS.",
                })
            decision = json.loads(out.getvalue()) if out.getvalue().strip() else {}
            check(
                "hook specifically blocks terminal language under lab scope",
                rc == 0
                and decision.get("decision") == "block"
                and "FRC-LAB-TERMINAL-FORBIDDEN" in decision.get("reason", ""),
                out.getvalue().strip(),
            )
    finally:
        if old is None:
            os.environ.pop("FRC_PARENT_SCOPE", None)
        else:
            os.environ["FRC_PARENT_SCOPE"] = old

    public_router = (ROOT / "skills" / "run-draft" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    router_low = " ".join(public_router.casefold().split())
    for token in ("`adhoc_review`", "`project_independent`", "`lab_iteration`", "`full_lifecycle`"):
        check(f"public /run-draft names {token}", token in router_low)
    check(
        "public /run-draft routes lab work as proposal-only without lifecycle/F9 authority",
        "proposal-only" in router_low
        and "no lifecycle" in router_low
        and ("no f9" in router_low or "f9 authority" in router_low),
    )

    role_paths = {
        "Planner": ROOT / "agents" / "planner.md",
        "Generator": ROOT / "agents" / "generator.md",
        "Evaluator": ROOT / "agents" / "evaluator.md",
    }
    for role, path in role_paths.items():
        role_text = path.read_text(encoding="utf-8")
        role_low = role_text.casefold()
        check(
            f"{role} names the exact four-scope vocabulary",
            all(scope in role_low for scope in (
                "adhoc_review", "project_independent", "lab_iteration", "full_lifecycle"
            )),
        )
        check(
            f"{role} binds child run_scope to the parent exactly",
            "run_scope:" in role_text
            and bool(re.search(
                r"(?:matching|matches|match).{0,80}(?:parent|parent's)",
                role_text,
                flags=re.IGNORECASE | re.DOTALL,
            )),
        )


def case_malformed_payload_fails_closed_only_when_scope_is_active() -> None:
    hook = load_module(
        "full_run_pretooluse_gate_malformed",
        ROOT / "scripts" / "hooks" / "full_run_pretooluse_gate.py",
    )
    old_scope = os.environ.pop("FRC_PARENT_SCOPE", None)
    old_stdin = hook.sys.stdin
    try:
        hook.sys.stdin = io.StringIO("{")
        with contextlib.redirect_stdout(io.StringIO()) as out, \
             contextlib.redirect_stderr(io.StringIO()):
            rc = hook.main()
        check("malformed ordinary-session payload remains inert",
              rc == 0 and not out.getvalue().strip(), out.getvalue().strip())

        os.environ["FRC_PARENT_SCOPE"] = "full_lifecycle"
        hook.sys.stdin = io.StringIO("{")
        with contextlib.redirect_stdout(io.StringIO()) as out, \
             contextlib.redirect_stderr(io.StringIO()):
            rc = hook.main()
        decision = json.loads(out.getvalue()) if out.getvalue().strip() else {}
        check("malformed active-scope payload is denied",
              rc == 0
              and decision.get("hookSpecificOutput", {}).get("permissionDecision") == "deny",
              out.getvalue().strip())
    finally:
        hook.sys.stdin = old_stdin
        if old_scope is None:
            os.environ.pop("FRC_PARENT_SCOPE", None)
        else:
            os.environ["FRC_PARENT_SCOPE"] = old_scope


def case_path_normalization_blocks_forward_slashes() -> None:
    hook = load_module(
        "full_run_pretooluse_gate_path",
        ROOT / "scripts" / "hooks" / "full_run_pretooluse_gate.py",
    )
    old = os.environ.get("FRC_PARENT_SCOPE")
    os.environ["FRC_PARENT_SCOPE"] = "full_lifecycle"
    try:
        with tempfile.TemporaryDirectory() as td:
            target = (Path(td) / "manuscript" / "essay.md").as_posix()
            with contextlib.redirect_stdout(io.StringIO()) as out:
                rc = hook._handle_write({"file_path": target})
            decision = json.loads(out.getvalue()) if out.getvalue().strip() else {}
            check("forward-slash manuscript path cannot bypass authorization",
                  rc == 0
                  and decision.get("hookSpecificOutput", {}).get("permissionDecision") == "deny",
                  out.getvalue().strip())
    finally:
        if old is None:
            os.environ.pop("FRC_PARENT_SCOPE", None)
        else:
            os.environ["FRC_PARENT_SCOPE"] = old


def case_terminal_claim_is_guarded_only_when_scope_is_active() -> None:
    config = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    check("Stop hook is installed for terminal-claim enforcement",
          bool(config["hooks"].get("Stop")))
    hook = load_module(
        "full_run_pretooluse_gate_stop",
        ROOT / "scripts" / "hooks" / "full_run_pretooluse_gate.py",
    )
    old = os.environ.pop("FRC_PARENT_SCOPE", None)
    try:
        with tempfile.TemporaryDirectory() as td:
            payload = {
                "hook_event_name": "Stop",
                "cwd": td,
                "last_assistant_message": "Ladder complete; terminal PASS.",
            }
            with contextlib.redirect_stdout(io.StringIO()) as out:
                rc = hook._handle_stop(payload)
            check("ordinary non-lifecycle response is unaffected",
                  rc == 0 and not out.getvalue().strip(), out.getvalue().strip())

            os.environ["FRC_PARENT_SCOPE"] = "full_lifecycle"
            with contextlib.redirect_stdout(io.StringIO()) as out:
                rc = hook._handle_stop(payload)
            decision = json.loads(out.getvalue()) if out.getvalue().strip() else {}
            check("active full run blocks an unearned terminal claim",
                  rc == 0 and decision.get("decision") == "block",
                  out.getvalue().strip())
    finally:
        if old is None:
            os.environ.pop("FRC_PARENT_SCOPE", None)
        else:
            os.environ["FRC_PARENT_SCOPE"] = old


def case_report_preserves_no_verdict_and_expected_roots() -> None:
    report = load_module(
        "full_run_completeness_report",
        ROOT / "scripts" / "full_run_completeness_report.py",
    )
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        project = root / "real-project"
        (project / "reviews").mkdir(parents=True)
        (project / "reviews" / "phase_state.json").write_text("{}", encoding="utf-8")
        contract_only = root / "contract-only-project"
        (contract_only / "reviews").mkdir(parents=True)
        (contract_only / "reviews" / "assignment_contract.json").write_text(
            "{}", encoding="utf-8"
        )
        loose = root / "narrated-output"
        loose.mkdir()

        original = report._gate_terminal
        report._gate_terminal = lambda _root: (2, "environment error")
        try:
            record = report.evaluate(project)
        finally:
            report._gate_terminal = original
        check("authoritative exit 2 remains UNVERIFIABLE",
              record.get("verdict") == "UNVERIFIABLE"
              and record.get("exit_hint") == 3,
              repr(record))

        roots = report.discover(root, [loose])
        check("mixed-tree scan retains an explicitly expected loose run root",
              project in roots and contract_only in roots and loose in roots,
              repr(roots))


SCOPE_KEYS = ("FRC_PARENT_SCOPE", "FRC_REQUIRE_SCOPE", "FRC_GATE_HOOK_DISABLE")
NO_MARKER_MESSAGE = "Results and evidence are available at the paths above."


@contextlib.contextmanager
def isolated_scope_env(**updates: str | None):
    old = {key: os.environ.get(key) for key in SCOPE_KEYS}
    for key in SCOPE_KEYS:
        os.environ.pop(key, None)
    for key, value in updates.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    try:
        yield
    finally:
        for key, value in old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def run_hook_main(hook, payload=None, stdin_text=None) -> tuple[int, str, str]:
    old_stdin = hook.sys.stdin
    hook.sys.stdin = io.StringIO(
        stdin_text if stdin_text is not None else json.dumps(payload)
    )
    try:
        with contextlib.redirect_stdout(io.StringIO()) as out, \
             contextlib.redirect_stderr(io.StringIO()) as err:
            rc = hook.main()
        return rc, out.getvalue(), err.getvalue()
    finally:
        hook.sys.stdin = old_stdin


def ordinary_write_payload(cwd: str) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "cwd": cwd,
        "tool_input": {"file_path": "src/parser.py", "content": "x = 1\n"},
    }


def stop_payload(cwd: str, message: str) -> dict:
    return {
        "hook_event_name": "Stop",
        "cwd": cwd,
        "last_assistant_message": message,
    }


def write_synthetic_terminal_state(root: Path) -> None:
    reviews = root / "reviews"
    reviews.mkdir(parents=True)
    (reviews / "assignment_contract.json").write_text(
        json.dumps({"status": "resolved"}), encoding="utf-8"
    )
    (reviews / "phase_state.json").write_text(
        json.dumps({
            "terminal_phase_reached": True,
            "terminal_round_id": "round_2026-08-21_001",
            "milestone_framework": {"mode": "native", "milestones": {}, "events": []},
            "sections": {},
        }),
        encoding="utf-8",
    )


def case_r6_require_scope_and_passthrough() -> None:
    hook = load_module(
        "full_run_pretooluse_gate_r6",
        ROOT / "scripts" / "hooks" / "full_run_pretooluse_gate.py",
    )
    with tempfile.TemporaryDirectory() as td:
        write_pl = ordinary_write_payload(td)
        stop_pl = stop_payload(td, "Ladder complete; terminal PASS.")

        with isolated_scope_env():
            rc, out, err = run_hook_main(hook, write_pl)
            check(
                "R6.1 default Write is allowed but loud passthrough",
                rc == 0 and not out.strip()
                and "FRC-SCOPE-PASSTHROUGH" in err and "Write" in err,
                f"rc={rc} out={out!r} err={err!r}",
            )
            rc, out, err = run_hook_main(hook, stop_pl)
            check(
                "R6.1 default Stop is allowed but loud passthrough",
                rc == 0 and not out.strip()
                and "FRC-SCOPE-PASSTHROUGH" in err and "Stop" in err,
                f"rc={rc} out={out!r} err={err!r}",
            )

        with isolated_scope_env(FRC_REQUIRE_SCOPE="1"):
            rc, out, err = run_hook_main(hook, write_pl)
            decision = json.loads(out) if out.strip() else {}
            reason = decision.get("hookSpecificOutput", {}).get(
                "permissionDecisionReason", ""
            )
            check(
                "R6.2 REQUIRE_SCOPE=1 Write denies SCOPE-REQUIRED",
                rc == 0
                and decision.get("hookSpecificOutput", {}).get("permissionDecision")
                == "deny"
                and "FRC-SCOPE-REQUIRED" in reason,
                out.strip(),
            )
            rc, out, err = run_hook_main(hook, stop_pl)
            decision = json.loads(out) if out.strip() else {}
            check(
                "R6.2 REQUIRE_SCOPE=1 Stop blocks SCOPE-REQUIRED",
                rc == 0
                and decision.get("decision") == "block"
                and "FRC-SCOPE-REQUIRED" in decision.get("reason", ""),
                out.strip(),
            )

        with isolated_scope_env(FRC_PARENT_SCOPE="full_lifecyle"):
            rc, out, err = run_hook_main(hook, write_pl)
            decision = json.loads(out) if out.strip() else {}
            reason = decision.get("hookSpecificOutput", {}).get(
                "permissionDecisionReason", ""
            )
            check(
                "R6.3 unknown-scope ordinary Write stays denied SCOPE-UNKNOWN",
                rc == 0
                and decision.get("hookSpecificOutput", {}).get("permissionDecision")
                == "deny"
                and "FRC-SCOPE-UNKNOWN" in reason
                and "PASSTHROUGH" not in err,
                f"out={out!r} err={err!r}",
            )
            rc, out, err = run_hook_main(hook, stop_pl)
            decision = json.loads(out) if out.strip() else {}
            check(
                "R6.3 unknown-scope Stop blocks SCOPE-UNKNOWN",
                rc == 0
                and decision.get("decision") == "block"
                and "FRC-SCOPE-UNKNOWN" in decision.get("reason", "")
                and "PASSTHROUGH" not in err,
                f"out={out!r} err={err!r}",
            )

        with isolated_scope_env():
            rc, out, err = run_hook_main(hook, stdin_text="{")
            check(
                "R6.4 default malformed stdin is loud passthrough",
                rc == 0 and not out.strip()
                and "FRC-HOOK-ERROR" in err and "FRC-SCOPE-PASSTHROUGH" in err,
                f"out={out!r} err={err!r}",
            )
        with isolated_scope_env(FRC_REQUIRE_SCOPE="1"):
            rc, out, err = run_hook_main(hook, stdin_text="{")
            decision = json.loads(out) if out.strip() else {}
            check(
                "R6.4 REQUIRE_SCOPE=1 malformed stdin denies with stderr",
                rc == 0
                and decision.get("hookSpecificOutput", {}).get("permissionDecision")
                == "deny"
                and bool(err.strip())
                and "FRC-HOOK-ERROR" in err,
                f"out={out!r} err={err!r}",
            )

        old_write = hook._handle_write
        old_stop = hook._handle_stop

        def boom_write(*_a, **_k):
            raise RuntimeError("injected write failure")

        def boom_stop(*_a, **_k):
            raise RuntimeError("injected stop failure")

        hook._handle_write = boom_write
        hook._handle_stop = boom_stop
        try:
            with isolated_scope_env():
                rc, out, err = run_hook_main(hook, write_pl)
                check(
                    "R6.4 default internal Write error is loud passthrough",
                    rc == 0 and not out.strip()
                    and "FRC-HOOK-ERROR" in err and "FRC-SCOPE-PASSTHROUGH" in err,
                    f"out={out!r} err={err!r}",
                )
                rc, out, err = run_hook_main(hook, stop_pl)
                check(
                    "R6.4 default internal Stop error is loud passthrough",
                    rc == 0 and not out.strip()
                    and "FRC-HOOK-ERROR" in err and "FRC-SCOPE-PASSTHROUGH" in err,
                    f"out={out!r} err={err!r}",
                )
            with isolated_scope_env(FRC_REQUIRE_SCOPE="1"):
                rc, out, err = run_hook_main(hook, write_pl)
                decision = json.loads(out) if out.strip() else {}
                check(
                    "R6.4 REQUIRE_SCOPE=1 internal Write error denies",
                    rc == 0
                    and decision.get("hookSpecificOutput", {}).get(
                        "permissionDecision"
                    ) == "deny"
                    and "FRC-HOOK-ERROR" in err,
                    f"out={out!r} err={err!r}",
                )
                rc, out, err = run_hook_main(hook, stop_pl)
                decision = json.loads(out) if out.strip() else {}
                check(
                    "R6.4 REQUIRE_SCOPE=1 internal Stop error blocks",
                    rc == 0
                    and decision.get("decision") == "block"
                    and "FRC-HOOK-ERROR" in err,
                    f"out={out!r} err={err!r}",
                )
        finally:
            hook._handle_write = old_write
            hook._handle_stop = old_stop

        with isolated_scope_env(FRC_REQUIRE_SCOPE="0"):
            rc, out, err = run_hook_main(hook, write_pl)
            check(
                "REQUIRE_SCOPE=0 behaves as default passthrough",
                rc == 0 and not out.strip() and "FRC-SCOPE-PASSTHROUGH" in err,
                f"out={out!r} err={err!r}",
            )
        with isolated_scope_env(FRC_REQUIRE_SCOPE="1", FRC_GATE_HOOK_DISABLE="1"):
            rc, out, err = run_hook_main(hook, write_pl)
            check(
                "explicit disable wins over REQUIRE_SCOPE=1",
                rc == 0 and not out.strip() and "FRC-SCOPE-REQUIRED" not in out
                and "PASSTHROUGH" not in err,
                f"out={out!r} err={err!r}",
            )
        with isolated_scope_env(FRC_PARENT_SCOPE="full_lifecycle"):
            rc, out, err = run_hook_main(hook, write_pl)
            check(
                "valid full_lifecycle emits no passthrough notice",
                rc == 0 and "PASSTHROUGH" not in err,
                f"out={out!r} err={err!r}",
            )


def case_r7_structured_terminal_detection() -> None:
    hook = load_module(
        "full_run_pretooluse_gate_r7",
        ROOT / "scripts" / "hooks" / "full_run_pretooluse_gate.py",
    )
    markers = tuple(m.casefold() for m in hook.TERMINAL_MARKERS)
    folded = " ".join(NO_MARKER_MESSAGE.casefold().split())
    check(
        "R7 message contains none of TERMINAL_MARKERS",
        not any(marker in folded for marker in markers),
        folded,
    )
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        write_synthetic_terminal_state(root)
        payload = stop_payload(str(root), NO_MARKER_MESSAGE)
        with isolated_scope_env(FRC_PARENT_SCOPE="full_lifecycle"):
            rc, out, err = run_hook_main(hook, payload)
            decision = json.loads(out) if out.strip() else {}
            check(
                "R7.1 structured terminal with no marker engages and blocks UNPROVEN",
                rc == 0
                and decision.get("decision") == "block"
                and "FRC-TERMINAL-UNPROVEN" in decision.get("reason", ""),
                f"out={out!r} err={err!r}",
            )

            calls: list[tuple] = []
            original = hook._run_gate

            def recorder(*args: str):
                calls.append(args)
                return 0, json.dumps({"ok": True, "findings": []})

            hook._run_gate = recorder
            try:
                rc, out, err = run_hook_main(hook, payload)
                check(
                    "R7.2 structured terminal delegates exactly one terminal call",
                    rc == 0
                    and not out.strip()
                    and calls == [("terminal", "--project-root", str(root))],
                    f"rc={rc} out={out!r} calls={calls!r}",
                )
            finally:
                hook._run_gate = original

            false_state = json.loads(
                (root / "reviews" / "phase_state.json").read_text(encoding="utf-8")
            )
            false_state["terminal_phase_reached"] = False
            false_state["terminal_round_id"] = None
            (root / "reviews" / "phase_state.json").write_text(
                json.dumps(false_state), encoding="utf-8"
            )
            calls.clear()
            hook._run_gate = recorder
            try:
                rc, out, err = run_hook_main(
                    hook, stop_payload(str(root), NO_MARKER_MESSAGE)
                )
                check(
                    "full_lifecycle terminal false + no marker does not call the gate",
                    rc == 0 and not out.strip() and calls == [],
                    f"out={out!r} calls={calls!r}",
                )
                rc, out, err = run_hook_main(
                    hook, stop_payload(str(root), "Ladder complete; terminal PASS.")
                )
                check(
                    "false state + marker still invokes the terminal gate",
                    rc == 0 and calls == [("terminal", "--project-root", str(root))],
                    f"out={out!r} calls={calls!r}",
                )
            finally:
                hook._run_gate = original


def _decision(out: str) -> dict:
    return json.loads(out) if out.strip() else {}


def _denied(out: str, code: str = "") -> bool:
    spec = _decision(out).get("hookSpecificOutput", {})
    return spec.get("permissionDecision") == "deny" and code in spec.get(
        "permissionDecisionReason", ""
    )


def case_territory_scoping_and_artifact_protection() -> None:
    """Folder names alone never deny; lifecycle artefacts stay gated in scope.

    Regression for the 2026-09-25 audit: an unscoped session was denied any
    path with a ``research``/``milestones`` segment anywhere on disk, while a
    declared read-only ``adhoc_review`` scope left ``milestones/`` open.
    """
    hook = load_module(
        "full_run_pretooluse_gate_territory",
        ROOT / "scripts" / "hooks" / "full_run_pretooluse_gate.py",
    )
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        plain = base / "plain"
        plain.mkdir()
        project = base / "native-project"
        (project / "reviews").mkdir(parents=True)
        (project / "reviews" / "phase_state.json").write_text("{}", encoding="utf-8")
        draft = project / "milestones" / "M4_complete_paper_draft.md"
        workspace = base / "ws"
        manifest = workspace / "governance" / "output-routing" / "output_routing.yaml"
        manifest.parent.mkdir(parents=True)
        manifest.write_text("schema_version: 1\n", encoding="utf-8")
        governed_note = workspace / "research" / "60_Workbench" / "w1" / "notes.md"
        governed_deliverable = (
            workspace / "research" / "60_Workbench" / "w1" / "milestones" / "M4.md"
        )
        shipment = (
            workspace / "research" / "60_Workbench" / "w1" / "reviews" / "harness"
            / "shipments" / "s1" / "report.md"
        )

        def write(path: Path, cwd: Path, tool: str = "Write") -> dict:
            return {
                "hook_event_name": "PreToolUse",
                "tool_name": tool,
                "cwd": str(cwd),
                "tool_input": {"file_path": str(path), "content": "x\n"},
            }

        def agent(prompt: str, cwd: Path) -> dict:
            return {
                "hook_event_name": "PreToolUse",
                "tool_name": "Task",
                "cwd": str(cwd),
                "tool_input": {"prompt": prompt},
            }

        with isolated_scope_env():
            rc, out, err = run_hook_main(
                hook, write(base / "Research" / "thesis" / "notes.md", plain)
            )
            check("unscoped Write under an ordinary Research folder passes",
                  rc == 0 and not out.strip() and "FRC-SCOPE-PASSTHROUGH" in err,
                  f"out={out!r}")
            rc, out, _ = run_hook_main(
                hook, write(plain / "src" / "milestones" / "api.py", plain, "Edit")
            )
            check("unscoped Edit to an unrelated milestones/ module passes",
                  rc == 0 and not out.strip(), f"out={out!r}")
            rc, out, _ = run_hook_main(hook, write(draft, project))
            check("unscoped Write to a native project's M4 draft is denied",
                  _denied(out, "FRC-SCOPE-REQUIRED"), out.strip())
            rc, out, _ = run_hook_main(hook, write(governed_note, workspace))
            check("unscoped Write inside a governed research tree is denied",
                  _denied(out, "FRC-SCOPE-REQUIRED"), out.strip())
            brief = "Summarize the manuscript upload endpoint."
            rc, out, _ = run_hook_main(hook, agent(brief, plain))
            check("unscoped brief naming manuscript outside harness territory passes",
                  rc == 0 and not out.strip(), f"out={out!r}")
            rc, out, _ = run_hook_main(hook, agent(brief, project))
            check("unscoped brief naming manuscript inside a native project is denied",
                  _denied(out, "FRC-SCOPE-REQUIRED"), out.strip())
            rc, out, _ = run_hook_main(
                hook, agent("Use run-generator-session on this text.", plain)
            )
            check("unscoped run-generator-session brief is denied anywhere",
                  _denied(out, "FRC-SCOPE-REQUIRED"), out.strip())
            rc, out, err = run_hook_main(hook, stdin_text="[1, 2]")
            check("unscoped non-object payload is a loud passthrough",
                  rc == 0 and not out.strip() and "FRC-HOOK-ERROR" in err,
                  f"out={out!r} err={err!r}")

        with isolated_scope_env(FRC_PARENT_SCOPE="adhoc_review"):
            rc, out, _ = run_hook_main(hook, write(draft, project, "Edit"))
            check("adhoc_review Edit to the canonical M4 draft is refused",
                  _denied(out, "FRC-PROSE-FORBIDDEN"), out.strip())

        with isolated_scope_env(FRC_PARENT_SCOPE="full_lifecycle"):
            calls: list[tuple] = []
            original = hook._run_gate

            def refusing_gate(*args: str):
                calls.append(args)
                return 1, json.dumps({"findings": [
                    {"code": "FRC-CONTRACT-MISSING", "message": "recorded"}
                ]})

            hook._run_gate = refusing_gate
            try:
                rc, out, _ = run_hook_main(hook, write(draft, project, "Edit"))
            finally:
                hook._run_gate = original
            check("full_lifecycle Edit to M4 routes through authorize for the project",
                  _denied(out, "FRC-CONTRACT-MISSING")
                  and calls == [("authorize", "--project-root", str(project),
                                 "--run-scope", "full_lifecycle")],
                  f"out={out!r} calls={calls!r}")
            rc, out, _ = run_hook_main(hook, write(governed_deliverable, workspace))
            check("full_lifecycle Write to a protected governed deliverable is DEST-PROTECTED",
                  _denied(out, "DEST-PROTECTED"), out.strip())
            rc, out, _ = run_hook_main(hook, write(shipment, workspace))
            check("full_lifecycle Write to the private shipment lane stays permitted",
                  rc == 0 and not out.strip(), f"out={out!r}")
            rc, out, _ = run_hook_main(hook, stdin_text="[1, 2]")
            check("full_lifecycle non-object payload is denied",
                  _denied(out, "FRC-HOOK-ERROR"), out.strip())

            rc, out, _ = run_hook_main(
                hook, stop_payload(str(plain), "See fig.4 for the chart.")
            )
            check("figure reference is not the G.4 terminal marker",
                  rc == 0 and not out.strip(), f"out={out!r}")
            rc, out, _ = run_hook_main(
                hook, stop_payload(str(plain), "G.4 sign-off recorded.")
            )
            check("a whole-word G.4 claim still engages the terminal gate",
                  rc == 0 and _decision(out).get("decision") == "block",
                  f"out={out!r}")

            terminal = base / "terminal-project"
            write_synthetic_terminal_state(terminal)
            reentry = stop_payload(str(terminal), NO_MARKER_MESSAGE)
            reentry["stop_hook_active"] = True
            rc, out, err = run_hook_main(hook, reentry)
            check("host re-invoked Stop is not re-blocked on structured state alone",
                  rc == 0 and not out.strip() and "FRC-STOP-REENTRY" in err,
                  f"out={out!r} err={err!r}")
            reentry["last_assistant_message"] = "Ladder complete; terminal PASS."
            rc, out, _ = run_hook_main(hook, reentry)
            check("host re-invoked Stop with a fresh terminal claim still blocks",
                  rc == 0 and _decision(out).get("decision") == "block",
                  f"out={out!r}")


def case_adhoc_review_dispatch_without_parent_scope() -> None:
    """A declared read-only adhoc_review brief dispatches without a parent scope.

    Pins 008013f: exactly one ``run_scope: adhoc_review`` declaration lets
    read/review work dispatch from harness territory while FRC_PARENT_SCOPE is
    unset. Affirmative mutation or generator requests, conflicting
    declarations, a malformed or required parent scope, and the child's own
    argument-bearing writes stay refused.
    """
    hook = load_module(
        "full_run_pretooluse_gate_adhoc_dispatch",
        ROOT / "scripts" / "hooks" / "full_run_pretooluse_gate.py",
    )
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        project = base / "native-project"
        (project / "reviews").mkdir(parents=True)
        (project / "reviews" / "phase_state.json").write_text("{}", encoding="utf-8")
        workspace = base / "ws"
        manifest = workspace / "governance" / "output-routing" / "output_routing.yaml"
        manifest.parent.mkdir(parents=True)
        manifest.write_text("schema_version: 1\n", encoding="utf-8")
        governed = workspace / "research" / "60_Workbench" / "w1"
        governed.mkdir(parents=True)

        def agent(prompt: str, cwd: Path) -> dict:
            return {
                "hook_event_name": "PreToolUse",
                "tool_name": "Task",
                "cwd": str(cwd),
                "tool_input": {"prompt": prompt},
            }

        declared = "run_scope: adhoc_review\n"
        review = declared + "Read and review manuscript/essay.md; return findings only."

        def allowed(rc: int, out: str, err: str) -> bool:
            return rc == 0 and not out.strip() and "Agent/Task adhoc_review" in err

        with isolated_scope_env():
            rc, out, err = run_hook_main(hook, agent(review, project))
            check("declared read-only review dispatches from a native project",
                  allowed(rc, out, err), f"out={out!r}")
            rc, out, err = run_hook_main(hook, agent(review, governed))
            check("declared read-only review dispatches from a governed research tree",
                  allowed(rc, out, err), f"out={out!r}")
            rc, out, err = run_hook_main(hook, agent(
                declared + "Do not write or edit anything; read manuscript/essay.md.", project))
            check("prohibition wording is not read as a mutation request",
                  allowed(rc, out, err), f"out={out!r}")
            for label, text in (
                ("a review-then-rewrite request", "Review the draft, then rewrite section 2."),
                ("an imperative revise request", "Please revise the abstract in manuscript/essay.md."),
                ("a generator drafting request", "Use the generator to draft section 3."),
                ("a run-generator-session request", "Run run-generator-session on the manuscript."),
            ):
                rc, out, _ = run_hook_main(hook, agent(declared + text, project))
                check(f"declared adhoc_review brief with {label} is denied",
                      _denied(out, "FRC-PROSE-FORBIDDEN"), out.strip())
            rc, out, _ = run_hook_main(hook, agent(
                declared + "run_scope: full_lifecycle\nReview manuscript/essay.md.", project))
            check("conflicting scope declarations do not unlock dispatch",
                  _denied(out, "FRC-SCOPE-REQUIRED"), out.strip())
            rc, out, _ = run_hook_main(
                hook, agent("Review manuscript/essay.md and return findings.", project))
            check("undeclared manuscript brief is denied with the declaration hint",
                  _denied(out, "FRC-SCOPE-REQUIRED")
                  and "run_scope: adhoc_review" in out, out.strip())
            rc, out, _ = run_hook_main(hook, {
                "hook_event_name": "PreToolUse",
                "tool_name": "Write",
                "cwd": str(project),
                "tool_input": {"file_path": str(project / "manuscript" / "essay.md"),
                               "content": "x\n"},
            })
            check("the dispatch exemption grants no manuscript write",
                  _denied(out, "FRC-SCOPE-REQUIRED"), out.strip())
        with isolated_scope_env(FRC_PARENT_SCOPE="bogus"):
            rc, out, _ = run_hook_main(hook, agent(review, project))
            check("a malformed parent scope does not unlock the exemption",
                  _denied(out, "FRC-SCOPE-REQUIRED"), out.strip())
        with isolated_scope_env(FRC_REQUIRE_SCOPE="1"):
            rc, out, _ = run_hook_main(hook, agent(review, project))
            check("FRC_REQUIRE_SCOPE=1 still requires a parent scope",
                  _denied(out), out.strip())


def main() -> int:
    print("full_run_enforcement_surfaces_smoketest")
    for case in (
        case_release_gate_uses_fixture_authority,
        case_current_agent_interface_and_scope_activation,
        case_lab_hook_public_router_and_role_propagation,
        case_malformed_payload_fails_closed_only_when_scope_is_active,
        case_path_normalization_blocks_forward_slashes,
        case_terminal_claim_is_guarded_only_when_scope_is_active,
        case_report_preserves_no_verdict_and_expected_roots,
        case_r6_require_scope_and_passthrough,
        case_r7_structured_terminal_detection,
        case_territory_scoping_and_artifact_protection,
        case_adhoc_review_dispatch_without_parent_scope,
    ):
        print(f"\n{case.__name__}:")
        try:
            case()
        except Exception as exc:  # noqa: BLE001 - a crash is a failed surface
            check(case.__name__, False, f"raised {type(exc).__name__}: {exc}")
    if CHECK_COUNT != EXPECTED_CHECKS:
        print(f"\nFAIL: denominator {CHECK_COUNT} != {EXPECTED_CHECKS}")
        FAILURES.append("denominator registration")
    if FAILURES:
        print(f"\nFAIL: {len(FAILURES)}: {FAILURES}")
        return 1
    print(
        f"\nPASS: full-run enforcement surfaces are structurally pinned "
        f"({CHECK_COUNT} checks; expected {EXPECTED_CHECKS})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
