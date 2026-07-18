#!/usr/bin/env python3
"""
Deterministic readiness check for Coupling E.2 (SK-20 graph overlay).

Usage:
  python scripts/coupling_readiness_check.py --project-root /abs/path/to/project
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from graphify_contract import parse_timestamp, resolve_wiki_root, validate_graph_payload
from graph_authority_gate import evaluate_graph_authority


DATE_RE = re.compile(r"Last updated:\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE)
CITE_RE = re.compile(r"\([A-Z][A-Za-z'`\-]+(?:\set\sal\.)?\s+\d{4}[a-z]?\)")
TEX_CITE_RE = re.compile(r"\\cite[a-zA-Z*]*\s*(\[[^\]]*\]\s*){0,2}\{[^}]+\}")


@dataclass
class CheckResult:
    key: str
    ok: bool
    detail: str


def parse_bool_flag(claude_text: str, field: str) -> Optional[bool]:
    pattern = re.compile(rf"`{re.escape(field)}`\s*\|\s*`(true|false)`", re.IGNORECASE)
    match = pattern.search(claude_text)
    if not match:
        return None
    return match.group(1).lower() == "true"


def parse_wiki_path(claude_text: str) -> Optional[str]:
    pattern = re.compile(r"`wiki_path`\s*\|\s*`([^`]+)`", re.IGNORECASE)
    match = pattern.search(claude_text)
    if not match:
        return None
    return match.group(1).strip()


def parse_cli_bool(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    norm = value.strip().lower()
    if norm in {"true", "1", "yes", "y"}:
        return True
    if norm in {"false", "0", "no", "n"}:
        return False
    return None


def resolve_project_claude_path(
    project_root: Path,
    explicit_path: Optional[str] = None,
    allow_ancestor: bool = False,
) -> Optional[Path]:
    if explicit_path:
        explicit = Path(explicit_path)
        if explicit.exists():
            return explicit.resolve()
        return None

    local = project_root / "CLAUDE.md"
    if local.exists():
        return local.resolve()

    if allow_ancestor:
        for parent in project_root.parents:
            candidate = parent / "CLAUDE.md"
            if candidate.exists():
                return candidate.resolve()
    return None


def extract_last_updated(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="ignore")
    match = DATE_RE.search(text)
    return match.group(1) if match else None


def has_citations(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8", errors="ignore")
    return bool(CITE_RE.search(text) or TEX_CITE_RE.search(text))


NOOP_REASON_BY_CHECK = {
    "project_claude_exists": "PROJECT_CLAUDE_MISSING",
    "wiki_linked_flag": "NOT_WIKI_LINKED",
    "coupling_e_on_review_flag": "COUPLING_E_DISABLED",
    "wiki_path_declared": "WIKI_PATH_MISSING",
    "graphify_outputs_exist": "GRAPH_OUTPUT_MISSING",
    "graph_schema_valid": "GRAPH_SCHEMA_INVALID",
    "graph_governed_available": "GRAPH_GOVERNED_GENERATION_UNAVAILABLE",
    "classification_exists": "CLASSIFICATION_MISSING",
    "manuscript_has_citation": "NO_CITATIONS",
    "graph_not_stale": "GRAPH_STALE",
}


def derive_noop_reason(results: List[CheckResult], metadata: Dict[str, object]) -> Tuple[Optional[str], str]:
    failed = [item for item in results if not item.ok]
    if not failed:
        return None, ""

    for item in failed:
        code = NOOP_REASON_BY_CHECK.get(item.key)
        if code:
            return code, item.detail

    graph_validation_errors = metadata.get("graph_validation_errors")
    if isinstance(graph_validation_errors, list) and graph_validation_errors:
        if any("unreadable" in str(item).lower() for item in graph_validation_errors):
            return "GRAPH_JSON_UNREADABLE", "graph.json could not be parsed"
        return "GRAPH_SCHEMA_INVALID", str(graph_validation_errors[0])

    return "SK20_PRECONDITION_FAILED", failed[0].detail


def run_checks(
    project_root: Path,
    overrides: Optional[Dict[str, object]] = None,
) -> Tuple[List[CheckResult], Dict[str, object]]:
    overrides = overrides or {}
    classification_path = Path(str(overrides.get("classification_path"))) if overrides.get("classification_path") else project_root / "reviews" / "classification.md"
    manuscript_path = Path(str(overrides.get("manuscript_path"))) if overrides.get("manuscript_path") else project_root / "manuscript" / "main.md"
    references_path = Path(str(overrides.get("references_path"))) if overrides.get("references_path") else project_root / "references" / "REFERENCES.md"

    results: List[CheckResult] = []
    metadata: Dict[str, object] = {"project_root": str(project_root)}

    allow_missing_project_claude = bool(overrides.get("allow_missing_project_claude", False))
    allow_ancestor_claude = bool(overrides.get("allow_ancestor_claude", False))
    claude_path = resolve_project_claude_path(
        project_root=project_root,
        explicit_path=str(overrides.get("project_claude_path")) if overrides.get("project_claude_path") else None,
        allow_ancestor=allow_ancestor_claude,
    )

    if claude_path is None and not allow_missing_project_claude:
        results.append(CheckResult("project_claude_exists", False, "Missing project CLAUDE.md"))
        return results, metadata
    if claude_path is None and allow_missing_project_claude:
        results.append(CheckResult("project_claude_exists", True, "Missing project CLAUDE.md; using CLI overrides"))
        claude_text = ""
    else:
        results.append(CheckResult("project_claude_exists", True, f"Using {claude_path}"))
        claude_text = claude_path.read_text(encoding="utf-8", errors="ignore")
        metadata["resolved_claude_path"] = str(claude_path)

    wiki_linked = parse_cli_bool(str(overrides.get("wiki_linked"))) if overrides.get("wiki_linked") is not None else parse_bool_flag(claude_text, "wiki_linked")
    coupling_e = parse_cli_bool(str(overrides.get("coupling_e_on_review"))) if overrides.get("coupling_e_on_review") is not None else parse_bool_flag(claude_text, "coupling_e_on_review")
    wiki_path_raw = str(overrides.get("wiki_path")) if overrides.get("wiki_path") else parse_wiki_path(claude_text)

    results.append(
        CheckResult(
            "wiki_linked_flag",
            wiki_linked is True,
            f"wiki_linked={wiki_linked}",
        )
    )
    results.append(
        CheckResult(
            "coupling_e_on_review_flag",
            coupling_e is True,
            f"coupling_e_on_review={coupling_e}",
        )
    )

    wiki_root = resolve_wiki_root(project_root, wiki_path_raw) if wiki_path_raw else None
    metadata["wiki_path"] = str(wiki_root) if wiki_root else None
    if wiki_root is None:
        results.append(CheckResult("wiki_path_declared", False, "wiki_path not declared"))
        return results, metadata

    graph_dir = wiki_root / "graphify-out"
    graph_json = graph_dir / "graph.json"
    graph_report = graph_dir / "GRAPH_REPORT.md"

    results.append(
        CheckResult(
            "graphify_outputs_exist",
            graph_json.exists() and graph_report.exists(),
            f"graph.json={graph_json.exists()} GRAPH_REPORT.md={graph_report.exists()}",
        )
    )

    legacy_override = overrides.get("allow_legacy_graph_confidence")
    if isinstance(legacy_override, str):
        parsed_legacy = parse_cli_bool(legacy_override)
        allow_legacy_confidence = True if parsed_legacy is None else parsed_legacy
    else:
        allow_legacy_confidence = True if legacy_override is None else bool(legacy_override)
    graph_data, graph_errors, graph_metrics = validate_graph_payload(
        graph_json,
        allow_legacy_confidence=allow_legacy_confidence,
    )
    metadata["graph_validation_errors"] = graph_errors
    metadata["graph_metrics"] = graph_metrics
    results.append(
        CheckResult(
            "graph_schema_valid",
            len(graph_errors) == 0,
            graph_errors[0] if graph_errors else "graph.json schema valid",
        )
    )

    authority = evaluate_graph_authority(structural_ok=(len(graph_errors) == 0))
    metadata["legacy_structural_ok"] = bool(authority.get("legacy_structural_ok"))
    metadata["governed_available"] = bool(authority.get("governed_available"))
    metadata["graph_authority_reason"] = authority.get("reason_code")
    metadata["graph_authority_detail"] = authority.get("detail")
    results.append(
        CheckResult(
            "graph_governed_available",
            bool(authority.get("governed_available")),
            str(authority.get("detail") or authority.get("reason_code")),
        )
    )

    results.append(
        CheckResult(
            "classification_exists",
            classification_path.exists(),
            f"{classification_path.exists()} ({classification_path})",
        )
    )

    citation_present = has_citations(manuscript_path)
    results.append(
        CheckResult(
            "manuscript_has_citation",
            citation_present,
            f"{citation_present} ({manuscript_path})",
        )
    )

    manuscript_last_updated = extract_last_updated(manuscript_path)
    references_last_updated = extract_last_updated(references_path)
    graph_captured = graph_metrics.get("captured_at_latest")

    metadata["dates"] = {
        "manuscript_last_updated": manuscript_last_updated,
        "references_last_updated": references_last_updated,
        "graph_captured_at": graph_captured,
    }
    metadata["inputs"] = {
        "classification_path": str(classification_path),
        "manuscript_path": str(manuscript_path),
        "references_path": str(references_path),
        "allow_legacy_graph_confidence": allow_legacy_confidence,
    }

    graph_dt = parse_timestamp(str(graph_captured)) if graph_captured else None
    manuscript_dt = parse_timestamp(manuscript_last_updated)
    references_dt = parse_timestamp(references_last_updated)

    freshest = None
    for dt in [manuscript_dt, references_dt]:
        if dt and (freshest is None or dt > freshest):
            freshest = dt

    freshness_ok = bool(graph_dt and (freshest is None or graph_dt >= freshest))
    if freshest and graph_dt:
        freshness_ok = graph_dt >= freshest
        detail = f"graph={graph_dt.date().isoformat()} freshest_project={freshest.date().isoformat()}"
    elif graph_dt and freshest is None:
        detail = "graph capture present; manuscript/references dates unavailable"
    elif graph_data is None:
        detail = "graph unavailable for freshness comparison"
    else:
        detail = "Unable to compare freshness; ensure Last updated dates and graph captured_at exist"
    results.append(CheckResult("graph_not_stale", freshness_ok, detail))

    return results, metadata


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True, help="Absolute path to project root")
    parser.add_argument(
        "--output-json",
        required=False,
        help="Optional path for machine-readable report",
    )
    parser.add_argument(
        "--noop-output-json",
        required=False,
        help="Optional path for SK-20 no-op payload when readiness is false",
    )
    parser.add_argument("--project-claude-path", required=False, help="Optional explicit CLAUDE.md path")
    parser.add_argument("--allow-ancestor-claude", action="store_true", help="Resolve CLAUDE.md from ancestor directories")
    parser.add_argument("--allow-missing-project-claude", action="store_true", help="Allow readiness checks with CLI metadata overrides even when project CLAUDE.md is absent")
    parser.add_argument("--wiki-linked", required=False, help="Override wiki_linked flag (true/false)")
    parser.add_argument("--coupling-e-on-review", required=False, help="Override coupling_e_on_review flag (true/false)")
    parser.add_argument("--wiki-path", required=False, help="Override wiki path")
    parser.add_argument("--manuscript-path", required=False, help="Override manuscript path for citation/freshness checks")
    parser.add_argument("--references-path", required=False, help="Override references path for freshness checks")
    parser.add_argument("--classification-path", required=False, help="Override classification path")
    parser.add_argument("--allow-legacy-graph-confidence", required=False, help="Allow compatibility normalization for legacy numeric/null graph confidence values (true/false)")
    args = parser.parse_args()

    project_root = Path(args.project_root)
    overrides = {
        "project_claude_path": args.project_claude_path,
        "allow_ancestor_claude": args.allow_ancestor_claude,
        "allow_missing_project_claude": args.allow_missing_project_claude,
        "wiki_linked": args.wiki_linked,
        "coupling_e_on_review": args.coupling_e_on_review,
        "wiki_path": args.wiki_path,
        "manuscript_path": args.manuscript_path,
        "references_path": args.references_path,
        "classification_path": args.classification_path,
        "allow_legacy_graph_confidence": parse_cli_bool(args.allow_legacy_graph_confidence),
    }
    results, metadata = run_checks(project_root, overrides=overrides)

    ready = all(item.ok for item in results)
    failed_keys = [item.key for item in results if not item.ok]
    reason_code, reason_detail = derive_noop_reason(results, metadata)

    summary = {
        "ready_for_sk20": ready,
        "failed_checks": failed_keys,
        "recommended_noop_reason_code": reason_code,
        "recommended_noop_message": reason_detail,
        "checks": [asdict(item) for item in results],
        "metadata": metadata,
    }

    if args.output_json:
        out = Path(args.output_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if args.noop_output_json and not ready:
        noop_payload = {
            "skill": "SK-20",
            "status": "noop",
            "reason_code": reason_code,
            "message": reason_detail,
            "failed_checks": failed_keys,
            "timestamp": datetime.now().strftime("%Y-%m-%d"),
            "source_readiness_report": args.output_json,
        }
        noop_out = Path(args.noop_output_json)
        noop_out.parent.mkdir(parents=True, exist_ok=True)
        noop_out.write_text(json.dumps(noop_payload, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
