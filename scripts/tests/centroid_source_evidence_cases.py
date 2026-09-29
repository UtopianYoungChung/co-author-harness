#!/usr/bin/env python3
"""Focused cases imported by the registered centroid sentence-logic suite."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import centroid_source_evidence as cse
from centroid_source_evidence import (
    DENNETT, YU_2011, SourceEvidenceError, passages_from_json,
    passages_from_pdf, validate_passage,
)
from source_extract import main as source_extract_main
from source_extract import qualified_pdf_extractor


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _synthetic_pdf(path: Path) -> None:
    # Same one-page wrong-source input as the 2026-09-29 assessment probe.
    stream = (b"BT /F1 12 Tf 50 730 Td (SYNTHETIC TEST DOCUMENT - not Yu or Dennett) "
              b"Tj 0 -30 Td (Synthetic prose for source identity testing.) Tj "
              b"0 -650 Td (3) Tj ET")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    body = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(body))
        body.extend(str(number).encode() + b" 0 obj\n" + obj + b"\nendobj\n")
    xref = len(body)
    body.extend(b"xref\n0 6\n0000000000 65535 f \n")
    for offset in offsets[1:]:
        body.extend(f"{offset:010d} 00000 n \n".encode())
    body.extend(b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n" + str(xref).encode() + b"\n%%EOF\n")
    path.write_bytes(body)


def _refuse(code: str, action) -> None:
    try:
        action()
    except SourceEvidenceError as exc:
        assert exc.code == code, (exc.code, exc.detail)
    else:
        raise AssertionError(f"expected {code}")


def _extract(root: Path, source: Path, manifest: Path, key: str, suffix: str) -> Path:
    out = root / suffix
    out.mkdir()
    receipt = out / "receipt.json"
    args = [
        "--source", str(source), "--text-out", str(out / "normalized.txt"),
        "--receipt-out", str(receipt), "--project-root", str(root),
        "--project-manifest", str(manifest), "--source-key", key,
        "--raw-out", str(out / "raw.txt"), "--page-map-out", str(out / "page-map.json"),
        "--manifest-out", str(out / "publication-manifest.json"),
        "--commit-marker-out", str(out / "publication-marker.json"),
    ]
    with contextlib.redirect_stdout(io.StringIO()) as stdout, contextlib.redirect_stderr(io.StringIO()) as stderr:
        rc = source_extract_main(args)
    assert rc == 0, stdout.getvalue() + stderr.getvalue()
    return receipt


def run_cases(tmp: Path | None = None) -> None:
    human = {"source_key": YU_2011, "locator": "book pp. 3, 7 and 10", "quote": "Exact human excerpt.", "admitted_by": "Author"}
    first = validate_passage(human)
    assert first["admission_kind"] == "human_attested"
    assert first["passage_id"] == validate_passage(human)["passage_id"]
    assert validate_passage(dict(human, locator="Page 3"))["locator"] == "Page 3"
    assert validate_passage(dict(human, locator="Pages 3 and 7"))["locator"] == "Pages 3 and 7"
    for locator in ("printed pp. 3-99", "printed pp. 3, 99", "book pp. 3\u201399", "p. 3 and 99"):
        _refuse("SENTENCE-LOGIC-SCOPE", lambda loc=locator: validate_passage(dict(human, locator=loc)))
    for locator in ("3", "p. ", "p. 3-", "p. 3,", "p. 3 and", "p. 3 and p. 4", "p. 7-3", "p. 3, 3"):
        _refuse("SENTENCE-LOGIC-SCOPE", lambda loc=locator: validate_passage(dict(human, locator=loc)))
    _refuse("SENTENCE-LOGIC-PASSAGE", lambda: validate_passage(dict(human, admitted_by="")))
    _refuse("SENTENCE-LOGIC-ROLE", lambda: validate_passage(dict(human, warrant_layer="argument")))
    assert validate_passage(dict(human, source_key=DENNETT, locator="p. 99"))["warrant_layer"] == "argument"
    assert cse._printed_page("Body text.\npage 7\n", 12) == 7
    assert cse._printed_page("CONTENTS\nBody text.\n7\n", 12) is None
    assert cse._printed_page("Body text.\niv\n", 12) is None
    assert cse._printed_page("3\nA chapter heading, not a footer.\n", 12) is None
    _refuse("SENTENCE-LOGIC-PDF", lambda: cse._printed_page("Body text.\n7\npage 8\n", 12))

    with tempfile.TemporaryDirectory(prefix="coauthor-centroid-source-cases-", dir=tmp) as td:
        root = Path(td).resolve()
        pdf = root / "synthetic-not-yu.pdf"
        _synthetic_pdf(pdf)
        manifest = root / "project-manifest.json"
        manifest.write_text(json.dumps({"identity": "centroid-source-cases", "admitted_sources": [
            {"path": pdf.name, "sha256": _sha(pdf)}
        ]}), encoding="utf-8")
        policy = root / "policy.json"
        policy.write_text(json.dumps({"domain_native_register": {"exemplar_members": [
            {"source_key": YU_2011, "pdf_sha256": _sha(pdf)}
        ]}}), encoding="utf-8")
        wrong_policy = root / "wrong-policy.json"
        wrong_policy.write_text(json.dumps({"domain_native_register": {"exemplar_members": [
            {"source_key": YU_2011, "pdf_sha256": "0" * 64}
        ]}}), encoding="utf-8")
        args = {"extract_receipt": None, "evidence_root": root, "wiki_root": root, "policy_path": policy}
        _refuse("SENTENCE-LOGIC-SOURCE", lambda: passages_from_pdf(
            pdf, YU_2011, [3], "surface", extract_receipt=None, evidence_root=root, wiki_root=root))
        _refuse("SENTENCE-LOGIC-SOURCE", lambda: passages_from_pdf(
            pdf, DENNETT, [3], "argument", extract_receipt=None, evidence_root=root, wiki_root=root))
        _refuse("SENTENCE-LOGIC-SOURCE", lambda: passages_from_pdf(
            pdf, YU_2011, [3], "surface", **dict(args, policy_path=wrong_policy)))
        tool, extractor_error = qualified_pdf_extractor()
        full_canonical = tool is not None
        if full_canonical:
            receipt = _extract(root, pdf, manifest, YU_2011, "yu")
            normalized = root / "yu" / "normalized.txt"
        else:
            # The host cannot publish a C2 receipt without a qualified
            # pdftotext. Exercise passage mapping with an injected, already
            # validated record; report this as a limited test, not C2 proof.
            receipt = root / "receipt-stub.json"
            receipt.write_text("{}", encoding="utf-8")
            normalized = root / "normalized-stub.txt"
            normalized.write_text("SYNTHETIC TEST DOCUMENT\n3\n", encoding="utf-8")
            validated_stub = {
                "value": {"source_key": YU_2011, "source": {"sha256": _sha(pdf)}},
                "source": pdf.resolve(), "normalized": normalized,
                "page_map": {"normalized_sha256": _sha(normalized), "pages": [{"page": 1, "normalized_start_utf8": 0,
                                         "normalized_end_utf8": len(normalized.read_bytes())}]},
            }
        args["extract_receipt"] = receipt
        if not full_canonical:
            _refuse("SENTENCE-LOGIC-EXTRACT", lambda: passages_from_pdf(pdf, YU_2011, [3], "surface", **args))
        with contextlib.nullcontext() if full_canonical else patch.object(cse, "validate_extract_receipt", return_value=validated_stub):
            out = passages_from_pdf(pdf, YU_2011, [3], "surface", **args)
            assert len(out) == 1 and out[0]["admission_kind"] == "canonical_extract"
            assert out[0]["page"] == 3 and out[0]["pdf_identity"] == 1
            assert "SYNTHETIC TEST DOCUMENT" in out[0]["quote"]
            assert out[0]["passage_id"] == passages_from_pdf(pdf, YU_2011, [3], "surface", **args)[0]["passage_id"]
            _refuse("SENTENCE-LOGIC-PDF", lambda: passages_from_pdf(pdf, YU_2011, [4], "surface", **args))
            _refuse("SENTENCE-LOGIC-PDF", lambda: passages_from_pdf(pdf, YU_2011, [3], "surface", **dict(args, extract_receipt=None)))
            if not full_canonical:
                with patch.object(cse, "validate_extract_receipt", return_value=dict(validated_stub, value={"source_key": DENNETT, "source": {"sha256": _sha(pdf)}})):
                    _refuse("SENTENCE-LOGIC-SOURCE", lambda: passages_from_pdf(pdf, YU_2011, [3], "surface", **args))
        if full_canonical:
            wrong_key_receipt = _extract(root, pdf, manifest, DENNETT, "wrong-key")
            _refuse("SENTENCE-LOGIC-SOURCE", lambda: passages_from_pdf(pdf, YU_2011, [3], "surface", **dict(args, extract_receipt=wrong_key_receipt)))
            original_normalized = normalized.read_bytes()
            normalized.write_bytes(original_normalized + b"stale")
            _refuse("SENTENCE-LOGIC-EXTRACT", lambda: passages_from_pdf(pdf, YU_2011, [3], "surface", **args))
            normalized.write_bytes(original_normalized)
        else:
            print(f"SKIP live C2 extract validation: {extractor_error}")
        # A distinct source byte change fails against the policy before receipt validation.
        pdf.write_bytes(pdf.read_bytes() + b"\n% changed\n")
        _refuse("SENTENCE-LOGIC-SOURCE", lambda: passages_from_pdf(pdf, YU_2011, [3], "surface", **args))
        if full_canonical:
            policy.write_text(json.dumps({"domain_native_register": {"exemplar_members": [
                {"source_key": YU_2011, "pdf_sha256": _sha(pdf)}
            ]}}), encoding="utf-8")
            _refuse("SENTENCE-LOGIC-EXTRACT", lambda: passages_from_pdf(pdf, YU_2011, [3], "surface", **args))
        passage_file = root / "human.json"
        passage_file.write_text(json.dumps([human]), encoding="utf-8")
        assert passages_from_json(passage_file)[0]["admission_kind"] == "human_attested"
        passage_file.write_text(json.dumps([human, None]), encoding="utf-8")
        _refuse("SENTENCE-LOGIC-PASSAGE", lambda: passages_from_json(passage_file))
        passage_file.write_text('[{"source_key":"' + YU_2011 + '","source_key":"' + YU_2011 + '"}]', encoding="utf-8")
        _refuse("SENTENCE-LOGIC-INPUT", lambda: passages_from_json(passage_file))
        passage_file.write_text('[{"source_key":"' + YU_2011 + '","locator":"Page 3","quote":"text","extra":NaN}]', encoding="utf-8")
        _refuse("SENTENCE-LOGIC-INPUT", lambda: passages_from_json(passage_file))
        policy.write_text('{"domain_native_register":{},"domain_native_register":{}}', encoding="utf-8")
        _refuse("SENTENCE-LOGIC-POLICY", lambda: passages_from_pdf(pdf, YU_2011, [3], "surface", **args))
