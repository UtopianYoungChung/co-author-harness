"""Audit orchestrator — runs every audit_* module against a target file.

Single entry point so skills and agents invoke ONE command and consume ONE
findings.json artifact. Adding a new auditor means appending to AUDITORS
below; the schema and run-surface do not change.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Tuple

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
AUDIT_DIR = Path(__file__).resolve().parent
if str(AUDIT_DIR) not in sys.path:
    sys.path.insert(0, str(AUDIT_DIR))

from audit_style import (
    audit_absolutes,
    audit_emdash,
    audit_llm_tics,
    audit_passive_voice,
    audit_sentence_length,
    audit_voice,
)
from audit_craft import audit_craft
import check8_g_prefilter
import check8_h_prefilter
from d_style_profile_check import build_report as build_d_style_profile_report
from reader_accessibility_policy import PolicyError, resolve_policy, validate_candidate_artifact
from schema import Finding, FindingsReport

Auditor = Callable[[str, Path], List[Finding]]

AUDITORS: List[Tuple[str, Auditor]] = [
    ("absolutes", audit_absolutes),
    ("emdash", audit_emdash),
    ("llm_tics", audit_llm_tics),
    ("voice", audit_voice),
    ("sentence_length", audit_sentence_length),
    ("passive_voice", audit_passive_voice),
    ("craft", audit_craft),
]


def audit_target(path: Path) -> FindingsReport:
    text = path.read_text(encoding="utf-8")
    report = FindingsReport(target=path.as_posix())
    for _name, fn in AUDITORS:
        report.extend(fn(text, path))
    return report


def run_d_style_profile(
    project_root: Path,
    *,
    manuscript_path: Path | None = None,
    date: str | None = None,
    output: Path | None = None,
) -> tuple[dict[str, object], Path]:
    """Write the project-level D-STYLE profile-routing report."""

    project_root = project_root.resolve()
    directives_path = project_root / "research_notes" / "directives.md"
    report = build_d_style_profile_report(project_root, directives_path, manuscript_path)
    stamp = date or datetime.now().strftime("%Y-%m-%d")
    output_path = output.resolve() if output else project_root / "reviews" / f"d_style_profile_{stamp}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report, output_path


def run_accessibility_prefilters(
    project_root: Path,
    manuscript_path: Path,
    *,
    phase: str,
    cycle_id: str,
    output: Path | None = None,
    profile_path: Path | None = None,
) -> tuple[dict[str, object], Path]:
    """Emit a separate schema-defined candidate artifact; do not overload Finding."""

    resolved = resolve_policy(project_root, profile_path=profile_path) if profile_path is not None else resolve_policy(project_root)
    profile = resolved["resolved_profile"]
    text = manuscript_path.read_text(encoding="utf-8")
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    cues = profile["thresholds"]["cadence"]["turn_point_candidates"]
    a_candidates = []
    for index, paragraph in enumerate(paragraphs, start=1):
        words = len(re.findall(r"[\w']+", paragraph))
        hits = [cue for cue in cues if re.search(r"(?<!\w)" + re.escape(cue) + r"(?!\w)", paragraph, re.I)]
        if words > profile["thresholds"]["cadence"]["bands"][0]["max_words"]:
            a_candidates.append({"paragraph": index, "word_count": words, "candidate_cues": hits, "candidate_status": "overlay_functional_confirmation_required"})
    p_stage = check8_g_prefilter._parse_pstage(project_root)
    d_candidates = []
    is_tex = manuscript_path.suffix.lower() in {".tex", ".ltx"}
    heading_pattern = r"(?m)^\\(?:chapter|section|subsection|subsubsection)\*?\{([^}]+)\}" if is_tex else r"(?m)^#{1,6}\s+(.+)$"
    for heading in re.finditer(heading_pattern, text):
        tail = text[heading.end():].lstrip("\n")
        opening = tail.split("\n\n", 1)[0] if tail else ""
        orienting = bool(re.search(r"\b(having established|after|so far|in the preceding|the previous section|up to this point)\b", opening, re.I))
        contribution = bool(re.search(r"\b(this section (?:shows|argues|develops|examines)|what follows|I now|I turn to|the next move|we will|I will show|the contribution here)\b", opening, re.I))
        if not (orienting and contribution):
            d_candidates.append({"heading": heading.group(1).strip(), "missing": [name for name, present in (("orienting_clause", orienting), ("contribution_clause", contribution)) if not present], "candidate_status": "overlay_required"})
    seen_terms: set[str] = set()
    e_candidates = []
    cap = profile["thresholds"]["jargon"]["new_domain_terms_per_paragraph"][p_stage] + 1
    for index, paragraph in enumerate(paragraphs, start=1):
        terms = [term.strip() for pair in re.findall(r"\\emph\{([^}]+)\}|(?<!\*)\*([^*\n]+)\*(?!\*)", paragraph) for term in pair if term.strip()]
        new_terms = [term for term in terms if term.casefold() not in seen_terms]
        seen_terms.update(term.casefold() for term in terms)
        if len(new_terms) >= cap:
            e_candidates.append({"paragraph": index, "new_terms": new_terms, "candidate_cap": cap, "candidate_status": "overlay_required"})
    f_candidates = []
    for index, paragraph in enumerate(paragraphs, start=1):
        triadic = bool(re.search(r"\bFirst,[\s\S]{5,400}?\bSecond,[\s\S]{5,400}?\bThird,", paragraph, re.I))
        questions = paragraph.count("?")
        question_floor = profile["thresholds"]["worked_example"]["rhetorical_question_stack_min"]
        if triadic or questions >= question_floor:
            f_candidates.append({"paragraph": index, "markers": [name for name, present in (("triadic_enumerator", triadic), ("rhetorical_question_stack", questions >= question_floor)) if present], "candidate_status": "worked_example_judgment_required"})
    g_stats, total_words, headings, long_proxy = check8_g_prefilter.analyze(text, manuscript_path, p_stage)
    h_bundles = check8_h_prefilter.analyse(text, manuscript_path, profile, phase=phase, register_class=resolved["register_class"])
    try:
        manuscript_binding = manuscript_path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        manuscript_binding = manuscript_path.resolve().as_posix()
    artifact: dict[str, object] = {
        "schema_version": "reader_accessibility_candidates.v1",
        "phase": phase,
        "cycle_id": cycle_id,
        "manuscript_path": manuscript_binding,
        "manuscript_sha256": hashlib.sha256(manuscript_path.read_bytes()).hexdigest(),
        "profile_path": resolved["profile_path"],
        "profile_sha256": resolved["profile_sha256"],
        "source_bindings": resolved["source_bindings"],
        "register_class": resolved["register_class"],
        "candidate_only": True,
        "evaluator_judgment_required": True,
        "sub_checks": {
            "A": {"applicable": phase in {"Ph2", "Ph3", "Ph4"}, "deterministic_disposition": "candidate_probe", "candidates": a_candidates},
            "B": {"applicable": phase in {"Ph2", "Ph3", "Ph4"}, "deterministic_disposition": "judgment_only", "reason": "rhythm and C-8 functional guards require Evaluator judgment"},
            "C": {"applicable": phase in {"Ph2", "Ph3", "Ph4"}, "deterministic_disposition": "judgment_only", "reason": "first-use conceptual work cannot be established by token order alone"},
            "D": {"applicable": phase in {"Ph2", "Ph3", "Ph4"}, "deterministic_disposition": "candidate_probe", "candidates": d_candidates},
            "E": {"applicable": phase in {"Ph2", "Ph3", "Ph4"}, "deterministic_disposition": "candidate_probe", "candidates": e_candidates},
            "F": {"applicable": phase in {"Ph2", "Ph3", "Ph4"}, "deterministic_disposition": "candidate_probe", "candidates": f_candidates},
            "G": {"applicable": phase in {"Ph3", "Ph4"}, "deterministic_disposition": "candidate_probe", "proxy_label": "word-and-cue gap proxy candidate; not the construct-accumulation predicate", "total_words": total_words, "headings": headings, "long_manuscript_proxy": long_proxy, "candidates": [s.__dict__ for s in g_stats if s.g_candidate]},
            "H": {"applicable": phase in {"Ph2", "Ph3", "Ph4"}, "deterministic_disposition": "candidate_probe", "ph2_scope": "orienting_clause blocker-candidate plus advisory passage roles" if phase == "Ph2" else None, "positive_marker_audit_required": True, "bundles": [{"locator": b.locator, "passage_role": b.passage_role, "role_confidence": b.role_confidence, "role_reason": b.role_reason, "binding_status": b.binding_status, "word_count": b.word_count, "candidate_status": "overlay_positive_marker_audit_required", "negative_prefilter_fired": b.any_fired, "probes": {"nominalisation": b.nominalisation.__dict__, "prep_run": b.prep_run.__dict__, "hedging": b.hedging.__dict__}} for b in h_bundles]},
        },
    }
    validate_candidate_artifact(artifact)
    output_path = output.resolve() if output else project_root / "reviews" / f"reader_accessibility_candidates_{cycle_id}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return artifact, output_path


def main(argv: List[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path)
    parser.add_argument("--out", type=Path, default=Path("reviews/findings.json"))
    parser.add_argument("--stdout", action="store_true", help="Print JSON instead of writing")
    parser.add_argument(
        "--project-root",
        type=Path,
        help="Project root containing research_notes/; enables the D-STYLE profile pre-flight",
    )
    parser.add_argument("--date", help="Date stamp for D-STYLE profile output (YYYY-MM-DD)")
    parser.add_argument("--d-style-profile-out", type=Path, help="Optional D-STYLE profile JSON path")
    parser.add_argument("--skip-d-style-profile", action="store_true", help="Skip project-level D-STYLE routing")
    parser.add_argument("--phase", choices=["Ph1", "Ph2", "Ph3", "Ph4"], default="Ph2", help="Phase geometry for accessibility candidate dispatch")
    parser.add_argument("--cycle-id", default="iter0", help="Accessibility candidate cycle id")
    parser.add_argument("--accessibility-out", type=Path, help="Separate reader-accessibility candidate JSON path")
    parser.add_argument("--accessibility-profile", type=Path, help="Explicit package-contained accessibility profile (testing/migration only)")
    parser.add_argument("--skip-accessibility", action="store_true", help="Skip profile-driven Check 8 candidate dispatch")
    parser.add_argument("--fail-on", choices=["none", "any", "inviolable"], default="none", help="Exit 2 if findings match: none (default; exit 0, unchanged contract), any finding, or only inviolable severity. Lets run_all act as a blocking pre-send gate. C-7 caution: 'any' also gates on advisory craft/voice/length findings, which are C-7 candidates (idiolect vs. defect needs an author-baseline read this deterministic pass cannot do) — prefer 'inviolable' for an automated gate, or pair 'any' with a human C-7 review.")
    args = parser.parse_args(argv)

    if not args.target.is_file():
        print(f"[BLOCKER] target not found: {args.target}", file=sys.stderr)
        return 2
    if args.project_root and not args.project_root.is_dir():
        print(f"[BLOCKER] project root not found: {args.project_root}", file=sys.stderr)
        return 2

    report = audit_target(args.target)
    profile_report: dict[str, object] | None = None
    profile_output: Path | None = None
    if args.project_root and not args.skip_d_style_profile:
        profile_report, profile_output = run_d_style_profile(
            args.project_root,
            manuscript_path=args.target.resolve(),
            date=args.date,
            output=args.d_style_profile_out,
        )
    accessibility_report: dict[str, object] | None = None
    accessibility_output: Path | None = None
    if args.project_root and not args.skip_accessibility:
        try:
            accessibility_report, accessibility_output = run_accessibility_prefilters(
                args.project_root.resolve(), args.target.resolve(), phase=args.phase,
                cycle_id=args.cycle_id, output=args.accessibility_out,
                profile_path=args.accessibility_profile,
            )
        except (PolicyError, OSError, UnicodeError, json.JSONDecodeError) as exc:
            payload = {"status": "MISCONFIGURED", "code": "RA-POLICY", "message": str(exc)}
            print(json.dumps(payload, ensure_ascii=False))
            return 4
    if args.stdout:
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    else:
        report.write(args.out)
        counts = report.counts()
        print(
            f"OK wrote {args.out} — {counts['total']} findings "
            f"(default: {counts['by_severity'].get('default', 0)}, "
            f"inviolable: {counts['by_severity'].get('inviolable', 0)})"
        )
    if not args.stdout and profile_report and profile_output:
        print(f"OK wrote {profile_output} -- d_style_profile: {profile_report['verdict']}")
    if not args.stdout and accessibility_report and accessibility_output:
        print(f"OK wrote {accessibility_output} -- reader_accessibility candidates; Evaluator judgment required")
    counts = report.counts()
    if args.fail_on == "any" and counts["total"] > 0:
        print(f"[GATE] {counts['total']} findings; failing per --fail-on=any", file=sys.stderr)
        return 2
    if args.fail_on == "inviolable" and counts["by_severity"].get("inviolable", 0) > 0:
        print("[GATE] inviolable findings present; failing per --fail-on=inviolable", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
