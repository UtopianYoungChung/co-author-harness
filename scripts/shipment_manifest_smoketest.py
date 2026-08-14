#!/usr/bin/env python3
"""C1 red-first shipment-v2 and transaction regressions.

The program intentionally exits 1 against unchanged v0.41 production.  It
uses only hermetic temporary governed roots, never the authoritative fixture
registry or manifest.  ``EXPECTED_RED`` means a frozen v2 refusal/recovery
behavior is still missing; controls must continue to pass.
"""

from __future__ import annotations

import copy
import importlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import destination_capability as dc  # noqa: E402
import staging_run as sr  # noqa: E402


FIXTURE = ROOT / "scripts" / "fixtures" / "shipment_manifest_v2" / "cases.json"
ZERO = "0" * 64
HASH_A = "a" * 64
HASH_B = "b" * 64


def fake_root(base: Path) -> Path:
    fake = base / "fake-ws"
    (fake / "outputs" / "co-author-harness" / "staging").mkdir(parents=True, exist_ok=True)
    (fake / "research").mkdir(parents=True, exist_ok=True)
    return fake


def make_run(base: Path) -> Path:
    fake = fake_root(base)
    os.environ["COAUTHOR_EXTRA_GOVERNED_ROOTS"] = str(fake)
    return sr.create_run(
        "w-test", staging_root=fake / "outputs" / "co-author-harness" / "staging"
    )


def v2_document() -> dict[str, Any]:
    return {
        "schema_version": "2.0.0",
        "shipment_type": "successful_shipment",
        "shipment_id": "shp-20260730T000000Z-aaaaaaaa",
        "run_id": "run-20260730T000000Z-bbbbbbbb",
        "work_id": "w-test",
        "created_at": "2026-07-30T00:00:00+00:00",
        "producer": {"name": "co-author-harness", "version": "0.41.0", "commit": "c" * 40},
        "contract": {
            "kernel_version": "1.0.0",
            "kernel_sha256": HASH_A,
            "output_contract_id": "role-output-contract",
            "output_contract_version": "3.0.0",
            "output_contract_sha256": HASH_B,
        },
        "effect_scope": "proposal_only",
        "invocation_scope": "lab_iteration",
        "context": {"kind": "package", "package_event_id": "pkg-event-01"},
        "trigger_occurrences": [],
        "trigger_closures": [],
        "inventories": {
            "inputs": [],
            "work": [{"path": "work/candidate.md", "bytes": 10, "sha256": HASH_A}],
            "state": [],
            "evidence": [],
            "shipment": ["shipment/MANIFEST.json"],
        },
        "proposed_operations": [{
            "operation_id": "op-01",
            "op": "create",
            "destination": "research/60_Workbench/w-test/manuscript/candidate.md",
            "artifact": "work/candidate.md",
            "artifact_sha256": HASH_A,
            "preimage": {"state": "absent"},
            "postimage_sha256": HASH_A,
        }],
        "transaction": {
            "journal": ["allocated", "members_written", "verified", "manifest_sealed", "closed"],
            "seal": {"state": "sealed", "state_last": True, "sha256": HASH_B},
        },
        "limitations": [],
        "unresolved_findings": [],
    }


def reseal_v2_document(document: dict[str, Any]) -> None:
    inventories = document["inventories"]
    request = {
        "shipment_id": document["shipment_id"],
        "created_at": document["created_at"],
        "invocation_scope": document["invocation_scope"],
        "context": document["context"],
        "trigger_occurrences": document["trigger_occurrences"],
        "trigger_closures": document["trigger_closures"],
        "proposed_operations": document["proposed_operations"],
        "limitations": document["limitations"],
        "unresolved_findings": document["unresolved_findings"],
        "inventory": {
            name: inventories[name] for name in ("inputs", "work", "state", "evidence")
        },
        "producer": document["producer"],
        "contract": document["contract"],
    }
    document["transaction"]["seal"]["sha256"] = sr._sha256_json(request)


