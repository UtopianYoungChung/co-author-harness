#!/usr/bin/env python3
"""Synthetic coverage for the single-source phase-engagement contract."""

from __future__ import annotations

import copy
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = ROOT / "scripts" / "phase_engagement_check.py"
API = "check_phase_engagement"

CONTRADICTION = "PHASE-CONTRACT-CONTRADICTION"
STALE_AUTHORITY = "PHASE-CONTRACT-STALE-AUTHORITY"
RETIRED_STATEMENT = "The Evaluator is dormant at Ph1 and does not engage.\n"
RETIREMENT_LEDGER_PATH = (
    "references/retired/PHASE_ENGAGEMENT_RETIREMENT_LEDGER.md"
)
CURRENT_STATEMENT = (
    "At Ph1, the Evaluator is required for a bounded independent review.\n"
)


def _policy() -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "policy_id": "synthetic-phase-engagement-v1",
        "effective_at": "2026-07-26T00:00:00Z",
        "phases": {
            "Ph1": {
                "planner": "required",
                "generator": "required",
                "evaluator": "bounded_independent_required",
                "reflector": "lightweight_required",
            },
            "Ph2": {
                "planner": "required",
                "generator": "required",
                "evaluator": "full_revision_maturity_required",
                "reflector": "lightweight_required",
            },
            "Ph3": {
                "planner": "required",
                "generator": "required",
                "evaluator": "full_iterative_required",
                "reflector": "lightweight_required",
            },
            "Ph4": {
                "planner": "required",
                "generator": "fix_only_required",
                "evaluator": "strict_final_required",
                "reflector": "full_required",
                "external_verifiers": "required",
            },
        },
        "retirement_ledger": [RETIREMENT_LEDGER_PATH],
    }


def _with_ledger(documents: list[dict[str, str]]) -> list[dict[str, str]]:
    if any(document.get("path") == RETIREMENT_LEDGER_PATH for document in documents):
        return copy.deepcopy(documents)
    return [
        {"path": RETIREMENT_LEDGER_PATH, "text": RETIRED_STATEMENT},
        *copy.deepcopy(documents),
    ]


def _load_module() -> Any | None:
    if not PRODUCTION.is_file():
        return None
    spec = importlib.util.spec_from_file_location("phase_engagement_check", PRODUCTION)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _expect_code(expected: str, function: Any, *args: Any) -> None:
    try:
        function(*copy.deepcopy(args))
    except Exception as exc:
        observed = getattr(exc, "code", type(exc).__name__)
        if observed != expected:
            raise AssertionError(
                f"expected {expected}, observed {observed}: {exc}"
            ) from exc
        return
    raise AssertionError(f"expected refusal {expected}")


