#!/usr/bin/env python3
"""Safely extract one plugin archive and run its isolated runtime-plane probe."""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import re
import shutil
import site
import stat
import subprocess
import sys
import tempfile
import unicodedata
import uuid
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator

import destination_capability as destinations


ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "references" / "schemas" / "archive_runtime_receipt.schema.json"
RUNTIME_SCHEMA_REL = Path("references/schemas/runtime_plane_receipt.schema.json")
EXPECTED_RUNTIME_SUITES = (
    ("governed_product_gate_self_check", "governed_product_gate_self_check", "scripts/run_product_gate_smoketest.py"),
    ("schema_runtime_check", "portable_core", "scripts/schema_runtime_check.py"),
    ("version_check", "portable_core", "scripts/version-check.py"),
    ("skill_check", "portable_core", "scripts/skill-check.py"),
    ("shipment_manifest_v2_smoketest", "portable_core", "scripts/shipment_manifest_smoketest.py"),
    ("output_contract_v3_smoketest", "portable_core", "scripts/output_contract_smoketest.py"),
)
RUNTIME_PROBE = "scripts/runtime_plane_probe.py"
DIGEST_ALGORITHM = "sha256(path-NUL-kind-NUL-content-sha256-LF)"
COMMIT_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
NESTED_ARCHIVE_SUFFIXES = (
    ".zip", ".plugin", ".whl", ".jar", ".tar", ".tgz", ".tar.gz",
    ".tar.bz2", ".tar.xz", ".gz", ".bz2", ".xz", ".7z", ".rar",
)
UNSAFE_SEPARATOR_CHARS = {"\\", "\u2215", "\u2044", "\uff0f"}
WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


class ArchiveProbeRefusal(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (OSError, ValueError):
        return False


def _finding(code: str, message: str) -> dict[str, str]:
    return {"code": code, "severity": "BLOCKER", "message": message}


def _safe_member_name(info: zipfile.ZipInfo) -> tuple[str, str]:
    # On Windows zipfile normalizes backslashes in ``filename``.  The original
    # central-directory spelling remains in ``orig_filename`` and is the only
    # safe input for separator and duplicate checks.
    raw = info.orig_filename
    if not isinstance(raw, str) or not raw or "\x00" in raw:
        raise ArchiveProbeRefusal("ARCHIVE-MEMBER-NAME", "archive member name is empty or contains NUL")
    if raw != unicodedata.normalize("NFC", raw):
        raise ArchiveProbeRefusal("ARCHIVE-MEMBER-NORMALIZATION", f"member is not NFC-normalized: {raw!r}")
    if raw.startswith(("/", "\\", "//", "\\\\")) or re.match(r"^[A-Za-z]:", raw):
        raise ArchiveProbeRefusal("ARCHIVE-MEMBER-ABSOLUTE", f"absolute, drive, or UNC member: {raw!r}")
    if any(character in raw for character in UNSAFE_SEPARATOR_CHARS) or "//" in raw:
        raise ArchiveProbeRefusal("ARCHIVE-MEMBER-SEPARATOR", f"unsafe separator in member: {raw!r}")
    if ":" in raw or any(ord(character) < 32 for character in raw):
        raise ArchiveProbeRefusal("ARCHIVE-MEMBER-SEPARATOR", f"unsafe character in member: {raw!r}")

    directory = info.is_dir() or raw.endswith("/")
    logical = raw[:-1] if directory and raw.endswith("/") else raw
    parts = logical.split("/")
    if not logical or any(part in {"", ".", ".."} for part in parts):
        raise ArchiveProbeRefusal("ARCHIVE-MEMBER-TRAVERSAL", f"empty or traversal segment in member: {raw!r}")
    for part in parts:
        if part.endswith((" ", ".")) or part.split(".", 1)[0].upper() in WINDOWS_RESERVED:
            raise ArchiveProbeRefusal("ARCHIVE-MEMBER-PORTABILITY", f"non-portable member segment: {raw!r}")

    mode = (info.external_attr >> 16) & 0xFFFF
    file_type = stat.S_IFMT(mode)
    if file_type == stat.S_IFLNK:
        raise ArchiveProbeRefusal("ARCHIVE-MEMBER-SYMLINK", f"symlink member: {raw!r}")
    if file_type not in {0, stat.S_IFREG, stat.S_IFDIR}:
        raise ArchiveProbeRefusal("ARCHIVE-MEMBER-SPECIAL", f"special-file member: {raw!r}")
    if directory and file_type == stat.S_IFREG:
        raise ArchiveProbeRefusal("ARCHIVE-MEMBER-KIND", f"directory/file mode disagreement: {raw!r}")
    if not directory and file_type == stat.S_IFDIR:
        raise ArchiveProbeRefusal("ARCHIVE-MEMBER-KIND", f"file/directory mode disagreement: {raw!r}")
    if directory and info.file_size != 0:
        raise ArchiveProbeRefusal("ARCHIVE-MEMBER-KIND", f"directory member carries file data: {raw!r}")
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400)
    if (info.external_attr & 0xFFFF) & reparse_flag:
        raise ArchiveProbeRefusal("ARCHIVE-MEMBER-SYMLINK", f"reparse-point-like member: {raw!r}")
    if info.flag_bits & 0x1:
        raise ArchiveProbeRefusal("ARCHIVE-MEMBER-ENCRYPTED", f"encrypted member: {raw!r}")
    lowered = logical.casefold()
    if not directory and lowered.endswith(NESTED_ARCHIVE_SUFFIXES):
        raise ArchiveProbeRefusal("ARCHIVE-MEMBER-NESTED", f"nested archive member: {raw!r}")
    return logical, "directory" if directory else "file"


