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

--pages names printed book pages. PDF admission requires a policy-pinned PDF
and a validated canonical extraction receipt for those pages.

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

import centroid_service as binder
from centroid_text import inventory
from centroid_source_evidence import SourceEvidenceError
from destination_capability import DestinationRefused, assert_writable

YU_2011 = "yu-et-al-2011-social-modeling"
DENNETT = "dennett-1987-intentional-stance"
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


def _load_json(payload: bytes, path: Path) -> dict[str, Any]:
    def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise Refusal("SENTENCE-LOGIC-INPUT", f"duplicate JSON key {key!r}: {path}")
            result[key] = value
        return result

    def nonfinite(value: str) -> None:
        raise Refusal("SENTENCE-LOGIC-INPUT", f"nonfinite JSON number {value}: {path}")

    data = json.loads(payload.decode("utf-8", errors="strict"),
                      object_pairs_hook=unique_pairs, parse_constant=nonfinite)
    if not isinstance(data, dict):
        raise Refusal("SENTENCE-LOGIC-INPUT", f"JSON root must be an object: {path}")
    return data


def _validate_packet(packet: dict[str, Any]) -> None:
    try:
        from jsonschema import Draft202012Validator
        from jsonschema.exceptions import SchemaError
    except ImportError as exc:
        raise Refusal("SENTENCE-LOGIC-SCHEMA", f"jsonschema dependency unavailable: {exc}") from exc
    schema_path = Path(__file__).resolve().parents[1] / "references" / "schemas" / "centroid_analysis.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    try:
        Draft202012Validator.check_schema(schema)
        errors = sorted(Draft202012Validator(schema).iter_errors(packet), key=lambda item: str(item.path))
    except SchemaError as exc:
        raise Refusal("SENTENCE-LOGIC-SCHEMA", f"invalid binder schema: {exc.message}") from exc
    if errors:
        raise Refusal("SENTENCE-LOGIC-PACKET", f"centroid-bind schema invalid at {list(errors[0].path)}: {errors[0].message}")
    if packet["status"] != "binding_resolved":
        raise Refusal("SENTENCE-LOGIC-PACKET", "centroid-bind packet is not binding_resolved")
    manuscript = packet["manuscript"]
    scope = manuscript.get("scope") if isinstance(manuscript, dict) else None
    if not isinstance(manuscript, dict) or not isinstance(manuscript.get("path"), str) or not manuscript["path"].strip():
        raise Refusal("SENTENCE-LOGIC-PACKET", "packet manuscript path must be a nonblank string")
    if not isinstance(scope, dict) or scope.get("kind") not in {"heading", "full_manuscript"}:
        raise Refusal("SENTENCE-LOGIC-PACKET", "packet manuscript scope is incomplete")
    required_scope = {"kind", "heading", "start_line", "end_line", "sha256"}
    if not required_scope <= scope.keys() or not all(type(scope.get(k)) is int for k in ("start_line", "end_line")):
        raise Refusal("SENTENCE-LOGIC-PACKET", "packet scope lacks binder fields")
    if scope["start_line"] < 1 or scope["end_line"] < scope["start_line"]:
        raise Refusal("SENTENCE-LOGIC-PACKET", "packet scope line range invalid")
    if scope["kind"] == "heading" and not isinstance(scope["heading"], str):
        raise Refusal("SENTENCE-LOGIC-PACKET", "heading scope needs heading text")
    if scope["kind"] == "full_manuscript" and scope["heading"] is not None:
        raise Refusal("SENTENCE-LOGIC-PACKET", "full manuscript scope cannot name a heading")
    for item in (manuscript.get("sha256"), scope.get("sha256")):
        if not isinstance(item, str) or not re.fullmatch(r"[0-9a-f]{64}", item):
            raise Refusal("SENTENCE-LOGIC-PACKET", "packet manuscript hashes invalid")
    if packet.get("centroid_source", {}).get("source_key") != YU_2011:
        raise Refusal("SENTENCE-LOGIC-PACKET", "packet centroid-source mismatch")
    if packet.get("semantic_findings") != []:
        raise Refusal("SENTENCE-LOGIC-PACKET", "binder cannot provide semantic findings")
    if not isinstance(packet.get("analysis_contract"), dict) or not isinstance(packet.get("policy"), dict):
        raise Refusal("SENTENCE-LOGIC-PACKET", "binder policy or analysis contract is missing")


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def _write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _passages_from_pdf(pdf_path: Path, source_key: str, pages: list[int], layer: str, *,
                       extract_receipt: Path | None, evidence_root: Path | None,
                       wiki_root: Path | None) -> list[dict[str, Any]]:
    from centroid_source_evidence import passages_from_pdf
    return passages_from_pdf(pdf_path, source_key, pages, layer,
                             extract_receipt=extract_receipt, evidence_root=evidence_root,
                             wiki_root=wiki_root, policy_path=binder.POLICY_PATH)


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
        cadence = "derivation_cue_present"
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
    }


