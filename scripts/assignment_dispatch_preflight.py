#!/usr/bin/env python3
"""Fail-closed pre-dispatch and pre-write assignment receipt verifier."""

from __future__ import annotations

import argparse
from pathlib import Path

from assignment_receipt_transaction import ReceiptTransactionError, reserve_receipt


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "assignment_process_gate.py"
EXPECTED_TARGETS = ("M1", "M2", "M3", "M4", "FINAL")


def _refuse(code: str, message: str) -> int:
    print("MISCONFIGURED")
    print(f"[BLOCKER] {code}: {message}")
    print(
        "[BLOCKER] APG-DISPATCH-REFUSED: "
        "assignment dispatch/write preflight did not pass"
    )
    return 4


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--expected-target", required=True, choices=EXPECTED_TARGETS)
    parser.add_argument("--consumer", required=True, choices=("planner",))
    parser.add_argument("--write-path", required=True, action="append")
    args = parser.parse_args()

    project = args.project_root.resolve()
    receipt_path = (
        args.receipt.resolve()
        if args.receipt.is_absolute()
        else (project / args.receipt).resolve()
    )
    if not GATE.is_file():
        return _refuse("APG-RECEIPT-INVALID", f"predicate engine is missing: {GATE}")
    try:
        record, reserved = reserve_receipt(
            project, receipt_path, args.expected_target, args.write_path
        )
    except ReceiptTransactionError as exc:
        return _refuse(exc.code, exc.message)
    except OSError as exc:
        return _refuse("APG-RECEIPT-INVALID", f"receipt reservation I/O failed: {exc}")
    print(
        f"READY assignment-dispatch target={args.expected_target} "
        f"receipt={reserved} reservation_id={record['reservation_id']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
