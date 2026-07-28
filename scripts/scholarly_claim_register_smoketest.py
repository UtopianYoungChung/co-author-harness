#!/usr/bin/env python3
"""C1 red/benign-twin boundary for the scholarly claim register."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import scholarly_claim_register as claim_register


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "scholarly_claim_register.py"
CASES = ROOT / "scripts" / "fixtures" / "scholarly_claim_register" / "cases.json"


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _evidence_span(path: Path, marker: bytes) -> dict[str, Any]:
    raw = path.read_bytes()
    start = raw.index(marker)
    end = raw.index(b"\n", start)
    return {
        "path": path.as_posix(),
        "sha256": _sha_bytes(raw),
        "byte_start": start,
        "byte_end": end,
        "span_sha256": _sha_bytes(raw[start:end]),
    }


def _parent(value: Any, dotted: str) -> tuple[Any, str | int]:
    parts = dotted.split(".")
    current = value
    for part in parts[:-1]:
        current = current[int(part)] if isinstance(current, list) else current[part]
    leaf: str | int = int(parts[-1]) if isinstance(current, list) else parts[-1]
    return current, leaf


def _apply(value: Any, change: dict[str, Any]) -> None:
    parent, leaf = _parent(value, change["path"])
    operation = change["op"]
    if operation == "remove":
        if isinstance(parent, list):
            parent.pop(leaf)
        else:
            del parent[leaf]
    elif operation == "set":
        parent[leaf] = copy.deepcopy(change["value"])
    elif operation == "append":
        target = parent[leaf]
        if not isinstance(target, list):
            raise AssertionError(f"append target is not a list: {change['path']}")
        target.append(copy.deepcopy(change["value"]))
    elif operation == "generator_omit":
        omitted = copy.deepcopy(parent[leaf])
        claim_id = change["value"]
        if omitted.get("claim_id") != claim_id:
            raise AssertionError("generator omission does not identify the bound artifact claim")
        value["generator_inventory"].remove(claim_id)
        value["evaluator_additions"].append(omitted)
        value["evaluator_omissions"].append(
            {
                "claim_id": claim_id,
                "text": omitted["text"],
                "span_sha256": omitted["span_sha256"],
                "locator": copy.deepcopy(omitted["locator"]),
                "reason": (
                    "Independent Evaluator identified this load-bearing artifact claim "
                    "outside the Generator inventory."
                ),
            }
        )
    elif operation == "duplicate_evidence_locator":
        value["claims"][0]["evidence_locator"].append(
            copy.deepcopy(value["claims"][0]["evidence_locator"][0])
        )
    elif operation == "evaluator_addition_complete":
        added = copy.deepcopy(value["claims"][1])
        value["generator_inventory"].remove(added["claim_id"])
        value["evaluator_additions"].append(added)
    elif operation == "duplicate_claim_span_alias":
        first = value["claims"][0]
        second = value["claims"][1]
        second["text"] = first["text"]
        second["span_sha256"] = first["span_sha256"]
        second["locator"] = copy.deepcopy(first["locator"])
    else:
        raise AssertionError(f"unknown fixture operation: {operation}")


def _base_register(
    artifact: Path,
    evidence_source: Path,
    *,
    section: str = "Synthetic analysis",
) -> dict[str, Any]:
    artifact_bytes = artifact.read_bytes()
    artifact_text = artifact_bytes.decode("utf-8", errors="strict")

    def evidence_span(claim_id: str) -> list[dict[str, Any]]:
        return [_evidence_span(evidence_source, f"{claim_id}:".encode("utf-8"))]

    def claim(claim_id: str, claim_text: str) -> dict[str, Any]:
        start = artifact_text.index(claim_text)
        return {
            "claim_id": claim_id,
            "text": claim_text,
            "span_sha256": _sha_bytes(claim_text.encode("utf-8")),
            "locator": {
                "section": section,
                "line": len(re.findall(r"\r\n|\n|\r", artifact_text[:start])) + 1,
                "byte_start": len(artifact_text[:start].encode("utf-8")),
                "byte_end": len(artifact_text[: start + len(claim_text)].encode("utf-8")),
            },
            "load_bearing": True,
            "viewpoint": "source_ascription",
            "provenance": "direct_source",
            "evidence_locator": evidence_span(claim_id),
            "admission_use": "admitted_evidence",
            "argument_leg": "ascription",
            "modal_force": "qualified",
            "warrant_relation": "constraint",
        }

    first_text = "A source states a bounded synthetic observation."
    second_text = "A second load-bearing observation constrains the boundary."
    return {
        "schema_version": "1.0.0",
        "register_id": "SCR-SYNTHETIC-001",
        "artifact": {
            "path": artifact.as_posix(),
            "sha256": _sha_bytes(artifact_bytes),
            "byte_length": len(artifact_bytes),
        },
        "review_dispatch": {
            "dispatch_id": "dispatch-evaluator-synthetic-001",
            "role": "evaluator",
        },
        "claims": [claim("C-001", first_text), claim("C-002", second_text)],
        "generator_inventory": ["C-001", "C-002"],
        "evaluator_additions": [],
        "evaluator_omissions": [],
        "coverage_disposition": "complete",
        "created_at": "2026-07-26T00:00:00Z",
    }


def _result_codes(stdout: str) -> tuple[set[str], list[dict[str, Any]]]:
    value = json.loads(stdout)
    findings = value.get("findings", [])
    if not isinstance(findings, list):
        raise AssertionError("validator result findings must be a list")
    codes = {
        row["code"] for row in findings
        if isinstance(row, dict) and isinstance(row.get("code"), str)
    }
    return codes, findings


def _run_validator(artifact: Path, register: Path) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--artifact", str(artifact), "--register", str(register)],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    return completed, json.loads(completed.stdout)


def main() -> int:
    fixture = json.loads(CASES.read_text(encoding="utf-8"))
    cases = fixture.get("cases", [])
    assert fixture.get("provenance", {}).get("live_research_material") is False
    assert len(cases) == 23
    assert len({case["id"] for case in cases}) == len(cases)
    assert all(set(case["red_change"]) >= {"op", "path"} for case in cases)

    interface_missing = not SCRIPT.is_file()
    failures: list[str] = []
    optional_alias_executed = 0
    optional_alias_skipped = 0
    api_cases = 0
    with tempfile.TemporaryDirectory(prefix="scholarly-claim-register-") as td:
        temporary = Path(td)
        artifact = temporary / "synthetic.md"
        artifact.write_text(
            "# Synthetic analysis\n\n"
            "A source states a bounded synthetic observation.\n"
            "A second load-bearing observation constrains the boundary.\n",
            encoding="utf-8",
            newline="\n",
        )
        evidence_source = temporary / "synthetic-source.txt"
        evidence_source.write_text(
            "C-001: bounded observation.\nC-002: boundary constraint.\n",
            encoding="utf-8",
            newline="\n",
        )
        evidence_source_b = temporary / "synthetic-source-b.txt"
        evidence_source_b.write_text(
            "B-001: independent comparison observation.\n",
            encoding="utf-8",
            newline="\n",
        )
        for case in cases:
            clean = _base_register(artifact, evidence_source)
            for change in case.get("base_changes", []):
                _apply(clean, change)
            red = copy.deepcopy(clean)
            _apply(red, case["red_change"])
            if case["id"] == "generator_omission_added_by_evaluator":
                omitted = red["claims"][1]
                assert omitted["claim_id"] not in red["generator_inventory"]
                assert red["evaluator_additions"] == [omitted]
                assert red["evaluator_omissions"][0]["text"] == omitted["text"]
                assert red["evaluator_omissions"][0]["span_sha256"] == omitted["span_sha256"]
                assert red["evaluator_omissions"][0]["locator"] == omitted["locator"]
                assert red["coverage_disposition"] == "complete"
            clean_path = temporary / f"{case['id']}.clean.json"
            red_path = temporary / f"{case['id']}.red.json"
            _write_json(clean_path, clean)
            _write_json(red_path, red)

            if interface_missing:
                expected = ",".join(case["expected_refusal_codes"])
                print(
                    f"[INTERFACE_BLOCKED] {case['id']}: missing {SCRIPT.relative_to(ROOT)}; "
                    f"expected red refusal {expected} and clean findings []"
                )
                continue

            clean_run = subprocess.run(
                [sys.executable, str(SCRIPT), "--artifact", str(artifact), "--register", str(clean_path)],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                check=False,
            )
            red_run = subprocess.run(
                [sys.executable, str(SCRIPT), "--artifact", str(artifact), "--register", str(red_path)],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                check=False,
            )
            try:
                clean_codes, clean_findings = _result_codes(clean_run.stdout)
                red_codes, _ = _result_codes(red_run.stdout)
            except (AssertionError, json.JSONDecodeError) as exc:
                failures.append(f"{case['id']}: non-contract output: {exc}")
                continue
            expected = set(case["expected_refusal_codes"])
            if clean_run.returncode != 0 or clean_findings != case["clean_expected_findings"]:
                failures.append(
                    f"{case['id']}: clean twin rc={clean_run.returncode} findings={sorted(clean_codes)}"
                )
            if red_run.returncode == 0 or red_codes != expected:
                failures.append(
                    f"{case['id']}: red rc={red_run.returncode} findings={sorted(red_codes)} "
                    f"expected={sorted(expected)}"
                )

        if not interface_missing:
            honest_incomplete = _base_register(artifact, evidence_source)
            _apply(
                honest_incomplete,
                {"op": "generator_omit", "path": "claims.1", "value": "C-002"},
            )
            honest_incomplete["coverage_disposition"] = "incomplete"
            incomplete_path = temporary / "honest-incomplete.json"
            _write_json(incomplete_path, honest_incomplete)
            incomplete_run = subprocess.run(
                [sys.executable, str(SCRIPT), "--artifact", str(artifact), "--register", str(incomplete_path)],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                check=False,
            )
            try:
                incomplete_result = json.loads(incomplete_run.stdout)
            except json.JSONDecodeError as exc:
                failures.append(f"honest incomplete register: non-contract output: {exc}")
            else:
                if (
                    incomplete_run.returncode != 0
                    or incomplete_result.get("status") != "incomplete"
                    or incomplete_result.get("coverage_disposition") != "incomplete"
                    or incomplete_result.get("findings") != []
                ):
                    failures.append(
                        "honest incomplete register did not remain valid-but-incomplete: "
                        f"rc={incomplete_run.returncode} result={incomplete_result}"
                    )

            render_path = temporary / "render-source.json"
            render_value = _base_register(artifact, evidence_source)
            _write_json(render_path, render_value)
            render_run = subprocess.run(
                [sys.executable, str(SCRIPT), "--artifact", str(artifact), "--register", str(render_path), "--render"],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                check=False,
            )
            if (
                render_run.returncode != 0
                or not render_run.stdout.startswith("<!-- NON-AUTHORITATIVE VIEW:")
                or render_value["artifact"]["sha256"] not in render_run.stdout
                or "C-001" not in render_run.stdout
            ):
                failures.append("Markdown renderer did not preserve non-authoritative exact-binding view")

            addition_incomplete = _base_register(artifact, evidence_source)
            _apply(
                addition_incomplete,
                {"op": "evaluator_addition_complete", "path": "claims.1"},
            )
            addition_incomplete["coverage_disposition"] = "incomplete"
            addition_path = temporary / "addition-incomplete.json"
            _write_json(addition_path, addition_incomplete)
            addition_run = subprocess.run(
                [sys.executable, str(SCRIPT), "--artifact", str(artifact), "--register", str(addition_path)],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                check=False,
            )
            addition_result = json.loads(addition_run.stdout)
            if (
                addition_run.returncode != 0
                or addition_result.get("status") != "incomplete"
                or addition_result.get("evaluator_addition_count") != 1
                or addition_result.get("findings") != []
            ):
                failures.append("exact Evaluator addition was not retained as valid-but-incomplete")

            cross_source = _base_register(artifact, evidence_source)
            cross_source["claims"][0]["provenance"] = "cross_source_comparison"
            cross_source["claims"][0]["evidence_locator"] = [
                _evidence_span(evidence_source, b"C-001:"),
                _evidence_span(evidence_source_b, b"B-001:"),
            ]
            cross_path = temporary / "cross-source-valid.json"
            _write_json(cross_path, cross_source)
            cross_run = subprocess.run(
                [sys.executable, str(SCRIPT), "--artifact", str(artifact), "--register", str(cross_path)],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                check=False,
            )
            cross_result = json.loads(cross_run.stdout)
            if (
                cross_run.returncode != 0
                or cross_result.get("status") != "qualified"
                or cross_result.get("findings") != []
            ):
                failures.append("two-sided exact cross-source locator did not qualify")

            cross_api = claim_register.validate_register_with_dependencies(
                artifact,
                cross_path,
                expected_register_payload=cross_path.read_bytes(),
            )
            dependency_rows = cross_api.get("dependencies", [])
            dependency_by_path = {
                row.get("path"): row for row in dependency_rows if isinstance(row, dict)
            }
            expected_dependencies = {
                artifact.resolve(),
                cross_path.resolve(),
                evidence_source.resolve(),
                evidence_source_b.resolve(),
                claim_register.SCHEMA_PATH.resolve(),
            }
            missing_dependencies = sorted(
                str(path) for path in expected_dependencies - {Path(path) for path in dependency_by_path}
            )
            stale_dependencies = sorted(
                path
                for path, row in dependency_by_path.items()
                if not isinstance(path, str)
                or not Path(path).is_file()
                or row.get("sha256") != _sha_bytes(Path(path).read_bytes())
                or row.get("byte_length") != Path(path).stat().st_size
            )
            if (
                cross_api.get("status") != "qualified"
                or cross_api.get("findings") != []
                or len(dependency_by_path) != len(dependency_rows)
                or missing_dependencies
                or stale_dependencies
            ):
                failures.append(
                    "claim-register read-set API omitted or stale-bound a cross-source input: "
                    f"missing={missing_dependencies} stale={stale_dependencies}"
                )
            api_cases += 1

            def mutation_probe(target: Path, expected_code: str, label: str) -> None:
                nonlocal api_cases
                original_target = target.read_bytes()
                original_coverage = claim_register._coverage_findings
                mutated = False

                def wrapper(value: dict[str, Any]) -> list[dict[str, str]]:
                    nonlocal mutated
                    result = original_coverage(value)
                    if not mutated:
                        target.write_bytes(original_target + b" ")
                        mutated = True
                    return result

                claim_register._coverage_findings = wrapper
                try:
                    result = claim_register.validate_register_with_dependencies(
                        artifact,
                        cross_path,
                        expected_register_payload=cross_path.read_bytes(),
                    )
                finally:
                    claim_register._coverage_findings = original_coverage
                    target.write_bytes(original_target)
                codes = {row.get("code") for row in result.get("findings", [])}
                if result.get("status") != "refused" or codes != {expected_code}:
                    failures.append(
                        f"claim-register {label} mutation was not refused exactly: {result!r}"
                    )
                api_cases += 1

            mutation_probe(
                evidence_source_b,
                "SCR-LOCATOR-REQUIRED",
                "evidence-source",
            )
            repository_schema = claim_register.SCHEMA_PATH
            repository_schema_payload = repository_schema.read_bytes()
            repository_schema_sha256 = _sha_bytes(repository_schema_payload)
            isolated_schema = temporary / "isolated-scholarly-claim-register.schema.json"
            isolated_schema.write_bytes(repository_schema_payload)
            claim_register.SCHEMA_PATH = isolated_schema
            try:
                if _sha_bytes(repository_schema.read_bytes()) != repository_schema_sha256:
                    failures.append("repository schema changed before isolated mutation probe")
                mutation_probe(
                    isolated_schema,
                    "SCR-SCHEMA",
                    "isolated-schema",
                )
                if _sha_bytes(repository_schema.read_bytes()) != repository_schema_sha256:
                    failures.append("repository schema changed during isolated mutation probe")

                isolated_schema.write_bytes(b'{"type":5}')
                invalid_schema = claim_register.validate_register_with_dependencies(
                    artifact,
                    cross_path,
                    expected_register_payload=cross_path.read_bytes(),
                )
                invalid_codes = {
                    row.get("code") for row in invalid_schema.get("findings", [])
                }
                if (
                    invalid_schema.get("status") != "refused"
                    or invalid_codes != {"SCR-SCHEMA"}
                ):
                    failures.append(
                        "parseable invalid isolated schema was not refused exactly: "
                        f"{invalid_schema!r}"
                    )
                api_cases += 1
                if _sha_bytes(repository_schema.read_bytes()) != repository_schema_sha256:
                    failures.append("repository schema changed during meta-schema probe")

                _write_json(
                    isolated_schema,
                    {
                        "$schema": "https://json-schema.org/draft/2020-12/schema",
                        "$ref": "missing-schema.json",
                    },
                )
                unresolved_schema = claim_register.validate_register_with_dependencies(
                    artifact,
                    cross_path,
                    expected_register_payload=cross_path.read_bytes(),
                )
                unresolved_codes = {
                    row.get("code") for row in unresolved_schema.get("findings", [])
                }
                if (
                    unresolved_schema.get("status") != "refused"
                    or unresolved_codes != {"SCR-SCHEMA"}
                ):
                    failures.append(
                        "unresolved-ref isolated schema was not refused exactly: "
                        f"{unresolved_schema!r}"
                    )
                api_cases += 1
                if _sha_bytes(repository_schema.read_bytes()) != repository_schema_sha256:
                    failures.append("repository schema changed during unresolved-ref probe")
            finally:
                claim_register.SCHEMA_PATH = repository_schema
            if _sha_bytes(repository_schema.read_bytes()) != repository_schema_sha256:
                failures.append("repository schema changed after isolated mutation probes")

            lexical_alias = copy.deepcopy(cross_source)
            lexical_alias["claims"][0]["evidence_locator"][1] = copy.deepcopy(
                lexical_alias["claims"][0]["evidence_locator"][0]
            )
            lexical_alias["claims"][0]["evidence_locator"][1]["path"] = evidence_source.name
            lexical_path = temporary / "cross-source-lexical-alias.json"
            _write_json(lexical_path, lexical_alias)
            lexical_run, lexical_result = _run_validator(artifact, lexical_path)
            lexical_codes = {row["code"] for row in lexical_result.get("findings", [])}
            if lexical_run.returncode == 0 or lexical_codes != {"SCR-LOCATOR-REQUIRED"}:
                failures.append("cross-source lexical alias was not refused exactly")

            for alias_kind, create_alias in (
                ("hardlink", lambda target: os.link(evidence_source, target)),
                ("symlink", lambda target: os.symlink(evidence_source, target)),
            ):
                alias_path = temporary / f"synthetic-source-{alias_kind}.txt"
                try:
                    create_alias(alias_path)
                except OSError as exc:
                    optional_alias_skipped += 1
                    print(f"[SKIP] {alias_kind} alias unavailable: {exc.__class__.__name__}")
                    continue
                optional_alias_executed += 1
                alias_value = copy.deepcopy(cross_source)
                alias_value["claims"][0]["evidence_locator"][1] = _evidence_span(
                    alias_path, b"C-001:"
                )
                alias_register = temporary / f"cross-source-{alias_kind}-alias.json"
                _write_json(alias_register, alias_value)
                alias_run, alias_result = _run_validator(artifact, alias_register)
                alias_codes = {row["code"] for row in alias_result.get("findings", [])}
                if alias_run.returncode == 0 or alias_codes != {"SCR-LOCATOR-REQUIRED"}:
                    failures.append(f"cross-source {alias_kind} alias was not refused exactly")

            section_cases = [
                ("terminal-hash-content", "# Analysis#\n\n", "Analysis#", "\n"),
                ("three-space-heading", "   ## Three Space\n\n", "Three Space", "\n"),
                ("backtick-fence", "# Outer\n```text\n# Fake\n```\n\n", "Outer", "\n"),
                ("tilde-fence", "# Outer\n~~~ text\n## Fake\n~~~~\n\n", "Outer", "\n"),
                ("closing-hashes", "## Closed ###\n\n", "Closed", "\n"),
                ("inline-and-indented", "# Real\nText # inline\n    # Indented\n\n", "Real", "\n"),
                ("repeated-headings", "# First\n## Second\n\n", "Second", "\n"),
                ("crlf-unicode", "### Étude\r\n\r\n", "Étude", "\r\n"),
                ("invalid-backtick-info", "# Outer\n```bad`info\n# Inner\n\n", "Inner", "\n"),
                ("tilde-info-allows-tilde", "# Outer\n~~~ bad~info\n# Fake\n~~~\n\n", "Outer", "\n"),
                ("hash-only-many", "# ###\n\n", "<empty-heading>", "\n"),
                ("hash-only-single", "# #\n\n", "<empty-heading>", "\n"),
                ("hash-prefix-text", "# ### text\n\n", "### text", "\n"),
                ("other-character-closing", "# Alpha #x\n\n", "Alpha #x", "\n"),
                ("bare-hash", "#\n\n", "<empty-heading>", "\n"),
                ("seven-hashes", "# Outer\n####### Not a heading\n\n", "Outer", "\n"),
                ("short-fence-close", "# Outer\n```` text\n# Fake\n```\n# Still fake\n````\n\n", "Outer", "\n"),
                ("other-fence-close", "# Outer\n``` text\n# Fake\n~~~\n# Still fake\n```\n\n", "Outer", "\n"),
                ("vt-inline", "# Outer\ntext\u000b# Fake\n\n", "Outer", "\n"),
                ("ff-inline", "# Outer\ntext\u000c# Fake\n\n", "Outer", "\n"),
                ("nel-inline", "# Outer\ntext\u0085# Fake\n\n", "Outer", "\n"),
                ("ls-inline", "# Outer\ntext\u2028# Fake\n\n", "Outer", "\n"),
                ("ps-inline", "# Outer\ntext\u2029# Fake\n\n", "Outer", "\n"),
                ("fs-inline", "# Outer\ntext\u001c# Fake\n\n", "Outer", "\n"),
                ("gs-inline", "# Outer\ntext\u001d# Fake\n\n", "Outer", "\n"),
                ("rs-inline", "# Outer\ntext\u001e# Fake\n\n", "Outer", "\n"),
                ("cr-only", "# CR Section\r\r", "CR Section", "\r"),
            ]
            for section_id, prefix, expected_section, line_ending in section_cases:
                section_artifact = temporary / f"section-{section_id}.md"
                body = (
                    "A source states a bounded synthetic observation."
                    + line_ending
                    + "A second load-bearing observation constrains the boundary."
                    + line_ending
                )
                section_artifact.write_bytes((prefix + body).encode("utf-8"))
                section_value = _base_register(
                    section_artifact,
                    evidence_source,
                    section=expected_section,
                )
                section_register = temporary / f"section-{section_id}.json"
                _write_json(section_register, section_value)
                section_run, section_result = _run_validator(
                    section_artifact, section_register
                )
                if section_run.returncode != 0 or section_result.get("findings") != []:
                    failures.append(
                        f"CommonMark ATX section case {section_id} failed: {section_result}"
                    )
                wrong_section = copy.deepcopy(section_value)
                wrong_section_name = (
                    "Not empty" if expected_section == "<empty-heading>" else "Wrong section"
                )
                for claim in wrong_section["claims"]:
                    claim["locator"]["section"] = wrong_section_name
                wrong_register = temporary / f"section-{section_id}-wrong.json"
                _write_json(wrong_register, wrong_section)
                wrong_run, wrong_result = _run_validator(
                    section_artifact, wrong_register
                )
                wrong_codes = {
                    row["code"] for row in wrong_result.get("findings", [])
                }
                if (
                    wrong_run.returncode == 0
                    or wrong_codes != {"SCR-ARTIFACT-STALE"}
                ):
                    failures.append(
                        f"CommonMark ATX wrong-section case {section_id} was not refused exactly"
                    )

    if interface_missing:
        print(f"scholarly_claim_register_smoketest: RED 0/{len(cases)} defended")
        return 1
    if failures:
        for failure in failures:
            print(f"[RED] {failure}")
        print(f"scholarly_claim_register_smoketest: RED {len(failures)} mismatch(es)")
        return 1
    print(
        f"scholarly_claim_register_smoketest: PASS ({len(cases)} red/twin pairs; "
        f"section parser pairs=27; optional aliases executed={optional_alias_executed} "
        f"skipped={optional_alias_skipped}; read-set API cases={api_cases})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
