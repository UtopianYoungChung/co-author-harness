#!/usr/bin/env python3
"""Journaled, marker-last publication for C2 evidence transactions."""

from __future__ import annotations

import contextlib
import contextvars
import ctypes
import hashlib
import json
import os
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Iterator

from destination_capability import assert_writable, classify


class EvidencePublicationError(RuntimeError):
    pass


_ACTIVE_BOUND_TREE: contextvars.ContextVar["_BoundDirectoryTree | None"] = (
    contextvars.ContextVar("evidence_publication_bound_tree", default=None)
)

_GENERIC_READ = 0x80000000
_FILE_SHARE_READ = 0x00000001
_FILE_SHARE_WRITE = 0x00000002
_OPEN_EXISTING = 3
_FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
_INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class _FILETIME(ctypes.Structure):
    _fields_ = (
        ("dwLowDateTime", ctypes.c_uint32),
        ("dwHighDateTime", ctypes.c_uint32),
    )


class _BY_HANDLE_FILE_INFORMATION(ctypes.Structure):
    _fields_ = (
        ("dwFileAttributes", ctypes.c_uint32),
        ("ftCreationTime", _FILETIME),
        ("ftLastAccessTime", _FILETIME),
        ("ftLastWriteTime", _FILETIME),
        ("dwVolumeSerialNumber", ctypes.c_uint32),
        ("nFileSizeHigh", ctypes.c_uint32),
        ("nFileSizeLow", ctypes.c_uint32),
        ("nNumberOfLinks", ctypes.c_uint32),
        ("nFileIndexHigh", ctypes.c_uint32),
        ("nFileIndexLow", ctypes.c_uint32),
    )


