#!/usr/bin/env python3
"""Load, validate, and resolve the package reader-accessibility policy.

Production code is standard-library only. Project files may narrow register
scope and override lexicons only with the polarity declared by the package
profile. Every contributing file is returned with its SHA-256 binding.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = ROOT / "references" / "policies" / "reader_accessibility.v1.json"
PHASES = ("Ph1", "Ph2", "Ph3", "Ph4")


class PolicyError(ValueError):
    pass


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _contained(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise PolicyError(f"override path escapes project root: {relative}") from exc
    return candidate


def _list_file(path: Path) -> list[str]:
    values = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if value and not value.startswith("#"):
            values.append(value)
    return list(dict.fromkeys(values))


def validate_profile(profile: dict[str, Any]) -> None:
    required = {"schema_version", "profile_version", "decision_status", "normative_authority", "package_contributors", "policy_telos", "phase_values", "passage_roles", "sub_checks", "aggregate", "adjacent_advisory_checks", "thresholds", "transitions", "register_scope", "lexicons", "domain_token_exclusions", "override_contract", "remediation_order", "corpus_drift"}
    missing = sorted(required - set(profile))
    if missing:
        raise PolicyError(f"missing profile keys: {', '.join(missing)}")
    if any("canonical_sha256" in key for key in profile):
        raise PolicyError("profile must not self-hash")
    if tuple(profile["phase_values"]) != PHASES:
        raise PolicyError("phase_values must be exactly Ph1-Ph4")
    if set(profile["sub_checks"]) != set("ABCDEFGH") or profile["aggregate"].get("members") != list("ABCDEFGH"):
        raise PolicyError("Check 8 aggregate membership must be exactly A-H")
    ve = profile.get("adjacent_advisory_checks", {}).get("VE", {})
    if ve.get("gate_contribution") != "none" or ve.get("aggregate_member") is not False:
        raise PolicyError("VE must remain outside the Check 8 aggregate")
    cadence = profile["thresholds"]["cadence"]
    if cadence.get("hard_ceiling_words") != 300 or not cadence.get("functional_confirmation_required"):
        raise PolicyError("provisional cadence decision is malformed")
    if profile.get("decision_status") != "provisional":
        raise PolicyError("ADR-ACCESS-01 has no proven acceptance; status must remain provisional")
    serialized = json.dumps(profile).lower()
    if any(token in serialized for token in ("todo", "tbd", "placeholder", "fill me", "stub")):
        raise PolicyError("profile contains unfinished data")
    for key, expected in (("plain_connectives", "replace"), ("hedges", "replace"), ("latinate_whitelist", "supplement"), ("terminology", "extend_domain_token_exclusions"), ("glossary", "extend_domain_token_exclusions")):
        if profile["override_contract"][key].get("polarity") != expected:
            raise PolicyError(f"override polarity mismatch: {key}")


def load_profile(path: Path = DEFAULT_PROFILE) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PolicyError(f"profile unreadable: {exc}") from exc
    if not isinstance(data, dict):
        raise PolicyError("profile root must be an object")
    validate_profile(data)
    return data


def evaluate_cadence(word_count: int, functional_turn_points: int, internal_break_signals: int, profile: dict[str, Any]) -> dict[str, Any]:
    cadence = profile["thresholds"]["cadence"]
    ceiling = cadence["hard_ceiling_words"]
    required = 0
    deficit = "CLEAN"
    for band in cadence["bands"]:
        if band["min_words"] <= word_count <= band["max_words"]:
            required = band["required_functional_turn_points"]
            deficit = band["deficit_severity"]
            break
    mandatory_split = word_count > ceiling
    if word_count > ceiling:
        severity = "BLOCKER" if functional_turn_points == 0 and internal_break_signals == 0 else "MAJOR"
    elif functional_turn_points < required:
        severity = deficit
    else:
        severity = "CLEAN"
    return {"word_count": word_count, "required_functional_turn_points": required, "functional_turn_points": functional_turn_points, "internal_break_signals": internal_break_signals, "current_severity": severity, "mandatory_split": mandatory_split}


def update_persistence(previous_content_sha256: str | None, current_content_sha256: str, prior_unchanged_rounds: int, current_severity: str) -> dict[str, Any]:
    unchanged = prior_unchanged_rounds + 1 if previous_content_sha256 == current_content_sha256 else 0
    return {"paragraph_content_sha256": current_content_sha256, "unchanged_rounds": unchanged, "current_severity": current_severity, "planner_workflow_escalation_candidate": unchanged >= 2}


def resolve_policy(project_root: Path | None, *, profile_path: Path = DEFAULT_PROFILE) -> dict[str, Any]:
    profile_path = profile_path.resolve()
    profile = load_profile(profile_path)
    resolved = copy.deepcopy(profile)
    bindings = [{"path": str(profile_path), "sha256": _hash(profile_path), "role": "package_profile"}]
    for relative in profile["package_contributors"]:
        contributor = (ROOT / relative).resolve()
        try:
            contributor.relative_to(ROOT)
        except ValueError as exc:
            raise PolicyError(f"package contributor escapes harness root: {relative}") from exc
        if not contributor.is_file():
            raise PolicyError(f"package contributor is missing: {relative}")
        bindings.append({"path": str(contributor), "sha256": _hash(contributor), "role": "package_contributor"})
    register_class = "technical"
    if project_root is not None:
        project_root = project_root.resolve()
        if not project_root.is_dir():
            raise PolicyError(f"project root is not a directory: {project_root}")
        contract = profile["override_contract"]
        directives = _contained(project_root, contract["directives"]["path"])
        if directives.is_file():
            text = directives.read_text(encoding="utf-8")
            match = re.search(r"(?mi)^\s*register_class\s*:\s*(technical|mixed|non-technical)\s*$", text)
            if match:
                register_class = match.group(1).lower()
            bindings.append({"path": str(directives), "sha256": _hash(directives), "role": "directives"})
        for key in ("plain_connectives", "hedges", "latinate_whitelist", "terminology", "glossary"):
            rule = contract[key]
            path = _contained(project_root, rule["path"])
            if not path.is_file():
                continue
            values = _list_file(path)
            if rule["polarity"] == "replace":
                if not values:
                    raise PolicyError(f"replace override is empty: {rule['path']}")
                resolved["lexicons"][key] = values
            elif rule["polarity"] == "supplement":
                resolved["lexicons"][key] = list(dict.fromkeys(resolved["lexicons"][key] + values))
            else:
                resolved["domain_token_exclusions"] = list(dict.fromkeys(resolved["domain_token_exclusions"] + values))
            bindings.append({"path": str(path), "sha256": _hash(path), "role": f"project_{key}", "polarity": rule["polarity"]})
    return {"contract_version": "1.0.0", "profile_path": str(profile_path), "profile_sha256": _hash(profile_path), "register_class": register_class, "resolved_profile": resolved, "source_bindings": bindings}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        result = resolve_policy(args.project_root, profile_path=args.profile)
    except PolicyError as exc:
        print(json.dumps({"status": "MISCONFIGURED", "code": "RA-POLICY", "message": str(exc)}))
        return 4
    payload = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8", newline="\n")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
