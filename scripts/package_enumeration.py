#!/usr/bin/env python3
"""package_enumeration - the neutral, normally-importable package-file authority.

WHY THIS MODULE EXISTS
----------------------
`build-plugin.py` carries a hyphen and cannot be imported normally, so the
census loaded it with a try/except:

    try:
        from build_plugin_shim import enumerate_package_files   # never existed
    except ImportError:
        <load build-plugin.py by path>

That is a latent hijack, not a fallback. The declared authority was in the
EXCEPT branch: create a file named `build_plugin_shim.py` anywhere on the path
and the census silently stops consuming the authority it documents. A checker
whose source of truth can be swapped by adding a file is not a checker.

So the enumeration lives here, in a module with an importable name, and
`build-plugin.py` and `scripts/analysis/code_census.py` both `import` it --
no path loading, no fallback, no branch that can quietly win.

SCOPE - READ BEFORE CALLING THIS "THE" AUTHORITY
------------------------------------------------
This is authoritative for the **Cowork `.plugin` upload bundle** only.
`scripts/release-gate.sh` (~:1127) still enumerates its own population for the
full-release path -- current working-tree files minus its own exclusions -- and
root governance names release-gate as the release path. Until release-gate
imports this function too, the repository has TWO package populations and
"drift is impossible by construction" is FALSE. That convergence is an open
blocker, deliberately not claimed closed here.

CONTRACT
--------
Enumeration answers "which files ship". It does NOT answer "what do they say
now". Which content a caller reads is the CALLER's decision, and the two live
callers correctly disagree:

  * scripts/analysis/code_census.py  -> WORKTREE bytes. Detecting uncommitted
    subject changes is the point; a run's evidence must go stale when the code
    it exercised changes. HEAD blobs would hide exactly what it exists to find.
  * scripts/build-plugin.py          -> HEAD bytes (via `git archive`).
    Producing a commit artifact is the point; worktree bytes would ship
    uncommitted content under a commit's file list.

An earlier version of this docstring told ALL callers to use worktree bytes and
"never HEAD blobs". That was the census's rule stated as a universal one, and it
was false for the builder the moment it existed -- the same mistake as reading
MFHP's component-scoped outcome table as global law. State the caller's rule
with the caller.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

# HARNESS is this file's repo. Full stop.
#
# A COAUTHOR_BUILD_SOURCE_REPO env override lived here to support a re-exec
# design that was ABANDONED (it could not bootstrap: the snapshot runs the
# committed toolchain, which cannot know about a pointer that is itself
# uncommitted). The override outlived the design and became a live ambient
# authority: any environment could silently redirect BOTH this module and the
# builder at another repository, unreported and absent from the declared
# dependency planes. Dead scaffolding that can still steer the authority is
# worse than the feature it was built for.
HARNESS = Path(__file__).resolve().parent.parent

GIT_CANDIDATES = [
    r"C:\Program Files\Git\bin\git.exe",
    r"C:\Program Files\Git\cmd\git.exe",
    "git",  # POSIX / PATH-resolvable
]


def find_git() -> str:
    for candidate in GIT_CANDIDATES:
        if Path(candidate).is_file() or candidate == "git":
            return candidate
    return "git"


GIT = find_git()

# Archives are never bundle inputs: nested archives violate the Cowork loader
# contract and can make upload installs fail.
ARCHIVE_SUFFIXES = (".plugin", ".zip")


def resolve_head() -> str:
    """Resolve HEAD to a full SHA, once.

    Every decision in a build must bind to ONE commit. Enumeration used to run
    `ls-tree HEAD` and materialization independently re-resolved `HEAD`, so a
    HEAD that moved between the two calls (a concurrent commit, a checkout)
    yielded membership from commit A and bytes from commit B -- the same
    check/act race the dirty guard had, one level up. Callers resolve first and
    pass the SHA to both.
    """
    return subprocess.run(
        [GIT, "-C", str(HARNESS), "rev-parse", "HEAD"],
        capture_output=True, text=True, encoding="utf-8", check=True,
    ).stdout.strip()


def enumerate_package_files(commit: str | None = None) -> tuple[list[str], list[str]]:
    """Return (files, excluded_archives) as repo-relative POSIX paths.

    Tracked files at `commit` (default: HEAD), minus archives. Single source of
    truth for the .plugin bundle -- see module docstring for the release-gate
    caveat.

    Pass an explicit SHA when the result must agree with other commit-bound
    operations; defaulting to HEAD is only safe for read-only inspection.

    Extracted from build-plugin.py 2026-07-15 because packaging and the
    fixture-runner's tested-input binding had diverged: the census hashed a
    six-root allowlist of 365 paths against this enumeration's 450, omitting 87
    shipped files (README.md, CLAUDE.md, CHANGELOG.md, .github/**, docs/**,
    reviews/**, root config) and including 2 generated .plugin archives this
    excludes. Editing an omitted shipped file left a run's evidence "valid";
    rebuilding an archive invalidated it. Wrong in both directions.
    """
    result = subprocess.run(
        [GIT, "-C", str(HARNESS), "ls-tree", "-r", commit or "HEAD", "--name-only"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    files = [line for line in result.stdout.splitlines() if line.strip()]
    filtered = [f for f in files if not f.endswith(ARCHIVE_SUFFIXES)]
    excluded = sorted(set(files) - set(filtered))
    return filtered, excluded
