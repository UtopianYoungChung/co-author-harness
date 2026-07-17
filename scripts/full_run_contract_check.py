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

THIS IS NOT A LIFECYCLE AUTHORITY. IT COMPOSES ONE.
------------------------------------------------------
The first cut of this file answered those questions by reading the project the
way a person skims it: glob for a file named ``*mcr*``, look for ``PASS`` in the
G.4 signoff, treat ``manuscript/revision_log.md`` existing as proof a Generator
wrote the manuscript. Every one of those is a filename, a file's presence, or a
substring standing in for a fact. CodeRabbit's semantic review of PR #14 walked
straight through them: ``verdict: NOT PASS`` contains ``PASS``; an artifact with
no recorded ``sha256`` skipped the exact-byte comparison because the check read
``if recorded_hash and recorded_hash != actual``; ``mcr_notes_scratch.md``
satisfied the MCR requirement by being named suggestively.

Those were not eight coincidental bugs. They were one design error: a second,
weaker lifecycle authority, written from memory, next to the real one. The
package already has validators that decide these facts, and they are stricter
than what was written here -- ``milestone_framework_validate._file_binding``
compares ``expected_sha != actual_sha`` unconditionally, so an ABSENT hash is
already a finding, which is precisely the bypass this file had opened.

So the rule for this file, and for anything extending it:

    compose authoritative structured evidence;
    never infer lifecycle truth from filenames, file presence, or substrings.

Concretely, every predicate below DELEGATES:

  project / contract / receipt   assignment_process_gate.verify_receipt
                                 (binds receipt to live phase_state + contract
                                 bytes, so staleness is its verdict, not ours)
                                 + assignment_dispatch_preflight.py
  milestones, approvals,         milestone_framework_validate.validate_gate over
  artifact + F9 packet bytes,    ALL THREE boundaries (ph1_to_ph2, ph4_admission,
  events, G.4 / ship signoff     ph4_terminal_close). `_signed_status` requires
                                 exactly one explicit `status: PASS|APPROVED|
                                 SIGNED` line -- which is why "NOT PASS" fails.
  phase state shape              phase_state_validate
  TerminalSignoffRow             pre_phase_advance_check._parse_t3_signoff_rows
  MCR clearance                  pre_phase_advance_check._is_mcr_cleared
                                 (MCR clearance is a STATE predicate, not a file
                                 -- which is the real reason no filename can
                                 satisfy it)

When one of those authorities changes, this file inherits the change. That is
the point: there is one place where each lifecycle fact is decided, and it is
not here.

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
import io
import json
import re
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
else:  # pragma: no cover
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

# The composed authorities. Import failure is an ERROR (exit 2), never a pass:
# if the real validator cannot be loaded we have no verdict, and "I could not
# check" must never read as "it is fine".
import assignment_process_gate as apg              # noqa: E402
import milestone_framework_validate as mfv         # noqa: E402
import phase_state_validate as psv                 # noqa: E402
import pre_phase_advance_check as ppa              # noqa: E402
import reader_accessibility_policy as rap          # noqa: E402


# Which milestone each gate boundary is ABOUT (milestone_framework_validate's
# own target_map). Kept for diagnostics; it no longer gates anything.
BOUNDARY_TARGETS = {
    "ph1_to_ph2": ("M1", "M2", "M3"),
    "ph4_admission": ("M4",),
    "ph4_terminal_close": ("M5",),
}

# ---------------------------------------------------------------------------
# `not_applicable` DOES NOT REACH TERMINAL, in a full_lifecycle run.
#
# An earlier cut skipped the ph4_admission / ph4_terminal_close boundaries when
# M4 / M5 declared `applicability: not_applicable`, reasoning that a waived
# milestone is "no requirement" rather than a skipped one. That reasoning is
# sound for a MILESTONE-LOCAL question and wrong for a TERMINAL one, and the
# difference is the whole contract:
#
#   * A full_lifecycle run is the user asking for the whole ladder. Every
#     milestone is required BECAUSE THEY ASKED FOR IT -- applicability is a
#     statement about one milestone's own validation, not a licence to redefine
#     what the user requested.
#   * §4 terminal evidence is not satisfiable without M5 anyway: requirement 2
#     needs M1-M4 accepted, and requirement 15 needs the FINAL/M5 packet and
#     terminal state. A "terminal claim" over a waived M5 is a claim that the
#     deliverable shipped without the deliverable.
#   * The skip was reachable by the very party the gate constrains. A waiver
#     that converts "ladder complete" from false to true is not applicability;
#     it is the audit failure this whole file exists to prevent, wearing the
#     vocabulary of a legitimate feature.
#
# Authorized N/A remains meaningful where it belongs: milestone-local and ad hoc
# validation (`milestone_framework_validate` validates its own
# `authorized_not_applicable` fixture at TARGET M4 and yields NOT_APPLICABLE).
# It simply cannot produce "ladder complete", "terminal PASS", or shipment.
# Every boundary runs at terminal, unconditionally; validate_gate still skips
# individual `not_applicable` records INSIDE a boundary where its own rules say
# so, which is its call to make, not ours.
# ---------------------------------------------------------------------------

