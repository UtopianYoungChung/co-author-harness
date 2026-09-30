#!/usr/bin/env python3
"""Regression contract for one fixture authority across every gate surface."""

from __future__ import annotations

import importlib.util
import hashlib
import io
import json
import tempfile
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from types import SimpleNamespace
from unittest import mock
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
RUNNER_REL = "scripts/analysis/fixture_runner.py"
INFRA_REL = "scripts/analysis/fixture_infrastructure_check.py"


def _load_registry() -> set[str]:
    path = ROOT / RUNNER_REL
    spec = importlib.util.spec_from_file_location("fixture_runner_authority", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return set(module.REGISTRY)


def _require_invocation(text: str, rel: str, surface: str, *, no_write: bool) -> None:
    name = re.escape(Path(rel).name)
    pattern = rf"python(?:3)?[^\n]*{name}[^\n]*"
    matches = re.findall(pattern, text)
    assert matches, f"{surface} does not invoke {rel}"
    if no_write:
        assert any("--no-write" in match for match in matches), (
            f"{surface} must run the corpus without rewriting committed evidence"
        )


def _check_qualification_proof_contract() -> None:
    runner_path = ROOT / RUNNER_REL
    spec = importlib.util.spec_from_file_location("fixture_runner_proof_test", runner_path)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    git_rows = {
        ("symbolic-ref", "--short", "HEAD"): "main\n",
        ("status", "--porcelain=v1", "--untracked-files=all"):
            " M docs/analysis/generated/fixture_manifest.json\n",
        ("rev-parse", "HEAD"): "a" * 40 + "\n",
        ("rev-parse", "HEAD^{tree}"): "b" * 40 + "\n",
    }
    def fake_git(argv, **_kwargs):
        key = tuple(argv[4:])
        return SimpleNamespace(stdout=git_rows[key])
    with mock.patch.object(runner.subprocess, "run", side_effect=fake_git):
        assert runner._qualification_git_binding(manifest_edit=True) == {
            "head": "a" * 40, "tree": "b" * 40,
        }, "porcelain's leading space was lost before postflight"
        try:
            runner._qualification_git_binding()
        except ValueError:
            pass
        else:
            raise AssertionError("dirty manifest passed producer preflight")
    with mock.patch.object(runner, "run", side_effect=AssertionError("executed")):
        for suffix in ("--no-write", "--allow-unavailable", "--cache-mode use",
                       "--tier quick", "--suite scripts/fixture_authority_smoketest.py",
                       "--list"):
            with mock.patch.object(sys, "argv", [str(runner_path), "--qualification-proof", *suffix.split()]):
                with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
                    assert runner.main() == 2, f"invalid producer flag reached execution: {suffix}"


def _check_fixture_reuse_contract() -> None:
    checker_path = ROOT / "scripts/analysis/fixture_result_check.py"
    spec = importlib.util.spec_from_file_location("fixture_result_check_test", checker_path)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    with tempfile.TemporaryDirectory(prefix="fixture-reuse-contract-") as temp:
        root = Path(temp)
        analysis = root / "scripts" / "analysis"
        manifest_path = root / checker.MANIFEST_REL
        analysis.mkdir(parents=True)
        manifest_path.parent.mkdir(parents=True)
        (analysis / "fixture_runner.py").write_bytes(b"runner")
        (analysis / "code_census.py").write_bytes(b"census")
        lock = root / ".git" / "coauthor-fixture-runner.lock"
        lock.parent.mkdir(); lock.write_bytes(b"lock")
        run_dir = root / "controller" / "run-one"
        run_dir.mkdir(parents=True)
        stdout_path = run_dir / "stdout.bin"
        source_head, source_tree = "a" * 40, "b" * 40
        case = {"fixture_file": "scripts/x_smoketest.py", "case_id": "default",
                "expected_exit": 0, "expected_code": None,
                "outcome_contract": "EXIT-ONLY", "expected_outcome": None,
                "observed_exit": 0, "execution_source": "EXEC",
                "cached_source_run_id": None}
        declared = {key: case[key] for key in (
            "case_id", "expected_exit", "expected_code", "outcome_contract", "expected_outcome")}
        manifest = {"run_id": "proof-run", "runner_sha256": hashlib.sha256(b"runner").hexdigest(),
                    "cases": [case], "tested_inputs": {"pre_sha256": "c", "post_sha256": "c",
                    "raw_pre_sha256": "d", "raw_post_sha256": "d"}}
        def write_manifest():
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8", newline="\n")
        write_manifest()
        proof = {"manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                 "run_id": "proof-run", "head": source_head, "tree": source_tree,
                 "runner_sha256": hashlib.sha256(b"runner").hexdigest(),
                 "census_sha256": hashlib.sha256(b"census").hexdigest()}
        def sync_proof():
            write_manifest()
            proof["manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            stdout_path.write_text(checker.PREFIX + json.dumps(proof) + "\n", encoding="utf-8")
        sync_proof()
        expected_argv = [sys.executable, "-u", "-X", "utf8", "-B",
                         str(analysis / "fixture_runner.py"), "--qualification-proof"]
        receipt = {"state": "succeeded", "exit": {"returncode": 0}, "argv": expected_argv,
                   "cwd": str(root), "input_roots": [{"path": str(root), "inventory": {}}],
                   "ignored_output_paths": [str(manifest_path), str(lock)],
                   "stdout": {"path": str(stdout_path)}}
        git_rows = {("symbolic-ref", "--short", "HEAD"): "main",
                    ("status", "--porcelain=v1", "--untracked-files=all"): "",
                    ("rev-parse", source_head + "^{tree}"): source_tree,
                    ("rev-parse", "HEAD"): source_head,
                    ("rev-list", "--parents", "-n", "1", "HEAD"): "e" * 40 + " " + "f" * 40,
                    ("diff", "--name-only", source_head, "e" * 40): checker.MANIFEST_REL}
        reparse = set()
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(checker, "ROOT", root))
            stack.enter_context(mock.patch.object(checker, "ANALYSIS", analysis))
            stack.enter_context(mock.patch.object(checker, "MANIFEST", manifest_path))
            stack.enter_context(mock.patch.object(checker.controller, "status_run", return_value=receipt))
            stack.enter_context(mock.patch.object(checker.controller, "_input_root_binding",
                                                  return_value={"inventory": {}}))
            stack.enter_context(mock.patch.object(checker.controller, "_is_reparse",
                                                  side_effect=lambda path: str(path) in reparse))
            stack.enter_context(mock.patch.object(checker.runner, "_lock_path", return_value=lock))
            stack.enter_context(mock.patch.object(checker.runner, "REGISTRY",
                                                  {"scripts/x_smoketest.py": [declared]}))
            stack.enter_context(mock.patch.object(checker.runner, "discover_suite_universe",
                                                  return_value=["scripts/x_smoketest.py"]))
            stack.enter_context(mock.patch.object(checker.runner.code_census, "build_report",
                                                  return_value={}))
            stack.enter_context(mock.patch.object(checker.runner.code_census,
                                                  "_check_suite_bound_manifest_consistency",
                                                  return_value=(True, "ok")))
            inputs = {"sha256": "c", "raw_sha256": "d"}
            stack.enter_context(mock.patch.object(checker.runner, "compute_tested_inputs",
                                                  return_value=inputs))
            stack.enter_context(mock.patch.object(checker, "_git",
                                                  side_effect=lambda *args: git_rows[args]))
            with redirect_stdout(io.StringIO()):
                checker.check(run_dir)
            transcript = root / "transcript"
            transcript.mkdir()
            receipt["argv"] = [*expected_argv, "--failure-transcript-root", str(transcript)]
            with redirect_stdout(io.StringIO()):
                checker.check(run_dir)
            receipt["argv"] = expected_argv
            git_rows[("rev-parse", "HEAD")] = "e" * 40
            git_rows[("rev-list", "--parents", "-n", "1", "HEAD")] = "e" * 40 + " " + source_head
            with redirect_stdout(io.StringIO()):
                checker.check(run_dir)
            git_rows[("rev-parse", "HEAD")] = source_head
            git_rows[("rev-list", "--parents", "-n", "1", "HEAD")] = "e" * 40 + " " + "f" * 40
            def blocked(change, restore, label, path=run_dir):
                change()
                try:
                    with redirect_stdout(io.StringIO()):
                        checker.check(path)
                except ValueError:
                    pass
                else:
                    raise AssertionError(f"fixture reuse accepted {label}")
                finally:
                    restore()
            blocked(lambda: receipt.update(state="child_failed"),
                    lambda: receipt.update(state="succeeded"), "failed status")
            blocked(lambda: receipt.update(state="running"),
                    lambda: receipt.update(state="succeeded"), "nonterminal status")
            blocked(lambda: receipt.update(exit={"returncode": 1}),
                    lambda: receipt.update(exit={"returncode": 0}), "nonzero child exit")
            blocked(lambda: receipt["input_roots"][0]["inventory"].update(foreign={"kind":"file"}),
                    lambda: receipt["input_roots"][0]["inventory"].clear(), "input drift")
            blocked(lambda: (manifest.update(run_id="other"), write_manifest()),
                    lambda: (manifest.update(run_id="proof-run"), sync_proof()),
                    "manifest drift")
            blocked(lambda: (case.update(expected_code="DIFFERENT"), sync_proof()),
                    lambda: (case.update(expected_code=None), sync_proof()),
                    "case contract drift")
            blocked(lambda: inputs.update(raw_sha256="other"),
                    lambda: inputs.update(raw_sha256="d"), "raw drift")
            blocked(lambda: git_rows.update({("rev-parse", "HEAD"): "e" * 40}),
                    lambda: git_rows.update({("rev-parse", "HEAD"): source_head}),
                    "unrelated successor")
            git_rows[("rev-parse", "HEAD")] = "e" * 40
            git_rows[("rev-list", "--parents", "-n", "1", "HEAD")] = "e" * 40 + " " + source_head
            blocked(lambda: git_rows.update({("diff", "--name-only", source_head, "e" * 40): "scripts/other.py"}),
                    lambda: git_rows.update({("diff", "--name-only", source_head, "e" * 40): checker.MANIFEST_REL}),
                    "immediate successor changed another file")
            git_rows[("rev-parse", "HEAD")] = source_head
            git_rows[("rev-list", "--parents", "-n", "1", "HEAD")] = "e" * 40 + " " + "f" * 40
            blocked(lambda: receipt["ignored_output_paths"].append(str(root / "extra")),
                    lambda: receipt["ignored_output_paths"].pop(), "wider ignored paths")
            blocked(lambda: (case.update(cached_source_run_id="old-run"), sync_proof()),
                    lambda: (case.update(cached_source_run_id=None), sync_proof()),
                    "cached case")
            alias = root / "reparse-alias"
            reparse.add(str(alias))
            blocked(lambda: None, lambda: reparse.clear(), "lexical reparse alias", path=alias)


def main() -> int:
    registry = _load_registry()
    assert "scripts/fixture_authority_smoketest.py" in registry
    for required in (
        "scripts/phase_state_validator_smoketest.py",
        "scripts/artefact_frontmatter_smoketest.py",
        "scripts/paragraph_hash_map_smoketest.py",
        "scripts/subprocess_text_policy_smoketest.py",
    ):
        assert required in registry, f"fixture registry missing {required}"

    docs = {
        "AGENTS.md": (ROOT / "AGENTS.md").read_text(encoding="utf-8"),
        "README.md": (ROOT / "README.md").read_text(encoding="utf-8"),
    }
    # AGENTS.md is the canonical maintainer checklist and carries every invocation;
    # README.md keeps the corpus command and delegates the checklist to AGENTS.md.
    _require_invocation(docs["AGENTS.md"], INFRA_REL, "AGENTS.md", no_write=False)
    for name, text in docs.items():
        _require_invocation(text, RUNNER_REL, name, no_write=False)
    assert "AGENTS.md#maintainer--structural-checks" in docs["README.md"], (
        "README.md does not point maintainers to the AGENTS.md structural checklist"
    )

    surfaces = {
        "CI": (ROOT / ".github/workflows/structural-checks.yml").read_text(
            encoding="utf-8"
        ),
        "release gate": (ROOT / "scripts/release-gate.sh").read_text(
            encoding="utf-8"
        ),
    }
    for name, text in surfaces.items():
        _require_invocation(text, INFRA_REL, name, no_write=False)
        _require_invocation(text, RUNNER_REL, name, no_write=True)
        duplicates = sorted(
            rel for rel in registry
            if Path(rel).name in text and rel != "scripts/fixture_authority_smoketest.py"
        )
        assert not duplicates, f"{name} duplicates registry-owned suites: {duplicates}"

    release = surfaces["release gate"]
    for retired_inline in (
        "PS_FIXTURE_PASS=",
        "AF_PASS=(",
        "PHM_TMP1=",
        "MILESTONE_FRAMEWORK_TESTS=(",
    ):
        assert retired_inline not in release, (
            f"release gate still owns inline fixture logic: {retired_inline}"
        )

    capability_check = (ROOT / "scripts/capability-contract-check.py").read_text(
        encoding="utf-8"
    )
    assert "fixture_registry =" not in capability_check, (
        "capability evidence still uses a source-text registry surrogate"
    )
    assert "registered_fixture_paths" in capability_check, (
        "capability evidence is not bound to structured registry membership"
    )

    _check_qualification_proof_contract()
    _check_fixture_reuse_contract()
    print(f"PASS: one registry drives local, CI, and release ({len(registry)} suites)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
