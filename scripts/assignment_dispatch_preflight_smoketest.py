#!/usr/bin/env python3
"""Regression tests for the assignment dispatch/write preflight."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "assignment_process_gate.py"
PREFLIGHT = ROOT / "scripts" / "assignment_dispatch_preflight.py"
PROFILE = ROOT / "references" / "policies" / "course_essay_milestones.v1.json"
FIXTURES = ROOT / "scripts" / "fixtures" / "assignment_dispatch_preflight"
PLANNER = ROOT / "agents" / "planner.md"
GENERATOR = ROOT / "agents" / "generator.md"
RUN_DRAFT = ROOT / "skills" / "run-draft" / "SKILL.md"
RUN_PHASE_1 = ROOT / "skills" / "run-phase-1" / "SKILL.md"
RUN_FINALIZE = ROOT / "skills" / "run-finalize" / "SKILL.md"
RUN_PHASE_4 = ROOT / "skills" / "run-phase-4" / "SKILL.md"
ORCHESTRATION = ROOT / "references" / "AGENT_ORCHESTRATION.md"
BOOTSTRAP = ROOT / "references" / "PROJECT_BOOTSTRAP.md"
MANIFEST = ROOT / "references" / "MANIFEST.md"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(project: Path) -> dict[str, bytes]:
    return {
        path.relative_to(project).as_posix(): path.read_bytes()
        for path in project.rglob("*")
        if path.is_file()
    }


def create_project(root: Path) -> tuple[Path, Path]:
    root.mkdir(parents=True)
    source = root / "course-assignment.pdf"
    source.write_bytes(b"synthetic assignment brief\n")
    reviews = root / "reviews"
    reviews.mkdir(parents=True)
    contract = {
        "contract_version": "1.0.0",
        "status": "resolved",
        "profile_id": "course-essay-four-milestones-v1",
        "profile_path": "references/policies/course_essay_milestones.v1.json",
        "profile_sha256": sha256(PROFILE),
        "assignment_source": {
            "path": str(source),
            "sha256": sha256(source),
            "authority": "instructor",
        },
        "assigned_sequence": ["M1", "M2", "M3", "M4", "FINAL"],
        "framework_mapping": {
            "M1": "M1",
            "M2": "M2",
            "M3": "M3",
            "M4": "M4",
            "FINAL": "M5",
        },
        "professor_copy_policy": "author_controlled_unless_explicitly_requested",
    }
    (reviews / "assignment_contract.json").write_text(
        json.dumps(contract, indent=2) + "\n", encoding="utf-8"
    )
    phase_state = {
        "milestone_framework": {
            "mode": "native",
            "primary_lineage_id": "live",
            "milestones": {
                key: {"status": "not_started"}
                for key in ("M1", "M2", "M3", "M4", "M5")
            },
        }
    }
    (reviews / "phase_state.json").write_text(
        json.dumps(phase_state, indent=2) + "\n", encoding="utf-8"
    )
    receipt = (
        reviews
        / ".harness"
        / "assignment"
        / "ready"
        / "gate_receipt_M1_20260715T000000Z.json"
    )
    return reviews, receipt


def emit_receipt(project: Path, receipt: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(GATE),
            "--project-root",
            str(project),
            "--stage",
            "draft",
            "--target-milestone",
            "M1",
            "--emit-receipt",
            str(receipt),
        ],
        text=True, encoding="utf-8", errors="replace",
        capture_output=True,
        check=False,
    )


def run_preflight(
    project: Path,
    receipt: Path,
    expected_target: str,
    write_path: str = "research_notes/project_memo.md",
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(PREFLIGHT),
            "--project-root",
            str(project),
            "--receipt",
            str(receipt),
            "--expected-target",
            expected_target,
            "--consumer",
            "planner",
            "--write-path",
            write_path,
        ],
        text=True, encoding="utf-8", errors="replace",
        capture_output=True,
        check=False,
    )


def main() -> int:
    if not PREFLIGHT.is_file():
        raise AssertionError("assignment_dispatch_preflight.py is missing")

    planner_contract = PLANNER.read_text(encoding="utf-8")
    assert "assignment_gate_receipt: <path>" in planner_contract
    assert "assignment_gate_target: <T>" in planner_contract
    assert "assignment_dispatch_preflight.py" in planner_contract
    assert "--emit-receipt" in planner_contract
    assert "--consumer planner" in planner_contract
    assert "--write-path" in planner_contract
    assert "assignment_receipt_invalidate.py" in planner_contract
    assert "status: consumed" not in planner_contract
    phase_1_contract = RUN_PHASE_1.read_text(encoding="utf-8")
    assert "assignment_dispatch_preflight.py" in phase_1_contract
    assert "ph1_draft_completion.md" in phase_1_contract
    assert "protocol violation" in phase_1_contract
    assert "assignment_writer_commit.py" in RUN_DRAFT.read_text(encoding="utf-8")
    assert "assignment_writer_commit.py" in RUN_PHASE_4.read_text(encoding="utf-8")
    assert "assignment_writer_commit.py" in RUN_FINALIZE.read_text(encoding="utf-8")
    orchestration_contract = ORCHESTRATION.read_text(encoding="utf-8")
    assert "assignment_gate_receipt: <reserved-path>" in orchestration_contract
    assert "assignment_gate_target: <T>" in orchestration_contract
    assert "assignment_dispatch_preflight.py" in orchestration_contract
    generator_contract = GENERATOR.read_text(encoding="utf-8")
    assert "assignment_writer_commit.py" in generator_contract
    assert "reviews/.harness/assignment/staged/<receipt_id>/" in generator_contract
    assert "reserved" in generator_contract
    assert "direct final-path write" in generator_contract
    bootstrap_contract = BOOTSTRAP.read_text(encoding="utf-8")
    assert "APG-CONTRACT-MISSING" in bootstrap_contract
    assert "assignment_source.path" in bootstrap_contract
    assert "assignment_source.sha256" in bootstrap_contract
    assert "profile_sha256" in bootstrap_contract
    assert "2026-07-14_first-principles-RE-essay-fresh" in bootstrap_contract
    assert "memo only" in bootstrap_contract
    manifest_contract = MANIFEST.read_text(encoding="utf-8")
    assert "schemas/assignment_gate_receipt.schema.json" in manifest_contract
    assert "templates/assignment_gate_receipt.json" in manifest_contract
    assert "scripts/assignment_dispatch_preflight.py" in manifest_contract
    assert "scripts/assignment_process_gate.py" in manifest_contract
    assert "scripts/assignment_writer_commit.py" in manifest_contract
    assert "scripts/assignment_receipt_invalidate.py" in manifest_contract
    assert "scripts/assignment_receipt_recover.py" in manifest_contract

    fresh_skip = FIXTURES / "fresh_skip_gate"
    if not fresh_skip.is_dir():
        raise AssertionError("fresh-skip-gate regression fixture is missing")
    assert (fresh_skip / "reviews" / "phase_state.json").is_file()
    assert (fresh_skip / "manuscript" / "main.md").is_file()
    assert not (fresh_skip / "reviews" / "assignment_contract.json").exists()
    fresh_receipt = (
        fresh_skip
        / "reviews"
        / ".harness"
        / "assignment"
        / "ready"
        / "gate_receipt_M1_missing.json"
    )
    assert not fresh_receipt.exists()
    fresh_before = snapshot(fresh_skip)
    fresh_blocked = run_preflight(fresh_skip, fresh_receipt, "M1")
    assert fresh_blocked.returncode == 4, fresh_blocked.stdout + fresh_blocked.stderr
    assert "APG-RECEIPT-MISSING" in fresh_blocked.stdout
    assert "APG-DISPATCH-REFUSED" in fresh_blocked.stdout
    assert snapshot(fresh_skip) == fresh_before

    wrong_target_fixture = FIXTURES / "wrong_target_m4"
    if not wrong_target_fixture.is_dir():
        raise AssertionError("wrong-target regression fixture is missing")
    assert (wrong_target_fixture / "reviews" / "assignment_contract.json").is_file()
    wrong_target_receipt = (
        wrong_target_fixture
        / "reviews"
        / ".harness"
        / "assignment"
        / "gate_receipt_M4_fixture.json"
    )
    assert wrong_target_receipt.is_file()
    wrong_target_before = snapshot(wrong_target_fixture)
    wrong_target_blocked = run_preflight(
        wrong_target_fixture, wrong_target_receipt, "M1"
    )
    assert wrong_target_blocked.returncode == 4, (
        wrong_target_blocked.stdout + wrong_target_blocked.stderr
    )
    assert "APG-RECEIPT-PATH-INVALID" in wrong_target_blocked.stdout
    assert "APG-DISPATCH-REFUSED" in wrong_target_blocked.stdout
    assert snapshot(wrong_target_fixture) == wrong_target_before

    with tempfile.TemporaryDirectory() as temp:
        project = Path(temp) / "preflight-project"
        reviews, receipt = create_project(project)

        before_missing = snapshot(project)
        missing = run_preflight(project, receipt, "M1")
        assert missing.returncode == 4, missing.stdout + missing.stderr
        assert "APG-RECEIPT-MISSING" in missing.stdout, missing.stdout + missing.stderr
        assert "APG-DISPATCH-REFUSED" in missing.stdout, missing.stdout + missing.stderr
        assert snapshot(project) == before_missing, "failed preflight must not write project files"

        emitted = emit_receipt(project, receipt)
        assert emitted.returncode == 0, emitted.stdout + emitted.stderr
        contract_before = (reviews / "assignment_contract.json").read_bytes()
        phase_before = (reviews / "phase_state.json").read_bytes()
        ready = run_preflight(project, receipt.relative_to(project), "M1")
        assert ready.returncode == 0, ready.stdout + ready.stderr
        assert "READY assignment-dispatch target=M1" in ready.stdout
        reserved = receipt.parent.parent / "reserved" / receipt.name
        assert not receipt.exists() and reserved.is_file(), "preflight must atomically reserve READY"
        assert (reviews / "assignment_contract.json").read_bytes() == contract_before
        assert (reviews / "phase_state.json").read_bytes() == phase_before

        copied_receipt = project / "gate_receipt_M1_copied.json"
        copied_receipt.write_bytes(reserved.read_bytes())
        wrong_path = run_preflight(project, copied_receipt, "M1")
        assert wrong_path.returncode == 4, wrong_path.stdout + wrong_path.stderr
        assert "APG-RECEIPT-PATH-INVALID" in wrong_path.stdout
        assert "APG-DISPATCH-REFUSED" in wrong_path.stdout
        replay = run_preflight(project, receipt, "M1")
        assert replay.returncode == 4, replay.stdout + replay.stderr
        assert "APG-RECEIPT-RESERVED" in replay.stdout

    with tempfile.TemporaryDirectory() as temp:
        project = Path(temp) / "wrong-target-project"
        _, receipt = create_project(project)
        emitted = emit_receipt(project, receipt)
        assert emitted.returncode == 0, emitted.stdout + emitted.stderr
        wrong_target = run_preflight(project, receipt, "M2")
        assert wrong_target.returncode == 4, wrong_target.stdout + wrong_target.stderr
        assert "APG-RECEIPT-TARGET-MISMATCH" in wrong_target.stdout

    with tempfile.TemporaryDirectory() as temp:
        project = Path(temp) / "stale-project"
        reviews, receipt = create_project(project)
        emitted = emit_receipt(project, receipt)
        assert emitted.returncode == 0, emitted.stdout + emitted.stderr
        phase_path = reviews / "phase_state.json"
        phase = json.loads(phase_path.read_text(encoding="utf-8"))
        phase["milestone_framework"]["milestones"]["M1"]["status"] = "in_progress"
        phase_path.write_text(json.dumps(phase, indent=2) + "\n", encoding="utf-8")
        stale = run_preflight(project, receipt, "M1")
        assert stale.returncode == 4, stale.stdout + stale.stderr
        assert "APG-RECEIPT-STALE" in stale.stdout

    with tempfile.TemporaryDirectory() as temp:
        project = Path(temp) / "terminal-state-project"
        _, receipt = create_project(project)
        emitted = emit_receipt(project, receipt)
        assert emitted.returncode == 0, emitted.stdout + emitted.stderr
        consumed_path = receipt.parent.parent / "consumed" / receipt.name
        consumed_path.parent.mkdir(parents=True)
        receipt.replace(consumed_path)
        consumed = run_preflight(project, receipt, "M1")
        assert consumed.returncode == 4, consumed.stdout + consumed.stderr
        assert "APG-RECEIPT-CONSUMED" in consumed.stdout
        invalidated_path = consumed_path.parent.parent / "invalidated" / receipt.name
        invalidated_path.parent.mkdir(parents=True, exist_ok=True)
        consumed_path.replace(invalidated_path)
        invalidated = run_preflight(project, receipt, "M1")
        assert invalidated.returncode == 4, invalidated.stdout + invalidated.stderr
        assert "APG-RECEIPT-INVALID" in invalidated.stdout

    with tempfile.TemporaryDirectory() as temp:
        project = Path(temp) / "contract-removed-project"
        reviews, receipt = create_project(project)
        emitted = emit_receipt(project, receipt)
        assert emitted.returncode == 0, emitted.stdout + emitted.stderr
        (reviews / "assignment_contract.json").unlink()
        before_contract_failure = snapshot(project)
        no_contract = run_preflight(project, receipt, "M1")
        assert no_contract.returncode == 4, no_contract.stdout + no_contract.stderr
        assert "APG-CONTRACT-MISSING" in no_contract.stdout
        assert "APG-DISPATCH-REFUSED" in no_contract.stdout
        assert snapshot(project) == before_contract_failure

    print("OK assignment_dispatch_preflight_smoketest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
