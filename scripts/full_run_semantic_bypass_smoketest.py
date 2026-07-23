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
    """Every legacy `unmet` prose line the terminal finding aggregated."""
    out: list[str] = []
    for f in (p or {}).get("findings", []):
        out.extend(f.get("unmet", []) or [])
    return out


def _unmet_findings(p: dict | None) -> list[dict]:
    """Every STRUCTURED unmet record the terminal finding aggregated."""
    out: list[dict] = []
    for f in (p or {}).get("findings", []):
        out.extend(f.get("unmet_findings", []) or [])
    return out


def refused_for(p: dict | None, code: str, path: str | None = None,
                *, message_contains: str | None = None) -> bool:
    """Did the gate refuse with THIS EXACT delegate code (and path)?

    Matches structured records, not prose. The previous version substring-matched
    a concatenation of every message -- which is the same "match a format, not a
    claim" trap this workstream just removed from `version-check.py`, turned on
    our own tests: `refused_for(p, "M5")` matched the letter M5 anywhere in any
    sentence, so a case could pass on an unrelated finding that merely mentioned
    M5, and fail the moment a delegate reworded a message it never meant to pin.

    `code` and `path` are compared EXACTLY. `message_contains` exists only for
    the few delegates that emit one code for several distinct facts (e.g.
    MF-PHASE covers both the deep pass and signoff continuity), and is a
    narrowing filter on top of an exact code -- never a substitute for one.
    """
    for rec in _unmet_findings(p):
        if rec.get("code") != code:
            continue
        if path is not None and rec.get("path") != path:
            continue
        if message_contains is not None and \
                message_contains.lower() not in str(rec.get("message", "")).lower():
            continue
        return True
    return False


def refused_with_code(p: dict | None, code: str) -> bool:
    """The gate's own top-level finding code (not a delegate's)."""
    return code in codes(p)


