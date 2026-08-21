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
import os
import re
import stat
import sys
import tempfile
import uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from coupling_readiness_check import CheckResult, derive_noop_reason, resolve_project_claude_path, run_checks
from graph_authority_gate import evaluate_graph_authority
from milestone_path_contract import canonical_deliverable


OUTCOME_READY = "READY"
OUTCOME_NOT_APPLICABLE = "NOT_APPLICABLE"
OUTCOME_MISCONFIGURED = "MISCONFIGURED"
ALLOWED_AUTHORITIES = {"user", "venue", "advisor", "instructor", "committee", "project_local_contract"}
ALLOWED_NA_SCOPES = {"SK-20", "Coupling E.2", "Coupling E.2 / SK-20"}
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
REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


class GateIOError(RuntimeError):
    pass


class GateUsageError(ValueError):
    pass


def build_summary(results, metadata: Dict[str, object], outcome: str, reason_code: Optional[str], reason_detail: str) -> Dict[str, object]:
    ready = outcome == OUTCOME_READY
    failed_keys: List[str] = [item.key for item in results if not item.ok]
    authority = evaluate_graph_authority(
        structural_ok=metadata.get("legacy_structural_ok") if isinstance(metadata, dict) else None
    )
    return {
        "outcome": outcome,
        "ready_for_sk20": ready,
        "failed_checks": failed_keys,
        "recommended_noop_reason_code": reason_code,
        "recommended_noop_message": reason_detail,
        "checks": [asdict(item) for item in results],
        "metadata": metadata,
        "graph_authority": authority,
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


def _is_reparse(path: Path) -> bool:
    try:
        info = os.lstat(path)
    except OSError as exc:
        raise GateIOError(f"cannot inspect {path}: {exc}") from exc
    return path.is_symlink() or bool(getattr(info, "st_file_attributes", 0) & REPARSE_POINT)


def _validate_project_root(raw: str) -> Path:
    requested = Path(raw)
    try:
        if not requested.exists() or not requested.is_dir():
            raise GateIOError("project_root must be an existing directory")
        if _is_reparse(requested):
            raise GateIOError("project_root must not be a symlink, junction, or reparse point")
        return requested.resolve(strict=True)
    except OSError as exc:
        raise GateIOError(f"cannot resolve project_root: {exc}") from exc


def _parse_stamp(raw: Optional[str]) -> str:
    if raw is None:
        return datetime.now().strftime("%Y-%m-%d")
    try:
        parsed = datetime.strptime(raw, "%Y-%m-%d")
    except ValueError as exc:
        raise GateUsageError("--date must be a real calendar date in YYYY-MM-DD form") from exc
    if parsed.strftime("%Y-%m-%d") != raw:
        raise GateUsageError("--date must be exactly YYYY-MM-DD")
    return raw


def _contained_file(project_root: Path, raw: str) -> Optional[Path]:
    candidate_path = Path(raw)
    if candidate_path.is_absolute() or ".." in candidate_path.parts:
        return None
    raw_current = project_root
    for part in candidate_path.parts:
        raw_current = raw_current / part
        if raw_current.exists() or raw_current.is_symlink():
            if _is_reparse(raw_current):
                return None
    try:
        candidate = (project_root / candidate_path).resolve(strict=True)
        candidate.relative_to(project_root.resolve(strict=True))
    except (OSError, ValueError):
        return None
    current = project_root
    for part in candidate.relative_to(project_root).parts:
        current = current / part
        if _is_reparse(current):
            return None
    return candidate if candidate.is_file() else None


def _read_only_input_path(project_root: Path, raw: Optional[str], default: str) -> Path:
    if raw is None:
        candidate = project_root / default
        if candidate.exists() or candidate.is_symlink():
            if _is_reparse(candidate):
                raise GateIOError(f"default read input must not itself be a reparse point: {candidate}")
            if not candidate.is_file():
                raise GateIOError(f"default read input must be a regular file: {candidate}")
        return candidate

    candidate = Path(raw)
    try:
        if not candidate.exists() or not candidate.is_file() or _is_reparse(candidate):
            raise GateIOError(f"explicit read input must be an existing regular non-reparse file: {candidate}")
        with candidate.open("rb") as handle:
            handle.read(0)
    except OSError as exc:
        raise GateIOError(f"explicit read input is not readable: {candidate}: {exc}") from exc
    return candidate


def _ensure_safe_reviews_dir(project_root: Path) -> Path:
    reviews = project_root / "reviews"
    try:
        if reviews.exists() or reviews.is_symlink():
            if not reviews.is_dir() or _is_reparse(reviews):
                raise GateIOError("reviews must be a real project-local directory, not a file or reparse point")
        else:
            reviews.mkdir()
        resolved = reviews.resolve(strict=True)
        resolved.relative_to(project_root)
        return resolved
    except (OSError, ValueError) as exc:
        if isinstance(exc, GateIOError):
            raise
        raise GateIOError(f"cannot prepare reviews directory: {exc}") from exc


def _validate_output_target(project_root: Path, reviews: Path, target: Path) -> None:
    try:
        target.parent.resolve(strict=True).relative_to(project_root)
    except (OSError, ValueError) as exc:
        raise GateIOError(f"output target escapes project_root: {target}") from exc
    if target.parent != reviews:
        raise GateIOError(f"output target is not directly under reviews: {target}")
    if target.exists() or target.is_symlink():
        if not target.is_file() or _is_reparse(target):
            raise GateIOError(f"output target must be a regular non-reparse file: {target}")


def _stage_json(reviews: Path, payload: Dict[str, object]) -> Path:
    descriptor, name = tempfile.mkstemp(prefix=".sk20-", suffix=".tmp", dir=reviews)
    staged = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        return staged
    except BaseException:
        try:
            staged.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _commit_outputs(
    project_root: Path,
    writes: Dict[Path, Dict[str, object]],
    deletes: List[Path],
    *,
    remove_backup=None,
) -> List[str]:
    reviews = _ensure_safe_reviews_dir(project_root)
    prior_backups: List[Path] = []
    prior_warnings: List[str] = []
    for candidate in reviews.glob(".*.bak"):
        if not (
            candidate.name.startswith(".coupling_readiness_")
            or candidate.name.startswith(".sk20_noop_")
        ):
            continue
        if not candidate.is_file() or _is_reparse(candidate):
            prior_warnings.append(f"unsafe stale backup residue requires manual inspection: {candidate.name}")
        else:
            prior_backups.append(candidate)
    targets = list(writes) + deletes
    for target in targets:
        _validate_output_target(project_root, reviews, target)
    staged: Dict[Path, Path] = {}
    backups: Dict[Path, Path] = {}
    placed: List[Path] = []
    try:
        for target, payload in writes.items():
            staged[target] = _stage_json(reviews, payload)
        for target in targets:
            if target.exists():
                backup = reviews / f".{target.name}.{uuid.uuid4().hex}.bak"
                os.replace(target, backup)
                backups[target] = backup
        for target, temporary in staged.items():
            os.replace(temporary, target)
            placed.append(target)
    except OSError as exc:
        for target in reversed(placed):
            try:
                target.unlink(missing_ok=True)
            except OSError:
                pass
        for target, backup in backups.items():
            try:
                if backup.exists():
                    os.replace(backup, target)
            except OSError:
                pass
        raise GateIOError(f"atomic SK-20 evidence update failed: {exc}") from exc
    finally:
        for temporary in staged.values():
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass

    cleanup = remove_backup or (lambda path: path.unlink())
    warnings: List[str] = list(prior_warnings)
    for backup in backups.values():
        try:
            cleanup(backup)
        except OSError as exc:
            warnings.append(f"committed evidence; backup cleanup deferred for {backup.name}: {exc}")
    for backup in prior_backups:
        try:
            backup.unlink()
        except OSError as exc:
            warnings.append(f"stale backup cleanup remains deferred for {backup.name}: {exc}")
    return warnings


def _resolve_configuration(project_root: Path, args: argparse.Namespace) -> Tuple[str, Dict[str, object], str, str]:
    local_agents = project_root / "AGENTS.md"
    local_claude = project_root / "CLAUDE.md"
    if args.project_claude_path:
        explicit = Path(args.project_claude_path).resolve(strict=True)
        try:
            relative = str(explicit.relative_to(project_root))
            resolved_claude = _contained_file(project_root, relative)
        except ValueError:
            if (
                not args.allow_ancestor_claude
                or explicit.name not in {"AGENTS.md", "CLAUDE.md"}
                or explicit.parent not in project_root.parents
            ):
                raise GateIOError("explicit project AGENTS.md must be contained or an allowed ancestor AGENTS.md")
            if not explicit.is_file() or _is_reparse(explicit):
                raise GateIOError("ancestor AGENTS.md must be a regular non-reparse file")
            resolved_claude = explicit
    elif local_agents.exists() or local_agents.is_symlink():
        resolved_claude = _contained_file(project_root, "AGENTS.md")
        if resolved_claude is None:
            raise GateIOError("project AGENTS.md must be a contained non-reparse file")
    elif local_claude.exists() or local_claude.is_symlink():
        resolved_claude = _contained_file(project_root, "CLAUDE.md")
        if resolved_claude is None:
            raise GateIOError("legacy project CLAUDE.md must be a contained non-reparse file")
    else:
        resolved_claude = resolve_project_claude_path(project_root, allow_ancestor=args.allow_ancestor_claude)
    claude_path = resolved_claude or project_root / "AGENTS.md"
    claude_fields, errors = _read_fields(claude_path)
    directives_path = project_root / "research_notes" / "directives.md"
    if directives_path.exists() or directives_path.is_symlink():
        safe_directives = _contained_file(project_root, "research_notes/directives.md")
        if safe_directives is None:
            raise GateIOError("research_notes/directives.md must be a contained non-reparse file")
        directives_path = safe_directives
    directive_fields, directive_errors = _read_fields(directives_path)
    errors.extend(directive_errors)

    cli_fields = {
        key: value for key, value in {
            "wiki_linked": args.wiki_linked,
            "coupling_e_on_review": args.coupling_e_on_review,
            "wiki_path": args.wiki_path,
            "sk20_not_applicable_authority": args.sk20_not_applicable_authority,
            "sk20_not_applicable_reason": args.sk20_not_applicable_reason,
            "sk20_not_applicable_scope": args.sk20_not_applicable_scope,
            "sk20_not_applicable_substitute_evidence": args.sk20_not_applicable_substitute_evidence,
        }.items() if value is not None
    }
    layers = [("project AGENTS.md", claude_fields), ("research_notes/directives.md", directive_fields), ("CLI", cli_fields)]
    effective: Dict[str, str] = {}
    for _, layer in layers:
        effective.update(layer)

    wiki_linked = _strict_bool(effective.get("wiki_linked"), "wiki_linked", errors)
    coupling_enabled = _strict_bool(effective.get("coupling_e_on_review"), "coupling_e_on_review", errors)
    active_layers = [name for name, layer in layers if layer]
    metadata: Dict[str, object] = {
        "project_root": str(project_root),
        "configuration_layers": active_layers,
        "configuration_precedence": "CLI > research_notes/directives.md > project AGENTS.md > package",
    }

    if not claude_path.is_file() and not args.allow_missing_project_claude:
        errors.append("missing project AGENTS.md")
    if wiki_linked is False and coupling_enabled is True:
        errors.append("coupling_e_on_review=true contradicts wiki_linked=false")
    if errors:
        return OUTCOME_MISCONFIGURED, metadata, "SK20_CONFIG_INVALID", "; ".join(errors)

    if wiki_linked is False or coupling_enabled is False:
        false_sources: List[Tuple[int, str, Dict[str, str]]] = []
        for key in ("wiki_linked", "coupling_e_on_review"):
            if effective.get(key, "").strip().lower() != "false":
                continue
            for index in range(len(layers) - 1, -1, -1):
                name, layer = layers[index]
                if key in layer:
                    false_sources.append((index, name, layer))
                    break
        _, authorization_source, authorization_layer = max(false_sources, key=lambda item: item[0])
        required = {
            "authority": authorization_layer.get("sk20_not_applicable_authority"),
            "reason": authorization_layer.get("sk20_not_applicable_reason"),
            "scope": authorization_layer.get("sk20_not_applicable_scope"),
            "substitute_evidence": authorization_layer.get("sk20_not_applicable_substitute_evidence"),
        }
        missing = [key for key, value in required.items() if not isinstance(value, str) or not value.strip()]
        authority = str(required["authority"] or "").strip()
        if authority and authority not in ALLOWED_AUTHORITIES:
            missing.append("allowed authority")
        scope = str(required["scope"] or "").strip()
        if scope and scope not in ALLOWED_NA_SCOPES:
            missing.append("scope explicitly naming SK-20 or Coupling E.2")
        evidence_raw = str(required["substitute_evidence"] or "").strip()
        if evidence_raw and _contained_file(project_root, evidence_raw) is None:
            missing.append("contained existing substitute_evidence")
        if missing:
            return (
                OUTCOME_MISCONFIGURED,
                metadata,
                "SK20_OVERRIDE_INCOMPLETE",
                f"not-applicable authorization must be complete in {authorization_source}; requires " + ", ".join(missing),
            )
        metadata["authorization_source"] = authorization_source
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
    parser.add_argument("--sk20-not-applicable-authority", required=False, help="CLI-layer N/A authority")
    parser.add_argument("--sk20-not-applicable-reason", required=False, help="CLI-layer N/A reason")
    parser.add_argument("--sk20-not-applicable-scope", required=False, help="CLI-layer N/A scope")
    parser.add_argument("--sk20-not-applicable-substitute-evidence", required=False, help="CLI-layer project-relative substitute evidence")
    parser.add_argument("--wiki-path", required=False, help="Override wiki path")
    parser.add_argument("--manuscript-path", required=False, help="Override manuscript path")
    parser.add_argument("--references-path", required=False, help="Override references path")
    parser.add_argument("--classification-path", required=False, help="Override classification path")
    parser.add_argument("--allow-legacy-graph-confidence", required=False, help="Allow compatibility normalization for legacy numeric/null graph confidence values (true/false)")
    args = parser.parse_args()

    from destination_capability import DestinationRefused, guard_project_root
    try:
        guard_project_root(args.project_root)
    except DestinationRefused as exc:
        print(f"[BLOCKER] {exc}")
        return 4

    try:
        stamp = _parse_stamp(args.date)
    except GateUsageError as exc:
        print(json.dumps({"outcome": OUTCOME_MISCONFIGURED, "error_code": "SK20_USAGE", "message": str(exc)}, indent=2))
        return 1

    try:
        project_root = _validate_project_root(args.project_root)
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
        default_manuscript = canonical_deliverable("M4")
        if not (project_root / default_manuscript).is_file():
            default_manuscript = canonical_deliverable("M3")
        overrides["manuscript_path"] = str(_read_only_input_path(project_root, args.manuscript_path, default_manuscript))
        overrides["references_path"] = str(_read_only_input_path(project_root, args.references_path, "references/REFERENCES.md"))
        overrides["classification_path"] = str(_read_only_input_path(project_root, args.classification_path, "reviews/classification.md"))
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
        writes = {readiness_path: summary}
        deletes: List[Path] = []
        if summary["ready_for_sk20"]:
            deletes.append(noop_path)
        else:
            writes[noop_path] = noop_payload
        output_warnings = _commit_outputs(project_root, writes, deletes)
    except (GateIOError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(json.dumps({"outcome": OUTCOME_MISCONFIGURED, "error_code": "SK20_IO", "message": str(exc)}, indent=2))
        return 2

    envelope = {
        "outcome": summary["outcome"],
        "should_run_sk20": summary["ready_for_sk20"],
        "readiness_report": str(readiness_path),
        "noop_report": str(noop_path) if noop_path.exists() else None,
        "reason_code": summary["recommended_noop_reason_code"],
        "warnings": output_warnings,
    }
    print(json.dumps(envelope, indent=2))

    if args.strict_exit and summary["outcome"] == OUTCOME_MISCONFIGURED:
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
