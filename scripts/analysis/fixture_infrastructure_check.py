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
  R4 portability        canonical evidence follows Git-clean content across
                        LF/CRLF checkouts while raw pre/post still observes
                        the exact bytes exercised in one run
  R5 tree ownership     every suite starts inside an owned process boundary;
                        direct exit, timeout, teardown races, and owner loss
                        leave no descendant, delayed mutation, or evidence

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
import inspect
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
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
    shared = (
        "package_enumeration", "worktree_paths", "code_census", "fixture_cache",
        "fixture_process_supervisor", "resolve_includes",
    )
    saved_mods = {k: sys.modules.pop(k, None) for k in shared}
    saved_named = sys.modules.get(name)
    try:
        if repo is not None:
            sys.path.insert(0, str(repo / "scripts" / "analysis"))
            sys.path.insert(0, str(repo / "scripts"))
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        # Dataclass resolution and exact-path imports legitimately consult
        # sys.modules while the module body executes.
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.path[:] = saved_path
        if saved_named is not None:
            sys.modules[name] = saved_named
        else:
            sys.modules.pop(name, None)
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
                          errors="strict",
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
                "scripts/analysis/fixture_cache.py",
                "scripts/analysis/fixture_process_supervisor.py",
                "scripts/analysis/fixture_runner.py",
                "scripts/worktree_paths.py"):
        shutil.copy2(HARNESS / rel, repo / rel)
    return repo


def _mini_registry(runner_mod) -> tuple[dict, list[str]]:
    return {FAST_SUITE: [runner_mod._default_case()]}, [FAST_SUITE]


# --------------------------------------------------------------------------
# R2: census writer-binding negatives (synthetic manifest, temp path, real repo)
# --------------------------------------------------------------------------

def case_static_matrix_does_not_consume_execution_receipts() -> None:
    census = _load(HARNESS / 'scripts/analysis/code_census.py', 'cc_static', repo=HARNESS)
    report = census.build_report()
    def receipt_unavailable(_report):
        raise AssertionError('Static predicate generation consulted a mutable execution receipt')
    census._check_suite_bound_manifest_consistency = receipt_unavailable
    try:
        first = census.emit_matrix(report)
        second = census.emit_matrix(report)
    except AssertionError as exc:
        check('static map remains generatable without execution receipts', False, str(exc))
        return
    check('static map remains generatable without execution receipts', first == second)
    check('static map points to separate execution evidence', 'fixture_manifest.json' in first and 'fixture_cases=0' not in first)


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
                "raw_mode": ti["raw_mode"],
                "raw_pre_sha256": ti["raw_sha256"],
                "raw_post_sha256": ti["raw_sha256"],
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


def case_checkout_digest_portability(repo: Path) -> None:
    """One clean Git tree may have different checkout bytes across hosts."""
    census = _load(repo / "scripts" / "analysis" / "code_census.py",
                   "cc_portability", repo=repo)
    target = repo / "README.md"
    original = target.read_bytes()
    lf = original.replace(b"\r\n", b"\n")
    crlf = lf.replace(b"\n", b"\r\n")
    assert lf != crlf

    target.write_bytes(lf)
    first = census.compute_tested_inputs()
    target.write_bytes(crlf)
    second = census.compute_tested_inputs()
    check("canonical digest is checkout-portable",
          first["sha256"] == second["sha256"],
          f"LF={first['sha256'][:12]} CRLF={second['sha256'][:12]}")
    check("raw digest records exact exercised bytes",
          first["raw_sha256"] != second["raw_sha256"],
          f"LF={first.get('raw_sha256', '')[:12]} "
          f"CRLF={second.get('raw_sha256', '')[:12]}")
    check("raw digest has an explicit local-only mode",
          first["raw_mode"] == "checkout-raw-bytes-v1")
    target.write_bytes(original)


def _cache_basis(seed: str) -> dict:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return {
        "runner_sha256": hashlib.sha256((seed + "runner").encode()).hexdigest(),
        "census_sha256": hashlib.sha256((seed + "census").encode()).hexdigest(),
        "cache_helper_sha256": hashlib.sha256((seed + "cache").encode()).hexdigest(),
        "suite_sha256": hashlib.sha256((seed + "suite").encode()).hexdigest(),
        "invocation_contract": {"fixture_file": f"scripts/{seed}.py", "case_id": "default"},
        "tested_inputs": {"sha256": digest, "raw_sha256": digest},
        "environment": {"host": "synthetic"},
    }


def case_cache_contract() -> None:
    cache = _load(HARNESS / "scripts" / "analysis" / "fixture_cache.py",
                  "fixture_cache_contract", repo=HARNESS)
    with tempfile.TemporaryDirectory(prefix="fixture-cache-contract-") as td:
        root = Path(td).resolve() / "cache"
        basis = _cache_basis("alpha")
        check("absent exact cache key is MISS", cache.lookup(root, basis) is cache.MISS)
        staged = cache.stage_entry(
            root,
            basis=basis,
            observed_exit=0,
            stdout_sha256=hashlib.sha256(b"stdout").hexdigest(),
            stderr_sha256=hashlib.sha256(b"stderr").hexdigest(),
            source_run_id="synthetic-run",
        )
        check("staged entry is not yet visible", cache.lookup(root, basis) is cache.MISS)
        published = cache.publish_staged([staged])
        check("green final-call publishes exactly one entry", published == [staged.final_path])
        hit = cache.lookup(root, basis)
        check("published exact basis is a validated hit",
              hit is not cache.MISS and hit["result"]["observed_exit"] == 0)

        changed = json.loads(json.dumps(basis))
        changed["invocation_contract"]["case_id"] = "changed"
        check("basis mutation is MISS, never an adjacent hit",
              cache.lookup(root, changed) is cache.MISS)

        # A malformed object at the exact key is VOID, not MISS.
        staged.final_path.write_bytes(b"{}\n")
        refused = False
        try:
            cache.lookup(root, basis)
        except cache.CacheError as exc:
            refused = exc.code == cache.FIXTURE_CACHE_INVALID
        check("malformed exact-key entry is FIXTURE-CACHE-INVALID", refused)

    with tempfile.TemporaryDirectory(prefix="fixture-cache-atomic-") as td:
        root = Path(td).resolve() / "cache"
        first = cache.stage_entry(
            root, basis=_cache_basis("first"), observed_exit=0,
            stdout_sha256=hashlib.sha256(b"1").hexdigest(),
            stderr_sha256=hashlib.sha256(b"").hexdigest(), source_run_id="r1")
        second = cache.stage_entry(
            root, basis=_cache_basis("second"), observed_exit=0,
            stdout_sha256=hashlib.sha256(b"2").hexdigest(),
            stderr_sha256=hashlib.sha256(b"").hexdigest(), source_run_id="r1")
        second.final_path.write_bytes(b"conflict")
        refused = False
        try:
            cache.publish_staged([first, second])
        except cache.CacheError as exc:
            refused = exc.code == cache.FIXTURE_CACHE_PUBLICATION
        check("set publication refuses a conflicting later key", refused)
        check("publication conflict exposes no earlier key", not first.final_path.exists())
        check("publication conflict removes every staged entry",
              not first.staged_path.exists() and not second.staged_path.exists())


# --------------------------------------------------------------------------
# R3: runner concurrency + void semantics (disposable clone)
# --------------------------------------------------------------------------

