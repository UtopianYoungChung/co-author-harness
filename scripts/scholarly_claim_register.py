#!/usr/bin/env python3
"""Validate and render an exact-byte scholarly claim register.

The JSON register is authoritative. Rendered Markdown is a convenience view
only and never upgrades an incomplete or blocked coverage disposition.

Schema 1.0.0 remains listed-claim partition only. Schema 1.1.0 adds a
declared byte-accounted document_inventory. Byte coverage is not semantic
claim-universe completeness and is not a human reference inventory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from referencing.exceptions import Unresolvable


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "references" / "schemas" / "scholarly_claim_register.schema.json"

VIEWPOINTS = {
    "source_ascription",
    "author_analysis",
    "project_position",
    "constructed_synthesis",
    "open_question",
}
PROVENANCE = {
    "direct_source",
    "cross_source_comparison",
    "author_derivation",
    "project_governance",
    "constructed_example",
    "unresolved",
}
EVIDENCE_REQUIRED_PROVENANCE = {
    "direct_source",
    "cross_source_comparison",
    "project_governance",
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
FENCE_OPEN_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
ATX_RE = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*)|[ \t]*)$")
ATX_CLOSING_RE = re.compile(r"^(.*?)(?:[ \t]+#+)[ \t]*$")
COMMONMARK_LINE_END_RE = re.compile(r"\r\n|\n|\r")
EVIDENCE_SPAN_FIELDS = {"path", "sha256", "byte_start", "byte_end", "span_sha256"}
INVENTORY_WHITESPACE = frozenset({0x09, 0x0A, 0x0D, 0x20})
INVENTORY_LIMITATION = (
    "Byte coverage of a block does not establish that every assertion in that "
    "block was inventoried or reviewed. A checked inventory is not an "
    "independently established human reference inventory."
)


class ClaimRegisterError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class _ReadSet:
    """Exact byte snapshots consumed by one claim-register validation."""

    def __init__(self) -> None:
        self._entries: dict[Path, tuple[bytes, str, str]] = {}

    def add(self, path: Path, payload: bytes, code: str, label: str) -> None:
        resolved = path.resolve(strict=False)
        previous = self._entries.get(resolved)
        if previous is not None and previous[0] != payload:
            raise ClaimRegisterError(code, f"split read for {label}")
        self._entries[resolved] = (payload, code, label)

    def replay_finding(self) -> dict[str, str] | None:
        for path, (payload, code, label) in sorted(
            self._entries.items(), key=lambda item: str(item[0])
        ):
            try:
                current = path.read_bytes()
            except OSError:
                return _finding(code, f"{label} changed or became unreadable during validation")
            if current != payload:
                return _finding(code, f"{label} changed during validation")
        return None

    def rows(self) -> list[dict[str, Any]]:
        return [
            {
                "path": str(path),
                "sha256": _sha_bytes(payload),
                "byte_length": len(payload),
            }
            for path, (payload, _, _) in sorted(
                self._entries.items(), key=lambda item: str(item[0])
            )
        ]


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ClaimRegisterError("SCR-SCHEMA", f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _reject_constant(value: str) -> None:
    raise ClaimRegisterError("SCR-SCHEMA", f"non-finite JSON number: {value}")


def _decode_register(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_pairs,
            parse_constant=_reject_constant,
        )
    except ClaimRegisterError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ClaimRegisterError("SCR-SCHEMA", f"cannot decode register: {exc}") from exc
    if not isinstance(value, dict):
        raise ClaimRegisterError("SCR-SCHEMA", "register must be one JSON object")
    return value


def _load_json(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ClaimRegisterError("SCR-SCHEMA", f"cannot load register: {exc}") from exc
    return _decode_register(raw)


def _finding(code: str, message: str, claim_id: str | None = None) -> dict[str, str]:
    row = {"code": code, "message": message}
    if claim_id is not None:
        row["claim_id"] = claim_id
    return row


def _early_cardinality_findings(value: dict[str, Any]) -> list[dict[str, str]]:
    claims = value.get("claims")
    if not isinstance(claims, list):
        return []
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            continue
        claim_id = claim.get("claim_id") if isinstance(claim.get("claim_id"), str) else f"index:{index}"
        for field, allowed, missing_code, ambiguous_code in (
            ("viewpoint", VIEWPOINTS, "SCR-VIEWPOINT-MISSING", "SCR-VIEWPOINT-AMBIGUOUS"),
            ("provenance", PROVENANCE, "SCR-PROVENANCE-MISSING", "SCR-PROVENANCE-AMBIGUOUS"),
        ):
            if field not in claim or claim[field] in (None, ""):
                return [_finding(missing_code, f"claim has no {field}", claim_id)]
            field_value = claim[field]
            if isinstance(field_value, (list, dict, tuple, set)):
                return [_finding(ambiguous_code, f"claim has more than one {field}", claim_id)]
            if not isinstance(field_value, str) or field_value not in allowed:
                return [_finding("SCR-SCHEMA", f"claim has invalid {field}", claim_id)]
    return []


def _early_locator_findings(value: dict[str, Any]) -> list[dict[str, str]]:
    claims = value.get("claims")
    if not isinstance(claims, list):
        return []
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            continue
        claim_id = claim.get("claim_id") if isinstance(claim.get("claim_id"), str) else f"index:{index}"
        provenance = claim.get("provenance")
        locator = claim.get("evidence_locator")
        required = provenance in EVIDENCE_REQUIRED_PROVENANCE
        if required and locator is None:
            return [_finding("SCR-LOCATOR-REQUIRED", "provenance requires an evidence locator", claim_id)]
        if locator is None:
            continue
        if not isinstance(locator, list) or not locator:
            return [_finding("SCR-LOCATOR-REQUIRED", "evidence locator must be a nonempty span list", claim_id)]
        expected_count = 2 if provenance == "cross_source_comparison" else 1
        if required and len(locator) != expected_count:
            return [_finding(
                "SCR-LOCATOR-REQUIRED",
                f"{provenance} requires exactly {expected_count} evidence span(s)",
                claim_id,
            )]
        identities: set[tuple[str, int, int]] = set()
        for row in locator:
            if not isinstance(row, dict) or set(row) != EVIDENCE_SPAN_FIELDS:
                return [_finding("SCR-LOCATOR-REQUIRED", "evidence span fields are malformed or unknown", claim_id)]
            if (
                not isinstance(row["path"], str)
                or not row["path"]
                or not isinstance(row["sha256"], str)
                or not SHA256_RE.fullmatch(row["sha256"])
                or not isinstance(row["span_sha256"], str)
                or not SHA256_RE.fullmatch(row["span_sha256"])
                or not isinstance(row["byte_start"], int)
                or isinstance(row["byte_start"], bool)
                or not isinstance(row["byte_end"], int)
                or isinstance(row["byte_end"], bool)
                or row["byte_start"] < 0
                or row["byte_end"] <= row["byte_start"]
            ):
                return [_finding("SCR-LOCATOR-REQUIRED", "evidence span values are malformed", claim_id)]
            identity = (row["path"], row["byte_start"], row["byte_end"])
            if identity in identities:
                return [_finding("SCR-LOCATOR-REQUIRED", "evidence spans must be distinct", claim_id)]
            identities.add(identity)
    return []


def _schema_findings(
    value: dict[str, Any], reads: _ReadSet | None = None
) -> list[dict[str, str]]:
    try:
        schema_raw = SCHEMA_PATH.read_bytes()
        if reads is not None:
            reads.add(SCHEMA_PATH, schema_raw, "SCR-SCHEMA", "claim-register schema")
        schema = json.loads(schema_raw.decode("utf-8", errors="strict"))
        Draft202012Validator.check_schema(schema)
        errors = sorted(
            Draft202012Validator(schema).iter_errors(value),
            key=lambda error: [str(part) for part in error.absolute_path],
        )
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        SchemaError,
        Unresolvable,
    ) as exc:
        return [_finding("SCR-SCHEMA", f"claim-register schema is unavailable: {exc}")]
    if not errors:
        return []
    error = errors[0]
    location = ".".join(str(part) for part in error.absolute_path) or "<root>"
    return [_finding("SCR-SCHEMA", f"{location}: {error.message}")]


def _resolve_binding_path(raw: str, register_path: Path) -> Path:
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = register_path.parent / candidate
    return candidate.resolve(strict=False)


def _artifact_findings(
    value: dict[str, Any], artifact_path: Path, register_path: Path,
    reads: _ReadSet | None = None,
) -> tuple[list[dict[str, str]], bytes | None]:
    binding = value["artifact"]
    declared = _resolve_binding_path(binding["path"], register_path)
    actual = artifact_path.resolve(strict=False)
    if declared != actual:
        return [_finding("SCR-ARTIFACT-STALE", "artifact path binding is not current")], None
    try:
        raw = artifact_path.read_bytes()
    except OSError as exc:
        return [_finding("SCR-ARTIFACT-STALE", f"artifact cannot be read: {exc}")], None
    if reads is not None:
        reads.add(artifact_path, raw, "SCR-ARTIFACT-STALE", "claim-register artifact")
    if binding["byte_length"] != len(raw) or binding["sha256"] != _sha_bytes(raw):
        return [_finding("SCR-ARTIFACT-STALE", "artifact hash or byte length is not current")], raw
    return [], raw


def _nearest_section(artifact_raw: bytes, start: int) -> str | None:
    try:
        prefix = artifact_raw[:start].decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return None
    nearest = "<root>"
    fence_char: str | None = None
    fence_length = 0
    for line in COMMONMARK_LINE_END_RE.split(prefix):
        if fence_char is not None:
            closing = re.fullmatch(
                rf" {{0,3}}{re.escape(fence_char)}{{{fence_length},}}[ \t]*",
                line,
            )
            if closing:
                fence_char = None
                fence_length = 0
            continue
        fence = FENCE_OPEN_RE.fullmatch(line)
        if fence:
            run = fence.group(1)
            info = fence.group(2)
            if run[0] != "`" or "`" not in info:
                fence_char = run[0]
                fence_length = len(run)
                continue
        match = ATX_RE.fullmatch(line)
        if not match:
            continue
        content = (match.group(2) or "").rstrip(" \t")
        closing = None
        if content and set(content) == {"#"}:
            content = ""
        else:
            closing = ATX_CLOSING_RE.fullmatch(content)
        if content and closing:
            content = closing.group(1).rstrip(" \t")
        nearest = content if content else "<empty-heading>"
    return nearest


def _commonmark_line_number(artifact_raw: bytes, start: int) -> int | None:
    try:
        prefix = artifact_raw[:start].decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return None
    return len(COMMONMARK_LINE_END_RE.findall(prefix)) + 1


def _replay_evidence_locator(
    locator: list[dict[str, Any]],
    register_path: Path,
    claim_id: str,
    provenance: str,
    reads: _ReadSet | None = None,
) -> list[dict[str, str]]:
    normalized: set[tuple[str, int, int]] = set()
    source_paths: list[Path] = []
    for row in locator:
        path = _resolve_binding_path(row["path"], register_path)
        source_paths.append(path)
        identity = (str(path).casefold(), row["byte_start"], row["byte_end"])
        if identity in normalized:
            return [_finding("SCR-LOCATOR-REQUIRED", "evidence spans resolve to a duplicate identity", claim_id)]
        normalized.add(identity)
        try:
            raw = path.read_bytes()
        except OSError:
            return [_finding("SCR-LOCATOR-REQUIRED", "evidence source is missing or unreadable", claim_id)]
        if reads is not None:
            reads.add(path, raw, "SCR-LOCATOR-REQUIRED", "claim evidence source")
        start, end = row["byte_start"], row["byte_end"]
        if row["sha256"] != _sha_bytes(raw):
            return [_finding("SCR-LOCATOR-REQUIRED", "evidence source hash is stale", claim_id)]
        if end > len(raw):
            return [_finding("SCR-LOCATOR-REQUIRED", "evidence byte range is out of bounds", claim_id)]
        if row["span_sha256"] != _sha_bytes(raw[start:end]):
            return [_finding("SCR-LOCATOR-REQUIRED", "evidence span hash is stale", claim_id)]
    if provenance == "cross_source_comparison":
        try:
            aliases = len(source_paths) != 2 or source_paths[0].samefile(source_paths[1])
        except OSError:
            aliases = True
        if aliases:
            return [_finding(
                "SCR-LOCATOR-REQUIRED",
                "cross-source comparison requires two distinct filesystem objects",
                claim_id,
            )]
    return []


def _claim_findings(
    value: dict[str, Any], artifact_raw: bytes, register_path: Path,
    reads: _ReadSet | None = None,
) -> list[dict[str, str]]:
    claim_ids: set[str] = set()
    artifact_spans: set[tuple[int, int]] = set()
    for claim in value["claims"]:
        claim_id = claim["claim_id"]
        if claim_id in claim_ids:
            return [_finding("SCR-SCHEMA", "claim IDs must be unique", claim_id)]
        claim_ids.add(claim_id)

        locator = claim["locator"]
        start, end = locator["byte_start"], locator["byte_end"]
        if (start, end) in artifact_spans:
            return [_finding(
                "SCR-ARTIFACT-STALE",
                "distinct claim IDs cannot alias the same artifact byte range",
                claim_id,
            )]
        artifact_spans.add((start, end))
        text_bytes = claim["text"].encode("utf-8")
        if end <= start or end > len(artifact_raw) or artifact_raw[start:end] != text_bytes:
            return [_finding("SCR-ARTIFACT-STALE", "claim locator does not bind exact artifact bytes", claim_id)]
        if claim["span_sha256"] != _sha_bytes(text_bytes):
            return [_finding("SCR-ARTIFACT-STALE", "claim span hash is not current", claim_id)]
        actual_line = _commonmark_line_number(artifact_raw, start)
        if actual_line is None or locator["line"] != actual_line:
            return [_finding("SCR-ARTIFACT-STALE", "claim line locator is not current", claim_id)]
        actual_section = _nearest_section(artifact_raw, start)
        if actual_section is None or locator["section"] != actual_section:
            return [_finding("SCR-ARTIFACT-STALE", "claim section locator is not current", claim_id)]

        evidence_locator = claim.get("evidence_locator")
        if evidence_locator is not None:
            findings = _replay_evidence_locator(
                evidence_locator,
                register_path,
                claim_id,
                claim["provenance"],
                reads,
            )
            if findings:
                return findings

        if (
            claim["provenance"] == "author_derivation"
            and claim["admission_use"] == "admitted_evidence"
        ):
            return [_finding(
                "SCR-ADMISSION-USE-INCONSISTENT",
                "author derivation cannot be represented as admitted evidence",
                claim_id,
            )]
    return []


def _coverage_findings(value: dict[str, Any]) -> list[dict[str, str]]:
    claims = {claim["claim_id"]: claim for claim in value["claims"]}
    generator = set(value["generator_inventory"])
    if not generator <= set(claims):
        return [_finding("SCR-COVERAGE-INCOMPLETE", "Generator inventory names an absent claim")]

    additions: dict[str, dict[str, Any]] = {}
    for addition in value["evaluator_additions"]:
        claim_id = addition["claim_id"]
        if claim_id in additions or claim_id not in claims or addition != claims[claim_id]:
            return [_finding("SCR-COVERAGE-INCOMPLETE", "Evaluator addition is not an exact registered claim", claim_id)]
        additions[claim_id] = addition
    if generator & set(additions):
        return [_finding("SCR-COVERAGE-INCOMPLETE", "claim appears in both Generator inventory and Evaluator additions")]
    if generator | set(additions) != set(claims):
        return [_finding("SCR-COVERAGE-INCOMPLETE", "claim inventory does not cover every registered claim")]

    omission_ids: set[str] = set()
    for omission in value["evaluator_omissions"]:
        claim_id = omission["claim_id"]
        claim = claims.get(claim_id)
        if claim_id in omission_ids or claim is None:
            return [_finding("SCR-COVERAGE-INCOMPLETE", "Evaluator omission is orphaned or duplicated", claim_id)]
        omission_ids.add(claim_id)
        if claim_id not in additions or claim_id in generator:
            return [_finding("SCR-COVERAGE-INCOMPLETE", "omission is not an independent Evaluator addition", claim_id)]
        if any(
            omission[key] != claim[key]
            for key in ("text", "span_sha256", "locator")
        ):
            return [_finding("SCR-COVERAGE-INCOMPLETE", "omission does not bind the exact registered claim", claim_id)]

    disposition = value["coverage_disposition"]
    if disposition == "complete" and (
        generator != set(claims) or additions or omission_ids
    ):
        return [_finding(
            "SCR-COVERAGE-INCOMPLETE",
            "complete coverage requires exact Generator coverage and zero Evaluator additions or omissions",
        )]
    if disposition == "incomplete" and not omission_ids and not additions:
        return [_finding("SCR-COVERAGE-INCOMPLETE", "incomplete coverage declares no concrete addition or omission")]
    return []


def _block_covers_claim(block_locator: dict[str, Any], claim_locator: dict[str, Any]) -> bool:
    return (
        claim_locator["byte_start"] >= block_locator["byte_start"]
        and claim_locator["byte_end"] <= block_locator["byte_end"]
    )


def _inventory_byte_stats(
    artifact_raw: bytes, blocks: list[dict[str, Any]]
) -> dict[str, Any]:
    covered = bytearray(len(artifact_raw))
    excluded_ns = 0
    inaccessible_ns = 0
    in_scope_ns = 0
    for block in blocks:
        start = block["locator"]["byte_start"]
        end = block["locator"]["byte_end"]
        coverage = block["coverage"]
        for index in range(start, min(end, len(artifact_raw))):
            covered[index] = 1
            if artifact_raw[index] in INVENTORY_WHITESPACE:
                continue
            if coverage == "excluded":
                excluded_ns += 1
            elif coverage == "inaccessible":
                inaccessible_ns += 1
            else:
                in_scope_ns += 1
    uncovered_ns = 0
    for index, flag in enumerate(covered):
        if flag == 0 and artifact_raw[index] not in INVENTORY_WHITESPACE:
            uncovered_ns += 1
    excluded_blocks = sum(1 for block in blocks if block["coverage"] == "excluded")
    inaccessible_blocks = sum(1 for block in blocks if block["coverage"] == "inaccessible")
    in_scope_blocks = sum(1 for block in blocks if block["coverage"] == "in_scope")
    narrowed = excluded_blocks > 0 or inaccessible_blocks > 0
    return {
        "covered_flag": covered,
        "uncovered_non_whitespace_bytes": uncovered_ns,
        "excluded_non_whitespace_bytes": excluded_ns,
        "inaccessible_non_whitespace_bytes": inaccessible_ns,
        "in_scope_non_whitespace_bytes": in_scope_ns,
        "excluded_blocks": excluded_blocks,
        "inaccessible_blocks": inaccessible_blocks,
        "in_scope_blocks": in_scope_blocks,
        "narrowed": narrowed,
    }


def _inventory_result(value: dict[str, Any], artifact_raw: bytes) -> dict[str, Any]:
    inventory = value.get("document_inventory") or {}
    blocks = inventory.get("blocks") or []
    stats = _inventory_byte_stats(artifact_raw, blocks)
    narrowed = bool(stats["narrowed"])
    # Byte-accounting fact only. Independent of disposition, review_scope,
    # acceptance, and semantic completeness. Not a document/review/semantic PASS.
    full_artifact_bytes_accounted = (
        stats["uncovered_non_whitespace_bytes"] == 0 and bool(blocks)
    )
    return {
        "coverage_basis": "declared_byte_accounted_inventory_and_exclusions",
        "semantic_claim_universe_complete": False,
        "human_reference_inventory_established": False,
        "review_scope": "narrowed" if narrowed else "declared_full_artifact_bytes",
        "full_artifact_bytes_accounted": full_artifact_bytes_accounted,
        "whitespace_gaps_ignored": inventory.get("whitespace_gaps_ignored") is True,
        "in_scope_non_whitespace_bytes": stats["in_scope_non_whitespace_bytes"],
        "excluded_non_whitespace_bytes": stats["excluded_non_whitespace_bytes"],
        "inaccessible_non_whitespace_bytes": stats["inaccessible_non_whitespace_bytes"],
        "uncovered_non_whitespace_bytes": stats["uncovered_non_whitespace_bytes"],
        "in_scope_blocks": stats["in_scope_blocks"],
        "excluded_blocks": stats["excluded_blocks"],
        "inaccessible_blocks": stats["inaccessible_blocks"],
        "limitation": INVENTORY_LIMITATION,
    }


def _inventory_incomplete_deficits(
    value: dict[str, Any], artifact_raw: bytes
) -> list[str]:
    """Concrete 1.1.0 incomplete deficits. Inaccessible-only is not a deficit."""
    inventory = value.get("document_inventory") or {}
    blocks = inventory.get("blocks") or []
    if not isinstance(blocks, list):
        return []
    stats = _inventory_byte_stats(artifact_raw, blocks)
    deficits: list[str] = []
    if stats["uncovered_non_whitespace_bytes"]:
        deficits.append("uncovered_bytes")
    claim_ids = {claim["claim_id"] for claim in value.get("claims") or []}
    owners: set[str] = set()
    in_scope_unclaimed = False
    for block in blocks:
        if not isinstance(block, dict):
            continue
        bound = list(block.get("claim_ids") or [])
        if block.get("coverage") == "in_scope":
            if not bound:
                in_scope_unclaimed = True
            owners.update(bound)
    if in_scope_unclaimed:
        deficits.append("in_scope_unclaimed")
    if claim_ids - owners:
        deficits.append("unassigned_claim")
    return deficits


def _inventory_findings(value: dict[str, Any], artifact_raw: bytes) -> list[dict[str, str]]:
    if value.get("schema_version") != "1.1.0":
        return []
    inventory = value.get("document_inventory")
    disposition = value["coverage_disposition"]
    if not isinstance(inventory, dict):
        if disposition in {"complete", "blocked"}:
            return [_finding(
                "SCR-COVERAGE-INVENTORY-MISSING",
                "1.1.0 complete or blocked coverage requires document_inventory",
            )]
        return []
    blocks = inventory.get("blocks")
    if not isinstance(blocks, list):
        return [_finding("SCR-SCHEMA", "document_inventory.blocks must be an array")]

    claims = {claim["claim_id"]: claim for claim in value["claims"]}
    seen_ids: set[str] = set()
    claimed_ranges: list[tuple[int, int, str]] = []
    claim_owners: dict[str, str] = {}

    for block in blocks:
        if not isinstance(block, dict):
            return [_finding("SCR-SCHEMA", "inventory block must be an object")]
        block_id = block.get("block_id")
        if not isinstance(block_id, str) or not block_id:
            return [_finding("SCR-SCHEMA", "inventory block_id is missing")]
        if block_id in seen_ids:
            return [_finding("SCR-INVENTORY-DUPLICATE-ID", "inventory block IDs must be unique")]
        seen_ids.add(block_id)

        locator = block.get("locator")
        if not isinstance(locator, dict):
            return [_finding("SCR-INVENTORY-STALE", "inventory block locator is missing")]
        start, end = locator.get("byte_start"), locator.get("byte_end")
        if (
            not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
            or end <= start
            or end > len(artifact_raw)
        ):
            return [_finding("SCR-INVENTORY-STALE", "inventory block locator does not bind exact artifact bytes")]
        span = artifact_raw[start:end]
        if block.get("span_sha256") != _sha_bytes(span):
            return [_finding("SCR-INVENTORY-STALE", "inventory block span hash is not current")]
        actual_line = _commonmark_line_number(artifact_raw, start)
        if actual_line is None or locator.get("line") != actual_line:
            return [_finding("SCR-INVENTORY-STALE", "inventory block line locator is not current")]
        actual_section = _nearest_section(artifact_raw, start)
        if actual_section is None or locator.get("section") != actual_section:
            return [_finding("SCR-INVENTORY-STALE", "inventory block section locator is not current")]

        coverage = block.get("coverage")
        if coverage in {"excluded", "inaccessible"}:
            reason = block.get("reason")
            if not isinstance(reason, str) or not reason:
                return [_finding("SCR-SCHEMA", "excluded or inaccessible block requires a reason")]
            if block.get("claim_ids"):
                return [_finding(
                    "SCR-INVENTORY-CLAIM-REF",
                    "excluded or inaccessible block cannot list claim_ids",
                )]

        for other_start, other_end, other_id in claimed_ranges:
            if not (end <= other_start or other_end <= start):
                return [_finding(
                    "SCR-INVENTORY-OVERLAP",
                    f"inventory blocks overlap: {block_id} and {other_id}",
                )]
        claimed_ranges.append((start, end, block_id))

        for claim_id in block.get("claim_ids") or []:
            claim = claims.get(claim_id)
            if claim is None:
                return [_finding(
                    "SCR-INVENTORY-CLAIM-REF",
                    "inventory block names an absent claim",
                    claim_id,
                )]
            if not _block_covers_claim(locator, claim["locator"]):
                return [_finding(
                    "SCR-INVENTORY-CLAIM-RANGE",
                    "claim locator is outside the bound inventory block",
                    claim_id,
                )]
            if claim_id in claim_owners:
                return [_finding(
                    "SCR-INVENTORY-CLAIM-REF",
                    "claim is bound to more than one inventory block",
                    claim_id,
                )]
            claim_owners[claim_id] = block_id

    stats = _inventory_byte_stats(artifact_raw, blocks)
    if disposition == "complete":
        if stats["inaccessible_blocks"]:
            return [_finding(
                "SCR-COVERAGE-INACCESSIBLE",
                "complete coverage cannot include inaccessible document blocks",
            )]
        if stats["uncovered_non_whitespace_bytes"]:
            return [_finding(
                "SCR-COVERAGE-UNCOVERED-BYTES",
                "non-whitespace artifact bytes are not covered by inventory blocks or excluded spans",
            )]
        for block in blocks:
            if block.get("coverage") == "in_scope" and not block.get("claim_ids"):
                return [_finding(
                    "SCR-COVERAGE-IN-SCOPE-UNCLAIMED",
                    "in_scope block has no bound claim",
                )]
        for claim_id in claims:
            if claim_id not in claim_owners:
                return [_finding(
                    "SCR-INVENTORY-CLAIM-REF",
                    "registered claim is not bound to an in_scope inventory block",
                    claim_id,
                )]
    return []


def _validate_register_value(
    artifact_path: Path,
    register_path: Path,
    value: dict[str, Any],
    reads: _ReadSet | None = None,
) -> dict[str, Any]:
    findings = _early_cardinality_findings(value)
    if not findings:
        findings = _early_locator_findings(value)
    if not findings:
        findings = _schema_findings(value, reads)
    artifact_raw: bytes | None = None
    if not findings:
        findings, artifact_raw = _artifact_findings(
            value, artifact_path, register_path, reads
        )
    if not findings and artifact_raw is not None:
        findings = _claim_findings(value, artifact_raw, register_path, reads)
    inventory_deficits: list[str] = []
    if not findings and value.get("schema_version") == "1.1.0" and artifact_raw is not None:
        findings = _inventory_findings(value, artifact_raw)
        if not findings:
            inventory_deficits = _inventory_incomplete_deficits(value, artifact_raw)
    if not findings:
        findings = _coverage_findings(value)
        if (
            findings
            and value.get("schema_version") == "1.1.0"
            and value.get("coverage_disposition") == "incomplete"
            and inventory_deficits
            and all(
                row.get("code") == "SCR-COVERAGE-INCOMPLETE"
                and row.get("message")
                == "incomplete coverage declares no concrete addition or omission"
                for row in findings
            )
        ):
            findings = []
    if findings:
        return {"status": "refused", "findings": findings}
    result = {
        "status": "qualified" if value["coverage_disposition"] == "complete" else value["coverage_disposition"],
        "coverage_disposition": value["coverage_disposition"],
        "claim_count": len(value["claims"]),
        "generator_claim_count": len(value["generator_inventory"]),
        "evaluator_addition_count": len(value["evaluator_additions"]),
        "evaluator_omission_count": len(value["evaluator_omissions"]),
        "findings": [],
    }
    if value.get("schema_version") == "1.1.0" and artifact_raw is not None:
        result["document_inventory_result"] = _inventory_result(value, artifact_raw)
    return result


def validate_register(
    artifact_path: Path,
    register_path: Path,
    value: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the authoritative deterministic validation result."""
    if value is None:
        try:
            value = _load_json(register_path)
        except ClaimRegisterError as exc:
            return {"status": "refused", "findings": [_finding(exc.code, str(exc))]}
    return _validate_register_value(artifact_path, register_path, value)


