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


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Resolve git the same way the packaging authority does -- import it, do not
# re-author it.
sys.path.insert(0, str(HARNESS / "scripts"))
from package_enumeration import GIT  # noqa: E402


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
                "scripts/analysis/fixture_runner.py"):
        shutil.copy2(HARNESS / rel, repo / rel)
    return repo


def _mini_registry(runner_mod) -> tuple[dict, list[str]]:
    return {FAST_SUITE: [runner_mod._default_case()]}, [FAST_SUITE]


# --------------------------------------------------------------------------
# R2: census writer-binding negatives (synthetic manifest, temp path, real repo)
# --------------------------------------------------------------------------

def case_census_writer_binding() -> None:
    census = _load(HARNESS / "scripts" / "analysis" / "code_census.py", "cc_real")
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
                "exclude": ti["exclude"], "file_count": ti["file_count"],
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

    # R1 exclusion shape: exact file, machine-recorded, no broad prefix.
    check("manifest excluded from tested inputs (exact path)",
          "docs/analysis/generated/fixture_manifest.json" in census.TESTED_INPUT_EXCLUDE)
    check("exclusion recorded in tested_inputs.exclude",
          "docs/analysis/generated/fixture_manifest.json" in ti["exclude"])
    check("no broad generated-docs exclusion",
          not any(x in ("docs/", "docs/analysis/", "docs/analysis/generated/")
                  for x in census.TESTED_INPUT_EXCLUDE))


# --------------------------------------------------------------------------
# R3: runner concurrency + void semantics (disposable clone)
# --------------------------------------------------------------------------

def case_runner_concurrency_and_void(repo: Path) -> None:
    runner = _load(repo / "scripts" / "analysis" / "fixture_runner.py", "fr_clone")
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
    runner = _load(repo / "scripts" / "analysis" / "fixture_runner.py", "fr_clone2")
    census = _load(repo / "scripts" / "analysis" / "code_census.py", "cc_clone")
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


def main() -> int:
    print("fixture_infrastructure_check (focused; never runs the corpus)")
    print(f"  harness: {HARNESS}")
    print()
    print("case_census_writer_binding:")
    case_census_writer_binding()
    print()
    base = Path(tempfile.mkdtemp(prefix="fic-", dir=str(HARNESS.parent)))
    try:
        repo = _make_clone(base)
        print("case_runner_concurrency_and_void:")
        case_runner_concurrency_and_void(repo)
        print()
        print("case_commit_stability:")
        case_commit_stability(repo)
    finally:
        _rmtree_force(base)
        leftover = base.exists()
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
