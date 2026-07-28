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
CHECKSUM_PUBLICATION_UNSUPPORTED = "CHECKSUM-PUBLICATION-UNSUPPORTED"
CHECKSUM_PUBLICATION_PARTIAL = "CHECKSUM-PUBLICATION-PARTIAL"
CHECKSUM_PUBLICATION_CONCURRENT = "CHECKSUM-PUBLICATION-CONCURRENT"
CHECKSUM_INVALID = "CHECKSUM-INVALID"


class ChecksumError(RuntimeError):
    """The release checksum contract was not satisfied."""

    def __init__(self, message: str, *, code: str = CHECKSUM_INVALID) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def _publication_error(code: str, message: str) -> ChecksumError:
    return ChecksumError(message, code=code)


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


def _file_identity_from_handle(handle: object) -> tuple[int, int]:
    value = os.fstat(handle.fileno())
    return value.st_dev, value.st_ino


def _same_identity(path: Path, identity: tuple[int, int]) -> bool:
    try:
        value = os.stat(path, follow_symlinks=False)
    except OSError:
        return False
    return not _is_link_or_reparse(path) and (value.st_dev, value.st_ino) == identity


def _remove_owned(path: Path, identity: tuple[int, int]) -> None:
    """Remove only the file created by this transaction."""

    if not path.exists() and not path.is_symlink():
        return
    if not _same_identity(path, identity):
        raise _publication_error(
            CHECKSUM_PUBLICATION_PARTIAL,
            f"refusing to remove checksum path whose identity changed: {path}",
        )
    try:
        path.unlink()
    except OSError as exc:
        raise _publication_error(
            CHECKSUM_PUBLICATION_PARTIAL,
            f"cannot remove partial checksum publication: {exc}",
        ) from exc


def _write_and_sync(handle: object, payload: bytes) -> None:
    written = handle.write(payload)
    if written != len(payload):
        raise OSError(f"short checksum write: expected {len(payload)}, wrote {written}")
    handle.flush()
    os.fsync(handle.fileno())


def _hard_link(source: Path, destination: Path) -> None:
    os.link(source, destination)


def _open_sidecar_exclusive(path: Path) -> object:
    """Capability seam: exclusive create with read-back on the same handle."""

    return path.open("x+b")


def _write_direct_payload(handle: object, payload: bytes) -> None:
    _write_and_sync(handle, payload)


def _publish_exclusive(sidecar: Path, payload: bytes) -> tuple[int, int]:
    """Publish directly only when the filesystem proves exclusive-create."""

    created = False
    identity: tuple[int, int] | None = None
    try:
        with _open_sidecar_exclusive(sidecar) as handle:
            created = True
            identity = _file_identity_from_handle(handle)
            _write_direct_payload(handle, payload)
            handle.seek(0)
            if handle.read() != payload:
                raise OSError("exclusive checksum read-back differs from requested bytes")
        assert identity is not None
        if not _same_identity(sidecar, identity):
            raise _publication_error(
                CHECKSUM_PUBLICATION_PARTIAL,
                "exclusive checksum path identity changed before publication completed",
            )
        return identity
    except FileExistsError as exc:
        if created and identity is not None:
            _remove_owned(sidecar, identity)
            raise _publication_error(
                CHECKSUM_PUBLICATION_PARTIAL,
                f"exclusive checksum publication failed after creation: {exc}",
            ) from exc
        raise _publication_error(
            CHECKSUM_PUBLICATION_CONCURRENT,
            "checksum output appeared concurrently; refusing overwrite",
        ) from exc
    except ChecksumError:
        if created and identity is not None:
            _remove_owned(sidecar, identity)
        raise
    except OSError as exc:
        if created and identity is not None:
            _remove_owned(sidecar, identity)
            raise _publication_error(
                CHECKSUM_PUBLICATION_PARTIAL,
                f"exclusive checksum publication failed after creation: {exc}",
            ) from exc
        raise _publication_error(
            CHECKSUM_PUBLICATION_UNSUPPORTED,
            f"filesystem provides neither hard-link nor exclusive-create publication: {exc}",
        ) from exc


def _publish_new_sidecar(sidecar: Path, payload: bytes) -> tuple[int, int]:
    """Publish by hard link, with an exclusive-create portability fallback."""

    temporary = sidecar.with_name(sidecar.name + f".tmp.{os.getpid()}")
    if temporary.exists() or temporary.is_symlink():
        raise ChecksumError("checksum temporary path already exists")
    temporary_identity: tuple[int, int] | None = None
    link_succeeded = False
    try:
        try:
            with temporary.open("xb") as handle:
                temporary_identity = _file_identity_from_handle(handle)
                _write_and_sync(handle, payload)
        except OSError as exc:
            if temporary_identity is not None:
                _remove_owned(temporary, temporary_identity)
            raise _publication_error(
                CHECKSUM_PUBLICATION_PARTIAL,
                f"checksum staging publication failed: {exc}",
            ) from exc
        try:
            _hard_link(temporary, sidecar)
            link_succeeded = True
        except FileExistsError as exc:
            if temporary_identity is not None and _same_identity(
                sidecar, temporary_identity
            ):
                _remove_owned(sidecar, temporary_identity)
                raise _publication_error(
                    CHECKSUM_PUBLICATION_PARTIAL,
                    f"hard-link publication failed after creating the sidecar: {exc}",
                ) from exc
            raise _publication_error(
                CHECKSUM_PUBLICATION_CONCURRENT,
                "checksum output appeared concurrently; refusing overwrite",
            ) from exc
        except OSError as exc:
            if sidecar.exists() or sidecar.is_symlink():
                if temporary_identity is not None and _same_identity(
                    sidecar, temporary_identity
                ):
                    _remove_owned(sidecar, temporary_identity)
                    raise _publication_error(
                        CHECKSUM_PUBLICATION_PARTIAL,
                        f"hard-link publication failed after creating the sidecar: {exc}",
                    ) from exc
                raise _publication_error(
                    CHECKSUM_PUBLICATION_CONCURRENT,
                    "checksum output appeared during failed hard-link publication",
                ) from exc
            # The link operation is unavailable. Remove staging first, then
            # require the destination filesystem to prove O_EXCL semantics.
            assert temporary_identity is not None
            _remove_owned(temporary, temporary_identity)
            temporary_identity = None
            return _publish_exclusive(sidecar, payload)
        assert temporary_identity is not None
        if not _same_identity(sidecar, temporary_identity):
            raise _publication_error(
                CHECKSUM_PUBLICATION_PARTIAL,
                "hard-link checksum publication did not preserve file identity",
            )
        return temporary_identity
    finally:
        if temporary_identity is not None and (
            temporary.exists() or temporary.is_symlink()
        ):
            _remove_owned(temporary, temporary_identity)
        if not link_succeeded and temporary.exists():
            # Defensive invariant only: never leave transaction-created staging.
            raise _publication_error(
                CHECKSUM_PUBLICATION_PARTIAL,
                f"checksum staging artifact remains after refusal: {temporary}",
            )


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
        owned_identity = None
    else:
        owned_identity = _publish_new_sidecar(sidecar, payload)
    try:
        verified_digest, sidecar_digest = validate_release_checksum(archive, sidecar)
    except (ChecksumError, OSError) as exc:
        if owned_identity is not None:
            _remove_owned(sidecar, owned_identity)
            raise _publication_error(
                CHECKSUM_PUBLICATION_PARTIAL,
                f"checksum publication failed final read-back: {exc}",
            ) from exc
        raise
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