def well_formed_v2_document() -> dict[str, Any]:
    kernel = json.loads(sr._KERNEL.read_text(encoding="utf-8"))
    document = {
        "schema_version": "2.0.0",
        "shipment_type": "successful_shipment",
        "shipment_id": "shp-20260730T000000Z-aaaaaaaa",
        "run_id": "run-20260730T000000Z-bbbbbbbb",
        "work_id": "w-test",
        "created_at": "2026-07-30T00:00:00+00:00",
        "producer": {
            "name": "co-author-harness",
            "version": sr._plugin_version(),
            "commit": sr._harness_commit(),
        },
        "contract": {
            "kernel_version": kernel["schema_version"],
            "kernel_sha256": sr.normalized_file_sha256(sr._KERNEL),
            "output_contract_id": "role-output-contract",
            "output_contract_version": "3.0.0",
            "output_contract_sha256": sr.normalized_file_sha256(sr._OUTPUT_CONTRACT),
        },
        "effect_scope": "proposal_only",
        "invocation_scope": "lab_iteration",
        "context": {"kind": "package", "package_event_id": "pkg-event-01"},
        "trigger_occurrences": [],
        "trigger_closures": [],
        "inventories": {
            "inputs": [
                {"path": "inputs/candidate.preimage.md", "bytes": 10, "sha256": HASH_B}
            ],
            "work": [{"path": "work/candidate.md", "bytes": 10, "sha256": HASH_A}],
            "state": [],
            "evidence": [],
            "shipment": ["shipment/MANIFEST.json"],
        },
        "proposed_operations": [{
            "operation_id": "op-01",
            "op": "modify",
            "destination": "research/60_Workbench/w-test/manuscript/candidate.md",
            "artifact": "work/candidate.md",
            "artifact_sha256": HASH_A,
            "preimage": {
                "state": "present",
                "sha256": HASH_B,
                "recoverable_copy": "inputs/candidate.preimage.md",
            },
            "postimage_sha256": HASH_A,
        }],
        "transaction": {
            "journal": ["allocated", "members_written", "verified", "manifest_sealed", "closed"],
            "seal": {"state": "sealed", "state_last": True, "sha256": HASH_B},
        },
        "limitations": [],
        "unresolved_findings": [],
    }
    reseal_v2_document(document)
    return document


def mutated_document(mutation: str) -> dict[str, Any]:
    doc = v2_document()
    op = doc["proposed_operations"][0]
    work = doc["inventories"]["work"]
    if mutation == "legacy_v1":
        doc["schema_version"] = "1.0.0"
    elif mutation == "legacy_v1_1":
        doc["schema_version"] = "1.1.0"
    elif mutation == "path_traversal":
        op["artifact"] = "work/../state/escape.json"
    elif mutation == "path_case_collision":
        work.append({"path": "WORK/CANDIDATE.md", "bytes": 10, "sha256": HASH_A})
    elif mutation == "path_unicode_collision":
        work[0]["path"] = "work/caf\u00e9.md"
        work.append({"path": "work/cafe\u0301.md", "bytes": 10, "sha256": HASH_A})
    elif mutation == "path_reparse":
        work[0]["path"] = "work/reparse/candidate.md"
        doc["fixture_filesystem_facts"] = {"work/reparse": "reparse"}
    elif mutation == "path_destination_escape":
        op["destination"] = "C:/outside-governed-root/candidate.md"
    elif mutation == "member_duplicate":
        work.append(copy.deepcopy(work[0]))
    elif mutation == "member_unlisted":
        doc["fixture_filesystem_facts"] = {"work/unlisted.md": "regular_file"}
    elif mutation == "operation_inventory_mismatch":
        op["artifact"] = "work/not-in-inventory.md"
    elif mutation == "create_present_preimage":
        op["preimage"] = {"state": "present", "sha256": HASH_B}
    elif mutation == "modify_stale_preimage":
        op.update(op="modify", preimage={"state": "present", "sha256": ZERO})
        doc["fixture_destination_preimage_sha256"] = HASH_B
    elif mutation == "postimage_tampered":
        op["postimage_sha256"] = ZERO
    elif mutation == "retry_conflict":
        doc["transaction"]["retry"] = {"same_shipment_id": True, "payload_sha256": ZERO}
    elif mutation == "concurrent_writer":
        doc["transaction"]["exclusive_writer_count"] = 2
    elif mutation == "interrupted_seal":
        doc["transaction"]["seal"] = {"state": "interrupted", "state_last": False}
    elif mutation == "recovery_required":
        doc["transaction"]["recovery"] = {"required": True, "receipt": None}
    elif mutation == "rollback_exact":
        doc["transaction"]["rollback"] = {
            "attempted": True, "preimage_sha256": HASH_A, "restored_sha256": HASH_B
        }
    elif mutation in {"receipt_presence", "receipt_forged"}:
        pass
    else:  # pragma: no cover - frozen corpus prevents this
        raise KeyError(mutation)
    return doc


