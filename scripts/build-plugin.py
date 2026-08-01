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

**Output.** The caller must provide `--out <external-directory>`. The bundle
is written there using the name from `.claude-plugin/plugin.json`; package and
governed consumer destinations are refused by the shared destination policy.

**Usage.**

    python scripts/build-plugin.py --out <external-directory>

Or with explicit interpreter UTF-8 mode on Windows hosts where stdlib defaults
to cp949 and the plugin tree carries §, →, em dashes, etc.:

    "C:\\Users\\<user>\\AppData\\Local\\Programs\\Python\\Launcher\\py.exe" \\
        -X utf8 scripts\\build-plugin.py --out <external-directory>

**Exit codes.**

    0  bundle written successfully
    1  required files missing from the tracked set, or a nested archive survived
    2  git failed (not a repo? HEAD missing?), or ls-tree and the worktree
       disagree on the population
    3  plugin.json missing or unparseable at the commit
    5  PROVENANCE.json does not describe the finished archive (readback failed)
    6  the child builder produced no bundle -- that commit's toolchain likely
       predates --build-here
    7  the build worktree could not be cleaned up: the environment is VOID
    8  environment, external-output, or post-build source-residue refusal

    (4 is retired: it belonged to the toolchain-drift check, which is gone --
     the builder now re-execs from a clean worktree, so drift is
     unrepresentable rather than detected.)

This contract had drifted: it still advertised 4 for a deleted path, omitted 5
and 6 entirely, and let cleanup failure escape as an uncaught RuntimeError ->
exit 1, i.e. an environmental VOID reported as "required files missing". Given
that component-specific exit semantics are the subject of this workstream, that
is contract drift, not documentation debt.

**Toolchain binding.** main() re-execs itself from a clean detached worktree at
HEAD (--build-here), so the executing builder IS the commit's builder. Nothing
is checked because nothing can differ.

