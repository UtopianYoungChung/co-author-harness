#!/usr/bin/env python3
"""retirement-sweep-check — no retired or missing script cited as live.

Closes the release-gate header's long-deferred retirement-sweep gap
(docs/analysis/2026-07-07_full-links-coherence-audit.md §4 item 4).

Invariant: on the LIVE surfaces (references/, agents/, skills/, commands/,
root CLAUDE.md / AGENTS.md / README.md), every `scripts/<name>.py|.sh`
citation must either (a) resolve to an existing file under scripts/, or
(b) sit on a line carrying a historical marker (retired / removed /
historical / ...) per references/schemas/retired_surfaces.json.

Registered retired names get provenance in the finding; unregistered
missing names are UNKNOWN DANGLERS (typo or undeclared retirement) and
always block. CHANGELOG.md, docs/, releases/, scratch/ are out of scope
by design — history may speak freely there.

Exit 0 = clean; exit 1 = blockers.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
REGISTRY = PLUGIN_ROOT / "references" / "schemas" / "retired_surfaces.json"

LIVE_DIRS = ["references", "agents", "skills", "commands"]
LIVE_FILES = ["CLAUDE.md", "AGENTS.md", "README.md"]
CITE = re.compile(r"scripts/([A-Za-z0-9_\-.]+\.(?:py|sh))")


def live_surface_files() -> list[Path]:
    out = []
    for d in LIVE_DIRS:
        out.extend(sorted((PLUGIN_ROOT / d).rglob("*.md")))
        out.extend(sorted((PLUGIN_ROOT / d).rglob("*.yaml")))
    for f in LIVE_FILES:
        p = PLUGIN_ROOT / f
        if p.is_file():
            out.append(p)
    return out


def main() -> int:
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    markers = [m.lower() for m in reg["historical_markers"]]
    retired = reg["retired_scripts"]
    blockers: list[str] = []
    scanned = cited = 0

    for path in live_surface_files():
        scanned += 1
        rel = path.relative_to(PLUGIN_ROOT)
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
        ):
            for m in CITE.finditer(line):
                cited += 1
                name = m.group(1)
                if (PLUGIN_ROOT / "scripts" / name).is_file():
                    continue
                # missing target — line must carry a historical marker
                low = line.lower()
                if any(mk in low for mk in markers):
                    continue
                if name in retired:
                    meta = retired[name]
                    blockers.append(
                        f"{rel}:{lineno}: cites retired script {name!r} as live "
                        f"(retired_at: {meta.get('retired_at')}; successor: "
                        f"{meta.get('successor')}). Annotate the line with a "
                        f"historical marker or update the citation."
                    )
                else:
                    blockers.append(
                        f"{rel}:{lineno}: UNKNOWN DANGLER — cites nonexistent "
                        f"script {name!r} (not in retired_surfaces.json). Fix "
                        f"the citation or register the retirement."
                    )

    print("RETIREMENT SWEEP CHECK")
    print(f"- Registry: {REGISTRY.relative_to(PLUGIN_ROOT)} "
          f"({len(retired)} retired names)")
    print(f"- Live-surface files scanned: {scanned}; script citations: {cited}")
    print(f"- Blockers: {len(blockers)}")
    for b in blockers:
        print(f"  BLOCKER: {b}")
    return 1 if blockers else 0


if __name__ == "__main__":
    sys.exit(main())
