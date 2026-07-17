#!/usr/bin/env python3
"""full_run_contract_check - mechanical enforcement of references/FULL_RUN_CONTRACT.md.

WHY THIS EXISTS
---------------
A "Harness full run" request produced a complete essay with no project root, no
assignment contract, no phase state, no milestone acceptance, no F7/F8/F9 and no
G.4 -- and reported "Ladder complete ... PASS" (audit 2026-07-17, lines 1, 112,
342). Every agent file already forbade this. The package enforced none of it:

  * the assignment gates are the real fail-closed mechanism, but each is
    --project-root parameterised, so with NO project nothing can fire;
  * `run_scope` did not exist, so a parent's intent could not bind a child --
    the coordinator told the Evaluator "no artifacts, response only" (:112);
  * references/AGENT_ORCHESTRATION.md states outright that role permissions are
    "not structurally enforced by the filesystem";
  * nothing stood between an agent and the sentence "ladder complete".

This script is the floor. It answers four questions deterministically, and the
answers do not depend on any agent's self-report:

  authorize  may academic prose be written here, at all?   (FRC-NO-PROJECT ...)
  scope      is this dispatch legal under its parent?      (FRC-SCOPE-*)
  authorship is manuscript movement Generator-attributable? (FRC-AUTHORSHIP)
  terminal   is a terminal claim earned?                    (FRC-TERMINAL-UNPROVEN)

CONTRACT
--------
Exit 0  = permitted / proven.
Exit 4  = refused, with findings on stdout (MISCONFIGURED-style, matching the
          assignment gate's convention so callers can treat 4 as "blocked").
Exit 2  = usage/environment error (cannot form a verdict).

Exit 4 is a VERDICT; exit 2 is the ABSENCE of one. Callers must not collapse
them: "I could not check" is not "it is fine". Findings are emitted as a JSON
object on stdout so a caller cannot mistake chatty prose for a pass, and every
refusal names the offending code from FULL_RUN_CONTRACT.md §5.

Usage
    full_run_contract_check.py authorize  --project-root P [--intent TEXT]
    full_run_contract_check.py scope      --parent-scope S --child-brief FILE|-
    full_run_contract_check.py authorship --project-root P
    full_run_contract_check.py terminal   --project-root P
    full_run_contract_check.py intent     --text TEXT      (classify only)
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
else:  # pragma: no cover
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent

OK, REFUSED, ERROR = 0, 4, 2

# --------------------------------------------------------------------------
# Run scope vocabulary (FULL_RUN_CONTRACT.md §1)
# --------------------------------------------------------------------------
FULL, ADHOC = "full_lifecycle", "adhoc_review"
SCOPES = (FULL, ADHOC)

# Intent phrases that mean "produce or advance an academic deliverable".
# Deliberately a RECOGNISER, not an allowlist: §1.1 makes full_lifecycle the
# DEFAULT for prose-producing intent, so a phrase missing here does not become
# adhoc -- it stays full unless adhoc is explicitly requested. Ambiguity must
# fail toward the lifecycle: guessing adhoc silently skips it, guessing full
# costs one bootstrap prompt the user can decline.
FULL_RUN_PHRASES = (
    "harness full run", "full harness run", "full run", "full-run",
    "draft the whole paper", "draft the whole thing", "write the whole paper",
    "draft me an essay", "draft an essay", "write me an essay", "write an essay",
    "draft the paper", "write the paper", "draft this section", "write this section",
    "run the ladder", "start the ladder", "take this to ph4", "ship this",
    "full lifecycle", "whole lifecycle",
)
# Explicit, unambiguous opt-out. Only these make a run adhoc.
ADHOC_PHRASES = (
    "just review", "only review", "quick look", "quick review",
    "no artifacts", "no artefacts", "don't bootstrap", "do not bootstrap",
    "dont bootstrap", "ad hoc review", "adhoc review", "response only",
    "response-only", "without bootstrapping", "no scaffold",
)

# Child-dispatch instructions that narrow a full-lifecycle parent. These are the
# literal shapes observed at audit :112 / :185 / :278.
DOWNGRADE_MARKERS = (
    "lightweight run", "this is a lightweight", "response only",
    "response-only", "no artifacts", "no artefacts", "no-artifacts",
    "no state", "no-state", "do not attempt to write", "dont write artifacts",
    "do not write reviews", "do not bootstrap", "don't bootstrap",
    "no project scaffold", "no phase_state", "in your response only",
    "return findings in your response",
)

TERMINAL_MARKERS = (
    "ladder complete", "ph4", "g.4", "terminal pass", "converged",
    "shipped", "lifecycle complete", "terminal_phase_reached",
)


def _emit(code_findings: list[dict], status: str) -> None:
    print(json.dumps({"status": status, "findings": code_findings},
                     ensure_ascii=False, indent=1))


def _f(code: str, message: str, **extra) -> dict:
    d = {"code": code, "message": message}
    d.update(extra)
    return d


def _load_json(path: Path) -> tuple[dict | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig")), None
    except FileNotFoundError:
        return None, "absent"
    except (OSError, json.JSONDecodeError) as exc:
        return None, str(exc)


# --------------------------------------------------------------------------
# intent
# --------------------------------------------------------------------------
def classify_intent(text: str) -> str:
    """Classify a user request's run scope. Ambiguity -> full_lifecycle (§1.1)."""
    low = " ".join(text.lower().split())
    if any(p in low for p in ADHOC_PHRASES):
        return ADHOC
    if any(p in low for p in FULL_RUN_PHRASES):
        return FULL
    return FULL  # prose-producing default; see §1.1


