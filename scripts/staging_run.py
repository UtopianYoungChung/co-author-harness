#!/usr/bin/env python3
"""Governed proposal-only staging and typed shipment transactions.

V2 emission requires an explicit invocation scope and context.  The historical
call shape remains readable for the frozen v1 compatibility control, but a v1
manifest can never prove application or satisfy v2 authority.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import stat
import subprocess
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator

from destination_capability import (  # noqa: F401 - stable re-export
    DestinationRefused,
    assert_writable,
    discovered_workspace_root,
)
from output_contract import normalized_file_sha256
from shipment_contract import (
    validate_application_receipt,
    validate_manifest as validate_v2_manifest,
)


HARNESS = Path(__file__).resolve().parent.parent
_STAGING_REL = Path("outputs") / "co-author-harness" / "staging"
_ID_RE = re.compile(r"^(run|shp)-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_RUN_DIRS = ("inputs", "work", "state", "evidence", "shipment")
_MEMBER_DIRS = ("inputs", "work", "state", "evidence")
_LOCK_NAME = ".TRANSACTION.lock"
_PARTIAL_NAME = ".MANIFEST.partial"
_JOURNAL = ["allocated", "members_written", "verified", "manifest_sealed", "closed"]
_APPLICATION_SCHEMA = HARNESS / "references" / "schemas" / "application_receipt.schema.json"
_RECOVERY_SCHEMA = HARNESS / "references" / "schemas" / "shipment_recovery_receipt.schema.json"
_REFUSAL_SCHEMA = HARNESS / "references" / "schemas" / "shipment_refusal_receipt.schema.json"
_OUTPUT_CONTRACT = HARNESS / "references" / "role_output_contract.json"
_KERNEL = HARNESS / "references" / "contract_kernel.v1.json"

_STABLE_CODES = frozenset(
    {
        "CAP-PLANE-MISSING", "CAP-STATUS-CONTRADICTION", "CONTRACT-HASH-STALE",
        "RUNTIME-PLANE-MISSING", "VERSION-LEGACY-NONAUTHORITATIVE",
        "OUTPUT-POPULATION-MISMATCH", "TRIGGER-UNKNOWN", "CLASS-UNKNOWN",
        "OCCURRENCE-DUPLICATE", "OCCURRENCE-CLOSURE-MISSING",
        "OCCURRENCE-STATE-CONTRADICTORY", "CONTEXT-SCOPE-MISMATCH",
        "CARDINALITY-VIOLATION", "ORDER-VIOLATION", "PATH-TRAVERSAL",
        "PATH-COLLISION", "PATH-REPARSE", "PATH-ESCAPE", "MEMBER-DUPLICATE",
        "MEMBER-UNLISTED", "OPERATION-INVENTORY-MISMATCH", "PREIMAGE-PRESENT",
        "PREIMAGE-STALE", "POSTIMAGE-TAMPERED", "TX-RETRY-CONFLICT",
        "TX-CONCURRENT", "TX-UNSEALED", "TX-RECOVERY-REQUIRED",
        "TX-ROLLBACK-FAILED", "RECEIPT-INVALID", "APPLICATION-UNPROVEN",
    }
)


class TransactionRefused(RuntimeError):
    """A fail-closed shipment refusal with one frozen stable code."""

    def __init__(self, code: str, detail: str):
        if code not in _STABLE_CODES:
            raise ValueError(f"unregistered transaction diagnostic {code!r}")
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _nfc(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_nfc(item) for item in value]
    if isinstance(value, tuple):
        return [_nfc(item) for item in value]
    if isinstance(value, Mapping):
        result: dict[Any, Any] = {}
        for key, item in value.items():
            normalized_key = _nfc(key)
            if normalized_key in result:
                raise TransactionRefused("PATH-COLLISION", "NFC creates a duplicate key")
            result[normalized_key] = _nfc(item)
        return result
    return value


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(_nfc(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _fresh_id(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}-{stamp}-{secrets.token_hex(4)}"


def default_staging_root() -> Path:
    root = discovered_workspace_root()
    if root is None:
        raise DestinationRefused(
            "DEST-UNGOVERNED",
            "no workspace routing manifest was discovered; no governed staging lane exists",
        )
    return root / _STAGING_REL


def create_run(work_id: str, staging_root: Path | None = None) -> Path:
    if not work_id or "/" in work_id or "\\" in work_id:
        raise ValueError(f"work_id must be a single path segment: {work_id!r}")
    base = Path(staging_root) if staging_root is not None else default_staging_root()
    run_dir = base / work_id / _fresh_id("run")
    kind = assert_writable(run_dir, purpose="staging-run creation")
    if kind != "staging":
        raise DestinationRefused(
            "DEST-PROTECTED", f"staging-run root {run_dir} classifies as {kind!r}"
        )
    run_dir.parent.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=False, exist_ok=False)
    for name in _RUN_DIRS:
        (run_dir / name).mkdir()
    return run_dir


def _manifest_path(run_dir: Path) -> Path:
    return Path(run_dir) / "shipment" / "MANIFEST.json"


def _lock_path(run_dir: Path) -> Path:
    return Path(run_dir) / "shipment" / _LOCK_NAME


def snapshot_input(run_dir: Path, source: Path) -> dict[str, Any]:
    run_dir = Path(run_dir)
    source = Path(source)
    if _manifest_path(run_dir).exists():
        raise FileExistsError("shipment already emitted; inputs are sealed")
    digest = sha256_file(source)
    snap_name = f"{len(list((run_dir / 'inputs').glob('*'))):04d}_{source.name}"
    snap = run_dir / "inputs" / snap_name
    shutil.copyfile(source, snap)
    if sha256_file(snap) != digest:
        snap.unlink()
        raise OSError(f"snapshot read-back mismatch for {source}")
    snap.chmod(stat.S_IREAD)
    return {
        "source_path": str(source),
        "snapshot_path": f"inputs/{snap_name}",
        "sha256": digest,
    }


def _harness_commit() -> str:
    result = subprocess.run(
        ["git", "-C", str(HARNESS), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.strip() if result.returncode == 0 else "0" * 40


def _plugin_version() -> str:
    for rel in ("version.json", "plugin.json", ".claude-plugin/plugin.json"):
        path = HARNESS / rel
        if path.is_file():
            document = json.loads(path.read_text(encoding="utf-8"))
            return str(document["version"])
    raise FileNotFoundError("package identity missing: version.json")


def _inventory(run_dir: Path) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for name in _MEMBER_DIRS:
        rows = []
        base = run_dir / name
        for path in sorted((item for item in base.rglob("*") if item.is_file()), key=lambda p: p.as_posix().casefold()):
            rows.append(
                {
                    "path": path.relative_to(run_dir).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
        result[name] = rows
    controls = ["shipment/MANIFEST.json"]
    controls.extend(
        f"shipment/{name}"
        for name in (
        "APPLICATION_RECEIPT.json",
        "CONSUMER_OBSERVATION_RECEIPT.json",
        "REFUSAL_RECEIPT.json",
        "RECOVERY_RECEIPT.json",
        )
    )
    result["shipment"] = controls
    return result


def _inventory_digest(run_dir: Path) -> str:
    inventory = _inventory(run_dir)
    inventory.pop("shipment", None)
    return _sha256_json(inventory)


def _enrich_operations(
    run_dir: Path,
    proposed_operations: list[dict[str, Any]],
    inventory: Mapping[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    members = {
        row["path"]: row
        for name in ("work", "state", "evidence")
        for row in inventory[name]
    }
    enriched = []
    for index, supplied in enumerate(proposed_operations, start=1):
        row = dict(supplied)
        artifact = str(row.get("artifact", ""))
        member = members.get(artifact)
        if member is None:
            raise TransactionRefused(
                "OPERATION-INVENTORY-MISMATCH", f"operation artifact {artifact!r} is not inventoried"
            )
        operation = str(row.get("op", ""))
        preimage = row.get("preimage")
        if not isinstance(preimage, Mapping):
            raise TransactionRefused("PREIMAGE-STALE", "every operation needs explicit preimage evidence")
        if operation == "create" and preimage.get("state") != "absent":
            raise TransactionRefused("PREIMAGE-PRESENT", "create lacks explicit absent-preimage evidence")
        if operation != "create" and (
            preimage.get("state") != "present" or not _SHA_RE.fullmatch(str(preimage.get("sha256", "")))
        ):
            raise TransactionRefused("PREIMAGE-STALE", "non-create preimage is absent or malformed")
        row.update(
            operation_id=row.get("operation_id") or f"op-{index:04d}",
            artifact_sha256=member["sha256"],
            preimage=dict(preimage),
            postimage_sha256=member["sha256"],
        )
        row.pop("sha256", None)
        enriched.append(row)
    if sorted(row["artifact"] for row in enriched) != sorted(members):
        raise TransactionRefused(
            "OPERATION-INVENTORY-MISMATCH", "operations and artifact inventory are not bijective"
        )
    return enriched


def _write_exclusive(path: Path, payload: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    if path.read_bytes() != payload:
        raise OSError(f"exclusive write read-back mismatch for {path}")


def _pid_alive(pid: object) -> bool:
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        process_query_limited_information = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(  # type: ignore[attr-defined]
            process_query_limited_information, False, pid
        )
        if not handle:
            return False
        ctypes.windll.kernel32.CloseHandle(handle)  # type: ignore[attr-defined]
        return True
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _acquire_lock(run_dir: Path, request: Mapping[str, Any]) -> Path:
    lock = _lock_path(run_dir)
    record = {
        "pid": os.getpid(),
        "started_at": _now(),
        "phase": "allocated",
        "preimage_inventory_sha256": _inventory_digest(run_dir),
        "request": request,
    }
    try:
        _write_exclusive(lock, _canonical_bytes(record))
    except FileExistsError:
        try:
            existing = json.loads(lock.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raise TransactionRefused("TX-RECOVERY-REQUIRED", "unreadable transaction lock")
        if _pid_alive(existing.get("pid")):
            raise TransactionRefused("TX-CONCURRENT", "another writer owns the transaction")
        raise TransactionRefused("TX-RECOVERY-REQUIRED", "an interrupted transaction requires recovery")
    return lock


def _update_lock(lock: Path, *, phase: str) -> None:
    record = json.loads(lock.read_text(encoding="utf-8"))
    record["phase"] = phase
    payload = _canonical_bytes(record)
    with lock.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _legacy_validate_manifest(document: Mapping[str, Any]) -> list[str]:
    problems = []
    if document.get("schema_version") != "1.0.0":
        problems.append("schema_version: must be 1.0.0")
    if not _ID_RE.match(str(document.get("shipment_id", ""))):
        problems.append("shipment_id: bad id")
    if not _ID_RE.match(str(document.get("run_id", ""))):
        problems.append("run_id: bad id")
    if document.get("effect_scope") != "proposal_only":
        problems.append("effect_scope: proposal only")
    for row in document.get("artifacts", []):
        if not _SHA_RE.match(str(row.get("sha256", ""))):
            problems.append("artifacts: bad sha256")
    return problems


def validate_manifest(document: Mapping[str, Any], *, run_dir: Path | None = None) -> list[str]:
    """Read legacy evidence or validate authoritative v2 through one kernel."""
    if document.get("schema_version") in {"1.0.0", "1.1.0"}:
        return _legacy_validate_manifest(document)
    return validate_v2_manifest(document, run_dir=run_dir)


def _emit_legacy_shipment(
    run_dir: Path,
    *,
    proposed_operations: list[dict[str, Any]],
    limitations: list[str],
    unresolved_findings: list[str],
) -> Path:
    artifacts = [
        {"path": row["path"], "sha256": row["sha256"]}
        for name, rows in _inventory(run_dir).items()
        if name in {"work", "state", "evidence"}
        for row in rows
    ]
    operations = []
    for operation in proposed_operations:
        row = dict(operation)
        row["sha256"] = sha256_file(run_dir / row["artifact"])
        operations.append(row)
    document = {
        "schema_version": "1.0.0",
        "shipment_id": _fresh_id("shp"),
        "run_id": run_dir.name,
        "work_id": run_dir.parent.name,
        "created_at": _now(),
        "producer": {"name": "co-author-harness", "harness_commit": _harness_commit()[:12]},
        "effect_scope": "proposal_only",
        "inputs": [],
        "proposed_operations": operations,
        "artifacts": artifacts,
        "limitations": list(limitations),
        "unresolved_findings": list(unresolved_findings),
    }
    problems = _legacy_validate_manifest(document)
    if problems:
        raise ValueError(f"invalid legacy evidence manifest: {problems[:3]}")
    target = _manifest_path(run_dir)
    _write_exclusive(target, json.dumps(document, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    return target


def emit_shipment(
    run_dir: Path,
    *,
    proposed_operations: list[dict[str, Any]],
    limitations: list[str],
    unresolved_findings: list[str],
    invocation_scope: str | None = None,
    context: Mapping[str, Any] | None = None,
    trigger_occurrences: list[dict[str, Any]] | None = None,
    trigger_closures: list[dict[str, Any]] | None = None,
    _shipment_id: str | None = None,
    _created_at: str | None = None,
    _fault_after: str | None = None,
) -> Path:
    """Emit v2 atomically, or the frozen legacy shape when no v2 scope is given."""
    run_dir = Path(run_dir)
    if invocation_scope is None and context is None:
        return _emit_legacy_shipment(
            run_dir,
            proposed_operations=proposed_operations,
            limitations=limitations,
            unresolved_findings=unresolved_findings,
        )
    if invocation_scope is None or context is None:
        raise TransactionRefused(
            "CONTEXT-SCOPE-MISMATCH", "v2 needs both invocation_scope and context"
        )

    inventory = _inventory(run_dir)
    operations = _enrich_operations(run_dir, proposed_operations, inventory)
    target = _manifest_path(run_dir)
    existing: Mapping[str, Any] | None = None
    if target.is_file():
        try:
            loaded = json.loads(target.read_text(encoding="utf-8"))
            if not isinstance(loaded, Mapping):
                raise TransactionRefused("TX-RECOVERY-REQUIRED", "manifest root is not an object")
            existing = loaded
        except (OSError, json.JSONDecodeError):
            raise TransactionRefused("TX-RECOVERY-REQUIRED", "manifest is unreadable")
    shipment_id = _shipment_id or (
        str(existing.get("shipment_id")) if existing is not None else _fresh_id("shp")
    )
    created_at = _created_at or (
        str(existing.get("created_at")) if existing is not None else _now()
    )
    request_inventory = {name: rows for name, rows in inventory.items() if name != "shipment"}
    contract = {
        "kernel_version": json.loads(_KERNEL.read_text(encoding="utf-8"))["schema_version"],
        "kernel_sha256": normalized_file_sha256(_KERNEL),
        "output_contract_id": "role-output-contract",
        "output_contract_version": "3.0.0",
        "output_contract_sha256": normalized_file_sha256(_OUTPUT_CONTRACT),
    }
    producer = {
        "name": "co-author-harness",
        "version": _plugin_version(),
        "commit": _harness_commit(),
    }
    request = {
        "shipment_id": shipment_id,
        "created_at": created_at,
        "invocation_scope": invocation_scope,
        "context": context,
        "trigger_occurrences": trigger_occurrences or [],
        "trigger_closures": trigger_closures or [],
        "proposed_operations": operations,
        "limitations": limitations,
        "unresolved_findings": unresolved_findings,
        "inventory": request_inventory,
        "producer": producer,
        "contract": contract,
    }
    request_sha256 = _sha256_json(request)
    if existing is not None:
        transaction = existing.get("transaction")
        existing_seal = transaction.get("seal") if isinstance(transaction, Mapping) else None
        existing_inventory = existing.get("inventories")
        sealed_request = {
            "shipment_id": existing.get("shipment_id"),
            "created_at": existing.get("created_at"),
            "invocation_scope": existing.get("invocation_scope"),
            "context": existing.get("context"),
            "trigger_occurrences": existing.get("trigger_occurrences"),
            "trigger_closures": existing.get("trigger_closures"),
            "proposed_operations": existing.get("proposed_operations"),
            "limitations": existing.get("limitations"),
            "unresolved_findings": existing.get("unresolved_findings"),
            "inventory": {
                name: existing_inventory.get(name)
                for name in _MEMBER_DIRS
            } if isinstance(existing_inventory, Mapping) else None,
            "producer": existing.get("producer"),
            "contract": existing.get("contract"),
        }
        sealed_sha256 = existing_seal.get("sha256") if isinstance(existing_seal, Mapping) else None
        if sealed_sha256 != _sha256_json(sealed_request):
            raise TransactionRefused("POSTIMAGE-TAMPERED", "sealed manifest request was modified")
        if (
            existing.get("schema_version") == "2.0.0"
            and sealed_sha256 == request_sha256
            and not validate_v2_manifest(existing, run_dir=run_dir)
        ):
            return target
        raise TransactionRefused("TX-RETRY-CONFLICT", "retry payload differs from sealed request")

    lock_request = {
        "shipment_id": shipment_id,
        "created_at": created_at,
        "invocation_scope": invocation_scope,
        "context": context,
        "trigger_occurrences": trigger_occurrences or [],
        "trigger_closures": trigger_closures or [],
        "proposed_operations": operations,
        "limitations": limitations,
        "unresolved_findings": unresolved_findings,
    }
    lock = _acquire_lock(run_dir, lock_request)
    if _fault_after == "allocated":
        raise TransactionRefused("TX-RECOVERY-REQUIRED", "injected interruption after allocation")
    try:
        _update_lock(lock, phase="members_written")
        if _fault_after == "members_written":
            _write_exclusive(run_dir / "shipment" / _PARTIAL_NAME, b'{"schema_version":"2.0.0"\n')
            raise TransactionRefused("TX-RECOVERY-REQUIRED", "injected interruption after members")

        document = {
            "schema_version": "2.0.0",
            "shipment_type": "successful_shipment",
            "shipment_id": shipment_id,
            "run_id": run_dir.name,
            "work_id": run_dir.parent.name,
            "created_at": created_at,
            "producer": producer,
            "contract": contract,
            "effect_scope": "proposal_only",
            "invocation_scope": invocation_scope,
            "context": dict(context),
            "trigger_occurrences": trigger_occurrences or [],
            "trigger_closures": trigger_closures or [],
            "inventories": inventory,
            "proposed_operations": operations,
            "transaction": {
                "journal": list(_JOURNAL),
                "seal": {"state": "sealed", "state_last": True, "sha256": request_sha256},
            },
            "limitations": list(limitations),
            "unresolved_findings": list(unresolved_findings),
        }
        problems = validate_v2_manifest(document, run_dir=run_dir)
        if problems:
            code = next((item for item in problems if item in _STABLE_CODES), "OCCURRENCE-STATE-CONTRADICTORY")
            lock.unlink(missing_ok=True)
            raise TransactionRefused(code, f"v2 validation refused emission: {problems[:3]}")
        _update_lock(lock, phase="verified")
        if _fault_after == "verified":
            raise TransactionRefused("TX-RECOVERY-REQUIRED", "injected interruption after verification")
        payload = json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
        _write_exclusive(target, payload)
        _update_lock(lock, phase="manifest_sealed")
        if _fault_after == "manifest_sealed":
            raise TransactionRefused("TX-RECOVERY-REQUIRED", "injected interruption after seal")
        _update_lock(lock, phase="closed")
        lock.unlink()
        if target.read_bytes() != payload:
            raise TransactionRefused("POSTIMAGE-TAMPERED", "manifest read-back diverged")
        return target
    except TransactionRefused:
        raise
    except Exception:
        # Unexpected failures preserve the lock and partial evidence for an
        # explicit recovery decision; they are never silently normalized.
        raise


def emit_refusal(
    run_dir: Path,
    *,
    invocation_scope: str,
    context: Mapping[str, Any],
    diagnostic_code: str,
    detail: str,
    recoverable: bool,
    limitations: list[str] | None = None,
    unresolved_findings: list[str] | None = None,
) -> Path:
    if diagnostic_code not in _STABLE_CODES:
        raise ValueError("refusal code is not in the frozen vocabulary")
    run_dir = Path(run_dir)
    target = _manifest_path(run_dir)
    receipt_target = run_dir / "shipment" / "REFUSAL_RECEIPT.json"
    if target.exists() or receipt_target.exists():
        raise TransactionRefused("TX-RETRY-CONFLICT", "refusal evidence already exists")
    created_at = _now()
    receipt_document = {
        "schema_version": "1.0.0",
        "receipt_type": "shipment_refusal",
        "receipt_id": f"refusal-{secrets.token_hex(8)}",
        "created_at": created_at,
        "work_id": run_dir.parent.name,
        "run_id": run_dir.name,
        "invocation_scope": invocation_scope,
        "context": dict(context),
        "diagnostic_code": diagnostic_code,
        "detail": detail,
        "recoverable": recoverable,
        "effect_scope": "proposal_only",
    }
    if not _validate_schema(receipt_document, _REFUSAL_SCHEMA):
        raise TransactionRefused("OCCURRENCE-STATE-CONTRADICTORY", "refusal receipt is invalid")
    document = {
        "schema_version": "2.0.0",
        "shipment_type": "refused_shipment",
        "shipment_id": _fresh_id("shp"),
        "run_id": run_dir.name,
        "work_id": run_dir.parent.name,
        "created_at": created_at,
        "producer": {"name": "co-author-harness", "version": _plugin_version(), "commit": _harness_commit()},
        "contract": {
            "kernel_version": json.loads(_KERNEL.read_text(encoding="utf-8"))["schema_version"],
            "kernel_sha256": normalized_file_sha256(_KERNEL),
            "output_contract_id": "role-output-contract",
            "output_contract_version": "3.0.0",
            "output_contract_sha256": normalized_file_sha256(_OUTPUT_CONTRACT),
        },
        "effect_scope": "proposal_only",
        "invocation_scope": invocation_scope,
        "context": dict(context),
        "refusal": {"code": diagnostic_code, "detail": detail, "recoverable": recoverable},
        "limitations": list(limitations or []),
        "unresolved_findings": list(unresolved_findings or []),
    }
    problems = validate_v2_manifest(document, run_dir=run_dir)
    if problems:
        raise TransactionRefused("OCCURRENCE-STATE-CONTRADICTORY", str(problems[:3]))
    _write_exclusive(
        receipt_target,
        json.dumps(receipt_document, indent=2, sort_keys=True).encode("utf-8") + b"\n",
    )
    # MANIFEST is the state-last seal and is never written before its distinct
    # refusal receipt is durable and schema-valid.
    _write_exclusive(target, json.dumps(document, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    return target


def verify_shipment(
    run_dir: Path,
    *,
    expected_consumer: Mapping[str, Any] | None = None,
    expected_authority_sha256: str | None = None,
) -> list[str]:
    run_dir = Path(run_dir)
    try:
        document = json.loads(_manifest_path(run_dir).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ["TX-UNSEALED"]
    if document.get("schema_version") in {"1.0.0", "1.1.0"}:
        problems = _legacy_validate_manifest(document)
        for row in document.get("artifacts", []):
            path = run_dir / row["path"]
            if not path.is_file() or sha256_file(path) != row["sha256"]:
                problems.append("POSTIMAGE-TAMPERED")
        return problems
    problems = validate_v2_manifest(document, run_dir=run_dir)
    receipt = run_dir / "shipment" / "APPLICATION_RECEIPT.json"
    if receipt.is_file() and not is_applied(
        run_dir,
        expected_consumer=expected_consumer,
        expected_authority_sha256=expected_authority_sha256,
    ):
        problems.append("APPLICATION-UNPROVEN")
    return sorted(set(problems))


def _validate_schema(document: Mapping[str, Any], schema_path: Path) -> bool:
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        return not any(Draft202012Validator(schema).iter_errors(document))
    except (OSError, json.JSONDecodeError):
        return False


def _application_pins_valid(
    expected_consumer: Mapping[str, Any] | None,
    expected_authority_sha256: str | None,
) -> bool:
    required = {"governance", "actor_id", "version", "sha256"}
    return (
        isinstance(expected_consumer, Mapping)
        and set(expected_consumer) == required
        and all(isinstance(expected_consumer[key], str) and expected_consumer[key] for key in required)
        and bool(_SHA_RE.fullmatch(str(expected_consumer.get("sha256", ""))))
        and isinstance(expected_authority_sha256, str)
        and bool(_SHA_RE.fullmatch(expected_authority_sha256))
    )


def _is_recognized_echo(path: Path) -> bool:
    """Recognition is a durable producer-set read-only echo, not presence."""
    try:
        return path.is_file() and not bool(path.stat().st_mode & stat.S_IWRITE)
    except OSError:
        return False


def recognize_application_receipt(
    run_dir: Path,
    receipt: Path,
    *,
    expected_consumer: Mapping[str, Any] | None = None,
    expected_authority_sha256: str | None = None,
) -> Path:
    run_dir = Path(run_dir)
    receipt = Path(receipt)
    if not _application_pins_valid(expected_consumer, expected_authority_sha256):
        raise TransactionRefused("RECEIPT-INVALID", "complete exact consumer and authority pins are required")
    if not receipt.is_file():
        raise TransactionRefused("RECEIPT-INVALID", "application receipt is absent")
    try:
        manifest_path = _manifest_path(run_dir)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        document = json.loads(receipt.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TransactionRefused("RECEIPT-INVALID", f"receipt is unreadable: {exc}")
    problems = validate_application_receipt(
        document,
        manifest,
        manifest_sha256=sha256_file(manifest_path),
        expected_consumer=expected_consumer,
        expected_authority_sha256=expected_authority_sha256,
    )
    if (
        validate_v2_manifest(manifest, run_dir=run_dir)
        or problems
        or not _validate_schema(document, _APPLICATION_SCHEMA)
    ):
        raise TransactionRefused("RECEIPT-INVALID", "external application receipt failed binding")
    target = run_dir / "shipment" / "APPLICATION_RECEIPT.json"
    payload = receipt.read_bytes()
    if target.exists():
        if target.read_bytes() == payload and is_applied(
            run_dir,
            expected_consumer=expected_consumer,
            expected_authority_sha256=expected_authority_sha256,
        ):
            return target
        raise TransactionRefused("RECEIPT-INVALID", "application receipt echo conflicts")
    _write_exclusive(target, payload)
    target.chmod(stat.S_IREAD)
    if not is_applied(
        run_dir,
        expected_consumer=expected_consumer,
        expected_authority_sha256=expected_authority_sha256,
    ):
        raise TransactionRefused("APPLICATION-UNPROVEN", "receipt echo did not validate")
    return target


def is_applied(
    run_dir: Path,
    *,
    expected_consumer: Mapping[str, Any] | None = None,
    expected_authority_sha256: str | None = None,
) -> bool:
    run_dir = Path(run_dir)
    target = run_dir / "shipment" / "APPLICATION_RECEIPT.json"
    manifest_path = _manifest_path(run_dir)
    if (
        not _application_pins_valid(expected_consumer, expected_authority_sha256)
        or not _is_recognized_echo(target)
        or not manifest_path.is_file()
    ):
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        receipt = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return not validate_v2_manifest(manifest, run_dir=run_dir) and not validate_application_receipt(
        receipt,
        manifest,
        manifest_sha256=sha256_file(manifest_path),
        expected_consumer=expected_consumer,
        expected_authority_sha256=expected_authority_sha256,
    )


def _write_recovery_receipt(
    run_dir: Path,
    *,
    lock_record: Mapping[str, Any],
    action: str,
    restored_sha256: str,
    outcome: str,
) -> Path:
    request = lock_record.get("request", {})
    document = {
        "schema_version": "1.0.0",
        "receipt_type": "shipment_recovery",
        "receipt_id": f"recovery-{secrets.token_hex(8)}",
        "created_at": _now(),
        "shipment_id": request.get("shipment_id", "unknown"),
        "journal_sha256": _sha256_json(_JOURNAL),
        "interrupted_state": lock_record.get("phase", "allocated"),
        "action": action,
        "preimage_inventory_sha256": lock_record.get("preimage_inventory_sha256", "0" * 64),
        "restored_inventory_sha256": restored_sha256,
        "outcome": outcome,
    }
    if not _validate_schema(document, _RECOVERY_SCHEMA):
        raise TransactionRefused("TX-ROLLBACK-FAILED", "recovery receipt is schema-invalid")
    target = run_dir / "shipment" / "RECOVERY_RECEIPT.json"
    if target.exists():
        try:
            existing = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raise TransactionRefused("TX-RETRY-CONFLICT", "recovery receipt is unreadable")
        binding_fields = (
            "shipment_id", "interrupted_state", "action", "preimage_inventory_sha256",
            "restored_inventory_sha256", "outcome",
        )
        if _validate_schema(existing, _RECOVERY_SCHEMA) and all(
            existing.get(field) == document.get(field) for field in binding_fields
        ):
            return target
        raise TransactionRefused("TX-RETRY-CONFLICT", "recovery receipt already conflicts")
    _write_exclusive(target, json.dumps(document, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    return target


def recover_shipment(run_dir: Path, *, action: str) -> Path:
    """Explicitly resume or exactly roll back an interrupted emission."""
    run_dir = Path(run_dir)
    lock = _lock_path(run_dir)
    recovery_guard = run_dir / "shipment" / ".RECOVERY.lock"
    if not lock.exists() and recovery_guard.exists():
        os.replace(recovery_guard, lock)
    elif lock.exists() and recovery_guard.exists():
        raise TransactionRefused("TX-CONCURRENT", "two recovery locks are present")
    if action not in {"resume", "rollback"} or not lock.is_file():
        raise TransactionRefused("TX-RECOVERY-REQUIRED", "no recoverable transaction is present")
    try:
        record = json.loads(lock.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise TransactionRefused("TX-RECOVERY-REQUIRED", "transaction record is unreadable")
    owner = record.get("pid")
    if owner != os.getpid() and _pid_alive(owner):
        raise TransactionRefused("TX-CONCURRENT", "live writer still owns the transaction")
    preimage = record.get("preimage_inventory_sha256")
    current = _inventory_digest(run_dir)
    if current != preimage:
        raise TransactionRefused("TX-ROLLBACK-FAILED", "producer members changed after allocation")
    partial = run_dir / "shipment" / _PARTIAL_NAME
    manifest = _manifest_path(run_dir)
    partial.unlink(missing_ok=True)

    if action == "rollback":
        manifest.unlink(missing_ok=True)
        restored = _inventory_digest(run_dir)
        if restored != preimage:
            raise TransactionRefused("TX-ROLLBACK-FAILED", "rollback did not restore exact inventory")
        receipt = _write_recovery_receipt(
            run_dir, lock_record=record, action="rollback", restored_sha256=restored, outcome="rolled_back"
        )
        _update_lock(lock, phase="closed")
        lock.unlink()
        return receipt

    if manifest.is_file():
        problems = validate_v2_manifest(
            json.loads(manifest.read_text(encoding="utf-8")), run_dir=run_dir
        )
        if not problems:
            _write_recovery_receipt(
                run_dir, lock_record=record, action="resume", restored_sha256=current, outcome="recovered"
            )
            _update_lock(lock, phase="closed")
            lock.unlink()
            return manifest
        manifest.unlink()
    os.replace(lock, recovery_guard)
    request = record["request"]
    try:
        recovered_manifest = emit_shipment(
            run_dir,
            proposed_operations=request["proposed_operations"],
            limitations=request["limitations"],
            unresolved_findings=request["unresolved_findings"],
            invocation_scope=request["invocation_scope"],
            context=request["context"],
            trigger_occurrences=request["trigger_occurrences"],
            trigger_closures=request["trigger_closures"],
            _shipment_id=request["shipment_id"],
            _created_at=request["created_at"],
        )
    except Exception:
        if not lock.exists() and recovery_guard.exists():
            os.replace(recovery_guard, lock)
        elif lock.exists():
            recovery_guard.unlink(missing_ok=True)
        raise
    try:
        _write_recovery_receipt(
            run_dir, lock_record=record, action="resume", restored_sha256=current, outcome="recovered"
        )
        _update_lock(recovery_guard, phase="closed")
        recovery_guard.unlink()
    except Exception:
        if not lock.exists() and recovery_guard.exists():
            os.replace(recovery_guard, lock)
        raise
    return recovered_manifest


__all__ = [
    "DestinationRefused",
    "TransactionRefused",
    "create_run",
    "default_staging_root",
    "emit_refusal",
    "emit_shipment",
    "is_applied",
    "recognize_application_receipt",
    "recover_shipment",
    "sha256_file",
    "snapshot_input",
    "validate_manifest",
    "verify_shipment",
]
