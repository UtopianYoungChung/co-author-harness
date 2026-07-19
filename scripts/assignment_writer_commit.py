#!/usr/bin/env python3
"""Consume one reserved receipt and publish its scoped staged write plan."""

from __future__ import annotations

import argparse
from pathlib import Path

from assignment_receipt_transaction import ReceiptTransactionError, commit_receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    args = parser.parse_args()
    project = args.project_root.resolve()
    receipt = args.receipt.resolve() if args.receipt.is_absolute() else (project / args.receipt).resolve()
    plan = args.plan.resolve() if args.plan.is_absolute() else (project / args.plan).resolve()
    try:
        consumed, result = commit_receipt(project, receipt, plan)
    except ReceiptTransactionError as exc:
        print("MISCONFIGURED")
        print(f"[BLOCKER] {exc.code}: {exc.message}")
        print("[BLOCKER] APG-DISPATCH-REFUSED: assignment writer transaction did not pass")
        return 4
    except OSError as exc:
        print("MISCONFIGURED")
        print(f"[BLOCKER] APG-WRITE-PUBLISH-FAILED: writer transaction I/O failed: {exc}")
        print("[BLOCKER] APG-DISPATCH-REFUSED: assignment writer transaction did not pass")
        return 4
    print(f"COMMITTED assignment-write receipt={consumed} result={result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
