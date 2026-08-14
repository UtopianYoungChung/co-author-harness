#!/usr/bin/env python3
"""C1 red-first tests for six-plane CAPABILITY_CLOSURE claims.

The historical filename is descriptive only.  Machine output deliberately
uses CAPABILITY_CLOSURE and never lifecycle ``completeness`` as a status.
This focused program does not invoke the fixture registry.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
FIXTURE = ROOT / "scripts" / "fixtures" / "package_completeness" / "cases.json"
REGISTRY = ROOT / "references" / "capabilities.yaml"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def closure_row() -> dict[str, Any]:
    return {
        "profile": "shipment-output-v2",
        "planes": {
            "policy": {"entrypoint": "skills/run-draft/SKILL.md"},
            "contract": {"component": "shipment-v2", "sha256": "a" * 64},
            "producer": {"implementation": "scripts/staging_run.py"},
            "consumer": {"profile": "independently-governed-consumer"},
            "runtime": {
                "members": ["scripts/shipment_manifest_smoketest.py"],
                "probe_ids": ["shipment_manifest_v2_smoketest"],
            },
            "evidence": {"fixture_ids": ["shipment_manifest_v2"]},
        },
        "behavior_status": "active",
        "kernel_sha256": "a" * 64,
        "runtime_sha256": "b" * 64,
    }


def synthetic_registry(current: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    data = copy.deepcopy(current)
    target = data["capabilities"]["centroid-pass"]
    target["capability_closure"] = closure_row()
    kind = case["kind"]
    if kind == "missing_plane":
        del target["capability_closure"]["planes"][case["plane"]]
    elif kind == "status_contradiction":
        target["capability_closure"]["behavior_status"] = "unavailable"
    elif kind == "stale_kernel":
        target["capability_closure"]["kernel_sha256"] = "0" * 64
    elif kind == "stale_runtime":
        target["capability_closure"]["runtime_sha256"] = "0" * 64
        target["capability_closure"]["planes"]["runtime"]["members"] = [
            "scripts/not-packaged.py"
        ]
    return data


def has_code(errors: list[str], code: str) -> bool:
    return any(error == code or error.startswith(code + " ") for error in errors)


def main() -> int:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    current = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    checker = load_module("capability_contract_check", ROOT / "scripts" / "capability-contract-check.py")
    runtime = load_module("runtime_plane_probe_for_c1", ROOT / "scripts" / "runtime_plane_probe.py")
    archive = load_module("archive_runtime_probe_for_c1", ROOT / "scripts" / "archive_runtime_probe.py")

    baseline_errors = checker.validate(ROOT, current)
    controls = {
        "control-current-capability-registry-valid": baseline_errors == [],
        "control-current-runtime-suite-universe-self-consistent":
            tuple((row["name"], row["kind"], row["script"]) for row in runtime.DEFAULT_SUITES)
            == tuple(archive.EXPECTED_RUNTIME_SUITES),
        "control-result-vocabulary-not-lifecycle-completeness":
            fixture.get("result_vocabulary") == "CAPABILITY_CLOSURE",
    }
    unexpected: list[str] = []
    for control_id, passed in controls.items():
        print(f"{'CONTROL_PASS' if passed else 'CONTROL_FAIL'} {control_id}")
        if not passed:
            unexpected.append(control_id)

    required_suites = {tuple(row) for row in fixture["required_runtime_suites"]}
    runtime_suites = {
        (row["name"], row["kind"], row["script"]) for row in runtime.DEFAULT_SUITES
    }
    archive_suites = set(archive.EXPECTED_RUNTIME_SUITES)
    expected_reds: list[str] = []
    unexpected_passes: list[str] = []
    for case in fixture["cases"]:
        case_id = case["id"]
        kind = case["kind"]
        if kind == "archive_suite":
            observed_suites = archive_suites - {tuple(case["suite"])}
            errors = [
                f"RUNTIME-PLANE-MISSING {case_id}: {row[0]}"
                for row in sorted(required_suites - observed_suites)
            ]
        elif kind == "cache_suite":
            observed_suites = runtime_suites - {tuple(case["suite"])}
            errors = [
                f"RUNTIME-PLANE-MISSING {case_id}: {row[0]}"
                for row in sorted(required_suites - observed_suites)
            ]
        else:
            errors = checker.validate(ROOT, synthetic_registry(current, case))
        passed = has_code(errors, case["expected_code"])
        if passed:
            print(
                f"UNEXPECTED_PASS {case_id} code={case['expected_code']} "
                f"observed={errors[:2]}"
            )
            unexpected_passes.append(case_id)
        else:
            print(f"EXPECTED_RED {case_id} missing={case['expected_code']}")
            expected_reds.append(case_id)

    summary = {
        "program": "package_completeness_smoketest",
        "result_vocabulary": "CAPABILITY_CLOSURE",
        "expected_red_ids": expected_reds,
        "unexpected_pass_ids": unexpected_passes,
        "unexpected_failures": unexpected,
        "passing_controls": [name for name, ok in controls.items() if ok],
    }
    print("C1_RED_SUMMARY " + json.dumps(summary, sort_keys=True))
    return 1 if expected_reds or unexpected else 0


if __name__ == "__main__":
    raise SystemExit(main())
