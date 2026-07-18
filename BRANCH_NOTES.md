# BRANCH_NOTES.md - codex-dist (generated distribution branch)

This branch is a **generated Codex-compatible repackaging** of the v0.30.0 release.
It is NOT the authoring root. Do not develop here.

Why it exists: Codex CLI's marketplace resolver does not enumerate a plugin whose
marketplace entry uses a self-referential `source: "./"`. It requires the plugin to
live in a real subdirectory. `main` keeps the canonical root-deploy layout; this
branch mirrors the same v0.30.0 content under `plugins/co-author-harness-claude/`
with a root marketplace.json pointing there.

Consumers:
- Codex:  codex plugin marketplace add UtopianYoungChung/co-author-harness --ref codex-dist
          codex plugin add co-author-harness-claude@joseph-chung-co-author-harness
- Claude Code also works from this layout, but currently installs from main (root).

Regenerate per release: worktree off the release tag, git mv the tree into
plugins/co-author-harness-claude/, write the root marketplace.json (source =
./plugins/co-author-harness-claude, metadata.version = <release>), commit, push.
