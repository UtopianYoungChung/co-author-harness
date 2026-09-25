#!/usr/bin/env python3
"""C2 exact-byte extraction, locator, bibliography, and passage validation."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

SHA_RE = re.compile(r"^[0-9a-f]{64}$")
SUPPORTED_EXTRACTOR = {
    "name": "pdftotext.exe",
    "version": "24.04.0",
    "sha256": "640b9a93fa31fc093860c635cd410a3e30f7d1e6166cb1130993fb1985f474ff",
    "size": 343552,
}
# Any other pdftotext is admitted only when the committed miniature fixture
# qualifies it (docs/superpowers/specs/2026-07-24-assurance-provenance-closure-c0.md):
# its utf8-lf-v1 normalization of miniature.pdf must equal the committed
# expected_utf8_lf_v1.txt byte for byte. The receipt then records the real
# executable's identity plus this qualification.
EXTRACTOR_NAMES = frozenset({"pdftotext", "pdftotext.exe"})
EXTRACTOR_QUALIFICATION = {
    "method": "fixture-conformance-v1",
    "fixture_id": "assurance-provenance-c2",
    "fixture_sha256": "e21a489ac04667bc46d4335e604f6e6ba3fbfa27d8f473a96d0ebce9737a6c3a",
    "normalized_sha256": "62260ccc2f6bcddf37f55f23d17d184493b2ba9ab17e3d9484d757b9f2ae5b87",
}
PORTABLE_FIELDS = {"root", "path", "sha256", "evidence_type"}
ROOT_FIELDS = {"kind", "identity", "discovery", "manifest_sha256"}


class EvidenceValidationError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON value {value}")


def _object_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def load_canonical_document(
    path: Path,
    *,
    schema_code: str,
    canonical_code: str | None = None,
) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_object_no_duplicates,
            parse_constant=_reject_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise EvidenceValidationError(
            schema_code, f"cannot read strict JSON at {path}: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise EvidenceValidationError(schema_code, f"JSON root is not an object: {path}")
    if canonical_code is not None and raw != canonical_bytes(value):
        raise EvidenceValidationError(
            canonical_code, f"JSON is not in the frozen canonical form: {path}"
        )
    return value, raw


def payload_sha256(value: dict[str, Any]) -> str:
    payload = copy.deepcopy(value)
    payload.pop("publication", None)
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _safe_relative(value: Any, code: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise EvidenceValidationError(code, "portable path must be a non-empty POSIX path")
    path = PurePosixPath(value)
    if path.is_absolute() or value != path.as_posix() or any(
        part in {"", ".", ".."} for part in path.parts
    ):
        raise EvidenceValidationError(code, f"portable path is not canonical: {value!r}")
    if ":" in value or any(part.endswith((" ", ".")) for part in path.parts):
        raise EvidenceValidationError(code, f"portable path uses an unsafe alias: {value!r}")
    return path


def _manifest_identity(value: dict[str, Any]) -> str | None:
    for key in ("identity", "manifest_id", "fixture_id"):
        if isinstance(value.get(key), str):
            return value[key]
    return None


def resolve_root(
    descriptor: Any,
    *,
    project_root: Path,
    wiki_root: Path,
    code: str,
) -> Path:
    if not isinstance(descriptor, dict) or set(descriptor) != ROOT_FIELDS:
        raise EvidenceValidationError(code, "governing-root descriptor is malformed")
    kind = descriptor.get("kind")
    if kind == "project":
        root = project_root.resolve(strict=True)
    elif kind == "wiki":
        root = wiki_root.resolve(strict=True)
    else:
        raise EvidenceValidationError(code, f"unsupported C2 governing-root kind: {kind!r}")
    discovery = descriptor.get("discovery")
    if not isinstance(discovery, str) or not discovery.startswith("explicit:"):
        raise EvidenceValidationError(code, "governing-root discovery rule is not explicit")
    manifest_rel = _safe_relative(discovery.removeprefix("explicit:"), code)
    manifest = (root / Path(*manifest_rel.parts)).resolve(strict=True)
    if not manifest.is_relative_to(root) or not manifest.is_file():
        raise EvidenceValidationError(code, "governing-root manifest escapes its root")
    digest = descriptor.get("manifest_sha256")
    if not isinstance(digest, str) or not SHA_RE.fullmatch(digest) or sha256(manifest) != digest:
        raise EvidenceValidationError(code, "governing-root manifest binding is stale")
    try:
        manifest_value = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceValidationError(code, "governing-root manifest is unreadable") from exc
    if not isinstance(manifest_value, dict) or _manifest_identity(manifest_value) != descriptor.get("identity"):
        raise EvidenceValidationError(code, "governing-root identity does not match its manifest")
    return root


def resolve_portable(
    binding: Any,
    *,
    project_root: Path,
    wiki_root: Path,
    stale_code: str,
    path_code: str,
) -> Path:
    if not isinstance(binding, dict) or set(binding) != PORTABLE_FIELDS:
        raise EvidenceValidationError(stale_code, "portable binding is malformed")
    root = resolve_root(
        binding.get("root"),
        project_root=project_root,
        wiki_root=wiki_root,
        code=path_code,
    )
    rel = _safe_relative(binding.get("path"), path_code)
    try:
        path = (root / Path(*rel.parts)).resolve(strict=True)
    except OSError as exc:
        raise EvidenceValidationError(stale_code, "portable binding target is missing") from exc
    if not path.is_relative_to(root) or not path.is_file():
        raise EvidenceValidationError(path_code, "portable binding resolves outside its root")
    digest = binding.get("sha256")
    if not isinstance(digest, str) or not SHA_RE.fullmatch(digest) or sha256(path) != digest:
        raise EvidenceValidationError(stale_code, f"portable binding is stale: {path}")
    if not isinstance(binding.get("evidence_type"), str) or not binding["evidence_type"]:
        raise EvidenceValidationError(stale_code, "portable binding evidence type is missing")
    return path


def require_binding_root_kind(binding: Any, kind: str, code: str) -> None:
    if (
        not isinstance(binding, dict)
        or not isinstance(binding.get("root"), dict)
        or binding["root"].get("kind") != kind
    ):
        raise EvidenceValidationError(code, f"binding must use the {kind} root")


def binding_manifest(binding: dict[str, Any], root: Path, code: str) -> dict[str, Any]:
    descriptor = binding["root"]
    discovery = descriptor.get("discovery")
    if not isinstance(discovery, str) or not discovery.startswith("explicit:"):
        raise EvidenceValidationError(code, "binding manifest discovery is invalid")
    relative = _safe_relative(discovery.removeprefix("explicit:"), code)
    path = (root / Path(*relative.parts)).resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file():
        raise EvidenceValidationError(code, "binding manifest escapes its root")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceValidationError(code, "binding manifest is unreadable") from exc
    if not isinstance(value, dict):
        raise EvidenceValidationError(code, "binding manifest is malformed")
    return value


def _validate_publication(
    owner: dict[str, Any],
    *,
    owner_path: Path,
    expected_inputs: list[dict[str, Any]],
    expected_outputs: list[dict[str, Any]],
    project_root: Path,
    wiki_root: Path,
    invalid_code: str,
    payload_type: str,
) -> None:
    publication = owner.get("publication")
    required = {"mode", "transaction_id", "manifest", "commit_marker"}
    if not isinstance(publication, dict) or set(publication) != required:
        raise EvidenceValidationError(invalid_code, "publication envelope is incomplete")
    if publication.get("mode") != "committed":
        raise EvidenceValidationError(invalid_code, "publication mode is invalid")
    transaction_id = publication.get("transaction_id")
    if not isinstance(transaction_id, str) or not transaction_id:
        raise EvidenceValidationError(invalid_code, "publication transaction id is missing")
    require_binding_root_kind(publication.get("manifest"), "project", invalid_code)
    require_binding_root_kind(publication.get("commit_marker"), "project", invalid_code)
    manifest_path = resolve_portable(
        publication.get("manifest"),
        project_root=project_root,
        wiki_root=wiki_root,
        stale_code=invalid_code,
        path_code=invalid_code,
    )
    marker_path = resolve_portable(
        publication.get("commit_marker"),
        project_root=project_root,
        wiki_root=wiki_root,
        stale_code=invalid_code,
        path_code=invalid_code,
    )
    manifest, _ = load_canonical_document(
        manifest_path, schema_code=invalid_code, canonical_code=invalid_code
    )
    marker, _ = load_canonical_document(
        marker_path, schema_code=invalid_code, canonical_code=invalid_code
    )
    manifest_fields = {
        "schema_version",
        "transaction_id",
        "mode",
        "state",
        "inputs",
        "intended_outputs",
        "prior_state",
        "prospective_state",
    }
    marker_fields = {
        "schema_version",
        "transaction_id",
        "mode",
        "state",
        "manifest",
        "final_output_hashes",
    }
    expected_payload = payload_sha256(owner)
    payload_output = {
        "path": owner_path.resolve(strict=True).relative_to(
            project_root.resolve(strict=True)
        ).as_posix(),
        "payload_sha256": expected_payload,
        "evidence_type": payload_type,
    }
    complete_outputs = [*copy.deepcopy(expected_outputs), payload_output]
    if (
        set(manifest) != manifest_fields
        or set(marker) != marker_fields
        or manifest.get("schema_version") != "1.0.0"
        or marker.get("schema_version") != "1.0.0"
        or manifest.get("transaction_id") != transaction_id
        or marker.get("transaction_id") != transaction_id
        or manifest.get("mode") != publication.get("mode")
        or marker.get("mode") != publication.get("mode")
        or manifest.get("state") != "prepared"
        or marker.get("state") != "committed"
        or manifest.get("inputs") != expected_inputs
        or manifest.get("intended_outputs") != complete_outputs
        or manifest.get("prior_state") != {"publication": "absent"}
        or manifest.get("prospective_state")
        != {"publication": "committed", "payload_sha256": expected_payload}
        or marker.get("manifest") != publication.get("manifest")
        or not isinstance(marker.get("final_output_hashes"), list)
        or marker.get("final_output_hashes") != manifest.get("intended_outputs")
    ):
        raise EvidenceValidationError(invalid_code, "publication transaction shape is invalid")


def _validate_page_map(
    value: dict[str, Any], raw: Path, normalized: Path
) -> None:
    required = {
        "schema_version",
        "normalization_version",
        "offset_unit",
        "raw_sha256",
        "normalized_sha256",
        "pages",
        "named_spans",
    }
    if (
        set(value) != required
        or value.get("schema_version") != "1.0.0"
        or value.get("normalization_version") != "utf8-lf-v1"
        or value.get("offset_unit") != "zero-based-end-exclusive-utf8-byte"
        or value.get("raw_sha256") != sha256(raw)
        or value.get("normalized_sha256") != sha256(normalized)
    ):
        raise EvidenceValidationError("EXTRACT-LOCATOR-MISMATCH", "page map header is stale")
    text = normalized.read_text(encoding="utf-8", errors="strict")
    parts = text.split("\f")
    if parts and not parts[-1]:
        parts.pop()
    expected_pages: list[dict[str, Any]] = []
    cursor = 0
    for number, page_text in enumerate(parts, 1):
        start = text.find(page_text, cursor)
        end = start + len(page_text)
        expected_pages.append({
            "page": number,
            "normalized_start_utf8": len(text[:start].encode("utf-8")),
            "normalized_end_utf8": len(text[:end].encode("utf-8")),
            "text_sha256": hashlib.sha256(page_text.encode("utf-8")).hexdigest(),
        })
        cursor = end + 1
    if value.get("pages") != expected_pages or not isinstance(value.get("named_spans"), dict):
        raise EvidenceValidationError("EXTRACT-LOCATOR-MISMATCH", "page boundaries do not replay")
    data = text.encode("utf-8")
    for rows in value["named_spans"].values():
        if not isinstance(rows, list) or not rows:
            raise EvidenceValidationError("EXTRACT-LOCATOR-MISMATCH", "named span list is empty")
        for row in rows:
            if not isinstance(row, dict) or set(row) != {
                "occurrence", "start_utf8", "end_utf8", "text_sha256"
            }:
                raise EvidenceValidationError("EXTRACT-LOCATOR-MISMATCH", "named span is malformed")
            start = row["start_utf8"]
            end = row["end_utf8"]
            if not isinstance(start, int) or not isinstance(end, int) or not (0 <= start < end <= len(data)):
                raise EvidenceValidationError("EXTRACT-LOCATOR-MISMATCH", "named span bounds are invalid")
            selected = data[start:end]
            if hashlib.sha256(selected).hexdigest() != row.get("text_sha256"):
                raise EvidenceValidationError("EXTRACT-LOCATOR-MISMATCH", "named span hash is stale")
            occurrences: list[int] = []
            at = 0
            while True:
                at = data.find(selected, at)
                if at < 0:
                    break
                occurrences.append(at)
                at += len(selected)
            try:
                actual_occurrence = occurrences.index(start) + 1
            except ValueError as exc:
                raise EvidenceValidationError(
                    "EXTRACT-LOCATOR-MISMATCH", "named span offset does not select its bytes"
                ) from exc
            if row.get("occurrence") != actual_occurrence:
                raise EvidenceValidationError("EXTRACT-LOCATOR-MISMATCH", "named span occurrence is stale")


def validate_page_map(
    value: dict[str, Any], *, raw: Path, normalized: Path
) -> None:
    """Validate a replayable raw-to-normalized page/span map."""
    _validate_page_map(value, raw.resolve(strict=True), normalized.resolve(strict=True))


def validate_extractor_identity(executable: Any) -> None:
    """Admit the reference extractor, or one the conformance fixture qualified."""
    base_keys = set(SUPPORTED_EXTRACTOR)
    if not isinstance(executable, dict) or set(executable) not in (
        base_keys, base_keys | {"qualification"}
    ):
        raise EvidenceValidationError("EXTRACT-RECEIPT-INVALID", "extractor identity is malformed")
    if "qualification" not in executable:
        if executable.get("version") != SUPPORTED_EXTRACTOR["version"]:
            raise EvidenceValidationError(
                "EXTRACTOR-UNSUPPORTED", "extractor version is not qualified"
            )
        if any(
            executable.get(key) != value
            for key, value in SUPPORTED_EXTRACTOR.items() if key != "version"
        ):
            raise EvidenceValidationError(
                "EXTRACTOR-IDENTITY-MISMATCH", "extractor bytes do not match qualification"
            )
        return
    if executable["qualification"] != EXTRACTOR_QUALIFICATION:
        raise EvidenceValidationError(
            "EXTRACTOR-UNSUPPORTED",
            "extractor qualification does not name the committed conformance fixture",
        )
    name = executable.get("name")
    version = executable.get("version")
    digest = executable.get("sha256")
    size = executable.get("size")
    if (
        not isinstance(name, str) or name.casefold() not in EXTRACTOR_NAMES
        or not isinstance(version, str) or not version
        or not isinstance(digest, str) or not SHA_RE.fullmatch(digest)
        or not isinstance(size, int) or isinstance(size, bool) or size < 1
    ):
        raise EvidenceValidationError("EXTRACT-RECEIPT-INVALID", "extractor identity is malformed")
    _reestablish_qualification(name, version, digest, size)


# (resolved executable path, sha256) -> (reported version, reproduces fixture)
_QUALIFICATION_CACHE: dict[tuple[str, str], tuple[str | None, bool]] = {}


def _reestablish_qualification(name: str, version: str, digest: str, size: int) -> None:
    """A qualified identity is self-reported, so re-establish it on this host.

    The executable the receipt names must be present on PATH with exactly that
    name, size and hash, must report the declared version, and must still
    reproduce the conformance fixture. A receipt naming an executable this host
    cannot re-qualify is refused rather than trusted.
    """
    # Lazy: source_extract imports this module at load time.
    from source_extract import _conforms, _extractor_candidates, _reported_version

    for candidate in _extractor_candidates():
        try:
            if (
                candidate.name.casefold() != name.casefold()
                or candidate.stat().st_size != size
                or sha256(candidate) != digest
            ):
                continue
        except OSError:
            continue
        key = (str(candidate.resolve()), digest)
        if key not in _QUALIFICATION_CACHE:
            _QUALIFICATION_CACHE[key] = (_reported_version(candidate), _conforms(candidate))
        observed_version, conforms = _QUALIFICATION_CACHE[key]
        if observed_version != version:
            raise EvidenceValidationError(
                "EXTRACTOR-UNSUPPORTED",
                "extractor version does not match the qualified executable",
            )
        if not conforms:
            raise EvidenceValidationError(
                "EXTRACTOR-UNSUPPORTED",
                "extractor no longer reproduces the conformance fixture",
            )
        return
    raise EvidenceValidationError(
        "EXTRACTOR-IDENTITY-MISMATCH",
        "the fixture-qualified extractor this receipt names is not on this host's "
        "PATH, so its qualification cannot be re-established",
    )


def _validate_extract(
    path: Path,
    *,
    project_root: Path,
    wiki_root: Path,
) -> dict[str, Any]:
    value, _ = load_canonical_document(
        path, schema_code="EXTRACT-RECEIPT-INVALID", canonical_code="EXTRACT-RECEIPT-INVALID"
    )
    required = {
        "schema_version", "receipt_type", "source_key", "source", "raw_output",
        "normalized_output", "page_span_map", "extraction", "publication",
    }
    if (
        set(value) != required
        or value.get("schema_version") != "2.0.0"
        or value.get("receipt_type") != "canonical_extract_receipt"
        or not isinstance(value.get("source_key"), str)
        or not value["source_key"]
        or not isinstance(value.get("extraction"), dict)
    ):
        raise EvidenceValidationError("EXTRACT-RECEIPT-INVALID", "extract receipt shape is invalid")
    extraction = value["extraction"]
    if set(extraction) != {
        "adapter", "executable", "argv", "layout_mode", "normalization_version"
    } or extraction.get("adapter") != "poppler-pdftotext":
        raise EvidenceValidationError("EXTRACT-RECEIPT-INVALID", "extract metadata is invalid")
    validate_extractor_identity(extraction.get("executable"))
    if (
        extraction.get("argv") != ["-enc", "UTF-8"]
        or extraction.get("layout_mode") != "logical-default-v1"
        or extraction.get("normalization_version") != "utf8-lf-v1"
    ):
        raise EvidenceValidationError("EXTRACT-BINDING-STALE", "extractor invocation contract is stale")
    for binding in (
        value["source"],
        value["raw_output"],
        value["normalized_output"],
        value["page_span_map"],
    ):
        require_binding_root_kind(binding, "project", "EXTRACT-PATH-ESCAPE")
        if binding.get("root") != value["source"].get("root"):
            raise EvidenceValidationError(
                "EXTRACT-BINDING-STALE", "extract bindings use different project roots"
            )
    source = resolve_portable(
        value["source"], project_root=project_root, wiki_root=wiki_root,
        stale_code="EXTRACT-BINDING-STALE", path_code="EXTRACT-PATH-ESCAPE",
    )
    raw = resolve_portable(
        value["raw_output"], project_root=project_root, wiki_root=wiki_root,
        stale_code="EXTRACT-BINDING-STALE", path_code="EXTRACT-PATH-ESCAPE",
    )
    normalized = resolve_portable(
        value["normalized_output"], project_root=project_root, wiki_root=wiki_root,
        stale_code="EXTRACT-BINDING-STALE", path_code="EXTRACT-PATH-ESCAPE",
    )
    page_map_path = resolve_portable(
        value["page_span_map"], project_root=project_root, wiki_root=wiki_root,
        stale_code="EXTRACT-BINDING-STALE", path_code="EXTRACT-PATH-ESCAPE",
    )
    admitted = binding_manifest(
        value["source"], project_root.resolve(), "EXTRACT-BINDING-STALE"
    ).get("admitted_sources")
    source_rel = source.relative_to(project_root.resolve()).as_posix()
    if not isinstance(admitted, list) or not any(
        isinstance(row, dict)
        and row.get("path") == source_rel
        and row.get("sha256") == sha256(source)
        for row in admitted
    ):
        raise EvidenceValidationError("EXTRACT-BINDING-STALE", "source is not admitted by the project manifest")
    page_map, _ = load_canonical_document(
        page_map_path,
        schema_code="EXTRACT-LOCATOR-MISMATCH",
        canonical_code="EXTRACT-LOCATOR-MISMATCH",
    )
    _validate_page_map(page_map, raw, normalized)
    _validate_publication(
        value,
        owner_path=path,
        expected_inputs=[
            copy.deepcopy(value["source"]),
            {"extraction": copy.deepcopy(value["extraction"])},
        ],
        expected_outputs=[
            copy.deepcopy(value["raw_output"]),
            copy.deepcopy(value["normalized_output"]),
            copy.deepcopy(value["page_span_map"]),
        ],
        project_root=project_root,
        wiki_root=wiki_root,
        invalid_code="EXTRACT-RECEIPT-INVALID",
        payload_type="canonical_extract_receipt_payload",
    )
    return {
        "value": value,
        "source": source,
        "raw": raw,
        "normalized": normalized,
        "page_map": page_map,
        "path": path,
    }


def validate_extract_receipt(
    path: Path, *, project_root: Path, wiki_root: Path
) -> dict[str, Any]:
    """Validate one standalone canonical-extract 2.0.0 receipt."""
    return _validate_extract(
        path,
        project_root=project_root.resolve(strict=True),
        wiki_root=wiki_root.resolve(strict=True),
    )


def _frontmatter(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise EvidenceValidationError(
            "CITATION-METADATA-MISSING",
            "canonical page metadata cannot be validated because PyYAML is unavailable",
        ) from exc
    try:
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            raise ValueError("missing front matter")
        value = yaml.safe_load(text.split("---", 2)[1])
    except (OSError, UnicodeError, ValueError, yaml.YAMLError) as exc:
        raise EvidenceValidationError("CITATION-METADATA-MISSING", "canonical page metadata is unreadable") from exc
    if not isinstance(value, dict):
        raise EvidenceValidationError("CITATION-METADATA-MISSING", "canonical page metadata is malformed")
    return value


def wiki_source_index(wiki_root: Path) -> dict[str, tuple[Path, dict[str, Any]]]:
    lane = (wiki_root / "wiki" / "sources").resolve(strict=True)
    result: dict[str, tuple[Path, dict[str, Any]]] = {}
    for path in sorted(lane.glob("*.md")):
        metadata = _frontmatter(path)
        key = metadata.get("source_key")
        if not isinstance(key, str) or not key or key in result:
            raise EvidenceValidationError(
                "CITATION-BIBLIOGRAPHY-AMBIGUOUS",
                "Wiki source keys are missing or ambiguous",
            )
        result[key] = (path.resolve(), metadata)
    return result


def resolve_wiki_source(
    key: str,
    index: dict[str, tuple[Path, dict[str, Any]]],
) -> tuple[Path, dict[str, Any], list[str]]:
    visited: list[str] = []
    current = key
    while True:
        if current in visited or current not in index:
            raise EvidenceValidationError(
                "CITATION-REDIRECT-INVALID", "Wiki redirect cycle or missing target"
            )
        visited.append(current)
        path, metadata = index[current]
        target = metadata.get("redirect_to")
        if target is None:
            return path, metadata, visited[1:]
        if not isinstance(target, str) or not target or "/" in target or "\\" in target:
            raise EvidenceValidationError(
                "CITATION-REDIRECT-INVALID", "Wiki redirect target is invalid"
            )
        current = target


def _validate_bibliography(
    path: Path,
    *,
    project_root: Path,
    wiki_root: Path,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    value, _ = load_canonical_document(
        path, schema_code="CITATION-SNAPSHOT-INVALID", canonical_code="CITATION-SNAPSHOT-INVALID"
    )
    if set(value) != {
        "schema_version", "snapshot_type", "snapshot_id", "wiki_root", "policy",
        "sources", "publication",
    } or value.get("schema_version") != "1.0.0" or value.get("snapshot_type") != "canonical_bibliography_snapshot":
        raise EvidenceValidationError("CITATION-SNAPSHOT-INVALID", "bibliography snapshot shape is invalid")
    resolved_wiki = resolve_root(
        value.get("wiki_root"), project_root=project_root, wiki_root=wiki_root,
        code="CITATION-ROOT-MISMATCH",
    )
    if resolved_wiki != wiki_root.resolve():
        raise EvidenceValidationError("CITATION-ROOT-MISMATCH", "bibliography uses another Wiki root")
    require_binding_root_kind(value.get("policy"), "wiki", "CITATION-ROOT-MISMATCH")
    resolve_portable(
        value.get("policy"), project_root=project_root, wiki_root=wiki_root,
        stale_code="CITATION-SNAPSHOT-STALE", path_code="CITATION-ROOT-MISMATCH",
    )
    rows = value.get("sources")
    if not isinstance(rows, list) or not rows:
        raise EvidenceValidationError("CITATION-SNAPSHOT-INVALID", "bibliography sources are invalid")
    by_key: dict[str, dict[str, Any]] = {}
    aliases: set[str] = set()
    wiki_index = wiki_source_index(wiki_root)
    required = {
        "source_key", "lookup_key", "canonical_page", "redirect_chain", "aliases", "zotero_key",
        "source_loc", "source", "authors", "year", "title",
    }
    for row in rows:
        if not isinstance(row, dict) or set(row) != required:
            raise EvidenceValidationError("CITATION-METADATA-MISSING", "bibliography row metadata is incomplete")
        key = row.get("source_key")
        if not isinstance(key, str) or not key or key in by_key:
            raise EvidenceValidationError("CITATION-BIBLIOGRAPHY-AMBIGUOUS", "source key is ambiguous")
        lookup_key = row.get("lookup_key")
        if not isinstance(lookup_key, str) or not lookup_key:
            raise EvidenceValidationError("CITATION-REDIRECT-INVALID", "lookup key is missing")
        redirect_chain = row.get("redirect_chain")
        if not isinstance(redirect_chain, list):
            raise EvidenceValidationError("CITATION-REDIRECT-INVALID", "redirect chain is malformed")
        row_aliases = row.get("aliases")
        if not isinstance(row_aliases, list) or any(not isinstance(item, str) or not item for item in row_aliases):
            raise EvidenceValidationError("CITATION-METADATA-MISSING", "aliases are invalid")
        identities = {
            key.casefold(),
            lookup_key.casefold(),
            *(item.casefold() for item in row_aliases),
        }
        if aliases & identities:
            raise EvidenceValidationError("CITATION-BIBLIOGRAPHY-AMBIGUOUS", "alias collision")
        aliases.update(identities)
        require_binding_root_kind(
            row["canonical_page"], "wiki", "CITATION-ROOT-MISMATCH"
        )
        page = resolve_portable(
            row["canonical_page"], project_root=project_root, wiki_root=wiki_root,
            stale_code="CITATION-SNAPSHOT-STALE", path_code="CITATION-ROOT-MISMATCH",
        )
        canonical_lane = (wiki_root / "wiki" / "sources").resolve(strict=True)
        if page.parent != canonical_lane:
            raise EvidenceValidationError(
                "CITATION-ROOT-MISMATCH",
                "canonical page is outside the Wiki source lane",
            )
        resolved_page, metadata, expected_chain = resolve_wiki_source(
            lookup_key, wiki_index
        )
        if redirect_chain != expected_chain or page != resolved_page:
            raise EvidenceValidationError(
                "CITATION-REDIRECT-INVALID",
                "snapshot redirect chain is not derived from Wiki metadata",
            )
        require_binding_root_kind(
            row["source"], "project", "CITATION-ROOT-MISMATCH"
        )
        source = resolve_portable(
            row["source"], project_root=project_root, wiki_root=wiki_root,
            stale_code="CITATION-SNAPSHOT-STALE", path_code="CITATION-ROOT-MISMATCH",
        )
        source_loc = row.get("source_loc")
        if (
            not isinstance(source_loc, str)
            or not source_loc
            or row["source"].get("path") != source_loc
        ):
            raise EvidenceValidationError("CITATION-IDENTITY-MISMATCH", "source_loc does not bind the source file")
        for field in ("source_key", "zotero_key", "source_loc", "authors", "year", "title", "aliases"):
            if metadata.get(field) != row.get(field):
                raise EvidenceValidationError("CITATION-IDENTITY-MISMATCH", f"canonical {field} does not match Wiki metadata")
        if (
            not isinstance(row.get("authors"), list)
            or not row["authors"]
            or any(not isinstance(author, str) or not author for author in row["authors"])
            or not isinstance(row.get("year"), int)
            or not isinstance(row.get("title"), str)
            or not row["title"]
        ):
            raise EvidenceValidationError("CITATION-METADATA-MISSING", "canonical citation metadata is invalid")
        by_key[key] = row
    publication_inputs: list[dict[str, Any]] = [copy.deepcopy(value["policy"])]
    for row in rows:
        publication_inputs.extend(
            [copy.deepcopy(row["canonical_page"]), copy.deepcopy(row["source"])]
        )
    _validate_publication(
        value,
        owner_path=path,
        expected_inputs=publication_inputs,
        expected_outputs=[],
        project_root=project_root,
        wiki_root=wiki_root,
        invalid_code="CITATION-SNAPSHOT-INVALID",
        payload_type="canonical_bibliography_snapshot_payload",
    )
    return value, by_key


def _span_bytes(value: str, span: Any, code: str) -> bytes:
    if not isinstance(span, dict) or set(span) != {"start_utf8", "end_utf8", "text_sha256"}:
        raise EvidenceValidationError(code, "manuscript span is malformed")
    start = span.get("start_utf8")
    end = span.get("end_utf8")
    data = value.encode("utf-8")
    if not isinstance(start, int) or not isinstance(end, int) or not (0 <= start < end <= len(data)):
        raise EvidenceValidationError(code, "manuscript span bounds are invalid")
    selected = data[start:end]
    if hashlib.sha256(selected).hexdigest() != span.get("text_sha256"):
        raise EvidenceValidationError(code, "manuscript span hash is stale")
    return selected


def _locator_bytes(extract: dict[str, Any], locator: Any) -> bytes:
    required = {
        "page_start", "page_end", "normalized_start_utf8", "normalized_end_utf8",
        "occurrence", "text_sha256",
    }
    if not isinstance(locator, dict) or set(locator) != required:
        raise EvidenceValidationError("EXTRACT-LOCATOR-MISMATCH", "locator is malformed")
    data = extract["normalized"].read_bytes()
    start = locator.get("normalized_start_utf8")
    end = locator.get("normalized_end_utf8")
    if not isinstance(start, int) or not isinstance(end, int) or not (0 <= start < end <= len(data)):
        raise EvidenceValidationError("EXTRACT-LOCATOR-MISMATCH", "locator bounds are invalid")
    selected = data[start:end]
    if hashlib.sha256(selected).hexdigest() != locator.get("text_sha256"):
        raise EvidenceValidationError("EXTRACT-LOCATOR-MISMATCH", "locator hash is stale")
    occurrences: list[int] = []
    at = 0
    while True:
        at = data.find(selected, at)
        if at < 0:
            break
        occurrences.append(at)
        at += len(selected)
    if start not in occurrences or locator.get("occurrence") != occurrences.index(start) + 1:
        raise EvidenceValidationError("EXTRACT-LOCATOR-MISMATCH", "locator occurrence is stale")
    pages = extract["page_map"]["pages"]
    page_start = next((row["page"] for row in pages if row["normalized_start_utf8"] <= start < row["normalized_end_utf8"]), None)
    page_end = next((row["page"] for row in pages if row["normalized_start_utf8"] <= end - 1 < row["normalized_end_utf8"]), None)
    if locator.get("page_start") != page_start or locator.get("page_end") != page_end:
        raise EvidenceValidationError("EXTRACT-LOCATOR-MISMATCH", "locator page selection is stale")
    return selected


def validate_v3_receipt(
    receipt: dict[str, Any],
    *,
    artifact: Path,
    project_root: Path | None,
    wiki_root: Path | None,
) -> dict[str, Any]:
    if project_root is None or wiki_root is None:
        raise EvidenceValidationError("EVIDENCE-ROOT-MISMATCH", "v3 validation requires explicit project and Wiki roots")
    project_root = project_root.resolve(strict=True)
    wiki_root = wiki_root.resolve(strict=True)
    require_binding_root_kind(
        receipt.get("artifact"), "project", "EVIDENCE-ROOT-MISMATCH"
    )
    artifact_binding = resolve_portable(
        receipt.get("artifact"), project_root=project_root, wiki_root=wiki_root,
        stale_code="ARTIFACT-BINDING", path_code="EVIDENCE-ROOT-MISMATCH",
    )
    if artifact_binding != artifact:
        raise EvidenceValidationError("ARTIFACT-BINDING", "semantic receipt targets another artifact")
    require_binding_root_kind(
        receipt.get("centroid_packet"), "project", "EVIDENCE-ROOT-MISMATCH"
    )
    packet_path = resolve_portable(
        receipt.get("centroid_packet"), project_root=project_root, wiki_root=wiki_root,
        stale_code="CENTROID-COVERAGE-INCOMPLETE", path_code="EVIDENCE-ROOT-MISMATCH",
    )
    require_binding_root_kind(
        receipt.get("policy"), "wiki", "CITATION-ROOT-MISMATCH"
    )
    resolve_portable(
        receipt.get("policy"), project_root=project_root, wiki_root=wiki_root,
        stale_code="CITATION-SNAPSHOT-STALE", path_code="CITATION-ROOT-MISMATCH",
    )
    extract_bindings = receipt.get("canonical_extract_receipts")
    if not isinstance(extract_bindings, list) or not extract_bindings:
        raise EvidenceValidationError("EXTRACT-RECEIPT-MISSING", "no canonical extract receipts are bound")
    extracts: dict[tuple[str, str], dict[str, Any]] = {}
    for binding in extract_bindings:
        require_binding_root_kind(binding, "project", "EXTRACT-PATH-ESCAPE")
        extract_path = resolve_portable(
            binding, project_root=project_root, wiki_root=wiki_root,
            stale_code="EXTRACT-RECEIPT-INVALID", path_code="EXTRACT-PATH-ESCAPE",
        )
        extract = _validate_extract(extract_path, project_root=project_root, wiki_root=wiki_root)
        extracts[(str(extract_path), sha256(extract_path))] = extract
    require_binding_root_kind(
        receipt.get("canonical_bibliography_snapshot"),
        "project",
        "CITATION-ROOT-MISMATCH",
    )
    bibliography_path = resolve_portable(
        receipt.get("canonical_bibliography_snapshot"),
        project_root=project_root, wiki_root=wiki_root,
        stale_code="CITATION-SNAPSHOT-STALE", path_code="CITATION-ROOT-MISMATCH",
    )
    if receipt.get("corpus_digest") != sha256(bibliography_path):
        raise EvidenceValidationError("CITATION-SNAPSHOT-STALE", "semantic corpus digest is stale")
    _bibliography, sources = _validate_bibliography(
        bibliography_path, project_root=project_root, wiki_root=wiki_root
    )
    passages = receipt.get("passages")
    if not isinstance(passages, list) or not passages:
        raise EvidenceValidationError("EXTRACT-RECEIPT-MISSING", "semantic receipt has no passages")
    artifact_text = artifact.read_text(encoding="utf-8", errors="strict")
    direct_legacy: list[dict[str, Any]] = []
    bibliography_materials: dict[str, dict[str, Any]] = {}
    cited_keys: set[str] = set()
    for passage in passages:
        if not isinstance(passage, dict) or "canonical_extract_receipt" not in passage:
            raise EvidenceValidationError("EXTRACT-RECEIPT-MISSING", "passage lacks its extract receipt")
        passage_binding = passage["canonical_extract_receipt"]
        require_binding_root_kind(
            passage_binding, "project", "EXTRACT-PATH-ESCAPE"
        )
        extract_path = resolve_portable(
            passage_binding, project_root=project_root, wiki_root=wiki_root,
            stale_code="EXTRACT-RECEIPT-INVALID", path_code="EXTRACT-PATH-ESCAPE",
        )
        extract = extracts.get((str(extract_path), sha256(extract_path)))
        if extract is None or passage.get("source_key") != extract["value"].get("source_key"):
            raise EvidenceValidationError("EXTRACT-RECEIPT-INVALID", "passage binds the wrong extract receipt")
        selected = _locator_bytes(extract, passage.get("locator"))
        material_locator = f"p. {passage['locator']['page_start']}"
        material_id = passage['source_key'] + '@' + material_locator
        material = bibliography_materials.setdefault(material_id, {
            'source_id': material_id, 'locator': material_locator,
            'path': str(extract['normalized']), 'sha256': sha256(extract['normalized']),
            'passage_texts': [],
        })
        if material['path'] != str(extract['normalized']) or material['sha256'] != sha256(extract['normalized']):
            raise EvidenceValidationError('BIBLIOGRAPHY-MATERIAL', 'Conflicting extracts for one source locator')
        material['passage_texts'].append(selected.decode('utf-8', errors='strict'))
        manuscript = _span_bytes(artifact_text, passage.get("manuscript_span"), "MANUSCRIPT-SPAN-MISMATCH")
        use = passage.get("passage_use")
        common = {
            "source_key", "use_scope", "passage_use", "canonical_extract_receipt",
            "locator", "manuscript_span", "citation",
        }
        if use == "direct_quotation":
            if set(passage) != common | {"direct_quotation"}:
                raise EvidenceValidationError("PASSAGE-CLASSIFICATION-MISMATCH", "direct quotation fields are inconsistent")
            direct = passage.get("direct_quotation")
            if not isinstance(direct, dict) or set(direct) != {"text"} or not isinstance(direct.get("text"), str):
                raise EvidenceValidationError("PASSAGE-CLASSIFICATION-MISMATCH", "direct quotation is malformed")
            quote_bytes = direct["text"].encode("utf-8")
            if selected != quote_bytes or manuscript != quote_bytes:
                raise EvidenceValidationError("PASSAGE-CLASSIFICATION-MISMATCH", "direct quotation is not byte exact")
        elif use == "conditioning_passage":
            if set(passage) != common | {"influence_statement", "evaluator_review"} or not isinstance(passage.get("influence_statement"), str) or not passage["influence_statement"].strip():
                raise EvidenceValidationError("PASSAGE-CLASSIFICATION-MISMATCH", "conditioning passage is malformed")
            if selected == manuscript:
                raise EvidenceValidationError("PASSAGE-CLASSIFICATION-MISMATCH", "verbatim manuscript bytes cannot be relabelled as conditioning")
            review = passage.get("evaluator_review")
            expected_review = {
                "schema_version": "1.0.0",
                "review_type": "conditioning_influence_review",
                "reviewer_role": "evaluator",
                "disposition": "accepted",
                "influence_statement_sha256": hashlib.sha256(
                    passage["influence_statement"].encode("utf-8")
                ).hexdigest(),
                "source_passage_sha256": hashlib.sha256(selected).hexdigest(),
                "manuscript_span_sha256": hashlib.sha256(manuscript).hexdigest(),
                "artifact_sha256": sha256(artifact),
            }
            if review != expected_review:
                raise EvidenceValidationError(
                    "PASSAGE-CLASSIFICATION-MISMATCH",
                    "conditioning influence lacks an exact Evaluator review",
                )
        else:
            raise EvidenceValidationError("PASSAGE-CLASSIFICATION-MISMATCH", "passage use is unknown")
        source_key = passage.get("source_key")
        citation = passage.get("citation")
        if source_key not in sources or not isinstance(citation, dict):
            raise EvidenceValidationError("CITATION-IDENTITY-MISMATCH", "passage citation has no canonical source")
        cited_keys.add(source_key)
        if use == "direct_quotation":
            direct_legacy.append({
                "source_key": source_key,
                "use_scope": passage.get("use_scope"),
                "source": {"path": str(extract["source"]), "sha256": sha256(extract["source"])},
                "locator": f"p. {passage['locator']['page_start']}",
                "extract": {"path": str(extract["normalized"]), "sha256": sha256(extract["normalized"])},
                "extraction": {"method": "pdftotext", "tool": "pdftotext", "canonical": True},
                "quote": passage["direct_quotation"]["text"],
                "citation": {
                    key: copy.deepcopy(citation[key])
                    for key in ("authors", "year", "title", "label")
                },
                "use": "Non-authoritative diagnostic compatibility quotation.",
            })
    groups: dict[tuple[tuple[str, ...], int], list[str]] = {}
    for key in cited_keys:
        row = sources[key]
        group = (tuple(author.casefold() for author in row["authors"]), row["year"])
        groups.setdefault(group, []).append(key)
    expected_labels: dict[str, str] = {}
    for (_authors, year), keys in groups.items():
        ordered = sorted(keys, key=lambda key: sources[key]["title"].casefold())
        for index, key in enumerate(ordered):
            expected_labels[key] = str(year) if len(ordered) == 1 else f"{year}{chr(97 + index)}"
    for passage in passages:
        canonical = sources[passage["source_key"]]
        expected = {
            "source_key": passage["source_key"],
            "authors": canonical["authors"],
            "year": canonical["year"],
            "title": canonical["title"],
            "label": expected_labels[passage["source_key"]],
        }
        if passage.get("citation") != expected:
            raise EvidenceValidationError("CITATION-IDENTITY-MISMATCH", "passage citation does not match cited-subset identity")
    reference_match = re.search(
        r"^#{1,6}\s+(?:references|bibliography)\s*$",
        artifact_text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if reference_match is None:
        raise EvidenceValidationError(
            "CITATION-IDENTITY-MISMATCH", "manuscript has no bibliography section"
        )
    prose = artifact_text[:reference_match.start()]
    references = artifact_text[reference_match.end():]
    reference_lines = [line.strip() for line in references.splitlines() if line.strip()]
    for key in cited_keys:
        canonical = sources[key]
        label = expected_labels[key]
        if not any(
            f"({label})." in line
            and canonical["title"].casefold() in line.casefold()
            and all(
                author.casefold() in line.casefold()
                for author in canonical["authors"]
            )
            for line in reference_lines
        ):
            raise EvidenceValidationError(
                "CITATION-IDENTITY-MISMATCH",
                "manuscript bibliography does not match canonical cited identity",
            )
        surname = canonical["authors"][0].split(",", 1)[0].strip()
        if f"({surname}, {label})".casefold() not in prose.casefold():
            raise EvidenceValidationError(
                "CITATION-IDENTITY-MISMATCH",
                "manuscript citation does not match canonical cited identity",
            )
    packet, _ = load_canonical_document(
        packet_path, schema_code="CENTROID-COVERAGE-INCOMPLETE", canonical_code="CENTROID-COVERAGE-INCOMPLETE"
    )
    members = packet.get("members")
    if not isinstance(members, list):
        raise EvidenceValidationError("CENTROID-COVERAGE-INCOMPLETE", "centroid packet members are missing")
    centroid_keys = {
        row.get("source_key") for row in members
        if isinstance(row, dict) and row.get("role") == "centroid"
    }
    if not any(
        passage.get("source_key") in centroid_keys and passage.get("use_scope") == "surface"
        for passage in passages
    ):
        raise EvidenceValidationError("CENTROID-COVERAGE-INCOMPLETE", "no centroid-role surface passage exists")
    coverage = receipt.get("member_coverage")
    if not isinstance(coverage, list):
        raise EvidenceValidationError("CENTROID-COVERAGE-INCOMPLETE", "member coverage is missing")
    coverage_by_key = {
        row.get("source_key"): row for row in coverage if isinstance(row, dict)
    }
    for member in members:
        if not isinstance(member, dict) or member.get("role") != "argument":
            continue
        row = coverage_by_key.get(member.get("source_key"))
        if (
            not isinstance(row, dict)
            or row.get("member_role") != "argument"
            or row.get("disposition") not in {"included", "omitted"}
            or not isinstance(row.get("rationale"), str)
            or not row["rationale"].strip()
        ):
            raise EvidenceValidationError("CENTROID-COVERAGE-INCOMPLETE", "argument-member rationale is incomplete")
    view = receipt.get("diagnostic_legacy_view")
    if not isinstance(view, dict) or set(view) != {"passages"} or view.get("passages") != direct_legacy:
        raise EvidenceValidationError("EVIDENCE-SCHEMA-INVALID", "diagnostic compatibility view is not derived from validated passages")
    return {
        "schema_version": "2.0.0",
        "receipt_type": "centroid_semantic_execution",
        "phase": receipt.get("phase"),
        "artifact": {"path": str(artifact), "sha256": sha256(artifact)},
        "passages": direct_legacy,
        "bibliography_materials": list(bibliography_materials.values()),
        "semantic_assessment": receipt.get("semantic_assessment"),
    }
