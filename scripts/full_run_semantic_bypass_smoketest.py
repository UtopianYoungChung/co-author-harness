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

Under the current build the anchor passes and every case below is closed --
including the rejected dispatch-preflight coverage, which an earlier cut
reported as "every bypass is closed" while its own docstring recorded that
regression as NOT COVERED. A suite that prints a stronger claim than it holds is
the same defect as a gate that does: the summary line is an assertion, and it
has to be earned like any other.

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
import assignment_fixture_support as afs  # noqa: E402


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


def _unmet(p: dict | None) -> list[str]:
    """Every `unmet` entry the terminal finding aggregated."""
    out: list[str] = []
    for f in (p or {}).get("findings", []):
        out.extend(f.get("unmet", []) or [])
    return out


def refused_for(p: dict | None, *needles: str) -> bool:
    """Did the gate refuse for THE reason this case is about?

    `rc == 4` alone is a weak assertion: every one of these fixtures is one
    edit away from a dozen unrelated terminal failures, so a case could keep
    reporting CLOSED long after the bypass it names had reopened -- passing on
    a hash drift, a fixture typo, or a neighbouring rule. The bypass is the
    thing under test, so the finding that names it is what gets asserted.
    """
    hay = " ".join(_unmet(p)) + " " + " ".join(
        f.get("message", "") for f in (p or {}).get("findings", []))
    low = hay.lower()
    return all(n.lower() in low for n in needles)


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
              rc == 4 and refused_for(p, "MF-GATE-M5", "G4_signoff.md"), f"rc={rc}")


def case_g4_failed_wording() -> None:
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        _w(proj / "reviews/G4_signoff.md",
           "# G.4\n\nstatus: FAIL\nnote: did not PASS review\n")
        rc, p = run("terminal", "--project-root", str(proj))
        check("G.4 'status: FAIL' (word PASS elsewhere) is refused",
              rc == 4 and refused_for(p, "MF-GATE-M5", "G4_signoff.md"), f"rc={rc}")


def case_artifact_hash_absent() -> None:
    """An artifact with no recorded sha256 must not satisfy exact-byte binding."""
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        mutate_state(proj, lambda st: st["milestone_framework"]["milestones"]["M4"]
                     ["artifacts"][0].pop("sha256"))
        rc, p = run("terminal", "--project-root", str(proj))
        check("M4 artifact without sha256 is refused",
              rc == 4 and refused_for(p, "MF-BINDING", "M4.artifacts[0]"), f"rc={rc}")


def case_f9_packet_hash_absent() -> None:
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        mutate_state(proj, lambda st: st["milestone_framework"]["milestones"]["M1"]
                     ["handoff"].pop("packet_sha256"))
        rc, p = run("terminal", "--project-root", str(proj))
        check("M1 F9 packet without packet_sha256 is refused",
              rc == 4 and refused_for(p, "M1", "packet"), f"rc={rc}")


def case_handoff_ready_not_consumed() -> None:
    """§4 requires CONSUMED predecessor handoffs; 'ready' is not consumed."""
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        mutate_state(proj, lambda st: st["milestone_framework"]["milestones"]["M1"]
                     ["handoff"].update({"status": "ready"}))
        rc, p = run("terminal", "--project-root", str(proj))
        check("predecessor handoff 'ready' (not consumed) is refused",
              rc == 4 and refused_for(p, "MF-GATE-CHAIN", "M1.handoff"), f"rc={rc}")


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


def case_authorized_na_m4_cannot_reach_terminal() -> None:
    """A waiver may not manufacture "ladder complete".

    An earlier cut skipped ph4_admission when M4 declared
    `applicability: not_applicable`. That is right for a MILESTONE-LOCAL
    question and wrong for a TERMINAL one: a full_lifecycle run is the user
    asking for the whole ladder, so every milestone is required BECAUSE THEY
    ASKED. Worse, the skip was reachable by the party the gate constrains -- a
    waiver that flips "ladder complete" from false to true is the original
    audit failure wearing the vocabulary of a legitimate feature.

    So this asserts the boundary itself: an N/A M4 is authorized (the ledger
    accepts it, and `milestone_framework_validate` validates it at target M4 as
    NOT_APPLICABLE) and STILL cannot produce a terminal claim.
    """
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        _authorize_na_m4(proj)
        rc, p = run("terminal", "--project-root", str(proj))
        check("authorized not_applicable M4 CANNOT reach terminal", rc == 4,
              f"rc={rc}")
        check("-> and the refusal is FRC-TERMINAL-UNPROVEN",
              "FRC-TERMINAL-UNPROVEN" in codes(p), str(codes(p)))


