#!/usr/bin/env python3
"""Prove the release loader check survives a non-UTF-8 Windows console.

Also covers R-3: hook interpreter resolution and loud launch failure.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CHECK = ROOT / "scripts" / "loader-compat-check.py"
HOOKS = ROOT / "hooks" / "hooks.json"
GATE_REL = "scripts/hooks/full_run_pretooluse_gate.py"
WINDOWS_GIT_BASH = Path(r"C:\Program Files\Git\bin\bash.exe")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _hook_launch_command() -> tuple[str, list[str]]:
    config = json.loads(HOOKS.read_text(encoding="utf-8"))
    hook = config["hooks"]["PreToolUse"][0]["hooks"][0]
    stop = config["hooks"]["Stop"][0]["hooks"][0]
    assert hook == stop, "PreToolUse and Stop must share the same interpreter resolver"
    return hook["command"], list(hook.get("args") or [])


def _hook_shell(command: str) -> str:
    """Resolve the configured shell before the test intentionally clears PATH."""
    located = shutil.which(command)
    if located:
        return located
    if os.name == "nt" and WINDOWS_GIT_BASH.is_file() and command == "bash":
        return str(WINDOWS_GIT_BASH)
    raise AssertionError(f"configured hook shell is unavailable: {command!r}")


def case_hook_interpreter_resolution() -> None:
    command, args = _hook_launch_command()
    blob = " ".join([command, *args])
    assert command != "python3", "bare python3 is the R-3 defect"
    assert "CLAUDE_PLUGIN_PYTHON" in blob
    assert "WindowsApps" in blob
    assert "HOOK-INTERPRETER" in blob
    assert GATE_REL in blob.replace("\\", "/")


def case_hook_launch_failure_is_loud() -> None:
    command, args = _hook_launch_command()
    shell = _hook_shell(command)
    env = {
        key: value for key, value in os.environ.items()
        if key not in {"CLAUDE_PLUGIN_PYTHON", "CLAUDE_PLUGIN_ROOT"}
        and key.upper() != "PYTHONUTF8"
    }
    env["PATH"] = ""
    proc = subprocess.run(
        [shell, *args],
        capture_output=True,
        check=False,
        env=env,
        timeout=30,
    )
    combined = (proc.stdout + proc.stderr).decode("utf-8", errors="replace")
    assert proc.returncode != 0, combined[-800:]
    assert "HOOK-INTERPRETER" in combined, combined[-800:]


def case_hook_launches_from_resolved_interpreter() -> None:
    command, args = _hook_launch_command()
    shell = _hook_shell(command)
    env = {
        key: value for key, value in os.environ.items()
        if key.upper() != "PYTHONUTF8"
    }
    env["CLAUDE_PLUGIN_PYTHON"] = sys.executable
    env["CLAUDE_PLUGIN_ROOT"] = str(ROOT)
    proc = subprocess.run(
        [shell, *args],
        input=b"{}",
        capture_output=True,
        check=False,
        env=env,
        timeout=30,
    )
    combined = (proc.stdout + proc.stderr).decode("utf-8", errors="replace")
    assert proc.returncode == 0, combined[-800:]
    assert "can't open file" not in combined, combined[-800:]


def case_loader_compat_encoding() -> None:
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
                "repository": "https://github.com/example/loader-portability-fixture",
            }]
        }
        _write(root / ".claude-plugin/plugin.json", json.dumps(manifest))
        _write(root / ".claude-plugin/marketplace.json", json.dumps(marketplace))
        _write(
            root / "skills/sample/SKILL.md",
            "---\nname: sample\ndescription: Synthetic fixture skill.\n---\n\n# Sample\n",
        )
        _write(root / "agents/sample.md", "# Sample agent\n")
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


def main() -> int:
    case_loader_compat_encoding()
    case_hook_interpreter_resolution()
    case_hook_launch_failure_is_loud()
    case_hook_launches_from_resolved_interpreter()
    print("PASS: loader compatibility check is console-encoding independent")
    print("PASS: hook interpreter resolves and launch failure is loud")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
