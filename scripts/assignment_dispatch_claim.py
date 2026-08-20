#!/usr/bin/env python3
"""C4 assignment-dispatch claim issuance and replay validation."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from referencing.exceptions import Unresolvable

from destination_capability import guard_project_root
from assignment_receipt_transaction import (
    ReceiptTransactionError,
    _assignment_root,
    _atomic_json,
    _issue_dispatch_kernel_authorization,
    _json_bytes,
    _load_record,
    _target_snapshot,
    _transaction_claim,
    load_mutation_ledger,
    state_path,
)


ROOT = Path(__file__).resolve().parents[1]
CLAIM_SCHEMA = ROOT / "references" / "schemas" / "assignment_dispatch_claim.schema.json"
CONSUMPTION_SCHEMA = (
    ROOT / "references" / "schemas" / "assignment_dispatch_consumption.schema.json"
)
HOST_SCHEMA = ROOT / "references" / "schemas" / "assignment_host_attestation.schema.json"
ISSUANCE_SCHEMA = (
    ROOT / "references" / "schemas" / "assignment_dispatch_issuance.schema.json"
)
COMMON_SCHEMA = (
    ROOT / "references" / "schemas" / "common_scholarly_primitives.schema.json"
)
COMMON_SCHEMA_ID = (
    "https://co-author-harness.local/schemas/"
    "common_scholarly_primitives.schema.json"
)
COMMON_SCHEMA_SHA256 = (
    "b5a397a4e90431c422a788414e40c1eed6ca5ba98191ed0aecaaa70aac3365e4"
)
KERNEL_AUTHORIZATION_SCHEMA = (
    ROOT
    / "references"
    / "schemas"
    / "assignment_dispatch_kernel_authorization.schema.json"
)
KERNEL_NAME = "assignment_transaction_kernel"
KERNEL_VERSION = "1.0.0"
PRODUCTION_HOST_ADAPTERS: dict[str, Any] = {}
SYNTHETIC_ADAPTER_IDENTITY = {
    "name": "c4_fixture_governance",
    "tool": "deterministic_fixture_adapter",
    "version": "1.0.0",
}


def _canonical_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest_path(path: Path) -> str:
    return _digest_bytes(path.read_bytes())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _validator(
    path: Path,
    code: str = "APG-DISPATCH-CLAIM-INVALID",
    *,
    common_schema_path: Path = COMMON_SCHEMA,
) -> Draft202012Validator:
    """Build a validator with the exact frozen common primitive resource."""

    try:
        schema_raw = path.read_bytes()
        common_raw = common_schema_path.read_bytes()
        schema = json.loads(schema_raw.decode("utf-8", errors="strict"))
        common = json.loads(common_raw.decode("utf-8", errors="strict"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReceiptTransactionError(
            code, f"dispatch schema resource is unavailable or invalid: {exc}"
        ) from exc
    if not isinstance(schema, dict) or not isinstance(common, dict):
        raise ReceiptTransactionError(
            code, "dispatch schema resources must be JSON objects"
        )
    if common.get("$id") != COMMON_SCHEMA_ID:
        raise ReceiptTransactionError(
            code, "common scholarly primitive schema has the wrong canonical $id"
        )
    if _digest_bytes(common_raw) != COMMON_SCHEMA_SHA256:
        raise ReceiptTransactionError(
            code,
            "common scholarly primitive schema hash differs from the frozen resource",
        )
    try:
        Draft202012Validator.check_schema(common)
        Draft202012Validator.check_schema(schema)
        registry = Registry().with_resource(
            COMMON_SCHEMA_ID, Resource.from_contents(common)
        )
        return Draft202012Validator(
            schema,
            registry=registry,
            format_checker=FormatChecker(),
        )
    except Exception as exc:
        raise ReceiptTransactionError(
            code, f"dispatch schema resource cannot be registered: {exc}"
        ) from exc


def _validate_schema(
    payload: dict[str, Any],
    schema: Path,
    code: str,
    *,
    common_schema_path: Path = COMMON_SCHEMA,
) -> None:
    validator = _validator(
        schema,
        code,
        common_schema_path=common_schema_path,
    )
    try:
        errors = sorted(
            validator.iter_errors(payload), key=lambda error: list(error.path)
        )
    except Unresolvable as exc:
        raise ReceiptTransactionError(
            code, f"dispatch schema reference is unresolved: {exc}"
        ) from exc
    if errors:
        raise ReceiptTransactionError(code, errors[0].message)


def _project_root_binding(project: Path) -> dict[str, Any]:
    manifest = project / "project_manifest.json"
    if not manifest.is_file():
        raise ReceiptTransactionError(
            "APG-DISPATCH-CLAIM-INVALID", "synthetic project manifest is missing"
        )
    value = _load_record(manifest, "APG-DISPATCH-CLAIM-INVALID")
    identity = value.get("identity")
    if not isinstance(identity, str) or not identity:
        raise ReceiptTransactionError(
            "APG-DISPATCH-CLAIM-INVALID", "project manifest identity is missing"
        )
    return {
        "kind": "project",
        "identity": identity,
        "discovery": "explicit:project_manifest.json",
        "manifest_sha256": _digest_path(manifest),
    }


def _identity_manifest() -> Path:
    general = ROOT / "version.json"
    if general.is_file():
        return general
    host = ROOT / "plugin.json"
    if host.is_file():
        return host
    return ROOT / ".claude-plugin" / "plugin.json"


def _harness_root_binding() -> dict[str, Any]:
    manifest = _identity_manifest()
    value = _load_record(manifest, "APG-DISPATCH-CLAIM-INVALID")
    rel = manifest.relative_to(ROOT).as_posix()
    return {
        "kind": "harness",
        "identity": value["name"],
        "discovery": f"explicit:{rel}",
        "manifest_sha256": _digest_path(manifest),
    }


def binding(project: Path, path: Path, evidence_type: str) -> dict[str, Any]:
    project = project.resolve()
    path = path.resolve()
    try:
        relative = path.relative_to(project).as_posix()
        root = _project_root_binding(project)
    except ValueError:
        relative = path.relative_to(ROOT).as_posix()
        root = _harness_root_binding()
    return {
        "root": root,
        "path": relative,
        "sha256": _digest_path(path),
        "evidence_type": evidence_type,
    }


def binding_from_digest(
    project: Path,
    path: Path,
    digest: str,
    evidence_type: str,
) -> dict[str, Any]:
    """Build a project binding for bytes published later at a canonical path."""
    project = project.resolve()
    path = path.resolve()
    return {
        "root": _project_root_binding(project),
        "path": path.relative_to(project).as_posix(),
        "sha256": digest,
        "evidence_type": evidence_type,
    }


def _resolve_binding(
    project: Path,
    value: dict[str, Any],
    *,
    code: str,
    expected_path: Path | None = None,
) -> Path:
    root = value.get("root")
    if root == _project_root_binding(project):
        base = project
    elif root == _harness_root_binding():
        base = ROOT
    else:
        raise ReceiptTransactionError(code, "binding root does not match a live manifest")
    raw = value.get("path")
    if not isinstance(raw, str):
        raise ReceiptTransactionError(code, "binding path is missing")
    path = (base / Path(raw)).resolve()
    try:
        path.relative_to(base.resolve())
    except ValueError as exc:
        raise ReceiptTransactionError(code, "binding path escapes its root") from exc
    if expected_path is not None and path != expected_path.resolve():
        raise ReceiptTransactionError(code, "binding path differs from the expected object")
    if not path.is_file() or _digest_path(path) != value.get("sha256"):
        raise ReceiptTransactionError(code, "binding bytes do not match the live object")
    return path


def _load_published(
    project: Path,
    object_path: Path | None,
    *,
    schema: Path,
    missing_code: str,
    invalid_code: str,
    uncommitted_code: str,
) -> dict[str, Any]:
    if object_path is None:
        raise ReceiptTransactionError(missing_code, "required object is absent")
    object_path = object_path.resolve()
    value = _load_record(object_path, invalid_code)
    _validate_schema(value, schema, invalid_code)
    manifest_path = object_path.parent / "publication_manifest.json"
    marker_path = object_path.parent / "commit_marker.json"
    if not manifest_path.is_file() or not marker_path.is_file():
        raise ReceiptTransactionError(uncommitted_code, "publication marker is absent")
    manifest = _load_record(manifest_path, uncommitted_code)
    marker = _load_record(marker_path, uncommitted_code)
    expected_relative = object_path.relative_to(project).as_posix()
    products = manifest.get("products")
    if (
        not isinstance(products, list)
        or len(products) != 1
        or products[0].get("path") != expected_relative
        or products[0].get("sha256") != _digest_path(object_path)
        or marker.get("state") != "committed"
        or marker.get("publication_manifest")
        != manifest_path.relative_to(project).as_posix()
        or marker.get("publication_manifest_sha256") != _digest_path(manifest_path)
    ):
        raise ReceiptTransactionError(uncommitted_code, "publication bindings are incomplete")
    return value


def _issuance_root(project: Path) -> Path:
    return _assignment_root(project) / "dispatch" / "issuance"


def _issuance_row_hash(row: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in row.items() if key != "row_sha256"}
    return _digest_bytes(_canonical_bytes(unsigned))


def _issuance_line_bytes(row: dict[str, Any]) -> bytes:
    return _canonical_bytes(row) + b"\n"


def _issuance_marker_path(project: Path, row: dict[str, Any]) -> Path:
    return (
        _issuance_root(project)
        / "markers"
        / f"{row['sequence']:08d}-{row['row_sha256'][:16]}"
        / "commit_marker.json"
    )


def _validate_kernel_authorization(
    project: Path,
    row: dict[str, Any],
    claim_path: Path,
    claim: dict[str, Any],
) -> None:
    """Require the exact kernel-owned fact behind one issuance row."""
    authorization_id = row["authorization_id"]
    authorization_path = (
        _assignment_root(project)
        / "dispatch"
        / "kernel_authorizations"
        / authorization_id
        / "authorization.json"
    )
    _resolve_binding(
        project,
        row["kernel_authorization"],
        code="APG-DISPATCH-CLAIM-AUTHORITY",
        expected_path=authorization_path,
    )
    authorization = _load_record(
        authorization_path, "APG-DISPATCH-CLAIM-AUTHORITY"
    )
    _validate_schema(
        authorization,
        KERNEL_AUTHORIZATION_SCHEMA,
        "APG-DISPATCH-CLAIM-AUTHORITY",
    )
    manifest_path = claim_path.parent / "publication_manifest.json"
    marker_path = claim_path.parent / "commit_marker.json"
    expected_claim = {
        "path": claim_path.relative_to(project).as_posix(),
        "sha256": _digest_path(claim_path),
        "claim_id": claim["claim_id"],
        "claim_kind": claim["claim_kind"],
    }
    expected_publication = {
        "manifest_path": manifest_path.relative_to(project).as_posix(),
        "manifest_sha256": _digest_path(manifest_path),
        "commit_marker_path": marker_path.relative_to(project).as_posix(),
        "commit_marker_sha256": _digest_path(marker_path),
    }
    expected_kernel = {
        "name": KERNEL_NAME,
        "version": KERNEL_VERSION,
        "transaction_id": claim["issuer"]["transaction_id"],
    }
    reservation_path = (
        _assignment_root(project)
        / "reservations"
        / f"{claim['receipt_id']}.json"
    )
    reservation = _load_record(
        reservation_path, "APG-DISPATCH-CLAIM-AUTHORITY"
    )
    transition = authorization["reservation_transition"]
    receipt_path = Path(claim["assignment_receipt"]["path"])
    ledger_path = (
        _assignment_root(project) / "ledger" / f"{receipt_path.name}.jsonl"
    )
    if (
        authorization["authorization_id"] != authorization_id
        or authorization["claim"] != expected_claim
        or authorization["publication"] != expected_publication
        or authorization["kernel"] != expected_kernel
        or transition["reservation_path"]
        != reservation_path.relative_to(project).as_posix()
        or transition["reservation_sha256"] != _digest_path(reservation_path)
        or transition["receipt_id"] != claim["receipt_id"]
        or transition["reservation_id"] != claim["reservation_id"]
        or transition["target_milestone"] != claim["target_milestone"]
        or transition["receipt_sha256"] != reservation.get("receipt_sha256")
        or transition["receipt_ledger_path"]
        != ledger_path.relative_to(project).as_posix()
        or transition["event"]
        != {
            "state": "reserved",
            "receipt_id": claim["receipt_id"],
            "reservation_id": claim["reservation_id"],
        }
    ):
        raise ReceiptTransactionError(
            "APG-DISPATCH-CLAIM-AUTHORITY",
            "kernel authorization does not bind the exact claim transition",
        )
    try:
        ledger_raw = ledger_path.read_bytes()
        lines = ledger_raw.splitlines(keepends=True)
        sequence = transition["sequence"]
        if sequence > len(lines):
            raise ValueError("transition sequence is beyond the live ledger")
        prefix = b"".join(lines[:sequence])
        event = json.loads(lines[sequence - 1].decode("utf-8", errors="strict"))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, IndexError) as exc:
        raise ReceiptTransactionError(
            "APG-DISPATCH-CLAIM-AUTHORITY",
            "kernel authorization reservation transition is unreadable",
        ) from exc
    if (
        event != transition["event"]
        or lines[sequence - 1]
        != json.dumps(event, sort_keys=True).encode("utf-8") + b"\n"
        or _digest_bytes(prefix) != transition["ledger_prefix_sha256"]
    ):
        raise ReceiptTransactionError(
            "APG-DISPATCH-CLAIM-AUTHORITY",
            "kernel authorization reservation transition bytes differ",
        )


def _load_issuance_ledger(project: Path) -> list[dict[str, Any]]:
    """Validate the canonical issuance chain, every prefix marker, and head."""
    project = project.resolve()
    root = _issuance_root(project)
    ledger = root / "ledger.jsonl"
    marker_root = root / "markers"
    if not ledger.is_file():
        extras = list(marker_root.glob("*/commit_marker.json")) if marker_root.is_dir() else []
        if extras:
            raise ReceiptTransactionError(
                "APG-DISPATCH-CLAIM-AUTHORITY",
                "issuance markers exist without an issuance ledger",
            )
        return []
    raw = ledger.read_bytes()
    if not raw or not raw.endswith(b"\n") or b"\r" in raw:
        raise ReceiptTransactionError(
            "APG-DISPATCH-CLAIM-AUTHORITY",
            "issuance ledger is not canonical newline-delimited JSON",
        )
    raw_lines = raw.splitlines(keepends=True)
    rows: list[dict[str, Any]] = []
    expected_markers: set[Path] = set()
    prefix = b""
    prior: str | None = None
    seen_claim_ids: set[str] = set()
    for sequence, line in enumerate(raw_lines, 1):
        try:
            row = json.loads(line.decode("utf-8", errors="strict"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ReceiptTransactionError(
                "APG-DISPATCH-CLAIM-AUTHORITY",
                "issuance ledger row is not valid UTF-8 JSON",
            ) from exc
        if not isinstance(row, dict) or line != _issuance_line_bytes(row):
            raise ReceiptTransactionError(
                "APG-DISPATCH-CLAIM-AUTHORITY",
                "issuance ledger row is not canonical",
            )
        _validate_schema(
            row, ISSUANCE_SCHEMA, "APG-DISPATCH-CLAIM-AUTHORITY"
        )
        expected_hash = _issuance_row_hash(row)
        if (
            row["sequence"] != sequence
            or row["prior_row_sha256"] != prior
            or row["row_sha256"] != expected_hash
            or row["claim_sha256"] != row["claim"]["sha256"]
            or row["claim_id"] in seen_claim_ids
        ):
            raise ReceiptTransactionError(
                "APG-DISPATCH-CLAIM-AUTHORITY",
                "issuance ledger sequence, chain, row hash, or uniqueness is invalid",
            )
        claim_path = (
            _assignment_root(project)
            / "dispatch"
            / "claims"
            / row["claim_id"]
            / "claim.json"
        )
        manifest_path = claim_path.parent / "publication_manifest.json"
        commit_marker_path = claim_path.parent / "commit_marker.json"
        _resolve_binding(
            project,
            row["claim"],
            code="APG-DISPATCH-CLAIM-AUTHORITY",
            expected_path=claim_path,
        )
        _resolve_binding(
            project,
            row["publication_manifest"],
            code="APG-DISPATCH-CLAIM-AUTHORITY",
            expected_path=manifest_path,
        )
        _resolve_binding(
            project,
            row["commit_marker"],
            code="APG-DISPATCH-CLAIM-AUTHORITY",
            expected_path=commit_marker_path,
        )
        claim = _load_record(claim_path, "APG-DISPATCH-CLAIM-AUTHORITY")
        if (
            claim.get("claim_id") != row["claim_id"]
            or claim.get("claim_kind") != row["claim_kind"]
            or claim.get("receipt_id") != row["receipt_id"]
            or claim.get("reservation_id") != row["reservation_id"]
            or claim.get("issuer") != row["issuer"]
            or claim.get("issued_at") != row["issued_at"]
        ):
            raise ReceiptTransactionError(
                "APG-DISPATCH-CLAIM-AUTHORITY",
                "issuance row does not bind the exact claim authority fields",
            )
        _validate_kernel_authorization(project, row, claim_path, claim)
        prefix += line
        marker_path = _issuance_marker_path(project, row)
        expected_markers.add(marker_path.resolve())
        if not marker_path.is_file():
            raise ReceiptTransactionError(
                "APG-DISPATCH-CLAIM-AUTHORITY",
                "issuance prefix has no marker-last commit record",
            )
        marker = _load_record(marker_path, "APG-DISPATCH-CLAIM-AUTHORITY")
        expected_marker = {
            "schema_version": "1.0.0",
            "marker_type": "assignment_dispatch_issuance",
            "state": "committed",
            "sequence": sequence,
            "row_count": sequence,
            "prior_head_row_sha256": prior,
            "head_row_sha256": row["row_sha256"],
            "ledger_path": ledger.relative_to(project).as_posix(),
            "ledger_prefix_sha256": _digest_bytes(prefix),
            "transaction_id": row["issuer"]["transaction_id"],
        }
        if marker != expected_marker:
            raise ReceiptTransactionError(
                "APG-DISPATCH-CLAIM-AUTHORITY",
                "issuance prefix/head marker is stale or malformed",
            )
        seen_claim_ids.add(row["claim_id"])
        prior = row["row_sha256"]
        rows.append(row)
    actual_markers = {
        path.resolve() for path in marker_root.glob("*/commit_marker.json")
    } if marker_root.is_dir() else set()
    if actual_markers != expected_markers:
        raise ReceiptTransactionError(
            "APG-DISPATCH-CLAIM-AUTHORITY",
            "issuance marker inventory differs from the ledger prefixes",
        )
    return rows


def _append_issuance_row(
    project: Path,
    claim: dict[str, Any],
    claim_path: Path,
    authorization_path: Path,
) -> dict[str, Any]:
    """Append one claim issuance and publish its prefix marker last."""
    rows = _load_issuance_ledger(project)
    manifest_path = claim_path.parent / "publication_manifest.json"
    commit_marker_path = claim_path.parent / "commit_marker.json"
    authorization = _load_record(
        authorization_path, "APG-DISPATCH-CLAIM-AUTHORITY"
    )
    _validate_schema(
        authorization,
        KERNEL_AUTHORIZATION_SCHEMA,
        "APG-DISPATCH-CLAIM-AUTHORITY",
    )
    row: dict[str, Any] = {
        "schema_version": "1.0.0",
        "issuance_type": "assignment_dispatch_claim",
        "sequence": len(rows) + 1,
        "prior_row_sha256": rows[-1]["row_sha256"] if rows else None,
        "claim": binding(project, claim_path, "assignment_dispatch_claim"),
        "claim_id": claim["claim_id"],
        "claim_sha256": _digest_path(claim_path),
        "claim_kind": claim["claim_kind"],
        "receipt_id": claim["receipt_id"],
        "reservation_id": claim["reservation_id"],
        "issuer": claim["issuer"],
        "issued_at": claim["issued_at"],
        "publication_manifest": binding(
            project, manifest_path, "assignment_dispatch_claim_manifest"
        ),
        "commit_marker": binding(
            project, commit_marker_path, "assignment_dispatch_claim_marker"
        ),
        "kernel_authorization": binding(
            project,
            authorization_path,
            "assignment_dispatch_kernel_authorization",
        ),
        "authorization_id": authorization["authorization_id"],
    }
    row["row_sha256"] = _issuance_row_hash(row)
    _validate_schema(row, ISSUANCE_SCHEMA, "APG-DISPATCH-CLAIM-AUTHORITY")
    root = _issuance_root(project)
    root.mkdir(parents=True, exist_ok=True)
    ledger = root / "ledger.jsonl"
    line = _issuance_line_bytes(row)
    with ledger.open("ab") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())
    marker_path = _issuance_marker_path(project, row)
    marker_path.parent.mkdir(parents=True, exist_ok=False)
    prefix = ledger.read_bytes()
    marker = {
        "schema_version": "1.0.0",
        "marker_type": "assignment_dispatch_issuance",
        "state": "committed",
        "sequence": row["sequence"],
        "row_count": row["sequence"],
        "prior_head_row_sha256": row["prior_row_sha256"],
        "head_row_sha256": row["row_sha256"],
        "ledger_path": ledger.relative_to(project).as_posix(),
        "ledger_prefix_sha256": _digest_bytes(prefix),
        "transaction_id": row["issuer"]["transaction_id"],
    }
    _atomic_json(marker_path, marker, exclusive=True)
    validated = _load_issuance_ledger(project)
    if validated[-1] != row:
        raise ReceiptTransactionError(
            "APG-DISPATCH-CLAIM-AUTHORITY",
            "issuance ledger did not commit the exact appended row",
        )
    return row


def _validate_issuance_authority(
    project: Path,
    claim_path: Path,
    claim: dict[str, Any],
) -> None:
    rows = _load_issuance_ledger(project)
    exact = [
        row for row in rows
        if row["claim_id"] == claim["claim_id"]
        and row["claim_sha256"] == _digest_path(claim_path)
        and row["claim_kind"] == claim["claim_kind"]
        and row["receipt_id"] == claim["receipt_id"]
        and row["reservation_id"] == claim["reservation_id"]
        and row["issuer"] == claim["issuer"]
    ]
    if len(exact) != 1:
        raise ReceiptTransactionError(
            "APG-DISPATCH-CLAIM-AUTHORITY",
            "claim has no unique exact kernel issuance ledger row",
        )


def _validate_claim_publication(project: Path, claim_path: Path | None) -> dict[str, Any]:
    claim = _load_published(
        project,
        claim_path,
        schema=CLAIM_SCHEMA,
        missing_code="APG-DISPATCH-CLAIM-MISSING",
        invalid_code="APG-DISPATCH-CLAIM-INVALID",
        uncommitted_code="APG-DISPATCH-CLAIM-UNCOMMITTED",
    )
    marker = _load_record(claim_path.resolve().parent / "commit_marker.json")
    issuer = claim["issuer"]
    unsigned = {key: value for key, value in claim.items() if key != "claim_id"}
    expected_claim_id = "dispatch-" + _digest_bytes(_canonical_bytes(unsigned))[:16]
    expected_lane = (
        _assignment_root(project)
        / "dispatch"
        / "claims"
        / expected_claim_id
        / "claim.json"
    ).resolve()
    allowed_issuer_transactions = (
        {
            f"assignment-reserve-{claim.get('target_milestone')}",
            f"assignment-recovery-{claim.get('target_milestone')}",
        }
        if claim.get("claim_kind") == "generation"
        else {f"assignment-evaluation-{claim.get('target_milestone')}"}
    )
    if (
        issuer.get("name") != KERNEL_NAME
        or issuer.get("version") != KERNEL_VERSION
        or issuer.get("transaction_id") not in allowed_issuer_transactions
        or marker.get("transaction_id") != issuer.get("transaction_id")
        or claim.get("claim_id") != expected_claim_id
        or claim_path.resolve() != expected_lane
    ):
        raise ReceiptTransactionError(
            "APG-DISPATCH-CLAIM-AUTHORITY", "claim issuer is not the issuing transaction"
        )
    reservation_path = _resolve_binding(
        project, claim["reservation"], code="APG-DISPATCH-CLAIM-AUTHORITY"
    )
    expected_reservation_path = (
        _assignment_root(project) / "reservations" / f"{claim['receipt_id']}.json"
    ).resolve()
    reservation = _load_record(
        reservation_path, "APG-DISPATCH-CLAIM-AUTHORITY"
    )
    if (
        reservation_path != expected_reservation_path
        or reservation.get("receipt_id") != claim.get("receipt_id")
        or reservation.get("reservation_id") != claim.get("reservation_id")
        or reservation.get("target_milestone") != claim.get("target_milestone")
        or reservation.get("writes") != claim.get("authorized_writes")
    ):
        raise ReceiptTransactionError(
            "APG-DISPATCH-CLAIM-AUTHORITY",
            "claim is not bound to the live kernel reservation transition",
        )
    _validate_issuance_authority(project, claim_path.resolve(), claim)
    return claim


def _committed_consumption(project: Path, path: Path) -> dict[str, Any]:
    return _load_published(
        project,
        path,
        schema=CONSUMPTION_SCHEMA,
        missing_code="APG-DISPATCH-CLAIM-GENERATION-MISMATCH",
        invalid_code="APG-DISPATCH-CLAIM-GENERATION-MISMATCH",
        uncommitted_code="APG-DISPATCH-CLAIM-GENERATION-MISMATCH",
    )


def _publish_record(
    project: Path,
    lane: Path,
    object_name: str,
    payload: dict[str, Any],
    transaction_id: str,
    *,
    stop_before_marker: bool = False,
    resume_incomplete: bool = False,
) -> tuple[Path, Path, Path]:
    """Publish object, manifest, then marker. Caller holds assignment lock."""
    object_path = lane / object_name
    manifest_path = lane / "publication_manifest.json"
    marker_path = lane / "commit_marker.json"
    manifest = {
        "schema_version": "1.0.0",
        "transaction_id": transaction_id,
        "products": [{
            "path": object_path.relative_to(project).as_posix(),
            "sha256": _digest_bytes(_json_bytes(payload)),
        }],
    }
    if resume_incomplete and object_path.is_file() and manifest_path.is_file() and not marker_path.is_file():
        if _load_record(object_path, "APG-DISPATCH-CLAIM-RECOVERY-REQUIRED") != payload:
            raise ReceiptTransactionError(
                "APG-DISPATCH-CLAIM-RECOVERY-REQUIRED",
                "partial publication object differs from the requested transaction",
            )
        if _load_record(manifest_path, "APG-DISPATCH-CLAIM-RECOVERY-REQUIRED") != manifest:
            raise ReceiptTransactionError(
                "APG-DISPATCH-CLAIM-RECOVERY-REQUIRED",
                "partial publication manifest differs from the requested transaction",
            )
    else:
        _atomic_json(object_path, payload, exclusive=True)
        manifest["products"][0]["sha256"] = _digest_path(object_path)
        _atomic_json(manifest_path, manifest, exclusive=True)
    if stop_before_marker:
        return object_path, manifest_path, marker_path
    marker = {
        "schema_version": "1.0.0",
        "transaction_id": transaction_id,
        "publication_manifest": manifest_path.relative_to(project).as_posix(),
        "publication_manifest_sha256": _digest_path(manifest_path),
        "state": "committed",
    }
    _atomic_json(marker_path, marker, exclusive=True)
    return object_path, manifest_path, marker_path


def issue_generation_claim(
    project: Path,
    reserved_receipt: Path,
    *,
    policy_path: Path,
    bibliography_snapshot: Path,
    nonce: str,
    issuer_transaction_id: str,
    issued_at: str | None = None,
) -> tuple[dict[str, Any], Path, Path]:
    """Issue one genuine generation control through the assignment kernel."""
    project = project.resolve()
    guard_project_root(project)
    reserved_receipt = reserved_receipt.resolve()
    with _transaction_claim(project):
        receipt = _load_record(reserved_receipt, "APG-DISPATCH-CLAIM-INVALID")
        allowed_issuer_transactions = {
            f"assignment-reserve-{receipt['target_milestone']}",
            f"assignment-recovery-{receipt['target_milestone']}",
        }
        if issuer_transaction_id not in allowed_issuer_transactions:
            raise ReceiptTransactionError(
                "APG-DISPATCH-CLAIM-AUTHORITY",
                "generation issuer transaction is not kernel-derived",
            )
        reservation_path = (
            _assignment_root(project) / "reservations" / f"{receipt['receipt_id']}.json"
        )
        reservation = _load_record(reservation_path, "APG-DISPATCH-CLAIM-INVALID")
        writes = reservation.get("writes")
        if not isinstance(writes, list) or not writes:
            raise ReceiptTransactionError(
                "APG-DISPATCH-CLAIM-INVALID", "reservation has no authorized writes"
            )
        target_path = str(receipt["primary_deliverable_path"])
        unsigned: dict[str, Any] = {
            "schema_version": "1.0.0",
            "claim_type": "assignment_dispatch",
            "claim_kind": "generation",
            "state": "issued",
            "role": "generator",
            "issued_at": issued_at or _now(),
            "nonce": nonce,
            "issuer": {
                "name": KERNEL_NAME,
                "version": KERNEL_VERSION,
                "transaction_id": issuer_transaction_id,
            },
            "assignment_receipt": binding_from_digest(
                project,
                state_path(project, reserved_receipt.name, "consumed"),
                _digest_path(reserved_receipt),
                "assignment_gate_receipt",
            ),
            "receipt_id": receipt["receipt_id"],
            "reservation": binding(
                project, reservation_path, "assignment_receipt_reservation"
            ),
            "reservation_id": receipt["reservation_id"],
            "target_milestone": receipt["target_milestone"],
            "target_path": target_path,
            "authorized_writes": writes,
            "policy": binding(project, policy_path, "assignment_policy"),
            "canonical_bibliography_snapshot": binding(
                project, bibliography_snapshot, "canonical_bibliography_snapshot"
            ),
            "corpus_digest": _digest_path(bibliography_snapshot),
        }
        claims_root = _assignment_root(project) / "dispatch" / "claims"
        for existing in claims_root.glob("*/claim.json"):
            prior = _load_record(existing, "APG-DISPATCH-CLAIM-INVALID")
            if (
                prior.get("claim_kind") == "generation"
                and prior.get("role") == "generator"
                and prior.get("nonce") == nonce
                and prior.get("issuer", {}).get("transaction_id")
                == issuer_transaction_id
            ):
                raise ReceiptTransactionError(
                    "APG-DISPATCH-CLAIM-DUPLICATE",
                    "logical generation dispatch has already been issued",
                )
        claim_id = f"dispatch-{_digest_bytes(_canonical_bytes(unsigned))[:16]}"
        claim = {**unsigned, "claim_id": claim_id}
        _validate_schema(claim, CLAIM_SCHEMA, "APG-DISPATCH-CLAIM-INVALID")
        lane = _assignment_root(project) / "dispatch" / "claims" / claim_id
        claim_path, _, marker_path = _publish_record(
            project, lane, "claim.json", claim, issuer_transaction_id
        )
        _, authorization_path = _issue_dispatch_kernel_authorization(
            project, claim_path
        )
        _append_issuance_row(project, claim, claim_path, authorization_path)
    return claim, claim_path, marker_path


def accept_claim_for_context(
    project: Path,
    claim_path: Path | None,
    *,
    expected_role: str,
    expected_target: str,
    expected_receipt_id: str,
    expected_preimages: list[dict[str, Any]] | None = None,
    expected_policy_sha256: str | None = None,
    expected_corpus_digest: str | None = None,
    expected_artifact_sha256: str | None = None,
    expected_generation_transaction_id: str | None = None,
) -> dict[str, Any]:
    """Validate one committed claim against its exact dispatch context."""
    project = project.resolve()
    claim = _validate_claim_publication(project, claim_path)
    if claim.get("role") != expected_role:
        raise ReceiptTransactionError(
            "APG-DISPATCH-CLAIM-ROLE-MISMATCH", "claim role differs from context"
        )
    if claim.get("target_path") != expected_target:
        raise ReceiptTransactionError(
            "APG-DISPATCH-CLAIM-TARGET-MISMATCH", "claim target differs from context"
        )
    if claim.get("receipt_id") != expected_receipt_id:
        raise ReceiptTransactionError(
            "APG-DISPATCH-CLAIM-RECEIPT-MISMATCH", "claim receipt differs from context"
        )
    if expected_preimages is not None and claim.get("authorized_writes") != expected_preimages:
        raise ReceiptTransactionError(
            "APG-DISPATCH-CLAIM-PREIMAGE-MISMATCH", "claim preimages differ from context"
        )
    if expected_policy_sha256 is not None and claim["policy"].get("sha256") != expected_policy_sha256:
        raise ReceiptTransactionError(
            "APG-DISPATCH-CLAIM-POLICY-MISMATCH", "claim policy differs from context"
        )
    if expected_corpus_digest is not None and claim.get("corpus_digest") != expected_corpus_digest:
        raise ReceiptTransactionError(
            "APG-DISPATCH-CLAIM-CORPUS-MISMATCH", "claim corpus differs from context"
        )
    if expected_artifact_sha256 is not None and claim.get("artifact", {}).get("sha256") != expected_artifact_sha256:
        raise ReceiptTransactionError(
            "APG-DISPATCH-CLAIM-ARTIFACT-MISMATCH", "claim artifact differs from context"
        )
    if (
        expected_generation_transaction_id is not None
        and claim.get("generation_verifier", {}).get("transaction_id")
        != expected_generation_transaction_id
    ):
        raise ReceiptTransactionError(
            "APG-DISPATCH-CLAIM-GENERATION-MISMATCH",
            "claim generation transaction differs from context",
        )
    return claim


def validate_consumed_claim_for_context(
    project: Path,
    claim_path: Path,
    consumption_path: Path,
    *,
    expected_role: str,
    expected_target: str,
    expected_receipt_id: str,
    expected_artifact_sha256: str,
    expected_generation_transaction_id: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate one committed claim and its one-time artifact consumption."""
    project = project.resolve()
    claim = accept_claim_for_context(
        project,
        claim_path,
        expected_role=expected_role,
        expected_target=expected_target,
        expected_receipt_id=expected_receipt_id,
        expected_artifact_sha256=(
            expected_artifact_sha256 if expected_role == "evaluator" else None
        ),
        expected_generation_transaction_id=expected_generation_transaction_id,
    )
    consumption = _load_published(
        project,
        consumption_path,
        schema=CONSUMPTION_SCHEMA,
        missing_code="APG-DISPATCH-CLAIM-MISSING",
        invalid_code="APG-DISPATCH-CLAIM-INVALID",
        uncommitted_code="APG-DISPATCH-CLAIM-UNCOMMITTED",
    )
    _resolve_binding(
        project,
        consumption["claim"],
        code="APG-DISPATCH-CLAIM-RECEIPT-MISMATCH",
        expected_path=claim_path,
    )
    postimages = consumption.get("postimages", [])
    expected_postimage = next(
        (row for row in postimages if row.get("path") == expected_target), None
    )
    if (
        consumption.get("claim_id") != claim.get("claim_id")
        or consumption.get("role") != expected_role
        or not isinstance(expected_postimage, dict)
        or expected_postimage.get("sha256") != expected_artifact_sha256
    ):
        raise ReceiptTransactionError(
            "APG-DISPATCH-CLAIM-ARTIFACT-MISMATCH",
            "claim consumption does not bind the exact governed artifact",
        )
    return claim, consumption


