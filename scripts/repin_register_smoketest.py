#!/usr/bin/env python3
"""Contract smoke tests for the deliberate domain-register re-pin workflow.

This is the authoritative home for the nine acceptance criteria in
``docs/analysis/2026-07-14_repin-skill-proposal.md`` section 9.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import domain_native_register_smoketest as dnr_fixture
import milestone_framework_smoketest as milestone_fixture
import milestone_framework_validate as milestone_validator
import reader_accessibility_policy as policy
import check8_h_prefilter
import reader_accessibility_candidates


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def fixture(root: Path) -> tuple[Path, Path, Path, Path]:
    """Create a package-local profile and real graph/wiki fixture."""
    harness = root / "harness"
    profile_path = harness / "references/policies/reader_accessibility.v1.json"
    schema_path = harness / "references/schemas/reader_accessibility_profile.schema.json"
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path.write_bytes((ROOT / "references/schemas/reader_accessibility_profile.schema.json").read_bytes())
    profile = policy.load_profile()
    # Hermetic baseline: strip post-release ingestions (argument-only members) and
    # reset version so fixture cases are independent of live re-pin history.
    dnr = profile["domain_native_register"]
    dnr["exemplar_members"] = [m for m in dnr["exemplar_members"] if m.get("warrant_scope", "both") == "both"]
    profile["profile_version"] = "1.0.0"
    write_json(profile_path, profile)
    wiki, workspace = dnr_fixture.write_fixture(root / "corpus")
    current = policy.resolve_domain_native_register(
        profile, wiki_root=wiki, workspace_root=workspace, harness_root=harness
    )
    expected = profile["domain_native_register"]["expected_verification"]
    expected.update(
        attestation_view_pin=current["attestation_view_pin"],
        exemplar_view_pin=current["exemplar_view_pin"],
        pin_epoch=1,
        pinned_at="2026-07-14T00:00:00Z",
    )
    profile["domain_native_register"]["corpus_binding"]["graph"][
        "observed_sha256_at_review"
    ] = current["graph_sha256_provenance"]
    write_json(profile_path, profile)
    return harness, profile_path, wiki, workspace


def invoke(
    harness: Path,
    profile_path: Path,
    wiki: Path,
    workspace: Path,
    *extra: str,
    answer: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/reader_accessibility_policy.py"),
            "--repin",
            "--harness-root",
            str(harness),
            "--profile",
            str(profile_path),
            "--wiki-root",
            str(wiki),
            "--workspace-root",
            str(workspace),
            *extra,
        ],
        input=answer,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def rows(harness: Path) -> list[dict]:
    path = harness / "references/policies/repin_log.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def initialize_main_commit(repository: Path) -> str:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repository, check=True)
    subprocess.run(["git", "config", "user.name", "fixture"], cwd=repository, check=True)
    subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=repository, check=True)
    subprocess.run(["git", "add", "."], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture repin"], cwd=repository, check=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repository, check=True,
        capture_output=True, text=True, encoding="utf-8", errors="strict",
    ).stdout.strip()


def case_no_delta() -> None:
    with tempfile.TemporaryDirectory() as td:
        harness, profile_path, wiki, workspace = fixture(Path(td))
        before = profile_path.read_bytes()
        result = invoke(harness, profile_path, wiki, workspace)
        assert result.returncode == 0, result.stdout + result.stderr
        assert profile_path.read_bytes() == before
        ledger = rows(harness)
        assert len(ledger) == 1 and ledger[0]["delta_class"] == "none"
        assert ledger[0]["attestation_view_pin"] == {"old": None, "new": None}
        assert ledger[0]["exemplar_view_pin"] == {"old": None, "new": None}
        try:
            policy.backfill_repin_commit(harness, ledger[0]["epoch"], "a" * 40)
        except policy.PolicyError as exc:
            assert "existing commit" in str(exc) or "git worktree" in str(exc)
        else:
            raise AssertionError("nonexistent commit was accepted for re-pin backfill")
        approved_commit = initialize_main_commit(harness)
        policy.backfill_repin_commit(harness, ledger[0]["epoch"], approved_commit)
        assert rows(harness)[0]["commit"] == approved_commit


def case_graph_semantic_eligibility() -> None:
    mutations = (
        ("missing metadata", lambda graph: graph.pop("graph"), "metadata object is required"),
        ("missing extraction mode", lambda graph: graph["graph"].pop("extraction_mode"), "extraction_mode"),
        ("structural only", lambda graph: graph["graph"].update(extraction_mode="structural-only"), "structural-only"),
        ("missing semantic status", lambda graph: graph["graph"].pop("semantic_status"), "semantic_status"),
        ("semantic pending", lambda graph: graph["graph"].update(semantic_status="pending"), "pending"),
        ("missing semantic scope", lambda graph: graph["graph"].pop("semantic_scope"), "semantic_scope"),
        ("missing manifest", lambda graph: graph["graph"].pop("semantic_manifest"), "semantic_manifest"),
        ("missing output digest", lambda graph: graph["graph"].pop("semantic_outputs_sha256"), "semantic_outputs_sha256"),
        ("missing output list", lambda graph: graph["graph"].pop("semantic_output_files"), "semantic_output_files"),
        ("missing inventory digest", lambda graph: graph["graph"].pop("research_inventory_sha256"), "research_inventory_sha256"),
        ("duplicate output path", lambda graph: graph["graph"]["semantic_output_files"].append(copy.deepcopy(graph["graph"]["semantic_output_files"][0])), "invalid or duplicate"),
        ("missing report", lambda graph: graph["graph"].pop("semantic_report"), "semantic_report"),
        ("missing receipt", lambda graph: graph["graph"].pop("semantic_receipt"), "semantic_receipt"),
        ("count mismatch", lambda graph: graph["graph"].update(semantic_edge_count=2), "semantic_edge_count"),
        ("tiny tagged scope", lambda graph: graph["graph"].update(semantic_scope="one page", semantic_pages_expected=265, semantic_pages_represented=1), "semantic_pages"),
    )
    for label, mutate, needle in mutations:
        with tempfile.TemporaryDirectory() as td:
            harness, profile_path, wiki, workspace = fixture(Path(td))
            graph_path = workspace / "knowledge/LLM wiki/graphify-out/graph.json"
            graph = json.loads(graph_path.read_text(encoding="utf-8"))
            mutate(graph)
            write_json(graph_path, graph)
            result = invoke(harness, profile_path, wiki, workspace, "--dry-run")
            output = result.stdout + result.stderr
            assert result.returncode != 0, f"{label} graph passed semantic eligibility"
            assert "GRAPH-SEMANTIC-INELIGIBLE" in output and needle in output, output
            assert not (harness / "references/policies/repin_log.jsonl").exists()
            snapshots = harness / "reviews/.harness/repin"
            assert not snapshots.exists() or not list(snapshots.glob("*.snapshot.json"))


def case_graph_semantic_artifact_integrity() -> None:
    cases = ("receipt_hash", "manifest_hash", "output_hash", "synchronized_schema_drift", "non_object_receipt", "non_object_manifest", "non_object_audit", "arbitrary_output", "audit_output_binding", "audit_reviewer", "audit_reviewer_counts", "audit_unknown_edge", "unaudited_seed_edge", "page_set", "seed_coverage")
    for case in cases:
        with tempfile.TemporaryDirectory() as td:
            harness, profile_path, wiki, workspace = fixture(Path(td))
            graph_path = workspace / "knowledge/LLM wiki/graphify-out/graph.json"
            if case == "receipt_hash":
                receipt_path = wiki / "graphify-out/fixture-receipt.json"
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                receipt["final_graph_sha256"] = "0" * 64
                write_json(receipt_path, receipt)
                needle = "receipt final_graph_sha256 mismatch"
            elif case == "manifest_hash":
                manifest_path = wiki / "graphify-out/fixture-manifest.json"
                manifest_path.write_bytes(manifest_path.read_bytes() + b" ")
                needle = "manifest hash mismatch"
            elif case == "output_hash":
                graph = json.loads(graph_path.read_text(encoding="utf-8"))
                output_path = wiki / graph["graph"]["semantic_output_files"][0]["path"]
                output_path.write_bytes(output_path.read_bytes() + b" ")
                needle = "semantic output hash mismatch"
            elif case == "synchronized_schema_drift":
                graph = json.loads(graph_path.read_text(encoding="utf-8"))
                metadata = graph["graph"]
                manifest_path = wiki / metadata["semantic_manifest"]
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest["schema_version"] = "9.9.9"
                write_json(manifest_path, manifest)
                metadata["semantic_manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
                for output_row in metadata["semantic_output_files"]:
                    output_path = wiki / output_row["path"]
                    output = json.loads(output_path.read_text(encoding="utf-8"))
                    output["schema_version"] = "9.9.9"
                    write_json(output_path, output)
                    output_row["sha256"] = hashlib.sha256(output_path.read_bytes()).hexdigest()
                output_payload = "\n".join(f"{row['path']}\t{row['sha256']}" for row in metadata["semantic_output_files"]).encode("utf-8")
                metadata["semantic_outputs_sha256"] = hashlib.sha256(output_payload).hexdigest()
                audit_path = wiki / metadata["semantic_audit"]
                audit = json.loads(audit_path.read_text(encoding="utf-8"))
                audit.update(schema_version="9.9.9", manifest_sha256=metadata["semantic_manifest_sha256"], semantic_outputs_sha256=metadata["semantic_outputs_sha256"])
                write_json(audit_path, audit)
                metadata["semantic_audit_sha256"] = hashlib.sha256(audit_path.read_bytes()).hexdigest()
                write_json(graph_path, graph)
                receipt_path = wiki / metadata["semantic_receipt"]
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                receipt.update(schema_version="9.9.9", manifest_sha256=metadata["semantic_manifest_sha256"], audit_sha256=metadata["semantic_audit_sha256"], semantic_outputs_sha256=metadata["semantic_outputs_sha256"], final_graph_sha256=hashlib.sha256(graph_path.read_bytes()).hexdigest())
                write_json(receipt_path, receipt)
                needle = "semantic receipt schema_version is unsupported"
            elif case == "non_object_receipt":
                graph = json.loads(graph_path.read_text(encoding="utf-8"))
                write_json(wiki / graph["graph"]["semantic_receipt"], [])
                needle = "semantic receipt must be a JSON object"
            elif case == "non_object_manifest":
                graph = json.loads(graph_path.read_text(encoding="utf-8"))
                metadata = graph["graph"]
                manifest_path = wiki / metadata["semantic_manifest"]
                write_json(manifest_path, [])
                metadata["semantic_manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
                write_json(graph_path, graph)
                receipt_path = wiki / metadata["semantic_receipt"]
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                receipt.update(manifest_sha256=metadata["semantic_manifest_sha256"], final_graph_sha256=hashlib.sha256(graph_path.read_bytes()).hexdigest())
                write_json(receipt_path, receipt)
                needle = "semantic manifest and audit must be JSON objects"
            elif case == "non_object_audit":
                graph = json.loads(graph_path.read_text(encoding="utf-8"))
                metadata = graph["graph"]
                audit_path = wiki / metadata["semantic_audit"]
                write_json(audit_path, [])
                metadata["semantic_audit_sha256"] = hashlib.sha256(audit_path.read_bytes()).hexdigest()
                write_json(graph_path, graph)
                receipt_path = wiki / metadata["semantic_receipt"]
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                receipt.update(audit_sha256=metadata["semantic_audit_sha256"], final_graph_sha256=hashlib.sha256(graph_path.read_bytes()).hexdigest())
                write_json(receipt_path, receipt)
                needle = "semantic manifest and audit must be JSON objects"
            elif case == "arbitrary_output":
                graph = json.loads(graph_path.read_text(encoding="utf-8"))
                metadata = graph["graph"]
                output_path = wiki / metadata["semantic_output_files"][0]["path"]
                write_json(output_path, {"unrelated": "content"})
                metadata["semantic_output_files"][0]["sha256"] = hashlib.sha256(output_path.read_bytes()).hexdigest()
                payload = "\n".join(f"{row['path']}\t{row['sha256']}" for row in metadata["semantic_output_files"]).encode("utf-8")
                metadata["semantic_outputs_sha256"] = hashlib.sha256(payload).hexdigest()
                audit_path = wiki / metadata["semantic_audit"]
                audit = json.loads(audit_path.read_text(encoding="utf-8"))
                audit["semantic_outputs_sha256"] = metadata["semantic_outputs_sha256"]
                write_json(audit_path, audit)
                metadata["semantic_audit_sha256"] = hashlib.sha256(audit_path.read_bytes()).hexdigest()
                write_json(graph_path, graph)
                receipt_path = wiki / metadata["semantic_receipt"]
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                receipt.update(semantic_outputs_sha256=metadata["semantic_outputs_sha256"], audit_sha256=metadata["semantic_audit_sha256"], final_graph_sha256=hashlib.sha256(graph_path.read_bytes()).hexdigest())
                write_json(receipt_path, receipt)
                needle = "semantic output schema/chunk/page count mismatch"
            elif case == "audit_output_binding":
                graph = json.loads(graph_path.read_text(encoding="utf-8"))
                audit_path = wiki / graph["graph"]["semantic_audit"]
                audit = json.loads(audit_path.read_text(encoding="utf-8"))
                audit["semantic_outputs_sha256"] = "0" * 64
                write_json(audit_path, audit)
                graph["graph"]["semantic_audit_sha256"] = hashlib.sha256(audit_path.read_bytes()).hexdigest()
                write_json(graph_path, graph)
                receipt_path = wiki / graph["graph"]["semantic_receipt"]
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                receipt["audit_sha256"] = graph["graph"]["semantic_audit_sha256"]
                receipt["final_graph_sha256"] = hashlib.sha256(graph_path.read_bytes()).hexdigest()
                write_json(receipt_path, receipt)
                needle = "semantic audit output binding mismatch"
            elif case in {"audit_reviewer", "audit_reviewer_counts"}:
                graph = json.loads(graph_path.read_text(encoding="utf-8"))
                audit_path = wiki / graph["graph"]["semantic_audit"]
                audit = json.loads(audit_path.read_text(encoding="utf-8"))
                if case == "audit_reviewer":
                    audit.update(reviewer="Unapproved", reviewers=["Unapproved"], reviewer_counts={"Unapproved": len(audit["edges"])})
                    for row in audit["edges"]:
                        row["reviewer"] = "Unapproved"
                    needle = "semantic audit reviewer provenance is invalid"
                else:
                    audit["reviewer_counts"]["Codex"] += 1
                    needle = "semantic audit row reviewer provenance mismatch"
                write_json(audit_path, audit)
                graph["graph"]["semantic_audit_sha256"] = hashlib.sha256(audit_path.read_bytes()).hexdigest()
                write_json(graph_path, graph)
                receipt_path = wiki / graph["graph"]["semantic_receipt"]
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                receipt["audit_sha256"] = graph["graph"]["semantic_audit_sha256"]
                receipt["final_graph_sha256"] = hashlib.sha256(graph_path.read_bytes()).hexdigest()
                write_json(receipt_path, receipt)
            elif case == "page_set":
                graph = json.loads(graph_path.read_text(encoding="utf-8"))
                next(node for node in graph["nodes"] if node.get("id") == "sem_fixture_yu")["source_file"] = "wiki/sources/import.md"
                write_json(graph_path, graph)
                receipt_path = wiki / graph["graph"]["semantic_receipt"]
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                receipt["final_graph_sha256"] = hashlib.sha256(graph_path.read_bytes()).hexdigest()
                write_json(receipt_path, receipt)
                needle = "semantic output node payload differs from graph"
            elif case == "audit_unknown_edge":
                graph = json.loads(graph_path.read_text(encoding="utf-8"))
                audit_path = wiki / graph["graph"]["semantic_audit"]
                audit = json.loads(audit_path.read_text(encoding="utf-8"))
                audit["edges"][0]["semantic_edge_id"] = "fixture:forged"
                write_json(audit_path, audit)
                graph["graph"]["semantic_audit_sha256"] = hashlib.sha256(audit_path.read_bytes()).hexdigest()
                write_json(graph_path, graph)
                receipt_path = wiki / graph["graph"]["semantic_receipt"]
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                receipt["audit_sha256"] = graph["graph"]["semantic_audit_sha256"]
                receipt["final_graph_sha256"] = hashlib.sha256(graph_path.read_bytes()).hexdigest()
                write_json(receipt_path, receipt)
                needle = "semantic audit references unknown graph edges"
            elif case == "unaudited_seed_edge":
                graph = json.loads(graph_path.read_text(encoding="utf-8"))
                graph["nodes"].append({"id":"sem_fixture_yu_extra","community":5,"label":"fixture yu extra","file_type":"claim","source_file":"wiki/sources/yu-1995-istar.md","source_location":"fixture","semantic_status":"validated","extraction_status":"semantic"})
                graph["links"].append({"source":"yu-1995-istar","target":"sem_fixture_yu_extra","_src":"yu-1995-istar","_tgt":"sem_fixture_yu_extra","semantic_edge_id":"fixture:yu-extra","semantic_status":"validated","relation":"supports","confidence":"INFERRED","confidence_score":0.8,"source_file":"wiki/sources/yu-1995-istar.md","source_location":"fixture","weight":1.0,"evidence":"fixture"})
                write_json(graph_path, graph)
                dnr_fixture.refresh_semantic_fixture(wiki, graph_path)
                graph = json.loads(graph_path.read_text(encoding="utf-8"))
                audit_path = wiki / graph["graph"]["semantic_audit"]
                audit = json.loads(audit_path.read_text(encoding="utf-8"))
                audit["edges"] = [row for row in audit["edges"] if row["semantic_edge_id"] != "fixture:yu-extra"]
                audit["sample_count"] = len(audit["edges"])
                audit["verdict_counts"]["supported"] = len(audit["edges"])
                audit["reviewer_counts"]["Codex"] = len(audit["edges"])
                write_json(audit_path, audit)
                graph["graph"]["semantic_audit_sha256"] = hashlib.sha256(audit_path.read_bytes()).hexdigest()
                write_json(graph_path, graph)
                receipt_path = wiki / graph["graph"]["semantic_receipt"]
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                receipt.update(audit_sha256=graph["graph"]["semantic_audit_sha256"], audit_sample_count=len(audit["edges"]), final_graph_sha256=hashlib.sha256(graph_path.read_bytes()).hexdigest())
                write_json(receipt_path, receipt)
                needle = "semantic audit sample differs from page/seed/class policy"
            else:
                graph = json.loads(graph_path.read_text(encoding="utf-8"))
                graph["nodes"] = [node for node in graph["nodes"] if node.get("id") != "sem_fixture_yu"]
                graph["links"] = [edge for edge in graph["links"] if edge.get("semantic_edge_id") != "fixture:yu"]
                write_json(graph_path, graph)
                dnr_fixture.refresh_semantic_fixture(wiki, graph_path)
                needle = "resolved register seed lacks semantic node/edge coverage"
            result = invoke(harness, profile_path, wiki, workspace, "--dry-run")
            output = result.stdout + result.stderr
            assert result.returncode != 0 and "GRAPH-SEMANTIC-INELIGIBLE" in output and needle in output, f"{case}: {output}"
            assert not (harness / "references/policies/repin_log.jsonl").exists()


def case_delta_apply() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        harness, profile_path, wiki, workspace = fixture(root)
        project = root / "project"
        phase_state = project / "reviews/phase_state.json"
        write_json(phase_state, {"sentinel": "Planner-only"})
        phase_state_before = phase_state.read_bytes()
        graph = workspace / "knowledge/LLM wiki/graphify-out/graph.json"
        value = json.loads(graph.read_text(encoding="utf-8"))
        value["nodes"].append({"id": "repin-new", "community": 5, "file_type": "concept", "source_file": "wiki/sources/import.md"})
        write_json(graph, value)
        dnr_fixture.refresh_semantic_fixture(wiki, graph)
        result = invoke(harness, profile_path, wiki, workspace, answer="yes\n")
        assert result.returncode == 0, result.stdout + result.stderr
        report = json.loads(result.stdout)
        for key in ("resolved_seed_count", "primary_communities", "degeneracy_warning", "unresolved_seed_ids", "membership", "exemplar_tuples_changed"):
            assert key in report["delta_report"]
        updated = json.loads(profile_path.read_text(encoding="utf-8"))
        expected = updated["domain_native_register"]["expected_verification"]
        assert updated["profile_version"] == "1.0.1" and expected["pin_epoch"] == 2
        row = rows(harness)[0]
        assert row["delta_class"] in {"attestation", "both"}
        assert (harness / row["snapshot_ref"]).is_file()
        assert report["read_back_verified"] is True
        project_phase = invoke(harness, profile_path, wiki, workspace, "--project-root", str(project))
        assert project_phase.returncode == 0, project_phase.stdout + project_phase.stderr
        request = json.loads((project / "reviews/repin_rebind_request.json").read_text(encoding="utf-8"))
        assert request["status"] == "pending" and request["pin_epoch"] == expected["pin_epoch"]
        assert phase_state.read_bytes() == phase_state_before, "re-pin workflow wrote Planner-owned phase_state.json"
        request_before = (project / "reviews/repin_rebind_request.json").read_bytes()
        retry = invoke(harness, profile_path, wiki, workspace, "--project-root", str(project))
        assert retry.returncode == 0, retry.stdout + retry.stderr
        assert json.loads(retry.stdout)["request_reused"] is True
        assert (project / "reviews/repin_rebind_request.json").read_bytes() == request_before
        write_json(phase_state, {"sections": {"intro": {"phase_entry_log": [{"trigger": "ph3_iteration_round"}]}}})
        refused = invoke(harness, profile_path, wiki, workspace, "--project-root", str(project))
        assert refused.returncode != 0 and "open round" in refused.stdout.lower()
        assert (project / "reviews/repin_rebind_request.json").read_bytes() == request_before


def case_rebind_transaction_rollback() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        harness, profile_path, wiki, workspace = fixture(root)
        project = root / "project"
        write_json(project / "reviews/phase_state.json", {"sentinel": "Planner-only"})
        request_path = project / "reviews/repin_rebind_request.json"
        write_json(request_path, {"request_id": "incompatible", "status": "pending", "pin_epoch": 999})
        request_before = request_path.read_bytes()
        profile_before = profile_path.read_bytes()
        graph = workspace / "knowledge/LLM wiki/graphify-out/graph.json"
        value = json.loads(graph.read_text(encoding="utf-8"))
        value["nodes"].append({"id": "rollback-new", "community": 5, "file_type": "concept", "source_file": "wiki/sources/import.md"})
        write_json(graph, value)
        dnr_fixture.refresh_semantic_fixture(wiki, graph)
        refused = invoke(harness, profile_path, wiki, workspace, "--project-root", str(project), answer="yes\n")
        assert refused.returncode != 0 and "different rebind request" in (refused.stdout + refused.stderr).lower()
        assert profile_path.read_bytes() == profile_before
        assert request_path.read_bytes() == request_before
        assert not (harness / "references/policies/repin_log.jsonl").exists()
        assert not (harness / "references/policies/repin_log.md").exists()
        snapshots = harness / "reviews/.harness/repin"
        assert not snapshots.exists() or not list(snapshots.glob("*.snapshot.json"))

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        harness, profile_path, wiki, workspace = fixture(root)
        project = root / "project"
        write_json(project / "reviews/phase_state.json", {"sentinel": "Planner-only"})
        profile_before = profile_path.read_bytes()
        graph = workspace / "knowledge/LLM wiki/graphify-out/graph.json"
        value = json.loads(graph.read_text(encoding="utf-8"))
        value["nodes"].append({"id": "publication-freshness-new", "community": 5, "file_type": "concept", "source_file": "wiki/sources/import.md"})
        write_json(graph, value)
        dnr_fixture.refresh_semantic_fixture(wiki, graph)
        request_path = project / "reviews/repin_rebind_request.json"
        original_atomic_create = policy._atomic_create_bytes

        def mutate_inventory_after_publication(path: Path, payload: bytes) -> None:
            original_atomic_create(path, payload)
            if path == request_path:
                page = wiki / "wiki/sources/yu-1995-istar.md"
                page.write_bytes(page.read_bytes() + b"publication-time mutation\n")

        policy._atomic_create_bytes = mutate_inventory_after_publication
        try:
            policy.run_repin(
                harness_root=harness, profile_path=profile_path,
                wiki_root=wiki, workspace_root=workspace, project_root=project,
                trigger="manual", dry_run=False, allow_unrelated_dirty=False,
                force_lock=False, add_exemplar=None, drop_exemplar=None,
                role=None, warrant_scope=None, confirm_drop_locked_role=False,
                confirm=lambda _: True,
            )
        except policy.PolicyError as exc:
            assert ("inventory" in str(exc).lower() or "changed" in str(exc).lower()) and "archive" in str(exc).lower()
        else:
            raise AssertionError("inventory mutation during request publication returned READY")
        finally:
            policy._atomic_create_bytes = original_atomic_create
        assert request_path.is_file(), "published request was destructively removed during rollback"
        assert profile_path.read_bytes() == profile_before
        stale_request = json.loads(request_path.read_text(encoding="utf-8"))
        old_profile = json.loads(profile_before)
        old_epoch = old_profile["domain_native_register"]["expected_verification"]["pin_epoch"]
        old_profile_hash = hashlib.sha256(profile_before).hexdigest()
        assert milestone_validator.policy_epoch_findings(
            {"pin_epoch": old_epoch}, old_epoch, stale_request,
            opening_new_cycle=True, current_profile_sha256=old_profile_hash,
        ) == [], "rolled-back request remained an active pending rebind"
        assert not (harness / "references/policies/repin_log.jsonl").exists()
        assert not (harness / "references/policies/repin_log.md").exists()
        snapshots = harness / "reviews/.harness/repin"
        assert not snapshots.exists() or not list(snapshots.glob("*.snapshot.json"))

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        harness, profile_path, wiki, workspace = fixture(root)
        graph = workspace / "knowledge/LLM wiki/graphify-out/graph.json"
        value = json.loads(graph.read_text(encoding="utf-8"))
        value["nodes"].append({"id": "cleanup-status-new", "community": 5, "file_type": "concept", "source_file": "wiki/sources/import.md"})
        write_json(graph, value)
        dnr_fixture.refresh_semantic_fixture(wiki, graph)
        original_release_graph_boundary = policy._release_graph_boundary

        def lose_graph_lock_ownership(path: Path, payload: bytes) -> None:
            path.write_bytes(b"foreign graph lock ownership\n")
            original_release_graph_boundary(path, payload)

        policy._release_graph_boundary = lose_graph_lock_ownership
        try:
            committed = policy.run_repin(
                harness_root=harness, profile_path=profile_path,
                wiki_root=wiki, workspace_root=workspace, project_root=None,
                trigger="manual", dry_run=False, allow_unrelated_dirty=False,
                force_lock=False, add_exemplar=None, drop_exemplar=None,
                role=None, warrant_scope=None, confirm_drop_locked_role=False,
                confirm=lambda _: True,
            )
        finally:
            policy._release_graph_boundary = original_release_graph_boundary
        assert committed["status"] == "COMMITTED_CLEANUP_REQUIRED"
        assert committed["applied"] is True and committed["cleanup_errors"]
        assert json.loads(profile_path.read_text(encoding="utf-8"))["profile_version"] == "1.0.1"
        assert rows(harness) and (harness / rows(harness)[-1]["snapshot_ref"]).is_file()

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        harness, profile_path, wiki, workspace = fixture(root)
        project = root / "project"
        write_json(project / "reviews/phase_state.json", {"sentinel": "Planner-only"})
        profile_before = profile_path.read_bytes()
        graph = workspace / "knowledge/LLM wiki/graphify-out/graph.json"
        value = json.loads(graph.read_text(encoding="utf-8"))
        value["nodes"].append({"id": "ownership-new", "community": 5, "file_type": "concept", "source_file": "wiki/sources/import.md"})
        write_json(graph, value)
        dnr_fixture.refresh_semantic_fixture(wiki, graph)
        request_path = project / "reviews/repin_rebind_request.json"
        foreign_request = b'{"request_id":"foreign-owner","status":"pending"}\n'
        original_atomic_create = policy._atomic_create_bytes

        def foreign_request_wins_create(path: Path, payload: bytes) -> None:
            if path == request_path:
                request_path.write_bytes(foreign_request)
                raise policy.PolicyError("destination appeared concurrently; refusing overwrite")
            original_atomic_create(path, payload)

        policy._atomic_create_bytes = foreign_request_wins_create
        try:
            policy.run_repin(
                harness_root=harness, profile_path=profile_path,
                wiki_root=wiki, workspace_root=workspace, project_root=project,
                trigger="manual", dry_run=False, allow_unrelated_dirty=False,
                force_lock=False, add_exemplar=None, drop_exemplar=None,
                role=None, warrant_scope=None, confirm_drop_locked_role=False,
                confirm=lambda _: True,
            )
        except policy.PolicyError as exc:
            assert "destination appeared" in str(exc).lower()
        else:
            raise AssertionError("foreign rebind request replacement was silently accepted")
        finally:
            policy._atomic_create_bytes = original_atomic_create
        assert request_path.read_bytes() == foreign_request
        assert profile_path.read_bytes() == profile_before
        assert not (harness / "references/policies/repin_log.jsonl").exists()
        assert not (harness / "references/policies/repin_log.md").exists()
        snapshots = harness / "reviews/.harness/repin"
        assert not snapshots.exists() or not list(snapshots.glob("*.snapshot.json"))

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        harness, profile_path, wiki, workspace = fixture(root)
        project = root / "project"
        write_json(project / "reviews/phase_state.json", {"sentinel": "Planner-only"})
        profile_before = profile_path.read_bytes()
        graph = workspace / "knowledge/LLM wiki/graphify-out/graph.json"
        value = json.loads(graph.read_text(encoding="utf-8"))
        value["nodes"].append({"id": "freshness-new", "community": 5, "file_type": "concept", "source_file": "wiki/sources/import.md"})
        write_json(graph, value)
        dnr_fixture.refresh_semantic_fixture(wiki, graph)
        original_open_project_round = policy._open_project_round

        def mutate_inventory_during_request(_: Path) -> bool:
            page = wiki / "wiki/sources/yu-1995-istar.md"
            page.write_bytes(page.read_bytes() + b"late mutation\n")
            return False

        policy._open_project_round = mutate_inventory_during_request
        try:
            policy.run_repin(
                harness_root=harness, profile_path=profile_path,
                wiki_root=wiki, workspace_root=workspace, project_root=project,
                trigger="manual", dry_run=False, allow_unrelated_dirty=False,
                force_lock=False, add_exemplar=None, drop_exemplar=None,
                role=None, warrant_scope=None, confirm_drop_locked_role=False,
                confirm=lambda _: True,
            )
        except policy.PolicyError as exc:
            assert "inventory" in str(exc).lower() or "changed" in str(exc).lower()
        else:
            raise AssertionError("inventory change during request publication was applied")
        finally:
            policy._open_project_round = original_open_project_round
        assert profile_path.read_bytes() == profile_before
        assert not (project / "reviews/repin_rebind_request.json").exists()
        assert not (harness / "references/policies/repin_log.jsonl").exists()
        assert not (harness / "references/policies/repin_log.md").exists()
        snapshots = harness / "reviews/.harness/repin"
        assert not snapshots.exists() or not list(snapshots.glob("*.snapshot.json"))


def case_epoch_softening() -> None:
    binding = {"pin_epoch": 1}
    request = {"status": "pending", "pin_epoch": 2}
    assert milestone_validator.policy_epoch_findings(binding, 2, request, opening_new_cycle=False) == []
    assert milestone_validator.policy_epoch_findings(binding, 2, request, opening_new_cycle=True) == ["MF-POLICY-PIN-EPOCH-STALE"]
    rebound = {"pin_epoch": 2}
    assert milestone_validator.policy_epoch_findings(rebound, 2, request, opening_new_cycle=True) == ["MF-POLICY-PIN-EPOCH-STALE"]
    assert milestone_validator.policy_epoch_findings(binding, 2, None, opening_new_cycle=True) == ["MF-POLICY-PIN-EPOCH-STALE"]
    assert milestone_validator.policy_epoch_findings(rebound, 2, None, opening_new_cycle=True) == []

    # Exercise the actual milestone validator, not only its reason-code helper.
    with tempfile.TemporaryDirectory() as td:
        project = Path(td) / "project"
        ledger = milestone_fixture._materialize_native_project(project)
        document = milestone_fixture._phase_document(ledger, "Ph4")
        bound_epoch = ledger["policy_bindings"]["reader_accessibility"]["pin_epoch"]
        binding = ledger["policy_bindings"]["reader_accessibility"]
        write_json(project / "reviews/repin_rebind_request.json", {
            "request_id": "fixture-request",
            "status": "pending",
            "pin_epoch": bound_epoch,
            "profile_sha256": binding["profile_sha256"],
            "attestation_view_pin": binding["attestation_view_pin"],
            "exemplar_view_pin": binding["exemplar_view_pin"],
            "delta_class": "attestation",
            "repin_log_ref": f"references/policies/repin_log.jsonl#epoch-{bound_epoch}",
        })
        continuing = milestone_validator.validate_document(
            project, copy.deepcopy(document), opening_new_cycle=False,
        )
        assert "MF-POLICY-PIN-EPOCH-STALE" not in {finding.code for finding in continuing.findings}
        opening = milestone_validator.validate_document(
            project, copy.deepcopy(document), opening_new_cycle=True,
        )
        assert "MF-POLICY-PIN-EPOCH-STALE" in {finding.code for finding in opening.findings}
        (project / "reviews/repin_rebind_request.json").rename(
            project / f"reviews/repin_rebind_request.{bound_epoch}.applied.json"
        )
        rebound_opening = milestone_validator.validate_document(
            project, copy.deepcopy(document), opening_new_cycle=True,
        )
        assert "MF-POLICY-PIN-EPOCH-STALE" not in {finding.code for finding in rebound_opening.findings}

    # v0.28 bindings lack the v0.29 member projections. They remain valid for
    # a continuing cycle when both semantic pins are unchanged, but not for a
    # newly opened cycle under the changed package profile.
    with tempfile.TemporaryDirectory() as td:
        project = Path(td) / "legacy-binding"
        ledger = milestone_fixture._materialize_native_project(project)
        binding = ledger["policy_bindings"]["reader_accessibility"]
        for key in ("exemplar_members", "surface_exemplar_members", "argument_exemplar_members"):
            binding["register_provenance"].pop(key, None)
        stale_hash = "48400ad0881c54920ea43eebd53754ce3aff5763ef8d0a6f35cf1d4d73583e61"
        binding["profile_sha256"] = stale_hash
        for source in binding["source_bindings"]:
            if source.get("role") == "package_profile":
                source["sha256"] = stale_hash
        resolved_path = project / binding["resolved_path"]
        resolved = json.loads(resolved_path.read_text(encoding="utf-8"))
        resolved["profile_sha256"] = stale_hash
        for source in resolved["source_bindings"]:
            if source.get("role") == "package_profile":
                source["sha256"] = stale_hash
        for key in ("exemplar_members", "surface_exemplar_members", "argument_exemplar_members"):
            resolved["register_provenance"].pop(key, None)
        resolved["resolved_profile"]["domain_native_register"]["warrant_layers"].pop("role_scoping", None)
        write_json(resolved_path, resolved)
        binding["resolved_sha256"] = policy._hash(resolved_path)
        for record in ledger["milestones"].values():
            milestone_fixture._reset_milestone(record)
        ledger["events"] = []
        document = milestone_fixture._phase_document(ledger, "Ph1")
        continuing = milestone_validator.validate_document(project, copy.deepcopy(document), opening_new_cycle=False)
        assert continuing.outcome.value == "READY" and not continuing.findings, [
            (finding.code, finding.path, finding.message) for finding in continuing.findings
        ]
        opening = milestone_validator.validate_document(project, copy.deepcopy(document), opening_new_cycle=True)
        assert "MF-POLICY-PROFILE-STALE" in {finding.code for finding in opening.findings}
        binding["profile_sha256"] = "b" * 64
        forged = milestone_validator.validate_document(project, copy.deepcopy(document), opening_new_cycle=False)
        assert "MF-POLICY-PROFILE-STALE" in {finding.code for finding in forged.findings}


def case_reason_code_matrix() -> None:
    good = "a" * 64
    base = {"profile_sha256": good, "attestation_view_pin": good, "exemplar_view_pin": good, "pin_epoch": 2}
    conditions = {
        "MF-POLICY-PROFILE-STALE": ({**base, "profile_sha256": "b" * 64}, base, False),
        "MF-POLICY-ATTESTATION-PIN-STALE": ({**base, "attestation_view_pin": "b" * 64}, base, False),
        "MF-POLICY-EXEMPLAR-PIN-STALE": ({**base, "exemplar_view_pin": "b" * 64}, base, False),
        "MF-POLICY-PIN-EPOCH-STALE": ({**base, "pin_epoch": 1}, base, True),
    }
    for expected, (binding, current, new_cycle) in conditions.items():
        observed = milestone_validator.reader_policy_staleness_codes(binding, current, opening_new_cycle=new_cycle)
        assert observed == [expected], (expected, observed)


def case_scoped_dirty() -> None:
    pin_paths = policy.repin_pin_affecting_paths()
    pin, unrelated = policy.classify_repin_dirty_paths(["notes/todo.md"], pin_paths)
    assert not pin and unrelated == ["notes/todo.md"]
    assert policy.repin_dirty_refusal(pin, unrelated, allow_unrelated_dirty=False)
    assert policy.repin_dirty_refusal(pin, unrelated, allow_unrelated_dirty=True) is None
    pin, unrelated = policy.classify_repin_dirty_paths(["references/policies/reader_accessibility.v1.json"], pin_paths)
    assert policy.repin_dirty_refusal(pin, unrelated, allow_unrelated_dirty=True)
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        (repo / "notes").mkdir()
        (repo / "notes/todo.md").write_text("clean\n", encoding="utf-8")
        subprocess.run(["git", "add", "notes/todo.md"], cwd=repo, check=True)
        subprocess.run(["git", "-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture"], cwd=repo, check=True)
        (repo / "notes/todo.md").write_text("dirty\n", encoding="utf-8")
        assert policy._git_dirty_paths(repo) == ["notes/todo.md"]


def case_lock_and_prior_diff() -> None:
    with tempfile.TemporaryDirectory() as td:
        harness, profile_path, wiki, workspace = fixture(Path(td))
        lock = harness / "reviews/.repin.lock"
        write_json(lock, {"pid": os.getpid(), "host": "fixture", "started_at": "2099-01-01T00:00:00Z", "stale_after": 1800})
        fresh = invoke(harness, profile_path, wiki, workspace)
        assert fresh.returncode != 0 and "lock" in fresh.stdout.lower()
        forced_fresh = invoke(harness, profile_path, wiki, workspace, "--force-lock", answer="yes\n")
        assert forced_fresh.returncode != 0 and "active" in forced_fresh.stdout.lower()
        write_json(lock, {"pid": 1, "host": "fixture", "started_at": "2000-01-01T00:00:00Z", "stale_after": 1})
        stale = invoke(harness, profile_path, wiki, workspace)
        assert stale.returncode != 0 and "recovery" in stale.stdout.lower()
        forced = invoke(harness, profile_path, wiki, workspace, "--force-lock")
        assert forced.returncode != 0 and "confirmation" in forced.stdout.lower()
        token = policy._acquire_repin_lock(lock, force_lock=True, confirm=lambda _: True)
        try:
            try:
                policy._acquire_repin_lock(lock, force_lock=False, confirm=lambda _: False)
            except policy.PolicyError as exc:
                assert "lock" in str(exc).lower()
            else:
                raise AssertionError("exclusive lock admitted a second owner")
        finally:
            policy._release_repin_lock(lock, token)
        ownership = policy._acquire_repin_lock(lock, force_lock=False, confirm=lambda _: False)
        lock.write_bytes(b"replacement ownership\n")
        try:
            policy._release_repin_lock(lock, ownership)
        except policy.PolicyError as exc:
            assert "ownership changed" in str(exc)
        else:
            raise AssertionError("replaced re-pin lock ownership was silently released")
        assert lock.read_bytes() == b"replacement ownership\n"
        lock.unlink()
        assert policy.repin_prior_diff_refusal(["references/policies/repin_log.jsonl"])
    with tempfile.TemporaryDirectory() as td:
        wiki = Path(td) / "wiki"
        (wiki / "graphify-out").mkdir(parents=True)
        graph_lock = wiki / "graphify-out/.graph-write.lock"
        original_fsync = policy.os.fsync

        def fail_fsync(_: int) -> None:
            raise OSError("injected fsync failure")

        policy.os.fsync = fail_fsync
        try:
            try:
                policy._acquire_graph_boundary(wiki)
            except policy.PolicyError as exc:
                assert "acquisition failed" in str(exc)
            else:
                raise AssertionError("graph lock fsync failure was accepted")
        finally:
            policy.os.fsync = original_fsync
        assert not graph_lock.exists(), "failed graph lock acquisition stranded a lock"
        try:
            policy._acquire_graph_boundary(Path(td) / "missing-wiki")
        except policy.PolicyError as exc:
            assert "could not be created" in str(exc)
        else:
            raise AssertionError("missing graph lock parent leaked raw OSError or was accepted")
    with tempfile.TemporaryDirectory() as td:
        harness, profile_path, wiki, workspace = fixture(Path(td))
        initial = invoke(harness, profile_path, wiki, workspace)
        assert initial.returncode == 0, initial.stdout + initial.stderr
        approved_commit = initialize_main_commit(harness)
        original_release_repin_lock = policy._release_repin_lock

        def lose_repin_lock_ownership(path: Path, ownership: bytes) -> None:
            path.write_bytes(b"foreign repin lock ownership\n")
            original_release_repin_lock(path, ownership)

        policy._release_repin_lock = lose_repin_lock_ownership
        try:
            committed = policy.backfill_repin_commit(harness, 2, approved_commit)
        finally:
            policy._release_repin_lock = original_release_repin_lock
        assert committed["status"] == "COMMITTED_CLEANUP_REQUIRED"
        assert committed["commit"] == approved_commit and committed["cleanup_errors"]
        assert rows(harness)[0]["commit"] == approved_commit


def case_schema_first() -> None:
    with tempfile.TemporaryDirectory() as td:
        harness, profile_path, wiki, workspace = fixture(Path(td))
        schema_path = harness / "references/schemas/reader_accessibility_profile.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        expected = schema["properties"]["domain_native_register"]["properties"]["expected_verification"]
        expected["required"] = ["attestation_view_pin", "exemplar_view_pin"]
        expected["properties"].pop("pin_epoch", None)
        expected["properties"].pop("pinned_at", None)
        write_json(schema_path, schema)
        result = invoke(harness, profile_path, wiki, workspace)
        assert result.returncode != 0 and "schema migration" in result.stdout.lower()


def case_package_only() -> None:
    with tempfile.TemporaryDirectory() as td:
        harness, profile_path, wiki, workspace = fixture(Path(td))
        subprocess.run(["git", "init", "-q"], cwd=harness, check=True)
        subprocess.run(["git", "add", "-A"], cwd=harness, check=True)
        subprocess.run(
            ["git", "-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture"],
            cwd=harness, check=True,
        )
        result = invoke(harness, profile_path, wiki, workspace, "--dry-run")
        assert result.returncode == 0, result.stdout + result.stderr
        assert not list(harness.rglob("phase_state.json"))
        subprocess.run(["git", "add", "-A"], cwd=harness, check=True)
        subprocess.run(
            ["git", "-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "first repin"],
            cwd=harness, check=True,
        )
        ledger = harness / "references/policies/repin_log.jsonl"
        subprocess.run(["git", "mv", str(ledger), str(ledger.with_name("repin_log.saved.jsonl"))], cwd=harness, check=True)
        renamed = invoke(harness, profile_path, wiki, workspace, "--allow-unrelated-dirty")
        assert renamed.returncode != 0 and "repin_log.jsonl" in renamed.stdout
        assert not ledger.exists(), "refused staged-rename case recreated the canonical ledger"


def case_exemplar_ingestion() -> None:
    """Criterion 9: admission/drop gates, scope routing, and re-pin coupling."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        harness, profile_path, wiki, workspace = fixture(root)
        sources = wiki / "wiki/sources"

        missing = invoke(
            harness, profile_path, wiki, workspace,
            "--add-exemplar", "missing-work", "--role", "classic-halo",
        )
        assert missing.returncode != 0
        assert "page missing" in missing.stdout.lower() and "create" in missing.stdout.lower()

        (sources / "dennett-1988-intentional-stance.md").write_text(
            "---\ngrounding_status: read\n---\n", encoding="utf-8"
        )
        anti_alias = invoke(
            harness, profile_path, wiki, workspace,
            "--add-exemplar", "dennett-1987-intentional-stance", "--role", "intentional-root",
        )
        assert anti_alias.returncode != 0 and "page missing" in anti_alias.stdout.lower()

        (sources / "stub-work.md").write_text(
            "---\ngrounding_status: stub - awaiting read\n---\n", encoding="utf-8"
        )
        stub = invoke(
            harness, profile_path, wiki, workspace,
            "--add-exemplar", "stub-work", "--role", "classic-halo",
        )
        assert stub.returncode != 0 and "grounding" in stub.stdout.lower()

        conflicting = invoke(
            harness, profile_path, wiki, workspace,
            "--add-exemplar", "stub-work", "--role", "classic-halo",
            "--drop-exemplar", "yu-2024-nine-pivots",
        )
        assert conflicting.returncode != 0 and "mutually exclusive" in (conflicting.stdout + conflicting.stderr).lower()

        (sources / "other-centroid.md").write_text(
            "---\ngrounding_status: full-read\n---\n", encoding="utf-8"
        )
        second_centroid = invoke(
            harness, profile_path, wiki, workspace,
            "--add-exemplar", "other-centroid", "--role", "centroid",
        )
        assert second_centroid.returncode != 0 and "locked" in second_centroid.stdout.lower()

        (sources / "other-root.md").write_text(
            "---\ngrounding_status: full-read\n---\n", encoding="utf-8"
        )
        second_root = invoke(
            harness, profile_path, wiki, workspace,
            "--add-exemplar", "other-root", "--role", "intentional-root",
        )
        assert second_root.returncode != 0 and "locked" in second_root.stdout.lower()

        (sources / "dennett-1987-intentional-stance.md").write_text(
            "---\ngrounding_status: full-read\n---\n", encoding="utf-8"
        )
        explicit_both = invoke(
            harness, profile_path, wiki, workspace,
            "--add-exemplar", "dennett-1987-intentional-stance", "--role", "intentional-root",
            "--warrant-scope", "both",
        )
        assert explicit_both.returncode != 0 and "argument-only" in explicit_both.stdout.lower()

        locked_drop = invoke(
            harness, profile_path, wiki, workspace,
            "--drop-exemplar", "yu-1995-istar",
        )
        assert locked_drop.returncode != 0 and "--confirm-drop-locked-role" in locked_drop.stdout

        # A grounded, graph-distant source with no staged PDF is admitted with
        # both advisories; omitted intentional-root scope becomes argument-only.
        (sources / "dennett-1987-intentional-stance.md").write_text(
            "---\ngrounding_status: full-read\nsource_loc: raw/corpus/missing-dennett.pdf\n---\n",
            encoding="utf-8",
        )
        graph_path = workspace / "knowledge/LLM wiki/graphify-out/graph.json"
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
        graph["nodes"].append({
            "id": "dennett-1987-intentional-stance", "community": 99,
            "file_type": "document",
            "source_file": "wiki/sources/dennett-1987-intentional-stance.md",
        })
        graph["nodes"].append({"id":"sem_fixture_dennett","community":99,"label":"fixture Dennett claim","file_type":"claim","source_file":"wiki/sources/dennett-1987-intentional-stance.md","source_location":"fixture","semantic_status":"validated","extraction_status":"semantic"})
        graph["links"].append({"source":"dennett-1987-intentional-stance","target":"sem_fixture_dennett","_src":"dennett-1987-intentional-stance","_tgt":"sem_fixture_dennett","semantic_edge_id":"fixture:dennett","semantic_status":"validated","relation":"describes","confidence":"EXTRACTED","confidence_score":1.0,"source_file":"wiki/sources/dennett-1987-intentional-stance.md","source_location":"fixture","weight":1.0,"evidence":"fixture"})
        write_json(graph_path, graph)
        dnr_fixture.refresh_semantic_fixture(wiki, graph_path)
        added = invoke(
            harness, profile_path, wiki, workspace,
            "--add-exemplar", "dennett-1987-intentional-stance", "--role", "intentional-root",
            answer="yes\n",
        )
        assert added.returncode == 0, added.stdout + added.stderr
        report = json.loads(added.stdout)
        assert report["delta_class"] in {"exemplar", "both"}
        assert report["epoch"] == 2 and report["applied"] is True
        warning_codes = {row["code"] for row in report["warnings"]}
        assert {"RA-DNR-PDF-MISSING", "RA-DNR-COHERENCE"} <= warning_codes
        updated = json.loads(profile_path.read_text(encoding="utf-8"))
        member = next(
            item for item in updated["domain_native_register"]["exemplar_members"]
            if item["source_key"] == "dennett-1987-intentional-stance"
        )
        assert member["warrant_scope"] == "argument-only"
        row = rows(harness)[-1]
        assert row["delta_summary"]["exemplar_members_added"] == [{
            "source_key": "dennett-1987-intentional-stance",
            "warrant_scope": "argument-only",
        }]
        snapshot = json.loads((harness / row["snapshot_ref"]).read_text(encoding="utf-8"))
        assert "dennett-1987-intentional-stance\tfull-read\t-" in snapshot["exemplar_hash_lines"]
        resolved_member = next(
            item for item in snapshot["exemplar_members"]
            if item["source_key"] == "dennett-1987-intentional-stance"
        )
        assert resolved_member["warrant_scope"] == "argument-only"
        assert "dennett-1987-intentional-stance" not in {
            item["source_key"] for item in policy.surface_exemplar_members(updated)
        }
        assert "dennett-1987-intentional-stance" not in {
            item["source_key"] for item in check8_h_prefilter.surface_register_exemplars(updated)
        }
        h_bundle = check8_h_prefilter.analyse_passage(
            "This section shows the argument.", "fixture", False, updated,
            "contribution_clause", "binding",
        )
        assert "dennett-1987-intentional-stance" not in h_bundle.surface_warrant_source_keys
        project = root / "candidate-project"
        project.mkdir()
        manuscript = project / "paper.md"
        manuscript.write_text("# Introduction\n\nThis section shows the argument.\n", encoding="utf-8")
        register = policy.resolve_domain_native_register(
            updated, wiki_root=wiki, workspace_root=workspace, harness_root=harness,
        )
        resolved = {
            "resolved_profile": updated,
            "profile_path": "references/policies/reader_accessibility.v1.json",
            "profile_sha256": policy._hash(profile_path),
            "source_bindings": [{
                "scope": "package", "path": "references/policies/reader_accessibility.v1.json",
                "sha256": policy._hash(profile_path), "role": "package_profile",
            }],
            "register_class": "domain-native", "passage_scope_class": "technical",
            "attestation_view_pin": register["attestation_view_pin"],
            "exemplar_view_pin": register["exemplar_view_pin"],
            "register_provenance": register,
        }
        candidate = reader_accessibility_candidates.build_candidate_artifact(
            project, manuscript, "Ph3", "fixture-cycle", resolved,
        )
        assert "dennett-1987-intentional-stance" not in candidate["sub_checks"]["H"]["surface_warrant_source_keys"]
        assert "dennett-1987-intentional-stance" in {
            item["source_key"] for item in policy.argument_exemplar_members(updated)
        }

        (sources / "dry-run-work.md").write_text(
            "---\ngrounding_status: section-read\n---\n", encoding="utf-8"
        )
        before_dry_run = profile_path.read_bytes()
        preview = invoke(
            harness, profile_path, wiki, workspace,
            "--add-exemplar", "dry-run-work", "--role", "classic-halo", "--dry-run",
        )
        assert preview.returncode == 0, preview.stdout + preview.stderr
        preview_report = json.loads(preview.stdout)
        assert preview_report["delta_class"] in {"exemplar", "both"}
        assert preview_report["applied"] is False
        assert "RA-DNR-COHERENCE" in {item["code"] for item in preview_report["warnings"]}
        assert profile_path.read_bytes() == before_dry_run

        dropped = invoke(
            harness, profile_path, wiki, workspace,
            "--drop-exemplar", "dennett-1987-intentional-stance",
            "--confirm-drop-locked-role", answer="yes\n",
        )
        assert dropped.returncode == 0, dropped.stdout + dropped.stderr
        dropped_row = rows(harness)[-1]
        assert dropped_row["delta_summary"]["exemplar_members_dropped"] == [{
            "source_key": "dennett-1987-intentional-stance",
            "warrant_scope": "argument-only",
        }]

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        harness, profile_path, wiki, workspace = fixture(root)
        page = wiki / "wiki/sources/race-work.md"
        page.write_text("---\ngrounding_status: full-read\n---\n", encoding="utf-8")
        before = profile_path.read_bytes()
        def change_grounding_during_confirmation(_: str) -> bool:
            page.write_text("---\ngrounding_status: stub\n---\n", encoding="utf-8")
            return True
        try:
            policy.run_repin(
                harness_root=harness, profile_path=profile_path,
                wiki_root=wiki, workspace_root=workspace, project_root=None,
                trigger="manual", dry_run=False, allow_unrelated_dirty=False,
                force_lock=False, add_exemplar="race-work", drop_exemplar=None,
                role="classic-halo", warrant_scope=None,
                confirm_drop_locked_role=False,
                confirm=change_grounding_during_confirmation,
            )
        except policy.PolicyError as exc:
            assert "grounding" in str(exc).lower() or "changed" in str(exc).lower()
        else:
            raise AssertionError("grounding change during confirmation was applied")
        assert profile_path.read_bytes() == before
        assert not (harness / "references/policies/repin_log.jsonl").exists()
        snapshots = harness / "reviews/.harness/repin"
        assert not snapshots.exists() or not list(snapshots.glob("*.snapshot.json"))


def main() -> int:
    cases = [
        case_graph_semantic_eligibility,
        case_graph_semantic_artifact_integrity,
        case_no_delta,
        case_delta_apply,
        case_rebind_transaction_rollback,
        case_epoch_softening,
        case_reason_code_matrix,
        case_scoped_dirty,
        case_lock_and_prior_diff,
        case_schema_first,
        case_package_only,
        case_exemplar_ingestion,
    ]
    for case in cases:
        case()
    print(f"repin-register smoke: {len(cases)} cases passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
