#!/usr/bin/env python3
"""Fail-closed pre-dispatch and pre-write assignment receipt verifier."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys


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
    args = parser.parse_args()

    project = args.project_root.resolve()
    receipt_path = (
        args.receipt.resolve()
        if args.receipt.is_absolute()
        else (project / args.receipt).resolve()
    )
    if not GATE.is_file():
        return _refuse("APG-RECEIPT-INVALID", f"predicate engine is missing: {GATE}")
    if not receipt_path.is_file():
        return _refuse(
            "APG-RECEIPT-MISSING", f"missing assignment gate receipt: {receipt_path}"
        )
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return _refuse(
            "APG-RECEIPT-INVALID",
            f"cannot read valid receipt JSON from {receipt_path}: {exc}",
        )
    if not isinstance(receipt, dict) or not isinstance(
        receipt.get("target_milestone"), str
    ):
        return _refuse(
            "APG-RECEIPT-INVALID", "receipt has no valid target_milestone"
        )
    actual_target = receipt["target_milestone"]
    if actual_target != args.expected_target:
        return _refuse(
            "APG-RECEIPT-TARGET-MISMATCH",
            f"expected {args.expected_target}; receipt authorizes {actual_target}",
        )

    result = subprocess.run(
        [
            sys.executable,
            str(GATE),
            "--project-root",
            str(project),
            "--verify-receipt",
            str(receipt_path),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="" if result.stderr.endswith("\n") else "\n")
    if result.returncode != 0:
        print(
            "[BLOCKER] APG-DISPATCH-REFUSED: "
            "assignment dispatch/write preflight did not pass"
        )
        return 4

    print(
        f"READY assignment-dispatch target={args.expected_target} receipt={receipt_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
