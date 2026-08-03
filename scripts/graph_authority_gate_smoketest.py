#!/usr/bin/env python3
"""Behavioral proof that structural graph validity cannot grant authority."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import coupling_readiness_check as readiness  # noqa: E402
import graph_authority_gate as gate  # noqa: E402


REASON = "GRAPH_GOVERNED_GENERATION_UNAVAILABLE"


def digest_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted((p for p in root.rglob("*") if p.is_file()), key=str):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def script_argv(name: str, *args: str) -> list[str]:
    return [sys.executable, "-B", str(ROOT / "scripts" / name), *args]


def run_script(name: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        script_argv(name, *args),
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def main() -> int:
    assert script_argv("probe.py")[:3] == [
        sys.executable, "-B", str(ROOT / "scripts" / "probe.py"),
    ]
    for structural in (None, False, True):
        result = gate.evaluate_graph_authority(structural_ok=structural)
        assert result["governed_available"] is False
        assert result["reason_code"] == REASON
        assert result["legacy_structural_ok"] is structural
    assert gate.is_graph_governed_available() is False

    with tempfile.TemporaryDirectory() as td:
        project = Path(td) / "project"
        wiki = Path(td) / "wiki"
        (project / "manuscript").mkdir(parents=True)
        (project / "references").mkdir()
        (project / "reviews").mkdir()
        (wiki / "graphify-out").mkdir(parents=True)
        manuscript = project / "manuscript" / "main.md"
        references = project / "references" / "REFERENCES.md"
        classification = project / "reviews" / "classification.md"
        manuscript.write_text(
            "Last updated: 2026-07-18\n\nA bounded claim (Yu 1995).\n",
            encoding="utf-8",
        )
        references.write_text("Last updated: 2026-07-18\n", encoding="utf-8")
        classification.write_text("# Classification\n", encoding="utf-8")
        (wiki / "graphify-out" / "GRAPH_REPORT.md").write_text("# Graph\n", encoding="utf-8")
        (wiki / "graphify-out" / "graph.json").write_text(
            json.dumps({
                "nodes": [{"id": "n1", "captured_at": "2026-07-19T00:00:00Z"}],
                "links": [],
            }),
            encoding="utf-8",
        )
        before = digest_tree(wiki)
        overrides = {
            "allow_missing_project_claude": True,
            "wiki_linked": "true",
            "coupling_e_on_review": "true",
            "wiki_path": str(wiki),
            "manuscript_path": str(manuscript),
            "references_path": str(references),
            "classification_path": str(classification),
            "allow_legacy_graph_confidence": False,
        }
        checks, metadata = readiness.run_checks(project, overrides=overrides)
        failed = [item.key for item in checks if not item.ok]
        assert failed == ["graph_governed_available"], failed
        assert metadata["legacy_structural_ok"] is True
        assert metadata["governed_available"] is False
        reason, _ = readiness.derive_noop_reason(checks, metadata)
        assert reason == REASON

        common = (
            "--project-root", str(project),
            "--date", "2026-07-19",
            "--allow-missing-project-claude",
            "--wiki-linked", "true",
            "--coupling-e-on-review", "true",
            "--wiki-path", str(wiki),
            "--manuscript-path", str(manuscript),
            "--references-path", str(references),
            "--classification-path", str(classification),
            "--allow-legacy-graph-confidence", "false",
        )
        preflight = run_script("sk20_preflight_gate.py", *common, "--strict-exit")
        assert preflight.returncode == 4, preflight.stdout + preflight.stderr
        envelope = json.loads(preflight.stdout)
        assert envelope["should_run_sk20"] is False
        assert envelope["reason_code"] == REASON
        noop = json.loads((project / "reviews" / "sk20_noop_2026-07-19.json").read_text(encoding="utf-8"))
        assert noop["reason_code"] == REASON

        overlay = run_script("sk20_overlay_run.py", *common)
        assert overlay.returncode == 2, overlay.stdout + overlay.stderr
        assert json.loads(overlay.stdout)["reason_code"] == REASON
        assert digest_tree(wiki) == before

        absent_wiki = Path(td) / "must-not-be-created"
        deferred = run_script(
            "sk20_autonomous_loop.py",
            "--project-root", str(project),
            "--wiki-path", str(absent_wiki),
        )
        assert deferred.returncode == 0
        deferred_packet = json.loads(deferred.stdout)
        assert deferred_packet["reason_code"] == "WIKI_WRITE_TRANSACTION_UNAVAILABLE"
        assert deferred_packet["wiki_mutation_performed"] is False
        assert not absent_wiki.exists()

    print("graph_authority_gate_smoketest: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
