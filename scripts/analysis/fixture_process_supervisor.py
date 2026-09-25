#!/usr/bin/env python3
"""Cross-platform, fail-closed ownership for one fixture-suite process tree.

The fixture runner's evidence is suite-process evidence, so a direct suite
exit is not sufficient while any suite descendant remains live.  Windows uses
a private Job assigned while the direct process is suspended.  Linux/WSL uses
a dedicated child-subreaper process with a control pipe so runner loss also
tears down the owned tree.  Other platforms refuse rather than falling back to
PID- or process-group-only cleanup.
"""

from __future__ import annotations

import base64
import json
import math
import os
import re
import signal
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import uuid
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping, NamedTuple, Sequence


class FixtureProcessResult(NamedTuple):
    returncode: int
    stdout: bytes
    stderr: bytes


class _PidfdIdentity(NamedTuple):
    pid: int
    token: str
    fd: int


class FixtureProcessError(RuntimeError):
    def __init__(
        self, code: str, detail: str, *, stdout: bytes = b"", stderr: bytes = b"",
    ) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.stdout = stdout
        self.stderr = stderr


_LAST_SYSTEMD_UNIT: str | None = None
_LAST_SYSTEMD_CGROUP: str | None = None
_LAST_SYSTEMD_CLIENT_PID: int | None = None
_LAST_SYSTEMD_ANCHOR_PID: int | None = None


def _cleanup_reserve(timeout_s: float) -> float:
    # The caller's one deadline includes teardown.  Reserve a small portion of
    # it before declaring execution timeout so TERM/KILL + two empty scans do
    # not silently become a second timeout budget.
    return min(2.0, max(0.05, timeout_s * 0.2), timeout_s * 0.5)


def _captured(stream: Any) -> bytes:
    stream.flush()
    stream.seek(0)
    return stream.read()


def _decorate_error(
    error: BaseException, stdout: bytes, stderr: bytes,
) -> BaseException:
    if isinstance(error, FixtureProcessError):
        error.stdout = stdout
        error.stderr = stderr
    return error


if os.name == "nt":
    import ctypes
    import msvcrt
    import _winapi
    from ctypes import wintypes

    class _BasicLimit(ctypes.Structure):
        _fields_ = (
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        )

    class _IoCounters(ctypes.Structure):
        _fields_ = tuple(
            (name, ctypes.c_ulonglong) for name in (
                "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                "ReadTransferCount", "WriteTransferCount", "OtherTransferCount",
            )
        )

    class _ExtendedLimit(ctypes.Structure):
        _fields_ = (
            ("BasicLimitInformation", _BasicLimit),
            ("IoInfo", _IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        )

    class _BasicAccounting(ctypes.Structure):
        _fields_ = (
            ("TotalUserTime", ctypes.c_longlong),
            ("TotalKernelTime", ctypes.c_longlong),
            ("ThisPeriodTotalUserTime", ctypes.c_longlong),
            ("ThisPeriodKernelTime", ctypes.c_longlong),
            ("TotalPageFaultCount", wintypes.DWORD),
            ("TotalProcesses", wintypes.DWORD),
            ("ActiveProcesses", wintypes.DWORD),
            ("TotalTerminatedProcesses", wintypes.DWORD),
        )

    _KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _KERNEL32.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
    _KERNEL32.CreateJobObjectW.restype = wintypes.HANDLE
    _KERNEL32.SetInformationJobObject.argtypes = (
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
    )
    _KERNEL32.SetInformationJobObject.restype = wintypes.BOOL
    _KERNEL32.QueryInformationJobObject.argtypes = (
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    )
    _KERNEL32.QueryInformationJobObject.restype = wintypes.BOOL
    _KERNEL32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    _KERNEL32.AssignProcessToJobObject.restype = wintypes.BOOL
    _KERNEL32.IsProcessInJob.argtypes = (
        wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL),
    )
    _KERNEL32.IsProcessInJob.restype = wintypes.BOOL
    _KERNEL32.QueryFullProcessImageNameW.argtypes = (
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    )
    _KERNEL32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    _KERNEL32.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
    _KERNEL32.TerminateJobObject.restype = wintypes.BOOL
    _KERNEL32.ResumeThread.argtypes = (wintypes.HANDLE,)
    _KERNEL32.ResumeThread.restype = wintypes.DWORD
    _KERNEL32.CloseHandle.argtypes = (wintypes.HANDLE,)
    _KERNEL32.CloseHandle.restype = wintypes.BOOL

    def _close_windows_handles(
        handles: Sequence[tuple[str, int]], *, prior: BaseException | None = None,
    ) -> None:
        errors: list[str] = []
        for label, handle in handles:
            try:
                _winapi.CloseHandle(handle)
            except BaseException as exc:
                errors.append(f"{label}={handle}: {type(exc).__name__}: {exc}")
        if errors:
            raise FixtureProcessError(
                "FIXTURE-PROCESS-LIVE",
                f"Windows handle cleanup was not proven: prior={prior!r}, "
                f"close_errors={errors!r}",
            )

    def _windows_concrete_executable(argv0: str) -> str:
        candidate = Path(argv0)
        try:
            details = os.lstat(candidate)
            reparse = bool(
                getattr(details, "st_file_attributes", 0)
                & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
            )
            if not candidate.is_absolute() or not candidate.is_file() or reparse:
                raise FixtureProcessError(
                    "FIXTURE-PROCESS-SPAWN",
                    "Windows suite executable must be one absolute existing "
                    f"regular non-reparse file: {candidate}",
                )
            resolved = candidate.resolve(strict=True)
        except FixtureProcessError:
            raise
        except OSError as exc:
            raise FixtureProcessError(
                "FIXTURE-PROCESS-SPAWN",
                f"cannot resolve Windows suite executable {candidate}: {exc}",
            ) from exc
        return os.path.normcase(os.path.realpath(resolved))

    def _windows_process_image_path(process_handle: int) -> str:
        buffer = ctypes.create_unicode_buffer(32768)
        length = wintypes.DWORD(len(buffer))
        if not _KERNEL32.QueryFullProcessImageNameW(
            process_handle, 0, buffer, ctypes.byref(length),
        ):
            raise FixtureProcessError(
                "FIXTURE-PROCESS-SPAWN",
                f"cannot inspect suspended Windows suite image: "
                f"{ctypes.WinError(ctypes.get_last_error())}",
            )
        return os.path.normcase(os.path.realpath(buffer.value))

    class _WindowsJob:
        def __init__(self) -> None:
            created = _KERNEL32.CreateJobObjectW(None, None)
            if not created:
                raise FixtureProcessError(
                    "FIXTURE-PROCESS-SPAWN",
                    f"CreateJobObjectW failed: {ctypes.WinError(ctypes.get_last_error())}",
                )
            self.handle = int(created)
            limits = _ExtendedLimit()
            # KILL_ON_JOB_CLOSE only.  In particular, neither BREAKAWAY flag is
            # present, so suite code cannot opt out of this boundary.
            limits.BasicLimitInformation.LimitFlags = 0x2000
            if not _KERNEL32.SetInformationJobObject(
                self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits),
            ):
                error = ctypes.WinError(ctypes.get_last_error())
                self.close()
                raise FixtureProcessError(
                    "FIXTURE-PROCESS-SPAWN", f"SetInformationJobObject failed: {error}",
                )

        def contains(self, process_handle: int) -> bool:
            member = wintypes.BOOL()
            if not _KERNEL32.IsProcessInJob(
                process_handle, self.handle, ctypes.byref(member),
            ):
                raise FixtureProcessError(
                    "FIXTURE-PROCESS-SPAWN",
                    f"Windows Job membership query failed: "
                    f"{ctypes.WinError(ctypes.get_last_error())}",
                )
            return bool(member.value)

        def assign_and_prove(self, process_handle: int) -> None:
            if not _KERNEL32.AssignProcessToJobObject(self.handle, process_handle):
                raise FixtureProcessError(
                    "FIXTURE-PROCESS-SPAWN",
                    f"AssignProcessToJobObject failed: "
                    f"{ctypes.WinError(ctypes.get_last_error())}",
                )
            if not self.contains(process_handle):
                raise FixtureProcessError(
                    "FIXTURE-PROCESS-SPAWN",
                    "suspended suite process membership in its private Job is unproven",
                )

        def active_processes(self) -> int:
            accounting = _BasicAccounting()
            returned = wintypes.DWORD()
            if not _KERNEL32.QueryInformationJobObject(
                self.handle, 1, ctypes.byref(accounting), ctypes.sizeof(accounting),
                ctypes.byref(returned),
            ):
                raise FixtureProcessError(
                    "FIXTURE-PROCESS-LIVE",
                    f"QueryInformationJobObject failed: "
                    f"{ctypes.WinError(ctypes.get_last_error())}",
                )
            return int(accounting.ActiveProcesses)

        def terminate(self) -> None:
            if self.active_processes() and not _KERNEL32.TerminateJobObject(
                self.handle, 1223,
            ):
                raise FixtureProcessError(
                    "FIXTURE-PROCESS-LIVE",
                    f"TerminateJobObject failed: "
                    f"{ctypes.WinError(ctypes.get_last_error())}",
                )

        def wait_empty(self, deadline: float) -> None:
            empty_scans = 0
            while empty_scans < 2:
                if self.active_processes() == 0:
                    empty_scans += 1
                    time.sleep(0.01)
                    continue
                empty_scans = 0
                if time.monotonic() >= deadline:
                    raise FixtureProcessError(
                        "FIXTURE-PROCESS-LIVE", "Windows suite Job did not become empty",
                    )
                time.sleep(0.01)

        def close(self) -> None:
            if self.handle:
                handle, self.handle = self.handle, 0
                if not _KERNEL32.CloseHandle(handle):
                    raise FixtureProcessError(
                        "FIXTURE-PROCESS-LIVE",
                        f"CloseHandle(Job) failed: "
                        f"{ctypes.WinError(ctypes.get_last_error())}",
                    )

    class _WindowsProcess:
        def __init__(self, handle: int, pid: int) -> None:
            self.handle = handle
            self.pid = pid
            self.returncode: int | None = None

        def poll(self) -> int | None:
            if self.returncode is not None:
                return self.returncode
            waited = _winapi.WaitForSingleObject(self.handle, 0)
            if waited == _winapi.WAIT_TIMEOUT:
                return None
            if waited != _winapi.WAIT_OBJECT_0:
                raise FixtureProcessError(
                    "FIXTURE-PROCESS-LIVE", f"WaitForSingleObject returned {waited}",
                )
            self.returncode = int(_winapi.GetExitCodeProcess(self.handle))
            return self.returncode

        def close(self) -> None:
            if self.handle:
                handle, self.handle = self.handle, 0
                _close_windows_handles((("Process", handle),))

    def _spawn_windows(
        argv: Sequence[str], cwd: Path, environment: Mapping[str, str],
        stdin: Any, stdout: Any, stderr: Any, job: _WindowsJob, deadline: float,
    ) -> _WindowsProcess:
        expected_executable = _windows_concrete_executable(argv[0])
        current = _winapi.GetCurrentProcess()
        duplicates: list[int] = []
        process_handle = thread_handle = None
        try:
            for stream in (stdin, stdout, stderr):
                duplicates.append(int(_winapi.DuplicateHandle(
                    current, msvcrt.get_osfhandle(stream.fileno()), current, 0, True,
                    _winapi.DUPLICATE_SAME_ACCESS,
                )))
            startup = subprocess.STARTUPINFO()
            startup.dwFlags |= _winapi.STARTF_USESTDHANDLES
            startup.hStdInput, startup.hStdOutput, startup.hStdError = duplicates
            startup.lpAttributeList = {"handle_list": duplicates}
            # CREATE_SUSPENDED | CREATE_UNICODE_ENVIRONMENT.  Deliberately no
            # CREATE_BREAKAWAY_FROM_JOB and no retry outside the private Job.
            process_handle, thread_handle, pid, _ = _winapi.CreateProcess(
                None, subprocess.list2cmdline(list(argv)), None, None, True,
                0x4 | 0x400, dict(environment), str(cwd), startup,
            )
            try:
                created_executable = _windows_process_image_path(int(process_handle))
                if created_executable != expected_executable:
                    raise FixtureProcessError(
                        "FIXTURE-PROCESS-SPAWN",
                        "suspended Windows suite image differs from requested "
                        f"executable: requested={expected_executable}, "
                        f"created={created_executable}",
                    )
                job.assign_and_prove(int(process_handle))
                if _KERNEL32.ResumeThread(int(thread_handle)) == 0xFFFFFFFF:
                    raise FixtureProcessError(
                        "FIXTURE-PROCESS-SPAWN",
                        f"ResumeThread failed: {ctypes.WinError(ctypes.get_last_error())}",
                    )
            except BaseException as spawn_exc:
                cleanup_error: FixtureProcessError | None = None
                try:
                    remaining_ms = max(
                        1, int(max(0.0, deadline - time.monotonic()) * 1000),
                    )
                    direct_error: BaseException | None = None
                    try:
                        _winapi.TerminateProcess(process_handle, 1223)
                    except BaseException as exc:
                        direct_error = exc
                    try:
                        waited = _winapi.WaitForSingleObject(process_handle, remaining_ms)
                    except BaseException:
                        waited = None
                    if waited != _winapi.WAIT_OBJECT_0:
                        try:
                            if not job.contains(int(process_handle)):
                                job.assign_and_prove(int(process_handle))
                            job.terminate()
                            job.wait_empty(deadline)
                            remaining_ms = max(
                                1, int(max(0.0, deadline - time.monotonic()) * 1000),
                            )
                            waited = _winapi.WaitForSingleObject(
                                process_handle, remaining_ms,
                            )
                        except BaseException as fallback_exc:
                            cleanup_error = FixtureProcessError(
                                "FIXTURE-PROCESS-LIVE",
                                "suspended-spawn cleanup failed: "
                                f"direct={direct_error!r}, fallback={fallback_exc!r}",
                            )
                    if waited != _winapi.WAIT_OBJECT_0 and cleanup_error is None:
                        cleanup_error = FixtureProcessError(
                            "FIXTURE-PROCESS-LIVE",
                            "suspended suite process did not exit within bounded cleanup",
                        )
                finally:
                    try:
                        _close_windows_handles(
                            (("suspended Process", int(process_handle)),),
                            prior=cleanup_error or spawn_exc,
                        )
                    except FixtureProcessError as close_exc:
                        cleanup_error = close_exc
                    process_handle = None
                if cleanup_error is not None:
                    raise cleanup_error from spawn_exc
                raise
            return _WindowsProcess(int(process_handle), int(pid))
        finally:
            pending = sys.exception()
            closing: list[tuple[str, int]] = []
            if thread_handle is not None:
                closing.append(("Thread", int(thread_handle)))
            closing.extend(
                (f"stdio duplicate {index}", handle)
                for index, handle in enumerate(duplicates)
            )
            try:
                _close_windows_handles(closing, prior=pending)
            except FixtureProcessError as close_exc:
                if process_handle is not None:
                    try:
                        _close_windows_handles(
                            (("Process after auxiliary-close failure", int(process_handle)),),
                            prior=close_exc,
                        )
                    except FixtureProcessError as process_close_exc:
                        raise FixtureProcessError(
                            "FIXTURE-PROCESS-LIVE",
                            "Windows handle cleanup accumulated auxiliary and process "
                            f"failures: {process_close_exc.detail}",
                        ) from close_exc
                raise