def _contradiction_pairs() -> list[tuple[str, list[dict[str, str]], list[dict[str, str]]]]:
    clean_live = [{"path": "references/live-contract.md", "text": CURRENT_STATEMENT}]
    return [
        (
            "exact_retired_statement_at_live_path",
            [{"path": "references/live-contract.md", "text": RETIRED_STATEMENT}],
            [{"path": RETIREMENT_LEDGER_PATH, "text": RETIRED_STATEMENT}],
        ),
        (
            "dormant_at_phase_one",
            [{"path": "agents/evaluator.md", "text": "The Evaluator remains dormant during Phase One.\n"}],
            clean_live,
        ),
        (
            "deliberate_bare_dormant_at_ph1",
            [{"path": "agents/evaluator-short.md", "text": "Evaluator dormant at Ph1.\n"}],
            clean_live,
        ),
        (
            "not_engaged_at_ph1",
            [{"path": "references/protocol.md", "text": "At Ph1, the Evaluator is not-engaged.\n"}],
            clean_live,
        ),
        (
            "line_wrapped_not_engaged_at_ph1",
            [{"path": "references/wrapped.md", "text": "At Ph1, the Evaluator\nnot engaged.\n"}],
            clean_live,
        ),
        (
            "no_evaluator_at_ph1",
            [{"path": "skills/example.md", "text": "There is no independent Evaluator in phase 1.\n"}],
            clean_live,
        ),
        (
            "evaluator_joins_at_ph2",
            [{"path": "agents/planner.md", "text": "The Evaluator joins at Ph2.\n"}],
            clean_live,
        ),
        (
            "evaluator_engagement_begins_at_ph2",
            [{"path": "references/roles.md", "text": "Evaluator engagement begins in Phase Two.\n"}],
            clean_live,
        ),
        (
            "evaluator_waits_until_ph2",
            [{"path": "references/flow.md", "text": "The Evaluator is not engaged until Ph2.\n"}],
            clean_live,
        ),
        (
            "inactive_ph1_with_punctuation",
            [{"path": "README.md", "text": "Ph1 -- the Evaluator is inactive.\n"}],
            clean_live,
        ),
        (
            "evaluator_optional_at_ph1",
            [{"path": "references/optional.md", "text": "The Evaluator is optional at Ph1.\n"}],
            [{"path": "references/optional.md", "text": "The Evaluator is not optional at Ph1.\n"}],
        ),
        (
            "evaluator_participation_may_be_omitted",
            [{"path": "agents/omitted.md", "text": "At Ph1, Evaluator participation may be omitted.\n"}],
            [{"path": "agents/omitted.md", "text": "At Ph1, Evaluator participation may not be omitted.\n"}],
        ),
        (
            "evaluator_can_be_skipped",
            [{"path": "skills/skipped.md", "text": "The Evaluator can be skipped at Ph1.\n"}],
            [{"path": "skills/skipped.md", "text": "The Evaluator cannot be skipped at Ph1.\n"}],
        ),
        (
            "evaluator_waived",
            [{"path": "references/waived.md", "text": "At Ph1, the Evaluator is waived.\n"}],
            [{"path": "references/waived.md", "text": "At Ph1, the Evaluator is not waived.\n"}],
        ),
        (
            "evaluator_not_required",
            [{"path": "references/not-required.md", "text": "The Evaluator is not required at Ph1.\n"}],
            clean_live,
        ),
    ]


def _policy_mutations() -> list[tuple[str, dict[str, Any]]]:
    cases: list[tuple[str, dict[str, Any]]] = []

    missing_phase = _policy()
    del missing_phase["phases"]["Ph1"]
    cases.append(("missing_phase", missing_phase))

    extra_phase = _policy()
    extra_phase["phases"]["Ph5"] = copy.deepcopy(extra_phase["phases"]["Ph4"])
    cases.append(("extra_phase", extra_phase))

    missing_role = _policy()
    del missing_role["phases"]["Ph1"]["evaluator"]
    cases.append(("missing_role", missing_role))

    extra_role = _policy()
    extra_role["phases"]["Ph1"]["external_verifiers"] = "optional"
    cases.append(("extra_role", extra_role))

    stale_ph1 = _policy()
    stale_ph1["phases"]["Ph1"]["evaluator"] = "dormant"
    cases.append(("stale_ph1_value", stale_ph1))

    stale_ph4 = _policy()
    stale_ph4["phases"]["Ph4"]["generator"] = "required"
    cases.append(("stale_ph4_value", stale_ph4))

    missing_ledger = _policy()
    del missing_ledger["retirement_ledger"]
    cases.append(("missing_retirement_ledger", missing_ledger))

    extra_field = _policy()
    extra_field["authority_hint"] = "unfrozen"
    cases.append(("extra_policy_field", extra_field))

    duplicate_ledger = _policy()
    duplicate_ledger["retirement_ledger"].append(RETIREMENT_LEDGER_PATH)
    cases.append(("duplicate_ledger_path", duplicate_ledger))

    expanded_ledger = _policy()
    expanded_ledger["retirement_ledger"].append("agents/evaluator.md")
    cases.append(("safe_ledger_expansion", expanded_ledger))

    substituted_ledger = _policy()
    substituted_ledger["retirement_ledger"] = ["references/retired/other.md"]
    cases.append(("safe_ledger_substitution", substituted_ledger))

    empty_ledger = _policy()
    empty_ledger["retirement_ledger"] = []
    cases.append(("empty_ledger", empty_ledger))

    traversal_ledger = _policy()
    traversal_ledger["retirement_ledger"] = ["../retired/history.md"]
    cases.append(("traversal_ledger_path", traversal_ledger))

    absolute_ledger = _policy()
    absolute_ledger["retirement_ledger"] = ["/retired/history.md"]
    cases.append(("absolute_ledger_path", absolute_ledger))

    backslash_ledger = _policy()
    backslash_ledger["retirement_ledger"] = ["retired\\history.md"]
    cases.append(("backslash_ledger_path", backslash_ledger))

    stale_schema = _policy()
    stale_schema["schema_version"] = "0.9.0"
    cases.append(("stale_schema_version", stale_schema))

    bad_time = _policy()
    bad_time["effective_at"] = "yesterday"
    cases.append(("malformed_effective_at", bad_time))

    bad_id = _policy()
    bad_id["policy_id"] = "not a stable id"
    cases.append(("malformed_policy_id", bad_id))
    return cases