PREFLIGHT = SCRIPTS / "assignment_dispatch_preflight.py"

OK, REFUSED, ERROR = 0, 4, 2

# The assignment gate's target vocabulary is M1..M4 + FINAL; the milestone
# ledger's schema is M1..M5 with additionalProperties:false (verified against
# references/schemas/milestone_framework.schema.json, which never mentions
# "FINAL"). FINAL is the assignment-side NAME for the ledger's M5. The old code
# wrote `milestones.get("FINAL") or milestones.get("M5")`, which could only ever
# find M5 -- a guess that happened to work, not a mapping.
ASSIGNMENT_TARGETS = apg.EXPECTED_SEQUENCE          # ("M1","M2","M3","M4","FINAL")
LEDGER_KEY = {"M1": "M1", "M2": "M2", "M3": "M3", "M4": "M4", "FINAL": "M5"}

# --------------------------------------------------------------------------
# Run scope vocabulary (FULL_RUN_CONTRACT.md §1)
# --------------------------------------------------------------------------
FULL, ADHOC = "full_lifecycle", "adhoc_review"
SCOPES = (FULL, ADHOC)

# --------------------------------------------------------------------------
# ADVISORY ONLY -- phrase lists are NOT the enforcement mechanism.
#
# The mechanism is: scope is DECLARED explicitly and gates are deterministic.
# A phrase list cannot be the floor, for the reason this whole repair exists:
# a list only catches the wordings someone thought of, and the next failure
# will be worded differently. "Harness full run" is one phrasing of an
# unbounded intent space; matching it would fix one sentence, not the contract.
#
# So these lists are a HINT for a human or agent deciding what to declare, and
# `intent` is explicitly non-authorizing (it cannot permit anything). Every
# permission below keys off an EXPLICIT declared scope; a dispatch that omits
# the declaration is refused (FRC-SCOPE-UNDECLARED) rather than sniffed.
# --------------------------------------------------------------------------
FULL_RUN_PHRASES = (
    "harness full run", "full harness run", "full run", "full-run",
    "draft the whole paper", "draft the whole thing", "write the whole paper",
    "draft me an essay", "draft an essay", "write me an essay", "write an essay",
    "draft the paper", "write the paper", "draft this section", "write this section",
    "run the ladder", "start the ladder", "take this to ph4", "ship this",
    "full lifecycle", "whole lifecycle",
)
ADHOC_PHRASES = (
    "just review", "only review", "quick look", "quick review",
    "no artifacts", "no artefacts", "don't bootstrap", "do not bootstrap",
    "dont bootstrap", "ad hoc review", "adhoc review", "response only",
    "response-only", "without bootstrapping", "no scaffold",
)

# A declared scope line in a dispatch brief: `run_scope: full_lifecycle`.
RUN_SCOPE_RE = re.compile(r"(?mi)^\s*run_scope\s*:\s*([A-Za-z_]+)\s*$")

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
    """ADVISORY. Suggests a scope to DECLARE; authorizes nothing.

    Deliberately cannot refuse and cannot permit: it always exits 0. If this
    could authorize, the phrase list would be the contract, and a phrase list
    only catches the wordings someone already thought of.
    """
    scope = classify_intent(args.text)
    print(json.dumps({"status": "OK", "advisory": True, "suggested_run_scope": scope,
                      "note": "advisory only: this classification authorizes nothing. "
                              "Declare the scope explicitly; gates key off the "
                              "declaration and off project state, never off phrasing."},
                     ensure_ascii=False))
    return OK


