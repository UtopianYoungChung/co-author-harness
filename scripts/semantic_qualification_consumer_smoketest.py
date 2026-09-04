#!/usr/bin/env python3
"""End-to-end fresh semantic producer to real reader resolver contract test."""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import domain_native_register_smoketest as dnr_fixture
import assignment_milestone_transaction as amt
import milestone_framework_validate as milestone_validator
import reader_accessibility_policy as policy
from semantic_graph_fixture_support import semantic_graph_fixture_environment


def _load_qualification(path: Path):
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("semantic_qualification_under_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load semantic qualification producer: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def run(qualification_script: Path, project_template: Path) -> None:
    qualification = _load_qualification(qualification_script.resolve())
    transaction_id = "semq-20260808T235959Z-c0dec0de"
    producer = "Codex"
    producer_model = "gpt-consumer-fixture"
    auditor = "Claude Code"
    auditor_model = "claude-consumer-fixture"
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        harness = root / "harness"
        profile_path = harness / "references/policies/reader_accessibility.v1.json"
        schema_path = harness / "references/schemas/reader_accessibility_profile.schema.json"
        schema_path.parent.mkdir(parents=True, exist_ok=True)
        schema_path.write_bytes((ROOT / "references/schemas/reader_accessibility_profile.schema.json").read_bytes())
        profile = policy.load_profile()
        profile["domain_native_register"]["exemplar_members"] = [
            member for member in profile["domain_native_register"]["exemplar_members"]
            if member.get("warrant_scope", "both") == "both"
        ]
        profile["profile_version"] = "1.0.0"
        _write_json(profile_path, profile)
        wiki, workspace = dnr_fixture.write_fixture(root / "corpus")
        structural_source = workspace / "knowledge/LLM wiki/graphify-out/graph.json"
        base = json.loads(structural_source.read_text(encoding="utf-8"))
        base["nodes"] = [node for node in base["nodes"] if node.get("semantic_status") != "validated"]
        base["links"] = [edge for edge in base["links"] if edge.get("semantic_status") != "validated"]
        represented = {node.get("source_file") for node in base["nodes"]}
        for directory in ("wiki/sources", "wiki/concepts", "wiki/entities", "wiki/syntheses"):
            for page_path in sorted((wiki / directory).glob("*.md")):
                source_file = page_path.relative_to(wiki).as_posix()
                if source_file not in represented:
                    base["nodes"].append({
                        "id": page_path.stem, "label": page_path.stem,
                        "file_type": "source", "source_file": source_file, "community": 1,
                    })
                    represented.add(source_file)
        base["graph"] = {
            "schema_version": "llm-wiki-graph-v1",
            "extraction_mode": "structural-only",
            "semantic_status": "pending",
        }
        base_graph = wiki / "graphify-out/graph.json"
        _write_json(base_graph, base)

        qualification.command_plan(wiki, transaction_id, producer, producer_model)
        stage = wiki / "graphify-out/semantic-qualifications" / transaction_id
        manifest = json.loads((stage / "manifest.json").read_text(encoding="utf-8"))
        for chunk in manifest["chunks"]:
            pages = []
            for source_file in chunk["source_files"]:
                page = next(row for row in manifest["pages"] if row["source_file"] == source_file)
                semantic_id = page["node_prefix"] + hashlib.sha256(
                    source_file.encode("utf-8")
                ).hexdigest()[:12]
                pages.append({
                    "source_file": source_file,
                    "sha256": page["sha256"],
                    "nodes": [{
                        "id": semantic_id, "label": f"Claim from {source_file}",
                        "file_type": "claim", "source_file": source_file,
                        "source_location": "fixture page", "semantic_status": "candidate",
                    }],
                    "edges": [{
                        "source": page["structural_node_id"], "target": semantic_id,
                        "relation": "describes", "confidence": "EXTRACTED",
                        "confidence_score": 1.0, "warrant": "model-textual",
                        "source_file": source_file, "source_location": "fixture page",
                        "weight": 1.0, "evidence": "fixture page states the claim",
                    }],
                })
            _write_json(stage / "chunks" / f"{chunk['chunk_id']}.output.json", {
                "schema_version": "1.0.0", "chunk_id": chunk["chunk_id"],
                "producer": producer, "producer_model": producer_model, "pages": pages,
            })
        qualification.command_candidate(wiki, transaction_id, producer, producer_model)
        qualification.command_audit_plan(
            wiki, transaction_id, producer, auditor, profile_path,
            producer_model, auditor_model,
        )
        audit_request = json.loads((stage / "audit_request.json").read_text(encoding="utf-8"))
        audit_rows = [{
            "semantic_edge_id": edge["semantic_edge_id"], "verdict": "supported",
            "note": "independently checked against fixture page", "reviewer": auditor,
        } for edge in audit_request["edges"]]
        _write_json(stage / "audit.submission.json", {
            "schema_version": "1.0.0", "transaction_id": transaction_id,
            "reviewer": auditor, "reviewer_model": auditor_model,
            "manifest_sha256": audit_request["manifest_sha256"],
            "semantic_outputs_sha256": audit_request["semantic_outputs_sha256"],
            "candidate_sha256": audit_request["candidate_sha256"],
            "sample_count": len(audit_rows),
            "verdict_counts": {"supported": len(audit_rows), "unclear": 0, "unsupported": 0},
            "edges": audit_rows,
        })
        qualification.command_apply(
            wiki, transaction_id, producer, auditor, producer_model, auditor_model,
        )

        graph_relative = (
            "knowledge/LLM wiki/graphify-out/semantic-qualifications/"
            f"{transaction_id}/qualified.graph.json"
        )
        qualified_workspace = workspace / graph_relative
        qualified_workspace.parent.mkdir(parents=True, exist_ok=True)
        qualified_workspace.write_bytes((stage / "qualified.graph.json").read_bytes())
        profile["domain_native_register"]["corpus_binding"]["graph"]["path"] = graph_relative
        resolved = policy.resolve_domain_native_register(
            profile, wiki_root=wiki, workspace_root=workspace, harness_root=harness,
        )
        assert resolved["graph_semantic_status"] == "validated"
        assert any(row["role"] == "semantic_rollback" for row in resolved["provenance"])

        # Exercise Planner with the canonical milestone validator, not a stub.
        project = root / "project"
        shutil.copytree(project_template, project)
        register = policy.resolve_domain_native_register(
            profile, wiki_root=wiki, workspace_root=workspace, harness_root=harness,
        )
        expected = profile["domain_native_register"]["expected_verification"]
        expected.update(
            attestation_view_pin=register["attestation_view_pin"],
            exemplar_view_pin=register["exemplar_view_pin"],
            pin_epoch=2, pinned_at="2026-08-08T23:59:59Z",
        )
        profile["domain_native_register"]["corpus_binding"]["graph"][
            "observed_sha256_at_review"
        ] = register["graph_sha256_provenance"]
        _write_json(profile_path, profile)
        for relative in profile["package_contributors"]:
            target = harness / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / relative).read_bytes())

        state_path = project / "reviews/phase_state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        framework = state["milestone_framework"]
        old_binding = framework["policy_bindings"]["reader_accessibility"]
        assert old_binding["binding_version"] == "2.0.0"
        resolved_path = project / old_binding["resolved_path"]
        old_resolved = resolved_path.read_bytes()
        old_binding["resolved_sha256"] = hashlib.sha256(old_resolved).hexdigest()
        state_path.write_bytes(amt._json_bytes(state))
        state_bytes = state_path.read_bytes()

        original_root = policy.ROOT
        original_resolve = policy.resolve_policy
        policy.ROOT = harness
        fresh = original_resolve(
            project, profile_path=profile_path, wiki_root=wiki,
            workspace_root=workspace, harness_root=harness,
        )
        ledger = harness / "references/policies/repin_log.jsonl"
        snapshot = harness / "reviews/.harness/repin/epoch-2.snapshot.json"
        _write_json(snapshot, {"epoch": 2, "graph_sha256_provenance": fresh["graph_sha256_provenance"]})
        ledger_row = {
            "epoch": 2, "delta_class": "corpus", "pinned_at": "2026-08-08T23:59:59Z",
            "profile_sha256": {"old": old_binding["profile_sha256"], "new": fresh["profile_sha256"]},
            "attestation_view_pin": {"old": old_binding.get("attestation_view_pin"), "new": fresh["attestation_view_pin"]},
            "exemplar_view_pin": {"old": old_binding.get("exemplar_view_pin"), "new": fresh["exemplar_view_pin"]},
            "graph_sha256_provenance": fresh["graph_sha256_provenance"],
            "snapshot_ref": snapshot.relative_to(harness).as_posix(),
        }
        event_bytes = (
            json.dumps(ledger_row, sort_keys=True, ensure_ascii=False) + "\n"
        ).encode("utf-8")
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_bytes(event_bytes)
        receipt = stage / "receipt.json"
        request = {
            "request_id": "real-validator-fixture",
            "schema_version": "reader-semantic-activation.v1",
            "operation": "reader_profile_v2_to_semantic",
            "phase_state_sha256": hashlib.sha256(state_bytes).hexdigest(),
            "prior_binding_sha256": hashlib.sha256(amt._json_bytes(old_binding)).hexdigest(),
            "prior_resolved_sha256": old_binding["resolved_sha256"],
            "pin_epoch": 2, "profile_sha256": fresh["profile_sha256"],
            "attestation_view_pin": fresh["attestation_view_pin"],
            "exemplar_view_pin": fresh["exemplar_view_pin"],
            "delta_class": "corpus",
            "repin_log_ref": "references/policies/repin_log.jsonl#epoch-2",
            "repin_event_sha256": hashlib.sha256(event_bytes).hexdigest(),
            "repin_ledger_sha256": hashlib.sha256(event_bytes).hexdigest(),
            "repin_snapshot_ref": snapshot.relative_to(harness).as_posix(),
            "repin_snapshot_sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(),
            "graph_path": graph_relative,
            "graph_sha256": fresh["graph_sha256_provenance"],
            "qualification_receipt_path": receipt.relative_to(wiki).as_posix(),
            "qualification_receipt_sha256": hashlib.sha256(receipt.read_bytes()).hexdigest(),
            "status": "pending",
        }
        request_path = project / "reviews/repin_rebind_request.json"
        request_path.write_bytes(amt._json_bytes(request))
        def resolve_temp_policy(project_root: Path | None, **_kwargs):
            return original_resolve(
                project_root, profile_path=profile_path, wiki_root=wiki,
                workspace_root=workspace, harness_root=harness,
            )

        policy.resolve_policy = resolve_temp_policy
        original_validator_resolve = milestone_validator.resolve_policy
        original_validator_root = milestone_validator.ROOT
        milestone_validator.resolve_policy = resolve_temp_policy
        milestone_validator.ROOT = harness
        try:
            archive = amt._activate_reader_profile_semantic(
                project, state_path, copy.deepcopy(state),
                hashlib.sha256(state_bytes).hexdigest(), copy.deepcopy(framework),
                copy.deepcopy(old_binding), request_path, "2026-08-08T23:59:59Z", policy,
            )
        finally:
            milestone_validator.ROOT = original_validator_root
            milestone_validator.resolve_policy = original_validator_resolve
            policy.resolve_policy = original_resolve
            policy.ROOT = original_root
        assert archive.is_file()


def main() -> int:
    parser = argparse.ArgumentParser()
    default = ROOT.parents[1] / "knowledge/LLM wiki/scripts/semantic_qualification.py"
    parser.add_argument("--qualification-script", type=Path, default=default)
    parser.add_argument(
        "--project-template", type=Path,
        default=ROOT.parents[1] / "research/60_Workbench/2026-07-27_augmented-selves-paper2",
    )
    args = parser.parse_args()
    with semantic_graph_fixture_environment():
        run(args.qualification_script, args.project_template.resolve())
    print("semantic_qualification_consumer_smoketest: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
