#!/usr/bin/env python3
"""Synthetic regressions for remote-install/release source parity."""

from __future__ import annotations

import tempfile
import warnings
import zipfile
from pathlib import Path

from release_source_parity_check import PROVENANCE, compare_archive

ROOT = Path(__file__).resolve().parent.parent


def _zip(path: Path, members: list[tuple[str, bytes]]) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(path, "w") as bundle:
            for name, data in members:
                bundle.writestr(name, data)


def main() -> int:
    expected = {
        ".claude-plugin/plugin.json": b'{"name":"fixture","version":"1.0.0"}',
        "policy.md": b"binding-policy\n",
    }
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        cases = {
            "exact": ([(k, v) for k, v in expected.items()] + [(PROVENANCE, b"{}")], False),
            "tampered-source": ([
                (".claude-plugin/plugin.json", expected[".claude-plugin/plugin.json"]),
                ("policy.md", b"changed-policy\n"), (PROVENANCE, b"{}")], True),
            "missing-source": ([
                (".claude-plugin/plugin.json", expected[".claude-plugin/plugin.json"]),
                (PROVENANCE, b"{}")], True),
            "unexpected-member": ([(k, v) for k, v in expected.items()] + [
                (PROVENANCE, b"{}"), ("generated.md", b"x")], True),
            "duplicate-source": ([(k, v) for k, v in expected.items()] + [
                ("policy.md", expected["policy.md"]), (PROVENANCE, b"{}")], True),
        }
        for name, (members, should_block) in cases.items():
            archive = root / f"{name}.plugin"
            _zip(archive, members)
            findings = compare_archive(archive, expected)
            ok = bool(findings) == should_block
            print(f"  {'PASS' if ok else 'FAIL'}  {name}: {findings[:1]}")
            if not ok:
                failures.append(name)

    live_includes = []
    for base in (ROOT / "agents", ROOT / "skills"):
        for path in base.rglob("*.md"):
            if "<!-- include:" in path.read_text(encoding="utf-8"):
                live_includes.append(path.relative_to(ROOT).as_posix())
    no_build_only_policy = not live_includes
    print(
        f"  {'PASS' if no_build_only_policy else 'FAIL'}  "
        f"no build-only policy includes: {live_includes}"
    )
    if not no_build_only_policy:
        failures.append("live-build-only-includes")

    if failures:
        print(f"FAIL: {failures}")
        return 1
    print("PASS: remote installs and the release archive share source bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
