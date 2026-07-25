#!/usr/bin/env python3
"""Safely extract one plugin archive and run its isolated runtime-plane probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
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
RUNTIME_PROBE = "scripts/runtime_plane_probe.py"
DIGEST_ALGORITHM = "sha256(path-NUL-kind-NUL-content-sha256-LF)"
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
    archive: Path,
) -> tuple[list[dict[str, Any]], dict[str, tuple[zipfile.ZipInfo, str]]]:
    """Inspect and decompress every member before any filesystem extraction."""
    records: list[dict[str, Any]] = []
    selected: dict[str, tuple[zipfile.ZipInfo, str]] = {}
    exact: set[str] = set()
    folded: dict[str, str] = {}
    kinds: dict[str, str] = {}
    try:
        with zipfile.ZipFile(archive, "r") as package:
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
    archive: Path,
    selected: Mapping[str, tuple[zipfile.ZipInfo, str]],
    root: Path,
) -> None:
    with zipfile.ZipFile(archive, "r") as package:
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


def _remove_probe_output(path: Path, extraction_root: Path, pre_dirs: set[str]) -> None:
    path.unlink(missing_ok=True)
    current = path.parent
    while current != extraction_root and _inside(current, extraction_root):
        relative = current.relative_to(extraction_root).as_posix()
        if relative in pre_dirs:
            break
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


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
    archive_receipt_path: Path,
    unpacked_runtime_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        raise ArchiveProbeRefusal("ARCHIVE-RUNTIME-ENV", "PYTHONDONTWRITEBYTECODE=1 is required")
    archive = archive.resolve(strict=True)
    source_root = source_root.resolve(strict=True)
    archive_receipt_path = archive_receipt_path.resolve()
    unpacked_runtime_path = unpacked_runtime_path.resolve()
    if not archive.is_file() or not source_root.is_dir():
        raise ArchiveProbeRefusal("ARCHIVE-INPUT", "archive and source root must exist")
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

    member_records, selected = _inspect_archive(archive)
    extraction_root = Path(tempfile.mkdtemp(prefix="coauthor-archive-runtime-")).resolve()
    runtime_receipt_path: Path | None = None
    pre_digest: dict[str, Any] | None = None
    post_digest: dict[str, Any] | None = None
    runtime_payload: dict[str, Any] | None = None
    completed: subprocess.CompletedProcess[bytes] | None = None
    sys_path: list[str] = []
    sys_path_observed = False
    findings: list[dict[str, str]] = []
    try:
        _extract_members(archive, selected, extraction_root)
        pre_inventory = _tree_inventory(extraction_root)
        pre_digest = _digest(pre_inventory)
        pre_dirs = {path for path, value in pre_inventory.items() if value["kind"] == "directory"}
        runtime_script = extraction_root / RUNTIME_PROBE
        if not runtime_script.is_file():
            findings.append(_finding("ARCHIVE-RUNTIME-PROBE-MISSING", f"missing {RUNTIME_PROBE}"))
        runtime_receipt_path = (
            extraction_root / "releases" / "verification"
            / f".archive-runtime-probe-{uuid.uuid4().hex}" / "runtime_plane.json"
        )
        child_env = dict(os.environ)
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
        argv = [
            sys.executable, "-I", "-B", str(runtime_script),
            "--local-root", str(extraction_root),
            "--baseline-root", str(extraction_root),
            "--out", str(runtime_receipt_path),
        ]
        if runtime_script.is_file():
            completed = subprocess.run(argv, cwd=extraction_root, env=child_env, capture_output=True, check=False)
            if runtime_receipt_path.is_file():
                try:
                    loaded = json.loads(runtime_receipt_path.read_text(encoding="utf-8"))
                    if isinstance(loaded, dict):
                        runtime_payload = loaded
                except (OSError, UnicodeError, json.JSONDecodeError):
                    runtime_payload = None
        if completed is None or completed.returncode != 0 or runtime_payload is None:
            findings.append(_finding("ARCHIVE-RUNTIME-PROBE-FAILED", "isolated runtime-plane probe did not produce a successful JSON receipt"))
        elif runtime_payload.get("verdict") == "blocked":
            findings.append(_finding("ARCHIVE-RUNTIME-PLANE-BLOCKED", "isolated runtime-plane receipt is blocked"))
        if not sys_path_observed:
            findings.append(_finding("ARCHIVE-RUNTIME-ISOLATION-PROBE", "isolated interpreter sys.path could not be observed"))

        runtime_receipt_sha = _sha_path(runtime_receipt_path) if runtime_receipt_path.is_file() else None
        _remove_probe_output(runtime_receipt_path, extraction_root, pre_dirs)
        post_inventory = _tree_inventory(extraction_root)
        post_digest = _digest(post_inventory)
        if pre_digest != post_digest:
            findings.append(_finding("ARCHIVE-RUNTIME-MUTATED", "extracted member tree changed during the runtime probe"))

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
                "PYTHONPATH": "",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONNOUSERSITE": "1",
                "PYTHONHOME": None,
            },
            "returncode": completed.returncode if completed is not None else None,
            "status": (
                "passed"
                if completed is not None and completed.returncode == 0 and runtime_payload is not None
                and runtime_payload.get("verdict") != "blocked"
                else "failed"
            ),
            "stdout_sha256": _sha_bytes(completed.stdout if completed is not None else b""),
            "stderr_sha256": _sha_bytes(completed.stderr if completed is not None else b""),
        }
        runtime_plane_receipt = {
            "path": str(runtime_receipt_path),
            "sha256": runtime_receipt_sha,
            "verdict": runtime_payload.get("verdict") if runtime_payload is not None else None,
            "retained": False,
        }
    finally:
        shutil.rmtree(extraction_root, ignore_errors=False)

    cleanup = {
        "temporary_root_removed": not extraction_root.exists(),
        "cwd_removed": not extraction_root.exists(),
        "temporary_root_exists_after": extraction_root.exists(),
        "cwd_exists_after": extraction_root.exists(),
        "runtime_plane_receipt_retained": bool(runtime_receipt_path and runtime_receipt_path.exists()),
    }
    if not cleanup["temporary_root_removed"] or not cleanup["cwd_removed"]:
        findings.append(_finding("ARCHIVE-RUNTIME-CLEANUP", "temporary runtime roots were not removed"))
    verdict = "blocked" if findings else "qualified"
    archive_binding = {
        "path": str(archive),
        "sha256": _sha_path(archive),
        "size": archive.stat().st_size,
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
        "schema_version": "1.0.0",
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
        "schema_version": "1.0.0",
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
    parser.add_argument("--archive-receipt", type=Path, required=True)
    parser.add_argument("--unpacked-runtime", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        archive_receipt, _ = probe_archive(
            archive=args.archive,
            source_root=args.source_root,
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
