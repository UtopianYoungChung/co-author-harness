#!/usr/bin/env python3
"""Restart-safe controller for release-qualification child processes."""

from __future__ import annotations

import argparse
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
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator

from destination_capability import assert_writable
from qualification_environment import (
    QualificationEnvironmentRefusal,
    assert_ambient_clean,
    controlled_environment,
)

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


class ControllerRefusal(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code, self.message = code, message


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
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
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
    if (
        value.get("worker") != owner
        or value.get("timestamps", {}).get("controller_started_at") != intent.get("created_at")
        or value.get("timestamps", {}).get("worker_started_at") != owner.get("started_at")
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
            or value.get("timestamps", {}).get("child_started_at")
                != capsule.get("timestamps", {}).get("child_started_at")
            or value.get("timestamps", {}).get("child_exited_at")
                != capsule.get("timestamps", {}).get("child_exited_at")
        ):
            raise ControllerRefusal("EVIDENCE_INCOMPLETE", "terminal exit-capsule projection is stale")
    return value


def _process_token(pid: int) -> str | None:
    if pid <= 0:
        return None
    if os.name == "nt":
        try:
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
            kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
            handle = kernel32.OpenProcess(0x1000, False, pid)
            if not handle:
                return None
            created, exited, kernel, user = FILETIME(), FILETIME(), FILETIME(), FILETIME()
            ok = kernel32.GetProcessTimes(
                handle, ctypes.byref(created), ctypes.byref(exited), ctypes.byref(kernel), ctypes.byref(user)
            )
            kernel32.CloseHandle(handle)
            return str((created.high << 32) | created.low) if ok else None
        except Exception:
            return None
    try:
        return Path(f"/proc/{pid}/stat").read_text(encoding="ascii").split()[21]
    except (OSError, IndexError):
        try:
            os.kill(pid, 0)
            return "alive-no-token"
        except OSError:
            return None


def _alive(owner: Mapping[str, Any]) -> bool:
    token = owner.get("process_token")
    if owner.get("host") != platform.node() or not isinstance(owner.get("pid"), int):
        return False
    if not isinstance(token, str) or not token or token == "unavailable":
        return False
    observed = _process_token(owner["pid"])
    return observed is not None and observed == token


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
    allowed = sorted({str(Path(path).resolve()) for path in allowed_output_roots})
    watched = sorted({str(Path(path).resolve()) for path in output_watch_roots})
    if any(not any(_inside(path, root) for root in watched) for path in allowed):
        raise ControllerRefusal(
            "RELEASE-CONTROLLER-OUTPUT-TOPOLOGY",
            "every allowed output root must be contained by a watched root",
        )
    for path in allowed:
        assert_writable(path, purpose="release qualification allowed output")
    created_watch_roots: list[str] = []
    for path in watched:
        assert_writable(path, purpose="release qualification watched output")
        if not Path(path).exists():
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
        candidate = Path(path)
        if not candidate.is_file() or _is_reparse(candidate) or not any(_inside(path, root) for root in watched):
            raise ControllerRefusal(
                "RELEASE-CONTROLLER-OUTPUT-TOPOLOGY",
                f"ignored output must be one existing regular file inside a watch root: {path}",
            )
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
    flags = 0
    kwargs: dict[str, Any] = {"stdin": subprocess.DEVNULL, "close_fds": True, "env": worker_env}
    if os.name == "nt":
        flags = getattr(subprocess, "DETACHED_PROCESS", 0x8) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x200)
        kwargs["creationflags"] = flags
    else:
        kwargs["start_new_session"] = detached
    with paths["worker_stdout"].open("xb") as worker_stdout, paths["worker_stderr"].open("xb") as worker_stderr:
        worker = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "_worker", "--run-dir", str(paths["root"])],
            stdout=worker_stdout, stderr=worker_stderr, **kwargs,
        )
    owner: dict[str, Any] = {}
    for _ in range(500):
        journal = _read(paths["journal"])
        if paths["owner"].is_file():
            owner = _read(paths["owner"])
        if owner and any(row.get("event") == "worker_ready" for row in journal["events"]):
            break
        if worker.poll() is not None:
            detail = paths["worker_stderr"].read_bytes().decode("utf-8", errors="replace")
            raise ControllerRefusal("RELEASE-CONTROLLER-WORKER-START", detail or f"worker exited {worker.returncode}")
        time.sleep(0.01)
    else:
        raise ControllerRefusal("RELEASE-CONTROLLER-WORKER-START", "worker readiness handshake timed out")
    if owner.get("pid") != worker.pid or not isinstance(owner.get("process_token"), str):
        raise ControllerRefusal("RELEASE-CONTROLLER-WORKER-START", "worker self-ownership binding is invalid")
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
    for raw in intent["ignored_output_paths"]:
        path = Path(raw)
        if not path.is_file() or _is_reparse(path) or not any(
            _inside(path, root) for root in intent["output_watch_roots"]
        ):
            raise ControllerRefusal(
                "RELEASE-CONTROLLER-OUTPUT-TOPOLOGY", f"ignored output identity changed: {path}",
            )
    post = _inventory(
        intent["output_watch_roots"], run_dir,
        ignored_paths=intent["ignored_output_paths"],
    )
    pre = intent["output_preimage"]
    changed = sorted(path for path in set(pre) | set(post) if pre.get(path) != post.get(path))
    return changed, _reparse_rows(post)


