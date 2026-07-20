#!/usr/bin/env python3
"""full_run_completeness_report - post-hoc detector for narrated / artefact-less runs.

WHY THIS EXISTS
---------------
In the Cowork desktop host, plugin PreToolUse hooks do not fire
(--setting-sources user excludes plugin scope; see the enforcement-hardening
plan and anthropics/claude-code#27398), so the FULL_RUN_CONTRACT cannot be
*prevented* from being bypassed there. This script is the DETECTION half: run it
against wherever a "harness full run" claimed to work, and it reports whether the
run actually produced a lifecycle, or merely narrated one.

It is the mechanical form of the question the 2026-07-17 and 2026-07-18 runs both
failed: "did a project, milestone state, and terminal evidence actually get
written, or is there just an essay and a summary sentence?"

COMPOSE, DO NOT PARAPHRASE
--------------------------
This script never re-implements the fifteen terminal requirements. It DELEGATES
every lifecycle-truth judgement to scripts/full_run_contract_check.py and reports
that subprocess's exit code and JSON verbatim. The only facts it decides itself
are structural file-presence facts (is there a reviews/phase_state.json at all),
used solely to tell "no project scaffold whatsoever" (the narrated-run
fingerprint) apart from "project exists but is incomplete".

USAGE
-----
  # evaluate one known project root
  python scripts/full_run_completeness_report.py --project-root <path>

  # scan a tree (e.g. a Workbench) for candidate project roots and grade each
  python scripts/full_run_completeness_report.py --search-root <dir>

  # also grade a location where the run was expected to leave a project
  python scripts/full_run_completeness_report.py --search-root <dir> \
      --expected-root <claimed-run-location>

  # machine-readable
  python scripts/full_run_completeness_report.py --search-root <dir> --json

EXIT CODES
  0  every evaluated target is COMPLETE (terminal earned)
  1  at least one target is INCOMPLETE
  2  no project scaffold found under a --search-root, or --project-root has none
     (the strongest signal: a full run was requested and no lifecycle exists)
  3  authoritative gate could not form a verdict, usage, or internal error
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
GATE = HERE / "full_run_contract_check.py"

# structural markers of a native project (file-presence only; not lifecycle truth)
PHASE_STATE = ("reviews", "phase_state.json")
CONTRACT = ("reviews", "assignment_contract.json")


def _has(root: Path, parts: tuple[str, ...]) -> bool:
    return root.joinpath(*parts).is_file()


def _gate_terminal(root: Path) -> tuple[int, str]:
    """Delegate the completeness verdict to the authoritative gate."""
    proc = subprocess.run(
        [sys.executable, str(GATE), "terminal", "--project-root", str(root)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return proc.returncode, (proc.stdout or proc.stderr).strip()


def evaluate(root: Path) -> dict:
    """Grade one candidate project root. Returns a structured verdict record."""
    has_ps = _has(root, PHASE_STATE)
    has_ct = _has(root, CONTRACT)
    if not has_ps and not has_ct:
        return {
            "project_root": str(root),
            "verdict": "NO-PROJECT",
            "detail": "no reviews/phase_state.json and no reviews/assignment_contract.json "
                      "-- this is the narrated-run fingerprint: a deliverable may exist, "
                      "but no lifecycle was created.",
            "exit_hint": 2,
        }
    rc, out = _gate_terminal(root)
    if rc == 0:
        return {"project_root": str(root), "verdict": "COMPLETE",
                "detail": "full_run_contract_check terminal exit 0 -- all fifteen "
                          "requirements met.", "gate_output": out, "exit_hint": 0}
    if rc == 4:
        return {"project_root": str(root), "verdict": "INCOMPLETE",
                "detail": "full_run_contract_check terminal refused the claim "
                          "(exit 4) -- see findings.",
                "gate_output": out, "exit_hint": 1}
    return {"project_root": str(root), "verdict": "UNVERIFIABLE",
            "detail": f"full_run_contract_check terminal exit {rc} -- the "
                      "authoritative gate could not form a verdict.",
            "gate_output": out, "exit_hint": 3}


def discover(search_root: Path, expected_roots: list[Path] | None = None) -> list[Path]:
    """Either native scaffold marker makes its containing directory a candidate.
    Explicit expected roots are retained even inside a mixed tree.  Discovery
    cannot infer that an arbitrary loose document was the output of a claimed
    run; callers name that location with ``--expected-root``."""
    roots = {
        p.parent.parent
        for marker in (PHASE_STATE[-1], CONTRACT[-1])
        for p in search_root.rglob(marker)
        if p.parent.name == "reviews"
    }
    roots.update(Path(p) for p in (expected_roots or []))
    roots = sorted(roots)
    return roots if roots else [search_root]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--project-root", type=Path)
    g.add_argument("--search-root", type=Path)
    ap.add_argument("--expected-root", type=Path, action="append", default=[],
                    help="location where a claimed run was expected to create a "
                         "project; repeatable and valid with --search-root")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = ap.parse_args(argv)

    if not GATE.is_file():
        print(f"[ERROR] cannot find authoritative gate at {GATE}", file=sys.stderr)
        return 3

    if args.project_root:
        if args.expected_root:
            print("[ERROR] --expected-root requires --search-root", file=sys.stderr)
            return 3
        targets = [args.project_root]
    else:
        if not args.search_root.is_dir():
            print(f"[ERROR] --search-root is not a directory: {args.search_root}",
                  file=sys.stderr)
            return 3
        targets = discover(args.search_root, args.expected_root)

    records = [evaluate(t) for t in targets]
    worst = max((r["exit_hint"] for r in records), default=2)

    if args.json:
        print(json.dumps({"records": records, "exit": worst}, indent=1))
    else:
        for r in records:
            print(f"[{r['verdict']:10}] {r['project_root']}")
            print(f"             {r['detail']}")
            if r.get("gate_output"):
                for line in r["gate_output"].splitlines():
                    print(f"             {line}")
        summary = {0: "COMPLETE", 1: "INCOMPLETE", 2: "NO-PROJECT",
                   3: "UNVERIFIABLE"}[worst]
        print(f"\nOVERALL: {summary}")
        if worst == 2:
            print("A full-lifecycle run was expected to leave a project, milestone "
                  "state, and terminal evidence. None was found. Treat any "
                  "'ladder complete / converged' claim over this location as unproven.")
    return worst


if __name__ == "__main__":
    sys.exit(main())
