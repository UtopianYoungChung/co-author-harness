"""Write-root routing of run_all, d_style_profile_check, the M5 canonical map and the signoff lookup."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS / "audit"))

from assignment_milestone_transaction import (  # noqa: E402
    MilestoneTransactionError,
    _m5_terminal_canonical_paths,
)
from audit import run_all  # noqa: E402
from d_style_profile_check import default_output_path  # noqa: E402
from milestone_framework_validate import PH3_SIGNOFF_REL, _signoff_write_root  # noqa: E402
from output_lane import OutputLaneError, set_active_shipment  # noqa: E402

SID = "shp-20260929T000000Z-abcdef01"
ROUND = "round_2026-09-29_001"


@pytest.fixture()
def governed(tmp_path, monkeypatch):
    manifest = tmp_path / "governance" / "output-routing" / "output_routing.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("routes: []\n", encoding="utf-8")
    work = tmp_path / "research" / "60_Workbench" / "WID-1"
    work.mkdir(parents=True)
    monkeypatch.setenv("COAUTHOR_EXTRA_GOVERNED_ROOTS", str(tmp_path))
    monkeypatch.delenv("COAUTHOR_SHIPMENT_ID", raising=False)
    return work


@pytest.fixture()
def plain(tmp_path, monkeypatch):
    monkeypatch.delenv("COAUTHOR_EXTRA_GOVERNED_ROOTS", raising=False)
    monkeypatch.delenv("COAUTHOR_SHIPMENT_ID", raising=False)
    proj = tmp_path / "proj"
    proj.mkdir()
    return proj


# (a) governed + id -> lane output; non-governed unchanged
def test_run_all_defaults_governed_lane(governed):
    lane = governed / "reviews" / "harness" / "shipments" / SID
    got = run_all.default_output_paths(governed, shipment_id=SID, date="2026-09-29", cycle_id="c1")
    assert got == {
        "findings": lane / "reviews" / "findings.json",
        "d_style": lane / "reviews" / "d_style_profile_2026-09-29.json",
        "accessibility": lane / "reviews" / "reader_accessibility_candidates_c1.json",
        "product_assurance": lane / "reviews" / "product_assurance_c1.json",
    }


def test_run_all_defaults_non_governed_unchanged(plain):
    got = run_all.default_output_paths(plain, date="2026-09-29", cycle_id="c1")
    assert got["findings"] == Path("reviews/findings.json")
    assert got["d_style"] == plain / "reviews" / "d_style_profile_2026-09-29.json"
    assert got["accessibility"] == plain / "reviews" / "reader_accessibility_candidates_c1.json"
    assert got["product_assurance"] == plain / "reviews" / "product_assurance_c1.json"


def test_d_style_default_output_path(governed, plain):
    lane = governed / "reviews" / "harness" / "shipments" / SID
    assert default_output_path(governed, "2026-09-29", SID) == lane / "reviews" / "d_style_profile_2026-09-29.json"
    assert default_output_path(plain, "2026-09-29") == plain / "reviews" / "d_style_profile_2026-09-29.json"


# (b) governed + no id -> refusal
def test_defaults_governed_without_id_refuse(governed):
    with pytest.raises(OutputLaneError):
        run_all.default_output_paths(governed)
    with pytest.raises(OutputLaneError):
        default_output_path(governed, "2026-09-29")


def test_run_all_main_governed_without_id_blocks(governed, tmp_path, capsys):
    target = tmp_path / "m.md"
    target.write_text("A sentence.\n", encoding="utf-8")
    rc = run_all.main([str(target), "--project-root", str(governed)])
    assert rc == 4
    assert "shipment id" in capsys.readouterr().err
    assert not (governed / "reviews").exists()


def test_run_all_main_governed_explicit_outputs_need_no_id(governed, tmp_path):
    target = tmp_path / "m.md"
    target.write_text("A sentence.\n", encoding="utf-8")
    # nothing defaulted is written: read-only form needs no lane
    rc = run_all.main([str(target), "--project-root", str(governed), "--stdout",
                       "--skip-d-style-profile", "--skip-accessibility"])
    assert rc == 0


def test_d_style_main_governed_without_id_blocks(governed, monkeypatch, capsys):
    from d_style_profile_check import main

    monkeypatch.setattr(sys, "argv", ["d_style_profile_check.py", "--project-root", str(governed)])
    assert main() == 4
    assert "shipment id" in capsys.readouterr().err


# (c) M5 canonical map
def test_m5_canonical_non_governed_unchanged(plain):
    assert _m5_terminal_canonical_paths(plain, ROUND) == {
        "g4_signoff": "reviews/G4_signoff.md",
        "ship_signoff": "reviews/ph4_ship_signoff.md",
        "final_round_report": f"reviews/final_round_report_{ROUND}.md",
        "reflector_full": "reviews/reflection_report.md",
        "events_log": "reviews/.harness/events.jsonl",
        "findings": "reviews/findings.json",
        "convergence_log": "reviews/convergence_log.md",
    }


def test_m5_canonical_governed_lane(governed, monkeypatch):
    monkeypatch.setenv("COAUTHOR_SHIPMENT_ID", SID)
    lane = f"reviews/harness/shipments/{SID}"
    got = _m5_terminal_canonical_paths(governed, ROUND)
    assert got["events_log"] == "reviews/.harness/events.jsonl"
    assert got["g4_signoff"] == f"{lane}/reviews/G4_signoff.md"
    assert got["final_round_report"] == f"{lane}/reviews/final_round_report_{ROUND}.md"
    assert got["convergence_log"] == f"{lane}/reviews/convergence_log.md"
    assert all(v.startswith(lane + "/") for r, v in got.items() if r != "events_log")


def test_m5_canonical_governed_without_id_refuses(governed):
    with pytest.raises(MilestoneTransactionError) as info:
        _m5_terminal_canonical_paths(governed, ROUND)
    assert info.value.code == "AMC-TERMINAL"


# Ph3 signoff lookup root (milestone_framework_validate)
def test_signoff_write_root(governed, plain, monkeypatch):
    assert _signoff_write_root(plain) == (plain, None)
    root, err = _signoff_write_root(governed)
    assert root is None and "shipment id" in err
    monkeypatch.setenv("COAUTHOR_SHIPMENT_ID", SID)
    root, err = _signoff_write_root(governed)
    assert err is None
    assert root / PH3_SIGNOFF_REL == governed / "reviews" / "harness" / "shipments" / SID / PH3_SIGNOFF_REL


# F3: the active-shipment pointer resolves without COAUTHOR_SHIPMENT_ID
def test_pointer_resolves_for_milestone_helpers_without_env(governed):
    set_active_shipment(governed, SID)
    lane = f"reviews/harness/shipments/{SID}"
    got = _m5_terminal_canonical_paths(governed, ROUND)
    assert got["g4_signoff"] == f"{lane}/reviews/G4_signoff.md"
    assert got["events_log"] == "reviews/.harness/events.jsonl"
    root, err = _signoff_write_root(governed)
    assert err is None
    assert root == governed / "reviews" / "harness" / "shipments" / SID


# R1: the terminal check reads seat-produced evidence from the lane
def test_frc_terminal_reads_lane_via_pointer_and_fails_closed_without(governed):
    import full_run_contract_check as frc

    with pytest.raises(OutputLaneError):
        frc._findings_json_findings(governed, {})
    set_active_shipment(governed, SID)
    lane = governed / "reviews" / "harness" / "shipments" / SID
    # findings.json at the package root is not evidence; only the lane copy is read
    (governed / "reviews").mkdir(exist_ok=True)
    (governed / "reviews" / "findings.json").write_text("{}", encoding="utf-8")
    absent = frc._findings_json_findings(governed, {})
    assert absent and absent[0]["code"] == frc.FRC_LOCAL["findings_json"]
    (lane / "reviews").mkdir(parents=True, exist_ok=True)
    (lane / "reviews" / "findings.json").write_text("not json", encoding="utf-8")
    unreadable = frc._findings_json_findings(governed, {})
    assert unreadable and unreadable[0]["code"] == frc.FRC_LOCAL["artefact_unreadable"]


def test_frc_signoffs_are_read_from_the_lane(governed):
    import full_run_contract_check as frc

    set_active_shipment(governed, SID)
    lane = governed / "reviews" / "harness" / "shipments" / SID
    (governed / "reviews").mkdir(exist_ok=True)
    (governed / "reviews" / "G4_signoff.md").write_text("round_id: x\n", encoding="utf-8")
    missing = frc._structured_terminal_signoff_findings(governed, {})
    assert any("G4_signoff.md" in f["path"] and f["code"] == frc.FRC_LOCAL["artefact_unreadable"]
               for f in missing)
    (lane / "reviews").mkdir(parents=True, exist_ok=True)
    (lane / "reviews" / "G4_signoff.md").write_text("round_id: x\n", encoding="utf-8")
    present = frc._structured_terminal_signoff_findings(governed, {})
    assert not any("G4_signoff.md" in f["path"] and f["code"] == frc.FRC_LOCAL["artefact_unreadable"]
                   for f in present)


def test_ph4_terminal_close_gate_reads_signoffs_from_the_lane(governed):
    from milestone_framework_validate import _gate_boundary_findings

    document = {"milestone_framework": {"milestones": {}}}

    def signoff_findings():
        return [f for f in _gate_boundary_findings(governed, document, "ph4_terminal_close")
                if f.code == "MF-GATE-M5" and f.path.startswith("reviews/")]

    # governed package, no shipment id: fail closed with the "name the id" message
    no_id = signoff_findings()
    assert len(no_id) == 2 and all("shipment id" in f.message for f in no_id)
    set_active_shipment(governed, SID)
    lane = governed / "reviews" / "harness" / "shipments" / SID
    # signoffs only at the package root are not evidence
    (governed / "reviews").mkdir(exist_ok=True)
    for name in ("G4_signoff.md", "ph4_ship_signoff.md"):
        (governed / "reviews" / name).write_text("status: PASS\n", encoding="utf-8")
    missing = signoff_findings()
    assert {f.path for f in missing} == {"reviews/G4_signoff.md", "reviews/ph4_ship_signoff.md"}
    assert all("shipment id" not in f.message for f in missing)
    # the lane copies are the evidence
    (lane / "reviews").mkdir(parents=True, exist_ok=True)
    for name in ("G4_signoff.md", "ph4_ship_signoff.md"):
        (lane / "reviews" / name).write_text("status: PASS\n", encoding="utf-8")
    assert signoff_findings() == []


def test_ph4_terminal_close_gate_non_governed_reads_package_root(plain):
    from milestone_framework_validate import _gate_boundary_findings

    document = {"milestone_framework": {"milestones": {}}}

    def signoff_findings():
        return [f for f in _gate_boundary_findings(plain, document, "ph4_terminal_close")
                if f.code == "MF-GATE-M5" and f.path.startswith("reviews/")]

    assert len(signoff_findings()) == 2
    (plain / "reviews").mkdir()
    for name in ("G4_signoff.md", "ph4_ship_signoff.md"):
        (plain / "reviews" / name).write_text("status: PASS\n", encoding="utf-8")
    assert signoff_findings() == []


def test_artefact_frontmatter_project_root_for_lane_artefacts(tmp_path):
    from artefact_frontmatter_validate import _artefact_project_root

    pkg = tmp_path / "pkg"
    assert _artefact_project_root(pkg / "reviews" / "x_findings.md") == pkg
    assert _artefact_project_root(pkg / "x_findings.md") == pkg
    for harness in ("harness", ".harness"):
        lane_artefact = pkg / "reviews" / harness / "shipments" / SID / "reviews" / "x_findings.md"
        assert _artefact_project_root(lane_artefact) == pkg


def test_pre_phase_advance_shipment_id_argument_routes_the_milestone_gate(governed, monkeypatch, capsys):
    import json

    import pre_phase_advance_check as ppac

    (governed / "reviews").mkdir(exist_ok=True)
    (governed / "reviews" / "phase_state.json").write_text(
        json.dumps({"milestone_framework": {"milestones": {}}}), encoding="utf-8")
    other = "shp-20260929T000000Z-00000000"
    set_active_shipment(governed, other)  # pointer names Y ...
    lane_x = governed / "reviews" / "harness" / "shipments" / SID
    (lane_x / "reviews").mkdir(parents=True)  # ... argument names X, the only lane with signoffs
    for name in ("G4_signoff.md", "ph4_ship_signoff.md"):
        (lane_x / "reviews" / name).write_text("status: PASS\n", encoding="utf-8")
    monkeypatch.setenv("COAUTHOR_SHIPMENT_ID", "placeholder")  # restored on teardown

    def signoff_errors(*extra):
        capsys.readouterr()
        ppac.main(["--project-root", str(governed), "--section", "S", "--target-tier", "Ph4",
                   "--terminal-close", "--json", *extra])
        errors = json.loads(capsys.readouterr().out).get("errors", [])
        return [e for e in errors if e.get("path", "").startswith("reviews/") and "signoff" in e["path"]]

    assert signoff_errors("--shipment-id", SID) == []
    monkeypatch.delenv("COAUTHOR_SHIPMENT_ID")
    assert len(signoff_errors()) == 2  # the pointer's lane (Y) has none


# R12: a real routed mutator lands in the lane and the destination guard agrees
def _run_coupling_health(work, tmp_path, *extra):
    env = dict(os.environ, COAUTHOR_EXTRA_GOVERNED_ROOTS=str(tmp_path))
    env.pop("COAUTHOR_SHIPMENT_ID", None)
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "coupling_health_report.py"), "--project-root", str(work), *extra],
        capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
    )


def test_routed_mutator_writes_lane_and_guard_refuses_package_root(governed, tmp_path):
    lane = governed / "reviews" / "harness" / "shipments" / SID
    ok = _run_coupling_health(governed, tmp_path, "--shipment-id", SID)
    assert ok.returncode == 0, ok.stdout + ok.stderr
    assert (lane / "reviews" / "coupling_health.json").is_file()
    assert (lane / "reviews" / "coupling_health.md").is_file()
    assert not (governed / "reviews" / "coupling_health.json").exists()
    bad = _run_coupling_health(governed, tmp_path, "--shipment-id", SID, "--output-json",
                               str(governed / "reviews" / "coupling_health.json"))
    assert bad.returncode == 4 and "[BLOCKER]" in bad.stdout
    assert not (governed / "reviews" / "coupling_health.json").exists()


def test_routed_mutator_resolves_lane_from_pointer(governed, tmp_path):
    none = _run_coupling_health(governed, tmp_path)
    assert none.returncode == 4 and "shipment id" in none.stdout
    set_active_shipment(governed, SID)
    ok = _run_coupling_health(governed, tmp_path)
    assert ok.returncode == 0, ok.stdout + ok.stderr
    assert (governed / "reviews" / "harness" / "shipments" / SID / "reviews" / "coupling_health.json").is_file()


# R11: check8 prefilter --stdout-only in a governed package needs an explicit P-stage
def test_check8_stdout_only_governed_needs_p_stage(governed, tmp_path):
    env = dict(os.environ, COAUTHOR_EXTRA_GOVERNED_ROOTS=str(tmp_path))
    env.pop("COAUTHOR_SHIPMENT_ID", None)
    ms = tmp_path / "m.md"
    ms.write_text("# Title\n\nA sentence.\n", encoding="utf-8")
    base = [sys.executable, str(SCRIPTS / "check8_g_prefilter.py"), "--project-root", str(governed),
            "--manuscript", str(ms), "--cycle-id", "c1", "--stdout-only"]
    refused = subprocess.run(base, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    assert refused.returncode == 4 and "[BLOCKER]" in refused.stdout
    allowed = subprocess.run(base + ["--p-stage", "P1"], capture_output=True, text=True,
                             encoding="utf-8", errors="replace", env=env)
    assert allowed.returncode == 0, allowed.stdout + allowed.stderr


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
