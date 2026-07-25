#!/usr/bin/env python3
"""Synthetic-only recorded M1-to-FINAL protocol-conformance fixture.

This module composes production publishers and validators.  Its report proves
protocol execution only; it does not certify human-quality semantic judgment
or host-attested separation of agents.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
import hashlib
import io
import json
from pathlib import Path
from typing import Any, Callable

import draft_evidence_verifier as verifier
import full_run_contract_check as full_run
import product_assurance as assurance
from assignment_receipt_transaction import ReceiptTransactionError, load_mutation_ledger
from c2_evidence_fixture_support import ASSET_ROOT, build_activation_fixture
from semantic_graph_fixture_support import semantic_graph_fixture_environment
from assignment_terminal_close_smoketest import (
    BOUND,
    CHECKPOINT,
    install_ph4_evidence,
    prepare_public_m1_m4,
    publish_final,
    run,
    state,
    terminal_inputs,
)


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ProtocolConformanceFixture:
    project: Path
    receipt: Path
    report: Path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def write_json(path: Path, value: object, *, canonical: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if canonical:
        path.write_bytes(canonical_bytes(value))
    else:
        path.write_text(
            json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )


def binding(project: Path, path: Path) -> dict[str, str]:
    return {
        "path": path.resolve().relative_to(project.resolve()).as_posix(),
        "sha256": sha(path),
    }


def _product_main(arguments: list[str]) -> int:
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
        io.StringIO()
    ):
        return assurance.main(arguments)


def _candidate_adjudication(project: Path) -> dict[str, Any]:
    lane = project / "reviews" / ".harness" / "protocol_conformance" / "candidate"
    activation = build_activation_fixture(
        project,
        artifact_relative=(lane / "candidate.md").relative_to(project).as_posix(),
        evidence_relative=(lane / "evidence").relative_to(project).as_posix(),
    )
    activation.mutate_artifact(
        lambda text: text.replace(
            "# References",
            "The bounded contribution is bounded and bounded.\n\n# References",
        )
    )
    v3 = json.loads(activation.receipt.read_text(encoding="utf-8"))
    receipt = lane / "semantic-evaluation-v2.json"
    placeholder = {"path": str(receipt.resolve()), "sha256": "0" * 64}
    semantic: dict[str, Any] = {
        "schema_version": "2.0.0",
        "receipt_type": "centroid_semantic_execution",
        "target": "FINAL",
        "phase": "evaluation",
        "role": "evaluator",
        "actor_id": "protocol-conformance-evaluator",
        "dispatch_id": "protocol-conformance-evaluation",
        "artifact": {
            "path": str(activation.artifact.resolve()),
            "sha256": sha(activation.artifact),
        },
        "centroid_packet": placeholder,
        "generation_envelope": placeholder,
        "adjudications": [],
        "passages": v3["diagnostic_legacy_view"]["passages"],
        "semantic_assessment": {
            "summary": "Synthetic protocol-conformance adjudication only.",
            "strengths": [],
            "deviations": [],
            "warrant_limits": [
                "No human-quality semantic judgment or host separation is claimed."
            ],
            "actionable_findings": [],
        },
    }
    write_json(receipt, semantic, canonical=True)
    first_report = lane / "product-candidates.json"
    first_rc = _product_main([
        "build",
        "--artifact", str(activation.artifact),
        "--semantic-receipt", str(receipt),
        "--project-root", str(project),
        "--wiki-root", str(activation.wiki_root),
        "--out", str(first_report),
    ])
    if first_rc == 0:
        raise AssertionError("candidate fixture unexpectedly produced no candidate")
    first = json.loads(first_report.read_text(encoding="utf-8"))
    candidates = [row for row in first["findings"] if row.get("severity") == "candidate"]
    if not candidates or any("candidate_fingerprint" not in row for row in candidates):
        raise AssertionError("product publisher omitted fingerprinted candidates")
    semantic["adjudications"] = [{
        "candidate_fingerprint": row["candidate_fingerprint"],
        "code": row["code"],
        "locator": row["locator"],
        "disposition": "accepted_synthesis",
        "rationale": "Synthetic evaluator accepts this fixture-only wording.",
    } for row in candidates]
    write_json(receipt, semantic, canonical=True)
    qualified_report = lane / "product-qualified.json"
    qualified_rc = _product_main([
        "build",
        "--artifact", str(activation.artifact),
        "--semantic-receipt", str(receipt),
        "--project-root", str(project),
        "--wiki-root", str(activation.wiki_root),
        "--out", str(qualified_report),
    ])
    if qualified_rc != 0:
        raise AssertionError(qualified_report.read_text(encoding="utf-8"))

    artifact_bytes = activation.artifact.read_bytes()
    receipt_bytes = receipt.read_bytes()
    activation.artifact.write_text(
        activation.artifact.read_text(encoding="utf-8").replace(
            "bounded contribution is bounded and bounded",
            "limited contribution is limited and limited",
        ),
        encoding="utf-8",
        newline="\n",
    )
    stale = json.loads(receipt.read_text(encoding="utf-8"))
    stale["artifact"] = {
        "path": str(activation.artifact.resolve()),
        "sha256": sha(activation.artifact),
    }
    write_json(receipt, stale, canonical=True)
    stale_report = lane / "product-stale-adjudication.json"
    stale_rc = _product_main([
        "build",
        "--artifact", str(activation.artifact),
        "--semantic-receipt", str(receipt),
        "--project-root", str(project),
        "--wiki-root", str(activation.wiki_root),
        "--out", str(stale_report),
    ])
    stale_value = json.loads(stale_report.read_text(encoding="utf-8"))
    stale_code = stale_value.get("reason_code")
    if stale_code is None:
        stale_code = next(
            (
                row.get("code")
                for row in stale_value.get("findings", [])
                if isinstance(row, dict) and isinstance(row.get("code"), str)
            ),
            None,
        )
    activation.artifact.write_bytes(artifact_bytes)
    receipt.write_bytes(receipt_bytes)
    if stale_rc == 0 or stale_code != "ADJUDICATION-STALE":
        raise AssertionError(f"candidate tamper reached {stale_rc}/{stale_code}")
    return {
        "status": "passed",
        "fingerprint_bound": True,
        "candidate_count": len(candidates),
        "receipt": binding(project, receipt),
        "qualified_report": binding(project, qualified_report),
        "tamper_report": binding(project, stale_report),
        "tamper_code": stale_code,
    }


def _milestone_locator(project: Path, milestone: str, phase: str) -> tuple[Path, Path]:
    document = state(project)
    record = document["milestone_framework"]["milestones"][milestone]
    locator_row = record["policy_evidence"][f"draft_{phase}"]
    locator = project / locator_row["evidence_path"]
    locator_value = json.loads(locator.read_text(encoding="utf-8"))
    return locator, project / locator_value["target"]


def _validate_locator(project: Path, milestone: str, phase: str) -> dict[str, Any]:
    locator, artifact = _milestone_locator(project, milestone, phase)
    return verifier.validate_lifecycle_verifier_binding(
        locator=locator,
        artifact=artifact,
        project_root=project,
        harness_root=ROOT,
        expected_phase=phase,
        expected_disposition=(
            "evaluation_ready" if phase == "generation" else "product_qualified"
        ),
    )


def _expect_verifier_error(action: Callable[[], object], code: str) -> str:
    try:
        action()
    except verifier.VerifierError as exc:
        if exc.code != code:
            raise AssertionError(f"expected {code}, got {exc.code}: {exc}") from exc
        return exc.code
    raise AssertionError(f"expected verifier refusal {code}")


def _expect_receipt_error(action: Callable[[], object], code: str) -> str:
    try:
        action()
    except ReceiptTransactionError as exc:
        if exc.code != code:
            raise AssertionError(f"expected {code}, got {exc.code}: {exc}") from exc
        return exc.code
    raise AssertionError(f"expected receipt refusal {code}")


def _tamper_results(project: Path, candidate: dict[str, Any]) -> dict[str, str]:
    results = {"candidate_text": str(candidate["tamper_code"])}

    m1_locator, _artifact = _milestone_locator(project, "M1", "generation")
    locator_value = json.loads(m1_locator.read_text(encoding="utf-8"))
    semantic = project / locator_value["semantic_receipt"]["path"]
    semantic_value = json.loads(semantic.read_text(encoding="utf-8"))
    extract_receipt = project / semantic_value["canonical_extract_receipts"][0]["path"]
    extract_value = json.loads(extract_receipt.read_text(encoding="utf-8"))
    normalized = project / extract_value["normalized_output"]["path"]
    normalized_bytes = normalized.read_bytes()
    try:
        normalized.write_bytes(normalized_bytes + b"tamper")
        results["extract_bytes"] = _expect_verifier_error(
            lambda: _validate_locator(project, "M1", "generation"),
            "EXTRACT-BINDING-STALE",
        )
    finally:
        normalized.write_bytes(normalized_bytes)

    m2_locator, _ = _milestone_locator(project, "M2", "generation")
    m2_value = json.loads(m2_locator.read_text(encoding="utf-8"))
    locator_bytes = m1_locator.read_bytes()
    try:
        locator_value["dispatch_consumption"] = m2_value["dispatch_consumption"]
        write_json(m1_locator, locator_value)
        results["dispatch_consumption"] = _expect_verifier_error(
            lambda: _validate_locator(project, "M1", "generation"),
            "LIFECYCLE-EVIDENCE-CLAIM",
        )
    finally:
        m1_locator.write_bytes(locator_bytes)

    ledger = project / "reviews" / ".harness" / "assignment" / "mutation_ledger.jsonl"
    ledger_bytes = ledger.read_bytes()
    try:
        rows = ledger.read_text(encoding="utf-8").splitlines()
        first = json.loads(rows[0])
        first["target_path"] = "milestones/tampered.md"
        rows[0] = json.dumps(first, sort_keys=True)
        ledger.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
        expected = "APG-MUTATION-LEDGER-INVALID"
        results["mutation_row"] = _expect_receipt_error(
            lambda: load_mutation_ledger(project), expected
        )
    finally:
        ledger.write_bytes(ledger_bytes)

    signoff = project / "reviews" / "G4_signoff.md"
    signoff_bytes = signoff.read_bytes()
    try:
        signoff.write_bytes(signoff_bytes + b"\nchanged\n")
        codes = {
            row.get("code")
            for row in full_run._structured_terminal_signoff_findings(
                project, state(project)
            )
        }
        expected = "FRC-TERMINAL-EVIDENCE-BINDING"
        if expected not in codes:
            raise AssertionError(f"signoff tamper codes: {sorted(codes)}")
        results["terminal_signoff"] = expected
    finally:
        signoff.write_bytes(signoff_bytes)

    if full_run.check_terminal(project):
        raise AssertionError("restored protocol fixture no longer passes terminal")
    return results


def _passage_summary(project: Path) -> dict[str, bool]:
    locator, _artifact = _milestone_locator(project, "M1", "generation")
    locator_value = json.loads(locator.read_text(encoding="utf-8"))
    semantic = project / locator_value["semantic_receipt"]["path"]
    value = json.loads(semantic.read_text(encoding="utf-8"))
    uses = {row["passage_use"] for row in value["passages"]}
    extract = project / value["canonical_extract_receipts"][0]["path"]
    extract_value = json.loads(extract.read_text(encoding="utf-8"))
    source = project / extract_value["source"]["path"]
    return {
        "real_pdf_extraction": (
            source.suffix.casefold() == ".pdf"
            and source.is_file()
            and sha(source) == sha(ASSET_ROOT / "miniature.pdf")
            and extract_value["extraction"]["adapter"] == "poppler-pdftotext"
        ),
        "direct_quotation": "direct_quotation" in uses,
        "conditioning_passage": "conditioning_passage" in uses,
    }


def _production_counts(project: Path) -> dict[str, int]:
    assignment = project / "reviews" / ".harness" / "assignment"
    consumed = [
        path for path in (assignment / "consumed").glob("gate_receipt_*.json")
        if not path.name.endswith(".result.json")
    ]
    return {
        "consumed_assignment_receipts": len(consumed),
        "dispatch_claims": len(list((assignment / "dispatch" / "claims").glob("*/claim.json"))),
        "dispatch_consumptions": len(list((assignment / "dispatch" / "consumptions").glob("*/consumption.json"))),
        "verifier_transactions": len(list((project / "reviews" / ".harness" / "verifier").glob("**/verifier-transaction.json"))),
        "mutation_rows": len(
            (assignment / "mutation_ledger.jsonl").read_text(encoding="utf-8").splitlines()
        ),
    }


def build_protocol_conformance(base: Path) -> ProtocolConformanceFixture:
    """Build and qualify one synthetic recorded M1-to-FINAL assignment."""
    project = (base / "protocol-project").resolve()
    with semantic_graph_fixture_environment():
        prepare_public_m1_m4(project)
        install_ph4_evidence(project, base / "terminal-input-fixture")
        run(
            CHECKPOINT,
            "begin",
            "--project-root", project,
            "--milestone", "FINAL",
            "--at", "2026-07-19T01:00:01Z",
        )
        final_bytes = b"# Protocol-conformance final manuscript\n\nSynthetic only.\n"
        consumed, lifecycle_policy = publish_final(
            project, final_bytes, final_bytes, label="protocol-conformance"
        )
        checkpoint, terminal, approval = terminal_inputs(project, lifecycle_policy)
        run(
            CHECKPOINT,
            "record",
            "--project-root", project,
            "--milestone", "FINAL",
            "--receipt", consumed,
            "--checkpoint", checkpoint,
            "--at", "2026-07-19T01:00:04Z",
        )
        run(
            CHECKPOINT,
            "accept",
            "--project-root", project,
            "--milestone", "FINAL",
            "--checkpoint", checkpoint,
            "--approval-evidence", approval,
            "--terminal-evidence", terminal,
            "--at", "2026-07-19T01:00:06Z",
        )
        terminal_result = run(
            ROOT / "scripts" / "full_run_contract_check.py",
            "terminal",
            "--project-root", project,
        )
        terminal_payload = json.loads(terminal_result.stdout)
        if terminal_payload != {"status": "OK", "findings": []}:
            raise AssertionError(terminal_result.stdout)

        candidate = _candidate_adjudication(project)
        for milestone in ("M1", "M2", "M3", "M4", "M5"):
            _validate_locator(project, milestone, "generation")
            _validate_locator(project, milestone, "evaluation")
        passage_summary = _passage_summary(project)
        production_counts = _production_counts(project)
        if production_counts != {
            "consumed_assignment_receipts": 5,
            "dispatch_claims": 10,
            "dispatch_consumptions": 10,
            "verifier_transactions": 10,
            "mutation_rows": 6,
        }:
            raise AssertionError(f"unexpected production counts: {production_counts}")
        tampers = _tamper_results(project, candidate)

        lane = project / "reviews" / ".harness" / "protocol_conformance"
        receipt_path = lane / "receipt.json"
        document = state(project)
        milestone_records = document["milestone_framework"]["milestones"]
        mutation_ledger = (
            project / "reviews" / ".harness" / "assignment" / "mutation_ledger.jsonl"
        )
        receipt_value = {
            "schema_version": "1.0.0",
            "receipt_type": "protocol_conformance",
            "status": "passed",
            "fixture_scope": "synthetic_only",
            "claims": {
                "human_quality_semantic_judgment": False,
                "host_attested_separate_agents": False,
            },
            "terminal_round_id": BOUND,
            "milestones": {
                key: {
                    "status": milestone_records[key]["status"],
                    "handoff": milestone_records[key]["handoff"],
                }
                for key in ("M1", "M2", "M3", "M4", "M5")
            },
            "production_evidence": {
                "mutation_ledger": binding(project, mutation_ledger),
                "candidate_adjudication": candidate,
                "passage_evidence": passage_summary,
                "production_counts": production_counts,
                "legacy_anchor": "not_applicable_new_synthetic_project",
            },
        }
        write_json(receipt_path, receipt_value)
        report_path = lane / "report.json"
        report_value = {
            "schema_version": "1.0.0",
            "report_type": "protocol_conformance",
            "status": "passed",
            "claims": receipt_value["claims"],
            "receipt": binding(project, receipt_path),
            "milestones": ["M1", "M2", "M3", "M4", "M5"],
            "terminal": {"status": "PASS", "round_id": BOUND},
            "candidate_adjudication": candidate,
            "passage_evidence": passage_summary,
            "production_counts": production_counts,
            "tamper_results": tampers,
            "limitations": [
                "Protocol conformance does not prove human-quality semantic judgment.",
                "Protocol conformance does not prove host-attested separate agents.",
                "Terminal-input prose artifacts reuse the established synthetic valid-project builder where no production publisher exists.",
            ],
        }
        write_json(report_path, report_value)
    return ProtocolConformanceFixture(project, receipt_path, report_path)