def _staging_capture_root(prefix: str) -> tuple[Path, Path]:
    """Return (sandbox workspace, empty capture dir inside its staging lane).

    The runner refuses a transcript root the destination guard cannot classify
    as writable. A bare temp directory is writable only on a host that already
    has a governed workspace; everywhere else it is DEST-UNGOVERNED. The probe
    therefore builds the smallest governed workspace (its routing manifest) and
    captures inside that workspace's staging lane, which is writable on every
    host. The caller removes the workspace.
    """
    workspace = Path(tempfile.mkdtemp(prefix=prefix))
    manifest = workspace / "governance" / "output-routing" / "output_routing.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("schema_version: 1\nroutes: []\n", encoding="utf-8")
    capture = (workspace / "outputs" / "co-author-harness" / "staging"
               / "fixture-probe" / "transcripts")
    capture.mkdir(parents=True)
    return workspace, capture


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
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=120)
    took = time.time() - t0
    check("second runner exits 2 under contention", proc.returncode == 2,
          f"rc={proc.returncode}")
    check("second runner names the lock", "lock" in (proc.stdout + proc.stderr).lower())
    check("second runner refused fast (no suites executed)", took < 60, f"{took:.1f}s")
    check("loser did not touch existing evidence",
          dummy.is_file() and "must-survive-loser" in dummy.read_text(encoding="utf-8"))
    runner._release_lock(lock)

    # Public callers cannot turn a focused registry into canonical evidence.
    before = dummy.read_bytes()
    rc = runner.run(registry, universe)
    check("partial public run is refused (exit 2)", rc == 2, f"rc={rc}")
    check("partial refusal leaves canonical evidence untouched", dummy.read_bytes() == before)

    # Upfront void: a RED mini run must (a) void the prior manifest at start,
    # (b) return 1, (c) write nothing new.
    transcript_suite = "scripts/failure_transcript_probe_smoketest.py"
    transcript_stdout = (
        "stdout-first\nstdout-second\nstdout-third\nstdout-last\n"
        .replace("\n", os.linesep).encode("utf-8")
    )
    transcript_stderr = (
        "stderr-first\nstderr-second\nstderr-last\n"
        .replace("\n", os.linesep).encode("utf-8")
    )
    (repo / transcript_suite).write_text(
        "import sys\n"
        "sys.stdout.write('stdout-first\\nstdout-second\\nstdout-third\\nstdout-last\\n')\n"
        "sys.stderr.write('stderr-first\\nstderr-second\\nstderr-last\\n')\n",
        encoding="utf-8",
        newline="\n",
    )
    bad_registry = {FAST_SUITE: [dict(runner._default_case(), expected_exit=1)]}
    transcript_registry = {
        transcript_suite: [dict(runner._default_case(), expected_exit=1)]
    }
    transcript_workspace, transcript_root = _staging_capture_root(
        "fixture-failure-transcripts-"
    )
    rc = runner.run(
        transcript_registry,
        [transcript_suite],
        failure_transcript_root=transcript_root,
        _test_only_allow_noncanonical_write=True,
    )
    check("red run returns 1", rc == 1, f"rc={rc}")
    check("red run leaves NO manifest (old green evidence voided)",
          not dummy.is_file())
    transcript_index = transcript_root / "failure-transcripts.json"
    check("red run writes a failure transcript index", transcript_index.is_file())
    if transcript_index.is_file():
        transcript = json.loads(transcript_index.read_text(encoding="utf-8"))
        failures = transcript.get("failures", [])
        check("transcript index retains one failed case", len(failures) == 1)
        if len(failures) == 1:
            failure = failures[0]
            check("transcript retains suite identity",
                  failure.get("fixture_file") == transcript_suite)
            check("transcript retains case identity",
                  failure.get("case_id") == "default")
            for stream, expected in (
                ("stdout", transcript_stdout), ("stderr", transcript_stderr),
            ):
                stream_binding = failure.get(stream, {})
                stream_path = transcript_root / stream_binding.get("path", "missing")
                observed = stream_path.read_bytes() if stream_path.is_file() else None
                check(f"{stream} transcript preserves complete bytes", observed == expected)
                check(f"{stream} transcript byte count is bound",
                      stream_binding.get("byte_length") == len(expected))
                check(f"{stream} transcript SHA-256 is bound",
                      stream_binding.get("sha256") == hashlib.sha256(expected).hexdigest())
    shutil.rmtree(transcript_workspace)

    # Green mini run writes evidence again.
    rc = runner.run(
        registry,
        universe,
        _test_only_allow_noncanonical_write=True,
    )
    check("green mini run returns 0", rc == 0, f"rc={rc}")
    check("green mini run wrote a manifest", dummy.is_file())
    man = json.loads(dummy.read_text(encoding="utf-8"))
    check("manifest carries full-length runner_sha256",
          isinstance(man.get("runner_sha256"), str) and len(man["runner_sha256"]) == 64)
    check("no stray tmp files left",
          not list(dummy.parent.glob("fixture_manifest.*.tmp")))

    before = dummy.read_bytes()
    cache_root = runner._cache_root()
    cache_before = sorted(cache_root.glob("*")) if cache_root.is_dir() else []
    rc = runner.run(registry, universe, write_manifest=False)
    check("green --no-write mini run returns 0", rc == 0, f"rc={rc}")
    check("--no-write preserves committed evidence byte-for-byte",
          dummy.read_bytes() == before)
    cache_after = sorted(cache_root.glob("*")) if cache_root.is_dir() else []
    check("cache-off run reads and writes no cache entries", cache_after == cache_before)

    rc = runner.run(registry, universe, write_manifest=False, cache_mode="use")
    check("cache-assisted partial run is refused (exit 2)", rc == 2, f"rc={rc}")
    check("cache-assisted partial refusal preserves evidence", dummy.read_bytes() == before)

    rc = runner.run(bad_registry, universe, write_manifest=False)
    check("red --no-write mini run returns 1", rc == 1, f"rc={rc}")
    check("red --no-write run does not void prior evidence",
          dummy.read_bytes() == before)

    # Empty registry is not evidence.
    rc = runner.run({}, [])
    check("empty registry refused (exit 2)", rc == 2, f"rc={rc}")


# --------------------------------------------------------------------------
# R5: runner-owned per-suite process trees (no Git or corpus required)
# --------------------------------------------------------------------------

def _stable_tested_inputs() -> dict[str, object]:
    digest = hashlib.sha256(b"fixture-process-tree-focused-inputs").hexdigest()
    return {
        "mode": "focused-synthetic",
        "enumerator": "fixture_infrastructure_check",
        "exclude_dirs": [],
        "exclude_files": [],
        "file_count": 1,
        "sha256": digest,
        "raw_mode": "focused-synthetic-raw",
        "raw_sha256": digest,
    }


def _write_process_suite(root: Path, source: str) -> str:
    rel = "scripts/process_tree_focused_suite.py"
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8", newline="\n")
    return rel


