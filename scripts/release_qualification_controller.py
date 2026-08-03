#!/usr/bin/env python3
"""Restart-safe controller for release-qualification child processes."""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import platform
import re
import secrets
import signal
import site
import stat
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator

from destination_capability import DEST_PROTECTED, DestinationRefused, assert_writable
from qualification_environment import (
    QualificationEnvironmentRefusal,
    assert_ambient_clean,
    controlled_environment,
)
from worktree_paths import git_common_dir, registered_worktree_roots

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "references" / "schemas" / "release_qualification_controller.schema.json"
RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
REGRESSION_CONTRACT = (
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
)
_REQUEST_IDENTITY_KEYS = (
    "schema_version", "run_id", "argv", "cwd", "environment_delta", "inputs",
    "input_roots", "allowed_output_roots", "output_watch_roots", "ignored_output_paths",
    "allow_user_site", "child_attestation", "test_fault",
)
_ATTESTATION_ENV = (
    "COAUTHOR_RELEASE_CONTROLLER_ATTESTATION_RUN_DIR",
    "COAUTHOR_RELEASE_CONTROLLER_ATTESTATION_TOKEN",
)
_SUPERVISOR_JOB_ENV = "COAUTHOR_RELEASE_CONTROLLER_SUPERVISOR_JOB_HANDLE"
_SHARED_RUNNER_LOCK = "coauthor-fixture-runner.lock"
_ATOMIC_LOCK = threading.RLock()


