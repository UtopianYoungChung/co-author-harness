#!/usr/bin/env python3
"""build_plugin_provenance_smoketest - the bundle is an artifact of one commit.

HERMETIC. Every mutation case runs in a disposable clone under a temp dir; the
user's checkout is never written to. The first revision of this file ran
`git mv` and `git restore --staged` against the LIVE workspace, so pre-existing
staged work on SECURITY.md or AGENTS.md could have been destroyed -- a test that
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
import json
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
from worktree_paths import sandbox_base  # noqa: E402

# ONE sandbox base for every worktree layout, derived from git's COMMON dir
# (see worktree_paths). Previously `HARNESS.parent / ".coauthor-provenance-sbx"`
# -- outside the repo only for the primary checkout. From a worktree under
# `co-author-harness/.worktrees/<name>` the base landed INSIDE the primary
# repository, so case_git_failure_fails_closed's .git deletion let git discovery
# walk up to the real repo and the builder SUCCEEDED: all three git-failure
# assertions failed. Computed once, at import, so no case can diverge.
SBX_BASE = sandbox_base(HARNESS, ".coauthor-provenance-sbx")

FAILURES: list[str] = []   # predicate failures -> the SUBJECT is wrong (exit 1)
ERRORS: list[str] = []     # environment failures -> the RUN IS VOID  (exit 2)


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{(' - ' + detail) if detail else ''}")
    if not ok:
        FAILURES.append(name)


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _git(repo: Path, *args: str, check_rc: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run([GIT, "-C", str(repo), *args],
                          capture_output=True, text=True, encoding="utf-8", errors="strict", check=check_rc)


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
_EXTERNAL_OUTPUT_BASE = Path(tempfile.gettempdir()) / "coauthor-build-provenance-smoke"


def _external_output_dir(repo: Path) -> Path:
    """Stable per-sandbox output outside every governed workspace root."""
    token = hashlib.sha256(str(repo.resolve()).encode("utf-8")).hexdigest()[:16]
    return _EXTERNAL_OUTPUT_BASE / token


def _cleanup_external_output(repo: Path) -> None:
    out_dir = _external_output_dir(repo)
    if out_dir.exists():
        _rmtree_force(out_dir)
    with contextlib.suppress(OSError):
        _EXTERNAL_OUTPUT_BASE.rmdir()


class SandboxEnvironmentError(RuntimeError):
    """The sandbox INFRASTRUCTURE broke -- an ACQ-* fact about the reader's
    environment, never a PRJ-* fact about the builder. Callers must route this
    to ERRORS (run VOID, exit 2), not FAILURES (subject wrong, exit 1)."""


def _reset_shared(repo: Path, attempts: int = 6) -> bool:
    """Restore the shared clone to HEAD; False if it cannot be restored.

    `reset --hard` + `clean -qfdx` must delete the previous case's untracked
    output (the built bundle, __pycache__). Measured 2026-07-22: git clean
    fails in ~0.15s with NO internal retry when an external handle (AV or
    indexer under fresh-file churn -- the machine state right after a full
    fixture-corpus run) blocks one unlink: "failed to remove ...: Invalid
    argument", exit 1. One-shot check=True turned that into nine consecutive
    case failures reported as PROVENANCE failures -- infrastructure noise
    masquerading as a contract breach, the exact collapse _verdict() exists
    to prevent. Same bounded-retry shape as _rmtree_force, and for the same
    reason; the caller falls back to a fresh clone when the fixture is
    genuinely unrestorable.
    """
    delay = 0.05
    last = ""
    for attempt in range(1, attempts + 1):
        r = _git(repo, "reset", "--hard", "--quiet", check_rc=False)
        if r.returncode == 0:
            r = _git(repo, "clean", "-qfdx", check_rc=False)
            if r.returncode == 0:
                return True
        last = (r.stderr or "").strip()
        if attempt < attempts:
            time.sleep(delay)
            delay *= 2
    print(f"  note  shared-sandbox reset failed after {attempts} attempts "
          f"({last[:120]!r}) -- discarding the clone, using a fresh one")
    return False


@contextmanager
def sandbox(destructive: bool = False):
    """A disposable clone of the harness. All mutation happens HERE, never in
    the user's checkout.

    Non-destructive cases REUSE one clone and reset it between cases: cloning
    per case ran the suite in 139s, most of it `git clone`. `reset --hard` +
    `clean -fdx` restores the fixture to the sandbox HEAD (builder under
    test, committed by _commit_builder_under_test). The overlay is
    re-applied afterwards so the parent stays the working-tree tool; the
    child remains the sandbox commit.

    `destructive=True` gets its OWN throwaway clone -- the git-failure case
    deletes .git, which no reset can undo.
    """
    # Same drive, outside EVERY worktree -- derived from git's common dir and
    # asserted against git's own worktree registry. See worktree_paths and
    # SBX_BASE above; the requirement was documented here long before the
    # computation actually satisfied it under `.worktrees/`.
    base = SBX_BASE
    base.mkdir(exist_ok=True)

    if not destructive and "repo" in _SHARED:
        repo = _SHARED["repo"]
        # Restore to HEAD. clean -fdx also removes the previous overlay and any
        # bundle, so the next case starts from commit content exactly.
        if _reset_shared(repo):
            _overlay(repo)
            try:
                yield repo
            finally:
                _cleanup_external_output(repo)
            return
        # Unrestorable fixture: discard it and fall through to the fresh-clone
        # path below. If even the discard fails, that is an environment fact
        # (run VOID), never a provenance verdict.
        stale = _SHARED.pop("tmp", None)
        _SHARED.pop("repo", None)
        if stale is not None:
            try:
                _rmtree_force(stale)
            except OSError as exc:
                raise SandboxEnvironmentError(
                    f"could not discard unrestorable shared sandbox {stale.name}: "
                    f"{type(exc).__name__}: {exc}") from exc

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
        _commit_builder_under_test(repo)
        if not destructive:
            _SHARED["repo"] = repo
            _SHARED["tmp"] = tmp
            try:
                yield repo
            finally:
                _cleanup_external_output(repo)
            return  # teardown deferred to teardown_shared()
        try:
            yield repo
        finally:
            _cleanup_external_output(repo)
    finally:
        if destructive or "repo" not in _SHARED:
            _rmtree_force(tmp)


def teardown_shared() -> None:
    tmp = _SHARED.pop("tmp", None)
    _SHARED.pop("repo", None)
    if tmp:
        _rmtree_force(tmp)


def _sweep_stale_bases() -> int:
    """Remove sandboxes stranded by an earlier run. Returns how many.

    Teardown can lose a race with an external file handle (see
    _final_teardown). Rather than leave debris forever, each run sweeps first --
    by then any transient holder is long gone.
    """
    base = SBX_BASE
    if not base.is_dir():
        return 0
    swept = 0
    for stale in base.glob("sbx-*"):
        try:
            _rmtree_force(stale)
            swept += 1
        except OSError:
            pass
    return swept


def _final_teardown() -> None:
    """Release the shared clone; report leftovers as ENVIRONMENT, not contract.

    Runs from an outer `finally` (see __main__): a case that raises must not
    strand a sandbox, and the leak check must measure the end state.

    A stranded sandbox is NOT a provenance failure and must not fail the
    provenance verdict. Measured: teardown lost to a transient handle on
    skills/run-phase-3/SKILL.md -- a file the builder had read -- which
    outlived a ~3.2s retry budget and then deleted cleanly seconds later
    (AV/indexer, not a leak). Failing the suite for that trains people to
    ignore a red suite, which is worse than the debris.

    This is the ACQ-* / PRJ-* distinction from the acquisition contract, one
    layer out: "I could not delete a temp dir" is a fact about the READER's
    environment; "the builder shipped worktree bytes" is a fact about the
    SUBJECT. Collapsing them lets infrastructure noise masquerade as a contract
    breach -- and lets a real breach hide in noise.
    """
    base = SBX_BASE
    try:
        teardown_shared()
    except OSError as exc:
        ERRORS.append(f"teardown: {type(exc).__name__}: {exc}")
    leftover = sorted(p.name for p in base.glob("sbx-*")) if base.is_dir() else []
    if leftover:
        ERRORS.append(f"{len(leftover)} sandbox(es) stranded: {leftover[:2]}")
        print(f"  ERROR  environment: {len(leftover)} sandbox(es) stranded: "
              f"{leftover[:2]} -- run VOID, swept next run")
    else:
        print("  ok     no sandbox left behind")
    with contextlib.suppress(OSError):
        base.rmdir()


OVERLAY_RELS = (
    "scripts/build-plugin.py",
    "scripts/package_enumeration.py",
    "scripts/resolve_includes.py",
    "scripts/destination_capability.py",
    "scripts/qualification_environment.py",
    "scripts/qualification_plane_topology.py",
)


def _overlay(repo: Path) -> None:
    """Copy the BUILDER UNDER TEST from the working tree into the sandbox.

    Without this the sandbox parent is HEAD's builder. Overlay alone is
    uncommitted: the child is `git worktree add` of HEAD, and source HEAD's
    builder still treats `.claude-plugin/plugin.json` as identity (exit 3).
    A HEAD clone of this repo has version.json + root plugin.json and does
    not have the retired pack -- fixtures must not plant a fake pack.

    Deliberately narrow and listed, not globbed. Everything else stays at
    the sandbox commit, so package bytes are commit content.

    The overlay makes the parent dirty by construction. That is the point of
    case_child_is_committed_builder: a child reading HEAD bytes is unaffected.
    """
    for rel in OVERLAY_RELS:
        shutil.copy2(HARNESS / rel, repo / rel)


def _commit_builder_under_test(repo: Path) -> None:
    """Commit the overlay so re-exec runs the builder under test.

    Source HEAD still fail-closes on the missing pack. Peer/HEAD-clone
    fixtures use version.json (authority) + root plugin.json (host
    metadata) by making the retargeted builder the sandbox HEAD.
    """
    _overlay(repo)
    for rel in OVERLAY_RELS:
        _git(repo, "add", "--", rel)
    staged = _git(repo, "diff", "--cached", "--name-only")
    if not staged.stdout.strip():
        return
    _git(repo, "-c", "user.name=sbx", "-c", "user.email=sbx@localhost",
         "-c", "commit.gpgsign=false",
         "commit", "--quiet", "-m", "sbx: builder under test")


def build(repo: Path) -> tuple[int, Path, str]:
    out_dir = _external_output_dir(repo)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "co-author-harness.plugin"
    out.unlink(missing_ok=True)
    r = subprocess.run([sys.executable, str(repo / "scripts" / "build-plugin.py"),
                        "--out", str(out_dir)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, out, (r.stdout + r.stderr)


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
            # PROVENANCE.json is the builder's DECLARED metadata member
            # ("metadata about the bundle, not a shipped package file" --
            # build-plugin.py), so it is exempt from HEAD-equality. Not a
            # silent skip: it must exist and must name this sandbox's commit.
            # This case predates the member and was red at HEAD (found
            # 2026-07-16: 'PROVENANCE.json:not-in-HEAD') -- the emission
            # commit never re-ran the clean case.
            names = z.namelist()
            check("clean: PROVENANCE.json member present", "PROVENANCE.json" in names)
            if "PROVENANCE.json" in names:
                rec = json.loads(z.read("PROVENANCE.json"))
                head = _git(repo, "rev-parse", "HEAD").stdout.strip()
                check("clean: provenance names the sandbox's commit",
                      rec.get("commit") == head,
                      f"rec {str(rec.get('commit'))[:12]} vs HEAD {head[:12]}")
            for n in names:
                if n == "PROVENANCE.json":
                    continue
                a = z.read(n)
                h = _head_blob(repo, n)
                if h is None:
                    bad.append(f"{n}:not-in-HEAD")
                    continue
                if _sha(a) == _sha(h):
                    continue
                try:
                    rendered = resolve_includes_in_text(h.decode("utf-8", errors="strict"), Path(n), repo)
                    if rendered.encode("utf-8") != a:
                        bad.append(f"{n}:differs-beyond-rendering")
                except Exception as exc:  # noqa: BLE001
                    bad.append(f"{n}:render-{type(exc).__name__}")
        check("clean: archive == HEAD modulo declared rendering", not bad,
              f"{len(bad)} unexplained: {bad[:3]}")


def case_external_output_required() -> None:
    with sandbox() as repo:
        source_bundle = repo / ".claude-plugin" / "co-author-harness.plugin"
        source_bundle.unlink(missing_ok=True)
        missing = subprocess.run(
            [sys.executable, str(repo / "scripts" / "build-plugin.py")],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        check("external output: omitted --out is refused", missing.returncode == 8,
              f"rc={missing.returncode}")
        inside = subprocess.run(
            [sys.executable, str(repo / "scripts" / "build-plugin.py"),
             "--out", str(repo / ".claude-plugin")],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        check("external output: source-contained --out is refused", inside.returncode == 8,
              f"rc={inside.returncode}")
        with tempfile.TemporaryDirectory(prefix="coauthor-governed-destination-") as governed_td:
            governed = Path(governed_td)
            routing = governed / "governance" / "output-routing" / "output_routing.yaml"
            routing.parent.mkdir(parents=True)
            routing.write_text("schema_version: fixture\n", encoding="utf-8")
            protected = governed / "research" / "protected-build-output"
            refused = subprocess.run(
                [sys.executable, str(repo / "scripts" / "build-plugin.py"),
                 "--out", str(protected)],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            refusal_log = refused.stdout + refused.stderr
            check("external output: governed protected destination is refused",
                  refused.returncode == 8 and "DEST-PROTECTED" in refusal_log,
                  f"rc={refused.returncode}; log={refusal_log.strip()[-120:]}")
            check("external output: protected refusal occurs before mkdir/write",
                  not protected.exists())
        check("external output: refusals leave no source artifact", not source_bundle.exists())


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
        victim = "AGENTS.md"
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
    """A dirty version.json must not rename the output or misreport the version.

    It was parsed from the worktree before materialization -- worktree state
    leaking into a commit artifact through the one file that names it.
    """
    with sandbox() as repo:
        rel = "version.json"
        import json as _json
        manifest = _json.loads(_head_blob(repo, rel).decode("utf-8", errors="strict"))
        manifest["name"] = "HIJACKED-NAME"
        manifest["version"] = "99.99.99"
        (repo / rel).write_text(_json.dumps(manifest), encoding="utf-8")
        rc, out, log = build(repo)
        check("dirty manifest: builder exits 0", rc == 0, log.strip().splitlines()[-1] if rc else "")
        if rc != 0:
            return
        check("dirty manifest: output name from HEAD, not worktree", out.is_file(),
              "expected co-author-harness.plugin")
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
        out_dir = _external_output_dir(repo)
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / "co-author-harness.plugin"
        if out.exists():
            out.unlink()
        # Destroy the repository: every git call the builder makes now fails.
        # A PATH shim did NOT work -- find_git() prefers the absolute Windows
        # git path, so the shim was never consulted and the case reported a
        # false FAIL. (The first version was worse: it asserted `"check=True" in
        # <source text>` -- a presence check, inside the suite written to prove
        # execution over presence.)
        _rmtree_force(repo / ".git")
        r = subprocess.run([sys.executable, str(repo / "scripts" / "build-plugin.py"),
                            "--out", str(out_dir)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
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


def case_reset_survives_transient_handle() -> None:
    """The inter-case shared-sandbox reset must survive a transient external
    handle on an untracked file it has to delete.

    Measured 2026-07-22 (baseline receipt,
    research_notes/2026-07-22_producer-boundary_phase-a_baseline.md): after a
    full fixture-corpus run, `clean -qfdx` in this reset exited 1 for nine
    consecutive cases -- an external holder (AV/indexer under fresh-file
    churn) blocking deletion of the previous case's untracked output -- then
    the identical suite passed 3/3 once the machine went idle. A one-shot
    reset cannot see that; _rmtree_force learned the same lesson for rmtree.
    This injects the exact shape deterministically: an open handle without
    FILE_SHARE_DELETE on an untracked file, released ~1.5s later, must not
    produce a case failure.
    """
    if os.name != "nt":
        print("  SKIP  handle-based injection is Windows-only; retry path "
              "exercised only where deletion can actually be blocked")
        return
    import threading
    with sandbox():
        pass  # ensure the shared clone exists before we plant the probe
    victim = _SHARED["repo"] / "TRANSIENT_HOLD.tmp"
    victim.write_bytes(b"untracked probe\n")
    # CPython opens without FILE_SHARE_DELETE, so git's unlink gets a sharing
    # violation. Measured: `clean -qfdx` fails in ~0.15s with NO internal
    # retry ("failed to remove ...: Invalid argument", exit 1). The hold must
    # outlive the `reset --hard` step (~0.3-0.5s on this clone) or it releases
    # before clean runs and the injection tests nothing.
    handle = open(victim, "rb")
    threading.Timer(1.5, handle.close).start()
    try:
        with sandbox() as repo:  # enters the reset path while the handle is held
            check("transient handle: reset survived and fixture restored",
                  not (repo / "TRANSIENT_HOLD.tmp").exists())
    finally:
        handle.close()


def case_no_temp_leak() -> None:
    before = {p.name for p in Path(tempfile.gettempdir()).glob("coauthor-*")}
    with sandbox() as repo:
        build(repo)
    after = {p.name for p in Path(tempfile.gettempdir()).glob("coauthor-*")}
    check("no tempdir leak", not (after - before), f"leaked: {sorted(after - before)[:3]}")


def _sub_once(text: str, old: str, new: str) -> str:
    """Substitute EXACTLY once, or raise. A mutation that silently no-ops
    because the source drifted is a test asserting nothing -- the blind-text-
    surgery failure from this workstream, re-armed. Raising surfaces the drift
    as a loud case failure instead."""
    n = text.count(old)
    if n != 1:
        raise AssertionError(f"expected exactly 1 occurrence of {old!r}, found {n}")
    return text.replace(old, new)


def case_child_is_committed_builder() -> None:
    """The EXECUTING child is the commit's builder, not the dirty worktree's.

    Poison the worktree builder's _runtime_plane (uncommitted) and assert the
    artifact's provenance carries the real interpreter. If the parent ever
    built in-process, or the re-exec ever picked up worktree bytes, the poison
    would ship -- this is the loaded-code-drift claim, tested at the artifact.
    """
    with sandbox() as repo:
        rel = repo / "scripts" / "build-plugin.py"
        poisoned = _sub_once(rel.read_text(encoding="utf-8"),
                             '"python": sys.version.split()[0],',
                             '"python": "0.0.0-DIRTY-BUILDER",')
        rel.write_text(poisoned, encoding="utf-8")
        rc, out, _ = build(repo)
        check("committed child: builder exits 0", rc == 0)
        if rc != 0:
            return
        with zipfile.ZipFile(out) as z:
            rec = json.loads(z.read("PROVENANCE.json"))
        check("committed child: provenance runtime is the real interpreter",
              rec["runtime"]["python"] == sys.version.split()[0],
              f"got {rec['runtime']['python']!r}")
        check("committed child: dirty poison absent from the artifact",
              "0.0.0-DIRTY-BUILDER" not in json.dumps(rec))


def case_exact_output_handoff() -> None:
    """The child's bundle lands at the PARENT's declared output, and nothing
    of the build worktree survives -- neither the directory nor git's admin
    registration. Pins the exit-6 detection's positive complement."""
    with sandbox() as repo:
        expected = _external_output_dir(repo) / "co-author-harness.plugin"
        if expected.exists():
            expected.unlink()
        rc, out, _ = build(repo)
        check("handoff: builder exits 0", rc == 0)
        if rc != 0:
            return
        check("handoff: bundle at the declared output path", expected.is_file())
        check("handoff: build() path and declared path agree", out == expected)
        wt_base = Path(tempfile.gettempdir())
        leftovers = sorted(p.name for p in wt_base.glob("coauthor-build-plane-*")) if wt_base.is_dir() else []
        check("handoff: no build worktree directory remains", not leftovers,
              f"{leftovers[:2]}")
        wt_list = _git(repo, "worktree", "list", "--porcelain").stdout
        check("handoff: no stale worktree registration", "build-" not in wt_list)


