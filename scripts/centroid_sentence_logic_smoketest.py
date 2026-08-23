#!/usr/bin/env python3
"""Hermetic smoketest for centroid_sentence_logic.py."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
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


def _site_packages(prefix: Path) -> Path | None:
    for candidate in (
        prefix / "Lib" / "site-packages",
        prefix / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages",
    ):
        if candidate.is_dir():
            return candidate
    return None


def _pypdf_inventory(prefix: Path) -> dict[str, tuple[int, str]]:
    site = _site_packages(prefix)
    if site is None:
        return {}
    hits: dict[str, tuple[int, str]] = {}
    for path in site.glob("pypdf*"):
        files = [path] if path.is_file() else [item for item in path.rglob("*") if item.is_file()]
        for item in files:
            hits[str(item.resolve())] = (item.stat().st_size, hashlib.sha256(item.read_bytes()).hexdigest())
    return hits


def _venv_python(venv: Path) -> Path:
    for candidate in (venv / "Scripts" / "python.exe", venv / "bin" / "python"):
        if candidate.is_file():
            return candidate
    raise SystemExit(f"FAIL: isolated venv python missing under {venv}")


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _minimal_pdf(pages: list[str]) -> bytes:
    """Hand-rolled PDF so the fixture does not import host/Hermes pypdf."""
    font_n = 3 + 2 * len(pages)
    kids = " ".join(f"{3 + 2 * index} 0 R" for index in range(len(pages)))
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode("ascii"),
        font_n: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    for index, text in enumerate(pages):
        page_n = 3 + 2 * index
        content_n = 4 + 2 * index
        stream = f"BT /F1 12 Tf 72 720 Td ({_pdf_escape(text)}) Tj ET\n".encode("latin-1", "replace")
        objects[page_n] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Contents {content_n} 0 R /Resources << /Font << /F1 {font_n} 0 R >> >> >>"
        ).encode("ascii")
        objects[content_n] = b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"endstream"
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = {0: 0}
    for number in sorted(objects):
        offsets[number] = len(out)
        out += f"{number} 0 obj\n".encode("ascii") + objects[number] + b"\nendobj\n"
    xref_at = len(out)
    size = max(objects) + 1
    out += f"xref\n0 {size}\n".encode("ascii")
    out += b"0000000000 65535 f \n"
    for number in range(1, size):
        out += f"{offsets[number]:010d} 00000 n \n".encode("ascii")
    out += f"trailer\n<< /Size {size} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode("ascii")
    return bytes(out)


def _isolation_env(tmp: Path, extra: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env.pop("PYTHONHOME", None)
    env["PYTHONNOUSERSITE"] = "1"
    env["UV_MANAGED_PYTHON"] = "1"
    if extra:
        env.update(extra)
    return env


def _run_from_harness_root(argv: list[str], *, env: dict[str, str], timeout: int = 180) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        env=env,
        timeout=timeout,
    )


def assert_dependency_isolation(tmp: Path, packet: Path, manuscript: Path) -> None:
    """Fail if PDF isolation, passage independence, or fail-closed degrade."""
    require(shutil.which("uv") is not None, "uv is required for isolated PDF admission")
    hermes_prefix = Path(sys.prefix).resolve()
    before = _pypdf_inventory(hermes_prefix)
    quote = "Strategic actors depend on each other for goals to be achieved."
    pdf_path = tmp / "yu-2011-window.pdf"
    pdf_path.write_bytes(_minimal_pdf([f"spacer page {page}" for page in range(1, 7)] + [quote]))

    bare = tmp / "bare-managed-311"
    venv_run = _run_from_harness_root(
        ["uv", "venv", "--python", "3.11", "--managed-python", str(bare)],
        env=_isolation_env(tmp),
    )
    require(venv_run.returncode == 0, f"managed 3.11 venv must create: {venv_run.stdout}{venv_run.stderr}")
    bare_python = _venv_python(bare)
    bare_probe = _run_from_harness_root(
        [str(bare_python), "-c", "import importlib.util, sys; print(sys.prefix); print(importlib.util.find_spec('pypdf'))"],
        env=_isolation_env(tmp),
    )
    require(bare_probe.returncode == 0 and "None" in bare_probe.stdout.splitlines()[-1], "bare managed 3.11 must not already have pypdf")
    require(Path(bare_probe.stdout.splitlines()[0]).resolve() != hermes_prefix, "bare venv must not be Hermes shared venv")

    passage_argv = [
        str(bare_python),
        str(SCRIPT),
        "--packet",
        str(packet),
        "--manuscript",
        str(manuscript),
        "--mode",
        "review",
        "--passages",
        str(packet.parent / "passages.json"),
    ]
    passage_run = _run_from_harness_root(passage_argv, env=_isolation_env(tmp))
    require(passage_run.returncode == 0, f"non-PDF passage mode must stay dependency-free: {passage_run.stdout}{passage_run.stderr}")
    passage_receipt = json.loads(passage_run.stdout)
    require(passage_receipt["status"] == "ready_for_role", "passage mode must not mint CLEAN")
    require(passage_receipt["summary"]["CLEAN"] == 0, "passage mode must not mint CLEAN counts")
    require(passage_receipt["reason_code"] is None, "passage mode must not emit a dependency refusal")

    missing_run = _run_from_harness_root(
        [
            str(bare_python),
            str(SCRIPT),
            "--packet",
            str(packet),
            "--manuscript",
            str(manuscript),
            "--mode",
            "review",
            "--admit-pdf",
            str(pdf_path),
            "--pages",
            "7",
        ],
        env=_isolation_env(tmp),
    )
    require(missing_run.returncode == 4, f"unavailable pypdf must fail closed: {missing_run.stdout}{missing_run.stderr}")
    missing = json.loads(missing_run.stdout)
    require(missing["status"] == "blocked", "unavailable dependency must not silently degrade to a ready receipt")
    require(missing["reason_code"] == "SENTENCE-LOGIC-DEPENDENCY", "unavailable dependency must use stable SENTENCE-LOGIC-DEPENDENCY")
    require("CLEAN" not in json.dumps(missing), "fail-closed PDF admission must not mint CLEAN")

    probe = tmp / "interpreter-probe.json"
    probe_dir = tmp / "sitecustomize-dir"
    probe_dir.mkdir()
    (probe_dir / "sitecustomize.py").write_text(
        "import json, os, sys\n"
        "from importlib.metadata import version\n"
        "from importlib.util import find_spec\n"
        "from pathlib import Path\n"
        "spec = find_spec('pypdf')\n"
        "Path(os.environ['SENTENCE_LOGIC_ISOLATION_PROBE']).write_text(\n"
        "    json.dumps({\n"
        "        'executable': sys.executable,\n"
        "        'prefix': sys.prefix,\n"
        "        'version_info': list(sys.version_info[:3]),\n"
        "        'pypdf_origin': None if spec is None else spec.origin,\n"
        "        'pypdf_version': None if spec is None else version('pypdf'),\n"
        "    }),\n"
        "    encoding='utf-8',\n"
        ")\n",
        encoding="utf-8",
    )
    isolated_env = _isolation_env(
        tmp,
        {
            "PYTHONPATH": str(probe_dir),
            "SENTENCE_LOGIC_ISOLATION_PROBE": str(probe),
        },
    )
    isolated_run = _run_from_harness_root(
        [
            "uv",
            "run",
            "--python",
            "3.11",
            "--isolated",
            "--no-project",
            "--managed-python",
            "--script",
            str(SCRIPT),
            "--packet",
            str(packet),
            "--manuscript",
            str(manuscript),
            "--mode",
            "review",
            "--admit-pdf",
            str(pdf_path),
            "--pages",
            "7",
        ],
        env=isolated_env,
    )
    require(isolated_run.returncode == 0, f"PDF admission from harness root in managed 3.11 must succeed: {isolated_run.stdout}{isolated_run.stderr}")
    isolated = json.loads(isolated_run.stdout)
    require(isolated["status"] == "ready_for_role", "isolated PDF admission must not mint CLEAN")
    require(isolated["summary"]["CLEAN"] == 0, "isolated PDF admission must not mint CLEAN counts")
    require(isolated["pairs"][0]["verdict"] == "not_run", "roles still fill isolated PDF verdicts")
    require(len(isolated["admitted_passages"]) == 1, "isolated PDF admission must bind the requested page")
    admitted = isolated["admitted_passages"][0]
    require(admitted["admitted_by"] == "hash-bound-pdf", "PDF page must be hash-bound, not a silent paste fallback")
    require(admitted.get("page") == 7, "isolated PDF admission must read the requested page")
    require(quote in admitted["quote"].replace("\n", " "), "isolated PDF admission must extract the page text")

    require(probe.is_file(), "isolated run must record its interpreter identity")
    identity = json.loads(probe.read_text(encoding="utf-8"))
    child_prefix = Path(identity["prefix"]).resolve()
    child_exe = Path(identity["executable"]).resolve()
    require(identity["version_info"][:2] == [3, 11], "PDF admission must run on managed Python 3.11")
    require(child_prefix != hermes_prefix, "PDF admission must not use Hermes shared venv prefix")
    require(child_exe != Path(sys.executable).resolve(), "PDF admission must not use the Hermes interpreter")
    require(identity["pypdf_origin"], "isolated PDF admission must resolve pypdf inside the script env")
    require(
        hermes_prefix not in Path(identity["pypdf_origin"]).resolve().parents
        and Path(identity["pypdf_origin"]).resolve() != hermes_prefix,
        "isolated pypdf must not be loaded from Hermes shared venv",
    )
    require(identity["pypdf_version"] == "6.14.2", "isolated env must honor the PEP 723 pypdf pin")
    after = _pypdf_inventory(hermes_prefix)
    require(after == before, "isolated PDF admission must not mutate Hermes shared venv pypdf artifacts")


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
        passage_blocked = run(
            tmp,
            "--packet", str(pkt),
            "--manuscript", str(man),
            "--mode", "review",
            "--passages", str(pas),
            env=dependency_env,
        )
        require(passage_blocked.returncode == 0, f"passage mode must not require pypdf: {passage_blocked.stdout}{passage_blocked.stderr}")
        passage_blocked_receipt = json.loads(passage_blocked.stdout)
        require(
            passage_blocked_receipt["status"] == "ready_for_role" and passage_blocked_receipt["summary"]["CLEAN"] == 0,
            "blocked-pypdf passage mode must not mint CLEAN",
        )

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
        dependency_payload = json.loads(dependency_run.stdout)
        require(dependency_payload["status"] == "blocked", "missing pypdf must not degrade to a ready receipt")
        require(dependency_payload["reason_code"] == "SENTENCE-LOGIC-DEPENDENCY", "missing pypdf must keep the stable reason_code")

        assert_dependency_isolation(tmp, pkt, man)

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
