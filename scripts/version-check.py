#!/usr/bin/env python3
"""
co-author-harness — version-check.py

THE MANIFEST IS THE SOLE AUTHORITY FOR THE CURRENT VERSION.

`version.json` owns it (fallback: `.claude-plugin/plugin.json`). Everything else either mirrors it
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
              AGENTS.md ("`version.json` is the single source of
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

from marketplace_contract import (
    manifest_entries,
    manifest_entry_cardinality_error,
    root_source_error,
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def manifest_path(plugin_root: Path) -> Path:
    """General version.json is current-version authority.

    `.claude-plugin/plugin.json` remains a fallback so older fixtures still
    resolve. Live trees should not restore the Claude pack just to read a version.
    """
    general = plugin_root / "version.json"
    if general.exists():
        return general
    return plugin_root / ".claude-plugin" / "plugin.json"


def extract_manifest_version(plugin_root: Path) -> str:
    manifest = json.loads(read_text(manifest_path(plugin_root)))
    version = str(manifest.get("version", "")).strip()
    if not version:
        raise ValueError("manifest version is empty")
    return version


def extract_manifest_license(plugin_root: Path) -> str:
    manifest = json.loads(read_text(manifest_path(plugin_root)))
    license_id = str(manifest.get("license", "")).strip()
    if not license_id:
        raise ValueError("manifest license is empty")
    return license_id


def find_retired_host_manifests(plugin_root: Path) -> List[str]:
    """Refuse unmanaged host manifests that duplicate package authority."""
    cursor_manifest = plugin_root / ".cursor-plugin" / "plugin.json"
    if cursor_manifest.exists():
        return [
            ".cursor-plugin/plugin.json is a retired unmanaged host manifest; "
            "Cursor uses the source checkout directly, and package identity/version "
            "must come only from version.json"
        ]
    return []


def find_readme_version_assertions(plugin_root: Path) -> List[str]:
    """Return BLOCKERs for README surfaces that ASSERT a current version.

    Inverted at 0.29.1. This function used to be two extractors that REQUIRED
    a shields.io badge and a "## Version `X.Y.Z`" literal and blocked when
    they were absent or stale -- i.e. it mandated exactly the duplicated
    authority AGENTS.md forbids, and the v0.15.0 badge-drift incident it was
    written for is the proof: the badge and the literal drifted apart because
    two hand-maintained copies of one fact always eventually disagree. The
    remedy is not a third copy to check the other two; it is one copy.

    A README may freely LINK to `version.json`, and may mention
    versions in historical narrative ("in v0.15.0 we ..."). What it may not do
    is state THE CURRENT VERSION as a bare fact.

    Matched by the SHAPE of the claim, not by a list of spellings. The first cut
    enumerated exactly two -- a case-sensitive `![Version](...Version-X.Y.Z-)`
    badge and a backticked ``## Version `X.Y.Z` `` -- so a lowercase
    `![version]` badge, a `Release`-labelled badge, `## Current version` over a
    bare literal, and `**Version:** 0.29.1` all asserted the current version and
    all passed. That gate refused a FORMAT; this one refuses a CLAIM. The
    failure mode is the same one this round keeps finding: a rule that only
    catches the wordings someone already thought of.
    """
    findings: List[str] = []
    text = read_text(plugin_root / "README.md")
    # Release HISTORY is not a current-version claim -- `## v0.29.0 — 2026-07-14`
    # records what shipped. A version-with-a-date is history, which this policy
    # exists to preserve, so it is removed before scanning for claims.
    scanned = _HISTORY_LINE.sub("", text)
    for pattern, template in _README_ASSERTION_PATTERNS:
        for m in pattern.finditer(scanned):
            findings.append("README " + template.format(v=m.group("v")))
    return findings


_SEMVER = r"\d+\.\d+\.\d+(?:\.\d+)?"

_README_ASSERTION_PATTERNS = (
    # any shields.io badge whose value is a version literal, whatever its label,
    # with or without a `v` prefix on the VALUE (`Version-v0.29.1-`). The label
    # is `[A-Za-z0-9._%+-]*?` and `v?` sits on the value, so `Version-v0.29.1-`
    # no longer parses as label "Version-v" with no version.
    (re.compile(r"!\[[^\]]*\]\(\s*https://img\.shields\.io/badge/"
                r"[A-Za-z0-9._%+-]*?-v?(?P<v>" + _SEMVER + r")-", re.I),
     "shields.io badge asserts version {v}: the manifest is the sole "
     "current-version authority; link to version.json "
     "(e.g. Version-manifest) instead of mirroring it"),
    # a version-ish heading followed by a bare / backticked / bolded literal
    (re.compile(r"^#{1,6}[ \t]+(?:current[ \t]+)?version\b[^\n]*\n+[ \t]*"
                r"[`*_]{0,2}v?(?P<v>" + _SEMVER + r")[`*_]{0,2}[ \t]*$", re.I | re.M),
     "version heading asserts version {v}: point readers at "
     "version.json instead of mirroring it; the section may keep "
     "its release-history table"),
    # an inline `Version: X.Y.Z` / `**Version:** X.Y.Z` claim. The colon may sit
    # INSIDE the emphasis markers (`**Version:**`) or outside them
    # (`**Version**:`) -- both are the same claim, and matching only one spelling
    # is the very mistake this pattern table exists to stop making.
    (re.compile(r"^[ \t]*[`*_]{0,2}(?:current[ \t]+)?version[ \t]*:?[`*_]{0,2}[ \t]*:?[ \t]*"
                r"[`*_]{0,2}v?(?P<v>" + _SEMVER + r")[`*_]{0,2}[ \t]*$", re.I | re.M),
     "asserts a current version inline ({v}): point readers at "
     "version.json instead of mirroring it"),
    # ORDINARY PROSE. The patterns above refuse headings, badges and
    # `Key: value` lines -- the SHAPES someone thought of -- while "The current
    # version is 0.29.1." walked straight through asserting exactly the same
    # fact. A claim is a claim whatever grammar carries it, so this matches the
    # CLAIM: a present-tense copula binding a version-ish noun to a literal.
    #
    # Deliberately narrow on the verb ("is"/"are"/"ships"/"ships with") and on
    # the subject ("current version", "plugin version", "version"), and it does
    # NOT fire on past-tense historical narrative ("in v0.15.0 the badge
    # drifted"), on a release-history table row, or on a heading with a date --
    # all of which this policy exists to preserve. A rule that cannot say yes is
    # not enforcing a distinction, it is just refusing.
    (re.compile(r"(?:^|[.;:!?]\s|\n)[^.\n]{0,60}?\b(?:current|plugin|package|latest)?"
                r"[ \t]*version\b[^.\n]{0,24}?\b(?:is|are|remains|stands\s+at)\b"
                r"[ \t]+[`*_]{0,2}v?(?P<v>" + _SEMVER + r")\b", re.I),
     "asserts a current version in prose ({v}): the manifest is the sole "
     "current-version authority; describe it as recorded in "
     "version.json rather than restating the number"),
    (re.compile(r"\b(?:ships|shipping|includes|bundles)\b[^.\n]{0,24}?\bversion\b"
                r"[ \t]+[`*_]{0,2}v?(?P<v>" + _SEMVER + r")\b", re.I),
     "asserts a current version in prose ({v}): the manifest is the sole "
     "current-version authority; do not restate the number"),
)

# `## v0.29.0 — 2026-07-14` is release HISTORY, not a current-version claim.
_HISTORY_LINE = re.compile(
    r"^#{1,6}[ \t]+v?" + _SEMVER + r"[ \t]*[—–-][ \t]*\d{4}-\d{2}-\d{2}[^\n]*$",
    re.M)

# A heading that LOOKS like a release but is not one. `extract_changelog_releases`
# silently skips anything outside the accepted shape, so `## v1.2.3.4.5` simply
# vanished: the remaining releases validated, and the checker reported a
# well-formed changelog while a malformed record sat in it. Silence on
# unparseable input is not tolerance, it is blindness -- the checker did not
# disagree with the file, it failed to see it.
_RELEASE_LIKE = re.compile(r"^##\s+v(?P<id>[0-9][0-9A-Za-z.\-+]*)(?P<rest>[^\n]*)$", re.M)
_RELEASE_WELL_FORMED = re.compile(r"^\d+(?:\.\d+){1,3}$")


def find_malformed_release_headings(plugin_root: Path) -> List[str]:
    text = read_text(plugin_root / "CHANGELOG.md")
    out: List[str] = []
    for m in _RELEASE_LIKE.finditer(text):
        if "(unreleased)" in m.group("rest").lower():
            continue
        if not _RELEASE_WELL_FORMED.match(m.group("id")):
            # Report the IDENTIFIER only, never the rest of the heading. Echoing
            # raw file content into a console message crashed this check with
            # UnicodeEncodeError the moment a malformed heading carried the em
            # dash every real heading here uses -- so the blocker for a
            # malformed changelog was itself unprintable. The identifier is
            # matched as ASCII, so it is always safe to echo.
            out.append(
                f"CHANGELOG malformed release heading '## v{m.group('id')}': a "
                "release identifier is 2-4 dot-separated integers (e.g. v0.29.1, "
                "v0.7.4.1). Silently skipping it would let a malformed release "
                "record pass as a well-formed changelog")
    return out


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


def extract_marketplace_self_referencing_metadata(
    plugin_root: Path,
) -> Optional[List[Tuple[str, str, str]]]:
    """Return [(plugin_name, version, license), ...] for the manifest entry.

    Identity is the manifest name, matching loader behaviour. Source syntax is
    validated separately so changing from a local path to the dual-loader URL
    form cannot silently remove the entry from parity enforcement.

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
    manifest = json.loads(read_text(manifest_path(plugin_root)))
    plugins = marketplace.get("plugins", [])
    if not isinstance(plugins, list):
        return []

    cardinality_error = manifest_entry_cardinality_error(plugins, manifest)
    if cardinality_error:
        return [(
            str(manifest.get("name", "")).strip() or "<unnamed>",
            f"<INVALID_SELF_ENTRY_COUNT: {cardinality_error}>",
            "<missing>",
        )]

    self_metadata: List[Tuple[str, str, str]] = []
    for entry in manifest_entries(plugins, manifest):
        source_error = root_source_error(entry)
        if source_error:
            self_metadata.append(
                (
                    str(entry.get("name", "<unnamed>")).strip() or "<unnamed>",
                    f"<INVALID_SOURCE_FORMAT: {source_error}>",
                    str(entry.get("license", "")).strip() or "<missing>",
                )
            )
            continue

        name = str(entry.get("name", "")).strip()
        version = str(entry.get("version", "")).strip()
        license_id = str(entry.get("license", "")).strip()
        if not name or not version or not license_id:
            # Self-referencing entry but missing identity metadata — flag with a
            # placeholder so main() can surface a useful BLOCKER.
            self_metadata.append((name or "<unnamed>", version or "<missing>",
                                  license_id or "<missing>"))
            continue
        self_metadata.append((name, version, license_id))

    return self_metadata


