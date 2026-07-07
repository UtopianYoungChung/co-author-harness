#!/usr/bin/env bash
# NOTE (2026-07-07): scripts/release-gate.sh Phase 1 is the CANONICAL packaging
# path (it builds the zip inline after the full check battery). This script is a
# convenience wrapper for ad-hoc builds only; if the two ever disagree, the gate wins.
# build-release-zip.sh — canonical packaging recipe for co-author-harness-claude
#
# Codifies the exclusion list that was tribal knowledge through v0.7.3:
#   * __pycache__ directories and .pyc files — most Claude-plugin loaders reject them
#   * .DS_Store — macOS Finder metadata, never load-bearing
#   * setup/ scratch dirs — reserved for author-side scaffolding, never shipped
#
# See handoff-§7.4 (v0.7.4 session handoff) for the history: the v0.7.3 first cut
# included scripts/__pycache__/ with 39 .pyc files, which blocked validation until
# trimmed. This script ensures that failure mode cannot recur from a clean invocation.
#
# Usage:
#   ./scripts/build-release-zip.sh <plugin-root> <version>
#
#   <plugin-root>  absolute path to the plugin source tree
#                  (the directory containing .claude-plugin/plugin.json)
#   <version>      semver string, e.g. 0.7.4 (no leading 'v')
#
# Output:
#   <plugin-root>/releases/co-author-harness-claude-v<version>.zip
#
# Exit codes:
#   0  success; zip built and staged
#   1  usage error
#   2  plugin-root missing or not a plugin source tree
#   3  plugin.json version field does not match <version> argument
#   4  plugin.json description exceeds 400-character ceiling
#      (see .auto-memory/feedback_plugin_manifest_description_limit.md)
#   5  zip command failed
#   6  validation check on built zip failed

set -euo pipefail

# ---------- argument parsing ----------

