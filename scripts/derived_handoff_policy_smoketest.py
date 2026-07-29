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
import platform
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SCHEMA = ROOT / "references" / "schemas" / "milestone_framework.schema.json"
BOOTSTRAP = SCRIPTS / "native_project_bootstrap.py"
GENERATOR = ROOT / "agents" / "generator.md"
ASSIGNMENT_PROCESS = ROOT / "references" / "ASSIGNMENT_MILESTONE_PROCESS.md"
HANDOFF_PROTOCOL = ROOT / "references" / "MILESTONE_FEEDBACK_HANDOFF_PROTOCOL.md"
FULL_RUN_CONTRACT = ROOT / "references" / "FULL_RUN_CONTRACT.md"
PYTHON_ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"}

sys.path.insert(0, str(SCRIPTS))
import assignment_milestone_transaction as transaction  # noqa: E402
import assignment_milestone_checkpoint_smoketest as checkpoint_fixture  # noqa: E402
import milestone_framework_smoketest as fixture  # noqa: E402
import render_lifecycle_state as renderer  # noqa: E402
from assignment_fixture_support import write_valid_contract  # noqa: E402
from milestone_path_contract import handoff_path  # noqa: E402
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


def _assert_bootstrap_help_discloses_policy() -> None:
    result = subprocess.run(
        [sys.executable, "-I", "-S", str(BOOTSTRAP), "--help"],
        cwd=ROOT,
        env=PYTHON_ENV,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"bootstrap help exit={result.returncode}: {(result.stdout + result.stderr)[:500]}"
        )
    help_text = " ".join((result.stdout + result.stderr).split())
    required = (
        "--handoff-policy {derived,audited}",
        "derived is the explicit default, audited preserves mandatory F9",
    )
    missing = [fact for fact in required if fact not in help_text]
    if missing:
        raise AssertionError(f"bootstrap help omits policy disclosure: {missing}")


def _assert_core_surfaces_are_policy_correct() -> None:
    required = {
        GENERATOR: (
            "accepted/approved/current state plus any validated optional non-consumed F9 "
            "under effective `derived`"
        ),
        ASSIGNMENT_PROCESS: (
            "Under effective `derived`, acceptance is authoritative without F9 and records "
            "`not_applicable`"
        ),
        HANDOFF_PROTOCOL: (
            "Under effective `derived`, the default authoritative handoff projection is "
            "`not_applicable` and milestone acceptance remains complete without a packet."
        ),
        FULL_RUN_CONTRACT: (
            "mandatory exact F9 only under effective `audited`; optional, non-gating exact F9 "
            "or `not_applicable` under effective `derived`"
        ),
    }
    missing: list[str] = []
    for path, fact in required.items():
        text = " ".join(path.read_text(encoding="utf-8").split())
        normalized_fact = " ".join(fact.split())
        if normalized_fact not in text:
            missing.append(f"{path.relative_to(ROOT).as_posix()}: {normalized_fact}")
    if missing:
        raise AssertionError(f"core surface requires policy-correct F9 language: {missing}")


def _prepare_m1_acceptance(project: Path) -> tuple[Path, Path]:
    """Build a real recorded M1 using the public synthetic transaction walk."""
    checkpoint_fixture.run(
        checkpoint_fixture.BOOTSTRAP,
        "--project-root", project,
        "--project-name", project.name,
        "--title", "Synthetic acceptance policy project",
        "--intended-reader", "researcher",
        "--created-at", "2026-07-29T16:00:00Z",
    )
    # The audited compatibility acceptance is deliberately prepared from exact
    # historical 1.0.0 bytes even after new bootstraps default to 1.1.0.
    document = _state(project)
    document["milestone_framework"]["contract_version"] = "1.0.0"
    document["milestone_framework"].pop("handoff_policy", None)
    _write_json(project / "reviews" / "phase_state.json", document)
    write_valid_contract(project)
    consumed, draft_policy = checkpoint_fixture.publish(
        project, "M1", b"# Synthetic M1 acceptance deliverable\n"
    )
    checkpoint = checkpoint_fixture.checkpoint_input(
        project, "M1", "2026-07-29T16:00:03Z", policy=draft_policy,
    )
    checkpoint_fixture.run(
        checkpoint_fixture.CHECKPOINT,
        "record",
        "--project-root", project,
        "--milestone", "M1",
        "--receipt", consumed,
        "--checkpoint", checkpoint,
        "--at", "2026-07-29T16:00:04Z",
    )
    approval = checkpoint_fixture.approval_input(
        project, "M1", "2026-07-29T16:00:05Z"
    )
    return checkpoint, approval