def cmd_intent(args) -> int:
    scope = classify_intent(args.text)
    print(json.dumps({"status": "OK", "run_scope": scope}, ensure_ascii=False))
    return OK


# --------------------------------------------------------------------------
# authorize  (§2 -- no project, no prose)
# --------------------------------------------------------------------------
def authorize(project_root: Path | None) -> list[dict]:
    findings: list[dict] = []
    if project_root is None or not project_root.is_dir():
        findings.append(_f(
            "FRC-NO-PROJECT",
            "prose-producing intent with no native project root. A full run "
            "needs a project: run scripts/native_project_bootstrap.py "
            "--project-root <path> --project-name <name> --title \"<title>\" "
            "--intended-reader \"<readers>\", then resolve "
            "reviews/assignment_contract.json from the controlling source "
            "(references/ASSIGNMENT_MILESTONE_PROCESS.md). Do not write "
            "academic prose, a scratch draft, or a task checklist instead.",
            project_root=str(project_root) if project_root else None))
        return findings

    state, err = _load_json(project_root / "reviews" / "phase_state.json")
    if state is None:
        findings.append(_f("FRC-NO-PROJECT",
                           f"reviews/phase_state.json {err}; not a native project"))
        return findings
    mf = state.get("milestone_framework")
    if not isinstance(mf, dict):
        findings.append(_f("FRC-NO-PROJECT", "phase_state has no milestone_framework"))
    elif mf.get("mode") != "native":
        findings.append(_f("FRC-NO-PROJECT",
                           f"milestone_framework.mode is {mf.get('mode')!r}, not 'native'"))

    contract, cerr = _load_json(project_root / "reviews" / "assignment_contract.json")
    if contract is None:
        findings.append(_f("FRC-CONTRACT-MISSING",
                           f"reviews/assignment_contract.json {cerr}. Resolve it from "
                           "the controlling source; a filename or prior default is not "
                           "a substitute."))
    else:
        status = str(contract.get("status", "")).lower()
        if status and status not in {"resolved", "accepted"}:
            findings.append(_f("FRC-CONTRACT-MISSING",
                               f"assignment contract status is {status!r}, not resolved"))
        if contract.get("unresolved") is True:
            findings.append(_f("FRC-CONTRACT-MISSING", "assignment contract is unresolved"))
    return findings


