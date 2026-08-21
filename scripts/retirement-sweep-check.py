#!/usr/bin/env python3
"""retirement-sweep-check — no retired or missing script cited as live.

Closes the release-gate header's long-deferred retirement-sweep gap
(docs/analysis/2026-07-07_full-links-coherence-audit.md §4 item 4).

Invariant: on the LIVE surfaces (references/, agents/, skills/,
root AGENTS.md / README.md), every `scripts/<name>.py|.sh`
citation must either (a) resolve to an existing file under scripts/, or
(b) sit on a line carrying a historical marker (retired / removed /
historical / ...) per references/schemas/retired_surfaces.json.

Registered retired names get provenance in the finding; unregistered
missing names are UNKNOWN DANGLERS (typo or undeclared retirement) and
always block. CHANGELOG.md, docs/, releases/, scratch/ are out of scope
by design — history may speak freely there.

Extended 2026-07-13 (audit C6): the registry's `retired_phrases` section
adds negative string assertions over the same live surfaces — stale
schema-count claims ("15-field", "30-trigger", ...) and retired ladder
vocabulary ("Lifecycle-Stage Ladder") block unless the line carries a
historical marker. Complements the snapshot-mode version-planes check,
which can only verify that registered assertions are present.

Exit 0 = clean; exit 1 = blockers.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
REGISTRY = PLUGIN_ROOT / "references" / "schemas" / "retired_surfaces.json"

LIVE_DIRS = ["references", "agents", "skills"]
LIVE_FILES = ["AGENTS.md", "README.md"]
CITE = re.compile(r"scripts/([A-Za-z0-9_\-.]+\.(?:py|sh))")
RETIRED_MILESTONE_SPLIT = ("M4a", "M4b")


def _is_archive_or_history(path: Path) -> bool:
    """Return whether *path* is structurally inside archival material."""
    return any(
        part.lower() in {"archive", "archives", "history", "historical"}
        for part in path.parts
    )


def retired_milestone_split_findings(
    path: Path, line: str, historical_markers: list[str]
) -> list[str]:
    """Return retired split tokens used in current voice on one live line."""
    if _is_archive_or_history(path):
        return []
    low = line.lower()
    if any(marker.lower() in low for marker in historical_markers):
        return []
    return [
        token
        for token in RETIRED_MILESTONE_SPLIT
        if re.search(rf"\b{re.escape(token)}\b", line)
    ]


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
    phrases = reg.get("retired_phrases", {})
    phrase_pairs = [(ph.lower(), ph) for ph in phrases]
    blockers: list[str] = []
    scanned = cited = phrase_hits = 0

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
            for token in retired_milestone_split_findings(rel, line, markers):
                blockers.append(
                    f"{rel}:{lineno}: retired milestone split token {token!r} "
                    "in current voice on a live role/package surface. Use orthogonal "
                    "unsplit M1-M5 milestones, or mark genuine history on the same line."
                )
            low_line = line.lower()
            if any(mk in low_line for mk in markers):
                continue
            for low_ph, ph in phrase_pairs:
                if low_ph in low_line:
                    phrase_hits += 1
                    meta = phrases[ph]
                    blockers.append(
                        f"{rel}:{lineno}: retired phrase {ph!r} in live voice "
                        f"(superseded_by: {meta.get('superseded_by')}). Update "
                        f"the claim or annotate the line with a historical "
                        f"marker."
                    )

    print("RETIREMENT SWEEP CHECK")
    print(f"- Registry: {REGISTRY.relative_to(PLUGIN_ROOT)} "
          f"({len(retired)} retired names)")
    print(f"- Live-surface files scanned: {scanned}; script citations: {cited}; "
          f"retired-phrase hits: {phrase_hits}")
    print(f"- Retired phrases registered: {len(phrases)}")
    print(f"- Blockers: {len(blockers)}")
    for b in blockers:
        print(f"  BLOCKER: {b}")
    return 1 if blockers else 0


if __name__ == "__main__":
    sys.exit(main())