def case_suite_process_tree_ownership() -> None:
    """R5: the direct suite exit is never mistaken for whole-tree closure."""
    with tempfile.TemporaryDirectory(prefix="fixture-process-tree-") as td:
        root = Path(td).resolve()
        runner = _load(
            HARNESS / "scripts" / "analysis" / "fixture_runner.py",
            "fr_process_tree",
            repo=HARNESS,
        )
        runner.PLUGIN_ROOT = root
        runner.MANIFEST_PATH = root / "docs" / "analysis" / "generated" / "fixture_manifest.json"
        runner.compute_tested_inputs = _stable_tested_inputs

        unsupported_sentinel = root / "unsupported-platform-ran.txt"
        unsupported_code = (
            "from pathlib import Path;"
            f"Path({str(unsupported_sentinel)!r}).write_text('ran',encoding='ascii')"
        )
        unsupported_refused = False
        try:
            runner.fixture_process_supervisor.run_owned(
                [sys.executable, "-I", "-B", "-c", unsupported_code],
                cwd=root, timeout_s=2, _test_platform=("posix", "darwin"),
            )
        except runner.fixture_process_supervisor.FixtureProcessError as exc:
            unsupported_refused = exc.code == "FIXTURE-PROCESS-UNSUPPORTED"
        check("unsupported process-tree platform mechanically refuses", unsupported_refused)
        check("unsupported-host refusal executes no suite bytes", not unsupported_sentinel.exists())
        if os.name != "nt" and not sys.platform.startswith("linux"):
            return

        lock_state = {"held": False, "acquired": 0, "released": 0}
        lock_token = object()

        def acquire_lock():
            if lock_state["held"]:
                return None
            lock_state["held"] = True
            lock_state["acquired"] += 1
            return lock_token

        def release_lock(token):
            assert token is lock_token and lock_state["held"]
            lock_state["held"] = False
            lock_state["released"] += 1

        runner._acquire_lock = acquire_lock
        runner._release_lock = release_lock
        runner._lock_path = lambda: root / "fixture-runner.lock"

        cache_calls = {"stage": 0, "publish": 0}
        original_stage = runner.fixture_cache.stage_entry
        original_publish = runner.fixture_cache.publish_staged

        def counted_stage(*args, **kwargs):
            cache_calls["stage"] += 1
            return original_stage(*args, **kwargs)

        def counted_publish(*args, **kwargs):
            cache_calls["publish"] += 1
            return original_publish(*args, **kwargs)

        runner.fixture_cache.stage_entry = counted_stage
        runner.fixture_cache.publish_staged = counted_publish

        infrastructure_stdout = b"infrastructure-stdout\n"
        infrastructure_stderr = b"infrastructure-stderr\n"
        infrastructure_suite = _write_process_suite(
            root,
            "import os,time\n"
            f"os.write(1,{infrastructure_stdout!r})\n"
            f"os.write(2,{infrastructure_stderr!r})\n"
            "time.sleep(5)\n",
        )
        transcript_workspace, transcript_root = _staging_capture_root(
            "infrastructure-error-transcripts-"
        )
        # The budget must cover supervised startup (systemd unit, anchor and
        # suite interpreters, about 0.3s on Linux) so the suite writes its
        # bytes before it times out.
        rc = runner.run(
            {infrastructure_suite: [runner._default_case(timeout_s=3)]},
            [infrastructure_suite],
            failure_transcript_root=transcript_root,
            _test_only_allow_noncanonical_write=True,
        )
        check("infrastructure error run returns 2", rc == 2, f"rc={rc}")
        transcript_index = transcript_root / "failure-transcripts.json"
        check("infrastructure error writes a transcript index", transcript_index.is_file())
        if transcript_index.is_file():
            transcript = json.loads(transcript_index.read_text(encoding="utf-8"))
            failures = transcript.get("failures", [])
            check("infrastructure transcript retains one error case", len(failures) == 1)
            if len(failures) == 1:
                failure = failures[0]
                check("infrastructure transcript retains suite identity",
                      failure.get("fixture_file") == infrastructure_suite)
                check("infrastructure transcript retains case identity",
                      failure.get("case_id") == "default")
                check("infrastructure transcript retains typed diagnostic",
                      failure.get("diagnostic", {}).get("code") == "FIXTURE-PROCESS-TIMEOUT")
                check("infrastructure transcript records no direct exit",
                      failure.get("observed_exit") is None)
                for stream, expected in (
                    ("stdout", infrastructure_stdout),
                    ("stderr", infrastructure_stderr),
                ):
                    stream_binding = failure.get(stream, {})
                    relative_path = Path(stream_binding.get("path", "missing"))
                    stream_path = transcript_root / relative_path
                    check(f"infrastructure {stream} path is capture-root relative",
                          not relative_path.is_absolute() and ".." not in relative_path.parts)
                    observed = stream_path.read_bytes() if stream_path.is_file() else None
                    check(f"infrastructure {stream} preserves complete bytes",
                          observed == expected)
                    check(f"infrastructure {stream} byte count is bound",
                          stream_binding.get("byte_length") == len(expected))
                    check(f"infrastructure {stream} SHA-256 is bound",
                          stream_binding.get("sha256") == hashlib.sha256(expected).hexdigest())
        check("infrastructure transcripts stay inside the capture root",
              all(path.parent == transcript_root for path in transcript_root.iterdir()))
        shutil.rmtree(transcript_workspace)

        if os.name == "nt":
            identity_sentinel = root / "windows-executable-identity-ran.txt"
            identity_code = (
                "from pathlib import Path;"
                f"Path({str(identity_sentinel)!r}).write_text('ran',encoding='ascii')"
            )
            relative_refused = False
            try:
                runner.fixture_process_supervisor.run_owned(
                    [Path(sys.executable).name, "-I", "-B", "-c", identity_code],
                    cwd=root, timeout_s=2,
                )
            except runner.fixture_process_supervisor.FixtureProcessError as exc:
                relative_refused = exc.code == "FIXTURE-PROCESS-SPAWN"
            check("relative Windows suite executable refuses", relative_refused)
            check("executable preflight runs no suite bytes", not identity_sentinel.exists())

            original_image_path = (
                runner.fixture_process_supervisor._windows_process_image_path
            )
            runner.fixture_process_supervisor._windows_process_image_path = (
                lambda _handle: os.path.normcase(str(root / "wrong-image.exe"))
            )
            image_refused = False
            try:
                runner.fixture_process_supervisor.run_owned(
                    [sys.executable, "-I", "-B", "-c", identity_code],
                    cwd=root, timeout_s=2,
                )
            except runner.fixture_process_supervisor.FixtureProcessError as exc:
                image_refused = exc.code == "FIXTURE-PROCESS-SPAWN"
            finally:
                runner.fixture_process_supervisor._windows_process_image_path = (
                    original_image_path
                )
            check("mismatched suspended Windows suite image refuses", image_refused)
            check("image mismatch runs no suite bytes", not identity_sentinel.exists())

            close_errors = ""
            original_close_handle = runner.fixture_process_supervisor._winapi.CloseHandle
            try:
                runner.fixture_process_supervisor._winapi.CloseHandle = (
                    lambda handle: (_ for _ in ()).throw(OSError(f"close-{handle}"))
                )
                try:
                    runner.fixture_process_supervisor._close_windows_handles(
                        (("first", 101), ("second", 202)),
                        prior=KeyboardInterrupt(),
                    )
                except runner.fixture_process_supervisor.FixtureProcessError as exc:
                    close_errors = exc.detail
            finally:
                runner.fixture_process_supervisor._winapi.CloseHandle = original_close_handle
            check(
                "multiple Windows handle-close failures are typed and aggregated",
                "first=101" in close_errors
                and "second=202" in close_errors
                and "KeyboardInterrupt" in close_errors,
            )

        unrelated = subprocess.Popen(
            [sys.executable, "-I", "-B", "-c", "import time;time.sleep(30)"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, close_fds=True,
        )
        try:
            delayed = root / "delayed-direct-descendant.txt"
            child = (
                "import time;from pathlib import Path;time.sleep(0.8);"
                f"Path({str(delayed)!r}).write_text('escaped',encoding='ascii')"
            )
            rel = _write_process_suite(root, f"""
import subprocess, sys
subprocess.Popen(
    [sys.executable, '-I', '-B', '-c', {child!r}],
    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL, close_fds=True,
)
""")
            registry = {rel: [runner._default_case(timeout_s=2)]}
            manifest = runner.MANIFEST_PATH
            manifest.parent.mkdir(parents=True, exist_ok=True)
            manifest.write_text('{"stale":true}', encoding="utf-8")
            rc = runner.run(
                registry, [rel], _test_only_allow_noncanonical_write=True,
            )
            check("direct exit with blocked descendant returns void exit 2", rc == 2, f"rc={rc}")
            check("tree refusal leaves no manifest", not manifest.exists())
            check("unrelated process survives owned-tree refusal", unrelated.poll() is None)
            time.sleep(1.0)
            check("blocked descendant cannot perform delayed mutation", not delayed.exists())

            # Exercise the cacheable basis path itself (refresh bypasses lookup)
            # and prove tree refusal occurs before staging or publication.
            cached_manifest = b'{"preserve":"cache-assisted-refusal"}\n'
            manifest.write_bytes(cached_manifest)
            runner.CACHEABLE_SUITES = frozenset({rel})
            runner._cache_root = lambda: root / "cache"
            cache_rc = runner._run_locked(
                registry, [rel], write_manifest=False, cache_mode="refresh", tier="full",
            )
            check("cache-assisted tree refusal returns void exit 2", cache_rc == 2, f"rc={cache_rc}")
            check("cache-assisted refusal performs no cache staging", cache_calls["stage"] == 0)
            check("cache-assisted refusal performs no cache publication", cache_calls["publish"] == 0)
            check(
                "cache-assisted refusal preserves prior evidence byte-for-byte",
                manifest.read_bytes() == cached_manifest,
            )
            manifest.unlink()

            grandchild_marker = root / "timeout-grandchild.txt"
            grandchild = (
                "import time;from pathlib import Path;time.sleep(0.9);"
                f"Path({str(grandchild_marker)!r}).write_text('escaped',encoding='ascii')"
            )
            child = (
                "import subprocess,sys,time;"
                f"subprocess.Popen([sys.executable,'-I','-B','-c',{grandchild!r}],"
                "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,"
                "stderr=subprocess.DEVNULL,close_fds=True);time.sleep(30)"
            )
            _write_process_suite(root, f"""
import subprocess, sys, time
subprocess.Popen(
    [sys.executable, '-I', '-B', '-c', {child!r}],
    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL, close_fds=True,
)
time.sleep(30)
""")
            timeout_registry = {rel: [runner._default_case(timeout_s=0.8)]}
            rc = runner.run(
                timeout_registry, [rel], _test_only_allow_noncanonical_write=True,
            )
            check("timeout with child and grandchild returns void exit 2", rc == 2, f"rc={rc}")
            time.sleep(1.1)
            check("timeout grandchild cannot perform delayed mutation", not grandchild_marker.exists())

            teardown_marker = root / "teardown-spawn.txt"
            spawned = (
                "import time;from pathlib import Path;time.sleep(1.0);"
                f"Path({str(teardown_marker)!r}).write_text('escaped',encoding='ascii')"
            )
            _write_process_suite(root, f"""
import subprocess, sys, time
while True:
    subprocess.Popen(
        [sys.executable, '-I', '-B', '-c', {spawned!r}],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, close_fds=True,
    )
    time.sleep(0.04)
""")
            rc = runner.run(
                {rel: [runner._default_case(timeout_s=0.8)]}, [rel],
                _test_only_allow_noncanonical_write=True,
            )
            check("dynamic teardown-spawn tree returns void exit 2", rc == 2, f"rc={rc}")
            time.sleep(1.2)
            check("dynamic teardown rescan prevents delayed mutation", not teardown_marker.exists())
            check("all refusal paths avoid cache staging", cache_calls["stage"] == 0)
            check("all refusal paths avoid cache publication", cache_calls["publish"] == 0)
            check("all refusal paths leave no manifest", not manifest.exists())

            owner_ready = root / "owner-loss.ready"
            owner_marker = root / "owner-loss-delayed.txt"
            owner_suite = root / "scripts" / "owner_loss_suite.py"
            owner_suite.write_text(
                "from pathlib import Path\nimport time\n"
                f"Path({str(owner_ready)!r}).write_text('ready',encoding='ascii')\n"
                "time.sleep(1.2)\n"
                f"Path({str(owner_marker)!r}).write_text('escaped',encoding='ascii')\n",
                encoding="utf-8", newline="\n",
            )
            driver = root / "owner_loss_driver.py"
            helper_path = HARNESS / "scripts" / "analysis" / "fixture_process_supervisor.py"
            driver.write_text(
                "import importlib.util,sys\n"
                f"spec=importlib.util.spec_from_file_location('fps_owner',{str(helper_path)!r})\n"
                "module=importlib.util.module_from_spec(spec)\n"
                "sys.modules[spec.name]=module\n"
                "spec.loader.exec_module(module)\n"
                f"module.run_owned([sys.executable,'-I','-B',{str(owner_suite)!r}],"
                f"cwd={str(root)!r},timeout_s=10)\n",
                encoding="utf-8", newline="\n",
            )
            owner = subprocess.Popen(
                [sys.executable, "-I", "-B", str(driver)],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, close_fds=True,
            )
            try:
                owner_deadline = time.monotonic() + 5
                while not owner_ready.is_file() and time.monotonic() < owner_deadline:
                    time.sleep(0.01)
                check("owner-loss fixture reached supervised execution", owner_ready.is_file())
                owner.terminate()
                owner.wait(timeout=10)
                time.sleep(1.4)
                check("runner owner loss closes the complete suite tree", not owner_marker.exists())
                check("unrelated process survives runner owner loss", unrelated.poll() is None)
            finally:
                if owner.poll() is None:
                    owner.kill()
                    owner.wait(timeout=10)

            if sys.platform.startswith("linux"):
                helper_source = inspect.getsource(
                    runner.fixture_process_supervisor._run_posix
                )
                check(
                    "POSIX product environment is absent from supervisor argv",
                    '"environment": dict(environment)' in helper_source
                    and "_write_all_before(client.stdin.fileno(), encoded" in helper_source
                    and '"_systemd_anchor", unit, systemctl' in helper_source,
                )

                unsupported_suite_marker = root / "systemd-preflight-suite-ran.txt"
                unsupported_suite = (
                    "from pathlib import Path;"
                    f"Path({str(unsupported_suite_marker)!r}).write_text('ran',encoding='ascii')"
                )
                for fault, label in (
                    ("systemd_manager_missing", "missing systemd user manager"),
                    ("non_cgroup_v2", "non-cgroup-v2 topology"),
                    ("unproven_killmode", "unproven systemd KillMode"),
                    ("nonnumeric_runtime_max", "nonnumeric systemd RuntimeMaxUSec"),
                    ("wrong_runtime_max", "wrong finite systemd RuntimeMaxUSec"),
                ):
                    preflight_refused = False
                    try:
                        runner.fixture_process_supervisor.run_owned(
                            [sys.executable, "-I", "-B", "-c", unsupported_suite],
                            cwd=root, timeout_s=3, _test_fault=fault,
                        )
                    except runner.fixture_process_supervisor.FixtureProcessError as exc:
                        preflight_refused = exc.code == "FIXTURE-PROCESS-UNSUPPORTED"
                    check(f"{label} refuses before suite bytes", preflight_refused)
                    check(
                        f"{label} leaves the suite sentinel absent",
                        not unsupported_suite_marker.exists(),
                    )

                fps = runner.fixture_process_supervisor
                original_systemd_run = fps.subprocess.run
                show_stderr_invoked = False

                def rc0_show_with_stderr(*args, **_kwargs):
                    nonlocal show_stderr_invoked
                    show_stderr_invoked = True
                    return subprocess.CompletedProcess(
                        args[0], 0, stdout=b"ActiveState=active\n",
                        stderr=b"synthetic rc0 property-query stderr",
                    )

                fps.subprocess.run = rc0_show_with_stderr
                show_stderr_refused = False
                try:
                    try:
                        fps._systemd_show(
                            "synthetic-systemctl", "synthetic.service", 1,
                        )
                    except fps.FixtureProcessError as exc:
                        show_stderr_refused = (
                            exc.code == "FIXTURE-PROCESS-UNSUPPORTED"
                            and "synthetic rc0 property-query stderr" in exc.detail
                        )
                finally:
                    fps.subprocess.run = original_systemd_run
                check(
                    "rc0 systemd property query with stderr refuses before START",
                    show_stderr_invoked and show_stderr_refused
                    and not unsupported_suite_marker.exists(),
                )

                fps = runner.fixture_process_supervisor
                parser_cases = {
                    "1s 500ms 250us": 1_500_250,
                    "2min 3.5s": 123_500_000,
                    "1h 2min 3s 4ms 5µs": 3_723_004_005,
                }
                check(
                    "systemd composite duration parser preserves exact microseconds",
                    all(
                        fps._parse_systemd_runtime_usec(raw) == expected
                        for raw, expected in parser_cases.items()
                    ),
                    repr(parser_cases),
                )

                bounded_values = {
                    "ActiveState": "active",
                    "CollectMode": "inactive-or-failed",
                    "KillMode": "control-group",
                    "KillSignal": "9",
                    "SendSIGKILL": "yes",
                    "MainPID": "4242",
                    "ControlGroup": "/user.slice/synthetic.service",
                    "ActiveEnterTimestampMonotonic": "1000000",
                    "RuntimeMaxUSec": "499999us",
                }
                bounded_deadline_ok = False
                try:
                    bounded_deadline_ok = fps._prove_systemd_unit(
                        bounded_values, pid=4242, runtime_max_usec=499_999,
                        absolute_deadline_usec=1_500_000,
                    ) == "/user.slice/synthetic.service"
                except fps.FixtureProcessError:
                    pass
                check(
                    "systemd activation plus runtime is bounded by the parent deadline",
                    bounded_deadline_ok,
                )
                late_runtime_refused = False
                try:
                    fps._prove_systemd_unit(
                        {**bounded_values, "RuntimeMaxUSec": "500001us"},
                        pid=4242, runtime_max_usec=500_001,
                        absolute_deadline_usec=1_500_000,
                    )
                except fps.FixtureProcessError as exc:
                    late_runtime_refused = (
                        exc.code == "FIXTURE-PROCESS-UNSUPPORTED"
                        and "RuntimeDeadlineUSec" in exc.detail
                    )
                check(
                    "systemd runtime extending past the parent deadline refuses",
                    late_runtime_refused,
                )

                watchdog_marker = root / "watchdog-open-failure-suite-ran.txt"
                watchdog_refused = False
                try:
                    fps = runner.fixture_process_supervisor
                    fps.run_owned(
                        [
                            sys.executable, "-I", "-B", "-c",
                            "from pathlib import Path;"
                            f"Path({str(watchdog_marker)!r}).write_text('ran',encoding='ascii')",
                        ],
                        cwd=root, timeout_s=3,
                        _test_fault="watchdog_pidfd_open_failure",
                    )
                except fps.FixtureProcessError as exc:
                    watchdog_refused = (
                        exc.code == "FIXTURE-PROCESS-LIVE"
                        and "watchdog" in exc.detail
                    )
                check(
                    "post-fork watchdog pidfd-open failure refuses",
                    watchdog_refused,
                )
                check(
                    "watchdog readiness failure reaches no suite bytes",
                    not watchdog_marker.exists(),
                )

                fps = runner.fixture_process_supervisor
                probe_read, probe_write = os.pipe()
                opened_pidfds: list[int] = []
                original_pidfd_open = fps.os.pidfd_open
                original_linux_processes = fps._linux_processes
                try:
                    observations = iter((
                        {4242: (1, "old-token")},
                        {4242: (1, "new-token")},
                    ))
                    fps._linux_processes = lambda: next(observations)
                    def fake_pidfd_open(_pid, _flags):
                        opened_pidfds.append(os.dup(probe_read))
                        return opened_pidfds[-1]
                    fps.os.pidfd_open = fake_pidfd_open
                    rollover = fps._open_pidfd_identity(4242, "old-token")
                finally:
                    fps.os.pidfd_open = original_pidfd_open
                    fps._linux_processes = original_linux_processes
                    os.close(probe_read)
                    os.close(probe_write)
                closed_rollover = False
                try:
                    os.fstat(opened_pidfds[0])
                except OSError:
                    closed_rollover = True
                check("PID token rollover refuses the stale identity", rollover is None)
                check("PID token rollover closes the stale pidfd", closed_rollover)

                signal_calls: list[tuple[int, object]] = []
                original_pidfd_signal = fps.signal.pidfd_send_signal
                signal_read, signal_write = os.pipe()
                try:
                    fps.signal.pidfd_send_signal = (
                        lambda fd, sig, _info, _flags: signal_calls.append((fd, sig))
                    )
                    fps._signal_identity(
                        fps._PidfdIdentity(4242, "stable-token", signal_read),
                        fps.signal.SIGSTOP,
                    )
                finally:
                    fps.signal.pidfd_send_signal = original_pidfd_signal
                    os.close(signal_read)
                    os.close(signal_write)
                check(
                    "owned identity signaling uses pidfd_send_signal",
                    signal_calls == [(signal_read, fps.signal.SIGSTOP)],
                )

                privacy_marker = root / "runtime-stdin-privacy.ready"
                privacy_secret = "COAUTHOR_RUNTIME_CANARY_" + uuid.uuid4().hex
                privacy_key = "COAUTHOR_FIXTURE_PRIVATE_CANARY"
                privacy_result: list[object] = []
                privacy_suite = (
                    "import os,time;from pathlib import Path;"
                    f"assert os.environ[{privacy_key!r}]=={privacy_secret!r};"
                    f"Path({str(privacy_marker)!r}).write_text('received',encoding='ascii');"
                    "time.sleep(1.0)"
                )
                def run_privacy_probe() -> None:
                    try:
                        privacy_result.append(fps.run_owned(
                            [sys.executable, "-I", "-B", "-c", privacy_suite],
                            cwd=root, timeout_s=3,
                            environment=dict(os.environ) | {privacy_key: privacy_secret},
                        ))
                    except BaseException as exc:
                        privacy_result.append(exc)
                privacy_thread = threading.Thread(target=run_privacy_probe)
                privacy_thread.start()
                privacy_deadline = time.monotonic() + 2
                while not privacy_marker.is_file() and time.monotonic() < privacy_deadline:
                    time.sleep(0.01)
                privacy_pids = (
                    fps._LAST_SYSTEMD_CLIENT_PID, fps._LAST_SYSTEMD_ANCHOR_PID,
                )
                cmdlines: list[bytes] = []
                for observed_pid in privacy_pids:
                    if isinstance(observed_pid, int):
                        try:
                            cmdlines.append(Path(
                                f"/proc/{observed_pid}/cmdline"
                            ).read_bytes())
                        except OSError:
                            cmdlines.append(b"<unreadable>")
                check(
                    "runtime stdin canary reaches the controlled suite environment",
                    privacy_marker.is_file(),
                )
                check(
                    "runtime stdin canary is absent from systemd-run and anchor argv",
                    len(cmdlines) == 2
                    and all(privacy_secret.encode("ascii") not in row for row in cmdlines)
                    and all(row != b"<unreadable>" for row in cmdlines),
                    repr(cmdlines),
                )
                privacy_thread.join(timeout=3)
                check(
                    "runtime argv privacy probe completes under the original deadline",
                    not privacy_thread.is_alive()
                    and len(privacy_result) == 1
                    and isinstance(privacy_result[0], fps.FixtureProcessResult),
                    repr(privacy_result),
                )

                interrupt_marker = root / "parent-interrupt-delayed.txt"
                interrupt_suite = root / "scripts" / "parent_interrupt_suite.py"
                interrupt_suite.write_text(
                    "from pathlib import Path\nimport time\n"
                    "time.sleep(1.0)\n"
                    f"Path({str(interrupt_marker)!r}).write_text('escaped',encoding='ascii')\n",
                    encoding="utf-8", newline="\n",
                )
                interrupted = False
                try:
                    runner.fixture_process_supervisor.run_owned(
                        [sys.executable, "-I", "-B", str(interrupt_suite)],
                        cwd=root, timeout_s=5,
                        _test_fault="parent_keyboard_interrupt",
                    )
                except KeyboardInterrupt:
                    interrupted = True
                check("parent interruption is re-raised after POSIX cleanup", interrupted)
                time.sleep(1.2)
                check(
                    "parent interruption joins cleanup before delayed mutation",
                    not interrupt_marker.exists(),
                )
                check("unrelated process survives parent interruption", unrelated.poll() is None)

                final_interrupt_marker = root / "final-cleanup-interrupt-delayed.txt"
                final_interrupt_suite = root / "scripts" / "final_cleanup_interrupt_suite.py"
                final_interrupt_suite.write_text(
                    "from pathlib import Path\nimport time\n"
                    "time.sleep(1.0)\n"
                    f"Path({str(final_interrupt_marker)!r}).write_text('escaped',encoding='ascii')\n",
                    encoding="utf-8", newline="\n",
                )
                final_interrupted = False
                try:
                    fps.run_owned(
                        [sys.executable, "-I", "-B", str(final_interrupt_suite)],
                        cwd=root, timeout_s=5,
                        _test_fault="baseexception_during_final_cleanup",
                    )
                except KeyboardInterrupt:
                    final_interrupted = True
                check("BaseException during final cleanup is re-raised", final_interrupted)
                time.sleep(1.2)
                check(
                    "final-cleanup BaseException is deferred until tree closure",
                    not final_interrupt_marker.exists(),
                )

                pidfd_close_calls: list[int] = []
                pidfd_close_injected = False
                original_close_pidfd = fps._close_pidfd

                def close_pidfd_then_fail_once(identity, **kwargs):
                    nonlocal pidfd_close_injected
                    original_close_pidfd(identity, **kwargs)
                    pidfd_close_calls.append(identity.pid)
                    if not pidfd_close_injected:
                        pidfd_close_injected = True
                        raise OSError("synthetic pidfd close failure after close")

                fps._close_pidfd = close_pidfd_then_fail_once
                pidfd_close_refused = False
                try:
                    fps.run_owned(
                        [sys.executable, "-I", "-B", "-c", "pass"],
                        cwd=root, timeout_s=2,
                    )
                except fps.FixtureProcessError as exc:
                    pidfd_close_refused = (
                        exc.code == "FIXTURE-PROCESS-LIVE"
                        and "teardown was not proven" in exc.detail
                    )
                finally:
                    fps._close_pidfd = original_close_pidfd
                check(
                    "pidfd close failure is typed after all identities are attempted",
                    pidfd_close_refused
                    and pidfd_close_injected
                    and len(set(pidfd_close_calls)) >= 2,
                    repr(pidfd_close_calls),
                )

                raw_pairs = [os.pipe(), os.pipe()]
                raw_close_fds = [fd for pair in raw_pairs for fd in pair]
                raw_close_failures: list[BaseException] = []
                raw_fds_closed = False

                def fd_is_closed(fd: int) -> bool:
                    try:
                        os.fstat(fd)
                    except OSError:
                        return True
                    return False

                try:
                    raw_close_failures = fps._close_raw_fds(
                        raw_close_fds, inject_after_first_close=True,
                    )
                    raw_fds_closed = all(
                        fd_is_closed(fd) for fd in raw_close_fds
                    )
                finally:
                    for fd in raw_close_fds:
                        try:
                            os.close(fd)
                        except OSError:
                            pass
                check(
                    "raw-pipe close failure does not skip remaining descriptors",
                    len(raw_close_failures) == 1 and raw_fds_closed,
                    repr(raw_close_failures),
                )

                raw_interrupt = SystemExit("synthetic raw-FD close interruption")
                raw_interrupt_pairs = [os.pipe(), os.pipe()]
                raw_interrupt_fds = [fd for pair in raw_interrupt_pairs for fd in pair]
                raw_interrupt_identity = False
                raw_interrupt_fds_closed = False
                try:
                    try:
                        fps._close_raw_fds(
                            raw_interrupt_fds,
                            test_interrupt_after_first_close=raw_interrupt,
                        )
                    except BaseException as exc:
                        raw_interrupt_identity = exc is raw_interrupt
                    raw_interrupt_fds_closed = all(
                        fd_is_closed(fd) for fd in raw_interrupt_fds
                    )
                finally:
                    for fd in raw_interrupt_fds:
                        try:
                            os.close(fd)
                        except OSError:
                            pass
                check(
                    "raw-FD BaseException preserves identity after all closes",
                    raw_interrupt_identity and raw_interrupt_fds_closed,
                )
                raw_pipe_close_refused = False
                try:
                    fps.run_owned(
                        [sys.executable, "-I", "-B", "-c", "pass"],
                        cwd=root, timeout_s=2,
                        _test_fault="raw_pipe_close_failure",
                    )
                except fps.FixtureProcessError as exc:
                    raw_pipe_close_refused = (
                        exc.code == "FIXTURE-PROCESS-LIVE"
                        and "deferred until closure" in exc.detail
                    )
                check(
                    "anchor raw-pipe close failure is propagated after continuation",
                    raw_pipe_close_refused,
                )

                cleanup_primitives = (
                    ("stdin_close", KeyboardInterrupt("stdin close interrupt")),
                    ("direct_kill", SystemExit("direct kill interrupt")),
                    ("pidfd_signal", KeyboardInterrupt("pidfd signal interrupt")),
                    ("pidfd_close", SystemExit("pidfd close interrupt")),
                    ("raw_fd_close", KeyboardInterrupt("raw FD close interrupt")),
                )
                for primitive, cleanup_interrupt in cleanup_primitives:
                    primitive_marker = root / f"{primitive}-interrupt-delayed.txt"
                    primitive_suite = (
                        "from pathlib import Path;import time;time.sleep(.7);"
                        f"Path({str(primitive_marker)!r}).write_text('escaped',encoding='ascii')"
                    )
                    observed_interrupt = None
                    closed_pidfd_identities: list[int] = []
                    try:
                        fps.run_owned(
                            [sys.executable, "-I", "-B", "-c", primitive_suite],
                            cwd=root, timeout_s=3,
                            _test_fault=f"baseexception_in_{primitive}",
                            _test_cleanup_interrupt=cleanup_interrupt,
                            _test_closed_pidfd_identities=closed_pidfd_identities,
                        )
                    except BaseException as exc:
                        observed_interrupt = exc
                    cgroup_proved = unit_proved = False
                    try:
                        assert fps._LAST_SYSTEMD_CGROUP is not None
                        fps._systemd_cgroup_empty(
                            fps._LAST_SYSTEMD_CGROUP, time.monotonic() + 1,
                        )
                        cgroup_proved = True
                    except (AssertionError, fps.FixtureProcessError):
                        pass
                    try:
                        assert fps._LAST_SYSTEMD_UNIT is not None
                        fps._systemd_unit_collected(
                            "systemctl", fps._LAST_SYSTEMD_UNIT,
                            time.monotonic() + 1,
                        )
                        unit_proved = True
                    except (AssertionError, fps.FixtureProcessError):
                        pass
                    time.sleep(.8)
                    check(
                        f"{primitive} BaseException identity survives complete cleanup",
                        observed_interrupt is cleanup_interrupt
                        and cgroup_proved and unit_proved
                        and (
                            primitive != "pidfd_close"
                            or len(set(closed_pidfd_identities)) >= 2
                        )
                        and not primitive_marker.exists()
                        and unrelated.poll() is None,
                        repr((observed_interrupt, closed_pidfd_identities)),
                    )

                abrupt_marker = root / "abrupt-supervisor-delayed.txt"
                abrupt_suite = root / "scripts" / "abrupt_supervisor_suite.py"
                abrupt_suite.write_text(
                    "from pathlib import Path\nimport time\n"
                    "time.sleep(1.0)\n"
                    f"Path({str(abrupt_marker)!r}).write_text('escaped',encoding='ascii')\n",
                    encoding="utf-8", newline="\n",
                )
                caller_was_subreaper = fps._child_subreaper_state()
                if not caller_was_subreaper:
                    fps._set_child_subreaper()
                try:
                    turnover_marker = root / "unrelated-turnover-adopted.txt"
                    turnover_child = (
                        "import time;from pathlib import Path;time.sleep(0.8);"
                        f"Path({str(turnover_marker)!r}).write_text('survived',encoding='ascii')"
                    )
                    turnover_parent = subprocess.Popen(
                        [
                            sys.executable, "-I", "-B", "-c",
                            "import subprocess,sys;"
                            f"subprocess.Popen([sys.executable,'-I','-B','-c',{turnover_child!r}],"
                            "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,"
                            "stderr=subprocess.DEVNULL,close_fds=True)",
                        ],
                        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL, close_fds=True,
                    )
                    turnover_parent.wait(timeout=5)

                    abrupt_refused = False
                    try:
                        runner.fixture_process_supervisor.run_owned(
                            [sys.executable, "-I", "-B", str(abrupt_suite)],
                            cwd=root, timeout_s=3,
                            _test_fault="sigkill_supervisor_after_product",
                        )
                    except runner.fixture_process_supervisor.FixtureProcessError as exc:
                        abrupt_refused = exc.code == "FIXTURE-PROCESS-LIVE"
                    check("SIGKILLed POSIX supervisor fails closed", abrupt_refused)
                    time.sleep(1.2)
                    check(
                        "dedicated anchor kills product after worker-supervisor PID loss",
                        not abrupt_marker.exists(),
                    )
                    check(
                        "unrelated process survives abrupt supervisor death",
                        unrelated.poll() is None,
                    )
                    check(
                        "already-subreaper caller keeps unrelated adoption outside anchor scope",
                        turnover_marker.exists(),
                    )
                finally:
                    fps._reap_children()
                    if not caller_was_subreaper:
                        fps._set_child_subreaper(False)

                anchor_death_marker = root / "anchor-death-delayed.txt"
                anchor_death_suite = root / "scripts" / "anchor_death_suite.py"
                anchor_death_suite.write_text(
                    "from pathlib import Path\nimport time\n"
                    "time.sleep(0.8)\n"
                    f"Path({str(anchor_death_marker)!r}).write_text('escaped',encoding='ascii')\n",
                    encoding="utf-8", newline="\n",
                )
                anchor_death_refused = False
                try:
                    fps.run_owned(
                        [sys.executable, "-I", "-B", str(anchor_death_suite)],
                        cwd=root, timeout_s=3,
                        _test_fault="sigkill_anchor_after_product",
                    )
                except fps.FixtureProcessError as exc:
                    anchor_death_refused = exc.code == "FIXTURE-PROCESS-LIVE"
                check("SIGKILLed systemd main anchor fails closed", anchor_death_refused)
                time.sleep(1.0)
                check("anchor death prevents delayed mutation", not anchor_death_marker.exists())
                check("unrelated process survives systemd anchor death", unrelated.poll() is None)
                last_cgroup = fps._LAST_SYSTEMD_CGROUP
                cgroup_empty = False
                if last_cgroup:
                    try:
                        fps._systemd_cgroup_empty(last_cgroup, time.monotonic() + 1)
                        cgroup_empty = True
                    except fps.FixtureProcessError:
                        pass
                check(
                    "anchor-death cgroup is absent or empty",
                    cgroup_empty,
                )
                last_unit = fps._LAST_SYSTEMD_UNIT
                collected_exact = False
                try:
                    fps._systemd_unit_collected(
                        "systemctl", str(last_unit), time.monotonic() + 1,
                    )
                    collected_exact = True
                except fps.FixtureProcessError:
                    pass
                check(
                    "anchor-death transient unit is inactive and collected",
                    collected_exact,
                )

                stalled_anchor_marker = root / "stalled-anchor-delayed.txt"
                stalled_anchor_suite = root / "scripts" / "stalled_anchor_suite.py"
                stalled_anchor_suite.write_text(
                    "from pathlib import Path\nimport time\n"
                    "time.sleep(0.8)\n"
                    f"Path({str(stalled_anchor_marker)!r}).write_text('escaped',encoding='ascii')\n",
                    encoding="utf-8", newline="\n",
                )
                stalled_anchor_refused = False
                stalled_anchor_started = time.monotonic()
                try:
                    fps.run_owned(
                        [sys.executable, "-I", "-B", str(stalled_anchor_suite)],
                        cwd=root, timeout_s=0.5,
                        _test_fault="stall_anchor_after_product",
                    )
                except fps.FixtureProcessError as exc:
                    stalled_anchor_refused = exc.code == "FIXTURE-PROCESS-LIVE"
                stalled_anchor_elapsed = time.monotonic() - stalled_anchor_started
                check("stalled systemd main anchor fails closed", stalled_anchor_refused)
                check(
                    "deadline watchdog kills a stalled anchor at the original deadline",
                    stalled_anchor_elapsed < 1.5 and not stalled_anchor_marker.exists(),
                    f"elapsed={stalled_anchor_elapsed:.3f}s",
                )
                check("unrelated process survives stalled anchor", unrelated.poll() is None)

                stopped_client_marker = root / "stopped-client-delayed.txt"
                stopped_client_suite = (
                    "from pathlib import Path;import time;time.sleep(.8);"
                    f"Path({str(stopped_client_marker)!r}).write_text('escaped',encoding='ascii')"
                )
                stopped_client_refused = False
                stopped_client_started = time.monotonic()
                try:
                    fps.run_owned(
                        [sys.executable, "-I", "-B", "-c", stopped_client_suite],
                        cwd=root, timeout_s=0.8,
                        _test_fault="stop_systemd_client_after_start",
                    )
                except fps.FixtureProcessError as exc:
                    stopped_client_refused = exc.code == "FIXTURE-PROCESS-LIVE"
                stopped_client_elapsed = time.monotonic() - stopped_client_started
                time.sleep(0.9)
                check("SIGSTOPped systemd-run client fails closed", stopped_client_refused)
                check(
                    "stopped systemd-run client is killed within the original deadline",
                    stopped_client_elapsed < 1.2 and not stopped_client_marker.exists(),
                    f"elapsed={stopped_client_elapsed:.3f}s",
                )
                stopped_cgroup_ok = False
                stopped_unit_ok = False
                try:
                    assert fps._LAST_SYSTEMD_CGROUP is not None
                    fps._systemd_cgroup_empty(
                        fps._LAST_SYSTEMD_CGROUP, time.monotonic() + 1,
                    )
                    stopped_cgroup_ok = True
                except (AssertionError, fps.FixtureProcessError):
                    pass
                try:
                    assert fps._LAST_SYSTEMD_UNIT is not None
                    fps._systemd_unit_collected(
                        "systemctl", fps._LAST_SYSTEMD_UNIT, time.monotonic() + 1,
                    )
                    stopped_unit_ok = True
                except (AssertionError, fps.FixtureProcessError):
                    pass
                check("stopped-client cgroup is absent or empty", stopped_cgroup_ok)
                check("stopped-client transient unit is exactly collected", stopped_unit_ok)
                check("unrelated process survives stopped systemd-run client", unrelated.poll() is None)

                collection_failure = False
                try:
                    fps.run_owned(
                        [sys.executable, "-I", "-B", "-c", "pass"],
                        cwd=root, timeout_s=2,
                        _test_fault="collection_query_failure",
                    )
                except fps.FixtureProcessError as exc:
                    collection_failure = (
                        exc.code == "FIXTURE-PROCESS-LIVE"
                        and "manager collection query failure" in exc.detail
                    )
                check(
                    "systemd manager collection-query failure is distinct and fail-closed",
                    collection_failure,
                )

                def direct_collection_failure(fake_run, expected: str) -> bool:
                    original_run = fps.subprocess.run
                    invoked = False

                    def observed_run(*args, **kwargs):
                        nonlocal invoked
                        invoked = True
                        return fake_run(*args, **kwargs)

                    fps.subprocess.run = observed_run
                    try:
                        try:
                            fps._systemd_unit_collected(
                                "synthetic-systemctl", "synthetic.service",
                                time.monotonic() + 1,
                            )
                        except fps.FixtureProcessError as exc:
                            return (
                                invoked and exc.code == "FIXTURE-PROCESS-LIVE"
                                and expected in exc.detail
                            )
                        return False
                    finally:
                        fps.subprocess.run = original_run

                check(
                    "systemd collection-query OSError branch is exercised",
                    direct_collection_failure(
                        lambda *_args, **_kwargs: (_ for _ in ()).throw(
                            OSError("synthetic manager I/O failure")
                        ),
                        "synthetic manager I/O failure",
                    ),
                )
                check(
                    "systemd collection-query timeout branch is exercised",
                    direct_collection_failure(
                        lambda *_args, **_kwargs: (_ for _ in ()).throw(
                            subprocess.TimeoutExpired("synthetic-systemctl", 1)
                        ),
                        "timed out",
                    ),
                )
                check(
                    "systemd collection-query nonzero branch is exercised",
                    direct_collection_failure(
                        lambda *args, **_kwargs: subprocess.CompletedProcess(
                            args[0], 7, stdout=b"", stderr=b"synthetic nonzero"
                        ),
                        "synthetic nonzero",
                    ),
                )
                check(
                    "systemd collection-query stderr-only branch is exercised",
                    direct_collection_failure(
                        lambda *args, **_kwargs: subprocess.CompletedProcess(
                            args[0], 0, stdout=b"", stderr=b"synthetic stderr"
                        ),
                        "synthetic stderr",
                    ),
                )

                protocol_stderr_refused = False
                try:
                    fps.run_owned(
                        [sys.executable, "-I", "-B", "-c", "pass"],
                        cwd=root, timeout_s=2,
                        _test_fault="systemd_protocol_stderr",
                    )
                except fps.FixtureProcessError as exc:
                    protocol_stderr_refused = (
                        exc.code == "FIXTURE-PROCESS-LIVE"
                        and "stderr diagnostics despite a valid result" in exc.detail
                        and "injected systemd-run stderr diagnostic" in exc.detail
                    )
                check(
                    "valid systemd protocol plus accumulated stderr refuses after closure proof",
                    protocol_stderr_refused,
                )

                missing_procs_refused = False

                class DisappearingCgroup:
                    def __init__(self) -> None:
                        self.exists_calls = 0
                        self.read_calls = 0

                    def exists(self) -> bool:
                        self.exists_calls += 1
                        return self.exists_calls == 1

                    def __truediv__(self, name: str):
                        assert name == "cgroup.procs"
                        return self

                    def read_text(self, **_kwargs):
                        self.read_calls += 1
                        raise FileNotFoundError("synthetic cgroup removal race")

                disappearing_cgroup = DisappearingCgroup()
                disappearing_race_accepted = True
                try:
                    fps._systemd_cgroup_empty(
                        "/synthetic-disappearing-cgroup", time.monotonic() + 1,
                        _test_path=disappearing_cgroup,
                    )
                except fps.FixtureProcessError:
                    disappearing_race_accepted = False
                check(
                    "cgroup removal between exists and cgroup.procs read is accepted",
                    disappearing_race_accepted
                    and disappearing_cgroup.exists_calls == 2
                    and disappearing_cgroup.read_calls == 1,
                )

                class ExistingCgroupMissingProcs:
                    def __init__(self) -> None:
                        self.exists_calls = 0
                        self.read_calls = 0

                    def exists(self) -> bool:
                        self.exists_calls += 1
                        return True

                    def __truediv__(self, name: str):
                        assert name == "cgroup.procs"
                        return self

                    def read_text(self, **_kwargs):
                        self.read_calls += 1
                        raise FileNotFoundError("synthetic missing cgroup.procs")

                existing_missing = ExistingCgroupMissingProcs()
                existing_missing_refused = False
                try:
                    fps._systemd_cgroup_empty(
                        "/synthetic-existing-cgroup", time.monotonic() + 1,
                        _test_path=existing_missing,
                    )
                except fps.FixtureProcessError as exc:
                    existing_missing_refused = (
                        exc.code == "FIXTURE-PROCESS-LIVE"
                        and "without readable cgroup.procs" in exc.detail
                    )
                check(
                    "existing cgroup plus FileNotFound cgroup.procs refuses",
                    existing_missing_refused
                    and existing_missing.exists_calls == 2
                    and existing_missing.read_calls == 1,
                )

                try:
                    fps.run_owned(
                        [sys.executable, "-I", "-B", "-c", "pass"],
                        cwd=root, timeout_s=2,
                        _test_fault="missing_cgroup_procs",
                    )
                except fps.FixtureProcessError as exc:
                    missing_procs_refused = (
                        exc.code == "FIXTURE-PROCESS-LIVE"
                        and "without readable cgroup.procs" in exc.detail
                    )
                check(
                    "existing cgroup with missing cgroup.procs is not empty proof",
                    missing_procs_refused,
                )

                cleanup_precedence = False
                try:
                    runner.fixture_process_supervisor.run_owned(
                        [sys.executable, "-I", "-B", "-c", "import time;time.sleep(2)"],
                        cwd=root, timeout_s=3,
                        _test_fault="cleanup_failure_after_primary",
                    )
                except runner.fixture_process_supervisor.FixtureProcessError as exc:
                    cleanup_precedence = (
                        exc.code == "FIXTURE-PROCESS-LIVE"
                        and "synthetic primary failure" in exc.detail
                        and "synthetic cleanup failure" in exc.detail
                    )
                check("POSIX cleanup failure overrides the earlier diagnostic", cleanup_precedence)
                check("unrelated process survives cleanup-precedence refusal", unrelated.poll() is None)

                fallback_marker = root / "stalled-supervisor-delayed.txt"
                fallback_suite = root / "scripts" / "stalled_supervisor_suite.py"
                fallback_suite.write_text(
                    "from pathlib import Path\nimport time\n"
                    "time.sleep(0.8)\n"
                    f"Path({str(fallback_marker)!r}).write_text('escaped',encoding='ascii')\n",
                    encoding="utf-8", newline="\n",
                )
                fallback_refused = False
                fallback_started = time.monotonic()
                try:
                    runner.fixture_process_supervisor.run_owned(
                        [sys.executable, "-I", "-B", str(fallback_suite)],
                        cwd=root, timeout_s=0.5,
                        _test_fault="stall_before_cleanup",
                    )
                except runner.fixture_process_supervisor.FixtureProcessError:
                    fallback_refused = True
                fallback_elapsed = time.monotonic() - fallback_started
                check("stalled POSIX supervisor fallback refuses", fallback_refused)
                check(
                    "stalled POSIX supervisor gets no second execution deadline",
                    fallback_elapsed < 1.5,
                    f"elapsed={fallback_elapsed:.3f}s",
                )
                time.sleep(1.2)
                check(
                    "stalled POSIX supervisor exact cleanup prevents delayed mutation",
                    not fallback_marker.exists(),
                )
                check("unrelated process survives exact POSIX fallback", unrelated.poll() is None)
            else:
                check(
                    "Windows uses Job-close owner-loss fallback",
                    os.name == "nt" and not owner_marker.exists(),
                )

            _write_process_suite(root, "import os\nos.write(1,b'green\\xff')\nos.write(2,b'err\\xff')\n")
            rc = runner.run(
                {rel: [runner._default_case(timeout_s=2)]}, [rel],
                _test_only_allow_noncanonical_write=True,
            )
            check("clean tree succeeds after refusals", rc == 0, f"rc={rc}")
            check(
                "runner lock is reusable after every refusal",
                not lock_state["held"]
                and lock_state["acquired"] == lock_state["released"] == 5,
                repr(lock_state),
            )
            written = json.loads(manifest.read_text(encoding="utf-8"))
            case_row = written["cases"][0]
            check("manifest schema keeps direct observed exit", case_row["observed_exit"] == 0)
            check(
                "manifest schema adds no process-tree fields",
                not any("tree" in key or "process" in key for key in case_row),
                repr(sorted(case_row)),
            )
        finally:
            if unrelated.poll() is None:
                unrelated.terminate()
            unrelated.wait(timeout=10)


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

    rc = runner.run(
        registry,
        universe,
        _test_only_allow_noncanonical_write=True,
    )
    check("initial mini run in clone returns 0", rc == 0, f"rc={rc}")

    # TRACK the manifest, then regenerate. Without the exact-path exclusion
    # this next run's evidence would be permanently stale the moment it is
    # written (the check recomputes over a tree containing the NEW manifest
    # while the record hashed the OLD one).
    _run_git(repo, "add", "docs/analysis/generated/fixture_manifest.json")
    _run_git(repo, "-c", "user.name=sbx", "-c", "user.email=sbx@localhost",
             "commit", "--quiet", "-m", "test: track fixture manifest")
    rc = runner.run(
        registry,
        universe,
        _test_only_allow_noncanonical_write=True,
    )
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
    rc = runner.run(
        registry,
        universe,
        _test_only_allow_noncanonical_write=True,
    )
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
    registered = {r.resolve() for r in roots}
    if internal.is_dir() and internal.resolve() in registered:
        check("internal worktree yields the SAME common dir",
              wp.git_common_dir(internal) == common,
              f"{wp.git_common_dir(internal)}")
        check("internal worktree yields the SAME sandbox base",
              wp.sandbox_base(internal, ".coauthor-provenance-sbx") == base)
    else:
        print("  SKIP  no registered internal worktree present to cross-check")

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
        capture_output=True, text=True, encoding="utf-8", errors="strict").stdout
    check("runner lock is invisible to git status in the primary worktree",
          "coauthor-fixture-runner.lock" not in status)
    for r in roots:
        st = subprocess.run([GIT, "-C", str(r), "status", "--porcelain", "--ignored"],
                            capture_output=True, text=True, encoding="utf-8",
                            errors="strict").stdout
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
                    "scripts/analysis/fixture_cache.py",
                    "scripts/analysis/fixture_process_supervisor.py",
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
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=180)
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



