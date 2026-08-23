#!/usr/bin/env python3
"""Hermetic smoketest for centroid_sentence_logic.py."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "centroid_sentence_logic.py"

sys.path.insert(0, str(ROOT / "scripts"))
import centroid_sentence_logic as logic_module  # noqa: E402
import centroid_service as binder_module  # noqa: E402


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run(tmp: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT / "scripts"),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        env=env,
    )


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"FAIL: {msg}")


def main() -> int:
    script_text = SCRIPT.read_text(encoding="utf-8")
    require("# /// script" in script_text and "# ///" in script_text, "PEP 723 script metadata missing")
    require('# dependencies = ["pypdf==6.14.2"]' in script_text, "pypdf PEP 723 pin missing")

    heading_parity_cases = (
        ("# Title#\nA sentence. B sentence.\n# Next\nC sentence.\n", "Title#"),
        ("# Title ###\nA sentence. B sentence.\n# Next\nC sentence.\n", "Title"),
        ("# Title\nA sentence. B sentence.\n # Faux\nC sentence.\n# Next\nD sentence.\n", "Title"),
    )
    for heading_text, heading_name in heading_parity_cases:
        binder_scope, _ = binder_module._scope(heading_text, heading_name)
        logic_scope = logic_module._heading_scope(heading_text, heading_name)
        require(logic_scope == binder_scope, f"heading grammar drift for {heading_name!r}")

    pseudo_reference = logic_module._prose_text(
        "Alpha remains.\n # References\nBeta remains.\n",
        scoped_heading=None,
    )
    require("Beta remains." in pseudo_reference, "indented pseudo-heading must not truncate prose")
    mixed_fence = logic_module._prose_text(
        "Before.\n```python\nhidden one.\n~~~\nhidden two.\n```\nAfter.\n",
        scoped_heading=None,
    )
    require(mixed_fence == "Before.\nAfter.", "mismatched fence marker leaked code")
    long_fence = logic_module._prose_text(
        "Before.\n````text\nhidden one.\n```\nhidden two.\n````\nAfter.\n",
        scoped_heading=None,
    )
    require(long_fence == "Before.\nAfter.", "short inner fence closed a longer outer fence")

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

        scoped_manuscript = """---
title: Polluted front matter sentence.
author: Initials A. B.
---

# Introduction

**Milestone:** M4 complete draft
**Status:** drafted, not accepted

Intro premise is visible. That premise continues the introduction.

## Target Section

**Milestone:** target control metadata

Name | Status
--- | ---
Alpha sentence. | Draft.

Actors depend on one another. That dependency defines the target unit.

## Other Section

Other prose starts here. Which means this sentence belongs elsewhere.

## References

