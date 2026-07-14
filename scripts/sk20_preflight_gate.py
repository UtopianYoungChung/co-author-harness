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
import re
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from coupling_readiness_check import CheckResult, derive_noop_reason, resolve_project_claude_path, run_checks


OUTCOME_READY = "READY"
OUTCOME_NOT_APPLICABLE = "NOT_APPLICABLE"
OUTCOME_MISCONFIGURED = "MISCONFIGURED"
ALLOWED_AUTHORITIES = {"user", "venue", "advisor", "instructor", "committee", "project_local_contract"}
CONFIG_KEYS = {
    "wiki_linked",
    "wiki_path",
    "coupling_e_on_review",
    "sk20_not_applicable_authority",
    "sk20_not_applicable_reason",
    "sk20_not_applicable_scope",
    "sk20_not_applicable_substitute_evidence",
}
TABLE_FIELD_RE = re.compile(r"^\s*\|\s*`?([a-z0-9_]+)`?\s*\|\s*`?([^|`]+?)`?\s*\|\s*$", re.IGNORECASE)
PLAIN_FIELD_RE = re.compile(r"^\s*`?([a-z0-9_]+)`?\s*:\s*`?(.+?)`?\s*$", re.IGNORECASE)


def build_summary(results, metadata: Dict[str, object], outcome: str, reason_code: Optional[str], reason_detail: str) -> Dict[str, object]:
    ready = outcome == OUTCOME_READY
    failed_keys: List[str] = [item.key for item in results if not item.ok]
    return {
        "outcome": outcome,
        "ready_for_sk20": ready,
        "failed_checks": failed_keys,
        "recommended_noop_reason_code": reason_code,
        "recommended_noop_message": reason_detail,
        "checks": [asdict(item) for item in results],
        "metadata": metadata,
    }


