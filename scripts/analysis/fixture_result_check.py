#!/usr/bin/env python3
"""Verify an opt-in controlled full corpus for reuse by the five-plane gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
ANALYSIS = SCRIPTS / "analysis"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ANALYSIS))
import release_qualification_controller as controller  # noqa: E402
import fixture_runner as runner  # noqa: E402

MANIFEST_REL = "docs/analysis/generated/fixture_manifest.json"
MANIFEST = ROOT / MANIFEST_REL
PREFIX = "QUALIFICATION_PROOF "


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "--no-optional-locks", "-C", str(ROOT), *args],
        capture_output=True, text=True, encoding="utf-8", errors="strict", check=True,
    ).stdout.strip()


def check(raw_run_dir: Path) -> None:
    lexical = raw_run_dir.absolute()
    for part in (lexical, *lexical.parents):
        require(not controller._is_reparse(part), "run directory has reparse path")
    run_dir = lexical.resolve(strict=True)
    require(run_dir.is_dir(), "run directory unavailable")
    receipt = controller.status_run(run_root=run_dir.parent, run_id=run_dir.name)
    require(receipt["state"] == "succeeded" and receipt["exit"] == {"returncode": 0},
            "controlled run failed")
    argv = receipt["argv"]
    expected = [sys.executable, "-u", "-X", "utf8", "-B",
                str((ANALYSIS / "fixture_runner.py").resolve()), "--qualification-proof"]
    if len(argv) == len(expected) + 2:
        require(argv[:len(expected)] == expected and argv[-2] == "--failure-transcript-root",
                "unexpected producer argv")
        transcript = Path(argv[-1])
        require(transcript.is_absolute() and transcript.is_dir()
                and not controller._is_reparse(transcript),
                "transcript root invalid")
    else:
        require(argv == expected, "unexpected producer argv")
    require(Path(receipt["cwd"]).resolve() == ROOT, "producer cwd differs")
    require(len(receipt["input_roots"]) == 1, "producer input root is not Source alone")
    prior = receipt["input_roots"][0]
    require(Path(prior["path"]).resolve() == ROOT, "producer input root differs")
    lock = runner._lock_path()
    ignored = {str(MANIFEST.resolve(strict=True)), str(lock.resolve(strict=True))}
    require(set(receipt["ignored_output_paths"]) == ignored
            and len(receipt["ignored_output_paths"]) == len(ignored),
            "producer ignored paths differ from exact manifest and lock")
    current = controller._input_root_binding(ROOT, ignored_paths=(MANIFEST, lock))
    ignored_lexical = {controller._lexical(MANIFEST), controller._lexical(lock)}
    recorded = {k: v for k, v in prior["inventory"].items() if k not in ignored_lexical}
    require(recorded == current["inventory"],
            "producer input bytes changed beyond manifest/lock")
    require(_git("symbolic-ref", "--short", "HEAD") == "main", "Source is not main")
    require(not _git("status", "--porcelain=v1", "--untracked-files=all"), "Source is dirty")
    raw = Path(receipt["stdout"]["path"]).read_bytes().decode("utf-8", errors="strict")
    lines = [line[len(PREFIX):] for line in raw.splitlines() if line.startswith(PREFIX)]
    require(len(lines) == 1, "producer did not emit exactly one proof")
    proof = json.loads(lines[0])
    require(isinstance(proof, dict) and set(proof) == {
        "manifest_sha256", "run_id", "head", "tree", "runner_sha256", "census_sha256",
    }, "proof fields differ")
    require(re.fullmatch(r"[0-9a-f]{64}", proof["manifest_sha256"]) is not None,
            "manifest digest malformed")
    require(re.fullmatch(r"[0-9a-f]{40,64}", proof["head"]) is not None,
            "producer commit malformed")
    require(re.fullmatch(r"[0-9a-f]{40,64}", proof["tree"]) is not None,
            "producer tree malformed")
    require(_sha(MANIFEST) == proof["manifest_sha256"], "manifest bytes differ")
    require(_sha(ANALYSIS / "fixture_runner.py") == proof["runner_sha256"],
            "runner bytes differ")
    require(_sha(ANALYSIS / "code_census.py") == proof["census_sha256"],
            "census bytes differ")
    require(_git("rev-parse", proof["head"] + "^{tree}") == proof["tree"],
            "producer Git tree differs")
    head = _git("rev-parse", "HEAD")
    if head != proof["head"]:
        require(_git("rev-list", "--parents", "-n", "1", "HEAD").split()
                == [head, proof["head"]], "not immediate successor")
        require(_git("diff", "--name-only", proof["head"], head).splitlines()
                == [MANIFEST_REL], "successor is not manifest-only")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    require(manifest["run_id"] == proof["run_id"]
            and manifest["runner_sha256"] == proof["runner_sha256"],
            "manifest identity differs")
    cases = manifest["cases"]
    expected_cases = {(key, case["case_id"]): case
                      for key, suite in runner.REGISTRY.items() for case in suite}
    actual_cases = {(case["fixture_file"], case["case_id"]): case for case in cases}
    require(len(cases) == len(expected_cases) == len(actual_cases), "case count differs")
    require(set(actual_cases) == set(expected_cases)
            and set(runner.REGISTRY) == set(runner.discover_suite_universe()),
            "registry membership differs")
    contract = ("expected_exit", "expected_code", "outcome_contract", "expected_outcome")
    for key, case in actual_cases.items():
        declared = expected_cases[key]
        require(all(type(case[field]) is type(declared[field])
                    and case[field] == declared[field] for field in contract),
                "registry case contract differs")
        require(case["execution_source"] == "EXEC"
                and case.get("cached_source_run_id") is None
                and type(case["observed_exit"]) is int
                and case["observed_exit"] == case["expected_exit"],
                "cached or failed case")
    report = runner.code_census.build_report()
    ok, detail = runner.code_census._check_suite_bound_manifest_consistency(report)
    require(ok, detail)
    current_inputs = runner.compute_tested_inputs()
    tested = manifest["tested_inputs"]
    require(tested["pre_sha256"] == tested["post_sha256"] == current_inputs["sha256"]
            and tested["raw_pre_sha256"] == tested["raw_post_sha256"]
            == current_inputs["raw_sha256"], "tested inputs drifted")
    print("FIXTURE-REUSE PASS")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-run", type=Path, required=True)
    args = parser.parse_args()
    try:
        check(args.fixture_run)
    except (OSError, ValueError, KeyError, TypeError, UnicodeError,
            subprocess.CalledProcessError, controller.ControllerRefusal) as exc:
        print(f"FIXTURE-REUSE BLOCKED: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