def _write_synthetic_package(root: Path) -> dict[str, Path]:
    policy = _policy()
    files = {
        "README": root / "README.md",
        "AGENTS": root / "AGENTS.md",
        "CLAUDE": root / "CLAUDE.md",
        "agents": root / "agents" / "evaluator.md",
        "references": root / "references" / "current-contract.md",
        "skills": root / "skills" / "phase-skill" / "SKILL.md",
        "docs": root / "docs" / "agent-instructions" / "phase-contract.md",
        "ledger": root / RETIREMENT_LEDGER_PATH,
        "policy": root / "references" / "policies" / "phase_engagement.v1.json",
    }
    for path in files.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    for name, path in files.items():
        if name not in {"ledger", "policy"}:
            path.write_text(CURRENT_STATEMENT, encoding="utf-8", newline="")
    files["ledger"].write_text(RETIRED_STATEMENT, encoding="utf-8", newline="")
    files["policy"].write_text(
        json.dumps(policy, indent=2) + "\n", encoding="utf-8", newline=""
    )
    ignored = root / "skills" / "phase-skill" / "fixture.bin"
    ignored.write_bytes(RETIRED_STATEMENT.encode("utf-8"))
    generated = root / "skills" / "__pycache__" / "generated.txt"
    generated.parent.mkdir(parents=True, exist_ok=True)
    generated.write_text(RETIRED_STATEMENT, encoding="utf-8", newline="")
    return files


def _run_cli(module: Any, root: Path) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = module.main(["--root", str(root)])
    return code, stdout.getvalue(), stderr.getvalue()


