#!/usr/bin/env python3
"""Behavioral direct-Python regressions for the durable release controller."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULE = ROOT / "scripts" / "release_qualification_controller.py"
ENVIRONMENT = ROOT / "scripts" / "qualification_environment.py"


def _load(path: Path, name: str):
    assert path.is_file(), f"missing {path.relative_to(ROOT)}"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _expect(code: str, call) -> None:
    try:
        call()
    except Exception as exc:
        assert getattr(exc, "code", None) == code, (code, repr(exc))
        return
    raise AssertionError(f"expected {code}")


def _expect_one(codes: set[str], call) -> None:
    try:
        call()
    except Exception as exc:
        assert getattr(exc, "code", None) in codes, (codes, repr(exc))
        return
    raise AssertionError(f"expected one of {sorted(codes)}")


def _start(ctl, root: Path, run_id: str, code: str, **extra):
    work = root / "work"
    work.mkdir(exist_ok=True)
    extra.setdefault("output_watch_roots", [work])
    cwd = extra.pop("cwd", work)
    return ctl.start_run(
        run_root=root / "runs", run_id=run_id,
        argv=[sys.executable, "-c", code], cwd=cwd, **extra,
    )


def _wait(ctl, root: Path, run_id: str):
    return ctl.wait_run(run_root=root / "runs", run_id=run_id, timeout_s=60)


def _event_names(root: Path, run_id: str) -> list[str]:
    value = json.loads((root / "runs" / run_id / "journal.json").read_text(encoding="ascii"))
    return [row["event"] for row in value["events"]]


def _wait_for_event(root: Path, run_id: str, event: str) -> None:
    for _ in range(200):
        try:
            if event in _event_names(root, run_id):
                return
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        time.sleep(.05)
    raise AssertionError(f"event {event!r} was not journaled")


def main() -> int:
    env = _load(ENVIRONMENT, "qualification_environment")
    ctl = _load(MODULE, "release_qualification_controller")
    cases = 0
    with tempfile.TemporaryDirectory(prefix="release-controller-smoke-") as raw:
        root = Path(raw)

        # Refusal happens before the sentinel child or run directory exists.
        sentinel = root / "ambient-sentinel"
        for key in ("PYTHONUTF8", "PYTHONPATH", "PYTHONHOME", "PYTHONWARNINGS", "PYTHONOPTIMIZE"):
            previous = os.environ.get(key)
            os.environ[key] = "poison"
            try:
                _expect("QUALIFICATION-ENV-AMBIENT", lambda k=key: _start(
                    ctl, root, f"ambient-{k.lower()}",
                    f"from pathlib import Path;Path({str(sentinel)!r}).write_text('ran')",
                ))
            finally:
                if previous is None: os.environ.pop(key, None)
                else: os.environ[key] = previous
        assert not sentinel.exists()
        _expect("RELEASE-CONTROLLER-ENV", lambda: ctl.start_run(
            run_root=root / "runs", run_id="opt-argv",
            argv=[sys.executable, "-O", "-c", "print('no')"], cwd=root / "work",
            output_watch_roots=[root / "work"],
        ))
        cases += 1

        # An unavailable creation token is never evidence that a process is
        # still alive: null must fail closed instead of comparing equal.
        original_process_token = ctl._process_token
        ctl._process_token = lambda _pid: None
        try:
            assert ctl._alive({
                "host": ctl.platform.node(), "pid": os.getpid(),
                "process_token": None, "started_at": "test",
            }) is False
        finally:
            ctl._process_token = original_process_token
        cases += 1

        # The shared delta accounts for scrubbed non-forbidden PYTHON controls.
        base = {"PATH": "x", "PYTHONHASHSEED": "7", "PYTHONDONTWRITEBYTECODE": "1"}
        child_env, delta = env.controlled_environment(base, {"CASE": "delta"})
        assert "PYTHONHASHSEED" not in child_env and delta["PYTHONHASHSEED"] is None
        assert child_env["CASE"] == "delta" and delta["CASE"] == "delta"

        stdout_raw, stderr_raw = "snowman=☃\n".encode(), "error=錯\n".encode()
        code = f"import os;os.write(1,{stdout_raw!r});os.write(2,{stderr_raw!r})"
        _start(ctl, root, "unicode", code)
        receipt = _wait(ctl, root, "unicode")
        assert receipt["state"] == "succeeded"
        assert Path(receipt["stdout"]["path"]).read_bytes() == stdout_raw
        assert Path(receipt["stderr"]["path"]).read_bytes() == stderr_raw
        cases += 1


        # The worker-private marker must not leak into the product child or be
        # omitted from what is claimed as the exact child environment delta.
        marker_output = root / "work" / "worker-marker.txt"
        _start(
            ctl, root, "worker-marker",
            "import os;from pathlib import Path;"
            f"Path({str(marker_output)!r}).write_text(os.environ.get('COAUTHOR_RELEASE_CONTROLLER_WORKER','absent'))",
            allowed_output_roots=[root / "work"],
        )
        receipt = _wait(ctl, root, "worker-marker")
        assert receipt["state"] == "succeeded"
        assert marker_output.read_text() == "absent"
        assert "COAUTHOR_RELEASE_CONTROLLER_WORKER" not in receipt["environment_delta"]
        cases += 1

        _start(ctl, root, "nonzero", "raise SystemExit(23)")
        receipt = _wait(ctl, root, "nonzero")
        assert receipt["state"] == "child_failed" and receipt["exit"]["returncode"] == 23
        assert "exit_capsule_committed" in _event_names(root, "nonzero")
        stdout_path = Path(receipt["stdout"]["path"])
        stdout_bytes = stdout_path.read_bytes()
        stdout_path.write_bytes(stdout_bytes + b"tamper")
        _expect("EVIDENCE_INCOMPLETE", lambda: ctl.status_run(run_root=root / "runs", run_id="nonzero"))
        stdout_path.write_bytes(stdout_bytes)
        assert ctl.status_run(run_root=root / "runs", run_id="nonzero")["state"] == "child_failed"
        cases += 1

        for run_id, fault in (("serialize", "serialization_failure_after_exit"), ("crash", "crash_after_exit")):
            counter = root / "work" / f"{run_id}.counter"
            _start(ctl, root, run_id, f"from pathlib import Path;Path({str(counter)!r}).write_text('once')",
                   _test_fault=fault, allowed_output_roots=[root / "work"])
            receipt = _wait(ctl, root, run_id)
            assert receipt["state"] == "succeeded" and receipt["recovered"] is True
            assert counter.read_text() == "once"
            assert "synthetic_post_exit_failure" in _event_names(root, run_id)
            cases += 1

        counter = root / "work" / "lost.counter"
        _start(ctl, root, "lost", f"from pathlib import Path;Path({str(counter)!r}).write_text('once')",
               _test_fault="lost_exit_status", allowed_output_roots=[root / "work"])
        receipt = _wait(ctl, root, "lost")
        assert receipt["state"] == "evidence_incomplete"
        assert receipt["diagnostic"]["code"] == "EVIDENCE_INCOMPLETE" and counter.read_text() == "once"
        cases += 1

        # The short-lived launcher exits; the detached worker still completes.
        launcher_code = (
            "import site,sys;from pathlib import Path;"
            f"[site.addsitedir(p) for p in {ctl._dependency_paths()!r}];"
            f"sys.path.insert(0,{str(MODULE.parent)!r});import release_qualification_controller as c;"
            f"c.start_run(run_root={str(root / 'runs')!r},run_id='disconnect',"
            f"argv=[sys.executable,'-c','import time;time.sleep(.4);print(99)'],cwd={str(root / 'work')!r},"
            f"output_watch_roots=[{str(root / 'work')!r}])"
        )
        launcher_env, _ = env.controlled_environment()
        launched = subprocess.run([sys.executable, "-c", launcher_code], env=launcher_env,
                                  stdin=subprocess.DEVNULL, capture_output=True, check=False)
        assert launched.returncode == 0, launched.stderr
        receipt = _wait(ctl, root, "disconnect")
        expected_stdout = b"99\r\n" if os.name == "nt" else b"99\n"
        assert receipt["state"] == "succeeded"
        assert Path(receipt["stdout"]["path"]).read_bytes() == expected_stdout
        cases += 1


        # Kill the launcher immediately after it spawns the detached worker,
        # before the launcher can write owner.json.  The worker must establish
        # its own durable identity and complete exactly once.
        crash_counter = root / "work" / "launcher-crash.counter"
        crash_launcher = f"""