def _norm_abs(path: Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def _under_admitted(child: Path, root: Path) -> bool:
    try:
        child_n = Path(_norm_abs(child))
        root_n = Path(_norm_abs(root))
        return child_n == root_n or child_n.is_relative_to(root_n)
    except (OSError, ValueError):
        return False


def _nt_kernel32() -> ctypes.WinDLL:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateFileW.argtypes = (
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    )
    kernel32.CreateFileW.restype = ctypes.c_void_p
    kernel32.GetFinalPathNameByHandleW.argtypes = (
        ctypes.c_void_p,
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
    )
    kernel32.GetFinalPathNameByHandleW.restype = ctypes.c_uint32
    kernel32.GetFileInformationByHandle.argtypes = (
        ctypes.c_void_p,
        ctypes.POINTER(_BY_HANDLE_FILE_INFORMATION),
    )
    kernel32.GetFileInformationByHandle.restype = ctypes.c_int
    kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
    kernel32.CloseHandle.restype = ctypes.c_int
    return kernel32


def _nt_strip_extended(raw: str) -> str:
    if raw.startswith("\\\\?\\UNC\\"):
        return "\\\\" + raw[8:]
    if raw.startswith("\\\\?\\"):
        return raw[4:]
    return raw


class _HeldDirectory:
    __slots__ = ("path", "final_path", "identity", "_fd", "_handle")

    def __init__(
        self,
        path: Path,
        final_path: Path,
        identity: tuple[int, int],
        *,
        fd: int | None = None,
        handle: int | None = None,
    ) -> None:
        self.path = path
        self.final_path = final_path
        self.identity = identity
        self._fd = fd
        self._handle = handle

    def close(self) -> None:
        handle = self._handle
        self._handle = None
        if handle is not None:
            _nt_kernel32().CloseHandle(handle)
        fd = self._fd
        self._fd = None
        if fd is not None:
            os.close(fd)


class _BoundDirectoryTree:
    """Hold admitted root and mutation ancestors across publication/recovery."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root_held: _HeldDirectory | None = None
        self._handles: list[_HeldDirectory] = []
        self._by_norm: dict[str, _HeldDirectory] = {}

    @classmethod
    def open(cls, root: Path) -> "_BoundDirectoryTree":
        tree = cls(root)
        tree.root_held = tree._open_existing(root)
        tree._register(tree.root_held)
        return tree

    def close(self) -> None:
        while self._handles:
            self._handles.pop().close()
        self._by_norm.clear()
        self.root_held = None

    def assert_root(self, root: Path) -> None:
        if self.root_held is None:
            raise EvidencePublicationError("bound directory tree is closed")
        if not _under_admitted(root, self.root_held.final_path) or not _under_admitted(
            self.root_held.final_path, root
        ):
            probe = self._probe_identity(root)
            if probe != self.root_held.identity:
                raise EvidencePublicationError("admitted root identity changed")

    def ensure_directory(self, path: Path) -> _HeldDirectory:
        if self.root_held is None:
            raise EvidencePublicationError("bound directory tree is closed")
        abs_root = _norm_abs(self.root)
        abs_path = _norm_abs(path)
        if abs_path == abs_root:
            return self.root_held
        prefix = abs_root + os.sep
        if not abs_path.startswith(prefix):
            raise EvidencePublicationError("directory escapes admitted root")
        current = self.root_held
        current_path = self.root
        for part in Path(abs_path[len(prefix):]).parts:
            if part in {"", ".", ".."}:
                raise EvidencePublicationError("directory escapes admitted root")
            current_path = current_path / part
            key = _norm_abs(current_path)
            held = self._by_norm.get(key)
            if held is None:
                held = self._create_or_open_child(current, current_path, part)
                self._register(held)
            current = held
        return current

    def assert_path_is_held(self, path: Path) -> _HeldDirectory:
        held = self.ensure_directory(path)
        probe = self._probe_identity(path)
        if probe != held.identity:
            raise EvidencePublicationError(
                "directory identity changed between bind and use"
            )
        return held

    def _register(self, held: _HeldDirectory) -> None:
        self._handles.append(held)
        self._by_norm[_norm_abs(held.path)] = held

    def _create_or_open_child(
        self, parent: _HeldDirectory, child_path: Path, name: str
    ) -> _HeldDirectory:
        if os.name == "nt":
            try:
                os.mkdir(os.fspath(child_path))
            except FileExistsError:
                pass
            except OSError as exc:
                raise EvidencePublicationError(
                    f"cannot create bound directory: {child_path}"
                ) from exc
            return self._open_existing(child_path)
        if parent._fd is None:
            raise EvidencePublicationError("missing parent directory descriptor")
        try:
            os.mkdir(name, dir_fd=parent._fd)
        except FileExistsError:
            pass
        except OSError as exc:
            raise EvidencePublicationError(
                f"cannot create bound directory: {child_path}"
            ) from exc
        return self._open_existing_posix_at(parent, child_path, name)

    def _open_existing(self, path: Path) -> _HeldDirectory:
        if os.name == "nt":
            return self._open_existing_nt(path)
        return self._open_existing_posix(path)

    def _open_existing_nt(self, path: Path) -> _HeldDirectory:
        kernel32 = _nt_kernel32()
        handle = kernel32.CreateFileW(
            os.fspath(path),
            _GENERIC_READ,
            _FILE_SHARE_READ | _FILE_SHARE_WRITE,
            None,
            _OPEN_EXISTING,
            _FILE_FLAG_BACKUP_SEMANTICS,
            None,
        )
        if handle is None or handle == _INVALID_HANDLE_VALUE:
            raise EvidencePublicationError(
                f"cannot bind directory handle: {path}: "
                f"{ctypes.WinError(ctypes.get_last_error())}"
            )
        try:
            identity = self._nt_identity(handle)
            final_path = self._nt_final_path(handle)
        except BaseException:
            kernel32.CloseHandle(handle)
            raise
        if self.root_held is None:
            if Path(_norm_abs(final_path)) != Path(_norm_abs(path)):
                kernel32.CloseHandle(handle)
                raise EvidencePublicationError("admitted root handle identity mismatch")
        elif not _under_admitted(final_path, self.root_held.final_path):
            kernel32.CloseHandle(handle)
            raise EvidencePublicationError("directory handle escapes admitted root")
        return _HeldDirectory(
            path, final_path, identity, handle=int(handle)
        )

    def _open_existing_posix(self, path: Path) -> _HeldDirectory:
        flags = os.O_RDONLY
        if not hasattr(os, "O_DIRECTORY"):
            raise EvidencePublicationError(
                "stable directory binding requires O_DIRECTORY"
            )
        flags |= os.O_DIRECTORY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(os.fspath(path), flags)
        except OSError as exc:
            raise EvidencePublicationError(
                f"cannot bind directory descriptor: {path}"
            ) from exc
        try:
            identity = self._posix_identity(fd)
            final_path = self._posix_final_path(fd)
        except BaseException:
            os.close(fd)
            raise
        if self.root_held is None:
            if Path(_norm_abs(final_path)) != Path(_norm_abs(path)):
                os.close(fd)
                raise EvidencePublicationError("admitted root handle identity mismatch")
        elif not _under_admitted(final_path, self.root_held.final_path):
            os.close(fd)
            raise EvidencePublicationError("directory handle escapes admitted root")
        return _HeldDirectory(path, final_path, identity, fd=fd)

    def _open_existing_posix_at(
        self, parent: _HeldDirectory, child_path: Path, name: str
    ) -> _HeldDirectory:
        if parent._fd is None:
            raise EvidencePublicationError("missing parent directory descriptor")
        flags = os.O_RDONLY
        if not hasattr(os, "O_DIRECTORY"):
            raise EvidencePublicationError(
                "stable directory binding requires O_DIRECTORY"
            )
        flags |= os.O_DIRECTORY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(name, flags, dir_fd=parent._fd)
        except OSError as exc:
            raise EvidencePublicationError(
                f"cannot bind directory descriptor: {child_path}"
            ) from exc
        try:
            identity = self._posix_identity(fd)
            final_path = self._posix_final_path(fd)
        except BaseException:
            os.close(fd)
            raise
        assert self.root_held is not None
        if not _under_admitted(final_path, self.root_held.final_path):
            os.close(fd)
            raise EvidencePublicationError("directory handle escapes admitted root")
        return _HeldDirectory(child_path, final_path, identity, fd=fd)

    def _probe_identity(self, path: Path) -> tuple[int, int]:
        held = self._open_existing(path)
        try:
            return held.identity
        finally:
            held.close()

    def _nt_identity(self, handle: int) -> tuple[int, int]:
        info = _BY_HANDLE_FILE_INFORMATION()
        if not _nt_kernel32().GetFileInformationByHandle(handle, ctypes.byref(info)):
            raise EvidencePublicationError(
                f"cannot read directory identity: {ctypes.WinError(ctypes.get_last_error())}"
            )
        index = (int(info.nFileIndexHigh) << 32) | int(info.nFileIndexLow)
        return (int(info.dwVolumeSerialNumber), index)

    def _nt_final_path(self, handle: int) -> Path:
        kernel32 = _nt_kernel32()
        buffer = ctypes.create_unicode_buffer(32768)
        written = kernel32.GetFinalPathNameByHandleW(handle, buffer, 32768, 0)
        if written == 0 or written >= 32768:
            raise EvidencePublicationError(
                f"cannot read directory final path: {ctypes.WinError(ctypes.get_last_error())}"
            )
        return Path(_nt_strip_extended(buffer.value))

    def _posix_identity(self, fd: int) -> tuple[int, int]:
        st = os.fstat(fd)
        return (int(st.st_dev), int(st.st_ino))

    def _posix_final_path(self, fd: int) -> Path:
        proc = f"/proc/self/fd/{fd}"
        try:
            return Path(os.readlink(proc))
        except OSError:
            pass
        try:
            import fcntl
        except ImportError as exc:
            raise EvidencePublicationError(
                "cannot read stable directory path from held descriptor"
            ) from exc
        getpath = getattr(fcntl, "F_GETPATH", None)
        if getpath is None:
            raise EvidencePublicationError(
                "cannot read stable directory path from held descriptor"
            )
        buffer = ctypes.create_string_buffer(4096)
        fcntl.fcntl(fd, getpath, buffer)
        return Path(os.fsdecode(buffer.value))


@contextlib.contextmanager
def _hold_bound_tree(root: Path) -> Iterator[_BoundDirectoryTree]:
    existing = _ACTIVE_BOUND_TREE.get()
    if existing is not None:
        existing.assert_root(root)
        yield existing
        return
    tree = _BoundDirectoryTree.open(root)
    token = _ACTIVE_BOUND_TREE.set(tree)
    try:
        yield tree
    finally:
        _ACTIVE_BOUND_TREE.reset(token)
        tree.close()


def _require_bound_tree(root: Path) -> _BoundDirectoryTree:
    existing = _ACTIVE_BOUND_TREE.get()
    if existing is None:
        raise EvidencePublicationError("publication mutations require a bound directory tree")
    existing.assert_root(root)
    return existing


def _transaction_control_root(root: Path) -> Path:
    """Keep live Workbench control state inside its instrument lane."""
    if classify(root) == "protected":
        return root / "reviews" / ".harness" / "evidence-transactions"
    return root / ".harness-evidence-transactions"


def _transaction_lane(root: Path, transaction_id: str) -> Path:
    return _transaction_control_root(root) / transaction_id


def _publication_lock_path(root: Path) -> Path:
    return _transaction_control_root(root) / "publication.lock"


def _assert_bound_path(root: Path, path: Path, purpose: str) -> Path:
    live_root = root.resolve(strict=True)
    live_path = path.resolve()
    if not live_path.is_relative_to(live_root):
        raise EvidencePublicationError(f"{purpose} escapes project root")
    assert_writable(live_path, purpose=purpose)
    return live_path


def _preflight_control_and_outputs(
    root: Path,
    transaction_id: str,
    resolved: list[tuple[Path, bytes]],
    *,
    purpose: str,
    include_recovery: bool,
) -> None:
    """Refuse every intended control/output destination before any mkdir."""
    control = _transaction_control_root(root)
    lane = _transaction_lane(root, transaction_id)
    state_purpose = (
        "evidence recovery transaction state"
        if include_recovery
        else "evidence transaction state"
    )
    lock_purpose = "evidence transaction lock"
    destinations: list[tuple[Path, str]] = []
    for path, _data in resolved:
        destinations.append((path, purpose))
        destinations.append((path.parent, purpose))
    destinations.extend(
        [
            (control, state_purpose),
            (_publication_lock_path(root), lock_purpose),
            (lane, state_purpose),
            (lane / "claim.lock", lock_purpose),
            (lane / "prepared", state_purpose),
        ]
    )
    if include_recovery:
        destinations.append((lane / "recovery", state_purpose))
    for path, item_purpose in destinations:
        _assert_bound_path(root, path, item_purpose)
    live_lane = _assert_bound_path(root, lane, state_purpose)
    live_control = _assert_bound_path(root, control, state_purpose)
    if Path(_norm_abs(live_lane.parent)) != Path(_norm_abs(live_control)):
        raise EvidencePublicationError(
            f"{state_purpose} escapes transaction control root"
        )


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _replace_with_transient_retry(source: Path, destination: Path) -> None:
    """Tolerate short Windows sharing denials without weakening atomic replace."""
    delays = (0.01, 0.02, 0.04, 0.08, 0.16, 0.32, 0.64)
    for attempt in range(len(delays) + 1):
        try:
            os.replace(source, destination)
            return
        except PermissionError:
            if os.name != "nt" or attempt == len(delays):
                raise
            time.sleep(delays[attempt])


def _durable_write_posix(bound: Path, data: bytes, parent: _HeldDirectory) -> None:
    if parent._fd is None:
        raise EvidencePublicationError("missing parent directory descriptor")
    tmp_name = f".{bound.name}.{uuid.uuid4().hex}.tmp"
    fd = os.open(
        tmp_name,
        os.O_CREAT | os.O_EXCL | os.O_WRONLY,
        0o644,
        dir_fd=parent._fd,
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            fd = -1
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        if fd >= 0:
            os.close(fd)
    try:
        os.replace(
            tmp_name,
            bound.name,
            src_dir_fd=parent._fd,
            dst_dir_fd=parent._fd,
        )
    except BaseException:
        try:
            os.unlink(tmp_name, dir_fd=parent._fd)
        except OSError:
            pass
        raise


def _exclusive_create_posix(
    bound: Path, data: bytes, parent: _HeldDirectory, *, already_exists: str
) -> None:
    if parent._fd is None:
        raise EvidencePublicationError("missing parent directory descriptor")
    try:
        fd = os.open(
            bound.name,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            0o644,
            dir_fd=parent._fd,
        )
    except FileExistsError as exc:
        raise EvidencePublicationError(already_exists) from exc
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def _durable_write(
    path: Path, data: bytes, *, root: Path, purpose: str = "evidence publication"
) -> None:
    bound = _assert_bound_path(root, path, purpose)
    tree = _require_bound_tree(root)
    tree.ensure_directory(bound.parent)
    parent = tree.assert_path_is_held(bound.parent)
    bound = _assert_bound_path(root, bound, purpose)
    if os.name != "nt":
        _durable_write_posix(bound, data, parent)
        return
    with tempfile.NamedTemporaryFile(
        mode="wb", dir=bound.parent, prefix=f".{bound.name}.", delete=False
    ) as handle:
        temporary = Path(handle.name)
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        bound = _assert_bound_path(root, bound, purpose)
        tree.assert_path_is_held(bound.parent)
        _replace_with_transient_retry(temporary, bound)
    finally:
        temporary.unlink(missing_ok=True)


def _exclusive_json(
    path: Path,
    value: dict[str, Any],
    *,
    root: Path,
    purpose: str = "evidence publication",
) -> None:
    bound = _assert_bound_path(root, path, purpose)
    tree = _require_bound_tree(root)
    tree.ensure_directory(bound.parent)
    parent = tree.assert_path_is_held(bound.parent)
    bound = _assert_bound_path(root, bound, purpose)
    payload = _canonical(value)
    if os.name != "nt":
        _exclusive_create_posix(
            bound,
            payload,
            parent,
            already_exists=f"exclusive record already exists: {bound}",
        )
        return
    try:
        with bound.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise EvidencePublicationError(f"exclusive record already exists: {bound}") from exc


def _exclusive_marker(
    path: Path, data: bytes, *, root: Path, purpose: str = "evidence publication"
) -> None:
    bound = _assert_bound_path(root, path, purpose)
    tree = _require_bound_tree(root)
    tree.ensure_directory(bound.parent)
    parent = tree.assert_path_is_held(bound.parent)
    bound = _assert_bound_path(root, bound, purpose)
    if bound.exists():
        if bound.is_file() and bound.read_bytes() == data:
            return
        raise EvidencePublicationError(
            "commit marker already exists with different bytes; recovery required"
        )
    if os.name != "nt":
        _exclusive_create_posix(
            bound,
            data,
            parent,
            already_exists="commit marker was concurrently created; recovery required",
        )
        return
    try:
        with bound.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise EvidencePublicationError(
            "commit marker was concurrently created; recovery required"
        ) from exc


def _open_lock_file(bound: Path, parent: _HeldDirectory):
    """Open the lock file; POSIX uses the held parent descriptor."""
    if os.name == "nt":
        return bound.open("a+b")
    if parent._fd is None:
        raise EvidencePublicationError("missing parent directory descriptor")
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    fd = -1
    try:
        fd = os.open(bound.name, flags, 0o644, dir_fd=parent._fd)
        st_parent = os.fstat(parent._fd)
        if (int(st_parent.st_dev), int(st_parent.st_ino)) != parent.identity:
            raise EvidencePublicationError("lock parent identity changed")
        handle = os.fdopen(fd, "r+b")
        fd = -1
        return handle
    except OSError as exc:
        raise EvidencePublicationError(f"cannot open transaction lock: {bound}") from exc
    finally:
        if fd >= 0:
            os.close(fd)


@contextlib.contextmanager
def _claim_lock(path: Path, *, root: Path) -> Iterator[None]:
    with _hold_bound_tree(root) as tree:
        bound = _assert_bound_path(root, path, "evidence transaction lock")
        tree.ensure_directory(bound.parent)
        parent = tree.assert_path_is_held(bound.parent)
        bound = _assert_bound_path(root, bound, "evidence transaction lock")
        handle = _open_lock_file(bound, parent)
        try:
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
        except OSError as exc:
            raise EvidencePublicationError("transaction claim is already live") from exc
        finally:
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            handle.close()


def _binding(root: Path, path: Path, data: bytes) -> dict[str, Any]:
    return {
        "path": path.resolve().relative_to(root).as_posix(),
        "sha256": _digest(data),
        "size": len(data),
    }


def publish_committed(
    *,
    project_root: Path,
    transaction_id: str,
    preconditions: list[tuple[Path, str]],
    inventory_preconditions: list[tuple[Path, dict[str, str]]],
    outputs: list[tuple[Path, bytes]],
    marker: tuple[Path, bytes],
    under_claim_validator: Callable[[], None] | None = None,
) -> None:
    """Publish prepared bytes under an exclusive claim, with marker last."""
    root = project_root.resolve(strict=True)
    all_rows = [*outputs, marker]
    resolved = [(path.resolve(), data) for path, data in all_rows]
    if not transaction_id or len({path for path, _ in resolved}) != len(resolved):
        raise EvidencePublicationError("transaction id or output set is invalid")
    if any(not path.is_relative_to(root) for path, _ in resolved):
        raise EvidencePublicationError("publication output escapes project root")
    _preflight_control_and_outputs(
        root,
        transaction_id,
        resolved,
        purpose="evidence publication",
        include_recovery=False,
    )
    plan = {
        "schema_version": "1.0.0",
        "transaction_id": transaction_id,
        "inputs": [
            {
                "path": str(path.resolve(strict=True)),
                "sha256": digest,
                "size": path.resolve(strict=True).stat().st_size,
            }
            for path, digest in preconditions
        ],
        "inventories": [
            {
                "root": str(inventory_root.resolve(strict=True)),
                "files": expected,
            }
            for inventory_root, expected in inventory_preconditions
        ],
        "outputs": [_binding(root, path, data) for path, data in resolved],
        "marker_path": resolved[-1][0].relative_to(root).as_posix(),
    }
    plan_hash = _digest(_canonical(plan))
    with _hold_bound_tree(root) as tree:
        for path, _data in resolved:
            tree.ensure_directory(path.parent)
        tree.ensure_directory(_transaction_control_root(root))
        tree.ensure_directory(_transaction_lane(root, transaction_id))
        tree.ensure_directory(_transaction_lane(root, transaction_id) / "prepared")
        return _finish_publish_committed(
            root,
            transaction_id,
            preconditions,
            inventory_preconditions,
            resolved,
            plan,
            plan_hash,
            under_claim_validator,
        )


def _finish_publish_committed(
    root: Path,
    transaction_id: str,
    preconditions: list[tuple[Path, str]],
    inventory_preconditions: list[tuple[Path, dict[str, str]]],
    resolved: list[tuple[Path, bytes]],
    plan: dict[str, Any],
    plan_hash: str,
    under_claim_validator: Callable[[], None] | None,
) -> None:
    lane = _assert_bound_path(
        root, _transaction_lane(root, transaction_id), "evidence transaction state"
    )
    prepared = lane / "prepared"
    claim_path = lane / "claim.json"
    journal_path = lane / "journal.json"
    with (
        _claim_lock(_publication_lock_path(root), root=root),
        _claim_lock(lane / "claim.lock", root=root),
    ):
        for path, expected in preconditions:
            resolved_input = path.resolve(strict=True)
            if hashlib.sha256(resolved_input.read_bytes()).hexdigest() != expected:
                raise EvidencePublicationError(
                    f"publication dependency changed under claim: {resolved_input}"
                )
        for inventory_root, expected in inventory_preconditions:
            resolved_inventory = inventory_root.resolve(strict=True)
            actual = {
                path.relative_to(resolved_inventory).as_posix(): hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
                for path in sorted(resolved_inventory.glob("*.md"))
                if path.is_file()
            }
            if actual != expected:
                raise EvidencePublicationError(
                    f"publication inventory changed under claim: {resolved_inventory}"
                )
        if under_claim_validator is not None:
            under_claim_validator()
        if claim_path.exists() or journal_path.exists():
            try:
                claim = json.loads(claim_path.read_text(encoding="utf-8"))
                journal = json.loads(journal_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise EvidencePublicationError(
                    "existing transaction state is unreadable; recovery required"
                ) from exc
            if (
                claim.get("plan_sha256") != plan_hash
                or journal.get("plan_sha256") != plan_hash
            ):
                raise EvidencePublicationError(
                    "existing transaction intent differs; recovery required"
                )
            if journal.get("state") not in {"prepared", "publishing", "published"}:
                raise EvidencePublicationError("transaction recovery is required")
        else:
            claim = {
                "schema_version": "1.0.0",
                "transaction_id": transaction_id,
                "claim_type": "exclusive_no_ttl",
                "owner_pid": os.getpid(),
                "state": "active",
                "plan_sha256": plan_hash,
            }
            _exclusive_json(claim_path, claim, root=root)
            _require_bound_tree(root).ensure_directory(prepared)
            prepared_rows: list[dict[str, Any]] = []
            for index, (path, data) in enumerate(resolved):
                prepared_path = prepared / f"{index:03d}.bin"
                _durable_write(prepared_path, data, root=root)
                row = _binding(root, path, data)
                row["prepared"] = prepared_path.relative_to(root).as_posix()
                row["prior_sha256"] = (
                    hashlib.sha256(path.read_bytes()).hexdigest()
                    if path.is_file()
                    else None
                )
                prepared_rows.append(row)
            journal = {
                "schema_version": "1.0.0",
                "transaction_id": transaction_id,
                "plan_sha256": plan_hash,
                "state": "prepared",
                "published": [],
                "inputs": plan["inputs"],
                "writes": prepared_rows,
            }
            _exclusive_json(journal_path, journal, root=root)
        for row in journal["writes"]:
            prepared_path = (root / row["prepared"]).resolve(strict=True)
            if (
                not prepared_path.is_relative_to(prepared)
                or hashlib.sha256(prepared_path.read_bytes()).hexdigest()
                != row["sha256"]
            ):
                raise EvidencePublicationError("prepared bytes are stale")
        marker_path, marker_data = resolved[-1]
        if marker_path.exists():
            if not marker_path.is_file() or marker_path.read_bytes() != marker_data:
                raise EvidencePublicationError(
                    "commit marker conflicts with intent; recovery required"
                )
            non_marker_exact = all(
                path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == _digest(data)
                for path, data in resolved[:-1]
            )
            if not non_marker_exact:
                raise EvidencePublicationError(
                    "visible commit marker has a non-matching output prefix; inspected recovery required"
                )
            expected_published = [row["path"] for row in journal["writes"]]
            if (
                journal.get("state") == "published"
                and journal.get("published") == expected_published
                and claim.get("state") == "consumed"
            ):
                return
            journal["published"] = expected_published
            journal["state"] = "published"
            claim["state"] = "consumed"
            _durable_write(journal_path, _canonical(journal), root=root)
            _durable_write(claim_path, _canonical(claim), root=root)
            return
        journal["state"] = "publishing"
        _durable_write(journal_path, _canonical(journal), root=root)
        try:
            for row in journal["writes"][:-1]:
                destination = _assert_bound_path(
                    root, root / row["path"], "evidence publication"
                )
                prepared_path = _assert_bound_path(
                    root, root / row["prepared"], "evidence publication"
                )
                _durable_write(destination, prepared_path.read_bytes(), root=root)
                if row["path"] not in journal["published"]:
                    journal["published"].append(row["path"])
                _durable_write(journal_path, _canonical(journal), root=root)
            marker_row = journal["writes"][-1]
            marker_path = _assert_bound_path(
                root, root / marker_row["path"], "evidence publication"
            )
            prepared_marker = _assert_bound_path(
                root, root / marker_row["prepared"], "evidence publication"
            )
            _exclusive_marker(marker_path, prepared_marker.read_bytes(), root=root)
            if marker_row["path"] not in journal["published"]:
                journal["published"].append(marker_row["path"])
            journal["state"] = "published"
            _durable_write(journal_path, _canonical(journal), root=root)
            claim["state"] = "consumed"
            _durable_write(claim_path, _canonical(claim), root=root)
        except OSError as exc:
            journal["state"] = "publishing"
            _durable_write(journal_path, _canonical(journal), root=root)
            raise EvidencePublicationError(
                "publication interrupted; recovery required"
            ) from exc


def validate_recorded_committed(
    *,
    project_root: Path,
    transaction_id: str,
    expected_products: list[Path],
    expected_marker: Path,
) -> None:
    """Replay an inventory-free publication through the exact validator.

    Journals do not record inventory maps. A plan needing those maps cannot
    be reconstructed here and must fail the normal plan-hash comparison.
    """
    root = project_root.resolve(strict=True)
    lane = _transaction_lane(root, transaction_id).resolve()
    if not lane.is_relative_to(root):
        raise EvidencePublicationError("transaction lane escapes project root")
    try:
        raw = (lane / "journal.json").read_bytes()
        journal = json.loads(raw.decode("utf-8", errors="strict"))
        if not isinstance(journal, dict) or raw != _canonical(journal):
            raise EvidencePublicationError("recorded transaction journal is not canonical")
        expected = [path.resolve(strict=True) for path in [*expected_products, expected_marker]]
        if any(not path.is_relative_to(root) for path in expected):
            raise EvidencePublicationError("recorded transaction output escapes project root")
        writes = journal.get("writes")
        if (
            not isinstance(writes, list)
            or [row.get("path") for row in writes if isinstance(row, dict)]
            != [path.relative_to(root).as_posix() for path in expected]
        ):
            raise EvidencePublicationError("recorded transaction output set differs")
        inputs = journal.get("inputs")
        if not isinstance(inputs, list) or any(
            not isinstance(row, dict) or set(row) != {"path", "sha256", "size"}
            or not isinstance(row["path"], str) or not isinstance(row["sha256"], str)
            for row in inputs
        ):
            raise EvidencePublicationError("recorded transaction input set is malformed")
        payloads = [
            (path, (lane / "prepared" / f"{index:03d}.bin").read_bytes())
            for index, path in enumerate(expected)
        ]
        validate_committed(
            project_root=root, transaction_id=transaction_id,
            preconditions=[(Path(row["path"]), row["sha256"]) for row in inputs],
            inventory_preconditions=[], outputs=payloads[:-1], marker=payloads[-1],
        )
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise EvidencePublicationError("recorded transaction state is unreadable") from exc


def validate_committed(
    *,
    project_root: Path,
    transaction_id: str,
    preconditions: list[tuple[Path, str]],
    inventory_preconditions: list[tuple[Path, dict[str, str]]],
    outputs: list[tuple[Path, bytes]],
    marker: tuple[Path, bytes],
) -> None:
    """Validate exact published bytes and the consumed transaction journal."""
    root = project_root.resolve(strict=True)
    all_rows = [*outputs, marker]
    resolved = [(path.resolve(strict=True), data) for path, data in all_rows]
    if not transaction_id or len({path for path, _ in resolved}) != len(resolved):
        raise EvidencePublicationError("transaction id or output set is invalid")
    if any(not path.is_relative_to(root) for path, _ in resolved):
        raise EvidencePublicationError("publication output escapes project root")
    for path, expected in preconditions:
        resolved_input = path.resolve(strict=True)
        if _digest(resolved_input.read_bytes()) != expected:
            raise EvidencePublicationError(
                f"publication dependency changed during committed validation: {resolved_input}"
            )
    for inventory_root, expected in inventory_preconditions:
        resolved_inventory = inventory_root.resolve(strict=True)
        actual = {
            path.relative_to(resolved_inventory).as_posix(): _digest(path.read_bytes())
            for path in sorted(resolved_inventory.glob("*.md"))
            if path.is_file()
        }
        if actual != expected:
            raise EvidencePublicationError(
                f"publication inventory changed during committed validation: {resolved_inventory}"
            )
    plan = {
        "schema_version": "1.0.0",
        "transaction_id": transaction_id,
        "inputs": [
            {
                "path": str(path.resolve(strict=True)),
                "sha256": digest,
                "size": path.resolve(strict=True).stat().st_size,
            }
            for path, digest in preconditions
        ],
        "inventories": [
            {
                "root": str(inventory_root.resolve(strict=True)),
                "files": expected,
            }
            for inventory_root, expected in inventory_preconditions
        ],
        "outputs": [_binding(root, path, data) for path, data in resolved],
        "marker_path": resolved[-1][0].relative_to(root).as_posix(),
    }
    plan_hash = _digest(_canonical(plan))
    lane = _transaction_lane(root, transaction_id).resolve()
    if not lane.is_relative_to(root):
        raise EvidencePublicationError("transaction lane escapes project root")
    claim_path = lane / "claim.json"
    journal_path = lane / "journal.json"
    try:
        claim_raw = claim_path.read_bytes()
        journal_raw = journal_path.read_bytes()
        claim = json.loads(claim_raw.decode("utf-8", errors="strict"))
        journal = json.loads(journal_raw.decode("utf-8", errors="strict"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EvidencePublicationError("transaction state is unreadable") from exc
    if claim_raw != _canonical(claim) or journal_raw != _canonical(journal):
        raise EvidencePublicationError("transaction state is not canonical")
    if (
        claim.get("schema_version") != "1.0.0"
        or claim.get("transaction_id") != transaction_id
        or claim.get("claim_type") != "exclusive_no_ttl"
        or claim.get("state") != "consumed"
        or claim.get("plan_sha256") != plan_hash
        or not isinstance(claim.get("owner_pid"), int)
    ):
        raise EvidencePublicationError("transaction claim is inconsistent")
    expected_writes: list[dict[str, Any]] = []
    for index, row in enumerate(plan["outputs"]):
        prepared_path = lane / "prepared" / f"{index:03d}.bin"
        expected = {
            **row,
            "prepared": prepared_path.relative_to(root).as_posix(),
        }
        expected_writes.append(expected)
    writes = journal.get("writes")
    if not isinstance(writes, list) or len(writes) != len(expected_writes):
        raise EvidencePublicationError("transaction journal write set is inconsistent")
    for actual, expected in zip(writes, expected_writes, strict=True):
        prior = actual.get("prior_sha256") if isinstance(actual, dict) else None
        if prior is not None and (
            not isinstance(prior, str)
            or len(prior) != 64
            or any(char not in "0123456789abcdef" for char in prior)
        ):
            raise EvidencePublicationError("transaction prior hash is invalid")
        if not isinstance(actual, dict) or {
            key: value for key, value in actual.items() if key != "prior_sha256"
        } != expected:
            raise EvidencePublicationError("transaction journal write binding differs")
        prepared_path = (root / expected["prepared"]).resolve(strict=True)
        if (
            not prepared_path.is_relative_to(lane / "prepared")
            or _digest(prepared_path.read_bytes()) != expected["sha256"]
        ):
            raise EvidencePublicationError("prepared publication bytes are stale")
    expected_published = [row["path"] for row in writes]
    if (
        journal.get("schema_version") != "1.0.0"
        or journal.get("transaction_id") != transaction_id
        or journal.get("plan_sha256") != plan_hash
        or journal.get("state") != "published"
        or journal.get("inputs") != plan["inputs"]
        or journal.get("published") != expected_published
    ):
        raise EvidencePublicationError("transaction journal is not committed")
    for path, data in resolved:
        if path.read_bytes() != data:
            raise EvidencePublicationError("published bytes differ from exact intent")


def recover_committed(
    *,
    project_root: Path,
    transaction_id: str,
    acknowledgement: str,
    preconditions: list[tuple[Path, str]],
    inventory_preconditions: list[tuple[Path, dict[str, str]]],
    outputs: list[tuple[Path, bytes]],
    marker: tuple[Path, bytes],
    destination_validator: Callable[[Path], None],
) -> str:
    """Recover only a caller-rederived and destination-authorized intent."""
    if acknowledgement != "inspected-evidence-state-and-journal":
        raise EvidencePublicationError("exact recovery acknowledgement is required")
    root = project_root.resolve(strict=True)
    all_rows = [*outputs, marker]
    resolved = [(path.resolve(), data) for path, data in all_rows]
    if not transaction_id or len({path for path, _ in resolved}) != len(resolved):
        raise EvidencePublicationError("transaction id or output set is invalid")
    if any(not path.is_relative_to(root) for path, _ in resolved):
        raise EvidencePublicationError("publication output escapes project root")
    _preflight_control_and_outputs(
        root,
        transaction_id,
        resolved,
        purpose="evidence recovery",
        include_recovery=True,
    )
    for path, _data in resolved:
        destination_validator(path)
    for path, expected in preconditions:
        resolved_input = path.resolve(strict=True)
        if _digest(resolved_input.read_bytes()) != expected:
            raise EvidencePublicationError(
                f"publication dependency changed before recovery: {resolved_input}"
            )
    for inventory_root, expected in inventory_preconditions:
        resolved_inventory = inventory_root.resolve(strict=True)
        actual = {
            path.relative_to(resolved_inventory).as_posix(): _digest(path.read_bytes())
            for path in sorted(resolved_inventory.glob("*.md"))
            if path.is_file()
        }
        if actual != expected:
            raise EvidencePublicationError(
                f"publication inventory changed before recovery: {resolved_inventory}"
            )
    plan = {
        "schema_version": "1.0.0",
        "transaction_id": transaction_id,
        "inputs": [
            {
                "path": str(path.resolve(strict=True)),
                "sha256": digest,
                "size": path.resolve(strict=True).stat().st_size,
            }
            for path, digest in preconditions
        ],
        "inventories": [
            {
                "root": str(inventory_root.resolve(strict=True)),
                "files": expected,
            }
            for inventory_root, expected in inventory_preconditions
        ],
        "outputs": [_binding(root, path, data) for path, data in resolved],
        "marker_path": resolved[-1][0].relative_to(root).as_posix(),
    }
    plan_hash = _digest(_canonical(plan))
    with _hold_bound_tree(root) as tree:
        for path, _data in resolved:
            tree.ensure_directory(path.parent)
        tree.ensure_directory(_transaction_control_root(root))
        tree.ensure_directory(_transaction_lane(root, transaction_id))
        tree.ensure_directory(_transaction_lane(root, transaction_id) / "prepared")
        tree.ensure_directory(_transaction_lane(root, transaction_id) / "recovery")
        return _finish_recover_committed(
            root,
            transaction_id,
            preconditions,
            inventory_preconditions,
            resolved,
            plan,
            plan_hash,
            destination_validator,
        )


def _finish_recover_committed(
    root: Path,
    transaction_id: str,
    preconditions: list[tuple[Path, str]],
    inventory_preconditions: list[tuple[Path, dict[str, str]]],
    resolved: list[tuple[Path, bytes]],
    plan: dict[str, Any],
    plan_hash: str,
    destination_validator: Callable[[Path], None],
) -> str:
    lane = _assert_bound_path(
        root,
        _transaction_lane(root, transaction_id),
        "evidence recovery transaction state",
    )
    claim_path = lane / "claim.json"
    journal_path = lane / "journal.json"
    with (
        _claim_lock(_publication_lock_path(root), root=root),
        _claim_lock(lane / "claim.lock", root=root),
    ):
        for path, _data in resolved:
            destination_validator(path)
        for path, expected in preconditions:
            resolved_input = path.resolve(strict=True)
            if _digest(resolved_input.read_bytes()) != expected:
                raise EvidencePublicationError(
                    f"publication dependency changed under recovery claims: {resolved_input}"
                )
        for inventory_root, expected in inventory_preconditions:
            resolved_inventory = inventory_root.resolve(strict=True)
            actual = {
                path.relative_to(resolved_inventory).as_posix(): _digest(path.read_bytes())
                for path in sorted(resolved_inventory.glob("*.md"))
                if path.is_file()
            }
            if actual != expected:
                raise EvidencePublicationError(
                    f"publication inventory changed under recovery claims: {resolved_inventory}"
                )
        try:
            claim_raw = claim_path.read_bytes()
            journal_raw = journal_path.read_bytes()
            claim = json.loads(claim_raw.decode("utf-8", errors="strict"))
            journal = json.loads(journal_raw.decode("utf-8", errors="strict"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise EvidencePublicationError("transaction state is unreadable") from exc
        if claim_raw != _canonical(claim) or journal_raw != _canonical(journal):
            raise EvidencePublicationError("transaction state is not canonical")
        if (
            claim.get("schema_version") != "1.0.0"
            or claim.get("transaction_id") != transaction_id
            or claim.get("claim_type") != "exclusive_no_ttl"
            or claim.get("state") not in {"active", "consumed"}
            or claim.get("plan_sha256") != plan_hash
            or not isinstance(claim.get("owner_pid"), int)
            or journal.get("schema_version") != "1.0.0"
            or journal.get("transaction_id") != transaction_id
            or journal.get("plan_sha256") != plan_hash
            or journal.get("state") not in {
                "prepared", "publishing", "published", "recovery_required"
            }
            or journal.get("inputs") != plan["inputs"]
            or not isinstance(journal.get("writes"), list)
            or len(journal["writes"]) != len(resolved)
        ):
            raise EvidencePublicationError("transaction state is inconsistent")
        expected_writes: list[dict[str, Any]] = []
        for index, row in enumerate(plan["outputs"]):
            expected_writes.append({
                **row,
                "prepared": (
                    lane / "prepared" / f"{index:03d}.bin"
                ).relative_to(root).as_posix(),
            })
        for actual, expected in zip(journal["writes"], expected_writes, strict=True):
            prior = actual.get("prior_sha256") if isinstance(actual, dict) else None
            if prior is not None and (
                not isinstance(prior, str)
                or len(prior) != 64
                or any(char not in "0123456789abcdef" for char in prior)
            ):
                raise EvidencePublicationError("transaction prior hash is invalid")
            if not isinstance(actual, dict) or {
                key: value for key, value in actual.items() if key != "prior_sha256"
            } != expected:
                raise EvidencePublicationError("transaction journal differs from intent")
            prepared_path = (root / expected["prepared"]).resolve(strict=True)
            if (
                not prepared_path.is_relative_to(lane / "prepared")
                or _digest(prepared_path.read_bytes()) != expected["sha256"]
            ):
                raise EvidencePublicationError("prepared recovery bytes are stale")
        states: list[str] = []
        for row, (destination, data) in zip(journal["writes"], resolved, strict=True):
            actual = (
                _digest(destination.read_bytes())
                if destination.is_file()
                else None
            )
            if actual == _digest(data):
                states.append("desired")
            elif actual == row.get("prior_sha256"):
                states.append("prior")
            else:
                journal["state"] = "recovery_required"
                _durable_write(journal_path, _canonical(journal), root=root)
                raise EvidencePublicationError(
                    "published bytes diverge from prior state and intent"
                )
        marker_state = states[-1]
        if marker_state == "desired":
            if any(state != "desired" for state in states[:-1]):
                journal["state"] = "recovery_required"
                _durable_write(journal_path, _canonical(journal), root=root)
                raise EvidencePublicationError(
                    "visible commit marker has a non-matching output prefix"
                )
            journal["published"] = [row["path"] for row in expected_writes]
            journal["state"] = "published"
            claim["state"] = "consumed"
            _durable_write(journal_path, _canonical(journal), root=root)
            _durable_write(claim_path, _canonical(claim), root=root)
            return "committed"
        marker_destination = resolved[-1][0]
        if marker_destination.exists():
            journal["state"] = "recovery_required"
            _durable_write(journal_path, _canonical(journal), root=root)
            raise EvidencePublicationError(
                "prior marker occupies the exclusive commit path"
            )
        recovery_root = lane / "recovery"
        _require_bound_tree(root).ensure_directory(recovery_root)
        record_path = recovery_root / (
            f"{time.time_ns()}-{uuid.uuid4().hex}.json"
        )
        if all(state == "prior" for state in states):
            journal["state"] = "rolled_back"
            claim["state"] = "recovered_rollback"
            _durable_write(journal_path, _canonical(journal), root=root)
            _durable_write(claim_path, _canonical(claim), root=root)
            _exclusive_json(
                record_path,
                {
                    "schema_version": "1.0.0",
                    "transaction_id": transaction_id,
                    "recovery": "rolled_back_no_durable_effects",
                    "plan_sha256": journal["plan_sha256"],
                },
                root=root,
                purpose="evidence recovery",
            )
            return "rolled_back"
        for row, state, (_destination, _data) in zip(
            journal["writes"], states, resolved, strict=True
        ):
            if state == "desired":
                continue
            prepared_path = _assert_bound_path(
                root, root / row["prepared"], "evidence recovery"
            )
            if (
                not prepared_path.is_relative_to(lane / "prepared")
                or hashlib.sha256(prepared_path.read_bytes()).hexdigest()
                != row["sha256"]
            ):
                raise EvidencePublicationError("prepared recovery bytes are stale")
            live_destination = _assert_bound_path(
                root, root / row["path"], "evidence recovery"
            )
            if row is journal["writes"][-1]:
                _exclusive_marker(
                    live_destination,
                    prepared_path.read_bytes(),
                    root=root,
                    purpose="evidence recovery",
                )
            else:
                _durable_write(
                    live_destination,
                    prepared_path.read_bytes(),
                    root=root,
                    purpose="evidence recovery",
                )
        journal["published"] = [row["path"] for row in expected_writes]
        journal["state"] = "published"
        claim["state"] = "consumed"
        _durable_write(journal_path, _canonical(journal), root=root)
        _durable_write(claim_path, _canonical(claim), root=root)
        _exclusive_json(
            record_path,
            {
                "schema_version": "1.0.0",
                "transaction_id": transaction_id,
                "recovery": "rolled_forward_exact_intent",
                "plan_sha256": journal["plan_sha256"],
            },
            root=root,
            purpose="evidence recovery",
        )
        return "committed"
