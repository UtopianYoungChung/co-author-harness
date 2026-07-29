#!/usr/bin/env python3
"""Synthetic red tests for ``lab-iteration-derived-handoff-v1`` migration.

All projects live in disposable package-local directories.  The suite invokes
the dedicated migration directly; it never runs the fixture registry and never
opens or mutates a research project.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import importlib
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
MIGRATOR = SCRIPTS / "migrate_lab_iteration_derived_handoff.py"
MIGRATION_ID = "lab-iteration-derived-handoff-v1"
LANE = Path("reviews/.harness/migrations") / MIGRATION_ID
LEDGER = Path("reviews/phase_state.json")
PYTHON_ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"}

sys.path.insert(0, str(SCRIPTS))
import milestone_framework_smoketest as fixture  # noqa: E402
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
            "MIGRATE_DERIVED_HANDOFF_MATRIX "
            f"passed={len(self.passed)} failed={len(self.failed)} "
            f"total={len(self.passed) + len(self.failed)}"
        )
        return 1 if self.failed else 0


def _sha_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_json_bytes(value))


def _write_bound_file(path: Path, payload: bytes) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {"path": path.as_posix(), "sha256": _sha_bytes(payload), "bytes": len(payload)}


def _run(operation: str, project: Path, *args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable, str(MIGRATOR), operation,
            "--project-root", str(project), *(str(arg) for arg in args),
        ],
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
        detail = (result.stdout + result.stderr).strip()
        if not MIGRATOR.is_file():
            raise AssertionError("dedicated v0.41 migration implementation is absent") from exc
        raise AssertionError(f"migration emitted no JSON (exit {result.returncode}): {detail[:500]}") from exc
    if not isinstance(value, dict):
        raise AssertionError(f"migration emitted {type(value).__name__}, not an object")
    return value


def _receipt(payload: dict[str, Any]) -> dict[str, Any]:
    candidate = payload.get("receipt", payload)
    if not isinstance(candidate, dict):
        raise AssertionError("response does not contain a receipt object")
    return candidate


def _codes(value: Any) -> set[str]:
    result: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "code" and isinstance(child, str):
                result.add(child)
            elif key == "blockers" and isinstance(child, list):
                result.update(item for item in child if isinstance(item, str))
            result.update(_codes(child))
    elif isinstance(value, list):
        for child in value:
            result.update(_codes(child))
    return result


def _expect(result: subprocess.CompletedProcess[str], exit_code: int, outcome: str, code: str | None = None) -> dict[str, Any]:
    payload = _payload(result)
    receipt = _receipt(payload)
    if result.returncode != exit_code:
        raise AssertionError(f"expected exit {exit_code}, got {result.returncode}: {payload}")
    if receipt.get("outcome") != outcome:
        raise AssertionError(f"expected outcome {outcome}, got {receipt.get('outcome')}: {receipt}")
    if code is not None and code not in _codes(payload):
        raise AssertionError(f"expected blocker {code}, got {sorted(_codes(payload))}")
    return receipt


def _snapshot(root: Path, *, exclude_migration_lane: bool = False) -> dict[str, tuple[int, str]]:
    rows: dict[str, tuple[int, str]] = {}
    if not root.exists():
        return rows
    lane = (root / LANE).resolve(strict=False)
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file() or path.is_symlink():
            continue
        resolved = path.resolve()
        if exclude_migration_lane and (resolved == lane or resolved.is_relative_to(lane)):
            continue
        payload = path.read_bytes()
        rows[path.relative_to(root).as_posix()] = (len(payload), _sha_bytes(payload))
    return rows


def _external_snapshot(project: Path) -> dict[str, tuple[int, str]]:
    rows = _snapshot(project, exclude_migration_lane=True)
    rows.pop(LEDGER.as_posix(), None)
    return rows


def _project(sandbox: Path, name: str, *, legacy: bool = False) -> tuple[Path, bytes]:
    # Scholarly/verifier compatibility artifacts include context derived from the
    # canonical project root.  Materialize once at the exact working path and
    # always restore to that same path; never validate the relocated pristine
    # backup as though it were a project.
    project = sandbox / ".valid-v1-working"
    pristine = sandbox / ".valid-v1-pristine"
    if not pristine.exists():
        project.mkdir()
        template_ledger = fixture._materialize_native_project(project, include_scholarly=True)
        template_ledger["contract_version"] = "1.0.0"
        template_ledger.pop("handoff_policy", None)
        _write_json(project / LEDGER, fixture._phase_document(template_ledger))
        _write_json(project / "reviews" / "assignment_contract.json", {"status": "resolved"})
        _write_json(project / "reviews" / "promotion_receipt.json", {"status": "not_promoted"})
        protected = project / "protected" / "governed.bin"
        protected.parent.mkdir(parents=True)
        protected.write_bytes(b"synthetic protected bytes\x00\xff")
        final = project / "manuscript" / "final-deliverable.md"
        final.parent.mkdir(parents=True, exist_ok=True)
        final.write_text("Synthetic final deliverable.\n", encoding="utf-8")
        shutil.copytree(project, pristine)
    else:
        if project.exists():
            shutil.rmtree(project)
        shutil.copytree(pristine, project)
    ledger_path = project / LEDGER
    if legacy:
        document = json.loads(ledger_path.read_text(encoding="utf-8"))
        approval = project / "reviews" / "migration_approval.md"
        report = project / "reviews" / "migration_report.md"
        approval.write_bytes(b"status: APPROVED\nauthority: user\n")
        report.write_bytes(b'{"adjudication_outcome":"approved","authority":"user"}\n')
        framework = document["milestone_framework"]
        framework["mode"] = "legacy"
        framework["migration_boundary"] = {
            "authority": "user",
            "evidence_path": approval.relative_to(project).as_posix(),
            "evidence_sha256": _sha(approval),
            "approved_at": "2026-07-29T14:59:00Z",
            "completed_through": "M5",
            "report_path": report.relative_to(project).as_posix(),
            "report_sha256": _sha(report),
        }
        _write_json(ledger_path, document)
    return project, ledger_path.read_bytes()


def _active_project(sandbox: Path, name: str) -> tuple[Path, bytes]:
    project = sandbox / ".valid-v1-working"
    if project.exists():
        shutil.rmtree(project)
    project.mkdir()
    fixture._write_real_case("valid_ph2_target", project)
    _write_json(project / "reviews" / "assignment_contract.json", {"status": "resolved"})
    _write_json(project / "reviews" / "promotion_receipt.json", {"status": "not_promoted"})
    _write_bound_file(project / "protected" / "governed.bin", b"synthetic protected bytes\x00\xff")
    _write_bound_file(project / "manuscript" / "final-deliverable.md", b"Synthetic final deliverable.\n")
    ledger_path = project / LEDGER
    return project, ledger_path.read_bytes()


def _authority(project: Path, preimage: bytes, *, digest: str | None = None, suffix: str = "valid") -> Path:
    path = project / "reviews" / ".harness" / "migration-authority" / f"{suffix}.json"
    receipt = {
        "schema": "co-author-harness/milestone-handoff-policy-migration-authority/v1",
        "authority_receipt_id": f"authority-{suffix}",
        "migration_id": MIGRATION_ID,
        "project_id": "smoke-project",
        "ledger_path": LEDGER.as_posix(),
        "preimage": {"sha256": digest or _sha_bytes(preimage), "bytes": len(preimage)},
        "source_contract_version": "1.0.0",
        "source_effective_handoff_policy": "audited",
        "target_contract_version": "1.1.0",
        "target_handoff_policy": "derived",
        "authority": "user",
        "authorized_at": "2026-07-29T15:00:00Z",
        "reason": "Synthetic exact-byte authorization for the C1 red boundary.",
        "nonce": f"nonce-{suffix}-0123456789",
    }
    _write_json(path, receipt)
    return path


def _binding(project: Path, path: Path) -> dict[str, str]:
    return {"path": path.relative_to(project).as_posix(), "sha256": _sha(path)}


def _canonical_without_policy(document: dict[str, Any]) -> str:
    value = copy.deepcopy(document)
    framework = value["milestone_framework"]
    framework.pop("contract_version", None)
    framework.pop("handoff_policy", None)
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return _sha_bytes(payload)


def _handoff_snapshot(project: Path) -> dict[str, Any]:
    framework = json.loads((project / LEDGER).read_text(encoding="utf-8"))["milestone_framework"]
    return {
        "records": {
            milestone: copy.deepcopy(record["handoff"])
            for milestone, record in framework["milestones"].items()
        },
        "events": [
            copy.deepcopy(event)
            for event in framework["events"]
            if event.get("event_type") in {"handoff_ready", "handoff_consumed"}
        ],
        "tree": _snapshot(project / "reviews" / ".harness" / "handoffs"),
    }


def _json_records(root: Path) -> list[tuple[Path, dict[str, Any], bytes]]:
    records: list[tuple[Path, dict[str, Any], bytes]] = []
    if not root.exists():
        return records
    for path in sorted(root.rglob("*.json"), key=lambda item: item.as_posix()):
        payload = path.read_bytes()
        try:
            value = json.loads(payload)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            records.append((path, value, payload))
    return records


def _one_record(
    records: list[tuple[Path, dict[str, Any], bytes]],
    *,
    schema: str,
    **fields: Any,
) -> tuple[Path, dict[str, Any], bytes]:
    matches = [
        record for record in records
        if record[1].get("schema") == schema
        and all(record[1].get(key) == value for key, value in fields.items())
    ]
    if len(matches) != 1:
        raise AssertionError(
            f"expected one prepared {schema} record with {fields}, found {len(matches)}"
        )
    return matches[0]


def _assert_common_proof(receipt: dict[str, Any], project: Path, authority: Path) -> None:
    if receipt.get("schema") != "co-author-harness/milestone-handoff-policy-migration-receipt/v1":
        raise AssertionError(f"wrong receipt schema: {receipt.get('schema')!r}")
    if receipt.get("migration_id") != MIGRATION_ID or receipt.get("ledger_path") != LEDGER.as_posix():
        raise AssertionError("receipt does not bind exact migration/ledger")
    if receipt.get("authority_receipt") != _binding(project, authority):
        raise AssertionError("receipt does not bind exact authority bytes")
    permitted = [
        {"path": "/milestone_framework/contract_version", "from": "1.0.0", "to": "1.1.0"},
        {"path": "/milestone_framework/handoff_policy", "from": None, "to": "derived"},
    ]
    if receipt.get("permitted_changes") != permitted:
        raise AssertionError(f"unexpected permitted changes: {receipt.get('permitted_changes')}")
    inventory = receipt.get("external_surface_inventory")
    if not isinstance(inventory, dict) or inventory.get("pre") != inventory.get("post"):
        raise AssertionError("external surface inventory is absent or changed")


def _assert_only_two_semantic_changes(preimage: bytes, postimage: bytes) -> None:
    before = json.loads(preimage)
    after = json.loads(postimage)
    if before["milestone_framework"].get("contract_version") != "1.0.0":
        raise AssertionError("fixture preimage is not 1.0.0")
    if after["milestone_framework"].get("contract_version") != "1.1.0":
        raise AssertionError("migration did not write 1.1.0")
    if "handoff_policy" in before["milestone_framework"]:
        raise AssertionError("fixture preimage unexpectedly declares policy")
    if after["milestone_framework"].get("handoff_policy") != "derived":
        raise AssertionError("migration did not write explicit derived policy")
    if _canonical_without_policy(before) != _canonical_without_policy(after):
        raise AssertionError("migration changed semantic state beyond the two permitted paths")


def _claim(project: Path, authority: Path, preimage: bytes, *, pid: int, transaction_id: str = "occupied") -> Path:
    path = project / LANE / "transaction.lock"
    claim = {
        "schema": "co-author-harness/milestone-handoff-policy-migration-claim/v1",
        "claim_type": "exclusive_no_ttl",
        "state": "active",
        "transaction_id": transaction_id,
        "migration_id": MIGRATION_ID,
        "operation": "apply",
        "host": platform.node(),
        "pid": pid,
        "created_at": "2026-07-29T15:00:01Z",
        "completed_at": None,
        "project_id": "smoke-project",
        "ledger_path": LEDGER.as_posix(),
        "ledger_preimage_sha256": _sha_bytes(preimage),
        "authority_receipt": _binding(project, authority),
        "recovery": None,
    }
    _write_json(path, claim)
    return path


def _apply(project: Path, authority: Path) -> tuple[dict[str, Any], Path, Path]:
    receipt = _expect(
        _run("apply", project, "--authority-receipt", authority, "--at", "2026-07-29T15:00:02Z"),
        0,
        "APPLIED",
    )
    transaction_id = receipt.get("transaction_id")
    if not isinstance(transaction_id, str) or not transaction_id:
        raise AssertionError("apply receipt lacks transaction_id")
    transaction_root = project / LANE / "transactions" / transaction_id
    apply_path = transaction_root / "apply.json"
    rollback_manifest = transaction_root / "rollback_manifest.json"
    if not apply_path.is_file() or json.loads(apply_path.read_text(encoding="utf-8")) != receipt:
        raise AssertionError("committed apply receipt is absent or differs from stdout")
    if not rollback_manifest.is_file():
        raise AssertionError("rollback manifest was not committed")
    return receipt, apply_path, rollback_manifest


def _interrupt_apply_after_state_publish(project: Path, authority: Path) -> tuple[Path, Path]:
    try:
        module = importlib.import_module("migrate_lab_iteration_derived_handoff")
    except ModuleNotFoundError as exc:
        raise AssertionError("dedicated v0.41 migration implementation is absent") from exc
    apply_migration = getattr(module, "apply_migration", None)
    if not callable(apply_migration):
        raise AssertionError("migration lacks apply_migration interruption test seam")

    class SyntheticInterruption(BaseException):
        pass

    def interrupt_after_state_publish() -> None:
        raise SyntheticInterruption("synthetic crash after state-last replacement")

    try:
        apply_migration(
            project,
            authority,
            at="2026-07-29T15:00:02Z",
            _after_state_publish=interrupt_after_state_publish,
        )
    except SyntheticInterruption:
        pass
    else:
        raise AssertionError("post-state-publish interruption seam did not interrupt apply")

    live_claim = project / LANE / "transaction.lock"
    if not live_claim.is_file():
        raise AssertionError("interrupted state-last apply did not retain its live claim")
    claim = json.loads(live_claim.read_text(encoding="utf-8"))
    transaction_id = claim.get("transaction_id")
    if claim.get("state") != "active" or not isinstance(transaction_id, str) or not transaction_id:
        raise AssertionError("interrupted state-last apply retained a malformed claim")
    return live_claim, project / LANE / "transactions" / transaction_id


def _interrupt_rollback_after_state_publish(
    project: Path,
    authority: Path,
    apply_receipt: Path,
    rollback_manifest: Path,
) -> tuple[Path, Path]:
    try:
        module = importlib.import_module("migrate_lab_iteration_derived_handoff")
    except ModuleNotFoundError as exc:
        raise AssertionError("dedicated v0.41 migration implementation is absent") from exc
    rollback_migration = getattr(module, "rollback_migration", None)
    if not callable(rollback_migration):
        raise AssertionError("migration lacks rollback_migration interruption test seam")

    class SyntheticInterruption(BaseException):
        pass

    def interrupt_after_state_publish() -> None:
        raise SyntheticInterruption("synthetic crash after rollback state restoration")

    try:
        rollback_migration(
            project,
            authority,
            apply_receipt,
            rollback_manifest,
            at="2026-07-29T15:00:03Z",
            _after_state_publish=interrupt_after_state_publish,
        )
    except SyntheticInterruption:
        pass
    else:
        raise AssertionError("post-state-publish interruption seam did not interrupt rollback")

    live_claim = project / LANE / "transaction.lock"
    if not live_claim.is_file():
        raise AssertionError("interrupted rollback did not retain its live claim")
    claim = json.loads(live_claim.read_text(encoding="utf-8"))
    transaction_id = claim.get("transaction_id")
    if (
        claim.get("state") != "active"
        or claim.get("operation") != "rollback"
        or not isinstance(transaction_id, str)
        or not transaction_id
    ):
        raise AssertionError("interrupted rollback retained a malformed claim")
    return live_claim, project / LANE / "transactions" / transaction_id


def main() -> int:
    matrix = Matrix()
    with tempfile.TemporaryDirectory(prefix="v041-migrate-derived-", dir=ROOT) as raw, semantic_graph_fixture_environment():
        sandbox = Path(raw)

        def no_authority_refuses_without_writes() -> None:
            project, _ = _project(sandbox, "no-authority")
            before = _snapshot(project)
            receipt = _expect(_run("dry-run", project), 4, "REFUSED", "MHD-MIGRATION-AUTHORITY-REQUIRED")
            if _snapshot(project) != before:
                raise AssertionError("authority refusal wrote project bytes")
            if receipt.get("authority_receipt") is not None or receipt.get("claim") is not None:
                raise AssertionError("refused receipt invented authority/claim proof")

        matrix.case("dry-run without authority refuses and writes nothing", no_authority_refuses_without_writes)

        def dry_run_exact_and_read_only() -> None:
            project, preimage = _project(sandbox, "dry-run")
            authority = _authority(project, preimage)
            before = _snapshot(project)
            receipt = _expect(
                _run("dry-run", project, "--authority-receipt", authority, "--at", "2026-07-29T15:00:02Z"),
                0,
                "WOULD_APPLY",
            )
            if _snapshot(project) != before:
                raise AssertionError("dry-run wrote project bytes")
            _assert_common_proof(receipt, project, authority)
            if receipt.get("claim") is not None or receipt.get("rollback_manifest") is not None or receipt.get("state_last") is not None:
                raise AssertionError("dry-run invented claim/rollback/state-last proof")
            if receipt.get("preimage") != {"sha256": _sha_bytes(preimage), "bytes": len(preimage)}:
                raise AssertionError("dry-run preimage proof is wrong")
            preserved = receipt.get("preserved_phase_state", {})
            expected = _canonical_without_policy(json.loads(preimage))
            if preserved != {"pre_sha256": expected, "post_sha256": expected}:
                raise AssertionError("dry-run preservation proof is wrong")

        matrix.case("dry-run proves exact delta and has zero project writes", dry_run_exact_and_read_only)

        def preimage_mismatch_refuses() -> None:
            project, preimage = _project(sandbox, "preimage-mismatch")
            authority = _authority(project, preimage, digest="0" * 64, suffix="mismatch")
            before = _snapshot(project)
            receipt = _expect(
                _run("apply", project, "--authority-receipt", authority),
                4,
                "REFUSED",
                "MHD-MIGRATION-PREIMAGE-MISMATCH",
            )
            if _snapshot(project) != before or receipt.get("preimage") is not None:
                raise AssertionError("preimage refusal wrote bytes or invented proof")

        matrix.case("apply is exact-preimage-bound", preimage_mismatch_refuses)

        def active_claim_refuses_untouched() -> None:
            project, preimage = _project(sandbox, "active-claim")
            authority = _authority(project, preimage)
            claim = _claim(project, authority, preimage, pid=os.getpid())
            before = _snapshot(project)
            _expect(
                _run("apply", project, "--authority-receipt", authority),
                4,
                "REFUSED",
                "MHD-MIGRATION-ACTIVE-CLAIM",
            )
            if _snapshot(project) != before or not claim.is_file():
                raise AssertionError("active-claim refusal changed or deleted the claim")

        matrix.case("live exclusive claim blocks with no TTL/takeover", active_claim_refuses_untouched)

        def assignment_transaction_in_use_refuses() -> None:
            project, preimage = _project(sandbox, "assignment-in-use")
            authority = _authority(project, preimage)
            busy = project / "reviews" / ".harness" / "milestones" / "claims" / "transaction.lock"
            busy.parent.mkdir(parents=True, exist_ok=True)
            busy.write_text("synthetic active assignment transaction\n", encoding="utf-8")
            before = _snapshot(project)
            _expect(
                _run("apply", project, "--authority-receipt", authority),
                4,
                "REFUSED",
                "MHD-MIGRATION-IN-USE",
            )
            if _snapshot(project) != before:
                raise AssertionError("in-use refusal changed project bytes")

        matrix.case("live assignment/milestone transaction blocks migration", assignment_transaction_in_use_refuses)

        def apply_preserves_every_external_byte() -> None:
            project, preimage = _project(sandbox, "apply-clean")
            authority = _authority(project, preimage)
            external_before = _external_snapshot(project)
            receipt, apply_path, rollback_manifest = _apply(project, authority)
            postimage = (project / LEDGER).read_bytes()
            _assert_only_two_semantic_changes(preimage, postimage)
            if _external_snapshot(project) != external_before:
                raise AssertionError("apply changed an external project surface")
            _assert_common_proof(receipt, project, authority)
            if receipt.get("postimage") != {"sha256": _sha_bytes(postimage), "bytes": len(postimage)}:
                raise AssertionError("apply postimage proof is wrong")
            if receipt.get("claim", {}).get("path", "").endswith("transaction.lock"):
                raise AssertionError("apply receipt bound transient live claim")
            if receipt.get("rollback_manifest") != _binding(project, rollback_manifest):
                raise AssertionError("apply receipt does not bind rollback manifest")
            state_last = receipt.get("state_last")
            if state_last != {"atomic_replace": True, "dependencies_rechecked": True, "concurrent_hash_rechecked": True}:
                raise AssertionError("apply did not prove all state-last properties")
            if _sha(apply_path) != _sha_bytes(_json_bytes(receipt)):
                raise AssertionError("apply receipt hash is not reproducible")

        matrix.case("apply changes only contract/policy and preserves all external bytes", apply_preserves_every_external_byte)

        def active_milestone_state_and_consumed_f9_are_preserved() -> None:
            project, preimage = _active_project(sandbox, "active-milestone")
            authority = _authority(project, preimage, suffix="active")
            before_document = json.loads(preimage)
            before_handoffs = _handoff_snapshot(project)
            before_external = _external_snapshot(project)
            framework = before_document["milestone_framework"]
            if framework["milestones"]["M4"]["status"] != "in_progress":
                raise AssertionError("active fixture does not have M4 in progress")
            if not any(
                record["status"] == "consumed"
                for record in before_handoffs["records"].values()
            ):
                raise AssertionError("active fixture has no historical consumed F9")
            _apply(project, authority)
            postimage = (project / LEDGER).read_bytes()
            _assert_only_two_semantic_changes(preimage, postimage)
            after_framework = json.loads(postimage)["milestone_framework"]
            if after_framework["milestones"] != framework["milestones"]:
                raise AssertionError("migration changed active or historical milestone state")
            if after_framework["events"] != framework["events"]:
                raise AssertionError("migration changed active or historical events")
            if _handoff_snapshot(project) != before_handoffs:
                raise AssertionError("migration changed historical consumed F9 state/bytes")
            if _external_snapshot(project) != before_external:
                raise AssertionError("active-state migration changed an external byte")

        matrix.case(
            "active 1.0.0 milestone state and historical consumed F9 survive migration",
            active_milestone_state_and_consumed_f9_are_preserved,
        )

        def historical_ready_and_consumed_f9_are_byte_preserved() -> None:
            project, preimage = _project(sandbox, "historical-f9")
            authority = _authority(project, preimage, suffix="historical-f9")
            before = _handoff_snapshot(project)
            statuses = {record["status"] for record in before["records"].values()}
            if not {"ready", "consumed"}.issubset(statuses):
                raise AssertionError(f"historical fixture lacks ready/consumed states: {statuses}")
            _apply(project, authority)
            if _handoff_snapshot(project) != before:
                raise AssertionError("migration rewrote a historical ready/consumed F9 record or byte")

        matrix.case(
            "historical ready and consumed F9 records remain byte-exact",
            historical_ready_and_consumed_f9_are_byte_preserved,
        )

        def legacy_mode_and_boundary_survive_migration() -> None:
            project, preimage = _project(sandbox, "legacy-mode", legacy=True)
            authority = _authority(project, preimage, suffix="legacy")
            before = json.loads(preimage)["milestone_framework"]
            before_external = _external_snapshot(project)
            if before.get("mode") != "legacy" or not isinstance(before.get("migration_boundary"), dict):
                raise AssertionError("legacy fixture lacks a valid explicit migration boundary")
            _apply(project, authority)
            postimage = (project / LEDGER).read_bytes()
            _assert_only_two_semantic_changes(preimage, postimage)
            after = json.loads(postimage)["milestone_framework"]
            if after.get("mode") != "legacy" or after.get("migration_boundary") != before.get("migration_boundary"):
                raise AssertionError("derived-handoff migration changed legacy mode/boundary")
            if _external_snapshot(project) != before_external:
                raise AssertionError("legacy migration changed an external project byte")

        matrix.case(
            "valid legacy mode migrates policy without changing legacy boundary",
            legacy_mode_and_boundary_survive_migration,
        )

        def verify_is_read_only() -> None:
            project, preimage = _project(sandbox, "verify")
            authority = _authority(project, preimage)
            _, apply_path, _ = _apply(project, authority)
            before = _snapshot(project)
            receipt = _expect(
                _run("verify", project, "--authority-receipt", authority, "--apply-receipt", apply_path),
                0,
                "VERIFIED",
            )
            if _snapshot(project) != before or receipt.get("claim") is not None or receipt.get("state_last") is not None:
                raise AssertionError("verify wrote bytes or invented a claim/state-last proof")

        matrix.case("verify replays proof without project writes", verify_is_read_only)

        def idempotent_apply_writes_nothing() -> None:
            project, preimage = _project(sandbox, "idempotent")
            authority = _authority(project, preimage)
            original, _, _ = _apply(project, authority)
            before = _snapshot(project)
            repeated = _expect(_run("apply", project, "--authority-receipt", authority), 0, "ALREADY_APPLIED")
            if _snapshot(project) != before:
                raise AssertionError("ALREADY_APPLIED changed project bytes")
            for key in ("claim", "rollback_manifest", "state_last"):
                if repeated.get(key) != original.get(key):
                    raise AssertionError(f"ALREADY_APPLIED did not copy {key} proof")

        matrix.case("idempotent apply copies proof and acquires no new claim", idempotent_apply_writes_nothing)

        def tampered_receipt_refuses_read_only() -> None:
            project, preimage = _project(sandbox, "tampered-receipt")
            authority = _authority(project, preimage)
            _, apply_path, _ = _apply(project, authority)
            value = json.loads(apply_path.read_text(encoding="utf-8"))
            value["completed_at"] = "2026-07-29T15:59:59Z"
            _write_json(apply_path, value)
            before = _snapshot(project)
            _expect(
                _run("verify", project, "--authority-receipt", authority, "--apply-receipt", apply_path),
                4,
                "REFUSED",
                "MHD-MIGRATION-RECEIPT-TAMPERED",
            )
            if _snapshot(project) != before:
                raise AssertionError("tampered-receipt refusal changed bytes")

        matrix.case("tampered apply receipt fails closed without writes", tampered_receipt_refuses_read_only)

        def rollback_restores_exact_preimage() -> None:
            project, preimage = _project(sandbox, "rollback")
            authority = _authority(project, preimage)
            external_before = _external_snapshot(project)
            _, apply_path, manifest_path = _apply(project, authority)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if base64.b64decode(manifest.get("preimage_bytes_base64", ""), validate=True) != preimage:
                raise AssertionError("rollback manifest does not carry exact preimage bytes")
            receipt = _expect(
                _run(
                    "rollback", project, "--authority-receipt", authority,
                    "--apply-receipt", apply_path, "--rollback-manifest", manifest_path,
                    "--at", "2026-07-29T15:00:03Z",
                ),
                0,
                "ROLLED_BACK",
            )
            if (project / LEDGER).read_bytes() != preimage:
                raise AssertionError("rollback did not restore exact ledger bytes")
            if _external_snapshot(project) != external_before:
                raise AssertionError("rollback changed an external project surface")
            if receipt.get("restored_preimage") != {"sha256": _sha_bytes(preimage), "bytes": len(preimage)}:
                raise AssertionError("rollback receipt does not prove restored preimage")
            if receipt.get("claim", {}).get("path", "").endswith("transaction.lock"):
                raise AssertionError("rollback receipt bound transient live claim")

            rollback_path = apply_path.with_name("rollback.json")
            if not rollback_path.is_file() or json.loads(rollback_path.read_text(encoding="utf-8")) != receipt:
                raise AssertionError("committed rollback receipt is absent or differs from stdout")
            before_repeat = _snapshot(project)
            repeated = _expect(
                _run(
                    "rollback", project, "--authority-receipt", authority,
                    "--apply-receipt", apply_path, "--rollback-manifest", manifest_path,
                    "--at", "2026-07-29T15:00:04Z",
                ),
                0,
                "ALREADY_ROLLED_BACK",
            )
            if _snapshot(project) != before_repeat:
                raise AssertionError("ALREADY_ROLLED_BACK changed project bytes")
            copied = (
                "authority_receipt", "apply_receipt", "rollback_manifest", "claim",
                "current_applied_postimage", "restored_preimage", "external_surface_inventory",
            )
            for key in copied:
                if repeated.get(key) != receipt.get(key):
                    raise AssertionError(f"ALREADY_ROLLED_BACK did not copy {key} proof")
            if repeated.get("state_last") is not None:
                raise AssertionError("ALREADY_ROLLED_BACK invented a new state-last write")

        matrix.case(
            "rollback restores exact preimage and repeats with byte-idempotent proof",
            rollback_restores_exact_preimage,
        )

        def tampered_committed_rollback_receipt_never_idempotently_passes() -> None:
            project, preimage = _project(sandbox, "rollback-receipt-tamper")
            authority = _authority(project, preimage, suffix="rollback-receipt-tamper")
            _, apply_path, manifest_path = _apply(project, authority)
            _expect(
                _run(
                    "rollback", project, "--authority-receipt", authority,
                    "--apply-receipt", apply_path, "--rollback-manifest", manifest_path,
                    "--at", "2026-07-29T15:00:03Z",
                ),
                0,
                "ROLLED_BACK",
            )
            if (project / LEDGER).read_bytes() != preimage:
                raise AssertionError("tamper fixture did not begin from an exact successful rollback")
            rollback_path = apply_path.with_name("rollback.json")
            original = rollback_path.read_bytes()

            def mutate_binding(value: dict[str, Any], field: str) -> None:
                value[field]["sha256"] = "0" * 64

            variants: tuple[tuple[str, Callable[[dict[str, Any]], None]], ...] = (
                ("apply_receipt.sha256", lambda value: mutate_binding(value, "apply_receipt")),
                ("rollback_manifest.sha256", lambda value: mutate_binding(value, "rollback_manifest")),
                ("restored_preimage.sha256", lambda value: value["restored_preimage"].update({"sha256": "0" * 64})),
                (
                    "external_surface_inventory.pre.digest",
                    lambda value: value["external_surface_inventory"]["pre"].update({"digest": "0" * 64}),
                ),
                ("transaction_id", lambda value: value.update({"transaction_id": "tampered-transaction-id"})),
            )
            for index, (label, mutate) in enumerate(variants, 1):
                value = json.loads(original)
                mutate(value)
                _write_json(rollback_path, value)
                before = _snapshot(project)
                receipt = _expect(
                    _run(
                        "rollback", project, "--authority-receipt", authority,
                        "--apply-receipt", apply_path, "--rollback-manifest", manifest_path,
                        "--at", f"2026-07-29T15:00:{3 + index:02d}Z",
                    ),
                    4,
                    "REFUSED",
                    "MHD-MIGRATION-RECEIPT-TAMPERED",
                )
                if receipt.get("outcome") == "ALREADY_ROLLED_BACK":
                    raise AssertionError(f"tampered {label} was treated as idempotent rollback")
                if _snapshot(project) != before:
                    raise AssertionError(f"tampered {label} refusal changed project bytes")

        matrix.case(
            "tampered committed rollback proof never returns ALREADY_ROLLED_BACK",
            tampered_committed_rollback_receipt_never_idempotently_passes,
        )

        def rollback_refuses_changed_postimage() -> None:
            project, preimage = _project(sandbox, "rollback-mismatch")
            authority = _authority(project, preimage)
            _, apply_path, manifest_path = _apply(project, authority)
            ledger_path = project / LEDGER
            value = json.loads(ledger_path.read_text(encoding="utf-8"))
            value["terminal_phase_reached"] = not value["terminal_phase_reached"]
            _write_json(ledger_path, value)
            before = ledger_path.read_bytes()
            _expect(
                _run(
                    "rollback", project, "--authority-receipt", authority,
                    "--apply-receipt", apply_path, "--rollback-manifest", manifest_path,
                ),
                4,
                "REFUSED",
                "MHD-MIGRATION-ROLLBACK-STATE-MISMATCH",
            )
            if ledger_path.read_bytes() != before:
                raise AssertionError("rollback mismatch overwrote concurrent bytes")

        matrix.case("rollback refuses non-postimage current state", rollback_refuses_changed_postimage)

        def concurrency_hook_preserves_concurrent_state() -> None:
            project, preimage = _project(sandbox, "concurrent")
            authority = _authority(project, preimage)
            try:
                module = importlib.import_module("migrate_lab_iteration_derived_handoff")
            except ModuleNotFoundError as exc:
                raise AssertionError("dedicated v0.41 migration implementation is absent") from exc
            apply_migration = getattr(module, "apply_migration", None)
            error_type = getattr(module, "MigrationError", None)
            if not callable(apply_migration) or not isinstance(error_type, type):
                raise AssertionError("migration lacks apply_migration/MigrationError test seam")
            ledger_path = project / LEDGER

            def change_ledger() -> None:
                value = json.loads(ledger_path.read_text(encoding="utf-8"))
                value["terminal_round_id"] = "synthetic-concurrent-change"
                _write_json(ledger_path, value)

            try:
                apply_migration(
                    project,
                    authority,
                    at="2026-07-29T15:00:02Z",
                    _before_state_publish=change_ledger,
                )
            except error_type as exc:
                if getattr(exc, "code", None) != "MHD-MIGRATION-CONCURRENT-CHANGE":
                    raise AssertionError(f"wrong concurrency code: {getattr(exc, 'code', None)}") from exc
            else:
                raise AssertionError("concurrent ledger change was overwritten")
            if json.loads(ledger_path.read_text(encoding="utf-8")).get("terminal_round_id") != "synthetic-concurrent-change":
                raise AssertionError("migration did not preserve concurrent actor's bytes")

        matrix.case("state-last apply refuses deterministic concurrent change", concurrency_hook_preserves_concurrent_state)

        def interrupted_apply_recovers_exact_prepared_evidence() -> None:
            project, preimage = _project(sandbox, "interrupted-apply")
            authority = _authority(project, preimage, suffix="interrupted")
            external_before = _external_snapshot(project)
            try:
                module = importlib.import_module("migrate_lab_iteration_derived_handoff")
            except ModuleNotFoundError as exc:
                raise AssertionError("dedicated v0.41 migration implementation is absent") from exc
            apply_migration = getattr(module, "apply_migration", None)
            if not callable(apply_migration):
                raise AssertionError("migration lacks apply_migration interruption test seam")

            class SyntheticInterruption(BaseException):
                pass

            def interrupt_after_state_publish() -> None:
                raise SyntheticInterruption("synthetic crash after state-last replacement")

            try:
                apply_migration(
                    project,
                    authority,
                    at="2026-07-29T15:00:02Z",
                    _after_state_publish=interrupt_after_state_publish,
                )
            except SyntheticInterruption:
                pass
            else:
                raise AssertionError("post-state-publish interruption seam did not interrupt apply")

            postimage = (project / LEDGER).read_bytes()
            _assert_only_two_semantic_changes(preimage, postimage)
            if _external_snapshot(project) != external_before:
                raise AssertionError("interrupted state-last apply changed an external byte")

            live_claim_path = project / LANE / "transaction.lock"
            if not live_claim_path.is_file():
                raise AssertionError("interrupted state-last apply did not retain its live claim")
            live_claim = json.loads(live_claim_path.read_text(encoding="utf-8"))
            if live_claim.get("state") != "active" or live_claim.get("operation") != "apply":
                raise AssertionError("interrupted apply claim is not active/apply")
            transaction_id = live_claim.get("transaction_id")
            if not isinstance(transaction_id, str) or not transaction_id:
                raise AssertionError("interrupted apply claim lacks transaction_id")
            transaction_root = project / LANE / "transactions" / transaction_id
            final_apply = transaction_root / "apply.json"
            final_manifest = transaction_root / "rollback_manifest.json"
            if final_apply.exists() or final_manifest.exists():
                raise AssertionError("interruption seam ran after prepared evidence was committed")

            records = _json_records(transaction_root)
            _, prepared_receipt, prepared_receipt_bytes = _one_record(
                records,
                schema="co-author-harness/milestone-handoff-policy-migration-receipt/v1",
                operation="apply",
                outcome="APPLIED",
            )
            _, prepared_manifest, prepared_manifest_bytes = _one_record(
                records,
                schema="co-author-harness/milestone-handoff-policy-migration-rollback-manifest/v1",
            )
            _, prepared_claim, prepared_claim_bytes = _one_record(
                records,
                schema="co-author-harness/milestone-handoff-policy-migration-claim/v1",
                state="consumed",
                operation="apply",
            )
            _assert_common_proof(prepared_receipt, project, authority)
            if prepared_receipt.get("preimage") != {"sha256": _sha_bytes(preimage), "bytes": len(preimage)}:
                raise AssertionError("prepared receipt does not bind the exact preimage")
            if prepared_receipt.get("postimage") != {"sha256": _sha_bytes(postimage), "bytes": len(postimage)}:
                raise AssertionError("prepared receipt does not bind the published postimage")
            if base64.b64decode(prepared_manifest.get("preimage_bytes_base64", ""), validate=True) != preimage:
                raise AssertionError("prepared rollback manifest lacks exact preimage bytes")
            if prepared_receipt.get("rollback_manifest") != {
                "path": final_manifest.relative_to(project).as_posix(),
                "sha256": _sha_bytes(prepared_manifest_bytes),
            }:
                raise AssertionError("prepared receipt does not prebind final rollback manifest bytes")
            final_consumed_claim = transaction_root / "claim.consumed.json"
            if prepared_receipt.get("claim") != {
                "path": final_consumed_claim.relative_to(project).as_posix(),
                "sha256": _sha_bytes(prepared_claim_bytes),
            }:
                raise AssertionError("prepared receipt does not prebind final consumed-claim bytes")

            _expect(
                _run(
                    "recover", project, "--authority-receipt", authority,
                    "--acknowledgement", "inspected-migration-state-and-receipts",
                    "--at", "2026-07-29T15:00:03Z",
                ),
                0,
                "RECOVERED",
            )
            if live_claim_path.exists():
                raise AssertionError("postimage recovery left the live claim in place")
            recovered_path = transaction_root / "claim.recovered.json"
            if not recovered_path.is_file():
                raise AssertionError("postimage recovery did not archive recovered claim")
            recovered = json.loads(recovered_path.read_text(encoding="utf-8"))
            recovery = recovered.get("recovery", {})
            if recovered.get("state") != "recovered" or recovery.get("disposition") != "postimage_committed":
                raise AssertionError("postimage recovery recorded the wrong claim disposition")
            if recovery.get("observed_ledger_sha256") != _sha_bytes(postimage):
                raise AssertionError("postimage recovery did not bind observed ledger bytes")
            if final_apply.read_bytes() != prepared_receipt_bytes:
                raise AssertionError("recovery did not publish prepared apply bytes exactly")
            if final_manifest.read_bytes() != prepared_manifest_bytes:
                raise AssertionError("recovery did not publish prepared rollback-manifest bytes exactly")
            if final_consumed_claim.read_bytes() != prepared_claim_bytes:
                raise AssertionError("recovery did not publish prebound consumed-claim bytes exactly")
            before_verify = _snapshot(project)
            _expect(
                _run("verify", project, "--authority-receipt", authority, "--apply-receipt", final_apply),
                0,
                "VERIFIED",
            )
            if _snapshot(project) != before_verify:
                raise AssertionError("verification after recovered apply wrote project bytes")

        matrix.case(
            "interrupted state-last apply recovers exact prepared postimage evidence",
            interrupted_apply_recovers_exact_prepared_evidence,
        )

        def tampered_prepared_evidence_blocks_interrupted_recovery() -> None:
            project, preimage = _project(sandbox, "interrupted-prepared-tamper")
            authority = _authority(project, preimage, suffix="interrupted-prepared-tamper")
            live_claim, transaction_root = _interrupt_apply_after_state_publish(project, authority)
            postimage = (project / LEDGER).read_bytes()
            _assert_only_two_semantic_changes(preimage, postimage)
            records = _json_records(transaction_root)
            prepared_manifest_path, prepared_manifest, _ = _one_record(
                records,
                schema="co-author-harness/milestone-handoff-policy-migration-rollback-manifest/v1",
            )
            prepared_manifest["created_at"] = "2026-07-29T15:59:59Z"
            _write_json(prepared_manifest_path, prepared_manifest)
            live_claim_bytes = live_claim.read_bytes()
            final_paths = (
                transaction_root / "apply.json",
                transaction_root / "rollback_manifest.json",
                transaction_root / "claim.consumed.json",
                transaction_root / "claim.recovered.json",
            )
            if any(path.exists() for path in final_paths):
                raise AssertionError("tamper fixture unexpectedly began with final evidence")
            before_recovery = _snapshot(project)
            receipt = _expect(
                _run(
                    "recover", project, "--authority-receipt", authority,
                    "--acknowledgement", "inspected-migration-state-and-receipts",
                    "--at", "2026-07-29T15:00:03Z",
                ),
                4,
                "REFUSED",
            )
            permitted_codes = {
                "MHD-MIGRATION-RECEIPT-TAMPERED",
                "MHD-MIGRATION-RECOVERY-STATE-MISMATCH",
            }
            observed_codes = _codes(receipt)
            if not observed_codes.intersection(permitted_codes):
                raise AssertionError(
                    f"tampered prepared recovery emitted wrong codes: {sorted(observed_codes)}"
                )
            if _snapshot(project) != before_recovery:
                raise AssertionError("tampered prepared-evidence recovery was not read-only")
            if not live_claim.is_file() or live_claim.read_bytes() != live_claim_bytes:
                raise AssertionError("tampered prepared-evidence recovery removed/changed live claim")
            if any(path.exists() for path in final_paths):
                raise AssertionError("tampered prepared-evidence recovery published final evidence")

        matrix.case(
            "tampered prepared evidence blocks interrupted recovery without releasing claim",
            tampered_prepared_evidence_blocks_interrupted_recovery,
        )

        def interrupted_rollback_recovers_exact_prepared_evidence() -> None:
            project, preimage = _project(sandbox, "interrupted-rollback")
            authority = _authority(project, preimage, suffix="interrupted-rollback")
            external_before = _external_snapshot(project)
            _, apply_path, manifest_path = _apply(project, authority)
            postimage = (project / LEDGER).read_bytes()
            live_claim, transaction_root = _interrupt_rollback_after_state_publish(
                project, authority, apply_path, manifest_path
            )
            if (project / LEDGER).read_bytes() != preimage:
                raise AssertionError("interrupted rollback did not restore exact preimage before crash")
            if _external_snapshot(project) != external_before:
                raise AssertionError("interrupted rollback changed an external project byte")

            records = _json_records(transaction_root)
            prepared_receipt_path, prepared_receipt, prepared_receipt_bytes = _one_record(
                records,
                schema="co-author-harness/milestone-handoff-policy-migration-rollback-receipt/v1",
                operation="rollback",
                outcome="ROLLED_BACK",
            )
            prepared_claim_path, prepared_claim, prepared_claim_bytes = _one_record(
                records,
                schema="co-author-harness/milestone-handoff-policy-migration-claim/v1",
                state="consumed",
                operation="rollback",
            )
            if prepared_receipt_path.parent.name != ".prepared" or prepared_claim_path.parent.name != ".prepared":
                raise AssertionError("interrupted rollback evidence is not confined to prepared staging")
            if prepared_receipt.get("current_applied_postimage") != {
                "sha256": _sha_bytes(postimage), "bytes": len(postimage)
            }:
                raise AssertionError("prepared rollback receipt does not bind exact applied postimage")
            if prepared_receipt.get("restored_preimage") != {
                "sha256": _sha_bytes(preimage), "bytes": len(preimage)
            }:
                raise AssertionError("prepared rollback receipt does not bind exact restored preimage")
            if prepared_receipt.get("apply_receipt") != _binding(project, apply_path):
                raise AssertionError("prepared rollback receipt does not bind exact apply receipt")
            if prepared_receipt.get("rollback_manifest") != _binding(project, manifest_path):
                raise AssertionError("prepared rollback receipt does not bind exact manifest")
            final_claim = project / prepared_receipt["claim"]["path"]
            final_rollback = apply_path.with_name("rollback.json")
            recovered_path = transaction_root / "claim.recovered.json"
            if prepared_receipt.get("claim") != {
                "path": final_claim.relative_to(project).as_posix(),
                "sha256": _sha_bytes(prepared_claim_bytes),
            }:
                raise AssertionError("prepared rollback receipt does not bind exact consumed claim")
            if any(path.exists() for path in (final_claim, final_rollback, recovered_path)):
                raise AssertionError("interrupted rollback published final evidence before recovery")

            recovered = _expect(
                _run(
                    "recover", project, "--authority-receipt", authority,
                    "--acknowledgement", "inspected-migration-state-and-receipts",
                    "--at", "2026-07-29T15:00:04Z",
                ),
                0,
                "RECOVERED",
            )
            if recovered.get("disposition") != "rollback_restored":
                raise AssertionError(f"wrong interrupted rollback disposition: {recovered}")
            if live_claim.exists() or not recovered_path.is_file():
                raise AssertionError("valid rollback recovery did not archive/release the live claim")
            archived = json.loads(recovered_path.read_text(encoding="utf-8"))
            recovery = archived.get("recovery", {})
            if (
                archived.get("state") != "recovered"
                or recovery.get("disposition") != "rollback_restored"
                or recovery.get("observed_ledger_sha256") != _sha_bytes(preimage)
            ):
                raise AssertionError("archived rollback recovery claim does not bind restored state")
            if final_claim.read_bytes() != prepared_claim_bytes:
                raise AssertionError("rollback recovery did not publish prepared claim bytes exactly")
            if final_rollback.read_bytes() != prepared_receipt_bytes:
                raise AssertionError("rollback recovery did not publish prepared receipt bytes exactly")
            if (project / LEDGER).read_bytes() != preimage or _external_snapshot(project) != external_before:
                raise AssertionError("valid rollback recovery changed restored/external bytes")

        matrix.case(
            "interrupted rollback recovery publishes exact prepared evidence and releases claim",
            interrupted_rollback_recovers_exact_prepared_evidence,
        )

        def tampered_prepared_rollback_evidence_blocks_recovery() -> None:
            project, preimage = _project(sandbox, "interrupted-rollback-tamper")
            authority = _authority(project, preimage, suffix="interrupted-rollback-tamper")
            _, apply_path, manifest_path = _apply(project, authority)
            live_claim, transaction_root = _interrupt_rollback_after_state_publish(
                project, authority, apply_path, manifest_path
            )
            if (project / LEDGER).read_bytes() != preimage:
                raise AssertionError("tampered rollback fixture did not restore exact preimage")
            records = _json_records(transaction_root)
            prepared_receipt_path, _, prepared_receipt_bytes = _one_record(
                records,
                schema="co-author-harness/milestone-handoff-policy-migration-rollback-receipt/v1",
                operation="rollback",
                outcome="ROLLED_BACK",
            )
            prepared_claim_path, _, prepared_claim_bytes = _one_record(
                records,
                schema="co-author-harness/milestone-handoff-policy-migration-claim/v1",
                state="consumed",
                operation="rollback",
            )
            original_live_claim = live_claim.read_bytes()
            prepared_receipt = json.loads(prepared_receipt_bytes)
            final_claim = project / prepared_receipt["claim"]["path"]
            final_rollback = apply_path.with_name("rollback.json")
            recovered_path = transaction_root / "claim.recovered.json"
            final_paths = (final_claim, final_rollback, recovered_path)

            def tamper_claim() -> None:
                value = json.loads(prepared_claim_bytes)
                value["completed_at"] = "2026-07-29T15:59:59Z"
                _write_json(prepared_claim_path, value)

            def tamper_receipt_binding() -> None:
                value = json.loads(prepared_receipt_bytes)
                value["apply_receipt"]["sha256"] = "0" * 64
                _write_json(prepared_receipt_path, value)

            variants = (
                ("prepared rollback claim", tamper_claim),
                ("prepared rollback receipt binding", tamper_receipt_binding),
            )
            for index, (label, tamper) in enumerate(variants, 1):
                prepared_claim_path.write_bytes(prepared_claim_bytes)
                prepared_receipt_path.write_bytes(prepared_receipt_bytes)
                tamper()
                if any(path.exists() for path in final_paths):
                    raise AssertionError(f"{label} fixture unexpectedly began with final evidence")
                before_recovery = _snapshot(project)
                refused = _expect(
                    _run(
                        "recover", project, "--authority-receipt", authority,
                        "--acknowledgement", "inspected-migration-state-and-receipts",
                        "--at", f"2026-07-29T15:00:{4 + index:02d}Z",
                    ),
                    4,
                    "REFUSED",
                )
                permitted_codes = {
                    "MHD-MIGRATION-RECEIPT-TAMPERED",
                    "MHD-MIGRATION-RECOVERY-STATE-MISMATCH",
                }
                observed_codes = _codes(refused)
                if not observed_codes.intersection(permitted_codes):
                    raise AssertionError(f"{label} emitted wrong codes: {sorted(observed_codes)}")
                if _snapshot(project) != before_recovery:
                    raise AssertionError(f"{label} recovery refusal changed project bytes")
                if not live_claim.is_file() or live_claim.read_bytes() != original_live_claim:
                    raise AssertionError(f"{label} recovery refusal changed/removed live claim")
                if any(path.exists() for path in final_paths):
                    raise AssertionError(f"{label} recovery refusal published final evidence")

        matrix.case(
            "tampered prepared rollback claim or receipt binding blocks recovery read-only",
            tampered_prepared_rollback_evidence_blocks_recovery,
        )

        def dead_owner_preimage_recovery_is_exact() -> None:
            project, preimage = _project(sandbox, "recovery-dead-preimage")
            authority = _authority(project, preimage, suffix="dead-preimage")
            transaction_id = "recovery-dead-preimage"
            live_claim = _claim(
                project, authority, preimage, pid=2147483647, transaction_id=transaction_id
            )
            external_before = _external_snapshot(project)
            _expect(
                _run(
                    "recover", project, "--authority-receipt", authority,
                    "--acknowledgement", "inspected-migration-state-and-receipts",
                    "--at", "2026-07-29T15:00:03Z",
                ),
                0,
                "RECOVERED",
            )
            if live_claim.exists() or (project / LEDGER).read_bytes() != preimage:
                raise AssertionError("dead-owner preimage recovery changed authority or retained claim")
            if _external_snapshot(project) != external_before:
                raise AssertionError("dead-owner preimage recovery changed an external byte")
            recovered_path = project / LANE / "transactions" / transaction_id / "claim.recovered.json"
            if not recovered_path.is_file():
                raise AssertionError("dead-owner recovery did not archive the exact claim")
            recovered = json.loads(recovered_path.read_text(encoding="utf-8"))
            recovery = recovered.get("recovery", {})
            expected = {
                "acknowledgement": "inspected-migration-state-and-receipts",
                "recovered_at": "2026-07-29T15:00:03Z",
                "observed_ledger_sha256": _sha_bytes(preimage),
                "disposition": "preimage_unchanged",
            }
            if recovered.get("state") != "recovered" or recovery != expected:
                raise AssertionError(f"wrong dead-owner recovery proof: {recovered}")

        matrix.case(
            "dead-owner recovery archives exact preimage-unchanged disposition",
            dead_owner_preimage_recovery_is_exact,
        )

        def recovery_requires_exact_ack_and_keeps_live_claim() -> None:
            project, preimage = _project(sandbox, "recovery-live")
            authority = _authority(project, preimage)
            claim = _claim(project, authority, preimage, pid=os.getpid(), transaction_id="recovery-live")
            before = _snapshot(project)
            _expect(
                _run(
                    "recover", project, "--authority-receipt", authority,
                    "--acknowledgement", "wrong-acknowledgement",
                ),
                4,
                "REFUSED",
                "MHD-MIGRATION-RECOVERY-ACK",
            )
            if _snapshot(project) != before or not claim.is_file():
                raise AssertionError("failed recovery changed/deleted live claim")

        matrix.case("claim recovery requires exact acknowledgement", recovery_requires_exact_ack_and_keeps_live_claim)

    return matrix.finish()


if __name__ == "__main__":
    raise SystemExit(main())