# --------------------------------------------------------------------------
# authorize  (§2 -- no project, no prose)
# --------------------------------------------------------------------------
def project_floor(project_root: Path | None) -> list[dict]:
    """§2 items 1-2 ONLY: is this an authoritative native project at all?

    Split out from `authorize` because `terminal` needs the floor without the
    receipt: a finished run has no outstanding target to hold a READY receipt
    for. `authorize` = this floor + items 3-5.
    """
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
    elif not isinstance(contract, dict):
        # `_load_json` returns whatever the file parses to -- a list, a string, a
        # number. Calling .get() on that raised AttributeError, so a malformed
        # contract crashed the gate instead of being refused by it. A gate that
        # dies on bad input has no verdict, and exit 2 is not exit 4: "I could
        # not check" must never be read as "it is fine".
        findings.append(_f(
            "FRC-CONTRACT-MISSING",
            f"reviews/assignment_contract.json parses to {type(contract).__name__}, "
            "not an object. A resolved assignment contract is a JSON object; a "
            "list or scalar is not a contract in a form this gate can honour.",
            parsed_type=type(contract).__name__))
    else:
        # EXACT match, positively asserted. The old test was
        #   `if status and status not in {"resolved", "accepted"}`
        # which passed a contract with NO status at all -- absence read as
        # consent, in the one check whose entire job is to require consent.
        status = str(contract.get("status", "")).strip().lower()
        if status != "resolved":
            findings.append(_f(
                "FRC-CONTRACT-MISSING",
                f"assignment contract status is {status or '<absent>'!r}; exactly "
                "'resolved' is required. An absent, empty, or differently-worded "
                "status is not a resolved contract."))
        if contract.get("unresolved") is True:
            findings.append(_f("FRC-CONTRACT-MISSING", "assignment contract is unresolved"))
    return findings


def derive_active_target(project_root: Path) -> tuple[str | None, list[dict]]:
    """The active target is DERIVED from state: first non-accepted of M1..FINAL.

    Never chosen by the agent, and never read from a request (§2 item 3). An
    applicable milestone that is not `accepted` is the target; `not_applicable`
    records are skipped only when the ledger itself declares them so.
    """
    state, _ = _load_json(project_root / "reviews" / "phase_state.json")
    mf = (state or {}).get("milestone_framework")
    milestones = mf.get("milestones") if isinstance(mf, dict) else None
    if not isinstance(milestones, dict):
        return None, [_f("FRC-NO-PROJECT",
                         "milestone_framework.milestones is absent or not an object; "
                         "no active target can be derived from state")]
    for target in ASSIGNMENT_TARGETS:
        record = milestones.get(LEDGER_KEY[target])
        if not isinstance(record, dict):
            return None, [_f(
                "FRC-MILESTONE-ORDER",
                f"milestone {LEDGER_KEY[target]} is absent from the ledger; the "
                "active target cannot be derived. An absent milestone is not a "
                "skipped one.")]
        if record.get("applicability") == "not_applicable":
            continue
        if record.get("status") != "accepted":
            return target, []
    return None, []  # every applicable milestone accepted: nothing to author


def _find_receipt(project_root: Path, target: str) -> Path | None:
    """The receipt path is DERIVED from the assignment gate's own contract.

    reviews/.harness/assignment/gate_receipt_{target}_<utc>.json -- the shape
    `assignment_process_gate._receipt_path_finding` enforces. We do not invent a
    location, and we do not accept one from an argument: newest candidate wins
    and `verify_receipt` decides whether it is actually valid and fresh.
    """
    d = project_root / "reviews" / ".harness" / "assignment"
    if not d.is_dir():
        return None
    cands = sorted(d.glob(f"gate_receipt_{target}_*.json"))
    return cands[-1] if cands else None


