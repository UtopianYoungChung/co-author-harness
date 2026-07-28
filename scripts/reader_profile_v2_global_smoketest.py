#!/usr/bin/env python3
"""Global routing regression for graph-independent native reader-profile v2."""

from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

import assignment_process_gate
import draft_governance
from milestone_framework_validate import validate_document
from native_project_bootstrap import bootstrap
from reader_accessibility_policy import PolicyError, validate_check8_evidence


ROOT = Path(__file__).resolve().parents[1]


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _check_operational_routes() -> None:
    required = {
        "README.md": ("native_project_bootstrap.py", "reader-profile v2"),
        "references/PROJECT_BOOTSTRAP.md": ("native_project_bootstrap.py", "binding_version: 2.0.0"),
        "references/FULL_RUN_CONTRACT.md": ("native_project_bootstrap.py",),
        "docs/agent-instructions/harness-discovery-lifecycle.md": ("native_project_bootstrap.py", "semantic_usage: not_invoked"),
        "agents/planner.md": ("native_project_bootstrap.py", "reader-profile binding v2"),
        "skills/run-draft/SKILL.md": ("native_project_bootstrap.py", "reader-profile binding v2"),
        "docs/superpowers/plans/2026-07-27-reader-profile-v2-next-version-integration.md": ("reader-profile-v2-decoupling", "0.40.0"),
    }
    for relative, tokens in required.items():
        text = (ROOT / relative).read_text(encoding="utf-8")
        missing = [token for token in tokens if token not in text]
        _assert(not missing, f"global reader-profile route is incomplete in {relative}: {missing}")

    operational = (
        "README.md",
        "agents/evaluator.md",
        "agents/generator.md",
        "references/AGENT_ORCHESTRATION.md",
        "references/ASSIGNMENT_MILESTONE_PROCESS.md",
        "references/MANIFEST.md",
        "references/PHASE_PROTOCOL.md",
        "references/REVIEW_ORCHESTRATION.md",
        "references/ROUTING_SPINE.md",
        "references/SKILL_REGISTRY.md",
        "skills/centroid-pass/SKILL.md",
        "skills/plugin-commands/SKILL.md",
    )
    forbidden = (
        "Universal centroid scope",
        "all assignment drafts require centroid/exemplar conditioning",
        "Every M1-M4 and FINAL dispatch requires centroid-conditioned generation",
        "Every M1-M4/FINAL draft receives centroid-conditioned",
        "under the centroid and complete applicable",
        "bounded centroid and complete applicable governing-policy pass",
        "mandatory centroid conditioning",
        "independently executes the centroid and applicable policy bundle",
        "bounded current-byte centroid and complete applicable policy pass",
        "independent centroid/style/grammar/grounding evaluation",
        "one bounded centroid and complete applicable policy evaluation",
        "bounded all-drafts centroid and governing-policy evaluation",
        "bounded all-drafts centroid/policy pass",
        "This pass is mandatory for every academic deliverable and revision, including\nM1-M3. An existing",
        "Status:** Active; mandatory within academic draft generation, evaluation, and revision orchestration.",
        "Trigger:** Every M1-M4/FINAL draft or revision, or explicit `/centroid-pass`.",
    )
    for relative in operational:
        text = (ROOT / relative).read_text(encoding="utf-8")
        present = [phrase for phrase in forbidden if phrase in text]
        _assert(not present, f"stale universal graph obligation remains in {relative}: {present}")


def _check_check8_v2() -> None:
    evidence = {
        "schema_version": "check8_evidence.v2",
        "cycle_id": "global-routing-001",
        "profile_path": "reviews/.harness/policies/reader_accessibility.resolved.json",
        "profile_sha256": "a" * 64,
        "semantic_usage": "not_invoked",
        "manuscript_path": "milestones/M4_complete_paper_draft.md",
        "manuscript_sha256": "b" * 64,
        "phase": "Ph3",
        "transition_snapshot": {key: "active" for key in ("G", "H", "VE")},
        "subchecks": {key: {"findings": []} for key in "ABCDEFGH"},
        "subcheck_verdicts": {key: "CLEAN" for key in "ABCDEFGH"},
        "ve": {"aggregate_member": False, "gate_contribution": "none", "findings": []},
        "aggregate_verdict": "CLEAN",
    }
    validate_check8_evidence(evidence)
    forged = copy.deepcopy(evidence)
    forged["attestation_view_pin"] = "c" * 64
    try:
        validate_check8_evidence(forged)
    except PolicyError:
        pass
    else:
        raise AssertionError("Check 8 v2 admitted a semantic register pin")


def main() -> int:
    _check_operational_routes()
    _check_check8_v2()
    with tempfile.TemporaryDirectory(prefix="reader-profile-v2-global-") as directory:
        project = Path(directory) / "native-v2"
        bootstrap(
            project,
            "native-v2",
            "Native V2",
            ["requirements engineering researchers"],
            "2026-07-27T17:30:00Z",
        )
        state_path = project / "reviews" / "phase_state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        binding = state["milestone_framework"]["policy_bindings"]["reader_accessibility"]
        _assert(binding.get("binding_version") == "2.0.0", "canonical bootstrap omitted binding v2")
        _assert(binding.get("binding_kind") == "reader_profile", "canonical bootstrap used the wrong binding kind")
        _assert(binding.get("semantic_usage") == "not_invoked", "canonical bootstrap fabricated semantic use")
        _assert(
            not any(key in binding for key in ("attestation_view_pin", "exemplar_view_pin", "graph_sha256_provenance", "blocker")),
            "canonical v2 binding retained graph-coupled authority fields",
        )
        _assert(not validate_document(project, state).findings, "canonical v2 bootstrap failed milestone validation")
        _assert(
            assignment_process_gate._graph_independent_reader_profile(project),
            "assignment dispatch did not derive the v2 graph-independent state",
        )

        contract = draft_governance.prepare(SimpleNamespace(
            project_root=str(project), target="M1", phase="generation", role="generator", artifact=None,
        ))
        _assert(contract["centroid"].get("required") is False, "v2 draft governance still requires centroid execution")
        _assert(contract["centroid"].get("semantic_usage") == "not_invoked", "v2 draft governance lost semantic usage")
        _assert(
            all(row.get("id") != "centroid-generation" for row in contract["obligations"]),
            "v2 draft governance retained the centroid generation obligation",
        )

        evaluation = draft_governance.prepare(SimpleNamespace(
            project_root=str(project), target="M1", phase="evaluation", role="evaluator", artifact=None,
        ))
        _assert(evaluation["centroid"].get("required") is False, "v2 evaluation still requires centroid execution")
        _assert(evaluation["centroid"].get("semantic_usage") == "not_invoked", "v2 evaluation lost semantic usage")
        _assert(
            all(row.get("id") != "centroid-evaluation" for row in evaluation["obligations"]),
            "v2 draft governance retained the centroid evaluation obligation",
        )

        bypass = copy.deepcopy(state)
        bypass["milestone_framework"]["policy_bindings"].pop("reader_accessibility")
        findings = validate_document(project, bypass).findings
        _assert(
            any(item.code == "MF-POLICY" and "reader-accessibility" in item.message for item in findings),
            "a hand-built native ledger bypassed the mandatory reader-profile binding",
        )

        malformed = copy.deepcopy(state)
        malformed["milestone_framework"]["policy_bindings"]["reader_accessibility"]["attestation_view_pin"] = "c" * 64
        findings = validate_document(project, malformed).findings
        _assert(
            any("reader_accessibility" in item.path for item in findings),
            "a malformed present reader-profile binding bypassed validation",
        )

    print("reader_profile_v2_global_smoketest: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
