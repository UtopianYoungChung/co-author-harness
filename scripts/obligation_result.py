#!/usr/bin/env python3
"""Verify typed obligation outcomes against a closed adapter registry.

This kernel verifies deterministic structure, registry membership, exact-byte
evidence, and adjudication bindings.  It does not make scholarly judgments.
"""

from __future__ import annotations

import copy
from dataclasses import asdict
import hashlib
import hmac
import importlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "references" / "schemas"
RESULT_SCHEMA_PATH = SCHEMA_DIR / "obligation_result.schema.json"
ADJUDICATION_SCHEMA_PATH = SCHEMA_DIR / "obligation_adjudication.schema.json"

PREFIX = "DRAFT-POLICY-OBLIGATION-"
UNKNOWN = PREFIX + "UNKNOWN"
SCHEMA = PREFIX + "SCHEMA"
STALE = PREFIX + "STALE"
BLOCKING_OUTCOME = PREFIX + "BLOCKING-OUTCOME"
ADJUDICATION_MISSING = PREFIX + "ADJUDICATION-MISSING"
ADJUDICATION_STALE = PREFIX + "ADJUDICATION-STALE"

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
OUTCOMES = {"clean", "findings", "error", "not_applicable"}
SEVERITIES = ("ADVISORY", "MINOR", "MAJOR", "BLOCKER")
SEVERITY_RANK = {severity: index for index, severity in enumerate(SEVERITIES)}
PHASES = {"generation", "evaluation"}
RESULT_SCHEMA_REL = "references/schemas/obligation_result.schema.json"
ADJUDICATION_SCHEMA_REL = "references/schemas/obligation_adjudication.schema.json"
GENERIC_REPORT_SCHEMA_REL = RESULT_SCHEMA_REL + "#/$defs/adapterReport"
DSTYLE_REPORT_SCHEMA_REL = "scripts/d_style_profile_check.py"
EXACT_BINDING = "path_sha256_byte_length"


class ObligationResultRefusal(RuntimeError):
    """Typed, frozen refusal from the obligation-result kernel."""

    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


def _refuse(code: str, detail: str) -> None:
    raise ObligationResultRefusal(code, detail)


