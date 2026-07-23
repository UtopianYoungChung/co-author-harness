#!/usr/bin/env python3
"""fixture_runner - the AUTHORITATIVE WRITER of fixture_manifest.json.

Why a runner writes the manifest
--------------------------------
code_census.py's SUITE-BOUND MANIFEST CONSISTENCY check states its own limit:
a document that describes itself cannot prove that its rows exhaust a suite's
cases, nor that any case ever RAN -- `case_count == len(cases)` compares the
manifest to itself. Completion stays ASSERTED EVIDENCE until "a central
runner is the authoritative writer and its case registry drives execution --
i.e. the manifest is a side effect of running, not an artifact someone
writes." This module is that runner.

What a manifest written here PROVES:
  * every registered suite EXECUTED, under its registered invocation, in
    this process, in this run (one run_id);
  * each execution's exit code equaled the registry's declared expectation
    -- a mismatch aborts the run and NO manifest is written;
  * the code under test was canonically identical and the checkout's raw bytes
    were byte-identical before and after the run (two separately labelled
    pre/post digests over the packaging authority's population);
  * each suite's bytes are the hashed bytes (suite_sha256 at write time,
    inside the pre==post window).

What it still does NOT prove, stated rather than overclaimed:
  * per-case coverage INSIDE a suite. Granularity here is one case per
    suite invocation ("default"): the suites are self-contained programs
    that run their own internal fixtures and fold the result into one exit
    code. Extracting native per-case rows requires each suite to emit them
    as a side effect of its own execution -- future work, per suite. Until
    then every case is declared under the EXIT-ONLY contract with
    expected_code null, which is exactly what a whole-suite invocation
    emits. No MFHP-9 / PRE-PHASE vocabulary is claimed at this granularity,
    because the suite PROCESS does not speak it -- its subjects do.

Registry discipline
-------------------
The suite UNIVERSE is owned by code_census.discover_suite_universe() (any
file under scripts/ matching a fixture marker; no content filter). The
REGISTRY here is this runner's declaration of HOW to run each suite and what
exit to expect. The two are reconciled in BOTH directions before anything
runs: an unregistered discovered suite fails the run (a new smoketest cannot
silently ship unexecuted), and a registered path that is no longer
discovered fails it too (the registry cannot pin phantom suites).
Expectations were established empirically 2026-07-16: all 31 suites exit 0
under a bare `python <suite>` from the repo root (probe log, ~6.5 min).

Failure semantics (three outcomes, as everywhere in this workstream)
--------------------------------------------------------------------
  exit 0  every registered case ran and matched; manifest written
  exit 1  a case's observed exit != declared expectation -> SUBJECT wrong.
          Mismatches are COLLECTED across all suites (the run completes for
          diagnostics; it does not abort at the first failure) and NO
          manifest is written.
  exit 2  environment failure (spawn error, timeout, pre/post digest
          mismatch, registry/universe disagreement, lock held by another
          runner) -> run VOID; no manifest is written.

In evidence-writing mode, evidence never outlives the run that supersedes it:
the PRIOR manifest is
voided immediately after the lock is acquired and before the first suite
executes, so a red or void run cannot leave old green evidence visible --
regardless of where in the run it failed. `--no-write` is the CI/release
verification mode: it executes the same registry but never touches committed
evidence.

Concurrency
-----------
Exactly one runner may execute at a time PER REPOSITORY -- not per worktree.
The lock lives in the shared git admin directory (`--git-common-dir`, i.e.
`<primary>/.git/coauthor-fixture-runner.lock`), an OS-level region lock that
dies with the process, acquired BEFORE evidence is touched or any suite
starts. A second concurrent runner -- from the same worktree OR any other
worktree of this repository -- fails cleanly with exit 2, executes no suites,
and, critically, voids nothing: only the lock HOLDER may touch evidence.
Suites share sandbox locations (the provenance smoketest sweeps
`.coauthor-provenance-sbx` at start, which is itself derived repo-globally),
so concurrent corpus runs would corrupt each other's verdicts. A per-worktree
lock gave each checkout its own lock and permitted exactly that.

Commit-stability
----------------
The manifest itself is excluded (by exact path) from the tested-inputs
population -- see TESTED_INPUT_EXCLUDE in code_census.py. Without that
exclusion, tracking the manifest would make every run self-stale: the
runner would hash the old manifest into pre/post and then overwrite it.
The manifest is written to a run-unique temp name and moved into place
atomically.

Usage
-----
    python scripts/analysis/fixture_runner.py            # run + write
    python scripts/analysis/fixture_runner.py --no-write # run, preserve evidence
    python scripts/analysis/fixture_runner.py --list     # show registry
Exit: 0 pass; 1 corpus failure; 2 run void.
"""