def _inspect_archive(
    archive_snapshot: bytes,
) -> tuple[list[dict[str, Any]], dict[str, tuple[zipfile.ZipInfo, str]]]:
    """Inspect and decompress every member before any filesystem extraction."""
    records: list[dict[str, Any]] = []
    selected: dict[str, tuple[zipfile.ZipInfo, str]] = {}
    exact: set[str] = set()
    folded: dict[str, str] = {}
    kinds: dict[str, str] = {}
    try:
        with zipfile.ZipFile(io.BytesIO(archive_snapshot), "r") as package:
            infos = package.infolist()
            if not infos:
                raise ArchiveProbeRefusal("ARCHIVE-EMPTY", "archive contains no members")
            for info in infos:
                logical, kind = _safe_member_name(info)
                if logical in exact:
                    raise ArchiveProbeRefusal("ARCHIVE-MEMBER-DUPLICATE", f"duplicate member target: {logical!r}")
                folded_name = logical.casefold()
                if folded_name in folded:
                    raise ArchiveProbeRefusal(
                        "ARCHIVE-MEMBER-CASEFOLD-DUPLICATE",
                        f"case-folded duplicate targets: {folded[folded_name]!r}, {logical!r}",
                    )
                exact.add(logical)
                folded[folded_name] = logical
                kinds[logical] = kind
                selected[logical] = (info, kind)

            for logical, kind in kinds.items():
                parts = PurePosixPath(logical).parts
                for index in range(1, len(parts)):
                    ancestor = "/".join(parts[:index])
                    if kinds.get(ancestor) == "file":
                        raise ArchiveProbeRefusal(
                            "ARCHIVE-MEMBER-KIND-COLLISION",
                            f"file member is an ancestor of another target: {ancestor!r}",
                        )

            for logical in sorted(selected, key=lambda item: (item.casefold(), item)):
                info, kind = selected[logical]
                digest = hashlib.sha256()
                size = 0
                if kind == "file":
                    with package.open(info, "r") as source:
                        for chunk in iter(lambda: source.read(1024 * 1024), b""):
                            digest.update(chunk)
                            size += len(chunk)
                    if size != info.file_size:
                        raise ArchiveProbeRefusal(
                            "ARCHIVE-MEMBER-SIZE", f"decompressed size differs for {logical!r}"
                        )
                records.append({
                    "path": logical,
                    "kind": kind,
                    "size": info.file_size,
                    "compressed_size": info.compress_size,
                    "crc32": f"{info.CRC:08x}",
                    "sha256": digest.hexdigest(),
                })
    except ArchiveProbeRefusal:
        raise
    except (OSError, zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
        raise ArchiveProbeRefusal("ARCHIVE-INVALID", f"archive inspection failed: {exc}") from exc
    return records, selected


def _extract_members(
    archive_snapshot: bytes,
    selected: Mapping[str, tuple[zipfile.ZipInfo, str]],
    root: Path,
) -> None:
    with zipfile.ZipFile(io.BytesIO(archive_snapshot), "r") as package:
        for logical in sorted(selected, key=lambda item: (len(PurePosixPath(item).parts), item.casefold(), item)):
            info, kind = selected[logical]
            target = root.joinpath(*PurePosixPath(logical).parts)
            if not _inside(target, root):
                raise ArchiveProbeRefusal("ARCHIVE-EXTRACT-CONTAINMENT", f"target escapes temporary root: {logical!r}")
            if kind == "directory":
                target.mkdir(parents=True, exist_ok=False)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                raise ArchiveProbeRefusal("ARCHIVE-EXTRACT-COLLISION", f"target already exists: {logical!r}")
            with package.open(info, "r") as source, target.open("xb") as destination:
                shutil.copyfileobj(source, destination, length=1024 * 1024)
                destination.flush()
                os.fsync(destination.fileno())


def _tree_inventory(root: Path) -> dict[str, dict[str, str]]:
    inventory: dict[str, dict[str, str]] = {}
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix().casefold()):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise ArchiveProbeRefusal("ARCHIVE-EXTRACT-SYMLINK", f"extracted tree contains a symlink: {relative}")
        if path.is_dir():
            inventory[relative] = {"kind": "directory", "sha256": _sha_bytes(b"")}
        elif path.is_file():
            inventory[relative] = {"kind": "file", "sha256": _sha_path(path)}
        else:
            raise ArchiveProbeRefusal("ARCHIVE-EXTRACT-SPECIAL", f"extracted tree contains a special file: {relative}")
    return inventory


