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

import io
import json
import subprocess
import sys
import tempfile
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
                         "manuscript/main.md. Write F7 evidence packets and update "
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
    check("only an EXPLICIT adhoc declaration permits the no-project path",
          rc == 0, f"rc={rc}")
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
    check("explicit ad hoc without a project is permitted (no prose)", rc == 0, f"rc={rc}")
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
        # Files EXIST for every milestone -- presence must not imply acceptance.
        (proj / "research_notes" / "project_memo.md").write_text("memo\n", encoding="utf-8")
        (proj / "research_notes" / "annotated_references.md").write_text("refs\n",
                                                                        encoding="utf-8")
        (proj / "manuscript" / "outline.md").write_text("outline\n", encoding="utf-8")
        (proj / "manuscript" / "main.md").write_text("# Essay\n\nBody.\n", encoding="utf-8")
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
        check("names M1 as unaccepted", "M1.status" in joined, joined[:70])
        check("file presence did NOT imply acceptance",
              "M1.status" in joined and "M2.status" in joined and "M3.status" in joined)


def case_authorship_catches_non_generator_prose() -> None:
    """Required: direct non-Generator manuscript writing is caught."""
    with tempfile.TemporaryDirectory() as td:
        proj = Path(td) / "p"
        (proj / "manuscript").mkdir(parents=True)
        (proj / "manuscript" / "main.md").write_text("# Essay\n\nProse nobody logged.\n",
                                                     encoding="utf-8")
        rc, p, _ = run("authorship", "--project-root", str(proj))
        check("unattributed manuscript prose -> REFUSED", rc == 4, f"rc={rc}")
        check("-> FRC-AUTHORSHIP", "FRC-AUTHORSHIP" in codes(p))
        # With a Generator revision log, the same bytes are accounted for.
        (proj / "manuscript" / "revision_log.md").write_text(
            "## round 1 (generator)\n- drafted §1\n", encoding="utf-8")
        rc, _, _ = run("authorship", "--project-root", str(proj))
        check("Generator-attributed prose passes", rc == 0, f"rc={rc}")


def case_valid_native_fixture_passes() -> None:
    """Required: a valid native M1->M4->FINAL fixture passes the terminal gate.

    This is the falsifiability anchor: without it, "refuse everything" would
    score full marks on every other case in this file.
    """
    with tempfile.TemporaryDirectory() as td:
        proj = Path(td) / "p"
        for d in ("reviews", "manuscript", "research_notes", "reviews/handoffs",
                  "reviews/evidence"):
            (proj / d).mkdir(parents=True, exist_ok=True)

        def w(rel: str, text: str) -> Path:
            p = proj / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8", newline="\n")
            return p

        import hashlib
        w("reviews/assignment_contract.json", json.dumps({"status": "resolved"}))
        w("manuscript/main.md", "# Essay\n\nBody.\n")
        w("manuscript/revision_log.md", "## round 1 (generator)\n- drafted\n")
        w("reviews/findings.json", json.dumps({"findings": []}))
        w("reviews/check8_evidence.json", json.dumps({"aggregate": "CLEAN"}))
        w("reviews/convergence_log.md", "- finding_id: F1\n  status: RESOLVED\n")
        w("reviews/ph3_convergence_signoff.md",
          "- row_timestamp: 2026-07-17T00:00:00Z\n  is_terminal: true\n"
          "  user_signature: user\n  user_signed_at: 2026-07-17T00:00:00Z\n"
          "  convergence_metric_value: 0.004\n  t3_verdict: CONVERGING\n"
          "  final_owner_state: closed\n")
        w("reviews/G4_signoff.md", "# G.4\n\nverdict: PASS\n")
        w("reviews/reflector_full_2026-07-17.md", "# Reflector-full close-out\n")
        w("reviews/f8_final_round_report.md", "# F8 final round\n")
        w("reviews/mcr_report.md", "# MCR\n\nverdict: CLEARED\n")
        w("reviews/evidence/f7_round1.json", json.dumps({"checks": []}))

        ms = {}
        for k, art in (("M1", "research_notes/project_memo.md"),
                       ("M2", "research_notes/annotated_references.md"),
                       ("M3", "manuscript/outline.md"),
                       ("M4", "manuscript/main.md")):
            w(art, f"# {k}\n\ncontent\n")
            ev = w(f"reviews/approval_{k}.md", f"# {k} approval\n\nuser accepted\n")
            af = proj / art
            entry = {
                "status": "accepted", "applicability": "applicable",
                "approval": {"status": "accepted", "authority": "user",
                             "evidence_path": f"reviews/approval_{k}.md",
                             "approved_at": "2026-07-17T00:00:00Z"},
                "artifacts": [{"path": art,
                               "sha256": hashlib.sha256(af.read_bytes()).hexdigest()}],
            }
            if k != "M4":
                pk = w(f"reviews/handoffs/{k}_to_next.json", json.dumps({"from": k}))
                entry["handoff"] = {
                    "status": "consumed",
                    "packet_path": f"reviews/handoffs/{k}_to_next.json",
                    "packet_sha256": hashlib.sha256(pk.read_bytes()).hexdigest()}
            else:
                entry["handoff"] = {"status": "consumed", "packet_path": None}
            ms[k] = entry
        fp = w("reviews/handoffs/FINAL_packet.json", json.dumps({"final": True}))
        ms["FINAL"] = {"status": "accepted", "applicability": "applicable",
                       "approval": {"status": "accepted", "authority": "user",
                                    "evidence_path": "reviews/approval_M4.md"},
                       "handoff": {"status": "consumed",
                                   "packet_path": "reviews/handoffs/FINAL_packet.json",
                                   "packet_sha256": hashlib.sha256(
                                       fp.read_bytes()).hexdigest()}}
        w("reviews/phase_state.json", json.dumps({
            "milestone_framework": {"mode": "native", "milestones": ms,
                                    "events": [{"event": "M1_accepted"}]},
            "sections": {"1": {"pre_mcr_deep_pass_completed": True}},
            "terminal_phase_reached": True}, indent=1))

        rc, p, out = run("terminal", "--project-root", str(proj))
        check("valid native M1->M4->FINAL fixture PASSES terminal", rc == 0,
              f"rc={rc} unmet={((p or {}).get('findings') or [{}])[-1].get('unmet', [])[:3]}")
        rc, _, _ = run("authorize", "--project-root", str(proj))
        check("valid fixture authorizes prose", rc == 0, f"rc={rc}")

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
    sys.exit(main())
