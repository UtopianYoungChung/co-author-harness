#!/usr/bin/env python3
"""Behavioral direct-Python regressions for the durable release controller."""

from __future__ import annotations

import errno
import hashlib
import importlib.util
import inspect
import json
import os
import signal
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
_FIXTURE_OWNER_MODE = False
WINDOWS_GIT_BASH = Path(r"C:\Program Files\Git\bin\bash.exe")


def _bash() -> str:
    """Locate Git Bash on Windows even when PowerShell PATH omits it."""
    if os.name == "nt" and WINDOWS_GIT_BASH.is_file():
        return str(WINDOWS_GIT_BASH)
    bash = shutil.which("bash")
    assert bash, "bash is required to exercise release-gate.sh"
    return bash


def _package_bytecode_inventory() -> tuple[tuple[str, ...], dict[str, tuple[int, str]]]:
    directories = tuple(sorted(
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("__pycache__") if path.is_dir()
    ))
    files = {
        path.relative_to(ROOT).as_posix(): (
            path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        for path in sorted(ROOT.rglob("*.pyc")) if path.is_file()
    }
    return directories, files


def _assert_release_gate_bytecode_argv() -> None:
    gate_text = (ROOT / "scripts" / "release-gate.sh").read_text(
        encoding="utf-8", errors="strict",
    )
    assert 'ATTEST_CONTROLLER="$SCRIPT_DIR/release_qualification_controller.py"' in gate_text
    assert 'cygpath -am "$ATTEST_CONTROLLER"' in gate_text
    assert 'python3 -B "$ATTEST_CONTROLLER" verify-child' in gate_text
    assert 'exec python3 -B "$CONTROLLER_NATIVE" run' in gate_text
    assert "sys.executable" not in gate_text
    verify_at = gate_text.index('python3 -B "$ATTEST_CONTROLLER" verify-child')
    rematerialize_at = gate_text.index('PLUGIN_ROOT="$(cygpath -am "$PLUGIN_ROOT")"')
    walk_at = gate_text.index('NEXT="$( dirname "$PROBE" )"')
    phase01_at = gate_text.index(
        "json.load(open(sys.argv[1], encoding='utf-8'))['name']"
    )
    assert verify_at < rematerialize_at < walk_at < phase01_at, (
        verify_at, rematerialize_at, walk_at, phase01_at,
    )
    assert 'SCRIPT_DIR="$(cygpath' not in gate_text
    assert 'if [[ "$NEXT" == "$PROBE" ]]; then' in gate_text
    rematerialize_if = gate_text.index(
        "if command -v cygpath >/dev/null 2>&1; then\n    PLUGIN_ROOT="
    )
    rematerialize_fi = gate_text.index(
        '\nfi\n\nif [[ ! -f "$VERSION_MANIFEST" ]]', rematerialize_if,
    )
    cygpath_block = gate_text[rematerialize_if:rematerialize_fi]
    assert "dirname" not in cygpath_block
    assert "NEXT=" not in cygpath_block


_WALK_HELPER = r"""
set +e
PROBE="$1"
CAP="$2"
FIXED="$3"
i=0
while [ "$PROBE" != "/" ]; do
  i=$((i + 1))
  if [ "$i" -gt "$CAP" ]; then
    printf 'CAP %s %s\n' "$i" "$PROBE"
    exit 2
  fi
  NEXT=$(dirname "$PROBE")
  if [ "$FIXED" = "1" ] && [ "$NEXT" = "$PROBE" ]; then
    printf 'FIXED %s %s\n' "$i" "$PROBE"
    exit 0
  fi
  PROBE=$NEXT
done
printf 'ROOT %s %s\n' "$i" "$PROBE"
exit 0
"""


def _run_dirname_walk(*, start: str, fixed_point: bool, cap: int = 32) -> subprocess.CompletedProcess:
    bash = _bash()
    return subprocess.run(
        [bash, "-c", _WALK_HELPER, "walk", start, str(cap), "1" if fixed_point else "0"],
        capture_output=True, check=False, timeout=15, text=True, encoding="utf-8", errors="replace"
    )


def _case_legacy_peer_walk_hits_cap() -> None:
    """Old while != / walk never terminates on a Windows drive root."""
    result = _run_dirname_walk(
        start="B:/Agents/platform/co-author-harness", fixed_point=False,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert result.stdout.startswith("CAP "), result.stdout


def _case_fixed_point_walk_terminates() -> None:
    result = _run_dirname_walk(
        start="B:/Agents/platform/co-author-harness", fixed_point=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.startswith("FIXED "), result.stdout
    iterations = int(result.stdout.split()[1])
    assert 1 <= iterations <= 32, result.stdout


def _case_phase01_native_open_and_git() -> None:
    """After rematerialize, native python3 and git -C can see PLUGIN_ROOT."""
    bash = _bash()
    script = r"""
set -euo pipefail
PLUGIN_ROOT="$(cd "$1" && pwd)"
if command -v cygpath >/dev/null 2>&1; then
  PLUGIN_ROOT="$(cygpath -am "$PLUGIN_ROOT")"
fi
VERSION_MANIFEST="$PLUGIN_ROOT/version.json"
python3 - "$VERSION_MANIFEST" <<'PY'
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["name"])
PY
git -C "$PLUGIN_ROOT" rev-parse --is-inside-work-tree
"""
    result = subprocess.run(
        [bash, "-s", str(ROOT)],
        input=script, capture_output=True, check=False, text=True, timeout=30,
        encoding="utf-8", errors="replace",
    )
    assert result.returncode == 0, (result.stdout + result.stderr)[-800:]
    assert "co-author-harness" in result.stdout, result.stdout
    assert "true" in result.stdout, result.stdout
    assert "/b/" not in result.stdout, result.stdout


def _case_verify_child_path_spelling() -> None:
    """Native Windows Python must open the controller; POSIX spelling stays."""
    gate = ROOT / "scripts" / "release-gate.sh"
    env = {
        key: value for key, value in os.environ.items()
        if key.upper() != "PYTHONUTF8"
    }
    env["COAUTHOR_RELEASE_CONTROLLER_ATTESTATION_RUN_DIR"] = str(
        ROOT / "does-not-exist-attestation-run"
    )
    env["COAUTHOR_RELEASE_CONTROLLER_ATTESTATION_TOKEN"] = "0" * 64
    bash = _bash()
    result = subprocess.run(
        [bash, str(gate), "--coauthor-controller-child", "--help"],
        capture_output=True, check=False, env=env, timeout=120,
    )
    combined = result.stdout + result.stderr
    assert result.returncode == 2, combined[-800:]
    assert b"can't open file" not in combined, combined[-800:]
    assert b"B:\\b\\Agents" not in combined and b"B:/b/Agents" not in combined, (
        combined[-800:]
    )
    assert b"CONTROLLER-CHILD-ATTESTATION" in combined, combined[-800:]


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
    if os.name == "nt" and _FIXTURE_OWNER_MODE:
        extra.setdefault("detached", False)
    cwd = extra.pop("cwd", work)
    return ctl.start_run(
        run_root=root / "runs", run_id=run_id,
        argv=[sys.executable, "-c", code], cwd=cwd, **extra,
    )


def _wait(ctl, root: Path, run_id: str):
    return ctl.wait_run(run_root=root / "runs", run_id=run_id, timeout_s=60)


def _execution_mode() -> bool:
    """Return explicit fixture-owner mode; refuse every unknown argument."""
    args = sys.argv[1:]
    if not args:
        return False
    if args == ["--fixture-owner"]:
        return True
    raise SystemExit(f"unsupported controller-smoketest arguments: {args!r}")


def _windows_fixture_owner_contract(ctl, root: Path) -> None:
    """Prove the outer owner and preserve the impossible-detach refusal."""
    if os.name != "nt":
        return
    import _winapi
    import ctypes
    from ctypes import wintypes

    process_handle = int(_winapi.GetCurrentProcess())
    assert ctl._windows_process_in_any_job(process_handle)
    kernel32, ExtendedLimit, _ = ctl._windows_job_api()
    limits = ExtendedLimit()
    returned = wintypes.DWORD()
    ctypes.set_last_error(0)
    assert kernel32.QueryInformationJobObject(
        None, 9, ctypes.byref(limits), ctypes.sizeof(limits), ctypes.byref(returned),
    ), ctypes.WinError(ctypes.get_last_error())
    flags = int(limits.BasicLimitInformation.LimitFlags)
    assert returned.value == ctypes.sizeof(limits), (
        returned.value, ctypes.sizeof(limits),
    )
    assert flags == 0x2000, hex(flags)  # exact KILL_ON_JOB_CLOSE owner contract
    _expect("RELEASE-CONTROLLER-PROCESS", ctl._windows_worker_creation_flag)

    (root / "work").mkdir(exist_ok=True)
    sentinel = root / "work" / "fixture-owner-default-detach.ran"
    spawn_modes: list[bool] = []
    original_spawn = ctl._spawn_worker_process

    def capture_spawn(*args, **kwargs):
        spawn_modes.append(kwargs["detached"])
        return original_spawn(*args, **kwargs)

    ctl._spawn_worker_process = capture_spawn
    try:
        value = ctl.start_run(
            run_root=root / "runs", run_id="fixture-owner-default-detach",
            argv=[
                sys.executable, "-c",
                f"from pathlib import Path;Path({str(sentinel)!r}).write_text('ran')",
            ],
            cwd=root / "work", output_watch_roots=[root / "work"],
        )
    finally:
        ctl._spawn_worker_process = original_spawn
    assert value["state"] == "refused"
    assert spawn_modes == [True]  # no automatic nested-mode retry
    refused = ctl.status_run(
        run_root=root / "runs", run_id="fixture-owner-default-detach",
    )
    assert refused["diagnostic"]["code"] == "RELEASE-CONTROLLER-PROCESS"
    assert refused["worker"] is None and refused["prechild_refusal"] is not None
    assert all(
        refused[key] is None for key in (
            "process", "exit", "exit_capsule", "stdout", "stderr",
        )
    )
    assert "worker_spawned" not in _event_names(root, "fixture-owner-default-detach")
    assert "child_spawned" not in _event_names(root, "fixture-owner-default-detach")
    assert not sentinel.exists()


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


def _wait_for_path(path: Path, timeout_s: float = 10.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if path.is_file():
            return
        time.sleep(.01)
    raise AssertionError(f"timed out waiting for {path}")


def _wait_for_pid_list(path: Path, timeout_s: float = 10.0) -> list[int]:
    """Accept a deliberately partial handoff only after complete JSON appears."""
    deadline = time.monotonic() + timeout_s
    error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            value = json.loads(path.read_text(encoding="ascii", errors="strict"))
            if not isinstance(value, list) or not value or not all(
                isinstance(pid, int) and pid > 0 for pid in value
            ):
                raise ValueError("PID handoff is not a nonempty positive-integer list")
            return value
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            error = exc
            time.sleep(.01)
    raise AssertionError(f"PID handoff did not become readable: {path}: {error}")


def _wait_for_positive_pid(path: Path, timeout_s: float = 10.0) -> int:
    """Read one atomically published canonical positive base-10 ASCII PID."""
    deadline = time.monotonic() + timeout_s
    missing: FileNotFoundError | None = None
    access_denied: OSError | None = None
    first_observation = True
    while first_observation or time.monotonic() < deadline:
        first_observation = False
        try:
            raw = path.read_bytes()
        except FileNotFoundError as exc:
            missing = exc
            access_denied = None
            remaining = deadline - time.monotonic()
            if remaining > 0:
                time.sleep(min(.01, remaining))
            continue
        except OSError as exc:
            if not isinstance(exc, PermissionError) and exc.errno != errno.EACCES:
                raise AssertionError(f"PID handoff read failed: {path}: {exc!r}") from exc
            access_denied = exc
            missing = None
            remaining = deadline - time.monotonic()
            if remaining > 0:
                time.sleep(min(.01, remaining))
            continue
        try:
            value = raw.decode("ascii", errors="strict")
        except UnicodeError as exc:
            raise AssertionError(f"PID handoff is not ASCII: {path}: raw={raw!r}") from exc
        if (
            not value
            or len(value) > 10
            or value[0] == "0"
            or any(character < "0" or character > "9" for character in value)
        ):
            raise AssertionError(
                f"PID handoff is not canonical positive base-10 ASCII: {path}: raw={raw!r}"
            )
        pid = int(value, 10)
        if pid <= 0 or pid > 0xFFFFFFFF or str(pid) != value:
            raise AssertionError(
                f"PID handoff is not canonical positive base-10 ASCII: {path}: raw={raw!r}"
            )
        return pid
    if access_denied is not None:
        raise AssertionError(
            f"PID handoff remained access-denied: {path}: last={access_denied!r}"
        )
    raise AssertionError(f"PID handoff remained absent: {path}: last={missing!r}")


def _identities(ctl, pids: list[int]) -> dict[int, str]:
    rows = {pid: ctl._process_token(pid) for pid in pids}
    assert all(isinstance(token, str) and token for token in rows.values()), rows
    return rows


def _alive_identities(ctl, identities: dict[int, str]) -> list[int]:
    return [pid for pid, token in identities.items() if ctl._process_token(pid) == token]


def _wait_identities_dead(
    ctl, identities: dict[int, str], *, timeout_s: float = 1.0,
) -> list[int]:
    """Wait for Windows Job accounting and exact process signaling to converge."""
    deadline = time.monotonic() + timeout_s
    while True:
        alive = _alive_identities(ctl, identities)
        if not alive or time.monotonic() >= deadline:
            return alive
        time.sleep(.01)


def _terminate_identities(
    ctl, identities: dict[int, str], *, before_terminate=None,
) -> set[tuple[int, str]]:
    """Bounded test-only fallback using an exact process handle, never a PID kill."""
    signalled: set[tuple[int, str]] = set()
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        class FILETIME(ctypes.Structure):
            _fields_ = (("low", wintypes.DWORD), ("high", wintypes.DWORD))

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.GetProcessTimes.argtypes = (
            wintypes.HANDLE, ctypes.POINTER(FILETIME), ctypes.POINTER(FILETIME),
            ctypes.POINTER(FILETIME), ctypes.POINTER(FILETIME),
        )
        kernel32.GetProcessTimes.restype = wintypes.BOOL
        kernel32.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
        kernel32.WaitForSingleObject.restype = wintypes.DWORD
        kernel32.TerminateProcess.argtypes = (wintypes.HANDLE, wintypes.UINT)
        kernel32.TerminateProcess.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel32.CloseHandle.restype = wintypes.BOOL
        retained: list[tuple[int, int]] = []
        try:
            for pid in reversed(list(identities)):
                ctypes.set_last_error(0)
                handle = kernel32.OpenProcess(0x1 | 0x1000 | 0x100000, False, pid)
                if not handle:
                    error = ctypes.get_last_error()
                    if error == 87:  # ERROR_INVALID_PARAMETER: PID does not exist.
                        continue
                    raise AssertionError(f"OpenProcess failed for {pid}: winerror={error}")
                keep_handle = False
                try:
                    wait = kernel32.WaitForSingleObject(handle, 0)
                    if wait == 0:
                        continue
                    assert wait == 258, f"WaitForSingleObject failed for {pid}: {wait}"
                    created, exited, kernel, user = FILETIME(), FILETIME(), FILETIME(), FILETIME()
                    assert kernel32.GetProcessTimes(
                        handle, ctypes.byref(created), ctypes.byref(exited),
                        ctypes.byref(kernel), ctypes.byref(user),
                    ), f"GetProcessTimes failed for {pid}: winerror={ctypes.get_last_error()}"
                    token = str((created.high << 32) | created.low)
                    if token != identities[pid]:
                        continue
                    wait = kernel32.WaitForSingleObject(handle, 0)
                    if wait == 0:
                        continue
                    assert wait == 258, f"post-read WaitForSingleObject failed for {pid}: {wait}"
                    if before_terminate is not None:
                        before_terminate(pid, int(handle))
                    ctypes.set_last_error(0)
                    if not kernel32.TerminateProcess(handle, 1223):
                        error = ctypes.get_last_error()
                        settled = kernel32.WaitForSingleObject(handle, 1000)
                        if settled == 0:
                            continue
                        raise AssertionError(
                            f"TerminateProcess failed for {pid}: winerror={error}; "
                            f"same_handle_wait={settled}"
                        )
                    signalled.add((pid, identities[pid]))
                    retained.append((int(handle), pid))
                    keep_handle = True
                finally:
                    if not keep_handle:
                        assert kernel32.CloseHandle(handle), f"CloseHandle failed for {pid}"
            for handle, pid in retained:
                assert kernel32.WaitForSingleObject(handle, 10000) == 0, (
                    f"exact Windows handle did not become signaled: {pid}"
                )
        finally:
            for handle, pid in retained:
                assert kernel32.CloseHandle(handle), f"CloseHandle failed for {pid}"
        return signalled

    import select

    retained_pidfds: list[tuple[int, int]] = []
    for pid in reversed(list(identities)):
        try:
            descriptor = os.pidfd_open(pid)
        except ProcessLookupError:
            continue
        keep_descriptor = False
        try:
            if ctl._process_token(pid) != identities[pid]:
                continue
            signal.pidfd_send_signal(descriptor, signal.SIGKILL)
            signalled.add((pid, identities[pid]))
            retained_pidfds.append((descriptor, pid))
            keep_descriptor = True
        finally:
            if not keep_descriptor:
                os.close(descriptor)
    try:
        for descriptor, pid in retained_pidfds:
            readable, _, _ = select.select([descriptor], [], [], 10)
            assert readable, f"exact pidfd did not become readable: {pid}"
    finally:
        for descriptor, _pid in retained_pidfds:
            os.close(descriptor)
    return signalled


def _windows_terminate_race_contract(ctl) -> None:
    """Force natural-exit timing on the same exact retained Windows handle."""
    if os.name != "nt":
        return
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.TerminateProcess.argtypes = (wintypes.HANDLE, wintypes.UINT)
    kernel32.TerminateProcess.restype = wintypes.BOOL
    kernel32.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel32.WaitForSingleObject.restype = wintypes.DWORD

    def assert_helper_handle_closed(handle: int) -> None:
        ctypes.set_last_error(0)
        closed_wait = kernel32.WaitForSingleObject(handle, 0)
        closed_error = ctypes.get_last_error()
        assert closed_wait == 0xFFFFFFFF and closed_error == 6, (
            f"exact helper handle was not closed: wait={closed_wait}; winerror={closed_error}"
        )

    process = subprocess.Popen(
        [sys.executable, "-B", "-c", "import time;time.sleep(60)"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )
    token = ctl._process_token(process.pid)
    assert isinstance(token, str) and token
    observed_handle: list[int] = []

    def exit_on_exact_handle(pid: int, handle: int) -> None:
        assert pid == process.pid
        observed_handle.append(handle)
        assert kernel32.TerminateProcess(handle, 1224), (
            f"race fixture could not terminate exact handle: winerror={ctypes.get_last_error()}"
        )
        assert kernel32.WaitForSingleObject(handle, 10000) == 0, (
            "race fixture exact handle did not signal"
        )

    try:
        signalled = _terminate_identities(
            ctl, {process.pid: token}, before_terminate=exit_on_exact_handle,
        )
        assert signalled == set(), signalled
        assert len(observed_handle) == 1, observed_handle
        assert process.wait(timeout=10) == 1224
        assert_helper_handle_closed(observed_handle[0])
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)

    forced = subprocess.Popen(
        [sys.executable, "-B", "-c", "import time;time.sleep(60)"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )
    forced_token = ctl._process_token(forced.pid)
    assert isinstance(forced_token, str) and forced_token
    try:
        forced_signalled = _terminate_identities(ctl, {forced.pid: forced_token})
        assert forced_signalled == {(forced.pid, forced_token)}, forced_signalled
        assert forced.wait(timeout=10) == 1223
    finally:
        if forced.poll() is None:
            forced.kill()
            forced.wait(timeout=10)

    partial_success = subprocess.Popen(
        [sys.executable, "-B", "-c", "import time;time.sleep(60)"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )
    partial_failure = subprocess.Popen(
        [sys.executable, "-B", "-c", "import time;time.sleep(60)"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )
    partial_success_token = ctl._process_token(partial_success.pid)
    partial_failure_token = ctl._process_token(partial_failure.pid)
    assert isinstance(partial_success_token, str) and partial_success_token
    assert isinstance(partial_failure_token, str) and partial_failure_token
    partial_handles: dict[int, int] = {}

    def fail_second_identity(pid: int, handle: int) -> None:
        partial_handles[pid] = handle
        if pid == partial_failure.pid:
            raise RuntimeError("forced-partial-identity-failure")

    try:
        try:
            _terminate_identities(
                ctl,
                {
                    partial_failure.pid: partial_failure_token,
                    partial_success.pid: partial_success_token,
                },
                before_terminate=fail_second_identity,
            )
        except RuntimeError as exc:
            assert str(exc) == "forced-partial-identity-failure", repr(exc)
        else:
            raise AssertionError("partial multi-identity failure was suppressed")
        assert partial_success.wait(timeout=10) == 1223
        assert partial_failure.poll() is None
        assert set(partial_handles) == {partial_success.pid, partial_failure.pid}, partial_handles
        assert_helper_handle_closed(partial_handles[partial_success.pid])
        assert_helper_handle_closed(partial_handles[partial_failure.pid])
    finally:
        for partial in (partial_success, partial_failure):
            if partial.poll() is None:
                partial.kill()
                partial.wait(timeout=10)


def _reap_frontends(processes: list[subprocess.Popen[bytes]]) -> None:
    for process in processes:
        try:
            process.communicate(timeout=10)
        except subprocess.TimeoutExpired as exc:
            raise AssertionError(
                f"frontend {getattr(process, 'pid', 'unknown')} was not reaped"
            ) from exc


def _capture_identity(ctl, identities: dict[int, str], pid: object) -> None:
    if not isinstance(pid, int) or pid <= 0:
        raise AssertionError(f"invalid frontend PID for identity capture: {pid!r}")
    token = ctl._process_token(pid)
    if not isinstance(token, str) or not token or token == "unavailable":
        raise AssertionError(f"frontend creation token is unavailable: {pid}")
    identities.setdefault(pid, token)


def _windows_observation_contract(ctl) -> tuple[int, list[str]]:
    def windows_error(code: int, message: str) -> OSError:
        error = OSError(message)
        error.winerror = code
        return error

    rows = [
        {"name": "signaled-dead", "waits": ["signaled"], "expected": None},
        {"name": "absent-pid-dead", "open_error": windows_error(87, "absent"), "expected": None},
        {"name": "access-refused", "open_error": windows_error(5, "access"), "expected": "refusal"},
        {"name": "wait-api-refused", "waits": [windows_error(6, "wait")], "expected": "refusal"},
        {"name": "times-refused", "waits": ["timeout"], "read_error": windows_error(6, "times"), "expected": "refusal"},
        {"name": "timeout-read-signaled-dead", "waits": ["timeout", "signaled"], "token": "creation-1", "expected": None},
        {"name": "timeout-read-timeout-live", "waits": ["timeout", "timeout"], "token": "creation-2", "expected": "creation-2"},
        {"name": "close-refused", "waits": ["signaled"], "close_error": windows_error(6, "close"), "expected": "refusal"},
    ]

    class FakeWindowsApi:
        def __init__(self, row):
            self.row = row
            self.waits = list(row.get("waits", []))
            self.opened = self.closed = 0

        def open_process(self, _pid):
            error = self.row.get("open_error")
            if error is not None:
                raise error
            self.opened += 1
            return object()

        def wait(self, _handle):
            value = self.waits.pop(0)
            if isinstance(value, Exception):
                raise value
            return value

        def creation_token(self, _handle):
            error = self.row.get("read_error")
            if error is not None:
                raise error
            return self.row.get("token", "unused-token")

        def close(self, _handle):
            self.closed += 1
            error = self.row.get("close_error")
            if error is not None:
                raise error

    observer = getattr(ctl, "_observe_windows_process", None)
    failures: list[str] = []
    if callable(observer):
        for row in rows:
            api = FakeWindowsApi(row)
            try:
                value = observer(4242, api=api)
            except Exception as exc:
                value = "refusal" if isinstance(exc, ctl.ControllerRefusal) else f"raw:{exc!r}"
            if value != row["expected"]:
                failures.append(
                    f"{row['name']} expected {row['expected']!r}, got {value!r}"
                )
            if api.opened and api.closed != 1:
                failures.append(
                    f"{row['name']} closed {api.closed} times after {api.opened} open"
                )
    else:
        failures.append("injectable observer API is absent")
    return len(rows), failures


def _run_lock_contract(ctl, root: Path) -> None:
    class FakeStream:
        def __init__(self):
            self.closed = False

        @staticmethod
        def fileno():
            return 12345

        @staticmethod
        def seek(*_args):
            return 0

        def close(self):
            self.closed = True

    if os.name == "nt":
        import msvcrt as lock_module
        primitive_name = "locking"
    else:
        import fcntl as lock_module
        primitive_name = "flock"
    original = getattr(lock_module, primitive_name)
    failure = lambda *_args: (_ for _ in ()).throw(OSError("synthetic non-contention"))

    stream = FakeStream()
    lock = ctl._RunLock(root / "synthetic-release.lock")
    lock.stream = stream
    ctl._ATOMIC_LOCK.acquire()
    setattr(lock_module, primitive_name, failure)
    try:
        try:
            lock.__exit__(None, None, None)
        except Exception as exc:
            assert isinstance(exc, ctl.ControllerRefusal)
            assert exc.code == "RELEASE-CONTROLLER-IO"
        else:
            raise AssertionError("synthetic unlock failure was suppressed")
    finally:
        setattr(lock_module, primitive_name, original)

    def second_thread_can_acquire() -> bool:
        result: list[bool] = []

        def probe() -> None:
            acquired = ctl._ATOMIC_LOCK.acquire(timeout=.2)
            result.append(acquired)
            if acquired:
                ctl._ATOMIC_LOCK.release()

        thread = threading.Thread(target=probe)
        thread.start()
        thread.join(timeout=2)
        assert not thread.is_alive()
        return result == [True]

    class FakeParent:
        @staticmethod
        def mkdir(**_kwargs):
            return None

    class CompoundStream(FakeStream):
        def __init__(self):
            super().__init__()
            self.close_count = 0

        @staticmethod
        def seek(*_args):
            return 1

        def close(self):
            self.close_count += 1
            raise OSError("cleanup-close")

    class FakePath:
        parent = FakeParent()

        def __init__(self, fake_stream, *, open_error: Exception | None = None):
            self.fake_stream, self.open_error = fake_stream, open_error

        def open(self, _mode):
            if self.open_error is not None:
                raise self.open_error
            return self.fake_stream

    compound_stream = CompoundStream()
    compound = ctl._RunLock(FakePath(compound_stream), timeout_s=0)
    setattr(lock_module, primitive_name, failure)
    try:
        try:
            compound.__enter__()
        except Exception as exc:
            assert isinstance(exc, ctl.ControllerRefusal)
            assert exc.code == "RELEASE-CONTROLLER-IO"
            assert "synthetic non-contention" in str(exc) and "cleanup-close" in str(exc)
        else:
            raise AssertionError("compound lock failure was suppressed")
    finally:
        setattr(lock_module, primitive_name, original)
    assert compound.stream is None and compound_stream.close_count == 1
    assert second_thread_can_acquire()

    for stage in ("mkdir", "open", "write", "flush", "fsync"):
        class InitParent:
            def mkdir(self, **_kwargs):
                if stage == "mkdir":
                    raise OSError("mkdir-init")

        class InitStream(FakeStream):
            def __init__(self):
                super().__init__()
                self.close_count = 0

            def write(self, _raw):
                if stage == "write":
                    raise OSError("write-init")
                return 1

            def flush(self):
                if stage == "flush":
                    raise OSError("flush-init")

            def close(self):
                self.close_count += 1
                self.closed = True

        class InitPath(FakePath):
            parent = InitParent()

        init_stream = InitStream()
        init_path = InitPath(
            init_stream,
            open_error=OSError("open-init") if stage == "open" else None,
        )
        init_lock = ctl._RunLock(init_path, timeout_s=0)
        original_fsync = ctl.os.fsync
        if stage == "fsync":
            ctl.os.fsync = lambda _fd: (_ for _ in ()).throw(OSError("fsync-init"))
        try:
            try:
                init_lock.__enter__()
            except Exception as exc:
                assert isinstance(exc, ctl.ControllerRefusal)
                assert exc.code == "RELEASE-CONTROLLER-IO" and f"{stage}-init" in str(exc)
            else:
                raise AssertionError(f"{stage} initialization failure was suppressed")
        finally:
            ctl.os.fsync = original_fsync
        assert init_lock.stream is None
        assert init_stream.close_count == (0 if stage in {"mkdir", "open"} else 1)
        assert second_thread_can_acquire()
    assert stream.closed and lock.stream is None

    acquire = ctl._RunLock(root / "synthetic-acquire.lock", timeout_s=0)
    setattr(lock_module, primitive_name, failure)
    try:
        try:
            acquire.__enter__()
        except Exception as exc:
            assert isinstance(exc, ctl.ControllerRefusal)
            assert exc.code == "RELEASE-CONTROLLER-IO"
        else:
            raise AssertionError("synthetic non-contention lock error was retried")
    finally:
        setattr(lock_module, primitive_name, original)


def _capture_run_identities(
    ctl, root: Path, run_id: str, identities: dict[int, str], *, run_root: Path | None = None,
) -> None:
    run_dir = (run_root if run_root is not None else root / "runs") / run_id
    try:
        owner = json.loads((run_dir / "owner.json").read_text(encoding="ascii"))
        owner_pid, owner_token = owner.get("pid"), owner.get("process_token")
        if (
            not isinstance(owner_pid, int) or owner_pid <= 0
            or not isinstance(owner_token, str) or not owner_token
            or owner_token == "unavailable"
        ):
            raise AssertionError("recorded owner identity is unavailable")
        identities.setdefault(owner_pid, owner_token)
    except (OSError, UnicodeError, json.JSONDecodeError):
        pass
    try:
        journal = json.loads((run_dir / "journal.json").read_text(encoding="ascii"))
        for row in journal.get("events", []):
            if row.get("event") == "child_spawned":
                child_pid, child_token = row.get("child_pid"), row.get("process_token")
                if (
                    not isinstance(child_pid, int) or child_pid <= 0
                    or not isinstance(child_token, str) or not child_token
                    or child_token == "unavailable"
                ):
                    raise AssertionError("recorded child identity is unavailable")
                identities.setdefault(child_pid, child_token)
    except (OSError, UnicodeError, json.JSONDecodeError):
        pass


def _cancel_finally(
    ctl, root: Path, run_id: str, *, run_root: Path | None = None,
) -> None:
    try:
        ctl.cancel_run(
            run_root=run_root if run_root is not None else root / "runs",
            run_id=run_id, timeout_s=30,
        )
    except Exception:
        # The exact-token fallback owned by each regression is responsible for
        # preserving cleanup if the controller itself is the behavior at fault.
        pass


def _reopened_red_against_committed() -> int:
    """Prove the reopened defects against the frozen 7712e60 controller."""
    expected_commit = "7712e600aef5ba6974e65f296ef1d9b85b7a3e6b"
    observed_commit = subprocess.run(
        ["git", "rev-parse", "7712e60^{commit}"], cwd=ROOT,
        stdin=subprocess.DEVNULL, capture_output=True, check=True, text=True,
        encoding="utf-8", errors="strict",
    ).stdout.strip()
    assert observed_commit == expected_commit, (observed_commit, expected_commit)

    frozen_files = {
        "scripts/release_qualification_controller.py": "63aebb54460b248094773336d4798f4ac39d80337d739cf57d450a7d9635234c",
        "scripts/destination_capability.py": "35b8ec81ac0fd06a4e8d1808c78126e7123f92c52de53fa2ee9b02e7e07c4a11",
        "scripts/qualification_environment.py": "a9f20c3c9e41536b73a7687d69250dfbc74ef12142831a77c59aab7d19d4346d",
        "references/schemas/release_qualification_controller.schema.json": "71a1a0a213cd832aec529852658f20d809ffbb2937ad780833b607166f7c9b14",
    }
    failures: list[str] = []
    platform_skips = 0
    with tempfile.TemporaryDirectory(prefix="release-controller-reopened-red-") as raw:
        isolated_root = Path(raw) / "committed-root"
        for relative, expected_sha256 in frozen_files.items():
            raw_file = subprocess.run(
                ["git", "show", f"{expected_commit}:{relative}"], cwd=ROOT,
                stdin=subprocess.DEVNULL, capture_output=True, check=True,
            ).stdout
            observed_sha256 = hashlib.sha256(raw_file).hexdigest()
            assert observed_sha256 == expected_sha256, (relative, observed_sha256, expected_sha256)
            destination = isolated_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw_file)

        scripts = isolated_root / "scripts"
        committed_path = scripts / "release_qualification_controller.py"

        sys.path.insert(0, str(scripts))
        try:
            ctl = _load(committed_path, "release_qualification_controller_reopened_red")
        finally:
            sys.path.remove(str(scripts))
        assert Path(sys.modules["destination_capability"].__file__).resolve() == (
            scripts / "destination_capability.py"
        ).resolve()
        assert Path(sys.modules["qualification_environment"].__file__).resolve() == (
            scripts / "qualification_environment.py"
        ).resolve()

        def require(case: str, condition: bool, detail: str) -> None:
            if not condition:
                failures.append(f"{case}: {detail}")

        if os.name != "nt":
            require(
                "POSIX-STAT-IDENTITY-ROBUST",
                callable(getattr(ctl, "_parse_proc_stat", None)),
                "final-paren /proc stat parser and zombie/dead rejection are absent",
            )
            terminate_parameters = inspect.signature(ctl._terminate_owned).parameters
            require(
                "POSIX-REUSED-SESSION-REFUSED",
                "leader_token" in terminate_parameters,
                "termination accepts no recorded creation token and can signal a reused PID/PGID",
            )
            worker_source = inspect.getsource(ctl._worker)
            require(
                "POSIX-PREJOURNAL-GATE-FAIL-CLOSED",
                callable(getattr(ctl, "_spawn_product_process", None))
                and "crash_after_supervisor_spawn_before_journal" in worker_source,
                "no recorded wrapper/pipe gate prevents product execution before child_spawned durability",
            )
            start_source = inspect.getsource(ctl.start_run)
            invalid_binding = start_source.find("worker self-ownership binding is invalid")
            require(
                "POSIX-READINESS-REFUSAL-TREE-CLEANED",
                invalid_binding >= 0 and "_terminate_owned(worker" in start_source[invalid_binding:],
                "parent readiness refusal raises without terminating the already spawned worker/product tree",
            )
            require(
                "POSIX-POST-KILL-SESSION-QUIESCENT",
                callable(getattr(ctl, "_session_members", None))
                and callable(getattr(ctl, "_terminate_posix_session", None)),
                "SIGKILL path neither enumerates the recorded session nor proves descendant quiescence",
            )
        else:
            platform_skips += 5
        require(
            "MULTIPROCESS-CANCEL-IDEMPOTENT",
            "_RunLock" in inspect.getsource(ctl.cancel_run),
            "cancel publication/finalization has no interprocess run lock",
        )
        require(
            "MULTIPROCESS-RECOVERY-SERIALIZED",
            "_RunLock" in inspect.getsource(ctl.recover_run),
            "recovery journal/receipt finalization has no interprocess run lock",
        )

    expected_failures = 7 if os.name != "nt" else 2
    assert len(failures) == expected_failures, failures
    print(f"reopened-red target: {expected_commit}")
    print(f"frozen inputs: {len(frozen_files)} exact-commit files SHA-256 bound")
    print(f"platform: os.name={os.name}; posix_evidence={'executed' if os.name != 'nt' else 'not-run'}; platform_skips={platform_skips}")
    for failure in failures:
        print(f"RED {failure}")
    print("cleanup: disposable committed mini-root removed; no product process was spawned")
    raise AssertionError("expected reopened red regressions:\n- " + "\n- ".join(failures))


def _third_reopened_red() -> int:
    """Prove third-review defects against the self-contained baseline commit."""
    expected_commit = "7d36c734b470748ee0b292b8bdaeca72e90d5d83"
    frozen_files = {
        "scripts/release_qualification_controller_smoketest.py": "07f3c1b2ebd3e669966ba03c5e6052b4334bf051864d5863fd13cfe1856a716c",
        "scripts/release_qualification_controller.py": "63aebb54460b248094773336d4798f4ac39d80337d739cf57d450a7d9635234c",
        "scripts/destination_capability.py": "35b8ec81ac0fd06a4e8d1808c78126e7123f92c52de53fa2ee9b02e7e07c4a11",
        "scripts/qualification_environment.py": "a9f20c3c9e41536b73a7687d69250dfbc74ef12142831a77c59aab7d19d4346d",
        "references/schemas/release_qualification_controller.schema.json": "71a1a0a213cd832aec529852658f20d809ffbb2937ad780833b607166f7c9b14",
    }
    observed_commit = subprocess.run(
        ["git", "rev-parse", f"{expected_commit}^{{commit}}"], cwd=ROOT,
        stdin=subprocess.DEVNULL, capture_output=True, check=True, text=True,
        encoding="utf-8", errors="strict",
    ).stdout.strip()
    assert observed_commit == expected_commit, (observed_commit, expected_commit)
    failures: list[str] = []
    cases = 0
    platform_skips = 0

    def require(case: str, condition: bool, detail: str) -> None:
        nonlocal cases
        cases += 1
        if not condition:
            failures.append(f"{case}: {detail}")

    with tempfile.TemporaryDirectory(prefix="release-controller-third-red-") as raw:
        isolated_root = Path(raw) / "committed-root"
        for relative, expected_sha256 in frozen_files.items():
            raw_file = subprocess.run(
                ["git", "show", f"{expected_commit}:{relative}"], cwd=ROOT,
                stdin=subprocess.DEVNULL, capture_output=True, check=True,
            ).stdout
            observed_sha256 = hashlib.sha256(raw_file).hexdigest()
            assert observed_sha256 == expected_sha256, (relative, observed_sha256, expected_sha256)
            destination = isolated_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw_file)
        scripts = isolated_root / "scripts"
        sys.path.insert(0, str(scripts))
        try:
            ctl = _load(
                scripts / "release_qualification_controller.py",
                "release_qualification_controller_third_red",
            )
            baseline_smoke = _load(
                scripts / "release_qualification_controller_smoketest.py",
                "release_qualification_controller_smoketest_third_red",
            )
        finally:
            sys.path.remove(str(scripts))
        assert Path(sys.modules["destination_capability"].__file__).resolve() == (
            scripts / "destination_capability.py"
        ).resolve()
        assert Path(sys.modules["qualification_environment"].__file__).resolve() == (
            scripts / "qualification_environment.py"
        ).resolve()
        root = isolated_root / "smoke"
        root.mkdir(parents=True)
        cleanup_probe = "pidfd exercised by setsid regression"
        if os.name == "nt":
            probe = subprocess.Popen(
                [sys.executable, "-c", "import time;time.sleep(60)"],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            probe_token = ctl._process_token(probe.pid)
            assert isinstance(probe_token, str) and probe_token
            try:
                _terminate_identities(ctl, {probe.pid: probe_token})
                assert probe.wait(timeout=1) is not None
            finally:
                if probe.poll() is None:
                    # Popen retains the exact process handle; this never targets
                    # a later process by its reused numeric PID.
                    probe.kill()
                    probe.wait(timeout=10)
            cleanup_probe = "exact Windows process handle exercised"

        if os.name != "nt":
            # A descendant that calls setsid remains an owned/reparented child
            # of the subreaper and must not outlive terminal evidence.
            escape_pids = root / "work" / "escaped-session-pids.json"
            escape_identities: dict[int, str] = {}
            receipt = None
            alive_at_terminal: list[int] = []
            escaped_child = (
                "import json,os,time;from pathlib import Path;"
                f"p=Path({str(escape_pids)!r});t=p.with_name('.'+p.name+'.tmp');"
                "t.write_text(json.dumps([os.getpid()]),encoding='ascii');os.replace(t,p);"
                "time.sleep(60)"
            )
            product = (
                "import subprocess,sys;"
                f"subprocess.Popen([sys.executable,'-c',{escaped_child!r}],start_new_session=True)"
            )
            try:
                _start(
                    ctl, root, "setsid-escape", product,
                    allowed_output_roots=[root / "work"],
                )
                escape_identities = _identities(ctl, _wait_for_pid_list(escape_pids))
                receipt_path = root / "runs" / "setsid-escape" / "receipt.json"
                _wait_for_path(receipt_path, timeout_s=20)
                receipt = json.loads(receipt_path.read_text(encoding="ascii"))
                alive_at_terminal = _alive_identities(ctl, escape_identities)
            finally:
                if escape_pids.is_file() and not escape_identities:
                    try:
                        escape_identities = _identities(
                            ctl, _wait_for_pid_list(escape_pids, timeout_s=1),
                        )
                    except AssertionError:
                        pass
                _cancel_finally(ctl, root, "setsid-escape")
                _terminate_identities(ctl, escape_identities)
            require(
                "POSIX-SETSID-DESCENDANT-OWNED",
                receipt is not None and not alive_at_terminal,
                f"terminal receipt was published while escaped owned identities remained: {alive_at_terminal}",
            )

            # Membership and creation identity must derive from one /proc stat
            # observation.  A second read may already describe a reused PID.
            members: dict[int, str] = {}
            signalled: list[int] = []

            class FakeStat:
                def read_text(self, **_kwargs):
                    return "4242 (old member) S 1 17 17 " + " ".join(map(str, range(4, 20)))

            class FakeEntry:
                name = "4242"

                def __truediv__(self, _name):
                    return FakeStat()

            class FakeProc:
                def iterdir(self):
                    return [FakeEntry()]

            membership_api = all(
                callable(getattr(ctl, name, None))
                for name in ("_session_members", "_signal_session")
            )
            if membership_api:
                original_path = ctl.Path
                original_token = ctl._process_token
                original_kill = ctl.os.kill
                ctl.Path = lambda raw_path: (
                    FakeProc() if os.fspath(raw_path) == "/proc" else original_path(raw_path)
                )
                ctl._process_token = lambda _pid: "new-process-token"
                ctl.os.kill = lambda pid, _signal: signalled.append(pid)
                try:
                    members = ctl._session_members(17)
                    ctl._signal_session(17, members, signal.SIGTERM)
                finally:
                    ctl.Path = original_path
                    ctl._process_token = original_token
                    ctl.os.kill = original_kill
            require(
                "POSIX-SESSION-MEMBERSHIP-SINGLE-OBSERVATION",
                membership_api and not members and not signalled,
                "single-observation membership API is absent"
                if not membership_api else (
                    f"a reused PID was admitted and signalled: members={members}, signalled={signalled}"
                ),
            )
        else:
            platform_skips += 2

        # Missing creation tokens and a second reap timeout must be explicit
        # failures; cleanup may never silently omit an owned frontend.
        class NoTokenController:
            @staticmethod
            def _process_token(_pid):
                return None

        class NeverReaped:
            pid = 919191

            @staticmethod
            def communicate(timeout):
                raise subprocess.TimeoutExpired(["synthetic-frontend"], timeout)

        capture_error = reap_error = None
        try:
            baseline_smoke._capture_identity(NoTokenController(), {}, NeverReaped.pid)
        except Exception as exc:
            capture_error = exc
        try:
            baseline_smoke._reap_frontends([NeverReaped()])
        except Exception as exc:
            reap_error = exc
        require(
            "SMOKE-FRONTEND-UNAVAILABLE-TOKEN-EXPLICIT",
            capture_error is not None,
            "token-unavailable capture was silently omitted",
        )
        require(
            "SMOKE-FRONTEND-SECOND-REAP-TIMEOUT-EXPLICIT",
            reap_error is not None,
            "second reap timeout was silently suppressed",
        )

        # Unlock errors must be typed, but the stream must always be closed and
        # cleared even when the platform unlock primitive fails.
        class FakeStream:
            def __init__(self):
                self.closed = False

            @staticmethod
            def fileno():
                return 12345

            @staticmethod
            def seek(*_args):
                return 0

            def close(self):
                self.closed = True

        stream = FakeStream()
        unlock_error = None
        lock = None
        lock_api = hasattr(ctl, "_RunLock") and hasattr(ctl, "_ATOMIC_LOCK")
        if lock_api:
            lock = ctl._RunLock(root / "synthetic-release.lock")
            lock.stream = stream
            ctl._ATOMIC_LOCK.acquire()
            if os.name == "nt":
                import msvcrt as lock_module
                primitive_name = "locking"
            else:
                import fcntl as lock_module
                primitive_name = "flock"
            original_unlock = getattr(lock_module, primitive_name)
            setattr(
                lock_module, primitive_name,
                lambda *_args: (_ for _ in ()).throw(OSError("synthetic unlock")),
            )
            try:
                lock.__exit__(None, None, None)
            except Exception as exc:
                unlock_error = exc
            finally:
                setattr(lock_module, primitive_name, original_unlock)
        require(
            "RUNLOCK-UNLOCK-FAILURE-CLOSES-AND-TYPES",
            lock_api and stream.closed and lock.stream is None
            and isinstance(unlock_error, ctl.ControllerRefusal),
            "run-lock API is absent" if not lock_api else (
                f"unlock failure retained the stream or surfaced untyped: {unlock_error!r}"
            ),
        )

        # Acquisition must retry only recognized contention.  Synthetic
        # non-contention OS errors require an immediate typed lock refusal.
        acquire_error = None
        if lock_api:
            acquire_lock = ctl._RunLock(root / "synthetic-acquire.lock", timeout_s=0)
            original_acquire = getattr(lock_module, primitive_name)
            setattr(
                lock_module, primitive_name,
                lambda *_args: (_ for _ in ()).throw(OSError("synthetic non-contention")),
            )
            try:
                acquire_lock.__enter__()
            except Exception as exc:
                acquire_error = exc
            finally:
                setattr(lock_module, primitive_name, original_acquire)
        require(
            "RUNLOCK-NONCONTENTION-ERROR-TYPED",
            lock_api and isinstance(acquire_error, ctl.ControllerRefusal)
            and getattr(acquire_error, "code", None) != "RELEASE-CONTROLLER-LIVE",
            "run-lock API is absent" if not lock_api else (
                f"non-contention acquisition error was raw or misclassified: {acquire_error!r}"
            ),
        )

        # Pure/injectable Windows observation table: only confirmed absence or
        # a signaled handle means dead; all observation errors are typed.
        observation_rows, observation_failures = _windows_observation_contract(ctl)
        require(
            "WINDOWS-PROCESS-OBSERVATION-TYPED",
            not observation_failures,
            "; ".join(observation_failures),
        )

        # Preserve red evidence for the committed unsafe cleanup while the
        # active smoke helper is guarded by exact handles/pidfds.
        committed_smoke = subprocess.run(
            ["git", "show", "3a1602625bea5c34a05aaa3f1eb1c4b8d10b6bc0:scripts/release_qualification_controller_smoketest.py"],
            cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True, check=True,
        ).stdout.decode("utf-8", errors="strict")
        committed_cleanup = committed_smoke.split("def _terminate_identities", 1)[1].split("\ndef ", 1)[0]
        active_cleanup = inspect.getsource(_terminate_identities)
        assert "taskkill" not in active_cleanup and "TerminateProcess" in active_cleanup
        require(
            "SMOKE-WINDOWS-CLEANUP-EXACT-HANDLE",
            "taskkill" not in committed_cleanup,
            "committed cleanup performs token-check then bare taskkill /PID",
        )

    expected_failures = 8 if os.name != "nt" else 6
    assert cases == expected_failures, (cases, expected_failures)
    assert len(failures) == expected_failures, failures
    print(f"third-red commit={expected_commit}")
    print(
        "frozen inputs: " + ", ".join(
            f"{relative}={digest}" for relative, digest in frozen_files.items()
        )
    )
    print(f"windows_observation_table_rows={observation_rows}")
    print(f"cleanup_probe={cleanup_probe}")
    print(
        f"platform: os.name={os.name}; behavioral_cases={cases}; "
        f"platform_skips={platform_skips}; posix_evidence={'executed' if os.name != 'nt' else 'not-run'}"
    )
    for failure in failures:
        print(f"RED {failure}")
    print("cleanup: exact handles/pidfds quiescent; disposable third-red root removed")
    raise AssertionError("expected third-review red regressions:\n- " + "\n- ".join(failures))


def _fourth_reopened_red() -> int:
    """Prove fourth-review defects against immutable committed source planes."""
    baseline_commit = "7d36c734b470748ee0b292b8bdaeca72e90d5d83"
    candidate_commit = "8aaa13beb5ff08944f6a9ce30b8a02b8b9128db8"
    baseline_files = {
        "scripts/release_qualification_controller.py": "63aebb54460b248094773336d4798f4ac39d80337d739cf57d450a7d9635234c",
        "scripts/destination_capability.py": "35b8ec81ac0fd06a4e8d1808c78126e7123f92c52de53fa2ee9b02e7e07c4a11",
        "scripts/qualification_environment.py": "a9f20c3c9e41536b73a7687d69250dfbc74ef12142831a77c59aab7d19d4346d",
        "references/schemas/release_qualification_controller.schema.json": "71a1a0a213cd832aec529852658f20d809ffbb2937ad780833b607166f7c9b14",
    }
    candidate_files = {
        **baseline_files,
        "scripts/release_qualification_controller.py": "54a6b03ecaad4ee0bb2b83e27faf6bec55781ca06f9daf0c36d6dabf855eba00",
    }
    for expected_commit in (baseline_commit, candidate_commit):
        observed_commit = subprocess.run(
            ["git", "rev-parse", f"{expected_commit}^{{commit}}"], cwd=ROOT,
            stdin=subprocess.DEVNULL, capture_output=True, check=True, text=True,
            encoding="utf-8", errors="strict",
        ).stdout.strip()
        assert observed_commit == expected_commit, (observed_commit, expected_commit)
    failures: list[str] = []
    cases = 0
    platform_skips = 0

    def require(case: str, condition: bool, detail: str) -> None:
        nonlocal cases
        cases += 1
        if not condition:
            failures.append(f"{case}: {detail}")

    def load_isolated(root: Path, name: str):
        scripts = root / "scripts"
        saved = {
            module_name: sys.modules.pop(module_name, None)
            for module_name in ("destination_capability", "qualification_environment")
        }
        sys.path.insert(0, str(scripts))
        try:
            return _load(scripts / "release_qualification_controller.py", name)
        finally:
            sys.path.remove(str(scripts))
            for module_name in saved:
                sys.modules.pop(module_name, None)
            for module_name, module in saved.items():
                if module is not None:
                    sys.modules[module_name] = module

    def second_thread_can_acquire(lock) -> bool:
        result: list[bool] = []

        def probe() -> None:
            acquired = lock.acquire(timeout=.2)
            result.append(acquired)
            if acquired:
                lock.release()

        thread = threading.Thread(target=probe)
        thread.start()
        thread.join(timeout=2)
        assert not thread.is_alive()
        return result == [True]

    def exception_text(exc: Exception | None) -> str:
        rows: list[str] = []
        seen: set[int] = set()
        while exc is not None and id(exc) not in seen:
            seen.add(id(exc))
            rows.append(f"{type(exc).__name__}: {exc}")
            exc = exc.__cause__ if exc.__cause__ is not None else exc.__context__
        return " | ".join(rows)

    with tempfile.TemporaryDirectory(prefix="release-controller-fourth-red-") as raw:
        transaction_root = Path(raw)
        baseline_root = transaction_root / "committed-root"
        candidate_root = transaction_root / "candidate-commit-root"
        for relative, expected_sha256 in baseline_files.items():
            content = subprocess.run(
                ["git", "show", f"{baseline_commit}:{relative}"], cwd=ROOT,
                stdin=subprocess.DEVNULL, capture_output=True, check=True,
            ).stdout
            assert hashlib.sha256(content).hexdigest() == expected_sha256
            destination = baseline_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
        for relative, expected_sha256 in candidate_files.items():
            content = subprocess.run(
                ["git", "show", f"{candidate_commit}:{relative}"], cwd=ROOT,
                stdin=subprocess.DEVNULL, capture_output=True, check=True,
            ).stdout
            assert hashlib.sha256(content).hexdigest() == expected_sha256
            destination = candidate_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
        baseline_ctl = load_isolated(
            baseline_root, "release_qualification_controller_fourth_baseline",
        )
        candidate_ctl = load_isolated(
            candidate_root, "release_qualification_controller_fourth_candidate",
        )

        if os.name != "nt":
            # A durable direct exit is not a durable supervisor success.  Kill
            # the exact supervisor after direct-exit publication while an
            # escaped child remains and prove the current worker accepts it.
            root = candidate_root / "supervisor-exit-red"
            root.mkdir(parents=True)
            escaped_pids = root / "work" / "escaped-pids.json"
            escaped_release = root / "work" / "release-late-stdio"
            escaped_ack = root / "work" / "late-stdio-complete"
            escaped: dict[int, str] = {}
            supervisor: dict[int, str] = {}
            receipt = None
            refusal_code = None
            stale_stdout = stale_stderr = False
            escaped_child = f"""import json, os, time
from pathlib import Path
p = Path({str(escaped_pids)!r})
t = p.with_name('.' + p.name + '.tmp')
t.write_text(json.dumps([os.getpid()]), encoding='ascii')
os.replace(t, p)
release = Path({str(escaped_release)!r})
ack = Path({str(escaped_ack)!r})
while not release.exists():
    time.sleep(.01)
os.write(1, b'late-stdout-after-receipt')
os.fsync(1)
os.write(2, b'late-stderr-after-receipt')
os.fsync(2)
ack.write_text('done', encoding='ascii')
time.sleep(60)
"""
            product = (
                "import subprocess,sys;"
                f"subprocess.Popen([sys.executable,'-c',{escaped_child!r}],start_new_session=True)"
            )
            try:
                _start(
                    candidate_ctl, root, "supervisor-exit", product,
                    allowed_output_roots=[root / "work"],
                )
                escaped = _identities(candidate_ctl, _wait_for_pid_list(escaped_pids))
                _wait_for_path(
                    root / "runs" / "supervisor-exit" / "direct-exit.json",
                    timeout_s=20,
                )
                journal = json.loads(
                    (root / "runs" / "supervisor-exit" / "journal.json").read_text(
                        encoding="ascii",
                    )
                )
                spawned = next(
                    row for row in journal["events"] if row.get("event") == "child_spawned"
                )
                supervisor = {spawned["child_pid"]: spawned["process_token"]}
                signalled_supervisor = _terminate_identities(candidate_ctl, supervisor)
                assert signalled_supervisor == set(supervisor.items()), (
                    signalled_supervisor, supervisor,
                )
                try:
                    receipt = candidate_ctl.wait_run(
                        run_root=root / "runs", run_id="supervisor-exit", timeout_s=20,
                    )
                except Exception as exc:
                    refusal_code = getattr(exc, "code", None)
                assert not escaped_release.exists() and not escaped_ack.exists()
                assert receipt is not None and receipt.get("state") == "succeeded"
                stdout_path = Path(receipt["stdout"]["path"])
                stderr_path = Path(receipt["stderr"]["path"])
                assert hashlib.sha256(stdout_path.read_bytes()).hexdigest() == receipt[
                    "stdout"
                ]["sha256"]
                assert hashlib.sha256(stderr_path.read_bytes()).hexdigest() == receipt[
                    "stderr"
                ]["sha256"]
                escaped_release.write_text("release", encoding="ascii")
                _wait_for_path(escaped_ack, timeout_s=10)
                stale_stdout = (
                    hashlib.sha256(stdout_path.read_bytes()).hexdigest()
                    != receipt["stdout"]["sha256"]
                )
                stale_stderr = (
                    hashlib.sha256(stderr_path.read_bytes()).hexdigest()
                    != receipt["stderr"]["sha256"]
                )
                assert stale_stdout and stale_stderr
            finally:
                _cancel_finally(candidate_ctl, root, "supervisor-exit")
                _terminate_identities(candidate_ctl, {**supervisor, **escaped})
            journal_state = json.loads(
                (root / "runs" / "supervisor-exit" / "journal.json").read_text(
                    encoding="ascii",
                )
            ).get("state")
            safe_failure = (
                receipt is None and refusal_code == "EVIDENCE_INCOMPLETE"
                and journal_state == "recovery_required"
                and not (root / "runs" / "supervisor-exit" / "receipt.json").exists()
            )
            receipt_summary = None if receipt is None else {
                "state": receipt.get("state"),
                "exit": receipt.get("exit"),
                "stdout_bound": receipt.get("stdout") is not None,
                "stderr_bound": receipt.get("stderr") is not None,
                "stdout_digest_stale": stale_stdout,
                "stderr_digest_stale": stale_stderr,
            }
            require(
                "SUPERVISOR-NONZERO-AFTER-DIRECT-EXIT-INCOMPLETE",
                safe_failure,
                f"worker accepted or bound stale terminal output: receipt={receipt_summary!r}, "
                f"refusal={refusal_code!r}, journal_state={journal_state!r}",
            )

            # The immutable baseline must not publish terminal evidence while a
            # true double-forked, setsid descendant can still write later.
            root = baseline_root / "double-fork-red"
            root.mkdir(parents=True)
            descendant_pids = root / "work" / "double-fork-pids.json"
            late_output = root / "work" / "late-output.txt"
            late_release = root / "work" / "release-late-output"
            descendants: dict[int, str] = {}
            alive_at_terminal: list[int] = []
            late_after_terminal = False
            double_fork = f"""import json, os, time
from pathlib import Path
first = os.fork()
if first == 0:
    second = os.fork()
    if second == 0:
        os.setsid()
        p = Path({str(descendant_pids)!r})
        t = p.with_name('.' + p.name + '.tmp')
        t.write_text(json.dumps([os.getpid()]), encoding='ascii')
        os.replace(t, p)
        release = Path({str(late_release)!r})
        while not release.exists():
            time.sleep(.01)
        Path({str(late_output)!r}).write_text('late', encoding='ascii')
        time.sleep(60)
    os._exit(0)
os.waitpid(first, 0)
"""
            try:
                _start(
                    baseline_ctl, root, "double-fork", f"exec({double_fork!r})",
                    allowed_output_roots=[root / "work"],
                )
                descendants = _identities(
                    baseline_ctl, _wait_for_pid_list(descendant_pids),
                )
                _wait(baseline_ctl, root, "double-fork")
                alive_at_terminal = _alive_identities(baseline_ctl, descendants)
                assert not late_release.exists() and not late_output.exists()
                late_release.write_text("release", encoding="ascii")
                _wait_for_path(late_output, timeout_s=5)
                late_after_terminal = late_output.is_file()
            finally:
                _cancel_finally(baseline_ctl, root, "double-fork")
                _terminate_identities(baseline_ctl, descendants)
            require(
                "POSIX-DOUBLE-FORK-SETSID-LATE-WRITER-OWNED",
                not alive_at_terminal and not late_after_terminal,
                f"terminal preceded owned late writer: alive={alive_at_terminal}, "
                f"late_after_terminal={late_after_terminal}",
            )

            # A TERM handler can fork a new setsid child while cleanup is in
            # progress.  Immutable baseline cleanup never rescans that escape.
            root = baseline_root / "term-fork-red"
            root.mkdir(parents=True)
            ready = root / "work" / "term-ready.txt"
            term_pids = root / "work" / "term-fork-pids.json"
            term_descendants: dict[int, str] = {}
            alive_after_cancel: list[int] = []
            handler_child = (
                "import json,os,time;from pathlib import Path;"
                f"p=Path({str(term_pids)!r});t=p.with_name('.'+p.name+'.tmp');"
                "t.write_text(json.dumps([os.getpid()]),encoding='ascii');os.replace(t,p);"
                "time.sleep(60)"
            )
            handler_product = f"""import signal, subprocess, sys, time
from pathlib import Path
def handle(_signum, _frame):
    subprocess.Popen([sys.executable, '-c', {handler_child!r}], start_new_session=True)
signal.signal(signal.SIGTERM, handle)
Path({str(ready)!r}).write_text('ready', encoding='ascii')
while True:
    time.sleep(.05)
"""
            try:
                _start(
                    baseline_ctl, root, "term-fork", f"exec({handler_product!r})",
                    allowed_output_roots=[root / "work"],
                )
                _wait_for_path(ready)
                baseline_ctl.cancel_run(
                    run_root=root / "runs", run_id="term-fork", timeout_s=30,
                )
                term_descendants = _identities(
                    baseline_ctl, _wait_for_pid_list(term_pids, timeout_s=5),
                )
                alive_after_cancel = _alive_identities(baseline_ctl, term_descendants)
            finally:
                _cancel_finally(baseline_ctl, root, "term-fork")
                _terminate_identities(baseline_ctl, term_descendants)
            require(
                "POSIX-TERM-FORK-DYNAMIC-RESCAN",
                not alive_after_cancel,
                f"TERM-created setsid descendants survived cancellation: {alive_after_cancel}",
            )
        else:
            platform_skips += 3

        # Acquisition and cleanup can fail together.  The primary and cleanup
        # failures must remain typed/preserved while stream and local RLock are
        # unconditionally released.
        class CompoundParent:
            @staticmethod
            def mkdir(**_kwargs):
                return None

        class CompoundStream:
            def __init__(self):
                self.close_count = 0

            @staticmethod
            def seek(*_args):
                return 1

            @staticmethod
            def fileno():
                return 12345

            def close(self):
                self.close_count += 1
                raise OSError("cleanup-close")

        class CompoundPath:
            parent = CompoundParent()

            def __init__(self, stream):
                self.stream = stream

            def open(self, _mode):
                return self.stream

        if os.name == "nt":
            import msvcrt as lock_module
            primitive_name = "locking"
        else:
            import fcntl as lock_module
            primitive_name = "flock"
        original_primitive = getattr(lock_module, primitive_name)
        compound_stream = CompoundStream()
        compound_lock = candidate_ctl._RunLock(CompoundPath(compound_stream), timeout_s=0)
        compound_error = None
        setattr(
            lock_module, primitive_name,
            lambda *_args: (_ for _ in ()).throw(OSError("primary-acquire")),
        )
        try:
            compound_lock.__enter__()
        except Exception as exc:
            compound_error = exc
        finally:
            setattr(lock_module, primitive_name, original_primitive)
        atomic_released = second_thread_can_acquire(candidate_ctl._ATOMIC_LOCK)
        if not atomic_released:
            candidate_ctl._ATOMIC_LOCK.release()
        compound_text = exception_text(compound_error)
        require(
            "RUNLOCK-ACQUIRE-AND-CLOSE-FAIL-PRESERVED",
            isinstance(compound_error, candidate_ctl.ControllerRefusal)
            and getattr(compound_error, "code", None) == "RELEASE-CONTROLLER-IO"
            and "primary-acquire" in compound_text and "cleanup-close" in compound_text
            and compound_lock.stream is None and compound_stream.close_count == 1
            and atomic_released,
            f"compound failure lost cleanup/state/lock: error={compound_text!r}, "
            f"stream_cleared={compound_lock.stream is None}, "
            f"close_count={compound_stream.close_count}, atomic_released={atomic_released}",
        )

        # Every lock-file initialization stage is typed IO and releases both
        # stream and local lock.  Fake objects keep this deterministic.
        initialization_failures: list[str] = []
        for stage in ("mkdir", "open", "write", "flush", "fsync"):
            class InitParent:
                def mkdir(self, **_kwargs):
                    if stage == "mkdir":
                        raise OSError("mkdir-init")

            class InitStream:
                def __init__(self):
                    self.close_count = 0

                @staticmethod
                def seek(*_args):
                    return 0

                def write(self, _raw):
                    if stage == "write":
                        raise OSError("write-init")
                    return 1

                def flush(self):
                    if stage == "flush":
                        raise OSError("flush-init")

                @staticmethod
                def fileno():
                    return 12345

                def close(self):
                    self.close_count += 1

            class InitPath:
                parent = InitParent()

                def __init__(self, stream):
                    self.stream = stream

                def open(self, _mode):
                    if stage == "open":
                        raise OSError("open-init")
                    return self.stream

            stream = InitStream()
            lock = candidate_ctl._RunLock(InitPath(stream), timeout_s=0)
            original_fsync = candidate_ctl.os.fsync
            if stage == "fsync":
                candidate_ctl.os.fsync = lambda _fd: (_ for _ in ()).throw(
                    OSError("fsync-init")
                )
            error = None
            try:
                lock.__enter__()
            except Exception as exc:
                error = exc
            finally:
                candidate_ctl.os.fsync = original_fsync
            released = second_thread_can_acquire(candidate_ctl._ATOMIC_LOCK)
            if not released:
                candidate_ctl._ATOMIC_LOCK.release()
            expected_close = 0 if stage in {"mkdir", "open"} else 1
            if not (
                isinstance(error, candidate_ctl.ControllerRefusal)
                and getattr(error, "code", None) == "RELEASE-CONTROLLER-IO"
                and lock.stream is None and stream.close_count == expected_close
                and released
            ):
                initialization_failures.append(
                    f"{stage}: error={exception_text(error)!r}, "
                    f"stream_cleared={lock.stream is None}, close_count={stream.close_count}, "
                    f"released={released}"
                )
        require(
            "RUNLOCK-INITIALIZATION-FAILURES-TYPED",
            not initialization_failures,
            "; ".join(initialization_failures),
        )

    expected_cases = 5 if os.name != "nt" else 2
    expected_skips = 0 if os.name != "nt" else 3
    assert cases == expected_cases, (cases, expected_cases)
    assert platform_skips == expected_skips, (platform_skips, expected_skips)
    assert len(failures) == expected_cases, failures
    print(f"fourth-red baseline_commit={baseline_commit}")
    print(
        "baseline inputs: " + ", ".join(
            f"{relative}={digest}" for relative, digest in baseline_files.items()
        )
    )
    print(
        f"candidate inputs ({candidate_commit}): " + ", ".join(
            f"{relative}={digest}" for relative, digest in candidate_files.items()
        )
    )
    print(
        f"platform: os.name={os.name}; behavioral_cases={cases}; "
        f"platform_skips={platform_skips}; posix_evidence="
        f"{'executed' if os.name != 'nt' else 'not-run'}"
    )
    for failure in failures:
        print(f"RED {failure}")
    print("cleanup: exact handles/pidfds quiescent; disposable fourth-red roots removed")
    raise AssertionError("expected fourth-review red regressions:\n- " + "\n- ".join(failures))


def main() -> int:
    global _FIXTURE_OWNER_MODE
    fixture_owner_mode = _execution_mode()
    if os.environ.get("COAUTHOR_CONTROLLER_FOURTH_REOPENED_RED") == "1":
        return _fourth_reopened_red()
    if os.environ.get("COAUTHOR_CONTROLLER_THIRD_REOPENED_RED") == "1":
        return _third_reopened_red()
    if os.environ.get("COAUTHOR_CONTROLLER_REOPENED_RED") == "1":
        return _reopened_red_against_committed()
    _FIXTURE_OWNER_MODE = fixture_owner_mode
    env = _load(ENVIRONMENT, "qualification_environment")
    ctl = _load(MODULE, "release_qualification_controller")
    cases = 0
    platform_skips = 0
    expected_failures: list[str] = []
    _assert_release_gate_bytecode_argv()
    _case_verify_child_path_spelling()
    cases += 1
    _case_legacy_peer_walk_hits_cap()
    cases += 1
    _case_fixed_point_walk_terminates()
    cases += 1
    _case_phase01_native_open_and_git()
    cases += 1
    unknown_env, _ = env.controlled_environment(
        delta={"COAUTHOR_CONTROLLER_REOPENED_RED": "1"}, allow_user_site=True,
    )
    unknown = subprocess.run(
        [sys.executable, "-B", str(Path(__file__).resolve()), "--unknown-mode"],
        env=unknown_env, stdin=subprocess.DEVNULL, capture_output=True, check=False,
    )
    assert unknown.returncode != 0
    assert b"unsupported controller-smoketest arguments: ['--unknown-mode']" in unknown.stderr
    assert b"reopened-red target:" not in unknown.stdout
    cases += 1
    with tempfile.TemporaryDirectory(prefix="release-controller-smoke-") as raw:
        root = Path(raw)

        native_environment = root / "work" / "native-environment.json"
        native_cli = ctl._parser().parse_args([
            "run", "--run-root", str(root / "cli-runs"), "--run-id", "native-cli",
            "--cwd", str(root), "--dependency-mode", "native", "--",
            sys.executable, "-c", "print('native-cli')",
        ])
        assert native_cli.dependency_mode == "native"
        _start(
            ctl,
            root,
            "native-dependency-mode",
            "import json,os;from pathlib import Path;"
            f"Path({str(native_environment)!r}).write_text(json.dumps({{"
            "'pythonpath_present':'PYTHONPATH' in os.environ,"
            "'no_user_site':os.environ.get('PYTHONNOUSERSITE')},sort_keys=True),"
            "encoding='ascii')",
            dependency_mode="native",
            allowed_output_roots=[root / "work"],
        )
        native_receipt = _wait(ctl, root, "native-dependency-mode")
        native_intent = json.loads(
            (root / "runs" / "native-dependency-mode" / "intent.json").read_text(
                encoding="ascii"
            )
        )
        assert native_receipt["state"] == "succeeded", native_receipt
        assert native_receipt["dependency_mode"] == "native"
        assert native_intent["dependency_mode"] == "native"
        assert json.loads(native_environment.read_text(encoding="ascii")) == {
            "no_user_site": "1",
            "pythonpath_present": False,
        }
        cases += 1

        # The terminal receipt must bind the resolved dependency mode in both
        # directions; a schema-valid flip cannot change execution provenance.
        for original_mode, flipped_mode in (
            ("native", "enumerated"), ("enumerated", "native"),
        ):
            run_id = f"dependency-mode-tamper-{original_mode}"
            _start(
                ctl, root, run_id, "print('dependency-mode-bound')",
                dependency_mode=original_mode,
            )
            _wait(ctl, root, run_id)
            receipt_path = root / "runs" / run_id / "receipt.json"
            receipt_value = json.loads(receipt_path.read_text(encoding="ascii"))
            assert receipt_value["dependency_mode"] == original_mode
            receipt_value["dependency_mode"] = flipped_mode
            receipt_path.write_text(
                json.dumps(receipt_value, sort_keys=True), encoding="ascii",
            )
            _expect("EVIDENCE_INCOMPLETE", lambda run_id=run_id: ctl.status_run(
                run_root=root / "runs", run_id=run_id,
            ))
            cases += 1

        handoff_probe = root / "positive-pid-handoff.probe"
        try:
            _wait_for_positive_pid(handoff_probe, timeout_s=.001)
        except AssertionError as exc:
            assert "PID handoff remained absent" in str(exc)
            assert "FileNotFoundError" in str(exc)
        else:
            raise AssertionError("missing PID handoff was accepted")
        for invalid in (
            b"", b"0", b"-1", b"+1", b" 1", b"1 ", b"01", b"1.0", b"\xff",
            b"4294967296", b"1" * 5000,
        ):
            handoff_probe.write_bytes(invalid)
            try:
                _wait_for_positive_pid(handoff_probe, timeout_s=.001)
            except AssertionError as exc:
                assert repr(invalid) in str(exc)
            else:
                raise AssertionError(f"invalid PID handoff accepted: {invalid!r}")
        handoff_probe.write_bytes(b"123")
        assert _wait_for_positive_pid(handoff_probe) == 123
        handoff_probe.unlink()

        class ScriptedPidHandoff:
            def __init__(self, outcomes, *, repeat_last: bool = False):
                self.outcomes = list(outcomes)
                self.repeat_last = repeat_last
                self.read_count = 0

            def read_bytes(self) -> bytes:
                index = self.read_count
                self.read_count += 1
                if index >= len(self.outcomes):
                    if not self.repeat_last:
                        raise AssertionError("scripted PID handoff exhausted")
                    index = len(self.outcomes) - 1
                outcome = self.outcomes[index]
                if isinstance(outcome, BaseException):
                    raise outcome
                return outcome

            def __str__(self) -> str:
                return "<scripted-pid-handoff>"

        denial_then_success = ScriptedPidHandoff([
            PermissionError(errno.EACCES, "synthetic access denial"), b"123",
        ])
        assert _wait_for_positive_pid(denial_then_success, timeout_s=.1) == 123
        assert denial_then_success.read_count == 2
        cases += 1

        persistent_denial = ScriptedPidHandoff(
            [PermissionError(errno.EACCES, "synthetic persistent access denial")],
            repeat_last=True,
        )
        denial_started = time.monotonic()
        try:
            _wait_for_positive_pid(persistent_denial, timeout_s=.025)
        except AssertionError as exc:
            assert "PID handoff remained access-denied" in str(exc)
            assert "PermissionError" in str(exc)
        else:
            raise AssertionError("persistent PID handoff access denial was accepted")
        assert time.monotonic() - denial_started >= .02
        assert persistent_denial.read_count >= 2
        cases += 1

        malformed_terminal = ScriptedPidHandoff([b"01", b"123"])
        try:
            _wait_for_positive_pid(malformed_terminal, timeout_s=.1)
        except AssertionError as exc:
            assert "not canonical positive base-10 ASCII" in str(exc)
            assert "b'01'" in str(exc)
        else:
            raise AssertionError("malformed PID handoff was accepted")
        assert malformed_terminal.read_count == 1
        cases += 1

        if _FIXTURE_OWNER_MODE:
            _windows_fixture_owner_contract(ctl, root)

        observation_rows, observation_failures = _windows_observation_contract(ctl)
        assert observation_rows == 8 and not observation_failures, observation_failures
        _windows_terminate_race_contract(ctl)
        cases += 1
        _run_lock_contract(ctl, root)
        cases += 1

        class NoTokenController:
            @staticmethod
            def _process_token(_pid):
                return None

        class NeverReaped:
            pid = 919191

            @staticmethod
            def communicate(timeout):
                raise subprocess.TimeoutExpired(["synthetic-frontend"], timeout)

        try:
            _capture_identity(NoTokenController(), {}, NeverReaped.pid)
        except AssertionError:
            pass
        else:
            raise AssertionError("unavailable frontend identity was suppressed")
        try:
            _reap_frontends([NeverReaped()])
        except AssertionError:
            pass
        else:
            raise AssertionError("unreaped frontend was suppressed")
        cases += 1

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

        # The short-lived launcher exits; the detached bare-host worker or
        # fixture-owned nested worker still completes.
        launcher_code = (
            "import site,sys;from pathlib import Path;"
            f"[site.addsitedir(p) for p in {ctl._dependency_paths()!r}];"
            f"sys.path.insert(0,{str(MODULE.parent)!r});import release_qualification_controller as c;"
            f"c.start_run(run_root={str(root / 'runs')!r},run_id='disconnect',"
            f"argv=[sys.executable,'-c','import time;time.sleep(.4);print(99)'],cwd={str(root / 'work')!r},"
            f"output_watch_roots=[{str(root / 'work')!r}],"
            f"detached={not (os.name == 'nt' and _FIXTURE_OWNER_MODE)!r})"
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


        # Kill the launcher immediately after it spawns the detached bare-host
        # worker or fixture-owned nested worker, before the launcher can write
        # owner.json.  The worker must establish its own durable identity and
        # complete exactly once.
        crash_counter = root / "work" / "launcher-crash.counter"
        crash_launcher = f"""
import os, site, sys
[site.addsitedir(p) for p in {ctl._dependency_paths()!r}]
sys.path.insert(0, {str(MODULE.parent)!r})
import release_qualification_controller as c
original_spawn = c._spawn_worker_process
def spawn_then_die(*args, **kwargs):
    original_spawn(*args, **kwargs)
    os._exit(73)
c._spawn_worker_process = spawn_then_die
c.start_run(
    run_root={str(root / 'runs')!r}, run_id='launcher-crash',
    argv=[sys.executable, '-c', {f"from pathlib import Path;Path({str(crash_counter)!r}).write_text('once')"!r}],
    cwd={str(root / 'work')!r},
    allowed_output_roots=[{str(root / 'work')!r}],
    output_watch_roots=[{str(root / 'work')!r}],
    detached={not (os.name == 'nt' and _FIXTURE_OWNER_MODE)!r},
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

        if os.name == "nt":
            # Detached-worker launch planning is explicit and fail-closed.
            assert ctl._windows_escape_creation_flag(False, None) == 0
            assert ctl._windows_escape_creation_flag(True, 0x1000) == 0
            assert ctl._windows_escape_creation_flag(True, 0x0800) == 0x01000000
            _expect(
                "RELEASE-CONTROLLER-PROCESS",
                lambda: ctl._windows_escape_creation_flag(True, 0),
            )
            _expect(
                "RELEASE-CONTROLLER-PROCESS",
                lambda: ctl._windows_escape_creation_flag(True, None),
            )
            cases += 1

            # Windows product launch is bound to one concrete absolute regular
            # non-reparse executable before any run directory or child exists.
            concrete_executable = Path(sys.executable)
            expected_executable = os.path.normcase(os.path.realpath(concrete_executable))
            assert concrete_executable.is_absolute() and concrete_executable.is_file()
            assert not ctl._is_reparse(concrete_executable)
            assert ctl._windows_concrete_executable(str(concrete_executable)) == expected_executable
            executable_preflight_sentinel = root / "work" / "executable-preflight-ran.txt"
            _expect(
                "RELEASE-CONTROLLER-PROCESS",
                lambda: ctl.start_run(
                    run_root=root / "runs", run_id="relative-executable-refused",
                    argv=[
                        concrete_executable.name, "-B", "-c",
                        "from pathlib import Path;"
                        f"Path({str(executable_preflight_sentinel)!r}).write_text('ran')",
                    ],
                    cwd=root / "work", output_watch_roots=[root / "work"],
                ),
            )
            assert not (root / "runs" / "relative-executable-refused").exists()
            assert not executable_preflight_sentinel.exists()
            original_is_reparse = ctl._is_reparse
            ctl._is_reparse = lambda path: (
                Path(path) == concrete_executable or original_is_reparse(path)
            )
            try:
                _expect(
                    "RELEASE-CONTROLLER-PROCESS",
                    lambda: ctl._windows_concrete_executable(str(concrete_executable)),
                )
            finally:
                ctl._is_reparse = original_is_reparse
            cases += 1

            # The created image is inspected while its primary thread remains
            # suspended.  A mismatch kills and closes that exact process before
            # the sentinel can execute, without leaving a member in the Job.
            image_sentinel = root / "work" / "created-image-mismatch-ran.txt"
            image_job = ctl._WindowsJob()
            original_image_path = ctl._windows_process_image_path
            captured_image_process: dict[str, object] = {}
            direct_terminate_failures: list[tuple[int, int]] = []
            import _winapi as _image_winapi
            import ctypes as _image_ctypes
            from ctypes import wintypes as _image_wintypes
            original_terminate_process = _image_winapi.TerminateProcess
            image_kernel32 = _image_ctypes.WinDLL("kernel32", use_last_error=True)
            image_kernel32.GetProcessId.argtypes = (_image_wintypes.HANDLE,)
            image_kernel32.GetProcessId.restype = _image_wintypes.DWORD
            image_kernel32.WaitForSingleObject.argtypes = (
                _image_wintypes.HANDLE, _image_wintypes.DWORD,
            )
            image_kernel32.WaitForSingleObject.restype = _image_wintypes.DWORD
            def mismatch_created_image(handle):
                pid = int(image_kernel32.GetProcessId(_image_wintypes.HANDLE(handle)))
                assert pid > 0
                token = ctl._process_token(pid)
                assert isinstance(token, str) and token
                captured_image_process.update(handle=int(handle), pid=pid, token=token)
                return os.path.normcase(os.path.realpath(root / "not-the-created-image.exe"))
            def refuse_direct_terminate(handle, exit_code):
                direct_terminate_failures.append((int(handle), int(exit_code)))
                raise OSError(5, "synthetic direct TerminateProcess refusal")
            ctl._windows_process_image_path = mismatch_created_image
            _image_winapi.TerminateProcess = refuse_direct_terminate
            try:
                with open(os.devnull, "rb") as devnull, open(os.devnull, "wb") as devnull_out:
                    _expect(
                        "RELEASE-CONTROLLER-PROCESS",
                        lambda: ctl._spawn_windows_job_process(
                            [
                                str(concrete_executable), "-B", "-c",
                                "from pathlib import Path;"
                                f"Path({str(image_sentinel)!r}).write_text('ran')",
                            ],
                            cwd=root / "work", environment=dict(launcher_env),
                            stdin=devnull, stdout=devnull_out, stderr=devnull_out,
                            job=image_job,
                        ),
                    )
                assert captured_image_process.keys() == {"handle", "pid", "token"}
                assert direct_terminate_failures == [
                    (captured_image_process["handle"], 1223),
                ]
                _image_ctypes.set_last_error(0)
                assert image_kernel32.WaitForSingleObject(
                    _image_wintypes.HANDLE(captured_image_process["handle"]), 0,
                ) == 0xFFFFFFFF
                assert _image_ctypes.get_last_error() == 6  # ERROR_INVALID_HANDLE
                assert image_job.active_processes() == 0
                assert not _alive_identities(
                    ctl,
                    {captured_image_process["pid"]: captured_image_process["token"]},
                )
                assert not image_sentinel.exists()
            finally:
                _image_winapi.TerminateProcess = original_terminate_process
                ctl._windows_process_image_path = original_image_path
                if {"pid", "token"} <= captured_image_process.keys():
                    _terminate_identities(
                        ctl,
                        {captured_image_process["pid"]: captured_image_process["token"]},
                    )
                image_job.close()
            cases += 1

            # A non-Exception interruption after CreateProcess must be re-raised
            # only after the exact suspended process is terminated and closed.
            class SuspendedLaunchAbort(BaseException):
                pass
            abort_sentinel = root / "work" / "base-exception-ran.txt"
            abort_job = ctl._WindowsJob()
            abort_process: dict[str, object] = {}
            abort_fault = SuspendedLaunchAbort("synthetic suspended-launch abort")
            original_image_path = ctl._windows_process_image_path
            def abort_created_image(handle):
                pid = int(image_kernel32.GetProcessId(_image_wintypes.HANDLE(handle)))
                assert pid > 0
                token = ctl._process_token(pid)
                assert isinstance(token, str) and token
                abort_process.update(handle=int(handle), pid=pid, token=token)
                raise abort_fault
            ctl._windows_process_image_path = abort_created_image
            try:
                with open(os.devnull, "rb") as devnull, open(os.devnull, "wb") as devnull_out:
                    try:
                        ctl._spawn_windows_job_process(
                            [
                                str(concrete_executable), "-B", "-c",
                                "from pathlib import Path;"
                                f"Path({str(abort_sentinel)!r}).write_text('ran')",
                            ],
                            cwd=root / "work", environment=dict(launcher_env),
                            stdin=devnull, stdout=devnull_out, stderr=devnull_out,
                            job=abort_job,
                        )
                    except SuspendedLaunchAbort as exc:
                        assert exc is abort_fault
                    else:
                        raise AssertionError("suspended BaseException was suppressed")
                assert abort_process.keys() == {"handle", "pid", "token"}
                _image_ctypes.set_last_error(0)
                assert image_kernel32.WaitForSingleObject(
                    _image_wintypes.HANDLE(abort_process["handle"]), 0,
                ) == 0xFFFFFFFF
                assert _image_ctypes.get_last_error() == 6  # ERROR_INVALID_HANDLE
                assert abort_job.active_processes() == 0
                assert not _alive_identities(
                    ctl, {abort_process["pid"]: abort_process["token"]},
                )
                assert not abort_sentinel.exists()
            finally:
                ctl._windows_process_image_path = original_image_path
                if {"pid", "token"} <= abort_process.keys():
                    _terminate_identities(
                        ctl, {abort_process["pid"]: abort_process["token"]},
                    )
                abort_job.close()
            cases += 1

            # A BaseException raised after ResumeThread (while ownership is
            # being wrapped for return) still terminates, drains, and closes
            # the exact resumed process before the original fault is re-raised.
            class PostResumeAbort(BaseException):
                pass
            post_resume_marker = root / "work" / "post-resume-abort-ran.txt"
            post_resume_ready = root / "work" / "post-resume-descendant.ready"
            post_resume_job = ctl._WindowsJob()
            post_resume_process: dict[str, object] = {}
            post_resume_descendant: dict[str, object] = {}
            post_resume_fault = PostResumeAbort("synthetic post-resume abort")
            original_windows_process = ctl._WindowsProcess
            post_resume_descendant_code = (
                "import time;from pathlib import Path;time.sleep(.7);"
                f"Path({str(post_resume_marker)!r}).write_text('ran')"
            )
            post_resume_code = (
                "import subprocess,sys,time;from pathlib import Path;"
                f"p=subprocess.Popen([sys.executable,'-B','-c',{post_resume_descendant_code!r}]);"
                f"r=Path({str(post_resume_ready)!r});t=r.with_name(r.name+'.tmp');"
                "t.write_text(str(p.pid),encoding='ascii');t.replace(r);"
                "time.sleep(30)"
            )
            def abort_process_wrapper(handle, pid):
                token = ctl._process_token(int(pid))
                assert isinstance(token, str) and token
                post_resume_process.update(handle=int(handle), pid=int(pid), token=token)
                descendant_pid = _wait_for_positive_pid(post_resume_ready, timeout_s=5)
                descendant_token = ctl._process_token(descendant_pid)
                assert isinstance(descendant_token, str) and descendant_token
                post_resume_descendant.update(
                    pid=descendant_pid, token=descendant_token,
                )
                raise post_resume_fault
            ctl._WindowsProcess = abort_process_wrapper
            post_resume_unrelated = subprocess.Popen(
                [sys.executable, "-B", "-c", "import time;time.sleep(30)"],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, close_fds=True,
            )
            try:
                with open(os.devnull, "rb") as devnull, open(os.devnull, "wb") as devnull_out:
                    try:
                        ctl._spawn_windows_job_process(
                            [str(concrete_executable), "-B", "-c", post_resume_code],
                            cwd=root / "work", environment=dict(launcher_env),
                            stdin=devnull, stdout=devnull_out, stderr=devnull_out,
                            job=post_resume_job,
                        )
                    except PostResumeAbort as exc:
                        assert exc is post_resume_fault
                    else:
                        raise AssertionError("post-resume BaseException was suppressed")
                assert post_resume_process.keys() == {"handle", "pid", "token"}
                assert post_resume_descendant.keys() == {"pid", "token"}
                _image_ctypes.set_last_error(0)
                assert image_kernel32.WaitForSingleObject(
                    _image_wintypes.HANDLE(post_resume_process["handle"]), 0,
                ) == 0xFFFFFFFF
                assert _image_ctypes.get_last_error() == 6  # ERROR_INVALID_HANDLE
                assert post_resume_job.active_processes() == 0
                assert not _wait_identities_dead(
                    ctl,
                    {
                        post_resume_process["pid"]: post_resume_process["token"],
                        post_resume_descendant["pid"]: post_resume_descendant["token"],
                    },
                )
                time.sleep(.8)
                assert not post_resume_marker.exists()
                assert post_resume_unrelated.poll() is None
            finally:
                ctl._WindowsProcess = original_windows_process
                remaining_identities = {}
                if {"pid", "token"} <= post_resume_process.keys():
                    remaining_identities[post_resume_process["pid"]] = post_resume_process["token"]
                if {"pid", "token"} <= post_resume_descendant.keys():
                    remaining_identities[post_resume_descendant["pid"]] = (
                        post_resume_descendant["token"]
                    )
                if remaining_identities:
                    _terminate_identities(
                        ctl, remaining_identities,
                    )
                post_resume_job.close()
                if post_resume_unrelated.poll() is None:
                    post_resume_unrelated.terminate()
                post_resume_unrelated.wait(timeout=10)
            cases += 1

            # Every thread/stdio handle close is attempted even when each close
            # raises.  The failures are aggregated into one typed refusal, and
            # a genuinely resumed process plus its descendant are drained by
            # the process_handle-not-None Job-cleanup branch.
            close_sentinel = root / "work" / "launch-close-failure-ran.txt"
            close_ready = root / "work" / "launch-close-descendant.ready"
            close_job = ctl._WindowsJob()
            close_process: dict[str, object] = {}
            close_descendant: dict[str, object] = {}
            duplicated_handles: list[int] = []
            created_thread_handle: list[int] = []
            refused_close_handles: list[int] = []
            original_image_path = ctl._windows_process_image_path
            original_duplicate_handle = _image_winapi.DuplicateHandle
            original_create_process = _image_winapi.CreateProcess
            original_close_handle = _image_winapi.CloseHandle
            close_descendant_code = (
                "import time;from pathlib import Path;time.sleep(.7);"
                f"Path({str(close_sentinel)!r}).write_text('ran')"
            )
            close_product_code = (
                "import subprocess,sys,time;from pathlib import Path;"
                f"p=subprocess.Popen([sys.executable,'-B','-c',{close_descendant_code!r}]);"
                f"r=Path({str(close_ready)!r});t=r.with_name(r.name+'.tmp');"
                "t.write_text(str(p.pid),encoding='ascii');t.replace(r);"
                "time.sleep(30)"
            )
            def capture_for_close_failure(handle):
                pid = int(image_kernel32.GetProcessId(_image_wintypes.HANDLE(handle)))
                assert pid > 0
                token = ctl._process_token(pid)
                assert isinstance(token, str) and token
                close_process.update(handle=int(handle), pid=pid, token=token)
                return original_image_path(handle)
            def record_duplicate_handle(*args):
                handle = int(original_duplicate_handle(*args))
                duplicated_handles.append(handle)
                return handle
            def record_create_process(*args):
                value = original_create_process(*args)
                created_thread_handle.append(int(value[1]))
                return value
            def refuse_each_launch_close(handle):
                exact = int(handle)
                targets = {*duplicated_handles, *created_thread_handle}
                if exact in targets and exact not in refused_close_handles:
                    if created_thread_handle and exact == created_thread_handle[0]:
                        descendant_pid = _wait_for_positive_pid(close_ready, timeout_s=5)
                        descendant_token = ctl._process_token(descendant_pid)
                        assert isinstance(descendant_token, str) and descendant_token
                        close_descendant.update(
                            pid=descendant_pid, token=descendant_token,
                        )
                    refused_close_handles.append(exact)
                    raise OSError(6, f"synthetic CloseHandle refusal for {exact}")
                return original_close_handle(handle)
            ctl._windows_process_image_path = capture_for_close_failure
            _image_winapi.DuplicateHandle = record_duplicate_handle
            _image_winapi.CreateProcess = record_create_process
            _image_winapi.CloseHandle = refuse_each_launch_close
            close_refusal = None
            try:
                with open(os.devnull, "rb") as devnull, open(os.devnull, "wb") as devnull_out:
                    try:
                        ctl._spawn_windows_job_process(
                            [str(concrete_executable), "-B", "-c", close_product_code],
                            cwd=root / "work", environment=dict(launcher_env),
                            stdin=devnull, stdout=devnull_out, stderr=devnull_out,
                            job=close_job,
                        )
                    except Exception as exc:
                        close_refusal = exc
                assert getattr(close_refusal, "code", None) == "RELEASE-CONTROLLER-PROCESS"
                assert "cannot close Windows launch handles" in str(close_refusal)
                assert "primary thread handle" in str(close_refusal)
                assert all(
                    f"duplicated standard handle {index}" in str(close_refusal)
                    for index in range(3)
                )
                assert len(duplicated_handles) == 3
                assert len(created_thread_handle) == 1
                assert refused_close_handles == [
                    created_thread_handle[0], *duplicated_handles,
                ]
                assert close_process.keys() == {"handle", "pid", "token"}
                assert close_descendant.keys() == {"pid", "token"}
                _image_ctypes.set_last_error(0)
                assert image_kernel32.WaitForSingleObject(
                    _image_wintypes.HANDLE(close_process["handle"]), 0,
                ) == 0xFFFFFFFF
                assert _image_ctypes.get_last_error() == 6  # ERROR_INVALID_HANDLE
                assert close_job.active_processes() == 0
                assert not _wait_identities_dead(
                    ctl, {
                        close_process["pid"]: close_process["token"],
                        close_descendant["pid"]: close_descendant["token"],
                    },
                )
                time.sleep(.8)
                assert not close_sentinel.exists()
            finally:
                _image_winapi.CloseHandle = original_close_handle
                _image_winapi.CreateProcess = original_create_process
                _image_winapi.DuplicateHandle = original_duplicate_handle
                ctl._windows_process_image_path = original_image_path
                for handle in refused_close_handles:
                    try:
                        original_close_handle(handle)
                    except OSError as exc:
                        assert getattr(exc, "winerror", None) == 6, repr(exc)
                remaining_identities = {}
                if {"pid", "token"} <= close_process.keys():
                    remaining_identities[close_process["pid"]] = close_process["token"]
                if {"pid", "token"} <= close_descendant.keys():
                    remaining_identities[close_descendant["pid"]] = close_descendant["token"]
                if remaining_identities:
                    _terminate_identities(
                        ctl, remaining_identities,
                    )
                close_job.close()
            current_process = _image_winapi.GetCurrentProcess()
            owned_probe_handle = int(original_duplicate_handle(
                current_process, current_process, current_process, 0, False,
                _image_winapi.DUPLICATE_SAME_ACCESS,
            ))
            owned_probe = ctl._WindowsProcess(owned_probe_handle, os.getpid())
            probe_close_calls = 0
            def refuse_owned_probe_close(handle):
                nonlocal probe_close_calls
                if int(handle) == owned_probe_handle and probe_close_calls == 0:
                    probe_close_calls += 1
                    raise OSError(6, "synthetic owned-process CloseHandle refusal")
                return original_close_handle(handle)
            _image_winapi.CloseHandle = refuse_owned_probe_close
            try:
                _expect("RELEASE-CONTROLLER-PROCESS", owned_probe.close)
                assert owned_probe._handle == owned_probe_handle
            finally:
                _image_winapi.CloseHandle = original_close_handle
                owned_probe.close()
            assert probe_close_calls == 1 and owned_probe._handle == 0
            cases += 1

            # A failure while duplicating the inherited supervisor handle is
            # outside child creation but still owns the newly-created Job.
            # The Job handle is closed before the exact BaseException returns.
            class SupervisorDuplicateAbort(BaseException):
                pass
            duplicate_fault = SupervisorDuplicateAbort("synthetic supervisor duplicate abort")
            duplicate_job: list[object] = []
            duplicate_job_handle: list[int] = []
            original_duplicate_inheritable = ctl._WindowsJob.duplicate_inheritable
            def abort_supervisor_duplicate(self):
                duplicate_job.append(self)
                duplicate_job_handle.append(int(self.handle))
                raise duplicate_fault
            ctl._WindowsJob.duplicate_inheritable = abort_supervisor_duplicate
            try:
                with open(os.devnull, "wb") as devnull_out:
                    try:
                        ctl._spawn_worker_process(
                            ctl._paths(root / "runs", "duplicate-abort"),
                            launcher_env, devnull_out, devnull_out, detached=False,
                        )
                    except SupervisorDuplicateAbort as exc:
                        assert exc is duplicate_fault
                    else:
                        raise AssertionError("supervisor duplicate BaseException was suppressed")
                assert len(duplicate_job) == len(duplicate_job_handle) == 1
                assert duplicate_job[0].handle == 0
                _image_ctypes.set_last_error(0)
                assert image_kernel32.WaitForSingleObject(
                    _image_wintypes.HANDLE(duplicate_job_handle[0]), 0,
                ) == 0xFFFFFFFF
                assert _image_ctypes.get_last_error() == 6  # ERROR_INVALID_HANDLE
            finally:
                ctl._WindowsJob.duplicate_inheritable = original_duplicate_inheritable
                if duplicate_job and duplicate_job[0].handle:
                    duplicate_job[0].close()
            cases += 1

            # Worker cleanup tracks inherited and Job closes separately: a
            # supervisor-only close failure cannot retry an already-closed
            # inherited handle.  When inherited close itself fails, tree
            # termination, drain, Job close, and process close are independent.
            class WorkerSpawnAbort(BaseException):
                pass
            worker_spawn_fault = WorkerSpawnAbort("synthetic worker spawn abort")
            first_job: list[object] = []
            first_inherited: list[int] = []
            first_inherited_closes: list[int] = []
            first_job_close_calls = 0
            original_spawn_windows_job_process = ctl._spawn_windows_job_process
            original_job_close = ctl._WindowsJob.close
            original_close_handle = _image_winapi.CloseHandle
            def capture_first_inherited(self):
                handle = int(original_duplicate_inheritable(self))
                first_job.append(self)
                first_inherited.append(handle)
                return handle
            def abort_worker_spawn(*_args, **_kwargs):
                raise worker_spawn_fault
            def refuse_first_job_close(self):
                nonlocal first_job_close_calls
                if first_job and self is first_job[0] and first_job_close_calls == 0:
                    first_job_close_calls += 1
                    raise OSError(6, "synthetic supervisor Job close refusal")
                return original_job_close(self)
            def count_first_inherited_close(handle):
                if first_inherited and int(handle) == first_inherited[0]:
                    first_inherited_closes.append(int(handle))
                return original_close_handle(handle)
            ctl._WindowsJob.duplicate_inheritable = capture_first_inherited
            ctl._WindowsJob.close = refuse_first_job_close
            ctl._spawn_windows_job_process = abort_worker_spawn
            _image_winapi.CloseHandle = count_first_inherited_close
            first_refusal = None
            try:
                with open(os.devnull, "wb") as devnull_out:
                    try:
                        ctl._spawn_worker_process(
                            ctl._paths(root / "runs", "separate-close-state"),
                            launcher_env, devnull_out, devnull_out, detached=False,
                        )
                    except Exception as exc:
                        first_refusal = exc
                assert getattr(first_refusal, "code", None) == "RELEASE-CONTROLLER-PROCESS"
                assert first_inherited_closes == first_inherited
                assert first_job_close_calls == 1
            finally:
                _image_winapi.CloseHandle = original_close_handle
                ctl._spawn_windows_job_process = original_spawn_windows_job_process
                ctl._WindowsJob.close = original_job_close
                ctl._WindowsJob.duplicate_inheritable = original_duplicate_inheritable
                if first_job and first_job[0].handle:
                    first_job[0].close()

            cleanup_job: list[object] = []
            cleanup_inherited: list[int] = []
            cleanup_close_attempts: list[int] = []
            cleanup_events: list[str] = []
            class FakeWorker:
                pid = os.getpid()
                def wait(self, timeout=None):
                    cleanup_events.append("worker wait")
                    raise OSError(5, "synthetic worker wait refusal")
                def close(self):
                    cleanup_events.append("worker process handle close")
            fake_worker = FakeWorker()
            def capture_cleanup_inherited(self):
                handle = int(original_duplicate_inheritable(self))
                cleanup_job.append(self)
                cleanup_inherited.append(handle)
                return handle
            def return_fake_worker(*_args, **_kwargs):
                return fake_worker
            def fail_first_cleanup_close(handle):
                exact = int(handle)
                if cleanup_inherited and exact == cleanup_inherited[0]:
                    cleanup_close_attempts.append(exact)
                    if len(cleanup_close_attempts) == 1:
                        raise OSError(6, "synthetic inherited handle close refusal")
                return original_close_handle(handle)
            original_job_terminate = ctl._WindowsJob.terminate
            original_job_wait_empty = ctl._WindowsJob.wait_empty
            def fail_cleanup_terminate(self, exit_code=1223):
                cleanup_events.append("Job termination")
                raise OSError(5, "synthetic Job termination refusal")
            def fail_cleanup_drain(self, timeout_s=30.0):
                cleanup_events.append("Job drain")
                raise OSError(5, "synthetic Job drain refusal")
            def record_cleanup_job_close(self):
                cleanup_events.append("Job handle close")
                return original_job_close(self)
            ctl._WindowsJob.duplicate_inheritable = capture_cleanup_inherited
            ctl._WindowsJob.terminate = fail_cleanup_terminate
            ctl._WindowsJob.wait_empty = fail_cleanup_drain
            ctl._WindowsJob.close = record_cleanup_job_close
            ctl._spawn_windows_job_process = return_fake_worker
            _image_winapi.CloseHandle = fail_first_cleanup_close
            cleanup_refusal = None
            try:
                with open(os.devnull, "wb") as devnull_out:
                    try:
                        ctl._spawn_worker_process(
                            ctl._paths(root / "runs", "independent-worker-cleanup"),
                            launcher_env, devnull_out, devnull_out, detached=False,
                        )
                    except Exception as exc:
                        cleanup_refusal = exc
                assert getattr(cleanup_refusal, "code", None) == "RELEASE-CONTROLLER-PROCESS"
                assert cleanup_close_attempts == [cleanup_inherited[0], cleanup_inherited[0]]
                assert cleanup_events == [
                    "Job termination", "Job drain", "worker wait",
                    "Job handle close", "worker process handle close",
                ]
            finally:
                _image_winapi.CloseHandle = original_close_handle
                ctl._spawn_windows_job_process = original_spawn_windows_job_process
                ctl._WindowsJob.close = original_job_close
                ctl._WindowsJob.wait_empty = original_job_wait_empty
                ctl._WindowsJob.terminate = original_job_terminate
                ctl._WindowsJob.duplicate_inheritable = original_duplicate_inheritable
                if cleanup_job and cleanup_job[0].handle:
                    cleanup_job[0].close()
            cases += 1

            # A suspended worker that remains in any enclosing Job is killed
            # before its primary thread can execute, then refused.
            inherited_sentinel = root / "work" / "inherited-worker-ran.txt"
            inherited_job = ctl._WindowsJob()
            original_in_job = ctl._windows_process_in_any_job
            captured_inherited: dict[str, object] = {}
            import ctypes as _ctypes
            from ctypes import wintypes as _wintypes
            inherited_kernel32 = _ctypes.WinDLL("kernel32", use_last_error=True)
            inherited_kernel32.GetProcessId.argtypes = (_wintypes.HANDLE,)
            inherited_kernel32.GetProcessId.restype = _wintypes.DWORD
            inherited_kernel32.WaitForSingleObject.argtypes = (
                _wintypes.HANDLE, _wintypes.DWORD,
            )
            inherited_kernel32.WaitForSingleObject.restype = _wintypes.DWORD
            def capture_inherited(handle):
                pid = int(inherited_kernel32.GetProcessId(_wintypes.HANDLE(handle)))
                assert pid > 0
                token = ctl._process_token(pid)
                assert isinstance(token, str) and token
                captured_inherited.update(handle=int(handle), pid=pid, token=token)
                return True
            ctl._windows_process_in_any_job = capture_inherited
            try:
                with open(os.devnull, "rb") as devnull, open(os.devnull, "wb") as devnull_out:
                    _expect(
                        "RELEASE-CONTROLLER-PROCESS",
                        lambda: ctl._spawn_windows_job_process(
                            [
                                sys.executable, "-c",
                                f"from pathlib import Path;Path({str(inherited_sentinel)!r}).write_text('ran')",
                            ],
                            cwd=root / "work", environment=dict(launcher_env),
                            stdin=devnull, stdout=devnull_out, stderr=devnull_out,
                            job=inherited_job, require_no_enclosing_job=True,
                        ),
                    )
                assert inherited_job.active_processes() == 0
                assert captured_inherited.keys() == {"handle", "pid", "token"}
                assert not _alive_identities(
                    ctl, {captured_inherited["pid"]: captured_inherited["token"]},
                )
                _ctypes.set_last_error(0)
                assert inherited_kernel32.WaitForSingleObject(
                    _wintypes.HANDLE(captured_inherited["handle"]), 0,
                ) == 0xFFFFFFFF
                assert _ctypes.get_last_error() == 6  # ERROR_INVALID_HANDLE
                assert not inherited_sentinel.exists()
            finally:
                ctl._windows_process_in_any_job = original_in_job
                if {"pid", "token"} <= captured_inherited.keys():
                    _terminate_identities(
                        ctl,
                        {captured_inherited["pid"]: captured_inherited["token"]},
                    )
                inherited_job.close()
            cases += 1

            # A launcher in an explicit-breakaway outer Job may die with that
            # outer Job while its proven-jobless detached worker completes.
            outer_ready = root / "work" / "outer-breakaway.ready"
            outer_counter = root / "work" / "outer-breakaway.counter"
            outer_done = root / "work" / "outer-breakaway.launcher-done"
            outer_launcher = f"""
import json, site, sys, time
from pathlib import Path
[site.addsitedir(p) for p in {ctl._dependency_paths()!r}]
sys.path.insert(0, {str(MODULE.parent)!r})
import release_qualification_controller as c
value = c.start_run(
    run_root={str(root / 'runs')!r}, run_id='outer-breakaway',
    argv=[sys.executable, '-c', {f"import time;time.sleep(2);from pathlib import Path;Path({str(outer_counter)!r}).write_text('once')"!r}],
    cwd={str(root / 'work')!r},
    allowed_output_roots=[{str(root / 'work')!r}],
    output_watch_roots=[{str(root / 'work')!r}],
)
Path({str(outer_ready)!r}).write_text(json.dumps(value), encoding='ascii')
if {not _FIXTURE_OWNER_MODE!r}:
    time.sleep(60)
Path({str(outer_done)!r}).write_text('done', encoding='ascii')
"""
            outer_job = ctl._WindowsJob(limit_flags=0x2000 | 0x0800)
            outer_process = None
            outer_worker: dict[int, str] = {}
            try:
                with open(os.devnull, "rb") as devnull, open(os.devnull, "wb") as devnull_out:
                    outer_process = ctl._spawn_windows_job_process(
                        [sys.executable, "-c", outer_launcher],
                        cwd=root / "work", environment=dict(launcher_env),
                        stdin=devnull, stdout=devnull_out, stderr=devnull_out,
                        job=outer_job,
                    )
                _wait_for_path(outer_ready)
                if _FIXTURE_OWNER_MODE:
                    assert outer_process.wait(timeout=10) == 0
                    nested = ctl.status_run(
                        run_root=root / "runs", run_id="outer-breakaway",
                    )
                    assert nested["state"] == "refused"
                    assert nested["diagnostic"] == {
                        "code": "RELEASE-CONTROLLER-PROCESS",
                        "detail": "detached Windows worker remains in an enclosing Job",
                    }
                    assert nested["worker"] is None and nested["prechild_refusal"] is not None
                    nested_prechild = json.loads(
                        Path(nested["prechild_refusal"]["path"]).read_text(encoding="ascii")
                    )
                    assert nested_prechild["diagnostic"] == nested["diagnostic"]
                    assert nested_prechild["intent_sha256"] == nested["intent_sha256"]
                    assert "worker_spawned" not in _event_names(root, "outer-breakaway")
                    assert "child_spawned" not in _event_names(root, "outer-breakaway")
                    assert not outer_counter.exists() and outer_done.read_text() == "done"
                    outer_job.close()
                else:
                    owner = json.loads(
                        (root / "runs" / "outer-breakaway" / "owner.json").read_text(
                            encoding="ascii",
                        )
                    )
                    outer_worker = {owner["pid"]: owner["process_token"]}
                    assert _alive_identities(ctl, outer_worker) == list(outer_worker)
                    outer_job.close()
                    outer_process.wait(timeout=10)
                    assert not outer_done.exists()
                    assert _alive_identities(ctl, outer_worker) == list(outer_worker)
                    receipt = _wait(ctl, root, "outer-breakaway")
                    assert receipt["state"] == "succeeded"
                    assert outer_counter.read_text() == "once"
                    assert not _alive_identities(ctl, outer_worker)
            finally:
                if outer_job.handle:
                    outer_job.close()
                if outer_process is not None:
                    outer_process.close()
                if outer_worker:
                    _terminate_identities(ctl, outer_worker)
            cases += 1

            # A non-permissive outer Job yields a bound pre-child refusal;
            # neither a worker event nor the product sentinel may exist.
            denied_result = root / "work" / "outer-denied.result"
            denied_sentinel = root / "work" / "outer-denied.ran"
            denied_launcher = f"""
import json, site, sys
from pathlib import Path
[site.addsitedir(p) for p in {ctl._dependency_paths()!r}]
sys.path.insert(0, {str(MODULE.parent)!r})
import release_qualification_controller as c
value = c.start_run(
    run_root={str(root / 'runs')!r}, run_id='outer-denied',
    argv=[sys.executable, '-c', {f"from pathlib import Path;Path({str(denied_sentinel)!r}).write_text('ran')"!r}],
    cwd={str(root / 'work')!r},
    allowed_output_roots=[{str(root / 'work')!r}],
    output_watch_roots=[{str(root / 'work')!r}],
)
Path({str(denied_result)!r}).write_text(json.dumps(value), encoding='ascii')
"""
            denied_job = ctl._WindowsJob(limit_flags=0x2000)
            denied_process = None
            try:
                with open(os.devnull, "rb") as devnull, open(os.devnull, "wb") as devnull_out:
                    denied_process = ctl._spawn_windows_job_process(
                        [sys.executable, "-c", denied_launcher],
                        cwd=root / "work", environment=dict(launcher_env),
                        stdin=devnull, stdout=devnull_out, stderr=devnull_out,
                        job=denied_job,
                    )
                assert denied_process.wait(timeout=10) == 0
                _wait_for_path(denied_result)
                denied = ctl.status_run(run_root=root / "runs", run_id="outer-denied")
                assert denied["state"] == "refused"
                assert denied["diagnostic"]["code"] == "RELEASE-CONTROLLER-PROCESS"
                assert denied["worker"] is None and denied["prechild_refusal"] is not None
                assert all(
                    denied[key] is None for key in (
                        "process", "exit", "exit_capsule", "stdout", "stderr",
                    )
                )
                denied_prechild = json.loads(
                    Path(denied["prechild_refusal"]["path"]).read_text(encoding="ascii")
                )
                assert denied_prechild["intent_sha256"] == denied["intent_sha256"]
                assert denied_prechild["diagnostic"] == denied["diagnostic"]
                assert "worker_spawned" not in _event_names(root, "outer-denied")
                assert "child_spawned" not in _event_names(root, "outer-denied")
                assert not denied_sentinel.exists()
            finally:
                denied_job.close()
                if denied_process is not None:
                    denied_process.close()
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

        # Deliberately publish an empty PID handoff before atomically replacing
        # it with complete JSON.  File existence alone is not readiness.  On
        # Windows this deliberately uses the ordinary concrete interpreter for
        # both the Job root and its inherited descendant.
        unrelated = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(60)"],
                                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            run_id = "cancel"
            pid_file = root / "work" / "owned-pids.json"
            ready_file = root / "work" / "owned-pids.ready"
            tree_code = f"""
import json, os, subprocess, sys, time
from pathlib import Path
p = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(60)'])
path = Path({str(pid_file)!r})
path.touch()
Path({str(ready_file)!r}).write_text('empty-visible', encoding='ascii')
time.sleep(.2)
temporary = path.with_name('.' + path.name + '.complete')
with temporary.open('w', encoding='ascii') as stream:
    json.dump([os.getpid(), p.pid], stream)
    stream.flush()
    os.fsync(stream.fileno())
for attempt in range(100):
    try:
        os.replace(temporary, path)
        break
    except PermissionError:
        if attempt == 99:
            raise
        time.sleep(.01)
time.sleep(60)
"""
            owned_identities: dict[int, str] = {}
            receipt = None
            try:
                allowed = root / "work"
                _start(
                    ctl, root, run_id, tree_code,
                    allowed_output_roots=[allowed], output_watch_roots=[allowed],
                )
                _wait_for_path(ready_file)
                assert pid_file.read_bytes() == b""
                owned = _wait_for_pid_list(pid_file)
                owned_identities = _identities(ctl, owned)
                if os.name == "nt":
                    concrete = ctl._windows_concrete_executable(sys.executable)
                    assert concrete == os.path.normcase(os.path.realpath(sys.executable))
                receipt = ctl.cancel_run(
                    run_root=root / "runs", run_id=run_id, timeout_s=30,
                )
            finally:
                _cancel_finally(ctl, root, run_id)
                _terminate_identities(ctl, owned_identities)
            assert receipt is not None and receipt["state"] == "cancelled"
            assert receipt["process"]["pid"] == owned[0]
            assert unrelated.poll() is None
            assert not _alive_identities(ctl, owned_identities)
        finally:
            if unrelated.poll() is None:
                unrelated.terminate()
            unrelated.wait(timeout=10)
        cases += 1

        # A direct product exit cannot authorize a terminal receipt while an
        # owned descendant is explicitly blocked before its final output.
        # Preferred policy: wait for that descendant, include its output in the
        # final inventory, and only then publish terminal success.
        late_marker = root / "work" / "late-descendant.txt"
        late_pids = root / "work" / "late-descendant-pids.json"
        late_ready = root / "work" / "late-descendant.ready"
        parent_done = root / "work" / "late-parent.done"
        late_release = root / "work" / "late-descendant.release"
        descendant_code = (
            "import time;from pathlib import Path;"
            f"ready=Path({str(late_ready)!r});release=Path({str(late_release)!r});"
            "ready.write_text('ready',encoding='ascii');"
            "\nwhile not release.is_file(): time.sleep(.01)\n"
            f"Path({str(late_marker)!r}).write_text('late',encoding='ascii');"
            "print('late-spool',flush=True)"
        )
        late_code = f"""
import json, os, subprocess, sys
from pathlib import Path
p = subprocess.Popen([sys.executable, '-c', {descendant_code!r}])
path = Path({str(late_pids)!r})
temporary = path.with_name('.' + path.name + '.complete')
temporary.write_text(json.dumps([p.pid]), encoding='ascii')
os.replace(temporary, path)
Path({str(parent_done)!r}).write_text('done', encoding='ascii')
"""
        late_identities: dict[int, str] = {}
        late_receipt = None
        try:
            _start(
                ctl, root, "late-descendant", late_code,
                allowed_output_roots=[root / "work"], output_watch_roots=[root / "work"],
            )
            _wait_for_path(late_ready)
            _wait_for_path(parent_done)
            late_identities = _identities(ctl, _wait_for_pid_list(late_pids))
            early_receipt = root / "runs" / "late-descendant" / "receipt.json"
            early_deadline = time.monotonic() + 2.0
            while not early_receipt.is_file() and time.monotonic() < early_deadline:
                time.sleep(.01)
            terminal_before_release = early_receipt.is_file()
            late_release.write_text("release", encoding="ascii")
            try:
                late_receipt = _wait(ctl, root, "late-descendant")
            except Exception as exc:
                expected_failures.append(f"late descendant invalidated early receipt: {exc!r}")
        finally:
            late_release.write_text("release", encoding="ascii")
            _cancel_finally(ctl, root, "late-descendant")
            _terminate_identities(ctl, late_identities)
        if terminal_before_release:
            expected_failures.append("late descendant was still blocked when terminal receipt appeared")
        if late_receipt is None or late_receipt.get("state") != "succeeded":
            expected_failures.append("late descendant run did not finish with terminal success")
        elif b"late-spool" not in Path(late_receipt["stdout"]["path"]).read_bytes():
            expected_failures.append("late descendant spool bytes were absent from terminal evidence")
        if not late_marker.is_file():
            expected_failures.append("late descendant output was absent from the completed run")
        if _alive_identities(ctl, late_identities):
            expected_failures.append("late descendant identity survived run cleanup")
        run_dir = root / "runs" / "late-descendant"
        probe = root / "late-descendant-run"
        run_dir.rename(probe); probe.rename(run_dir)
        cases += 1

        # If the worker dies after spawning the product, recovery must close
        # the recorded owned tree before publishing terminal incomplete evidence.
        crash_pids = root / "work" / "worker-crash-pids.json"
        crash_code = f"""
import json, os, subprocess, sys, time
from pathlib import Path
p = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(60)'])
path = Path({str(crash_pids)!r})
temporary = path.with_name('.' + path.name + '.complete')
temporary.write_text(json.dumps([os.getpid(), p.pid]), encoding='ascii')
os.replace(temporary, path)
time.sleep(60)
"""
        crash_identities: dict[int, str] = {}
        crash_receipt = None
        alive_after_recovery: list[int] = []
        started = _start(
            ctl, root, "worker-crash-tree", crash_code,
            allowed_output_roots=[root / "work"], output_watch_roots=[root / "work"],
        )
        try:
            _wait_for_event(root, "worker-crash-tree", "child_spawned")
            crash_identities = _identities(ctl, _wait_for_pid_list(crash_pids))
            worker = started["worker"]
            assert ctl._process_token(worker["pid"]) == worker["process_token"]
            os.kill(worker["pid"], signal.SIGTERM)
            deadline = time.monotonic() + 10.0
            while ctl._process_token(worker["pid"]) == worker["process_token"] and time.monotonic() < deadline:
                time.sleep(.05)
            crash_receipt = ctl.recover_run(run_root=root / "runs", run_id="worker-crash-tree")
            alive_after_recovery = _alive_identities(ctl, crash_identities)
        finally:
            _cancel_finally(ctl, root, "worker-crash-tree")
            _terminate_identities(ctl, crash_identities)
        if crash_receipt is None or crash_receipt.get("state") != "evidence_incomplete":
            expected_failures.append("worker-crash recovery did not produce incomplete evidence")
        if alive_after_recovery:
            expected_failures.append(f"worker-crash recovery left live identities: {alive_after_recovery}")
        cases += 1

        # A worker that never completes readiness is still an owned detached
        # tree; start_run must terminate and wait for it before refusing.
        stalled_pids = root / "work" / "stalled-worker-pids.json"
        stalled_code = f"""
import json, os, subprocess, sys, time
from pathlib import Path
p = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(60)'])
path = Path({str(stalled_pids)!r})
temporary = path.with_name('.' + path.name + '.complete')
temporary.write_text(json.dumps([os.getpid(), p.pid]), encoding='ascii')
os.replace(temporary, path)
time.sleep(60)
"""
        stalled_identities: dict[int, str] = {}
        def spawn_stalled_worker(_paths, worker_env, worker_stdout, worker_stderr, *, detached):
            if os.name == "nt":
                job = ctl._WindowsJob()
                try:
                    with open(os.devnull, "rb") as devnull:
                        process = ctl._spawn_windows_job_process(
                            [sys.executable, "-c", stalled_code], cwd=Path.cwd(),
                            environment=dict(worker_env), stdin=devnull,
                            stdout=worker_stdout, stderr=worker_stderr, job=job,
                        )
                except Exception:
                    job.close()
                    raise
                return process, job
            kwargs = {
                "stdin": subprocess.DEVNULL, "stdout": worker_stdout,
                "stderr": worker_stderr, "close_fds": True, "env": dict(worker_env),
            }
            kwargs["start_new_session"] = detached
            return subprocess.Popen([sys.executable, "-c", stalled_code], **kwargs), None
        original_spawn = ctl._spawn_worker_process
        ctl._spawn_worker_process = spawn_stalled_worker
        stalled_outcomes: list[object] = []
        def launch_stalled():
            try:
                stalled_outcomes.append(_start(
                    ctl, root, "stalled-worker", "print('must-not-run')",
                ))
            except Exception as exc:
                stalled_outcomes.append(exc)
        stalled_thread = threading.Thread(target=launch_stalled)
        try:
            stalled_thread.start()
            stalled_identities = _identities(ctl, _wait_for_pid_list(stalled_pids))
            assert _alive_identities(ctl, stalled_identities) == list(stalled_identities)
            stalled_thread.join(timeout=15)
            alive_after_refusal = _alive_identities(ctl, stalled_identities)
        finally:
            ctl._spawn_worker_process = original_spawn
            _terminate_identities(ctl, stalled_identities)
            stalled_thread.join(timeout=10)
        if stalled_thread.is_alive():
            expected_failures.append("stalled-worker start thread did not return after cleanup")
        if len(stalled_outcomes) != 1 or getattr(
            stalled_outcomes[0], "code", None
        ) != "RELEASE-CONTROLLER-WORKER-START":
            expected_failures.append(f"stalled-worker refusal was not typed: {stalled_outcomes!r}")
        if alive_after_refusal:
            expected_failures.append(f"stalled-worker refusal left live identities: {alive_after_refusal}")
        cases += 1

        # Simultaneous cancellation writers must not share a PID-only temp
        # name, surface raw FileExistsError, or leave a stale temp behind.
        _start(ctl, root, "concurrent-cancel", "import time;time.sleep(60)")
        original_atomic = ctl._atomic
        cancel_publications = 0
        publication_guard = threading.Lock()
        def synchronized_cancel_atomic(path, raw):
            nonlocal cancel_publications
            if path.name == "cancel.request.json":
                with publication_guard:
                    cancel_publications += 1
                time.sleep(.1)
            return original_atomic(path, raw)
        ctl._atomic = synchronized_cancel_atomic
        outcomes: list[object] = []
        cancel_start = threading.Barrier(2)
        def competing_cancel():
            try:
                cancel_start.wait(timeout=10)
                outcomes.append(ctl.cancel_run(
                    run_root=root / "runs", run_id="concurrent-cancel", timeout_s=30,
                ))
            except Exception as exc:
                outcomes.append(exc)
        cancel_threads = [threading.Thread(target=competing_cancel) for _ in range(2)]
        try:
            for thread in cancel_threads: thread.start()
            for thread in cancel_threads: thread.join(timeout=40)
        finally:
            ctl._atomic = original_atomic
            _cancel_finally(ctl, root, "concurrent-cancel")
        if any(thread.is_alive() for thread in cancel_threads):
            expected_failures.append("concurrent cancel threads did not finish")
        if len(outcomes) != 2 or not all(
            isinstance(item, dict) and item.get("state") == "cancelled" for item in outcomes
        ):
            expected_failures.append(f"concurrent cancel surfaced a non-idempotent outcome: {outcomes!r}")
        if cancel_publications != 1:
            expected_failures.append(f"concurrent cancel published {cancel_publications} requests")
        cancel_temps = [
            *list((root / "runs" / "concurrent-cancel").glob("*.tmp")),
            *list((root / "runs" / "concurrent-cancel").glob(".*.tmp")),
        ]
        if cancel_temps:
            expected_failures.append(f"concurrent cancel left temp files: {cancel_temps!r}")
        cases += 1

        # Linux stat parsing must tolerate spaces and ')' inside comm.  Zombie
        # rows retain PPID ancestry for descendant closure, but callers keep
        # them non-live and non-signalable.
        if os.name != "nt":
            tail = ["S", "1", "17", "17", *map(str, range(4, 20))]
            parsed = ctl._parse_proc_stat("321 (odd ) process name) " + " ".join(tail))
            assert parsed is not None
            assert parsed["pid"] == 321 and parsed["ppid"] == 1
            assert parsed["pgrp"] == 17 and parsed["session"] == 17
            assert parsed["starttime"] == "19"
            tail[0] = "Z"
            zombie = ctl._parse_proc_stat("321 (odd ) process name) " + " ".join(tail))
            assert zombie is not None and zombie["state"] == "Z" and zombie["ppid"] == 1
            stat_reads = 0

            class FakeStat:
                def read_text(self, **_kwargs):
                    nonlocal stat_reads
                    stat_reads += 1
                    return "4242 (member) S 1 17 17 " + " ".join(map(str, range(4, 20)))

            class FakeEntry:
                name = "4242"

                def __truediv__(self, _name):
                    return FakeStat()

            class FakeProc:
                def iterdir(self):
                    return [FakeEntry()]

            class FakeBoot:
                @staticmethod
                def read_text(**_kwargs):
                    return "boot-one\n"

            original_path = ctl.Path
            original_token = ctl._process_token
            ctl.Path = lambda raw_path: (
                FakeProc() if os.fspath(raw_path) == "/proc" else (
                    FakeBoot() if os.fspath(raw_path) == "/proc/sys/kernel/random/boot_id"
                    else original_path(raw_path)
                )
            )
            ctl._process_token = lambda _pid: (_ for _ in ()).throw(
                AssertionError("second stat/token observation")
            )
            try:
                assert ctl._session_members(17) == {4242: "linux:boot-one:19"}
            finally:
                ctl.Path = original_path
                ctl._process_token = original_token
            assert stat_reads == 1
            cases += 1
        else:
            platform_skips += 1

        # A descendant that leaves the product session with setsid remains
        # owned by the subreaper-rooted PPID closure.  Terminal evidence waits
        # until that exact descendant exits.
        if os.name != "nt":
            escaped_pids = root / "work" / "live-escaped-session-pids.json"
            escaped_identities: dict[int, str] = {}
            escaped_child = (
                "import json,os,time;from pathlib import Path;"
                f"p=Path({str(escaped_pids)!r});t=p.with_name('.'+p.name+'.tmp');"
                "t.write_text(json.dumps([os.getpid()]),encoding='ascii');os.replace(t,p);"
                "time.sleep(2)"
            )
            escaping_product = (
                "import subprocess,sys;"
                f"subprocess.Popen([sys.executable,'-c',{escaped_child!r}],start_new_session=True)"
            )
            try:
                _start(
                    ctl, root, "live-setsid-escape", escaping_product,
                    allowed_output_roots=[root / "work"],
                )
                escaped_identities = _identities(
                    ctl, _wait_for_pid_list(escaped_pids),
                )
                time.sleep(.2)
                assert _alive_identities(ctl, escaped_identities)
                assert not (
                    root / "runs" / "live-setsid-escape" / "receipt.json"
                ).is_file()
                escaped_receipt = _wait(ctl, root, "live-setsid-escape")
                assert escaped_receipt["state"] == "succeeded"
            finally:
                _cancel_finally(ctl, root, "live-setsid-escape")
                _terminate_identities(ctl, escaped_identities)
            assert not _alive_identities(ctl, escaped_identities)
            cases += 1
        else:
            platform_skips += 1

        # Killing the exact supervisor after durable direct exit can never
        # authorize success or stream bindings, even if an escaped descendant
        # writes those inherited streams later.
        if os.name != "nt":
            loss_pids = root / "work" / "current-loss-pids.json"
            loss_release = root / "work" / "current-loss-release"
            loss_ack = root / "work" / "current-loss-ack"
            loss_descendants: dict[int, str] = {}
            loss_supervisor: dict[int, str] = {}
            loss_receipt = None
            loss_code = None
            late_child = f"""import json, os, time
from pathlib import Path
p = Path({str(loss_pids)!r})
t = p.with_name('.' + p.name + '.tmp')
t.write_text(json.dumps([os.getpid()]), encoding='ascii')
os.replace(t, p)
release = Path({str(loss_release)!r})
while not release.exists():
    time.sleep(.01)
os.write(1, b'late-current-stdout')
os.fsync(1)
os.write(2, b'late-current-stderr')
os.fsync(2)
Path({str(loss_ack)!r}).write_text('done', encoding='ascii')
time.sleep(60)
"""
            late_product = (
                "import subprocess,sys;"
                f"subprocess.Popen([sys.executable,'-c',{late_child!r}],start_new_session=True)"
            )
            try:
                _start(
                    ctl, root, "current-supervisor-loss", late_product,
                    allowed_output_roots=[root / "work"],
                )
                loss_descendants = _identities(ctl, _wait_for_pid_list(loss_pids))
                run_dir = root / "runs" / "current-supervisor-loss"
                _wait_for_path(run_dir / "direct-exit.json", timeout_s=20)
                journal = json.loads((run_dir / "journal.json").read_text(encoding="ascii"))
                spawned = next(
                    row for row in journal["events"] if row.get("event") == "child_spawned"
                )
                loss_supervisor = {spawned["child_pid"]: spawned["process_token"]}
                assert _terminate_identities(ctl, loss_supervisor) == set(
                    loss_supervisor.items()
                )
                try:
                    loss_receipt = _wait(ctl, root, "current-supervisor-loss")
                except Exception as exc:
                    loss_code = getattr(exc, "code", None)
                loss_release.write_text("release", encoding="ascii")
                _wait_for_path(loss_ack, timeout_s=10)
            finally:
                _cancel_finally(ctl, root, "current-supervisor-loss")
                _terminate_identities(ctl, {**loss_supervisor, **loss_descendants})
            if loss_receipt is not None:
                assert loss_receipt["state"] == "evidence_incomplete"
                assert loss_receipt["stdout"] is None and loss_receipt["stderr"] is None
            else:
                assert loss_code == "EVIDENCE_INCOMPLETE"
            cases += 1
        else:
            platform_skips += 1

        # True double-fork+setsid ownership delays terminal evidence until the
        # released late writer exits; the post-release mutation is then bound.
        if os.name != "nt":
            double_pids = root / "work" / "current-double-fork-pids.json"
            double_release = root / "work" / "current-double-fork-release"
            double_late = root / "work" / "current-double-fork-late.txt"
            double_identities: dict[int, str] = {}
            double_script = f"""import json, os, time
from pathlib import Path
first = os.fork()
if first == 0:
    second = os.fork()
    if second == 0:
        os.setsid()
        p = Path({str(double_pids)!r})
        t = p.with_name('.' + p.name + '.tmp')
        t.write_text(json.dumps([os.getpid()]), encoding='ascii')
        os.replace(t, p)
        release = Path({str(double_release)!r})
        while not release.exists():
            time.sleep(.01)
        Path({str(double_late)!r}).write_text('late', encoding='ascii')
        os._exit(0)
    os._exit(0)
os.waitpid(first, 0)
"""
            try:
                _start(
                    ctl, root, "current-double-fork", f"exec({double_script!r})",
                    allowed_output_roots=[root / "work"],
                )
                double_identities = _identities(ctl, _wait_for_pid_list(double_pids))
                time.sleep(.2)
                assert not (root / "runs" / "current-double-fork" / "receipt.json").exists()
                assert not double_late.exists()
                double_release.write_text("release", encoding="ascii")
                _wait_for_path(double_late)
                double_receipt = _wait(ctl, root, "current-double-fork")
                assert double_receipt["state"] == "succeeded"
            finally:
                _cancel_finally(ctl, root, "current-double-fork")
                _terminate_identities(ctl, double_identities)
            assert not _alive_identities(ctl, double_identities)
            cases += 1
        else:
            platform_skips += 1

        # Descendants forked by a SIGTERM handler are found by dynamic rescans
        # and quiesced before cooperative cancellation becomes terminal.
        if os.name != "nt":
            term_ready = root / "work" / "current-term-ready.txt"
            term_pids = root / "work" / "current-term-pids.json"
            term_identities: dict[int, str] = {}
            term_outcome: dict[str, object] = {}
            term_child = (
                "import json,os,signal,time;from pathlib import Path;"
                "signal.signal(signal.SIGTERM,signal.SIG_IGN);"
                f"p=Path({str(term_pids)!r});t=p.with_name('.'+p.name+'.tmp');"
                "t.write_text(json.dumps([os.getpid()]),encoding='ascii');os.replace(t,p);"
                "time.sleep(60)"
            )
            term_product = f"""import signal, subprocess, sys, time
from pathlib import Path
def handle(_signum, _frame):
    subprocess.Popen([sys.executable, '-c', {term_child!r}], start_new_session=True)
signal.signal(signal.SIGTERM, handle)
Path({str(term_ready)!r}).write_text('ready', encoding='ascii')
while True:
    time.sleep(.05)
"""
            try:
                _start(
                    ctl, root, "current-term-fork", f"exec({term_product!r})",
                    allowed_output_roots=[root / "work"],
                )
                _wait_for_path(term_ready)

                def cancel_term_fork() -> None:
                    try:
                        term_outcome["receipt"] = ctl.cancel_run(
                            run_root=root / "runs", run_id="current-term-fork", timeout_s=30,
                        )
                    except Exception as exc:
                        term_outcome["error"] = exc

                cancel_thread = threading.Thread(target=cancel_term_fork)
                cancel_thread.start()
                term_identities = _identities(
                    ctl, _wait_for_pid_list(term_pids, timeout_s=5),
                )
                cancel_thread.join(timeout=40)
                assert not cancel_thread.is_alive() and "error" not in term_outcome
                assert term_outcome["receipt"]["state"] == "cancelled"
            finally:
                _cancel_finally(ctl, root, "current-term-fork")
                _terminate_identities(ctl, term_identities)
            assert not _alive_identities(ctl, term_identities)
            cases += 1
        else:
            platform_skips += 1

        # A reused POSIX PID/PGID may never be signalled after its recorded
        # creation token changes.
        if os.name != "nt":
            original_token = ctl._process_token
            original_members = ctl._session_members
            original_signal = ctl._signal_session
            signalled: list[int] = []
            ctl._process_token = lambda _pid: "new-token"
            ctl._session_members = lambda _sid, **_kwargs: {44444: "new-token"}
            ctl._signal_session = lambda _sid, rows, _signal: signalled.extend(rows)
            try:
                _expect("RELEASE-CONTROLLER-PROCESS", lambda: ctl._terminate_posix_session(
                    44444, leader_pid=44444, leader_token="old-token", timeout_s=.1,
                ))
            finally:
                ctl._process_token = original_token
                ctl._session_members = original_members
                ctl._signal_session = original_signal
            assert not signalled
            cases += 1
        else:
            platform_skips += 1

        # The POSIX session leader is blocked before product execution.  A
        # worker crash before its durable child_spawned event closes the gate;
        # the product sentinel must never run.
        if os.name != "nt":
            prejournal_sentinel = root / "work" / "prejournal-sentinel.txt"
            prejournal_pids = root / "work" / "prejournal-pids.json"
            prejournal_identities: dict[int, str] = {}
            receipt = None
            prejournal_code = (
                "import json,os,time;from pathlib import Path;"
                f"p=Path({str(prejournal_pids)!r});t=p.with_name('.'+p.name+'.tmp');"
                "t.write_text(json.dumps([os.getpid()]),encoding='ascii');os.replace(t,p);"
                f"Path({str(prejournal_sentinel)!r}).write_text('ran');time.sleep(60)"
            )
            try:
                started = _start(
                    ctl, root, "prejournal-crash", prejournal_code,
                    _test_fault="crash_after_supervisor_spawn_before_journal",
                    allowed_output_roots=[root / "work"],
                )
                _capture_identity(ctl, prejournal_identities, started.get("worker", {}).get("pid"))
                receipt = _wait(ctl, root, "prejournal-crash")
            finally:
                if prejournal_pids.is_file():
                    try:
                        handed_off = _wait_for_pid_list(prejournal_pids, timeout_s=1)
                    except AssertionError:
                        handed_off = []
                    for pid in handed_off:
                        _capture_identity(ctl, prejournal_identities, pid)
                _capture_run_identities(ctl, root, "prejournal-crash", prejournal_identities)
                _cancel_finally(ctl, root, "prejournal-crash")
                _terminate_identities(ctl, prejournal_identities)
            assert not _alive_identities(ctl, prejournal_identities)
            assert receipt is not None
            assert receipt["state"] == "evidence_incomplete"
            assert not prejournal_sentinel.exists()
            assert "child_spawned" not in _event_names(root, "prejournal-crash")
            cases += 1
        else:
            platform_skips += 1

        # Parent-side readiness refusal happens after a separately-sessioned
        # product tree is live.  Cleanup must cover both worker and product.
        if os.name != "nt":
            refusal_pids = root / "work" / "parent-refusal-pids.json"
            refusal_code = f"""
import json, os, subprocess, sys, time
from pathlib import Path
p = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(60)'])
Path({str(refusal_pids)!r}).write_text(json.dumps([os.getpid(), p.pid]), encoding='ascii')
time.sleep(60)
"""
            refusal_identities: dict[int, str] = {}
            alive_after_refusal: list[int] = []
            original_read = ctl._read
            def invalid_owner(path):
                value = original_read(path)
                if path.name == "owner.json":
                    pids = _wait_for_pid_list(refusal_pids)
                    refusal_identities.update(_identities(ctl, pids))
                    value = dict(value); value["pid"] += 1000000
                return value
            ctl._read = invalid_owner
            try:
                _expect("RELEASE-CONTROLLER-WORKER-START", lambda: _start(
                    ctl, root, "parent-refusal", refusal_code,
                    allowed_output_roots=[root / "work"],
                ))
                alive_after_refusal = _alive_identities(ctl, refusal_identities)
            finally:
                ctl._read = original_read
                _terminate_identities(ctl, refusal_identities)
            assert not alive_after_refusal
            cases += 1
        else:
            platform_skips += 1

        # Cancellation is not terminal until a stubborn POSIX session is
        # empty after the SIGKILL path.
        if os.name != "nt":
            stubborn_pids = root / "work" / "stubborn-session-pids.json"
            stubborn_code = f"""
import json, os, signal, subprocess, sys, time
from pathlib import Path
signal.signal(signal.SIGTERM, signal.SIG_IGN)
p = subprocess.Popen([sys.executable, '-c', 'import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(60)'])
target = Path({str(stubborn_pids)!r})
temporary = target.with_name('.' + target.name + '.tmp')
temporary.write_text(json.dumps([os.getpid(), p.pid]), encoding='ascii')
os.replace(temporary, target)
time.sleep(60)
"""
            stubborn_identities: dict[int, str] = {}
            receipt = None
            child_event = None
            try:
                started = _start(
                    ctl, root, "post-kill-quiescence", stubborn_code,
                    allowed_output_roots=[root / "work"],
                )
                _capture_identity(ctl, stubborn_identities, started.get("worker", {}).get("pid"))
                for pid in _wait_for_pid_list(stubborn_pids):
                    _capture_identity(ctl, stubborn_identities, pid)
                child_event = next(
                    row for row in json.loads(
                        (root / "runs" / "post-kill-quiescence" / "journal.json").read_text(encoding="ascii")
                    )["events"] if row["event"] == "child_spawned"
                )
                receipt = ctl.cancel_run(
                    run_root=root / "runs", run_id="post-kill-quiescence", timeout_s=30,
                )
            finally:
                _capture_run_identities(ctl, root, "post-kill-quiescence", stubborn_identities)
                _cancel_finally(ctl, root, "post-kill-quiescence")
                _terminate_identities(ctl, stubborn_identities)
            assert not _alive_identities(ctl, stubborn_identities)
            assert receipt is not None and child_event is not None
            assert receipt["state"] == "cancelled"
            assert not ctl._session_members(child_event["process_group"])
            cases += 1
        else:
            platform_skips += 1

        # True separate frontends must converge on one cancellation request
        # and one final receipt without raw publication or RMW failures.
        cancel_command = [
            sys.executable, str(MODULE), "cancel", "--run-root", str(root / "runs"),
            "--run-id", "multiprocess-cancel", "--timeout", "30",
        ]
        cancelers: list[subprocess.Popen[bytes]] = []
        cancel_results: list[tuple[bytes, bytes]] = []
        cancel_run_identities: dict[int, str] = {}
        cancel_frontend_identities: dict[int, str] = {}
        cancel_outputs: list[dict[str, object]] = []
        cancel_disk_receipt: dict[str, object] | None = None
        try:
            started = _start(ctl, root, "multiprocess-cancel", "import time;time.sleep(60)")
            _capture_identity(ctl, cancel_run_identities, started.get("worker", {}).get("pid"))
            _capture_run_identities(ctl, root, "multiprocess-cancel", cancel_run_identities)
            cancelers = [subprocess.Popen(
                cancel_command, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            ) for _ in range(2)]
            for process in cancelers:
                _capture_identity(ctl, cancel_frontend_identities, process.pid)
            cancel_results = [process.communicate(timeout=40) for process in cancelers]
            cancel_outputs = [json.loads(stdout) for stdout, _ in cancel_results]
            cancel_disk_receipt = json.loads(
                (root / "runs" / "multiprocess-cancel" / "receipt.json").read_text(encoding="ascii")
            )
        finally:
            _terminate_identities(ctl, cancel_frontend_identities)
            _reap_frontends(cancelers)
            _capture_run_identities(ctl, root, "multiprocess-cancel", cancel_run_identities)
            _cancel_finally(ctl, root, "multiprocess-cancel")
            _terminate_identities(ctl, cancel_run_identities)
        assert not _alive_identities(ctl, cancel_frontend_identities)
        assert not _alive_identities(ctl, cancel_run_identities)
        assert all(process.returncode == 0 for process in cancelers), cancel_results
        assert len(cancel_outputs) == 2 and cancel_disk_receipt is not None
        assert cancel_outputs[0] == cancel_outputs[1] == cancel_disk_receipt
        assert cancel_disk_receipt["state"] == "cancelled"
        cases += 1

        # Two independent recovery frontends serialize journal/receipt
        # finalization and both return the same immutable terminal receipt.
        recover_command = [
            sys.executable, str(MODULE), "recover", "--run-root", str(root / "runs"),
            "--run-id", "multiprocess-recover",
        ]
        recoverers: list[subprocess.Popen[bytes]] = []
        recover_results: list[tuple[bytes, bytes]] = []
        recover_run_identities: dict[int, str] = {}
        recover_frontend_identities: dict[int, str] = {}
        recovered: list[dict[str, object]] = []
        recover_disk_receipt: dict[str, object] | None = None
        try:
            started = _start(
                ctl, root, "multiprocess-recover", "print('recover')",
                _test_fault="crash_after_exit",
            )
            _capture_identity(ctl, recover_run_identities, started.get("worker", {}).get("pid"))
            owner_path = root / "runs" / "multiprocess-recover" / "owner.json"
            _wait_for_path(owner_path)
            owner = json.loads(owner_path.read_text(encoding="ascii"))
            _capture_identity(ctl, recover_run_identities, owner.get("pid"))
            deadline = time.monotonic() + 20
            while ctl._process_token(owner["pid"]) == owner["process_token"] and time.monotonic() < deadline:
                time.sleep(.01)
            recoverers = [subprocess.Popen(
                recover_command, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            ) for _ in range(2)]
            for process in recoverers:
                _capture_identity(ctl, recover_frontend_identities, process.pid)
            recover_results = [process.communicate(timeout=40) for process in recoverers]
            recovered = [json.loads(stdout) for stdout, _ in recover_results]
            recover_disk_receipt = json.loads(
                (root / "runs" / "multiprocess-recover" / "receipt.json").read_text(encoding="ascii")
            )
        finally:
            _terminate_identities(ctl, recover_frontend_identities)
            _reap_frontends(recoverers)
            _capture_run_identities(ctl, root, "multiprocess-recover", recover_run_identities)
            _cancel_finally(ctl, root, "multiprocess-recover")
            _terminate_identities(ctl, recover_run_identities)
        assert not _alive_identities(ctl, recover_frontend_identities)
        assert not _alive_identities(ctl, recover_run_identities)
        assert all(process.returncode == 0 for process in recoverers), recover_results
        assert len(recovered) == 2 and recover_disk_receipt is not None
        assert recovered[0] == recovered[1] == recover_disk_receipt
        assert recovered[0]["state"] == "succeeded" and recovered[0]["recovered"] is True
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
        _expect("RELEASE-CONTROLLER-OUTPUT-TOPOLOGY", lambda: ctl.start_run(
            run_root=root / "runs", run_id="output-reparse-root",
            argv=[sys.executable, "-c", "raise AssertionError('child ran')"],
            cwd=reparse_link, output_watch_roots=[reparse_link],
        ))
        assert not escaped.exists()
        cases += 1

        # Complete input-root evidence is bound into both intent and receipt
        # and is revalidated before the product child starts.
        input_root = root / "input-root"; input_root.mkdir()
        (input_root / "nested").mkdir(); (input_root / "nested" / "bound.txt").write_text("before")
        input_sentinel = root / "work" / "input-root-child.txt"
        preflight_gate = root / "runs" / "input-root-drift" / ".test-preflight-gate"
        try:
            _start(
                ctl, root, "input-root-drift",
                "from pathlib import Path;" + f"Path({str(input_sentinel)!r}).write_text('ran')",
                input_roots=[input_root], allowed_output_roots=[root / "work"],
                _test_fault="pause_before_input_drift",
            )
            _wait_for_event(root, "input-root-drift", "test_preflight_paused")
            (input_root / "nested" / "bound.txt").write_text("after")
        finally:
            if preflight_gate.parent.is_dir():
                preflight_gate.write_text("continue", encoding="ascii")
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

        # A protected sibling may be observed only when it is the exact root
        # of a worktree registered to the controller's own Git common dir.
        # This is observation authority, never allowed-output authority.
        registered = root / "registered-worktree"; registered.mkdir()
        registered_subdir = registered / "nested"; registered_subdir.mkdir()
        unregistered = root / "unregistered-worktree"; unregistered.mkdir()
        common = registered / ".git"; common.mkdir()
        other_common = root / "other.git"; other_common.mkdir()
        original_roots = ctl.registered_worktree_roots
        original_common = ctl.git_common_dir
        ctl.registered_worktree_roots = lambda _repo: [registered]
        ctl.git_common_dir = lambda repo: (
            common if Path(repo).resolve() in {ctl.ROOT.resolve(), registered.resolve()}
            else other_common
        )
        try:
            assert ctl._is_registered_same_repository_worktree(registered)
            assert not ctl._is_registered_same_repository_worktree(registered_subdir)
            ctl.git_common_dir = lambda repo: (
                common if Path(repo).resolve() == ctl.ROOT.resolve() else other_common
            )
            assert not ctl._is_registered_same_repository_worktree(registered)
            ctl.registered_worktree_roots = lambda _repo: (_ for _ in ()).throw(
                OSError("synthetic worktree registry failure")
            )
            _expect(
                "RELEASE-CONTROLLER-OUTPUT-TOPOLOGY",
                lambda: ctl._is_registered_same_repository_worktree(registered),
            )
        finally:
            ctl.registered_worktree_roots = original_roots
            ctl.git_common_dir = original_common

        original_assert_writable = ctl.assert_writable
        original_registered = ctl._is_registered_same_repository_worktree
        misrouted_ignored = registered / "outputs" / "co-author-harness" / "hidden.txt"
        misrouted_ignored.parent.mkdir(parents=True)
        misrouted_ignored.write_text("misrouted")
        protected = {
            registered.resolve(), registered_subdir.resolve(), unregistered.resolve(),
        }
        def synthetic_destination_guard(path, purpose="write"):
            resolved = Path(path).resolve()
            if resolved == misrouted_ignored.resolve():
                raise ctl.DestinationRefused("DEST-MISROUTED", "synthetic misrouted file")
            if (
                resolved in protected
                or registered.resolve() in resolved.parents
            ):
                raise ctl.DestinationRefused("DEST-PROTECTED", "synthetic protected root")
            return original_assert_writable(path, purpose=purpose)
        ctl.assert_writable = synthetic_destination_guard
        ctl._is_registered_same_repository_worktree = (
            lambda path: Path(path).resolve() == registered.resolve()
        )
        ctl.git_common_dir = lambda _repo: common
        try:
            ctl._validate_existing_watch_root(registered)
            _start(
                ctl, root, "registered-watch", "print('observed')",
                cwd=registered, output_watch_roots=[root / "work", registered],
            )
            assert _wait(ctl, root, "registered-watch")["state"] == "succeeded"
            _expect("DEST-PROTECTED", lambda: _start(
                ctl, root, "registered-allowed", "raise AssertionError('child ran')",
                cwd=registered, allowed_output_roots=[registered],
                output_watch_roots=[registered],
            ))
            _expect("RELEASE-CONTROLLER-OUTPUT-TOPOLOGY", lambda: _start(
                ctl, root, "unregistered-watch", "raise AssertionError('child ran')",
                cwd=unregistered, output_watch_roots=[unregistered],
            ))
            _expect("RELEASE-CONTROLLER-OUTPUT-TOPOLOGY", lambda: _start(
                ctl, root, "registered-subdir-watch", "raise AssertionError('child ran')",
                cwd=registered_subdir, output_watch_roots=[registered_subdir],
            ))
            arbitrary_ignored = registered / "arbitrary.txt"
            arbitrary_ignored.write_text("protected")
            shared_lock = common / "coauthor-fixture-runner.lock"
            shared_lock.write_text("stable")
            _expect("RELEASE-CONTROLLER-OUTPUT-TOPOLOGY", lambda:
                ctl._validate_ignored_output_path(arbitrary_ignored, [registered])
            )
            _expect("DEST-MISROUTED", lambda:
                ctl._validate_ignored_output_path(misrouted_ignored, [registered])
            )
            ctl._validate_ignored_output_path(shared_lock, [registered])
            ctl.assert_writable = lambda _path, purpose="write": (_ for _ in ()).throw(
                ctl.DestinationRefused("DEST-UNGOVERNED", "synthetic ungoverned root")
            )
            _expect(
                "DEST-UNGOVERNED",
                lambda: ctl._validate_existing_watch_root(registered),
            )
            ctl.assert_writable = synthetic_destination_guard
            ctl._is_registered_same_repository_worktree = lambda _path: False
            _expect(
                "RELEASE-CONTROLLER-OUTPUT-TOPOLOGY",
                lambda: ctl._validate_existing_watch_root(registered),
            )
            ctl._is_registered_same_repository_worktree = (
                lambda path: Path(path).resolve() == registered.resolve()
            )
            ctl._is_registered_same_repository_worktree = lambda _path: (_ for _ in ()).throw(
                ctl.ControllerRefusal(
                    "RELEASE-CONTROLLER-OUTPUT-TOPOLOGY",
                    "synthetic registry discovery failure",
                )
            )
            _expect("RELEASE-CONTROLLER-OUTPUT-TOPOLOGY", lambda: _start(
                ctl, root, "registered-discovery-failure",
                "raise AssertionError('child ran')", cwd=registered,
                output_watch_roots=[registered],
            ))
            ctl._is_registered_same_repository_worktree = (
                lambda path: Path(path).resolve() == registered.resolve()
            )
            for run_id, target in (
                ("multi-watch-primary", root / "work" / "forbidden.txt"),
                ("multi-watch-registered", registered / "forbidden.txt"),
            ):
                _start(
                    ctl, root, run_id,
                    f"from pathlib import Path;Path({str(target)!r}).write_text('bad')",
                    cwd=registered, output_watch_roots=[root / "work", registered],
                )
                receipt = _wait(ctl, root, run_id)
                assert receipt["state"] == "refused"
                assert receipt["diagnostic"]["code"] == "RELEASE-CONTROLLER-OUTPUT-SCOPE"
                assert str(target.resolve()) in receipt["diagnostic"]["paths"]

            worker_source = inspect.getsource(ctl._worker)
            spawn_at = worker_source.index("child, product_job, control_fd = _spawn_product_process")
            assert worker_source.rfind(
                '_validate_existing_watch_roots(intent["output_watch_roots"])', 0, spawn_at,
            ) > worker_source.rfind("controlled_environment(", 0, spawn_at)

            spawn_watch = root / "spawn-watch"; spawn_watch.mkdir()
            spawn_target = root / "spawn-watch-target"
            spawn_sentinel = root / "spawn-child-ran.txt"
            _start(
                ctl, root, "watch-authority-at-spawn",
                f"from pathlib import Path;Path({str(spawn_sentinel)!r}).write_text('ran')",
                cwd=spawn_watch, output_watch_roots=[spawn_watch],
                _test_fault="pause_before_watch_spawn",
            )
            _wait_for_event(root, "watch-authority-at-spawn", "test_watch_spawn_paused")
            gate = root / "runs" / "watch-authority-at-spawn" / ".test-preflight-gate"
            try:
                spawn_watch.rename(spawn_target)
                if os.name == "nt":
                    linked = subprocess.run(
                        ["cmd", "/c", "mklink", "/J", str(spawn_watch), str(spawn_target)],
                        stdin=subprocess.DEVNULL, capture_output=True, check=False,
                    )
                    assert linked.returncode == 0, linked.stderr
                else:
                    spawn_watch.symlink_to(spawn_target, target_is_directory=True)
            finally:
                gate.write_text("continue", encoding="ascii")
            receipt = _wait(ctl, root, "watch-authority-at-spawn")
            assert receipt["state"] == "refused"
            assert receipt["diagnostic"]["code"] == "RELEASE-CONTROLLER-OUTPUT-TOPOLOGY"
            assert "watch_root_authority_refused_at_spawn" in _event_names(
                root, "watch-authority-at-spawn",
            )
            assert not spawn_sentinel.exists()

            bracket_root = root / "work"
            bracket_ignored = bracket_root / "bracket-ignored.txt"
            bracket_ignored.write_text("stable")
            bracket_intent = {
                "output_watch_roots": [str(bracket_root.resolve())],
                "ignored_output_paths": [str(bracket_ignored.resolve())],
                "output_preimage": ctl._inventory(
                    [bracket_root], root / "not-a-run",
                    ignored_paths=[bracket_ignored],
                ),
            }
            original_validate_watch_roots = ctl._validate_existing_watch_roots
            validation_calls = 0
            def fail_second_validation(_paths):
                nonlocal validation_calls
                validation_calls += 1
                if validation_calls == 2:
                    raise ctl.ControllerRefusal(
                        "RELEASE-CONTROLLER-OUTPUT-TOPOLOGY",
                        "synthetic postimage authority loss",
                    )
            ctl._validate_existing_watch_roots = fail_second_validation
            try:
                _expect(
                    "RELEASE-CONTROLLER-OUTPUT-TOPOLOGY",
                    lambda: ctl._changed_outputs(bracket_intent, root / "not-a-run"),
                )
                assert validation_calls == 2
            finally:
                ctl._validate_existing_watch_roots = original_validate_watch_roots
            original_validate_ignored = ctl._validate_ignored_output_path
            ignored_validation_calls = 0
            def fail_second_ignored_validation(_path, _roots):
                nonlocal ignored_validation_calls
                ignored_validation_calls += 1
                if ignored_validation_calls == 2:
                    raise ctl.ControllerRefusal(
                        "RELEASE-CONTROLLER-OUTPUT-TOPOLOGY",
                        "synthetic ignored-output identity loss",
                    )
            ctl._validate_ignored_output_path = fail_second_ignored_validation
            try:
                _expect(
                    "RELEASE-CONTROLLER-OUTPUT-TOPOLOGY",
                    lambda: ctl._changed_outputs(bracket_intent, root / "not-a-run"),
                )
                assert ignored_validation_calls == 2
            finally:
                ctl._validate_ignored_output_path = original_validate_ignored
        finally:
            ctl.assert_writable = original_assert_writable
            ctl._is_registered_same_repository_worktree = original_registered
            ctl.git_common_dir = original_common
        cases += 1

        # A launcher/spawn failure before owner.json exists must still recover
        # to typed terminal incomplete evidence, never an unrecoverable schema
        # exception or product rerun.
        original_spawn = ctl._spawn_worker_process
        def refuse_worker_spawn(*_args, **_kwargs):
            raise OSError("synthetic worker spawn refusal")
        ctl._spawn_worker_process = refuse_worker_spawn
        try:
            try:
                _start(ctl, root, "pre-owner-failure", "print('no')")
            except OSError:
                pass
            else:
                raise AssertionError("worker spawn fault did not surface")
        finally:
            ctl._spawn_worker_process = original_spawn
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
        bash = Path(_bash())
        assert bash.is_file(), bash
        facade_root = root / "facade-runs"
        # Fresh identity prevents old source-side output from masking drift.
        facade_run_id = "ambient-marker-" + root.name.rsplit("-", 1)[-1]
        source_evidence = ROOT / "releases" / "verification" / facade_run_id
        assert not source_evidence.exists()
        facade_env = {
            key: value for key, value in os.environ.items()
            if not key.upper().startswith("PYTHON")
        }
        facade_env.update({
            "COAUTHOR_RELEASE_GATE_CONTROLLED_CHILD": "1",
            "COAUTHOR_RELEASE_CONTROLLER_ROOT": str(facade_root),
            "COAUTHOR_RELEASE_RUN_ID": facade_run_id,
        })
        bytecode_before = _package_bytecode_inventory()
        facade_process = subprocess.Popen(
            [str(bash), str(gate), "--help"], env=facade_env,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        facade_frontend: dict[int, str] = {}
        facade_owned: dict[int, str] = {}
        _capture_identity(ctl, facade_frontend, facade_process.pid)
        facade_output: tuple[bytes, bytes] | None = None
        try:
            # WSL/NTFS inventories the complete checkout through p9; retain a
            # bounded slow-host envelope without abandoning the durable worker.
            facade_output = facade_process.communicate(timeout=300)
        finally:
            _terminate_identities(ctl, facade_frontend)
            _reap_frontends([facade_process])
            _capture_run_identities(
                ctl, root, facade_run_id, facade_owned, run_root=facade_root,
            )
            if (facade_root / facade_run_id / "intent.json").is_file():
                _cancel_finally(
                    ctl, root, facade_run_id, run_root=facade_root,
                )
            _capture_run_identities(
                ctl, root, facade_run_id, facade_owned, run_root=facade_root,
            )
            _terminate_identities(ctl, facade_owned)
        assert not _alive_identities(ctl, facade_frontend)
        assert not _alive_identities(ctl, facade_owned)
        assert facade_output is not None
        assert facade_process.returncode == 0, facade_output[1]
        facade_receipt_path = facade_root / facade_run_id / "receipt.json"
        assert facade_receipt_path.is_file()
        facade_receipt = ctl.status_run(
            run_root=facade_root, run_id=facade_run_id,
        )
        assert facade_receipt["state"] == "succeeded"
        assert facade_receipt["diagnostic"] is None
        assert not source_evidence.exists()
        assert (Path(str(facade_root) + "-products") / facade_run_id / "verification").is_dir()
        cases += 1

        direct_marker = subprocess.run(
            [str(bash), str(gate), "--coauthor-controller-child", "--help"],
            env=facade_env | {
                "COAUTHOR_RELEASE_RUN_ID": "must-not-exist",
                "COAUTHOR_RELEASE_CONTROLLER_ATTESTATION_RUN_DIR": str(
                    root / "missing-attestation-run"
                ),
                "COAUTHOR_RELEASE_CONTROLLER_ATTESTATION_TOKEN": "0" * 64,
            },
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
        assert _package_bytecode_inventory() == bytecode_before
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
        "partial_pid_handoff_cleanup_finally",
        "owned_process_tree_quiescent_before_terminal",
        "worker_crash_owned_tree_recovered",
        "worker_readiness_failure_tree_cleaned",
        "concurrent_cancel_atomic_publication",
        "posix_stat_identity_robust",
        "posix_reused_session_refused",
        "posix_prejournal_gate_fail_closed",
        "posix_readiness_refusal_tree_cleaned",
        "posix_post_kill_session_quiescent",
        "posix_subreaper_descendant_closure",
        "posix_single_snapshot_identity",
        "posix_supervisor_result_authority",
        "posix_double_fork_setsid_quiescence",
        "posix_term_spawn_dynamic_rescan",
        "windows_process_observation_typed",
        "windows_detached_worker_job_escape_proven",
        "windows_concrete_executable_identity_enforced",
        "windows_created_image_identity_enforced",
        "run_lock_fail_closed",
        "run_lock_initialization_fail_closed",
        "multiprocess_cancel_idempotent",
        "multiprocess_recovery_serialized",
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
        "registered_worktree_observation_fail_closed",
        "pre_owner_failure_is_evidence_incomplete",
        "direct_release_gate_child_marker_refused",
        "five_plane_production_facade",
    }
    missing_contracts = sorted(required_contracts - set(ctl.REGRESSION_CONTRACT))
    if missing_contracts:
        expected_failures.append(f"production regression contract is missing: {missing_contracts!r}")
    expected_case_count = 61 if os.name != "nt" else 63
    expected_skip_count = 0 if os.name != "nt" else 9
    assert cases == expected_case_count, (cases, expected_case_count)
    assert platform_skips == expected_skip_count, (platform_skips, expected_skip_count)
    assert not expected_failures, "expected red regressions:\n- " + "\n- ".join(expected_failures)
    print(
        "release_qualification_controller_smoketest: PASS "
        f"({cases} behavioral cases; {platform_skips} platform skips; "
        f"posix_evidence={'executed' if os.name != 'nt' else 'not-run'}; "
        f"mode={'fixture-owner' if _FIXTURE_OWNER_MODE else 'bare-host'})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
