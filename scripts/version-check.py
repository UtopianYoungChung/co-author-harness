#!/usr/bin/env python3
"""
co-author-harness — version-check.py

Checks that the current release version is synchronized across:
- .claude-plugin/plugin.json
- README.md (latest entry in "## Version")
- CHANGELOG.md (top release heading)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_manifest_version(plugin_root: Path) -> str:
    manifest_path = plugin_root / ".claude-plugin" / "plugin.json"
    manifest = json.loads(read_text(manifest_path))
    version = str(manifest.get("version", "")).strip()
    if not version:
        raise ValueError("manifest version is empty")
    return version


def extract_readme_latest_version(plugin_root: Path) -> Optional[str]:
    text = read_text(plugin_root / "README.md")
    # Capture first backticked semantic version under the Version section.
    match = re.search(r"## Version\s+`(\d+\.\d+\.\d+)`", text, re.S)
    if match:
        return match.group(1)
    return None


def extract_changelog_latest_version(plugin_root: Path) -> Optional[str]:
    text = read_text(plugin_root / "CHANGELOG.md")
    match = re.search(r"^##\s+v(\d+\.\d+\.\d+)\b", text, re.M)
    if match:
        return match.group(1)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Check release version consistency.")
    parser.add_argument(
        "--plugin-root",
        default=None,
        help="Plugin root path (defaults to parent directory of this script).",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    plugin_root = Path(args.plugin_root).resolve() if args.plugin_root else script_dir.parent

    blockers: List[str] = []
    warnings: List[str] = []

    try:
        manifest_version = extract_manifest_version(plugin_root)
    except Exception as exc:  # noqa: BLE001
        print(f"[BLOCKER] manifest version check failed: {exc}")
        return 1

    readme_version = extract_readme_latest_version(plugin_root)
    changelog_version = extract_changelog_latest_version(plugin_root)

    if readme_version is None:
        blockers.append("README latest version entry not found under '## Version'")
    elif readme_version != manifest_version:
        blockers.append(
            f"README latest version ({readme_version}) != manifest version ({manifest_version})"
        )

    if changelog_version is None:
        blockers.append("CHANGELOG top release heading not found")
    elif changelog_version != manifest_version:
        blockers.append(
            f"CHANGELOG top version ({changelog_version}) != manifest version ({manifest_version})"
        )

    print("VERSION CONSISTENCY CHECK")
    print(f"- Plugin root: {plugin_root}")
    print(f"- Manifest version: {manifest_version}")
    print(f"- README latest version: {readme_version or '<missing>'}")
    print(f"- CHANGELOG top version: {changelog_version or '<missing>'}")
    print(f"- Blockers: {len(blockers)}")
    print(f"- Warnings: {len(warnings)}")

    for item in blockers:
        print(f"[BLOCKER] {item}")
    for item in warnings:
        print(f"[WARN] {item}")

    return 1 if blockers else 0


if __name__ == "__main__":
    sys.exit(main())