# Files where a version trailer is legitimate and expected: the manifests
# themselves, the changelog/release-notes archive, the historical-plans
# archive, the historical-reviews archive, the README's Version section,
# and `docs/historical/`. Every other prose surface should be version-free
# so that documentation does not silently drift relative to the manifest.
_VERSION_TRAILER_EXEMPT_PATHS = (
    "version.json",
    "plugin.json",
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
        manifest_license = extract_manifest_license(plugin_root)
    except Exception as exc:  # noqa: BLE001
        print(f"[BLOCKER] manifest version check failed: {exc}")
        return 1

    # README must not assert a current version (AGENTS.md authority rule).
    blockers.extend(find_readme_version_assertions(plugin_root))
    blockers.extend(find_retired_host_manifests(plugin_root))

    # CHANGELOG: structure + release consistency; never the current-version authority.
    blockers.extend(find_malformed_release_headings(plugin_root))
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

    # Root plugin.json is a generic host identity file, not a second authority.
    root_plugin = plugin_root / "plugin.json"
    if root_plugin.exists():
        try:
            root_manifest = json.loads(read_text(root_plugin))
            for field in ("name", "version", "license"):
                left = str(root_manifest.get(field, "")).strip()
                right = str(json.loads(read_text(plugin_root / "version.json")).get(field, "")).strip() if (plugin_root / "version.json").exists() else {
                    "version": manifest_version,
                    "license": manifest_license,
                    "name": "",
                }.get(field, "")
                if field == "version":
                    right = manifest_version
                elif field == "license":
                    right = manifest_license
                elif field == "name":
                    right = str(json.loads(read_text(manifest_path(plugin_root))).get("name", "")).strip()
                if left and right and left != right:
                    blockers.append(
                        f"plugin.json {field} ({left}) != version.json {field} ({right})"
                    )
        except Exception as exc:  # noqa: BLE001
            blockers.append(f"plugin.json identity check failed: {exc}")

    marketplace_metadata = extract_marketplace_self_referencing_metadata(plugin_root)

    if marketplace_metadata is None:
        # marketplace.json is absent — silent skip per docstring contract.
        marketplace_summary = "<no marketplace.json>"
    elif not marketplace_metadata:
        # marketplace.json present but no self-referencing entries.
        marketplace_summary = "<no self-referencing entries>"
    else:
        marketplace_summary = ", ".join(
            f"{name}={version}/{license_id}"
            for name, version, license_id in marketplace_metadata
        )
        for name, version, license_id in marketplace_metadata:
            if version != manifest_version:
                blockers.append(
                    f"marketplace.json plugin '{name}' version ({version}) "
                    f"!= manifest version ({manifest_version})"
                )
            if license_id != manifest_license:
                blockers.append(
                    f"marketplace.json plugin '{name}' license ({license_id}) "
                    f"!= manifest license ({manifest_license})"
                )

    # v0.11.0 c8: enforce the c7 trailer-strip invariant on active prose.
    trailer_findings = check_no_version_trailers_in_prose(plugin_root)
    blockers.extend(trailer_findings)

    print("VERSION CONSISTENCY CHECK")
    print(f"- Plugin root: {plugin_root}")
    print(f"- Manifest version (SOLE current-version authority): {manifest_version}")
    print(f"- Manifest license: {manifest_license}")
    print(f"- README version assertions: {len(find_readme_version_assertions(plugin_root))} "
          f"(must be 0)")
    print(f"- Retired host manifests present: {len(find_retired_host_manifests(plugin_root))} "
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