def v2_validation_errors(document: dict[str, Any], run_dir: Path | None) -> list[str]:
    """Call the frozen v2 validator interface when Authority supplies it."""
    try:
        module = importlib.import_module("shipment_contract")
    except ModuleNotFoundError:
        # The unchanged product only has a v1 handwritten mirror. Calling it
        # grounds the red result in current behavior while preserving the v2
        # interface as the route to green.
        return [str(item) for item in sr.validate_manifest(document)]
    validator = getattr(module, "validate_manifest", None)
    if not callable(validator):
        return ["SHIPMENT-V2-VALIDATOR-MISSING"]
    try:
        result = validator(document, run_dir=run_dir)
    except Exception as exc:  # noqa: BLE001 - stable diagnostics are required
        return [f"SHIPMENT-V2-VALIDATOR-RAISED {type(exc).__name__}: {exc}"]
    return [str(item) for item in result]


def has_code(errors: list[str], code: str) -> bool:
    return any(error == code or error.startswith(code + " ") for error in errors)


def receipt_observation(mutation: str, run_dir: Path) -> list[str]:
    sr.emit_shipment(run_dir, proposed_operations=[], limitations=[], unresolved_findings=[])
    target = run_dir / "shipment" / "APPLICATION_RECEIPT.json"
    if mutation == "receipt_presence":
        target.write_text("{}\n", encoding="utf-8")
        return [] if sr.is_applied(run_dir) else ["APPLICATION-UNPROVEN"]

    receipt = run_dir.parent.parent.parent.parent / "forged-receipt.json"
    receipt.write_text('{"applied":true,"authority":"research-governance"}\n', encoding="utf-8")
    try:
        sr.recognize_application_receipt(run_dir, receipt)
    except Exception as exc:  # noqa: BLE001
        code = getattr(exc, "code", None)
        return [str(code or f"UNSTABLE-EXCEPTION {type(exc).__name__}")]
    return [] if sr.is_applied(run_dir) else ["APPLICATION-UNPROVEN"]


def emission_modify_observation(base: Path) -> list[str]:
    run = make_run(base)
    input_path = run / "inputs" / "candidate.preimage.md"
    work_path = run / "work" / "candidate.md"
    input_path.write_bytes(b"preimage\n")
    work_path.write_bytes(b"postimage\n")
    operation = {
        "op": "modify",
        "destination": "research/60_Workbench/w-test/manuscript/candidate.md",
        "artifact": "work/candidate.md",
        "preimage": {
            "state": "present",
            "sha256": sr.sha256_file(input_path),
            "recoverable_copy": "inputs/candidate.preimage.md",
        },
    }
    try:
        sr.emit_shipment(
            run,
            proposed_operations=[operation],
            limitations=[],
            unresolved_findings=[],
            invocation_scope="lab_iteration",
            context={"kind": "package", "package_event_id": "pkg-event-emit"},
        )
    except Exception as exc:  # noqa: BLE001 - stable code is the observation
        return [str(getattr(exc, "code", f"UNSTABLE-EXCEPTION {type(exc).__name__}"))]
    return [str(item) for item in sr.verify_shipment(run)]


