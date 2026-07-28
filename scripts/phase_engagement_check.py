#!/usr/bin/env python3
"""Validate the single-source Ph1-Ph4 role-engagement contract."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from pathlib import PurePosixPath
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
POLICY_RELATIVE_PATH = "references/policies/phase_engagement.v1.json"
RETIREMENT_LEDGER_PATH = (
    "references/retired/PHASE_ENGAGEMENT_RETIREMENT_LEDGER.md"
)
CONTRADICTION = "PHASE-CONTRACT-CONTRADICTION"
STALE_AUTHORITY = "PHASE-CONTRACT-STALE-AUTHORITY"

PHASE_MATRIX = {
    "Ph1": {
        "planner": "required",
        "generator": "required",
        "evaluator": "bounded_independent_required",
        "reflector": "lightweight_required",
    },
    "Ph2": {
        "planner": "required",
        "generator": "required",
        "evaluator": "full_revision_maturity_required",
        "reflector": "lightweight_required",
    },
    "Ph3": {
        "planner": "required",
        "generator": "required",
        "evaluator": "full_iterative_required",
        "reflector": "lightweight_required",
    },
    "Ph4": {
        "planner": "required",
        "generator": "fix_only_required",
        "evaluator": "strict_final_required",
        "reflector": "full_required",
        "external_verifiers": "required",
    },
}

RETIRED_PH1_STATEMENT = (
    "The Evaluator is dormant at Ph1 and does not engage.\n"
)

_TOP_LEVEL_FIELDS = {
    "schema_version",
    "policy_id",
    "phases",
    "retirement_ledger",
    "effective_at",
}
_LIVE_ROOTS = (
    "agents",
    "references",
    "skills",
    "docs/agent-instructions",
)
_ROOT_DOCUMENTS = ("README.md", "AGENTS.md", "CLAUDE.md")
_TEXT_SUFFIXES = {".md", ".markdown", ".txt", ".json", ".yaml", ".yml", ".toml"}
_GENERATED_PARTS = {"__pycache__", "node_modules", "dist", "build"}
_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_UTC_TIME_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)
_PH1_RE = re.compile(r"\b(?:ph\s*1|phase\s*(?:1|one))\b", re.IGNORECASE)
_PH2_RE = re.compile(r"\b(?:ph\s*2|phase\s*(?:2|two))\b", re.IGNORECASE)
_EVALUATOR_RE = re.compile(r"\b(?:the\s+)?evaluator\b", re.IGNORECASE)
_DORMANT_STATUS_RE = re.compile(
    r"(?<!not\s)(?<!never\s)\b(?:dormant|inactive|absent)\b"
    r"|\bnot[-\s]+engaged\b"
    r"|\b(?:does|did|will)\s+not\s+engage\b",
    re.IGNORECASE,
)
_NO_EVALUATOR_RE = re.compile(
    r"\bno\s+(?:bounded\s+|independent\s+|active\s+)*evaluator\b",
    re.IGNORECASE,
)
_PH2_JOIN_RE = re.compile(
    r"\b(?:the\s+)?evaluator\s+"
    r"(?:only\s+)?(?:joins?|starts?|begins?|enters?|engages?)\b"
    r"|\b(?:the\s+)?evaluator(?:'s)?\s+engagement\s+"
    r"(?:only\s+)?(?:starts?|begins?)\b"
    r"|\b(?:the\s+)?evaluator\b[^.!?;\n]{0,80}\bnot\b[^.!?;\n]{0,40}\buntil\b",
    re.IGNORECASE,
)
_OPTIONAL_RE = re.compile(r"\boptional\b", re.IGNORECASE)
_NOT_OPTIONAL_RE = re.compile(r"\bnot\s+optional\b", re.IGNORECASE)
_OMITTABLE_RE = re.compile(
    r"\b(?:participation\s+)?may\s+be\s+omitted\b", re.IGNORECASE
)
_SKIPPABLE_RE = re.compile(r"\bcan\s+be\s+skipped\b", re.IGNORECASE)
_WAIVED_RE = re.compile(r"\bwaived\b", re.IGNORECASE)
_WAIVER_NEGATION_RE = re.compile(
    r"\b(?:not|cannot\s+be|may\s+not\s+be)\s+waived\b", re.IGNORECASE
)
_NOT_REQUIRED_RE = re.compile(r"\bnot\s+required\b", re.IGNORECASE)


class PhaseEngagementRefusal(RuntimeError):
    """Typed refusal from the phase-engagement checker."""

    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


def _refuse(code: str, detail: str) -> None:
    raise PhaseEngagementRefusal(code, detail)


def _package_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        _refuse(STALE_AUTHORITY, f"{label} must be a normalized POSIX path")
    path = PurePosixPath(value)
    if path.is_absolute() or str(path) != value or any(
        part in {"", ".", ".."} for part in path.parts
    ):
        _refuse(STALE_AUTHORITY, f"{label} is unsafe or noncanonical: {value!r}")
    return value


def _validated_policy(policy: Any) -> tuple[str, set[str]]:
    if not isinstance(policy, dict) or set(policy) != _TOP_LEVEL_FIELDS:
        _refuse(STALE_AUTHORITY, "phase authority fields are missing or extra")
    if policy.get("schema_version") != "1.0.0":
        _refuse(STALE_AUTHORITY, "phase authority schema_version is stale")
    policy_id = policy.get("policy_id")
    if not isinstance(policy_id, str) or not _IDENTIFIER_RE.fullmatch(policy_id):
        _refuse(STALE_AUTHORITY, "phase authority policy_id is malformed")
    effective_at = policy.get("effective_at")
    if not isinstance(effective_at, str) or not _UTC_TIME_RE.fullmatch(effective_at):
        _refuse(STALE_AUTHORITY, "phase authority effective_at is malformed")
    phases = policy.get("phases")
    if not isinstance(phases, dict) or phases != PHASE_MATRIX:
        _refuse(
            STALE_AUTHORITY,
            "phase authority must exactly match the frozen Ph1-Ph4 role matrix",
        )
    ledger = policy.get("retirement_ledger")
    if ledger != [RETIREMENT_LEDGER_PATH]:
        _refuse(
            STALE_AUTHORITY,
            "retirement_ledger must be the frozen exact singleton path",
        )
    return policy_id, {RETIREMENT_LEDGER_PATH}


def _requiredness_contradiction(segment: str) -> bool:
    evaluator_matches = list(_EVALUATOR_RE.finditer(segment))
    ph1_matches = list(_PH1_RE.finditer(segment))
    status_matches = [
        match
        for match in _OPTIONAL_RE.finditer(segment)
        if not _NOT_OPTIONAL_RE.search(segment[max(0, match.start() - 12):match.end()])
    ]
    status_matches.extend(_OMITTABLE_RE.finditer(segment))
    status_matches.extend(_SKIPPABLE_RE.finditer(segment))
    status_matches.extend(_NOT_REQUIRED_RE.finditer(segment))
    status_matches.extend(
        match
        for match in _WAIVED_RE.finditer(segment)
        if not _WAIVER_NEGATION_RE.search(
            segment[max(0, match.start() - 20):match.end()]
        )
    )
    return any(
        max(evaluator.end(), phase.end(), status.end())
        - min(evaluator.start(), phase.start(), status.start())
        <= 160
        for evaluator in evaluator_matches
        for phase in ph1_matches
        for status in status_matches
    )


def _contradictory_ph1_assertion(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text)
    segments = re.split(r"[.!?;]+", normalized)
    for segment in segments:
        if not segment.strip() or not _EVALUATOR_RE.search(segment):
            continue
        if _PH1_RE.search(segment) and (
            _DORMANT_STATUS_RE.search(segment) or _NO_EVALUATOR_RE.search(segment)
            or _requiredness_contradiction(segment)
        ):
            return True
        if _PH2_RE.search(segment) and _PH2_JOIN_RE.search(segment):
            return True
    return False


def check_phase_engagement(
    policy: dict[str, Any], documents: list[dict[str, str]]
) -> dict[str, Any]:
    """Validate the authority and reject superseded Ph1-dormancy prose."""

    policy_id, retired_paths = _validated_policy(policy)
    if not isinstance(documents, list):
        _refuse(STALE_AUTHORITY, "documents must be an array")

    seen: set[str] = set()
    retired_exceptions: list[str] = []
    for index, document in enumerate(documents):
        if not isinstance(document, dict) or set(document) != {"path", "text"}:
            _refuse(STALE_AUTHORITY, f"document[{index}] fields are missing or extra")
        path = _package_path(document.get("path"), f"document[{index}].path")
        text = document.get("text")
        if not isinstance(text, str):
            _refuse(STALE_AUTHORITY, f"document[{index}].text must be a string")
        if path in seen:
            _refuse(STALE_AUTHORITY, f"duplicate document path: {path}")
        seen.add(path)

        if path in retired_paths:
            if text != RETIRED_PH1_STATEMENT or len(text.encode("utf-8")) != 53:
                _refuse(
                    STALE_AUTHORITY,
                    f"retirement ledger bytes are stale: {path}",
                )
            retired_exceptions.append(path)
            continue
        if _contradictory_ph1_assertion(text):
            _refuse(
                CONTRADICTION,
                f"superseded Ph1 Evaluator-engagement assertion outside exact retirement exception: {path}",
            )

    if retired_exceptions != [RETIREMENT_LEDGER_PATH]:
        _refuse(STALE_AUTHORITY, "required retirement ledger document is missing")

    return {
        "schema_version": "1.0.0",
        "status": "verified",
        "policy_id": policy_id,
        "documents_checked": len(documents),
        "retirement_exceptions": sorted(retired_exceptions),
        "phase_matrix": copy.deepcopy(PHASE_MATRIX),
        "findings": [],
    }


def _discover_documents(root: Path) -> list[dict[str, str]]:
    if not root.is_dir():
        _refuse(STALE_AUTHORITY, f"package root is not a directory: {root}")
    candidates: set[Path] = set()
    for relative in _ROOT_DOCUMENTS:
        path = root / relative
        if not path.is_file():
            _refuse(STALE_AUTHORITY, f"required live contract is missing: {relative}")
        candidates.add(path)
    for relative in _LIVE_ROOTS:
        live_root = root / relative
        if not live_root.is_dir():
            _refuse(STALE_AUTHORITY, f"required live contract root is missing: {relative}")
        for path in live_root.rglob("*"):
            if (
                path.is_file()
                and path.suffix.lower() in _TEXT_SUFFIXES
                and not any(part in _GENERATED_PARTS for part in path.parts)
            ):
                candidates.add(path)

    documents: list[dict[str, str]] = []
    for path in sorted(candidates, key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        try:
            text = path.read_bytes().decode("utf-8", errors="strict")
        except (OSError, UnicodeError) as exc:
            _refuse(STALE_AUTHORITY, f"cannot read live contract {relative}: {exc}")
        documents.append({"path": relative, "text": text})
    return documents


def _load_package_policy(root: Path) -> dict[str, Any]:
    path = root / POLICY_RELATIVE_PATH
    try:
        policy = json.loads(path.read_text(encoding="utf-8", errors="strict"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _refuse(STALE_AUTHORITY, f"cannot load phase authority {POLICY_RELATIVE_PATH}: {exc}")
    if not isinstance(policy, dict):
        _refuse(STALE_AUTHORITY, "phase authority JSON root must be an object")
    return policy


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the package phase-engagement authority and live prose."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="Package root override for synthetic verification.",
    )
    args = parser.parse_args(argv)
    root = args.root.absolute()
    try:
        policy = _load_package_policy(root)
        documents = _discover_documents(root)
        receipt = check_phase_engagement(policy, documents)
    except PhaseEngagementRefusal as exc:
        print(
            f"phase_engagement_check: FAIL code={exc.code} detail={exc.detail}",
            file=sys.stderr,
        )
        return 1
    print(
        "phase_engagement_check: PASS "
        f"documents={receipt['documents_checked']} "
        f"retirement_exceptions={len(receipt['retirement_exceptions'])} blockers=0"
    )
    return 0


__all__ = [
    "PhaseEngagementRefusal",
    "check_phase_engagement",
    "CONTRADICTION",
    "STALE_AUTHORITY",
]


if __name__ == "__main__":
    raise SystemExit(main())
