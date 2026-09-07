#!/usr/bin/env python3
"""Canonical transient invocation-scope vocabulary and comparison helpers.

Scope rank is used only to name a mismatch as a downgrade or escalation.  No
function in this module converts one declared scope into another or grants a
lifecycle transition.
"""

from __future__ import annotations

import re
from types import MappingProxyType
from typing import Final, Literal, TypedDict, cast


Scope = Literal["adhoc_review", "project_independent", "lab_iteration", "full_lifecycle"]
ScopeResult = Literal["OK", "PROPOSAL_ONLY", "REFUSED"]
DeclarationResult = Literal["DECLARED", "UNDECLARED", "INVALID"]
ComparisonDirection = Literal["exact", "downgrade", "escalation", "undeclared"]

ADHOC_REVIEW: Final[Scope] = "adhoc_review"
LAB_ITERATION: Final[Scope] = "lab_iteration"
FULL_LIFECYCLE: Final[Scope] = "full_lifecycle"
PROJECT_INDEPENDENT: Final[Scope] = "project_independent"

SCOPES: Final[tuple[Scope, Scope, Scope, Scope]] = (
    ADHOC_REVIEW,
    PROJECT_INDEPENDENT,
    LAB_ITERATION,
    FULL_LIFECYCLE,
)
SCOPE_ORDER: Final = SCOPES
SCOPE_RANK: Final = MappingProxyType({
    scope: rank for rank, scope in enumerate(SCOPE_ORDER)
})

RESULT_OK: Final[ScopeResult] = "OK"
RESULT_PROPOSAL_ONLY: Final[ScopeResult] = "PROPOSAL_ONLY"
RESULT_REFUSED: Final[ScopeResult] = "REFUSED"

FRC_SCOPE_UNDECLARED: Final = "FRC-SCOPE-UNDECLARED"
FRC_SCOPE_DOWNGRADE: Final = "FRC-SCOPE-DOWNGRADE"
FRC_SCOPE_ESCALATION: Final = "FRC-SCOPE-ESCALATION"
FRC_PROSE_FORBIDDEN: Final = "FRC-PROSE-FORBIDDEN"
FRC_TERMINAL_UNPROVEN: Final = "FRC-TERMINAL-UNPROVEN"
FRC_PIW_SESSION_REQUIRED: Final = "FRC-PIW-SESSION-REQUIRED"
FRC_PIW_NON_TERMINAL: Final = "FRC-PIW-NON-TERMINAL"
FRC_PIW_HISTORY_RECONSTRUCT: Final = "FRC-HISTORY-RECONSTRUCT-FORBIDDEN"
MSS_PIN_DRIFT: Final = "MSS_PIN_DRIFT"

FRC_LAB_PROPOSAL_ONLY: Final = "FRC-LAB-PROPOSAL-ONLY"
FRC_LAB_PROJECT_REQUIRED: Final = "FRC-LAB-PROJECT-REQUIRED"
FRC_LAB_CONTRACT_REQUIRED: Final = "FRC-LAB-CONTRACT-REQUIRED"
FRC_LAB_DESTINATION_REQUIRED: Final = "FRC-LAB-DESTINATION-REQUIRED"
FRC_LAB_DESTINATION_MISMATCH: Final = "FRC-LAB-DESTINATION-MISMATCH"
FRC_LAB_LIFECYCLE_FORBIDDEN: Final = "FRC-LAB-LIFECYCLE-FORBIDDEN"
FRC_LAB_F9_FORBIDDEN: Final = "FRC-LAB-F9-FORBIDDEN"
FRC_LAB_TERMINAL_FORBIDDEN: Final = "FRC-LAB-TERMINAL-FORBIDDEN"


class ScopeDeclaration(TypedDict):
    declared_scope: Scope | None
    declaration_count: int
    result: DeclarationResult
    code: str | None
    message: str


class ScopeComparison(TypedDict):
    parent_scope: Scope | None
    child_scope: Scope | None
    exact: bool
    direction: ComparisonDirection
    result: ScopeResult
    code: str
    message: str


class ScopeFinding(TypedDict):
    code: str
    message: str


class LabAuthorityRecord(TypedDict):
    result: Literal["PROPOSAL_ONLY"]
    code: Literal["FRC-LAB-PROPOSAL-ONLY"]
    lifecycle_authority: Literal[False]
    f9_authority: Literal[False]
    terminal_authority: Literal[False]


# One plain token is deliberate: child dispatches use a mechanical declaration,
# not YAML inference, aliases, quoted values, or embedded prose.
RUN_SCOPE_DECLARATION_RE: Final = re.compile(
    r"(?mi)^\s*run_scope\s*:\s*([^\s#]+)\s*(?:#.*)?$"
)