def _restore_project(project: Path, backup: Path, sandbox: Path) -> None:
    project_root = project.resolve()
    sandbox_root = sandbox.resolve()
    if project_root.parent != sandbox_root or backup.resolve().parent != sandbox_root:
        raise AssertionError("acceptance fixture restore escaped its temporary sandbox")
    if project.exists():
        shutil.rmtree(project)
    shutil.copytree(backup, project)


def _declare_derived(project: Path) -> None:
    document = _state(project)
    document["milestone_framework"]["contract_version"] = "1.1.0"
    document["milestone_framework"]["handoff_policy"] = "derived"
    _write_json(project / "reviews" / "phase_state.json", document)


def _handoff_tree(project: Path) -> dict[str, tuple[int, str]]:
    root = project / "reviews" / ".harness" / "handoffs"
    rows: dict[str, tuple[int, str]] = {}
    for path in sorted(root.rglob("*.json"), key=lambda item: item.as_posix()):
        payload = path.read_bytes()
        rows[path.relative_to(root).as_posix()] = (
            len(payload), hashlib.sha256(payload).hexdigest()
        )
    return rows


def _write_recovery_claim(project: Path, pid: int) -> Path:
    claim = project / "reviews" / ".harness" / "milestones" / "claims" / "transaction.lock"
    _write_json(
        claim,
        {
            "schema_version": "1.0.0",
            "pid": pid,
            "host": platform.node(),
            "operation": "accept:M1",
            "started_at": "2026-07-29T16:00:06Z",
        },
    )
    return claim


