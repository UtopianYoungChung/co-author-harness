#!/usr/bin/env python3
"""C4 mutation-authority activation boundary over real assignment writes."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

import assignment_mutation_anchor as anchors
from assignment_c4_fixture_support import (
    DeterministicFixtureAdapter,
    exact_tree_state,
    fixture_manifest,
    issue_legacy_anchor,
)
from assignment_fixture_support import minimal_gate_project
from assignment_receipt_transaction import (
    ReceiptTransactionError,
    _assignment_root,
    _mutation_row_hash,
    _transaction_claim,
    commit_receipt,
    reserve_receipt,
)
from assignment_dispatch_claim import _publish_record
from destination_capability import DEST_PROTECTED, DestinationRefused


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "assignment_process_gate.py"
TARGET = "milestones/M1_project_memo.md"
FIXED_AT = "2026-07-25T13:00:00Z"


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(project: Path, path: Path) -> str:
    return path.resolve().relative_to(project.resolve()).as_posix()


def rebind_publication(project: Path, object_path: Path) -> None:
    """Refresh only derived publication hashes after a one-fact edit."""
    manifest_path = object_path.parent / "publication_manifest.json"
    marker_path = object_path.parent / "commit_marker.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    product_path = relative(project, object_path)
    product = next(row for row in manifest["products"] if row["path"] == product_path)
    product["sha256"] = sha(object_path)
    write_json(manifest_path, manifest)
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    marker["publication_manifest_sha256"] = sha(manifest_path)
    write_json(marker_path, marker)


def initialize_project(project: Path, initial: bytes) -> None:
    project.mkdir(parents=True)
    fixture_manifest(project)
    target = project / TARGET
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(initial)
    minimal_gate_project(project, target="M1")


def append_target(
    project: Path,
    value: bytes,
    label: str,
    *,
    fail_after_mutation_append: bool = False,
) -> dict[str, Path]:
    phase_state_path = project / "reviews" / "phase_state.json"
    phase_state = json.loads(phase_state_path.read_text(encoding="utf-8"))
    phase_state["synthetic_fixture_round"] = label
    write_json(phase_state_path, phase_state)
    ready = _assignment_root(project) / "ready" / f"gate_receipt_M1_{label}.json"
    gate = subprocess.run(
        [
            sys.executable,
            str(GATE),
            "--project-root",
            str(project),
            "--stage",
            "draft",
            "--target-milestone",
            "M1",
            "--emit-receipt",
            str(ready),
        ],
        text=True,
        encoding="utf-8",
        errors="strict",
        capture_output=True,
        check=False,
    )
    assert gate.returncode == 0, gate.stdout + gate.stderr
    receipt, reserved = reserve_receipt(project, ready, "M1", [TARGET])
    staged = _assignment_root(project) / "staged" / receipt["receipt_id"] / f"{label}.md"
    staged.parent.mkdir(parents=True, exist_ok=True)
    staged.write_bytes(value)
    plan = staged.parent / "write_plan.json"
    write_json(
        plan,
        {
            "schema_version": "1.0.0",
            "receipt_id": receipt["receipt_id"],
            "reservation_id": receipt["reservation_id"],
            "target_milestone": "M1",
            "role": "generator",
            "writes": [
                {
                    "staged_path": relative(project, staged),
                    "target_path": TARGET,
                    "sha256": sha(staged),
                }
            ],
        },
    )
    try:
        consumed, result = commit_receipt(
            project,
            reserved,
            plan,
            fail_after_mutation_append=fail_after_mutation_append,
        )
    except ReceiptTransactionError as exc:
        if not fail_after_mutation_append or exc.code != "APG-WRITE-PUBLISH-FAILED":
            raise
        consumed = _assignment_root(project) / "consumed" / reserved.name
        result = consumed.with_suffix(".result.json")
    return {
        "consumed": consumed,
        "result": result,
        "journal": _assignment_root(project) / "journal" / f"{receipt['receipt_id']}.json",
        "ledger": _assignment_root(project) / "mutation_ledger.jsonl",
    }


def publish_current_state(
    project: Path,
    *,
    authority_kind: str,
    authority_path: Path,
    authority_type: str,
    transaction_id: str,
) -> Path:
    with _transaction_claim(project):
        state = anchors._state_payload(
            project,
            authority_kind=authority_kind,
            authority_path=authority_path,
            authority_type=authority_type,
        )
        anchors._validate(
            state, anchors.STATE_SCHEMA, "APG-MUTATION-ANCHOR-INVALID"
        )
        lane = _assignment_root(project) / "mutation" / "states" / transaction_id
        state_path, _, _ = _publish_record(
            project, lane, "state.json", state, transaction_id
        )
    return state_path


def build_fresh(project: Path) -> dict[str, str]:
    initialize_project(project, b"fresh initial\n")
    genesis, genesis_path, _, initial_state = anchors.issue_genesis(
        project,
        initial_target_paths=[TARGET],
        policy_sha256="1" * 64,
        corpus_digest="2" * 64,
        issuer_transaction_id="fresh-genesis",
        nonce="3" * 32,
        issued_at=FIXED_AT,
    )
    tx = append_target(project, b"fresh committed\n", "fresh")
    current_state = publish_current_state(
        project,
        authority_kind="genesis",
        authority_path=genesis_path,
        authority_type="assignment_mutation_genesis",
        transaction_id="fresh-current",
    )
    anchors.validate_accepted_prefix(project, current_state)
    anchors.validate_live_head(project, current_state)
    return {
        "genesis": relative(project, genesis_path),
        "initial_state": relative(project, initial_state),
        "current_state": relative(project, current_state),
        "journal": relative(project, tx["journal"]),
        "ledger": relative(project, tx["ledger"]),
    }


def build_legacy(project: Path) -> dict[str, str]:
    initialize_project(project, b"legacy initial\n")
    first = append_target(project, b"legacy anchored\n", "legacy_a")
    authorization = project / "reviews/.harness/fixture_authorization.json"
    write_json(
        authorization,
        {
            "synthetic": True,
            "scope": "local C4 mutation anchor fixture",
            "production_authority": False,
        },
    )
    _, anchor_path, _ = issue_legacy_anchor(
        project,
        ledger_path=first["ledger"],
        live_target_paths=[TARGET],
        authorization_path=authorization,
        nonce="4" * 32,
        issued_at="2026-07-25T13:01:00Z",
    )
    adapter = DeterministicFixtureAdapter()
    anchors.inspect_legacy_anchor(project, anchor_path, fixture_adapter=adapter)
    _, accepted_state = anchors.activate_legacy_anchor(
        project,
        anchor_path,
        fixture_adapter=adapter,
        transaction_id="legacy-activation",
    )
    second = append_target(project, b"legacy later append\n", "legacy_b")
    current_state = publish_current_state(
        project,
        authority_kind="legacy_anchor",
        authority_path=anchor_path,
        authority_type="assignment_mutation_legacy_anchor",
        transaction_id="legacy-current",
    )
    # An accepted prefix remains valid after a later legitimate append.
    anchors.validate_accepted_prefix(project, accepted_state)
    anchors.validate_live_head(project, current_state)
    return {
        "anchor": relative(project, anchor_path),
        "accepted_state": relative(project, accepted_state),
        "current_state": relative(project, current_state),
        "first_journal": relative(project, first["journal"]),
        "second_journal": relative(project, second["journal"]),
        "ledger": relative(project, second["ledger"]),
    }


def build_partial_append(project: Path) -> dict[str, str]:
    initialize_project(project, b"partial initial\n")
    _, genesis_path, _, initial_state = anchors.issue_genesis(
        project,
        initial_target_paths=[TARGET],
        policy_sha256="6" * 64,
        corpus_digest="7" * 64,
        issuer_transaction_id="partial-genesis",
        nonce="8" * 32,
        issued_at="2026-07-25T13:05:00Z",
    )
    tx = append_target(
        project,
        b"partial published target\n",
        "partial",
        fail_after_mutation_append=True,
    )
    journal = json.loads(tx["journal"].read_text(encoding="utf-8"))
    append_state = journal["mutation_append"]
    rows = [
        json.loads(line)
        for line in tx["ledger"].read_text(encoding="utf-8").splitlines()
    ]
    assert append_state["state"] == "ledger_appended"
    assert append_state["prior_row_count"] == 0
    assert append_state["prior_head"] is None
    assert append_state["prospective_row_count"] == 1
    assert append_state["prospective_rows"] == rows
    assert append_state["prospective_head"] == rows[-1]["row_sha256"]
    assert append_state["ledger_sha256"] == sha(tx["ledger"])
    assert append_state["targets"] == [
        {"path": TARGET, "sha256": sha(project / TARGET)}
    ]
    assert not (
        _assignment_root(project)
        / "mutation"
        / "append"
        / journal["receipt_id"]
        / "commit_marker.json"
    ).exists()
    return {
        "genesis": relative(project, genesis_path),
        "state": relative(project, initial_state),
        "journal": relative(project, tx["journal"]),
        "ledger": relative(project, tx["ledger"]),
    }


def clone_control(source: Path, base: Path, name: str) -> Path:
    destination = base / name / "project"
    shutil.copytree(source, destination)
    return destination


def expect_future_refusal(
    project: Path,
    code: str,
    call: Callable[[], Any],
    intended_red: list[str],
) -> None:
    before = exact_tree_state(project)
    try:
        call()
    except ReceiptTransactionError as exc:
        if exc.code != code:
            intended_red.append(f"{code}: current activation returned {exc.code}")
        elif exact_tree_state(project) != before:
            raise AssertionError(f"{code}: refusal changed synthetic project state")
        return
    intended_red.append(
        f"{code}: current activation consumer returned success; "
        f"state_changed={exact_tree_state(project) != before}"
    )


def resign_anchor(path: Path, mutate: Callable[[dict[str, Any]], None]) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    mutate(payload)
    unsigned = {key: value for key, value in payload.items() if key != "authenticator"}
    payload["authenticator"] = {
        "kind": "mac",
        "digest": DeterministicFixtureAdapter().digest(unsigned),
    }
    write_json(path, payload)


def recompute_chain(path: Path) -> None:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    rows[0]["receipt_id"] = "receipt-rewritten"
    prior: str | None = None
    for sequence, row in enumerate(rows, 1):
        row["sequence"] = sequence
        row["prior_row_sha256"] = prior
        row["row_sha256"] = _mutation_row_hash(row)
        prior = row["row_sha256"]
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="c4-mutation-") as temporary:
        root = Path(temporary)
        fresh_control = root / "fresh-control" / "project"
        legacy_control = root / "legacy-control" / "project"
        partial_control = root / "partial-control" / "project"
        fresh = build_fresh(fresh_control)
        legacy = build_legacy(legacy_control)
        partial = build_partial_append(partial_control)
        intended_red: list[str] = []
        adapter = DeterministicFixtureAdapter()

        project = clone_control(legacy_control, root, "missing")
        expect_future_refusal(
            project,
            "APG-MUTATION-ANCHOR-MISSING",
            lambda: anchors.inspect_legacy_anchor(project, None, fixture_adapter=adapter),
            intended_red,
        )

        project = clone_control(legacy_control, root, "malformed")
        anchor = project / legacy["anchor"]
        payload = json.loads(anchor.read_text(encoding="utf-8"))
        del payload["authorization"]
        write_json(anchor, payload)
        expect_future_refusal(
            project,
            "APG-MUTATION-ANCHOR-INVALID",
            lambda: anchors.inspect_legacy_anchor(project, anchor, fixture_adapter=adapter),
            intended_red,
        )

        project = clone_control(legacy_control, root, "unknown_issuer")
        anchor = project / legacy["anchor"]
        payload = json.loads(anchor.read_text(encoding="utf-8"))
        payload["adapter"]["issuer"] = "unavailable_fixture_authority"
        write_json(anchor, payload)
        rebind_publication(project, anchor)
        expect_future_refusal(
            project,
            "APG-MUTATION-ANCHOR-UNAUTHORIZED",
            lambda: anchors.inspect_legacy_anchor(project, anchor, fixture_adapter=adapter),
            intended_red,
        )

        project = clone_control(legacy_control, root, "bad_authenticator")
        anchor = project / legacy["anchor"]
        payload = json.loads(anchor.read_text(encoding="utf-8"))
        payload["authenticator"]["digest"] = "0" * 64
        write_json(anchor, payload)
        rebind_publication(project, anchor)
        expect_future_refusal(
            project,
            "APG-MUTATION-ANCHOR-UNAUTHORIZED",
            lambda: anchors.inspect_legacy_anchor(project, anchor, fixture_adapter=adapter),
            intended_red,
        )

        project = clone_control(legacy_control, root, "binding")
        anchor = project / legacy["anchor"]
        resign_anchor(anchor, lambda value: value["project"].update({"manifest_sha256": "5" * 64}))
        rebind_publication(project, anchor)
        expect_future_refusal(
            project,
            "APG-MUTATION-ANCHOR-INVALID",
            lambda: anchors.inspect_legacy_anchor(project, anchor, fixture_adapter=adapter),
            intended_red,
        )

        project = clone_control(legacy_control, root, "overclaim")
        anchor = project / legacy["anchor"]
        resign_anchor(anchor, lambda value: value.update({"historical_provenance_asserted": True}))
        rebind_publication(project, anchor)
        expect_future_refusal(
            project,
            "APG-MUTATION-LEGACY-PROVENANCE-OVERCLAIM",
            lambda: anchors.inspect_legacy_anchor(project, anchor, fixture_adapter=adapter),
            intended_red,
        )

        project = clone_control(legacy_control, root, "replay")
        anchor = project / legacy["anchor"]
        expect_future_refusal(
            project,
            "APG-MUTATION-ANCHOR-UNAUTHORIZED",
            lambda: anchors.activate_legacy_anchor(
                project,
                anchor,
                fixture_adapter=adapter,
                transaction_id="legacy-replay",
            ),
            intended_red,
        )

        project = clone_control(legacy_control, root, "truncated")
        ledger = project / legacy["ledger"]
        ledger.write_bytes(b"")
        expect_future_refusal(
            project,
            "APG-MUTATION-PREFIX-MISMATCH",
            lambda: anchors.validate_accepted_prefix(project, project / legacy["accepted_state"]),
            intended_red,
        )

        project = clone_control(legacy_control, root, "rewritten")
        recompute_chain(project / legacy["ledger"])
        expect_future_refusal(
            project,
            "APG-MUTATION-PREFIX-MISMATCH",
            lambda: anchors.validate_accepted_prefix(project, project / legacy["accepted_state"]),
            intended_red,
        )

        project = clone_control(legacy_control, root, "row_rewrite")
        ledger = project / legacy["ledger"]
        rows = ledger.read_text(encoding="utf-8").splitlines()
        first = json.loads(rows[0])
        first["receipt_id"] = "receipt-unrecomputed"
        rows[0] = json.dumps(first, sort_keys=True)
        ledger.write_text("\n".join(rows) + "\n", encoding="utf-8")
        expect_future_refusal(
            project,
            "APG-MUTATION-PREFIX-MISMATCH",
            lambda: anchors.validate_accepted_prefix(project, project / legacy["accepted_state"]),
            intended_red,
        )

        project = clone_control(legacy_control, root, "stale_head")
        expect_future_refusal(
            project,
            "APG-MUTATION-HEAD-STALE",
            lambda: anchors.validate_live_head(project, project / legacy["accepted_state"]),
            intended_red,
        )

        project = clone_control(fresh_control, root, "live_target")
        (project / TARGET).write_bytes(b"changed outside assignment transaction\n")
        expect_future_refusal(
            project,
            "APG-MUTATION-HEAD-STALE",
            lambda: anchors.validate_live_head(project, project / fresh["current_state"]),
            intended_red,
        )

        project = clone_control(partial_control, root, "append_incomplete")
        expect_future_refusal(
            project,
            "APG-MUTATION-APPEND-INCOMPLETE",
            lambda: anchors.validate_live_head(project, project / partial["state"]),
            intended_red,
        )

        project = clone_control(partial_control, root, "recovery_required")
        (project / TARGET).write_bytes(b"divergent partial target\n")
        expect_future_refusal(
            project,
            "APG-MUTATION-RECOVERY-REQUIRED",
            lambda: anchors.validate_live_head(project, project / partial["state"]),
            intended_red,
        )

        project = clone_control(fresh_control, root, "protected_destination")
        governance = root / "governance" / "output-routing" / "output_routing.yaml"
        governance.parent.mkdir(parents=True, exist_ok=True)
        governance.write_text("schema_version: 1.0.0\n", encoding="utf-8")
        before = exact_tree_state(project)
        try:
            anchors.issue_genesis(
                project,
                initial_target_paths=[TARGET],
                policy_sha256="1" * 64,
                corpus_digest="2" * 64,
                issuer_transaction_id="protected-destination",
                nonce="3" * 32,
                issued_at="2026-07-25T13:30:00Z",
            )
        except DestinationRefused as exc:
            assert exc.code == DEST_PROTECTED
        else:
            raise AssertionError("protected mutation destination was accepted")
        assert exact_tree_state(project) == before

        if intended_red:
            raise AssertionError(
                "C4 intended-red mutation boundary:\n  " + "\n  ".join(intended_red)
            )
    print("assignment_mutation_anchor_smoketest: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
