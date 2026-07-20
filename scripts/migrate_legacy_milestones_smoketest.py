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
    "generic_artifact_candidates_are_unclassified_hints",
    "unrelated_artifact_hint_can_be_explicitly_excluded",
    "archive_live_ambiguity_creates_hold",
    "missing_feedback_is_not_captured_not_invented",
    "array_sections_migrate_to_object",
    "mixed_tier_phase_state_requires_adjudication",
    "inf_m1_m3_archive_live_divergence_creates_holds",
    "inf_array_sections_are_controlled",
    "inf_simultaneous_tier_phase_blocks_apply",
    "inf_feedback_requires_explicit_typed_adjudication",
    "misleading_feedback_filename_cannot_auto_classify",
    "adjudication_can_override_filename_milestone_hint",
    "approved_migration_is_idempotent",
    "rollback_manifest_restores_original_hash",
)


def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", "-S", str(MIGRATOR), *args],
        cwd=ROOT,
        text=True, encoding="utf-8", errors="replace",
        capture_output=True,
        check=False,
    )


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def assert_synthetic_fixture(project: Path, sandbox: Path) -> None:
    """Fail closed before the migrator can be pointed at a non-temporary tree."""
    project_root = project.resolve()
    sandbox_root = sandbox.resolve()
    if project_root == sandbox_root or not project_root.is_relative_to(sandbox_root):
        raise AssertionError(f"fixture escaped its temporary sandbox: {project_root}")


