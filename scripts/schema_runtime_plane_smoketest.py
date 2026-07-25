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
            check = root / plane / "scripts" / SOURCE_CHECK.name
            check.parent.mkdir(parents=True)
            shutil.copy2(SOURCE_CHECK, check)
            observed = run(check)
            assert observed == source
    print("schema_runtime_plane_smoketest: PASS (source, unpacked, plugin-cache)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