class ControllerRefusal(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code, self.message = code, message


class _WindowsDurabilityRefusal(ControllerRefusal):
    def __init__(self, message: str):
        super().__init__("RELEASE-CONTROLLER-PROCESS", message)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")


def _sha_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic(path: Path, raw: bytes) -> None:
    with _ATOMIC_LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(
            f".{path.name}.{os.getpid()}.{secrets.token_hex(16)}.tmp"
        )
        try:
            with temporary.open("xb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            for attempt in range(50):
                try:
                    os.replace(temporary, path)
                    break
                except PermissionError:
                    if attempt == 49:
                        raise
                    time.sleep(0.01)
            if path.read_bytes() != raw:
                raise ControllerRefusal("RELEASE-CONTROLLER-IO", f"atomic readback failed: {path}")
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


class _RunLock:
    def __init__(self, path: Path, timeout_s: float = 30.0):
        self.path, self.timeout_s, self.stream = path, timeout_s, None

    def __enter__(self):
        _ATOMIC_LOCK.acquire()
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.stream = self.path.open("a+b")
            if self.stream.seek(0, os.SEEK_END) == 0:
                self.stream.write(b"\0")
                self.stream.flush()
                os.fsync(self.stream.fileno())
            deadline = time.monotonic() + self.timeout_s
            if os.name == "nt":
                import msvcrt

                while True:
                    try:
                        self.stream.seek(0)
                        msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
                        break
                    except OSError as exc:
                        if (
                            getattr(exc, "winerror", None) not in {33, 36}
                            and getattr(exc, "errno", None) not in {
                                errno.EACCES, errno.EAGAIN, errno.EDEADLK,
                            }
                        ):
                            raise ControllerRefusal(
                                "RELEASE-CONTROLLER-IO",
                                f"run lock acquisition failed: {exc}",
                            ) from exc
                        if time.monotonic() >= deadline:
                            raise ControllerRefusal("RELEASE-CONTROLLER-LIVE", "run lock timed out")
                        time.sleep(.01)
            else:
                import fcntl

                while True:
                    try:
                        fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except OSError as exc:
                        if (
                            not isinstance(exc, BlockingIOError)
                            and getattr(exc, "errno", None) not in {
                                errno.EACCES, errno.EAGAIN, errno.EDEADLK,
                            }
                        ):
                            raise ControllerRefusal(
                                "RELEASE-CONTROLLER-IO",
                                f"run lock acquisition failed: {exc}",
                            ) from exc
                        if time.monotonic() >= deadline:
                            raise ControllerRefusal("RELEASE-CONTROLLER-LIVE", "run lock timed out")
                        time.sleep(.01)
            return self
        except Exception as primary:
            stream, self.stream = self.stream, None
            cleanup_error: Exception | None = None
            try:
                if stream is not None:
                    stream.close()
            except Exception as exc:
                cleanup_error = exc
            finally:
                _ATOMIC_LOCK.release()
            if isinstance(primary, ControllerRefusal) and cleanup_error is None:
                raise
            code = (
                primary.code if isinstance(primary, ControllerRefusal)
                else "RELEASE-CONTROLLER-IO"
            )
            detail = (
                primary.message if isinstance(primary, ControllerRefusal)
                else f"run lock initialization failed: {primary}"
            )
            if cleanup_error is not None:
                detail += f"; cleanup close failed: {cleanup_error}"
            raise ControllerRefusal(code, detail) from primary

    def __exit__(self, _exc_type, _exc, _traceback):
        stream, self.stream = self.stream, None
        unlock_error: Exception | None = None
        close_error: Exception | None = None
        try:
            if stream is not None:
                if os.name == "nt":
                    import msvcrt

                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        except Exception as exc:
            unlock_error = exc
        finally:
            try:
                if stream is not None:
                    stream.close()
            except Exception as exc:
                close_error = exc
            finally:
                _ATOMIC_LOCK.release()
        if unlock_error is not None:
            raise ControllerRefusal(
                "RELEASE-CONTROLLER-IO", f"run lock release failed: {unlock_error}",
            ) from unlock_error
        if close_error is not None:
            raise ControllerRefusal(
                "RELEASE-CONTROLLER-IO", f"run lock close failed: {close_error}",
            ) from close_error


def _read(path: Path) -> dict[str, Any]:
    error: Exception | None = None
    for attempt in range(50):
        try:
            value = json.loads(path.read_text(encoding="ascii", errors="strict"))
            break
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            error = exc
            if attempt == 49:
                raise ControllerRefusal("RELEASE-CONTROLLER-EVIDENCE", f"unreadable {path.name}: {exc}") from exc
            time.sleep(0.01)
    if not isinstance(value, dict):
        raise ControllerRefusal("RELEASE-CONTROLLER-EVIDENCE", f"{path.name} is not an object")
    return value


def _binding(path: Path) -> dict[str, Any]:
    return {"path": str(path.resolve()), "byte_length": path.stat().st_size, "sha256": _sha_file(path)}


def _validated_intent(path: Path) -> dict[str, Any]:
    value = _read(path)
    expected_keys = {
        *_REQUEST_IDENTITY_KEYS, "request_sha256", "output_preimage",
        "controller_created_output_roots", "intent_sha256", "created_at",
    }
    if set(value) != expected_keys:
        raise ControllerRefusal("RELEASE-CONTROLLER-INTENT", "intent fields are incomplete or unexpected")
    request = _request_identity(value)
    if value.get("request_sha256") != _sha_bytes(_canonical(request)):
        raise ControllerRefusal("RELEASE-CONTROLLER-INTENT", "request digest is stale")
    full_intent = {key: item for key, item in value.items() if key != "intent_sha256"}
    if value.get("intent_sha256") != _sha_bytes(_canonical(full_intent)):
        raise ControllerRefusal("RELEASE-CONTROLLER-INTENT", "full intent digest is stale")
    return value


def _request_identity(value: Mapping[str, Any]) -> dict[str, Any]:
    request = {key: value.get(key) for key in _REQUEST_IDENTITY_KEYS}
    environment_delta = dict(request.get("environment_delta") or {})
    for key in _ATTESTATION_ENV:
        environment_delta.pop(key, None)
    request["environment_delta"] = environment_delta
    return request


def _validate_receipt(value: Mapping[str, Any]) -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda error: list(error.path))
    if errors:
        raise ControllerRefusal("RELEASE-CONTROLLER-SCHEMA", errors[0].message)


def _validate_terminal(paths: Mapping[str, Path], value: dict[str, Any]) -> dict[str, Any]:
    child_result = value.get("state") in {"succeeded", "child_failed", "cancelled"} or (
        value.get("state") == "refused" and value.get("prechild_refusal") is None
    )
    if child_result and any(
        value.get(key) is None for key in ("exit", "exit_capsule", "stdout", "stderr")
    ):
        raise ControllerRefusal("EVIDENCE_INCOMPLETE", "terminal result lacks child-exit evidence")
    if value.get("state") == "succeeded" and value.get("exit", {}).get("returncode") != 0:
        raise ControllerRefusal("EVIDENCE_INCOMPLETE", "success receipt has a nonzero or absent exit")
    if value.get("state") == "child_failed" and value.get("exit", {}).get("returncode") == 0:
        raise ControllerRefusal("EVIDENCE_INCOMPLETE", "child-failed receipt has a zero exit")
    _validate_receipt(value)
    expected_intent_binding = _binding(paths["intent"])
    if value.get("intent") != expected_intent_binding:
        raise ControllerRefusal("EVIDENCE_INCOMPLETE", "terminal intent-file binding is stale")
    for key in ("stdout", "stderr", "journal", "exit_capsule", "prechild_refusal", "child_attestation"):
        expected = value.get(key)
        if expected is None:
            continue
        path = Path(expected["path"])
        if not path.is_file() or _binding(path) != expected:
            raise ControllerRefusal("EVIDENCE_INCOMPLETE", f"terminal {key} binding is stale")
    try:
        intent = _validated_intent(paths["intent"])
    except ControllerRefusal as exc:
        raise ControllerRefusal("EVIDENCE_INCOMPLETE", f"terminal intent is invalid: {exc.message}") from exc
    if (
        value.get("request_sha256") != intent.get("request_sha256")
        or
        value.get("intent_sha256") != intent.get("intent_sha256")
        or value.get("argv") != intent.get("argv")
        or value.get("cwd") != intent.get("cwd")
        or value.get("environment_delta") != intent.get("environment_delta")
        or value.get("inputs") != intent.get("inputs")
        or value.get("input_roots") != intent.get("input_roots")
        or value.get("ignored_output_paths") != intent.get("ignored_output_paths")
        or value.get("controller_created_output_roots") != intent.get("controller_created_output_roots")
    ):
        raise ControllerRefusal("EVIDENCE_INCOMPLETE", "terminal intent binding is stale")
    owner = _read(paths["owner"]) if paths["owner"].is_file() else None
    owner_started_at = owner.get("started_at") if owner is not None else None
    if (
        value.get("worker") != owner
        or value.get("timestamps", {}).get("controller_started_at") != intent.get("created_at")
        or value.get("timestamps", {}).get("worker_started_at") != owner_started_at
    ):
        raise ControllerRefusal("EVIDENCE_INCOMPLETE", "terminal owner/timestamp binding is stale")
    if value.get("exit_capsule") is not None:
        capsule = _read(Path(value["exit_capsule"]["path"]))
        if (
            capsule.get("intent_sha256") != intent.get("intent_sha256")
            or value.get("exit") != {"returncode": capsule.get("returncode")}
            or value.get("process") != capsule.get("process")
            or value.get("stdout") != capsule.get("stdout")
            or value.get("stderr") != capsule.get("stderr")
            or capsule.get("supervisor_result") != (
                _binding(paths["supervisor_result"])
                if paths["supervisor_result"].is_file() else None
            )
            or value.get("timestamps", {}).get("child_started_at")
                != capsule.get("timestamps", {}).get("child_started_at")
            or value.get("timestamps", {}).get("child_exited_at")
                != capsule.get("timestamps", {}).get("child_exited_at")
        ):
            raise ControllerRefusal("EVIDENCE_INCOMPLETE", "terminal exit-capsule projection is stale")
    return value


class _WindowsProcessObservationApi:
    """Small injectable boundary for exact Windows process observation."""

    def __init__(self):
        import ctypes
        from ctypes import wintypes

        class FILETIME(ctypes.Structure):
            _fields_ = (("low", wintypes.DWORD), ("high", wintypes.DWORD))

        self.ctypes = ctypes
        self.FILETIME = FILETIME
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel32.OpenProcess.argtypes = (
            wintypes.DWORD, wintypes.BOOL, wintypes.DWORD,
        )
        self.kernel32.OpenProcess.restype = wintypes.HANDLE
        self.kernel32.GetProcessTimes.argtypes = (
            wintypes.HANDLE, ctypes.POINTER(FILETIME), ctypes.POINTER(FILETIME),
            ctypes.POINTER(FILETIME), ctypes.POINTER(FILETIME),
        )
        self.kernel32.GetProcessTimes.restype = wintypes.BOOL
        self.kernel32.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
        self.kernel32.WaitForSingleObject.restype = wintypes.DWORD
        self.kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        self.kernel32.CloseHandle.restype = wintypes.BOOL

    def open_process(self, pid: int) -> Any:
        self.ctypes.set_last_error(0)
        handle = self.kernel32.OpenProcess(0x100000 | 0x1000, False, pid)
        if not handle:
            raise self.ctypes.WinError(self.ctypes.get_last_error())
        return handle

    def wait(self, handle: Any) -> str:
        self.ctypes.set_last_error(0)
        result = self.kernel32.WaitForSingleObject(handle, 0)
        if result == 0:
            return "signaled"
        if result == 258:
            return "timeout"
        raise self.ctypes.WinError(self.ctypes.get_last_error())

    def creation_token(self, handle: Any) -> str:
        created = self.FILETIME()
        exited, kernel, user = self.FILETIME(), self.FILETIME(), self.FILETIME()
        self.ctypes.set_last_error(0)
        if not self.kernel32.GetProcessTimes(
            handle, self.ctypes.byref(created), self.ctypes.byref(exited),
            self.ctypes.byref(kernel), self.ctypes.byref(user),
        ):
            raise self.ctypes.WinError(self.ctypes.get_last_error())
        return str((created.high << 32) | created.low)

    def close(self, handle: Any) -> None:
        self.ctypes.set_last_error(0)
        if not self.kernel32.CloseHandle(handle):
            raise self.ctypes.WinError(self.ctypes.get_last_error())


def _windows_observation_refusal(operation: str, exc: Exception) -> ControllerRefusal:
    code = getattr(exc, "winerror", None)
    suffix = f"winerror={code}" if code is not None else str(exc)
    return ControllerRefusal(
        "RELEASE-CONTROLLER-PROCESS", f"Windows process {operation} failed: {suffix}",
    )


def _observe_windows_process(
    pid: int, *, api: Any | None = None,
) -> str | None:
    """Return the live creation token; only confirmed absence/signaling is dead."""
    try:
        boundary = api if api is not None else _WindowsProcessObservationApi()
    except Exception as exc:
        raise _windows_observation_refusal("API initialization", exc) from exc
    try:
        handle = boundary.open_process(pid)
    except Exception as exc:
        if getattr(exc, "winerror", None) == 87:  # ERROR_INVALID_PARAMETER
            return None
        raise _windows_observation_refusal("open", exc) from exc
    try:
        try:
            first_wait = boundary.wait(handle)
        except Exception as exc:
            raise _windows_observation_refusal("initial wait", exc) from exc
        if first_wait == "signaled":
            return None
        if first_wait != "timeout":
            raise ControllerRefusal(
                "RELEASE-CONTROLLER-PROCESS",
                f"Windows process initial wait returned {first_wait!r}",
            )
        try:
            token = boundary.creation_token(handle)
        except Exception as exc:
            raise _windows_observation_refusal("creation-time read", exc) from exc
        if not isinstance(token, str) or not token:
            raise ControllerRefusal(
                "RELEASE-CONTROLLER-PROCESS", "Windows process creation token is invalid",
            )
        try:
            second_wait = boundary.wait(handle)
        except Exception as exc:
            raise _windows_observation_refusal("post-read wait", exc) from exc
        if second_wait == "signaled":
            return None
        if second_wait != "timeout":
            raise ControllerRefusal(
                "RELEASE-CONTROLLER-PROCESS",
                f"Windows process post-read wait returned {second_wait!r}",
            )
        return token
    finally:
        try:
            boundary.close(handle)
        except Exception as exc:
            raise _windows_observation_refusal("handle close", exc) from exc


def _process_token(pid: int) -> str | None:
    if pid <= 0:
        return None
    if os.name == "nt":
        return _observe_windows_process(pid)
    try:
        stat_row = _parse_proc_stat(Path(f"/proc/{pid}/stat").read_text(encoding="ascii"))
        boot_id = Path("/proc/sys/kernel/random/boot_id").read_text(encoding="ascii").strip()
    except OSError:
        return None
    if (
        stat_row is None or stat_row["pid"] != pid
        or stat_row["state"] in {"Z", "X", "x"} or not boot_id
    ):
        return None
    return _proc_token(stat_row, boot_id)


def _parse_proc_stat(raw: str) -> dict[str, int | str] | None:
    opening = raw.find("(")
    closing = raw.rfind(")")
    if opening < 1 or closing <= opening:
        return None
    fields = raw[closing + 1:].strip().split()
    if len(fields) < 20:
        return None
    try:
        return {
            "pid": int(raw[:opening].strip()), "state": fields[0],
            "ppid": int(fields[1]), "pgrp": int(fields[2]),
            "session": int(fields[3]), "starttime": fields[19],
        }
    except ValueError:
        return None


def _proc_token(stat_row: Mapping[str, int | str], boot_id: str) -> str:
    return f"linux:{boot_id}:{stat_row['starttime']}"


def _proc_snapshot() -> tuple[str, dict[int, dict[str, int | str]]]:
    try:
        boot_id = Path("/proc/sys/kernel/random/boot_id").read_text(
            encoding="ascii",
        ).strip()
        entries = list(Path("/proc").iterdir())
    except OSError as exc:
        raise ControllerRefusal(
            "RELEASE-CONTROLLER-PROCESS", f"cannot observe /proc: {exc}",
        ) from exc
    if not boot_id:
        raise ControllerRefusal("RELEASE-CONTROLLER-PROCESS", "Linux boot identity is empty")
    rows: dict[int, dict[str, int | str]] = {}
    for entry in entries:
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        try:
            stat_row = _parse_proc_stat((entry / "stat").read_text(encoding="ascii"))
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise ControllerRefusal(
                "RELEASE-CONTROLLER-PROCESS", f"cannot observe /proc/{pid}/stat: {exc}",
            ) from exc
        if stat_row is not None and stat_row["pid"] == pid:
            stat_row["token"] = _proc_token(stat_row, boot_id)
            rows[pid] = stat_row
    return boot_id, rows


def _session_members(session: int, *, exclude: Iterable[int] = ()) -> dict[int, str]:
    if os.name == "nt":
        return {}
    excluded = set(exclude)
    _, snapshot = _proc_snapshot()
    return {
        pid: str(row["token"]) for pid, row in snapshot.items()
        if pid not in excluded and row["session"] == session
        and row["state"] not in {"Z", "X", "x"}
    }


def _descendant_ids(
    ancestor: int, snapshot: Mapping[int, Mapping[str, int | str]],
) -> set[int]:
    owned = {ancestor}
    changed = True
    while changed:
        changed = False
        for pid, row in snapshot.items():
            if pid not in owned and row["ppid"] in owned:
                owned.add(pid)
                changed = True
    owned.discard(ancestor)
    return owned


def _descendant_members(ancestor: int, *, exclude: Iterable[int] = ()) -> dict[int, str]:
    if os.name == "nt":
        return {}
    excluded = set(exclude)
    _, snapshot = _proc_snapshot()
    owned = _descendant_ids(ancestor, snapshot)
    return {
        pid: str(snapshot[pid]["token"]) for pid in owned
        if pid not in excluded and pid in snapshot
        and snapshot[pid]["state"] not in {"Z", "X", "x"}
    }


def _descendant_processes(ancestor: int) -> set[int]:
    if os.name == "nt":
        return set()
    _, snapshot = _proc_snapshot()
    return _descendant_ids(ancestor, snapshot)


def _signal_posix_identity(
    pid: int, token: str, signum: int, *, session_id: int | None = None,
    ancestor: int | None = None,
) -> None:
    try:
        descriptor = os.pidfd_open(pid)
    except ProcessLookupError:
        return
    except (AttributeError, OSError) as exc:
        raise ControllerRefusal(
            "RELEASE-CONTROLLER-PROCESS", f"pidfd_open failed for {pid}: {exc}",
    ) from exc
    try:
        _, snapshot = _proc_snapshot()
        row = snapshot.get(pid)
        membership_valid = (
            session_id is not None and row is not None and row["session"] == session_id
        ) or (
            ancestor is not None and pid in _descendant_ids(ancestor, snapshot)
        )
        if row is None or row["state"] in {"Z", "X", "x"}:
            return
        if (
            str(row["token"]) != token or not membership_valid
        ):
            raise ControllerRefusal(
                "RELEASE-CONTROLLER-PROCESS",
                f"POSIX process {pid} changed identity or membership before signal",
            )
        try:
            signal.pidfd_send_signal(descriptor, signum)
        except ProcessLookupError:
            pass
        except (AttributeError, OSError) as exc:
            raise ControllerRefusal(
                "RELEASE-CONTROLLER-PROCESS", f"pidfd signal failed for {pid}: {exc}",
            ) from exc
    finally:
        try:
            os.close(descriptor)
        except OSError as exc:
            raise ControllerRefusal(
                "RELEASE-CONTROLLER-PROCESS", f"pidfd close failed for {pid}: {exc}",
            ) from exc


def _signal_session(
    session: int, identities: Mapping[int, str], signum: int,
) -> None:
    for pid, token in identities.items():
        _signal_posix_identity(pid, token, signum, session_id=session)


def _signal_descendants(
    ancestor: int, identities: Mapping[int, str], signum: int,
) -> None:
    for pid, token in identities.items():
        _signal_posix_identity(pid, token, signum, ancestor=ancestor)


def _alive(owner: Mapping[str, Any]) -> bool:
    token = owner.get("process_token")
    if owner.get("host") != platform.node() or not isinstance(owner.get("pid"), int):
        return False
    if not isinstance(token, str) or not token or token == "unavailable":
        return False
    observed = _process_token(owner["pid"])
    return observed is not None and observed == token


_WINDOWS_JOB_API: tuple[Any, Any, Any] | None = None


def _windows_job_api() -> tuple[Any, Any, Any]:
    global _WINDOWS_JOB_API
    if os.name != "nt":
        raise ControllerRefusal("RELEASE-CONTROLLER-PROCESS", "Windows Job API requested off Windows")
    if _WINDOWS_JOB_API is not None:
        return _WINDOWS_JOB_API
    import ctypes
    from ctypes import wintypes

    class BasicLimit(ctypes.Structure):
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

    class IoCounters(ctypes.Structure):
        _fields_ = tuple(
            (name, ctypes.c_ulonglong) for name in (
                "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                "ReadTransferCount", "WriteTransferCount", "OtherTransferCount",
            )
        )

    class ExtendedLimit(ctypes.Structure):
        _fields_ = (
            ("BasicLimitInformation", BasicLimit),
            ("IoInfo", IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        )

    class BasicAccounting(ctypes.Structure):
        _fields_ = (
            ("TotalUserTime", ctypes.c_longlong),
            ("TotalKernelTime", ctypes.c_longlong),
            ("ThisPeriodTotalUserTime", ctypes.c_longlong),
            ("ThisPeriodTotalKernelTime", ctypes.c_longlong),
            ("TotalPageFaultCount", wintypes.DWORD),
            ("TotalProcesses", wintypes.DWORD),
            ("ActiveProcesses", wintypes.DWORD),
            ("TotalTerminatedProcesses", wintypes.DWORD),
        )

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.SetInformationJobObject.argtypes = (
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
    )
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel32.IsProcessInJob.argtypes = (
        wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL),
    )
    kernel32.IsProcessInJob.restype = wintypes.BOOL
    kernel32.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
    kernel32.TerminateJobObject.restype = wintypes.BOOL
    kernel32.QueryInformationJobObject.argtypes = (
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    )
    kernel32.QueryInformationJobObject.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.ResumeThread.argtypes = (wintypes.HANDLE,)
    kernel32.ResumeThread.restype = wintypes.DWORD
    _WINDOWS_JOB_API = kernel32, ExtendedLimit, BasicAccounting
    return _WINDOWS_JOB_API


def _windows_process_in_any_job(process_handle: int) -> bool:
    import ctypes
    from ctypes import wintypes

    kernel32, _, _ = _windows_job_api()
    result = wintypes.BOOL()
    ctypes.set_last_error(0)
    if not kernel32.IsProcessInJob(
        wintypes.HANDLE(process_handle), None, ctypes.byref(result),
    ):
        raise _WindowsDurabilityRefusal(
            f"IsProcessInJob failed: {ctypes.WinError(ctypes.get_last_error())}",
        )
    return bool(result.value)


def _windows_escape_creation_flag(in_job: bool, limit_flags: int | None) -> int:
    if not in_job:
        return 0
    if limit_flags is None:
        raise _WindowsDurabilityRefusal(
            "detached Windows worker cannot inspect its enclosing Job limits",
        )
    if limit_flags & 0x1000:  # JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK
        return 0
    if limit_flags & 0x0800:  # JOB_OBJECT_LIMIT_BREAKAWAY_OK
        return 0x01000000  # CREATE_BREAKAWAY_FROM_JOB
    raise _WindowsDurabilityRefusal(
        "detached Windows worker cannot escape the enclosing Job",
    )


def _windows_worker_creation_flag() -> int:
    import _winapi
    import ctypes
    from ctypes import wintypes

    if not _windows_process_in_any_job(int(_winapi.GetCurrentProcess())):
        return 0
    kernel32, ExtendedLimit, _ = _windows_job_api()
    limits = ExtendedLimit()
    returned = wintypes.DWORD()
    ctypes.set_last_error(0)
    if not kernel32.QueryInformationJobObject(
        None, 9, ctypes.byref(limits), ctypes.sizeof(limits), ctypes.byref(returned),
    ):
        raise _WindowsDurabilityRefusal(
            f"cannot inspect enclosing Windows Job: "
            f"{ctypes.WinError(ctypes.get_last_error())}",
        )
    return _windows_escape_creation_flag(
        True, int(limits.BasicLimitInformation.LimitFlags),
    )


class _WindowsJob:
    def __init__(self, handle: int | None = None, *, limit_flags: int = 0x2000):
        import ctypes

        kernel32, ExtendedLimit, _ = _windows_job_api()
        self.handle = int(handle or 0)
        if self.handle:
            return
        created = kernel32.CreateJobObjectW(None, None)
        if not created:
            raise ControllerRefusal(
                "RELEASE-CONTROLLER-PROCESS", f"CreateJobObjectW failed: {ctypes.WinError(ctypes.get_last_error())}",
            )
        self.handle = int(created)
        limits = ExtendedLimit()
        limits.BasicLimitInformation.LimitFlags = limit_flags
        if not kernel32.SetInformationJobObject(
            self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits),
        ):
            error = ctypes.WinError(ctypes.get_last_error())
            self.close()
            raise ControllerRefusal("RELEASE-CONTROLLER-PROCESS", f"SetInformationJobObject failed: {error}")

    def duplicate_inheritable(self) -> int:
        import _winapi

        current = _winapi.GetCurrentProcess()
        return int(_winapi.DuplicateHandle(
            current, self.handle, current, 0, True, _winapi.DUPLICATE_SAME_ACCESS,
        ))

    def assign(self, process_handle: int) -> None:
        import ctypes

        kernel32, _, _ = _windows_job_api()
        if not kernel32.AssignProcessToJobObject(self.handle, process_handle):
            raise ControllerRefusal(
                "RELEASE-CONTROLLER-PROCESS",
                f"AssignProcessToJobObject failed: {ctypes.WinError(ctypes.get_last_error())}",
            )

    def active_processes(self) -> int:
        import ctypes
        from ctypes import wintypes

        kernel32, _, BasicAccounting = _windows_job_api()
        accounting = BasicAccounting()
        returned = wintypes.DWORD()
        if not kernel32.QueryInformationJobObject(
            self.handle, 1, ctypes.byref(accounting), ctypes.sizeof(accounting), ctypes.byref(returned),
        ):
            raise ControllerRefusal(
                "RELEASE-CONTROLLER-PROCESS",
                f"QueryInformationJobObject failed: {ctypes.WinError(ctypes.get_last_error())}",
            )
        return int(accounting.ActiveProcesses)

    def terminate(self, exit_code: int = 1223) -> None:
        import ctypes

        kernel32, _, _ = _windows_job_api()
        if self.active_processes() and not kernel32.TerminateJobObject(self.handle, exit_code):
            raise ControllerRefusal(
                "RELEASE-CONTROLLER-PROCESS",
                f"TerminateJobObject failed: {ctypes.WinError(ctypes.get_last_error())}",
            )

    def wait_empty(self, timeout_s: float = 30.0) -> None:
        deadline = time.monotonic() + timeout_s
        while self.active_processes():
            if time.monotonic() >= deadline:
                raise ControllerRefusal("RELEASE-CONTROLLER-LIVE", "Windows Job did not become empty")
            time.sleep(.01)

    def close(self) -> None:
        if not self.handle:
            return
        import ctypes

        kernel32, _, _ = _windows_job_api()
        if not kernel32.CloseHandle(self.handle):
            raise ControllerRefusal(
                "RELEASE-CONTROLLER-PROCESS",
                f"CloseHandle(Job) failed: {ctypes.WinError(ctypes.get_last_error())}",
            )
        self.handle = 0


