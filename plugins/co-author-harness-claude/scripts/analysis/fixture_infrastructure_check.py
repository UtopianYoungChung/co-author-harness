#!/usr/bin/env python3
"""fixture_infrastructure_check - focused regressions for the evidence chain.

Covers the 2026-07-16 repair round:

  R1 commit-stability   the manifest is excluded (exact path) from tested
                        inputs; regeneration succeeds with the manifest
                        TRACKED; editing any non-excluded tracked subject
                        file still makes evidence stale
  R2 writer binding     census rejects wrong writer, stale runner hash,
                        mixed run ids, observed/expected mismatch
  R3 concurrency        a second runner fails cleanly without executing
                        suites; prior evidence is voided at run start; a
                        red run leaves no manifest

DELIBERATELY NOT IN THE SUITE UNIVERSE: the filename carries no fixture
marker, so the runner never executes this file -- it exercises the runner
and would otherwise recurse. Clone-based cases use disposable local clones
(same-drive, hardlinked objects) and overlay ONLY scripts/analysis/* --
which is excluded from tested inputs, so the overlay cannot dirty digests.

Run:  python scripts/analysis/fixture_infrastructure_check.py
Exit: 0 all pass; 1 a check failed; 2 environment error.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HARNESS = Path(__file__).resolve().parent.parent.parent
FAILURES: list[str] = []

# Fast suite used by every mini registry (measured ~0.1s).
FAST_SUITE = "scripts/retirement_sweep_smoketest.py"


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{(' - ' + detail) if detail else ''}")
    if not ok:
        FAILURES.append(name)


def _load(path: Path, name: str, repo: Path | None = None):
    """Load a module from `path` with its dependencies resolved inside `repo`.

    WRONG SUBJECT, IN THE SUITE THAT EXISTS TO CATCH WRONG SUBJECTS.
    Loading `<clone>/scripts/analysis/code_census.py` executes
    `from package_enumeration import enumerate_package_files` -- and
    `package_enumeration` was ALREADY in sys.modules from this file's own
    top-level import of the PRIMARY's copy. Python returned the cached
    primary module, so the clone's census enumerated the PRIMARY repository
    while every assertion said "clone". Caught 2026-07-16 by the new
    near-name regression: a file committed in the clone was invisible to the
    clone's own census (it is not in the primary's HEAD), so editing it could
    not stale the evidence -- the test reported the population as 461 files,
    the PRIMARY's count. The README staleness case passed only by accident
    (both repos have README.md, and the digest hashes clone paths).

    So dependencies are resolved against `repo`: its scripts dir goes first on
    sys.path and the shared module names are evicted for the duration, so the
    exec binds the CLONE's modules. Names are restored afterwards; the loaded
    module keeps its own references.
    """
    saved_path = list(sys.path)
    shared = ("package_enumeration", "worktree_paths", "code_census",
              "resolve_includes")
    saved_mods = {k: sys.modules.pop(k, None) for k in shared}
    try:
        if repo is not None:
            sys.path.insert(0, str(repo / "scripts" / "analysis"))
            sys.path.insert(0, str(repo / "scripts"))
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.path[:] = saved_path
        for k, v in saved_mods.items():
            if v is not None:
                sys.modules[k] = v
            else:
                sys.modules.pop(k, None)


# Resolve git and sandbox placement the same way the authorities do -- import
# them, do not re-author them.
sys.path.insert(0, str(HARNESS / "scripts"))
from package_enumeration import GIT  # noqa: E402
from worktree_paths import sandbox_base  # noqa: E402


def _run_git(repo: Path, *args: str, check_rc: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run([GIT, "-C", str(repo), *args],
                          capture_output=True, text=True, encoding="utf-8",
                          check=check_rc)


def _rmtree_force(path: Path) -> None:
    def _on_error(func, p, _exc):
        os.chmod(p, 0o700)
        func(p)
    for attempt in range(6):
        try:
            try:
                shutil.rmtree(path, onexc=_on_error)
            except TypeError:
                shutil.rmtree(path, onerror=lambda f, p, e: _on_error(f, p, e))
            return
        except (PermissionError, OSError):
            if attempt == 5:
                raise
            time.sleep(0.05 * (2 ** attempt))


def _make_clone(base: Path) -> Path:
    repo = base / "repo"
    subprocess.run([GIT, "clone", "--quiet", "--local", str(HARNESS), str(repo)],
                   capture_output=True, check=True)
    head = _run_git(HARNESS, "rev-parse", "HEAD").stdout.strip()
    _run_git(repo, "checkout", "--quiet", "--detach", head)
    # Overlay the OBSERVER ZONE only (excluded from tested inputs by
    # construction, so this cannot dirty any digest).
    (repo / "scripts" / "analysis").mkdir(exist_ok=True)
    for rel in ("scripts/analysis/code_census.py",
                "scripts/analysis/fixture_runner.py",
                "scripts/worktree_paths.py"):
        shutil.copy2(HARNESS / rel, repo / rel)
    return repo


def _mini_registry(runner_mod) -> tuple[dict, list[str]]:
    return {FAST_SUITE: [runner_mod._default_case()]}, [FAST_SUITE]


# --------------------------------------------------------------------------
# R2: census writer-binding negatives (synthetic manifest, temp path, real repo)
# --------------------------------------------------------------------------

def case_census_writer_binding() -> None:
    census = _load(HARNESS / "scripts" / "analysis" / "code_census.py", "cc_real",
                   repo=HARNESS)
    universe = census.discover_suite_universe()
    report = {"suite_universe": universe}
    ti = census.compute_tested_inputs()
    runner_file = HARNESS / "scripts" / "analysis" / "fixture_runner.py"
    rid = str(uuid.uuid4())

    def baseline() -> dict:
        return {
            "schema": "coauthor-fixture-manifest/v1",
            "written_by": "scripts/analysis/fixture_runner.py",
            "runner_sha256": hashlib.sha256(runner_file.read_bytes()).hexdigest(),
            "granularity": "suite",
            "run_id": rid,
            "suites": [{
                "fixture_file": s,
                "suite_sha256": hashlib.sha256((HARNESS / s).read_bytes()).hexdigest(),
                "case_count": 1,
                "run_id": rid,
            } for s in universe],
            "cases": [{
                "fixture_file": s, "case_id": "default",
                "expected_exit": 0, "expected_code": None,
                "outcome_contract": "EXIT-ONLY", "expected_outcome": None,
                "observed_exit": 0, "duration_s": 0.0,
            } for s in universe],
            "tested_inputs": {
                "mode": ti["mode"], "enumerator": ti["enumerator"],
                "exclude_dirs": ti["exclude_dirs"],
                "exclude_files": ti["exclude_files"],
                "file_count": ti["file_count"],
                "pre_sha256": ti["sha256"], "post_sha256": ti["sha256"],
            },
        }

    with tempfile.TemporaryDirectory() as td:
        mpath = Path(td) / "manifest.json"

        def verdict(man: dict) -> tuple[bool, str]:
            mpath.write_text(json.dumps(man), encoding="utf-8")
            return census._check_suite_bound_manifest_consistency(report, mpath)

        ok, detail = verdict(baseline())
        check("baseline synthetic manifest accepted (guard)", ok, detail[:90])

        m = baseline(); m["written_by"] = "scripts/evil_writer.py"
        ok, detail = verdict(m)
        check("wrong writer rejected", not ok and "written_by" in detail, detail[:90])

        m = baseline(); m["runner_sha256"] = "0" * 64
        ok, detail = verdict(m)
        check("stale runner hash rejected", not ok and "runner_sha256" in detail,
              detail[:90])

        m = baseline()
        m["suites"][0]["run_id"] = str(uuid.uuid4())
        ok, detail = verdict(m)
        check("mixed run ids rejected", not ok and "run_id" in detail, detail[:90])

        m = baseline()
        m["cases"][0]["observed_exit"] = 7
        ok, detail = verdict(m)
        check("observed/expected mismatch rejected",
              not ok and "observed_exit" in detail, detail[:90])

        m = baseline(); m["schema"] = "somebody-else/v9"
        ok, detail = verdict(m)
        check("wrong schema rejected", not ok and "schema" in detail, detail[:90])

        m = baseline()
        m["tested_inputs"]["exclude_files"] = m["tested_inputs"]["exclude_files"] + [
            "docs/analysis/generated/predicate_rows.md"]
        ok, detail = verdict(m)
        check("widened exclude_files rejected", not ok and "exclude_files" in detail,
              detail[:90])

        m = baseline()
        m["tested_inputs"]["exclude_dirs"] = ["docs/analysis/generated/"]
        ok, detail = verdict(m)
        check("widened exclude_dirs rejected", not ok and "exclude_dirs" in detail,
              detail[:90])

        m = baseline()
        ti_flat = dict(m["tested_inputs"])
        ti_flat["exclude"] = ti_flat["exclude_dirs"] + ti_flat["exclude_files"]
        m["tested_inputs"] = ti_flat
        ok, detail = verdict(m)
        check("retired flat `exclude` shape rejected",
              not ok and "flat `exclude`" in detail, detail[:90])

    # R1/F3 exclusion shape: exact files matched by EQUALITY, dir prefixes by
    # prefix, both machine-recorded under distinct keys, no broad generated/.
    MAN = "docs/analysis/generated/fixture_manifest.json"
    check("manifest is an EXACT-file exclusion", MAN in census.TESTED_INPUT_EXCLUDE_FILES)
    check("manifest is NOT a directory-prefix exclusion",
          MAN not in census.TESTED_INPUT_EXCLUDE_DIRS)
    check("exclusion recorded under tested_inputs.exclude_files",
          MAN in ti["exclude_files"])
    check("observer zone recorded under tested_inputs.exclude_dirs",
          "scripts/analysis/" in ti["exclude_dirs"])
    check("retired flat `exclude` field not emitted", "exclude" not in ti)
    check("no broad generated-docs directory exclusion",
          not any(d in ("docs/", "docs/analysis/", "docs/analysis/generated/")
                  for d in census.TESTED_INPUT_EXCLUDE_DIRS))
    # The F3 defect itself: startswith() on the manifest path also swallowed
    # every near-name sibling.
    check("_is_excluded excludes the manifest exactly", census._is_excluded(MAN))
    for near in (MAN + ".backup", MAN + ".tmp", MAN + ".orig",
                 "docs/analysis/generated/fixture_manifest.json2"):
        check(f"near-name INCLUDED: {near.rsplit('/', 1)[-1]}",
              not census._is_excluded(near))
    check("observer-zone prefix still excludes its members",
          census._is_excluded("scripts/analysis/code_census.py"))
    check("predicate_rows.md remains SUBJECT (not excluded)",
          not census._is_excluded("docs/analysis/generated/predicate_rows.md"))


# --------------------------------------------------------------------------
# R3: runner concurrency + void semantics (disposable clone)
# --------------------------------------------------------------------------

def case_runner_concurrency_and_void(repo: Path) -> None:
    runner = _load(repo / "scripts" / "analysis" / "fixture_runner.py", "fr_clone",
                   repo=repo)
    registry, universe = _mini_registry(runner)

    # Hold the clone's lock, then start a REAL second runner process against
    # the clone. It must exit 2 quickly, execute nothing, and touch nothing.
    dummy = runner.MANIFEST_PATH
    dummy.parent.mkdir(parents=True, exist_ok=True)
    dummy.write_text('{"sentinel": "must-survive-loser"}', encoding="utf-8")
    lock = runner._acquire_lock()
    check("lock acquired for contention test", lock is not None)
    t0 = time.time()
    proc = subprocess.run(
        [sys.executable, str(repo / "scripts" / "analysis" / "fixture_runner.py")],
        capture_output=True, text=True, encoding="utf-8", timeout=120)
    took = time.time() - t0
    check("second runner exits 2 under contention", proc.returncode == 2,
          f"rc={proc.returncode}")
    check("second runner names the lock", "lock" in (proc.stdout + proc.stderr).lower())
    check("second runner refused fast (no suites executed)", took < 60, f"{took:.1f}s")
    check("loser did not touch existing evidence",
          dummy.is_file() and "must-survive-loser" in dummy.read_text(encoding="utf-8"))
    runner._release_lock(lock)

    # Upfront void: a RED mini run must (a) void the prior manifest at start,
    # (b) return 1, (c) write nothing new.
    bad_registry = {FAST_SUITE: [dict(runner._default_case(), expected_exit=1)]}
    rc = runner.run(bad_registry, universe)
    check("red run returns 1", rc == 1, f"rc={rc}")
    check("red run leaves NO manifest (old green evidence voided)",
          not dummy.is_file())

    # Green mini run writes evidence again.
    rc = runner.run(registry, universe)
    check("green mini run returns 0", rc == 0, f"rc={rc}")
    check("green mini run wrote a manifest", dummy.is_file())
    man = json.loads(dummy.read_text(encoding="utf-8"))
    check("manifest carries full-length runner_sha256",
          isinstance(man.get("runner_sha256"), str) and len(man["runner_sha256"]) == 64)
    check("no stray tmp files left",
          not list(dummy.parent.glob("fixture_manifest.*.tmp")))

    # Empty registry is not evidence.
    rc = runner.run({}, [])
    check("empty registry refused (exit 2)", rc == 2, f"rc={rc}")


# --------------------------------------------------------------------------
# R1: commit-stability (disposable clone; manifest TRACKED)
# --------------------------------------------------------------------------

def case_commit_stability(repo: Path) -> None:
    runner = _load(repo / "scripts" / "analysis" / "fixture_runner.py", "fr_clone2",
                   repo=repo)
    census = _load(repo / "scripts" / "analysis" / "code_census.py", "cc_clone",
                   repo=repo)
    registry, universe = _mini_registry(runner)
    report = {"suite_universe": universe}

    rc = runner.run(registry, universe)
    check("initial mini run in clone returns 0", rc == 0, f"rc={rc}")

    # TRACK the manifest, then regenerate. Without the exact-path exclusion
    # this next run's evidence would be permanently stale the moment it is
    # written (the check recomputes over a tree containing the NEW manifest
    # while the record hashed the OLD one).
    _run_git(repo, "add", "docs/analysis/generated/fixture_manifest.json")
    _run_git(repo, "-c", "user.name=sbx", "-c", "user.email=sbx@localhost",
             "commit", "--quiet", "-m", "test: track fixture manifest")
    rc = runner.run(registry, universe)
    check("regeneration succeeds with manifest TRACKED", rc == 0, f"rc={rc}")
    ok, detail = census._check_suite_bound_manifest_consistency(report)
    check("evidence remains CURRENT after tracked regeneration",
          ok and "STALE" not in detail, detail[:110])

    # A NON-excluded tracked subject edit must still stale the evidence.
    victim = repo / "README.md"
    original = victim.read_bytes()
    victim.write_bytes(original + b"\n<!-- staleness probe -->\n")
    try:
        ok, detail = census._check_suite_bound_manifest_consistency(report)
        check("subject edit makes evidence STALE",
              not ok and "STALE" in detail, detail[:110])
    finally:
        victim.write_bytes(original)
    ok, detail = census._check_suite_bound_manifest_consistency(report)
    check("restore returns evidence to CURRENT", ok, detail[:110])

    # F3 END-TO-END: a TRACKED near-name sibling of the manifest is SUBJECT.
    # Under the old startswith() rule this file was silently excluded, so
    # editing it could never stale the evidence -- a tracked file outside the
    # subject population with no one saying so.
    near = repo / "docs/analysis/generated/fixture_manifest.json.backup"
    near.write_text('{"near-name": "must be subject"}\n', encoding="utf-8",
                    newline="\n")
    _run_git(repo, "add", "docs/analysis/generated/fixture_manifest.json.backup")
    _run_git(repo, "-c", "user.name=sbx", "-c", "user.email=sbx@localhost",
             "commit", "--quiet", "-m", "test: track a near-name manifest sibling")
    rc = runner.run(registry, universe)
    check("regeneration succeeds with a tracked near-name sibling", rc == 0, f"rc={rc}")
    baseline_ok, baseline_detail = census._check_suite_bound_manifest_consistency(report)
    check("evidence CURRENT with near-name sibling tracked", baseline_ok,
          baseline_detail[:110])
    near.write_text('{"near-name": "MUTATED"}\n', encoding="utf-8", newline="\n")
    ok, detail = census._check_suite_bound_manifest_consistency(report)
    check("editing the tracked near-name sibling makes evidence STALE",
          not ok and "STALE" in detail, detail[:110])


def case_repo_global_paths() -> None:
    """F1/F2: sandbox base and runner lock are REPOSITORY-global.

    Both were derived from this file's location (`HARNESS.parent`,
    `PLUGIN_ROOT/...`), which says where the CODE is, not where the
    REPOSITORY is. From a worktree under `co-author-harness/.worktrees/<n>`
    that put the sandbox INSIDE the primary repo (git discovery walks up, so
    the git-failure case's .git deletion found the real repo and the builder
    succeeded) and gave every worktree its own lock (so two worktrees ran the
    shared corpus concurrently).

    Asserted against git's own registry, from THIS worktree, plus a simulated
    internal-worktree root to prove the rule is layout-independent rather
    than accidentally correct in the primary.
    """
    import worktree_paths as wp

    common = wp.git_common_dir(HARNESS)
    roots = wp.registered_worktree_roots(HARNESS)
    primary = wp.primary_worktree_root(HARNESS)
    check("git-common-dir resolves", common.is_dir(), str(common))
    check("primary root derived from common dir", primary.is_dir(), str(primary))
    check("worktree registry non-empty", bool(roots), f"{len(roots)} root(s)")

    base = wp.sandbox_base(HARNESS, ".coauthor-provenance-sbx")
    check("sandbox base is same-drive as primary (clone --local hardlinks)",
          base.drive.lower() == primary.drive.lower(), f"{base.drive} vs {primary.drive}")
    check("sandbox base outside EVERY registered worktree",
          all(base != r and r not in base.parents for r in roots), str(base))

    # The identity that makes the rule layout-independent: a linked worktree
    # anywhere (including under the primary) must yield the SAME base and the
    # SAME lock, because both hang off the common dir, not off __file__.
    internal = HARNESS / ".worktrees" / "milestone-feedback-framework"
    if internal.is_dir():
        check("internal worktree yields the SAME common dir",
              wp.git_common_dir(internal) == common,
              f"{wp.git_common_dir(internal)}")
        check("internal worktree yields the SAME sandbox base",
              wp.sandbox_base(internal, ".coauthor-provenance-sbx") == base)
    else:
        print("  SKIP  no internal worktree present to cross-check")

    # The guard is mechanical: point it at a path inside a worktree and it
    # must refuse, rather than document a rule it does not enforce.
    refused = False
    try:
        wp.assert_outside_all_worktrees(primary / ".worktrees" / "sbx-probe", HARNESS)
    except RuntimeError:
        refused = True
    check("assert_outside_all_worktrees refuses a path under a worktree", refused)

    # The lock is in the shared admin dir -> one lock for all worktrees, and
    # no untracked lock file inside any working tree.
    import importlib.util as _ilu
    spec = _ilu.spec_from_file_location(
        "fr_lockprobe", HARNESS / "scripts" / "analysis" / "fixture_runner.py")
    fr = _ilu.module_from_spec(spec)
    spec.loader.exec_module(fr)
    lock_path = fr._lock_path()
    check("runner lock lives in the shared git admin dir",
          lock_path.parent.resolve() == common, str(lock_path))
    # NOT "outside every worktree root by path": the common dir IS
    # `<primary>/.git`, which is under the primary's root, so a path-ancestry
    # test fails on a correct lock (my first assertion did exactly that). The
    # property that matters is that no worktree's WORKING TREE contains it --
    # git never reports files under .git, so the lock can never appear as an
    # untracked path. Assert that mechanically via git itself rather than by
    # reasoning about paths.
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.touch()
    status = subprocess.run(
        [GIT, "-C", str(HARNESS), "status", "--porcelain", "--ignored"],
        capture_output=True, text=True, encoding="utf-8").stdout
    check("runner lock is invisible to git status in the primary worktree",
          "coauthor-fixture-runner.lock" not in status)
    for r in roots:
        st = subprocess.run([GIT, "-C", str(r), "status", "--porcelain", "--ignored"],
                            capture_output=True, text=True, encoding="utf-8").stdout
        check(f"lock invisible to git status in {r.name}",
              "coauthor-fixture-runner.lock" not in st)
    check("no stale in-tree lock file from the per-worktree design",
          not (HARNESS / "docs/analysis/generated/.fixture_runner.lock").exists())


def case_cross_worktree_lock(repo: Path, base: Path) -> None:
    """F2: two WORKTREES of one repository contend for ONE lock.

    Not two processes in one worktree (already covered): a second linked
    worktree, which is exactly what a per-worktree lock failed to coordinate.
    Uses the disposable clone as 'the repository' and adds an internal linked
    worktree to it -- the layout that previously produced two independent
    locks.
    """
    wt = repo / ".worktrees" / "lockprobe"
    head = _run_git(repo, "rev-parse", "HEAD").stdout.strip()
    _run_git(repo, "worktree", "add", "--quiet", "--detach", str(wt), head)
    try:
        # Overlay the observer zone into the linked worktree too (its HEAD
        # predates these repairs; only the tooling under test is current).
        (wt / "scripts" / "analysis").mkdir(parents=True, exist_ok=True)
        for rel in ("scripts/analysis/code_census.py",
                    "scripts/analysis/fixture_runner.py",
                    "scripts/worktree_paths.py"):
            shutil.copy2(HARNESS / rel, wt / rel)

        runner_a = _load(repo / "scripts" / "analysis" / "fixture_runner.py", "fr_a",
                         repo=repo)
        runner_b = _load(wt / "scripts" / "analysis" / "fixture_runner.py", "fr_b",
                         repo=wt)
        check("both worktrees resolve the SAME lock path",
              runner_a._lock_path() == runner_b._lock_path(),
              str(runner_a._lock_path()))

        # A's evidence must survive B's refusal untouched.
        evidence = runner_a.MANIFEST_PATH
        evidence.parent.mkdir(parents=True, exist_ok=True)
        evidence.write_text('{"sentinel": "A-evidence"}', encoding="utf-8")
        lock = runner_a._acquire_lock()
        check("worktree A acquired the lock", lock is not None)
        t0 = time.time()
        proc = subprocess.run(
            [sys.executable, str(wt / "scripts" / "analysis" / "fixture_runner.py")],
            capture_output=True, text=True, encoding="utf-8", timeout=180)
        took = time.time() - t0
        out = proc.stdout + proc.stderr
        check("worktree B exits 2 under cross-worktree contention",
              proc.returncode == 2, f"rc={proc.returncode}")
        check("worktree B names the repository-global lock",
              "repository-global lock" in out)
        check("worktree B executed no suite", "PASS  exit" not in out and
              "FAIL  exit" not in out)
        check("worktree B refused fast", took < 60, f"{took:.1f}s")
        check("worktree A's evidence untouched by B",
              evidence.is_file() and "A-evidence" in evidence.read_text(encoding="utf-8"))
        runner_a._release_lock(lock)

        # Release permits a subsequent run: B can now take the lock.
        lock_b = runner_b._acquire_lock()
        check("after release, worktree B acquires the lock", lock_b is not None)
        if lock_b is not None:
            runner_b._release_lock(lock_b)
    finally:
        _run_git(repo, "worktree", "remove", "--force", str(wt), check_rc=False)
        _run_git(repo, "worktree", "prune", check_rc=False)


def main() -> int:
    print("fixture_infrastructure_check (focused; never runs the corpus)")
    print(f"  harness: {HARNESS}")
    print()
    print("case_repo_global_paths:")
    case_repo_global_paths()
    print()
    print("case_census_writer_binding:")
    case_census_writer_binding()
    print()
    # Clone base derived repo-globally, like every other sandbox (F1): under
    # `.worktrees/` the old `HARNESS.parent` base put clones inside the repo.
    base = Path(tempfile.mkdtemp(prefix="fic-",
                                 dir=str(sandbox_base(HARNESS, ".coauthor-fic-sbx"))))
    try:
        repo = _make_clone(base)
        print("case_runner_concurrency_and_void:")
        case_runner_concurrency_and_void(repo)
        print()
        print("case_cross_worktree_lock:")
        case_cross_worktree_lock(repo, base)
        print()
        print("case_commit_stability:")
        case_commit_stability(repo)
    finally:
        _rmtree_force(base)
        leftover = base.exists()
        # Remove the sandbox BASE too when empty: sandbox_base() creates it, so
        # leaving it behind is debris this suite introduced (the old
        # HARNESS.parent design created nothing). suppress: a concurrent run
        # legitimately owns it.
        with contextlib.suppress(OSError):
            base.parent.rmdir()
        print()
        print("  ok     clone removed" if not leftover
              else "  ERROR  clone left behind")
        if leftover:
            FAILURES.append("clone-teardown")
    if FAILURES:
        print(f"\nFAIL: {len(FAILURES)}: {FAILURES}")
        return 1
    print("\nPASS: fixture-evidence infrastructure holds under commit, "
          "contention, and red runs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
