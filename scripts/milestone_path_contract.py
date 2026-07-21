#!/usr/bin/env python3
"""Single resolver and fail-closed validator for milestone artifact paths."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_PATH = ROOT / "references" / "role_output_contract.json"
PATH_CONTRACT_VERSION = "2.0.0"
PUBLIC_TO_LEDGER = {"FINAL": "M5"}
LEGACY_DELIVERABLE_PATHS = frozenset({
    "research_notes/project_memo.md",
    "research_notes/annotated_references.md",
    "manuscript/outline.md",
    "manuscript/main.md",
    "manuscript/final.md",
})


class CanonicalPathError(ValueError):
    """A project exposes a legacy, aliased, or otherwise unsafe path surface."""


def load_role_output_contract() -> dict[str, Any]:
    data = json.loads(AUTHORITY_PATH.read_text(encoding="utf-8"))
    if data.get("schema_version") != PATH_CONTRACT_VERSION:
        raise CanonicalPathError("ROLE-OUTPUT-CONTRACT-VERSION: expected 2.0.0")
    if data.get("path_contract_version") != PATH_CONTRACT_VERSION:
        raise CanonicalPathError("MILESTONE-PATH-CONTRACT-VERSION: expected 2.0.0")
    milestones = data.get("milestones")
    if not isinstance(milestones, dict) or set(milestones) != {"M1", "M2", "M3", "M4", "M5"}:
        raise CanonicalPathError("MILESTONE-PATH-CONTRACT-SHAPE: expected M1-M5")
    paths = [row.get("deliverable_path") for row in milestones.values() if isinstance(row, dict)]
    if len(paths) != 5 or len(set(paths)) != 5 or any(not isinstance(path, str) for path in paths):
        raise CanonicalPathError("MILESTONE-PATH-CONTRACT-ALIAS: deliverable paths must be unique")
    return data


def ledger_milestone(target: str) -> str:
    milestone = PUBLIC_TO_LEDGER.get(target, target)
    if milestone not in {"M1", "M2", "M3", "M4", "M5"}:
        raise CanonicalPathError(f"MILESTONE-TARGET-UNKNOWN: {target}")
    return milestone


def milestone_row(target: str) -> dict[str, Any]:
    return load_role_output_contract()["milestones"][ledger_milestone(target)]


def canonical_deliverable(target: str) -> str:
    return str(milestone_row(target)["deliverable_path"])


def released_export(target: str) -> str | None:
    value = milestone_row(target).get("released_export_path")
    return str(value) if isinstance(value, str) else None


def authorized_paths(target: str) -> list[str]:
    paths = [canonical_deliverable(target)]
    export = released_export(target)
    if export:
        paths.append(export)
    return paths


def handoff_path(target: str) -> str:
    return str(milestone_row(target)["handoff_path"])


def snapshot_path(target: str, digest: str) -> str:
    milestone = ledger_milestone(target)
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise CanonicalPathError("MILESTONE-SNAPSHOT-DIGEST: expected lowercase SHA-256")
    return f"reviews/.harness/snapshots/{milestone}/{digest}.md"


def _file_identity(path: Path) -> tuple[int, int] | tuple[str, str]:
    try:
        details = path.stat()
        return details.st_dev, details.st_ino
    except OSError:
        return str(path.resolve()), hashlib.sha256(path.read_bytes()).hexdigest()


def _is_reparse(path: Path) -> bool:
    details = path.lstat()
    attrs = getattr(details, "st_file_attributes", 0)
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return path.is_symlink() or bool(attrs & reparse)


def validate_project_path_surface(project_root: Path, *, require_all: bool = True) -> None:
    root = project_root.resolve()
    contract = load_role_output_contract()
    canonical = [str(row["deliverable_path"]) for row in contract["milestones"].values()]
    present: list[Path] = []
    for relative in canonical:
        path = root / relative
        if require_all and not path.is_file():
            raise CanonicalPathError(f"MILESTONE-CANONICAL-MISSING: {relative}")
        if path.exists() or path.is_symlink():
            if not path.is_file() or _is_reparse(path):
                raise CanonicalPathError(f"MILESTONE-CANONICAL-UNSAFE: {relative}")
            present.append(path)
    legacy_present = sorted(relative for relative in LEGACY_DELIVERABLE_PATHS if (root / relative).exists() or (root / relative).is_symlink())
    if legacy_present:
        raise CanonicalPathError("MILESTONE-LEGACY-ALIAS: " + ", ".join(legacy_present))
    identities: dict[tuple[int, int] | tuple[str, str], str] = {}
    for path in present:
        identity = _file_identity(path)
        if identity in identities:
            raise CanonicalPathError(f"MILESTONE-WRITABLE-ALIAS: {path.relative_to(root).as_posix()} aliases {identities[identity]}")
        identities[identity] = path.relative_to(root).as_posix()


def role_output_contract_sha256() -> str:
    return hashlib.sha256(AUTHORITY_PATH.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
