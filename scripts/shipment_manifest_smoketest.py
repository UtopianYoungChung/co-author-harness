#!/usr/bin/env python3
"""shipment_manifest_smoketest - staging run lifecycle + shipment contract.

Phase D of the producer-boundary plan. Hermetic: a fake governed root supplied
via COAUTHOR_EXTRA_GOVERNED_ROOTS hosts the staging lane, so every write lands
in a temp tree. Covers: run creation (collision-resistant ids, five-directory
layout, refusal outside the lane, fail-closed when ungoverned), immutable
input snapshots, exclusive byte-verified shipment emission, manifest
round-trip validation, tamper detection, and application-receipt recognition
(absence means NOT applied).

Run:  python scripts/shipment_manifest_smoketest.py
Exit: 0 all pass; 1 a case failed.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HARNESS / "scripts"))

import destination_capability as dc  # noqa: E402
import staging_run as sr  # noqa: E402

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{(' - ' + detail) if detail else ''}")
    if not ok:
        FAILURES.append(name)


def fake_root(base: Path) -> Path:
    fake = base / "fake-ws"
    (fake / "outputs" / "co-author-harness" / "staging").mkdir(parents=True)
    (fake / "research").mkdir(parents=True)
    return fake


def case_run_creation() -> None:
    with tempfile.TemporaryDirectory(prefix="shpd-") as td:
        fake = fake_root(Path(td))
        os.environ["COAUTHOR_EXTRA_GOVERNED_ROOTS"] = str(fake)
        try:
            lane = fake / "outputs" / "co-author-harness" / "staging"
            run1 = sr.create_run("w-test", staging_root=lane)
            run2 = sr.create_run("w-test", staging_root=lane)
            check("run dir under the lane", str(run1).startswith(str(lane)))
            check("run-id pattern", run1.name.startswith("run-") and len(run1.name) == 29,
                  run1.name)
            check("collision-resistant ids", run1.name != run2.name)
            layout = {"inputs", "work", "state", "evidence", "shipment"}
            check("five-directory layout",
                  {p.name for p in run1.iterdir() if p.is_dir()} == layout)
            refused = None
            try:
                sr.create_run("w-test", staging_root=fake / "research" / "not-a-lane")
            except dc.DestinationRefused as exc:
                refused = exc
            check("refuses a run outside the staging lane",
                  refused is not None and refused.code == dc.DEST_PROTECTED)
        finally:
            os.environ.pop("COAUTHOR_EXTRA_GOVERNED_ROOTS", None)


def case_ungoverned_fails_closed() -> None:
    # staging_run imports the resolver by value, so suppress both module
    # bindings.  This keeps the negative case genuinely ungoverned even as the
    # capability kernel independently discovers manifests from destinations.
    real_dc = dc.discovered_workspace_root
    real_sr = sr.discovered_workspace_root
    dc.discovered_workspace_root = lambda: None
    sr.discovered_workspace_root = lambda: None
    os.environ.pop("COAUTHOR_EXTRA_GOVERNED_ROOTS", None)
    try:
        refused = None
        try:
            sr.create_run("w-test")
        except dc.DestinationRefused as exc:
            refused = exc
        check("no governed root: create_run fails closed",
              refused is not None and refused.code == dc.DEST_UNGOVERNED)
    finally:
        dc.discovered_workspace_root = real_dc
        sr.discovered_workspace_root = real_sr


def case_input_snapshots() -> None:
    with tempfile.TemporaryDirectory(prefix="shpd-") as td:
        fake = fake_root(Path(td))
        os.environ["COAUTHOR_EXTRA_GOVERNED_ROOTS"] = str(fake)
        try:
            lane = fake / "outputs" / "co-author-harness" / "staging"
            run = sr.create_run("w-test", staging_root=lane)
            src = Path(td) / "source.md"
            src.write_bytes(b"allowlisted input bytes\n")
            entry = sr.snapshot_input(run, src)
            snap = run / entry["snapshot_path"]
            check("snapshot bytes equal source", snap.read_bytes() == src.read_bytes())
            check("snapshot hash recorded", entry["sha256"] == sr.sha256_file(src))
            check("snapshot is a regular file, not a link",
                  snap.is_file() and not snap.is_symlink())
            check("snapshot read-only", not os.access(snap, os.W_OK))
            src.write_bytes(b"MUTATED AFTER SNAPSHOT\n")
            check("later source mutation does not reach the snapshot",
                  snap.read_bytes() == b"allowlisted input bytes\n")
        finally:
            os.environ.pop("COAUTHOR_EXTRA_GOVERNED_ROOTS", None)


def case_shipment_roundtrip() -> None:
    with tempfile.TemporaryDirectory(prefix="shpd-") as td:
        fake = fake_root(Path(td))
        os.environ["COAUTHOR_EXTRA_GOVERNED_ROOTS"] = str(fake)
        try:
            lane = fake / "outputs" / "co-author-harness" / "staging"
            run = sr.create_run("w-test", staging_root=lane)
            src = Path(td) / "in.md"
            src.write_bytes(b"input\n")
            sr.snapshot_input(run, src)
            (run / "work" / "candidate.md").write_bytes(b"candidate prose\n")
            (run / "state" / "ledger.json").write_bytes(b"{\"status\": \"production_ready\"}\n")
            ops = [{"op": "create",
                    "destination": "research/60_Workbench/w-test/manuscript/candidate.md",
                    "artifact": "work/candidate.md"}]
            manifest_path = sr.emit_shipment(
                run, proposed_operations=ops,
                limitations=["hermetic test shipment"], unresolved_findings=[])
            doc = json.loads(manifest_path.read_text(encoding="utf-8"))
            problems = sr.validate_manifest(doc)
            check("emitted manifest validates", problems == [], str(problems[:2]))
            check("effect_scope is proposal_only", doc["effect_scope"] == "proposal_only")
            check("proposed op carries artifact hash",
                  doc["proposed_operations"][0]["sha256"] == sr.sha256_file(run / "work" / "candidate.md"))
            check("artifacts inventory covers state ledger",
                  any(a["path"] == "state/ledger.json" for a in doc["artifacts"]))
            verify = sr.verify_shipment(run)
            check("verify_shipment green on intact run", verify == [])
            second = None
            try:
                sr.emit_shipment(run, proposed_operations=ops,
                                 limitations=[], unresolved_findings=[])
            except FileExistsError:
                second = "refused"
            check("second emission refused (exclusive create)", second == "refused")
            (run / "work" / "candidate.md").write_bytes(b"tampered after emission\n")
            tampered = sr.verify_shipment(run)
            check("tamper after emission detected",
                  any("work/candidate.md" in p for p in tampered), str(tampered[:1]))
        finally:
            os.environ.pop("COAUTHOR_EXTRA_GOVERNED_ROOTS", None)


def case_application_receipt() -> None:
    with tempfile.TemporaryDirectory(prefix="shpd-") as td:
        fake = fake_root(Path(td))
        os.environ["COAUTHOR_EXTRA_GOVERNED_ROOTS"] = str(fake)
        try:
            lane = fake / "outputs" / "co-author-harness" / "staging"
            run = sr.create_run("w-test", staging_root=lane)
            sr.emit_shipment(run, proposed_operations=[],
                             limitations=[], unresolved_findings=[])
            check("fresh shipment is NOT applied", not sr.is_applied(run))
            missing = None
            try:
                sr.recognize_application_receipt(run, Path(td) / "no-such-receipt.json")
            except FileNotFoundError:
                missing = "refused"
            check("recognition refuses a missing receipt", missing == "refused")
            receipt = Path(td) / "receipt.json"
            receipt.write_text('{"applied": true, "authority": "research-governance"}',
                               encoding="utf-8")
            sr.recognize_application_receipt(run, receipt)
            check("recognized shipment reports applied", sr.is_applied(run))
            echo = json.loads((run / "shipment" / "APPLICATION_RECEIPT.json")
                              .read_text(encoding="utf-8"))
            check("echo records receipt hash",
                  echo["receipt_sha256"] == sr.sha256_file(receipt))
        finally:
            os.environ.pop("COAUTHOR_EXTRA_GOVERNED_ROOTS", None)


def main() -> int:
    print("shipment_manifest_smoketest")
    for fn in (case_run_creation, case_ungoverned_fails_closed,
               case_input_snapshots, case_shipment_roundtrip,
               case_application_receipt):
        print(f"{fn.__name__}:")
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            check(fn.__name__, False, f"raised {type(exc).__name__}: {exc}")
        print()
    if FAILURES:
        print(f"FAIL: {len(FAILURES)} case(s): {FAILURES}")
        return 1
    print("PASS: staging runs are governed, snapshots immutable, shipments "
          "byte-verified proposals")
    return 0


if __name__ == "__main__":
    sys.exit(main())