def case_na_m4_does_not_waive_applicable_predecessors() -> None:
    """Waiving M4 must not waive M1-M3 either -- refusal for the RIGHT reason.

    Kept alongside the boundary case above so that "N/A M4 is refused" cannot
    be satisfied by a gate that refuses N/A projects for one blanket reason: the
    predecessor breakage must still be NAMED.
    """
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        _authorize_na_m4(proj)
        mutate_state(proj, lambda st: st["milestone_framework"]["milestones"]["M1"]
                     ["handoff"].update({"status": "not_ready"}))
        rc, p = run("terminal", "--project-root", str(proj))
        unmet = " ".join(_unmet(p))
        check("N/A M4 does not waive an applicable M1 predecessor",
              rc == 4 and "M1" in unmet, f"rc={rc}")


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


def case_malformed_nested_milestone_data_is_refused_not_a_crash() -> None:
    """Truthy-but-wrong-typed nested data must produce a verdict, not a stack trace.

    `milestones`, `policy_bindings.reader_accessibility` and `check8_path` were
    read without type checks: a list is truthy, so `.get()` on it raises
    AttributeError, and a Path built from an int raises TypeError. Each escaped
    as exit 2 -- the ABSENCE of a verdict -- from the one function whose job is
    to produce one. The gate must fail CLOSED on garbage, not fall over.
    """
    mutations = (
        ("milestones is a list",
         lambda st: st["milestone_framework"].update({"milestones": [{"M1": {}}]})),
        ("milestones is a string",
         lambda st: st["milestone_framework"].update({"milestones": "M1"})),
        ("reader_accessibility binding is a list",
         lambda st: st["milestone_framework"].update(
             {"policy_bindings": {"reader_accessibility": ["nope"]}})),
        ("policy_bindings is a string",
         lambda st: st["milestone_framework"].update({"policy_bindings": "nope"})),
        ("check8_path is an int",
         lambda st: st["milestone_framework"]["milestones"]["M5"]
         ["policy_evidence"].update({"check8_path": 42})),
        ("policy_evidence is a list",
         lambda st: st["milestone_framework"]["milestones"]["M5"]
         .update({"policy_evidence": ["nope"]})),
    )
    for label, mut in mutations:
        with tempfile.TemporaryDirectory() as td:
            proj = valid_project(Path(td))
            mutate_state(proj, mut)
            rc, p = run("terminal", "--project-root", str(proj))
            check(f"malformed nested data ({label}) -> structured refusal",
                  rc == 4 and p is not None, f"rc={rc} json={p is not None}")


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
              rc == 4 and refused_for(p, "E-ROW-SHAPE-VIOLATION", "iteration_number"),
              f"rc={rc}")


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
              rc == 4 and refused_for(p, "E-T3-CONVERGENCE-NULL-AT-SIGNOFF"), f"rc={rc}")


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
              rc == 4 and refused_for(p, "MF-PHASE", "pre_mcr_deep_pass_completed",
                                      "2. Second"), f"rc={rc}")


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
        check("a consistent Check 8 BLOCKER still refuses terminal",
              rc == 4 and refused_for(p, "Check 8", "BLOCKER"), f"rc={rc}")


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
              rc == 4 and refused_for(p, "no Check 8 evidence is bound"), f"rc={rc}")


def case_malformed_section_container_is_refused_not_dropped() -> None:
    """Silently dropping malformed sections REDUCES state, and reduced state passes.

    `translate_phase_ledger` skipped any section entry that was not a dict, and
    accepted a non-dict `sections` container by yielding none. Zero sections
    then means clause g never runs for the dropped ones -- so malformed ledger
    data did not fail validation, it REMOVED itself from validation. That is
    strictly worse than a crash: a crash is visible.
    """
    for label, sections in (
        ("sections is a list", [{"heading_path": ["1"]}]),
        ("sections is a string", "not-an-object"),
        ("a section entry is a string", {"1. A": "not-an-object"}),
        ("a section entry is a list", {"1. A": []}),
    ):
        with tempfile.TemporaryDirectory() as td:
            proj = valid_project(Path(td))
            mutate_state(proj, lambda st, s=sections: st.update({"sections": s}))
            rc, p = run("terminal", "--project-root", str(proj))
            check(f"malformed phase_state ({label}) is REFUSED, not dropped",
                  rc == 4, f"rc={rc}")


