#!/usr/bin/env python3
"""Resolve and validate a project's D-STYLE profile.

This is a routing check, not a judgment check. It reads the optional
``d_style_profile`` block in ``research_notes/directives.md``, validates the
declared enum values, resolves inherit-by-absence defaults, and emits the
review obligations the Planner/Evaluator must consider.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


FIELDS = {
    "question_type": {"conceptual", "practical", "applied", "mixed", "tbd"},
    "citation_style": {"turabian_author_date", "venue_template", "acm", "lncs", "tbd"},
    "source_role_policy": {"strict_role_classification", "venue_default", "project_defined"},
    "evidence_display_policy": {"standard", "visual_ethics_required", "project_defined"},
    "assistance_disclosure_policy": {"project_local", "venue_required", "overseer_escalate"},
    "harness_profile": {
        "standard_research_review",
        "thesis_qe",
        "venue_submission",
        "supervisor_memo",
    },
}

DEFAULTS = {
    "question_type": "tbd",
    "citation_style": "tbd",
    "source_role_policy": "strict_role_classification",
    "evidence_display_policy": "standard",
    "assistance_disclosure_policy": "project_local",
    "harness_profile": "standard_research_review",
}


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    message: str
    field: str | None = None


def _strip_inline_comment(value: str) -> str:
    in_single = False
    in_double = False
    for index, char in enumerate(value):
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            return value[:index].strip()
    return value.strip()


def _clean_value(raw: str) -> str:
    value = _strip_inline_comment(raw).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1].strip()
    return value


def parse_profile(text: str) -> tuple[dict[str, str], bool]:
    """Parse the simple directives.md block:

    d_style_profile:
      question_type: mixed
      ...
    """

    lines = text.splitlines()
    profile: dict[str, str] = {}
    in_block = False
    base_indent = 0

    for line in lines:
        stripped = line.strip()
        if not in_block:
            if stripped == "d_style_profile:":
                in_block = True
                base_indent = len(line) - len(line.lstrip(" "))
            continue

        if not stripped or stripped.startswith("#"):
            continue

        indent = len(line) - len(line.lstrip(" "))
        if indent <= base_indent:
            break

        if ":" not in stripped:
            continue
        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        profile[key] = _clean_value(raw_value)

    return profile, in_block


def resolve_profile(raw_profile: dict[str, str]) -> dict[str, str]:
    resolved = dict(DEFAULTS)
    for key, value in raw_profile.items():
        if value:
            resolved[key] = value
    return resolved


def validate_profile(
    raw_profile: dict[str, str],
    resolved_profile: dict[str, str],
    profile_declared: bool,
) -> list[Finding]:
    findings: list[Finding] = []
    if not profile_declared:
        findings.append(
            Finding(
                "INFO",
                "DSTYLE_PROFILE_INHERITED",
                "No d_style_profile block declared; inherited D-STYLE defaults are active.",
            )
        )

    unknown_fields = sorted(set(raw_profile) - set(FIELDS))
    for field in unknown_fields:
        findings.append(
            Finding(
                "MINOR",
                "DSTYLE_PROFILE_UNKNOWN_FIELD",
                f"Unknown d_style_profile field ignored: {field}.",
                field,
            )
        )

    for field, allowed in FIELDS.items():
        value = resolved_profile[field]
        if value not in allowed:
            findings.append(
                Finding(
                    "BLOCKER",
                    "DSTYLE_PROFILE_BAD_ENUM",
                    f"{field}={value!r} is not one of: {', '.join(sorted(allowed))}.",
                    field,
                )
            )

    if resolved_profile["question_type"] == "tbd":
        findings.append(
            Finding(
                "MINOR",
                "DSTYLE_PROFILE_QUESTION_TYPE_TBD",
                "question_type remains tbd; replace before claiming argument readiness.",
                "question_type",
            )
        )
    if resolved_profile["citation_style"] == "tbd":
        findings.append(
            Finding(
                "MINOR",
                "DSTYLE_PROFILE_CITATION_STYLE_TBD",
                "citation_style remains tbd; resolve before citation/form review or promotion.",
                "citation_style",
            )
        )

    return findings


def build_obligations(profile: dict[str, str]) -> list[dict[str, str]]:
    obligations = [
        {
            "id": "grounding_floor",
            "status": "active",
            "source": "GROUNDING_PROTOCOL.md",
            "note": "Read-before-cite, compute-before-report, and no gap-filling remain binding.",
        },
        {
            "id": "claim_reason_evidence_warrant",
            "status": "active",
            "source": "D-STYLE",
            "note": "Expose claim, reasons, evidence, warrants, objections, and limits.",
        },
        {
            "id": "reader_so_what_gate",
            "status": "active",
            "source": "D-STYLE",
            "note": f"Question type resolved as {profile['question_type']}; review why this reader should care.",
        },
    ]

    if profile["source_role_policy"] == "strict_role_classification":
        obligations.append(
            {
                "id": "source_role_classification",
                "status": "active",
                "source": "D-STYLE",
                "note": "Classify source roles before allowing them to carry claims.",
            }
        )
    elif profile["source_role_policy"] == "project_defined":
        obligations.append(
            {
                "id": "source_role_policy_project_defined",
                "status": "active",
                "source": "research_notes/directives.md",
                "note": "Apply the project-defined source role policy and cite the directive.",
            }
        )

    if profile["evidence_display_policy"] == "visual_ethics_required":
        obligations.append(
            {
                "id": "visual_evidence_ethics",
                "status": "active_unenforced",
                "source": "D-STYLE open front",
                "note": "Evaluator must review scale choices, transformations, source lines, and display limits.",
            }
        )
    elif profile["evidence_display_policy"] == "project_defined":
        obligations.append(
            {
                "id": "evidence_display_policy_project_defined",
                "status": "active",
                "source": "research_notes/directives.md",
                "note": "Apply the project-defined evidence-display policy and cite the directive.",
            }
        )

    if profile["assistance_disclosure_policy"] == "venue_required":
        obligations.append(
            {
                "id": "assistance_disclosure_venue",
                "status": "active",
                "source": "venue rules",
                "note": "Check venue disclosure requirements for material assistance.",
            }
        )
    elif profile["assistance_disclosure_policy"] == "overseer_escalate":
        obligations.append(
            {
                "id": "assistance_boundary_overseer",
                "status": "active",
                "source": "Overseer doctrine",
                "note": "Escalate material-assistance disclosure questions to Overseer/user governance.",
            }
        )
    else:
        obligations.append(
            {
                "id": "assistance_boundary_project_local",
                "status": "active_unenforced",
                "source": "D-STYLE open front",
                "note": "Log material AI/reviewer/collaborator assistance per project-local rules.",
            }
        )

    harness_profile = profile["harness_profile"]
    if harness_profile == "thesis_qe":
        obligations.extend(
            [
                {
                    "id": "candidate_vs_canonical_status",
                    "status": "active",
                    "source": "project governance",
                    "note": "Verify candidate/non-canonical vs canonical status before promotion claims.",
                },
                {
                    "id": "advisor_committee_constraints",
                    "status": "active",
                    "source": "project governance",
                    "note": "Check advisor/QE constraints and avoid resolving open decisions by implication.",
                },
            ]
        )
    elif harness_profile == "venue_submission":
        obligations.extend(
            [
                {
                    "id": "venue_template_precedence",
                    "status": "active",
                    "source": "venue rules",
                    "note": "Venue template overrides D-STYLE/Turabian where they conflict.",
                },
                {
                    "id": "external_verification",
                    "status": "active",
                    "source": "EXTERNAL_VERIFIERS.md",
                    "note": "Submission-bound cited claims require external verification where applicable.",
                },
            ]
        )
    elif harness_profile == "supervisor_memo":
        obligations.append(
            {
                "id": "supervisor_facing_scope",
                "status": "active",
                "source": "D-STYLE",
                "note": "Make scope, decision asks, and unresolved fronts visible to the advisor.",
            }
        )

    return obligations


def verdict(findings: Iterable[Finding]) -> str:
    severities = {finding.severity for finding in findings}
    if "BLOCKER" in severities:
        return "BLOCKER"
    if "MAJOR" in severities:
        return "MAJOR"
    if "MINOR" in severities:
        return "ADVISORY"
    return "CLEAN"


def build_report(project_root: Path, directives_path: Path) -> dict[str, object]:
    if directives_path.exists():
        text = directives_path.read_text(encoding="utf-8")
        raw_profile, profile_declared = parse_profile(text)
    else:
        raw_profile = {}
        profile_declared = False

    resolved = resolve_profile(raw_profile)
    findings = validate_profile(raw_profile, resolved, profile_declared)
    return {
        "schema_version": "1.0.0",
        "check": "d_style_profile",
        "project_root": str(project_root),
        "directives_path": str(directives_path),
        "directives_exists": directives_path.exists(),
        "profile_declared": profile_declared,
        "raw_profile": raw_profile,
        "resolved_profile": resolved,
        "active_obligations": build_obligations(resolved),
        "findings": [asdict(finding) for finding in findings],
        "verdict": verdict(findings),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True, help="Project root containing research_notes/")
    parser.add_argument("--directives-path", help="Optional explicit directives.md path")
    parser.add_argument("--date", help="Date stamp override (YYYY-MM-DD)")
    parser.add_argument("--output", help="Optional output JSON path")
    parser.add_argument("--no-write", action="store_true", help="Print only; do not write a review artifact")
    parser.add_argument("--strict-exit", action="store_true", help="Return non-zero on BLOCKER")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    directives_path = (
        Path(args.directives_path).resolve()
        if args.directives_path
        else project_root / "research_notes" / "directives.md"
    )
    report = build_report(project_root, directives_path)

    output_path: Path | None = None
    if not args.no_write:
        stamp = args.date or datetime.now().strftime("%Y-%m-%d")
        output_path = Path(args.output).resolve() if args.output else project_root / "reviews" / f"d_style_profile_{stamp}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    envelope = {
        "verdict": report["verdict"],
        "profile_declared": report["profile_declared"],
        "resolved_profile": report["resolved_profile"],
        "active_obligation_ids": [item["id"] for item in report["active_obligations"]],
        "report_path": str(output_path) if output_path else None,
    }
    print(json.dumps(envelope, indent=2))

    if args.strict_exit and report["verdict"] == "BLOCKER":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
