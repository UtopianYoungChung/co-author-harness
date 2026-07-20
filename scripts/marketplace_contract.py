#!/usr/bin/env python3
"""Shared marketplace identity and dual-loader source rules.

The package is the repository root. Claude accepts a local ``"./"`` source
for that layout, but Codex currently cannot resolve a marketplace entry to the
marketplace root. A remote URL source is the non-duplicating form accepted by
both loaders.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence
from urllib.parse import urlsplit, urlunsplit


def is_manifest_entry(entry: Mapping[str, Any], manifest: Mapping[str, Any]) -> bool:
    """Identify the package entry by loader identity, not source syntax."""
    return (
        str(entry.get("name", "")).strip()
        == str(manifest.get("name", "")).strip()
        != ""
    )


def manifest_entries(
    plugins: Any, manifest: Mapping[str, Any]
) -> Sequence[Mapping[str, Any]]:
    """Return every marketplace entry carrying the manifest plugin identity."""
    if not isinstance(plugins, list):
        return []
    return [
        entry for entry in plugins
        if isinstance(entry, dict) and is_manifest_entry(entry, manifest)
    ]


def manifest_entry_cardinality_error(
    plugins: Any, manifest: Mapping[str, Any]
) -> Optional[str]:
    matches = manifest_entries(plugins, manifest)
    if len(matches) != 1:
        name = str(manifest.get("name", "")).strip() or "<unnamed>"
        return (
            f"marketplace must contain exactly one entry named {name!r}; "
            f"found {len(matches)}"
        )
    return None


def _normalise_repository_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    path = parsed.path.rstrip("/")
    if path.endswith(".git"):
        path = path[:-4]
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, "", ""))


def root_source_error(entry: Mapping[str, Any]) -> Optional[str]:
    """Return the package-root source contract error, or ``None`` when valid."""
    source = entry.get("source")
    if not isinstance(source, dict):
        return (
            "marketplace root plugin requires a remote URL source for Codex "
            "compatibility; local './' is accepted by Claude but Codex cannot "
            "resolve the marketplace root"
        )
    if source.get("source") != "url":
        return "marketplace root plugin source object must use source='url'"
    url = str(source.get("url", "")).strip()
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.netloc:
        return "marketplace root plugin URL source must be an absolute HTTPS URL"
    if "path" in source:
        return "marketplace root plugin URL source must omit path"
    repository = str(entry.get("repository", "")).strip()
    if not repository:
        return "marketplace root plugin requires repository metadata"
    if _normalise_repository_url(repository) != _normalise_repository_url(url):
        return "marketplace source URL and repository metadata identify different repositories"
    return None