def _run_windows(
    argv: Sequence[str], cwd: Path, environment: Mapping[str, str], timeout_s: float,
) -> FixtureProcessResult:
    started = time.monotonic()
    deadline = started + timeout_s
    execution_deadline = deadline - _cleanup_reserve(timeout_s)
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        job: Any = None
        child: Any = None
        result: FixtureProcessResult | None = None
        failure: BaseException | None = None
        try:
            if os.name != "nt":
                raise FixtureProcessError(
                    "FIXTURE-PROCESS-UNSUPPORTED", "Windows supervisor requested off Windows",
                )
            job = _WindowsJob()
            with open(os.devnull, "rb") as devnull:
                child = _spawn_windows(
                    argv, cwd, environment, devnull, stdout, stderr, job, deadline,
                )
            while child.poll() is None:
                if time.monotonic() >= execution_deadline:
                    raise FixtureProcessError(
                        "FIXTURE-PROCESS-TIMEOUT",
                        f"suite exceeded its {timeout_s:g}s tree-inclusive deadline",
                    )
                time.sleep(0.01)
            returncode = child.returncode
            for _ in range(2):
                active = job.active_processes()
                if active:
                    raise FixtureProcessError(
                        "FIXTURE-PROCESS-TREE-LIVE",
                        f"suite exited while {active} owned descendant process(es) remained",
                    )
                time.sleep(0.01)
            if returncode is None:
                raise FixtureProcessError(
                    "FIXTURE-PROCESS-LIVE", "direct Windows suite exit status is unavailable",
                )
            result = FixtureProcessResult(returncode, b"", b"")
        except BaseException as exc:
            failure = exc
        finally:
            cleanup_errors: list[BaseException] = []
            try:
                if job is not None and job.handle and job.active_processes():
                    job.terminate()
                    job.wait_empty(deadline)
            except BaseException as cleanup_exc:
                cleanup_errors.append(cleanup_exc)
            if child is not None:
                try:
                    child.close()
                except BaseException as close_exc:
                    cleanup_errors.append(close_exc)
            if job is not None and job.handle:
                try:
                    job.close()
                except BaseException as close_exc:
                    cleanup_errors.append(close_exc)
            if cleanup_errors:
                failure = FixtureProcessError(
                    "FIXTURE-PROCESS-LIVE",
                    "Windows suite cleanup was not proven: "
                    f"prior={failure!r}, cleanup={cleanup_errors!r}",
                )
        stdout_bytes, stderr_bytes = _captured(stdout), _captured(stderr)
        if failure is not None:
            raise _decorate_error(failure, stdout_bytes, stderr_bytes)
        assert result is not None
        return FixtureProcessResult(result.returncode, stdout_bytes, stderr_bytes)


