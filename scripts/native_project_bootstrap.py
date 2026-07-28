#!/usr/bin/env python3
"""Seed lifecycle-critical files for a native milestone-framework project."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from reader_accessibility_policy import (
    reader_profile_phase_state_binding,
    resolve_reader_profile,
)
from milestone_path_contract import (
    PATH_CONTRACT_VERSION,
    canonical_deliverable,
    validate_project_path_surface,
)


UTC_SHAPE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z$"
)
PROJECT_ID_SHAPE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
ValidatorRunner = Callable[..., subprocess.CompletedProcess[str]]


def _pending_record(
    purpose: str,
    required_inputs: list[str],
    exit_criteria: list[str],
    *,
    status: str = "not_started",
    policy_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "purpose": purpose,
        "status": status,
        "applicability": "applicable",
        "required_inputs": required_inputs,
        "exit_criteria": exit_criteria,
        "artifacts": [],
        "feedback_records": [],
        "approval": {
            "status": "pending",
            "authority": None,
            "evidence_path": None,
            "approved_at": None,
        },
        "handoff": {
            "status": "not_ready",
            "packet_path": None,
            "packet_sha256": None,
        },
        "dependency_state": "current",
        "authorized_override": None,
    }
    if policy_evidence is not None:
        record["policy_evidence"] = policy_evidence
    return record


def _framework(
    project_name: str,
    intended_readers: list[str],
    created_at: str,
    policy_binding: dict[str, Any],
    reader_model: dict[str, Any],
) -> dict[str, Any]:
    milestones = {
        "M1": _pending_record(
            "Establish the project's focus, motivating tension, intended readers, and question candidates.",
            ["User brief, venue or advisor constraints, and initial problem evidence"],
            [
                "Project memo is reviewed against the stated problem and intended readers.",
                "Feedback is adjudicated and an authorized approver accepts the memo.",
                "An F9 handoff binds the accepted memo and instructions for M2.",
            ],
            status="in_progress",
            policy_evidence={"reader_model": reader_model},
        ),
        "M2": _pending_record(
            "Build and annotate the evidence base needed to test and refine the M1 framing.",
            ["Accepted M1 F9 handoff", canonical_deliverable("M1")],
            [
                "Annotated references cover the M1 tension and expose material gaps or disagreements.",
                "Feedback is adjudicated and an authorized approver accepts the reference set.",
                "An F9 handoff binds the accepted references and instructions for M3.",
            ],
        ),
        "M3": _pending_record(
            "Turn the accepted framing and evidence base into a coherent argument and evidence plan.",
            ["Accepted M2 F9 handoff", canonical_deliverable("M2")],
            [
                "The outline maps claims, evidence, objections, and section dependencies.",
                "Feedback is adjudicated and an authorized approver accepts the outline.",
                "An F9 handoff binds the accepted outline and drafting instructions for M4.",
            ],
        ),
        "M4": _pending_record(
            "Produce and stabilize a complete manuscript that realizes the accepted M3 argument plan.",
            ["Accepted M3 F9 handoff", canonical_deliverable("M3")],
            [
                "A complete manuscript is bound as the deliverable rather than a plan or checklist.",
                "Review feedback is adjudicated against the current manuscript hash.",
                "An authorized approver accepts the draft and an F9 handoff releases it to M5.",
            ],
        ),
        "M5": _pending_record(
            "Finalize the accepted draft for its declared submission or delivery surface.",
            ["Accepted M4 F9 handoff", canonical_deliverable("M4"), "Venue or delivery requirements"],
            [
                "The submission-bound manuscript and released export are hash-bound.",
                "Final feedback and closure checks are adjudicated.",
                "An authorized approver accepts the final deliverable and terminal F9 packet.",
            ],
        ),
    }
    return {
        "contract_version": "1.0.0",
        "path_contract_version": PATH_CONTRACT_VERSION,
        "mode": "native",
        "migration_boundary": None,
        "primary_lineage": "main",
        "policy_bindings": {"reader_accessibility": policy_binding},
        "milestones": milestones,
        "events": [
            {
                "sequence": 1,
                "event_type": "milestone_started",
                "timestamp": created_at,
                "milestone": "M1",
                "lineage_id": "main",
                "actor": "planner",
                "authority": None,
                "reason": f"Native project {project_name} initialized at M1 without acceptance claims.",
                "evidence_path": None,
                "evidence_sha256": None,
                "caused_by_sequence": None,
                "bindings": [],
            }
        ],
    }


def _phase_state(
    project_name: str,
    created_at: str,
    framework: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "0.7.4",
        "manuscript_id": project_name,
        "default_final_phase": "Ph4",
        "terminal_phase_reached": False,
        # Additive terminal state. Seeded explicitly rather than omitted so a
        # fresh ledger states "no terminal round yet" instead of leaving a
        # reader to decide whether absence means not-yet or lost.
        "terminal_round_id": None,
        "sections": {
            canonical_deliverable("M4"): {
                "current_phase": "Ph1",
                "phase_entry_log": [
                    {
                        "prev_phase": None,
                        "new_phase": "Ph1",
                        "trigger": "initial_dispatch",
                        "actor": "planner",
                        "notes": "Native bootstrap created an empty manuscript scaffold; no milestone was accepted.",
                        "timestamp": created_at,
                        "model_used": None,
                    }
                ],
            }
        },
        "milestone_framework": framework,
    }


def _valid_utc_timestamp(value: str) -> bool:
    if UTC_SHAPE.fullmatch(value) is None:
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() == timezone.utc.utcoffset(parsed)


def _destination(staging_root: Path, relative: str) -> Path:
    candidate = staging_root / relative
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(staging_root.resolve())
    except ValueError as exc:
        raise ValueError(f"seed destination escapes staging root: {relative}") from exc
    return resolved


def _mkdir(staging_root: Path, relative: str) -> Path:
    path = _destination(staging_root, relative)
    path.mkdir(parents=True, exist_ok=False)
    contained = path.resolve()
    try:
        contained.relative_to(staging_root.resolve())
    except ValueError as exc:
        raise ValueError(f"created directory escapes staging root: {relative}") from exc
    return path


def _write(staging_root: Path, relative: str, content: str) -> Path:
    path = _destination(staging_root, relative)
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    try:
        parent.resolve().relative_to(staging_root.resolve())
    except ValueError as exc:
        raise ValueError(f"seed parent escapes staging root: {relative}") from exc
    path.write_text(content, encoding="utf-8", newline="\n")
    return path


def _run_validator(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, encoding="utf-8", errors="replace", capture_output=True, check=False)


def _validate_staging(staging_root: Path, validator_runner: ValidatorRunner) -> None:
    commands = (
        [
            sys.executable,
            "-I",
            "-S",
            str(SCRIPT_DIR / "milestone_framework_validate.py"),
            "--project-root",
            str(staging_root),
        ],
        [
            sys.executable,
            "-I",
            "-S",
            str(SCRIPT_DIR / "phase_state_validate.py"),
            "--project-root",
            str(staging_root),
        ],
    )
    for command in commands:
        result = validator_runner(command, cwd=PACKAGE_ROOT)
        if result.returncode != 0:
            detail = (result.stdout + result.stderr).strip()
            raise ValueError(
                f"canonical bootstrap validation failed ({Path(command[3]).name}, exit {result.returncode})"
                + (f": {detail}" if detail else "")
            )


def bootstrap(
    project_root: Path,
    project_name: str,
    title: str,
    intended_readers: list[str],
    created_at: str,
    *,
    validator_runner: ValidatorRunner = _run_validator,
) -> None:
    requested_root = project_root.expanduser().absolute()
    if requested_root.exists() or requested_root.is_symlink():
        raise ValueError("project root must not exist; native bootstrap never merges or overwrites")
    parent = requested_root.parent.resolve()
    if not parent.is_dir():
        raise ValueError("project-root parent must already exist and be a directory")
    project_root = parent / requested_root.name
    if PROJECT_ID_SHAPE.fullmatch(project_name) is None:
        raise ValueError(
            "project name must be an ASCII slug matching [A-Za-z0-9][A-Za-z0-9._-]*"
        )
    if not title.strip() or not title.isprintable():
        raise ValueError("title must be non-empty, single-line, printable text")
    if not intended_readers or any(not value.strip() for value in intended_readers):
        raise ValueError("at least one non-empty intended reader is required")
    if not _valid_utc_timestamp(created_at):
        raise ValueError("created-at must be a real strict ISO-8601 UTC timestamp ending in Z")

    staging = Path(tempfile.mkdtemp(prefix=f".{project_root.name}.bootstrap-", dir=parent))
    try:
        _mkdir(staging, "reviews/.harness/handoffs")
        _mkdir(staging, "reviews/.harness/snapshots")
        _write(
            staging,
            "research_notes/directives.md",
            f"# Directives — {project_name}\n\n"
            "This file records user, venue, advisor, and project-local overrides. "
            "Higher-authority instructions retain package precedence.\n\n"
            f"project_id: {project_name}\n"
            "passage_scope_class: technical\n\n"
            "No project-local override has been authorized at bootstrap.\n",
        )
        policy_path = _destination(
            staging, "reviews/.harness/policies/reader_accessibility.resolved.json"
        )
        resolved = resolve_reader_profile(staging)
        _write(
            staging,
            "reviews/.harness/policies/reader_accessibility.resolved.json",
            json.dumps(resolved, indent=2, ensure_ascii=False) + "\n",
        )
        binding = reader_profile_phase_state_binding(resolved, policy_path, staging)
        reader_model = resolved["resolved_profile"]["domain_native_register"]["reader_model"]
        framework = _framework(
            project_name, intended_readers, created_at, binding, reader_model
        )

        _write(
            staging,
            canonical_deliverable("M1"),
            f"# Project Memo — {project_name}\n\n**Milestone:** M1 (Project Memo)\n**Status:** In progress\n\n"
            "## Focus and framing\n\n## Core tension\n\n## Reader elicitation notes\n\n"
            + "\n".join(f"- {reader}" for reader in intended_readers) + "\n\n"
            "The authoritative M1 reader model is stored in phase_state.json and remains domain-native.\n\n"
            "## Question candidates\n\n## Evidence and snowball plan\n",
        )
        _write(
            staging,
            canonical_deliverable("M2"),
            f"# Annotated References — {project_name}\n\n**Milestone:** M2 (Annotated References)\n"
            "**Status:** Not started\n\nNo reference has been reviewed or accepted at bootstrap.\n",
        )
        _write(
            staging,
            canonical_deliverable("M3"),
            f"# Structured Outline — {project_name}\n\n**Milestone:** M3 (Structured Outline)\n"
            "**Status:** Not started\n\nNo outline has been reviewed or accepted at bootstrap.\n",
        )
        _write(
            staging,
            canonical_deliverable("M4"),
            f"# {title}\n\n**Milestone:** M4 (Paper Draft)\n**Status:** Not started\n\n"
            "No manuscript has been reviewed or accepted at bootstrap.\n",
        )
        _write(
            staging,
            canonical_deliverable("M5"),
            f"# Final Paper — {project_name}\n\n**Milestone:** M5 (Final Paper)\n"
            "**Status:** Not started\n\nNo final paper has been reviewed or accepted at bootstrap.\n",
        )
        phase_state_doc = _phase_state(project_name, created_at, framework)
        from destination_capability import classify
        if classify(project_root) == "staging":
            # Producer boundary: a staging-lane project's genesis event is
            # production bookkeeping, proposal-only like every later event.
            for row in phase_state_doc["milestone_framework"]["events"]:
                row["effect_scope"] = "proposal_only"
        _write(
            staging,
            "reviews/phase_state.json",
            json.dumps(phase_state_doc, indent=2, ensure_ascii=False)
            + "\n",
        )
        _validate_staging(staging, validator_runner)
        validate_project_path_surface(staging)
        if project_root.exists() or project_root.is_symlink():
            raise ValueError("project root appeared during bootstrap; refusing publication")
        staging.rename(project_root)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--intended-reader", action="append", required=True)
    parser.add_argument(
        "--created-at",
        default=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    )
    args = parser.parse_args(argv)
    from destination_capability import DestinationRefused, guard_project_root
    try:
        guard_project_root(args.project_root)
    except DestinationRefused as exc:
        parser.exit(4, f"[BLOCKER] {exc}\n")
    try:
        bootstrap(
            args.project_root,
            args.project_name,
            args.title,
            list(dict.fromkeys(args.intended_reader)),
            args.created_at,
        )
    except (OSError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")
    state = json.loads((args.project_root / "reviews" / "phase_state.json").read_text(encoding="utf-8"))
    binding = state["milestone_framework"]["policy_bindings"]["reader_accessibility"]
    if binding.get("binding_version") == "2.0.0":
        print("READER_PROFILE_READY semantic_usage=not_invoked")
    print(f"BOOTSTRAPPED {args.project_root.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
