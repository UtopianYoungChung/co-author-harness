#!/usr/bin/env python3
"""centroid-check — join consecutive sentences to admitted Yu/Dennett passages.

This CLI is centroid-check. It is not centroid-source and not a centroid-bind.

  centroid-source  live policy member yu-et-al-2011-social-modeling (role
                   centroid). Retrieval is the Yu-authored window only: book
                   pp. 3-10 and 11-52. Dennett is argument-only warrant, not
                   a second centroid. That object does not move when this
                   check binds new manuscript bytes.
  centroid-check   this instrument. Requires named manuscript bytes at start.
                   A check of live M4 is a check, not a redefinition of
                   centroid-source. Receipts say: this is a centroid-check of
                   manuscript <sha256/bytes> against centroid-source
                   yu-et-al-2011-social-modeling.
  centroid-bind    scripts/centroid_service.py packet (policy + graph
                   eligibility + named bytes). GRAPH-SEMANTIC-INELIGIBLE is
                   eligibility, not a pair verdict. Empty binder
                   semantic_findings is not a pass.

--pages is printed book pages (running footer or non-identity labels).
Identity 1…N labels are ignored. Title/foreword/contents are not admitted
Yu body. Legacy PDF-index 3,7,12 is refused.

Public skill folder remains skills/centroid-sentence-logic (catalog id).
The binder stays a binder. No scholarly CLEAN mint. SK-32 stays CLOSED.
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
FRONT_HEADING_RE = re.compile(
    r"(?im)^\s*(title page|title|foreword|preface|table of contents|contents|copyright)\s*$"
)
PRINTED_PAGE_RE = re.compile(r"(?m)^\s*(?:pp?\.\s*)?(\d{1,3})(?:\s+\S.*)?\s*$")
OBJECT_NAMES = {
    "centroid-source": "live policy member yu-et-al-2011-social-modeling (role centroid)",
    "centroid-check": "this instrument: sentence-logic on named manuscript bytes",
    "centroid-bind": "centroid_service packet; GRAPH-SEMANTIC-INELIGIBLE is eligibility, not a pair verdict",
}
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


def _is_front_matter(text: str) -> bool:
    head = "\n".join(text.splitlines()[:8])
    return bool(FRONT_HEADING_RE.search(head))


def _printed_page_number(text: str, identity: int, label: str | None) -> int | None:
    """Return a printed book page. Identity 1…N labels are ignored."""
    if label is not None:
        stripped = str(label).strip()
        if stripped.isdigit() and int(stripped) != identity:
            return int(stripped)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in reversed(lines[-4:]):
        match = PRINTED_PAGE_RE.fullmatch(line)
        if not match:
            continue
        printed = int(match.group(1))
        if printed != identity:
            return printed
        if not _is_front_matter(text):
            return printed
    return None


def resolve_printed_pages(pages: list[dict[str, Any]], requested: list[int]) -> list[dict[str, Any]]:
    """Map --pages (printed book pages) onto page records. Refuse identity/front-matter."""
    by_printed: dict[int, dict[str, Any]] = {}
    annotated: list[dict[str, Any]] = []
    for rec in pages:
        printed = _printed_page_number(rec["text"], rec["identity"], rec.get("label"))
        row = {**rec, "printed_page": printed}
        annotated.append(row)
        if printed is None:
            continue
        if printed in by_printed:
            raise Refusal("SENTENCE-LOGIC-PDF", f"printed book page {printed} is ambiguous")
        by_printed[printed] = row

    out: list[dict[str, Any]] = []
    for page in requested:
        rec = by_printed.get(page)
        if rec is None:
            identity_hits = [row for row in annotated if row["identity"] == page]
            if identity_hits and (
                _is_front_matter(identity_hits[0]["text"])
                or identity_hits[0].get("label") == str(page)
            ):
                raise Refusal(
                    "SENTENCE-LOGIC-PDF-INDEX",
                    f"legacy PDF-index {page} is an identity 1…N label or "
                    "title/foreword/contents, not a printed book page",
                )
            raise Refusal(
                "SENTENCE-LOGIC-PDF",
                f"printed book page {page} was not found (identity 1…N labels are ignored)",
            )
        if _is_front_matter(rec["text"]):
            raise Refusal(
                "SENTENCE-LOGIC-PDF",
                f"printed book page {page} is title/foreword/contents, not admitted Yu body",
            )
        out.append(rec)
    return out


def _pdf_page_records(pdf_path: Path) -> list[dict[str, Any]]:
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    try:
        labels = list(reader.page_labels)
    except Exception:
        labels = [None] * len(reader.pages)
    records: list[dict[str, Any]] = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        label = labels[index - 1] if index - 1 < len(labels) else None
        records.append({"identity": index, "text": text, "label": label})
    return records


def _passages_from_pdf(pdf_path: Path, source_key: str, pages: list[int], layer: str) -> list[dict[str, Any]]:
    file_sha = _sha_bytes(pdf_path.read_bytes())
    resolved = resolve_printed_pages(_pdf_page_records(pdf_path), pages)
    out: list[dict[str, Any]] = []
    for rec in resolved:
        quote = rec["text"]
        if not quote.strip():
            raise Refusal("SENTENCE-LOGIC-PDF", f"{pdf_path.name} printed p. {rec['printed_page']} extracted empty text")
        page = rec["printed_page"]
        row = _validate_passage(
            {
                "source_key": source_key,
                "locator": f"hash-bound PDF {pdf_path.name} printed p. {page} sha256={file_sha}",
                "quote": quote,
                "warrant_layer": layer,
            },
            admitted_by="hash-bound-pdf",
        )
        row["pdf_sha256"] = file_sha
        row["page"] = page
        row["pdf_identity"] = rec["identity"]
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


def _check_sentence(receipt: dict[str, Any]) -> str:
    return (
        f"this is a centroid-check of manuscript {receipt['manuscript_sha256']}/"
        f"{receipt['manuscript_bytes']} against centroid-source {YU_2011}"
    )


def _markdown_receipt(receipt: dict[str, Any]) -> str:
    lines = [
        f"# centroid-check ({receipt['mode']})",
        "",
        _check_sentence(receipt) + ".",
        "",
        "This is not centroid-source and not a centroid-bind. A check of these "
        "manuscript bytes does not redefine centroid-source.",
        "GRAPH-SEMANTIC-INELIGIBLE on the centroid-bind packet is eligibility, not a pair verdict.",
        "",
        f"- instrument: `centroid-check`",
        f"- centroid-source: `{receipt['centroid_source']}`",
        f"- status: `{receipt['status']}`",
        f"- reason_code: `{receipt['reason_code']}`",
        f"- packet_sha256: `{receipt['packet_sha256']}`",
        f"- manuscript_sha256: `{receipt['manuscript_sha256']}`",
        f"- manuscript_bytes: `{receipt['manuscript_bytes']}`",
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
        raise Refusal("SENTENCE-LOGIC-PACKET", "centroid-bind packet is not binding_resolved")
    requested_source = str(getattr(args, "centroid_source", YU_2011) or YU_2011)
    if requested_source != YU_2011:
        raise Refusal(
            "SENTENCE-LOGIC-SOURCE",
            "centroid-source is yu-et-al-2011-social-modeling; this check does not move that object",
        )
    manuscript_bytes = manuscript_path.read_bytes()
    manuscript_sha = _sha_bytes(manuscript_bytes)
    bound = packet.get("manuscript") or {}
    if bound.get("sha256") != manuscript_sha:
        raise Refusal(
            "SENTENCE-LOGIC-STALE",
            "manuscript sha256 does not match packet.manuscript.sha256; re-run centroid-bind on these bytes",
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
    receipt = {
        "schema_version": "1.2.0",
        "pass": "centroid-check",
        "instrument": "centroid-check",
        "centroid_source": YU_2011,
        "object_names": dict(OBJECT_NAMES),
        "status": "ready_for_role",
        "reason_code": None,
        "mode": args.mode,
        "packet_path": str(packet_path),
        "packet_sha256": _sha_bytes(packet_path.read_bytes()),
        "manuscript_path": str(manuscript_path),
        "manuscript_sha256": manuscript_sha,
        "manuscript_bytes": len(manuscript_bytes),
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
            "This is a centroid-check of named manuscript bytes against centroid-source yu-et-al-2011-social-modeling.",
            "GRAPH-SEMANTIC-INELIGIBLE is eligibility, not a pair verdict.",
            "Instrument listed pairs and bound admitted passages only.",
            "Roles fill CLEAN/ADVISORY/BLOCKER. This file is not a scholarly CLEAN.",
            "One BLOCKER pair fails the bound scope for qualification.",
            "Do not copy empty binder semantic_findings as a pass.",
            "join_cadence and needed_backtrack are mechanical signals, not scholarly CLEAN.",
            "A missing join-cadence is a miss even when an attested hinge is named.",
            "Backtrack is not required on every pair.",
        ],
    }
    receipt["naming"] = _check_sentence(receipt)
    return receipt


def _out_dir(args: argparse.Namespace) -> Path | None:
    if args.shipment_id:
        if not args.project_root:
            raise Refusal("SENTENCE-LOGIC-DEST", "--shipment-id requires --project-root")
        dest = Path(args.project_root).resolve() / "reviews" / "harness" / "shipments" / args.shipment_id
    elif args.out_dir:
        dest = Path(args.out_dir).resolve()
    else:
        return None
    assert_writable(dest, purpose="centroid-check receipt")
    dest.mkdir(parents=True, exist_ok=True)
    return dest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True, help="centroid-bind packet JSON (not centroid-source)")
    parser.add_argument("--manuscript", required=True, help="Named manuscript bytes for this centroid-check")
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument(
        "--centroid-source",
        default=YU_2011,
        help="centroid-source key. Locked to yu-et-al-2011-social-modeling. Does not move the policy centroid.",
    )
    parser.add_argument("--passages", help="Joseph-admitted passages JSON")
    parser.add_argument("--admit-pdf", help="Hash-bound PDF to read as admitted printed book pages")
    parser.add_argument(
        "--pages",
        help=(
            "Printed book pages (running footer or non-identity labels). "
            "Identity 1…N labels are ignored. Title/foreword/contents are not "
            "admitted Yu body. Legacy PDF-index 3,7,12 is refused."
        ),
    )
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
            stem = f"centroid-check_{args.mode}"
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
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="strict")
    raise SystemExit(main())
