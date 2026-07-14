#!/usr/bin/env python3
"""Adversarial refusal tests for the guarded legacy migration."""

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
            "artifact_roles": {},
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
        replacement = project / "reviews" / "phase_state.json"
        replacement.write_bytes(replacement.read_bytes() + b" ")
        changed_hash = sha(replacement)
        refused_rollback = run("--project-root", str(project), "--rollback", str(manifest))
        assert refused_rollback.returncode == 2 and "replacement hash changed" in refused_rollback.stderr.lower()
        assert sha(replacement) == changed_hash

    print("PASS migrate_legacy_milestones_adversarial_smoketest (8 refusals)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
