#!/usr/bin/env python3
"""
Runs Coupling E.2 preflight and emits deterministic gate artifacts.

Outputs:
- reviews/coupling_readiness_YYYY-MM-DD.json
- reviews/sk20_noop_YYYY-MM-DD.json (only when not ready)
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from coupling_readiness_check import derive_noop_reason, run_checks


def build_summary(results, metadata: Dict[str, object]) -> Dict[str, object]:
    ready = all(item.ok for item in results)
    failed_keys: List[str] = [item.key for item in results if not item.ok]
    reason_code, reason_detail = derive_noop_reason(results, metadata)
    return {
        "ready_for_sk20": ready,
        "failed_checks": failed_keys,
        "recommended_noop_reason_code": reason_code,
        "recommended_noop_message": reason_detail,
        "checks": [asdict(item) for item in results],
        "metadata": metadata,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True, help="Absolute path to project root")
    parser.add_argument("--date", required=False, help="Date stamp override (YYYY-MM-DD)")
    parser.add_argument(
        "--strict-exit",
        action="store_true",
        help="Return non-zero exit code when not ready",
    )
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
    stamp = args.date or datetime.now().strftime("%Y-%m-%d")
    reviews_dir = project_root / "reviews"
    readiness_path = reviews_dir / f"coupling_readiness_{stamp}.json"
    noop_path = reviews_dir / f"sk20_noop_{stamp}.json"

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
        "allow_legacy_graph_confidence": args.allow_legacy_graph_confidence,
    }
    results, metadata = run_checks(project_root, overrides=overrides)
    summary = build_summary(results, metadata)

    reviews_dir.mkdir(parents=True, exist_ok=True)
    readiness_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if not summary["ready_for_sk20"]:
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
    elif noop_path.exists():
        noop_path.unlink()

    envelope = {
        "should_run_sk20": summary["ready_for_sk20"],
        "readiness_report": str(readiness_path),
        "noop_report": str(noop_path) if noop_path.exists() else None,
        "reason_code": summary["recommended_noop_reason_code"],
    }
    print(json.dumps(envelope, indent=2))

    if args.strict_exit and not summary["ready_for_sk20"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
