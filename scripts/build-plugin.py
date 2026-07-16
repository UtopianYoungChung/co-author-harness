#!/usr/bin/env python3
"""Build the co-author-harness `.plugin` bundle for Cowork's file-upload install path.

A `.plugin` file is a ZIP archive with `.claude-plugin/plugin.json` at the
archive root and the plugin's directory tree underneath. Cowork's plugin
loader UI accepts file uploads with this extension; the bundle sidesteps the
URL/marketplace install path (which requires the repo to be public + ship a
marketplace.json).

**Bundle definition.** `git ls-tree -r HEAD --name-only` on the harness root.
Tracked files at the current HEAD go in; untracked session-scope content
(`.claude/handoffs/`, `artifacts/efficiency/<timestamp>/`, runtime outputs)
is excluded by definition. The `.gitignore` excludes `*.plugin` files, so
the previously-built bundle (if present in `.claude-plugin/`) is invisible
to `git ls-tree` and won't recurse into the new bundle.

**Defense-in-depth.** The script filters archive files from the bundle
even if `git ls-tree` returned them — protects against future `.gitignore`
drift. A nested archive file inside a `.plugin` archive violates the
Cowork loader contract.

**Output.** `<harness>/.claude-plugin/<plugin-name>.plugin` (plugin name read
from `.claude-plugin/plugin.json`).

**Usage.**

    python scripts/build-plugin.py

Or with PYTHONUTF8=1 on Windows hosts where stdlib defaults to cp949 and the
plugin tree carries §, →, em dashes, etc.:

    set PYTHONUTF8=1
    "C:\\Users\\<user>\\AppData\\Local\\Programs\\Python\\Launcher\\py.exe" \\
        scripts\\build-plugin.py

**Exit codes.**

    0  bundle written successfully
    1  required files missing from the tracked set
    2  git ls-tree failed (not a git repo? HEAD missing?)
    3  plugin.json missing or unparseable
"""

from __future__ import annotations

import json
import contextlib
import datetime
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

from resolve_includes import resolve_includes_in_text

# Resolve harness root from this script's location: scripts/build-plugin.py
HARNESS = Path(__file__).resolve().parent.parent

# Resolve git executable. On Windows hosts the launcher path is required
# because PATH may not include git in some shell environments.
GIT_CANDIDATES = [
    r"C:\Program Files\Git\cmd\git.exe",
    "git",  # POSIX / PATH-resolvable
]


def find_git() -> str:
    for candidate in GIT_CANDIDATES:
        if Path(candidate).is_file() or candidate == "git":
            return candidate
    return "git"


GIT = find_git()

# Sanity-check files: every bundle must include these or it's not a usable plugin
REQUIRED_FILES = (
    ".claude-plugin/plugin.json",
    "agents/planner.md",
    "skills/plugin-commands/SKILL.md",
    "README.md",
    "CHANGELOG.md",
    "CLAUDE.md",
    # This module's own import target. Added 2026-07-15 after the extraction
    # shipped a BROKEN bundle: build-plugin.py (tracked) began importing
    # package_enumeration.py (untracked), so HEAD-based enumeration excluded the
    # target while including the importer. Verified against the archive:
    #   MEMBERS 450 / HAS_AUTHORITY_MODULE False /
    #   ARCHIVED_BUILDER_IMPORTS_AUTHORITY True / HEAD_TRACKS_AUTHORITY False
    # Running the archived builder would raise ModuleNotFoundError. It "passed"
    # only because it was run from the worktree, where the import resolves --
    # the artifact was never exercised.
    #
    # Listing it here makes the builder REFUSE to build until the dependency is
    # tracked at HEAD. A build tool must not be able to emit a bundle that
    # cannot run itself.
    "scripts/package_enumeration.py",
)


