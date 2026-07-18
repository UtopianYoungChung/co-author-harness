#!/usr/bin/env python3
"""
Graphify contract helpers for Coupling E.2 checks.

This module ports graphify-inspired hardening patterns into the harness:
- schema-style graph payload validation
- confidence taxonomy enforcement
- robust timestamp parsing for freshness checks
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple


VALID_CONFIDENCES = {"EXTRACTED", "INFERRED", "AMBIGUOUS"}


def parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    """Parse YYYY-MM-DD or ISO 8601 values into datetime."""
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None

    # Date-only format used in project markdown.
    try:
        dt = datetime.strptime(raw, "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        pass

    # ISO-8601 strings commonly used by graphify captured_at.
    try:
        norm = raw.replace("Z", "+00:00")
        dt = datetime.fromisoformat(norm)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def resolve_wiki_root(project_root: Path, wiki_path_raw: str) -> Path:
    """Resolve wiki path with project-relative fallback."""
    candidate = Path(wiki_path_raw)
    if candidate.is_absolute():
        return candidate.resolve()
    return (project_root / candidate).resolve()


def normalize_confidence(value: object, allow_legacy: bool = True) -> Tuple[Optional[str], Optional[str]]:
    """Normalize confidence labels, with optional legacy numeric compatibility."""
    if isinstance(value, str) and value in VALID_CONFIDENCES:
        return value, None
    if not allow_legacy:
        return None, None

    # Legacy null/None values are treated as ambiguous.
    if value is None:
        return "AMBIGUOUS", "legacy_null"
    if isinstance(value, str) and value.strip().lower() in {"none", "null", ""}:
        return "AMBIGUOUS", "legacy_null_string"

    # Legacy numeric confidence values are mapped into graphify categories.
    try:
        numeric = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None, None
    if numeric >= 0.9:
        return "EXTRACTED", "legacy_numeric"
    if numeric >= 0.4:
        return "INFERRED", "legacy_numeric"
    return "AMBIGUOUS", "legacy_numeric"


def validate_graph_payload(
    graph_json: Path,
    allow_legacy_confidence: bool = True,
) -> Tuple[Optional[Dict[str, object]], List[str], Dict[str, object]]:
    """
    Validate graph.json and return (data, errors, metrics).

    Metrics are always returned (best effort) to support diagnostics in reports.
    """
    errors: List[str] = []
    metrics: Dict[str, object] = {
        "node_count": 0,
        "edge_count": 0,
        "community_count": 0,
        "confidence_counts": {"EXTRACTED": 0, "INFERRED": 0, "AMBIGUOUS": 0},
        "legacy_confidence_normalized": 0,
        "legacy_confidence_modes": {},
        "captured_at_latest": None,
        "hyperedge_count": 0,
    }

    if not graph_json.exists():
        errors.append(f"graph.json missing: {graph_json}")
        return None, errors, metrics

    try:
        data = json.loads(graph_json.read_text(encoding="utf-8", errors="ignore"))
    except json.JSONDecodeError as exc:
        errors.append(f"graph.json unreadable: {exc}")
        return None, errors, metrics

    nodes = data.get("nodes")
    links = data.get("links")

    if not isinstance(nodes, list):
        errors.append("graph.json schema: 'nodes' must be a list")
        return data, errors, metrics
    if not isinstance(links, list):
        errors.append("graph.json schema: 'links' must be a list")
        return data, errors, metrics

    metrics["node_count"] = len(nodes)
    metrics["edge_count"] = len(links)
    if isinstance(data.get("hyperedges"), list):
        metrics["hyperedge_count"] = len(data["hyperedges"])

    node_ids = set()
    communities = set()
    latest_capture: Optional[datetime] = None

    for idx, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(f"graph.json schema: node[{idx}] must be an object")
            continue
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id.strip():
            errors.append(f"graph.json schema: node[{idx}] missing non-empty 'id'")
            continue
        node_ids.add(node_id)

        community = node.get("community")
        if community is not None:
            communities.add(community)

        captured = parse_timestamp(node.get("captured_at"))
        if captured and (latest_capture is None or captured > latest_capture):
            latest_capture = captured

    metrics["community_count"] = len(communities)
    if latest_capture is not None:
        metrics["captured_at_latest"] = latest_capture.isoformat()

    conf_counts = metrics["confidence_counts"]
    for idx, edge in enumerate(links):
        if not isinstance(edge, dict):
            errors.append(f"graph.json schema: link[{idx}] must be an object")
            continue

        source = edge.get("source")
        target = edge.get("target")
        if source not in node_ids:
            errors.append(f"graph.json schema: link[{idx}] source '{source}' not found in node ids")
        if target not in node_ids:
            errors.append(f"graph.json schema: link[{idx}] target '{target}' not found in node ids")

        confidence_raw = edge.get("confidence")
        confidence, legacy_mode = normalize_confidence(
            confidence_raw,
            allow_legacy=allow_legacy_confidence,
        )
        if confidence not in VALID_CONFIDENCES:
            errors.append(
                f"graph.json schema: link[{idx}] invalid confidence '{confidence_raw}'"
            )
        else:
            conf_counts[confidence] += 1
            if legacy_mode:
                metrics["legacy_confidence_normalized"] += 1
                modes = metrics["legacy_confidence_modes"]
                modes[legacy_mode] = modes.get(legacy_mode, 0) + 1

    return data, errors, metrics
