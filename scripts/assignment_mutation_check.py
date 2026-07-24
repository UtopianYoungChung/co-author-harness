#!/usr/bin/env python3
"""Verify one project-relative target against the sanctioned mutation chain."""

from __future__ import annotations

import argparse
from pathlib import Path

from assignment_receipt_transaction import ReceiptTransactionError, validate_mutation_target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--target", required=True)
    args = parser.parse_args()
    try:
        row = validate_mutation_target(args.project_root, args.target)
    except ReceiptTransactionError as exc:
        print(f"MISCONFIGURED\n[BLOCKER] {exc.code}: {exc.message}")
        return 4
    print(f"VERIFIED mutation target={args.target} row_sha256={row['row_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