Yu, E. 2011. Bibliography fragment. https://doi.org/10.0000/example.
"""
        scoped_sha = sha(scoped_manuscript)
        scoped_text = "## Target Section\n\n**Milestone:** target control metadata\n\nName | Status\n--- | ---\nAlpha sentence. | Draft.\n\nActors depend on one another. That dependency defines the target unit.\n"
        scoped_packet = json.loads(json.dumps(packet))
        scoped_packet["manuscript"]["sha256"] = scoped_sha
        scoped_packet["manuscript"]["scope"] = {
            "kind": "heading",
            "heading": "Target Section",
            "start_line": 11,
            "end_line": 14,
            "sha256": sha(scoped_text),
        }
        scoped_man = tmp / "scoped.md"
        scoped_pkt = tmp / "scoped_packet.json"
        scoped_man.write_text(scoped_manuscript, encoding="utf-8", newline="\n")
        scoped_pkt.write_text(json.dumps(scoped_packet), encoding="utf-8")
        scoped_run = run(
            tmp,
            "--packet", str(scoped_pkt),
            "--manuscript", str(scoped_man),
            "--mode", "review",
            "--heading", "Target Section",
            "--passages", str(pas),
        )
        require(scoped_run.returncode == 0, f"heading scope should run: {scoped_run.stdout}{scoped_run.stderr}")
        scoped_receipt = json.loads(scoped_run.stdout)
        require(len(scoped_receipt["pairs"]) == 1, "heading scope must emit only the target section pair")
        scoped_pair_text = json.dumps(scoped_receipt["pairs"])
        require(
            "front matter" not in scoped_pair_text
            and "Milestone" not in scoped_pair_text
            and "Name | Status" not in scoped_pair_text
            and "References" not in scoped_pair_text,
            "heading scope leaked metadata or bibliography",
        )
        require(scoped_receipt["scope_heading"] == "Target Section", "receipt must bind requested heading")
        require(scoped_receipt["scope_sha256"] == sha(scoped_text), "receipt scope hash must bind extracted heading bytes")

        mismatch_run = run(
            tmp,
            "--packet", str(scoped_pkt),
            "--manuscript", str(scoped_man),
            "--mode", "review",
            "--heading", "Other Section",
            "--passages", str(pas),
        )
        require(mismatch_run.returncode == 4 and "SENTENCE-LOGIC-SCOPE" in mismatch_run.stdout, "CLI heading must match packet scope")

        full_packet = json.loads(json.dumps(packet))
        full_packet["manuscript"]["sha256"] = scoped_sha
        full_packet["manuscript"]["scope"] = {
            "kind": "full_manuscript",
            "heading": None,
            "start_line": 1,
            "end_line": len(scoped_manuscript.splitlines()),
            "sha256": scoped_sha,
        }
        full_pkt = tmp / "full_packet.json"
        full_pkt.write_text(json.dumps(full_packet), encoding="utf-8")
        full_run = run(
            tmp,
            "--packet", str(full_pkt),
            "--manuscript", str(scoped_man),
            "--mode", "review",
            "--passages", str(pas),
        )
        require(full_run.returncode == 0, f"full manuscript should run: {full_run.stdout}{full_run.stderr}")
        full_receipt = json.loads(full_run.stdout)
        full_pair_text = json.dumps(full_receipt["pairs"])
        require(
            "title:" not in full_pair_text
            and "Milestone" not in full_pair_text
            and "doi.org" not in full_pair_text,
            "full manuscript leaked front matter, control metadata, or References",
        )

        blocked_import = tmp / "blocked-import"
        blocked_import.mkdir()
        (blocked_import / "pypdf.py").write_text("raise ImportError('simulated missing pypdf')\n", encoding="utf-8")
        fake_pdf = tmp / "fake.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 simulated")
        dependency_env = os.environ.copy()
        dependency_env["PYTHONPATH"] = str(blocked_import)
        dependency_run = run(
            tmp,
            "--packet", str(pkt),
            "--manuscript", str(man),
            "--mode", "review",
            "--admit-pdf", str(fake_pdf),
            "--pages", "7",
            env=dependency_env,
        )
        require(
            dependency_run.returncode == 4
            and "SENTENCE-LOGIC-DEPENDENCY" in dependency_run.stdout
            and "Traceback" not in dependency_run.stderr,
            "missing pypdf must fail closed with a stable dependency code",
        )

        fake_workspace = tmp / "fake-workspace"
        routing_manifest = fake_workspace / "governance" / "output-routing" / "output_routing.yaml"
        routing_manifest.parent.mkdir(parents=True)
        routing_manifest.write_text("schema_version: 1\n", encoding="utf-8")
        traversal_root = fake_workspace / "research" / "60_Workbench" / "work"
        governed_env = os.environ.copy()
        governed_env["COAUTHOR_EXTRA_GOVERNED_ROOTS"] = str(fake_workspace)
        safe_shipment = run(
            tmp,
            "--packet", str(pkt),
            "--manuscript", str(man),
            "--mode", "review",
            "--passages", str(pas),
            "--project-root", str(traversal_root),
            "--shipment-id", "safe-shipment",
            env=governed_env,
        )
        require(
            safe_shipment.returncode == 0
            and (traversal_root / "reviews" / ".harness" / "shipments" / "safe-shipment" / "centroid-sentence-logic_review.json").is_file(),
            "safe governed shipment must remain writable",
        )
        receipts_before = {path.resolve() for path in tmp.rglob("centroid-sentence-logic_review.json")}
        traversal_run = run(
            tmp,
            "--packet", str(pkt),
            "--manuscript", str(man),
            "--mode", "review",
            "--passages", str(pas),
            "--project-root", str(traversal_root),
            "--shipment-id", "../../escape",
            env=governed_env,
        )
        receipts_after = {path.resolve() for path in tmp.rglob("centroid-sentence-logic_review.json")}
        require(
            traversal_run.returncode == 4
            and "SENTENCE-LOGIC-DEST" in traversal_run.stdout
            and receipts_after == receipts_before,
            "shipment id traversal must fail before any receipt write",
        )
        for unsafe_id in ("C:/absolute", ".", ".."):
            unsafe_run = run(
                tmp,
                "--packet", str(pkt),
                "--manuscript", str(man),
                "--mode", "review",
                "--passages", str(pas),
                "--project-root", str(traversal_root),
                "--shipment-id", unsafe_id,
                env=governed_env,
            )
            require(unsafe_run.returncode == 4 and "SENTENCE-LOGIC-DEST" in unsafe_run.stdout, f"unsafe shipment id accepted: {unsafe_id}")

        wrong_root_run = run(
            tmp,
            "--packet", str(pkt),
            "--manuscript", str(man),
            "--mode", "review",
            "--passages", str(pas),
            "--project-root", str(tmp / "outside-workspace"),
            "--shipment-id", "safe-name",
            env=governed_env,
        )
        require(
            wrong_root_run.returncode == 4 and "SENTENCE-LOGIC-DEST" in wrong_root_run.stdout,
            "shipment-id mode accepted a non-shipment destination",
        )

        shipment_parent = traversal_root / "reviews" / ".harness" / "shipments"
        outside_target = tmp / "junction-outside"
        outside_target.mkdir()
        link = shipment_parent / "linked-shipment"
        try:
            link.symlink_to(outside_target, target_is_directory=True)
        except OSError:
            pass  # platform privilege may forbid symlinks; destination_capability owns junction coverage
        else:
            link_run = run(
                tmp,
                "--packet", str(pkt),
                "--manuscript", str(man),
                "--mode", "review",
                "--passages", str(pas),
                "--project-root", str(traversal_root),
                "--shipment-id", "linked-shipment",
                env=governed_env,
            )
            require(link_run.returncode == 4 and "SENTENCE-LOGIC-DEST" in link_run.stdout, "shipment junction escaped the governed lane")

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