def case_suite_selector_non_authoritative(repo: Path) -> None:
    """--suite is NON_AUTHORITATIVE_PARTIAL: resolve, refuse write, fail closed.

    Named leftover from the paused quality-audit close: CLI --suite lacked
    destination-coverage regression. These probes resolve selectors in-process
    or fail on the CLI before any suite executes, and they must not write or
    void the clone's planted manifest.
    """
    runner = _load(repo / "scripts" / "analysis" / "fixture_runner.py",
                   "fr_suite_sel", repo=repo)
    runner_path = repo / "scripts" / "analysis" / "fixture_runner.py"
    exact = FAST_SUITE
    basename = Path(exact).name
    stem = Path(exact).stem

    selected = runner.resolve_suite_selectors([exact])
    check("exact REGISTRY path resolves",
          list(selected) == [exact], str(list(selected)))
    selected = runner.resolve_suite_selectors([basename])
    check("unique basename resolves",
          list(selected) == [exact], str(list(selected)))
    selected = runner.resolve_suite_selectors([stem])
    check("unique stem resolves",
          list(selected) == [exact], str(list(selected)))

    unknown_raised = False
    try:
        runner.resolve_suite_selectors(["not-a-registry-key-zz"])
    except ValueError as exc:
        unknown_raised = "not a REGISTRY key" in str(exc)
    check("unknown key raises ValueError", unknown_raised)

    dummy = runner.MANIFEST_PATH
    dummy.parent.mkdir(parents=True, exist_ok=True)
    dummy.write_text('{"sentinel": "suite-selector-must-survive"}', encoding="utf-8")
    before = dummy.read_bytes()

    def _cli(*extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(runner_path), *extra],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(repo), timeout=30)

    proc = _cli("--suite", exact)
    out = proc.stdout + proc.stderr
    check("--suite without --no-write exits 2", proc.returncode == 2,
          f"rc={proc.returncode}")
    check("--suite without --no-write names the requirement",
          "requires --no-write" in out)
    check("--suite without --no-write leaves committed evidence untouched",
          dummy.read_bytes() == before)

    proc = _cli("--suite", "not-a-registry-key-zz", "--no-write")
    out = proc.stdout + proc.stderr
    check("unknown --suite key exits 2", proc.returncode == 2,
          f"rc={proc.returncode}")
    check("unknown --suite key is named", "not a REGISTRY key" in out)
    check("unknown --suite key leaves committed evidence untouched",
          dummy.read_bytes() == before)

    proc = _cli("--suite", exact, "--tier", "quick", "--no-write")
    out = proc.stdout + proc.stderr
    check("--suite + --tier quick exits 2", proc.returncode == 2,
          f"rc={proc.returncode}")
    check("--suite + --tier quick names the refusal",
          "cannot be combined with --tier quick" in out)
    check("--suite + --tier quick leaves committed evidence untouched",
          dummy.read_bytes() == before)

    registry = {exact: runner.REGISTRY[exact]}
    rc = runner.run(registry, [exact], write_manifest=True, tier="suite")
    check("tier=suite write is refused (exit 2)", rc == 2, f"rc={rc}")
    check("tier=suite cannot write or void the committed manifest",
          dummy.is_file() and dummy.read_bytes() == before)

