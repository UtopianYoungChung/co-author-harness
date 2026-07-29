#!/usr/bin/env python3
"""full_run_contract_smoketest - adversarial cases for FULL_RUN_CONTRACT.md.

The regression fixture is the REAL failure (audit 2026-07-17, session
local_7fe69519…): a "Harness full run" request that produced a complete essay
with no project, told its Evaluator "no artifacts, response only", and reported
"Ladder complete … PASS". The dispatch strings below are the observed ones,
minimised and de-identified; nothing here is reconstructed from the failed
session's own summary of itself.

Every case asserts the MECHANISM, not a message: the exit code and the finding
CODE. A gate that refuses for the wrong reason is not a gate.

Run:  python scripts/full_run_contract_smoketest.py
Exit: 0 all pass; 1 a case failed.
"""

from __future__ import annotations

import hashlib
import io
import json
import subprocess
import sys
import tempfile
from semantic_graph_fixture_support import semantic_graph_fixture_environment
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "full_run_contract_check.py"
FAILURES: list[str] = []

# --- observed dispatch strings (audit :112 / :185 / :278), minimised ---------
OBSERVED_LIGHTWEIGHT_DISPATCH = (
    "Run a Ph3 Evaluator pass, check_profile=refine, on this manuscript. "
    "This is a LIGHTWEIGHT run - no project scaffold, no phase_state.json. "
    "Do NOT attempt to write reviews/ artifacts or bootstrap state. "
    "Return findings in your response only."
)
OBSERVED_TERMINAL_CLAIM = (
    "Ladder complete - Ph1 draft -> Ph3 evaluator + revision -> Ph4 grounding "
    "audit, PASS on re-audit."
)


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{(' - ' + detail) if detail else ''}")
    if not ok:
        FAILURES.append(name)


def run(*args: str, stdin: str | None = None) -> tuple[int, dict | None, str]:
    r = subprocess.run([sys.executable, str(GATE), *args], input=stdin,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=300)
    try:
        payload = json.loads(r.stdout)
    except (json.JSONDecodeError, ValueError):
        payload = None
    return r.returncode, payload, r.stdout + r.stderr


def codes(payload: dict | None) -> set[str]:
    if not payload:
        return set()
    return {f.get("code") for f in payload.get("findings", [])}


# --------------------------------------------------------------------------
def case_full_run_intent_recognised() -> None:
    """The advisory recogniser suggests full_lifecycle for the observed request.

    This is a HINT layer, not the mechanism (see case_intent_is_advisory_only
    and case_scope_is_structural_not_phrasal, which pin the actual floor). It
    is still worth a test: the suggestion is what a human or agent reads when
    deciding what to declare, and it must not steer toward ad hoc.
    """
    rc, p, _ = run("intent", "--text",
                   "Harness full run: referring to the LLM wiki, draft me a short "
                   "essay (soft 2000-word limit) on Actor vs. Agency or Actor and Agency.")
    check("observed request suggests full_lifecycle",
          rc == 0 and p and p.get("suggested_run_scope") == "full_lifecycle", str(p)[:70])
    for phrase in ("full harness run", "draft the whole paper", "write me an essay",
                   "run the ladder", "ship this"):
        rc, p, _ = run("intent", "--text", phrase)
        check(f"'{phrase}' -> suggests full_lifecycle",
              p and p.get("suggested_run_scope") == "full_lifecycle")
    # Ambiguity must lean TOWARD the lifecycle (§1.1): guessing adhoc silently
    # skips it; guessing full costs one declinable prompt.
    rc, p, _ = run("intent", "--text", "can you help me with this document")
    check("ambiguous prose intent suggests full_lifecycle",
          p and p.get("suggested_run_scope") == "full_lifecycle")


