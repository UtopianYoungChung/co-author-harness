#!/usr/bin/env python3
"""Regression tests for the assignment-derived milestone drafting gate."""

from __future__ import annotations

import copy
import hashlib
import json
import locale
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from assignment_fixture_support import package_scratch


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "assignment_process_gate.py"
PROFILE = ROOT / "references" / "policies" / "course_essay_milestones.v1.json"
RECEIPT_SCHEMA = ROOT / "references" / "schemas" / "assignment_gate_receipt.schema.json"
RECEIPT_TEMPLATE = ROOT / "references" / "templates" / "assignment_gate_receipt.json"


sys.path.insert(0, str(Path(__file__).resolve().parent))

# `sha256` and `write_wiki_evidence` were defined here and needed by a second
# suite. Extracted to shared support rather than copied: two copies of one
# fixture drift, and the copy in the newer file quietly becomes a different --
# and weaker -- idea of "valid". Imported back so this suite keeps using the
# same fixture it always did, and so both suites fail together if it breaks.
from assignment_fixture_support import (  # noqa: E402
    sha256, write_wiki_evidence, write_valid_contract,
)


def run_gate(
    project: Path,
    stage: str | None = None,
    target_milestone: str | None = None,
    exemplar_conditioning: bool = False,
    emit_receipt: Path | None = None,
    verify_receipt: Path | None = None,
    control_transition_id: str | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(GATE), "--project-root", str(project)]
    if stage is not None:
        command.extend(["--stage", stage])
    if target_milestone is not None:
        command.extend(["--target-milestone", target_milestone])
    if exemplar_conditioning:
        command.append("--exemplar-conditioning")
    if emit_receipt is not None:
        command.extend(["--emit-receipt", str(emit_receipt)])
    if verify_receipt is not None:
        command.extend(["--verify-receipt", str(verify_receipt)])
    if control_transition_id is not None:
        command.extend(["--control-transition-id", control_transition_id])
    return subprocess.run(
        command,
        text=True, encoding="utf-8", errors="replace",
        capture_output=True,
        check=False,
    )


