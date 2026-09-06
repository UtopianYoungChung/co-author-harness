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


def _v110_span(raw: bytes, text: str) -> tuple[int, int]:
    needle = text.encode("utf-8")
    start = raw.find(needle)
    if start < 0 or raw.find(needle, start + 1) >= 0:
        raise AssertionError(f"inventory span missing or not unique: {text!r}")
    return start, start + len(needle)


def _v110_locator(raw: bytes, start: int, end: int) -> dict[str, Any]:
    section = claim_register._nearest_section(raw, start)
    line = claim_register._commonmark_line_number(raw, start)
    if not isinstance(section, str) or line is None:
        raise AssertionError(f"inventory locator failed start={start}")
    return {
        "section": section,
        "line": line,
        "byte_start": start,
        "byte_end": end,
    }


def _v110_block(
    raw: bytes,
    block_id: str,
    kind: str,
    text: str,
    coverage: str,
    *,
    claim_ids: list[str] | None = None,
    reason: str | None = None,
    start: int | None = None,
    end: int | None = None,
) -> dict[str, Any]:
    if start is None or end is None:
        start, end = _v110_span(raw, text)
    block: dict[str, Any] = {
        "block_id": block_id,
        "kind": kind,
        "locator": _v110_locator(raw, start, end),
        "span_sha256": _sha_bytes(raw[start:end]),
        "coverage": coverage,
        "claim_ids": list(claim_ids or []),
    }
    if reason is not None:
        block["reason"] = reason
    return block


def _v110_claim(
    artifact: Path,
    evidence: Path,
    claim_id: str,
    claim_text: str,
    evidence_marker: bytes,
) -> dict[str, Any]:
    raw = artifact.read_bytes()
    start, end = _v110_span(raw, claim_text)
    return {
        "claim_id": claim_id,
        "text": claim_text,
        "span_sha256": _sha_bytes(claim_text.encode("utf-8")),
        "locator": _v110_locator(raw, start, end),
        "load_bearing": True,
        "viewpoint": "source_ascription",
        "provenance": "direct_source",
        "evidence_locator": [_evidence_span(evidence, evidence_marker)],
        "admission_use": "admitted_evidence",
        "argument_leg": "ascription",
        "modal_force": "qualified",
        "warrant_relation": "constraint",
    }


def _v110_register(
    artifact: Path,
    claims: list[dict[str, Any]],
    blocks: list[dict[str, Any]],
    *,
    register_id: str,
    schema_version: str = "1.1.0",
    disposition: str = "complete",
    include_inventory: bool = True,
) -> dict[str, Any]:
    raw = artifact.read_bytes()
    value: dict[str, Any] = {
        "schema_version": schema_version,
        "register_id": register_id,
        "artifact": {
            "path": artifact.as_posix(),
            "sha256": _sha_bytes(raw),
            "byte_length": len(raw),
        },
        "review_dispatch": {
            "dispatch_id": "dispatch-evaluator-v110-synthetic",
            "role": "evaluator",
        },
        "claims": claims,
        "generator_inventory": [claim["claim_id"] for claim in claims],
        "evaluator_additions": [],
        "evaluator_omissions": [],
        "coverage_disposition": disposition,
        "created_at": "2026-09-05T00:00:00Z",
    }
    if include_inventory:
        value["document_inventory"] = {
            "blocks": blocks,
            "whitespace_gaps_ignored": True,
        }
    return value