def _all_short_stack(sentences: list[str]) -> bool:
    if len(sentences) < STACK_MIN_SENTENCES:
        return False
    return all(len(_words(sentence)) <= SHORT_WORDS for sentence in sentences)


def _pairs(sentences: list[str]) -> list[dict[str, Any]]:
    """Compatibility helper for direct synthetic signal probes."""
    rows: list[dict[str, Any]] = []
    for index in range(len(sentences) - 1):
        rows.append({"id": f"pair{index + 1}", "left_id": f"s{index + 1}",
                     "right_id": f"s{index + 2}", "verdict": "not_run",
                     "signals": _join_signals(sentences[index], sentences[index + 1])})
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
        "SK-32 stays CLOSED. The author is the only R-plane actor.",
        "",
    ]
    return "\n".join(lines) + "\n"


def _review_view(receipt: dict[str, Any]) -> str:
    """Compact role-facing view; stable IDs point to the machine evidence."""
    lines = [f"centroid-check {receipt['mode']} | {receipt['graph_state']} | {len(receipt['sentences'])} sentences | {len(receipt['pairs'])} pairs",
             f"manuscript {receipt['manuscript_sha256']} scope {receipt['scope']['kind']} heading={receipt['scope']['heading']!r} lines={receipt['scope']['start_line']}-{receipt['scope']['end_line']} sha256={receipt['scope']['sha256']}",
             f"packet {receipt['packet_sha256']} policy {receipt['policy_sha256']}",
             "All pair verdicts are not_run; signals are cues only."]
    for row in receipt["admitted_passages"]:
        provenance = " ".join(f"{key}={row[key]}" for key in ("admission_kind", "admitted_by", "pdf_sha256", "extract_receipt_sha256") if key in row)
        lines.append(f"{row['id']} source={row['source_key']} locator={row['locator']} warrant={row['warrant_layer']} {provenance}")
        lines.append(f"  quote: {row['quote']}")
    for row in receipt["sentences"]:
        lines.append(f"{row['id']} [{row['paragraph_id']}]: {row['text']}")
    for pair in receipt["pairs"]:
        left, right = pair["left_id"], pair["right_id"]
        lines.append(f"{pair['id']} {left}→{right} context={','.join(pair['context_paragraph_ids'])} signals={pair['signals']}")
    return "\n".join(lines) + "\n"


