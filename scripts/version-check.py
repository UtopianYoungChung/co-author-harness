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


def extract_readme_badge_version(plugin_root: Path) -> Optional[str]:
    """Capture the shields.io Version badge embedded near the top of README.md.

    Added at v0.15.0 — the v0.14.0 → v0.15.0 release prep caught a silent
    drift where the `## Version` line was bumped but the badge was not, and
    the GitHub README continued to render the stale badge. The badge is the
    most user-visible version surface and must match the manifest.
    """
    text = read_text(plugin_root / "README.md")
    match = re.search(
        r"!\[Version\]\(https://img\.shields\.io/badge/Version-(\d+\.\d+\.\d+)-",
        text,
    )
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
        # Format check (v0.10.1 follow-up): the Claude Code marketplace
        # loader's schema rejects bare "." as `Invalid input` for the
        # `source` field. Accepted forms surfaced empirically against
        # working examples are relative paths starting with "./" or
        # "../", and absolute git/HTTPS URLs. We do not enforce git URLs
        # here (the loader handles those); we only flag the bare-dot
        # class that has shipped twice (v0.10.0 RC marketplace skew and
        # v0.10.1 RC schema-format slip) so future RC gates catch it.
        if source in (".", ".."):
            self_versions.append(
                (
                    str(entry.get("name", "<unnamed>")).strip() or "<unnamed>",
                    f"<INVALID_SOURCE_FORMAT: bare '{source}' rejected by "
                    f"marketplace loader; use '{source}/' instead>",
                )
            )
            continue
        # Normalise to absolute path for comparison; treat "./" and
        # "../" as relative-to-marketplace.json's-directory by Claude
        # Code convention. We additionally try the parent-of-marketplace
        # interpretation (some marketplaces co-locate the registration
        # one directory up) so the check is robust to layout variation.
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


# Files where a version trailer is legitimate and expected: the manifests
# themselves, the changelog/release-notes archive, the historical-plans
# archive, the historical-reviews archive, the README's Version section,
# and `docs/historical/`. Every other prose surface should be version-free
# so that documentation does not silently drift relative to the manifest.
_VERSION_TRAILER_EXEMPT_PATHS = (
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    "CHANGELOG.md",
    "docs/release-notes/",
    "docs/superpowers/plans/",
    "docs/historical/",
    "reviews/",
    "scripts/fixtures/",
)

# Patterns for version-trailer prose: a line ending with a parenthetical
# version like "(v0.7.4)" or "v0.7.4 release notes", or an "Updated YYYY-MM-DD
# — vX.Y.Z" pattern in active-substrate prose. Calibrated to surface trailers
# the c7 sweep removed; tolerant of inline version mentions inside code blocks
# or links.
_VERSION_TRAILER_PATTERNS = (
    re.compile(r"^\*Last updated\.\s+\d{4}-\d{2}-\d{2}\s+[—-]\s+v\d+\.\d+\.\d+", re.M),
    re.compile(r"^\*Package reference,\s+v\d+\.\d+\.\d+", re.M),
)


def check_no_version_trailers_in_prose(plugin_root: Path) -> List[str]:
    """Return a list of BLOCKER strings for version trailers found in prose.

    Authored at v0.11.0 c8 to enforce the c7 trailer-strip invariant: every
    .md file outside the exempt set should be version-free at the file
    level. The check inspects only the file's tail (last 30 lines) where
    version trailers conventionally sit; whole-file scanning would surface
    too many false positives from inline version mentions in body prose.
    """
    findings: List[str] = []
    for md_path in plugin_root.rglob("*.md"):
        rel_str = str(md_path.relative_to(plugin_root)).replace("\\", "/")
        if any(rel_str.startswith(prefix) or rel_str == prefix.rstrip("/")
               for prefix in _VERSION_TRAILER_EXEMPT_PATHS):
            continue
        try:
            text = md_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        # Inspect only the file tail — version trailers live at the bottom.
        tail_lines = text.splitlines()[-30:]
        tail = "\n".join(tail_lines)
        for pattern in _VERSION_TRAILER_PATTERNS:
            if pattern.search(tail):
                findings.append(
                    f"version trailer detected in {rel_str}: pattern "
                    f"{pattern.pattern!r} matched in file tail"
                )
                break  # one finding per file
    return findings


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
    readme_badge_version = extract_readme_badge_version(plugin_root)
    changelog_version = extract_changelog_latest_version(plugin_root)
    marketplace_versions = extract_marketplace_self_referencing_versions(plugin_root)

    if readme_version is None:
        blockers.append("README latest version entry not found under '## Version'")
    elif readme_version != manifest_version:
        blockers.append(
            f"README latest version ({readme_version}) != manifest version ({manifest_version})"
        )

    if readme_badge_version is None:
        blockers.append("README shields.io Version badge not found near top of README.md")
    elif readme_badge_version != manifest_version:
        blockers.append(
            f"README badge version ({readme_badge_version}) != manifest version ({manifest_version})"
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

    # v0.11.0 c8: enforce the c7 trailer-strip invariant on active prose.
    trailer_findings = check_no_version_trailers_in_prose(plugin_root)
    blockers.extend(trailer_findings)

    print("VERSION CONSISTENCY CHECK")
    print(f"- Plugin root: {plugin_root}")
    print(f"- Manifest version: {manifest_version}")
    print(f"- README latest version: {readme_version or '<missing>'}")
    print(f"- README badge version:  {readme_badge_version or '<missing>'}")
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