def _child_subreaper_state() -> bool:
    if not sys.platform.startswith("linux"):
        raise FixtureProcessError(
            "FIXTURE-PROCESS-UNSUPPORTED",
            f"child-subreaper supervision is unsupported on {sys.platform}",
        )
    import ctypes

    libc = ctypes.CDLL(None, use_errno=True)
    value = ctypes.c_int()
    if libc.prctl(37, ctypes.byref(value), 0, 0, 0) != 0:  # PR_GET_CHILD_SUBREAPER
        raise FixtureProcessError(
            "FIXTURE-PROCESS-SPAWN",
            f"PR_GET_CHILD_SUBREAPER failed with errno {ctypes.get_errno()}",
        )
    return bool(value.value)


def _set_child_subreaper(enabled: bool = True) -> None:
    if not sys.platform.startswith("linux"):
        raise FixtureProcessError(
            "FIXTURE-PROCESS-UNSUPPORTED",
            f"child-subreaper supervision is unsupported on {sys.platform}",
        )
    import ctypes

    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, int(enabled), 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
        raise FixtureProcessError(
            "FIXTURE-PROCESS-SPAWN",
            f"PR_SET_CHILD_SUBREAPER failed with errno {ctypes.get_errno()}",
        )


def _linux_processes() -> dict[int, tuple[int, str]]:
    rows: dict[int, tuple[int, str]] = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            raw = (entry / "stat").read_text(encoding="ascii")
            tail = raw[raw.rfind(")") + 2:].split()
            rows[int(entry.name)] = (int(tail[1]), tail[19])
        except (FileNotFoundError, PermissionError, OSError, ValueError, IndexError):
            continue
    return rows


def _descendants(ancestor: int) -> set[int]:
    snapshot = _linux_processes()
    found: set[int] = set()
    changed = True
    while changed:
        changed = False
        for pid, (ppid, _) in snapshot.items():
            if pid != ancestor and pid not in found and (ppid == ancestor or ppid in found):
                found.add(pid)
                changed = True
    return found


def _descendant_identities(ancestor: int) -> dict[int, str]:
    snapshot = _linux_processes()
    found: dict[int, str] = {}
    changed = True
    while changed:
        changed = False
        for pid, (ppid, token) in snapshot.items():
            if pid != ancestor and pid not in found and (ppid == ancestor or ppid in found):
                found[pid] = token
                changed = True
    return found


def _require_pidfd() -> None:
    if not hasattr(os, "pidfd_open") or not hasattr(signal, "pidfd_send_signal"):
        raise FixtureProcessError(
            "FIXTURE-PROCESS-UNSUPPORTED",
            "Linux suite supervision requires pidfd_open and pidfd_send_signal",
        )


def _close_pidfd(
    identity: _PidfdIdentity, *,
    test_interrupt: BaseException | None = None,
    test_closed_identities: list[int] | None = None,
) -> None:
    try:
        os.close(identity.fd)
        if test_closed_identities is not None:
            test_closed_identities.append(identity.pid)
        if test_interrupt is not None:
            raise test_interrupt
    except Exception as exc:
        raise FixtureProcessError(
            "FIXTURE-PROCESS-LIVE",
            f"cannot close pidfd for owned PID {identity.pid}: {exc}",
        ) from exc


def _close_raw_fds(
    fds: Sequence[int], *, inject_after_first_close: bool = False,
    test_interrupt_after_first_close: BaseException | None = None,
) -> list[BaseException]:
    """Attempt every raw-FD close and return, rather than short-circuit, failures."""
    failures: list[BaseException] = []
    interruptions: list[BaseException] = []
    injected = False
    for fd in fds:
        if fd < 0:
            continue
        try:
            os.close(fd)
            if test_interrupt_after_first_close is not None and not injected:
                injected = True
                raise test_interrupt_after_first_close
            if inject_after_first_close and not injected:
                injected = True
                raise OSError("injected raw-pipe close failure after successful close")
        except BaseException as exc:
            if isinstance(exc, Exception):
                failures.append(exc)
            else:
                interruptions.append(exc)
    if failures:
        # Ordinary cleanup failure overrides a deferred interruption, but every
        # descriptor above has still been attempted.
        return [*failures, *interruptions]
    if interruptions:
        raise interruptions[0]
    return failures


def _open_pidfd_identity(pid: int, expected_token: str) -> _PidfdIdentity | None:
    """Open a stable PID identity, then reverify the observed /proc token."""
    _require_pidfd()
    before = _linux_processes().get(pid)
    if before is None or before[1] != expected_token:
        return None
    try:
        fd = os.pidfd_open(pid, 0)
    except ProcessLookupError:
        return None
    except OSError as exc:
        raise FixtureProcessError(
            "FIXTURE-PROCESS-LIVE", f"cannot open pidfd for owned PID {pid}: {exc}",
        ) from exc
    after = _linux_processes().get(pid)
    if after is None or after[1] != expected_token:
        identity = _PidfdIdentity(pid, expected_token, fd)
        _close_pidfd(identity)
        return None
    return _PidfdIdentity(pid, expected_token, fd)


def _signal_identity(identity: _PidfdIdentity, sig: signal.Signals) -> None:
    try:
        signal.pidfd_send_signal(identity.fd, sig, None, 0)
    except ProcessLookupError:
        return
    except OSError as exc:
        raise FixtureProcessError(
            "FIXTURE-PROCESS-LIVE",
            f"cannot signal pidfd for owned PID {identity.pid}: {exc}",
        ) from exc


def _refresh_pidfd_identities(
    ancestor: int, opened: dict[int, _PidfdIdentity],
) -> dict[int, str]:
    current = _descendant_identities(ancestor)
    for pid, identity in tuple(opened.items()):
        token = current.get(pid)
        if token == identity.token:
            continue
        _close_pidfd(identity)
        del opened[pid]
    for pid, token in current.items():
        if pid in opened:
            continue
        identity = _open_pidfd_identity(pid, token)
        if identity is not None:
            opened[pid] = identity
    return current


def _reap_children(allowed: Mapping[int, _PidfdIdentity] | None = None) -> None:
    if allowed is not None:
        for pid in tuple(allowed):
            try:
                os.waitpid(pid, os.WNOHANG)
            except ChildProcessError:
                continue
        return
    while True:
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            return
        if pid == 0:
            return


def _terminate_posix_tree(ancestor: int, deadline: float) -> None:
    """Freeze by the absolute deadline, kill by pidfd, and prove two empties."""
    opened: dict[int, _PidfdIdentity] = {}
    proof_error: FixtureProcessError | None = None
    stable_scans = 0
    previous: dict[int, str] | None = None
    try:
        # Freeze the complete dynamic shape before killing any ancestor.  This
        # prevents a reparenting interval from looking empty while a child is
        # still being adopted by this subreaper.
        while stable_scans < 2:
            current = _refresh_pidfd_identities(ancestor, opened)
            for identity in tuple(opened.values()):
                _signal_identity(identity, signal.SIGSTOP)
            if current == previous:
                stable_scans += 1
            else:
                stable_scans = 0
                previous = dict(current)
            if time.monotonic() >= deadline and proof_error is None:
                proof_error = FixtureProcessError(
                    "FIXTURE-PROCESS-LIVE",
                    "Linux/WSL suite freeze exceeded its absolute deadline",
                )
            time.sleep(0.01)
        for identity in tuple(opened.values()):
            _signal_identity(identity, signal.SIGKILL)

        empty_scans = 0
        while empty_scans < 2:
            _reap_children(opened)
            current = _refresh_pidfd_identities(ancestor, opened)
            if current:
                empty_scans = 0
                for identity in tuple(opened.values()):
                    _signal_identity(identity, signal.SIGSTOP)
                for identity in tuple(opened.values()):
                    _signal_identity(identity, signal.SIGKILL)
            else:
                empty_scans += 1
            if time.monotonic() >= deadline and proof_error is None:
                proof_error = FixtureProcessError(
                    "FIXTURE-PROCESS-LIVE",
                    "Linux/WSL suite cleanup exceeded its absolute deadline",
                )
            time.sleep(0.01)
        if proof_error is not None:
            raise proof_error
    finally:
        close_errors: list[BaseException] = []
        for identity in tuple(opened.values()):
            try:
                _close_pidfd(identity)
            except BaseException as exc:
                close_errors.append(exc)
        if close_errors:
            raise FixtureProcessError(
                "FIXTURE-PROCESS-LIVE",
                f"Linux/WSL pidfd cleanup was not proven: {close_errors!r}",
            )


def _control_message(control_fd: int, timeout_s: float = 0.01) -> bytes | None:
    import select

    readable, _, _ = select.select([control_fd], [], [], timeout_s)
    return os.read(control_fd, 1) if readable else None