def cmd_authorize(args) -> int:
    findings = authorize(args.project_root)
    if args.intent:
        scope = classify_intent(args.intent)
        if scope == ADHOC and findings:
            # An explicit ad hoc review is legal WITHOUT a project -- it just
            # cannot write prose, advance, or claim terminal (§1, §4). Report
            # the scope so the caller cannot silently treat it as a full run.
            print(json.dumps({"status": "OK", "run_scope": ADHOC,
                              "note": "ad hoc review: no prose, no advancement, "
                                      "no terminal claim, response is not evidence"},
                             ensure_ascii=False, indent=1))
            return OK
    if findings:
        _emit(findings, "REFUSED")
        return REFUSED
    _emit([], "OK")
    return OK


# --------------------------------------------------------------------------
# scope  (§1.2 -- a child may not narrow a full-lifecycle parent)
# --------------------------------------------------------------------------
def check_scope(parent_scope: str, brief: str) -> list[dict]:
    findings: list[dict] = []
    if parent_scope not in SCOPES:
        findings.append(_f("FRC-SCOPE-UNDECLARED",
                           f"parent scope {parent_scope!r} is not one of {SCOPES}"))
        return findings
    low = " ".join(brief.lower().split())
    if parent_scope == FULL:
        hits = sorted({m for m in DOWNGRADE_MARKERS if m in low})
        if hits:
            findings.append(_f(
                "FRC-SCOPE-DOWNGRADE",
                "child dispatch narrows a full_lifecycle parent to a "
                "lightweight/response-only/no-artifacts/no-state run. Under a full "
                "lifecycle the child must write its artefacts and state; a parent "
                "may not instruct it otherwise.",
                markers=hits))
    if parent_scope == ADHOC:
        hits = sorted({m for m in TERMINAL_MARKERS if m in low})
        if hits:
            findings.append(_f(
                "FRC-TERMINAL-UNPROVEN",
                "ad hoc review dispatch carries lifecycle/terminal vocabulary; an "
                "ad hoc run cannot advance the ladder or claim terminal.",
                markers=hits))
    return findings


def cmd_scope(args) -> int:
    if args.child_brief == "-":
        brief = sys.stdin.read()
    else:
        p = Path(args.child_brief)
        if not p.is_file():
            print(f"[ERROR] child brief not found: {p}", file=sys.stderr)
            return ERROR
        brief = p.read_text(encoding="utf-8", errors="replace")
    findings = check_scope(args.parent_scope, brief)
    if findings:
        _emit(findings, "REFUSED")
        return REFUSED
    _emit([], "OK")
    return OK


# --------------------------------------------------------------------------
# authorship  (§3 -- manuscript movement must be Generator-attributable)
# --------------------------------------------------------------------------
def check_authorship(project_root: Path) -> list[dict]:
    findings: list[dict] = []
    man_dir = project_root / "manuscript"
    if not man_dir.is_dir():
        return findings
    prose = [p for p in man_dir.rglob("*")
             if p.is_file() and p.suffix.lower() in {".md", ".tex"}
             and p.name != "revision_log.md" and p.name != "outline.md"]
    if not prose:
        return findings
    # Only non-empty prose needs an author.
    substantive = [p for p in prose if len(p.read_text(encoding="utf-8",
                                                       errors="replace").strip()) > 0]
    if not substantive:
        return findings
    log = project_root / "manuscript" / "revision_log.md"
    if not log.is_file():
        findings.append(_f(
            "FRC-AUTHORSHIP",
            "manuscript prose exists with no manuscript/revision_log.md: no "
            "Generator round accounts for these bytes. Only the Generator writes "
            "manuscript prose (agents/generator.md); a Planner/Evaluator write, or "
            "a draft produced outside any round, is out of contract.",
            files=[p.relative_to(project_root).as_posix() for p in substantive]))
    return findings


def cmd_authorship(args) -> int:
    if not args.project_root.is_dir():
        print(f"[ERROR] project root not found: {args.project_root}", file=sys.stderr)
        return ERROR
    findings = check_authorship(args.project_root)
    if findings:
        _emit(findings, "REFUSED")
        return REFUSED
    _emit([], "OK")
    return OK


