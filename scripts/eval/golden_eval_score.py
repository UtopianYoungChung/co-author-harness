#!/usr/bin/env python3
"""golden_eval_score — deterministic scorer for judgment-layer eval runs.

Introduced by docs/analysis/2026-07-06_systematic-improvement-plan.md §6 (WS-4).

Usage:
    python3 scripts/eval/golden_eval_score.py <findings.json> [--baseline <prior_scored.json>]

<findings.json> follows manifest.json -> findings_file_schema. The scorer:
  1. Matches findings to seeded defects with two-pass matching (exact
     normalized equality first, bidirectional substring second); location_hint
     tiebreaks only within a pass [AR-8]. Single-pass substring matching lets
     a broad family (C-6<->C-8/M-1) steal the finding meant for a narrower
     one (C-8/M-1) — caught by smoke test, 2026-07-06.
  2. Reports per-defect hit/miss and overall recall for detection fixtures.
  3. Reports false positives on the P1 control (any finding whose family is
     p2-gated per the manifest).
  4. With --baseline, compares recall and FP count to a prior scored run and
     exits 1 on regression (recall drop or new FP). Without --baseline, exit
     is always 0 — a gate with no baseline is noise (plan §6).

The run itself is agent work; only the scoring is deterministic.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
PLUGIN_ROOT = HERE.parent.parent.parent
MANIFEST = PLUGIN_ROOT / "scripts" / "fixtures" / "golden" / "manifest.json"


def norm_code(code: str) -> str:
    """Strip severity brackets/dashes: '[MAJOR — C-8/M-2]' -> 'C-8/M-2'."""
    code = re.sub(r"^\[\s*(BLOCKER|MAJOR|MINOR)\s*[—–-]\s*", "", code.strip())
    return code.rstrip("]").strip()


def family_match(expected: str, found: str) -> bool:
    e, f = expected.strip(), norm_code(found)
    return bool(e) and bool(f) and (e in f or f in e)


def score(findings_doc: dict, manifest: dict) -> dict:
    fixture = findings_doc["fixture"]
    fx = manifest["fixtures"].get(fixture)
    if fx is None:
        raise SystemExit(f"unknown fixture: {fixture!r} (known: {list(manifest['fixtures'])})")
    findings = findings_doc.get("findings", [])
    out: dict = {"fixture": fixture, "pass": findings_doc.get("pass", "?"), "role": fx["role"]}

    if fx["role"] == "detection":
        hits: dict = {d["defect_id"]: False for d in fx["defects"]}
        unmatched = list(range(len(findings)))

        def tiebreak(defect: dict, candidates: list) -> list:
            if len(candidates) <= 1:
                return candidates
            loc = defect.get("location_hint", "").lower()
            narrowed = [i for i in candidates
                        if findings[i].get("location_hint", "").lower() and
                        (findings[i]["location_hint"].lower() in loc or
                         loc in findings[i]["location_hint"].lower())]
            return narrowed or candidates

        for exact_pass in (True, False):
            for defect in fx["defects"]:
                if hits[defect["defect_id"]]:
                    continue
                fam = defect["expected_code_family"]
                if exact_pass:
                    candidates = [i for i in unmatched
                                  if norm_code(findings[i]["finding_code"]) == fam]
                else:
                    candidates = [i for i in unmatched
                                  if family_match(fam, findings[i]["finding_code"])]
                candidates = tiebreak(defect, candidates)
                if candidates:
                    unmatched.remove(candidates[0])
                    hits[defect["defect_id"]] = True
        out["per_defect"] = hits
        out["recall"] = round(sum(hits.values()) / len(hits), 3) if hits else None
        out["extra_findings"] = len(unmatched)
    else:  # false-positive-control
        gated = manifest["findings_file_schema"]["p2_gated_families"]
        fps = [f for f in findings
               if any(family_match(g, f["finding_code"]) for g in gated)]
        out["false_positives"] = len(fps)
        out["false_positive_codes"] = [f["finding_code"] for f in fps]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("findings", type=Path)
    ap.add_argument("--baseline", type=Path, default=None)
    args = ap.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    result = score(json.loads(args.findings.read_text(encoding="utf-8")), manifest)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if args.baseline:
        base = json.loads(args.baseline.read_text(encoding="utf-8"))
        regressed = False
        if result["role"] == "detection" and base.get("recall") is not None:
            if (result["recall"] or 0) < base["recall"]:
                print(f"REGRESSION: recall {result['recall']} < baseline {base['recall']}")
                regressed = True
        if result["role"] == "false-positive-control":
            if result["false_positives"] > base.get("false_positives", 0):
                print(f"REGRESSION: false positives {result['false_positives']} > "
                      f"baseline {base.get('false_positives', 0)}")
                regressed = True
        if regressed:
            return 1
        print("No regression vs baseline.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
