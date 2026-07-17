#!/usr/bin/env python3
"""full_run_semantic_bypass_smoketest - semantic bypasses of the full-run contract.

WRITTEN BEFORE THE FIX, AND PROVEN TO FAIL AGAINST c945245.

    FRC_GATE=<old build> python scripts/full_run_semantic_bypass_smoketest.py

Re-run that against c945245 and read the result carefully, because it is not
"15 OPEN". It is:

  * 7 genuinely OPEN  - authorship (2), authorize (2), scope (2), and the
    BASELINE ANCHOR ITSELF;
  * 8 vacuously "CLOSED" - the old gate refuses the mutated project, but it
    also refuses the VALID one, so those cases prove nothing about it.

The anchor is what exposes that, and it is the reason the anchor exists. The
old gate rejected a genuinely valid project on:

    M1..M4.approval.status is 'approved'      <- the schema's own value
    no MCR artefact under reviews/            <- MCR clearance is not a file

It demanded `approval.status == "accepted"` because that is the word the author
(me) remembered, while `references/schemas/milestone_framework.schema.json` says
`approved`. So the old checker was not merely permissive; it was wrong in BOTH
directions -- it passed a project I invented and would have refused every real
one. That is the strongest available argument for composing the real validators
rather than paraphrasing them from memory: a paraphrase is not a weaker
authority, it is a DIFFERENT one, and it disagrees with the real system exactly
where it matters.

Under the current build the anchor passes and all 16 bypasses are closed.

These cases encode the CodeRabbit semantic review of PR #14. Every one of them
is a way to satisfy the gate's LETTER while defeating its PURPOSE -- the gate
inferring lifecycle truth from a filename, a file's existence, or a substring,
rather than from authoritative structured evidence.

The design principle these enforce:

    compose authoritative structured evidence;
    never infer lifecycle truth from filenames, file presence, or substrings.

Each case is named for the bypass, not the code path, because the bypass is the
thing that must stay closed when the implementation is refactored.

Run:  python scripts/full_run_semantic_bypass_smoketest.py
Exit: 0 every bypass is closed; 1 at least one bypass is OPEN.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
# FRC_GATE exists so this suite can be pointed at an OLDER build of the gate and
# demonstrated to fail against it. A test that has only ever run against the
# implementation it was written for proves agreement, not correctness -- these
# cases were required to fail against c945245 before the fix landed, and that
# claim has to stay re-runnable rather than resting on a note in a commit.
GATE = Path(os.environ.get("FRC_GATE") or (ROOT / "scripts" / "full_run_contract_check.py"))
sys.path.insert(0, str(ROOT / "scripts"))
FAILURES: list[str] = []

# The baseline is the MILESTONE AUTHORITY'S OWN valid-project fixture, not one
# invented here.
#
# The first cut of this suite hand-rolled a "valid project": a ledger with a
# `FINAL` key, four milestones, and whatever fields the checker of the day
# happened to read. It passed -- against a checker that read exactly those
# fields. It was not a valid project at all: the real schema requires M1..M5
# with additionalProperties:false and never mentions "FINAL", so that fixture
# could not have survived contact with milestone_framework_validate.
#
# A fixture that only satisfies the checker under test proves nothing about the
# checker: both can be wrong in the same direction, and a green suite then
# certifies the agreement rather than the behaviour. So the baseline is built by
# the fixture builder the milestone authority tests ITSELF against. If that
# builder drifts, this suite fails loudly rather than quietly agreeing with a
# stale idea of a valid project.
from milestone_framework_smoketest import (  # noqa: E402
    _materialize_native_project, _phase_document,
)


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'CLOSED' if ok else 'OPEN  '}  {name}{(' - ' + detail) if detail else ''}")
    if not ok:
        FAILURES.append(name)


def run(*args: str, stdin: str | None = None) -> tuple[int, dict | None]:
    r = subprocess.run([sys.executable, str(GATE), *args], input=stdin,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=300)
    try:
        return r.returncode, json.loads(r.stdout)
    except (json.JSONDecodeError, ValueError):
        return r.returncode, None


def codes(p: dict | None) -> set[str]:
    return {f.get("code") for f in (p or {}).get("findings", [])}


def _w(p: Path, text: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")
    return p


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def valid_project(base: Path) -> Path:
    """A project that SHOULD pass terminal. Every bypass below mutates one fact.

    Built by the milestone authority's own fixture builder, then topped up with
    the artefacts the full-run contract requires beyond the ledger. Kept
    deliberately close to legitimate so each case isolates exactly one semantic
    hole; if the baseline itself stopped passing, every case would 'pass' for
    the wrong reason -- so the baseline is asserted first, as an anchor.
    """
    proj = base / "p"
    proj.mkdir(parents=True, exist_ok=True)
    ledger = _materialize_native_project(proj)
    ledger["mode"] = "native"
    doc = _phase_document(ledger, "Ph4")

    # The full-run contract's own §4 requirements, beyond the ledger's.
    for key, section in doc.get("sections", {}).items():
        section["current_tier"] = "T3_converged"   # MCR clearance is state
    _w(proj / "reviews/assignment_contract.json", json.dumps({"status": "resolved"}))
    _w(proj / "manuscript/revision_log.md",
       "## Round 1 — 2026-07-17\n\n"
       "**Round program focus:** none — full scope\n"
       "**Hypothesis:** drafting the section establishes the argument.\n"
       "**Scope:** §1\n"
       "**Changes:**\n- [§1] → drafted → plan action A1\n"
       "**Self-check result:** CLEAN\n"
       "**Verdict:** RETAIN\n"
       "**Carried forward:** none\n")
    _w(proj / "reviews/findings.json", json.dumps({"findings": []}))
    _w(proj / "reviews/check8_evidence.json", json.dumps({"aggregate": "CLEAN"}))
    _w(proj / "reviews/convergence_log.md", "- finding_id: F1\n  status: RESOLVED\n")
    _w(proj / "reviews/ph3_convergence_signoff.md",
       "- row_timestamp: 2026-07-17T00:00:00Z\n  iteration_number: 3\n"
       "  is_terminal: true\n  is_reengagement: false\n"
       "  user_signature: user\n  user_signed_at: 2026-07-17T00:00:00Z\n"
       "  convergence_metric_value: 0.004\n  t3_verdict: CONVERGING\n"
       "  final_owner_state: closed\n")
    # `status:` lines, not `verdict:` prose -- milestone_framework_validate's
    # _signed_status is the authority for what a signoff says.
    _w(proj / "reviews/G4_signoff.md", "# G.4\n\nstatus: PASS\n")
    _w(proj / "reviews/ph4_ship_signoff.md", "# Ph4 ship\n\nstatus: APPROVED\n")
    _w(proj / "reviews/reflector_full_2026-07-17.md", "# Reflector-full close-out\n")
    _w(proj / "reviews/f8_final_round_report.md", "# F8 final round\n")
    _w(proj / "reviews/evidence/f7_round1.json", json.dumps({"checks": []}))
    _w(proj / "reviews/phase_state.json", json.dumps(doc, indent=1))
    return proj


def mutate_state(proj: Path, fn) -> None:
    p = proj / "reviews/phase_state.json"
    st = json.loads(p.read_text(encoding="utf-8"))
    fn(st)
    _w(p, json.dumps(st, indent=1))


# ==========================================================================
# BASELINE -- must PASS, else every case below is vacuous
# ==========================================================================
def case_baseline_valid_project_passes() -> None:
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        rc, p = run("terminal", "--project-root", str(proj))
        check("BASELINE valid project passes terminal (anchor)", rc == 0,
              f"rc={rc} {str((p or {}).get('findings'))[:90]}")


# ==========================================================================
# TERMINAL EVIDENCE bypasses  (CodeRabbit :454)
# ==========================================================================
def case_g4_not_pass_substring() -> None:
    """`status: NOT PASS` contains "PASS" -- a substring is not a verdict."""
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        _w(proj / "reviews/G4_signoff.md", "# G.4\n\nstatus: NOT PASS\n")
        rc, p = run("terminal", "--project-root", str(proj))
        check("G.4 'status: NOT PASS' is refused (substring is not a verdict)",
              rc == 4, f"rc={rc}")


def case_g4_failed_wording() -> None:
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        _w(proj / "reviews/G4_signoff.md",
           "# G.4\n\nstatus: FAIL\nnote: did not PASS review\n")
        rc, p = run("terminal", "--project-root", str(proj))
        check("G.4 'status: FAIL' (word PASS elsewhere) is refused", rc == 4, f"rc={rc}")


def case_artifact_hash_absent() -> None:
    """An artifact with no recorded sha256 must not satisfy exact-byte binding."""
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        mutate_state(proj, lambda st: st["milestone_framework"]["milestones"]["M4"]
                     ["artifacts"][0].pop("sha256"))
        rc, p = run("terminal", "--project-root", str(proj))
        check("M4 artifact without sha256 is refused", rc == 4, f"rc={rc}")


def case_f9_packet_hash_absent() -> None:
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        mutate_state(proj, lambda st: st["milestone_framework"]["milestones"]["M1"]
                     ["handoff"].pop("packet_sha256"))
        rc, p = run("terminal", "--project-root", str(proj))
        check("M1 F9 packet without packet_sha256 is refused", rc == 4, f"rc={rc}")


def case_handoff_ready_not_consumed() -> None:
    """§4 requires CONSUMED predecessor handoffs; 'ready' is not consumed."""
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        mutate_state(proj, lambda st: st["milestone_framework"]["milestones"]["M1"]
                     ["handoff"].update({"status": "ready"}))
        rc, p = run("terminal", "--project-root", str(proj))
        check("predecessor handoff 'ready' (not consumed) is refused", rc == 4, f"rc={rc}")


def _unclear_mcr(st: dict) -> None:
    """Put every section back to un-converged: MCR is NOT cleared in state."""
    for section in st.get("sections", {}).values():
        section["current_tier"] = "T3"
        section["ceiling_locked"] = False
        section.pop("last_approved_tier", None)


def case_mcr_filename_glob() -> None:
    """A suggestively-named file must not count as a passing MCR.

    MCR clearance is a state predicate (TIER_PROTOCOL.md §9.4), so the file is
    not merely insufficient -- it is not the kind of thing that could ever
    settle the question.
    """
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        mutate_state(proj, _unclear_mcr)
        _w(proj / "reviews/mcr_notes_scratch.md", "# random mcr musings, not a verdict\n")
        rc, p = run("terminal", "--project-root", str(proj))
        check("arbitrary *mcr* filename does not satisfy MCR", rc == 4, f"rc={rc}")


def case_mcr_failed_verdict() -> None:
    """A file ASSERTING clearance does not clear the MCR."""
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        mutate_state(proj, _unclear_mcr)
        _w(proj / "reviews/mcr_report.md", "# MCR\n\nverdict: CLEARED\nstatus: PASS\n")
        rc, p = run("terminal", "--project-root", str(proj))
        check("an MCR file claiming CLEARED does not clear un-converged state",
              rc == 4, f"rc={rc}")


def case_final_milestone_absent() -> None:
    """A missing FINAL/M5 record must not skip the final-packet requirement."""
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        mutate_state(proj, lambda st: st["milestone_framework"]["milestones"].pop("M5"))
        rc, p = run("terminal", "--project-root", str(proj))
        check("absent FINAL/M5 record is refused (not skipped)", rc == 4, f"rc={rc}")


def case_final_packet_unbound() -> None:
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        mutate_state(proj, lambda st: st["milestone_framework"]["milestones"]["M5"]
                     ["handoff"].pop("packet_sha256"))
        rc, p = run("terminal", "--project-root", str(proj))
        check("terminal F9 packet without hash binding is refused", rc == 4, f"rc={rc}")


# ==========================================================================
# AUTHORSHIP bypasses  (CodeRabbit :364)
# ==========================================================================
def case_empty_revision_log_is_not_authorship() -> None:
    """A filename is not evidence. An EMPTY log must not attribute prose."""
    with tempfile.TemporaryDirectory() as td:
        proj = Path(td) / "p"
        _w(proj / "manuscript/main.md", "# Essay\n\nProse nobody wrote.\n")
        _w(proj / "manuscript/revision_log.md", "")
        rc, p = run("authorship", "--project-root", str(proj))
        check("empty revision_log.md does not establish authorship", rc == 4, f"rc={rc}")


def case_complete_round_entry_still_needs_a_receipt() -> None:
    """§3 has two halves. The log entry alone is the round marking its own work.

    CodeRabbit (bd194d0): "The contract requires a Generator round entry and its
    preflight receipt, but neither is parsed or bound." The parsing half was
    closed at e948569 -- the two cases either side of this one prove it -- but
    the receipt half was not, and it is the half that is not self-attested: a
    round entry is written by the same actor whose authority is in question.
    """
    with tempfile.TemporaryDirectory() as td:
        proj = Path(td) / "p"
        _w(proj / "manuscript/main.md", "# Essay\n\nProse.\n")
        _w(proj / "manuscript/revision_log.md",
           "## Round 1 — 2026-07-17\n\n"
           "**Hypothesis:** h\n**Scope:** §1\n"
           "**Changes:**\n- [§1] → drafted → A1\n"
           "**Self-check result:** CLEAN\n**Verdict:** RETAIN\n")
        _w(proj / "reviews/assignment_contract.json", json.dumps({"status": "resolved"}))
        _w(proj / "reviews/phase_state.json", json.dumps({
            "milestone_framework": {"mode": "native", "milestones": {
                "M1": {"status": "in_progress", "applicability": "applicable",
                       "approval": {"status": "pending"}}}}}))
        rc, p = run("authorship", "--project-root", str(proj))
        check("a complete round entry without a gate receipt is refused",
              rc == 4, f"rc={rc}")


def case_fabricated_revision_log_is_not_authorship() -> None:
    """Arbitrary prose in the log must not attribute the manuscript."""
    with tempfile.TemporaryDirectory() as td:
        proj = Path(td) / "p"
        _w(proj / "manuscript/main.md", "# Essay\n\nProse nobody wrote.\n")
        _w(proj / "manuscript/revision_log.md", "today I had a sandwich\n")
        rc, p = run("authorship", "--project-root", str(proj))
        check("fabricated revision_log content does not establish authorship",
              rc == 4, f"rc={rc}")


# ==========================================================================
# AUTHORIZE bypasses  (CodeRabbit :214)
# ==========================================================================
def case_authorize_requires_exact_resolved_status() -> None:
    with tempfile.TemporaryDirectory() as td:
        proj = Path(td) / "p"
        _w(proj / "reviews/phase_state.json", json.dumps(
            {"milestone_framework": {"mode": "native", "milestones": {}}}))
        _w(proj / "reviews/assignment_contract.json", json.dumps({}))
        rc, p = run("authorize", "--project-root", str(proj))
        check("contract with NO status field is refused", rc == 4, f"rc={rc}")


def case_authorize_requires_receipt_and_preflight() -> None:
    """A resolved contract alone must not authorize prose (§2 items 3-5)."""
    with tempfile.TemporaryDirectory() as td:
        proj = Path(td) / "p"
        _w(proj / "reviews/phase_state.json", json.dumps({
            "milestone_framework": {"mode": "native", "milestones": {
                "M1": {"status": "in_progress", "applicability": "applicable",
                       "approval": {"status": "pending"}}}}}))
        _w(proj / "reviews/assignment_contract.json", json.dumps({"status": "resolved"}))
        rc, p = run("authorize", "--project-root", str(proj))
        check("resolved contract WITHOUT a READY receipt/preflight is refused",
              rc == 4, f"rc={rc}")


# ==========================================================================
# SCOPE bypasses  (CodeRabbit :294)
# ==========================================================================
def case_scope_escalation_refused() -> None:
    """An adhoc parent must not authorize a full_lifecycle child.

    Escalation is the mirror of downgrade and was entirely unguarded: only
    full-parent downgrades were rejected. A child may not grant itself
    authority its parent does not have.
    """
    rc, p = run("scope", "--parent-scope", "adhoc_review", "--child-brief", "-",
                stdin="run_scope: full_lifecycle\nDraft the manuscript.")
    check("adhoc parent cannot authorize a full_lifecycle child (escalation)",
          rc == 4, f"rc={rc}")


def case_undeclared_child_not_allowed() -> None:
    """--allow-undeclared-child must not let an undeclared child through."""
    rc, p = run("scope", "--parent-scope", "full_lifecycle", "--child-brief", "-",
                "--allow-undeclared-child",
                stdin="Please look at section 3 and report back.")
    check("--allow-undeclared-child cannot bypass the declaration requirement",
          rc == 4, f"rc={rc}")


def main() -> int:
    print("full_run_semantic_bypass_smoketest")
    print("  every case below is a way to satisfy the gate's letter and defeat its purpose")
    print()
    for fn in (case_baseline_valid_project_passes,
               case_g4_not_pass_substring, case_g4_failed_wording,
               case_artifact_hash_absent, case_f9_packet_hash_absent,
               case_handoff_ready_not_consumed, case_mcr_filename_glob,
               case_mcr_failed_verdict, case_final_milestone_absent,
               case_final_packet_unbound,
               case_empty_revision_log_is_not_authorship,
               case_fabricated_revision_log_is_not_authorship,
               case_complete_round_entry_still_needs_a_receipt,
               case_authorize_requires_exact_resolved_status,
               case_authorize_requires_receipt_and_preflight,
               case_scope_escalation_refused,
               case_undeclared_child_not_allowed):
        print(f"{fn.__name__}:")
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            check(fn.__name__, False, f"raised {type(exc).__name__}: {exc}")
        print()
    if FAILURES:
        print(f"OPEN BYPASSES: {len(FAILURES)}")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("PASS: every semantic bypass is closed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
