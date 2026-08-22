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
        errors="strict",
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
        require(receipt["pairs"][0]["checks"]["join_cadence"] == "derivation_shown", "that-dependency pair should show derivation")
        require(receipt["pairs"][0]["checks"]["needed_backtrack"] == "not_required", "forward derivation must not require backtrack")
        require(receipt["summary"]["all_short_stack"] is False, "two-sentence manuscript is not a stack")
        require((out / "centroid-sentence-logic_review.json").is_file(), "json receipt missing")
        require((out / "centroid-sentence-logic_review.md").is_file(), "md receipt missing")

        short = "Actors depend. So they are strategic. Thus i-star applies.\n"
        short_sha = sha(short)
        short_packet = json.loads(json.dumps(packet))
        short_packet["manuscript"]["sha256"] = short_sha
        short_packet["manuscript"]["scope"]["sha256"] = short_sha
        short_man = tmp / "short.md"
        short_pkt = tmp / "short_packet.json"
        short_man.write_text(short, encoding="utf-8", newline="\n")
        short_pkt.write_text(json.dumps(short_packet), encoding="utf-8")
        short_run = run(tmp, "--packet", str(short_pkt), "--manuscript", str(short_man), "--mode", "review", "--passages", str(pas))
        require(short_run.returncode == 0, f"short stack should still run: {short_run.stdout}{short_run.stderr}")
        short_receipt = json.loads(short_run.stdout)
        require(short_receipt["summary"]["CLEAN"] == 0, "must not mint CLEAN on short stack")
        require(short_receipt["pairs"][0]["verdict"] == "not_run", "roles still fill verdicts")
        require(short_receipt["summary"]["all_short_stack"] is True, "three short sentences are an all-short stack")
        require(short_receipt["summary"]["join_cadence_misses"] >= 1, "unearned so/thus verdicts are join-cadence misses")
        require(short_receipt["pairs"][0]["checks"]["join_cadence"] == "unearned_verdict", "so-they-are-strategic is an unearned verdict")

        retract = "Actors depend on one another. But theory is enough.\n"
        retract_sha = sha(retract)
        retract_packet = json.loads(json.dumps(packet))
        retract_packet["manuscript"]["sha256"] = retract_sha
        retract_packet["manuscript"]["scope"]["sha256"] = retract_sha
        retract_man = tmp / "retract.md"
        retract_pkt = tmp / "retract_packet.json"
        retract_man.write_text(retract, encoding="utf-8", newline="\n")
        retract_pkt.write_text(json.dumps(retract_packet), encoding="utf-8")
        retract_run = run(tmp, "--packet", str(retract_pkt), "--manuscript", str(retract_man), "--mode", "review", "--passages", str(pas))
        require(retract_run.returncode == 0, f"retract pair should run: {retract_run.stdout}{retract_run.stderr}")
        retract_receipt = json.loads(retract_run.stdout)
        require(retract_receipt["pairs"][0]["checks"]["needed_backtrack"] == "missing", "short retract without return is a needed-backtrack miss")
        require(retract_receipt["pairs"][0]["verdict"] == "not_run", "backtrack miss is a signal, not a minted BLOCKER")

    print("centroid_sentence_logic_smoketest: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
