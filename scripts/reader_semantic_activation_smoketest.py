#!/usr/bin/env python3
"""Transaction tests for governed reader-profile-v2 semantic activation."""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import assignment_milestone_transaction as amt


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(amt._json_bytes(value))


class FakePolicy:
    class PolicyError(Exception):
        pass

    def __init__(self, root: Path, wiki: Path, fresh: dict, *, fail_binding: bool = False):
        self.ROOT = root
        self.DEFAULT_PROFILE = root / "references/policies/reader_accessibility.v1.json"
        self.wiki = wiki
        self.fresh = copy.deepcopy(fresh)
        self.fail_binding = fail_binding

    def resolve_policy(self, project: Path) -> dict:
        return copy.deepcopy(self.fresh)

    def phase_state_binding(self, resolved: dict, resolved_path: Path, project: Path) -> dict:
        if self.fail_binding:
            raise self.PolicyError("injected binding failure")
        expected = resolved["resolved_profile"]["domain_native_register"]["expected_verification"]
        return {
            "profile_path": resolved["profile_path"],
            "profile_sha256": resolved["profile_sha256"],
            "resolved_path": resolved_path.relative_to(project).as_posix(),
            "resolved_sha256": hashlib.sha256(resolved_path.read_bytes()).hexdigest(),
            "source_bindings": copy.deepcopy(resolved["source_bindings"]),
            "project_identity": resolved.get("project_identity"),
            "attestation_view_pin": resolved["attestation_view_pin"],
            "exemplar_view_pin": resolved["exemplar_view_pin"],
            "pin_epoch": expected["pin_epoch"],
            "pinned_at": expected["pinned_at"],
            "graph_sha256_provenance": resolved["graph_sha256_provenance"],
            "register_provenance": copy.deepcopy(resolved["register_provenance"]),
            "transitions": {},
        }


