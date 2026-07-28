#!/usr/bin/env python3
"""C4 dispatch-claim and host-independence activation boundary."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft202012Validator, FormatChecker

import assignment_dispatch_claim as claims
import draft_evidence_verifier as verifier
from assignment_c4_fixture_support import (
    DeterministicFixtureAdapter,
    exact_tree_state,
    issue_host_attestation,
)
from assignment_fixture_support import minimal_gate_project
from assignment_receipt_transaction import (
    ReceiptTransactionError,
    _assignment_root,
    commit_receipt,
    reserve_receipt,
)
from c2_evidence_fixture_support import build_activation_fixture
from destination_capability import DEST_PROTECTED, DestinationRefused


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "assignment_process_gate.py"
SEMANTICS = ROOT / "references" / "semantics_manifest.v1.json"
TARGET = "milestones/M1_project_memo.md"
FIXED_AT = "2026-07-25T12:00:00Z"
CLAIM_SCHEMA = (
    ROOT / "references" / "schemas" / "assignment_dispatch_claim.schema.json"
)
ISSUANCE_SCHEMA = (
    ROOT / "references" / "schemas" / "assignment_dispatch_issuance.schema.json"
)
COMMON_SCHEMA = (
    ROOT / "references" / "schemas" / "common_scholarly_primitives.schema.json"
)


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(project: Path, path: Path) -> str:
    return path.resolve().relative_to(project.resolve()).as_posix()


def write_fixture_semantics_manifest(path: Path) -> None:
    """Pin current owned validator bytes without editing the governed manifest."""
    value = json.loads(
        (ROOT / "references" / "semantics_manifest.v1.json").read_text(
            encoding="utf-8"
        )
    )
    refreshed = {
        "references/schemas/assignment_dispatch_claim.schema.json",
        "references/schemas/assignment_dispatch_issuance.schema.json",
        "scripts/assignment_dispatch_claim.py",
        "scripts/assignment_receipt_transaction.py",
    }
    members = {row["path"]: row for row in value["members"]}
    for member_path in refreshed:
        members[member_path]["sha256"] = sha(ROOT / member_path)
    write_json(path, value)


def rebind_publication(
    project: Path,
    object_path: Path,
    *,
    transaction_id: str | None = None,
) -> None:
    """Refresh only derived publication hashes after a one-fact edit."""
    manifest_path = object_path.parent / "publication_manifest.json"
    marker_path = object_path.parent / "commit_marker.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if transaction_id is not None:
        manifest["transaction_id"] = transaction_id
    product_path = relative(project, object_path)
    product = next(row for row in manifest["products"] if row["path"] == product_path)
    product["sha256"] = sha(object_path)
    write_json(manifest_path, manifest)
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    if transaction_id is not None:
        marker["transaction_id"] = transaction_id
    marker["publication_manifest_sha256"] = sha(manifest_path)
    write_json(marker_path, marker)


def republish_issuance_chain(
    project: Path,
    rows: list[dict[str, Any]],
) -> None:
    """Recompute a synthetic ledger chain and all deterministic prefix markers."""
    prior = None
    for sequence, row in enumerate(rows, 1):
        row["sequence"] = sequence
        row["prior_row_sha256"] = prior
        row["row_sha256"] = claims._issuance_row_hash(row)
        prior = row["row_sha256"]
    root = claims._issuance_root(project)
    ledger = root / "ledger.jsonl"
    ledger.write_bytes(b"".join(canonical_bytes(row) for row in rows))
    marker_root = root / "markers"
    if marker_root.is_dir():
        shutil.rmtree(marker_root)
    prefix = b""
    prior = None
    for row in rows:
        prefix += canonical_bytes(row)
        marker = {
            "schema_version": "1.0.0",
            "marker_type": "assignment_dispatch_issuance",
            "state": "committed",
            "sequence": row["sequence"],
            "row_count": row["sequence"],
            "prior_head_row_sha256": prior,
            "head_row_sha256": row["row_sha256"],
            "ledger_path": relative(project, ledger),
            "ledger_prefix_sha256": hashlib.sha256(prefix).hexdigest(),
            "transaction_id": row["issuer"]["transaction_id"],
        }
        write_json(claims._issuance_marker_path(project, row), marker)
        prior = row["row_sha256"]


def append_role_authored_issuance(
    project: Path,
    claim: dict[str, Any],
    claim_path: Path,
    *,
    copied_authorization: dict[str, Any] | None = None,
) -> None:
    """Manufacture a fully consistent issuance row without calling the kernel."""
    rows = claims._load_issuance_ledger(project)
    if copied_authorization is None:
        authorization_id = "00000000-0000-4000-8000-000000000000"
        authorization_path = (
            _assignment_root(project)
            / "dispatch"
            / "kernel_authorizations"
            / authorization_id
            / "authorization.json"
        )
        authorization_binding = claims.binding_from_digest(
            project,
            authorization_path,
            "0" * 64,
            "assignment_dispatch_kernel_authorization",
        )
    else:
        authorization_id = copied_authorization["authorization_id"]
        authorization_binding = copied_authorization["kernel_authorization"]
    row: dict[str, Any] = {
        "schema_version": "1.0.0",
        "issuance_type": "assignment_dispatch_claim",
        "sequence": len(rows) + 1,
        "prior_row_sha256": rows[-1]["row_sha256"] if rows else None,
        "claim": claims.binding(project, claim_path, "assignment_dispatch_claim"),
        "claim_id": claim["claim_id"],
        "claim_sha256": sha(claim_path),
        "claim_kind": claim["claim_kind"],
        "receipt_id": claim["receipt_id"],
        "reservation_id": claim["reservation_id"],
        "issuer": claim["issuer"],
        "issued_at": claim["issued_at"],
        "publication_manifest": claims.binding(
            project,
            claim_path.parent / "publication_manifest.json",
            "assignment_dispatch_claim_manifest",
        ),
        "commit_marker": claims.binding(
            project,
            claim_path.parent / "commit_marker.json",
            "assignment_dispatch_claim_marker",
        ),
        "kernel_authorization": authorization_binding,
        "authorization_id": authorization_id,
    }
    row["row_sha256"] = claims._issuance_row_hash(row)
    rows.append(row)
    republish_issuance_chain(project, rows)


def resign_fixture_record(
    project: Path,
    path: Path,
    mutation: Callable[[dict[str, Any]], None],
) -> None:
    from assignment_c4_fixture_support import DeterministicFixtureAdapter

    value = json.loads(path.read_text(encoding="utf-8"))
    mutation(value)
    unsigned = {key: item for key, item in value.items() if key != "authenticator"}
    value["authenticator"] = {
        "kind": "mac",
        "digest": DeterministicFixtureAdapter().digest(unsigned),
    }
    write_json(path, value)
    rebind_publication(project, path)


def rebind_verifier_publication(
    project: Path,
    transaction_path: Path,
    manifest_path: Path,
    marker_path: Path,
) -> None:
    transaction = json.loads(transaction_path.read_text(encoding="utf-8"))
    product_path = project / transaction["product_assurance"]["path"]
    transaction["product_assurance"]["sha256"] = sha(product_path)
    if "phase" in transaction:
        transaction_seed = {
            "artifact": transaction["artifact"]["sha256"],
            "semantic_receipt": transaction["semantic_receipt"]["sha256"],
            "semantics_digest": transaction["semantics_digest"],
            "phase": transaction["phase"],
            "requested_independence_level": transaction[
                "requested_independence_level"
            ],
            "out_dir": transaction_path.parent.relative_to(project).as_posix(),
        }
        transaction["transaction_id"] = (
            "verifier-"
            + hashlib.sha256(canonical_bytes(transaction_seed)).hexdigest()[:16]
        )
    write_json(transaction_path, transaction)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["transaction_id"] = transaction["transaction_id"]
    transaction_relative = relative(project, transaction_path)
    product_relative = relative(project, product_path)
    for row in manifest["intended_outputs"]:
        if row["path"] == transaction_relative:
            row["sha256"] = sha(transaction_path)
        elif row["path"] == product_relative:
            row["sha256"] = sha(product_path)
    write_json(manifest_path, manifest)
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    marker["transaction_id"] = transaction["transaction_id"]
    manifest_relative = relative(project, manifest_path)
    marker["manifest"]["sha256"] = sha(manifest_path)
    for row in marker["final_output_hashes"]:
        if row["path"] == transaction_relative:
            row["sha256"] = sha(transaction_path)
        elif row["path"] == product_relative:
            row["sha256"] = sha(product_path)
        elif row["path"] == manifest_relative:
            row["sha256"] = sha(manifest_path)
    write_json(marker_path, marker)


def build_control(project: Path) -> dict[str, Any]:
    activation = build_activation_fixture(project, artifact_relative=TARGET)
    shutil.copyfile(activation.project_manifest, project / "project_manifest.json")
    minimal_gate_project(project, target="M1")
    ready = (
        project
        / "reviews/.harness/assignment/ready/gate_receipt_M1_c4.json"
    )
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
    generation_claim, generation_claim_path, generation_claim_marker = (
        claims.issue_generation_claim(
            project,
            reserved,
            policy_path=activation.wiki_root / "policy.json",
            bibliography_snapshot=activation.bibliography_snapshot,
            nonce="1" * 32,
            issuer_transaction_id="assignment-reserve-M1",
            issued_at=FIXED_AT,
        )
    )
    recovery_claim, recovery_claim_path, _ = claims.issue_generation_claim(
        project,
        reserved,
        policy_path=activation.wiki_root / "policy.json",
        bibliography_snapshot=activation.bibliography_snapshot,
        nonce="9" * 32,
        issuer_transaction_id="assignment-recovery-M1",
        issued_at="2026-07-25T12:00:30Z",
    )

    staged = (
        project
        / "reviews/.harness/assignment/staged"
        / receipt["receipt_id"]
        / "M1_project_memo.md"
    )
    staged.parent.mkdir(parents=True, exist_ok=True)
    staged.write_bytes(activation.artifact.read_bytes())
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
    consumed_receipt, _result = commit_receipt(project, reserved, plan)
    _, generation_host_path, _ = issue_host_attestation(
        project,
        claim_path=generation_claim_path,
        target=TARGET,
        artifact=activation.artifact,
        role="generator",
        host_task_id="fixture-generation-task",
        host_session_id="fixture-generation-session",
        nonce="3" * 32,
        issued_at="2026-07-25T12:00:35Z",
    )
    generation_consumption, generation_consumption_path, _ = (
        claims.consume_dispatch_claim(
            project,
            generation_claim_path,
            role="generator",
            consumer_transaction_id="assignment-write-M1",
            target_paths=[TARGET],
            consumed_at="2026-07-25T12:00:45Z",
        )
    )

    verifier_paths = verifier.publish_verifier_transaction(
        artifact=activation.artifact,
        semantic_receipt=activation.receipt,
        phase="generation",
        project_root=project,
        wiki_root=activation.wiki_root,
        harness_root=ROOT,
        semantics_manifest=SEMANTICS,
        out_dir=project / "reviews/.harness/verifier/generation",
        requested_independence_level="none",
    )
    verifier.validate_verifier_transaction(
        transaction=verifier_paths["transaction"],
        publication_manifest=verifier_paths["publication_manifest"],
        commit_marker=verifier_paths["commit_marker"],
        artifact=activation.artifact,
        semantic_receipt=activation.receipt,
        project_root=project,
        wiki_root=activation.wiki_root,
        harness_root=ROOT,
        semantics_manifest=SEMANTICS,
    )
    evaluation_semantic = (
        project / "reviews/.harness/verifier/evaluation-phase-semantic.json"
    )
    evaluation_semantic_value = json.loads(
        activation.receipt.read_text(encoding="utf-8")
    )
    evaluation_semantic_value["phase"] = "evaluation"
    evaluation_semantic_value["role"] = "evaluator"
    write_json(evaluation_semantic, evaluation_semantic_value)
    evaluation_phase_paths = verifier.publish_verifier_transaction(
        artifact=activation.artifact,
        semantic_receipt=evaluation_semantic,
        phase="evaluation",
        project_root=project,
        wiki_root=activation.wiki_root,
        harness_root=ROOT,
        semantics_manifest=SEMANTICS,
        out_dir=project / "reviews/.harness/verifier/evaluation-phase-control",
        requested_independence_level="none",
    )
    verifier.validate_verifier_transaction(
        transaction=evaluation_phase_paths["transaction"],
        publication_manifest=evaluation_phase_paths["publication_manifest"],
        commit_marker=evaluation_phase_paths["commit_marker"],
        artifact=activation.artifact,
        semantic_receipt=evaluation_semantic,
        project_root=project,
        wiki_root=activation.wiki_root,
        harness_root=ROOT,
        semantics_manifest=SEMANTICS,
    )
    evaluation_claim, evaluation_claim_path, evaluation_claim_marker = (
        claims.issue_evaluation_claim(
            project,
            generation_claim_path,
            generation_consumption=generation_consumption_path,
            artifact=activation.artifact,
            generation_transaction=verifier_paths["transaction"],
            generation_publication_manifest=verifier_paths["publication_manifest"],
            generation_commit_marker=verifier_paths["commit_marker"],
            generation_semantic_receipt=activation.receipt,
            wiki_root=activation.wiki_root,
            semantics_manifest=SEMANTICS,
            nonce="2" * 32,
            issuer_transaction_id="assignment-evaluation-M1",
            issued_at="2026-07-25T12:01:00Z",
        )
    )
    _, evaluation_host_path, _ = issue_host_attestation(
        project,
        claim_path=evaluation_claim_path,
        target=TARGET,
        artifact=activation.artifact,
        role="evaluator",
        host_task_id="fixture-evaluation-task",
        host_session_id="fixture-evaluation-session",
        nonce="4" * 32,
        issued_at="2026-07-25T12:01:30Z",
        generation_verifier=verifier_paths["transaction"],
    )
    evaluation_consumption, evaluation_consumption_path, _ = (
        claims.consume_dispatch_claim(
            project,
            evaluation_claim_path,
            role="evaluator",
            consumer_transaction_id="evaluation-M1",
            target_paths=[TARGET],
            consumed_at="2026-07-25T12:01:45Z",
        )
    )

    accepted_generation = claims.accept_claim_for_context(
        project,
        generation_claim_path,
        expected_role="generator",
        expected_target=TARGET,
        expected_receipt_id=receipt["receipt_id"],
        expected_preimages=generation_claim["authorized_writes"],
        expected_policy_sha256=generation_claim["policy"]["sha256"],
        expected_corpus_digest=generation_claim["corpus_digest"],
    )
    accepted_evaluation = claims.accept_claim_for_context(
        project,
        evaluation_claim_path,
        expected_role="evaluator",
        expected_target=TARGET,
        expected_receipt_id=receipt["receipt_id"],
        expected_artifact_sha256=sha(activation.artifact),
        expected_generation_transaction_id=verifier_paths["transaction_id"],
    )
    independence = claims.accept_host_pair_for_independence(
        project,
        generation_host_path,
        evaluation_host_path,
        requested_level="host_attested_independence",
        expected_generation_claim_id=generation_claim["claim_id"],
        expected_evaluation_claim_id=evaluation_claim["claim_id"],
        _test_only_adapter=DeterministicFixtureAdapter(),
    )
    host_uses = list(
        (_assignment_root(project) / "dispatch" / "host-uses").glob("*/use.json")
    )
    assert len(host_uses) == 1
    host_use_path = host_uses[0]
    host_use_marker = host_use_path.parent / "commit_marker.json"
    assert host_use_marker.is_file()
    assert accepted_generation["claim_id"] == generation_claim["claim_id"]
    assert accepted_evaluation["claim_id"] == evaluation_claim["claim_id"]
    assert independence == "host_attested_independence"
    assert generation_consumption["claim_id"] == generation_claim["claim_id"]
    assert evaluation_consumption["claim_id"] == evaluation_claim["claim_id"]

    return {
        "target": TARGET,
        "artifact": relative(project, activation.artifact),
        "policy": relative(project, activation.wiki_root / "policy.json")
        if (activation.wiki_root / "policy.json").is_relative_to(project)
        else str((activation.wiki_root / "policy.json").resolve()),
        "bibliography": relative(project, activation.bibliography_snapshot),
        "consumed_receipt": relative(project, consumed_receipt),
        "receipt_id": receipt["receipt_id"],
        "generation_claim": relative(project, generation_claim_path),
        "recovery_claim": relative(project, recovery_claim_path),
        "generation_claim_marker": relative(project, generation_claim_marker),
        "generation_consumption": relative(project, generation_consumption_path),
        "evaluation_claim": relative(project, evaluation_claim_path),
        "evaluation_claim_marker": relative(project, evaluation_claim_marker),
        "evaluation_consumption": relative(project, evaluation_consumption_path),
        "host_use": relative(project, host_use_path),
        "host_use_marker": relative(project, host_use_marker),
        "generation_host": relative(project, generation_host_path),
        "evaluation_host": relative(project, evaluation_host_path),
        "generation_transaction": relative(project, verifier_paths["transaction"]),
        "generation_manifest": relative(project, verifier_paths["publication_manifest"]),
        "generation_marker": relative(project, verifier_paths["commit_marker"]),
        "evaluation_phase_transaction": relative(
            project, evaluation_phase_paths["transaction"]
        ),
        "evaluation_phase_manifest": relative(
            project, evaluation_phase_paths["publication_manifest"]
        ),
        "evaluation_phase_marker": relative(
            project, evaluation_phase_paths["commit_marker"]
        ),
        "evaluation_phase_semantic": relative(project, evaluation_semantic),
        "semantic_receipt": relative(project, activation.receipt),
        "wiki_root": str(activation.wiki_root.resolve()),
        "generation_claim_value": generation_claim,
        "recovery_claim_value": recovery_claim,
        "evaluation_claim_value": evaluation_claim,
    }


def clone_control(source: Path, base: Path, name: str) -> Path:
    project = base / name / source.name
    project.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, project)
    return project


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
        after = exact_tree_state(project)
        if exc.code == code and after == before:
            return
        intended_red.append(
            f"{code}: current refusal was {exc.code}; state_unchanged={after == before}"
        )
    else:
        intended_red.append(
            f"{code}: current activation consumer returned success; "
            f"state_changed={exact_tree_state(project) != before}"
        )


def pre_refactor_schema(path: Path) -> dict[str, Any]:
    """Reconstruct the exact local primitives replaced by the common schema."""

    schema = json.loads(path.read_text(encoding="utf-8"))
    old_sha = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
    old_timestamp = {
        "type": "string",
        "pattern": (
            "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:"
            "[0-9]{2}(\\.[0-9]+)?Z$"
        ),
    }
    old_safe_path = {
        "type": "string",
        "minLength": 1,
        "pattern": "^(?!/)(?!.*(?:^|/)\\.\\.(?:/|$))(?!.*[\\\\:]).+$",
    }
    old_root = {
        "type": "object",
        "additionalProperties": False,
        "required": ["kind", "identity", "discovery", "manifest_sha256"],
        "properties": {
            "kind": {"enum": ["project", "harness", "wiki"]},
            "identity": {"type": "string", "minLength": 1},
            "discovery": {"type": "string", "minLength": 1},
            "manifest_sha256": {"$ref": "#/$defs/sha256"},
        },
    }
    old_binding = {
        "type": "object",
        "additionalProperties": False,
        "required": ["root", "path", "sha256", "evidence_type"],
        "properties": {
            "root": {"$ref": "#/$defs/root"},
            "path": {"$ref": "#/$defs/safePath"},
            "sha256": {"$ref": "#/$defs/sha256"},
            "evidence_type": {"type": "string", "minLength": 1},
        },
    }
    schema["$defs"].update(
        {
            "sha256": old_sha,
            "timestamp": old_timestamp,
            "safePath": old_safe_path,
            "root": old_root,
            "binding": old_binding,
        }
    )
    if path == CLAIM_SCHEMA:
        schema["$defs"]["generationVerifier"].pop("allOf")
    else:
        schema.pop("allOf")
        schema["properties"]["sequence"] = {"type": "integer", "minimum": 1}
        schema["properties"]["prior_row_sha256"] = {
            "oneOf": [{"$ref": "#/$defs/sha256"}, {"type": "null"}]
        }
        schema["properties"]["row_sha256"] = {"$ref": "#/$defs/sha256"}
    return schema


def schema_accepts(validator: Draft202012Validator, value: dict[str, Any]) -> bool:
    return not any(validator.iter_errors(value))


def expect_schema_refusal(code: str, call: Callable[[], Any]) -> None:
    try:
        call()
    except ReceiptTransactionError as exc:
        assert exc.code == code, exc
    else:
        raise AssertionError(f"expected {code}")


def main() -> int:
    global SEMANTICS
    with tempfile.TemporaryDirectory(
        prefix="assignment-dispatch-semantics-", dir=ROOT
    ) as semantics_td, tempfile.TemporaryDirectory(
        prefix="assignment-dispatch-c4-"
    ) as td:
        SEMANTICS = Path(semantics_td) / "semantics-manifest.json"
        write_fixture_semantics_manifest(SEMANTICS)
        base = Path(td)
        control = base / "control" / "project"
        facts = build_control(control)
        intended_red: list[str] = []
        fixture_adapter = DeterministicFixtureAdapter()
        issuance_rows = claims._load_issuance_ledger(control)
        assert [row["claim_kind"] for row in issuance_rows] == [
            "generation", "generation", "evaluation"
        ]
        assert {row["claim_id"] for row in issuance_rows} == {
            facts["generation_claim_value"]["claim_id"],
            facts["recovery_claim_value"]["claim_id"],
            facts["evaluation_claim_value"]["claim_id"],
        }
        assert len({row["authorization_id"] for row in issuance_rows}) == 3
        for row in issuance_rows:
            authorization_path = control / row["kernel_authorization"]["path"]
            assert authorization_path.is_file()
            assert sha(authorization_path) == row["kernel_authorization"]["sha256"]

        old_claim_validator = Draft202012Validator(
            pre_refactor_schema(CLAIM_SCHEMA), format_checker=FormatChecker()
        )
        old_issuance_validator = Draft202012Validator(
            pre_refactor_schema(ISSUANCE_SCHEMA), format_checker=FormatChecker()
        )
        new_claim_validator = claims._validator(
            CLAIM_SCHEMA, "APG-DISPATCH-CLAIM-INVALID"
        )
        new_issuance_validator = claims._validator(
            ISSUANCE_SCHEMA, "APG-DISPATCH-CLAIM-AUTHORITY"
        )
        invalid_timestamp = copy.deepcopy(facts["generation_claim_value"])
        invalid_timestamp["issued_at"] = "not-a-timestamp"
        legacy_shape_timestamp = copy.deepcopy(facts["generation_claim_value"])
        legacy_shape_timestamp["issued_at"] = "2026-99-99T99:99:99Z"
        invalid_sha = copy.deepcopy(facts["generation_claim_value"])
        invalid_sha["corpus_digest"] = "0" * 63
        invalid_path = copy.deepcopy(facts["generation_claim_value"])
        invalid_path["target_path"] = "C:forbidden.md"
        invalid_root = copy.deepcopy(facts["generation_claim_value"])
        invalid_root["assignment_receipt"]["root"]["kind"] = "consumer"
        invalid_extra = copy.deepcopy(facts["generation_claim_value"])
        invalid_extra["unexpected"] = True
        incomplete_chain = copy.deepcopy(facts["evaluation_claim_value"])
        del incomplete_chain["generation_verifier"]["publication_manifest"]
        claim_vectors = [
            facts["generation_claim_value"],
            facts["evaluation_claim_value"],
            invalid_timestamp,
            legacy_shape_timestamp,
            invalid_sha,
            invalid_path,
            invalid_root,
            invalid_extra,
            incomplete_chain,
        ]
        invalid_sequence = copy.deepcopy(issuance_rows[0])
        invalid_sequence["sequence"] = 0
        invalid_prior = copy.deepcopy(issuance_rows[1])
        invalid_prior["prior_row_sha256"] = "0" * 63
        invalid_row_hash = copy.deepcopy(issuance_rows[0])
        invalid_row_hash["row_sha256"] = "A" * 64
        invalid_binding_path = copy.deepcopy(issuance_rows[0])
        invalid_binding_path["claim"]["path"] = "C:forbidden.json"
        invalid_binding_root = copy.deepcopy(issuance_rows[0])
        invalid_binding_root["claim"]["root"]["kind"] = "consumer"
        invalid_issuance_extra = copy.deepcopy(issuance_rows[0])
        invalid_issuance_extra["unexpected"] = True
        issuance_vectors = issuance_rows + [
            invalid_sequence,
            invalid_prior,
            invalid_row_hash,
            invalid_binding_path,
            invalid_binding_root,
            invalid_issuance_extra,
        ]
        for label, old_validator, new_validator, vectors in (
            ("claim", old_claim_validator, new_claim_validator, claim_vectors),
            (
                "issuance",
                old_issuance_validator,
                new_issuance_validator,
                issuance_vectors,
            ),
        ):
            for index, vector in enumerate(vectors):
                before = canonical_bytes(vector)
                old_accepts = schema_accepts(old_validator, vector)
                new_accepts = schema_accepts(new_validator, vector)
                assert old_accepts == new_accepts, (
                    label,
                    index,
                    old_accepts,
                    new_accepts,
                )
                if old_accepts:
                    assert canonical_bytes(vector) == before

        schema_attacks = base / "schema-attacks"
        common_value = json.loads(COMMON_SCHEMA.read_text(encoding="utf-8"))
        expect_schema_refusal(
            "APG-DISPATCH-CLAIM-INVALID",
            lambda: claims._validator(
                CLAIM_SCHEMA,
                "APG-DISPATCH-CLAIM-INVALID",
                common_schema_path=schema_attacks / "missing-common.json",
            ),
        )
        invalid_common = schema_attacks / "invalid-common.json"
        invalid_common.parent.mkdir(parents=True, exist_ok=True)
        invalid_common.write_bytes(b"{")
        expect_schema_refusal(
            "APG-DISPATCH-CLAIM-INVALID",
            lambda: claims._validator(
                CLAIM_SCHEMA,
                "APG-DISPATCH-CLAIM-INVALID",
                common_schema_path=invalid_common,
            ),
        )
        wrong_id = copy.deepcopy(common_value)
        wrong_id["$id"] = "https://example.invalid/common.json"
        wrong_id_path = schema_attacks / "wrong-id.json"
        write_json(wrong_id_path, wrong_id)
        expect_schema_refusal(
            "APG-DISPATCH-CLAIM-AUTHORITY",
            lambda: claims._validator(
                ISSUANCE_SCHEMA,
                "APG-DISPATCH-CLAIM-AUTHORITY",
                common_schema_path=wrong_id_path,
            ),
        )
        same_id_different_bytes = copy.deepcopy(common_value)
        same_id_different_bytes["$comment"] = "same id, synthetic foreign bytes"
        wrong_hash_path = schema_attacks / "same-id-different-bytes.json"
        write_json(wrong_hash_path, same_id_different_bytes)
        expect_schema_refusal(
            "APG-DISPATCH-CLAIM-INVALID",
            lambda: claims._validator(
                CLAIM_SCHEMA,
                "APG-DISPATCH-CLAIM-INVALID",
                common_schema_path=wrong_hash_path,
            ),
        )
        invalid_dispatch_schema = schema_attacks / "invalid-dispatch.schema.json"
        write_json(invalid_dispatch_schema, {"type": 7})
        expect_schema_refusal(
            "APG-DISPATCH-CLAIM-AUTHORITY",
            lambda: claims._validator(
                invalid_dispatch_schema, "APG-DISPATCH-CLAIM-AUTHORITY"
            ),
        )
        unresolved = json.loads(CLAIM_SCHEMA.read_text(encoding="utf-8"))
        unresolved_text = json.dumps(unresolved).replace(
            claims.COMMON_SCHEMA_ID,
            "https://co-author-harness.local/schemas/missing-common.json",
        )
        unresolved_path = schema_attacks / "unresolved-claim.schema.json"
        write_json(unresolved_path, json.loads(unresolved_text))
        expect_schema_refusal(
            "APG-DISPATCH-CLAIM-INVALID",
            lambda: claims._validate_schema(
                facts["generation_claim_value"],
                unresolved_path,
                "APG-DISPATCH-CLAIM-INVALID",
            ),
        )

        def claim_case(name: str, *, evaluation: bool = False) -> tuple[Path, Path]:
            project = clone_control(control, base / "cases", name)
            key = "evaluation_claim" if evaluation else "generation_claim"
            return project, project / facts[key]

        # QG-1 executable red: deterministic claim bytes plus the canonical
        # object/manifest/marker publication are not issuance authority.  This
        # forged claim keeps every live binding and an allowed transaction id,
        # recomputes its identifier, and occupies its derived canonical lane,
        # but no assignment-kernel issuance record exists for it.
        project, _path = claim_case("missing_issuance_row")
        forged = copy.deepcopy(facts["generation_claim_value"])
        forged["issued_at"] = "2026-07-25T12:00:01Z"
        unsigned = {key: value for key, value in forged.items() if key != "claim_id"}
        forged["claim_id"] = "dispatch-" + hashlib.sha256(
            json.dumps(
                unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
        ).hexdigest()[:16]
        forged_lane = (
            _assignment_root(project)
            / "dispatch"
            / "claims"
            / forged["claim_id"]
        )
        forged_path, _forged_manifest, forged_marker = claims._publish_record(
            project,
            forged_lane,
            "claim.json",
            forged,
            "assignment-reserve-M1",
        )
        assert forged_marker.is_file()
        expect_future_refusal(
            project,
            "APG-DISPATCH-CLAIM-AUTHORITY",
            lambda: claims.accept_claim_for_context(
                project,
                forged_path,
                expected_role="generator",
                expected_target=TARGET,
                expected_receipt_id=facts["receipt_id"],
                expected_preimages=forged["authorized_writes"],
                expected_policy_sha256=forged["policy"]["sha256"],
                expected_corpus_digest=forged["corpus_digest"],
            ),
            intended_red,
        )

        # Stronger QG-1 boundary: the role also manufactures the complete,
        # internally consistent deterministic issuance journal and marker.
        project, _path = claim_case("coordinated_role_authored_issuance")
        coordinated = copy.deepcopy(facts["generation_claim_value"])
        coordinated["issued_at"] = "2026-07-25T12:00:03Z"
        unsigned = {
            key: value for key, value in coordinated.items()
            if key != "claim_id"
        }
        coordinated["claim_id"] = "dispatch-" + hashlib.sha256(
            json.dumps(
                unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
        ).hexdigest()[:16]
        coordinated_lane = (
            _assignment_root(project)
            / "dispatch"
            / "claims"
            / coordinated["claim_id"]
        )
        coordinated_path, _, coordinated_marker = claims._publish_record(
            project,
            coordinated_lane,
            "claim.json",
            coordinated,
            "assignment-reserve-M1",
        )
        assert coordinated_marker.is_file()
        append_role_authored_issuance(project, coordinated, coordinated_path)
        expect_future_refusal(
            project,
            "APG-DISPATCH-CLAIM-AUTHORITY",
            lambda: claims.accept_claim_for_context(
                project,
                coordinated_path,
                expected_role="generator",
                expected_target=TARGET,
                expected_receipt_id=facts["receipt_id"],
                expected_preimages=coordinated["authorized_writes"],
                expected_policy_sha256=coordinated["policy"]["sha256"],
                expected_corpus_digest=coordinated["corpus_digest"],
            ),
            intended_red,
        )

        project, path = claim_case("generation_authorization_absent")
        rows = claims._load_issuance_ledger(project)
        generation_row = next(
            row for row in rows
            if row["claim_id"] == facts["generation_claim_value"]["claim_id"]
        )
        (project / generation_row["kernel_authorization"]["path"]).unlink()
        expect_future_refusal(
            project,
            "APG-DISPATCH-CLAIM-AUTHORITY",
            lambda: claims.accept_claim_for_context(
                project,
                path,
                expected_role="generator",
                expected_target=TARGET,
                expected_receipt_id=facts["receipt_id"],
            ),
            intended_red,
        )

        project, path = claim_case("evaluation_authorization_absent", evaluation=True)
        rows = claims._load_issuance_ledger(project)
        evaluation_row = next(
            row for row in rows
            if row["claim_id"] == facts["evaluation_claim_value"]["claim_id"]
        )
        (project / evaluation_row["kernel_authorization"]["path"]).unlink()
        expect_future_refusal(
            project,
            "APG-DISPATCH-CLAIM-AUTHORITY",
            lambda: claims.accept_claim_for_context(
                project,
                path,
                expected_role="evaluator",
                expected_target=TARGET,
                expected_receipt_id=facts["receipt_id"],
                expected_artifact_sha256=facts["evaluation_claim_value"]["artifact"]["sha256"],
                expected_generation_transaction_id=(
                    facts["evaluation_claim_value"]["generation_verifier"]["transaction_id"]
                ),
            ),
            intended_red,
        )

        project, path = claim_case("kernel_authorization_rewritten")
        rows = claims._load_issuance_ledger(project)
        row_index = next(
            index for index, row in enumerate(rows)
            if row["claim_id"] == facts["generation_claim_value"]["claim_id"]
        )
        authorization_path = project / rows[row_index]["kernel_authorization"]["path"]
        authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
        authorization["claim"]["sha256"] = "0" * 64
        write_json(authorization_path, authorization)
        rows[row_index]["kernel_authorization"] = claims.binding(
            project,
            authorization_path,
            "assignment_dispatch_kernel_authorization",
        )
        republish_issuance_chain(project, rows)
        expect_future_refusal(
            project,
            "APG-DISPATCH-CLAIM-AUTHORITY",
            lambda: claims.accept_claim_for_context(
                project,
                path,
                expected_role="generator",
                expected_target=TARGET,
                expected_receipt_id=facts["receipt_id"],
            ),
            intended_red,
        )

        project, _path = claim_case("kernel_authorization_copied")
        copied = copy.deepcopy(facts["generation_claim_value"])
        copied["issued_at"] = "2026-07-25T12:00:04Z"
        unsigned = {key: value for key, value in copied.items() if key != "claim_id"}
        copied["claim_id"] = "dispatch-" + hashlib.sha256(
            json.dumps(
                unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
        ).hexdigest()[:16]
        copied_lane = (
            _assignment_root(project) / "dispatch" / "claims" / copied["claim_id"]
        )
        copied_path, _, copied_marker = claims._publish_record(
            project,
            copied_lane,
            "claim.json",
            copied,
            "assignment-reserve-M1",
        )
        assert copied_marker.is_file()
        rows = claims._load_issuance_ledger(project)
        original_row = next(
            row for row in rows
            if row["claim_id"] == facts["generation_claim_value"]["claim_id"]
        )
        append_role_authored_issuance(
            project,
            copied,
            copied_path,
            copied_authorization=original_row,
        )
        expect_future_refusal(
            project,
            "APG-DISPATCH-CLAIM-AUTHORITY",
            lambda: claims.accept_claim_for_context(
                project,
                copied_path,
                expected_role="generator",
                expected_target=TARGET,
                expected_receipt_id=facts["receipt_id"],
                expected_preimages=copied["authorized_writes"],
                expected_policy_sha256=copied["policy"]["sha256"],
                expected_corpus_digest=copied["corpus_digest"],
            ),
            intended_red,
        )

        project, _path = claim_case("missing_evaluation_issuance_row", evaluation=True)
        forged_evaluation = copy.deepcopy(facts["evaluation_claim_value"])
        forged_evaluation["issued_at"] = "2026-07-25T12:01:01Z"
        unsigned = {
            key: value for key, value in forged_evaluation.items()
            if key != "claim_id"
        }
        forged_evaluation["claim_id"] = "dispatch-" + hashlib.sha256(
            json.dumps(
                unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
        ).hexdigest()[:16]
        forged_lane = (
            _assignment_root(project)
            / "dispatch"
            / "claims"
            / forged_evaluation["claim_id"]
        )
        forged_evaluation_path, _, forged_evaluation_marker = claims._publish_record(
            project,
            forged_lane,
            "claim.json",
            forged_evaluation,
            "assignment-evaluation-M1",
        )
        assert forged_evaluation_marker.is_file()
        expect_future_refusal(
            project,
            "APG-DISPATCH-CLAIM-AUTHORITY",
            lambda: claims.accept_claim_for_context(
                project,
                forged_evaluation_path,
                expected_role="evaluator",
                expected_target=TARGET,
                expected_receipt_id=facts["receipt_id"],
                expected_artifact_sha256=forged_evaluation["artifact"]["sha256"],
                expected_generation_transaction_id=(
                    forged_evaluation["generation_verifier"]["transaction_id"]
                ),
            ),
            intended_red,
        )

        project, path = claim_case("issuance_marker_missing", evaluation=True)
        rows = claims._load_issuance_ledger(project)
        claims._issuance_marker_path(project, rows[-1]).unlink()
        expect_future_refusal(
            project,
            "APG-DISPATCH-CLAIM-AUTHORITY",
            lambda: claims.accept_claim_for_context(
                project,
                path,
                expected_role="evaluator",
                expected_target=TARGET,
                expected_receipt_id=facts["receipt_id"],
                expected_artifact_sha256=facts["evaluation_claim_value"]["artifact"]["sha256"],
                expected_generation_transaction_id=(
                    facts["evaluation_claim_value"]["generation_verifier"]["transaction_id"]
                ),
            ),
            intended_red,
        )

        project, path = claim_case("issuance_reordered")
        ledger = claims._issuance_root(project) / "ledger.jsonl"
        lines = ledger.read_bytes().splitlines(keepends=True)
        ledger.write_bytes(lines[1] + lines[0] + b"".join(lines[2:]))
        expect_future_refusal(
            project,
            "APG-DISPATCH-CLAIM-AUTHORITY",
            lambda: claims.accept_claim_for_context(
                project,
                path,
                expected_role="generator",
                expected_target=TARGET,
                expected_receipt_id=facts["receipt_id"],
            ),
            intended_red,
        )

        project, path = claim_case("issuance_rewritten")
        rewritten = claims._load_issuance_ledger(project)
        rewritten[0]["issued_at"] = "2026-07-25T12:00:02Z"
        republish_issuance_chain(project, rewritten)
        expect_future_refusal(
            project,
            "APG-DISPATCH-CLAIM-AUTHORITY",
            lambda: claims.accept_claim_for_context(
                project,
                path,
                expected_role="generator",
                expected_target=TARGET,
                expected_receipt_id=facts["receipt_id"],
            ),
            intended_red,
        )

        project, path = claim_case("malformed")
        malformed = project / "reviews/.harness/assignment/dispatch/malformed.json"
        write_json(malformed, {})
        expect_future_refusal(
            project,
            "APG-DISPATCH-CLAIM-INVALID",
            lambda: claims.accept_claim_for_context(
                project, malformed, expected_role="generator", expected_target=TARGET,
                expected_receipt_id=facts["receipt_id"]
            ),
            intended_red,
        )

        project, path = claim_case("coordinated_authority")
        value = json.loads(path.read_text(encoding="utf-8"))
        value["issuer"]["transaction_id"] = "role-authored-coordinated"
        write_json(path, value)
        rebind_publication(
            project, path, transaction_id="role-authored-coordinated"
        )
        expect_future_refusal(
            project,
            "APG-DISPATCH-CLAIM-AUTHORITY",
            lambda: claims.accept_claim_for_context(
                project, path, expected_role="generator", expected_target=TARGET,
                expected_receipt_id=facts["receipt_id"]
            ),
            intended_red,
        )

        project, path = claim_case("recomputed_claim_id")
        value = json.loads(path.read_text(encoding="utf-8"))
        value["issued_at"] = "2026-07-25T12:00:01Z"
        unsigned = {key: item for key, item in value.items() if key != "claim_id"}
        value["claim_id"] = "dispatch-" + hashlib.sha256(
            json.dumps(
                unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
        ).hexdigest()[:16]
        write_json(path, value)
        rebind_publication(project, path)
        expect_future_refusal(
            project,
            "APG-DISPATCH-CLAIM-AUTHORITY",
            lambda: claims.accept_claim_for_context(
                project, path, expected_role="generator", expected_target=TARGET,
                expected_receipt_id=facts["receipt_id"]
            ),
            intended_red,
        )

        project, path = claim_case("authority")
        value = json.loads(path.read_text(encoding="utf-8"))
        value["issuer"]["transaction_id"] = "role-authored"
        write_json(path, value)
        rebind_publication(project, path)
        expect_future_refusal(
            project,
            "APG-DISPATCH-CLAIM-AUTHORITY",
            lambda: claims.accept_claim_for_context(
                project, path, expected_role="generator", expected_target=TARGET,
                expected_receipt_id=facts["receipt_id"]
            ),
            intended_red,
        )

        project, _ = claim_case("missing")
        expect_future_refusal(
            project,
            "APG-DISPATCH-CLAIM-MISSING",
            lambda: claims.accept_claim_for_context(
                project, None, expected_role="generator", expected_target=TARGET,
                expected_receipt_id=facts["receipt_id"]
            ),
            intended_red,
        )

        project, path = claim_case("uncommitted")
        uncommitted = project / "uncommitted-claim.json"
        shutil.copyfile(path, uncommitted)
        expect_future_refusal(
            project,
            "APG-DISPATCH-CLAIM-UNCOMMITTED",
            lambda: claims.accept_claim_for_context(
                project, uncommitted, expected_role="generator", expected_target=TARGET,
                expected_receipt_id=facts["receipt_id"]
            ),
            intended_red,
        )

        mismatch_rows = [
            ("role", "APG-DISPATCH-CLAIM-ROLE-MISMATCH", {"expected_role": "evaluator"}),
            ("target", "APG-DISPATCH-CLAIM-TARGET-MISMATCH", {"expected_target": "other.md"}),
            ("receipt", "APG-DISPATCH-CLAIM-RECEIPT-MISMATCH", {"expected_receipt_id": "00000000-0000-0000-0000-000000000000"}),
            ("preimage", "APG-DISPATCH-CLAIM-PREIMAGE-MISMATCH", {"expected_preimages": []}),
            ("policy", "APG-DISPATCH-CLAIM-POLICY-MISMATCH", {"expected_policy_sha256": "0" * 64}),
            ("corpus", "APG-DISPATCH-CLAIM-CORPUS-MISMATCH", {"expected_corpus_digest": "0" * 64}),
        ]
        for name, code, override in mismatch_rows:
            project, path = claim_case(name)
            kwargs = {
                "expected_role": "generator",
                "expected_target": TARGET,
                "expected_receipt_id": facts["receipt_id"],
                "expected_preimages": facts["generation_claim_value"]["authorized_writes"],
                "expected_policy_sha256": facts["generation_claim_value"]["policy"]["sha256"],
                "expected_corpus_digest": facts["generation_claim_value"]["corpus_digest"],
            }
            kwargs.update(override)
            expect_future_refusal(
                project,
                code,
                lambda project=project, path=path, kwargs=kwargs:
                    claims.accept_claim_for_context(project, path, **kwargs),
                intended_red,
            )

        for name, code, override in (
            ("artifact", "APG-DISPATCH-CLAIM-ARTIFACT-MISMATCH", {"expected_artifact_sha256": "0" * 64}),
            ("generation", "APG-DISPATCH-CLAIM-GENERATION-MISMATCH", {"expected_generation_transaction_id": "verifier-0000000000000000"}),
        ):
            project, path = claim_case(name, evaluation=True)
            kwargs = {
                "expected_role": "evaluator",
                "expected_target": TARGET,
                "expected_receipt_id": facts["receipt_id"],
                "expected_artifact_sha256": facts["evaluation_claim_value"]["artifact"]["sha256"],
                "expected_generation_transaction_id": facts["evaluation_claim_value"]["generation_verifier"]["transaction_id"],
            }
            kwargs.update(override)
            expect_future_refusal(
                project,
                code,
                lambda project=project, path=path, kwargs=kwargs:
                    claims.accept_claim_for_context(project, path, **kwargs),
                intended_red,
            )

        def evaluation_issue_case(name: str) -> tuple[Path, dict[str, Path]]:
            project = clone_control(control, base / "evaluation-issue-cases", name)
            return project, {
                "claim": project / facts["generation_claim"],
                "consumption": project / facts["generation_consumption"],
                "artifact": project / facts["artifact"],
                "transaction": project / facts["generation_transaction"],
                "manifest": project / facts["generation_manifest"],
                "marker": project / facts["generation_marker"],
                "semantic": project / facts["semantic_receipt"],
            }

        for index, (name, code) in enumerate((
            ("malformed_generation", "APG-DISPATCH-CLAIM-GENERATION-MISMATCH"),
            ("stale_artifact", "APG-DISPATCH-CLAIM-GENERATION-MISMATCH"),
            ("wrong_phase", "APG-DISPATCH-CLAIM-GENERATION-MISMATCH"),
            ("wrong_disposition", "APG-DISPATCH-CLAIM-GENERATION-MISMATCH"),
            ("uncommitted_generation", "APG-DISPATCH-CLAIM-UNCOMMITTED"),
            ("missing_consumption", "APG-DISPATCH-CLAIM-GENERATION-MISMATCH"),
            ("incomplete_consumption", "APG-DISPATCH-CLAIM-GENERATION-MISMATCH"),
            ("mismatched_consumption", "APG-DISPATCH-CLAIM-GENERATION-MISMATCH"),
        ), 1):
            project, paths = evaluation_issue_case(name)
            if name == "malformed_generation":
                value = json.loads(paths["transaction"].read_text(encoding="utf-8"))
                del value["phase"]
                write_json(paths["transaction"], value)
                rebind_verifier_publication(project, paths["transaction"], paths["manifest"], paths["marker"])
            elif name == "stale_artifact":
                paths["artifact"].write_bytes(b"stale generation artifact\n")
            elif name == "wrong_phase":
                paths["transaction"] = project / facts["evaluation_phase_transaction"]
                paths["manifest"] = project / facts["evaluation_phase_manifest"]
                paths["marker"] = project / facts["evaluation_phase_marker"]
                paths["semantic"] = project / facts["evaluation_phase_semantic"]
            elif name == "wrong_disposition":
                value = json.loads(paths["transaction"].read_text(encoding="utf-8"))
                value["product_disposition"] = "product_qualified"
                write_json(paths["transaction"], value)
                product = paths["transaction"].parent / "product-assurance.json"
                value = json.loads(product.read_text(encoding="utf-8"))
                value["product_disposition"] = "product_qualified"
                write_json(product, value)
                rebind_verifier_publication(project, paths["transaction"], paths["manifest"], paths["marker"])
            elif name == "missing_consumption":
                paths["claim"] = project / facts["recovery_claim"]
                paths["consumption"] = None
            elif name == "incomplete_consumption":
                paths["claim"] = project / facts["recovery_claim"]
                _, partial_path, partial_marker = claims.consume_dispatch_claim(
                    project,
                    paths["claim"],
                    role="generator",
                    consumer_transaction_id="evaluation-issue-incomplete-consumption",
                    target_paths=[TARGET],
                    consumed_at="2026-07-25T12:20:00Z",
                    stop_before_marker=True,
                )
                assert partial_path.is_file()
                assert not partial_marker.exists()
                paths["consumption"] = partial_path
            elif name == "mismatched_consumption":
                paths["consumption"] = project / facts["evaluation_consumption"]
            else:
                value = json.loads(paths["marker"].read_text(encoding="utf-8"))
                value["state"] = "prepared"
                write_json(paths["marker"], value)
            expect_future_refusal(
                project,
                code,
                lambda project=project, paths=paths, index=index: claims.issue_evaluation_claim(
                    project,
                    paths["claim"],
                    generation_consumption=paths["consumption"],
                    artifact=paths["artifact"],
                    generation_transaction=paths["transaction"],
                    generation_publication_manifest=paths["manifest"],
                    generation_commit_marker=paths["marker"],
                    generation_semantic_receipt=paths["semantic"],
                    wiki_root=Path(facts["wiki_root"]),
                    semantics_manifest=SEMANTICS,
                    nonce=f"{index + 10:x}" * 32,
                    issuer_transaction_id="assignment-evaluation-M1",
                    issued_at=f"2026-07-25T12:{10 + index:02d}:00Z",
                ),
                intended_red,
            )

        project, _ = claim_case("duplicate")
        consumed_receipt = project / facts["consumed_receipt"]
        policy = ROOT / "scripts/fixtures/assurance_provenance_c2/wiki/policy.json"
        bibliography = project / facts["bibliography"]
        expect_future_refusal(
            project,
            "APG-DISPATCH-CLAIM-DUPLICATE",
            lambda: claims.issue_generation_claim(
                project,
                consumed_receipt,
                policy_path=policy,
                bibliography_snapshot=bibliography,
                nonce="1" * 32,
                issuer_transaction_id="assignment-reserve-M1",
                issued_at="2026-07-25T12:00:01Z",
            ),
            intended_red,
        )

        project, path = claim_case("replay", evaluation=True)
        expect_future_refusal(
            project,
            "APG-DISPATCH-CLAIM-REPLAY",
            lambda: claims.consume_dispatch_claim(
                project,
                path,
                role="evaluator",
                consumer_transaction_id="evaluation-M1-replay",
                target_paths=[TARGET],
            ),
            intended_red,
        )

        project, _ = claim_case("recovery")
        path = project / facts["recovery_claim"]
        partial_consumption, partial_path, partial_marker = claims.consume_dispatch_claim(
            project,
            path,
            role="generator",
            consumer_transaction_id="generation-recovery-M1",
            target_paths=[TARGET],
            consumed_at="2026-07-25T12:04:00Z",
            stop_before_marker=True,
        )
        assert partial_consumption["claim_id"] == facts["recovery_claim_value"]["claim_id"]
        assert partial_consumption["claim"]["path"] == relative(project, path)
        assert partial_consumption["claim"]["sha256"] == sha(path)
        assert partial_path.is_file()
        assert partial_path.parent.joinpath("publication_manifest.json").is_file()
        assert not partial_marker.exists()
        expect_future_refusal(
            project,
            "APG-DISPATCH-CLAIM-RECOVERY-REQUIRED",
            lambda: claims.consume_dispatch_claim(
                project,
                path,
                role="generator",
                consumer_transaction_id="generation-recovery-M1",
                target_paths=[TARGET],
                consumed_at="2026-07-25T12:04:00Z",
            ),
            intended_red,
        )
        recovered, recovered_path, recovered_marker = claims.consume_dispatch_claim(
            project,
            path,
            role="generator",
            consumer_transaction_id="generation-recovery-M1",
            target_paths=[TARGET],
            consumed_at="2026-07-25T12:04:00Z",
            resume_incomplete=True,
        )
        assert recovered == partial_consumption
        assert recovered_path == partial_path
        assert recovered_marker.is_file()
        expect_future_refusal(
            project,
            "APG-DISPATCH-CLAIM-REPLAY",
            lambda: claims.consume_dispatch_claim(
                project,
                path,
                role="generator",
                consumer_transaction_id="generation-recovery-M1",
                target_paths=[TARGET],
                consumed_at="2026-07-25T12:04:00Z",
            ),
            intended_red,
        )

        project, _ = claim_case("concurrent_consumption")
        concurrent_claim = project / facts["recovery_claim"]
        barrier = threading.Barrier(2)

        def concurrent_consume(index: int) -> str:
            barrier.wait()
            try:
                claims.consume_dispatch_claim(
                    project,
                    concurrent_claim,
                    role="generator",
                    consumer_transaction_id=f"concurrent-consumer-{index}",
                    target_paths=[TARGET],
                    consumed_at=f"2026-07-25T12:05:0{index}Z",
                )
                return "success"
            except ReceiptTransactionError as exc:
                return exc.code

        with ThreadPoolExecutor(max_workers=2) as executor:
            concurrent_results = sorted(executor.map(concurrent_consume, (1, 2)))
        assert concurrent_results.count("success") == 1
        assert concurrent_results[1 if concurrent_results[0] == "success" else 0] in {
            "APG-RECEIPT-BUSY",
            "APG-RECEIPT-IN-USE",
            "APG-DISPATCH-CLAIM-REPLAY",
        }, concurrent_results

        def host_case(name: str) -> tuple[Path, Path, Path]:
            project = clone_control(control, base / "host-cases", name)
            return (
                project,
                project / facts["generation_host"],
                project / facts["evaluation_host"],
            )

        project, generation_host, evaluation_host = host_case("issuer")
        resign_fixture_record(
            project,
            evaluation_host,
            lambda value: value["issuer"].update({"name": "unlisted_fixture"}),
        )
        expect_future_refusal(
            project,
            "HOST-ATTESTATION-ISSUER-UNTRUSTED",
            lambda: claims.accept_host_pair_for_independence(
                project, generation_host, evaluation_host,
                requested_level="host_attested_independence",
                expected_generation_claim_id=facts["generation_claim_value"]["claim_id"],
                expected_evaluation_claim_id=facts["evaluation_claim_value"]["claim_id"],
                _test_only_adapter=fixture_adapter,
            ),
            intended_red,
        )

        for name, mutation in (
            ("invalid", lambda value: value["authenticator"].update({"digest": "0" * 64})),
            ("binding", lambda value: value.update({"host_session_id": "fixture-generation-session"})),
        ):
            project, generation_host, evaluation_host = host_case(name)
            if name == "binding":
                resign_fixture_record(project, evaluation_host, mutation)
            else:
                value = json.loads(evaluation_host.read_text(encoding="utf-8"))
                mutation(value)
                write_json(evaluation_host, value)
                rebind_publication(project, evaluation_host)
            code = (
                "HOST-ATTESTATION-INVALID"
                if name == "invalid"
                else "HOST-ATTESTATION-BINDING-MISMATCH"
            )
            expect_future_refusal(
                project,
                code,
                lambda project=project, generation_host=generation_host,
                evaluation_host=evaluation_host: claims.accept_host_pair_for_independence(
                    project, generation_host, evaluation_host,
                    requested_level="host_attested_independence",
                    expected_generation_claim_id=facts["generation_claim_value"]["claim_id"],
                    expected_evaluation_claim_id=facts["evaluation_claim_value"]["claim_id"],
                    _test_only_adapter=fixture_adapter,
                ),
                intended_red,
            )

        for name, mutation in (
            ("claim_binding", lambda value: value["dispatch_claim"].update({"sha256": "0" * 64})),
            ("target_binding", lambda value: value.update({"target": "other.md"})),
            ("artifact_binding", lambda value: value["artifact"].update({"sha256": "0" * 64})),
            ("generation_binding", lambda value: value["generation_verifier"].update({"sha256": "0" * 64})),
            ("nonce_binding", lambda value: value.update({"nonce": "3" * 32})),
        ):
            project, generation_host, evaluation_host = host_case(name)
            resign_fixture_record(project, evaluation_host, mutation)
            expect_future_refusal(
                project,
                "HOST-ATTESTATION-BINDING-MISMATCH",
                lambda project=project, generation_host=generation_host,
                evaluation_host=evaluation_host: claims.accept_host_pair_for_independence(
                    project,
                    generation_host,
                    evaluation_host,
                    requested_level="host_attested_independence",
                    expected_generation_claim_id=facts["generation_claim_value"]["claim_id"],
                    expected_evaluation_claim_id=facts["evaluation_claim_value"]["claim_id"],
                    _test_only_adapter=fixture_adapter,
                ),
                intended_red,
            )

        project, generation_host, evaluation_host = host_case("role_binding")
        expect_future_refusal(
            project,
            "HOST-ATTESTATION-BINDING-MISMATCH",
            lambda: claims.accept_host_pair_for_independence(
                project,
                evaluation_host,
                generation_host,
                requested_level="host_attested_independence",
                expected_generation_claim_id=facts["generation_claim_value"]["claim_id"],
                expected_evaluation_claim_id=facts["evaluation_claim_value"]["claim_id"],
                _test_only_adapter=fixture_adapter,
            ),
            intended_red,
        )

        project, generation_host, evaluation_host = host_case("replay")
        assert (project / facts["host_use"]).is_file()
        assert (project / facts["host_use_marker"]).is_file()
        expect_future_refusal(
            project,
            "HOST-ATTESTATION-REPLAY",
            lambda: claims.accept_host_pair_for_independence(
                project, generation_host, evaluation_host,
                requested_level="host_attested_independence",
                expected_generation_claim_id=facts["generation_claim_value"]["claim_id"],
                expected_evaluation_claim_id=facts["evaluation_claim_value"]["claim_id"],
                _test_only_adapter=fixture_adapter,
            ),
            intended_red,
        )

        project, _, _ = host_case("unavailable")
        expect_future_refusal(
            project,
            "INDEPENDENCE_UNVERIFIED",
            lambda: claims.accept_host_pair_for_independence(
                project, None, None,
                requested_level="host_attested_independence",
                expected_generation_claim_id=facts["generation_claim_value"]["claim_id"],
                expected_evaluation_claim_id=facts["evaluation_claim_value"]["claim_id"],
            ),
            intended_red,
        )

        project, claim_path = claim_case("protected_destination")
        governance = base / "governance" / "output-routing" / "output_routing.yaml"
        governance.parent.mkdir(parents=True, exist_ok=True)
        governance.write_text("schema_version: 1.0.0\n", encoding="utf-8")
        before = exact_tree_state(project)
        try:
            claims.consume_dispatch_claim(
                project,
                claim_path,
                role="generator",
                consumer_transaction_id="protected-destination",
                target_paths=[TARGET],
                consumed_at="2026-07-25T12:40:00Z",
            )
        except DestinationRefused as exc:
            assert exc.code == DEST_PROTECTED
        else:
            raise AssertionError("protected dispatch destination was accepted")
        assert exact_tree_state(project) == before

        if intended_red:
            raise AssertionError(
                "C4 intended-red dispatch boundary:\n  " + "\n  ".join(intended_red)
            )
    print("assignment_dispatch_claim_smoketest: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
