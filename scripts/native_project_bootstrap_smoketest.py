#!/usr/bin/env python3
"""Exercise the native milestone bootstrap against its production validator."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from semantic_graph_fixture_support import semantic_graph_fixture_environment


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "scripts" / "native_project_bootstrap.py"
VALIDATOR = ROOT / "scripts" / "milestone_framework_validate.py"
PHASE_VALIDATOR = ROOT / "scripts" / "phase_state_validate.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", "-S", *args],
        cwd=ROOT,
        text=True, encoding="utf-8", errors="replace",
        capture_output=True,
        check=False,
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="native-bootstrap-") as directory:
        project = Path(directory) / "test-project"
        created = _run(
            str(BOOTSTRAP),
            "--project-root", str(project),
            "--project-name", "test-project",
            "--title", "Test Project",
            "--intended-reader", "requirements engineering researchers",
            "--created-at", "2026-07-13T20:00:00Z",
        )
        if created.returncode != 0:
            raise AssertionError(
                f"bootstrap failed ({created.returncode}):\n{created.stdout}{created.stderr}"
            )

        required_files = {
            "reviews/phase_state.json",
            "reviews/.harness/policies/reader_accessibility.resolved.json",
            "research_notes/project_memo.md",
            "research_notes/annotated_references.md",
            "research_notes/directives.md",
            "manuscript/outline.md",
            "manuscript/main.md",
        }
        missing = sorted(path for path in required_files if not (project / path).is_file())
        if missing:
            raise AssertionError(f"bootstrap omitted required files: {missing}")
        if not (project / "reviews" / ".harness" / "milestones").is_dir():
            raise AssertionError("bootstrap omitted reviews/.harness/milestones/")

        phase_state = json.loads((project / "reviews" / "phase_state.json").read_text(encoding="utf-8"))
        framework = phase_state.get("milestone_framework")
        if not isinstance(framework, dict):
            raise AssertionError("phase_state.json is not the milestone authority")
        expected_statuses = {
            "M1": "in_progress",
            "M2": "not_started",
            "M3": "not_started",
            "M4": "not_started",
            "M5": "not_started",
        }
        actual_statuses = {
            key: framework["milestones"][key]["status"] for key in expected_statuses
        }
        if actual_statuses != expected_statuses:
            raise AssertionError(f"wrong native milestone seed: {actual_statuses}")
        source_bindings = framework["policy_bindings"]["reader_accessibility"]["source_bindings"]
        if not any(
            item.get("scope") == "project"
            and item.get("role") == "directives"
            and item.get("path") == "research_notes/directives.md"
            for item in source_bindings
        ):
            raise AssertionError("bootstrap policy is not bound to the seeded project directives")
        reader_binding = framework["policy_bindings"]["reader_accessibility"]
        if reader_binding.get("project_identity") != "test-project":
            raise AssertionError("policy binding identity is not the full validated project identifier")
        resolved_policy = json.loads(
            (project / "reviews" / ".harness" / "policies" / "reader_accessibility.resolved.json").read_text(
                encoding="utf-8"
            )
        )
        if resolved_policy.get("project_identity") != "test-project" or resolved_policy.get("register_class") != "domain-native" or resolved_policy.get("passage_scope_class") != "technical":
            raise AssertionError("project identifier changed policy identity or register class")

        for key, record in framework["milestones"].items():
            if record["artifacts"] or record["feedback_records"]:
                raise AssertionError(f"{key} fabricated artifact or feedback evidence")
            if record["approval"] != {
                "status": "pending",
                "authority": None,
                "evidence_path": None,
                "approved_at": None,
            }:
                raise AssertionError(f"{key} fabricated approval state")
            if record["handoff"] != {
                "status": "not_ready",
                "packet_path": None,
                "packet_sha256": None,
            }:
                raise AssertionError(f"{key} fabricated handoff state")

        events = framework.get("events")
        if not isinstance(events, list) or len(events) != 1 or events[0]["event_type"] != "milestone_started":
            raise AssertionError(f"bootstrap event stream is not minimal: {events!r}")
        if any(events[0].get(field) is not None for field in ("authority", "evidence_path", "evidence_sha256")):
            raise AssertionError("bootstrap fabricated authority or evidence on M1 start")

        milestone_result = _run(str(VALIDATOR), "--project-root", str(project))
        if milestone_result.returncode != 0 or not milestone_result.stdout.startswith("READY "):
            raise AssertionError(
                "milestone validator rejected bootstrap output:\n"
                f"{milestone_result.stdout}{milestone_result.stderr}"
            )
        phase_result = _run(str(PHASE_VALIDATOR), "--project-root", str(project))
        if phase_result.returncode != 0 or "PASS" not in phase_result.stdout:
            raise AssertionError(
                "phase validator rejected bootstrap output:\n"
                f"{phase_result.stdout}{phase_result.stderr}"
            )

    print("native_project_bootstrap_smoketest: PASS")
    return 0


if __name__ == "__main__":
    with semantic_graph_fixture_environment():
        raise SystemExit(main())