def fixture(root: Path, *, fail_binding: bool = False) -> tuple[dict, FakePolicy]:
    harness = root / "harness"
    wiki = root / "wiki"
    project = root / "project"
    receipt = wiki / "graphify-out/semantic-qualifications/semq-20260808T000000Z-1234abcd/receipt.json"
    receipt.parent.mkdir(parents=True)
    receipt.write_text('{"status":"qualified"}\n', encoding="utf-8")
    graph_relative = (
        "knowledge/LLM wiki/graphify-out/semantic-qualifications/"
        "semq-20260808T000000Z-1234abcd/qualified.graph.json"
    )
    graph_sha = "3" * 64
    attestation = "4" * 64
    exemplar = "5" * 64
    profile_sha = "6" * 64
    fresh = {
        "contract_version": "1.1.0",
        "profile_path": "references/policies/reader_accessibility.v1.json",
        "profile_sha256": profile_sha,
        "register_class": "domain-native",
        "passage_scope_class": "technical",
        "project_identity": "fixture",
        "resolved_profile": {"domain_native_register": {
            "corpus_binding": {"graph": {"path": graph_relative}},
            "expected_verification": {
                "attestation_view_pin": attestation,
                "exemplar_view_pin": exemplar,
                "pin_epoch": 2,
                "pinned_at": "2026-08-08T00:00:00Z",
            },
        }},
        "source_bindings": [{
            "scope": "package", "path": "references/policies/reader_accessibility.v1.json",
            "sha256": profile_sha, "role": "package_profile",
        }],
        "attestation_view_pin": attestation,
        "exemplar_view_pin": exemplar,
        "graph_sha256_provenance": graph_sha,
        "register_provenance": {
            "path_roots": {"effective": {"wiki_root": str(wiki)}},
            "provenance": [{
                "role": "semantic_receipt", "path": str(receipt),
                "sha256": hashlib.sha256(receipt.read_bytes()).hexdigest(),
            }],
        },
    }
    resolved = project / "reviews/.harness/policies/reader_accessibility.resolved.json"
    resolved.parent.mkdir(parents=True)
    old_payload = {
        "contract_version": "2.0.0", "binding_kind": "reader_profile",
        "semantic_usage": "not_invoked",
    }
    resolved.write_bytes(amt._json_bytes(old_payload))
    transitions = {
        key: {"state": "active", "observed_count": 0, "last_event_sequence": None, "events": []}
        for key in ("G", "H", "VE")
    }
    old_binding = {
        "binding_version": "2.0.0", "binding_kind": "reader_profile",
        "semantic_usage": "not_invoked",
        "profile_path": "references/policies/reader_accessibility.v1.json",
        "profile_sha256": "1" * 64,
        "resolved_path": resolved.relative_to(project).as_posix(),
        "resolved_sha256": hashlib.sha256(resolved.read_bytes()).hexdigest(),
        "source_bindings": [{
            "scope": "package", "path": "old", "sha256": "1" * 64,
            "role": "package_profile",
        }],
        "project_identity": "fixture",
        "transitions": transitions,
    }
    milestones = {
        "M1": {"status": "in_progress", "policy_evidence": {"reader_model": {"fixture": True}}},
        **{name: {"status": "not_started"} for name in ("M2", "M3", "M4", "M5")},
    }
    state = {"milestone_framework": {
        "policy_bindings": {"reader_accessibility": old_binding},
        "milestones": milestones,
    }}
    state_path = project / "reviews/phase_state.json"
    write_json(state_path, state)
    ledger = harness / "references/policies/repin_log.jsonl"
    ledger.parent.mkdir(parents=True)
    ledger_row = {
        "epoch": 2, "delta_class": "corpus", "pinned_at": "2026-08-08T00:00:00Z",
        "profile_sha256": {"old": "1" * 64, "new": profile_sha},
        "attestation_view_pin": {"old": attestation, "new": attestation},
        "exemplar_view_pin": {"old": exemplar, "new": exemplar},
        "graph_sha256_provenance": graph_sha,
        "snapshot_ref": "reviews/.harness/repin/epoch-2.snapshot.json",
        "operator": "José",
    }
    ledger.write_text(
        json.dumps(ledger_row, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8",
    )
    snapshot = harness / ledger_row["snapshot_ref"]
    write_json(snapshot, {"epoch": 2, "graph_sha256_provenance": graph_sha})
    event_bytes = (
        json.dumps(ledger_row, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    request = {
        "request_id": "fixture-request",
        "schema_version": "reader-semantic-activation.v1",
        "operation": "reader_profile_v2_to_semantic",
        "phase_state_sha256": hashlib.sha256(state_path.read_bytes()).hexdigest(),
        "prior_binding_sha256": hashlib.sha256(amt._json_bytes(old_binding)).hexdigest(),
        "prior_resolved_sha256": old_binding["resolved_sha256"],
        "pin_epoch": 2,
        "profile_sha256": profile_sha,
        "attestation_view_pin": attestation,
        "exemplar_view_pin": exemplar,
        "delta_class": "corpus",
        "repin_log_ref": "references/policies/repin_log.jsonl#epoch-2",
        "repin_event_sha256": hashlib.sha256(event_bytes).hexdigest(),
        "repin_ledger_sha256": hashlib.sha256(ledger.read_bytes()).hexdigest(),
        "repin_snapshot_ref": ledger_row["snapshot_ref"],
        "repin_snapshot_sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(),
        "graph_path": graph_relative,
        "graph_sha256": graph_sha,
        "qualification_receipt_path": receipt.relative_to(wiki).as_posix(),
        "qualification_receipt_sha256": hashlib.sha256(receipt.read_bytes()).hexdigest(),
        "status": "pending",
    }
    request_path = project / "reviews/repin_rebind_request.json"
    write_json(request_path, request)
    fake = FakePolicy(harness, wiki, fresh, fail_binding=fail_binding)
    return {
        "project": project, "state": state, "state_path": state_path,
        "old_state": state_path.read_bytes(), "old_resolved": resolved.read_bytes(),
        "resolved": resolved, "request": request, "request_path": request_path,
        "request_bytes": request_path.read_bytes(), "old_binding": old_binding,
        "milestones": copy.deepcopy(milestones),
    }, fake


def invoke(fx: dict, fake: FakePolicy, validate_hook=None) -> Path:
    original_validate = amt.validate_document
    def validate(_project: Path, _state: dict) -> SimpleNamespace:
        if validate_hook is not None:
            validate_hook()
        return SimpleNamespace(findings=[])
    amt.validate_document = validate
    try:
        return amt._activate_reader_profile_semantic(
            fx["project"], fx["state_path"], copy.deepcopy(fx["state"]),
            hashlib.sha256(fx["old_state"]).hexdigest(),
            copy.deepcopy(fx["state"]["milestone_framework"]),
            copy.deepcopy(fx["old_binding"]), fx["request_path"],
            "2026-08-08T00:00:00Z", fake,
        )
    finally:
        amt.validate_document = original_validate


def case_apply_preserves_milestones() -> None:
    with tempfile.TemporaryDirectory() as td:
        fx, fake = fixture(Path(td))
        archive = invoke(fx, fake)
        assert archive.is_file() and not fx["request_path"].exists()
        state = json.loads(fx["state_path"].read_text(encoding="utf-8"))
        binding = state["milestone_framework"]["policy_bindings"]["reader_accessibility"]
        assert "binding_version" not in binding
        assert binding["graph_sha256_provenance"] == fx["request"]["graph_sha256"]
        assert binding["transitions"] == fx["old_binding"]["transitions"]
        assert state["milestone_framework"]["milestones"] == fx["milestones"]
        receipt = json.loads(archive.read_text(encoding="utf-8"))
        assert receipt["applied_by"] == "planner"
        assert receipt["rollback"]["phase_state_pre_sha256"] == fx["request"]["phase_state_sha256"]
        assert receipt["qualification_receipt_sha256"] == fx["request"]["qualification_receipt_sha256"]


def case_failure_restores_exact_preimages() -> None:
    with tempfile.TemporaryDirectory() as td:
        fx, fake = fixture(Path(td), fail_binding=True)
        try:
            invoke(fx, fake)
        except Exception as exc:
            assert "injected binding failure" in str(exc)
        else:
            raise AssertionError("injected Planner activation failure was accepted")
        assert fx["state_path"].read_bytes() == fx["old_state"]
        assert fx["resolved"].read_bytes() == fx["old_resolved"]
        assert fx["request_path"].read_bytes() == fx["request_bytes"]
        assert not list((fx["project"] / "reviews").glob("repin_rebind_request.*.applied.json"))


def case_external_postimage_conflict_is_preserved() -> None:
    with tempfile.TemporaryDirectory() as td:
        fx, fake = fixture(Path(td))
        foreign = b'{"external":"owner"}\n'
        def replace_resolver_during_validation() -> None:
            fx["resolved"].write_bytes(foreign)
        try:
            invoke(fx, fake, validate_hook=replace_resolver_during_validation)
        except amt.MilestoneTransactionError as exc:
            assert exc.code == "AMC-SEMANTIC-ACTIVATION-RECOVERY-CONFLICT"
        else:
            raise AssertionError("external resolver postimage was overwritten during rollback")
        assert fx["resolved"].read_bytes() == foreign
        assert fx["state_path"].read_bytes() == fx["old_state"]
        assert fx["request_path"].read_bytes() == fx["request_bytes"]


def case_prepublication_resolved_conflict_is_preserved() -> None:
    with tempfile.TemporaryDirectory() as td:
        fx, fake = fixture(Path(td))
        foreign = b'{"external":"before-publication"}\n'
        original_resolve = fake.resolve_policy

        def conflicting_resolve(project: Path) -> dict:
            result = original_resolve(project)
            fx["resolved"].write_bytes(foreign)
            return result

        fake.resolve_policy = conflicting_resolve  # type: ignore[method-assign]
        try:
            invoke(fx, fake)
        except amt.MilestoneTransactionError as exc:
            assert exc.code == "AMC-CONCURRENT-CHANGE"
        else:
            raise AssertionError("prepublication resolved-policy conflict was overwritten")
        assert fx["resolved"].read_bytes() == foreign
        assert fx["state_path"].read_bytes() == fx["old_state"]
        assert fx["request_path"].read_bytes() == fx["request_bytes"]


def case_ledger_and_snapshot_bindings_fail_closed() -> None:
    with tempfile.TemporaryDirectory() as td:
        fx, fake = fixture(Path(td))
        snapshot = fake.ROOT / fx["request"]["repin_snapshot_ref"]
        snapshot.write_bytes(b'{"external":"snapshot"}\n')
        try:
            invoke(fx, fake)
        except amt.MilestoneTransactionError as exc:
            assert exc.code == "AMC-SEMANTIC-ACTIVATION-LEDGER"
        else:
            raise AssertionError("stale re-pin snapshot was accepted")

    with tempfile.TemporaryDirectory() as td:
        fx, fake = fixture(Path(td))
        ledger = fake.ROOT / "references/policies/repin_log.jsonl"
        duplicated = ledger.read_bytes() + ledger.read_bytes()
        ledger.write_bytes(duplicated)
        request = json.loads(fx["request_path"].read_text(encoding="utf-8"))
        request["repin_ledger_sha256"] = hashlib.sha256(duplicated).hexdigest()
        write_json(fx["request_path"], request)
        fx["request_bytes"] = fx["request_path"].read_bytes()
        try:
            invoke(fx, fake)
        except amt.MilestoneTransactionError as exc:
            assert exc.code == "AMC-SEMANTIC-ACTIVATION-LEDGER"
        else:
            raise AssertionError("duplicate re-pin epoch was accepted")


def case_public_planner_command() -> None:
    result = subprocess.run(
        [sys.executable, str(Path(__file__).with_name("assignment_milestone_checkpoint.py")), "--help"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert result.returncode == 0
    assert "activate-reader-semantic" in result.stdout


def main() -> int:
    case_apply_preserves_milestones()
    case_failure_restores_exact_preimages()
    case_external_postimage_conflict_is_preserved()
    case_prepublication_resolved_conflict_is_preserved()
    case_ledger_and_snapshot_bindings_fail_closed()
    case_public_planner_command()
    print("reader_semantic_activation_smoketest: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