from __future__ import annotations

import argparse
import importlib.util
import io
import json
import hashlib
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

# Same console discipline as the census: UTF-8 in-process, ASCII out.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
else:  # pragma: no cover
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent
MANIFEST_PATH = PLUGIN_ROOT / "docs" / "analysis" / "generated" / "fixture_manifest.json"
SUITE_TIMEOUT_S = 900

# THE LOCK IS REPOSITORY-GLOBAL, NOT PER-WORKTREE (2026-07-16, review F2).
#
# It was `PLUGIN_ROOT/docs/analysis/generated/.fixture_runner.lock` -- one lock
# per worktree, so two worktrees of the SAME repository each took their own
# lock and ran the shared corpus concurrently. That is precisely the collision
# the lock exists to prevent: the suites share sandbox bases (the provenance
# smoketest SWEEPS its base at start, deleting a concurrent run's live
# sandbox), so the mutual exclusion has to span every checkout of the repo.
#
# The shared git admin directory is the one location every worktree agrees on
# (`--git-common-dir` is identical from primary, internal, and external
# worktrees -- `--git-dir` is not). It is also outside every working tree, so
# no worktree gains an untracked .fixture_runner.lock to clean up or
# accidentally commit.
def _lock_path() -> Path:
    from worktree_paths import git_common_dir  # local: keeps import order clear
    return git_common_dir(PLUGIN_ROOT) / "coauthor-fixture-runner.lock"

# One authority for universe + tested-inputs, imported by EXACT PATH. The
# previous `sys.path.insert(0, scripts/analysis); sys.path.insert(0, scripts)`
# left `scripts` FIRST on the path, so a file named scripts/code_census.py
# would silently shadow the intended scripts/analysis/code_census.py -- the
# build_plugin_shim hijack shape, reintroduced by insertion order. Spec-load
# from the resolved path; no name resolution, nothing to shadow. If this
# fails, the runner must die.
_CENSUS_PATH = PLUGIN_ROOT / "scripts" / "analysis" / "code_census.py"
_spec = importlib.util.spec_from_file_location("code_census", _CENSUS_PATH)
code_census = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(code_census)
assert Path(code_census.__file__).resolve() == _CENSUS_PATH.resolve()
compute_tested_inputs = code_census.compute_tested_inputs
discover_suite_universe = code_census.discover_suite_universe


def _default_case() -> dict:
    """The suite-level invocation contract: bare run, exit 0, EXIT-ONLY.

    A helper, not an auto-registration: every suite below is REGISTERED BY
    NAME. Deriving the registry from the universe would make a new suite
    self-register and the unregistered-suite failure unreachable.
    """
    return {
        "case_id": "default",
        "argv": [],
        "expected_exit": 0,
        "expected_code": None,
        "outcome_contract": "EXIT-ONLY",
        "expected_outcome": None,
    }


