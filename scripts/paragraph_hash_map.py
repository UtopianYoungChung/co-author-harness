#!/usr/bin/env python3
# paragraph_hash_map.py — v0.8.0 P2.1c
#
# Computes a stable paragraph_id → SHA-256 map from the consumer project's
# manuscript Markdown file (default manuscript/main.md), per
# proposals/v0.7.5_phase3_refinement_loop_proposal.md §P-10 and
# proposals/v0.8.0_upgrade_architecture.md §3.2 P2.1 / §9.2 P2.1c.
#
# Contract (this script only — journal append is scheduled with P-2 / P-10
# integration, not co-landed at P2.1c):
#
#   * paragraph_id — zero-based document order, fixed width four digits:
#       p-0000, p-0001, …
#   * Paragraph boundaries — split on one-or-more blank lines (two or more
#     newline characters in sequence after CRLF→LF normalization). Sequences
#     of only horizontal whitespace between newlines still start a new
#     paragraph (Markdown-tolerant).
#   * Canonical bytes for hashing — UTF-8 encoding of the canonical string:
#       (1) CRLF and lone CR normalized to LF on the full file before split.
#       (2) Each paragraph block: outer strip; split on LF; each line rstrip;
#           lines rejoined with LF (no trailing LF after the last line unless
#           the paragraph was empty after strip — empty blocks are dropped).
#   * paragraph_hash_map values — lowercase hex SHA-256 of canonical UTF-8.
#   * manuscript_sha256 — SHA-256 of the manuscript file read as raw bytes
#     (before newline normalization); audit trail alongside paragraph hashes.
#
# JSON stdout uses sort_keys=True and separators=(",", ":") for deterministic
# byte output across runs and Python versions.
#
# Usage:
#   python3 paragraph_hash_map.py --project-root /path/to/paper
#   python3 paragraph_hash_map.py --project-root /path --manuscript drafts/body.md
#
# Exit: 0 ok, 1 usage, 2 I/O or missing manuscript

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

_PARA_SPLIT = re.compile(r"\n(?:[ \t]*\n)+")


def _die(msg: str, code: int) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def normalize_crlf(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def split_paragraphs(normalized_text: str) -> list[str]:
    chunks = _PARA_SPLIT.split(normalized_text)
    return [c for c in chunks if c.strip() != ""]


def canonical_paragraph(block: str) -> str:
    block = block.strip()
    if not block:
        return ""
    lines = block.split("\n")
    return "\n".join(line.rstrip() for line in lines)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def manuscript_relpath(manuscript_path: Path, project_root: Path) -> str:
    """Stable display path: posix, relative to project root when under it."""
    m = manuscript_path.resolve()
    r = project_root.resolve()
    try:
        return m.relative_to(r).as_posix()
    except ValueError:
        return m.as_posix()


def build_map(manuscript_path: Path, project_root: Path) -> dict[str, object]:
    raw = manuscript_path.read_bytes()
    text = raw.decode("utf-8", errors="strict")
    normalized = normalize_crlf(text)
    paragraphs = split_paragraphs(normalized)
    pmap: dict[str, str] = {}
    for i, raw_block in enumerate(paragraphs):
        canon = canonical_paragraph(raw_block)
        pid = f"p-{i:04d}"
        pmap[pid] = sha256_hex(canon.encode("utf-8"))
    return {
        "manuscript_path": manuscript_relpath(manuscript_path, project_root),
        "manuscript_sha256": sha256_hex(raw),
        "paragraph_count": len(pmap),
        "paragraph_hash_map": pmap,
    }


def emit_json(obj: dict[str, object]) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Compute paragraph_id → SHA-256 map for manuscript/main.md (P-10 / P2.1c)."
    )
    ap.add_argument(
        "--project-root",
        required=True,
        help="Consumer project root (directory containing manuscript/).",
    )
    ap.add_argument(
        "--manuscript",
        default="manuscript/main.md",
        help="Path relative to project root (default: manuscript/main.md).",
    )
    args = ap.parse_args(argv)
    root = Path(args.project_root).resolve()
    if not root.is_dir():
        _die(f"ERROR: --project-root is not a directory: {root}", 2)
    ms_path = (root / args.manuscript).resolve()
    if not ms_path.is_file():
        _die(f"ERROR: manuscript not found: {ms_path}", 2)
    try:
        payload = build_map(ms_path, root)
    except OSError as e:
        _die(f"ERROR: read failed: {e}", 2)
    except UnicodeDecodeError as e:
        _die(f"ERROR: manuscript must be UTF-8: {e}", 2)
    sys.stdout.write(emit_json(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
