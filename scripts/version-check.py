#!/usr/bin/env python3
"""
co-author-harness — version-check.py

Checks that the current release version is synchronized across:
- .claude-plugin/plugin.json
- README.md (latest entry in "## Version")
- CHANGELOG.md (top release heading)
- .claude-plugin/marketplace.json (self-referencing plugins[] entries with
  source == "."; closes the v0.10.0 RC slip in which marketplace.json carried
  a stale "0.9.0" entry while plugin.json had been bumped to "0.10.0",
  producing a loader-rejected disagreement when the plugin was packaged via
  the .plugin ZIP route.)
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
    """Return the version of the most recent *released* CHANGELOG entry.

    Skips headings tagged as `(unreleased)` so that the in-flight stage-by-stage
    accumulation pattern declared by the snowball-implementation-strategy
    §8.2 does not collide with the strategy §8.4 invariant that the manifest
    version is bumped only at the RC gate. Without this filter, every stage
    close from S1 onward would surface a spurious BLOCKER as soon as the
    `## v0.10.0 (unreleased)` heading is appended.
    """
    text = read_text(plugin_root / "CHANGELOG.md")
    for match in re.finditer(r"^##\s+v(\d+\.\d+\.\d+)([^\n]*)$", text, re.M):
        version, rest = match.group(1), match.group(2)
        if "(unreleased)" in rest.lower():
            continue
        return version
    return None


def extract_marketplace_self_referencing_versions(
    plugin_root: Path,
) -> Optional[List[Tuple[str, str]]]:
    """Return [(plugin_name, version), ...] for marketplace.json entries
    whose source resolves to the same plugin root (source == "." or "./",
    or an absolute/relative path that resolves to plugin_root).

    Returns None when marketplace.json does not exist — the file is
    optional infrastructure (not every plugin ships with a co-located
    marketplace), so its absence is silent rather than a BLOCKER.

    Returns [] when marketplace.json exists but has no self-referencing
    plugin entries — the marketplace registers other plugins by path but
    not this one; nothing for version-check.py to enforce.

    The check exists because v0.10.0 RC shipped with marketplace.json
    line 13 reading "version": "0.9.0" while plugin.json had been bumped
    to "0.10.0". The .plugin ZIP carries both files; loader rejected the
    install on the disagreement. Closing the gap at the validator level
    prevents recurrence.
    """
    marketplace_path = plugin_root / ".claude-plugin" / "marketplace.json"
    if not marketplace_path.exists():
        return None

    marketplace = json.loads(read_text(marketplace_path))
    plugins = marketplace.get("plugins", [])
    if not isinstance(plugins, list):
        return []

    self_versions: List[Tuple[str, str]] = []
    for entry in plugins:
        if not isinstance(entry, dict):
            continue
        source = str(entry.get("source", "")).strip()
        if not source:
            continue
        # Normalise to absolute path for comparison; treat "." / "./" as
        # the marketplace.json's directory, which is plugin_root/.claude-plugin.
        # The convention is that source is relative to marketplace.json's
        # location, so source="." in plugin_root/.claude-plugin/marketplace.json
        # resolves to plugin_root/.claude-plugin — but the harness convention
        # (verified against the v0.10.0 marketplace.json) treats source="."
        # as the plugin root one level up. We honour both interpretations:
        # if either resolution lands on plugin_root, count the entry as
        # self-referencing.
        candidates = [
            (marketplace_path.parent / source).resolve(),  # ./ relative to marketplace.json
            (marketplace_path.parent.parent / source).resolve(),  # ./ relative to plugin root
        ]
        if plugin_root.resolve() not in candidates:
            continue

        name = str(entry.get("name", "")).strip()
        version = str(entry.get("version", "")).strip()
        if not name or not version:
            # Self-referencing entry but missing name/version — flag with a
            # placeholder so main() can surface a useful BLOCKER.
            self_versions.append((name or "<unnamed>", version or "<missing>"))
            continue
        self_versions.append((name, version))

    return self_versions


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
    marketplace_versions = extract_marketplace_self_referencing_versions(plugin_root)

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

    if marketplace_versions is None:
        # marketplace.json is absent — silent skip per docstring contract.
        marketplace_summary = "<no marketplace.json>"
    elif not marketplace_versions:
        # marketplace.json present but no self-referencing entries.
        marketplace_summary = "<no self-referencing entries>"
    else:
        marketplace_summary = ", ".join(
            f"{name}={version}" for name, version in marketplace_versions
        )
        for name, version in marketplace_versions:
            if version != manifest_version:
                blockers.append(
                    f"marketplace.json plugin '{name}' version ({version}) "
                    f"!= manifest version ({manifest_version})"
                )

    print("VERSION CONSISTENCY CHECK")
    print(f"- Plugin root: {plugin_root}")
    print(f"- Manifest version: {manifest_version}")
    print(f"- README latest version: {readme_version or '<missing>'}")
    print(f"- CHANGELOG top version: {changelog_version or '<missing>'}")
    print(f"- Marketplace self-referencing entries: {marketplace_summary}")
    print(f"- Blockers: {len(blockers)}")
    print(f"- Warnings: {len(warnings)}")

    for item in blockers:
        print(f"[BLOCKER] {item}")
    for item in warnings:
        print(f"[WARN] {item}")

    return 1 if blockers else 0


if __name__ == "__main__":
    sys.exit(main())

