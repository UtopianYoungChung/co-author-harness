#!/usr/bin/env python3
"""Adversarial receipt-transaction and scoped-writer regressions."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "assignment_process_gate.py"
PREFLIGHT = ROOT / "scripts" / "assignment_dispatch_preflight.py"
WRITER = ROOT / "scripts" / "assignment_writer_commit.py"
INVALIDATE = ROOT / "scripts" / "assignment_receipt_invalidate.py"
RECOVER = ROOT / "scripts" / "assignment_receipt_recover.py"
TRANSACTION = ROOT / "scripts" / "assignment_receipt_transaction.py"
PROFILE = ROOT / "references" / "policies" / "course_essay_milestones.v1.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(project: Path) -> dict[str, bytes]:
    return {
        path.relative_to(project).as_posix(): path.read_bytes()
        for path in project.rglob("*")
        if path.is_file()
    }


def create_project(base: Path, name: str) -> tuple[Path, Path]:
    project = base / name
    reviews = project / "reviews"
    reviews.mkdir(parents=True)
    source = project / "assignment.txt"
    source.write_text("synthetic assignment\n", encoding="utf-8")
    contract = {
        "contract_version": "1.0.0",
        "status": "resolved",
        "profile_id": "course-essay-four-milestones-v1",
        "profile_path": "references/policies/course_essay_milestones.v1.json",
        "profile_sha256": sha256(PROFILE),
        "assignment_source": {
            "path": "assignment.txt",
            "sha256": sha256(source),
            "authority": "instructor",
        },
        "assigned_sequence": ["M1", "M2", "M3", "M4", "FINAL"],
        "framework_mapping": {
            "M1": "M1", "M2": "M2", "M3": "M3", "M4": "M4", "FINAL": "M5",
        },
        "professor_copy_policy": "author_controlled_unless_explicitly_requested",
    }
    (reviews / "assignment_contract.json").write_text(
        json.dumps(contract, indent=2) + "\n", encoding="utf-8"
    )
    phase = {
        "milestone_framework": {
            "mode": "native",
            "primary_lineage_id": "live",
            "milestones": {
                key: {"status": "not_started"}
                for key in ("M1", "M2", "M3", "M4", "M5")
            },
        }
    }
    (reviews / "phase_state.json").write_text(
        json.dumps(phase, indent=2) + "\n", encoding="utf-8"
    )
    ready = (
        reviews / ".harness" / "assignment" / "ready"
        / f"gate_receipt_M1_{name}.json"
    )
    return project, ready


def emit(project: Path, ready: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable, str(GATE), "--project-root", str(project),
            "--stage", "draft", "--target-milestone", "M1",
            "--emit-receipt", str(ready),
        ],
        text=True, encoding="utf-8", errors="replace", capture_output=True, check=False,
    )


def reserve_command(project: Path, ready: Path) -> list[str]:
    return [
        sys.executable, str(PREFLIGHT), "--project-root", str(project),
        "--receipt", str(ready), "--consumer", "planner",
        "--expected-target", "M1", "--write-path", "research_notes/project_memo.md",
    ]


def reserve(project: Path, ready: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        reserve_command(project, ready), text=True, encoding="utf-8", errors="replace", capture_output=True, check=False
    )


def write_plan(
    project: Path,
    record: dict,
    *,
    content: bytes = b"project memo\n",
    role: str = "generator",
    target_path: str = "research_notes/project_memo.md",
    reservation_id: str | None = None,
) -> Path:
    staged_dir = (
        project / "reviews" / ".harness" / "assignment" / "staged"
        / record["receipt_id"]
    )
    staged_dir.mkdir(parents=True, exist_ok=True)
    staged = staged_dir / "project_memo.md"
    staged.write_bytes(content)
    plan = {
        "schema_version": "1.0.0",
        "receipt_id": record["receipt_id"],
        "reservation_id": reservation_id or record["reservation_id"],
        "target_milestone": "M1",
        "role": role,
        "writes": [{
            "staged_path": staged.relative_to(project).as_posix(),
            "target_path": target_path,
            "sha256": hashlib.sha256(content).hexdigest(),
        }],
    }
    plan_path = staged_dir / "write_plan.json"
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return plan_path


def write_plan_rows(
    project: Path,
    record: dict,
    rows: list[tuple[str, str, bytes]],
) -> Path:
    """Build a receipt-bound plan with distinct staged files for each target."""
    staged_dir = (
        project / "reviews" / ".harness" / "assignment" / "staged"
        / record["receipt_id"]
    )
    staged_dir.mkdir(parents=True, exist_ok=True)
    writes = []
    for staged_name, target_path, content in rows:
        staged = staged_dir / staged_name
        staged.write_bytes(content)
        writes.append({
            "staged_path": staged.relative_to(project).as_posix(),
            "target_path": target_path,
            "sha256": hashlib.sha256(content).hexdigest(),
        })
    plan = {
        "schema_version": "1.0.0",
        "receipt_id": record["receipt_id"],
        "reservation_id": record["reservation_id"],
        "target_milestone": record["target_milestone"],
        "role": record["authorized_role"],
        "writes": writes,
    }
    plan_path = staged_dir / "write_plan.json"
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return plan_path


def reserve_paths(
    project: Path, ready: Path, *write_paths: str
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable, str(PREFLIGHT), "--project-root", str(project),
        "--receipt", str(ready), "--consumer", "planner",
        "--expected-target", "M1",
    ]
    for write_path in write_paths:
        command.extend(("--write-path", write_path))
    return subprocess.run(command, text=True, encoding="utf-8", errors="replace", capture_output=True, check=False)


def commit_command(project: Path, reserved: Path, plan: Path) -> list[str]:
    return [
        sys.executable, str(WRITER), "--project-root", str(project),
        "--receipt", str(reserved), "--plan", str(plan),
    ]


def commit(project: Path, reserved: Path, plan: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        commit_command(project, reserved, plan),
        text=True, encoding="utf-8", errors="replace", capture_output=True, check=False,
    )


def receipt_paths(ready: Path) -> tuple[Path, Path, Path]:
    root = ready.parent.parent
    return (
        root / "reserved" / ready.name,
        root / "consumed" / ready.name,
        root / "invalidated" / ready.name,
    )


def emitted_project(base: Path, name: str) -> tuple[Path, Path, dict]:
    project, ready = create_project(base, name)
    result = emit(project, ready)
    assert result.returncode == 0, result.stdout + result.stderr
    record = json.loads(ready.read_text(encoding="utf-8"))
    assert record["schema_version"] == "2.1.0"
    assert record["authorized_role"] == "generator"
    assert record["primary_deliverable_path"] == "research_notes/project_memo.md"
    assert record["authorized_paths"] == [
        "research_notes/project_memo.md", "manuscript/revision_log.md"
    ]
    assert "status" not in record
    return project, ready, record


def forged_receipt_authorization_is_refused(base: Path) -> None:
    project, ready, record = emitted_project(base, "forged-authority")
    record["authorized_paths"].append("admin/forged.md")
    ready.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    reserved_result = reserve(project, ready)
    if reserved_result.returncode != 0:
        return
    reserved, _, _ = receipt_paths(ready)
    forged_plan = write_plan_rows(project, record, [
        ("memo.md", "research_notes/project_memo.md", b"memo\n"),
        ("forged.md", "admin/forged.md", b"forged\n"),
    ])
    committed = commit(project, reserved, forged_plan)
    assert committed.returncode == 4, (
        "forged receipt authorization reached publication\n"
        + committed.stdout + committed.stderr
    )
    assert not (project / "admin" / "forged.md").exists()


def copied_consumed_receipt_cannot_replay(base: Path) -> None:
    project, ready, record = emitted_project(base, "copied-consumed")
    assert reserve(project, ready).returncode == 0
    reserved, consumed, _ = receipt_paths(ready)
    first_plan = write_plan(project, record, content=b"first\n")
    first = commit(project, reserved, first_plan)
    assert first.returncode == 0, first.stdout + first.stderr
    published = project / "research_notes" / "project_memo.md"
    assert published.read_bytes() == b"first\n"

    # Directory state must not be replayable by restoring immutable receipt bytes.
    shutil.copy2(consumed, reserved)
    replay_plan = write_plan(project, record, content=b"replayed\n")
    replay = commit(project, reserved, replay_plan)
    assert replay.returncode == 4, (
        "copied consumed receipt replayed from canonical reserved directory\n"
        + replay.stdout + replay.stderr
    )
    assert published.read_bytes() == b"first\n"


def distinct_receipts_cannot_overwrite_same_snapshot(base: Path) -> None:
    project, first_ready, first_record = emitted_project(base, "dual-receipt")
    second_ready = first_ready.with_name("gate_receipt_M1_dual-receipt-second.json")
    second_emitted = emit(project, second_ready)
    assert second_emitted.returncode == 0, second_emitted.stdout + second_emitted.stderr
    second_record = json.loads(second_ready.read_text(encoding="utf-8"))
    assert reserve(project, first_ready).returncode == 0
    second_reserve = reserve(project, second_ready)
    assert second_reserve.returncode == 4, second_reserve.stdout + second_reserve.stderr
    assert "APG-TARGET-LEASED" in second_reserve.stdout
    first_reserved, _, _ = receipt_paths(first_ready)
    first_plan = write_plan(project, first_record, content=b"first receipt\n")
    first_commit = commit(project, first_reserved, first_plan)
    assert first_commit.returncode == 0, first_commit.stdout + first_commit.stderr
    assert (project / "research_notes" / "project_memo.md").read_bytes() == b"first receipt\n"


def reservation_scope_cannot_expand_at_commit(base: Path) -> None:
    project, ready, record = emitted_project(base, "scope-expansion")
    assert reserve_paths(project, ready, "research_notes/project_memo.md").returncode == 0
    reserved, _, _ = receipt_paths(ready)
    expanded_plan = write_plan_rows(project, record, [
        ("memo.md", "research_notes/project_memo.md", b"memo\n"),
        ("revision.md", "manuscript/revision_log.md", b"revision\n"),
    ])
    expanded = commit(project, reserved, expanded_plan)
    assert expanded.returncode == 4, (
        "commit expanded beyond the paths reserved at dispatch\n"
        + expanded.stdout + expanded.stderr
    )
    assert not (project / "manuscript" / "revision_log.md").exists()


def append_only_output_cannot_be_overwritten(base: Path) -> None:
    project, ready, record = emitted_project(base, "append-overwrite")
    revision_log = project / "manuscript" / "revision_log.md"
    revision_log.parent.mkdir(parents=True, exist_ok=True)
    revision_log.write_bytes(b"existing entry\n")
    reserved_result = reserve_paths(
        project,
        ready,
        "research_notes/project_memo.md",
        "manuscript/revision_log.md",
    )
    assert reserved_result.returncode == 0, reserved_result.stdout + reserved_result.stderr
    reserved, _, _ = receipt_paths(ready)
    overwrite_plan = write_plan_rows(project, record, [
        ("memo.md", "research_notes/project_memo.md", b"memo\n"),
        ("revision.md", "manuscript/revision_log.md", b"replacement\n"),
    ])
    overwritten = commit(project, reserved, overwrite_plan)
    assert overwritten.returncode == 4, (
        "append-only output accepted replacement publication\n"
        + overwritten.stdout + overwritten.stderr
    )
    assert revision_log.read_bytes() == b"existing entry\n"


def failure_after_first_publish_is_not_partial(base: Path) -> None:
    project, ready, record = emitted_project(base, "partial-publish")
    assert reserve_paths(
        project,
        ready,
        "research_notes/project_memo.md",
        "manuscript/revision_log.md",
    ).returncode == 0
    reserved, consumed, _ = receipt_paths(ready)
    plan = write_plan_rows(project, record, [
        ("memo.md", "research_notes/project_memo.md", b"memo\n"),
        ("revision.md", "manuscript/revision_log.md", b"revision\n"),
    ])
    spec = importlib.util.spec_from_file_location(
        "assignment_receipt_transaction_partial_publish", TRANSACTION
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    real_replace = module.os.replace
    second_target = (project / "manuscript" / "revision_log.md").resolve()

    def fail_second_target(source: Path, target: Path) -> None:
        if Path(target).resolve() == second_target:
            raise OSError("injected failure on second target publication")
        real_replace(source, target)

    module.os.replace = fail_second_target
    try:
        try:
            module.commit_receipt(project, reserved, plan)
        except module.ReceiptTransactionError as exc:
            assert exc.code == "APG-WRITE-PUBLISH-FAILED"
        else:
            raise AssertionError("second-target publication failpoint did not fail")
    finally:
        module.os.replace = real_replace

    primary_exists = (project / "research_notes" / "project_memo.md").exists()
    revision_exists = (project / "manuscript" / "revision_log.md").exists()
    assert primary_exists == revision_exists, (
        "publication failure left a partially committed target set: "
        f"primary={primary_exists} revision_log={revision_exists} "
        f"consumed={consumed.exists()}"
    )


def main() -> int:
    for required in (WRITER, INVALIDATE, RECOVER, TRANSACTION):
        assert required.is_file(), f"missing WP2 implementation: {required}"

    with tempfile.TemporaryDirectory() as temp:
        base = Path(temp)

        # One concurrent READY->RESERVED transition wins.
        project, ready, record = emitted_project(base, "race-reserve")
        processes = [
            subprocess.Popen(reserve_command(project, ready), text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            for _ in range(2)
        ]
        outcomes = [process.communicate() + (process.returncode,) for process in processes]
        assert sorted(outcome[2] for outcome in outcomes) == [0, 4], outcomes
        reserved, consumed, invalidated = receipt_paths(ready)
        assert not ready.exists() and reserved.is_file()
        assert any(
            ("APG-RECEIPT-RESERVED" in outcome[0] or "APG-RECEIPT-IN-USE" in outcome[0])
            for outcome in outcomes if outcome[2] == 4
        )

        # Concurrent same-basename emission is exclusive and never overwrites.
        p, same_ready = create_project(base, "race-emit")
        emitters = [
            subprocess.Popen(
                [sys.executable, str(GATE), "--project-root", str(p),
                 "--stage", "draft", "--target-milestone", "M1",
                 "--emit-receipt", str(same_ready)],
                text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            for _ in range(2)
        ]
        emitted = [process.communicate() + (process.returncode,) for process in emitters]
        assert sorted(item[2] for item in emitted) == [0, 4], emitted
        json.loads(same_ready.read_text(encoding="utf-8"))

        # Fresh reserved receipt commits exactly the authorized primary deliverable.
        plan = write_plan(project, record)
        committed = commit(project, reserved, plan)
        assert committed.returncode == 0, committed.stdout + committed.stderr
        assert not reserved.exists() and consumed.is_file()
        assert (project / "research_notes" / "project_memo.md").read_bytes() == b"project memo\n"
        result_sidecar = consumed.with_suffix(".result.json")
        assert result_sidecar.is_file()

        # Replay is refused and cannot alter final bytes.
        before_replay = snapshot(project)
        replay = commit(project, reserved, plan)
        assert replay.returncode == 4
        assert "APG-RECEIPT-CONSUMED" in replay.stdout
        assert snapshot(project) == before_replay

        # Wrong role, forged reservation token, and wrong path fail before consumption.
        for suffix, kwargs, code in (
            ("role", {"role": "planner"}, "APG-RECEIPT-ROLE-MISMATCH"),
            ("token", {"reservation_id": "00000000-0000-0000-0000-000000000000"}, "APG-RECEIPT-RESERVATION-MISMATCH"),
            ("path", {"target_path": "manuscript/main.md"}, "APG-RECEIPT-PATH-MISMATCH"),
            ("escape", {"target_path": "../outside.md"}, "APG-RECEIPT-PATH-INVALID"),
        ):
            p, r, rec = emitted_project(base, f"wrong-{suffix}")
            assert reserve(p, r).returncode == 0
            rs, _, _ = receipt_paths(r)
            bad_plan = write_plan(p, rec, **kwargs)
            before = snapshot(p)
            blocked = commit(p, rs, bad_plan)
            assert blocked.returncode == 4, blocked.stdout + blocked.stderr
            assert code in blocked.stdout
            assert snapshot(p) == before
            assert rs.is_file()

        # Copied reservation outside the reserved directory is never authority.
        p, r, rec = emitted_project(base, "copied")
        assert reserve(p, r).returncode == 0
        rs, _, _ = receipt_paths(r)
        copied = p / rs.name
        copied.write_bytes(rs.read_bytes())
        copied_plan = write_plan(p, rec)
        blocked_copy = commit(p, copied, copied_plan)
        assert blocked_copy.returncode == 4
        assert "APG-RECEIPT-PATH-INVALID" in blocked_copy.stdout

        # Hash drift after reserve blocks consumption.
        p, r, rec = emitted_project(base, "stale")
        assert reserve(p, r).returncode == 0
        rs, _, _ = receipt_paths(r)
        stale_plan = write_plan(p, rec)
        phase = p / "reviews" / "phase_state.json"
        phase.write_bytes(phase.read_bytes() + b" ")
        stale = commit(p, rs, stale_plan)
        assert stale.returncode == 4
        assert "APG-RECEIPT-STALE" in stale.stdout
        assert rs.is_file()

        # Concurrent consume vs invalidate has exactly one winner.
        p, r, rec = emitted_project(base, "race-invalidate")
        assert reserve(p, r).returncode == 0
        rs, cs, iv = receipt_paths(r)
        race_plan = write_plan(p, rec)
        commit_process = subprocess.Popen(commit_command(p, rs, race_plan), text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        invalidate_process = subprocess.Popen(
            [sys.executable, str(INVALIDATE), "--project-root", str(p), "--receipt", str(rs)],
            text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        race = [
            commit_process.communicate() + (commit_process.returncode,),
            invalidate_process.communicate() + (invalidate_process.returncode,),
        ]
        assert sorted(item[2] for item in race) == [0, 4], race
        assert cs.is_file() ^ iv.is_file()

        # Two concurrent commits cannot publish twice.
        p, r, rec = emitted_project(base, "race-consume")
        assert reserve(p, r).returncode == 0
        rs, cs, _ = receipt_paths(r)
        race_plan = write_plan(p, rec)
        consumers = [
            subprocess.Popen(commit_command(p, rs, race_plan), text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            for _ in range(2)
        ]
        outcomes = [process.communicate() + (process.returncode,) for process in consumers]
        assert sorted(item[2] for item in outcomes) == [0, 4], outcomes
        assert cs.is_file()

        # An interrupted publication rolls back and remains recoverable under
        # the same exact reservation and write plan; it never creates a
        # terminal consumed receipt with missing output.
        p, r, rec = emitted_project(base, "crash")
        assert reserve(p, r).returncode == 0
        rs, cs, _ = receipt_paths(r)
        crash_plan = write_plan(p, rec)
        spec = importlib.util.spec_from_file_location("assignment_receipt_transaction", TRANSACTION)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        try:
            module.commit_receipt(p, rs, crash_plan, fail_after_consume=True)
        except module.ReceiptTransactionError as exc:
            assert exc.code == "APG-WRITE-PUBLISH-FAILED"
        else:
            raise AssertionError("crash failpoint did not fail")
        assert rs.is_file() and not cs.exists()
        assert not (p / "research_notes" / "project_memo.md").exists()
        after_crash = commit(p, rs, crash_plan)
        assert after_crash.returncode == 0, after_crash.stdout + after_crash.stderr
        assert cs.is_file() and not rs.exists()
        assert (p / "research_notes" / "project_memo.md").is_file()

        # A hard interruption after one visible publication leaves a journal,
        # and the exact plan deterministically resumes the pending target.
        p, r, rec = emitted_project(base, "hard-crash-resume")
        assert reserve_paths(
            p, r, "research_notes/project_memo.md", "manuscript/revision_log.md"
        ).returncode == 0
        rs, cs, _ = receipt_paths(r)
        resume_plan = write_plan_rows(p, rec, [
            ("memo.md", "research_notes/project_memo.md", b"memo\n"),
            ("revision.md", "manuscript/revision_log.md", b"revision\n"),
        ])
        spec = importlib.util.spec_from_file_location(
            "assignment_receipt_transaction_hard_crash", TRANSACTION
        )
        assert spec and spec.loader
        crash_module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = crash_module
        spec.loader.exec_module(crash_module)
        real_replace = crash_module.os.replace
        second_target = (p / "manuscript" / "revision_log.md").resolve()

        def hard_stop_second(source: Path, target: Path) -> None:
            if Path(target).resolve() == second_target:
                raise KeyboardInterrupt("injected hard interruption")
            real_replace(source, target)

        crash_module.os.replace = hard_stop_second
        try:
            try:
                crash_module.commit_receipt(p, rs, resume_plan)
            except KeyboardInterrupt:
                pass
            else:
                raise AssertionError("hard interruption failpoint did not fire")
        finally:
            crash_module.os.replace = real_replace
        assert (p / "research_notes" / "project_memo.md").is_file()
        assert not (p / "manuscript" / "revision_log.md").exists()
        resumed = commit(p, rs, resume_plan)
        assert resumed.returncode == 0, resumed.stdout + resumed.stderr
        assert cs.is_file()
        assert (p / "manuscript" / "revision_log.md").read_bytes() == b"revision\n"

        # Append mode accepts only a strict full-file extension and publishes
        # the exact extended bytes.
        p, r, rec = emitted_project(base, "append-positive")
        revision = p / "manuscript" / "revision_log.md"
        revision.parent.mkdir(parents=True, exist_ok=True)
        revision.write_bytes(b"existing\n")
        assert reserve_paths(
            p, r, "research_notes/project_memo.md", "manuscript/revision_log.md"
        ).returncode == 0
        rs, _, _ = receipt_paths(r)
        append_plan = write_plan_rows(p, rec, [
            ("memo.md", "research_notes/project_memo.md", b"memo\n"),
            ("revision.md", "manuscript/revision_log.md", b"existing\nnew\n"),
        ])
        appended = commit(p, rs, append_plan)
        assert appended.returncode == 0, appended.stdout + appended.stderr
        assert revision.read_bytes() == b"existing\nnew\n"

        # Stale claims require inspection plus exact acknowledgement and are
        # archived as evidence rather than silently expiring.
        p, _, _ = emitted_project(base, "recovery")
        claim = p / "reviews" / ".harness" / "assignment" / "claims" / "transaction.lock"
        claim.parent.mkdir(parents=True, exist_ok=True)
        claim.write_text(
            json.dumps({"pid": 2147483647, "host": platform.node(), "started_at": "1970-01-01T00:00:00Z"}),
            encoding="utf-8",
        )
        inspect = subprocess.run(
            [sys.executable, str(RECOVER), "--project-root", str(p)],
            text=True, encoding="utf-8", errors="replace", capture_output=True, check=False,
        )
        assert inspect.returncode == 4 and "APG-RECOVERY-ACK-REQUIRED" in inspect.stdout
        recovered = subprocess.run(
            [sys.executable, str(RECOVER), "--project-root", str(p),
             "--clear-stale-claim", "--acknowledge", "inspected-receipt-states-and-journal"],
            text=True, encoding="utf-8", errors="replace", capture_output=True, check=False,
        )
        assert recovered.returncode == 0, recovered.stdout + recovered.stderr
        assert not claim.exists()
        assert list(claim.parent.glob("transaction.recovered.*.json"))

        adversarial_regressions = (
            ("forged receipt authorization", forged_receipt_authorization_is_refused),
            ("copied consumed receipt replay", copied_consumed_receipt_cannot_replay),
            ("distinct same-target receipts", distinct_receipts_cannot_overwrite_same_snapshot),
            ("reservation scope expansion", reservation_scope_cannot_expand_at_commit),
            ("append-only overwrite", append_only_output_cannot_be_overwritten),
            ("partial multi-file publication", failure_after_first_publish_is_not_partial),
        )
        failures = []
        for name, regression in adversarial_regressions:
            try:
                regression(base)
            except AssertionError as exc:
                failures.append(f"{name}: {exc}")
        assert not failures, "WP2 SECURITY REGRESSIONS\n- " + "\n- ".join(failures)

    print("assignment_receipt_transaction_smoketest: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