_LAB_LIFECYCLE_RE: Final = re.compile(
    r"(?mi)^\s*lifecycle_mutation\s*:\s*true\s*(?:#.*)?$"
)
_LAB_F9_RE: Final = re.compile(
    r"(?mi)^\s*f9_use\s*:\s*true\s*(?:#.*)?$"
)
_LAB_TERMINAL_RE: Final = re.compile(
    r"(?mi)^\s*terminal_claim\s*:\s*\S.*$"
)


def canonical_scope(value: object) -> Scope | None:
    """Return one normalized known scope, or ``None`` without guessing."""

    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if normalized not in SCOPE_RANK:
        return None
    return cast(Scope, normalized)


def scope_rank(value: object) -> int | None:
    """Return diagnostic rank for one known scope, never a permission grant."""

    scope = canonical_scope(value)
    return SCOPE_RANK[scope] if scope is not None else None


def resolve_top_level_scope(value: object | None) -> ScopeDeclaration:
    """Resolve top-level omission safely to full lifecycle.

    This is the one omission compatibility rule.  Child omission is always a
    refusal and is handled by :func:`parse_scope_declaration`.
    """

    if value is None:
        return {
            "declared_scope": FULL_LIFECYCLE,
            "declaration_count": 0,
            "result": "DECLARED",
            "code": None,
            "message": "top-level omission resolves safely to full_lifecycle",
        }
    scope = canonical_scope(value)
    if scope is None:
        return {
            "declared_scope": None,
            "declaration_count": 1,
            "result": "INVALID",
            "code": FRC_SCOPE_UNDECLARED,
            "message": f"top-level run scope {value!r} is not one of {SCOPES}",
        }
    return {
        "declared_scope": scope,
        "declaration_count": 1,
        "result": "DECLARED",
        "code": None,
        "message": f"top-level run scope is explicitly {scope}",
    }


def parse_scope_declaration(brief: object) -> ScopeDeclaration:
    """Parse exactly one explicit child ``run_scope:`` declaration."""

    if not isinstance(brief, str):
        return {
            "declared_scope": None,
            "declaration_count": 0,
            "result": "INVALID",
            "code": FRC_SCOPE_UNDECLARED,
            "message": "child brief must be text containing exactly one run_scope declaration",
        }

    raw_values = RUN_SCOPE_DECLARATION_RE.findall(brief)
    if not raw_values:
        return {
            "declared_scope": None,
            "declaration_count": 0,
            "result": "UNDECLARED",
            "code": FRC_SCOPE_UNDECLARED,
            "message": "child dispatch carries no `run_scope:` declaration; child omission is refused",
        }
    if len(raw_values) != 1:
        return {
            "declared_scope": None,
            "declaration_count": len(raw_values),
            "result": "INVALID",
            "code": FRC_SCOPE_UNDECLARED,
            "message": "child dispatch must carry exactly one unambiguous `run_scope:` declaration",
        }

    scope = canonical_scope(raw_values[0])
    if scope is None:
        return {
            "declared_scope": None,
            "declaration_count": 1,
            "result": "INVALID",
            "code": FRC_SCOPE_UNDECLARED,
            "message": f"child run_scope {raw_values[0]!r} is not one of {SCOPES}",
        }
    return {
        "declared_scope": scope,
        "declaration_count": 1,
        "result": "DECLARED",
        "code": None,
        "message": f"child run_scope is explicitly {scope}",
    }


def compare_scope_inheritance(
    parent_scope: object,
    child_scope: object,
) -> ScopeComparison:
    """Compare exact inheritance and classify, but never permit, a mismatch."""

    parent = canonical_scope(parent_scope)
    child = canonical_scope(child_scope)
    if parent is None:
        return {
            "parent_scope": None,
            "child_scope": child,
            "exact": False,
            "direction": "undeclared",
            "result": RESULT_REFUSED,
            "code": FRC_SCOPE_UNDECLARED,
            "message": f"parent scope {parent_scope!r} is not one of {SCOPES}",
        }
    if child is None:
        return {
            "parent_scope": parent,
            "child_scope": None,
            "exact": False,
            "direction": "undeclared",
            "result": RESULT_REFUSED,
            "code": FRC_SCOPE_UNDECLARED,
            "message": "child dispatch has no valid explicit run_scope declaration",
        }
    if parent != child:
        direction: Literal["downgrade", "escalation"]
        if SCOPE_RANK[child] < SCOPE_RANK[parent]:
            direction = "downgrade"
            code = FRC_SCOPE_DOWNGRADE
        else:
            direction = "escalation"
            code = FRC_SCOPE_ESCALATION
        return {
            "parent_scope": parent,
            "child_scope": child,
            "exact": False,
            "direction": direction,
            "result": RESULT_REFUSED,
            "code": code,
            "message": (
                f"child declares run_scope: {child} under a {parent} parent; "
                "scope must be inherited exactly"
            ),
        }

    if parent == LAB_ITERATION:
        return {
            "parent_scope": parent,
            "child_scope": child,
            "exact": True,
            "direction": "exact",
            "result": RESULT_PROPOSAL_ONLY,
            "code": FRC_LAB_PROPOSAL_ONLY,
            "message": "exact lab_iteration inheritance is proposal-only",
        }
    return {
        "parent_scope": parent,
        "child_scope": child,
        "exact": True,
        "direction": "exact",
        "result": RESULT_OK,
        "code": RESULT_OK,
        "message": f"exact {parent} scope inheritance",
    }