def build_receipt(args: argparse.Namespace) -> dict[str, Any]:
    from centroid_source_evidence import passages_from_json

    packet_path = Path(args.packet).resolve(strict=True)
    manuscript_path = Path(args.manuscript).resolve(strict=True)
    packet_bytes = packet_path.read_bytes()
    packet = _load_json(packet_bytes, packet_path)
    _validate_packet(packet)
    if packet["analysis_contract"].get("derivation") != args.mode:
        raise Refusal("SENTENCE-LOGIC-PACKET", "binder analysis mode differs from requested checker mode")
    requested_source = str(getattr(args, "centroid_source", YU_2011) or YU_2011)
    if requested_source != YU_2011:
        raise Refusal("SENTENCE-LOGIC-SOURCE", "centroid-source remains yu-et-al-2011-social-modeling")
    manuscript_bytes = manuscript_path.read_bytes()
    manuscript_sha = _sha_bytes(manuscript_bytes)
    bound = packet["manuscript"]
    if Path(bound.get("path", "")).resolve() != manuscript_path:
        raise Refusal("SENTENCE-LOGIC-STALE", "manuscript path differs from named centroid-bind target")
    if bound.get("sha256") != manuscript_sha:
        raise Refusal("SENTENCE-LOGIC-STALE", "manuscript sha256 differs from centroid-bind packet")
    text = manuscript_bytes.decode("utf-8", errors="strict")
    bound_scope = bound["scope"]
    supplied_heading = getattr(args, "heading", None)
    if supplied_heading is not None and supplied_heading != bound_scope["heading"]:
        raise Refusal("SENTENCE-LOGIC-SCOPE", "supplied heading differs from packet heading")
    try:
        scoped_text, resolved_scope = binder._scope(text, bound_scope["heading"])
    except binder.Unavailable as exc:
        raise Refusal("SENTENCE-LOGIC-SCOPE", exc.detail) from exc
    scope = {**resolved_scope, "sha256": _sha_text(scoped_text)}
    if scope != bound_scope:
        raise Refusal("SENTENCE-LOGIC-STALE", "resolved kind, heading, lines, or scope hash differs from packet")
    current_policy_sha = _sha_bytes(binder.POLICY_PATH.read_bytes())
    try:
        live_centroid = binder._live_centroid_source()
    except binder.Unavailable as exc:
        raise Refusal("SENTENCE-LOGIC-SOURCE", exc.detail) from exc
    if packet["centroid_source"] != live_centroid:
        raise Refusal("SENTENCE-LOGIC-SOURCE", "packet centroid source differs from current policy")
    reason = packet.get("reason_code")
    project_root = Path(args.project_root).resolve(strict=True) if getattr(args, "project_root", None) else None
    if reason == "GRAPH-SEMANTIC-INELIGIBLE":
        pinned = packet["policy"].get("profile_sha256")
        if pinned is not None and pinned != current_policy_sha:
            raise Refusal("SENTENCE-LOGIC-STALE", "ineligible packet policy hash differs from current policy")
        graph_state = "ineligible"
        policy_sha = current_policy_sha
    elif reason == "SEMANTIC_USAGE_NOT_INVOKED":
        raise Refusal("SENTENCE-LOGIC-DORMANT", "semantic usage is dormant; semantic checker cannot run")
    elif reason is None:
        if not getattr(args, "allow_eligible", False):
            raise Refusal("SENTENCE-LOGIC-INVOKE", "eligible semantic invocation requires --allow-eligible")
        if binder._reader_profile_v2_is_dormant(project_root):
            raise Refusal("SENTENCE-LOGIC-DORMANT", "live project semantic usage is dormant")
        try:
            live = binder.policy.resolve_policy(
                project_root,
                wiki_root=Path(args.wiki_root) if getattr(args, "wiki_root", None) else None,
                workspace_root=Path(args.workspace_root) if getattr(args, "workspace_root", None) else None,
                harness_root=Path(args.harness_root) if getattr(args, "harness_root", None) else None,
            )
            live_provenance = binder._binding_provenance(project_root, live)
        except (binder.Unavailable, binder.policy.PolicyError, OSError, ValueError) as exc:
            raise Refusal("SENTENCE-LOGIC-ELIGIBILITY", f"live semantic policy could not be proven: {exc}") from exc
        live_register = live["register_provenance"]
        expected_policy = {
            "profile_path": live["profile_path"],
            "profile_sha256": live["profile_sha256"],
            "attestation_view_pin": live["attestation_view_pin"],
            "exemplar_view_pin": live["exemplar_view_pin"],
            "members": binder._member_view(live_register.get("exemplar_members")),
            "surface_member_keys": sorted(item["source_key"] for item in binder._member_view(live_register.get("surface_exemplar_members"))),
            "argument_member_keys": sorted(item["source_key"] for item in binder._member_view(live_register.get("argument_exemplar_members"))),
        }
        packet_policy = packet["policy"]
        if live_provenance != packet["binding_provenance"] or any(packet_policy.get(k) != v for k, v in expected_policy.items()):
            raise Refusal("SENTENCE-LOGIC-ELIGIBILITY", "packet policy, source members, pins, or provenance differ from live resolution")
        if not any(item.get("source_key") == YU_2011 and item.get("role") == "centroid" for item in expected_policy["members"]):
            raise Refusal("SENTENCE-LOGIC-ELIGIBILITY", "live centroid source is absent")
        graph_state = "eligible"
        policy_sha = live["profile_sha256"]
    else:
        raise Refusal("SENTENCE-LOGIC-STATE", f"unknown binder reason: {reason!r}")

    admitted: list[dict[str, Any]] = []
    if args.passages:
        admitted.extend(passages_from_json(Path(args.passages).resolve(strict=True), admitted_by=args.admitted_by))
    if args.admit_pdf:
        if not args.pages:
            raise Refusal("SENTENCE-LOGIC-PDF", "--admit-pdf requires --pages")
        try:
            pages = [int(item.strip()) for item in args.pages.split(",")]
        except ValueError as exc:
            raise Refusal("SENTENCE-LOGIC-PDF", "--pages must be comma-separated printed page numbers") from exc
        if not pages:
            raise Refusal("SENTENCE-LOGIC-PDF", "--admit-pdf requires --pages")
        source_key = args.pdf_source_key
        layer = "argument" if source_key == DENNETT else "surface"
        admitted.extend(
            _passages_from_pdf(Path(args.admit_pdf).resolve(strict=True), source_key, pages, layer,
                               extract_receipt=Path(args.extract_receipt).resolve(strict=True) if getattr(args, "extract_receipt", None) else None,
                               evidence_root=Path(args.evidence_root).resolve(strict=True) if getattr(args, "evidence_root", None) else None,
                               wiki_root=Path(args.wiki_root).resolve(strict=True) if getattr(args, "wiki_root", None) else None)
        )
    if not admitted:
        raise Refusal("SENTENCE-LOGIC-NO-PASSAGE", "semantic checker requires admitted passages")
    for row in admitted:
        row["id"] = row.pop("passage_id")
    if len({row["id"] for row in admitted}) != len(admitted):
        raise Refusal("SENTENCE-LOGIC-PASSAGE", "duplicate admitted passage IDs")
    sentences, paragraphs, pairs = inventory(text, scope)
    if not sentences:
        raise Refusal("SENTENCE-LOGIC-SCOPE", "bound scope has no prose sentences")
    by_id = {row["id"]: row for row in sentences}
    paragraph_positions = {row["id"]: index for index, row in enumerate(paragraphs)}
    for pair in pairs:
        pair["signals"] = _join_signals(by_id[pair["left_id"]]["text"], by_id[pair["right_id"]]["text"])
        position = paragraph_positions[by_id[pair["left_id"]]["paragraph_id"]]
        pair["context_paragraph_ids"] = [paragraphs[index]["id"] for index in range(max(0, position - 1), min(len(paragraphs), position + 2))]
    cadence_misses = sum(row["signals"]["join_cadence"] == "unearned_verdict" for row in pairs)
    backtrack_misses = sum(row["signals"]["needed_backtrack"] == "missing" for row in pairs)
    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    inputs = {key: getattr(args, key, None) for key in (
        "packet", "manuscript", "mode", "heading", "passages", "admitted_by", "admit_pdf",
        "pages", "pdf_source_key", "extract_receipt", "evidence_root", "project_root",
        "wiki_root", "workspace_root", "harness_root", "centroid_source", "invoke_only",
        "allow_eligible",
    )}
    for key in ("packet", "manuscript", "passages", "admit_pdf", "extract_receipt", "evidence_root", "project_root", "wiki_root", "workspace_root", "harness_root"):
        if inputs[key]:
            inputs[key] = str(Path(inputs[key]).resolve())
    receipt = {
        "schema_version": "2.0.0",
        "preparation_code_sha256": {
            name: _sha_bytes((Path(__file__).resolve().parent / name).read_bytes())
            for name in ("centroid_sentence_logic.py", "centroid_text.py", "centroid_source_evidence.py")
        },
        "pass": "centroid-check",
        "instrument": "centroid-check",
        "centroid_source": YU_2011,
        "status": "ready_for_role",
        "reason_code": None,
        "mode": args.mode,
        "packet_path": str(packet_path),
        "packet_sha256": _sha_bytes(packet_bytes),
        "manuscript_path": str(manuscript_path),
        "manuscript_sha256": manuscript_sha,
        "manuscript_bytes": len(manuscript_bytes),
        "scope_sha256": scope["sha256"],
        "scope": scope,
        "graph_state": graph_state,
        "binder_reason_code": reason,
        "policy_sha256": policy_sha,
        "admitted_passages": admitted,
        "sentences": sentences,
        "paragraphs": paragraphs,
        "pairs": pairs,
        "summary": {
            "not_run": len(pairs),
            "qualification": "incomplete",
            "all_short_stack": _all_short_stack([row["text"] for row in sentences]),
            "join_cadence_misses": cadence_misses,
            "needed_backtrack_missing": backtrack_misses,
        },
        "actor": "Generator" if args.mode in {"write", "revise"} else "Evaluator",
        "r_plane": "author only",
        "sk32": "CLOSED",
        "created_at": created,
        "inputs": inputs,
        "limitations": [
            "Binder state is eligibility, not a pair verdict.",
            "Pairs are not_run until a role reviews them; no scholarly CLEAN is minted.",
            "Mechanical signals are review cues, not proof of derivation or source support.",
        ],
    }
    receipt["naming"] = _check_sentence(receipt)
    if packet_path.read_bytes() != packet_bytes or manuscript_path.read_bytes() != manuscript_bytes:
        raise Refusal("SENTENCE-LOGIC-STALE", "packet or manuscript changed during preparation")
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
    parser.add_argument("--passages", help="Admitted passages JSON; each row names its admitting party (admitted_by) unless --admitted-by does")
    parser.add_argument("--admitted-by", help="The person who admitted the --passages rows that do not name one")
    parser.add_argument("--admit-pdf", help="Hash-bound PDF to read as admitted printed book pages")
    parser.add_argument(
        "--pages",
        help="Comma-separated printed book pages in the policy-pinned PDF and canonical extraction receipt.",
    )
    parser.add_argument("--pdf-source-key", default=YU_2011)
    parser.add_argument("--extract-receipt", help="Canonical source extraction receipt for PDF evidence")
    parser.add_argument("--evidence-root", help="Canonical source evidence root")
    parser.add_argument("--project-root")
    parser.add_argument("--wiki-root")
    parser.add_argument("--workspace-root")
    parser.add_argument("--harness-root")
    parser.add_argument("--out-dir")
    parser.add_argument("--shipment-id")
    parser.add_argument("--heading")
    parser.add_argument("--format", choices=("json", "review"), default="json")
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
        if args.format == "review":
            print(_review_view(receipt), end="")
        elif dest is not None:
            print(json.dumps({"status": receipt["status"], "schema_version": receipt["schema_version"],
                              "sentences": len(receipt["sentences"]), "pairs": len(receipt["pairs"]),
                              "written": receipt["written"]}, ensure_ascii=False))
        else:
            print(json.dumps(receipt, indent=2, ensure_ascii=False))
        return 0
    except (Refusal, SourceEvidenceError, DestinationRefused, OSError, json.JSONDecodeError, ValueError, UnicodeError) as exc:
        code = getattr(exc, "code", "SENTENCE-LOGIC-IO")
        detail = getattr(exc, "detail", str(exc))
        print(json.dumps({"status": "blocked", "reason_code": code, "detail": detail}, ensure_ascii=False))
        return 4


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="strict")
    raise SystemExit(main())