def _digest(inventory: Mapping[str, Mapping[str, str]]) -> dict[str, Any]:
    digest = hashlib.sha256()
    for relative in sorted(inventory, key=lambda item: (item.casefold(), item)):
        record = inventory[relative]
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(record["kind"].encode("ascii"))
        digest.update(b"\0")
        digest.update(record["sha256"].encode("ascii"))
        digest.update(b"\n")
    return {"algorithm": DIGEST_ALGORITHM, "sha256": digest.hexdigest(), "member_count": len(inventory)}


def _validate(receipt: Mapping[str, Any]) -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    errors = sorted(Draft202012Validator(schema).iter_errors(receipt), key=lambda error: list(error.path))
    if errors:
        raise ArchiveProbeRefusal(
            "ARCHIVE-RECEIPT-SCHEMA",
            "; ".join(f"{list(error.path)}: {error.message}" for error in errors),
        )


def _runtime_schema_errors(
    payload: Mapping[str, Any], source_root: Path
) -> list[str]:
    try:
        schema = json.loads((source_root / RUNTIME_SCHEMA_REL).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        errors = [
            f"{list(error.path)}: {error.message}"
            for error in sorted(
                Draft202012Validator(schema).iter_errors(payload),
                key=lambda error: list(error.path),
            )
        ]
        return errors
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"runtime receipt schema could not be loaded: {exc}"]


