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
        assert receipt_record["schema_version"] == "2.1.0"
        assert "status" not in receipt_record
        assert "consumed_at" not in receipt_record
        assert receipt_record["stage"] == "draft"
        assert receipt_record["target_milestone"] == "M1"
        assert receipt_record["authorized_role"] == "generator"
        assert receipt_record["authorized_writes"] == [
            {"path": "research_notes/project_memo.md", "mode": "replace"},
            {"path": "manuscript/revision_log.md", "mode": "append"},
        ]
        assert receipt_record["project_root_resolved"] == str(root.resolve())
        assert receipt_record["primary_deliverable_path"] == "research_notes/project_memo.md"
        assert receipt_record["primary_deliverable_path"] in receipt_record["authorized_paths"]
        assert receipt_record["assignment_contract_sha256"] == sha256(
            reviews / "assignment_contract.json"
        )
        assert receipt_record["phase_state_sha256"] == sha256(
            reviews / "phase_state.json"
        )
        assert receipt_record["profile_sha256"] == sha256(PROFILE)
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
        assert (
            m2_exemplar.returncode == 4
            and "APG-EXEMPLAR-SCOPE" in m2_exemplar.stdout
        ), m2_exemplar.stdout + m2_exemplar.stderr
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

    print("OK assignment_process_gate_smoketest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
