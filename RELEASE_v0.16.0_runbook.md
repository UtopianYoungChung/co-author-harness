# Release v0.16.0 — Finish-on-Windows Runbook

**Status as of 2026-06-25.** The 0.16.0 release was prepared in a Cowork Linux sandbox
whose mount of `B:\` blocks file *deletion*, so git writes could not be completed
cleanly there. Everything below must run on **Windows**, where unlink works normally.

Run all commands from the repo root: `B:\Agents\platform\co-author-harness`.

---

## What is already done (on disk)

- **Version bumped to 0.16.0** across `plugin.json`, `marketplace.json`, README badge +
  `## Version` + table, and `CHANGELOG.md` (the `Unreleased` section became
  `## v0.16.0 — 2026-06-25`, documenting PR-3b.4 *and* the BFO ontology guideline + C-6).
- **Release commit made:** `1d1987f` "Release v0.16.0: lifecycle ladder (PR-3b.4) + BFO
  ontology guideline & C-6". Tag `v0.16.0` currently points here.
- **`release-gate.sh`: CLEARED** — 0 blockers (2 advisory warnings: long description,
  104 token-budget soft breaches; both pre-existing, non-blocking).
- **Release zip built + validated:** `releases/co-author-harness-claude-v0.16.0.zip`
  (513 entries, ~1.66 MB; 0 `__pycache__`/`.pyc`/`.git`/`.claude`; manifest 0.16.0).
- **Marketplace validation errors fixed** (the upload that failed with 3 errors):
  - CRLF→LF normalized in 11 `SKILL.md` files (the two flagged — `run-phase-1`,
    `run-phase-3` — plus 9 with latent CRLF). *Note: git already stored LF, so these are
    invisible to `git diff`; the CRLF lived only in the working tree, which is what the
    marketplace packages.*
  - `claim-coverage-audit` description: `<section>/<date>/<cycle_id>` →
    `{section}/{date}/{cycle_id}` (angle brackets were read as XML tags).
  - `.gitattributes` hardened to `* text=auto eol=lf` so checkout cannot re-introduce CRLF.
  - Zip rebuilt and re-verified: 0 CRLF, 0 XML tags.

## What remains (do these on Windows)

The only *committable* changes still uncommitted are `claim-coverage-audit/SKILL.md` and
`.gitattributes` (the 11 CRLF normalizations don't appear in `git diff` — see note above).
The tag `v0.16.0` still points at `1d1987f` (the bump commit), **not** the validation fixes.

---

## Step 1 — Clean up stray git lock/temp files

The sandbox left lock and temp files it could not delete (`HEAD.lock`, `index.lock`,
`refs/tags/v0.16.0.lock`, `objects/maintenance.lock`, ~55 `objects/**/tmp_obj_*`, and a
few `_lk_*` / `stale_index_lock_*`). `.git/HEAD.lock` will block local git writes until
removed.

```powershell
cd "B:\Agents\platform\co-author-harness"
Get-ChildItem .git -Recurse -Include "tmp_obj_*","*.lock","stale_index_lock_*","_lk_*" | Remove-Item -Force
git status   # should run cleanly now
```

## Step 2 — Commit the validation fixes and move the tag onto them

```powershell
git commit -am "Fix SKILL.md marketplace validation (v0.16.0): pin eol=lf, debrace claim-coverage placeholders"
git tag -f v0.16.0
```

## Step 3 — Push commit + tag to GitHub

Remote: `https://github.com/UtopianYoungChung/co-author-harness.git`

```powershell
git push origin main --follow-tags --force-with-lease
```

(`--force-with-lease` is needed only because Step 2 moved the `v0.16.0` tag.)

## Step 4 — Verify

```powershell
git status            # clean tree
git describe --tags   # -> v0.16.0
python scripts\version-check.py   # 0 blockers; all surfaces = 0.16.0
```

## Step 5 — Re-upload the plugin

Upload the corrected artifact — either re-run the marketplace upload from the working tree
or use `releases\co-author-harness-claude-v0.16.0.zip`. It should now pass (the 3 SKILL.md
errors are resolved).

## Step 6 — Refresh the plugin runtime

In Claude's plugin / marketplace settings, refresh the `agents` marketplace (or remove +
re-add `co-author-harness-claude`) so the runtime picks up **0.16.0** from
`platform/co-author-harness`. Confirm it reports `0.16.0` — this also closes the last
`canonical` watch item in the Overseer status
(`governance/overseer-governance/status/index.json`).

---

## Rollback (if needed)

The pre-edit index backup is `..\..\ROOT_ARCHITECTURE_INDEX.md.bak_2026-06-25` (governance
refresh, unrelated to the plugin). For the plugin itself, the bump and fixes are isolated
to: `plugin.json`, `marketplace.json`, `README.md`, `CHANGELOG.md`, `.gitattributes`, and
`skills/claim-coverage-audit/SKILL.md`. `git revert 1d1987f` (and the fix commit) undoes
the release without touching history if you have already pushed.
