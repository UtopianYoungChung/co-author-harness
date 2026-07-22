#!/usr/bin/env python3
"""
Installs gate-first evaluator assets into a project folder.

Usage:
  python scripts/install_preflight_assets.py --project-root /abs/path/to/project [--overwrite]
"""

from __future__ import annotations

import argparse
from pathlib import Path


WRAPPER_CONTENT = """param(
  [string]$Date = (Get-Date -Format "yyyy-MM-dd"),
  [string]$PluginRoot = $env:AGENT_PLUGIN_ROOT
)

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

if (-not $PluginRoot -or -not (Test-Path $PluginRoot)) {
  if ($env:CLAUDE_PLUGIN_ROOT -and (Test-Path $env:CLAUDE_PLUGIN_ROOT)) {
    $PluginRoot = $env:CLAUDE_PLUGIN_ROOT
  } elseif ($env:CURSOR_PLUGIN_ROOT -and (Test-Path $env:CURSOR_PLUGIN_ROOT)) {
    $PluginRoot = $env:CURSOR_PLUGIN_ROOT
  }
}

if (-not $PluginRoot -or -not (Test-Path $PluginRoot)) {
  $Fallback = Resolve-Path (Join-Path $PSScriptRoot "..\\..\\.paper-package") -ErrorAction SilentlyContinue
  if ($Fallback) {
    $PluginRoot = $Fallback
  }
}

if (-not $PluginRoot -or -not (Test-Path $PluginRoot)) {
  Write-Error "Plugin root not found. Set AGENT_PLUGIN_ROOT (or CLAUDE_PLUGIN_ROOT/CURSOR_PLUGIN_ROOT) or pass -PluginRoot."
  exit 2
}

$GateScript = Join-Path $PluginRoot "scripts/sk20_preflight_gate.py"
$HealthScript = Join-Path $PluginRoot "scripts/coupling_health_report.py"

if (-not (Test-Path $GateScript)) {
  Write-Error "Missing gate script: $GateScript"
  exit 2
}
if (-not (Test-Path $HealthScript)) {
  Write-Error "Missing health script: $HealthScript"
  exit 2
}

Write-Host "[preflight] Running SK-20 deterministic gate for $ProjectRoot"
python "$GateScript" --project-root "$ProjectRoot" --date "$Date" --strict-exit
if ($LASTEXITCODE -ne 0) {
  Write-Host "[preflight] Gate failed; see reviews/sk20_noop_$Date.json"
  exit $LASTEXITCODE
}

Write-Host "[preflight] Updating coupling health report"
python "$HealthScript" --project-root "$ProjectRoot"

Write-Host "[preflight] Ready for Evaluator Step 0a+."
"""


CHECKLIST_CONTENT = """# Round Checklist — <PROJECT_NAME>

1. Run `scripts/run-evaluator-preflight.ps1`.
   - Default env var: `AGENT_PLUGIN_ROOT` (fallback: `CLAUDE_PLUGIN_ROOT` or `CURSOR_PLUGIN_ROOT`).
   - If needed, pass `-PluginRoot <path-to-co-author-harness-plugin-root>`.
2. If gate fails, read `reviews/sk20_noop_YYYY-MM-DD.json` and fix failed checks.
3. Run Evaluator Step 0a deterministic checks.
4. Run full review and confirm `reviews/graph_overlay_YYYY-MM-DD.md` behavior.
5. Refresh trend artifacts via `reviews/coupling_health.md`.
"""


def write_if_needed(path: Path, content: str, overwrite: bool) -> str:
    if path.exists() and not overwrite:
        return f"SKIP {path} (exists)"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"WRITE {path}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True, help="Absolute path to project root")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files")
    args = parser.parse_args()

    project_root = Path(args.project_root)
    from destination_capability import DestinationRefused, guard_project_root
    try:
        guard_project_root(project_root)
    except DestinationRefused as exc:
        print(f"[BLOCKER] {exc}")
        return 4
    if not project_root.exists():
        raise SystemExit(f"Project root not found: {project_root}")

    changes = []
    changes.append(
        write_if_needed(
            project_root / "scripts" / "run-evaluator-preflight.ps1",
            WRAPPER_CONTENT,
            args.overwrite,
        )
    )
    changes.append(
        write_if_needed(
            project_root / "reviews" / "round_checklist.md",
            CHECKLIST_CONTENT,
            args.overwrite,
        )
    )

    print("\n".join(changes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
