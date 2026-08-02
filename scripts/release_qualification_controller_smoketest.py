#!/usr/bin/env python3
"""Behavioral direct-Python regressions for the durable release controller."""

from __future__ import annotations

import importlib.util
import inspect
import hashlib
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


def _identities(ctl, pids: list[int]) -> dict[int, str]:
    rows = {pid: ctl._process_token(pid) for pid in pids}
    assert all(isinstance(token, str) and token for token in rows.values()), rows
    return rows


def _alive_identities(ctl, identities: dict[int, str]) -> list[int]:
    return [pid for pid, token in identities.items() if ctl._process_token(pid) == token]


def _terminate_identities(ctl, identities: dict[int, str]) -> set[tuple[int, str]]:
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
                assert kernel32.TerminateProcess(handle, 1223), f"TerminateProcess failed for {pid}"
                signalled.add((pid, identities[pid]))
                retained.append((int(handle), pid))
                keep_handle = True
            finally:
                if not keep_handle:
                    assert kernel32.CloseHandle(handle), f"CloseHandle failed for {pid}"
        try:
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
    if os.environ.get("COAUTHOR_CONTROLLER_FOURTH_REOPENED_RED") == "1":
        return _fourth_reopened_red()
    if os.environ.get("COAUTHOR_CONTROLLER_THIRD_REOPENED_RED") == "1":
        return _third_reopened_red()
    if os.environ.get("COAUTHOR_CONTROLLER_REOPENED_RED") == "1":
        return _reopened_red_against_committed()
    env = _load(ENVIRONMENT, "qualification_environment")
    ctl = _load(MODULE, "release_qualification_controller")
    cases = 0
    platform_skips = 0
    expected_failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="release-controller-smoke-") as raw:
        root = Path(raw)

        observation_rows, observation_failures = _windows_observation_contract(ctl)
        assert observation_rows == 8 and not observation_failures, observation_failures
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

        # Deliberately publish an empty PID handoff before atomically replacing
        # it with complete JSON.  File existence alone is not readiness.
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
                receipt = ctl.cancel_run(
                    run_root=root / "runs", run_id=run_id, timeout_s=30,
                )
            finally:
                _cancel_finally(ctl, root, run_id)
                _terminate_identities(ctl, owned_identities)
            assert receipt is not None and receipt["state"] == "cancelled"
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
                ctl, root, "ambient-marker", facade_owned, run_root=facade_root,
            )
            if (facade_root / "ambient-marker" / "intent.json").is_file():
                _cancel_finally(
                    ctl, root, "ambient-marker", run_root=facade_root,
                )
            _capture_run_identities(
                ctl, root, "ambient-marker", facade_owned, run_root=facade_root,
            )
            _terminate_identities(ctl, facade_owned)
        assert not _alive_identities(ctl, facade_frontend)
        assert not _alive_identities(ctl, facade_owned)
        assert facade_output is not None
        assert facade_process.returncode == 0, facade_output[1]
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
        "windows_process_observation_typed",
        "run_lock_fail_closed",
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
        "pre_owner_failure_is_evidence_incomplete",
        "direct_release_gate_child_marker_refused",
        "five_plane_production_facade",
    }
    missing_contracts = sorted(required_contracts - set(ctl.REGRESSION_CONTRACT))
    if missing_contracts:
        expected_failures.append(f"production regression contract is missing: {missing_contracts!r}")
    expected_case_count = 46 if os.name != "nt" else 40
    expected_skip_count = 0 if os.name != "nt" else 6
    assert cases == expected_case_count, (cases, expected_case_count)
    assert platform_skips == expected_skip_count, (platform_skips, expected_skip_count)
    assert not expected_failures, "expected red regressions:\n- " + "\n- ".join(expected_failures)
    print(
        "release_qualification_controller_smoketest: PASS "
        f"({cases} behavioral cases; {platform_skips} platform skips; "
        f"posix_evidence={'executed' if os.name != 'nt' else 'not-run'})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
