#!/usr/bin/env python3
"""Regression test: the pre-advance guardrail must load phase_state.json."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from pre_phase_advance_check import load_ledger


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        reviews = root / "reviews"
        reviews.mkdir()
        ledger = {
            "schema_version": "0.7.4",
            "default_final_phase": "Ph4",
            "sections": {
                "Closing": {
                    "heading_path": ["Closing"],
                    "current_phase": "Ph3_converged",
                    "phase_entry_log": [],
                }
            },
        }
        (reviews / "phase_state.json").write_text(
            json.dumps(ledger), encoding="utf-8"
        )
        args = argparse.Namespace(project_root=root, section='["Closing"]')
        loaded, section = load_ledger(args)
        assert loaded["schema_version"] == "0.7.4"
        assert section["current_phase"] == "Ph3_converged"
    print("PASS: pre-advance guardrail loads phase_state.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

