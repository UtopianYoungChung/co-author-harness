#!/usr/bin/env python3
"""Synthetic red regressions for v1.1 derived/audited handoff policy.

The suite reuses committed fixture constructors but materializes projects only
inside disposable package-local temporary directories.  It never edits a live
project and never invokes the global fixture runner.
"""

from __future__ import annotations

import copy
import hashlib
import importlib
import inspect
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SCHEMA = ROOT / "references" / "schemas" / "milestone_framework.schema.json"
BOOTSTRAP = SCRIPTS / "native_project_bootstrap.py"
PYTHON_ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"}

sys.path.insert(0, str(SCRIPTS))
import assignment_milestone_transaction as transaction  # noqa: E402
import milestone_framework_smoketest as fixture  # noqa: E402
import render_lifecycle_state as renderer  # noqa: E402
from semantic_graph_fixture_support import semantic_graph_fixture_environment  # noqa: E402


class Matrix:
    def __init__(self) -> None:
        self.passed: list[str] = []
        self.failed: list[tuple[str, str]] = []

    def case(self, name: str, operation: Callable[[], None]) -> None:
        try:
            operation()
        except Exception as exc:
            detail = f"{type(exc).__name__}: {exc}".replace("\n", " | ")
            self.failed.append((name, detail))
            print(f"FAIL {name}: {detail}")
        else:
            self.passed.append(name)
            print(f"PASS {name}")

    def finish(self) -> int:
        print(
            "DERIVED_HANDOFF_POLICY_MATRIX "
            f"passed={len(self.passed)} failed={len(self.failed)} "
            f"total={len(self.passed) + len(self.failed)}"
        )
        return 1 if self.failed else 0


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_json_bytes(value))


def _schema_accepts(ledger: dict[str, Any]) -> bool:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    try:
        fixture._validate(ledger, schema, schema, "milestone_framework")
    except fixture.SchemaError:
        return False
    return True


def _assert_schema(ledger: dict[str, Any], accepted: bool) -> None:
    actual = _schema_accepts(ledger)
    if actual is not accepted:
        raise AssertionError(f"schema accepted={actual}, expected {accepted}")


def _resolver_callable() -> Callable[[dict[str, Any]], dict[str, Any]]:
    try:
        module = importlib.import_module("milestone_handoff_policy")
    except ModuleNotFoundError as exc:
        raise AssertionError("canonical milestone_handoff_policy module is absent") from exc
    resolver = getattr(module, "resolve_handoff_policy", None)
    if not callable(resolver):
        raise AssertionError("resolve_handoff_policy(framework) is absent")
    return resolver


def _resolver(framework: dict[str, Any]) -> dict[str, Any]:
    resolver = _resolver_callable()
    before = _json_bytes(framework)
    result = resolver(framework)
    if _json_bytes(framework) != before:
        raise AssertionError("effective-policy resolution rewrote its input")
    if not isinstance(result, dict):
        raise AssertionError("resolver did not return a record")
    return result


def _assert_resolution(framework: dict[str, Any], declared: str | None, effective: str, result: str) -> None:
    resolved = _resolver(framework)
    expected = {
        "declared_policy": declared,
        "effective_policy": effective,
        "result": result,
    }
    for key, value in expected.items():
        if resolved.get(key) != value:
            raise AssertionError(f"{key}={resolved.get(key)!r}, expected {value!r}; record={resolved}")


def _expect_resolver_refusal(framework: dict[str, Any]) -> None:
    resolver = _resolver_callable()
    before = _json_bytes(framework)
    try:
        resolver(framework)
    except Exception:
        if _json_bytes(framework) != before:
            raise AssertionError("resolver refusal mutated input")
        return
    raise AssertionError("unsupported/contradictory policy resolved instead of refusing")


def _reset_after_m1(ledger: dict[str, Any]) -> None:
    for milestone in ("M2", "M3", "M4", "M5"):
        fixture._reset_milestone(ledger["milestones"][milestone])
    fixture._drop_milestone_events(ledger, "M2", "M3", "M4", "M5")


