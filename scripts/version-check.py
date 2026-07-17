#!/usr/bin/env python3
"""
co-author-harness — version-check.py

THE MANIFEST IS THE SOLE AUTHORITY FOR THE CURRENT VERSION.

`.claude-plugin/plugin.json` owns it. Everything else either mirrors it
mechanically (and is gated) or must not state it at all.

  HARD GATE   .claude-plugin/marketplace.json — self-referencing plugins[]
              entries must equal the manifest. Both files ship inside the
              .plugin ZIP and the loader rejects the install when they
              disagree: v0.10.0 RC shipped marketplace.json "0.9.0" against a
              manifest bumped to "0.10.0". This is mechanical parity between
              two manifests, not prose mirroring it.

  REFUSED     README.md asserting a version — a shields.io badge or a
              standalone "## Version `X.Y.Z`" literal. This file used to
              REQUIRE both, which put it in direct contradiction with
              AGENTS.md ("`.claude-plugin/plugin.json` is the single source of
              truth ... No prose document in this tree asserts a version
              number; consult the manifest"). The contradiction was invisible
              because the checker enforced the losing side. Duplicated
              authority drifts, and the drift is only visible to whoever reads
              the rendered page. The README points at the manifest instead.

  PERMITTED   CHANGELOG.md / docs/release-notes/ release identifiers. A
              heading like "## v0.29.0 — 2026-07-14" is a HISTORICAL RECORD of
              what shipped, not a claim about the current version. Deleting
              release history to satisfy a rule about current-version
              authority would be a category error. These paths were already
              exempt from the trailer-strip invariant below; that exemption
              encoded the right distinction and is now stated outright.

  VALIDATED   CHANGELOG structure and release consistency — well-formed
              headings, unique release identifiers, descending order. Not
              authoritative for the current version: a changelog that lags the
              manifest is a documentation gap (WARN), not a release blocker,
              because treating it as a blocker makes it a competing authority.
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


def find_readme_version_assertions(plugin_root: Path) -> List[str]:
    """Return BLOCKERs for README surfaces that ASSERT a current version.

    Inverted at 0.29.1. This function used to be two extractors that REQUIRED
    a shields.io badge and a "## Version `X.Y.Z`" literal and blocked when
    they were absent or stale -- i.e. it mandated exactly the duplicated
    authority AGENTS.md forbids, and the v0.15.0 badge-drift incident it was
    written for is the proof: the badge and the literal drifted apart because
    two hand-maintained copies of one fact always eventually disagree. The
    remedy is not a third copy to check the other two; it is one copy.

    A README may freely LINK to `.claude-plugin/plugin.json`, and may mention
    versions in historical narrative ("in v0.15.0 we ..."). What it may not do
    is state THE CURRENT VERSION as a bare fact.
    """
    findings: List[str] = []
    text = read_text(plugin_root / "README.md")

    badge = re.search(
        r"!\[Version\]\(https://img\.shields\.io/badge/Version-(\d+\.\d+\.\d+)-", text)
    if badge:
        findings.append(
            f"README shields.io badge asserts version {badge.group(1)}: the manifest "
            "is the sole current-version authority; link to "
            ".claude-plugin/plugin.json instead of mirroring it")

    literal = re.search(r"##\s+Version\s+`(\d+\.\d+\.\d+)`", text, re.S)
    if literal:
        findings.append(
            f"README '## Version' section asserts version {literal.group(1)}: the "
            "manifest is the sole current-version authority; point readers at "
            ".claude-plugin/plugin.json instead of mirroring it")
    return findings


def extract_changelog_releases(plugin_root: Path) -> List[Tuple[str, str]]:
    """Return [(version, rest_of_heading), ...] in document order.

    `(unreleased)` headings are skipped for RELEASE purposes: the
    stage-by-stage accumulation pattern appends `## v0.10.0 (unreleased)`
    long before the RC gate bumps the manifest.
    """
    text = read_text(plugin_root / "CHANGELOG.md")
    out: List[Tuple[str, str]] = []
    # `{2,3}` captures HOTFIX identifiers whole. A `\d+\.\d+\.\d+` pattern
    # captures "0.7.4" out of "v0.7.4.1" and then reports a duplicate against
    # the real "v0.7.4" -- a collision that exists only in the regex. Found by
    # running this checker against the repository's own CHANGELOG, which
    # legitimately records both v0.7.4 and its v0.7.4.1 hotfix. Acting on that
    # false positive would have meant deleting a real release record.
    for match in re.finditer(r"^##\s+v(\d+(?:\.\d+){1,3})([^\n]*)$", text, re.M):
        if "(unreleased)" in match.group(2).lower():
            continue
        out.append((match.group(1), match.group(2)))
    return out


def _semver(v: str) -> Tuple[int, ...]:
    """Sort key tolerant of 2-4 component identifiers.

    Zero-padded to 4 so that v0.7.4 -> (0,7,4,0) sorts BELOW its v0.7.4.1
    hotfix -> (0,7,4,1), which is the order a newest-first changelog uses.
    """
    parts = tuple(int(p) for p in v.split("."))
    return parts + (0,) * (4 - len(parts))


def check_changelog_structure(releases: List[Tuple[str, str]]) -> List[str]:
    """Structure and release consistency -- NOT current-version authority.

    Validated: at least one release heading exists; identifiers are unique; and
    they descend. Not validated: whether the top entry equals the manifest --
    that would make the changelog a second authority, which is the defect being
    removed. A lagging changelog is a documentation gap (WARN in main()).
    """
    findings: List[str] = []
    if not releases:
        findings.append("CHANGELOG has no release heading (expected '## vX.Y.Z ...')")
        return findings

    seen: dict[str, int] = {}
    for version, _rest in releases:
        seen[version] = seen.get(version, 0) + 1
    for version, count in seen.items():
        if count > 1:
            findings.append(
                f"CHANGELOG duplicate release heading for v{version} ({count} "
                "occurrences): a release identifier names one release")

    ordered = [v for v, _ in releases]
    if ordered != sorted(ordered, key=_semver, reverse=True):
        findings.append(
            "CHANGELOG release headings are out of order: expected newest first, "
            f"got {ordered[:4]}")
    return findings


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

    # README must not assert a current version (AGENTS.md authority rule).
    blockers.extend(find_readme_version_assertions(plugin_root))

    # CHANGELOG: structure + release consistency; never the current-version authority.
    releases = extract_changelog_releases(plugin_root)
    changelog_version = releases[0][0] if releases else None
    blockers.extend(check_changelog_structure(releases))
    if changelog_version is not None and changelog_version != manifest_version:
        warnings.append(
            f"CHANGELOG newest release (v{changelog_version}) is not the manifest "
            f"version ({manifest_version}): expected when a bump has not yet been "
            "written up. The manifest is authoritative; this is a documentation "
            "gap, not a release blocker."
        )

    marketplace_versions = extract_marketplace_self_referencing_versions(plugin_root)

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
    print(f"- Manifest version (SOLE current-version authority): {manifest_version}")
    print(f"- README version assertions: {len(find_readme_version_assertions(plugin_root))} "
          f"(must be 0)")
    print(f"- CHANGELOG newest release (history, not authority): "
          f"{('v' + changelog_version) if changelog_version else '<none>'}")
    print(f"- CHANGELOG releases recorded: {len(releases)}")
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

