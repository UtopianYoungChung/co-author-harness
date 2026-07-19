#!/usr/bin/env python3
"""Explicitly invalidate a ready or reserved assignment receipt."""

from __future__ import annotations

import argparse
from pathlib import Path

from assignment_receipt_transaction import ReceiptTransactionError, invalidate_receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    project = args.project_root.resolve()
    receipt = args.receipt.resolve() if args.receipt.is_absolute() else (project / args.receipt).resolve()
    try:
        invalidated = invalidate_receipt(project, receipt)
    except ReceiptTransactionError as exc:
        print("MISCONFIGURED")
        print(f"[BLOCKER] {exc.code}: {exc.message}")
        return 4
    except OSError as exc:
        print("MISCONFIGURED")
        print(f"[BLOCKER] APG-RECEIPT-INVALID: receipt invalidation I/O failed: {exc}")
        return 4
    print(f"INVALIDATED assignment-receipt path={invalidated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