def _w(p: Path, text: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")
    return p


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# --- canonical terminal artefacts -----------------------------------------
# Built to the contracts the gate composes, not to what the gate happens to
# read. If a contract changes, these fail loudly rather than agreeing with a
# stale idea of the artefact.

def _findings_report(target: str, *, findings=None, counts=None,
                     schema_version="0.15.0") -> dict:
    """A payload in audit.schema's canonical shape (FindingsReport.to_dict)."""
    findings = findings if findings is not None else []
    if counts is None:
        counts = {"total": len(findings), "by_severity": {}, "by_category": {}}
        for f in findings:
            counts["by_severity"][f["severity"]] = \
                counts["by_severity"].get(f["severity"], 0) + 1
            counts["by_category"][f["category"]] = \
                counts["by_category"].get(f["category"], 0) + 1
    return {"schema_version": schema_version, "target": target,
            "findings": findings, "counts": counts}


CONVERGENCE_LOG = (
    "- iteration_index: 1\n"
    "  convergence_metric: 0.180\n"
    "  cycle_id: round_2026-07-17_001\n"
    "  profile: deep\n"
    "- iteration_index: 2\n"
    "  convergence_metric: 0.004\n"
    "  cycle_id: round_2026-07-17_001\n"
    "  profile: deep\n"
    "- finding_id: F1\n"
    "  status: RESOLVED\n"
    "  owner: user\n"
)

_COMMON_FM = (
    "schema_version: 0.7.4\n"
    "produced_at: '2026-07-17T00:00:00Z'\n"
    "produced_by: reflector\n"
    "model_used: opus-4-7\n"
    "cycle_id: round_2026-07-17_001\n"
    "iteration: 2\n"
    "section_heading_path:\n  - '1. Test'\n"
    "current_phase: Ph4\n"
    "grounding_basis:\n  - reviews/findings.json\n"
)

F4_REPORT = (
    "---\n"
    "document_type: reflector_full_report\n"
    + _COMMON_FM +
    "phase_aggregates:\n"
    "  Ph4:\n"
    "    rounds: 1\n"
    "overall_verdict: CLEAN\n"
    "---\n\n# Reflector-full close-out\n"
)

F8_REPORT = (
    "---\n"
    "artifact_family: F8\n"
    "document_type: final_round_report\n"
    "round_id: round_2026-07-17_001\n"
    "evidence_status: complete\n"
    "created_at: '2026-07-17T00:00:00Z'\n"
    "---\n\n# Final round report\n"
)


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
    # REAL terminal artefacts, not plausible filenames.
    #
    # These four used to be `{"findings": []}`, an empty convergence log, and
    # two files whose NAMES matched a glob. Each discharged one of the fifteen.
    # They are now built to the canonical contracts the gate composes:
    # audit.schema's report shape, the convergence iteration rows, F4
    # (reflector_full_report at reviews/reflection_report.md) and F8
    # (final_round_report_<round_id>.md).
    _w(proj / "reviews/findings.json", json.dumps(_findings_report(
        ledger["milestones"]["M5"]["artifacts"][0]["path"]), indent=2))
    # The fabricated `reviews/check8_evidence.json` -- `{"aggregate": "CLEAN"}`,
    # a document with no subchecks, no profile binding and no relation to the
    # manuscript -- is gone. It existed only to satisfy a `*check8*` glob.
    # `_install_reader_accessibility_policy` (via `_materialize_native_project`)
    # writes the CANONICAL sidecars at reviews/.harness/policy/{m4,m5}_check8.json
    # and binds them by hash in milestones.*.policy_evidence, which is where the
    # gate now looks.
    _w(proj / "reviews/convergence_log.md", CONVERGENCE_LOG)
    _w(proj / "reviews/ph3_convergence_signoff.md",
       "- row_timestamp: 2026-07-17T00:00:00Z\n  iteration_number: 3\n"
       "  is_terminal: true\n  is_reengagement: false\n"
       "  user_signature: user\n  user_signed_at: 2026-07-17T00:00:00Z\n"
       "  convergence_metric_value: 0.004\n  t3_verdict: CONVERGING\n"
       "  final_owner_state: closed\n")
    # `status:` lines, not `verdict:` prose -- milestone_framework_validate's
    # _signed_status is the authority for what a signoff says.
    terminal_m5 = ledger["milestones"]["M5"]
    terminal_deliverable = next(row for row in terminal_m5["artifacts"] if row["role"] == "deliverable")
    _w(
        proj / "reviews/G4_signoff.md",
        "# G.4\n\nstatus: PASS\n"
        f"manuscript_path: {terminal_deliverable['path']}\n"
        f"manuscript_sha256: {terminal_deliverable['sha256']}\n"
        "round_id: round_2026-07-17_001\n"
        "authority: evaluator\n"
        f"check8_sha256: {terminal_m5['policy_evidence']['check8_sha256']}\n"
        "safeguard_status: CLEAN\n",
    )
    _w(
        proj / "reviews/ph4_ship_signoff.md",
        "# Ph4 ship\n\nstatus: APPROVED\n"
        f"manuscript_path: {terminal_deliverable['path']}\n"
        f"manuscript_sha256: {terminal_deliverable['sha256']}\n"
        "round_id: round_2026-07-17_001\n"
        "authority: user\n",
    )
    _w(proj / "reviews/reflection_report.md", F4_REPORT)
    _w(proj / "reviews/final_round_report_round_2026-07-17_001.md", F8_REPORT)
    event_id = "round_2026-07-17_001__ph4__001"
    f7 = proj / "reviews/.harness/evidence" / f"{event_id}.json"
    _w(f7, json.dumps({
        "artifact_family": "F7", "document_type": "evidence_packet",
        "round_id": "round_2026-07-17_001", "event_id": event_id,
        "phase": "Ph4", "target": ledger["milestones"]["M5"]["artifacts"][0]["path"],
        "evidence_status": "complete", "created_at": "2026-07-17T00:00:00Z",
    }, indent=2))
    events = proj / "reviews/.harness/events.jsonl"
    _w(events, json.dumps({
        "round_id": "round_2026-07-17_001", "event_id": event_id,
        "timestamp": "2026-07-17T00:00:00Z", "phase": "Ph4",
        "event": "evidence_packet_written", "path": f7.relative_to(proj).as_posix(),
    }) + "\n")

    # Historical FINAL publication evidence. The public transaction smoketest
    # proves the producer; this semantic fixture supplies the exact immutable
    # read-side shape so bypass cases can mutate one terminal fact at a time.
    m5 = ledger["milestones"]["M5"]
    deliverable = next(row for row in m5["artifacts"] if row["role"] == "deliverable")
    export = next(row for row in m5["artifacts"] if row["role"] == "export")
    receipt_path = proj / "reviews/.harness/assignment/consumed/gate_receipt_FINAL_fixture.json"
    result_path = receipt_path.with_suffix(".result.json")
    receipt_id = "00000000-0000-4000-8000-000000000005"
    reservation_id = "00000000-0000-4000-8000-000000000006"
    _w(receipt_path, json.dumps({
        "schema_version": "1.0.0", "receipt_id": receipt_id,
        "reservation_id": reservation_id, "stage": "final",
        "target_milestone": "FINAL", "authorized_role": "generator",
        "primary_deliverable_path": deliverable["path"],
    }, indent=2))
    _w(result_path, json.dumps({
        "schema_version": "1.0.0", "receipt_id": receipt_id,
        "reservation_id": reservation_id, "outcome": "published",
        "published": [
            {"path": deliverable["path"], "sha256": deliverable["sha256"]},
            {"path": export["path"], "sha256": export["sha256"]},
        ],
    }, indent=2))
    for artifact_kind, evidence_path in (
        ("consumed_final_receipt", receipt_path),
        ("final_publication_result", result_path),
    ):
        m5["artifacts"].append({
            "role": "evidence", "artifact_kind": artifact_kind,
            "path": evidence_path.relative_to(proj).as_posix(), "sha256": _sha(evidence_path),
            "bytes": evidence_path.stat().st_size, "verified_at": "2026-07-17T00:00:00Z",
            "lineage_id": ledger["primary_lineage"],
        })

    terminal_bindings = []
    for role, path in (
        ("g4_signoff", proj / "reviews/G4_signoff.md"),
        ("ship_signoff", proj / "reviews/ph4_ship_signoff.md"),
        ("final_round_report", proj / "reviews/final_round_report_round_2026-07-17_001.md"),
        ("reflector_full", proj / "reviews/reflection_report.md"),
        ("f7_evidence", f7), ("events_log", events),
        ("findings", proj / "reviews/findings.json"),
        ("convergence_log", proj / "reviews/convergence_log.md"),
    ):
        terminal_bindings.append({"role": role, "path": path.relative_to(proj).as_posix(), "sha256": _sha(path)})
    # Universal all-drafts evidence: every accepted artifact carries separate
    # Generator and Evaluator verified envelopes bound to its exact hash.
    predecessor_packet = None
    for milestone in ("M1", "M2", "M3", "M4", "M5"):
        record = ledger["milestones"][milestone]
        artifact = next(row for row in record["artifacts"] if row.get("role") == "deliverable")
        target = "FINAL" if milestone == "M5" else milestone
        record.setdefault("policy_evidence", {})
        for field, phase, role in (
            ("draft_generation", "generation", "generator"),
            ("draft_evaluation", "evaluation", "evaluator"),
        ):
            evidence_path = proj / "reviews" / ".harness" / "shipments" / "synthetic" / f"{milestone.lower()}_{phase}.verified.json"
            _w(evidence_path, json.dumps({
                "schema_version": "1.0.0", "status": "verified",
                "phase": phase, "role": role, "target": target,
                "artifact_sha256": artifact["sha256"],
                "centroid": {"required": True}, "obligation_ids": [],
            }, indent=2))
            record["policy_evidence"][field] = {
                "evidence_path": evidence_path.relative_to(proj).as_posix(),
                "evidence_sha256": _sha(evidence_path),
            }
        if milestone != "M5" and isinstance(record.get("handoff"), dict) and record["handoff"].get("packet_path"):
            handoff_path = proj / record["handoff"]["packet_path"]
            handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
            handoff["policy_evidence"] = record["policy_evidence"]
            handoff["predecessor_packet"] = predecessor_packet
            _w(handoff_path, json.dumps(handoff, indent=2))
            record["handoff"]["packet_sha256"] = _sha(handoff_path)
            for event in ledger["events"]:
                for event_binding in event.get("bindings", []):
                    if event_binding.get("path") == record["handoff"]["packet_path"]:
                        event_binding["sha256"] = record["handoff"]["packet_sha256"]
            predecessor_packet = {
                "path": record["handoff"]["packet_path"],
                "sha256": record["handoff"]["packet_sha256"],
            }

    check8_path = proj / m5["policy_evidence"]["check8_path"]
    check8 = json.loads(check8_path.read_text(encoding="utf-8"))
    check8["cycle_id"] = "round_2026-07-17_001"
    _w(check8_path, json.dumps(check8, indent=2))
    m5["policy_evidence"]["cycle_id"] = "round_2026-07-17_001"
    m5["policy_evidence"]["check8_sha256"] = _sha(check8_path)
    m5["policy_evidence"]["terminal_round_id"] = "round_2026-07-17_001"
    _w(
        proj / "reviews/G4_signoff.md",
        "# G.4\n\nstatus: PASS\n"
        f"manuscript_path: {deliverable['path']}\n"
        f"manuscript_sha256: {deliverable['sha256']}\n"
        "round_id: round_2026-07-17_001\n"
        "authority: evaluator\n"
        f"check8_sha256: {m5['policy_evidence']['check8_sha256']}\n"
        "safeguard_status: CLEAN\n",
    )
    next(row for row in terminal_bindings if row["role"] == "g4_signoff")["sha256"] = _sha(proj / "reviews/G4_signoff.md")
    m5["policy_evidence"]["bindings"] = terminal_bindings
    packet_path = proj / m5["handoff"]["packet_path"]
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["policy_evidence"] = m5["policy_evidence"]
    packet["predecessor_packet"] = predecessor_packet
    packet["inputs_consumed"] = [
        {"path": row["path"], "sha256": row["sha256"]} for row in terminal_bindings
    ] + [
        {"path": receipt_path.relative_to(proj).as_posix(), "sha256": _sha(receipt_path)},
        {"path": result_path.relative_to(proj).as_posix(), "sha256": _sha(result_path)},
    ]
    _w(packet_path, json.dumps(packet, indent=2))
    m5["handoff"]["packet_sha256"] = _sha(packet_path)
    for event in ledger["events"]:
        if event.get("milestone") == "M5" and event.get("event_type") == "handoff_ready":
            event["bindings"] = [{"binding_type": "handoff_packet", "path": m5["handoff"]["packet_path"], "sha256": m5["handoff"]["packet_sha256"]}]
    doc = _phase_document(ledger, "Ph4")
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
              rc == 4 and refused_for(p, "MF-GATE-M5", "reviews/G4_signoff.md"),
              f"rc={rc}")