# --------------------------------------------------------------------------
# terminal  (§4 -- the fifteen)
# --------------------------------------------------------------------------
def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check_terminal(project_root: Path) -> list[dict]:
    """The fifteen requirements. Absence of the project is itself requirement 0."""
    findings: list[dict] = []

    # 0/1 -- project + contract
    base = authorize(project_root)
    findings.extend(base)
    if any(f["code"] == "FRC-NO-PROJECT" for f in base):
        findings.append(_f("FRC-TERMINAL-UNPROVEN",
                           "terminal claim with no authoritative project: zero of the "
                           "fifteen requirements can be satisfied"))
        return findings

    state, _ = _load_json(project_root / "reviews" / "phase_state.json")
    state = state or {}
    mf = state.get("milestone_framework") or {}
    milestones = mf.get("milestones") or {}

    missing: list[str] = []

    # 2 -- M1..M4 accepted (respecting declared applicability)
    for key in ("M1", "M2", "M3", "M4"):
        m = milestones.get(key)
        if not isinstance(m, dict):
            missing.append(f"milestone {key} absent from milestone_framework")
            continue
        if m.get("applicability") == "not_applicable":
            continue
        if m.get("status") != "accepted":
            missing.append(f"{key}.status is {m.get('status')!r}, not 'accepted'")
        appr = m.get("approval") or {}
        if appr.get("status") != "accepted":
            missing.append(f"{key}.approval.status is {appr.get('status')!r}")
        else:
            if not appr.get("authority"):
                missing.append(f"{key}.approval.authority is empty")
            ev = appr.get("evidence_path")
            if not ev:
                missing.append(f"{key}.approval.evidence_path is empty")
            elif not (project_root / ev).is_file():
                missing.append(f"{key}.approval.evidence_path does not resolve: {ev}")

        # 3 -- exact-byte deliverable bindings
        for art in m.get("artifacts") or []:
            if not isinstance(art, dict):
                continue
            ap, ah = art.get("path"), art.get("sha256")
            if not ap:
                continue
            f = project_root / ap
            if not f.is_file():
                missing.append(f"{key} artifact missing on disk: {ap}")
            elif ah and _sha(f) != ah:
                missing.append(f"{key} artifact bytes differ from recorded sha256: {ap}")

        # 4/5 -- F9 handoffs consumed + packet bytes bound
        ho = m.get("handoff") or {}
        if key != "M4":
            if ho.get("status") not in {"consumed", "ready"}:
                missing.append(f"{key}.handoff.status is {ho.get('status')!r}")
            pp, ps = ho.get("packet_path"), ho.get("packet_sha256")
            if not pp:
                missing.append(f"{key}.handoff.packet_path is empty (no F9 packet)")
            else:
                pf = project_root / pp
                if not pf.is_file():
                    missing.append(f"{key} F9 packet missing on disk: {pp}")
                elif ps and _sha(pf) != ps:
                    missing.append(f"{key} F9 packet bytes differ from packet_sha256: {pp}")

    # 6 -- events
    if not (mf.get("events") or []):
        missing.append("milestone_framework.events is empty (no recorded lifecycle events)")

    # 6 -- F7 evidence
    f7 = list((project_root / "reviews").glob("**/f7_*.json")) + \
         list((project_root / "reviews").glob("**/evidence*.json"))
    if not f7:
        missing.append("no F7 evidence packets under reviews/")

    # 7 -- revision log
    if not (project_root / "manuscript" / "revision_log.md").is_file():
        missing.append("manuscript/revision_log.md absent")

    # 8 -- deterministic + Check 8 evidence
    if not (project_root / "reviews" / "findings.json").is_file():
        missing.append("reviews/findings.json absent (deterministic check evidence)")
    check8 = list((project_root / "reviews").glob("**/*check8*")) + \
             list((project_root / "reviews").glob("**/*accessibility*"))
    if not check8:
        missing.append("no Check 8 accessibility evidence under reviews/")

    # 9 -- convergence journal + TerminalSignoffRow
    signoff = project_root / "reviews" / "ph3_convergence_signoff.md"
    if not signoff.is_file():
        missing.append("reviews/ph3_convergence_signoff.md absent (no TerminalSignoffRow)")
    else:
        text = signoff.read_text(encoding="utf-8", errors="replace")
        if "is_terminal: true" not in text:
            missing.append("ph3_convergence_signoff.md carries no `is_terminal: true` row")
        if "user_signature" not in text:
            missing.append("TerminalSignoffRow has no user_signature")
    if not (project_root / "reviews" / "convergence_log.md").is_file():
        missing.append("reviews/convergence_log.md absent (no convergence journal)")

    # 10 -- deep pass, 11 -- MCR
    sections = state.get("sections")
    sect_iter = sections.values() if isinstance(sections, dict) else (
        sections if isinstance(sections, list) else [])
    deep = [s for s in sect_iter if isinstance(s, dict)
            and s.get("pre_mcr_deep_pass_completed") is True]
    if not deep:
        missing.append("no section records pre_mcr_deep_pass_completed: true (deep pass)")
    if not list((project_root / "reviews").glob("**/*mcr*")):
        missing.append("no MCR artefact under reviews/")

    # 12 -- G.4
    g4 = project_root / "reviews" / "G4_signoff.md"
    if not g4.is_file():
        missing.append("reviews/G4_signoff.md absent")
    elif "PASS" not in g4.read_text(encoding="utf-8", errors="replace"):
        missing.append("reviews/G4_signoff.md records no PASS")

    # 13 -- Reflector-full close-out
    if not list((project_root / "reviews").glob("**/reflector_full*")):
        missing.append("no Reflector-full close-out artefact under reviews/")

    # 14 -- F8 final-round report
    if not list((project_root / "reviews").glob("**/f8_*")):
        missing.append("no F8 final-round report under reviews/")

    # 15 -- terminal state + final packet
    if state.get("terminal_phase_reached") is not True:
        missing.append("phase_state.terminal_phase_reached is not true")
    fin = (milestones.get("FINAL") or milestones.get("M5") or {})
    if isinstance(fin, dict) and fin:
        fho = fin.get("handoff") or {}
        if not fho.get("packet_path"):
            missing.append("FINAL milestone has no terminal F9 packet")

    if missing:
        findings.append(_f(
            "FRC-TERMINAL-UNPROVEN",
            f"{len(missing)} of the FULL_RUN_CONTRACT §4 requirements are unmet; a "
            "terminal claim (\"Ph4\", \"G.4\", \"terminal PASS\", \"ladder complete\", "
            "\"converged\", \"shipped\") is refused.",
            unmet=missing))
    return findings


def cmd_terminal(args) -> int:
    findings = check_terminal(args.project_root)
    if findings:
        _emit(findings, "REFUSED")
        return REFUSED
    _emit([], "OK")
    return OK


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("authorize", help="may academic prose be written here?")
    a.add_argument("--project-root", type=Path)
    a.add_argument("--intent", type=str, default=None)
    a.set_defaults(fn=cmd_authorize)

    s = sub.add_parser("scope", help="is this child dispatch legal under its parent?")
    s.add_argument("--parent-scope", required=True)
    s.add_argument("--child-brief", required=True, help="file path, or - for stdin")
    s.set_defaults(fn=cmd_scope)

    au = sub.add_parser("authorship", help="is manuscript movement Generator-attributable?")
    au.add_argument("--project-root", required=True, type=Path)
    au.set_defaults(fn=cmd_authorship)

    t = sub.add_parser("terminal", help="is a terminal claim earned?")
    t.add_argument("--project-root", type=Path)
    t.set_defaults(fn=cmd_terminal)

    i = sub.add_parser("intent", help="classify a request's run scope")
    i.add_argument("--text", required=True)
    i.set_defaults(fn=cmd_intent)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
