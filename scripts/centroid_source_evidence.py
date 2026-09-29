#!/usr/bin/env python3
"""Read-only admission of centroid passages from human excerpts or C2 extracts."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from c2_evidence_validation import EvidenceValidationError, validate_extract_receipt

ROOT = Path(__file__).resolve().parent.parent
YU_2011 = "yu-et-al-2011-social-modeling"
DENNETT = "dennett-1987-intentional-stance"
POLICY_SOURCES = frozenset({YU_2011, DENNETT})
YU_PAGES = frozenset(range(3, 53))
DEFAULT_POLICY = ROOT / "references/policies/reader_accessibility.v1.json"
PAGE_MARKER = re.compile(r"(?i)(?<![A-Za-z0-9_])(?:pp?\.|pages?\b)\s*")
PAGE_EXPR = re.compile(r"\d+(?:\s*[-\u2013]\s*\d+)?(?:\s*(?:,|\band\b)\s*\d+(?:\s*[-\u2013]\s*\d+)?)*", re.I)
FOOTER = re.compile(r"(?i)(?:p\.|page\s+)?\s*(\d{1,4})")
FRONT = re.compile(r"(?im)^\s*(?:title(?: page)?|foreword|preface|table of contents|contents|copyright)\s*$")
ROMAN = re.compile(r"(?i)^[ivxlcdm]+$")


class SourceEvidenceError(RuntimeError):
    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _no_nonfinite(value: str) -> None:
    raise ValueError(f"non-finite JSON value {value}")


def _strict_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_no_duplicate_keys,
        parse_constant=_no_nonfinite,
    )


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _id(row: dict[str, Any]) -> str:
    identity = {key: row[key] for key in (
        "source_key", "locator", "quote_sha256", "warrant_layer", "admission_kind",
        "pdf_sha256", "extract_receipt_sha256", "normalized_sha256", "page", "pdf_identity",
    ) if key in row}
    data = json.dumps(identity, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "centroid-passage-" + _sha(data)[:24]


def _pages(locator: str) -> list[int]:
    markers = list(PAGE_MARKER.finditer(locator))
    if len(markers) != 1 or not PAGE_EXPR.fullmatch(locator[markers[0].end():].strip()):
        raise SourceEvidenceError("SENTENCE-LOGIC-SCOPE", f"locator needs one explicit, complete page expression: {locator!r}")
    expression = locator[markers[0].end():].strip()
    # The prefix may name a work, but cannot hide a second page expression.
    if re.search(r"\d+\s*[-\u2013,]\s*\d+", locator[:markers[0].start()]):
        raise SourceEvidenceError("SENTENCE-LOGIC-SCOPE", f"ambiguous page locator: {locator!r}")
    result: list[int] = []
    for token in re.split(r"\s*(?:,|\band\b)\s*", expression, flags=re.I):
        bounds = re.split(r"\s*[-\u2013]\s*", token)
        start = int(bounds[0])
        end = int(bounds[-1])
        if start < 1 or end < start or end - start > 10000:
            raise SourceEvidenceError("SENTENCE-LOGIC-SCOPE", f"invalid page range: {locator!r}")
        result.extend(range(start, end + 1))
    if not result or len(result) != len(set(result)):
        raise SourceEvidenceError("SENTENCE-LOGIC-SCOPE", f"empty or overlapping locator: {locator!r}")
    return result


def validate_passage(row: dict[str, Any], *, admitted_by: str | None = None) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise SourceEvidenceError("SENTENCE-LOGIC-PASSAGE", "passage row must be an object")
    source = row.get("source_key")
    locator = row.get("locator")
    quote = row.get("quote")
    if not all(isinstance(v, str) and v.strip() for v in (source, locator, quote)):
        raise SourceEvidenceError("SENTENCE-LOGIC-PASSAGE", "each passage needs nonempty source_key, locator, and quote")
    if source not in POLICY_SOURCES:
        raise SourceEvidenceError("SENTENCE-LOGIC-SOURCE", f"source {source!r} is not a centroid member")
    pages = _pages(locator)
    if source == YU_2011 and any(page not in YU_PAGES for page in pages):
        raise SourceEvidenceError("SENTENCE-LOGIC-SCOPE", f"Yu 2011 passage is outside book pp. 3-52: {locator}")
    layer = row.get("warrant_layer") or ("argument" if source == DENNETT else "surface")
    if layer != ("argument" if source == DENNETT else "surface"):
        raise SourceEvidenceError("SENTENCE-LOGIC-ROLE", f"invalid warrant_layer for {source}")
    quote_sha = _sha(quote.encode("utf-8"))
    if row.get("quote_sha256", quote_sha) != quote_sha:
        raise SourceEvidenceError("SENTENCE-LOGIC-PASSAGE", "quote_sha256 does not match quote bytes")
    admitter = row.get("admitted_by") or admitted_by
    if not isinstance(admitter, str) or not admitter.strip():
        raise SourceEvidenceError("SENTENCE-LOGIC-PASSAGE", "passage names no admitting party")
    result = {
        "source_key": source, "locator": locator, "quote": quote,
        "quote_sha256": quote_sha, "warrant_layer": layer,
        "admitted_by": admitter.strip(), "admission_kind": "human_attested",
    }
    result["passage_id"] = _id(result)
    return result


def passages_from_json(path: Path, admitted_by: str | None = None) -> list[dict[str, Any]]:
    try:
        data = _strict_json(Path(path))
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        raise SourceEvidenceError("SENTENCE-LOGIC-INPUT", f"cannot read passage JSON: {exc}") from exc
    rows = data if isinstance(data, list) else data.get("passages") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise SourceEvidenceError("SENTENCE-LOGIC-PASSAGE", "passages file must be a list or {passages: []}")
    return [validate_passage(row, admitted_by=admitted_by) for row in rows]


def _policy_member(path: Path, source: str) -> dict[str, Any]:
    try:
        policy = _strict_json(Path(path))
        members = policy["domain_native_register"]["exemplar_members"]
        hits = [row for row in members if isinstance(row, dict) and row.get("source_key") == source]
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        raise SourceEvidenceError("SENTENCE-LOGIC-POLICY", f"cannot read centroid policy: {exc}") from exc
    if len(hits) != 1:
        raise SourceEvidenceError("SENTENCE-LOGIC-SOURCE", f"source {source!r} is absent or ambiguous in policy")
    return hits[0]


def _printed_page(text: str, pdf_index: int) -> int | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if FRONT.search("\n".join(lines[:8])):
        return None
    tail = lines[-4:]
    if any(ROMAN.fullmatch(line) for line in tail):
        return None
    hits = [int(match.group(1)) for index, line in enumerate(lines)
            if index >= max(0, len(lines) - 4) and index > 0
            if (match := FOOTER.fullmatch(line))]
    if len(hits) > 1:
        raise SourceEvidenceError("SENTENCE-LOGIC-PDF", f"PDF index {pdf_index} has ambiguous printed folios: {hits}")
    return hits[0] if hits else None


def passages_from_pdf(
    pdf_path: Path, source_key: str, pages: list[int], layer: str, *,
    extract_receipt: Path | None = None, evidence_root: Path | None = None,
    wiki_root: Path | None = None, policy_path: Path | None = None,
) -> list[dict[str, Any]]:
    if not isinstance(source_key, str) or source_key not in POLICY_SOURCES:
        raise SourceEvidenceError("SENTENCE-LOGIC-SOURCE", f"source {source_key!r} is not a centroid member")
    if not isinstance(pages, list) or not pages or any(type(p) is not int or p < 1 for p in pages) or len(pages) != len(set(pages)):
        raise SourceEvidenceError("SENTENCE-LOGIC-SCOPE", "--pages needs distinct positive printed page numbers")
    if source_key == YU_2011 and any(p not in YU_PAGES for p in pages):
        raise SourceEvidenceError("SENTENCE-LOGIC-SCOPE", "Yu 2011 pages must be within book pp. 3-52")
    if layer != ("argument" if source_key == DENNETT else "surface"):
        raise SourceEvidenceError("SENTENCE-LOGIC-ROLE", f"invalid warrant_layer for {source_key}")
    try:
        pdf = Path(pdf_path).resolve(strict=True)
        if not pdf.is_file():
            raise ValueError("PDF path is not a file")
        pdf_sha = _sha(pdf.read_bytes())
    except (OSError, TypeError, ValueError) as exc:
        raise SourceEvidenceError("SENTENCE-LOGIC-PDF", f"cannot read PDF: {exc}") from exc
    member = _policy_member(policy_path if policy_path is not None else DEFAULT_POLICY, source_key)
    pin = member.get("pdf_sha256")
    if not isinstance(pin, str) or not re.fullmatch(r"[0-9a-f]{64}", pin):
        raise SourceEvidenceError("SENTENCE-LOGIC-SOURCE", f"{source_key} has no pinned policy PDF; use an explicitly author-admitted JSON excerpt")
    if pdf_sha != pin:
        raise SourceEvidenceError("SENTENCE-LOGIC-SOURCE", f"PDF SHA256 is not the policy-pinned {source_key} source; use an explicitly author-admitted JSON excerpt")
    if extract_receipt is None or evidence_root is None or wiki_root is None:
        raise SourceEvidenceError("SENTENCE-LOGIC-PDF", "canonical extract receipt, evidence_root, and wiki_root are required")
    try:
        receipt_path = Path(extract_receipt).resolve(strict=True)
        receipt_before = receipt_path.read_bytes()
        validated = validate_extract_receipt(
            receipt_path, project_root=Path(evidence_root), wiki_root=Path(wiki_root)
        )
        receipt_after = receipt_path.read_bytes()
        if receipt_before != receipt_after:
            raise SourceEvidenceError("SENTENCE-LOGIC-EXTRACT", "extract receipt changed during validation")
        receipt_sha = _sha(receipt_before)
    except (EvidenceValidationError, OSError, TypeError, ValueError) as exc:
        raise SourceEvidenceError("SENTENCE-LOGIC-EXTRACT", f"canonical extract validation failed: {exc}") from exc
    if validated["value"]["source_key"] != source_key:
        raise SourceEvidenceError("SENTENCE-LOGIC-SOURCE", "extract receipt source_key differs from requested source")
    if validated["source"] != pdf or validated["value"]["source"].get("sha256") != pdf_sha:
        raise SourceEvidenceError("SENTENCE-LOGIC-SOURCE", "extract receipt source file or digest differs from PDF")
    try:
        normalized = validated["normalized"].read_bytes()
        if _sha(normalized) != validated["page_map"]["normalized_sha256"]:
            raise SourceEvidenceError("SENTENCE-LOGIC-EXTRACT", "normalized text changed after receipt validation")
        if _sha(pdf.read_bytes()) != pdf_sha:
            raise SourceEvidenceError("SENTENCE-LOGIC-SOURCE", "PDF changed during receipt validation")
        mapped: dict[int, tuple[int, str]] = {}
        for record in validated["page_map"]["pages"]:
            index = record["page"]
            page_text = normalized[record["normalized_start_utf8"]:record["normalized_end_utf8"]].decode("utf-8", errors="strict")
            printed = _printed_page(page_text, index)
            if printed is None:
                continue
            if printed in mapped:
                raise SourceEvidenceError("SENTENCE-LOGIC-PDF", f"printed page {printed} maps to multiple PDF pages")
            mapped[printed] = (index, page_text)
    except (OSError, UnicodeError, KeyError, TypeError, ValueError) as exc:
        raise SourceEvidenceError("SENTENCE-LOGIC-EXTRACT", f"cannot use validated page map: {exc}") from exc
    missing = [p for p in pages if p not in mapped]
    if missing:
        raise SourceEvidenceError("SENTENCE-LOGIC-PDF", f"printed pages missing from canonical extract: {missing}")
    out: list[dict[str, Any]] = []
    normalized_sha = _sha(normalized)
    for page in pages:
        index, quote = mapped[page]
        if not quote.strip():
            raise SourceEvidenceError("SENTENCE-LOGIC-PDF", f"printed page {page} is empty")
        row = {
            "source_key": source_key, "locator": f"printed p. {page}",
            "quote": quote, "quote_sha256": _sha(quote.encode("utf-8")),
            "warrant_layer": layer, "admitted_by": "canonical-extract-validator",
            "admission_kind": "canonical_extract", "pdf_sha256": pdf_sha,
            "extract_receipt_path": str(receipt_path), "extract_receipt_sha256": receipt_sha,
            "normalized_sha256": normalized_sha, "page": page, "pdf_identity": index,
        }
        row["passage_id"] = _id(row)
        out.append(row)
    return out
