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
                                 (read-only readiness; actual Planner dispatch
                                 performs the sole exact-path reservation)
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
import hashlib
import io
import json
import re
import sys
from pathlib import Path, PurePosixPath

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
from draft_evidence_verifier import (              # noqa: E402
    VerifierError,
    validate_lifecycle_verifier_binding,
)
import pre_phase_advance_check as ppa              # noqa: E402
import reader_accessibility_policy as rap          # noqa: E402
import artefact_frontmatter_validate as afv        # noqa: E402
import round_identifier as rid                     # noqa: E402
from milestone_path_contract import canonical_deliverable  # noqa: E402
from audit import schema as audit_schema           # noqa: E402
from assignment_receipt_transaction import (       # noqa: E402
    ReceiptTransactionError, validate_mutation_target,
)


# There is no boundary->milestone map here.
#
# One was kept "for diagnostics" after the applicability skip was removed. A
# second copy of `milestone_framework_validate`'s own target_map, retained with
# no caller, is a fact waiting to drift: the authority adds a boundary, this
# table does not, and the next person to reach for it is told something false by
# a structure that looks maintained. `mfv.GATE_BOUNDARIES` is the sole authority
# for which boundaries exist, and the loop below iterates it directly.

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

OK, REFUSED, ERROR = 0, 4, 2


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

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


# ---------------------------------------------------------------------------
# STRUCTURED UNMET RECORDS
#
# `unmet` was a list of prose strings, so every consumer -- including this
# package's own tests -- had to substring-match to learn WHY a terminal claim
# was refused. That is the defect this workstream keeps finding, turned on our
# own output: a caller matching "MF-GATE-M5" in a sentence is matching a
# FORMAT, and the sentence is free to change. Tests then pass on a message they
# never meant to assert, or fail on a reworded one they did.
#
# `unmet_findings` is additive and structured: source, exact delegate code,
# exact path, message. `unmet` is preserved verbatim for existing consumers --
# removing it would break them to fix ourselves.
#
# Local codes exist where no delegate owns the fact, so that even our own checks
# are matchable by code rather than by prose.
FRC_LOCAL = {
    "findings_json": "FRC-DETERMINISTIC-EVIDENCE-ABSENT",
    "check8_unbound": "FRC-CHECK8-UNBOUND",
    "check8_path": "FRC-CHECK8-PATH-UNRESOLVED",
    "check8_json": "FRC-CHECK8-NOT-CANONICAL-JSON",
    "check8_invalid": "FRC-CHECK8-INVALID",
    "check8_mismatch": "FRC-CHECK8-AGGREGATE-MISMATCH",
    "check8_blocker": "FRC-CHECK8-BLOCKER",
    "check8_type": "FRC-CHECK8-MALFORMED-STATE",
    "convergence_log": "FRC-CONVERGENCE-LOG-ABSENT",
    "reflector": "FRC-REFLECTOR-CLOSEOUT-ABSENT",
    "f8": "FRC-F8-REPORT-ABSENT",
    "terminal_state": "FRC-TERMINAL-STATE-NOT-REACHED",
    "ledger_malformed": "FRC-LEDGER-MALFORMED",
    "sections_empty": "FRC-SECTIONS-EMPTY",
    "authorship": "FRC-AUTHORSHIP",
    "na_milestone": "FRC-NA-MILESTONE-IN-FULL-LIFECYCLE",
    "artefact_absent": "FRC-ARTEFACT-ABSENT",
    "artefact_ambiguous": "FRC-ARTEFACT-AMBIGUOUS",
    "artefact_unreadable": "FRC-ARTEFACT-UNREADABLE",
    "artefact_family": "FRC-ARTEFACT-WRONG-FAMILY",
    "round_unbound": "FRC-TERMINAL-ROUND-UNBOUND",
    "round_mismatch": "FRC-ARTEFACT-ROUND-MISMATCH",
    "raised": "FRC-VALIDATOR-RAISED",
}


def _u(source: str, code: str, path: str, message: str) -> dict:
    """One unmet requirement, attributed to the authority that decided it."""
    return {"source": source, "code": code, "path": path, "message": message}


def _u_line(rec: dict) -> str:
    """The legacy `unmet` prose line, derived from the structured record."""
    where = f" {rec['path']}" if rec["path"] else ""
    return f"[{rec['source']}] {rec['code']}{where}: {rec['message']}"


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
    # Type BEFORE `.get`. A JSON list or scalar is not None, so it walked past
    # the guard above and raised AttributeError -- exit 2, the absence of a
    # verdict, from the function whose job is to produce one.
    if not isinstance(state, dict):
        findings.append(_f(
            "FRC-NO-PROJECT",
            f"reviews/phase_state.json parses to {type(state).__name__}, not an "
            "object; not a native project",
            parsed_type=type(state).__name__))
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


def _find_receipt(
    project_root: Path, target: str, states: tuple[str, ...] = ("ready",)
) -> Path | None:
    """The receipt path is DERIVED from the assignment gate's own contract.

    reviews/.harness/assignment/<state>/gate_receipt_{target}_<utc>.json -- the shape
    `assignment_process_gate._receipt_path_finding` enforces. We do not invent a
    location, and we do not accept one from an argument: newest candidate wins
    and `verify_receipt` decides whether it is actually valid and fresh.
    """
    root = project_root / "reviews" / ".harness" / "assignment"
    if not root.is_dir():
        return None
    cands = sorted(
        path
        for state in states
        for path in (root / state).glob(f"gate_receipt_{target}_*.json")
        if not path.name.endswith(".result.json")
    )
    return cands[-1] if cands else None


