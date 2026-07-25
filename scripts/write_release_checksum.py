#!/usr/bin/env python3
"""Write and read back one canonical SHA-256 sidecar for a release ZIP."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import stat
import sys
from pathlib import Path

import destination_capability as destinations


SAFE_ZIP_BASENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.zip$")
LOWER_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ChecksumError(RuntimeError):
    """The release checksum contract was not satisfied."""


def _is_link_or_reparse(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        attributes = getattr(os.lstat(path), "st_file_attributes", 0)
    except OSError:
        return False
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400)
    return bool(attributes & reparse_flag)


def _refuse_parent_reference(path: Path, label: str) -> None:
    if ".." in path.parts:
        raise ChecksumError(f"{label} contains a parent-directory escape")


def _absolute_without_links(path: Path, label: str) -> Path:
    _refuse_parent_reference(path, label)
    absolute = path.absolute()
    existing = absolute if absolute.exists() or absolute.is_symlink() else absolute.parent
    while True:
        if _is_link_or_reparse(existing):
            raise ChecksumError(f"{label} traverses a symlink or junction: {existing}")
        parent = existing.parent
        if parent == existing:
            break
        existing = parent
    return absolute


def _canonical_paths(
    archive: Path,
    output: Path | None,
) -> tuple[Path, Path]:
    archive = _absolute_without_links(archive, "release ZIP")
    if not SAFE_ZIP_BASENAME.fullmatch(archive.name):
        raise ChecksumError("release ZIP basename is unsafe or does not end in .zip")
    if not archive.is_file() or _is_link_or_reparse(archive):
        raise ChecksumError("release ZIP must be an existing plain file")
    canonical_output = archive.with_suffix(".sha256")
    requested_output = canonical_output if output is None else Path(output)
    requested_output = _absolute_without_links(requested_output, "checksum output")
    if requested_output != canonical_output:
        raise ChecksumError("checksum output must be the canonical sibling .sha256 path")
    if not requested_output.parent.is_dir():
        raise ChecksumError("checksum destination directory does not exist")
    if _is_link_or_reparse(requested_output.parent):
        raise ChecksumError("checksum destination is a symlink or junction")
    if requested_output.exists() and (
        not requested_output.is_file() or _is_link_or_reparse(requested_output)
    ):
        raise ChecksumError("checksum output is not a plain file")
    return archive, requested_output


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sidecar_bytes(digest: str, archive_basename: str) -> bytes:
    if not LOWER_SHA256.fullmatch(digest):
        raise ChecksumError("checksum digest is not one lowercase SHA-256")
    try:
        rendered = f"{digest}  {archive_basename}\n".encode("ascii")
    except UnicodeEncodeError as exc:
        raise ChecksumError("release ZIP basename is not ASCII") from exc
    return rendered


def validate_release_checksum(
    archive: Path,
    sidecar: Path | None = None,
) -> tuple[str, str]:
    """Validate exact sidecar bytes and a fresh read of the release ZIP."""
    archive, sidecar = _canonical_paths(Path(archive), sidecar)
    if not sidecar.is_file():
        raise ChecksumError("checksum sidecar is absent")
    digest = _sha256(archive)
    expected = _sidecar_bytes(digest, archive.name)
    try:
        actual = sidecar.read_bytes()
    except OSError as exc:
        raise ChecksumError(f"cannot read checksum sidecar: {exc}") from exc
    if actual != expected:
        raise ChecksumError(
            "checksum sidecar is malformed or does not match the live ZIP basename/hash"
        )
    sidecar_digest = hashlib.sha256(actual).hexdigest()
    if _sha256(archive) != digest or sidecar.read_bytes() != actual:
        raise ChecksumError("release ZIP or checksum sidecar changed during read-back")
    return digest, sidecar_digest


def write_release_checksum(
    archive: Path,
    output: Path | None = None,
) -> tuple[Path, str, str]:
    """Write the canonical sidecar once, then verify both files by read-back."""
    requested_archive = Path(archive)
    requested_sidecar = (
        Path(output) if output is not None else requested_archive.with_suffix(".sha256")
    )
    destinations.assert_writable(
        requested_sidecar, purpose="release checksum sidecar"
    )
    archive, sidecar = _canonical_paths(requested_archive, output)
    digest = _sha256(archive)
    payload = _sidecar_bytes(digest, archive.name)
    if sidecar.exists():
        if sidecar.read_bytes() != payload:
            raise ChecksumError("refusing to overwrite a non-identical checksum sidecar")
    else:
        temporary = sidecar.with_name(sidecar.name + f".tmp.{os.getpid()}")
        if temporary.exists() or temporary.is_symlink():
            raise ChecksumError("checksum temporary path already exists")
        try:
            with temporary.open("xb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.link(temporary, sidecar)
        except FileExistsError as exc:
            raise ChecksumError("checksum output appeared concurrently; refusing overwrite") from exc
        except OSError as exc:
            raise ChecksumError(f"cannot publish checksum sidecar: {exc}") from exc
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
    verified_digest, sidecar_digest = validate_release_checksum(archive, sidecar)
    return sidecar, verified_digest, sidecar_digest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.validate_only:
            archive_digest, sidecar_digest = validate_release_checksum(
                args.archive, args.output
            )
            sidecar = args.output or args.archive.with_suffix(".sha256")
        else:
            sidecar, archive_digest, sidecar_digest = write_release_checksum(
                args.archive, args.output
            )
    except (ChecksumError, destinations.DestinationRefused, OSError) as exc:
        print(f"[BLOCKER] release checksum refused: {exc}", file=sys.stderr)
        return 1
    print("RELEASE CHECKSUM: PASS")
    print(f"- ZIP SHA-256: {archive_digest}")
    print(f"- Sidecar: {sidecar}")
    print(f"- Sidecar SHA-256: {sidecar_digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
