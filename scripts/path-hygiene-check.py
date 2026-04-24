#!/usr/bin/env python3
"""
co-author-harness — path-hygiene-check.py

Blocks maintainer-local absolute paths from install-facing files.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable, List


BLOCKED_PATTERNS = [
    re.compile(r"C:\\Users\\young\\", re.I),
    re.compile(r"/Users/young/"),
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def iter_target_files(plugin_root: Path) -> Iterable[Path]:
    yield plugin_root / "README.md"
    yield plugin_root / "CHANGELOG.md"
    yield plugin_root / ".claude-plugin" / "plugin.json"

    for pattern in ("skills/*/SKILL.md", "agents/*.md", "scripts/*.py", "scripts/*.sh"):
        for path in sorted(plugin_root.glob(pattern)):
            if path.name == "path-hygiene-check.py":
                continue
            yield path


def main() -> int:
    parser = argparse.ArgumentParser(description="Check for forbidden local absolute paths.")
    parser.add_argument(
        "--plugin-root",
        default=None,
        help="Plugin root path (defaults to parent directory of this script).",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    plugin_root = Path(args.plugin_root).resolve() if args.plugin_root else script_dir.parent

    blockers: List[str] = []

    for path in iter_target_files(plugin_root):
        if not path.exists() or path.is_dir():
            continue
        text = read_text(path)
        for patt in BLOCKED_PATTERNS:
            if patt.search(text):
                blockers.append(f"{path}: matched forbidden path pattern '{patt.pattern}'")

    print("PATH HYGIENE CHECK")
    print(f"- Plugin root: {plugin_root}")
    print(f"- Blockers: {len(blockers)}")
    for item in blockers:
        print(f"[BLOCKER] {item}")

    return 1 if blockers else 0


if __name__ == "__main__":
    sys.exit(main())

