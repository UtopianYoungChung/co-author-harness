#!/usr/bin/env python3
"""
Resolve Markdown include sentinels for packaging-time expansion.

Sentinel form:
    <!-- include: _snippets/output-profile.md -->

Bare `_snippets/...` paths resolve under `references/`; other paths resolve
first relative to the including file, then relative to the plugin root.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable, List, Set, Tuple


INCLUDE_RE = re.compile(r"<!--\s*include:\s*([^>]+?)\s*-->")


def plugin_root() -> Path:
    return Path(__file__).resolve().parent.parent


def iter_markdown_files(root: Path) -> Iterable[Path]:
    excluded = {".git", ".claude", "releases", "unpacked", "archives"}
    for path in root.rglob("*.md"):
        if any(part in excluded for part in path.parts):
            continue
        yield path


def include_candidates(root: Path, source: Path, include_ref: str) -> List[Path]:
    ref = include_ref.strip()
    candidates: List[Path] = []
    raw = Path(ref)
    if raw.is_absolute():
        candidates.append(raw)
    else:
        candidates.append(source.parent / raw)
        candidates.append(root / raw)
        if ref.startswith("_snippets/"):
            candidates.append(root / "references" / raw)
    return candidates


def resolve_include_path(root: Path, source: Path, include_ref: str) -> Path:
    for candidate in include_candidates(root, source, include_ref):
        if candidate.is_file():
            return candidate.resolve()
    tried = ", ".join(str(p) for p in include_candidates(root, source, include_ref))
    raise FileNotFoundError(f"{source}: include {include_ref!r} did not resolve; tried {tried}")


def resolve_includes_in_text(
    text: str,
    source: Path,
    root: Path | None = None,
    seen: Set[Path] | None = None,
) -> str:
    root = root or plugin_root()
    seen = seen or set()
    source = source.resolve()
    if source in seen:
        chain = " -> ".join(str(p) for p in [*seen, source])
        raise ValueError(f"recursive include detected: {chain}")

    def replace(match: re.Match[str]) -> str:
        include_path = resolve_include_path(root, source, match.group(1))
        include_text = include_path.read_text(encoding="utf-8")
        return resolve_includes_in_text(include_text, include_path, root, seen | {source})

    return INCLUDE_RE.sub(replace, text)


def check_all(root: Path) -> List[str]:
    errors: List[str] = []
    for path in iter_markdown_files(root):
        text = path.read_text(encoding="utf-8")
        if "<!-- include:" not in text:
            continue
        try:
            resolve_includes_in_text(text, path, root)
        except (FileNotFoundError, ValueError) as exc:
            errors.append(str(exc))
    return errors


def main(argv: List[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugin-root", type=Path, default=plugin_root())
    parser.add_argument("--file", type=Path, help="Resolve includes for one Markdown file")
    parser.add_argument("--check", action="store_true", help="Check that all include sentinels resolve")
    args = parser.parse_args(argv)

    root = args.plugin_root.resolve()
    if args.check:
        errors = check_all(root)
        if errors:
            for error in errors:
                print(f"[BLOCKER] {error}", file=sys.stderr)
            return 1
        print("OK include sentinels resolve")
        return 0

    if not args.file:
        parser.error("provide --file or --check")
    source = args.file if args.file.is_absolute() else root / args.file
    text = source.read_text(encoding="utf-8")
    print(resolve_includes_in_text(text, source, root), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
