#!/usr/bin/env python3
"""Create canonical, hash-bound text extraction evidence for one source."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from c2_evidence_validation import (
    EXTRACTOR_NAMES,
    EXTRACTOR_QUALIFICATION,
    SUPPORTED_EXTRACTOR,
    canonical_bytes,
    payload_sha256,
    validate_page_map,
)
from destination_capability import DestinationRefused, assert_writable
from evidence_publication import EvidencePublicationError, publish_committed


# The reference extractor: Poppler pdftotext 24.04.0 as first qualified.
SUPPORTED_PDF_EXTRACTOR = dict(SUPPORTED_EXTRACTOR)
CONFORMANCE_PDF = (
    Path(__file__).resolve().parent / "fixtures" / "assurance_provenance_c2" / "miniature.pdf"
)
_VERSION_RE = re.compile(r"pdftotext version (\S+)", re.IGNORECASE)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _block(code: str, detail: str) -> int:
    print(
        json.dumps({
            "schema_version": "1.0.0",
            "report_type": "source_extract_blocker",
            "status": "blocked",
            "reason_code": code,
            "detail": detail,
        }, sort_keys=True, separators=(",", ":")),
        file=sys.stderr,
    )
    return 4


def _extractor_candidates() -> list[Path]:
    candidates: list[Path] = []
    seen: set[str] = set()
    for entry in os.get_exec_path():
        path_entry = entry.strip().strip('"')
        if not path_entry:
            continue
        for name in sorted(EXTRACTOR_NAMES):
            candidate_value = shutil.which(name, path=path_entry)
            if candidate_value is None:
                continue
            candidate = Path(candidate_value)
            if candidate.name.casefold() not in EXTRACTOR_NAMES:
                continue
            identity = str(candidate.resolve()).casefold()
            if identity not in seen:
                seen.add(identity)
                candidates.append(candidate)
    return candidates


def _reported_version(candidate: Path) -> str | None:
    try:
        result = subprocess.run(
            [str(candidate), "-v"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    match = _VERSION_RE.search(result.stdout + result.stderr)
    return match.group(1) if match else None


def _conforms(candidate: Path) -> bool:
    """True when the candidate reproduces the committed conformance fixture."""
    try:
        if sha(CONFORMANCE_PDF) != EXTRACTOR_QUALIFICATION["fixture_sha256"]:
            return False
    except OSError:
        return False
    with tempfile.TemporaryDirectory(prefix="coauthor-extractor-conformance-") as td:
        out = Path(td) / "raw.txt"
        try:
            result = subprocess.run(
                [str(candidate), "-enc", "UTF-8", str(CONFORMANCE_PDF), str(out)],
                capture_output=True,
                timeout=60,
            )
            raw = out.read_bytes() if result.returncode == 0 and out.is_file() else None
        except (OSError, subprocess.SubprocessError):
            return False
    if raw is None:
        return False
    try:
        normalized = raw.decode("utf-8", errors="strict").replace("\r\n", "\n").replace("\r", "\n")
    except UnicodeError:
        return False
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return digest == EXTRACTOR_QUALIFICATION["normalized_sha256"]


def resolve_pdf_extractor() -> tuple[Path | None, dict | None, str | None]:
    """Return (tool, receipt identity, error code).

    The reference extractor is preferred wherever it sits on PATH, so an
    earlier shadow binary cannot displace it. Any other pdftotext is admitted
    only when it reproduces the committed conformance fixture; its identity is
    then its own bytes plus that qualification, never the reference's.
    """
    candidates = _extractor_candidates()
    if not candidates:
        return None, None, "EXTRACTOR-UNAVAILABLE"

    reference_bytes_seen = False
    for candidate in candidates:
        try:
            identity_matches = (
                candidate.name.casefold() == SUPPORTED_PDF_EXTRACTOR["name"].casefold()
                and candidate.stat().st_size == SUPPORTED_PDF_EXTRACTOR["size"]
                and sha(candidate) == SUPPORTED_PDF_EXTRACTOR["sha256"]
            )
        except OSError:
            continue
        if not identity_matches:
            continue
        reference_bytes_seen = True
        if _reported_version(candidate) == SUPPORTED_PDF_EXTRACTOR["version"]:
            return candidate, copy.deepcopy(SUPPORTED_PDF_EXTRACTOR), None

    for candidate in candidates:
        version = _reported_version(candidate)
        if version is None or not _conforms(candidate):
            continue
        try:
            identity = {
                "name": candidate.name,
                "version": version,
                "sha256": sha(candidate),
                "size": candidate.stat().st_size,
                "qualification": copy.deepcopy(EXTRACTOR_QUALIFICATION),
            }
        except OSError:
            continue
        return candidate, identity, None

    if reference_bytes_seen:
        return None, None, "EXTRACTOR-UNSUPPORTED"
    return None, None, "EXTRACTOR-IDENTITY-MISMATCH"


def qualified_pdf_extractor() -> tuple[Path | None, str | None]:
    """Resolve the reference or a fixture-qualified extractor (see resolve_pdf_extractor)."""
    tool, _identity, error = resolve_pdf_extractor()
    return tool, error


def _project_binding(
    path: Path,
    *,
    project_root: Path,
    project_manifest: Path,
    identity: str,
    evidence_type: str,
    digest: str | None = None,
) -> dict:
    return {
        "root": {
            "kind": "project",
            "identity": identity,
            "discovery": (
                "explicit:"
                + project_manifest.relative_to(project_root).as_posix()
            ),
            "manifest_sha256": sha(project_manifest),
        },
        "path": path.relative_to(project_root).as_posix(),
        "sha256": digest if digest is not None else sha(path),
        "evidence_type": evidence_type,
    }


def _page_map(raw: bytes, normalized: str) -> dict:
    parts = normalized.split("\f")
    if parts and not parts[-1]:
        parts.pop()
    pages: list[dict] = []
    cursor = 0
    for number, page_text in enumerate(parts, 1):
        start = normalized.find(page_text, cursor)
        end = start + len(page_text)
        pages.append({
            "page": number,
            "normalized_start_utf8": len(normalized[:start].encode("utf-8")),
            "normalized_end_utf8": len(normalized[:end].encode("utf-8")),
            "text_sha256": hashlib.sha256(page_text.encode("utf-8")).hexdigest(),
        })
        cursor = end + 1
    return {
        "schema_version": "1.0.0",
        "normalization_version": "utf8-lf-v1",
        "offset_unit": "zero-based-end-exclusive-utf8-byte",
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "normalized_sha256": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
        "pages": pages,
        "named_spans": {},
    }


def _future_pdf_extract(
    args: argparse.Namespace, source: Path, tool: Path, extractor_identity: dict
) -> int:
    required = {
        "project_root": args.project_root,
        "project_manifest": args.project_manifest,
        "source_key": args.source_key,
        "raw_out": args.raw_out,
        "page_map_out": args.page_map_out,
        "manifest_out": args.manifest_out,
        "commit_marker_out": args.commit_marker_out,
    }
    missing = [key for key, value in required.items() if value is None]
    if missing:
        return _block(
            "EVIDENCE-SCHEMA-INVALID",
            "future extraction requires: " + ", ".join(sorted(missing)),
        )
    project_root = args.project_root.resolve(strict=True)
    project_manifest = args.project_manifest.resolve(strict=True)
    source_digest = sha(source)
    project_manifest_digest = sha(project_manifest)
    page_map_seed_digest: str | None = None
    try:
        manifest_value = json.loads(project_manifest.read_text(encoding="utf-8"))
        identity = manifest_value["identity"]
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        return _block("EXTRACT-BINDING-STALE", f"project manifest is invalid: {exc}")
    outputs = [
        args.text_out,
        args.receipt_out,
        args.raw_out,
        args.page_map_out,
        args.manifest_out,
        args.commit_marker_out,
    ]
    resolved_outputs: list[Path] = []
    for output in outputs:
        resolved = output.resolve()
        if not resolved.is_relative_to(project_root):
            return _block("EXTRACT-PATH-ESCAPE", f"output escapes project root: {output}")
        resolved_outputs.append(resolved)
    text_out, receipt_out, raw_out, page_map_out, manifest_out, marker_out = resolved_outputs
    if not source.is_relative_to(project_root):
        return _block("EXTRACT-PATH-ESCAPE", "source escapes project root")
    with tempfile.TemporaryDirectory(prefix="coauthor-extract-staged-") as td:
        staged_root = Path(td)
        prepared_raw = staged_root / "raw.txt"
        result = subprocess.run(
            [str(tool), "-enc", "UTF-8", str(source), str(prepared_raw)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0 or not prepared_raw.is_file():
            return _block("EXTRACTOR-FAILED", result.stderr.strip())
        raw_bytes = prepared_raw.read_bytes()
        try:
            raw_text = raw_bytes.decode("utf-8", errors="strict")
        except UnicodeError as exc:
            return _block("EXTRACTOR-FAILED", f"extract is not UTF-8: {exc}")
        normalized = raw_text.replace("\r\n", "\n").replace("\r", "\n")
        prepared_text = staged_root / "normalized.txt"
        prepared_text.write_text(normalized, encoding="utf-8", newline="\n")
        if args.page_map_seed is not None:
            try:
                page_map_seed_bytes = args.page_map_seed.read_bytes()
                page_map_value = json.loads(
                    page_map_seed_bytes.decode("utf-8", errors="strict")
                )
                page_map_seed_digest = hashlib.sha256(page_map_seed_bytes).hexdigest()
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                return _block("EXTRACT-LOCATOR-MISMATCH", f"page-map seed is invalid: {exc}")
        else:
            page_map_value = _page_map(raw_bytes, normalized)
        prepared_map = staged_root / "page-map.json"
        prepared_map.write_bytes(canonical_bytes(page_map_value))
        try:
            validate_page_map(
                page_map_value, raw=prepared_raw, normalized=prepared_text
            )
        except Exception as exc:
            return _block("EXTRACT-LOCATOR-MISMATCH", str(exc))
    source_binding = _project_binding(
        source,
        project_root=project_root,
        project_manifest=project_manifest,
        identity=identity,
        evidence_type="source_pdf",
        digest=source_digest,
    )
    raw_binding = _project_binding(
        raw_out,
        project_root=project_root,
        project_manifest=project_manifest,
        identity=identity,
        evidence_type="raw_extract",
        digest=hashlib.sha256(raw_bytes).hexdigest(),
    )
    normalized_binding = _project_binding(
        text_out,
        project_root=project_root,
        project_manifest=project_manifest,
        identity=identity,
        evidence_type="normalized_extract",
        digest=hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
    )
    map_binding = _project_binding(
        page_map_out,
        project_root=project_root,
        project_manifest=project_manifest,
        identity=identity,
        evidence_type="page_span_map",
        digest=hashlib.sha256(canonical_bytes(page_map_value)).hexdigest(),
    )
    receipt = {
        "schema_version": "2.0.0",
        "receipt_type": "canonical_extract_receipt",
        "source_key": args.source_key,
        "source": source_binding,
        "raw_output": raw_binding,
        "normalized_output": normalized_binding,
        "page_span_map": map_binding,
        "extraction": {
            "adapter": "poppler-pdftotext",
            "executable": copy.deepcopy(extractor_identity),
            "argv": ["-enc", "UTF-8"],
            "layout_mode": "logical-default-v1",
            "normalization_version": "utf8-lf-v1",
        },
    }
    transaction_id = "extract-" + hashlib.sha256(canonical_bytes({
        "source_sha256": source_digest,
        "outputs": [
            path.relative_to(project_root).as_posix()
            for path in (raw_out, text_out, page_map_out, manifest_out, receipt_out, marker_out)
        ],
    })).hexdigest()[:16]
    payload_hash = payload_sha256(receipt)
    transaction_manifest = {
        "schema_version": "1.0.0",
        "transaction_id": transaction_id,
        "mode": "committed",
        "state": "prepared",
        "inputs": [source_binding, {"extraction": receipt["extraction"]}],
        "intended_outputs": [
            raw_binding,
            normalized_binding,
            map_binding,
            {
                "path": receipt_out.relative_to(project_root).as_posix(),
                "payload_sha256": payload_hash,
                "evidence_type": "canonical_extract_receipt_payload",
            },
        ],
        "prior_state": {"publication": "absent"},
        "prospective_state": {
            "publication": "committed",
            "payload_sha256": payload_hash,
        },
    }
    manifest_bytes = canonical_bytes(transaction_manifest)
    manifest_binding = _project_binding(
        manifest_out,
        project_root=project_root,
        project_manifest=project_manifest,
        identity=identity,
        evidence_type="publication_manifest",
        digest=hashlib.sha256(manifest_bytes).hexdigest(),
    )
    marker = {
        "schema_version": "1.0.0",
        "transaction_id": transaction_id,
        "mode": "committed",
        "state": "committed",
        "manifest": manifest_binding,
        "final_output_hashes": transaction_manifest["intended_outputs"],
    }
    marker_bytes = canonical_bytes(marker)
    marker_binding = {
        "root": copy.deepcopy(manifest_binding["root"]),
        "path": marker_out.relative_to(project_root).as_posix(),
        "sha256": hashlib.sha256(marker_bytes).hexdigest(),
        "evidence_type": "publication_commit_marker",
    }
    receipt["publication"] = {
        "mode": "committed",
        "transaction_id": transaction_id,
        "manifest": manifest_binding,
        "commit_marker": marker_binding,
    }
    try:
        preconditions = [
            (source, source_digest),
            (project_manifest, project_manifest_digest),
            (tool, extractor_identity["sha256"]),
        ]
        if args.page_map_seed is not None:
            assert page_map_seed_digest is not None
            preconditions.append((args.page_map_seed, page_map_seed_digest))
        publish_committed(
            project_root=project_root,
            transaction_id=transaction_id,
            preconditions=preconditions,
            inventory_preconditions=[],
            outputs=[
                (raw_out, raw_bytes),
                (text_out, normalized.encode("utf-8")),
                (page_map_out, canonical_bytes(page_map_value)),
                (manifest_out, manifest_bytes),
                (receipt_out, canonical_bytes(receipt)),
            ],
            marker=(marker_out, marker_bytes),
        )
    except EvidencePublicationError as exc:
        return _block("EXTRACT-RECEIPT-INVALID", str(exc))
    print(canonical_bytes(receipt).decode("utf-8", errors="strict").rstrip("\n"))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--text-out", type=Path, required=True)
    parser.add_argument("--receipt-out", type=Path, required=True)
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--project-manifest", type=Path)
    parser.add_argument("--source-key")
    parser.add_argument("--raw-out", type=Path)
    parser.add_argument("--page-map-out", type=Path)
    parser.add_argument("--page-map-seed", type=Path)
    parser.add_argument("--manifest-out", type=Path)
    parser.add_argument("--commit-marker-out", type=Path)
    args = parser.parse_args(argv)
    try:
        for output in (
            args.text_out,
            args.receipt_out,
            args.raw_out,
            args.page_map_out,
            args.manifest_out,
            args.commit_marker_out,
        ):
            if output is not None:
                assert_writable(output.resolve(), purpose="source extraction publication")
    except DestinationRefused as exc:
        print(f"[BLOCKER] {exc}", file=sys.stderr)
        return 4
    source = args.source.resolve(strict=True)
    if source.suffix.casefold() == ".pdf":
        tool_path, tool_identity, resolution_error = resolve_pdf_extractor()
        if resolution_error == "EXTRACTOR-UNAVAILABLE":
            return _block(
                "EXTRACTOR-UNAVAILABLE",
                "pdftotext is required for PDF evidence",
            )
        if resolution_error == "EXTRACTOR-UNSUPPORTED":
            return _block(
                "EXTRACTOR-UNSUPPORTED",
                "pdftotext version is not qualified",
            )
        if resolution_error == "EXTRACTOR-IDENTITY-MISMATCH":
            return _block(
                "EXTRACTOR-IDENTITY-MISMATCH",
                "no pdftotext on PATH is the reference build or reproduces the "
                "committed conformance fixture",
            )
        assert tool_path is not None
        if args.project_root is not None:
            assert tool_identity is not None
            return _future_pdf_extract(args, source, tool_path, tool_identity)
        args.text_out.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [str(tool_path), "-enc", "UTF-8", str(source), str(args.text_out)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0 or not args.text_out.is_file():
            print(f"[BLOCKER] EXTRACTOR-FAILED: {result.stderr.strip()}", file=sys.stderr)
            return 4
        method = "pdftotext"; tool_name = tool_path.name
    else:
        try:
            text = source.read_text(encoding="utf-8", errors="strict")
        except (OSError, UnicodeError) as exc:
            print(f"[BLOCKER] EXTRACTOR-FAILED: {exc}", file=sys.stderr)
            return 4
        args.text_out.parent.mkdir(parents=True, exist_ok=True)
        args.text_out.write_text(text, encoding="utf-8", newline="\n")
        method = "text-direct"; tool_name = "utf-8"
    receipt = {
        "schema_version": "1.0.0", "receipt_type": "canonical_source_extract",
        "source": {"path": str(source), "sha256": sha(source)},
        "extract": {"path": str(args.text_out.resolve()), "sha256": sha(args.text_out)},
        "extraction": {"method": method, "tool": tool_name, "canonical": True},
    }
    args.receipt_out.parent.mkdir(parents=True, exist_ok=True)
    args.receipt_out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
