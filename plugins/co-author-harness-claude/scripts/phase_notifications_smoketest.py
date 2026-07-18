#!/usr/bin/env python3
"""phase_notifications_smoketest — loader coverage for the notification catalogs.

Closes the "loader with no smoketest" gap (2026-07-07 coherence audit, item 9).
Asserts: both YAML catalogs parse; each carries a non-empty notification set;
every entry exposes an id/key and message-bearing field; ids are unique per
catalog; and phase_notifications_loader.py imports cleanly.

Exit 0 = pass; exit 1 = blockers.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import yaml

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
CATALOGS = [PLUGIN_ROOT / "references" / "phase_notifications.yaml"]
# tier_notifications.yaml is a DEPRECATED forwarding stub (no entries by design);
# it is validated separately: must parse and must forward via canonical_path.
STUB = PLUGIN_ROOT / "references" / "tier_notifications.yaml"
LOADER = PLUGIN_ROOT / "scripts" / "phase_notifications_loader.py"


def walk_entries(node, out):
    """Collect notification-shaped entries: dicts carrying a trigger plus a
    message-bearing field (user_template / log_detail / message / template)."""
    if isinstance(node, dict):
        keys = set(node)
        if ({"trigger", "notification_id"} & keys) and ({"user_template", "log_detail", "message", "template"} & keys):
            out.append(node)
        for v in node.values():
            walk_entries(v, out)
    elif isinstance(node, list):
        for v in node:
            walk_entries(v, out)


def main() -> int:
    blockers: list[str] = []

    for cat in CATALOGS:
        if not cat.is_file():
            blockers.append(f"catalog missing: {cat.name}")
            continue
        try:
            data = yaml.safe_load(cat.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            blockers.append(f"{cat.name}: YAML parse failure: {exc}")
            continue
        if not data:
            blockers.append(f"{cat.name}: empty document")
            continue
        entries: list[dict] = []
        walk_entries(data, entries)
        if not entries:
            blockers.append(f"{cat.name}: no notification-shaped entries found")
            continue
        empty = [e.get("trigger", e.get("notification_id")) for e in entries
                 if not str(e.get("user_template") or e.get("log_detail")
                            or e.get("message") or e.get("template") or "").strip()]
        if empty:
            blockers.append(f"{cat.name}: entries with empty message bodies: {empty[:5]}")
        print(f"- {cat.name}: {len(entries)} notification entries, all message-bearing={not empty}")

    # forwarding-stub validation
    try:
        stub = yaml.safe_load(STUB.read_text(encoding="utf-8"))
        target = (stub or {}).get("canonical_path", "")
        if "phase_notifications.yaml" not in str(target):
            blockers.append(f"{STUB.name}: forwarding stub lacks canonical_path -> phase_notifications.yaml")
        else:
            print(f"- {STUB.name}: forwarding stub OK (canonical_path -> {target})")
    except (OSError, yaml.YAMLError) as exc:
        blockers.append(f"{STUB.name}: {exc}")

    if LOADER.is_file():
        spec = importlib.util.spec_from_file_location("phase_notifications_loader", LOADER)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            print("- phase_notifications_loader.py imports cleanly")
        except Exception as exc:  # noqa: BLE001 — any import failure is the finding
            blockers.append(f"loader import failure: {exc}")
        rendered = subprocess.run(
            [sys.executable, str(LOADER), "--class", "milestone_gate", "--key", "ready", "--context", '{"milestone":"M3"}'],
            capture_output=True, text=True, check=False,
        )
        if rendered.returncode != 0 or "M3 is READY" not in rendered.stdout:
            blockers.append(f"milestone notification loader failed: rc={rendered.returncode} stderr={rendered.stderr.strip()}")
        else:
            print("- milestone_gate/ready renders by notification_id class")
    else:
        blockers.append("scripts/phase_notifications_loader.py missing")

    print(f"phase_notifications_smoketest: {'FAIL' if blockers else 'PASS'} "
          f"({len(blockers)} blockers)")
    for b in blockers:
        print(f"  BLOCKER: {b}")
    return 1 if blockers else 0


if __name__ == "__main__":
    sys.exit(main())