def validate_generation_for_evaluation(
    project: Path,
    *,
    generation_claim_path: Path,
    generation_consumption: Path | None,
    artifact: Path,
    generation_transaction: Path,
    generation_publication_manifest: Path,
    generation_commit_marker: Path,
    generation_semantic_receipt: Path,
    wiki_root: Path,
    semantics_manifest: Path,
) -> dict[str, Any]:
    """Validate committed generation evidence before evaluation issuance."""
    project = project.resolve()
    generation_claim = _validate_claim_publication(project, generation_claim_path)
    if generation_claim.get("claim_kind") != "generation":
        raise ReceiptTransactionError(
            "APG-DISPATCH-CLAIM-GENERATION-MISMATCH", "source claim is not generation"
        )
    if generation_consumption is None:
        raise ReceiptTransactionError(
            "APG-DISPATCH-CLAIM-GENERATION-MISMATCH", "generation consumption is absent"
        )
    consumption = _committed_consumption(project, generation_consumption)
    if consumption.get("claim_id") != generation_claim.get("claim_id"):
        raise ReceiptTransactionError(
            "APG-DISPATCH-CLAIM-GENERATION-MISMATCH", "consumption binds another claim"
        )
    try:
        _resolve_binding(
            project,
            consumption["claim"],
            code="APG-DISPATCH-CLAIM-GENERATION-MISMATCH",
            expected_path=generation_claim_path,
        )
        from draft_evidence_verifier import VerifierError, validate_verifier_transaction

        marker_value = _load_record(
            generation_commit_marker, "APG-DISPATCH-CLAIM-UNCOMMITTED"
        )
        if marker_value.get("state") != "committed":
            raise ReceiptTransactionError(
                "APG-DISPATCH-CLAIM-UNCOMMITTED",
                "generation verifier publication is not committed",
            )
        transaction = validate_verifier_transaction(
            transaction=generation_transaction,
            publication_manifest=generation_publication_manifest,
            commit_marker=generation_commit_marker,
            artifact=artifact,
            semantic_receipt=generation_semantic_receipt,
            project_root=project,
            wiki_root=wiki_root,
            harness_root=ROOT,
            semantics_manifest=semantics_manifest,
        )
    except (ReceiptTransactionError, KeyError):
        raise
    except VerifierError as exc:
        raise ReceiptTransactionError(
            "APG-DISPATCH-CLAIM-GENERATION-MISMATCH", str(exc)
        ) from exc
    value = _load_record(generation_transaction, "APG-DISPATCH-CLAIM-GENERATION-MISMATCH")
    if value.get("phase") != "generation" or value.get("product_disposition") != "evaluation_ready":
        raise ReceiptTransactionError(
            "APG-DISPATCH-CLAIM-GENERATION-MISMATCH",
            "verifier transaction is not evaluation-ready generation evidence",
        )
    return value