def case_g4_failed_wording() -> None:
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        _w(proj / "reviews/G4_signoff.md",
           "# G.4\n\nstatus: FAIL\nnote: did not PASS review\n")
        rc, p = run("terminal", "--project-root", str(proj))
        check("G.4 'status: FAIL' (word PASS elsewhere) is refused",
              rc == 4 and refused_for(p, "MF-GATE-M5", "reviews/G4_signoff.md"),
              f"rc={rc}")


def case_g4_status_only_is_not_a_terminal_binding() -> None:
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        _w(proj / "reviews/G4_signoff.md", "# G.4\n\nstatus: PASS\n")
        rc, payload = run("terminal", "--project-root", str(proj))
        check(
            "G.4 status-only file cannot bind the FINAL manuscript and round",
            rc == 4 and refused_for(payload, "FRC-TERMINAL-SIGNOFF-BINDING", "reviews/G4_signoff.md::manuscript_path"),
            f"rc={rc}",
        )


def case_artifact_hash_absent() -> None:
    """An artifact with no recorded sha256 must not satisfy exact-byte binding."""
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        mutate_state(proj, lambda st: st["milestone_framework"]["milestones"]["M4"]
                     ["artifacts"][0].pop("sha256"))
        rc, p = run("terminal", "--project-root", str(proj))
        check("M4 artifact without sha256 is refused",
              rc == 4 and refused_for(p, "MF-BINDING",
                                      "milestone_framework.milestones.M4.artifacts[0].path"),
              f"rc={rc}")


def case_f9_packet_hash_absent() -> None:
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        mutate_state(proj, lambda st: st["milestone_framework"]["milestones"]["M1"]
                     ["handoff"].pop("packet_sha256"))
        rc, p = run("terminal", "--project-root", str(proj))
        check("M1 F9 packet without packet_sha256 is refused",
              rc == 4 and refused_for(p, "MF-BINDING",
                                      "milestone_framework.milestones.M1.handoff.packet_path"),
              f"rc={rc}")


def case_handoff_ready_not_consumed() -> None:
    """§4 requires CONSUMED predecessor handoffs; 'ready' is not consumed."""
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        mutate_state(proj, lambda st: st["milestone_framework"]["milestones"]["M1"]
                     ["handoff"].update({"status": "ready"}))
        rc, p = run("terminal", "--project-root", str(proj))
        check("predecessor handoff 'ready' (not consumed) is refused",
              rc == 4 and refused_for(p, "MF-GATE-CHAIN",
                                      "milestone_framework.milestones.M1.handoff"),
              f"rc={rc}")


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
        check("authorized not_applicable M4 CANNOT reach terminal",
              rc == 4 and refused_with_code(p, "FRC-TERMINAL-UNPROVEN"),
              f"rc={rc}")
        check("-> ph4_admission names M4 itself (MF-GATE-M4), not a symptom",
              refused_for(p, "MF-GATE-M4", "milestone_framework.milestones.M4"),
              str([r["code"] for r in _unmet_findings(p)][:4]))


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
        check("N/A M4 does not waive an applicable M1 predecessor",
              rc == 4 and refused_for(p, "MF-GATE-CHAIN",
                                      "milestone_framework.milestones.M1.handoff"),
              f"rc={rc}")


def case_adhoc_review_refuses_prose_authorization() -> None:
    """`authorize` must not exit 0 while saying prose is forbidden.

    It returned OK plus a note reading "no prose". The note is for humans; the
    exit code is for machines; the machine was told to proceed. A gate whose
    prose and exit code disagree is enforcing the prose -- that is, nothing.
    The ad hoc review remains legal; `scope` is where its dispatch is validated.
    """
    rc, p = run("authorize", "--run-scope", "adhoc_review")
    check("authorize --run-scope adhoc_review is REFUSED (exit 4)", rc == 4,
          f"rc={rc}")
    check("-> with FRC-PROSE-FORBIDDEN",
          refused_with_code(p, "FRC-PROSE-FORBIDDEN"), str(codes(p)))
    check("-> and status is REFUSED, not OK",
          (p or {}).get("status") == "REFUSED", str((p or {}).get("status")))


def case_adhoc_dispatch_remains_legal_via_scope() -> None:
    """...and the ad hoc review itself is still legal, via the right command."""
    rc, p = run("scope", "--parent-scope", "adhoc_review", "--child-brief", "-",
                stdin="run_scope: adhoc_review\nRead §3 and report back.")
    check("a legal adhoc child under an adhoc parent still PASSES scope",
          rc == 0, f"rc={rc} {str((p or {}).get('findings'))[:80]}")


def case_omitted_run_scope_defaults_to_full_lifecycle() -> None:
    """§1.1: an omitted top-level scope resolves to full_lifecycle.

    A SAFE DEFAULT is not phrase sniffing -- they are opposites. Sniffing reads
    the request text to guess intent and guesses wrong permissively. This reads
    nothing and resolves ambiguity toward the STRICTER path: guessing
    full_lifecycle costs one bootstrap prompt the user can decline; guessing
    adhoc_review silently skips the lifecycle, which is the audit this contract
    exists to prevent.
    """
    with tempfile.TemporaryDirectory() as td:
        proj = Path(td) / "p"
        (proj / "reviews").mkdir(parents=True)
        rc_omitted, p_omitted = run("authorize", "--project-root", str(proj))
        rc_explicit, p_explicit = run("authorize", "--project-root", str(proj),
                                      "--run-scope", "full_lifecycle")
        check("omitted --run-scope behaves identically to explicit full_lifecycle",
              rc_omitted == rc_explicit and codes(p_omitted) == codes(p_explicit),
              f"omitted={rc_omitted}/{sorted(codes(p_omitted))} "
              f"explicit={rc_explicit}/{sorted(codes(p_explicit))}")
        check("-> and with no project it still FAILS CLOSED (FRC-NO-PROJECT)",
              rc_omitted == 4 and refused_with_code(p_omitted, "FRC-NO-PROJECT"),
              f"rc={rc_omitted}")
    rc_adhoc, p_adhoc = run("authorize", "--run-scope", "adhoc_review")
    check("-> adhoc_review must be EXPLICIT (it is never the default)",
          rc_adhoc == 4 and refused_with_code(p_adhoc, "FRC-PROSE-FORBIDDEN"),
          f"rc={rc_adhoc}")


