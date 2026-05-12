"""Audit orchestrator — runs every audit_* module against a target file.

Single entry point so skills and agents invoke ONE command and consume ONE
findings.json artifact. Adding a new auditor means appending to AUDITORS
below; the schema and run-surface do not change.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable, List, Tuple

from audit_style import (
    audit_absolutes,
    audit_emdash,
    audit_llm_tics,
    audit_passive_voice,
    audit_sentence_length,
    audit_voice,
)
from schema import Finding, FindingsReport

Auditor = Callable[[str, Path], List[Finding]]

AUDITORS: List[Tuple[str, Auditor]] = [
    ("absolutes", audit_absolutes),
    ("emdash", audit_emdash),
    ("llm_tics", audit_llm_tics),
    ("voice", audit_voice),
    ("sentence_length", audit_sentence_length),
    ("passive_voice", audit_passive_voice),
]


def audit_target(path: Path) -> FindingsReport:
    text = path.read_text(encoding="utf-8")
    report = FindingsReport(target=path.as_posix())
    for _name, fn in AUDITORS:
        report.extend(fn(text, path))
    return report


def main(argv: List[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path)
    parser.add_argument("--out", type=Path, default=Path("reviews/findings.json"))
    parser.add_argument("--stdout", action="store_true", help="Print JSON instead of writing")
    args = parser.parse_args(argv)

    if not args.target.is_file():
        print(f"[BLOCKER] target not found: {args.target}", file=sys.stderr)
        return 2

    report = audit_target(args.target)
    if args.stdout:
        import json
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    else:
        report.write(args.out)
        counts = report.counts()
        print(
            f"OK wrote {args.out} — {counts['total']} findings "
            f"(default: {counts['by_severity'].get('default', 0)}, "
            f"inviolable: {counts['by_severity'].get('inviolable', 0)})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