def main() -> int:
    print("fixture_infrastructure_check (focused; never runs the corpus)")
    print(f"  harness: {HARNESS}")
    print()
    if sys.argv[1:]:
        if sys.argv[1:] != ["--process-tree-only"]:
            print(f"ERROR: unsupported arguments: {sys.argv[1:]}", file=sys.stderr)
            return 2
        print("case_suite_process_tree_ownership:")
        case_suite_process_tree_ownership()
        if FAILURES:
            print(f"\nFAIL: {len(FAILURES)}: {FAILURES}")
            return 1
        print("\nPASS: fixture suite process-tree ownership holds")
        return 0
    print("case_repo_global_paths:")
    case_repo_global_paths()
    print()
    print("case_census_writer_binding:")
    case_static_matrix_does_not_consume_execution_receipts()
    case_census_writer_binding()
    print()
    print("case_cache_contract:")
    case_cache_contract()
    print()
    # Clone base derived repo-globally, like every other sandbox (F1): under
    # `.worktrees/` the old `HARNESS.parent` base put clones inside the repo.
    base = Path(tempfile.mkdtemp(prefix="fic-",
                                 dir=str(sandbox_base(HARNESS, ".coauthor-fic-sbx"))))
    try:
        repo = _make_clone(base)
        print("case_checkout_digest_portability:")
        case_checkout_digest_portability(repo)
        print()
        print("case_runner_concurrency_and_void:")
        case_runner_concurrency_and_void(repo)
        print()
        print("case_suite_selector_non_authoritative:")
        case_suite_selector_non_authoritative(repo)
        print()
        print("case_suite_process_tree_ownership:")
        case_suite_process_tree_ownership()
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