def authorize(project_root: Path | None) -> list[dict]:
    """Read-only §2 readiness: floor, active target, and current READY receipt.

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
            "--emit-receipt reviews/.harness/assignment/ready/"
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

    # Deliberately read-only. Actual Planner dispatch performs the one and only
    # READY->RESERVED transition with exact --write-path arguments. Calling the
    # destructive preflight here would consume the dispatch opportunity early.
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
        # REFUSED, not OK. This command answers exactly one question -- "may
        # academic prose be written here?" -- and exit 0 is its way of saying
        # yes. It used to answer an explicitly declared ad hoc review with exit
        # 0 plus a note reading "no prose", which is a contradiction a
        # return-code-only caller cannot see: the note is for humans, the exit
        # code is for machines, and the machine was told to proceed. A gate whose
        # prose and whose exit code disagree is enforcing the prose, i.e.
        # nothing.
        #
        # An ad hoc review remains perfectly legal -- it is simply not a prose
        # authorization. Its legality is validated by the `scope` command, which
        # is the mechanism for checking a dispatch, and which still passes an
        # ad hoc parent with an ad hoc child.
        _emit([_f("FRC-PROSE-FORBIDDEN",
                  "run_scope is adhoc_review: academic prose may not be written, "
                  "the ladder may not advance, no terminal claim may be made, and "
                  "the response is not F7/F8/F9 evidence. This is a refusal, not "
                  "an error: the ad hoc review itself is legal. Validate its "
                  "dispatch with `full_run_contract_check.py scope "
                  "--parent-scope adhoc_review --child-brief <file>`; do not read "
                  "an authorization exit code out of it.",
                  run_scope=ADHOC)], "REFUSED")
        return REFUSED

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
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_ROUND_FIELDS = ("Hypothesis", "Scope", "Changes")


def check_authorship(project_root: Path, *, require_receipt: bool = True) -> list[dict]:
    findings: list[dict] = []
    prose = [
        project_root / canonical_deliverable(target)
        for target in ("M4", "FINAL")
        if (project_root / canonical_deliverable(target)).is_file()
    ]
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

    if not require_receipt:
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
    receipt = _find_receipt(project_root, target, states=("consumed",))
    if receipt is None:
        findings.append(_f(
            "FRC-AUTHORSHIP",
            f"manuscript prose exists and {target} is still outstanding, but no "
            f"assignment gate receipt authorizes a write against {target}. The "
            "round's own log entry is not evidence that the round was permitted "
            "to run: those bytes were written without authorization.",
            files=files, active_target=target))
        return findings
    gate_findings = apg.verify_receipt(
        project_root.resolve(), receipt.resolve(), allow_consumed=True
    )
    if gate_findings:
        findings.extend(_f(
            "FRC-AUTHORSHIP",
            f"the receipt covering the round that wrote this prose is not valid "
            f"for {target}: {code}: {msg}",
            files=files, active_target=target, receipt=str(receipt))
            for code, msg in gate_findings)
        return findings
    result_path = receipt.with_suffix(".result.json")
    try:
        result = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        findings.append(_f(
            "FRC-AUTHORSHIP",
            f"consumed receipt has no valid publication result: {exc}",
            files=files, active_target=target, receipt=str(receipt)))
        return findings
    published = result.get("published") if isinstance(result, dict) else None
    if not isinstance(published, list):
        findings.append(_f(
            "FRC-AUTHORSHIP", "publication result has no published path/hash list",
            files=files, active_target=target, receipt=str(receipt)))
        return findings
    for row in published:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str):
            findings.append(_f("FRC-AUTHORSHIP", "publication result row is invalid", files=files))
            continue
        path = project_root / row["path"]
        if not path.is_file() or row.get("sha256") != _sha256(path):
            findings.append(_f(
                "FRC-AUTHORSHIP", f"published path/hash is missing or stale: {row.get('path')}",
                files=files, active_target=target, receipt=str(receipt)))
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
def _phase_guardrail_findings(project_root: Path, state: dict) -> list[dict]:
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
    out: list[dict] = []

    # --- MCR admission proof + per-section deep pass + signoff continuity ----
    try:
        result = mfv.validate_document(project_root, state, "Ph4")
        for f in result.findings:
            out.append(_u("Ph4", f.code, f.path, f.message))
    except Exception as exc:  # noqa: BLE001
        out.append(_u("Ph4", FRC_LOCAL["raised"], "",
                      f"milestone validation raised {type(exc).__name__}: {exc}"))

    # --- full TerminalSignoffRow validation ---------------------------------
    try:
        ledger = ppa.translate_phase_ledger(state)
    except ppa.LedgerTranslationError as exc:
        # The translator now REFUSES malformed sections, entries and entry logs
        # rather than dropping them. That refusal is a terminal finding, not an
        # error: a ledger whose sections cannot be read is a ledger whose
        # sections cannot be validated.
        return out + [_u("phase_state", FRC_LOCAL["ledger_malformed"],
                         "reviews/phase_state.json", f"malformed ledger: {exc}")]
    except Exception as exc:  # noqa: BLE001
        return out + [_u("clause g", FRC_LOCAL["raised"], "",
                         f"ledger translation raised {type(exc).__name__}: {exc}")]

    sections = ledger.get("sections") or []
    if not sections:
        return out + [_u("phase_state", FRC_LOCAL["sections_empty"],
                         "phase_state.sections",
                         "sections is empty: the convergence signoff cannot be "
                         "attributed to any section")]

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
            out.append(_u("clause g", FRC_LOCAL["raised"], "",
                          f"raised {type(exc).__name__}: {exc}"))
            break
        for f in ctx.findings:
            key = (f.code, f.message)
            if key in seen:
                continue  # the signoff file is shared; each section re-reads it
            seen.add(key)
            out.append(_u(f"clause {f.clause}", f.code, f.section, f.message))
    return out


# Terminal-acceptable Check 8 aggregate. `recompute_check8` yields CLEAN /
# BORDERLINE / MAJOR / BLOCKER; the ladder's floor is "no Check 8 BLOCKER"
# (run-phase-3 SKILL.md, FULL_RUN_CONTRACT.md §4 row 8).
CHECK8_TERMINAL_REFUSED = {"BLOCKER"}


def _check8_findings(project_root: Path, state: dict) -> list[dict]:
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
        return [_u("check8", FRC_LOCAL["check8_type"], "milestone_framework",
                   f"must be an object, got {type(mf).__name__}")]
    milestones = mf.get("milestones")
    if not isinstance(milestones, dict):
        return [_u("check8", FRC_LOCAL["check8_type"],
                   "milestone_framework.milestones",
                   f"must be an object, got {type(milestones).__name__}")]
    bindings = mf.get("policy_bindings")
    binding = bindings.get("reader_accessibility") if isinstance(bindings, dict) else None
    transitions = binding.get("transitions") if isinstance(binding, dict) else None
    if not isinstance(transitions, dict):
        transitions = {}

    bound = []
    for key, rec in milestones.items():
        if not isinstance(rec, dict):
            return [_u("check8", FRC_LOCAL["check8_type"],
                       f"milestone_framework.milestones.{key}",
                       f"must be an object, got {type(rec).__name__}")]
        ev = rec.get("policy_evidence")
        if ev is None:
            continue
        if not isinstance(ev, dict):
            return [_u("check8", FRC_LOCAL["check8_type"],
                       f"milestone_framework.milestones.{key}.policy_evidence",
                       f"must be an object, got {type(ev).__name__}")]
        rel = ev.get("check8_path")
        if rel is None:
            continue
        if not isinstance(rel, str) or not rel.strip():
            return [_u("check8", FRC_LOCAL["check8_type"],
                       f"milestone_framework.milestones.{key}.policy_evidence"
                       ".check8_path",
                       f"must be a non-empty string, got {type(rel).__name__}")]
        bound.append((key, ev))
    if not bound:
        return [_u("check8", FRC_LOCAL["check8_unbound"],
                   "milestone_framework.milestones.*.policy_evidence.check8_path",
                   "no Check 8 evidence is bound in milestone_framework; a file "
                   "merely named *check8* under reviews/ is not the project's "
                   "Check 8 evidence")]

    out: list[dict] = []
    for key, ev in bound:
        rel = ev.get("check8_path")
        path = project_root / rel
        where = f"milestone_framework.milestones.{key}.policy_evidence.check8_path"
        if not path.is_file():
            out.append(_u("check8", FRC_LOCAL["check8_path"], where,
                          f"does not resolve: {rel}"))
            continue
        try:
            sidecar = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            out.append(_u("check8", FRC_LOCAL["check8_json"], where,
                          f"Check 8 evidence is not canonical JSON: {rel}: {exc}"))
            continue
        try:
            rap.validate_check8_evidence(sidecar)
            recomputed = rap.recompute_check8(sidecar, transitions)
        except Exception as exc:  # PolicyError and schema errors  # noqa: BLE001
            out.append(_u("check8", FRC_LOCAL["check8_invalid"], where,
                          f"Check 8 evidence is invalid: {rel}: {exc}"))
            continue
        verdict = recomputed.get("aggregate_verdict")
        if verdict != sidecar.get("aggregate_verdict"):
            out.append(_u("check8", FRC_LOCAL["check8_mismatch"], where,
                          f"recorded aggregate {sidecar.get('aggregate_verdict')!r} "
                          f"!= recomputed {verdict!r}"))
        if verdict in CHECK8_TERMINAL_REFUSED:
            out.append(_u("check8", FRC_LOCAL["check8_blocker"], where,
                          f"recomputed aggregate is {verdict}: a terminal claim is "
                          "refused while a Check 8 BLOCKER stands"))
    return out


# ---------------------------------------------------------------------------
# TERMINAL ARTEFACTS -- discovered by CONTRACT, validated by AUTHORITY.
#
# Four requirements used to be satisfied by `is_file()` / a `glob`, in the same
# file whose own rule forbids exactly that. An empty `findings.json`, an empty
# `convergence_log.md`, and any file matching `reflector_full*` or `f8_*`
# discharged four of the fifteen.
#
# The split of labour, kept deliberately narrow:
#   DISCOVERY + IDENTITY are this file's job. Which path is canonical, and
#   whether the file found there is the artefact we mean, is a question about
#   THIS project -- and `validate_path` cannot answer it: it returns [] for a
#   file with no frontmatter at all, so "no findings" from it means "nothing I
#   recognised", not "valid".
#   VALIDATION is the authority's job, and is never re-derived here.
# ---------------------------------------------------------------------------
def _expected_deliverable(state: dict) -> str | None:
    """The manuscript this project's own ledger says is the deliverable."""
    mf = state.get("milestone_framework")
    milestones = mf.get("milestones") if isinstance(mf, dict) else None
    if not isinstance(milestones, dict):
        return None
    for key in ("M5", "M4"):
        record = milestones.get(key)
        if not isinstance(record, dict):
            continue
        for art in record.get("artifacts") or []:
            if isinstance(art, dict) and art.get("role") in (None, "deliverable") \
                    and isinstance(art.get("path"), str):
                return art["path"]
    return None


