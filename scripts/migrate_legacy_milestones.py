#!/usr/bin/env python3
"""Discover, adjudicate, and safely migrate legacy milestone ledgers."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
MILESTONES = ("M1", "M2", "M3", "M4", "M5")
AUTHORITIES = {"user", "venue", "advisor", "instructor", "committee", "project_local_contract"}
FEEDBACK_CLASSES = (
    "direct_milestone_feedback",
    "retrospective_application",
    "harness_review_evidence",
    "cross_cutting_guidance",
)
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
MILESTONE_RE = re.compile(r"(?i)(?:milestone|(?<![a-z])m)[ _.-]*([1-5])")
REPARSE_ATTRIBUTE = 0x400


class MigrationError(ValueError):
    """A controlled migration refusal."""


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def _read_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeError as exc:
        raise MigrationError(f"{label} must be UTF-8: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise MigrationError(f"{label} is invalid JSON: {exc}") from exc
    except OSError as exc:
        raise MigrationError(f"cannot read {label}: {exc}") from exc


def _is_reparse(path: Path) -> bool:
    try:
        stat = path.lstat()
    except OSError as exc:
        raise MigrationError(f"cannot inspect path {path}: {exc}") from exc
    return path.is_symlink() or bool(getattr(stat, "st_file_attributes", 0) & REPARSE_ATTRIBUTE)


def _project_root(path: Path) -> Path:
    requested = path.expanduser().absolute()
    if not requested.is_dir() or _is_reparse(requested):
        raise MigrationError("project root must be an existing non-reparse directory")
    return requested.resolve()


def _contained(project: Path, value: str | Path, *, must_exist: bool = True) -> Path:
    if not isinstance(value, (str, Path)) or not str(value):
        raise MigrationError("contained path must be a non-empty string")
    raw = Path(value)
    candidate = raw if raw.is_absolute() else project / raw
    resolved = candidate.resolve(strict=must_exist)
    try:
        relative = resolved.relative_to(project)
    except ValueError as exc:
        raise MigrationError(f"path must be contained by project root: {value}") from exc
    cursor = project
    for part in relative.parts:
        cursor /= part
        if cursor.exists() and _is_reparse(cursor):
            raise MigrationError(f"contained path traverses a symlink or reparse point: {value}")
    return resolved


def _reject_reparse_tree(project: Path) -> None:
    for base, directories, files in os.walk(project, followlinks=False):
        for name in [*directories, *files]:
            candidate = Path(base) / name
            if _is_reparse(candidate):
                raise MigrationError(f"project contains a symlink or reparse point: {candidate.relative_to(project).as_posix()}")


def _relative(project: Path, path: Path) -> str:
    return path.relative_to(project).as_posix()


def _ledger_paths(project: Path) -> list[Path]:
    return [path for path in (project / "reviews" / "phase_state.json", project / "reviews" / "tier_state.json") if path.is_file()]


def _load_ledgers(project: Path) -> dict[str, Any]:
    reviews = project / "reviews"
    if not reviews.is_dir():
        raise MigrationError("reviews/ directory is required")
    paths = _ledger_paths(project)
    if not paths:
        raise MigrationError("neither reviews/phase_state.json nor reviews/tier_state.json exists")
    return {_relative(project, path): _read_json(path, _relative(project, path)) for path in paths}


def _iter_path_values(value: Any, prefix: str = "$") -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}"
            if isinstance(child, str) and (key == "path" or key.endswith("_path")):
                yield child_prefix, child
            else:
                yield from _iter_path_values(child, child_prefix)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_path_values(child, f"{prefix}[{index}]")


def _candidate_role(path: str) -> str:
    lower = path.lower()
    if any(word in lower for word in ("checklist", "handoff", "gate", "plan")):
        return "transition_control"
    if any(word in lower for word in ("review", "feedback", "comment")):
        return "evidence"
    if any(word in lower for word in ("export", "shipment", ".pdf")):
        return "export"
    return "deliverable"


def _artifact_candidates(project: Path) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for path in sorted(project.rglob("*"), key=lambda item: item.as_posix().lower()):
        if not path.is_file() or ".harness" in path.parts:
            continue
        relative = _relative(project, path)
        match = MILESTONE_RE.search(path.name)
        if match is None:
            continue
        payload = path.read_bytes()
        candidates.append({
            "path": relative,
            "milestone": f"M{match.group(1)}",
            "sha256": _sha(payload),
            "bytes": len(payload),
            "location_class": "archive" if any(part.lower() in {"archive", "archived"} for part in path.parts) else "live",
        })
    return candidates


def _feedback(project: Path) -> dict[str, list[str]]:
    result = {key: [] for key in FEEDBACK_CLASSES}
    for path in sorted(project.rglob("*"), key=lambda item: item.as_posix().lower()):
        if not path.is_file() or ".harness" in path.parts:
            continue
        lower = _relative(project, path).lower()
        if "feedback" in lower or "comment" in lower:
            result["direct_milestone_feedback"].append(_relative(project, path))
        elif "retrospective" in lower:
            result["retrospective_application"].append(_relative(project, path))
        elif "harness" in lower and "review" in lower:
            result["harness_review_evidence"].append(_relative(project, path))
        elif "guidance" in lower or "directive" in lower:
            result["cross_cutting_guidance"].append(_relative(project, path))
    return result


def discover(project_root: Path) -> dict[str, Any]:
    project = _project_root(project_root)
    _reject_reparse_tree(project)
    ledgers = _load_ledgers(project)
    candidates = _artifact_candidates(project)
    findings: list[dict[str, str]] = []
    holds: list[dict[str, Any]] = []
    for name, document in sorted(ledgers.items()):
        if not isinstance(document, dict):
            findings.append({"code": "LEDGER_NOT_OBJECT", "path": name})
            holds.append({"hold_id": f"ledger-not-object:{name}", "code": "LEDGER_NOT_OBJECT", "paths": [name]})
            continue
        if isinstance(document.get("sections"), list):
            findings.append({"code": "ARRAY_SECTIONS", "path": f"{name}#sections"})
        elif not isinstance(document.get("sections"), dict):
            findings.append({"code": "SECTIONS_NOT_OBJECT_OR_ARRAY", "path": f"{name}#sections"})
            holds.append({"hold_id": f"bad-sections:{name}", "code": "SECTIONS_NOT_OBJECT_OR_ARRAY", "paths": [name]})
    if len(ledgers) > 1:
        holds.append({
            "hold_id": "mixed-tier-phase-state",
            "code": "MIXED_TIER_PHASE_STATE",
            "paths": sorted(ledgers),
        })
    grouped: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        if _candidate_role(candidate["path"]) == "deliverable":
            grouped.setdefault(candidate["milestone"], []).append(candidate)
    for milestone, group in sorted(grouped.items()):
        if {item["location_class"] for item in group} == {"archive", "live"}:
            paths = sorted(item["path"] for item in group)
            holds.append({
                "hold_id": f"archive-live:{milestone}",
                "code": "ARCHIVE_LIVE_AMBIGUITY",
                "paths": paths,
            })
    path_failures: list[dict[str, str]] = []
    for ledger_name, document in sorted(ledgers.items()):
        for json_path, value in _iter_path_values(document):
            try:
                candidate = _contained(project, value)
            except (MigrationError, OSError):
                path_failures.append({"ledger": ledger_name, "json_path": json_path, "value": value})
                continue
            if not candidate.exists():
                path_failures.append({"ledger": ledger_name, "json_path": json_path, "value": value})
    feedback = _feedback(project)
    return {
        "matrix_version": "1.0.0",
        "artifact_candidates": candidates,
        "proposed_roles": [
            {"path": item["path"], "milestone": item["milestone"], "role": _candidate_role(item["path"]), "lineage_id": item["location_class"]}
            for item in candidates
        ],
        "lineage_graph": {
            "nodes": [{"path": item["path"], "lineage_id": item["location_class"], "milestone": item["milestone"]} for item in candidates],
            "edges": [],
        },
        "feedback_classes": feedback,
        "feedback_status": "captured" if any(feedback.values()) else "not captured under prior contract",
        "path_failures": path_failures,
        "ledger_shape_findings": findings,
        "holds": sorted(holds, key=lambda item: item["hold_id"]),
        "ledger_sources": sorted(ledgers),
    }


def _strict_date(value: Any, label: str) -> str:
    if not isinstance(value, str) or UTC_RE.fullmatch(value) is None:
        raise MigrationError(f"{label} must be a strict UTC timestamp ending in Z")
    try:
        from datetime import datetime
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise MigrationError(f"{label} is not a real date") from exc
    return value


def _adjudication(project: Path, path: Path, matrix: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
    contained = _contained(project, path)
    if not contained.is_file():
        raise MigrationError("adjudication must be a contained UTF-8 JSON file")
    payload = contained.read_bytes()
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise MigrationError(f"adjudication must be contained UTF-8 JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise MigrationError("adjudication must be a JSON object")
    required = {"authority", "approved_at", "evidence_path", "evidence_sha256", "primary_lineage", "completed_through", "phase_source", "resolved_holds", "artifact_roles"}
    missing = sorted(required - set(value))
    if missing:
        raise MigrationError(f"adjudication missing required fields: {missing}")
    if value["authority"] not in AUTHORITIES:
        raise MigrationError("adjudication authority is not recognized")
    _strict_date(value["approved_at"], "approved_at")
    if value["completed_through"] not in MILESTONES:
        raise MigrationError("completed_through must be M1 through M5")
    if not isinstance(value["primary_lineage"], str) or not value["primary_lineage"].strip():
        raise MigrationError("primary_lineage must be explicit")
    if value["phase_source"] not in matrix["ledger_sources"]:
        raise MigrationError("phase_source must select a discovered contained ledger")
    evidence = _contained(project, value["evidence_path"])
    if not evidence.is_file() or _sha(evidence.read_bytes()) != value["evidence_sha256"]:
        raise MigrationError("adjudication evidence path/hash does not match current bytes")
    expected_holds = {item["hold_id"] for item in matrix["holds"]}
    resolved = value["resolved_holds"]
    if (
        not isinstance(resolved, list)
        or any(not isinstance(item, str) for item in resolved)
        or set(resolved) != expected_holds
        or len(resolved) != len(set(resolved))
    ):
        raise MigrationError("all and only current migration holds must be explicitly resolved")
    if matrix["path_failures"]:
        raise MigrationError("path failures must be repaired before migration can apply")
    if not isinstance(value["artifact_roles"], dict):
        raise MigrationError("artifact_roles must be an object")
    known = {item["path"] for item in matrix["artifact_candidates"]}
    for artifact_path, role in value["artifact_roles"].items():
        if artifact_path not in known or not isinstance(role, dict):
            raise MigrationError(f"artifact role references an unknown candidate: {artifact_path}")
        if role.get("milestone") not in MILESTONES or role.get("role") not in {"deliverable", "transition_control", "evidence", "derived_view", "export"}:
            raise MigrationError(f"artifact role is invalid: {artifact_path}")
        if not isinstance(role.get("lineage_id"), str) or not role["lineage_id"]:
            raise MigrationError(f"artifact lineage is missing: {artifact_path}")
    return value, payload


def _translate_tier(value: Any) -> Any:
    mapping = {"T1": "Ph1", "T2": "Ph2", "T3": "Ph3", "T4": "Ph4"}
    if isinstance(value, str):
        return mapping.get(value, value)
    if isinstance(value, list):
        return [_translate_tier(item) for item in value]
    if isinstance(value, dict):
        translated: dict[str, Any] = {}
        key_map = {"current_tier": "current_phase", "prev_tier": "prev_phase", "new_tier": "new_phase", "default_final_tier": "default_final_phase"}
        for key, child in value.items():
            translated[key_map.get(key, key)] = _translate_tier(child)
        return translated
    return value


def _normalize_sections(document: dict[str, Any]) -> dict[str, Any]:
    document = _translate_tier(document)
    sections = document.get("sections")
    if isinstance(sections, list):
        normalized: dict[str, Any] = {}
        for index, section in enumerate(sections):
            if not isinstance(section, dict):
                raise MigrationError(f"sections[{index}] is not an object")
            section = dict(section)
            name = section.pop("path", None) or section.pop("section_path", None) or section.pop("name", None)
            if not isinstance(name, str) or not name or name in normalized:
                raise MigrationError("array sections require unique path, section_path, or name keys")
            normalized[name] = section
        document["sections"] = normalized
    if not isinstance(document.get("sections"), dict):
        raise MigrationError("sections cannot be migrated to the canonical object shape")
    document["schema_version"] = "0.7.4"
    document.pop("milestone_assignment", None)
    return document


def _record(milestone: str) -> dict[str, Any]:
    purposes = {
        "M1": "Establish project focus, motivating tension, intended readers, and question candidates.",
        "M2": "Build and annotate the evidence base needed to test the M1 framing.",
        "M3": "Turn framing and evidence into a coherent argument and evidence plan.",
        "M4": "Produce and stabilize a complete manuscript from the accepted argument plan.",
        "M5": "Finalize the manuscript for its declared delivery surface.",
    }
    return {
        "purpose": purposes[milestone],
        "status": "not_started",
        "applicability": "applicable",
        "required_inputs": ["Legacy evidence matrix and approved migration record"],
        "exit_criteria": ["Contemporaneous evidence is captured under the current milestone contract."],
        "artifacts": [],
        "feedback_records": [],
        "approval": {"status": "pending", "authority": None, "evidence_path": None, "approved_at": None},
        "handoff": {"status": "not_ready", "packet_path": None, "packet_sha256": None},
        "dependency_state": "current",
        "authorized_override": None,
    }


def _framework(project: Path, matrix: dict[str, Any], adjudication: dict[str, Any], report_path: str, report_sha: str) -> dict[str, Any]:
    milestones = {key: _record(key) for key in MILESTONES}
    by_path = {item["path"]: item for item in matrix["artifact_candidates"]}
    for path, role in sorted(adjudication["artifact_roles"].items()):
        candidate = by_path[path]
        milestones[role["milestone"]]["artifacts"].append({
            "role": role["role"],
            "artifact_kind": role.get("artifact_kind", "legacy_artifact"),
            "path": path,
            "sha256": candidate["sha256"],
            "bytes": candidate["bytes"],
            "verified_at": adjudication["approved_at"],
            "lineage_id": role["lineage_id"],
            **({"source_sha256": role["source_sha256"]} if role["role"] == "export" and "source_sha256" in role else {}),
        })
    return {
        "contract_version": "1.0.0",
        "mode": "legacy",
        "migration_boundary": {
            "authority": adjudication["authority"],
            "evidence_path": adjudication["evidence_path"],
            "evidence_sha256": adjudication["evidence_sha256"],
            "approved_at": adjudication["approved_at"],
            "completed_through": adjudication["completed_through"],
            "report_path": report_path,
            "report_sha256": report_sha,
        },
        "primary_lineage": adjudication["primary_lineage"],
        "milestones": milestones,
        "events": [],
    }


def _run_validator(script: str, project: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-I", "-S", str(SCRIPT_DIR / script), "--project-root", str(project)],
        cwd=PACKAGE_ROOT, text=True, capture_output=True, check=False,
    )
    if result.returncode != 0:
        detail = (result.stdout + result.stderr).strip()
        raise MigrationError(f"{script} rejected staged migration (exit {result.returncode}): {detail}")


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _commit_payload(migration_id: str, replacement_sha256: str, report_sha256: str) -> bytes:
    return _json_bytes({
        "migration_id": migration_id,
        "transaction_state": "committed",
        "replacement_path": "reviews/phase_state.json",
        "replacement_sha256": replacement_sha256,
        "report_sha256": report_sha256,
    })


def apply_migration(
    project_root: Path,
    adjudication_path: Path,
    *,
    atomic_writer: Callable[[Path, bytes], None] = _atomic_write,
) -> dict[str, Any]:
    project = _project_root(project_root)
    _reject_reparse_tree(project)
    canonical = project / "reviews" / "phase_state.json"
    if canonical.is_file():
        existing = _read_json(canonical, "reviews/phase_state.json")
        framework = existing.get("milestone_framework") if isinstance(existing, dict) else None
        if isinstance(framework, dict) and framework.get("mode") == "legacy" and framework.get("migration_boundary"):
            boundary = framework["migration_boundary"]
            if not isinstance(boundary, dict):
                raise MigrationError("existing legacy migration boundary is not an object")
            report_path = _contained(project, boundary.get("report_path", ""))
            migration_dir = report_path.parent
            manifest = _read_json(migration_dir / "rollback_manifest.json", "rollback manifest")
            current_sha = _sha(canonical.read_bytes())
            if (
                not isinstance(manifest, dict)
                or not isinstance(manifest.get("migration_id"), str)
                or manifest.get("replacement_sha256") != current_sha
                or not isinstance(boundary.get("report_sha256"), str)
            ):
                raise MigrationError("existing legacy migration has no matching rollback manifest")
            commit_path = migration_dir / "commit.json"
            expected_commit = _commit_payload(
                manifest["migration_id"], current_sha, boundary["report_sha256"]
            )
            if commit_path.exists():
                if commit_path.read_bytes() != expected_commit:
                    raise MigrationError("existing migration commit marker does not match current authority")
            else:
                _atomic_write(commit_path, expected_commit)
                return {"outcome": "recovered_committed", "report_path": boundary["report_path"]}
            return {"outcome": "already_migrated", "report_path": boundary["report_path"]}
    matrix = discover(project)
    adjudication, adjudication_payload = _adjudication(project, adjudication_path, matrix)
    ledgers = _load_ledgers(project)
    source_name = adjudication["phase_source"]
    source_doc = ledgers[source_name]
    if not isinstance(source_doc, dict):
        raise MigrationError("selected phase source must be an object")
    source_hashes = {name: _sha((project / name).read_bytes()) for name in ledgers}
    migration_id = _sha((source_hashes[source_name] + _sha(adjudication_payload)).encode("ascii"))[:16]
    migration_relative = f"reviews/.harness/migrations/{migration_id}"
    report_relative = f"{migration_relative}/migration_report.json"
    report = {
        "migration_id": migration_id,
        "adjudication_outcome": "approved",
        "transaction_state": "prepared",
        "authority_effect": "non-authoritative until commit.json exists and matches replacement bytes",
        "authority": adjudication["authority"],
        "approved_at": adjudication["approved_at"],
        "completed_through": adjudication["completed_through"],
        "primary_lineage": adjudication["primary_lineage"],
        "resolved_holds": adjudication["resolved_holds"],
        "artifact_roles": adjudication["artifact_roles"],
        "adjudication_sha256": _sha(adjudication_payload),
        "feedback_status": matrix["feedback_status"],
        "evidence_matrix": matrix,
        "historical_approval_policy": "No milestone approval or F9 handoff was inferred from legacy completion.",
    }
    report_payload = _json_bytes(report)
    candidate = _normalize_sections(json.loads(json.dumps(source_doc)))
    candidate["milestone_framework"] = _framework(project, matrix, adjudication, report_relative, _sha(report_payload))
    candidate_payload = _json_bytes(candidate)
    archive_entries = []
    for name, digest in sorted(source_hashes.items()):
        archive_entries.append({
            "original_path": name,
            "original_sha256": digest,
            "archive_path": f"{migration_relative}/original/{Path(name).name}",
        })
    manifest = {
        "manifest_version": "1.0.0",
        "migration_id": migration_id,
        "replacement_path": "reviews/phase_state.json",
        "replacement_sha256": _sha(candidate_payload),
        "original_sha256": source_hashes[source_name],
        "archive_path": next(item["archive_path"] for item in archive_entries if item["original_path"] == source_name),
        "originals": archive_entries,
    }
    manifest_payload = _json_bytes(manifest)
    commit_payload = _commit_payload(
        migration_id, manifest["replacement_sha256"], _sha(report_payload)
    )
    stage_parent = project.parent
    stage = Path(tempfile.mkdtemp(prefix=f".{project.name}.legacy-migration-", dir=stage_parent))
    published_dir = project / migration_relative
    removed_backups: dict[Path, bytes] = {}
    state_replaced = False
    try:
        shutil.rmtree(stage)
        shutil.copytree(project, stage, symlinks=True)
        stage_migration = stage / migration_relative
        stage_migration.mkdir(parents=True, exist_ok=False)
        (stage_migration / "original").mkdir()
        for item in archive_entries:
            archive = stage / item["archive_path"]
            archive.write_bytes((project / item["original_path"]).read_bytes())
        (stage / report_relative).write_bytes(report_payload)
        (stage_migration / "rollback_manifest.json").write_bytes(manifest_payload)
        for name in ledgers:
            legacy = stage / name
            if legacy.exists():
                legacy.unlink()
        (stage / "reviews" / "phase_state.json").write_bytes(candidate_payload)
        _run_validator("milestone_framework_validate.py", stage)
        _run_validator("phase_state_validate.py", stage)
        for name, digest in source_hashes.items():
            current = project / name
            if not current.is_file() or _sha(current.read_bytes()) != digest:
                raise MigrationError(f"source changed during migration transaction: {name}")
        if published_dir.exists() or published_dir.is_symlink():
            if _is_reparse(published_dir):
                raise MigrationError("migration publication directory is a reparse point")
            orphan_report = _read_json(published_dir / "migration_report.json", "prepared migration report")
            orphan_manifest = _read_json(published_dir / "rollback_manifest.json", "prepared rollback manifest")
            orphan_originals = orphan_manifest.get("originals") if isinstance(orphan_manifest, dict) else None
            if (
                not isinstance(orphan_report, dict)
                or orphan_report.get("transaction_state") != "prepared"
                or (published_dir / "commit.json").exists()
                or not isinstance(orphan_manifest, dict)
                or orphan_manifest.get("migration_id") != migration_id
                or not isinstance(orphan_originals, list)
                or any(
                    not isinstance(item, dict)
                    or not isinstance(item.get("original_path"), str)
                    or not isinstance(item.get("original_sha256"), str)
                    for item in (orphan_originals or [])
                )
                or any(
                    not (project / item["original_path"]).is_file()
                    or _sha((project / item["original_path"]).read_bytes()) != item["original_sha256"]
                    for item in (orphan_originals or [])
                )
            ):
                raise MigrationError("existing migration publication is not a recoverable prepared transaction")
            shutil.rmtree(published_dir)
        published_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(stage_migration, published_dir)
        for name in ledgers:
            path = project / name
            removed_backups[path] = path.read_bytes()
            if path.name != "phase_state.json":
                path.unlink()
        atomic_writer(canonical, candidate_payload)
        state_replaced = True
        atomic_writer(published_dir / "commit.json", commit_payload)
    except Exception:
        if state_replaced or removed_backups:
            for path, payload in removed_backups.items():
                _atomic_write(path, payload)
        if published_dir.exists():
            shutil.rmtree(published_dir)
        raise
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return {"outcome": "migrated", "migration_id": migration_id, "report_path": report_relative, "replacement_sha256": manifest["replacement_sha256"]}


def rollback(project_root: Path, manifest_path: Path) -> dict[str, Any]:
    project = _project_root(project_root)
    _reject_reparse_tree(project)
    path = _contained(project, manifest_path)
    manifest = _read_json(path, "rollback manifest")
    if not isinstance(manifest, dict) or manifest.get("manifest_version") != "1.0.0":
        raise MigrationError("rollback manifest has an unsupported shape")
    replacement = _contained(project, manifest.get("replacement_path", ""))
    if not replacement.is_file() or _sha(replacement.read_bytes()) != manifest.get("replacement_sha256"):
        raise MigrationError("current replacement hash changed; rollback refuses to overwrite it")
    originals = manifest.get("originals")
    if not isinstance(originals, list) or not originals:
        raise MigrationError("rollback manifest has no original ledger entries")
    restored: list[str] = []
    for item in originals:
        if not isinstance(item, dict):
            raise MigrationError("rollback manifest original entry is invalid")
        archive = _contained(project, item.get("archive_path", ""))
        target = _contained(project, item.get("original_path", ""), must_exist=False)
        payload = archive.read_bytes()
        if _sha(payload) != item.get("original_sha256"):
            raise MigrationError("archived original hash changed; rollback refuses")
        if target.exists() and target != replacement:
            raise MigrationError(f"rollback refuses to overwrite a recreated ledger: {item['original_path']}")
        restored.append(item["original_path"])
    for item in originals:
        archive = _contained(project, item["archive_path"])
        target = _contained(project, item["original_path"], must_exist=False)
        _atomic_write(target, archive.read_bytes())
    return {"outcome": "rolled_back", "restored": sorted(restored)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--adjudication", type=Path)
    parser.add_argument("--rollback", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.rollback is not None:
            if args.apply or args.adjudication is not None:
                raise MigrationError("--rollback cannot be combined with --apply or --adjudication")
            result = rollback(args.project_root, args.rollback)
        elif args.apply:
            if args.adjudication is None:
                raise MigrationError("--apply requires --adjudication with contained UTF-8 JSON")
            result = apply_migration(args.project_root, args.adjudication)
        else:
            if args.adjudication is not None:
                raise MigrationError("--adjudication is meaningful only with --apply")
            result = discover(args.project_root)
    except (MigrationError, OSError, UnicodeError) as exc:
        parser.exit(2, f"error: {exc}\n")
    sys.stdout.buffer.write(_json_bytes(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
