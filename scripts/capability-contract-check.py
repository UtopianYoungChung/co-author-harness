#!/usr/bin/env python3
"""Validate the six-plane machine-readable capability truth registry."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
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
CAPABILITY_PLANES = ("policy", "contract", "producer", "consumer", "runtime", "evidence")
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


def _sha256(path: Path, *, normalized_text: bool = False) -> str:
    raw = path.read_bytes()
    if normalized_text:
        raw = raw.replace(b"\r\n", b"\n")
    return hashlib.sha256(raw).hexdigest()


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


def _kernel_components(plugin_root: Path) -> tuple[dict[str, dict[str, Any]], str]:
    path = plugin_root / "references" / "contract_kernel.v1.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("components", [])
    components = {
        row["id"]: row for row in rows
        if isinstance(row, dict) and isinstance(row.get("id"), str)
    }
    return components, _sha256(path, normalized_text=True)


def _profile_errors(
    plugin_root: Path,
    name: str,
    row: dict[str, Any],
    profile: dict[str, Any],
    fixture_paths: set[str],
    kernel_components: dict[str, dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    planes = profile.get("planes")
    if not isinstance(planes, dict):
        return [f"CAP-PLANE-MISSING {name}: profile planes must be a mapping"]
    for plane in CAPABILITY_PLANES:
        if not isinstance(planes.get(plane), dict):
            errors.append(f"CAP-PLANE-MISSING {name}: {plane}")
    extras = sorted(set(planes) - set(CAPABILITY_PLANES))
    if extras:
        errors.append(f"CAP-PLANE-UNKNOWN {name}: {', '.join(extras)}")

    behavior = profile.get("behavior_status")
    if behavior != row.get("availability"):
        errors.append(
            f"CAP-STATUS-CONTRADICTION {name}: availability={row.get('availability')} "
            f"behavior_status={behavior}"
        )
    missing = profile.get("missing_planes")
    if not isinstance(missing, list) or any(item not in CAPABILITY_PLANES for item in missing):
        errors.append(f"CAP-PLANE-MISSING {name}: missing_planes must name known planes")
    elif behavior == "active" and missing:
        errors.append(f"CAP-STATUS-CONTRADICTION {name}: active profile has missing planes")
    elif behavior != "active" and not missing:
        errors.append(f"CAP-STATUS-CONTRADICTION {name}: non-active profile lacks missing plane")

    policy = planes.get("policy", {})
    entrypoint = policy.get("entrypoint")
    if isinstance(entrypoint, str):
        entrypoint = entrypoint.replace("{capability}", name)
    if _safe_file(plugin_root, entrypoint) is None:
        errors.append(f"CAP-PATH {name}: missing or unsafe policy entrypoint {entrypoint!r}")

    contract = planes.get("contract", {})
    component_id = contract.get("kernel_component")
    component = kernel_components.get(component_id)
    if component is None:
        errors.append(f"CONTRACT-HASH-STALE {name}: unknown kernel component {component_id!r}")
    else:
        bound = _safe_file(plugin_root, component.get("path"))
        if bound is None or _sha256(bound, normalized_text=True) != component.get("sha256"):
            errors.append(f"CONTRACT-HASH-STALE {name}: kernel component {component_id}")

    producer = planes.get("producer", {})
    implementation = row.get("implementation")
    if producer.get("implementation_from_row"):
        if _safe_file(plugin_root, implementation) is None:
            errors.append(f"CAP-PATH {name}: profile requires a valid implementation")
    elif implementation is not None and _safe_file(plugin_root, implementation) is None:
        errors.append(f"CAP-PATH {name}: missing or unsafe implementation {implementation!r}")

    runtime = planes.get("runtime", {})
    runtime_members: list[str] = []
    for member in runtime.get("members", []) if isinstance(runtime.get("members"), list) else []:
        runtime_members.append(member.replace("{capability}", name))
    if runtime.get("members_from_policy_and_implementation"):
        runtime_members.append(str(entrypoint))
        if isinstance(implementation, str):
            runtime_members.append(implementation)
    for member in runtime_members:
        if _safe_file(plugin_root, member) is None:
            errors.append(f"RUNTIME-PLANE-MISSING {name}: {member}")

    evidence = row.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append(f"CAP-PLANE-MISSING {name}: evidence")
    else:
        for rel in evidence:
            if _safe_file(plugin_root, rel) is None:
                errors.append(f"CAP-PATH {name}: missing or unsafe evidence path {rel!r}")
        if behavior == "active":
            if SELF_TEST in evidence:
                errors.append(f"CAP-TEST-CIRCULAR {name}: capability smoke cannot be capability evidence")
            for rel in evidence:
                if rel not in fixture_paths:
                    errors.append(f"CAP-TEST-UNREGISTERED {name}: {rel}")
    return errors


def _direct_closure_errors(
    plugin_root: Path,
    name: str,
    row: dict[str, Any],
    closure: dict[str, Any],
    kernel_components: dict[str, dict[str, Any]],
    kernel_sha256: str,
) -> list[str]:
    """Validate a direct six-plane block used by focused and future rows."""
    errors: list[str] = []
    planes = closure.get("planes")
    if not isinstance(planes, dict):
        return [f"CAP-PLANE-MISSING {name}: planes"]
    for plane in CAPABILITY_PLANES:
        if not isinstance(planes.get(plane), dict):
            errors.append(f"CAP-PLANE-MISSING {name}: {plane}")
    if closure.get("behavior_status") != row.get("availability"):
        errors.append(f"CAP-STATUS-CONTRADICTION {name}: direct closure status")
    declared_kernel = closure.get("kernel_sha256")
    if declared_kernel is not None and declared_kernel != kernel_sha256:
        errors.append(f"CONTRACT-HASH-STALE {name}: contract kernel")
    contract = planes.get("contract", {})
    component_id = contract.get("component")
    component = kernel_components.get(component_id)
    if component is None:
        errors.append(f"CONTRACT-HASH-STALE {name}: unknown component {component_id!r}")
    elif contract.get("sha256") is not None and contract.get("sha256") != component.get("sha256"):
        errors.append(f"CONTRACT-HASH-STALE {name}: component hash")
    runtime = planes.get("runtime", {})
    members = runtime.get("members") if isinstance(runtime, dict) else None
    if isinstance(members, list):
        for rel in members:
            if _safe_file(plugin_root, rel) is None:
                errors.append(f"RUNTIME-PLANE-MISSING {name}: {rel}")
    return errors


def validate(plugin_root: Path, data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    caps = data.get("capabilities")
    if not isinstance(caps, dict):
        return ["capabilities must be a mapping"]
    profiles = data.get("closure_profiles")
    if not isinstance(profiles, dict) or not profiles:
        errors.append("closure_profiles must be a non-empty mapping")
        profiles = {}
    if data.get("capability_planes") != list(CAPABILITY_PLANES):
        errors.append("capability_planes must declare the six frozen planes in order")

    discovered = {p.parent.name for p in (plugin_root / "skills").glob("*/SKILL.md")}
    declared = set(caps)
    fixture_paths = registered_fixture_paths(plugin_root)
    kernel_components, kernel_sha256 = _kernel_components(plugin_root)
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

        direct = row.get("capability_closure")
        if isinstance(direct, dict):
            errors.extend(_direct_closure_errors(
                plugin_root, name, row, direct, kernel_components, kernel_sha256
            ))
        else:
            profile_id = row.get("closure_profile")
            profile = profiles.get(profile_id)
            if not isinstance(profile, dict):
                errors.append(f"CAP-PLANE-MISSING {name}: unknown closure_profile {profile_id!r}")
            else:
                errors.extend(_profile_errors(
                    plugin_root, name, row, profile, fixture_paths, kernel_components
                ))

        if availability == "active":
            if mode == "deferred":
                errors.append(f"{name}: active capability cannot be deferred")
            if row.get("reason_code"):
                errors.append(f"{name}: active capability cannot carry reason_code")
            if mode == "script-backed" and not row.get("implementation"):
                errors.append(f"{name}: active script-backed capability needs implementation")
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
                prelude = "\n".join(skill_path.read_text(encoding="utf-8").splitlines()[:80])
                if reason_code not in prelude:
                    errors.append(
                        f"CAP-DEFERRED-UNDECLARED {name}: reason_code {reason_code!r} "
                        "is absent from the first 80 skill lines"
                    )
        elif availability == "external-dependent" and not row.get("provider"):
            errors.append(f"{name}: external-dependent capability needs provider")

        if isinstance(evidence, list) and SELF_TEST in evidence and availability == "active":
            errors.append(f"CAP-TEST-CIRCULAR {name}: capability smoke cannot be capability evidence")

    if data.get("schema_version") != "2.0.0":
        errors.append("schema_version must be 2.0.0")
    if data.get("authority") != "references/capabilities.yaml":
        errors.append("authority must name references/capabilities.yaml")
    return errors


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugin-root", default=None)
    args = parser.parse_args()
    root = Path(args.plugin_root).resolve() if args.plugin_root else Path(__file__).resolve().parent.parent
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
