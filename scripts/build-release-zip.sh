#!/usr/bin/env bash
# build-release-zip.sh — convenience wrapper over the committed builder.
#
# CONVERGED (2026-07-16): this script no longer owns a package population.
# It used to run its own `zip -r` over the WORKTREE with a hand-maintained
# exclusion list — a THIRD population beside release-gate.sh Phase 1 and
# scripts/package_enumeration.py, each with different opinions (this one
# also stripped historical release notes and .plugin-calibrator.json, which
# the canonical population ships). Every bundle producer now delegates to
# scripts/build-plugin.py: commit-bound bytes from a clean worktree re-exec,
# rendered includes, embedded PROVENANCE.json, one population authority
# (scripts/package_enumeration.py). If you need a different population,
# change the authority, not a wrapper.
#
# What this wrapper still owns:
#   * the releases/ staging convention and <name>-v<version>.zip naming
#   * fail-fast manifest checks (version arg match; 400-char description
#     ceiling learned empirically at the v0.7.3 cut — the loader rejects
#     overruns with a generic "Plugin validation failed")
#   * independent post-build validation of the ARTIFACT (never trust the
#     producer's exit code alone)
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
#   0  success; zip built, validated, and staged
#   1  usage error
#   2  plugin-root missing or not a plugin source tree
#   3  plugin.json version field does not match <version> argument
#   4  plugin.json description exceeds 400-character ceiling
#   5  the committed builder failed (its own exit code is reported;
#      see scripts/build-plugin.py's contract: 5 provenance readback,
#      6 no child bundle, 7 worktree cleanup VOID, ...)
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
DESCRIPTION_LEN="$(python3 -c '
import json, sys
with open(sys.argv[1]) as f:
    d = json.load(f)
print(len(d.get("description", "")))
' "$MANIFEST")"

if [[ "$DESCRIPTION_LEN" -gt 400 ]]; then
  printf 'error: plugin.json description length %d exceeds 400-char ceiling\n' \
    "$DESCRIPTION_LEN" >&2
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

# ---------- build via the committed builder ----------

printf 'building via scripts/build-plugin.py ...\n'
set +e
( cd "$PLUGIN_ROOT" && python3 scripts/build-plugin.py )
BUILD_RC=$?
set -e
if [[ "$BUILD_RC" -ne 0 ]]; then
  printf 'error: build-plugin.py exited %d (see its exit-code contract)\n' "$BUILD_RC" >&2
  exit 5
fi

PLUGIN_ARTIFACT="$PLUGIN_ROOT/.claude-plugin/co-author-harness-claude.plugin"
if [[ ! -f "$PLUGIN_ARTIFACT" ]]; then
  printf 'error: builder exited 0 but no artifact at %s\n' "$PLUGIN_ARTIFACT" >&2
  exit 5
fi

cp "$PLUGIN_ARTIFACT" "$ZIP_PATH"

# ---------- post-build validation ----------

# Independent checks on the produced zip — verify the ARTIFACT, not the
# producer's exit code:
#   (a) no __pycache__ / .pyc entries        (c) manifest present
#   (b) no nested archives, no .claude state (d) agents + skills present
#   (e) PROVENANCE.json names the repo's current HEAD

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

HAS_MANIFEST="$(unzip -Z1 "$ZIP_PATH" | grep -c '^\.claude-plugin/plugin\.json$' || true)"
if [[ "$HAS_MANIFEST" -lt 1 ]]; then
  printf 'error: zip does not contain .claude-plugin/plugin.json\n' >&2
  exit 6
fi

HAS_AGENTS="$(unzip -Z1 "$ZIP_PATH" | grep -c '^agents/.*\.md$' || true)"
if [[ "$HAS_AGENTS" -lt 1 ]]; then
  printf 'error: zip contains no agents/*.md\n' >&2
  exit 6
fi

HAS_SKILLS="$(unzip -Z1 "$ZIP_PATH" | grep -c '^skills/.*/SKILL\.md$' || true)"
if [[ "$HAS_SKILLS" -lt 1 ]]; then
  printf 'error: zip contains no skills/*/SKILL.md\n' >&2
  exit 6
fi

PROV_COMMIT="$(unzip -p "$ZIP_PATH" PROVENANCE.json 2>/dev/null \
  | python3 -c 'import json,sys; print(json.load(sys.stdin).get("commit",""))' 2>/dev/null || true)"
HEAD_SHA="$(git -C "$PLUGIN_ROOT" rev-parse HEAD 2>/dev/null || true)"
if [[ -z "$PROV_COMMIT" || -z "$HEAD_SHA" || "$PROV_COMMIT" != "$HEAD_SHA" ]]; then
  printf 'error: PROVENANCE.json commit (%s) does not name HEAD (%s)\n' \
    "${PROV_COMMIT:0:12}" "${HEAD_SHA:0:12}" >&2
  exit 6
fi

# Final size report.
SIZE_BYTES="$(stat -c%s "$ZIP_PATH" 2>/dev/null || stat -f%z "$ZIP_PATH")"
SIZE_KB="$(( SIZE_BYTES / 1024 ))"

printf 'done.\n'
printf '  zip:    %s\n' "$ZIP_PATH"
printf '  commit: %s\n' "$PROV_COMMIT"
printf '  size:   %d KB (%d bytes)\n' "$SIZE_KB" "$SIZE_BYTES"
printf '  entries: %d\n' "$(unzip -Z1 "$ZIP_PATH" | wc -l)"
