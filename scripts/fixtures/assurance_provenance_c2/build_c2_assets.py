#!/usr/bin/env python3
"""Regenerate the self-authored C2 PDF and exact expected extraction assets."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "miniature_source.tex"
PDF = HERE / "miniature.pdf"
RAW = HERE / "expected_pdftotext_raw.txt"
NORMALIZED = HERE / "expected_utf8_lf_v1.txt"
PAGE_MAP = HERE / "expected_page_span_map.json"
HASHES = HERE / "hashes.json"


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def utf8_offset(value: str, index: int) -> int:
    return len(value[:index].encode("utf-8"))


def occurrences(value: str, needle: str) -> list[dict[str, int | str]]:
    rows: list[dict[str, int | str]] = []
    start = 0
    occurrence = 1
    while True:
        at = value.find(needle, start)
        if at < 0:
            return rows
        end = at + len(needle)
        rows.append({
            "occurrence": occurrence,
            "start_utf8": utf8_offset(value, at),
            "end_utf8": utf8_offset(value, end),
            "text_sha256": digest_bytes(needle.encode("utf-8")),
        })
        occurrence += 1
        start = end


def main() -> int:
    pdflatex = shutil.which("pdflatex")
    pdftotext = shutil.which("pdftotext")
    if not pdflatex or not pdftotext:
        raise SystemExit("pdflatex and pdftotext are required to regenerate C2 assets")

    with tempfile.TemporaryDirectory(prefix="coauthor-c2-pdf-") as td:
        out = Path(td)
        env = dict(os.environ)
        env["SOURCE_DATE_EPOCH"] = "0"
        subprocess.run(
            [
                pdflatex,
                "-halt-on-error",
                "-interaction=batchmode",
                f"-output-directory={out}",
                str(SOURCE),
            ],
            cwd=HERE,
            env=env,
            check=True,
            capture_output=True,
        )
        built_pdf = out / "miniature_source.pdf"
        PDF.write_bytes(built_pdf.read_bytes())

        raw_path = out / "raw.txt"
        subprocess.run(
            [pdftotext, "-enc", "UTF-8", str(PDF), str(raw_path)],
            cwd=HERE,
            check=True,
            capture_output=True,
        )
        raw_bytes = raw_path.read_bytes()

    raw_text = raw_bytes.decode("utf-8")
    normalized_text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    RAW.write_bytes(raw_bytes)
    NORMALIZED.write_text(normalized_text, encoding="utf-8", newline="\n")

    page_texts = normalized_text.split("\f")
    if page_texts and not page_texts[-1]:
        page_texts.pop()
    pages: list[dict[str, int | str]] = []
    cursor = 0
    for number, page_text in enumerate(page_texts, 1):
        start = normalized_text.find(page_text, cursor)
        end = start + len(page_text)
        pages.append({
            "page": number,
            "normalized_start_utf8": utf8_offset(normalized_text, start),
            "normalized_end_utf8": utf8_offset(normalized_text, end),
            "text_sha256": digest_bytes(page_text.encode("utf-8")),
        })
        cursor = end + 1

    repeated = "Repeated locator sentence: evidence must remain at the recorded occurrence."
    cross_page_left = "deterministic evidence crosses the"
    cross_page_right = "page boundary without losing its locator."
    mapping = {
        "schema_version": "1.0.0",
        "normalization_version": "utf8-lf-v1",
        "offset_unit": "zero-based-end-exclusive-utf8-byte",
        "raw_sha256": digest_bytes(raw_bytes),
        "normalized_sha256": digest_bytes(normalized_text.encode("utf-8")),
        "pages": pages,
        "named_spans": {
            "repeated_locator": occurrences(normalized_text, repeated),
            "cross_page_left": occurrences(normalized_text, cross_page_left),
            "cross_page_right": occurrences(normalized_text, cross_page_right),
            "ligature_probe": occurrences(normalized_text, "efficient affinity office fixture"),
            "centroid_quote": occurrences(
                normalized_text,
                "replayable evidence must bind exact",
            ),
            "argument_quote": occurrences(
                normalized_text,
                "rationale records why a member is\nincluded or omitted",
            ),
        },
    }
    PAGE_MAP.write_text(
        json.dumps(mapping, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    tracked = [
        "PROVENANCE.md",
        "build_c2_assets.py",
        "expected_page_span_map.json",
        "expected_pdftotext_raw.txt",
        "expected_utf8_lf_v1.txt",
        "final.md",
        "miniature.pdf",
        "miniature_source.tex",
        "miniature_source.txt",
        "wiki/manifest.json",
        "wiki/policy.json",
        "wiki/wiki/sources/c2-argument.md",
        "wiki/wiki/sources/c2-centroid.md",
        "wiki/wiki/sources/c2-redirect.md",
    ]
    payload = {
        "schema_version": "1.0.0",
        "fixture_id": "assurance-provenance-c2",
        "files": [{"path": rel, "sha256": digest(HERE / rel)} for rel in tracked],
    }
    HASHES.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
