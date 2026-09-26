#!/usr/bin/env python3
"""Focused checks for command-driven package/host identity updates."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import update_version_manifests as updater
import destination_capability as destinations


def dump(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def claude_version_fixture(parent: Path) -> None:
    """Claude manifests stay version-free across an update; a declared one refuses."""
    root = parent / "claude"
    dump(root / "version.json", {"name": "fixture", "version": "0.1.0", "license": "MIT"})
    claude = root / ".claude-plugin/plugin.json"
    market = root / ".claude-plugin/marketplace.json"
    entry = {"name": "fixture", "license": "MIT", "source": "./"}
    dump(claude, {"name": "fixture", "license": "MIT"})
    dump(market, {"name": "m", "plugins": [entry]})
    before = (claude.read_bytes(), market.read_bytes())
    updater.update(root, "0.2.0")
    assert json.loads((root / "version.json").read_text())["version"] == "0.2.0"
    assert before == (claude.read_bytes(), market.read_bytes()), "Claude manifests rewritten"
    for path, value in (
        (claude, {"name": "fixture", "license": "MIT", "version": "0.2.0"}),
        (market, {"name": "m", "plugins": [entry | {"version": "0.2.0"}]}),
    ):
        original = path.read_bytes()
        dump(path, value)
        authority = (root / "version.json").read_bytes()
        try:
            updater.update(root, "0.3.0")
        except updater.VersionUpdateRefusal:
            pass
        else:
            raise AssertionError(f"declared Claude version accepted: {path.name}")
        assert (root / "version.json").read_bytes() == authority, "refusal wrote version.json"
        path.write_bytes(original)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="version-manifests-") as raw:
        root = Path(raw)
        version = root / "version.json"
        dump(version, {"name": "fixture", "version": "0.1.0", "license": "MIT"})
        codex = root / '.codex-plugin/plugin.json'
        dump(codex, {'name': 'fixture', 'version': '0.1.0', 'license': 'MIT', 'skills': './skills/'})
        updater.update(root, "0.2.0")
        assert json.loads(version.read_text())["version"] == "0.2.0"
        assert json.loads(codex.read_text())['version'] == '0.2.0'
        assert json.loads(codex.read_text())['skills'] == './skills/'
        before = (version.read_bytes(), codex.read_bytes())
        updater.update(root, "0.2.0")
        assert before == (version.read_bytes(), codex.read_bytes())
        try:
            updater.update(root, "v0.2.0")
        except updater.VersionUpdateRefusal:
            pass
        else:
            raise AssertionError("non-release semver accepted")
        mismatched = json.loads(codex.read_text())
        mismatched["name"] = "other"
        dump(codex, mismatched)
        try:
            updater.update(root, "0.3.0")
        except updater.VersionUpdateRefusal:
            pass
        else:
            raise AssertionError("mismatched host identity accepted")
        claude_version_fixture(root)
        protected = Path(__file__).resolve().parents[2] / "protected-version-fixture"
        try:
            updater.update(protected, "0.3.0")
        except (updater.VersionUpdateRefusal, destinations.DestinationRefused):
            pass
        else:
            raise AssertionError("protected destination accepted")
    print("update_version_manifests_smoketest: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