def case_missing_scaffold_blocks_before_prose() -> None:
    """Required: full-run intent + missing scaffold blocks BEFORE prose."""
    with tempfile.TemporaryDirectory() as td:
        nothing = Path(td) / "no-such-project"
        rc, p, out = run("authorize", "--project-root", str(nothing))
        check("no project -> REFUSED", rc == 4, f"rc={rc}")
        check("no project -> FRC-NO-PROJECT", "FRC-NO-PROJECT" in codes(p))
        check("refusal names the bootstrap command",
              "native_project_bootstrap.py" in out)
        check("refusal forbids the checklist substitute",
              "task checklist" in out)


def case_bootstrapped_but_no_contract_blocks() -> None:
    """A scaffold alone does not authorize prose: the contract must resolve."""
    with tempfile.TemporaryDirectory() as td:
        proj = Path(td) / "p"
        (proj / "reviews").mkdir(parents=True)
        (proj / "reviews" / "phase_state.json").write_text(json.dumps({
            "milestone_framework": {"mode": "native", "milestones": {}}}), encoding="utf-8")
        rc, p, _ = run("authorize", "--project-root", str(proj))
        check("native project without contract -> REFUSED", rc == 4, f"rc={rc}")
        check("-> FRC-CONTRACT-MISSING", "FRC-CONTRACT-MISSING" in codes(p))


def case_lightweight_child_blocks() -> None:
    """Required: full-run intent + lightweight child dispatch blocks.

    The input is the OBSERVED dispatch from audit :112.
    """
    rc, p, _ = run("scope", "--parent-scope", "full_lifecycle", "--child-brief", "-",
                   stdin=OBSERVED_LIGHTWEIGHT_DISPATCH)
    check("observed :112 dispatch -> REFUSED", rc == 4, f"rc={rc}")
    check("-> FRC-SCOPE-DOWNGRADE", "FRC-SCOPE-DOWNGRADE" in codes(p))
    joined = json.dumps(p)
    check("names the offending instructions", "markers" in joined, joined[:60])

    # A legitimate full-lifecycle dispatch, WITH its declaration, must pass.
    rc, p, _ = run("scope", "--parent-scope", "full_lifecycle", "--child-brief", "-",
                   stdin="run_scope: full_lifecycle\n"
                         "Run a Ph3 Evaluator pass, check_profile=refine, on "
                         "milestones/M4_complete_paper_draft.md. Write F7 evidence packets and update "
                         "reviews/ as usual. assignment_gate_receipt: reviews/r.json")
    check("legitimate declared full-lifecycle dispatch passes", rc == 0, f"rc={rc}")

    # An undeclared parent scope is itself a refusal.
    rc, p, _ = run("scope", "--parent-scope", "unset", "--child-brief", "-",
                   stdin="run_scope: full_lifecycle\nanything")
    check("undeclared parent scope -> FRC-SCOPE-UNDECLARED",
          rc == 4 and "FRC-SCOPE-UNDECLARED" in codes(p))


def case_scope_is_structural_not_phrasal() -> None:
    """The mechanism is the DECLARATION, not a phrase list.

    This is the generalisation that matters: the next failure will not be
    worded like the last one. A child that narrows the run is refused on its
    declared scope alone -- with no lightweight/response-only wording anywhere
    in the brief -- and a child that declares nothing is refused rather than
    guessed at.
    """
    # Narrowing declared structurally, in prose nobody anticipated.
    rc, p, _ = run("scope", "--parent-scope", "full_lifecycle", "--child-brief", "-",
                   stdin="run_scope: adhoc_review\n"
                         "Please cast an eye over the argument and tell me what you "
                         "reckon; keep it brief and informal.")
    check("declared narrowing refused with NO downgrade phrasing present",
          rc == 4 and "FRC-SCOPE-DOWNGRADE" in codes(p), f"rc={rc}")
    fs = [f for f in (p or {}).get("findings", [])
          if f.get("code") == "FRC-SCOPE-DOWNGRADE"]
    check("refusal cites the declared scopes, not a phrase",
          bool(fs) and fs[0].get("child_scope") == "adhoc_review"
          and fs[0].get("parent_scope") == "full_lifecycle", str(fs[:1])[:80])

    # No declaration at all -> refused, not inferred.
    rc, p, _ = run("scope", "--parent-scope", "full_lifecycle", "--child-brief", "-",
                   stdin="Have a look at section 3 and report back.")
    check("undeclared child scope -> FRC-SCOPE-UNDECLARED",
          rc == 4 and "FRC-SCOPE-UNDECLARED" in codes(p), f"rc={rc}")

    # Legacy escape hatch still applies the marker net.
    rc, p, _ = run("scope", "--parent-scope", "full_lifecycle", "--child-brief", "-",
                   "--allow-undeclared-child",
                   stdin="Return findings in your response only.")
    check("legacy undeclared brief still caught by the marker net",
          rc == 4 and "FRC-SCOPE-DOWNGRADE" in codes(p), f"rc={rc}")