def _v110_expect(
    failures: list[str],
    label: str,
    run: subprocess.CompletedProcess[str],
    result: dict[str, Any],
    *,
    exit_code: int,
    status: str,
    codes: set[str],
    inventory: dict[str, Any] | None = None,
) -> None:
    got_codes = {
        row["code"]
        for row in result.get("findings") or []
        if isinstance(row, dict) and isinstance(row.get("code"), str)
    }
    if run.returncode != exit_code or result.get("status") != status or got_codes != codes:
        failures.append(
            f"{label}: rc={run.returncode} status={result.get('status')!r} "
            f"codes={sorted(got_codes)} expected_rc={exit_code} "
            f"expected_status={status!r} expected_codes={sorted(codes)}"
        )
        return
    if inventory is None:
        return
    inv = result.get("document_inventory_result")
    if not isinstance(inv, dict):
        failures.append(f"{label}: missing document_inventory_result")
        return
    if "whole_document_pass" in inv:
        failures.append(f"{label}: unqualified whole_document_pass is present")
    if inv.get("semantic_claim_universe_complete") is True:
        failures.append(f"{label}: semantic_claim_universe_complete is true")
    if inv.get("human_reference_inventory_established") is True:
        failures.append(f"{label}: human_reference_inventory_established is true")
    for key, wanted in inventory.items():
        if inv.get(key) != wanted:
            failures.append(
                f"{label}: inventory.{key}={inv.get(key)!r} expected={wanted!r}"
            )


