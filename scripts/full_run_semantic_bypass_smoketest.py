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

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
REPO_GATE = ROOT / "scripts" / "full_run_contract_check.py"

# The gate under test. Bare execution -- which is how the fixture runner invokes
# this suite -- is PINNED to the repository's own gate, and nothing in the
# environment can move it.
#
# This was an `os.environ.get("FRC_GATE")`, which the fixture runner's children
# inherit. A stray export in a shell would have had the runner record, in a
# manifest bound to the repository's tested-input digest, that these suites
# passed -- while they in fact exercised an untracked file elsewhere on disk.
# Evidence that names one artefact and tests another is worse than no evidence,
# because it is believed. Historical comparison is a deliberate act, so it takes
# a deliberate argument the registry never passes.
GATE = REPO_GATE
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
    #
    # NOTE what is NOT here any more. This used to set `current_tier:
    # T3_converged` on every section -- a legacy, tier-native field a real
    # phase-native project does not carry. It was here because the gate passed
    # raw phase sections to a tier-native predicate, so the fixture was edited
    # to speak the predicate's private dialect and make the bug pass: a fixture
    # built to fit a defect. `_phase_document` already sets `current_phase: Ph4`
    # and `pre_mcr_deep_pass_completed: true`, and the gate now reads canonical
    # state, so no dialect needs forging.
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
    # The fabricated `reviews/check8_evidence.json` -- `{"aggregate": "CLEAN"}`,
    # a document with no subchecks, no profile binding and no relation to the
    # manuscript -- is gone. It existed only to satisfy a `*check8*` glob.
    # `_install_reader_accessibility_policy` (via `_materialize_native_project`)
    # writes the CANONICAL sidecars at reviews/.harness/policy/{m4,m5}_check8.json
    # and binds them by hash in milestones.*.policy_evidence, which is where the
    # gate now looks.
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


def _authorize_na_m4(proj: Path) -> None:
    """Make M4 authorizedly not-applicable, EXACTLY as the milestone authority does.

    Lifted from milestone_framework_smoketest's own `authorized_not_applicable`
    case, not invented. A first attempt DID invent it -- `{"authority", "rule",
    "rationale", "authorized_at"}` -- and the gate refused it on four counts:
    missing `reason`/`scope`; a `rule` anchor that must resolve in the authority
    document; a `substitute_evidence` path that must exist and hash; and a
    required append-only `authorized_override` EVENT. That refusal is the system
    working: a waiver cannot be self-granted by editing one field, which is
    exactly what you want of the field that switches a requirement off.

    Scoped to M4 because that is the milestone the authority's own fixtures
    waive. M5 is the terminal deliverable; no authoritative N/A-M5 fixture
    exists to copy, and inventing one would repeat the mistake above.
    """
    import milestone_framework_smoketest as mfs

    st = json.loads((proj / "reviews/phase_state.json").read_text(encoding="utf-8"))
    ledger = st["milestone_framework"]
    target = ledger["milestones"]["M4"]
    target.update({
        "status": "not_applicable", "applicability": "not_applicable",
        "artifacts": [], "feedback_records": [],
        "approval": {"status": "not_applicable", "authority": None,
                     "evidence_path": None, "approved_at": None},
        "handoff": {"status": "not_applicable", "packet_path": None,
                    "packet_sha256": None},
        "dependency_state": "not_applicable",
        "authorized_override": mfs._override(["M4"], ["M4_to_M5"]),
    })
    target.pop("policy_evidence", None)
    override_hash, _ = mfs._write_bound_file(
        proj, target["authorized_override"]["substitute_evidence"], "authorized N/A\n")
    target["authorized_override"]["substitute_evidence_sha256"] = override_hash
    ledger["events"].append({
        "sequence": len(ledger["events"]) + 1, "event_type": "authorized_override",
        "timestamp": "2026-07-13T19:00:00Z", "milestone": "M4", "lineage_id": "main",
        "actor": "planner", "authority": "user",
        "reason": "Authorized M4 as not applicable.",
        "evidence_path": target["authorized_override"]["substitute_evidence"],
        "evidence_sha256": override_hash, "caused_by_sequence": None, "bindings": [],
    })
    # Waiving M4 re-parents the F9 chain: M5's predecessor is now M3, not the
    # milestone that no longer exists. Without this the authority refuses with
    # MF-HANDOFF ("F9 predecessor binding does not match" / "successor work
    # started before predecessor approval and consumed handoff") -- and it is
    # RIGHT to: a waived milestone does not get to leave a dangling link in a
    # chain whose whole job is to prove each deliverable descends from an
    # approved one. Rewired through the authority's own packet writer.
    m3_handoff = ledger["milestones"]["M3"]["handoff"]
    predecessor = {"path": m3_handoff["packet_path"],
                   "sha256": m3_handoff["packet_sha256"]}
    mfs._rewrite_packet(proj, ledger, "M5",
                        lambda packet: packet.update({"predecessor_packet": predecessor}))
    _w(proj / "reviews/phase_state.json", json.dumps(st, indent=1))


