#!/usr/bin/env python3
"""Validate Contract Kernel identity, component hashes, and coherence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


EXPECTED_PHASES = ["Ph1", "Ph2", "Ph3", "Ph4"]
EXPECTED_MILESTONES = ["M1", "M2", "M3", "M4", "M5"]
REQUIRED_COMPONENT_IDS = {
    "lifecycle-transitions", "role-output-machine-contract", "phase-state",
    "assignment-process", "milestone-handoff", "agent-contracts",
    "full-run-contract", "grounding-protocol", "artefact-schema",
    "course-essay-milestones", "reader-accessibility",
    "assignment-receipt-schema", "assignment-receipt-template",
    "assignment-process-gate", "assignment-dispatch-preflight",
    "assignment-receipt-transaction", "assignment-writer-commit",
    "assignment-receipt-invalidate", "assignment-receipt-recover",
}


def _sha256(path: Path) -> str:
    # Bind text contracts to repository content, not a checkout's CRLF policy.
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _safe_file(root: Path, rel: Any) -> Path | None:
    if not isinstance(rel, str) or not rel or "\\" in rel:
        return None
    candidate = Path(rel)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        return None
    return resolved if resolved.is_file() else None


def validate(root: Path, data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != "1.0.0":
        errors.append("schema_version must be 1.0.0")
    if not data.get("kernel_id"):
        errors.append("kernel_id is required")
    if data.get("repository_policy", {}).get("single_branch") != "main":
        errors.append("repository_policy.single_branch must be main")
    if data.get("lifecycle", {}).get("phases") != EXPECTED_PHASES:
        errors.append("lifecycle phases must be Ph1, Ph2, Ph3, Ph4")
    if data.get("lifecycle", {}).get("milestones") != EXPECTED_MILESTONES:
        errors.append("lifecycle milestones must be M1 through M5")

    lifecycle = data.get("lifecycle", {})
    transition_path = _safe_file(root, lifecycle.get("transition_authority"))
    role_path = _safe_file(root, lifecycle.get("role_output_authority"))
    if transition_path is None:
        errors.append("lifecycle.transition_authority is missing or unsafe")
    else:
        transition_contract = json.loads(transition_path.read_text(encoding="utf-8"))
        state_rows = transition_contract.get("states", [])
        state_ids = [row.get("id") for row in state_rows if isinstance(row, dict)]
        expected_states = EXPECTED_PHASES[:3] + ["Ph3_converged", EXPECTED_PHASES[3]]
        if state_ids != expected_states:
            errors.append("transition authority lifecycle states are incoherent")
    if role_path is None:
        errors.append("lifecycle.role_output_authority is missing or unsafe")
    else:
        role_contract = json.loads(role_path.read_text(encoding="utf-8"))
        role_milestones = role_contract.get("milestones", {})
        expected_paths = {
            "M1": "research_notes/project_memo.md",
            "M2": "research_notes/annotated_references.md",
            "M3": "manuscript/outline.md",
            "M4": "manuscript/main.md",
        }
        if {
            key: role_milestones.get(key, {}).get("deliverable_path")
            for key in expected_paths
        } != expected_paths:
            errors.append("role output authority M1-M4 paths are incoherent")

    cap_path = data.get("capability_registry")
    if _safe_file(root, cap_path) is None:
        errors.append("capability_registry path is missing")

    seen: set[str] = set()
    components = data.get("components")
    if not isinstance(components, list) or not components:
        return errors + ["components must be a non-empty list"]
    for component in components:
        if not isinstance(component, dict):
            errors.append("component row must be an object")
            continue
        cid = component.get("id")
        if not isinstance(cid, str) or not cid:
            errors.append("component id is required")
        elif cid in seen:
            errors.append(f"duplicate component id: {cid}")
        else:
            seen.add(cid)
        rel = component.get("path")
        expected = component.get("sha256")
        bound_path = _safe_file(root, rel)
        if bound_path is None:
            errors.append(f"{cid}: component path is missing or unsafe")
            continue
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            errors.append(f"{cid}: invalid sha256")
        elif _sha256(bound_path) != expected:
            errors.append(f"{cid}: content hash drift")
        if not isinstance(component.get("migration_ids"), list):
            errors.append(f"{cid}: migration_ids must be a list")
    missing_components = sorted(REQUIRED_COMPONENT_IDS - seen)
    if missing_components:
        errors.append(f"required components missing: {', '.join(missing_components)}")

    identity_path = _safe_file(root, data.get("plugin_identity_source"))
    if identity_path is None:
        errors.append("plugin_identity_source is missing or unsafe")
        identity_path = root / ".claude-plugin" / "plugin.json"
    plugin = json.loads(identity_path.read_text(encoding="utf-8"))
    marketplace = json.loads((root / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list) or not plugins or not isinstance(plugins[0], dict):
        errors.append("marketplace plugins[0] entry is required")
        market_license = None
    else:
        market_license = plugins[0].get("license")
    readme = (root / "README.md").read_text(encoding="utf-8")
    license_text = (root / "LICENSE").read_text(encoding="utf-8")
    if plugin.get("license") != "MIT" or market_license != "MIT":
        errors.append("plugin and marketplace license must be MIT")
    if "License-MIT" not in readme or "MIT License" not in license_text:
        errors.append("README and LICENSE must declare MIT")
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
        data = json.loads(
            (root / "references" / "contract_kernel.v1.json").read_text(encoding="utf-8")
        )
        errors = validate(root, data)
    except Exception as exc:  # noqa: BLE001
        print(f"BLOCK: Contract Kernel could not be validated: {exc}")
        return 1
    for error in errors:
        print(f"BLOCK: {error}")
    if errors:
        print(f"contract-kernel-check: FAIL ({len(errors)} blockers)")
        return 1
    kernel_digest = _sha256(root / "references" / "contract_kernel.v1.json")
    print(
        f"contract-kernel-check: PASS ({len(data['components'])} components; "
        f"kernel_sha256={kernel_digest})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
