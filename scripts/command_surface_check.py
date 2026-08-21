#!/usr/bin/env python3
"""Validate the plugin's single native-skill command surface."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

SLASH_NAME = re.compile(
    r"(?<![A-Za-z0-9_.-])/([a-z][a-z0-9-]{1,63})(?![A-Za-z0-9_.-])"
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_frontmatter(path: Path) -> dict:
    match = re.search(r"^---\r?\n(.*?)\r?\n---", read_text(path), re.S)
    if not match:
        raise ValueError(f"{path}: missing YAML frontmatter")
    parsed = yaml.safe_load(match.group(1)) or {}
    if not isinstance(parsed, dict):
        raise ValueError(f"{path}: YAML frontmatter must be a mapping")
    return parsed


def discover_skills(plugin_root: Path) -> dict[str, dict]:
    skills: dict[str, dict] = {}
    for path in sorted((plugin_root / "skills").glob("*/SKILL.md")):
        frontmatter = read_frontmatter(path)
        name = str(frontmatter.get("name", "")).strip()
        if not name:
            raise ValueError(f"{path}: frontmatter name is empty")
        if name in skills:
            raise ValueError(f"duplicate skill name: {name}")
        skills[name] = frontmatter
    return skills


def catalog_names(plugin_root: Path) -> set[str]:
    path = plugin_root / "skills" / "plugin-commands" / "SKILL.md"
    names: set[str] = set()
    for line in read_text(path).splitlines():
        match = re.match(r"^\|\s*`/([^`]+)`\s*\|", line.strip())
        if match:
            names.add(match.group(1).strip())
    return names


def _string_list(payload: dict, key: str, path: Path) -> list[str] | None:
    if key not in payload:
        return None
    value = payload[key]
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{path}: {key} must be a list of strings")
    return value


def load_policy(plugin_root: Path) -> tuple[set[str], dict[str, set[str]], dict]:
    path = plugin_root / "references" / "policies" / "command_surface.v1.json"
    payload = json.loads(read_text(path))
    if payload.get("schema_version") != "1.0.0":
        raise ValueError(f"{path}: schema_version must be 1.0.0")
    public = set(payload.get("public", []))
    hidden_raw = payload.get("hidden", {})
    if not isinstance(hidden_raw, dict):
        raise ValueError(f"{path}: hidden must be an object")
    hidden = {category: set(names) for category, names in hidden_raw.items()}
    extras = {
        "degraded": _string_list(payload, "degraded", path),
        "external_dependent": _string_list(payload, "external_dependent", path),
    }
    return public, hidden, extras


def capability_records(plugin_root: Path) -> dict[str, dict]:
    path = plugin_root / "references" / "capabilities.yaml"
    payload = yaml.safe_load(read_text(path)) or {}
    capabilities = payload.get("capabilities")
    if not isinstance(capabilities, dict):
        raise ValueError(f"{path}: capabilities must be a mapping")
    records: dict[str, dict] = {}
    for name, record in capabilities.items():
        if not isinstance(record, dict) or not isinstance(record.get("exposure"), str):
            raise ValueError(f"{path}: capability {name} lacks a string exposure")
        records[str(name)] = record
    return records


def capability_exposures(plugin_root: Path) -> dict[str, str]:
    return {name: record["exposure"] for name, record in capability_records(plugin_root).items()}


def section(text: str, heading: str, next_heading: str) -> str:
    start = text.find(heading)
    if start < 0:
        return ""
    end = text.find(next_heading, start + len(heading))
    return text[start:] if end < 0 else text[start:end]


def advertised_slash_names(plugin_root: Path) -> dict[str, set[str]]:
    surfaces: dict[str, set[str]] = {}
    for rel in ("AGENTS.md",):
        path = plugin_root / rel
        if path.is_file():
            surfaces[rel] = set(SLASH_NAME.findall(read_text(path)))

    phase_path = plugin_root / "references" / "PHASE_PROTOCOL.md"
    if phase_path.is_file():
        excerpt = section(read_text(phase_path), "## 14. Invocation entry points", "## 15.")
        surfaces["references/PHASE_PROTOCOL.md#14"] = set(SLASH_NAME.findall(excerpt))

    registry_path = plugin_root / "references" / "SKILL_REGISTRY.md"
    if registry_path.is_file():
        excerpt = section(read_text(registry_path), "## Planner intents", "## Skill Retirement Criteria")
        surfaces["references/SKILL_REGISTRY.md#Planner-intents"] = set(
            SLASH_NAME.findall(excerpt)
        )
    return surfaces


def validate(plugin_root: Path) -> list[str]:
    blockers: list[str] = []
    try:
        skills = discover_skills(plugin_root)
        public, hidden_by_category, extras = load_policy(plugin_root)
        catalog = catalog_names(plugin_root)
        records = capability_records(plugin_root)
        exposures = {name: record["exposure"] for name, record in records.items()}
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        return [str(exc)]

    hidden: set[str] = set()
    for category, names in hidden_by_category.items():
        overlap = hidden & names
        if overlap:
            blockers.append(
                f"command policy repeats hidden names in {category}: {', '.join(sorted(overlap))}"
            )
        hidden |= names

    overlap = public & hidden
    if overlap:
        blockers.append(f"command policy lists names as both public and hidden: {', '.join(sorted(overlap))}")

    policy_names = public | hidden
    skill_names = set(skills)
    missing = sorted(skill_names - policy_names)
    extra = sorted(policy_names - skill_names)
    if missing:
        blockers.append(f"command policy is missing shipped skills: {', '.join(missing)}")
    if extra:
        blockers.append(f"command policy lists non-shipped skills: {', '.join(extra)}")

    missing_capabilities = sorted(policy_names - set(exposures))
    extra_capabilities = sorted(set(exposures) - policy_names)
    if missing_capabilities:
        blockers.append(f"capability registry is missing command-policy skills: {', '.join(missing_capabilities)}")
    if extra_capabilities:
        blockers.append(f"capability registry lists non-shipped skills: {', '.join(extra_capabilities)}")
    expected_exposure = {name: "public" for name in public}
    expected_exposure.update({name: "compatibility" for name in hidden_by_category.get("legacy", set())})
    expected_exposure.update({name: "internal" for name in hidden - hidden_by_category.get("legacy", set())})
    for name in sorted(policy_names & set(exposures)):
        if exposures[name] != expected_exposure[name]:
            blockers.append(
                f"capability registry exposure drift for {name}: "
                f"{exposures[name]} != {expected_exposure[name]}"
            )

    public_unavailable = sorted(
        name
        for name in public
        if records.get(name, {}).get("availability") == "unavailable"
    )
    if public_unavailable:
        blockers.append(
            "command policy lists unavailable capabilities as public: "
            + ", ".join(public_unavailable)
        )

    public_degraded = {
        name for name in public if records.get(name, {}).get("availability") == "degraded"
    }
    public_external = {
        name
        for name in public
        if records.get(name, {}).get("availability") == "external-dependent"
    }
    if any(records.get(name, {}).get("availability") for name in public):
        labeled_degraded = set(extras["degraded"] or [])
        labeled_external = set(extras["external_dependent"] or [])
        if extras["degraded"] is None:
            blockers.append(
                "command policy is missing a degraded list for public degraded capabilities"
            )
        elif labeled_degraded != public_degraded:
            missing = ", ".join(sorted(public_degraded - labeled_degraded)) or "<none>"
            extra = ", ".join(sorted(labeled_degraded - public_degraded)) or "<none>"
            blockers.append(
                "command policy degraded list does not match public degraded capabilities: "
                f"missing={missing}; extra={extra}"
            )
        if extras["external_dependent"] is None:
            blockers.append(
                "command policy is missing an external_dependent list for public "
                "external-dependent capabilities"
            )
        elif labeled_external != public_external:
            missing = ", ".join(sorted(public_external - labeled_external)) or "<none>"
            extra = ", ".join(sorted(labeled_external - public_external)) or "<none>"
            blockers.append(
                "command policy external_dependent list does not match public "
                f"external-dependent capabilities: missing={missing}; extra={extra}"
            )
    for key, labeled in (
        ("degraded", extras["degraded"]),
        ("external_dependent", extras["external_dependent"]),
    ):
        if labeled is None:
            continue
        labeled_set = set(labeled)
        outside = sorted(labeled_set - public)
        if outside:
            blockers.append(
                f"command policy {key} list includes non-public names: " + ", ".join(outside)
            )

    command_files = sorted((plugin_root / "commands").glob("*.md"))
    if command_files:
        blockers.append(
            "duplicate commands/*.md surface is forbidden; native skills already provide slash commands: "
            + ", ".join(path.name for path in command_files)
        )

    for name, frontmatter in skills.items():
        invocable = frontmatter.get("user-invocable", True)
        if not isinstance(invocable, bool):
            blockers.append(f"skills/{name}/SKILL.md: user-invocable must be boolean")
            continue
        expected = name in public
        if invocable != expected:
            blockers.append(
                f"skills/{name}/SKILL.md: user-invocable={str(invocable).lower()} "
                f"but command policy classifies it as {'public' if expected else 'hidden'}"
            )

    missing_catalog = sorted(public - catalog)
    extra_catalog = sorted(catalog - public)
    if missing_catalog:
        blockers.append(f"/plugin-commands omits public commands: {', '.join(missing_catalog)}")
    if extra_catalog:
        blockers.append(f"/plugin-commands exposes hidden or unknown commands: {', '.join(extra_catalog)}")

    for surface, names in advertised_slash_names(plugin_root).items():
        unknown = sorted(names - public)
        if unknown:
            blockers.append(
                f"{surface} advertises slash names outside the public command policy: "
                + ", ".join(unknown)
            )
    return blockers


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugin-root", default=None)
    args = parser.parse_args()
    plugin_root = (
        Path(args.plugin_root).resolve()
        if args.plugin_root
        else Path(__file__).resolve().parent.parent
    )
    blockers = validate(plugin_root)
    print("COMMAND SURFACE CHECK")
    print(f"- Plugin root: {plugin_root}")
    print(f"- Blockers: {len(blockers)}")
    for blocker in blockers:
        print(f"[BLOCKER] {blocker}")
    return 1 if blockers else 0


if __name__ == "__main__":
    sys.exit(main())