def case_malformed_ledger_gives_structured_exit_2_not_a_traceback() -> None:
    """pre_phase_advance_check's contract: exit 2 on structural failure.

    The mutation is a malformed section ENTRY, not a malformed container, and
    the distinction is the test. A non-dict `sections` container never reaches
    the translator: `main()` runs `check_milestone_gate` first and
    `validate_document` legitimately refuses it as MF-STRUCTURE with exit 1 --
    a structured finding, correctly reported. A non-dict section *entry* passes
    that gate (nothing there inspects entries) and lands in the translator,
    which is precisely the path that must not escape as a traceback.

    Exit 1 means "a clause failed". A caller told that by a crash has been told
    something false about the ledger, in the vocabulary of a verdict it never
    reached.
    """
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        mutate_state(proj, lambda st: st["sections"].update({"1. Test": "oops"}))
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "pre_phase_advance_check.py"),
             "--project-root", str(proj), "--section", '["1. Test"]',
             "--target-tier", "Ph4"],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        out = (r.stdout or "") + (r.stderr or "")
        last = out.strip().splitlines()[-1][:80] if out.strip() else ""
        check("malformed section entry -> exit 2, no traceback",
              r.returncode == 2 and "Traceback" not in out,
              f"rc={r.returncode} {last}")


def case_malformed_phase_state_is_refused_despite_code_prefix() -> None:
    """phase_state_validate's codes do not all start with E."""
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        mutate_state(proj, lambda st: st.update({"sections": "not-an-object"}))
        rc, p = run("terminal", "--project-root", str(proj))
        check("malformed phase_state (non-E finding codes) is refused",
              rc == 4 and refused_for(p, "phase_state"), f"rc={rc}")


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
        check("arbitrary *mcr* filename does not satisfy MCR",
              rc == 4 and refused_for(p, "MCR admission"), f"rc={rc}")


def case_mcr_failed_verdict() -> None:
    """A file ASSERTING clearance does not clear the MCR."""
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        mutate_state(proj, _unclear_mcr)
        _w(proj / "reviews/mcr_report.md", "# MCR\n\nverdict: CLEARED\nstatus: PASS\n")
        rc, p = run("terminal", "--project-root", str(proj))
        check("an MCR file claiming CLEARED does not clear un-converged state",
              rc == 4 and refused_for(p, "MCR admission"), f"rc={rc}")


def case_final_milestone_absent() -> None:
    """A missing FINAL/M5 record must not skip the final-packet requirement."""
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        mutate_state(proj, lambda st: st["milestone_framework"]["milestones"].pop("M5"))
        rc, p = run("terminal", "--project-root", str(proj))
        check("absent FINAL/M5 record is refused (not skipped)",
              rc == 4 and refused_for(p, "MF-STRUCTURE", "'M5'"), f"rc={rc}")


def case_final_packet_unbound() -> None:
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        mutate_state(proj, lambda st: st["milestone_framework"]["milestones"]["M5"]
                     ["handoff"].pop("packet_sha256"))
        rc, p = run("terminal", "--project-root", str(proj))
        check("terminal F9 packet without hash binding is refused",
              rc == 4 and refused_for(p, "M5"), f"rc={rc}")


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
# RECEIPT / PREFLIGHT reachability -- the branches nothing used to reach.
#
# Every other authorize case stops BEFORE receipt verification and preflight:
# on a missing contract, a missing receipt, or no active target. A branch no
# test reaches is a branch whose failure mode is a guess, and these three are
# the branches that decide whether a write is authorized RIGHT NOW.
#
# They need a real READY receipt, which needs a genuinely resolved contract --
# the gate refuses a stub with nine blockers, which is the gate working. The
# contract now comes from scripts/assignment_fixture_support.py, shared with
# assignment_process_gate_smoketest, so neither suite carries its own idea of
# "valid".
# ==========================================================================
def _emit_real_receipt(proj: Path, target: str = "M1") -> tuple[Path, str]:
    """Build a gate-acceptable project and emit a genuine READY receipt."""
    afs.minimal_gate_project(proj, target=target)
    rel = f"reviews/.harness/assignment/gate_receipt_{target}_20260717T000000Z.json"
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "assignment_process_gate.py"),
         "--project-root", str(proj), "--stage", "draft",
         "--target-milestone", target, "--emit-receipt", rel],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proj / rel, (r.stdout or "") + (r.stderr or "")


