#!/usr/bin/env python3
"""Public Planner command for assignment milestones M1-M4 and FINAL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from assignment_milestone_transaction import (
    MilestoneTransactionError, accept, activate_reader_semantic,
    archive_stale_reader_accessibility_request,
    begin, derive, record,
    rebind_reader_accessibility, recover_claim,
)
from destination_capability import DestinationRefused


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in (
        "derive", "begin", "record", "accept", "rebind-reader-policy",
        "activate-reader-semantic", "recover",
    ):
        command = sub.add_parser(name)
        command.add_argument("--project-root", type=Path, required=True)
        if name in {"begin", "record", "accept"}:
            command.add_argument("--milestone", choices=("M1", "M2", "M3", "M4", "FINAL"), required=True)
            command.add_argument("--at")
        if name == "record":
            command.add_argument("--receipt", type=Path, required=True)
            command.add_argument("--checkpoint", type=Path, required=True)
        if name == "accept":
            command.add_argument("--checkpoint", type=Path, required=True)
            command.add_argument("--approval-evidence", type=Path, required=True)
            command.add_argument("--policy-evidence", type=Path)
            command.add_argument("--terminal-evidence", type=Path)
            command.add_argument("--emit-f9", action="store_true")
        if name == "recover":
            command.add_argument("--acknowledgement", required=True)
        if name == "rebind-reader-policy":
            command.add_argument("--archive-stale-request", action="store_true")
            command.add_argument("--expected-request-sha256")
    args = parser.parse_args()
    try:
        if args.command == "derive":
            print(json.dumps(derive(args.project_root.resolve()), sort_keys=True))
        elif args.command == "begin":
            begin(args.project_root, args.milestone, args.at); print(f"BEGUN {args.milestone}")
        elif args.command == "record":
            record(args.project_root, args.milestone, args.receipt, args.checkpoint, args.at); print(f"RECORDED {args.milestone}")
        elif args.command == "accept":
            accept(
                args.project_root, args.milestone, args.checkpoint,
                args.approval_evidence, args.at, args.policy_evidence,
                args.terminal_evidence,
                emit_f9=args.emit_f9,
            ); print(f"ACCEPTED {args.milestone}")
        elif args.command == "rebind-reader-policy":
            if args.archive_stale_request:
                if not args.expected_request_sha256:
                    raise MilestoneTransactionError(
                        "AMC-REPIN-REQUEST-HASH",
                        "--archive-stale-request requires --expected-request-sha256",
                    )
                archive = archive_stale_reader_accessibility_request(
                    args.project_root, args.expected_request_sha256,
                )
                print(f"ARCHIVED_STALE {archive}")
            elif args.expected_request_sha256:
                raise MilestoneTransactionError(
                    "AMC-REPIN-REQUEST-HASH",
                    "--expected-request-sha256 is valid only with --archive-stale-request",
                )
            else:
                archive = rebind_reader_accessibility(args.project_root); print(f"REBOUND {archive}")
        elif args.command == "activate-reader-semantic":
            archive = activate_reader_semantic(args.project_root)
            print(f"SEMANTIC_ACTIVATED {archive}")
        else:
            archived = recover_claim(args.project_root, args.acknowledgement); print(f"RECOVERED {archived}")
    except DestinationRefused as exc:
        # Producer boundary: the destination is illegal regardless of domain
        # state, so this refusal outranks every transaction-level check.
        print(f"MISCONFIGURED\n[BLOCKER] {exc}")
        return 4
    except MilestoneTransactionError as exc:
        print(f"MISCONFIGURED\n[BLOCKER] {exc.code}: {exc.message}")
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