def case_boundary_composition_is_applicability_aware() -> None:
    """A waived milestone is not a skipped requirement -- it is no requirement.

    SCOPE, and why it is this and not an end-to-end pass.

    The intent (CodeRabbit: "calling all three boundary validators
    unconditionally rejects valid projects where M4 or M5 is legitimately
    not_applicable") is right, and `_boundary_applies` implements it. What I
    could NOT do is demonstrate a whole N/A-M4 project passing `terminal`, and
    the reason matters more than the gap: the milestone authority's own
    expectation table validates its `authorized_not_applicable` fixture at
    TARGET M4 -- `("NOT_APPLICABLE", 0, "M4", None)` -- and never at M5. Push
    that fixture through a terminal (M5) claim and it refuses with MF-HANDOFF:
    M5 may not descend from a waived predecessor without the chain being
    legitimately re-parented, which its `native_m5_not_started_target` case
    (`MISCONFIGURED`, MF-HANDOFF) shows is deliberate.

    I could have kept editing the fixture until it went green. That is exactly
    how the fabricated `current_tier` and the invented `authorized_override`
    got in -- each was a fixture bent to make a claim pass. So this asserts the
    predicate directly, which is a real claim I can ground, and the end-to-end
    N/A-M4 terminal pass stays explicitly unproven rather than faked green.
    """
    import full_run_contract_check as frc

    def state(applicability: str) -> dict:
        return {"milestone_framework": {"milestones": {
            k: {"applicability": applicability if k == "M4" else "applicable"}
            for k in ("M1", "M2", "M3", "M4", "M5")}}}

    applicable = state("applicable")
    waived = state("not_applicable")
    check("ph4_admission runs when M4 is applicable",
          frc._boundary_applies(applicable, "ph4_admission") is True)
    check("ph4_admission is skipped when M4 is authorizedly not_applicable",
          frc._boundary_applies(waived, "ph4_admission") is False)
    check("waiving M4 does not skip ph1_to_ph2 (M1-M3 still validated)",
          frc._boundary_applies(waived, "ph1_to_ph2") is True)
    check("waiving M4 does not skip ph4_terminal_close (M5 still validated)",
          frc._boundary_applies(waived, "ph4_terminal_close") is True)
    check("an ABSENT milestone record does not skip its boundary",
          frc._boundary_applies({"milestone_framework": {"milestones": {}}},
                                "ph4_admission") is True)


def case_na_m4_does_not_waive_applicable_predecessors() -> None:
    """...and waiving M4 must not waive M1-M3."""
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        _authorize_na_m4(proj)
        mutate_state(proj, lambda st: st["milestone_framework"]["milestones"]["M1"]
                     ["handoff"].update({"status": "not_ready"}))
        rc, p = run("terminal", "--project-root", str(proj))
        check("N/A M4 does not waive an applicable M1 predecessor", rc == 4, f"rc={rc}")


def case_non_object_contract_is_refused_not_a_crash() -> None:
    """A malformed contract must produce a VERDICT, not an AttributeError.

    `_load_json` returns whatever parses. A list reached `.get()` and raised, so
    the gate exited 2 -- and exit 2 is the ABSENCE of a verdict, which a caller
    that collapses "error" into "not refused" reads as permission.
    """
    for payload in ('["resolved"]', '"resolved"', "42"):
        with tempfile.TemporaryDirectory() as td:
            proj = Path(td) / "p"
            _w(proj / "reviews/phase_state.json", json.dumps(
                {"milestone_framework": {"mode": "native", "milestones": {}}}))
            _w(proj / "reviews/assignment_contract.json", payload)
            rc, p = run("authorize", "--project-root", str(proj))
            check(f"non-object contract {payload!r} is refused (rc=4, not a crash)",
                  rc == 4 and "FRC-CONTRACT-MISSING" in codes(p), f"rc={rc}")