def _write_posix_result(result_fd: int, value: Mapping[str, Any]) -> None:
    raw = (json.dumps(dict(value), sort_keys=True, separators=(",", ":")) + "\n").encode(
        "ascii",
    )
    os.write(result_fd, raw)


def _posix_worker(
    control_fd: int, result_fd: int, stdout_fd: int, stderr_fd: int,
    spec: Mapping[str, Any],
) -> int:
    error: FixtureProcessError | None = None
    product: subprocess.Popen[bytes] | None = None
    returncode: int | None = None
    deadline = float(spec["deadline"])
    execution_deadline = float(spec["execution_deadline"])
    try:
        _set_child_subreaper()
        product = subprocess.Popen(
            list(spec["argv"]), cwd=str(spec["cwd"]), env=dict(spec["environment"]),
            stdin=subprocess.DEVNULL, stdout=stdout_fd, stderr=stderr_fd,
            close_fds=True,
        )
        if spec.get("test_fault") == "sigkill_supervisor_after_product":
            os.kill(os.getpid(), signal.SIGKILL)
        if spec.get("test_fault") == "sigkill_anchor_after_product":
            os.kill(os.getppid(), signal.SIGKILL)
            time.sleep(60)
        if spec.get("test_fault") == "stall_anchor_after_product":
            os.kill(os.getppid(), signal.SIGSTOP)
            time.sleep(60)
        if spec.get("test_fault") == "cleanup_failure_after_primary":
            raise FixtureProcessError(
                "FIXTURE-PROCESS-TIMEOUT", "synthetic primary failure",
            )
        while product.poll() is None:
            message = _control_message(control_fd)
            if message == b"":
                raise FixtureProcessError(
                    "FIXTURE-PROCESS-OWNER-LOST", "fixture runner owner was lost",
                )
            if message is not None:
                raise FixtureProcessError(
                    "FIXTURE-PROCESS-OWNER-LOST", "invalid fixture runner control message",
                )
            if time.monotonic() >= execution_deadline:
                raise FixtureProcessError(
                    "FIXTURE-PROCESS-TIMEOUT",
                    f"suite exceeded its {float(spec['timeout_s']):g}s tree-inclusive deadline",
                )
        returncode = product.wait() if product.returncode is None else product.returncode
        _reap_children()
        for _ in range(2):
            members = _descendants(os.getpid())
            if members:
                raise FixtureProcessError(
                    "FIXTURE-PROCESS-TREE-LIVE",
                    f"suite exited while {len(members)} owned descendant process(es) remained",
                )
            message = _control_message(control_fd)
            if message == b"":
                raise FixtureProcessError(
                    "FIXTURE-PROCESS-OWNER-LOST", "fixture runner owner was lost",
                )
            time.sleep(0.01)
    except FixtureProcessError as exc:
        error = exc
    except BaseException as exc:
        error = FixtureProcessError(
            "FIXTURE-PROCESS-SPAWN", f"{type(exc).__name__}: {exc}",
        )
    finally:
        if spec.get("test_fault") == "stall_before_cleanup" and error is not None:
            time.sleep(60)
        try:
            _terminate_posix_tree(os.getpid(), deadline)
            if spec.get("test_fault") == "cleanup_failure_after_primary":
                raise FixtureProcessError(
                    "FIXTURE-PROCESS-LIVE", "synthetic cleanup failure",
                )
        except FixtureProcessError as cleanup_exc:
            error = FixtureProcessError(
                "FIXTURE-PROCESS-LIVE",
                "Linux/WSL suite cleanup was not proven: "
                f"prior={error!r}, cleanup={cleanup_exc!r}",
            )
        if product is not None and product.returncode is None:
            product.poll()
        try:
            if error is None and returncode is not None:
                _write_posix_result(result_fd, {
                    "status": "ok", "returncode": returncode,
                    "descendants_quiescent": True, "empty_scans": 2,
                })
            else:
                assert error is not None
                _write_posix_result(result_fd, {
                    "status": "error", "code": error.code, "detail": error.detail,
                    "descendants_quiescent": not bool(_descendants(os.getpid())),
                })
        finally:
            close_errors = _close_raw_fds((control_fd, result_fd))
            if close_errors:
                error = FixtureProcessError(
                    "FIXTURE-PROCESS-LIVE",
                    f"Linux/WSL worker pipe cleanup was not proven: {close_errors!r}",
                )
    return 0 if error is None else 2


def _read_all_fd(fd: int) -> bytes:
    raw = b""
    while True:
        chunk = os.read(fd, 65536)
        if not chunk:
            return raw
        raw += chunk


def _deadline_watchdog(
    anchor_pid: int, anchor_token: str, deadline: float, ready_fd: int,
    *, inject_open_failure: bool = False,
) -> None:
    identity = None if inject_open_failure else _open_pidfd_identity(
        anchor_pid, anchor_token,
    )
    if identity is None:
        os._exit(2)
    try:
        os.write(ready_fd, b"R")
        os.close(ready_fd)
        ready_fd = -1
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _signal_identity(identity, signal.SIGKILL)
                os._exit(0)
            time.sleep(min(0.01, remaining))
    except BaseException:
        os._exit(2)


def _read_one_before(fd: int, deadline: float) -> bytes:
    import select

    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return b""
    readable, _, _ = select.select([fd], [], [], remaining)
    return os.read(fd, 1) if readable else b""


