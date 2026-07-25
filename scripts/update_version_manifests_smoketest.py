#!/usr/bin/env python3
"""Focused checks for command-driven version-manifest parity updates."""

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
        plugin = root / ".claude-plugin/plugin.json"
        market = root / ".claude-plugin/marketplace.json"
        dump(plugin, {"name": "fixture", "version": "0.1.0"})
        dump(market, {"name": "local", "plugins": [{"name": "fixture", "version": "0.1.0"}]})
        updater.update(root, "0.2.0")
        assert json.loads(plugin.read_text())["version"] == "0.2.0"
        assert json.loads(market.read_text())["plugins"][0]["version"] == "0.2.0"
        before = (plugin.read_bytes(), market.read_bytes())
        updater.update(root, "0.2.0")
        assert before == (plugin.read_bytes(), market.read_bytes())
        try:
            updater.update(root, "v0.2.0")
        except updater.VersionUpdateRefusal:
            pass
        else:
            raise AssertionError("non-release semver accepted")
        duplicate = json.loads(market.read_text())
        duplicate["plugins"].append(dict(duplicate["plugins"][0]))
        dump(market, duplicate)
        try:
            updater.update(root, "0.3.0")
        except updater.VersionUpdateRefusal:
            pass
        else:
            raise AssertionError("duplicate marketplace identity accepted")
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
