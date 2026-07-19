#!/usr/bin/env python3
"""Adversarial smoke tests for contract-kernel-check.py."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CHECK = ROOT / "scripts" / "contract-kernel-check.py"
SPEC = importlib.util.spec_from_file_location("contract_kernel_check", CHECK)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def require_error(data: dict, needle: str) -> None:
    errors = MODULE.validate(ROOT, data)
    assert any(needle in error for error in errors), (needle, errors)


def main() -> int:
    data = json.loads(
        (ROOT / "references" / "contract_kernel.v1.json").read_text(encoding="utf-8")
    )
    assert MODULE.validate(ROOT, data) == []

    case = copy.deepcopy(data)
    case["repository_policy"]["single_branch"] = "feature"
    require_error(case, "single_branch must be main")

    case = copy.deepcopy(data)
    case["lifecycle"]["milestones"] = ["M1", "M2", "M3", "M4"]
    require_error(case, "milestones must be M1 through M5")

    case = copy.deepcopy(data)
    case["components"][0]["sha256"] = "0" * 64
    require_error(case, "content hash drift")

    case = copy.deepcopy(data)
    case["components"][1]["id"] = case["components"][0]["id"]
    require_error(case, "duplicate component id")

    for required_id in (
        "assignment-process-gate",
        "assignment-dispatch-preflight",
        "assignment-receipt-transaction",
        "assignment-writer-commit",
        "assignment-receipt-invalidate",
        "assignment-receipt-recover",
        "assignment-receipt-schema",
        "assignment-receipt-template",
    ):
        case = copy.deepcopy(data)
        case["components"] = [
            row for row in case["components"] if row["id"] != required_id
        ]
        require_error(case, f"required components missing: {required_id}")

    case = copy.deepcopy(data)
    case["components"][0]["path"] = "../phase_state_schema.md"
    require_error(case, "missing or unsafe")

    case = copy.deepcopy(data)
    case.pop("kernel_id")
    require_error(case, "kernel_id is required")

    case = copy.deepcopy(data)
    case["plugin_identity_source"] = "../plugin.json"
    require_error(case, "plugin_identity_source is missing or unsafe")

    print("contract_kernel_coherence_smoketest: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
