#!/usr/bin/env python3
"""Hermetic smoketest for centroid_sentence_logic.py."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "centroid_sentence_logic.py"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run(tmp: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT / "scripts"),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"FAIL: {msg}")


def main() -> int:
    manuscript = "Actors depend on one another. That dependency is the unit of analysis.\n"
    ms_sha = sha(manuscript)
    packet = {
        "schema_version": "1.0.0",
        "capability": "centroid-pass",
        "status": "binding_resolved",
        "reason_code": "GRAPH-SEMANTIC-INELIGIBLE",
        "manuscript": {
            "path": "synthetic.md",
            "sha256": ms_sha,
            "scope": {"kind": "full_manuscript", "sha256": ms_sha},
        },
        "semantic_findings": [],
    }
    passages = [
        {
            "source_key": "yu-et-al-2011-social-modeling",
            "locator": "book p. 7",
            "quote": "Strategic actors depend on each other for goals to be achieved.",
            "warrant_layer": "surface",
        }
    ]
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        man = tmp / "m.md"
        pkt = tmp / "packet.json"
        pas = tmp / "passages.json"
        out = tmp / "out"
        man.write_text(manuscript, encoding="utf-8", newline="\n")
        pkt.write_text(json.dumps(packet), encoding="utf-8")
        pas.write_text(json.dumps(passages), encoding="utf-8")

        blocked = run(tmp, "--packet", str(pkt), "--manuscript", str(man), "--mode", "review")
        require(blocked.returncode == 4 and "SENTENCE-LOGIC-NO-PASSAGE" in blocked.stdout, "ineligible without passages must fail closed")

        stale = json.loads(json.dumps(packet))
        stale["manuscript"]["sha256"] = "0" * 64
        stale_path = tmp / "stale.json"
        stale_path.write_text(json.dumps(stale), encoding="utf-8")
        stale_run = run(tmp, "--packet", str(stale_path), "--manuscript", str(man), "--mode", "review", "--passages", str(pas))
        require(stale_run.returncode == 4 and "SENTENCE-LOGIC-STALE" in stale_run.stdout, "stale manuscript must fail")

        bad = [{"source_key": "yu-et-al-2011-social-modeling", "locator": "book p. 90", "quote": "out of window", "warrant_layer": "surface"}]
        bad_path = tmp / "bad.json"
        bad_path.write_text(json.dumps(bad), encoding="utf-8")
        bad_run = run(tmp, "--packet", str(pkt), "--manuscript", str(man), "--mode", "write", "--passages", str(bad_path))
        require(bad_run.returncode == 4 and "SENTENCE-LOGIC-SCOPE" in bad_run.stdout, "Yu page outside 3-52 must fail")

        ok = run(
            tmp,
            "--packet", str(pkt),
            "--manuscript", str(man),
            "--mode", "review",
            "--passages", str(pas),
            "--out-dir", str(out),
        )
        require(ok.returncode == 0, f"admitted paste should run: {ok.stdout}{ok.stderr}")
        receipt = json.loads(ok.stdout)
        require(receipt["status"] == "ready_for_role", "must not mint CLEAN")
        require(receipt["summary"]["CLEAN"] == 0, "must not mint CLEAN counts")
        require(len(receipt["pairs"]) == 1, "expected one sentence pair")
        require(receipt["pairs"][0]["verdict"] == "not_run", "roles fill verdicts")
        require((out / "centroid-sentence-logic_review.json").is_file(), "json receipt missing")
        require((out / "centroid-sentence-logic_review.md").is_file(), "md receipt missing")

    print("centroid_sentence_logic_smoketest: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