def main() -> int:
    matrix = Matrix()

    v1 = fixture._valid_ledger()
    v11_derived = copy.deepcopy(v1)
    v11_derived.update({"contract_version": "1.1.0", "handoff_policy": "derived"})
    v11_audited = copy.deepcopy(v1)
    v11_audited.update({"contract_version": "1.1.0", "handoff_policy": "audited"})
    v11_legacy = copy.deepcopy(v11_derived)
    v11_legacy["mode"] = "legacy"
    # Canonical legacy boundary shape from milestone_framework_smoketest's
    # valid_approved_legacy_migration fixture.  This schema-only row uses
    # syntactically valid digests because no project filesystem is consulted.
    v11_legacy["migration_boundary"] = {
        "authority": "user",
        "evidence_path": "reviews/migration_approval.md",
        "evidence_sha256": "0" * 64,
        "approved_at": "2026-07-13T18:00:00Z",
        "completed_through": "M5",
        "report_path": "reviews/migration_report.md",
        "report_sha256": "1" * 64,
    }

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
    matrix.case(
        "native bootstrap help discloses derived default and audited compatibility",
        _assert_bootstrap_help_discloses_policy,
    )
    matrix.case(
        "core Generator assignment handoff and full-run surfaces do not universally require F9 under derived",
        _assert_core_surfaces_are_policy_correct,
    )

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
            required = (
                "Declared handoff policy: `implicit`",
                "Effective handoff policy: `audited`",
                "Handoff policy resolution: `implicit audited (1.0.0 compatibility)`",
            )
            missing = [fact for fact in required if fact not in text]
            if missing:
                raise AssertionError(
                    f"renderer does not expose all 1.0.0 compatibility facts: {missing}"
                )

        matrix.case("renderer shows declared/effective implicit audited compatibility", render_implicit_audited)

        accept_project = sandbox / "acceptance-transaction"
        acceptance_checkpoint, acceptance_approval = _prepare_m1_acceptance(
            accept_project
        )
        acceptance_backup = sandbox / "acceptance-preimage"
        shutil.copytree(accept_project, acceptance_backup)

        def audited_acceptance_is_byte_compatible() -> None:
            _restore_project(accept_project, acceptance_backup, sandbox)
            before = _state(accept_project)
            before_events = len(before["milestone_framework"]["events"])
            before_tree = _handoff_tree(accept_project)
            transaction.accept(
                accept_project,
                "M1",
                acceptance_checkpoint,
                acceptance_approval,
                "2026-07-29T16:00:06Z",
            )
            after = _state(accept_project)
            handoff = after["milestone_framework"]["milestones"]["M1"]["handoff"]
            if handoff.get("status") != "ready":
                raise AssertionError("audited acceptance did not publish ready F9")
            packet = accept_project / handoff["packet_path"]
            packet_bytes = packet.read_bytes()
            if hashlib.sha256(packet_bytes).hexdigest() != handoff.get("packet_sha256"):
                raise AssertionError("audited acceptance ledger does not bind exact F9 bytes")
            packet_record = json.loads(packet_bytes)
            if packet_record.get("artifact_family") != "F9" or packet_record.get("from_milestone") != "M1":
                raise AssertionError("audited acceptance changed the F9 contract shape")
            new_types = [
                event.get("event_type")
                for event in after["milestone_framework"]["events"][before_events:]
            ]
            if new_types != ["milestone_accepted", "handoff_ready"]:
                raise AssertionError(f"audited acceptance event order changed: {new_types}")
            expected_relative = Path(handoff_path("M1")).relative_to(
                "reviews/.harness/handoffs"
            ).as_posix()
            if before_tree or set(_handoff_tree(accept_project)) != {expected_relative}:
                raise AssertionError("audited acceptance changed the one-packet F9 surface")

        matrix.case(
            "audited transaction.accept preserves exact ready-F9 byte/event behavior",
            audited_acceptance_is_byte_compatible,
        )

        def derived_default_accepts_without_f9() -> None:
            _restore_project(accept_project, acceptance_backup, sandbox)
            _declare_derived(accept_project)
            before = _state(accept_project)
            before_events = len(before["milestone_framework"]["events"])
            before_tree = _handoff_tree(accept_project)
            transaction.accept(
                accept_project,
                "M1",
                acceptance_checkpoint,
                acceptance_approval,
                "2026-07-29T16:00:06Z",
            )
            after = _state(accept_project)
            expected = {
                "status": "not_applicable",
                "packet_path": None,
                "packet_sha256": None,
            }
            if after["milestone_framework"]["milestones"]["M1"]["handoff"] != expected:
                raise AssertionError("derived default acceptance did not write exact not_applicable handoff")
            new_types = [
                event.get("event_type")
                for event in after["milestone_framework"]["events"][before_events:]
            ]
            if new_types != ["milestone_accepted"]:
                raise AssertionError(f"derived default acceptance fabricated F9 events: {new_types}")
            if _handoff_tree(accept_project) != before_tree:
                raise AssertionError("derived default acceptance created F9 bytes")

        matrix.case(
            "derived transaction.accept defaults to exact not_applicable with no F9",
            derived_default_accepts_without_f9,
        )

        def derived_emit_f9_is_exact_and_recovery_bound() -> None:
            _restore_project(accept_project, acceptance_backup, sandbox)
            _declare_derived(accept_project)
            before = _state(accept_project)
            before_events = len(before["milestone_framework"]["events"])
            transaction.accept(
                accept_project,
                "M1",
                acceptance_checkpoint,
                acceptance_approval,
                "2026-07-29T16:00:06Z",
                emit_f9=True,
            )
            after = _state(accept_project)
            handoff = after["milestone_framework"]["milestones"]["M1"]["handoff"]
            if handoff.get("status") != "ready":
                raise AssertionError("explicit derived --emit-f9 did not bind ready evidence")
            packet = accept_project / handoff["packet_path"]
            packet_before_recovery = packet.read_bytes()
            if hashlib.sha256(packet_before_recovery).hexdigest() != handoff.get("packet_sha256"):
                raise AssertionError("explicit derived F9 path/hash is not exact")
            new_types = [
                event.get("event_type")
                for event in after["milestone_framework"]["events"][before_events:]
            ]
            if new_types != ["milestone_accepted", "handoff_ready"]:
                raise AssertionError(f"explicit derived F9 event order is wrong: {new_types}")

            claim = _write_recovery_claim(accept_project, 2147483647)
            transaction.recover_claim(
                accept_project, "inspected-milestone-state-and-journal"
            )
            if claim.exists() or packet.read_bytes() != packet_before_recovery:
                raise AssertionError("recovery removed or changed state-bound optional F9")
            journal = accept_project / "reviews" / ".harness" / "milestones" / "journal"
            if list(journal.glob(f"orphan-{packet.stem}-*.json")):
                raise AssertionError("state-bound optional F9 was misclassified as residue")

        matrix.case(
            "explicit derived emit_f9 is exact and bound evidence survives dead-owner recovery",
            derived_emit_f9_is_exact_and_recovery_bound,
        )

        def dead_owner_archives_only_unbound_f9_residue() -> None:
            _restore_project(accept_project, acceptance_backup, sandbox)
            orphan = accept_project / handoff_path("M1")
            _write_json(orphan, {"synthetic_unbound_residue": True})
            orphan_bytes = orphan.read_bytes()
            claim = _write_recovery_claim(accept_project, 2147483647)
            transaction.recover_claim(
                accept_project, "inspected-milestone-state-and-journal"
            )
            if claim.exists() or orphan.exists():
                raise AssertionError("dead-owner recovery did not clear claim/unbound residue")
            journal = accept_project / "reviews" / ".harness" / "milestones" / "journal"
            archives = list(journal.glob(f"orphan-{orphan.stem}-*.json"))
            if len(archives) != 1 or archives[0].read_bytes() != orphan_bytes:
                raise AssertionError("unbound F9 residue was not archived byte-exactly")

        matrix.case(
            "dead-owner recovery archives byte-exact unbound F9 residue",
            dead_owner_archives_only_unbound_f9_residue,
        )

        def live_owner_refuses_unbound_f9_recovery() -> None:
            _restore_project(accept_project, acceptance_backup, sandbox)
            orphan = accept_project / handoff_path("M1")
            _write_json(orphan, {"synthetic_unbound_residue": True})
            orphan_before = orphan.read_bytes()
            claim = _write_recovery_claim(accept_project, os.getpid())
            claim_before = claim.read_bytes()
            try:
                transaction.recover_claim(
                    accept_project, "inspected-milestone-state-and-journal"
                )
            except transaction.MilestoneTransactionError as exc:
                if exc.code != "AMC-RECOVERY-LIVE":
                    raise AssertionError(f"wrong live-owner recovery code: {exc.code}") from exc
            else:
                raise AssertionError("live owner did not block F9-residue recovery")
            if claim.read_bytes() != claim_before or orphan.read_bytes() != orphan_before:
                raise AssertionError("live-owner refusal changed claim or unbound F9 bytes")

        matrix.case(
            "live owner refuses recovery and preserves claim/unbound F9 bytes",
            live_owner_refuses_unbound_f9_recovery,
        )

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
                    raise AssertionError(
                        "derived optional-F9 byte validation was not reached; "
                        f"current refusal code is {exc.code}"
                    ) from exc
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
                    raise AssertionError(
                        "derived approval guard was not reached; current refusal is "
                        f"{exc.code} {exc.message}"
                    ) from exc
            else:
                raise AssertionError("derived begin admitted a predecessor without approved authority")
            if state_path.read_bytes() != before:
                raise AssertionError("forged-acceptance refusal changed state")

        matrix.case("derived policy does not weaken approval authority", forged_acceptance_refuses_without_state_change)

    return matrix.finish()


if __name__ == "__main__":
    raise SystemExit(main())
