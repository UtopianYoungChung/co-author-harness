#!/usr/bin/env python3
"""
co-author-harness — catalog-check.py

Catalog parity checks:
1) README skill count matches discovered skills/*/SKILL.md count.
2) /plugin-commands command table matches user-invocable skill names.
3) SKILL_REGISTRY includes every shipped skill name.
4) The obsolete commands/*.md redirect surface is absent (enforced by
   command_surface_check.py).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Set

import yaml


REGISTRY_SKILL_HEADING = re.compile(r"^###\s+SK-\d+\.\s+`([^`]+)`\s*$")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def discover_skills(plugin_root: Path) -> Dict[str, Path]:
    discovered: Dict[str, Path] = {}
    for skill_md in sorted((plugin_root / "skills").glob("*/SKILL.md")):
        text = read_text(skill_md)
        match = re.search(r"^---\n(.*?)\n---", text, re.S)
        if not match:
            continue
        frontmatter = yaml.safe_load(match.group(1)) or {}
        name = str(frontmatter.get("name", "")).strip()
        if name:
            discovered[name] = skill_md
    return discovered


def discover_user_invocable_skills(plugin_root: Path) -> Set[str]:
    public: Set[str] = set()
    for name, path in discover_skills(plugin_root).items():
        text = read_text(path)
        match = re.search(r"^---\n(.*?)\n---", text, re.S)
        frontmatter = yaml.safe_load(match.group(1)) or {} if match else {}
        if frontmatter.get("user-invocable", True) is not False:
            public.add(name)
    return public


def parse_readme_skill_count(plugin_root: Path) -> int | None:
    """Return the count parsed from a `### Skills (N)` heading if present.

    NOTE (v0.11.0-c2.6): an asserted count is a BLOCKER under plan §3.1
    (Principle 2 — single source of truth). The c8 catalog-check inversion
    moved enforcement from "heading must exist" to "heading must NOT
    assert a count." This function now only exists to surface the
    asserted value (if any) so the BLOCKER message can name it; it does
    not signal validator health by itself.
    """
    readme = read_text(plugin_root / "README.md")
    match = re.search(r"^###\s+Skills\s+\((\d+)\)\s*$", readme, re.M)
    if match:
        return int(match.group(1))
    return None


def find_readme_skill_assertions(plugin_root: Path) -> List[str]:
    """Find any asserted skill counts in README (plan §3.1).

    Two patterns are flagged (per c8 spec):
    1. `### Skills (N)` heading.
    2. `\\bN skills\\b` bare prose.

    The skill count is exclusively derived from `ls skills/` by this
    validator; any assertion in README is a drift hazard.
    """
    readme = read_text(plugin_root / "README.md")
    findings: List[str] = []
    for match in re.finditer(r"###\s+Skills\s+\((\d+)\)", readme):
        findings.append(f"`### Skills ({match.group(1)})` heading")
    for match in re.finditer(r"\b(\d+)\s+skills\b", readme):
        findings.append(f"`{match.group(1)} skills` prose")
    return findings


def parse_plugin_commands(plugin_root: Path) -> Set[str]:
    path = plugin_root / "skills" / "plugin-commands" / "SKILL.md"
    text = read_text(path)
    found: Set[str] = set()
    for line in text.splitlines():
        match = re.match(r"^\|\s*`/([^`]+)`\s*\|", line.strip())
        if match:
            found.add(match.group(1).strip())
    return found


def parse_registry_names(plugin_root: Path) -> Set[str]:
    registry = read_text(plugin_root / "references" / "SKILL_REGISTRY.md")
    names: Set[str] = set()
    for line in registry.splitlines():
        match = REGISTRY_SKILL_HEADING.match(line.strip())
        if match:
            names.add(match.group(1).strip())
    return names


def main() -> int:
    parser = argparse.ArgumentParser(description="Check catalog/documentation parity.")
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

    discovered = discover_skills(plugin_root)
    discovered_names = set(discovered.keys())
    public_names = discover_user_invocable_skills(plugin_root)

    readme_count = parse_readme_skill_count(plugin_root)
    asserted_findings = find_readme_skill_assertions(plugin_root)
    for finding in asserted_findings:
        blockers.append(
            f"README asserts skill count via {finding} — the count must be derived from "
            "the skills/ directory, not asserted in prose. See plan §3.1 (Principle 2). "
            "Use `Skills (catalog)` or similar non-numeric form."
        )

    try:
        command_names = parse_plugin_commands(plugin_root)
        missing_in_commands = sorted(public_names - command_names)
        extra_in_commands = sorted(command_names - public_names)
        if missing_in_commands:
            blockers.append(
                "/plugin-commands is missing user-invocable skills: " + ", ".join(missing_in_commands)
            )
        if extra_in_commands:
            blockers.append(
                "/plugin-commands lists hidden or non-shipped skills: " + ", ".join(extra_in_commands)
            )
    except Exception as exc:  # noqa: BLE001
        blockers.append(f"/plugin-commands catalog check failed: {exc}")

    try:
        registry_names = parse_registry_names(plugin_root)
        missing_in_registry = sorted(discovered_names - registry_names)
        if missing_in_registry:
            blockers.append(
                "SKILL_REGISTRY missing shipped skills: " + ", ".join(missing_in_registry)
            )
        registry_only = sorted(registry_names - discovered_names)
        if registry_only:
            warnings.append(
                "SKILL_REGISTRY contains non-shipped or historical skills: "
                + ", ".join(registry_only)
            )
    except Exception as exc:  # noqa: BLE001
        blockers.append(f"SKILL_REGISTRY check failed: {exc}")

    print("CATALOG PARITY CHECK")
    print(f"- Plugin root: {plugin_root}")
    print(f"- Discovered skills: {len(discovered_names)}")
    print(f"- User-invocable commands: {len(public_names)}")
    print(f"- README skills count: {readme_count if readme_count is not None else '<missing>'}")
    print(f"- Blockers: {len(blockers)}")
    print(f"- Warnings: {len(warnings)}")

    for item in blockers:
        print(f"[BLOCKER] {item}")
    for item in warnings:
        print(f"[WARN] {item}")

    return 1 if blockers else 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
