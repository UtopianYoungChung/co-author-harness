"""Unit tests for output_lane.py (FINDING-20260929-001 write-root rule)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))

import output_lane  # noqa: E402
from output_lane import (  # noqa: E402
    ACTIVE_SHIPMENT_REL,
    OutputLaneError,
    is_never_redirected,
    read_active_shipment,
    resolve_path,
    resolve_write_root,
    set_active_shipment,
    validate_shipment_id,
)


@pytest.fixture()
def governed(tmp_path, monkeypatch):
    """A temp governed root (routing manifest) with one Workbench work-id."""
    manifest = tmp_path / "governance" / "output-routing" / "output_routing.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("routes: []\n", encoding="utf-8")
    work = tmp_path / "research" / "60_Workbench" / "WID-1"
    work.mkdir(parents=True)
    monkeypatch.setenv("COAUTHOR_EXTRA_GOVERNED_ROOTS", str(tmp_path))
    monkeypatch.delenv("COAUTHOR_SHIPMENT_ID", raising=False)
    return tmp_path, work


def test_governed_with_shipment_id(governed):
    _, work = governed
    got = resolve_write_root(work, "shp-20260929T000000Z-abcdef01")
    assert got == work / "reviews" / "harness" / "shipments" / "shp-20260929T000000Z-abcdef01"


def test_governed_shipment_id_from_env(governed, monkeypatch):
    _, work = governed
    monkeypatch.setenv("COAUTHOR_SHIPMENT_ID", "S1")
    assert resolve_write_root(work) == work / "reviews" / "harness" / "shipments" / "S1"


def test_argument_beats_env(governed, monkeypatch):
    _, work = governed
    monkeypatch.setenv("COAUTHOR_SHIPMENT_ID", "ENV")
    assert resolve_write_root(work, "ARG").name == "ARG"


def test_governed_missing_id_fails_closed(governed):
    _, work = governed
    with pytest.raises(OutputLaneError, match="name the active shipment id"):
        resolve_write_root(work)


@pytest.mark.parametrize(
    "bad",
    [
        "../x", "a/b", "a\\b", "..", ".", "a..b", ".hidden", "", "  ", "x y",
        "trailing.", "CON", "con", "Nul", "aux.txt", "COM1", "lpt9.log", "PRN.",
        "COM0", "lpt0.txt", "COM"+chr(0xb9), "LPT"+chr(0xb2),
    ],
)
def test_governed_bad_id(governed, bad):
    _, work = governed
    with pytest.raises(OutputLaneError):
        resolve_write_root(work, bad)


def test_lane_resolving_outside_the_package_is_refused(governed, tmp_path):
    _, work = governed
    outside = tmp_path / "outside"
    outside.mkdir()
    (work / "reviews" / "harness").mkdir(parents=True)
    link = work / "reviews" / "harness" / "shipments"
    try:
        os.symlink(outside, link, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not permitted on this platform")
    with pytest.raises(OutputLaneError, match="outside the package"):
        resolve_write_root(work, "S1")
    link.unlink()
    assert resolve_write_root(work, "S1") == work / "reviews" / "harness" / "shipments" / "S1"


def test_governed_package_that_does_not_exist_is_named_not_misreported(governed):
    tmp_path, _ = governed
    missing = tmp_path / "research" / "60_Workbench" / "WID-MISSING"
    assert not missing.exists()
    with pytest.raises(OutputLaneError, match="governed package does not exist") as exc:
        resolve_write_root(missing, "S1")
    assert "outside the package" not in str(exc.value)
    assert str(missing) in str(exc.value)


def test_non_governed_project_unchanged(tmp_path, monkeypatch):
    monkeypatch.delenv("COAUTHOR_EXTRA_GOVERNED_ROOTS", raising=False)
    monkeypatch.delenv("COAUTHOR_SHIPMENT_ID", raising=False)
    proj = tmp_path / "proj"
    proj.mkdir()
    assert resolve_write_root(proj) == proj
    assert resolve_write_root(proj, "ignored") == proj


def test_governed_root_but_not_work_id_root_unchanged(governed):
    root, work = governed
    assert resolve_write_root(root) == root
    assert resolve_write_root(work / "manuscript") == work / "manuscript"
    assert resolve_write_root(root / "research" / "60_Workbench") == (
        root / "research" / "60_Workbench"
    )


@pytest.mark.parametrize(
    "rel",
    [
        "reviews/phase_state.json",
        "reviews/.harness",
        "reviews/.harness/assignment/ready/x.json",
        "reviews/.harness/policies/reader_accessibility.resolved.json",
        "reviews/repin_rebind_request.json",
        "reviews/repin_rebind_request.1700000000.applied.json",
        "reviews/repin_rebind_request.1700000000.stale.json",
    ],
)
def test_never_redirected(rel):
    assert is_never_redirected(rel)
    assert is_never_redirected(rel.replace("/", "\\"))


@pytest.mark.parametrize(
    "rel",
    [
        "reviews/revision_plan.md",
        "reviews/convergence_log.md",
        "reviews/harness/shipments/x/report.md",
        "reviews/repin_rebind_request.notes.md",
        "research_notes/lessons_learned.md",
        "manuscript/revision_log.md",
        "phase_state.json",
    ],
)
def test_redirected(rel):
    assert not is_never_redirected(rel)


def test_resolve_path(governed):
    _, work = governed
    lane = work / "reviews" / "harness" / "shipments" / "S1"
    assert resolve_path(work, "reviews/revision_plan.md", "S1") == lane / "reviews" / "revision_plan.md"
    assert resolve_path(work, "reviews/phase_state.json") == work / "reviews" / "phase_state.json"


def test_cli(governed):
    _, work = governed
    env_run = subprocess.run(
        [sys.executable, str(SCRIPTS / "output_lane.py"), str(work), "--shipment-id", "S1"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert env_run.returncode == 0
    assert Path(env_run.stdout.strip()) == work / "reviews" / "harness" / "shipments" / "S1"
    missing = subprocess.run(
        [sys.executable, str(SCRIPTS / "output_lane.py"), str(work)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env={k: v for k, v in __import__("os").environ.items() if k != "COAUTHOR_SHIPMENT_ID"},
    )
    assert missing.returncode == 2
    assert "shipment id" in missing.stderr


def test_lane_is_writable_by_destination_capability(governed):
    import destination_capability as dc

    _, work = governed
    lane = resolve_write_root(work, "S1")
    assert dc.classify(lane / "reviews" / "revision_plan.md") == "shipment"
    assert dc.classify(work / "reviews" / "revision_plan.md") == "protected"


@pytest.mark.parametrize("ok", ["S1", "shp-20260929T000000Z-abcdef01", "console", "com10", "a.b", "CONX"])
def test_valid_ids_including_reserved_lookalikes(ok):
    assert validate_shipment_id(ok) == ok


# ---- active-shipment pointer (R2)
def _pointer(work):
    return work / Path(ACTIVE_SHIPMENT_REL)


def test_set_active_writes_pointer_and_lane(governed):
    _, work = governed
    pointer = set_active_shipment(work, "S1")
    assert pointer == _pointer(work)
    data = json.loads(pointer.read_text(encoding="utf-8"))
    assert data["schema"] == "active-shipment.v1" and data["shipment_id"] == "S1"
    assert data["set_at"].endswith("Z")
    assert (work / "reviews" / "harness" / "shipments" / "S1").is_dir()
    assert not list(pointer.parent.glob("*.tmp"))


def test_pointer_resolution_order(governed, monkeypatch):
    _, work = governed
    set_active_shipment(work, "PTR")
    lane = work / "reviews" / "harness" / "shipments"
    assert resolve_write_root(work) == lane / "PTR"          # pointer, no arg, no env
    monkeypatch.setenv("COAUTHOR_SHIPMENT_ID", "ENV")
    assert resolve_write_root(work) == lane / "ENV"          # env beats pointer
    assert resolve_write_root(work, "ARG") == lane / "ARG"   # argument beats both


@pytest.mark.parametrize("body", [
    "not json", "[]", "{}", '{"schema": "x", "shipment_id": "S1"}',
    '{"schema": "active-shipment.v1", "shipment_id": 5}',
    '{"schema": "active-shipment.v1", "shipment_id": "../x"}',
])
def test_malformed_pointer_is_an_error_not_ignored(governed, body):
    _, work = governed
    _pointer(work).parent.mkdir(parents=True)
    _pointer(work).write_text(body, encoding="utf-8")
    with pytest.raises(OutputLaneError):
        resolve_write_root(work)
    with pytest.raises(OutputLaneError):
        read_active_shipment(work)


def test_no_pointer_still_fails_closed(governed):
    _, work = governed
    assert read_active_shipment(work) is None
    with pytest.raises(OutputLaneError, match="set-active"):
        resolve_write_root(work)


def test_set_active_refuses_non_governed_and_bad_id(governed, tmp_path):
    _, work = governed
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(OutputLaneError, match="governed"):
        set_active_shipment(plain, "S1")
    assert not (plain / "reviews").exists()
    with pytest.raises(OutputLaneError):
        set_active_shipment(work, "../x")
    assert not _pointer(work).exists()


def test_set_active_replaces_pointer(governed):
    _, work = governed
    set_active_shipment(work, "A")
    set_active_shipment(work, "B")
    assert read_active_shipment(work) == "B"


def test_pointer_is_never_redirected_and_passes_the_guard(governed):
    import destination_capability as dc

    _, work = governed
    assert is_never_redirected(ACTIVE_SHIPMENT_REL)
    dc.assert_writable(_pointer(work), purpose="test")


def test_set_active_cli(governed):
    _, work = governed
    env = {k: v for k, v in os.environ.items() if k != "COAUTHOR_SHIPMENT_ID"}
    run = subprocess.run(
        [sys.executable, str(SCRIPTS / "output_lane.py"), "set-active",
         "--project-root", str(work), "--shipment-id", "S9"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
    )
    assert run.returncode == 0, run.stderr
    assert read_active_shipment(work) == "S9"
    root = subprocess.run(
        [sys.executable, str(SCRIPTS / "output_lane.py"), str(work)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
    )
    assert Path(root.stdout.strip()) == work / "reviews" / "harness" / "shipments" / "S9"
    bad = subprocess.run(
        [sys.executable, str(SCRIPTS / "output_lane.py"), "set-active",
         "--project-root", str(work.parent), "--shipment-id", "S9"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
    )
    assert bad.returncode == 2 and "governed" in bad.stderr


def test_validate_shipment_id_rejects_trailing_newline():
    with pytest.raises(OutputLaneError):
        validate_shipment_id("S1\n")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
