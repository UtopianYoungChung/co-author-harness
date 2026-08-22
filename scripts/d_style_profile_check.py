#!/usr/bin/env python3
"""Resolve and validate a project's D-STYLE profile.

This is a routing and surface-validation check, not a quality-judgment check. It reads the optional
``d_style_profile`` block in ``research_notes/directives.md``, validates the
declared enum values, resolves inherit-by-absence defaults, and emits the
review obligations the Planner/Evaluator must consider. When passed a manuscript,
it also checks that claim/warrant, visual-evidence, assistance-boundary,
abstract-citation, and introduction-roadmap surfaces are visible enough
for Evaluator judgment.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


FIELDS = {
    "question_type": {"conceptual", "practical", "applied", "mixed", "tbd"},
    "citation_style": {
        "turabian_author_date",
        "turabian_notes_bibliography",
        "venue_template",
        "acm",
        "lncs",
        "tbd",
    },
    "source_role_policy": {"strict_role_classification", "venue_default", "project_defined"},
    "evidence_display_policy": {"standard", "visual_ethics_required", "project_defined"},
    "assistance_disclosure_policy": {"project_local", "venue_required", "overseer_escalate"},
    "abstract_citation_policy": {"tbd", "required", "forbidden"},
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
    "abstract_citation_policy": "tbd",
    "harness_profile": "standard_research_review",
}


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    message: str
    field: str | None = None
    locator: str | None = None


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
    if resolved_profile["abstract_citation_policy"] == "tbd":
        findings.append(
            Finding(
                "INFO",
                "DSTYLE_PROFILE_ABSTRACT_CITATION_POLICY_TBD",
                "abstract_citation_policy remains tbd; record abstract citation presence or absence as INFO only. Do not insert or strip abstract citations to close a finding.",
                "abstract_citation_policy",
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
                "status": "active",
                "source": "D-STYLE",
                "note": "Pre-flight checks for source, scale/axis, transformation/method, and display-limit surfaces; Evaluator judges adequacy.",
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
                "status": "active",
                "source": "D-STYLE",
                "note": "Pre-flight checks for assistance disclosure or assistance log surfaces; Evaluator judges adequacy.",
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


def _has_any(text: str, patterns: Iterable[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE) for pattern in patterns)


def _line_for(text: str, pattern: str) -> int | None:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    if not match:
        return None
    return text[: match.start()].count("\n") + 1


def _locator(path: Path | None, line: int | None) -> str | None:
    if path is None or line is None:
        return None
    return f"{path}:{line}"


def _has_visual_evidence(text: str) -> bool:
    return _has_any(
        text,
        [
            r"^\s*(figure|fig\.|table|chart|graph)\s+\d+",
            r"!\[[^\]]*\]\([^)]+\)",
            r"<img\b",
            r"\|[^\n]*\|[^\n]*\n\s*\|[-:\s|]+\|",
        ],
    )


def validate_argument_surface(text: str, manuscript_path: Path | None) -> list[Finding]:
    checks = [
        (
            "DSTYLE_ARGUMENT_CLAIM_SURFACE_MISSING",
            "claim",
            "No explicit claim/thesis/argument surface detected.",
            [r"\b(claim|thesis|argument)\b", r"\b(i|we|this paper|this memo|this chapter)\s+argue[s]?\b"],
        ),
        (
            "DSTYLE_ARGUMENT_REASON_SURFACE_MISSING",
            "reason",
            "No explicit reason/because/explanation surface detected.",
            [r"\b(reason|because|explains?|therefore|so that|in order to)\b"],
        ),
        (
            "DSTYLE_ARGUMENT_EVIDENCE_SURFACE_MISSING",
            "evidence",
            "No explicit evidence/citation/example/source surface detected.",
            [r"\b(evidence|data|example|source|according to)\b", r"\([A-Z][A-Za-z-]+(?:\s+and\s+[A-Z][A-Za-z-]+)?\s+\d{4}"],
        ),
        (
            "DSTYLE_ARGUMENT_WARRANT_SURFACE_MISSING",
            "warrant",
            "No explicit warrant/assumption/premise/stakes surface detected.",
            [r"\b(warrant|assumption|premise|stakes|so what|this matters because)\b"],
        ),
        (
            "DSTYLE_ARGUMENT_LIMIT_SURFACE_MISSING",
            "limit",
            "No explicit objection/limitation/scope/alternative surface detected.",
            [r"\b(objection|counterargument|limitation|limit|scope|alternative explanation|however|although)\b"],
        ),
    ]

    findings: list[Finding] = []
    for code, field, message, patterns in checks:
        if not _has_any(text, patterns):
            findings.append(Finding("MAJOR", code, message, field))
    if not findings:
        line = _line_for(text, r"\b(claim|thesis|argument)\b")
        findings.append(
            Finding(
                "INFO",
                "DSTYLE_ARGUMENT_SURFACE_PRESENT",
                "Claim/reason/evidence/warrant/limit surfaces detected; Evaluator must judge adequacy.",
                "argument_surface",
                _locator(manuscript_path, line),
            )
        )
    return findings


def validate_visual_evidence_surface(
    profile: dict[str, str],
    text: str,
    manuscript_path: Path | None,
) -> list[Finding]:
    if profile["evidence_display_policy"] != "visual_ethics_required" and not _has_visual_evidence(text):
        return []

    if not _has_visual_evidence(text):
        return [
            Finding(
                "INFO",
                "DSTYLE_VISUAL_EVIDENCE_NOT_PRESENT",
                "Visual-evidence policy is active, but no table/figure/image surface was detected.",
                "evidence_display_policy",
            )
        ]

    findings: list[Finding] = []
    requirements = [
        (
            "DSTYLE_VISUAL_SOURCE_SURFACE_MISSING",
            "No visual-evidence source/caption/source-note surface detected.",
            [r"\b(source|caption|note:|data source)\b"],
        ),
        (
            "DSTYLE_VISUAL_SCALE_SURFACE_MISSING",
            "No visual-evidence scale/axis/unit/denominator surface detected.",
            [r"\b(scale|axis|axes|unit|denominator|n\s*=|sample)\b"],
        ),
        (
            "DSTYLE_VISUAL_TRANSFORM_SURFACE_MISSING",
            "No visual-evidence method/transformation/aggregation/filter surface detected.",
            [r"\b(method|transform|transformation|aggregate|aggregation|filtered?|normalized?|coded?)\b"],
        ),
        (
            "DSTYLE_VISUAL_LIMIT_SURFACE_MISSING",
            "No visual-evidence limitation/interpretive caution surface detected.",
            [r"\b(limit|limitation|caution|interpret|cannot show|does not show)\b"],
        ),
    ]
    for code, message, patterns in requirements:
        if not _has_any(text, patterns):
            findings.append(Finding("MAJOR", code, message, "visual_evidence"))
    if not findings:
        line = _line_for(text, r"^\s*(figure|fig\.|table|chart|graph)\s+\d+|!\[[^\]]*\]\([^)]+\)")
        findings.append(
            Finding(
                "INFO",
                "DSTYLE_VISUAL_EVIDENCE_SURFACE_PRESENT",
                "Visual-evidence source, scale, method, and limit surfaces detected; Evaluator must judge adequacy.",
                "visual_evidence",
                _locator(manuscript_path, line),
            )
        )
    return findings


_ABSTRACT_START = re.compile(
    r"^(?:#{1,3}\s+abstract\b|\\begin\{abstract\})",
    re.IGNORECASE | re.MULTILINE,
)
_ABSTRACT_END = re.compile(
    r"^(?:#{1,3}\s+\S|\\end\{abstract\})",
    re.MULTILINE,
)
_CITATION_SURFACE = [
    r"\([A-Z][A-Za-z-]+(?:\s+(?:and|&)\s+[A-Z][A-Za-z-]+)?(?:\s+et\s+al\.)?,?\s+\d{4}",
    r"\\cite[a-zA-Z]*\s*\{",
    r"\[[0-9]+(?:,\s*[0-9]+)*\]",
    r"\[[A-Za-z][A-Za-z0-9:_-]+\]",
]
_SECTION_HEADING = re.compile(r"^#{1,3}\s+(.+)$", re.MULTILINE)
_NON_BODY_HEADINGS = {
    "abstract",
    "keywords",
    "acknowledgements",
    "acknowledgment",
    "acknowledgments",
    "references",
    "bibliography",
}
_ROADMAP_SURFACE = [
    r"§\s*\d",
    r"\bsections?\s+\d",
    r"\bproceeds as\s+follows\b",
    r"\bis organis(?:e|z)ed as\s+follows\b",
    r"\bthe rest of (?:this|the) (?:paper|essay|chapter)\b",
]
_INTRO_TITLES = {"introduction", "intro"}


def _abstract_span(text: str) -> tuple[str, int] | None:
    match = _ABSTRACT_START.search(text)
    if not match:
        return None
    rest = text[match.end() :]
    end = _ABSTRACT_END.search(rest)
    body = rest[: end.start()] if end else rest
    return body, text[: match.start()].count("\n") + 1


def validate_abstract_citation_surface(
    profile: dict[str, str],
    text: str,
    manuscript_path: Path | None,
) -> list[Finding]:
    span = _abstract_span(text)
    if span is None:
        return []
    body, line = span
    locator = _locator(manuscript_path, line)
    has_cite = _has_any(body, _CITATION_SURFACE)
    policy = profile.get("abstract_citation_policy", "tbd")
    if policy == "required":
        if has_cite:
            return [
                Finding(
                    "INFO",
                    "DSTYLE_ABSTRACT_CITATION_PRESENT",
                    "Abstract citation surface detected under abstract_citation_policy=required.",
                    "abstract",
                    locator,
                )
            ]
        return [
            Finding(
                "MINOR",
                "DSTYLE_ABSTRACT_CITATION_MISSING",
                "Abstract has no citation surface; abstract_citation_policy=required.",
                "abstract",
                locator,
            )
        ]
    if policy == "forbidden":
        if has_cite:
            return [
                Finding(
                    "MINOR",
                    "DSTYLE_ABSTRACT_CITATION_FORBIDDEN",
                    "Abstract contains a citation surface; abstract_citation_policy=forbidden.",
                    "abstract",
                    locator,
                )
            ]
        return [
            Finding(
                "INFO",
                "DSTYLE_ABSTRACT_CITATION_ABSENT",
                "Abstract has no citation surface under abstract_citation_policy=forbidden.",
                "abstract",
                locator,
            )
        ]
    if has_cite:
        return [
            Finding(
                "INFO",
                "DSTYLE_ABSTRACT_CITATION_PRESENT",
                "Abstract citation surface detected; abstract_citation_policy=tbd. Do not treat presence as required. Evaluator must judge venue fit.",
                "abstract",
                locator,
            )
        ]
    return [
        Finding(
            "INFO",
            "DSTYLE_ABSTRACT_CITATION_ABSENT",
            "Abstract has no citation surface; abstract_citation_policy=tbd. Do not insert citations to close this finding.",
            "abstract",
            locator,
        )
    ]


def validate_intro_roadmap_surface(
    text: str, manuscript_path: Path | None
) -> list[Finding]:
    headings = list(_SECTION_HEADING.finditer(text))
    if len(headings) < 3:
        return []

    def _title(match: re.Match[str]) -> str:
        return re.sub(r"^(?:\d+[\.\)]\s+|§\s*)", "", match.group(1).strip().lower())

    def _body(match: re.Match[str]) -> str:
        nxt = next((row for row in headings if row.start() > match.start()), None)
        return text[match.end() : nxt.start() if nxt else None]

    candidates = [
        match
        for match in headings
        if _title(match) not in _NON_BODY_HEADINGS
    ]
    intro = next((match for match in candidates if _title(match) in _INTRO_TITLES), None)
    if intro is None:
        intro = next((match for match in candidates if len(_body(match).strip()) >= 40), None)
    if intro is None:
        return []
    body = _body(intro)
    if _has_any(body, _ROADMAP_SURFACE):
        return [
            Finding(
                "INFO",
                "DSTYLE_INTRO_ROADMAP_PRESENT",
                "Introduction roadmap surface detected; Evaluator must judge section fit.",
                "roadmap",
                _locator(manuscript_path, text[: intro.start()].count("\n") + 1),
            )
        ]
    return [
        Finding(
            "MINOR",
            "DSTYLE_INTRO_ROADMAP_MISSING",
            "No §1 roadmap surface detected in the opening body section.",
            "roadmap",
            _locator(manuscript_path, text[: intro.start()].count("\n") + 1),
        )
    ]


def validate_assistance_boundary_surface(
    profile: dict[str, str],
    text: str,
    project_root: Path,
) -> list[Finding]:
    policy = profile["assistance_disclosure_policy"]
    disclosure_in_text = _has_any(
        text,
        [
            r"\b(assistance|acknowledg(?:e|ement)|ai-assisted|artificial intelligence|language model|co-author harness|reviewer feedback|advisor feedback)\b",
        ],
    )
    candidate_logs = [
        project_root / "research_notes" / "assistance_log.md",
        project_root / "research_notes" / "disclosure.md",
        project_root / "reviews" / "assistance_log.md",
    ]
    existing_logs = [path for path in candidate_logs if path.exists()]

    if disclosure_in_text or existing_logs:
        locator = str(existing_logs[0]) if existing_logs else _locator(None, None)
        return [
            Finding(
                "INFO",
                "DSTYLE_ASSISTANCE_SURFACE_PRESENT",
                "Assistance disclosure/log surface detected; Evaluator must judge policy adequacy.",
                "assistance_disclosure_policy",
                locator,
            )
        ]

    severity = "BLOCKER" if policy in {"venue_required", "overseer_escalate"} else "MAJOR"
    return [
        Finding(
            severity,
            "DSTYLE_ASSISTANCE_SURFACE_MISSING",
            "No assistance disclosure or assistance-log surface detected for the active D-STYLE policy.",
            "assistance_disclosure_policy",
        )
    ]


def validate_substantive_surfaces(
    profile: dict[str, str],
    text: str | None,
    project_root: Path,
    manuscript_path: Path | None,
) -> list[Finding]:
    if text is None:
        return []
    findings: list[Finding] = []
    findings.extend(validate_argument_surface(text, manuscript_path))
    findings.extend(validate_visual_evidence_surface(profile, text, manuscript_path))
    findings.extend(validate_assistance_boundary_surface(profile, text, project_root))
    findings.extend(validate_abstract_citation_surface(profile, text, manuscript_path))
    findings.extend(validate_intro_roadmap_surface(text, manuscript_path))
    return findings


def surface_finding_codes(findings: Iterable[Finding]) -> list[str]:
    prefixes = (
        "DSTYLE_ARGUMENT_",
        "DSTYLE_VISUAL_",
        "DSTYLE_ASSISTANCE_",
        "DSTYLE_ABSTRACT_",
        "DSTYLE_INTRO_",
    )
    return [finding.code for finding in findings if finding.code.startswith(prefixes)]


def verdict(findings: Iterable[Finding]) -> str:
    severities = {finding.severity for finding in findings}
    if "BLOCKER" in severities:
        return "BLOCKER"
    if "MAJOR" in severities:
        return "MAJOR"
    if "MINOR" in severities:
        return "ADVISORY"
    return "CLEAN"


def build_report(
    project_root: Path,
    directives_path: Path,
    manuscript_path: Path | None = None,
) -> dict[str, object]:
    if directives_path.exists():
        text = directives_path.read_text(encoding="utf-8")
        raw_profile, profile_declared = parse_profile(text)
    else:
        raw_profile = {}
        profile_declared = False

    resolved = resolve_profile(raw_profile)
    findings = validate_profile(raw_profile, resolved, profile_declared)
    manuscript_text: str | None = None
    if manuscript_path is not None:
        manuscript_text = manuscript_path.read_text(encoding="utf-8")
        findings.extend(validate_substantive_surfaces(resolved, manuscript_text, project_root, manuscript_path))
    return {
        "schema_version": "1.1.0",
        "check": "d_style_profile",
        "project_root": str(project_root),
        "directives_path": str(directives_path),
        "manuscript_path": str(manuscript_path) if manuscript_path else None,
        "directives_exists": directives_path.exists(),
        "profile_declared": profile_declared,
        "raw_profile": raw_profile,
        "resolved_profile": resolved,
        "active_obligations": build_obligations(resolved),
        "surface_findings": surface_finding_codes(findings),
        "findings": [asdict(finding) for finding in findings],
        "verdict": verdict(findings),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True, help="Project root containing research_notes/")
    parser.add_argument("--directives-path", help="Optional explicit directives.md path")
    parser.add_argument("--manuscript", help="Optional manuscript path for substantive D-STYLE surface checks")
    parser.add_argument("--date", help="Date stamp override (YYYY-MM-DD)")
    parser.add_argument("--output", help="Optional output JSON path")
    parser.add_argument("--no-write", action="store_true", help="Print only; do not write a review artifact")
    parser.add_argument("--strict-exit", action="store_true", help="Return non-zero on BLOCKER")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    from destination_capability import DestinationRefused, assert_writable, guard_project_root
    try:
        if not args.no_write:
            guard_project_root(project_root)
            if args.output:
                assert_writable(Path(args.output).resolve(), purpose="D-STYLE profile output")
    except DestinationRefused as exc:
        print(f"[BLOCKER] {exc}", file=sys.stderr)
        return 4
    directives_path = (
        Path(args.directives_path).resolve()
        if args.directives_path
        else project_root / "research_notes" / "directives.md"
    )
    manuscript_path = Path(args.manuscript).resolve() if args.manuscript else None
    report = build_report(project_root, directives_path, manuscript_path)

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
        "surface_findings": report["surface_findings"],
        "report_path": str(output_path) if output_path else None,
    }
    print(json.dumps(envelope, indent=2))

    if args.strict_exit and report["verdict"] == "BLOCKER":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
