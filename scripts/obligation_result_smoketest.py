#!/usr/bin/env python3
"""C1 red boundary for typed obligation outcomes and adjudication.

The future production module must expose ``verify_obligation_result(result,
registry, root=...)``.  A refusal exception carries ``code``; an eligible clean
twin returns a mapping with no findings.  Fixtures use actual short,
self-authored artifact and policy bytes under a temporary synthetic root.
"""

from __future__ import annotations

import copy
import hashlib
import hmac
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = ROOT / "scripts" / "obligation_result.py"
API = "verify_obligation_result"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


ARTIFACT_TEXT = "Synthetic scholarly paragraph.\n"
POLICY_TEXT = '{"policy_id":"synthetic-d-style","schema_version":"1.0.0"}\n'
GENERIC_REPORT_SCHEMA = (
    "references/schemas/obligation_result.schema.json#/$defs/adapterReport"
)
EVIDENCE_IDENTITY = "synthetic-span-1"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


class InjectedTestAuthorityAdapter:
    """Test-only authority seam; production callers never receive this object."""

    issuer = "obligation_result_smoketest"
    tool = "injected_test_authority_adapter"
    version = "1.0.0"
    _key = b"obligation-result-smoketest-only-authority-key"

    def digest(self, unsigned: dict[str, Any]) -> str:
        return hmac.new(self._key, _canonical(unsigned), hashlib.sha256).hexdigest()

    def verify(self, unsigned: dict[str, Any], digest: Any) -> bool:
        return isinstance(digest, str) and hmac.compare_digest(
            self.digest(unsigned), digest
        )


TEST_AUTHORITY_ADAPTER = InjectedTestAuthorityAdapter()


def _fingerprint(
    obligation_id: str,
    code: str,
    severity: str,
    evidence_identity: str,
    artifact_sha256: str,
) -> str:
    return hashlib.sha256(
        _canonical(
            {
                "artifact_sha256": artifact_sha256,
                "code": code,
                "evidence_identity": evidence_identity,
                "obligation_id": obligation_id,
                "severity": severity,
            }
        )
    ).hexdigest()


FINDING_FINGERPRINT = _fingerprint(
    "d-style-profile",
    "DSTYLE-SYNTHETIC-MAJOR",
    "MAJOR",
    EVIDENCE_IDENTITY,
    _sha(ARTIFACT_TEXT),
)


def _placeholder(path: str) -> dict[str, Any]:
    return {"path": path, "sha256": "0" * 64, "byte_length": 0}


def _registry() -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "registry_id": "synthetic-obligation-registry",
        "obligations": {
            "d-style-profile": {
                "adapter_id": "d-style-profile-adapter",
                "adapter_version": "1.0.0",
                "report_schema": {
                    "path": GENERIC_REPORT_SCHEMA,
                    "version": "1.0.0",
                },
                "allowed_outcomes": ["clean", "findings", "error", "not_applicable"],
                "blocking_threshold": "MAJOR",
                "adjudication_schema": {
                    "path": "references/schemas/obligation_adjudication.schema.json",
                    "version": "1.0.0",
                },
                "authorized_adjudicators": [
                    "synthetic-independent-evaluator",
                    "synthetic-escalation-owner",
                ],
                "binding_requirements": {
                    "artifact": "path_sha256_byte_length",
                    "policy": "path_sha256_byte_length",
                },
                "diagnostic_only": False,
                "activation": "always",
                "phases": ["generation", "evaluation"],
            }
        },
    }


def _applied_major_result() -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "obligation_id": "d-style-profile",
        "adapter_version": "1.0.0",
        "artifact": {
            "path": "synthetic/M1.md",
            "sha256": _sha(ARTIFACT_TEXT),
            "byte_length": len(ARTIFACT_TEXT.encode("utf-8")),
        },
        "policy": {
            "path": "synthetic/d-style-policy.json",
            "sha256": _sha(POLICY_TEXT),
            "byte_length": len(POLICY_TEXT.encode("utf-8")),
        },
        "report": _placeholder("synthetic/reports/pending.json"),
        "verifier_receipt": _placeholder("synthetic/authority/pending-verifier.json"),
        "activation": "always",
        "execution_status": "completed",
        "legacy_execution_evidence": {
            "status": "applied",
            "evidence": [
                {
                    "path": "synthetic/d-style-report.json",
                    "sha256": _sha("synthetic applied D-STYLE report\n"),
                    "byte_length": len("synthetic applied D-STYLE report\n".encode("utf-8")),
                }
            ],
            "rationale": "The legacy runner executed; this is not a pass verdict.",
        },
        "outcome": "findings",
        "findings": [
            {
                "code": "DSTYLE-SYNTHETIC-MAJOR",
                "severity": "MAJOR",
                "evidence_identity": EVIDENCE_IDENTITY,
                "fingerprint": FINDING_FINGERPRINT,
                "disposition": "open",
            }
        ],
        "diagnostic_only": False,
        "created_at": "2026-07-26T00:00:00Z",
        "adjudications": [],
    }


def _current_resolution() -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "adjudication_id": "synthetic-dstyle-resolution",
        "obligation_id": "d-style-profile",
        "finding_fingerprint": FINDING_FINGERPRINT,
        "artifact": {
            "path": "synthetic/M1.md",
            "sha256": _sha(ARTIFACT_TEXT),
            "byte_length": len(ARTIFACT_TEXT.encode("utf-8")),
        },
        "disposition": "resolved",
        "authority": "synthetic-independent-evaluator",
        "authority_receipt": _placeholder(
            "synthetic/authority/pending-adjudication.json"
        ),
        "rationale": "The current synthetic bytes were independently rechecked.",
        "resolution_verification": {
            "artifact_sha256": _sha(ARTIFACT_TEXT),
            "artifact_byte_length": len(ARTIFACT_TEXT.encode("utf-8")),
            "finding_fingerprint": FINDING_FINGERPRINT,
            "verified": True,
        },
        "created_at": "2026-07-26T00:01:00Z",
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
    spec = importlib.util.spec_from_file_location("obligation_result", PRODUCTION)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json_binding(root: Path, relative: str, value: dict[str, Any]) -> dict[str, Any]:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _canonical(value)
    path.write_bytes(payload)
    return {
        "path": relative,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "byte_length": len(payload),
    }