# fixture_file -> list of registered cases. Empirical basis: 2026-07-16 probe,
# every suite exit 0 bare. A suite needing args or a nonzero expectation gets
# its own literal entry; do not widen _default_case for one suite's needs.
REGISTRY: dict[str, list[dict]] = {
    "scripts/alias_parity_smoketest.py": [_default_case()],
    "scripts/command_surface_smoketest.py": [_default_case()],
    "scripts/assignment_dispatch_preflight_smoketest.py": [_default_case()],
    "scripts/assignment_process_gate_smoketest.py": [_default_case()],
    "scripts/assignment_receipt_transaction_smoketest.py": [_default_case()],
    "scripts/assignment_milestone_checkpoint_smoketest.py": [_default_case()],
    "scripts/assignment_terminal_close_smoketest.py": [_default_case()],
    "scripts/artefact_frontmatter_smoketest.py": [_default_case()],
    "scripts/audit/test_audit.py": [_default_case()],
    "scripts/audit/test_citations.py": [_default_case()],
    "scripts/build_plugin_provenance_smoketest.py": [_default_case()],
    "scripts/capability_contract_smoketest.py": [_default_case()],
    "scripts/centroid_service_smoketest.py": [_default_case()],
    "scripts/draft_governance_smoketest.py": [_default_case()],
    "scripts/concept_introduction_contract_smoketest.py": [_default_case()],
    "scripts/contract_kernel_coherence_smoketest.py": [_default_case()],
    "scripts/corpus_root_portability_smoketest.py": [_default_case()],
    "scripts/d_style_profile_smoketest.py": [_default_case()],
    "scripts/destination_capability_smoketest.py": [_default_case()],
    "scripts/domain_native_register_smoketest.py": [_default_case()],
    "scripts/distribution_rights_smoketest.py": [_default_case()],
    "scripts/end_to_end_smoketest.py": [_default_case()],
    "scripts/full_run_contract_smoketest.py": [_default_case()],
    "scripts/full_run_enforcement_surfaces_smoketest.py": [_default_case()],
    "scripts/full_run_semantic_bypass_smoketest.py": [_default_case()],
    "scripts/fixture_authority_smoketest.py": [_default_case()],
    "scripts/graph_authority_gate_smoketest.py": [_default_case()],
    "scripts/lifecycle_contract_smoketest.py": [_default_case()],
    "scripts/loader_compat_portability_smoketest.py": [_default_case()],
    "scripts/mcr_convergence_evidence_smoketest.py": [_default_case()],
    "scripts/migrate_legacy_milestones_adversarial_smoketest.py": [_default_case()],
    "scripts/migrate_legacy_milestones_smoketest.py": [_default_case()],
    "scripts/migrate_v0150pre_stage_profile_smoketest.py": [_default_case()],
    "scripts/milestone_framework_smoketest.py": [_default_case()],
    "scripts/milestone_path_contract_smoketest.py": [_default_case()],
    "scripts/native_project_bootstrap_adversarial_smoketest.py": [_default_case()],
    "scripts/native_project_bootstrap_smoketest.py": [_default_case()],
    "scripts/output_economy_smoketest.py": [_default_case()],
    "scripts/paragraph_hash_map_smoketest.py": [_default_case()],
    "scripts/phase_notifications_smoketest.py": [_default_case()],
    "scripts/phase_state_validator_smoketest.py": [_default_case()],
    "scripts/pre_phase_advance_phase_state_smoketest.py": [_default_case()],
    "scripts/reader_accessibility_adversarial_smoketest.py": [_default_case()],
    "scripts/reader_accessibility_contract_smoketest.py": [_default_case()],
    "scripts/reader_accessibility_semantics_smoketest.py": [_default_case()],
    "scripts/release_source_parity_smoketest.py": [_default_case()],
    "scripts/reflector_split_parity_smoketest.py": [_default_case()],
    "scripts/render_lifecycle_state_adversarial_smoketest.py": [_default_case()],
    "scripts/render_lifecycle_state_smoketest.py": [_default_case()],
    "scripts/repin_register_smoketest.py": [_default_case()],
    "scripts/retirement_sweep_smoketest.py": [_default_case()],
    "scripts/routing_role_coherence_smoketest.py": [_default_case()],
    "scripts/semantic_predication_contract_smoketest.py": [_default_case()],
    "scripts/shipment_manifest_smoketest.py": [_default_case()],
    "scripts/staging_authority_mode_smoketest.py": [_default_case()],
    "scripts/subprocess_text_policy_smoketest.py": [_default_case()],
    "scripts/tests/test_resolve_includes.py": [_default_case()],
    "scripts/token_budget_smoketest.py": [_default_case()],
    "scripts/version_policy_smoketest.py": [_default_case()],
}


def _void_stale_manifest(reason: str) -> None:
    """A failed or void run must not leave prior evidence standing.

    If the tree is unchanged since the last good run, a stale manifest would
    keep PASSING the census's hash binding while the corpus is currently red
    -- evidence and reality diverging behind matching hashes. Called only by
    the LOCK HOLDER (see _acquire_lock): a runner that lost the lock race
    must never touch evidence.
    """
    if MANIFEST_PATH.is_file():
        MANIFEST_PATH.unlink()
        print(f"  voided existing manifest ({reason})")


