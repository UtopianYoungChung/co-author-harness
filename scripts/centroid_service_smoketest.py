#!/usr/bin/env python3
"""Behavioral contract for the public read-only centroid packet builder."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "scripts" / "centroid_service.py"
SCHEMA = ROOT / "references" / "schemas" / "centroid_analysis.schema.json"
sys.path.insert(0, str(ROOT / "scripts"))
from domain_native_register_smoketest import write_fixture  # noqa: E402


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        return digest.hexdigest()
    for path in sorted((p for p in root.rglob("*") if p.is_file()), key=str):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def invoke(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SERVICE), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def common_args(project: Path, manuscript: Path, wiki: Path, workspace: Path) -> list[str]:
    return [
        "--manuscript", str(manuscript),
        "--project-root", str(project),
        "--wiki-root", str(wiki),
        "--workspace-root", str(workspace),
        "--harness-root", str(ROOT),
    ]


def validate_packet(packet: dict, schema: dict) -> None:
    """Exercise the shipped schema without adding a runtime jsonschema dependency."""
    properties = schema["properties"]
    assert set(schema["required"]) <= set(packet)
    if schema.get("additionalProperties") is False:
        assert set(packet) <= set(properties), sorted(set(packet) - set(properties))
    type_map = {
        "object": dict,
        "array": list,
        "string": str,
        "null": type(None),
        "boolean": bool,
    }
    for key, value in packet.items():
        rule = properties[key]
        if "const" in rule:
            assert value == rule["const"], (key, value, rule["const"])
        if "enum" in rule:
            assert value in rule["enum"], (key, value)
        if "type" in rule:
            allowed = rule["type"] if isinstance(rule["type"], list) else [rule["type"]]
            assert any(isinstance(value, type_map[item]) for item in allowed), (key, value, allowed)
        if isinstance(value, list) and "maxItems" in rule:
            assert len(value) <= rule["maxItems"]
    conditional = schema["allOf"][0]
    branch = conditional["then"] if packet["status"] == "ready" else conditional["else"]
    assert set(branch["required"]) <= set(packet)
    for key, rule in branch.get("properties", {}).items():
        value = packet[key]
        allowed = rule["type"] if isinstance(rule["type"], list) else [rule["type"]]
        assert any(isinstance(value, type_map[item]) for item in allowed), (key, value, allowed)
        if isinstance(value, str) and "minLength" in rule:
            assert len(value) >= rule["minLength"]


def main() -> int:
    assert SERVICE.is_file(), "centroid analysis service is missing"
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema["$id"].endswith("centroid_analysis.schema.json")
    assert {"status", "reason_code", "read_only"} <= set(schema["required"])

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        project = base / "project"
        manuscript = project / "manuscript" / "main.md"
        manuscript.parent.mkdir(parents=True)
        manuscript.write_text(
            "# Study\n\nCafé systems remain accountable.\n\n"
            "## Methods\n\nWe compare two bounded cases.\n\n"
            "## Results\n\nThe trace stays explicit.\n",
            encoding="utf-8",
        )
        wiki, workspace = write_fixture(base / "corpus", all_members=True)
        before = {path: tree_digest(path) for path in (project, wiki, workspace)}

        ready = invoke(*common_args(project, manuscript, wiki, workspace))
        assert ready.returncode == 0, (ready.returncode, ready.stdout, ready.stderr)
        packet = json.loads(ready.stdout)
        validate_packet(packet, schema)
        assert packet["status"] == "ready"
        assert packet["reason_code"] is None
        assert packet["read_only"] is True
        assert packet["public_activation"] == "active"
        assert packet["semantic_findings"] == []
        assert packet["manuscript"]["scope"]["kind"] == "full_manuscript"
        assert len(packet["manuscript"]["sha256"]) == 64
        assert packet["policy"]["attestation_view_pin"]
        assert packet["policy"]["exemplar_view_pin"]
        assert "review" == packet["analysis_contract"]["derivation"]

        write_mode = invoke(
            *common_args(project, manuscript, wiki, workspace),
            "--mode", "write",
        )
        assert write_mode.returncode == 0, write_mode.stdout + write_mode.stderr
        assert json.loads(write_mode.stdout)["analysis_contract"]["derivation"] == "write"

        graph_path = workspace / "knowledge" / "LLM wiki" / "graphify-out" / "graph.json"
        graph_bytes = graph_path.read_bytes()
        graph = json.loads(graph_bytes)
        graph["graph"]["extraction_mode"] = "structural-only"
        graph_path.write_text(json.dumps(graph), encoding="utf-8")
        ineligible = invoke(*common_args(project, manuscript, wiki, workspace))
        assert ineligible.returncode == 4
        assert json.loads(ineligible.stdout)["reason_code"] == "GRAPH-SEMANTIC-INELIGIBLE"
        graph_path.write_bytes(graph_bytes)

        heading = invoke(
            *common_args(project, manuscript, wiki, workspace),
            "--heading", "Methods",
            "--exemplar-warrant", "surface",
        )
        assert heading.returncode == 0, heading.stdout + heading.stderr
        scoped = json.loads(heading.stdout)
        assert scoped["manuscript"]["scope"]["heading"] == "Methods"
        assert scoped["manuscript"]["scope"]["start_line"] == 5
        assert scoped["analysis_contract"]["exemplar_warrant"] == "surface"

        unresolved = invoke(
            *common_args(project, manuscript, wiki, workspace),
            "--heading", "Missing heading",
        )
        assert unresolved.returncode == 4
        unresolved_packet = json.loads(unresolved.stdout)
        validate_packet(unresolved_packet, schema)
        assert unresolved_packet["reason_code"] == "HEADING_NOT_RESOLVED"

        manuscript.write_text("# Table only\n\n| A | B |\n|---|---|\n| 1 | 2 |\n", encoding="utf-8")
        no_prose = invoke(*common_args(project, manuscript, wiki, workspace))
        assert no_prose.returncode == 4
        no_prose_packet = json.loads(no_prose.stdout)
        validate_packet(no_prose_packet, schema)
        assert no_prose_packet["reason_code"] == "NO_PROSE"

        manuscript.write_text("# One\n\nText.\n\n# One\n\nMore text.\n", encoding="utf-8")
        duplicate = invoke(*common_args(project, manuscript, wiki, workspace), "--heading", "One")
        assert duplicate.returncode == 4
        assert json.loads(duplicate.stdout)["reason_code"] == "HEADING_AMBIGUOUS"

        manuscript.write_text("# Bound\n\nCurrent prose.\n", encoding="utf-8")
        (project / "reviews").mkdir(parents=True)
        (project / "reviews" / "phase_state.json").write_text(
            json.dumps({
                "milestone_framework": {
                    "policy_bindings": {
                        "reader_accessibility": {
                            "profile_sha256": "0" * 64,
                            "attestation_view_pin": "1" * 64,
                            "exemplar_view_pin": "2" * 64,
                        }
                    }
                }
            }),
            encoding="utf-8",
        )
        stale = invoke(*common_args(project, manuscript, wiki, workspace))
        assert stale.returncode == 4
        stale_packet = json.loads(stale.stdout)
        validate_packet(stale_packet, schema)
        assert stale_packet["reason_code"] == "PROJECT_BINDING_STALE"
        (project / "reviews" / "phase_state.json").unlink()
        (project / "reviews").rmdir()

        missing = invoke(*common_args(project, project / "missing.md", wiki, workspace))
        assert missing.returncode == 4
        assert json.loads(missing.stdout)["reason_code"] == "MANUSCRIPT_UNREADABLE"

        try:
            validate_packet({**packet, "unexpected": True}, schema)
        except AssertionError:
            pass
        else:
            raise AssertionError("schema check accepted an additional property")

        help_result = invoke("--help")
        assert help_result.returncode == 0
        assert "--apply" not in help_result.stdout
        assert "--mode" in help_result.stdout

        after = {path: tree_digest(path) for path in (project, wiki, workspace)}
        # Restore-neutral comparison: only the smoke itself changed the manuscript.
        assert before[wiki] == after[wiki]
        assert before[workspace] == after[workspace]
        assert not (project / "reviews").exists()
        assert not (project / "reviews" / "phase_state.json").exists()

    print("centroid_service_smoketest: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