if [[ $# -ne 2 ]]; then
  printf 'usage: %s <plugin-root> <version>\n' "$(basename "$0")" >&2
  printf '  example: %s /path/to/co-author-harness 0.7.4\n' "$(basename "$0")" >&2
  exit 1
fi

PLUGIN_ROOT="$1"
VERSION="$2"

if [[ ! -d "$PLUGIN_ROOT" ]]; then
  printf 'error: plugin-root is not a directory: %s\n' "$PLUGIN_ROOT" >&2
  exit 2
fi

MANIFEST="$PLUGIN_ROOT/.claude-plugin/plugin.json"
if [[ ! -f "$MANIFEST" ]]; then
  printf 'error: .claude-plugin/plugin.json not found under %s\n' "$PLUGIN_ROOT" >&2
  exit 2
fi

# ---------- manifest integrity checks ----------

# Check the manifest version field matches the <version> arg.
# We use python because jq may not be available on every dev box.
MANIFEST_VERSION="$(python3 -c '
import json, sys
with open(sys.argv[1]) as f:
    d = json.load(f)
print(d.get("version", ""))
' "$MANIFEST")"

if [[ "$MANIFEST_VERSION" != "$VERSION" ]]; then
  printf 'error: manifest version (%s) does not match <version> arg (%s)\n' \
    "$MANIFEST_VERSION" "$VERSION" >&2
  printf '  expected: %s\n' "$VERSION" >&2
  printf '  actual:   %s (in %s)\n' "$MANIFEST_VERSION" "$MANIFEST" >&2
  exit 3
fi

# Check the description field does not exceed 400 characters.
# Anthropic's plugin loader silently rejects overruns with a generic
# "Plugin validation failed" message; the 400-char ceiling was learned
# empirically at the v0.7.3 release cut.
DESCRIPTION_LEN="$(python3 -c '
import json, sys
with open(sys.argv[1]) as f:
    d = json.load(f)
print(len(d.get("description", "")))
' "$MANIFEST")"

if [[ "$DESCRIPTION_LEN" -gt 400 ]]; then
  printf 'error: plugin.json description length %d exceeds 400-char ceiling\n' \
    "$DESCRIPTION_LEN" >&2
  printf '  see .auto-memory/feedback_plugin_manifest_description_limit.md\n' >&2
  exit 4
fi

# ---------- release directory setup ----------

RELEASES_DIR="$PLUGIN_ROOT/releases"
if [[ ! -d "$RELEASES_DIR" ]]; then
  printf 'creating releases/ dir at %s\n' "$RELEASES_DIR"
  mkdir -p "$RELEASES_DIR"
fi

ZIP_NAME="co-author-harness-claude-v${VERSION}.zip"
ZIP_PATH="$RELEASES_DIR/$ZIP_NAME"

if [[ -f "$ZIP_PATH" ]]; then
  printf 'note: overwriting existing %s\n' "$ZIP_PATH" >&2
  rm -f "$ZIP_PATH"
fi

# ---------- the zip invocation ----------

# The exclusion list is LOAD-BEARING. Do not remove entries without updating
# handoff-§7.4 and the release-cut runbook.
#
# -r     recurse into subdirectories
# -q     quiet (show only errors; success is signaled by exit code)
# -9     maximum compression
# -x PAT exclude paths matching PAT (repeated per pattern)
#
# The PATTERNS (each listed in BOTH top-level and nested form, because the
# zip default glob `*/legacy/*` matches only nested paths and lets the
# top-level dir slip through — a v0.7.4-discovered packaging bug):
#   __pycache__/* + */__pycache__/*  bytecode cache contents
#   __pycache__   + */__pycache__    the cache dir entry itself
#   *.pyc                            bytecode artefacts at any depth
#   */.DS_Store                      macOS Finder metadata
#   setup/*       + */setup/*        author-side scaffolding
#   unpacked/*    + */unpacked/*     unpacked-snapshot mirrors
#   archive/*     + */archive/*      workspace-retired ancestry
#   archives/*    + */archives/*     bulk / legacy drops (gitignored; not plugin payload)
#   legacy/*      + */legacy/*       plugin-internal retired surfaces
#   proposals/*   + */proposals/*    harness-root artefacts, not plugin payload
#   releases/*    + */releases/*     releases dir never zipped into a release
#   .plugin-calibrator.json          config for a peer plugin, not this plugin
#   docs/release-notes/RELEASE_NOTES_v0.*[!4].md  historical release notes (keep current only)
#   .git/*, *.swp, *~                VCS / editor crud
#
# v0.7.4-discovery: the original `*/path/*` patterns failed to exclude
# TOP-LEVEL `legacy/` and `releases/`. The fix adds the bare `legacy/*`
# and `releases/*` patterns alongside the nested forms, and also strips
# historical `docs/release-notes/RELEASE_NOTES_*.md` and the `.plugin-calibrator.json` config file
# that belongs to a peer plugin, not this plugin. Reference: the v0.5.4
# known-good reference zip ships only the current release's RELEASE_NOTES
# and no legacy/ at top-level.

cd "$PLUGIN_ROOT"

printf 'building %s ...\n' "$ZIP_PATH"

zip -r -q -9 "$ZIP_PATH" . \
  -x "__pycache__/*" \
  -x "*/__pycache__/*" \
  -x "__pycache__" \
  -x "*/__pycache__" \
  -x "*.pyc" \
  -x "*/.DS_Store" \
  -x "setup/*" \
  -x "*/setup/*" \
  -x "unpacked/*" \
  -x "*/unpacked/*" \
  -x "archive/*" \
  -x "*/archive/*" \
  -x "archives/*" \
  -x "*/archives/*" \
  -x "legacy/*" \
  -x "*/legacy/*" \
  -x "proposals/*" \
  -x "*/proposals/*" \
  -x "releases/*" \
  -x "*/releases/*" \
  -x ".claude/*" \
  -x "*/.claude/*" \
  -x "*.plugin" \
  -x "*.zip" \
  -x ".plugin-calibrator.json" \
  -x "docs/release-notes/RELEASE_NOTES_v0.5*.md" \
  -x "docs/release-notes/RELEASE_NOTES_v0.6*.md" \
  -x "docs/release-notes/RELEASE_NOTES_v0.7.0.md" \
  -x "docs/release-notes/RELEASE_NOTES_v0.7.1.md" \
  -x "docs/release-notes/RELEASE_NOTES_v0.7.2.md" \
  -x "docs/release-notes/RELEASE_NOTES_v0.7.3.md" \
  -x "docs/release-notes/RELEASE_NOTES_v0.7.4.md" \
  -x "docs/release-notes/RELEASE_NOTES_v0.7.4.1.md" \
  -x "docs/release-notes/RELEASE_NOTES_v0.8.0.md" \
  -x "docs/release-notes/RELEASE_NOTES_v0.8.1.md" \
  -x "docs/release-notes/RELEASE_NOTES_v0.8.2.md" \
  -x "docs/release-notes/RELEASE_NOTES_v0.8.3.md" \
  -x ".git/*" \
  -x ".git" \
  -x "*.swp" \
  -x "*~" \
  || { printf 'error: zip command failed\n' >&2; exit 5; }

# ---------- post-build validation ----------

# Sanity checks on the produced zip:
#   (a) no __pycache__ entries
#   (b) no .pyc entries
#   (c) plugin.json is present at .claude-plugin/plugin.json
#   (d) at least one agent file is present
#   (e) at least one skill file is present

printf 'validating %s ...\n' "$ZIP_NAME"

BAD_PYCACHE="$(unzip -l "$ZIP_PATH" | grep -c '__pycache__' || true)"
if [[ "$BAD_PYCACHE" -gt 0 ]]; then
  printf 'error: zip contains %d __pycache__ entries\n' "$BAD_PYCACHE" >&2
  exit 6
fi

BAD_PYC="$(unzip -l "$ZIP_PATH" | grep -c '\.pyc$' || true)"
if [[ "$BAD_PYC" -gt 0 ]]; then
  printf 'error: zip contains %d .pyc entries\n' "$BAD_PYC" >&2
  exit 6
fi

BAD_ARCHIVES="$(unzip -Z1 "$ZIP_PATH" | grep -Ec '\.(plugin|zip)$' || true)"
if [[ "$BAD_ARCHIVES" -gt 0 ]]; then
  printf 'error: zip contains %d nested archive entries\n' "$BAD_ARCHIVES" >&2
  exit 6
fi

BAD_CLAUDE_STATE="$(unzip -Z1 "$ZIP_PATH" | grep -Ec '(^|/)\.claude/' || true)"
if [[ "$BAD_CLAUDE_STATE" -gt 0 ]]; then
  printf 'error: zip contains %d local .claude state entries\n' "$BAD_CLAUDE_STATE" >&2
  exit 6
fi

HAS_MANIFEST="$(unzip -l "$ZIP_PATH" | grep -c '.claude-plugin/plugin.json' || true)"
if [[ "$HAS_MANIFEST" -lt 1 ]]; then
  printf 'error: zip does not contain .claude-plugin/plugin.json\n' >&2
  exit 6
fi

# Final size report.
SIZE_BYTES="$(stat -c%s "$ZIP_PATH" 2>/dev/null || stat -f%z "$ZIP_PATH")"
SIZE_KB="$(( SIZE_BYTES / 1024 ))"

printf 'done.\n'
printf '  zip:    %s\n' "$ZIP_PATH"
printf '  size:   %d KB (%d bytes)\n' "$SIZE_KB" "$SIZE_BYTES"
printf '  entries: %d\n' "$(unzip -l "$ZIP_PATH" | tail -1 | awk '{print $2}')"
