#!/usr/bin/env python3
"""Verify one exact-byte, independently dispatched scholarly evaluation.

This verifier authenticates transaction structure, current bytes, check coverage,
and blocking disposition.  It deliberately does not infer whether an Evaluator's
scholarly judgment is true.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import stat
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

import assignment_dispatch_claim as dispatch
import obligation_result as obligations
import scholarly_claim_register as claim_register
import bibliography_review as bibliography
import coherence_review as coherence


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "references" / "schemas" / "scholarly_evaluation.schema.json"

SET_SCHEMA = "SET-SCHEMA"
SET_BINDING_MISSING = "SET-BINDING-MISSING"
SET_ARTIFACT_STALE = "SET-ARTIFACT-STALE"
SET_DISPATCH_SEPARATION = "SET-DISPATCH-SEPARATION"
SET_COVERAGE_INCOMPLETE = "SET-COVERAGE-INCOMPLETE"
SET_OMITTED_CHECK_INVALID = "SET-OMITTED-CHECK-INVALID"
SET_FINDING_UNRESOLVED = "SET-FINDING-UNRESOLVED"

SHA_RE = re.compile(r"^[0-9a-f]{64}$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
SEVERITY_RANK = {"ADVISORY": 0, "MINOR": 1, "MAJOR": 2, "BLOCKER": 3}
OMISSION_CODES = {"not_applicable", "capability_unavailable", "source_unavailable"}
PROFILE_AUTHORITY_ID = "scholarly-evaluation-v1"
PROFILE_AUTHORITY_VERSION = "1.0.0"
PROFILE_MINIMUM: dict[str, dict[str, Any]] = {
    "milestone_criteria": {"omissions": set(), "floors": {}},
    "claim_register": {"omissions": set(), "floors": {}},
    "scope_quantifier": {"omissions": set(), "floors": {}},
    "provenance_integrity": {
        "omissions": set(),
        "floors": {"SCHOLARLY-CONSTRUCTED-SYNTHESIS-AS-DIRECT-SOURCE": "MAJOR"},
    },
    "admission_use": {
        "omissions": set(),
        "floors": {"SCHOLARLY-DERIVATION-NO-ROLE": "MAJOR"},
    },
    "argument_leg": {
        "omissions": set(),
        "floors": {"SCHOLARLY-CROSS-LEG-GENERALIZATION": "MAJOR"},
    },
    "warrant_logic": {
        "omissions": set(),
        "floors": {
            "SCHOLARLY-NECESSARY-AS-SUFFICIENT": "MAJOR",
            "SCHOLARLY-DEFEATER-AS-SUFFICIENT": "MAJOR",
        },
    },
    "modal_consistency": {
        "omissions": set(),
        "floors": {
            "SCHOLARLY-UNHEDGED-AUTHOR-COMPARISON": "MAJOR",
            "SCHOLARLY-OPEN-QUESTION-SETTLED": "MAJOR",
        },
    },
    "grounding_citation": {"omissions": set(), "floors": {}},
    # references/ARGUMENT_COHERENCE.md section 8: the governed route's enforcement
    # point. A profile that omits this check is SET_COVERAGE_INCOMPLETE. Coverage
    # is mandatory; no finding-code floor is pinned here, because AC-1..AC-5
    # severity is assigned by SAFEGUARD Check 9 on the reviewed bytes and pinning
    # codes a project has not yet emitted would be a floor over nothing.
    "argument_coherence": {"omissions": set(), "floors": {}},
    "d_style": {"omissions": set(), "floors": {}},
    "reader_accessibility": {"omissions": set(), "floors": {}},
    "active_overlays": {"omissions": {"not_applicable"}, "floors": {}},
}


class EvaluationRefusal(RuntimeError):
    """One stable, typed scholarly-evaluation refusal."""

    def __init__(self, code: str, message: str, **details: Any) -> None:
        super().__init__(message)
        self.code = code
        self.details = details


@dataclass(frozen=True)
class BoundFile:
    path: Path
    payload: bytes
    binding: dict[str, Any]
    label: str


@dataclass(frozen=True)
class ConditionalPath:
    path: Path
    existed: bool
    label: str


STATIC_DEPENDENCY_PATHS = (
    SCHEMA,
    ROOT / 'scripts' / 'bibliography_review.py',
    ROOT / 'references' / 'CITATION_DISCIPLINE.md',
    ROOT / 'scripts' / 'coherence_review.py',
    ROOT / 'scripts' / 'coherence_prefilter.py',
    ROOT / 'references' / 'ARGUMENT_COHERENCE.md',
    ROOT / 'references' / 'SAFEGUARD_LAYER.md',
    dispatch.CLAIM_SCHEMA,
    dispatch.CONSUMPTION_SCHEMA,
    dispatch.HOST_SCHEMA,
    dispatch.ISSUANCE_SCHEMA,
    dispatch.KERNEL_AUTHORIZATION_SCHEMA,
    obligations.RESULT_SCHEMA_PATH,
    obligations.ADJUDICATION_SCHEMA_PATH,
)


def _refuse(code: str, message: str, **details: Any) -> None:
    raise EvaluationRefusal(code, message, **details)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON value {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key {key!r}")
        value[key] = item
    return value


def _decode_json(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        _refuse(SET_SCHEMA, f"{label} is not strict JSON: {exc}")
    if not isinstance(value, dict):
        _refuse(SET_SCHEMA, f"{label} must contain a JSON object")
    return value


def finding_fingerprint(
    *, artifact_sha256: str, claim_register_sha256: str, finding: dict[str, Any]
) -> str:
    """Return the frozen current-evidence identity for an Evaluator finding."""

    material = {
        "artifact_sha256": artifact_sha256,
        "claim_register_sha256": claim_register_sha256,
        "finding_id": finding.get("finding_id"),
        "code": finding.get("code"),
        "severity": finding.get("severity"),
        "claim_id": finding.get("claim_id"),
        "span_sha256": finding.get("span", {}).get("sha256"),
        "evidence": finding.get("evidence"),
        "reasoning": finding.get("reasoning"),
        "required_disposition": finding.get("required_disposition"),
        "disposition": finding.get("disposition"),
    }
    return _sha(_canonical(material))


def _is_link(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        attributes = getattr(os.lstat(path), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400))


def _safe_relative(root: Path, raw: Any, label: str) -> Path:
    if not isinstance(raw, str) or not raw or "\\" in raw:
        _refuse(SET_SCHEMA, f"{label} path is not a non-empty POSIX path")
    relative = PurePosixPath(raw)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        _refuse(SET_SCHEMA, f"{label} path is unsafe: {raw!r}")
    if any(character in '<>:"|?*' or ord(character) < 0x20 for character in raw):
        _refuse(SET_SCHEMA, f"{label} path is unsafe: {raw!r}")
    cursor = root
    for part in relative.parts:
        if part != part.rstrip(" ."):
            _refuse(SET_SCHEMA, f"{label} path is Windows-ambiguous: {raw!r}")
        cursor /= part
        if (cursor.exists() or cursor.is_symlink()) and _is_link(cursor):
            _refuse(SET_ARTIFACT_STALE, f"{label} traverses a link or reparse point")
    root_real = Path(os.path.realpath(root))
    resolved = Path(os.path.realpath(cursor))
    try:
        resolved.relative_to(root_real)
    except ValueError:
        _refuse(SET_SCHEMA, f"{label} escapes the project root")
    return cursor


def _bind(root: Path, binding: Any, label: str) -> BoundFile:
    if not isinstance(binding, dict) or set(binding) != {"path", "sha256", "byte_length"}:
        _refuse(SET_SCHEMA, f"{label} is not an exact binding")
    if not SHA_RE.fullmatch(str(binding.get("sha256", ""))) or not isinstance(
        binding.get("byte_length"), int
    ) or binding["byte_length"] < 0:
        _refuse(SET_SCHEMA, f"{label} digest or byte length is malformed")
    path = _safe_relative(root, binding.get("path"), label)
    if not path.is_file() or _is_link(path):
        _refuse(SET_BINDING_MISSING, f"{label} is missing or not a plain file")
    try:
        payload = path.read_bytes()
    except OSError as exc:
        _refuse(SET_BINDING_MISSING, f"cannot read {label}: {exc}")
    if _sha(payload) != binding["sha256"] or len(payload) != binding["byte_length"]:
        _refuse(SET_ARTIFACT_STALE, f"{label} does not match its exact binding")
    return BoundFile(path=path, payload=payload, binding=binding, label=label)


def _bind_if_present(root: Path, binding: Any, label: str) -> BoundFile | None:
    """Bind a present file; return None when the named path is simply absent.

    Used for Generator envelope and Evaluator dispatch claim so C6 can still
    read already-staged bytes when no generator run occurred. A present stale
    digest still refuses. A link or reparse point is not treated as absence.
    """

    if not isinstance(binding, dict) or set(binding) != {"path", "sha256", "byte_length"}:
        _refuse(SET_SCHEMA, f"{label} is not an exact binding")
    if not SHA_RE.fullmatch(str(binding.get("sha256", ""))) or not isinstance(
        binding.get("byte_length"), int
    ) or binding["byte_length"] < 0:
        _refuse(SET_SCHEMA, f"{label} digest or byte length is malformed")
    path = _safe_relative(root, binding.get("path"), label)
    if not path.exists() and not path.is_symlink():
        return None
    return _bind(root, binding, label)


def _json(bound: BoundFile) -> dict[str, Any]:
    return _decode_json(bound.payload, bound.label)


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.samefile(right)
    except OSError:
        return left.resolve() == right.resolve()


def _tree_state(root: Path) -> dict[str, tuple[str, bytes | str]]:
    """Capture exact files and link targets without following directory links."""

    if not root.exists():
        return {}
    state: dict[str, tuple[str, bytes | str]] = {}
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(root).as_posix()
        if _is_link(path):
            try:
                target = os.readlink(path)
            except OSError:
                target = "<unreadable-link>"
            state[relative] = ("link", target)
        elif path.is_file():
            state[relative] = ("file", path.read_bytes())
        elif path.is_dir():
            state[relative] = ("dir", b"")
    return state


def _watch_path(path: Path, label: str) -> BoundFile:
    if not path.is_file() or _is_link(path):
        _refuse(SET_BINDING_MISSING, f"{label} is missing or not a plain file")
    try:
        payload = path.read_bytes()
    except OSError as exc:
        _refuse(SET_BINDING_MISSING, f"cannot read {label}: {exc}")
    return BoundFile(path=path, payload=payload, binding={}, label=label)


def _dependency_rows(
    watched: list[BoundFile],
    assignment_root: Path,
    assignment_state: dict[str, tuple[str, bytes | str]],
) -> list[dict[str, Any]]:
    """Return the unique exact-byte inventory consumed by one verification.

    The assignment subtree is a load-bearing read surface even when a file is
    inspected only while deriving the globally unique dispatch consumption.
    Preserve every file from the equal pre/post snapshot, then merge the
    explicitly bound project and package files watched by the verifier.
    """

    dependencies: dict[Path, bytes] = {}
    for relative, (kind, payload) in assignment_state.items():
        if kind != "file":
            continue
        assert isinstance(payload, bytes)
        dependencies[(assignment_root / PurePosixPath(relative)).resolve()] = payload
    for bound in watched:
        resolved = bound.path.resolve()
        previous = dependencies.get(resolved)
        if previous is not None and previous != bound.payload:
            _refuse(SET_ARTIFACT_STALE, f"dependency inventory split for {bound.label}")
        dependencies[resolved] = bound.payload
    return [
        {
            "path": str(path),
            "sha256": _sha(payload),
            "byte_length": len(payload),
        }
        for path, payload in sorted(dependencies.items(), key=lambda item: str(item[0]))
    ]


def _merge_subordinate_dependencies(
    rows: Any, watched: list[BoundFile], label: str
) -> None:
    """Bind an authoritative subordinate read set without re-deriving it."""

    if not isinstance(rows, list):
        _refuse(SET_COVERAGE_INCOMPLETE, f"{label} did not return a dependency inventory")
    seen: set[Path] = set()
    for index, row in enumerate(rows):
        if (
            not isinstance(row, dict)
            or set(row) != {"path", "sha256", "byte_length"}
            or not isinstance(row.get("path"), str)
            or not Path(row["path"]).is_absolute()
            or not SHA_RE.fullmatch(str(row.get("sha256", "")))
            or not isinstance(row.get("byte_length"), int)
            or row["byte_length"] < 0
        ):
            _refuse(SET_COVERAGE_INCOMPLETE, f"{label} dependency {index} is malformed")
        path = Path(row["path"])
        bound = _watch_path(path, f"{label} dependency {index}")
        resolved = bound.path.resolve()
        if resolved in seen:
            _refuse(SET_COVERAGE_INCOMPLETE, f"{label} dependency inventory is duplicate")
        seen.add(resolved)
        if _sha(bound.payload) != row["sha256"] or len(bound.payload) != row["byte_length"]:
            _refuse(SET_ARTIFACT_STALE, f"{label} dependency changed after subordinate validation")
        watched.append(bound)


def _discover_exact_bindings(
    project: Path,
    value: Any,
    label: str,
    watched: list[BoundFile],
    seen: set[Path] | None = None,
) -> None:
    """Watch exact nested project/harness bindings consumed by subordinate verifiers."""

    if seen is None:
        seen = set()
    if isinstance(value, dict):
        if set(value) == {"path", "sha256", "byte_length"}:
            bound = _bind(project, value, label)
            resolved = bound.path.resolve()
            watched.append(bound)
            if resolved not in seen:
                seen.add(resolved)
                try:
                    nested = json.loads(
                        bound.payload.decode("utf-8", errors="strict"),
                        object_pairs_hook=_unique_object,
                        parse_constant=_reject_constant,
                    )
                except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                    nested = None
                if isinstance(nested, (dict, list)):
                    _discover_exact_bindings(
                        project, nested, f"{label} content", watched, seen
                    )
            return
        if {"root", "path", "sha256", "evidence_type"} <= set(value):
            root_value = value.get("root")
            kind = root_value.get("kind") if isinstance(root_value, dict) else root_value
            base = project if kind == "project" else ROOT if kind == "harness" else None
            if base is not None and isinstance(value.get("path"), str):
                path = _safe_relative(base, value["path"], label)
                watched_file = _watch_path(path, label)
                if _sha(watched_file.payload) != value.get("sha256"):
                    _refuse(SET_ARTIFACT_STALE, f"{label} assignment binding is stale")
                watched.append(watched_file)
                resolved = watched_file.path.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    try:
                        nested = json.loads(
                            watched_file.payload.decode("utf-8", errors="strict"),
                            object_pairs_hook=_unique_object,
                            parse_constant=_reject_constant,
                        )
                    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                        nested = None
                    if isinstance(nested, (dict, list)):
                        _discover_exact_bindings(
                            project, nested, f"{label} content", watched, seen
                        )
                return
        for key, item in value.items():
            _discover_exact_bindings(project, item, f"{label}.{key}", watched, seen)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _discover_exact_bindings(project, item, f"{label}[{index}]", watched, seen)


def _load_input(root: Path, path: Path, label: str) -> Path:
    absolute = path.absolute()
    if not absolute.is_file() or _is_link(absolute):
        _refuse(SET_BINDING_MISSING, f"{label} input is missing or not a plain file")
    try:
        absolute.resolve().relative_to(root.resolve())
    except ValueError:
        _refuse(SET_SCHEMA, f"{label} input is outside the project root")
    return absolute


def _schema_validate(value: Any) -> None:
    try:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        errors = sorted(
            Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value),
            key=lambda error: [str(part) for part in error.absolute_path],
        )
    except (OSError, json.JSONDecodeError) as exc:
        _refuse(SET_SCHEMA, f"scholarly evaluation schema is unavailable: {exc}")
    if errors:
        path = "/".join(str(part) for part in errors[0].absolute_path) or "$"
        _refuse(SET_SCHEMA, f"schema violation at {path}: {errors[0].message}")


def _closed(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        _refuse(SET_SCHEMA, f"{label} must contain exactly {sorted(fields)}")
    return value


def _profile_contract(profile: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, str], list[str], dict[str, Any]]:
    _closed(
        profile,
        {"schema_version", "profile_id", "checks", "obligation_registry", "obligations"},
        "scholarly profile",
    )
    if (
        profile.get("schema_version") != PROFILE_AUTHORITY_VERSION
        or profile.get("profile_id") != PROFILE_AUTHORITY_ID
    ):
        _refuse(SET_SCHEMA, "scholarly profile identity is malformed")
    checks = profile.get("checks")
    if not isinstance(checks, list) or not checks:
        _refuse(SET_COVERAGE_INCOMPLETE, "scholarly profile has no applicable checks")
    by_id: dict[str, dict[str, Any]] = {}
    code_owner: dict[str, str] = {}
    for row in checks:
        _closed(
            row,
            {"check_id", "allowed_omission_codes", "finding_severity_floor"},
            "scholarly profile check",
        )
        check_id = row.get("check_id")
        if not isinstance(check_id, str) or not ID_RE.fullmatch(check_id) or check_id in by_id:
            _refuse(SET_SCHEMA, "scholarly profile check ids are malformed or duplicate")
        allowed = row.get("allowed_omission_codes")
        floors = row.get("finding_severity_floor")
        if (
            not isinstance(allowed, list)
            or len(set(allowed)) != len(allowed)
            or any(code not in OMISSION_CODES for code in allowed)
            or not isinstance(floors, dict)
        ):
            _refuse(SET_SCHEMA, f"profile policy is malformed for {check_id}")
        for code, severity in floors.items():
            if (
                not isinstance(code, str)
                or not ID_RE.fullmatch(code)
                or severity not in SEVERITY_RANK
                or code in code_owner
            ):
                _refuse(SET_SCHEMA, f"finding code policy is malformed or duplicate: {code!r}")
            code_owner[code] = check_id
        by_id[check_id] = row
    missing = set(PROFILE_MINIMUM) - set(by_id)
    if missing:
        _refuse(
            SET_COVERAGE_INCOMPLETE,
            f"profile omits canonical checks: {sorted(missing)}",
        )
    for check_id, authority in PROFILE_MINIMUM.items():
        row = by_id[check_id]
        if not set(row["allowed_omission_codes"]) <= authority["omissions"]:
            _refuse(
                SET_OMITTED_CHECK_INVALID,
                f"profile widens canonical omission policy: {check_id}",
            )
        floors = row["finding_severity_floor"]
        for code, minimum in authority["floors"].items():
            actual = floors.get(code)
            if actual is None or SEVERITY_RANK[actual] < SEVERITY_RANK[minimum]:
                _refuse(
                    SET_SCHEMA,
                    f"profile weakens canonical finding floor: {check_id}/{code}",
                )
    obligation_ids = profile.get("obligations")
    if (
        not isinstance(obligation_ids, list)
        or len(set(obligation_ids)) != len(obligation_ids)
        or any(not isinstance(item, str) or not ID_RE.fullmatch(item) for item in obligation_ids)
    ):
        _refuse(SET_SCHEMA, "profile obligations are malformed or duplicate")
    registry_binding = profile.get("obligation_registry")
    return by_id, code_owner, obligation_ids, registry_binding


def _verify_generator_envelope(
    root: Path,
    envelope_bound: BoundFile,
    artifact_binding: dict[str, Any],
    evaluation_claim: dict[str, Any],
) -> tuple[str, Path, dict[str, Any]]:
    envelope = _json(envelope_bound)
    _closed(
        envelope,
        {"schema_version", "envelope_type", "dispatch_id", "role", "artifact"},
        "Generator envelope",
    )
    generation_binding = evaluation_claim.get("generation_claim")
    if not isinstance(generation_binding, dict) or not isinstance(generation_binding.get("path"), str):
        _refuse(SET_DISPATCH_SEPARATION, "Evaluator claim lacks a generation-claim binding")
    generation_path = _safe_relative(root, generation_binding["path"], "generation claim")
    try:
        generation_claim = dispatch.accept_claim_for_context(
            root,
            generation_path,
            expected_role="generator",
            expected_target=artifact_binding["path"],
            expected_receipt_id=evaluation_claim["receipt_id"],
        )
    except Exception as exc:
        _refuse(SET_DISPATCH_SEPARATION, f"generation dispatch does not authenticate: {exc}")
    expected = {
        "schema_version": "1.0.0",
        "envelope_type": "generator_envelope",
        "dispatch_id": generation_claim.get("claim_id"),
        "role": "generator",
        "artifact": artifact_binding,
    }
    if envelope != expected:
        _refuse(SET_DISPATCH_SEPARATION, "Generator envelope is stale or names another dispatch")
    return generation_claim["claim_id"], generation_path, generation_claim


def _derive_evaluation_consumption(
    root: Path,
    value: dict[str, Any],
    evaluation_path: Path,
    evaluation_payload: bytes,
    claim_bound: BoundFile,
    watched: list[BoundFile],
) -> tuple[dict[str, Any], dict[str, Any], Path]:
    """Derive the unique committed consumption that published this evaluation."""

    transaction_id = value["evaluation_dispatch"]["consumer_transaction_id"]
    expected_transaction = f"scholarly-evaluation:{value['evaluation_id']}"
    if transaction_id != expected_transaction:
        _refuse(
            SET_DISPATCH_SEPARATION,
            "evaluation consumer transaction does not derive from evaluation_id",
        )
    claim_preview = _decode_json(claim_bound.payload, "Evaluator dispatch claim")
    claim_id = claim_preview.get("claim_id")
    consumption_root = (
        root
        / "reviews"
        / ".harness"
        / "assignment"
        / "dispatch"
        / "consumptions"
    )
    matches: list[tuple[Path, dict[str, Any]]] = []
    if consumption_root.is_dir() and not _is_link(consumption_root):
        for lane in sorted(consumption_root.iterdir(), key=lambda item: item.name):
            if not lane.is_dir() or _is_link(lane):
                continue
            path = lane / "consumption.json"
            marker = lane / "commit_marker.json"
            if marker.exists() and (not marker.is_file() or _is_link(marker) or not path.is_file()):
                _refuse(
                    SET_DISPATCH_SEPARATION,
                    "committed consumption lane is malformed",
                )
            if not path.is_file():
                continue
            if _is_link(path):
                _refuse(SET_DISPATCH_SEPARATION, "dispatch consumption is a link")
            try:
                candidate = _decode_json(path.read_bytes(), "dispatch consumption")
            except EvaluationRefusal:
                _refuse(
                    SET_DISPATCH_SEPARATION,
                    "dispatch consumption candidate is malformed",
                )
            if candidate.get("consumer_transaction_id") != transaction_id:
                continue
            if not marker.is_file() or _is_link(marker):
                _refuse(
                    SET_DISPATCH_SEPARATION,
                    "matching evaluation consumption is not marker-committed",
                )
            matches.append((path, candidate))
    if len(matches) != 1:
        _refuse(
            SET_DISPATCH_SEPARATION,
            "exactly one committed consumption must globally match the evaluation transaction",
        )
    consumption_path, candidate = matches[0]
    if candidate.get("claim_id") != claim_id:
        _refuse(
            SET_DISPATCH_SEPARATION,
            "global evaluation transaction binds another Evaluator claim",
        )
    try:
        generation_verifier_id = claim_preview.get("generation_verifier", {}).get("transaction_id")
        generation_draft_id = claim_preview.get("generation_draft_governance", {}).get("evidence_id")
        evaluator_claim, consumption = dispatch.validate_consumed_claim_for_context(
            root,
            claim_bound.path,
            consumption_path,
            expected_role="evaluator",
            expected_target=value["artifact"]["path"],
            expected_receipt_id=claim_preview.get("receipt_id"),
            expected_artifact_sha256=value["artifact"]["sha256"],
            expected_generation_transaction_id=generation_verifier_id,
            expected_generation_evidence_id=generation_draft_id,
        )
    except Exception as exc:
        _refuse(SET_DISPATCH_SEPARATION, f"Evaluator dispatch does not authenticate: {exc}")
    relative_evaluation = evaluation_path.relative_to(root).as_posix()
    postimages = consumption.get("postimages", [])
    product_rows = [
        row
        for row in postimages
        if row.get("path") == relative_evaluation
    ]
    artifact_rows = [
        row for row in postimages if row.get("path") == value["artifact"]["path"]
    ]
    if (
        len(postimages) != 2
        or len({row.get("path") for row in postimages}) != 2
        or relative_evaluation == value["artifact"]["path"]
        or len(product_rows) != 1
        or len(artifact_rows) != 1
        or product_rows[0].get("sha256") != _sha(evaluation_payload)
        or product_rows[0].get("size") != len(evaluation_payload)
        or artifact_rows[0].get("sha256") != value["artifact"]["sha256"]
        or artifact_rows[0].get("size") != value["artifact"]["byte_length"]
    ):
        _refuse(
            SET_DISPATCH_SEPARATION,
            "dispatch consumption must bind exactly one manuscript and one evaluation product",
        )
    watched.append(_watch_path(consumption_path, "Evaluator dispatch consumption"))
    for name in ("publication_manifest.json", "commit_marker.json"):
        watched.append(_watch_path(consumption_path.parent / name, f"Evaluator consumption {name}"))
    _discover_exact_bindings(root, consumption, "Evaluator consumption", watched)
    return evaluator_claim, consumption, consumption_path


def _verify_span(
    artifact: bytes, claim: dict[str, Any], finding: dict[str, Any]
) -> None:
    span = finding["span"]
    start, end = span["byte_start"], span["byte_end"]
    if not (0 <= start < end <= len(artifact)):
        _refuse(SET_SCHEMA, f"finding span is out of range: {finding['finding_id']}")
    expected = span["text"].encode("utf-8")
    if artifact[start:end] != expected or _sha(expected) != span["sha256"]:
        _refuse(SET_ARTIFACT_STALE, f"finding span is stale: {finding['finding_id']}")
    locator = claim["locator"]
    if (
        finding["claim_id"] != claim["claim_id"]
        or span["text"] != claim["text"]
        or start != locator["byte_start"]
        or end != locator["byte_end"]
        or span["sha256"] != claim["span_sha256"]
        or span["locator"] != {"section": locator["section"], "line": locator["line"]}
    ):
        _refuse(SET_COVERAGE_INCOMPLETE, f"finding does not bind its exact registered claim: {finding['finding_id']}")


def _verify_findings(
    value: dict[str, Any], artifact: bytes, register: dict[str, Any],
    check_by_id: dict[str, dict[str, Any]], code_owner: dict[str, str],
    watched: list[BoundFile],
) -> tuple[set[str], list[dict[str, Any]]]:
    claims = {row["claim_id"]: row for row in register["claims"]}
    represented: set[str] = set()
    blockers: list[dict[str, Any]] = []
    ids: set[str] = set()
    fingerprints: set[str] = set()
    for finding in value["findings"]:
        finding_id = finding["finding_id"]
        if finding_id in ids or finding["current_fingerprint"] in fingerprints:
            _refuse(SET_SCHEMA, "finding ids and fingerprints must be unique")
        ids.add(finding_id)
        fingerprints.add(finding["current_fingerprint"])
        claim = claims.get(finding["claim_id"])
        if claim is None:
            _refuse(SET_COVERAGE_INCOMPLETE, f"finding references an unknown claim: {finding_id}")
        _verify_span(artifact, claim, finding)
        check_id = code_owner.get(finding["code"])
        if check_id is None:
            _refuse(SET_COVERAGE_INCOMPLETE, f"finding code is absent from the bound profile: {finding['code']}")
        floor = check_by_id[check_id]["finding_severity_floor"][finding["code"]]
        if SEVERITY_RANK[finding["severity"]] < SEVERITY_RANK[floor]:
            _refuse(SET_SCHEMA, f"finding severity is below the profile floor: {finding_id}")
        expected_fingerprint = finding_fingerprint(
            artifact_sha256=value["artifact"]["sha256"],
            claim_register_sha256=value["claim_register"]["sha256"],
            finding=finding,
        )
        if not hmac.compare_digest(finding["current_fingerprint"], expected_fingerprint):
            _refuse(SET_ARTIFACT_STALE, f"finding fingerprint is stale: {finding_id}")
        represented.add(check_id)
        if finding["disposition"] == "resolved":
            resolution = _bind(Path(value["_root"]), finding["resolution"], f"finding resolution {finding_id}")
            watched.append(resolution)
            resolution_value = _json(resolution)
            _discover_exact_bindings(
                Path(value["_root"]),
                resolution_value,
                f"finding resolution {finding_id}",
                watched,
            )
            if resolution_value != {
                "schema_version": "1.0.0",
                "artifact_sha256": value["artifact"]["sha256"],
                "finding_fingerprint": finding["current_fingerprint"],
                "verified": True,
            }:
                _refuse(SET_ARTIFACT_STALE, f"finding resolution is stale: {finding_id}")
        elif SEVERITY_RANK[finding["severity"]] >= SEVERITY_RANK["MAJOR"]:
            blockers.append(finding)
    return represented, blockers


def _verify_obligations(
    root: Path,
    value: dict[str, Any],
    artifact_binding: dict[str, Any],
    expected_ids: list[str],
    registry: dict[str, Any],
    watched: list[BoundFile],
    conditional_paths: list[ConditionalPath],
) -> list[dict[str, Any]]:
    seen: set[str] = set()
    blockers: list[dict[str, Any]] = []
    for entry in value["obligation_results"]:
        bound = _bind(root, entry["result"], "obligation result")
        watched.append(bound)
        result = _json(bound)
        _discover_exact_bindings(root, result, "obligation result", watched)
        obligation_id = result.get("obligation_id")
        if not isinstance(obligation_id, str) or obligation_id in seen:
            _refuse(SET_COVERAGE_INCOMPLETE, "obligation results are unknown or duplicate")
        seen.add(obligation_id)
        if result.get("artifact") != artifact_binding:
            _refuse(
                SET_ARTIFACT_STALE,
                f"obligation result binds another artifact: {obligation_id}",
            )
        adapter = registry.get("obligations", {}).get(obligation_id)
        if (
            isinstance(adapter, dict)
            and adapter.get("report_schema", {}).get("path")
            == obligations.DSTYLE_REPORT_SCHEMA_REL
        ):
            watched.append(
                _watch_path(
                    ROOT / obligations.DSTYLE_REPORT_SCHEMA_REL,
                    "D-STYLE obligation runtime",
                )
            )
            directives = root / "research_notes" / "directives.md"
            directives_existed = directives.exists()
            conditional_paths.append(
                ConditionalPath(
                    path=directives,
                    existed=directives_existed,
                    label="D-STYLE directives existence",
                )
            )
            if directives_existed:
                watched.append(_watch_path(directives, "D-STYLE directives"))
            for assistance_path, assistance_label in (
                (
                    root / "research_notes" / "assistance_log.md",
                    "D-STYLE research-notes assistance-log",
                ),
                (
                    root / "research_notes" / "disclosure.md",
                    "D-STYLE research-notes disclosure",
                ),
                (
                    root / "reviews" / "assistance_log.md",
                    "D-STYLE reviews assistance-log",
                ),
            ):
                assistance_existed = assistance_path.exists()
                conditional_paths.append(
                    ConditionalPath(
                        path=assistance_path,
                        existed=assistance_existed,
                        label=f"{assistance_label} existence",
                    )
                )
                if assistance_existed:
                    watched.append(_watch_path(assistance_path, assistance_label))
        adjudications = result.get("adjudications", [])
        identities = entry["adjudications"]
        if len(identities) != len(adjudications):
            _refuse(SET_COVERAGE_INCOMPLETE, f"adjudication coverage is incomplete: {obligation_id}")
        by_id = {row.get("adjudication_id"): row for row in adjudications}
        if len(by_id) != len(adjudications):
            _refuse(SET_COVERAGE_INCOMPLETE, f"adjudication ids are duplicate: {obligation_id}")
        for identity in identities:
            adjudication = by_id.get(identity["adjudication_id"])
            canonical = _canonical(adjudication) if adjudication is not None else b""
            if (
                adjudication is None
                or identity["canonical_sha256"] != _sha(canonical)
                or identity["canonical_byte_length"] != len(canonical)
            ):
                _refuse(SET_ARTIFACT_STALE, f"adjudication identity is stale: {obligation_id}")
        try:
            verified = obligations.verify_obligation_result(result, registry, root=root)
            if verified.get("lifecycle_eligible") is not True:
                _refuse(
                    SET_COVERAGE_INCOMPLETE,
                    f"obligation result is diagnostic-only: {obligation_id}",
                )
        except obligations.ObligationResultRefusal as exc:
            if exc.code == obligations.BLOCKING_OUTCOME:
                fingerprints = [
                    row.get("fingerprint")
                    for row in result.get("findings", [])
                    if row.get("severity") in {"BLOCKER", "MAJOR"}
                    and row.get("disposition") != "resolved"
                ]
                blockers.append(
                    {
                        "code": SET_FINDING_UNRESOLVED,
                        "message": f"obligation {obligation_id} remains blocking",
                        "scholarly_code": f"OBLIGATION:{obligation_id}",
                        "current_fingerprint": fingerprints[0] if fingerprints else bound.binding["sha256"],
                    }
                )
            else:
                _refuse(SET_COVERAGE_INCOMPLETE, f"obligation {obligation_id} does not verify: {exc.code}: {exc}")
    if seen != set(expected_ids):
        _refuse(SET_COVERAGE_INCOMPLETE, "obligation results do not exactly cover the bound profile")
    return blockers


def _verify_evaluation_transaction(
    project_root: Path,
    artifact_path: Path,
    register_path: Path,
    evaluation_path: Path,
    *,
    expected_evaluation: BoundFile | None = None,
    preflight_claim: Path | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Authenticate one evaluation transaction; do not infer judgment truth.

    Predecessor acceptance in ``phase_state`` is not a C6 input. Dest-safe
    sequence / source-hash / wiki-grounding misses stay on draft dispatch
    and FINAL apply; they do not refuse scholarly evaluate of named bytes.
    A missing Generator envelope or empty assignment_dispatch is not a bar
    on claim/derivation/warrant/citation of already-staged bytes. A present
    stale or wrong envelope still refuses. C6 does not invent an envelope
    and cannot mint CLEAN without Evaluator fire and unresolved-finding close.
    """

    root = project_root.absolute()
    if not root.is_dir() or _is_link(root):
        _refuse(SET_BINDING_MISSING, "project root is absent, not a directory, or a link")
    bound_files = [
        _watch_path(path, f"static verifier dependency {path.name}")
        for path in STATIC_DEPENDENCY_PATHS
    ]
    assignment_root = root / "reviews" / ".harness" / "assignment"
    assignment_initial = _tree_state(assignment_root)
    conditional_paths: list[ConditionalPath] = []
    artifact_input = _load_input(root, artifact_path, "artifact")
    register_input = _load_input(root, register_path, "claim register")
    if expected_evaluation is not None and preflight_claim is not None:
        evaluation_input = expected_evaluation.path.absolute()
        try:
            evaluation_input.resolve().relative_to(root.resolve())
        except ValueError:
            _refuse(SET_SCHEMA, "evaluation preflight path is outside the project root")
    else:
        evaluation_input = _load_input(root, evaluation_path, "evaluation")
    if expected_evaluation is not None and preflight_claim is not None:
        evaluation_payload = expected_evaluation.payload
        evaluation_snapshot = expected_evaluation
    elif expected_evaluation is not None:
        if not _same_path(evaluation_input, expected_evaluation.path):
            _refuse(SET_ARTIFACT_STALE, "authoritative evaluation path differs from the caller snapshot")
        try:
            current_evaluation_payload = evaluation_input.read_bytes()
        except OSError as exc:
            _refuse(SET_BINDING_MISSING, f"cannot reconcile evaluation input: {exc}")
        if current_evaluation_payload != expected_evaluation.payload:
            _refuse(SET_ARTIFACT_STALE, "authoritative evaluation bytes differ from the caller snapshot")
        evaluation_payload = expected_evaluation.payload
        evaluation_snapshot = expected_evaluation
    else:
        try:
            evaluation_payload = evaluation_input.read_bytes()
        except OSError as exc:
            _refuse(SET_BINDING_MISSING, f"cannot read evaluation input: {exc}")
        evaluation_snapshot = BoundFile(
            path=evaluation_input,
            payload=evaluation_payload,
            binding={},
            label="evaluation input",
        )
    value = _decode_json(evaluation_payload, "evaluation")
    _schema_validate(value)
    value["_root"] = str(root)

    if preflight_claim is None:
        bound_files.append(evaluation_snapshot)
    artifact = _bind(root, value["artifact"], "artifact")
    register_bound = _bind(root, value["claim_register"], "claim register")
    if not _same_path(artifact.path, artifact_input) or not _same_path(register_bound.path, register_input):
        _refuse(SET_ARTIFACT_STALE, "CLI inputs differ from evaluation bindings")
    bound_files.extend([artifact, register_bound])

    generator_envelope = _bind_if_present(
        root, value["generator_envelope"], "Generator envelope"
    )
    criteria_bound = _bind(root, value["milestone_criteria"], "milestone criteria")
    profile_bound = _bind(root, value["scholarly_profile"], "scholarly profile")
    claim_bound = _bind_if_present(
        root, value["evaluation_dispatch"]["claim"], "Evaluator dispatch claim"
    )
    bound_files.extend(
        item
        for item in (generator_envelope, criteria_bound, profile_bound, claim_bound)
        if item is not None
    )

    criteria = _json(criteria_bound)
    if (
        set(criteria) != {"schema_version", "milestone", "criteria"}
        or criteria.get("schema_version") != "1.0.0"
        or criteria.get("milestone") not in {"M1", "M2", "M3", "M4", "FINAL"}
        or not isinstance(criteria.get("criteria"), list)
        or not criteria["criteria"]
        or any(not isinstance(item, str) or not item.strip() for item in criteria["criteria"])
    ):
        _refuse(SET_SCHEMA, "milestone criteria are malformed")

    profile = _json(profile_bound)
    check_by_id, code_owner, obligation_ids, registry_binding = _profile_contract(profile)
    registry_bound = _bind(root, registry_binding, "obligation registry")
    bound_files.append(registry_bound)
    registry = _json(registry_bound)
    try:
        obligations.validate_obligation_registry(registry)
    except obligations.ObligationResultRefusal as exc:
        _refuse(SET_COVERAGE_INCOMPLETE, f"obligation registry does not verify: {exc.code}: {exc}")

    register = _json(register_bound)
    register_result = claim_register.validate_register_with_dependencies(
        artifact.path,
        register_bound.path,
        expected_register_payload=register_bound.payload,
    )
    _merge_subordinate_dependencies(
        register_result.get("dependencies"), bound_files, "claim-register validator"
    )
    if register_result.get("status") != "qualified":
        _refuse(SET_COVERAGE_INCOMPLETE, "claim register is not complete and current")

    if preflight_claim is not None and claim_bound is None:
        _refuse(SET_DISPATCH_SEPARATION, "preflight requires an authenticated Evaluator claim")
    evaluator_fire = False
    if claim_bound is None and generator_envelope is not None:
        _refuse(
            SET_DISPATCH_SEPARATION,
            "Generator envelope is stale or names another dispatch",
        )
    if claim_bound is not None:
        if preflight_claim is None:
            evaluator_claim, _, _ = _derive_evaluation_consumption(
                root,
                value,
                evaluation_input,
                evaluation_payload,
                claim_bound,
                bound_files,
            )
        else:
            preflight_claim_path = _load_input(root, preflight_claim, "preflight Evaluator claim")
            if not _same_path(claim_bound.path, preflight_claim_path):
                _refuse(SET_DISPATCH_SEPARATION, "preflight claim differs from evaluation binding")
            claim_value = _json(claim_bound)
            try:
                evaluator_claim = dispatch.accept_claim_for_context(
                    root, preflight_claim_path, expected_role="evaluator",
                    expected_target=artifact.path.relative_to(root).as_posix(),
                    expected_receipt_id=claim_value["receipt_id"],
                    expected_artifact_sha256=value["artifact"]["sha256"],
                )
            except (KeyError, dispatch.ReceiptTransactionError) as exc:
                _refuse(SET_DISPATCH_SEPARATION, f"Evaluator claim fails preflight: {exc}")
        if evaluator_claim.get("claim_kind") != "evaluation":
            _refuse(SET_DISPATCH_SEPARATION, "consumed dispatch is not an evaluation claim")
        _discover_exact_bindings(root, evaluator_claim, "Evaluator claim", bound_files)
        evaluator_fire = True
        generation_binding = evaluator_claim.get("generation_claim")
        generation_exists = False
        if isinstance(generation_binding, dict) and isinstance(
            generation_binding.get("path"), str
        ):
            generation_candidate = _safe_relative(
                root, generation_binding["path"], "generation claim"
            )
            if generation_candidate.is_file() and not _is_link(generation_candidate):
                generation_exists = True
        if generator_envelope is None:
            if generation_exists:
                _refuse(
                    SET_DISPATCH_SEPARATION,
                    "Generator envelope is stale or names another dispatch",
                )
            for path, label in (
                (
                    claim_bound.path.parent / "publication_manifest.json",
                    "Evaluator claim publication manifest",
                ),
                (
                    claim_bound.path.parent / "commit_marker.json",
                    "Evaluator claim commit marker",
                ),
            ):
                if path.is_file() and not _is_link(path):
                    bound_files.append(_watch_path(path, label))
            if register["review_dispatch"] != {
                "dispatch_id": evaluator_claim["claim_id"],
                "role": "evaluator",
            }:
                _refuse(
                    SET_DISPATCH_SEPARATION,
                    "claim register names another review dispatch",
                )
        else:
            generation_id, generation_path, generation_claim = _verify_generator_envelope(
                root, generator_envelope, value["artifact"], evaluator_claim
            )
            bound_files.append(_watch_path(generation_path, "nested Generator claim"))
            for path, label in (
                (
                    claim_bound.path.parent / "publication_manifest.json",
                    "Evaluator claim publication manifest",
                ),
                (
                    claim_bound.path.parent / "commit_marker.json",
                    "Evaluator claim commit marker",
                ),
                (
                    generation_path.parent / "publication_manifest.json",
                    "Generator claim publication manifest",
                ),
                (
                    generation_path.parent / "commit_marker.json",
                    "Generator claim commit marker",
                ),
            ):
                bound_files.append(_watch_path(path, label))
            _discover_exact_bindings(root, generation_claim, "Generator claim", bound_files)
            evaluator_id = evaluator_claim["claim_id"]
            separation = value["dispatch_separation"]
            if (
                generation_id == evaluator_id
                or separation["generator_claim_id"] != generation_id
                or separation["evaluator_claim_id"] != evaluator_id
                or separation["separate"] is not True
            ):
                _refuse(SET_DISPATCH_SEPARATION, "dispatch separation is false or stale")
            if separation["independence_level"] == "host_attested_independence":
                # Host attestations are higher-grade optional evidence.  Their exact
                # bytes are bound here; host semantics remain the host verifier's
                # authority.
                for index, binding in enumerate(separation["host_attestations"]):
                    bound_files.append(_bind(root, binding, f"host attestation {index}"))
            if register["review_dispatch"] != {
                "dispatch_id": evaluator_id,
                "role": "evaluator",
            }:
                _refuse(
                    SET_DISPATCH_SEPARATION,
                    "claim register names another review dispatch",
                )

    represented, finding_blockers = _verify_findings(
        value, artifact.payload, register, check_by_id, code_owner, bound_files
    )
    pass_ids: set[str] = set()
    for row in value["verdict"]["check_results"]:
        check_id = row["check_id"]
        if check_id not in check_by_id or check_id in pass_ids or check_id in represented:
            _refuse(SET_COVERAGE_INCOMPLETE, f"pass evidence is unknown, duplicate, or conflicts: {check_id}")
        pass_ids.add(check_id)
        for index, binding in enumerate(row["evidence"]):
            bound_files.append(_bind(root, binding, f"pass evidence {check_id}/{index}"))

    omission_ids: set[str] = set()
    for row in value["omitted_checks"]:
        check_id = row["check_id"]
        if (
            check_id not in check_by_id
            or check_id in omission_ids
            or check_id in represented
            or check_id in pass_ids
            or row["omission_code"] not in check_by_id[check_id]["allowed_omission_codes"]
        ):
            _refuse(SET_OMITTED_CHECK_INVALID, f"omission is not allowed or conflicts: {check_id}")
        omission_ids.add(check_id)
        for index, binding in enumerate(row["evidence"]):
            bound_files.append(_bind(root, binding, f"omission evidence {check_id}/{index}"))
    if represented | pass_ids | omission_ids != set(check_by_id):
        _refuse(SET_COVERAGE_INCOMPLETE, "profile check coverage is incomplete")

    obligation_blockers = _verify_obligations(
        root,
        value,
        value["artifact"],
        obligation_ids,
        registry,
        bound_files,
        conditional_paths,
    )
    blockers = [
        {
            "code": SET_FINDING_UNRESOLVED,
            "message": f"{finding['severity']} finding remains {finding['disposition']}",
            "scholarly_code": finding["code"],
            "current_fingerprint": finding["current_fingerprint"],
        }
        for finding in finding_blockers
    ] + obligation_blockers
    if bibliography.has_sources(artifact.payload.decode('utf-8-sig')):
        materials, material_bytes = [], {}
        for row in value.get('source_materials', []):
            bound = _bind(root, row['binding'], 'bibliography inspected material')
            bound_files.append(bound)
            material_bytes[str(bound.path)] = bound.payload
            materials.append({'source_id': row['source_id'], 'locator': row['locator'],
                              'path': str(bound.path), 'sha256': row['binding']['sha256']})
        try:
            bibliography.validate(artifact.payload.decode('utf-8-sig'), value.get('bibliography_review'),
                                  materials, lambda path: material_bytes[path])
        except bibliography.ReviewError as exc:
            blockers.append({'code': exc.code, 'message': str(exc),
                             'scholarly_code': 'BIBLIOGRAPHY-REVIEW-REQUIRED',
                             'current_fingerprint': value['artifact']['sha256']})
    # references/ARGUMENT_COHERENCE.md section 8. A check id and a generic
    # evidence binding cannot show the obligation ran, so the structured review
    # is validated against these artifact bytes, over the whole artifact, before
    # the verdict can be qualified. Absent, partial, stale or wrong-scope review
    # evidence is a blocker; a failing check still needs a valid review.
    if 'argument_coherence' in check_by_id:
        try:
            coherence.validate(artifact.payload.decode('utf-8-sig'), value.get('coherence_review'),
                               require_clear='argument_coherence' in pass_ids)
        except coherence.ReviewError as exc:
            blockers.append({'code': exc.code, 'message': str(exc),
                             'scholarly_code': 'COHERENCE-REVIEW-REQUIRED',
                             'current_fingerprint': value['artifact']['sha256']})
    if not evaluator_fire:
        blockers.append(
            {
                "code": SET_FINDING_UNRESOLVED,
                "message": "C6 cannot mint CLEAN without Evaluator fire",
                "scholarly_code": "EVALUATOR-FIRE-REQUIRED",
                "current_fingerprint": value["artifact"]["sha256"],
            }
        )
    expected_status = "blocked" if blockers else "qualified"
    if evaluator_fire and value["verdict"]["status"] != expected_status:
        _refuse(
            SET_FINDING_UNRESOLVED if blockers else SET_SCHEMA,
            f"verdict status must be {expected_status}",
            blockers=blockers,
        )

    # Marker-like final replay: every bound byte surface must remain unchanged
    # through the complete transaction validation.
    if _tree_state(assignment_root) != assignment_initial:
        _refuse(
            SET_ARTIFACT_STALE,
            "assignment dispatch/authority subtree changed during verification",
        )
    seen_paths: set[Path] = set()
    for bound in bound_files:
        resolved = bound.path.resolve()
        if resolved in seen_paths:
            continue
        seen_paths.add(resolved)
        try:
            current_payload = bound.path.read_bytes()
        except OSError:
            _refuse(
                SET_ARTIFACT_STALE,
                f"{bound.label} changed or became unreadable during verification",
            )
        if current_payload != bound.payload:
            _refuse(SET_ARTIFACT_STALE, f"{bound.label} changed during verification")
    for conditional in conditional_paths:
        if conditional.path.exists() is not conditional.existed:
            _refuse(SET_ARTIFACT_STALE, f"{conditional.label} changed during verification")
    dependencies = _dependency_rows(bound_files, assignment_root, assignment_initial)
    if blockers:
        return (
            {"status": "blocked", "evaluation_id": value["evaluation_id"], "findings": blockers},
            dependencies,
        )
    return ({
        "status": "qualified",
        "evaluation_id": value["evaluation_id"],
        "verdict": "qualified",
        "check_count": len(check_by_id),
        "finding_count": len(value["findings"]),
        "omitted_check_count": len(value["omitted_checks"]),
        "obligation_result_count": len(value["obligation_results"]),
        "judgment_truth_certified": False,
        "findings": [],
    }, dependencies)


