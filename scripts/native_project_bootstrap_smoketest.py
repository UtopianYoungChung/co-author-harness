#!/usr/bin/env python3
"""Exercise the native milestone bootstrap against its production validator."""

from __future__ import annotations

import json
import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from semantic_graph_fixture_support import semantic_graph_fixture_environment
from assignment_milestone_transaction import rebind_reader_accessibility
from reader_accessibility_policy import (
    resolve_unavailable_policy,
    unavailable_phase_state_binding,
)


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "scripts" / "native_project_bootstrap.py"
VALIDATOR = ROOT / "scripts" / "milestone_framework_validate.py"
PHASE_VALIDATOR = ROOT / "scripts" / "phase_state_validate.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", "-S", "-B", *args],
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
            "milestones/M1_project_memo.md",
            "milestones/M2_annotated_references.md",
            "research_notes/directives.md",
            "milestones/M3_argument_evidence_outline.md",
            "milestones/M4_complete_paper_draft.md",
            "milestones/M5_final_paper.md",
        }
        missing = sorted(path for path in required_files if not (project / path).is_file())
        if missing:
            raise AssertionError(f"bootstrap omitted required files: {missing}")
        for directory_name in ("handoffs", "snapshots"):
            if not (project / "reviews" / ".harness" / directory_name).is_dir():
                raise AssertionError(f"bootstrap omitted reviews/.harness/{directory_name}/")
        legacy = {
            "research_notes/project_memo.md", "research_notes/annotated_references.md",
            "manuscript/outline.md", "manuscript/main.md", "manuscript/final.md",
        }
        leaked = sorted(path for path in legacy if (project / path).exists() or (project / path).is_symlink())
        if leaked:
            raise AssertionError(f"bootstrap created legacy milestone aliases: {leaked}")

        phase_state = json.loads((project / "reviews" / "phase_state.json").read_text(encoding="utf-8"))
        framework = phase_state.get("milestone_framework")
        if not isinstance(framework, dict):
            raise AssertionError("phase_state.json is not the milestone authority")
        if framework.get("path_contract_version") != "2.0.0":
            raise AssertionError("bootstrap omitted milestone_framework.path_contract_version")
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

        graph_path = (
            Path(os.environ["AGENT_WORKSPACE_ROOT"])
            / "knowledge" / "LLM wiki" / "graphify-out" / "graph.json"
        )
        original_graph = json.loads(graph_path.read_text(encoding="utf-8"))
        structural_graph = json.loads(json.dumps(original_graph))
        structural_graph["graph"]["extraction_mode"] = "structural-only"
        structural_graph["graph"]["semantic_status"] = "pending"
        graph_path.write_text(
            json.dumps(structural_graph, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        deferred = Path(directory) / "structural-project"
        created_deferred = _run(
            str(BOOTSTRAP),
            "--project-root", str(deferred),
            "--project-name", "structural-project",
            "--title", "Structural Project",
            "--intended-reader", "requirements engineering researchers",
            "--created-at", "2026-07-27T15:00:00Z",
        )
        if created_deferred.returncode != 0:
            raise AssertionError(
                "structural-only graph should permit a graph-independent bootstrap:\n"
                f"{created_deferred.stdout}{created_deferred.stderr}"
            )
        if "READER_PROFILE_READY semantic_usage=not_invoked" not in created_deferred.stdout:
            raise AssertionError("bootstrap did not disclose its graph-independent reader profile")
        deferred_state_path = deferred / "reviews" / "phase_state.json"
        deferred_state = json.loads(deferred_state_path.read_text(encoding="utf-8"))
        deferred_binding = deferred_state["milestone_framework"]["policy_bindings"]["reader_accessibility"]
        if deferred_binding.get("binding_version") != "2.0.0":
            raise AssertionError("structural bootstrap omitted the v2 reader-profile binding")
        if deferred_binding.get("semantic_usage") != "not_invoked":
            raise AssertionError("structural bootstrap fabricated semantic graph use")
        if any(key in deferred_binding for key in ("blocker", "graph_sha256_provenance", "attestation_view_pin", "exemplar_view_pin")):
            raise AssertionError("graph-independent binding retained graph-coupled fields")
        deferred_validation = _run(str(VALIDATOR), "--project-root", str(deferred))
        if deferred_validation.returncode != 0 or not deferred_validation.stdout.startswith("READY "):
            raise AssertionError(
                "canonical validator rejected the graph-independent bootstrap:\n"
                f"{deferred_validation.stdout}{deferred_validation.stderr}"
            )
        state_hash = hashlib.sha256(deferred_state_path.read_bytes()).hexdigest()
        changed_graph = json.loads(json.dumps(structural_graph))
        changed_graph["graph"]["decoupling_probe"] = "must-not-affect-reader-profile"
        graph_path.write_text(
            json.dumps(changed_graph, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        changed_graph_validation = _run(str(VALIDATOR), "--project-root", str(deferred))
        if changed_graph_validation.returncode != 0 or not changed_graph_validation.stdout.startswith("READY "):
            raise AssertionError(
                "structural graph drift incorrectly invalidated the reader profile:\n"
                f"{changed_graph_validation.stdout}{changed_graph_validation.stderr}"
            )
        if hashlib.sha256(deferred_state_path.read_bytes()).hexdigest() != state_hash:
            raise AssertionError("read-only validation changed governed phase-state bytes")

        # A legacy M1-only fallback is upgraded only through an explicit,
        # receipted Planner transaction; structural graph eligibility is not a
        # prerequisite for the reader-profile migration.
        legacy_resolved_path = deferred / deferred_binding["resolved_path"]
        legacy_resolved = resolve_unavailable_policy(
            deferred,
            "GRAPH-SEMANTIC-INELIGIBLE: synthetic legacy migration fixture",
        )
        legacy_resolved_path.write_text(
            json.dumps(legacy_resolved, indent=2) + "\n", encoding="utf-8", newline="\n",
        )
        legacy_binding = unavailable_phase_state_binding(
            legacy_resolved, legacy_resolved_path, deferred,
        )
        legacy_state = json.loads(deferred_state_path.read_text(encoding="utf-8"))
        legacy_state["milestone_framework"]["policy_bindings"]["reader_accessibility"] = legacy_binding
        deferred_state_path.write_text(
            json.dumps(legacy_state, indent=2) + "\n", encoding="utf-8", newline="\n",
        )
        migration_receipt = rebind_reader_accessibility(
            deferred, "2026-07-27T15:30:00Z",
        )
        if not migration_receipt.is_file():
            raise AssertionError("legacy reader-policy migration omitted its receipt")
        migrated = json.loads(deferred_state_path.read_text(encoding="utf-8"))
        migrated_binding = migrated["milestone_framework"]["policy_bindings"]["reader_accessibility"]
        if migrated_binding.get("binding_version") != "2.0.0" or migrated_binding.get("semantic_usage") != "not_invoked":
            raise AssertionError("legacy migration did not install the v2 reader-profile binding")
        migrated_validation = _run(str(VALIDATOR), "--project-root", str(deferred))
        if migrated_validation.returncode != 0 or not migrated_validation.stdout.startswith("READY "):
            raise AssertionError(
                "canonical validator rejected migrated reader profile:\n"
                f"{migrated_validation.stdout}{migrated_validation.stderr}"
            )

    print("native_project_bootstrap_smoketest: PASS")
    return 0


if __name__ == "__main__":
    with semantic_graph_fixture_environment():
        raise SystemExit(main())
