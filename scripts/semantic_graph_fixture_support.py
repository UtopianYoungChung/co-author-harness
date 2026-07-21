#!/usr/bin/env python3
"""Hermetic semantic-graph substrate for lifecycle and policy fixtures.

The live Wiki is an integration input, not test data.  This helper builds a
temporary, fully audited hybrid-semantic graph from the tracked re-pin snapshot
that corresponds to the profile's current pin epoch.  It never copies or
publishes the archived graph and never reads the live Wiki.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "references" / "policies" / "reader_accessibility.v1.json"
FIXTURE_MODE_ENV = "COAUTHOR_HARNESS_SEMANTIC_FIXTURE"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _current_snapshot() -> tuple[dict, dict]:
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    expected = profile["domain_native_register"]["expected_verification"]
    snapshot_path = (
        ROOT / "reviews" / ".harness" / "repin"
        / f"epoch-{expected['pin_epoch']}.snapshot.json"
    )
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    for key in ("attestation_view_pin", "exemplar_view_pin"):
        if snapshot.get(key) != expected.get(key):
            raise AssertionError(
                f"fixture snapshot {snapshot_path} does not match profile {key}"
            )
    return profile, snapshot


def write_semantic_graph_fixture(root: Path) -> tuple[Path, Path]:
    """Create an eligible synthetic Wiki/workspace pair beneath ``root``."""
    profile, snapshot = _current_snapshot()
    model = profile["domain_native_register"]
    wiki = root / "wiki"
    workspace = root / "workspace"
    graph_dir = workspace / "knowledge" / "LLM wiki" / "graphify-out"
    provenance_dir = wiki / "graphify-out"
    sources = wiki / "wiki" / "sources"
    graph_dir.mkdir(parents=True, exist_ok=True)
    provenance_dir.mkdir(parents=True, exist_ok=True)
    sources.mkdir(parents=True, exist_ok=True)

    grounding = {
        row["source_key"]: row["grounding"]
        for row in snapshot["exemplar_members"]
    }
    pages: list[str] = []
    for member in model["exemplar_members"]:
        key = member["source_key"]
        page = f"wiki/sources/{key}.md"
        pages.append(page)
        (wiki / page).write_text(
            f"---\ngrounding_status: {grounding[key]}\n---\n\n"
            f"Synthetic semantic fixture page for {key}.\n",
            encoding="utf-8",
            newline="\n",
        )

    member_ids = list(snapshot["attestation_member_ids"])
    seed_map = snapshot["seed_resolution_map"]
    primary_communities = list(snapshot["primary_communities"])
    if not primary_communities:
        raise AssertionError("fixture snapshot has no primary communities")
    seed_communities = {
        key: primary_communities[index % len(primary_communities)]
        for index, key in enumerate(seed_map)
    }
    nodes_by_id = {
        node_id: {"id": node_id, "community": primary_communities[0], "file_type": "concept"}
        for node_id in member_ids
    }
    semantic_nodes: list[dict] = []
    semantic_edges: list[dict] = []
    for index, (key, node_id) in enumerate(seed_map.items(), start=1):
        page = f"wiki/sources/{key}.md"
        node = nodes_by_id[node_id]
        node.update(
            community=seed_communities[key],
            file_type="document",
            source_file=page,
            source_location="synthetic fixture",
            label=f"fixture {key}",
            norm_label=f"fixture {key}",
            semantic_status="validated",
            extraction_status="semantic",
        )
        semantic_nodes.append(node)
        semantic_edges.append({
            "source": node_id,
            "target": node_id,
            "_src": node_id,
            "_tgt": node_id,
            "semantic_edge_id": f"fixture:{index:03d}:{key}",
            "semantic_status": "validated",
            "relation": "describes",
            "confidence": "EXTRACTED",
            "confidence_score": 1.0,
            "source_file": page,
            "source_location": "synthetic fixture",
            "weight": 1.0,
            "evidence": "tracked pin snapshot",
        })

    semantic_rows = sorted(
        zip(pages, semantic_nodes, semantic_edges),
        key=lambda row: row[0].encode("utf-8"),
    )
    pages = [row[0] for row in semantic_rows]
    semantic_nodes = [row[1] for row in semantic_rows]
    semantic_edges = [row[2] for row in semantic_rows]

    output_rows: list[dict[str, str]] = []
    chunks: list[dict] = []
    for index, (page, node, edge) in enumerate(
        zip(pages, semantic_nodes, semantic_edges), start=1
    ):
        chunk_id = f"fixture-chunk-{index:03d}"
        relative = f"graphify-out/chunks/{chunk_id}.output.json"
        output_path = wiki / relative
        output_node = {
            key: value for key, value in node.items()
            if key not in {"community", "extraction_status", "norm_label"}
        }
        output_node["semantic_status"] = "candidate"
        output_edge = {
            key: value for key, value in edge.items()
            if key not in {"_src", "_tgt", "semantic_edge_id", "semantic_status"}
        }
        _write_json(output_path, {
            "schema_version": "1.0.0",
            "chunk_id": chunk_id,
            "pages": [{
                "source_file": page,
                "sha256": _sha256(wiki / page),
                "nodes": [output_node],
                "edges": [output_edge],
            }],
        })
        output_rows.append({"path": relative, "sha256": _sha256(output_path)})
        chunks.append({"chunk_id": chunk_id, "page_count": 1, "source_files": [page]})

    output_payload = "\n".join(
        f"{row['path']}\t{row['sha256']}" for row in output_rows
    ).encode("utf-8")
    outputs_sha256 = hashlib.sha256(output_payload).hexdigest()
    manifest_pages = [
        {"source_file": page, "sha256": _sha256(wiki / page)} for page in pages
    ]
    inventory_payload = "\n".join(
        f"{row['source_file']}\t{row['sha256']}" for row in manifest_pages
    ).encode("utf-8")
    inventory_sha256 = hashlib.sha256(inventory_payload).hexdigest()

    manifest_path = provenance_dir / "fixture-manifest.json"
    audit_path = provenance_dir / "fixture-audit.json"
    report_path = provenance_dir / "fixture-report.md"
    receipt_path = provenance_dir / "fixture-receipt.json"
    _write_json(manifest_path, {
        "schema_version": "1.0.0",
        "page_count": len(pages),
        "chunk_count": len(chunks),
        "research_inventory_sha256": inventory_sha256,
        "pages": manifest_pages,
        "chunks": chunks,
    })
    manifest_sha256 = _sha256(manifest_path)
    audit_rows = [{
        "semantic_edge_id": edge["semantic_edge_id"],
        "verdict": "supported",
        "note": "synthetic fixture derived from tracked pin snapshot",
        "reviewer": "Codex",
    } for edge in semantic_edges]
    _write_json(audit_path, {
        "schema_version": "1.0.0",
        "manifest_sha256": manifest_sha256,
        "semantic_outputs_sha256": outputs_sha256,
        "reviewer": "Codex",
        "reviewers": ["Codex"],
        "reviewer_counts": {"Codex": len(audit_rows)},
        "sample_count": len(audit_rows),
        "verdict_counts": {"supported": len(audit_rows), "unclear": 0, "unsupported": 0},
        "edges": audit_rows,
    })
    report_path.write_text("# Synthetic semantic fixture report\n", encoding="utf-8", newline="\n")

    graph = {
        "graph": {
            "extraction_mode": "hybrid-structural-semantic",
            "semantic_status": "validated",
            "semantic_scope": "synthetic-fixture",
            "semantic_manifest": "graphify-out/fixture-manifest.json",
            "semantic_manifest_sha256": manifest_sha256,
            "semantic_outputs_sha256": outputs_sha256,
            "semantic_output_files": output_rows,
            "semantic_audit": "graphify-out/fixture-audit.json",
            "semantic_audit_sha256": _sha256(audit_path),
            "semantic_report": "graphify-out/fixture-report.md",
            "semantic_receipt": "graphify-out/fixture-receipt.json",
            "semantic_pages_expected": len(pages),
            "semantic_pages_represented": len(pages),
            "research_inventory_sha256": inventory_sha256,
            "semantic_node_count": len(semantic_nodes),
            "semantic_edge_count": len(semantic_edges),
            "fixture_exemplar_hash_lines": snapshot["exemplar_hash_lines"],
        },
        "nodes": list(nodes_by_id.values()),
        "links": semantic_edges,
    }
    graph_path = graph_dir / "graph.json"
    _write_json(graph_path, graph)
    _write_json(receipt_path, {
        "schema_version": "1.0.0",
        "final_graph_sha256": _sha256(graph_path),
        "manifest_sha256": manifest_sha256,
        "audit_sha256": _sha256(audit_path),
        "semantic_outputs_sha256": outputs_sha256,
        "research_inventory_sha256": inventory_sha256,
        "report_sha256": _sha256(report_path),
        "extraction_mode": "hybrid-structural-semantic",
        "semantic_status": "validated",
        "semantic_scope": "synthetic-fixture",
        "page_count": len(pages),
        "semantic_node_count": len(semantic_nodes),
        "semantic_edge_count": len(semantic_edges),
        "audit_sample_count": len(audit_rows),
    })
    return wiki, workspace


@contextmanager
def semantic_graph_fixture_environment() -> Iterator[tuple[Path, Path]]:
    """Install per-process roots for a temp semantic fixture, then restore them."""
    with tempfile.TemporaryDirectory(prefix="coauthor-semantic-fixture-") as td:
        wiki, workspace = write_semantic_graph_fixture(Path(td))
        updates = {
            "AGENT_WIKI_ROOT": str(wiki),
            "AGENT_WORKSPACE_ROOT": str(workspace),
            "AGENT_HARNESS_ROOT": str(ROOT),
            FIXTURE_MODE_ENV: "1",
        }
        prior = {key: os.environ.get(key) for key in updates}
        os.environ.update(updates)
        try:
            yield wiki, workspace
        finally:
            for key, value in prior.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