def case_real_receipt_reaches_and_passes_preflight() -> None:
    """POSITIVE: a real READY receipt authorizes -- the branch is reachable.

    Without this the two negatives below could both pass on a gate that refuses
    everything, which is the vacuity trap the anchor exists to catch elsewhere.
    """
    with tempfile.TemporaryDirectory() as td:
        proj = Path(td) / "p"
        receipt, log = _emit_real_receipt(proj)
        if not receipt.is_file():
            check("a real READY receipt authorizes prose", False,
                  f"gate did not emit a receipt: {log[-160:]}")
            return
        rc, p = run("authorize", "--project-root", str(proj))
        check("a real READY receipt + passing preflight AUTHORIZES (rc=0)",
              rc == 0, f"rc={rc} {str((p or {}).get('findings'))[:110]}")


def case_receipt_goes_stale_when_state_moves() -> None:
    """The receipt is bound to phase_state BYTES: move them and it expires.

    Authorization is a statement about a specific state, not a token that keeps
    its meaning after the state changes underneath it.
    """
    with tempfile.TemporaryDirectory() as td:
        proj = Path(td) / "p"
        receipt, log = _emit_real_receipt(proj)
        if not receipt.is_file():
            check("a moved phase_state staleness the receipt", False,
                  f"gate did not emit a receipt: {log[-160:]}")
            return
        st = json.loads((proj / "reviews/phase_state.json").read_text(encoding="utf-8"))
        st["manuscript_id"] = "moved-underneath"
        _w(proj / "reviews/phase_state.json", json.dumps(st, indent=2) + "\n")
        rc, p = run("authorize", "--project-root", str(proj))
        msgs = " ".join(f.get("message", "") for f in (p or {}).get("findings", []))
        check("moving phase_state under a READY receipt makes it APG-RECEIPT-STALE",
              rc == 4 and "APG-RECEIPT-STALE" in msgs,
              f"rc={rc} {msgs[:110]}")


def case_preflight_only_rejection_is_target_mismatch() -> None:
    """A rejection that ONLY the dispatch preflight can produce.

    `authorize` cannot reach this one, and that is a property worth pinning
    rather than a gap: `verify_receipt` subsumes preflight's other checks, and
    the derived target is passed as `--expected-target`, so a mismatch is
    unreachable from there BY CONSTRUCTION. The preflight's distinct job is to
    refuse a receipt that authorizes a DIFFERENT milestone than the one about
    to be dispatched -- so it is exercised directly, with the precise code.
    """
    with tempfile.TemporaryDirectory() as td:
        proj = Path(td) / "p"
        receipt, log = _emit_real_receipt(proj, target="M1")
        if not receipt.is_file():
            check("preflight refuses a receipt for a different target", False,
                  f"gate did not emit a receipt: {log[-160:]}")
            return
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "assignment_dispatch_preflight.py"),
             "--project-root", str(proj), "--receipt", str(receipt),
             "--expected-target", "M2"],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        out = (r.stdout or "") + (r.stderr or "")
        check("preflight refuses an M1 receipt for an M2 dispatch "
              "(APG-RECEIPT-TARGET-MISMATCH)",
              r.returncode == 4 and "APG-RECEIPT-TARGET-MISMATCH" in out
              and "APG-DISPATCH-REFUSED" in out,
              f"rc={r.returncode} {out[:110]}")


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
               case_authorized_na_m4_cannot_reach_terminal,
               case_na_m4_does_not_waive_applicable_predecessors,
               case_non_object_contract_is_refused_not_a_crash,
               case_malformed_nested_milestone_data_is_refused_not_a_crash,
               case_malformed_section_container_is_refused_not_dropped,
               case_malformed_ledger_gives_structured_exit_2_not_a_traceback,
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
               case_real_receipt_reaches_and_passes_preflight,
               case_receipt_goes_stale_when_state_moves,
               case_preflight_only_rejection_is_target_mismatch,
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