def _run_cli_cases(module: Any) -> list[str]:
    completed: list[str] = []
    with TemporaryDirectory(prefix="coauthor-v040-phase-") as temporary:
        root = Path(temporary)
        files = _write_synthetic_package(root)
        documents = module._discover_documents(root)
        paths = [document["path"] for document in documents]
        assert paths == sorted(paths), "CLI discovery is not deterministic"
        assert "references/retired/PHASE_ENGAGEMENT_RETIREMENT_LEDGER.md" in paths
        assert not any(path.endswith("fixture.bin") for path in paths)
        assert not any("__pycache__" in path for path in paths)
        code, stdout, stderr = _run_cli(module, root)
        assert code == 0 and stderr == ""
        assert stdout == (
            "phase_engagement_check: PASS "
            f"documents={len(documents)} retirement_exceptions=1 blockers=0\n"
        )
        completed.append("deterministic_discovery_includes_exact_ledger")

        for category in (
            "agents",
            "references",
            "skills",
            "docs",
            "README",
            "CLAUDE",
        ):
            path = files[category]
            original = path.read_bytes()
            try:
                path.write_text(
                    "The Evaluator joins at Ph2 and is dormant at Ph1.\n",
                    encoding="utf-8",
                    newline="",
                )
                code, stdout, stderr = _run_cli(module, root)
                assert code == 1 and stdout == ""
                assert f"code={CONTRADICTION}" in stderr
                assert path.relative_to(root).as_posix() in stderr
            finally:
                path.write_bytes(original)
            completed.append(f"cli_mutation_{category.lower()}_refuses")

        policy_original = files["policy"].read_bytes()
        stale_policy = _policy()
        stale_policy["phases"]["Ph1"]["evaluator"] = "dormant"
        try:
            files["policy"].write_text(
                json.dumps(stale_policy), encoding="utf-8", newline=""
            )
            code, stdout, stderr = _run_cli(module, root)
            assert code == 1 and stdout == ""
            assert f"code={STALE_AUTHORITY}" in stderr
            assert "detail=" in stderr
        finally:
            files["policy"].write_bytes(policy_original)
        completed.append("cli_stale_policy_prints_typed_refusal")

        requiredness_mutations = {
            "optional": "The Evaluator is optional at Ph1.\n",
            "omitted": "At Ph1, Evaluator participation may be omitted.\n",
            "skipped": "The Evaluator can be skipped at Ph1.\n",
            "waived": "At Ph1, the Evaluator is waived.\n",
            "not_required": "The Evaluator is not required at Ph1.\n",
        }
        contract_original = files["references"].read_bytes()
        for name, text in requiredness_mutations.items():
            try:
                files["references"].write_text(
                    text, encoding="utf-8", newline=""
                )
                code, stdout, stderr = _run_cli(module, root)
                assert code == 1 and stdout == ""
                assert f"code={CONTRADICTION}" in stderr
            finally:
                files["references"].write_bytes(contract_original)
            completed.append(f"cli_requiredness_{name}_refuses")

        try:
            files["references"].write_text(
                "At Ph1, the Evaluator is not optional, cannot be skipped, "
                "may not be omitted, and is not waived.\n",
                encoding="utf-8",
                newline="",
            )
            code, stdout, stderr = _run_cli(module, root)
            assert code == 0 and stderr == "" and "blockers=0" in stdout
        finally:
            files["references"].write_bytes(contract_original)
        completed.append("cli_requiredness_negations_qualify")

        ledger_policy_mutations = {
            "expansion": [RETIREMENT_LEDGER_PATH, "agents/evaluator.md"],
            "substitution": ["references/retired/other.md"],
            "omission": [],
        }
        for name, ledger in ledger_policy_mutations.items():
            mutated = _policy()
            mutated["retirement_ledger"] = ledger
            try:
                files["policy"].write_text(
                    json.dumps(mutated), encoding="utf-8", newline=""
                )
                code, stdout, stderr = _run_cli(module, root)
                assert code == 1 and stdout == ""
                assert f"code={STALE_AUTHORITY}" in stderr
            finally:
                files["policy"].write_bytes(policy_original)
            completed.append(f"cli_ledger_{name}_refuses")

        ledger_original = files["ledger"].read_bytes()
        try:
            files["ledger"].write_bytes(
                RETIRED_STATEMENT.replace("\n", "\r\n").encode("utf-8")
            )
            code, stdout, stderr = _run_cli(module, root)
            assert code == 1 and stdout == ""
            assert f"code={STALE_AUTHORITY}" in stderr
        finally:
            files["ledger"].write_bytes(ledger_original)
        completed.append("cli_ledger_byte_drift_refuses")
    return completed