def _findings_json_findings(project_root: Path, state: dict) -> list[dict]:
    """Requirement 8 (deterministic half), via audit.schema.validate_report_payload.

    The read-side validator lives in `scripts/audit/schema.py`, beside the
    `FindingsReport` writer it mirrors. Audit-report semantics are that module's
    business; a second module deciding what a valid report is would be the
    duplicate-authority problem this gate exists to stop repeating.
    """
    rel = "reviews/findings.json"
    path = project_root / rel
    if not path.is_file():
        return [_u("deterministic", FRC_LOCAL["findings_json"], rel,
                   "absent: no deterministic-check evidence at the canonical path")]
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return [_u("deterministic", FRC_LOCAL["artefact_unreadable"], rel,
                   f"not canonical JSON: {exc}")]
    expected = _expected_deliverable(state)
    return [_u("audit.schema", code, f"{rel}::{where}", message)
            for code, where, message in
            audit_schema.validate_report_payload(payload, expected_target=expected)]


def _convergence_findings(project_root: Path) -> list[dict]:
    """Requirement 9 (journal half), via ppa.validate_terminal_convergence_log."""
    return [_u("convergence", code, where, message)
            for code, where, message in ppa.validate_terminal_convergence_log(
                project_root / "reviews" / "convergence_log.md")]