class _WindowsProcess:
    def __init__(self, handle: int, pid: int):
        self._handle = int(handle)
        self.pid = int(pid)
        self.returncode: int | None = None

    def poll(self) -> int | None:
        if self.returncode is not None:
            return self.returncode
        import _winapi

        wait = _winapi.WaitForSingleObject(self._handle, 0)
        if wait == 0xFFFFFFFF:
            raise ControllerRefusal("RELEASE-CONTROLLER-PROCESS", "WaitForSingleObject failed")
        if wait != _winapi.WAIT_OBJECT_0:
            return None
        self.returncode = int(_winapi.GetExitCodeProcess(self._handle))
        self.close()
        return self.returncode

    def wait(self, timeout: float | None = None) -> int:
        if self.returncode is not None:
            return self.returncode
        import _winapi

        milliseconds = _winapi.INFINITE if timeout is None else max(0, int(timeout * 1000))
        wait = _winapi.WaitForSingleObject(self._handle, milliseconds)
        if wait == 0xFFFFFFFF:
            raise ControllerRefusal("RELEASE-CONTROLLER-PROCESS", "WaitForSingleObject failed")
        if wait != _winapi.WAIT_OBJECT_0:
            raise subprocess.TimeoutExpired(["owned-process"], timeout)
        self.returncode = int(_winapi.GetExitCodeProcess(self._handle))
        self.close()
        return self.returncode

    def close(self) -> None:
        if not self._handle:
            return
        import _winapi

        handle, self._handle = self._handle, 0
        _winapi.CloseHandle(handle)


def _spawn_windows_job_process(
    argv: list[str], *, cwd: str | Path, environment: Mapping[str, str],
    stdin: Any, stdout: Any, stderr: Any, job: _WindowsJob,
    extra_inherited_handles: Iterable[int] = (), creation_flags: int = 0,
    require_no_enclosing_job: bool = False,
) -> _WindowsProcess:
    import _winapi
    import ctypes
    import msvcrt

    current = _winapi.GetCurrentProcess()
    duplicates: list[int] = []
    try:
        for stream in (stdin, stdout, stderr):
            duplicates.append(int(_winapi.DuplicateHandle(
                current, msvcrt.get_osfhandle(stream.fileno()), current, 0, True,
                _winapi.DUPLICATE_SAME_ACCESS,
            )))
    except Exception:
        for handle in duplicates:
            _winapi.CloseHandle(handle)
        raise
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= _winapi.STARTF_USESTDHANDLES
    startup.hStdInput, startup.hStdOutput, startup.hStdError = duplicates
    inherited = [*duplicates, *map(int, extra_inherited_handles)]
    startup.lpAttributeList = {"handle_list": inherited}
    process_handle = thread_handle = None
    try:
        process_handle, thread_handle, pid, _ = _winapi.CreateProcess(
            None, subprocess.list2cmdline(argv), None, None, True,
            0x4 | 0x200 | 0x400 | creation_flags,
            dict(environment), str(Path(cwd).resolve()), startup,
        )
        try:
            if require_no_enclosing_job and _windows_process_in_any_job(
                int(process_handle),
            ):
                raise _WindowsDurabilityRefusal(
                    "detached Windows worker remains in an enclosing Job",
                )
            job.assign(int(process_handle))
            kernel32, _, _ = _windows_job_api()
            if kernel32.ResumeThread(int(thread_handle)) == 0xFFFFFFFF:
                raise ControllerRefusal(
                    "RELEASE-CONTROLLER-PROCESS",
                    f"ResumeThread failed: {ctypes.WinError(ctypes.get_last_error())}",
                )
        except Exception:
            _winapi.TerminateProcess(process_handle, 1223)
            _winapi.WaitForSingleObject(process_handle, _winapi.INFINITE)
            _winapi.CloseHandle(process_handle)
            process_handle = None
            raise
        return _WindowsProcess(int(process_handle), int(pid))
    finally:
        if thread_handle is not None:
            _winapi.CloseHandle(thread_handle)
        for handle in duplicates:
            _winapi.CloseHandle(handle)


def _inside(path: str | Path, root: str | Path) -> bool:
    child = os.path.normcase(os.path.realpath(os.fspath(path)))
    parent = os.path.normcase(os.path.realpath(os.fspath(root)))
    return child == parent or child.startswith(parent + os.sep)


def _lexical(path: str | Path) -> str:
    return os.path.abspath(os.fspath(path))


