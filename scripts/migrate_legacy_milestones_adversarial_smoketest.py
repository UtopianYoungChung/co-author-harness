#!/usr/bin/env python3
"""Adversarial refusal tests for the guarded legacy migration."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATOR = ROOT / "scripts" / "migrate_legacy_milestones.py"
sys.path.insert(0, str(ROOT / "scripts"))
import migrate_legacy_milestones as migration


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-I", "-S", str(MIGRATOR), *args], cwd=ROOT, text=True, capture_output=True, check=False)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="legacy-migration-adversarial-") as directory:
        project = Path(directory) / "project"
        (project / "reviews").mkdir(parents=True)
        (project / "reviews" / "phase_state.json").write_text("{not json", encoding="utf-8")
        malformed = run("--project-root", str(project))
        assert malformed.returncode == 2 and "json" in malformed.stderr.lower()

        write_json(project / "reviews" / "phase_state.json", {
            "schema_version": "0.7.4",
            "manuscript_id": "adversarial",
            "default_final_phase": "Ph4",
            "terminal_phase_reached": False,
            "sections": {"manuscript/main.md": {
                "current_phase": "Ph1",
                "phase_entry_log": [{
                    "prev_phase": None, "new_phase": "Ph1", "trigger": "initial_dispatch",
                    "actor": "planner", "notes": "Fixture.",
                    "timestamp": "2026-07-13T20:00:00Z", "model_used": None,
                }],
            }},
        })
        write_json(project / "reviews" / "tier_state.json", {
            "schema_version": "0.7.3",
            "manuscript_id": "adversarial",
            "default_final_phase": "Ph4",
            "terminal_phase_reached": False,
            "sections": {"manuscript/main.md": {
                "current_phase": "Ph1",
                "phase_entry_log": [{
                    "prev_phase": None, "new_phase": "Ph1", "trigger": "initial_dispatch",
                    "actor": "planner", "notes": "Tier fixture selected only by adjudication.",
                    "timestamp": "2026-07-13T20:00:00Z", "model_used": None,
                }],
            }},
        })
        outside = Path(directory) / "outside.json"
        outside.write_text("{}\n", encoding="utf-8")
        escaped = run("--project-root", str(project), "--apply", "--adjudication", str(outside))
        assert escaped.returncode == 2 and "contained" in escaped.stderr.lower()

        (project / "archive").mkdir()
        (project / "manuscript").mkdir()
        (project / "archive" / "milestone1_memo.md").write_text("archive\n", encoding="utf-8")
        (project / "manuscript" / "milestone1_memo.md").write_text("live\n", encoding="utf-8")
        approval = project / "reviews" / "migration_approval.md"
        approval.write_text("Approved by user.\n", encoding="utf-8")
        matrix = json.loads(run("--project-root", str(project)).stdout)
        adjudication = project / "adjudication.json"
        base = {
            "authority": "user",
            "approved_at": "2026-07-13T21:00:00Z",
            "evidence_path": "reviews/migration_approval.md",
            "evidence_sha256": sha(approval),
            "primary_lineage": "live",
            "completed_through": "M1",
            "phase_source": "reviews/phase_state.json",
            "resolved_holds": [],
            "artifact_roles": {
                "archive/milestone1_memo.md": {
                    "milestone": "M1", "role": "evidence", "lineage_id": "archive",
                },
                "manuscript/milestone1_memo.md": {
                    "milestone": "M1", "role": "deliverable", "lineage_id": "live",
                },
            },
        }
        write_json(adjudication, base)
        original_hash = sha(project / "reviews" / "phase_state.json")
        unresolved = run("--project-root", str(project), "--apply", "--adjudication", str(adjudication))
        assert unresolved.returncode == 2 and "holds" in unresolved.stderr.lower()
        assert sha(project / "reviews" / "phase_state.json") == original_hash

        base["resolved_holds"] = [{}]
        write_json(adjudication, base)
        malformed_holds = run("--project-root", str(project), "--apply", "--adjudication", str(adjudication))
        assert malformed_holds.returncode == 2 and "holds" in malformed_holds.stderr.lower()

        base["resolved_holds"] = [item["hold_id"] for item in matrix["holds"]]
        valid_roles = json.loads(json.dumps(base["artifact_roles"]))

        base["artifact_roles"] = {}
        write_json(adjudication, base)
        empty_roles = run("--project-root", str(project), "--apply", "--adjudication", str(adjudication))
        assert empty_roles.returncode == 2 and "deliverable" in empty_roles.stderr.lower()

        base["artifact_roles"] = json.loads(json.dumps(valid_roles))
        base["primary_lineage"] = "arbitrary"
        write_json(adjudication, base)
        arbitrary_lineage = run("--project-root", str(project), "--apply", "--adjudication", str(adjudication))
        assert arbitrary_lineage.returncode == 2 and "primary_lineage" in arbitrary_lineage.stderr.lower()

        base["primary_lineage"] = "live"
        base["phase_source"] = "reviews/missing.json"
        write_json(adjudication, base)
        bad_phase_source = run("--project-root", str(project), "--apply", "--adjudication", str(adjudication))
        assert bad_phase_source.returncode == 2 and "phase_source" in bad_phase_source.stderr.lower()

        base["phase_source"] = "reviews/phase_state.json"
        base["artifact_roles"]["manuscript/milestone1_memo.md"]["milestone"] = "M2"
        write_json(adjudication, base)
        wrong_milestone = run("--project-root", str(project), "--apply", "--adjudication", str(adjudication))
        assert wrong_milestone.returncode == 2 and "discovered milestone" in wrong_milestone.stderr.lower()

        base["artifact_roles"] = json.loads(json.dumps(valid_roles))
        del base["artifact_roles"]["archive/milestone1_memo.md"]
        write_json(adjudication, base)
        incomplete_hold = run("--project-root", str(project), "--apply", "--adjudication", str(adjudication))
        assert incomplete_hold.returncode == 2 and "hold paths" in incomplete_hold.stderr.lower()

        base["artifact_roles"] = json.loads(json.dumps(valid_roles))
        base["completed_through"] = "M2"
        write_json(adjudication, base)
        incomplete_boundary = run("--project-root", str(project), "--apply", "--adjudication", str(adjudication))
        assert incomplete_boundary.returncode == 2 and "completed_through" in incomplete_boundary.stderr.lower()

        base["completed_through"] = "M1"
        base["approved_at"] = "2026-02-30T21:00:00Z"
        write_json(adjudication, base)
        bad_date = run("--project-root", str(project), "--apply", "--adjudication", str(adjudication))
        assert bad_date.returncode == 2 and "real date" in bad_date.stderr.lower()

        base["approved_at"] = "2026-07-13T21:00:00Z"
        base["evidence_sha256"] = "0" * 64
        write_json(adjudication, base)
        bad_evidence = run("--project-root", str(project), "--apply", "--adjudication", str(adjudication))
        assert bad_evidence.returncode == 2 and "path/hash" in bad_evidence.stderr.lower()

        base["evidence_sha256"] = sha(approval)
        write_json(adjudication, base)

        unexpected_project = Path(directory) / "unexpected-concurrent"
        shutil.copytree(project, unexpected_project)
        unexpected_adjudication = unexpected_project / "adjudication.json"
        unexpected_canonical = unexpected_project / "reviews" / "phase_state.json"
        concurrent_payload = b'{"concurrent":"changed"}\n'

        def unexpected_writer(path: Path, payload: bytes) -> None:
            if path == unexpected_canonical:
                migration._atomic_write(path, concurrent_payload)
                raise OSError("simulated unexpected concurrent bytes")
            migration._atomic_write(path, payload)

        try:
            migration.apply_migration(
                unexpected_project, unexpected_adjudication, atomic_writer=unexpected_writer
            )
        except migration.MigrationError as exc:
            assert "concurrent" in str(exc).lower() and "recovery evidence" in str(exc).lower()
        else:
            raise AssertionError("unexpected concurrent bytes were not a controlled refusal")
        assert unexpected_canonical.read_bytes() == concurrent_payload
        unexpected_migrations = list(
            (unexpected_project / "reviews" / ".harness" / "migrations").glob("*")
        )
        assert len(unexpected_migrations) == 1
        assert (unexpected_migrations[0] / "migration_report.json").is_file()
        assert (unexpected_migrations[0] / "rollback_manifest.json").is_file()
        assert not (unexpected_migrations[0] / "commit.json").exists()
        assert (unexpected_project / "reviews" / "tier_state.json").is_file()

        def fail_at_authority(path: Path, payload: bytes) -> None:
            if path == project / "reviews" / "phase_state.json":
                raise OSError("simulated publication interruption")
            migration._atomic_write(path, payload)

        try:
            migration.apply_migration(project, adjudication, atomic_writer=fail_at_authority)
        except OSError as exc:
            assert "simulated publication interruption" in str(exc)
        else:
            raise AssertionError("simulated publication interruption was not propagated")
        assert sha(project / "reviews" / "phase_state.json") == original_hash
        migrations = project / "reviews" / ".harness" / "migrations"
        assert not migrations.exists() or not any(migrations.iterdir())

        applied = run("--project-root", str(project), "--apply", "--adjudication", str(adjudication))
        assert applied.returncode == 0, applied.stdout + applied.stderr
        manifest = next((project / "reviews" / ".harness" / "migrations").glob("*/rollback_manifest.json"))
        migration_dir = manifest.parent
        replacement = project / "reviews" / "phase_state.json"

        manifest_doc = json.loads(manifest.read_text(encoding="utf-8"))
        tier_entry = next(item for item in manifest_doc["originals"] if item["original_path"] == "reviews/tier_state.json")
        commit_path = migration_dir / "commit.json"
        commit_bytes = commit_path.read_bytes()
        commit_path.unlink()
        (project / "reviews" / "tier_state.json").write_bytes((project / tier_entry["archive_path"]).read_bytes())
        crash_recovered = run("--project-root", str(project), "--apply", "--adjudication", str(adjudication))
        assert crash_recovered.returncode == 0, crash_recovered.stdout + crash_recovered.stderr
        assert json.loads(crash_recovered.stdout)["outcome"] == "recovered_committed"
        assert not (project / "reviews" / "tier_state.json").exists()
        assert commit_path.read_bytes() == commit_bytes

        (project / "reviews" / "tier_state.json").write_bytes((project / tier_entry["archive_path"]).read_bytes())
        stale_fast_path = run("--project-root", str(project), "--apply", "--adjudication", str(adjudication))
        assert stale_fast_path.returncode == 2 and "coexist" in stale_fast_path.stderr.lower()
        assert (project / "reviews" / "tier_state.json").is_file()
        (project / "reviews" / "tier_state.json").unlink()

        missing_adjudication = run("--project-root", str(project), "--apply", "--adjudication", str(project / "missing.json"))
        assert missing_adjudication.returncode == 2 and "adjudication" in missing_adjudication.stderr.lower()

        different_adjudication = project / "different-adjudication.json"
        different_adjudication.write_bytes(adjudication.read_bytes() + b" ")
        different = run("--project-root", str(project), "--apply", "--adjudication", str(different_adjudication))
        assert different.returncode == 2 and "adjudication" in different.stderr.lower()

        commit_path.unlink()
        report_path = migration_dir / "migration_report.json"
        report_bytes = report_path.read_bytes()
        report_path.write_text("{}\n", encoding="utf-8")
        bad_report = run("--project-root", str(project), "--apply", "--adjudication", str(adjudication))
        assert bad_report.returncode == 2 and "report" in bad_report.stderr.lower()
        assert not commit_path.exists()
        report_path.write_bytes(report_bytes)

        manifest_bytes = manifest.read_bytes()
        manifest_doc = json.loads(manifest_bytes)
        archive_path = project / manifest_doc["originals"][0]["archive_path"]
        archive_bytes = archive_path.read_bytes()
        archive_path.write_bytes(archive_bytes + b"tamper")
        bad_archive = run("--project-root", str(project), "--apply", "--adjudication", str(adjudication))
        assert bad_archive.returncode == 2 and "archive" in bad_archive.stderr.lower()
        assert not commit_path.exists()
        archive_path.write_bytes(archive_bytes)

        manifest.write_text("{}\n", encoding="utf-8")
        bad_manifest = run("--project-root", str(project), "--apply", "--adjudication", str(adjudication))
        assert bad_manifest.returncode == 2 and "manifest" in bad_manifest.stderr.lower()
        assert not commit_path.exists()
        manifest.write_bytes(manifest_bytes)

        recovered = run("--project-root", str(project), "--apply", "--adjudication", str(adjudication))
        assert recovered.returncode == 0, recovered.stdout + recovered.stderr
        assert json.loads(recovered.stdout)["outcome"] == "recovered_committed"
        assert commit_path.read_bytes() == commit_bytes

        commit_path.write_text("{}\n", encoding="utf-8")
        bad_commit = run("--project-root", str(project), "--apply", "--adjudication", str(adjudication))
        assert bad_commit.returncode == 2 and "commit" in bad_commit.stderr.lower()
        commit_path.write_bytes(commit_bytes)

        replacement.write_bytes(replacement.read_bytes() + b" ")
        changed_hash = sha(replacement)
        refused_rollback = run("--project-root", str(project), "--rollback", str(manifest))
        assert refused_rollback.returncode == 2 and "replacement hash changed" in refused_rollback.stderr.lower()
        assert sha(replacement) == changed_hash

    print("PASS migrate_legacy_milestones_adversarial_smoketest (21 refusals)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