def case_three_scope_contract_matrix() -> None:
    """C1 red boundary for the exact three-scope authority lattice."""
    exact = {
        "adhoc_review": "run_scope: adhoc_review\nReturn findings only.\n",
        "lab_iteration": "run_scope: lab_iteration\nProduce a proposal in private staging only.\n",
        "full_lifecycle": (
            "run_scope: full_lifecycle\nRun the governed lifecycle and write its "
            "required evidence. assignment_gate_receipt: reviews/r.json\n"
        ),
    }
    for scope, brief in exact.items():
        rc, p, _ = run(
            "scope", "--parent-scope", scope, "--child-brief", "-", stdin=brief,
        )
        if scope == "lab_iteration":
            check(
                "exact lab child inherits lab scope with proposal-only result",
                rc == 0
                and p is not None
                and p.get("status") == "PROPOSAL_ONLY"
                and "FRC-LAB-PROPOSAL-ONLY" in codes(p),
                f"rc={rc} payload={p}",
            )
        else:
            check(f"exact {scope} child inherits its scope", rc == 0, f"rc={rc}")

    transitions = (
        ("lab_iteration", exact["adhoc_review"], "FRC-SCOPE-DOWNGRADE"),
        ("lab_iteration", exact["full_lifecycle"], "FRC-SCOPE-ESCALATION"),
        ("full_lifecycle", exact["lab_iteration"], "FRC-SCOPE-DOWNGRADE"),
        ("adhoc_review", exact["lab_iteration"], "FRC-SCOPE-ESCALATION"),
    )
    for parent, brief, expected in transitions:
        rc, p, _ = run(
            "scope", "--parent-scope", parent, "--child-brief", "-", stdin=brief,
        )
        check(
            f"{parent} transition emits {expected}",
            rc == 4 and expected in codes(p),
            f"rc={rc} payload={p}",
        )

    rc, p, _ = run(
        "scope", "--parent-scope", "lab_iteration", "--child-brief", "-",
        stdin="proposal_only: true\n",
    )
    omission = next(
        (f for f in (p or {}).get("findings", [])
         if f.get("code") == "FRC-SCOPE-UNDECLARED"),
        {},
    )
    omission_message = str(omission.get("message", "")).casefold()
    check(
        "lab child omission is diagnosed as child omission, not unknown parent",
        rc == 4 and "child" in omission_message and "run_scope" in omission_message,
        f"rc={rc} finding={omission}",
    )

    rc, p, _ = run(
        "scope", "--parent-scope", "lab_iteration", "--child-brief", "-",
        stdin="run_scope: lab_iteration\nterminal_claim: shipped\n",
    )
    check(
        "lab child terminal language is specifically refused",
        rc == 4 and "FRC-LAB-TERMINAL-FORBIDDEN" in codes(p),
        f"rc={rc} payload={p}",
    )