def case_active_target_uses_top_level_status_not_approval_status() -> None:
    """Two fields, two facts: `status: accepted` vs `approval.status: approved`.

    Deriving the target from `approval.status != "accepted"` would match every
    correctly approved milestone -- a correct approval never says `accepted` --
    and so would always select M1, re-authorising work that is already done.
    This pins the distinction against that "fix".
    """
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        # Every applicable milestone is accepted; approvals say `approved`.
        st = json.loads((proj / "reviews/phase_state.json").read_text(encoding="utf-8"))
        ms = st["milestone_framework"]["milestones"]
        check("fixture precondition: M1 status=accepted, approval.status=approved",
              ms["M1"]["status"] == "accepted"
              and ms["M1"]["approval"]["status"] == "approved",
              f"status={ms['M1']['status']!r} "
              f"approval={ms['M1']['approval']['status']!r}")
        rc, p = run("authorize", "--project-root", str(proj))
        # Correct predicate -> no target -> FRC-NO-ACTIVE-MILESTONE.
        # Inverted predicate -> target M1 -> a receipt/contract finding instead.
        check("top-level status drives derivation (no target on a closed ladder)",
              rc == 4 and refused_with_code(p, "FRC-NO-ACTIVE-MILESTONE"),
              f"rc={rc} {sorted(codes(p))}")


def case_na_m5_cannot_reach_terminal() -> None:
    """M5 waived -> terminal refused with the exact structured code."""
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        mutate_state(proj, lambda st: st["milestone_framework"]["milestones"]["M5"]
                     .update({"applicability": "not_applicable"}))
        rc, p = run("terminal", "--project-root", str(proj))
        check("authorized not_applicable M5 CANNOT reach terminal",
              rc == 4 and refused_for(
                  p, "FRC-NA-MILESTONE-IN-FULL-LIFECYCLE",
                  "milestone_framework.milestones.M5.applicability"),
              f"rc={rc}")


def case_non_object_phase_state_is_refused_not_a_crash() -> None:
    """A JSON list/scalar/null phase_state must be a verdict, not AttributeError."""
    for payload in ("[]", '"nope"', "42", "null"):
        with tempfile.TemporaryDirectory() as td:
            proj = Path(td) / "p"
            _w(proj / "reviews/phase_state.json", payload)
            _w(proj / "reviews/assignment_contract.json", json.dumps({"status": "resolved"}))
            rc, p = run("terminal", "--project-root", str(proj))
            check(f"phase_state.json = {payload} -> structured refusal",
                  rc == 4 and refused_with_code(p, "FRC-NO-PROJECT"),
                  f"rc={rc} codes={sorted(codes(p))}")


def case_default_final_phase_must_be_recognized() -> None:
    """Default only when ABSENT; an unrecognised value is malformed, not T3.

    Coercing "Ph9" / 7 / "" to T3 let malformed state become a plausible ceiling
    and then influence the MCR disjunction as if someone had chosen it. A
    default stands in for a value nobody supplied; it does not repair a value
    someone got wrong.
    """
    import pre_phase_advance_check as _ppa

    base = {"sections": {}, "milestone_framework": {}}
    # absent -> T3
    check("absent default_final_phase -> T3",
          _ppa.translate_phase_ledger(dict(base))["default_final_tier"] == "T3")
    # valid -> mapped
    for phase, tier in (("Ph1", "T1"), ("Ph3", "T3"), ("Ph3_converged", "T3_converged"),
                        ("Ph4", "T4")):
        d = dict(base, default_final_phase=phase)
        check(f"valid default_final_phase {phase} -> {tier}",
              _ppa.translate_phase_ledger(d)["default_final_tier"] == tier)
    # unknown / scalar / null -> refused
    for bad in ("Ph9", "", 7, None, ["Ph3"]):
        d = dict(base, default_final_phase=bad)
        try:
            _ppa.translate_phase_ledger(d)
            check(f"default_final_phase {bad!r} is REFUSED", False, "no raise")
        except _ppa.LedgerTranslationError:
            check(f"default_final_phase {bad!r} is REFUSED", True)


# ==========================================================================
# TERMINAL ARTEFACTS -- four requirements that used to be satisfied by a
# filename. Every case here is a file that LOOKS right at a path that IS right.
# ==========================================================================
# ==========================================================================
# PHASE-STATE OWNER: terminal_round_id
#
# These exercise `phase_state_validate` directly, because the field is the
# PHASE STATE's to own -- the terminal gate only reads it. Putting the rule in
# the gate would have been a locally inferred rule about someone else's state,
# which is the defect this whole workstream removes.
# ==========================================================================
def _state_doc(**over) -> dict:
    doc = {
        "schema_version": "0.7.4",
        "terminal_phase_reached": False,
        "terminal_round_id": None,
        "sections": {"1. Test": {"current_phase": "Ph1", "phase_entry_log": []}},
    }
    doc.update(over)
    return doc


def _psv_codes(doc: dict) -> set[str]:
    import phase_state_validate as _psv

    findings: list = []
    _psv._validate_doc(doc, findings)
    return {getattr(f, "code", "") for f in findings}


def case_terminal_round_id_state_contract() -> None:
    """The eight state cases from the ruling, asserted by exact validator code."""
    CODE = "TERMINAL_ROUND_ID_INVALID"

    # 1. fresh nonterminal with an explicit null -> passes
    check("fresh nonterminal state with terminal_round_id: null PASSES",
          CODE not in _psv_codes(_state_doc()), str(_psv_codes(_state_doc())))

    # 2. legacy nonterminal WITHOUT the field -> still readable (additive)
    legacy = _state_doc()
    del legacy["terminal_round_id"]
    check("legacy nonterminal state without the field remains readable",
          CODE not in _psv_codes(legacy), str(_psv_codes(legacy)))

    # 3. terminal true, field missing -> fails closed
    t_missing = _state_doc(terminal_phase_reached=True)
    del t_missing["terminal_round_id"]
    check("terminal true + missing terminal_round_id FAILS",
          CODE in _psv_codes(t_missing), str(_psv_codes(t_missing)))

    # 4. terminal true, null -> fails
    check("terminal true + null terminal_round_id FAILS",
          CODE in _psv_codes(_state_doc(terminal_phase_reached=True)))

    # 5. terminal true, wrong type -> fails
    check("terminal true + non-string terminal_round_id FAILS",
          CODE in _psv_codes(_state_doc(terminal_phase_reached=True,
                                        terminal_round_id=7)))

    # 6. terminal true, malformed round syntax -> fails
    check("terminal true + malformed round syntax FAILS",
          CODE in _psv_codes(_state_doc(terminal_phase_reached=True,
                                        terminal_round_id="round-1")))

    # 7. terminal FALSE with a non-null id -> inconsistent, fails closed
    check("terminal false + non-null terminal_round_id FAILS (inconsistent)",
          CODE in _psv_codes(_state_doc(
              terminal_round_id="round_2026-07-17_001")))

    # 8. terminal true, well-formed -> passes
    good = _state_doc(terminal_phase_reached=True,
                      terminal_round_id="round_2026-07-17_001")
    check("terminal true + well-formed terminal_round_id PASSES",
          CODE not in _psv_codes(good), str(_psv_codes(good)))