def _runtime_binding_errors(
    payload: Mapping[str, Any],
    *,
    source_root: Path,
    extraction_root: Path,
    snapshot_path: Path,
    archive_sha256: str,
    archive_size: int,
    provenance_sha256: str | None,
    source_commit: str,
) -> list[str]:
    errors: list[str] = []

    def same_path(value: Any, expected: Path) -> bool:
        try:
            return isinstance(value, str) and Path(value).resolve() == expected.resolve()
        except OSError:
            return False

    environment = payload.get("environment", {})
    dependencies = environment.get("dependency_paths", []) if isinstance(environment, Mapping) else None
    if not (
        isinstance(environment, Mapping)
        and isinstance(dependencies, list)
        and all(isinstance(path, str) for path in dependencies)
        and environment.get("suite_pythonpath") == os.pathsep.join(dependencies)
    ):
        errors.append("suite PYTHONPATH does not equal the recorded dependency-path join")
    if not same_path(payload.get("baseline_root"), source_root):
        errors.append("baseline_root is not the exact source root")
    if not same_path(payload.get("local_root"), extraction_root):
        errors.append("local_root is not the exact extracted archive root")

    cleared = payload.get("cleared_zip", {})
    if not isinstance(cleared, Mapping):
        errors.append("cleared_zip is absent")
    else:
        expected_values = {
            "sha256": archive_sha256,
            "byte_length": archive_size,
            "source_commit": source_commit,
            "provenance_sha256": provenance_sha256,
        }
        if not same_path(cleared.get("path"), snapshot_path):
            errors.append("cleared_zip.path is not the immutable archive snapshot")
        for key, expected in expected_values.items():
            if cleared.get(key) != expected:
                errors.append(f"cleared_zip.{key} differs from the outer archive binding")

    suites = payload.get("suites", [])
    observed_suites = [
        (row.get("name"), row.get("kind"), row.get("script"))
        for row in suites
        if isinstance(row, Mapping)
    ] if isinstance(suites, list) else []
    if observed_suites != list(EXPECTED_RUNTIME_SUITES):
        errors.append("runtime suite universe/order differs from the six required suites")
    verdict = payload.get("verdict")
    if verdict in {"qualified", "qualified_with_caveats"} and (
        not isinstance(suites, list)
        or any(
            not isinstance(row, Mapping)
            or row.get("status") != "passed"
            or row.get("returncode") != 0
            for row in suites
        )
    ):
        errors.append("a non-blocked runtime receipt has a missing or failed required suite")
    if verdict == "qualified":
        if payload.get("cache_state") != "CODEX_CACHE_QUALIFIED":
            errors.append("qualified receipt lacks CODEX_CACHE_QUALIFIED state")
        if payload.get("identity", {}).get("canonical_archive_claim") is not True:
            errors.append("qualified receipt lacks the canonical archive claim")
        if payload.get("package_digests", {}).get("stable") is not True:
            errors.append("qualified receipt lacks a stable package digest")
        for key in ("crlf_only", "semantic_differences", "missing_files", "foreign_extras", "findings"):
            if payload.get(key) != []:
                errors.append(f"qualified receipt has nonempty {key}")
    return errors


