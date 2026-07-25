#!/usr/bin/env python3
"""C4 mutation genesis/legacy-anchor activation seam.

The schema-valid controls are real assignment-kernel publications.  The
context, prefix, head, authenticator, and replay checks are intentionally
absent until the activation red is independently reviewed.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from destination_capability import guard_project_root
from assignment_dispatch_claim import (
    _load_published,
    _publish_record,
    _resolve_binding,
    binding,
)
from assignment_receipt_transaction import (
    ReceiptTransactionError,
    _assignment_root,
    _load_record,
    _target_snapshot,
    _transaction_claim,
    load_mutation_ledger,
)


ROOT = Path(__file__).resolve().parents[1]
GENESIS_SCHEMA = ROOT / "references" / "schemas" / "assignment_mutation_genesis.schema.json"
ANCHOR_SCHEMA = ROOT / "references" / "schemas" / "assignment_mutation_anchor.schema.json"
STATE_SCHEMA = ROOT / "references" / "schemas" / "assignment_mutation_state.schema.json"
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()


def _canonical_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest_path(path: Path) -> str:
    return _digest_bytes(path.read_bytes())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _validator(path: Path) -> Draft202012Validator:
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _validate(payload: dict[str, Any], schema_path: Path, code: str) -> None:
    errors = sorted(
        _validator(schema_path).iter_errors(payload), key=lambda error: list(error.path)
    )
    if errors:
        raise ReceiptTransactionError(code, errors[0].message)


def _project_root(project: Path) -> dict[str, Any]:
    manifest = project / "project_manifest.json"
    if not manifest.is_file():
        raise ReceiptTransactionError(
            "APG-MUTATION-ANCHOR-INVALID", "synthetic project manifest is missing"
        )
    value = _load_record(manifest, "APG-MUTATION-ANCHOR-INVALID")
    identity = value.get("identity")
    if not isinstance(identity, str) or not identity:
        raise ReceiptTransactionError(
            "APG-MUTATION-ANCHOR-INVALID", "project manifest identity is missing"
        )
    return {
        "kind": "project",
        "identity": identity,
        "discovery": "explicit:project_manifest.json",
        "manifest_sha256": _digest_path(manifest),
    }


def _target_rows(project: Path, target_paths: list[str]) -> list[dict[str, Any]]:
    return [
        {"path": target, "snapshot": _target_snapshot(project / Path(target))}
        for target in target_paths
    ]


def _state_payload(
    project: Path,
    *,
    authority_kind: str,
    authority_path: Path,
    authority_type: str,
) -> dict[str, Any]:
    ledger_path = _assignment_root(project) / "mutation_ledger.jsonl"
    ledger_bytes = ledger_path.read_bytes() if ledger_path.is_file() else b""
    rows = load_mutation_ledger(project)
    head = rows[-1]["row_sha256"] if rows else None
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        latest[row["target_path"]] = row
    targets = [
        {
            "path": path,
            "sha256": row["postimage"]["sha256"],
            "size": row["postimage"]["size"],
        }
        for path, row in sorted(latest.items())
        if row["postimage"]["sha256"] is not None
    ]
    return {
        "schema_version": "1.0.0",
        "state_type": "assignment_mutation_authority",
        "authority_kind": authority_kind,
        "authority": binding(project, authority_path, authority_type),
        "accepted_prefix": {
            "row_count": len(rows),
            "prefix_sha256": _digest_bytes(ledger_bytes),
            "head": head,
        },
        "live_head": {
            "row_count": len(rows),
            "ledger_sha256": _digest_bytes(ledger_bytes),
            "head": head,
            "targets": targets,
        },
    }


def issue_genesis(
    project: Path,
    *,
    initial_target_paths: list[str],
    policy_sha256: str,
    corpus_digest: str,
    issuer_transaction_id: str,
    nonce: str,
    issued_at: str | None = None,
) -> tuple[dict[str, Any], Path, Path, Path]:
    """Issue a schema-valid fresh-project genesis and authority state."""
    project = project.resolve()
    guard_project_root(project)
    ledger_path = _assignment_root(project) / "mutation_ledger.jsonl"
    with _transaction_claim(project):
        if ledger_path.is_file() and ledger_path.read_bytes():
            raise ReceiptTransactionError(
                "APG-MUTATION-ANCHOR-INVALID", "fresh genesis requires a zero-row ledger"
            )
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        ledger_path.touch(exist_ok=True)
        unsigned = {
            "schema_version": "1.0.0",
            "genesis_type": "assignment_mutation",
            "state": "committed",
            "project": _project_root(project),
            "ledger_path": ledger_path.relative_to(project).as_posix(),
            "row_count": 0,
            "head": None,
            "initial_targets": _target_rows(project, initial_target_paths),
            "policy_sha256": policy_sha256,
            "corpus_digest": corpus_digest,
            "issuer_transaction_id": issuer_transaction_id,
            "issued_at": issued_at or _now(),
            "nonce": nonce,
        }
        genesis_id = f"genesis-{_digest_bytes(_canonical_bytes(unsigned))[:16]}"
        genesis = {**unsigned, "genesis_id": genesis_id}
        _validate(genesis, GENESIS_SCHEMA, "APG-MUTATION-ANCHOR-INVALID")
        lane = _assignment_root(project) / "mutation" / "genesis" / genesis_id
        genesis_path, _, genesis_marker = _publish_record(
            project, lane, "genesis.json", genesis, issuer_transaction_id
        )
        state = _state_payload(
            project,
            authority_kind="genesis",
            authority_path=genesis_path,
            authority_type="assignment_mutation_genesis",
        )
        _validate(state, STATE_SCHEMA, "APG-MUTATION-ANCHOR-INVALID")
        state_lane = _assignment_root(project) / "mutation" / "states" / genesis_id
        state_path, _, _ = _publish_record(
            project, state_lane, "state.json", state, issuer_transaction_id
        )
    return genesis, genesis_path, genesis_marker, state_path


def inspect_legacy_anchor(
    project: Path,
    anchor_path: Path | None,
    *,
    fixture_adapter: Any,
) -> dict[str, Any]:
    """Validate a committed, externally authenticated legacy anchor."""
    project = project.resolve()
    anchor = _load_published(
        project,
        anchor_path,
        schema=ANCHOR_SCHEMA,
        missing_code="APG-MUTATION-ANCHOR-MISSING",
        invalid_code="APG-MUTATION-ANCHOR-INVALID",
        uncommitted_code="APG-MUTATION-ANCHOR-INVALID",
    )
    expected_adapter = {
        "issuer": fixture_adapter.issuer,
        "tool": fixture_adapter.tool,
        "version": fixture_adapter.version,
        "authorization_id": "synthetic-c4-anchor",
    }
    if anchor.get("adapter") != expected_adapter:
        raise ReceiptTransactionError(
            "APG-MUTATION-ANCHOR-UNAUTHORIZED", "anchor issuer is not authorized"
        )
    unsigned = {key: value for key, value in anchor.items() if key != "authenticator"}
    if not fixture_adapter.verify(unsigned, anchor["authenticator"]["digest"]):
        raise ReceiptTransactionError(
            "APG-MUTATION-ANCHOR-UNAUTHORIZED", "anchor authenticator does not verify"
        )
    if anchor.get("historical_provenance_asserted") is not False:
        raise ReceiptTransactionError(
            "APG-MUTATION-LEGACY-PROVENANCE-OVERCLAIM",
            "legacy anchor may not assert historical provenance",
        )
    try:
        if anchor.get("project") != _project_root(project):
            raise ReceiptTransactionError(
                "APG-MUTATION-ANCHOR-INVALID", "anchor project binding is stale"
            )
        ledger_binding = anchor["ledger"]
        if ledger_binding.get("root") != _project_root(project):
            raise ReceiptTransactionError(
                "APG-MUTATION-ANCHOR-INVALID", "anchor ledger root is stale"
            )
        ledger_path = (project / Path(ledger_binding["path"])).resolve()
        if ledger_path != (_assignment_root(project) / "mutation_ledger.jsonl").resolve():
            raise ReceiptTransactionError(
                "APG-MUTATION-ANCHOR-INVALID", "anchor ledger path is stale"
            )
        rows = load_mutation_ledger(project)
        count = anchor["row_count"]
        raw_lines = ledger_path.read_bytes().splitlines(keepends=True)
        prefix = b"".join(raw_lines[:count])
        if (
            len(rows) < count
            or anchor.get("head") != (rows[count - 1]["row_sha256"] if count else None)
            or ledger_binding.get("sha256") != _digest_bytes(prefix)
        ):
            raise ReceiptTransactionError(
                "APG-MUTATION-ANCHOR-INVALID", "anchor ledger binding is stale"
            )
        _resolve_binding(
            project,
            anchor["authorization"]["evidence"],
            code="APG-MUTATION-ANCHOR-INVALID",
        )
        for row in anchor["live_targets"]:
            if _target_snapshot(project / Path(row["path"])) != row["snapshot"]:
                raise ReceiptTransactionError(
                    "APG-MUTATION-ANCHOR-INVALID", "anchor target snapshot is stale"
                )
    except (KeyError, TypeError) as exc:
        raise ReceiptTransactionError(
            "APG-MUTATION-ANCHOR-INVALID", "anchor bindings are malformed"
        ) from exc
    return anchor


def activate_legacy_anchor(
    project: Path,
    anchor_path: Path,
    *,
    fixture_adapter: Any,
    transaction_id: str,
) -> tuple[dict[str, Any], Path]:
    """Activate an external anchor only when a fixture adapter is injected."""
    project = project.resolve()
    guard_project_root(project)
    with _transaction_claim(project):
        states = _assignment_root(project) / "mutation" / "states"
        anchor_relative = anchor_path.resolve().relative_to(project).as_posix()
        for existing in states.glob("*/state.json"):
            prior = _load_record(existing, "APG-MUTATION-ANCHOR-UNAUTHORIZED")
            if (
                prior.get("authority_kind") == "legacy_anchor"
                and prior.get("authority", {}).get("path") == anchor_relative
                and prior.get("authority", {}).get("sha256") == _digest_path(anchor_path)
            ):
                raise ReceiptTransactionError(
                    "APG-MUTATION-ANCHOR-UNAUTHORIZED", "legacy anchor is already active"
                )
        anchor = inspect_legacy_anchor(
            project, anchor_path, fixture_adapter=fixture_adapter
        )
        state = _state_payload(
            project,
            authority_kind="legacy_anchor",
            authority_path=anchor_path,
            authority_type="assignment_mutation_legacy_anchor",
        )
        _validate(state, STATE_SCHEMA, "APG-MUTATION-ANCHOR-INVALID")
        lane = _assignment_root(project) / "mutation" / "states" / transaction_id
        state_path, _, _ = _publish_record(
            project, lane, "state.json", state, transaction_id
        )
    return state, state_path


def validate_accepted_prefix(project: Path, state_path: Path) -> dict[str, Any]:
    """Validate the exact accepted ledger prefix while allowing later appends."""
    project = project.resolve()
    try:
        state = _load_published(
            project,
            state_path,
            schema=STATE_SCHEMA,
            missing_code="APG-MUTATION-PREFIX-MISMATCH",
            invalid_code="APG-MUTATION-PREFIX-MISMATCH",
            uncommitted_code="APG-MUTATION-PREFIX-MISMATCH",
        )
        rows = load_mutation_ledger(project)
        expected = state["accepted_prefix"]
        count = expected["row_count"]
        if len(rows) < count:
            raise ValueError("ledger shorter than accepted prefix")
        raw_lines = (_assignment_root(project) / "mutation_ledger.jsonl").read_bytes().splitlines(
            keepends=True
        )
        prefix_bytes = b"".join(raw_lines[:count])
        head = rows[count - 1]["row_sha256"] if count else None
        if (
            _digest_bytes(prefix_bytes) != expected["prefix_sha256"]
            or head != expected["head"]
        ):
            raise ValueError("accepted prefix bytes or head differ")
    except (ReceiptTransactionError, KeyError, OSError, TypeError, ValueError) as exc:
        if isinstance(exc, ReceiptTransactionError) and exc.code == "APG-MUTATION-PREFIX-MISMATCH":
            raise
        raise ReceiptTransactionError(
            "APG-MUTATION-PREFIX-MISMATCH", "accepted mutation prefix differs"
        ) from exc
    return state


def validate_live_head(project: Path, state_path: Path) -> dict[str, Any]:
    """Validate the current ledger head, targets, and completed append state."""
    project = project.resolve()
    assignment_root = _assignment_root(project)
    for journal_path in (assignment_root / "journal").glob("*.json"):
        journal = _load_record(journal_path, "APG-MUTATION-RECOVERY-REQUIRED")
        append = journal.get("mutation_append")
        if not isinstance(append, dict) or append.get("state") != "ledger_appended":
            continue
        marker = (
            assignment_root
            / "mutation"
            / "append"
            / str(journal.get("receipt_id"))
            / "commit_marker.json"
        )
        if marker.is_file():
            continue
        try:
            ledger = assignment_root / "mutation_ledger.jsonl"
            rows = load_mutation_ledger(project)
            consistent = (
                append.get("ledger_sha256") == _digest_path(ledger)
                and append.get("prospective_row_count") == len(rows)
                and append.get("prospective_head")
                == (rows[-1]["row_sha256"] if rows else None)
                and append.get("prospective_rows")
                == rows[append.get("prior_row_count", 0) :]
                and all(
                    _target_snapshot(project / Path(row["path"]))["sha256"]
                    == row["sha256"]
                    for row in append.get("targets", [])
                )
            )
        except (ReceiptTransactionError, KeyError, OSError, TypeError):
            consistent = False
        code = (
            "APG-MUTATION-APPEND-INCOMPLETE"
            if consistent
            else "APG-MUTATION-RECOVERY-REQUIRED"
        )
        raise ReceiptTransactionError(code, "mutation append lacks its completion marker")
    try:
        state = _load_published(
            project,
            state_path,
            schema=STATE_SCHEMA,
            missing_code="APG-MUTATION-HEAD-STALE",
            invalid_code="APG-MUTATION-HEAD-STALE",
            uncommitted_code="APG-MUTATION-HEAD-STALE",
        )
        rows = load_mutation_ledger(project)
        raw = (assignment_root / "mutation_ledger.jsonl").read_bytes()
        expected = state["live_head"]
        if (
            expected["row_count"] != len(rows)
            or expected["ledger_sha256"] != _digest_bytes(raw)
            or expected["head"] != (rows[-1]["row_sha256"] if rows else None)
            or any(
                _target_snapshot(project / Path(row["path"]))
                != {"exists": True, "sha256": row["sha256"], "size": row["size"]}
                for row in expected["targets"]
            )
        ):
            raise ValueError("live mutation head differs")
    except (ReceiptTransactionError, KeyError, OSError, TypeError, ValueError) as exc:
        if isinstance(exc, ReceiptTransactionError) and exc.code == "APG-MUTATION-HEAD-STALE":
            raise
        raise ReceiptTransactionError(
            "APG-MUTATION-HEAD-STALE", "live mutation head differs"
        ) from exc
    return state
