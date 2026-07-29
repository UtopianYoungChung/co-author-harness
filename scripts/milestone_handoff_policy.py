#!/usr/bin/env python3
"""Resolve the versioned milestone handoff policy without rewriting a ledger.

This module deliberately resolves only the contract-version/policy pair.  The
milestone schema remains authoritative for the independent ``mode`` field and
for the rest of the framework shape.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final, TypedDict


CONTRACT_VERSION_1_0: Final = "1.0.0"
CONTRACT_VERSION_1_1: Final = "1.1.0"
AUDITED_POLICY: Final = "audited"
DERIVED_POLICY: Final = "derived"

IMPLICIT_AUDITED_COMPATIBILITY: Final = "IMPLICIT_AUDITED_COMPATIBILITY"
EXPLICIT_AUDITED: Final = "EXPLICIT_AUDITED"
EXPLICIT_DERIVED: Final = "EXPLICIT_DERIVED"

MHP_FRAMEWORK_INVALID: Final = "MHP-FRAMEWORK-INVALID"
MHP_CONTRACT_VERSION_REQUIRED: Final = "MHP-CONTRACT-VERSION-REQUIRED"
MHP_CONTRACT_VERSION_INVALID: Final = "MHP-CONTRACT-VERSION-INVALID"
MHP_CONTRACT_VERSION_UNSUPPORTED: Final = "MHP-CONTRACT-VERSION-UNSUPPORTED"
MHP_HANDOFF_POLICY_FORBIDDEN: Final = "MHP-HANDOFF-POLICY-FORBIDDEN"
MHP_HANDOFF_POLICY_REQUIRED: Final = "MHP-HANDOFF-POLICY-REQUIRED"
MHP_HANDOFF_POLICY_INVALID: Final = "MHP-HANDOFF-POLICY-INVALID"


class HandoffPolicyResolution(TypedDict):
    """Deterministic declared/effective policy projection."""

    contract_version: str
    declared_policy: str | None
    effective_policy: str
    result: str


class HandoffPolicyResolutionError(ValueError):
    """One stable fail-closed refusal from effective-policy resolution."""

    def __init__(self, code: str, path: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.path = path
        self.message = message

    def json_value(self) -> dict[str, str]:
        return {"code": self.code, "path": self.path, "message": self.message}


def _refuse(code: str, path: str, message: str) -> None:
    raise HandoffPolicyResolutionError(code, path, message)


def resolve_handoff_policy(
    framework: Mapping[str, object],
) -> HandoffPolicyResolution:
    """Return the canonical policy record for one milestone framework object.

    A valid 1.0.0 object has no declared policy and resolves mechanically to
    audited compatibility.  Version 1.1.0 requires an explicit audited or
    derived policy.  The input is inspected only and is never copied back or
    otherwise mutated.
    """

    if not isinstance(framework, Mapping):
        _refuse(
            MHP_FRAMEWORK_INVALID,
            "milestone_framework",
            "milestone framework must be an object",
        )

    if "contract_version" not in framework:
        _refuse(
            MHP_CONTRACT_VERSION_REQUIRED,
            "milestone_framework.contract_version",
            "contract_version is required",
        )
    contract_version = framework["contract_version"]
    if not isinstance(contract_version, str) or not contract_version:
        _refuse(
            MHP_CONTRACT_VERSION_INVALID,
            "milestone_framework.contract_version",
            "contract_version must be a non-empty string",
        )

    policy_is_declared = "handoff_policy" in framework
    declared_policy = framework.get("handoff_policy")

    if contract_version == CONTRACT_VERSION_1_0:
        if policy_is_declared:
            _refuse(
                MHP_HANDOFF_POLICY_FORBIDDEN,
                "milestone_framework.handoff_policy",
                "contract 1.0.0 must omit handoff_policy",
            )
        return {
            "contract_version": CONTRACT_VERSION_1_0,
            "declared_policy": None,
            "effective_policy": AUDITED_POLICY,
            "result": IMPLICIT_AUDITED_COMPATIBILITY,
        }

    if contract_version != CONTRACT_VERSION_1_1:
        _refuse(
            MHP_CONTRACT_VERSION_UNSUPPORTED,
            "milestone_framework.contract_version",
            f"unsupported milestone framework contract version: {contract_version!r}",
        )

    if not policy_is_declared:
        _refuse(
            MHP_HANDOFF_POLICY_REQUIRED,
            "milestone_framework.handoff_policy",
            "contract 1.1.0 requires an explicit handoff_policy",
        )
    if declared_policy not in {AUDITED_POLICY, DERIVED_POLICY}:
        _refuse(
            MHP_HANDOFF_POLICY_INVALID,
            "milestone_framework.handoff_policy",
            "handoff_policy must be exactly 'audited' or 'derived'",
        )

    assert isinstance(declared_policy, str)
    result = EXPLICIT_AUDITED if declared_policy == AUDITED_POLICY else EXPLICIT_DERIVED
    return {
        "contract_version": CONTRACT_VERSION_1_1,
        "declared_policy": declared_policy,
        "effective_policy": declared_policy,
        "result": result,
    }


__all__ = [
    "AUDITED_POLICY",
    "CONTRACT_VERSION_1_0",
    "CONTRACT_VERSION_1_1",
    "DERIVED_POLICY",
    "EXPLICIT_AUDITED",
    "EXPLICIT_DERIVED",
    "HandoffPolicyResolution",
    "HandoffPolicyResolutionError",
    "IMPLICIT_AUDITED_COMPATIBILITY",
    "MHP_CONTRACT_VERSION_INVALID",
    "MHP_CONTRACT_VERSION_REQUIRED",
    "MHP_CONTRACT_VERSION_UNSUPPORTED",
    "MHP_FRAMEWORK_INVALID",
    "MHP_HANDOFF_POLICY_FORBIDDEN",
    "MHP_HANDOFF_POLICY_INVALID",
    "MHP_HANDOFF_POLICY_REQUIRED",
    "resolve_handoff_policy",
]