def _transaction_project(
    sandbox: Path,
    name: str,
    *,
    contract_version: str,
    handoff_policy: str | None,
    m1_handoff: str,
    approval_status: str = "approved",
) -> Path:
    project = sandbox / name
    project.mkdir()
    ledger = fixture._materialize_native_project(
        project,
        include_scholarly=True,
        scholarly_milestones=frozenset({"M1"}),
    )
    _reset_after_m1(ledger)
    ledger["contract_version"] = contract_version
    if handoff_policy is None:
        ledger.pop("handoff_policy", None)
    else:
        ledger["handoff_policy"] = handoff_policy

    m1 = ledger["milestones"]["M1"]
    if approval_status != "approved":
        m1["approval"] = {
            "status": approval_status,
            "authority": None,
            "evidence_path": None,
            "approved_at": None,
        }
    if m1_handoff == "not_applicable":
        m1["handoff"] = {"status": "not_applicable", "packet_path": None, "packet_sha256": None}
        ledger["events"] = [
            event for event in ledger["events"]
            if not (event.get("milestone") == "M1" and event.get("event_type") in {"handoff_ready", "handoff_consumed"})
        ]
    elif m1_handoff == "ready":
        m1["handoff"]["status"] = "ready"
        ledger["events"] = [
            event for event in ledger["events"]
            if not (event.get("milestone") == "M1" and event.get("event_type") == "handoff_consumed")
        ]
    else:
        raise ValueError(f"unsupported fixture handoff: {m1_handoff}")
    fixture._resequence_events(ledger)

    handoff_root = project / "reviews" / ".harness" / "handoffs"
    for packet in handoff_root.glob("*_packet.json"):
        if m1_handoff == "ready" and packet.name == "M1_packet.json":
            continue
        packet.unlink()

    document = fixture._phase_document(ledger, current_phase="Ph1")
    document["terminal_phase_reached"] = False
    document["terminal_round_id"] = None
    _write_json(project / "reviews" / "phase_state.json", document)
    return project


def _begin(project: Path) -> None:
    transaction.begin(project, "M2", "2026-07-29T15:00:00Z")


def _state(project: Path) -> dict[str, Any]:
    return json.loads((project / "reviews" / "phase_state.json").read_text(encoding="utf-8"))


def _run_bootstrap(project: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable, "-I", "-S", str(BOOTSTRAP),
            "--project-root", str(project),
            "--project-name", project.name,
            "--title", "Synthetic policy project",
            "--intended-reader", "researcher",
            "--created-at", "2026-07-29T15:00:00Z",
            *extra,
        ],
        cwd=ROOT,
        env=PYTHON_ENV,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )


def _assert_bootstrap(project: Path, policy: str, *extra: str) -> None:
    result = _run_bootstrap(project, *extra)
    if result.returncode != 0:
        raise AssertionError(f"bootstrap exit={result.returncode}: {(result.stdout + result.stderr)[:500]}")
    framework = _state(project)["milestone_framework"]
    if framework.get("contract_version") != "1.1.0" or framework.get("handoff_policy") != policy:
        raise AssertionError(
            f"bootstrap wrote contract={framework.get('contract_version')!r} "
            f"policy={framework.get('handoff_policy')!r}"
        )
    if framework.get("mode") != "native":
        raise AssertionError("handoff policy changed milestone_framework.mode")


