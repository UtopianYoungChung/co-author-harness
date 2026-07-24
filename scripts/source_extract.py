#!/usr/bin/env python3
"""Create canonical, hash-bound text extraction evidence for one source."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from destination_capability import DestinationRefused, assert_writable


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--text-out", type=Path, required=True)
    parser.add_argument("--receipt-out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        assert_writable(args.text_out.resolve(), purpose="canonical source extract")
        assert_writable(args.receipt_out.resolve(), purpose="source-extract receipt")
    except DestinationRefused as exc:
        print(f"[BLOCKER] {exc}", file=sys.stderr)
        return 4
    source = args.source.resolve(strict=True)
    args.text_out.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix.casefold() == ".pdf":
        tool = shutil.which("pdftotext")
        if tool is None:
            print("[BLOCKER] EXTRACTOR-UNAVAILABLE: pdftotext is required for PDF evidence", file=sys.stderr)
            return 4
        result = subprocess.run([tool, "-enc", "UTF-8", str(source), str(args.text_out)],
                                capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode != 0 or not args.text_out.is_file():
            print(f"[BLOCKER] EXTRACTOR-FAILED: {result.stderr.strip()}", file=sys.stderr)
            return 4
        method = "pdftotext"; tool_name = Path(tool).name
    else:
        try:
            text = source.read_text(encoding="utf-8", errors="strict")
        except (OSError, UnicodeError) as exc:
            print(f"[BLOCKER] EXTRACTOR-FAILED: {exc}", file=sys.stderr)
            return 4
        args.text_out.write_text(text, encoding="utf-8", newline="\n")
        method = "text-direct"; tool_name = "utf-8"
    receipt = {
        "schema_version": "1.0.0", "receipt_type": "canonical_source_extract",
        "source": {"path": str(source), "sha256": sha(source)},
        "extract": {"path": str(args.text_out.resolve()), "sha256": sha(args.text_out)},
        "extraction": {"method": method, "tool": tool_name, "canonical": True},
    }
    args.receipt_out.parent.mkdir(parents=True, exist_ok=True)
    args.receipt_out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
