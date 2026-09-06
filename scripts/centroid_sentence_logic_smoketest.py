#!/usr/bin/env python3
"""Hermetic smoketest for centroid_sentence_logic.py."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "centroid_sentence_logic.py"
sys.path.insert(0, str(ROOT / "scripts"))
import centroid_sentence_logic as csl  # noqa: E402


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run(tmp: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT / "scripts"),
        capture_output=True,
        text=True,
        encoding="utf-8", errors="replace"
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
        out = Path(tempfile.mkdtemp(prefix=".centroid-check-smoke-", dir=str(ROOT)))
        try:
            _run_cases(tmp, man, pkt, pas, out, manuscript, packet, passages)
        finally:
            shutil.rmtree(out, ignore_errors=True)

    print("centroid_sentence_logic_smoketest: PASS")
    return 0


def _run_cases(tmp, man, pkt, pas, out, manuscript, packet, passages) -> None:
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
        require(receipt["pass"] == "centroid-check", "instrument name is centroid-check")
        require(receipt["instrument"] == "centroid-check", "instrument field")
        require(receipt["centroid_source"] == "yu-et-al-2011-social-modeling", "centroid-source stays Yu 2011")
        require(
            receipt["naming"]
            == (
                f"this is a centroid-check of manuscript {receipt['manuscript_sha256']}/"
                f"{receipt['manuscript_bytes']} against centroid-source yu-et-al-2011-social-modeling"
            ),
            "receipt must name check vs source",
        )
        require("eligibility, not a pair verdict" in " ".join(receipt["limitations"]), "bind eligibility sentence")
        require(len(receipt["pairs"]) == 1, "expected one sentence pair")
        require(receipt["pairs"][0]["verdict"] == "not_run", "roles fill verdicts")
        require(receipt["pairs"][0]["checks"]["join_cadence"] == "derivation_shown", "that-dependency pair should show derivation")
        require(receipt["pairs"][0]["checks"]["needed_backtrack"] == "not_required", "forward derivation must not require backtrack")
        require(receipt["summary"]["all_short_stack"] is False, "two-sentence manuscript is not a stack")
        require((out / "centroid-check_review.json").is_file(), "json receipt missing")
        require((out / "centroid-check_review.md").is_file(), "md receipt missing")
        md = (out / "centroid-check_review.md").read_text(encoding="utf-8")
        require("this is a centroid-check of manuscript" in md, "md receipt names the check")
        require("centroid-source yu-et-al-2011-social-modeling" in md, "md receipt names the source")
        require("GRAPH-SEMANTIC-INELIGIBLE" in md, "md receipt keeps bind eligibility distinct")

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

        locked = run(
            tmp,
            "--packet", str(pkt),
            "--manuscript", str(man),
            "--mode", "review",
            "--passages", str(pas),
            "--centroid-source", "yu-1995-istar",
        )
        require(locked.returncode == 4 and "SENTENCE-LOGIC-SOURCE" in locked.stdout, "centroid-source must stay locked")

        # Legacy PDF-index 3,7,12: identity labels on title/foreword/contents are not printed book pages.
        front_pages = []
        headings = {3: "TITLE PAGE", 7: "FOREWORD", 12: "CONTENTS"}
        for identity in range(1, 13):
            heading = headings.get(identity, "front matter")
            front_pages.append(
                {
                    "identity": identity,
                    "label": str(identity),
                    "text": f"{heading}\nSocial Modeling\n{identity}\n",
                }
            )
        try:
            csl.resolve_printed_pages(front_pages, [3, 7, 12])
        except csl.Refusal as exc:
            require(exc.code == "SENTENCE-LOGIC-PDF-INDEX", f"legacy PDF-index must refuse, got {exc.code}")
        else:
            raise SystemExit("FAIL: legacy PDF-index 3,7,12 must be refused")

        yu_body = [
            {
                "identity": 20,
                "label": "iv",
                "text": "Actors depend on each other for goals to be achieved.\n7\n",
            }
        ]
        admitted = csl.resolve_printed_pages(yu_body, [7])
        require(admitted[0]["printed_page"] == 7, "printed book page 7 must resolve from a non-identity footer")

        yu_running_head = [
            {
                "identity": 12,
                "label": "12",
                "text": "Actors depend on each other for goals to be achieved.\n5 Introduction\n",
            }
        ]
        admitted_rh = csl.resolve_printed_pages(yu_running_head, [5])
        require(
            admitted_rh[0]["printed_page"] == 5,
            "printed book page 5 must resolve from a running-head footer",
        )

        help_run = run(tmp, "--help")
        require(help_run.returncode == 0, "help must run")
        require("centroid-source" in help_run.stdout, "help names centroid-source")
        require("centroid-check" in help_run.stdout, "help names centroid-check")
        require("centroid-bind" in help_run.stdout, "help names centroid-bind")
        require("Printed book pages" in help_run.stdout, "help says --pages is printed book pages")
        require("PDF-index 3,7,12" in help_run.stdout, "help refuses legacy PDF-index 3,7,12")


if __name__ == "__main__":
    raise SystemExit(main())
