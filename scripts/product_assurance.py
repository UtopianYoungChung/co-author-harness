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

from destination_capability import DestinationRefused, assert_writable


SHA_RE = re.compile(r"^[0-9a-f]{64}$")
WORD_RE = re.compile(r"[^\W_]+(?:[-'][^\W_]+)*", re.UNICODE)
QUOTE_SPACE_RE = re.compile(r"\s+")
AUTHOR_YEAR_RE = re.compile(r"\(([^()]{1,120}?),\s*((?:19|20)\d{2}[a-z]?)\)")
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


class AssuranceError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AssuranceError(code, f"cannot read valid JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AssuranceError(code, f"JSON root is not an object: {path}")
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


def line_for(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def finding(code: str, dimension: str, severity: str, locator: str,
            evidence: str, *, tentative: bool = False) -> dict[str, Any]:
    return {
        "code": code, "dimension": dimension, "severity": severity,
        "locator": locator, "evidence": evidence, "tentative": tentative,
    }


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
    corpus_tokens = set(words(corpus))
    lines = text.splitlines()
    references_at = next((i for i, line in enumerate(lines)
                          if re.match(r"^#{1,6}\s+(references|bibliography)\s*$", line.strip(), re.IGNORECASE)),
                         len(lines))
    prose_lines = lines[:references_at]
    manuscript_counts = Counter(words("\n".join(prose_lines)))
    abstract_end = next((i for i, line in enumerate(lines[1:], 1)
                         if line.startswith("#") and "abstract" not in line.casefold()),
                        min(len(lines), 20))
    abstract_text = "\n".join(lines[:abstract_end])

    for number, line in enumerate(prose_lines, 1):
        owned = "[s]" in line.casefold()
        for token in words(line):
            if ("-" in token and token not in corpus_tokens and len(token) >= 6
                    and not owned):
                out.append(finding(
                    "TERM-COINAGE", "grounding", "candidate",
                    f"{artifact.as_posix()}:{number}",
                    f"hyphenated term absent from bound extracts: {token}", tentative=True,
                ))
        if EMPIRICAL_RE.search(line) and not owned and not AUTHOR_YEAR_RE.search(line):
            out.append(finding(
                "EMPIRICAL-UNSUPPORTED", "grounding", "candidate",
                f"{artifact.as_posix()}:{number}",
                line.strip()[:240], tentative=True,
            ))

    seen_prefix = ""
    for match in INSIDER_RE.finditer(abstract_text):
        phrase = match.group(1).strip().rstrip(".,;:")
        head = phrase.split()[0].casefold()
        if head not in set(words(seen_prefix)):
            out.append(finding(
                "INSIDER-NEGATION", "register", "candidate",
                f"{artifact.as_posix()}:{line_for(abstract_text, match.start())}",
                f"abstract negates an unintroduced reader term: {phrase}", tentative=True,
            ))
        seen_prefix = abstract_text[:match.end()]

    for token, count in sorted(manuscript_counts.items()):
        if (count >= 3 and token not in corpus_tokens and token not in STOPWORDS
                and len(token) >= 6 and "-" not in token):
            out.append(finding(
                "REGISTER-ABSENT", "register", "candidate", artifact.as_posix(),
                f"high-frequency manuscript token absent from bound extracts: {token} ({count}x)",
                tentative=True,
            ))
    return out


def build(artifact: Path, receipt_path: Path) -> dict[str, Any]:
    artifact = artifact.resolve(strict=True)
    receipt_path = receipt_path.resolve(strict=True)
    receipt = load_json(receipt_path, "SEMANTIC-RECEIPT")
    if receipt.get("schema_version") != "2.0.0" or receipt.get("receipt_type") != "centroid_semantic_execution":
        raise AssuranceError("SEMANTIC-RECEIPT-VERSION", "product assurance requires a v2 semantic receipt")
    bound_artifact = resolve_binding(receipt.get("artifact"), "ARTIFACT-BINDING")
    if bound_artifact != artifact:
        raise AssuranceError("ARTIFACT-BINDING", "semantic receipt targets a different artifact")
    text = artifact.read_text(encoding="utf-8", errors="strict")
    passages = receipt.get("passages")
    if not isinstance(passages, list) or not passages:
        raise AssuranceError("PASSAGE-MISSING", "semantic receipt contains no passages")
    hard, corpus = _hard_evidence_findings(artifact, text, passages)
    semantic = _semantic_findings(artifact, text, corpus)
    adjudications = receipt.get("adjudications", [])
    if not isinstance(adjudications, list):
        raise AssuranceError("ADJUDICATION-SHAPE", "adjudications must be an array")
    cleared: list[dict[str, Any]] = []
    remaining_semantic = list(semantic)
    for row in adjudications:
        if (
            not isinstance(row, dict)
            or set(row) != {"code", "locator", "disposition", "rationale"}
            or row.get("disposition") not in {"accepted_synthesis", "false_positive", "resolved_in_bytes"}
            or not isinstance(row.get("rationale"), str)
            or not row["rationale"].strip()
        ):
            raise AssuranceError("ADJUDICATION-SHAPE", "adjudication row is invalid")
        match = next((item for item in remaining_semantic
                      if item["code"] == row.get("code") and item["locator"] == row.get("locator")), None)
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
        "needs_adjudication" if not hard and receipt.get("phase") == "generation" else "blocked"
    )
    return {
        "schema_version": "1.0.0", "report_type": "product_assurance",
        "status": status,
        "artifact": {"path": str(artifact), "sha256": sha256(artifact)},
        "semantic_receipt": {"path": str(receipt_path), "sha256": sha256(receipt_path)},
        "corpus_extract_sha256": hashlib.sha256(corpus.encode("utf-8")).hexdigest(),
        "dimensions": dimensions, "findings": findings, "adjudications": cleared,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("build")
    command.add_argument("--artifact", type=Path, required=True)
    command.add_argument("--semantic-receipt", type=Path, required=True)
    command.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        assert_writable(args.out.resolve(), purpose="product-assurance report")
    except DestinationRefused as exc:
        print(json.dumps({"status": "blocked", "reason_code": exc.code, "detail": str(exc)}))
        return 4
    try:
        report = build(args.artifact, args.semantic_receipt)
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
