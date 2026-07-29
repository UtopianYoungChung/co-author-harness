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


def check(name: str, ok: bool, detail: str = "") -> None:
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
        "hook scope vocabulary is exactly the three charter scopes",
        set(getattr(hook, "SCOPES", set()))
        == {"adhoc_review", "lab_iteration", "full_lifecycle"},
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
    for token in ("`adhoc_review`", "`lab_iteration`", "`full_lifecycle`"):
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
            f"{role} names the exact three-scope vocabulary",
            all(scope in role_low for scope in (
                "adhoc_review", "lab_iteration", "full_lifecycle"
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
    ):
        print(f"\n{case.__name__}:")
        try:
            case()
        except Exception as exc:  # noqa: BLE001 - a crash is a failed surface
            check(case.__name__, False, f"raised {type(exc).__name__}: {exc}")
    if FAILURES:
        print(f"\nFAIL: {len(FAILURES)}: {FAILURES}")
        return 1
    print("\nPASS: full-run enforcement surfaces are structurally pinned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
