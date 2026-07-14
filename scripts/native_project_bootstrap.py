#!/usr/bin/env python3
"""Seed lifecycle-critical files for a native milestone-framework project."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from reader_accessibility_policy import phase_state_binding, resolve_policy


UTC_PATTERN = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z$"
)
MILESTONES = ("M1", "M2", "M3", "M4", "M5")


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
            policy_evidence={"intended_readers": intended_readers},
        ),
        "M2": _pending_record(
            "Build and annotate the evidence base needed to test and refine the M1 framing.",
            ["Accepted M1 F9 handoff", "research_notes/project_memo.md"],
            [
                "Annotated references cover the M1 tension and expose material gaps or disagreements.",
                "Feedback is adjudicated and an authorized approver accepts the reference set.",
                "An F9 handoff binds the accepted references and instructions for M3.",
            ],
        ),
        "M3": _pending_record(
            "Turn the accepted framing and evidence base into a coherent argument and evidence plan.",
            ["Accepted M2 F9 handoff", "research_notes/annotated_references.md"],
            [
                "The outline maps claims, evidence, objections, and section dependencies.",
                "Feedback is adjudicated and an authorized approver accepts the outline.",
                "An F9 handoff binds the accepted outline and drafting instructions for M4.",
            ],
        ),
        "M4": _pending_record(
            "Produce and stabilize a complete manuscript that realizes the accepted M3 argument plan.",
            ["Accepted M3 F9 handoff", "manuscript/outline.md"],
            [
                "A complete manuscript is bound as the deliverable rather than a plan or checklist.",
                "Review feedback is adjudicated against the current manuscript hash.",
                "An authorized approver accepts the draft and an F9 handoff releases it to M5.",
            ],
        ),
        "M5": _pending_record(
            "Finalize the accepted draft for its declared submission or delivery surface.",
            ["Accepted M4 F9 handoff", "manuscript/main.md", "Venue or delivery requirements"],
            [
                "The submission-bound manuscript and released export are hash-bound.",
                "Final feedback and closure checks are adjudicated.",
                "An authorized approver accepts the final deliverable and terminal F9 packet.",
            ],
        ),
    }
    return {
        "contract_version": "1.0.0",
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
        "sections": {
            "manuscript/main.md": {
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


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def bootstrap(
    project_root: Path,
    project_name: str,
    title: str,
    intended_readers: list[str],
    created_at: str,
) -> None:
    project_root = project_root.resolve()
    if not project_name.strip() or not title.strip():
        raise ValueError("project name and title must be non-empty")
    if not intended_readers or any(not value.strip() for value in intended_readers):
        raise ValueError("at least one non-empty intended reader is required")
    if not UTC_PATTERN.fullmatch(created_at):
        raise ValueError("created-at must be strict ISO-8601 UTC ending in Z")

    seeded = [
        project_root / "reviews" / "phase_state.json",
        project_root / "research_notes" / "project_memo.md",
        project_root / "research_notes" / "annotated_references.md",
        project_root / "manuscript" / "outline.md",
        project_root / "manuscript" / "main.md",
    ]
    existing = [str(path) for path in seeded if path.exists()]
    if existing:
        raise ValueError(f"refusing to overwrite bootstrap surfaces: {', '.join(existing)}")

    (project_root / "reviews" / ".harness" / "milestones").mkdir(parents=True, exist_ok=True)
    policy_path = project_root / "reviews" / ".harness" / "policies" / "reader_accessibility.resolved.json"
    resolved = resolve_policy(project_root)
    _write(policy_path, json.dumps(resolved, indent=2, ensure_ascii=False) + "\n")
    binding = phase_state_binding(resolved, policy_path, project_root)
    framework = _framework(project_name, intended_readers, created_at, binding)

    _write(
        project_root / "research_notes" / "project_memo.md",
        f"# Project Memo — {project_name}\n\n**Milestone:** M1 (Project Memo)\n**Status:** In progress\n\n"
        "## Focus and framing\n\n## Core tension\n\n## Intended readers\n\n"
        "## Question candidates\n\n## Evidence and snowball plan\n",
    )
    _write(
        project_root / "research_notes" / "annotated_references.md",
        f"# Annotated References — {project_name}\n\n**Milestone:** M2 (Annotated References)\n"
        "**Status:** Not started\n\nNo reference has been reviewed or accepted at bootstrap.\n",
    )
    _write(
        project_root / "manuscript" / "outline.md",
        f"# Structured Outline — {project_name}\n\n**Milestone:** M3 (Structured Outline)\n"
        "**Status:** Not started\n\nNo outline has been reviewed or accepted at bootstrap.\n",
    )
    _write(
        project_root / "manuscript" / "main.md",
        f"# {title}\n\n**Milestone:** M4 (Paper Draft)\n**Status:** Not started\n\n"
        "No manuscript has been reviewed or accepted at bootstrap.\n",
    )
    _write(
        project_root / "reviews" / "phase_state.json",
        json.dumps(_phase_state(project_name, created_at, framework), indent=2, ensure_ascii=False) + "\n",
    )


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
    print(f"BOOTSTRAPPED {args.project_root.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
