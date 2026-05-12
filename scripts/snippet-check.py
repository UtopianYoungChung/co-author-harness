#!/usr/bin/env python3
"""
Static checks for snippet-based Markdown policy reuse.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, List

from resolve_includes import check_all, plugin_root


OUTPUT_PROFILE_SNIPPET = Path("references/_snippets/output-profile.md")
MAX_SNIPPET_LINES = 60


def iter_markdown_files(root: Path) -> Iterable[Path]:
    excluded = {".git", ".claude", "releases", "unpacked", "archives"}
    for path in root.rglob("*.md"):
        if any(part in excluded for part in path.parts):
            continue
        yield path


def main() -> int:
    root = plugin_root()
    errors: List[str] = []

    errors.extend(check_all(root))

    snippet_path = root / OUTPUT_PROFILE_SNIPPET
    if not snippet_path.is_file():
        errors.append(f"missing snippet {OUTPUT_PROFILE_SNIPPET}")
    else:
        snippet_text = snippet_path.read_text(encoding="utf-8").strip().replace("\r\n", "\n")
        line_count = len(snippet_text.splitlines())
        if line_count > MAX_SNIPPET_LINES:
            errors.append(
                f"{OUTPUT_PROFILE_SNIPPET}: {line_count} lines exceeds {MAX_SNIPPET_LINES}"
            )
        for path in iter_markdown_files(root):
            if path.resolve() == snippet_path.resolve():
                continue
            text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
            if snippet_text in text:
                rel = path.relative_to(root).as_posix()
                errors.append(
                    f"{rel}: duplicates {OUTPUT_PROFILE_SNIPPET}; use "
                    "<!-- include: _snippets/output-profile.md -->"
                )

    if errors:
        for error in errors:
            print(f"[BLOCKER] {error}", file=sys.stderr)
        return 1
    print("OK snippets resolve and output-profile block is not duplicated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