def case_intent_is_advisory_only() -> None:
    """`intent` must not be able to authorize anything."""
    rc, p, _ = run("intent", "--text", "just review this quickly, no artifacts")
    check("intent always exits 0 (cannot refuse)", rc == 0, f"rc={rc}")
    check("intent marks itself advisory", p and p.get("advisory") is True)
    check("intent yields a SUGGESTION, not a scope grant",
          p and "suggested_run_scope" in p and "run_scope" not in p)
    # The permission path must ignore phrasing entirely: an unanticipated ad hoc
    # wording cannot authorize an ad hoc path without an explicit declaration.
    rc, p, _ = run("authorize", "--project-root", "/definitely/not/here")
    check("authorize defaults to full_lifecycle and REFUSES without a project",
          rc == 4 and "FRC-NO-PROJECT" in codes(p), f"rc={rc}")
    rc, p, out = run("authorize", "--project-root", "/definitely/not/here",
                     "--run-scope", "adhoc_review")
    # An explicit ad hoc declaration is REFUSED by `authorize`, and that is the
    # point: this command answers "may academic prose be written here?", so an
    # ad hoc review -- which may not write prose -- must not receive exit 0.
    # The old assertion pinned rc == 0 with a note reading "no prose": a
    # contradiction a return-code-only caller cannot see.
    check("an EXPLICIT adhoc declaration is REFUSED by authorize (not exit 0)",
          rc == 4 and "FRC-PROSE-FORBIDDEN" in codes(p), f"rc={rc}")
    check("and it is declared non-evidence", "not F7/F8/F9 evidence" in out)


def case_adhoc_cannot_claim_lifecycle() -> None:
    """Required: lightweight review cannot claim advancement or completion."""
    rc, p, _ = run("scope", "--parent-scope", "adhoc_review", "--child-brief", "-",
                   stdin=OBSERVED_TERMINAL_CLAIM)
    check("ad hoc + terminal vocabulary -> REFUSED", rc == 4, f"rc={rc}")
    check("-> FRC-TERMINAL-UNPROVEN", "FRC-TERMINAL-UNPROVEN" in codes(p))

    # Required: a valid ad hoc review still works.
    rc, p, _ = run("scope", "--parent-scope", "adhoc_review", "--child-brief", "-",
                   stdin="run_scope: adhoc_review\n"
                         "Read this essay and tell me whether the argument is earned. "
                         "Return your findings in your response.")
    check("valid ad hoc review still works", rc == 0, f"rc={rc}")
    rc, p, out = run("authorize", "--project-root", "/definitely/not/here",
                     "--run-scope", "adhoc_review")
    check("ad hoc prose authorization is REFUSED (FRC-PROSE-FORBIDDEN)",
          rc == 4 and "FRC-PROSE-FORBIDDEN" in codes(p), f"rc={rc}")
    check("ad hoc response is declared non-evidence", "not F7/F8/F9 evidence" in out)


def case_terminal_blocks_observed_two_file_state() -> None:
    """Required: the gate blocks the EXACT observed two-file state."""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "actor-and-agency.md").write_text("# Actor and Agency\n\nEssay body.\n",
                                               encoding="utf-8")
        (d / "actor-and-agency_review-record.md").write_text(
            "Review record without frontmatter.\n", encoding="utf-8")
        rc, p, _ = run("terminal", "--project-root", str(d))
        check("observed two-file state -> terminal REFUSED", rc == 4, f"rc={rc}")
        check("-> FRC-TERMINAL-UNPROVEN", "FRC-TERMINAL-UNPROVEN" in codes(p))
        check("-> also FRC-NO-PROJECT", "FRC-NO-PROJECT" in codes(p))


