#!/usr/bin/env python3
"""Command-driven atomic update of authoritative and parity plugin manifests."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

import destination_capability as destinations


ROOT = Path(__file__).resolve().parent.parent
SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


class VersionUpdateRefusal(RuntimeError):
    pass


def _load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8", errors="strict"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise VersionUpdateRefusal(f"cannot read valid JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise VersionUpdateRefusal(f"manifest is not an object: {path}")
    return value


def _bytes(value: dict) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def update(root: Path, version: str) -> None:
    if not SEMVER.fullmatch(version):
        raise VersionUpdateRefusal(f"version is not release semver: {version!r}")
    destinations.assert_writable(root / ".claude-plugin/plugin.json", purpose="plugin version update")
    destinations.assert_writable(root / ".claude-plugin/marketplace.json", purpose="marketplace parity update")
    root = root.resolve(strict=True)
    plugin_path = root / ".claude-plugin/plugin.json"
    marketplace_path = root / ".claude-plugin/marketplace.json"
    plugin = _load(plugin_path)
    marketplace = _load(marketplace_path)
    name = plugin.get("name")
    if not isinstance(name, str) or not name:
        raise VersionUpdateRefusal("authoritative manifest has no plugin name")
    entries = marketplace.get("plugins")
    matches = [row for row in entries if isinstance(row, dict) and row.get("name") == name] if isinstance(entries, list) else []
    if len(matches) != 1:
        raise VersionUpdateRefusal(f"marketplace must contain exactly one parity entry for {name}")
    plugin["version"] = version
    matches[0]["version"] = version
    outputs = ((plugin_path, _bytes(plugin)), (marketplace_path, _bytes(marketplace)))
    originals = {path: path.read_bytes() for path, _data in outputs}
    temporaries: list[tuple[Path, Path]] = []
    replaced: list[Path] = []
    try:
        for path, data in outputs:
            temporary = path.with_name(path.name + f".tmp.{os.getpid()}")
            with temporary.open("xb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            _load(temporary)
            temporaries.append((temporary, path))
        for temporary, path in temporaries:
            os.replace(temporary, path)
            replaced.append(path)
        if _load(plugin_path).get("version") != version:
            raise VersionUpdateRefusal("version readback failed")
        parity = next(row for row in _load(marketplace_path)["plugins"] if row.get("name") == name)
        if parity.get("version") != version:
            raise VersionUpdateRefusal("marketplace parity readback failed")
    except Exception:
        for path in reversed(replaced):
            recovery = path.with_name(path.name + f".recover.{os.getpid()}")
            try:
                with recovery.open("xb") as handle:
                    handle.write(originals[path])
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(recovery, path)
            finally:
                recovery.unlink(missing_ok=True)
        raise
    finally:
        for temporary, _path in temporaries:
            temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("version")
    parser.add_argument("--plugin-root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        update(args.plugin_root, args.version)
    except (VersionUpdateRefusal, destinations.DestinationRefused) as exc:
        print(exc)
        return 2
    print(f"version manifests updated: {args.version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
