#!/usr/bin/env python3
"""v0.15.0-pre PR-4d — token-budget measurement (warn-only).

Measures every file in `agents/`, `references/`, `skills/*/SKILL.md`, and
`references/_snippets/` against per-class warn/fail thresholds using the
cl100k_base encoding (tiktoken). At PR-4d the check is **strictly
warn-only**: any threshold breach prints a WARN line to stdout but does
not increment release-gate BLOCKERS. The aim is measurement-first
evidence for the Reflector split (PR-4c) and any subsequent agent slim,
not enforcement.

Per-class budgets (from the v0.15.0 architecture):

    File class                  Warn      Fail (advisory)
    --------------------------  --------  -----------------
    agents/*.md                 > 300     > 700  tokens
    references/*.md             > 600     > 1000 tokens
    skills/*/SKILL.md           > 120     > 250  tokens
    references/_snippets/*.md   > 40      > 60   tokens

The "fail" column is advisory only at PR-4d; a future PR (after the
Reflector split) may promote breaches at the fail threshold to a real
BLOCKER. For now both warn and fail are surfaced as WARN tier so writers
get the signal without the work being blocked.

Output
------
Prints a per-class summary plus the **top-10 largest files across the
package** so PR-4c has a measured target list. A machine-readable
`reviews/token_budget_report.json` is also written when invoked with
`--out`. Exit code is always 0 unless tiktoken is unavailable or a path
read fails outright (in which case exit 2 — environment error).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, List, Tuple

HARNESS = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Class definitions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FileClass:
    name: str
    glob_pattern: str       # rglob pattern relative to HARNESS
    warn_tokens: int
    fail_tokens: int
    base: str               # root directory under HARNESS

    def iter_paths(self) -> Iterable[Path]:
        base_dir = HARNESS / self.base
        if not base_dir.is_dir():
            return
        for p in sorted(base_dir.rglob(self.glob_pattern)):
            yield p


FILE_CLASSES: List[FileClass] = [
    FileClass(
        name="agents",
        base="agents",
        glob_pattern="*.md",
        warn_tokens=300,
        fail_tokens=700,
    ),
    FileClass(
        name="references (non-snippet)",
        base="references",
        glob_pattern="*.md",
        warn_tokens=600,
        fail_tokens=1000,
    ),
    FileClass(
        name="skills",
        base="skills",
        glob_pattern="SKILL.md",
        warn_tokens=120,
        fail_tokens=250,
    ),
    FileClass(
        name="snippets",
        base="references/_snippets",
        glob_pattern="*.md",
        warn_tokens=40,
        fail_tokens=60,
    ),
]


@dataclass
class FileReport:
    path: str
    cls: str
    tokens: int
    warn_threshold: int
    fail_threshold: int
    status: str             # "ok" | "warn" | "fail"


@dataclass
class BudgetReport:
    schema_version: str = "0.15.0-pre"
    total_files: int = 0
    by_class: dict = field(default_factory=dict)
    breaches: List[FileReport] = field(default_factory=list)
    top10_largest: List[FileReport] = field(default_factory=list)
    always_loaded_floor_tokens: int = 0


# ---------------------------------------------------------------------------
# Counting
# ---------------------------------------------------------------------------


def _get_encoder():
    try:
        import tiktoken
    except ImportError as exc:
        raise SystemExit(
            f"[BLOCKER] tiktoken is required for the token-budget check; "
            f"install via `pip install tiktoken`. ({exc})"
        )
    return tiktoken.get_encoding("cl100k_base")


def count_tokens(path: Path, encoder) -> int:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SystemExit(f"[BLOCKER] cannot read {path}: {exc}")
    return len(encoder.encode(text))


def classify(tokens: int, warn: int, fail: int) -> str:
    if tokens > fail:
        return "fail"
    if tokens > warn:
        return "warn"
    return "ok"


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


# References that PR-4b designated as "always-loaded floor."
ALWAYS_LOADED_FILES = [
    Path("references/GROUNDING_PROTOCOL.md"),
    Path("references/CLAUDE.md"),
    Path("references/MANIFEST.md"),
]


def _exclude_snippets_from_references(path: Path) -> bool:
    """References class measures non-snippet refs only; snippets have their
    own class with a tighter budget."""
    rel = path.relative_to(HARNESS)
    return "_snippets" in rel.parts


def build_report() -> BudgetReport:
    encoder = _get_encoder()
    report = BudgetReport()

    all_files: List[FileReport] = []
    for cls in FILE_CLASSES:
        per_class_ok = 0
        per_class_warn = 0
        per_class_fail = 0
        for p in cls.iter_paths():
            # The references class must skip the _snippets/ subtree.
            if cls.name.startswith("references") and _exclude_snippets_from_references(p):
                continue
            tokens = count_tokens(p, encoder)
            status = classify(tokens, cls.warn_tokens, cls.fail_tokens)
            fr = FileReport(
                path=p.relative_to(HARNESS).as_posix(),
                cls=cls.name,
                tokens=tokens,
                warn_threshold=cls.warn_tokens,
                fail_threshold=cls.fail_tokens,
                status=status,
            )
            all_files.append(fr)
            report.total_files += 1
            if status == "ok":
                per_class_ok += 1
            elif status == "warn":
                per_class_warn += 1
                report.breaches.append(fr)
            else:
                per_class_fail += 1
                report.breaches.append(fr)
        report.by_class[cls.name] = {
            "warn_threshold": cls.warn_tokens,
            "fail_threshold": cls.fail_tokens,
            "ok": per_class_ok,
            "warn": per_class_warn,
            "fail": per_class_fail,
            "total": per_class_ok + per_class_warn + per_class_fail,
        }

    report.top10_largest = sorted(
        all_files, key=lambda f: f.tokens, reverse=True
    )[:10]

    floor_total = 0
    for rel in ALWAYS_LOADED_FILES:
        p = HARNESS / rel
        if p.is_file():
            floor_total += count_tokens(p, encoder)
    report.always_loaded_floor_tokens = floor_total

    return report


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def _emit(report: BudgetReport, *, verbose: bool) -> None:
    print(f"token_budget_check (warn-only, cl100k_base, PR-4d)")
    print(f"  total files measured: {report.total_files}")
    print(f"  always-loaded prelude floor: "
          f"{report.always_loaded_floor_tokens} tokens "
          f"(target: <= 8000 per v0.15.0 architecture)")
    print()
    print("Per-class summary:")
    for cls_name, summary in report.by_class.items():
        print(
            f"  {cls_name:30s}  ok={summary['ok']:>3}  "
            f"warn={summary['warn']:>3}  fail={summary['fail']:>3}  "
            f"(warn>{summary['warn_threshold']}, "
            f"fail>{summary['fail_threshold']} tokens)"
        )
    print()
    print(f"Threshold breaches ({len(report.breaches)} files):")
    if not report.breaches:
        print("  (none — every measured file is within its warn threshold)")
    else:
        # Sort breaches by severity then size descending
        order = {"fail": 0, "warn": 1}
        for fr in sorted(report.breaches,
                          key=lambda f: (order.get(f.status, 9), -f.tokens)):
            tag = "FAIL" if fr.status == "fail" else "WARN"
            print(
                f"  [{tag}] {fr.tokens:>5} tok ({fr.cls})  {fr.path}  "
                f"(warn>{fr.warn_threshold}, fail>{fr.fail_threshold})"
            )
    print()
    print("Top-10 largest files across the package "
          "(PR-4c target list):")
    for fr in report.top10_largest:
        tag = fr.status.upper() if fr.status != "ok" else "ok  "
        print(f"  [{tag}] {fr.tokens:>5} tok  {fr.path}")
    print()
    print("NOTE: warn-only at PR-4d. Breaches do not block release-gate.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: List[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, default=None,
                        help="Optional: write reviews/token_budget_report.json")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress per-file output (still writes --out)")
    args = parser.parse_args(argv)

    if args.out:
        from destination_capability import DestinationRefused, assert_writable
        try:
            assert_writable(args.out.resolve(), purpose="token-budget report output")
        except DestinationRefused as exc:
            print(f"[BLOCKER] {exc}", file=sys.stderr)
            return 4

    report = build_report()

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(
                {
                    "schema_version": report.schema_version,
                    "total_files": report.total_files,
                    "always_loaded_floor_tokens": report.always_loaded_floor_tokens,
                    "by_class": report.by_class,
                    "breaches": [asdict(f) for f in report.breaches],
                    "top10_largest": [asdict(f) for f in report.top10_largest],
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    if not args.quiet:
        _emit(report, verbose=False)

    # ALWAYS exit 0 at PR-4d (measurement-first; warn-only). A future PR may
    # promote `fail`-tier breaches to a real exit-1 BLOCKER.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