def _run_v110_inventory_regressions(temporary: Path, failures: list[str]) -> int:
    """Self-contained 1.1.0 inventory cases. Synthetic temp files only."""
    counted = 0
    artifact = temporary / "v110-inventory.md"
    artifact.write_text(
        "# Synthetic inventory\n"
        "\n"
        "A source states a bounded synthetic observation.\n"
        "\n"
        "| Metric | Value |\n"
        "| --- | --- |\n"
        "| constructed_count | 7 |\n"
        "\n"
        "Table 1. Synthetic caption for the constructed_count table.\n"
        "\n"
        "![Unavailable figure](missing-synthetic-figure.png)\n"
        "\n"
        "Figure 1. Synthetic caption for an unavailable image-only figure.\n"
        "\n"
        "A second load-bearing observation constrains the boundary.\n",
        encoding="utf-8",
        newline="\n",
    )
    evidence = temporary / "v110-evidence.txt"
    evidence.write_text(
        "C-001: bounded observation.\n"
        "C-002: boundary constraint.\n"
        "C-TABLE: constructed_count is 7.\n"
        "C-CAPTION: table caption.\n"
        "C-FIGCAP: figure caption.\n"
        "C-FIGACC: accessible caption.\n",
        encoding="utf-8",
        newline="\n",
    )
    raw = artifact.read_bytes()
    claim_specs = [
        ("C-001", "A source states a bounded synthetic observation.", b"C-001:"),
        ("C-TABLE", "| constructed_count | 7 |", b"C-TABLE:"),
        ("C-CAPTION", "Table 1. Synthetic caption for the constructed_count table.", b"C-CAPTION:"),
        ("C-FIGCAP", "Figure 1. Synthetic caption for an unavailable image-only figure.", b"C-FIGCAP:"),
        ("C-002", "A second load-bearing observation constrains the boundary.", b"C-002:"),
    ]
    claims_by_id = {
        claim_id: _v110_claim(artifact, evidence, claim_id, text, marker)
        for claim_id, text, marker in claim_specs
    }

    def blocks_for(*, omit: set[str] | None = None, figure_coverage: str = "excluded") -> list[dict[str, Any]]:
        omit = omit or set()
        specs: list[dict[str, Any]] = [
            {
                "block_id": "B-HEAD",
                "kind": "heading",
                "text": "# Synthetic inventory",
                "coverage": "excluded",
                "reason": "ATX heading; locator metadata, not a proposition",
            },
            {
                "block_id": "B-SENT",
                "kind": "sentence",
                "text": "A source states a bounded synthetic observation.",
                "coverage": "in_scope",
                "claim_ids": ["C-001"],
            },
            {
                "block_id": "B-THDR",
                "kind": "other",
                "text": "| Metric | Value |",
                "coverage": "excluded",
                "reason": "table chrome",
            },
            {
                "block_id": "B-TSEP",
                "kind": "other",
                "text": "| --- | --- |",
                "coverage": "excluded",
                "reason": "table chrome",
            },
            {
                "block_id": "B-TABLE",
                "kind": "table",
                "text": "| constructed_count | 7 |",
                "coverage": "in_scope",
                "claim_ids": ["C-TABLE"],
            },
            {
                "block_id": "B-CAPTION",
                "kind": "caption",
                "text": "Table 1. Synthetic caption for the constructed_count table.",
                "coverage": "in_scope",
                "claim_ids": ["C-CAPTION"],
            },
            {
                "block_id": "B-FIG",
                "kind": "figure",
                "text": "![Unavailable figure](missing-synthetic-figure.png)",
                "coverage": figure_coverage,
                "reason": (
                    "image-only pixels are not in the markdown artifact; no OCR; unsupported assurance"
                    if figure_coverage == "inaccessible"
                    else "image markdown listed as nonclaim; pixels are outside the markdown artifact"
                ),
                "claim_ids": [],
            },
            {
                "block_id": "B-FIGCAP",
                "kind": "caption",
                "text": "Figure 1. Synthetic caption for an unavailable image-only figure.",
                "coverage": "in_scope",
                "claim_ids": ["C-FIGCAP"],
            },
            {
                "block_id": "B-SENT2",
                "kind": "sentence",
                "text": "A second load-bearing observation constrains the boundary.",
                "coverage": "in_scope",
                "claim_ids": ["C-002"],
            },
        ]
        built: list[dict[str, Any]] = []
        for spec in specs:
            if spec["block_id"] in omit:
                continue
            coverage = spec["coverage"]
            reason = spec.get("reason")
            claim_ids = list(spec.get("claim_ids") or [])
            if coverage != "in_scope":
                claim_ids = []
            else:
                reason = None
            built.append(
                _v110_block(
                    raw,
                    spec["block_id"],
                    spec["kind"],
                    spec["text"],
                    coverage,
                    claim_ids=claim_ids,
                    reason=reason,
                )
            )
        return built

    def claims_for(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        wanted: list[str] = []
        for block in blocks:
            wanted.extend(block.get("claim_ids") or [])
        return [copy.deepcopy(claims_by_id[claim_id]) for claim_id in wanted]

    def write_and_run(name: str, value: dict[str, Any]) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        path = temporary / f"{name}.json"
        _write_json(path, value)
        return _run_validator(artifact, path)

    accounted = {
        "full_artifact_bytes_accounted": True,
        "semantic_claim_universe_complete": False,
        "human_reference_inventory_established": False,
        "coverage_basis": "declared_byte_accounted_inventory_and_exclusions",
    }
    narrowed = {**accounted, "review_scope": "narrowed"}
    full_scope = {**accounted, "review_scope": "declared_full_artifact_bytes"}

    complete_blocks = blocks_for()
    complete = _v110_register(
        artifact,
        claims_for(complete_blocks),
        complete_blocks,
        register_id="SCR-V110-COMPLETE",
    )
    run, result = write_and_run("v110-complete", complete)
    _v110_expect(
        failures,
        "v110_complete_twin",
        run,
        result,
        exit_code=0,
        status="qualified",
        codes=set(),
        inventory=narrowed,
    )
    counted += 1

    omit_specs = [
        ("v110_omit_sentence", {"B-SENT"}, "SCR-COVERAGE-UNCOVERED-BYTES"),
        ("v110_omit_table", {"B-TABLE"}, "SCR-COVERAGE-UNCOVERED-BYTES"),
        ("v110_omit_caption", {"B-CAPTION"}, "SCR-COVERAGE-UNCOVERED-BYTES"),
        ("v110_omit_figure", {"B-FIG"}, "SCR-COVERAGE-UNCOVERED-BYTES"),
    ]
    for label, omit, code in omit_specs:
        omitted_blocks = blocks_for(omit=omit)
        omitted = _v110_register(
            artifact,
            claims_for(omitted_blocks),
            omitted_blocks,
            register_id=f"SCR-V110-{label.upper()}",
        )
        run, result = write_and_run(label, omitted)
        _v110_expect(
            failures,
            label,
            run,
            result,
            exit_code=2,
            status="refused",
            codes={code},
        )
        counted += 1

    run, result = write_and_run("v110-complete-restore", complete)
    _v110_expect(
        failures,
        "v110_omit_sentence_twin",
        run,
        result,
        exit_code=0,
        status="qualified",
        codes=set(),
        inventory=narrowed,
    )
    counted += 1

    dup = copy.deepcopy(complete)
    dup["register_id"] = "SCR-V110-DUP"
    dup["document_inventory"]["blocks"][3]["block_id"] = dup["document_inventory"]["blocks"][2]["block_id"]
    run, result = write_and_run("v110-duplicate", dup)
    _v110_expect(
        failures, "v110_duplicate_block_id", run, result,
        exit_code=2, status="refused", codes={"SCR-INVENTORY-DUPLICATE-ID"},
    )
    counted += 1

    stale = copy.deepcopy(complete)
    stale["register_id"] = "SCR-V110-STALE"
    stale["document_inventory"]["blocks"][1]["span_sha256"] = "0" * 64
    run, result = write_and_run("v110-stale", stale)
    _v110_expect(
        failures, "v110_stale_block_hash", run, result,
        exit_code=2, status="refused", codes={"SCR-INVENTORY-STALE"},
    )
    counted += 1

    overlap = copy.deepcopy(complete)
    overlap["register_id"] = "SCR-V110-OVERLAP"
    overlap["document_inventory"]["blocks"][2]["locator"] = copy.deepcopy(
        overlap["document_inventory"]["blocks"][1]["locator"]
    )
    overlap["document_inventory"]["blocks"][2]["span_sha256"] = overlap["document_inventory"]["blocks"][1]["span_sha256"]
    run, result = write_and_run("v110-overlap", overlap)
    _v110_expect(
        failures, "v110_overlap", run, result,
        exit_code=2, status="refused", codes={"SCR-INVENTORY-OVERLAP"},
    )
    counted += 1

    dangling = copy.deepcopy(complete)
    dangling["register_id"] = "SCR-V110-DANGLE"
    dangling["document_inventory"]["blocks"][1]["claim_ids"] = ["C-MISSING"]
    run, result = write_and_run("v110-dangling", dangling)
    _v110_expect(
        failures, "v110_dangling_claim", run, result,
        exit_code=2, status="refused", codes={"SCR-INVENTORY-CLAIM-REF"},
    )
    counted += 1

    oor = copy.deepcopy(complete)
    oor["register_id"] = "SCR-V110-OOR"
    oor["document_inventory"]["blocks"][4]["claim_ids"] = ["C-001"]
    run, result = write_and_run("v110-oor", oor)
    _v110_expect(
        failures, "v110_claim_out_of_range", run, result,
        exit_code=2, status="refused", codes={"SCR-INVENTORY-CLAIM-RANGE"},
    )
    counted += 1

    inac_blocks = blocks_for(figure_coverage="inaccessible")
    inac = _v110_register(
        artifact,
        claims_for(inac_blocks),
        inac_blocks,
        register_id="SCR-V110-INACC-COMPLETE",
    )
    run, result = write_and_run("v110-inacc-complete", inac)
    _v110_expect(
        failures, "v110_inaccessible_complete", run, result,
        exit_code=2, status="refused", codes={"SCR-COVERAGE-INACCESSIBLE"},
    )
    counted += 1

    inac_blocked = _v110_register(
        artifact,
        claims_for(inac_blocks),
        inac_blocks,
        register_id="SCR-V110-INACC-BLOCKED",
        disposition="blocked",
    )
    run, result = write_and_run("v110-inacc-blocked", inac_blocked)
    _v110_expect(
        failures, "v110_inaccessible_blocked", run, result,
        exit_code=0, status="blocked", codes=set(), inventory=narrowed,
    )
    counted += 1

    honest = _v110_register(
        artifact,
        claims_for(blocks_for(omit={"B-SENT"})),
        blocks_for(omit={"B-SENT"}),
        register_id="SCR-V110-INCOMPLETE-UNCOVERED",
        disposition="incomplete",
    )
    run, result = write_and_run("v110-incomplete-uncovered", honest)
    _v110_expect(
        failures,
        "v110_honest_incomplete_uncovered",
        run,
        result,
        exit_code=0,
        status="incomplete",
        codes=set(),
        inventory={
            "full_artifact_bytes_accounted": False,
            "semantic_claim_universe_complete": False,
            "coverage_basis": "declared_byte_accounted_inventory_and_exclusions",
        },
    )
    counted += 1

    no_deficit = copy.deepcopy(complete)
    no_deficit["register_id"] = "SCR-V110-INCOMPLETE-NO-DEFICIT"
    no_deficit["coverage_disposition"] = "incomplete"
    run, result = write_and_run("v110-incomplete-no-deficit", no_deficit)
    _v110_expect(
        failures, "v110_incomplete_no_deficit", run, result,
        exit_code=2, status="refused", codes={"SCR-COVERAGE-INCOMPLETE"},
    )
    counted += 1

    inac_incomplete = _v110_register(
        artifact,
        claims_for(inac_blocks),
        inac_blocks,
        register_id="SCR-V110-INACC-INCOMPLETE",
        disposition="incomplete",
    )
    run, result = write_and_run("v110-inacc-incomplete", inac_incomplete)
    _v110_expect(
        failures, "v110_inaccessible_incomplete_only", run, result,
        exit_code=2, status="refused", codes={"SCR-COVERAGE-INCOMPLETE"},
    )
    counted += 1

    stale_incomplete = copy.deepcopy(stale)
    stale_incomplete["register_id"] = "SCR-V110-STALE-INCOMPLETE"
    stale_incomplete["coverage_disposition"] = "incomplete"
    run, result = write_and_run("v110-stale-incomplete", stale_incomplete)
    _v110_expect(
        failures, "v110_incomplete_stale", run, result,
        exit_code=2, status="refused", codes={"SCR-INVENTORY-STALE"},
    )
    counted += 1

    overlap_incomplete = copy.deepcopy(overlap)
    overlap_incomplete["register_id"] = "SCR-V110-OVERLAP-INCOMPLETE"
    overlap_incomplete["coverage_disposition"] = "incomplete"
    run, result = write_and_run("v110-overlap-incomplete", overlap_incomplete)
    _v110_expect(
        failures, "v110_incomplete_overlap", run, result,
        exit_code=2, status="refused", codes={"SCR-INVENTORY-OVERLAP"},
    )
    counted += 1

    forbidden = copy.deepcopy(complete)
    forbidden["register_id"] = "SCR-V110-100-FORBIDS"
    forbidden["schema_version"] = "1.0.0"
    run, result = write_and_run("v110-100-forbids", forbidden)
    _v110_expect(
        failures, "v110_1_0_0_forbids_inventory", run, result,
        exit_code=2, status="refused", codes={"SCR-SCHEMA"},
    )
    counted += 1

    full_block = _v110_block(
        raw,
        "B-FULL",
        "paragraph",
        "# Synthetic inventory",
        "in_scope",
        claim_ids=["C-001"],
        start=0,
        end=len(raw),
    )
    full_claims = [copy.deepcopy(claims_by_id["C-001"])]
    full_complete = _v110_register(
        artifact,
        full_claims,
        [full_block],
        register_id="SCR-V110-FULLSPAN-COMPLETE",
    )
    run, result = write_and_run("v110-fullspan-complete", full_complete)
    _v110_expect(
        failures, "v110_fullspan_complete", run, result,
        exit_code=0, status="qualified", codes=set(), inventory=full_scope,
    )
    counted += 1

    full_blocked = _v110_register(
        artifact,
        full_claims,
        [full_block],
        register_id="SCR-V110-FULLSPAN-BLOCKED",
        disposition="blocked",
    )
    run, result = write_and_run("v110-fullspan-blocked", full_blocked)
    _v110_expect(
        failures, "v110_fullspan_blocked", run, result,
        exit_code=0, status="blocked", codes=set(), inventory=full_scope,
    )
    counted += 1

    accessible = temporary / "v110-accessible.md"
    accessible.write_text(
        "# Accessible figure\n"
        "\n"
        "![Described figure](synthetic-described.png)\n"
        "\n"
        "Figure 1. Seven constructed bars; the caption is the assurance surface.\n",
        encoding="utf-8",
        newline="\n",
    )
    acc_raw = accessible.read_bytes()
    acc_claim = _v110_claim(
        accessible,
        evidence,
        "C-FIGACC",
        "Figure 1. Seven constructed bars; the caption is the assurance surface.",
        b"C-FIGACC:",
    )
    acc_fig_text = (
        "![Described figure](synthetic-described.png)\n"
        "\n"
        "Figure 1. Seven constructed bars; the caption is the assurance surface."
    )
    acc_blocks = [
        _v110_block(
            acc_raw,
            "B-AHEAD",
            "heading",
            "# Accessible figure",
            "excluded",
            reason="ATX heading",
        ),
        _v110_block(
            acc_raw,
            "B-AFIG",
            "figure",
            acc_fig_text,
            "in_scope",
            claim_ids=["C-FIGACC"],
        ),
    ]
    acc_register = _v110_register(
        accessible,
        [acc_claim],
        acc_blocks,
        register_id="SCR-V110-ACCFIG",
    )
    acc_path = temporary / "v110-accessible.json"
    _write_json(acc_path, acc_register)
    acc_run, acc_result = _run_validator(accessible, acc_path)
    _v110_expect(
        failures, "v110_accessible_figure", acc_run, acc_result,
        exit_code=0, status="qualified", codes=set(), inventory=narrowed,
    )
    counted += 1

    rendered = claim_register.render_markdown(complete)
    required_ids = ["B-HEAD", "B-THDR", "B-TSEP", "B-FIG"]
    if "Declared document inventory" not in rendered:
        failures.append("v110_render_exclusions: missing inventory table")
    if "narrowed" not in rendered:
        failures.append("v110_render_exclusions: missing declared review_scope narrowed")
    if "whole_document_pass" in rendered:
        failures.append("v110_render_exclusions: contains whole_document_pass")
    for block_id in required_ids:
        lines_with_id = [line for line in rendered.splitlines() if block_id in line]
        if not any("excluded" in line for line in lines_with_id):
            failures.append(f"v110_render_exclusions: {block_id} not shown as excluded row")
    fig_lines = [line for line in rendered.splitlines() if "B-FIG" in line]
    if not any("image markdown" in line or "pixels" in line for line in fig_lines):
        failures.append("v110_render_exclusions: B-FIG reason not rendered")
    counted += 1

    rendered_inacc = claim_register.render_markdown(inac_blocked)
    inacc_lines = [line for line in rendered_inacc.splitlines() if "B-FIG" in line]
    if not any("inaccessible" in line for line in inacc_lines):
        failures.append("v110_render_inaccessible: B-FIG not shown as inaccessible row")
    if "whole_document_pass" in rendered_inacc:
        failures.append("v110_render_inaccessible: contains whole_document_pass")
    counted += 1

    legacy = _base_register(artifact, evidence)
    rendered_10 = claim_register.render_markdown(legacy)
    if "NON-AUTHORITATIVE VIEW" not in rendered_10:
        failures.append("v110_render_1_0_0: lost non-authoritative banner")
    if "Declared document inventory" in rendered_10:
        failures.append("v110_render_1_0_0: gained 1.1.0 inventory table")
    counted += 1

    complete_path = temporary / "v110-complete.json"
    render_run = subprocess.run(
        [sys.executable, str(SCRIPT), "--artifact", str(artifact), "--register", str(complete_path), "--render"],
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
        or "B-HEAD" not in render_run.stdout
        or "excluded" not in render_run.stdout
    ):
        failures.append("v110_render_cli: did not render declared exclusions")
    counted += 1

    return counted


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
    v110_cases = 0
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
            v110_cases = _run_v110_inventory_regressions(temporary, failures)

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
        f"skipped={optional_alias_skipped}; read-set API cases={api_cases}; "
        f"v1.1.0 inventory cases={v110_cases})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
