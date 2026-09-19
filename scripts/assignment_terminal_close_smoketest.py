#!/usr/bin/env python3
"""Public FINAL/M5 publication and state-last terminal-close regression."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from assignment_fixture_support import package_scratch
import subprocess
import sys
import tempfile
import time

import assignment_dispatch_claim as dispatch_claims
import draft_evidence_verifier as verifier
from assignment_fixture_support import write_valid_contract
from c2_evidence_fixture_support import build_activation_fixture
from semantic_graph_fixture_support import semantic_graph_fixture_environment
from scholarly_assurance_fixture_support import (
    build_qualified_scholarly_from_authorities,
)
from assignment_milestone_checkpoint_smoketest import (
    _lifecycle_locator, approval_input, checkpoint_input, converge_m4_fixture,
    m4_acceptance_policy_input, publish,
)
from assignment_milestone_transaction import (
    MilestoneTransactionError, accept as accept_transaction,
    _dependency_snapshot, _exclusive_bytes, _recheck_dependencies,
    _validate_m5_terminal_policy,
)
from milestone_path_contract import snapshot_path
from full_run_semantic_bypass_smoketest import (
    BOUND, CONVERGENCE_LOG, F4_REPORT, F8_REPORT, _findings_report,
)


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "scripts" / "native_project_bootstrap.py"
GATE = ROOT / "scripts" / "assignment_process_gate.py"
PREFLIGHT = ROOT / "scripts" / "assignment_dispatch_preflight.py"
WRITER = ROOT / "scripts" / "assignment_writer_commit.py"
CHECKPOINT = ROOT / "scripts" / "assignment_milestone_checkpoint.py"
VALIDATOR = ROOT / "scripts" / "milestone_framework_validate.py"
TERMINAL = ROOT / "scripts" / "full_run_contract_check.py"
SEMANTICS = ROOT / "references" / "semantics_manifest.v1.json"
FINAL_PATH = "milestones/M5_final_paper.md"
EXPORT_PATH = "submission_bundle/final_manuscript.md"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def run(*args: object, expected: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, *(str(arg) for arg in args)], cwd=ROOT,
        text=True, encoding="utf-8", errors="replace", capture_output=True, check=False,
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
        "--created-at", "2026-07-19T00:00:00Z", "--handoff-policy", "audited",
    )
    write_valid_contract(project)
    ticks = iter(range(1, 40))
    for milestone in ("M1", "M2", "M3"):
        if milestone != "M1":
            run(CHECKPOINT, "begin", "--project-root", project, "--milestone", milestone, "--at", f"2026-07-19T00:00:{next(ticks):02d}Z")
        consumed, lifecycle_policy = publish(project, milestone, f"# {milestone} terminal walk deliverable\n".encode(), label="terminal")
        checkpoint = checkpoint_input(project, milestone, f"2026-07-19T00:00:{next(ticks):02d}Z", label="terminal", policy=lifecycle_policy)
        run(CHECKPOINT, "record", "--project-root", project, "--milestone", milestone, "--receipt", consumed, "--checkpoint", checkpoint, "--at", f"2026-07-19T00:00:{next(ticks):02d}Z")
        approval = approval_input(project, milestone, f"2026-07-19T00:00:{next(ticks):02d}Z")
        run(CHECKPOINT, "accept", "--project-root", project, "--milestone", milestone, "--checkpoint", checkpoint, "--approval-evidence", approval, "--at", f"2026-07-19T00:00:{next(ticks):02d}Z")
    run(CHECKPOINT, "begin", "--project-root", project, "--milestone", "M4", "--at", "2026-07-19T00:00:20Z")
    consumed, lifecycle_policy = publish(project, "M4", b"# Accepted M4 manuscript\n", label="terminal")
    checkpoint = checkpoint_input(project, "M4", "2026-07-19T00:00:21Z", label="terminal", phase="Ph1", cycle_id="m4-terminal-001", policy=lifecycle_policy)
    run(CHECKPOINT, "record", "--project-root", project, "--milestone", "M4", "--receipt", consumed, "--checkpoint", checkpoint, "--at", "2026-07-19T00:00:22Z")
    converge_m4_fixture(project)
    policy = m4_acceptance_policy_input(project)
    approval = approval_input(project, "M4", "2026-07-19T00:00:24Z")
    run(CHECKPOINT, "accept", "--project-root", project, "--milestone", "M4", "--checkpoint", checkpoint, "--approval-evidence", approval, "--policy-evidence", policy, "--at", "2026-07-19T00:00:25Z")


def install_ph4_evidence(project: Path, fixture_root: Path) -> None:
    del fixture_root
    document = state(project)
    from milestone_framework_smoketest import _phase_document

    document["sections"] = _phase_document(
        document["milestone_framework"], "Ph4"
    )["sections"]
    document["terminal_phase_reached"] = False
    document["terminal_round_id"] = None
    write_json(project / "reviews" / "phase_state.json", document)
    (project / "manuscript").mkdir(parents=True, exist_ok=True)
    (project / "manuscript" / "revision_log.md").write_text(
        "## Round 1 - 2026-07-17\n\n"
        "**Round program focus:** none - full scope\n"
        "**Hypothesis:** drafting the section establishes the argument.\n"
        "**Scope:** section 1\n"
        "**Changes:**\n- section 1 - drafted - plan action A1\n"
        "**Self-check result:** CLEAN\n"
        "**Verdict:** RETAIN\n"
        "**Carried forward:** none\n",
        encoding="utf-8",
    )
    (project / "reviews" / "convergence_log.md").write_text(
        CONVERGENCE_LOG, encoding="utf-8"
    )
    (project / "reviews" / "ph3_convergence_signoff.md").write_text(
        "- row_timestamp: 2026-07-17T00:00:00Z\n"
        "  iteration_number: 3\n  is_terminal: true\n"
        "  is_reengagement: false\n  user_signature: user\n"
        "  user_signed_at: 2026-07-17T00:00:00Z\n"
        "  convergence_metric_value: 0.004\n  t3_verdict: CONVERGING\n"
        "  final_owner_state: closed\n",
        encoding="utf-8",
    )
    (project / "reviews" / "reflection_report.md").write_text(
        F4_REPORT, encoding="utf-8"
    )
    (project / "reviews" / f"final_round_report_{BOUND}.md").write_text(
        F8_REPORT, encoding="utf-8"
    )


def publish_final(
    project: Path, final_bytes: bytes, export_bytes: bytes, *, label: str = "terminal"
) -> tuple[Path, dict]:
    activation = build_activation_fixture(
        project,
        artifact_relative=FINAL_PATH,
        evidence_relative=f"reviews/.harness/fixtures/final-{label}",
    )
    requested_final = final_bytes
    requested_export = export_bytes
    final_text = requested_final.decode("utf-8", errors="strict").strip()
    claim_text = "A bounded synthetic FINAL claim remains qualified."
    activation.mutate_artifact(
        lambda text: f"{text}\n\n{final_text}\n\n# Synthetic analysis\n\n{claim_text}\n"
    )
    final_bytes = activation.artifact.read_bytes()
    activation.refresh_synthetic_bibliography()
    export_bytes = final_bytes if requested_export == requested_final else requested_export
    ready = project / "reviews" / ".harness" / "assignment" / "ready" / f"gate_receipt_FINAL_{label}.json"
    run(GATE, "--project-root", project, "--stage", "final", "--emit-receipt", ready)
    receipt = json.loads(ready.read_text(encoding="utf-8"))
    wrong_path = run(
        PREFLIGHT, "--project-root", project, "--receipt", ready,
        "--consumer", "planner", "--expected-target", "FINAL",
        "--write-path", "milestones/M4_complete_paper_draft.md", expected=4,
    )
    assert "APG-RECEIPT-PATH-MISMATCH" in wrong_path.stdout and ready.is_file()
    run(
        PREFLIGHT, "--project-root", project, "--receipt", ready,
        "--consumer", "planner", "--expected-target", "FINAL",
        "--write-path", FINAL_PATH, "--write-path", EXPORT_PATH,
    )
    reserved = ready.parent.parent / "reserved" / ready.name
    generation_claim, generation_claim_path, _ = dispatch_claims.issue_generation_claim(
        project,
        reserved,
        policy_path=activation.wiki_root / "policy.json",
        bibliography_snapshot=activation.bibliography_snapshot,
        nonce=hashlib.sha256(f"FINAL:{label}:generation".encode()).hexdigest()[:32],
        issuer_transaction_id="assignment-reserve-FINAL",
        issued_at="2026-07-19T01:00:01.1Z",
    )
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
    consumed = ready.parent.parent / "consumed" / ready.name
    generation_consumption, generation_consumption_path, _ = dispatch_claims.consume_dispatch_claim(
        project,
        generation_claim_path,
        role="generator",
        consumer_transaction_id=f"assignment-write-FINAL-{label}",
        target_paths=[FINAL_PATH, EXPORT_PATH],
        consumed_at="2026-07-19T01:00:02Z",
    )
    verifier_root = project / "reviews" / ".harness" / "verifier" / f"final-{label}"
    semantics = SEMANTICS
    generation_paths = verifier.publish_verifier_transaction(
        artifact=project / FINAL_PATH,
        semantic_receipt=activation.receipt,
        phase="generation",
        project_root=project,
        wiki_root=activation.wiki_root,
        harness_root=ROOT,
        semantics_manifest=semantics,
        out_dir=verifier_root / "generation",
        requested_independence_level="none",
    )
    evaluation_claim, evaluation_claim_path, _ = dispatch_claims.issue_evaluation_claim(
        project,
        generation_claim_path,
        generation_consumption=generation_consumption_path,
        artifact=project / FINAL_PATH,
        generation_transaction=generation_paths["transaction"],
        generation_publication_manifest=generation_paths["publication_manifest"],
        generation_commit_marker=generation_paths["commit_marker"],
        generation_semantic_receipt=activation.receipt,
        wiki_root=activation.wiki_root,
        semantics_manifest=semantics,
        nonce=hashlib.sha256(f"FINAL:{label}:evaluation".encode()).hexdigest()[:32],
        issuer_transaction_id="assignment-evaluation-FINAL",
        issued_at="2026-07-19T01:00:02.1Z",
    )
    scholarly = build_qualified_scholarly_from_authorities(
        project,
        authorities={
            "artifact": project / FINAL_PATH,
            "artifact_relative": FINAL_PATH,
            "receipt_id": receipt["receipt_id"],
            "reservation_id": receipt["reservation_id"],
            "activation": activation,
            "semantics": semantics,
            "generation": generation_claim,
            "generation_path": generation_claim_path,
            "generation_consumption": generation_consumption_path,
            "generation_paths": generation_paths,
            "evaluator": evaluation_claim,
            "evaluator_path": evaluation_claim_path,
        },
        label=f"final-{label}",
        claim_text=claim_text,
    )
    evaluation_consumption_path = scholarly.evaluation_consumption
    evaluation_semantic = scholarly.evaluation_semantic_receipt
    evaluation_paths = scholarly.evaluation_verifier
    generation_id = json.loads(
        generation_paths["transaction"].read_text(encoding="utf-8")
    )["transaction_id"]
    policy = {
        "draft_generation": _lifecycle_locator(
            project, milestone="M5", label=label, phase="generation",
            receipt_id=receipt["receipt_id"], paths=generation_paths,
            claim=generation_claim_path, consumption=generation_consumption_path,
            semantic_receipt=activation.receipt, wiki_root=activation.wiki_root,
            generation_transaction_id=None,
            semantics_manifest=semantics,
        ),
        "draft_evaluation": _lifecycle_locator(
            project, milestone="M5", label=label, phase="evaluation",
            receipt_id=receipt["receipt_id"], paths=evaluation_paths,
            claim=evaluation_claim_path, consumption=evaluation_consumption_path,
            semantic_receipt=evaluation_semantic, wiki_root=activation.wiki_root,
            generation_transaction_id=generation_id,
            semantics_manifest=semantics,
        ),
        "scholarly_evaluation": scholarly.binding,
    }
    assert generation_consumption["claim_id"] == generation_claim["claim_id"]
    return consumed, policy


def terminal_inputs(
    project: Path, lifecycle_policy: dict, *, snapshot_manuscript: bool = False,
) -> tuple[Path, Path, Path]:
    document = state(project)
    framework = document["milestone_framework"]
    binding = framework["policy_bindings"]["reader_accessibility"]
    final = project / FINAL_PATH
    manuscript_relative = (
        snapshot_path("M5", sha(final)) if snapshot_manuscript else FINAL_PATH
    )

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
        "policy_evidence": {
            **lifecycle_policy,
            "phase": "Ph4", "cycle_id": BOUND,
        },
    })

    transition_snapshot = {key: binding["transitions"][key]["state"] for key in ("G", "H", "VE")}
    check8 = project / "reviews" / ".harness" / "policy" / "m5_terminal_check8.json"
    write_json(check8, {
        "schema_version": "check8_evidence.v2", "cycle_id": BOUND,
        "profile_path": binding["resolved_path"], "profile_sha256": binding["profile_sha256"],
        "semantic_usage": "not_invoked",
        "manuscript_path": manuscript_relative, "manuscript_sha256": sha(final), "phase": "Ph4",
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
    started = time.perf_counter()

    def stage(name: str) -> None:
        line = f"terminal-stage {name} {time.perf_counter() - started:.3f}s"
        print(line, flush=True)
        trace = os.environ.get("COAUTHOR_TERMINAL_TIMING_LOG")
        if trace:
            target = Path(trace).resolve()
            allowed = (ROOT / "releases/verification/v0.40.0/C9").resolve()
            if not target.is_relative_to(allowed):
                raise AssertionError("terminal timing log must remain inside C9 evidence")
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(line + "\n")
                handle.flush()
                os.fsync(handle.fileno())

    with tempfile.TemporaryDirectory(prefix="assignment-terminal-close-", dir=package_scratch(ROOT)) as raw:
        project = Path(raw) / "walk"
        prepare_public_m1_m4(project)
        stage("m1-m4-ready")
        install_ph4_evidence(project, Path(raw) / "fixture")
        stage("ph4-evidence-ready")
        assert json.loads(run(CHECKPOINT, "derive", "--project-root", project).stdout) == {
            "status": "READY", "milestone": "FINAL", "action": "begin",
            "authority_mode": "direct_local",
        }
        run(CHECKPOINT, "begin", "--project-root", project, "--milestone", "FINAL", "--at", "2026-07-19T01:00:01Z")
        final_bytes = b"# Submission-bound final manuscript\n\nChanged after accepted M4.\n"
        consumed, lifecycle_policy = publish_final(project, final_bytes, final_bytes)
        stage("final-published")
        checkpoint, terminal, approval = terminal_inputs(project, lifecycle_policy)
        run(
            CHECKPOINT, "record", "--project-root", project, "--milestone", "FINAL",
            "--receipt", consumed, "--checkpoint", checkpoint, "--at", "2026-07-19T01:00:04Z",
        )
        stage("final-recorded")
        before_close = state(project)
        assert before_close["terminal_phase_reached"] is False
        assert before_close["milestone_framework"]["milestones"]["M5"]["status"] == "in_progress"
        packet_path = project / "reviews" / ".harness" / "handoffs" / "M5_terminal.json"

        packet_path.parent.mkdir(parents=True, exist_ok=True)
        packet_path.write_bytes(b'{"orphaned_terminal_packet":true}\n')
        claim = project / "reviews" / ".harness" / "milestones" / "claims" / "transaction.lock"
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
        assert list((project / "reviews" / ".harness" / "milestones" / "journal").glob("orphan-M5_terminal-*.json"))
        stage("recovery")

        terminal_payload = json.loads(terminal.read_text(encoding="utf-8"))
        terminal_artifact = next(
            row for row in before_close["milestone_framework"]["milestones"]["M5"]["artifacts"]
            if row.get("role") == "deliverable"
        )
        for label, updates in (
            ("wrong_phase", {"phase": "Ph2"}),
            ("major_check8", {"aggregate_verdict": "MAJOR"}),
        ):
            invalid_terminal = terminal.with_name(f"m5_terminal_{label}.json")
            write_json(invalid_terminal, {**terminal_payload, **updates})
            try:
                _validate_m5_terminal_policy(project, invalid_terminal, terminal_artifact)
            except MilestoneTransactionError as exc:
                assert exc.code == "AMC-TERMINAL"
            else:
                raise AssertionError(f"terminal shape attack accepted: {label}")
        stage("terminal-shape-refusals")

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
        try:
            _validate_m5_terminal_policy(project, stale_f7_terminal, terminal_artifact)
        except MilestoneTransactionError as exc:
            assert exc.code == "AMC-TERMINAL"
        else:
            raise AssertionError("incomplete bound F7 was accepted")
        stage("f7-refusal")
        events.write_bytes(events_bytes)

        packet_path.write_bytes(b'{"conflicting":true}\n')
        try:
            _exclusive_bytes(packet_path, b'{"candidate":true}\n')
        except MilestoneTransactionError as exc:
            assert exc.code == "AMC-F9-CONFLICT"
        else:
            raise AssertionError("conflicting F9 bytes were overwritten")
        assert packet_path.read_bytes() == b'{"conflicting":true}\n'
        assert state(project) == before_close
        packet_path.unlink()
        stage("f9-conflict")

        g4 = project / "reviews" / "G4_signoff.md"
        g4_bytes = g4.read_bytes()
        dependency_snapshot = _dependency_snapshot(project, [g4])
        g4.write_bytes(g4_bytes + b" ")
        try:
            _recheck_dependencies(project, dependency_snapshot)
        except MilestoneTransactionError as exc:
            assert exc.code == "AMC-DEPENDENCY-CHANGED", exc.code
        else:
            raise AssertionError("changed terminal dependency passed recheck")
        assert state(project) == before_close and not packet_path.exists()
        g4.write_bytes(g4_bytes)
        stage("dependency-race")
        accept_transaction(
            project,
            "FINAL",
            checkpoint,
            approval,
            "2026-07-19T01:00:06Z",
            terminal_evidence_path=terminal,
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
            "authority_mode": "direct_local",
        }
        stage("complete")

    print("OK assignment_terminal_close_smoketest")
    return 0


if __name__ == "__main__":
    with semantic_graph_fixture_environment():
        raise SystemExit(main())