def issue_evaluation_claim(
    project: Path,
    generation_claim_path: Path,
    *,
    generation_consumption: Path | None,
    artifact: Path,
    generation_transaction: Path,
    generation_publication_manifest: Path,
    generation_commit_marker: Path,
    generation_semantic_receipt: Path,
    wiki_root: Path,
    semantics_manifest: Path,
    nonce: str,
    issuer_transaction_id: str,
    issued_at: str | None = None,
) -> tuple[dict[str, Any], Path, Path]:
    """Issue the activation evaluation control from a generation claim."""
    project = project.resolve()
    guard_project_root(project)
    generation_claim_path = generation_claim_path.resolve()
    artifact = artifact.resolve()
    with _transaction_claim(project):
        generation_claim = _load_record(
            generation_claim_path, "APG-DISPATCH-CLAIM-INVALID"
        )
        expected_issuer_transaction = (
            f"assignment-evaluation-{generation_claim['target_milestone']}"
        )
        if issuer_transaction_id != expected_issuer_transaction:
            raise ReceiptTransactionError(
                "APG-DISPATCH-CLAIM-AUTHORITY",
                "evaluation issuer transaction is not kernel-derived",
            )
        transaction = validate_generation_for_evaluation(
            project,
            generation_claim_path=generation_claim_path,
            generation_consumption=generation_consumption,
            artifact=artifact,
            generation_transaction=generation_transaction,
            generation_publication_manifest=generation_publication_manifest,
            generation_commit_marker=generation_commit_marker,
            generation_semantic_receipt=generation_semantic_receipt,
            wiki_root=wiki_root,
            semantics_manifest=semantics_manifest,
        )
        if generation_consumption is None:
            consumption_binding = binding_from_digest(
                project,
                _assignment_root(project)
                / "dispatch"
                / "consumptions"
                / "absent"
                / "consumption.json",
                "0" * 64,
                "assignment_dispatch_consumption",
            )
        else:
            consumption_binding = binding(
                project,
                generation_consumption,
                "assignment_dispatch_consumption",
            )
        unsigned: dict[str, Any] = {
            "schema_version": "1.0.0",
            "claim_type": "assignment_dispatch",
            "claim_kind": "evaluation",
            "state": "issued",
            "role": "evaluator",
            "issued_at": issued_at or _now(),
            "nonce": nonce,
            "issuer": {
                "name": KERNEL_NAME,
                "version": KERNEL_VERSION,
                "transaction_id": issuer_transaction_id,
            },
            "assignment_receipt": generation_claim["assignment_receipt"],
            "receipt_id": generation_claim["receipt_id"],
            "reservation": generation_claim["reservation"],
            "reservation_id": generation_claim["reservation_id"],
            "target_milestone": generation_claim["target_milestone"],
            "target_path": generation_claim["target_path"],
            "authorized_writes": generation_claim["authorized_writes"],
            "policy": generation_claim["policy"],
            "canonical_bibliography_snapshot": generation_claim[
                "canonical_bibliography_snapshot"
            ],
            "corpus_digest": generation_claim["corpus_digest"],
            "generation_claim": binding(
                project, generation_claim_path, "assignment_generation_claim"
            ),
            "generation_consumption": consumption_binding,
            "artifact": binding(project, artifact, "governed_artifact"),
            "generation_verifier": {
                "transaction_id": transaction["transaction_id"],
                "transaction": binding(
                    project, generation_transaction, "verifier_transaction"
                ),
                "publication_manifest": binding(
                    project,
                    generation_publication_manifest,
                    "verifier_publication_manifest",
                ),
                "commit_marker": binding(
                    project, generation_commit_marker, "verifier_commit_marker"
                ),
                "product_disposition": "evaluation_ready",
            },
        }
        claim_id = f"dispatch-{_digest_bytes(_canonical_bytes(unsigned))[:16]}"
        claim = {**unsigned, "claim_id": claim_id}
        _validate_schema(claim, CLAIM_SCHEMA, "APG-DISPATCH-CLAIM-INVALID")
        lane = _assignment_root(project) / "dispatch" / "claims" / claim_id
        claim_path, _, marker_path = _publish_record(
            project, lane, "claim.json", claim, issuer_transaction_id
        )
        _, authorization_path = _issue_dispatch_kernel_authorization(
            project, claim_path
        )
        _append_issuance_row(project, claim, claim_path, authorization_path)
    return claim, claim_path, marker_path


