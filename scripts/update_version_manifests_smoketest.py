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


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="version-manifests-") as raw:
        root = Path(raw)
        version = root / "version.json"
        plugin = root / "plugin.json"
        dump(version, {"name": "fixture", "version": "0.1.0", "license": "MIT"})
        dump(plugin, {"name": "fixture", "version": "0.1.0", "license": "MIT", "description": "fixture"})
        updater.update(root, "0.2.0")
        assert json.loads(version.read_text())["version"] == "0.2.0"
        assert json.loads(plugin.read_text())["version"] == "0.2.0"
        before = (version.read_bytes(), plugin.read_bytes())
        updater.update(root, "0.2.0")
        assert before == (version.read_bytes(), plugin.read_bytes())
        try:
            updater.update(root, "v0.2.0")
        except updater.VersionUpdateRefusal:
            pass
        else:
            raise AssertionError("non-release semver accepted")
        mismatched = json.loads(plugin.read_text())
        mismatched["name"] = "other"
        dump(plugin, mismatched)
        try:
            updater.update(root, "0.3.0")
        except updater.VersionUpdateRefusal:
            pass
        else:
            raise AssertionError("mismatched host identity accepted")
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
