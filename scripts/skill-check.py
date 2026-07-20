#!/usr/bin/env python3
"""
co-author-harness — skill-check.py

Static integrity checks for package skills and manifest contract:
1) Validate all skills/*/SKILL.md frontmatter and required fields.
2) Verify /plugin-commands matches user-invocable shipped skill names.
3) Verify SKILL_REGISTRY contains every shipped skill name.
4) Report registry entries that do not correspond to shipped skills (warning).
5) Validate plugin manifest contract (required keys and forbidden hooks field).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

import yaml


REQUIRED_FRONTMATTER_KEYS = {"name", "description", "trigger", "version"}
REGISTRY_SKILL_HEADING = re.compile(r"^###\s+SK-\d+\.\s+`([^`]+)`\s*$")
REQUIRED_MANIFEST_KEYS = {"name", "version", "description", "author", "license"}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_frontmatter(skill_path: Path) -> Tuple[Dict, str]:
    text = read_text(skill_path)
    match = re.search(r"^---\n(.*?)\n---", text, re.S)
    if not match:
        raise ValueError("missing frontmatter block")
    try:
        fm = yaml.safe_load(match.group(1)) or {}
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"invalid YAML frontmatter: {exc}") from exc
    return fm, text


def discover_skills(plugin_root: Path) -> Tuple[Dict[str, Path], List[str], List[str]]:
    skill_name_to_path: Dict[str, Path] = {}
    blockers: List[str] = []
    warnings: List[str] = []

    for skill_md in sorted((plugin_root / "skills").glob("*/SKILL.md")):
        try:
            fm, _ = parse_frontmatter(skill_md)
        except ValueError as exc:
            blockers.append(f"{skill_md}: {exc}")
            continue

        missing = sorted(REQUIRED_FRONTMATTER_KEYS - set(fm.keys()))
        if missing:
            blockers.append(
                f"{skill_md}: missing required frontmatter keys: {', '.join(missing)}"
            )
            continue

        name = str(fm.get("name", "")).strip()
        if not name:
            blockers.append(f"{skill_md}: 'name' is empty")
            continue
        if name in skill_name_to_path:
            blockers.append(
                f"{skill_md}: duplicate skill name '{name}' (already in {skill_name_to_path[name]})"
            )
            continue
        skill_name_to_path[name] = skill_md

    return skill_name_to_path, blockers, warnings


def parse_plugin_commands(plugin_root: Path) -> Set[str]:
    skill_path = plugin_root / "skills" / "plugin-commands" / "SKILL.md"
    if not skill_path.exists():
        raise FileNotFoundError(f"missing {skill_path}")

    text = read_text(skill_path)
    command_names: Set[str] = set()
    for line in text.splitlines():
        # Table row shape: | `/command` | ...
        match = re.match(r"^\|\s*`/([^`]+)`\s*\|", line.strip())
        if match:
            command_names.add(match.group(1).strip())
    return command_names


def parse_registry_skill_names(plugin_root: Path) -> Set[str]:
    registry = plugin_root / "references" / "SKILL_REGISTRY.md"
    if not registry.exists():
        raise FileNotFoundError(f"missing {registry}")
    names: Set[str] = set()
    for line in read_text(registry).splitlines():
        match = REGISTRY_SKILL_HEADING.match(line.strip())
        if match:
            names.add(match.group(1).strip())
    return names


def validate_manifest(plugin_root: Path) -> Tuple[List[str], List[str]]:
    blockers: List[str] = []
    warnings: List[str] = []

    manifest_path = plugin_root / ".claude-plugin" / "plugin.json"
    if not manifest_path.exists():
        blockers.append(f"manifest missing: {manifest_path}")
        return blockers, warnings

    try:
        manifest = json.loads(read_text(manifest_path))
    except Exception as exc:  # noqa: BLE001
        blockers.append(f"manifest parse failed ({manifest_path}): {exc}")
        return blockers, warnings

    missing = sorted(REQUIRED_MANIFEST_KEYS - set(manifest.keys()))
    if missing:
        blockers.append(f"manifest missing required keys: {', '.join(missing)}")

    if "hooks" in manifest:
        blockers.append("manifest must not define top-level 'hooks' field")

    if not str(manifest.get("name", "")).strip():
        blockers.append("manifest 'name' is empty")
    if not str(manifest.get("version", "")).strip():
        blockers.append("manifest 'version' is empty")
    if not str(manifest.get("description", "")).strip():
        blockers.append("manifest 'description' is empty")

    author = manifest.get("author")
    if isinstance(author, dict):
        if not str(author.get("name", "")).strip():
            blockers.append("manifest author.name is empty")
        if not str(author.get("email", "")).strip():
            warnings.append("manifest author.email is empty")
    else:
        blockers.append("manifest 'author' must be an object")

    return blockers, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate skill metadata consistency.")
    parser.add_argument(
        "--plugin-root",
        default=None,
        help="Plugin root path (defaults to parent directory of this script).",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    plugin_root = Path(args.plugin_root).resolve() if args.plugin_root else script_dir.parent

    blockers: List[str] = []
    warnings: List[str] = []

    skill_name_to_path, skill_blockers, skill_warnings = discover_skills(plugin_root)
    blockers.extend(skill_blockers)
    warnings.extend(skill_warnings)

    discovered_skill_names = set(skill_name_to_path.keys())
    public_skill_names: Set[str] = set()
    for name, path in skill_name_to_path.items():
        try:
            frontmatter, _ = parse_frontmatter(path)
        except ValueError:
            continue
        user_invocable = frontmatter.get("user-invocable", True)
        if not isinstance(user_invocable, bool):
            blockers.append(f"{path}: 'user-invocable' must be boolean when present")
        elif user_invocable:
            public_skill_names.add(name)

    # /plugin-commands parity check
    try:
        command_catalog = parse_plugin_commands(plugin_root)
        missing_in_catalog = sorted(public_skill_names - command_catalog)
        extra_in_catalog = sorted(command_catalog - public_skill_names)
        if missing_in_catalog:
            blockers.append(
                "/plugin-commands is missing user-invocable shipped skills: "
                + ", ".join(missing_in_catalog)
            )
        if extra_in_catalog:
            blockers.append(
                "/plugin-commands lists hidden or non-shipped skills: "
                + ", ".join(extra_in_catalog)
            )
    except Exception as exc:  # noqa: BLE001
        blockers.append(f"plugin-commands validation failed: {exc}")

    # Registry consistency check
    try:
        registry_names = parse_registry_skill_names(plugin_root)
        missing_in_registry = sorted(discovered_skill_names - registry_names)
        if missing_in_registry:
            blockers.append(
                "SKILL_REGISTRY is missing shipped skills: " + ", ".join(missing_in_registry)
            )

        registry_only = sorted(registry_names - discovered_skill_names)
        if registry_only:
            warnings.append(
                "SKILL_REGISTRY contains non-shipped or external skills: "
                + ", ".join(registry_only)
            )
    except Exception as exc:  # noqa: BLE001
        blockers.append(f"SKILL_REGISTRY validation failed: {exc}")

    # Manifest contract check
    manifest_blockers, manifest_warnings = validate_manifest(plugin_root)
    blockers.extend(manifest_blockers)
    warnings.extend(manifest_warnings)

    print("SKILL INTEGRITY CHECK")
    print(f"- Plugin root: {plugin_root}")
    print(f"- Shipped skills discovered: {len(discovered_skill_names)}")
    print(f"- User-invocable skills: {len(public_skill_names)}")
    print(f"- Blockers: {len(blockers)}")
    print(f"- Warnings: {len(warnings)}")

    for item in blockers:
        print(f"[BLOCKER] {item}")
    for item in warnings:
        print(f"[WARN] {item}")

    return 1 if blockers else 0


if __name__ == "__main__":
    sys.exit(main())
