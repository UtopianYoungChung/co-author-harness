#!/usr/bin/env python3
"""Receipted 1.0.0 audited -> 1.1.0 derived handoff-policy migration.

Dry-run and verify are read-only. Apply and rollback use one exclusive no-TTL
claim and replace ``reviews/phase_state.json`` only after every dependency and
prepared receipt has been rechecked. The migration lane is evidence, never a
second lifecycle authority.
"""

from __future__ import annotations

import argparse
import base64
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import stat
import sys
import uuid
from typing import Any, Callable


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import milestone_framework_validate as milestone_validator  # noqa: E402
from milestone_handoff_policy import (  # noqa: E402
    DERIVED_POLICY,
    HandoffPolicyResolutionError,
    IMPLICIT_AUDITED_COMPATIBILITY,
    resolve_handoff_policy,
)


MIGRATION_ID = "lab-iteration-derived-handoff-v1"
LEDGER_REL = "reviews/phase_state.json"
LANE_REL = f"reviews/.harness/migrations/{MIGRATION_ID}"
LIVE_CLAIM_REL = f"{LANE_REL}/transaction.lock"
EXCLUDED_PATHS = [LEDGER_REL, f"{LANE_REL}/**"]

AUTHORITY_SCHEMA = "co-author-harness/milestone-handoff-policy-migration-authority/v1"
CLAIM_SCHEMA = "co-author-harness/milestone-handoff-policy-migration-claim/v1"
RECEIPT_SCHEMA = "co-author-harness/milestone-handoff-policy-migration-receipt/v1"
ROLLBACK_MANIFEST_SCHEMA = "co-author-harness/milestone-handoff-policy-migration-rollback-manifest/v1"
ROLLBACK_RECEIPT_SCHEMA = "co-author-harness/milestone-handoff-policy-migration-rollback-receipt/v1"

SCHEMA_PATHS = {
    "authority": ROOT / "references/schemas/milestone_handoff_policy_migration_authority.schema.json",
    "claim": ROOT / "references/schemas/milestone_handoff_policy_migration_claim.schema.json",
    "receipt": ROOT / "references/schemas/milestone_handoff_policy_migration_receipt.schema.json",
    "rollback_manifest": ROOT / "references/schemas/milestone_handoff_policy_migration_rollback_manifest.schema.json",
    "rollback_receipt": ROOT / "references/schemas/milestone_handoff_policy_migration_rollback_receipt.schema.json",
}

PERMITTED_CHANGES = [
    {"path": "/milestone_framework/contract_version", "from": "1.0.0", "to": "1.1.0"},
    {"path": "/milestone_framework/handoff_policy", "from": None, "to": "derived"},
]
STATE_LAST = {
    "atomic_replace": True,
    "dependencies_rechecked": True,
    "concurrent_hash_rechecked": True,
}

AUTHORITY_REQUIRED = "MHD-MIGRATION-AUTHORITY-REQUIRED"
AUTHORITY_INVALID = "MHD-MIGRATION-AUTHORITY-INVALID"
PREIMAGE_MISMATCH = "MHD-MIGRATION-PREIMAGE-MISMATCH"
LEDGER_INVALID = "MHD-MIGRATION-LEDGER-INVALID"
ACTIVE_CLAIM = "MHD-MIGRATION-ACTIVE-CLAIM"
IN_USE = "MHD-MIGRATION-IN-USE"
RECOVERY_ACK = "MHD-MIGRATION-RECOVERY-ACK"
RECOVERY_FOREIGN = "MHD-MIGRATION-RECOVERY-FOREIGN"
RECOVERY_LIVE = "MHD-MIGRATION-RECOVERY-LIVE"
RECOVERY_LIVENESS = "MHD-MIGRATION-RECOVERY-LIVENESS"
RECOVERY_STATE_MISMATCH = "MHD-MIGRATION-RECOVERY-STATE-MISMATCH"
CONCURRENT_CHANGE = "MHD-MIGRATION-CONCURRENT-CHANGE"
POSTIMAGE_INVALID = "MHD-MIGRATION-POSTIMAGE-INVALID"
RECEIPT_TAMPERED = "MHD-MIGRATION-RECEIPT-TAMPERED"
VERIFY_FAILED = "MHD-MIGRATION-VERIFY-FAILED"
ROLLBACK_STATE_MISMATCH = "MHD-MIGRATION-ROLLBACK-STATE-MISMATCH"
ROLLBACK_RESTORE_FAILED = "MHD-MIGRATION-ROLLBACK-RESTORE-FAILED"

UTC_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z$")


