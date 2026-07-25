#!/usr/bin/env python3
"""One-command diagnostic or governed product-gate adapter."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from c2_evidence_validation import canonical_bytes
from destination_capability import assert_writable
from draft_evidence_verifier import VerifierError, validate_verifier_transaction
from product_assurance import DETECTOR_NAME, DETECTOR_VERSION
from source_extract import SUPPORTED_PDF_EXTRACTOR


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "references" / "schemas" / "run_product_gate_manifest.schema.json"
SEMANTICS = ROOT / "references" / "semantics_manifest.v1.json"
RUN_ALL = ROOT / "scripts" / "audit" / "run_all.py"
CHECK_DETERMINISTIC = "deterministic-audit-suite"
CHECK_SEMANTIC = "semantic-product-verifier"
CHECK_VOCABULARY = frozenset({CHECK_DETERMINISTIC, CHECK_SEMANTIC})
GOVERNED_INPUT_KINDS = frozenset({
    "governed_artifact",
    "semantic_receipt",
    "verifier_transaction",
    "verifier_publication_manifest",
    "verifier_commit_marker",
    "semantics_manifest",
    "wiki_root_manifest",
    "project_root_manifest",
})


class ProductGateError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _input(path: Path, kind: str) -> dict[str, Any]:
    path = path.resolve(strict=True)
    return {"kind": kind, "path": str(path), "sha256": sha(path), "size": path.stat().st_size}


def _validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _validate_check_accounting(value: dict[str, Any]) -> None:
    requested = value.get("requested_checks", [])
    unknown = sorted(set(requested) - CHECK_VOCABULARY)
    if unknown:
        raise ProductGateError(
            "PRODUCT-GATE-CHECK-UNKNOWN",
            f"unknown requested checks: {', '.join(unknown)}",
        )
    dispositions = [row.get("check") for row in value.get("dispositions", [])]
    omissions = [row.get("check") for row in value.get("omissions", [])]
    accounted = dispositions + omissions
    if (
        len(accounted) != len(set(accounted))
        or set(accounted) != set(requested)
    ):
        raise ProductGateError(
            "PRODUCT-GATE-CHECK-ACCOUNTING",
            "every requested check must have exactly one disposition or omission",
        )
    required = CHECK_SEMANTIC if value.get("mode") == "governed-product" else CHECK_DETERMINISTIC
    if required not in requested:
        raise ProductGateError(
            "PRODUCT-GATE-MODE-MISMATCH",
            f"{value.get('mode')} mode requires requested check {required}",
        )


def _write_exclusive(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    try:
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _publication(manifest_path: Path, manifest_bytes: bytes, run_id: str) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "transaction_id": run_id,
        "state": "prepared",
        "products": [{"path": manifest_path.name, "sha256": hashlib.sha256(manifest_bytes).hexdigest()}],
    }


def _marker(publication_path: Path, publication_bytes: bytes, run_id: str) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "transaction_id": run_id,
        "state": "committed",
        "publication_manifest": publication_path.name,
        "publication_manifest_sha256": hashlib.sha256(publication_bytes).hexdigest(),
    }


def _publish(
    out_dir: Path,
    manifest: dict[str, Any],
    *,
    recover: bool,
    stop_before_marker: bool,
) -> dict[str, Path]:
    assert_writable(out_dir, "product-gate run publication")
    manifest_path = out_dir / "run-manifest.json"
    publication_path = out_dir / "publication-manifest.json"
    marker_path = out_dir / "commit-marker.json"
    manifest_bytes = canonical_bytes(manifest)
    publication = _publication(manifest_path, manifest_bytes, manifest["run_id"])
    publication_bytes = canonical_bytes(publication)
    marker_bytes = canonical_bytes(_marker(publication_path, publication_bytes, manifest["run_id"]))
    existing = (manifest_path.exists(), publication_path.exists(), marker_path.exists())
    if existing[0] or existing[1] or existing[2]:
        if not existing[0] or not existing[1]:
            raise ProductGateError(
                "PRODUCT-GATE-RECOVERY-REQUIRED", "partial run publication is ambiguous"
            )
        if manifest_path.read_bytes() != manifest_bytes or publication_path.read_bytes() != publication_bytes:
            raise ProductGateError(
                "PRODUCT-GATE-RECOVERY-REQUIRED", "partial run differs from requested inputs"
            )
        if marker_path.exists():
            if marker_path.read_bytes() != marker_bytes:
                raise ProductGateError(
                    "PRODUCT-GATE-RECOVERY-REQUIRED", "run marker differs from requested inputs"
                )
            return {"manifest": manifest_path, "publication": publication_path, "marker": marker_path}
        if not recover:
            raise ProductGateError(
                "PRODUCT-GATE-TRANSACTION-INCOMPLETE", "run publication lacks its commit marker"
            )
    else:
        _write_exclusive(manifest_path, manifest_bytes)
        _write_exclusive(publication_path, publication_bytes)
    if not stop_before_marker:
        _write_exclusive(marker_path, marker_bytes)
    return {"manifest": manifest_path, "publication": publication_path, "marker": marker_path}


def _mechanics_result(artifact: Path) -> tuple[dict[str, Any], bytes]:
    command = [
        sys.executable,
        str(RUN_ALL),
        str(artifact),
        "--stdout",
        "--skip-d-style-profile",
        "--skip-accessibility",
        "--fail-on",
        "none",
    ]
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode != 0:
        raise ProductGateError("PRODUCT-GATE-MECHANICS-FAILED", result.stderr.decode("utf-8", "replace"))
    return json.loads(result.stdout.decode("utf-8", errors="strict")), result.stdout


def run_gate(
    *,
    mode: str,
    project_root: Path,
    artifact: Path,
    out_dir: Path,
    requested_checks: list[str],
    wiki_root: Path | None = None,
    semantic_receipt: Path | None = None,
    verifier_transaction: Path | None = None,
    verifier_publication_manifest: Path | None = None,
    verifier_commit_marker: Path | None = None,
    semantics_manifest: Path = SEMANTICS,
    recover: bool = False,
    _stop_before_marker: bool = False,
) -> dict[str, Path]:
    project_root = project_root.resolve(strict=True)
    artifact = artifact.resolve(strict=True)
    out_dir = out_dir.resolve()
    checks = sorted(set(requested_checks))
    if not checks:
        raise ProductGateError("PRODUCT-GATE-MODE-MISMATCH", "at least one check is required")
    unknown = sorted(set(checks) - CHECK_VOCABULARY)
    if unknown:
        raise ProductGateError(
            "PRODUCT-GATE-CHECK-UNKNOWN",
            f"unknown requested checks: {', '.join(unknown)}",
        )
    required_check = CHECK_SEMANTIC if mode == "governed-product" else CHECK_DETERMINISTIC
    if required_check not in checks:
        raise ProductGateError(
            "PRODUCT-GATE-MODE-MISMATCH",
            f"{mode} mode requires requested check {required_check}",
        )
    inputs = [_input(artifact, "governed_artifact")]
    verifier_value = None
    omissions: list[dict[str, str]] = []
    dispositions: list[dict[str, str]] = []
    outputs: list[dict[str, str]] = []
    if mode == "mechanics":
        audit, audit_bytes = _mechanics_result(artifact)
        if CHECK_SEMANTIC in checks:
            omissions.append({
                "check": CHECK_SEMANTIC,
                "reason": "mechanics mode is diagnostic and carries no lifecycle authority",
            })
        dispositions.append({
            "check": CHECK_DETERMINISTIC,
            "status": "diagnostic",
            "detail": f"surface audit completed with {len(audit.get('findings', []))} findings",
        })
        outputs.append({
            "kind": "mechanics_stdout",
            "sha256": hashlib.sha256(audit_bytes).hexdigest(),
            "status": "diagnostic",
        })
        lifecycle_eligible = False
        terminal_state = "diagnostic_complete"
    elif mode == "governed-product":
        evidence = (
            wiki_root,
            semantic_receipt,
            verifier_transaction,
            verifier_publication_manifest,
            verifier_commit_marker,
        )
        if any(value is None for value in evidence):
            raise ProductGateError(
                "PRODUCT-GATE-EVIDENCE-REQUIRED",
                "governed-product mode requires semantic and committed verifier evidence",
            )
        try:
            transaction = validate_verifier_transaction(
                transaction=verifier_transaction,
                publication_manifest=verifier_publication_manifest,
                commit_marker=verifier_commit_marker,
                artifact=artifact,
                semantic_receipt=semantic_receipt,
                project_root=project_root,
                wiki_root=wiki_root,
                harness_root=ROOT,
                semantics_manifest=semantics_manifest,
            )
        except (VerifierError, OSError) as exc:
            raise ProductGateError("PRODUCT-GATE-EVIDENCE-REQUIRED", str(exc)) from exc
        if transaction.get("phase") != "evaluation" or transaction.get("product_disposition") != "product_qualified":
            raise ProductGateError(
                "PRODUCT-GATE-EVIDENCE-REQUIRED", "verifier transaction is not product-qualified evaluation"
            )
        for path, kind in (
            (semantic_receipt, "semantic_receipt"),
            (verifier_transaction, "verifier_transaction"),
            (verifier_publication_manifest, "verifier_publication_manifest"),
            (verifier_commit_marker, "verifier_commit_marker"),
            (semantics_manifest, "semantics_manifest"),
            (wiki_root / "manifest.json", "wiki_root_manifest"),
            (project_root / "project_manifest.json", "project_root_manifest"),
        ):
            inputs.append(_input(path, kind))
        verifier_value = {
            "transaction_id": transaction["transaction_id"],
            "phase": transaction["phase"],
            "product_disposition": transaction["product_disposition"],
            "transaction_sha256": sha(verifier_transaction),
            "publication_manifest_sha256": sha(verifier_publication_manifest),
            "commit_marker_sha256": sha(verifier_commit_marker),
        }
        dispositions.append({
            "check": CHECK_SEMANTIC,
            "status": "qualified",
            "detail": "exact committed evaluation transaction validated",
        })
        outputs.append({
            "kind": "verifier_transaction",
            "path": str(verifier_transaction.resolve()),
            "sha256": sha(verifier_transaction),
            "status": "qualified",
        })
        if CHECK_DETERMINISTIC in checks:
            omissions.append({
                "check": CHECK_DETERMINISTIC,
                "reason": "governed-product mode executes the semantic verifier; mechanics is a separate diagnostic run",
            })
        lifecycle_eligible = True
        terminal_state = "product_qualified"
    else:
        raise ProductGateError("PRODUCT-GATE-MODE-MISMATCH", f"unsupported mode: {mode}")
    recovery_command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--recover",
        "--mode",
        mode,
        "--project-root",
        str(project_root),
        "--artifact",
        str(artifact),
        "--out-dir",
        str(out_dir),
    ]
    for check in checks:
        recovery_command.extend(["--check", check])
    if mode == "governed-product":
        recovery_command.extend([
            "--wiki-root",
            str(wiki_root.resolve()),
            "--semantic-receipt",
            str(semantic_receipt.resolve()),
            "--verifier-transaction",
            str(verifier_transaction.resolve()),
            "--verifier-publication-manifest",
            str(verifier_publication_manifest.resolve()),
            "--verifier-commit-marker",
            str(verifier_commit_marker.resolve()),
            "--semantics-manifest",
            str(semantics_manifest.resolve()),
        ])
    seed = {
        "mode": mode,
        "checks": checks,
        "inputs": inputs,
        "verifier": verifier_value,
        "terminal_state": terminal_state,
    }
    manifest = {
        "schema_version": "1.0.0",
        "manifest_type": "product_gate_run",
        "run_id": "product-gate-" + hashlib.sha256(canonical_bytes(seed)).hexdigest()[:16],
        "state": "prepared",
        "mode": mode,
        "lifecycle_eligible": lifecycle_eligible,
        "requested_checks": checks,
        "inputs": inputs,
        "verifier_transaction": verifier_value,
        "runtime_versions": {
            "extractor": {
                key: SUPPORTED_PDF_EXTRACTOR[key]
                for key in ("name", "version", "sha256")
            },
            "detector": {"name": DETECTOR_NAME, "version": DETECTOR_VERSION},
        },
        "omissions": omissions,
        "dispositions": dispositions,
        "outputs": outputs,
        "recovery_command": recovery_command,
        "terminal_state": terminal_state,
    }
    errors = sorted(_validator().iter_errors(manifest), key=lambda error: list(error.path))
    if errors:
        raise ProductGateError("PRODUCT-GATE-MODE-MISMATCH", errors[0].message)
    _validate_check_accounting(manifest)
    return _publish(
        out_dir,
        manifest,
        recover=recover,
        stop_before_marker=_stop_before_marker,
    )


def validate_run_manifest(path: Path, *, require_lifecycle: bool = False) -> dict[str, Any]:
    path = path.resolve(strict=True)
    value = json.loads(path.read_text(encoding="utf-8"))
    errors = sorted(_validator().iter_errors(value), key=lambda error: list(error.path))
    if errors:
        raise ProductGateError("PRODUCT-GATE-MODE-MISMATCH", errors[0].message)
    _validate_check_accounting(value)
    publication_path = path.parent / "publication-manifest.json"
    marker_path = path.parent / "commit-marker.json"
    if not publication_path.is_file() or not marker_path.is_file():
        raise ProductGateError("PRODUCT-GATE-TRANSACTION-INCOMPLETE", "run publication is incomplete")
    publication = json.loads(publication_path.read_text(encoding="utf-8"))
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    if (
        publication.get("transaction_id") != value["run_id"]
        or publication.get("products") != [{"path": path.name, "sha256": sha(path)}]
        or marker.get("transaction_id") != value["run_id"]
        or marker.get("state") != "committed"
        or marker.get("publication_manifest") != publication_path.name
        or marker.get("publication_manifest_sha256") != sha(publication_path)
    ):
        raise ProductGateError("PRODUCT-GATE-RECOVERY-REQUIRED", "run publication bindings differ")
    if require_lifecycle and not value["lifecycle_eligible"]:
        raise ProductGateError(
            "PRODUCT-GATE-MODE-MISMATCH", "mechanics manifest is not lifecycle product evidence"
        )
    resolved_inputs: dict[str, Path] = {}
    try:
        for row in value["inputs"]:
            kind = row["kind"]
            if kind in resolved_inputs:
                raise ValueError(f"duplicate input kind: {kind}")
            current = Path(row["path"]).resolve(strict=True)
            if (
                str(current) != row["path"]
                or not current.is_file()
                or sha(current) != row["sha256"]
                or current.stat().st_size != row["size"]
            ):
                raise ValueError(f"stale input: {kind}")
            resolved_inputs[kind] = current
    except (KeyError, OSError, TypeError, ValueError) as exc:
        raise ProductGateError("PRODUCT-GATE-EVIDENCE-STALE", str(exc)) from exc
    if value["lifecycle_eligible"]:
        if value.get("mode") != "governed-product" or set(resolved_inputs) != GOVERNED_INPUT_KINDS:
            raise ProductGateError(
                "PRODUCT-GATE-EVIDENCE-STALE",
                "governed manifest does not bind the exact required input set",
            )
        try:
            transaction = validate_verifier_transaction(
                transaction=resolved_inputs["verifier_transaction"],
                publication_manifest=resolved_inputs["verifier_publication_manifest"],
                commit_marker=resolved_inputs["verifier_commit_marker"],
                artifact=resolved_inputs["governed_artifact"],
                semantic_receipt=resolved_inputs["semantic_receipt"],
                project_root=resolved_inputs["project_root_manifest"].parent,
                wiki_root=resolved_inputs["wiki_root_manifest"].parent,
                harness_root=ROOT,
                semantics_manifest=resolved_inputs["semantics_manifest"],
            )
        except (VerifierError, OSError, KeyError) as exc:
            raise ProductGateError("PRODUCT-GATE-EVIDENCE-STALE", str(exc)) from exc
        verifier_value = value.get("verifier_transaction") or {}
        if (
            transaction.get("phase") != "evaluation"
            or transaction.get("product_disposition") != "product_qualified"
            or transaction.get("transaction_id") != verifier_value.get("transaction_id")
            or sha(resolved_inputs["verifier_transaction"]) != verifier_value.get("transaction_sha256")
            or sha(resolved_inputs["verifier_publication_manifest"]) != verifier_value.get("publication_manifest_sha256")
            or sha(resolved_inputs["verifier_commit_marker"]) != verifier_value.get("commit_marker_sha256")
        ):
            raise ProductGateError(
                "PRODUCT-GATE-EVIDENCE-STALE",
                "governed verifier replay differs from the committed run manifest",
            )
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("mechanics", "governed-product"), required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--check", action="append", dest="checks", choices=sorted(CHECK_VOCABULARY), default=[])
    parser.add_argument("--wiki-root", type=Path)
    parser.add_argument("--semantic-receipt", type=Path)
    parser.add_argument("--verifier-transaction", type=Path)
    parser.add_argument("--verifier-publication-manifest", type=Path)
    parser.add_argument("--verifier-commit-marker", type=Path)
    parser.add_argument("--semantics-manifest", type=Path, default=SEMANTICS)
    parser.add_argument("--recover", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        paths = run_gate(
            mode=args.mode,
            project_root=args.project_root,
            artifact=args.artifact,
            out_dir=args.out_dir,
            requested_checks=args.checks or [
                CHECK_SEMANTIC if args.mode == "governed-product" else CHECK_DETERMINISTIC
            ],
            wiki_root=args.wiki_root,
            semantic_receipt=args.semantic_receipt,
            verifier_transaction=args.verifier_transaction,
            verifier_publication_manifest=args.verifier_publication_manifest,
            verifier_commit_marker=args.verifier_commit_marker,
            semantics_manifest=args.semantics_manifest,
            recover=args.recover,
        )
    except ProductGateError as exc:
        print(json.dumps({"status": "blocked", "reason_code": exc.code, "detail": exc.message}), file=sys.stderr)
        return 4
    print(json.dumps({"status": "committed", "manifest": str(paths["manifest"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