def _fixture_envelope(
    root: Path,
    *,
    receipt_type: str,
    authority: str,
    subject: dict[str, Any],
    token: str,
) -> dict[str, Any]:
    unsigned = {
        "schema_version": "1.0.0",
        "receipt_type": receipt_type,
        "authority_mode": "fixture_hmac",
        "authority": authority,
        "subject": subject,
    }
    adapter = TEST_AUTHORITY_ADAPTER
    envelope = {
        **unsigned,
        "authenticator": {
            "issuer": adapter.issuer,
            "tool": adapter.tool,
            "version": adapter.version,
            "digest": adapter.digest(unsigned),
        },
    }
    return _write_json_binding(
        root,
        f"synthetic/authority/{receipt_type}-{token}.json",
        envelope,
    )


def _materialize_result(
    root: Path, result: dict[str, Any], registry: dict[str, Any]
) -> None:
    adapter = registry.get("obligations", {}).get(result.get("obligation_id"))
    if not isinstance(adapter, dict):
        return
    authority = adapter.get("authorized_adjudicators", [
        "synthetic-independent-evaluator"
    ])[0]
    if adapter.get("report_schema", {}).get("path") == GENERIC_REPORT_SCHEMA:
        report = {
            "schema_version": result.get("schema_version"),
            "report_type": "obligation_adapter_report",
            "adapter_id": adapter.get("adapter_id"),
            "adapter_version": result.get("adapter_version"),
            "obligation_id": result.get("obligation_id"),
            "artifact": copy.deepcopy(result.get("artifact")),
            "policy": copy.deepcopy(result.get("policy")),
            "activation": result.get("activation"),
            "execution_status": result.get("execution_status"),
            "outcome": result.get("outcome"),
            "findings": copy.deepcopy(result.get("findings")),
            "diagnostic_only": result.get("diagnostic_only"),
            "created_at": result.get("created_at"),
        }
        token = hashlib.sha256(_canonical(report)).hexdigest()[:16]
        result["report"] = _write_json_binding(
            root, f"synthetic/reports/{token}.json", report
        )
        result["verifier_receipt"] = _fixture_envelope(
            root,
            receipt_type="obligation_verifier_authority",
            authority=authority,
            subject=result["report"],
            token=token,
        )

    for adjudication in result.get("adjudications", []):
        payload = {
            key: copy.deepcopy(value)
            for key, value in adjudication.items()
            if key != "authority_receipt"
        }
        subject = {
            "schema_version": "1.0.0",
            "subject_type": "obligation_adjudication_authorization",
            "authority": adjudication.get("authority"),
            "adjudication_payload_sha256": hashlib.sha256(
                _canonical(payload)
            ).hexdigest(),
            "obligation_id": result.get("obligation_id"),
            "finding_fingerprint": adjudication.get("finding_fingerprint"),
            "artifact": copy.deepcopy(result.get("artifact")),
        }
        token = hashlib.sha256(_canonical(subject)).hexdigest()[:16]
        subject_binding = _write_json_binding(
            root, f"synthetic/authority/adjudication-subject-{token}.json", subject
        )
        adjudication["authority_receipt"] = _fixture_envelope(
            root,
            receipt_type="obligation_adjudication_authority",
            authority=adjudication.get("authority"),
            subject=subject_binding,
            token=token,
        )

    if result.get("outcome") == "not_applicable":
        predicate = adapter.get("activation")
        active = result.get("activation") != f"not:{predicate}"
        context = {
            "schema_version": "1.0.0",
            "context_type": "obligation_activation_context",
            "artifact": copy.deepcopy(result.get("artifact")),
            "policy": copy.deepcopy(result.get("policy")),
            "predicates": {predicate: active},
        }
        token = hashlib.sha256(_canonical(context)).hexdigest()[:16]
        context_binding = _write_json_binding(
            root, f"synthetic/activation/context-{token}.json", context
        )
        subject = {
            "schema_version": "1.0.0",
            "subject_type": "obligation_activation_evaluation",
            "adapter_id": adapter.get("adapter_id"),
            "adapter_version": adapter.get("adapter_version"),
            "obligation_id": result.get("obligation_id"),
            "predicate": predicate,
            "artifact": copy.deepcopy(result.get("artifact")),
            "policy": copy.deepcopy(result.get("policy")),
            "inputs": [context_binding],
            "active": active,
        }
        subject_binding = _write_json_binding(
            root, f"synthetic/activation/subject-{token}.json", subject
        )
        result["activation_proof"] = _fixture_envelope(
            root,
            receipt_type="obligation_activation_authority",
            authority=authority,
            subject=subject_binding,
            token=token,
        )


