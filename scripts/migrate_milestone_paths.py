#!/usr/bin/env python3
"""Plan, apply, verify, or roll back canonical milestone path migration.

Dry-run is read-only and emits the exact reviewed manifest. Apply requires that
manifest back through ``--reviewed-manifest`` so the inspected plan, not a
fresh implicit plan, controls the mutation.
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
import stat
import sys
import uuid
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from milestone_path_contract import (
    LEGACY_DELIVERABLE_PATHS,
    PATH_CONTRACT_VERSION,
    canonical_deliverable,
    handoff_path,
    validate_project_path_surface,
)


LEGACY_TO_CANONICAL = {
    "research_notes/project_memo.md": canonical_deliverable("M1"),
    "research_notes/annotated_references.md": canonical_deliverable("M2"),
    "manuscript/outline.md": canonical_deliverable("M3"),
    "manuscript/main.md": canonical_deliverable("M4"),
    "manuscript/final.md": canonical_deliverable("FINAL"),
}
HANDOFF_NAMES = {
    "M1_to_M2.json": handoff_path("M1"),
    "M2_to_M3.json": handoff_path("M2"),
    "M3_to_M4.json": handoff_path("M3"),
    "M4_to_M5.json": handoff_path("M4"),
    "M5_terminal.json": handoff_path("FINAL"),
}
SHA = "sha256"


class MigrationError(RuntimeError):
    pass


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _safe(project: Path, relative: str) -> Path:
    if "\\" in relative:
        raise MigrationError(f"PATH-UNSAFE: {relative}")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts:
        raise MigrationError(f"PATH-UNSAFE: {relative}")
    path = project.joinpath(*pure.parts)
    try:
        path.resolve(strict=False).relative_to(project.resolve())
    except ValueError as exc:
        raise MigrationError(f"PATH-ESCAPE: {relative}") from exc
    return path


def _is_reparse(path: Path) -> bool:
    attrs = getattr(path.lstat(), "st_file_attributes", 0)
    return path.is_symlink() or bool(attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def _plain_file(path: Path, label: str) -> None:
    if not path.is_file() or _is_reparse(path):
        raise MigrationError(f"MIGRATION-UNSAFE-{label}: {path}")


def _replace(value: Any) -> Any:
    """Rebind current records; append-only historical event rows are skipped by caller."""
    if isinstance(value, str):
        if value in LEGACY_TO_CANONICAL:
            return LEGACY_TO_CANONICAL[value]
        if value.startswith("reviews/.harness/milestones/artifacts/M4/"):
            return value.replace("reviews/.harness/milestones/artifacts/M4/", "reviews/.harness/snapshots/M4/", 1)
        for name, target in HANDOFF_NAMES.items():
            if value == f"reviews/.harness/milestones/{name}":
                return target
        return value
    if isinstance(value, list):
        return [_replace(item) for item in value]
    if isinstance(value, dict):
        return {key: _replace(item) for key, item in value.items()}
    return value


def _receipt_inventory(project: Path) -> list[dict[str, Any]]:
    root = project / "reviews" / ".harness" / "assignment"
    rows: list[dict[str, Any]] = []
    for state in ("ready", "reserved", "consumed", "invalidated"):
        directory = root / state
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("gate_receipt_*.json")):
            _plain_file(path, "RECEIPT")
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (UnicodeError, json.JSONDecodeError) as exc:
                raise MigrationError(f"MIGRATION-RECEIPT-JSON: {path}: {exc}") from exc
            bound = sorted(set(data.get("authorized_paths", [])) & set(LEGACY_TO_CANONICAL)) if isinstance(data, dict) else []
            rows.append({"path": path.relative_to(project).as_posix(), "state": state, "sha256": _sha(path), "legacy_paths": bound})
    return rows


def build_plan(project: Path) -> dict[str, Any]:
    project = project.resolve()
    claim = project / "reviews" / ".harness" / "milestones" / "claims" / "transaction.lock"
    if claim.exists() or claim.is_symlink():
        raise MigrationError(f"MIGRATION-ACTIVE-TRANSACTION: {claim}")
    moves: list[dict[str, Any]] = []
    identities: dict[tuple[int, int], str] = {}
    for source, target in LEGACY_TO_CANONICAL.items():
        old = _safe(project, source); new = _safe(project, target)
        if old.exists() or old.is_symlink():
            _plain_file(old, "DELIVERABLE")
            details = old.stat(); identity = (details.st_dev, details.st_ino)
            if identity in identities:
                raise MigrationError(f"MIGRATION-DUPLICATE-WRITABLE-ALIAS: {source} aliases {identities[identity]}")
            identities[identity] = source
            if new.exists() or new.is_symlink():
                raise MigrationError(f"MIGRATION-MIXED-PATHS: both {source} and {target} exist")
            moves.append({"kind": "deliverable", "source": source, "target": target, "sha256": _sha(old), "bytes": old.stat().st_size})
        elif new.exists() or new.is_symlink():
            _plain_file(new, "DELIVERABLE")
    old_handoffs = project / "reviews" / ".harness" / "milestones"
    for name, target in HANDOFF_NAMES.items():
        old = old_handoffs / name
        if old.exists() or old.is_symlink():
            _plain_file(old, "HANDOFF")
            new = _safe(project, target)
            if new.exists() or new.is_symlink():
                raise MigrationError(f"MIGRATION-MIXED-HANDOFFS: both {old.relative_to(project).as_posix()} and {target} exist")
            moves.append({"kind": "handoff", "source": old.relative_to(project).as_posix(), "target": target, "sha256": _sha(old), "bytes": old.stat().st_size})
    old_snapshots = project / "reviews" / ".harness" / "milestones" / "artifacts" / "M4"
    if old_snapshots.is_dir():
        for old in sorted(old_snapshots.glob("*.md")):
            _plain_file(old, "SNAPSHOT")
            target = f"reviews/.harness/snapshots/M4/{old.name}"
            if _safe(project, target).exists():
                raise MigrationError(f"MIGRATION-MIXED-SNAPSHOTS: {target}")
            moves.append({"kind": "snapshot", "source": old.relative_to(project).as_posix(), "target": target, "sha256": _sha(old), "bytes": old.stat().st_size})
    receipts = _receipt_inventory(project)
    invalidations = [row["path"] for row in receipts if row["state"] in {"ready", "reserved"} and row["legacy_paths"]]
    state_path = project / "reviews" / "phase_state.json"
    state = None
    if state_path.is_file():
        _plain_file(state_path, "STATE")
        state = {"path": "reviews/phase_state.json", "sha256": _sha(state_path), "bytes": state_path.stat().st_size}
    identity = hashlib.sha256(json.dumps({"moves": moves, "receipts": receipts, "state": state}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {
        "schema_version": "1.0.0", "migration_id": f"milestone-paths-v2-{identity[:16]}",
        "path_contract_version": PATH_CONTRACT_VERSION, "project_root": str(project),
        "moves": moves, "receipt_inventory": receipts, "invalidate_receipts": invalidations,
        "state": state, "plan_sha256": identity,
    }


def _write_json_atomic(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def _append_migration_event(state: dict[str, Any], migration_id: str, manifest_path: str, at: str) -> None:
    framework = state.get("milestone_framework")
    if not isinstance(framework, dict):
        raise MigrationError("MIGRATION-STATE: milestone_framework is required")
    framework["path_contract_version"] = PATH_CONTRACT_VERSION
    # Rebind current records but keep append-only historical event rows intact.
    events = framework.get("events", [])
    current = {key: value for key, value in framework.items() if key != "events"}
    current = _replace(current)
    framework.clear(); framework.update(current); framework["events"] = events
    sequence = max((row.get("sequence", 0) for row in events if isinstance(row, dict)), default=0) + 1
    events.append({
        "sequence": sequence, "event_type": "migration_accepted",
        "timestamp": at, "milestone": "M1", "lineage_id": framework.get("primary_lineage", "main"),
        "actor": "planner", "authority": "project_local_contract",
        "reason": f"Migrated current milestone bindings to path contract {PATH_CONTRACT_VERSION}.",
        "evidence_path": manifest_path, "evidence_sha256": None,
        "caused_by_sequence": None, "bindings": [],
    })
    sections = state.get("sections")
    if isinstance(sections, dict):
        state["sections"] = {_replace(key): _replace(value) for key, value in sections.items()}


def apply_plan(project: Path, reviewed: dict[str, Any]) -> Path:
    project = project.resolve()
    migration_id = reviewed.get("migration_id")
    if not isinstance(migration_id, str) or not migration_id:
        raise MigrationError("MIGRATION-PLAN-SHAPE: reviewed manifest lacks migration_id")
    manifest_rel = f"reviews/.harness/path_migrations/{migration_id}.applied.json"
    manifest_path = _safe(project, manifest_rel)
    if manifest_path.exists():
        validate_project_path_surface(project, require_all=False)
        return manifest_path
    live = build_plan(project)
    if reviewed != live:
        raise MigrationError("MIGRATION-PLAN-DRIFT: reviewed manifest differs from current inventory")
    rollback: list[dict[str, str]] = []
    handoff_hashes: dict[str, str] = {}
    for move in live["moves"]:
        source = _safe(project, move["source"]); target = _safe(project, move["target"])
        data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != move["sha256"]:
            raise MigrationError(f"MIGRATION-HASH-DRIFT: {move['source']}")
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(source, target)
        if _sha(target) != move["sha256"]:
            raise MigrationError(f"MIGRATION-MOVE-HASH: {move['target']}")
        if move["kind"] == "handoff":
            history = project / "reviews" / ".harness" / "path_migrations" / "history" / migration_id / source.name
            history.parent.mkdir(parents=True, exist_ok=True)
            history.write_bytes(data)
            packet = _replace(json.loads(data))
            _write_json_atomic(target, packet)
            handoff_hashes[move["target"]] = _sha(target)
        rollback.append({"path": move["source"], "content_b64": base64.b64encode(data).decode("ascii")})
    invalidated_root = project / "reviews" / ".harness" / "assignment" / "invalidated"
    for relative in live["invalidate_receipts"]:
        source = _safe(project, relative); target = invalidated_root / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            target = target.with_name(f"{target.stem}-{migration_id}{target.suffix}")
        os.replace(source, target)
        rollback.append({"path": relative, "content_b64": base64.b64encode(target.read_bytes()).decode("ascii")})
    state_path = project / "reviews" / "phase_state.json"
    if state_path.is_file():
        before = state_path.read_bytes(); state = json.loads(before)
        rollback.append({"path": "reviews/phase_state.json", "content_b64": base64.b64encode(before).decode("ascii")})
        _append_migration_event(state, migration_id, manifest_rel, _timestamp())
        framework = state["milestone_framework"]
        for record in framework.get("milestones", {}).values():
            if not isinstance(record, dict) or not isinstance(record.get("handoff"), dict):
                continue
            packet_path = record["handoff"].get("packet_path")
            if packet_path in handoff_hashes:
                record["handoff"]["packet_sha256"] = handoff_hashes[packet_path]
        _write_json_atomic(state_path, state)
    applied = copy.deepcopy(live)
    applied.update({"applied_at": _timestamp(), "rollback": rollback, "manifest_path": manifest_rel})
    _write_json_atomic(manifest_path, applied)
    # Bind the event to the final manifest bytes in a second state-last write.
    if state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["milestone_framework"]["events"][-1]["evidence_sha256"] = _sha(manifest_path)
        _write_json_atomic(state_path, state)
    validate_project_path_surface(project, require_all=False)
    return manifest_path


def rollback(project: Path, manifest_path: Path) -> None:
    project = project.resolve(); manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("project_root") != str(project):
        raise MigrationError("MIGRATION-ROLLBACK-PROJECT: manifest belongs to another project")
    for move in reversed(manifest.get("moves", [])):
        target = _safe(project, move["target"])
        if target.exists():
            target.unlink()
    for row in manifest.get("rollback", []):
        path = _safe(project, row["path"]); path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(base64.b64decode(row["content_b64"]))
    manifest_path.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--rollback", action="store_true")
    parser.add_argument("--reviewed-manifest", type=Path)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.dry_run:
            print(json.dumps(build_plan(args.project_root), indent=2, ensure_ascii=False))
        elif args.apply:
            if args.reviewed_manifest is None:
                raise MigrationError("MIGRATION-REVIEW-REQUIRED: --apply requires --reviewed-manifest")
            reviewed = json.loads(args.reviewed_manifest.read_text(encoding="utf-8"))
            print(f"APPLIED {apply_plan(args.project_root, reviewed)}")
        else:
            if args.manifest is None:
                raise MigrationError("MIGRATION-ROLLBACK-MANIFEST: --rollback requires --manifest")
            rollback(args.project_root, args.manifest)
            print("ROLLED_BACK")
    except (OSError, UnicodeError, json.JSONDecodeError, MigrationError, ValueError) as exc:
        print(f"BLOCKED {exc}")
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