import os, site, sys
[site.addsitedir(p) for p in {ctl._dependency_paths()!r}]
sys.path.insert(0, {str(MODULE.parent)!r})
import release_qualification_controller as c
original_popen = c.subprocess.Popen
def spawn_then_die(*args, **kwargs):
    original_popen(*args, **kwargs)
    os._exit(73)
c.subprocess.Popen = spawn_then_die
c.start_run(
    run_root={str(root / 'runs')!r}, run_id='launcher-crash',
    argv=[sys.executable, '-c', {f"from pathlib import Path;Path({str(crash_counter)!r}).write_text('once')"!r}],
    cwd={str(root / 'work')!r},
    allowed_output_roots=[{str(root / 'work')!r}],
    output_watch_roots=[{str(root / 'work')!r}],
)
"""
        crashed = subprocess.run(
            [sys.executable, "-c", crash_launcher], env=launcher_env,
            stdin=subprocess.DEVNULL, capture_output=True, check=False,
        )
        assert crashed.returncode == 73, crashed.stderr
        time.sleep(3.0)
        receipt = _wait(ctl, root, "launcher-crash")
        assert receipt["state"] == "succeeded" and crash_counter.read_text() == "once"
        cases += 1

        idem_output = root / "work" / "idem.out"
        idem_code = f"from pathlib import Path;Path({str(idem_output)!r}).write_text('one')"
        first = _start(ctl, root, "idem", idem_code, allowed_output_roots=[root / "work"])
        _wait(ctl, root, "idem")
        assert idem_output.read_text() == "one"
        replay = _start(ctl, root, "idem", idem_code, allowed_output_roots=[root / "work"])
        assert replay["idempotent"] is True and replay["intent_sha256"] == first["intent_sha256"]
        cases += 1
        _expect("RELEASE-CONTROLLER-INTENT-CONFLICT", lambda: _start(ctl, root, "idem", "print('two')"))
        barrier = threading.Barrier(2)
        outcomes = []
        def competing(code):
            barrier.wait()
            try: outcomes.append(_start(ctl, root, "concurrent-intent", code))
            except Exception as exc: outcomes.append(exc)
        threads = [threading.Thread(target=competing, args=(f"import time;time.sleep(.2);print({n})",)) for n in (1, 2)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        assert sum(isinstance(item, dict) for item in outcomes) == 1
        assert [getattr(item, "code", None) for item in outcomes].count("RELEASE-CONTROLLER-INTENT-CONFLICT") == 1
        _wait(ctl, root, "concurrent-intent")
        cases += 1


        # Alter the committed intent before worker spawn while retaining its
        # self-reported digest.  The substituted command must never execute.
        substituted = root / "work" / "substituted-command.txt"
        original_atomic = ctl._atomic
        def corrupt_intent(path, raw):
            original_atomic(path, raw)
            if path.name == "intent.json" and path.parent.name == "intent-corrupt":
                value = json.loads(path.read_text(encoding="ascii"))
                value["argv"] = [
                    sys.executable, "-c",
                    f"from pathlib import Path;Path({str(substituted)!r}).write_text('ran')",
                ]
                path.write_text(json.dumps(value, sort_keys=True), encoding="ascii")
        ctl._atomic = corrupt_intent
        try:
            try:
                _start(ctl, root, "intent-corrupt", "print('original')",
                       allowed_output_roots=[root / "work"])
            except Exception as exc:
                assert getattr(exc, "code", None) in {
                    "RELEASE-CONTROLLER-INTENT", "RELEASE-CONTROLLER-WORKER-START",
                }, repr(exc)
            else:
                receipt = _wait(ctl, root, "intent-corrupt")
                assert receipt["state"] in {"refused", "evidence_incomplete"}
        finally:
            ctl._atomic = original_atomic
        assert not substituted.exists()
        cases += 1

        # The output baseline and controller timestamp are evidence-bearing
        # intent bytes, not mutable metadata outside the intent digest.
        original_atomic = ctl._atomic
        def corrupt_full_intent(path, raw):
            original_atomic(path, raw)
            if path.name == "intent.json" and path.parent.name == "full-intent-corrupt":
                value = json.loads(path.read_text(encoding="ascii"))
                value["output_preimage"] = {}
                value["created_at"] = "1999-01-01T00:00:00Z"
                path.write_text(json.dumps(value, sort_keys=True), encoding="ascii")
        ctl._atomic = corrupt_full_intent
        try:
            try:
                _start(ctl, root, "full-intent-corrupt", "print('must-not-run')")
            except Exception as exc:
                assert getattr(exc, "code", None) in {
                    "RELEASE-CONTROLLER-INTENT", "RELEASE-CONTROLLER-WORKER-START",
                }, repr(exc)
            else:
                receipt = _wait(ctl, root, "full-intent-corrupt")
                assert receipt["state"] in {"refused", "evidence_incomplete"}
        finally:
            ctl._atomic = original_atomic
        cases += 1

        # A terminal receipt binds the complete immutable intent, including
        # output allowances that are not projected into its convenience fields.
        _start(ctl, root, "intent-terminal", "print('bound')")
        _wait(ctl, root, "intent-terminal")
        intent_path = root / "runs" / "intent-terminal" / "intent.json"
        intent_value = json.loads(intent_path.read_text(encoding="ascii"))
        intent_value["allowed_output_roots"] = [str(root / "work")]
        intent_path.write_text(json.dumps(intent_value, sort_keys=True), encoding="ascii")
        _expect("EVIDENCE_INCOMPLETE", lambda: ctl.status_run(
            run_root=root / "runs", run_id="intent-terminal",
        ))
        cases += 1

        pid_file = root / "work" / "owned-pids.json"
        tree_code = (
            "import json,os,subprocess,sys,time;"
            "p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']);"
            f"open({str(pid_file)!r},'w').write(json.dumps([os.getpid(),p.pid]));time.sleep(60)"
        )
        unrelated = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(60)"],
                                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            allowed = root / "work"; _start(ctl, root, "cancel", tree_code,
                allowed_output_roots=[allowed], output_watch_roots=[allowed])
            for _ in range(200):
                if pid_file.is_file(): break
                time.sleep(.05)
            owned = json.loads(pid_file.read_text())
            receipt = ctl.cancel_run(run_root=root / "runs", run_id="cancel", timeout_s=30)
            assert receipt["state"] == "cancelled" and unrelated.poll() is None
            for _ in range(100):
                if all(ctl._process_token(pid) is None for pid in owned): break
                time.sleep(.05)
            assert all(ctl._process_token(pid) is None for pid in owned)
        finally:
            unrelated.terminate(); unrelated.wait(timeout=10)
        cases += 1

        bound = root / "bound.txt"; bound.write_text("before")
        _start(ctl, root, "input-drift", "import time;time.sleep(.4)", input_paths=[bound])
        _wait_for_event(root, "input-drift", "child_spawned")
        bound.write_text("after")
        receipt = _wait(ctl, root, "input-drift")
        assert receipt["state"] == "refused" and receipt["diagnostic"]["code"] == "RELEASE-CONTROLLER-INPUT-DRIFT"
        cases += 1

        watched = root / "watched"; allowed = watched / "allowed"; allowed.mkdir(parents=True)
        forbidden = watched / "forbidden.txt"
        _start(ctl, root, "output-scope", f"from pathlib import Path;Path({str(forbidden)!r}).write_text('bad')",
               allowed_output_roots=[allowed], output_watch_roots=[root / "work", watched])
        receipt = _wait(ctl, root, "output-scope")
        assert receipt["state"] == "refused" and receipt["diagnostic"]["code"] == "RELEASE-CONTROLLER-OUTPUT-SCOPE"
        cases += 1


        # Empty-directory changes are output mutations too; inventories must
        # not silently ignore them merely because they contain no files.
        empty_forbidden = watched / "empty-forbidden"
        _start(ctl, root, "output-empty-dir",
               f"from pathlib import Path;Path({str(empty_forbidden)!r}).mkdir()",
               allowed_output_roots=[allowed], output_watch_roots=[root / "work", watched])
        receipt = _wait(ctl, root, "output-empty-dir")
        assert receipt["state"] == "refused"
        assert receipt["diagnostic"]["code"] == "RELEASE-CONTROLLER-OUTPUT-SCOPE"
        cases += 1

        # Directory symlinks/junctions under a watched tree are refused before
        # a child can use them to mutate an unobserved destination.
        reparse_watch = root / "reparse-watch"; reparse_watch.mkdir()
        reparse_target = root / "reparse-target"; reparse_target.mkdir()
        reparse_link = reparse_watch / "escape"
        if os.name == "nt":
            linked = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(reparse_link), str(reparse_target)],
                stdin=subprocess.DEVNULL, capture_output=True, check=False,
            )
            assert linked.returncode == 0, linked.stderr
        else:
            reparse_link.symlink_to(reparse_target, target_is_directory=True)
        escaped = reparse_target / "escaped.txt"
        _expect("RELEASE-CONTROLLER-OUTPUT-TOPOLOGY", lambda: ctl.start_run(
            run_root=root / "runs", run_id="output-reparse",
            argv=[sys.executable, "-c", f"from pathlib import Path;Path({str(escaped)!r}).write_text('bad')"],
            cwd=reparse_watch, allowed_output_roots=[reparse_watch],
            output_watch_roots=[reparse_watch],
        ))
        assert not escaped.exists()
        cases += 1

        # Complete input-root evidence is bound into both intent and receipt
        # and is revalidated before the product child starts.
        input_root = root / "input-root"; input_root.mkdir()
        (input_root / "nested").mkdir(); (input_root / "nested" / "bound.txt").write_text("before")
        input_sentinel = root / "work" / "input-root-child.txt"
        _start(
            ctl, root, "input-root-drift",
            "from pathlib import Path;" + f"Path({str(input_sentinel)!r}).write_text('ran')",
            input_roots=[input_root], allowed_output_roots=[root / "work"],
        )
        (input_root / "nested" / "bound.txt").write_text("after")
        receipt = _wait(ctl, root, "input-root-drift")
        assert receipt["state"] == "refused"
        assert receipt["diagnostic"]["code"] == "RELEASE-CONTROLLER-INPUT-DRIFT-BEFORE-CHILD"
        assert not input_sentinel.exists() and receipt["input_roots"]
        cases += 1

        # An exact ignored output nested inside a complete input root is
        # excluded from both inventories.  Otherwise the output contract says
        # the mutation is ignored while the input contract still refuses it.
        ignored_input_root = root / "ignored-input-root"; ignored_input_root.mkdir()
        ignored_cache = ignored_input_root / "runtime.pyc"; ignored_cache.write_bytes(b"old")
        _start(
            ctl, root, "ignored-input-root-exact",
            f"from pathlib import Path;Path({str(ignored_cache)!r}).write_bytes(b'new')",
            cwd=ignored_input_root, input_roots=[ignored_input_root],
            output_watch_roots=[ignored_input_root], ignored_output_paths=[ignored_cache],
        )
        receipt = _wait(ctl, root, "ignored-input-root-exact")
        assert receipt["state"] == "succeeded"
        cases += 1

        # An exact ignored output file may change, but the ignore cannot mask
        # any sibling file (including another file beneath .git).
        ignored_watch = root / "ignored-watch"; ignored_watch.mkdir()
        git_dir = ignored_watch / ".git"; git_dir.mkdir()
        persistent_lock = git_dir / "coauthor-fixture-runner.lock"; persistent_lock.write_text("old")
        sibling = git_dir / "must-still-bind"; sibling.write_text("old")
        _start(
            ctl, root, "ignored-lock-only",
            f"from pathlib import Path;Path({str(persistent_lock)!r}).write_text('new')",
            cwd=ignored_watch, output_watch_roots=[ignored_watch],
            ignored_output_paths=[persistent_lock],
        )
        receipt = _wait(ctl, root, "ignored-lock-only")
        assert receipt["state"] == "succeeded"
        _start(
            ctl, root, "ignored-lock-sibling",
            f"from pathlib import Path;Path({str(sibling)!r}).write_text('new')",
            cwd=ignored_watch, output_watch_roots=[ignored_watch],
            ignored_output_paths=[persistent_lock],
        )
        receipt = _wait(ctl, root, "ignored-lock-sibling")
        assert receipt["state"] == "refused"
        assert str(sibling.resolve()) in receipt["diagnostic"]["paths"]
        cases += 1

        # Controller-created watch roots are authorized only when they are
        # inside an allowed output root and are reported explicitly.
        created_watch = root / "created-watch"
        _start(
            ctl, root, "created-watch", "print('created')",
            output_watch_roots=[root / "work", created_watch],
            allowed_output_roots=[created_watch],
        )
        receipt = _wait(ctl, root, "created-watch")
        assert receipt["state"] == "succeeded"
        assert receipt["controller_created_output_roots"] == [str(created_watch.resolve())]
        unallowed_watch = root / "unallowed-watch"
        _expect("RELEASE-CONTROLLER-OUTPUT-TOPOLOGY", lambda: ctl.start_run(
            run_root=root / "runs", run_id="unallowed-watch",
            argv=[sys.executable, "-c", "print('no')"], cwd=root / "work",
            output_watch_roots=[root / "work", unallowed_watch],
        ))
        assert not unallowed_watch.exists()
        cases += 1

        # A launcher/spawn failure before owner.json exists must still recover
        # to typed terminal incomplete evidence, never an unrecoverable schema
        # exception or product rerun.
        original_popen = ctl.subprocess.Popen
        def refuse_worker_spawn(*_args, **_kwargs):
            raise OSError("synthetic worker spawn refusal")
        ctl.subprocess.Popen = refuse_worker_spawn
        try:
            try:
                _start(ctl, root, "pre-owner-failure", "print('no')")
            except OSError:
                pass
            else:
                raise AssertionError("worker spawn fault did not surface")
        finally:
            ctl.subprocess.Popen = original_popen
        receipt = ctl.recover_run(run_root=root / "runs", run_id="pre-owner-failure")
        assert receipt["state"] == "evidence_incomplete"
        assert receipt["worker"] is None and receipt["diagnostic"]["code"] == "EVIDENCE_INCOMPLETE"
        # The terminal receipt must remain durable through every public reopen
        # path, including an idempotent restart of the exact same intent.
        assert ctl.status_run(
            run_root=root / "runs", run_id="pre-owner-failure",
        ) == receipt
        assert ctl.wait_run(
            run_root=root / "runs", run_id="pre-owner-failure", timeout_s=1,
        ) == receipt
        reopened = _start(ctl, root, "pre-owner-failure", "print('no')")
        assert reopened["state"] == "evidence_incomplete"
        assert reopened["worker"] is None and reopened["idempotent"] is True
        cases += 1

        # Cross-field validation may never accept a success claim with no exit
        # capsule or captured byte streams.
        _start(ctl, root, "semantic-receipt", "print('semantic')")
        valid = _wait(ctl, root, "semantic-receipt")
        forged = dict(valid)
        forged.update({"state": "succeeded", "exit": None, "exit_capsule": None,
                       "stdout": None, "stderr": None})
        semantic_paths = ctl._paths(root / "runs", "semantic-receipt")
        _expect_one({"EVIDENCE_INCOMPLETE", "RELEASE-CONTROLLER-SCHEMA"},
                    lambda: ctl._validate_terminal(semantic_paths, forged))
        cases += 1

        # An ambient recursion marker cannot bypass the durable release-gate
        # facade.  The controller receipt proves the gate was relaunched.
        gate = ROOT / "scripts" / "release-gate.sh"
        bash = (Path(r"C:\Program Files\Git\bin\bash.exe") if os.name == "nt"
                else Path(shutil.which("bash") or ""))
        assert bash.is_file(), bash
        facade_root = root / "facade-runs"
        facade_env = {
            key: value for key, value in os.environ.items()
            if not key.upper().startswith("PYTHON")
        }
        facade_env.update({
            "COAUTHOR_RELEASE_GATE_CONTROLLED_CHILD": "1",
            "COAUTHOR_RELEASE_CONTROLLER_ROOT": str(facade_root),
            "COAUTHOR_RELEASE_RUN_ID": "ambient-marker",
        })
        facade = subprocess.run(
            [str(bash), str(gate), "--help"], env=facade_env,
            # The facade inventories the complete checkout before its child;
            # allow the same slow-host envelope as the registered suite.
            stdin=subprocess.DEVNULL, capture_output=True, check=False, timeout=120,
        )
        assert facade.returncode == 0, facade.stderr
        assert (facade_root / "ambient-marker" / "receipt.json").is_file()
        cases += 1

        direct_marker = subprocess.run(
            [str(bash), str(gate), "--coauthor-controller-child", "--help"],
            env=facade_env | {"COAUTHOR_RELEASE_RUN_ID": "must-not-exist"},
            stdin=subprocess.DEVNULL, capture_output=True, check=False, timeout=120,
        )
        assert direct_marker.returncode == 2
        assert b"CONTROLLER-CHILD-ATTESTATION" in direct_marker.stderr
        assert not (facade_root / "must-not-exist").exists()
        cases += 1

        missing_spec = root / "relative-missing-topology.json"
        missing = subprocess.run(
            [str(bash), str(gate), "--qualification-spec", missing_spec.name],
            cwd=root, env=facade_env | {"COAUTHOR_RELEASE_RUN_ID": "missing-spec"},
            stdin=subprocess.DEVNULL, capture_output=True, check=False, timeout=120,
        )
        assert missing.returncode == 2
        assert b"RELEASE-CONTROLLER-INPUT" in missing.stdout
        assert b"Authoritative fixture registry" not in missing.stdout
        assert not missing_spec.exists()
        cases += 1

        # The compatibility facade may run the product corpus only after a
        # clean saved-main source preimage, and it must attest source stability
        # again after the corpus.
        gate_text = gate.read_text(encoding="utf-8", errors="strict")
        preflight_marker = 'echo "Source-plane preflight before product corpus"'
        corpus_marker = 'echo "Authoritative fixture registry"'
        assert preflight_marker in gate_text and corpus_marker in gate_text
        assert gate_text.index(preflight_marker) < gate_text.index(corpus_marker)
        assert "snapshot-source" in gate_text and "PLANE-SOURCE-RESIDUE" in gate_text
        cases += 1

        # The product facade must expose the same mandatory five-plane
        # topology that the probes enforce, before any expensive corpus work.
        topology_marker = 'echo "Five-plane qualification topology"'
        post_build_marker = 'echo "Post-build source-plane stability before product suites"'
        assert "--qualification-spec" in gate_text
        assert topology_marker in gate_text
        assert gate_text.index(post_build_marker) < gate_text.index(topology_marker) < gate_text.index(corpus_marker)
        assert "qualification_plane_topology.py" in gate_text
        assert "archive_runtime_probe.py" in gate_text
        assert gate_text.count("runtime_plane_probe.py") >= 2
        assert "--plane-kind unpacked" in gate_text
        assert "--plane-kind installed_cache" in gate_text
        assert "PLANE_TOPOLOGY_PENDING" in gate_text
        assert 'ORIGINAL_ARGS[$((ARG_I + 1))]="$SPEC_INPUT"' in gate_text
        assert 'CONTROLLER_INPUT_ARGS+=(--input "$SPEC_INPUT")' in gate_text
        source_binding = "PLANE-SOURCE-BINDING differs from the controlled plugin root/HEAD"
        archive_binding = "PLANE-ARCHIVE differs from the artifact built in this attempt"
        corpus_guard = "if (( PLANE_QUALIFICATION_OK == 1 )); then"
        assert source_binding in gate_text and archive_binding in gate_text and corpus_guard in gate_text
        assert gate_text.index(source_binding) < gate_text.index(archive_binding) < gate_text.index(corpus_guard) < gate_text.index(corpus_marker)
        cases += 1

    required_contracts = {
        "ambient_environment_refused_before_child",
        "unicode_stdout_stderr_captured_as_bytes",
        "nonzero_exit_journaled",
        "serialization_failure_after_exit_recoverable",
        "crash_after_exit_recovery_without_rerun",
        "lost_exit_status_is_evidence_incomplete",
        "frontend_disconnect_survives",
        "same_intent_idempotent",
        "different_intent_refused",
        "owned_process_tree_cancelled_unrelated_survives",
        "input_drift_refused",
        "output_scope_refused",
        "null_process_token_not_alive",
        "worker_private_environment_not_leaked",
        "launcher_crash_before_owner_survives",
        "intent_digest_tamper_refused_before_child",
        "terminal_intent_binding_tamper_refused",
        "empty_directory_output_scope_refused",
        "output_reparse_topology_refused",
        "terminal_semantics_fail_closed",
        "ambient_release_gate_marker_cannot_bypass",
        "source_preflight_before_product_corpus",
        "full_intent_document_immutable",
        "complete_input_root_refused_before_child",
        "exact_ignored_output_excluded_from_input_root",
        "exact_ignored_output_file_only",
        "controller_created_output_roots_accounted",
        "pre_owner_failure_is_evidence_incomplete",
        "direct_release_gate_child_marker_refused",
        "five_plane_production_facade",
    }
    assert required_contracts <= set(ctl.REGRESSION_CONTRACT)
    assert cases == 31, cases
    print(f"release_qualification_controller_smoketest: PASS ({cases} behavioral cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
