#!/usr/bin/env python3
"""Tier Marshal — Preflight runner.

Executes the thirteen preflight predicates (P-1 through P-13) defined
in ``research_notes/tier_marshal_design_v1.md §10.1`` and emits a paired
``reviews/marshal_preflight_<round>_<date>.md`` + ``.json`` sidecar.

Verdict grammar (three values, no fourth): ``PASS`` / ``WARN`` /
``BLOCK``. Exit codes 0 / 1 / 2 respectively.

Usage::

    python scripts/marshal_preflight.py \
        --project-root /path/to/project \
        --tier T3 \
        --round 7 \
        [--date 2026-04-19] \
        [--plugin-root /path/to/plugin] \
        [--advisory-only]

``--advisory-only`` flips every BLOCK to WARN at emission time, which
is the Phase F.1 rollout mode. Phase F.2 removes the flag.

Design constraints honoured:

- Stdlib only. No third-party imports.
- Never writes outside ``reviews/``. Never touches the manuscript.
- Per ``TIER_MARSHAL_CONTRACT.md §8.3.4`` the Marshal is a pure reader
  of every Planner-exclusive artefact.
- ``--project-root`` that does not exist surfaces as a single BLOCK
  row and an empty artefact is still emitted so the Planner has
  something to read.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import re
import sys
from pathlib import Path

# Make sibling module importable regardless of invocation cwd.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from _marshal_common import (  # noqa: E402
    CheckResult,
    LEGAL_OVERRIDE_REASONS,
    LEGAL_TIERS,
    MarshalReport,
    classify_override_tags,
    emit_artefact,
    find_rule_digest,
    read_frontmatter,
    read_override_tags,
    read_plugin_version,
    resolve_plugin_root,
)


# --- Individual predicates ---------------------------------------------------------


def _p1_classification_exists(project_root: Path) -> CheckResult:
    path = project_root / "reviews" / "classification.md"
    if path.is_file():
        return CheckResult(
            "P-1",
            "pass",
            "classification.md exists",
        )
    return CheckResult(
        "P-1",
        "block",
        "classification.md exists",
        remediation=(
            "Run /classify-manuscript and save the result to "
            "reviews/classification.md."
        ),
    )


def _p2_classification_tier_field(project_root: Path) -> CheckResult:
    path = project_root / "reviews" / "classification.md"
    if not path.is_file():
        return CheckResult("P-2", "block", "classification.md has tier: field", remediation="classification.md missing (see P-1).")
    fm, _ = read_frontmatter(path)
    if "tier" in fm and str(fm["tier"]).strip() in LEGAL_TIERS:
        return CheckResult("P-2", "pass", f"classification.md has tier: field (tier: {fm['tier']})")
    if "review_depth" in fm:
        return CheckResult(
            "P-2",
            "block",
            "classification.md has tier: field (not retired review_depth:)",
            remediation=(
                "classification.md carries retired review_depth: "
                f"{fm.get('review_depth')!r}. Re-run /classify-manuscript "
                "to emit the tier: field required by TIER_PROTOCOL §1."
            ),
        )
    return CheckResult(
        "P-2",
        "block",
        "classification.md has tier: field",
        remediation="Add tier: <T0|T1|T2|T3|T3R|T4> to classification.md frontmatter.",
    )


def _p3_tier_matches_request(project_root: Path, requested: str) -> CheckResult:
    path = project_root / "reviews" / "classification.md"
    if not path.is_file():
        return CheckResult("P-3", "block", "classification.md tier: matches requested tier", remediation="classification.md missing (see P-1).")
    fm, _ = read_frontmatter(path)
    declared = str(fm.get("tier", "")).strip()
    if declared == requested:
        return CheckResult("P-3", "pass", f"classification.md tier: matches requested ({requested})")
    if declared == "":
        return CheckResult("P-3", "block", "classification.md tier: matches requested tier", remediation="tier: field is empty or missing (see P-2).")
    # A requested tier that is ≠ classification_tier is legal (e.g., Stay at T2
    # when classification_tier is T3). Surface as advisory, never block.
    return CheckResult(
        "P-3",
        "warn",
        f"classification.md tier: {declared} ≠ requested {requested} (Stay/Down/Up election expected)",
        remediation=(
            "If this is an intentional Down or Stay election, confirm the "
            "corresponding row was recorded in tier_decisions_log.md."
        ),
    )


def _p4_rule_digest_present(project_root: Path, tier: str, plugin_version: str, advisory: bool) -> CheckResult:
    if tier not in ("T1", "T2"):
        return CheckResult("P-4", "na", f"rule digest present (N/A at {tier})")
    digest = find_rule_digest(project_root, plugin_version)
    if digest is not None:
        return CheckResult("P-4", "pass", f"rule digest present ({digest.name})")
    return CheckResult(
        "P-4",
        "warn" if advisory else "block",
        "rule digest present",
        remediation=(
            f"Build the digest: python scripts/build_rule_digest.py "
            f"--project-root {project_root} (target: reviews/_rule_digest_{plugin_version}.json)."
        ),
    )


def _p5_digest_plugin_version(project_root: Path, tier: str, plugin_version: str, advisory: bool) -> CheckResult:
    if tier not in ("T1", "T2"):
        return CheckResult("P-5", "na", f"digest plugin-version matches plugin.json (N/A at {tier})")
    digest_path = find_rule_digest(project_root, plugin_version)
    if digest_path is None:
        return CheckResult("P-5", "warn" if advisory else "block", "digest plugin-version matches plugin.json", remediation="digest missing (see P-4).")
    import json as _json
    try:
        data = _json.loads(digest_path.read_text(encoding="utf-8"))
    except _json.JSONDecodeError as exc:
        return CheckResult("P-5", "warn" if advisory else "block", "digest plugin-version matches plugin.json", remediation=f"digest JSON parse error: {exc}")
    dv = data.get("plugin_version")
    if dv == plugin_version:
        return CheckResult("P-5", "pass", f"digest plugin-version matches plugin.json ({plugin_version})")
    return CheckResult(
        "P-5",
        "warn" if advisory else "block",
        "digest plugin-version matches plugin.json",
        remediation=f"digest.plugin_version={dv!r} ≠ plugin.json.version={plugin_version!r}; rebuild the digest.",
    )


def _p6_revision_log_readable(project_root: Path, tier: str) -> CheckResult:
    if tier == "T0":
        return CheckResult("P-6", "na", "manuscript/revision_log.md readable (N/A at T0)")
    path = project_root / "manuscript" / "revision_log.md"
    if path.is_file():
        try:
            _ = path.read_text(encoding="utf-8")
            return CheckResult("P-6", "pass", "manuscript/revision_log.md readable")
        except OSError as exc:
            return CheckResult("P-6", "block", "manuscript/revision_log.md readable", remediation=f"IO error reading revision_log.md: {exc}")
    return CheckResult(
        "P-6",
        "warn",
        "manuscript/revision_log.md readable",
        remediation=(
            "No revision_log.md yet; Generator will create on first append. "
            "Legitimate in first-run projects."
        ),
    )


def _p7_ratchet_readable(project_root: Path, tier: str) -> CheckResult:
    if tier == "T0":
        return CheckResult("P-7", "na", "tier-decisions log readable (N/A at T0)")
    path = project_root / "reviews" / "tier_decisions_log.md"
    if path.is_file():
        return CheckResult("P-7", "pass", "tier_decisions_log.md readable")
    # Legitimate absence: no prior Phase-5.5 elections. Surface as WARN so the
    # Reflector can distinguish true first-run from systemic Phase-5.5 skipping.
    return CheckResult(
        "P-7",
        "warn",
        "tier-decisions log readable (or legitimately absent)",
        remediation=(
            "No tier_decisions_log.md yet. First Phase 5.5 election will "
            "create the header (bootstrap exemption; see §8.3.11)."
        ),
    )


def _read_ascent_observed(project_root: Path) -> list[str]:
    """Parse ascent_observed from the session header of tier_decisions_log.md."""
    path = project_root / "reviews" / "tier_decisions_log.md"
    if not path.is_file():
        return []
    fm, _ = read_frontmatter(path)
    val = fm.get("ascent_observed")
    if isinstance(val, list):
        return [str(v) for v in val]
    # Fall back to scanning for an ``ascent_observed:`` line anywhere.
    text = path.read_text(encoding="utf-8")
    m = re.search(r"ascent_observed:\s*\[([^\]]*)\]", text)
    if m:
        raw = m.group(1)
        return [s.strip().strip("'\"") for s in raw.split(",") if s.strip()]
    return []


def _p8_down_legality(project_root: Path, tier: str, classification_tier: str) -> CheckResult:
    if tier == "T0":
        return CheckResult("P-8", "na", "requested tier legal under ratchet (N/A at T0)")
    ascent = _read_ascent_observed(project_root)
    # Legal if tier is the classification tier (initial-dispatch), is present
    # in the ratchet (already observed this session), or is an Up election.
    if not ascent:
        # No ratchet yet — initial dispatch. Legal iff tier == classification_tier.
        if tier == classification_tier:
            return CheckResult("P-8", "pass", "requested tier legal under ratchet (initial dispatch)")
        # Treat as WARN rather than BLOCK — first-round latitude.
        return CheckResult(
            "P-8",
            "warn",
            "requested tier legal under ratchet (first-round latitude)",
            remediation="No ascent_observed ratchet yet; confirm the requested tier is intentional.",
        )
    if tier in ascent:
        return CheckResult("P-8", "pass", f"requested tier legal under ratchet ({tier} ∈ {ascent})")
    # Up election beyond ratchet: always legal (Up is unrestricted).
    # Down election below ratchet floor: illegal.
    try:
        order = {"T0": 0, "T1": 1, "T2": 2, "T3": 3, "T3R": 3, "T4": 4}
        floor = min(order[t] for t in ascent if t in order)
        if order[tier] < floor:
            return CheckResult(
                "P-8",
                "block",
                "requested tier legal under ratchet (Down-legality)",
                remediation=(
                    f"Requested {tier} is below ratchet floor (observed: {ascent}). "
                    "Down is legal only to a tier already in ascent_observed "
                    "(see TIER_PROTOCOL §11.4)."
                ),
            )
    except (KeyError, ValueError):
        pass
    return CheckResult("P-8", "pass", f"requested tier legal under ratchet ({tier}; Up-legal)")


def _p9_t2_scope(project_root: Path, tier: str) -> CheckResult:
    if tier != "T2":
        return CheckResult("P-9", "na", f"T2 local-scope envelope computable (N/A at {tier})")
    path = project_root / "reviews" / "round_program.md"
    if not path.is_file():
        return CheckResult(
            "P-9",
            "block",
            "T2 local-scope envelope computable",
            remediation=(
                "T2 runs require round_program.md declaring the local scope "
                "(paragraphs / section IDs). Emit the program before dispatch."
            ),
        )
    text = path.read_text(encoding="utf-8")
    # Look for a scope: or paragraphs: field as a minimum signal.
    if re.search(r"(^|\n)\s*(scope|paragraphs|sections)\s*:", text):
        return CheckResult("P-9", "pass", "T2 local-scope envelope declared in round_program.md")
    return CheckResult(
        "P-9",
        "block",
        "T2 local-scope envelope computable",
        remediation="round_program.md present but lacks a scope:/paragraphs:/sections: declaration.",
    )


def _p10_response_letter_present(project_root: Path, tier: str) -> CheckResult:
    if tier != "T3R":
        return CheckResult("P-10", "na", f"response_letter.md present (N/A at {tier})")
    # Accept any of the common filenames used for the response letter.
    candidates = [
        project_root / "manuscript" / "response_letter.md",
        project_root / "reviews" / "response_letter.md",
        project_root / "response_letter.md",
    ]
    for p in candidates:
        if p.is_file():
            return CheckResult("P-10", "pass", f"response_letter.md present ({p.relative_to(project_root)})")
    return CheckResult(
        "P-10",
        "block",
        "response_letter.md present",
        remediation="T3R requires an authored response_letter.md; place it under manuscript/ or reviews/.",
    )


def _p11_class1_verifier_reachable(project_root: Path, tier: str) -> CheckResult:
    if tier != "T4":
        return CheckResult("P-11", "na", f"Class-1 verifier reachable (N/A at {tier})")
    # Heuristic: the package release gate is the documented verifier hook.
    hook = project_root.parent / "scripts" / "release-gate.sh"
    plugin_hook = resolve_plugin_root() / "scripts" / "release-gate.sh"
    if hook.is_file() or plugin_hook.is_file():
        return CheckResult("P-11", "pass", "Class-1 verifier reachable (release-gate.sh on plugin root)")
    return CheckResult(
        "P-11",
        "warn",
        "Class-1 verifier reachable",
        remediation=(
            "Could not locate scripts/release-gate.sh. The Marshal treats "
            "this as advisory; the Planner should confirm Class-1 verifier "
            "configuration before T4 submission."
        ),
    )


def _p12_no_prior_block(project_root: Path) -> CheckResult:
    reviews = project_root / "reviews"
    if not reviews.is_dir():
        return CheckResult("P-12", "pass", "no unresolved prior-round BLOCK postflight (no reviews/ yet)")
    prior = sorted(reviews.glob("marshal_postflight_*.md"))
    if not prior:
        return CheckResult("P-12", "pass", "no unresolved prior-round BLOCK postflight (no prior postflights)")
    latest = prior[-1]
    text = latest.read_text(encoding="utf-8")
    # Status line lives on the first non-frontmatter line starting with STATUS:
    m = re.search(r"^STATUS:\s*(PASS|WARN|BLOCK)\s*$", text, flags=re.MULTILINE)
    status = m.group(1) if m else "UNKNOWN"
    if status != "BLOCK":
        return CheckResult("P-12", "pass", f"no unresolved prior-round BLOCK postflight (latest: {latest.name} → {status})")
    # A prior BLOCK is unresolved unless a matching override for this round is recorded.
    return CheckResult(
        "P-12",
        "block",
        "no unresolved prior-round BLOCK postflight",
        remediation=(
            f"Prior postflight {latest.name} closed with STATUS: BLOCK. "
            "Resolve the blocking predicate(s) or sign a legal "
            "[MARSHAL-OVERRIDE-<reason>] tag into round_program.md."
        ),
    )


def _p13_override_enum(tags: list[str], illegal: list[str]) -> CheckResult:
    if not tags:
        return CheckResult("P-13", "pass", "round_program override-tags use legal enum (no tags present)")
    if not illegal:
        return CheckResult("P-13", "pass", f"round_program override-tags use legal enum ({tags})")
    return CheckResult(
        "P-13",
        "block",
        "round_program override-tags use legal enum",
        remediation=(
            f"Illegal override reason-code(s) {illegal} in round_program.md. "
            f"Legal enum: {list(LEGAL_OVERRIDE_REASONS)}. Unknown codes "
            "are themselves a BLOCK condition (see §8.3.7)."
        ),
    )


# --- Runner ------------------------------------------------------------------------


def _classification_tier(project_root: Path) -> str:
    path = project_root / "reviews" / "classification.md"
    if not path.is_file():
        return ""
    fm, _ = read_frontmatter(path)
    return str(fm.get("tier", "")).strip()


def run_preflight(
    project_root: Path,
    tier: str,
    round_id: int,
    date: str,
    plugin_version: str,
    advisory_only: bool,
) -> MarshalReport:
    tags_raw = read_override_tags(project_root) if project_root.is_dir() else []
    legal_tags, illegal_tags = classify_override_tags(tags_raw)
    classification_tier = _classification_tier(project_root)

    first_run = not any((project_root / "reviews").glob("marshal_*.md")) if (project_root / "reviews").is_dir() else True

    report = MarshalReport(
        kind="preflight",
        round_id=round_id,
        tier=tier,
        date=date,
        plugin_version=plugin_version,
        first_run=first_run,
        overrides_read=tags_raw,
    )

    # Fast path: project root does not exist.
    if not project_root.is_dir():
        report.checks.append(
            CheckResult(
                "P-ENV",
                "block",
                "project root exists and is a directory",
                remediation=f"Path {project_root} is not a directory.",
            )
        )
        return report

    # Reduced set for T0 and first-run projects.
    reduced = (tier == "T0") or first_run

    # Full set otherwise.
    report.checks.append(_p1_classification_exists(project_root))
    report.checks.append(_p2_classification_tier_field(project_root))
    report.checks.append(_p3_tier_matches_request(project_root, tier))
    report.checks.append(_p4_rule_digest_present(project_root, tier, plugin_version, advisory_only))
    report.checks.append(_p5_digest_plugin_version(project_root, tier, plugin_version, advisory_only))
    if not reduced:
        report.checks.append(_p6_revision_log_readable(project_root, tier))
        report.checks.append(_p7_ratchet_readable(project_root, tier))
        report.checks.append(_p8_down_legality(project_root, tier, classification_tier))
        report.checks.append(_p9_t2_scope(project_root, tier))
        report.checks.append(_p10_response_letter_present(project_root, tier))
        report.checks.append(_p11_class1_verifier_reachable(project_root, tier))
    else:
        # Reduced set still runs P-12 and P-13 per §8.3.5.
        for cid, msg in (
            ("P-6", "manuscript/revision_log.md readable"),
            ("P-7", "tier-decisions log readable"),
            ("P-8", "requested tier legal under ratchet"),
            ("P-9", "T2 local-scope envelope computable"),
            ("P-10", "response_letter.md present"),
            ("P-11", "Class-1 verifier reachable"),
        ):
            report.checks.append(CheckResult(cid, "na", f"{msg} (N/A under reduced set)"))
    report.checks.append(_p12_no_prior_block(project_root))
    report.checks.append(_p13_override_enum(tags_raw, illegal_tags))

    # Apply overrides: a signed legal override downgrades the matching BLOCK to WARN.
    applied: list[str] = []
    for t in legal_tags:
        # Match override reason-codes to failed checks per §8.3.7.
        mapping = {
            "DIGEST-UNAVAILABLE": {"P-4", "P-5"},
            "CLASSIFICATION-PENDING": {"P-2", "P-3"},
            "USER-TIME-CRITICAL": {"P-4", "P-5", "P-6", "P-7", "P-8", "P-9", "P-10", "P-11"},
            "EXPERIMENTAL-SKIP": {"P-1", "P-2", "P-3", "P-4", "P-5", "P-6", "P-7", "P-8", "P-9", "P-10", "P-11", "P-12"},
        }
        targets = mapping.get(t, set())
        for c in report.checks:
            if c.severity == "block" and c.check_id in targets:
                c.severity = "warn"
                c.remediation = f"[{t}] override applied — downgraded to WARN. " + c.remediation
                if t not in applied:
                    applied.append(t)
    report.overrides_applied = applied

    # Advisory-only rollout: flip any residual BLOCK to WARN.
    if advisory_only:
        for c in report.checks:
            if c.severity == "block":
                c.severity = "warn"
                c.remediation = "[ADVISORY-ONLY mode: would BLOCK at F.2] " + c.remediation

    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Tier Marshal preflight runner.")
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--tier", required=True, choices=list(LEGAL_TIERS))
    parser.add_argument("--round", required=True, type=int, dest="round_id")
    parser.add_argument("--date", default="")
    parser.add_argument("--plugin-root", type=Path, default=None)
    parser.add_argument("--advisory-only", action="store_true", help="Phase F.1 rollout: flip BLOCK→WARN.")
    args = parser.parse_args(argv)

    date = args.date or _dt.date.today().isoformat()
    plugin_root = args.plugin_root or resolve_plugin_root()
    plugin_version = read_plugin_version(plugin_root) or "unknown"

    report = run_preflight(
        project_root=args.project_root,
        tier=args.tier,
        round_id=args.round_id,
        date=date,
        plugin_version=plugin_version,
        advisory_only=args.advisory_only,
    )

    basename = f"marshal_preflight_{args.round_id:02d}_{date}"
    try:
        md, js = emit_artefact(report, args.project_root, basename)
        print(f"[marshal] preflight → {md}")
        print(f"[marshal] sidecar   → {js}")
    except OSError as exc:
        print(f"[marshal] failed to emit artefact: {exc}", file=sys.stderr)
        return 2

    print(f"[marshal] STATUS: {report.verdict()}")
    return report.exit_code()


if __name__ == "__main__":
    sys.exit(main())
