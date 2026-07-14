#!/usr/bin/env python3
"""Smoke tests for the guarded legacy milestone migration."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATOR = ROOT / "scripts" / "migrate_legacy_milestones.py"
CASES = (
    "dry_run_writes_nothing",
    "archive_live_ambiguity_creates_hold",
    "missing_feedback_is_not_captured_not_invented",
    "array_sections_migrate_to_object",
    "mixed_tier_phase_state_requires_adjudication",
    "approved_migration_is_idempotent",
    "rollback_manifest_restores_original_hash",
)


def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", "-S", str(MIGRATOR), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def phase_document(*, sections_as_array: bool = True) -> dict:
    section = {
        "path": "manuscript/main.md",
        "current_phase": "Ph1",
        "phase_entry_log": [{
            "prev_phase": None,
            "new_phase": "Ph1",
            "trigger": "initial_dispatch",
            "actor": "planner",
            "notes": "Legacy project state.",
            "timestamp": "2026-07-13T20:00:00Z",
            "model_used": None,
        }],
    }
    return {
        "schema_version": "0.7.4",
        "manuscript_id": "legacy-test",
        "default_final_phase": "Ph4",
        "terminal_phase_reached": False,
        "sections": [section] if sections_as_array else {"manuscript/main.md": {k: v for k, v in section.items() if k != "path"}},
    }


def make_project(root: Path, *, ambiguous: bool = False, mixed: bool = False) -> Path:
    project = root / "legacy-test"
    (project / "reviews").mkdir(parents=True)
    (project / "manuscript").mkdir()
    (project / "archive").mkdir()
    (project / "manuscript" / "main.md").write_text("# Live draft\n", encoding="utf-8")
    (project / "archive" / "milestone1_project_memo.md").write_text("# Archived memo\n", encoding="utf-8")
    if ambiguous:
        (project / "manuscript" / "milestone1_revised_memo.md").write_text("# Live memo\n", encoding="utf-8")
    write_json(project / "reviews" / "phase_state.json", phase_document())
    if mixed:
        write_json(project / "reviews" / "tier_state.json", {"schema_version": "0.7.3", "sections": {}})
    return project


def approved_adjudication(project: Path, matrix: dict) -> Path:
    approval = project / "reviews" / "migration_approval.md"
    approval.write_text("User authorizes the bounded legacy migration.\n", encoding="utf-8")
    adjudication = {
        "authority": "user",
        "approved_at": "2026-07-13T21:00:00Z",
        "evidence_path": "reviews/migration_approval.md",
        "evidence_sha256": sha(approval.read_bytes()),
        "primary_lineage": "live",
        "completed_through": "M3",
        "phase_source": "reviews/phase_state.json",
        "resolved_holds": [hold["hold_id"] for hold in matrix["holds"]],
        "artifact_roles": {},
    }
    path = project / "adjudication.json"
    write_json(path, adjudication)
    return path


def main() -> int:
    completed: list[str] = []
    with tempfile.TemporaryDirectory(prefix="legacy-migration-smoke-") as directory:
        base = Path(directory)

        project = make_project(base / "dry")
        before = {p.relative_to(project).as_posix(): sha(p.read_bytes()) for p in project.rglob("*") if p.is_file()}
        dry = run("--project-root", str(project))
        assert dry.returncode == 0, dry.stdout + dry.stderr
        matrix = json.loads(dry.stdout)
        after = {p.relative_to(project).as_posix(): sha(p.read_bytes()) for p in project.rglob("*") if p.is_file()}
        assert before == after
        assert set(("artifact_candidates", "proposed_roles", "lineage_graph", "feedback_classes", "path_failures", "ledger_shape_findings", "holds")) <= set(matrix)
        completed.append("dry_run_writes_nothing")

        ambiguous = make_project(base / "ambiguous", ambiguous=True)
        result = run("--project-root", str(ambiguous))
        evidence = json.loads(result.stdout)
        assert any(h["code"] == "ARCHIVE_LIVE_AMBIGUITY" for h in evidence["holds"])
        completed.append("archive_live_ambiguity_creates_hold")

        assert evidence["feedback_classes"] == {
            "direct_milestone_feedback": [],
            "retrospective_application": [],
            "harness_review_evidence": [],
            "cross_cutting_guidance": [],
        }
        assert evidence["feedback_status"] == "not captured under prior contract"
        completed.append("missing_feedback_is_not_captured_not_invented")

        apply_project = make_project(base / "apply")
        dry_matrix = json.loads(run("--project-root", str(apply_project)).stdout)
        adjudication = approved_adjudication(apply_project, dry_matrix)
        applied = run("--project-root", str(apply_project), "--apply", "--adjudication", str(adjudication))
        assert applied.returncode == 0, applied.stdout + applied.stderr
        result_doc = json.loads((apply_project / "reviews" / "phase_state.json").read_text(encoding="utf-8"))
        assert isinstance(result_doc["sections"], dict)
        migration_dir = next((apply_project / "reviews" / ".harness" / "migrations").iterdir())
        report = json.loads((migration_dir / "migration_report.json").read_text(encoding="utf-8"))
        commit = json.loads((migration_dir / "commit.json").read_text(encoding="utf-8"))
        assert report["transaction_state"] == "prepared"
        assert report["authority_effect"] == "non-authoritative until commit.json exists and matches replacement bytes"
        assert commit["transaction_state"] == "committed"
        assert commit["replacement_sha256"] == sha((apply_project / "reviews" / "phase_state.json").read_bytes())
        completed.append("array_sections_migrate_to_object")

        mixed = make_project(base / "mixed", mixed=True)
        mixed_matrix = json.loads(run("--project-root", str(mixed)).stdout)
        assert any(h["code"] == "MIXED_TIER_PHASE_STATE" for h in mixed_matrix["holds"])
        refused = run("--project-root", str(mixed), "--apply")
        assert refused.returncode == 2 and "adjudication" in refused.stderr.lower()
        completed.append("mixed_tier_phase_state_requires_adjudication")

        commit_path = migration_dir / "commit.json"
        commit_path.unlink()
        state_before_recovery = sha((apply_project / "reviews" / "phase_state.json").read_bytes())
        recovered = run("--project-root", str(apply_project), "--apply", "--adjudication", str(adjudication))
        assert recovered.returncode == 0, recovered.stdout + recovered.stderr
        assert json.loads(recovered.stdout)["outcome"] == "recovered_committed"
        assert commit_path.is_file()
        assert sha((apply_project / "reviews" / "phase_state.json").read_bytes()) == state_before_recovery

        first_hashes = {p.relative_to(apply_project).as_posix(): sha(p.read_bytes()) for p in apply_project.rglob("*") if p.is_file()}
        second = run("--project-root", str(apply_project), "--apply", "--adjudication", str(adjudication))
        assert second.returncode == 0, second.stdout + second.stderr
        second_hashes = {p.relative_to(apply_project).as_posix(): sha(p.read_bytes()) for p in apply_project.rglob("*") if p.is_file()}
        assert first_hashes == second_hashes
        assert json.loads(second.stdout)["outcome"] == "already_migrated"
        completed.append("approved_migration_is_idempotent")

        manifest_paths = list((apply_project / "reviews" / ".harness" / "migrations").glob("*/rollback_manifest.json"))
        assert len(manifest_paths) == 1
        manifest = json.loads(manifest_paths[0].read_text(encoding="utf-8"))
        current = apply_project / manifest["replacement_path"]
        assert sha(current.read_bytes()) == manifest["replacement_sha256"]
        rolled = run("--project-root", str(apply_project), "--rollback", str(manifest_paths[0]))
        assert rolled.returncode == 0, rolled.stdout + rolled.stderr
        assert sha(current.read_bytes()) == manifest["original_sha256"]
        completed.append("rollback_manifest_restores_original_hash")

    assert tuple(completed) == CASES, completed
    print(f"PASS migrate_legacy_milestones_smoketest ({len(completed)} cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