def evaluate_scope_inheritance(parent_scope: object, brief: object) -> ScopeComparison:
    """Parse a child brief and return its canonical inheritance comparison."""

    declaration = parse_scope_declaration(brief)
    if declaration["result"] != "DECLARED":
        comparison = compare_scope_inheritance(parent_scope, None)
        comparison["message"] = declaration["message"]
        return comparison
    return compare_scope_inheritance(parent_scope, declaration["declared_scope"])


def lab_brief_findings(brief: object) -> tuple[ScopeFinding, ...]:
    """Return exact structured lab-authority refusals in stable order."""

    if not isinstance(brief, str):
        return ()
    findings: list[ScopeFinding] = []
    if _LAB_LIFECYCLE_RE.search(brief):
        findings.append({
            "code": FRC_LAB_LIFECYCLE_FORBIDDEN,
            "message": "lab_iteration cannot request lifecycle or milestone mutation",
        })
    if _LAB_F9_RE.search(brief):
        findings.append({
            "code": FRC_LAB_F9_FORBIDDEN,
            "message": "lab_iteration has no F9 authority",
        })
    if _LAB_TERMINAL_RE.search(brief):
        findings.append({
            "code": FRC_LAB_TERMINAL_FORBIDDEN,
            "message": "lab_iteration cannot make a terminal or shipment claim",
        })
    return tuple(findings)


def proposal_only_authority() -> LabAuthorityRecord:
    """Return a fresh exact non-authority record for a legal lab operation."""

    return {
        "result": RESULT_PROPOSAL_ONLY,
        "code": FRC_LAB_PROPOSAL_ONLY,
        "lifecycle_authority": False,
        "f9_authority": False,
        "terminal_authority": False,
    }


__all__ = [
    "ADHOC_REVIEW",
    "FULL_LIFECYCLE",
    "PROJECT_INDEPENDENT",
    "FRC_LAB_CONTRACT_REQUIRED",
    "FRC_LAB_DESTINATION_MISMATCH",
    "FRC_LAB_DESTINATION_REQUIRED",
    "FRC_LAB_F9_FORBIDDEN",
    "FRC_LAB_LIFECYCLE_FORBIDDEN",
    "FRC_LAB_PROJECT_REQUIRED",
    "FRC_LAB_PROPOSAL_ONLY",
    "FRC_LAB_TERMINAL_FORBIDDEN",
    "FRC_PROSE_FORBIDDEN",
    "FRC_PIW_SESSION_REQUIRED",
    "FRC_PIW_NON_TERMINAL",
    "FRC_PIW_HISTORY_RECONSTRUCT",
    "MSS_PIN_DRIFT",
    "FRC_SCOPE_DOWNGRADE",
    "FRC_SCOPE_ESCALATION",
    "FRC_SCOPE_UNDECLARED",
    "FRC_TERMINAL_UNPROVEN",
    "LAB_ITERATION",
    "LabAuthorityRecord",
    "RESULT_OK",
    "RESULT_PROPOSAL_ONLY",
    "RESULT_REFUSED",
    "RUN_SCOPE_DECLARATION_RE",
    "SCOPES",
    "SCOPE_ORDER",
    "SCOPE_RANK",
    "Scope",
    "ScopeComparison",
    "ScopeDeclaration",
    "ScopeFinding",
    "canonical_scope",
    "compare_scope_inheritance",
    "evaluate_scope_inheritance",
    "lab_brief_findings",
    "parse_scope_declaration",
    "proposal_only_authority",
    "resolve_top_level_scope",
    "scope_rank",
]
