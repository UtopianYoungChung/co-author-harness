#!/usr/bin/env python3
"""
Run SK-20 overlay end-to-end:
1) deterministic readiness gate
2) graph/manuscript citation overlay
3) report + revision log artifacts
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from coupling_readiness_check import derive_noop_reason, run_checks, parse_cli_bool
from graph_authority_gate import evaluate_graph_authority, REASON_CODE as GRAPH_AUTHORITY_REASON


TEX_CITE_RE = re.compile(r"\\cite[a-zA-Z*]*\s*(?:\[[^\]]*\]\s*){0,2}\{([^}]+)\}")
MD_CITE_RE = re.compile(r"\(([A-Z][A-Za-z'`\-]+(?:\set\sal\.)?\s+\d{4}[a-z]?)\)")


def _norm_confidence(value: object) -> str:
    if isinstance(value, str) and value in {"EXTRACTED", "INFERRED", "AMBIGUOUS"}:
        return value
    if value is None or (isinstance(value, str) and value.strip().lower() in {"none", "null", ""}):
        return "AMBIGUOUS"
    try:
        x = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return "AMBIGUOUS"
    if x >= 0.9:
        return "EXTRACTED"
    if x >= 0.4:
        return "INFERRED"
    return "AMBIGUOUS"


def _tokenize(text: str) -> List[str]:
    stop = {"the", "and", "of", "for", "in", "on", "to", "a", "an"}
    return [t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if t and t not in stop]


def _extract_citation_keys(manuscript_text: str) -> List[str]:
    keys: List[str] = []
    for match in TEX_CITE_RE.findall(manuscript_text):
        keys.extend([part.strip() for part in match.split(",") if part.strip()])
    return sorted(set(keys))


def _extract_author_year_mentions(manuscript_text: str) -> List[str]:
    return sorted(set(MD_CITE_RE.findall(manuscript_text)))


def _parse_bib_entries(bib_path: Path) -> Dict[str, Dict[str, str]]:
    if not bib_path.exists():
        return {}
    text = bib_path.read_text(encoding="utf-8", errors="ignore")
    entry_pat = re.compile(r"@([A-Za-z]+)\s*\{\s*([^,]+)\s*,(.*?)\n\}", re.S)
    field_pat = re.compile(r"([A-Za-z]+)\s*=\s*[\"{]([^\"}]+)[\"}]", re.S)
    out: Dict[str, Dict[str, str]] = {}
    for _etype, key, body in entry_pat.findall(text):
        out[key.strip()] = {k.lower(): v.strip().replace("\n", " ") for k, v in field_pat.findall(body)}
    return out


def _score_source_match(
    key: str,
    source_lower: str,
    year: str,
    surname: str,
    title_tokens: List[str],
    labels: List[str],
) -> int:
    """Score how well a single source file matches a citation key."""
    score = 0
    if key.lower() in source_lower:
        score += 4
    if year and year in source_lower:
        score += 2
    if surname and surname in source_lower:
        score += 2
    score += sum(1 for tok in title_tokens if len(tok) >= 4 and tok in source_lower)
    # Secondary signal: title tokens in any node label from this source.
    if labels and title_tokens:
        for tok in title_tokens:
            if len(tok) >= 5 and any(tok in label for label in labels):
                score += 1
                break
    return score


def _resolve_key_to_source(
    key: str,
    fields: Dict[str, str],
    source_files: List[str],
    node_labels_by_source: Dict[str, List[str]],
) -> Tuple[Optional[str], int]:
    year = fields.get("year", "")
    author_tokens = _tokenize(fields.get("author", ""))
    surname = author_tokens[0] if author_tokens else ""
    title_tokens = _tokenize(fields.get("title", ""))[:6]

    best_source: Optional[str] = None
    best_score = 0
    for source in source_files:
        score = _score_source_match(
            key, source.lower(), year, surname, title_tokens,
            node_labels_by_source.get(source, []),
        )
        if score > best_score:
            best_score = score
            best_source = source

    if best_source and best_score >= 3:
        return best_source, best_score
    return None, best_score


class _GraphCorpus:
    """Loaded graph corpus with precomputed indices."""

    __slots__ = (
        "nodes", "links", "conf_counts", "id_to_node",
        "node_labels_by_source", "nodes_by_source", "captured_at",
    )

    def __init__(self, wiki_root: Path) -> None:
        graph_json = wiki_root / "graphify-out" / "graph.json"
        graph = json.loads(graph_json.read_text(encoding="utf-8", errors="ignore"))
        self.nodes: List[Dict[str, object]] = graph.get("nodes", [])
        self.links: List[Dict[str, object]] = graph.get("links", [])

        self.conf_counts = {"EXTRACTED": 0, "INFERRED": 0, "AMBIGUOUS": 0}
        for edge in self.links:
            self.conf_counts[_norm_confidence(edge.get("confidence"))] += 1

        self.id_to_node = {n.get("id"): n for n in self.nodes if n.get("id")}

        self.node_labels_by_source: Dict[str, List[str]] = {}
        self.nodes_by_source: Dict[str, List[Dict[str, object]]] = {}
        for node in self.nodes:
            sf = str(node.get("source_file", ""))
            if not sf:
                continue
            self.node_labels_by_source.setdefault(sf, []).append(str(node.get("label", "")).lower())
            self.nodes_by_source.setdefault(sf, []).append(node)

        self.captured_at = next(
            (str(n.get("captured_at")) for n in self.nodes if n.get("captured_at")),
            "unknown",
        )


def _resolve_citations(
    citation_keys: List[str],
    bib_entries: Dict[str, Dict[str, str]],
    corpus: _GraphCorpus,
) -> Tuple[List[Dict[str, object]], List[Dict[str, str]]]:
    """Resolve each citation key against graph source files."""
    source_files = sorted(corpus.node_labels_by_source.keys())
    resolved: List[Dict[str, object]] = []
    unresolved: List[Dict[str, str]] = []
    for key in citation_keys:
        source, score = _resolve_key_to_source(
            key=key,
            fields=bib_entries.get(key, {}),
            source_files=source_files,
            node_labels_by_source=corpus.node_labels_by_source,
        )
        if source is None:
            unresolved.append({"key": key, "reason": "no robust source_file match in graph corpus"})
        else:
            resolved.append({"key": key, "source_file": source, "score": score})
    return resolved, unresolved


def _generate_stub_findings(
    resolved: List[Dict[str, object]],
    unresolved: List[Dict[str, str]],
    corpus: _GraphCorpus,
) -> Tuple[List[str], List[Dict[str, object]], List[Dict[str, object]]]:
    """Finding type A: graph-stub citations (unresolved + resolved without nodes)."""
    resolved_with = [r for r in resolved if corpus.nodes_by_source.get(str(r["source_file"]))]
    resolved_without = [r for r in resolved if not corpus.nodes_by_source.get(str(r["source_file"]))]
    findings: List[str] = []
    for item in unresolved:
        findings.append(
            f"- [MINOR] [source: graph-stub] Citation `{item['key']}` could not be mapped to any graph source file."
        )
    for item in resolved_without:
        findings.append(
            f"- [MINOR] [source: graph-stub] Citation `{item['key']}` mapped to `{item['source_file']}` but has zero graph nodes."
        )
    return findings, resolved_with, resolved_without


def _generate_missing_citation_findings(
    resolved_with_nodes: List[Dict[str, object]],
    corpus: _GraphCorpus,
) -> List[str]:
    """Finding type C: missing-citation candidates from graph edges."""
    cited_sources = {str(r["source_file"]) for r in resolved_with_nodes}
    interesting = {"supports", "extends", "semantically_similar_to", "contradicts"}
    findings: List[str] = []
    for edge in corpus.links:
        relation = str(edge.get("relation", ""))
        if relation not in interesting:
            continue
        src_node = corpus.id_to_node.get(edge.get("source"))
        tgt_node = corpus.id_to_node.get(edge.get("target"))
        if not src_node or not tgt_node:
            continue
        src_file = str(src_node.get("source_file", ""))
        tgt_file = str(tgt_node.get("source_file", ""))
        if not src_file or not tgt_file or src_file == tgt_file:
            continue
        if (src_file in cited_sources) ^ (tgt_file in cited_sources):
            cited = src_file if src_file in cited_sources else tgt_file
            uncited = tgt_file if src_file in cited_sources else src_file
            conf = _norm_confidence(edge.get("confidence"))
            severity = "[MAJOR]" if relation == "contradicts" or conf == "EXTRACTED" else "[MINOR]"
            tag = "graph-extracted" if conf == "EXTRACTED" else "graph-inferred"
            findings.append(
                f"- {severity} [source: {tag}] `{cited}` {relation} `{uncited}` (confidence={conf}, score={edge.get('confidence_score')})"
            )
    return findings


def _compute_graph_stats(
    corpus: _GraphCorpus,
    wiki_root: Path,
) -> Tuple[List[str], int, int]:
    """Compute god-nodes list, community count, and isolated-node count."""
    god_nodes: List[str] = []
    graph_report = wiki_root / "graphify-out" / "GRAPH_REPORT.md"
    if graph_report.exists():
        for line in graph_report.read_text(encoding="utf-8", errors="ignore").splitlines():
            m = re.match(r"\d+\. `([^`]+)` - (\d+) edges", line.strip())
            if m:
                god_nodes.append(f"{m.group(1)} ({m.group(2)})")
            if len(god_nodes) >= 5:
                break

    communities = {n.get("community") for n in corpus.nodes if n.get("community") is not None}
    connected: set = set()
    for e in corpus.links:
        connected.add(e.get("source"))
        connected.add(e.get("target"))
    isolated_count = sum(
        1 for n in corpus.nodes
        if n.get("id") is not None and n.get("id") not in connected
    )
    return god_nodes, len(communities), isolated_count


def _render_overlay_report(
    manuscript_path: Path,
    classification_path: Path,
    stamp: str,
    corpus: _GraphCorpus,
    citation_keys: List[str],
    author_year_mentions: List[str],
    resolved: List[Dict[str, object]],
    unresolved: List[Dict[str, str]],
    resolved_with_nodes: List[Dict[str, object]],
    resolved_without_nodes: List[Dict[str, object]],
    findings_a: List[str],
    findings_c: List[str],
    god_nodes: List[str],
    community_count: int,
    isolated_count: int,
) -> str:
    """Assemble the overlay report markdown."""
    total_findings = len(findings_a) + len(findings_c)
    major_count = sum(1 for f in findings_a + findings_c if "[MAJOR]" in f)
    minor_count = sum(1 for f in findings_a + findings_c if "[MINOR]" in f)

    lines: List[str] = [
        "# Graph Overlay Report",
        "",
        f"**Artifact overlaid:** `{manuscript_path}`",
        f"**Date:** {stamp}",
        f"**Graph captured:** {corpus.captured_at}",
        "**P-stage:** P1 (inferred from advisor artifact path)",
        f"**Paper type:** Derived from advisor consultation artifact `{classification_path.name}`",
        "",
        "## Graph inventory",
        f"- Total nodes: {len(corpus.nodes)}",
        f"- Total edges: {len(corpus.links)}  (EXTRACTED: {corpus.conf_counts['EXTRACTED']} · INFERRED: {corpus.conf_counts['INFERRED']} · AMBIGUOUS: {corpus.conf_counts['AMBIGUOUS']})",
        f"- God-nodes: {', '.join(god_nodes) if god_nodes else 'not available'}",
        f"- Communities: {community_count}",
        f"- Isolated nodes: {isolated_count}",
        "",
        "## Citation alignment",
        f"- Total citations (LaTeX cite entries): {len(citation_keys)}",
        f"- Unique citation keys: {len(citation_keys)}",
        f"- Author-year mentions (non-key): {len(author_year_mentions)}",
        f"- Resolved to graph source_file: {len(resolved)}",
        f"- Unresolved: {len(unresolved)}",
        f"- Cited sources with graph nodes: {len(resolved_with_nodes)}",
        f"- Cited sources without graph nodes: {len(resolved_without_nodes)}",
        "",
        "## Findings",
        "",
        "### Finding type A — Graph-stub citations",
    ]
    lines.extend(findings_a if findings_a else ["None"])
    lines.extend([
        "",
        "### Finding type B — Section-location mismatches",
        "None (not executed: deterministic section-claim parser for TeX not yet enabled).",
        "",
        "### Finding type C — Missing-citation candidates",
    ])
    lines.extend(findings_c[:60] if findings_c else ["None"])
    if len(findings_c) > 60:
        lines.append(f"- ... and {len(findings_c) - 60} more candidates")
    lines.extend([
        "",
        "## P-stage adjustments applied",
        "No automatic severity promotion/demotion applied in this compatibility run.",
        "",
        "## Unresolved citations",
    ])
    if unresolved:
        for item in unresolved:
            lines.append(f"- `{item['key']}` — {item['reason']}")
    else:
        lines.append("None")
    lines.extend([
        "",
        "## Handback",
        f"- Findings emitted: {total_findings}  (BLOCKER: 0 · MAJOR: {major_count} · MINOR: {minor_count})",
        "- Next step: Evaluator Step 1 classification gating (this report is pre-flight input)",
        "- Grounding-audit Category 8 target: this file",
    ])
    return "\n".join(lines)


def _append_revision_log(
    manuscript_path: Path,
    stamp: str,
    findings_a_count: int,
    findings_c_count: int,
    graph_captured: str,
) -> None:
    """Append overlay-run entry to the revision log (idempotent)."""
    total = findings_a_count + findings_c_count
    revlog = manuscript_path.parent / "revision_log.md"
    revlog.parent.mkdir(parents=True, exist_ok=True)
    entry = (
        f"{stamp} — SK-20 graph-overlay run — {total} findings "
        f"(A: {findings_a_count} · B: 0 · C: {findings_c_count}) · graph {graph_captured}"
    )
    if revlog.exists():
        content = revlog.read_text(encoding="utf-8", errors="ignore")
    else:
        content = "# Revision Log\n"
    if entry not in content:
        content = content.rstrip() + "\n" + entry + "\n"
        revlog.write_text(content, encoding="utf-8")


def run_overlay(
    project_root: Path,
    manuscript_path: Path,
    references_path: Path,
    classification_path: Path,
    wiki_root: Path,
    stamp: str,
) -> Path:
    """Orchestrate the SK-20 overlay: load, resolve, find, render, log."""
    corpus = _GraphCorpus(wiki_root)

    manuscript_text = manuscript_path.read_text(encoding="utf-8", errors="ignore")
    citation_keys = _extract_citation_keys(manuscript_text)
    author_year_mentions = _extract_author_year_mentions(manuscript_text)
    bib_entries = _parse_bib_entries(references_path)

    resolved, unresolved = _resolve_citations(citation_keys, bib_entries, corpus)
    findings_a, resolved_with, resolved_without = _generate_stub_findings(resolved, unresolved, corpus)
    findings_c = _generate_missing_citation_findings(resolved_with, corpus)
    god_nodes, community_count, isolated_count = _compute_graph_stats(corpus, wiki_root)

    report_text = _render_overlay_report(
        manuscript_path=manuscript_path,
        classification_path=classification_path,
        stamp=stamp,
        corpus=corpus,
        citation_keys=citation_keys,
        author_year_mentions=author_year_mentions,
        resolved=resolved,
        unresolved=unresolved,
        resolved_with_nodes=resolved_with,
        resolved_without_nodes=resolved_without,
        findings_a=findings_a,
        findings_c=findings_c,
        god_nodes=god_nodes,
        community_count=community_count,
        isolated_count=isolated_count,
    )

    out_dir = project_root / "reviews"
    out_dir.mkdir(parents=True, exist_ok=True)
    overlay_path = out_dir / f"graph_overlay_{stamp}.md"
    overlay_path.write_text(report_text, encoding="utf-8")

    _append_revision_log(manuscript_path, stamp, len(findings_a), len(findings_c), corpus.captured_at)
    return overlay_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True, help="Absolute path to project root")
    parser.add_argument("--date", required=False, help="Date stamp override (YYYY-MM-DD)")
    parser.add_argument("--project-claude-path", required=False, help="Optional explicit CLAUDE.md path")
    parser.add_argument("--allow-ancestor-claude", action="store_true", help="Resolve CLAUDE.md from ancestor directories")
    parser.add_argument("--allow-missing-project-claude", action="store_true", help="Allow readiness checks with CLI metadata overrides even when project CLAUDE.md is absent")
    parser.add_argument("--wiki-linked", required=False, help="Override wiki_linked flag (true/false)")
    parser.add_argument("--coupling-e-on-review", required=False, help="Override coupling_e_on_review flag (true/false)")
    parser.add_argument("--wiki-path", required=False, help="Override wiki path")
    parser.add_argument("--manuscript-path", required=False, help="Override manuscript path")
    parser.add_argument("--references-path", required=False, help="Override references path")
    parser.add_argument("--classification-path", required=False, help="Override classification path")
    parser.add_argument("--allow-legacy-graph-confidence", required=False, help="Allow compatibility normalization for legacy numeric/null graph confidence values (true/false)")
    args = parser.parse_args()

    project_root = Path(args.project_root)
    from destination_capability import DestinationRefused, guard_project_root
    try:
        guard_project_root(project_root)
    except DestinationRefused as exc:
        print(f"[BLOCKER] {exc}")
        return 4
    stamp = args.date or datetime.date.today().isoformat()

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

    checks, metadata = run_checks(project_root=project_root, overrides=overrides)
    authority = evaluate_graph_authority(
        structural_ok=metadata.get("legacy_structural_ok")
        if "legacy_structural_ok" in metadata
        else None
    )
    if authority.get("governed_available") is not False:
        raise RuntimeError("graph_authority_gate must be unconditionally unavailable in this delta")
    ready = all(item.ok for item in checks)
    failed_keys = [item.key for item in checks if not item.ok]
    reason_code, reason_detail = derive_noop_reason(checks, metadata)
    summary = {
        "ready_for_sk20": ready,
        "graph_authority": authority,
        "failed_checks": failed_keys,
        "recommended_noop_reason_code": reason_code,
        "recommended_noop_message": reason_detail,
        "checks": [item.__dict__ for item in checks],
        "metadata": metadata,
    }

    reviews_dir = project_root / "reviews"
    reviews_dir.mkdir(parents=True, exist_ok=True)
    readiness_path = reviews_dir / f"coupling_readiness_{stamp}.json"
    readiness_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if not summary["ready_for_sk20"]:
        noop_path = reviews_dir / f"sk20_noop_{stamp}.json"
        noop_payload = {
            "skill": "SK-20",
            "status": "noop",
            "reason_code": summary["recommended_noop_reason_code"],
            "message": summary["recommended_noop_message"],
            "failed_checks": summary["failed_checks"],
            "timestamp": stamp,
            "source_readiness_report": str(readiness_path),
        }
        noop_path.write_text(json.dumps(noop_payload, indent=2), encoding="utf-8")
        print(json.dumps({
            "status": "noop",
            "reason_code": summary["recommended_noop_reason_code"],
            "readiness_report": str(readiness_path),
            "noop_report": str(noop_path),
        }, indent=2))
        return 2

    manuscript_path = Path(str(overrides["manuscript_path"])) if overrides.get("manuscript_path") else project_root / "manuscript" / "main.md"
    references_path = Path(str(overrides["references_path"])) if overrides.get("references_path") else project_root / "references" / "REFERENCES.md"
    classification_path = Path(str(overrides["classification_path"])) if overrides.get("classification_path") else project_root / "reviews" / "classification.md"
    wiki_path_raw = str(overrides["wiki_path"]) if overrides.get("wiki_path") else metadata.get("wiki_path", "")
    wiki_root = Path(wiki_path_raw)

    overlay_path = run_overlay(
        project_root=project_root,
        manuscript_path=manuscript_path,
        references_path=references_path,
        classification_path=classification_path,
        wiki_root=wiki_root,
        stamp=stamp,
    )

    print(json.dumps({
        "status": "ok",
        "readiness_report": str(readiness_path),
        "overlay_report": str(overlay_path),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
