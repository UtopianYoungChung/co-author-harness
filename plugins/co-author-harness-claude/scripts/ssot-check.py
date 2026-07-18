#!/usr/bin/env python3
"""
co-author-harness — ssot-check.py

Reads .claude-plugin/ssot.yaml and verifies that each registered fact's
consumers agree with the authoritative value (or, for `method: none`
consumers, that the value is genuinely absent — the c2.6 inversion
posture).

Authored at v0.11.0 c9 per the definitive-architectural-plan §3.4.

Authority methods:
  - count: count of files matching a glob pattern under plugin_root.
  - json_field: a field inside a JSON file, dotted-path supported.

Consumer methods:
  - none: the fact MUST NOT appear at this consumer (asserted-count
    inversion). Returns BLOCKER if any well-known assertion pattern
    surfaces.
  - regex: a pattern whose first capture group must equal the
    authoritative value.
  - json_field: the consumer's JSON field must equal the authoritative
    value. For paths with `[*]` (e.g., `plugins[*].version`), every
    self-referencing entry is checked; non-self-referencing entries are
    ignored.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml  # type: ignore
except ImportError:
    print("[BLOCKER] PyYAML required to parse .claude-plugin/ssot.yaml")
    sys.exit(1)


# Patterns that detect prose assertions of skill counts. Mirrors
# manifest-coherence-check.ASSERTED_COUNT_PATTERNS. Kept duplicate (rather
# than imported) so the two validators remain independently runnable.
_ASSERTED_COUNT_PATTERNS = (
    re.compile(r"\bships\s+\d+\s+skills?\b", re.IGNORECASE),
    re.compile(r"\b\d+\s+(shipped\s+)?skills?\s+(across|spanning|over)\b", re.IGNORECASE),
    re.compile(r"\bcontains\s+\d+\s+skills?\b", re.IGNORECASE),
    re.compile(r"\b\d+\s+skills?\s+available\b", re.IGNORECASE),
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(read_text(path))


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(read_text(path))


def resolve_authority(
    authority: Dict[str, Any], plugin_root: Path
) -> Tuple[Optional[str], Optional[str]]:
    """Resolve an authority spec to (value, error).

    Returns (value, None) on success. Returns (None, error_message) when
    the authority cannot be resolved.
    """
    method = str(authority.get("method", "")).strip()
    if method == "count":
        pattern = str(authority.get("pattern", "")).strip()
        if not pattern:
            return None, "authority method=count missing 'pattern'"
        count = sum(1 for _ in plugin_root.glob(pattern))
        return str(count), None
    if method == "json_field":
        path_str = str(authority.get("path", "")).strip()
        field = str(authority.get("field", "")).strip()
        if not path_str or not field:
            return None, "authority method=json_field missing 'path' or 'field'"
        target = plugin_root / path_str
        if not target.exists():
            return None, f"authority json_field path does not exist: {path_str}"
        try:
            data = load_json(target)
        except json.JSONDecodeError as exc:
            return None, f"authority json_field parse failed for {path_str}: {exc}"
        # Walk dotted-path; we don't need glob support for authority.
        cur: Any = data
        for part in field.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return None, f"authority json_field {path_str}#{field} not present"
        return str(cur), None
    return None, f"unknown authority method: {method!r}"


def is_self_referencing_marketplace_entry(
    entry: Dict[str, Any], marketplace_path: Path, plugin_root: Path
) -> bool:
    """True if this marketplace entry references the current plugin root."""
    source = str(entry.get("source", "")).strip()
    if not source:
        return False
    if source in (".", "./"):
        # Convention: source-relative-to-marketplace-dir.
        return marketplace_path.parent.resolve() == plugin_root.resolve()
    candidates = [
        (marketplace_path.parent / source).resolve(),
        (marketplace_path.parent.parent / source).resolve(),
    ]
    return plugin_root.resolve() in candidates


def check_consumer(
    consumer: Dict[str, Any],
    expected_value: str,
    plugin_root: Path,
    fact_name: str,
) -> List[str]:
    """Return list of BLOCKER strings for this consumer."""
    findings: List[str] = []
    path_str = str(consumer.get("path", "")).strip()
    method = str(consumer.get("method", "")).strip()
    if not path_str or not method:
        return [f"SSOT consumer for {fact_name!r}: missing 'path' or 'method'"]
    consumer_path = plugin_root / path_str
    if not consumer_path.exists():
        # Absent consumer files are not BLOCKERs — they may be optional
        # (e.g., marketplace.json may not exist for every plugin).
        return findings
    if method == "none":
        # The fact MUST NOT appear at this consumer. Inspect file contents
        # for any asserted-count pattern and flag.
        try:
            text = read_text(consumer_path)
        except OSError as exc:
            return [f"SSOT consumer {path_str!r}: read failed: {exc}"]
        # For JSON consumers, look at the description field specifically.
        if path_str.endswith(".json"):
            try:
                data = load_json(consumer_path)
            except json.JSONDecodeError:
                return findings
            if path_str.endswith("plugin.json"):
                desc = str(data.get("description", ""))
                for pattern in _ASSERTED_COUNT_PATTERNS:
                    if pattern.search(desc):
                        findings.append(
                            f"SSOT {fact_name!r} method=none violation in "
                            f"{path_str}: description asserts count "
                            f"({pattern.pattern})"
                        )
            elif path_str.endswith("marketplace.json"):
                plugins = data.get("plugins", [])
                if isinstance(plugins, list):
                    for entry in plugins:
                        if not isinstance(entry, dict):
                            continue
                        if not is_self_referencing_marketplace_entry(
                            entry, consumer_path, plugin_root
                        ):
                            continue
                        desc = str(entry.get("description", ""))
                        for pattern in _ASSERTED_COUNT_PATTERNS:
                            if pattern.search(desc):
                                findings.append(
                                    f"SSOT {fact_name!r} method=none violation "
                                    f"in {path_str} self-referencing entry: "
                                    f"description asserts count "
                                    f"({pattern.pattern})"
                                )
        else:
            # For non-JSON (e.g., README.md), the asserted-count claim
            # would surface in prose. Keep this check tight: only the
            # patterns that catalog-check.py inverted at c2.6.
            for pattern in _ASSERTED_COUNT_PATTERNS:
                if pattern.search(text):
                    findings.append(
                        f"SSOT {fact_name!r} method=none violation in "
                        f"{path_str}: prose asserts count "
                        f"({pattern.pattern})"
                    )
        return findings
    if method == "regex":
        pattern_str = str(consumer.get("pattern", "")).strip()
        if not pattern_str:
            return [f"SSOT consumer {path_str!r}: regex method missing 'pattern'"]
        try:
            text = read_text(consumer_path)
        except OSError as exc:
            return [f"SSOT consumer {path_str!r}: read failed: {exc}"]
        match = re.search(pattern_str, text, re.M)
        if not match:
            return [
                f"SSOT consumer {path_str!r}: regex {pattern_str!r} "
                f"did not match"
            ]
        captured = match.group(1) if match.groups() else match.group(0)
        if captured != expected_value:
            return [
                f"SSOT consumer {path_str!r}: captured {captured!r} != "
                f"authoritative {expected_value!r} for {fact_name!r}"
            ]
        return findings
    if method == "json_field":
        field = str(consumer.get("field", "")).strip()
        if not field:
            return [f"SSOT consumer {path_str!r}: json_field missing 'field'"]
        try:
            data = load_json(consumer_path)
        except json.JSONDecodeError as exc:
            return [
                f"SSOT consumer {path_str!r}: JSON parse failed: {exc}"
            ]
        # Support glob form `plugins[*].field` for self-referencing entries.
        if "[*]" in field:
            base, _, suffix = field.partition("[*].")
            entries = data.get(base, [])
            if not isinstance(entries, list):
                return findings
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                if path_str.endswith("marketplace.json"):
                    if not is_self_referencing_marketplace_entry(
                        entry, consumer_path, plugin_root
                    ):
                        continue
                actual = str(entry.get(suffix, "")).strip()
                if actual != expected_value:
                    name = entry.get("name", "<unnamed>")
                    findings.append(
                        f"SSOT consumer {path_str!r} entry '{name}': "
                        f"{suffix} = {actual!r} != authoritative "
                        f"{expected_value!r} for {fact_name!r}"
                    )
            return findings
        # Simple dotted-path.
        cur: Any = data
        for part in field.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return [
                    f"SSOT consumer {path_str!r}: field {field!r} not present"
                ]
        if str(cur) != expected_value:
            return [
                f"SSOT consumer {path_str!r}: {field} = {cur!r} != "
                f"authoritative {expected_value!r} for {fact_name!r}"
            ]
        return findings
    return [f"SSOT consumer {path_str!r}: unknown method {method!r}"]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify SSOT fact consistency across consumers (v0.11.0 c9)."
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

    ssot_path = plugin_root / ".claude-plugin" / "ssot.yaml"
    if not ssot_path.exists():
        print(f"[BLOCKER] SSOT registry not found: {ssot_path}")
        return 1

    try:
        registry = load_yaml(ssot_path)
    except yaml.YAMLError as exc:
        print(f"[BLOCKER] SSOT registry parse failed: {exc}")
        return 1

    facts = (registry or {}).get("facts", {})
    if not isinstance(facts, dict):
        print(f"[BLOCKER] SSOT registry: 'facts' must be a mapping")
        return 1

    blockers: List[str] = []
    fact_summary: List[str] = []

    for fact_name, fact_spec in facts.items():
        if not isinstance(fact_spec, dict):
            blockers.append(f"SSOT fact {fact_name!r}: spec is not a mapping")
            continue
        authority = fact_spec.get("authority", {})
        if not isinstance(authority, dict):
            blockers.append(f"SSOT fact {fact_name!r}: authority is not a mapping")
            continue
        value, err = resolve_authority(authority, plugin_root)
        if err is not None:
            blockers.append(f"SSOT fact {fact_name!r}: {err}")
            continue
        consumers = fact_spec.get("consumers", []) or []
        if not isinstance(consumers, list):
            blockers.append(f"SSOT fact {fact_name!r}: consumers is not a list")
            continue
        for consumer in consumers:
            if not isinstance(consumer, dict):
                continue
            blockers.extend(check_consumer(consumer, value, plugin_root, fact_name))
        fact_summary.append(f"{fact_name}={value} ({len(consumers)} consumer(s))")

    print("SSOT REGISTRY CHECK")
    print(f"- Plugin root: {plugin_root}")
    print(f"- Registry: {ssot_path.relative_to(plugin_root)}")
    print(f"- Facts checked: {len(facts)}")
    for line in fact_summary:
        print(f"  - {line}")
    print(f"- Blockers: {len(blockers)}")

    for item in blockers:
        print(f"[BLOCKER] {item}")

    return 1 if blockers else 0


if __name__ == "__main__":
    sys.exit(main())
