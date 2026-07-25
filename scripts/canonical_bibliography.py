#!/usr/bin/env python3
"""Publish a committed bibliography snapshot from governed Wiki source pages."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path, PurePosixPath
from typing import Any

from c2_evidence_validation import (
    canonical_bytes,
    payload_sha256,
    resolve_wiki_source,
    sha256,
    wiki_source_index,
)
from destination_capability import DestinationRefused, assert_writable
from evidence_publication import EvidencePublicationError, publish_committed


class BibliographyPublishError(RuntimeError):
    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


def _block(code: str, detail: str) -> int:
    print(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "report_type": "canonical_bibliography_blocker",
                "status": "blocked",
                "reason_code": code,
                "detail": detail,
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
        file=sys.stderr,
    )
    return 4


def _manifest(path: Path, *, identity_fields: tuple[str, ...]) -> tuple[dict[str, Any], str]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BibliographyPublishError(
            "CITATION-ROOT-MISMATCH", f"manifest is unreadable: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise BibliographyPublishError(
            "CITATION-ROOT-MISMATCH", "manifest is not an object"
        )
    identity = next(
        (value.get(field) for field in identity_fields if isinstance(value.get(field), str)),
        None,
    )
    if not identity:
        raise BibliographyPublishError(
            "CITATION-ROOT-MISMATCH", "manifest identity is missing"
        )
    return value, identity


def _descriptor(
    *, kind: str, identity: str, root: Path, manifest: Path
) -> dict[str, str]:
    return {
        "kind": kind,
        "identity": identity,
        "discovery": "explicit:" + manifest.relative_to(root).as_posix(),
        "manifest_sha256": sha256(manifest),
    }


def _binding(
    path: Path,
    *,
    root: Path,
    descriptor: dict[str, str],
    evidence_type: str,
    digest: str | None = None,
) -> dict[str, Any]:
    resolved = path.resolve() if digest is not None else path.resolve(strict=True)
    if not resolved.is_relative_to(root):
        raise BibliographyPublishError(
            "CITATION-ROOT-MISMATCH", f"bound path escapes its root: {path}"
        )
    return {
        "root": copy.deepcopy(descriptor),
        "path": resolved.relative_to(root).as_posix(),
        "sha256": digest if digest is not None else sha256(resolved),
        "evidence_type": evidence_type,
    }


def _source_path(project_root: Path, source_loc: Any) -> Path:
    if not isinstance(source_loc, str) or not source_loc or "\\" in source_loc:
        raise BibliographyPublishError(
            "CITATION-IDENTITY-MISMATCH", "source_loc is not a portable path"
        )
    relative = PurePosixPath(source_loc)
    if relative.is_absolute() or relative.as_posix() != source_loc or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise BibliographyPublishError(
            "CITATION-IDENTITY-MISMATCH", "source_loc is not canonical"
        )
    try:
        result = (project_root / Path(*relative.parts)).resolve(strict=True)
    except OSError as exc:
        raise BibliographyPublishError(
            "CITATION-SNAPSHOT-STALE", "canonical source bytes are missing"
        ) from exc
    if not result.is_relative_to(project_root) or not result.is_file():
        raise BibliographyPublishError(
            "CITATION-ROOT-MISMATCH", "canonical source escapes the project root"
        )
    return result


def publish_bibliography(
    *,
    project_root: Path,
    project_manifest: Path,
    wiki_root: Path,
    wiki_manifest: Path,
    policy: Path,
    source_keys: list[str],
    snapshot_id: str,
    out: Path,
    manifest_out: Path,
    commit_marker_out: Path,
) -> dict[str, Any]:
    project_root = project_root.resolve(strict=True)
    wiki_root = wiki_root.resolve(strict=True)
    project_manifest = project_manifest.resolve(strict=True)
    wiki_manifest = wiki_manifest.resolve(strict=True)
    policy = policy.resolve(strict=True)
    outputs = [out.resolve(), manifest_out.resolve(), commit_marker_out.resolve()]
    if len(set(outputs)) != len(outputs):
        raise BibliographyPublishError(
            "CITATION-SNAPSHOT-INVALID", "publication outputs must be distinct"
        )
    if any(not path.is_relative_to(project_root) for path in outputs):
        raise BibliographyPublishError(
            "CITATION-ROOT-MISMATCH", "publication output escapes project root"
        )
    if not source_keys or any(not key for key in source_keys):
        raise BibliographyPublishError(
            "CITATION-METADATA-MISSING", "at least one source key is required"
        )
    _, project_identity = _manifest(
        project_manifest, identity_fields=("identity", "fixture_id")
    )
    _, wiki_identity = _manifest(
        wiki_manifest, identity_fields=("manifest_id", "identity")
    )
    if not project_manifest.is_relative_to(project_root):
        raise BibliographyPublishError(
            "CITATION-ROOT-MISMATCH", "project manifest escapes project root"
        )
    if not wiki_manifest.is_relative_to(wiki_root) or not policy.is_relative_to(wiki_root):
        raise BibliographyPublishError(
            "CITATION-ROOT-MISMATCH", "Wiki manifest or policy escapes Wiki root"
        )
    project_descriptor = _descriptor(
        kind="project",
        identity=project_identity,
        root=project_root,
        manifest=project_manifest,
    )
    wiki_descriptor = _descriptor(
        kind="wiki", identity=wiki_identity, root=wiki_root, manifest=wiki_manifest
    )
    index = wiki_source_index(wiki_root)
    wiki_source_lane = (wiki_root / "wiki" / "sources").resolve(strict=True)
    wiki_inventory = {
        path.relative_to(wiki_source_lane).as_posix(): sha256(path)
        for path, _metadata in index.values()
    }
    rows: list[dict[str, Any]] = []
    preconditions: dict[Path, str] = {
        project_manifest: project_descriptor["manifest_sha256"],
        wiki_manifest: wiki_descriptor["manifest_sha256"],
        policy: sha256(policy),
    }
    canonical_keys: set[str] = set()
    for lookup_key in source_keys:
        try:
            page, metadata, redirect_chain = resolve_wiki_source(lookup_key, index)
        except Exception as exc:
            code = getattr(exc, "code", "CITATION-REDIRECT-INVALID")
            raise BibliographyPublishError(code, str(exc)) from exc
        required = {
            "source_key", "aliases", "zotero_key", "source_loc", "authors", "year", "title"
        }
        if any(field not in metadata for field in required):
            raise BibliographyPublishError(
                "CITATION-METADATA-MISSING", f"canonical metadata is incomplete for {lookup_key}"
            )
        canonical_key = metadata["source_key"]
        if not isinstance(canonical_key, str) or canonical_key in canonical_keys:
            raise BibliographyPublishError(
                "CITATION-BIBLIOGRAPHY-AMBIGUOUS", "canonical source is duplicated"
            )
        canonical_keys.add(canonical_key)
        source = _source_path(project_root, metadata["source_loc"])
        page_digest = sha256(page)
        source_digest = sha256(source)
        preconditions.update({page: page_digest, source: source_digest})
        rows.append(
            {
                "source_key": canonical_key,
                "lookup_key": lookup_key,
                "canonical_page": _binding(
                    page,
                    root=wiki_root,
                    descriptor=wiki_descriptor,
                    evidence_type="canonical_source_page",
                    digest=page_digest,
                ),
                "redirect_chain": redirect_chain,
                "aliases": copy.deepcopy(metadata["aliases"]),
                "zotero_key": metadata["zotero_key"],
                "source_loc": metadata["source_loc"],
                "source": _binding(
                    source,
                    root=project_root,
                    descriptor=project_descriptor,
                    evidence_type="source_pdf",
                    digest=source_digest,
                ),
                "authors": copy.deepcopy(metadata["authors"]),
                "year": metadata["year"],
                "title": metadata["title"],
            }
        )
    snapshot: dict[str, Any] = {
        "schema_version": "1.0.0",
        "snapshot_type": "canonical_bibliography_snapshot",
        "snapshot_id": snapshot_id,
        "wiki_root": wiki_descriptor,
        "policy": _binding(
            policy,
            root=wiki_root,
            descriptor=wiki_descriptor,
            evidence_type="bibliography_policy",
        ),
        "sources": rows,
    }
    transaction_id = "bibliography-" + hashlib.sha256(canonical_bytes({
        "snapshot": snapshot,
        "outputs": [path.relative_to(project_root).as_posix() for path in outputs],
    })).hexdigest()[:16]
    payload_hash = payload_sha256(snapshot)
    output_binding = {
        "path": outputs[0].relative_to(project_root).as_posix(),
        "payload_sha256": payload_hash,
        "evidence_type": "canonical_bibliography_snapshot_payload",
    }
    inputs = [copy.deepcopy(snapshot["policy"])]
    for row in rows:
        inputs.extend([copy.deepcopy(row["canonical_page"]), copy.deepcopy(row["source"])])
    transaction_manifest = {
        "schema_version": "1.0.0",
        "transaction_id": transaction_id,
        "mode": "committed",
        "state": "prepared",
        "inputs": inputs,
        "intended_outputs": [output_binding],
        "prior_state": {"publication": "absent"},
        "prospective_state": {
            "publication": "committed",
            "payload_sha256": payload_hash,
        },
    }
    manifest_bytes = canonical_bytes(transaction_manifest)
    manifest_binding = _binding(
        outputs[1],
        root=project_root,
        descriptor=project_descriptor,
        evidence_type="publication_manifest",
        digest=hashlib.sha256(manifest_bytes).hexdigest(),
    )
    marker = {
        "schema_version": "1.0.0",
        "transaction_id": transaction_id,
        "mode": "committed",
        "state": "committed",
        "manifest": manifest_binding,
        "final_output_hashes": [copy.deepcopy(output_binding)],
    }
    marker_bytes = canonical_bytes(marker)
    snapshot["publication"] = {
        "mode": "committed",
        "transaction_id": transaction_id,
        "manifest": manifest_binding,
        "commit_marker": {
            "root": copy.deepcopy(project_descriptor),
            "path": outputs[2].relative_to(project_root).as_posix(),
            "sha256": hashlib.sha256(marker_bytes).hexdigest(),
            "evidence_type": "publication_commit_marker",
        },
    }

    def revalidate_under_claim() -> None:
        current_index = wiki_source_index(wiki_root)
        for row in rows:
            try:
                page, metadata, chain = resolve_wiki_source(
                    row["lookup_key"], current_index
                )
            except Exception as exc:
                raise EvidencePublicationError(
                    f"Wiki redirect re-resolution failed under claim: {exc}"
                ) from exc
            expected_page = (
                wiki_root / Path(*PurePosixPath(row["canonical_page"]["path"]).parts)
            ).resolve(strict=True)
            if page != expected_page or chain != row["redirect_chain"]:
                raise EvidencePublicationError(
                    "Wiki redirect result changed under claim"
                )
            for field in (
                "source_key",
                "aliases",
                "zotero_key",
                "source_loc",
                "authors",
                "year",
                "title",
            ):
                if metadata.get(field) != row[field]:
                    raise EvidencePublicationError(
                        f"Wiki canonical {field} changed under claim"
                    )
            source = _source_path(project_root, metadata["source_loc"])
            if (
                source.relative_to(project_root).as_posix() != row["source"]["path"]
                or sha256(source) != row["source"]["sha256"]
                or sha256(page) != row["canonical_page"]["sha256"]
            ):
                raise EvidencePublicationError(
                    "Wiki canonical page or source bytes changed under claim"
                )
    publish_committed(
        project_root=project_root,
        transaction_id=transaction_id,
        preconditions=sorted(preconditions.items(), key=lambda row: str(row[0])),
        inventory_preconditions=[(wiki_source_lane, wiki_inventory)],
        outputs=[
            (outputs[1], manifest_bytes),
            (outputs[0], canonical_bytes(snapshot)),
        ],
        marker=(outputs[2], marker_bytes),
        under_claim_validator=revalidate_under_claim,
    )
    return snapshot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--project-manifest", type=Path, required=True)
    parser.add_argument("--wiki-root", type=Path, required=True)
    parser.add_argument("--wiki-manifest", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--source-key", action="append", required=True)
    parser.add_argument("--snapshot-id", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--manifest-out", type=Path, required=True)
    parser.add_argument("--commit-marker-out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        for output in (args.out, args.manifest_out, args.commit_marker_out):
            assert_writable(output.resolve(), purpose="canonical bibliography publication")
        value = publish_bibliography(
            project_root=args.project_root,
            project_manifest=args.project_manifest,
            wiki_root=args.wiki_root,
            wiki_manifest=args.wiki_manifest,
            policy=args.policy,
            source_keys=args.source_key,
            snapshot_id=args.snapshot_id,
            out=args.out,
            manifest_out=args.manifest_out,
            commit_marker_out=args.commit_marker_out,
        )
    except DestinationRefused as exc:
        return _block("CITATION-ROOT-MISMATCH", str(exc))
    except (BibliographyPublishError, EvidencePublicationError, OSError) as exc:
        return _block(getattr(exc, "code", "CITATION-SNAPSHOT-INVALID"), str(exc))
    print(canonical_bytes(value).decode("utf-8").rstrip("\n"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
