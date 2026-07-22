#!/usr/bin/env python3
"""
Builds a project-level Coupling E.2 health report from review artifacts.

Usage:
  python scripts/coupling_health_report.py --project-root /abs/path/to/project
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Dict, List


def read_json(path: Path) -> Dict[str, object]:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except json.JSONDecodeError:
        return {}


def collect_health(project_root: Path) -> Dict[str, object]:
    reviews_dir = project_root / "reviews"
    readiness_files = sorted(reviews_dir.glob("coupling_readiness_*.json"))
    noop_files = sorted(reviews_dir.glob("sk20_noop_*.json"))
    overlay_files = sorted(reviews_dir.glob("graph_overlay_*.md"))

    readiness_total = len(readiness_files)
    readiness_ready = 0
    failed_check_counter: Counter[str] = Counter()
    graph_confidence_counter: Counter[str] = Counter()
    graph_schema_error_count = 0
    graph_samples = 0
    latest_graph_nodes = None
    latest_graph_edges = None
    latest_graph_communities = None
    latest_graph_capture = None

    for file_path in readiness_files:
        payload = read_json(file_path)
        if payload.get("ready_for_sk20") is True:
            readiness_ready += 1
        for key in payload.get("failed_checks", []) or []:
            if isinstance(key, str):
                failed_check_counter[key] += 1
        metadata = payload.get("metadata", {})
        if isinstance(metadata, dict):
            graph_metrics = metadata.get("graph_metrics", {})
            if isinstance(graph_metrics, dict):
                graph_samples += 1
                conf_counts = graph_metrics.get("confidence_counts", {})
                if isinstance(conf_counts, dict):
                    for conf_key, count in conf_counts.items():
                        if isinstance(conf_key, str) and isinstance(count, int):
                            graph_confidence_counter[conf_key] += count
                latest_graph_nodes = graph_metrics.get("node_count", latest_graph_nodes)
                latest_graph_edges = graph_metrics.get("edge_count", latest_graph_edges)
                latest_graph_communities = graph_metrics.get("community_count", latest_graph_communities)
                latest_graph_capture = graph_metrics.get("captured_at_latest", latest_graph_capture)
            validation_errors = metadata.get("graph_validation_errors", [])
            if isinstance(validation_errors, list) and validation_errors:
                graph_schema_error_count += 1

    noop_reason_counter: Counter[str] = Counter()
    for file_path in noop_files:
        payload = read_json(file_path)
        code = payload.get("reason_code")
        if isinstance(code, str) and code:
            noop_reason_counter[code] += 1

    data = {
        "project_root": str(project_root),
        "readiness_reports": readiness_total,
        "ready_count": readiness_ready,
        "not_ready_count": readiness_total - readiness_ready,
        "overlay_reports": len(overlay_files),
        "noop_reports": len(noop_files),
        "failed_check_counts": dict(failed_check_counter),
        "noop_reason_counts": dict(noop_reason_counter),
        "latest_readiness_report": str(readiness_files[-1]) if readiness_files else None,
        "latest_overlay_report": str(overlay_files[-1]) if overlay_files else None,
        "latest_noop_report": str(noop_files[-1]) if noop_files else None,
        "graph_samples": graph_samples,
        "graph_schema_error_reports": graph_schema_error_count,
        "graph_confidence_counts": dict(graph_confidence_counter),
        "latest_graph_snapshot": {
            "nodes": latest_graph_nodes,
            "edges": latest_graph_edges,
            "communities": latest_graph_communities,
            "captured_at_latest": latest_graph_capture,
        },
    }
    return data


def render_markdown(health: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# Coupling E.2 Health Report")
    lines.append("")
    lines.append(f"**Project root:** `{health['project_root']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Readiness reports: {health['readiness_reports']}")
    lines.append(f"- Ready for SK-20: {health['ready_count']}")
    lines.append(f"- Not ready: {health['not_ready_count']}")
    lines.append(f"- Overlay reports: {health['overlay_reports']}")
    lines.append(f"- No-op reports: {health['noop_reports']}")
    lines.append("")
    lines.append("## Latest graph snapshot (from readiness metadata)")
    snap = health.get("latest_graph_snapshot", {})
    lines.append(f"- Nodes: {snap.get('nodes')}")
    lines.append(f"- Edges: {snap.get('edges')}")
    lines.append(f"- Communities: {snap.get('communities')}")
    lines.append(f"- Captured at: {snap.get('captured_at_latest')}")
    lines.append("")

    lines.append("## Graph contract quality")
    lines.append(f"- Readiness reports with graph metrics: {health.get('graph_samples', 0)}")
    lines.append(f"- Reports with graph schema errors: {health.get('graph_schema_error_reports', 0)}")
    conf_counts = health.get("graph_confidence_counts", {})
    if conf_counts:
        conf_text = " · ".join(f"{key}: {value}" for key, value in sorted(conf_counts.items()))
        lines.append(f"- Confidence totals: {conf_text}")
    else:
        lines.append("- Confidence totals: none recorded yet")
    lines.append("")

    lines.append("## Latest artifacts")
    lines.append(f"- readiness: {health['latest_readiness_report']}")
    lines.append(f"- overlay: {health['latest_overlay_report']}")
    lines.append(f"- noop: {health['latest_noop_report']}")
    lines.append("")

    failed_checks = health["failed_check_counts"]
    if failed_checks:
        lines.append("## Failed check frequency")
        for key, count in sorted(failed_checks.items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"- `{key}`: {count}")
        lines.append("")

    noop_reasons = health["noop_reason_counts"]
    if noop_reasons:
        lines.append("## No-op reason frequency")
        for key, count in sorted(noop_reasons.items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"- `{key}`: {count}")
        lines.append("")

    if not failed_checks and not noop_reasons:
        lines.append("No failed-check or no-op history recorded yet.")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True, help="Absolute path to project root")
    parser.add_argument(
        "--output-md",
        required=False,
        help="Optional markdown output path (default: <project>/reviews/coupling_health.md)",
    )
    parser.add_argument(
        "--output-json",
        required=False,
        help="Optional JSON output path (default: <project>/reviews/coupling_health.json)",
    )
    args = parser.parse_args()

    project_root = Path(args.project_root)
    health = collect_health(project_root)

    md_output = args.output_md or str(project_root / "reviews" / "coupling_health.md")
    json_output = args.output_json or str(project_root / "reviews" / "coupling_health.json")

    md_path = Path(md_output)
    json_path = Path(json_output)
    from destination_capability import DestinationRefused, assert_writable, guard_project_root
    try:
        guard_project_root(project_root)
        assert_writable(md_path, purpose="coupling-health markdown output")
        assert_writable(json_path, purpose="coupling-health JSON output")
    except DestinationRefused as exc:
        print(f"[BLOCKER] {exc}")
        return 4
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    md_path.write_text(render_markdown(health), encoding="utf-8")
    json_path.write_text(json.dumps(health, indent=2), encoding="utf-8")

    print(json.dumps(health, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
