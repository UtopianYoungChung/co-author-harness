#!/usr/bin/env python3
"""centroid-sentence-logic — admitted-passage sentence-pair instrument.

The binder stays a binder. This script does not emit a scholarly CLEAN
verdict. It fail-closes without a binding_resolved packet, matching
manuscript bytes, and admitted passages (Joseph paste or hash-bound PDF
pages). Roles fill pair verdicts. SK-32 stays CLOSED.

Join-cadence is a miss of its own: S_n+1 must show derivation from S_n,
not only an attested hinge. Mechanical signals only. No CLEAN mint.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from destination_capability import DestinationRefused, assert_writable

YU_2011 = "yu-et-al-2011-social-modeling"
DENNETT = "dennett-1987-intentional-stance"
YU_PAGES = set(range(3, 11)) | set(range(11, 53))
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"“])")
WORD_RE = re.compile(r"[A-Za-z0-9']+")
VERDICT_OPEN = re.compile(r"^(thus|therefore|hence|so|accordingly|in short)\b", re.I)
DERIVE_CUE = re.compile(
    r"\b(which means|that dependency|the same actor|because|so that|in virtue of|from this|from that|this means|that means)\b",
    re.I,
)
RETRACT_CUE = re.compile(r"\b(but|however|yet|instead|rather|although)\b", re.I)
BACKTRACK_CUE = re.compile(
    r"\b(return to|that earlier|as above|we still|still owe|the same (actor|goal|dependency)|back to)\b",
    re.I,
)
SHORT_WORDS = 12
STACK_MIN_SENTENCES = 3
CONTENT_STOP = frozenset(
    {
        "that", "this", "with", "from", "they", "them", "their", "have", "been",
        "were", "which", "into", "also", "only", "does", "than", "then", "thus",
        "therefore", "hence", "such", "into", "over", "under",
    }
)
MODES = ("write", "review", "revise")


class Refusal(RuntimeError):
    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


def _sha_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha_text(text: str) -> str:
    return _sha_bytes(text.encode("utf-8"))


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise Refusal("SENTENCE-LOGIC-INPUT", f"JSON root must be an object: {path}")
    return data


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def _write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _page_from_locator(locator: str) -> int | None:
    match = re.search(r"(?:p{1,2}\.?|page)\s*(\d+)", locator, re.I)
    if match:
        return int(match.group(1))
    match = re.search(r"\b(\d+)\b", locator)
    return int(match.group(1)) if match else None


def _validate_passage(row: dict[str, Any], *, admitted_by: str) -> dict[str, Any]:
    source_key = str(row.get("source_key", "")).strip()
    locator = str(row.get("locator", "")).strip()
    quote = str(row.get("quote", "")).strip()
    if not source_key or not locator or not quote:
        raise Refusal("SENTENCE-LOGIC-PASSAGE", "each admitted passage needs source_key, locator, and quote")
    quote_sha = str(row.get("quote_sha256") or _sha_text(quote))
    if quote_sha != _sha_text(quote):
        raise Refusal("SENTENCE-LOGIC-PASSAGE", f"quote_sha256 does not match quote bytes: {source_key}")
    layer = str(row.get("warrant_layer") or ("argument" if source_key == DENNETT else "surface"))
    if source_key == YU_2011:
        page = _page_from_locator(locator)
        if page is None or page not in YU_PAGES:
            raise Refusal(
                "SENTENCE-LOGIC-SCOPE",
                f"Yu 2011 passage is outside book pp. 3-10 and 11-52: {locator}",
            )
        if layer != "surface":
            raise Refusal("SENTENCE-LOGIC-ROLE", "Yu 2011 warrant_layer must be surface")
    if source_key == DENNETT and layer != "argument":
        raise Refusal("SENTENCE-LOGIC-ROLE", "Dennett warrant_layer must be argument")
    return {
        "source_key": source_key,
        "locator": locator,
        "quote": quote,
        "quote_sha256": quote_sha,
        "warrant_layer": layer,
        "admitted_by": admitted_by,
    }


def _passages_from_json(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = raw if isinstance(raw, list) else raw.get("passages")
    if not isinstance(rows, list):
        raise Refusal("SENTENCE-LOGIC-PASSAGE", "passages file must be a list or {passages: []}")
    return [_validate_passage(row, admitted_by="joseph") for row in rows if isinstance(row, dict)]


def _extract_pdf_page(pdf_path: Path, page_number: int) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    index = page_number - 1
    if index < 0 or index >= len(reader.pages):
        raise Refusal("SENTENCE-LOGIC-PDF", f"{pdf_path.name} has no page {page_number}")
    text = reader.pages[index].extract_text() or ""
    if not text.strip():
        raise Refusal("SENTENCE-LOGIC-PDF", f"{pdf_path.name} page {page_number} extracted empty text")
    return text


def _passages_from_pdf(pdf_path: Path, source_key: str, pages: list[int], layer: str) -> list[dict[str, Any]]:
    file_sha = _sha_bytes(pdf_path.read_bytes())
    out: list[dict[str, Any]] = []
    for page in pages:
        quote = _extract_pdf_page(pdf_path, page)
        row = _validate_passage(
            {
                "source_key": source_key,
                "locator": f"hash-bound PDF {pdf_path.name} p. {page} sha256={file_sha}",
                "quote": quote,
                "warrant_layer": layer,
            },
            admitted_by="hash-bound-pdf",
        )
        row["pdf_sha256"] = file_sha
        row["page"] = page
        out.append(row)
    return out


def _sentences(text: str) -> list[str]:
    parts = [part.strip() for part in SENTENCE_SPLIT.split(text) if part.strip()]
    return parts if parts else [text.strip()] if text.strip() else []


def _words(text: str) -> list[str]:
    return WORD_RE.findall(text)


def _content(text: str) -> set[str]:
    return {word.lower() for word in _words(text) if len(word) >= 4 and word.lower() not in CONTENT_STOP}


def _join_signals(left: str, right: str) -> dict[str, Any]:
    right_words = _words(right)
    short_right = len(right_words) <= SHORT_WORDS
    derive = bool(DERIVE_CUE.search(right))
    verdict = bool(VERDICT_OPEN.search(right.strip()))
    retract = bool(RETRACT_CUE.search(right))
    backtrack = bool(BACKTRACK_CUE.search(right))
    shared = bool(_content(left) & _content(right))
    if derive:
        cadence = "derivation_shown"
    elif short_right and verdict:
        cadence = "unearned_verdict"
    else:
        cadence = None
    if backtrack:
        needed = "present"
    elif retract and short_right and not shared:
        needed = "missing"
    else:
        needed = "not_required"
    return {
        "join_cadence": cadence,
        "needed_backtrack": needed,
        "s_n_words": len(_words(left)),
        "s_n1_words": len(right_words),
    }


def _all_short_stack(sentences: list[str]) -> bool:
    if len(sentences) < STACK_MIN_SENTENCES:
        return False
    return all(len(_words(sentence)) <= SHORT_WORDS for sentence in sentences)


def _pairs(sentences: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index in range(len(sentences) - 1):
        left = sentences[index]
        right = sentences[index + 1]
        signals = _join_signals(left, right)
        rows.append(
            {
                "n": index + 1,
                "s_n": left,
                "s_n1": right,
                "s_n_sha256": _sha_text(left),
                "s_n1_sha256": _sha_text(right),
                "verdict": "not_run",
                "yu_hinge": None,
                "dennett_warrant": None,
                "checks": {
                    "carry": None,
                    "hinge": None,
                    "attestation": None,
                    "scope": None,
                    "voice": None,
                    "role_split": None,
                    "join_cadence": signals["join_cadence"],
                    "needed_backtrack": signals["needed_backtrack"],
                },
                "word_counts": {
                    "s_n": signals["s_n_words"],
                    "s_n1": signals["s_n1_words"],
                },
            }
        )
    return rows


def _markdown_receipt(receipt: dict[str, Any]) -> str:
    lines = [
        f"# centroid-sentence-logic ({receipt['mode']})",
        "",
        f"- status: `{receipt['status']}`",
        f"- reason_code: `{receipt['reason_code']}`",
        f"- packet_sha256: `{receipt['packet_sha256']}`",
        f"- manuscript_sha256: `{receipt['manuscript_sha256']}`",
        f"- graph_state: `{receipt['graph_state']}`",
        f"- admitted_passages: {len(receipt['admitted_passages'])}",
        f"- pairs: {len(receipt['pairs'])} (verdicts not_run; roles fill CLEAN/ADVISORY/BLOCKER)",
        f"- all_short_stack: `{receipt['summary'].get('all_short_stack')}`",
        f"- join_cadence_misses: {receipt['summary'].get('join_cadence_misses')}",
        f"- needed_backtrack_missing: {receipt['summary'].get('needed_backtrack_missing')}",
        f"- one BLOCKER pair fails the bound scope for qualification",
        "",
        "This is not a scholarly CLEAN. Empty binder semantic_findings is not a pass.",
        "SK-32 stays CLOSED. Joseph is the only R-plane actor.",
        "",
    ]
    return "\n".join(lines) + "\n"


def build_receipt(args: argparse.Namespace) -> dict[str, Any]:
    packet_path = Path(args.packet).resolve(strict=True)
    manuscript_path = Path(args.manuscript).resolve(strict=True)
    packet = _load_json(packet_path)
    if packet.get("status") != "binding_resolved":
        raise Refusal("SENTENCE-LOGIC-PACKET", "binder packet is not binding_resolved")
    manuscript_bytes = manuscript_path.read_bytes()
    manuscript_sha = _sha_bytes(manuscript_bytes)
    bound = packet.get("manuscript") or {}
    if bound.get("sha256") != manuscript_sha:
        raise Refusal(
            "SENTENCE-LOGIC-STALE",
            "manuscript sha256 does not match packet.manuscript.sha256; re-run centroid-pass on these bytes",
        )
    scope = bound.get("scope") or {}
    if scope.get("sha256") and scope.get("sha256") != manuscript_sha and args.heading is None:
        raise Refusal("SENTENCE-LOGIC-STALE", "scope sha256 does not match manuscript bytes")
    reason = packet.get("reason_code")
    ineligible = reason == "GRAPH-SEMANTIC-INELIGIBLE"
    graph_state = "ineligible" if ineligible else "eligible"
    if ineligible is False and args.invoke_only:
        raise Refusal(
            "SENTENCE-LOGIC-INVOKE",
            "packet is semantically eligible; invoke-only is for GRAPH-SEMANTIC-INELIGIBLE (auto-run is later)",
        )

    admitted: list[dict[str, Any]] = []
    if args.passages:
        admitted.extend(_passages_from_json(Path(args.passages).resolve(strict=True)))
    if args.admit_pdf:
        pages = [int(item) for item in args.pages.split(",") if item.strip()]
        if not pages:
            raise Refusal("SENTENCE-LOGIC-PDF", "--admit-pdf requires --pages")
        source_key = args.pdf_source_key
        layer = "argument" if source_key == DENNETT else "surface"
        admitted.extend(
            _passages_from_pdf(Path(args.admit_pdf).resolve(strict=True), source_key, pages, layer)
        )
    if ineligible and not admitted:
        raise Refusal(
            "SENTENCE-LOGIC-NO-PASSAGE",
            "GRAPH-SEMANTIC-INELIGIBLE and no admitted passages; pass --passages (Joseph) or --admit-pdf pages",
        )

    text = manuscript_bytes.decode("utf-8", errors="strict")
    sentences = _sentences(text)
    pairs = _pairs(sentences)
    cadence_misses = sum(1 for row in pairs if row["checks"]["join_cadence"] == "unearned_verdict")
    backtrack_misses = sum(1 for row in pairs if row["checks"]["needed_backtrack"] == "missing")
    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return {
        "schema_version": "1.1.0",
        "pass": "centroid-sentence-logic",
        "status": "ready_for_role",
        "reason_code": None,
        "mode": args.mode,
        "packet_path": str(packet_path),
        "packet_sha256": _sha_bytes(packet_path.read_bytes()),
        "manuscript_path": str(manuscript_path),
        "manuscript_sha256": manuscript_sha,
        "scope_sha256": scope.get("sha256") or manuscript_sha,
        "graph_state": graph_state,
        "binder_reason_code": reason,
        "admitted_passages": admitted,
        "pairs": pairs,
        "summary": {
            "not_run": len(pairs),
            "CLEAN": 0,
            "ADVISORY": 0,
            "BLOCKER": 0,
            "qualification": "incomplete",
            "all_short_stack": _all_short_stack(sentences),
            "join_cadence_misses": cadence_misses,
            "needed_backtrack_missing": backtrack_misses,
        },
        "c7": [],
        "actor": "Generator" if args.mode in {"write", "revise"} else "Evaluator",
        "r_plane": "Joseph only",
        "sk32": "CLOSED",
        "created_at": created,
        "limitations": [
            "Instrument listed pairs and bound admitted passages only.",
            "Roles fill CLEAN/ADVISORY/BLOCKER. This file is not a scholarly CLEAN.",
            "One BLOCKER pair fails the bound scope for qualification.",
            "Do not copy empty binder semantic_findings as a pass.",
            "join_cadence and needed_backtrack are mechanical signals, not scholarly CLEAN.",
            "A missing join-cadence is a miss even when an attested hinge is named.",
            "Backtrack is not required on every pair.",
        ],
    }


def _out_dir(args: argparse.Namespace) -> Path | None:
    if args.shipment_id:
        if not args.project_root:
            raise Refusal("SENTENCE-LOGIC-DEST", "--shipment-id requires --project-root")
        dest = Path(args.project_root).resolve() / "reviews" / ".harness" / "shipments" / args.shipment_id
    elif args.out_dir:
        dest = Path(args.out_dir).resolve()
    else:
        return None
    assert_writable(dest, purpose="centroid-sentence-logic receipt")
    dest.mkdir(parents=True, exist_ok=True)
    return dest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True)
    parser.add_argument("--manuscript", required=True)
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--passages", help="Joseph-admitted passages JSON")
    parser.add_argument("--admit-pdf", help="Hash-bound PDF to read as admitted pages")
    parser.add_argument("--pages", help="Comma-separated PDF page numbers (book pagination)")
    parser.add_argument("--pdf-source-key", default=YU_2011)
    parser.add_argument("--project-root")
    parser.add_argument("--out-dir")
    parser.add_argument("--shipment-id")
    parser.add_argument("--heading")
    parser.add_argument(
        "--invoke-only",
        action="store_true",
        default=True,
        help="Refuse eligible packets (default while graph is ineligible)",
    )
    parser.add_argument("--allow-eligible", action="store_true", help="Permit invoke on a semantically eligible packet")
    args = parser.parse_args(argv)
    if args.allow_eligible:
        args.invoke_only = False
    try:
        receipt = build_receipt(args)
        dest = _out_dir(args)
        if dest is not None:
            stem = f"centroid-sentence-logic_{args.mode}"
            _write_json(dest / f"{stem}.json", receipt)
            _write_md(dest / f"{stem}.md", _markdown_receipt(receipt))
            receipt["written"] = {
                "json": str(dest / f"{stem}.json"),
                "markdown": str(dest / f"{stem}.md"),
            }
        print(json.dumps(receipt, indent=2, ensure_ascii=False))
        return 0
    except (Refusal, DestinationRefused, OSError, json.JSONDecodeError, ValueError) as exc:
        code = getattr(exc, "code", "SENTENCE-LOGIC-IO")
        detail = getattr(exc, "detail", str(exc))
        print(json.dumps({"status": "blocked", "reason_code": code, "detail": detail}, ensure_ascii=False))
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
