#!/usr/bin/env python3
"""Registered synthetic regression cases for centroid-check preparation."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "centroid_sentence_logic.py"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "tests"))
import centroid_service as binder  # noqa: E402
from assignment_fixture_support import package_scratch  # noqa: E402
from domain_native_register_smoketest import write_fixture  # noqa: E402


def require(ok: bool, label: str) -> None:
    if not ok:
        raise SystemExit(f"FAIL: {label}")


def run(*args: str) -> tuple[int, dict]:
    result = subprocess.run([sys.executable, "-B", "-X", "utf8", str(SCRIPT), *args],
                            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise SystemExit(f"FAIL: non-JSON output: {result.stdout[:300]} {result.stderr}")
    return result.returncode, output


def fixture(tmp: Path, text: str, heading: str | None = None) -> tuple[Path, Path]:
    man = tmp / "synthetic.md"
    pkt = tmp / "packet.json"
    man.write_text(text, encoding="utf-8", newline="")
    scoped, scope = binder._scope(text, heading)
    packet = binder._general_packet(
        manuscript_path=man.resolve(), manuscript_bytes=man.read_bytes(),
        scoped_text=scoped, scope=scope, prose=binder._prose_lines(scoped),
        mode="review", reason_code="GRAPH-SEMANTIC-INELIGIBLE",
        detail="synthetic fixture: graph semantic capability unavailable",
    )
    pkt.write_text(json.dumps(packet), encoding="utf-8")
    return man, pkt


def passage_file(tmp: Path) -> Path:
    path = tmp / "passages.json"
    path.write_text(json.dumps([{
        "source_key": "yu-et-al-2011-social-modeling", "locator": "book p. 7",
        "quote": "SYNTHETIC TEST PASSAGE — mechanics only, no scholarly support claimed.",
        "warrant_layer": "surface", "admitted_by": "Synthetic fixture author",
    }]), encoding="utf-8")
    return path


def case_scope(tmp: Path, passages: Path) -> None:
    manuscript = "# Target\nTargetMarker begins. That dependency continues.\n\n# Outside\nOutsideMarker begins. OutsideMarker continues.\n"
    man, pkt = fixture(tmp, manuscript, "Target")
    common = ("--packet", str(pkt), "--manuscript", str(man), "--mode", "review", "--passages", str(passages))
    code, receipt = run(*common)
    require(code == 0, f"valid heading scope: {receipt}")
    require(receipt["scope"]["kind"] == "heading" and receipt["scope"]["heading"] == "Target", "scope identity")
    require(all("OutsideMarker" not in s["text"] for s in receipt["sentences"]), "outside section excluded")
    require(len(receipt["pairs"]) == 1, "only in-scope prose pair")
    for heading in ("Outside", "DOES-NOT-EXIST"):
        code, blocked = run(*common, "--heading", heading)
        require(code == 4 and blocked["reason_code"] == "SENTENCE-LOGIC-SCOPE", f"heading mismatch {heading}")
    changed = json.loads(pkt.read_text(encoding="utf-8"))
    changed["manuscript"]["scope"]["sha256"] = "0" * 64
    pkt.write_text(json.dumps(changed), encoding="utf-8")
    code, blocked = run(*common)
    require(code == 4 and blocked["reason_code"] == "SENTENCE-LOGIC-STALE", "stale scope hash")
    man, pkt = fixture(tmp, manuscript, "Target")
    changed = json.loads(pkt.read_text(encoding="utf-8"))
    changed["manuscript"]["scope"]["start_line"] += 1
    pkt.write_text(json.dumps(changed), encoding="utf-8")
    code, blocked = run(*common)
    require(code == 4 and blocked["reason_code"] == "SENTENCE-LOGIC-STALE", "stale scope lines")
    duplicate = "# Target\nOne sentence.\n# Target\nAnother sentence.\n"
    try:
        binder._scope(duplicate, "Target")
    except binder.Unavailable as exc:
        require(exc.reason_code == "HEADING_AMBIGUOUS", "ambiguous heading code")
    else:
        raise SystemExit("FAIL: duplicate heading should be ambiguous")


def case_states(tmp: Path, passages: Path) -> None:
    man, pkt = fixture(tmp, "Actors depend. That dependency matters.\n")
    common = ("--packet", str(pkt), "--manuscript", str(man), "--mode", "review")
    duplicate = tmp / "duplicate-packet.json"
    duplicate.write_text('{"capability":"forged",' + pkt.read_text(encoding="utf-8")[1:], encoding="utf-8")
    code, blocked = run("--packet", str(duplicate), "--manuscript", str(man), "--mode", "review", "--passages", str(passages))
    require(code == 4 and blocked["reason_code"] == "SENTENCE-LOGIC-INPUT", "duplicate JSON packet key refused")
    valid_packet = json.loads(pkt.read_text(encoding="utf-8"))
    for label, changed in (
        ("null manuscript path", {**valid_packet, "manuscript": {**valid_packet["manuscript"], "path": None}}),
        ("boolean scope line", {**valid_packet, "manuscript": {**valid_packet["manuscript"], "scope": {**valid_packet["manuscript"]["scope"], "start_line": True}}}),
    ):
        pkt.write_text(json.dumps(changed), encoding="utf-8")
        code, blocked = run(*common, "--passages", str(passages))
        require(code == 4 and blocked["reason_code"] == "SENTENCE-LOGIC-PACKET", f"{label} refused")
    pkt.write_text(json.dumps(valid_packet), encoding="utf-8")
    code, blocked = run(*common)
    require(code == 4 and blocked["reason_code"] == "SENTENCE-LOGIC-NO-PASSAGE", "all states need passages")
    packet = json.loads(pkt.read_text(encoding="utf-8"))
    packet["reason_code"] = "SEMANTIC_USAGE_NOT_INVOKED"
    pkt.write_text(json.dumps(packet), encoding="utf-8")
    code, blocked = run(*common, "--passages", str(passages), "--allow-eligible")
    require(code == 4 and blocked["reason_code"] == "SENTENCE-LOGIC-DORMANT", "dormant cannot be overridden")
    packet["reason_code"] = "unexpected-state"
    pkt.write_text(json.dumps(packet), encoding="utf-8")
    code, blocked = run(*common, "--passages", str(passages))
    require(code == 4 and blocked["reason_code"] == "SENTENCE-LOGIC-STATE", "unknown state refuses")
    packet["reason_code"] = None
    pkt.write_text(json.dumps(packet), encoding="utf-8")
    code, blocked = run(*common, "--passages", str(passages), "--allow-eligible")
    require(code == 4 and blocked["reason_code"] == "SENTENCE-LOGIC-ELIGIBILITY", "forged eligible refuses")
    packet["reason_code"] = "GRAPH-SEMANTIC-INELIGIBLE"
    packet["capability"] = "forged"
    pkt.write_text(json.dumps(packet), encoding="utf-8")
    code, blocked = run(*common, "--passages", str(passages))
    require(code == 4 and blocked["reason_code"] == "SENTENCE-LOGIC-PACKET", "binder schema enforced")
    packet["capability"] = "centroid-pass"
    packet["manuscript"]["scope"].pop("start_line")
    pkt.write_text(json.dumps(packet), encoding="utf-8")
    code, blocked = run(*common, "--passages", str(passages))
    require(code == 4 and blocked["reason_code"] == "SENTENCE-LOGIC-PACKET", "nested scope invariant enforced")
    packet["manuscript"]["scope"]["start_line"] = 1
    packet["centroid_source"]["role"] = "forged"
    pkt.write_text(json.dumps(packet), encoding="utf-8")
    code, blocked = run(*common, "--passages", str(passages))
    require(code == 4 and blocked["reason_code"] == "SENTENCE-LOGIC-PACKET", "invalid nested source schema refused")
    packet["centroid_source"]["role"] = "centroid"
    packet["policy"]["profile_sha256"] = "0" * 64
    pkt.write_text(json.dumps(packet), encoding="utf-8")
    code, blocked = run(*common, "--passages", str(passages))
    require(code == 4 and blocked["reason_code"] == "SENTENCE-LOGIC-STALE", "stale ineligible policy hash refused")


def case_inventory(tmp: Path, passages: Path) -> None:
    text = ("---\ntitle: Synthetic\n---\n# Target\nDr. Smith explains e.g. an actor. (Yu, 2011) The actor continues.\n"
            "Another line completes the paragraph.\n\n> A quoted prose sentence. A second quoted sentence.\n\n"
            "| A | B |\n| --- | --- |\n| Cell. | Cell. |\n\n```md\nCode. Not prose.\n```\n"
            "## References\nReference sentence. Another reference sentence.\n")
    man, pkt = fixture(tmp, text, "Target")
    code, receipt = run("--packet", str(pkt), "--manuscript", str(man), "--mode", "review", "--passages", str(passages))
    require(code == 0, f"Markdown inventory: {receipt}")
    snippets = [row["text"] for row in receipt["sentences"]]
    require(any("Dr. Smith" in row for row in snippets), "Dr. protected")
    require(not any(row.strip() == "Dr." for row in snippets), "Dr. not standalone")
    require(any(row.startswith("(Yu, 2011)") for row in snippets), "parenthetical citation opening")
    require(not any("Reference sentence" in row or "Code." in row or "Cell." in row for row in snippets), "nonprose excluded")
    raw = man.read_bytes()
    for row in receipt["sentences"]:
        require(raw[row["start_utf8"]:row["end_utf8"]].decode("utf-8") == row["text"], "exact UTF-8 offset")
    by_id = {row["id"]: row for row in receipt["sentences"]}
    require(all(by_id[row["left_id"]]["paragraph_id"] == by_id[row["right_id"]]["paragraph_id"] for row in receipt["pairs"]), "pairs stay in paragraph")
    require(all(set(row) == {"id", "left_id", "right_id", "verdict", "signals", "context_paragraph_ids"} for row in receipt["pairs"]), "compact pair shape")
    require(all(row["verdict"] == "not_run" for row in receipt["pairs"]), "no minted verdict")
    require(all(row.get("id", "").startswith("centroid-passage-") for row in receipt["admitted_passages"]), "stable passage IDs")
    require(receipt["schema_version"] == "2.0.0", "receipt v2")
    require(receipt["inputs"]["manuscript"] == str(man.resolve()), "rerunnable inputs")


def case_markdown_boundaries(tmp: Path, passages: Path) -> None:
    text = ("Setext Title\n============\n"
            "Visible first. Visible second.\n\n"
            "----\n"
            "After break first. After break second.\n\n"
            "````md\nHidden code first. Hidden code second.\n````oops\n"
            "```\nStill hidden after short fence.\n~~~\nStill hidden after alternate fence.\n````\n"
            "After fence first. After fence second.\n\n"
            "Another Heading\n---------------\n"
            "Following heading first. Following heading second.\n\n"
            "References\n----------\nCited sentence. Another cited sentence.\n")
    man, pkt = fixture(tmp, text)
    code, receipt = run("--packet", str(pkt), "--manuscript", str(man), "--mode", "review", "--passages", str(passages))
    require(code == 0, f"Markdown boundaries: {receipt}")
    snippets = [row["text"] for row in receipt["sentences"]]
    require(len(snippets) == 8 and len(receipt["pairs"]) == 4, "four prose blocks with internal pairs")
    require(all("Hidden" not in row and "Still hidden" not in row and "Cited" not in row for row in snippets), "fence and references excluded")
    require(all("Setext Title" not in row and "Another Heading" not in row and "----" not in row for row in snippets), "setext headings and thematic break excluded")


def case_admission(tmp: Path) -> None:
    man, pkt = fixture(tmp, "First sentence. Second sentence.\n")
    base = ("--packet", str(pkt), "--manuscript", str(man), "--mode", "review")
    path = tmp / "bad_passages.json"
    for locator in ("book pp. 3-99", "book pp. 3, 99"):
        path.write_text(json.dumps([{"source_key": "yu-et-al-2011-social-modeling", "locator": locator,
                                     "quote": "SYNTHETIC TEST ONLY", "admitted_by": "Synthetic fixture author"}]), encoding="utf-8")
        code, blocked = run(*base, "--passages", str(path))
        require(code == 4 and blocked["reason_code"] == "SENTENCE-LOGIC-SCOPE", f"entire locator checked: {locator}")
    path.write_text(json.dumps([{"source_key": "yu-et-al-2011-social-modeling", "locator": "book p. 7",
                                 "quote": "SYNTHETIC TEST ONLY"}]), encoding="utf-8")
    code, blocked = run(*base, "--passages", str(path))
    require(code == 4 and blocked["reason_code"] == "SENTENCE-LOGIC-PASSAGE", "anonymous passage refused")
    code, receipt = run(*base, "--passages", str(path), "--admitted-by", "Synthetic fixture author")
    require(code == 0 and receipt["admitted_passages"][0]["admitted_by"] == "Synthetic fixture author", "named admission")


def case_signals(tmp: Path, passages: Path) -> None:
    cases = (
        ("Actors depend on one another. That dependency continues.\n", "join_cadence", "derivation_cue_present"),
        ("Actors depend. Thus i-star applies. Therefore they agree.\n", "join_cadence", "unearned_verdict"),
        ("Actors depend on one another. However theory is enough.\n", "needed_backtrack", "missing"),
    )
    for index, (text, signal, expected) in enumerate(cases):
        man, pkt = fixture(tmp, text)
        code, receipt = run("--packet", str(pkt), "--manuscript", str(man), "--mode", "review", "--passages", str(passages))
        require(code == 0, f"signal fixture {index}: {receipt}")
        require(receipt["pairs"][0]["signals"][signal] == expected, f"{signal}={expected}")
        require(all(pair["verdict"] == "not_run" for pair in receipt["pairs"]), "signals never mint a verdict")
        require(all(pair["signals"].get("join_cadence") != "derivation_shown" for pair in receipt["pairs"]), "derivation cue never claims proof")
        if index == 1:
            require(receipt["summary"]["all_short_stack"] is True, "three short sentences form short stack")


def case_full_scope_and_view(tmp: Path, passages: Path) -> None:
    text = "# Synthetic title\r\nCafé actors depend. The relation continues.\r\n\r\n# References\r\nExcluded citation.\r\n"
    man, pkt = fixture(tmp, text)
    args = ("--packet", str(pkt), "--manuscript", str(man), "--mode", "review", "--passages", str(passages))
    code, receipt = run(*args)
    require(code == 0 and receipt["scope"]["kind"] == "full_manuscript", "full scope accepted")
    require(len(receipt["sentences"]) == 2 and len(receipt["pairs"]) == 1, "full scope excludes references")
    require(receipt["scope"]["sha256"] == receipt["manuscript_sha256"], "full scope hash bound")
    raw = man.read_bytes()
    for row in receipt["sentences"]:
        require(raw[row["start_utf8"]:row["end_utf8"]].decode("utf-8") == row["text"], "Unicode and CRLF byte offsets")
    result = subprocess.run([sys.executable, "-B", "-X", "utf8", str(SCRIPT), *args, "--format", "review"],
                            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    require(result.returncode == 0 and result.stdout.count("Café actors depend.") == 1, "compact review view stores sentence once")
    require(result.stdout.count("SYNTHETIC TEST PASSAGE") == 1 and "centroid-passage-" in result.stdout, "review view includes source passage once")
    require("heading=None" in result.stdout and "lines=1-" in result.stdout, "review view includes exact scope")
    code, blocked = run(*args, "--out-dir", str(ROOT / "outputs" / "co-author-harness" / "forbidden-fixture"))
    require(code == 4 and blocked["reason_code"] == "DEST-MISROUTED", f"package output lookalike refused: {blocked}")
    with tempfile.TemporaryDirectory(prefix="centroid-check-", dir=package_scratch(ROOT)) as raw:
        out = Path(raw)
        code, written = run(*args, "--out-dir", str(out))
        require(code == 0 and set(written) == {"status", "schema_version", "sentences", "pairs", "written"}, "artifact stdout summary")
        require((out / "centroid-check_review.json").is_file() and (out / "centroid-check_review.md").is_file(), "artifact writes")


def case_live_eligible(tmp: Path, passages: Path) -> None:
    project = tmp / "eligible-project"
    man = project / "manuscript" / "main.md"
    man.parent.mkdir(parents=True)
    man.write_text("# Synthetic Study\nActors depend on one another. That dependency continues.\n", encoding="utf-8")
    wiki, workspace = write_fixture(tmp / "eligible-corpus", all_members=True)
    bind = subprocess.run([
        sys.executable, "-B", "-X", "utf8", str(ROOT / "scripts" / "centroid_service.py"),
        "--manuscript", str(man), "--project-root", str(project), "--wiki-root", str(wiki),
        "--workspace-root", str(workspace), "--harness-root", str(ROOT),
    ], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    require(bind.returncode == 0, f"real fixture binder resolved: {bind.stdout[:300]} {bind.stderr[:300]}")
    packet = json.loads(bind.stdout)
    require(packet["reason_code"] is None and packet["binding_provenance"] in {"project", "package-default"}, "real fixture eligible state")
    pkt = tmp / "eligible-packet.json"
    pkt.write_text(bind.stdout, encoding="utf-8")
    base = ("--packet", str(pkt), "--manuscript", str(man), "--mode", "review",
            "--project-root", str(project), "--wiki-root", str(wiki),
            "--workspace-root", str(workspace), "--harness-root", str(ROOT), "--allow-eligible")
    code, blocked = run(*base)
    require(code == 4 and blocked["reason_code"] == "SENTENCE-LOGIC-NO-PASSAGE", "eligible state still needs admission")
    code, receipt = run(*base, "--passages", str(passages))
    require(code == 0 and receipt["graph_state"] == "eligible" and receipt["summary"]["qualification"] == "incomplete", "real fixture eligible preparation")
    stale = json.loads(bind.stdout)
    stale["policy"]["profile_sha256"] = "0" * 64
    pkt.write_text(json.dumps(stale), encoding="utf-8")
    code, blocked = run(*base, "--passages", str(passages))
    require(code == 4 and blocked["reason_code"] == "SENTENCE-LOGIC-ELIGIBILITY", "stale live policy pin refused")
    stale = json.loads(bind.stdout)
    stale["binding_provenance"] = "general"
    pkt.write_text(json.dumps(stale), encoding="utf-8")
    code, blocked = run(*base, "--passages", str(passages))
    require(code == 4 and blocked["reason_code"] == "SENTENCE-LOGIC-ELIGIBILITY", "stale live provenance refused")
    pkt.write_text(bind.stdout, encoding="utf-8")
    (wiki / "wiki" / "sources" / "yu-1995-istar.md").write_text("changed synthetic corpus\n", encoding="utf-8")
    code, blocked = run(*base, "--passages", str(passages))
    require(code == 4 and blocked["reason_code"] == "SENTENCE-LOGIC-ELIGIBILITY", "changed live corpus refused")


def main() -> int:
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        passages = passage_file(tmp)
        case_scope(tmp, passages)
        case_states(tmp, passages)
        case_inventory(tmp, passages)
        case_markdown_boundaries(tmp, passages)
        case_admission(tmp)
        case_signals(tmp, passages)
        case_full_scope_and_view(tmp, passages)
        case_live_eligible(tmp, passages)
        from centroid_source_evidence_cases import run_cases as source_cases
        source_cases(tmp)
        from centroid_review_cases import run_cases as review_cases
        review_cases(tmp)
    print("centroid_sentence_logic_smoketest: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
