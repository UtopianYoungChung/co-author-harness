#!/usr/bin/env python3
"""assignment_fixture_support - the ONE valid assignment contract fixture.

WHY THIS MODULE EXISTS
----------------------
`full_run_semantic_bypass_smoketest` needed a real READY receipt to reach the
dispatch-preflight branch of `authorize`. It could not get one: the assignment
gate refused its `{"status": "resolved"}` stub with nine blockers
(APG-CONTRACT-UNRESOLVED, APG-PROFILE-ID, APG-PROFILE-PATH, APG-PROFILE-HASH,
APG-SOURCE-AUTHORITY, APG-SEQUENCE, APG-MAPPING,
APG-PROFESSOR-COPY-AUTHORITY, APG-WIKI-GROUNDING-MISSING). That refusal is the
gate working: a receipt is not obtainable without a genuinely resolved
contract, which is the property the receipt certifies.

The obvious shortcut -- hand-copy the contract dict out of
`assignment_process_gate_smoketest.main()` into the other suite -- is the exact
mistake this whole workstream keeps finding, one layer down: two copies of one
fact, drifting, with the copy in the newer file quietly becoming a DIFFERENT
and weaker idea of "valid". A fixture paraphrase is no better than a validator
paraphrase.

So the fixture is extracted here and both suites import it. If the contract
schema changes, both suites change with it, or both fail together -- which is
the point.

Nothing here is authoritative ABOUT the contract. `assignment_process_gate.py`
remains the only thing that decides whether a contract is resolved; this module
just builds one it will accept, from the profile on disk.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "references" / "policies" / "course_essay_milestones.v1.json"


def package_scratch(root: Path = ROOT) -> Path:
    """Package-local fixtures share one ignored, non-distributable namespace."""
    scratch = root.resolve() / '.harness-test-scratch'
    scratch.mkdir(exist_ok=True)
    return scratch


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_valid_contract(project: Path) -> dict[str, Any]:
    """Write a contract `assignment_process_gate.py` accepts as resolved.

    The profile hash is READ FROM THE PROFILE ON DISK rather than pinned here:
    a pinned hash is a second copy of the profile's identity, and it goes stale
    the moment the profile is edited -- turning a real change into a mystery
    fixture failure.
    """
    source = project / "course-assignment.pdf"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"synthetic assignment brief\n")
    contract = {
        "contract_version": "1.0.0",
        "status": "resolved",
        "profile_id": "course-essay-four-milestones-v1",
        "profile_path": "references/policies/course_essay_milestones.v1.json",
        "profile_sha256": sha256(PROFILE),
        "assignment_source": {
            "path": str(source),
            "sha256": sha256(source),
            "authority": "instructor",
        },
        "assigned_sequence": ["M1", "M2", "M3", "M4", "FINAL"],
        "framework_mapping": {
            "M1": "M1", "M2": "M2", "M3": "M3", "M4": "M4", "FINAL": "M5",
        },
        "professor_copy_policy": "author_controlled_unless_explicitly_requested",
    }
    path = project / "reviews" / "assignment_contract.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    return contract


def write_wiki_evidence(project: Path, phase_state: dict) -> Path:
    """Bind wiki-first grounding evidence to M3 (required for M4/FINAL targets).

    Moved here verbatim from `assignment_process_gate_smoketest`, which now
    imports it. Mutates `phase_state` and rewrites reviews/phase_state.json,
    exactly as before.
    """
    references = project / "references" / "REFERENCES.md"
    references.parent.mkdir(parents=True, exist_ok=True)
    references.write_text("# Verified references\n", encoding="utf-8")
    wiki = project / "synthetic-wiki"
    source_page = wiki / "sources" / "yu.md"
    source_page.parent.mkdir(parents=True, exist_ok=True)
    source_page.write_text("# Yu source page\n", encoding="utf-8")
    graph = wiki / "graphify-out" / "graph.json"
    graph.parent.mkdir(parents=True, exist_ok=True)
    graph.write_text('{"nodes": []}\n', encoding="utf-8")
    evidence_path = project / "reviews" / ".harness" / "assignment" / "wiki_grounding_test.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence = {
        "schema_version": "1.0.0",
        "lineage_id": "live",
        "produced_at": "2026-07-15T00:00:00Z",
        "wiki_path": str(wiki),
        "wiki_first_resources": True,
        "skills_invoked": ["seed-snowball-discovery"],
        "references_path": "references/REFERENCES.md",
        "references_sha256": sha256(references),
        "graph_path": str(graph),
        "graph_sha256_provenance": sha256(graph),
        "sources_consulted": [{"path": str(source_page), "sha256": sha256(source_page)}],
        "authority": "planner",
        "notes": "Synthetic wiki-first grounding evidence for the gate smoketest.",
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    phase_state["milestone_framework"]["milestones"]["M3"]["policy_evidence"] = {
        "wiki_grounding": {
            "evidence_path": evidence_path.relative_to(project).as_posix(),
            "evidence_sha256": sha256(evidence_path),
        }
    }
    (project / "reviews" / "phase_state.json").write_text(
        json.dumps(phase_state, indent=2) + "\n", encoding="utf-8"
    )
    return evidence_path


def minimal_gate_project(project: Path, *, target: str = "M1") -> dict[str, Any]:
    """A project the assignment gate will emit a READY receipt for.

    Deliberately minimal: milestones up to `target` not_started, the rest as the
    gate's own smoketest has them. This is NOT a full-lifecycle project and is
    not meant to pass `terminal` -- it exists to reach the gate/preflight path.
    """
    write_valid_contract(project)
    phase_state = {
        "milestone_framework": {
            "mode": "native",
            "milestones": {
                key: {"status": "not_started"} for key in ("M1", "M2", "M3", "M4", "M5")
            },
        }
    }
    path = project / "reviews" / "phase_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(phase_state, indent=2) + "\n", encoding="utf-8")
    return phase_state