def accept_host_pair_for_independence(
    project: Path,
    generation_attestation_path: Path | None,
    evaluation_attestation_path: Path | None,
    *,
    requested_level: str,
    expected_generation_claim_id: str,
    expected_evaluation_claim_id: str,
    _test_only_adapter: Any | None = None,
) -> str:
    """Validate a trusted, distinct host-use pair or report unavailable evidence."""
    project = project.resolve()
    if requested_level != "host_attested_independence":
        return "dispatch_separation"
    if generation_attestation_path is None or evaluation_attestation_path is None:
        raise ReceiptTransactionError(
            "INDEPENDENCE_UNVERIFIED", "trusted host evidence is unavailable"
        )
    generation = _load_published(
        project,
        generation_attestation_path,
        schema=HOST_SCHEMA,
        missing_code="HOST-ATTESTATION-INVALID",
        invalid_code="HOST-ATTESTATION-INVALID",
        uncommitted_code="HOST-ATTESTATION-INVALID",
    )
    evaluation = _load_published(
        project,
        evaluation_attestation_path,
        schema=HOST_SCHEMA,
        missing_code="HOST-ATTESTATION-INVALID",
        invalid_code="HOST-ATTESTATION-INVALID",
        uncommitted_code="HOST-ATTESTATION-INVALID",
    )
    issuer_key = (
        generation.get("issuer", {}).get("name"),
        generation.get("issuer", {}).get("tool"),
        generation.get("issuer", {}).get("version"),
    )
    adapter = PRODUCTION_HOST_ADAPTERS.get("|".join(str(item) for item in issuer_key))
    if _test_only_adapter is not None:
        manifest = _load_record(
            project / "project_manifest.json", "HOST-ATTESTATION-INVALID"
        )
        supplied_identity = {
            "name": getattr(_test_only_adapter, "issuer", None),
            "tool": getattr(_test_only_adapter, "tool", None),
            "version": getattr(_test_only_adapter, "version", None),
        }
        if (
            (
                (
                    manifest.get("synthetic_fixture") == "c4"
                    and manifest.get("production_authority") is False
                )
                or manifest.get("fixture_id") == "assurance-provenance-c2-activation"
            )
            and supplied_identity == SYNTHETIC_ADAPTER_IDENTITY
        ):
            adapter = _test_only_adapter
    if adapter is None:
        raise ReceiptTransactionError(
            "INDEPENDENCE_UNVERIFIED", "no production host adapter is allowlisted"
        )
    expected_issuer = SYNTHETIC_ADAPTER_IDENTITY
    for value in (generation, evaluation):
        if value.get("issuer") != expected_issuer:
            raise ReceiptTransactionError(
                "HOST-ATTESTATION-ISSUER-UNTRUSTED", "host issuer is not allowlisted"
            )
        unsigned = {key: item for key, item in value.items() if key != "authenticator"}
        if not adapter.verify(unsigned, value["authenticator"]["digest"]):
            raise ReceiptTransactionError(
                "HOST-ATTESTATION-INVALID", "host authenticator does not verify"
            )
    if generation.get("role") != "generator" or evaluation.get("role") != "evaluator":
        raise ReceiptTransactionError(
            "HOST-ATTESTATION-BINDING-MISMATCH", "host roles do not match the pair"
        )
    if (
        generation.get("host_task_id") == evaluation.get("host_task_id")
        or generation.get("host_session_id") == evaluation.get("host_session_id")
        or generation.get("nonce") == evaluation.get("nonce")
        or generation.get("target") != evaluation.get("target")
        or generation.get("artifact", {}).get("sha256")
        != evaluation.get("artifact", {}).get("sha256")
    ):
        raise ReceiptTransactionError(
            "HOST-ATTESTATION-BINDING-MISMATCH", "host pair is not distinctly bound"
        )
    for value, path, expected_claim in (
        (generation, generation_attestation_path, expected_generation_claim_id),
        (evaluation, evaluation_attestation_path, expected_evaluation_claim_id),
    ):
        claim_path = _resolve_binding(
            project, value["dispatch_claim"], code="HOST-ATTESTATION-BINDING-MISMATCH"
        )
        claim = _validate_claim_publication(project, claim_path)
        if claim.get("claim_id") != expected_claim:
            raise ReceiptTransactionError(
                "HOST-ATTESTATION-BINDING-MISMATCH", "host claim binding differs"
            )
        _resolve_binding(
            project, value["artifact"], code="HOST-ATTESTATION-BINDING-MISMATCH"
        )
    generation_claim = _validate_claim_publication(
        project,
        _resolve_binding(
            project,
            generation["dispatch_claim"],
            code="HOST-ATTESTATION-BINDING-MISMATCH",
        ),
    )
    evaluation_claim = _validate_claim_publication(
        project,
        _resolve_binding(
            project,
            evaluation["dispatch_claim"],
            code="HOST-ATTESTATION-BINDING-MISMATCH",
        ),
    )
    expected_verifier = evaluation_claim.get("generation_verifier", {}).get("transaction")
    supplied_verifier = evaluation.get("generation_verifier")
    if expected_verifier is None or supplied_verifier is None or supplied_verifier != expected_verifier:
        raise ReceiptTransactionError(
            "HOST-ATTESTATION-BINDING-MISMATCH", "generation verifier binding differs"
        )
    _resolve_binding(
        project, supplied_verifier, code="HOST-ATTESTATION-BINDING-MISMATCH"
    )
    generation_hash = _digest_path(generation_attestation_path)
    evaluation_hash = _digest_path(evaluation_attestation_path)
    payload = {
        "schema_version": "1.0.0",
        "use_type": "synthetic_host_pair",
        "state": "consumed",
        "generation_attestation": binding(
            project, generation_attestation_path, "assignment_host_attestation"
        ),
        "evaluation_attestation": binding(
            project, evaluation_attestation_path, "assignment_host_attestation"
        ),
        "generation_claim_id": expected_generation_claim_id,
        "evaluation_claim_id": expected_evaluation_claim_id,
        "transaction_id": "host-pair-acceptance",
    }
    use_id = "host-use-" + _digest_bytes(_canonical_bytes(payload))[:16]
    lane = _assignment_root(project) / "dispatch" / "host-uses" / use_id
    guard_project_root(project)
    with _transaction_claim(project):
        if (
            _digest_path(generation_attestation_path) != generation_hash
            or _digest_path(evaluation_attestation_path) != evaluation_hash
        ):
            raise ReceiptTransactionError(
                "HOST-ATTESTATION-BINDING-MISMATCH", "host evidence changed under claim"
            )
        if (lane / "use.json").is_file():
            raise ReceiptTransactionError(
                "HOST-ATTESTATION-REPLAY", "host pair has already been used"
            )
        _publish_record(
            project, lane, "use.json", payload, "host-pair-acceptance"
        )
    return "host_attested_independence"