def main() -> int:
    if not GATE.is_file():
        raise AssertionError("assignment_process_gate.py is missing")
    if not PROFILE.is_file():
        raise AssertionError("course essay milestone profile is missing")
    if not RECEIPT_SCHEMA.is_file():
        raise AssertionError("assignment gate receipt schema is missing")
    if not RECEIPT_TEMPLATE.is_file():
        raise AssertionError("assignment gate receipt template is missing")
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    deliverables = profile["deliverables"]
    assert "preliminary focus" in deliverables["M1"]["required_elements"]
    assert "a frozen thesis" in deliverables["M1"]["must_not_be_treated_as"]
    assert "relevant course readings" in deliverables["M2"]["required_elements"]
    assert "how the application sharpens the originating idea" in deliverables["M3"]["required_elements"]
    assert "complete argument" in deliverables["M4"]["required_elements"]
    assert deliverables["FINAL"]["prerequisites"] == ["M1", "M2", "M3", "M4"]
    assert "a fifth assigned milestone" in deliverables["FINAL"]["must_not_be_treated_as"]

    dummy_governed = Path(tempfile.mkdtemp(prefix="apg-dummy-governed-"))
    extra_roots = [
        item
        for item in os.environ.get("COAUTHOR_EXTRA_GOVERNED_ROOTS", "").split(os.pathsep)
        if item
    ]
    extra_roots.append(str(dummy_governed))
    os.environ["COAUTHOR_EXTRA_GOVERNED_ROOTS"] = os.pathsep.join(extra_roots)

    # F1 regression: milestone_framework.mode describes lifecycle format, not
    # assignment-process applicability.  Treating mode:native + a missing
    # contract as an implicit N/A would turn a deleted or never-resolved
    # controlling brief into authorization to draft.
    with tempfile.TemporaryDirectory() as temp:
        native = Path(temp)
        reviews = native / "reviews"
        reviews.mkdir()
        (reviews / "phase_state.json").write_text(
            json.dumps({"milestone_framework": {"mode": "native"}}) + "\n",
            encoding="utf-8",
        )
        unbound = run_gate(native, "draft", "M1")
        assert unbound.returncode == 4, unbound.stdout + unbound.stderr
        assert "APG-CONTRACT-MISSING" in unbound.stdout
        assert "mode:native does not make the assignment process NOT_APPLICABLE" in unbound.stdout

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        reviews = root / "reviews"
        reviews.mkdir()

        # The single shared fixture -- see scripts/assignment_fixture_support.py.
        contract = write_valid_contract(root)
        source = root / "course-assignment.pdf"
        phase_state = {
            "milestone_framework": {
                "mode": "native",
                "milestones": {
                    key: {"status": "accepted" if key != "M4" else "feedback_pending"}
                    for key in ("M1", "M2", "M3", "M4", "M5")
                }
            }
        }
        (reviews / "phase_state.json").write_text(
            json.dumps(phase_state, indent=2) + "\n", encoding="utf-8"
        )

        for key in ("M1", "M2", "M3", "M4"):
            phase_state["milestone_framework"]["milestones"][key]["status"] = "not_started"
        (reviews / "phase_state.json").write_text(
            json.dumps(phase_state, indent=2) + "\n", encoding="utf-8"
        )
        before_gate = (reviews / "phase_state.json").read_bytes()
        receipt = (
            reviews
            / ".harness"
            / "assignment"
            / "ready"
            / "gate_receipt_M1_20260715T000000Z.json"
        )
        receipt_argument = receipt.relative_to(root)
        missing_receipt = run_gate(root, verify_receipt=receipt_argument)
        assert (
            missing_receipt.returncode == 4
            and "APG-RECEIPT-MISSING" in missing_receipt.stdout
        ), missing_receipt.stdout + missing_receipt.stderr

        m1 = run_gate(root, "draft", "M1", emit_receipt=receipt_argument)
        assert m1.returncode == 0 and "target=M1" in m1.stdout, m1.stdout + m1.stderr
        assert receipt.is_file(), "READY gate must emit the requested receipt"
        receipt_record = json.loads(receipt.read_text(encoding="utf-8"))
        assert receipt_record["schema_version"] == "2.2.0"
        assert receipt_record["control_transition"] is None
        assert "status" not in receipt_record
        assert "consumed_at" not in receipt_record
        assert receipt_record["stage"] == "draft"
        assert receipt_record["target_milestone"] == "M1"
        assert receipt_record["authorized_role"] == "generator"
        assert receipt_record["authorized_writes"] == [
            {"path": "milestones/M1_project_memo.md", "mode": "replace"},
            {"path": "manuscript/revision_log.md", "mode": "append"},
        ]
        assert receipt_record["project_root_resolved"] == str(root.resolve())
        assert receipt_record["primary_deliverable_path"] == "milestones/M1_project_memo.md"
        assert receipt_record["primary_deliverable_path"] in receipt_record["authorized_paths"]
        assert receipt_record["assignment_contract_sha256"] == sha256(
            reviews / "assignment_contract.json"
        )
        assert receipt_record["phase_state_sha256"] == sha256(
            reviews / "phase_state.json"
        )
        assert receipt_record["profile_sha256"] == sha256(PROFILE)
        assert receipt_record["exemplar_conditioning"] is True, (
            "every academic draft gate must bind centroid conditioning, including M1"
        )
        verified = run_gate(root, verify_receipt=receipt_argument)
        assert (
            verified.returncode == 0 and "VERIFIED assignment-process receipt" in verified.stdout
        ), verified.stdout + verified.stderr

        phase_before_drift = (reviews / "phase_state.json").read_bytes()
        drifted_state = copy.deepcopy(phase_state)
        drifted_state["milestone_framework"]["milestones"]["M1"]["status"] = "in_progress"
        (reviews / "phase_state.json").write_text(
            json.dumps(drifted_state, indent=2) + "\n", encoding="utf-8"
        )
        stale_receipt = run_gate(root, verify_receipt=receipt_argument)
        assert (
            stale_receipt.returncode == 4
            and "APG-RECEIPT-STALE" in stale_receipt.stdout
        ), stale_receipt.stdout + stale_receipt.stderr
        (reviews / "phase_state.json").write_bytes(phase_before_drift)

        consumed_path = receipt.parent.parent / "consumed" / receipt.name
        consumed_path.parent.mkdir(parents=True)
        receipt.replace(consumed_path)
        consumed_receipt = run_gate(root, verify_receipt=consumed_path.relative_to(root))
        assert (
            consumed_receipt.returncode == 4
            and "APG-RECEIPT-CONSUMED" in consumed_receipt.stdout
        ), consumed_receipt.stdout + consumed_receipt.stderr

        # The emitter must inspect the lexical control path before resolving it;
        # otherwise a junctioned/symlinked ready directory can receive a valid
        # receipt outside the project tree before transaction preflight runs.
        ready_dir = receipt.parent
        external_ready = root / "external-ready"
        external_ready.mkdir()
        ready_dir.rmdir()
        linked = False
        try:
            os.symlink(external_ready, ready_dir, target_is_directory=True)
            linked = True
        except OSError:
            ready_dir.mkdir()
        if linked:
            escaped_name = "gate_receipt_M1_20260715T000001Z.json"
            escaped_argument = receipt_argument.parent / escaped_name
            escaped = run_gate(root, "draft", "M1", emit_receipt=escaped_argument)
            assert (
                escaped.returncode == 4
                and "APG-RECEIPT-PATH-INVALID" in escaped.stdout
            ), escaped.stdout + escaped.stderr
            assert not (external_ready / escaped_name).exists()
            ready_dir.unlink()
            ready_dir.mkdir()

        if os.name == "nt":
            junction_target = root / "external-junction-ready"
            junction_target.mkdir()
            ready_dir.rmdir()
            junction = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(ready_dir), str(junction_target)],
                text=True,
                encoding=locale.getpreferredencoding(False),
                errors="replace",
                capture_output=True,
                check=False,
            )
            if junction.returncode != 0:
                ready_dir.mkdir()
                raise AssertionError(
                    "Windows junction regression could not create its fixture: "
                    + junction.stdout
                    + junction.stderr
                )
            junction_name = "gate_receipt_M1_20260715T000002Z.json"
            junction_argument = receipt_argument.parent / junction_name
            escaped = run_gate(root, "draft", "M1", emit_receipt=junction_argument)
            assert (
                escaped.returncode == 4
                and "APG-RECEIPT-PATH-INVALID" in escaped.stdout
            ), escaped.stdout + escaped.stderr
            assert not (junction_target / junction_name).exists()
            ready_dir.rmdir()
            ready_dir.mkdir()
        assert (reviews / "phase_state.json").read_bytes() == before_gate, "gate must not write acceptance"
        premature_m2 = run_gate(root, "draft", "M2")
        assert (
            premature_m2.returncode == 4 and "APG-SEQUENCE-M2" in premature_m2.stdout
        ), premature_m2.stdout + premature_m2.stderr

        missing_target = run_gate(root, "draft")
        assert (
            missing_target.returncode == 4
            and "APG-SEQUENCE-TARGET" in missing_target.stdout
        ), missing_target.stdout + missing_target.stderr

        phase_state["milestone_framework"]["milestones"].update(
            {
                "M1": {"status": "accepted"},
                "M2": {"status": "not_started"},
                "M3": {"status": "not_started"},
                "M4": {"status": "not_started"},
            }
        )
        (reviews / "phase_state.json").write_text(
            json.dumps(phase_state, indent=2) + "\n", encoding="utf-8"
        )
        m2 = run_gate(root, "draft", "M2")
        assert m2.returncode == 0 and "target=M2" in m2.stdout, m2.stdout + m2.stderr

        m3 = run_gate(root, "draft", "M3")
        assert m3.returncode == 4 and "APG-SEQUENCE-M3" in m3.stdout, m3.stdout + m3.stderr

        m4_blocked = run_gate(root, "draft", "M4")
        assert (
            m4_blocked.returncode == 4 and "APG-SEQUENCE-M4" in m4_blocked.stdout
        ), m4_blocked.stdout + m4_blocked.stderr

        phase_state["milestone_framework"]["milestones"]["M2"]["status"] = "accepted"
        (reviews / "phase_state.json").write_text(
            json.dumps(phase_state, indent=2) + "\n", encoding="utf-8"
        )
        m3_ready = run_gate(root, "draft", "M3")
        assert m3_ready.returncode == 0 and "target=M3" in m3_ready.stdout, m3_ready.stdout + m3_ready.stderr
        phase_state["milestone_framework"]["milestones"]["M3"]["status"] = "accepted"
        (reviews / "phase_state.json").write_text(
            json.dumps(phase_state, indent=2) + "\n", encoding="utf-8"
        )
        no_wiki = run_gate(root, "draft", "M4")
        assert (
            no_wiki.returncode == 4
            and "APG-WIKI-GROUNDING-MISSING" in no_wiki.stdout
        ), no_wiki.stdout + no_wiki.stderr

        evidence_path = write_wiki_evidence(root, phase_state)
        m4 = run_gate(root, "draft", "M4")
        assert m4.returncode == 0 and "target=M4" in m4.stdout, m4.stdout + m4.stderr

        m2_exemplar = run_gate(root, "draft", "M2", exemplar_conditioning=True)
        assert m2_exemplar.returncode == 0, m2_exemplar.stdout + m2_exemplar.stderr
        m4_exemplar = run_gate(root, "draft", "M4", exemplar_conditioning=True)
        assert m4_exemplar.returncode == 0, m4_exemplar.stdout + m4_exemplar.stderr

        contract["dennett_exemplar_status"] = "pending"
        (reviews / "assignment_contract.json").write_text(
            json.dumps(contract, indent=2) + "\n", encoding="utf-8"
        )
        dennett_pending = run_gate(root, "draft", "M4", exemplar_conditioning=True)
        assert (
            dennett_pending.returncode == 0
            and "[ADVISORY] APG-EXEMPLAR-DENNETT-PENDING" in dennett_pending.stdout
        ), dennett_pending.stdout + dennett_pending.stderr

        references = root / "references" / "REFERENCES.md"
        references.write_text("# Drifted references\n", encoding="utf-8")
        stale = run_gate(root, "draft", "M4")
        assert (
            stale.returncode == 4 and "APG-WIKI-GROUNDING-STALE" in stale.stdout
        ), stale.stdout + stale.stderr
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        evidence["references_sha256"] = sha256(references)
        evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        phase_state["milestone_framework"]["milestones"]["M3"]["policy_evidence"]["wiki_grounding"]["evidence_sha256"] = sha256(evidence_path)
        (reviews / "phase_state.json").write_text(
            json.dumps(phase_state, indent=2) + "\n", encoding="utf-8"
        )

        missing = root / "missing"
        (missing / "reviews").mkdir(parents=True)
        absent_receipt = Path(
            "reviews/.harness/assignment/ready/gate_receipt_M1_20260715T000000Z.json"
        )
        absent = run_gate(
            missing, "draft", "M1", emit_receipt=absent_receipt
        )
        assert absent.returncode == 4 and "APG-CONTRACT-MISSING" in absent.stdout, absent.stdout + absent.stderr
        assert not (missing / absent_receipt).exists(), "missing contract must not emit READY receipt"

        blocked = run_gate(root, "final")
        assert blocked.returncode == 4 and "APG-PREREQUISITE-M4" in blocked.stdout, blocked.stdout + blocked.stderr

        phase_state["milestone_framework"]["milestones"]["M4"]["status"] = "accepted"
        phase_state["milestone_framework"]["milestones"]["M5"]["status"] = "in_progress"
        phase_state["terminal_phase_reached"] = False
        phase_state["terminal_round_id"] = None
        phase_state["sections"] = {"body": {"current_phase": "Ph4"}}
        (reviews / "phase_state.json").write_text(
            json.dumps(phase_state, indent=2) + "\n", encoding="utf-8"
        )
        draft_final = run_gate(root, "draft", "FINAL")
        assert (
            draft_final.returncode == 4 and "APG-SEQUENCE-TARGET" in draft_final.stdout
        ), draft_final.stdout + draft_final.stderr

        final = run_gate(root, "final")
        assert final.returncode == 0 and "READY" in final.stdout, final.stdout + final.stderr
        policy_evidence = phase_state["milestone_framework"]["milestones"]["M3"]["policy_evidence"]
        policy_evidence.pop("wiki_grounding")
        opt_out_evidence = reviews / "wiki_opt_out_approval.txt"
        opt_out_evidence.write_text("User approved wiki-grounding opt-out for this fixture.\n", encoding="utf-8")
        policy_evidence["wiki_grounding_opt_out"] = {
            "authority": "planner",
            "reason": "Synthetic opt-out test.",
            "evidence_path": opt_out_evidence.relative_to(root).as_posix(),
            "evidence_sha256": sha256(opt_out_evidence),
        }
        (reviews / "phase_state.json").write_text(
            json.dumps(phase_state, indent=2) + "\n", encoding="utf-8"
        )
        invalid_opt_out = run_gate(root, "draft", "M4")
        assert (
            invalid_opt_out.returncode == 4
            and "APG-WIKI-OPT-OUT-INVALID" in invalid_opt_out.stdout
        ), invalid_opt_out.stdout + invalid_opt_out.stderr
        policy_evidence["wiki_grounding_opt_out"]["authority"] = "user"
        (reviews / "phase_state.json").write_text(
            json.dumps(phase_state, indent=2) + "\n", encoding="utf-8"
        )
        valid_opt_out = run_gate(root, "draft", "M4")
        assert valid_opt_out.returncode == 0, valid_opt_out.stdout + valid_opt_out.stderr

        # Circulate: four current accepted hashes latch restage of M4 while M3 is reopened.
        phase_state["milestone_framework"]["milestones"]["M3"]["status"] = "reopened"
        (reviews / "phase_state.json").write_text(
            json.dumps(phase_state, indent=2) + "\n", encoding="utf-8"
        )
        m4_circulate = run_gate(root, "draft", "M4")
        assert m4_circulate.returncode == 0 and "target=M4" in m4_circulate.stdout, (
            m4_circulate.stdout + m4_circulate.stderr
        )
        blocked_final_reopen = run_gate(root, "final")
        assert (
            blocked_final_reopen.returncode == 4
            and "APG-PREREQUISITE-M3" in blocked_final_reopen.stdout
        ), blocked_final_reopen.stdout + blocked_final_reopen.stderr

        manuscript = root / "milestones" / "M4_complete_paper_draft.md"
        manuscript.parent.mkdir(parents=True, exist_ok=True)
        manuscript.write_text("# File presence is not materials-in-play.\n", encoding="utf-8")

        # Joseph declaration does not skip first-start of a not_started M4.
        phase_state["milestone_framework"]["milestones"]["M3"]["status"] = "reopened"
        phase_state["milestone_framework"]["milestones"]["M4"]["status"] = "not_started"
        declaration_evidence = reviews / "materials_in_play.txt"
        declaration_evidence.write_text("Joseph: materials are in play.\n", encoding="utf-8")
        phase_state["milestone_framework"]["materials_in_play"] = {
            "authority": "user",
            "declared_at": "2026-08-21T00:00:00Z",
            "evidence_path": declaration_evidence.relative_to(root).as_posix(),
            "evidence_sha256": sha256(declaration_evidence),
            "reason": "Enough materials gathered through M1-M4.",
        }
        (reviews / "phase_state.json").write_text(
            json.dumps(phase_state, indent=2) + "\n", encoding="utf-8"
        )
        m4_first_start = run_gate(root, "draft", "M4")
        assert (
            m4_first_start.returncode == 4 and "APG-SEQUENCE-M4" in m4_first_start.stdout
        ), m4_first_start.stdout + m4_first_start.stderr

        # Started M4 + Joseph declaration + M3 reopened: restage is legal.
        phase_state["milestone_framework"]["milestones"]["M4"]["status"] = "in_progress"
        phase_state["milestone_framework"]["milestones"]["M3"]["status"] = "reopened"
        (reviews / "phase_state.json").write_text(
            json.dumps(phase_state, indent=2) + "\n", encoding="utf-8"
        )
        m4_declared = run_gate(root, "draft", "M4")
        assert m4_declared.returncode == 0 and "target=M4" in m4_declared.stdout, (
            m4_declared.stdout + m4_declared.stderr
        )

        # Invalid declaration does not latch circulation by itself.
        phase_state["milestone_framework"]["milestones"]["M2"]["status"] = "not_started"
        phase_state["milestone_framework"]["milestones"]["M3"]["status"] = "not_started"
        phase_state["milestone_framework"]["materials_in_play"]["authority"] = "planner"
        (reviews / "phase_state.json").write_text(
            json.dumps(phase_state, indent=2) + "\n", encoding="utf-8"
        )
        invalid_decl = run_gate(root, "draft", "M4")
        assert (
            invalid_decl.returncode == 4
            and "APG-MATERIALS-IN-PLAY-INVALID" in invalid_decl.stdout
            and "APG-SEQUENCE-M4" in invalid_decl.stdout
        ), invalid_decl.stdout + invalid_decl.stderr

        phase_state["milestone_framework"].pop("materials_in_play")
        for key in ("M1", "M2", "M3", "M4"):
            phase_state["milestone_framework"]["milestones"][key]["status"] = "accepted"
        (reviews / "phase_state.json").write_text(
            json.dumps(phase_state, indent=2) + "\n", encoding="utf-8"
        )

        phase_state["milestone_framework"]["mode"] = "legacy"
        (reviews / "phase_state.json").write_text(
            json.dumps(phase_state, indent=2) + "\n", encoding="utf-8"
        )
        legacy_gate = run_gate(root, "draft", "M1")
        assert (
            legacy_gate.returncode == 4
            and "APG-SEQUENCE-LEGACY" in legacy_gate.stdout
            and "migration" in legacy_gate.stdout.lower()
            and "acceptance" in legacy_gate.stdout.lower()
        ), legacy_gate.stdout + legacy_gate.stderr
        phase_state["milestone_framework"]["mode"] = "native"
        (reviews / "phase_state.json").write_text(
            json.dumps(phase_state, indent=2) + "\n", encoding="utf-8"
        )

        unauthorized = copy.deepcopy(contract)
        unauthorized["professor_copy_policy"] = "harness_generates_professor_copy"
        (reviews / "assignment_contract.json").write_text(
            json.dumps(unauthorized, indent=2) + "\n", encoding="utf-8"
        )
        boundary = run_gate(root, "draft", "M1")
        assert boundary.returncode == 4 and "APG-PROFESSOR-COPY-AUTHORITY" in boundary.stdout, boundary.stdout + boundary.stderr

    from assignment_process_gate import named_draft_permitted, resolve_circulation
    from full_run_contract_check import derive_active_target

    empty = Path(".")
    gather_framework = {
        "milestones": {
            key: {"status": "not_started"}
            for key in ("M1", "M2", "M3", "M4", "M5")
        }
    }
    mode, reason, findings = resolve_circulation(empty, gather_framework)
    assert (mode, reason, findings) == ("gather", "gather", [])
    assert named_draft_permitted(empty, gather_framework, "M1")
    assert not named_draft_permitted(empty, gather_framework, "M2")
    assert not named_draft_permitted(empty, gather_framework, "M4")
    assert not named_draft_permitted(empty, gather_framework, "FINAL")

    gather_framework["milestones"]["M1"]["status"] = "accepted"
    assert named_draft_permitted(empty, gather_framework, "M2")
    assert not named_draft_permitted(empty, gather_framework, "M4")

    ever_framework = {
        "milestones": {
            "M1": {"status": "reopened"},
            "M2": {"status": "accepted"},
            "M3": {"status": "accepted"},
            "M4": {"status": "in_progress"},
            "M5": {"status": "not_started"},
        },
        "events": [{"event_type": "milestone_accepted", "milestone": "M4"}],
    }
    mode, reason, findings = resolve_circulation(empty, ever_framework)
    assert mode == "circulate" and reason == "four_ever_accepted" and findings == []
    assert named_draft_permitted(empty, ever_framework, "M4")
    assert named_draft_permitted(empty, ever_framework, "M1")
    assert not named_draft_permitted(empty, ever_framework, "FINAL")

    closed_framework = copy.deepcopy(ever_framework)
    closed_framework["milestones"]["M5"]["status"] = "accepted"
    assert not named_draft_permitted(empty, closed_framework, "M4")

    with tempfile.TemporaryDirectory() as temp:
        proj = Path(temp)
        reviews = proj / "reviews"
        reviews.mkdir()
        (reviews / "phase_state.json").write_text(
            json.dumps({"milestone_framework": ever_framework}, indent=2) + "\n",
            encoding="utf-8",
        )
        target, errors = derive_active_target(proj)
        assert target == "M1" and errors == []
        named, named_errors = derive_active_target(proj, requested="M4")
        assert named == "M4" and named_errors == []
        refused, refused_errors = derive_active_target(proj, requested="FINAL")
        assert refused is None and any(
            row.get("code") == "FRC-MILESTONE-ORDER" for row in refused_errors
        )

    # Live M4 evaluate: stale bootstrap (M1 in_progress, M2/M3 not_started)
    # must not let dest-safe sequence/source/wiki occupy the scholarly path.
    # File presence is never acceptance. FINAL apply still needs current hashes.
    with tempfile.TemporaryDirectory(prefix="apg-evaluate-guardrail-") as temp:
        from assignment_milestone_transaction import (
            MilestoneTransactionError,
            derive as derive_checkpoint,
        )

        root = Path(temp)
        reviews = root / "reviews"
        reviews.mkdir()
        contract = write_valid_contract(root)
        source = root / "course-assignment.pdf"
        source.write_bytes(b"stale assignment source after hash bind\n")
        manuscript = root / "milestones" / "M4_complete_paper_draft.md"
        manuscript.parent.mkdir(parents=True, exist_ok=True)
        manuscript.write_text("# Already-staged M4 bytes are not acceptance.\n", encoding="utf-8")
        stale_framework = {
            "mode": "native",
            "milestones": {
                "M1": {"status": "in_progress"},
                "M2": {"status": "not_started"},
                "M3": {"status": "not_started"},
                "M4": {"status": "not_started"},
                "M5": {"status": "not_started"},
            },
        }
        (reviews / "phase_state.json").write_text(
            json.dumps({"milestone_framework": stale_framework}, indent=2) + "\n",
            encoding="utf-8",
        )

        draft_m4 = run_gate(root, "draft", "M4")
        assert (
            draft_m4.returncode == 4
            and "APG-SEQUENCE-M4" in draft_m4.stdout
            and "APG-SOURCE-HASH" in draft_m4.stdout
            and "APG-WIKI-GROUNDING-MISSING" in draft_m4.stdout
        ), draft_m4.stdout + draft_m4.stderr

        evaluate_m4 = run_gate(root, "evaluate", "M4")
        assert evaluate_m4.returncode == 0, evaluate_m4.stdout + evaluate_m4.stderr
        assert "EVALUATE-ADMITTED" in evaluate_m4.stdout, evaluate_m4.stdout
        assert "READY assignment-process" not in evaluate_m4.stdout, evaluate_m4.stdout
        for code in (
            "APG-SEQUENCE-M4",
            "APG-SOURCE-HASH",
            "APG-WIKI-GROUNDING-MISSING",
        ):
            assert code not in evaluate_m4.stdout, evaluate_m4.stdout + evaluate_m4.stderr

        evaluate_receipt = Path(
            "reviews/.harness/assignment/ready/gate_receipt_M4_20260821T000000Z.json"
        )
        evaluate_emit = run_gate(
            root, "evaluate", "M4", emit_receipt=evaluate_receipt
        )
        assert (
            evaluate_emit.returncode == 4
            and "APG-RECEIPT-INVALID" in evaluate_emit.stdout
        ), evaluate_emit.stdout + evaluate_emit.stderr
        assert not (root / evaluate_receipt).exists(), (
            "evaluate must not mint a write-authorizing READY receipt"
        )

        evaluate_final = run_gate(root, "evaluate", "FINAL")
        assert (
            evaluate_final.returncode == 4
            and "APG-SEQUENCE-TARGET" in evaluate_final.stdout
        ), evaluate_final.stdout + evaluate_final.stderr

        blocked_final = run_gate(root, "final")
        assert (
            blocked_final.returncode == 4
            and "APG-PREREQUISITE-M1" in blocked_final.stdout
        ), blocked_final.stdout + blocked_final.stderr

        hole, hole_errors = derive_active_target(root)
        assert hole == "M1" and hole_errors == []
        dispatch_named, dispatch_errors = derive_active_target(root, requested="M4")
        assert dispatch_named is None and any(
            row.get("code") == "FRC-MILESTONE-ORDER" for row in dispatch_errors
        )
        evaluate_named, evaluate_errors = derive_active_target(
            root, requested="M4", purpose="evaluate"
        )
        assert evaluate_named == "M4" and evaluate_errors == []
        evaluate_final_named, evaluate_final_errors = derive_active_target(
            root, requested="FINAL", purpose="evaluate"
        )
        assert evaluate_final_named is None and any(
            row.get("code") == "FRC-MILESTONE-ORDER" for row in evaluate_final_errors
        )

        try:
            fallback = derive_checkpoint(root, requested="M4")
        except MilestoneTransactionError as exc:
            assert exc.code == "AMC-ORDER", exc.code
        else:
            raise AssertionError(
                "named M4 dispatch must refuse rather than bind another milestone: "
                + repr(fallback)
            )
        evaluated = derive_checkpoint(root, requested="M4", purpose="evaluate")
        assert evaluated == {
            "status": "READY",
            "milestone": "M4",
            "action": "evaluate",
            "authority_mode": evaluated.get("authority_mode"),
        }, evaluated
        assert evaluated["authority_mode"] in {"direct_local", "shipment_only"}

        phase_path = reviews / "phase_state.json"
        pre_hash = hashlib.sha256(phase_path.read_bytes()).hexdigest()
        defaulted = derive_checkpoint(root)
        assert defaulted["status"] == "READY"
        assert defaulted["milestone"] == "M1"
        assert defaulted["action"] == "draft", defaulted
        assert defaulted["authority_mode"] in {"direct_local", "shipment_only"}
        named_hole = derive_checkpoint(root, requested="M1")
        assert named_hole == defaulted, named_hole
        try:
            derive_checkpoint(root, requested="M2")
        except MilestoneTransactionError as exc:
            assert exc.code == "AMC-ORDER", exc.code
        else:
            raise AssertionError("named M2 dispatch must refuse before materials-in-play")
        try:
            derive_checkpoint(root, purpose="evaluate")
        except MilestoneTransactionError as exc:
            assert exc.code == "AMC-ORDER", exc.code
        else:
            raise AssertionError("unnamed evaluate must refuse")
        try:
            derive_checkpoint(root, requested="M9", purpose="evaluate")
        except MilestoneTransactionError as exc:
            assert exc.code == "AMC-ORDER", exc.code
        else:
            raise AssertionError("invalid evaluate target must refuse")
        try:
            derive_checkpoint(root, requested="FINAL", purpose="evaluate")
        except MilestoneTransactionError as exc:
            assert exc.code == "AMC-ORDER", exc.code
        else:
            raise AssertionError("FINAL evaluate must refuse")
        try:
            derive_checkpoint(root, requested="M4", purpose="restage")
        except MilestoneTransactionError as exc:
            assert exc.code == "AMC-ORDER", exc.code
        else:
            raise AssertionError("unknown purpose must refuse")
        assert hashlib.sha256(phase_path.read_bytes()).hexdigest() == pre_hash

        with tempfile.TemporaryDirectory(prefix="apg-derive-m5-door-") as closed_temp:
            closed = Path(closed_temp)
            closed_reviews = closed / "reviews"
            closed_reviews.mkdir()
            closed_framework = {
                "mode": "native",
                "milestones": {
                    "M1": {"status": "accepted"},
                    "M2": {"status": "accepted"},
                    "M3": {"status": "accepted"},
                    "M4": {"status": "accepted"},
                    "M5": {"status": "accepted"},
                },
            }
            closed_phase = closed_reviews / "phase_state.json"
            closed_phase.write_text(
                json.dumps({"milestone_framework": closed_framework}, indent=2) + "\n",
                encoding="utf-8",
            )
            closed_hash = hashlib.sha256(closed_phase.read_bytes()).hexdigest()
            complete = derive_checkpoint(closed)
            assert complete == {
                "status": "COMPLETE",
                "milestone": None,
                "action": None,
                "authority_mode": complete.get("authority_mode"),
            }, complete
            assert complete["authority_mode"] in {"direct_local", "shipment_only"}
            try:
                derive_checkpoint(closed, requested="M4", purpose="evaluate")
            except MilestoneTransactionError as exc:
                assert exc.code == "AMC-ORDER", exc.code
            else:
                raise AssertionError("accepted M5 evaluate must refuse")
            try:
                derive_checkpoint(closed, requested="M4")
            except MilestoneTransactionError as exc:
                assert exc.code == "AMC-ORDER", exc.code
            else:
                raise AssertionError("accepted M5 named dispatch must refuse")
            assert hashlib.sha256(closed_phase.read_bytes()).hexdigest() == closed_hash

        with tempfile.TemporaryDirectory(prefix="apg-derive-circulate-") as circ_temp:
            circ = Path(circ_temp)
            circ_reviews = circ / "reviews"
            circ_reviews.mkdir()
            circulate_framework = {
                "mode": "native",
                "milestones": {
                    "M1": {"status": "reopened"},
                    "M2": {"status": "accepted"},
                    "M3": {"status": "accepted"},
                    "M4": {"status": "in_progress"},
                    "M5": {"status": "not_started"},
                },
                "events": [{"event_type": "milestone_accepted", "milestone": "M4"}],
            }
            circ_phase = circ_reviews / "phase_state.json"
            circ_phase.write_text(
                json.dumps({"milestone_framework": circulate_framework}, indent=2) + "\n",
                encoding="utf-8",
            )
            circ_hash = hashlib.sha256(circ_phase.read_bytes()).hexdigest()
            circ_default = derive_checkpoint(circ)
            assert circ_default["status"] == "READY"
            assert circ_default["milestone"] == "M1", circ_default
            named_m4 = derive_checkpoint(circ, requested="M4")
            assert named_m4["status"] == "READY"
            assert named_m4["milestone"] == "M4"
            assert named_m4["action"] == "draft", named_m4
            assert named_m4["authority_mode"] in {"direct_local", "shipment_only"}
            circ_eval = derive_checkpoint(circ, requested="M4", purpose="evaluate")
            assert circ_eval["status"] == "READY"
            assert circ_eval["milestone"] == "M4"
            assert circ_eval["action"] == "evaluate"
            assert hashlib.sha256(circ_phase.read_bytes()).hexdigest() == circ_hash

        with tempfile.TemporaryDirectory(prefix="apg-derive-malformed-") as bad_temp:
            bad = Path(bad_temp)
            bad_reviews = bad / "reviews"
            bad_reviews.mkdir()
            (bad_reviews / "phase_state.json").write_text(
                json.dumps(
                    {"milestone_framework": {"mode": "native", "milestones": {}}},
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            try:
                derive_checkpoint(bad)
            except MilestoneTransactionError as exc:
                assert exc.code == "AMC-PHASE-STATE", exc.code
            else:
                raise AssertionError("empty milestones must fail AMC-PHASE-STATE")
            try:
                derive_checkpoint(bad, requested="M4", purpose="evaluate")
            except MilestoneTransactionError as exc:
                assert exc.code == "AMC-PHASE-STATE", exc.code
            else:
                raise AssertionError("named evaluate must preserve AMC-PHASE-STATE")

    # C7 coupling: once C2 has rebound the active Generator target, an unbound
    # receipt cannot survive, while a receipt naming the exact marker-committed
    # transition remains replayable through the public gate.
    with tempfile.TemporaryDirectory(prefix="assignment-gate-control-", dir=package_scratch(ROOT)) as temp:
        import control_plane_transition as control
        from control_plane_transition_smoketest import _project_fixture

        project = Path(temp)
        reviews = project / "reviews"
        reviews.mkdir()
        write_valid_contract(project)
        phase_state = {
            "milestone_framework": {
                "mode": "native",
                "milestones": {
                    key: {"status": "not_started"}
                    for key in ("M1", "M2", "M3", "M4", "M5")
                },
            }
        }
        (reviews / "phase_state.json").write_text(
            json.dumps(phase_state, indent=2) + "\n", encoding="utf-8"
        )
        plan, _ = _project_fixture(project)
        active = next(row for row in plan["members"] if row["member"] == "active_target")
        old_target = project / active["path"]
        new_target = project / "milestones" / "M1_project_memo.md"
        new_target.parent.mkdir(parents=True, exist_ok=True)
        new_target.write_bytes(old_target.read_bytes())
        active["path"] = "milestones/M1_project_memo.md"
        transition_id = "assignment-gate-rebind"
        control.prepare(project, plan, transition_id)
        control.publish(project, transition_id)
        ready = Path(
            "reviews/.harness/assignment/ready/"
            "gate_receipt_M1_20260726T000000Z.json"
        )
        unbound = run_gate(project, "draft", "M1", emit_receipt=ready)
        assert unbound.returncode == 4 and "CPT-LIVE-RECEIPT" in unbound.stdout, unbound.stdout + unbound.stderr
        from full_run_contract_check import authorize
        assert any(
            row.get("code") == "FRC-CONTRACT-MISSING"
            for row in authorize(project)
        ), "full-run authorize must not recover authority from an unbound rebind"
        bound = run_gate(
            project, "draft", "M1", emit_receipt=ready,
            control_transition_id=transition_id,
        )
        assert bound.returncode == 0, bound.stdout + bound.stderr
        receipt_value = json.loads((project / ready).read_text(encoding="utf-8"))
        assert receipt_value["control_transition"]["transition_id"] == transition_id
        verified = run_gate(project, verify_receipt=ready)
        assert verified.returncode == 0, verified.stdout + verified.stderr
        assert authorize(project) == []
        marker = project / receipt_value["control_transition"]["commit_marker"]["path"]
        marker_bytes = marker.read_bytes()
        marker.write_bytes(marker_bytes + b" ")
        stale_authorize = authorize(project)
        assert any(
            row.get("code") == "FRC-CONTRACT-MISSING"
            and "CPT-PUBLICATION-INCOMPLETE" in row.get("message", "")
            for row in stale_authorize
        ), stale_authorize
        marker.write_bytes(marker_bytes)
        assert authorize(project) == []

    print("OK assignment_process_gate_smoketest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