# ==========================================================================
# F8 SELECTION, bound to terminal_round_id.
# ==========================================================================
BOUND = "round_2026-07-17_001"
OTHER = "round_2026-07-16_001"


def _f8_for(round_id: str) -> str:
    return F8_REPORT.replace(BOUND, round_id)


def case_f8_multi_round_project_is_permitted() -> None:
    """A real multi-round project is VALID: history is not ambiguity.

    The previous cut refused any project with two F8 reports, which rejected
    every legitimate multi-round run. Two reports are not two answers -- the
    binding says which one is the terminal round, and the other is history.
    """
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        _w(proj / f"reviews/final_round_report_{OTHER}.md", _f8_for(OTHER))
        rc, p = run("terminal", "--project-root", str(proj))
        check("two historical F8 reports PASS when one matches the binding",
              rc == 0, f"rc={rc} {str((p or {}).get('findings'))[:100]}")


def case_f8_requires_the_terminal_binding() -> None:
    """No binding -> fail closed BEFORE any selection is attempted."""
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        mutate_state(proj, lambda st: st.pop("terminal_round_id", None))
        rc, p = run("terminal", "--project-root", str(proj))
        check("a terminal ledger with no terminal_round_id FAILS CLOSED",
              rc == 4 and refused_for(p, "FRC-TERMINAL-ROUND-UNBOUND",
                                      "phase_state.terminal_round_id"),
              f"rc={rc}")


def case_f8_missing_report_for_bound_round() -> None:
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        (proj / f"reviews/final_round_report_{BOUND}.md").unlink()
        _w(proj / f"reviews/final_round_report_{OTHER}.md", _f8_for(OTHER))
        rc, p = run("terminal", "--project-root", str(proj))
        check("no report for the bound round FAILS (history does not substitute)",
              rc == 4 and refused_for(p, "FRC-ARTEFACT-ABSENT",
                                      f"reviews/final_round_report_{BOUND}.md"),
              f"rc={rc}")


def case_f8_frontmatter_must_match_the_binding() -> None:
    """Canonical filename, wrong frontmatter round_id -> refused."""
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        _w(proj / f"reviews/final_round_report_{BOUND}.md", _f8_for(OTHER))
        rc, p = run("terminal", "--project-root", str(proj))
        check("F8 frontmatter round_id != terminal_round_id FAILS",
              rc == 4 and refused_for(
                  p, "FRC-ARTEFACT-ROUND-MISMATCH",
                  f"reviews/final_round_report_{BOUND}.md::round_id"),
              f"rc={rc}")


def case_f8_ambiguity_only_among_bound_round_claimants() -> None:
    """A SECOND file claiming the bound round is ambiguity; history is not."""
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        # a differently named file whose frontmatter claims the bound round
        _w(proj / "reviews/final_round_report_round_2026-07-99_001.md", F8_REPORT)
        rc, p = run("terminal", "--project-root", str(proj))
        check("a second file claiming the bound round FAILS as ambiguous",
              rc == 4 and refused_for(p, "FRC-ARTEFACT-AMBIGUOUS"), f"rc={rc}")


def case_f8_selected_report_still_validates() -> None:
    """Selection is not a substitute for validation."""
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        _w(proj / f"reviews/final_round_report_{BOUND}.md",
           F8_REPORT.replace("evidence_status: complete", "evidence_status: bogus"))
        rc, p = run("terminal", "--project-root", str(proj))
        check("the SELECTED F8 still fails through artefact_frontmatter_validate",
              rc == 4 and refused_for(
                  p, "R-Refl-FM-2",
                  f"reviews/final_round_report_{BOUND}.md::evidence_status"),
              f"rc={rc}")


def case_findings_json_must_be_a_real_report() -> None:
    """`{"findings": []}` and an empty file both used to discharge requirement 8."""
    target = "reviews/M5 canonical deliverable"  # replaced per-case below
    cases = (
        ("empty object", {}, "AUDIT-REPORT-SCHEMA-VERSION", "reviews/findings.json::schema_version"),
        ("a JSON list", [], "AUDIT-REPORT-NOT-OBJECT", "reviews/findings.json::$"),
        ("the old {'findings': []} stub", {"findings": []},
         "AUDIT-REPORT-SCHEMA-VERSION", "reviews/findings.json::schema_version"),
        ("wrong schema_version",
         {"schema_version": "0.1.0", "target": "t", "findings": [], "counts": {}},
         "AUDIT-REPORT-SCHEMA-VERSION", "reviews/findings.json::schema_version"),
        ("empty target",
         {"schema_version": "0.15.0", "target": "", "findings": [],
          "counts": {"total": 0, "by_severity": {}, "by_category": {}}},
         "AUDIT-REPORT-TARGET-EMPTY", "reviews/findings.json::target"),
        ("findings not a list",
         {"schema_version": "0.15.0", "target": "t", "findings": {}, "counts": {}},
         "AUDIT-REPORT-FINDINGS-NOT-LIST", "reviews/findings.json::findings"),
    )
    for label, payload, code, where in cases:
        with tempfile.TemporaryDirectory() as td:
            proj = valid_project(Path(td))
            _w(proj / "reviews/findings.json", json.dumps(payload))
            rc, p = run("terminal", "--project-root", str(proj))
            check(f"findings.json {label} is REFUSED",
                  rc == 4 and refused_for(p, code, where), f"rc={rc}")


