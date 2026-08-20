#!/usr/bin/env python3
"""Atomically update authoritative package identity and its host mirror."""

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
    destinations.assert_writable(root / "version.json", purpose="package version update")
    destinations.assert_writable(root / "plugin.json", purpose="host manifest parity update")
    root = root.resolve(strict=True)
    version_path = root / "version.json"
    plugin_path = root / "plugin.json"
    authoritative = _load(version_path)
    plugin = _load(plugin_path)
    name = authoritative.get("name")
    if not isinstance(name, str) or not name:
        raise VersionUpdateRefusal("authoritative manifest has no plugin name")
    if plugin.get("name") != name:
        raise VersionUpdateRefusal("plugin.json name does not mirror version.json")
    license_name = authoritative.get("license")
    if plugin.get("license") != license_name:
        raise VersionUpdateRefusal("plugin.json license does not mirror version.json")
    authoritative["version"] = version
    plugin["version"] = version
    outputs = ((version_path, _bytes(authoritative)), (plugin_path, _bytes(plugin)))
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
        if _load(version_path).get("version") != version:
            raise VersionUpdateRefusal("version readback failed")
        parity = _load(plugin_path)
        if parity.get("version") != version:
            raise VersionUpdateRefusal("plugin.json parity readback failed")
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