def case_m4_blocks_while_m1_m3_unaccepted() -> None:
    """Required: M4 blocks while any M1-M3 is unaccepted; presence != acceptance."""
    with tempfile.TemporaryDirectory() as td:
        proj = Path(td) / "p"
        (proj / "reviews").mkdir(parents=True)
        (proj / "research_notes").mkdir(parents=True)
        (proj / "manuscript").mkdir(parents=True)
        (proj / "milestones").mkdir(parents=True)
        # Files EXIST for every milestone -- presence must not imply acceptance.
        (proj / "milestones" / "M1_project_memo.md").write_text("memo\n", encoding="utf-8")
        (proj / "milestones" / "M2_annotated_references.md").write_text("refs\n",
                                                                        encoding="utf-8")
        (proj / "milestones" / "M3_argument_evidence_outline.md").write_text("outline\n", encoding="utf-8")
        (proj / "milestones" / "M4_complete_paper_draft.md").write_text("# Essay\n\nBody.\n", encoding="utf-8")
        (proj / "reviews" / "assignment_contract.json").write_text(
            json.dumps({"status": "resolved"}), encoding="utf-8")
        ms = {}
        for k in ("M1", "M2", "M3"):
            ms[k] = {"status": "in_progress", "applicability": "applicable",
                     "approval": {"status": "pending", "authority": None,
                                  "evidence_path": None},
                     "handoff": {"status": "not_ready", "packet_path": None}}
        ms["M4"] = {"status": "in_progress", "applicability": "applicable",
                    "approval": {"status": "pending"}, "handoff": {"status": "not_ready"}}
        (proj / "reviews" / "phase_state.json").write_text(json.dumps({
            "milestone_framework": {"mode": "native", "milestones": ms, "events": []},
            "terminal_phase_reached": False, "sections": {}}), encoding="utf-8")

        rc, p, _ = run("terminal", "--project-root", str(proj))
        check("M1-M3 unaccepted -> terminal REFUSED", rc == 4, f"rc={rc}")
        unmet = ((p or {}).get("findings") or [{}])[-1].get("unmet", [])
        joined = " | ".join(unmet)
        # Assert the BEHAVIOUR (each unaccepted milestone is named), not the
        # phrasing. The old assertion required the literal string "M1.status",
        # which was this gate's own wording for a fact the milestone validator
        # states in its own vocabulary. Pinning a delegate's phrasing would make
        # composition impossible: the authority could not improve a message
        # without breaking a test that never cared about the message.
        for key in ("M1", "M2", "M3"):
            check(f"names {key} as unaccepted", key in joined, joined[:70])
        check("file presence did NOT imply acceptance", rc == 4 and bool(unmet))


_ROUND_ENTRY = (
    "## Round 1 — 2026-07-17\n\n"
    "**Round program focus:** none — full scope\n"
    "**Hypothesis:** drafting §1 establishes the argument.\n"
    "**Scope:** §1\n"
    "**Changes:**\n- [§1] → drafted → plan action A1\n"
    "**Self-check result:** CLEAN\n"
    "**Verdict:** RETAIN\n")


def _gate_project_with_receipt(proj: Path, target: str = "M1"):
    """A real gate project holding a GENUINE READY receipt for `target`."""
    import assignment_fixture_support as afs

    phase_state = afs.minimal_gate_project(proj, target=target)
    if target == "M4":
        for key in ("M1", "M2", "M3"):
            phase_state["milestone_framework"]["milestones"][key]["status"] = "accepted"
        afs.write_wiki_evidence(proj, phase_state)
    rel = f"reviews/.harness/assignment/ready/gate_receipt_{target}_20260717T000000Z.json"
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "assignment_process_gate.py"),
         "--project-root", str(proj), "--stage", "draft",
         "--target-milestone", target, "--emit-receipt", rel],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proj / rel, (r.stdout or "") + (r.stderr or "")


