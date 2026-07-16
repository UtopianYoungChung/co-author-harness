#!/usr/bin/env python3
"""build_plugin_provenance_smoketest - the bundle is an artifact of one commit.

HERMETIC. Every mutation case runs in a disposable clone under a temp dir; the
user's checkout is never written to. The first revision of this file ran
`git mv` and `git restore --staged` against the LIVE workspace, so pre-existing
staged work on SECURITY.md or CLAUDE.md could have been destroyed -- a test that
can corrupt the repo is worse than no test.

Guards the property membership checks cannot see. build-plugin.py takes paths
from `git ls-tree` and used to take BYTES from disk, so a bundle built from a
dirty worktree carried uncommitted content under a clean commit's file list
while 451/451 membership passed. Measured 2026-07-15:

    reviews/plugin_update_proposals.md
      ARCHIVE_EQ_HEAD     False    HEAD_SHA    421eae8d6462
      ARCHIVE_EQ_WORKTREE True     ARCHIVE_SHA b566860d962d

The first fix was a check-then-act dirty guard: it failed open (probe lacked
check=True), mis-parsed staged renames, and raced. Deleted, not repaired -- the
builder now materializes the commit via `git archive` and reads only from that
snapshot, so a dirty bundle is unrepresentable.

Run:  python scripts/build_plugin_provenance_smoketest.py
Exit: 0 all pass; 1 a case failed.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from contextlib import contextmanager
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HARNESS / "scripts"))

from package_enumeration import GIT  # noqa: E402
from resolve_includes import resolve_includes_in_text  # noqa: E402

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{(' - ' + detail) if detail else ''}")
    if not ok:
        FAILURES.append(name)


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _git(repo: Path, *args: str, check_rc: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run([GIT, "-C", str(repo), *args],
                          capture_output=True, text=True, encoding="utf-8", check=check_rc)


def _head_blob(repo: Path, rel: str) -> bytes | None:
    r = subprocess.run([GIT, "-C", str(repo), "show", f"HEAD:{rel}"], capture_output=True)
    return r.stdout if r.returncode == 0 else None


def _rmtree_force(path: Path, attempts: int = 6) -> None:
    """rmtree that survives read-only git objects AND transient Windows handles.

    Two distinct failure modes, fixed in two rounds:

    * `ignore_errors=True` silently gave up on read-only .git/objects and left
      4 sandboxes behind -- a cleanup that ignores errors is a leak with a
      comment on it. Fixed by chmod-and-retry in the error hook.
    * That still flaked: an independent run hit PermissionError [WinError 32]
      ("used by another process") and left 1 sandbox, while my single run
      reported zero. The directory vanished after the process exited, so the
      handle was transient -- git/AV/indexer holding a file for a few
      milliseconds. A one-shot delete cannot see that; ONE PASSING RUN IS NOT
      EVIDENCE OF A STABLE TEST.

    Hence bounded retry with backoff, and the outcome is still not ignored: if
    every attempt fails the exception propagates.
    """
    def _on_error(func, p, _exc):
        os.chmod(p, 0o700)
        func(p)

    if not path.exists():
        return
    delay = 0.05
    for attempt in range(1, attempts + 1):
        try:
            try:
                shutil.rmtree(path, onexc=_on_error)      # py3.12+
            except TypeError:
                shutil.rmtree(path, onerror=lambda f, p, e: _on_error(f, p, e))
            return
        except (PermissionError, OSError):
            if attempt == attempts:
                raise
            time.sleep(delay)
            delay *= 2


_SHARED: dict[str, Path] = {}


@contextmanager
def sandbox(destructive: bool = False):
    """A disposable clone of the harness. All mutation happens HERE, never in
    the user's checkout.

    Non-destructive cases REUSE one clone and reset it between cases: cloning
    per case ran the suite in 139s, most of it `git clone`. `reset --hard` +
    `clean -fdx` restores the fixture to HEAD, and the builder-under-test
    overlay is re-applied afterwards (clean -fdx would otherwise delete it,
    since it is untracked relative to the sandbox's HEAD).

    `destructive=True` gets its OWN throwaway clone -- the git-failure case
    deletes .git, which no reset can undo.
    """
    # Sandbox lives on the SAME DRIVE as the repo but OUTSIDE its tree.
    #
    # Same drive: `git clone --local` hardlinks the object store, and hardlinks
    # cannot cross volumes -- cloning B:\ into C:\Users\...\Temp dies with
    # `fatal: failed to create link ... Improper link` (exit 128).
    # --no-hardlinks works cross-drive but deep-copies a 6 MB object store per
    # case, which made the suite unusably slow.
    #
    # Outside the tree: a sandbox under HARNESS/.worktrees/ is NOT isolated,
    # because git discovery WALKS UP. Deleting the sandbox's .git (the
    # failure-injection case) made git find the PARENT repo instead of failing,
    # so the builder half-succeeded and died on a tar ReadError rather than
    # aborting cleanly. Nesting a fixture repo inside a real one is not a
    # sandbox.
    base = HARNESS.parent / ".coauthor-provenance-sbx"
    base.mkdir(exist_ok=True)

    if not destructive and "repo" in _SHARED:
        repo = _SHARED["repo"]
        # Restore to HEAD. clean -fdx also removes the previous overlay and any
        # bundle, so the next case starts from commit content exactly.
        _git(repo, "reset", "--hard", "--quiet")
        _git(repo, "clean", "-qfdx")
        _overlay(repo)
        yield repo
        return

    tmp = Path(tempfile.mkdtemp(prefix="sbx-", dir=str(base)))
    try:
        repo = tmp / "repo"
        # The sandbox only READS objects and is never gc'd, so sharing them is
        # safe.
        subprocess.run([GIT, "clone", "--quiet", "--local", str(HARNESS), str(repo)],
                       capture_output=True, check=True)
        # Match the source HEAD exactly (clone follows the default branch).
        head = _git(HARNESS, "rev-parse", "HEAD").stdout.strip()
        _git(repo, "checkout", "--quiet", "--detach", head)
        _overlay(repo)
        if not destructive:
            _SHARED["repo"] = repo
            _SHARED["tmp"] = tmp
            yield repo
            return  # teardown deferred to teardown_shared()
        yield repo
    finally:
        if destructive or "repo" not in _SHARED:
            _rmtree_force(tmp)


def teardown_shared() -> None:
    tmp = _SHARED.pop("tmp", None)
    _SHARED.pop("repo", None)
    if tmp:
        _rmtree_force(tmp)


def _final_teardown() -> None:
    """Release the shared clone and assert nothing survived.

    Lives in main()'s outer `finally` (see __main__): a case that raises must
    not skip teardown and strand a sandbox. The leak assertion runs AFTER
    teardown, so it measures the end state rather than a hopeful one.
    """
    base = HARNESS.parent / ".coauthor-provenance-sbx"
    try:
        teardown_shared()
    except Exception as exc:  # noqa: BLE001
        check("shared teardown succeeds", False, f"{type(exc).__name__}: {exc}")
    leftover = sorted(p.name for p in base.glob("sbx-*")) if base.is_dir() else []
    check("suite leaves no sandbox behind", not leftover,
          f"{len(leftover)} left: {leftover[:2]}")
    with contextlib.suppress(OSError):
        base.rmdir()


def _overlay(repo: Path) -> None:
    """Copy the BUILDER UNDER TEST from the working tree into the sandbox.

    Without this the sandbox runs HEAD's builder, so the suite tests the
    committed code rather than the change under review -- and it reported
    exactly that: every provenance case failed against e4a23c7, whose builder
    still read worktree bytes. Correct results, wrong subject.

    Deliberately narrow and listed, not globbed: these are the three modules
    that decide provenance. Everything else stays at HEAD, so the fixtures the
    builder reads are commit content -- only the tool is current.

    The overlay makes the sandbox dirty by construction. That is the point: a
    builder reading HEAD bytes is unaffected by it, which is what these cases
    assert.
    """
    for rel in ("scripts/build-plugin.py",
                "scripts/package_enumeration.py",
                "scripts/resolve_includes.py"):
        shutil.copy2(HARNESS / rel, repo / rel)


def build(repo: Path) -> tuple[int, Path, str]:
    r = subprocess.run([sys.executable, str(repo / "scripts" / "build-plugin.py")],
                       capture_output=True, text=True, encoding="utf-8")
    return r.returncode, repo / ".claude-plugin" / "co-author-harness-claude.plugin", (r.stdout + r.stderr)


def case_clean_build_equals_head() -> None:
    """Every member equals its HEAD blob, modulo the builder's DECLARED
    include-rendering -- re-run, never assumed ("6 diffs, probably fine" is not
    an assertion)."""
    with sandbox() as repo:
        rc, out, _ = build(repo)
        check("clean: builder exits 0", rc == 0)
        if rc != 0:
            return
        bad: list[str] = []
        # `with`: an unclosed ZipFile holds a Windows file lock, so the
        # sandbox teardown died with PermissionError [WinError 32] -- a leaked
        # handle masquerading as a test failure.
        with zipfile.ZipFile(out) as z:
            for n in z.namelist():
                a = z.read(n)
                h = _head_blob(repo, n)
                if h is None:
                    bad.append(f"{n}:not-in-HEAD")
                    continue
                if _sha(a) == _sha(h):
                    continue
                try:
                    rendered = resolve_includes_in_text(h.decode("utf-8"), Path(n), repo)
                    if rendered.encode("utf-8") != a:
                        bad.append(f"{n}:differs-beyond-rendering")
                except Exception as exc:  # noqa: BLE001
                    bad.append(f"{n}:render-{type(exc).__name__}")
        check("clean: archive == HEAD modulo declared rendering", not bad,
              f"{len(bad)} unexplained: {bad[:3]}")


def case_dirty_unstaged_ignored() -> None:
    with sandbox() as repo:
        victim = "README.md"
        (repo / victim).write_bytes(_head_blob(repo, victim) + b"\n<!-- UNSTAGED PROBE -->\n")
        rc, out, _ = build(repo)
        check("unstaged: builder exits 0", rc == 0)
        if rc != 0:
            return
        arch = zipfile.ZipFile(out).read(victim)
        check("unstaged: member == HEAD, not worktree", _sha(arch) == _sha(_head_blob(repo, victim)))
        check("unstaged: probe text absent", b"UNSTAGED PROBE" not in arch)


def case_dirty_staged_ignored() -> None:
    with sandbox() as repo:
        victim = "CLAUDE.md"
        (repo / victim).write_bytes(_head_blob(repo, victim) + b"\n<!-- STAGED PROBE -->\n")
        _git(repo, "add", victim)
        rc, out, _ = build(repo)
        check("staged: builder exits 0", rc == 0)
        if rc != 0:
            return
        arch = zipfile.ZipFile(out).read(victim)
        check("staged: member == HEAD, not index", _sha(arch) == _sha(_head_blob(repo, victim)))
        check("staged: probe text absent", b"STAGED PROBE" not in arch)


def case_staged_rename_ignored() -> None:
    """The deleted guard parsed `R  old -> new` into the path "old -> new",
    intersecting nothing, so renames were invisible. Materialization is immune
    by construction; pin it."""
    with sandbox() as repo:
        _git(repo, "mv", "SECURITY.md", "SECURITY_RENAMED.md")
        rc, out, _ = build(repo)
        check("rename: builder exits 0", rc == 0)
        if rc != 0:
            return
        names = zipfile.ZipFile(out).namelist()
        check("rename: HEAD path still shipped", "SECURITY.md" in names)
        check("rename: renamed path NOT shipped", "SECURITY_RENAMED.md" not in names)


def case_manifest_from_snapshot() -> None:
    """A dirty plugin.json must not rename the output or misreport the version.

    It was parsed from the worktree before materialization -- worktree state
    leaking into a commit artifact through the one file that names it.
    """
    with sandbox() as repo:
        rel = ".claude-plugin/plugin.json"
        import json as _json
        manifest = _json.loads(_head_blob(repo, rel).decode("utf-8"))
        manifest["name"] = "HIJACKED-NAME"
        manifest["version"] = "99.99.99"
        (repo / rel).write_text(_json.dumps(manifest), encoding="utf-8")
        rc, out, log = build(repo)
        check("dirty manifest: builder exits 0", rc == 0, log.strip().splitlines()[-1] if rc else "")
        if rc != 0:
            return
        check("dirty manifest: output name from HEAD, not worktree", out.is_file(),
              "expected co-author-harness-claude.plugin")
        check("dirty manifest: hijacked name not used",
              not (repo / ".claude-plugin" / "HIJACKED-NAME.plugin").exists())
        check("dirty manifest: hijacked version not reported", "99.99.99" not in log)


def case_git_failure_fails_closed() -> None:
    """REAL failure injection, not a source grep.

    The prior version asserted `"check=True" in <source text>` -- a PRESENCE
    check, inside the very smoketest written to prove execution over presence.
    It could pass while the runtime path was broken. This actually breaks git:
    a PATH shim that exits non-zero. The builder must abort, never emit a
    bundle from an empty-but-successful git result.
    """
    # destructive=True: its OWN clone. Deleting .git is not undoable by reset,
    # so it must never touch the shared fixture.
    with sandbox(destructive=True) as repo:
        out = repo / ".claude-plugin" / "co-author-harness-claude.plugin"
        if out.exists():
            out.unlink()
        # Destroy the repository: every git call the builder makes now fails.
        # A PATH shim did NOT work -- find_git() prefers the absolute Windows
        # git path, so the shim was never consulted and the case reported a
        # false FAIL. (The first version was worse: it asserted `"check=True" in
        # <source text>` -- a presence check, inside the suite written to prove
        # execution over presence.)
        _rmtree_force(repo / ".git")
        r = subprocess.run([sys.executable, str(repo / "scripts" / "build-plugin.py")],
                           capture_output=True, text=True, encoding="utf-8")
        check("git failure: builder aborts (nonzero)", r.returncode != 0, f"rc={r.returncode}")
        check("git failure: no bundle emitted", not out.exists())
        check("git failure: error names the cause", "ERROR" in (r.stdout + r.stderr),
              (r.stdout + r.stderr).strip().splitlines()[-1][:80] if (r.stdout + r.stderr) else "silent")


def case_byte_reproducible() -> None:
    """Two builds of one SHA must be byte-identical WHOLE-ARCHIVE.

    "451 members, zero unexplained content differences" was true while the
    archive was NOT reproducible: 2F2C179D1A30 vs 0C0B32EBF6A1. `writestr()`
    stamped ambient wall-clock and `write()` copied extracted mtimes, giving
    three distinct ZIP timestamps -- and the 7 rendered members landed on two
    different seconds inside a single build. Content-faithful is a weaker claim
    than reproducible; this case is the difference.
    """
    with sandbox() as repo:
        rc1, out, _ = build(repo)
        check("repro: first build exits 0", rc1 == 0)
        if rc1 != 0:
            return
        first = out.read_bytes()
        out.unlink()
        rc2, out, _ = build(repo)
        check("repro: second build exits 0", rc2 == 0)
        if rc2 != 0:
            return
        second = out.read_bytes()
        check("repro: whole-archive bytes identical across builds",
              _sha(first) == _sha(second),
              f"{_sha(first)[:12]} vs {_sha(second)[:12]}")
        # SCOPE: this proves SAME-RUNTIME reproducibility, not environment-
        # independent purity. ZIP_DEFLATED bytes depend on the zlib
        # implementation, so the archive is a function of
        # (commit + compression runtime). Recorded, not asserted -- claiming
        # cross-environment purity would be the kind of unearned adjective this
        # workstream keeps producing ("conservative", "durable", "the
        # authority").
        print(f"      [runtime plane] python={sys.version.split()[0]} "
              f"zlib={_zlib_plane()}")
        with zipfile.ZipFile(out) as z:
            stamps = {i.date_time for i in z.infolist()}
            modes = {i.external_attr for i in z.infolist()}
        check("repro: one ZIP timestamp for all members", len(stamps) == 1,
              f"{len(stamps)} distinct: {sorted(stamps)[:3]}")
        # ZIP stores DOS time at 2-SECOND resolution, so an odd commit second
        # rounds DOWN (verified: 13 -> 12, 15 -> 14). The stamp is still a pure
        # function of the commit; compare quantized rather than loosening the
        # assertion to "close enough".
        expected = _commit_date_time(repo)
        expected_q = expected[:5] + (expected[5] & ~1,)
        check("repro: timestamp is the COMMIT's (DOS 2s-quantized), not the build's",
              stamps == {expected_q},
              f"members={sorted(stamps)[:1]} expected={expected_q} (commit {expected})")
        check("repro: uniform member permissions", len(modes) == 1, f"{len(modes)} distinct")


def _zlib_plane() -> str:
    """The compression implementation the archive's bytes depend on."""
    import zlib
    return getattr(zlib, "ZLIB_RUNTIME_VERSION", getattr(zlib, "ZLIB_VERSION", "?"))


def _commit_date_time(repo: Path) -> tuple:
    import datetime as _dt
    epoch = int(_git(repo, "show", "-s", "--format=%ct", "HEAD").stdout.strip())
    d = _dt.datetime.fromtimestamp(epoch, _dt.timezone.utc)
    return (d.year, d.month, d.day, d.hour, d.minute, d.second)


def case_no_temp_leak() -> None:
    before = {p.name for p in Path(tempfile.gettempdir()).glob("coauthor-*")}
    with sandbox() as repo:
        build(repo)
    after = {p.name for p in Path(tempfile.gettempdir()).glob("coauthor-*")}
    check("no tempdir leak", not (after - before), f"leaked: {sorted(after - before)[:3]}")


def main() -> int:
    print("build_plugin_provenance_smoketest (hermetic)")
    print(f"  source HEAD: {_git(HARNESS, 'rev-parse', '--short', 'HEAD').stdout.strip()}")
    print("  all mutations run in disposable clones; the checkout is never written\n")
    for fn in (
        case_clean_build_equals_head,
        case_dirty_unstaged_ignored,
        case_dirty_staged_ignored,
        case_staged_rename_ignored,
        case_manifest_from_snapshot,
        case_byte_reproducible,
        case_git_failure_fails_closed,
        case_no_temp_leak,
    ):
        print(f"{fn.__name__}:")
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            check(fn.__name__, False, f"raised {type(exc).__name__}: {exc}")
        print()
    if FAILURES:
        print(f"FAIL: {len(FAILURES)} case(s): {FAILURES}")
        return 1
    print("PASS: bundle is commit-faithful and same-runtime reproducible "
          "under every probed condition")
    return 0


if __name__ == "__main__":
    # Teardown in an OUTER finally: a case that raises must not strand a
    # sandbox. An earlier revision called it inline after the loop, so any
    # escape skipped it.
    try:
        _rc = main()
    finally:
        _final_teardown()
    sys.exit(1 if FAILURES else _rc)
