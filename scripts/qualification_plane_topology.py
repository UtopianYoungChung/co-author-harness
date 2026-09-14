#!/usr/bin/env python3
"""Validate the five non-overlapping planes used by release qualification."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import unicodedata
import zipfile
from pathlib import Path
from typing import Any, Iterable, Mapping
import sys

from qualification_environment import QualificationEnvironmentRefusal, assert_ambient_clean


ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "references/schemas/qualification_plane_topology_receipt.schema.json"
PLANE_KINDS = ("source", "build", "archive", "unpacked", "installed_cache")
COMMIT_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
REGRESSION_CONTRACT = {
    "missing_plane_kind", "unknown_plane_kind", "five_planes_required",
    "attached_build_refused", "dirty_build_refused", "wrong_commit_refused",
    "overlap_refused", "casefold_alias_refused", "nfc_alias_refused",
    "reparse_refused", "archive_provenance_mismatch_refused",
    "git_metadata_outside_source_build_refused",
    "post_build_source_residue_refused_before_suites",
    "source_preflight_refuses_dirty_before_product_suites",
    "live_git_state_rechecked_before_suites",
    "receipt_path_reparse_rechecked_before_suites",
    "final_source_stability_rechecked_before_receipt",
}
_MISSING = object()


class PlaneTopologyRefusal(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True,
        encoding="utf-8", errors="strict", check=False,
    )


def _is_reparse(path: Path) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return True
    return path.is_symlink() or bool(
        getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )


def _assert_no_reparse(path: Path) -> None:
    current = path
    while True:
        if _is_reparse(current):
            raise PlaneTopologyRefusal("PLANE-REPARSE", f"plane path traverses a reparse point: {current}")
        if current.parent == current:
            return
        current = current.parent


def _assert_no_descendant_reparse(root: Path) -> None:
    """Reject links/junctions before walking into any directory-plane child."""
    for current, dirs, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        for name in sorted(dirs + files):
            candidate = current_path / name
            if _is_reparse(candidate):
                raise PlaneTopologyRefusal(
                    "PLANE-REPARSE",
                    f"plane contains a link or reparse point: {candidate}",
                )


def _path_key(path: Path) -> str:
    return unicodedata.normalize("NFC", os.path.normcase(str(path))).casefold()


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def capture_source_snapshot(root: Path) -> dict[str, dict[str, Any]]:
    """Capture every non-Git source entry, including ignored build residue."""
    root = root.resolve(strict=True)
    result: dict[str, dict[str, Any]] = {}
    for current, dirs, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        dirs[:] = sorted(name for name in dirs if name != ".git")
        for name in sorted(dirs + files):
            path = current_path / name
            rel = path.relative_to(root).as_posix()
            if path.is_symlink():
                raw = os.readlink(path).encode("utf-8", errors="surrogatepass")
                result[rel] = {"kind": "symlink", "sha256": _sha(raw)}
            elif path.is_file():
                result[rel] = {"kind": "file", "sha256": _sha(path.read_bytes())}
            elif path.is_dir():
                result[rel] = {"kind": "directory", "sha256": _sha(b"")}
    return result


def _tree_digest(root: Path) -> str:
    inventory = capture_source_snapshot(root)
    inventory = {
        rel: row for rel, row in inventory.items()
        if rel != "releases/verification" and not rel.startswith("releases/verification/")
    }
    material = "".join(
        f"{rel}\0{row['kind']}\0{row['sha256']}\n"
        for rel, row in sorted(inventory.items())
    ).encode("utf-8")
    return _sha(material)


def plane_digest(kind: str, path: Path) -> str:
    """Return the topology digest for one already-materialized plane."""
    resolved = path.resolve(strict=True)
    _assert_no_reparse(path.absolute())
    if kind == "archive":
        if not resolved.is_file():
            raise PlaneTopologyRefusal("PLANE-PATH", "archive plane must be a file")
        return _sha(resolved.read_bytes())
    if kind not in PLANE_KINDS or not resolved.is_dir():
        raise PlaneTopologyRefusal("PLANE-PATH", f"invalid {kind!r} directory plane")
    _assert_no_descendant_reparse(resolved)
    return _tree_digest(resolved)


def _provenance_from_bytes(raw: bytes) -> str | None:
    try:
        value = json.loads(raw)
    except (UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict) or value.get("schema") != "coauthor-build-provenance/v1":
        return None
    commit = value.get("commit")
    return commit.lower() if isinstance(commit, str) and COMMIT_RE.fullmatch(commit.lower()) else None


def _directory_provenance(root: Path) -> str | None:
    path = root / "PROVENANCE.json"
    return _provenance_from_bytes(path.read_bytes()) if path.is_file() else None


def _archive_facts(path: Path) -> tuple[str, str | None]:
    raw = path.read_bytes()
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if any(part.casefold() == ".git" for name in names for part in Path(name).parts):
                raise PlaneTopologyRefusal("PLANE-GIT-CONTAMINATION", "archive contains Git metadata")
            provenance = _provenance_from_bytes(archive.read("PROVENANCE.json"))
    except PlaneTopologyRefusal:
        raise
    except (OSError, KeyError, zipfile.BadZipFile, RuntimeError) as exc:
        raise PlaneTopologyRefusal("PLANE-ARCHIVE", f"archive is unreadable or lacks provenance: {exc}") from exc
    return _sha(raw), provenance


def _git_facts(root: Path, kind: str, source_commit: str) -> tuple[str, str]:
    top = _git(root, "rev-parse", "--show-toplevel")
    head = _git(root, "rev-parse", "HEAD")
    if top.returncode or head.returncode or Path(top.stdout.strip()).resolve() != root:
        raise PlaneTopologyRefusal("PLANE-GIT", f"{kind} is not an exact Git worktree root")
    commit = head.stdout.strip().lower()
    if commit != source_commit:
        raise PlaneTopologyRefusal("PLANE-BUILD-COMMIT" if kind == "build" else "PLANE-SOURCE-COMMIT", f"{kind} commit differs")
    status = _git(root, "status", "--porcelain", "--untracked-files=all")
    if status.returncode or status.stdout:
        raise PlaneTopologyRefusal("PLANE-BUILD-DIRTY" if kind == "build" else "PLANE-SOURCE-DIRTY", f"{kind} worktree is dirty")
    branch = _git(root, "symbolic-ref", "-q", "--short", "HEAD")
    if kind == "build":
        if branch.returncode == 0:
            raise PlaneTopologyRefusal("PLANE-BUILD-ATTACHED", "build worktree must be detached")
        return commit, "detached_clean"
    if branch.returncode != 0 or branch.stdout.strip() != "main":
        raise PlaneTopologyRefusal("PLANE-SOURCE-BRANCH", "source worktree must be saved main")
    return commit, "source_main"


def capture_clean_source_preimage(root: Path) -> dict[str, dict[str, Any]]:
    """Bind a clean saved-main source plane before product suites execute."""

    try:
        assert_ambient_clean()
    except QualificationEnvironmentRefusal as exc:
        raise PlaneTopologyRefusal(exc.code, exc.message) from exc
    raw = root.absolute()
    _assert_no_reparse(raw)
    resolved = raw.resolve(strict=True)
    if not resolved.is_dir():
        raise PlaneTopologyRefusal("PLANE-PATH", "source plane must be a directory")
    _assert_no_descendant_reparse(resolved)
    head = _git(resolved, "rev-parse", "HEAD")
    commit = head.stdout.strip().lower()
    if head.returncode or not COMMIT_RE.fullmatch(commit):
        raise PlaneTopologyRefusal("PLANE-SOURCE-COMMIT", "source HEAD is unavailable")
    _git_facts(resolved, "source", commit)
    return capture_source_snapshot(resolved)


def validate_topology(
    planes: Iterable[Mapping[str, Any]], *, source_commit: str,
    source_preimage: Mapping[str, Mapping[str, Any]] | object = _MISSING,
) -> dict[str, Any]:
    # The commit-bound package builder imports only capture_source_snapshot in
    # a dependency-isolated clean worktree. Keep jsonschema out of that import
    # plane; schema validation owns the dependency at its point of use.
    from jsonschema import Draft202012Validator

    try:
        assert_ambient_clean()
    except QualificationEnvironmentRefusal as exc:
        raise PlaneTopologyRefusal(exc.code, exc.message) from exc
    source_commit = source_commit.lower()
    if not COMMIT_RE.fullmatch(source_commit):
        raise PlaneTopologyRefusal("PLANE-SOURCE-COMMIT", "source_commit must be a full object id")
    if source_preimage is _MISSING:
        raise PlaneTopologyRefusal(
            "PLANE-SOURCE-PREIMAGE-MISSING",
            "a pre-build source inventory is required",
        )
    if not isinstance(source_preimage, Mapping) or not all(
        isinstance(rel, str) and isinstance(value, Mapping)
        for rel, value in source_preimage.items()
    ):
        raise PlaneTopologyRefusal(
            "PLANE-SOURCE-PREIMAGE-INVALID",
            "source preimage must be a path-keyed inventory object",
        )
    rows = [dict(row) for row in planes]
    if any("plane_kind" not in row for row in rows):
        raise PlaneTopologyRefusal("PLANE-KIND-MISSING", "every plane requires plane_kind")
    unknown = [row.get("plane_kind") for row in rows if row.get("plane_kind") not in PLANE_KINDS]
    if unknown:
        raise PlaneTopologyRefusal("PLANE-KIND-UNKNOWN", f"unknown plane_kind: {unknown[0]!r}")
    kinds = [str(row["plane_kind"]) for row in rows]
    if sorted(kinds) != sorted(PLANE_KINDS):
        raise PlaneTopologyRefusal("PLANE-FIVE-REQUIRED", "exactly one of all five plane kinds is required")

    # Alias identity is a property of the caller's absolute spellings, not of
    # filesystem resolution. Check it first so a case-only spelling on a
    # case-sensitive host, or one side of an NFC pair, cannot degrade into the
    # weaker PLANE-PATH result merely because that spelling is not materialized.
    raw_paths: dict[str, Path] = {}
    raw_keys: dict[str, str] = {}
    for row in rows:
        kind = str(row["plane_kind"])
        raw_path = row.get("path")
        if not isinstance(raw_path, (str, os.PathLike)):
            raise PlaneTopologyRefusal("PLANE-PATH", f"{kind} path is missing")
        try:
            raw_absolute = Path(raw_path).absolute()
        except (OSError, TypeError, ValueError) as exc:
            raise PlaneTopologyRefusal("PLANE-PATH", f"{kind} path is unavailable: {exc}") from exc
        key = _path_key(raw_absolute)
        if key in raw_keys:
            raise PlaneTopologyRefusal(
                "PLANE-PATH-ALIAS",
                f"{kind} aliases {raw_keys[key]} after absolute NFC/casefold",
            )
        raw_keys[key] = kind
        raw_paths[kind] = raw_absolute

    paths: dict[str, Path] = {}
    for row in rows:
        kind = str(row["plane_kind"])
        raw_absolute = raw_paths[kind]
        try:
            path = raw_absolute.resolve(strict=True)
        except OSError as exc:
            raise PlaneTopologyRefusal("PLANE-PATH", f"{kind} path is unavailable: {exc}") from exc
        if kind == "archive" and not path.is_file():
            raise PlaneTopologyRefusal("PLANE-PATH", "archive plane must be a file")
        if kind != "archive" and not path.is_dir():
            raise PlaneTopologyRefusal("PLANE-PATH", f"{kind} plane must be a directory")
        _assert_no_reparse(raw_absolute)
        if kind != "archive":
            _assert_no_descendant_reparse(path)
        paths[kind] = path

    keys: dict[str, str] = {}
    for kind, path in paths.items():
        key = _path_key(path)
        if key in keys:
            raise PlaneTopologyRefusal("PLANE-PATH-ALIAS", f"{kind} aliases {keys[key]} after NFC/casefold")
        keys[key] = kind
    for left, left_path in paths.items():
        for right, right_path in paths.items():
            if left >= right:
                continue
            if _inside(left_path, right_path) or _inside(right_path, left_path):
                raise PlaneTopologyRefusal("PLANE-PATH-OVERLAP", f"{left} and {right} overlap")

    stable = dict(source_preimage) == capture_source_snapshot(paths["source"])
    if not stable:
        raise PlaneTopologyRefusal("PLANE-SOURCE-RESIDUE", "source changed after build and before suite launch")

    records: list[dict[str, Any]] = []
    for kind in PLANE_KINDS:
        path = paths[kind]
        git_commit: str | None = None
        git_state = "absent"
        provenance_commit: str | None = None
        if kind in {"source", "build"}:
            git_commit, git_state = _git_facts(path, kind, source_commit)
            digest = _tree_digest(path)
        elif kind == "archive":
            digest, provenance_commit = _archive_facts(path)
        else:
            if any(item.name.casefold() == ".git" for item in path.rglob("*")):
                raise PlaneTopologyRefusal("PLANE-GIT-CONTAMINATION", f"{kind} contains Git metadata")
            provenance_commit = _directory_provenance(path)
            digest = _tree_digest(path)
        if kind in {"archive", "unpacked", "installed_cache"} and provenance_commit != source_commit:
            raise PlaneTopologyRefusal("PLANE-PROVENANCE-MISMATCH", f"{kind} provenance does not bind source commit")
        records.append({
            "plane_kind": kind, "path": str(path),
            "path_kind": "file" if kind == "archive" else "directory",
            "digest_sha256": digest, "git_commit": git_commit,
            "git_state": git_state, "provenance_commit": provenance_commit,
        })

    # Receipt issuance is itself a transaction.  The first source comparison
    # guarded suite launch, but the Git queries and five plane digests above
    # take time.  Re-read both Git state and every source byte after those reads
    # so a mutation in that window cannot be memorialized as source_stable.
    _git_facts(paths["source"], "source", source_commit)
    final_source = capture_source_snapshot(paths["source"])
    if dict(source_preimage) != final_source:
        raise PlaneTopologyRefusal(
            "PLANE-SOURCE-RESIDUE",
            "source changed while the topology receipt was being produced",
        )
    source_record = next(record for record in records if record["plane_kind"] == "source")
    if _tree_digest(paths["source"]) != source_record["digest_sha256"]:
        raise PlaneTopologyRefusal(
            "PLANE-SOURCE-RESIDUE",
            "source digest changed while the topology receipt was being produced",
        )

    receipt = {
        "schema_version": "1.0.0", "receipt_type": "qualification_plane_topology",
        "source_commit": source_commit, "planes": records, "source_stable": stable,
        "findings": [], "verdict": "qualified",
    }
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(receipt), key=lambda error: list(error.path))
    if errors:
        raise PlaneTopologyRefusal("PLANE-SCHEMA", "; ".join(error.message for error in errors))
    return receipt


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8", errors="strict"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PlaneTopologyRefusal("PLANE-RECEIPT", f"cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PlaneTopologyRefusal("PLANE-RECEIPT", f"{path} must contain a JSON object")
    return value


def canonical_receipt_bytes(receipt: Mapping[str, Any]) -> bytes:
    return (json.dumps(dict(receipt), sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def verify_topology_receipt_binding(
    receipt_input: Path | Mapping[str, Any] | None,
    *,
    source_commit: str,
    bindings: Mapping[str, Path],
) -> tuple[dict[str, Any], str]:
    """Verify a qualified receipt and exact live bindings before child execution."""
    from jsonschema import Draft202012Validator

    if receipt_input is None:
        raise PlaneTopologyRefusal("PLANE-TOPOLOGY-MISSING", "a qualified five-plane topology receipt is required")
    receipt = _load_json_object(receipt_input) if isinstance(receipt_input, Path) else dict(receipt_input)
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(receipt), key=lambda error: list(error.path))
    if errors:
        raise PlaneTopologyRefusal("PLANE-TOPOLOGY-SCHEMA", "; ".join(error.message for error in errors))
    normalized_commit = source_commit.lower()
    if receipt.get("verdict") != "qualified" or receipt.get("source_stable") is not True:
        raise PlaneTopologyRefusal("PLANE-TOPOLOGY-UNQUALIFIED", "topology receipt is not qualified and stable")
    if receipt.get("source_commit") != normalized_commit:
        raise PlaneTopologyRefusal("PLANE-TOPOLOGY-COMMIT", "topology receipt source commit differs")
    records = {row["plane_kind"]: row for row in receipt["planes"]}
    resolved_records: dict[str, Path] = {}
    path_keys: dict[str, str] = {}
    for kind in PLANE_KINDS:
        record = records[kind]
        if kind in {"source", "build"}:
            if record["git_commit"] != normalized_commit or record["provenance_commit"] is not None:
                raise PlaneTopologyRefusal("PLANE-TOPOLOGY-COMMIT", f"{kind} identity fields differ")
        elif record["git_commit"] is not None or record["provenance_commit"] != normalized_commit:
            raise PlaneTopologyRefusal("PLANE-TOPOLOGY-COMMIT", f"{kind} provenance fields differ")
        try:
            recorded_raw = Path(record["path"]).absolute()
            _assert_no_reparse(recorded_raw)
            recorded_path = recorded_raw.resolve(strict=True)
        except OSError as exc:
            raise PlaneTopologyRefusal("PLANE-TOPOLOGY-PATH", f"cannot resolve {kind}: {exc}") from exc
        key = _path_key(recorded_path)
        if key in path_keys:
            raise PlaneTopologyRefusal("PLANE-PATH-ALIAS", f"{kind} aliases {path_keys[key]}")
        path_keys[key] = kind
        resolved_records[kind] = recorded_path
        if kind in {"source", "build"}:
            live_commit, live_state = _git_facts(recorded_path, kind, normalized_commit)
            if live_commit != record["git_commit"] or live_state != record["git_state"]:
                raise PlaneTopologyRefusal(
                    "PLANE-TOPOLOGY-COMMIT",
                    f"{kind} live Git identity differs from topology receipt",
                )
        if plane_digest(kind, recorded_raw) != record["digest_sha256"]:
            raise PlaneTopologyRefusal("PLANE-TOPOLOGY-DRIFT", f"{kind} digest differs from topology receipt")
    for left, left_path in resolved_records.items():
        for right, right_path in resolved_records.items():
            if left < right and (_inside(left_path, right_path) or _inside(right_path, left_path)):
                raise PlaneTopologyRefusal("PLANE-PATH-OVERLAP", f"{left} and {right} overlap")
    for kind, supplied in bindings.items():
        if kind not in PLANE_KINDS:
            raise PlaneTopologyRefusal("PLANE-KIND-UNKNOWN", f"unknown binding kind: {kind}")
        expected = records[kind]
        try:
            supplied_raw = supplied.absolute()
            _assert_no_reparse(supplied_raw)
            actual_path = supplied_raw.resolve(strict=True)
        except OSError as exc:
            raise PlaneTopologyRefusal("PLANE-TOPOLOGY-PATH", f"cannot resolve {kind} binding: {exc}") from exc
        if actual_path != resolved_records[kind]:
            raise PlaneTopologyRefusal("PLANE-TOPOLOGY-PATH", f"{kind} path differs from topology receipt")
    # Close the same mutation window during consumer verification: source Git
    # state and bytes must still match after every other plane has been read.
    live_commit, live_state = _git_facts(resolved_records["source"], "source", normalized_commit)
    source_record = records["source"]
    if live_commit != source_record["git_commit"] or live_state != source_record["git_state"]:
        raise PlaneTopologyRefusal(
            "PLANE-TOPOLOGY-COMMIT", "source live Git identity differs after topology verification",
        )
    if plane_digest("source", Path(source_record["path"]).absolute()) != source_record["digest_sha256"]:
        raise PlaneTopologyRefusal(
            "PLANE-TOPOLOGY-DRIFT", "source changed while topology binding was verified",
        )
    return receipt, _sha(canonical_receipt_bytes(receipt))


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    snapshot = commands.add_parser("snapshot-source")
    snapshot.add_argument("--source-root", type=Path, required=True)
    validate = commands.add_parser("validate")
    validate.add_argument("--spec", type=Path, required=True)
    validate.add_argument("--source-preimage", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "snapshot-source":
            result: Mapping[str, Any] = capture_clean_source_preimage(args.source_root)
        else:
            spec = _load_json_object(args.spec)
            preimage = _load_json_object(args.source_preimage)
            result = validate_topology(
                spec.get("planes", ()),
                source_commit=spec.get("source_commit", ""),
                source_preimage=preimage,
            )
    except (PlaneTopologyRefusal, OSError, UnicodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 4
    sys.stdout.buffer.write(canonical_receipt_bytes(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