def main() -> int:
    module = _load_module()
    if module is None or not callable(getattr(module, API, None)):
        print("[RED] phase_engagement_check: INTERFACE_BLOCKED")
        print("phase_engagement_smoketest: FAIL")
        return 1

    failures: list[str] = []
    cli_cases: list[str] = []
    contradiction_pairs = _contradiction_pairs()
    for name, red, clean in contradiction_pairs:
        try:
            _expect_code(
                CONTRADICTION,
                module.check_phase_engagement,
                _policy(),
                _with_ledger(red),
            )
            receipt = module.check_phase_engagement(
                copy.deepcopy(_policy()), _with_ledger(clean)
            )
            assert receipt["status"] == "verified"
            assert receipt["findings"] == []
        except Exception as exc:
            failures.append(f"{name}: {type(exc).__name__}: {exc}")

    clean_documents = [
        {"path": RETIREMENT_LEDGER_PATH, "text": RETIRED_STATEMENT},
        {
            "path": "references/delegation.md",
            "text": "Role engagement delegates to references/policies/phase_engagement.v1.json.\n",
        },
        {"path": "references/current.md", "text": CURRENT_STATEMENT},
        {
            "path": "references/negation.md",
            "text": "The Evaluator is not dormant at Ph1; bounded independent review is required.\n",
        },
        {
            "path": "references/ph2.md",
            "text": "At Ph2, full revision-maturity evaluation begins after bounded Ph1 review.\n",
        },
        {
            "path": "references/requiredness-negations.md",
            "text": (
                "At Ph1, the Evaluator is not optional. "
                "Evaluator participation may not be omitted. "
                "The Evaluator cannot be skipped and is not waived.\n"
            ),
        },
    ]
    try:
        receipt = module.check_phase_engagement(_policy(), clean_documents)
        assert receipt["documents_checked"] == len(clean_documents)
        assert receipt["retirement_exceptions"] == [RETIREMENT_LEDGER_PATH]
        assert receipt["phase_matrix"] == _policy()["phases"]
        assert receipt["findings"] == []
    except Exception as exc:
        failures.append(f"clean_contracts: {type(exc).__name__}: {exc}")

    policy_cases = _policy_mutations()
    for name, policy in policy_cases:
        try:
            _expect_code(
                STALE_AUTHORITY,
                module.check_phase_engagement,
                policy,
                clean_documents,
            )
        except Exception as exc:
            failures.append(f"{name}: {type(exc).__name__}: {exc}")

    ledger_abuse = [
        (
            "ledger_prefix_is_not_authority",
            CONTRADICTION,
            _with_ledger(
                [
                    {
                        "path": RETIREMENT_LEDGER_PATH + "/appendix.md",
                        "text": RETIRED_STATEMENT,
                    }
                ]
            ),
        ),
        (
            "ledger_path_is_case_sensitive",
            CONTRADICTION,
            _with_ledger(
                [
                    {
                        "path": "references/retired/phase_engagement_retirement_ledger.md",
                        "text": RETIRED_STATEMENT,
                    }
                ]
            ),
        ),
        (
            "retired_bytes_must_be_exact",
            STALE_AUTHORITY,
            [
                {
                    "path": RETIREMENT_LEDGER_PATH,
                    "text": RETIRED_STATEMENT.replace("\n", "\r\n"),
                }
            ],
        ),
        (
            "ledger_does_not_exempt_equivalent_mutation",
            STALE_AUTHORITY,
            [
                {
                    "path": RETIREMENT_LEDGER_PATH,
                    "text": "At Ph1, the Evaluator is dormant.\n",
                }
            ],
        ),
        (
            "required_ledger_document_missing",
            STALE_AUTHORITY,
            [{"path": "references/current.md", "text": CURRENT_STATEMENT}],
        ),
        (
            "unsafe_document_path",
            STALE_AUTHORITY,
            _with_ledger(
                [{"path": "../retired/history.md", "text": RETIRED_STATEMENT}]
            ),
        ),
        (
            "duplicate_document_path",
            STALE_AUTHORITY,
            _with_ledger(
                [
                    {"path": "references/current.md", "text": CURRENT_STATEMENT},
                    {"path": "references/current.md", "text": CURRENT_STATEMENT},
                ]
            ),
        ),
        (
            "extra_document_field",
            STALE_AUTHORITY,
            _with_ledger(
                [
                    {
                        "path": "references/current.md",
                        "text": CURRENT_STATEMENT,
                        "role": "evaluator",
                    }
                ]
            ),
        ),
    ]
    for name, expected, documents in ledger_abuse:
        try:
            _expect_code(
                expected, module.check_phase_engagement, _policy(), documents
            )
        except Exception as exc:
            failures.append(f"{name}: {type(exc).__name__}: {exc}")

    try:
        _expect_code(
            STALE_AUTHORITY,
            module.check_phase_engagement,
            _policy(),
            "not-a-document-array",
        )
    except Exception as exc:
        failures.append(f"documents_not_array: {type(exc).__name__}: {exc}")

    try:
        cli_cases = _run_cli_cases(module)
        if len(cli_cases) != 18:
            failures.append(
                f"CLI coverage expected 18 cases, observed {len(cli_cases)}"
            )
    except Exception as exc:
        failures.append(f"cli_cases: {type(exc).__name__}: {exc}")

    if failures:
        for failure in failures:
            print(f"[RED] {failure}")
        print(f"phase_engagement_smoketest: FAIL ({len(failures)} failures)")
        return 1
    print(
        "phase_engagement_smoketest: PASS "
        f"({len(contradiction_pairs)} red/clean contradiction pairs + "
        f"1 clean contract set + {len(policy_cases)} stale-authority cases + "
        f"{len(ledger_abuse) + 1} ledger/input abuse cases + "
        f"{len(cli_cases)} CLI discovery/mutation cases)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
