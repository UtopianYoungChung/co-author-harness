#!/usr/bin/env python3
"""Synthetic-only fixtures for the uncommitted C4 activation boundary."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
ANCHOR_SCHEMA = ROOT / "references" / "schemas" / "assignment_mutation_anchor.schema.json"
HOST_SCHEMA = ROOT / "references" / "schemas" / "assignment_host_attestation.schema.json"
FIXTURE_KEY = b"co-author-harness-c4-synthetic-fixture-key"


def canonical_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture_manifest(project: Path) -> Path:
    path = project / "project_manifest.json"
    path.write_text(
        json.dumps({
            "identity": "c4-synthetic-project",
            "synthetic_fixture": "c4",
            "production_authority": False,
        }, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return path


def exact_tree_state(root: Path) -> list[tuple[str, str, bytes | str]]:
    """Snapshot exact bytes and link/reparse targets without following them."""
    rows: list[tuple[str, str, bytes | str]] = []

    def visit(directory: Path) -> None:
        with os.scandir(directory) as entries:
            ordered = sorted(entries, key=lambda entry: entry.name)
        for entry in ordered:
            path = Path(entry.path)
            relative = path.relative_to(root).as_posix()
            is_junction = bool(
                getattr(entry, "is_junction", lambda: False)()
            )
            if entry.is_symlink() or is_junction:
                rows.append((relative, "link", os.readlink(path)))
            elif entry.is_file(follow_symlinks=False):
                rows.append((relative, "file", path.read_bytes()))
            elif entry.is_dir(follow_symlinks=False):
                rows.append((relative, "dir", b""))
                visit(path)
            else:
                rows.append((relative, "other", str(path.lstat().st_mode)))

    visit(root)
    return rows


class DeterministicFixtureAdapter:
    """Not reachable from a production CLI; tests inject this object directly."""

    issuer = "c4_fixture_governance"
    tool = "deterministic_fixture_adapter"
    version = "1.0.0"

    def digest(self, payload: dict[str, Any]) -> str:
        return hmac.new(FIXTURE_KEY, canonical_bytes(payload), hashlib.sha256).hexdigest()

    def verify(self, payload: dict[str, Any], digest: str) -> bool:
        return hmac.compare_digest(self.digest(payload), digest)


def issue_host_attestation(
    project: Path,
    *,
    claim_path: Path,
    target: str,
    artifact: Path,
    role: str,
    host_task_id: str,
    host_session_id: str,
    nonce: str,
    issued_at: str,
    generation_verifier: Path | None = None,
) -> tuple[dict[str, Any], Path, Path]:
    """Issue one marker-committed, fixture-only host control."""
    from assignment_dispatch_claim import _publish_record, binding
    from assignment_receipt_transaction import _assignment_root, _transaction_claim

    project = project.resolve()
    adapter = DeterministicFixtureAdapter()
    unsigned: dict[str, Any] = {
        "schema_version": "1.0.0",
        "attestation_type": "host_dispatch_independence",
        "issuer": {
            "name": adapter.issuer,
            "tool": adapter.tool,
            "version": adapter.version,
        },
        "host_task_id": host_task_id,
        "host_session_id": host_session_id,
        "role": role,
        "dispatch_claim": binding(
            project, claim_path, "assignment_dispatch_claim"
        ),
        "target": target,
        "artifact": binding(project, artifact, "governed_artifact"),
        "issued_at": issued_at,
        "nonce": nonce,
    }
    if generation_verifier is not None:
        unsigned["generation_verifier"] = binding(
            project, generation_verifier, "verifier_transaction"
        )
    attestation_id = (
        "host-" + hashlib.sha256(canonical_bytes(unsigned)).hexdigest()[:16]
    )
    unsigned["attestation_id"] = attestation_id
    attestation = {
        **unsigned,
        "authenticator": {"kind": "mac", "digest": adapter.digest(unsigned)},
    }
    schema = json.loads(HOST_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(
        schema, format_checker=FormatChecker()
    ).validate(attestation)
    lane = _assignment_root(project) / "dispatch" / "host" / attestation_id
    with _transaction_claim(project):
        path, _, marker = _publish_record(
            project, lane, "attestation.json", attestation, attestation_id
        )
    return attestation, path, marker


def issue_legacy_anchor(
    project: Path,
    *,
    ledger_path: Path,
    live_target_paths: list[str],
    authorization_path: Path,
    nonce: str,
    issued_at: str,
) -> tuple[dict[str, Any], Path, Path]:
    """Externally issue one schema-valid synthetic legacy anchor."""
    from assignment_receipt_transaction import _target_snapshot, load_mutation_ledger

    project = project.resolve()
    adapter = DeterministicFixtureAdapter()
    manifest = project / "project_manifest.json"
    manifest_value = json.loads(manifest.read_text(encoding="utf-8"))
    project_root = {
        "kind": "project",
        "identity": manifest_value["identity"],
        "discovery": "explicit:project_manifest.json",
        "manifest_sha256": sha256(manifest),
    }
    rows = load_mutation_ledger(project)
    head = rows[-1]["row_sha256"] if rows else None
    unsigned: dict[str, Any] = {
        "schema_version": "1.0.0",
        "anchor_type": "assignment_mutation_legacy",
        "state": "committed",
        "project": project_root,
        "ledger": {
            "root": project_root,
            "path": ledger_path.relative_to(project).as_posix(),
            "sha256": sha256(ledger_path),
            "evidence_type": "assignment_mutation_ledger",
        },
        "row_count": len(rows),
        "head": head,
        "live_targets": [
            {"path": target, "snapshot": _target_snapshot(project / Path(target))}
            for target in live_target_paths
        ],
        "authorization": {
            "authority": "user",
            "evidence": {
                "root": project_root,
                "path": authorization_path.relative_to(project).as_posix(),
                "sha256": sha256(authorization_path),
                "evidence_type": "synthetic_user_authorization",
            },
        },
        "adapter": {
            "issuer": adapter.issuer,
            "tool": adapter.tool,
            "version": adapter.version,
            "authorization_id": "synthetic-c4-anchor",
        },
        "issued_at": issued_at,
        "nonce": nonce,
        "historical_provenance_asserted": False,
    }
    anchor_id = f"anchor-{hashlib.sha256(canonical_bytes(unsigned)).hexdigest()[:16]}"
    unsigned["anchor_id"] = anchor_id
    anchor = {
        **unsigned,
        "authenticator": {"kind": "mac", "digest": adapter.digest(unsigned)},
    }
    schema = json.loads(ANCHOR_SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    validator.validate(anchor)
    lane = project / "reviews" / ".harness" / "assignment" / "mutation" / "external" / anchor_id
    lane.mkdir(parents=True, exist_ok=True)
    anchor_path = lane / "anchor.json"
    anchor_path.write_text(json.dumps(anchor, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_payload = {
        "schema_version": "1.0.0",
        "products": [{
            "path": anchor_path.relative_to(project).as_posix(),
            "sha256": sha256(anchor_path),
        }],
    }
    manifest_path = lane / "publication_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    marker_path = lane / "commit_marker.json"
    marker_path.write_text(
        json.dumps({
            "schema_version": "1.0.0",
            "state": "committed",
            "publication_manifest": manifest_path.relative_to(project).as_posix(),
            "publication_manifest_sha256": sha256(manifest_path),
        }, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return anchor, anchor_path, marker_path
