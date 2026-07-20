#!/usr/bin/env python3
"""Prove the release loader check survives a non-UTF-8 Windows console."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CHECK = ROOT / "scripts" / "loader-compat-check.py"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        description = "Synthetic loader portability fixture."
        manifest = {
            "name": "loader-portability-fixture",
            "version": "1.0.0",
            "description": description,
            "keywords": ["fixture"],
        }
        marketplace = {
            "plugins": [{
                "name": manifest["name"],
                "version": manifest["version"],
                "description": description,
                "source": {
                    "source": "url",
                    "url": "https://github.com/example/loader-portability-fixture.git",
                },
            }]
        }
        _write(root / ".claude-plugin/plugin.json", json.dumps(manifest))
        _write(root / ".claude-plugin/marketplace.json", json.dumps(marketplace))
        _write(
            root / "skills/sample/SKILL.md",
            "---\nname: sample\ndescription: Synthetic fixture skill.\n---\n\n# Sample\n",
        )
        _write(root / "agents/sample.md", "# Sample agent\n")
        _write(root / "commands/sample.md", "# Sample command\n")
        _write(root / "README.md", "# Fixture\n")
        _write(root / "CHANGELOG.md", "# Changelog\n")

        archive = root / ".claude-plugin/loader-portability-fixture.plugin"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(root.rglob("*")):
                if path.is_file() and path != archive:
                    bundle.write(path, path.relative_to(root).as_posix())

        env = os.environ.copy()
        env["PYTHONUTF8"] = "0"
        env["PYTHONIOENCODING"] = "cp949"
        proc = subprocess.run(
            [
                sys.executable,
                str(CHECK),
                "--plugin-root",
                str(root),
                "--plugin-file",
                str(archive),
            ],
            capture_output=True,
            check=False,
            env=env,
        )
        combined = proc.stdout + proc.stderr
        assert b"UnicodeEncodeError" not in combined, combined[-1200:]
        decoded = combined.decode("utf-8", errors="strict")
        assert proc.returncode == 0, decoded[-1600:]
        # The check's own heading contains an em dash. Requiring it proves the
        # formerly crashing non-CP949 output path was exercised, not bypassed.
        assert "co-author-harness — loader-compat-check" in decoded

    print("PASS: loader compatibility check is console-encoding independent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
