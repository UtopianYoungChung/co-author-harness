#!/usr/bin/env python3
"""Local Agent Plugins v1.0.0 checks for the published root plugin.json.

Root plugin.json is the package's portable identity. It must carry the
canonical v1.0.0 schema identifier; a missing or unknown $schema is a refused
package, not a warning.

This module is a local producer gate. It does not claim installed-cache or
startup qualification on any host.

Native plugin.yaml / plugin.yml manifests are refused at the package root so
root plugin.json stays the only portable identity.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Tuple

PLUGIN_SCHEMA_V1 = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
PLUGIN_FIELDS = {
    "$schema",
    "name",
    "version",
    "description",
    "author",
    "homepage",
    "repository",
    "license",
    "keywords",
    "extensions",
}
AUTHOR_FIELDS = {"name", "email", "url"}
# Spec §5.5: 1-64 chars, [a-z0-9.-], start/end alphanumeric, no -- or ...
PLUGIN_NAME_RE = re.compile(
    r"^(?:[a-z0-9]|[a-z0-9](?!.*--)(?!.*\.\.)[a-z0-9.-]{0,62}[a-z0-9])$"
)
NATIVE_MANIFESTS = ("plugin.yaml", "plugin.yml")


def _load_object(path: Path, label: str) -> Tuple[dict, List[str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {}, [f"{label} could not be read: {exc}"]
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        return {}, [f"{label} is not valid JSON: {exc}"]
    if not isinstance(value, dict):
        return {}, [f"{label} must be a JSON object"]
    return value, []


def validate_manifest(manifest: dict, *, label: str = "plugin.json") -> List[str]:
    """Return BLOCKERs for a parsed Agent Plugins v1 manifest object."""
    blockers: List[str] = []
    unknown = sorted(set(manifest) - PLUGIN_FIELDS)
    if unknown:
        blockers.append(
            f"{label} is not a closed Agent Plugins v1 manifest; "
            f"unknown top-level field(s): {', '.join(unknown)}"
        )

    schema = manifest.get("$schema")
    if schema != PLUGIN_SCHEMA_V1:
        blockers.append(
            f"{label} declares an unsupported or missing Agent Plugins schema"
        )

    name = manifest.get("name")
    if (
        not isinstance(name, str)
        or not 1 <= len(name) <= 64
        or PLUGIN_NAME_RE.fullmatch(name) is None
    ):
        blockers.append(f"{label} name does not satisfy v1 constraints")

    for field in ("version", "description", "homepage", "repository", "license"):
        if field in manifest and not isinstance(manifest[field], str):
            blockers.append(f"{label} {field} must be a string")

    if "keywords" in manifest:
        keywords = manifest["keywords"]
        if not isinstance(keywords, list) or any(
            not isinstance(value, str) for value in keywords
        ):
            blockers.append(f"{label} keywords must be an array of strings")

    if "author" in manifest:
        author = manifest["author"]
        if not isinstance(author, dict):
            blockers.append(f"{label} author must be an object")
        else:
            unknown_author = set(author) - AUTHOR_FIELDS
            if unknown_author or any(
                not isinstance(value, str) for value in author.values()
            ):
                blockers.append(
                    f"{label} author may contain only string name, email, and url fields"
                )

    if "extensions" in manifest:
        extensions = manifest["extensions"]
        if not isinstance(extensions, dict) or any(
            not isinstance(value, dict) for value in extensions.values()
        ):
            blockers.append(f"{label} extensions must be an object of objects")

    return blockers


def check_plugin_root(plugin_root: Path) -> List[str]:
    """Refuse native plugin YAML and require a portable v1 plugin.json when present."""
    blockers: List[str] = []
    for relative in NATIVE_MANIFESTS:
        native = plugin_root / relative
        if native.exists():
            blockers.append(
                f"{relative} is a native plugin manifest; this package is "
                "a portable Agent Plugins v1 package whose only identity is "
                "plugin.json"
            )

    manifest_path = plugin_root / "plugin.json"
    if not manifest_path.exists():
        return blockers
    manifest, load_blockers = _load_object(manifest_path, "plugin.json")
    if load_blockers:
        return blockers + load_blockers
    blockers.extend(validate_manifest(manifest))
    return blockers