def validate_register_with_dependencies(
    artifact_path: Path,
    register_path: Path,
    *,
    expected_register_payload: bytes | None = None,
) -> dict[str, Any]:
    """Validate one exact register snapshot and return its complete read set.

    The legacy ``validate_register`` result is intentionally unchanged.  This
    lifecycle-facing API owns the register read, reconciles an optional caller
    snapshot, and replays every schema, artifact, register, and evidence-source
    byte before returning.
    """

    reads = _ReadSet()
    try:
        register_payload = register_path.read_bytes()
    except OSError as exc:
        return {
            "status": "refused",
            "findings": [_finding("SCR-SCHEMA", f"cannot load register: {exc}")],
            "dependencies": [],
        }
    if (
        expected_register_payload is not None
        and register_payload != expected_register_payload
    ):
        return {
            "status": "refused",
            "findings": [_finding("SCR-ARTIFACT-STALE", "register differs from the caller's exact snapshot")],
            "dependencies": [],
        }
    try:
        reads.add(
            register_path,
            register_payload,
            "SCR-ARTIFACT-STALE",
            "scholarly claim register",
        )
        value = _decode_register(register_payload)
        result = _validate_register_value(
            artifact_path, register_path, value, reads
        )
    except ClaimRegisterError as exc:
        result = {"status": "refused", "findings": [_finding(exc.code, str(exc))]}
    replay_finding = reads.replay_finding()
    if replay_finding is not None:
        result = {"status": "refused", "findings": [replay_finding]}
    return {**result, "dependencies": reads.rows()}


