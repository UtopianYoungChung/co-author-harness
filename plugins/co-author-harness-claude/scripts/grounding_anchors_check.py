#!/usr/bin/env python3
"""Verify that references/GROUNDING_PROTOCOL.md exposes a stable HTML anchor
above every `## Rule N` heading. The forthcoming audit_citations.py (PR-4)
resolves [GP §N] citations against these anchors; if an anchor is dropped
or renamed during a refactor, citation grounding silently breaks.

Run as part of release-gate.sh.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
GP = HARNESS / "references" / "GROUNDING_PROTOCOL.md"

RULE_HEADING_RE = re.compile(r"^## Rule (\d+[a-z]?) ", re.MULTILINE)
ANCHOR_RE = re.compile(r'<a id="gp-(\d+[a-z]?)"></a>')


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if not GP.is_file():
        print(f"[BLOCKER] missing {GP}", file=sys.stderr)
        return 2

    text = GP.read_text(encoding="utf-8")
    rules = RULE_HEADING_RE.findall(text)
    anchors = set(ANCHOR_RE.findall(text))

    if not rules:
        print("[BLOCKER] no Rule headings found", file=sys.stderr)
        return 1

    missing = [r for r in rules if r not in anchors]
    if missing:
        print(
            f"[BLOCKER] GROUNDING_PROTOCOL.md missing stable anchors for "
            f"rules: {missing}. Add `<a id=\"gp-N\"></a>` directly above the "
            f"`## Rule N` heading.",
            file=sys.stderr,
        )
        return 1

    # Each anchor must immediately precede its rule heading (within 2 lines)
    for rule in rules:
        pat = re.compile(
            rf'<a id="gp-{re.escape(rule)}"></a>\s*\n## Rule {re.escape(rule)} '
        )
        if not pat.search(text):
            print(
                f"[BLOCKER] anchor gp-{rule} is present but not directly "
                f"above `## Rule {rule}`. Anchors must precede their heading.",
                file=sys.stderr,
            )
            return 1

    print(f"OK GROUNDING_PROTOCOL anchors valid ({len(rules)} rules)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
