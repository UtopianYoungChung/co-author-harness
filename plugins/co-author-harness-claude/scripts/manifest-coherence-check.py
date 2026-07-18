#!/usr/bin/env python3
"""
co-author-harness — manifest-coherence-check.py

Manifest coherence checks (introduced at v0.11.0 c8 per the
definitive-architectural-plan §3.3):

1) plugin.json description ≤ 300 characters (forensic §4 Gap 1).
2) plugin.json keywords ≤ 12 entries; every keyword is a non-empty string.
3) Every keyword resolves to a substrate token visible somewhere under the
   plugin root — discovered SKILL names, command names, the package's own
   name tokens, or one of an allow-list of governance/topic terms. The
   intent is to refuse keywords that name aspirations the package does
   not actually carry (forensic §4 Gap 2).
4) plugin.json description does not assert any "Ships <N> skills" /
   "<N> skills" hardcoded count. The asserted-count BLOCKER guards
   against the SSOT violation surfaced at v0.11.0 §2.2 — manifest
   descriptions are NOT the source of truth for skill counts; the
   filesystem is. catalog-check.py inverts the same contract for the
   README; this validator inverts it for both manifests.
5) plugin.json description == marketplace.json self-referencing entry's
   description (description parity — forensic §4 Gap 4). Closes the
   class of failure where the two manifests drift in the user-facing
   tagline. marketplace.json's absence or its lack of a self-referencing
   entry skips this check silently (parity is meaningless without two
   sources).

Exit code: 1 on any BLOCKER; 0 otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None  # noqa: N816


DESCRIPTION_MAX_CHARS = 300
KEYWORDS_MAX_COUNT = 12

# Keywords that name domain or governance concepts the package legitimately
# carries even when no SKILL.md or command.md surfaces them. Maintained as a
# small allow-list rather than a free-for-all so that keyword drift surfaces
# at the validator layer.
GOVERNANCE_KEYWORD_ALLOWLIST: Set[str] = {
    "research",
    "academic-writing",
    "peer-review",
    "four-agent-loop",
    "phase-ladder",
    "grounding-protocol",
    "snowball-references",
    "is-research",  # Information Systems
    "hci",          # Human-Computer Interaction
    "zotero",       # external connector
    "scholarly-search",  # external connector
}

# Patterns that flag asserted skill counts in description prose.
ASSERTED_COUNT_PATTERNS = (
    re.compile(r"\bships\s+\d+\s+skills?\b", re.IGNORECASE),
    re.compile(r"\b\d+\s+(shipped\s+)?skills?\s+(across|spanning|over)\b", re.IGNORECASE),
    re.compile(r"\bcontains\s+\d+\s+skills?\b", re.IGNORECASE),
    re.compile(r"\b\d+\s+skills?\s+available\b", re.IGNORECASE),
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> dict:
    return json.loads(read_text(path))


def discover_skill_names(plugin_root: Path) -> Set[str]:
    """Return the set of shipped skill names from the SKILL.md frontmatter.

    Mirrors catalog-check.py's discover_skills() so coherence checks
    are evaluated against the same skill-set the catalog validator uses.
    """
    names: Set[str] = set()
    for skill_md in sorted((plugin_root / "skills").glob("*/SKILL.md")):
        try:
            text = read_text(skill_md)
        except OSError:
            continue
        match = re.search(r"^---\n(.*?)\n---", text, re.S)
        if not match:
            continue
        if yaml is not None:
            try:
                frontmatter = yaml.safe_load(match.group(1)) or {}
                name = str(frontmatter.get("name", "")).strip()
            except yaml.YAMLError:
                name = ""
        else:
            # Fallback: line-scan for "name: <value>" without PyYAML.
            name = ""
            for line in match.group(1).splitlines():
                if line.strip().startswith("name:"):
                    name = line.split(":", 1)[1].strip()
                    break
        if name:
            names.add(name)
    return names


def discover_command_names(plugin_root: Path) -> Set[str]:
    """Return the set of command shim names from commands/*.md."""
    names: Set[str] = set()
    cmd_dir = plugin_root / "commands"
    if not cmd_dir.is_dir():
        return names
    for cmd_md in cmd_dir.glob("*.md"):
        names.add(cmd_md.stem)
    return names


def keyword_resolves(
    keyword: str,
    skill_names: Set[str],
    command_names: Set[str],
    plugin_name_tokens: Set[str],
) -> bool:
    """True if the keyword resolves to a substrate token.

    Resolution sources (any single match suffices):
      - exact match in the GOVERNANCE_KEYWORD_ALLOWLIST (case-insensitive)
      - exact match in skill_names or command_names (case-insensitive)
      - substring match against any plugin-name token (case-insensitive)
      - canonical lower/dash form is a hyphenated compound of substrate
        tokens (e.g., "snowball-references" against tokens
        {"snowball", "references"})
    """
    canon = keyword.strip().lower()
    if not canon:
        return False
    if canon in {k.lower() for k in GOVERNANCE_KEYWORD_ALLOWLIST}:
        return True
    if canon in {n.lower() for n in skill_names}:
        return True
    if canon in {c.lower() for c in command_names}:
        return True
    for token in plugin_name_tokens:
        if token and token in canon:
            return True
    # Hyphenated-compound resolution: every dash-separated component is a
    # substrate token.
    if "-" in canon:
        components = [c for c in canon.split("-") if c]
        all_tokens = (
            {n.lower() for n in skill_names}
            | {c.lower() for c in command_names}
            | plugin_name_tokens
            | {k.lower() for k in GOVERNANCE_KEYWORD_ALLOWLIST}
        )
        if components and all(any(comp in t or t in comp for t in all_tokens) for comp in components):
            return True
    return False


def find_asserted_skill_counts(description: str) -> List[str]:
    """Return the list of asserted-count substrings present in description."""
    hits: List[str] = []
    for pattern in ASSERTED_COUNT_PATTERNS:
        for match in pattern.finditer(description):
            hits.append(match.group(0))
    return hits


def extract_marketplace_self_description(plugin_root: Path) -> Optional[str]:
    """Return the marketplace.json self-referencing entry's description.

    Returns None when marketplace.json does not exist or has no
    self-referencing plugin entry. The check exists to enforce parity
    between plugin.json and marketplace.json descriptions; absence on
    either side trivially passes the check.
    """
    marketplace_path = plugin_root / ".claude-plugin" / "marketplace.json"
    if not marketplace_path.exists():
        return None
    try:
        marketplace = load_json(marketplace_path)
    except (OSError, json.JSONDecodeError):
        return None
    plugins = marketplace.get("plugins", [])
    if not isinstance(plugins, list):
        return None
    for entry in plugins:
        if not isinstance(entry, dict):
            continue
        source = str(entry.get("source", "")).strip()
        if source not in (".", "./", "../"):
            # Only inspect canonical self-reference forms; bare-dot is
            # handled by version-check.py's separate format check.
            candidates = [
                (marketplace_path.parent / source).resolve()
                if source
                else None,
                (marketplace_path.parent.parent / source).resolve()
                if source
                else None,
            ]
            if plugin_root.resolve() not in [c for c in candidates if c]:
                continue
        description = str(entry.get("description", "")).strip()
        if description:
            return description
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check plugin.json + marketplace.json coherence (v0.11.0 c8)."
    )
    parser.add_argument(
        "--plugin-root",
        default=None,
        help="Plugin root path (defaults to parent directory of this script).",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    plugin_root = (
        Path(args.plugin_root).resolve() if args.plugin_root else script_dir.parent
    )

    blockers: List[str] = []
    warnings: List[str] = []

    manifest_path = plugin_root / ".claude-plugin" / "plugin.json"
    if not manifest_path.exists():
        print(f"[BLOCKER] manifest not found: {manifest_path}")
        return 1

    try:
        manifest = load_json(manifest_path)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[BLOCKER] manifest parse failed: {exc}")
        return 1

    description = str(manifest.get("description", "")).strip()
    keywords = manifest.get("keywords", [])
    plugin_name = str(manifest.get("name", "")).strip()
    plugin_name_tokens = {
        token.strip().lower()
        for token in re.split(r"[-_/\s]+", plugin_name)
        if token.strip()
    }

    # Check 1: description length
    if not description:
        blockers.append("manifest description is empty")
    elif len(description) > DESCRIPTION_MAX_CHARS:
        blockers.append(
            f"manifest description length {len(description)} chars exceeds "
            f"budget {DESCRIPTION_MAX_CHARS}"
        )

    # Check 2: keywords list shape
    if not isinstance(keywords, list):
        blockers.append(f"manifest keywords is not a list (got {type(keywords).__name__})")
        keywords_list: List[str] = []
    else:
        keywords_list = [str(k).strip() for k in keywords]
        if len(keywords_list) > KEYWORDS_MAX_COUNT:
            blockers.append(
                f"manifest keywords count {len(keywords_list)} exceeds "
                f"budget {KEYWORDS_MAX_COUNT}"
            )
        for idx, kw in enumerate(keywords_list):
            if not kw:
                blockers.append(f"manifest keywords[{idx}] is empty")

    # Check 3: keyword substrate resolution
    skill_names = discover_skill_names(plugin_root)
    command_names = discover_command_names(plugin_root)
    unresolved_keywords: List[str] = []
    for kw in keywords_list:
        if not kw:
            continue
        if not keyword_resolves(kw, skill_names, command_names, plugin_name_tokens):
            unresolved_keywords.append(kw)
    if unresolved_keywords:
        blockers.append(
            "manifest keywords do not resolve to substrate tokens or "
            "GOVERNANCE_KEYWORD_ALLOWLIST: " + ", ".join(unresolved_keywords)
        )

    # Check 4: description must not assert hardcoded skill counts
    asserted_counts = find_asserted_skill_counts(description)
    if asserted_counts:
        blockers.append(
            "manifest description asserts hardcoded skill counts (SSOT "
            "violation; counts must derive from filesystem at "
            "validate-time): " + "; ".join(asserted_counts)
        )

    # Check 5: description parity with marketplace.json self-reference
    marketplace_description = extract_marketplace_self_description(plugin_root)
    if marketplace_description is None:
        parity_summary = "<no marketplace.json self-reference>"
    elif marketplace_description == description:
        parity_summary = "OK (identical)"
    else:
        parity_summary = "DIVERGENT"
        blockers.append(
            "manifest description differs from marketplace.json self-referencing "
            "entry's description (parity violation; both manifests must carry "
            "the same user-facing tagline)"
        )

    print("MANIFEST COHERENCE CHECK")
    print(f"- Plugin root: {plugin_root}")
    print(f"- Description length: {len(description)} chars (budget {DESCRIPTION_MAX_CHARS})")
    print(f"- Keywords count: {len(keywords_list)} (budget {KEYWORDS_MAX_COUNT})")
    print(f"- Discovered skills: {len(skill_names)}")
    print(f"- Discovered commands: {len(command_names)}")
    print(f"- Description parity (plugin.json vs marketplace.json): {parity_summary}")
    print(f"- Blockers: {len(blockers)}")
    print(f"- Warnings: {len(warnings)}")

    for item in blockers:
        print(f"[BLOCKER] {item}")
    for item in warnings:
        print(f"[WARN] {item}")

    return 1 if blockers else 0


if __name__ == "__main__":
    sys.exit(main())
