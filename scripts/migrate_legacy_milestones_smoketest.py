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
sys.path.insert(0, str(ROOT / "scripts"))
import migrate_legacy_milestones as migration
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


def make_project(root: Path, *, ambiguous: bool = False, mixed: bool = False, tier_only: bool = False) -> Path:
    project = root / "legacy-test"
    (project / "reviews").mkdir(parents=True)
    (project / "manuscript").mkdir()
    (project / "archive").mkdir()
    (project / "research_notes").mkdir()
    (project / "manuscript" / "main.md").write_text("# Live draft\n", encoding="utf-8")
    (project / "research_notes" / "milestone1_project_memo.md").write_text("# Live memo\n", encoding="utf-8")
    (project / "research_notes" / "milestone2_annotated_references.md").write_text("# Live references\n", encoding="utf-8")
    (project / "manuscript" / "milestone3_outline.md").write_text("# Live outline\n", encoding="utf-8")
    if ambiguous:
        (project / "archive" / "milestone1_archived_memo.md").write_text("# Archived memo\n", encoding="utf-8")
    if not tier_only:
        write_json(project / "reviews" / "phase_state.json", phase_document())
    if mixed:
        write_json(project / "reviews" / "tier_state.json", {"schema_version": "0.7.3", "sections": {}})
    elif tier_only:
        tier = phase_document()
        tier["schema_version"] = "0.7.3"
        tier["sections"][0]["current_tier"] = "T1"
        del tier["sections"][0]["current_phase"]
        tier["sections"][0]["phase_entry_log"][0]["prev_tier"] = None
        tier["sections"][0]["phase_entry_log"][0]["new_tier"] = "T1"
        del tier["sections"][0]["phase_entry_log"][0]["prev_phase"]
        del tier["sections"][0]["phase_entry_log"][0]["new_phase"]
        write_json(project / "reviews" / "tier_state.json", tier)
    return project


def approved_adjudication(project: Path, matrix: dict) -> Path:
    approval = project / "reviews" / "migration_approval.md"
    approval.write_text("User authorizes the bounded legacy migration.\n", encoding="utf-8")
    boundary = "M3"
    artifact_roles = {}
    for candidate in matrix["artifact_candidates"]:
        if candidate["milestone"] not in {"M1", "M2", "M3"}:
            continue
        if candidate["location_class"] == "live":
            artifact_roles[candidate["path"]] = {
                "milestone": candidate["milestone"],
                "role": "deliverable",
                "lineage_id": "live",
            }
        else:
            artifact_roles[candidate["path"]] = {
                "milestone": candidate["milestone"],
                "role": "evidence",
                "lineage_id": "archive",
            }
    adjudication = {
        "authority": "user",
        "approved_at": "2026-07-13T21:00:00Z",
        "evidence_path": "reviews/migration_approval.md",
        "evidence_sha256": sha(approval.read_bytes()),
        "primary_lineage": "live",
        "completed_through": boundary,
        "phase_source": matrix["ledger_sources"][0],
        "resolved_holds": [hold["hold_id"] for hold in matrix["holds"]],
        "artifact_roles": artifact_roles,
    }
    path = project / "adjudication.json"
    write_json(path, adjudication)
    return path


def ledger_snapshot(project: Path) -> dict[str, bytes]:
    return {
        path.relative_to(project).as_posix(): path.read_bytes()
        for path in (project / "reviews").glob("*_state.json")
    }