# The enumeration lives in the neutral, importable module so that packaging and
# the census consume the SAME function -- not two copies that drift.
# scripts/analysis/code_census.py imports it from there as well.
#
# NOTE (open): scripts/release-gate.sh (~:1127) still enumerates its own
# population for the full-release path, and root governance names release-gate
# as the release path. Until it consumes package_enumeration too, this repo has
# TWO package populations. Do not describe this as "the" repo-wide authority.
from package_enumeration import (  # noqa: E402,F401
    ARCHIVE_SUFFIXES,
    enumerate_package_files,
    resolve_head,
)


@contextlib.contextmanager
def materialize_commit(commit: str):
    """Yield a Path holding the tree of `commit`, extracted from the object store.

    Takes an explicit SHA -- never re-resolves HEAD. An earlier revision had
    enumeration run `ls-tree HEAD` and materialization separately resolve
    `HEAD`: if HEAD moved between them, membership came from commit A and bytes
    from commit B. One SHA, resolved once, passed to both.

    `git archive` streams from the object store, so the result cannot contain
    worktree bytes -- no probe, no race, no fail-open branch. check=True on the
    call: a git failure must raise, never yield an empty result that reads as
    success (the deleted dirty guard's probe had no check=True and concluded
    "clean" on returncode 128).

    Context-managed. An earlier revision deliberately leaked the tempdir ("the
    build is short-lived") and left six behind within one session -- a leak
    rationalised is still a leak.

    Cleanup does NOT ignore errors: `ignore_errors=True` was the exact
    behaviour rejected in the smoketest (it silently gave up on read-only
    .git objects and left four sandboxes behind), and it shipped here anyway.
    A cleanup that swallows failure is a leak with a comment on it.
    """
    tmp = Path(tempfile.mkdtemp(prefix="coauthor-build-"))
    try:
        tar_path = tmp / "tree.tar"
        with tar_path.open("wb") as fh:
            subprocess.run(
                [GIT, "-C", str(HARNESS), "archive", "--format=tar", commit],
                stdout=fh, check=True,
            )
        root = tmp / "tree"
        root.mkdir()
        with tarfile.open(tar_path) as tf:
            tf.extractall(root)
        tar_path.unlink()
        yield root
    finally:
        def _on_error(func, p, _exc):
            os.chmod(p, 0o700)   # read-only tar members defeat plain rmtree
            func(p)
        try:
            shutil.rmtree(tmp, onexc=_on_error)          # py3.12+
        except TypeError:
            shutil.rmtree(tmp, onerror=lambda f, p, e: _on_error(f, p, e))


def main() -> int:
    # ONE SHA governs every decision below: enumeration, materialization, the
    # manifest, and the reported provenance. Resolving HEAD more than once
    # reintroduces a check/act race at the COMMIT level -- membership from
    # commit A, bytes from commit B.
    try:
        head_sha = resolve_head()
    except subprocess.CalledProcessError as exc:
        print(f"[ERROR] cannot resolve HEAD: {exc.stderr or exc}", file=sys.stderr)
        return 2

    # Enumerate via the SHARED authority, bound to that SHA (also consumed by
    # the census's tested-input binding). Do not inline a second copy here: a
    # duplicated enumeration is how packaging and the fixture runner drifted.
    try:
        files, excluded_archive_files = enumerate_package_files(head_sha)
    except subprocess.CalledProcessError as exc:
        print(f"[ERROR] git ls-tree failed: {exc.stderr or exc}", file=sys.stderr)
        return 2

    print(f"Tracked files: {len(files)}")
    if excluded_archive_files:
        print(f"[WARN] excluding {len(excluded_archive_files)} archive file(s) "
              f"from bundle (defense-in-depth):", file=sys.stderr)
        for f in excluded_archive_files:
            print(f"    {f}", file=sys.stderr)

    # NO DIRTY GUARD. The guard is deleted, not fixed.
    #
    # The first attempt was a check-then-act preflight: read `git status`, refuse
    # if tracked files were dirty. Three defects, all structural rather than
    # incidental:
    #   * fails open -- the probe had no check=True; a git failure yields empty
    #     stdout, so `dirty == []` and the builder concludes CLEAN (verified:
    #     returncode 128, stdout empty);
    #   * mis-parses porcelain -- a staged rename `R  old.md -> new.md` became
    #     the path "old.md -> new.md", intersecting nothing, so the rename was
    #     invisible;
    #   * races -- it checked once and read each file later; a file edited
    #     between the check and z.write() ships uncommitted bytes under a clean
    #     verdict. No amount of parsing fixes that.
    #
    # The real error was the component boundary, not the parser:
    #   census  = HEAD enumeration + WORKTREE bytes -- detecting dirty subject
    #             changes IS its job.
    #   builder = HEAD enumeration + HEAD bytes -- producing a COMMIT ARTIFACT
    #             is its job.
    # Reading HEAD bytes makes a dirty bundle unrepresentable, so there is
    # nothing to guard, nothing to race, and nothing to fail open. `git archive`
    # materializes the commit tree atomically from the object store; include
    # resolution then runs against that snapshot, so includes are HEAD-sourced
    # too (resolve_includes_in_text reads its targets from disk at :73 -- reading
    # HEAD for the outer file alone would have pulled worktree includes into it).
    with materialize_commit(head_sha) as source_root:
        return _build(head_sha, source_root, files)


