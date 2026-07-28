#!/usr/bin/env python3
"""Strict content-addressed cache primitives for the fixture runner.

This module does not decide authority, discover the repository cache root, or
acquire the repository-global runner lock.  Its caller must do all three.  It
only validates complete cache bases, stages canonical entries, and publishes
them through an explicit final no-replace operation.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any, Iterable, Mapping
import uuid


FIXTURE_CACHE_INVALID = "FIXTURE-CACHE-INVALID"
FIXTURE_CACHE_PUBLICATION = "FIXTURE-CACHE-PUBLICATION"
CACHE_SCHEMA = "coauthor-fixture-cache/v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class CacheError(RuntimeError):
    """A typed cache validation or publication refusal."""

    def __init__(self, code: str, message: str):
        if code not in {FIXTURE_CACHE_INVALID, FIXTURE_CACHE_PUBLICATION}:
            raise ValueError(f"unknown fixture-cache refusal code: {code}")
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class _CacheMiss:
    def __repr__(self) -> str:
        return "MISS"


MISS = _CacheMiss()


@dataclass(frozen=True)
class StagedEntry:
    """An unpublished canonical entry owned by one caller run."""

    cache_root: Path
    key: str
    staged_path: Path
    final_path: Path
    payload_sha256: str


class _DuplicateKey(ValueError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_json_value(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if type(value) is int:
        return
    if isinstance(value, float):
        raise CacheError(
            FIXTURE_CACHE_INVALID,
            f"{path} contains a floating-point value; cache bases require exact JSON values",
        )
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise CacheError(
                    FIXTURE_CACHE_INVALID, f"{path} contains a non-string object key"
                )
            _validate_json_value(item, f"{path}.{key}")
        return
    raise CacheError(
        FIXTURE_CACHE_INVALID,
        f"{path} contains a non-JSON value of type {type(value).__name__}",
    )


def canonical_json_bytes(value: Any) -> bytes:
    """Return the sole cache serialization: sorted compact UTF-8 plus LF."""

    _validate_json_value(value)
    try:
        text = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        return (text + "\n").encode("utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise CacheError(
            FIXTURE_CACHE_INVALID, f"value cannot be canonically serialized: {exc}"
        ) from exc


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _load_strict_json(raw: bytes) -> Any:
    try:
        text = raw.decode("utf-8", errors="strict")
        return json.loads(text, object_pairs_hook=_strict_object)
    except _DuplicateKey as exc:
        raise CacheError(
            FIXTURE_CACHE_INVALID, f"cache JSON contains duplicate key {str(exc)!r}"
        ) from exc
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CacheError(
            FIXTURE_CACHE_INVALID, f"cache entry is not strict UTF-8 JSON: {exc}"
        ) from exc


def _require_sha256(value: Any, label: str) -> None:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise CacheError(
            FIXTURE_CACHE_INVALID, f"{label} must be a lowercase SHA-256 digest"
        )


def validate_basis(basis: Any) -> dict[str, Any]:
    """Validate the minimum complete basis while binding every caller field."""

    if not isinstance(basis, dict) or not basis:
        raise CacheError(FIXTURE_CACHE_INVALID, "cache basis must be a nonempty object")
    required = {
        "runner_sha256",
        "census_sha256",
        "cache_helper_sha256",
        "suite_sha256",
        "invocation_contract",
        "tested_inputs",
    }
    missing = sorted(required - set(basis))
    if missing:
        raise CacheError(
            FIXTURE_CACHE_INVALID,
            f"cache basis is incomplete; missing {', '.join(missing)}",
        )
    for key in (
        "runner_sha256",
        "census_sha256",
        "cache_helper_sha256",
        "suite_sha256",
    ):
        _require_sha256(basis.get(key), f"basis.{key}")
    invocation = basis.get("invocation_contract")
    if not isinstance(invocation, dict) or not invocation:
        raise CacheError(
            FIXTURE_CACHE_INVALID,
            "basis.invocation_contract must be a nonempty exact invocation object",
        )
    tested = basis.get("tested_inputs")
    if not isinstance(tested, dict):
        raise CacheError(
            FIXTURE_CACHE_INVALID, "basis.tested_inputs must be an object"
        )
    _require_sha256(tested.get("sha256"), "basis.tested_inputs.sha256")
    _require_sha256(tested.get("raw_sha256"), "basis.tested_inputs.raw_sha256")
    # Canonical round-trip produces a detached JSON value and catches every
    # unsupported nested value without relying on caller object identity.
    return _load_strict_json(canonical_json_bytes(basis))


def basis_key(basis: Mapping[str, Any]) -> str:
    validated = validate_basis(basis)
    return sha256_bytes(canonical_json_bytes(validated))


def make_entry(
    *,
    basis: Mapping[str, Any],
    observed_exit: int,
    stdout_sha256: str,
    stderr_sha256: str,
    source_run_id: str,
) -> dict[str, Any]:
    validated_basis = validate_basis(basis)
    if type(observed_exit) is not int:
        raise CacheError(FIXTURE_CACHE_INVALID, "observed_exit must be an integer")
    _require_sha256(stdout_sha256, "stdout_sha256")
    _require_sha256(stderr_sha256, "stderr_sha256")
    if (
        not isinstance(source_run_id, str)
        or not source_run_id.strip()
        or source_run_id != source_run_id.strip()
    ):
        raise CacheError(
            FIXTURE_CACHE_INVALID, "source_run_id must be a nonempty trimmed string"
        )
    key = basis_key(validated_basis)
    body = {
        "schema": CACHE_SCHEMA,
        "key": key,
        "basis": validated_basis,
        "result": {
            "observed_exit": observed_exit,
            "stdout_sha256": stdout_sha256,
            "stderr_sha256": stderr_sha256,
            "source_run_id": source_run_id,
        },
    }
    return {**body, "entry_sha256": sha256_bytes(canonical_json_bytes(body))}


def validate_entry(
    entry: Any,
    *,
    expected_basis: Mapping[str, Any] | None = None,
    expected_key: str | None = None,
) -> dict[str, Any]:
    if not isinstance(entry, dict) or set(entry) != {
        "schema",
        "key",
        "basis",
        "result",
        "entry_sha256",
    }:
        raise CacheError(
            FIXTURE_CACHE_INVALID,
            "cache entry must contain exactly schema, key, basis, result, and entry_sha256",
        )
    if entry.get("schema") != CACHE_SCHEMA:
        raise CacheError(FIXTURE_CACHE_INVALID, "cache entry schema is unknown")
    basis = validate_basis(entry.get("basis"))
    actual_key = basis_key(basis)
    if entry.get("key") != actual_key:
        raise CacheError(
            FIXTURE_CACHE_INVALID, "cache entry key does not hash its exact basis"
        )
    if expected_key is not None and actual_key != expected_key:
        raise CacheError(
            FIXTURE_CACHE_INVALID, "cache entry belongs to another expected key"
        )
    if expected_basis is not None:
        wanted = validate_basis(expected_basis)
        if canonical_json_bytes(basis) != canonical_json_bytes(wanted):
            raise CacheError(
                FIXTURE_CACHE_INVALID, "cache entry binds another execution basis"
            )
    result = entry.get("result")
    if not isinstance(result, dict) or set(result) != {
        "observed_exit",
        "stdout_sha256",
        "stderr_sha256",
        "source_run_id",
    }:
        raise CacheError(
            FIXTURE_CACHE_INVALID,
            "cache result must contain exactly observed_exit, output hashes, and source_run_id",
        )
    if type(result.get("observed_exit")) is not int:
        raise CacheError(FIXTURE_CACHE_INVALID, "cached observed_exit must be an integer")
    _require_sha256(result.get("stdout_sha256"), "result.stdout_sha256")
    _require_sha256(result.get("stderr_sha256"), "result.stderr_sha256")
    source_run_id = result.get("source_run_id")
    if (
        not isinstance(source_run_id, str)
        or not source_run_id.strip()
        or source_run_id != source_run_id.strip()
    ):
        raise CacheError(
            FIXTURE_CACHE_INVALID, "cached source_run_id must be a nonempty trimmed string"
        )
    _require_sha256(entry.get("entry_sha256"), "entry.entry_sha256")
    integrity_body = {key: value for key, value in entry.items() if key != "entry_sha256"}
    if entry["entry_sha256"] != sha256_bytes(canonical_json_bytes(integrity_body)):
        raise CacheError(FIXTURE_CACHE_INVALID, "cache entry integrity hash is stale")
    return _load_strict_json(canonical_json_bytes(entry))


def parse_entry_bytes(
    raw: bytes,
    *,
    expected_basis: Mapping[str, Any] | None = None,
    expected_key: str | None = None,
) -> dict[str, Any]:
    entry = _load_strict_json(raw)
    validated = validate_entry(
        entry, expected_basis=expected_basis, expected_key=expected_key
    )
    if raw != canonical_json_bytes(validated):
        raise CacheError(
            FIXTURE_CACHE_INVALID, "cache entry bytes are not canonical JSON"
        )
    return validated


def _absolute_lexical(path: Path) -> Path:
    if not path.is_absolute():
        raise CacheError(FIXTURE_CACHE_INVALID, "cache root must be an absolute path")
    return Path(os.path.abspath(os.fspath(path)))


def _is_reparse(st: os.stat_result) -> bool:
    if stat.S_ISLNK(st.st_mode):
        return True
    attributes = getattr(st, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse_flag)


def _assert_no_reparse(path: Path, *, code: str) -> None:
    chain = list(reversed((path, *path.parents)))
    for component in chain:
        try:
            metadata = os.lstat(component)
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise CacheError(code, f"cannot inspect cache path component {component}: {exc}") from exc
        if _is_reparse(metadata):
            raise CacheError(code, f"cache path crosses symlink/reparse point: {component}")


def _prepare_root(cache_root: Path) -> Path:
    root = _absolute_lexical(cache_root)
    _assert_no_reparse(root.parent, code=FIXTURE_CACHE_PUBLICATION)
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise CacheError(
            FIXTURE_CACHE_PUBLICATION, f"cannot create cache root {root}: {exc}"
        ) from exc
    _assert_no_reparse(root, code=FIXTURE_CACHE_PUBLICATION)
    if not root.is_dir():
        raise CacheError(FIXTURE_CACHE_PUBLICATION, "cache root is not a directory")
    return root


def _read_regular(path: Path, *, code: str) -> bytes:
    _assert_no_reparse(path, code=code)
    try:
        metadata = os.lstat(path)
        if not stat.S_ISREG(metadata.st_mode):
            raise CacheError(code, f"cache path is not a regular file: {path}")
        return path.read_bytes()
    except CacheError:
        raise
    except OSError as exc:
        raise CacheError(code, f"cannot read cache entry {path}: {exc}") from exc


def lookup(cache_root: Path, basis: Mapping[str, Any]) -> dict[str, Any] | _CacheMiss:
    """Return a verified entry, or MISS only when the expected path is absent."""

    validated_basis = validate_basis(basis)
    key = basis_key(validated_basis)
    root = _absolute_lexical(cache_root)
    _assert_no_reparse(root, code=FIXTURE_CACHE_INVALID)
    try:
        root_metadata = os.lstat(root)
    except FileNotFoundError:
        return MISS
    except OSError as exc:
        raise CacheError(
            FIXTURE_CACHE_INVALID, f"cannot inspect cache root {root}: {exc}"
        ) from exc
    if not stat.S_ISDIR(root_metadata.st_mode):
        raise CacheError(FIXTURE_CACHE_INVALID, "cache root is not a directory")
    expected = root / f"{key}.json"
    try:
        os.lstat(expected)
    except FileNotFoundError:
        return MISS
    except OSError as exc:
        raise CacheError(
            FIXTURE_CACHE_INVALID, f"cannot inspect expected cache entry {expected}: {exc}"
        ) from exc
    raw = _read_regular(expected, code=FIXTURE_CACHE_INVALID)
    return parse_entry_bytes(raw, expected_basis=validated_basis, expected_key=key)


def stage_entry(
    cache_root: Path,
    *,
    basis: Mapping[str, Any],
    observed_exit: int,
    stdout_sha256: str,
    stderr_sha256: str,
    source_run_id: str,
) -> StagedEntry:
    """Write one unpublished, run-unique staged entry."""

    root = _prepare_root(cache_root)
    entry = make_entry(
        basis=basis,
        observed_exit=observed_exit,
        stdout_sha256=stdout_sha256,
        stderr_sha256=stderr_sha256,
        source_run_id=source_run_id,
    )
    raw = canonical_json_bytes(entry)
    key = entry["key"]
    final_path = root / f"{key}.json"
    staged_path = root / f".{key}.{uuid.uuid4().hex}.staged"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    try:
        descriptor = os.open(staged_path, flags, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if _read_regular(staged_path, code=FIXTURE_CACHE_PUBLICATION) != raw:
            raise CacheError(
                FIXTURE_CACHE_PUBLICATION, "staged cache entry differs on readback"
            )
    except CacheError:
        try:
            staged_path.unlink()
        except FileNotFoundError:
            pass
        raise
    except OSError as exc:
        try:
            staged_path.unlink()
        except FileNotFoundError:
            pass
        raise CacheError(
            FIXTURE_CACHE_PUBLICATION, f"cannot stage cache entry: {exc}"
        ) from exc
    return StagedEntry(
        cache_root=root,
        key=key,
        staged_path=staged_path,
        final_path=final_path,
        payload_sha256=sha256_bytes(raw),
    )


def _validate_staged(staged: StagedEntry) -> bytes:
    root = _absolute_lexical(staged.cache_root)
    if staged.cache_root != root:
        raise CacheError(FIXTURE_CACHE_PUBLICATION, "staged cache root is not canonical")
    if staged.final_path != root / f"{staged.key}.json":
        raise CacheError(FIXTURE_CACHE_PUBLICATION, "staged final path is not key-derived")
    if staged.staged_path.parent != root or staged.staged_path.suffix != ".staged":
        raise CacheError(FIXTURE_CACHE_PUBLICATION, "staged path is outside its cache root")
    _require_sha256(staged.key, "staged key")
    expected_prefix = f".{staged.key}."
    staged_name = staged.staged_path.name
    run_token = staged_name[len(expected_prefix) : -len(".staged")]
    if not staged_name.startswith(expected_prefix) or not re.fullmatch(
        r"[0-9a-f]{32}", run_token
    ):
        raise CacheError(
            FIXTURE_CACHE_PUBLICATION, "staged path is not a run-unique key-derived name"
        )
    _require_sha256(staged.payload_sha256, "staged payload_sha256")
    raw = _read_regular(staged.staged_path, code=FIXTURE_CACHE_PUBLICATION)
    if sha256_bytes(raw) != staged.payload_sha256:
        raise CacheError(FIXTURE_CACHE_PUBLICATION, "staged payload hash is stale")
    parse_entry_bytes(raw, expected_key=staged.key)
    return raw


def _remove_staged(staged_items: Iterable[StagedEntry]) -> list[str]:
    failures: list[str] = []
    for staged in staged_items:
        try:
            os.unlink(staged.staged_path)
        except FileNotFoundError:
            pass
        except OSError as exc:
            failures.append(f"{staged.staged_path}: {exc}")
    return failures


def discard_staged(staged_items: Iterable[StagedEntry]) -> None:
    """Discard an uncommitted RED/VOID run's staged entries."""

    items = tuple(staged_items)
    failures = _remove_staged(items)
    if failures:
        raise CacheError(
            FIXTURE_CACHE_PUBLICATION,
            "cannot remove staged cache entries: " + "; ".join(failures),
        )


