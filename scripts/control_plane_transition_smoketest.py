#!/usr/bin/env python3
"""C1 red boundary for the frozen atomic control-plane interface.

The production module intentionally does not exist at C1.  Until it does, each
red case reports ``INTERFACE_BLOCKED`` and its clean twin is deferred.  Once the
module exists, it must expose ``validate_transition(candidate)``.  A refusal
exception must carry ``code``; an accepted twin must return a mapping whose
``findings`` array is empty.

All fixtures are short, self-authored, in-memory analogues.  They contain no
live research path or byte.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = ROOT / "scripts" / "control_plane_transition.py"
API = "validate_transition"
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _base() -> dict[str, Any]:
    target_bytes = "synthetic M1 successor bytes\n"
    members = []
    for name in (
        "controlling_brief",
        "directives",
        "active_target",
        "round_program",
        "revision_plan",
        "assignment_source_binding",
        "reader_policy_binding",
        "affected_receipts_and_evaluations",
    ):
        before = f"{name}: B17\n"
        after = target_bytes if name == "active_target" else f"{name}: B18\n"
        members.append(
            {
                "member": name,
                "control_revision": "B18",
                "path": f"synthetic/{name}.json",
                "preimage": {
                    "exists": True,
                    "sha256": _sha(before),
                    "byte_length": len(before.encode("utf-8")),
                },
                "postimage": {
                    "exists": True,
                    "sha256": _sha(after),
                    "byte_length": len(after.encode("utf-8")),
                },
                "publication_mode": "replace",
            }
        )
    authority_bytes = "synthetic receipt B17\n"
    authority_image = {
        "exists": True,
        "sha256": _sha(authority_bytes),
        "byte_length": len(authority_bytes.encode("utf-8")),
    }
    absent = {"exists": False, "sha256": None, "byte_length": None}
    return {
        "schema_version": "1.0.0",
        "transition_id": "synthetic-b18-transition",
        "state": "validated",
        "project_root": "synthetic://governed-staging/work-1/run-1",
        "destination_capability": "governed_staging",
        "active_target": {
            "path": "synthetic/active_target.json",
            "sha256": _sha(target_bytes),
            "byte_length": len(target_bytes.encode("utf-8")),
        },
        "members": members,
        "superseded_authority": [
            {
                "receipt_id": "synthetic-receipt-b17",
                "authority_kind": "receipt",
                "pre_state": "ready",
                "post_state": "invalidated",
            }
        ],
        "preimage_digest": _sha("synthetic-preimages-b17"),
        "postimage_digest": _sha("synthetic-postimages-b18"),
        "journal": {"state": "prepared", "events": ["prepared"]},
        "publication_manifest": {
            "state": "candidate",
            "member_publications": [
                {
                    "member": row["member"],
                    "path": row["path"],
                    "staged_path": f"transaction/staged/{row['member']}.bin",
                    "postimage": copy.deepcopy(row["postimage"]),
                }
                for row in members
            ],
            "invalidations": [
                {
                    "receipt_id": "synthetic-receipt-b17",
                    "authority_kind": "receipt",
                    "pre_state": "ready",
                    "post_state": "invalidated",
                    "source": {
                        "path": "authority/ready/synthetic-receipt-b17.json",
                        "preimage": authority_image,
                        "postimage": absent,
                    },
                    "destination": {
                        "path": "authority/invalidated/synthetic-receipt-b17.json",
                        "preimage": absent,
                        "postimage": authority_image,
                    },
                    "staged_path": "transaction/staged_authority/synthetic-receipt-b17.json",
                }
            ],
            "completed_effects": [],
        },
        "commit_marker": None,
    }


def _leaf_differences(left: Any, right: Any, path: str = "$") -> list[str]:
    if type(left) is not type(right):
        return [path]
    if isinstance(left, dict):
        if set(left) != set(right):
            return [path]
        differences: list[str] = []
        for key in sorted(left):
            differences.extend(_leaf_differences(left[key], right[key], f"{path}.{key}"))
        return differences
    if isinstance(left, list):
        if len(left) != len(right):
            return [path]
        differences: list[str] = []
        for index, (left_item, right_item) in enumerate(zip(left, right, strict=True)):
            differences.extend(_leaf_differences(left_item, right_item, f"{path}[{index}]"))
        return differences
    return [] if left == right else [path]


def _load_module() -> Any | None:
    if not PRODUCTION.is_file():
        return None
    spec = importlib.util.spec_from_file_location("control_plane_transition", PRODUCTION)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _observe(module: Any, payload: dict[str, Any]) -> tuple[str | None, list[Any]]:
    function = getattr(module, API, None)
    if not callable(function):
        return "INTERFACE_BLOCKED", []
    try:
        result = function(copy.deepcopy(payload))
    except Exception as exc:  # production refusal types are intentionally typed by code
        return getattr(exc, "code", type(exc).__name__), []
    if not isinstance(result, dict):
        return "INTERFACE_INVALID", []
    findings = result.get("findings", [])
    return None, findings if isinstance(findings, list) else ["findings-not-array"]


def _expect_code(expected: str, function: Any, *args: Any, **kwargs: Any) -> None:
    try:
        function(*args, **kwargs)
    except Exception as exc:
        observed = getattr(exc, "code", type(exc).__name__)
        if observed != expected:
            raise AssertionError(f"expected {expected}, observed {observed}: {exc}") from exc
        return
    raise AssertionError(f"expected refusal {expected}")


def _project_fixture(root: Path) -> tuple[dict[str, Any], dict[str, bytes]]:
    plan: dict[str, Any] = {"members": [], "superseded_authority": []}
    expected: dict[str, bytes] = {}
    for index, name in enumerate(
        (
            "controlling_brief",
            "directives",
            "active_target",
            "round_program",
            "revision_plan",
            "assignment_source_binding",
            "reader_policy_binding",
            "affected_receipts_and_evaluations",
        )
    ):
        target_rel = (
            "milestones/M1.md" if name == "active_target" else f"controls/{name}.json"
        )
        candidate_rel = f"candidate/{name}.bin"
        before = f"synthetic {name} revision B17\n".encode("utf-8")
        after = f"synthetic {name} revision B18\n".encode("utf-8")
        mode = "replace"
        if index == 0:
            mode = "create"
        elif index == 7:
            mode = "delete"
        target = root / target_rel
        candidate = root / candidate_rel
        if mode != "create":
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(before)
        if mode != "delete":
            candidate.parent.mkdir(parents=True, exist_ok=True)
            candidate.write_bytes(after)
        plan["members"].append(
            {
                "member": name,
                "control_revision": "B18",
                "path": target_rel,
                "candidate_path": candidate_rel if mode != "delete" else None,
                "publication_mode": mode,
            }
        )
        if mode == "delete":
            plan["members"][-1].pop("candidate_path")
        expected[target_rel] = after if mode != "delete" else b""

    authority_rel = "reviews/.harness/assignment/ready/synthetic-receipt-b17.json"
    authority = root / authority_rel
    authority.parent.mkdir(parents=True, exist_ok=True)
    authority.write_text(
        json.dumps(
            {
                "schema_version": "synthetic",
                "receipt_id": "synthetic-receipt-b17",
                "state": "ready",
                "artifact": "milestones/M1.md",
            },
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
        newline="",
    )
    plan["superseded_authority"].append(
        {
            "receipt_id": "synthetic-receipt-b17",
            "authority_kind": "receipt",
            "pre_state": "ready",
            "path": authority_rel,
        }
    )
    return plan, expected


def _transaction_path(root: Path, transition_id: str, name: str) -> Path:
    return (
        root
        / "reviews"
        / ".harness"
        / "control-plane"
        / "transitions"
        / transition_id
        / name
    )


def _write_record(root: Path, transition_id: str, payload: dict[str, Any]) -> None:
    _transaction_path(root, transition_id, "transaction.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="",
    )


def _late_authority(root: Path, name: str = "late-receipt.json") -> Path:
    path = root / "reviews/.harness/assignment/ready" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"schema_version": "synthetic", "receipt_id": name[:-5], "state": "ready"},
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
        newline="",
    )
    return path


def _assert_postimages(root: Path, expected: dict[str, bytes]) -> None:
    for relative, data in expected.items():
        path = root / relative
        if data:
            assert path.read_bytes() == data, f"wrong postimage: {relative}"
        else:
            assert not path.exists(), f"delete postimage still exists: {relative}"
    ready = root / "reviews/.harness/assignment/ready/synthetic-receipt-b17.json"
    invalidated = root / "reviews/.harness/assignment/invalidated/synthetic-receipt-b17.json"
    assert not ready.exists(), "superseded authority remains in ready lane"
    authority = json.loads(
        invalidated.read_text(
            encoding="utf-8"
        )
    )
    assert authority["receipt_id"] == "synthetic-receipt-b17"


def _package_root() -> TemporaryDirectory[str]:
    return TemporaryDirectory(prefix=".v040-c2-control-", dir=ROOT)


def _run_direct_api_cases(module: Any, base: dict[str, Any]) -> list[str]:
    cases: list[tuple[str, dict[str, Any]]] = []

    def member_path(candidate: dict[str, Any], index: int, path: str) -> None:
        candidate["members"][index]["path"] = path
        candidate["publication_manifest"]["member_publications"][index]["path"] = path

    traversal = copy.deepcopy(base)
    traversal["members"][0]["path"] = "../escape.json"
    cases.append(("member_traversal", traversal))

    dot_segment = copy.deepcopy(base)
    member_path(dot_segment, 1, "synthetic/./directives.json")
    cases.append(("member_raw_dot_segment", dot_segment))

    repeated_separator = copy.deepcopy(base)
    member_path(repeated_separator, 1, "synthetic//directives.json")
    cases.append(("member_repeated_separator", repeated_separator))

    absolute = copy.deepcopy(base)
    absolute["publication_manifest"]["member_publications"][0]["staged_path"] = (
        "C:/synthetic/escape.bin"
    )
    cases.append(("staged_absolute", absolute))

    separator = copy.deepcopy(base)
    separator["publication_manifest"]["invalidations"][0]["source"]["path"] = (
        "authority\\ready\\synthetic-receipt-b17.json"
    )
    cases.append(("source_backslash_separator", separator))

    alias = copy.deepcopy(base)
    alias["members"][1]["path"] = "SYNTHETIC/CONTROLLING_BRIEF.JSON"
    cases.append(("normalized_member_alias", alias))

    staged_alias = copy.deepcopy(base)
    staged_alias["publication_manifest"]["member_publications"][1]["staged_path"] = (
        "TRANSACTION/STAGED/CONTROLLING_BRIEF.BIN"
    )
    cases.append(("normalized_staged_alias", staged_alias))

    destination_alias = copy.deepcopy(base)
    destination_alias["publication_manifest"]["invalidations"][0]["destination"]["path"] = (
        "AUTHORITY/READY/SYNTHETIC-RECEIPT-B17.JSON"
    )
    cases.append(("normalized_invalidation_alias", destination_alias))

    marker = copy.deepcopy(base)
    marker["state"] = "committed"
    marker["commit_marker"] = {
        "path": "../commit_marker.json",
        "sha256": "0" * 64,
        "byte_length": 0,
    }
    cases.append(("marker_traversal", marker))

    trailing_dot = copy.deepcopy(base)
    member_path(trailing_dot, 1, "synthetic/controlling_brief.json.")
    cases.append(("windows_trailing_dot_alias_collision", trailing_dot))

    trailing_space = copy.deepcopy(base)
    member_path(trailing_space, 1, "synthetic/controlling_brief.json ")
    cases.append(("windows_trailing_space_alias_collision", trailing_space))

    reserved_paths = (
        ("reserved_nul_bare", "NUL"),
        ("reserved_nul_extension", "synthetic/NUL.json"),
        ("reserved_con_mixed_case", "synthetic/CoN.txt"),
        ("reserved_prn", "synthetic/PRN"),
        ("reserved_aux_spaced_stem", "synthetic/AUX .log"),
        ("reserved_com1_extension", "synthetic/COM1.json"),
        ("reserved_com9_mixed_case", "synthetic/cOm9.log"),
        ("reserved_lpt1_extension", "synthetic/LPT1.json"),
        ("reserved_lpt9_mixed_case", "synthetic/lPt9.log"),
    )
    for name, path in reserved_paths:
        candidate = copy.deepcopy(base)
        member_path(candidate, 1, path)
        cases.append((name, candidate))

    staged_reserved = copy.deepcopy(base)
    staged_reserved["publication_manifest"]["member_publications"][1]["staged_path"] = (
        "transaction/NUL.bin"
    )
    cases.append(("staged_reserved_device", staged_reserved))

    invalidation_reserved = copy.deepcopy(base)
    invalidation_reserved["publication_manifest"]["invalidations"][0]["destination"]["path"] = (
        "authority/invalidated/COM1.json"
    )
    cases.append(("invalidation_reserved_device", invalidation_reserved))

    invalid_character_paths = (
        ("member_question_mark", "member", "synthetic/invalid?.json"),
        ("member_asterisk", "member", "synthetic/invalid*.json"),
        ("staged_pipe", "staged", "transaction/staged/invalid|.bin"),
        ("staged_less_than", "staged", "transaction/staged/invalid<.bin"),
        (
            "invalidation_greater_than",
            "invalidation_destination",
            "authority/invalidated/invalid>.json",
        ),
        (
            "invalidation_quote",
            "invalidation_staged",
            'transaction/staged_authority/invalid".json',
        ),
    )
    for name, surface, path in invalid_character_paths:
        candidate = copy.deepcopy(base)
        if surface == "member":
            member_path(candidate, 1, path)
        elif surface == "staged":
            candidate["publication_manifest"]["member_publications"][1]["staged_path"] = path
        elif surface == "invalidation_destination":
            candidate["publication_manifest"]["invalidations"][0]["destination"]["path"] = path
        else:
            candidate["publication_manifest"]["invalidations"][0]["staged_path"] = path
        cases.append((f"win32_invalid_{name}", candidate))

    for codepoint in range(0x20):
        candidate = copy.deepcopy(base)
        member_path(
            candidate,
            1,
            f"synthetic/control-{codepoint:02x}{chr(codepoint)}.json",
        )
        cases.append((f"ascii_control_u{codepoint:04x}", candidate))

    missing = copy.deepcopy(base)
    missing["publication_manifest"]["invalidations"] = []
    _expect_code("CPT-IDENTITY-SPLIT", module.validate_transition, missing)
    completed = ["direct_missing_invalidation_bijection"]
    for name, candidate in cases:
        _expect_code(
            "CPT-DESTINATION-PROTECTED", module.validate_transition, candidate
        )
        completed.append(f"direct_{name}_refused")

    benign_paths = (
        ("null_not_nul", "synthetic/NULL.json"),
        ("com10_not_reserved", "synthetic/COM10.json"),
        ("lpt10_not_reserved", "synthetic/lpt10.log"),
        ("auxiliary_not_aux", "synthetic/AUXILIARY.json"),
        (
            "valid_punctuation",
            "synthetic/report (draft)_[v2]+ok,@home!#$%&'=;{}.json",
        ),
    )
    for name, path in benign_paths:
        candidate = copy.deepcopy(base)
        member_path(candidate, 1, path)
        result = module.validate_transition(candidate)
        assert result.get("findings") == [], f"benign Windows path refused: {path}"
        completed.append(f"direct_{name}_accepted")
    return completed


def _run_transaction_cases(module: Any) -> list[str]:
    completed: list[str] = []

    with _package_root() as temporary:
        project = Path(temporary)
        plan, expected = _project_fixture(project)
        transition_id = "atomic-publish"
        prepared = module.prepare(project, plan, transition_id)
        assert prepared["state"] == "prepared"
        assert module.validate(project, transition_id)["findings"] == []
        writes: list[Path] = []
        original = module._atomic_write

        def tracked(path: Path, data: bytes) -> None:
            original(path, data)
            writes.append(path)

        module._atomic_write = tracked
        try:
            committed = module.publish(project, transition_id)
        finally:
            module._atomic_write = original
        assert committed["state"] == "committed"
        assert writes[-1].name == "commit_marker.json", "commit marker was not written last"
        _assert_postimages(project, expected)
        assert module.verify_committed(project, transition_id)["findings"] == []
        completed.append("atomic_prepare_validate_publish_marker_last")

        before_replay = {
            path.relative_to(project).as_posix(): path.read_bytes()
            for path in project.rglob("*")
            if path.is_file()
        }
        module.publish(project, transition_id)
        after_replay = {
            path.relative_to(project).as_posix(): path.read_bytes()
            for path in project.rglob("*")
            if path.is_file()
        }
        assert after_replay == before_replay, "committed replay changed bytes"
        completed.append("committed_replay_idempotent")

    with _package_root() as temporary:
        project = Path(temporary)
        plan, expected = _project_fixture(project)
        transition_id = "partial-recover"
        module.prepare(project, plan, transition_id)
        _expect_code(
            "CPT-PUBLICATION-INCOMPLETE",
            module.publish,
            project,
            transition_id,
            crash_after_effects=2,
        )
        assert not _transaction_path(project, transition_id, "commit_marker.json").exists()
        _expect_code(
            "CPT-PUBLICATION-INCOMPLETE", module.verify_committed, project, transition_id
        )
        module.recover(project, transition_id)
        _assert_postimages(project, expected)
        assert module.verify_committed(project, transition_id)["findings"] == []
        completed.append("partial_crash_nonauthoritative_then_recover")

    with _package_root() as temporary:
        project = Path(temporary)
        plan, expected = _project_fixture(project)
        transition_id = "marker-crash"
        module.prepare(project, plan, transition_id)
        _expect_code(
            "CPT-PUBLICATION-INCOMPLETE",
            module.publish,
            project,
            transition_id,
            crash_before_marker=True,
        )
        _assert_postimages(project, expected)
        assert not _transaction_path(project, transition_id, "commit_marker.json").exists()
        _expect_code(
            "CPT-PUBLICATION-INCOMPLETE", module.verify_committed, project, transition_id
        )
        module.recover(project, transition_id)
        assert module.verify_committed(project, transition_id)["findings"] == []
        completed.append("all_effects_crash_before_marker_then_recover")

    with _package_root() as temporary:
        project = Path(temporary)
        plan, expected = _project_fixture(project)
        transition_id = "authority-move-crash"
        module.prepare(project, plan, transition_id)
        _expect_code(
            "CPT-PUBLICATION-INCOMPLETE",
            module.publish,
            project,
            transition_id,
            crash_after_effects=9,
        )
        ready = project / "reviews/.harness/assignment/ready/synthetic-receipt-b17.json"
        invalidated = project / "reviews/.harness/assignment/invalidated/synthetic-receipt-b17.json"
        assert ready.is_file() and invalidated.is_file(), "expected safe duplicate-state crash surface"
        assert not _transaction_path(project, transition_id, "commit_marker.json").exists()
        module.recover(project, transition_id)
        _assert_postimages(project, expected)
        assert module.verify_committed(project, transition_id)["findings"] == []
        completed.append("authority_move_crash_recovery")

    with _package_root() as temporary:
        project = Path(temporary)
        plan, _ = _project_fixture(project)
        transition_id = "stale-preimage"
        module.prepare(project, plan, transition_id)
        target = project / "controls/directives.json"
        target.write_bytes(b"foreign concurrent bytes\n")
        _expect_code("CPT-PREIMAGE-STALE", module.publish, project, transition_id)
        assert not _transaction_path(project, transition_id, "commit_marker.json").exists()
        completed.append("stale_preimage_refused")

    with _package_root() as temporary:
        project = Path(temporary)
        plan, _ = _project_fixture(project)
        transition_id = "foreign-recovery"
        module.prepare(project, plan, transition_id)
        _expect_code(
            "CPT-PUBLICATION-INCOMPLETE",
            module.publish,
            project,
            transition_id,
            crash_after_effects=2,
        )
        (project / "controls/directives.json").write_bytes(b"foreign after crash\n")
        _expect_code("CPT-RECOVERY-REQUIRED", module.recover, project, transition_id)
        record = json.loads(
            _transaction_path(project, transition_id, "transaction.json").read_text(
                encoding="utf-8"
            )
        )
        assert record["state"] == "recovery_required"
        assert not _transaction_path(project, transition_id, "commit_marker.json").exists()
        completed.append("foreign_partial_state_recovery_refused")

    with _package_root() as temporary:
        project = Path(temporary)
        plan, _ = _project_fixture(project)
        plan["superseded_authority"] = []
        _expect_code(
            "CPT-LIVE-RECEIPT",
            module.prepare,
            project,
            plan,
            "omitted-live-authority",
        )
        assert not _transaction_path(
            project, "omitted-live-authority", "transaction.json"
        ).exists()
        completed.append("omitted_live_authority_refused_before_effect")

    with _package_root() as temporary:
        project = Path(temporary)
        plan, _ = _project_fixture(project)
        transition_id = "win32-invalid-prepare"
        plan["members"][0]["path"] = "controls/invalid?.json"
        directives = project / "controls/directives.json"
        directives_before = directives.read_bytes()
        ready_authority = (
            project
            / "reviews/.harness/assignment/ready/synthetic-receipt-b17.json"
        )
        _expect_code(
            "CPT-DESTINATION-PROTECTED",
            module.prepare,
            project,
            plan,
            transition_id,
        )
        assert not (project / "controls/invalid?.json").exists()
        assert not (project / "controls/controlling_brief.json").exists()
        assert directives.read_bytes() == directives_before
        assert ready_authority.is_file()
        assert not (
            project
            / "reviews/.harness/assignment/invalidated/synthetic-receipt-b17.json"
        ).exists()
        transaction_root = _transaction_path(
            project, transition_id, "transaction.json"
        ).parent
        assert not transaction_root.exists()
        assert not (
            project / "reviews/.harness/control-plane/active_claim.json"
        ).exists()
        completed.append("win32_invalid_prepare_refused_before_durable_effect")

    with _package_root() as temporary:
        sandbox = Path(temporary)
        fake_harness = sandbox / "synthetic-harness"
        fake_harness.mkdir()
        governed = sandbox / "governed"
        routing = governed / "governance/output-routing/output_routing.yaml"
        routing.parent.mkdir(parents=True)
        routing.write_text("schema_version: synthetic\n", encoding="utf-8", newline="")
        protected = governed / "research/60_Workbench/work-1"
        protected.mkdir(parents=True)
        plan, _ = _project_fixture(protected)
        prior_harness = module.destinations.HARNESS
        prior_extra = os.environ.get("COAUTHOR_EXTRA_GOVERNED_ROOTS")
        module.destinations.HARNESS = fake_harness
        os.environ["COAUTHOR_EXTRA_GOVERNED_ROOTS"] = str(governed)
        try:
            _expect_code(
                "CPT-DESTINATION-PROTECTED",
                module.prepare,
                protected,
                plan,
                "protected-destination",
            )
            assert not (protected / "reviews/.harness/control-plane").exists()
            with module.authority_issuance_guard(
                protected, allow_repin_container=True,
            ):
                pass
        finally:
            module.destinations.HARNESS = prior_harness
            if prior_extra is None:
                os.environ.pop("COAUTHOR_EXTRA_GOVERNED_ROOTS", None)
            else:
                os.environ["COAUTHOR_EXTRA_GOVERNED_ROOTS"] = prior_extra
        completed.append("protected_destination_no_effect")

    with _package_root() as temporary:
        project = Path(temporary)
        plan, _ = _project_fixture(project)
        transition_id = "missing-invalidation"
        module.prepare(project, plan, transition_id)
        record = json.loads(
            _transaction_path(project, transition_id, "transaction.json").read_text(
                encoding="utf-8"
            )
        )
        record["publication_manifest"]["invalidations"] = []
        _write_record(project, transition_id, record)
        _expect_code("CPT-IDENTITY-SPLIT", module.validate, project, transition_id)
        assert not _transaction_path(project, transition_id, "commit_marker.json").exists()
        completed.append("missing_manifest_invalidation_refused_no_marker")

    with _package_root() as temporary:
        project = Path(temporary)
        plan, _ = _project_fixture(project)
        transition_id = "substituted-invalidation"
        module.prepare(project, plan, transition_id)
        record = json.loads(
            _transaction_path(project, transition_id, "transaction.json").read_text(
                encoding="utf-8"
            )
        )
        record["publication_manifest"]["invalidations"][0]["receipt_id"] = "substituted-receipt"
        _write_record(project, transition_id, record)
        _expect_code("CPT-IDENTITY-SPLIT", module.publish, project, transition_id)
        assert not _transaction_path(project, transition_id, "commit_marker.json").exists()
        completed.append("substituted_manifest_invalidation_refused_no_marker")

    with _package_root() as temporary:
        project = Path(temporary)
        plan, _ = _project_fixture(project)
        transition_id = "late-before-effects"
        module.prepare(project, plan, transition_id)
        _late_authority(project)
        _expect_code("CPT-LIVE-RECEIPT", module.publish, project, transition_id)
        assert not _transaction_path(project, transition_id, "commit_marker.json").exists()
        assert not (project / "controls/controlling_brief.json").exists()
        completed.append("late_receipt_pre_effect_epoch_refused")

    with _package_root() as temporary:
        project = Path(temporary)
        plan, _ = _project_fixture(project)
        transition_id = "late-before-marker"
        module.prepare(project, plan, transition_id)
        original_post_epoch = module._assert_post_authority_epoch

        def inject_before_marker(bound_project: Path, record: dict[str, Any]) -> None:
            _late_authority(bound_project, "late-before-marker.json")
            original_post_epoch(bound_project, record)

        module._assert_post_authority_epoch = inject_before_marker
        try:
            _expect_code("CPT-LIVE-RECEIPT", module.publish, project, transition_id)
        finally:
            module._assert_post_authority_epoch = original_post_epoch
        assert not _transaction_path(project, transition_id, "commit_marker.json").exists()
        completed.append("late_receipt_pre_marker_epoch_refused")

    with _package_root() as temporary:
        project = Path(temporary)
        plan, _ = _project_fixture(project)
        module.prepare(project, plan, "claim-owner")
        _expect_code(
            "CPT-RECOVERY-REQUIRED", module.prepare, project, plan, "concurrent-prepare"
        )
        assert not _transaction_path(project, "concurrent-prepare", "transaction.json").exists()
        with module._authority_lock(project):
            _expect_code(
                "CPT-RECOVERY-REQUIRED", module.publish, project, "claim-owner"
            )
        completed.append("concurrent_prepare_and_publish_refused")

    with _package_root() as temporary:
        project = Path(temporary)
        plan, _ = _project_fixture(project)
        transition_id = "live-owner-recovery"
        module.prepare(project, plan, transition_id)
        process = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        try:
            claim_path = project / "reviews/.harness/control-plane/active_claim.json"
            claim = json.loads(claim_path.read_text(encoding="utf-8"))
            claim["owner"] = {"host": module.platform.node(), "pid": process.pid}
            claim_path.write_text(
                json.dumps(claim, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
                newline="",
            )
            _expect_code(
                "CPT-RECOVERY-REQUIRED", module.recover, project, transition_id
            )
            assert not _transaction_path(project, transition_id, "commit_marker.json").exists()
        finally:
            process.terminate()
            process.wait(timeout=5)
        completed.append("live_owner_recovery_refused")

    with _package_root() as temporary:
        project = Path(temporary)
        plan, _ = _project_fixture(project)
        transition_id = "parent-reparse"
        module.prepare(project, plan, transition_id)
        original_is_link = module._is_link
        substituted_parent = project / "controls"

        def synthetic_reparse(path: Path) -> bool:
            return path == substituted_parent or original_is_link(path)

        module._is_link = synthetic_reparse
        try:
            _expect_code(
                "CPT-DESTINATION-PROTECTED", module.publish, project, transition_id
            )
        finally:
            module._is_link = original_is_link
        assert not _transaction_path(project, transition_id, "commit_marker.json").exists()
        assert not (project / "controls/controlling_brief.json").exists()
        completed.append("parent_reparse_substitution_refused")

    with _package_root() as temporary:
        project = Path(temporary)
        plan, _ = _project_fixture(project)
        transition_id = "real-issuance-guard"
        module.prepare(project, plan, transition_id)
        from assignment_fixture_support import write_valid_contract
        from assignment_receipt_transaction import ReceiptTransactionError, _transaction_claim

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
        (project / "reviews/phase_state.json").write_text(
            json.dumps(phase_state, indent=2) + "\n", encoding="utf-8", newline=""
        )
        receipt_rel = (
            "reviews/.harness/assignment/ready/"
            "gate_receipt_M1_20260726T000000Z.json"
        )
        gate = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/assignment_process_gate.py"),
                "--project-root",
                str(project),
                "--stage",
                "draft",
                "--target-milestone",
                "M1",
                "--emit-receipt",
                receipt_rel,
            ],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
        assert gate.returncode == 4 and "CPT-LIVE-RECEIPT" in gate.stdout, (
            gate.stdout + gate.stderr
        )
        assert not (project / receipt_rel).exists()
        try:
            with _transaction_claim(project):
                raise AssertionError("receipt transition unexpectedly entered")
        except ReceiptTransactionError as exc:
            assert exc.code == "CPT-LIVE-RECEIPT", exc
        completed.append("real_process_gate_and_receipt_transition_refused")

    with _package_root() as temporary:
        project = Path(temporary)
        plan, _ = _project_fixture(project)
        transition_id = "committed-invalidation-tamper"
        module.prepare(project, plan, transition_id)
        module.publish(project, transition_id)
        record = json.loads(
            _transaction_path(project, transition_id, "transaction.json").read_text(
                encoding="utf-8"
            )
        )
        record["publication_manifest"]["invalidations"][0]["authority_kind"] = "evaluation"
        _write_record(project, transition_id, record)
        _expect_code(
            "CPT-IDENTITY-SPLIT", module.verify_committed, project, transition_id
        )
        completed.append("committed_invalidation_tamper_refused")

    return completed


def main() -> int:
    base = _base()
    pairs: list[tuple[str, str, dict[str, Any], dict[str, Any]]] = []

    mixed = copy.deepcopy(base)
    mixed["members"][1]["control_revision"] = "B17"
    pairs.append(("mixed_control_revision", "CPT-CONTROL-REVISION-MIXED", mixed, base))

    split = copy.deepcopy(base)
    split["active_target"]["sha256"] = _sha("different target identity\n")
    pairs.append(("split_target_identity", "CPT-IDENTITY-SPLIT", split, base))

    live = copy.deepcopy(base)
    live["superseded_authority"][0]["post_state"] = "ready"
    pairs.append(("old_live_receipt_after_rebind", "CPT-LIVE-RECEIPT", live, base))

    module = _load_module()
    failures: list[str] = []
    for name, expected, red, clean in pairs:
        delta = _leaf_differences(red, clean)
        if len(delta) != 1:
            failures.append(f"{name}: fixture pair changes {len(delta)} leaves: {delta}")
            continue
        if module is None:
            failures.append(
                f"{name}: INTERFACE_BLOCKED expected {expected}; clean twin deferred; delta={delta[0]}"
            )
            continue
        red_code, _ = _observe(module, red)
        clean_code, clean_findings = _observe(module, clean)
        if red_code != expected:
            failures.append(f"{name}: expected {expected}, observed {red_code!r}")
        if clean_code is not None or clean_findings:
            failures.append(
                f"{name}: clean twin must have zero relevant findings; code={clean_code!r} findings={clean_findings!r}"
            )

    if module is not None:
        try:
            direct = _run_direct_api_cases(module, base)
            if len(direct) != 66:
                failures.append(f"direct API coverage expected 66 cases, observed {len(direct)}")
            completed = _run_transaction_cases(module)
            if len(completed) != 19:
                failures.append(f"transaction coverage expected 19 cases, observed {len(completed)}")
        except Exception as exc:
            failures.append(f"transaction behavior: {type(exc).__name__}: {exc}")

    if failures:
        for failure in failures:
            print(f"[RED] {failure}")
        print(f"control_plane_transition_smoketest: FAIL ({len(failures)} of {len(pairs)} pairs blocked)")
        return 1
    print(
        f"control_plane_transition_smoketest: PASS "
        f"({len(pairs)} red/clean pairs + 66 direct API + 19 transaction cases)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