def _finish(run_dir: Path, *, recovery: bool) -> dict[str, Any]:
    paths = _paths(run_dir.parent, run_dir.name)
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
        "stdout": _binding(paths["stdout"]) if paths["stdout"].is_file() else None,
        "stderr": _binding(paths["stderr"]) if paths["stderr"].is_file() else None,
        "journal": _binding(paths["journal"]), "diagnostic": diagnostic, "recovered": recovery,
    }
    _validate_receipt(receipt)
    _atomic(paths["receipt"], _canonical(receipt))
    return receipt


def recover_run(*, run_root: str | Path, run_id: str) -> dict[str, Any]:
    paths = _paths(run_root, run_id)
    status = status_run(run_root=run_root, run_id=run_id)
    if status.get("worker_alive"):
        raise ControllerRefusal("RELEASE-CONTROLLER-LIVE", "owned worker is still active")
    return _finish(paths["root"], recovery=True)


def wait_run(*, run_root: str | Path, run_id: str, timeout_s: float | None = None) -> dict[str, Any]:
    deadline = None if timeout_s is None else time.monotonic() + timeout_s
    while True:
        status = status_run(run_root=run_root, run_id=run_id)
        if status.get("state") in {"succeeded", "child_failed", "cancelled", "refused", "evidence_incomplete"}:
            paths = _paths(run_root, run_id)
            owner = _read(paths["owner"]) if paths["owner"].is_file() else {}
            if not _alive(owner):
                # Windows may report the process object gone a few scheduler
                # ticks before inherited spool handles become deletable.
                time.sleep(0.25)
                return status
        if not status.get("worker_alive", False):
            return recover_run(run_root=run_root, run_id=run_id)
        if deadline is not None and time.monotonic() >= deadline:
            raise ControllerRefusal("RELEASE-CONTROLLER-TIMEOUT", "wait timed out; run continues durably")
        time.sleep(0.05)


def cancel_run(*, run_root: str | Path, run_id: str, timeout_s: float = 30.0) -> dict[str, Any]:
    paths = _paths(run_root, run_id)
    status = status_run(run_root=run_root, run_id=run_id)
    if status.get("state") in {"succeeded", "child_failed", "cancelled", "refused", "evidence_incomplete"}:
        return status
    if not status.get("worker_alive"):
        return recover_run(run_root=run_root, run_id=run_id)
    _atomic(paths["cancel"], _canonical({"intent_sha256": status["intent_sha256"], "requested_at": _now()}))
    return wait_run(run_root=run_root, run_id=run_id, timeout_s=timeout_s)


def _terminate_owned(child: subprocess.Popen[bytes]) -> None:
    if child.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(child.pid), "/T", "/F"], stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    else:
        try:
            os.killpg(child.pid, signal.SIGTERM)
            time.sleep(0.2)
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


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
                "COAUTHOR_RELEASE_CONTROLLER_WORKER",
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
    with paths["stdout"].open("xb") as stdout, paths["stderr"].open("xb") as stderr:
        kwargs: dict[str, Any] = {"cwd": intent["cwd"], "env": child_env, "stdin": subprocess.DEVNULL,
                                  "stdout": stdout, "stderr": stderr, "close_fds": True}
        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x200)
        else:
            kwargs["start_new_session"] = True
        child = subprocess.Popen(intent["argv"], **kwargs)
        group = child.pid
        _event(paths, "running", "child_spawned", child_pid=child.pid, process_group=group)
        while child.poll() is None:
            if paths["cancel"].is_file():
                cancelled = True
                _terminate_owned(child)
            time.sleep(0.05)
        returncode = child.wait()
        stdout.flush(); os.fsync(stdout.fileno())
        stderr.flush(); os.fsync(stderr.fileno())
    ended = _now()
    if intent.get("test_fault") in {"lost_exit_status", "after_child_exit_before_exit_capsule"}:
        _event(paths, "recovery_required", "exit_status_lost")
        return 70
    capsule = {
        "schema_version": "1.0.0", "intent_sha256": intent["intent_sha256"], "returncode": returncode,
        "cancelled": cancelled, "process": {"pid": child.pid, "process_group": group},
        "timestamps": {"child_started_at": started, "child_exited_at": ended},
        "stdout": _binding(paths["stdout"]), "stderr": _binding(paths["stderr"]),
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
    verify = commands.add_parser("verify-child")
    verify.add_argument("--run-dir", required=True); verify.add_argument("--token", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
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
