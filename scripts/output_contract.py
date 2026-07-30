#!/usr/bin/env python3
"""Canonical resolver and semantic validator for typed output transactions.

The JSON contract is the registry authority.  This module deliberately does
not duplicate its class, trigger, scope, context, or cardinality tables.
Callers receive only the stable diagnostics frozen by the v0.42 C0 contract.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator


_DRIVE = re.compile(r"^[A-Za-z]:")
_DEVICE_PREFIXES = ("//?/", "//./")
_CLOSURE_STATES = frozenset({"emitted", "not_applicable", "suppressed"})
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

_DIAGNOSTIC_ORDER = (
    "CONTRACT-HASH-STALE",
    "OUTPUT-POPULATION-MISMATCH",
    "TRIGGER-UNKNOWN",
    "CLASS-UNKNOWN",
    "OCCURRENCE-DUPLICATE",
    "OCCURRENCE-CLOSURE-MISSING",
    "OCCURRENCE-STATE-CONTRADICTORY",
    "CONTEXT-SCOPE-MISMATCH",
    "CARDINALITY-VIOLATION",
    "ORDER-VIOLATION",
    "PATH-TRAVERSAL",
    "PATH-COLLISION",
    "PATH-ESCAPE",
)


def _add(diagnostics: set[str], code: str) -> None:
    """Add one stable code; callers intentionally do not receive prose drift."""
    diagnostics.add(code)


def _ordered(diagnostics: Iterable[str]) -> list[str]:
    order = {code: index for index, code in enumerate(_DIAGNOSTIC_ORDER)}
    return sorted(
        {code for code in diagnostics if code in order},
        key=lambda code: order[code],
    )


def load_contract(contract_path: str | Path) -> dict[str, Any]:
    """Read the exact output registry selected by the caller."""
    document = json.loads(Path(contract_path).read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("role/output contract must be a JSON object")
    return document


def normalized_file_sha256(path: str | Path) -> str:
    """Hash exact bytes after the repository's governed CRLF-to-LF transform."""
    payload = Path(path).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(payload).hexdigest()


def _nfc(value: Any) -> Any:
    """Recursively normalize every JSON string, including object keys."""
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_nfc(item) for item in value]
    if isinstance(value, tuple):
        return [_nfc(item) for item in value]
    if isinstance(value, Mapping):
        normalized: dict[Any, Any] = {}
        for key, item in value.items():
            normalized_key = _nfc(key)
            if normalized_key in normalized:
                raise ValueError("Unicode normalization creates a duplicate JSON key")
            normalized[normalized_key] = _nfc(item)
        return normalized
    return value


