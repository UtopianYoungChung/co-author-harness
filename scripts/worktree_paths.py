#!/usr/bin/env python3
r"""worktree_paths - one authority for "where may a test sandbox live".

WHY THIS MODULE EXISTS (2026-07-16, Codex review finding F1)
-----------------------------------------------------------
Three test scripts each derived a sandbox base as `HARNESS.parent / <name>`.
That is outside the repository ONLY for the primary checkout. For a perfectly
legitimate linked worktree at `co-author-harness/.worktrees/<name>`, the base
lands at `co-author-harness/.worktrees/` -- INSIDE the primary repository.

The consequence was not cosmetic. `build_plugin_provenance_smoketest`'s
git-failure case deletes a sandbox clone's `.git` to prove the builder aborts
when git is unusable. With the sandbox nested inside the real repo, git
discovery WALKS UP, finds the primary repository, and the builder succeeds --
so all three `git failure:*` assertions failed and the suite exited 1 when run
from `.worktrees/`. The file's own comments already said "a fixture repo
nested inside a real repo is not a sandbox"; the code then computed a base
that violated it in the exact layout git itself creates. Reproduced by Codex:
30/31 suites, provenance rc=1, runner rc=1, parity rc=1 (the runner correctly
voided the manifest).

The fix is to stop deriving location from `__file__` -- which says where the
CODE is, not where the REPOSITORY is -- and ask git:

    git rev-parse --path-format=absolute --git-common-dir

That resolves to the PRIMARY's `.git` from every worktree (verified: primary,
internal, and external worktrees all return the same path), so one rule yields
one shared, outside-every-worktree base for all layouts.

SAME-DRIVE IS LOAD-BEARING, NOT INCIDENTAL
`git clone --local` hardlinks the object store, and hardlinks cannot cross
volumes: cloning `B:\...` into `C:\Users\...\Temp` dies with `fatal: failed to
create link ... Improper link` (exit 128). `--no-hardlinks` works but deep-
copies a ~6 MB object store per case and made the suite unusably slow. The
base is therefore a SIBLING of the primary worktree: same drive, outside the
tree.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from package_enumeration import GIT

__all__ = ["git_common_dir", "registered_worktree_roots", "primary_worktree_root",
           "sandbox_base", "assert_outside_all_worktrees"]


def git_common_dir(repo: Path) -> Path:
    """The SHARED git admin directory -- identical from every worktree.

    `--git-dir` differs per worktree (a linked worktree's is
    `<common>/worktrees/<name>`); `--git-common-dir` is the shared one. That
    difference is exactly why the lock and the sandbox base must be derived
    from the COMMON dir: anything per-worktree is not repository-global.
    """
    out = subprocess.run(
        [GIT, "-C", str(repo), "rev-parse", "--path-format=absolute",
         "--git-common-dir"],
        capture_output=True, text=True, encoding="utf-8", check=True,
    ).stdout.strip()
    return Path(out).resolve()


def registered_worktree_roots(repo: Path) -> list[Path]:
    """Every worktree root git knows about (primary first, per porcelain)."""
    out = subprocess.run(
        [GIT, "-C", str(repo), "worktree", "list", "--porcelain"],
        capture_output=True, text=True, encoding="utf-8", check=True,
    ).stdout
    roots: list[Path] = []
    for line in out.splitlines():
        if line.startswith("worktree "):
            roots.append(Path(line[len("worktree "):].strip()).resolve())
    return roots


def primary_worktree_root(repo: Path) -> Path:
    """The primary checkout's root, derived from the COMMON git dir.

    Not `HARNESS` and not "the first porcelain entry": both are indirect. The
    common dir is `<primary>/.git` for a normal (non-bare, non-separate-dir)
    repository, which this project is; the parent is therefore the primary
    worktree root, whichever worktree we are called from.
    """
    common = git_common_dir(repo)
    if common.name != ".git":
        # Separate git dir / bare repo: no primary worktree to be a sibling
        # of. Fail loudly rather than invent a location -- an unreviewed
        # guess here silently relocates every test sandbox.
        raise RuntimeError(
            f"unsupported layout: --git-common-dir is {common}, expected a "
            "path ending in .git; sandbox placement is undefined here"
        )
    return common.parent


def assert_outside_all_worktrees(path: Path, repo: Path) -> None:
    """Refuse a path that is, or lives inside, any registered worktree.

    Mechanical, not a comment: the previous version DOCUMENTED this
    requirement and then computed a base that violated it under
    `.worktrees/`. Checked against git's own registry, so a worktree added
    after this module was written is still caught.
    """
    path = path.resolve()
    for root in registered_worktree_roots(repo):
        if path == root or root in path.parents:
            raise RuntimeError(
                f"sandbox base {path} is inside registered worktree {root}; "
                "git discovery walks up, so a fixture repo there is not a "
                "sandbox (deleting its .git would find the parent repo)"
            )


def sandbox_base(repo: Path, name: str) -> Path:
    """A safe, same-drive sandbox base, identical from every worktree.

    Sibling of the PRIMARY worktree root: same volume (hardlinked
    `git clone --local` works) and outside every worktree (git discovery
    cannot walk up into a real repository). Verified mechanically before
    it is returned.
    """
    base = primary_worktree_root(repo).parent / name
    assert_outside_all_worktrees(base, repo)
    base.mkdir(parents=True, exist_ok=True)
    return base