def assert_publication_failure_restores(
    project: Path,
    adjudication: Path,
    *,
    after_durable_write: bool,
) -> None:
    before = ledger_snapshot(project)
    canonical = project / "reviews" / "phase_state.json"

    def interrupted_writer(path: Path, payload: bytes) -> None:
        if path == canonical:
            if after_durable_write:
                migration._atomic_write(path, payload)
            raise OSError(
                "simulated after-durable-write interruption"
                if after_durable_write
                else "simulated before-write interruption"
            )
        migration._atomic_write(path, payload)

    try:
        migration.apply_migration(project, adjudication, atomic_writer=interrupted_writer)
    except OSError as exc:
        assert "interruption" in str(exc)
    else:
        raise AssertionError("publication interruption was not propagated")
    assert ledger_snapshot(project) == before
    migrations = project / "reviews" / ".harness" / "migrations"
    assert not migrations.exists() or not any(migrations.iterdir())
    assert not any(project.parent.glob(f".{project.name}.legacy-migration-*"))

    reapplied = run("--project-root", str(project), "--apply", "--adjudication", str(adjudication))
    assert reapplied.returncode == 0, reapplied.stdout + reapplied.stderr
    assert json.loads(reapplied.stdout)["outcome"] == "migrated"


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

        tier_project = make_project(base / "tier-only", tier_only=True)
        original_ledgers = {
            path.relative_to(tier_project).as_posix(): path.read_bytes()
            for path in (tier_project / "reviews").glob("*_state.json")
        }
        tier_matrix = json.loads(run("--project-root", str(tier_project)).stdout)
        tier_adjudication = approved_adjudication(tier_project, tier_matrix)

        for tier_only in (False, True):
            for after_durable in (False, True):
                crash_project = make_project(
                    base / f"publication-crash-{tier_only}-{after_durable}",
                    tier_only=tier_only,
                )
                crash_matrix = json.loads(run("--project-root", str(crash_project)).stdout)
                crash_adjudication = approved_adjudication(crash_project, crash_matrix)
                assert_publication_failure_restores(
                    crash_project,
                    crash_adjudication,
                    after_durable_write=after_durable,
                )

        interrupted_project = make_project(base / "tier-interrupted", tier_only=True)
        interrupted_matrix = json.loads(run("--project-root", str(interrupted_project)).stdout)
        interrupted_adjudication = approved_adjudication(interrupted_project, interrupted_matrix)
        interrupted_tier = interrupted_project / "reviews" / "tier_state.json"
        interrupted_original = interrupted_tier.read_bytes()

        def fail_commit(path: Path, payload: bytes) -> None:
            if path.name == "commit.json":
                raise OSError("simulated commit-marker interruption")
            migration._atomic_write(path, payload)

        try:
            migration.apply_migration(
                interrupted_project, interrupted_adjudication, atomic_writer=fail_commit
            )
        except OSError as exc:
            assert "commit-marker" in str(exc)
        else:
            raise AssertionError("commit-marker interruption was not propagated")
        assert interrupted_tier.read_bytes() == interrupted_original
        assert not (interrupted_project / "reviews" / "phase_state.json").exists()
        interrupted_migrations = interrupted_project / "reviews" / ".harness" / "migrations"
        assert not interrupted_migrations.exists() or not any(interrupted_migrations.iterdir())

        tier_applied = run("--project-root", str(tier_project), "--apply", "--adjudication", str(tier_adjudication))
        assert tier_applied.returncode == 0, tier_applied.stdout + tier_applied.stderr
        manifest_paths = list((tier_project / "reviews" / ".harness" / "migrations").glob("*/rollback_manifest.json"))
        assert len(manifest_paths) == 1
        manifest = json.loads(manifest_paths[0].read_text(encoding="utf-8"))
        assert manifest["replacement_existed_before"] is False
        current = tier_project / manifest["replacement_path"]
        assert sha(current.read_bytes()) == manifest["replacement_sha256"]
        tier_adjudication_bytes = tier_adjudication.read_bytes()
        tier_adjudication.unlink()
        rolled = run("--project-root", str(tier_project), "--rollback", str(manifest_paths[0]))
        assert rolled.returncode == 0, rolled.stdout + rolled.stderr
        assert not current.exists()
        for relative, payload in original_ledgers.items():
            assert (tier_project / relative).read_bytes() == payload
        migration_dir = manifest_paths[0].parent
        assert not (migration_dir / "commit.json").exists()
        rollback_record = json.loads((migration_dir / "rollback.json").read_text(encoding="utf-8"))
        assert rollback_record["transaction_state"] == "rolled_back"
        tier_adjudication.write_bytes(tier_adjudication_bytes)
        reapplied = run("--project-root", str(tier_project), "--apply", "--adjudication", str(tier_adjudication))
        assert reapplied.returncode == 0, reapplied.stdout + reapplied.stderr
        assert json.loads(reapplied.stdout)["outcome"] == "migrated"
        assert current.is_file() and not (tier_project / "reviews" / "tier_state.json").exists()
        completed.append("rollback_manifest_restores_original_hash")

    assert tuple(completed) == CASES, completed
    print(f"PASS migrate_legacy_milestones_smoketest ({len(completed)} cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
