# Release notes

Per-version ship notes live here as `RELEASE_NOTES_v*.md` (workspace copy of what accompanies releases; older versions remain for history).

- **Current manifest version** is authoritative in `.claude-plugin/plugin.json` and the top of `CHANGELOG.md`.
- **Lean release zips** (see `scripts/build-release-zip.sh`) exclude historical `RELEASE_NOTES_*.md` files so the archive carries only the current point release’s note, plus the rolling `CHANGELOG.md`.