def _read_fields(path: Path) -> Tuple[Dict[str, str], List[str]]:
    if not path.is_file():
        return {}, []
    values: Dict[str, str] = {}
    errors: List[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = TABLE_FIELD_RE.match(line) or PLAIN_FIELD_RE.match(line)
        if not match:
            continue
        key, value = match.group(1).lower(), match.group(2).strip().strip("`").strip()
        if key not in CONFIG_KEYS:
            continue
        if key in values and values[key] != value:
            errors.append(f"contradictory duplicate {key} in {path}")
        values[key] = value
    return values, errors


def _strict_bool(value: Optional[str], key: str, errors: List[str]) -> Optional[bool]:
    if value is None:
        errors.append(f"missing required {key}")
        return None
    normalized = value.strip().lower()
    if normalized not in {"true", "false"}:
        errors.append(f"{key} must be exactly true or false, got {value!r}")
        return None
    return normalized == "true"


def _is_contained_file(project_root: Path, relative: str) -> bool:
    candidate_path = Path(relative)
    if candidate_path.is_absolute() or ".." in candidate_path.parts:
        return False
    try:
        candidate = (project_root / candidate_path).resolve(strict=True)
        candidate.relative_to(project_root.resolve(strict=True))
    except (OSError, ValueError):
        return False
    return candidate.is_file()


def _resolve_configuration(project_root: Path, args: argparse.Namespace) -> Tuple[str, Dict[str, object], str, str]:
    resolved_claude = resolve_project_claude_path(
        project_root,
        explicit_path=args.project_claude_path,
        allow_ancestor=args.allow_ancestor_claude,
    )
    claude_path = resolved_claude or project_root / "CLAUDE.md"
    claude_fields, errors = _read_fields(claude_path)
    directives_path = project_root / "research_notes" / "directives.md"
    directive_fields, directive_errors = _read_fields(directives_path)
    errors.extend(directive_errors)

    effective = dict(claude_fields)
    if directive_fields:
        effective.update(directive_fields)
    if args.wiki_linked is not None:
        effective["wiki_linked"] = args.wiki_linked
    if args.coupling_e_on_review is not None:
        effective["coupling_e_on_review"] = args.coupling_e_on_review
    if args.wiki_path is not None:
        effective["wiki_path"] = args.wiki_path

    wiki_linked = _strict_bool(effective.get("wiki_linked"), "wiki_linked", errors)
    coupling_enabled = _strict_bool(effective.get("coupling_e_on_review"), "coupling_e_on_review", errors)
    source = "research_notes/directives.md" if directive_fields else (str(claude_path) if claude_path.is_file() else None)
    metadata: Dict[str, object] = {
        "project_root": str(project_root),
        "configuration_source": source,
        "configuration_precedence": "CLI > research_notes/directives.md > project CLAUDE.md > package",
    }

    if not claude_path.is_file() and not args.allow_missing_project_claude:
        errors.append("missing project CLAUDE.md")
    if wiki_linked is False and coupling_enabled is True:
        errors.append("coupling_e_on_review=true contradicts wiki_linked=false")
    if errors:
        return OUTCOME_MISCONFIGURED, metadata, "SK20_CONFIG_INVALID", "; ".join(errors)

    if wiki_linked is False or coupling_enabled is False:
        required = {
            "authority": effective.get("sk20_not_applicable_authority"),
            "reason": effective.get("sk20_not_applicable_reason"),
            "scope": effective.get("sk20_not_applicable_scope"),
            "substitute_evidence": effective.get("sk20_not_applicable_substitute_evidence"),
        }
        missing = [key for key, value in required.items() if not isinstance(value, str) or not value.strip()]
        authority = str(required["authority"] or "").strip()
        if authority and authority not in ALLOWED_AUTHORITIES:
            missing.append("allowed authority")
        evidence_raw = str(required["substitute_evidence"] or "").strip()
        if evidence_raw and not _is_contained_file(project_root, evidence_raw):
            missing.append("contained existing substitute_evidence")
        if missing:
            return (
                OUTCOME_MISCONFIGURED,
                metadata,
                "SK20_OVERRIDE_INCOMPLETE",
                "not-applicable configuration requires " + ", ".join(missing),
            )
        metadata["not_applicable"] = required
        return OUTCOME_NOT_APPLICABLE, metadata, "AUTHORIZED_NOT_APPLICABLE", str(required["reason"])

    if not effective.get("wiki_path"):
        return OUTCOME_MISCONFIGURED, metadata, "WIKI_PATH_MISSING", "enabled SK-20 requires wiki_path"
    metadata["effective_config"] = {
        "wiki_linked": True,
        "coupling_e_on_review": True,
        "wiki_path": effective["wiki_path"],
    }
    return OUTCOME_READY, metadata, "", ""


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
    try:
        applicability, config_metadata, reason_code, reason_detail = _resolve_configuration(project_root, args)
        if applicability == OUTCOME_READY:
            effective = config_metadata["effective_config"]
            overrides["wiki_linked"] = "true"
            overrides["coupling_e_on_review"] = "true"
            overrides["wiki_path"] = effective["wiki_path"]
            results, check_metadata = run_checks(project_root, overrides=overrides)
            config_metadata.update(check_metadata)
            if all(item.ok for item in results):
                outcome = OUTCOME_READY
                reason_code, reason_detail = None, ""
            else:
                outcome = OUTCOME_MISCONFIGURED
                reason_code, reason_detail = derive_noop_reason(results, config_metadata)
        else:
            outcome = applicability
            results = [] if outcome == OUTCOME_NOT_APPLICABLE else [
                CheckResult("sk20_configuration", False, reason_detail)
            ]
        summary = build_summary(results, config_metadata, outcome, reason_code, reason_detail)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"outcome": OUTCOME_MISCONFIGURED, "error": str(exc)}, indent=2))
        return 2

    reviews_dir.mkdir(parents=True, exist_ok=True)
    readiness_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if not summary["ready_for_sk20"]:
        noop_payload = {
            "skill": "SK-20",
            "status": "noop",
            "outcome": summary["outcome"],
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
        "outcome": summary["outcome"],
        "should_run_sk20": summary["ready_for_sk20"],
        "readiness_report": str(readiness_path),
        "noop_report": str(noop_path) if noop_path.exists() else None,
        "reason_code": summary["recommended_noop_reason_code"],
    }
    print(json.dumps(envelope, indent=2))

    if args.strict_exit and summary["outcome"] == OUTCOME_MISCONFIGURED:
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