def authorize(project_root: Path | None) -> list[dict]:
    """§2 in full: floor (1-2) + derived target (3) + READY receipt (4) + preflight (5).

    A resolved contract used to be the whole test, which meant items 3-5 of the
    contract this script claims to enforce were simply not enforced. The receipt
    is what makes authorization CURRENT rather than historical:
    `verify_receipt` binds it to live phase_state and contract bytes, so a stale
    receipt is refused by the gate that issued it, not by a rule re-guessed here.
    """
    findings = project_floor(project_root)
    if findings:
        return findings
    assert project_root is not None

    target, derr = derive_active_target(project_root)
    findings.extend(derr)
    if derr:
        return findings
    if target is None:
        # Every applicable milestone is accepted, so there is no lifecycle target
        # to author against. The first cut returned no findings here, which
        # `cmd_authorize` renders as OK -- authorizing prose into a project with
        # nothing left to write, the one state where a write is certainly out of
        # contract. "No target" is not "no objection"; it is the absence of the
        # thing that would make a write legible. Refused, without demanding a
        # receipt that cannot exist in this state.
        findings.append(_f(
            "FRC-NO-ACTIVE-MILESTONE",
            "every applicable milestone M1-FINAL is already accepted: there is no "
            "active target to authorize prose against. If the run is finished, "
            "validate it with `full_run_contract_check.py terminal`; if more work "
            "is intended, reopen a milestone or derive a new target through the "
            "milestone framework first. Do not write prose against a closed ladder.",
            active_target=None))
        return findings

    receipt = _find_receipt(project_root, target)
    if receipt is None:
        return [_f(
            "FRC-CONTRACT-MISSING",
            f"no assignment gate receipt for the derived active target {target}. "
            f"Run scripts/assignment_process_gate.py --project-root <p> --stage "
            f"{'final' if target == 'FINAL' else 'draft'} "
            f"{'' if target == 'FINAL' else f'--target-milestone {target} '}"
            "--emit-receipt reviews/.harness/assignment/"
            f"gate_receipt_{target}_<utc>.json. A resolved contract alone does not "
            "authorize a write: it says what the work IS, not that this round may "
            "do it now.",
            active_target=target)]

    gate_findings = apg.verify_receipt(project_root.resolve(), receipt.resolve())
    if gate_findings:
        return [_f("FRC-CONTRACT-MISSING",
                   f"assignment gate refused the receipt for {target}: {code}: {msg}",
                   active_target=target, receipt=str(receipt))
                for code, msg in gate_findings]

    pf = subprocess.run(
        [sys.executable, str(PREFLIGHT), "--project-root", str(project_root),
         "--receipt", str(receipt), "--expected-target", target],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    if pf.returncode != 0:
        return [_f("FRC-CONTRACT-MISSING",
                   f"assignment_dispatch_preflight.py refused the dispatch for "
                   f"{target} (exit {pf.returncode})",
                   active_target=target, receipt=str(receipt),
                   preflight_stdout=pf.stdout.strip()[:600])]
    return findings


def cmd_authorize(args) -> int:
    """May academic prose be written here?

    The scope is an EXPLICIT argument, never sniffed from the request text. An
    earlier cut of this command accepted `--intent` and classified it with a
    phrase list -- which made a phrase list load-bearing for a PERMISSION: an
    unanticipated wording of "just look at this" would have silently authorized
    an ad hoc path. Permissions key off declarations; phrase lists only advise.
    """
    scope = (args.run_scope or FULL).strip().lower()
    if scope not in SCOPES:
        _emit([_f("FRC-SCOPE-UNDECLARED",
                  f"--run-scope {scope!r} is not one of {SCOPES}")], "REFUSED")
        return REFUSED

    if scope == ADHOC:
        # An explicitly declared ad hoc review is legal WITHOUT a project -- it
        # simply may not write prose, advance the ladder, or claim terminal, and
        # its response is not evidence (§1, §4).
        print(json.dumps({"status": "OK", "run_scope": ADHOC,
                          "note": "ad hoc review: no prose, no advancement, no "
                                  "terminal claim, response is not F7/F8/F9 evidence"},
                         ensure_ascii=False, indent=1))
        return OK

    findings = authorize(args.project_root)
    if findings:
        _emit(findings, "REFUSED")
        return REFUSED
    _emit([], "OK")
    return OK


# --------------------------------------------------------------------------
# scope  (§1.2 -- a child may not narrow a full-lifecycle parent)
# --------------------------------------------------------------------------
def check_scope(parent_scope: str, brief: str) -> list[dict]:
    """Is this child dispatch legal under its parent?

    STRUCTURE FIRST, TEXT SECOND. The primary rule is a comparison of DECLARED
    scopes: the parent states one, the child must carry EXACTLY that one. That
    is general -- it holds for wordings nobody anticipated, which is the whole
    point, since the next failure will not be phrased like the last one.

    EXACT inheritance, both directions. The first cut only refused DOWNGRADE
    (full parent, narrower child) and so left ESCALATION entirely unguarded: an
    `adhoc_review` parent could dispatch a `full_lifecycle` child, and the child
    would then be authorized to write prose and advance the ladder under a
    parent that could do neither. A child may not grant itself authority its
    parent does not have; scope is inherited, not negotiated.

    The marker scan is a SECONDARY net for the self-contradicting brief: one
    that declares `run_scope: full_lifecycle` and then says "return findings in
    your response only". Markers can only ADD a refusal; they can never grant
    one, so the enforcement floor never depends on a phrase list.
    """
    findings: list[dict] = []
    if parent_scope not in SCOPES:
        findings.append(_f("FRC-SCOPE-UNDECLARED",
                           f"parent scope {parent_scope!r} is not one of {SCOPES}. "
                           "Every dispatch declares its scope; it is never inferred."))
        return findings

    # --- primary: the child's DECLARED scope -------------------------------
    m = RUN_SCOPE_RE.search(brief)
    child_scope = m.group(1).strip().lower() if m else None
    if child_scope is not None and child_scope not in SCOPES:
        findings.append(_f("FRC-SCOPE-UNDECLARED",
                           f"child declares run_scope: {child_scope!r}, not one of {SCOPES}"))
        return findings
    if child_scope is None:
        findings.append(_f(
            "FRC-SCOPE-UNDECLARED",
            "child dispatch carries no `run_scope:` declaration. A dispatch whose "
            "scope must be guessed is refused: inheritance is explicit, not "
            "assumed. Add `run_scope: " + parent_scope + "` if that is what is "
            "intended."))
    elif child_scope != parent_scope:
        code = ("FRC-SCOPE-DOWNGRADE" if parent_scope == FULL
                else "FRC-SCOPE-ESCALATION")
        detail = ("A child may not narrow the run: under a full lifecycle it must "
                  "write its artefacts and state."
                  if parent_scope == FULL else
                  "A child may not widen the run: an ad hoc parent cannot confer "
                  "authority to write prose, advance the ladder, or claim terminal, "
                  "because it does not hold that authority itself.")
        findings.append(_f(
            code,
            f"child declares run_scope: {child_scope} under a {parent_scope} parent; "
            f"scope must be inherited exactly. {detail}",
            parent_scope=parent_scope, child_scope=child_scope))

    # --- secondary: a brief that contradicts its own declaration -----------
    low = " ".join(brief.lower().split())
    if parent_scope == FULL:
        hits = sorted({m for m in DOWNGRADE_MARKERS if m in low})
        if hits:
            findings.append(_f(
                "FRC-SCOPE-DOWNGRADE",
                "child dispatch instructs a lightweight/response-only/no-artifacts/"
                "no-state run under a full_lifecycle parent. Under a full lifecycle "
                "the child must write its artefacts and state; a parent may not "
                "instruct it otherwise.",
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
# The structured experiment log format is specified at
# references/AGENT_CONTRACTS.md:163-177 (Generator "Outputs (write)"): a round
# header plus Hypothesis / Scope / Changes / Verdict. We check THAT, because it
# is what a Generator round actually produces. The previous check was
# `log.is_file()` -- so an empty file, or one reading "today I had a sandwich",
# attributed a manuscript to a round that never ran. A filename is not evidence.
ROUND_HEADER_RE = re.compile(r"(?mi)^##\s+Round\s+\S+")
VERDICT_RE = re.compile(r"(?mi)^\*\*Verdict:\*\*\s*(RETAIN|REVERT|PARTIAL)\b")
REQUIRED_ROUND_FIELDS = ("Hypothesis", "Scope", "Changes")


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

    files = [p.relative_to(project_root).as_posix() for p in substantive]
    log = project_root / "manuscript" / "revision_log.md"
    if not log.is_file():
        findings.append(_f(
            "FRC-AUTHORSHIP",
            "manuscript prose exists with no manuscript/revision_log.md: no "
            "Generator round accounts for these bytes. Only the Generator writes "
            "manuscript prose (agents/generator.md); a Planner/Evaluator write, or "
            "a draft produced outside any round, is out of contract.",
            files=files))
        return findings

    text = log.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        findings.append(_f(
            "FRC-AUTHORSHIP",
            "manuscript/revision_log.md is empty: an empty log attributes nothing. "
            "Manuscript prose exists that no Generator round accounts for.",
            files=files))
        return findings

    if not ROUND_HEADER_RE.search(text):
        findings.append(_f(
            "FRC-AUTHORSHIP",
            "manuscript/revision_log.md contains no `## Round <N>` entry. The "
            "Generator's round entry uses the structured experiment log format "
            "(references/AGENT_CONTRACTS.md 'Outputs (write)'); prose in the log "
            "that is not a round entry attributes nothing.",
            files=files))
        return findings

    missing = [k for k in REQUIRED_ROUND_FIELDS
               if not re.search(rf"(?mi)^\*\*{k}:\*\*", text)]
    if not VERDICT_RE.search(text):
        missing.append("Verdict (RETAIN|REVERT|PARTIAL)")
    if missing:
        findings.append(_f(
            "FRC-AUTHORSHIP",
            "manuscript/revision_log.md has a round header but is not a complete "
            f"round entry: missing {', '.join(missing)}. An incomplete entry is a "
            "claim that a round happened, not a record of one.",
            files=files, missing_fields=missing))
        return findings

    # §3 requires BOTH halves: a Generator round entry AND a preflight receipt
    # for the round. A complete-looking entry is still only the round's own
    # account of itself -- it is written by the same actor whose authority is in
    # question, so on its own it proves the claim by restating it. The receipt is
    # the independent half, and it is the assignment gate's verdict, not ours.
    #
    # Only meaningful while a target is outstanding. Once every applicable
    # milestone is accepted there is no round in flight to hold a receipt, and
    # the manuscript bytes are bound by the ledger itself (M4's artifact sha256,
    # enforced by milestone_framework_validate._file_binding at `terminal`), so
    # requiring a live receipt here would make a finished project unprovable.
    if not (project_root / "reviews" / "phase_state.json").is_file():
        return findings
    target, derr = derive_active_target(project_root)
    if derr or target is None:
        return findings
    receipt = _find_receipt(project_root, target)
    if receipt is None:
        findings.append(_f(
            "FRC-AUTHORSHIP",
            f"manuscript prose exists and {target} is still outstanding, but no "
            f"assignment gate receipt authorizes a write against {target}. The "
            "round's own log entry is not evidence that the round was permitted "
            "to run: those bytes were written without authorization.",
            files=files, active_target=target))
        return findings
    gate_findings = apg.verify_receipt(project_root.resolve(), receipt.resolve())
    if gate_findings:
        findings.extend(_f(
            "FRC-AUTHORSHIP",
            f"the receipt covering the round that wrote this prose is not valid "
            f"for {target}: {code}: {msg}",
            files=files, active_target=target, receipt=str(receipt))
            for code, msg in gate_findings)
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
def _phase_guardrail_findings(project_root: Path, state: dict) -> list[str]:
    """Requirements 9, 10 and 11 -- each from the authority that is TERMINAL-AWARE.

    Which authority answers "has the MCR passed?" depends on WHEN you ask, and
    getting that wrong is how a gate refuses good work.

    `pre_phase_advance_check.check_clause_f` is a PRE-ADVANCE guardrail: its
    `_is_mcr_cleared` asks "may this section ENTER T4?", and that question is
    answered while the section still sits at Ph3_converged. Composing it here
    refused the baseline outright -- a finished project's sections are at Ph4,
    so `current_tier` is T4, so "not at T3_converged", so E-MCR-NOT-CLEARED on a
    perfectly valid terminal claim. The admission gate is not a completion gate;
    it already ran, at the moment it applied.

    `milestone_framework_validate.validate_document(..., target="Ph4")` is the
    terminal-aware one, and it decides all three of these per section:

      MF-PHASE  "Ph4 target has no valid unretracted MCR admission or
                ceiling-lock proof surface"       -- the MCR, asked correctly:
                not "may it be admitted?" but "is the admission on the record?"
      MF-PHASE  "Ph4 MCR continuity requires the pre-MCR deep pass to be
                complete"                          -- per SECTION (requirement
                10). The hand-rolled `if not deep` passed when ONE of several
                sections carried the flag.
      MF-PHASE  "Ph4 MCR continuity requires current terminal Ph3 convergence
                signoff evidence"

    `check_clause_g` remains the row-shape authority (requirement 9): a terminal
    row needs iteration_number, a non-null convergence_metric_value, a legal
    t3_verdict, final_owner_state, and the terminal/re-engagement exclusion --
    where the hand-rolled version checked three fields and accepted rows the
    authority rejects. Its clauses keep a T-coded internal API, so the ledger is
    translated through `ppa.translate_phase_ledger`, the same translation
    `load_ledger` uses.
    """
    out: list[str] = []

    # --- MCR admission proof + per-section deep pass + signoff continuity ----
    try:
        result = mfv.validate_document(project_root, state, "Ph4")
        for f in result.findings:
            out.append(f"[Ph4] {f.code} {f.path}: {f.message}")
    except Exception as exc:  # noqa: BLE001
        out.append(f"[Ph4] milestone validation raised {type(exc).__name__}: {exc}")

    # --- full TerminalSignoffRow validation ---------------------------------
    try:
        ledger = ppa.translate_phase_ledger(state)
    except ppa.LedgerTranslationError as exc:
        # The translator now REFUSES malformed sections rather than dropping
        # them. That refusal is a terminal finding, not an error: a ledger whose
        # sections cannot be read is a ledger whose sections cannot be validated.
        return out + [f"[phase_state] malformed ledger: {exc}"]
    except Exception as exc:  # noqa: BLE001
        return out + [f"[clause g] ledger translation raised "
                      f"{type(exc).__name__}: {exc}"]

    sections = ledger.get("sections") or []
    if not sections:
        return out + ["phase_state.sections is empty: the convergence signoff "
                      "cannot be attributed to any section"]

    seen: set[tuple[str, str]] = set()
    for section in sections:
        ctx = ppa.CheckContext(
            project_root=project_root,
            target_tier="T4",
            target_section_key=ppa._heading_key(section.get("heading_path", [])),
            target_section=section,
            ledger=ledger,
            t3_staleness_budget_days=14,
            strict_clause_f=False,
        )
        try:
            ppa.check_clause_g(ctx)
        except Exception as exc:  # noqa: BLE001
            out.append(f"[clause g] raised {type(exc).__name__}: {exc}")
            break
        for f in ctx.findings:
            key = (f.code, f.message)
            if key in seen:
                continue  # the signoff file is shared; each section re-reads it
            seen.add(key)
            out.append(f"[clause {f.clause}] {f.code}: {f.message}")
    return out


# Terminal-acceptable Check 8 aggregate. `recompute_check8` yields CLEAN /
# BORDERLINE / MAJOR / BLOCKER; the ladder's floor is "no Check 8 BLOCKER"
# (run-phase-3 SKILL.md, FULL_RUN_CONTRACT.md §4 row 8).
CHECK8_TERMINAL_REFUSED = {"BLOCKER"}


def _check8_findings(project_root: Path, state: dict) -> list[str]:
    """Requirement 8 (Check 8 half), from the CANONICALLY BOUND evidence.

    `milestone_framework_validate` already binds this evidence by hash, parses
    it, runs `validate_check8_evidence`, and requires the recorded
    `aggregate_verdict` to equal the recomputed one -- so validate_gate covers
    schema and consistency. What it does not do is require the verdict to be
    terminally acceptable: a project may record, consistently and truthfully,
    an aggregate of BLOCKER. Consistency is not clearance.

    The evidence is located through the ledger's `policy_evidence` binding, not
    a `reviews/**/*check8*` glob. The glob was the same category error as the
    MCR one: it asked the filesystem which file is the evidence, when only the
    ledger knows -- and it accepted `{"aggregate": "CLEAN"}`, a document with no
    subchecks, no profile binding, and no relation to the manuscript.
    """
    # Type-check every nested container before use. `or {}` guards ABSENCE but
    # not WRONG TYPE: a list is truthy, so it sails past `or {}` and then
    # `.get()` raises AttributeError -- turning the refusal this function exists
    # to produce into exit 2, the absence of a verdict. Garbage in must mean
    # refusal out, not a stack trace.
    mf = state.get("milestone_framework")
    if not isinstance(mf, dict):
        return [f"milestone_framework must be an object, got {type(mf).__name__}"]
    milestones = mf.get("milestones")
    if not isinstance(milestones, dict):
        return [f"milestone_framework.milestones must be an object, got "
                f"{type(milestones).__name__}"]
    bindings = mf.get("policy_bindings")
    binding = bindings.get("reader_accessibility") if isinstance(bindings, dict) else None
    transitions = binding.get("transitions") if isinstance(binding, dict) else None
    if not isinstance(transitions, dict):
        transitions = {}

    bound = []
    for key, rec in milestones.items():
        if not isinstance(rec, dict):
            return [f"milestone_framework.milestones.{key} must be an object, got "
                    f"{type(rec).__name__}"]
        ev = rec.get("policy_evidence")
        if ev is None:
            continue
        if not isinstance(ev, dict):
            return [f"{key}.policy_evidence must be an object, got "
                    f"{type(ev).__name__}"]
        rel = ev.get("check8_path")
        if rel is None:
            continue
        if not isinstance(rel, str) or not rel.strip():
            return [f"{key}.policy_evidence.check8_path must be a non-empty string, "
                    f"got {type(rel).__name__}"]
        bound.append((key, ev))
    if not bound:
        return ["no Check 8 evidence is bound in milestone_framework "
                "(milestones.*.policy_evidence.check8_path); a file merely named "
                "*check8* under reviews/ is not the project's Check 8 evidence"]

    out: list[str] = []
    for key, ev in bound:
        rel = ev.get("check8_path")
        path = project_root / rel
        if not path.is_file():
            out.append(f"{key}.policy_evidence.check8_path does not resolve: {rel}")
            continue
        try:
            sidecar = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            out.append(f"{key} Check 8 evidence is not canonical JSON: {rel}: {exc}")
            continue
        try:
            rap.validate_check8_evidence(sidecar)
            recomputed = rap.recompute_check8(sidecar, transitions)
        except Exception as exc:  # PolicyError and schema errors  # noqa: BLE001
            out.append(f"{key} Check 8 evidence is invalid: {rel}: {exc}")
            continue
        verdict = recomputed.get("aggregate_verdict")
        if verdict != sidecar.get("aggregate_verdict"):
            out.append(f"{key} Check 8 recorded aggregate "
                       f"{sidecar.get('aggregate_verdict')!r} != recomputed {verdict!r}")
        if verdict in CHECK8_TERMINAL_REFUSED:
            out.append(f"{key} Check 8 recomputed aggregate is {verdict}: a terminal "
                       "claim is refused while a Check 8 BLOCKER stands")
    return out


def check_terminal(project_root: Path) -> list[dict]:
    """The fifteen requirements. Absence of the project is itself requirement 0.

    Composed, not reimplemented. Requirements 2-6 and 12 are decided by
    `milestone_framework_validate.validate_gate` across ALL THREE boundaries --
    a terminal claim asserts the whole ladder held, so every gate on it must
    pass, not only the last. That single delegation closes, at once: G.4
    wording (`_signed_status` demands exactly one explicit `status:` line),
    absent artifact/packet hashes (`_file_binding` compares unconditionally),
    predecessor handoffs still `ready` rather than `consumed` (the ph1_to_ph2
    chain rule), and an absent M5 (the schema requires it).
    """
    findings: list[dict] = []

    # 0/1 -- project + contract. NOT the full `authorize`: a completed run has
    # no outstanding target, so requiring a live READY receipt here would make
    # the terminal check unsatisfiable exactly when it is meant to pass.
    base = project_floor(project_root)
    findings.extend(base)
    if any(f["code"] == "FRC-NO-PROJECT" for f in base):
        findings.append(_f("FRC-TERMINAL-UNPROVEN",
                           "terminal claim with no authoritative project: zero of the "
                           "fifteen requirements can be satisfied"))
        return findings

    state, _ = _load_json(project_root / "reviews" / "phase_state.json")
    state = state or {}

    missing: list[str] = []

    # 2-6, 12 -- the milestone authority, EVERY boundary, unconditionally.
    # A full_lifecycle terminal claim may not skip M4 or M5 on an applicability
    # declaration; see the note above BOUNDARY_TARGETS.
    for boundary in mfv.GATE_BOUNDARIES:
        try:
            result = mfv.validate_gate(project_root, state, boundary)
        except Exception as exc:  # noqa: BLE001
            missing.append(f"[{boundary}] milestone validation raised "
                           f"{type(exc).__name__}: {exc}")
            continue
        for finding in result.findings:
            missing.append(f"[{boundary}] {finding.code} {finding.path}: {finding.message}")

    # phase state shape -- the phase authority, ALL of it.
    #
    # The previous filter kept only codes starting with "E", on the assumption
    # that phase_state_validate speaks in E-codes. It does not: DOC_NOT_OBJECT,
    # DOC_NO_SECTIONS, and the SECTION_* family carry no E prefix, so malformed
    # state walked through the terminal gate because its complaint was worded
    # unexpectedly. Filtering a delegate's findings by a guess at its naming
    # convention is paraphrase by another route -- take the findings it gives.
    psv_findings: list = []
    try:
        psv._validate_doc(state, psv_findings)
    except Exception as exc:  # noqa: BLE001
        missing.append(f"[phase_state] validation raised {type(exc).__name__}: {exc}")
    for finding in psv_findings:
        code = getattr(finding, "code", "") or "<uncoded>"
        missing.append(f"[phase_state] {code}: {getattr(finding, 'message', finding)}")

    # 7 -- revision log, as a Generator round (not as a filename).
    missing.extend(f["message"] for f in check_authorship(project_root))

    # 8 -- deterministic + Check 8 accessibility evidence
    if not (project_root / "reviews" / "findings.json").is_file():
        missing.append("reviews/findings.json absent (deterministic check evidence)")
    missing.extend(_check8_findings(project_root, state))

    # 9, 10, 11 -- convergence signoff rows, the deep pass, and MCR clearance,
    # all from the phase guardrail's clauses f and g.
    missing.extend(_phase_guardrail_findings(project_root, state))
    if not (project_root / "reviews" / "convergence_log.md").is_file():
        missing.append("reviews/convergence_log.md absent (no convergence journal)")

    # 13 -- Reflector-full close-out
    if not list((project_root / "reviews").glob("**/reflector_full*")):
        missing.append("no Reflector-full close-out artefact under reviews/")

    # 14 -- F8 final-round report
    if not list((project_root / "reviews").glob("**/f8_*")):
        missing.append("no F8 final-round report under reviews/")

    # 15 -- terminal state. The FINAL/M5 packet binding is validate_gate's
    # (ph4_terminal_close), so it is not re-decided here.
    if state.get("terminal_phase_reached") is not True:
        missing.append("phase_state.terminal_phase_reached is not true")

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
    a.add_argument("--run-scope", type=str, default=None,
                   help=f"explicit declared scope, one of {SCOPES} (default: {FULL}). "
                        "Never inferred from request text.")
    a.set_defaults(fn=cmd_authorize)

    s = sub.add_parser("scope", help="is this child dispatch legal under its parent?")
    s.add_argument("--parent-scope", required=True)
    s.add_argument("--child-brief", required=True, help="file path, or - for stdin")
    # --allow-undeclared-child is RETIRED, not renamed. It was an opt-out from
    # the primary structural rule, available to the same caller the rule
    # constrains -- a gate whose subject can waive it is not a gate. It is
    # accepted-and-ignored (with a refusal note) so legacy invocations fail
    # loudly on the declaration requirement rather than silently on an
    # unrecognised flag, which would look like a tooling error rather than a
    # verdict.
    s.add_argument("--allow-undeclared-child", action="store_true",
                   help=argparse.SUPPRESS)
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