def main() -> int:
    matrix = Matrix()

    v1 = fixture._valid_ledger()
    v11_derived = copy.deepcopy(v1)
    v11_derived.update({"contract_version": "1.1.0", "handoff_policy": "derived"})
    v11_audited = copy.deepcopy(v1)
    v11_audited.update({"contract_version": "1.1.0", "handoff_policy": "audited"})
    v11_legacy = copy.deepcopy(v11_derived)
    v11_legacy["mode"] = "legacy"

    matrix.case("schema preserves untouched 1.0.0 without policy", lambda: _assert_schema(v1, True))
    matrix.case(
        "schema refuses policy on 1.0.0",
        lambda: _assert_schema({**copy.deepcopy(v1), "handoff_policy": "derived"}, False),
    )
    matrix.case("schema accepts explicit derived 1.1.0", lambda: _assert_schema(v11_derived, True))
    matrix.case("schema accepts explicit audited 1.1.0", lambda: _assert_schema(v11_audited, True))
    matrix.case("schema accepts legacy mode at explicit 1.1.0", lambda: _assert_schema(v11_legacy, True))
    matrix.case(
        "schema refuses missing policy at 1.1.0",
        lambda: _assert_schema({**copy.deepcopy(v1), "contract_version": "1.1.0"}, False),
    )
    matrix.case(
        "schema refuses unknown policy",
        lambda: _assert_schema({**copy.deepcopy(v1), "contract_version": "1.1.0", "handoff_policy": "optional"}, False),
    )

    matrix.case(
        "resolver maps untouched 1.0.0 to implicit audited without rewrite",
        lambda: _assert_resolution(v1, None, "audited", "IMPLICIT_AUDITED_COMPATIBILITY"),
    )
    matrix.case(
        "resolver maps explicit 1.1.0 audited",
        lambda: _assert_resolution(v11_audited, "audited", "audited", "EXPLICIT_AUDITED"),
    )
    matrix.case(
        "resolver maps explicit 1.1.0 derived",
        lambda: _assert_resolution(v11_derived, "derived", "derived", "EXPLICIT_DERIVED"),
    )
    matrix.case(
        "resolver refuses contradictory 1.0.0 policy without rewrite",
        lambda: _expect_resolver_refusal({**copy.deepcopy(v1), "handoff_policy": "derived"}),
    )

    def accept_exposes_optional_f9() -> None:
        parameter = inspect.signature(transaction.accept).parameters.get("emit_f9")
        if parameter is None or parameter.default is not False or parameter.kind is not inspect.Parameter.KEYWORD_ONLY:
            raise AssertionError("accept must expose keyword-only emit_f9=False")

    matrix.case("accept exposes explicit optional F9 request with default off", accept_exposes_optional_f9)

    with tempfile.TemporaryDirectory(prefix="v041-derived-policy-", dir=ROOT) as raw, semantic_graph_fixture_environment():
        sandbox = Path(raw)
        matrix.case(
            "new native bootstrap explicitly defaults to derived 1.1.0",
            lambda: _assert_bootstrap(sandbox / "bootstrap-derived", "derived"),
        )
        matrix.case(
            "new native bootstrap permits explicit audited 1.1.0",
            lambda: _assert_bootstrap(sandbox / "bootstrap-audited", "audited", "--handoff-policy", "audited"),
        )

        def render_implicit_audited() -> None:
            project = sandbox / "render-v1"
            project.mkdir()
            ledger = fixture._materialize_native_project(project, include_scholarly=True)
            _write_json(project / "reviews" / "phase_state.json", fixture._phase_document(ledger))
            text = renderer.render_bytes(project, "2026-07-29T15:00:00Z").decode("utf-8")
            if "Declared handoff policy: `implicit`" not in text or "Effective handoff policy: `audited`" not in text:
                raise AssertionError("renderer does not label 1.0.0 implicit audited compatibility")

        matrix.case("renderer shows declared/effective implicit audited compatibility", render_implicit_audited)

        def audited_begin_unchanged() -> None:
            project = _transaction_project(
                sandbox, "audited-begin", contract_version="1.0.0",
                handoff_policy=None, m1_handoff="ready",
            )
            packet = project / _state(project)["milestone_framework"]["milestones"]["M1"]["handoff"]["packet_path"]
            packet_before = packet.read_bytes()
            _begin(project)
            framework = _state(project)["milestone_framework"]
            if framework["milestones"]["M1"]["handoff"]["status"] != "consumed":
                raise AssertionError("audited begin did not consume predecessor F9")
            if framework["milestones"]["M2"]["status"] != "in_progress":
                raise AssertionError("audited begin did not start M2")
            if packet.read_bytes() != packet_before:
                raise AssertionError("audited begin rewrote packet bytes")
            if not any(event.get("event_type") == "handoff_consumed" for event in framework["events"]):
                raise AssertionError("audited begin omitted handoff_consumed")

        matrix.case("audited 1.0.0 begin semantics remain byte-compatible", audited_begin_unchanged)

        def derived_begin_without_f9() -> None:
            project = _transaction_project(
                sandbox, "derived-no-f9", contract_version="1.1.0",
                handoff_policy="derived", m1_handoff="not_applicable",
            )
            before = _state(project)
            _begin(project)
            after = _state(project)
            expected_handoff = {"status": "not_applicable", "packet_path": None, "packet_sha256": None}
            if after["milestone_framework"]["milestones"]["M1"]["handoff"] != expected_handoff:
                raise AssertionError("derived begin changed the not_applicable handoff representation")
            if after["milestone_framework"]["milestones"]["M2"]["status"] != "in_progress":
                raise AssertionError("derived begin did not start successor")
            new_events = after["milestone_framework"]["events"][len(before["milestone_framework"]["events"]):]
            if any(event.get("event_type") == "handoff_consumed" for event in new_events):
                raise AssertionError("derived begin emitted handoff_consumed")
            if list((project / "reviews" / ".harness" / "handoffs").glob("*.json")):
                raise AssertionError("derived begin created an F9 packet")

        matrix.case("derived successor begins from accepted current predecessor without F9", derived_begin_without_f9)

        def derived_optional_f9_is_not_consumed() -> None:
            project = _transaction_project(
                sandbox, "derived-optional-f9", contract_version="1.1.0",
                handoff_policy="derived", m1_handoff="ready",
            )
            before = _state(project)
            handoff = before["milestone_framework"]["milestones"]["M1"]["handoff"]
            packet = project / handoff["packet_path"]
            packet_before = packet.read_bytes()
            _begin(project)
            after = _state(project)
            if after["milestone_framework"]["milestones"]["M1"]["handoff"] != handoff:
                raise AssertionError("derived begin consumed or rewrote optional F9 state")
            if packet.read_bytes() != packet_before or hashlib.sha256(packet_before).hexdigest() != handoff["packet_sha256"]:
                raise AssertionError("derived begin changed optional F9 bytes/hash")
            new_events = after["milestone_framework"]["events"][len(before["milestone_framework"]["events"]):]
            if any(event.get("event_type") == "handoff_consumed" for event in new_events):
                raise AssertionError("derived optional F9 gained consumption authority")

        matrix.case("derived optional F9 remains exact ready evidence and non-consumed", derived_optional_f9_is_not_consumed)

        def invalid_optional_packet_refuses_without_state_change() -> None:
            project = _transaction_project(
                sandbox, "derived-tampered-f9", contract_version="1.1.0",
                handoff_policy="derived", m1_handoff="ready",
            )
            state_path = project / "reviews" / "phase_state.json"
            handoff = _state(project)["milestone_framework"]["milestones"]["M1"]["handoff"]
            (project / handoff["packet_path"]).write_bytes(b"{}\n")
            before = state_path.read_bytes()
            try:
                _begin(project)
            except transaction.MilestoneTransactionError as exc:
                if exc.code not in {"MF-HANDOFF", "MF-BINDING"}:
                    raise AssertionError(f"tampered optional F9 refused for unrelated code {exc.code}") from exc
            else:
                raise AssertionError("tampered optional F9 was accepted")
            if state_path.read_bytes() != before:
                raise AssertionError("tampered optional F9 refusal changed state")

        matrix.case("present optional F9 remains fully validated", invalid_optional_packet_refuses_without_state_change)

        def forged_acceptance_refuses_without_state_change() -> None:
            project = _transaction_project(
                sandbox, "derived-forged-approval", contract_version="1.1.0",
                handoff_policy="derived", m1_handoff="not_applicable", approval_status="pending",
            )
            state_path = project / "reviews" / "phase_state.json"
            before = state_path.read_bytes()
            try:
                _begin(project)
            except transaction.MilestoneTransactionError as exc:
                if "approval" not in exc.message.lower():
                    raise AssertionError(f"forged acceptance refused for unrelated reason: {exc.code} {exc.message}") from exc
            else:
                raise AssertionError("derived begin admitted a predecessor without approved authority")
            if state_path.read_bytes() != before:
                raise AssertionError("forged-acceptance refusal changed state")

        matrix.case("derived policy does not weaken approval authority", forged_acceptance_refuses_without_state_change)

    return matrix.finish()


if __name__ == "__main__":
    raise SystemExit(main())