**Provenance.** The bundle carries a deterministic PROVENANCE.json member
recording the commit, toolchain hashes, and the runtime plane, and the builder
reconciles that record against the finished archive before returning. Terminal
output is not provenance -- it scrolls away and the artifact is then
indistinguishable.
"""

from __future__ import annotations

import json
import contextlib
import datetime
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import destination_capability as destinations
from resolve_includes import resolve_includes_in_text
from qualification_environment import (
    QualificationEnvironmentRefusal,
    assert_ambient_clean,
    controlled_environment,
)
from qualification_plane_topology import capture_source_snapshot

# Resolve harness root from this script's location: scripts/build-plugin.py.
# No env override: COAUTHOR_BUILD_SOURCE_REPO was scaffolding for an abandoned
# re-exec and survived as an ambient authority that could silently point the
# builder at another repo, unreported and outside the declared planes.
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
# NOTE (closed 2026-07-16): scripts/release-gate.sh Phase 1 now builds the
# release zip by invoking THIS builder, so the former second population
# (worktree `zip -r` with exclusion globs) is retired and package_enumeration
# is the repo-wide population authority for both bundle paths.
from package_enumeration import (  # noqa: E402,F401
    ARCHIVE_SUFFIXES,
    enumerate_package_files,
    resolve_head,
)


class CleanupFailed(RuntimeError):
    """The build's environment could not be restored -> exit 7, not exit 1.

    An uncaught RuntimeError exits 1, which this script's own contract defines
    as "required files missing from the tracked set". An environmental VOID
    would have been read as a package defect -- exactly the ACQ/PRJ conflation
    audited elsewhere in this workstream, arriving through an exit code.
    """


@contextlib.contextmanager
def commit_worktree(commit: str):
    """Yield a CLEAN detached worktree at `commit`.

    This is what makes toolchain binding structural rather than checked.

    The drift CHECK it replaces was unsound: Python imports build-plugin.py,
    package_enumeration.py and resolve_includes.py BEFORE _toolchain_drift()
    re-reads those paths, so a dirty implementation already loaded in memory
    passes if its disk file is restored before the check -- and the record then
    hashes the committed files and asserts toolchain_matches_commit: true about
    code that never executed. It measured the disk, not the interpreter.

    Re-exec from a `git archive` snapshot failed earlier because the snapshot
    has no git context. A WORKTREE keeps it (.git is a file pointing at the
    main repo), so the child can resolve and enumerate normally. The worktree
    is also already the commit's content -- no tar, no second materialization.
    """
    path = Path(tempfile.mkdtemp(prefix="coauthor-build-plane-"))
    path.rmdir()  # git insists on creating it
    subprocess.run(
        [GIT, "-C", str(HARNESS), "worktree", "add", "--quiet", "--detach",
         str(path), commit],
        capture_output=True, check=True,
    )
    try:
        yield path
    finally:
        # Cleanup does NOT fail open. `git worktree remove` had no check=True
        # and the fallback rmtree was wrapped in suppress(OSError): an injected
        # removal failure let the build exit 0 -- the R-8 error (a reader/
        # environment failure VOIDS the verdict, it does not soften it), fixed
        # in the smoketest one commit earlier and still live here. It can also
        # strand git ADMIN state even when the directory is gone, which
        # `worktree prune` exists for.
        # FAILURE IS A BOOLEAN, NOT A MESSAGE.
        # This tracked failure in `err` and tested `if err:` -- so a git that
        # exits 1 with EMPTY stderr yielded err="" (falsy) and cleanup returned
        # success. Third time this workstream has shipped a fail-open: the
        # porcelain probe without check=True, ignore_errors=True on rmtree, and
        # now truthiness-on-a-message. The verdict must never depend on whether
        # a failure was chatty.
        failed = False
        reasons: list[str] = []

        rc = subprocess.run(
            [GIT, "-C", str(HARNESS), "worktree", "remove", "--force", str(path)],
            capture_output=True, text=True, encoding="utf-8",
            errors="strict",
        )
        if rc.returncode != 0:
            failed = True
            reasons.append(f"worktree remove exited {rc.returncode}: "
                           f"{(rc.stderr or '').strip() or '(no stderr)'}")
        if path.exists():
            def _on_error(func, p, _exc):
                os.chmod(p, 0o700)
                func(p)
            try:
                try:
                    shutil.rmtree(path, onexc=_on_error)
                except TypeError:
                    shutil.rmtree(path, onerror=lambda f, p, e: _on_error(f, p, e))
            except OSError as exc:
                failed = True
                reasons.append(f"rmtree: {exc}")
        # Reconcile git's ADMIN state whether or not the directory vanished --
        # and check it, since a prune that fails leaves a registered worktree
        # pointing at nothing.
        pr = subprocess.run([GIT, "-C", str(HARNESS), "worktree", "prune"],
                            capture_output=True, text=True, encoding="utf-8", errors="strict")
        if pr.returncode != 0:
            failed = True
            reasons.append(f"worktree prune exited {pr.returncode}: "
                           f"{(pr.stderr or '').strip() or '(no stderr)'}")
        if failed:
            raise CleanupFailed(
                f"build worktree cleanup failed for {path}: {'; '.join(reasons)}. "
                "The build is VOID: its environment could not be restored."
            )


def main() -> int:
    try:
        assert_ambient_clean()
    except QualificationEnvironmentRefusal as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 8
    try:
        out_index = sys.argv.index("--out")
        explicit_out = Path(sys.argv[out_index + 1]).resolve()
    except (ValueError, IndexError):
        print("[ERROR] --out <external-directory> is required; source-plane output is forbidden", file=sys.stderr)
        return 8
    try:
        output_class = destinations.assert_writable(
            explicit_out, purpose="isolated build-plane output",
        )
    except destinations.DestinationRefused as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 8
    if output_class != "external":
        print(
            "[ERROR] BUILD-OUTPUT-CLASS: isolated build plane requires an "
            f"external destination; got {output_class}",
            file=sys.stderr,
        )
        return 8

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
    # CHILD MODE: this process IS the commit's builder, running from a clean
    # detached worktree. Its own tree is the commit's content, so it reads
    # directly -- no snapshot, no drift check, nothing to verify. Mismatch is
    # unrepresentable rather than detected.
    if "--build-here" in sys.argv:
        return _build(head_sha, HARNESS, files, explicit_out)

    source_preimage = capture_source_snapshot(HARNESS)
    child_rc = 0
    with commit_worktree(head_sha) as wt:
        print(f"Toolchain:     re-exec from a clean worktree at {head_sha[:12]}")
        out_dir = explicit_out
        out_dir.mkdir(parents=True, exist_ok=True)
        before = {p: p.stat().st_mtime_ns for p in out_dir.glob("*.plugin")}
        # The detached child lives outside the governed workspace, so carry
        # forward only the additive governed-root set that made the parent's
        # destination classification possible. This preserves fail-closed
        # classification in the child without granting a new writable lane.
        governed_root_value = os.pathsep.join(
            str(root) for root in destinations.governed_roots(explicit_out)
        )
        child_env, _ = controlled_environment(delta={
            "COAUTHOR_EXTRA_GOVERNED_ROOTS": governed_root_value,
        })
        proc = subprocess.run([
            sys.executable, str(wt / "scripts" / "build-plugin.py"),
            "--build-here", "--out", str(out_dir),
        ], env=child_env)
        if proc.returncode != 0:
            child_rc = proc.returncode
        # The child MUST have written here. A commit whose builder predates
        # --build-here ignores the flag, builds into its own worktree, and exits
        # 0 -- the worktree is then deleted and the real bundle is silently
        # untouched. Observed exactly that during the transition. An exit code
        # is not evidence that the work happened.
        after = {p: p.stat().st_mtime_ns for p in out_dir.glob("*.plugin")}
        if child_rc == 0 and after == before:
            print(f"[ERROR] child at {head_sha[:12]} produced no bundle in {out_dir}; "
                  "that commit's builder likely predates --build-here. Build from a "
                  "commit whose toolchain supports worktree re-exec.", file=sys.stderr)
            child_rc = 6
    if capture_source_snapshot(HARNESS) != source_preimage:
        print("[ERROR] PLANE-SOURCE-RESIDUE: source changed during build before suite launch", file=sys.stderr)
        return 8
    return child_rc




TOOLCHAIN = (
    "scripts/build-plugin.py",
    "scripts/package_enumeration.py",
    "scripts/resolve_includes.py",
)


def _runtime_plane() -> dict:
    """The non-commit planes the archive's bytes actually depend on.

    ZIP_DEFLATED output depends on the zlib implementation, so the archive is a
    function of (commit + compression runtime). This goes INTO the artifact
    (see PROVENANCE member), not just the console: I transcribed the runtime by
    hand as "python=3.14.0rc2" when the interpreter was 3.14.2 -- console-
    transcribed provenance is unreliable evidence, demonstrated on itself.
    """
    import zlib
    return {
        "python": sys.version.split()[0],
        "python_full": sys.version.replace("\n", " "),
        "zlib": getattr(zlib, "ZLIB_RUNTIME_VERSION",
                        getattr(zlib, "ZLIB_VERSION", "unknown")),
        "compression": "ZIP_DEFLATED",
        "note": ("archive bytes are reproducible under THIS runtime; deflate "
                 "output is implementation-dependent, so cross-runtime purity "
                 "is not claimed"),
    }


def _build(head_sha: str, source_root: Path, files: list[str], out_dir: Path) -> int:
    print(f"Built from:    {head_sha[:12]} (clean worktree; this process IS the "
          "commit's builder)")

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
    output = out_dir / f"{plugin_name}.plugin"

    print(f"Harness root:  {HARNESS}")
    print(f"Plugin name:   {plugin_name}  (from {head_sha[:12]}, not the worktree)")
    print(f"Plugin ver:    {plugin_version} (manifest may be RC-deferred behind tag state)")
    print(f"Output:        {output}")

    # ls-tree and git archive are TWO population rules over the same commit.
    # They agree today, but `export-ignore` in .gitattributes would silently
    # make archive a subset -- membership from one rule, bytes from another.
    # Assert they match rather than assume it.
    # Not package content, each for a stated reason -- never a blanket filter:
    #   .git            worktree pointer FILE (not a dir, so rglob sees it)
    #   __pycache__/    bytecode this very process created by importing itself
    #   *.plugin/*.zip  dropped by the enumerator by design
    def _is_package_path(rel: str) -> bool:
        return not (rel == ".git"
                    or "__pycache__/" in f"{rel}/"
                    or rel.endswith(ARCHIVE_SUFFIXES))

    materialized = {
        p.relative_to(source_root).as_posix()
        for p in source_root.rglob("*") if p.is_file()
    }
    enumerated = set(files)
    only_enum = sorted(enumerated - materialized)
    only_mat = sorted(f for f in (materialized - enumerated) if _is_package_path(f))
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
        errors="strict",
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

        # BIND PROVENANCE TO THE ARTIFACT.
        #
        # Terminal output is not provenance: once stdout scrolls away, a
        # drifted archive is indistinguishable from a clean one. This
        # workstream recorded that defect twice (--allow-dirty's stderr stamp;
        # the toolchain WARN) and shipped it both times. The record therefore
        # goes INSIDE the zip.
        #
        # Deterministic by construction: sorted keys, the commit's timestamp,
        # no wall-clock. A provenance member that varied per build would break
        # the reproducibility it documents. Emitted LAST and excluded from the
        # enumeration checks -- it is metadata about the bundle, not a shipped
        # package file.
        # Two fields in the first version were FALSE ON ARRIVAL, because
        # nothing reconciled the record against the archive:
        #   member_count: 452  <- actual ZIP members 453 (forgot itself)
        #   zip_date_time: (..,19) <- stored (..,18): I VERIFIED DOS 2-second
        #                             quantization, wrote a test asserting it,
        #                             then recorded the unquantized value here.
        # A record whose purpose is to be trusted must be checked like anything
        # else. Hence distinct names for distinct populations, the QUANTIZED
        # stamp as actually stored, and a readback below.
        stored_dt = zip_date_time[:5] + (zip_date_time[5] & ~1,)
        provenance = {
            "schema": "coauthor-build-provenance/v1",
            "commit": head_sha,
            "enumerator": "scripts/package_enumeration.py::enumerate_package_files",
            # Distinct populations, distinct names: the package files enumerated
            # from the commit vs every member of the finished ZIP (which also
            # carries this record).
            "package_member_count": len(files) - skipped,
            "archive_member_count": len(files) - skipped + 1,
            "toolchain": {rel: hashlib.sha256((source_root / rel).read_bytes()).hexdigest()
                          for rel in TOOLCHAIN if (source_root / rel).is_file()},
            "toolchain_is_commit": True,   # structural: built from a clean
                                           # worktree at `commit`, not checked
            "runtime": _runtime_plane(),
            "zip_date_time_stored": list(stored_dt),
            "zip_date_time_commit": list(zip_date_time),
        }
        z.writestr(_member("PROVENANCE.json"),
                   json.dumps(provenance, indent=2, sort_keys=True).encode("utf-8"))

    # READBACK: reconcile the record against the FINISHED archive.
    # Without this, PROVENANCE.json shipped two false fields -- machine-readable
    # but never machine-verified is just a nicer-looking caveat.
    with zipfile.ZipFile(output) as z:
        rec = json.loads(z.read("PROVENANCE.json"))
        names = z.namelist()
        stamps = {i.date_time for i in z.infolist()}
        bad = []

        # CARDINALITY IS NOT CORRESPONDENCE. Counting members proves nothing
        # about WHICH members. Demonstrated: an archive with SECURITY.md deleted
        # and CONTRIBUTING.md duplicated passed every check here -- counts,
        # timestamps, required-files, nested-archive -- because the count was
        # right and the set was not. Assert the exact set, and uniqueness (a zip
        # may legally carry duplicate names; namelist() shows both, and a
        # count-only check cannot tell that from a distinct member).
        expected = sorted(files) + ["PROVENANCE.json"]
        if sorted(names) != sorted(expected):
            missing = sorted(set(expected) - set(names))
            extra = sorted(set(names) - set(expected))
            bad.append(f"member set != enumeration (missing {missing[:3]}, extra {extra[:3]})")
        if len(names) != len(set(names)):
            dupes = sorted({n for n in names if names.count(n) > 1})
            bad.append(f"duplicate member names: {dupes[:3]}")

        if rec["archive_member_count"] != len(names):
            bad.append(f"archive_member_count {rec['archive_member_count']} != {len(names)}")
        if rec["package_member_count"] != len(names) - 1:
            bad.append(f"package_member_count {rec['package_member_count']} != {len(names)-1}")
        if stamps != {tuple(rec["zip_date_time_stored"])}:
            bad.append(f"zip_date_time_stored {tuple(rec['zip_date_time_stored'])} "
                       f"not the stored stamp {sorted(stamps)}")
        if rec["commit"] != head_sha:
            bad.append("commit mismatch")
        # EVERY DEFINED FIELD IS CHECKED, AND KEY SETS ARE EXACT.
        #
        # The previous validator iterated `rec["toolchain"].items()` -- so it
        # only checked entries that HAPPENED TO BE PRESENT, and deleting the
        # resolve_includes.py entry passed. It also read only runtime.python and
        # runtime.zlib, leaving python_full and compression unchecked, and never
        # looked at `enumerator` or `toolchain_is_commit` at all. Verified: five
        # simultaneous tamperings (enumerator -> TOTALLY_FAKE,
        # toolchain_is_commit -> false, a toolchain entry removed, python_full
        # rewritten, compression -> ZIP_STORED) produced bad=[]. Iterating what
        # is there cannot detect what is missing -- the same shape as every
        # under-narrow population in this workstream.
        if rec.get("schema") != "coauthor-build-provenance/v1":
            bad.append(f"unknown schema {rec.get('schema')!r}")
        if rec.get("enumerator") != \
                "scripts/package_enumeration.py::enumerate_package_files":
            bad.append(f"enumerator {rec.get('enumerator')!r} is not this builder's")
        if rec.get("toolchain_is_commit") is not True:
            bad.append("toolchain_is_commit is not True")

        expected_tc = {rel for rel in TOOLCHAIN if (source_root / rel).is_file()}
        got_tc = set(rec.get("toolchain", {}))
        if got_tc != expected_tc:
            bad.append(f"toolchain key set {sorted(got_tc)} != {sorted(expected_tc)}")
        for rel in expected_tc:
            actual = hashlib.sha256((source_root / rel).read_bytes()).hexdigest()
            if rec.get("toolchain", {}).get(rel) != actual:
                bad.append(f"toolchain hash {rel} does not match the built tree")

        live = _runtime_plane()
        if set(rec.get("runtime", {})) != set(live):
            bad.append(f"runtime key set {sorted(rec.get('runtime', {}))} != {sorted(live)}")
        for k, v in live.items():
            if rec.get("runtime", {}).get(k) != v:
                bad.append(f"runtime.{k} does not match this process")

        # compression is a CLAIM about the archive; verify it against the members.
        actual_ct = {i.compress_type for i in z.infolist()}
        want_ct = {zipfile.ZIP_DEFLATED} if live["compression"] == "ZIP_DEFLATED" \
            else {zipfile.ZIP_STORED}
        if actual_ct != want_ct:
            bad.append(f"runtime.compression {live['compression']!r} but members "
                       f"use compress_type {sorted(actual_ct)}")

        if tuple(rec["zip_date_time_commit"])[:5] != tuple(rec["zip_date_time_stored"])[:5] or \
                (tuple(rec["zip_date_time_commit"])[5] & ~1) != tuple(rec["zip_date_time_stored"])[5]:
            bad.append("zip_date_time_stored is not the DOS-quantized commit stamp")
        if bad:
            print(f"[ERROR] PROVENANCE.json does not describe the archive: {bad}",
                  file=sys.stderr)
            return 5
    print("Provenance:    PROVENANCE.json readback reconciles with the archive")

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
    try:
        sys.exit(main())
    except CleanupFailed as exc:
        # Distinct exit: a VOID environment is not "required files missing".
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(7)
