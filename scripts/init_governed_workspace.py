#!/usr/bin/env python3
"""init_governed_workspace - establish a governed workspace for an installed harness.

The producer boundary (AGENTS.md; scripts/destination_capability.py) refuses
every write outside the package when no workspace routing manifest can be
discovered (DEST-UNGOVERNED). The author's workspace already carries that
manifest; an installer anywhere else has none, so project bootstrap and every
governed writer refuse. This one-time, user-invoked setup step creates the
smallest workspace the harness recognises:

  <workspace>/governance/output-routing/output_routing.yaml   routing manifest
  <workspace>/outputs/co-author-harness/staging/              writable lane

The fail-closed rule is unchanged: a destination is writable only inside a
discovered workspace's staging or private-shipment lanes (or outside every
workspace once one is discovered). Projects then live in the staging lane,
<workspace>/outputs/co-author-harness/staging/<work-id>/<run-id>/.

The tool never writes inside the harness package, never nests one workspace
inside another, and never overwrites an existing manifest.

Usage:  python scripts/init_governed_workspace.py <workspace-dir> [--dry-run]
Exit:   0 initialized or already initialized; 2 refused (reason on stderr).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
import destination_capability as destination  # noqa: E402

MANIFEST_REL = Path("governance") / "output-routing" / "output_routing.yaml"
STAGING_REL = Path("outputs") / "co-author-harness" / "staging"


def _refuse(code: str, message: str) -> int:
    print(json.dumps({"status": "REFUSED", "code": code, "message": message}), file=sys.stderr)
    return 2


def _manifest_text(created_at: str) -> str:
    return (
        "# Routing manifest created by co-author-harness\n"
        "# scripts/init_governed_workspace.py. Its presence makes this directory a\n"
        "# governed workspace root for the harness producer boundary\n"
        "# (scripts/destination_capability.py). Harness project output belongs in\n"
        "# outputs/co-author-harness/staging/<work-id>/<run-id>/.\n"
        "schema_version: 1\n"
        "workspace_kind: harness-local\n"
        f"created_at: \"{created_at}\"\n"
        "routes: []\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create the routing manifest and staging lane of a governed workspace."
    )
    parser.add_argument("workspace", type=Path, help="directory to make a governed workspace root")
    parser.add_argument("--dry-run", action="store_true", help="report what would be created")
    args = parser.parse_args(argv)

    workspace = args.workspace.expanduser().resolve()
    harness = destination.HARNESS.resolve()
    if workspace == harness or harness in workspace.parents:
        return _refuse(
            destination.DEST_MISROUTED,
            f"{workspace} is inside the harness package; project output must never "
            "become package state. Choose a directory outside the plugin.",
        )
    if workspace in harness.parents:
        # The package may live inside a workspace (the author's layout), but a
        # manifest above the package would silently govern the package's own
        # neighbourhood; require that to be set up deliberately, not by this tool.
        return _refuse(
            "WORKSPACE-ENCLOSES-PACKAGE",
            f"{workspace} contains the harness package; create the workspace "
            "elsewhere or set up its governance by hand.",
        )

    manifest = workspace / MANIFEST_REL
    staging = workspace / STAGING_REL
    existing = destination.discovered_destination_workspace_root(workspace / "probe")
    if existing is not None and existing.resolve() != workspace:
        return _refuse(
            "WORKSPACE-NESTED",
            f"{workspace} is already inside the governed workspace {existing}; "
            "use that workspace's staging lane instead of nesting another.",
        )

    already = manifest.is_file()
    result = {
        "status": "ALREADY_INITIALIZED" if already else "INITIALIZED",
        "workspace": str(workspace),
        "manifest": str(manifest),
        "staging_lane": str(staging),
        "next": (
            f"create {staging / '<work-id>'}, then run "
            "python <package-root>/scripts/native_project_bootstrap.py "
            f"--project-root {staging / '<work-id>' / '<run-id>'} "
            "--project-name <id> --title <title> --intended-reader \"<reader>\""
        ),
    }
    if args.dry_run:
        result["status"] = "DRY_RUN_" + result["status"]
        print(json.dumps(result, indent=2))
        return 0

    if not already:
        manifest.parent.mkdir(parents=True, exist_ok=True)
        created_at = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        try:
            with manifest.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(_manifest_text(created_at.replace("+00:00", "Z")))
        except FileExistsError:
            result["status"] = "ALREADY_INITIALIZED"
    staging.mkdir(parents=True, exist_ok=True)
    if destination.classify(staging / "probe") != "staging":
        return _refuse(
            "WORKSPACE-UNRECOGNISED",
            f"{staging} does not classify as a staging lane after initialization",
        )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
