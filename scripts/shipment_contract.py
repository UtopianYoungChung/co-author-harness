#!/usr/bin/env python3
"""Canonical shipment-v2 schema, path, membership, and transaction validator.

Historical v1/v1.1 documents are intentionally recognizable but cannot pass
this v2 authority boundary.  The validator is read-only: it never allocates,
writes, seals, recovers, rolls back, or recognizes application authority.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator

from output_contract import normalize_windows_relative_path, validate_output_transaction


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "references" / "schemas" / "shipment_manifest.schema.json"
OUTPUT_CONTRACT_PATH = ROOT / "references" / "role_output_contract.json"
KERNEL_PATH = ROOT / "references" / "contract_kernel.v1.json"

_INVENTORY_NAMES = ("inputs", "work", "state", "evidence")
_SHIPMENT_CONTROL = frozenset(
    {
        "shipment/MANIFEST.json",
        "shipment/APPLICATION_RECEIPT.json",
        "shipment/CONSUMER_OBSERVATION_RECEIPT.json",
        "shipment/REFUSAL_RECEIPT.json",
        "shipment/RECOVERY_RECEIPT.json",
    }
)
_JOURNAL = ("allocated", "members_written", "verified", "manifest_sealed", "closed")
_LEGACY_VERSIONS = frozenset({"1.0.0", "1.1.0"})
_DIAGNOSTIC_ORDER = (
    "VERSION-LEGACY-NONAUTHORITATIVE",
    "CONTRACT-HASH-STALE",
    "OUTPUT-POPULATION-MISMATCH",
    "TRIGGER-UNKNOWN",
    "CLASS-UNKNOWN",
    "OCCURRENCE-DUPLICATE",
    "OCCURRENCE-CLOSURE-MISSING",
    "OCCURRENCE-STATE-CONTRADICTORY",
    "CONTEXT-SCOPE-MISMATCH",
    "CARDINALITY-VIOLATION",
    "ORDER-VIOLATION",
    "PATH-TRAVERSAL",
    "PATH-COLLISION",
    "PATH-REPARSE",
    "PATH-ESCAPE",
    "MEMBER-DUPLICATE",
    "MEMBER-UNLISTED",
    "OPERATION-INVENTORY-MISMATCH",
    "PREIMAGE-PRESENT",
    "PREIMAGE-STALE",
    "POSTIMAGE-TAMPERED",
    "TX-RETRY-CONFLICT",
    "TX-CONCURRENT",
    "TX-UNSEALED",
    "TX-RECOVERY-REQUIRED",
    "TX-ROLLBACK-FAILED",
    "RECEIPT-INVALID",
    "APPLICATION-UNPROVEN",
)


def _ordered(diagnostics: Iterable[str]) -> list[str]:
    order = {code: index for index, code in enumerate(_DIAGNOSTIC_ORDER)}
    return sorted(set(diagnostics), key=lambda code: (order.get(code, len(order)), code))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return document


def _json_pointer(parts: Iterable[object]) -> str:
    encoded = [str(part).replace("~", "~0").replace("/", "~1") for part in parts]
    return "/" + "/".join(encoded) if encoded else "/"


def schema_validation_errors(document: Mapping[str, Any]) -> list[str]:
    """Return deterministic detailed JSON-Schema violations.

    These details are deliberately separate from ``validate_manifest`` because
    C0 froze no generic schema-invalid diagnostic code.  Runtime callers can
    still fail closed on a non-empty result without inventing authority state.
    """
    try:
        schema = _load_json(SCHEMA_PATH)
        validator = Draft202012Validator(schema)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return [f"SCHEMA / unavailable: {type(exc).__name__}: {exc}"]
    errors = []
    for error in sorted(
        validator.iter_errors(document),
        key=lambda item: (tuple(str(part) for part in item.absolute_path), item.message),
    ):
        errors.append(
            f"SCHEMA {_json_pointer(error.absolute_path)} {error.validator}: {error.message}"
        )
    return errors


def _safe_key(value: object, diagnostics: set[str], *, destination: bool = False) -> str | None:
    try:
        return normalize_windows_relative_path(value)
    except ValueError:
        diagnostics.add("PATH-ESCAPE" if destination else "PATH-TRAVERSAL")
        return None


def _is_reparse(path: Path) -> bool:
    try:
        info = os.lstat(path)
    except OSError:
        return False
    attributes = getattr(info, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(info.st_mode) or bool(attributes & reparse_flag)


def _path_has_reparse(run_dir: Path, relative_path: object) -> bool:
    if not isinstance(relative_path, str):
        return False
    candidate = run_dir
    for part in relative_path.replace("\\", "/").split("/"):
        if part in {"", ".", ".."}:
            return False
        candidate /= part
        if _is_reparse(candidate):
            return True
    return False


def _is_contained(run_dir: Path, relative_path: object) -> bool:
    if not isinstance(relative_path, str):
        return False
    try:
        root = run_dir.resolve(strict=True)
        candidate = (run_dir / Path(*relative_path.replace("\\", "/").split("/"))).resolve(
            strict=False
        )
        candidate.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        return False
    return True


def _actual_members(run_dir: Path) -> tuple[set[str], bool]:
    members: set[str] = set()
    reparse = False
    for name in (*_INVENTORY_NAMES, "shipment"):
        base = run_dir / name
        if not base.exists():
            continue
        for candidate in base.rglob("*"):
            if _is_reparse(candidate):
                reparse = True
                continue
            if candidate.is_file():
                members.add(candidate.relative_to(run_dir).as_posix())
    return members, reparse


def _validate_contract_identity(document: Mapping[str, Any], diagnostics: set[str]) -> None:
    binding = document.get("contract")
    if not isinstance(binding, Mapping):
        diagnostics.add("CONTRACT-HASH-STALE")
        return
    try:
        output_bytes = OUTPUT_CONTRACT_PATH.read_bytes()
        output_document = json.loads(output_bytes.decode("utf-8"))
        if (
            binding.get("output_contract_id") != output_document.get("contract_id")
            or binding.get("output_contract_version") != output_document.get("schema_version")
            or binding.get("output_contract_sha256") != _sha256_bytes(output_bytes)
        ):
            diagnostics.add("CONTRACT-HASH-STALE")
        kernel_bytes = KERNEL_PATH.read_bytes()
        kernel = json.loads(kernel_bytes.decode("utf-8"))
        kernel_version = kernel.get("schema_version", kernel.get("version"))
        if (
            binding.get("kernel_version") != kernel_version
            or binding.get("kernel_sha256") != _sha256_bytes(kernel_bytes)
        ):
            diagnostics.add("CONTRACT-HASH-STALE")
    except (OSError, UnicodeError, json.JSONDecodeError, AttributeError):
        diagnostics.add("CONTRACT-HASH-STALE")


def _validate_inventory(
    document: Mapping[str, Any], run_dir: Path | None, diagnostics: set[str]
) -> dict[str, Mapping[str, Any]]:
    inventories = document.get("inventories")
    if not isinstance(inventories, Mapping):
        diagnostics.add("MEMBER-UNLISTED")
        return {}

    by_key: dict[str, Mapping[str, Any]] = {}
    spellings: dict[str, str] = {}
    declared: set[str] = set()
    for name in _INVENTORY_NAMES:
        rows = inventories.get(name, ())
        if not isinstance(rows, list):
            diagnostics.add("MEMBER-UNLISTED")
            continue
        for row in rows:
            if not isinstance(row, Mapping):
                diagnostics.add("MEMBER-UNLISTED")
                continue
            spelling = row.get("path")
            key = _safe_key(spelling, diagnostics)
            if key is None:
                continue
            if not key.startswith(name + "/"):
                diagnostics.add("PATH-ESCAPE")
            if key in by_key:
                if spellings[key] == spelling:
                    diagnostics.add("MEMBER-DUPLICATE")
                else:
                    diagnostics.add("PATH-COLLISION")
            else:
                by_key[key] = row
                spellings[key] = str(spelling)
            declared.add(key)
            if run_dir is not None:
                if _path_has_reparse(run_dir, spelling):
                    diagnostics.add("PATH-REPARSE")
                if not _is_contained(run_dir, spelling):
                    diagnostics.add("PATH-ESCAPE")
                candidate = run_dir / Path(*str(spelling).replace("\\", "/").split("/"))
                if candidate.is_file() and not _is_reparse(candidate):
                    if row.get("sha256") != _sha256_file(candidate):
                        diagnostics.add("POSTIMAGE-TAMPERED")
                    try:
                        if row.get("bytes") != candidate.stat().st_size:
                            diagnostics.add("POSTIMAGE-TAMPERED")
                    except OSError:
                        diagnostics.add("POSTIMAGE-TAMPERED")

    shipment_rows = inventories.get("shipment", ())
    if not isinstance(shipment_rows, list):
        diagnostics.add("MEMBER-UNLISTED")
        shipment_rows = []
    for spelling in shipment_rows:
        key = _safe_key(spelling, diagnostics)
        if key is not None:
            if key in declared:
                diagnostics.add("MEMBER-DUPLICATE")
            declared.add(key)
        if spelling not in _SHIPMENT_CONTROL:
            diagnostics.add("MEMBER-UNLISTED")

    fixture_facts = document.get("fixture_filesystem_facts", {})
    if isinstance(fixture_facts, Mapping):
        for spelling, kind in fixture_facts.items():
            key = _safe_key(spelling, diagnostics)
            if kind == "reparse":
                diagnostics.add("PATH-REPARSE")
            elif kind == "regular_file" and key is not None and key not in declared:
                diagnostics.add("MEMBER-UNLISTED")

    if run_dir is not None and run_dir.exists():
        actual, has_reparse = _actual_members(run_dir)
        if has_reparse:
            diagnostics.add("PATH-REPARSE")
        actual_keys = {
            key
            for spelling in actual
            if (key := _safe_key(spelling, diagnostics)) is not None
        }
        # During pre-emission validation MANIFEST.json is declared but not yet
        # present.  Every other declared member must match exact regular files.
        comparable_declared = declared - {"shipment/manifest.json"}
        comparable_actual = actual_keys - {"shipment/manifest.json"}
        if comparable_actual != comparable_declared:
            diagnostics.add("MEMBER-UNLISTED")

    return by_key


def _validate_operations(
    document: Mapping[str, Any], inventory: Mapping[str, Mapping[str, Any]], diagnostics: set[str]
) -> None:
    operations = document.get("proposed_operations")
    if not isinstance(operations, list):
        diagnostics.add("OPERATION-INVENTORY-MISMATCH")
        return

    operation_keys: list[str] = []
    observed_preimage = document.get("fixture_destination_preimage_sha256")
    for operation in operations:
        if not isinstance(operation, Mapping):
            diagnostics.add("OPERATION-INVENTORY-MISMATCH")
            continue
        artifact_key = _safe_key(operation.get("artifact"), diagnostics)
        _safe_key(operation.get("destination"), diagnostics, destination=True)
        if artifact_key is None:
            diagnostics.add("OPERATION-INVENTORY-MISMATCH")
            continue
        operation_keys.append(artifact_key)
        member = inventory.get(artifact_key)
        if member is None:
            diagnostics.add("OPERATION-INVENTORY-MISMATCH")
        else:
            artifact_hash = operation.get("artifact_sha256")
            if artifact_hash != member.get("sha256"):
                diagnostics.add("POSTIMAGE-TAMPERED")
            if operation.get("postimage_sha256") != artifact_hash:
                diagnostics.add("POSTIMAGE-TAMPERED")

        op = operation.get("op")
        preimage = operation.get("preimage")
        if not isinstance(preimage, Mapping):
            diagnostics.add("PREIMAGE-STALE")
            continue
        if op == "create":
            if preimage.get("state") != "absent":
                diagnostics.add("PREIMAGE-PRESENT")
        else:
            if preimage.get("state") != "present" or not preimage.get("sha256"):
                diagnostics.add("PREIMAGE-STALE")
            expected = operation.get("observed_preimage_sha256", observed_preimage)
            if expected is not None and preimage.get("sha256") != expected:
                diagnostics.add("PREIMAGE-STALE")
            if op in {"move", "rename", "delete"} and (
                not operation.get("source") or not preimage.get("recoverable_copy")
            ):
                diagnostics.add("PREIMAGE-STALE")

    if Counter(operation_keys) != Counter(inventory.keys()):
        diagnostics.add("OPERATION-INVENTORY-MISMATCH")


def _validate_transaction(document: Mapping[str, Any], diagnostics: set[str]) -> None:
    transaction = document.get("transaction")
    if not isinstance(transaction, Mapping):
        diagnostics.add("TX-UNSEALED")
        return
    seal = transaction.get("seal")
    journal = transaction.get("journal")
    if (
        journal != list(_JOURNAL)
        or not isinstance(seal, Mapping)
        or seal.get("state") != "sealed"
        or seal.get("state_last") is not True
    ):
        diagnostics.add("TX-UNSEALED")
    retry = transaction.get("retry")
    if isinstance(retry, Mapping) and retry.get("same_shipment_id") is True:
        expected = seal.get("sha256") if isinstance(seal, Mapping) else None
        if retry.get("payload_sha256") != expected:
            diagnostics.add("TX-RETRY-CONFLICT")
    writers = transaction.get("exclusive_writer_count")
    if isinstance(writers, int) and not isinstance(writers, bool) and writers > 1:
        diagnostics.add("TX-CONCURRENT")
    recovery = transaction.get("recovery")
    if isinstance(recovery, Mapping) and recovery.get("required") is True and not recovery.get("receipt"):
        diagnostics.add("TX-RECOVERY-REQUIRED")
    rollback = transaction.get("rollback")
    if isinstance(rollback, Mapping) and rollback.get("attempted") is True:
        if rollback.get("preimage_sha256") != rollback.get("restored_sha256"):
            diagnostics.add("TX-ROLLBACK-FAILED")


def validate_manifest(
    document: Mapping[str, Any], *, run_dir: str | Path | None = None
) -> list[str]:
    """Validate a shipment offered as authoritative v2 transaction evidence."""
    version = document.get("schema_version")
    if version in _LEGACY_VERSIONS:
        return ["VERSION-LEGACY-NONAUTHORITATIVE"]

    diagnostics: set[str] = set()
    if version != "2.0.0":
        diagnostics.add("CONTRACT-HASH-STALE")

    _validate_contract_identity(document, diagnostics)
    shipment_type = document.get("shipment_type")
    if shipment_type == "successful_shipment":
        resolved_run = Path(run_dir) if run_dir is not None else None
        inventory = _validate_inventory(document, resolved_run, diagnostics)
        _validate_operations(document, inventory, diagnostics)
        _validate_transaction(document, diagnostics)
        output_document = {
            "contract_id": document.get("contract", {}).get("output_contract_id")
            if isinstance(document.get("contract"), Mapping)
            else None,
            "contract_version": document.get("contract", {}).get("output_contract_version")
            if isinstance(document.get("contract"), Mapping)
            else None,
            "invocation_scope": document.get("invocation_scope"),
            "context": document.get("context"),
            "trigger_occurrences": document.get("trigger_occurrences", []),
            "closures": document.get("trigger_closures", []),
        }
        diagnostics.update(validate_output_transaction(OUTPUT_CONTRACT_PATH, output_document))
    elif shipment_type == "refused_shipment":
        if any(key in document for key in ("inventories", "proposed_operations", "transaction")):
            diagnostics.add("OCCURRENCE-STATE-CONTRADICTORY")
        if not isinstance(document.get("refusal"), Mapping):
            diagnostics.add("OCCURRENCE-STATE-CONTRADICTORY")
    else:
        diagnostics.add("OCCURRENCE-STATE-CONTRADICTORY")

    # Execute the canonical schema on every v2 document.  Mapped semantic
    # checks above return C0-frozen codes; unmapped details remain available
    # through schema_validation_errors() until Root assigns a generic code.
    diagnostics.update(schema_validation_errors(document))
    return _ordered(diagnostics)


__all__ = ["schema_validation_errors", "validate_manifest"]