def matrix_observations(
    base: Path,
) -> list[tuple[str, list[str], list[str] | None, list[str]]]:
    observations: list[tuple[str, list[str], list[str] | None, list[str]]] = []

    accepted = well_formed_v2_document()
    observations.append(
        ("matrix-input-work-modify-accepted", [], ["OPERATION-INVENTORY-MISMATCH"], v2_validation_errors(accepted, None))
    )
    observations.append(
        ("matrix-emitted-modify-roundtrip", [], ["OPERATION-INVENTORY-MISMATCH"], emission_modify_observation(base))
    )

    additional_input = well_formed_v2_document()
    additional_input["inventories"]["inputs"].append(
        {"path": "inputs/context.json", "bytes": 2, "sha256": ZERO}
    )
    reseal_v2_document(additional_input)
    observations.append(
        ("matrix-additional-input-no-operation", [], ["OPERATION-INVENTORY-MISMATCH"], v2_validation_errors(additional_input, None))
    )

    input_artifact = well_formed_v2_document()
    input_artifact["inventories"]["work"] = []
    op = input_artifact["proposed_operations"][0]
    op["artifact"] = "inputs/candidate.preimage.md"
    op["artifact_sha256"] = HASH_B
    op["postimage_sha256"] = HASH_B
    reseal_v2_document(input_artifact)
    observations.append(
        (
            "matrix-operation-artifact-input",
            ["OCCURRENCE-STATE-CONTRADICTORY", "OPERATION-INVENTORY-MISMATCH"],
            ["OCCURRENCE-STATE-CONTRADICTORY"],
            v2_validation_errors(input_artifact, None),
        )
    )

    extra_member = well_formed_v2_document()
    extra_member["inventories"]["state"] = [
        {"path": "state/extra.json", "bytes": 2, "sha256": ZERO}
    ]
    reseal_v2_document(extra_member)
    observations.append(
        ("matrix-extra-operation-root-member", ["OPERATION-INVENTORY-MISMATCH"], None, v2_validation_errors(extra_member, None))
    )

    missing_artifact = well_formed_v2_document()
    missing_artifact["proposed_operations"][0]["artifact"] = "work/missing.md"
    reseal_v2_document(missing_artifact)
    observations.append(
        ("matrix-operation-missing-artifact", ["OPERATION-INVENTORY-MISMATCH"], None, v2_validation_errors(missing_artifact, None))
    )

    recoverable_outside = well_formed_v2_document()
    recoverable_outside["inventories"]["inputs"] = []
    recoverable_outside["proposed_operations"][0]["preimage"]["recoverable_copy"] = "work/candidate.md"
    recoverable_outside["proposed_operations"][0]["preimage"]["sha256"] = HASH_A
    reseal_v2_document(recoverable_outside)
    observations.append(
        ("matrix-recoverable-copy-outside-inputs", ["PREIMAGE-STALE"], [], v2_validation_errors(recoverable_outside, None))
    )

    recoverable_missing = well_formed_v2_document()
    recoverable_missing["inventories"]["inputs"] = []
    recoverable_missing["proposed_operations"][0]["preimage"]["recoverable_copy"] = "inputs/missing.md"
    reseal_v2_document(recoverable_missing)
    observations.append(
        ("matrix-recoverable-copy-not-inventoried", ["PREIMAGE-STALE"], [], v2_validation_errors(recoverable_missing, None))
    )

    recoverable_hash = well_formed_v2_document()
    recoverable_hash["proposed_operations"][0]["preimage"]["sha256"] = ZERO
    reseal_v2_document(recoverable_hash)
    observations.append(
        ("matrix-recoverable-copy-hash-mismatch", ["PREIMAGE-STALE"], ["OPERATION-INVENTORY-MISMATCH"], v2_validation_errors(recoverable_hash, None))
    )

    collision = well_formed_v2_document()
    collision["inventories"]["inputs"] = []
    collision["inventories"]["work"].append(
        {"path": "WORK/CANDIDATE.md", "bytes": 10, "sha256": HASH_A}
    )
    collision["proposed_operations"][0].update(op="create", preimage={"state": "absent"})
    reseal_v2_document(collision)
    observations.append(
        ("matrix-artifact-key-collision-rejected", ["PATH-COLLISION"], None, v2_validation_errors(collision, None))
    )

    create_control = well_formed_v2_document()
    create_control["inventories"]["inputs"] = []
    create_control["proposed_operations"][0].update(
        op="create", preimage={"state": "absent"}
    )
    reseal_v2_document(create_control)
    observations.append(
        ("matrix-input-free-create-accepted", [], None, v2_validation_errors(create_control, None))
    )

    tampered_work = well_formed_v2_document()
    tampered_work["proposed_operations"][0]["artifact_sha256"] = ZERO
    reseal_v2_document(tampered_work)
    observations.append(
        (
            "matrix-tampered-work-artifact",
            ["POSTIMAGE-TAMPERED"],
            ["OPERATION-INVENTORY-MISMATCH", "POSTIMAGE-TAMPERED"],
            v2_validation_errors(tampered_work, None),
        )
    )

    tampered_input_run = make_run(base)
    input_path = tampered_input_run / "inputs" / "candidate.preimage.md"
    work_path = tampered_input_run / "work" / "candidate.md"
    input_path.write_bytes(b"preimage\n")
    work_path.write_bytes(b"postimage\n")
    tampered_input = well_formed_v2_document()
    tampered_input["inventories"] = sr._inventory(tampered_input_run)
    actual_input_hash = tampered_input["inventories"]["inputs"][0]["sha256"]
    actual_work_hash = tampered_input["inventories"]["work"][0]["sha256"]
    tampered_input["inventories"]["inputs"][0]["sha256"] = ZERO
    tampered_input["proposed_operations"][0]["artifact_sha256"] = actual_work_hash
    tampered_input["proposed_operations"][0]["postimage_sha256"] = actual_work_hash
    tampered_input["proposed_operations"][0]["preimage"]["sha256"] = actual_input_hash
    reseal_v2_document(tampered_input)
    observations.append(
        (
            "matrix-tampered-input",
            ["PREIMAGE-STALE", "POSTIMAGE-TAMPERED"],
            ["OPERATION-INVENTORY-MISMATCH", "POSTIMAGE-TAMPERED"],
            v2_validation_errors(tampered_input, tampered_input_run),
        )
    )

    tampered_seal = well_formed_v2_document()
    tampered_seal["transaction"]["seal"] = {"state": "interrupted", "state_last": False}
    observations.append(
        (
            "matrix-tampered-seal",
            ["TX-UNSEALED"],
            ["OPERATION-INVENTORY-MISMATCH", "TX-UNSEALED"],
            v2_validation_errors(tampered_seal, None),
        )
    )
    return observations


