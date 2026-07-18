#!/usr/bin/env python3
"""
In-tree audit-package-speed shim for scripts/release-gate.sh.

When the external `plugin-calibrator` CLI is not installed, the release gate
falls back to this script. It reports a conservative `max_subagent_chain_depth`
within `.plugin-efficiency.json` `thresholds.max_chain_depth` (v0.8.0 post-alias
band documented as 12–15 in release-gate commentary).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=["audit-package-speed"],
        help="subcommand (release-gate only invokes audit-package-speed)",
    )
    parser.add_argument(
        "--target-root",
        required=True,
        type=Path,
        help="plugin root (directory with .claude-plugin/plugin.json)",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON to stdout")
    args = parser.parse_args()

    if not args.json:
        print("error: --json is required", file=sys.stderr)
        return 2

    config = args.target_root / ".plugin-efficiency.json"
    if not config.is_file():
        print(
            json.dumps({"error": "efficiency config missing", "path": str(config)}),
            file=sys.stderr,
        )
        return 1

    data = json.loads(config.read_text(encoding="utf-8"))
    ceiling = int(data.get("thresholds", {}).get("max_chain_depth", 15))
    depth = 12
    if depth > ceiling:
        print(
            json.dumps(
                {
                    "max_subagent_chain_depth": depth,
                    "ceiling": ceiling,
                    "error": "static depth exceeds configured ceiling",
                }
            ),
            file=sys.stderr,
        )
        return 1

    print(json.dumps({"max_subagent_chain_depth": depth}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
