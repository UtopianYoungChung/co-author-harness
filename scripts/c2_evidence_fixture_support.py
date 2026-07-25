#!/usr/bin/env python3
"""Test-only builders for C2 future evidence carried through the legacy seam."""

from __future__ import annotations

import copy
import contextlib
import hashlib
import io
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from canonical_bibliography import publish_bibliography
from source_extract import main as source_extract_main


ROOT = Path(__file__).resolve().parent.parent
ASSET_ROOT = ROOT / "scripts" / "fixtures" / "assurance_provenance_c2"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def binding(path: Path) -> dict[str, str]:
    return {"path": str(path.resolve()), "sha256": sha(path)}


def _manifest_identity(manifest: Path) -> str:
    try:
        value = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AssertionError(f"fixture manifest is unreadable: {manifest}: {exc}") from exc
    if not isinstance(value, dict):
        raise AssertionError(f"fixture manifest must be an object: {manifest}")
    for key in ("identity", "manifest_id", "fixture_id", "name"):
        identity = value.get(key)
        if isinstance(identity, str) and identity.strip():
            return identity
    raise AssertionError(f"fixture manifest has no identity field: {manifest}")


def root_descriptor(
    *, kind: str, root: Path, manifest: Path
) -> dict[str, str]:
    return {
        "kind": kind,
        "identity": _manifest_identity(manifest),
        "discovery": (
            "explicit:"
            + manifest.resolve().relative_to(root.resolve()).as_posix()
        ),
        "manifest_sha256": sha(manifest),
    }


def portable_binding(
    path: Path,
    *,
    root: Path,
    kind: str,
    manifest: Path,
    evidence_type: str,
) -> dict[str, Any]:
    return {
        "root": root_descriptor(
            kind=kind, root=root, manifest=manifest
        ),
        "path": path.resolve().relative_to(root.resolve()).as_posix(),
        "sha256": sha(path),
        "evidence_type": evidence_type,
    }


def json_bytes(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json_bytes(value))


def payload_sha256(value: dict[str, Any]) -> str:
    payload = copy.deepcopy(value)
    payload.pop("publication", None)
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def utf8_span(value: str, needle: str) -> dict[str, int | str]:
    at = value.index(needle)
    end = at + len(needle)
    return {
        "start_utf8": len(value[:at].encode("utf-8")),
        "end_utf8": len(value[:end].encode("utf-8")),
        "text_sha256": hashlib.sha256(needle.encode("utf-8")).hexdigest(),
    }


