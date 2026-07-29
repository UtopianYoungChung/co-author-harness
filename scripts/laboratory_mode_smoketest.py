#!/usr/bin/env python3
"""Synthetic red boundary for the transient ``lab_iteration`` run scope.

This suite deliberately exercises only temporary governed workspaces.  It does
not invoke the fixture registry and it never points a writer at a research
project.  Until the v0.41 laboratory boundary exists, the lab-specific cases
must fail while the pre-existing ad-hoc/full-lifecycle compatibility cases stay
green.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Callable

from assignment_fixture_support import write_valid_contract
import destination_capability as destination


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "scripts" / "full_run_contract_check.py"
DESTINATION = ROOT / "scripts" / "destination_capability.py"
PYTHON_ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"}


class Matrix:
    def __init__(self) -> None:
        self.passed: list[str] = []
        self.failed: list[tuple[str, str]] = []

    def case(self, name: str, operation: Callable[[], None]) -> None:
        try:
            operation()
        except Exception as exc:  # every row is reported in one red receipt
            detail = f"{type(exc).__name__}: {exc}".replace("\n", " | ")
            self.failed.append((name, detail))
            print(f"FAIL {name}: {detail}")
        else:
            self.passed.append(name)
            print(f"PASS {name}")

    def finish(self) -> int:
        print(
            "LABORATORY_MODE_MATRIX "
            f"passed={len(self.passed)} failed={len(self.failed)} "
            f"total={len(self.passed) + len(self.failed)}"
        )
        return 1 if self.failed else 0


def _run(*args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CONTRACT), *(str(arg) for arg in args)],
        cwd=ROOT,
        env=PYTHON_ENV,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )


def _payload(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"command did not emit JSON (exit {result.returncode}): "
            f"{(result.stdout + result.stderr).strip()[:400]}"
        ) from exc
    if not isinstance(value, dict):
        raise AssertionError(f"command emitted {type(value).__name__}, not an object")
    return value


def _codes(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        code = value.get("code")
        if isinstance(code, str):
            found.add(code)
        for child in value.values():
            found.update(_codes(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_codes(child))
    return found


def _expect(result: subprocess.CompletedProcess[str], exit_code: int, code: str) -> dict[str, Any]:
    payload = _payload(result)
    if result.returncode != exit_code:
        raise AssertionError(
            f"expected exit {exit_code}, got {result.returncode}: "
            f"{json.dumps(payload, sort_keys=True)[:500]}"
        )
    codes = _codes(payload)
    if code not in codes:
        raise AssertionError(f"expected {code}, got codes={sorted(codes)} payload={payload}")
    return payload


def _expect_child_omission(result: subprocess.CompletedProcess[str]) -> None:
    """Require the undeclared diagnostic to be caused by the child omission."""
    payload = _expect(result, 4, "FRC-SCOPE-UNDECLARED")
    messages = [
        finding.get("message", "")
        for finding in payload.get("findings", [])
        if isinstance(finding, dict) and finding.get("code") == "FRC-SCOPE-UNDECLARED"
    ]
    if not any(
        "child" in message.lower()
        and ("no `run_scope:`" in message.lower() or "no run_scope" in message.lower() or "omission" in message.lower())
        and "parent scope" not in message.lower()
        for message in messages
    ):
        raise AssertionError(
            "FRC-SCOPE-UNDECLARED did not identify the omitted child declaration: "
            f"{messages}"
        )


def _expect_destination_refusal(path: Path, code: str) -> None:
    try:
        destination.assert_writable(path, purpose="synthetic lab output")
    except destination.DestinationRefused as exc:
        if exc.code != code:
            raise AssertionError(f"expected {code}, got {exc.code}") from exc
        return
    raise AssertionError(f"destination unexpectedly writable: {path}")


def _assert_proposal_only_payload(payload: dict[str, Any]) -> None:
    required = {
        "result": "PROPOSAL_ONLY",
        "lifecycle_authority": False,
        "f9_authority": False,
        "terminal_authority": False,
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise AssertionError(
                f"{key}={payload.get(key)!r}, expected {expected!r}"
            )


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _tree_snapshot(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False}
    rows: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            rows[relative] = {"kind": "symlink", "target": os.readlink(path)}
        elif path.is_dir():
            rows[relative] = {"kind": "directory"}
        elif path.is_file():
            payload = path.read_bytes()
            rows[relative] = {
                "kind": "file",
                "bytes": len(payload),
                "sha256": _sha(payload),
            }
        else:
            rows[relative] = {"kind": "other"}
    return {"exists": True, "rows": rows}


def _path_snapshot(path: Path) -> dict[str, Any]:
    """Exact file/tree inventory used by the laboratory non-effect guard."""
    if not path.exists() and not path.is_symlink():
        return {"exists": False}
    if path.is_symlink():
        return {"exists": True, "kind": "symlink", "target": os.readlink(path)}
    if path.is_file():
        payload = path.read_bytes()
        return {
            "exists": True,
            "kind": "file",
            "bytes": len(payload),
            "sha256": _sha(payload),
        }
    if path.is_dir():
        return {"exists": True, "kind": "directory", "tree": _tree_snapshot(path)}
    return {"exists": True, "kind": "other"}


def _event_array_snapshot(phase_state: Path) -> dict[str, Any]:
    """Capture the exact decoded event array in addition to ledger raw bytes."""
    if not phase_state.is_file():
        return {"exists": False}
    try:
        document = json.loads(phase_state.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {"exists": True, "parse_error": f"{type(exc).__name__}: {exc}"}
    framework = document.get("milestone_framework") if isinstance(document, dict) else None
    events = framework.get("events") if isinstance(framework, dict) else None
    return {"exists": True, "events": events}


def _lab_surface_snapshot(project: Path) -> dict[str, Any]:
    """Snapshot every charter-named surface for one synthetic lab project."""
    reviews = project / "reviews"
    phase_state = reviews / "phase_state.json"
    return {
        "phase_state_bytes": _path_snapshot(phase_state),
        "event_arrays": _event_array_snapshot(phase_state),
        "f9_tree": _path_snapshot(reviews / ".harness" / "handoffs"),
        "assignment_state": {
            "contract": _path_snapshot(reviews / "assignment_contract.json"),
            "transaction_tree": _path_snapshot(reviews / ".harness" / "assignment"),
        },
        "promotion_surfaces": {
            "receipt": _path_snapshot(reviews / "promotion_receipt.json"),
            "harness_tree": _path_snapshot(reviews / ".harness" / "promotion"),
            "project_tree": _path_snapshot(project / "promotion"),
        },
        "protected_destinations": {
            "sentinel": _path_snapshot(reviews / "protected_destination.json"),
            "project_tree": _path_snapshot(project / "protected"),
        },
        "final_deliverable_paths": {
            "manuscript_tree": _path_snapshot(project / "manuscript"),
            "export_tree": _path_snapshot(project / "exports"),
            "milestone_m5": _path_snapshot(project / "milestones" / "M5_final_paper.md"),
        },
    }


def _guard_lab_nonmutation(project: Path, operation: Callable[[], None]) -> None:
    """Run one lab case and prove all charter-named surfaces are unchanged."""
    before = _lab_surface_snapshot(project)
    try:
        operation()
    except Exception:
        after = _lab_surface_snapshot(project)
        if after != before:
            raise AssertionError(
                "lab case changed a lifecycle/event/F9/assignment/promotion/"
                "protected/final-deliverable surface while refusing"
            )
        raise
    after = _lab_surface_snapshot(project)
    if after != before:
        raise AssertionError(
            "lab case changed a lifecycle/event/F9/assignment/promotion/"
            "protected/final-deliverable surface"
        )


def _synthetic_workspace(base: Path) -> tuple[Path, Path, Path]:
    workspace = base / "governed-workspace"
    routing = workspace / "governance" / "output-routing" / "output_routing.yaml"
    routing.parent.mkdir(parents=True)
    routing.write_text("schema_version: synthetic-test-only\n", encoding="utf-8")

    work_id = "synthetic-lab"
    project = workspace / "research" / "60_Workbench" / work_id
    reviews = project / "reviews"
    _write_json(
        reviews / "phase_state.json",
        {
            "schema_version": "0.7.4",
            "manuscript_id": work_id,
            "terminal_phase_reached": False,
            "sections": {},
            "milestone_framework": {
                "contract_version": "1.0.0",
                "mode": "native",
                "primary_lineage": "main",
                "milestones": {},
                "events": [{"sequence": 1, "event_type": "synthetic_baseline"}],
            },
        },
    )
    write_valid_contract(project)
    _write_json(reviews / ".harness" / "handoffs" / "existing-f9.json", {"artifact_family": "F9"})
    _write_json(reviews / ".harness" / "assignment" / "ready" / "existing.json", {"state": "ready"})
    _write_json(reviews / "promotion_receipt.json", {"status": "not_promoted"})
    _write_json(reviews / "protected_destination.json", {"authority": "research_governance"})
    final = project / "manuscript" / "final.md"
    final.parent.mkdir(parents=True)
    final.write_text("Synthetic final deliverable; immutable in lab authorization.\n", encoding="utf-8")

    output = workspace / "outputs" / "co-author-harness" / "staging" / work_id / "run-001"
    output.mkdir(parents=True)
    return workspace, project, output


def _brief(base: Path, name: str, content: str) -> Path:
    path = base / f"{name}.md"
    path.write_text(content, encoding="utf-8")
    return path


def main() -> int:
    matrix = Matrix()
    with tempfile.TemporaryDirectory(prefix="v041-laboratory-mode-") as raw:
        sandbox = Path(raw)
        workspace, project, output = _synthetic_workspace(sandbox)

        def lab_case(name: str, fixture_project: Path, operation: Callable[[], None]) -> None:
            matrix.case(
                name,
                lambda: _guard_lab_nonmutation(fixture_project, operation),
            )

        def exact_scope_vocabulary() -> None:
            sys.path.insert(0, str(ROOT / "scripts"))
            try:
                import full_run_contract_check as contract  # type: ignore
                if tuple(contract.SCOPES) != ("adhoc_review", "lab_iteration", "full_lifecycle"):
                    raise AssertionError(f"SCOPES={contract.SCOPES!r}")
            finally:
                sys.path.pop(0)

        lab_case("scope vocabulary is exactly adhoc_review/lab_iteration/full_lifecycle", project, exact_scope_vocabulary)

        same = _brief(sandbox, "same", "run_scope: lab_iteration\nproposal_only: true\n")
        down = _brief(sandbox, "down", "run_scope: adhoc_review\n")
        up = _brief(sandbox, "up", "run_scope: full_lifecycle\n")
        absent = _brief(sandbox, "absent", "proposal_only: true\n")
        terminal = _brief(sandbox, "terminal", "run_scope: lab_iteration\nterminal_claim: shipped\n")
        lifecycle = _brief(sandbox, "lifecycle", "run_scope: lab_iteration\nlifecycle_mutation: true\n")
        f9 = _brief(sandbox, "f9", "run_scope: lab_iteration\nf9_use: true\n")

        lab_case(
            "lab child inherits exact lab scope",
            project,
            lambda: _expect(_run("scope", "--parent-scope", "lab_iteration", "--child-brief", same), 0, "FRC-LAB-PROPOSAL-ONLY"),
        )
        lab_case(
            "lab to adhoc mismatch is a downgrade refusal",
            project,
            lambda: _expect(_run("scope", "--parent-scope", "lab_iteration", "--child-brief", down), 4, "FRC-SCOPE-DOWNGRADE"),
        )
        lab_case(
            "lab to full mismatch is an escalation refusal",
            project,
            lambda: _expect(_run("scope", "--parent-scope", "lab_iteration", "--child-brief", up), 4, "FRC-SCOPE-ESCALATION"),
        )
        lab_case(
            "lab child omission fails closed",
            project,
            lambda: _expect_child_omission(
                _run("scope", "--parent-scope", "lab_iteration", "--child-brief", absent)
            ),
        )
        lab_case(
            "lab brief cannot request lifecycle mutation",
            project,
            lambda: _expect(_run("scope", "--parent-scope", "lab_iteration", "--child-brief", lifecycle), 4, "FRC-LAB-LIFECYCLE-FORBIDDEN"),
        )
        lab_case(
            "lab brief cannot request F9",
            project,
            lambda: _expect(_run("scope", "--parent-scope", "lab_iteration", "--child-brief", f9), 4, "FRC-LAB-F9-FORBIDDEN"),
        )
        lab_case(
            "lab brief cannot make terminal claim",
            project,
            lambda: _expect(_run("scope", "--parent-scope", "lab_iteration", "--child-brief", terminal), 4, "FRC-LAB-TERMINAL-FORBIDDEN"),
        )

        def authorize_proposal_only_without_effects() -> None:
            before = _tree_snapshot(workspace)
            result = _run(
                "authorize", "--project-root", project,
                "--run-scope", "lab_iteration", "--output-root", output,
            )
            payload = _expect(result, 0, "FRC-LAB-PROPOSAL-ONLY")
            _assert_proposal_only_payload(payload)
            after = _tree_snapshot(workspace)
            if after != before:
                raise AssertionError("lab authorization changed project/output/governance bytes")

        lab_case("lab authorization is proposal-only with exact zero non-effects", project, authorize_proposal_only_without_effects)

        missing_contract = sandbox / "missing-contract"
        _, project_without_contract, missing_output = _synthetic_workspace(missing_contract)
        (project_without_contract / "reviews" / "assignment_contract.json").unlink()
        lab_case(
            "lab requires a resolved assignment contract",
            project_without_contract,
            lambda: _expect(
                _run("authorize", "--project-root", project_without_contract, "--run-scope", "lab_iteration", "--output-root", missing_output),
                4,
                "FRC-LAB-CONTRACT-REQUIRED",
            ),
        )
        lab_case(
            "lab requires an existing governed project",
            sandbox / "absent-project",
            lambda: _expect(
                _run("authorize", "--project-root", sandbox / "absent-project", "--run-scope", "lab_iteration", "--output-root", output),
                4,
                "FRC-LAB-PROJECT-REQUIRED",
            ),
        )
        lab_case(
            "lab requires an output root",
            project,
            lambda: _expect(_run("authorize", "--project-root", project, "--run-scope", "lab_iteration"), 4, "FRC-LAB-DESTINATION-REQUIRED"),
        )
        mismatch = workspace / "outputs" / "co-author-harness" / "staging" / "different-work" / "run-001"
        lab_case(
            "lab staging work-id must match the project",
            project,
            lambda: _expect(
                _run("authorize", "--project-root", project, "--run-scope", "lab_iteration", "--output-root", mismatch),
                4,
                "FRC-LAB-DESTINATION-MISMATCH",
            ),
        )
        lab_case(
            "package-local output lookalike remains independently misrouted",
            project,
            lambda: _expect(
                _run(
                    "authorize", "--project-root", project, "--run-scope", "lab_iteration",
                    "--output-root", ROOT / "outputs" / "co-author-harness" / "staging" / "synthetic-lab" / "run-001",
                ),
                4,
                "DEST-MISROUTED",
            ),
        )
        ungoverned = sandbox / "ungoverned" / "outputs" / "co-author-harness" / "staging" / "synthetic-lab" / "run-001"
        lab_case(
            "ungoverned lab output remains independently refused",
            project,
            lambda: _expect(
                _run("authorize", "--project-root", project, "--run-scope", "lab_iteration", "--output-root", ungoverned),
                4,
                "DEST-UNGOVERNED",
            ),
        )

        lab_case(
            "protected governed destination remains independently refused",
            project,
            lambda: _expect_destination_refusal(
                project / "reviews" / "phase_state.json", "DEST-PROTECTED"
            ),
        )
        private_shipment = (
            project / "reviews" / ".harness" / "shipments" / "synthetic-shipment-001"
        )

        def exact_private_shipment_is_writable() -> None:
            if destination.classify(private_shipment) != "shipment":
                raise AssertionError(
                    f"exact private shipment classified as {destination.classify(private_shipment)!r}"
                )
            if destination.assert_writable(
                private_shipment, purpose="synthetic lab output"
            ) != "shipment":
                raise AssertionError("exact private shipment did not yield shipment capability")

        lab_case(
            "exact private shipment lane is a positive lab destination capability",
            project,
            exact_private_shipment_is_writable,
        )

        def authorize_exact_private_shipment() -> None:
            payload = _expect(
                _run(
                    "authorize",
                    "--project-root", project,
                    "--run-scope", "lab_iteration",
                    "--output-root", private_shipment,
                ),
                0,
                "FRC-LAB-PROPOSAL-ONLY",
            )
            _assert_proposal_only_payload(payload)

        lab_case(
            "lab authorizer grants proposal-only result for exact private shipment lane",
            project,
            authorize_exact_private_shipment,
        )
        lab_case(
            "lab authorizer independently refuses exact governed protected output",
            project,
            lambda: _expect(
                _run(
                    "authorize",
                    "--project-root", project,
                    "--run-scope", "lab_iteration",
                    "--output-root", project / "reviews" / "phase_state.json",
                ),
                4,
                "DEST-PROTECTED",
            ),
        )

        adhoc = _brief(sandbox, "adhoc", "run_scope: adhoc_review\n")
        matrix.case(
            "compatibility control: pre-existing ad hoc review remains read-only",
            lambda: _expect(_run("authorize", "--project-root", project, "--run-scope", "adhoc_review"), 4, "FRC-PROSE-FORBIDDEN"),
        )
        matrix.case(
            "compatibility control: pre-existing ad hoc scope inheritance remains legal",
            lambda: (
                (_result := _run("scope", "--parent-scope", "adhoc_review", "--child-brief", adhoc)),
                (_payload_value := _payload(_result)),
                None if _result.returncode == 0 and _payload_value.get("status") == "OK" else (_ for _ in ()).throw(AssertionError(f"unexpected ad hoc result: {_result.returncode} {_payload_value}")),
            ) and None,
        )

    return matrix.finish()


if __name__ == "__main__":
    raise SystemExit(main())
