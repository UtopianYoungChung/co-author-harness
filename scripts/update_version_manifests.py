#!/usr/bin/env python3
"""Atomically update authoritative package identity and its Codex host mirror."""

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
    root = root.resolve(strict=True)
    version_path = root / "version.json"
    claude_path = root / ".claude-plugin" / "plugin.json"
    codex_path = root / ".codex-plugin" / "plugin.json"
    marketplace_path = root / ".claude-plugin" / "marketplace.json"
    if codex_path.exists():
        destinations.assert_writable(codex_path, purpose="Codex host identity parity update")
    authoritative = _load(version_path)
    name = authoritative.get("name")
    if not isinstance(name, str) or not name:
        raise VersionUpdateRefusal("authoritative manifest has no plugin name")
    license_name = authoritative.get("license")
    authoritative["version"] = version
    planned: list[tuple[Path, bytes]] = [
        (version_path, _bytes(authoritative)),
    ]
    if codex_path.exists():
        codex = _load(codex_path)
        if codex.get('name') != name or codex.get('license') != license_name:
            raise VersionUpdateRefusal('.codex-plugin/plugin.json identity does not mirror version.json')
        codex['version'] = version
        planned.append((codex_path, _bytes(codex)))
    # The Claude host identity and marketplace self-entry mirror name and
    # license only and never carry a version (Claude Code would pin
    # marketplace installs to it), so a version update leaves them unchanged.
    if claude_path.exists():
        claude = _load(claude_path)
        if claude.get("name") != name:
            raise VersionUpdateRefusal(".claude-plugin/plugin.json name does not mirror version.json")
        if claude.get("license") != license_name:
            raise VersionUpdateRefusal(".claude-plugin/plugin.json license does not mirror version.json")
        if "version" in claude:
            raise VersionUpdateRefusal(".claude-plugin/plugin.json must not declare a version")
    if marketplace_path.exists():
        marketplace = _load(marketplace_path)
        plugins = marketplace.get("plugins")
        if not isinstance(plugins, list):
            raise VersionUpdateRefusal("marketplace.json plugins is not a list")
        entries = [
            entry for entry in plugins
            if isinstance(entry, dict) and entry.get("name") == name
        ]
        if len(entries) != 1:
            raise VersionUpdateRefusal(
                "marketplace.json must contain exactly one self-entry mirroring version.json"
            )
        if entries[0].get("license") != license_name:
            raise VersionUpdateRefusal(
                "marketplace.json self-entry license does not mirror version.json"
            )
        if "version" in entries[0]:
            raise VersionUpdateRefusal("marketplace.json self-entry must not declare a version")
    outputs = tuple(planned)
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
        if codex_path.exists():
            codex = _load(codex_path)
            if (codex.get('name'), codex.get('version'), codex.get('license')) != (name, version, license_name):
                raise VersionUpdateRefusal('Codex host identity readback failed')
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
