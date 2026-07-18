#!/usr/bin/env python3
"""commitment-interactions-check — declare-or-fail guard for the C-x pair space.

Introduced by docs/analysis/2026-07-06_systematic-improvement-plan.md §5 (WS-3).

The pairwise interaction space of the declared style commitments grows
quadratically; the C-6/C-8 collision was discovered by live-run failure.
This check moves collision discovery to design time:

Invariants:
  A) Commitment IDs in references/schemas/commitment_interactions.json exactly
     match the C-x rows of the STYLE_COMMITMENTS.md §1 table.
  B) Pair coverage is complete: C(n,2) entries, no duplicates, no absences.
     Adding C-9 without the 8 new pair entries is a BLOCKER.
  C) Every declared-tension / protective-overlap / meta-rule entry names a
     locus whose file exists and contains the anchor string (file-exists +
     anchor-string-present; section-level resolution is out of mechanical
     scope [AR-9a]).
  D) 'no-known-tension' entries are the explicit default and need no locus.

Exit 0 = clean; exit 1 = blockers found.
"""

from __future__ import annotations

import itertools
import json
import re
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
REGISTRY = PLUGIN_ROOT / "references" / "schemas" / "commitment_interactions.json"
STYLE = PLUGIN_ROOT / "references" / "STYLE_COMMITMENTS.md"

LOCUS_CLASSES = {"declared-tension", "protective-overlap", "meta-rule"}
VALID_CLASSES = LOCUS_CLASSES | {"no-known-tension"}


def commitments_from_style(text: str) -> set[str]:
    """C-x IDs from §1 table rows: lines starting `| **C-n** |`."""
    return set(re.findall(r"^\|\s*\*\*(C-\d+)\*\*\s*\|", text, re.M))


def main() -> int:
    blockers: list[str] = []

    if not REGISTRY.is_file():
        print(f"BLOCKER: registry missing: {REGISTRY}")
        return 1
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    declared_ids = list(registry.get("commitments", []))
    pairs = registry.get("pairs", [])

    # A) ID parity with STYLE_COMMITMENTS §1 table
    style_ids = commitments_from_style(STYLE.read_text(encoding="utf-8"))
    if set(declared_ids) != style_ids:
        missing = sorted(style_ids - set(declared_ids))
        extra = sorted(set(declared_ids) - style_ids)
        if missing:
            blockers.append(
                f"registry missing commitments present in STYLE_COMMITMENTS §1: "
                f"{missing} — every new commitment requires {len(declared_ids)} "
                f"new pair entries (declare-or-fail)"
            )
        if extra:
            blockers.append(
                f"registry declares commitments absent from STYLE_COMMITMENTS §1: {extra}"
            )

    # B) complete, duplicate-free pair coverage over the registry's own ID set
    expected = {tuple(sorted(p)) for p in itertools.combinations(declared_ids, 2)}
    seen: set[tuple[str, str]] = set()
    for entry in pairs:
        key = tuple(sorted(entry.get("pair", [])))
        if len(key) != 2:
            blockers.append(f"malformed pair entry: {entry.get('pair')!r}")
            continue
        if key in seen:
            blockers.append(f"duplicate pair entry: {key}")
        seen.add(key)
        cls = entry.get("class")
        if cls not in VALID_CLASSES:
            blockers.append(f"pair {key}: invalid class {cls!r}")
        # C) locus verification
        if cls in LOCUS_CLASSES:
            locus = entry.get("locus")
            if not locus:
                blockers.append(f"pair {key} ({cls}): no locus declared")
                continue
            locus_path = PLUGIN_ROOT / locus.get("file", "")
            if not locus_path.is_file():
                blockers.append(f"pair {key}: locus file missing: {locus.get('file')}")
                continue
            anchor = locus.get("anchor", "")
            if anchor and anchor not in locus_path.read_text(encoding="utf-8"):
                blockers.append(
                    f"pair {key}: anchor not found in {locus.get('file')}: {anchor!r}"
                )
    for absent in sorted(expected - seen):
        blockers.append(f"pair not declared: {absent} — add an entry (explicit "
                        f"'no-known-tension' is acceptable)")
    for orphan in sorted(seen - expected):
        blockers.append(f"pair references unknown commitment(s): {orphan}")

    print("COMMITMENT INTERACTIONS CHECK")
    print(f"- Registry: {REGISTRY.relative_to(PLUGIN_ROOT)}")
    print(f"- Commitments: {len(declared_ids)}; pairs declared: {len(seen)}/{len(expected)}")
    counts: dict[str, int] = {}
    for entry in pairs:
        counts[entry.get("class", "?")] = counts.get(entry.get("class", "?"), 0) + 1
    print(f"- Classes: {counts}")
    print(f"- Blockers: {len(blockers)}")
    for b in blockers:
        print(f"  BLOCKER: {b}")
    return 1 if blockers else 0


if __name__ == "__main__":
    sys.exit(main())
