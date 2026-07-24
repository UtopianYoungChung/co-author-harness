#!/usr/bin/env python3
"""Public-command M1-M4 checkpoint walk and adversarial regressions."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile

from assignment_fixture_support import write_valid_contract
from semantic_graph_fixture_support import semantic_graph_fixture_environment
from assignment_milestone_transaction import (
    MilestoneTransactionError, accept as accept_transaction,
    record as record_transaction,
)


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "scripts" / "native_project_bootstrap.py"
GATE = ROOT / "scripts" / "assignment_process_gate.py"
PREFLIGHT = ROOT / "scripts" / "assignment_dispatch_preflight.py"
WRITER = ROOT / "scripts" / "assignment_writer_commit.py"
CHECKPOINT = ROOT / "scripts" / "assignment_milestone_checkpoint.py"
VALIDATOR = ROOT / "scripts" / "milestone_framework_validate.py"
PHASE_VALIDATOR = ROOT / "scripts" / "phase_state_validate.py"
PATHS = {
    "M1": "milestones/M1_project_memo.md",
    "M2": "milestones/M2_annotated_references.md",
    "M3": "milestones/M3_argument_evidence_outline.md",
    "M4": "milestones/M4_complete_paper_draft.md",
    "M5": "milestones/M5_final_paper.md",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_read_only(path: Path) -> bool:
    current = path.stat()
    attributes = getattr(current, "st_file_attributes", 0)
    read_only_flag = getattr(stat, "FILE_ATTRIBUTE_READONLY", 0x0001)
    if attributes:
        return bool(attributes & read_only_flag)
    return not bool(current.st_mode & stat.S_IWUSR)


def run(*args: object, expected: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run([sys.executable, *(str(arg) for arg in args)], cwd=ROOT, text=True, encoding="utf-8", errors="replace", capture_output=True, check=False)
    if result.returncode != expected:
        raise AssertionError(f"expected {expected}, got {result.returncode}: {' '.join(str(arg) for arg in args)}\n{result.stdout}{result.stderr}")
    return result


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def state(project: Path) -> dict:
    return json.loads((project / "reviews" / "phase_state.json").read_text(encoding="utf-8"))


def draft_policy_evidence(project: Path, milestone: str, label: str) -> dict:
    artifact = project / PATHS[milestone]
    artifact_sha = sha(artifact)
    always = {
        "grounding-protocol", "d-style-profile", "reader-accessibility",
        "master-guidelines", "research-writing-playbook", "style-commitments",
        "integrated-style-checklist", "grammar-mechanics", "citation-discipline",
        "emdash-bundle", "sentence-craft", "narrative-structure",
        "deterministic-audit",
    }
    bindings = {}
    generation_sha = None
    for key, phase, role, centroid_id in (
        ("draft_generation", "generation", "generator", "centroid-generation"),
        ("draft_evaluation", "evaluation", "evaluator", "centroid-evaluation"),
    ):
        evidence = (
            project / "reviews" / ".harness" / "shipments" / "synthetic"
            / f"{milestone.lower()}_{label}_{phase}.verified.json"
        )
        envelope = {
            "schema_version": "1.0.0", "status": "verified",
            "phase": phase, "role": role, "target": "FINAL" if milestone == "M5" else milestone,
            "contract_sha256": "1" * 64, "artifact_sha256": artifact_sha,
            "centroid": {"required": True, "binding_provenance": "project"},
            "obligation_ids": sorted(always | {centroid_id}),
            "actor_id": "generator-A" if phase == "generation" else "evaluator-B",
            "dispatch_id": f"{milestone.lower()}-{label}-{phase}",
            "semantic_receipt_sha256": "2" * 64,
            "centroid_packet_sha256": "3" * 64,
            "product_assurance_sha256": "4" * 64,
            "passage_count": 1,
            "passage_source_keys": ["fixture-source"],
        }
        if phase == "evaluation":
            envelope["generation_envelope_sha256"] = generation_sha
        write_json(evidence, envelope)
        if phase == "generation":
            generation_sha = sha(evidence)
        bindings[key] = {
            "evidence_path": evidence.relative_to(project).as_posix(),
            "evidence_sha256": sha(evidence),
        }
    return bindings


def checkpoint_input(
    project: Path, milestone: str, at: str, *, valid_m4: bool = True,
    label: str = "initial", phase: str = "Ph1", cycle_id: str | None = None,
) -> Path:
    suffix = "" if label == "initial" else f"_{label}"
    evidence = project / "reviews" / ".harness" / "milestones" / "checkpoints" / f"{milestone.lower()}_feedback{suffix}.md"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(f"Synthetic adjudicated feedback for {milestone}.\n", encoding="utf-8")
    policy: dict = draft_policy_evidence(project, milestone, label)
    if milestone == "M3":
        references = project / "references" / "REFERENCES.md"
        references.parent.mkdir(parents=True, exist_ok=True)
        references.write_text("# Verified synthetic references\n", encoding="utf-8")
        wiki = project / "synthetic-wiki"
        source = wiki / "sources" / "source.md"; source.parent.mkdir(parents=True, exist_ok=True); source.write_text("# Source\n", encoding="utf-8")
        graph = wiki / "graphify-out" / "graph.json"; graph.parent.mkdir(parents=True, exist_ok=True); graph.write_text('{"nodes": []}\n', encoding="utf-8")
        grounding = project / "reviews" / ".harness" / "assignment" / "wiki_grounding_walk.json"
        write_json(grounding, {
            "schema_version": "1.0.0", "lineage_id": "main", "produced_at": at,
            "wiki_path": str(wiki), "wiki_first_resources": True,
            "skills_invoked": ["seed-snowball-discovery"],
            "references_path": "references/REFERENCES.md", "references_sha256": sha(references),
            "graph_path": str(graph), "graph_sha256_provenance": sha(graph),
            "sources_consulted": [{"path": str(source), "sha256": sha(source)}],
            "authority": "planner", "notes": "Synthetic public-command walk evidence."
        })
        policy["wiki_grounding"] = {"evidence_path": grounding.relative_to(project).as_posix(), "evidence_sha256": sha(grounding)}
    elif milestone == "M4":
        policy.update({
            "phase": phase,
            "cycle_id": cycle_id or f"m4-{label}-assembly-001",
        } if valid_m4 else {"phase": phase})
    payload = {
        "schema_version": "1.0.0", "milestone": milestone,
        "feedback_records": [{
            "feedback_id": f"{milestone.lower()}-feedback-{label}",
            "evidence_class": "direct_milestone_feedback",
            "source_path": evidence.relative_to(project).as_posix(), "source_sha256": sha(evidence),
            "source_actor": "user", "source_authority": "user",
            "source_milestone": milestone, "target_milestone": milestone,
            "received_at": at,
            "contemporaneity_evidence_path": evidence.relative_to(project).as_posix(),
            "contemporaneity_evidence_sha256": sha(evidence),
            "lineage_id": "main", "blocking": False, "disposition": "informational",
            "rationale": "Synthetic feedback was reviewed and requires no revision.",
            "successor_effect": "Proceed only after explicit approval."
        }],
        "inputs_consumed": [], "decisions_frozen": [f"Freeze {milestone} synthetic decision."],
        "open_debts": [], "next_milestone_instructions": [f"Use accepted {milestone} evidence."],
        "policy_evidence": policy,
    }
    path = evidence.with_name(f"{milestone.lower()}_checkpoint{suffix}{'_invalid' if not valid_m4 else ''}.json")
    write_json(path, payload)
    return path


def approval_input(project: Path, milestone: str, at: str) -> Path:
    if milestone == "M4":
        record = state(project)["milestone_framework"]["milestones"][milestone]
        artifact = next(row for row in record["artifacts"] if row["role"] == "deliverable")
        deliverable_path = artifact["path"]
    else:
        deliverable_path = PATHS[milestone]
    deliverable = project / deliverable_path
    path = project / "reviews" / ".harness" / "milestones" / "checkpoints" / f"{milestone.lower()}_approval.json"
    write_json(path, {
        "schema_version": "1.0.0", "status": "approved", "milestone": milestone,
        "authority": "user", "approved_at": at,
        "deliverable": {"path": deliverable_path, "sha256": sha(deliverable)},
    })
    return path


def advance_m4_fixture_to_ph2(project: Path) -> None:
    """Prepare a valid Ph2 state so public M4 re-record can bind a revision."""
    document = state(project)
    for section in document["sections"].values():
        section["current_phase"] = "Ph2"
        section["phase_entry_log"].append({
            "prev_phase": "Ph1", "new_phase": "Ph2", "trigger": "user_approval",
            "actor": "user", "notes": "Synthetic Ph2 entry for M4 revision.",
            "timestamp": "2026-07-19T00:00:23.1Z", "model_used": None,
        })
    write_json(project / "reviews" / "phase_state.json", document)


def converge_m4_fixture(project: Path) -> None:
    """Prepare upstream phase-owned state for the separate M4-accept test."""
    document = state(project)
    for section in document["sections"].values():
        if section["current_phase"] == "Ph1":
            section["phase_entry_log"].append(
                {"prev_phase": "Ph1", "new_phase": "Ph2", "trigger": "user_approval", "actor": "user", "notes": "Synthetic Ph2 entry.", "timestamp": "2026-07-19T00:00:23.1Z", "model_used": None}
            )
        section["current_phase"] = "Ph3_converged"
        section["phase_entry_log"].extend([
            {"prev_phase": "Ph2", "new_phase": "Ph3", "trigger": "user_approval", "actor": "user", "notes": "Synthetic Ph3 entry.", "timestamp": "2026-07-19T00:00:23.2Z", "model_used": None},
            {"prev_phase": "Ph3", "new_phase": "Ph3_converged", "trigger": "ph3_convergence_signoff_terminal", "actor": "planner", "notes": "Synthetic terminal convergence signoff.", "timestamp": "2026-07-19T00:00:23.3Z", "model_used": None},
        ])
    write_json(project / "reviews" / "phase_state.json", document)


def m4_acceptance_policy_input(project: Path) -> Path:
    document = state(project)
    framework = document["milestone_framework"]
    binding = framework["policy_bindings"]["reader_accessibility"]
    manuscript = project / PATHS["M4"]
    transition_snapshot = {key: binding["transitions"][key]["state"] for key in ("G", "H", "VE")}
    check8 = project / "reviews" / "check8_m4_converged.json"
    write_json(check8, {
        "schema_version": "check8_evidence.v1", "cycle_id": "m4-converged-001",
        "profile_path": binding["resolved_path"], "profile_sha256": binding["profile_sha256"],
        "attestation_view_pin": binding["attestation_view_pin"], "exemplar_view_pin": binding["exemplar_view_pin"],
        "manuscript_path": PATHS["M4"], "manuscript_sha256": sha(manuscript), "phase": "Ph3",
        "transition_snapshot": transition_snapshot,
        "subchecks": {letter: {"findings": []} for letter in "ABCDEFGH"},
        "subcheck_verdicts": {letter: "CLEAN" for letter in "ABCDEFGH"},
        "ve": {"aggregate_member": False, "gate_contribution": "none", "findings": []},
        "aggregate_verdict": "CLEAN",
    })
    policy = project / "reviews" / ".harness" / "milestones" / "checkpoints" / "m4_acceptance_policy.json"
    write_json(policy, {
        "schema_version": "1.0.0", "milestone": "M4", "manuscript_sha256": sha(manuscript),
        "phase": "Ph3", "cycle_id": "m4-converged-001",
        "check8_path": check8.relative_to(project).as_posix(), "check8_sha256": sha(check8),
        "aggregate_verdict": "CLEAN",
    })
    return policy


def publish(project: Path, milestone: str, content: bytes, *, label: str = "initial") -> Path:
    ready = project / "reviews" / ".harness" / "assignment" / "ready" / f"gate_receipt_{milestone}_walk_{label}.json"
    run(GATE, "--project-root", project, "--stage", "draft", "--target-milestone", milestone, "--emit-receipt", ready)
    record = json.loads(ready.read_text(encoding="utf-8"))
    run(PREFLIGHT, "--project-root", project, "--receipt", ready, "--consumer", "planner", "--expected-target", milestone, "--write-path", PATHS[milestone])
    reserved = ready.parent.parent / "reserved" / ready.name
    staged = project / "reviews" / ".harness" / "assignment" / "staged" / record["receipt_id"] / f"{milestone.lower()}_{label}.md"
    staged.parent.mkdir(parents=True, exist_ok=True); staged.write_bytes(content)
    plan = staged.with_name("write_plan.json")
    write_json(plan, {
        "schema_version": "1.0.0", "receipt_id": record["receipt_id"],
        "reservation_id": record["reservation_id"], "target_milestone": milestone,
        "role": "generator", "writes": [{
            "staged_path": staged.relative_to(project).as_posix(),
            "target_path": PATHS[milestone], "sha256": hashlib.sha256(content).hexdigest(),
        }]
    })
    run(WRITER, "--project-root", project, "--receipt", reserved, "--plan", plan)
    return ready.parent.parent / "consumed" / ready.name


def main() -> int:
    # Package-local scratch keeps this end-to-end fixture runnable from a
    # distributed plugin cache whose production boundary correctly refuses
    # unrelated OS-temp writes when no workspace manifest is discoverable.
    with tempfile.TemporaryDirectory(
            prefix="assignment-milestone-checkpoint-", dir=ROOT) as raw:
        project = Path(raw) / "walk"
        run(BOOTSTRAP, "--project-root", project, "--project-name", "walk", "--title", "Synthetic Walk", "--intended-reader", "researcher", "--created-at", "2026-07-19T00:00:00Z")
        write_valid_contract(project)

        # No state or F9 handoff is edited by this test: every lifecycle change
        # below goes through the public command under test.
        ticks = iter(range(1, 50))
        for milestone in ("M1", "M2", "M3"):
            print(f"walk/{milestone}", flush=True)
            if milestone != "M1":
                run(CHECKPOINT, "begin", "--project-root", project, "--milestone", milestone, "--at", f"2026-07-19T00:00:{next(ticks):02d}Z")
            derived = json.loads(run(CHECKPOINT, "derive", "--project-root", project).stdout)
            assert derived == {"status": "READY", "milestone": milestone, "action": "draft", "authority_mode": "direct_local"}, derived
            consumed = publish(project, milestone, f"# {milestone} synthetic deliverable\n".encode())
            checkpoint = checkpoint_input(project, milestone, f"2026-07-19T00:00:{next(ticks):02d}Z")
            run(CHECKPOINT, "record", "--project-root", project, "--milestone", milestone, "--receipt", consumed, "--checkpoint", checkpoint, "--at", f"2026-07-19T00:00:{next(ticks):02d}Z")
            approval = approval_input(project, milestone, f"2026-07-19T00:00:{next(ticks):02d}Z")
            run(CHECKPOINT, "accept", "--project-root", project, "--milestone", milestone, "--checkpoint", checkpoint, "--approval-evidence", approval, "--at", f"2026-07-19T00:00:{next(ticks):02d}Z")
            run(VALIDATOR, "--project-root", project)

        # The re-pin producer publishes a request; only this Planner command
        # may refresh the phase binding and archive that request. M3 acceptance
        # leaves no round open, so exercise both fail-closed request validation
        # and the positive state-last path at the authorized boundary.
        initial = state(project)
        initial_binding = initial["milestone_framework"]["policy_bindings"]["reader_accessibility"]
        request_path = project / "reviews" / "repin_rebind_request.json"
        write_json(request_path, {"status": "pending"})
        before_open_round_refusal = (project / "reviews" / "phase_state.json").read_bytes()
        refused = run(CHECKPOINT, "rebind-reader-policy", "--project-root", project, expected=4)
        assert "AMC-REPIN-ROUND" in refused.stdout
        assert (project / "reviews" / "phase_state.json").read_bytes() == before_open_round_refusal
        # Synthetic phase setup: this lifecycle fixture does not run the
        # section-round closer, so mark its initial dispatch logs closed before
        # testing the authorized no-open-round transaction boundary.
        closed = state(project)
        for section in closed["sections"].values():
            if section.get("phase_entry_log"):
                section["phase_entry_log"].append({
                    "prev_phase": "Ph1", "new_phase": "Ph1",
                    "trigger": "ph1_draft_completion_signed", "actor": "planner",
                    "notes": "Synthetic no-open-round boundary for Planner rebind regression.",
                    "timestamp": "2026-07-19T00:00:00Z", "model_used": None,
                })
        write_json(project / "reviews" / "phase_state.json", closed)
        before_invalid_rebind = (project / "reviews" / "phase_state.json").read_bytes()
        refused = run(CHECKPOINT, "rebind-reader-policy", "--project-root", project, expected=4)
        assert "AMC-REPIN-REQUEST" in refused.stdout
        assert (project / "reviews" / "phase_state.json").read_bytes() == before_invalid_rebind
        repin_rows = [
            json.loads(line) for line in
            (ROOT / "references" / "policies" / "repin_log.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        epoch = initial_binding["pin_epoch"]
        repin_row = next(row for row in repin_rows if row.get("epoch") == epoch)
        write_json(request_path, {
            "request_id": "synthetic-inert-rebind",
            "pin_epoch": epoch,
            "profile_sha256": initial_binding["profile_sha256"],
            "attestation_view_pin": "f" * 64,
            "exemplar_view_pin": initial_binding["exemplar_view_pin"],
            "delta_class": repin_row["delta_class"],
            "repin_log_ref": f"references/policies/repin_log.jsonl#epoch-{epoch}",
            "status": "pending",
        })
        inert_sha = sha(request_path)
        before_inert_archive = (project / "reviews" / "phase_state.json").read_bytes()
        refused = run(
            CHECKPOINT, "rebind-reader-policy", "--project-root", project,
            "--archive-stale-request", "--expected-request-sha256", "0" * 64,
            expected=4,
        )
        assert "AMC-REPIN-REQUEST-HASH" in refused.stdout
        assert request_path.is_file()
        run(
            CHECKPOINT, "rebind-reader-policy", "--project-root", project,
            "--archive-stale-request", "--expected-request-sha256", inert_sha,
        )
        stale_archives = list((project / "reviews").glob(f"repin_rebind_request.{epoch}.*.stale.json"))
        assert len(stale_archives) == 1 and not request_path.exists()
        stale = json.loads(stale_archives[0].read_text(encoding="utf-8"))
        assert stale["status"] == "archived_stale" and stale["request_sha256"] == inert_sha
        assert stale["request"]["request_id"] == "synthetic-inert-rebind"
        assert (project / "reviews" / "phase_state.json").read_bytes() == before_inert_archive
        write_json(request_path, {
            "request_id": "synthetic-planner-rebind",
            "pin_epoch": epoch,
            "profile_sha256": initial_binding["profile_sha256"],
            "attestation_view_pin": initial_binding["attestation_view_pin"],
            "exemplar_view_pin": initial_binding["exemplar_view_pin"],
            "delta_class": repin_row["delta_class"],
            "repin_log_ref": f"references/policies/repin_log.jsonl#epoch-{epoch}",
            "status": "pending",
        })
        current_request_sha = sha(request_path)
        refused = run(
            CHECKPOINT, "rebind-reader-policy", "--project-root", project,
            "--archive-stale-request", "--expected-request-sha256", current_request_sha,
            expected=4,
        )
        assert "AMC-REPIN-REQUEST-CURRENT" in refused.stdout and request_path.is_file()
        state_path = project / "reviews" / "phase_state.json"
        os.chmod(state_path, stat.S_IREAD)
        try:
            run(CHECKPOINT, "rebind-reader-policy", "--project-root", project)
            assert is_read_only(state_path), "Planner rebind must preserve the read-only state attribute"
        finally:
            os.chmod(state_path, stat.S_IREAD | stat.S_IWRITE)
        archive = project / "reviews" / f"repin_rebind_request.{epoch}.applied.json"
        applied = json.loads(archive.read_text(encoding="utf-8"))
        rebound = state(project)["milestone_framework"]["policy_bindings"]["reader_accessibility"]
        assert not request_path.exists() and applied["status"] == "applied"
        assert applied["applied_by"] == "planner" and rebound["pin_epoch"] == epoch
        assert rebound["transitions"] == initial_binding["transitions"]
        run(VALIDATOR, "--project-root", project)

        before_wrong_begin = (project / "reviews" / "phase_state.json").read_bytes()
        refused = run(CHECKPOINT, "begin", "--project-root", project, "--milestone", "M3", "--at", f"2026-07-19T00:00:{next(ticks):02d}Z", expected=4)
        assert "AMC-ORDER" in refused.stdout and (project / "reviews" / "phase_state.json").read_bytes() == before_wrong_begin
        run(CHECKPOINT, "begin", "--project-root", project, "--milestone", "M4", "--at", f"2026-07-19T00:00:{next(ticks):02d}Z")
        print("walk/M4-started", flush=True)
        before = state(project)["milestone_framework"]["milestones"]["M4"]
        assert before["status"] == "in_progress" and not before["artifacts"]
        assert set(before["policy_evidence"]) == {"profile_path", "profile_sha256", "resolved_sha256", "attestation_view_pin", "exemplar_view_pin"}
        run(VALIDATOR, "--project-root", project)

        consumed = publish(project, "M4", b"# M4 complete initial manuscript\n")
        forged_receipt = project / "reviews" / ".harness" / "milestones" / "checkpoints" / "copied_consumed_receipt.json"
        forged_receipt.write_bytes(consumed.read_bytes())
        forged_checkpoint = checkpoint_input(project, "M4", f"2026-07-19T00:00:{next(ticks):02d}Z")
        phase_before_forgery = (project / "reviews" / "phase_state.json").read_bytes()
        refused = run(CHECKPOINT, "record", "--project-root", project, "--milestone", "M4", "--receipt", forged_receipt, "--checkpoint", forged_checkpoint, "--at", f"2026-07-19T00:00:{next(ticks):02d}Z", expected=4)
        assert "APG-RECEIPT-INVALID" in refused.stdout and (project / "reviews" / "phase_state.json").read_bytes() == phase_before_forgery
        invalid_checkpoint = checkpoint_input(project, "M4", f"2026-07-19T00:00:{next(ticks):02d}Z", valid_m4=False)
        phase_before_refusal = (project / "reviews" / "phase_state.json").read_bytes()
        refused = run(CHECKPOINT, "record", "--project-root", project, "--milestone", "M4", "--receipt", consumed, "--checkpoint", invalid_checkpoint, "--at", f"2026-07-19T00:00:{next(ticks):02d}Z", expected=4)
        assert "AMC-CHECKPOINT" in refused.stdout and (project / "reviews" / "phase_state.json").read_bytes() == phase_before_refusal

        valid_checkpoint = checkpoint_input(project, "M4", f"2026-07-19T00:00:{next(ticks):02d}Z")
        checkpoint_bytes = valid_checkpoint.read_bytes()
        phase_before_mutation = (project / "reviews" / "phase_state.json").read_bytes()
        try:
            record_transaction(
                project, "M4", consumed, valid_checkpoint,
                f"2026-07-19T00:00:{next(ticks):02d}Z",
                _before_state_publish=lambda: valid_checkpoint.write_bytes(checkpoint_bytes + b" "),
            )
        except MilestoneTransactionError as exc:
            assert exc.code == "AMC-DEPENDENCY-CHANGED", exc.code
        else:
            raise AssertionError("record accepted a checkpoint mutated after validation")
        assert (project / "reviews" / "phase_state.json").read_bytes() == phase_before_mutation
        failed_snapshot = project / "reviews" / ".harness" / "snapshots" / "M4" / f"{sha(project / PATHS['M4'])}.md"
        assert not failed_snapshot.exists(), "failed record left an unbound M4 snapshot"
        valid_checkpoint.write_bytes(checkpoint_bytes)
        run(CHECKPOINT, "record", "--project-root", project, "--milestone", "M4", "--receipt", consumed, "--checkpoint", valid_checkpoint, "--at", f"2026-07-19T00:00:{next(ticks):02d}Z")
        after = state(project)["milestone_framework"]["milestones"]["M4"]
        manuscript = after["artifacts"][0]
        assert after["policy_evidence"]["manuscript_sha256"] == manuscript["sha256"]
        assert after["policy_evidence"]["phase"] == "Ph1"
        assert after["policy_evidence"]["cycle_id"] == "m4-initial-assembly-001"
        run(VALIDATOR, "--project-root", project)

        # Initial assembly is not the end of M4. A later, receipt-scoped
        # Generator revision must be re-recordable without rewriting the first
        # deliverable event or its exact-byte evidence.
        initial_digest = manuscript["sha256"]
        initial_event_count = len(state(project)["milestone_framework"]["events"])
        advance_m4_fixture_to_ph2(project)
        run(PHASE_VALIDATOR, "--project-root", project)
        derived = json.loads(run(CHECKPOINT, "derive", "--project-root", project).stdout)
        assert derived == {"status": "READY", "milestone": "M4", "action": "revise", "authority_mode": "direct_local"}, derived
        revised_consumed = publish(
            project, "M4", b"# M4 substantively revised manuscript\n",
            label="ph2-revision",
        )
        revised_checkpoint = checkpoint_input(
            project, "M4", f"2026-07-19T00:00:{next(ticks):02d}Z",
            label="ph2-revision", phase="Ph2", cycle_id="m4-ph2-revision-001",
        )
        run(
            CHECKPOINT, "record", "--project-root", project, "--milestone", "M4",
            "--receipt", revised_consumed, "--checkpoint", revised_checkpoint,
            "--at", f"2026-07-19T00:00:{next(ticks):02d}Z",
        )
        revised = state(project)["milestone_framework"]
        revised_m4 = revised["milestones"]["M4"]
        assert revised_m4["artifacts"][0]["sha256"] != initial_digest
        assert revised_m4["policy_evidence"]["phase"] == "Ph2"
        assert revised_m4["policy_evidence"]["cycle_id"] == "m4-ph2-revision-001"
        assert len(revised["events"]) == initial_event_count + 3
        run(VALIDATOR, "--project-root", project)
        valid_checkpoint = revised_checkpoint

        approval = approval_input(project, "M4", f"2026-07-19T00:00:{next(ticks):02d}Z")
        phase_before_accept = (project / "reviews" / "phase_state.json").read_bytes()
        refused = run(CHECKPOINT, "accept", "--project-root", project, "--milestone", "M4", "--checkpoint", valid_checkpoint, "--approval-evidence", approval, "--at", f"2026-07-19T00:00:{next(ticks):02d}Z", expected=4)
        assert "AMC-M4-NOT-CONVERGED" in refused.stdout
        assert (project / "reviews" / "phase_state.json").read_bytes() == phase_before_accept
        assert not (project / "reviews" / ".harness" / "handoffs" / "M4_to_M5.json").exists()

        # A live claim cannot be recovered, and there is no TTL bypass.
        claim = project / "reviews" / ".harness" / "milestones" / "claims" / "transaction.lock"
        write_json(claim, {"schema_version": "1.0.0", "pid": __import__("os").getpid(), "host": __import__("platform").node(), "operation": "test", "started_at": "2026-07-19T00:00:00Z"})
        refused = run(CHECKPOINT, "recover", "--project-root", project, "--acknowledgement", "inspected-milestone-state-and-journal", expected=4)
        assert "AMC-RECOVERY-LIVE" in refused.stdout and claim.exists()
        claim.unlink()

        write_json(claim, {"schema_version": "1.0.0", "pid": 2147483647, "host": "foreign-host", "operation": "accept:M4", "started_at": "2026-07-19T00:00:00Z"})
        refused = run(CHECKPOINT, "recover", "--project-root", project, "--acknowledgement", "inspected-milestone-state-and-journal", expected=4)
        assert "AMC-RECOVERY-FOREIGN" in refused.stdout and claim.exists()
        claim.unlink()

        # Adversarial residue injection is outside the positive public walk:
        # inspected recovery archives both a dead claim and an unbound F9.
        orphan = project / "reviews" / ".harness" / "handoffs" / "M4_to_M5.json"
        write_json(orphan, {"synthetic_orphan": True})
        write_json(claim, {"schema_version": "1.0.0", "pid": 2147483647, "host": __import__("platform").node(), "operation": "accept:M4", "started_at": "2026-07-19T00:00:00Z"})
        run(CHECKPOINT, "recover", "--project-root", project, "--acknowledgement", "inspected-milestone-state-and-journal")
        assert not claim.exists() and not orphan.exists()
        journal = project / "reviews" / ".harness" / "milestones" / "journal"
        assert list(journal.glob("recovered-claim-*.json")) and list(journal.glob("orphan-M4_to_M5-*.json"))

        # Separate acceptance fixture: phase ownership is prepared explicitly,
        # then the milestone acceptance itself remains public-command-only.
        converge_m4_fixture(project)
        run(PHASE_VALIDATOR, "--project-root", project)
        policy = m4_acceptance_policy_input(project)
        approval = approval_input(project, "M4", f"2026-07-19T00:00:{next(ticks):02d}Z")
        approval_bytes = approval.read_bytes()
        phase_before_accept_mutation = (project / "reviews" / "phase_state.json").read_bytes()
        try:
            accept_transaction(
                project, "M4", valid_checkpoint, approval,
                f"2026-07-19T00:00:{next(ticks):02d}Z", policy,
                _before_state_publish=lambda: approval.write_bytes(approval_bytes + b" "),
            )
        except MilestoneTransactionError as exc:
            assert exc.code == "AMC-DEPENDENCY-CHANGED", exc.code
        else:
            raise AssertionError("accept published state after approval evidence mutation")
        assert (project / "reviews" / "phase_state.json").read_bytes() == phase_before_accept_mutation
        assert not (project / "reviews" / ".harness" / "handoffs" / "M4_to_M5.json").exists()
        approval.write_bytes(approval_bytes)
        run(CHECKPOINT, "accept", "--project-root", project, "--milestone", "M4", "--checkpoint", valid_checkpoint, "--approval-evidence", approval, "--policy-evidence", policy, "--at", f"2026-07-19T00:00:{next(ticks):02d}Z")
        accepted = state(project)["milestone_framework"]["milestones"]["M4"]
        assert accepted["status"] == "accepted" and accepted["policy_evidence"]["phase"] == "Ph3"
        run(VALIDATOR, "--project-root", project)

    print("OK assignment_milestone_checkpoint_smoketest")
    return 0


if __name__ == "__main__":
    with semantic_graph_fixture_environment():
        raise SystemExit(main())
