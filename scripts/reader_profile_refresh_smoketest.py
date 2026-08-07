#!/usr/bin/env python3
"""Guard regressions for the v2 -> refreshed-v2 reader-profile transaction.

Covers the branch added 2026-08-07 to `assignment_milestone_transaction`:
`_refresh_reader_profile_v2`, dispatched from `rebind_reader_accessibility`
after the open-round refusal.

SCOPE. These cases exercise dispatch ordering and every guard clause that
fires BEFORE the transaction body writes anything. The write/validate/receipt/
rollback body needs the full milestone fixture chain, which builds through
`c2_evidence_fixture_support.build_activation_fixture` ->
`source_extract.py`, whose `SUPPORTED_PDF_EXTRACTOR` is pinned to the Windows
binary name `pdftotext.exe` and therefore cannot resolve on Linux
(`EXTRACTOR-UNAVAILABLE`, exit 4). End-to-end coverage lives in
`assignment_milestone_checkpoint_smoketest.py` and must be run host-side.
This file is the portion that is qualifiable on any host.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))

import assignment_milestone_transaction as amt  # noqa: E402
import reader_accessibility_policy as policy  # noqa: E402


V2_BINDING = {
    "binding_version": "2.0.0",
    "binding_kind": "reader_profile",
    "semantic_usage": "not_invoked",
    "profile_path": "references/policies/reader_accessibility.v1.json",
    "profile_sha256": "0" * 64,
    "resolved_path": "reviews/.harness/policies/reader_accessibility.resolved.json",
    "resolved_sha256": "0" * 64,
    "source_bindings": [],
    "project_identity": None,
    "transitions": {
        key: {"state": "active", "observed_count": 0, "last_event_sequence": None, "events": []}
        for key in ("G", "H", "VE")
    },
}


class _FakePolicy:
    PolicyError = policy.PolicyError

    def __init__(self, fresh: dict, hook=None):
        self.fresh = fresh
        self.hook = hook
        self.calls = 0

    def resolve_reader_profile(self, project: Path) -> dict:
        self.calls += 1
        if self.hook is not None:
            self.hook(self.calls)
        return deepcopy(self.fresh)

    def reader_profile_phase_state_binding(
        self, resolved: dict, resolved_path: Path, project: Path,
    ) -> dict:
        return {
            "binding_version": "2.0.0",
            "binding_kind": "reader_profile",
            "semantic_usage": "not_invoked",
            "profile_path": resolved["profile_path"],
            "profile_sha256": resolved["profile_sha256"],
            "resolved_path": resolved_path.relative_to(project).as_posix(),
            "resolved_sha256": hashlib.sha256(resolved_path.read_bytes()).hexdigest(),
            "source_bindings": deepcopy(resolved["source_bindings"]),
            "project_identity": None,
            "transitions": deepcopy(V2_BINDING["transitions"]),
        }


def _transaction_fixture(root: Path, name: str) -> dict:
    project = root / name
    resolved = project / "reviews/.harness/policies/reader_accessibility.resolved.json"
    state_path = project / "reviews/phase_state.json"
    resolved.parent.mkdir(parents=True)
    old_sources = [{
        "scope": "package", "path": "old", "sha256": "1" * 64,
        "role": "package_profile",
    }]
    old_payload = {
        "contract_version": "2.0.0",
        "binding_kind": "reader_profile",
        "semantic_usage": "not_invoked",
        "profile_path": "references/policies/reader_accessibility.v1.json",
        "profile_sha256": "1" * 64,
        "source_bindings": old_sources,
    }
    old_resolved = amt._json_bytes(old_payload)
    resolved.write_bytes(old_resolved)
    binding = deepcopy(V2_BINDING)
    binding.update({
        "profile_sha256": "1" * 64,
        "resolved_sha256": hashlib.sha256(old_resolved).hexdigest(),
        "source_bindings": old_sources,
    })
    framework = {
        "policy_bindings": {"reader_accessibility": binding},
        "milestones": {
            key: {"status": "not_started"} for key in ("M1", "M2", "M3", "M4", "M5")
        },
    }
    state = {"milestone_framework": framework}
    old_state = amt._json_bytes(state)
    state_path.write_bytes(old_state)
    fresh = {
        "contract_version": "2.0.0",
        "binding_kind": "reader_profile",
        "semantic_usage": "not_invoked",
        "profile_path": "references/policies/reader_accessibility.v1.json",
        "profile_sha256": "2" * 64,
        "source_bindings": [{
            "scope": "package", "path": "new", "sha256": "2" * 64,
            "role": "package_profile",
        }],
    }
    return {
        "project": project, "state_path": state_path, "state": state,
        "prehash": hashlib.sha256(old_state).hexdigest(), "framework": framework,
        "binding": binding, "resolved": resolved, "old_state": old_state,
        "old_resolved": old_resolved, "fresh": fresh,
    }


def _invoke(fx: dict, fake: _FakePolicy, validate_hook=None) -> Path:
    original_validate = amt.validate_document
    def validate(_project: Path, _proposed: dict) -> SimpleNamespace:
        if validate_hook is not None:
            validate_hook()
        return SimpleNamespace(findings=[])

    amt.validate_document = validate
    try:
        return amt._refresh_reader_profile_v2(
            fx["project"], fx["state_path"], fx["state"], fx["prehash"],
            fx["framework"], fx["binding"], "2026-08-07T00:00:00Z", fake,
        )
    finally:
        amt.validate_document = original_validate


def _refuses(project: Path, binding: dict, needle: str, label: str) -> None:
    try:
        amt._refresh_reader_profile_v2(
            project, project / "reviews/phase_state.json", {}, "0" * 64, {}, binding,
            "2026-08-07T00:00:00Z", policy,
        )
    except amt.MilestoneTransactionError as exc:
        assert needle in str(exc), f"{label}: expected {needle!r}, got {exc}"
        return
    raise AssertionError(f"{label}: refresh did not refuse")


def case_dispatch_order() -> None:
    """The v2 branch must sit after the open-round refusal, not beside legacy."""
    src = inspect.getsource(amt.rebind_reader_accessibility)
    round_at = src.index("_open_project_round")
    legacy_at = src.index("_activate_unavailable_reader_accessibility")
    v2_at = src.index("_refresh_reader_profile_v2")
    request_at = src.index("AMC-REPIN-REQUEST")
    assert legacy_at < round_at, "legacy migration is expected to return before the round check"
    assert round_at < v2_at, "v2 refresh must be gated by the open-round refusal"
    assert v2_at < request_at, "v2 refresh must pre-empt the semantic request path"


def case_open_round_predicate() -> None:
    """The approved gate: opening triggers only, read from per-section log tails."""
    opening = {
        "initial_dispatch",
        "ph3_iteration_round",
        "ph3_iteration_round_manuscript",
        "stability_mode_escalated_to_full_ph3",
    }
    src = inspect.getsource(policy._open_project_round)
    for trigger in opening:
        assert trigger in src, f"open-round predicate lost trigger {trigger}"
    assert "user_defer" not in src, "user_defer must not open a round"


def case_pin_fields_refused(tmp: Path) -> None:
    """A v2 binding carrying any semantic pin field is malformed, not refreshable."""
    for pin in ("attestation_view_pin", "exemplar_view_pin", "graph_sha256_provenance", "pin_epoch"):
        binding = dict(V2_BINDING)
        binding[pin] = "x"
        _refuses(tmp, binding, "carries semantic pin fields", f"pin/{pin}")


def case_malformed_binding_refused(tmp: Path) -> None:
    for key, value in (
        ("binding_version", "1.0.0"),
        ("binding_kind", "something_else"),
        ("semantic_usage", "invoked"),
        ("source_bindings", None),
        ("profile_path", ""),
        ("profile_path", 7),
        ("profile_sha256", None),
        ("resolved_sha256", None),
        ("transitions", None),
        ("transitions", {"G": {}, "H": {}}),
    ):
        binding = dict(V2_BINDING)
        binding[key] = value
        _refuses(tmp, binding, "v2 reader-profile binding is malformed", f"malformed/{key}={value!r}")

    # Both defects below passed the first cut's explicit pre-write shape check.
    # `profile_path` absent entirely is distinct from present-but-bad. An EXTRA
    # transition key is distinct from a missing one and is deep-copied into the
    # proposed binding, but the production canonical validator rejects X with
    # MF-STRUCTURE before authoritative phase-state publication and rollback
    # restores the preimages. The missing explicit checks were still real defects:
    # Step 1 required complete pre-write shape validation.
    binding = dict(V2_BINDING)
    del binding["profile_path"]
    _refuses(tmp, binding, "v2 reader-profile binding is malformed", "malformed/profile_path-absent")

    binding = dict(V2_BINDING)
    binding["transitions"] = dict(V2_BINDING["transitions"])
    binding["transitions"]["X"] = {
        "state": "active", "observed_count": 0, "last_event_sequence": None, "events": [],
    }
    _refuses(tmp, binding, "v2 reader-profile binding is malformed", "malformed/transitions-extra-X")


def case_artifact_guards(tmp: Path) -> None:
    """Path, hash, and artifact/binding agreement all fail closed before any write."""
    binding = dict(V2_BINDING)
    binding["resolved_path"] = 42
    _refuses(tmp, binding, "existing resolved policy path is invalid", "path/type")

    binding = dict(V2_BINDING)
    binding["resolved_path"] = "../escape.json"
    _refuses(tmp, binding, "escapes project root", "path/escape")

    binding = dict(V2_BINDING)
    _refuses(tmp, binding, "resolved policy path is absent or linked", "path/absent")

    resolved = tmp / "reviews/.harness/policies/reader_accessibility.resolved.json"
    resolved.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "contract_version": "2.0.0",
        "binding_kind": "reader_profile",
        "semantic_usage": "not_invoked",
        "source_bindings": [],
    }
    raw = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
    resolved.write_bytes(raw)

    binding = dict(V2_BINDING)
    _refuses(tmp, binding, "v2 resolver artifact hash is stale", "artifact/hash")

    binding = dict(V2_BINDING)
    binding["resolved_sha256"] = hashlib.sha256(raw).hexdigest()
    binding["source_bindings"] = [{"scope": "package", "path": "x", "sha256": "y", "role": "z"}]
    _refuses(tmp, binding, "v2 resolver artifact and binding disagree", "artifact/disagree")

    resolved.write_bytes(b"{not json")
    binding = dict(V2_BINDING)
    binding["resolved_sha256"] = hashlib.sha256(b"{not json").hexdigest()
    _refuses(tmp, binding, "v2 resolver artifact is invalid", "artifact/parse")


def case_no_delta_is_refusal() -> None:
    """A refresh that would change no byte must not write a receipt."""
    src = inspect.getsource(amt._refresh_reader_profile_v2)
    assert "AMC-REPIN-NO-DELTA" in src, "no-delta path is missing"
    assert src.index("AMC-REPIN-NO-DELTA") < src.index("_atomic_replace"), (
        "no-delta must be decided before the first write"
    )


def case_no_pin_or_ledger_write() -> None:
    """The refresh must never touch a pin, the graph, or the re-pin ledger."""
    src = inspect.getsource(amt._refresh_reader_profile_v2)
    for forbidden in ("repin_log", "resolve_policy(", "attestation_pin", "graph.json"):
        assert forbidden not in src, f"refresh must not reference {forbidden}"
    assert "resolve_reader_profile" in src, "refresh must resolve through the v2 route"
    assert 'binding["transitions"] = copy.deepcopy(old_binding["transitions"])' in src, (
        "transition history must be carried forward, not reset"
    )


def case_source_revalidation_precedes_receipt() -> None:
    """Profile/contributor drift after state publication must roll back before receipt."""
    src = inspect.getsource(amt._refresh_reader_profile_v2)
    state_publish = src.index("_atomic_replace(state_path, proposed)")
    second_resolve = src.index("post_resolved = policy.resolve_reader_profile(project)")
    receipt_publish = src.index("_exclusive_bytes(receipt")
    assert state_publish < second_resolve < receipt_publish
    assert "post_source_bindings_digest != current_source_bindings_digest" in src
    assert "AMC-CONCURRENT-CHANGE" in src[second_resolve:receipt_publish]
    assert "state_path.read_bytes() != state_post_bytes" in src[second_resolve:receipt_publish]


def case_accepted_evidence_refused_before_write() -> None:
    """A refresh cannot rewrite accepted policy evidence or immutable F9 history."""
    src = inspect.getsource(amt._refresh_reader_profile_v2)
    refusal = src.index("AMC-REPIN-ACCEPTED-EVIDENCE")
    first_write = src.index("_restore_exact_bytes(resolved_path, fresh_bytes)")
    assert refusal < first_write


def case_prewrite_drift_preserved(root: Path) -> None:
    fx = _transaction_fixture(root, "prewrite-drift")
    external = b'{"external":"state"}\n'
    fake = _FakePolicy(fx["fresh"], lambda call: fx["state_path"].write_bytes(external) if call == 1 else None)
    try:
        _invoke(fx, fake)
    except amt.MilestoneTransactionError as exc:
        assert exc.code == "AMC-CONCURRENT-CHANGE", exc
    else:
        raise AssertionError("prewrite drift did not refuse")
    assert fx["state_path"].read_bytes() == external
    assert fx["resolved"].read_bytes() == fx["old_resolved"]


def case_state_write_fault_rolls_back_own_postimage(root: Path) -> None:
    fx = _transaction_fixture(root, "state-write-fault")
    original = amt._atomic_replace

    def write_then_fail(path: Path, payload: dict) -> None:
        original(path, payload)
        raise OSError("injected state-write fault")

    amt._atomic_replace = write_then_fail
    try:
        try:
            _invoke(fx, _FakePolicy(fx["fresh"]))
        except OSError as exc:
            assert "injected" in str(exc)
        else:
            raise AssertionError("state-write fault did not propagate")
    finally:
        amt._atomic_replace = original
    assert fx["state_path"].read_bytes() == fx["old_state"]
    assert fx["resolved"].read_bytes() == fx["old_resolved"]


def case_late_prewrite_drift_preserved(root: Path) -> None:
    fx = _transaction_fixture(root, "late-prewrite-drift")
    external = b'{"external":"after-validation"}\n'

    def drift_after_validation() -> None:
        fx["state_path"].write_bytes(external)

    try:
        _invoke(fx, _FakePolicy(fx["fresh"]), validate_hook=drift_after_validation)
    except amt.MilestoneTransactionError as exc:
        assert exc.code == "AMC-CONCURRENT-CHANGE", exc
    else:
        raise AssertionError("late prewrite drift did not refuse")
    assert fx["state_path"].read_bytes() == external
    assert fx["resolved"].read_bytes() == fx["old_resolved"]


def case_postwrite_drift_is_preserved(root: Path) -> None:
    fx = _transaction_fixture(root, "postwrite-drift")
    external = b'{"external":"post-state"}\n'
    fake = _FakePolicy(fx["fresh"], lambda call: fx["state_path"].write_bytes(external) if call == 2 else None)
    try:
        _invoke(fx, fake)
    except amt.MilestoneTransactionError as exc:
        assert exc.code == "AMC-REPIN-RECOVERY-CONFLICT", exc
    else:
        raise AssertionError("postwrite drift did not refuse")
    assert fx["state_path"].read_bytes() == external
    assert fx["resolved"].read_bytes() == fx["old_resolved"]


def case_receipt_conflict_rolls_back_targets(root: Path) -> None:
    fx = _transaction_fixture(root, "receipt-conflict")
    original = amt._exclusive_bytes
    conflict = b'external receipt bytes\n'

    def conflict_receipt(path: Path, _data: bytes) -> bool:
        path.write_bytes(conflict)
        raise amt.MilestoneTransactionError("AMC-F9-CONFLICT", "injected receipt conflict")

    amt._exclusive_bytes = conflict_receipt
    try:
        try:
            _invoke(fx, _FakePolicy(fx["fresh"]))
        except amt.MilestoneTransactionError as exc:
            assert exc.code == "AMC-F9-CONFLICT", exc
        else:
            raise AssertionError("receipt conflict did not refuse")
    finally:
        amt._exclusive_bytes = original
    receipts = list((fx["project"] / "reviews").glob("reader-policy-refresh-*.applied.json"))
    assert len(receipts) == 1 and receipts[0].read_bytes() == conflict
    assert fx["state_path"].read_bytes() == fx["old_state"]
    assert fx["resolved"].read_bytes() == fx["old_resolved"]


def case_conditional_rollback_preserves_resolved_race(root: Path) -> None:
    fx = _transaction_fixture(root, "resolved-race")
    original = amt._atomic_replace
    external = b'{"external":"resolved"}\n'

    def race_then_fail(_path: Path, _payload: dict) -> None:
        fx["resolved"].write_bytes(external)
        raise OSError("injected resolved race")

    amt._atomic_replace = race_then_fail
    try:
        try:
            _invoke(fx, _FakePolicy(fx["fresh"]))
        except amt.MilestoneTransactionError as exc:
            assert exc.code == "AMC-REPIN-RECOVERY-CONFLICT", exc
        else:
            raise AssertionError("resolved race did not require recovery")
    finally:
        amt._atomic_replace = original
    assert fx["resolved"].read_bytes() == external
    assert fx["state_path"].read_bytes() == fx["old_state"]


def case_changed_source_success(root: Path) -> None:
    """The happy path, qualifiable on any host.

    The end-to-end success case lives in `assignment_milestone_checkpoint_smoketest`,
    which cannot run on Linux (`pdftotext.exe` pin). Without this case the ONLY
    executed paths here would be refusals and rollbacks -- a suite that proves the
    transaction never commits wrongly while proving nothing about it committing at
    all. Recorded 2026-08-07.
    """
    fx = _transaction_fixture(root, "changed-source-success")
    receipt = _invoke(fx, _FakePolicy(fx["fresh"]))

    assert receipt.is_file(), "refresh did not publish a receipt"
    assert receipt.name.startswith("reader-policy-refresh-"), receipt.name
    receipts = list((fx["project"] / "reviews").glob("reader-policy-refresh-*.applied.json"))
    assert len(receipts) == 1, f"expected exactly one refresh receipt, got {len(receipts)}"

    fresh_bytes = amt._json_bytes(fx["fresh"])
    assert fx["resolved"].read_bytes() == fresh_bytes, "resolver artifact was not replaced"
    assert fx["state_path"].read_bytes() != fx["old_state"], "phase state was not updated"

    published = json.loads(fx["state_path"].read_bytes())
    binding = published["milestone_framework"]["policy_bindings"]["reader_accessibility"]
    assert binding["binding_version"] == "2.0.0"
    assert binding["semantic_usage"] == "not_invoked"
    assert binding["profile_sha256"] == "2" * 64, "refreshed binding kept the stale profile hash"
    assert binding["resolved_sha256"] == hashlib.sha256(fresh_bytes).hexdigest()
    assert binding["source_bindings"] == fx["fresh"]["source_bindings"]
    assert binding["transitions"] == V2_BINDING["transitions"], "transition history was not carried"
    for pin in ("attestation_view_pin", "exemplar_view_pin", "graph_sha256_provenance", "pin_epoch"):
        assert pin not in binding, f"refreshed binding introduced {pin}"

    payload = json.loads(receipt.read_bytes())
    assert payload["schema_version"] == "2.0.0"
    assert payload["status"] == "applied"
    assert payload["applied_by"] == "planner"
    assert payload["prior"]["profile_sha256"] == "1" * 64
    assert payload["current"]["profile_sha256"] == "2" * 64
    assert payload["current"]["semantic_usage"] == "not_invoked"
    assert payload["prior"]["source_bindings_digest"] != payload["current"]["source_bindings_digest"]
    for side in ("prior", "current"):
        assert len(payload[side]["source_bindings_digest"]) == 64, side
    assert payload["phase_state"]["pre_sha256"] == fx["prehash"]
    assert payload["phase_state"]["post_sha256"] == hashlib.sha256(
        fx["state_path"].read_bytes()
    ).hexdigest(), "receipt post-hash does not match the published state"


def main() -> int:
    import tempfile

    case_dispatch_order()
    case_open_round_predicate()
    case_no_delta_is_refusal()
    case_no_pin_or_ledger_write()
    case_source_revalidation_precedes_receipt()
    case_accepted_evidence_refused_before_write()
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td).resolve()
        (tmp / "reviews").mkdir(parents=True, exist_ok=True)
        case_pin_fields_refused(tmp)
        case_malformed_binding_refused(tmp)
        case_artifact_guards(tmp)
        case_changed_source_success(tmp)
        case_prewrite_drift_preserved(tmp)
        case_state_write_fault_rolls_back_own_postimage(tmp)
        case_late_prewrite_drift_preserved(tmp)
        case_postwrite_drift_is_preserved(tmp)
        case_receipt_conflict_rolls_back_targets(tmp)
        case_conditional_rollback_preserves_resolved_race(tmp)
    print("OK reader_profile_refresh_smoketest (16 cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