def _consume_claim_locked(
    project: Path,
    claim_path: Path,
    *,
    role: str,
    consumer_transaction_id: str,
    postimages: list[dict[str, Any]],
    mutation_row_hashes: list[str],
    consumed_at: str | None = None,
    stop_before_marker: bool = False,
    resume_incomplete: bool = False,
) -> tuple[dict[str, Any], Path, Path]:
    claim = _load_record(claim_path, "APG-DISPATCH-CLAIM-INVALID")
    consumed_at = consumed_at or _now()
    nonce = _digest_bytes(
        f"{claim.get('claim_id')}:{consumer_transaction_id}:{consumed_at}".encode("utf-8")
    )[:32]
    unsigned = {
        "schema_version": "1.0.0",
        "consumption_type": "assignment_dispatch",
        "state": "consumed",
        "claim": binding(project, claim_path, "assignment_dispatch_claim"),
        "claim_id": claim["claim_id"],
        "role": role,
        "consumer_transaction_id": consumer_transaction_id,
        "postimages": postimages,
        "mutation_row_hashes": mutation_row_hashes,
        "mutation_head": mutation_row_hashes[-1],
        "consumed_at": consumed_at,
        "nonce": nonce,
    }
    consumption_id = f"consume-{_digest_bytes(_canonical_bytes(unsigned))[:16]}"
    consumption = {**unsigned, "consumption_id": consumption_id}
    _validate_schema(
        consumption, CONSUMPTION_SCHEMA, "APG-DISPATCH-CLAIM-INVALID"
    )
    lane = _assignment_root(project) / "dispatch" / "consumptions" / consumption_id
    consumption_path, _, marker_path = _publish_record(
        project,
        lane,
        "consumption.json",
        consumption,
        consumer_transaction_id,
        stop_before_marker=stop_before_marker,
        resume_incomplete=resume_incomplete,
    )
    return consumption, consumption_path, marker_path