def preflight_evaluation(
    project_root: Path,
    artifact_path: Path,
    register_path: Path,
    evaluation_path: Path,
    evaluation_payload: bytes,
    evaluation_claim: Path,
) -> dict[str, Any]:
    """Validate complete C6 judgment semantics before claim consumption."""

    snapshot = BoundFile(
        path=evaluation_path.absolute(),
        payload=evaluation_payload,
        binding={},
        label="unpublished evaluation preflight",
    )
    result, dependencies = _verify_evaluation_transaction(
        project_root,
        artifact_path,
        register_path,
        evaluation_path,
        expected_evaluation=snapshot,
        preflight_claim=evaluation_claim,
    )
    return {**result, "dependencies": dependencies}


def verify_evaluation(
    project_root: Path, artifact_path: Path, register_path: Path, evaluation_path: Path
) -> dict[str, Any]:
    """Preserve the qualified C6 verifier API and its established result shape."""

    result, _ = _verify_evaluation_transaction(
        project_root, artifact_path, register_path, evaluation_path
    )
    return result


def validate_scholarly_evaluation_binding(
    project_root: Path,
    artifact_path: Path,
    binding: dict[str, Any],
) -> dict[str, Any]:
    """Validate one lifecycle binding and return its authoritative read set.

    ``binding`` is intentionally smaller than the evaluation's internal exact
    bindings.  The evaluation bytes remain the sole source for locating the
    claim register and every nested transaction dependency.
    """

    root = project_root.absolute()
    if not root.is_dir() or _is_link(root):
        _refuse(SET_BINDING_MISSING, "project root is absent, not a directory, or a link")
    if not isinstance(binding, dict) or set(binding) != {
        "evidence_path",
        "evidence_sha256",
    }:
        _refuse(SET_SCHEMA, "scholarly evaluation binding must contain exactly evidence_path and evidence_sha256")
    if not SHA_RE.fullmatch(str(binding.get("evidence_sha256", ""))):
        _refuse(SET_SCHEMA, "scholarly evaluation binding digest is malformed")
    evaluation_path = _safe_relative(
        root, binding.get("evidence_path"), "scholarly evaluation binding"
    )
    if not evaluation_path.is_file() or _is_link(evaluation_path):
        _refuse(SET_BINDING_MISSING, "scholarly evaluation binding is missing or not a plain file")
    try:
        evaluation_payload = evaluation_path.read_bytes()
    except OSError as exc:
        _refuse(SET_BINDING_MISSING, f"cannot read scholarly evaluation binding: {exc}")
    if not hmac.compare_digest(_sha(evaluation_payload), binding["evidence_sha256"]):
        _refuse(SET_ARTIFACT_STALE, "scholarly evaluation binding digest is stale")
    evaluation_value = _decode_json(evaluation_payload, "scholarly evaluation binding")
    register_binding = evaluation_value.get("claim_register")
    if not isinstance(register_binding, dict):
        _refuse(SET_SCHEMA, "scholarly evaluation binding lacks a claim-register binding")
    register_bound = _bind(root, register_binding, "claim register")
    evaluation_snapshot = BoundFile(
        path=evaluation_path,
        payload=evaluation_payload,
        binding={
            "path": evaluation_path.resolve().relative_to(root.resolve()).as_posix(),
            "sha256": _sha(evaluation_payload),
            "byte_length": len(evaluation_payload),
        },
        label="lifecycle scholarly evaluation",
    )

    artifact_input = artifact_path
    if not artifact_input.is_absolute():
        artifact_input = _safe_relative(
            root, artifact_input.as_posix(), "scholarly evaluation artifact input"
        )
    result, dependencies = _verify_evaluation_transaction(
        root,
        artifact_input,
        register_bound.path,
        evaluation_path,
        expected_evaluation=evaluation_snapshot,
    )
    if result.get("status") == "blocked" and isinstance(result.get("findings"), list):
        blockers = result["findings"]
        if not blockers:
            _refuse(SET_SCHEMA, "blocked scholarly evaluation has no current blockers")
        _refuse(
            SET_FINDING_UNRESOLVED,
            "scholarly evaluation remains blocked",
            blockers=blockers,
        )
    if not (
        result.get("status") == "qualified"
        and result.get("verdict") == "qualified"
        and result.get("findings") == []
        and result.get("judgment_truth_certified") is False
    ):
        _refuse(SET_SCHEMA, "scholarly evaluation verifier returned a malformed qualification result")
    evaluation_dependencies = [
        row for row in dependencies if Path(row["path"]) == evaluation_path.resolve()
    ]
    if evaluation_dependencies != [
        {
            "path": str(evaluation_path.resolve()),
            "sha256": _sha(evaluation_snapshot.payload),
            "byte_length": len(evaluation_snapshot.payload),
        }
    ]:
        _refuse(SET_ARTIFACT_STALE, "qualified evaluation dependency differs from the caller snapshot")
    normalized_path = evaluation_path.resolve().relative_to(root.resolve()).as_posix()
    normalized_artifact_path = artifact_input.resolve().relative_to(
        root.resolve()
    ).as_posix()
    return {
        "binding": {
            "evidence_path": normalized_path,
            "evidence_sha256": _sha(evaluation_snapshot.payload),
        },
        "artifact": {
            "path": normalized_artifact_path,
            "sha256": evaluation_value["artifact"]["sha256"],
            "byte_length": evaluation_value["artifact"]["byte_length"],
        },
        "evaluation_id": result["evaluation_id"],
        "status": result["status"],
        "judgment_truth_certified": False,
        "dependencies": dependencies,
    }