def _is_reparse(path: Path) -> bool:
    details = os.lstat(path)
    attributes = getattr(details, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(details.st_mode) or bool(attributes & reparse_flag)


def _is_registered_same_repository_worktree(path: str | Path) -> bool:
    """Return whether *path* is one exact worktree of this Git repository.

    This grants read-only inventory authority only.  Callers must first let the
    destination capability decide whether the path is writable; a protected
    watch root may use this predicate only to recover observation authority.
    """
    candidate = Path(path)
    try:
        if _is_reparse(candidate):
            raise ControllerRefusal(
                "RELEASE-CONTROLLER-OUTPUT-TOPOLOGY",
                f"watch root is a reparse point: {candidate}",
            )
        resolved = candidate.resolve(strict=True)
        registered = [
            root.resolve(strict=True) for root in registered_worktree_roots(ROOT)
        ]
        if registered.count(resolved) != 1:
            return False
        source_common = git_common_dir(ROOT).resolve(strict=True)
        watched_common = git_common_dir(resolved).resolve(strict=True)
    except ControllerRefusal:
        raise
    except Exception as exc:
        raise ControllerRefusal(
            "RELEASE-CONTROLLER-OUTPUT-TOPOLOGY",
            f"cannot prove registered worktree observation authority for {candidate}: {exc}",
        ) from exc
    return watched_common == source_common


def _validate_existing_watch_root(path: str | Path) -> None:
    """Prove one existing root is writable or observation-only registered."""
    candidate = Path(path)
    if not candidate.is_dir() or _is_reparse(candidate):
        raise ControllerRefusal(
            "RELEASE-CONTROLLER-OUTPUT-TOPOLOGY",
            f"watch root is not one existing non-reparse directory: {candidate}",
        )
    try:
        assert_writable(candidate, purpose="release qualification watched output")
    except DestinationRefused as exc:
        if exc.code != DEST_PROTECTED:
            raise ControllerRefusal(exc.code, str(exc)) from exc
        if not _is_registered_same_repository_worktree(candidate):
            raise ControllerRefusal(
                "RELEASE-CONTROLLER-OUTPUT-TOPOLOGY",
                f"protected watch root is not one exact registered worktree "
                f"of the controller repository: {candidate}",
            ) from exc


def _validate_existing_watch_roots(paths: Iterable[str | Path]) -> None:
    for path in paths:
        _validate_existing_watch_root(path)


def _validate_ignored_output_path(
    path: str | Path, watched_roots: Iterable[str | Path],
) -> None:
    """Validate one exact ignored file without masking protected worktree data."""
    candidate = Path(path)
    try:
        containing = [
            Path(root).resolve(strict=True) for root in watched_roots
            if _inside(candidate, root)
        ]
    except OSError as exc:
        raise ControllerRefusal(
            "RELEASE-CONTROLLER-OUTPUT-TOPOLOGY",
            f"cannot resolve ignored-output watch topology for {candidate}: {exc}",
        ) from exc
    try:
        regular_file = candidate.is_file()
        candidate_reparse = _is_reparse(candidate) if regular_file else False
    except OSError as exc:
        raise ControllerRefusal(
            "RELEASE-CONTROLLER-OUTPUT-TOPOLOGY",
            f"cannot inspect ignored-output identity for {candidate}: {exc}",
        ) from exc
    if not regular_file or candidate_reparse or not containing:
        raise ControllerRefusal(
            "RELEASE-CONTROLLER-OUTPUT-TOPOLOGY",
            f"ignored output must be one existing regular file inside a watch root: {candidate}",
        )
    try:
        assert_writable(candidate, purpose="release qualification ignored output")
    except DestinationRefused as exc:
        if exc.code != DEST_PROTECTED:
            raise ControllerRefusal(exc.code, str(exc)) from exc
        root = max(containing, key=lambda item: len(item.parts))
        if not _is_registered_same_repository_worktree(root):
            raise ControllerRefusal(
                "RELEASE-CONTROLLER-OUTPUT-TOPOLOGY",
                f"ignored output watch root lost registered-worktree authority: {root}",
            ) from exc
        try:
            permitted = (git_common_dir(root) / _SHARED_RUNNER_LOCK).resolve(strict=True)
            resolved = candidate.resolve(strict=True)
        except Exception as discovery_exc:
            raise ControllerRefusal(
                "RELEASE-CONTROLLER-OUTPUT-TOPOLOGY",
                f"cannot bind protected ignored output {candidate}: {discovery_exc}",
            ) from discovery_exc
        if resolved != permitted:
            raise ControllerRefusal(
                "RELEASE-CONTROLLER-OUTPUT-TOPOLOGY",
                f"protected watch roots may ignore only the exact shared runner lock: {candidate}",
            ) from exc


def _inventory(
    roots: Iterable[str | Path], excluded: Path,
    *, ignored_paths: Iterable[str | Path] = (), exclude_root_git: bool = False,
) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    ignored = {_lexical(path) for path in ignored_paths}
    for raw_root in roots:
        root = Path(raw_root).resolve(strict=True)
        if not root.is_dir():
            raise ControllerRefusal("RELEASE-CONTROLLER-OUTPUT-SCOPE", f"watch root is not a directory: {root}")
        for base, dirs, files in os.walk(root):
            base_path = Path(base)
            retained = []
            for name in sorted(dirs):
                path = base_path / name
                if exclude_root_git and base_path == root and name == ".git":
                    continue
                if _inside(path, excluded):
                    continue
                key = _lexical(path)
                if _is_reparse(path):
                    rows[key] = {"kind": "reparse_directory"}
                    continue
                rows[key] = {"kind": "directory"}
                retained.append(name)
            dirs[:] = retained
            for name in sorted(files):
                path = base_path / name
                if _inside(path, excluded):
                    continue
                try:
                    key = _lexical(path)
                    if key in ignored and not _is_reparse(path):
                        continue
                    if _is_reparse(path):
                        rows[key] = {"kind": "reparse_file"}
                    else:
                        rows[key] = {
                            "kind": "file", "sha256": _sha_file(path),
                            "byte_length": path.stat().st_size,
                        }
                except OSError as exc:
                    raise ControllerRefusal("RELEASE-CONTROLLER-OUTPUT-SCOPE", str(exc)) from exc
    return rows


def _reparse_rows(inventory: Mapping[str, Mapping[str, Any]]) -> list[str]:
    return sorted(path for path, row in inventory.items() if str(row.get("kind", "")).startswith("reparse_"))


def _inputs(paths: Iterable[str | Path]) -> list[dict[str, Any]]:
    rows = []
    for raw in paths:
        lexical = Path(raw).absolute()
        try:
            path = lexical.resolve(strict=True)
        except OSError as exc:
            raise ControllerRefusal(
                "RELEASE-CONTROLLER-INPUT", f"input is unavailable: {lexical}"
            ) from exc
        if not path.is_file() or _is_reparse(lexical):
            raise ControllerRefusal("RELEASE-CONTROLLER-INPUT", f"input is not a regular file: {lexical}")
        rows.append(_binding(path))
    return sorted(rows, key=lambda row: row["path"])


def _input_root_binding(
    raw: str | Path, *, ignored_paths: Iterable[str | Path] = (),
) -> dict[str, Any]:
    lexical = Path(raw).absolute()
    if not lexical.exists() or _is_reparse(lexical):
        raise ControllerRefusal("RELEASE-CONTROLLER-INPUT", f"input root is unavailable or reparse: {lexical}")
    root = lexical.resolve(strict=True)
    if not root.is_dir():
        raise ControllerRefusal("RELEASE-CONTROLLER-INPUT", f"input root is not a directory: {root}")
    inventory = _inventory(
        [root], root / ".controller-excluded-impossible",
        ignored_paths=ignored_paths, exclude_root_git=True,
    )
    reparse = _reparse_rows(inventory)
    if reparse:
        raise ControllerRefusal("RELEASE-CONTROLLER-INPUT", "input root contains reparse entries: " + ", ".join(reparse))
    return {
        "path": str(root), "entry_count": len(inventory),
        "inventory_sha256": _sha_bytes(_canonical(inventory)), "inventory": inventory,
    }


def _input_roots(
    paths: Iterable[str | Path], *, ignored_paths: Iterable[str | Path] = (),
) -> list[dict[str, Any]]:
    ignored = tuple(ignored_paths)
    return sorted(
        (_input_root_binding(path, ignored_paths=ignored) for path in paths),
        key=lambda row: row["path"],
    )


def _dependency_paths() -> tuple[str, ...]:
    candidates = [*site.getsitepackages(), site.getusersitepackages()]
    return tuple(sorted({str(Path(path).resolve()) for path in candidates if path and Path(path).is_dir()}))


def _paths(run_root: str | Path, run_id: str) -> dict[str, Path]:
    if not RUN_ID.fullmatch(run_id):
        raise ControllerRefusal("RELEASE-CONTROLLER-RUN-ID", "unsafe run id")
    root = Path(run_root).resolve() / run_id
    return {name: root / filename for name, filename in {
        "root": ".", "intent": "intent.json", "journal": "journal.json", "owner": "owner.json",
        "stdout": "stdout.bin", "stderr": "stderr.bin", "exit": "exit.json",
        "receipt": "receipt.json", "cancel": "cancel.request.json",
        "prechild": "prechild-refusal.json", "attestation": "child-attestation.json",
        "lock": ".controller.lock", "direct_exit": "direct-exit.json",
        "product_started": "product-started.json", "supervisor_result": "supervisor-result.json",
        "test_preflight_gate": ".test-preflight-gate",
        "worker_stdout": "worker-stdout.bin", "worker_stderr": "worker-stderr.bin",
    }.items()} | {"root": root}


def _event(paths: Mapping[str, Path], state: str, event: str, **extra: Any) -> dict[str, Any]:
    journal = _read(paths["journal"])
    journal["state"] = state
    journal["events"].append({"at": _now(), "event": event, **extra})
    _atomic(paths["journal"], _canonical(journal))
    return journal


def _check_argv(argv: list[str]) -> None:
    if not argv or not all(isinstance(item, str) and item for item in argv):
        raise ControllerRefusal("RELEASE-CONTROLLER-ARGV", "argv must contain nonempty text entries")
    if any(item in {"-O", "-OO"} for item in argv[1:]):
        raise ControllerRefusal("RELEASE-CONTROLLER-ENV", "Python optimization flags are forbidden")


def _spawn_worker_process(
    paths: Mapping[str, Path], worker_env: Mapping[str, str],
    worker_stdout: Any, worker_stderr: Any, *, detached: bool,
) -> tuple[Any, _WindowsJob | None]:
    argv = [sys.executable, str(Path(__file__).resolve()), "_worker", "--run-dir", str(paths["root"])]
    if os.name != "nt":
        return subprocess.Popen(
            argv, stdin=subprocess.DEVNULL, stdout=worker_stdout, stderr=worker_stderr,
            close_fds=True, env=dict(worker_env), start_new_session=detached,
        ), None
    import _winapi

    creation_flags = _windows_worker_creation_flag() if detached else 0
    supervisor = _WindowsJob()
    inherited = supervisor.duplicate_inheritable()
    exact_env = dict(worker_env)
    exact_env[_SUPERVISOR_JOB_ENV] = str(inherited)
    try:
        with open(os.devnull, "rb") as devnull:
            worker = _spawn_windows_job_process(
                argv, cwd=Path.cwd(), environment=exact_env,
                stdin=devnull, stdout=worker_stdout, stderr=worker_stderr,
                job=supervisor, extra_inherited_handles=[inherited],
                creation_flags=creation_flags,
                require_no_enclosing_job=detached,
            )
    except Exception:
        supervisor.close()
        raise
    finally:
        _winapi.CloseHandle(inherited)
    return worker, supervisor


def _spawn_product_process(
    argv: list[str], *, cwd: str | Path, environment: Mapping[str, str],
    stdout: Any, stderr: Any, run_dir: Path,
) -> tuple[Any, _WindowsJob | None, int | None]:
    if os.name != "nt":
        read_fd, write_fd = os.pipe()
        os.set_inheritable(read_fd, True)
        try:
            supervisor = subprocess.Popen(
                [
                    sys.executable, str(Path(__file__).resolve()), "_posix_supervisor",
                    "--run-dir", str(run_dir), "--control-fd", str(read_fd),
                ],
                cwd=cwd, env=dict(environment), stdin=subprocess.DEVNULL,
                stdout=stdout, stderr=stderr, close_fds=True,
                pass_fds=(read_fd,), start_new_session=True,
            )
        except Exception:
            os.close(write_fd)
            raise
        finally:
            os.close(read_fd)
        return supervisor, None, write_fd
    product_job = _WindowsJob()
    try:
        with open(os.devnull, "rb") as devnull:
            child = _spawn_windows_job_process(
                argv, cwd=cwd, environment=environment,
                stdin=devnull, stdout=stdout, stderr=stderr, job=product_job,
            )
    except Exception:
        product_job.close()
        raise
    return child, product_job, None


def _terminate_posix_session(
    session: int, *, leader_pid: int, leader_token: str, timeout_s: float = 30.0,
) -> None:
    if os.name == "nt":
        raise ControllerRefusal("RELEASE-CONTROLLER-PROCESS", "POSIX session requested on Windows")
    members = _session_members(session)
    if _process_token(leader_pid) != leader_token:
        if members:
            raise ControllerRefusal(
                "RELEASE-CONTROLLER-PROCESS",
                "recorded POSIX leader token changed while its session remains active",
            )
        return
    _terminate_session_members(session, timeout_s=timeout_s)


def _terminate_session_members(
    session: int, *, exclude: Iterable[int] = (), timeout_s: float = 30.0,
) -> None:
    excluded = set(exclude)
    members = _session_members(session, exclude=excluded)
    _signal_session(session, members, signal.SIGTERM)
    grace = time.monotonic() + .2
    while _session_members(session, exclude=excluded) and time.monotonic() < grace:
        time.sleep(.01)
    deadline = time.monotonic() + timeout_s
    while True:
        members = _session_members(session, exclude=excluded)
        if not members:
            return
        _signal_session(session, members, signal.SIGKILL)
        if time.monotonic() >= deadline:
            raise ControllerRefusal("RELEASE-CONTROLLER-LIVE", "POSIX session members did not disappear")
        time.sleep(.01)


def _terminate_descendants(ancestor: int, *, timeout_s: float = 30.0) -> None:
    members = _descendant_members(ancestor)
    if members:
        _signal_descendants(ancestor, members, signal.SIGTERM)
    grace = time.monotonic() + .2
    while time.monotonic() < grace:
        _reap_children()
        if not _descendant_processes(ancestor):
            break
        time.sleep(.01)
    deadline = time.monotonic() + timeout_s
    empty_scans = 0
    while empty_scans < 2:
        _reap_children()
        members = _descendant_members(ancestor)
        if not _descendant_processes(ancestor):
            empty_scans += 1
            time.sleep(.01)
            continue
        empty_scans = 0
        if members:
            _signal_descendants(ancestor, members, signal.SIGKILL)
        if time.monotonic() >= deadline:
            raise ControllerRefusal(
                "RELEASE-CONTROLLER-LIVE", "owned POSIX descendants did not disappear",
            )
        time.sleep(.01)


def _recorded_child(paths: Mapping[str, Path]) -> dict[str, Any] | None:
    if not paths["journal"].is_file():
        return None
    journal = _read(paths["journal"])
    for row in reversed(journal.get("events", [])):
        if row.get("event") != "child_spawned":
            continue
        if (
            isinstance(row.get("child_pid"), int)
            and isinstance(row.get("process_group"), int)
            and isinstance(row.get("process_token"), str)
        ):
            return row
        return None
    return None


def _quiesce_recorded_child(paths: Mapping[str, Path], timeout_s: float = 30.0) -> None:
    recorded = _recorded_child(paths)
    if recorded is None:
        return
    pid, token, group = (
        recorded["child_pid"], recorded["process_token"], recorded["process_group"],
    )
    deadline = time.monotonic() + timeout_s
    if os.name == "nt":
        # Closing the worker's last supervisor-Job handle is the primary crash
        # shield.  Wait for that asynchronous kill, then use the exact creation
        # token only as a bounded recovery fallback.
        while _process_token(pid) == token and time.monotonic() < deadline:
            time.sleep(.01)
        if _process_token(pid) == token:
            raise ControllerRefusal(
                "RELEASE-CONTROLLER-LIVE",
                "recorded Windows product tree remains active after supervisor Job closure",
            )
        return
    _terminate_posix_session(
        group, leader_pid=pid, leader_token=token, timeout_s=timeout_s,
    )


def start_run(
    *, run_root: str | Path, run_id: str, argv: Iterable[str], cwd: str | Path,
    environment_delta: Mapping[str, str | None] | None = None,
    input_paths: Iterable[str | Path] = (), input_roots: Iterable[str | Path] = (),
    allowed_output_roots: Iterable[str | Path] = (), output_watch_roots: Iterable[str | Path] = (),
    ignored_output_paths: Iterable[str | Path] = (), detached: bool = True,
    allow_user_site: bool = False, child_attestation: bool = False,
    _test_fault: str | None = None,
) -> dict[str, Any]:
    assert_ambient_clean()
    command = list(argv)
    _check_argv(command)
    cwd_path = Path(cwd).resolve(strict=True)
    if not cwd_path.is_dir():
        raise ControllerRefusal("RELEASE-CONTROLLER-CWD", "cwd is not a directory")
    paths = _paths(run_root, run_id)
    assert_writable(paths["root"], purpose="release qualification evidence")
    dependencies = _dependency_paths()
    _, recorded_delta = controlled_environment(
        delta=environment_delta,
        dependency_paths=None if allow_user_site else dependencies,
        allow_user_site=allow_user_site,
    )
    allowed_candidates = [Path(path) for path in allowed_output_roots]
    watched_candidates = [Path(path) for path in output_watch_roots]
    for candidate in watched_candidates:
        try:
            os.lstat(candidate)
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise ControllerRefusal(
                "RELEASE-CONTROLLER-OUTPUT-TOPOLOGY",
                f"cannot inspect watch-root topology for {candidate}: {exc}",
            ) from exc
        if _is_reparse(candidate):
            raise ControllerRefusal(
                "RELEASE-CONTROLLER-OUTPUT-TOPOLOGY",
                f"watch root is a reparse point: {candidate}",
            )
    allowed = sorted({str(path.resolve()) for path in allowed_candidates})
    watched = sorted({str(path.resolve()) for path in watched_candidates})
    if any(not any(_inside(path, root) for root in watched) for path in allowed):
        raise ControllerRefusal(
            "RELEASE-CONTROLLER-OUTPUT-TOPOLOGY",
            "every allowed output root must be contained by a watched root",
        )
    for path in allowed:
        assert_writable(path, purpose="release qualification allowed output")
    created_watch_roots: list[str] = []
    for path in watched:
        if Path(path).exists():
            _validate_existing_watch_root(path)
        else:
            assert_writable(path, purpose="release qualification watched output")
            if not any(_inside(path, root) for root in allowed):
                raise ControllerRefusal(
                    "RELEASE-CONTROLLER-OUTPUT-TOPOLOGY",
                    f"missing watch root is not an allowed output: {path}",
                )
            Path(path).mkdir(parents=True, exist_ok=False)
            created_watch_roots.append(path)
        if not Path(path).is_dir():
            raise ControllerRefusal("RELEASE-CONTROLLER-OUTPUT-TOPOLOGY", f"watch root is not a directory: {path}")
    if not watched or not any(_inside(cwd_path, root) for root in watched):
        raise ControllerRefusal(
            "RELEASE-CONTROLLER-OUTPUT-TOPOLOGY",
            "cwd must be contained by an explicit output watch root",
        )
    ignored = sorted({str(Path(path).resolve(strict=True)) for path in ignored_output_paths})
    for path in ignored:
        _validate_ignored_output_path(path, watched)
    request_core = {
        "schema_version": "1.0.0", "run_id": run_id, "argv": command, "cwd": str(cwd_path),
        "environment_delta": recorded_delta, "inputs": _inputs(input_paths),
        "input_roots": _input_roots(input_roots, ignored_paths=ignored),
        "allowed_output_roots": allowed, "output_watch_roots": watched,
        "ignored_output_paths": ignored, "allow_user_site": allow_user_site,
        "child_attestation": child_attestation, "test_fault": _test_fault,
    }
    request_sha = _sha_bytes(_canonical(request_core))

    def existing_result() -> dict[str, Any]:
        for _ in range(200):
            if paths["intent"].is_file():
                break
            time.sleep(0.01)
        existing = _validated_intent(paths["intent"])
        comparable = _request_identity(existing)
        if comparable != request_core or existing.get("request_sha256") != request_sha:
            raise ControllerRefusal("RELEASE-CONTROLLER-INTENT-CONFLICT", "run id is bound to different intent")
        return {**status_run(run_root=run_root, run_id=run_id), "idempotent": True}

    if paths["root"].exists():
        return existing_result()
    output_preimage = _inventory(watched, paths["root"], ignored_paths=ignored)
    reparse = _reparse_rows(output_preimage)
    if reparse:
        raise ControllerRefusal(
            "RELEASE-CONTROLLER-OUTPUT-TOPOLOGY",
            "watched outputs contain reparse entries: " + ", ".join(reparse),
        )
    paths["root"].parent.mkdir(parents=True, exist_ok=True)
    try:
        paths["root"].mkdir(exist_ok=False)
    except FileExistsError:
        return existing_result()
    exact_environment_delta = dict(recorded_delta)
    attestation_token: str | None = None
    if child_attestation:
        attestation_token = secrets.token_hex(32)
        exact_environment_delta.update({
            _ATTESTATION_ENV[0]: str(paths["root"]),
            _ATTESTATION_ENV[1]: attestation_token,
        })
    intent_without_digest = {
        **request_core, "environment_delta": exact_environment_delta,
        "request_sha256": request_sha,
        "output_preimage": output_preimage,
        "controller_created_output_roots": created_watch_roots,
        "created_at": _now(),
    }
    intent_sha = _sha_bytes(_canonical(intent_without_digest))
    intent = {**intent_without_digest, "intent_sha256": intent_sha}
    _atomic(paths["intent"], _canonical(intent))
    _atomic(paths["journal"], _canonical({
        "schema_version": "1.0.0", "run_id": run_id, "intent_sha256": intent_sha,
        "state": "starting", "events": [{"at": _now(), "event": "intent_committed"}],
    }))
    if child_attestation and attestation_token is not None:
        _atomic(paths["attestation"], _canonical({
            "schema_version": "1.0.0", "run_id": run_id,
            "intent_sha256": intent_sha, "token_sha256": _sha_bytes(attestation_token.encode("ascii")),
            "state": "issued", "issued_at": _now(),
        }))
    worker_env, _ = controlled_environment(
        delta={"COAUTHOR_RELEASE_CONTROLLER_WORKER": "1"}, dependency_paths=dependencies
    )
    worker = None
    supervisor_job = None
    try:
        with paths["worker_stdout"].open("xb") as worker_stdout, paths["worker_stderr"].open("xb") as worker_stderr:
            worker, supervisor_job = _spawn_worker_process(
                paths, worker_env, worker_stdout, worker_stderr, detached=detached,
            )
    except _WindowsDurabilityRefusal as exc:
        _atomic(paths["prechild"], _canonical({
            "schema_version": "1.0.0", "intent_sha256": intent_sha,
            "refused_at": _now(), "diagnostic": {
                "code": exc.code, "detail": exc.message,
            },
        }))
        _event(
            paths, "prechild_refused", "windows_durability_refused_before_worker",
            code=exc.code,
        )
        return _finish(paths["root"], recovery=False)
    worker_token = _process_token(worker.pid)
    if worker_token is None:
        try:
            _terminate_owned(worker, job=supervisor_job)
        finally:
            if supervisor_job is not None:
                supervisor_job.close()
        raise ControllerRefusal(
            "RELEASE-CONTROLLER-WORKER-START", "worker creation token is unavailable",
        )
    owner: dict[str, Any] = {}
    try:
        for _ in range(500):
            journal = _read(paths["journal"])
            if paths["owner"].is_file():
                owner = _read(paths["owner"])
            if owner and any(row.get("event") == "worker_ready" for row in journal["events"]):
                break
            if worker.poll() is not None:
                detail = paths["worker_stderr"].read_bytes().decode("utf-8", errors="replace")
                raise ControllerRefusal(
                    "RELEASE-CONTROLLER-WORKER-START", detail or f"worker exited {worker.returncode}",
                )
            time.sleep(0.01)
        else:
            raise ControllerRefusal("RELEASE-CONTROLLER-WORKER-START", "worker readiness handshake timed out")
        if owner.get("pid") != worker.pid or owner.get("process_token") != worker_token:
            raise ControllerRefusal(
                "RELEASE-CONTROLLER-WORKER-START", "worker self-ownership binding is invalid",
            )
    except Exception:
        try:
            _terminate_owned(
                worker, job=supervisor_job, process_token=worker_token,
                process_group=worker.pid,
            )
            if os.name != "nt":
                _quiesce_recorded_child(paths)
        finally:
            if supervisor_job is not None:
                supervisor_job.close()
        raise
    if supervisor_job is not None:
        # The worker inherited the only remaining supervisor handle.  Its
        # process exit therefore kills any setup-window or product residue.
        supervisor_job.close()
    if isinstance(worker, _WindowsProcess):
        worker.close()
    return {"run_id": run_id, "request_sha256": request_sha, "intent_sha256": intent_sha,
            "state": "running", "worker": owner, "idempotent": False}


def status_run(*, run_root: str | Path, run_id: str) -> dict[str, Any]:
    paths = _paths(run_root, run_id)
    if paths["receipt"].is_file():
        return _validate_terminal(paths, _read(paths["receipt"]))
    intent = _validated_intent(paths["intent"])
    journal = _read(paths["journal"])
    owner = _read(paths["owner"]) if paths["owner"].is_file() else {}
    return {"run_id": run_id, "request_sha256": intent["request_sha256"],
            "intent_sha256": intent["intent_sha256"], "state": journal["state"],
            "worker": owner, "worker_alive": _alive(owner), "journal": str(paths["journal"])}


def _changed_outputs(intent: Mapping[str, Any], run_dir: Path) -> tuple[list[str], list[str]]:
    _validate_existing_watch_roots(intent["output_watch_roots"])
    for raw in intent["ignored_output_paths"]:
        _validate_ignored_output_path(raw, intent["output_watch_roots"])
    try:
        post = _inventory(
            intent["output_watch_roots"], run_dir,
            ignored_paths=intent["ignored_output_paths"],
        )
    except OSError as exc:
        raise ControllerRefusal(
            "RELEASE-CONTROLLER-OUTPUT-TOPOLOGY",
            f"cannot complete watched-output postimage: {exc}",
        ) from exc
    _validate_existing_watch_roots(intent["output_watch_roots"])
    for raw in intent["ignored_output_paths"]:
        _validate_ignored_output_path(raw, intent["output_watch_roots"])
    pre = intent["output_preimage"]
    changed = sorted(path for path in set(pre) | set(post) if pre.get(path) != post.get(path))
    return changed, _reparse_rows(post)


def _finish(
    run_dir: Path, *, recovery: bool, _lock_held: bool = False,
) -> dict[str, Any]:
    paths = _paths(run_dir.parent, run_dir.name)
    if not _lock_held:
        with _RunLock(paths["lock"]):
            return _finish(run_dir, recovery=recovery, _lock_held=True)
    if paths["receipt"].is_file():
        return _validate_terminal(paths, _read(paths["receipt"]))
    intent, journal = _validated_intent(paths["intent"]), _read(paths["journal"])
    exit_value = _read(paths["exit"]) if paths["exit"].is_file() else None
    prechild_value = _read(paths["prechild"]) if paths["prechild"].is_file() else None
    diagnostic = None
    capsule_exact = (
        exit_value is not None
        and exit_value.get("intent_sha256") == intent.get("intent_sha256")
        and exit_value.get("stdout") == (_binding(paths["stdout"]) if paths["stdout"].is_file() else None)
        and exit_value.get("stderr") == (_binding(paths["stderr"]) if paths["stderr"].is_file() else None)
        and exit_value.get("supervisor_result") == (
            _binding(paths["supervisor_result"])
            if paths["supervisor_result"].is_file() else None
        )
    )
    if prechild_value is not None:
        if (
            exit_value is not None
            or prechild_value.get("intent_sha256") != intent.get("intent_sha256")
            or not isinstance(prechild_value.get("diagnostic"), dict)
        ):
            state = "evidence_incomplete"
            diagnostic = {"code": "EVIDENCE_INCOMPLETE", "detail": "pre-child refusal evidence is stale"}
        else:
            state = "refused"
            diagnostic = prechild_value["diagnostic"]
    elif exit_value is None or not capsule_exact:
        state = "evidence_incomplete"
        diagnostic = {"code": "EVIDENCE_INCOMPLETE", "detail": "exit capsule or captured stream binding is absent or stale"}
    else:
        drift = _input_drift(intent)
        try:
            changes, reparse = _changed_outputs(intent, run_dir)
        except ControllerRefusal as exc:
            changes, reparse = [], []
            state, diagnostic = "refused", {"code": exc.code, "detail": exc.message}
        else:
            state = ""
        outside = [path for path in changes if not any(_inside(path, root) for root in intent["allowed_output_roots"])]
        if state:
            pass
        elif drift:
            state, diagnostic = "refused", {"code": "RELEASE-CONTROLLER-INPUT-DRIFT", "paths": drift}
        elif reparse:
            state, diagnostic = "refused", {
                "code": "RELEASE-CONTROLLER-OUTPUT-TOPOLOGY", "paths": reparse,
            }
        elif outside:
            state, diagnostic = "refused", {"code": "RELEASE-CONTROLLER-OUTPUT-SCOPE", "paths": outside}
        elif exit_value.get("cancelled"):
            state = "cancelled"
        elif exit_value["returncode"] == 0:
            state = "succeeded"
        else:
            state = "child_failed"
    # Keep the mutable journal non-terminal until the immutable terminal
    # receipt is visible; otherwise a waiter can observe a terminal label in
    # the narrow window before receipt publication.
    journal = _event(paths, "finalizing", "receipt_recovered" if recovery else "receipt_prepared",
                     terminal_state=state)
    owner = _read(paths["owner"]) if paths["owner"].is_file() else None
    exit_timestamps = exit_value.get("timestamps", {}) if exit_value else {}
    receipt = {
        "schema_version": "1.0.0", "receipt_type": "release_qualification_controller",
        "run_id": intent["run_id"], "request_sha256": intent["request_sha256"],
        "intent_sha256": intent["intent_sha256"], "state": state,
        "intent": _binding(paths["intent"]),
        "argv": intent["argv"], "cwd": intent["cwd"], "environment_delta": intent["environment_delta"],
        "inputs": intent["inputs"], "input_roots": intent["input_roots"],
        "ignored_output_paths": intent["ignored_output_paths"],
        "controller_created_output_roots": intent["controller_created_output_roots"],
        "worker": owner, "process": exit_value.get("process") if exit_value else None,
        "timestamps": {
            "controller_started_at": intent["created_at"],
            "worker_started_at": owner.get("started_at") if owner else None,
            "child_started_at": exit_timestamps.get("child_started_at"),
            "child_exited_at": exit_timestamps.get("child_exited_at"),
            "finalized_at": _now(),
        },
        "exit": ({"returncode": exit_value["returncode"]} if exit_value else None),
        "exit_capsule": _binding(paths["exit"]) if paths["exit"].is_file() else None,
        "prechild_refusal": _binding(paths["prechild"]) if paths["prechild"].is_file() else None,
        "child_attestation": _binding(paths["attestation"]) if paths["attestation"].is_file() else None,
        "stdout": exit_value.get("stdout") if capsule_exact else None,
        "stderr": exit_value.get("stderr") if capsule_exact else None,
        "journal": _binding(paths["journal"]), "diagnostic": diagnostic, "recovered": recovery,
    }
    _validate_receipt(receipt)
    _atomic(paths["receipt"], _canonical(receipt))
    return receipt


def recover_run(*, run_root: str | Path, run_id: str) -> dict[str, Any]:
    paths = _paths(run_root, run_id)
    with _RunLock(paths["lock"]):
        status = status_run(run_root=run_root, run_id=run_id)
        if status.get("worker_alive"):
            raise ControllerRefusal("RELEASE-CONTROLLER-LIVE", "owned worker is still active")
        _quiesce_recorded_child(paths)
        return _finish(paths["root"], recovery=True, _lock_held=True)


def wait_run(*, run_root: str | Path, run_id: str, timeout_s: float | None = None) -> dict[str, Any]:
    deadline = None if timeout_s is None else time.monotonic() + timeout_s
    while True:
        status = status_run(run_root=run_root, run_id=run_id)
        if status.get("state") in {"succeeded", "child_failed", "cancelled", "refused", "evidence_incomplete"}:
            paths = _paths(run_root, run_id)
            owner = _read(paths["owner"]) if paths["owner"].is_file() else {}
            if not _alive(owner):
                return status
        if not status.get("worker_alive", False):
            return recover_run(run_root=run_root, run_id=run_id)
        if deadline is not None and time.monotonic() >= deadline:
            raise ControllerRefusal("RELEASE-CONTROLLER-TIMEOUT", "wait timed out; run continues durably")
        time.sleep(0.05)


def cancel_run(*, run_root: str | Path, run_id: str, timeout_s: float = 30.0) -> dict[str, Any]:
    paths = _paths(run_root, run_id)
    recover = False
    with _RunLock(paths["lock"]):
        status = status_run(run_root=run_root, run_id=run_id)
        if status.get("state") in {"succeeded", "child_failed", "cancelled", "refused", "evidence_incomplete"}:
            return status
        if not status.get("worker_alive"):
            recover = True
        elif not paths["cancel"].is_file():
            _atomic(paths["cancel"], _canonical({
                "intent_sha256": status["intent_sha256"], "requested_at": _now(),
            }))
    if recover:
        return recover_run(run_root=run_root, run_id=run_id)
    return wait_run(run_root=run_root, run_id=run_id, timeout_s=timeout_s)


def _terminate_owned(
    child: Any, *, job: _WindowsJob | None = None,
    process_token: str | None = None, process_group: int | None = None,
) -> None:
    if job is not None:
        job.terminate()
        job.wait_empty()
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired as exc:
            raise ControllerRefusal("RELEASE-CONTROLLER-LIVE", "owned worker did not exit") from exc
        if isinstance(child, _WindowsProcess):
            child.close()
        return
    if os.name == "nt":
        raise ControllerRefusal(
            "RELEASE-CONTROLLER-PROCESS",
            "Windows owned-tree termination requires its preassigned Job handle",
        )
    group = process_group or child.pid
    if process_token is None:
        raise ControllerRefusal(
            "RELEASE-CONTROLLER-PROCESS", "POSIX termination requires a creation token",
        )
    _terminate_posix_session(
        group, leader_pid=child.pid, leader_token=process_token, timeout_s=10,
    )
    try:
        child.wait(timeout=10)
    except subprocess.TimeoutExpired as exc:
        raise ControllerRefusal("RELEASE-CONTROLLER-LIVE", "owned session leader did not exit") from exc


def _set_child_subreaper() -> None:
    if os.name == "nt":
        return
    import ctypes

    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
        raise ControllerRefusal(
            "RELEASE-CONTROLLER-PROCESS",
            f"PR_SET_CHILD_SUBREAPER failed with errno {ctypes.get_errno()}",
        )


def _reap_children() -> None:
    if os.name == "nt":
        return
    while True:
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            return
        if pid == 0:
            return


def _terminate_supervised_descendants(
    ancestor: int, product: subprocess.Popen[Any], *, timeout_s: float = 30.0,
) -> int:
    members = _descendant_members(ancestor)
    if members:
        _signal_descendants(ancestor, members, signal.SIGTERM)
    grace = time.monotonic() + .2
    direct_returncode = product.poll()
    while time.monotonic() < grace:
        direct_returncode = (
            product.poll() if direct_returncode is None else direct_returncode
        )
        if not _descendant_members(ancestor):
            break
        time.sleep(.01)
    deadline = time.monotonic() + timeout_s
    empty_scans = 0
    while empty_scans < 2:
        direct_returncode = (
            product.poll() if direct_returncode is None else direct_returncode
        )
        members = _descendant_members(ancestor)
        if members:
            _signal_descendants(ancestor, members, signal.SIGKILL)
        if direct_returncode is not None:
            _reap_children()
            if not _descendant_processes(ancestor):
                empty_scans += 1
                time.sleep(.01)
                continue
        empty_scans = 0
        if time.monotonic() >= deadline:
            raise ControllerRefusal(
                "RELEASE-CONTROLLER-LIVE",
                "supervised POSIX descendants did not become quiescent",
            )
        time.sleep(.01)
    if direct_returncode is None:
        raise ControllerRefusal(
            "EVIDENCE_INCOMPLETE", "direct product exit status is unavailable",
        )
    return direct_returncode


def _posix_supervisor(run_dir: Path, control_fd: int) -> int:
    import select

    paths = _paths(run_dir.parent, run_dir.name)
    intent = _validated_intent(paths["intent"])
    _set_child_subreaper()
    if os.read(control_fd, 1) != b"G":
        os.close(control_fd)
        return 74
    supervisor_token = _process_token(os.getpid())
    if supervisor_token is None:
        os.close(control_fd)
        return 76
    product_env = {
        key: value for key, value in os.environ.items()
        if key != _SUPERVISOR_JOB_ENV
    }
    product = subprocess.Popen(
        intent["argv"], cwd=intent["cwd"], env=product_env,
        stdin=subprocess.DEVNULL, close_fds=True,
    )
    product_token = _process_token(product.pid)
    if product_token is None:
        product.terminate()
        product.wait(timeout=10)
        os.close(control_fd)
        return 76
    _atomic(paths["product_started"], _canonical({
        "intent_sha256": intent["intent_sha256"], "pid": product.pid,
        "process_token": product_token, "started_at": _now(),
    }))

    def control_message(timeout_s: float = .05) -> bytes | None:
        readable, _, _ = select.select([control_fd], [], [], timeout_s)
        return os.read(control_fd, 1) if readable else None

    def commit_direct_exit(returncode: int) -> None:
        if not paths["direct_exit"].is_file():
            _atomic(paths["direct_exit"], _canonical({
                "intent_sha256": intent["intent_sha256"], "pid": product.pid,
                "process_token": product_token, "returncode": returncode,
                "exited_at": _now(),
            }))

    def commit_supervisor_result(mode: str, returncode: int) -> None:
        expected_supervisor_returncode = 0 if mode == "normal" else 75
        cancellation = (
            _binding(paths["cancel"]) if mode == "cancelled" and paths["cancel"].is_file()
            else None
        )
        if mode == "cancelled" and cancellation is None:
            raise ControllerRefusal(
                "EVIDENCE_INCOMPLETE", "durable cancellation binding is absent",
            )
        _atomic(paths["supervisor_result"], _canonical({
            "schema_version": "1.0.0", "intent_sha256": intent["intent_sha256"],
            "mode": mode,
            "expected_supervisor_returncode": expected_supervisor_returncode,
            "supervisor": {"pid": os.getpid(), "process_token": supervisor_token},
            "product": {
                "pid": product.pid, "process_token": product_token,
                "returncode": returncode,
            },
            "product_started": _binding(paths["product_started"]),
            "direct_exit": _binding(paths["direct_exit"]),
            "cancellation": cancellation,
            "descendants_quiescent": True, "empty_scans": 2,
            "completed_at": _now(),
        }))

    def owner_lost() -> int:
        try:
            returncode = _terminate_supervised_descendants(os.getpid(), product)
            commit_direct_exit(returncode)
        finally:
            os.close(control_fd)
        return 76

    def cancel_and_finish() -> int:
        returncode = _terminate_supervised_descendants(os.getpid(), product)
        commit_direct_exit(returncode)
        commit_supervisor_result("cancelled", returncode)
        os.close(control_fd)
        return 75

    direct_returncode = None
    while direct_returncode is None:
        direct_returncode = product.poll()
        message = control_message()
        if message == b"C":
            return cancel_and_finish()
        if message == b"":
            return owner_lost()
        if message is not None:
            return owner_lost()
    direct_returncode = product.wait() if product.returncode is None else product.returncode
    commit_direct_exit(direct_returncode)
    empty_scans = 0
    while empty_scans < 2:
        _reap_children()
        if not _descendant_processes(os.getpid()):
            empty_scans += 1
        else:
            empty_scans = 0
        message = control_message()
        if message == b"C":
            return cancel_and_finish()
        if message == b"":
            return owner_lost()
        if message is not None:
            return owner_lost()
    commit_supervisor_result("normal", direct_returncode)
    os.close(control_fd)
    _reap_children()
    return 0


def _input_drift(intent: Mapping[str, Any]) -> list[str]:
    drift = [
        row["path"] for row in intent["inputs"]
        if not Path(row["path"]).is_file() or _binding(Path(row["path"])) != row
    ]
    for row in intent["input_roots"]:
        try:
            current = _input_root_binding(
                row["path"], ignored_paths=intent.get("ignored_output_paths", ()),
            )
        except ControllerRefusal:
            current = None
        if current != row:
            drift.append(row["path"])
    return sorted(set(drift))


def verify_child_attestation(*, run_dir: str | Path, token: str) -> None:
    resolved = Path(run_dir).resolve()
    paths = _paths(resolved.parent, resolved.name)
    intent = _validated_intent(paths["intent"])
    if not intent.get("child_attestation") or not paths["attestation"].is_file():
        raise ControllerRefusal("CONTROLLER-CHILD-ATTESTATION", "controlled-child attestation was not issued")
    value = _read(paths["attestation"])
    owner = _read(paths["owner"]) if paths["owner"].is_file() else {}
    if (
        value.get("state") != "issued"
        or value.get("intent_sha256") != intent.get("intent_sha256")
        or value.get("token_sha256") != _sha_bytes(token.encode("utf-8"))
        or not _alive(owner)
    ):
        raise ControllerRefusal("CONTROLLER-CHILD-ATTESTATION", "controlled-child attestation is absent, stale, or replayed")
    _atomic(paths["attestation"], _canonical({
        **value, "state": "consumed", "consumed_at": _now(), "verifier_pid": os.getpid(),
    }))


def _worker(run_dir: Path) -> int:
    paths = _paths(run_dir.parent, run_dir.name)
    supervisor_job = None
    if os.name == "nt":
        inherited = os.environ.get(_SUPERVISOR_JOB_ENV, "")
        if not inherited.isdigit() or int(inherited) <= 0:
            return 74
        os.set_handle_inheritable(int(inherited), False)
        supervisor_job = _WindowsJob(handle=int(inherited))
        if supervisor_job.active_processes() < 1:
            return 74
    token = _process_token(os.getpid())
    owner = {
        "host": platform.node(), "pid": os.getpid(),
        "process_token": token if token is not None else "unavailable", "started_at": _now(),
    }
    _atomic(paths["owner"], _canonical(owner))
    _event(paths, "running", "worker_spawned", worker_pid=os.getpid(), process_group=os.getpid())
    if token is None:
        _event(paths, "recovery_required", "worker_identity_unavailable")
        return 74
    intent = _validated_intent(paths["intent"])
    _event(paths, "running", "worker_ready", worker_pid=os.getpid())
    if intent.get("test_fault") == "pause_before_input_drift":
        _event(paths, "running", "test_preflight_paused")
        while not paths["test_preflight_gate"].is_file():
            if paths["cancel"].is_file():
                _event(paths, "recovery_required", "test_preflight_cancelled")
                return 70
            time.sleep(.01)
    try:
        _validate_existing_watch_roots(intent["output_watch_roots"])
    except ControllerRefusal as exc:
        _atomic(paths["prechild"], _canonical({
            "schema_version": "1.0.0", "intent_sha256": intent["intent_sha256"],
            "refused_at": _now(), "diagnostic": {
                "code": exc.code, "detail": exc.message,
            },
        }))
        _event(
            paths, "prechild_refused", "watch_root_authority_refused_before_child",
            code=exc.code,
        )
        _finish(run_dir, recovery=False)
        return 0
    drift = _input_drift(intent)
    if drift:
        _atomic(paths["prechild"], _canonical({
            "schema_version": "1.0.0", "intent_sha256": intent["intent_sha256"],
            "refused_at": _now(), "diagnostic": {
                "code": "RELEASE-CONTROLLER-INPUT-DRIFT-BEFORE-CHILD", "paths": drift,
            },
        }))
        _event(paths, "prechild_refused", "input_drift_refused_before_child", paths=drift)
        _finish(run_dir, recovery=False)
        return 0
    try:
        worker_base = {
            key: value for key, value in os.environ.items()
            if key.upper() not in {
                "PYTHONUTF8", "PYTHONPATH", "PYTHONHOME", "PYTHONWARNINGS", "PYTHONOPTIMIZE",
                "COAUTHOR_RELEASE_CONTROLLER_WORKER", _SUPERVISOR_JOB_ENV,
            }
        }
        child_env, _ = controlled_environment(
            environment=worker_base,
            delta={key: value for key, value in intent["environment_delta"].items()
                   if not key.upper().startswith("PYTHON")},
            dependency_paths=(None if intent.get("allow_user_site") else tuple(
                filter(None, intent["environment_delta"].get("PYTHONPATH", "").split(os.pathsep))
            )),
            allow_user_site=bool(intent.get("allow_user_site")),
        )
    except QualificationEnvironmentRefusal as exc:
        _event(paths, "recovery_required", "environment_refused", code=exc.code)
        return 2
    started = _now()
    cancelled = False
    cancel_sent = False
    child = None
    product_job = None
    control_fd = None
    group = 0
    child_token = None
    product_pid = None
    returncode = None
    with paths["stdout"].open("xb") as stdout, paths["stderr"].open("xb") as stderr:
        try:
            if intent.get("test_fault") == "pause_before_watch_spawn":
                _event(paths, "running", "test_watch_spawn_paused")
                while not paths["test_preflight_gate"].is_file():
                    if paths["cancel"].is_file():
                        _event(paths, "recovery_required", "test_watch_spawn_cancelled")
                        return 70
                    time.sleep(.01)
            try:
                _validate_existing_watch_roots(intent["output_watch_roots"])
            except ControllerRefusal as exc:
                _atomic(paths["prechild"], _canonical({
                    "schema_version": "1.0.0", "intent_sha256": intent["intent_sha256"],
                    "refused_at": _now(), "diagnostic": {
                        "code": exc.code, "detail": exc.message,
                    },
                }))
                _event(
                    paths, "prechild_refused", "watch_root_authority_refused_at_spawn",
                    code=exc.code,
                )
                stdout.close()
                stderr.close()
                _finish(run_dir, recovery=False)
                return 0
            child, product_job, control_fd = _spawn_product_process(
                intent["argv"], cwd=intent["cwd"], environment=child_env,
                stdout=stdout, stderr=stderr, run_dir=run_dir,
            )
            group = child.pid
            child_token = _process_token(child.pid)
            if child_token is None:
                raise ControllerRefusal(
                    "RELEASE-CONTROLLER-PROCESS", "product creation token is unavailable",
                )
            if (
                os.name != "nt"
                and intent.get("test_fault") == "crash_after_supervisor_spawn_before_journal"
            ):
                os._exit(72)
            _event(
                paths, "running", "child_spawned", child_pid=child.pid,
                process_group=group, process_token=child_token,
            )
            if control_fd is not None:
                os.write(control_fd, b"G")
            if intent.get("test_fault") == "crash_after_child_spawn":
                os._exit(72)
            while True:
                direct_returncode = child.poll()
                tree_alive = (
                    product_job.active_processes()
                    if product_job is not None else bool(_session_members(group))
                )
                if paths["cancel"].is_file():
                    cancelled = True
                    if os.name != "nt" and control_fd is not None and not cancel_sent:
                        os.write(control_fd, b"C")
                        cancel_sent = True
                    if tree_alive and os.name == "nt":
                        _terminate_owned(
                            child, job=product_job, process_token=child_token,
                            process_group=group,
                        )
                        direct_returncode = child.poll()
                        tree_alive = False
                    elif tree_alive and cancel_sent:
                        try:
                            child.wait(timeout=30)
                        except subprocess.TimeoutExpired:
                            _terminate_owned(
                                child, process_token=child_token,
                                process_group=group,
                            )
                        direct_returncode = child.poll()
                        tree_alive = False
                if direct_returncode is not None and not tree_alive:
                    break
                time.sleep(.01)
            if os.name == "nt":
                returncode, product_pid = direct_returncode, child.pid
            else:
                if not paths["supervisor_result"].is_file():
                    raise ControllerRefusal(
                        "EVIDENCE_INCOMPLETE", "durable POSIX supervisor result is absent",
                    )
                supervisor_result = _read(paths["supervisor_result"])
                direct_exit = _read(paths["direct_exit"])
                product_started = _read(paths["product_started"])
                mode = supervisor_result.get("mode")
                expected_supervisor_returncode = 0 if mode == "normal" else (
                    75 if mode == "cancelled" else None
                )
                cancellation_binding = (
                    _binding(paths["cancel"]) if paths["cancel"].is_file() else None
                )
                if (
                    direct_exit.get("intent_sha256") != intent["intent_sha256"]
                    or product_started.get("intent_sha256") != intent["intent_sha256"]
                    or direct_exit.get("pid") != product_started.get("pid")
                    or direct_exit.get("process_token") != product_started.get("process_token")
                    or not isinstance(direct_exit.get("returncode"), int)
                    or supervisor_result.get("intent_sha256") != intent["intent_sha256"]
                    or supervisor_result.get("supervisor") != {
                        "pid": child.pid, "process_token": child_token,
                    }
                    or supervisor_result.get("product") != {
                        "pid": product_started.get("pid"),
                        "process_token": product_started.get("process_token"),
                        "returncode": direct_exit.get("returncode"),
                    }
                    or supervisor_result.get("product_started") != _binding(
                        paths["product_started"]
                    )
                    or supervisor_result.get("direct_exit") != _binding(paths["direct_exit"])
                    or supervisor_result.get("descendants_quiescent") is not True
                    or supervisor_result.get("empty_scans") != 2
                    or expected_supervisor_returncode is None
                    or supervisor_result.get("expected_supervisor_returncode")
                        != expected_supervisor_returncode
                    or direct_returncode != expected_supervisor_returncode
                    or bool(_session_members(group))
                ):
                    raise ControllerRefusal(
                        "EVIDENCE_INCOMPLETE",
                        "POSIX supervisor/direct-product/quiescence binding is absent or stale",
                    )
                if mode == "normal" and (
                    cancelled or paths["cancel"].is_file()
                    or supervisor_result.get("cancellation") is not None
                ):
                    raise ControllerRefusal(
                        "EVIDENCE_INCOMPLETE", "normal supervisor result overlaps cancellation",
                    )
                if mode == "cancelled" and (
                    not cancelled or not cancel_sent or cancellation_binding is None
                    or supervisor_result.get("cancellation") != cancellation_binding
                ):
                    raise ControllerRefusal(
                        "EVIDENCE_INCOMPLETE", "cancelled supervisor result is unbound",
                    )
                cancelled = mode == "cancelled"
                returncode, product_pid = direct_exit["returncode"], product_started["pid"]
        except Exception as exc:
            _event(
                paths, "recovery_required", "owned_tree_supervision_failed",
                code=getattr(exc, "code", "RELEASE-CONTROLLER-PROCESS"),
            )
            return 76
        finally:
            if control_fd is not None:
                os.close(control_fd)
            if product_job is not None:
                try:
                    if product_job.active_processes():
                        product_job.terminate()
                        product_job.wait_empty()
                finally:
                    product_job.close()
            if isinstance(child, _WindowsProcess):
                child.close()
        stdout.flush(); os.fsync(stdout.fileno())
        stderr.flush(); os.fsync(stderr.fileno())
    ended = _now()
    if returncode is None or child is None or product_pid is None:
        _event(paths, "recovery_required", "owned_tree_exit_status_unavailable")
        return 76
    if intent.get("test_fault") in {"lost_exit_status", "after_child_exit_before_exit_capsule"}:
        _event(paths, "recovery_required", "exit_status_lost")
        return 70
    capsule = {
        "schema_version": "1.0.0", "intent_sha256": intent["intent_sha256"], "returncode": returncode,
        "cancelled": cancelled, "process": {"pid": product_pid, "process_group": group},
        "timestamps": {"child_started_at": started, "child_exited_at": ended},
        "stdout": _binding(paths["stdout"]), "stderr": _binding(paths["stderr"]),
        "supervisor_result": (
            _binding(paths["supervisor_result"])
            if paths["supervisor_result"].is_file() else None
        ),
    }
    _atomic(paths["exit"], _canonical(capsule))
    _event(paths, "exited", "exit_capsule_committed", returncode=returncode)
    if intent.get("test_fault") in {"serialization_failure_after_exit", "receipt_serialization", "crash_after_exit", "after_exit_capsule_before_receipt"}:
        _event(paths, "recovery_required", "synthetic_post_exit_failure")
        return 71
    _finish(run_dir, recovery=False)
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("start", "run"):
        start = commands.add_parser(name)
        start.add_argument("--run-root", required=True); start.add_argument("--run-id", required=True)
        start.add_argument("--cwd", required=True); start.add_argument("--input", action="append", default=[])
        start.add_argument("--input-root", action="append", default=[])
        start.add_argument("--allowed-output", action="append", default=[]); start.add_argument("--watch-root", action="append", default=[])
        start.add_argument("--ignored-output", action="append", default=[])
        start.add_argument("--env", action="append", default=[]); start.add_argument("--timeout", type=float, default=None)
        start.add_argument("--allow-user-site", action="store_true")
        start.add_argument("--child-attestation", action="store_true")
        start.add_argument("argv", nargs=argparse.REMAINDER)
    for name in ("status", "wait", "cancel", "recover"):
        sub = commands.add_parser(name); sub.add_argument("--run-root", required=True); sub.add_argument("--run-id", required=True)
        if name in {"wait", "cancel"}: sub.add_argument("--timeout", type=float, default=None)
    worker = commands.add_parser("_worker"); worker.add_argument("--run-dir", required=True)
    supervisor = commands.add_parser("_posix_supervisor")
    supervisor.add_argument("--run-dir", required=True)
    supervisor.add_argument("--control-fd", required=True, type=int)
    verify = commands.add_parser("verify-child")
    verify.add_argument("--run-dir", required=True); verify.add_argument("--token", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "_posix_supervisor":
        if os.name == "nt":
            return 74
        try:
            return _posix_supervisor(Path(args.run_dir), args.control_fd)
        except Exception:
            return 72
    if args.command == "_worker":
        run_dir = Path(args.run_dir)
        try:
            return _worker(run_dir)
        except Exception:
            _atomic(run_dir / "worker-failure.json", _canonical({
                "failed_at": _now(), "traceback": traceback.format_exc(),
            }))
            try:
                _event(_paths(run_dir.parent, run_dir.name), "recovery_required", "worker_failed")
            except Exception:
                pass
            return 72
    if args.command == "verify-child":
        try:
            verify_child_attestation(run_dir=args.run_dir, token=args.token)
        except ControllerRefusal as exc:
            print(f"{exc.code}: {exc.message}", file=sys.stderr)
            return 2
        return 0
    try:
        if args.command in {"start", "run"}:
            command = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
            delta = dict(item.split("=", 1) for item in args.env)
            value = start_run(run_root=args.run_root, run_id=args.run_id, argv=command, cwd=args.cwd,
                              environment_delta=delta, input_paths=args.input, input_roots=args.input_root,
                              allowed_output_roots=args.allowed_output, output_watch_roots=args.watch_root,
                              ignored_output_paths=args.ignored_output,
                              allow_user_site=args.allow_user_site,
                              child_attestation=args.child_attestation)
            if args.command == "run":
                value = wait_run(run_root=args.run_root, run_id=args.run_id, timeout_s=args.timeout)
        elif args.command == "status": value = status_run(run_root=args.run_root, run_id=args.run_id)
        elif args.command == "wait": value = wait_run(run_root=args.run_root, run_id=args.run_id, timeout_s=args.timeout)
        elif args.command == "cancel": value = cancel_run(run_root=args.run_root, run_id=args.run_id, timeout_s=args.timeout or 30.0)
        else: value = recover_run(run_root=args.run_root, run_id=args.run_id)
    except (ControllerRefusal, QualificationEnvironmentRefusal) as exc:
        print(json.dumps({"state": "refused", "code": exc.code, "detail": str(exc)}, sort_keys=True))
        return 2
    if args.command == "run":
        if value.get("stdout"):
            sys.stdout.buffer.write(Path(value["stdout"]["path"]).read_bytes())
            sys.stdout.buffer.flush()
        if value.get("stderr"):
            sys.stderr.buffer.write(Path(value["stderr"]["path"]).read_bytes())
            sys.stderr.buffer.flush()
        if value.get("exit") is not None and value.get("state") in {"succeeded", "child_failed"}:
            return int(value["exit"]["returncode"])
        print(json.dumps({"controller_receipt": str(Path(args.run_root).resolve() / args.run_id / "receipt.json"),
                          "state": value.get("state"), "diagnostic": value.get("diagnostic")}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(value, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
