#!/usr/bin/env python3
"""Focused regressions for milestone-aware phase advancement."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from milestone_framework_smoketest import (
    _materialize_native_project,
    _override,
    _phase_document,
    _reset_milestone,
    _write_real_case,
)
from pre_phase_advance_check import check_milestone_gate


def _project(root: Path) -> dict:
    ledger = _materialize_native_project(root)
    document = _phase_document(ledger, "Ph4")
    (root / "reviews" / "phase_state.json").write_text(json.dumps(document), encoding="utf-8")
    (root / "reviews" / "ph4_ship_signoff.md").write_text("G.4: signed\n", encoding="utf-8")
    (root / "reviews" / "G4_signoff.md").write_text("G.4 PASS — signed\n", encoding="utf-8")
    return document


def _codes(findings) -> set[str]:
    return {finding.code for finding in findings}


def main() -> int:
    checks = 0
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        base = _project(root)

        result = check_milestone_gate(root, copy.deepcopy(base), "Ph2")
        assert not result.findings and result.outcomes == {"M1": "READY", "M2": "READY", "M3": "READY"}
        checks += 1

        legacy_root = root / "legacy"; legacy_root.mkdir()
        _write_real_case("valid_approved_legacy_migration", legacy_root)
        legacy_doc = json.loads((legacy_root / "reviews" / "phase_state.json").read_text(encoding="utf-8"))
        legacy_result = check_milestone_gate(legacy_root, legacy_doc, "Ph2")
        assert not legacy_result.findings and set(legacy_result.outcomes.values()) == {"LEGACY_READY"}
        checks += 1

        na_root = root / "na"; na_root.mkdir()
        na_ledger = _materialize_native_project(na_root)
        m3 = na_ledger["milestones"]["M3"]
        evidence = na_root / "reviews" / "not_applicable_approval.md"
        evidence.write_text("advisor-approved M3 substitute\n", encoding="utf-8")
        override = _override(["M3"], ["M3_to_M4"])
        override["substitute_evidence_sha256"] = hashlib.sha256(evidence.read_bytes()).hexdigest()
        m3.update({
            "status": "not_applicable", "applicability": "not_applicable", "artifacts": [],
            "feedback_records": [], "approval": {"status": "not_applicable", "authority": None, "evidence_path": None, "approved_at": None},
            "handoff": {"status": "not_applicable", "packet_path": None, "packet_sha256": None},
            "dependency_state": "not_applicable", "authorized_override": override,
        })
        _reset_milestone(na_ledger["milestones"]["M4"])
        _reset_milestone(na_ledger["milestones"]["M5"])
        na_doc = _phase_document(na_ledger, "Ph2")
        na_result = check_milestone_gate(na_root, na_doc, "Ph2")
        assert not na_result.findings and na_result.outcomes["M3"] == "NOT_APPLICABLE"
        checks += 1

        legacy = copy.deepcopy(base)
        legacy["milestone_framework"]["mode"] = "legacy"
        # A legacy boundary is deliberately omitted here: the validator must distinguish it as bad.
        assert "MF-STRUCTURE" in _codes(check_milestone_gate(root, legacy, "Ph2").findings)
        checks += 1

        na = copy.deepcopy(base)
        m3 = na["milestone_framework"]["milestones"]["M3"]
        m3["applicability"] = m3["status"] = "not_applicable"
        m3["approval"] = {"status": "not_applicable", "authority": None, "evidence_path": None, "approved_at": None}
        m3["handoff"] = {"status": "not_applicable", "packet_path": None, "packet_sha256": None}
        m3["dependency_state"] = "not_applicable"
        # Missing authorization is never silently treated as N/A.
        assert "MF-OVERRIDE" in _codes(check_milestone_gate(root, na, "Ph2").findings)
        checks += 1

        absent = copy.deepcopy(base); del absent["milestone_framework"]
        assert "MF-STRUCTURE" in _codes(check_milestone_gate(root, absent, "Ph2").findings)
        checks += 1

        broken = copy.deepcopy(base)
        broken["milestone_framework"]["milestones"]["M2"]["handoff"]["status"] = "ready"
        assert "MF-GATE-CHAIN" in _codes(check_milestone_gate(root, broken, "Ph2").findings)
        checks += 1

        m4_bad = copy.deepcopy(base)
        m4_bad["milestone_framework"]["milestones"]["M4"]["approval"]["status"] = "pending"
        assert "MF-GATE-M4" in _codes(check_milestone_gate(root, m4_bad, "Ph4").findings)
        checks += 1

        m4_ready = copy.deepcopy(base)
        m4_ready["milestone_framework"]["milestones"]["M4"]["handoff"]["status"] = "ready"
        _reset_milestone(m4_ready["milestone_framework"]["milestones"]["M5"])
        assert not check_milestone_gate(root, m4_ready, "Ph4").findings
        checks += 1

        terminal = copy.deepcopy(base)
        terminal["terminal_phase_reached"] = False
        assert not check_milestone_gate(root, terminal, "Ph4", terminal_close=True).findings
        checks += 1
        terminal["milestone_framework"]["milestones"]["M5"]["dependency_state"] = "stale"
        assert "MF-GATE-M5" in _codes(check_milestone_gate(root, terminal, "Ph4", terminal_close=True).findings)
        checks += 1

        drift = copy.deepcopy(base)
        drift["milestone_framework"]["milestones"]["M5"]["artifacts"][0]["sha256"] = "f" * 64
        assert "MF-BINDING" in _codes(check_milestone_gate(root, drift, "Ph4", terminal_close=True).findings)
        checks += 1

        missing_g4 = copy.deepcopy(base)
        (root / "reviews" / "G4_signoff.md").unlink()
        assert "MF-GATE-M5" in _codes(check_milestone_gate(root, missing_g4, "Ph4", terminal_close=True).findings)
        (root / "reviews" / "G4_signoff.md").write_text("G.4 PASS — signed\n", encoding="utf-8")
        checks += 1

        malformed = copy.deepcopy(base); malformed["sections"] = []
        assert "MF-STRUCTURE" in _codes(check_milestone_gate(root, malformed, "Ph4").findings)
        checks += 1

        canonical = root / "reviews" / "ph3_convergence_signoff.md"
        assert canonical.exists()
        canonical.unlink()
        (root / "reviews" / "t3_convergence_signoff.md").write_text("is_terminal: true\n", encoding="utf-8")
        assert "MF-PHASE" in _codes(check_milestone_gate(root, base, "Ph4").findings)
        checks += 1

        command = [sys.executable, str(Path(__file__).with_name("pre_phase_advance_check.py")), "--project-root", str(root), "--section", '["1. Test"]', "--target-phase", "Ph4", "--json"]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        assert completed.returncode == 1 and "MF-PHASE" in completed.stdout and "ph3_convergence_signoff.md" in completed.stdout
        checks += 1
        command.insert(-1, "--terminal-close")
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        assert completed.returncode == 0, completed.stderr + completed.stdout
        checks += 1
        illegal = command.copy(); illegal[illegal.index("Ph4")] = "Ph2"
        completed = subprocess.run(illegal, capture_output=True, text=True, check=False)
        assert completed.returncode != 0 and "terminal-close" in (completed.stderr + completed.stdout)
        checks += 1

    print(f"PASS: {checks} milestone-aware phase-gate regressions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