def _acquire_lock():
    """Cross-process, cross-WORKTREE exclusive runner lock, or None if held.

    OS-level region lock on an open handle (msvcrt on Windows, flock on
    POSIX): released by the OS when the process dies, so a crashed runner
    cannot wedge the lock the way an existence-check lockfile would. The
    lock file lives in the shared git admin dir (see _lock_path), so every
    worktree contends for ONE lock. It carries the holder's pid and worktree
    as diagnostics; those are informational, never the lock.
    """
    lock_path = _lock_path()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(lock_path, "a+", encoding="utf-8")
    try:
        if os.name == "nt":
            import msvcrt
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        fh.close()
        return None
    fh.seek(0)
    fh.truncate()
    fh.write(f"pid={os.getpid()} worktree={PLUGIN_ROOT}\n")
    fh.flush()
    return fh


def _release_lock(fh) -> None:
    try:
        if os.name == "nt":
            import msvcrt
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    finally:
        fh.close()


def run(registry: dict[str, list[dict]],
        universe: list[str] | None = None,
        *, write_manifest: bool = True) -> int:
    """Execute the registry; write the manifest only on a fully green run.

    `universe` exists for focused tests ONLY (they exercise the runner with
    a one-suite registry without launching the whole corpus); production
    callers pass nothing and get the discovered universe.
    """
    if not registry:
        print("ERROR: empty registry; nothing to execute is not evidence",
              file=sys.stderr)
        return 2

    lock = _acquire_lock()
    if lock is None:
        holder = ""
        try:
            holder = _lock_path().read_text(encoding="utf-8").strip()
        except OSError:
            pass
        print(f"ERROR: another fixture runner holds the repository-global lock "
              f"({_lock_path()}); refusing to run concurrently. Holder: "
              f"{holder or 'unknown'}. No suites were executed; existing "
              "evidence untouched.", file=sys.stderr)
        return 2
    try:
        return _run_locked(registry, universe, write_manifest=write_manifest)
    finally:
        _release_lock(lock)


