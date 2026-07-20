#!/usr/bin/env python3
"""Adversarial smoke tests for capability-contract-check.py."""

from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
CHECK = ROOT / "scripts" / "capability-contract-check.py"
SPEC = importlib.util.spec_from_file_location("capability_contract_check", CHECK)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def require_error(data: dict, needle: str) -> None:
    errors = MODULE.validate(ROOT, data)
    assert any(needle in error for error in errors), (needle, errors)


def main() -> int:
    data = yaml.safe_load(
        (ROOT / "references" / "capabilities.yaml").read_text(encoding="utf-8")
    )
    assert MODULE.validate(ROOT, data) == []

    case = copy.deepcopy(data)
    case["capabilities"].pop("centroid-pass")
    require_error(case, "missing capability row: centroid-pass")

    case = copy.deepcopy(data)
    case["capabilities"]["quick-deterministic"]["execution_mode"] = "deferred"
    require_error(case, "active capability cannot be deferred")

    case = copy.deepcopy(data)
    case["capabilities"]["centroid-pass"].pop("reason_code")
    require_error(case, "unavailable capability needs reason_code")

    case = copy.deepcopy(data)
    case["capabilities"]["centroid-pass"]["reason_code"] = (
        "SYNTHETIC_REASON_NOT_DECLARED"
    )
    require_error(case, "CAP-DEFERRED-UNDECLARED")

    case = copy.deepcopy(data)
    case["capabilities"]["advisor-escalation"].pop("provider")
    require_error(case, "external-dependent capability needs provider")

    case = copy.deepcopy(data)
    case["capabilities"]["quick-deterministic"]["evidence"] = [
        "scripts/capability_contract_smoketest.py"
    ]
    require_error(case, "CAP-TEST-CIRCULAR")

    case = copy.deepcopy(data)
    case["capabilities"]["quick-deterministic"]["implementation"] = "../outside.py"
    require_error(case, "CAP-PATH")

    case = copy.deepcopy(data)
    case["capabilities"]["quick-deterministic"]["evidence"] = [
        "scripts/catalog-check.py"
    ]
    require_error(case, "CAP-TEST-UNREGISTERED")

    case = copy.deepcopy(data)
    graph = case["capabilities"]["graph-grounding-overlay"]
    graph["availability"] = "active"
    graph["execution_mode"] = "prompt-mediated"
    graph.pop("reason_code")
    require_error(case, "CAP-ACTIVE-DEFERRED")

    print("capability_contract_smoketest: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