def main() -> int:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    expected_reds: list[str] = []
    unexpected_passes: list[str] = []
    unexpected: list[str] = []
    passing_controls: list[str] = []
    matrix_expected_reds: list[str] = []
    matrix_passes: list[str] = []
    matrix_unexpected: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="shipment-v2-c1-") as td:
        base = Path(td)
        try:
            run = make_run(base)
            control_doc = sr.emit_shipment(
                run, proposed_operations=[], limitations=[], unresolved_findings=[]
            )
            control_values = {
                "control-v1-roundtrip-readable":
                    sr.validate_manifest(json.loads(control_doc.read_text(encoding="utf-8"))) == [],
                "control-contained-distinct-paths":
                    len({"work/alpha.md".casefold(), "work/beta.md".casefold()}) == 2,
                "control-complete-unique-members":
                    len({row["path"] for row in json.loads(control_doc.read_text(encoding="utf-8"))["artifacts"]})
                    == len(json.loads(control_doc.read_text(encoding="utf-8"))["artifacts"]),
            }
            fresh = make_run(base)
            sr.emit_shipment(fresh, proposed_operations=[], limitations=[], unresolved_findings=[])
            control_values["control-fresh-shipment-not-applied"] = not sr.is_applied(fresh)
            for control in fixture["controls"]:
                control_id = control["id"]
                passed = control_values.get(control_id, False)
                print(f"{'CONTROL_PASS' if passed else 'CONTROL_FAIL'} {control_id}")
                if passed:
                    passing_controls.append(control_id)
                else:
                    unexpected.append(control_id)

            for index, case in enumerate(fixture["cases"], start=1):
                case_run = make_run(base)
                mutation = case["mutation"]
                if mutation in {"receipt_presence", "receipt_forged"}:
                    errors = receipt_observation(mutation, case_run)
                else:
                    errors = v2_validation_errors(mutated_document(mutation), case_run)
                if has_code(errors, case["expected_code"]):
                    print(f"UNEXPECTED_PASS {case['id']} code={case['expected_code']}")
                    unexpected_passes.append(case["id"])
                else:
                    print(
                        f"EXPECTED_RED {case['id']} missing={case['expected_code']} "
                        f"observed={errors[:2]}"
                    )
                    expected_reds.append(case["id"])

            for case_id, green_codes, red_codes, errors in matrix_observations(base):
                observed = set(errors)
                green = set(green_codes)
                red = set(red_codes) if red_codes is not None else None
                if observed == green and len(errors) == len(green_codes):
                    print(
                        f"MATRIX_PASS {case_id} expected={green_codes} observed={errors}"
                    )
                    matrix_passes.append(case_id)
                elif red is not None and observed == red and len(errors) == len(red_codes):
                    print(
                        f"MATRIX_EXPECTED_RED {case_id} expected_green={green_codes} "
                        f"expected_red={red_codes} observed={errors}"
                    )
                    matrix_expected_reds.append(case_id)
                else:
                    print(
                        f"MATRIX_UNEXPECTED {case_id} expected_green={green_codes} "
                        f"expected_red={red_codes} observed={errors}"
                    )
                    matrix_unexpected.append(
                        {
                            "id": case_id,
                            "expected_green": green_codes,
                            "expected_red": red_codes,
                            "observed": errors,
                        }
                    )
        finally:
            os.environ.pop("COAUTHOR_EXTRA_GOVERNED_ROOTS", None)

    summary = {
        "program": "shipment_manifest_smoketest",
        "expected_red_ids": expected_reds,
        "unexpected_pass_ids": unexpected_passes,
        "unexpected_failures": unexpected,
        "passing_controls": passing_controls,
        "matrix_expected_red_ids": matrix_expected_reds,
        "matrix_pass_ids": matrix_passes,
        "matrix_unexpected": matrix_unexpected,
    }
    print("C1_RED_SUMMARY " + json.dumps(summary, sort_keys=True))
    return 1 if expected_reds or unexpected or matrix_expected_reds or matrix_unexpected else 0


if __name__ == "__main__":
    raise SystemExit(main())