def _artefact_family_findings(project_root: Path, *, source: str, rel: str | None,
                              candidates: list[Path], doc_type: str,
                              refused_severities: frozenset[str]) -> list[dict]:
    """Discover exactly one canonical artefact, then hand it to `validate_path`."""
    if not candidates:
        return [_u(source, FRC_LOCAL["artefact_absent"], "reviews/",
                   f"no {doc_type} artefact at its canonical path "
                   f"({rel}): a terminal claim requires the artefact, not a "
                   "plausible substitute elsewhere")]
    if len(candidates) > 1:
        names = sorted(p.name for p in candidates)
        return [_u(source, FRC_LOCAL["artefact_ambiguous"], "reviews/",
                   f"{len(candidates)} candidate {doc_type} artefacts {names}: a "
                   "terminal claim must name ONE, not leave a reader to choose")]
    path = candidates[0]
    where = path.relative_to(project_root).as_posix()

    fm, err = afv.extract_frontmatter(path)
    if err is not None:
        return [_u(source, FRC_LOCAL["artefact_unreadable"], where,
                   f"unparseable frontmatter: {err}")]
    if fm is None:
        # `validate_path` returns [] here -- "nothing I recognised", which a
        # caller must not read as "valid". Identity is ours to assert.
        return [_u(source, FRC_LOCAL["artefact_family"], where,
                   f"no frontmatter block: cannot be a {doc_type}. A file at the "
                   "right path with the right name is not the artefact.")]
    actual = fm.get("document_type")
    if actual != doc_type:
        return [_u(source, FRC_LOCAL["artefact_family"], f"{where}::document_type",
                   f"expected {doc_type!r}, got {actual!r}")]

    out: list[dict] = []
    for f in afv.validate_path(path):
        # `.cls` is this validator's rule identifier (R-Refl-FM-*); it has no
        # `.code`. Read the authority's own attribute rather than the name our
        # other delegates happen to use -- guessing a delegate's field names is
        # how the E-prefix filter silently dropped every phase_state finding.
        if f.severity in refused_severities:
            out.append(_u(source, f.cls, f"{where}::{f.field}", f.message))
    return out


def _f4_findings(project_root: Path) -> list[dict]:
    """Requirement 13: the Reflector-full close-out (F4).

    The canonical path is `reviews/reflection_report.md`
    (references/AGENT_CONTRACTS.md, Reflector "Outputs"). The previous glob was
    `reviews/**/reflector_full*` -- a name this contract never specified, which
    is how a suggestively named file came to satisfy a requirement.
    """
    path = project_root / "reviews" / "reflection_report.md"
    return _artefact_family_findings(
        project_root, source="reflector",
        rel="reviews/reflection_report.md",
        candidates=[path] if path.is_file() else [],
        doc_type="reflector_full_report",
        refused_severities=frozenset({"BLOCKER", "MAJOR"}))


def _f8_findings(project_root: Path, state: dict) -> list[dict]:
    """Requirement 14: the F8 final-round report for the BOUND terminal round.

    A multi-round project legitimately accumulates one F8 per round. The
    previous cut refused any project with two, which rejected every real
    multi-round run: it treated HISTORY as AMBIGUITY. Two reports are not two
    answers -- one is the terminal round and the rest are the record of getting
    there. The gate simply had no way to tell which, so it refused all of them.

    It now reads `phase_state.terminal_round_id` -- state the Planner writes
    atomically with `terminal_phase_reached`, validated by
    `phase_state_validate`. Selection is by IDENTITY, never by lexicographic
    order, mtime, glob order, event order, or notes parsing: every one of those
    answers "which round was terminal?" with a guess, and a guess is what this
    file exists to delete.

    No binding -> fail closed BEFORE any selection is attempted. Not being able
    to tell which round was terminal is a reason to refuse, not a licence to
    pick.
    """
    bound = state.get("terminal_round_id")
    if not rid.is_valid_round_id(bound):
        return [_u("f8", FRC_LOCAL["round_unbound"], "phase_state.terminal_round_id",
                   f"terminal_round_id is {bound!r}: no authoritative terminal "
                   "round, so no F8 can be selected. Selecting one anyway -- "
                   "newest, last, only -- would be the heuristic this binding "
                   "exists to abolish. The Planner writes this atomically with "
                   "terminal_phase_reached at terminal close.")]

    reviews = project_root / "reviews"
    canonical = reviews / f"final_round_report_{bound}.md"
    rel = f"reviews/final_round_report_{bound}.md"

    # Any OTHER file whose frontmatter claims the bound round is ambiguity: two
    # documents asserting the same round is two answers to one question.
    # Reports for other rounds are history and are ignored entirely.
    rival: list[str] = []
    if reviews.is_dir():
        for cand in sorted(reviews.glob("final_round_report_*.md")):
            if cand == canonical:
                continue
            fm, err = afv.extract_frontmatter(cand)
            if err is not None or not isinstance(fm, dict):
                continue
            if fm.get("round_id") == bound:
                rival.append(cand.name)
    if rival:
        return [_u("f8", FRC_LOCAL["artefact_ambiguous"], "reviews/",
                   f"{len(rival) + 1} reports claim the terminal round {bound}: "
                   f"{sorted([canonical.name] + rival)}. A terminal claim must "
                   "name ONE report; two documents asserting the same round is "
                   "two answers to one question.")]

    if not canonical.is_file():
        return [_u("f8", FRC_LOCAL["artefact_absent"], rel,
                   f"no final-round report for the bound terminal round {bound}. "
                   "Reports for other rounds are history and cannot substitute "
                   "for the one this claim is about.")]

    findings = _artefact_family_findings(
        project_root, source="f8", rel=rel, candidates=[canonical],
        doc_type="final_round_report",
        refused_severities=frozenset({"BLOCKER", "MAJOR"}))
    if findings:
        return findings

    # Filename identity is not enough: the document must claim the bound round
    # itself. A correctly named file whose frontmatter names another round is
    # either a copy or a mistake, and both are refusals.
    fm, _ = afv.extract_frontmatter(canonical)
    claimed = (fm or {}).get("round_id")
    if claimed != bound:
        return [_u("f8", FRC_LOCAL["round_mismatch"], f"{rel}::round_id",
                   f"report claims round_id {claimed!r} but the terminal round is "
                   f"{bound!r}: the filename agrees with the binding and the "
                   "document does not.")]
    if (fm or {}).get("evidence_status") != "complete":
        return [_u("f8", FRC_LOCAL["artefact_family"], f"{rel}::evidence_status",
                   "terminal close requires a complete F8 evidence synthesis; partial or incomplete reports remain non-terminal")]
    return []