def _prepared(
    root: Path, result: dict[str, Any], registry: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    prepared_result = copy.deepcopy(result)
    prepared_registry = copy.deepcopy(registry)
    _materialize_result(root, prepared_result, prepared_registry)
    return prepared_result, prepared_registry


def _observe(
    module: Any,
    result: dict[str, Any],
    registry: dict[str, Any],
    root: Path,
) -> tuple[str | None, list[Any]]:
    function = getattr(module, API, None)
    if not callable(function):
        return "INTERFACE_BLOCKED", []
    prepared_result, prepared_registry = _prepared(root, result, registry)
    try:
        receipt = function(
            prepared_result,
            prepared_registry,
            root=root,
            _test_authority_adapter=TEST_AUTHORITY_ADAPTER,
        )
    except Exception as exc:
        return getattr(exc, "code", type(exc).__name__), []
    if not isinstance(receipt, dict):
        return "INTERFACE_INVALID", []
    findings = receipt.get("findings", [])
    return None, findings if isinstance(findings, list) else ["findings-not-array"]


def _verify_current_binding(root: Path, binding: dict[str, Any], label: str) -> None:
    path = root / binding["path"]
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != binding["sha256"]:
        raise AssertionError(f"{label} hash does not bind current bytes")
    if len(data) != binding["byte_length"]:
        raise AssertionError(f"{label} length does not bind current bytes")


def _expect_code(expected: str, function: Any, *args: Any, **kwargs: Any) -> None:
    prepare_fixture = kwargs.pop("_prepare_fixture", True)
    inject_test_authority = kwargs.pop("_inject_test_authority", True)
    if prepare_fixture and getattr(function, "__name__", "") == API and len(args) >= 2:
        root = Path(kwargs["root"])
        prepared = _prepared(root, args[0], args[1])
        args = (*prepared, *args[2:])
    if inject_test_authority and getattr(function, "__name__", "") == API:
        kwargs.setdefault("_test_authority_adapter", TEST_AUTHORITY_ADAPTER)
    try:
        function(*args, **kwargs)
    except Exception as exc:
        observed = getattr(exc, "code", type(exc).__name__)
        if observed != expected:
            raise AssertionError(
                f"expected {expected}, observed {observed}: {exc}"
            ) from exc
        return
    raise AssertionError(f"expected refusal {expected}")


def _clean_result() -> dict[str, Any]:
    result = _applied_major_result()
    result["outcome"] = "clean"
    result["findings"] = []
    result["adjudications"] = []
    return result


def _finding_result(
    severity: str,
    *,
    disposition: str = "open",
    token: str | None = None,
) -> dict[str, Any]:
    result = _applied_major_result()
    token = token or f"synthetic-{severity.lower()}-{disposition}"
    evidence_identity = _sha(token)
    fingerprint = _fingerprint(
        result["obligation_id"],
        f"SYNTHETIC-{severity}",
        severity,
        evidence_identity,
        result["artifact"]["sha256"],
    )
    result["findings"] = [
        {
            "code": f"SYNTHETIC-{severity}",
            "severity": severity,
            "evidence_identity": evidence_identity,
            "fingerprint": fingerprint,
            "disposition": disposition,
        }
    ]
    result["adjudications"] = []
    return result


def _adjudication_for(
    result: dict[str, Any],
    disposition: str,
    *,
    authority: str = "synthetic-independent-evaluator",
) -> dict[str, Any]:
    fingerprint = result["findings"][0]["fingerprint"]
    adjudication: dict[str, Any] = {
        "schema_version": "1.0.0",
        "adjudication_id": f"synthetic-{disposition}-adjudication",
        "obligation_id": result["obligation_id"],
        "finding_fingerprint": fingerprint,
        "artifact": copy.deepcopy(result["artifact"]),
        "disposition": disposition,
        "authority": authority,
        "authority_receipt": _placeholder(
            f"synthetic/authority/pending-{disposition}.json"
        ),
        "rationale": "Synthetic current-byte adjudication rationale.",
        "created_at": "2026-07-26T00:01:00Z",
    }
    if disposition == "resolved":
        adjudication["resolution_verification"] = {
            "artifact_sha256": result["artifact"]["sha256"],
            "artifact_byte_length": result["artifact"]["byte_length"],
            "finding_fingerprint": fingerprint,
            "verified": True,
        }
    if disposition == "escalated":
        adjudication["owner"] = "synthetic-escalation-owner"
    return adjudication


def _verify_ok(
    module: Any,
    result: dict[str, Any],
    registry: dict[str, Any],
    root: Path,
    *,
    lifecycle_eligible: bool,
) -> None:
    prepared_result, prepared_registry = _prepared(root, result, registry)
    receipt = module.verify_obligation_result(
        prepared_result,
        prepared_registry,
        root=root,
        _test_authority_adapter=TEST_AUTHORITY_ADAPTER,
    )
    assert receipt["status"] == "verified"
    assert receipt["findings"] == []
    assert receipt["lifecycle_eligible"] is lifecycle_eligible


def _adapter_row(
    obligation_id: str,
    *,
    activation: str = "always",
    phases: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "adapter_id": f"{obligation_id}-adapter",
        "adapter_version": "1.0.0",
        "report_schema": {
            "path": GENERIC_REPORT_SCHEMA,
            "version": "1.0.0",
        },
        "allowed_outcomes": ["clean", "findings", "error", "not_applicable"],
        "blocking_threshold": "MAJOR",
        "adjudication_schema": {
            "path": "references/schemas/obligation_adjudication.schema.json",
            "version": "1.0.0",
        },
        "authorized_adjudicators": [
            "synthetic-independent-evaluator",
            "synthetic-escalation-owner",
        ],
        "binding_requirements": {
            "artifact": "path_sha256_byte_length",
            "policy": "path_sha256_byte_length",
        },
        "diagnostic_only": False,
        "activation": activation,
        "phases": phases or ["generation", "evaluation"],
    }


def _all_policy_registry() -> dict[str, Any]:
    return json.loads(
        (
            ROOT / "references/policies/obligation_result_registry.v1.json"
        ).read_text(encoding="utf-8")
    )


def _run_adversarial_cases(module: Any, root: Path) -> list[str]:
    completed: list[str] = []
    registry = _registry()

    malformed = _clean_result()
    malformed["unexpected"] = True
    _expect_code(
        module.SCHEMA, module.verify_obligation_result, malformed, registry, root=root
    )
    completed.append("closed_result_schema")

    malformed_registry = copy.deepcopy(registry)
    malformed_registry["obligations"]["d-style-profile"]["unexpected"] = True
    _expect_code(
        module.SCHEMA,
        module.verify_obligation_result,
        _clean_result(),
        malformed_registry,
        root=root,
    )
    completed.append("closed_registry_schema")

    duplicate_adapter_registry = copy.deepcopy(registry)
    duplicate_adapter_registry["obligations"]["grounding-protocol"] = copy.deepcopy(
        duplicate_adapter_registry["obligations"]["d-style-profile"]
    )
    _expect_code(
        module.SCHEMA,
        module.verify_obligation_result,
        _clean_result(),
        duplicate_adapter_registry,
        root=root,
    )
    completed.append("duplicate_registry_adapter")

    contradictory = _clean_result()
    contradictory["outcome"] = "error"
    _expect_code(
        module.SCHEMA,
        module.verify_obligation_result,
        contradictory,
        registry,
        root=root,
    )
    completed.append("outcome_status_contradiction")

    clean_with_finding = _finding_result("MINOR")
    clean_with_finding["outcome"] = "clean"
    _expect_code(
        module.SCHEMA,
        module.verify_obligation_result,
        clean_with_finding,
        registry,
        root=root,
    )
    completed.append("clean_with_finding_schema_refused")

    wrong_version = _clean_result()
    wrong_version["adapter_version"] = "1.0.1"
    _expect_code(
        module.SCHEMA,
        module.verify_obligation_result,
        wrong_version,
        registry,
        root=root,
    )
    completed.append("adapter_version_mismatch")

    disallowed_registry = copy.deepcopy(registry)
    disallowed_registry["obligations"]["d-style-profile"]["allowed_outcomes"] = [
        "findings"
    ]
    _expect_code(
        module.SCHEMA,
        module.verify_obligation_result,
        _clean_result(),
        disallowed_registry,
        root=root,
    )
    completed.append("outcome_not_allowed_by_adapter")

    diagnostic_mismatch = _clean_result()
    diagnostic_mismatch["diagnostic_only"] = True
    _expect_code(
        module.SCHEMA,
        module.verify_obligation_result,
        diagnostic_mismatch,
        registry,
        root=root,
    )
    completed.append("diagnostic_policy_mismatch")

    artifact_path = root / "synthetic/M1.md"
    artifact_path.write_text("stale synthetic bytes\n", encoding="utf-8", newline="")
    try:
        _expect_code(
            module.STALE,
            module.verify_obligation_result,
            _clean_result(),
            registry,
            root=root,
        )
    finally:
        artifact_path.write_text(ARTIFACT_TEXT, encoding="utf-8", newline="")
    completed.append("stale_artifact_bytes")

    stale_policy = _clean_result()
    stale_policy["policy"]["byte_length"] += 1
    _expect_code(
        module.STALE,
        module.verify_obligation_result,
        stale_policy,
        registry,
        root=root,
    )
    completed.append("stale_policy_binding")

    stale_legacy = _clean_result()
    stale_legacy["legacy_execution_evidence"]["evidence"][0]["sha256"] = "0" * 64
    _expect_code(
        module.STALE,
        module.verify_obligation_result,
        stale_legacy,
        registry,
        root=root,
    )
    completed.append("stale_legacy_execution_evidence")

    unsafe_binding = _clean_result()
    unsafe_binding["artifact"]["path"] = "../synthetic/M1.md"
    _expect_code(
        module.STALE,
        module.verify_obligation_result,
        unsafe_binding,
        registry,
        root=root,
    )
    completed.append("unsafe_binding_path")

    blocker_threshold = copy.deepcopy(registry)
    blocker_threshold["obligations"]["d-style-profile"]["blocking_threshold"] = "BLOCKER"
    _verify_ok(
        module,
        _finding_result("MAJOR"),
        blocker_threshold,
        root,
        lifecycle_eligible=True,
    )
    completed.append("major_below_blocker_threshold")

    _verify_ok(
        module,
        _finding_result("MINOR"),
        registry,
        root,
        lifecycle_eligible=True,
    )
    completed.append("minor_below_major_threshold")

    minor_threshold = copy.deepcopy(registry)
    minor_threshold["obligations"]["d-style-profile"]["blocking_threshold"] = "MINOR"
    _expect_code(
        module.BLOCKING_OUTCOME,
        module.verify_obligation_result,
        _finding_result("MINOR"),
        minor_threshold,
        root=root,
    )
    completed.append("minor_at_threshold_blocks")

    advisory_threshold = copy.deepcopy(registry)
    advisory_threshold["obligations"]["d-style-profile"]["blocking_threshold"] = "ADVISORY"
    _expect_code(
        module.BLOCKING_OUTCOME,
        module.verify_obligation_result,
        _finding_result("ADVISORY"),
        advisory_threshold,
        root=root,
    )
    completed.append("advisory_at_threshold_blocks")

    diagnostic_registry = copy.deepcopy(registry)
    diagnostic_registry["obligations"]["d-style-profile"]["diagnostic_only"] = True
    diagnostic_clean = _clean_result()
    diagnostic_clean["diagnostic_only"] = True
    _verify_ok(
        module,
        diagnostic_clean,
        diagnostic_registry,
        root,
        lifecycle_eligible=False,
    )
    completed.append("diagnostic_only_never_lifecycle_eligible")

    diagnostic_major = _finding_result("MAJOR")
    diagnostic_major["diagnostic_only"] = True
    diagnostic_major, prepared_diagnostic_registry = _prepared(
        root, diagnostic_major, diagnostic_registry
    )
    diagnostic_receipt = module.verify_obligation_result(
        diagnostic_major,
        prepared_diagnostic_registry,
        root=root,
        _test_authority_adapter=TEST_AUTHORITY_ADAPTER,
    )
    assert diagnostic_receipt["lifecycle_eligible"] is False
    assert diagnostic_receipt["blocking_fingerprints"] == [
        diagnostic_major["findings"][0]["fingerprint"]
    ]
    completed.append("diagnostic_findings_complete_without_clearance")

    conditional_registry = copy.deepcopy(registry)
    conditional_registry["obligations"]["d-style-profile"]["activation"] = (
        "is_or_adjacent_piece"
    )
    inactive = _clean_result()
    inactive["activation"] = "not:is_or_adjacent_piece"
    inactive["execution_status"] = "not_applicable"
    inactive["outcome"] = "not_applicable"
    _verify_ok(
        module,
        inactive,
        conditional_registry,
        root,
        lifecycle_eligible=True,
    )
    completed.append("registered_false_activation_not_applicable")

    always_inactive = copy.deepcopy(inactive)
    always_inactive["activation"] = "not:always"
    _expect_code(
        module.BLOCKING_OUTCOME,
        module.verify_obligation_result,
        always_inactive,
        registry,
        root=root,
    )
    completed.append("always_not_applicable_blocks")

    active_not_applicable = copy.deepcopy(inactive)
    active_not_applicable["activation"] = "is_or_adjacent_piece"
    _expect_code(
        module.BLOCKING_OUTCOME,
        module.verify_obligation_result,
        active_not_applicable,
        conditional_registry,
        root=root,
    )
    completed.append("active_predicate_not_applicable_blocks")

    inactive_clean = _clean_result()
    inactive_clean["activation"] = "not:is_or_adjacent_piece"
    _expect_code(
        module.SCHEMA,
        module.verify_obligation_result,
        inactive_clean,
        conditional_registry,
        root=root,
    )
    completed.append("inactive_predicate_clean_contradiction")

    resolved_missing = _finding_result("MAJOR", disposition="resolved")
    _expect_code(
        module.ADJUDICATION_MISSING,
        module.verify_obligation_result,
        resolved_missing,
        registry,
        root=root,
    )
    completed.append("resolved_adjudication_missing")

    stale_adjudication = _finding_result("MAJOR", disposition="resolved")
    stale_adjudication["adjudications"] = [
        _adjudication_for(stale_adjudication, "resolved")
    ]
    stale_adjudication["adjudications"][0]["artifact"]["sha256"] = "0" * 64
    _expect_code(
        module.ADJUDICATION_STALE,
        module.verify_obligation_result,
        stale_adjudication,
        registry,
        root=root,
    )
    completed.append("stale_adjudication_artifact")

    stale_verification = _finding_result("MAJOR", disposition="resolved")
    stale_verification["adjudications"] = [
        _adjudication_for(stale_verification, "resolved")
    ]
    stale_verification["adjudications"][0]["resolution_verification"][
        "artifact_sha256"
    ] = "0" * 64
    _expect_code(
        module.ADJUDICATION_STALE,
        module.verify_obligation_result,
        stale_verification,
        registry,
        root=root,
    )
    completed.append("stale_resolution_verification")

    predating_adjudication = _finding_result("MAJOR", disposition="resolved")
    predating_adjudication["adjudications"] = [
        _adjudication_for(predating_adjudication, "resolved")
    ]
    predating_adjudication["adjudications"][0]["created_at"] = (
        "2026-07-25T23:59:59Z"
    )
    _expect_code(
        module.ADJUDICATION_STALE,
        module.verify_obligation_result,
        predating_adjudication,
        registry,
        root=root,
    )
    completed.append("predating_adjudication")

    duplicate_adjudication = _finding_result("MAJOR", disposition="resolved")
    adjudication = _adjudication_for(duplicate_adjudication, "resolved")
    duplicate_adjudication["adjudications"] = [
        adjudication,
        copy.deepcopy(adjudication),
    ]
    _expect_code(
        module.ADJUDICATION_STALE,
        module.verify_obligation_result,
        duplicate_adjudication,
        registry,
        root=root,
    )
    completed.append("duplicate_adjudication")

    orphan = _clean_result()
    orphan_finding = _finding_result("MAJOR", disposition="resolved")
    orphan_adjudication = _adjudication_for(orphan_finding, "resolved")
    orphan["adjudications"] = [orphan_adjudication]
    _expect_code(
        module.ADJUDICATION_STALE,
        module.verify_obligation_result,
        orphan,
        registry,
        root=root,
    )
    completed.append("orphan_adjudication")

    cross_obligation = _finding_result("MAJOR", disposition="resolved")
    cross_obligation["adjudications"] = [
        _adjudication_for(cross_obligation, "resolved")
    ]
    cross_obligation["adjudications"][0]["obligation_id"] = "grounding-protocol"
    _expect_code(
        module.ADJUDICATION_STALE,
        module.verify_obligation_result,
        cross_obligation,
        registry,
        root=root,
    )
    completed.append("cross_obligation_adjudication")

    acknowledged = _finding_result("MAJOR", disposition="acknowledged")
    acknowledged["adjudications"] = [
        _adjudication_for(acknowledged, "acknowledged")
    ]
    _expect_code(
        module.BLOCKING_OUTCOME,
        module.verify_obligation_result,
        acknowledged,
        registry,
        root=root,
    )
    completed.append("authorized_acknowledgement_remains_blocking")

    unauthorized = copy.deepcopy(acknowledged)
    unauthorized["adjudications"][0]["authority"] = "unauthorized-actor"
    _expect_code(
        module.ADJUDICATION_STALE,
        module.verify_obligation_result,
        unauthorized,
        registry,
        root=root,
    )
    completed.append("unauthorized_acknowledgement")

    no_rationale = copy.deepcopy(acknowledged)
    no_rationale["adjudications"][0]["rationale"] = ""
    _expect_code(
        module.SCHEMA,
        module.verify_obligation_result,
        no_rationale,
        registry,
        root=root,
    )
    completed.append("acknowledgement_requires_rationale")

    escalated = _finding_result("MAJOR", disposition="escalated")
    escalated["adjudications"] = [_adjudication_for(escalated, "escalated")]
    _expect_code(
        module.BLOCKING_OUTCOME,
        module.verify_obligation_result,
        escalated,
        registry,
        root=root,
    )
    completed.append("authorized_escalation_remains_blocking")

    no_owner = copy.deepcopy(escalated)
    del no_owner["adjudications"][0]["owner"]
    _expect_code(
        module.SCHEMA,
        module.verify_obligation_result,
        no_owner,
        registry,
        root=root,
    )
    completed.append("escalation_requires_owner")

    refused = _finding_result("MAJOR", disposition="refused")
    refused["adjudications"] = [_adjudication_for(refused, "refused")]
    _expect_code(
        module.BLOCKING_OUTCOME,
        module.verify_obligation_result,
        refused,
        registry,
        root=root,
    )
    completed.append("refused_disposition_remains_blocking")

    resolved_minor = _finding_result("MINOR", disposition="resolved")
    resolved_minor["adjudications"] = [_adjudication_for(resolved_minor, "resolved")]
    _verify_ok(
        module,
        resolved_minor,
        registry,
        root,
        lifecycle_eligible=True,
    )
    completed.append("nonblocking_current_resolution")

    duplicate_finding = _finding_result("MINOR")
    duplicate_finding["findings"].append(copy.deepcopy(duplicate_finding["findings"][0]))
    _expect_code(
        module.SCHEMA,
        module.verify_obligation_result,
        duplicate_finding,
        registry,
        root=root,
    )
    completed.append("duplicate_finding_fingerprint")

    error_result = _clean_result()
    error_result["execution_status"] = "failed"
    error_result["outcome"] = "error"
    _expect_code(
        module.BLOCKING_OUTCOME,
        module.verify_obligation_result,
        error_result,
        registry,
        root=root,
    )
    completed.append("error_outcome_blocks")

    _verify_ok(
        module,
        _clean_result(),
        registry,
        root,
        lifecycle_eligible=True,
    )
    completed.append("explicit_clean_with_legacy_applied")
    return completed


def _run_all_registry_rows(module: Any, root: Path) -> list[str]:
    registry = _all_policy_registry()
    completed: list[str] = []
    for obligation_id, adapter in registry["obligations"].items():
        if obligation_id == "d-style-profile":
            result = _native_dstyle_result(
                module,
                root,
                relative="synthetic/dstyle-registry-row.md",
                text=(
                    "This paper argues a claim because evidence from a source supports "
                    "the warrant. However, a limitation defines scope and an alternative "
                    "explanation. AI-assisted work is disclosed.\n"
                ),
            )
        else:
            result = _clean_result()
            result["obligation_id"] = obligation_id
            result["adapter_version"] = adapter["adapter_version"]
            result["activation"] = adapter["activation"]
            result["diagnostic_only"] = adapter["diagnostic_only"]
        _verify_ok(
            module,
            result,
            registry,
            root,
            lifecycle_eligible=not adapter["diagnostic_only"],
        )
        completed.append(obligation_id)
    return completed


def _run_public_registry_api_case(module: Any) -> list[str]:
    registry = _registry()
    before = copy.deepcopy(registry)
    rows = module.validate_obligation_registry(registry)
    assert set(rows) == {"d-style-profile"}
    assert rows["d-style-profile"] == registry["obligations"]["d-style-profile"]
    rows["d-style-profile"]["allowed_outcomes"].remove("clean")
    assert registry == before, "public registry validator leaked mutable registry state"
    return ["public_registry_validation_returns_detached_keyed_rows"]


def _binding_for_file(root: Path, relative: str) -> dict[str, Any]:
    payload = (root / relative).read_bytes()
    return {
        "path": relative,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "byte_length": len(payload),
    }


def _native_dstyle_registry() -> dict[str, Any]:
    registry = _registry()
    row = registry["obligations"]["d-style-profile"]
    row["adapter_id"] = "d-style-profile-result"
    row["report_schema"] = {
        "path": "scripts/d_style_profile_check.py",
        "version": "1.1.0",
    }
    return registry


def _native_dstyle_result(
    module: Any, root: Path, *, relative: str, text: str
) -> dict[str, Any]:
    from d_style_profile_check import build_report

    artifact_path = root / relative
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(text, encoding="utf-8", newline="")
    artifact = _binding_for_file(root, relative)
    policy = _binding_for_file(root, "synthetic/d-style-policy.json")
    report = build_report(
        root, root / "research_notes/directives.md", artifact_path
    )
    report_binding = _write_json_binding(
        root,
        f"synthetic/reports/native-{Path(relative).stem}.json",
        report,
    )
    findings: list[dict[str, Any]] = []
    for observed in report["findings"]:
        severity = observed["severity"]
        if severity not in {"BLOCKER", "MAJOR", "MINOR", "ADVISORY"}:
            continue
        evidence_identity = hashlib.sha256(
            _canonical(
                {
                    "field": observed.get("field"),
                    "locator": observed.get("locator"),
                    "message": observed.get("message"),
                }
            )
        ).hexdigest()
        findings.append(
            {
                "code": observed["code"],
                "severity": severity,
                "evidence_identity": evidence_identity,
                "fingerprint": module.finding_fingerprint(
                    "d-style-profile",
                    observed["code"],
                    severity,
                    evidence_identity,
                    artifact["sha256"],
                ),
                "disposition": "open",
            }
        )
    return {
        "schema_version": "1.0.0",
        "obligation_id": "d-style-profile",
        "adapter_version": "1.0.0",
        "artifact": artifact,
        "policy": policy,
        "report": report_binding,
        "activation": "always",
        "execution_status": "completed",
        "outcome": "findings" if findings else "clean",
        "findings": findings,
        "diagnostic_only": False,
        "created_at": "2026-07-26T00:00:00Z",
        "adjudications": [],
    }


def _tamper_fixture_envelope(
    root: Path, binding: dict[str, Any]
) -> dict[str, Any]:
    path = root / binding["path"]
    value = json.loads(path.read_text(encoding="utf-8"))
    value["authenticator"]["digest"] = "0" * 64
    payload = _canonical(value)
    path.write_bytes(payload)
    return {
        "path": binding["path"],
        "sha256": hashlib.sha256(payload).hexdigest(),
        "byte_length": len(payload),
    }


def _run_round1_attack_pairs(module: Any, root: Path) -> list[str]:
    completed: list[str] = []

    native_registry = _native_dstyle_registry()
    major = _native_dstyle_result(
        module,
        root,
        relative="synthetic/dstyle-major.md",
        text="A short paragraph without explicit argumentative surfaces.\n",
    )
    declared_clean = copy.deepcopy(major)
    declared_clean["outcome"] = "clean"
    declared_clean["findings"] = []
    _expect_code(
        module.STALE,
        module.verify_obligation_result,
        declared_clean,
        native_registry,
        root=root,
        _prepare_fixture=False,
    )
    clean = _native_dstyle_result(
        module,
        root,
        relative="synthetic/dstyle-clean.md",
        text=(
            "This paper argues a claim because evidence from a source supports the "
            "warrant and explains the stakes. However, a limitation defines the scope "
            "and an alternative explanation. AI-assisted work is disclosed.\n"
        ),
    )
    receipt = module.verify_obligation_result(clean, native_registry, root=root)
    assert receipt["lifecycle_eligible"] is True
    completed.append("native_dstyle_major_cannot_be_declared_clean")

    generic_registry = _registry()
    generic_clean, prepared_registry = _prepared(
        root, _clean_result(), generic_registry
    )
    assert module.verify_obligation_result(
        generic_clean,
        prepared_registry,
        root=root,
        _test_authority_adapter=TEST_AUTHORITY_ADAPTER,
    )["lifecycle_eligible"] is True
    forged_report = copy.deepcopy(generic_clean)
    forged_report["verifier_receipt"] = _tamper_fixture_envelope(
        root, forged_report["verifier_receipt"]
    )
    _expect_code(
        module.STALE,
        module.verify_obligation_result,
        forged_report,
        prepared_registry,
        root=root,
        _prepare_fixture=False,
    )
    completed.append("generic_clean_requires_authenticated_verifier")

    downgraded = _finding_result("MAJOR")
    downgraded["findings"][0]["severity"] = "MINOR"
    downgraded, downgraded_registry = _prepared(root, downgraded, generic_registry)
    _expect_code(
        module.STALE,
        module.verify_obligation_result,
        downgraded,
        downgraded_registry,
        root=root,
        _prepare_fixture=False,
    )
    _verify_ok(
        module,
        _finding_result("MINOR"),
        generic_registry,
        root,
        lifecycle_eligible=True,
    )
    completed.append("severity_downgrade_requires_new_fingerprint")

    resolved = _finding_result("MAJOR", disposition="resolved")
    resolved["adjudications"] = [_adjudication_for(resolved, "resolved")]
    resolved, resolved_registry = _prepared(root, resolved, generic_registry)
    assert module.verify_obligation_result(
        resolved,
        resolved_registry,
        root=root,
        _test_authority_adapter=TEST_AUTHORITY_ADAPTER,
    )["lifecycle_eligible"] is True
    forged_authority = copy.deepcopy(resolved)
    forged_authority["adjudications"][0]["authority_receipt"] = (
        _tamper_fixture_envelope(
            root, forged_authority["adjudications"][0]["authority_receipt"]
        )
    )
    _expect_code(
        module.ADJUDICATION_STALE,
        module.verify_obligation_result,
        forged_authority,
        resolved_registry,
        root=root,
        _prepare_fixture=False,
    )
    completed.append("adjudicator_string_cannot_replace_authenticated_receipt")

    conditional_registry = _registry()
    conditional_registry["obligations"]["d-style-profile"]["activation"] = (
        "is_or_adjacent_piece"
    )
    inactive = _clean_result()
    inactive["activation"] = "not:is_or_adjacent_piece"
    inactive["execution_status"] = "not_applicable"
    inactive["outcome"] = "not_applicable"
    inactive, conditional_registry = _prepared(root, inactive, conditional_registry)
    assert module.verify_obligation_result(
        inactive,
        conditional_registry,
        root=root,
        _test_authority_adapter=TEST_AUTHORITY_ADAPTER,
    )["lifecycle_eligible"] is True
    forged_activation = copy.deepcopy(inactive)
    forged_activation["activation_proof"] = _tamper_fixture_envelope(
        root, forged_activation["activation_proof"]
    )
    _expect_code(
        module.STALE,
        module.verify_obligation_result,
        forged_activation,
        conditional_registry,
        root=root,
        _prepare_fixture=False,
    )
    completed.append("self_asserted_false_activation_cannot_clear")
    return completed


def _run_toctou_cases(module: Any, root: Path) -> list[str]:
    completed: list[str] = []

    original_value = {"state": "original"}
    swapped_value = {"state": "swapped"}
    bound_json = _write_json_binding(
        root, "synthetic/toctou-bound.json", original_value
    )
    bound_path = root / bound_json["path"]
    original_read_bytes = Path.read_bytes

    def swap_after_verified_read(path: Path) -> bytes:
        payload = original_read_bytes(path)
        if path == bound_path:
            path.write_bytes(_canonical(swapped_value))
        return payload

    loaded: dict[str, Any] | None = None
    try:
        Path.read_bytes = swap_after_verified_read
        _, loaded = module._load_bound_json(root, bound_json, "TOCTOU bound JSON")
    finally:
        Path.read_bytes = original_read_bytes
        bound_path.write_bytes(_canonical(original_value))
    assert loaded == original_value, "bound JSON parser trusted reopened bytes"
    completed.append("bound_json_parses_the_exact_verified_bytes")

    subject = _write_json_binding(
        root,
        "synthetic/toctou-subject.json",
        {"schema_version": "1.0.0", "subject": "exact"},
    )
    claim = _write_json_binding(
        root,
        "synthetic/toctou-claim.json",
        {"receipt_id": "synthetic-receipt"},
    )
    consumption = _write_json_binding(
        root,
        "synthetic/toctou-consumption.json",
        {"state": "initial"},
    )
    envelope = _write_json_binding(
        root,
        "synthetic/toctou-envelope.json",
        {
            "schema_version": "1.0.0",
            "receipt_type": "obligation_verifier_authority",
            "authority_mode": "assignment_dispatch",
            "authority": "synthetic-independent-evaluator",
            "subject": subject,
            "claim": claim,
            "consumption": consumption,
        },
    )
    claim_path = root / claim["path"]

    class SwappingDispatch:
        @staticmethod
        def validate_consumed_claim_for_context(*args: Any, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
            claim_path.write_bytes(_canonical({"receipt_id": "swapped-receipt"}))
            return {}, {
                "postimages": [
                    {
                        "path": subject["path"],
                        "sha256": subject["sha256"],
                        "size": subject["byte_length"],
                    }
                ]
            }

    original_import_module = module.importlib.import_module

    def import_with_swap(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "assignment_dispatch_claim":
            return SwappingDispatch
        return original_import_module(name, *args, **kwargs)

    try:
        module.importlib.import_module = import_with_swap
        _expect_code(
            module.STALE,
            module._authenticate_envelope,
            root,
            envelope,
            receipt_type="obligation_verifier_authority",
            expected_subject=subject,
            artifact=_binding_for_file(root, "synthetic/M1.md"),
            code=module.STALE,
        )
    finally:
        module.importlib.import_module = original_import_module
        claim_path.write_bytes(_canonical({"receipt_id": "synthetic-receipt"}))
    completed.append("dispatch_claim_swap_during_validation_is_refused")
    return completed


def _run_round2_qualification_cases(module: Any, root: Path) -> list[str]:
    completed: list[str] = []

    manifest_path = root / "project_manifest.json"
    original_manifest = manifest_path.read_bytes()
    manifest_path.write_bytes(
        _canonical(
            {
                "identity": "ordinary-caller-authored-project",
                "synthetic_fixture": "c4",
                "production_authority": False,
            }
        )
    )
    fixture_result, fixture_registry = _prepared(root, _clean_result(), _registry())
    try:
        _expect_code(
            module.STALE,
            module.verify_obligation_result,
            fixture_result,
            fixture_registry,
            root=root,
            _prepare_fixture=False,
            _inject_test_authority=False,
        )
    finally:
        manifest_path.write_bytes(original_manifest)
    completed.append("caller_authored_fixture_manifest_cannot_enable_authority")

    native_registry = _native_dstyle_registry()
    clean_text = (
        "This paper argues a claim because evidence from a source supports the "
        "warrant and explains the stakes. However, a limitation defines the scope "
        "and an alternative explanation. AI-assisted work is disclosed.\n"
    )
    artifact_result = _native_dstyle_result(
        module,
        root,
        relative="synthetic/dstyle-artifact-swap.md",
        text=clean_text,
    )
    artifact_path = root / artifact_result["artifact"]["path"]
    artifact_original = artifact_path.read_bytes()
    original_read_bytes = Path.read_bytes
    artifact_swapped = False

    def swap_artifact_after_snapshot(path: Path) -> bytes:
        nonlocal artifact_swapped
        payload = original_read_bytes(path)
        if path == artifact_path and not artifact_swapped:
            artifact_swapped = True
            path.write_bytes(b"Swapped artifact bytes.\n")
        return payload

    try:
        Path.read_bytes = swap_artifact_after_snapshot
        _expect_code(
            module.STALE,
            module.verify_obligation_result,
            artifact_result,
            native_registry,
            root=root,
            _prepare_fixture=False,
        )
    finally:
        Path.read_bytes = original_read_bytes
        artifact_path.write_bytes(artifact_original)
    assert module.verify_obligation_result(
        artifact_result, native_registry, root=root
    )["lifecycle_eligible"] is True
    completed.append("dstyle_artifact_read_swap_refuses_and_clean_twin_qualifies")

    directives_path = root / "research_notes" / "directives.md"
    directives_path.parent.mkdir(parents=True, exist_ok=True)
    directives_original = b"# Stable synthetic directives snapshot.\n"
    directives_path.write_bytes(directives_original)
    directives_result = _native_dstyle_result(
        module,
        root,
        relative="synthetic/dstyle-directives-swap.md",
        text=clean_text,
    )
    directives_swapped = False

    def swap_directives_after_snapshot(path: Path) -> bytes:
        nonlocal directives_swapped
        payload = original_read_bytes(path)
        if path == directives_path and not directives_swapped:
            directives_swapped = True
            path.write_bytes(b"# Swapped synthetic directives bytes.\n")
        return payload

    try:
        Path.read_bytes = swap_directives_after_snapshot
        _expect_code(
            module.STALE,
            module.verify_obligation_result,
            directives_result,
            native_registry,
            root=root,
            _prepare_fixture=False,
        )
    finally:
        Path.read_bytes = original_read_bytes
        directives_path.write_bytes(directives_original)
    assert module.verify_obligation_result(
        directives_result, native_registry, root=root
    )["lifecycle_eligible"] is True
    completed.append("dstyle_directives_read_swap_refuses_and_clean_twin_qualifies")
    return completed


def main() -> int:
    failures: list[str] = []
    adversarial: list[str] = []
    registry_rows: list[str] = []
    registry_api: list[str] = []
    round1_pairs: list[str] = []
    toctou_cases: list[str] = []
    round2_cases: list[str] = []
    with TemporaryDirectory(prefix="coauthor-v040-obligation-") as temporary:
        synthetic_root = Path(temporary)
        (synthetic_root / "synthetic").mkdir()
        (synthetic_root / "project_manifest.json").write_text(
            json.dumps(
                {
                    "identity": "c4-obligation-synthetic-project",
                    "synthetic_fixture": "c4",
                    "production_authority": False,
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
            newline="",
        )
        (synthetic_root / "synthetic" / "M1.md").write_text(
            ARTIFACT_TEXT, encoding="utf-8", newline=""
        )
        (synthetic_root / "synthetic" / "d-style-policy.json").write_text(
            POLICY_TEXT, encoding="utf-8", newline=""
        )
        (synthetic_root / "synthetic" / "d-style-report.json").write_text(
            "synthetic applied D-STYLE report\n", encoding="utf-8", newline=""
        )

        registry = _registry()
        unresolved_major = _applied_major_result()
        clean_major = copy.deepcopy(unresolved_major)
        clean_major["adjudications"] = [_current_resolution()]

        known_registry = copy.deepcopy(registry)
        unknown_registry = copy.deepcopy(registry)
        del unknown_registry["obligations"]["d-style-profile"]
        known_result = copy.deepcopy(clean_major)

        pairs = [
            (
                "dstyle_major_merely_applied",
                "DRAFT-POLICY-OBLIGATION-BLOCKING-OUTCOME",
                {"result": unresolved_major, "registry": registry},
                {"result": clean_major, "registry": registry},
            ),
            (
                "unknown_obligation_by_path_presence",
                "DRAFT-POLICY-OBLIGATION-UNKNOWN",
                {"result": known_result, "registry": unknown_registry},
                {"result": known_result, "registry": known_registry},
            ),
        ]

        module = _load_module()
        for name, expected, red, clean in pairs:
            for label, fixture in (("red", red), ("clean", clean)):
                _verify_current_binding(
                    synthetic_root, fixture["result"]["artifact"], f"{name} {label} artifact"
                )
                _verify_current_binding(
                    synthetic_root, fixture["result"]["policy"], f"{name} {label} policy"
                )
                for index, binding in enumerate(
                    fixture["result"]["legacy_execution_evidence"]["evidence"]
                ):
                    _verify_current_binding(
                        synthetic_root,
                        binding,
                        f"{name} {label} legacy applied evidence {index}",
                    )
            delta = _leaf_differences(red, clean)
            if len(delta) != 1:
                failures.append(f"{name}: fixture pair changes {len(delta)} leaves: {delta}")
                continue
            if module is None:
                failures.append(
                    f"{name}: INTERFACE_BLOCKED expected {expected}; clean twin deferred; delta={delta[0]}"
                )
                continue
            red_code, _ = _observe(
                module, red["result"], red["registry"], synthetic_root
            )
            clean_code, clean_findings = _observe(
                module, clean["result"], clean["registry"], synthetic_root
            )
            if red_code != expected:
                failures.append(f"{name}: expected {expected}, observed {red_code!r}")
            if clean_code is not None or clean_findings:
                failures.append(
                    f"{name}: clean twin must have zero relevant findings; code={clean_code!r} findings={clean_findings!r}"
                )

        if module is not None:
            try:
                adversarial = _run_adversarial_cases(module, synthetic_root)
                if len(adversarial) != 39:
                    failures.append(
                        f"adversarial coverage expected 39 cases, observed {len(adversarial)}"
                    )
                registry_rows = _run_all_registry_rows(module, synthetic_root)
                policy_count = len(
                    json.loads(
                        (
                            ROOT / "references/policies/draft_governance.v1.json"
                        ).read_text(encoding="utf-8")
                    )["obligations"]
                )
                if len(registry_rows) != policy_count:
                    failures.append(
                        "generic registry coverage does not equal draft-governance rows: "
                        f"{len(registry_rows)} != {policy_count}"
                    )
                registry_api = _run_public_registry_api_case(module)
                if len(registry_api) != 1:
                    failures.append(
                        f"public registry API coverage expected 1 case, observed {len(registry_api)}"
                    )
                round1_pairs = _run_round1_attack_pairs(module, synthetic_root)
                if len(round1_pairs) != 5:
                    failures.append(
                        f"round-1 attack coverage expected 5 cases, observed {len(round1_pairs)}"
                    )
                toctou_cases = _run_toctou_cases(module, synthetic_root)
                if len(toctou_cases) != 2:
                    failures.append(
                        f"TOCTOU coverage expected 2 cases, observed {len(toctou_cases)}"
                    )
                round2_cases = _run_round2_qualification_cases(
                    module, synthetic_root
                )
                if len(round2_cases) != 3:
                    failures.append(
                        "round-2 qualification coverage expected 3 cases, "
                        f"observed {len(round2_cases)}"
                    )
            except Exception as exc:
                failures.append(
                    f"adversarial behavior: {type(exc).__name__}: {exc}"
                )

    if failures:
        for failure in failures:
            print(f"[RED] {failure}")
        print(f"obligation_result_smoketest: FAIL ({len(failures)} of {len(pairs)} pairs blocked)")
        return 1
    print(
        "obligation_result_smoketest: PASS "
        f"({len(pairs)} red/clean pairs + {len(adversarial)} adversarial cases + "
        f"{len(registry_rows)} draft-governance registry rows + "
        f"{len(registry_api)} public registry API case + "
        f"{len(round1_pairs)} round-1 red/clean attack pairs + "
        f"{len(toctou_cases)} TOCTOU cases + "
        f"{len(round2_cases)} round-2 qualification cases)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