def _captured_fd(fd: int) -> bytes:
    os.lseek(fd, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    while True:
        chunk = os.read(fd, 65536)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def _posix_anchor(
    control_fd: int, result_fd: int, stdout_fd: int, stderr_fd: int,
    spec: Mapping[str, Any],
) -> int:
    """Own one worker tree in an otherwise child-free subreaper process."""
    error: FixtureProcessError | None = None
    deferred: BaseException | None = None
    worker_pid: int | None = None
    watchdog_pid: int | None = None
    watchdog_ready_read = watchdog_ready_write = -1
    worker_status: int | None = None
    worker_control_read = worker_control_write = -1
    worker_result_read = worker_result_write = -1
    worker_raw = b""
    deadline = float(spec["deadline"])
    execution_deadline = float(spec["execution_deadline"])
    try:
        _require_pidfd()
        _set_child_subreaper()
        anchor_pid = os.getpid()
        anchor_row = _linux_processes().get(anchor_pid)
        if anchor_row is None:
            raise FixtureProcessError(
                "FIXTURE-PROCESS-LIVE", "cannot bind the anchor identity for its watchdog",
            )
        watchdog_ready_read, watchdog_ready_write = os.pipe()
        watchdog_pid = os.fork()
        if watchdog_pid == 0:
            os.close(watchdog_ready_read)
            _deadline_watchdog(
                anchor_pid, anchor_row[1], deadline, watchdog_ready_write,
                inject_open_failure=(
                    spec.get("test_fault") == "watchdog_pidfd_open_failure"
                ),
            )
            os._exit(2)
        os.close(watchdog_ready_write)
        watchdog_ready_write = -1
        if _read_one_before(watchdog_ready_read, execution_deadline) != b"R":
            raise FixtureProcessError(
                "FIXTURE-PROCESS-LIVE",
                "Linux/WSL deadline watchdog did not prove its pidfd before worker start",
            )
        os.close(watchdog_ready_read)
        watchdog_ready_read = -1
        worker_control_read, worker_control_write = os.pipe()
        worker_result_read, worker_result_write = os.pipe()
        worker_pid = os.fork()
        if worker_pid == 0:
            try:
                os.close(control_fd)
                os.close(result_fd)
                os.close(worker_control_write)
                os.close(worker_result_read)
                rc = _posix_worker(
                    worker_control_read, worker_result_write, stdout_fd, stderr_fd, spec,
                )
            except BaseException:
                rc = 2
            os._exit(rc)
        os.close(worker_control_read)
        worker_control_read = -1
        os.close(worker_result_write)
        worker_result_write = -1

        while True:
            try:
                observed, status = os.waitpid(worker_pid, os.WNOHANG)
            except ChildProcessError:
                observed, status = worker_pid, 0
            if observed == worker_pid:
                worker_status = status
                break
            message = _control_message(control_fd, 0.005)
            if message == b"":
                error = FixtureProcessError(
                    "FIXTURE-PROCESS-OWNER-LOST", "fixture runner owner was lost",
                )
                break
            if message is not None:
                error = FixtureProcessError(
                    "FIXTURE-PROCESS-OWNER-LOST", "invalid fixture runner control message",
                )
                break
            if time.monotonic() >= execution_deadline:
                error = FixtureProcessError(
                    "FIXTURE-PROCESS-TIMEOUT",
                    f"suite exceeded its {float(spec['timeout_s']):g}s tree-inclusive deadline",
                )
                break
    except BaseException as exc:
        deferred = exc
    finally:
        if worker_control_write >= 0:
            try:
                os.close(worker_control_write)
            except BaseException as exc:
                deferred = deferred or exc
            worker_control_write = -1
        while True:
            try:
                _terminate_posix_tree(os.getpid(), deadline)
                break
            except FixtureProcessError as cleanup_exc:
                error = FixtureProcessError(
                    "FIXTURE-PROCESS-LIVE",
                    "Linux/WSL anchor cleanup was not proven: "
                    f"prior={error or deferred!r}, cleanup={cleanup_exc!r}",
                )
                break
            except BaseException as exc:
                deferred = deferred or exc
                continue
        if worker_pid is not None and worker_status is None:
            try:
                observed, status = os.waitpid(worker_pid, os.WNOHANG)
                if observed == worker_pid:
                    worker_status = status
            except ChildProcessError:
                pass
        if worker_result_read >= 0:
            try:
                worker_raw = _read_all_fd(worker_result_read)
            except BaseException as exc:
                deferred = deferred or exc

        for close_exc in _close_raw_fds(
            (
                watchdog_ready_read, watchdog_ready_write,
                worker_control_read, worker_control_write,
                worker_result_read, worker_result_write,
            ),
            inject_after_first_close=(spec.get("test_fault") == "raw_pipe_close_failure"),
        ):
            deferred = deferred or close_exc

    value: dict[str, Any] | None = None
    if worker_raw:
        try:
            decoded = json.loads(worker_raw.decode("ascii"))
            if isinstance(decoded, dict):
                value = decoded
        except (UnicodeDecodeError, json.JSONDecodeError):
            value = None
    if error is None and deferred is not None:
        if isinstance(deferred, FixtureProcessError):
            error = deferred
        else:
            error = FixtureProcessError(
                "FIXTURE-PROCESS-LIVE",
                f"anchor interruption was deferred until closure: {deferred!r}",
            )
    if error is None and (worker_status is None or not os.WIFEXITED(worker_status)):
        error = FixtureProcessError(
            "FIXTURE-PROCESS-LIVE", "Linux/WSL worker terminated without a normal exit",
        )
    if error is None and value is None:
        error = FixtureProcessError(
            "FIXTURE-PROCESS-LIVE", "Linux/WSL worker result is absent or invalid",
        )
    if (
        error is None and value is not None and value.get("status") == "ok"
        and worker_status is not None and os.WEXITSTATUS(worker_status) != 0
    ):
        error = FixtureProcessError(
            "FIXTURE-PROCESS-LIVE",
            "Linux/WSL worker reported success with a nonzero process exit",
        )
    try:
        capture_fields = {
            "stdout_b64": base64.b64encode(_captured_fd(stdout_fd)).decode("ascii"),
            "stderr_b64": base64.b64encode(_captured_fd(stderr_fd)).decode("ascii"),
        }
        if error is None:
            assert value is not None
            value["descendants_quiescent"] = True
            value["empty_scans"] = 2
            value.update(capture_fields)
            _write_posix_result(result_fd, value)
        else:
            _write_posix_result(result_fd, {
                "status": "error", "code": error.code, "detail": error.detail,
                "descendants_quiescent": True, "empty_scans": 2,
                **capture_fields,
            })
    finally:
        close_errors = _close_raw_fds((control_fd, result_fd))
        if close_errors:
            error = FixtureProcessError(
                "FIXTURE-PROCESS-LIVE",
                f"Linux/WSL anchor pipe cleanup was not proven: {close_errors!r}",
            )
    return 0 if error is None and value is not None and value.get("status") == "ok" else 2


_SYSTEMD_PROPERTIES = (
    "ActiveEnterTimestampMonotonic", "ActiveState", "CollectMode", "ControlGroup",
    "KillMode", "KillSignal", "MainPID", "RuntimeMaxUSec", "SendSIGKILL",
)


def _systemd_tools() -> tuple[str, str]:
    run = shutil.which("systemd-run")
    control = shutil.which("systemctl")
    if not run or not control:
        raise FixtureProcessError(
            "FIXTURE-PROCESS-UNSUPPORTED",
            "Linux suite supervision requires systemd-run and systemctl",
        )
    if not Path("/sys/fs/cgroup/cgroup.controllers").is_file():
        raise FixtureProcessError(
            "FIXTURE-PROCESS-UNSUPPORTED", "Linux suite supervision requires cgroup v2",
        )
    return str(Path(run).resolve()), str(Path(control).resolve())


def _systemd_show(control: str, unit: str, timeout_s: float) -> dict[str, str]:
    argv = [control, "--user", "show", unit]
    for name in _SYSTEMD_PROPERTIES:
        argv.append(f"--property={name}")
    try:
        observed = subprocess.run(
            argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=max(0.001, timeout_s), check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise FixtureProcessError(
            "FIXTURE-PROCESS-UNSUPPORTED",
            f"systemd user-manager property query failed before suite start: {exc}",
        ) from exc
    if observed.returncode != 0 or observed.stderr != b"":
        raise FixtureProcessError(
            "FIXTURE-PROCESS-UNSUPPORTED",
            "systemd user-manager property query was not clean before suite start: "
            + observed.stderr.decode("utf-8", errors="replace").strip(),
        )
    values: dict[str, str] = {}
    for line in observed.stdout.decode("utf-8", errors="strict").splitlines():
        key, separator, value = line.partition("=")
        if separator:
            values[key] = value
    return values


def _runtime_max_usec(timeout_s: float) -> int:
    scaled = timeout_s * 1_000_000
    if not math.isfinite(timeout_s) or timeout_s <= 0:
        raise FixtureProcessError(
            "FIXTURE-PROCESS-SPAWN",
            "suite timeout must be positive and finite",
        )
    # systemd accepts integral microseconds.  Always round toward the earlier
    # deadline; rounding up would silently extend the kernel fallback.
    bounded = math.ceil(scaled) - 1
    if bounded < 1:
        raise FixtureProcessError(
            "FIXTURE-PROCESS-SPAWN",
            "suite timeout leaves no positive integral-microsecond runtime budget",
        )
    return bounded


_SYSTEMD_TIMESPAN = re.compile(
    r"(?P<number>[0-9]+(?:\.[0-9]+)?)(?P<unit>usec|us|[µμ]s|msec|ms|sec|s|min|hr|h|d|w)"
)
_SYSTEMD_TIMESPAN_MULTIPLIERS = {
    "usec": 1, "us": 1, "µs": 1, "μs": 1,
    "msec": 1_000, "ms": 1_000,
    "sec": 1_000_000, "s": 1_000_000,
    "min": 60_000_000, "hr": 3_600_000_000, "h": 3_600_000_000,
    "d": 86_400_000_000, "w": 604_800_000_000,
}


def _parse_systemd_runtime_usec(raw: str) -> int:
    if not raw or raw == "infinity":
        raise ValueError("RuntimeMaxUSec is absent or infinite")
    total = Decimal(0)
    cursor = 0
    matched = False
    for match in _SYSTEMD_TIMESPAN.finditer(raw):
        if raw[cursor:match.start()].strip():
            raise ValueError(f"invalid RuntimeMaxUSec syntax: {raw!r}")
        matched = True
        try:
            total += Decimal(match.group("number")) * _SYSTEMD_TIMESPAN_MULTIPLIERS[
                match.group("unit")
            ]
        except (InvalidOperation, KeyError) as exc:
            raise ValueError(f"invalid RuntimeMaxUSec syntax: {raw!r}") from exc
        cursor = match.end()
    if not matched or raw[cursor:].strip() or total != total.to_integral_value():
        raise ValueError(f"invalid RuntimeMaxUSec syntax: {raw!r}")
    return int(total)


def _prove_systemd_unit(
    values: Mapping[str, str], *, pid: int | None = None,
    runtime_max_usec: int | None = None,
    absolute_deadline_usec: int | None = None,
) -> str:
    expected = {
        "ActiveState": "active", "CollectMode": "inactive-or-failed",
        "KillMode": "control-group", "KillSignal": "9", "SendSIGKILL": "yes",
    }
    mismatches = {
        key: (values.get(key), wanted)
        for key, wanted in expected.items() if values.get(key) != wanted
    }
    if pid is not None and values.get("MainPID") != str(pid):
        mismatches["MainPID"] = (values.get("MainPID"), str(pid))
    observed_runtime: int | None = None
    if runtime_max_usec is not None:
        raw_runtime = values.get("RuntimeMaxUSec")
        try:
            observed_runtime = _parse_systemd_runtime_usec(raw_runtime or "")
        except (TypeError, ValueError):
            mismatches["RuntimeMaxUSec"] = (raw_runtime, str(runtime_max_usec))
        else:
            if observed_runtime != runtime_max_usec:
                mismatches["RuntimeMaxUSec"] = (raw_runtime, str(runtime_max_usec))
    if absolute_deadline_usec is not None:
        raw_active = values.get("ActiveEnterTimestampMonotonic", "")
        try:
            active_enter_usec = int(raw_active, 10)
            if active_enter_usec <= 0 or str(active_enter_usec) != raw_active:
                raise ValueError
        except (TypeError, ValueError):
            mismatches["ActiveEnterTimestampMonotonic"] = (
                raw_active, "positive base-10 microseconds",
            )
        else:
            if observed_runtime is None:
                mismatches["RuntimeDeadlineUSec"] = (
                    "unproven", f"<= {absolute_deadline_usec}",
                )
            elif active_enter_usec + observed_runtime > absolute_deadline_usec:
                mismatches["RuntimeDeadlineUSec"] = (
                    str(active_enter_usec + observed_runtime),
                    f"<= {absolute_deadline_usec}",
                )
    cgroup = values.get("ControlGroup", "")
    if not cgroup.startswith("/user.slice/") or ".." in cgroup:
        mismatches["ControlGroup"] = (cgroup, "/user.slice/<exact-unit>")
    if mismatches:
        raise FixtureProcessError(
            "FIXTURE-PROCESS-UNSUPPORTED",
            f"systemd user-service containment properties are unproven: {mismatches!r}",
        )
    return cgroup


def _systemd_cgroup_empty(
    cgroup: str, deadline: float, *, inject_missing_procs: bool = False,
    _test_path: Any | None = None,
) -> None:
    path = _test_path if _test_path is not None else (
        Path("/sys/fs/cgroup") / cgroup.lstrip("/")
    )
    if inject_missing_procs:
        raise FixtureProcessError(
            "FIXTURE-PROCESS-LIVE",
            f"systemd cgroup exists without readable cgroup.procs: {cgroup}",
        )
    empty_scans = 0
    while empty_scans < 2:
        if not path.exists():
            return
        procs = path / "cgroup.procs"
        try:
            live = procs.read_text(encoding="ascii", errors="strict").strip()
        except FileNotFoundError as exc:
            if not path.exists():
                return
            raise FixtureProcessError(
                "FIXTURE-PROCESS-LIVE",
                f"systemd cgroup exists without readable cgroup.procs: {cgroup}",
            ) from exc
        except (OSError, UnicodeError) as exc:
            raise FixtureProcessError(
                "FIXTURE-PROCESS-LIVE",
                f"cannot prove systemd cgroup emptiness for {cgroup}: {exc}",
            ) from exc
        if live:
            empty_scans = 0
        else:
            empty_scans += 1
            if empty_scans >= 2:
                return
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise FixtureProcessError(
                "FIXTURE-PROCESS-LIVE", f"systemd cgroup remained populated: {cgroup}",
            )
        time.sleep(min(0.01, remaining))


def _systemd_unit_collected(
    control: str, unit: str, deadline: float, *, inject_manager_failure: bool = False,
) -> None:
    command = [
        control, "--user", "list-units", "--all", "--full", "--plain",
        "--no-legend", unit,
    ]
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise FixtureProcessError(
                "FIXTURE-PROCESS-LIVE",
                f"deadline expired before transient systemd unit collection was proved: {unit}",
            )
        try:
            observed = subprocess.run(
                command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, timeout=remaining, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise FixtureProcessError(
                "FIXTURE-PROCESS-LIVE",
                f"systemd manager collection query failed for {unit}: {exc}",
            ) from exc
        if inject_manager_failure:
            raise FixtureProcessError(
                "FIXTURE-PROCESS-LIVE",
                f"injected systemd manager collection query failure for {unit}",
            )
        if observed.returncode != 0 or observed.stderr != b"":
            raise FixtureProcessError(
                "FIXTURE-PROCESS-LIVE",
                "systemd manager collection query failed for " + unit + ": "
                + observed.stderr.decode("utf-8", errors="replace").strip(),
            )
        if observed.stdout == b"":
            return
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise FixtureProcessError(
                "FIXTURE-PROCESS-LIVE",
                f"transient systemd unit was not collected: {unit}: {observed.stdout!r}",
            )
        time.sleep(min(0.01, remaining))


def _systemd_anchor_main(unit: str, control: str) -> int:
    try:
        values = _systemd_show(control, unit, 2.0)
        cgroup = _prove_systemd_unit(values, pid=os.getpid())
        _write_posix_result(1, {"status": "ready", "pid": os.getpid(), "cgroup": cgroup})
        line = sys.stdin.buffer.readline(16 * 1024 * 1024)
        if not line.endswith(b"\n"):
            raise FixtureProcessError(
                "FIXTURE-PROCESS-OWNER-LOST", "suite specification channel closed before START",
            )
        spec = json.loads(line.decode("utf-8", errors="strict"))
        if not isinstance(spec, dict):
            raise ValueError("suite specification is not an object")
        if spec.get("test_fault") == "systemd_protocol_stderr":
            os.write(2, b"injected systemd-run stderr diagnostic\n")
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            return _posix_anchor(0, 1, stdout.fileno(), stderr.fileno(), spec)
    except BaseException as exc:
        error = exc if isinstance(exc, FixtureProcessError) else FixtureProcessError(
            "FIXTURE-PROCESS-SPAWN", f"{type(exc).__name__}: {exc}",
        )
        try:
            _write_posix_result(1, {
                "status": "error", "code": error.code, "detail": error.detail,
                "descendants_quiescent": True, "empty_scans": 2,
                "stdout_b64": "", "stderr_b64": "",
            })
        except BaseException:
            pass
        return 2


def _write_all_before(fd: int, raw: bytes, deadline: float) -> None:
    import select

    offset = 0
    while offset < len(raw):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise FixtureProcessError(
                "FIXTURE-PROCESS-LIVE", "deadline expired while sending suite specification",
            )
        _, writable, _ = select.select([], [fd], [], remaining)
        if not writable:
            continue
        offset += os.write(fd, raw[offset:])


def _read_ready_before(
    stdout_fd: int, stderr_fd: int, deadline: float, diagnostics: bytearray,
) -> tuple[bytes, bytes]:
    import select

    pending = bytearray()
    while b"\n" not in pending:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise FixtureProcessError(
                "FIXTURE-PROCESS-UNSUPPORTED",
                "systemd anchor did not reach pre-suite READY before the deadline",
            )
        readable, _, _ = select.select([stdout_fd, stderr_fd], [], [], remaining)
        if not readable:
            continue
        for fd in readable:
            chunk = os.read(fd, 65536)
            if fd == stderr_fd:
                diagnostics.extend(chunk)
            elif not chunk:
                raise FixtureProcessError(
                    "FIXTURE-PROCESS-UNSUPPORTED",
                    "systemd anchor closed its READY channel before START",
                )
            else:
                pending.extend(chunk)
                if len(pending) > 16 * 1024 * 1024:
                    raise FixtureProcessError(
                        "FIXTURE-PROCESS-UNSUPPORTED", "systemd anchor READY is oversized",
                    )
    line, remainder = bytes(pending).split(b"\n", 1)
    return line + b"\n", remainder


def _drain_systemd_pipes(
    stdout_fd: int, stderr_fd: int, protocol: bytearray, diagnostics: bytearray,
    timeout_s: float,
) -> tuple[bool, bool]:
    import select

    readable, _, _ = select.select(
        [fd for fd in (stdout_fd, stderr_fd) if fd >= 0], [], [], max(0.0, timeout_s),
    )
    stdout_eof = stderr_eof = False
    for fd in readable:
        try:
            chunk = os.read(fd, 65536)
        except BlockingIOError:
            continue
        if fd == stdout_fd:
            if chunk:
                protocol.extend(chunk)
            else:
                stdout_eof = True
        else:
            if chunk:
                diagnostics.extend(chunk)
            else:
                stderr_eof = True
    return stdout_eof, stderr_eof


def _run_posix(
    argv: Sequence[str], cwd: Path, environment: Mapping[str, str], timeout_s: float,
    *, test_fault: str | None = None,
    test_cleanup_interrupt: BaseException | None = None,
    test_closed_pidfd_identities: list[int] | None = None,
) -> FixtureProcessResult:
    if not sys.platform.startswith("linux"):
        raise FixtureProcessError(
            "FIXTURE-PROCESS-UNSUPPORTED",
            f"child-subreaper supervision is unsupported on {sys.platform}",
        )
    _require_pidfd()
    if test_fault == "systemd_manager_missing":
        raise FixtureProcessError(
            "FIXTURE-PROCESS-UNSUPPORTED", "injected missing systemd user manager",
        )
    systemd_run, systemctl = _systemd_tools()
    if test_fault == "non_cgroup_v2":
        raise FixtureProcessError(
            "FIXTURE-PROCESS-UNSUPPORTED", "injected non-cgroup-v2 topology",
        )
    deadline = time.monotonic() + timeout_s
    cleanup_reserve = _cleanup_reserve(timeout_s)
    execution_deadline = deadline - cleanup_reserve
    absolute_deadline_usec = math.floor(deadline * 1_000_000)
    # Reserve the final teardown interval before creating the unit.  The later
    # property proof binds systemd's actual activation timestamp to this
    # parent-established absolute deadline and refuses if startup consumed the
    # reserve.
    runtime_max_usec = _runtime_max_usec(timeout_s - cleanup_reserve)
    unit = f"coauthor-fixture-{uuid.uuid4().hex}.service"
    global _LAST_SYSTEMD_UNIT, _LAST_SYSTEMD_CGROUP
    global _LAST_SYSTEMD_CLIENT_PID, _LAST_SYSTEMD_ANCHOR_PID
    _LAST_SYSTEMD_UNIT = unit
    _LAST_SYSTEMD_CGROUP = None
    _LAST_SYSTEMD_CLIENT_PID = None
    _LAST_SYSTEMD_ANCHOR_PID = None
    spec = {
        "argv": list(argv), "cwd": str(cwd), "environment": dict(environment),
        "timeout_s": timeout_s, "deadline": deadline, "test_fault": test_fault,
    }
    command = [
        systemd_run, "--user", "--pipe", "--wait", "--collect", "--quiet",
        "--service-type=exec", f"--unit={unit}", "--expand-environment=no",
        "--property=KillMode=control-group", "--property=KillSignal=SIGKILL",
        "--property=SendSIGKILL=yes", "--property=TimeoutStopSec=1s",
        f"--property=RuntimeMaxSec={runtime_max_usec}us",
        sys.executable, "-I", "-B", str(Path(__file__).resolve()),
        "_systemd_anchor", unit, systemctl,
    ]
    client: subprocess.Popen[bytes] | None = None
    primary: BaseException | None = None
    protocol = bytearray()
    diagnostics = bytearray()
    cgroup = ""
    client_identity: _PidfdIdentity | None = None
    anchor_identity: _PidfdIdentity | None = None
    stdout_fd = stderr_fd = -1
    stdout_eof = stderr_eof = False
    cleanup_interrupt_raised = False

    def take_cleanup_interrupt(primitive: str) -> BaseException | None:
        nonlocal cleanup_interrupt_raised
        if (
            test_cleanup_interrupt is not None
            and test_fault == f"baseexception_in_{primitive}"
            and not cleanup_interrupt_raised
        ):
            cleanup_interrupt_raised = True
            return test_cleanup_interrupt
        return None

    def raise_cleanup_interrupt(primitive: str) -> None:
        interruption = take_cleanup_interrupt(primitive)
        if interruption is not None:
            raise interruption

    try:
        client = subprocess.Popen(
            command, env=dict(os.environ), stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True,
        )
        assert client.stdin is not None and client.stdout is not None
        assert client.stderr is not None
        _LAST_SYSTEMD_CLIENT_PID = client.pid
        client_row = _linux_processes().get(client.pid)
        if client_row is None:
            raise FixtureProcessError(
                "FIXTURE-PROCESS-UNSUPPORTED",
                "cannot bind the systemd-run client identity before suite start",
            )
        client_identity = _open_pidfd_identity(client.pid, client_row[1])
        if client_identity is None:
            raise FixtureProcessError(
                "FIXTURE-PROCESS-UNSUPPORTED",
                "systemd-run client identity changed before suite start",
            )
        if test_fault == "baseexception_in_direct_kill":
            # Exercise the exact unreaped-direct-child fallback without leaking
            # the already-proved pidfd identity used for ordinary operation.
            _close_pidfd(client_identity)
            client_identity = None
        stdout_fd, stderr_fd = client.stdout.fileno(), client.stderr.fileno()
        os.set_blocking(stdout_fd, False)
        os.set_blocking(stderr_fd, False)
        ready_raw, remainder = _read_ready_before(
            stdout_fd, stderr_fd, execution_deadline, diagnostics,
        )
        protocol.extend(remainder)
        try:
            ready = json.loads(ready_raw.decode("ascii"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise FixtureProcessError(
                "FIXTURE-PROCESS-UNSUPPORTED",
                f"systemd anchor READY is absent or invalid: {ready_raw!r}",
            ) from exc
        if ready.get("status") != "ready":
            raise FixtureProcessError(
                "FIXTURE-PROCESS-UNSUPPORTED", f"systemd anchor refused before START: {ready!r}",
            )
        try:
            anchor_pid = int(ready["pid"])
        except (KeyError, TypeError, ValueError) as exc:
            raise FixtureProcessError(
                "FIXTURE-PROCESS-UNSUPPORTED", "systemd anchor PID is absent or invalid",
            ) from exc
        _LAST_SYSTEMD_ANCHOR_PID = anchor_pid
        anchor_row = _linux_processes().get(anchor_pid)
        if anchor_row is None:
            raise FixtureProcessError(
                "FIXTURE-PROCESS-UNSUPPORTED",
                "cannot bind the systemd anchor identity before suite start",
            )
        anchor_identity = _open_pidfd_identity(anchor_pid, anchor_row[1])
        if anchor_identity is None:
            raise FixtureProcessError(
                "FIXTURE-PROCESS-UNSUPPORTED",
                "systemd anchor identity changed before suite start",
            )
        values = _systemd_show(
            systemctl, unit, max(0.001, execution_deadline - time.monotonic()),
        )
        if test_fault == "unproven_killmode":
            values["KillMode"] = "process"
        if test_fault == "nonnumeric_runtime_max":
            values["RuntimeMaxUSec"] = "not-a-number"
        if test_fault == "wrong_runtime_max":
            values["RuntimeMaxUSec"] = f"{runtime_max_usec + 1}us"
        cgroup = _prove_systemd_unit(
            values, pid=anchor_pid, runtime_max_usec=runtime_max_usec,
            absolute_deadline_usec=absolute_deadline_usec,
        )
        _LAST_SYSTEMD_CGROUP = cgroup
        if ready.get("cgroup") != cgroup:
            raise FixtureProcessError(
                "FIXTURE-PROCESS-UNSUPPORTED", "anchor and parent observed different cgroups",
            )
        # RuntimeMaxSec is systemd's hard stop behind the anchor.  It lands at
        # activation + (timeout - reserve), a startup latency after
        # execution_deadline, so an anchor that detected a suite timeout at
        # execution_deadline was killed mid-report and its TIMEOUT diagnostic
        # and captured bytes were lost.  Detect the timeout early enough to
        # leave the anchor half the reserve before the proven hard stop.
        runtime_end = (
            int(values["ActiveEnterTimestampMonotonic"]) + runtime_max_usec
        ) / 1_000_000
        suite_deadline = min(execution_deadline, runtime_end - cleanup_reserve / 2)
        spec["execution_deadline"] = suite_deadline
        if time.monotonic() >= suite_deadline:
            raise FixtureProcessError(
                "FIXTURE-PROCESS-UNSUPPORTED", "absolute deadline expired before START",
            )
        encoded = (json.dumps(spec, sort_keys=True, separators=(",", ":")) + "\n").encode()
        _write_all_before(client.stdin.fileno(), encoded, suite_deadline)
        client.stdin.flush()
        if test_fault == "parent_keyboard_interrupt":
            raise KeyboardInterrupt
        if test_fault == "stop_systemd_client_after_start":
            _signal_identity(client_identity, signal.SIGSTOP)
        cleanup_interrupt_faults = {
            "baseexception_during_final_cleanup",
            "baseexception_in_stdin_close",
            "baseexception_in_direct_kill",
            "baseexception_in_pidfd_signal",
            "baseexception_in_pidfd_close",
            "baseexception_in_raw_fd_close",
        }
        if test_fault not in cleanup_interrupt_faults:
            # Wait for the anchor's report, or for systemd's hard stop to end
            # the unit; only a unit that outlives that stop is killed here,
            # leaving the rest of the reserve for terminal proof.
            unit_cutoff = runtime_end + max(0.0, deadline - runtime_end) / 2
            while client.poll() is None:
                remaining = unit_cutoff - time.monotonic()
                if remaining <= 0:
                    raise FixtureProcessError(
                        "FIXTURE-PROCESS-LIVE", "systemd unit outlived its RuntimeMaxSec hard stop",
                    )
                out_eof, err_eof = _drain_systemd_pipes(
                    stdout_fd, stderr_fd, protocol, diagnostics, min(0.01, remaining),
                )
                stdout_eof = stdout_eof or out_eof
                stderr_eof = stderr_eof or err_eof
    except BaseException as exc:
        primary = primary or exc
    finally:
        cleanup_errors: list[BaseException] = []
        inject_legacy_cleanup_interrupt = test_fault == "baseexception_during_final_cleanup"
        teardown_complete = False

        def record_cleanup_exception(exc: BaseException) -> None:
            nonlocal primary
            if isinstance(exc, Exception):
                cleanup_errors.append(exc)
            else:
                primary = primary or exc

        while not teardown_complete:
            try:
                if client is not None and client.stdin is not None:
                    try:
                        client.stdin.close()
                        raise_cleanup_interrupt("stdin_close")
                    except BaseException as exc:
                        record_cleanup_exception(exc)
                if inject_legacy_cleanup_interrupt:
                    inject_legacy_cleanup_interrupt = False
                    raise KeyboardInterrupt
                if client is not None and (primary is not None or client.poll() is None):
                    if client.poll() is None and client_identity is None:
                        try:
                            # An unreaped direct child PID cannot be reused; this path
                            # exists only when pre-START pidfd binding itself failed.
                            client.kill()
                            raise_cleanup_interrupt("direct_kill")
                        except BaseException as exc:
                            record_cleanup_exception(exc)
                    for identity in (anchor_identity, client_identity):
                        if identity is not None:
                            try:
                                _signal_identity(identity, signal.SIGKILL)
                                raise_cleanup_interrupt("pidfd_signal")
                            except BaseException as exc:
                                record_cleanup_exception(exc)
                    cleanup_cutoff = deadline - min(
                        0.02, _cleanup_reserve(timeout_s) * 0.25,
                    )
                    while client.poll() is None and time.monotonic() < cleanup_cutoff:
                        remaining = cleanup_cutoff - time.monotonic()
                        if stdout_fd >= 0 and stderr_fd >= 0:
                            out_eof, err_eof = _drain_systemd_pipes(
                                stdout_fd, stderr_fd, protocol, diagnostics,
                                min(0.01, max(0.0, remaining)),
                            )
                            stdout_eof = stdout_eof or out_eof
                            stderr_eof = stderr_eof or err_eof
                    if client.poll() is None:
                        cleanup_errors.append(FixtureProcessError(
                            "FIXTURE-PROCESS-LIVE",
                            "pidfd-killed systemd-run client did not exit before terminal proof",
                        ))
                if stdout_fd >= 0 and stderr_fd >= 0:
                    drain_cutoff = deadline - min(0.01, _cleanup_reserve(timeout_s) * 0.1)
                    while not (stdout_eof and stderr_eof) and time.monotonic() < drain_cutoff:
                        out_eof, err_eof = _drain_systemd_pipes(
                            stdout_fd, stderr_fd, protocol, diagnostics,
                            min(0.01, max(0.0, drain_cutoff - time.monotonic())),
                        )
                        stdout_eof = stdout_eof or out_eof
                        stderr_eof = stderr_eof or err_eof
                    if client is not None and client.poll() is not None and not (
                        stdout_eof and stderr_eof
                    ):
                        cleanup_errors.append(FixtureProcessError(
                            "FIXTURE-PROCESS-LIVE",
                            "systemd client pipe closure was not proved before terminal query",
                        ))
                if client is not None:
                    for stream in (client.stdout, client.stderr):
                        if stream is not None:
                            try:
                                stream.close()
                                raise_cleanup_interrupt("raw_fd_close")
                            except BaseException as exc:
                                record_cleanup_exception(exc)
                if anchor_identity is not None:
                    try:
                        _close_pidfd(
                            anchor_identity,
                            test_interrupt=take_cleanup_interrupt("pidfd_close"),
                            test_closed_identities=test_closed_pidfd_identities,
                        )
                    except BaseException as exc:
                        record_cleanup_exception(exc)
                    finally:
                        anchor_identity = None
                if client_identity is not None:
                    try:
                        _close_pidfd(
                            client_identity,
                            test_interrupt=take_cleanup_interrupt("pidfd_close"),
                            test_closed_identities=test_closed_pidfd_identities,
                        )
                    except BaseException as exc:
                        record_cleanup_exception(exc)
                    finally:
                        client_identity = None
                teardown_complete = True
            except BaseException as exc:
                # Cleanup is a state machine: defer asynchronous interruption
                # and resume until owned PIDs, pipes, and pidfds are terminal.
                record_cleanup_exception(exc)
        if cleanup_errors:
            primary = FixtureProcessError(
                "FIXTURE-PROCESS-LIVE",
                f"systemd client/anchor teardown was not proven: prior={primary!r}; "
                f"cleanup={cleanup_errors!r}",
            )

    # Terminal systemd state is part of the proof, including anchor-SIGKILL.
    terminal_failures: list[FixtureProcessError] = []
    terminal_cleanup_errors: list[BaseException] = []
    cgroup_proved = not bool(cgroup)
    unit_proved = False
    while not (cgroup_proved and unit_proved):
        try:
            if not cgroup_proved:
                try:
                    _systemd_cgroup_empty(
                        cgroup, deadline,
                        inject_missing_procs=(test_fault == "missing_cgroup_procs"),
                    )
                except FixtureProcessError as exc:
                    terminal_failures.append(exc)
                cgroup_proved = True
            if not unit_proved:
                try:
                    _systemd_unit_collected(
                        systemctl, unit, deadline,
                        inject_manager_failure=(test_fault == "collection_query_failure"),
                    )
                except FixtureProcessError as exc:
                    terminal_failures.append(exc)
                unit_proved = True
        except BaseException as exc:
            # Even an interrupt in terminal observation is deferred until both
            # independent systemd closure planes have been attempted.
            if isinstance(exc, Exception):
                terminal_cleanup_errors.append(exc)
            else:
                primary = primary or exc
    if terminal_failures or terminal_cleanup_errors:
        raise FixtureProcessError(
            "FIXTURE-PROCESS-LIVE",
            f"terminal systemd closure was not proven: prior={primary!r}; "
            f"terminal={terminal_failures!r}; cleanup={terminal_cleanup_errors!r}",
        )
    if primary is not None and not isinstance(primary, FixtureProcessError):
        raise primary
    if (
        not protocol and isinstance(primary, FixtureProcessError)
        and primary.code == "FIXTURE-PROCESS-UNSUPPORTED"
    ):
        raise primary
    if not protocol:
        raise FixtureProcessError(
            "FIXTURE-PROCESS-LIVE",
            "systemd anchor result is absent; "
            + diagnostics.decode("utf-8", errors="replace").strip(),
        )
    try:
        value = json.loads(bytes(protocol).decode("ascii"))
        stdout_bytes = base64.b64decode(value.pop("stdout_b64"), validate=True)
        stderr_bytes = base64.b64decode(value.pop("stderr_b64"), validate=True)
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, ValueError) as exc:
        raise FixtureProcessError(
            "FIXTURE-PROCESS-LIVE", "systemd anchor result is invalid",
        ) from exc
    if value.get("descendants_quiescent") is not True or value.get("empty_scans") != 2:
        raise FixtureProcessError(
            "FIXTURE-PROCESS-LIVE", "systemd anchor closure is unproven",
            stdout=stdout_bytes, stderr=stderr_bytes,
        )
    if primary is not None:
        if value.get("code") == "FIXTURE-PROCESS-LIVE":
            raise FixtureProcessError(
                "FIXTURE-PROCESS-LIVE", str(value.get("detail", "systemd cleanup failed")),
                stdout=stdout_bytes, stderr=stderr_bytes,
            )
        raise _decorate_error(primary, stdout_bytes, stderr_bytes)
    if client is None or client.returncode != 0 or value.get("status") != "ok":
        raise FixtureProcessError(
            str(value.get("code", "FIXTURE-PROCESS-LIVE")),
            str(value.get("detail", "systemd suite supervision failed")),
            stdout=stdout_bytes, stderr=stderr_bytes,
        )
    if diagnostics:
        raise FixtureProcessError(
            "FIXTURE-PROCESS-LIVE",
            "systemd-run emitted stderr diagnostics despite a valid result: "
            + diagnostics.decode("utf-8", errors="replace").strip(),
            stdout=stdout_bytes, stderr=stderr_bytes,
        )
    return FixtureProcessResult(int(value["returncode"]), stdout_bytes, stderr_bytes)


def run_owned(
    argv: Sequence[str], *, cwd: str | Path, timeout_s: float,
    environment: Mapping[str, str] | None = None,
    _test_fault: str | None = None,
    _test_platform: tuple[str, str] | None = None,
    _test_cleanup_interrupt: BaseException | None = None,
    _test_closed_pidfd_identities: list[int] | None = None,
) -> FixtureProcessResult:
    """Run one suite under an owned process-tree boundary.

    ``timeout_s`` is one tree-inclusive monotonic deadline.  A successful
    result proves the direct exit and two empty-tree observations.  Any
    ambiguity raises ``FixtureProcessError`` after best-effort complete cleanup.
    """
    if not argv or timeout_s <= 0:
        raise FixtureProcessError(
            "FIXTURE-PROCESS-SPAWN", "argv must be non-empty and timeout_s positive",
        )
    exact_cwd = Path(cwd).resolve()
    exact_env = dict(os.environ if environment is None else environment)
    try:
        platform_os, platform_name = _test_platform or (os.name, sys.platform)
        if platform_os == "nt":
            return _run_windows(argv, exact_cwd, exact_env, float(timeout_s))
        if platform_name.startswith("linux"):
            return _run_posix(
                argv, exact_cwd, exact_env, float(timeout_s), test_fault=_test_fault,
                test_cleanup_interrupt=_test_cleanup_interrupt,
                test_closed_pidfd_identities=_test_closed_pidfd_identities,
            )
        raise FixtureProcessError(
            "FIXTURE-PROCESS-UNSUPPORTED",
            f"fixture process-tree supervision is unsupported on {platform_name}",
        )
    except FixtureProcessError:
        raise
    except Exception as exc:
        raise FixtureProcessError(
            "FIXTURE-PROCESS-SPAWN", f"{type(exc).__name__}: {exc}",
        ) from exc
    except BaseException:
        raise


def _main(argv: Sequence[str]) -> int:
    if len(argv) == 3 and argv[0] == "_systemd_anchor":
        return _systemd_anchor_main(argv[1], argv[2])
    print("fixture_process_supervisor is an internal fixture-runner helper", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
