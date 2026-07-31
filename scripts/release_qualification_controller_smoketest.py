#!/usr/bin/env python3
"""Red-first contract for the durable release qualification controller."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULE = ROOT / "scripts" / "release_qualification_controller.py"
ENVIRONMENT = ROOT / "scripts" / "qualification_environment.py"


def _load(path: Path, name: str):
    assert path.is_file(), f"RED: missing {path.relative_to(ROOT)}"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    env = _load(ENVIRONMENT, "qualification_environment")
    ctl = _load(MODULE, "release_qualification_controller")
    required_environment = {"assert_ambient_clean", "controlled_environment"}
    required_controller = {
        "start_run", "status_run", "wait_run", "cancel_run", "recover_run",
    }
    assert required_environment <= set(dir(env))
    assert required_controller <= set(dir(ctl))
    cases = {
        "ambient_environment_refused_before_child",
        "unicode_stdout_stderr_captured_as_bytes",
        "nonzero_exit_journaled",
        "serialization_failure_after_exit_recoverable",
        "crash_after_exit_recovery_without_rerun",
        "lost_exit_status_is_evidence_incomplete",
        "frontend_disconnect_survives",
        "same_intent_idempotent",
        "different_intent_refused",
        "owned_process_tree_cancelled_unrelated_survives",
        "input_drift_refused",
        "output_scope_refused",
    }
    advertised = set(getattr(ctl, "REGRESSION_CONTRACT", ()))
    assert cases <= advertised, f"missing controller regression contracts: {sorted(cases-advertised)}"
    print(f"release_qualification_controller_smoketest: PASS {len(cases)} cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