def _finding(exc: EvaluationRefusal) -> dict[str, Any]:
    row = {"code": exc.code, "message": str(exc)}
    row.update({key: value for key, value in exc.details.items() if key != "blockers"})
    return row


def canonical_scholarly_profile(
    registry_binding: dict[str, Any],
    obligation_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Return the dest-safe C6 profile document. Does not mint CLEAN."""

    if not isinstance(registry_binding, dict) or set(registry_binding) != {
        "path",
        "sha256",
        "byte_length",
    }:
        _refuse(SET_SCHEMA, "obligation registry is not an exact binding")
    ids = list(obligation_ids or [])
    if len(set(ids)) != len(ids) or any(
        not isinstance(item, str) or not ID_RE.fullmatch(item) for item in ids
    ):
        _refuse(SET_SCHEMA, "profile obligations are malformed or duplicate")
    return {
        "schema_version": PROFILE_AUTHORITY_VERSION,
        "profile_id": PROFILE_AUTHORITY_ID,
        "checks": [
            {
                "check_id": check_id,
                "allowed_omission_codes": sorted(authority["omissions"]),
                "finding_severity_floor": dict(authority["floors"]),
            }
            for check_id, authority in PROFILE_MINIMUM.items()
        ],
        "obligation_registry": registry_binding,
        "obligations": ids,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--claim-register", required=True, type=Path)
    parser.add_argument("--evaluation", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = verify_evaluation(
            args.project_root, args.artifact, args.claim_register, args.evaluation
        )
    except EvaluationRefusal as exc:
        blockers = exc.details.get("blockers")
        findings = blockers if isinstance(blockers, list) and blockers else [_finding(exc)]
        print(json.dumps({"status": "refused", "findings": findings}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 1 if result["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "EvaluationRefusal",
    "finding_fingerprint",
    "verify_evaluation",
    "canonical_scholarly_profile",
    "SET_SCHEMA",
    "SET_BINDING_MISSING",
    "SET_ARTIFACT_STALE",
    "SET_DISPATCH_SEPARATION",
    "SET_COVERAGE_INCOMPLETE",
    "SET_OMITTED_CHECK_INVALID",
    "SET_FINDING_UNRESOLVED",
]
