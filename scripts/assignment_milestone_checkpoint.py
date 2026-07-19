#!/usr/bin/env python3
"""Public Planner command for assignment milestone begin/record/accept."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from assignment_milestone_transaction import (
    MilestoneTransactionError, accept, begin, derive, record, recover_claim,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("derive", "begin", "record", "accept", "recover"):
        command = sub.add_parser(name)
        command.add_argument("--project-root", type=Path, required=True)
        if name in {"begin", "record", "accept"}:
            command.add_argument("--milestone", choices=("M1", "M2", "M3", "M4"), required=True)
            command.add_argument("--at")
        if name == "record":
            command.add_argument("--receipt", type=Path, required=True)
            command.add_argument("--checkpoint", type=Path, required=True)
        if name == "accept":
            command.add_argument("--checkpoint", type=Path, required=True)
            command.add_argument("--approval-evidence", type=Path, required=True)
            command.add_argument("--policy-evidence", type=Path)
        if name == "recover":
            command.add_argument("--acknowledgement", required=True)
    args = parser.parse_args()
    try:
        if args.command == "derive":
            print(json.dumps(derive(args.project_root.resolve()), sort_keys=True))
        elif args.command == "begin":
            begin(args.project_root, args.milestone, args.at); print(f"BEGUN {args.milestone}")
        elif args.command == "record":
            record(args.project_root, args.milestone, args.receipt, args.checkpoint, args.at); print(f"RECORDED {args.milestone}")
        elif args.command == "accept":
            accept(args.project_root, args.milestone, args.checkpoint, args.approval_evidence, args.at, args.policy_evidence); print(f"ACCEPTED {args.milestone}")
        else:
            archived = recover_claim(args.project_root, args.acknowledgement); print(f"RECOVERED {archived}")
    except MilestoneTransactionError as exc:
        print(f"MISCONFIGURED\n[BLOCKER] {exc.code}: {exc.message}")
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
