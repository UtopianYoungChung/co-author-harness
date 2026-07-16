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
now": callers needing content must hash the WORKING TREE, never HEAD blobs. A
dirty worktree carries uncommitted subject changes under a clean commit id.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

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


def enumerate_package_files() -> tuple[list[str], list[str]]:
    """Return (files, excluded_archives) as repo-relative POSIX paths.

    Tracked files at HEAD, minus archives. Single source of truth for the
    .plugin bundle -- see module docstring for the release-gate caveat.

    Extracted from build-plugin.py 2026-07-15 because packaging and the
    fixture-runner's tested-input binding had diverged: the census hashed a
    six-root allowlist of 365 paths against this enumeration's 450, omitting 87
    shipped files (README.md, CLAUDE.md, CHANGELOG.md, .github/**, docs/**,
    reviews/**, root config) and including 2 generated .plugin archives this
    excludes. Editing an omitted shipped file left a run's evidence "valid";
    rebuilding an archive invalidated it. Wrong in both directions.
    """
    result = subprocess.run(
        [GIT, "-C", str(HARNESS), "ls-tree", "-r", "HEAD", "--name-only"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    files = [line for line in result.stdout.splitlines() if line.strip()]
    filtered = [f for f in files if not f.endswith(ARCHIVE_SUFFIXES)]
    excluded = sorted(set(files) - set(filtered))
    return filtered, excluded