def case_findings_json_row_and_count_integrity() -> None:
    """A report whose counts disagree with its findings is lying about itself."""
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        deliverable = json.loads(
            (proj / "reviews/phase_state.json").read_text(encoding="utf-8")
        )["milestone_framework"]["milestones"]["M5"]["artifacts"][0]["path"]
        row = {"check_id": "c1", "category": "style", "severity": "default",
               "locator": "milestones/M4_complete_paper_draft.md:1", "evidence": "e", "rule_ref": "r",
               "tentative": False}

        # counts lie about the findings
        bad = _findings_report(deliverable, findings=[row],
                               counts={"total": 0, "by_severity": {}, "by_category": {}})
        _w(proj / "reviews/findings.json", json.dumps(bad))
        rc, p = run("terminal", "--project-root", str(proj))
        check("findings.json with recomputed-count mismatch is REFUSED",
              rc == 4 and refused_for(p, "AUDIT-REPORT-COUNTS-MISMATCH",
                                      "reviews/findings.json::counts"), f"rc={rc}")

        # an illegal enum
        bad_row = dict(row, severity="catastrophic")
        _w(proj / "reviews/findings.json",
           json.dumps(_findings_report(deliverable, findings=[bad_row])))
        rc, p = run("terminal", "--project-root", str(proj))
        check("findings.json with an illegal severity is REFUSED",
              rc == 4 and refused_for(p, "AUDIT-FINDING-SEVERITY",
                                      "reviews/findings.json::findings[0].severity"),
              f"rc={rc}")

        # a report about ANOTHER manuscript
        _w(proj / "reviews/findings.json",
           json.dumps(_findings_report("some/other/paper.md")))
        rc, p = run("terminal", "--project-root", str(proj))
        check("a valid report about ANOTHER target is REFUSED",
              rc == 4 and refused_for(p, "AUDIT-REPORT-TARGET-MISMATCH",
                                      "reviews/findings.json::target"), f"rc={rc}")


def case_convergence_log_must_be_a_real_record() -> None:
    """An empty or arbitrary Markdown file used to discharge requirement 9."""
    cases = (
        ("empty file", "", "CONV-LOG-EMPTY"),
        ("arbitrary prose", "# notes\n\nlooks convergent to me\n", "CONV-LOG-NO-RECORDS"),
        ("no iteration rows (findings only)",
         "- finding_id: F1\n  status: RESOLVED\n", "CONV-LOG-NO-ITERATIONS"),
        ("iteration row missing convergence_metric",
         "- iteration_index: 1\n  cycle_id: round_2026-07-17_001\n",
         "CONV-ROW-FIELD-MISSING"),
        ("iteration row with null metric",
         "- iteration_index: 1\n  convergence_metric: null\n", "CONV-ROW-METRIC-NULL"),
    )
    for label, body, code in cases:
        with tempfile.TemporaryDirectory() as td:
            proj = valid_project(Path(td))
            _w(proj / "reviews/convergence_log.md", body)
            rc, p = run("terminal", "--project-root", str(proj))
            check(f"convergence_log {label} is REFUSED",
                  rc == 4 and refused_for(p, code), f"rc={rc}")


def case_convergence_unresolved_transfer_is_refused() -> None:
    """Linear-Accountability: an open owner at the moment of shipping."""
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        _w(proj / "reviews/convergence_log.md",
           CONVERGENCE_LOG + "- finding_id: F2\n  transferred_to: evaluator\n"
                             "  transfer_rationale:\n")
        rc, p = run("terminal", "--project-root", str(proj))
        check("convergence_log with an unresolved transfer is REFUSED",
              rc == 4 and refused_for(p, "CONV-TRANSFER-UNRESOLVED"), f"rc={rc}")


def case_f4_must_be_a_real_reflector_full_report() -> None:
    """`reflector_full_2026-07-17.md` was a NAME, not an artefact."""
    cases = (
        ("absent", None, "FRC-ARTEFACT-ABSENT", "reviews/"),
        # A file with no extractable frontmatter block is UNREADABLE as the
        # family, not merely the wrong family: there is nothing to read a
        # document_type out of. `validate_path` returns [] for it -- "nothing I
        # recognised" -- which is exactly why identity is asserted here.
        ("empty file", "", "FRC-ARTEFACT-UNREADABLE", "reviews/reflection_report.md"),
        ("no frontmatter", "# Reflector-full close-out\n",
         "FRC-ARTEFACT-UNREADABLE", "reviews/reflection_report.md"),
        ("wrong family", "---\ndocument_type: evaluator_findings\n---\n\nx\n",
         "FRC-ARTEFACT-WRONG-FAMILY", "reviews/reflection_report.md::document_type"),
    )
    for label, body, code, where in cases:
        with tempfile.TemporaryDirectory() as td:
            proj = valid_project(Path(td))
            target = proj / "reviews/reflection_report.md"
            if body is None:
                target.unlink()
            else:
                _w(target, body)
            rc, p = run("terminal", "--project-root", str(proj))
            check(f"F4 {label} is REFUSED",
                  rc == 4 and refused_for(p, code, where), f"rc={rc}")


def case_f4_validator_findings_are_refused() -> None:
    """A real F4 that the AUTHORITY rejects must not pass."""
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        _w(proj / "reviews/reflection_report.md",
           F4_REPORT.replace("overall_verdict: CLEAN", "overall_verdict: NONSENSE"))
        rc, p = run("terminal", "--project-root", str(proj))
        check("F4 with an illegal overall_verdict is REFUSED (validator finding)",
              rc == 4 and any(r["source"] == "reflector"
                              for r in _unmet_findings(p)), f"rc={rc}")


def case_f8_must_be_a_real_final_round_report() -> None:
    """`f8_final_round_report.md` matched a glob and said nothing."""
    cases = (
        # The bound path, not a bare directory: the gate now knows exactly
        # which report it is missing.
        ("absent", None, None, "FRC-ARTEFACT-ABSENT",
         "reviews/final_round_report_round_2026-07-17_001.md"),
        ("filename only, no frontmatter",
         "final_round_report_round_2026-07-17_001.md", "# F8 final round\n",
         "FRC-ARTEFACT-UNREADABLE",
         "reviews/final_round_report_round_2026-07-17_001.md"),
        ("wrong family",
         "final_round_report_round_2026-07-17_001.md",
         "---\ndocument_type: reflector_full_report\n---\n\nx\n",
         "FRC-ARTEFACT-WRONG-FAMILY",
         "reviews/final_round_report_round_2026-07-17_001.md::document_type"),
    )
    for label, name, body, code, where in cases:
        with tempfile.TemporaryDirectory() as td:
            proj = valid_project(Path(td))
            (proj / "reviews/final_round_report_round_2026-07-17_001.md").unlink()
            if name is not None:
                _w(proj / "reviews" / name, body)
            rc, p = run("terminal", "--project-root", str(proj))
            check(f"F8 {label} is REFUSED",
                  rc == 4 and refused_for(p, code, where), f"rc={rc}")


def case_f8_incomplete_evidence_is_refused() -> None:
    """`evidence_status` is the F8 dispatcher's call, not a filename's."""
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        _w(proj / "reviews/final_round_report_round_2026-07-17_001.md",
           F8_REPORT.replace("artifact_family: F8", "artifact_family: F1"))
        rc, p = run("terminal", "--project-root", str(proj))
        check("F8 with the wrong artifact_family is REFUSED",
              rc == 4 and refused_for(p, "R-Refl-FM-2",
                                      "reviews/final_round_report_round_2026-07-17_001.md"
                                      "::artifact_family"), f"rc={rc}")
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        _w(proj / "reviews/final_round_report_round_2026-07-17_001.md",
           F8_REPORT.replace("evidence_status: complete", "evidence_status: bogus"))
        rc, p = run("terminal", "--project-root", str(proj))
        check("F8 with an illegal evidence_status is REFUSED",
              rc == 4 and refused_for(p, "R-Refl-FM-2",
                                      "reviews/final_round_report_round_2026-07-17_001.md"
                                      "::evidence_status"), f"rc={rc}")


