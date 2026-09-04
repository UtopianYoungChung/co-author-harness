#!/usr/bin/env python3
"""Journaled, marker-last publication for C2 evidence transactions."""

from __future__ import annotations

import contextlib
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


def _transaction_lane(root: Path, transaction_id: str) -> Path:
    """Keep live Workbench control state inside its instrument lane."""
    if classify(root) == "protected":
        return root / "reviews" / ".harness" / "evidence-transactions" / transaction_id
    return root / ".harness-evidence-transactions" / transaction_id


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


def _durable_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as handle:
        temporary = Path(handle.name)
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        _replace_with_transient_retry(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _exclusive_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(_canonical(value))
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise EvidencePublicationError(f"exclusive record already exists: {path}") from exc


def _exclusive_marker(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_file() and path.read_bytes() == data:
            return
        raise EvidencePublicationError(
            "commit marker already exists with different bytes; recovery required"
        )
    try:
        with path.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise EvidencePublicationError(
            "commit marker was concurrently created; recovery required"
        ) from exc


@contextlib.contextmanager
def _claim_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+b")
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
    for path, _data in resolved:
        assert_writable(path, purpose="evidence publication")
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
    lane = _transaction_lane(root, transaction_id)
    assert_writable(lane, purpose="evidence transaction state")
    prepared = lane / "prepared"
    claim_path = lane / "claim.json"
    journal_path = lane / "journal.json"
    with _claim_lock(lane / "claim.lock"):
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
            _exclusive_json(claim_path, claim)
            prepared.mkdir(parents=True, exist_ok=True)
            prepared_rows: list[dict[str, Any]] = []
            for index, (path, data) in enumerate(resolved):
                prepared_path = prepared / f"{index:03d}.bin"
                _durable_write(prepared_path, data)
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
            _exclusive_json(journal_path, journal)
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
            _durable_write(journal_path, _canonical(journal))
            _durable_write(claim_path, _canonical(claim))
            return
        journal["state"] = "publishing"
        _durable_write(journal_path, _canonical(journal))
        try:
            for row in journal["writes"][:-1]:
                destination = (root / row["path"]).resolve()
                prepared_path = (root / row["prepared"]).resolve(strict=True)
                _durable_write(destination, prepared_path.read_bytes())
                if row["path"] not in journal["published"]:
                    journal["published"].append(row["path"])
                _durable_write(journal_path, _canonical(journal))
            marker_row = journal["writes"][-1]
            marker_path = (root / marker_row["path"]).resolve()
            prepared_marker = (root / marker_row["prepared"]).resolve(strict=True)
            _exclusive_marker(marker_path, prepared_marker.read_bytes())
            if marker_row["path"] not in journal["published"]:
                journal["published"].append(marker_row["path"])
            journal["state"] = "published"
            _durable_write(journal_path, _canonical(journal))
            claim["state"] = "consumed"
            _durable_write(claim_path, _canonical(claim))
        except OSError as exc:
            journal["state"] = "publishing"
            _durable_write(journal_path, _canonical(journal))
            raise EvidencePublicationError(
                "publication interrupted; recovery required"
            ) from exc


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
    for path, _data in resolved:
        assert_writable(path, purpose="evidence recovery")
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
    lane = _transaction_lane(root, transaction_id).resolve()
    assert_writable(lane, purpose="evidence recovery transaction state")
    if not lane.is_relative_to(root):
        raise EvidencePublicationError("transaction lane escapes project root")
    claim_path = lane / "claim.json"
    journal_path = lane / "journal.json"
    with _claim_lock(lane / "claim.lock"):
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
                _durable_write(journal_path, _canonical(journal))
                raise EvidencePublicationError(
                    "published bytes diverge from prior state and intent"
                )
        marker_state = states[-1]
        if marker_state == "desired":
            if any(state != "desired" for state in states[:-1]):
                journal["state"] = "recovery_required"
                _durable_write(journal_path, _canonical(journal))
                raise EvidencePublicationError(
                    "visible commit marker has a non-matching output prefix"
                )
            journal["published"] = [row["path"] for row in expected_writes]
            journal["state"] = "published"
            claim["state"] = "consumed"
            _durable_write(journal_path, _canonical(journal))
            _durable_write(claim_path, _canonical(claim))
            return "committed"
        marker_destination = resolved[-1][0]
        if marker_destination.exists():
            journal["state"] = "recovery_required"
            _durable_write(journal_path, _canonical(journal))
            raise EvidencePublicationError(
                "prior marker occupies the exclusive commit path"
            )
        recovery_root = lane / "recovery"
        recovery_root.mkdir(parents=True, exist_ok=True)
        record_path = recovery_root / (
            f"{time.time_ns()}-{uuid.uuid4().hex}.json"
        )
        if all(state == "prior" for state in states):
            journal["state"] = "rolled_back"
            claim["state"] = "recovered_rollback"
            _durable_write(journal_path, _canonical(journal))
            _durable_write(claim_path, _canonical(claim))
            _exclusive_json(record_path, {
                "schema_version": "1.0.0",
                "transaction_id": transaction_id,
                "recovery": "rolled_back_no_durable_effects",
                "plan_sha256": journal["plan_sha256"],
            })
            return "rolled_back"
        for row, state, (destination, _data) in zip(
            journal["writes"], states, resolved, strict=True
        ):
            if state == "desired":
                continue
            prepared_path = (root / row["prepared"]).resolve(strict=True)
            if (
                not prepared_path.is_relative_to(lane / "prepared")
                or hashlib.sha256(prepared_path.read_bytes()).hexdigest()
                != row["sha256"]
            ):
                raise EvidencePublicationError("prepared recovery bytes are stale")
            if row is journal["writes"][-1]:
                _exclusive_marker(destination, prepared_path.read_bytes())
            else:
                _durable_write(destination, prepared_path.read_bytes())
        journal["published"] = [row["path"] for row in expected_writes]
        journal["state"] = "published"
        claim["state"] = "consumed"
        _durable_write(journal_path, _canonical(journal))
        _durable_write(claim_path, _canonical(claim))
        _exclusive_json(record_path, {
            "schema_version": "1.0.0",
            "transaction_id": transaction_id,
            "recovery": "rolled_forward_exact_intent",
            "plan_sha256": journal["plan_sha256"],
        })
        return "committed"
