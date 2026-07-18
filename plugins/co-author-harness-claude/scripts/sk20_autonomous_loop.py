#!/usr/bin/env python3
"""
Autonomous SK-20 loop runner:
1) ingest bibliography into wiki sources
2) augment + rebuild graphify graph artifacts
3) run SK-20 overlay pipeline
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from coupling_readiness_check import parse_cli_bool


TEX_CITE_RE = re.compile(r"\\cite[a-zA-Z*]*\s*(?:\[[^\]]*\]\s*){0,2}\{([^}]+)\}")


def _slug(text: str) -> str:
    raw = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return raw[:64] if raw else "untitled"


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[A-Za-z0-9]+", text or "")


def _first_author_surname(author_field: str) -> str:
    if not author_field:
        return "unknown"
    # BibTeX authors are typically separated by " and ".
    first = author_field.split(" and ")[0].strip()
    if "," in first:
        # "Surname, Name" form.
        return _slug(first.split(",", 1)[0].strip()) or "unknown"
    parts = _tokenize(first)
    if not parts:
        return "unknown"
    return _slug(parts[-1]) or "unknown"


def parse_bib_entries(bib_path: Path) -> Dict[str, Dict[str, str]]:
    if not bib_path.exists():
        return {}
    text = bib_path.read_text(encoding="utf-8", errors="ignore")
    entry_pat = re.compile(r"@([A-Za-z]+)\s*\{\s*([^,]+)\s*,(.*?)\n\}", re.S)
    field_pat = re.compile(r"([A-Za-z]+)\s*=\s*[\"{]([^\"}]+)[\"}]", re.S)
    out: Dict[str, Dict[str, str]] = {}
    for etype, key, body in entry_pat.findall(text):
        fields = {k.lower(): v.strip().replace("\n", " ") for k, v in field_pat.findall(body)}
        fields["entry_type"] = etype.lower()
        out[key.strip()] = fields
    return out


def extract_citation_keys(manuscript_path: Path) -> List[str]:
    if not manuscript_path.exists():
        return []
    text = manuscript_path.read_text(encoding="utf-8", errors="ignore")
    keys: List[str] = []
    for match in TEX_CITE_RE.findall(text):
        keys.extend([part.strip() for part in match.split(",") if part.strip()])
    return sorted(set(keys))


def write_bib_sources(
    wiki_root: Path,
    entries: Dict[str, Dict[str, str]],
    keys: List[str],
    stamp: str,
) -> Tuple[Dict[str, str], int]:
    sources_dir = wiki_root / "wiki" / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)

    key_to_source: Dict[str, str] = {}
    written = 0
    for key in keys:
        fields = entries.get(key)
        if not fields:
            continue
        title = fields.get("title", key)
        year = fields.get("year", "nd")
        surname = _first_author_surname(fields.get("author", ""))
        fname = f"{surname}-{year}-{_slug(title)[:40]}.md"
        source_rel = f"wiki/sources/{fname}"
        source_path = sources_dir / fname

        lines = [
            "---",
            "type: source",
            f"created: {stamp}",
            f"updated: {stamp}",
            "tags: [bibliography, sk20-autonomous-ingest]",
            f"source_key: {key}",
            f"source_presence: {'present' if source_path.exists() else 'ingested'}",
            "---",
            "",
            f"# {title}",
            "",
            f"- **Citation key:** `{key}`",
            f"- **Authors:** {fields.get('author', 'unknown')}",
            f"- **Year:** {year}",
            f"- **Entry type:** {fields.get('entry_type', 'unknown')}",
        ]
        if fields.get("journal"):
            lines.append(f"- **Journal:** {fields['journal']}")
        if fields.get("booktitle"):
            lines.append(f"- **Booktitle:** {fields['booktitle']}")
        if fields.get("doi"):
            lines.append(f"- **DOI:** {fields['doi']}")
        if fields.get("url"):
            lines.append(f"- **URL:** {fields['url']}")
        lines.extend(
            [
                "",
                "## Abstract/Notes",
                "",
                "_Bibliography-ingested placeholder source for graph grounding and citation alignment._",
            ]
        )
        source_path.write_text("\n".join(lines), encoding="utf-8")
        written += 1
        key_to_source[key] = source_rel

    return key_to_source, written


def _ensure_graphify_imports(graphify_src_root: Optional[Path]) -> None:
    if graphify_src_root and graphify_src_root.exists():
        if str(graphify_src_root) not in sys.path:
            sys.path.insert(0, str(graphify_src_root))


def augment_and_rebuild_graph(
    wiki_root: Path,
    key_to_source: Dict[str, str],
    entries: Dict[str, Dict[str, str]],
    stamp: str,
    graphify_src_root: Optional[Path],
) -> Dict[str, object]:
    _ensure_graphify_imports(graphify_src_root)

    from networkx.readwrite import json_graph  # type: ignore

    graph_out = wiki_root / "graphify-out"
    graph_json_path = graph_out / "graph.json"
    report_path = graph_out / "GRAPH_REPORT.md"
    graph_out.mkdir(parents=True, exist_ok=True)

    if graph_json_path.exists():
        raw = json.loads(graph_json_path.read_text(encoding="utf-8", errors="ignore"))
    else:
        raw = {
            "directed": True,
            "multigraph": False,
            "graph": {},
            "nodes": [],
            "links": [],
            "hyperedges": [],
        }

    nodes = raw.get("nodes", [])
    links = raw.get("links", [])
    if not isinstance(nodes, list):
        nodes = []
    if not isinstance(links, list):
        links = []

    node_by_id = {str(n.get("id")): n for n in nodes if isinstance(n, dict) and n.get("id")}
    edge_keys = set()
    for edge in links:
        if not isinstance(edge, dict):
            continue
        edge_keys.add(
            (
                str(edge.get("source")),
                str(edge.get("target")),
                str(edge.get("relation")),
                str(edge.get("source_file")),
            )
        )

    added_nodes = 0
    added_edges = 0
    for key, source_rel in key_to_source.items():
        fields = entries.get(key, {})
        bib_node_id = f"bib:{key}"
        title = fields.get("title", key)
        year = fields.get("year")
        author = fields.get("author")
        source_loc = f"citation_key:{key}"

        bib_node = {
            "id": bib_node_id,
            "label": title,
            "file_type": "paper",
            "source_file": source_rel,
            "source_location": source_loc,
            "author": author,
            "captured_at": f"{stamp}T00:00:00+00:00",
            "norm_label": title.lower(),
        }
        if bib_node_id not in node_by_id:
            nodes.append(bib_node)
            node_by_id[bib_node_id] = bib_node
            added_nodes += 1
        else:
            node_by_id[bib_node_id].update(bib_node)

        if year:
            year_node_id = f"year:{year}"
            if year_node_id not in node_by_id:
                year_node = {
                    "id": year_node_id,
                    "label": f"Year {year}",
                    "file_type": "document",
                    "source_file": source_rel,
                    "source_location": source_loc,
                    "captured_at": f"{stamp}T00:00:00+00:00",
                }
                nodes.append(year_node)
                node_by_id[year_node_id] = year_node
                added_nodes += 1
            ekey = (bib_node_id, year_node_id, "published_in", source_rel)
            if ekey not in edge_keys:
                links.append(
                    {
                        "source": bib_node_id,
                        "target": year_node_id,
                        "relation": "published_in",
                        "confidence": "EXTRACTED",
                        "confidence_score": 1.0,
                        "source_file": source_rel,
                        "source_location": source_loc,
                        "weight": 1.0,
                    }
                )
                edge_keys.add(ekey)
                added_edges += 1

    merged_raw = dict(raw)
    merged_raw["nodes"] = nodes
    merged_raw["links"] = links
    if not isinstance(merged_raw.get("hyperedges"), list):
        merged_raw["hyperedges"] = []

    fallback_reason: Optional[str] = None
    used_graphify_recluster = False

    try:
        from graphify.cluster import cluster, score_all  # type: ignore
        from graphify.analyze import god_nodes, surprising_connections, suggest_questions  # type: ignore
        from graphify.report import generate  # type: ignore
        from graphify.export import to_json  # type: ignore

        G = json_graph.node_link_graph(merged_raw, edges="links")
        communities = cluster(G)
        cohesion = score_all(G, communities)
        labels = {cid: f"Community {cid}" for cid in communities}
        gods = god_nodes(G)
        surprises = surprising_connections(G, communities)
        questions = suggest_questions(G, communities, labels)

        detection = {
            "warning": None,
            "total_files": len(key_to_source),
            "total_words": 0,
            "files": {"code": [], "document": [], "paper": list(key_to_source.values()), "image": []},
        }
        tokens = {"input": 0, "output": 0}
        report = generate(
            G,
            communities,
            cohesion,
            labels,
            gods,
            surprises,
            detection,
            tokens,
            str(wiki_root),
            suggested_questions=questions,
        )
        report_path.write_text(report, encoding="utf-8")
        to_json(G, communities, str(graph_json_path))
        used_graphify_recluster = True
    except Exception as exc:
        fallback_reason = str(exc)
        merged_raw["nodes"] = nodes
        merged_raw["links"] = links
        graph_json_path.write_text(json.dumps(merged_raw, indent=2), encoding="utf-8")
        fallback_report = [
            f"# Graph Report - {wiki_root}  ({stamp})",
            "",
            "## Autonomous Loop Fallback",
            "- Graph was augmented with bibliography-derived nodes/edges.",
            f"- Full graphify recluster/report step was skipped due to missing runtime dependency: `{fallback_reason}`",
            f"- Nodes: {len(nodes)}",
            f"- Edges: {len(links)}",
        ]
        report_path.write_text("\n".join(fallback_report), encoding="utf-8")

    final_graph = json.loads(graph_json_path.read_text(encoding="utf-8", errors="ignore"))
    return {
        "graph_json": str(graph_json_path),
        "graph_report": str(report_path),
        "node_count": len(final_graph.get("nodes", [])) if isinstance(final_graph.get("nodes"), list) else 0,
        "edge_count": len(final_graph.get("links", [])) if isinstance(final_graph.get("links"), list) else 0,
        "added_nodes": added_nodes,
        "added_edges": added_edges,
        "used_graphify_recluster": used_graphify_recluster,
        "fallback_reason": fallback_reason,
    }


def run_overlay_subprocess(
    script_path: Path,
    args: argparse.Namespace,
    stamp: str,
) -> Tuple[int, Dict[str, object], str]:
    cmd = [
        sys.executable,
        str(script_path),
        "--project-root",
        str(args.project_root),
        "--date",
        stamp,
        "--wiki-linked",
        str(args.wiki_linked),
        "--coupling-e-on-review",
        str(args.coupling_e_on_review),
        "--wiki-path",
        str(args.wiki_path),
        "--manuscript-path",
        str(args.manuscript_path),
        "--references-path",
        str(args.references_path),
        "--classification-path",
        str(args.classification_path),
        "--allow-legacy-graph-confidence",
        str(args.allow_legacy_graph_confidence),
    ]
    if args.project_claude_path:
        cmd.extend(["--project-claude-path", str(args.project_claude_path)])
    if args.allow_ancestor_claude:
        cmd.append("--allow-ancestor-claude")
    if args.allow_missing_project_claude:
        cmd.append("--allow-missing-project-claude")

    proc = subprocess.run(cmd, capture_output=True, text=True)
    parsed: Dict[str, object] = {}
    output = (proc.stdout or "").strip()
    if output:
        try:
            parsed = json.loads(output)
        except json.JSONDecodeError:
            parsed = {"raw_stdout": output}
    if proc.stderr:
        parsed["stderr"] = proc.stderr.strip()
    return proc.returncode, parsed, " ".join(cmd)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--wiki-path", required=True)
    parser.add_argument("--manuscript-path", required=True)
    parser.add_argument("--references-path", required=True)
    parser.add_argument("--classification-path", required=True)
    parser.add_argument("--date", required=False, help="Date stamp override YYYY-MM-DD")
    parser.add_argument("--project-claude-path", required=False)
    parser.add_argument("--allow-ancestor-claude", action="store_true")
    parser.add_argument("--allow-missing-project-claude", action="store_true")
    parser.add_argument("--wiki-linked", required=False, default="true")
    parser.add_argument("--coupling-e-on-review", required=False, default="true")
    parser.add_argument("--allow-legacy-graph-confidence", required=False, default="true")
    parser.add_argument(
        "--graphify-src-root",
        required=False,
        help="Optional graphify source root for imports (e.g., B:\\Agents\\graphify-main\\graphify-main)",
    )
    parser.add_argument("--ingest-all-bib-entries", action="store_true", help="Ingest all BibTeX entries, not only cited keys")
    args = parser.parse_args()

    stamp = args.date or datetime.date.today().isoformat()
    project_root = Path(args.project_root)
    wiki_root = Path(args.wiki_path)
    manuscript_path = Path(args.manuscript_path)
    references_path = Path(args.references_path)
    graphify_src_root = Path(args.graphify_src_root) if args.graphify_src_root else None

    entries = parse_bib_entries(references_path)
    cited_keys = extract_citation_keys(manuscript_path)
    target_keys = sorted(entries.keys()) if args.ingest_all_bib_entries else cited_keys

    key_to_source, files_written = write_bib_sources(
        wiki_root=wiki_root,
        entries=entries,
        keys=target_keys,
        stamp=stamp,
    )

    graph_stats = augment_and_rebuild_graph(
        wiki_root=wiki_root,
        key_to_source=key_to_source,
        entries=entries,
        stamp=stamp,
        graphify_src_root=graphify_src_root,
    )

    overlay_script = Path(__file__).parent / "sk20_overlay_run.py"
    overlay_rc, overlay_payload, overlay_cmd = run_overlay_subprocess(
        script_path=overlay_script,
        args=args,
        stamp=stamp,
    )

    reviews_dir = project_root / "reviews"
    reviews_dir.mkdir(parents=True, exist_ok=True)
    out_path = reviews_dir / f"sk20_autonomous_{stamp}.json"

    summary = {
        "status": "ok" if overlay_rc == 0 else "error",
        "date": stamp,
        "inputs": {
            "project_root": str(project_root),
            "wiki_path": str(wiki_root),
            "manuscript_path": str(manuscript_path),
            "references_path": str(references_path),
            "classification_path": str(args.classification_path),
            "wiki_linked": parse_cli_bool(str(args.wiki_linked)),
            "coupling_e_on_review": parse_cli_bool(str(args.coupling_e_on_review)),
            "allow_legacy_graph_confidence": parse_cli_bool(str(args.allow_legacy_graph_confidence)),
            "ingest_all_bib_entries": args.ingest_all_bib_entries,
            "graphify_src_root": str(graphify_src_root) if graphify_src_root else None,
        },
        "ingest": {
            "bib_entries_total": len(entries),
            "manuscript_citation_keys": len(cited_keys),
            "keys_targeted_for_ingest": len(target_keys),
            "keys_written_to_wiki_sources": len(key_to_source),
            "source_files_written": files_written,
        },
        "graph_rebuild": graph_stats,
        "overlay_run": {
            "return_code": overlay_rc,
            "command": overlay_cmd,
            "payload": overlay_payload,
        },
    }
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps({"status": summary["status"], "autonomous_report": str(out_path), "overlay": overlay_payload}, indent=2))
    return 0 if overlay_rc == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
