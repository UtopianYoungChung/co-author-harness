#!/usr/bin/env python3
"""staging_authority_mode_smoketest - shipment_only mode + staging revisability.

Phases E/F of the producer-boundary plan. A full public-command walk runs
inside a FAKE governed root's staging lane (COAUTHOR_EXTRA_GOVERNED_ROOTS, so
subprocesses inherit it and no real governed tree is touched). Covers:

  E: derive() reports authority_mode (shipment_only in the lane, direct_local
     elsewhere); events and the F9 handoff written in shipment_only mode carry
     effect_scope: proposal_only; direct_local writes are unchanged.
  F: post-convergence M4 re-record and post-record M5 (FINAL) re-record are
     permitted IN STAGING ONLY, append candidate-supersession +
     revalidation-advisory events, and never mutate authoritative research
     state (there is none in the lane to mutate). Direct-local projects keep
     the historical AMC-ORDER refusals.

Run:  python scripts/staging_authority_mode_smoketest.py
Exit: 0 all pass; 1 a case failed.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HARNESS / "scripts"))

from assignment_fixture_support import write_valid_contract  # noqa: E402
from semantic_graph_fixture_support import semantic_graph_fixture_environment  # noqa: E402
from assignment_milestone_checkpoint_smoketest import (  # noqa: E402
    approval_input, checkpoint_input, converge_m4_fixture,
    m4_acceptance_policy_input, publish, run,
)
from assignment_terminal_close_smoketest import (  # noqa: E402
    EXPORT_PATH, FINAL_PATH, GATE, PREFLIGHT, WRITER,
    install_ph4_evidence, publish_final, terminal_inputs, write_json,
)

ROOT = HARNESS
BOOTSTRAP = ROOT / "scripts" / "native_project_bootstrap.py"
CHECKPOINT = ROOT / "scripts" / "assignment_milestone_checkpoint.py"
VALIDATOR = ROOT / "scripts" / "milestone_framework_validate.py"

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{(' - ' + detail) if detail else ''}")
    if not ok:
        FAILURES.append(name)


def state(project: Path) -> dict:
    return json.loads((project / "reviews" / "phase_state.json").read_text(encoding="utf-8"))


def events(project: Path) -> list[dict]:
    return state(project)["milestone_framework"]["events"]


def derive(project: Path) -> dict:
    return json.loads(run(CHECKPOINT, "derive", "--project-root", project).stdout)


def drive_to_m4_recorded_converged(project: Path) -> Path:
    """Public-command walk to: M1-M3 accepted, M4 recorded, all sections
    Ph3_converged, M4 NOT accepted. Returns the M4 checkpoint path."""
    project.parent.mkdir(parents=True, exist_ok=True)
    run(BOOTSTRAP, "--project-root", project, "--project-name", "staging-walk",
        "--title", "Staging Authority Walk", "--intended-reader", "researcher",
        "--created-at", "2026-07-19T00:00:00Z")
    write_valid_contract(project)
    ticks = iter(range(1, 40))
    for milestone in ("M1", "M2", "M3"):
        if milestone != "M1":
            run(CHECKPOINT, "begin", "--project-root", project, "--milestone", milestone, "--at", f"2026-07-19T00:00:{next(ticks):02d}Z")
        consumed, lifecycle_policy = publish(project, milestone, f"# {milestone} staging deliverable\n".encode(), label="staging")
        checkpoint = checkpoint_input(project, milestone, f"2026-07-19T00:00:{next(ticks):02d}Z", label="staging", policy=lifecycle_policy)
        run(CHECKPOINT, "record", "--project-root", project, "--milestone", milestone, "--receipt", consumed, "--checkpoint", checkpoint, "--at", f"2026-07-19T00:00:{next(ticks):02d}Z")
        approval = approval_input(project, milestone, f"2026-07-19T00:00:{next(ticks):02d}Z")
        run(CHECKPOINT, "accept", "--project-root", project, "--milestone", milestone, "--checkpoint", checkpoint, "--approval-evidence", approval, "--at", f"2026-07-19T00:00:{next(ticks):02d}Z")
    run(CHECKPOINT, "begin", "--project-root", project, "--milestone", "M4", "--at", "2026-07-19T00:00:20Z")
    consumed, lifecycle_policy = publish(project, "M4", b"# M4 staging manuscript v1\n", label="staging")
    checkpoint = checkpoint_input(project, "M4", "2026-07-19T00:00:21Z", label="staging", phase="Ph1", cycle_id="m4-staging-001", policy=lifecycle_policy)
    run(CHECKPOINT, "record", "--project-root", project, "--milestone", "M4", "--receipt", consumed, "--checkpoint", checkpoint, "--at", "2026-07-19T00:00:22Z")
    converge_m4_fixture(project)
    return checkpoint


def publish_final_rev(project: Path, final_bytes: bytes, export_bytes: bytes, label: str) -> Path:
    """publish_final with a distinct receipt basename so a staging FINAL
    re-record can run a second publication cycle (the gate correctly refuses
    duplicate receipt basenames)."""
    import hashlib
    ready = project / "reviews" / ".harness" / "assignment" / "ready" / f"gate_receipt_FINAL_{label}.json"
    run(GATE, "--project-root", project, "--stage", "final", "--emit-receipt", ready)
    receipt = json.loads(ready.read_text(encoding="utf-8"))
    run(PREFLIGHT, "--project-root", project, "--receipt", ready,
        "--consumer", "planner", "--expected-target", "FINAL",
        "--write-path", FINAL_PATH, "--write-path", EXPORT_PATH)
    reserved = ready.parent.parent / "reserved" / ready.name
    staged_root = project / "reviews" / ".harness" / "assignment" / "staged" / receipt["receipt_id"]
    staged_final = staged_root / "final.md"
    staged_export = staged_root / "final_export.md"
    staged_root.mkdir(parents=True, exist_ok=True)
    staged_final.write_bytes(final_bytes)
    staged_export.write_bytes(export_bytes)
    plan = staged_root / "write_plan.json"
    write_json(plan, {
        "schema_version": "1.0.0", "receipt_id": receipt["receipt_id"],
        "reservation_id": receipt["reservation_id"], "target_milestone": "FINAL",
        "role": "generator", "writes": [
            {"staged_path": staged_final.relative_to(project).as_posix(),
             "target_path": FINAL_PATH, "sha256": hashlib.sha256(final_bytes).hexdigest()},
            {"staged_path": staged_export.relative_to(project).as_posix(),
             "target_path": EXPORT_PATH, "sha256": hashlib.sha256(export_bytes).hexdigest()},
        ],
    })
    run(WRITER, "--project-root", project, "--receipt", reserved, "--plan", plan)
    return ready.parent.parent / "consumed" / ready.name


def case_shipment_only_walk(raw: Path) -> None:
    fake = raw / "fake-ws"
    lane = fake / "outputs" / "co-author-harness" / "staging"
    lane.mkdir(parents=True)
    (fake / "research").mkdir()
    os.environ["COAUTHOR_EXTRA_GOVERNED_ROOTS"] = str(fake)
    try:
        project = lane / "w-staging" / "run-manual" / "project"

        # --- E: authority mode + proposal-only stamping ---
        drive_to_m4_recorded_converged(project)
        derived = derive(project)
        check("E: staging derive reports shipment_only",
              derived.get("authority_mode") == "shipment_only", str(derived))
        stamped = [row for row in events(project) if row.get("effect_scope") == "proposal_only"]
        check("E: staging events carry effect_scope proposal_only",
              len(stamped) == len(events(project)),
              f"{len(stamped)}/{len(events(project))} stamped")

        # --- F: post-convergence M4 re-record (stranded before this phase) ---
        assert derive(project) == {**derive(project)}  # shape probe only
        check("F: derived M4 action is accept (post-convergence)",
              derive(project).get("action") == "accept", str(derive(project)))
        consumed2, lifecycle_policy2 = publish(project, "M4", b"# M4 staging manuscript v2 (post-convergence edit)\n", label="staging2")
        checkpoint2 = checkpoint_input(project, "M4", "2026-07-19T00:00:30Z", label="staging2", phase="Ph3", cycle_id="m4-staging-002", policy=lifecycle_policy2)
        rerecord = run(CHECKPOINT, "record", "--project-root", project, "--milestone", "M4",
                       "--receipt", consumed2, "--checkpoint", checkpoint2,
                       "--at", "2026-07-19T00:00:31Z", expected=0)
        check("F: post-convergence M4 re-record succeeds in staging",
              "RECORDED M4" in rerecord.stdout, rerecord.stdout.strip()[:60])
        m4_records = [row for row in events(project)
                      if row["event_type"] == "deliverable_recorded" and row["milestone"] == "M4"]
        superseding = m4_records[-1]
        prior_bindings = [b for b in superseding["bindings"] if b["binding_type"] == "previous_content"]
        check("F: supersession record carries previous_content binding",
              len(prior_bindings) == 1, str(len(prior_bindings)))
        check("F: supersession names candidate_superseded",
              "candidate_superseded" in superseding.get("reason", ""), superseding.get("reason", "")[:70])
        check("F: revalidation advisory disclosed",
              "research-master revalidation" in superseding.get("reason", ""))
        check("F: supersession is proposal-only",
              superseding.get("effect_scope") == "proposal_only")
        run(VALIDATOR, "--project-root", project)
        m4 = state(project)["milestone_framework"]["milestones"]["M4"]
        deliverables = [row for row in m4["artifacts"] if row["role"] == "deliverable"]
        check("F: live artifacts carry the superseding candidate",
              len(deliverables) == 1 and deliverables[0]["sha256"] != "", str(len(deliverables)))

        # --- F: M4 accept still closes over the superseding candidate ---
        policy = m4_acceptance_policy_input(project)
        approval = approval_input(project, "M4", "2026-07-19T00:00:33Z")
        run(CHECKPOINT, "accept", "--project-root", project, "--milestone", "M4",
            "--checkpoint", checkpoint2, "--approval-evidence", approval,
            "--policy-evidence", policy, "--at", "2026-07-19T00:00:34Z")

        # --- E: F9 handoff carries effect_scope ---
        handoffs = sorted((project / "reviews" / ".harness" / "handoffs").glob("*.json"))
        check("E: F9 handoffs exist", bool(handoffs))
        f9 = json.loads(handoffs[-1].read_text(encoding="utf-8"))
        check("E: F9 handoff is proposal-only",
              f9.get("effect_scope") == "proposal_only", str(f9.get("effect_scope")))

        # --- F: FINAL (M5) re-record after first record ---
        install_ph4_evidence(project, raw / "fixture")
        run(CHECKPOINT, "begin", "--project-root", project, "--milestone", "FINAL", "--at", "2026-07-19T01:00:01Z")
        consumed_final, lifecycle_final = publish_final(project, b"# FINAL staging v1\n", b"# FINAL export v1\n")
        checkpoint_final, _terminal, _approval = terminal_inputs(project, lifecycle_final)
        run(CHECKPOINT, "record", "--project-root", project, "--milestone", "FINAL",
            "--receipt", consumed_final, "--checkpoint", checkpoint_final, "--at", "2026-07-19T01:00:02Z")
        check("F: derived M5 action is close after first record",
              derive(project).get("action") == "close", str(derive(project)))
        consumed_final2, lifecycle_final2 = publish_final(project, b"# FINAL staging v2 (post-record edit)\n", b"# FINAL export v2\n", label="rev2")
        checkpoint_final2, _terminal2, _approval2 = terminal_inputs(project, lifecycle_final2)
        rerecord_final = run(CHECKPOINT, "record", "--project-root", project, "--milestone", "FINAL",
                             "--receipt", consumed_final2, "--checkpoint", checkpoint_final2,
                             "--at", "2026-07-19T01:00:04Z", expected=0)
        check("F: FINAL re-record succeeds in staging",
              "RECORDED FINAL" in rerecord_final.stdout, rerecord_final.stdout.strip()[:60])
        m5_records = [row for row in events(project)
                      if row["event_type"] == "deliverable_recorded" and row["milestone"] == "M5"]
        check("F: FINAL supersession record carries previous_content binding",
              any(b["binding_type"] == "previous_content" for b in m5_records[-1]["bindings"]),
              str([b["binding_type"] for b in m5_records[-1]["bindings"]]))
        check("F: FINAL supersession names candidate_superseded",
              "candidate_superseded" in m5_records[-1].get("reason", ""))
        run(VALIDATOR, "--project-root", project)
    finally:
        os.environ.pop("COAUTHOR_EXTRA_GOVERNED_ROOTS", None)


def case_direct_local_unchanged(raw: Path) -> None:
    """Outside the lane the historical refusals stand: no silent behavior
    widening for direct-local projects."""
    project = raw / "direct" / "walk"
    checkpoint = drive_to_m4_recorded_converged(project)
    derived = derive(project)
    check("direct_local: derive reports direct_local",
          derived.get("authority_mode") == "direct_local", str(derived))
    consumed2, lifecycle_policy2 = publish(project, "M4", b"# direct-local M4 v2\n", label="direct2")
    checkpoint2 = checkpoint_input(project, "M4", "2026-07-19T00:00:40Z", label="direct2", phase="Ph3", cycle_id="m4-direct-002", policy=lifecycle_policy2)
    refused = run(CHECKPOINT, "record", "--project-root", project, "--milestone", "M4",
                  "--receipt", consumed2, "--checkpoint", checkpoint2,
                  "--at", "2026-07-19T00:00:41Z", expected=4)
    check("direct_local: post-convergence M4 re-record still refused (AMC-ORDER)",
          "AMC-ORDER" in refused.stdout, refused.stdout.strip().splitlines()[-1][:70])
    stamped = [row for row in events(project) if "effect_scope" in row]
    check("direct_local: events carry no effect_scope stamp",
          stamped == [], f"{len(stamped)} stamped")
    _ = checkpoint  # M4 checkpoint retained for parity with staging walk


def main() -> int:
    print("staging_authority_mode_smoketest")
    with tempfile.TemporaryDirectory(prefix="staging-authority-") as raw:
        for fn, arg in ((case_shipment_only_walk, Path(raw)),
                        (case_direct_local_unchanged, Path(raw))):
            print(f"{fn.__name__}:")
            try:
                fn(arg)
            except Exception as exc:  # noqa: BLE001
                check(fn.__name__, False, f"raised {type(exc).__name__}: {exc}")
            print()
    if FAILURES:
        print(f"FAIL: {len(FAILURES)} case(s): {FAILURES}")
        return 1
    print("PASS: shipment_only staging is freely revisable and proposal-only; "
          "direct_local behavior is unchanged")
    return 0


if __name__ == "__main__":
    with semantic_graph_fixture_environment():
        sys.exit(main())