def case_non_object_f7_is_refused_not_a_crash() -> None:
    """A JSON F7 array is malformed evidence, not permission to traceback."""
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        state_path = proj / "reviews/phase_state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        bindings = state["milestone_framework"]["milestones"]["M5"]["policy_evidence"]["bindings"]
        f7_binding = next(row for row in bindings if row["role"] == "f7_evidence")
        f7_path = proj / f7_binding["path"]
        _w(f7_path, "[]\n")
        f7_binding["sha256"] = _sha(f7_path)
        _w(state_path, json.dumps(state, indent=1))
        rc, p = run("terminal", "--project-root", str(proj))
        check("non-object F7 is REFUSED without a traceback",
              rc == 4 and refused_for(p, "FRC-ARTEFACT-UNREADABLE", f7_binding["path"]),
              f"rc={rc}")


# RETIRED: `case_ambiguous_f8_candidates_are_refused`.
#
# It asserted that ANY two F8 reports are ambiguous, which was the Major: it
# refused every legitimate multi-round project, because it treated the record of
# getting to the end as competing claims about the end. That was never a
# property worth pinning -- it was the absence of a binding, expressed as a
# refusal.
#
# Its intent survives, split according to what is actually true:
#   case_f8_multi_round_project_is_permitted            history is permitted
#   case_f8_ambiguity_only_among_bound_round_claimants  two claims on the BOUND
#                                                       round are ambiguous


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
                  rc == 4 and refused_with_code(p, "FRC-TERMINAL-UNPROVEN")
                  and any(r["code"].startswith("FRC-CHECK8-")
                          or r["source"] in {"phase_state", "ph1_to_ph2"}
                          for r in _unmet_findings(p)),
                  f"rc={rc} codes={sorted(codes(p))}")


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
              rc == 4 and refused_for(p, "E-ROW-SHAPE-VIOLATION",
                                      message_contains="iteration_number"),
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
              rc == 4 and refused_for(p, "E-T3-CONVERGENCE-NULL-AT-SIGNOFF"),
              f"rc={rc}")


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
              rc == 4 and refused_for(
                  p, "MF-PHASE",
                  "sections['2. Second'].pre_mcr_deep_pass_completed"),
              f"rc={rc}")


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
              rc == 4 and refused_for(p, "FRC-CHECK8-BLOCKER"), f"rc={rc}")


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
              rc == 4 and refused_for(p, "FRC-CHECK8-UNBOUND"), f"rc={rc}")


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
                  rc == 4 and refused_with_code(p, "FRC-TERMINAL-UNPROVEN")
                  and (refused_for(p, "FRC-LEDGER-MALFORMED",
                                   "reviews/phase_state.json")
                       or any(r["source"] == "phase_state"
                              for r in _unmet_findings(p))),
                  f"rc={rc} codes={[r['code'] for r in _unmet_findings(p)][:3]}")


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


def case_malformed_entry_log_gives_structured_exit_2() -> None:
    """phase_entry_log is not incidental -- coercing it to [] erases evidence.

    Clause g validates every row in it, and the Ph4 MCR admission proof surface
    IS a row in it. A malformed container coerced to `[]` handed clause g
    nothing to reject and deleted the admission record in the same gesture: the
    ledger would then read as a section that had simply never transitioned,
    which is a story about the project told by a parsing shortcut.

    Both the container and each entry are checked, through the CLI, because the
    contract being pinned is `load_ledger`'s exit code -- exit 2 for a
    structural failure, and never a traceback.
    """
    for label, mutate in (
        ("phase_entry_log is a string",
         lambda st: st["sections"]["1. Test"].update({"phase_entry_log": "nope"})),
        ("phase_entry_log is an object",
         lambda st: st["sections"]["1. Test"].update({"phase_entry_log": {"a": 1}})),
        ("a phase_entry_log row is a string",
         lambda st: st["sections"]["1. Test"].update({"phase_entry_log": ["nope"]})),
        ("a phase_entry_log row is a list",
         lambda st: st["sections"]["1. Test"].update({"phase_entry_log": [[]]})),
    ):
        with tempfile.TemporaryDirectory() as td:
            proj = valid_project(Path(td))
            mutate_state(proj, mutate)
            r = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "pre_phase_advance_check.py"),
                 "--project-root", str(proj), "--section", '["1. Test"]',
                 "--target-tier", "Ph4"],
                capture_output=True, text=True, encoding="utf-8", errors="replace")
            out = (r.stdout or "") + (r.stderr or "")
            check(f"{label} -> exit 2, no traceback",
                  r.returncode == 2 and "Traceback" not in out,
                  f"rc={r.returncode}")


def case_malformed_entry_log_refuses_terminal() -> None:
    """...and the full-run gate turns that same refusal into a terminal finding."""
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        mutate_state(proj, lambda st: st["sections"]["1. Test"]
                     .update({"phase_entry_log": "nope"}))
        rc, p = run("terminal", "--project-root", str(proj))
        check("malformed phase_entry_log refuses terminal (FRC-LEDGER-MALFORMED)",
              rc == 4 and refused_for(p, "FRC-LEDGER-MALFORMED",
                                      "reviews/phase_state.json"),
              f"rc={rc} {[r['code'] for r in _unmet_findings(p)][:3]}")


def case_malformed_phase_state_is_refused_despite_code_prefix() -> None:
    """phase_state_validate's codes do not all start with E."""
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        mutate_state(proj, lambda st: st.update({"sections": "not-an-object"}))
        rc, p = run("terminal", "--project-root", str(proj))
        check("malformed phase_state (non-E finding codes) is refused",
              rc == 4 and any(r["source"] == "phase_state"
                              for r in _unmet_findings(p)), f"rc={rc}")


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
              rc == 4 and refused_for(p, "MF-PHASE", "sections",
                                      message_contains="MCR admission"),
              f"rc={rc}")


def case_mcr_failed_verdict() -> None:
    """A file ASSERTING clearance does not clear the MCR."""
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        mutate_state(proj, _unclear_mcr)
        _w(proj / "reviews/mcr_report.md", "# MCR\n\nverdict: CLEARED\nstatus: PASS\n")
        rc, p = run("terminal", "--project-root", str(proj))
        check("an MCR file claiming CLEARED does not clear un-converged state",
              rc == 4 and refused_for(p, "MF-PHASE", "sections",
                                      message_contains="MCR admission"),
              f"rc={rc}")


def case_final_milestone_absent() -> None:
    """A missing FINAL/M5 record must not skip the final-packet requirement."""
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        mutate_state(proj, lambda st: st["milestone_framework"]["milestones"].pop("M5"))
        rc, p = run("terminal", "--project-root", str(proj))
        check("absent FINAL/M5 record is refused (not skipped)",
              rc == 4 and refused_for(p, "MF-STRUCTURE", "milestone_framework.milestones",
                                      message_contains="'M5'"),
              f"rc={rc}")


