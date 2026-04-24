#!/usr/bin/env python3
"""Tier Marshal — Postflight runner.

Executes the eleven postflight predicates (Q-1 through Q-11) defined
in ``research_notes/tier_marshal_design_v1.md §10.2`` and emits a paired
``reviews/marshal_postflight_<round>_<date>.md`` + ``.json`` sidecar.

Verdict grammar (three values, no fourth): ``PASS`` / ``WARN`` /
``BLOCK``. Exit codes 0 / 1 / 2 respectively.

Usage::

    python scripts/marshal_postflight.py \
        --project-root /path/to/project \
        --tier T3 \
        --round 7 \
        [--date 2026-04-19] \
        [--plugin-root /path/to/plugin] \
        [--advisory-only]

Design constraints honoured: stdlib only; pure reader of every
Planner-exclusive artefact; the only files written are the two
Marshal sidecars under ``reviews/``.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from pathlib import Path

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
    is_registered,
    list_reviews,
    read_frontmatter,
    read_override_tags,
    read_plugin_version,
    resolve_plugin_root,
    scoped_artefacts_for,
)


# --- Helpers for log parsing -------------------------------------------------------


def _closeout_path(project_root: Path, round_id: int) -> Path | None:
    reviews = project_root / "reviews"
    if not reviews.is_dir():
        return None
    candidates = sorted(reviews.glob(f"tier_closeout_{round_id:02d}_*.md"))
    if candidates:
        return candidates[-1]
    # Fall back to un-padded round id (e.g., tier_closeout_7_*.md)
    candidates = sorted(reviews.glob(f"tier_closeout_{round_id}_*.md"))
    return candidates[-1] if candidates else None


def _state_probe_for(project_root: Path, date: str) -> Path | None:
    reviews = project_root / "reviews"
    if not reviews.is_dir():
        return None
    hits = sorted(reviews.glob(f"state_probe_{date}*.md")) or sorted(reviews.glob(f"state_probe_*{date}*.md"))
    return hits[-1] if hits else None


def _escalation_rows_for(project_root: Path, round_id: int) -> list[str]:
    path = project_root / "reviews" / "escalation_log.md"
    if not path.is_file():
        return []
    rows: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or stripped.startswith("|---"):
            continue
        # Row columns include round_id per AGENT_ORCHESTRATION §8.2a.
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if not cells:
            continue
        # Escalation-log schema per AGENT_ORCHESTRATION §8.2a places round_id in
        # the last column; decisions-log schema places round in the first column.
        # Scan every cell for a tolerant match.
        if any(cell == str(round_id) or cell == f"{round_id:02d}" or cell == f"{round_id:03d}" for cell in cells):
            rows.append(stripped)
    return rows


def _decisions_row_for(project_root: Path, round_id: int) -> str | None:
    path = project_root / "reviews" / "tier_decisions_log.md"
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or stripped.startswith("|---"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if any(cell == str(round_id) or cell == f"{round_id:02d}" or cell == f"{round_id:03d}" for cell in cells):
            return stripped
    return None


def _decisions_ascent_observed(project_root: Path) -> tuple[list[str], bool]:
    """Return (tiers, present) where `present` distinguishes a declared empty
    list from a missing header entirely."""
    path = project_root / "reviews" / "tier_decisions_log.md"
    if not path.is_file():
        return [], False
    fm, _ = read_frontmatter(path)
    val = fm.get("ascent_observed")
    if isinstance(val, list):
        return [str(v) for v in val], True
    text = path.read_text(encoding="utf-8")
    m = re.search(r"ascent_observed(?:_at_open)?:\s*\[([^\]]*)\]", text)
    if m:
        return [s.strip().strip("'\"") for s in m.group(1).split(",") if s.strip()], True
    return [], False


# --- Individual predicates ---------------------------------------------------------


def _q1_state_probe(project_root: Path, tier: str, date: str) -> CheckResult:
    if tier != "T0":
        return CheckResult("Q-1", "na", f"state_probe_<date>.md emitted (N/A at {tier})")
    path = _state_probe_for(project_root, date)
    if path:
        return CheckResult("Q-1", "pass", f"state_probe emitted ({path.name})")
    return CheckResult(
        "Q-1",
        "block",
        "state_probe_<date>.md emitted",
        remediation=(
            f"T0 rounds must emit reviews/state_probe_{date}.md. "
            "See TIER_PROTOCOL §2.1."
        ),
    )


def _q2_tier_closeout(project_root: Path, tier: str, round_id: int) -> tuple[CheckResult, Path | None]:
    if tier == "T0":
        return CheckResult("Q-2", "na", "tier_closeout emitted (N/A at T0)"), None
    path = _closeout_path(project_root, round_id)
    if path is None:
        return (
            CheckResult(
                "Q-2",
                "block",
                "tier_closeout_<round>_<date>.md emitted",
                remediation=(
                    f"T1+ rounds must emit reviews/tier_closeout_{round_id:02d}_<date>.md "
                    "(TIER_PROTOCOL §11.9 invariant 1). SAFEGUARD Check 5 "
                    "structural violation if absent."
                ),
            ),
            None,
        )
    return CheckResult("Q-2", "pass", f"tier_closeout emitted ({path.name})"), path


def _q3_closeout_schema_valid(closeout: Path | None, tier: str) -> CheckResult:
    if tier == "T0":
        return CheckResult("Q-3", "na", "tier_closeout schema valid (N/A at T0)")
    if closeout is None:
        return CheckResult("Q-3", "block", "tier_closeout schema valid", remediation="closeout missing (see Q-2).")
    fm, body = read_frontmatter(closeout)
    required_fields = ("round", "tier_entered", "tier_entered_via", "ascent_observed", "classification_tier", "advisories")
    missing = [f for f in required_fields if f not in fm]
    errors: list[str] = []
    if missing:
        errors.append(f"missing frontmatter: {missing}")
    # Validate enum values per tier_closeout_schema.md §3.
    te = str(fm.get("tier_entered", "")).strip()
    if te and te not in LEGAL_TIERS:
        errors.append(f"tier_entered {te!r} not in legal enum")
    tev = str(fm.get("tier_entered_via", "")).strip()
    if tev and not (tev in ("initial-dispatch", "user-up", "user-stay", "user-down") or re.match(r"auto-escalation-EG-\d+", tev)):
        errors.append(f"tier_entered_via {tev!r} not in legal enum")
    # Body sections required per §4.
    for required in ("## Delta", "## Narrative", "## Close-out choice"):
        if required not in body:
            errors.append(f"missing body section: {required}")
    if errors:
        return CheckResult(
            "Q-3",
            "block",
            "tier_closeout schema valid",
            remediation="; ".join(errors) + ". See references/tier_closeout_schema.md §3–§4.",
        )
    return CheckResult("Q-3", "pass", "tier_closeout schema valid")


def _q4_escalation_rows(project_root: Path, tier: str, round_id: int) -> CheckResult:
    if tier == "T0":
        return CheckResult("Q-4", "na", "escalation_log has row(s) for round (N/A at T0)")
    rows = _escalation_rows_for(project_root, round_id)
    if rows:
        return CheckResult("Q-4", "pass", f"escalation_log has row(s) for round ({len(rows)} row(s))")
    return CheckResult(
        "Q-4",
        "block",
        "escalation_log has row(s) for round",
        remediation=(
            f"reviews/escalation_log.md has no row for round {round_id}. "
            "Every tier transition (including initial-dispatch) emits a row; "
            "see AGENT_ORCHESTRATION §8.2a."
        ),
    )


def _q5_decisions_row(project_root: Path, tier: str, round_id: int) -> CheckResult:
    if tier == "T0":
        return CheckResult("Q-5", "na", "tier_decisions_log has row for Phase 5.5 (N/A at T0)")
    row = _decisions_row_for(project_root, round_id)
    if row:
        return CheckResult("Q-5", "pass", "tier_decisions_log has row for this round's Phase 5.5")
    # First-round exemption: if the log has just been created, Q-5 is WARN.
    log = project_root / "reviews" / "tier_decisions_log.md"
    if log.is_file() and log.read_text(encoding="utf-8").count("\n") < 10:
        return CheckResult(
            "Q-5",
            "warn",
            "tier_decisions_log has row for Phase 5.5 (first-round exemption)",
            remediation="Confirm the header-only log will receive its first row in this round.",
        )
    return CheckResult(
        "Q-5",
        "block",
        "tier_decisions_log has row for Phase 5.5",
        remediation=(
            f"No row for round {round_id} in tier_decisions_log.md. "
            "Phase 5.5 is non-skippable at T1+ (TIER_PROTOCOL §11.9 invariant 1)."
        ),
    )


def _q6_scoped_artefact(project_root: Path, tier: str, date: str) -> CheckResult:
    if tier == "T0":
        return CheckResult("Q-6", "na", "tier-scoped artefact present (N/A at T0)")
    matches = scoped_artefacts_for(tier, project_root, date)
    # Narrow matches to those dated this round when possible.
    if matches:
        return CheckResult(
            "Q-6",
            "pass",
            f"tier-scoped artefact present ({', '.join(p.name for p in matches[:3])}"
            + (f", +{len(matches)-3} more" if len(matches) > 3 else "")
            + ")",
        )
    tier_artefact = {
        "T1": "patch_report_<date>.md",
        "T2": "local_findings_<date>.md",
        "T3": "consolidated_findings_report_<date>.md",
        "T3R": "letter_findings_<date>.md",
        "T4": "consolidated_findings_report_<date>.md",
    }.get(tier, "tier-scoped findings file")
    return CheckResult(
        "Q-6",
        "block",
        "tier-scoped artefact present",
        remediation=f"No {tier_artefact} under reviews/. The tier's Evaluator output is missing.",
    )


def _q7_tier_entered_via_consistent(project_root: Path, tier: str, closeout: Path | None, round_id: int) -> CheckResult:
    if tier == "T0" or closeout is None:
        return CheckResult("Q-7", "na", "tier_entered_via consistent with escalation_log terminal (N/A)")
    fm, _ = read_frontmatter(closeout)
    tev = str(fm.get("tier_entered_via", "")).strip()
    rows = _escalation_rows_for(project_root, round_id)
    if not rows:
        return CheckResult(
            "Q-7",
            "block",
            "tier_entered_via consistent with escalation_log terminal",
            remediation="Cannot verify provenance: escalation_log has no rows for this round (see Q-4).",
        )
    terminal = rows[-1]
    # Heuristic consistency: initial-dispatch must be the first row of the round;
    # auto-escalation-EG-<n> requires the EG label in a row cell.
    if tev == "initial-dispatch":
        if len(rows) >= 1:
            return CheckResult("Q-7", "pass", "tier_entered_via=initial-dispatch consistent with escalation_log")
    m = re.match(r"auto-escalation-EG-(\d+)", tev)
    if m and f"EG-{m.group(1)}" in terminal:
        return CheckResult("Q-7", "pass", f"tier_entered_via={tev} matches escalation_log terminal row")
    if tev in ("user-up", "user-stay", "user-down"):
        return CheckResult("Q-7", "pass", f"tier_entered_via={tev} is user-elected; prior-round provenance")
    return CheckResult(
        "Q-7",
        "warn",
        "tier_entered_via consistent with escalation_log terminal",
        remediation=(
            f"tier_entered_via={tev!r} could not be matched to escalation_log terminal "
            f"row for round {round_id}. Manual verification recommended."
        ),
    )


def _q8_ascent_observed_consistent(project_root: Path, tier: str, closeout: Path | None) -> CheckResult:
    if tier == "T0" or closeout is None:
        return CheckResult("Q-8", "na", "ascent_observed consistent with decisions-log header (N/A)")
    fm, _ = read_frontmatter(closeout)
    closeout_ao = fm.get("ascent_observed")
    if not isinstance(closeout_ao, list):
        return CheckResult(
            "Q-8",
            "block",
            "ascent_observed consistent with decisions-log header",
            remediation="closeout ascent_observed is missing or not a list.",
        )
    log_ao, present = _decisions_ascent_observed(project_root)
    if not present:
        # No header field at all — legitimate first-round bootstrap.
        return CheckResult(
            "Q-8",
            "warn",
            "ascent_observed consistent with decisions-log header (first-round exemption)",
            remediation="tier_decisions_log.md header has no ascent_observed yet. First-round exempt.",
        )
    if [str(v) for v in closeout_ao] == log_ao:
        return CheckResult("Q-8", "pass", f"ascent_observed consistent ({closeout_ao})")
    return CheckResult(
        "Q-8",
        "block",
        "ascent_observed consistent with decisions-log header",
        remediation=(
            f"closeout ascent_observed={closeout_ao} ≠ tier_decisions_log.md header={log_ao}. "
            "TIER_PROTOCOL §11.9 invariant 3 (append-only decisions log) was not upheld."
        ),
    )


def _q9_orphan_artefacts(project_root: Path) -> CheckResult:
    files = list_reviews(project_root)
    orphans = [p for p in files if not is_registered(p.name)]
    if not orphans:
        return CheckResult("Q-9", "pass", "no orphan artefacts in reviews/")
    names = ", ".join(p.name for p in orphans[:5])
    more = f" (+{len(orphans)-5} more)" if len(orphans) > 5 else ""
    return CheckResult(
        "Q-9",
        "warn",
        f"orphan artefacts in reviews/ ({len(orphans)} file(s)): {names}{more}",
        remediation=(
            "Formalise as a new artefact type in TIER_PROTOCOL.md, rename to "
            "match an existing type, or delete after review. Always advisory; "
            "never a BLOCK."
        ),
    )


def _q10_g4_signoff(project_root: Path, tier: str) -> CheckResult:
    if tier != "T4":
        return CheckResult("Q-10", "na", f"G.4 sign-off emitted (N/A at {tier})")
    reviews = project_root / "reviews"
    if not reviews.is_dir():
        return CheckResult("Q-10", "block", "G.4 sign-off emitted", remediation="no reviews/ directory.")
    hits = list(reviews.glob("signoff*.md")) + list(reviews.glob("*G4*.md")) + list(reviews.glob("g4_*.md"))
    if hits:
        return CheckResult("Q-10", "pass", f"G.4 sign-off present ({hits[0].name})")
    return CheckResult(
        "Q-10",
        "block",
        "G.4 sign-off emitted",
        remediation=(
            "T4 submission rounds require a G.4 sign-off artefact. "
            "See run-tier-submission skill."
        ),
    )


def _q11_manuscript_diff(project_root: Path, tier: str, round_id: int) -> CheckResult:
    if tier == "T0":
        # T0 emits no edits. PASS iff revision_log has no entry for this round.
        rl = project_root / "manuscript" / "revision_log.md"
        if not rl.is_file():
            return CheckResult("Q-11", "pass", "manuscript diff absent at T0")
        text = rl.read_text(encoding="utf-8")
        if re.search(rf"Round\s*{round_id}\b", text):
            return CheckResult(
                "Q-11",
                "block",
                "manuscript diff absent at T0",
                remediation="T0 state-probe rounds must not edit the manuscript.",
            )
        return CheckResult("Q-11", "pass", "manuscript diff absent at T0")
    # T1+ paths: warn if revision_log looks empty for this round; do not hard-block
    # because some rounds legitimately conclude without edits.
    rl = project_root / "manuscript" / "revision_log.md"
    if not rl.is_file():
        return CheckResult(
            "Q-11",
            "warn",
            "manuscript diff non-empty if any edit was made",
            remediation="No revision_log.md present; cannot verify edit non-emptiness.",
        )
    text = rl.read_text(encoding="utf-8")
    if re.search(rf"Round\s*{round_id}\b", text):
        return CheckResult("Q-11", "pass", f"revision_log.md has Round {round_id} entry")
    return CheckResult(
        "Q-11",
        "warn",
        "manuscript diff non-empty if any edit was made",
        remediation=(
            f"No Round {round_id} entry in revision_log.md. Legitimate if the "
            "round terminated on a PASS verdict with no edits required."
        ),
    )


# --- Runner ------------------------------------------------------------------------


def run_postflight(
    project_root: Path,
    tier: str,
    round_id: int,
    date: str,
    plugin_version: str,
    advisory_only: bool,
) -> MarshalReport:
    tags_raw = read_override_tags(project_root) if project_root.is_dir() else []
    legal_tags, illegal_tags = classify_override_tags(tags_raw)

    report = MarshalReport(
        kind="postflight",
        round_id=round_id,
        tier=tier,
        date=date,
        plugin_version=plugin_version,
        overrides_read=tags_raw,
    )

    if not project_root.is_dir():
        report.checks.append(
            CheckResult(
                "Q-ENV",
                "block",
                "project root exists and is a directory",
                remediation=f"Path {project_root} is not a directory.",
            )
        )
        return report

    report.checks.append(_q1_state_probe(project_root, tier, date))
    q2, closeout = _q2_tier_closeout(project_root, tier, round_id)
    report.checks.append(q2)
    report.checks.append(_q3_closeout_schema_valid(closeout, tier))
    report.checks.append(_q4_escalation_rows(project_root, tier, round_id))
    report.checks.append(_q5_decisions_row(project_root, tier, round_id))
    report.checks.append(_q6_scoped_artefact(project_root, tier, date))
    report.checks.append(_q7_tier_entered_via_consistent(project_root, tier, closeout, round_id))
    report.checks.append(_q8_ascent_observed_consistent(project_root, tier, closeout))
    report.checks.append(_q9_orphan_artefacts(project_root))
    report.checks.append(_q10_g4_signoff(project_root, tier))
    report.checks.append(_q11_manuscript_diff(project_root, tier, round_id))

    # Populate tier_entered_via from closeout if present, for the artefact header.
    if closeout is not None:
        fm, _ = read_frontmatter(closeout)
        report.tier_entered_via = str(fm.get("tier_entered_via", "")).strip()

    # Apply overrides (postflight override mapping is intentionally narrower than
    # preflight: only EXPERIMENTAL-SKIP and USER-TIME-CRITICAL can downgrade
    # postflight BLOCKs, because the structural guarantees they encode are
    # the Marshal's entire reason for existing).
    applied: list[str] = []
    for t in legal_tags:
        mapping = {
            "USER-TIME-CRITICAL": {"Q-4", "Q-5", "Q-7", "Q-8", "Q-10"},
            "EXPERIMENTAL-SKIP": {
                "Q-1", "Q-2", "Q-3", "Q-4", "Q-5", "Q-6",
                "Q-7", "Q-8", "Q-10", "Q-11",
            },
        }
        targets = mapping.get(t, set())
        for c in report.checks:
            if c.severity == "block" and c.check_id in targets:
                c.severity = "warn"
                c.remediation = f"[{t}] override applied — downgraded to WARN. " + c.remediation
                if t not in applied:
                    applied.append(t)
    report.overrides_applied = applied

    if illegal_tags:
        report.checks.append(
            CheckResult(
                "Q-13",
                "block",
                "round_program override-tags use legal enum",
                remediation=(
                    f"Illegal override reason-code(s) {illegal_tags}. "
                    f"Legal enum: {list(LEGAL_OVERRIDE_REASONS)}."
                ),
            )
        )

    if advisory_only:
        for c in report.checks:
            if c.severity == "block":
                c.severity = "warn"
                c.remediation = "[ADVISORY-ONLY mode: would BLOCK at F.2] " + c.remediation

    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Tier Marshal postflight runner.")
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

    report = run_postflight(
        project_root=args.project_root,
        tier=args.tier,
        round_id=args.round_id,
        date=date,
        plugin_version=plugin_version,
        advisory_only=args.advisory_only,
    )

    basename = f"marshal_postflight_{args.round_id:02d}_{date}"
    try:
        md, js = emit_artefact(report, args.project_root, basename)
        print(f"[marshal] postflight → {md}")
        print(f"[marshal] sidecar    → {js}")
    except OSError as exc:
        print(f"[marshal] failed to emit artefact: {exc}", file=sys.stderr)
        return 2

    print(f"[marshal] STATUS: {report.verdict()}")
    return report.exit_code()


if __name__ == "__main__":
    sys.exit(main())