class MigrationError(RuntimeError):
    """One stable fail-closed migration refusal."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def _sha_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _image(payload: bytes) -> dict[str, Any]:
    return {"sha256": _sha_bytes(payload), "bytes": len(payload)}


def _timestamp(value: str | None = None) -> str:
    result = value or datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    if not isinstance(result, str) or UTC_RE.fullmatch(result) is None:
        raise MigrationError(LEDGER_INVALID, "timestamp must be strict UTC ending in Z")
    try:
        datetime.fromisoformat(result[:-1] + "+00:00")
    except ValueError as exc:
        raise MigrationError(LEDGER_INVALID, f"invalid UTC timestamp: {result}") from exc
    return result


def _is_reparse(path: Path) -> bool:
    try:
        attrs = getattr(os.lstat(path), "st_file_attributes", 0)
    except OSError:
        return False
    return path.is_symlink() or bool(attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def _project(project: Path) -> Path:
    try:
        resolved = project.resolve(strict=True)
    except OSError as exc:
        raise MigrationError(LEDGER_INVALID, f"project root is unavailable: {project}") from exc
    if not resolved.is_dir() or _is_reparse(resolved):
        raise MigrationError(LEDGER_INVALID, f"project root is not a plain directory: {resolved}")
    return resolved


def _safe_path(project: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise MigrationError(RECEIPT_TAMPERED, f"unsafe project-relative path: {relative!r}")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise MigrationError(RECEIPT_TAMPERED, f"unsafe project-relative path: {relative!r}")
    current = project
    for part in pure.parts:
        current = current / part
        if current.exists() and _is_reparse(current):
            raise MigrationError(RECEIPT_TAMPERED, f"path traverses a link or reparse point: {relative}")
    try:
        current.resolve(strict=False).relative_to(project)
    except (OSError, ValueError) as exc:
        raise MigrationError(RECEIPT_TAMPERED, f"path escapes project root: {relative}") from exc
    return current


def _plain_file(path: Path, code: str, label: str) -> None:
    if not path.is_file() or _is_reparse(path):
        raise MigrationError(code, f"{label} is not a plain file: {path}")


def _supplied_file(project: Path, supplied: Path | None, code: str, label: str) -> tuple[Path, str]:
    if supplied is None:
        raise MigrationError(code, f"{label} is required")
    candidate = supplied if supplied.is_absolute() else project / supplied
    try:
        resolved = candidate.resolve(strict=True)
        relative = resolved.relative_to(project).as_posix()
    except (OSError, ValueError) as exc:
        raise MigrationError(code, f"{label} must be contained by the project root") from exc
    safe = _safe_path(project, relative)
    _plain_file(safe, code, label)
    return safe, relative


def _binding(project: Path, path: Path) -> dict[str, str]:
    _plain_file(path, RECEIPT_TAMPERED, "bound evidence")
    return {"path": path.relative_to(project).as_posix(), "sha256": _sha_bytes(path.read_bytes())}


def _read_object(path: Path, code: str, label: str) -> tuple[dict[str, Any], bytes]:
    _plain_file(path, code, label)
    payload = path.read_bytes()
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise MigrationError(code, f"{label} is not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise MigrationError(code, f"{label} must be a JSON object")
    return value, payload


def _validate_schema(kind: str, value: dict[str, Any], code: str) -> None:
    path = SCHEMA_PATHS[kind]
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
        from jsonschema import Draft202012Validator
        errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda item: list(item.absolute_path))
    except (OSError, UnicodeError, json.JSONDecodeError, ImportError) as exc:
        raise MigrationError(code, f"cannot load migration {kind} schema: {exc}") from exc
    if errors:
        first = errors[0]
        where = "/".join(str(item) for item in first.absolute_path) or "$"
        raise MigrationError(code, f"{kind} schema refusal at {where}: {first.message}")


def _ensure_directory(path: Path, project: Path) -> None:
    try:
        path.resolve(strict=False).relative_to(project)
    except (OSError, ValueError) as exc:
        raise MigrationError(LEDGER_INVALID, f"migration directory escapes project: {path}") from exc
    missing: list[Path] = []
    current = path
    while not current.exists():
        missing.append(current)
        current = current.parent
    if not current.is_dir() or _is_reparse(current):
        raise MigrationError(LEDGER_INVALID, f"migration ancestor is not a plain directory: {current}")
    for directory in reversed(missing):
        directory.mkdir()
        if _is_reparse(directory):
            raise MigrationError(LEDGER_INVALID, f"created migration directory became linked: {directory}")


def _fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def _publish_exact(
    path: Path,
    payload: bytes,
    project: Path,
    *,
    code: str = RECEIPT_TAMPERED,
) -> None:
    _ensure_directory(path.parent, project)
    if path.exists() or path.is_symlink():
        if not path.is_file() or _is_reparse(path) or path.read_bytes() != payload:
            raise MigrationError(code, f"existing transaction evidence conflicts: {path}")
        return
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if not path.is_file() or _is_reparse(path) or path.read_bytes() != payload:
                raise MigrationError(code, f"concurrent transaction evidence conflicts: {path}")
        _fsync_directory(path.parent)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _assert_publishable_exact(path: Path, payload: bytes, project: Path, *, code: str) -> None:
    try:
        path.resolve(strict=False).relative_to(project)
    except (OSError, ValueError) as exc:
        raise MigrationError(code, f"transaction evidence target escapes project: {path}") from exc
    if _is_reparse(path.parent) or not path.parent.is_dir():
        raise MigrationError(code, f"transaction evidence parent is not a plain directory: {path.parent}")
    if path.exists() or path.is_symlink():
        if not path.is_file() or _is_reparse(path) or path.read_bytes() != payload:
            raise MigrationError(code, f"existing transaction evidence conflicts: {path}")


def _replace_state(path: Path, payload: bytes) -> None:
    if _is_reparse(path) or _is_reparse(path.parent):
        raise MigrationError(LEDGER_INVALID, "authoritative ledger path is linked or reparsed")
    mode = stat.S_IMODE(path.stat().st_mode)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    unlocked = False
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        if not mode & stat.S_IWRITE:
            os.chmod(path, mode | stat.S_IWRITE)
            unlocked = True
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    except BaseException:
        if unlocked and path.exists():
            os.chmod(path, mode)
        raise
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _load_ledger(project: Path) -> tuple[Path, dict[str, Any], bytes]:
    path = _safe_path(project, LEDGER_REL)
    value, payload = _read_object(path, LEDGER_INVALID, "phase-state ledger")
    return path, value, payload


def _project_id(document: dict[str, Any]) -> str:
    value = document.get("manuscript_id")
    if not isinstance(value, str) or not value:
        raise MigrationError(LEDGER_INVALID, "phase-state ledger lacks a non-empty manuscript_id")
    return value


def _framework(document: dict[str, Any]) -> dict[str, Any]:
    value = document.get("milestone_framework")
    if not isinstance(value, dict):
        raise MigrationError(LEDGER_INVALID, "phase-state ledger lacks milestone_framework")
    return value


def _validate_ledger(project: Path, document: dict[str, Any], *, target: bool = False) -> str:
    code = POSTIMAGE_INVALID if target else LEDGER_INVALID
    try:
        resolution = resolve_handoff_policy(_framework(document))
    except HandoffPolicyResolutionError as exc:
        raise MigrationError(code, f"{exc.code}: {exc.message}") from exc
    try:
        validation = milestone_validator.validate_document(project, document, target=None)
    except (OSError, UnicodeError, json.JSONDecodeError, milestone_validator.SchemaViolation) as exc:
        raise MigrationError(code, f"canonical ledger validation failed: {exc}") from exc
    if not validation.exit_permitted:
        detail = "; ".join(
            f"{finding.code} at {finding.path}: {finding.message}"
            for finding in validation.findings[:8]
        )
        raise MigrationError(
            code,
            detail or f"canonical ledger validation outcome is {validation.outcome.value}",
        )
    return resolution["result"]


def _proposed(document: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
    value = copy.deepcopy(document)
    framework = _framework(value)
    framework["contract_version"] = "1.1.0"
    framework["handoff_policy"] = DERIVED_POLICY
    return value, _json_bytes(value)


def _preserved_hash(document: dict[str, Any]) -> str:
    value = copy.deepcopy(document)
    framework = _framework(value)
    framework.pop("contract_version", None)
    framework.pop("handoff_policy", None)
    return _sha_bytes(_canonical_bytes(value))


def _preserved(pre: dict[str, Any], post: dict[str, Any]) -> dict[str, str]:
    return {"pre_sha256": _preserved_hash(pre), "post_sha256": _preserved_hash(post)}


def _inventory(project: Path) -> dict[str, Any]:
    rows: list[tuple[str, int, str]] = []
    lane_prefix = LANE_REL + "/"
    for directory, directory_names, file_names in os.walk(project, topdown=True, followlinks=False):
        base = Path(directory)
        kept: list[str] = []
        for name in sorted(directory_names):
            child = base / name
            relative = child.relative_to(project).as_posix()
            if relative == LANE_REL or relative.startswith(lane_prefix):
                continue
            if _is_reparse(child):
                raise MigrationError(LEDGER_INVALID, f"external inventory refuses linked directory: {relative}")
            kept.append(name)
        directory_names[:] = kept
        for name in sorted(file_names):
            path = base / name
            relative = path.relative_to(project).as_posix()
            if relative == LEDGER_REL or relative == LANE_REL or relative.startswith(lane_prefix):
                continue
            if not path.is_file() or _is_reparse(path):
                raise MigrationError(LEDGER_INVALID, f"external inventory refuses non-plain file: {relative}")
            payload = path.read_bytes()
            rows.append((relative, len(payload), _sha_bytes(payload)))
    rows.sort()
    digest = _sha_bytes(_canonical_bytes([[path, length, digest] for path, length, digest in rows]))
    return {
        "mode": "project-tree-raw-bytes-v1",
        "excluded_paths": list(EXCLUDED_PATHS),
        "file_count": len(rows),
        "byte_count": sum(row[1] for row in rows),
        "digest": digest,
    }


def _load_authority(
    project: Path,
    supplied: Path | None,
    document: dict[str, Any],
) -> tuple[Path, dict[str, Any], bytes, dict[str, str]]:
    if supplied is None:
        raise MigrationError(AUTHORITY_REQUIRED, "--authority-receipt is required")
    path, _ = _supplied_file(project, supplied, AUTHORITY_INVALID, "authority receipt")
    value, payload = _read_object(path, AUTHORITY_INVALID, "authority receipt")
    _validate_schema("authority", value, AUTHORITY_INVALID)
    if value.get("project_id") != _project_id(document):
        raise MigrationError(AUTHORITY_INVALID, "authority project_id does not match the ledger")
    return path, value, payload, {"path": path.relative_to(project).as_posix(), "sha256": _sha_bytes(payload)}


def _assert_source_authority(authority: dict[str, Any], ledger_bytes: bytes) -> None:
    if authority.get("preimage") != _image(ledger_bytes):
        raise MigrationError(PREIMAGE_MISMATCH, "authority preimage does not match exact current ledger bytes")


def _assert_no_claims(project: Path) -> None:
    live = _safe_path(project, LIVE_CLAIM_REL)
    if live.exists() or live.is_symlink():
        raise MigrationError(ACTIVE_CLAIM, "an exclusive migration claim already exists; inspect and recover explicitly")
    for relative in (
        "reviews/.harness/milestones/claims/transaction.lock",
        "reviews/.harness/assignment/claims/transaction.lock",
    ):
        path = _safe_path(project, relative)
        if path.exists() or path.is_symlink():
            raise MigrationError(IN_USE, f"assignment or milestone transaction claim is present: {relative}")


def _transaction_id(operation: str, at: str) -> str:
    stamp = re.sub(r"[^0-9]", "", at)[:14]
    return f"mhd-{operation}-{stamp}-{uuid.uuid4().hex[:16]}"


def _claim_record(
    operation: str,
    transaction_id: str,
    project_id: str,
    ledger_sha256: str,
    authority_binding: dict[str, str],
    at: str,
    *,
    state: str = "active",
) -> dict[str, Any]:
    return {
        "schema": CLAIM_SCHEMA,
        "claim_type": "exclusive_no_ttl",
        "state": state,
        "transaction_id": transaction_id,
        "migration_id": MIGRATION_ID,
        "operation": operation,
        "host": platform.node() or "unknown-local-host",
        "pid": os.getpid(),
        "created_at": at,
        "completed_at": at if state == "consumed" else None,
        "project_id": project_id,
        "ledger_path": LEDGER_REL,
        "ledger_preimage_sha256": ledger_sha256,
        "authority_receipt": copy.deepcopy(authority_binding),
        "recovery": None,
    }


def _begin_claim(project: Path, record: dict[str, Any]) -> tuple[Path, bytes]:
    _validate_schema("claim", record, LEDGER_INVALID)
    path = _safe_path(project, LIVE_CLAIM_REL)
    _ensure_directory(path.parent, project)
    payload = _json_bytes(record)
    try:
        with path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise MigrationError(ACTIVE_CLAIM, "an exclusive migration claim appeared concurrently") from exc
    _fsync_directory(path.parent)
    return path, payload


def _release_owned_claim(path: Path, payload: bytes) -> None:
    try:
        if path.is_file() and not _is_reparse(path) and path.read_bytes() == payload:
            path.unlink()
            _fsync_directory(path.parent)
    except OSError:
        pass


def _common_receipt(
    *, operation: str, outcome: str, transaction_id: str, project_id: str,
    authority: dict[str, str] | None, claim: dict[str, str] | None,
    preimage: dict[str, Any] | None, postimage: dict[str, Any] | None,
    changes: list[dict[str, Any]], preserved: dict[str, str] | None,
    inventory: dict[str, Any] | None, rollback_manifest: dict[str, str] | None,
    started_at: str, completed_at: str, state_last: dict[str, bool] | None,
    blockers: list[str],
) -> dict[str, Any]:
    return {
        "schema": RECEIPT_SCHEMA,
        "migration_id": MIGRATION_ID,
        "transaction_id": transaction_id,
        "operation": operation,
        "outcome": outcome,
        "project_id": project_id,
        "ledger_path": LEDGER_REL,
        "authority_receipt": authority,
        "claim": claim,
        "preimage": preimage,
        "postimage": postimage,
        "permitted_changes": changes,
        "preserved_phase_state": preserved,
        "external_surface_inventory": inventory,
        "rollback_manifest": rollback_manifest,
        "started_at": started_at,
        "completed_at": completed_at,
        "state_last": state_last,
        "blockers": blockers,
    }


def dry_run_migration(project: Path, authority_receipt: Path | None, *, at: str | None = None) -> dict[str, Any]:
    project = _project(project)
    at = _timestamp(at)
    _assert_no_claims(project)
    _, document, ledger_bytes = _load_ledger(project)
    _, authority, _, authority_binding = _load_authority(project, authority_receipt, document)
    result = _validate_ledger(project, document)
    inventory = _inventory(project)
    if result == IMPLICIT_AUDITED_COMPATIBILITY:
        _assert_source_authority(authority, ledger_bytes)
        proposed, post_bytes = _proposed(document)
        _validate_ledger(project, proposed, target=True)
        preserved = _preserved(document, proposed)
        if preserved["pre_sha256"] != preserved["post_sha256"]:
            raise MigrationError(POSTIMAGE_INVALID, "prospective migration changes more than the two permitted paths")
        receipt = _common_receipt(
            operation="dry_run", outcome="WOULD_APPLY", transaction_id=_transaction_id("dry-run", at),
            project_id=_project_id(document), authority=authority_binding, claim=None,
            preimage=_image(ledger_bytes), postimage=_image(post_bytes), changes=copy.deepcopy(PERMITTED_CHANGES),
            preserved=preserved, inventory={"pre": inventory, "post": copy.deepcopy(inventory)},
            rollback_manifest=None, started_at=at, completed_at=at, state_last=None, blockers=[],
        )
    elif result == "EXPLICIT_DERIVED":
        evidence = _find_committed_apply(project, authority_binding, ledger_bytes)
        preserved_hash = _preserved_hash(document)
        receipt = _common_receipt(
            operation="dry_run", outcome="ALREADY_DERIVED", transaction_id=evidence["receipt"]["transaction_id"],
            project_id=_project_id(document), authority=authority_binding, claim=None,
            preimage=_image(ledger_bytes), postimage=_image(ledger_bytes), changes=[],
            preserved={"pre_sha256": preserved_hash, "post_sha256": preserved_hash},
            inventory={"pre": inventory, "post": copy.deepcopy(inventory)}, rollback_manifest=None,
            started_at=at, completed_at=at, state_last=None, blockers=[],
        )
    else:
        raise MigrationError(LEDGER_INVALID, "migration source must be implicit audited 1.0.0 or receipted derived 1.1.0")
    _validate_schema("receipt", receipt, POSTIMAGE_INVALID)
    return receipt


def _prepared_paths(project: Path, transaction_id: str) -> dict[str, Path]:
    root = _safe_path(project, f"{LANE_REL}/transactions/{transaction_id}")
    return {
        "root": root,
        "prepared": root / ".prepared",
        "apply": root / "apply.json",
        "manifest": root / "rollback_manifest.json",
        "claim": root / "claim.consumed.json",
        "prepared_apply": root / ".prepared" / "apply.json",
        "prepared_manifest": root / ".prepared" / "rollback_manifest.json",
        "prepared_claim": root / ".prepared" / "claim.consumed.json",
    }


def apply_migration(
    project: Path,
    authority_receipt: Path,
    *,
    at: str | None = None,
    _before_state_publish: Callable[[], None] | None = None,
    _after_state_publish: Callable[[], None] | None = None,
) -> dict[str, Any]:
    project = _project(project)
    at = _timestamp(at)
    _assert_no_claims(project)
    ledger_path, document, ledger_bytes = _load_ledger(project)
    authority_path, authority, authority_bytes, authority_binding = _load_authority(project, authority_receipt, document)
    result = _validate_ledger(project, document)
    if result == "EXPLICIT_DERIVED":
        evidence = _find_committed_apply(project, authority_binding, ledger_bytes)
        repeated = copy.deepcopy(evidence["receipt"])
        repeated["outcome"] = "ALREADY_APPLIED"
        _validate_schema("receipt", repeated, RECEIPT_TAMPERED)
        return repeated
    if result != IMPLICIT_AUDITED_COMPATIBILITY:
        raise MigrationError(LEDGER_INVALID, "apply requires a valid implicit-audited 1.0.0 ledger")
    _assert_source_authority(authority, ledger_bytes)
    proposed, post_bytes = _proposed(document)
    _validate_ledger(project, proposed, target=True)
    preserved = _preserved(document, proposed)
    if preserved["pre_sha256"] != preserved["post_sha256"]:
        raise MigrationError(POSTIMAGE_INVALID, "prospective migration changes more than the two permitted paths")
    external_pre = _inventory(project)
    transaction_id = _transaction_id("apply", at)
    paths = _prepared_paths(project, transaction_id)
    active = _claim_record("apply", transaction_id, _project_id(document), _sha_bytes(ledger_bytes), authority_binding, at)
    if _after_state_publish is not None:
        # The private interruption seam models a process that dies immediately
        # after state publication.  Its synthetic owner must therefore be
        # provably absent when the separate recovery process inspects the claim.
        active["pid"] = 2147483647
    live_path, live_bytes = _begin_claim(project, active)
    state_published = False
    try:
        consumed = copy.deepcopy(active)
        consumed["state"] = "consumed"
        consumed["completed_at"] = at
        consumed_bytes = _json_bytes(consumed)
        _validate_schema("claim", consumed, POSTIMAGE_INVALID)
        claim_binding = {"path": paths["claim"].relative_to(project).as_posix(), "sha256": _sha_bytes(consumed_bytes)}
        apply_relative = paths["apply"].relative_to(project).as_posix()
        manifest = {
            "schema": ROLLBACK_MANIFEST_SCHEMA,
            "migration_id": MIGRATION_ID,
            "transaction_id": transaction_id,
            "project_id": _project_id(document),
            "ledger_path": LEDGER_REL,
            "authority_receipt": copy.deepcopy(authority_binding),
            "apply_receipt": {"path": apply_relative},
            "preimage_bytes_base64": base64.b64encode(ledger_bytes).decode("ascii"),
            "preimage": _image(ledger_bytes),
            "applied_postimage": _image(post_bytes),
            "preserved_phase_state": preserved,
            "external_surface_inventory": {"pre": external_pre, "post": copy.deepcopy(external_pre)},
            "created_at": at,
        }
        _validate_schema("rollback_manifest", manifest, POSTIMAGE_INVALID)
        manifest_bytes = _json_bytes(manifest)
        manifest_binding = {"path": paths["manifest"].relative_to(project).as_posix(), "sha256": _sha_bytes(manifest_bytes)}
        receipt = _common_receipt(
            operation="apply", outcome="APPLIED", transaction_id=transaction_id,
            project_id=_project_id(document), authority=authority_binding, claim=claim_binding,
            preimage=_image(ledger_bytes), postimage=_image(post_bytes), changes=copy.deepcopy(PERMITTED_CHANGES),
            preserved=preserved, inventory={"pre": external_pre, "post": copy.deepcopy(external_pre)},
            rollback_manifest=manifest_binding, started_at=at, completed_at=at,
            state_last=copy.deepcopy(STATE_LAST), blockers=[],
        )
        _validate_schema("receipt", receipt, POSTIMAGE_INVALID)
        receipt_bytes = _json_bytes(receipt)
        for path, payload in (
            (paths["prepared_claim"], consumed_bytes),
            (paths["prepared_manifest"], manifest_bytes),
            (paths["prepared_apply"], receipt_bytes),
        ):
            _publish_exact(path, payload, project)

        if ledger_path.read_bytes() != ledger_bytes:
            raise MigrationError(CONCURRENT_CHANGE, "ledger changed before state publication")
        if authority_path.read_bytes() != authority_bytes:
            raise MigrationError(CONCURRENT_CHANGE, "authority receipt changed during migration")
        if _inventory(project) != external_pre:
            raise MigrationError(CONCURRENT_CHANGE, "external project surface changed during migration")
        _assert_no_other_transaction_claims(project)
        if _before_state_publish is not None:
            _before_state_publish()
        if ledger_path.read_bytes() != ledger_bytes:
            raise MigrationError(CONCURRENT_CHANGE, "ledger changed at the state-last boundary")
        if authority_path.read_bytes() != authority_bytes or _inventory(project) != external_pre:
            raise MigrationError(CONCURRENT_CHANGE, "a migration dependency changed at the state-last boundary")
        _replace_state(ledger_path, post_bytes)
        state_published = True
        if ledger_path.read_bytes() != post_bytes:
            raise MigrationError(POSTIMAGE_INVALID, "state-last replacement did not reproduce the prepared postimage")
        external_post = _inventory(project)
        if external_post != external_pre:
            raise MigrationError(CONCURRENT_CHANGE, "external project surface changed across state publication")
        if _after_state_publish is not None:
            _after_state_publish()
        for final, prepared in (
            (paths["manifest"], paths["prepared_manifest"]),
            (paths["claim"], paths["prepared_claim"]),
            (paths["apply"], paths["prepared_apply"]),
        ):
            _publish_exact(final, prepared.read_bytes(), project)
        _release_owned_claim(live_path, live_bytes)
        return receipt
    except Exception:
        if not state_published:
            _release_owned_claim(live_path, live_bytes)
        raise


def _assert_no_other_transaction_claims(project: Path) -> None:
    for relative in (
        "reviews/.harness/milestones/claims/transaction.lock",
        "reviews/.harness/assignment/claims/transaction.lock",
    ):
        path = _safe_path(project, relative)
        if path.exists() or path.is_symlink():
            raise MigrationError(IN_USE, f"assignment or milestone transaction claim appeared: {relative}")


def _evidence_path(
    project: Path,
    binding: Any,
    label: str,
    *,
    code: str = RECEIPT_TAMPERED,
) -> tuple[Path, dict[str, Any], bytes]:
    if not isinstance(binding, dict) or set(binding) != {"path", "sha256"}:
        raise MigrationError(code, f"{label} binding is malformed")
    path = _safe_path(project, binding.get("path"))
    value, payload = _read_object(path, code, label)
    if binding.get("sha256") != _sha_bytes(payload):
        raise MigrationError(code, f"{label} binding hash differs from current bytes")
    return path, value, payload


def _validate_apply_evidence_graph(
    project: Path,
    *,
    apply_path: Path,
    receipt: dict[str, Any],
    receipt_bytes: bytes,
    claim_path: Path,
    claim: dict[str, Any],
    claim_bytes: bytes,
    manifest_path: Path,
    manifest: dict[str, Any],
    manifest_bytes: bytes,
    authority_binding: dict[str, str],
    code: str,
    active_claim: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _validate_schema("receipt", receipt, code)
    _validate_schema("claim", claim, code)
    _validate_schema("rollback_manifest", manifest, code)
    if receipt.get("operation") != "apply" or receipt.get("outcome") != "APPLIED":
        raise MigrationError(code, "apply evidence must record the exact APPLIED transaction")
    transaction_id = receipt.get("transaction_id")
    if not isinstance(transaction_id, str):
        raise MigrationError(code, "apply receipt transaction_id is invalid")
    expected_apply = _safe_path(project, f"{LANE_REL}/transactions/{transaction_id}/apply.json")
    expected_claim = _safe_path(project, f"{LANE_REL}/transactions/{transaction_id}/claim.consumed.json")
    expected_manifest = _safe_path(project, f"{LANE_REL}/transactions/{transaction_id}/rollback_manifest.json")
    if apply_path != expected_apply or claim_path != expected_claim or manifest_path != expected_manifest:
        raise MigrationError(code, "apply evidence is outside its canonical transaction paths")
    claim_binding = {
        "path": claim_path.relative_to(project).as_posix(),
        "sha256": _sha_bytes(claim_bytes),
    }
    manifest_binding = {
        "path": manifest_path.relative_to(project).as_posix(),
        "sha256": _sha_bytes(manifest_bytes),
    }
    if receipt.get("claim") != claim_binding or receipt.get("rollback_manifest") != manifest_binding:
        raise MigrationError(code, "apply receipt bindings do not reproduce exact claim/manifest bytes")
    if receipt.get("authority_receipt") != authority_binding:
        raise MigrationError(code, "apply receipt authority binding differs")
    _, authority, _ = _evidence_path(
        project, authority_binding, "migration authority receipt", code=code,
    )
    _validate_schema("authority", authority, code)
    project_id = receipt.get("project_id")
    if authority.get("project_id") != project_id:
        raise MigrationError(code, "apply receipt project identity differs from immutable authority")
    if (
        claim.get("state") != "consumed"
        or claim.get("operation") != "apply"
        or claim.get("transaction_id") != transaction_id
        or claim.get("project_id") != project_id
        or claim.get("authority_receipt") != authority_binding
        or claim.get("ledger_preimage_sha256") != receipt.get("preimage", {}).get("sha256")
        or claim.get("created_at") != receipt.get("started_at")
        or claim.get("completed_at") != receipt.get("completed_at")
        or claim.get("recovery") is not None
    ):
        raise MigrationError(code, "consumed claim does not reproduce apply identity, authority, time, and state")
    if active_claim is not None:
        expected_consumed = copy.deepcopy(active_claim)
        expected_consumed["state"] = "consumed"
        expected_consumed["completed_at"] = receipt.get("completed_at")
        if claim != expected_consumed:
            raise MigrationError(code, "prepared consumed claim is not the exact disposition of the live claim")
    if (
        manifest.get("transaction_id") != transaction_id
        or manifest.get("project_id") != project_id
        or manifest.get("authority_receipt") != authority_binding
        or manifest.get("apply_receipt") != {"path": apply_path.relative_to(project).as_posix()}
        or manifest.get("created_at") != receipt.get("completed_at")
    ):
        raise MigrationError(code, "rollback manifest does not reproduce apply identity, authority, and time")
    try:
        pre_bytes = base64.b64decode(manifest.get("preimage_bytes_base64", ""), validate=True)
        pre_document = json.loads(pre_bytes.decode("utf-8"))
    except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
        raise MigrationError(code, f"rollback preimage is invalid: {exc}") from exc
    if not isinstance(pre_document, dict) or manifest.get("preimage") != _image(pre_bytes):
        raise MigrationError(code, "rollback manifest preimage bytes do not reproduce its image")
    if authority.get("preimage") != _image(pre_bytes):
        raise MigrationError(code, "immutable authority does not bind the rollback preimage bytes")
    post_document, post_bytes = _proposed(pre_document)
    try:
        source_policy = _validate_ledger(project, pre_document)
        target_policy = _validate_ledger(project, post_document, target=True)
    except MigrationError as exc:
        raise MigrationError(code, f"apply evidence ledger replay failed: {exc.code}: {exc.message}") from exc
    if source_policy != IMPLICIT_AUDITED_COMPATIBILITY or target_policy != "EXPLICIT_DERIVED":
        raise MigrationError(code, "apply evidence does not reproduce audited-to-derived policy resolution")
    if manifest.get("applied_postimage") != _image(post_bytes):
        raise MigrationError(code, "rollback manifest postimage is not derived from its exact preimage")
    preserved = _preserved(pre_document, post_document)
    inventory = manifest.get("external_surface_inventory")
    if (
        preserved["pre_sha256"] != preserved["post_sha256"]
        or manifest.get("preserved_phase_state") != preserved
        or not isinstance(inventory, dict)
        or inventory.get("pre") != inventory.get("post")
        or receipt.get("preimage") != _image(pre_bytes)
        or receipt.get("postimage") != _image(post_bytes)
        or receipt.get("permitted_changes") != PERMITTED_CHANGES
        or receipt.get("preserved_phase_state") != preserved
        or receipt.get("external_surface_inventory") != inventory
        or receipt.get("state_last") != STATE_LAST
        or receipt.get("blockers") != []
    ):
        raise MigrationError(code, "apply receipt proof fields do not reproduce exact migration evidence")
    return {
        "receipt": receipt,
        "receipt_bytes": receipt_bytes,
        "receipt_path": apply_path,
        "claim": claim,
        "claim_bytes": claim_bytes,
        "claim_path": claim_path,
        "manifest": manifest,
        "manifest_bytes": manifest_bytes,
        "manifest_path": manifest_path,
        "pre_bytes": pre_bytes,
        "pre_document": pre_document,
        "post_bytes": post_bytes,
        "post_document": post_document,
    }


def _load_apply_evidence(
    project: Path,
    apply_path: Path,
    authority_binding: dict[str, str],
    *,
    code: str = RECEIPT_TAMPERED,
) -> dict[str, Any]:
    receipt, receipt_bytes = _read_object(apply_path, code, "apply receipt")
    claim_path, claim, claim_bytes = _evidence_path(
        project, receipt.get("claim"), "consumed claim", code=code,
    )
    manifest_path, manifest, manifest_bytes = _evidence_path(
        project, receipt.get("rollback_manifest"), "rollback manifest", code=code,
    )
    return _validate_apply_evidence_graph(
        project,
        apply_path=apply_path,
        receipt=receipt,
        receipt_bytes=receipt_bytes,
        claim_path=claim_path,
        claim=claim,
        claim_bytes=claim_bytes,
        manifest_path=manifest_path,
        manifest=manifest,
        manifest_bytes=manifest_bytes,
        authority_binding=authority_binding,
        code=code,
    )


def _find_committed_apply(project: Path, authority_binding: dict[str, str], ledger_bytes: bytes) -> dict[str, Any]:
    transactions = _safe_path(project, f"{LANE_REL}/transactions")
    if not transactions.is_dir() or _is_reparse(transactions):
        raise MigrationError(RECEIPT_TAMPERED, "derived ledger lacks a committed migration transaction")
    candidates = sorted(transactions.glob("*/apply.json"))
    valid: list[dict[str, Any]] = []
    failures: list[str] = []
    for path in candidates:
        try:
            evidence = _load_apply_evidence(project, path, authority_binding)
        except MigrationError as exc:
            failures.append(exc.message)
            continue
        if evidence["post_bytes"] == ledger_bytes:
            valid.append(evidence)
    if len(valid) != 1:
        detail = failures[0] if failures else "no exact apply receipt binds the current derived ledger"
        raise MigrationError(RECEIPT_TAMPERED, detail)
    return valid[0]


def verify_migration(
    project: Path,
    authority_receipt: Path,
    apply_receipt: Path,
    *,
    at: str | None = None,
) -> dict[str, Any]:
    project = _project(project)
    at = _timestamp(at)
    _assert_no_claims(project)
    _, document, current_bytes = _load_ledger(project)
    _, _, _, authority_binding = _load_authority(project, authority_receipt, document)
    apply_path, _ = _supplied_file(project, apply_receipt, RECEIPT_TAMPERED, "apply receipt")
    evidence = _load_apply_evidence(project, apply_path, authority_binding)
    current_inventory = _inventory(project)
    expected_inventory = evidence["receipt"]["external_surface_inventory"]["post"]
    verified = current_bytes == evidence["post_bytes"] and current_inventory == expected_inventory
    if verified:
        _validate_ledger(project, document, target=True)
        receipt = _common_receipt(
            operation="verify", outcome="VERIFIED", transaction_id=evidence["receipt"]["transaction_id"],
            project_id=_project_id(document), authority=authority_binding, claim=None,
            preimage=evidence["receipt"]["preimage"], postimage=evidence["receipt"]["postimage"],
            changes=copy.deepcopy(PERMITTED_CHANGES), preserved=evidence["receipt"]["preserved_phase_state"],
            inventory={"pre": evidence["receipt"]["external_surface_inventory"]["pre"], "post": current_inventory},
            rollback_manifest=evidence["receipt"]["rollback_manifest"], started_at=at, completed_at=at,
            state_last=None, blockers=[],
        )
    else:
        try:
            current_document = json.loads(current_bytes.decode("utf-8"))
            current_preserved = _preserved_hash(current_document) if isinstance(current_document, dict) else "0" * 64
        except (UnicodeError, json.JSONDecodeError, MigrationError):
            current_preserved = "0" * 64
        receipt = _common_receipt(
            operation="verify", outcome="NOT_APPLIED", transaction_id=evidence["receipt"]["transaction_id"],
            project_id=evidence["receipt"]["project_id"], authority=authority_binding, claim=None,
            preimage=_image(current_bytes), postimage=evidence["receipt"]["postimage"],
            changes=copy.deepcopy(PERMITTED_CHANGES),
            preserved={"pre_sha256": current_preserved, "post_sha256": evidence["receipt"]["preserved_phase_state"]["post_sha256"]},
            inventory={"pre": current_inventory, "post": expected_inventory},
            rollback_manifest=evidence["receipt"]["rollback_manifest"], started_at=at, completed_at=at,
            state_last=None, blockers=[VERIFY_FAILED],
        )
    _validate_schema("receipt", receipt, RECEIPT_TAMPERED)
    return receipt


def _rollback_receipt(
    *, outcome: str, evidence: dict[str, Any], authority: dict[str, str],
    claim: dict[str, str] | None, rollback_transaction_id: str,
    inventory: dict[str, Any], at: str, state_last: dict[str, bool] | None,
    blockers: list[str],
) -> dict[str, Any]:
    return {
        "schema": ROLLBACK_RECEIPT_SCHEMA,
        "migration_id": MIGRATION_ID,
        "transaction_id": evidence["receipt"]["transaction_id"],
        "rollback_transaction_id": rollback_transaction_id,
        "operation": "rollback",
        "outcome": outcome,
        "project_id": evidence["receipt"]["project_id"],
        "ledger_path": LEDGER_REL,
        "authority_receipt": authority,
        "apply_receipt": {"path": evidence["receipt_path"].relative_to(evidence["project"]).as_posix(), "sha256": _sha_bytes(evidence["receipt_bytes"])},
        "rollback_manifest": {"path": evidence["manifest_path"].relative_to(evidence["project"]).as_posix(), "sha256": _sha_bytes(evidence["manifest_bytes"])},
        "claim": claim,
        "current_applied_postimage": evidence["receipt"]["postimage"],
        "restored_preimage": evidence["receipt"]["preimage"],
        "external_surface_inventory": inventory,
        "started_at": at,
        "completed_at": at,
        "state_last": state_last,
        "blockers": blockers,
    }


def _validate_rollback_evidence_graph(
    project: Path,
    *,
    evidence: dict[str, Any],
    receipt_path: Path,
    receipt: dict[str, Any],
    receipt_bytes: bytes,
    claim_path: Path,
    claim: dict[str, Any],
    claim_bytes: bytes,
    authority: dict[str, str],
    current_bytes: bytes,
    code: str,
    state_code: str,
    active_claim: dict[str, Any] | None = None,
) -> dict[str, Any]:
    expected_path = _safe_path(
        project,
        f"{LANE_REL}/transactions/{evidence['receipt']['transaction_id']}/rollback.json",
    )
    if receipt_path != expected_path:
        raise MigrationError(code, "rollback receipt is outside the canonical apply transaction path")
    _validate_schema("rollback_receipt", receipt, code)
    transaction_id = evidence["receipt"]["transaction_id"]
    rollback_transaction_id = receipt.get("rollback_transaction_id")
    apply_binding = {
        "path": evidence["receipt_path"].relative_to(project).as_posix(),
        "sha256": _sha_bytes(evidence["receipt_bytes"]),
    }
    manifest_binding = {
        "path": evidence["manifest_path"].relative_to(project).as_posix(),
        "sha256": _sha_bytes(evidence["manifest_bytes"]),
    }
    if (
        receipt.get("operation") != "rollback"
        or receipt.get("outcome") != "ROLLED_BACK"
        or receipt.get("transaction_id") != transaction_id
        or not isinstance(rollback_transaction_id, str)
        or rollback_transaction_id == transaction_id
        or receipt.get("project_id") != evidence["receipt"]["project_id"]
        or receipt.get("ledger_path") != LEDGER_REL
        or receipt.get("authority_receipt") != authority
        or receipt.get("apply_receipt") != apply_binding
        or receipt.get("rollback_manifest") != manifest_binding
        or receipt.get("current_applied_postimage") != _image(evidence["post_bytes"])
        or receipt.get("restored_preimage") != _image(evidence["pre_bytes"])
        or receipt.get("state_last") != STATE_LAST
        or receipt.get("blockers") != []
    ):
        raise MigrationError(code, "rollback receipt does not reproduce the complete apply/rollback transaction graph")
    if current_bytes != evidence["pre_bytes"]:
        raise MigrationError(state_code, "current ledger does not reproduce completed rollback")
    expected_inventory = evidence["receipt"]["external_surface_inventory"]["post"]
    receipt_inventory = receipt.get("external_surface_inventory")
    if receipt_inventory != {"pre": expected_inventory, "post": expected_inventory}:
        raise MigrationError(code, "rollback receipt inventory does not reproduce apply evidence")
    if _inventory(project) != expected_inventory:
        raise MigrationError(state_code, "external project bytes differ from completed rollback proof")
    _validate_schema("claim", claim, code)
    expected_claim_path = _safe_path(
        project, f"{LANE_REL}/transactions/{rollback_transaction_id}/claim.consumed.json",
    )
    exact_claim_binding = {
        "path": expected_claim_path.relative_to(project).as_posix(),
        "sha256": _sha_bytes(claim_bytes),
    }
    if (
        claim_path != expected_claim_path
        or receipt.get("claim") != exact_claim_binding
        or claim.get("state") != "consumed"
        or claim.get("operation") != "rollback"
        or claim.get("transaction_id") != rollback_transaction_id
        or claim.get("project_id") != receipt.get("project_id")
        or claim.get("ledger_preimage_sha256") != evidence["receipt"]["postimage"]["sha256"]
        or claim.get("authority_receipt") != authority
        or claim.get("created_at") != receipt.get("started_at")
        or claim.get("completed_at") != receipt.get("completed_at")
        or claim.get("recovery") is not None
    ):
        raise MigrationError(code, "rollback claim does not reproduce transaction identity, authority, time, and state")
    if active_claim is not None:
        expected_consumed = copy.deepcopy(active_claim)
        expected_consumed["state"] = "consumed"
        expected_consumed["completed_at"] = receipt.get("completed_at")
        if claim != expected_consumed:
            raise MigrationError(code, "prepared rollback claim is not the exact disposition of the live claim")
    return receipt


def _load_rollback_receipt(project: Path, evidence: dict[str, Any], authority: dict[str, str], current_bytes: bytes) -> dict[str, Any]:
    path = evidence["receipt_path"].parent / "rollback.json"
    receipt, receipt_bytes = _read_object(path, RECEIPT_TAMPERED, "rollback receipt")
    claim_path, claim, claim_bytes = _evidence_path(
        project, receipt.get("claim"), "rollback consumed claim",
    )
    return _validate_rollback_evidence_graph(
        project,
        evidence=evidence,
        receipt_path=path,
        receipt=receipt,
        receipt_bytes=receipt_bytes,
        claim_path=claim_path,
        claim=claim,
        claim_bytes=claim_bytes,
        authority=authority,
        current_bytes=current_bytes,
        code=RECEIPT_TAMPERED,
        state_code=ROLLBACK_STATE_MISMATCH,
    )


def rollback_migration(
    project: Path,
    authority_receipt: Path,
    apply_receipt: Path,
    rollback_manifest: Path,
    *,
    at: str | None = None,
    _after_state_publish: Callable[[], None] | None = None,
) -> dict[str, Any]:
    project = _project(project)
    at = _timestamp(at)
    _assert_no_claims(project)
    ledger_path, document, current_bytes = _load_ledger(project)
    _, _, authority_bytes, authority_binding = _load_authority(project, authority_receipt, document)
    authority_path, _ = _supplied_file(project, authority_receipt, AUTHORITY_INVALID, "authority receipt")
    apply_path, _ = _supplied_file(project, apply_receipt, RECEIPT_TAMPERED, "apply receipt")
    evidence = _load_apply_evidence(project, apply_path, authority_binding)
    evidence["project"] = project
    supplied_manifest, _ = _supplied_file(project, rollback_manifest, RECEIPT_TAMPERED, "rollback manifest")
    if supplied_manifest != evidence["manifest_path"]:
        raise MigrationError(RECEIPT_TAMPERED, "supplied rollback manifest differs from apply receipt binding")
    if current_bytes == evidence["pre_bytes"]:
        existing = _load_rollback_receipt(project, evidence, authority_binding, current_bytes)
        repeated = copy.deepcopy(existing)
        repeated["outcome"] = "ALREADY_ROLLED_BACK"
        repeated["state_last"] = None
        _validate_schema("rollback_receipt", repeated, RECEIPT_TAMPERED)
        return repeated
    if current_bytes != evidence["post_bytes"]:
        raise MigrationError(ROLLBACK_STATE_MISMATCH, "current ledger is neither exact applied postimage nor receipted restored preimage")
    external_pre = _inventory(project)
    if external_pre != evidence["receipt"]["external_surface_inventory"]["post"]:
        raise MigrationError(ROLLBACK_STATE_MISMATCH, "external project bytes changed after apply")
    rollback_transaction_id = _transaction_id("rollback", at)
    rollback_root = _safe_path(project, f"{LANE_REL}/transactions/{rollback_transaction_id}")
    prepared = rollback_root / ".prepared"
    consumed_path = rollback_root / "claim.consumed.json"
    rollback_path = evidence["receipt_path"].parent / "rollback.json"
    active = _claim_record("rollback", rollback_transaction_id, evidence["receipt"]["project_id"], _sha_bytes(current_bytes), authority_binding, at)
    if _after_state_publish is not None:
        # The private interruption seam models process death immediately after
        # exact rollback restoration, so recovery must observe a dead owner.
        active["pid"] = 2147483647
    live_path, live_bytes = _begin_claim(project, active)
    state_published = False
    try:
        consumed = copy.deepcopy(active)
        consumed["state"] = "consumed"
        consumed["completed_at"] = at
        consumed_bytes = _json_bytes(consumed)
        _validate_schema("claim", consumed, ROLLBACK_RESTORE_FAILED)
        claim_binding = {"path": consumed_path.relative_to(project).as_posix(), "sha256": _sha_bytes(consumed_bytes)}
        inventory = {"pre": external_pre, "post": copy.deepcopy(external_pre)}
        receipt = _rollback_receipt(
            outcome="ROLLED_BACK", evidence=evidence, authority=authority_binding,
            claim=claim_binding, rollback_transaction_id=rollback_transaction_id,
            inventory=inventory, at=at, state_last=copy.deepcopy(STATE_LAST), blockers=[],
        )
        _validate_schema("rollback_receipt", receipt, ROLLBACK_RESTORE_FAILED)
        receipt_bytes = _json_bytes(receipt)
        _publish_exact(prepared / "claim.consumed.json", consumed_bytes, project)
        _publish_exact(prepared / "rollback.json", receipt_bytes, project)
        if ledger_path.read_bytes() != current_bytes or authority_path.read_bytes() != authority_bytes:
            raise MigrationError(CONCURRENT_CHANGE, "rollback dependency changed before state restoration")
        if _inventory(project) != external_pre:
            raise MigrationError(CONCURRENT_CHANGE, "external project surface changed before rollback")
        _assert_no_other_transaction_claims(project)
        _replace_state(ledger_path, evidence["pre_bytes"])
        state_published = True
        if ledger_path.read_bytes() != evidence["pre_bytes"]:
            raise MigrationError(ROLLBACK_RESTORE_FAILED, "rollback did not reproduce exact preimage bytes")
        if _inventory(project) != external_pre:
            raise MigrationError(ROLLBACK_RESTORE_FAILED, "external project surface changed across rollback")
        if _after_state_publish is not None:
            _after_state_publish()
        _publish_exact(consumed_path, (prepared / "claim.consumed.json").read_bytes(), project)
        _publish_exact(rollback_path, (prepared / "rollback.json").read_bytes(), project)
        _release_owned_claim(live_path, live_bytes)
        return receipt
    except Exception:
        if not state_published:
            _release_owned_claim(live_path, live_bytes)
        raise


def _pid_state(pid: Any) -> str:
    if not isinstance(pid, int) or isinstance(pid, bool) or pid < 1:
        return "unknown"
    if pid in {os.getpid(), os.getppid()}:
        return "live"
    if os.name == "nt":
        import ctypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = kernel32.OpenProcess(0x1000, False, pid)
        if handle:
            try:
                code = ctypes.c_ulong()
                if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                    return "unknown"
                return "live" if code.value == 259 else "dead"
            finally:
                kernel32.CloseHandle(handle)
        return "dead" if ctypes.get_last_error() == 87 else "unknown"
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return "dead"
    except PermissionError:
        return "live"
    except OSError:
        return "unknown"
    return "live"


def recover_migration_claim(
    project: Path,
    authority_receipt: Path,
    acknowledgement: str,
    *,
    at: str | None = None,
) -> dict[str, Any]:
    project = _project(project)
    at = _timestamp(at)
    if acknowledgement != "inspected-migration-state-and-receipts":
        raise MigrationError(RECOVERY_ACK, "exact recovery acknowledgement is required")
    ledger_path, document, ledger_bytes = _load_ledger(project)
    authority_path, _, authority_bytes, authority_binding = _load_authority(
        project, authority_receipt, document,
    )
    live_path = _safe_path(project, LIVE_CLAIM_REL)
    claim, live_bytes = _read_object(live_path, ACTIVE_CLAIM, "live migration claim")
    _validate_schema("claim", claim, ACTIVE_CLAIM)
    if claim.get("state") != "active" or claim.get("authority_receipt") != authority_binding:
        raise MigrationError(AUTHORITY_INVALID, "live claim does not bind supplied immutable authority")
    if claim.get("host") != (platform.node() or "unknown-local-host"):
        raise MigrationError(RECOVERY_FOREIGN, "foreign-host claim recovery fails closed")
    liveness = _pid_state(claim.get("pid"))
    if liveness == "live":
        raise MigrationError(RECOVERY_LIVE, "claim owner process is still live")
    if liveness != "dead":
        raise MigrationError(RECOVERY_LIVENESS, "claim owner cannot be proven dead")
    transaction_id = claim["transaction_id"]
    paths = _prepared_paths(project, transaction_id)
    observed = _sha_bytes(ledger_bytes)
    disposition: str
    if observed == claim.get("ledger_preimage_sha256"):
        disposition = "preimage_unchanged"
    elif claim.get("operation") == "apply" and paths["prepared_apply"].is_file():
        receipt, receipt_bytes = _read_object(paths["prepared_apply"], RECOVERY_STATE_MISMATCH, "prepared apply receipt")
        prepared_manifest, manifest_bytes = _read_object(
            paths["prepared_manifest"], RECOVERY_STATE_MISMATCH, "prepared rollback manifest",
        )
        prepared_claim, claim_bytes = _read_object(
            paths["prepared_claim"], RECOVERY_STATE_MISMATCH, "prepared consumed claim",
        )
        evidence = _validate_apply_evidence_graph(
            project,
            apply_path=paths["apply"],
            receipt=receipt,
            receipt_bytes=receipt_bytes,
            claim_path=paths["claim"],
            claim=prepared_claim,
            claim_bytes=claim_bytes,
            manifest_path=paths["manifest"],
            manifest=prepared_manifest,
            manifest_bytes=manifest_bytes,
            authority_binding=authority_binding,
            code=RECOVERY_STATE_MISMATCH,
            active_claim=claim,
        )
        if evidence["post_bytes"] != ledger_bytes or receipt.get("postimage") != _image(ledger_bytes):
            raise MigrationError(RECOVERY_STATE_MISMATCH, "ledger does not match prepared apply postimage")
        if _inventory(project) != receipt["external_surface_inventory"]["post"]:
            raise MigrationError(RECOVERY_STATE_MISMATCH, "external project bytes differ from prepared apply proof")
        publications = (
            (paths["manifest"], manifest_bytes),
            (paths["claim"], claim_bytes),
            (paths["apply"], receipt_bytes),
        )
        for final, payload in publications:
            _assert_publishable_exact(final, payload, project, code=RECOVERY_STATE_MISMATCH)
        _plain_file(live_path, CONCURRENT_CHANGE, "live migration claim")
        _plain_file(ledger_path, CONCURRENT_CHANGE, "authoritative ledger")
        _plain_file(authority_path, CONCURRENT_CHANGE, "migration authority receipt")
        if (
            live_path.read_bytes() != live_bytes
            or ledger_path.read_bytes() != ledger_bytes
            or authority_path.read_bytes() != authority_bytes
            or _inventory(project) != receipt["external_surface_inventory"]["post"]
        ):
            raise MigrationError(CONCURRENT_CHANGE, "recovery dependency changed before evidence publication")
        for final, payload in publications:
            _publish_exact(final, payload, project, code=RECOVERY_STATE_MISMATCH)
        disposition = "postimage_committed"
    elif claim.get("operation") == "rollback":
        rollback_root = _safe_path(project, f"{LANE_REL}/transactions/{transaction_id}")
        prepared_receipt = rollback_root / ".prepared" / "rollback.json"
        prepared_claim = rollback_root / ".prepared" / "claim.consumed.json"
        receipt, receipt_bytes = _read_object(prepared_receipt, RECOVERY_STATE_MISMATCH, "prepared rollback receipt")
        _validate_schema("rollback_receipt", receipt, RECOVERY_STATE_MISMATCH)
        apply_path, _, _ = _evidence_path(
            project, receipt.get("apply_receipt"), "rollback-bound apply receipt",
            code=RECOVERY_STATE_MISMATCH,
        )
        evidence = _load_apply_evidence(
            project, apply_path, authority_binding, code=RECOVERY_STATE_MISMATCH,
        )
        evidence["project"] = project
        rollback_path = evidence["receipt_path"].parent / "rollback.json"
        prepared_claim_value, prepared_claim_bytes = _read_object(
            prepared_claim, RECOVERY_STATE_MISMATCH, "prepared rollback consumed claim",
        )
        claim_binding = receipt.get("claim")
        if not isinstance(claim_binding, dict) or set(claim_binding) != {"path", "sha256"}:
            raise MigrationError(RECOVERY_STATE_MISMATCH, "prepared rollback claim binding is malformed")
        consumed_path = _safe_path(project, claim_binding.get("path"))
        if claim_binding.get("sha256") != _sha_bytes(prepared_claim_bytes):
            raise MigrationError(RECOVERY_STATE_MISMATCH, "prepared rollback receipt does not bind exact claim bytes")
        _validate_rollback_evidence_graph(
            project,
            evidence=evidence,
            receipt_path=rollback_path,
            receipt=receipt,
            receipt_bytes=receipt_bytes,
            claim_path=consumed_path,
            claim=prepared_claim_value,
            claim_bytes=prepared_claim_bytes,
            authority=authority_binding,
            current_bytes=ledger_bytes,
            code=RECOVERY_STATE_MISMATCH,
            state_code=RECOVERY_STATE_MISMATCH,
            active_claim=claim,
        )
        expected_inventory = evidence["receipt"]["external_surface_inventory"]["post"]
        publications = (
            (consumed_path, prepared_claim_bytes),
            (rollback_path, receipt_bytes),
        )
        for final, payload in publications:
            _assert_publishable_exact(final, payload, project, code=RECOVERY_STATE_MISMATCH)
        _plain_file(live_path, CONCURRENT_CHANGE, "live migration claim")
        _plain_file(ledger_path, CONCURRENT_CHANGE, "authoritative ledger")
        _plain_file(authority_path, CONCURRENT_CHANGE, "migration authority receipt")
        if (
            live_path.read_bytes() != live_bytes
            or ledger_path.read_bytes() != ledger_bytes
            or authority_path.read_bytes() != authority_bytes
            or _inventory(project) != expected_inventory
        ):
            raise MigrationError(CONCURRENT_CHANGE, "rollback recovery dependency changed before evidence publication")
        for final, payload in publications:
            _publish_exact(final, payload, project, code=RECOVERY_STATE_MISMATCH)
        disposition = "rollback_restored"
    else:
        raise MigrationError(RECOVERY_STATE_MISMATCH, "authoritative ledger bytes match no recoverable prepared state")
    recovered = copy.deepcopy(claim)
    recovered["state"] = "recovered"
    recovered["completed_at"] = at
    recovered["recovery"] = {
        "acknowledgement": acknowledgement,
        "recovered_at": at,
        "observed_ledger_sha256": observed,
        "disposition": disposition,
    }
    _validate_schema("claim", recovered, RECOVERY_STATE_MISMATCH)
    archive = _safe_path(project, f"{LANE_REL}/transactions/{transaction_id}/claim.recovered.json")
    recovered_bytes = _json_bytes(recovered)
    _publish_exact(archive, recovered_bytes, project)
    if live_path.read_bytes() != live_bytes:
        raise MigrationError(CONCURRENT_CHANGE, "live claim changed during recovery")
    live_path.unlink()
    _fsync_directory(live_path.parent)
    return {
        "operation": "recover",
        "outcome": "RECOVERED",
        "migration_id": MIGRATION_ID,
        "transaction_id": transaction_id,
        "disposition": disposition,
        "claim": {"path": archive.relative_to(project).as_posix(), "sha256": _sha_bytes(recovered_bytes)},
        "blockers": [],
    }


def _fallback_project_id(project: Path) -> str:
    try:
        value = json.loads((project / LEDGER_REL).read_text(encoding="utf-8")).get("manuscript_id")
        return value if isinstance(value, str) and value else "unresolved-project"
    except Exception:
        return "unresolved-project"


def _refused_common(operation: str, project: Path, code: str, at: str) -> dict[str, Any]:
    return _common_receipt(
        operation=operation, outcome="REFUSED", transaction_id=_transaction_id("refused", at),
        project_id=_fallback_project_id(project), authority=None, claim=None, preimage=None, postimage=None,
        changes=[], preserved=None, inventory=None, rollback_manifest=None,
        started_at=at, completed_at=at, state_last=None, blockers=[code],
    )


def _refused_rollback(project: Path, code: str, at: str) -> dict[str, Any]:
    return {
        "schema": ROLLBACK_RECEIPT_SCHEMA,
        "migration_id": MIGRATION_ID,
        "transaction_id": _transaction_id("refused-apply", at),
        "rollback_transaction_id": _transaction_id("refused-rollback", at),
        "operation": "rollback",
        "outcome": "REFUSED",
        "project_id": _fallback_project_id(project),
        "ledger_path": LEDGER_REL,
        "authority_receipt": None,
        "apply_receipt": None,
        "rollback_manifest": None,
        "claim": None,
        "current_applied_postimage": None,
        "restored_preimage": None,
        "external_surface_inventory": None,
        "started_at": at,
        "completed_at": at,
        "state_last": None,
        "blockers": [code],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("dry-run", "apply", "verify", "rollback", "recover"))
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--authority-receipt", type=Path)
    parser.add_argument("--apply-receipt", type=Path)
    parser.add_argument("--rollback-manifest", type=Path)
    parser.add_argument("--acknowledgement")
    parser.add_argument("--at")
    args = parser.parse_args(argv)
    operation = args.operation
    try:
        if operation == "dry-run":
            receipt = dry_run_migration(args.project_root, args.authority_receipt, at=args.at)
        elif operation == "apply":
            if args.authority_receipt is None:
                raise MigrationError(AUTHORITY_REQUIRED, "--authority-receipt is required")
            receipt = apply_migration(args.project_root, args.authority_receipt, at=args.at)
        elif operation == "verify":
            if args.authority_receipt is None:
                raise MigrationError(AUTHORITY_REQUIRED, "--authority-receipt is required")
            if args.apply_receipt is None:
                raise MigrationError(RECEIPT_TAMPERED, "--apply-receipt is required")
            receipt = verify_migration(args.project_root, args.authority_receipt, args.apply_receipt, at=args.at)
        elif operation == "rollback":
            if args.authority_receipt is None:
                raise MigrationError(AUTHORITY_REQUIRED, "--authority-receipt is required")
            if args.apply_receipt is None or args.rollback_manifest is None:
                raise MigrationError(RECEIPT_TAMPERED, "rollback requires --apply-receipt and --rollback-manifest")
            receipt = rollback_migration(
                args.project_root, args.authority_receipt, args.apply_receipt,
                args.rollback_manifest, at=args.at,
            )
        else:
            if args.authority_receipt is None:
                raise MigrationError(AUTHORITY_REQUIRED, "--authority-receipt is required")
            receipt = recover_migration_claim(
                args.project_root, args.authority_receipt,
                args.acknowledgement or "", at=args.at,
            )
    except MigrationError as exc:
        try:
            at = _timestamp(args.at)
        except MigrationError:
            at = _timestamp()
        if operation == "rollback":
            receipt = _refused_rollback(args.project_root, exc.code, at)
        elif operation == "recover":
            receipt = {
                "operation": "recover", "outcome": "REFUSED",
                "authority_receipt": None, "claim": None,
                "blockers": [exc.code], "code": exc.code, "message": exc.message,
            }
        else:
            receipt = _refused_common(operation.replace("-", "_"), args.project_root, exc.code, at)
        print(json.dumps({"receipt": receipt, "diagnostic": {"code": exc.code, "message": exc.message}}, indent=2, sort_keys=True, ensure_ascii=False))
        return 4
    except Exception as exc:
        at = _timestamp()
        code = LEDGER_INVALID
        if operation == "rollback":
            receipt = _refused_rollback(args.project_root, code, at)
        elif operation == "recover":
            receipt = {"operation": "recover", "outcome": "REFUSED", "authority_receipt": None, "claim": None, "blockers": [code]}
        else:
            receipt = _refused_common(operation.replace("-", "_"), args.project_root, code, at)
        print(json.dumps({"receipt": receipt, "diagnostic": {"code": code, "message": f"{type(exc).__name__}: {exc}"}}, indent=2, sort_keys=True, ensure_ascii=False))
        return 4
    print(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False))
    if receipt.get("outcome") == "NOT_APPLIED":
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