def case_terminal_state_without_final_publication_is_refused() -> None:
    """Hand-built terminal state/F9 cannot authenticate a missing FINAL write."""
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        mutate_state(proj, lambda st: st["milestone_framework"]["milestones"]["M5"].update({
            "artifacts": [
                row for row in st["milestone_framework"]["milestones"]["M5"]["artifacts"]
                if row.get("artifact_kind") not in {"consumed_final_receipt", "final_publication_result"}
            ]
        }))
        rc, payload = run("terminal", "--project-root", str(proj))
        check(
            "terminal state and F9 without consumed FINAL receipt/result are refused",
            rc == 4 and refused_for(payload, "FRC-FINAL-PUBLICATION-ABSENT", "milestone_framework.milestones.M5.artifacts"),
            f"rc={rc}",
        )


def case_final_packet_unbound() -> None:
    with tempfile.TemporaryDirectory() as td:
        proj = valid_project(Path(td))
        mutate_state(proj, lambda st: st["milestone_framework"]["milestones"]["M5"]
                     ["handoff"].pop("packet_sha256"))
        rc, p = run("terminal", "--project-root", str(proj))
        check("terminal F9 packet without hash binding is refused",
              rc == 4 and refused_for(p, "MF-BINDING",
                                      "milestone_framework.milestones.M5.handoff.packet_path"),
              f"rc={rc}")


# ==========================================================================
# AUTHORSHIP bypasses  (CodeRabbit :364)
# ==========================================================================
def case_empty_revision_log_is_not_authorship() -> None:
    """A filename is not evidence. An EMPTY log must not attribute prose."""
    with tempfile.TemporaryDirectory() as td:
        proj = Path(td) / "p"
        _w(proj / "milestones/M4_complete_paper_draft.md", "# Essay\n\nProse nobody wrote.\n")
        _w(proj / "manuscript/revision_log.md", "")
        rc, p = run("authorship", "--project-root", str(proj))
        check("empty revision_log.md does not establish authorship",
              rc == 4 and refused_with_code(p, "FRC-AUTHORSHIP"), f"rc={rc}")


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
        _w(proj / "milestones/M4_complete_paper_draft.md", "# Essay\n\nProse.\n")
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
              rc == 4 and refused_with_code(p, "FRC-AUTHORSHIP"), f"rc={rc}")


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
    rel = f"reviews/.harness/assignment/ready/gate_receipt_{target}_20260717T000000Z.json"
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "assignment_process_gate.py"),
         "--project-root", str(proj), "--stage", "draft",
         "--target-milestone", target, "--emit-receipt", rel],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proj / rel, (r.stdout or "") + (r.stderr or "")


def case_real_receipt_reaches_and_passes_preflight() -> None:
    """POSITIVE: a real READY receipt passes read-only authorization readiness.

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
        check("a real READY receipt passes authorization readiness (rc=0)",
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
             "--expected-target", "M2", "--consumer", "planner",
             "--write-path", "milestones/M1_project_memo.md"],
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
        _w(proj / "milestones/M4_complete_paper_draft.md", "# Essay\n\nProse nobody wrote.\n")
        _w(proj / "manuscript/revision_log.md", "today I had a sandwich\n")
        rc, p = run("authorship", "--project-root", str(proj))
        check("fabricated revision_log content does not establish authorship",
              rc == 4 and refused_with_code(p, "FRC-AUTHORSHIP"), f"rc={rc}")


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
        check("contract with NO status field is refused",
              rc == 4 and refused_with_code(p, "FRC-CONTRACT-MISSING"), f"rc={rc}")


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
              rc == 4 and refused_with_code(p, "FRC-CONTRACT-MISSING"), f"rc={rc}")


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
          rc == 4 and refused_with_code(p, "FRC-SCOPE-ESCALATION"), f"rc={rc}")


def case_undeclared_child_not_allowed() -> None:
    """--allow-undeclared-child must not let an undeclared child through."""
    rc, p = run("scope", "--parent-scope", "full_lifecycle", "--child-brief", "-",
                "--allow-undeclared-child",
                stdin="Please look at section 3 and report back.")
    check("--allow-undeclared-child cannot bypass the declaration requirement",
          rc == 4 and refused_with_code(p, "FRC-SCOPE-UNDECLARED"), f"rc={rc}")


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
               case_na_m5_cannot_reach_terminal,
               case_adhoc_review_refuses_prose_authorization,
               case_adhoc_dispatch_remains_legal_via_scope,
               case_omitted_run_scope_defaults_to_full_lifecycle,
               case_active_target_uses_top_level_status_not_approval_status,
               case_non_object_phase_state_is_refused_not_a_crash,
               case_default_final_phase_must_be_recognized,
               case_na_m4_does_not_waive_applicable_predecessors,
               case_terminal_round_id_state_contract,
               case_f8_multi_round_project_is_permitted,
               case_f8_requires_the_terminal_binding,
               case_f8_missing_report_for_bound_round,
               case_f8_frontmatter_must_match_the_binding,
               case_f8_ambiguity_only_among_bound_round_claimants,
               case_f8_selected_report_still_validates,
               case_findings_json_must_be_a_real_report,
               case_findings_json_row_and_count_integrity,
               case_convergence_log_must_be_a_real_record,
               case_convergence_unresolved_transfer_is_refused,
               case_f4_must_be_a_real_reflector_full_report,
               case_f4_validator_findings_are_refused,
               case_f8_must_be_a_real_final_round_report,
               case_f8_incomplete_evidence_is_refused,
               case_non_object_f7_is_refused_not_a_crash,
               case_non_object_contract_is_refused_not_a_crash,
               case_malformed_nested_milestone_data_is_refused_not_a_crash,
               case_malformed_section_container_is_refused_not_dropped,
               case_malformed_ledger_gives_structured_exit_2_not_a_traceback,
               case_malformed_entry_log_gives_structured_exit_2,
               case_malformed_entry_log_refuses_terminal,
               case_fully_accepted_project_does_not_authorize_prose,
               case_terminal_row_missing_required_fields_is_refused,
               case_terminal_row_null_convergence_metric_is_refused,
               case_deep_pass_required_for_every_section,
               case_check8_blocker_refuses_terminal,
               case_fabricated_check8_file_is_not_evidence,
               case_malformed_phase_state_is_refused_despite_code_prefix,
               case_g4_not_pass_substring, case_g4_failed_wording,
               case_g4_status_only_is_not_a_terminal_binding,
               case_artifact_hash_absent, case_f9_packet_hash_absent,
               case_handoff_ready_not_consumed, case_mcr_filename_glob,
               case_mcr_failed_verdict, case_final_milestone_absent,
               case_terminal_state_without_final_publication_is_refused,
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
    from semantic_graph_fixture_support import semantic_graph_fixture_environment
    with semantic_graph_fixture_environment():
        sys.exit(main())