def case_fully_accepted_project_does_not_authorize_prose() -> None:
    """No active target is not 'no objection'."""
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        rc, p = run("authorize", "--project-root", str(proj))
        check("fully accepted project refuses authorize (no active milestone)",
              rc == 4 and "FRC-NO-ACTIVE-MILESTONE" in codes(p), f"rc={rc}")


def case_terminal_row_missing_required_fields_is_refused() -> None:
    """Delegate FULL row validation: a terminal row is more than is_terminal."""
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        _w(proj / "reviews/ph3_convergence_signoff.md",
           "- row_timestamp: 2026-07-17T00:00:00Z\n  is_terminal: true\n"
           "  is_reengagement: false\n  user_signature: user\n"
           "  user_signed_at: 2026-07-17T00:00:00Z\n")
        rc, p = run("terminal", "--project-root", str(proj))
        check("terminal row missing iteration_number/metric/verdict is refused",
              rc == 4, f"rc={rc}")


def case_terminal_row_null_convergence_metric_is_refused() -> None:
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        _w(proj / "reviews/ph3_convergence_signoff.md",
           "- row_timestamp: 2026-07-17T00:00:00Z\n  iteration_number: 3\n"
           "  is_terminal: true\n  is_reengagement: false\n"
           "  user_signature: user\n  user_signed_at: 2026-07-17T00:00:00Z\n"
           "  convergence_metric_value: null\n  t3_verdict: CONVERGING\n"
           "  final_owner_state: closed\n")
        rc, p = run("terminal", "--project-root", str(proj))
        check("terminal row with null convergence_metric_value is refused",
              rc == 4, f"rc={rc}")


def case_deep_pass_required_for_every_section() -> None:
    """`if not deep` passed when ONE of several sections had the flag."""
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))

        def add_undeep_section(st: dict) -> None:
            first = next(iter(st["sections"].values()))
            clone = json.loads(json.dumps(first))
            clone["pre_mcr_deep_pass_completed"] = False
            clone["heading_path"] = ["2. Second"]
            st["sections"]["2. Second"] = clone

        mutate_state(proj, add_undeep_section)
        rc, p = run("terminal", "--project-root", str(proj))
        check("one section without the deep pass refuses the whole terminal claim",
              rc == 4, f"rc={rc}")


def case_check8_blocker_refuses_terminal() -> None:
    """Consistency is not clearance: a truthfully recorded BLOCKER is a BLOCKER."""
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        st = json.loads((proj / "reviews/phase_state.json").read_text(encoding="utf-8"))
        ev = st["milestone_framework"]["milestones"]["M5"]["policy_evidence"]
        sidecar_path = proj / ev["check8_path"]
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        sidecar["subchecks"]["A"]["findings"] = [
            {"finding_id": "A-1", "severity": "BLOCKER", "independence_group": "g1"}]
        sidecar["aggregate_verdict"] = "BLOCKER"
        sidecar["subcheck_verdicts"]["A"] = "BLOCKER"
        payload = json.dumps(sidecar, indent=2) + "\n"
        sidecar_path.write_text(payload, encoding="utf-8", newline="\n")
        ev["check8_sha256"] = hashlib.sha256(payload.encode()).hexdigest()
        ev["aggregate_verdict"] = "BLOCKER"
        _w(proj / "reviews/phase_state.json", json.dumps(st, indent=1))
        rc, p = run("terminal", "--project-root", str(proj))
        check("a consistent Check 8 BLOCKER still refuses terminal", rc == 4, f"rc={rc}")


def case_fabricated_check8_file_is_not_evidence() -> None:
    """The old `{"aggregate": "CLEAN"}` glob-bait must not satisfy Check 8."""
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        mutate_state(proj, lambda st: [
            rec.pop("policy_evidence", None)
            for rec in st["milestone_framework"]["milestones"].values()
            if isinstance(rec, dict)])
        _w(proj / "reviews/check8_evidence.json", json.dumps({"aggregate": "CLEAN"}))
        _w(proj / "reviews/accessibility_notes.md", "# looks accessible to me\n")
        rc, p = run("terminal", "--project-root", str(proj))
        check("a file named *check8* with no bound evidence is refused",
              rc == 4, f"rc={rc}")


