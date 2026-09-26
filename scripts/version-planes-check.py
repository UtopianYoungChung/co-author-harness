#!/usr/bin/env python3
"""version-planes-check — snapshot-mode guard for non-package version planes.

Introduced by docs/analysis/2026-07-06_systematic-improvement-plan.md §4 (WS-2).

The package version plane is owned by version.json and validated
by scripts/version-check.py. This check covers the planes version-check.py does
not: lifecycle_ladder, phase_state_schema, evaluator_envelope,
stage_profile_vocabulary — as recorded in
references/schemas/version_planes.json (snapshot mode).

Invariants:
  A) Every snapshotted assertion string is still present verbatim in its file.
     A file that changed its version assertion without updating the registry
     is silent drift -> BLOCKER.
  B) No NEW distinct value for a plane appears in any registered file
     (fork-widening). Scanning is bounded to files named in the plane's
     assertions -> zero false positives on historical narrative elsewhere.
  C) Every registered file and every plane authority file exists.
  D) The package plane delegates: version.json must parse and carry a version.

Exit 0 = clean; exit 1 = blockers found.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
REGISTRY = PLUGIN_ROOT / "references" / "schemas" / "version_planes.json"


def main() -> int:
    blockers: list[str] = []

    if not REGISTRY.is_file():
        print(f"BLOCKER: registry missing: {REGISTRY}")
        return 1
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    planes = registry.get("planes", {})

    # D) package delegation
    manifest = PLUGIN_ROOT / "version.json"
    if not manifest.is_file():
        manifest = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
    try:
        version = json.loads(manifest.read_text(encoding="utf-8")).get("version")
        if not version:
            blockers.append("package: version.json has no version field")
    except (OSError, json.JSONDecodeError) as exc:
        blockers.append(f"package: cannot read version.json ({exc})")

    for plane_name, plane in planes.items():
        if plane_name == "package":
            continue

        # C) authority exists
        authority = plane.get("authority", "")
        if authority and not (PLUGIN_ROOT / authority).is_file():
            blockers.append(f"{plane_name}: authority file missing: {authority}")

        allowed = set(plane.get("allowed_values", []))
        patterns = [re.compile(p) for p in plane.get("widening_patterns", [])]
        registered_files = {a["file"] for a in plane.get("assertions", [])}

        file_texts: dict[str, str] = {}
        for rel in sorted(registered_files):
            path = PLUGIN_ROOT / rel
            if not path.is_file():
                blockers.append(f"{plane_name}: registered file missing: {rel}")
                continue
            file_texts[rel] = path.read_text(encoding="utf-8")

        # A) assertions still present verbatim
        for entry in plane.get("assertions", []):
            rel, assertion = entry["file"], entry["assertion"]
            text = file_texts.get(rel)
            if text is not None and assertion not in text:
                blockers.append(
                    f"{plane_name}: DRIFT — assertion no longer present in {rel}: "
                    f"{assertion!r}. Update the file back, or re-snapshot the "
                    f"registry deliberately."
                )

        # B) fork-widening inside registered files
        for rel, text in file_texts.items():
            for pat in patterns:
                for match in pat.finditer(text):
                    value = match.group(1)
                    if value not in allowed:
                        blockers.append(
                            f"{plane_name}: FORK-WIDENING — new value "
                            f"{value!r} in {rel} (allowed: {sorted(allowed)}). "
                            f"Register it deliberately or revert."
                        )

    print("VERSION PLANES CHECK (snapshot mode)")
    print(f"- Registry: {REGISTRY.relative_to(PLUGIN_ROOT)}")
    print(f"- Planes: {', '.join(planes)}")
    print(f"- Blockers: {len(blockers)}")
    for b in blockers:
        print(f"  BLOCKER: {b}")
    return 1 if blockers else 0


if __name__ == "__main__":
    sys.exit(main())