def consume_dispatch_claim(
    project: Path,
    claim_path: Path,
    *,
    role: str,
    consumer_transaction_id: str,
    target_paths: list[str],
    consumed_at: str | None = None,
    stop_before_marker: bool = False,
    resume_incomplete: bool = False,
) -> tuple[dict[str, Any], Path, Path]:
    """Consume one dispatch claim under the assignment transaction claim."""
    project = project.resolve()
    guard_project_root(project)
    with _transaction_claim(project):
        claim = _validate_claim_publication(project, claim_path)
        if claim.get("role") != role:
            raise ReceiptTransactionError(
                "APG-DISPATCH-CLAIM-ROLE-MISMATCH", "consumer role differs from claim"
            )
        rows = load_mutation_ledger(project)
        row_by_target = {row["target_path"]: row for row in rows}
        postimages: list[dict[str, Any]] = []
        row_hashes: list[str] = []
        for target_path in target_paths:
            row = row_by_target[target_path]
            snapshot = _target_snapshot(project / Path(target_path))
            postimages.append({
                "path": target_path,
                "sha256": snapshot["sha256"],
                "size": snapshot["size"],
            })
            row_hashes.append(row["row_sha256"])
        consumptions = _assignment_root(project) / "dispatch" / "consumptions"
        partial: Path | None = None
        for existing in consumptions.glob("*/consumption.json"):
            prior = _load_record(existing, "APG-DISPATCH-CLAIM-RECOVERY-REQUIRED")
            if prior.get("claim_id") != claim.get("claim_id"):
                continue
            marker = existing.parent / "commit_marker.json"
            if marker.is_file():
                raise ReceiptTransactionError(
                    "APG-DISPATCH-CLAIM-REPLAY", "dispatch claim is already consumed"
                )
            partial = existing
            break
        if partial is not None and not resume_incomplete:
            raise ReceiptTransactionError(
                "APG-DISPATCH-CLAIM-RECOVERY-REQUIRED",
                "dispatch consumption publication is incomplete",
            )
        return _consume_claim_locked(
            project,
            claim_path,
            role=role,
            consumer_transaction_id=consumer_transaction_id,
            postimages=postimages,
            mutation_row_hashes=row_hashes,
            consumed_at=consumed_at,
            stop_before_marker=stop_before_marker,
            resume_incomplete=resume_incomplete,
        )