def case_malformed_phase_state_is_refused_despite_code_prefix() -> None:
    """phase_state_validate's codes do not all start with E."""
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        mutate_state(proj, lambda st: st.update({"sections": "not-an-object"}))
        rc, p = run("terminal", "--project-root", str(proj))
        check("malformed phase_state (non-E finding codes) is refused",
              rc == 4, f"rc={rc}")


def _unclear_mcr(st: dict) -> None:
    """Remove the MCR admission from CANONICAL state.

    This used to set `current_tier: "T3"` -- a legacy tier-native field. Once the
    gate stopped reading the legacy dialect, the mutation stopped meaning
    anything and both MCR cases silently went green: the test was un-clearing a
    field nobody consults. A negative case that mutates the wrong field does not
    fail loudly; it passes, quietly, for no reason.

    The canonical facts are `current_phase` and the admission proof surface in
    `phase_entry_log` (MF-PHASE: "Ph4 target has no valid unretracted MCR
    admission or ceiling-lock proof surface").
    """
    for section in st.get("sections", {}).values():
        section["current_phase"] = "Ph3"
        section["ceiling_locked"] = False
        section["phase_entry_log"] = []
        section.pop("last_approved_phase", None)


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


# ==========================================================================
# NOT CLOSED, and named rather than quietly dropped:
#   "add a case that genuinely reaches rejected dispatch preflight"
#
# Every authorize case here stops BEFORE the receipt-verification and preflight
# branches -- on a missing contract, a missing receipt, or no active target. So
# those two branches are reachable in principle and unexercised in fact, and a
# branch no test reaches is a branch whose failure mode is a guess.
#
# The attempt failed for an instructive reason, recorded so the next attempt
# starts from it rather than rediscovering it. Reaching preflight needs a REAL
# READY receipt, and `assignment_process_gate.py` refuses to emit one against
# this fixture's `{"status": "resolved"}` stub contract, with nine blockers:
#
#   APG-CONTRACT-UNRESOLVED (needs version 1.0.0), APG-PROFILE-ID,
#   APG-PROFILE-PATH, APG-PROFILE-HASH, APG-SOURCE-AUTHORITY, APG-SEQUENCE,
#   APG-MAPPING, APG-PROFESSOR-COPY-AUTHORITY, APG-WIKI-GROUNDING-MISSING
#
# That refusal is the assignment gate working: a receipt is not obtainable
# without a genuinely resolved contract, which is exactly the property the
# receipt is supposed to certify.
#
# To close it: `scripts/assignment_process_gate_smoketest.py` builds a valid
# contract inline in `main()` (~L123-141) together with `write_wiki_evidence`.
# Extract that into a shared fixture builder -- do NOT hand-copy it here, which
# would recreate the paraphrase problem one layer down -- then emit a real
# receipt, mutate `phase_state.json` underneath it, and assert
# APG-RECEIPT-STALE: authorization is a statement about a specific state, and
# it must expire the moment that state moves.
# ==========================================================================


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
    global GATE
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gate", type=Path, default=None,
                    help="run these cases against a DIFFERENT build of the gate "
                         "(e.g. `git show c945245:scripts/full_run_contract_check.py` "
                         "written to a temp path). Historical comparison only; the "
                         "fixture registry never passes this, so a registered "
                         "evidence run is always the repository's own gate.")
    args = ap.parse_args()
    if args.gate is not None:
        GATE = args.gate.resolve()

    print("full_run_semantic_bypass_smoketest")
    print("  every case below is a way to satisfy the gate's letter and defeat its purpose")
    if GATE != REPO_GATE:
        print(f"  !! HISTORICAL COMPARISON: gate = {GATE}")
        print("  !! this run is NOT evidence about this repository")
    print()
    for fn in (case_baseline_valid_project_passes,
               case_boundary_composition_is_applicability_aware,
               case_na_m4_does_not_waive_applicable_predecessors,
               case_non_object_contract_is_refused_not_a_crash,
               case_fully_accepted_project_does_not_authorize_prose,
               case_terminal_row_missing_required_fields_is_refused,
               case_terminal_row_null_convergence_metric_is_refused,
               case_deep_pass_required_for_every_section,
               case_check8_blocker_refuses_terminal,
               case_fabricated_check8_file_is_not_evidence,
               case_malformed_phase_state_is_refused_despite_code_prefix,
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