def _load_schema(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8", errors="strict"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _refuse(SCHEMA, f"cannot load schema {path}: {exc}")
    if not isinstance(value, dict):
        _refuse(SCHEMA, f"schema root must be an object: {path}")
    return value


def _validator() -> Draft202012Validator:
    result_schema = _load_schema(RESULT_SCHEMA_PATH)
    adjudication_schema = _load_schema(ADJUDICATION_SCHEMA_PATH)
    try:
        Draft202012Validator.check_schema(result_schema)
        Draft202012Validator.check_schema(adjudication_schema)
        schema_registry = Registry().with_resource(
            str(adjudication_schema["$id"]),
            Resource.from_contents(adjudication_schema),
        )
        return Draft202012Validator(result_schema, registry=schema_registry)
    except Exception as exc:
        _refuse(SCHEMA, f"Draft 2020-12 schema runtime failed: {exc}")


def _schema_check(result: Any) -> None:
    if not isinstance(result, dict):
        _refuse(SCHEMA, "obligation result must be an object")
    try:
        errors = sorted(
            _validator().iter_errors(result),
            key=lambda error: [str(part) for part in error.absolute_path],
        )
    except Exception as exc:
        _refuse(SCHEMA, f"obligation result schema resolution failed: {exc}")
    if errors:
        error = errors[0]
        location = "/".join(str(part) for part in error.absolute_path) or "$"
        _refuse(SCHEMA, f"schema violation at {location}: {error.message}")


def _closed_object(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        _refuse(SCHEMA, f"{label} must contain exactly {sorted(fields)}")
    return value


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _schema_descriptor(
    value: Any, *, label: str, expected: set[tuple[str, str]]
) -> dict[str, Any]:
    row = _closed_object(value, {"path", "version"}, label)
    if (row.get("path"), row.get("version")) not in expected:
        _refuse(SCHEMA, f"{label} names an unsupported schema/version")
    return row


def _validate_registry(registry: Any) -> dict[str, dict[str, Any]]:
    top = _closed_object(
        registry,
        {"schema_version", "registry_id", "obligations"},
        "obligation registry",
    )
    if top.get("schema_version") != "1.0.0" or not _nonempty(top.get("registry_id")):
        _refuse(SCHEMA, "registry version and registry_id are required")
    obligations = top.get("obligations")
    if not isinstance(obligations, dict):
        _refuse(SCHEMA, "registry obligations must be an object")

    row_fields = {
        "adapter_id",
        "adapter_version",
        "report_schema",
        "allowed_outcomes",
        "blocking_threshold",
        "adjudication_schema",
        "authorized_adjudicators",
        "binding_requirements",
        "diagnostic_only",
        "activation",
        "phases",
    }
    adapters: set[str] = set()
    validated: dict[str, dict[str, Any]] = {}
    for obligation_id, raw_row in obligations.items():
        if not isinstance(obligation_id, str) or not ID_RE.fullmatch(obligation_id):
            _refuse(SCHEMA, f"invalid registry obligation id: {obligation_id!r}")
        row = _closed_object(raw_row, row_fields, f"registry row {obligation_id}")
        adapter_id = row.get("adapter_id")
        if not isinstance(adapter_id, str) or not ID_RE.fullmatch(adapter_id):
            _refuse(SCHEMA, f"invalid adapter_id for {obligation_id}")
        if adapter_id in adapters:
            _refuse(SCHEMA, f"duplicate adapter_id: {adapter_id}")
        adapters.add(adapter_id)
        if not isinstance(row.get("adapter_version"), str) or not SEMVER_RE.fullmatch(
            row["adapter_version"]
        ):
            _refuse(SCHEMA, f"invalid adapter_version for {obligation_id}")
        _schema_descriptor(
            row.get("report_schema"),
            label=f"report_schema for {obligation_id}",
            expected={
                (GENERIC_REPORT_SCHEMA_REL, "1.0.0"),
                (DSTYLE_REPORT_SCHEMA_REL, "1.1.0"),
            },
        )
        if (
            row["report_schema"]["path"] == DSTYLE_REPORT_SCHEMA_REL
            and obligation_id != "d-style-profile"
        ):
            _refuse(SCHEMA, "the package-native D-STYLE adapter is identity-bound")
        _schema_descriptor(
            row.get("adjudication_schema"),
            label=f"adjudication_schema for {obligation_id}",
            expected={(ADJUDICATION_SCHEMA_REL, "1.0.0")},
        )
        outcomes = row.get("allowed_outcomes")
        if (
            not isinstance(outcomes, list)
            or not outcomes
            or any(
                not isinstance(outcome, str) or outcome not in OUTCOMES
                for outcome in outcomes
            )
            or len(set(outcomes)) != len(outcomes)
        ):
            _refuse(SCHEMA, f"allowed_outcomes are invalid for {obligation_id}")
        if row.get("blocking_threshold") not in SEVERITY_RANK:
            _refuse(SCHEMA, f"blocking_threshold is invalid for {obligation_id}")
        authorities = row.get("authorized_adjudicators")
        if (
            not isinstance(authorities, list)
            or not authorities
            or any(not _nonempty(actor) for actor in authorities)
            or len(set(authorities)) != len(authorities)
        ):
            _refuse(SCHEMA, f"authorized_adjudicators are invalid for {obligation_id}")
        requirements = _closed_object(
            row.get("binding_requirements"),
            {"artifact", "policy"},
            f"binding_requirements for {obligation_id}",
        )
        if requirements != {"artifact": EXACT_BINDING, "policy": EXACT_BINDING}:
            _refuse(SCHEMA, f"binding_requirements are invalid for {obligation_id}")
        if not isinstance(row.get("diagnostic_only"), bool):
            _refuse(SCHEMA, f"diagnostic_only must be boolean for {obligation_id}")
        if not isinstance(row.get("activation"), str) or not ID_RE.fullmatch(row["activation"]):
            _refuse(SCHEMA, f"activation predicate is invalid for {obligation_id}")
        phases = row.get("phases")
        if (
            not isinstance(phases, list)
            or not phases
            or any(not isinstance(phase, str) or phase not in PHASES for phase in phases)
            or len(set(phases)) != len(phases)
        ):
            _refuse(SCHEMA, f"phases are invalid for {obligation_id}")
        validated[obligation_id] = row
    return validated


def validate_obligation_registry(
    registry: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Validate the closed registry and return detached keyed adapter rows."""

    return copy.deepcopy(_validate_registry(registry))


def _is_link(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        attributes = getattr(os.lstat(path), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400))


def _safe_binding_path(root: Path, raw: Any, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        _refuse(STALE, f"unsafe {label} path: {raw!r}")
    win32_invalid = frozenset('<>:"\\|?*')
    if any(character in win32_invalid or ord(character) < 0x20 for character in raw):
        _refuse(STALE, f"unsafe {label} path: {raw!r}")
    parts = raw.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        _refuse(STALE, f"unsafe {label} path: {raw!r}")
    reserved_devices = {"con", "prn", "aux", "nul"}
    for part in parts:
        if part != part.rstrip(" ."):
            _refuse(STALE, f"Windows-ambiguous {label} path: {raw!r}")
        device_stem = part.split(".", 1)[0].rstrip(" .").casefold()
        if (
            device_stem in reserved_devices
            or (
                len(device_stem) == 4
                and device_stem[:3] in {"com", "lpt"}
                and device_stem[3] in "123456789"
            )
        ):
            _refuse(STALE, f"reserved Windows device in {label} path: {raw!r}")
    relative = PurePosixPath(raw)
    if relative.is_absolute():
        _refuse(STALE, f"unsafe {label} path: {raw!r}")
    root_real = Path(os.path.realpath(root))
    cursor = root
    for part in relative.parts:
        cursor /= part
        if (cursor.exists() or cursor.is_symlink()) and _is_link(cursor):
            _refuse(STALE, f"{label} path traverses a link or reparse point: {raw}")
    resolved = Path(os.path.realpath(cursor))
    try:
        resolved.relative_to(root_real)
    except ValueError:
        _refuse(STALE, f"{label} path escapes verification root: {raw}")
    return cursor


def _verified_binding_bytes(
    root: Path, binding: Any, label: str, *, code: str = STALE
) -> tuple[Path, bytes]:
    if not isinstance(binding, dict):
        _refuse(code, f"{label} binding is not an object")
    path = _safe_binding_path(root, binding.get("path"), label)
    if not path.is_file() or _is_link(path):
        _refuse(code, f"{label} is missing or not a plain file: {binding.get('path')}")
    try:
        payload = path.read_bytes()
    except OSError as exc:
        _refuse(code, f"cannot read {label}: {exc}")
    if (
        hashlib.sha256(payload).hexdigest() != binding.get("sha256")
        or len(payload) != binding.get("byte_length")
    ):
        _refuse(code, f"{label} binding is stale: {binding.get('path')}")
    return path, payload


def _verify_binding(
    root: Path, binding: Any, label: str, *, code: str = STALE
) -> Path:
    path, _ = _verified_binding_bytes(root, binding, label, code=code)
    return path


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest_value(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def finding_fingerprint(
    obligation_id: str,
    code: str,
    severity: str,
    evidence_identity: str,
    artifact_sha256: str,
) -> str:
    """Return the frozen current-evidence finding identity."""

    return _digest_value(
        {
            "artifact_sha256": artifact_sha256,
            "code": code,
            "evidence_identity": evidence_identity,
            "obligation_id": obligation_id,
            "severity": severity,
        }
    )


def _load_bound_json(
    root: Path, binding: Any, label: str, *, code: str = STALE
) -> tuple[Path, dict[str, Any]]:
    path, payload = _verified_binding_bytes(root, binding, label, code=code)
    try:
        value = json.loads(payload.decode("utf-8", errors="strict"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        _refuse(code, f"{label} is not valid JSON: {exc}")
    if not isinstance(value, dict):
        _refuse(code, f"{label} JSON root must be an object")
    return path, value


def _authenticate_envelope(
    root: Path,
    envelope_binding: Any,
    *,
    receipt_type: str,
    expected_subject: dict[str, Any] | None,
    artifact: dict[str, Any],
    code: str,
    test_authority_adapter: Any | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _, envelope = _load_bound_json(root, envelope_binding, receipt_type, code=code)
    common = {
        "schema_version", "receipt_type", "authority_mode", "authority", "subject"
    }
    mode = envelope.get("authority_mode")
    expected_fields = (
        common | {"claim", "consumption"}
        if mode == "assignment_dispatch"
        else common | {"authenticator"}
        if mode == "fixture_hmac" and test_authority_adapter is not None
        else set()
    )
    if (
        not expected_fields
        or set(envelope) != expected_fields
        or envelope.get("schema_version") != "1.0.0"
        or envelope.get("receipt_type") != receipt_type
        or not _nonempty(envelope.get("authority"))
        or not isinstance(envelope.get("subject"), dict)
    ):
        _refuse(code, f"{receipt_type} envelope is malformed")
    subject_binding = envelope["subject"]
    if expected_subject is not None and subject_binding != expected_subject:
        _refuse(code, f"{receipt_type} binds another subject")
    _, subject = _load_bound_json(root, subject_binding, f"{receipt_type} subject", code=code)

    if mode == "fixture_hmac":
        authenticator = envelope.get("authenticator")
        expected_identity = {
            "issuer": getattr(test_authority_adapter, "issuer", None),
            "tool": getattr(test_authority_adapter, "tool", None),
            "version": getattr(test_authority_adapter, "version", None),
        }
        if not isinstance(authenticator, dict) or set(authenticator) != {
            "issuer", "tool", "version", "digest"
        } or {key: authenticator.get(key) for key in expected_identity} != expected_identity:
            _refuse(code, "fixture authority identity is malformed")
        try:
            unsigned = {key: value for key, value in envelope.items() if key != "authenticator"}
            valid = test_authority_adapter.verify(unsigned, authenticator.get("digest"))
        except Exception as exc:
            _refuse(code, f"fixture authority verification failed: {exc}")
        if not valid:
            _refuse(code, "fixture authority authenticator does not verify")
        return envelope, subject

    claim_path, claim_payload = _verified_binding_bytes(
        root, envelope["claim"], "dispatch claim", code=code
    )
    consumption_path, consumption_payload = _verified_binding_bytes(
        root, envelope["consumption"], "dispatch consumption", code=code
    )
    try:
        claim_value = json.loads(claim_payload.decode("utf-8", errors="strict"))
        dispatch = importlib.import_module("assignment_dispatch_claim")
        _, consumption = dispatch.validate_consumed_claim_for_context(
            root,
            claim_path,
            consumption_path,
            expected_role="evaluator",
            expected_target=artifact["path"],
            expected_receipt_id=claim_value.get("receipt_id"),
            expected_artifact_sha256=artifact["sha256"],
        )
    except Exception as exc:
        _refuse(code, f"assignment-dispatch authority does not validate: {exc}")
    _, claim_after = _verified_binding_bytes(
        root, envelope["claim"], "dispatch claim after validation", code=code
    )
    _, consumption_after = _verified_binding_bytes(
        root,
        envelope["consumption"],
        "dispatch consumption after validation",
        code=code,
    )
    if claim_after != claim_payload or consumption_after != consumption_payload:
        _refuse(code, "assignment-dispatch authority bytes changed during validation")
    postimage = next(
        (
            row
            for row in consumption.get("postimages", [])
            if row.get("path") == subject_binding.get("path")
        ),
        None,
    )
    if not isinstance(postimage, dict) or (
        postimage.get("sha256") != subject_binding.get("sha256")
        or postimage.get("size") != subject_binding.get("byte_length")
    ):
        _refuse(code, "dispatch consumption does not authorize the exact subject postimage")
    return envelope, subject


def _validate_fingerprints(result: dict[str, Any]) -> None:
    for finding in result["findings"]:
        expected = finding_fingerprint(
            result["obligation_id"],
            finding["code"],
            finding["severity"],
            finding["evidence_identity"],
            result["artifact"]["sha256"],
        )
        if not hmac.compare_digest(finding["fingerprint"], expected):
            _refuse(STALE, f"finding fingerprint is stale: {finding['code']}")


def _adapter_report_validator() -> Draft202012Validator:
    schema = _load_schema(RESULT_SCHEMA_PATH)
    adapter_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$ref": "#/$defs/adapterReport",
        "$defs": schema["$defs"],
    }
    return Draft202012Validator(adapter_schema)


def _generic_report_adapter(
    result: dict[str, Any],
    adapter: dict[str, Any],
    root: Path,
    test_authority_adapter: Any | None,
) -> None:
    _, report = _load_bound_json(root, result["report"], "obligation adapter report")
    errors = sorted(
        _adapter_report_validator().iter_errors(report),
        key=lambda error: [str(part) for part in error.absolute_path],
    )
    if errors:
        _refuse(SCHEMA, f"adapter report schema violation: {errors[0].message}")
    expected = {
        "schema_version": result["schema_version"],
        "report_type": "obligation_adapter_report",
        "adapter_id": adapter["adapter_id"],
        "adapter_version": result["adapter_version"],
        "obligation_id": result["obligation_id"],
        "artifact": result["artifact"],
        "policy": result["policy"],
        "activation": result["activation"],
        "execution_status": result["execution_status"],
        "outcome": result["outcome"],
        "findings": result["findings"],
        "diagnostic_only": result["diagnostic_only"],
        "created_at": result["created_at"],
    }
    if report != expected:
        _refuse(STALE, "typed result does not exactly mirror its adapter report")
    receipt = result.get("verifier_receipt")
    if not isinstance(receipt, dict):
        _refuse(SCHEMA, "generic adapter result requires verifier_receipt")
    envelope, _ = _authenticate_envelope(
        root,
        receipt,
        receipt_type="obligation_verifier_authority",
        expected_subject=result["report"],
        artifact=result["artifact"],
        code=STALE,
        test_authority_adapter=test_authority_adapter,
    )
    authority = envelope["authority"]
    authorized = authority in adapter["authorized_adjudicators"]
    if not authorized:
        _refuse(STALE, "generic report issuer is not authorized by the registry")


def _dstyle_evidence_identity(finding: dict[str, Any]) -> str:
    return _digest_value(
        {
            "field": finding.get("field"),
            "locator": finding.get("locator"),
            "message": finding.get("message"),
        }
    )


def _dstyle_report_from_snapshots(
    dstyle: Any,
    root: Path,
    directives_path: Path,
    directives_exists: bool,
    directives_text: str | None,
    artifact_path: Path,
    artifact_text: str,
) -> dict[str, Any]:
    if directives_exists:
        raw_profile, profile_declared = dstyle.parse_profile(directives_text)
    else:
        raw_profile = {}
        profile_declared = False
    resolved = dstyle.resolve_profile(raw_profile)
    findings = dstyle.validate_profile(raw_profile, resolved, profile_declared)
    findings.extend(
        dstyle.validate_substantive_surfaces(
            resolved, artifact_text, root, artifact_path
        )
    )
    return {
        "schema_version": "1.1.0",
        "check": "d_style_profile",
        "project_root": str(root),
        "directives_path": str(directives_path),
        "manuscript_path": str(artifact_path),
        "directives_exists": directives_exists,
        "profile_declared": profile_declared,
        "raw_profile": raw_profile,
        "resolved_profile": resolved,
        "active_obligations": dstyle.build_obligations(resolved),
        "surface_findings": dstyle.surface_finding_codes(findings),
        "findings": [asdict(finding) for finding in findings],
        "verdict": dstyle.verdict(findings),
    }


def _dstyle_report_adapter(
    result: dict[str, Any],
    adapter: dict[str, Any],
    root: Path,
    artifact_path: Path,
    artifact_payload: bytes,
) -> None:
    if result.get("verifier_receipt") is not None:
        _refuse(SCHEMA, "package-native D-STYLE results forbid verifier_receipt")
    _, observed = _load_bound_json(root, result["report"], "D-STYLE report")
    directives_path = root / "research_notes" / "directives.md"
    directives_exists = directives_path.exists()
    directives_payload: bytes | None = None
    try:
        artifact_text = artifact_payload.decode("utf-8", errors="strict")
        if directives_exists:
            if not directives_path.is_file() or _is_link(directives_path):
                _refuse(STALE, "D-STYLE directives are not a plain file")
            directives_payload = directives_path.read_bytes()
            directives_text = directives_payload.decode("utf-8", errors="strict")
        else:
            directives_text = None
        dstyle = importlib.import_module("d_style_profile_check")
        recomputed = _dstyle_report_from_snapshots(
            dstyle,
            root,
            directives_path,
            directives_exists,
            directives_text,
            artifact_path,
            artifact_text,
        )
    except ObligationResultRefusal:
        raise
    except Exception as exc:
        _refuse(STALE, f"D-STYLE report recomputation failed: {exc}")
    _, artifact_after = _verified_binding_bytes(
        root, result["artifact"], "D-STYLE artifact after recomputation"
    )
    if artifact_after != artifact_payload:
        _refuse(STALE, "D-STYLE artifact bytes changed during recomputation")
    if directives_path.exists() is not directives_exists:
        _refuse(STALE, "D-STYLE directives existence changed during recomputation")
    if directives_exists:
        if not directives_path.is_file() or _is_link(directives_path):
            _refuse(STALE, "D-STYLE directives changed type during recomputation")
        try:
            directives_after = directives_path.read_bytes()
        except OSError as exc:
            _refuse(STALE, f"cannot replay D-STYLE directives bytes: {exc}")
        if directives_after != directives_payload:
            _refuse(STALE, "D-STYLE directives bytes changed during recomputation")
    if observed != recomputed:
        _refuse(STALE, "bound D-STYLE report differs from current-byte recomputation")
    expected_findings: list[dict[str, Any]] = []
    for finding in recomputed.get("findings", []):
        severity = finding.get("severity")
        if severity not in SEVERITY_RANK:
            continue
        evidence_identity = _dstyle_evidence_identity(finding)
        expected_findings.append(
            {
                "code": finding.get("code"),
                "severity": severity,
                "evidence_identity": evidence_identity,
                "fingerprint": finding_fingerprint(
                    result["obligation_id"],
                    finding.get("code"),
                    severity,
                    evidence_identity,
                    result["artifact"]["sha256"],
                ),
            }
        )
    observed_findings = [
        {key: row[key] for key in ("code", "severity", "evidence_identity", "fingerprint")}
        for row in result["findings"]
    ]
    expected_outcome = "findings" if expected_findings else "clean"
    if (
        observed_findings != expected_findings
        or result["outcome"] != expected_outcome
        or result["execution_status"] != "completed"
    ):
        _refuse(STALE, "typed D-STYLE outcome/findings differ from recomputed report")


def _verify_report_adapter(
    result: dict[str, Any],
    adapter: dict[str, Any],
    root: Path,
    artifact_path: Path,
    artifact_payload: bytes,
    test_authority_adapter: Any | None,
) -> None:
    report_path = adapter["report_schema"]["path"]
    if report_path == DSTYLE_REPORT_SCHEMA_REL:
        _dstyle_report_adapter(
            result, adapter, root, artifact_path, artifact_payload
        )
    elif report_path == GENERIC_REPORT_SCHEMA_REL:
        _generic_report_adapter(result, adapter, root, test_authority_adapter)
    else:
        _refuse(SCHEMA, f"no verifier dispatch for adapter {adapter['adapter_id']}")


def _validate_activation(
    result: dict[str, Any],
    adapter: dict[str, Any],
    root: Path,
    test_authority_adapter: Any | None,
) -> None:
    predicate = adapter["activation"]
    observed = result["activation"]
    outcome = result["outcome"]
    if outcome != "not_applicable":
        if observed != predicate:
            _refuse(SCHEMA, "result activation does not bind the registered active predicate")
        return
    if predicate == "always" or observed != f"not:{predicate}":
        _refuse(
            BLOCKING_OUTCOME,
            "not_applicable requires the registered conditional activation predicate to be false",
        )
    proof_binding = result.get("activation_proof")
    if not isinstance(proof_binding, dict):
        _refuse(SCHEMA, "conditional not_applicable requires activation_proof")
    envelope, subject = _authenticate_envelope(
        root,
        proof_binding,
        receipt_type="obligation_activation_authority",
        expected_subject=None,
        artifact=result["artifact"],
        code=STALE,
        test_authority_adapter=test_authority_adapter,
    )
    subject_fields = {
        "schema_version", "subject_type", "adapter_id", "adapter_version",
        "obligation_id", "predicate", "artifact", "policy", "inputs", "active",
    }
    if (
        set(subject) != subject_fields
        or subject.get("schema_version") != "1.0.0"
        or subject.get("subject_type") != "obligation_activation_evaluation"
        or subject.get("adapter_id") != adapter["adapter_id"]
        or subject.get("adapter_version") != adapter["adapter_version"]
        or subject.get("obligation_id") != result["obligation_id"]
        or subject.get("predicate") != predicate
        or subject.get("artifact") != result["artifact"]
        or subject.get("policy") != result["policy"]
        or not isinstance(subject.get("inputs"), list)
        or len(subject["inputs"]) != 1
        or not isinstance(subject.get("active"), bool)
    ):
        _refuse(STALE, "activation evaluation subject is malformed or stale")
    _, context = _load_bound_json(
        root, subject["inputs"][0], "activation context", code=STALE
    )
    if (
        set(context) != {
            "schema_version", "context_type", "artifact", "policy", "predicates"
        }
        or context.get("schema_version") != "1.0.0"
        or context.get("context_type") != "obligation_activation_context"
        or context.get("artifact") != result["artifact"]
        or context.get("policy") != result["policy"]
        or not isinstance(context.get("predicates"), dict)
        or set(context["predicates"]) != {predicate}
        or not isinstance(context["predicates"].get(predicate), bool)
    ):
        _refuse(STALE, "activation context is malformed or does not bind the predicate")
    recomputed = context["predicates"][predicate]
    if subject["active"] is not recomputed or recomputed is not False:
        _refuse(BLOCKING_OUTCOME, "activation proof does not recompute predicate=false")
    if envelope["authority"] not in adapter["authorized_adjudicators"]:
        _refuse(STALE, "activation proof issuer is not registry-authorized")


def _validate_adjudications(
    result: dict[str, Any],
    adapter: dict[str, Any],
    root: Path,
    test_authority_adapter: Any | None,
) -> dict[str, dict[str, Any]]:
    findings = result["findings"]
    by_fingerprint: dict[str, dict[str, Any]] = {}
    for finding in findings:
        fingerprint = finding["fingerprint"]
        if fingerprint in by_fingerprint:
            _refuse(SCHEMA, f"duplicate finding fingerprint: {fingerprint}")
        by_fingerprint[fingerprint] = finding

    adjudications = result.get("adjudications", [])
    ids: set[str] = set()
    bound: dict[str, dict[str, Any]] = {}
    for adjudication in adjudications:
        adjudication_id = adjudication["adjudication_id"]
        fingerprint = adjudication["finding_fingerprint"]
        if adjudication_id in ids or fingerprint in bound:
            _refuse(ADJUDICATION_STALE, "duplicate adjudication id or finding binding")
        ids.add(adjudication_id)
        finding = by_fingerprint.get(fingerprint)
        if finding is None:
            _refuse(ADJUDICATION_STALE, f"orphan adjudication: {adjudication_id}")
        if adjudication["obligation_id"] != result["obligation_id"]:
            _refuse(ADJUDICATION_STALE, f"cross-obligation adjudication: {adjudication_id}")
        if (
            adjudication["disposition"] != finding["disposition"]
            and not (
                finding["disposition"] == "open"
                and adjudication["disposition"] == "resolved"
            )
        ):
            _refuse(ADJUDICATION_STALE, f"adjudication disposition is stale: {adjudication_id}")
        if adjudication["authority"] not in adapter["authorized_adjudicators"]:
            _refuse(ADJUDICATION_STALE, f"unauthorized adjudicator: {adjudication_id}")
        if adjudication["created_at"] < result["created_at"]:
            _refuse(ADJUDICATION_STALE, f"adjudication predates its result: {adjudication_id}")
        if adjudication["artifact"] != result["artifact"]:
            _refuse(ADJUDICATION_STALE, f"adjudication artifact binding is stale: {adjudication_id}")
        _verify_binding(
            root,
            adjudication["artifact"],
            f"adjudication {adjudication_id} artifact",
            code=ADJUDICATION_STALE,
        )
        envelope, subject = _authenticate_envelope(
            root,
            adjudication["authority_receipt"],
            receipt_type="obligation_adjudication_authority",
            expected_subject=None,
            artifact=result["artifact"],
            code=ADJUDICATION_STALE,
            test_authority_adapter=test_authority_adapter,
        )
        adjudication_payload = {
            key: value
            for key, value in adjudication.items()
            if key != "authority_receipt"
        }
        expected_subject = {
            "schema_version": "1.0.0",
            "subject_type": "obligation_adjudication_authorization",
            "authority": adjudication["authority"],
            "adjudication_payload_sha256": _digest_value(adjudication_payload),
            "obligation_id": result["obligation_id"],
            "finding_fingerprint": fingerprint,
            "artifact": result["artifact"],
        }
        if subject != expected_subject or envelope["authority"] != adjudication["authority"]:
            _refuse(
                ADJUDICATION_STALE,
                f"adjudication authority receipt does not bind payload: {adjudication_id}",
            )
        if adjudication["disposition"] == "resolved":
            verification = adjudication["resolution_verification"]
            if (
                verification["artifact_sha256"] != result["artifact"]["sha256"]
                or verification["artifact_byte_length"] != result["artifact"]["byte_length"]
                or verification["finding_fingerprint"] != fingerprint
                or verification["verified"] is not True
            ):
                _refuse(
                    ADJUDICATION_STALE,
                    f"resolution verification is stale: {adjudication_id}",
                )
        bound[fingerprint] = adjudication
    return bound


def verify_obligation_result(
    result: dict[str, Any],
    registry: dict[str, Any],
    *,
    root: Path | str = ROOT,
    _test_authority_adapter: Any | None = None,
) -> dict[str, Any]:
    """Verify one result, returning lifecycle eligibility or a typed refusal."""

    _schema_check(result)
    adapters = _validate_registry(registry)
    obligation_id = result["obligation_id"]
    adapter = adapters.get(obligation_id)
    if adapter is None:
        _refuse(UNKNOWN, f"obligation is not registered: {obligation_id}")
    if (
        result["adapter_version"] != adapter["adapter_version"]
        or result["outcome"] not in adapter["allowed_outcomes"]
        or result["diagnostic_only"] is not adapter["diagnostic_only"]
    ):
        _refuse(SCHEMA, "result does not conform to its registered adapter policy")

    verification_root = Path(root).absolute()
    if not verification_root.is_dir() or _is_link(verification_root):
        _refuse(STALE, "verification root is absent, not a directory, or a link")
    artifact_path, artifact_payload = _verified_binding_bytes(
        verification_root, result["artifact"], "artifact"
    )
    _verify_binding(verification_root, result["policy"], "policy")
    _verify_binding(verification_root, result["report"], "report")
    legacy = result.get("legacy_execution_evidence")
    if legacy is not None:
        for index, binding in enumerate(legacy["evidence"]):
            _verify_binding(
                verification_root,
                binding,
                f"legacy execution evidence {index}",
            )

    _validate_fingerprints(result)
    _verify_report_adapter(
        result,
        adapter,
        verification_root,
        artifact_path,
        artifact_payload,
        _test_authority_adapter,
    )
    _validate_activation(
        result, adapter, verification_root, _test_authority_adapter
    )
    adjudications = _validate_adjudications(
        result, adapter, verification_root, _test_authority_adapter
    )
    threshold = SEVERITY_RANK[adapter["blocking_threshold"]]
    blocking = [
        finding
        for finding in result["findings"]
        if SEVERITY_RANK[finding["severity"]] >= threshold
    ]
    for finding in blocking:
        disposition = finding["disposition"]
        adjudication = adjudications.get(finding["fingerprint"])
        if adjudication is not None and adjudication["disposition"] == "resolved":
            continue
        if disposition == "resolved":
            if adjudication is None:
                _refuse(
                    ADJUDICATION_MISSING,
                    f"resolved blocking finding lacks current adjudication: {finding['fingerprint']}",
                )
        if disposition in {"acknowledged", "escalated", "refused"} and adjudication is None:
            _refuse(
                ADJUDICATION_MISSING,
                f"blocking disposition lacks adjudication: {finding['fingerprint']}",
            )
        if result["diagnostic_only"]:
            continue
        _refuse(
            BLOCKING_OUTCOME,
            f"{finding['severity']} finding remains blocking with disposition {disposition}",
        )

    if result["outcome"] == "error" and not result["diagnostic_only"]:
        _refuse(BLOCKING_OUTCOME, "error outcome cannot qualify lifecycle state")

    lifecycle_eligible = not result["diagnostic_only"]
    return {
        "schema_version": "1.0.0",
        "status": "verified",
        "obligation_id": obligation_id,
        "execution_status": result["execution_status"],
        "outcome": result["outcome"],
        "diagnostic_only": result["diagnostic_only"],
        "lifecycle_eligible": lifecycle_eligible,
        "blocking_fingerprints": [
            finding["fingerprint"] for finding in blocking
        ],
        "findings": [],
    }


__all__ = [
    "ObligationResultRefusal",
    "finding_fingerprint",
    "validate_obligation_registry",
    "verify_obligation_result",
    "UNKNOWN",
    "SCHEMA",
    "STALE",
    "BLOCKING_OUTCOME",
    "ADJUDICATION_MISSING",
    "ADJUDICATION_STALE",
]