def _escape_md_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(value: dict[str, Any], result: dict[str, Any] | None = None) -> str:
    """Render a non-authoritative human-readable view of a validated register.

    Does not reread artifact bytes. Optional ``result`` may supply already
    validated snapshot statistics; those are not new verification claims.
    """
    lines = [
        "<!-- NON-AUTHORITATIVE VIEW: the JSON scholarly claim register governs. -->",
        "# Scholarly Claim Register",
        "",
        f"- Register: `{value['register_id']}`",
        f"- Artifact: `{value['artifact']['path']}`",
        f"- Artifact SHA-256: `{value['artifact']['sha256']}`",
        f"- Coverage: `{value['coverage_disposition']}`",
    ]
    if value.get("schema_version") == "1.1.0":
        inventory = value.get("document_inventory") or {}
        blocks = inventory.get("blocks") if isinstance(inventory, dict) else None
        if not isinstance(blocks, list):
            blocks = []
        declared_narrowed = any(
            isinstance(block, dict) and block.get("coverage") in {"excluded", "inaccessible"}
            for block in blocks
        )
        declared_scope = "narrowed" if declared_narrowed else "declared_full_artifact_bytes"
        lines.extend(
            [
                "- Inventory coverage basis: `declared_byte_accounted_inventory_and_exclusions`",
                "- Semantic claim-universe completeness: `not established`",
                "- Human reference inventory: `not established`",
                f"- Declared review_scope: `{declared_scope}`",
                f"- Limitation: {INVENTORY_LIMITATION}",
            ]
        )
        snapshot = None
        if isinstance(result, dict):
            snapshot = result.get("document_inventory_result")
        if isinstance(snapshot, dict):
            lines.extend(
                [
                    "- Validated snapshot review_scope: "
                    f"`{snapshot.get('review_scope')}`",
                    "- Validated snapshot full_artifact_bytes_accounted: "
                    f"`{snapshot.get('full_artifact_bytes_accounted')}`",
                    "- Validated snapshot uncovered_non_whitespace_bytes: "
                    f"`{snapshot.get('uncovered_non_whitespace_bytes')}`",
                    "- Snapshot statistics are copied from the already validated "
                    "result; this view does not re-verify artifact bytes.",
                ]
            )
        lines.extend(
            [
                "",
                "## Declared document inventory (non-authoritative)",
                "",
                "| block_id | kind | range | coverage | reason | claim_ids |",
                "|---|---|---|---|---|---|",
            ]
        )
        for block in blocks:
            if not isinstance(block, dict):
                continue
            locator = block.get("locator") if isinstance(block.get("locator"), dict) else {}
            start = locator.get("byte_start")
            end = locator.get("byte_end")
            claim_ids = ",".join(str(item) for item in (block.get("claim_ids") or []))
            lines.append(
                "| "
                + " | ".join(
                    [
                        _escape_md_cell(block.get("block_id", "")),
                        _escape_md_cell(block.get("kind", "")),
                        _escape_md_cell(f"[{start},{end})"),
                        _escape_md_cell(block.get("coverage", "")),
                        _escape_md_cell(block.get("reason", "")),
                        _escape_md_cell(claim_ids),
                    ]
                )
                + " |"
            )
    lines.extend(
        [
            "",
            "| Claim | Viewpoint | Provenance | Admission/use | Argument leg | Modal force | Warrant |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for claim in value["claims"]:
        lines.append(
            "| "
            + " | ".join(
                _escape_md_cell(claim[key])
                for key in (
                    "claim_id",
                    "viewpoint",
                    "provenance",
                    "admission_use",
                    "argument_leg",
                    "modal_force",
                    "warrant_relation",
                )
            )
            + " |"
        )
    lines.extend(["", "Rendered for inspection only; validate the bound JSON before use.", ""])
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--register", required=True, type=Path)
    parser.add_argument("--render", action="store_true", help="print a non-authoritative Markdown view")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        value = _load_json(args.register)
    except ClaimRegisterError as exc:
        result = {"status": "refused", "findings": [_finding(exc.code, str(exc))]}
    else:
        result = validate_register(args.artifact, args.register, value)
    if result["findings"] or not args.render:
        print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    else:
        print(render_markdown(value, result), end="")
    return 0 if not result["findings"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
