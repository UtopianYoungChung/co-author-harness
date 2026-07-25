#!/usr/bin/env python3
"""Crash-recoverable receipt transactions for assignment-scoped writes."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import stat
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from destination_capability import guard_project_root


STATE_NAMES = ("ready", "reserved", "consumed", "invalidated")
PLAN_FIELDS = {
    "schema_version", "receipt_id", "reservation_id", "target_milestone",
    "role", "writes",
}
WRITE_FIELDS = {"staged_path", "target_path", "sha256"}


class ReceiptTransactionError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _assignment_root(project: Path) -> Path:
    return project / "reviews" / ".harness" / "assignment"


def state_path(project: Path, basename: str, state: str) -> Path:
    if state not in STATE_NAMES:
        raise ValueError(f"unknown receipt state: {state}")
    return _assignment_root(project) / state / basename


def _safe_relative(raw: Any, code: str = "APG-RECEIPT-PATH-INVALID") -> PurePosixPath:
    if not isinstance(raw, str) or not raw or "\\" in raw or ":" in raw:
        raise ReceiptTransactionError(code, f"unsafe project-relative path: {raw!r}")
    relative = PurePosixPath(raw)
    if relative.is_absolute() or ".." in relative.parts or "." in relative.parts:
        raise ReceiptTransactionError(code, f"unsafe project-relative path: {raw!r}")
    return relative


def _is_link(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        attributes = getattr(os.lstat(path), "st_file_attributes", 0)
    except OSError:
        return False
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400)
    return bool(attributes & reparse_flag)


def _ensure_control_tree(project: Path) -> Path:
    root = _assignment_root(project)
    directories = [
        project / "reviews",
        project / "reviews" / ".harness",
        root,
        *(root / name for name in (*STATE_NAMES, "claims", "ledger", "leases", "reservations", "journal", "prepared", "staged")),
    ]
    for directory in directories:
        if directory.exists() and (not directory.is_dir() or _is_link(directory)):
            raise ReceiptTransactionError(
                "APG-RECEIPT-PATH-INVALID",
                f"receipt control path is not a plain directory: {directory}",
            )
        directory.mkdir(parents=True, exist_ok=True)
        if _is_link(directory):
            raise ReceiptTransactionError(
                "APG-RECEIPT-PATH-INVALID",
                f"receipt control path is linked or junctioned: {directory}",
            )
    return root


def _has_link_escape(project: Path, relative: PurePosixPath) -> bool:
    current = project.resolve()
    for part in relative.parts:
        current = current / part
        if current.exists() and _is_link(current):
            return True
    return False


def _resolved_inside(project: Path, relative: PurePosixPath) -> Path:
    if _has_link_escape(project, relative):
        raise ReceiptTransactionError(
            "APG-RECEIPT-PATH-INVALID", f"path traverses a symlink or junction: {relative}"
        )
    root = project.resolve()
    resolved = (root / Path(*relative.parts)).resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ReceiptTransactionError(
            "APG-RECEIPT-PATH-INVALID", f"path escapes project root: {relative}"
        ) from exc
    return resolved


def _load_record(path: Path, code: str = "APG-RECEIPT-INVALID") -> dict[str, Any]:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReceiptTransactionError(code, f"cannot read valid JSON from {path}: {exc}") from exc
    if not isinstance(record, dict):
        raise ReceiptTransactionError(code, f"JSON record must be an object: {path}")
    return record


def _atomic_json(path: Path, payload: dict[str, Any], *, exclusive: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp.{os.getpid()}")
    data = _json_bytes(payload)
    try:
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if exclusive:
            os.link(temporary, path)
        else:
            os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _append_ledger(project: Path, basename: str, payload: dict[str, Any]) -> None:
    path = _assignment_root(project) / "ledger" / f"{basename}.jsonl"
    line = json.dumps(payload, sort_keys=True).encode("utf-8") + b"\n"
    prior = path.read_bytes() if path.exists() else b""
    temporary = path.with_name(path.name + f".tmp.{os.getpid()}")
    try:
        with temporary.open("xb") as handle:
            handle.write(prior + line)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _mutation_ledger_path(project: Path) -> Path:
    return _assignment_root(project) / "mutation_ledger.jsonl"


def _mutation_row_hash(row: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in row.items() if key != "row_sha256"}
    return hashlib.sha256(
        json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def load_mutation_ledger(project: Path) -> list[dict[str, Any]]:
    """Load and verify the append-only manuscript mutation hash-chain."""
    path = _mutation_ledger_path(project.resolve())
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    prior: str | None = None
    try:
        for sequence, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError("row is not an object")
            if row.get("sequence") != sequence or row.get("prior_row_sha256") != prior:
                raise ValueError("sequence or prior-row binding is invalid")
            digest = row.get("row_sha256")
            if not isinstance(digest, str) or digest != _mutation_row_hash(row):
                raise ValueError("row hash is invalid")
            rows.append(row)
            prior = digest
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ReceiptTransactionError(
            "APG-MUTATION-LEDGER-INVALID", f"invalid mutation ledger: {exc}"
        ) from exc
    return rows


def validate_mutation_target(project: Path, target_path: str) -> dict[str, Any]:
    """Require live target bytes to equal the last sanctioned postimage."""
    project = project.resolve()
    relative = _safe_relative(target_path, "APG-MUTATION-TARGET")
    rows = [row for row in load_mutation_ledger(project)
            if row.get("target_path") == relative.as_posix()]
    if not rows:
        raise ReceiptTransactionError(
            "APG-MUTATION-AUTHORITY-MISSING",
            f"target has no sanctioned mutation row: {relative.as_posix()}",
        )
    target = _resolved_inside(project, relative)
    live = _target_snapshot(target)
    expected = rows[-1].get("postimage")
    if live != expected:
        raise ReceiptTransactionError(
            "APG-MUTATION-UNJOURNALED",
            f"live target differs from latest sanctioned postimage: {relative.as_posix()}",
        )
    return rows[-1]


def _append_mutation_rows(project: Path, record: dict[str, Any],
                          journal: dict[str, Any]) -> dict[str, str]:
    path = _mutation_ledger_path(project)
    rows = load_mutation_ledger(project)
    prior = rows[-1]["row_sha256"] if rows else None
    by_identity = {
        (row.get("receipt_id"), row.get("target_path")): row for row in rows
    }
    appended: list[dict[str, Any]] = []
    row_hashes: dict[str, str] = {}
    for write in journal["writes"]:
        identity = (record["receipt_id"], write["target_path"])
        existing = by_identity.get(identity)
        postimage = _target_snapshot(
            _resolved_inside(project, _safe_relative(write["target_path"]))
        )
        if postimage.get("sha256") != write["desired_sha256"]:
            raise ReceiptTransactionError(
                "APG-MUTATION-UNJOURNALED",
                f"published target does not equal desired postimage: {write['target_path']}",
            )
        if existing is not None:
            if existing.get("postimage") != postimage or existing.get("preimage") != write["preimage"]:
                raise ReceiptTransactionError(
                    "APG-MUTATION-LEDGER-INVALID",
                    f"existing mutation row conflicts with publication: {write['target_path']}",
                )
            row_hashes[write["target_path"]] = existing["row_sha256"]
            continue
        row = {
            "schema_version": "1.0.0",
            "sequence": len(rows) + len(appended) + 1,
            "prior_row_sha256": prior,
            "receipt_id": record["receipt_id"],
            "reservation_id": record["reservation_id"],
            "target_path": write["target_path"],
            "mode": write["mode"],
            "preimage": write["preimage"],
            "postimage": postimage,
        }
        row["row_sha256"] = _mutation_row_hash(row)
        appended.append(row)
        prior = row["row_sha256"]
        row_hashes[write["target_path"]] = row["row_sha256"]
    append_state = {
        "state": "prepared",
        "prior_row_count": len(rows),
        "prior_head": rows[-1]["row_sha256"] if rows else None,
        "prospective_rows": appended,
        "prospective_row_count": len(rows) + len(appended),
        "prospective_head": prior,
        "targets": [
            {
                "path": write["target_path"],
                "sha256": write["desired_sha256"],
            }
            for write in journal["writes"]
        ],
    }
    journal["mutation_append"] = append_state
    journal_path = _assignment_root(project) / "journal" / f"{record['receipt_id']}.json"
    _atomic_json(journal_path, journal)
    if appended:
        path.parent.mkdir(parents=True, exist_ok=True)
        prior_bytes = path.read_bytes() if path.exists() else b""
        payload = prior_bytes + b"".join(
            json.dumps(row, sort_keys=True).encode("utf-8") + b"\n" for row in appended
        )
        temporary = path.with_name(path.name + f".tmp.{os.getpid()}")
        try:
            with temporary.open("xb") as handle:
                handle.write(payload); handle.flush(); os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
    append_state["state"] = "ledger_appended"
    append_state["ledger_sha256"] = _sha256(path)
    _atomic_json(journal_path, journal)
    return row_hashes


def _write_mutation_append_marker(
    project: Path,
    record: dict[str, Any],
    consumed: Path,
    journal_path: Path,
) -> Path:
    ledger_path = _mutation_ledger_path(project)
    rows = load_mutation_ledger(project)
    marker_path = (
        _assignment_root(project)
        / "mutation"
        / "append"
        / str(record["receipt_id"])
        / "commit_marker.json"
    )
    marker = {
        "schema_version": "1.0.0",
        "state": "committed",
        "receipt_id": record["receipt_id"],
        "reservation_id": record["reservation_id"],
        "consumed_receipt": consumed.relative_to(project).as_posix(),
        "consumed_receipt_sha256": _sha256(consumed),
        "journal": journal_path.relative_to(project).as_posix(),
        "journal_sha256": _sha256(journal_path),
        "ledger": ledger_path.relative_to(project).as_posix(),
        "ledger_sha256": _sha256(ledger_path),
        "row_count": len(rows),
        "head": rows[-1]["row_sha256"] if rows else None,
    }
    _atomic_json(marker_path, marker, exclusive=True)
    return marker_path


def _ledger_events(project: Path, basename: str) -> list[dict[str, Any]]:
    path = _assignment_root(project) / "ledger" / f"{basename}.jsonl"
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            if not isinstance(event, dict):
                raise ValueError("ledger row is not an object")
            events.append(event)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ReceiptTransactionError("APG-RECEIPT-INVALID", f"invalid receipt ledger: {exc}") from exc
    return events


@contextmanager
def _transaction_claim(project: Path):
    """Serialize all receipt and target transitions within one project.

    An unclean termination may leave the claim. There is deliberately no TTL:
    the explicit recovery command must inspect state before clearing residue.
    """
    root = _ensure_control_tree(project)
    claim = root / "claims" / "transaction.lock"
    try:
        with claim.open("xb") as handle:
            handle.write(json.dumps({
                "pid": os.getpid(),
                "host": platform.node(),
                "started_at": datetime.now(timezone.utc).isoformat(),
            }).encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise ReceiptTransactionError(
            "APG-RECEIPT-IN-USE", "another receipt transition is already in progress"
        ) from exc
    try:
        yield
    finally:
        try:
            claim.unlink()
        except FileNotFoundError:
            pass


def _state_files(project: Path, basename: str) -> dict[str, Path]:
    return {
        state: state_path(project, basename, state)
        for state in STATE_NAMES
        if state_path(project, basename, state).is_file()
    }


def _state_failure(project: Path, basename: str, expected: str) -> ReceiptTransactionError:
    present = _state_files(project, basename)
    events = _ledger_events(project, basename)
    last = events[-1].get("state") if events else None
    if len(present) > 1:
        return ReceiptTransactionError(
            "APG-RECEIPT-DUPLICATE-STATE",
            f"receipt exists in multiple lifecycle states: {sorted(present)}",
        )
    if last == "consumed" or "consumed" in present:
        return ReceiptTransactionError("APG-RECEIPT-CONSUMED", "receipt has already been consumed")
    if last == "invalidated" or "invalidated" in present:
        return ReceiptTransactionError("APG-RECEIPT-INVALID", "receipt has been invalidated")
    if last == "reserved" or "reserved" in present:
        return ReceiptTransactionError("APG-RECEIPT-RESERVED", "receipt has already been reserved")
    if "ready" in present and expected != "ready":
        return ReceiptTransactionError("APG-RECEIPT-INVALID", "receipt has not been reserved")
    return ReceiptTransactionError("APG-RECEIPT-MISSING", "receipt is missing")


def _require_state_path(project: Path, supplied: Path, expected: str) -> Path:
    canonical = state_path(project, supplied.name, expected).resolve()
    if supplied.resolve() != canonical:
        raise ReceiptTransactionError(
            "APG-RECEIPT-PATH-INVALID",
            f"receipt must be supplied from the canonical {expected} directory",
        )
    present = _state_files(project, supplied.name)
    if len(present) != 1 or expected not in present:
        raise _state_failure(project, supplied.name, expected)
    events = _ledger_events(project, supplied.name)
    if events and events[-1].get("state") in {"consumed", "invalidated"}:
        raise _state_failure(project, supplied.name, expected)
    return canonical


def _exclusive_move(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise ReceiptTransactionError(
            "APG-RECEIPT-DUPLICATE-STATE", f"destination lifecycle state already exists: {target}"
        )
    try:
        os.rename(source, target)
    except FileExistsError as exc:
        raise ReceiptTransactionError(
            "APG-RECEIPT-DUPLICATE-STATE", f"destination lifecycle state already exists: {target}"
        ) from exc
    except OSError as exc:
        raise ReceiptTransactionError(
            "APG-RECEIPT-INVALID", f"atomic lifecycle rename failed: {exc}",
        ) from exc


def _verify_live(project: Path, receipt: Path) -> dict[str, Any]:
    from assignment_process_gate import verify_receipt

    findings = verify_receipt(project, receipt)
    if findings:
        code, message = findings[0]
        raise ReceiptTransactionError(code, message)
    return _load_record(receipt)


def _target_key(path: str) -> str:
    return hashlib.sha256(path.casefold().encode("utf-8")).hexdigest()


def _target_snapshot(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "sha256": None, "size": 0}
    if not path.is_file() or path.is_symlink():
        raise ReceiptTransactionError("APG-RECEIPT-PATH-INVALID", f"target is not a plain file: {path}")
    return {"exists": True, "sha256": _sha256(path), "size": path.stat().st_size}


def _write_lease(project: Path, target_path: str, payload: dict[str, Any]) -> None:
    lease = _assignment_root(project) / "leases" / f"{_target_key(target_path)}.json"
    _atomic_json(lease, payload)


def reserve_receipt(
    project: Path,
    receipt: Path,
    expected_target: str,
    requested_paths: list[str],
) -> tuple[dict[str, Any], Path]:
    project = project.resolve()
    guard_project_root(project)
    with _transaction_claim(project):
        ready = _require_state_path(project, receipt, "ready")
        record = _verify_live(project, ready)
        if record.get("target_milestone") != expected_target:
            raise ReceiptTransactionError(
                "APG-RECEIPT-TARGET-MISMATCH",
                f"expected {expected_target}; receipt authorizes {record.get('target_milestone')}",
            )
        requested = [_safe_relative(path).as_posix() for path in requested_paths]
        if not requested or len(set(requested)) != len(requested):
            raise ReceiptTransactionError("APG-RECEIPT-PATH-MISMATCH", "dispatch paths must be non-empty and unique")
        authority = {row["path"]: row["mode"] for row in record.get("authorized_writes", [])}
        if any(path not in authority for path in requested):
            raise ReceiptTransactionError(
                "APG-RECEIPT-PATH-MISMATCH", "dispatch requests a path outside receipt authority"
            )
        if record.get("primary_deliverable_path") not in requested:
            raise ReceiptTransactionError(
                "APG-RECEIPT-PATH-MISMATCH", "dispatch must include the primary deliverable path"
            )

        reservation_writes: list[dict[str, Any]] = []
        for path_string in requested:
            target = _resolved_inside(project, _safe_relative(path_string))
            lease_path = _assignment_root(project) / "leases" / f"{_target_key(path_string)}.json"
            if lease_path.is_file():
                lease = _load_record(lease_path)
                if lease.get("state") == "active":
                    if lease.get("receipt_id") != record.get("receipt_id"):
                        raise ReceiptTransactionError("APG-TARGET-LEASED", f"target already has a live receipt: {path_string}")
                if (
                    lease.get("state") == "completed"
                    and lease.get("phase_state_sha256") == record.get("phase_state_sha256")
                ):
                    raise ReceiptTransactionError(
                        "APG-TARGET-ALREADY-WRITTEN",
                        f"target was already published from this phase-state snapshot: {path_string}",
                    )
            preimage = _target_snapshot(target)
            reservation_writes.append({
                "path": path_string,
                "mode": authority[path_string],
                "preimage": preimage,
            })

        reservation = {
            "schema_version": "1.0.0",
            "receipt_id": record["receipt_id"],
            "reservation_id": record["reservation_id"],
            "receipt_sha256": _sha256(ready),
            "target_milestone": record["target_milestone"],
            "role": record["authorized_role"],
            "phase_state_sha256": record["phase_state_sha256"],
            "writes": reservation_writes,
        }
        reservation_path = _assignment_root(project) / "reservations" / f"{record['receipt_id']}.json"
        if reservation_path.is_file():
            if _load_record(reservation_path) != reservation:
                raise ReceiptTransactionError(
                    "APG-RECEIPT-RESERVATION-MISMATCH",
                    "existing reservation record differs from this exact reservation",
                )
        else:
            try:
                _atomic_json(reservation_path, reservation, exclusive=True)
            except FileExistsError as exc:
                raise ReceiptTransactionError("APG-RECEIPT-RESERVED", "reservation record already exists") from exc
        for row in reservation_writes:
            _write_lease(project, row["path"], {
                "schema_version": "1.0.0",
                "state": "active",
                "receipt_id": record["receipt_id"],
                "reservation_id": record["reservation_id"],
                "phase_state_sha256": record["phase_state_sha256"],
                "target_path": row["path"],
            })
        reserved = state_path(project, ready.name, "reserved")
        _exclusive_move(ready, reserved)
        _append_ledger(project, ready.name, {
            "state": "reserved",
            "receipt_id": record["receipt_id"],
            "reservation_id": record["reservation_id"],
        })
    return record, reserved


def _validate_plan(
    project: Path,
    record: dict[str, Any],
    reservation: dict[str, Any],
    plan_path: Path,
    recovery_desired: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    plan = _load_record(plan_path, "APG-WRITE-PLAN-INVALID")
    if set(plan) != PLAN_FIELDS:
        raise ReceiptTransactionError("APG-WRITE-PLAN-INVALID", "write plan fields are invalid")
    if plan.get("schema_version") != "1.0.0" or plan.get("receipt_id") != record.get("receipt_id"):
        raise ReceiptTransactionError("APG-WRITE-PLAN-INVALID", "write plan receipt binding is invalid")
    if plan.get("reservation_id") != record.get("reservation_id"):
        raise ReceiptTransactionError(
            "APG-RECEIPT-RESERVATION-MISMATCH", "write plan reservation token does not match"
        )
    if plan.get("target_milestone") != record.get("target_milestone"):
        raise ReceiptTransactionError("APG-RECEIPT-TARGET-MISMATCH", "write plan target does not match receipt")
    if plan.get("role") != record.get("authorized_role"):
        raise ReceiptTransactionError("APG-RECEIPT-ROLE-MISMATCH", "write plan role does not match receipt authority")
    writes = plan.get("writes")
    if not isinstance(writes, list) or not writes:
        raise ReceiptTransactionError("APG-WRITE-PLAN-INVALID", "write plan needs at least one write")

    reserved_by_path = {row["path"]: row for row in reservation.get("writes", [])}
    expected_stage_root = (_assignment_root(project) / "staged" / str(record["receipt_id"])).resolve()
    targets_seen: set[str] = set()
    validated: list[dict[str, Any]] = []
    for row in writes:
        if not isinstance(row, dict) or set(row) != WRITE_FIELDS:
            raise ReceiptTransactionError("APG-WRITE-PLAN-INVALID", "write row fields are invalid")
        staged_rel = _safe_relative(row.get("staged_path"))
        target_rel = _safe_relative(row.get("target_path"))
        target_string = target_rel.as_posix()
        if target_string not in reserved_by_path:
            raise ReceiptTransactionError(
                "APG-RECEIPT-PATH-MISMATCH", f"target was not reserved: {target_string}"
            )
        if target_string in targets_seen:
            raise ReceiptTransactionError("APG-WRITE-PLAN-INVALID", "duplicate target path")
        targets_seen.add(target_string)
        staged = _resolved_inside(project, staged_rel)
        try:
            staged.relative_to(expected_stage_root)
        except ValueError as exc:
            raise ReceiptTransactionError(
                "APG-RECEIPT-PATH-INVALID", "staged file is outside receipt-scoped staging"
            ) from exc
        if not staged.is_file() or staged.is_symlink():
            raise ReceiptTransactionError("APG-WRITE-PLAN-INVALID", "staged file is missing or linked")
        digest = row.get("sha256")
        if not isinstance(digest, str) or _sha256(staged) != digest:
            raise ReceiptTransactionError("APG-WRITE-HASH-MISMATCH", "staged file hash does not match")
        target = _resolved_inside(project, target_rel)
        reservation_row = reserved_by_path[target_string]
        current = _target_snapshot(target)
        already_published = (
            current["exists"]
            and recovery_desired is not None
            and recovery_desired.get(target_string) == digest
            and current["sha256"] == digest
        )
        if current != reservation_row["preimage"] and not already_published:
            raise ReceiptTransactionError("APG-WRITE-PREIMAGE-MISMATCH", f"target changed after reservation: {target_string}")
        if reservation_row["mode"] == "create" and current["exists"]:
            raise ReceiptTransactionError("APG-WRITE-MODE-MISMATCH", f"create target already exists: {target_string}")
        if reservation_row["mode"] == "append" and current["exists"] and not already_published:
            old = target.read_bytes()
            new = staged.read_bytes()
            if not new.startswith(old) or len(new) <= len(old):
                raise ReceiptTransactionError(
                    "APG-WRITE-MODE-MISMATCH",
                    f"append target must be staged as a strict extension: {target_string}",
                )
        validated.append({
            "staged": staged,
            "target": target,
            "target_path": target_string,
            "sha256": digest,
            "mode": reservation_row["mode"],
            "preimage": reservation_row["preimage"],
        })
    if set(targets_seen) != set(reserved_by_path):
        raise ReceiptTransactionError(
            "APG-RECEIPT-PATH-MISMATCH", "write plan must exactly match the reserved path set"
        )
    return validated


def _copy_fsync(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as reader, target.open("xb") as writer:
        shutil.copyfileobj(reader, writer)
        writer.flush()
        os.fsync(writer.fileno())


def _ensure_prepared_copy(source: Path, target: Path, expected_hash: str) -> None:
    if target.is_file():
        if _sha256(target) != expected_hash:
            raise ReceiptTransactionError(
                "APG-WRITE-JOURNAL-INVALID", f"prepared recovery copy is stale: {target}"
            )
        return
    _copy_fsync(source, target)
    if _sha256(target) != expected_hash:
        raise ReceiptTransactionError(
            "APG-WRITE-JOURNAL-INVALID", f"prepared recovery copy hash mismatch: {target}"
        )


def _prepare_journal(
    project: Path,
    record: dict[str, Any],
    plan_path: Path,
    writes: list[dict[str, Any]],
) -> tuple[Path, dict[str, Any]]:
    root = _assignment_root(project)
    journal_path = root / "journal" / f"{record['receipt_id']}.json"
    plan_hash = _sha256(plan_path)
    if journal_path.is_file():
        journal = _load_record(journal_path, "APG-WRITE-JOURNAL-INVALID")
        if journal.get("plan_sha256") != plan_hash:
            raise ReceiptTransactionError("APG-WRITE-JOURNAL-INVALID", "recovery plan differs from journal")
        return journal_path, journal

    prepared_root = root / "prepared" / str(record["receipt_id"])
    prepared_root.mkdir(parents=True, exist_ok=True)
    journal_writes: list[dict[str, Any]] = []
    for index, row in enumerate(writes):
        new_path = prepared_root / f"{index}.new"
        _ensure_prepared_copy(row["staged"], new_path, row["sha256"])
        old_path: Path | None = None
        if row["preimage"]["exists"]:
            old_path = prepared_root / f"{index}.old"
            _ensure_prepared_copy(
                row["target"], old_path, str(row["preimage"]["sha256"])
            )
        journal_writes.append({
            "target_path": row["target_path"],
            "mode": row["mode"],
            "desired_sha256": row["sha256"],
            "preimage": row["preimage"],
            "prepared_new": new_path.relative_to(project).as_posix(),
            "prepared_old": old_path.relative_to(project).as_posix() if old_path else None,
            "applied": False,
        })
    journal = {
        "schema_version": "1.0.0",
        "receipt_id": record["receipt_id"],
        "reservation_id": record["reservation_id"],
        "plan_sha256": plan_hash,
        "state": "prepared",
        "writes": journal_writes,
    }
    _atomic_json(journal_path, journal, exclusive=True)
    return journal_path, journal


def _publish_one(project: Path, row: dict[str, Any]) -> None:
    target = _resolved_inside(project, _safe_relative(row["target_path"]))
    current = _target_snapshot(target)
    if current["exists"] and current["sha256"] == row["desired_sha256"]:
        return
    if current != row["preimage"]:
        raise ReceiptTransactionError(
            "APG-WRITE-PREIMAGE-MISMATCH", f"target changed during publication: {row['target_path']}"
        )
    prepared = _resolved_inside(project, _safe_relative(row["prepared_new"]))
    if not prepared.is_file() or _sha256(prepared) != row["desired_sha256"]:
        raise ReceiptTransactionError("APG-WRITE-JOURNAL-INVALID", "prepared publication bytes are missing or stale")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(
        f".{target.name}.{row['desired_sha256'][:12]}.{os.getpid()}.publish.tmp"
    )
    try:
        _copy_fsync(prepared, temporary)
        os.replace(temporary, target)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _rollback(project: Path, journal: dict[str, Any]) -> bool:
    ok = True
    for row in reversed(journal["writes"]):
        if not row.get("applied"):
            continue
        try:
            target = _resolved_inside(project, _safe_relative(row["target_path"]))
            old_rel = row.get("prepared_old")
            if old_rel is None:
                if target.exists():
                    target.unlink()
            else:
                old = _resolved_inside(project, _safe_relative(old_rel))
                temporary = target.with_name(f".{target.name}.{os.getpid()}.rollback.tmp")
                _copy_fsync(old, temporary)
                os.replace(temporary, target)
            row["applied"] = False
        except (OSError, ReceiptTransactionError):
            ok = False
    return ok


def commit_receipt(
    project: Path,
    receipt: Path,
    plan_path: Path,
    *,
    fail_after_consume: bool = False,
    fail_after_mutation_append: bool = False,
) -> tuple[Path, Path]:
    project = project.resolve()
    guard_project_root(project)
    with _transaction_claim(project):
        reserved = _require_state_path(project, receipt, "reserved")
        record = _verify_live(project, reserved)
        reservation_path = _assignment_root(project) / "reservations" / f"{record['receipt_id']}.json"
        reservation = _load_record(reservation_path, "APG-RECEIPT-RESERVATION-MISMATCH")
        if (
            reservation.get("receipt_id") != record.get("receipt_id")
            or reservation.get("reservation_id") != record.get("reservation_id")
            or reservation.get("receipt_sha256") != _sha256(reserved)
        ):
            raise ReceiptTransactionError(
                "APG-RECEIPT-RESERVATION-MISMATCH", "reservation record does not bind this receipt"
            )
        existing_journal_path = _assignment_root(project) / "journal" / f"{record['receipt_id']}.json"
        recovery_desired: dict[str, str] | None = None
        if existing_journal_path.is_file():
            existing_journal = _load_record(
                existing_journal_path, "APG-WRITE-JOURNAL-INVALID"
            )
            if existing_journal.get("plan_sha256") != _sha256(plan_path):
                raise ReceiptTransactionError(
                    "APG-WRITE-JOURNAL-INVALID", "recovery plan differs from journal"
                )
            recovery_desired = {
                row.get("target_path"): row.get("desired_sha256")
                for row in existing_journal.get("writes", [])
                if isinstance(row, dict)
                and isinstance(row.get("target_path"), str)
                and isinstance(row.get("desired_sha256"), str)
            }
        writes = _validate_plan(
            project, record, reservation, plan_path, recovery_desired=recovery_desired
        )
        journal_path, journal = _prepare_journal(project, record, plan_path, writes)
        journal["state"] = "publishing"
        _atomic_json(journal_path, journal)
        try:
            if fail_after_consume:
                raise OSError("injected failure before publication finalization")
            for row in journal["writes"]:
                _publish_one(project, row)
                row["applied"] = True
                _atomic_json(journal_path, journal)
        except (OSError, ReceiptTransactionError) as exc:
            rolled_back = _rollback(project, journal)
            journal["state"] = "prepared" if rolled_back else "recovery_required"
            _atomic_json(journal_path, journal)
            raise ReceiptTransactionError(
                "APG-WRITE-PUBLISH-FAILED",
                f"publication interrupted; {'rolled back' if rolled_back else 'explicit recovery required'}: {exc}",
            ) from exc

        consumed = state_path(project, reserved.name, "consumed")
        result_path = consumed.with_suffix(".result.json")
        mutation_hashes = _append_mutation_rows(project, record, journal)
        if fail_after_mutation_append:
            raise ReceiptTransactionError(
                "APG-WRITE-PUBLISH-FAILED",
                "injected interruption after mutation append and before completion marker",
            )
        published = [
            {"path": row["target_path"], "sha256": row["desired_sha256"],
             "mode": row["mode"], "mutation_row_sha256": mutation_hashes[row["target_path"]]}
            for row in journal["writes"]
        ]
        result = {
            "schema_version": "1.0.0",
            "receipt_id": record["receipt_id"],
            "reservation_id": record["reservation_id"],
            "outcome": "published",
            "published": published,
        }
        if result_path.exists():
            if _load_record(result_path) != result:
                raise ReceiptTransactionError("APG-WRITE-JOURNAL-INVALID", "publication result conflicts")
        else:
            _atomic_json(result_path, result, exclusive=True)
        for row in reservation["writes"]:
            _write_lease(project, row["path"], {
                "schema_version": "1.0.0",
                "state": "completed",
                "receipt_id": record["receipt_id"],
                "reservation_id": record["reservation_id"],
                "phase_state_sha256": record["phase_state_sha256"],
                "target_path": row["path"],
            })
        journal["state"] = "published"
        _atomic_json(journal_path, journal)
        _exclusive_move(reserved, consumed)
        _append_ledger(project, reserved.name, {
            "state": "consumed",
            "receipt_id": record["receipt_id"],
            "reservation_id": record["reservation_id"],
        })
        _write_mutation_append_marker(project, record, consumed, journal_path)
    return consumed, result_path


def invalidate_receipt(project: Path, receipt: Path) -> Path:
    project = project.resolve()
    guard_project_root(project)
    with _transaction_claim(project):
        supplied = receipt.resolve()
        candidates = {
            state: state_path(project, receipt.name, state).resolve()
            for state in ("ready", "reserved")
        }
        source_state = next((state for state, path in candidates.items() if supplied == path), None)
        if source_state is None:
            raise ReceiptTransactionError(
                "APG-RECEIPT-PATH-INVALID", "only canonical ready or reserved receipts can be invalidated"
            )
        source = _require_state_path(project, receipt, source_state)
        record = _load_record(source)
        reservation_path = _assignment_root(project) / "reservations" / f"{record['receipt_id']}.json"
        if reservation_path.is_file():
            reservation = _load_record(reservation_path, "APG-RECEIPT-RESERVATION-MISMATCH")
            for row in reservation.get("writes", []):
                _write_lease(project, row["path"], {
                    "schema_version": "1.0.0",
                    "state": "invalidated",
                    "receipt_id": record["receipt_id"],
                    "reservation_id": record["reservation_id"],
                    "phase_state_sha256": record["phase_state_sha256"],
                    "target_path": row["path"],
                })
        invalidated = state_path(project, receipt.name, "invalidated")
        _exclusive_move(source, invalidated)
        _append_ledger(project, receipt.name, {
            "state": "invalidated",
            "receipt_id": record.get("receipt_id"),
            "reservation_id": record.get("reservation_id"),
        })
    return invalidated
