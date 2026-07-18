#!/usr/bin/env python3
"""SK-20 autonomous loop — deferred-only Wiki-write entry (CD2).

Canonical Wiki mutation and graph rebuild are unavailable. This entry returns a
structured deferred result before any Wiki directory creation or filesystem write.

Graph authority (GRAPH_GOVERNED_GENERATION_UNAVAILABLE) is a separate plane.
A future governed-graph unlock must never unlock Wiki mutation from this entry.
"""

from __future__ import annotations

import argparse
import json


DEFERRED_RESULT = {
    "status": "deferred",
    "reason_code": "WIKI_WRITE_TRANSACTION_UNAVAILABLE",
    "wiki_mutation_performed": False,
    "overlay_performed": False,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "SK-20 autonomous loop (deferred). Canonical Wiki mutation and "
            "graph rebuild are unavailable under WIKI_WRITE_TRANSACTION_UNAVAILABLE."
        )
    )
    # Accept legacy flags so existing callers fail closed without inventing writes.
    parser.add_argument("--project-root", required=False)
    parser.add_argument("--wiki-path", required=False)
    parser.add_argument("--manuscript-path", required=False)
    parser.add_argument("--references-path", required=False)
    parser.add_argument("--classification-path", required=False)
    parser.add_argument("--date", required=False)
    parser.add_argument("--project-claude-path", required=False)
    parser.add_argument("--allow-ancestor-claude", action="store_true")
    parser.add_argument("--allow-missing-project-claude", action="store_true")
    parser.add_argument("--wiki-linked", required=False)
    parser.add_argument("--coupling-e-on-review", required=False)
    parser.add_argument("--allow-legacy-graph-confidence", required=False)
    parser.add_argument("--graphify-src-root", required=False)
    parser.add_argument("--ingest-all-bib-entries", action="store_true")
    parser.parse_args(argv)

    print(json.dumps(DEFERRED_RESULT, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