def _build(head_sha: str, source_root: Path, files: list[str]) -> int:
    print(f"Built from:    {head_sha[:12]} (materialized; worktree state is irrelevant)")

    # THE MANIFEST COMES FROM THE SNAPSHOT, NOT THE WORKTREE.
    # It was parsed from HARNESS before materialization, so a dirty
    # plugin.json could rename the output file, misreport the version, or make
    # a perfectly valid HEAD unbuildable -- worktree state leaking into an
    # artifact that claims commit provenance, through the one file that names it.
    manifest_path = source_root / ".claude-plugin" / "plugin.json"
    if not manifest_path.is_file():
        print(f"[ERROR] missing manifest at {head_sha[:12]}: .claude-plugin/plugin.json",
              file=sys.stderr)
        return 3
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[ERROR] cannot parse manifest at {head_sha[:12]}: {exc}", file=sys.stderr)
        return 3
    plugin_name = manifest.get("name", "plugin")
    plugin_version = manifest.get("version", "0.0.0")
    output = HARNESS / ".claude-plugin" / f"{plugin_name}.plugin"

    print(f"Harness root:  {HARNESS}")
    print(f"Plugin name:   {plugin_name}  (from {head_sha[:12]}, not the worktree)")
    print(f"Plugin ver:    {plugin_version} (manifest may be RC-deferred behind tag state)")
    print(f"Output:        {output}")

    # ls-tree and git archive are TWO population rules over the same commit.
    # They agree today, but `export-ignore` in .gitattributes would silently
    # make archive a subset -- membership from one rule, bytes from another.
    # Assert they match rather than assume it.
    materialized = {
        p.relative_to(source_root).as_posix()
        for p in source_root.rglob("*") if p.is_file()
    }
    enumerated = set(files)
    only_enum = sorted(enumerated - materialized)
    # Archive-suffixed paths are dropped by the enumerator by design, so their
    # presence in the snapshot is expected, not drift.
    only_mat = sorted(
        f for f in (materialized - enumerated) if not f.endswith(ARCHIVE_SUFFIXES)
    )
    if only_enum or only_mat:
        print("[ERROR] ls-tree and git archive disagree at "
              f"{head_sha[:12]} (export-ignore drift?):", file=sys.stderr)
        for f in only_enum[:5]:
            print(f"    enumerated, not materialized: {f}", file=sys.stderr)
        for f in only_mat[:5]:
            print(f"    materialized, not enumerated: {f}", file=sys.stderr)
        return 2
    print(f"Population:    ls-tree == git archive ({len(enumerated)} files)")

    # Verify required files are in the tracked set
    missing = [r for r in REQUIRED_FILES if r not in files]
    if missing:
        print(f"[ERROR] required files missing from tracked set: {missing}",
              file=sys.stderr)
        return 1
    print("All required files present.")

    # Build the .plugin (ZIP) file
    output.parent.mkdir(parents=True, exist_ok=True)
    total_size = 0
    skipped = 0
    # DETERMINISTIC ZIP METADATA -- the archive must be a pure function of the
    # commit, not of when it was built.
    #
    # Content-faithful was NOT byte-reproducible. `writestr()` stamps ambient
    # wall-clock, `write()` copies the extracted file's mtime, so two builds of
    # one SHA differed (2F2C179D1A30 vs 0C0B32EBF6A1) across THREE distinct
    # timestamps: 444 tar-mtime members plus 7 rendered ones that took two
    # different seconds *within a single build*.
    #
    # Every member is therefore written through an explicit ZipInfo carrying the
    # COMMIT's timestamp and fixed permissions. Nothing ambient touches the
    # archive: same SHA in, same bytes out.
    commit_epoch = int(subprocess.run(
        [GIT, "-C", str(HARNESS), "show", "-s", "--format=%ct", head_sha],
        capture_output=True, text=True, encoding="utf-8", check=True,
    ).stdout.strip())
    commit_dt = datetime.datetime.fromtimestamp(commit_epoch, datetime.timezone.utc)
    zip_date_time = (commit_dt.year, commit_dt.month, commit_dt.day,
                     commit_dt.hour, commit_dt.minute, commit_dt.second)

    def _member(arcname: str) -> zipfile.ZipInfo:
        zi = zipfile.ZipInfo(arcname, date_time=zip_date_time)
        zi.compress_type = zipfile.ZIP_DEFLATED
        zi.external_attr = 0o644 << 16   # fixed mode; never the host's umask
        zi.create_system = 3             # unix, regardless of build host
        return zi

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for rel in sorted(files):
            # EVERY read is from the materialized HEAD snapshot -- never HARNESS.
            # If this reverted to HARNESS the bundle would silently carry
            # worktree bytes again, and membership would still pass 451/451.
            src = source_root / rel
            if not src.is_file():
                # Submodule entry, broken symlink, or stale ls-tree row
                skipped += 1
                continue
            # Use forward slashes in archive (zip convention)
            arcname = rel.replace("\\", "/")
            payload: bytes
            if src.suffix.lower() == ".md":
                source_text = src.read_text(encoding="utf-8")
                if "<!-- include:" in source_text:
                    # Resolve against source_root so include TARGETS are HEAD
                    # bytes too; resolve_includes_in_text reads them from disk.
                    payload = resolve_includes_in_text(
                        source_text, src, source_root).encode("utf-8")
                else:
                    payload = src.read_bytes()
            else:
                payload = src.read_bytes()
            # One write path for every member: z.write() would reintroduce
            # host mtimes for the 444 non-rendered files.
            z.writestr(_member(arcname), payload)
            total_size += len(payload)

    bundle_size = output.stat().st_size
    print(f"\nBundle written: {output}")
    print(f"Source bytes:   {total_size:>12,}")
    print(f"Compressed:     {bundle_size:>12,}")
    if total_size > 0:
        print(f"Compression:    {bundle_size / total_size:.1%}")
    if skipped:
        print(f"Skipped (not a regular file): {skipped}")

    # Verify by reading back
    with zipfile.ZipFile(output) as z:
        names = z.namelist()
        print(f"Members in bundle: {len(names)}")
        for required in REQUIRED_FILES:
            if required in names:
                info = z.getinfo(required)
                print(f"  OK  {required}  ({info.file_size} bytes)")
            else:
                print(f"  [ERROR] missing from bundle: {required}", file=sys.stderr)
                return 1
        # Safety net: assert no nested archive survived.
        nested = [n for n in names if n.endswith(ARCHIVE_SUFFIXES)]
        if nested:
            print(f"[ERROR] nested archive file(s) in bundle: {nested}",
                  file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
