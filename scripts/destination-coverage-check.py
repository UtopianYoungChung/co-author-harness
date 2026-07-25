#!/usr/bin/env python3
"""destination-coverage-check - every filesystem writer is classified, mechanically.

Blocker-1 lesson (2026-07-22): a prose inventory listed coupling_health_report
as a writer, the corpus was green, and the script still wrote two files into a
protected governed root — coverage that only lives in prose is coverage that
rots. This check makes the writer census and its classification machine-
enforced:

  1. CENSUS  — scan scripts/**/*.py for write-operation call sites (the same
     pattern family the Phase A inventory used). Files whose name marks them
     as test material (*smoketest*, test_*, scripts/tests/) are pattern-exempt.
  2. REGISTRY — references/destination_coverage_registry.json must classify
     every remaining writer as exactly one of:
       guarded           destination checks live in the file; the named
                         negative regression exists; the file must textually
                         call guard_project_root(/assert_writable(.
       package_confined  writes only package-derived paths; sha256-pinned so
                         ANY change forces re-review here.
       test_only         test/fixture support; bounded justification;
                         sha256-pinned.
       excluded          precise reason (e.g. write-helper library whose only
                         callers are guarded CLIs); sha256-pinned.
  3. A writer with no entry, a stale entry (file no longer a writer), a
     guarded entry without a live guard call or named regression, or a pinned
     entry whose bytes drifted -> exit 1.

Run:   python scripts/destination-coverage-check.py          # validate
       python scripts/destination-coverage-check.py --pin    # refresh sha256
                                                             # pins (deliberate
                                                             # re-review only)
Exit: 0 OK; 1 finding(s); 2 cannot validate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "references" / "destination_coverage_registry.json"

WRITE_PATTERN = re.compile(
    r"write_text|write_bytes|open\([^)]*[\"']w|open\([^)]*[\"']x"
    r"|os\.replace|shutil\.(?:move|copy|rmtree)|\.rename\(|\.unlink\(|\.mkdir\("
    r"|publish_committed\(|_atomic_json\("
)
GUARD_PATTERN = re.compile(
    r"guard_project_root\(|guard_repin_project_root\(|assert_writable\("
)
CLASSES = {"guarded", "package_confined", "test_only", "excluded"}


def pattern_exempt(rel: str) -> bool:
    name = Path(rel).name
    return ("smoketest" in name or name.startswith("test_")
            or rel.replace("\\", "/").startswith("scripts/tests/"))


def census() -> list[str]:
    writers = []
    for path in sorted(ROOT.glob("scripts/**/*.py")):
        rel = path.relative_to(ROOT).as_posix()
        if pattern_exempt(rel):
            continue
        if WRITE_PATTERN.search(path.read_text(encoding="utf-8", errors="replace")):
            writers.append(rel)
    return writers


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pin", action="store_true",
                        help="refresh sha256 pins for pinned classes (deliberate re-review)")
    args = parser.parse_args()

    if not REGISTRY.is_file():
        print(f"FATAL: registry not found: {REGISTRY}")
        return 2
    try:
        doc = json.loads(REGISTRY.read_text(encoding="utf-8"))
        entries: dict = doc["writers"]
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        print(f"FATAL: registry unreadable: {exc}")
        return 2

    findings: list[str] = []
    writers = census()

    for rel in writers:
        entry = entries.get(rel)
        if entry is None:
            findings.append(f"[UNCLASSIFIED] {rel}: writer has no registry entry")
            continue
        klass = entry.get("class")
        if klass not in CLASSES:
            findings.append(f"[BAD-CLASS] {rel}: {klass!r} not in {sorted(CLASSES)}")
            continue
        text = (ROOT / rel).read_text(encoding="utf-8", errors="replace")
        if klass == "guarded":
            if not GUARD_PATTERN.search(text):
                findings.append(f"[UNGUARDED] {rel}: classified guarded but no "
                                "guard_project_root(/assert_writable( call present")
            if not str(entry.get("regression", "")).strip():
                findings.append(f"[NO-REGRESSION] {rel}: guarded entry names no negative regression")
        else:
            reason_key = {"package_confined": "evidence", "test_only": "justification",
                          "excluded": "reason"}[klass]
            if not str(entry.get(reason_key, "")).strip():
                findings.append(f"[NO-{reason_key.upper()}] {rel}: {klass} entry lacks {reason_key}")
            live = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
            if args.pin:
                entry["sha256"] = live
            elif entry.get("sha256") != live:
                findings.append(f"[PIN-DRIFT] {rel}: {klass} bytes changed; re-review "
                                "and re-pin deliberately (--pin)")

    for rel in sorted(entries):
        if rel not in writers:
            findings.append(f"[STALE-ENTRY] {rel}: registered but no longer a census writer")

    # Runbook parity: BOTH root maintainer runbooks must carry this check.
    # CLAUDE.md alone is not enough -- AGENTS.md governs Codex and every other
    # agent, and a battery that only some agents run is a battery that rots
    # (the Blocker-1 lesson applied to the check itself).
    for runbook in ("CLAUDE.md", "AGENTS.md"):
        text = (ROOT / runbook).read_text(encoding="utf-8", errors="replace")
        if "python scripts/destination-coverage-check.py" not in text:
            findings.append(
                f"[RUNBOOK-PARITY] {runbook}: maintainer battery does not "
                "list python scripts/destination-coverage-check.py")

    if args.pin:
        REGISTRY.write_text(json.dumps(doc, indent=2, sort_keys=False) + "\n", encoding="utf-8")
        print(f"pins refreshed for pinned classes ({len(writers)} writers in census)")

    if findings:
        print(f"DESTINATION COVERAGE: {len(findings)} finding(s)")
        for row in findings:
            print(f"  {row}")
        return 1
    print(f"OK destination coverage: {len(writers)} writers classified "
          f"({sum(1 for e in entries.values() if e.get('class') == 'guarded')} guarded), "
          "0 unclassified, 0 drifted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