def _run_locked(registry: dict[str, list[dict]],
                universe_arg: list[str] | None,
                *, write_manifest: bool) -> int:
    universe = set(universe_arg if universe_arg is not None
                   else discover_suite_universe())
    registered = set(registry)
    unregistered = sorted(universe - registered)
    phantom = sorted(registered - universe)
    if unregistered or phantom:
        for s in unregistered:
            print(f"ERROR: discovered suite not registered: {s}", file=sys.stderr)
        for s in phantom:
            print(f"ERROR: registry names undiscovered suite: {s}", file=sys.stderr)
        if write_manifest:
            _void_stale_manifest("registry/universe mismatch")
        return 2

    print(f"fixture_runner: {len(universe)} suites, "
          f"{sum(len(v) for v in registry.values())} registered case(s)")

    # VOID PRIOR EVIDENCE NOW -- after the lock, before the first suite. From
    # this point there is no green manifest until THIS run earns one, so a
    # failure anywhere below cannot leave stale evidence visible.
    if write_manifest:
        _void_stale_manifest("superseded by the run now starting")

    pre = compute_tested_inputs()
    print(f"  tested-inputs canonical pre: {pre['sha256'][:12]} "
          f"({pre['file_count']} files)")
    print(f"  tested-inputs raw pre:       {pre['raw_sha256'][:12]} "
          "(checkout-local)")

    run_id = str(uuid.uuid4())
    cases_out: list[dict] = []
    suites_out: list[dict] = []
    failures: list[str] = []

    for rel in sorted(registry):
        suite_path = PLUGIN_ROOT / rel
        for case in registry[rel]:
            argv = [sys.executable, str(suite_path), *case["argv"]]
            t0 = time.time()
            try:
                proc = subprocess.run(argv, cwd=str(PLUGIN_ROOT), capture_output=True,
                                      text=True, encoding="utf-8", errors="replace",
                                      timeout=SUITE_TIMEOUT_S)
            except (OSError, subprocess.TimeoutExpired) as exc:
                print(f"ERROR: {rel}::{case['case_id']}: {type(exc).__name__}: {exc}",
                      file=sys.stderr)
                # Prior evidence was already voided at run start; nothing to
                # clean up -- the run simply ends with no manifest.
                return 2
            secs = round(time.time() - t0, 1)
            ok = proc.returncode == case["expected_exit"]
            print(f"  {'PASS' if ok else 'FAIL'}  exit {proc.returncode} "
                  f"(want {case['expected_exit']})  {secs:>7}s  {rel}::{case['case_id']}")
            if not ok:
                tail = (proc.stdout + proc.stderr).strip().splitlines()[-2:]
                failures.append(f"{rel}::{case['case_id']}: exit "
                                f"{proc.returncode} != {case['expected_exit']} | {tail}")
            cases_out.append({
                "fixture_file": rel,
                "case_id": case["case_id"],
                "expected_exit": case["expected_exit"],
                "expected_code": case["expected_code"],
                "outcome_contract": case["outcome_contract"],
                "expected_outcome": case["expected_outcome"],
                # Observed evidence (extra fields; census ignores them).
                "observed_exit": proc.returncode,
                "duration_s": secs,
            })
        suites_out.append({
            "fixture_file": rel,
            "suite_sha256": hashlib.sha256(suite_path.read_bytes()).hexdigest(),
            "case_count": len(registry[rel]),
            "run_id": run_id,
        })

    post = compute_tested_inputs()
    print(f"  tested-inputs canonical post: {post['sha256'][:12]} "
          f"({post['file_count']} files)")
    print(f"  tested-inputs raw post:       {post['raw_sha256'][:12]} "
          "(checkout-local)")
    if ((pre["sha256"], pre["raw_sha256"], pre["file_count"])
            != (post["sha256"], post["raw_sha256"], post["file_count"])):
        print("ERROR: code under test changed DURING the run; results describe "
              "no single tree", file=sys.stderr)
        return 2

    if failures:
        print(f"\nFAIL: {len(failures)} case(s):")
        for f in failures:
            print(f"  {f}")
        print("  no manifest written; " + (
            "prior evidence was voided at run start"
            if write_manifest else "--no-write preserved prior evidence"
        ))
        return 1

    if not write_manifest:
        print(f"\nPASS: {len(suites_out)} suites, {len(cases_out)} cases; "
              "--no-write preserved committed evidence")
        return 0

    manifest = {
        "schema": "coauthor-fixture-manifest/v1",
        "written_by": "scripts/analysis/fixture_runner.py",
        # FULL sha256, verified (not merely recorded) by the census's writer
        # binding against the runner file on disk at check time.
        "runner_sha256": hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest(),
        "granularity": "suite",
        "run_id": run_id,
        "suites": suites_out,
        "cases": cases_out,
        "tested_inputs": {
            "mode": pre["mode"],
            "enumerator": pre["enumerator"],
            # Two categories, recorded by match rule (review F3): prefixes and
            # exact paths are not interchangeable and must not share a field.
            "exclude_dirs": pre["exclude_dirs"],
            "exclude_files": pre["exclude_files"],
            "file_count": pre["file_count"],
            "pre_sha256": pre["sha256"],
            "post_sha256": post["sha256"],
            "raw_mode": pre["raw_mode"],
            "raw_pre_sha256": pre["raw_sha256"],
            "raw_post_sha256": post["raw_sha256"],
        },
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Run-unique temp name: a fixed .tmp name is a rendezvous point for any
    # future concurrent writer (belt to the lock's braces), and a crashed
    # run's leftover can never be mistaken for another run's in-flight file.
    tmp = MANIFEST_PATH.with_name(f"fixture_manifest.{run_id}.tmp")
    # LF explicitly: this repo normalizes text to LF at commit, so a CRLF
    # worktree write would hash differently from its own fresh checkout and
    # the evidence would go stale the moment it was committed and re-checked
    # out. Worktree bytes must equal blob bytes.
    tmp.write_text(json.dumps(manifest, indent=1, sort_keys=True),
                   encoding="utf-8", newline="\n")
    tmp.replace(MANIFEST_PATH)
    print(f"\nPASS: manifest written as a side effect of execution: "
          f"{MANIFEST_PATH.relative_to(PLUGIN_ROOT).as_posix()}")
    print(f"  run_id {run_id}; {len(suites_out)} suites, {len(cases_out)} cases")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="print the registry and exit")
    ap.add_argument(
        "--no-write",
        action="store_true",
        help="run the authoritative registry without rewriting or voiding the manifest",
    )
    args = ap.parse_args()
    if args.list:
        for rel in sorted(REGISTRY):
            for c in REGISTRY[rel]:
                print(f"{rel}::{c['case_id']}  argv={c['argv']}  "
                      f"expect exit {c['expected_exit']}  {c['outcome_contract']}")
        return 0
    return run(REGISTRY, write_manifest=not args.no_write)


if __name__ == "__main__":
    sys.exit(main())