def case_authorship_catches_non_generator_prose() -> None:
    """Required: direct non-Generator manuscript writing is caught.

    The POSITIVE anchor needs a genuine assignment-gate receipt, not just a
    round entry. A revision-log entry is written by the same actor whose
    authority is in question, so on its own it proves the claim by restating it:
    "I was authorized to write this, signed, the thing that wrote it." An anchor
    that accepts self-attestation preserves the very bypass the negative cases
    close -- and `case_complete_round_entry_still_needs_a_receipt` in the
    bypass suite would then contradict it.
    """
    with tempfile.TemporaryDirectory() as td:
        proj = Path(td) / "p"
        receipt, log = _gate_project_with_receipt(proj, target="M4")
        if not receipt.is_file():
            check("authorship anchor has a genuine receipt", False,
                  f"gate did not emit one: {log[-120:]}")
            return
        (proj / "manuscript").mkdir(parents=True, exist_ok=True)
        (proj / "milestones").mkdir(parents=True, exist_ok=True)
        (proj / "milestones" / "M4_complete_paper_draft.md").write_text("# Essay\n\nProse nobody logged.\n",
                                                     encoding="utf-8")

        # 1. prose, no log at all -> refused
        rc, p, _ = run("authorship", "--project-root", str(proj))
        check("unattributed manuscript prose -> REFUSED", rc == 4, f"rc={rc}")
        check("-> FRC-AUTHORSHIP", "FRC-AUTHORSHIP" in codes(p))

        # 2. empty log -> refused
        (proj / "manuscript" / "revision_log.md").write_text("", encoding="utf-8")
        rc, p, _ = run("authorship", "--project-root", str(proj))
        check("empty revision_log -> REFUSED", rc == 4 and "FRC-AUTHORSHIP" in codes(p),
              f"rc={rc}")

        # 3. fabricated log -> refused
        (proj / "manuscript" / "revision_log.md").write_text(
            "today I had a sandwich\n", encoding="utf-8")
        rc, p, _ = run("authorship", "--project-root", str(proj))
        check("fabricated revision_log -> REFUSED",
              rc == 4 and "FRC-AUTHORSHIP" in codes(p), f"rc={rc}")

        # 4. genuine scoped writer transaction + valid Generator round -> PASS
        (proj / "manuscript" / "revision_log.md").write_text("", encoding="utf-8")
        record = json.loads(receipt.read_text(encoding="utf-8"))
        preflight = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "assignment_dispatch_preflight.py"),
             "--project-root", str(proj), "--receipt", str(receipt),
             "--expected-target", "M4", "--consumer", "planner",
             "--write-path", "milestones/M4_complete_paper_draft.md",
             "--write-path", "manuscript/revision_log.md"],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        check("M4 receipt reserves for the exact writer paths", preflight.returncode == 0,
              (preflight.stdout or "")[-120:])
        reserved = receipt.parent.parent / "reserved" / receipt.name
        staged = (proj / "reviews" / ".harness" / "assignment" / "staged"
                  / record["receipt_id"])
        staged.mkdir(parents=True, exist_ok=True)
        staged_main = staged / "main.md"
        staged_log = staged / "revision_log.md"
        staged_main.write_bytes((proj / "milestones" / "M4_complete_paper_draft.md").read_bytes())
        staged_log.write_text(_ROUND_ENTRY, encoding="utf-8")
        plan = {
            "schema_version": "1.0.0", "receipt_id": record["receipt_id"],
            "reservation_id": record["reservation_id"], "target_milestone": "M4",
            "role": "generator", "writes": [
                {"staged_path": staged_main.relative_to(proj).as_posix(),
                 "target_path": "milestones/M4_complete_paper_draft.md",
                 "sha256": hashlib.sha256(staged_main.read_bytes()).hexdigest()},
                {"staged_path": staged_log.relative_to(proj).as_posix(),
                 "target_path": "manuscript/revision_log.md",
                 "sha256": hashlib.sha256(staged_log.read_bytes()).hexdigest()},
            ],
        }
        plan_path = staged / "write_plan.json"
        plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
        writer = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "assignment_writer_commit.py"),
             "--project-root", str(proj), "--receipt", str(reserved),
             "--plan", str(plan_path)], capture_output=True, text=True,
            encoding="utf-8", errors="replace")
        check("scoped writer commits M4 evidence", writer.returncode == 0,
              (writer.stdout or "")[-120:])
        receipt = receipt.parent.parent / "consumed" / receipt.name
        rc, p, _ = run("authorship", "--project-root", str(proj))
        check("genuine receipt + valid Generator round PASSES", rc == 0,
              f"rc={rc} {str((p or {}).get('findings'))[:500]}")

        # 5. same valid round, receipt now STALE -> refused
        st = json.loads((proj / "reviews/phase_state.json").read_text(encoding="utf-8"))
        st["manuscript_id"] = "moved-underneath"
        (proj / "reviews/phase_state.json").write_text(
            json.dumps(st, indent=2) + "\n", encoding="utf-8")
        rc, p, _ = run("authorship", "--project-root", str(proj))
        msgs = " ".join(f.get("message", "") for f in (p or {}).get("findings", []))
        check("valid round + STALE receipt -> REFUSED (APG-RECEIPT-STALE)",
              rc == 4 and "FRC-AUTHORSHIP" in codes(p)
              and "APG-RECEIPT-STALE" in msgs, f"rc={rc} {msgs[:80]}")

        # 6. same valid round, receipt removed -> refused
        receipt.unlink()
        rc, p, _ = run("authorship", "--project-root", str(proj))
        check("valid-looking round WITHOUT a receipt -> REFUSED",
              rc == 4 and "FRC-AUTHORSHIP" in codes(p), f"rc={rc}")


