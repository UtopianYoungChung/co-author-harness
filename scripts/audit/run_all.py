"""Audit orchestrator — runs every audit_* module against a target file.

Single entry point so skills and agents invoke ONE command and consume ONE
findings.json artifact. Adding a new auditor means appending to AUDITORS
below; the schema and run-surface do not change.

This command is diagnostic and never produces lifecycle product evidence.
Its optional semantic-receipt path is retained as a compatibility report only;
governed product qualification is owned by ``scripts/run_product_gate.py`` in
``governed-product`` mode with a committed evaluation verifier transaction.
"""

from __future__ import annotations

import argparse
import json
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
from d_style_profile_check import build_report as build_d_style_profile_report
from reader_accessibility_policy import (
    PolicyError,
    policy_error_payload,
    resolve_declared_policy,
)
from reader_accessibility_candidates import build_candidate_artifact
from schema import Finding, FindingsReport
from product_assurance import AssuranceError, build as build_product_assurance

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
    wiki_root: Path | None = None,
    workspace_root: Path | None = None,
    harness_root: Path | None = None,
) -> tuple[dict[str, object], Path]:
    """Emit a separate schema-defined candidate artifact; do not overload Finding."""

    # Root overrides are threaded through, not re-implemented: resolve_declared_policy
    # already owns the seam (and records path_roots_mode=override in the
    # artifact). Passing None keeps the declared-profile behaviour exactly.
    # All THREE roots are exposed here. The first cut passed wiki and workspace
    # only, so an alternate package install could not be pointed at from this
    # entry point even though resolve_policy and centroid_service both accept
    # it — an asymmetry that forced callers to reach for a different command to
    # do the same portable resolution. Recorded 2026-08-06.
    root_kwargs: dict[str, Path] = {}
    if wiki_root is not None:
        root_kwargs["wiki_root"] = wiki_root
    if workspace_root is not None:
        root_kwargs["workspace_root"] = workspace_root
    if harness_root is not None:
        root_kwargs["harness_root"] = harness_root
    resolved = (resolve_declared_policy(project_root, profile_path=profile_path, **root_kwargs)
                if profile_path is not None
                else resolve_declared_policy(project_root, **root_kwargs))
    artifact = build_candidate_artifact(project_root, manuscript_path, phase, cycle_id, resolved)
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
    parser.add_argument(
        "--wiki-root",
        type=Path,
        help="Override the domain-native corpus wiki root (testing/migration only). "
             "corpus_binding.path_roots records the roots the pinned corpus was "
             "declared under and is not portable across hosts; supply roots this "
             "host can use. Recorded as path_roots_mode=override.",
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        help="Override the domain-native corpus workspace root (testing/migration "
             "only); see --wiki-root. Recorded as path_roots_mode=override.",
    )
    parser.add_argument(
        "--harness-root",
        type=Path,
        help="Override the running package root used for contained package "
             "lookups (testing/migration only); see --wiki-root. Defaults to the "
             "installed package. Recorded as path_roots_mode=override.",
    )
    parser.add_argument("--skip-accessibility", action="store_true", help="Skip profile-driven Check 8 candidate dispatch")
    parser.add_argument("--semantic-receipt", type=Path, help="compatibility-only semantic receipt; emits diagnostic product-assurance findings and never lifecycle evidence")
    parser.add_argument("--product-assurance-out", type=Path, help="Exact diagnostic compatibility report path (required with --stdout when --semantic-receipt is used)")
    parser.add_argument("--fail-on", choices=["none", "any", "inviolable"], default="none", help="Exit 2 within this diagnostic mechanics command if findings match: none (default; exit 0, unchanged contract), any finding, or only inviolable severity. This result is never governed product or lifecycle qualification. C-7 caution: 'any' also checks advisory craft/voice/length candidates (idiolect vs. defect needs an author-baseline read this deterministic pass cannot do) — prefer 'inviolable' for automated diagnostics, or pair 'any' with a human C-7 review.")
    args = parser.parse_args(argv)

    if args.semantic_receipt:
        print(
            "[DIAGNOSTIC] run_all semantic compatibility output is not governed "
            "product or lifecycle evidence; use run_product_gate.py --mode "
            "governed-product with a committed evaluation verifier transaction.",
            file=sys.stderr,
        )

    if not args.target.is_file():
        print(f"[BLOCKER] target not found: {args.target}", file=sys.stderr)
        return 2
    if args.project_root and not args.project_root.is_dir():
        print(f"[BLOCKER] project root not found: {args.project_root}", file=sys.stderr)
        return 2

    from destination_capability import (
        DEST_PROTECTED,
        DestinationRefused,
        assert_writable,
        classify,
        guard_project_root,
    )
    try:
        project_kind = classify(args.project_root) if args.project_root else None
        destinations = ([] if args.stdout else [args.out])
        if args.project_root and not args.skip_d_style_profile:
            destinations.append(
                args.d_style_profile_out
                or args.project_root / "reviews" /
                f"d_style_profile_{args.date or datetime.now().strftime('%Y-%m-%d')}.json")
        if args.project_root and not args.skip_accessibility:
            destinations.append(
                args.accessibility_out
                or args.project_root / "reviews" /
                f"reader_accessibility_candidates_{args.cycle_id}.json")
        product_output = None
        if args.semantic_receipt:
            product_output = args.product_assurance_out or (
                args.project_root / "reviews" / f"product_assurance_{args.cycle_id}.json"
                if args.project_root else args.out.with_name("product_assurance.json")
            )
            destinations.append(product_output)
        if args.project_root and project_kind != "protected":
            guard_project_root(args.project_root)
        for dest in destinations:
            if dest is not None:
                output_kind = assert_writable(Path(dest).resolve(), purpose="audit output")
                if project_kind == "protected" and output_kind != "shipment":
                    raise DestinationRefused(
                        DEST_PROTECTED,
                        "an audit of a protected project may write only to its "
                        "private reviews/.harness/shipments/<shipment-id>/ lane; "
                        f"got {Path(dest).resolve()!s}")
    except DestinationRefused as exc:
        print(f"[BLOCKER] {exc}", file=sys.stderr)
        return 4

    report = audit_target(args.target)
    product_report: dict[str, object] | None = None
    product_output: Path | None = None
    if args.semantic_receipt:
        product_output = args.product_assurance_out or (
            args.project_root / "reviews" / f"product_assurance_{args.cycle_id}.json"
            if args.project_root else args.out.with_name("product_assurance.json")
        )
        try:
            product_report = build_product_assurance(args.target, args.semantic_receipt)
        except (AssuranceError, OSError, UnicodeError) as exc:
            code = exc.code if isinstance(exc, AssuranceError) else "PRODUCT-ASSURANCE-IO"
            message = exc.message if isinstance(exc, AssuranceError) else str(exc)
            product_report = {
                "schema_version": "1.0.0", "report_type": "product_assurance",
                "status": "blocked", "findings": [{
                    "code": code, "dimension": "evidence", "severity": "hard",
                    "locator": "$", "evidence": message, "tentative": False,
                }],
            }
        product_output.parent.mkdir(parents=True, exist_ok=True)
        product_output.write_text(
            json.dumps(product_report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        for row in product_report.get("findings", []):
            if not isinstance(row, dict):
                continue
            dimension = row.get("dimension")
            category = (
                "citation" if dimension in {"citation", "quotation", "evidence"}
                else "grounding" if dimension == "grounding" else "register"
            )
            report.add(Finding(
                check_id=str(row.get("code", "PRODUCT-ASSURANCE")),
                category=category,
                severity="inviolable" if row.get("severity") == "hard" else "default",
                locator=str(row.get("locator", args.target.as_posix())),
                evidence=str(row.get("evidence", "product-assurance finding")),
                rule_ref="product-assurance-kernel",
                tentative=bool(row.get("tentative", False)),
            ))
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
                wiki_root=args.wiki_root, workspace_root=args.workspace_root,
                harness_root=args.harness_root,
            )
        except (PolicyError, OSError, UnicodeError, json.JSONDecodeError) as exc:
            payload = (
                policy_error_payload(exc)
                if isinstance(exc, PolicyError)
                else {"status": "MISCONFIGURED", "code": "RA-POLICY", "message": str(exc)}
            )
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
    if not args.stdout and product_report and product_output:
        print(
            f"OK wrote {product_output} -- diagnostic_compatibility_product_assurance: "
            f"{product_report.get('status')} (lifecycle_eligible=false)"
        )
    counts = report.counts()
    if args.fail_on == "any" and counts["total"] > 0:
        print(f"[DIAGNOSTIC-FAIL] {counts['total']} findings; failing per --fail-on=any", file=sys.stderr)
        return 2
    if args.fail_on == "inviolable" and counts["by_severity"].get("inviolable", 0) > 0:
        print("[DIAGNOSTIC-FAIL] inviolable findings present; failing per --fail-on=inviolable", file=sys.stderr)
        return 2
    if product_report is not None and product_report.get("status") != "passed":
        print("[DIAGNOSTIC-FAIL] compatibility product assurance did not pass; lifecycle_eligible=false", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