def compute_occurrence_id(
    *,
    contract_id: str,
    contract_version: str,
    contract_sha256: str,
    work_id: str,
    invocation_scope: str,
    class_id: str,
    trigger_id: str,
    context: Mapping[str, Any],
    ordinal: int,
    triggering_evidence_sha256: str,
) -> str:
    """Compute the C0-frozen typed-output occurrence identity."""
    identity = {
        "contract_id": contract_id,
        "contract_version": contract_version,
        "contract_sha256": contract_sha256,
        "work_id": work_id,
        "invocation_scope": invocation_scope,
        "class_id": class_id,
        "trigger_id": trigger_id,
        "context": context,
        "ordinal": ordinal,
        "triggering_evidence_sha256": triggering_evidence_sha256,
    }
    canonical = (
        json.dumps(
            _nfc(identity),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _json_pointer(parts: Iterable[object]) -> str:
    encoded = [str(part).replace("~", "~0").replace("/", "~1") for part in parts]
    return "/" + "/".join(encoded) if encoded else "/"


def contract_schema_validation_errors(contract_path: str | Path) -> list[str]:
    """Return deterministic schema detail without minting a diagnostic code."""
    path = Path(contract_path)
    schema_path = path.parent / "schemas" / "role_output_contract.schema.json"
    try:
        contract = load_contract(path)
        schema = load_contract(schema_path)
        validator = Draft202012Validator(schema)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return [f"SCHEMA / unavailable: {type(exc).__name__}: {exc}"]
    details = []
    for error in sorted(
        validator.iter_errors(contract),
        key=lambda item: (tuple(str(part) for part in item.absolute_path), item.validator, item.message),
    ):
        details.append(
            f"SCHEMA {_json_pointer(error.absolute_path)} {error.validator}: {error.message}"
        )
    return details


def normalize_windows_relative_path(value: object) -> str:
    """Return a slash/NFC/case-folded key for a safe relative path.

    ``ValueError`` means the input is absolute, drive/UNC/device addressed, or
    contains traversal.  The original spelling is not returned because this
    function is for comparison and collision detection, not presentation.
    """
    if not isinstance(value, str) or not value:
        raise ValueError("path is empty or non-text")
    normalized = unicodedata.normalize("NFC", value.replace("\\", "/"))
    if (
        normalized.startswith("/")
        or normalized.startswith("//")
        or normalized.casefold().startswith(_DEVICE_PREFIXES)
        or _DRIVE.match(normalized)
    ):
        raise ValueError("path is absolute or device addressed")
    parts = normalized.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError("path is empty, ambiguous, or traversing")
    # PurePosixPath is used only after the platform-independent rejection
    # above, so Windows comparison is deterministic on every host.
    return PurePosixPath(*parts).as_posix().casefold()


def resolve_output_class(
    contract: Mapping[str, Any], class_id: str
) -> Mapping[str, Any] | None:
    """Resolve a triggered class solely through the versioned registry."""
    rows = contract.get("triggered_output_classes")
    if not isinstance(rows, Mapping):
        return None
    row = rows.get(class_id)
    return row if isinstance(row, Mapping) else None


def _context_kind(document: Mapping[str, Any], occurrence: Mapping[str, Any]) -> str | None:
    context = occurrence.get("context", document.get("context"))
    if not isinstance(context, Mapping):
        return None
    kind = context.get("kind")
    return kind if isinstance(kind, str) else None


def _validate_path(
    value: object, seen: dict[str, str], diagnostics: set[str]
) -> None:
    try:
        key = normalize_windows_relative_path(value)
    except ValueError:
        _add(diagnostics, "PATH-TRAVERSAL")
        return
    rendered = str(value)
    if key in seen and seen[key] != rendered:
        _add(diagnostics, "PATH-COLLISION")
    else:
        seen[key] = rendered


def _ordering_dependencies(rule: object) -> tuple[set[str], set[str]]:
    """Decode the registry's compact ordering vocabulary without class tables."""
    if not isinstance(rule, str):
        return set(), set()
    after: set[str] = set()
    before: set[str] = set()
    if rule.startswith("after_"):
        after.update(re.findall(r"F[1-9](?:_[A-Za-z0-9]+)*", rule[6:]))
        # Current registry intentionally uses compact ``F4_F5_F7`` tokens.
        after.update(re.findall(r"F[1-9]", rule[6:]))
    if rule.startswith("before_"):
        before.update(re.findall(r"F[1-9](?:_[A-Za-z0-9]+)*", rule[7:]))
        before.update(re.findall(r"F[1-9]", rule[7:]))
    return after, before


def validate_output_transaction(
    contract_path: str | Path, document: Mapping[str, Any]
) -> list[str]:
    """Validate occurrence, closure, context, cardinality, and ordering rules.

    Structural JSON-Schema parity for the registry is checked by the package's
    schema runtime gate.  This function resolves all behavioral facts from the
    caller-pinned registry bytes and returns stable cross-system diagnostics.
    """
    diagnostics: set[str] = set()
    try:
        contract = load_contract(contract_path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return ["CONTRACT-HASH-STALE"]

    if contract_schema_validation_errors(contract_path):
        _add(diagnostics, "CONTRACT-HASH-STALE")

    try:
        exact_contract_sha256 = normalized_file_sha256(contract_path)
    except OSError:
        exact_contract_sha256 = None
    contract_sha256 = document.get("contract_sha256")
    if exact_contract_sha256 is None or contract_sha256 != exact_contract_sha256:
        _add(diagnostics, "CONTRACT-HASH-STALE")

    if (
        document.get("contract_id") != contract.get("contract_id")
        or document.get("contract_version") != contract.get("schema_version")
    ):
        _add(diagnostics, "CONTRACT-HASH-STALE")

    populations = set(contract.get("output_populations", ()))
    fixed_roles = contract.get("fixed_roles", {})
    triggered = contract.get("triggered_output_classes", {})
    if not isinstance(fixed_roles, Mapping):
        fixed_roles = {}
    if not isinstance(triggered, Mapping):
        triggered = {}

    occurrences = document.get("trigger_occurrences", ())
    closures = document.get("closures", document.get("trigger_closures", ()))
    if not isinstance(occurrences, list):
        occurrences = []
        _add(diagnostics, "OCCURRENCE-CLOSURE-MISSING")
    if not isinstance(closures, list):
        closures = []
        _add(diagnostics, "OCCURRENCE-CLOSURE-MISSING")

    occurrence_ids = [
        row.get("occurrence_id")
        for row in occurrences
        if isinstance(row, Mapping)
    ]
    if any(count > 1 for count in Counter(occurrence_ids).values()):
        _add(diagnostics, "OCCURRENCE-DUPLICATE")

    closure_rows: dict[object, list[Mapping[str, Any]]] = defaultdict(list)
    for row in closures:
        if isinstance(row, Mapping):
            closure_rows[row.get("occurrence_id")].append(row)

    scope = document.get("invocation_scope")
    work_id = document.get("work_id")
    if (
        not isinstance(work_id, str)
        or not work_id
        or scope not in contract.get("invocation_scopes", ())
    ):
        _add(diagnostics, "CONTEXT-SCOPE-MISMATCH")
    seen_paths: dict[str, str] = {}
    class_counts: Counter[tuple[str, str | None]] = Counter()
    class_ordinals: dict[tuple[str, str | None], list[int]] = defaultdict(list)

    for occurrence in occurrences:
        if not isinstance(occurrence, Mapping):
            _add(diagnostics, "OCCURRENCE-STATE-CONTRADICTORY")
            continue
        occurrence_id = occurrence.get("occurrence_id")
        population = occurrence.get("population")
        class_id = occurrence.get("class_id", occurrence.get("role_id"))
        row: Mapping[str, Any] | None = None

        if population not in populations:
            _add(diagnostics, "OUTPUT-POPULATION-MISMATCH")
        if class_id in triggered:
            if population != "triggered_class":
                _add(diagnostics, "OUTPUT-POPULATION-MISMATCH")
            row = resolve_output_class(contract, str(class_id))
        elif class_id in fixed_roles:
            if population != "fixed_role":
                _add(diagnostics, "OUTPUT-POPULATION-MISMATCH")
            candidate = fixed_roles.get(class_id)
            row = candidate if isinstance(candidate, Mapping) else None
        else:
            _add(diagnostics, "CLASS-UNKNOWN")

        if row is not None and population == "triggered_class":
            if occurrence.get("trigger_id") != row.get("trigger_id"):
                _add(diagnostics, "TRIGGER-UNKNOWN")
            kind = _context_kind(document, occurrence)
            allowed_contexts = row.get("context_kinds", ())
            allowed_scopes = row.get("invocation_scopes", ())
            if kind not in allowed_contexts or scope not in allowed_scopes:
                _add(diagnostics, "CONTEXT-SCOPE-MISMATCH")
            count_key = (str(class_id), kind)
            class_counts[count_key] += 1
            ordinal = occurrence.get("ordinal")
            if isinstance(ordinal, int) and not isinstance(ordinal, bool):
                class_ordinals[count_key].append(ordinal)

        evidence_sha256 = occurrence.get("triggering_evidence_sha256")
        context = occurrence.get("context", document.get("context"))
        ordinal = occurrence.get("ordinal")
        identity_fields_valid = (
            isinstance(occurrence_id, str)
            and bool(_SHA256.fullmatch(occurrence_id))
            and isinstance(class_id, str)
            and bool(class_id)
            and isinstance(occurrence.get("trigger_id"), str)
            and bool(occurrence.get("trigger_id"))
            and isinstance(context, Mapping)
            and isinstance(ordinal, int)
            and not isinstance(ordinal, bool)
            and ordinal >= 1
            and isinstance(evidence_sha256, str)
            and bool(_SHA256.fullmatch(evidence_sha256))
            and isinstance(work_id, str)
            and bool(work_id)
            and isinstance(scope, str)
            and bool(scope)
            and isinstance(contract_sha256, str)
            and bool(_SHA256.fullmatch(contract_sha256))
        )
        if identity_fields_valid:
            try:
                expected_occurrence_id = compute_occurrence_id(
                    contract_id=str(document.get("contract_id")),
                    contract_version=str(document.get("contract_version")),
                    contract_sha256=contract_sha256,
                    work_id=work_id,
                    invocation_scope=scope,
                    class_id=class_id,
                    trigger_id=occurrence["trigger_id"],
                    context=context,
                    ordinal=ordinal,
                    triggering_evidence_sha256=evidence_sha256,
                )
            except (TypeError, ValueError):
                expected_occurrence_id = None
            if occurrence_id != expected_occurrence_id:
                _add(diagnostics, "OCCURRENCE-STATE-CONTRADICTORY")
        else:
            _add(diagnostics, "OCCURRENCE-STATE-CONTRADICTORY")

        matching_closures = closure_rows.get(occurrence_id, [])
        if not matching_closures:
            _add(diagnostics, "OCCURRENCE-CLOSURE-MISSING")
            continue
        if len(matching_closures) != 1:
            _add(diagnostics, "OCCURRENCE-STATE-CONTRADICTORY")
        closure = matching_closures[0]
        state = closure.get("state")
        artifact = closure.get("artifact")
        reason = closure.get("suppression_reason")
        if state not in _CLOSURE_STATES:
            _add(diagnostics, "OCCURRENCE-STATE-CONTRADICTORY")
        elif state == "emitted":
            if not isinstance(artifact, Mapping) or reason is not None:
                _add(diagnostics, "OCCURRENCE-STATE-CONTRADICTORY")
            elif "path" in artifact:
                _validate_path(artifact.get("path"), seen_paths, diagnostics)
        else:
            if artifact is not None or reason not in contract.get("suppression_reasons", ()):
                _add(diagnostics, "OCCURRENCE-STATE-CONTRADICTORY")

    known_ids = set(occurrence_ids)
    if any(row_id not in known_ids for row_id in closure_rows):
        _add(diagnostics, "OCCURRENCE-STATE-CONTRADICTORY")

    for (class_id, _kind), count in class_counts.items():
        row = resolve_output_class(contract, class_id)
        cardinality = row.get("cardinality", {}) if row else {}
        maximum = cardinality.get("maximum") if isinstance(cardinality, Mapping) else None
        minimum = cardinality.get("minimum", 0) if isinstance(cardinality, Mapping) else 0
        if (isinstance(maximum, int) and count > maximum) or count < minimum:
            _add(diagnostics, "CARDINALITY-VIOLATION")

    for ordinals in class_ordinals.values():
        if ordinals != sorted(ordinals) or len(ordinals) != len(set(ordinals)):
            _add(diagnostics, "ORDER-VIOLATION")

    observed_order = document.get("observed_order")
    if isinstance(observed_order, list):
        positions = {
            item: index for index, item in enumerate(observed_order) if isinstance(item, str)
        }

        def dependency_position(dependency: str) -> int | None:
            if dependency in positions:
                return positions[dependency]
            matches = [
                index
                for candidate, index in positions.items()
                if candidate.startswith(dependency + "_")
            ]
            return min(matches) if matches else None

        for class_id, position in positions.items():
            row = resolve_output_class(contract, class_id)
            if row is None:
                continue
            after, before = _ordering_dependencies(row.get("ordering"))
            if any(
                (dep_position := dependency_position(dep)) is not None
                and dep_position > position
                for dep in after
            ):
                _add(diagnostics, "ORDER-VIOLATION")
            if any(
                (dep_position := dependency_position(dep)) is not None
                and dep_position < position
                for dep in before
            ):
                _add(diagnostics, "ORDER-VIOLATION")

    return _ordered(diagnostics)


__all__ = [
    "compute_occurrence_id",
    "contract_schema_validation_errors",
    "load_contract",
    "normalize_windows_relative_path",
    "normalized_file_sha256",
    "resolve_output_class",
    "validate_output_transaction",
]
