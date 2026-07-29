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
    template = sandbox / ".valid-v1-template"
    if not template.exists():
        template.mkdir()
        template_ledger = fixture._materialize_native_project(template, include_scholarly=True)
        template_ledger["contract_version"] = "1.0.0"
        template_ledger.pop("handoff_policy", None)
        _write_json(template / LEDGER, fixture._phase_document(template_ledger))
        _write_json(template / "reviews" / "assignment_contract.json", {"status": "resolved"})
        _write_json(template / "reviews" / "promotion_receipt.json", {"status": "not_promoted"})
        protected = template / "protected" / "governed.bin"
        protected.parent.mkdir(parents=True)
        protected.write_bytes(b"synthetic protected bytes\x00\xff")
        final = template / "manuscript" / "final-deliverable.md"
        final.parent.mkdir(parents=True, exist_ok=True)
        final.write_text("Synthetic final deliverable.\n", encoding="utf-8")

    project = sandbox / name
    shutil.copytree(template, project)
    ledger_path = project / LEDGER
    if legacy:
        document = json.loads(ledger_path.read_text(encoding="utf-8"))
        document["milestone_framework"]["mode"] = "legacy"
        _write_json(ledger_path, document)
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

        matrix.case("rollback restores exact preimage and preserves external bytes", rollback_restores_exact_preimage)

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
