#!/usr/bin/env python3
"""Public FINAL/M5 publication and state-last terminal-close regression."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from assignment_fixture_support import write_valid_contract
from assignment_milestone_checkpoint_smoketest import (
    approval_input, checkpoint_input, converge_m4_fixture,
    m4_acceptance_policy_input, publish,
)
from assignment_milestone_transaction import (
    MilestoneTransactionError, accept as accept_transaction,
)
from full_run_semantic_bypass_smoketest import BOUND, _findings_report, valid_project


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "scripts" / "native_project_bootstrap.py"
GATE = ROOT / "scripts" / "assignment_process_gate.py"
PREFLIGHT = ROOT / "scripts" / "assignment_dispatch_preflight.py"
WRITER = ROOT / "scripts" / "assignment_writer_commit.py"
CHECKPOINT = ROOT / "scripts" / "assignment_milestone_checkpoint.py"
VALIDATOR = ROOT / "scripts" / "milestone_framework_validate.py"
TERMINAL = ROOT / "scripts" / "full_run_contract_check.py"
FINAL_PATH = "manuscript/final.md"
EXPORT_PATH = "submission_bundle/final_manuscript.md"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def run(*args: object, expected: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, *(str(arg) for arg in args)], cwd=ROOT,
        text=True, capture_output=True, check=False,
    )
    if result.returncode != expected:
        raise AssertionError(
            f"expected {expected}, got {result.returncode}: {' '.join(str(arg) for arg in args)}\n"
            f"{result.stdout}{result.stderr}"
        )
    return result


def state(project: Path) -> dict:
    return json.loads((project / "reviews" / "phase_state.json").read_text(encoding="utf-8"))


def prepare_public_m1_m4(project: Path) -> None:
    run(
        BOOTSTRAP, "--project-root", project, "--project-name", "terminal-walk",
        "--title", "Synthetic Terminal Walk", "--intended-reader", "researcher",
        "--created-at", "2026-07-19T00:00:00Z",
    )
    write_valid_contract(project)
    ticks = iter(range(1, 40))
    for milestone in ("M1", "M2", "M3"):
        if milestone != "M1":
            run(CHECKPOINT, "begin", "--project-root", project, "--milestone", milestone, "--at", f"2026-07-19T00:00:{next(ticks):02d}Z")
        consumed = publish(project, milestone, f"# {milestone} terminal walk deliverable\n".encode(), label="terminal")
        checkpoint = checkpoint_input(project, milestone, f"2026-07-19T00:00:{next(ticks):02d}Z", label="terminal")
        run(CHECKPOINT, "record", "--project-root", project, "--milestone", milestone, "--receipt", consumed, "--checkpoint", checkpoint, "--at", f"2026-07-19T00:00:{next(ticks):02d}Z")
        approval = approval_input(project, milestone, f"2026-07-19T00:00:{next(ticks):02d}Z")
        run(CHECKPOINT, "accept", "--project-root", project, "--milestone", milestone, "--checkpoint", checkpoint, "--approval-evidence", approval, "--at", f"2026-07-19T00:00:{next(ticks):02d}Z")
    run(CHECKPOINT, "begin", "--project-root", project, "--milestone", "M4", "--at", "2026-07-19T00:00:20Z")
    consumed = publish(project, "M4", b"# Accepted M4 manuscript\n", label="terminal")
    checkpoint = checkpoint_input(project, "M4", "2026-07-19T00:00:21Z", label="terminal", phase="Ph1", cycle_id="m4-terminal-001")
    run(CHECKPOINT, "record", "--project-root", project, "--milestone", "M4", "--receipt", consumed, "--checkpoint", checkpoint, "--at", "2026-07-19T00:00:22Z")
    converge_m4_fixture(project)
    policy = m4_acceptance_policy_input(project)
    approval = approval_input(project, "M4", "2026-07-19T00:00:24Z")
    run(CHECKPOINT, "accept", "--project-root", project, "--milestone", "M4", "--checkpoint", checkpoint, "--approval-evidence", approval, "--policy-evidence", policy, "--at", "2026-07-19T00:00:25Z")


def install_ph4_evidence(project: Path, fixture_root: Path) -> None:
    source = valid_project(fixture_root)
    source_state = state(source)
    document = state(project)
    for key, value in source_state.items():
        if key not in {"manuscript_id", "milestone_framework", "terminal_phase_reached", "terminal_round_id"}:
            document[key] = value
    document["terminal_phase_reached"] = False
    document["terminal_round_id"] = None
    write_json(project / "reviews" / "phase_state.json", document)
    for relative in (
        "manuscript/revision_log.md", "reviews/convergence_log.md",
        "reviews/ph3_convergence_signoff.md", "reviews/G4_signoff.md",
        "reviews/ph4_ship_signoff.md", "reviews/reflection_report.md",
        f"reviews/final_round_report_{BOUND}.md",
    ):
        source_path = source / relative
        target = project / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target)


def publish_final(project: Path, final_bytes: bytes, export_bytes: bytes) -> Path:
    ready = project / "reviews" / ".harness" / "assignment" / "ready" / "gate_receipt_FINAL_terminal.json"
    run(GATE, "--project-root", project, "--stage", "final", "--emit-receipt", ready)
    receipt = json.loads(ready.read_text(encoding="utf-8"))
    wrong_path = run(
        PREFLIGHT, "--project-root", project, "--receipt", ready,
        "--consumer", "planner", "--expected-target", "FINAL",
        "--write-path", "manuscript/main.md", expected=4,
    )
    assert "APG-RECEIPT-PATH-MISMATCH" in wrong_path.stdout and ready.is_file()
    run(
        PREFLIGHT, "--project-root", project, "--receipt", ready,
        "--consumer", "planner", "--expected-target", "FINAL",
        "--write-path", FINAL_PATH, "--write-path", EXPORT_PATH,
    )
    reserved = ready.parent.parent / "reserved" / ready.name
    staged_root = project / "reviews" / ".harness" / "assignment" / "staged" / receipt["receipt_id"]
    staged_final = staged_root / "final.md"
    staged_export = staged_root / "final_export.md"
    staged_root.mkdir(parents=True, exist_ok=True)
    staged_final.write_bytes(final_bytes)
    staged_export.write_bytes(export_bytes)
    plan = staged_root / "write_plan.json"
    write_json(plan, {
        "schema_version": "1.0.0", "receipt_id": receipt["receipt_id"],
        "reservation_id": receipt["reservation_id"], "target_milestone": "FINAL",
        "role": "generator", "writes": [
            {"staged_path": staged_final.relative_to(project).as_posix(), "target_path": FINAL_PATH, "sha256": hashlib.sha256(final_bytes).hexdigest()},
            {"staged_path": staged_export.relative_to(project).as_posix(), "target_path": EXPORT_PATH, "sha256": hashlib.sha256(export_bytes).hexdigest()},
        ],
    })
    run(WRITER, "--project-root", project, "--receipt", reserved, "--plan", plan)
    return ready.parent.parent / "consumed" / ready.name


def terminal_inputs(project: Path) -> tuple[Path, Path, Path]:
    document = state(project)
    framework = document["milestone_framework"]
    binding = framework["policy_bindings"]["reader_accessibility"]
    final = project / FINAL_PATH

    feedback = project / "reviews" / ".harness" / "milestones" / "checkpoints" / "m5_feedback.md"
    feedback.parent.mkdir(parents=True, exist_ok=True)
    feedback.write_text("Synthetic terminal feedback was adjudicated.\n", encoding="utf-8")
    checkpoint = feedback.with_name("m5_checkpoint.json")
    write_json(checkpoint, {
        "schema_version": "1.0.0", "milestone": "M5",
        "feedback_records": [{
            "feedback_id": "m5-terminal-feedback", "evidence_class": "direct_milestone_feedback",
            "source_path": feedback.relative_to(project).as_posix(), "source_sha256": sha(feedback),
            "source_actor": "user", "source_authority": "user", "source_milestone": "M5",
            "target_milestone": "M5", "received_at": "2026-07-19T01:00:03Z",
            "contemporaneity_evidence_path": feedback.relative_to(project).as_posix(),
            "contemporaneity_evidence_sha256": sha(feedback), "lineage_id": "main",
            "blocking": False, "disposition": "informational",
            "rationale": "Terminal feedback was reviewed and requires no further revision.",
            "successor_effect": "Proceed to explicit terminal approval.",
        }],
        "inputs_consumed": [], "decisions_frozen": ["Freeze submission-bound bytes."],
        "open_debts": [], "next_milestone_instructions": ["Archive terminal evidence."],
        "policy_evidence": {"phase": "Ph4", "cycle_id": BOUND},
    })

    transition_snapshot = {key: binding["transitions"][key]["state"] for key in ("G", "H", "VE")}
    check8 = project / "reviews" / ".harness" / "policy" / "m5_terminal_check8.json"
    write_json(check8, {
        "schema_version": "check8_evidence.v1", "cycle_id": BOUND,
        "profile_path": binding["resolved_path"], "profile_sha256": binding["profile_sha256"],
        "attestation_view_pin": binding["attestation_view_pin"], "exemplar_view_pin": binding["exemplar_view_pin"],
        "manuscript_path": FINAL_PATH, "manuscript_sha256": sha(final), "phase": "Ph4",
        "transition_snapshot": transition_snapshot,
        "subchecks": {letter: {"findings": []} for letter in "ABCDEFGH"},
        "subcheck_verdicts": {letter: "CLEAN" for letter in "ABCDEFGH"},
        "ve": {"aggregate_member": False, "gate_contribution": "none", "findings": []},
        "aggregate_verdict": "CLEAN",
    })
    (project / "reviews" / "G4_signoff.md").write_text(
        "# G.4\n\nstatus: PASS\n"
        f"manuscript_path: {FINAL_PATH}\n"
        f"manuscript_sha256: {sha(final)}\n"
        f"round_id: {BOUND}\n"
        "authority: evaluator\n"
        f"check8_sha256: {sha(check8)}\n"
        "safeguard_status: CLEAN\n",
        encoding="utf-8",
    )
    (project / "reviews" / "ph4_ship_signoff.md").write_text(
        "# Ph4 ship\n\nstatus: APPROVED\n"
        f"manuscript_path: {FINAL_PATH}\n"
        f"manuscript_sha256: {sha(final)}\n"
        f"round_id: {BOUND}\n"
        "authority: user\n",
        encoding="utf-8",
    )

    f7 = project / "reviews" / ".harness" / "evidence" / f"{BOUND}__ph4__001.json"
    write_json(f7, {
        "artifact_family": "F7", "document_type": "evidence_packet", "round_id": BOUND,
        "event_id": f"{BOUND}__ph4__001", "phase": "Ph4", "target": FINAL_PATH,
        "evidence_status": "complete", "created_at": "2026-07-19T01:00:03Z",
        "checks_run": ["terminal-fixture"], "blockers": [], "major_actions": [],
        "minor_actions_count": 0, "manuscript_delta_summary": "FINAL publication verified.",
        "state_updates": {}, "source_reads": [FINAL_PATH],
        "final_report_inputs": {"checks_skipped": [], "baseline_metrics": {}, "notes": []},
    })
    events = project / "reviews" / ".harness" / "events.jsonl"
    events.parent.mkdir(parents=True, exist_ok=True)
    events.write_text(json.dumps({
        "round_id": BOUND, "event_id": f"{BOUND}__ph4__001",
        "timestamp": "2026-07-19T01:00:03Z", "phase": "Ph4",
        "event": "evidence_packet_written", "path": f7.relative_to(project).as_posix(),
    }) + "\n", encoding="utf-8")
    write_json(project / "reviews" / "findings.json", _findings_report(FINAL_PATH))

    bindings = []
    for role, relative in (
        ("g4_signoff", "reviews/G4_signoff.md"),
        ("ship_signoff", "reviews/ph4_ship_signoff.md"),
        ("final_round_report", f"reviews/final_round_report_{BOUND}.md"),
        ("reflector_full", "reviews/reflection_report.md"),
        ("f7_evidence", f7.relative_to(project).as_posix()),
        ("events_log", events.relative_to(project).as_posix()),
        ("findings", "reviews/findings.json"),
        ("convergence_log", "reviews/convergence_log.md"),
    ):
        path = project / Path(*Path(relative).parts)
        bindings.append({"role": role, "path": relative.replace("\\", "/"), "sha256": sha(path)})
    terminal = feedback.with_name("m5_terminal_evidence.json")
    write_json(terminal, {
        "schema_version": "1.0.0", "milestone": "M5", "terminal_round_id": BOUND,
        "manuscript_sha256": sha(final), "phase": "Ph4", "cycle_id": BOUND,
        "check8_path": check8.relative_to(project).as_posix(), "check8_sha256": sha(check8),
        "aggregate_verdict": "CLEAN", "bindings": bindings,
    })
    approval = feedback.with_name("m5_approval.json")
    write_json(approval, {
        "schema_version": "1.0.0", "status": "approved", "milestone": "M5",
        "authority": "user", "approved_at": "2026-07-19T01:00:05Z",
        "deliverable": {"path": FINAL_PATH, "sha256": sha(final)},
    })
    return checkpoint, terminal, approval


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="assignment-terminal-close-") as raw:
        project = Path(raw) / "walk"
        prepare_public_m1_m4(project)
        install_ph4_evidence(project, Path(raw) / "fixture")
        assert json.loads(run(CHECKPOINT, "derive", "--project-root", project).stdout) == {
            "status": "READY", "milestone": "FINAL", "action": "begin",
        }
        run(CHECKPOINT, "begin", "--project-root", project, "--milestone", "FINAL", "--at", "2026-07-19T01:00:01Z")
        final_bytes = b"# Submission-bound final manuscript\n\nChanged after accepted M4.\n"
        consumed = publish_final(project, final_bytes, final_bytes)
        checkpoint, terminal, approval = terminal_inputs(project)
        run(
            CHECKPOINT, "record", "--project-root", project, "--milestone", "FINAL",
            "--receipt", consumed, "--checkpoint", checkpoint, "--at", "2026-07-19T01:00:04Z",
        )
        before_close = state(project)
        assert before_close["terminal_phase_reached"] is False
        assert before_close["milestone_framework"]["milestones"]["M5"]["status"] == "in_progress"
        packet_path = project / "reviews" / ".harness" / "milestones" / "M5_terminal.json"

        revision_log = project / "manuscript" / "revision_log.md"
        revision_log_bytes = revision_log.read_bytes()
        revision_log.write_bytes(b"")
        refused = run(
            CHECKPOINT, "accept", "--project-root", project, "--milestone", "FINAL",
            "--checkpoint", checkpoint, "--approval-evidence", approval,
            "--terminal-evidence", terminal, "--at", "2026-07-19T01:00:06Z", expected=4,
        )
        assert "AMC-TERMINAL-CONTRACT" in refused.stdout and state(project) == before_close and not packet_path.exists()
        revision_log.write_bytes(revision_log_bytes)

        packet_path.parent.mkdir(parents=True, exist_ok=True)
        packet_path.write_bytes(b'{"orphaned_terminal_packet":true}\n')
        claim = packet_path.parent / "claims" / "transaction.lock"
        write_json(claim, {
            "schema_version": "1.0.0", "pid": 2147483647,
            "host": __import__("platform").node(), "operation": "accept:FINAL",
            "started_at": "2026-07-19T01:00:05Z",
        })
        run(
            CHECKPOINT, "recover", "--project-root", project,
            "--acknowledgement", "inspected-milestone-state-and-journal",
        )
        assert not packet_path.exists() and not claim.exists()
        assert list((packet_path.parent / "journal").glob("orphan-M5_terminal-*.json"))

        terminal_payload = json.loads(terminal.read_text(encoding="utf-8"))
        for label, updates in (
            ("wrong_phase", {"phase": "Ph2"}),
            ("major_check8", {"aggregate_verdict": "MAJOR"}),
        ):
            invalid_terminal = terminal.with_name(f"m5_terminal_{label}.json")
            write_json(invalid_terminal, {**terminal_payload, **updates})
            refused = run(
                CHECKPOINT, "accept", "--project-root", project, "--milestone", "FINAL",
                "--checkpoint", checkpoint, "--approval-evidence", approval,
                "--terminal-evidence", invalid_terminal, "--at", "2026-07-19T01:00:06Z", expected=4,
            )
            assert "AMC-TERMINAL" in refused.stdout and state(project) == before_close and not packet_path.exists()

        f8 = project / "reviews" / f"final_round_report_{BOUND}.md"
        f8_bytes = f8.read_bytes()
        f8.write_bytes(f8_bytes.replace(b"evidence_status: complete", b"evidence_status: incomplete"))
        incomplete_payload = json.loads(terminal.read_text(encoding="utf-8"))
        next(row for row in incomplete_payload["bindings"] if row["role"] == "final_round_report")["sha256"] = sha(f8)
        incomplete_terminal = terminal.with_name("m5_terminal_incomplete_f8.json")
        write_json(incomplete_terminal, incomplete_payload)
        refused = run(
            CHECKPOINT, "accept", "--project-root", project, "--milestone", "FINAL",
            "--checkpoint", checkpoint, "--approval-evidence", approval,
            "--terminal-evidence", incomplete_terminal, "--at", "2026-07-19T01:00:06Z", expected=4,
        )
        assert "AMC-TERMINAL-CONTRACT" in refused.stdout and state(project) == before_close and not packet_path.exists()
        f8.write_bytes(f8_bytes)

        ship = project / "reviews" / "ph4_ship_signoff.md"
        ship_bytes = ship.read_bytes()
        ship.write_text(
            ship.read_text(encoding="utf-8").replace("authority: user\n", ""),
            encoding="utf-8",
        )
        missing_ship_payload = json.loads(terminal.read_text(encoding="utf-8"))
        next(row for row in missing_ship_payload["bindings"] if row["role"] == "ship_signoff")["sha256"] = sha(ship)
        missing_ship_terminal = terminal.with_name("m5_terminal_missing_ship_authority.json")
        write_json(missing_ship_terminal, missing_ship_payload)
        refused = run(
            CHECKPOINT, "accept", "--project-root", project, "--milestone", "FINAL",
            "--checkpoint", checkpoint, "--approval-evidence", approval,
            "--terminal-evidence", missing_ship_terminal, "--at", "2026-07-19T01:00:06Z", expected=4,
        )
        assert "AMC-TERMINAL-CONTRACT" in refused.stdout and state(project) == before_close and not packet_path.exists()
        ship.write_bytes(ship_bytes)

        bound_f7 = project / "reviews" / ".harness" / "evidence" / f"{BOUND}__ph4__bound-stale.json"
        write_json(bound_f7, {
            "artifact_family": "F7", "document_type": "evidence_packet", "round_id": BOUND,
            "event_id": f"{BOUND}__ph4__bound-stale", "phase": "Ph4", "target": FINAL_PATH,
            "evidence_status": "incomplete", "created_at": "2026-07-19T01:00:03Z",
            "checks_run": [], "blockers": [], "major_actions": [], "minor_actions_count": 0,
            "manuscript_delta_summary": "Incomplete bound packet.", "state_updates": {},
            "source_reads": [FINAL_PATH], "final_report_inputs": {"checks_skipped": [], "baseline_metrics": {}, "notes": []},
        })
        events = project / "reviews" / ".harness" / "events.jsonl"
        events_bytes = events.read_bytes()
        events.write_bytes(events_bytes + (json.dumps({
            "round_id": BOUND, "event_id": f"{BOUND}__ph4__bound-stale",
            "timestamp": "2026-07-19T01:00:03Z", "phase": "Ph4",
            "event": "evidence_packet_written", "path": bound_f7.relative_to(project).as_posix(),
        }) + "\n").encode())
        stale_f7_payload = json.loads(terminal.read_text(encoding="utf-8"))
        next(row for row in stale_f7_payload["bindings"] if row["role"] == "f7_evidence").update(
            {"path": bound_f7.relative_to(project).as_posix(), "sha256": sha(bound_f7)}
        )
        next(row for row in stale_f7_payload["bindings"] if row["role"] == "events_log")["sha256"] = sha(events)
        stale_f7_terminal = terminal.with_name("m5_terminal_stale_bound_f7.json")
        write_json(stale_f7_terminal, stale_f7_payload)
        refused = run(
            CHECKPOINT, "accept", "--project-root", project, "--milestone", "FINAL",
            "--checkpoint", checkpoint, "--approval-evidence", approval,
            "--terminal-evidence", stale_f7_terminal, "--at", "2026-07-19T01:00:06Z", expected=4,
        )
        assert "AMC-TERMINAL" in refused.stdout and state(project) == before_close and not packet_path.exists()
        events.write_bytes(events_bytes)

        packet_path.write_bytes(b'{"conflicting":true}\n')
        conflict = run(
            CHECKPOINT, "accept", "--project-root", project, "--milestone", "FINAL",
            "--checkpoint", checkpoint, "--approval-evidence", approval,
            "--terminal-evidence", terminal, "--at", "2026-07-19T01:00:06Z", expected=4,
        )
        assert "AMC-F9-CONFLICT" in conflict.stdout and packet_path.read_bytes() == b'{"conflicting":true}\n'
        assert state(project) == before_close
        packet_path.unlink()

        g4 = project / "reviews" / "G4_signoff.md"
        g4_bytes = g4.read_bytes()
        try:
            accept_transaction(
                project, "FINAL", checkpoint, approval, "2026-07-19T01:00:06Z",
                terminal_evidence_path=terminal,
                _before_state_publish=lambda: g4.write_bytes(g4_bytes + b" "),
            )
        except MilestoneTransactionError as exc:
            assert exc.code == "AMC-DEPENDENCY-CHANGED", exc.code
        else:
            raise AssertionError("terminal close published state after a bound dependency changed")
        assert state(project) == before_close and not packet_path.exists()
        g4.write_bytes(g4_bytes)
        run(
            CHECKPOINT, "accept", "--project-root", project, "--milestone", "FINAL",
            "--checkpoint", checkpoint, "--approval-evidence", approval,
            "--terminal-evidence", terminal, "--at", "2026-07-19T01:00:06Z",
        )
        closed = state(project)
        m5 = closed["milestone_framework"]["milestones"]["M5"]
        assert closed["terminal_phase_reached"] is True and closed["terminal_round_id"] == BOUND
        assert m5["status"] == "accepted" and m5["handoff"]["packet_path"].endswith("M5_terminal.json")
        packet = json.loads((project / m5["handoff"]["packet_path"]).read_text(encoding="utf-8"))
        assert packet["to_milestone"] is None and packet["released_export"]["source_sha256"] == sha(project / FINAL_PATH)
        assert packet["inputs_consumed"]
        run(VALIDATOR, "--project-root", project)
        run(TERMINAL, "terminal", "--project-root", project)
        assert json.loads(run(CHECKPOINT, "derive", "--project-root", project).stdout) == {
            "status": "COMPLETE", "milestone": None, "action": None,
        }

    print("OK assignment_terminal_close_smoketest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