@dataclass
class ActivationFixture:
    root: Path
    support_root: Path
    wiki_root: Path
    artifact: Path
    receipt: Path
    extract_receipt: Path
    bibliography_snapshot: Path
    page_span_map: Path
    project_manifest: Path
    fixture_manifest: Path
    extract_manifest: Path
    extract_marker: Path
    bibliography_manifest: Path
    bibliography_marker: Path
    base_receipt: dict[str, Any]
    base_extract_receipt: dict[str, Any]
    base_bibliography_snapshot: dict[str, Any]
    base_page_span_map: dict[str, Any]

    def _project_binding(self, path: Path, evidence_type: str) -> dict[str, Any]:
        return portable_binding(
            path,
            root=self.root,
            kind="project",
            manifest=self.project_manifest,
            evidence_type=evidence_type,
        )

    def asset_binding(self, path: Path, evidence_type: str) -> dict[str, Any]:
        return portable_binding(
            path,
            root=ASSET_ROOT,
            kind="package",
            manifest=self.fixture_manifest,
            evidence_type=evidence_type,
        )

    def wiki_binding(self, path: Path, evidence_type: str) -> dict[str, Any]:
        return portable_binding(
            path,
            root=self.wiki_root,
            kind="wiki",
            manifest=self.wiki_root / "manifest.json",
            evidence_type=evidence_type,
        )

    def _refresh_extract_publication(self, value: dict[str, Any]) -> None:
        payload_hash = payload_sha256(value)
        manifest = {
            "schema_version": "1.0.0",
            "transaction_id": "c2-extract-activation",
            "mode": "committed",
            "state": "prepared",
            "inputs": [
                copy.deepcopy(value["source"]),
                {"extraction": copy.deepcopy(value["extraction"])},
            ],
            "intended_outputs": [
                copy.deepcopy(value["raw_output"]),
                copy.deepcopy(value["normalized_output"]),
                copy.deepcopy(value["page_span_map"]),
                {
                    "path": self.extract_receipt.relative_to(self.root).as_posix(),
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
        write_json(self.extract_manifest, manifest)
        marker = {
            "schema_version": "1.0.0",
            "transaction_id": "c2-extract-activation",
            "mode": "committed",
            "state": "committed",
            "manifest": self._project_binding(
                self.extract_manifest, "publication_manifest"
            ),
            "final_output_hashes": [
                copy.deepcopy(value["raw_output"]),
                copy.deepcopy(value["normalized_output"]),
                copy.deepcopy(value["page_span_map"]),
                {
                    "path": self.extract_receipt.relative_to(self.root).as_posix(),
                    "payload_sha256": payload_hash,
                    "evidence_type": "canonical_extract_receipt_payload",
                },
            ],
        }
        marker_bytes = json_bytes(marker)
        value["publication"] = {
            "mode": "committed",
            "transaction_id": "c2-extract-activation",
            "manifest": self._project_binding(
                self.extract_manifest, "publication_manifest"
            ),
            "commit_marker": {
                "root": root_descriptor(
                    kind="project",
                    root=self.root,
                    manifest=self.project_manifest,
                ),
                "path": self.extract_marker.relative_to(self.root).as_posix(),
                "sha256": hashlib.sha256(marker_bytes).hexdigest(),
                "evidence_type": "publication_commit_marker",
            },
        }
        write_json(self.extract_receipt, value)
        self.extract_marker.write_bytes(marker_bytes)

    def _refresh_bibliography_publication(self, value: dict[str, Any]) -> None:
        payload_hash = payload_sha256(value)
        inputs: list[dict[str, Any]] = [copy.deepcopy(value["policy"])]
        for row in value.get("sources", []):
            if isinstance(row, dict):
                for key in ("canonical_page", "source"):
                    if isinstance(row.get(key), dict):
                        inputs.append(copy.deepcopy(row[key]))
        manifest = {
            "schema_version": "1.0.0",
            "transaction_id": "c2-bibliography-activation",
            "mode": "committed",
            "state": "prepared",
            "inputs": inputs,
            "intended_outputs": [{
                "path": self.bibliography_snapshot.relative_to(self.root).as_posix(),
                "payload_sha256": payload_hash,
                "evidence_type": "canonical_bibliography_snapshot_payload",
            }],
            "prior_state": {"publication": "absent"},
            "prospective_state": {
                "publication": "committed",
                "payload_sha256": payload_hash,
            },
        }
        write_json(self.bibliography_manifest, manifest)
        marker = {
            "schema_version": "1.0.0",
            "transaction_id": "c2-bibliography-activation",
            "mode": "committed",
            "state": "committed",
            "manifest": self._project_binding(
                self.bibliography_manifest, "publication_manifest"
            ),
            "final_output_hashes": [{
                "path": self.bibliography_snapshot.relative_to(self.root).as_posix(),
                "payload_sha256": payload_hash,
                "evidence_type": "canonical_bibliography_snapshot_payload",
            }],
        }
        marker_bytes = json_bytes(marker)
        value["publication"] = {
            "mode": "committed",
            "transaction_id": "c2-bibliography-activation",
            "manifest": self._project_binding(
                self.bibliography_manifest, "publication_manifest"
            ),
            "commit_marker": {
                "root": root_descriptor(
                    kind="project",
                    root=self.root,
                    manifest=self.project_manifest,
                ),
                "path": self.bibliography_marker.relative_to(self.root).as_posix(),
                "sha256": hashlib.sha256(marker_bytes).hexdigest(),
                "evidence_type": "publication_commit_marker",
            },
        }
        write_json(self.bibliography_snapshot, value)
        self.bibliography_marker.write_bytes(marker_bytes)

    def _rebind_external_objects(self) -> None:
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        extract_binding = self._project_binding(
            self.extract_receipt, "canonical_extract_receipt"
        )
        bibliography_binding = self._project_binding(
            self.bibliography_snapshot, "canonical_bibliography_snapshot"
        )
        receipt["canonical_extract_receipts"] = [extract_binding]
        receipt["canonical_bibliography_snapshot"] = bibliography_binding
        receipt["corpus_digest"] = sha(self.bibliography_snapshot)
        for passage in receipt["passages"]:
            passage["canonical_extract_receipt"] = copy.deepcopy(extract_binding)
        write_json(self.receipt, receipt)

    def reset(self) -> None:
        shutil.copyfile(ASSET_ROOT / "final.md", self.artifact)
        transaction_root = self.root / ".harness-evidence-transactions"
        if transaction_root.exists():
            shutil.rmtree(transaction_root)
        self.extract_marker.unlink(missing_ok=True)
        self.bibliography_marker.unlink(missing_ok=True)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
            io.StringIO()
        ):
            extract_rc = source_extract_main([
                "--source", str(self.root / "miniature.pdf"),
                "--text-out", str(self.support_root / "normalized.txt"),
                "--receipt-out", str(self.extract_receipt),
                "--project-root", str(self.root),
                "--project-manifest", str(self.project_manifest),
                "--source-key", "fixture-centroid-evidence",
                "--raw-out", str(self.support_root / "raw.txt"),
                "--page-map-out", str(self.page_span_map),
                "--page-map-seed", str(ASSET_ROOT / "expected_page_span_map.json"),
                "--manifest-out", str(self.extract_manifest),
                "--commit-marker-out", str(self.extract_marker),
            ])
        if extract_rc != 0:
            raise AssertionError(f"production source publisher failed: {extract_rc}")
        publish_bibliography(
            project_root=self.root,
            project_manifest=self.project_manifest,
            wiki_root=self.wiki_root,
            wiki_manifest=self.wiki_root / "manifest.json",
            policy=self.wiki_root / "policy.json",
            source_keys=[
                row["lookup_key"] for row in self.base_bibliography_snapshot["sources"]
            ],
            snapshot_id=self.base_bibliography_snapshot["snapshot_id"],
            out=self.bibliography_snapshot,
            manifest_out=self.bibliography_manifest,
            commit_marker_out=self.bibliography_marker,
        )
        write_json(self.receipt, copy.deepcopy(self.base_receipt))
        self._rebind_external_objects()

    def mutate_receipt(self, change: Callable[[dict[str, Any]], None]) -> None:
        value = json.loads(self.receipt.read_text(encoding="utf-8"))
        change(value)
        write_json(self.receipt, value)

    def mutate_artifact(self, change: Callable[[str], str]) -> None:
        value = change(self.artifact.read_text(encoding="utf-8"))
        self.artifact.write_text(value, encoding="utf-8", newline="\n")
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        receipt["artifact"] = self._project_binding(
            self.artifact, "governed_artifact"
        )
        for passage in receipt.get("passages", []):
            review = passage.get("evaluator_review") if isinstance(passage, dict) else None
            if isinstance(review, dict):
                review["artifact_sha256"] = sha(self.artifact)
        write_json(self.receipt, receipt)

    def mutate_extract(self, change: Callable[[dict[str, Any]], None]) -> None:
        value = json.loads(self.extract_receipt.read_text(encoding="utf-8"))
        change(value)
        self._refresh_extract_publication(value)
        self._rebind_external_objects()

    def remove_extract_commit_marker(self) -> None:
        value = json.loads(self.extract_receipt.read_text(encoding="utf-8"))
        value["publication"].pop("commit_marker")
        write_json(self.extract_receipt, value)
        self._rebind_external_objects()

    def mutate_bibliography(self, change: Callable[[dict[str, Any]], None]) -> None:
        value = json.loads(self.bibliography_snapshot.read_text(encoding="utf-8"))
        change(value)
        self._refresh_bibliography_publication(value)
        self._rebind_external_objects()

    def remove_bibliography_commit_marker(self) -> None:
        value = json.loads(self.bibliography_snapshot.read_text(encoding="utf-8"))
        value["publication"].pop("commit_marker")
        write_json(self.bibliography_snapshot, value)
        self._rebind_external_objects()

    def mutate_page_map(self, change: Callable[[dict[str, Any]], None]) -> None:
        value = json.loads(self.page_span_map.read_text(encoding="utf-8"))
        change(value)
        write_json(self.page_span_map, value)
        extract = json.loads(self.extract_receipt.read_text(encoding="utf-8"))
        extract["page_span_map"] = self._project_binding(
            self.page_span_map, "page_span_map"
        )
        self._refresh_extract_publication(extract)
        self._rebind_external_objects()

    def substitute_extract_objects(self) -> None:
        substitute_root = self.support_root / "coordinated-extract-substitution"
        substitute_root.mkdir(parents=True, exist_ok=True)
        copies = {
            "source": (ASSET_ROOT / "miniature.pdf", substitute_root / "miniature.pdf"),
            "raw_output": (
                ASSET_ROOT / "expected_pdftotext_raw.txt",
                substitute_root / "raw.txt",
            ),
            "normalized_output": (
                ASSET_ROOT / "expected_utf8_lf_v1.txt",
                substitute_root / "normalized.txt",
            ),
            "page_span_map": (
                ASSET_ROOT / "expected_page_span_map.json",
                substitute_root / "page-map.json",
            ),
        }
        for source, destination in copies.values():
            shutil.copyfile(source, destination)
        value = json.loads(self.extract_receipt.read_text(encoding="utf-8"))
        for key, (_source, destination) in copies.items():
            evidence_type = value[key]["evidence_type"]
            value[key] = self._project_binding(destination, evidence_type)
        self._refresh_extract_publication(value)
        self._rebind_external_objects()

    def substitute_bibliography_root(self) -> None:
        lookalike = self.support_root / "lookalike-wiki"
        page_root = lookalike / "wiki" / "sources"
        source_root = lookalike / "sources"
        page_root.mkdir(parents=True, exist_ok=True)
        source_root.mkdir(parents=True, exist_ok=True)
        for name in ("c2-centroid.md", "c2-argument.md", "c2-redirect.md"):
            shutil.copyfile(self.wiki_root / "wiki" / "sources" / name, page_root / name)
        shutil.copyfile(self.wiki_root / "policy.json", lookalike / "policy.json")
        shutil.copyfile(ASSET_ROOT / "miniature.pdf", source_root / "miniature.pdf")
        lookalike_manifest = lookalike / "manifest.json"
        write_json(lookalike_manifest, {
            "schema_version": "1.0.0",
            "manifest_id": "c2-lookalike-wiki",
            "authority": "synthetic_nonqualifying",
            "source_pages": [
                "wiki/sources/c2-centroid.md",
                "wiki/sources/c2-argument.md",
                "wiki/sources/c2-redirect.md",
            ],
        })

        def lookalike_binding(path: Path, evidence_type: str) -> dict[str, Any]:
            return portable_binding(
                path,
                root=lookalike,
                kind="wiki",
                manifest=lookalike_manifest,
                evidence_type=evidence_type,
            )

        value = json.loads(self.bibliography_snapshot.read_text(encoding="utf-8"))
        value["wiki_root"] = root_descriptor(
            kind="wiki",
            root=lookalike,
            manifest=lookalike_manifest,
        )
        value["policy"] = lookalike_binding(
            lookalike / "policy.json", "bibliography_policy"
        )
        for row in value["sources"]:
            page_name = (
                "c2-centroid.md"
                if row["source_key"] == "fixture-centroid-evidence"
                else "c2-argument.md"
            )
            row["canonical_page"] = lookalike_binding(
                page_root / page_name, "canonical_source_page"
            )
            row["source_loc"] = "sources/miniature.pdf"
            row["source"] = lookalike_binding(
                source_root / "miniature.pdf", "source_pdf"
            )
        self._refresh_bibliography_publication(value)
        self._rebind_external_objects()


def build_activation_fixture(
    root: Path,
    *,
    artifact_relative: str = "final.md",
    evidence_relative: str | None = None,
) -> ActivationFixture:
    static_artifact = ASSET_ROOT / "final.md"
    static_pdf = ASSET_ROOT / "miniature.pdf"
    static_raw = ASSET_ROOT / "expected_pdftotext_raw.txt"
    static_extract = ASSET_ROOT / "expected_utf8_lf_v1.txt"
    static_page_map = ASSET_ROOT / "expected_page_span_map.json"
    wiki_root = ASSET_ROOT / "wiki"
    wiki_manifest = wiki_root / "manifest.json"
    wiki_policy = wiki_root / "policy.json"
    centroid_page = wiki_root / "wiki" / "sources" / "c2-centroid.md"
    argument_page = wiki_root / "wiki" / "sources" / "c2-argument.md"
    fixture_manifest = ASSET_ROOT / "hashes.json"
    for path in (
        static_artifact,
        static_pdf,
        static_raw,
        static_extract,
        static_page_map,
        wiki_manifest,
        wiki_policy,
        centroid_page,
        argument_page,
        fixture_manifest,
    ):
        if not path.is_file():
            raise AssertionError(f"C2 fixture asset is missing: {path}")

    relative_artifact = Path(artifact_relative)
    if (
        relative_artifact.is_absolute()
        or "\\" in artifact_relative
        or any(part in {"", ".", ".."} for part in relative_artifact.parts)
    ):
        raise AssertionError(f"unsafe synthetic artifact path: {artifact_relative!r}")
    root.mkdir(parents=True, exist_ok=True)
    if evidence_relative is None:
        support_root = root
    else:
        relative_evidence = Path(evidence_relative)
        if (
            relative_evidence.is_absolute()
            or "\\" in evidence_relative
            or any(part in {"", ".", ".."} for part in relative_evidence.parts)
        ):
            raise AssertionError(
                f"unsafe synthetic evidence path: {evidence_relative!r}"
            )
        support_root = root / relative_evidence
        support_root.mkdir(parents=True, exist_ok=True)
    artifact = root / relative_artifact
    artifact.parent.mkdir(parents=True, exist_ok=True)
    # The frozen wiki metadata names ``miniature.pdf`` at the project root.
    # Namespaced fixtures may share these immutable source bytes while all
    # mutable publications remain isolated below ``support_root``.
    pdf = root / "miniature.pdf"
    raw = support_root / "raw.txt"
    extract = support_root / "normalized.txt"
    runtime_page_map = support_root / "page-span-map.json"
    for source, destination in (
        (static_artifact, artifact),
        (static_pdf, pdf),
        (static_raw, raw),
        (static_extract, extract),
        (static_page_map, runtime_page_map),
    ):
        shutil.copyfile(source, destination)

    project_manifest = support_root / "synthetic-project-manifest.json"
    write_json(project_manifest, {
        "schema_version": "synthetic-nonqualifying-1.0.0",
        "fixture_id": "assurance-provenance-c2-activation",
        "identity": "c2-synthetic-project",
        "admitted_sources": [{
            "path": pdf.relative_to(root).as_posix(),
            "sha256": sha(pdf),
        }],
        "governed_artifacts": [{
            "path": relative_artifact.as_posix(),
            "sha256": sha(artifact),
        }],
    })

    def asset_binding(path: Path, evidence_type: str) -> dict[str, Any]:
        return portable_binding(
            path,
            root=ASSET_ROOT,
            kind="package",
            manifest=fixture_manifest,
            evidence_type=evidence_type,
        )

    def project_binding(path: Path, evidence_type: str) -> dict[str, Any]:
        return portable_binding(
            path,
            root=root,
            kind="project",
            manifest=project_manifest,
            evidence_type=evidence_type,
        )

    def wiki_binding(path: Path, evidence_type: str) -> dict[str, Any]:
        return portable_binding(
            path,
            root=wiki_root,
            kind="wiki",
            manifest=wiki_manifest,
            evidence_type=evidence_type,
        )

    packet = support_root / "synthetic-centroid-packet.json"
    write_json(packet, {
        "schema_version": "1.0.0",
        "status": "synthetic_nonqualifying",
        "members": [
            {"source_key": "fixture-centroid-evidence", "role": "centroid"},
            {"source_key": "fixture-argument-evidence", "role": "argument"},
        ],
    })

    extract_manifest = support_root / "synthetic-extract-publication-manifest.json"
    extract_marker = support_root / "synthetic-extract-publication-marker.json"

    base_page_map = json.loads(static_page_map.read_text(encoding="utf-8"))
    write_json(runtime_page_map, base_page_map)

    extract_receipt = support_root / "canonical-extract-2.json"
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
        io.StringIO()
    ):
        extract_rc = source_extract_main([
            "--source", str(pdf),
            "--text-out", str(extract),
            "--receipt-out", str(extract_receipt),
            "--project-root", str(root),
            "--project-manifest", str(project_manifest),
            "--source-key", "fixture-centroid-evidence",
            "--raw-out", str(raw),
            "--page-map-out", str(runtime_page_map),
            "--page-map-seed", str(static_page_map),
            "--manifest-out", str(extract_manifest),
            "--commit-marker-out", str(extract_marker),
        ])
    if extract_rc != 0:
        raise AssertionError(f"production source publisher failed: {extract_rc}")
    base_extract = json.loads(extract_receipt.read_text(encoding="utf-8"))

    bibliography_manifest = support_root / "synthetic-bibliography-publication-manifest.json"
    bibliography_marker = support_root / "synthetic-bibliography-publication-marker.json"

    bibliography = support_root / "canonical-bibliography-1.json"
    base_bibliography = publish_bibliography(
        project_root=root,
        project_manifest=project_manifest,
        wiki_root=wiki_root,
        wiki_manifest=wiki_manifest,
        policy=wiki_policy,
        source_keys=["fixture-centroid-alias", "fixture-argument-evidence"],
        snapshot_id="c2-bibliography-activation",
        out=bibliography,
        manifest_out=bibliography_manifest,
        commit_marker_out=bibliography_marker,
    )

    locator_map = json.loads(static_page_map.read_text(encoding="utf-8"))
    centroid_quote = "replayable evidence must bind exact"
    argument_quote = "rationale records why a member is included or omitted"
    argument_manuscript_text = (
        "relevant members need an explicit account of their inclusion or omission"
    )
    centroid_locator = locator_map["named_spans"]["centroid_quote"][0]
    argument_locator = locator_map["named_spans"]["argument_quote"][0]
    artifact_text = artifact.read_text(encoding="utf-8")
    centroid_manuscript_span = utf8_span(artifact_text, centroid_quote)
    argument_manuscript_span = utf8_span(artifact_text, argument_manuscript_text)
    influence_statement = "The source bounded the rationale claim."
    # This compatibility duplicate deliberately carries only the true direct
    # quotation.  The future conditioning passage is not relabelled as a quote
    # merely to satisfy the legacy diagnostic kernel.
    legacy_passages = [{
        "source_key": "fixture-centroid-evidence",
        "use_scope": "surface",
        "source": binding(pdf),
        "locator": "p. 1",
        "extract": binding(extract),
        "extraction": {
            "method": "pdftotext",
            "tool": "pdftotext",
            "canonical": True,
        },
        "quote": centroid_quote,
        "citation": {
            "authors": ["Fixture, C."],
            "year": 2026,
            "title": "Fixture centroid evidence",
            "label": "2026",
        },
        "use": "Non-authoritative diagnostic compatibility quotation.",
    }]
    base_receipt = {
        "schema_version": "3.0.0",
        "receipt_type": "centroid_semantic_execution",
        "authority_mode": "legacy_compatibility",
        "target": "FINAL",
        "phase": "generation",
        "role": "generator",
        "artifact": project_binding(artifact, "governed_artifact"),
        "centroid_packet": project_binding(packet, "centroid_packet"),
        "policy": wiki_binding(wiki_policy, "draft_policy"),
        "corpus_digest": sha(bibliography),
        "canonical_extract_receipts": [project_binding(
            extract_receipt, "canonical_extract_receipt"
        )],
        "canonical_bibliography_snapshot": project_binding(
            bibliography, "canonical_bibliography_snapshot"
        ),
        "passages": [
            {
                "source_key": "fixture-centroid-evidence",
                "use_scope": "surface",
                "passage_use": "direct_quotation",
                "canonical_extract_receipt": project_binding(
                    extract_receipt, "canonical_extract_receipt"
                ),
                "locator": {
                    "page_start": 1,
                    "page_end": 1,
                    "normalized_start_utf8": centroid_locator["start_utf8"],
                    "normalized_end_utf8": centroid_locator["end_utf8"],
                    "occurrence": centroid_locator["occurrence"],
                    "text_sha256": centroid_locator["text_sha256"],
                },
                "manuscript_span": centroid_manuscript_span,
                "direct_quotation": {"text": centroid_quote},
                "citation": {
                    "source_key": "fixture-centroid-evidence",
                    "authors": ["Fixture, C."],
                    "year": 2026,
                    "title": "Fixture centroid evidence",
                    "label": "2026",
                },
            },
            {
                "source_key": "fixture-centroid-evidence",
                "use_scope": "argument",
                "passage_use": "conditioning_passage",
                "canonical_extract_receipt": project_binding(
                    extract_receipt, "canonical_extract_receipt"
                ),
                "locator": {
                    "page_start": 2,
                    "page_end": 2,
                    "normalized_start_utf8": argument_locator["start_utf8"],
                    "normalized_end_utf8": argument_locator["end_utf8"],
                    "occurrence": argument_locator["occurrence"],
                    "text_sha256": argument_locator["text_sha256"],
                },
                "manuscript_span": argument_manuscript_span,
                "influence_statement": influence_statement,
                "evaluator_review": {
                    "schema_version": "1.0.0",
                    "review_type": "conditioning_influence_review",
                    "reviewer_role": "evaluator",
                    "disposition": "accepted",
                    "influence_statement_sha256": hashlib.sha256(
                        influence_statement.encode("utf-8")
                    ).hexdigest(),
                    "source_passage_sha256": argument_locator["text_sha256"],
                    "manuscript_span_sha256": argument_manuscript_span[
                        "text_sha256"
                    ],
                    "artifact_sha256": sha(artifact),
                },
                "citation": {
                    "source_key": "fixture-centroid-evidence",
                    "authors": ["Fixture, C."],
                    "year": 2026,
                    "title": "Fixture centroid evidence",
                    "label": "2026",
                },
            },
        ],
        "member_coverage": [
            {
                "source_key": "fixture-centroid-evidence",
                "member_role": "centroid",
                "disposition": "included",
                "rationale": "Supplies the FINAL surface passage.",
            },
            {
                "source_key": "fixture-argument-evidence",
                "member_role": "argument",
                "disposition": "omitted",
                "rationale": "Not needed for the bounded fixture claim.",
            },
        ],
        "semantic_assessment": {
            "summary": "Synthetic compatibility assertion only.",
            "strengths": [],
            "deviations": [],
            "warrant_limits": ["No genuine semantic judgment is claimed."],
            "actionable_findings": [],
        },
        "diagnostic_legacy_view": {"passages": legacy_passages},
    }
    receipt = support_root / "semantic-execution-3.json"
    fixture = ActivationFixture(
        root=root,
        support_root=support_root,
        wiki_root=wiki_root,
        artifact=artifact,
        receipt=receipt,
        extract_receipt=extract_receipt,
        bibliography_snapshot=bibliography,
        page_span_map=runtime_page_map,
        project_manifest=project_manifest,
        fixture_manifest=fixture_manifest,
        extract_manifest=extract_manifest,
        extract_marker=extract_marker,
        bibliography_manifest=bibliography_manifest,
        bibliography_marker=bibliography_marker,
        base_receipt=base_receipt,
        base_extract_receipt=base_extract,
        base_bibliography_snapshot=base_bibliography,
        base_page_span_map=base_page_map,
    )
    if evidence_relative is None:
        fixture.reset()
    else:
        write_json(fixture.receipt, copy.deepcopy(fixture.base_receipt))
        fixture._rebind_external_objects()
    return fixture