def case_prune_failure_voids() -> None:
    """`worktree prune` exiting 1 with EMPTY stderr must still fail cleanup.

    The shipped defect tested `if err:` -- truthiness on a MESSAGE -- so a
    quiet failure passed. This case injects exactly that shape (rc=1,
    stderr="") and requires CleanupFailed. In-process against commit_worktree
    because prune-only failure cannot be injected from outside without a race
    against a successful remove; the end-to-end exit-7 mapping is pinned by
    case_cleanup_failure_exit7.
    """
    import importlib.util
    with sandbox() as repo:
        spec = importlib.util.spec_from_file_location(
            "bp_under_test", repo / "scripts" / "build-plugin.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        head = _git(repo, "rev-parse", "HEAD").stdout.strip()
        real_run = subprocess.run

        def fake_run(args, **kw):
            if isinstance(args, (list, tuple)) and "worktree" in args and "prune" in args:
                return subprocess.CompletedProcess(args, 1, stdout="", stderr="")
            return real_run(args, **kw)

        raised = None
        subprocess.run = fake_run
        try:
            with mod.commit_worktree(head):
                pass
        except mod.CleanupFailed as exc:
            raised = exc
        finally:
            subprocess.run = real_run
        check("prune: silent rc=1 (empty stderr) raises CleanupFailed",
              raised is not None)
        if raised is not None:
            check("prune: reason names prune, not message truthiness",
                  "prune" in str(raised), str(raised)[:80])
        _git(repo, "worktree", "prune", check_rc=False)


def case_committed_mutant_contracts() -> None:
    """Exit 5 and exit 6 pinned by EXECUTING committed mutants.

    The child is whatever the commit says it is, so these contracts can only
    be exercised by committing a mutated builder in a throwaway clone and
    letting the worktree re-exec run it. Post-hoc archive tampering would test
    a different subject (nothing re-validates a finished archive); a mutated
    OVERLAY would test nothing (the child never executes worktree bytes --
    that is case_child_is_committed_builder's point).

    Mutants, each committed from the sandbox HEAD builder (retargeted
    identity: version.json + root plugin.json), not source HEAD's pack path:
      missing-key   drop `enumerator` from the record        -> exit 5
      runtime-tamper poison rec.runtime.python only          -> exit 5
      compress-claim claim ZIP_STORED, write ZIP_DEFLATED    -> exit 5
      stub-child     builder predating --build-here          -> exit 6
    """
    with sandbox(destructive=True) as repo:
        rel = "scripts/build-plugin.py"
        pristine = _head_blob(repo, rel).decode("utf-8", errors="strict")

        def run_mutant(name: str, mutated: str, expect_rc: int, expect_msg: str) -> None:
            (repo / rel).write_text(mutated, encoding="utf-8")
            _git(repo, "add", rel)
            _git(repo, "-c", "user.name=sbx", "-c", "user.email=sbx@localhost",
                 "commit", "--quiet", "-m", f"mutant: {name}")
            _overlay(repo)  # the PARENT under test stays the current builder
            rc, _out, log = build(repo)
            check(f"{name}: exit {expect_rc}", rc == expect_rc, f"rc={rc}")
            check(f"{name}: error names the cause", expect_msg in log,
                  log.strip().splitlines()[-1][:80] if log.strip() else "silent")

        run_mutant(
            "missing-key",
            _sub_once(pristine,
                      '            "enumerator": "scripts/package_enumeration.py'
                      '::enumerate_package_files",\n', ""),
            5, "enumerator")
        run_mutant(
            "runtime-tamper",
            _sub_once(pristine,
                      '"runtime": _runtime_plane(),',
                      '"runtime": {**_runtime_plane(), "python": "9.9.9-TAMPERED"},'),
            5, "runtime.python")
        run_mutant(
            "compress-claim",
            _sub_once(pristine,
                      '"compression": "ZIP_DEFLATED",',
                      '"compression": "ZIP_STORED",'),
            5, "compress_type")
        run_mutant(
            "stub-child",
            "import sys\nsys.exit(0)\n",
            6, "produced no bundle")


def case_cleanup_failure_exit7() -> None:
    """An undeletable build worktree VOIDS the build: exit 7, never 0 or 1.

    Real injection: hold an open handle (no FILE_SHARE_DELETE) on a file
    inside the live build worktree, so `git worktree remove --force` and the
    rmtree fallback both genuinely fail. Windows-only by nature; on POSIX an
    open handle does not block unlink, and this case SKIPS with disclosure --
    the CleanupFailed path itself is still pinned by case_prune_failure_voids.
    """
    if os.name != "nt":
        print("  SKIP  handle-based injection is Windows-only; CleanupFailed "
              "path still pinned by case_prune_failure_voids")
        return
    with sandbox(destructive=True) as repo:
        wt_base = Path(tempfile.gettempdir())
        before_worktrees = set(wt_base.glob("coauthor-build-plane-*"))
        out_dir = _external_output_dir(repo)
        out_dir.mkdir(parents=True, exist_ok=True)
        proc = subprocess.Popen(
            [sys.executable, str(repo / "scripts" / "build-plugin.py"),
             "--out", str(out_dir)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace")
        handle = None
        out = err = ""
        deadline = time.time() + 120
        try:
            while handle is None and proc.poll() is None and time.time() < deadline:
                if wt_base.is_dir():
                    for wt in set(wt_base.glob("coauthor-build-plane-*")) - before_worktrees:
                        probe = wt / "README.md"
                        if probe.is_file():
                            try:
                                handle = open(probe, "r", encoding="utf-8")
                            except OSError:
                                pass
                            break
                time.sleep(0.005)
            out, err = proc.communicate(timeout=300)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.communicate()
        if handle is None:
            # Could not inject in time: no verdict, not a pass -- R-8.
            ERRORS.append("cleanup-injection: never acquired a handle inside "
                          "the build worktree")
            print("  ERROR  environment: handle injection missed the build "
                  "window -- no verdict for this case")
            return
        try:
            check("cleanup failure: exit 7", proc.returncode == 7,
                  f"rc={proc.returncode}")
            check("cleanup failure: error says the build is VOID",
                  "VOID" in (out + err),
                  (out + err).strip().splitlines()[-1][:80] if (out + err).strip() else "silent")
        finally:
            handle.close()
        # Reconcile the SANDBOX we deliberately wounded (never the checkout).
        if wt_base.is_dir():
            for wt in set(wt_base.glob("coauthor-build-plane-*")) - before_worktrees:
                _git(repo, "worktree", "remove", "--force", str(wt), check_rc=False)
                if wt.exists():
                    _rmtree_force(wt)
        _git(repo, "worktree", "prune", check_rc=False)


def main() -> int:
    print("build_plugin_provenance_smoketest (hermetic)")
    print(f"  source HEAD: {_git(HARNESS, 'rev-parse', '--short', 'HEAD').stdout.strip()}")
    print("  all mutations run in disposable clones; the checkout is never written")
    swept = _sweep_stale_bases()
    if swept:
        print(f"  swept {swept} sandbox(es) stranded by an earlier run")
    print()
    for fn in (
        case_clean_build_equals_head,
        case_external_output_required,
        case_dirty_unstaged_ignored,
        case_dirty_staged_ignored,
        case_staged_rename_ignored,
        case_manifest_from_snapshot,
        case_byte_reproducible,
        case_child_is_committed_builder,
        case_exact_output_handoff,
        case_prune_failure_voids,
        case_committed_mutant_contracts,
        case_cleanup_failure_exit7,
        case_git_failure_fails_closed,
        case_reset_survives_transient_handle,
        case_no_temp_leak,
    ):
        print(f"{fn.__name__}:")
        try:
            fn()
        except SandboxEnvironmentError as exc:
            # Reader broke, not the subject: no verdict, run VOID (exit 2).
            ERRORS.append(f"{fn.__name__}: {exc}")
            print(f"  ERROR  environment: {exc} -- no verdict for this case")
        except subprocess.CalledProcessError as exc:
            # Surface git's stderr: "exit status 1" without the refused path
            # cost a full diagnosis round (2026-07-22).
            stderr = (exc.stderr or "").strip() if isinstance(exc.stderr, str) else ""
            check(fn.__name__, False,
                  f"raised CalledProcessError: {exc}"
                  + (f" :: stderr {stderr[:160]!r}" if stderr else ""))
        except Exception as exc:  # noqa: BLE001
            check(fn.__name__, False, f"raised {type(exc).__name__}: {exc}")
        print()
    if FAILURES:
        print(f"FAIL: {len(FAILURES)} case(s): {FAILURES}")
        return 1
    return 0


def _verdict(rc: int) -> int:
    """Three outcomes, not two. THE RUN IS VOID is not a PASS.

    I drew the ACQ-*/PRJ-* line correctly -- an environment failure is not a
    predicate failure -- and then drew the WRONG conclusion from it: teardown
    errors printed a NOTE and left FAILURES empty, so a suite that could not
    restore its own environment still exited 0. My own acquisition contract
    says the opposite (R-8): a reader failure VOIDS the verdict; it does not
    soften it. "Not the subject's fault" and "therefore fine" are different
    claims.

      exit 0  PASS   predicates held, environment intact
      exit 1  FAIL   a predicate failed -> the SUBJECT is wrong
      exit 2  ERROR  the environment broke -> NO VERDICT was established
    """
    if ERRORS:
        print(f"ERROR: run VOID -- {len(ERRORS)} environment failure(s): {ERRORS}")
        print("  No verdict established. This is NOT a pass and NOT a "
              "provenance failure; re-run.")
        return 2
    if rc == 0 and not FAILURES:
        print("PASS: bundle is commit-faithful and same-runtime reproducible "
              "under every probed condition")
    return 1 if FAILURES else rc


if __name__ == "__main__":
    # Teardown in an OUTER finally: a case that raises must not strand a
    # sandbox. An earlier revision called it inline after the loop, so any
    # escape skipped it.
    _rc = 1
    try:
        _rc = main()
    finally:
        _final_teardown()
    sys.exit(_verdict(_rc))
