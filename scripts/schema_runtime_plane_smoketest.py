#!/usr/bin/env python3
"""Run the required JSON Schema capability probe from relocated runtime planes."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SOURCE_CHECK = ROOT / "scripts" / "schema_runtime_check.py"
RUNTIME_SCRIPTS = (
    "schema_runtime_check.py",
    "output_contract.py",
    "shipment_contract.py",
)


def run(path: Path) -> dict[str, str]:
    result = subprocess.run(
        [sys.executable, str(path)],
        cwd=path.parent.parent,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "passed"
    assert payload["draft"] == "2020-12"
    return payload


def main() -> int:
    source = run(SOURCE_CHECK)
    with tempfile.TemporaryDirectory(prefix="schema-runtime-planes-") as td:
        root = Path(td)
        for plane in ("unpacked", "plugin-cache"):
            plane_root = root / plane
            shutil.copytree(ROOT / "references", plane_root / "references")
            scripts_root = plane_root / "scripts"
            scripts_root.mkdir(parents=True)
            for name in RUNTIME_SCRIPTS:
                shutil.copy2(ROOT / "scripts" / name, scripts_root / name)
            check = scripts_root / SOURCE_CHECK.name
            observed = run(check)
            assert observed == source
    print("schema_runtime_plane_smoketest: PASS (source, unpacked, plugin-cache)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
