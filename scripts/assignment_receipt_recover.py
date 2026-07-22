#!/usr/bin/env python3
"""Inspect and explicitly archive a stale assignment transaction claim."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
import platform
from pathlib import Path


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--clear-stale-claim", action="store_true")
    parser.add_argument(
        "--acknowledge",
        choices=("inspected-receipt-states-and-journal",),
        help="Required acknowledgement before a stale claim is archived.",
    )
    args = parser.parse_args()
    project = args.project_root.resolve()
    from destination_capability import DestinationRefused, guard_project_root
    try:
        guard_project_root(project)
    except DestinationRefused as exc:
        print(f"[BLOCKER] {exc}")
        return 4
    assignment = project / "reviews" / ".harness" / "assignment"
    claim = assignment / "claims" / "transaction.lock"
    journals = sorted((assignment / "journal").glob("*.json")) if (assignment / "journal").is_dir() else []
    states = {
        state: sorted(path.name for path in (assignment / state).glob("*.json"))
        for state in ("ready", "reserved", "consumed", "invalidated")
        if (assignment / state).is_dir()
    }
    if not claim.is_file():
        print(json.dumps({"status": "CLEAR", "claim": None, "states": states, "journals": [str(p) for p in journals]}))
        return 0
    try:
        record = json.loads(claim.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"[BLOCKER] APG-RECOVERY-CLAIM-INVALID: {exc}")
        return 4
    same_host = record.get("host") == platform.node()
    live = same_host and isinstance(record.get("pid"), int) and _pid_alive(record["pid"])
    report = {"status": "ACTIVE" if live else "STALE", "claim": record, "states": states, "journals": [str(p) for p in journals]}
    print(json.dumps(report, indent=2))
    if live:
        print("[BLOCKER] APG-RECOVERY-CLAIM-ACTIVE: owning process is still alive")
        return 4
    if not args.clear_stale_claim or args.acknowledge != "inspected-receipt-states-and-journal":
        print("[BLOCKER] APG-RECOVERY-ACK-REQUIRED: inspect states and journals, then provide the exact acknowledgement")
        return 4
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archived = claim.with_name(f"transaction.recovered.{stamp}.{record.get('pid', 'unknown')}.json")
    try:
        os.replace(claim, archived)
    except OSError as exc:
        print(f"[BLOCKER] APG-RECOVERY-FAILED: {exc}")
        return 4
    print(f"RECOVERED stale-claim archived={archived}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
