#!/usr/bin/env python3
"""Losslessly compact canonical JSON receipts under the frozen V40-06 index.

Each source receipt receives one exact-contract index in ``indices/`` and one
immutable descriptor in ``details/``. Descriptors reference shared,
content-addressed top-level field blobs in ``blobs/``. Source bytes are never
changed, and all output writes pass through destination capability.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import unicodedata
from pathlib import Path
from typing import Any, Callable, Iterable

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

import destination_capability


ROOT = Path(__file__).resolve().parents[1]
INDEX_SCHEMA = ROOT / "references/schemas/compact_receipt_index.schema.json"
COMMON_SCHEMA = ROOT / "references/schemas/common_scholarly_primitives.schema.json"
COMMON_SCHEMA_ID = "https://co-author-harness.local/schemas/common_scholarly_primitives.schema.json"
COMMON_SCHEMA_SHA256 = "b5a397a4e90431c422a788414e40c1eed6ca5ba98191ed0aecaaa70aac3365e4"
INDEX_SCHEMA_ID = "https://co-author-harness.local/schemas/compact_receipt_index.schema.json"
INDEX_FIELDS = {
    "schema_version", "index_id", "source_receipt", "detail_blob", "verdict",
    "counts", "warnings", "recovery_commands", "hashes",
    "compression_measurement", "created_at",
}
DESCRIPTOR_FIELDS = {
    "schema_version", "descriptor_type", "index_id", "authority_effect",
    "created_at", "source_receipt", "top_level_keys", "fields",
}
FIELD_FIELDS = {"key", "blob"}

RC_COMMON_SCHEMA = "RC-COMMON-SCHEMA"
RC_INDEX_SCHEMA = "RC-INDEX-SCHEMA"
RC_INDEX_TAMPERED = "RC-INDEX-TAMPERED"
RC_INPUT_INVALID = "RC-INPUT-INVALID"
RC_NONCANONICAL = "RC-NONCANONICAL"
RC_PATH_ALIAS = "RC-PATH-ALIAS"
RC_DETAIL_MISSING = "RC-DETAIL-MISSING"
RC_DETAIL_UNKNOWN = "RC-DETAIL-UNKNOWN"
RC_DETAIL_TAMPERED = "RC-DETAIL-TAMPERED"
RC_ORIGINAL_MISMATCH = "RC-ORIGINAL-MISMATCH"
RC_OUTPUT_EXISTS = "RC-OUTPUT-EXISTS"
RC_ATOMIC_WRITE = "RC-ATOMIC-WRITE"

ALIASES = {
    "verdict": ("verdict", "outcome", "status", "state", "disposition"),
    "counts": ("count", "counts", "total", "totals", "metrics", "statistics"),
    "warnings": ("warning", "warnings", "alert", "alerts", "caveat", "caveats"),
    "recovery_commands": ("recovery", "remediation", "action", "actions", "command", "commands"),
    "hashes": ("hash", "hashes", "digest", "digests", "checksum", "checksums", "sha256"),
}
_WINDOWS_RESERVED = {
    "con", "prn", "aux", "nul", *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
}


class ReceiptCompactionError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _pretty(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ReceiptCompactionError(RC_INPUT_INVALID, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite(token: str) -> None:
    raise ReceiptCompactionError(RC_INPUT_INVALID, f"non-finite JSON number refused: {token}")


def _load_json_any(path: Path, code: str) -> tuple[Any, bytes]:
    try:
        raw = path.read_bytes()
        value = json.loads(
            raw.decode("utf-8", errors="strict"), object_pairs_hook=_strict_pairs,
            parse_constant=_reject_nonfinite,
        )
    except ReceiptCompactionError as exc:
        raise ReceiptCompactionError(code, str(exc)) from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReceiptCompactionError(code, f"cannot load JSON {path}: {exc}") from exc
    return value, raw


def _load_json_object(path: Path, code: str) -> tuple[dict[str, Any], bytes]:
    value, raw = _load_json_any(path, code)
    if not isinstance(value, dict):
        raise ReceiptCompactionError(code, f"JSON root must be an object: {path}")
    return value, raw


def _common_registry() -> Registry:
    common, common_raw = _load_json_object(COMMON_SCHEMA, RC_COMMON_SCHEMA)
    if common.get("$id") != COMMON_SCHEMA_ID:
        raise ReceiptCompactionError(RC_COMMON_SCHEMA, f"common schema identity must be {COMMON_SCHEMA_ID}")
    if _sha256(common_raw) != COMMON_SCHEMA_SHA256:
        raise ReceiptCompactionError(RC_COMMON_SCHEMA, f"common schema bytes must match {COMMON_SCHEMA_SHA256}")
    try:
        Draft202012Validator.check_schema(common)
        registry = Registry().with_resource(COMMON_SCHEMA_ID, Resource.from_contents(common))
        probe = Draft202012Validator(
            {"$schema": "https://json-schema.org/draft/2020-12/schema", "$ref": f"{COMMON_SCHEMA_ID}#/$defs/sha256"},
            registry=registry,
        )
        if list(probe.iter_errors("0" * 64)):
            raise ValueError("registered common sha256 probe rejected a valid digest")
        return registry
    except Exception as exc:
        raise ReceiptCompactionError(RC_COMMON_SCHEMA, f"common schema cannot be registered/resolved: {exc}") from exc


def _validate_index_schema(index: dict[str, Any]) -> None:
    schema, _ = _load_json_object(INDEX_SCHEMA, RC_INDEX_SCHEMA)
    if schema.get("$id") != INDEX_SCHEMA_ID:
        raise ReceiptCompactionError(RC_INDEX_SCHEMA, f"index schema identity must be {INDEX_SCHEMA_ID}")
    try:
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, registry=_common_registry(), format_checker=FormatChecker())
        errors = sorted(validator.iter_errors(index), key=lambda error: [str(part) for part in error.absolute_path])
    except ReceiptCompactionError:
        raise
    except Exception as exc:
        raise ReceiptCompactionError(RC_INDEX_SCHEMA, f"schema resolution failed: {exc}") from exc
    if errors:
        error = errors[0]
        location = "/".join(str(part) for part in error.absolute_path) or "<root>"
        raise ReceiptCompactionError(RC_INDEX_SCHEMA, f"schema rejection at {location}: {error.message}")


def _canonical_safe_path(value: str, code: str = RC_PATH_ALIAS) -> tuple[str, str]:
    if not isinstance(value, str) or not value:
        raise ReceiptCompactionError(code, f"path must be a nonempty string: {value!r}")
    if unicodedata.normalize("NFC", value) != value:
        raise ReceiptCompactionError(code, f"path is not Unicode NFC: {value!r}")
    if value.startswith("/") or "\\" in value or ":" in value or re.match(r"^[A-Za-z]:", value):
        raise ReceiptCompactionError(code, f"absolute, drive, backslash, or ADS path refused: {value!r}")
    if "//" in value:
        raise ReceiptCompactionError(code, f"redundant separator refused: {value!r}")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ReceiptCompactionError(code, f"dot or empty segment refused: {value!r}")
    identity_parts: list[str] = []
    for part in parts:
        if part.endswith((".", " ")):
            raise ReceiptCompactionError(code, f"Windows trailing dot/space alias refused: {value!r}")
        if part.split(".", 1)[0].casefold() in _WINDOWS_RESERVED:
            raise ReceiptCompactionError(code, f"Windows reserved-name alias refused: {value!r}")
        identity_parts.append(part.casefold())
    return value, "/".join(identity_parts)


class _PathRegistry:
    def __init__(self) -> None:
        self.identities: dict[str, str] = {}

    def add(self, value: str, *, allow_exact_repeat: bool) -> str:
        canonical, identity = _canonical_safe_path(value)
        previous = self.identities.get(identity)
        if previous is not None and (previous != canonical or not allow_exact_repeat):
            raise ReceiptCompactionError(RC_PATH_ALIAS, f"duplicate normalized path identity: {previous!r} vs {canonical!r}")
        self.identities[identity] = canonical
        return canonical


def _resolve_under(root: Path, relative: str, code: str) -> Path:
    canonical, _ = _canonical_safe_path(relative, code)
    root_resolved = root.resolve()
    candidate = (root_resolved / Path(*canonical.split("/"))).resolve(strict=False)
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise ReceiptCompactionError(code, f"path resolves outside root: {relative!r}") from exc
    return candidate


def _resolve_exact_under(root: Path, relative: str, code: str) -> Path:
    """Resolve a controlling file while refusing any symlink/reparse alias."""
    canonical, _ = _canonical_safe_path(relative, code)
    root_resolved = root.resolve()
    lexical = root_resolved / Path(*canonical.split("/"))
    resolved = _resolve_under(root_resolved, canonical, code)
    if os.path.normcase(os.path.abspath(os.fspath(lexical))) != os.path.normcase(
        os.path.abspath(os.fspath(resolved))
    ):
        raise ReceiptCompactionError(code, f"path traverses a symlink/reparse alias: {relative!r}")
    return resolved


def _binding(path: str, payload: bytes) -> dict[str, Any]:
    _canonical_safe_path(path)
    return {"path": path, "sha256": _sha256(payload), "byte_length": len(payload)}


def _pointer_escape(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _alias_tokens(key: str) -> list[str]:
    camel_split = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", unicodedata.normalize("NFKC", key))
    return [token for token in re.split(r"[^a-z0-9]+", camel_split.casefold()) if token]


def _project_facts(receipt: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    projected: dict[str, list[dict[str, Any]]] = {category: [] for category in ALIASES}

    def visit(value: Any, pointer: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_pointer = f"{pointer}/{_pointer_escape(key)}"
                tokens = _alias_tokens(key)
                for category, grammar in ALIASES.items():
                    for alias in grammar:
                        if alias in tokens:
                            projected[category].append({
                                "pointer": child_pointer,
                                "alias": alias,
                                "value": child,
                                "value_sha256": _sha256(_pretty(child)),
                            })
                visit(child, child_pointer)
        elif isinstance(value, list):
            for position, child in enumerate(value):
                visit(child, f"{pointer}/{position}")

    visit(receipt, "")
    return projected


def _validate_receipt(value: dict[str, Any], raw: bytes, path: Path) -> None:
    if not value:
        raise ReceiptCompactionError(RC_INPUT_INVALID, f"receipt object is empty: {path}")
    if any(not isinstance(key, str) or not key for key in value):
        raise ReceiptCompactionError(RC_INPUT_INVALID, f"receipt has an empty key: {path}")
    if _pretty(value) != raw:
        raise ReceiptCompactionError(RC_NONCANONICAL, f"receipt is not canonical UTF-8 JSON: {path}")


def _index_id(source_binding: dict[str, Any]) -> str:
    return "receipt-" + _sha256(_canonical(source_binding))[:24]


def _measurement(source_bytes: int, original_total: int, compact_total: int, receipt_count: int, blob_count: int) -> dict[str, Any]:
    return {
        "scope": "archive_serialized_bytes",
        "source_receipt_bytes": source_bytes,
        "archive_source_bytes": original_total,
        "archive_compact_bytes": compact_total,
        "archive_reduction_bytes": original_total - compact_total,
        "archive_reduction_ratio": round((original_total - compact_total) / original_total, 15),
        "receipt_count": receipt_count,
        "detail_blob_count": blob_count,
    }


def _build(source: Path, _source_set_id: str, created_at: str) -> tuple[dict[str, bytes], dict[str, Any]]:
    if not source.is_dir():
        raise ReceiptCompactionError(RC_INPUT_INVALID, f"source is not a directory: {source}")
    paths = sorted(path for path in source.rglob("*.json") if path.is_file())
    if not paths:
        raise ReceiptCompactionError(RC_INPUT_INVALID, "source contains no JSON receipts")
    source_registry = _PathRegistry()
    records: list[dict[str, Any]] = []
    field_blobs: dict[str, bytes] = {}
    descriptors: dict[str, bytes] = {}
    original_total = 0
    for path in paths:
        relative = path.relative_to(source).as_posix()
        source_registry.add(relative, allow_exact_repeat=False)
        receipt, raw = _load_json_object(path, RC_INPUT_INVALID)
        _validate_receipt(receipt, raw, path)
        source_binding = _binding(relative, raw)
        index_id = _index_id(source_binding)
        fields: list[dict[str, Any]] = []
        for key, value in receipt.items():
            blob_raw = _pretty(value)
            blob_path = f"blobs/{_sha256(blob_raw)}.json"
            field_blobs.setdefault(blob_path, blob_raw)
            fields.append({"key": key, "blob": _binding(blob_path, blob_raw)})
        descriptor = {
            "schema_version": "1.0.0",
            "descriptor_type": "compact_receipt_detail",
            "index_id": index_id,
            "authority_effect": "none",
            "created_at": created_at,
            "source_receipt": source_binding,
            "top_level_keys": list(receipt),
            "fields": fields,
        }
        descriptor_raw = _pretty(descriptor)
        descriptor_path = f"details/{_sha256(descriptor_raw)}.json"
        descriptors[descriptor_path] = descriptor_raw
        projections = _project_facts(receipt)
        records.append({
            "index_id": index_id,
            "source": source_binding,
            "descriptor": _binding(descriptor_path, descriptor_raw),
            "projections": projections,
            "created_at": created_at,
        })
        original_total += len(raw)
    blob_count = len(field_blobs) + len(descriptors)
    compact_guess = 1
    index_files: dict[str, bytes] = {}
    seen_guesses: set[int] = set()
    for _ in range(32):
        index_files = {}
        for record in records:
            index = {
                "schema_version": "1.0.0",
                "index_id": record["index_id"],
                "source_receipt": record["source"],
                "detail_blob": record["descriptor"],
                "verdict": record["projections"]["verdict"],
                "counts": record["projections"]["counts"],
                "warnings": record["projections"]["warnings"],
                "recovery_commands": record["projections"]["recovery_commands"],
                "hashes": record["projections"]["hashes"],
                "compression_measurement": _measurement(
                    record["source"]["byte_length"], original_total, compact_guess,
                    len(records), blob_count,
                ),
                "created_at": record["created_at"],
            }
            _validate_index_schema(index)
            index_files[f"indices/{record['index_id']}.json"] = _pretty(index)
        actual = sum(map(len, index_files.values())) + sum(map(len, descriptors.values())) + sum(map(len, field_blobs.values()))
        if actual == compact_guess:
            break
        if actual in seen_guesses:
            raise ReceiptCompactionError(RC_INPUT_INVALID, "compression measurement did not reach a byte-stable fixed point")
        seen_guesses.add(actual)
        compact_guess = actual
    else:
        raise ReceiptCompactionError(RC_INPUT_INVALID, "compression measurement fixed point exceeded iteration limit")
    files = {**index_files, **descriptors, **field_blobs}
    metrics = {
        "receipt_count": len(records),
        "detail_blob_count": blob_count,
        "field_blob_count": len(field_blobs),
        "original_bytes": original_total,
        "compact_bytes": compact_guess,
        "reduction_bytes": original_total - compact_guess,
        "reduction_ratio": round((original_total - compact_guess) / original_total, 15),
        "index_set_sha256": _sha256(_canonical([
            {"path": path, "sha256": _sha256(payload), "byte_length": len(payload)}
            for path, payload in sorted(index_files.items())
        ])),
    }
    return files, metrics


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _atomic_directory(destination: Path, writer: Callable[[Path], None], purpose: str) -> None:
    destination = destination.resolve()
    destination_capability.assert_writable(destination, purpose)
    if destination.exists():
        raise ReceiptCompactionError(RC_OUTPUT_EXISTS, f"destination already exists: {destination}")
    parent = destination.parent
    if not parent.is_dir():
        raise ReceiptCompactionError(RC_ATOMIC_WRITE, f"destination parent must already exist: {parent}")
    temporary = Path(tempfile.mkdtemp(prefix=f".{destination.name}.tmp-", dir=parent))
    try:
        destination_capability.assert_writable(temporary, purpose)
        writer(temporary)
        os.rename(temporary, destination)
    except Exception as exc:
        if temporary.exists():
            shutil.rmtree(temporary)
        if isinstance(exc, (ReceiptCompactionError, destination_capability.DestinationRefused)):
            raise
        raise ReceiptCompactionError(RC_ATOMIC_WRITE, f"atomic directory publication failed: {exc}") from exc


def compact(source: Path, destination: Path, source_set_id: str, compacted_at: str) -> dict[str, Any]:
    files, metrics = _build(source.resolve(), source_set_id, compacted_at)

    def writer(temporary: Path) -> None:
        for relative, payload in sorted(files.items()):
            _write_bytes(_resolve_under(temporary, relative, RC_PATH_ALIAS), payload)

    _atomic_directory(destination, writer, "receipt compaction")
    return metrics


def _load_bound_json(root: Path, binding: dict[str, Any], kind: str, path_registry: _PathRegistry) -> tuple[Any, bytes]:
    relative = path_registry.add(binding["path"], allow_exact_repeat=True)
    expected_prefix = f"{kind}/"
    expected_path = f"{expected_prefix}{binding['sha256']}.json"
    if relative != expected_path:
        raise ReceiptCompactionError(RC_DETAIL_UNKNOWN, f"{kind} path is not content-addressed: {relative}")
    path = _resolve_under(root, relative, RC_PATH_ALIAS)
    if not path.is_file():
        raise ReceiptCompactionError(RC_DETAIL_MISSING, f"bound {kind} blob omitted: {relative}")
    value, raw = _load_json_any(path, RC_DETAIL_TAMPERED)
    if len(raw) != binding["byte_length"] or _sha256(raw) != binding["sha256"]:
        raise ReceiptCompactionError(RC_DETAIL_TAMPERED, f"{kind} blob binding failed: {relative}")
    if raw != _pretty(value):
        raise ReceiptCompactionError(RC_DETAIL_TAMPERED, f"{kind} blob is noncanonical: {relative}")
    return value, raw


def _expected_measurements(indices: list[dict[str, Any]], compact_total: int, blob_count: int) -> list[dict[str, Any]]:
    original_total = sum(index["source_receipt"]["byte_length"] for index in indices)
    return [
        _measurement(index["source_receipt"]["byte_length"], original_total, compact_total, len(indices), blob_count)
        for index in indices
    ]


def _load_and_validate(compact_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any], list[tuple[str, bytes]]]:
    compact_root = compact_root.resolve()
    indices_dir = _resolve_exact_under(compact_root, "indices", RC_PATH_ALIAS)
    index_entries: list[tuple[str, Path]] = []
    if indices_dir.is_dir():
        for candidate in sorted(indices_dir.glob("*.json")):
            index_relative = candidate.relative_to(compact_root).as_posix()
            index_path = _resolve_exact_under(compact_root, index_relative, RC_PATH_ALIAS)
            if index_path.is_file():
                index_entries.append((index_relative, index_path))
    if not index_entries:
        raise ReceiptCompactionError(RC_DETAIL_MISSING, "archive has no per-receipt indices")
    # Preflight every restore identity before following any descriptor. This
    # makes alias collisions fail before per-index bindings can mask them.
    preflight_sources = _PathRegistry()
    for _, index_path in index_entries:
        preflight_index, preflight_raw = _load_json_object(index_path, RC_INDEX_SCHEMA)
        if preflight_raw != _pretty(preflight_index):
            raise ReceiptCompactionError(RC_INDEX_TAMPERED, f"index is noncanonical: {index_path}")
        _validate_index_schema(preflight_index)
        preflight_sources.add(preflight_index["source_receipt"]["path"], allow_exact_repeat=False)
    resource_registry = _PathRegistry()
    source_registry = _PathRegistry()
    indices: list[dict[str, Any]] = []
    index_raw_by_path: dict[str, bytes] = {}
    descriptors: dict[str, bytes] = {}
    field_blobs: dict[str, bytes] = {}
    reconstructed: list[tuple[str, bytes]] = []
    expected_files: set[str] = set()
    index_ids: set[str] = set()
    for index_relative, index_path in index_entries:
        resource_registry.add(index_relative, allow_exact_repeat=False)
        expected_files.add(index_relative)
        index, index_raw = _load_json_object(index_path, RC_INDEX_SCHEMA)
        if index_raw != _pretty(index):
            raise ReceiptCompactionError(RC_INDEX_TAMPERED, f"index is noncanonical: {index_relative}")
        _validate_index_schema(index)
        if set(index) != INDEX_FIELDS:
            raise ReceiptCompactionError(RC_INDEX_SCHEMA, "index fields differ from frozen contract")
        if index["index_id"] in index_ids or index_relative != f"indices/{index['index_id']}.json":
            raise ReceiptCompactionError(RC_INDEX_TAMPERED, "duplicate index id or filename mismatch")
        index_ids.add(index["index_id"])
        source_path = source_registry.add(index["source_receipt"]["path"], allow_exact_repeat=False)
        if index["index_id"] != _index_id(index["source_receipt"]):
            raise ReceiptCompactionError(RC_INDEX_TAMPERED, f"index id does not bind source: {index['index_id']}")
        descriptor, descriptor_raw = _load_bound_json(compact_root, index["detail_blob"], "details", resource_registry)
        descriptor_path = index["detail_blob"]["path"]
        expected_files.add(descriptor_path)
        descriptors.setdefault(descriptor_path, descriptor_raw)
        if not isinstance(descriptor, dict) or set(descriptor) != DESCRIPTOR_FIELDS:
            raise ReceiptCompactionError(RC_DETAIL_TAMPERED, f"descriptor shape changed: {descriptor_path}")
        if descriptor["schema_version"] != "1.0.0" or descriptor["descriptor_type"] != "compact_receipt_detail":
            raise ReceiptCompactionError(RC_DETAIL_TAMPERED, "descriptor identity changed")
        if descriptor["authority_effect"] != "none" or descriptor["index_id"] != index["index_id"]:
            raise ReceiptCompactionError(RC_DETAIL_TAMPERED, "descriptor authority/index binding changed")
        if descriptor["created_at"] != index["created_at"] or descriptor["source_receipt"] != index["source_receipt"]:
            raise ReceiptCompactionError(RC_DETAIL_TAMPERED, "descriptor source/time binding changed")
        keys = descriptor["top_level_keys"]
        field_keys = [field.get("key") for field in descriptor["fields"] if isinstance(field, dict)]
        if keys != field_keys or len(keys) != len(set(keys)) or any(set(field) != FIELD_FIELDS for field in descriptor["fields"]):
            raise ReceiptCompactionError(RC_DETAIL_TAMPERED, "descriptor field order/coverage changed")
        values: dict[str, Any] = {}
        for field in descriptor["fields"]:
            value, blob_raw = _load_bound_json(compact_root, field["blob"], "blobs", resource_registry)
            blob_path = field["blob"]["path"]
            expected_files.add(blob_path)
            field_blobs.setdefault(blob_path, blob_raw)
            values[field["key"]] = value
        receipt = {key: values[key] for key in keys}
        projections = _project_facts(receipt)
        for category in ALIASES:
            if index[category] != projections[category]:
                raise ReceiptCompactionError(RC_INDEX_TAMPERED, f"{category} projection changed or omitted: {index['index_id']}")
        receipt_raw = _pretty(receipt)
        source = index["source_receipt"]
        if len(receipt_raw) != source["byte_length"] or _sha256(receipt_raw) != source["sha256"]:
            raise ReceiptCompactionError(RC_ORIGINAL_MISMATCH, f"source reconstruction binding failed: {source_path}")
        reconstructed.append((source_path, receipt_raw))
        indices.append(index)
        index_raw_by_path[index_relative] = index_raw
    actual_files = {
        path.relative_to(compact_root).as_posix()
        for path in compact_root.rglob("*") if path.is_file()
    }
    unknown = sorted(actual_files - expected_files)
    missing = sorted(expected_files - actual_files)
    if missing:
        raise ReceiptCompactionError(RC_DETAIL_MISSING, f"archive files omitted: {missing}")
    if unknown:
        raise ReceiptCompactionError(RC_DETAIL_UNKNOWN, f"unreferenced archive files: {unknown}")
    compact_total = sum(path.stat().st_size for path in compact_root.rglob("*") if path.is_file())
    blob_count = len(descriptors) + len(field_blobs)
    expected_measurements = _expected_measurements(indices, compact_total, blob_count)
    for index, expected in zip(indices, expected_measurements):
        if index["compression_measurement"] != expected:
            raise ReceiptCompactionError(RC_INDEX_TAMPERED, f"compression measurement changed: {index['index_id']}")
    original_total = sum(index["source_receipt"]["byte_length"] for index in indices)
    metrics = {
        "receipt_count": len(indices),
        "detail_blob_count": blob_count,
        "field_blob_count": len(field_blobs),
        "original_bytes": original_total,
        "compact_bytes": compact_total,
        "reduction_bytes": original_total - compact_total,
        "reduction_ratio": round((original_total - compact_total) / original_total, 15),
        "index_set_sha256": _sha256(_canonical([
            {"path": path, "sha256": _sha256(raw), "byte_length": len(raw)}
            for path, raw in sorted(index_raw_by_path.items())
        ])),
    }
    return indices, metrics, reconstructed


def validate(compact_root: Path) -> dict[str, Any]:
    _, metrics, _ = _load_and_validate(compact_root)
    return metrics


def restore(compact_root: Path, destination: Path) -> dict[str, Any]:
    _, _, reconstructed = _load_and_validate(compact_root)
    planned: list[tuple[str, Path, bytes]] = []
    physical: dict[str, str] = {}
    destination_resolved = destination.resolve()
    for relative, payload in sorted(reconstructed):
        target = _resolve_under(destination_resolved, relative, RC_PATH_ALIAS)
        identity = os.path.normcase(os.path.realpath(os.fspath(target)))
        previous = physical.get(identity)
        if previous is not None:
            raise ReceiptCompactionError(RC_PATH_ALIAS, f"restore destination collision: {previous!r} vs {relative!r}")
        physical[identity] = relative
        planned.append((relative, target, payload))

    def writer(temporary: Path) -> None:
        for relative, _, payload in planned:
            _write_bytes(_resolve_under(temporary, relative, RC_PATH_ALIAS), payload)

    _atomic_directory(destination, writer, "receipt reconstruction")
    return {"receipt_count": len(planned), "restored_bytes": sum(len(payload) for _, _, payload in planned)}


def _assert_unique_paths(paths: Iterable[str]) -> None:
    registry = _PathRegistry()
    for path in paths:
        registry.add(path, allow_exact_repeat=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    compact_parser = subparsers.add_parser("compact")
    compact_parser.add_argument("--source", type=Path, required=True)
    compact_parser.add_argument("--output", type=Path, required=True)
    compact_parser.add_argument("--source-set-id", required=True)
    compact_parser.add_argument("--compacted-at", required=True)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--compact-root", type=Path, required=True)
    restore_parser = subparsers.add_parser("restore")
    restore_parser.add_argument("--compact-root", type=Path, required=True)
    restore_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "compact":
            result = compact(args.source, args.output, args.source_set_id, args.compacted_at)
        elif args.command == "validate":
            result = validate(args.compact_root)
        else:
            result = restore(args.compact_root, args.output)
        print(json.dumps({"status": "PASS", **result}, sort_keys=True))
        return 0
    except (ReceiptCompactionError, destination_capability.DestinationRefused) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
