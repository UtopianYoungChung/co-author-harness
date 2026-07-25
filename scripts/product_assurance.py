#!/usr/bin/env python3
"""Build or verify exact-byte product-assurance evidence.

This module owns checks whose subject is the product rather than proof that a
workflow step ran.  It deliberately emits candidates for contestable language
and hard failures for broken evidence bindings, quotations, and citation
identity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from c2_evidence_validation import (
    EvidenceValidationError,
    canonical_bytes,
    load_canonical_document,
    validate_v3_receipt,
)
from destination_capability import DestinationRefused, assert_writable


SHA_RE = re.compile(r"^[0-9a-f]{64}$")
WORD_RE = re.compile(r"[^\W_]+(?:[-'][^\W_]+)*", re.UNICODE)
QUOTE_SPACE_RE = re.compile(r"\s+")
PARENTHETICAL_AUTHOR_YEAR_RE = re.compile(
    r"\([^()\n]{1,120}?,\s*(?:19|20)\d{2}[a-z]?\)", re.IGNORECASE
)
NARRATIVE_AUTHOR_YEAR_RE = re.compile(
    r"\b[A-Z][A-Za-z'\N{RIGHT SINGLE QUOTATION MARK}-]+"
    r"(?:\s+(?:(?:and|&)\s+[A-Z][A-Za-z'\N{RIGHT SINGLE QUOTATION MARK}-]+|et\s+al\.))?"
    r"\s+\((?:19|20)\d{2}[a-z]?\)"
)
MARKDOWN_HEADING_RE = re.compile(
    r"^(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$"
)
EMPIRICAL_RE = re.compile(
    r"\b(?:is|are|was|were|has|have|had)?\s*(?:often|frequently|typically|generally|usually)\b"
    r"|\b(?:tends?|most|majority of)\b",
    re.IGNORECASE,
)
INSIDER_RE = re.compile(
    r"\bnot\s+(?:(?:a|an|the)\s+)?([a-z][a-z-]*(?:\s+[a-z][a-z-]*){0,3})",
    re.IGNORECASE,
)
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "but",
    "by", "can", "could", "did", "do", "does", "each", "for", "from",
    "had", "has", "have", "he", "her", "here", "hers", "him", "his",
    "how", "i", "if", "in", "into", "is", "it", "its", "may", "might",
    "more", "most", "must", "no", "not", "of", "on", "one", "or", "our",
    "she", "should", "so", "some", "such", "than", "that", "the", "their",
    "them", "then", "there", "these", "they", "this", "those", "through",
    "to", "under", "was", "we", "were", "what", "when", "where", "which",
    "who", "why", "will", "with", "would", "you", "your",
}
DETECTOR_NAME = "product-assurance-semantic-candidates"
DETECTOR_VERSION = "3.0.0"

V3_LEGACY_COMPATIBILITY_FIELDS = frozenset({
    "schema_version",
    "receipt_type",
    "authority_mode",
    "target",
    "phase",
    "role",
    "artifact",
    "centroid_packet",
    "policy",
    "corpus_digest",
    "canonical_extract_receipts",
    "canonical_bibliography_snapshot",
    "passages",
    "member_coverage",
    "semantic_assessment",
    "diagnostic_legacy_view",
})
V2_FIELDS = frozenset({
    "schema_version",
    "receipt_type",
    "target",
    "phase",
    "role",
    "actor_id",
    "dispatch_id",
    "artifact",
    "centroid_packet",
    "generation_envelope",
    "adjudications",
    "passages",
    "semantic_assessment",
})
V2_REQUIRED_FIELDS = frozenset({
    "schema_version",
    "receipt_type",
    "target",
    "phase",
    "role",
    "actor_id",
    "dispatch_id",
    "artifact",
    "centroid_packet",
    "passages",
    "semantic_assessment",
})


class AssuranceError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json_document(path: Path, code: str) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8", errors="strict"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AssuranceError(code, f"cannot read valid JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AssuranceError(code, f"JSON root is not an object: {path}")
    return value, raw


def load_json(path: Path, code: str) -> dict[str, Any]:
    value, _raw = load_json_document(path, code)
    return value


def resolve_binding(value: Any, code: str) -> Path:
    if not isinstance(value, dict) or set(value) != {"path", "sha256"}:
        raise AssuranceError(code, "binding must contain exactly path and sha256")
    digest = value.get("sha256")
    if not isinstance(digest, str) or not SHA_RE.fullmatch(digest):
        raise AssuranceError(code, "binding sha256 is invalid")
    try:
        path = Path(str(value.get("path"))).resolve(strict=True)
    except OSError as exc:
        raise AssuranceError(code, f"binding path is unreadable: {value.get('path')}") from exc
    if not path.is_file() or sha256(path) != digest:
        raise AssuranceError(code, f"binding is stale: {path}")
    return path


def normalize(text: str) -> str:
    table = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"',
                           "\u201d": '"', "\u2013": "-", "\u2014": "-",
                           "\u00ad": "", "\ufb01": "fi", "\ufb02": "fl"})
    return QUOTE_SPACE_RE.sub(" ", text.translate(table)).strip().casefold()


def words(text: str) -> list[str]:
    return [item.casefold() for item in WORD_RE.findall(text)]


def _lemma(token: str) -> str:
    """Apply a deliberately small, deterministic English inflection fold."""
    value = token.casefold()
    if len(value) > 4 and value.endswith("ies"):
        return value[:-3] + "y"
    if len(value) > 4 and value.endswith(("ches", "shes", "sses", "xes", "zes")):
        return value[:-2]
    if (len(value) > 3 and value.endswith("s")
            and not value.endswith(("ss", "us", "is"))):
        return value[:-1]
    return value


def _lexical_lemmas(text: str) -> list[str]:
    """Tokenize compounds as word sequences before applying light lemmatization."""
    out: list[str] = []
    for token in words(text):
        out.extend(_lemma(part) for part in token.split("-") if part)
    return out


def _contains_sequence(haystack: list[str], needle: list[str]) -> bool:
    if not needle or len(needle) > len(haystack):
        return False
    width = len(needle)
    return any(haystack[index:index + width] == needle
               for index in range(len(haystack) - width + 1))


def _trimmed_span(text: str, start: int, end: int) -> tuple[int, int] | None:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return (start, end) if start < end else None


def _sentence_spans(text: str) -> list[tuple[int, int]]:
    """Return Markdown prose sentence spans across soft line breaks."""
    spans: list[tuple[int, int]] = []
    blocks: list[tuple[int, int]] = []
    block_start: int | None = None
    block_end: int | None = None
    offset = 0
    for raw in text.splitlines(keepends=True):
        content = raw.rstrip("\r\n")
        stripped = content.strip()
        hard_boundary = not stripped or MARKDOWN_HEADING_RE.fullmatch(stripped)
        if hard_boundary:
            if block_start is not None and block_end is not None:
                blocks.append((block_start, block_end))
            block_start = block_end = None
        else:
            if block_start is None:
                block_start = offset
            block_end = offset + len(content)
        offset += len(raw)
    if block_start is not None and block_end is not None:
        blocks.append((block_start, block_end))

    for block_start, block_end in blocks:
        cursor = block_start
        for boundary in re.finditer(r"[.!?]+(?=\s|$)", text[block_start:block_end]):
            raw_end = block_start + boundary.end()
            prefix = text[cursor:raw_end]
            if re.search(r"\bet\s+al\.$", prefix, re.IGNORECASE):
                continue
            span = _trimmed_span(text, cursor, raw_end)
            if span is not None:
                spans.append(span)
            cursor = raw_end
        span = _trimmed_span(text, cursor, block_end)
        if span is not None:
            spans.append(span)
    return spans


def _has_author_year_citation(text: str) -> bool:
    return bool(
        PARENTHETICAL_AUTHOR_YEAR_RE.search(text)
        or NARRATIVE_AUTHOR_YEAR_RE.search(text)
    )


def _abstract_span(text: str) -> tuple[int, int] | None:
    """Resolve the body owned by an explicit Markdown Abstract heading."""
    records: list[tuple[int, int, str]] = []
    cursor = 0
    for raw in text.splitlines(keepends=True):
        records.append((cursor, cursor + len(raw), raw.rstrip("\r\n")))
        cursor += len(raw)
    if not records and text:
        records.append((0, len(text), text))

    abstract_index: int | None = None
    abstract_level: int | None = None
    for index, (_start, _end, line) in enumerate(records):
        heading = MARKDOWN_HEADING_RE.fullmatch(line.strip())
        if heading and heading.group(2).strip().casefold() == "abstract":
            abstract_index = index
            abstract_level = len(heading.group(1))
            break
    if abstract_index is None or abstract_level is None:
        return None

    start = records[abstract_index][1]
    end = len(text)
    for _index, (line_start, _line_end, line) in enumerate(
        records[abstract_index + 1:], abstract_index + 1
    ):
        heading = MARKDOWN_HEADING_RE.fullmatch(line.strip())
        if heading and len(heading.group(1)) <= abstract_level:
            end = line_start
            break
    return start, end


def line_for(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def finding(code: str, dimension: str, severity: str, locator: str,
            evidence: str, *, tentative: bool = False,
            candidate_text: str | None = None,
            span: dict[str, Any] | None = None) -> dict[str, Any]:
    value = {
        "code": code, "dimension": dimension, "severity": severity,
        "locator": locator, "evidence": evidence, "tentative": tentative,
    }
    if candidate_text is not None and span is not None:
        value["candidate_text"] = candidate_text
        value["span"] = span
    return value


def _span(text: str, start: int, end: int) -> dict[str, Any]:
    selected = text[start:end]
    return {
        "start_utf8": len(text[:start].encode("utf-8")),
        "end_utf8": len(text[:end].encode("utf-8")),
        "text_sha256": hashlib.sha256(selected.encode("utf-8")).hexdigest(),
    }


def _candidate_fingerprint(
    row: dict[str, Any],
    *,
    artifact_sha256: str,
    corpus_binding_sha256: str,
    policy_sha256: str,
) -> str:
    payload = {
        "schema_version": "1.0.0",
        "artifact_sha256": artifact_sha256,
        "detector": {"name": DETECTOR_NAME, "version": DETECTOR_VERSION},
        "code": row["code"],
        "locator": row["locator"],
        "span": row["span"],
        "candidate_text": row["candidate_text"],
        "corpus_binding_sha256": corpus_binding_sha256,
        "policy_sha256": policy_sha256,
        "evidence_sha256": hashlib.sha256(
            canonical_bytes({"evidence": row["evidence"]})
        ).hexdigest(),
    }
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def _corpus_binding_sha256(receipt: dict[str, Any]) -> str:
    governed = receipt.get("corpus_digest")
    if isinstance(governed, str) and SHA_RE.fullmatch(governed):
        return governed
    legacy_rows: list[dict[str, Any]] = []
    for row in receipt.get("passages", []):
        if not isinstance(row, dict):
            continue
        source = row.get("source")
        extract = row.get("extract")
        legacy_rows.append({
            "source_key": row.get("source_key"),
            "source_sha256": (
                source.get("sha256") if isinstance(source, dict) else None
            ),
            "extract_sha256": (
                extract.get("sha256") if isinstance(extract, dict) else None
            ),
            "extraction": row.get("extraction"),
            "citation": row.get("citation"),
        })
    return hashlib.sha256(canonical_bytes(legacy_rows)).hexdigest()


def _validate_passage_shape(row: Any) -> None:
    required = {
        "source_key", "use_scope", "source", "locator", "extract",
        "extraction", "quote", "citation", "use",
    }
    if not isinstance(row, dict) or set(row) != required:
        raise AssuranceError("PASSAGE-SHAPE", "passage fields do not match the v2 contract")
    extraction = row.get("extraction")
    if not isinstance(extraction, dict) or set(extraction) != {"method", "tool", "canonical"}:
        raise AssuranceError("EXTRACT-METADATA", "extraction metadata fields are invalid")
    if extraction.get("canonical") is not True:
        raise AssuranceError("EXTRACT-NONCANONICAL", "passage extract is not canonical")
    method = extraction.get("method")
    source_path = Path(str(row.get("source", {}).get("path", "")))
    if source_path.suffix.casefold() == ".pdf" and method != "pdftotext":
        raise AssuranceError(
            "EXTRACT-PDF-NONCANONICAL",
            "PDF passage evidence must use the pdftotext canonical adapter",
        )
    citation = row.get("citation")
    if not isinstance(citation, dict) or set(citation) != {"authors", "year", "title", "label"}:
        raise AssuranceError("CITATION-IDENTITY", "citation identity fields are invalid")
    if (not isinstance(citation.get("authors"), list)
            or not citation["authors"]
            or any(not isinstance(a, str) or not a.strip() for a in citation["authors"])
            or not isinstance(citation.get("year"), int)
            or not isinstance(citation.get("title"), str)
            or not citation["title"].strip()
            or not re.fullmatch(r"(?:19|20)\d{2}[a-z]?", str(citation.get("label", "")))):
        raise AssuranceError("CITATION-IDENTITY", "citation identity values are invalid")


def _citation_groups(passages: list[dict[str, Any]]) -> dict[tuple[tuple[str, ...], int], list[dict[str, Any]]]:
    grouped: dict[tuple[tuple[str, ...], int], list[dict[str, Any]]] = defaultdict(list)
    for row in passages:
        citation = row["citation"]
        key = (tuple(a.casefold() for a in citation["authors"]), citation["year"])
        grouped[key].append(row)
    return grouped


def _hard_evidence_findings(artifact: Path, text: str,
                            passages: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    findings: list[dict[str, Any]] = []
    corpus_parts: list[str] = []
    normalized_artifact = normalize(text)
    artifact_lines = text.splitlines()
    for row in passages:
        _validate_passage_shape(row)
        source = resolve_binding(row["source"], "SOURCE-BINDING")
        extract = resolve_binding(row["extract"], "EXTRACT-BINDING")
        extract_text = extract.read_text(encoding="utf-8", errors="strict")
        corpus_parts.append(extract_text)
        quote = row["quote"]
        if not isinstance(quote, str) or not quote.strip():
            raise AssuranceError("QUOTE-EMPTY", "passage quote must be non-empty")
        if normalize(quote) not in normalize(extract_text):
            findings.append(finding(
                "QUOTE-NOT-IN-EXTRACT", "quotation", "hard",
                str(row["locator"]),
                f"{row['source_key']}: recorded quote is absent from canonical extract {extract}",
            ))
        if normalize(quote) not in normalized_artifact:
            findings.append(finding(
                "QUOTE-NOT-IN-ARTIFACT", "quotation", "hard",
                artifact.as_posix(),
                f"{row['source_key']}: recorded quotation is not present in the governed artifact",
            ))
        source_key_words = set(words(str(row["source_key"]).replace("-", " "))) - STOPWORDS
        title_words = set(words(row["citation"]["title"])) - STOPWORDS
        if not (source_key_words & title_words):
            findings.append(finding(
                "CITATION-SOURCE-TITLE", "citation", "hard", str(source),
                f"source key {row['source_key']!r} does not support title {row['citation']['title']!r}",
            ))
        # Bind the passage's source title to the label actually assigned in the
        # manuscript bibliography. This catches a/b transposition even when
        # both labels remain syntactically valid and unique.
        best_label = None
        best_overlap = 0
        for line in artifact_lines:
            match = re.search(r"\(((?:19|20)\d{2}[a-z])\)", line, re.IGNORECASE)
            if not match:
                continue
            overlap = len(title_words & (set(words(line)) - STOPWORDS))
            if overlap > best_overlap:
                best_overlap = overlap
                best_label = match.group(1).casefold()
        if (best_overlap >= 2 and best_label is not None
                and best_label != str(row["citation"]["label"]).casefold()):
            findings.append(finding(
                "CITATION-SAME-YEAR", "citation", "hard", artifact.as_posix(),
                f"source title {row['citation']['title']!r} is assigned {best_label} in the bibliography, not {row['citation']['label']}",
            ))

    for _identity, rows in _citation_groups(passages).items():
        if len(rows) < 2:
            continue
        labels = [str(row["citation"]["label"]) for row in rows]
        years = {str(row["citation"]["year"]) for row in rows}
        suffixes = [label[-1] if label[-1:].isalpha() else "" for label in labels]
        if len(set(labels)) != len(labels) or "" in suffixes:
            findings.append(finding(
                "CITATION-SAME-YEAR", "citation", "hard", artifact.as_posix(),
                f"same-author/year sources require distinct suffixed labels; got {labels}",
            ))
        for row in rows:
            quote_norm = normalize(row["quote"])
            at = normalized_artifact.find(quote_norm)
            if at < 0:
                continue
            window = normalized_artifact[at:at + len(quote_norm) + 220]
            label = str(row["citation"]["label"]).casefold()
            if label not in window:
                findings.append(finding(
                    "CITATION-SAME-YEAR", "citation", "hard",
                    f"{artifact.as_posix()}:{line_for(normalized_artifact, at)}",
                    f"quote from {row['source_key']} is not followed by its bound label {label}",
                ))
        # Reject non-suffixed base years even if an unrelated numeric token
        # happens to be present in the local quotation window.
        if any(label in years for label in labels):
            findings.append(finding(
                "CITATION-SAME-YEAR", "citation", "hard", artifact.as_posix(),
                "same-author/year identity is not disambiguated",
            ))
    return findings, "\n".join(corpus_parts)


def _semantic_findings(artifact: Path, text: str, corpus: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    corpus_lemmas = _lexical_lemmas(corpus)
    corpus_lemma_set = set(corpus_lemmas)
    lines = text.splitlines()
    references_at = next((i for i, line in enumerate(lines)
                          if re.match(r"^#{1,6}\s+(references|bibliography)\s*$", line.strip(), re.IGNORECASE)),
                         len(lines))
    prose_lines = lines[:references_at]
    line_starts: list[int] = []
    cursor = 0
    for raw_line in text.splitlines(keepends=True):
        line_starts.append(cursor)
        cursor += len(raw_line)
    if len(line_starts) < len(lines):
        line_starts.append(cursor)

    lemma_spans: dict[str, list[tuple[int, int, str]]] = defaultdict(list)
    for number, line in enumerate(prose_lines, 1):
        base = line_starts[number - 1]
        for match in WORD_RE.finditer(line):
            token = match.group(0)
            if "-" not in token:
                lemma_spans[_lemma(token)].append(
                    (base + match.start(), base + match.end(), token)
                )
    manuscript_counts = Counter({lemma: len(spans)
                                 for lemma, spans in lemma_spans.items()})

    prose_end = line_starts[references_at] if references_at < len(line_starts) else len(text)
    for sentence_start, sentence_end in _sentence_spans(text[:prose_end]):
        sentence = text[sentence_start:sentence_end]
        number = line_for(text, sentence_start)
        owned = "[s]" in sentence.casefold()
        for match in WORD_RE.finditer(sentence):
            token = match.group(0)
            term_lemmas = _lexical_lemmas(token)
            if ("-" in token and len(token) >= 6 and not owned
                    and not _contains_sequence(corpus_lemmas, term_lemmas)):
                start = sentence_start + match.start()
                end = sentence_start + match.end()
                out.append(finding(
                    "TERM-COINAGE", "grounding", "candidate",
                    f"{artifact.as_posix()}:{number}",
                    "compound term absent from bound extracts: "
                    + " ".join(term_lemmas),
                    tentative=True, candidate_text=text[start:end],
                    span=_span(text, start, end),
                ))
        if (EMPIRICAL_RE.search(sentence) and not owned
                and not _has_author_year_citation(sentence)):
            out.append(finding(
                "EMPIRICAL-UNSUPPORTED", "grounding", "candidate",
                f"{artifact.as_posix()}:{number}",
                sentence[:240], tentative=True,
                candidate_text=sentence, span=_span(text, sentence_start, sentence_end),
            ))

    abstract_bounds = _abstract_span(text)
    if abstract_bounds is not None:
        abstract_start, abstract_end = abstract_bounds
        abstract_text = text[abstract_start:abstract_end]
        for match in INSIDER_RE.finditer(abstract_text):
            phrase = match.group(1).strip().rstrip(".,;:")
            head = _lemma(phrase.split()[0])
            if head in set(_lexical_lemmas(abstract_text[:match.start()])):
                continue
            start = abstract_start + match.start(1)
            end = abstract_start + match.end(1)
            out.append(finding(
                "INSIDER-NEGATION", "register", "candidate",
                f"{artifact.as_posix()}:{line_for(text, start)}",
                f"abstract negates an unintroduced reader term: {phrase}",
                tentative=True, candidate_text=text[start:end],
                span=_span(text, start, end),
            ))

    stopword_lemmas = {_lemma(token) for token in STOPWORDS}
    for lemma, count in sorted(manuscript_counts.items()):
        if (count >= 3 and lemma not in corpus_lemma_set
                and lemma not in stopword_lemmas and len(lemma) >= 6):
            start, end, candidate_text = lemma_spans[lemma][0]
            out.append(finding(
                "REGISTER-ABSENT", "register", "candidate", artifact.as_posix(),
                f"high-frequency manuscript lemma absent from bound extracts: {lemma} ({count}x)",
                tentative=True, candidate_text=candidate_text,
                span=_span(text, start, end),
            ))
    return out


def _legacy_centroid_surface_finding(
    receipt: dict[str, Any], artifact: Path
) -> dict[str, Any] | None:
    """Apply the C2 centroid-surface invariant when a real v2 packet is bound."""
    try:
        packet_path = resolve_binding(
            receipt.get("centroid_packet"), "CENTROID-PACKET-BINDING"
        )
    except AssuranceError:
        # Historical diagnostic receipts used non-resolving packet placeholders.
        # They remain diagnostic-only; a resolvable packet cannot evade C2.
        return None
    packet = load_json(packet_path, "CENTROID-COVERAGE-INCOMPLETE")
    policy = packet.get("policy")
    members = policy.get("members") if isinstance(policy, dict) else None
    if not isinstance(members, list):
        return finding(
            "CENTROID-COVERAGE-INCOMPLETE",
            "grounding",
            "hard",
            artifact.as_posix(),
            "bound centroid packet has no member inventory",
        )
    centroid_keys = {
        row.get("source_key")
        for row in members
        if isinstance(row, dict) and row.get("role") == "centroid"
    }
    passages = receipt.get("passages")
    if not isinstance(passages, list) or not any(
        isinstance(row, dict)
        and row.get("source_key") in centroid_keys
        and row.get("use_scope") == "surface"
        for row in passages
    ):
        return finding(
            "CENTROID-COVERAGE-INCOMPLETE",
            "grounding",
            "hard",
            artifact.as_posix(),
            "no centroid-role surface passage exists",
        )
    return None


def diagnostic_legacy_view(
    receipt: dict[str, Any],
    *,
    artifact: Path,
    project_root: Path | None,
    wiki_root: Path | None,
) -> dict[str, Any]:
    """Project permanent non-authoritative v3 compatibility data to v2.

    The caller-supplied diagnostic view is quarantined compatibility input, not
    evidence authority.  Future extraction, bibliography, locator,
    classification, span, and coverage objects are intentionally not inspected
    here.  Later hardening must cross-check this view against independently
    validated future evidence before diagnostic execution.  The two roots are
    accepted only to freeze the retained production call surface; resolving
    them here would implement trust predicates before their independently
    reviewed red tests exist.
    """
    del project_root, wiki_root
    if (
        receipt.get("authority_mode") != "legacy_compatibility"
        or receipt.get("target") != "FINAL"
        or receipt.get("phase") != "generation"
        or receipt.get("role") != "generator"
        or set(receipt) != V3_LEGACY_COMPATIBILITY_FIELDS
    ):
        raise AssuranceError(
            "SEMANTIC-RECEIPT-VERSION",
            "semantic v3 is available only for the exact FINAL generation "
            "legacy-compatibility surface",
        )
    view = receipt.get("diagnostic_legacy_view")
    if (
        not isinstance(view, dict)
        or set(view) != {"passages"}
        or not isinstance(view.get("passages"), list)
        or not view["passages"]
    ):
        raise AssuranceError(
            "SEMANTIC-RECEIPT-VERSION",
            "semantic v3 diagnostic legacy view is incomplete",
        )
    projected = {
        "schema_version": "2.0.0",
        "receipt_type": "centroid_semantic_execution",
        "phase": receipt.get("phase"),
        "artifact": {"path": str(artifact), "sha256": sha256(artifact)},
        "passages": view["passages"],
        "semantic_assessment": receipt.get("semantic_assessment"),
    }
    return projected


def build(
    artifact: Path,
    receipt_path: Path,
    *,
    project_root: Path | None = None,
    wiki_root: Path | None = None,
) -> dict[str, Any]:
    artifact = artifact.resolve(strict=True)
    receipt_path = receipt_path.resolve(strict=True)
    try:
        receipt, receipt_bytes = load_canonical_document(
            receipt_path,
            schema_code="EVIDENCE-SCHEMA-INVALID",
        )
    except EvidenceValidationError as exc:
        raise AssuranceError(exc.code, exc.message) from exc
    has_diagnostic_view = "diagnostic_legacy_view" in receipt
    if (
        receipt.get("schema_version") == "2.0.0"
        and receipt.get("receipt_type") == "centroid_semantic_execution"
        and not has_diagnostic_view
    ):
        if not V2_REQUIRED_FIELDS <= set(receipt) or not set(receipt) <= V2_FIELDS:
            raise AssuranceError(
                "EVIDENCE-SCHEMA-INVALID",
                "v2 semantic receipt fields do not match the closed schema",
            )
        working_receipt = receipt
    elif (
        receipt.get("schema_version") == "3.0.0"
        and receipt.get("receipt_type") == "centroid_semantic_execution"
        and receipt.get("authority_mode") == "legacy_compatibility"
    ):
        if set(receipt) != V3_LEGACY_COMPATIBILITY_FIELDS:
            raise AssuranceError(
                "SEMANTIC-RECEIPT-VERSION",
                "v3 semantic receipt fields do not match the closed C2 schema",
            )
        try:
            working_receipt = validate_v3_receipt(
                receipt,
                artifact=artifact,
                project_root=project_root,
                wiki_root=wiki_root,
            )
        except EvidenceValidationError as exc:
            raise AssuranceError(exc.code, exc.message) from exc
    else:
        raise AssuranceError("SEMANTIC-RECEIPT-VERSION", "product assurance requires a v2 semantic receipt")
    if receipt_bytes != canonical_bytes(receipt):
        raise AssuranceError(
            "EVIDENCE-CANONICALIZATION-INVALID",
            "semantic receipt is not in the frozen canonical JSON form",
        )
    bound_artifact = resolve_binding(working_receipt.get("artifact"), "ARTIFACT-BINDING")
    if bound_artifact != artifact:
        raise AssuranceError("ARTIFACT-BINDING", "semantic receipt targets a different artifact")
    text = artifact.read_bytes().decode("utf-8", errors="strict")
    passages = working_receipt.get("passages")
    if not isinstance(passages, list) or not passages:
        raise AssuranceError("PASSAGE-MISSING", "semantic receipt contains no passages")
    hard, corpus = _hard_evidence_findings(artifact, text, passages)
    if receipt.get("schema_version") == "2.0.0":
        coverage_finding = _legacy_centroid_surface_finding(receipt, artifact)
        if coverage_finding is not None:
            hard.append(coverage_finding)
    semantic = _semantic_findings(artifact, text, corpus)
    corpus_sha256 = hashlib.sha256(corpus.encode("utf-8")).hexdigest()
    corpus_binding_sha256 = _corpus_binding_sha256(receipt)
    policy_binding = receipt.get("policy", receipt.get("centroid_packet", {}))
    policy_sha256 = (
        policy_binding.get("sha256")
        if isinstance(policy_binding, dict)
        and isinstance(policy_binding.get("sha256"), str)
        and SHA_RE.fullmatch(policy_binding["sha256"])
        else "0" * 64
    )
    for row in semantic:
        row["candidate_fingerprint"] = _candidate_fingerprint(
            row,
            artifact_sha256=sha256(artifact),
            corpus_binding_sha256=corpus_binding_sha256,
            policy_sha256=policy_sha256,
        )
    adjudications = working_receipt.get("adjudications", [])
    if not isinstance(adjudications, list):
        raise AssuranceError("ADJUDICATION-SHAPE", "adjudications must be an array")
    cleared: list[dict[str, Any]] = []
    remaining_semantic = list(semantic)
    for row in adjudications:
        if (
            not isinstance(row, dict)
            or set(row) != {
                "candidate_fingerprint", "code", "locator", "disposition", "rationale"
            }
            or not isinstance(row.get("candidate_fingerprint"), str)
            or not SHA_RE.fullmatch(row["candidate_fingerprint"])
            or row.get("disposition") not in {"accepted_synthesis", "false_positive", "resolved_in_bytes"}
            or not isinstance(row.get("rationale"), str)
            or not row["rationale"].strip()
        ):
            raise AssuranceError("ADJUDICATION-SHAPE", "adjudication row is invalid")
        match = next((item for item in remaining_semantic
                      if item["code"] == row.get("code")
                      and item["locator"] == row.get("locator")
                      and item["candidate_fingerprint"]
                      == row.get("candidate_fingerprint")), None)
        if match is None:
            raise AssuranceError(
                "ADJUDICATION-STALE",
                f"adjudication does not match a current candidate: {row.get('code')} at {row.get('locator')}",
            )
        remaining_semantic.remove(match)
        cleared.append({**row, "evidence": match["evidence"]})
    findings = hard + remaining_semantic
    dimensions = {
        "quotation": "failed" if any(f["dimension"] == "quotation" for f in hard) else "passed",
        "citation": "failed" if any(f["dimension"] == "citation" for f in hard) else "passed",
        "grounding": "needs_adjudication" if any(f["dimension"] == "grounding" for f in remaining_semantic) else "passed",
        "register": "needs_adjudication" if any(f["dimension"] == "register" for f in remaining_semantic) else "passed",
    }
    status = "passed" if not findings else (
        "needs_adjudication" if not hard and working_receipt.get("phase") == "generation" else "blocked"
    )
    return {
        "schema_version": "1.0.0", "report_type": "product_assurance",
        "status": status,
        "artifact": {"path": str(artifact), "sha256": sha256(artifact)},
        "semantic_receipt": {
            "path": str(receipt_path),
            "sha256": hashlib.sha256(receipt_bytes).hexdigest(),
        },
        "corpus_extract_sha256": corpus_sha256,
        "dimensions": dimensions, "findings": findings, "adjudications": cleared,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("build")
    command.add_argument("--artifact", type=Path, required=True)
    command.add_argument("--semantic-receipt", type=Path, required=True)
    command.add_argument("--project-root", type=Path)
    command.add_argument("--wiki-root", type=Path)
    command.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        assert_writable(args.out.resolve(), purpose="product-assurance report")
    except DestinationRefused as exc:
        print(json.dumps({"status": "blocked", "reason_code": exc.code, "detail": str(exc)}))
        return 4
    try:
        report = build(
            args.artifact,
            args.semantic_receipt,
            project_root=args.project_root,
            wiki_root=args.wiki_root,
        )
    except (AssuranceError, OSError, UnicodeError) as exc:
        code = exc.code if isinstance(exc, AssuranceError) else "PRODUCT-ASSURANCE-IO"
        message = exc.message if isinstance(exc, AssuranceError) else str(exc)
        report = {"schema_version": "1.0.0", "report_type": "product_assurance",
                  "status": "blocked", "findings": [finding(
                      code, "evidence", "hard", "$", message)]}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report.get("status") in {"passed", "needs_adjudication"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