def case_valid_native_fixture_passes() -> None:
    """Required: a genuinely valid native fixture passes the terminal gate.

    This is the falsifiability anchor: without it, "refuse everything" would
    score full marks on every other case in this file. It previously scored full
    marks on a fixture invented HERE -- a hand-rolled ledger with a ``FINAL``
    key and ``approval.status: accepted``, neither of which the real schema has
    (it requires M1..M5, and the accepted value is ``approved``). So the anchor
    certified nothing: fixture and gate shared one author and one
    misunderstanding, and agreed with each other instead of with the system.

    The fixture is now the milestone authority's own, through the shared
    ``valid_project`` builder: one fixture, built by the authority that defines
    what "valid" means.
    """
    from full_run_semantic_bypass_smoketest import valid_project

    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))

        rc, p, _ = run("terminal", "--project-root", str(proj))
        check("valid native M1->M5 fixture PASSES terminal", rc == 0,
              f"rc={rc} unmet={((p or {}).get('findings') or [{}])[-1].get('unmet', [])[:3]}")

        # And the same fixture must FAIL the moment one requirement is removed --
        # otherwise the pass proves only that the gate can say yes.
        (proj / "reviews" / "G4_signoff.md").unlink()
        rc, p, _ = run("terminal", "--project-root", str(proj))
        check("removing G.4 flips the same fixture to REFUSED", rc == 4, f"rc={rc}")


def main() -> int:
    print("full_run_contract_smoketest")
    print(f"  gate: {GATE.relative_to(ROOT).as_posix()}")
    print()
    for fn in (case_full_run_intent_recognised,
               case_intent_is_advisory_only,
               case_scope_is_structural_not_phrasal,
               case_three_scope_contract_matrix,
               case_missing_scaffold_blocks_before_prose,
               case_bootstrapped_but_no_contract_blocks,
               case_lightweight_child_blocks,
               case_adhoc_cannot_claim_lifecycle,
               case_terminal_blocks_observed_two_file_state,
               case_m4_blocks_while_m1_m3_unaccepted,
               case_authorship_catches_non_generator_prose,
               case_valid_native_fixture_passes):
        print(f"{fn.__name__}:")
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            check(fn.__name__, False, f"raised {type(exc).__name__}: {exc}")
        print()
    if FAILURES:
        print(f"FAIL: {len(FAILURES)}: {FAILURES}")
        return 1
    print("PASS: the full-run contract holds against the observed failure")
    return 0


if __name__ == "__main__":
    with semantic_graph_fixture_environment():
        sys.exit(main())
