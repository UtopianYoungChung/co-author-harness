#!/usr/bin/env python3
"""
co-author-harness — catalog-check.py

Catalog parity checks:
1) README skill count matches discovered skills/*/SKILL.md count.
2) /plugin-commands command table matches discovered skill names.
3) SKILL_REGISTRY includes every shipped skill name.
4) commands/<name>.md shim descriptions are prefix-matches of the
   plugin-commands SKILL catalog Purpose column (v0.9.0+).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Set

import yaml


REGISTRY_SKILL_HEADING = re.compile(r"^###\s+SK-\d+\.\s+`([^`]+)`\s*$")


def _normalize_quotes(s: str) -> str:
    """Normalize curly quotes to ASCII so plain-text shim descriptions
    can prefix-match catalog rows that use smart quotes."""
    return (
        s.replace("’", "'")
         .replace("‘", "'")
         .replace("“", '"')
         .replace("”", '"')
    )


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


def parse_plugin_commands_purposes(plugin_root: Path) -> Dict[str, str]:
    """Parse the /plugin-commands SKILL command catalog table.

    Returns a mapping of command name (no leading slash) to its Purpose
    column text, whitespace-stripped, with markdown bold markers stripped
    so plain-text shim descriptions can prefix-match.
    """
    path = plugin_root / "skills" / "plugin-commands" / "SKILL.md"
    text = read_text(path)
    purposes: Dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip().startswith("| `/"):
            continue
        parts = line.split("|")
        if len(parts) < 4:
            continue
        first_cell = parts[1].strip()
        match = re.match(r"^`/([^`]+)`$", first_cell)
        if not match:
            continue
        name = match.group(1).strip()
        purpose = _normalize_quotes(parts[2].strip().replace("**", "").replace("`", ""))
        purposes[name] = purpose
    return purposes


def discover_commands(plugin_root: Path) -> Dict[str, str]:
    """Discover commands/<name>.md shims and return a mapping of
    command name to frontmatter description (whitespace-stripped).
    """
    discovered: Dict[str, str] = {}
    commands_dir = plugin_root / "commands"
    if not commands_dir.exists():
        return discovered
    for command_md in sorted(commands_dir.glob("*.md")):
        name = command_md.stem
        text = read_text(command_md)
        match = re.search(r"^---\n(.*?)\n---", text, re.S)
        if not match:
            discovered[name] = ""
            continue
        frontmatter = yaml.safe_load(match.group(1)) or {}
        description = _normalize_quotes(str(frontmatter.get("description", "")).strip())
        discovered[name] = description
    return discovered


def check_commands_parity(
    plugin_root: Path,
    blockers: List[str],
    warnings: List[str],
) -> int:
    """v0.9.0 parity rule: every commands/<name>.md frontmatter description
    must be a prefix of the matching plugin-commands SKILL catalog row's
    Purpose column (whitespace-stripped, prefix-tolerant; markdown bold
    markers stripped from the catalog before comparison).
    """
    try:
        commands = discover_commands(plugin_root)
        purposes = parse_plugin_commands_purposes(plugin_root)
    except Exception as exc:  # noqa: BLE001
        blockers.append(f"commands/ parity check failed: {exc}")
        return 0

    if not commands:
        warnings.append(
            "commands/ directory empty or absent — UI loadability shims not present"
        )
        return 0

    for name, description in sorted(commands.items()):
        if name not in purposes:
            blockers.append(
                f"commands/{name}.md has no matching row in plugin-commands SKILL catalog"
            )
            continue
        if not description:
            blockers.append(f"commands/{name}.md is missing frontmatter description")
            continue
        if not purposes[name].startswith(description):
            blockers.append(
                f"commands/{name}.md description is not a prefix of the catalog Purpose column"
            )
    return len(commands)


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
        missing_in_commands = sorted(discovered_names - command_names)
        extra_in_commands = sorted(command_names - discovered_names)
        if missing_in_commands:
            blockers.append(
                "/plugin-commands is missing shipped skills: " + ", ".join(missing_in_commands)
            )
        if extra_in_commands:
            blockers.append(
                "/plugin-commands lists non-shipped skills: " + ", ".join(extra_in_commands)
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

    commands_count = check_commands_parity(plugin_root, blockers, warnings)

    print("CATALOG PARITY CHECK")
    print(f"- Plugin root: {plugin_root}")
    print(f"- Discovered skills: {len(discovered_names)}")
    print(f"- Discovered commands: {commands_count}")
    print(f"- README skills count: {readme_count if readme_count is not None else '<missing>'}")
    print(f"- Blockers: {len(blockers)}")
    print(f"- Warnings: {len(warnings)}")

    for item in blockers:
        print(f"[BLOCKER] {item}")
    for item in warnings:
        print(f"[WARN] {item}")

    return 1 if blockers else 0


if __name__ == "__main__":
    sys.exit(main())