def _f7_findings(project_root: Path, state: dict) -> list[dict]:
    """Requirement 6: at least one complete, event-indexed F7 for the terminal round."""
    round_id = state.get("terminal_round_id")
    events_path = project_root / "reviews" / ".harness" / "events.jsonl"
    if not isinstance(round_id, str) or not events_path.is_file():
        return [_u("f7", FRC_LOCAL["artefact_absent"], "reviews/.harness/events.jsonl",
                   "terminal round has no append-only F7 event index")]
    rows: list[dict] = []
    try:
        for number, line in enumerate(events_path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if isinstance(row, dict) and row.get("round_id") == round_id and row.get("event") == "evidence_packet_written":
                rows.append(row)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [_u("f7", FRC_LOCAL["artefact_unreadable"], "reviews/.harness/events.jsonl", f"invalid F7 event index: {exc}")]
    complete_paths: set[str] = set()
    findings: list[dict] = []
    for index, row in enumerate(rows):
        rel = row.get("path")
        event_id = row.get("event_id")
        if not isinstance(rel, str) or rel != f"reviews/.harness/evidence/{event_id}.json":
            findings.append(_u("f7", FRC_LOCAL["artefact_family"], f"reviews/.harness/events.jsonl[{index}]", "F7 event path must derive exactly from its event_id"))
            continue
        path = project_root / Path(*PurePosixPath(rel).parts)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            findings.append(_u("f7", FRC_LOCAL["artefact_unreadable"], rel, f"invalid F7 packet: {exc}")); continue
        if not isinstance(payload, dict):
            findings.append(_u("f7", FRC_LOCAL["artefact_unreadable"], rel, "F7 packet is not a JSON object")); continue
        for finding in afv.validate_path(path):
            if finding.severity in {"BLOCKER", "MAJOR"}:
                findings.append(_u("f7", finding.cls, f"{rel}::{finding.field}", finding.message))
        if payload.get("round_id") != round_id or payload.get("event_id") != event_id:
            findings.append(_u("f7", FRC_LOCAL["round_mismatch"], rel, "F7 packet identity disagrees with its event row"))
        elif payload.get("evidence_status") == "complete":
            complete_paths.add(rel)
    if not rows or not complete_paths:
        findings.append(_u("f7", FRC_LOCAL["artefact_absent"], "reviews/.harness/evidence/", "terminal round requires at least one complete F7 packet recorded in events.jsonl"))
    framework = state.get("milestone_framework") if isinstance(state, dict) else None
    milestones = framework.get("milestones") if isinstance(framework, dict) else None
    m5 = milestones.get("M5") if isinstance(milestones, dict) else None
    policy = m5.get("policy_evidence") if isinstance(m5, dict) else None
    bindings = policy.get("bindings") if isinstance(policy, dict) else None
    bound_f7 = [row.get("path") for row in bindings if isinstance(row, dict) and row.get("role") == "f7_evidence"] if isinstance(bindings, list) else []
    if len(bound_f7) != 1 or bound_f7[0] not in complete_paths:
        findings.append(_u("f7", "FRC-TERMINAL-EVIDENCE-BINDING", "milestone_framework.milestones.M5.policy_evidence.bindings", "the unique f7_evidence binding must name a complete terminal-round packet indexed by events.jsonl"))
    return findings


def _final_publication_findings(project_root: Path, state: dict) -> list[dict]:
    """Require immutable evidence of a consumed public FINAL publication."""
    milestones = ((state.get("milestone_framework") or {}).get("milestones")
                  if isinstance(state.get("milestone_framework"), dict) else None)
    m5 = milestones.get("M5") if isinstance(milestones, dict) else None
    artifacts = m5.get("artifacts") if isinstance(m5, dict) else None
    by_kind = {
        row.get("artifact_kind"): row for row in artifacts
        if isinstance(row, dict) and row.get("role") == "evidence"
    } if isinstance(artifacts, list) else {}
    receipt_art = by_kind.get("consumed_final_receipt")
    result_art = by_kind.get("final_publication_result")
    if not isinstance(receipt_art, dict) or not isinstance(result_art, dict):
        return [_u("authorship", "FRC-FINAL-PUBLICATION-ABSENT", "milestone_framework.milestones.M5.artifacts",
                   "accepted M5 must bind the consumed FINAL receipt and its publication result")]
    try:
        receipt_rel = PurePosixPath(receipt_art["path"])
        result_rel = PurePosixPath(result_art["path"])
        if receipt_rel.parts[:4] != ("reviews", ".harness", "assignment", "consumed"):
            raise ValueError("FINAL receipt evidence is not in the consumed assignment scope")
        if result_rel != receipt_rel.with_suffix(".result.json"):
            raise ValueError("FINAL result evidence is not the consumed receipt's result sidecar")
        receipt_path = project_root / Path(*receipt_rel.parts)
        result_path = project_root / Path(*result_rel.parts)
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        result = json.loads(result_path.read_text(encoding="utf-8"))
    except (KeyError, OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        return [_u("authorship", "FRC-FINAL-PUBLICATION-INVALID", "milestone_framework.milestones.M5.artifacts", f"cannot read bound FINAL publication evidence: {exc}")]
    deliverable = next((row for row in artifacts if isinstance(row, dict) and row.get("role") == "deliverable"), None)
    export = next((row for row in artifacts if isinstance(row, dict) and row.get("role") == "export"), None)
    published = result.get("published") if isinstance(result, dict) else None
    published_map = {row.get("path"): row.get("sha256") for row in published if isinstance(row, dict)} if isinstance(published, list) else {}
    valid = (
        isinstance(receipt, dict) and receipt.get("target_milestone") == "FINAL"
        and receipt.get("stage") == "final" and receipt.get("authorized_role") == "generator"
        and receipt.get("primary_deliverable_path") == (deliverable or {}).get("path")
        and isinstance(result, dict) and result.get("outcome") == "published"
        and result.get("receipt_id") == receipt.get("receipt_id")
        and result.get("reservation_id") == receipt.get("reservation_id")
        and published_map.get((deliverable or {}).get("path")) == (deliverable or {}).get("sha256")
        and published_map.get((export or {}).get("path")) == (export or {}).get("sha256")
        and (export or {}).get("source_sha256") == (deliverable or {}).get("sha256")
    )
    if not valid:
        return [_u("authorship", "FRC-FINAL-PUBLICATION-INVALID", "milestone_framework.milestones.M5.artifacts", "bound receipt/result do not prove one exact Generator FINAL manuscript and released export")]
    for artifact in (deliverable, export):
        try:
            mutation = validate_mutation_target(project_root, artifact["path"])
        except (ReceiptTransactionError, KeyError) as exc:
            code = exc.code if isinstance(exc, ReceiptTransactionError) else "APG-MUTATION-AUTHORITY-MISSING"
            message = exc.message if isinstance(exc, ReceiptTransactionError) else str(exc)
            return [_u("authorship", code, "reviews/.harness/assignment/mutation_ledger.jsonl", message)]
        result_row = next(row for row in published if isinstance(row, dict)
                          and row.get("path") == artifact["path"])
        if result_row.get("mutation_row_sha256") != mutation.get("row_sha256"):
            return [_u("authorship", "FRC-FINAL-MUTATION-BINDING", artifact["path"],
                       "FINAL publication result does not bind the sanctioned mutation row")]
    return []


def _structured_terminal_signoff_findings(project_root: Path, state: dict) -> list[dict]:
    """Bind G.4 and ship approval to the exact terminal manuscript and round."""
    framework = state.get("milestone_framework") if isinstance(state, dict) else None
    milestones = framework.get("milestones") if isinstance(framework, dict) else None
    m5 = milestones.get("M5") if isinstance(milestones, dict) else None
    artifacts = m5.get("artifacts") if isinstance(m5, dict) else None
    deliverable = next((row for row in artifacts if isinstance(row, dict) and row.get("role") == "deliverable"), None) if isinstance(artifacts, list) else None
    raw_policy = m5.get("policy_evidence") if isinstance(m5, dict) else None
    policy = raw_policy if isinstance(raw_policy, dict) else {}
    expected_common = {
        "manuscript_path": (deliverable or {}).get("path"),
        "manuscript_sha256": (deliverable or {}).get("sha256"),
        "round_id": state.get("terminal_round_id"),
    }
    specs = {
        "reviews/G4_signoff.md": {
            **expected_common, "authority": "evaluator",
            "check8_sha256": policy.get("check8_sha256"),
            "safeguard_status": "CLEAN",
        },
        "reviews/ph4_ship_signoff.md": {
            **expected_common, "authority": "user",
        },
    }
    findings: list[dict] = []
    terminal_bindings = policy.get("bindings")
    required_roles = {"g4_signoff", "ship_signoff", "final_round_report", "reflector_full", "f7_evidence", "events_log", "findings", "convergence_log"}
    observed_roles = {row.get("role") for row in terminal_bindings if isinstance(row, dict)} if isinstance(terminal_bindings, list) else set()
    if (
        policy.get("terminal_round_id") != state.get("terminal_round_id")
        or policy.get("cycle_id") != state.get("terminal_round_id")
        or observed_roles != required_roles
        or not isinstance(terminal_bindings, list)
        or len(terminal_bindings) != len(required_roles)
    ):
        findings.append(_u(
            "signoff", "FRC-TERMINAL-EVIDENCE-BINDING", "milestone_framework.milestones.M5.policy_evidence",
            "terminal M5 policy must bind its cycle and complete closure-evidence role set to terminal_round_id",
        ))
    elif isinstance(terminal_bindings, list):
        for index, row in enumerate(terminal_bindings):
            try:
                bound = project_root / Path(*PurePosixPath(row["path"]).parts)
                current = _sha256(bound)
            except (KeyError, OSError, TypeError, ValueError) as exc:
                findings.append(_u("signoff", "FRC-TERMINAL-EVIDENCE-BINDING", f"milestone_framework.milestones.M5.policy_evidence.bindings[{index}]", f"cannot read terminal evidence binding: {exc}")); continue
            if current != row.get("sha256"):
                findings.append(_u("signoff", "FRC-TERMINAL-EVIDENCE-BINDING", f"milestone_framework.milestones.M5.policy_evidence.bindings[{index}]", "terminal evidence hash is stale"))
    for relative, expected in specs.items():
        path = project_root / relative
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError) as exc:
            findings.append(_u("signoff", FRC_LOCAL["artefact_unreadable"], relative, f"cannot read terminal signoff: {exc}")); continue
        fields: dict[str, list[str]] = {}
        for line in lines:
            match = re.fullmatch(r"\s*([a-z0-9_]+)\s*:\s*(.*?)\s*", line, re.IGNORECASE)
            if match:
                fields.setdefault(match.group(1).lower(), []).append(match.group(2))
        for key, value in expected.items():
            observed = fields.get(key, [])
            if len(observed) != 1 or observed[0] != value:
                findings.append(_u(
                    "signoff", "FRC-TERMINAL-SIGNOFF-BINDING", f"{relative}::{key}",
                    f"terminal signoff must bind {key} exactly once to {value!r}; observed {observed!r}",
                ))
    return findings


def check_terminal(project_root: Path, state_override: dict | None = None) -> list[dict]:
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

    if state_override is None:
        state, _ = _load_json(project_root / "reviews" / "phase_state.json")
        state = state or {}
    else:
        state = state_override

    unmet: list[dict] = []

    # 2-6, 12 -- the milestone authority, EVERY boundary, unconditionally.
    # `mfv.GATE_BOUNDARIES` is iterated directly: it is the sole authority for
    # which boundaries exist. A full_lifecycle terminal claim may not skip M4 or
    # M5 on an applicability declaration; see the note at the top of this file.
    for boundary in mfv.GATE_BOUNDARIES:
        try:
            result = mfv.validate_gate(project_root, state, boundary)
        except Exception as exc:  # noqa: BLE001
            unmet.append(_u(boundary, FRC_LOCAL["raised"], "",
                            f"milestone validation raised {type(exc).__name__}: {exc}"))
            continue
        for finding in result.findings:
            unmet.append(_u(boundary, finding.code, finding.path, finding.message))

    # DIRECT refusal of any N/A milestone. Running every boundary is NOT enough:
    # the delegated validator legitimately SKIPS `not_applicable` records -- that
    # is correct for the milestone-local question it answers ("is this waiver
    # itself in order?"), and it means a waived milestone produces no finding at
    # all. Relying on the delegate's silence to refuse a terminal claim is
    # relying on an authority to answer a question nobody asked it. So the
    # terminal rule is stated here, where the terminal question is being asked.
    milestones = ((state.get("milestone_framework") or {}).get("milestones")
                  if isinstance(state.get("milestone_framework"), dict) else None)
    if isinstance(milestones, dict):
        for key in ("M1", "M2", "M3", "M4", "M5"):
            record = milestones.get(key)
            if isinstance(record, dict) and \
                    record.get("applicability") == "not_applicable":
                unmet.append(_u(
                    "full_lifecycle", FRC_LOCAL["na_milestone"],
                    f"milestone_framework.milestones.{key}.applicability",
                    f"{key} is authorized not_applicable. That waiver is legal for "
                    "milestone-local and ad hoc validation, and it cannot satisfy a "
                    "full_lifecycle terminal claim: the user asked for the whole "
                    "ladder, so every milestone is required because they asked. A "
                    "waiver that turns 'ladder complete' from false to true is not "
                    "applicability -- it is the failure this contract exists to "
                    "prevent, in the vocabulary of a feature."))

        # Every terminal deliverable must retain the same committed verifier
        # transactions accepted by the milestone transaction kernel.
        for key in ("M1", "M2", "M3", "M4", "M5"):
            record = milestones.get(key)
            if not isinstance(record, dict):
                continue
            deliverables = [
                row for row in record.get("artifacts", [])
                if isinstance(row, dict) and row.get("role") == "deliverable"
            ]
            if len(deliverables) != 1:
                continue
            artifact_binding = deliverables[0]
            try:
                artifact_path = (project_root / artifact_binding["path"]).resolve(strict=True)
                artifact_path.relative_to(project_root.resolve())
                if not artifact_path.is_file() or _sha256(artifact_path) != artifact_binding.get("sha256"):
                    raise ValueError("stale artifact binding")
            except (KeyError, OSError, TypeError, ValueError) as exc:
                unmet.append(_u(
                    "full_lifecycle", "FRC-DRAFT-POLICY-STALE",
                    f"milestone_framework.milestones.{key}.artifacts",
                    f"accepted deliverable binding is stale: {exc}",
                ))
                continue
            policy = record.get("policy_evidence")
            for field, phase, disposition in (
                ("draft_generation", "generation", "evaluation_ready"),
                ("draft_evaluation", "evaluation", "product_qualified"),
            ):
                binding = policy.get(field) if isinstance(policy, dict) else None
                where = f"milestone_framework.milestones.{key}.policy_evidence.{field}"
                if not isinstance(binding, dict):
                    unmet.append(_u("full_lifecycle", "FRC-DRAFT-POLICY-MISSING", where,
                                    "accepted deliverable lacks current-byte generation or independent evaluation evidence"))
                    continue
                raw_path = binding.get("evidence_path")
                try:
                    evidence_path = (project_root / raw_path).resolve(strict=True)
                    evidence_path.relative_to(project_root.resolve())
                    if not evidence_path.is_file() or binding.get("evidence_sha256") != _sha256(evidence_path):
                        raise ValueError("stale binding")
                except (OSError, TypeError, ValueError) as exc:
                    unmet.append(_u("full_lifecycle", "FRC-DRAFT-POLICY-STALE", where,
                                    f"draft-policy evidence is unreadable, outside the project, or hash-stale: {exc}"))
                    continue
                try:
                    locator_probe = json.loads(evidence_path.read_text(encoding="utf-8"))
                    target = locator_probe.get("target")
                    if not isinstance(target, str) or not target:
                        raise ValueError("locator target is absent")
                    lifecycle_artifact = (
                        project_root / Path(*PurePosixPath(target).parts)
                    ).resolve(strict=True)
                    lifecycle_artifact.relative_to(project_root.resolve())
                    if (
                        not lifecycle_artifact.is_file()
                        or _sha256(lifecycle_artifact) != artifact_binding.get("sha256")
                    ):
                        raise ValueError(
                            "locator target differs from accepted deliverable bytes"
                        )
                    result = validate_lifecycle_verifier_binding(
                        locator=evidence_path,
                        artifact=lifecycle_artifact,
                        project_root=project_root,
                        harness_root=ROOT,
                        expected_phase=phase,
                        expected_disposition=disposition,
                    )
                    if result["locator"].get("target") != target:
                        raise VerifierError(
                            "LIFECYCLE-EVIDENCE-CLAIM", "locator target differs"
                        )
                except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
                    unmet.append(_u(
                        "full_lifecycle", "FRC-DRAFT-POLICY-STALE", where,
                        f"lifecycle target is unreadable, outside the project, or byte-stale: {exc}",
                    ))
                except VerifierError as exc:
                    code = "FRC-DRAFT-POLICY-STALE" if exc.code in {
                        "LIFECYCLE-EVIDENCE-STALE", "EVIDENCE-TOCTOU",
                        "VERIFIER-TRANSACTION-INCOMPLETE",
                    } else "FRC-DRAFT-POLICY-INVALID"
                    unmet.append(_u(
                        "full_lifecycle", code, where,
                        f"{exc.code}: {exc.message}",
                    ))

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
        unmet.append(_u("phase_state", FRC_LOCAL["raised"], "",
                        f"validation raised {type(exc).__name__}: {exc}"))
    for finding in psv_findings:
        code = getattr(finding, "code", "") or "<uncoded>"
        unmet.append(_u("phase_state", code, getattr(finding, "path", "") or "",
                        str(getattr(finding, "message", finding))))

    # 7 -- revision log, as a Generator round (not as a filename).
    # Candidate close changes phase_state by design, so the consumed receipt's
    # pre-state hash is necessarily stale against the in-memory post-state.
    # Historical FINAL receipt/result proof is checked below from immutable M5
    # artifacts. Candidate validation still enforces the state-independent
    # revision-log half; only the necessarily stale live-receipt half is skipped.
    for f in check_authorship(project_root, require_receipt=state_override is None):
        unmet.append(_u("authorship", f["code"], "manuscript/revision_log.md",
                        f["message"]))
    unmet.extend(_final_publication_findings(project_root, state))
    unmet.extend(_structured_terminal_signoff_findings(project_root, state))

    # 8 -- deterministic + Check 8 accessibility evidence
    unmet.extend(_findings_json_findings(project_root, state))
    unmet.extend(_check8_findings(project_root, state))

    # 9, 10, 11 -- convergence signoff rows, the deep pass, and MCR clearance,
    # all from the phase guardrail's clauses f and g.
    unmet.extend(_phase_guardrail_findings(project_root, state))
    unmet.extend(_convergence_findings(project_root))

    # 13 -- Reflector-full close-out (F4)
    unmet.extend(_f4_findings(project_root))

    # 14 -- F8 final-round report
    unmet.extend(_f7_findings(project_root, state))
    unmet.extend(_f8_findings(project_root, state))

    # 15 -- terminal state. The FINAL/M5 packet binding is validate_gate's
    # (ph4_terminal_close), so it is not re-decided here.
    if state.get("terminal_phase_reached") is not True:
        unmet.append(_u("phase_state", FRC_LOCAL["terminal_state"],
                        "phase_state.terminal_phase_reached", "is not true"))

    if unmet:
        findings.append(_f(
            "FRC-TERMINAL-UNPROVEN",
            f"{len(unmet)} of the FULL_RUN_CONTRACT §4 requirements are unmet; a "
            "terminal claim (\"Ph4\", \"G.4\", \"terminal PASS\", \"ladder complete\", "
            "\"converged\", \"shipped\") is refused.",
            # `unmet` stays exactly as it was -- prose lines, same shape, same
            # order -- because existing consumers read it and breaking them to
            # improve ourselves is not an improvement. `unmet_findings` is
            # ADDITIVE: the same facts, structured, so a caller can match an
            # exact code and path instead of grepping a sentence that is free to
            # be reworded. The prose is derived FROM the records, so the two
            # cannot drift apart.
            unmet=[_u_line(rec) for rec in unmet],
            unmet_findings=unmet))
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
    # NOT required, deliberately. §1.1 resolves an omitted top-level scope to
    # full_lifecycle, and only `adhoc_review` must be declared explicitly. That
    # is a SAFE DEFAULT, not phrase sniffing: the two are opposites. Sniffing
    # reads the request text to guess what the user meant, and guesses wrong in
    # the permissive direction. This default reads nothing at all, and resolves
    # ambiguity toward the STRICTER path -- guessing full_lifecycle costs one
    # bootstrap prompt the user can decline, while guessing adhoc_review
    # silently skips the entire lifecycle, which is the 2026-07-17 audit.
    # Making the flag mandatory would make the strict path the one you have to
    # remember to ask for.
    a.add_argument("--run-scope", type=str, default=None,
                   help=f"declared scope, one of {SCOPES}. Omitted resolves to "
                        f"{FULL} (§1.1: only adhoc_review must be explicit). "
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