def publish_staged(staged_items: Iterable[StagedEntry]) -> list[Path]:
    """Final-call publication: exclusive, no-replace, exact-readback, cleanup."""

    items = tuple(staged_items)
    payloads: list[bytes] = []
    published: list[Path] = []
    created_by_call: list[Path] = []
    failure: Exception | None = None
    try:
        if len({item.final_path for item in items}) != len(items):
            raise CacheError(
                FIXTURE_CACHE_PUBLICATION,
                "final publication contains duplicate cache keys",
            )
        # Preflight every staged byte and every existing final path before
        # exposing the first new final path.  Publication is a set operation:
        # a conflict in item N must not leave items 0..N-1 newly visible.
        payloads = [_validate_staged(item) for item in items]
        for item, raw in zip(items, payloads):
            _assert_no_reparse(item.cache_root, code=FIXTURE_CACHE_PUBLICATION)
            try:
                os.lstat(item.final_path)
            except FileNotFoundError:
                continue
            except OSError as exc:
                raise CacheError(
                    FIXTURE_CACHE_PUBLICATION,
                    f"cannot inspect final cache entry for {item.key}: {exc}",
                ) from exc
            existing = _read_regular(item.final_path, code=FIXTURE_CACHE_PUBLICATION)
            if existing != raw:
                raise CacheError(
                    FIXTURE_CACHE_PUBLICATION,
                    f"conflicting cache entry already exists for key {item.key}",
                )
        for item, raw in zip(items, payloads):
            _assert_no_reparse(item.cache_root, code=FIXTURE_CACHE_PUBLICATION)
            try:
                os.link(item.staged_path, item.final_path, follow_symlinks=False)
                created_by_call.append(item.final_path)
            except FileExistsError:
                existing = _read_regular(
                    item.final_path, code=FIXTURE_CACHE_PUBLICATION
                )
                if existing != raw:
                    raise CacheError(
                        FIXTURE_CACHE_PUBLICATION,
                        f"conflicting cache entry already exists for key {item.key}",
                    )
            except OSError as exc:
                raise CacheError(
                    FIXTURE_CACHE_PUBLICATION,
                    f"exclusive hard-link publication unavailable for {item.key}: {exc}",
                ) from exc
            readback = _read_regular(item.final_path, code=FIXTURE_CACHE_PUBLICATION)
            if readback != raw:
                raise CacheError(
                    FIXTURE_CACHE_PUBLICATION,
                    f"published cache entry differs on readback for key {item.key}",
                )
            parse_entry_bytes(readback, expected_key=item.key)
            published.append(item.final_path)
    except Exception as exc:
        failure = exc
        rollback_failures: list[str] = []
        for path in reversed(created_by_call):
            try:
                os.unlink(path)
            except FileNotFoundError:
                pass
            except OSError as rollback_exc:
                rollback_failures.append(f"{path}: {rollback_exc}")
        if rollback_failures:
            failure = CacheError(
                FIXTURE_CACHE_PUBLICATION,
                "cache publication rollback failed: " + "; ".join(rollback_failures),
            )
    cleanup_failures = _remove_staged(items)
    if cleanup_failures:
        raise CacheError(
            FIXTURE_CACHE_PUBLICATION,
            "cache publication left staged residue: " + "; ".join(cleanup_failures),
        ) from failure
    if failure is not None:
        if isinstance(failure, CacheError):
            raise failure
        raise CacheError(
            FIXTURE_CACHE_PUBLICATION, f"unexpected cache publication failure: {failure}"
        ) from failure
    return published


__all__ = [
    "CACHE_SCHEMA",
    "FIXTURE_CACHE_INVALID",
    "FIXTURE_CACHE_PUBLICATION",
    "MISS",
    "CacheError",
    "StagedEntry",
    "basis_key",
    "canonical_json_bytes",
    "discard_staged",
    "lookup",
    "make_entry",
    "parse_entry_bytes",
    "publish_staged",
    "sha256_bytes",
    "stage_entry",
    "validate_basis",
    "validate_entry",
]