def _write_exclusive(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(_canonical(payload))
            handle.flush()
            os.fsync(handle.fileno())
        os.rename(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def probe_archive(
    *,
    archive: Path,
    source_root: Path,
    source_commit: str,
    archive_receipt_path: Path,
    unpacked_runtime_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        raise ArchiveProbeRefusal("ARCHIVE-RUNTIME-ENV", "PYTHONDONTWRITEBYTECODE=1 is required")
    archive = archive.resolve(strict=True)
    source_root = source_root.resolve(strict=True)
    source_commit = source_commit.lower()
    if not COMMIT_RE.fullmatch(source_commit):
        raise ArchiveProbeRefusal(
            "ARCHIVE-SOURCE-COMMIT", "source commit must be a full Git object id"
        )
    archive_receipt_path = archive_receipt_path.resolve()
    unpacked_runtime_path = unpacked_runtime_path.resolve()
    if not archive.is_file() or not source_root.is_dir():
        raise ArchiveProbeRefusal("ARCHIVE-INPUT", "archive and source root must exist")
    archive_snapshot = archive.read_bytes()
    if not archive_snapshot:
        raise ArchiveProbeRefusal("ARCHIVE-EMPTY", "archive contains no bytes")
    archive_snapshot_sha256 = _sha_bytes(archive_snapshot)
    if archive_receipt_path == unpacked_runtime_path or archive_receipt_path.exists() or unpacked_runtime_path.exists():
        raise ArchiveProbeRefusal("ARCHIVE-OUTPUT", "receipt paths must be distinct and absent")
    evidence_root = (source_root / "releases" / "verification").resolve()
    for output in (archive_receipt_path, unpacked_runtime_path):
        if output.suffix.casefold() != ".json" or not _inside(output, evidence_root):
            raise ArchiveProbeRefusal("ARCHIVE-OUTPUT", "receipts must be JSON beneath source releases/verification")
        try:
            destinations.assert_writable(output, purpose="archive runtime qualification receipt")
        except destinations.DestinationRefused as exc:
            raise ArchiveProbeRefusal(exc.code, str(exc)) from exc

    member_records, selected = _inspect_archive(archive_snapshot)
    transaction_root = Path(tempfile.mkdtemp(prefix="coauthor-archive-runtime-")).resolve()
    extraction_root = transaction_root / "unpacked"
    extraction_root.mkdir()
    snapshot_path = transaction_root / "cleared.zip"
    with snapshot_path.open("xb") as handle:
        handle.write(archive_snapshot)
        handle.flush()
        os.fsync(handle.fileno())
    pre_digest: dict[str, Any] | None = None
    post_digest: dict[str, Any] | None = None
    runtime_payload: dict[str, Any] | None = None
    completed: subprocess.CompletedProcess[bytes] | None = None
    runtime_result_accepted = False
    runtime_payload_valid = False
    sys_path: list[str] = []
    sys_path_observed = False
    findings: list[dict[str, str]] = []
    try:
        _extract_members(archive_snapshot, selected, extraction_root)
        pre_inventory = _tree_inventory(extraction_root)
        pre_digest = _digest(pre_inventory)
        inspected_inventory: dict[str, dict[str, str]] = {}
        for row in member_records:
            parts = PurePosixPath(row["path"]).parts
            for index in range(1, len(parts)):
                parent = "/".join(parts[:index])
                inspected_inventory.setdefault(
                    parent, {"kind": "directory", "sha256": _sha_bytes(b"")}
                )
            inspected_inventory[row["path"]] = {
                "kind": row["kind"], "sha256": row["sha256"]
            }
        if inspected_inventory != pre_inventory:
            findings.append(_finding(
                "ARCHIVE-EXTRACTED-INVENTORY-MISMATCH",
                "the extracted member inventory differs from the inspected immutable ZIP snapshot",
            ))
        runtime_script = extraction_root / RUNTIME_PROBE
        if not runtime_script.is_file():
            findings.append(_finding("ARCHIVE-RUNTIME-PROBE-MISSING", f"missing {RUNTIME_PROBE}"))
        child_env = {
            key: value
            for key, value in os.environ.items()
            if not key.upper().startswith("PYTHON")
        }
        child_env["PYTHONPATH"] = ""
        child_env["PYTHONDONTWRITEBYTECODE"] = "1"
        child_env["PYTHONNOUSERSITE"] = "1"
        child_env.pop("PYTHONHOME", None)
        inspect_argv = [
            sys.executable, "-I", "-B", "-c",
            "import json,sys;print(json.dumps(sys.path,separators=(',',':')))",
        ]
        inspected = subprocess.run(inspect_argv, cwd=extraction_root, env=child_env, capture_output=True, check=False)
        if inspected.returncode == 0:
            try:
                value = json.loads(inspected.stdout.decode("utf-8", errors="strict"))
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    sys_path = value
                    sys_path_observed = True
            except (UnicodeError, json.JSONDecodeError):
                pass
        dependency_paths = tuple(sorted({
            str(Path(path).resolve())
            for path in (*site.getsitepackages(), site.getusersitepackages())
            if path and Path(path).is_dir()
        }))
        isolated_runner = (
            "import runpy,site,sys;"
            f"[site.addsitedir(path) for path in {dependency_paths!r}];"
            f"sys.path.insert(0,{str(runtime_script.parent)!r});"
            f"sys.argv=[{str(runtime_script)!r},*sys.argv[1:]];"
            f"runpy.run_path({str(runtime_script)!r},run_name='__main__')"
        )
        argv = [
            sys.executable, "-I", "-B", "-c", isolated_runner,
            "--local-root", str(extraction_root),
            "--baseline-root", str(source_root),
            "--cleared-zip", str(snapshot_path),
            "--source-commit", source_commit,
            "--stdout",
        ]
        if runtime_script.is_file():
            completed = subprocess.run(argv, cwd=extraction_root, env=child_env, capture_output=True, check=False)
            try:
                loaded = json.loads(completed.stdout.decode("utf-8", errors="strict"))
                if isinstance(loaded, dict):
                    runtime_payload = loaded
            except (UnicodeError, json.JSONDecodeError):
                runtime_payload = None
        runtime_verdict = (
            runtime_payload.get("verdict")
            if runtime_payload is not None
            else None
        )
        if completed is None or runtime_payload is None:
            findings.append(_finding(
                "ARCHIVE-RUNTIME-PROBE-FAILED",
                "isolated runtime-plane probe did not produce a valid JSON receipt",
            ))
        else:
            runtime_schema_errors = _runtime_schema_errors(runtime_payload, source_root)
            provenance_sha256 = next(
                (
                    row["sha256"]
                    for row in member_records
                    if row["path"] == "PROVENANCE.json" and row["kind"] == "file"
                ),
                None,
            )
            if runtime_schema_errors:
                findings.append(_finding(
                    "ARCHIVE-RUNTIME-RECEIPT-SCHEMA",
                    "isolated runtime-plane receipt failed schema validation: "
                    + "; ".join(runtime_schema_errors),
                ))
            else:
                runtime_binding_errors = _runtime_binding_errors(
                    runtime_payload,
                    source_root=source_root,
                    extraction_root=extraction_root,
                    snapshot_path=snapshot_path,
                    archive_sha256=archive_snapshot_sha256,
                    archive_size=len(archive_snapshot),
                    provenance_sha256=provenance_sha256,
                    source_commit=source_commit,
                )
                if runtime_binding_errors:
                    findings.append(_finding(
                        "ARCHIVE-RUNTIME-RECEIPT-BINDING",
                        "isolated runtime-plane receipt failed outer binding checks: "
                        + "; ".join(runtime_binding_errors),
                    ))
                else:
                    runtime_payload_valid = True
        if runtime_payload_valid and completed.returncode == 0 and runtime_verdict == "qualified":
            runtime_result_accepted = True
        elif runtime_payload_valid and completed.returncode == 0 and runtime_verdict == "qualified_with_caveats":
            findings.append(_finding(
                "ARCHIVE-RUNTIME-PLANE-CAVEATED",
                "isolated runtime-plane receipt is qualified only with caveats",
            ))
        elif runtime_payload_valid and completed.returncode == 2 and runtime_verdict == "blocked":
            findings.append(_finding("ARCHIVE-RUNTIME-PLANE-BLOCKED", "isolated runtime-plane receipt is blocked"))
        elif runtime_payload_valid:
            findings.append(_finding(
                "ARCHIVE-RUNTIME-PROBE-FAILED",
                "isolated runtime-plane probe returned an inconsistent "
                f"return-code/verdict pair: {completed.returncode}/{runtime_verdict!r}",
            ))
        if not sys_path_observed:
            findings.append(_finding("ARCHIVE-RUNTIME-ISOLATION-PROBE", "isolated interpreter sys.path could not be observed"))

        runtime_stdout = completed.stdout if completed is not None else b""
        runtime_receipt_sha = _sha_bytes(runtime_stdout)
        post_inventory = _tree_inventory(extraction_root)
        post_digest = _digest(post_inventory)
        if pre_digest != post_digest:
            findings.append(_finding("ARCHIVE-RUNTIME-MUTATED", "extracted member tree changed during the runtime probe"))
        try:
            archive_changed = archive.read_bytes() != archive_snapshot
        except OSError:
            archive_changed = True
        if archive_changed:
            findings.append(_finding(
                "ARCHIVE-CHANGED-DURING-PROBE",
                "the public archive path changed after its immutable qualification snapshot was captured",
            ))

        source_in_sys_path = any(_inside(Path(item), source_root) for item in sys_path if item)
        source_isolation = {
            "source_root": str(source_root),
            "cwd_outside_source": not _inside(extraction_root, source_root),
            "extraction_outside_source": not _inside(extraction_root, source_root),
            "pythonpath_empty": child_env.get("PYTHONPATH") == "",
            "isolated_flag": "-I" in argv,
            "source_root_absent_from_sys_path": not source_in_sys_path,
            "interpreter_sys_path_observed": sys_path_observed,
            "interpreter_sys_path": sys_path,
        }
        if not all(
            source_isolation[key]
            for key in (
                "cwd_outside_source", "extraction_outside_source", "pythonpath_empty",
                "isolated_flag", "source_root_absent_from_sys_path",
                "interpreter_sys_path_observed",
            )
        ):
            findings.append(_finding("ARCHIVE-RUNTIME-SOURCE-ISOLATION", "runtime process retained an ambient source-checkout route"))

        runtime_execution = {
            "script": RUNTIME_PROBE,
            "argv": argv,
            "cwd": str(extraction_root),
            "environment": {
                "python_environment_policy": "scrub-all-restore-three-v1",
                "PYTHONPATH": "",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONNOUSERSITE": "1",
                "PYTHONHOME": None,
                "dependency_paths": list(dependency_paths),
            },
            "returncode": completed.returncode if completed is not None else None,
            "status": (
                "passed"
                if runtime_result_accepted
                else "failed"
            ),
            "stdout_sha256": _sha_bytes(completed.stdout if completed is not None else b""),
            "stderr_sha256": _sha_bytes(completed.stderr if completed is not None else b""),
        }
        runtime_plane_receipt = {
            "path": "stdout",
            "sha256": runtime_receipt_sha,
            "verdict": runtime_payload.get("verdict") if runtime_payload is not None else None,
            "retained": True,
            "stdout_base64": base64.b64encode(runtime_stdout).decode("ascii"),
            "payload": runtime_payload,
        }
    finally:
        shutil.rmtree(transaction_root, ignore_errors=False)

    cleanup = {
        "temporary_root_removed": not extraction_root.exists(),
        "cwd_removed": not extraction_root.exists(),
        "temporary_root_exists_after": extraction_root.exists(),
        "cwd_exists_after": extraction_root.exists(),
        "runtime_plane_receipt_retained": True,
    }
    if not cleanup["temporary_root_removed"] or not cleanup["cwd_removed"]:
        findings.append(_finding("ARCHIVE-RUNTIME-CLEANUP", "temporary runtime roots were not removed"))
    verdict = "blocked" if findings else "qualified"
    archive_binding = {
        "path": str(archive),
        "sha256": archive_snapshot_sha256,
        "size": len(archive_snapshot),
        "member_count": len(member_records),
    }
    digests = {"algorithm": DIGEST_ALGORITHM, "pre": pre_digest, "post": post_digest, "stable": pre_digest == post_digest}
    extraction = {
        "temporary_root": str(extraction_root),
        "created_new": True,
        "member_by_member": True,
        "targets_contained": True,
        "extracted_member_count": len(member_records),
    }
    unpacked: dict[str, Any] = {
        "schema_version": "1.1.0",
        "receipt_type": "unpacked_zip_runtime",
        "archive": archive_binding,
        "extraction": extraction,
        "runtime_execution": runtime_execution,
        "runtime_plane_receipt": runtime_plane_receipt,
        "member_digests": digests,
        "source_isolation": source_isolation,
        "cleanup": cleanup,
        "findings": findings,
        "verdict": verdict,
    }
    _validate(unpacked)
    unpacked_bytes = _canonical(unpacked)
    archive_receipt: dict[str, Any] = {
        "schema_version": "1.1.0",
        "receipt_type": "archive_runtime_probe",
        "archive": archive_binding,
        "central_directory": {
            "inspected_before_write": True,
            "members": member_records,
        },
        "extraction": extraction,
        "runtime_execution": runtime_execution,
        "runtime_plane_receipt": runtime_plane_receipt,
        "member_digests": digests,
        "source_isolation": source_isolation,
        "cleanup": cleanup,
        "unpacked_runtime_receipt": {
            "path": str(unpacked_runtime_path),
            "sha256": _sha_bytes(unpacked_bytes),
        },
        "findings": findings,
        "verdict": verdict,
    }
    _validate(archive_receipt)
    placed_unpacked = False
    try:
        _write_exclusive(unpacked_runtime_path, unpacked)
        placed_unpacked = True
        _write_exclusive(archive_receipt_path, archive_receipt)
    except Exception:
        if placed_unpacked:
            unpacked_runtime_path.unlink(missing_ok=True)
        raise
    return archive_receipt, unpacked


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--archive-receipt", type=Path, required=True)
    parser.add_argument("--unpacked-runtime", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        archive_receipt, _ = probe_archive(
            archive=args.archive,
            source_root=args.source_root,
            source_commit=args.source_commit,
            archive_receipt_path=args.archive_receipt,
            unpacked_runtime_path=args.unpacked_runtime,
        )
    except (ArchiveProbeRefusal, OSError, UnicodeError, json.JSONDecodeError) as exc:
        code = getattr(exc, "code", "ARCHIVE-RUNTIME-ERROR")
        print(json.dumps({"status": "refused", "code": code, "message": str(exc)}))
        return 2
    print(json.dumps({
        "status": archive_receipt["verdict"],
        "archive_receipt": str(args.archive_receipt.resolve()),
        "unpacked_runtime": str(args.unpacked_runtime.resolve()),
    }))
    return 0 if archive_receipt["verdict"] == "qualified" else 2


if __name__ == "__main__":
    raise SystemExit(main())