def tree_snapshot(project: Path) -> dict[str, str]:
    return {
        path.relative_to(project).as_posix(): sha(path.read_bytes())
        for path in project.rglob("*") if path.is_file()
    }


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
        milestone = candidate.get("milestone_hint")
        if milestone is None and candidate["path"] == "manuscript/main.md":
            milestone = "M4"
        if milestone not in {"M1", "M2", "M3", "M4", "M5"}:
            artifact_roles[candidate["path"]] = {
                "migration_disposition": "exclude_unrelated",
                "rationale": "Synthetic helper has no milestone evidence for this generic candidate.",
            }
            continue
        if candidate["location_class"] == "live":
            artifact_roles[candidate["path"]] = {
                "migration_disposition": "admit",
                "milestone": milestone,
                "role": "deliverable",
                "lineage_id": "live",
            }
        else:
            artifact_roles[candidate["path"]] = {
                "migration_disposition": "admit",
                "milestone": milestone,
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
        "feedback_adjudications": {},
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
        (project / "manuscript" / "INF3130 Term Paper Chung.tex").write_text(
            "Synthetic venue-named manuscript source.\n", encoding="utf-8"
        )
        (project / "manuscript" / "INF3130 Term Paper Chung.pdf").write_bytes(b"%PDF-synthetic\n")
        (project / "manuscript" / "INF3130 Term Paper Chung.aux").write_text(
            "Synthetic build byproduct.\n", encoding="utf-8"
        )
        (project / "manuscript" / "milestone5_manuscript.aux").write_text(
            "Synthetic milestone-named build byproduct.\n", encoding="utf-8"
        )
        before = {p.relative_to(project).as_posix(): sha(p.read_bytes()) for p in project.rglob("*") if p.is_file()}
        dry = run("--project-root", str(project))
        assert dry.returncode == 0, dry.stdout + dry.stderr
        matrix = json.loads(dry.stdout)
        assert matrix["matrix_version"] == "1.1.0"
        after = {p.relative_to(project).as_posix(): sha(p.read_bytes()) for p in project.rglob("*") if p.is_file()}
        assert before == after
        assert set(("artifact_candidates", "proposed_roles", "lineage_graph", "feedback_classes", "path_failures", "ledger_shape_findings", "holds")) <= set(matrix)
        completed.append("dry_run_writes_nothing")

        by_path = {item["path"]: item for item in matrix["artifact_candidates"]}
        assert by_path["manuscript/main.md"]["milestone_hint"] is None
        assert by_path["manuscript/main.md"]["role_hint"] == "deliverable"
        assert by_path["research_notes/milestone1_project_memo.md"]["milestone_hint"] == "M1"
        assert by_path["manuscript/INF3130 Term Paper Chung.tex"]["milestone_hint"] is None
        assert by_path["manuscript/INF3130 Term Paper Chung.pdf"]["milestone_hint"] is None
        assert "manuscript/INF3130 Term Paper Chung.aux" not in by_path
        assert "manuscript/milestone5_manuscript.aux" not in by_path
        assert all("milestone" not in item for item in matrix["artifact_candidates"])
        assert any(
            hold["code"] == "UNADJUDICATED_ARTIFACT"
            and hold["paths"] == ["manuscript/main.md"]
            for hold in matrix["holds"]
        )
        completed.append("generic_artifact_candidates_are_unclassified_hints")

        excluded_project = make_project(base / "excluded-artifact")
        template = excluded_project / "research_notes" / "outline_template.md"
        template.write_text("# Generic outline template, not a project milestone\n", encoding="utf-8")
        excluded_matrix = json.loads(run("--project-root", str(excluded_project)).stdout)
        excluded_adjudication = approved_adjudication(excluded_project, excluded_matrix)
        excluded_doc = json.loads(excluded_adjudication.read_text(encoding="utf-8"))
        excluded_doc["artifact_roles"]["research_notes/outline_template.md"] = {
            "migration_disposition": "exclude_unrelated",
            "rationale": "This is a reusable template rather than project milestone evidence.",
        }
        write_json(excluded_adjudication, excluded_doc)
        excluded_result = run(
            "--project-root", str(excluded_project), "--apply", "--adjudication", str(excluded_adjudication)
        )
        assert excluded_result.returncode == 0, excluded_result.stdout + excluded_result.stderr
        excluded_ledger = json.loads((excluded_project / "reviews" / "phase_state.json").read_text(encoding="utf-8"))
        assert all(
            item["path"] != "research_notes/outline_template.md"
            for milestone in excluded_ledger["milestone_framework"]["milestones"].values()
            for item in milestone["artifacts"]
        )
        completed.append("unrelated_artifact_hint_can_be_explicitly_excluded")

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

        inf_divergent = make_project(base / "inf-divergent", ambiguous=True)
        assert_synthetic_fixture(inf_divergent, base)
        (inf_divergent / "archive" / "milestone3_archived_outline.md").write_text(
            "# Synthetic archived M3 lineage\n", encoding="utf-8"
        )
        divergent = run("--project-root", str(inf_divergent))
        assert divergent.returncode == 0 and "Traceback" not in divergent.stderr
        divergent_matrix = json.loads(divergent.stdout)
        archive_live_holds = {
            hold["hold_id"]: hold for hold in divergent_matrix["holds"]
            if hold["code"] == "ARCHIVE_LIVE_AMBIGUITY"
        }
        assert set(archive_live_holds) == {"archive-live:M1", "archive-live:M3"}
        assert all(
            {item["location_class"] for item in divergent_matrix["artifact_candidates"] if item["path"] in hold["paths"]}
            == {"archive", "live"}
            for hold in archive_live_holds.values()
        )
        completed.append("inf_m1_m3_archive_live_divergence_creates_holds")

        inf_array = make_project(base / "inf-array")
        assert_synthetic_fixture(inf_array, base)
        array_result = run("--project-root", str(inf_array))
        assert array_result.returncode == 0 and "Traceback" not in (array_result.stdout + array_result.stderr)
        array_matrix = json.loads(array_result.stdout)
        assert {item["code"] for item in array_matrix["ledger_shape_findings"]} == {"ARRAY_SECTIONS"}
        completed.append("inf_array_sections_are_controlled")

        inf_mixed = make_project(base / "inf-mixed", mixed=True)
        assert_synthetic_fixture(inf_mixed, base)
        mixed_dry = run("--project-root", str(inf_mixed))
        assert mixed_dry.returncode == 0 and "Traceback" not in (mixed_dry.stdout + mixed_dry.stderr)
        mixed_matrix = json.loads(mixed_dry.stdout)
        assert any(
            hold["code"] == "MIXED_TIER_PHASE_STATE"
            and hold["paths"] == ["reviews/phase_state.json", "reviews/tier_state.json"]
            for hold in mixed_matrix["holds"]
        )
        mixed_before = tree_snapshot(inf_mixed)
        mixed_apply = run("--project-root", str(inf_mixed), "--apply")
        assert mixed_apply.returncode == 2
        assert "adjudication" in mixed_apply.stderr.lower()
        assert "Traceback" not in (mixed_apply.stdout + mixed_apply.stderr)
        assert tree_snapshot(inf_mixed) == mixed_before
        completed.append("inf_simultaneous_tier_phase_blocks_apply")

        inf_feedback = make_project(base / "inf-feedback")
        assert_synthetic_fixture(inf_feedback, base)
        guides = inf_feedback / "resources_and_guides"
        guides.mkdir()
        (guides / "Feedback Milestone 3.md").write_text(
            "Synthetic direct M3 feedback marker.\n", encoding="utf-8"
        )
        (guides / "milestone1_principles_retrospective.md").write_text(
            "Synthetic later audit applied to M1.\n", encoding="utf-8"
        )
        receipt_log = inf_feedback / "reviews" / "historical_receipt_log.md"
        receipt_log.write_text(
            "Synthetic retained receipt evidence for the two fixture feedback records.\n", encoding="utf-8"
        )
        feedback_result = run("--project-root", str(inf_feedback))
        assert feedback_result.returncode == 0 and "Traceback" not in feedback_result.stderr
        feedback_matrix = json.loads(feedback_result.stdout)
        assert feedback_matrix["feedback_classes"] == {key: [] for key in migration.FEEDBACK_CLASSES}
        assert feedback_matrix["feedback_status"] == "not captured under prior contract"
        candidates = {item["path"]: item for item in feedback_matrix["feedback_candidates"]}
        assert set(candidates) == {
            "resources_and_guides/Feedback Milestone 3.md",
            "resources_and_guides/milestone1_principles_retrospective.md",
        }
        assert all(item["evidence_class"] is None for item in candidates.values())
        feedback_adjudication = approved_adjudication(inf_feedback, feedback_matrix)
        adjudication_doc = json.loads(feedback_adjudication.read_text(encoding="utf-8"))
        common = {
            "migration_disposition": "admit",
            "source_actor": "Prof. Darlington",
            "source_authority": "advisor",
            "received_at": "2026-07-13T20:30:00Z",
            "contemporaneity_evidence_path": "reviews/historical_receipt_log.md",
            "contemporaneity_evidence_sha256": sha(receipt_log.read_bytes()),
            "lineage_id": "live",
            "blocking": False,
            "disposition": "informational",
            "rationale": "Explicit synthetic migration adjudication.",
            "successor_effect": "Preserve the historical classification without inferring approval.",
        }
        adjudication_doc["feedback_adjudications"] = {
            "resources_and_guides/Feedback Milestone 3.md": {
                **common,
                "feedback_id": "legacy-direct-m3",
                "evidence_class": "direct_milestone_feedback",
                "source_milestone": "M3",
                "target_milestone": "M3",
            },
            "resources_and_guides/milestone1_principles_retrospective.md": {
                **common,
                "feedback_id": "legacy-retro-m1",
                "evidence_class": "retrospective_application",
                "source_milestone": "M3",
                "target_milestone": "M1",
            },
        }
        write_json(feedback_adjudication, adjudication_doc)
        migrated_feedback = run(
            "--project-root", str(inf_feedback), "--apply", "--adjudication", str(feedback_adjudication)
        )
        assert migrated_feedback.returncode == 0, migrated_feedback.stdout + migrated_feedback.stderr
        feedback_ledger = json.loads((inf_feedback / "reviews" / "phase_state.json").read_text(encoding="utf-8"))
        milestones = feedback_ledger["milestone_framework"]["milestones"]
        assert [item["evidence_class"] for item in milestones["M3"]["feedback_records"]] == [
            "direct_milestone_feedback"
        ]
        assert [item["evidence_class"] for item in milestones["M1"]["feedback_records"]] == [
            "retrospective_application"
        ]
        direct_record = milestones["M3"]["feedback_records"][0]
        assert direct_record["source_actor"] == "Prof. Darlington"
        assert direct_record["source_authority"] == "advisor"
        assert direct_record["contemporaneity_evidence_path"] == "reviews/historical_receipt_log.md"
        assert direct_record["contemporaneity_evidence_sha256"] == sha(receipt_log.read_bytes())
        migration_events = feedback_ledger["milestone_framework"]["events"]
        assert migration_events
        assert all(event["timestamp"] == adjudication_doc["approved_at"] for event in migration_events)
        assert all(event["actor"] == "planner" for event in migration_events)
        assert all(event["authority"] == adjudication_doc["authority"] for event in migration_events)
        completed.append("inf_feedback_requires_explicit_typed_adjudication")

        misleading = make_project(base / "misleading-feedback")
        misleading_guides = misleading / "resources_and_guides"
        misleading_guides.mkdir()
        misleading_path = misleading_guides / "milestone1_retrospective_feedback.md"
        misleading_path.write_text("Synthetic ambiguous feedback marker.\n", encoding="utf-8")
        (misleading_guides / "directives.md").write_text(
            "Synthetic project directives that are not attributable feedback.\n", encoding="utf-8"
        )
        (misleading_guides / "milestone1_principles_audit.md").write_text(
            "Synthetic legacy principles audit with unproven class.\n", encoding="utf-8"
        )
        misleading_matrix = json.loads(run("--project-root", str(misleading)).stdout)
        assert misleading_matrix["feedback_classes"] == {key: [] for key in migration.FEEDBACK_CLASSES}
        item = next(
            candidate for candidate in misleading_matrix["feedback_candidates"]
            if candidate["path"] == "resources_and_guides/milestone1_retrospective_feedback.md"
        )
        assert item["evidence_class"] is None
        audit_item = next(
            candidate for candidate in misleading_matrix["feedback_candidates"]
            if candidate["path"] == "resources_and_guides/milestone1_principles_audit.md"
        )
        assert audit_item["evidence_class"] is None
        assert any(
            hold["code"] == "UNADJUDICATED_FEEDBACK" and item["path"] in hold["paths"]
            for hold in misleading_matrix["holds"]
        )
        unavailable_adjudication = approved_adjudication(misleading, misleading_matrix)
        unavailable_doc = json.loads(unavailable_adjudication.read_text(encoding="utf-8"))
        unavailable_doc["feedback_adjudications"] = {
            candidate["path"]: {
                "migration_disposition": (
                    "exclude_unrelated" if candidate["path"].endswith("directives.md")
                    else "unavailable_under_prior_contract"
                ),
                "rationale": (
                    "This is project policy, not feedback."
                    if candidate["path"].endswith("directives.md")
                    else "Actor, date, and class cannot be proven from retained legacy evidence."
                ),
            }
            for candidate in misleading_matrix["feedback_candidates"]
        }
        write_json(unavailable_adjudication, unavailable_doc)
        unavailable_result = run(
            "--project-root", str(misleading), "--apply", "--adjudication", str(unavailable_adjudication)
        )
        assert unavailable_result.returncode == 0, unavailable_result.stdout + unavailable_result.stderr
        unavailable_ledger = json.loads((misleading / "reviews" / "phase_state.json").read_text(encoding="utf-8"))
        assert all(
            not milestone["feedback_records"]
            for milestone in unavailable_ledger["milestone_framework"]["milestones"].values()
        )
        unavailable_report = next((misleading / "reviews" / ".harness" / "migrations").glob("*/migration_report.json"))
        unavailable_report_doc = json.loads(unavailable_report.read_text(encoding="utf-8"))
        assert unavailable_report_doc["feedback_status"] == "not captured under prior contract"
        assert unavailable_report_doc["inventory_outcomes"]["unavailable_feedback"] == sorted(
            candidate["path"] for candidate in misleading_matrix["feedback_candidates"]
            if not candidate["path"].endswith("directives.md")
        )
        assert unavailable_report_doc["inventory_outcomes"]["excluded_feedback"] == [
            "resources_and_guides/directives.md"
        ]
        completed.append("misleading_feedback_filename_cannot_auto_classify")

        remapped = make_project(base / "remapped-artifact")
        (remapped / "research_notes" / "milestone1_project_memo.md").unlink()
        misleading_memo = remapped / "research_notes" / "milestone2_project_memo.md"
        misleading_memo.write_text("# Synthetic memo with misleading milestone token\n", encoding="utf-8")
        remapped_matrix = json.loads(run("--project-root", str(remapped)).stdout)
        remapped_adjudication = approved_adjudication(remapped, remapped_matrix)
        remapped_doc = json.loads(remapped_adjudication.read_text(encoding="utf-8"))
        assert next(
            item for item in remapped_matrix["artifact_candidates"] if item["path"] == "research_notes/milestone2_project_memo.md"
        )["milestone_hint"] == "M2"
        remapped_doc["artifact_roles"]["research_notes/milestone2_project_memo.md"]["milestone"] = "M1"
        write_json(remapped_adjudication, remapped_doc)
        remapped_result = run(
            "--project-root", str(remapped), "--apply", "--adjudication", str(remapped_adjudication)
        )
        assert remapped_result.returncode == 0, remapped_result.stdout + remapped_result.stderr
        remapped_ledger = json.loads((remapped / "reviews" / "phase_state.json").read_text(encoding="utf-8"))
        m1_paths = [
            item["path"]
            for item in remapped_ledger["milestone_framework"]["milestones"]["M1"]["artifacts"]
            if item["role"] == "deliverable"
        ]
        assert m1_paths == ["research_notes/milestone2_project_memo.md"]
        completed.append("adjudication_can_override_filename_milestone_hint")

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
