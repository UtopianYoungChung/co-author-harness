#!/usr/bin/env python3
"""Validate the machine-readable capability truth registry."""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import Any

import yaml


AVAILABILITY = {"active", "degraded", "external-dependent", "unavailable"}
EXECUTION_MODES = {
    "prompt-mediated", "script-backed", "orchestration", "catalog-only", "deferred"
}
EXPOSURES = {"public", "compatibility", "internal"}
SELF_TEST = "scripts/capability_contract_smoketest.py"
HARD_STOP_MARKERS = (
    "immediate no-op",
    "returns a structured deferred result only",
    "fail-closed: governed graph generation is unavailable",
)


def _load(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("registry root must be a mapping")
    return data


def _safe_file(plugin_root: Path, rel: Any) -> Path | None:
    if not isinstance(rel, str) or not rel or "\\" in rel:
        return None
    candidate = Path(rel)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None
    resolved = (plugin_root / candidate).resolve()
    try:
        resolved.relative_to(plugin_root.resolve())
    except ValueError:
        return None
    return resolved if resolved.is_file() else None


def _skill_frontmatter_name(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^---\n(.*?)\n---", text, re.S)
    if not match:
        return None
    data = yaml.safe_load(match.group(1)) or {}
    return str(data.get("name", "")).strip() or None


def registered_fixture_paths(plugin_root: Path) -> set[str]:
    """Read literal REGISTRY keys as Python structure, never source substrings."""
    runner = plugin_root / "scripts" / "analysis" / "fixture_runner.py"
    tree = ast.parse(runner.read_text(encoding="utf-8"), filename=str(runner))
    for node in tree.body:
        target = node.target if isinstance(node, ast.AnnAssign) else None
        if isinstance(target, ast.Name) and target.id == "REGISTRY":
            if not isinstance(node.value, ast.Dict):
                raise ValueError("fixture REGISTRY must be a literal dictionary")
            keys: set[str] = set()
            for key in node.value.keys:
                if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                    raise ValueError("fixture REGISTRY keys must be literal strings")
                keys.add(key.value)
            return keys
    raise ValueError("fixture REGISTRY declaration is missing")


def validate(plugin_root: Path, data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    caps = data.get("capabilities")
    if not isinstance(caps, dict):
        return ["capabilities must be a mapping"]

    discovered = {
        p.parent.name for p in (plugin_root / "skills").glob("*/SKILL.md")
    }
    declared = set(caps)
    fixture_paths = registered_fixture_paths(plugin_root)
    for name in sorted(discovered - declared):
        errors.append(f"missing capability row: {name}")
    for name in sorted(declared - discovered):
        errors.append(f"orphan capability row: {name}")

    for name, row in sorted(caps.items()):
        if not isinstance(row, dict):
            errors.append(f"{name}: row must be a mapping")
            continue
        skill_path = _safe_file(plugin_root, f"skills/{name}/SKILL.md")
        if skill_path is None:
            errors.append(f"CAP-ENTRYPOINT-MISSING {name}: skill entrypoint is missing")
        elif _skill_frontmatter_name(skill_path) != name:
            errors.append(f"CAP-ENTRYPOINT-NAME {name}: frontmatter name mismatch")

        availability = row.get("availability")
        mode = row.get("execution_mode")
        exposure = row.get("exposure")
        evidence = row.get("evidence")

        if availability not in AVAILABILITY:
            errors.append(f"{name}: invalid availability {availability!r}")
        if mode not in EXECUTION_MODES:
            errors.append(f"{name}: invalid execution_mode {mode!r}")
        if exposure not in EXPOSURES:
            errors.append(f"{name}: invalid exposure {exposure!r}")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{name}: evidence must be a non-empty list")
        else:
            for rel in evidence:
                if _safe_file(plugin_root, rel) is None:
                    errors.append(f"CAP-PATH {name}: missing or unsafe evidence path {rel!r}")

        implementation = row.get("implementation")
        if implementation is not None and (
            _safe_file(plugin_root, implementation) is None
        ):
            errors.append(f"CAP-PATH {name}: missing or unsafe implementation {implementation!r}")

        if availability == "active":
            if mode == "deferred":
                errors.append(f"{name}: active capability cannot be deferred")
            if row.get("reason_code"):
                errors.append(f"{name}: active capability cannot carry reason_code")
            if mode == "script-backed" and not implementation:
                errors.append(f"{name}: active script-backed capability needs implementation")
            if SELF_TEST in (evidence or []):
                errors.append(f"CAP-TEST-CIRCULAR {name}: capability smoke cannot be capability evidence")
            for rel in evidence or []:
                if rel not in fixture_paths:
                    errors.append(f"CAP-TEST-UNREGISTERED {name}: {rel}")
            if skill_path is not None:
                prelude = "\n".join(skill_path.read_text(encoding="utf-8").splitlines()[:80]).lower()
                if any(marker in prelude for marker in HARD_STOP_MARKERS):
                    errors.append(f"CAP-ACTIVE-DEFERRED {name}: hard-stop marker in skill prelude")
        elif availability == "unavailable":
            if mode != "deferred":
                errors.append(f"{name}: unavailable capability must use deferred mode")
            reason_code = row.get("reason_code")
            if not reason_code:
                errors.append(f"{name}: unavailable capability needs reason_code")
            elif skill_path is not None:
                prelude = "\n".join(
                    skill_path.read_text(encoding="utf-8").splitlines()[:80]
                )
                if reason_code not in prelude:
                    errors.append(
                        f"CAP-DEFERRED-UNDECLARED {name}: reason_code {reason_code!r} "
                        "is absent from the first 80 skill lines"
                    )
        elif availability == "external-dependent" and not row.get("provider"):
            errors.append(f"{name}: external-dependent capability needs provider")

    if data.get("schema_version") != "1.0.0":
        errors.append("schema_version must be 1.0.0")
    if data.get("authority") != "references/capabilities.yaml":
        errors.append("authority must name references/capabilities.yaml")
    return errors


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugin-root", default=None)
    args = parser.parse_args()
    root = (
        Path(args.plugin_root).resolve()
        if args.plugin_root
        else Path(__file__).resolve().parent.parent
    )
    try:
        data = _load(root / "references" / "capabilities.yaml")
        errors = validate(root, data)
    except Exception as exc:  # noqa: BLE001
        print(f"BLOCK: capability registry could not be validated: {exc}")
        return 1
    for error in errors:
        print(f"BLOCK: {error}")
    if errors:
        print(f"capability-contract-check: FAIL ({len(errors)} blockers)")
        return 1
    print(f"capability-contract-check: PASS ({len(data['capabilities'])} capabilities)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
