#!/usr/bin/env python3
"""Focused synthetic checks for the deterministic release checksum writer."""

from __future__ import annotations

import errno
import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable

import destination_capability as destinations
import write_release_checksum as checksum

from write_release_checksum import (
    ChecksumError,
    validate_release_checksum,
    write_release_checksum,
)


SCRIPT = Path(__file__).with_name("write_release_checksum.py")
ZIP_NAME = "co-author-harness-claude-v0.39.0.zip"
ZIP_BYTES = b"synthetic deterministic release ZIP bytes\x00\x01\n"


def make_archive(root: Path, case: str, name: str = ZIP_NAME) -> Path:
    directory = root / case
    directory.mkdir(parents=True)
    archive = directory / name
    archive.write_bytes(ZIP_BYTES)
    return archive


def expect_refusal(label: str, call: Callable[[], object]) -> None:
    try:
        call()
    except ChecksumError:
        return
    raise AssertionError(f"{label}: checksum operation unexpectedly succeeded")


def expect_code(label: str, code: str, call: Callable[[], object]) -> None:
    try:
        call()
    except ChecksumError as exc:
        assert exc.code == code, (label, code, exc.code, str(exc))
        return
    raise AssertionError(f"{label}: checksum operation unexpectedly succeeded")


def assert_no_staging(archive: Path) -> None:
    sidecar = archive.with_suffix(".sha256")
    assert list(sidecar.parent.glob(sidecar.name + ".tmp.*")) == []


def main() -> int:
    cases = 0
    with tempfile.TemporaryDirectory(prefix="release-checksum-") as td:
        root = Path(td)

        archive = make_archive(root, "control")
        sidecar, zip_digest, sidecar_digest = write_release_checksum(archive)
        expected = hashlib.sha256(ZIP_BYTES).hexdigest()
        expected_bytes = f"{expected}  {ZIP_NAME}\n".encode("ascii")
        assert sidecar == archive.with_suffix(".sha256")
        assert sidecar.read_bytes() == expected_bytes
        assert zip_digest == expected
        assert sidecar_digest == hashlib.sha256(expected_bytes).hexdigest()
        assert validate_release_checksum(archive) == (zip_digest, sidecar_digest)
        before = (sidecar.stat().st_ino, sidecar.stat().st_mtime_ns, sidecar.read_bytes())
        assert write_release_checksum(archive) == (sidecar, zip_digest, sidecar_digest)
        after = (sidecar.stat().st_ino, sidecar.stat().st_mtime_ns, sidecar.read_bytes())
        assert after == before, "exact idempotent invocation rewrote the sidecar"
        cases += 1

        original_link = checksum._hard_link
        original_open = checksum._open_sidecar_exclusive
        original_direct_write = checksum._write_direct_payload

        def hard_link_unsupported(_source: Path, _destination: Path) -> None:
            raise OSError(errno.ENOTSUP, "synthetic hard-link capability unavailable")

        fallback_archive = make_archive(root, "exclusive_fallback")
        checksum._hard_link = hard_link_unsupported
        try:
            fallback_result = write_release_checksum(fallback_archive)
        finally:
            checksum._hard_link = original_link
        assert fallback_result[0].read_bytes() == expected_bytes
        assert validate_release_checksum(fallback_archive) == fallback_result[1:]
        assert_no_staging(fallback_archive)
        cases += 1

        unsupported_archive = make_archive(root, "no_publication_capability")

        def exclusive_unsupported(_path: Path) -> object:
            raise OSError(errno.ENOTSUP, "synthetic exclusive-create unavailable")

        checksum._hard_link = hard_link_unsupported
        checksum._open_sidecar_exclusive = exclusive_unsupported
        try:
            expect_code(
                "both_publication_capabilities_unavailable",
                checksum.CHECKSUM_PUBLICATION_UNSUPPORTED,
                lambda: write_release_checksum(unsupported_archive),
            )
        finally:
            checksum._hard_link = original_link
            checksum._open_sidecar_exclusive = original_open
        assert not unsupported_archive.with_suffix(".sha256").exists()
        assert_no_staging(unsupported_archive)
        cases += 1

        late_archive = make_archive(root, "late_hard_link_failure")

        def late_hard_link(source: Path, destination: Path) -> None:
            original_link(source, destination)
            raise OSError(errno.EIO, "synthetic failure after link publication")

        checksum._hard_link = late_hard_link
        try:
            expect_code(
                "late_hard_link_failure",
                checksum.CHECKSUM_PUBLICATION_PARTIAL,
                lambda: write_release_checksum(late_archive),
            )
        finally:
            checksum._hard_link = original_link
        assert not late_archive.with_suffix(".sha256").exists()
        assert_no_staging(late_archive)
        cases += 1

        short_archive = make_archive(root, "exclusive_short_write")

        def short_direct_write(handle: object, payload: bytes) -> None:
            handle.write(payload[:-1])
            handle.flush()
            os.fsync(handle.fileno())
            raise OSError("synthetic short exclusive write")

        checksum._hard_link = hard_link_unsupported
        checksum._write_direct_payload = short_direct_write
        try:
            expect_code(
                "exclusive_short_write",
                checksum.CHECKSUM_PUBLICATION_PARTIAL,
                lambda: write_release_checksum(short_archive),
            )
        finally:
            checksum._hard_link = original_link
            checksum._write_direct_payload = original_direct_write
        assert not short_archive.with_suffix(".sha256").exists()
        assert_no_staging(short_archive)
        cases += 1

        race_archive = make_archive(root, "appearance_race")
        raced_sidecar = race_archive.with_suffix(".sha256")
        foreign_bytes = b"foreign concurrent sidecar\n"

        def appearance_race(_source: Path, destination: Path) -> None:
            destination.write_bytes(foreign_bytes)
            raise FileExistsError(errno.EEXIST, "synthetic appearance race")

        checksum._hard_link = appearance_race
        try:
            expect_code(
                "appearance_race",
                checksum.CHECKSUM_PUBLICATION_CONCURRENT,
                lambda: write_release_checksum(race_archive),
            )
        finally:
            checksum._hard_link = original_link
        assert raced_sidecar.read_bytes() == foreign_bytes
        assert_no_staging(race_archive)
        cases += 1

        recovered_sidecar, recovered_zip, recovered_sidecar_hash = (
            write_release_checksum(short_archive)
        )
        recovered_before = (
            recovered_sidecar.stat().st_ino,
            recovered_sidecar.stat().st_mtime_ns,
            recovered_sidecar.read_bytes(),
        )
        assert write_release_checksum(short_archive) == (
            recovered_sidecar,
            recovered_zip,
            recovered_sidecar_hash,
        )
        assert (
            recovered_sidecar.stat().st_ino,
            recovered_sidecar.stat().st_mtime_ns,
            recovered_sidecar.read_bytes(),
        ) == recovered_before
        assert_no_staging(short_archive)
        cases += 1

        cli_archive = make_archive(root, "cli")
        write_run = subprocess.run(
            [sys.executable, str(SCRIPT), str(cli_archive)],
            text=True,
            encoding="utf-8",
            errors="strict",
            capture_output=True,
            check=False,
        )
        assert write_run.returncode == 0, write_run.stdout + write_run.stderr
        assert "RELEASE CHECKSUM: PASS" in write_run.stdout
        validate_run = subprocess.run(
            [sys.executable, str(SCRIPT), str(cli_archive), "--validate-only"],
            text=True,
            encoding="utf-8",
            errors="strict",
            capture_output=True,
            check=False,
        )
        assert validate_run.returncode == 0, validate_run.stdout + validate_run.stderr
        cases += 1

        malformed_payloads = {
            "uppercase_hash": expected.upper().encode("ascii") + b"  " + ZIP_NAME.encode() + b"\n",
            "single_space": f"{expected} {ZIP_NAME}\n".encode("ascii"),
            "asterisk_separator": f"{expected} *{ZIP_NAME}\n".encode("ascii"),
            "missing_newline": f"{expected}  {ZIP_NAME}".encode("ascii"),
            "extra_line": expected_bytes + b"extra\n",
            "wrong_basename": f"{expected}  another.zip\n".encode("ascii"),
            "wrong_hash": f"{'0' * 64}  {ZIP_NAME}\n".encode("ascii"),
        }
        for label, payload in malformed_payloads.items():
            malformed_archive = make_archive(root, f"malformed_{label}")
            malformed_sidecar = malformed_archive.with_suffix(".sha256")
            malformed_sidecar.write_bytes(payload)
            expect_refusal(
                label,
                lambda archive=malformed_archive: validate_release_checksum(archive),
            )
            expect_refusal(
                f"{label}_overwrite",
                lambda archive=malformed_archive: write_release_checksum(archive),
            )
            assert malformed_sidecar.read_bytes() == payload
            cases += 1

        changed_archive = make_archive(root, "changed_zip")
        changed_sidecar, _, _ = write_release_checksum(changed_archive)
        original_sidecar = changed_sidecar.read_bytes()
        changed_archive.write_bytes(ZIP_BYTES + b"changed")
        expect_refusal("changed_zip_validate", lambda: validate_release_checksum(changed_archive))
        expect_refusal("changed_zip_overwrite", lambda: write_release_checksum(changed_archive))
        assert changed_sidecar.read_bytes() == original_sidecar
        cases += 1

        unsafe_output_archive = make_archive(root, "unsafe_output")
        outside = root / "outside.sha256"
        expect_refusal(
            "noncanonical_output",
            lambda: write_release_checksum(unsafe_output_archive, outside),
        )
        assert not outside.exists()
        escaped = (
            unsafe_output_archive.parent
            / "nested"
            / ".."
            / unsafe_output_archive.with_suffix(".sha256").name
        )
        expect_refusal(
            "parent_escape_output",
            lambda: write_release_checksum(unsafe_output_archive, escaped),
        )
        assert not unsafe_output_archive.with_suffix(".sha256").exists()
        escaped_archive = (
            unsafe_output_archive.parent
            / "nested"
            / ".."
            / unsafe_output_archive.name
        )
        expect_refusal(
            "parent_escape_archive",
            lambda: write_release_checksum(escaped_archive),
        )
        cases += 3

        directory_archive = make_archive(root, "directory_output")
        directory_archive.with_suffix(".sha256").mkdir()
        expect_refusal("directory_output", lambda: write_release_checksum(directory_archive))
        cases += 1

        for index, name in enumerate(
            ["unsafe name.zip", "unsafe\nname.zip", "unicodé.zip", ".zip", "archive.ZIP"]
        ):
            unsafe_directory = root / f"unsafe_name_{index}"
            unsafe_directory.mkdir()
            unsafe_archive = unsafe_directory / name
            try:
                unsafe_archive.write_bytes(ZIP_BYTES)
            except OSError:
                # Some hosts refuse control characters at creation time.  The
                # writer must still reject the unsafe lexical input itself.
                pass
            expect_refusal(
                f"unsafe_archive_name_{index}",
                lambda archive=unsafe_archive: write_release_checksum(archive),
            )
            cases += 1

        symlink_output_archive = make_archive(root, "symlink_output")
        symlink_target = symlink_output_archive.parent / "external-sidecar.txt"
        symlink_target.write_bytes(b"do not modify\n")
        os.symlink(symlink_target, symlink_output_archive.with_suffix(".sha256"))
        expect_refusal(
            "symlink_output",
            lambda: write_release_checksum(symlink_output_archive),
        )
        assert symlink_target.read_bytes() == b"do not modify\n"
        cases += 1

        symlink_archive_target = make_archive(root, "symlink_archive_target")
        symlink_archive = root / "symlink-archive.zip"
        os.symlink(symlink_archive_target, symlink_archive)
        expect_refusal("symlink_archive", lambda: write_release_checksum(symlink_archive))
        cases += 1

        linked_target = root / "linked-target"
        linked_target.mkdir()
        linked_archive = linked_target / ZIP_NAME
        linked_archive.write_bytes(ZIP_BYTES)
        linked_parent = root / "linked-parent"
        os.symlink(linked_target, linked_parent, target_is_directory=True)
        expect_refusal(
            "symlink_parent",
            lambda: write_release_checksum(linked_parent / ZIP_NAME),
        )
        assert not (linked_target / Path(ZIP_NAME).with_suffix(".sha256")).exists()
        cases += 1

        if os.name == "nt":
            junction_target = root / "junction-target"
            junction_target.mkdir()
            junction_archive = junction_target / ZIP_NAME
            junction_archive.write_bytes(ZIP_BYTES)
            junction = root / "junction-parent"
            created = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(junction), str(junction_target)],
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                check=False,
            )
            assert created.returncode == 0, created.stdout + created.stderr
            try:
                expect_refusal(
                    "junction_parent",
                    lambda: write_release_checksum(junction / ZIP_NAME),
                )
                assert not junction_archive.with_suffix(".sha256").exists()
            finally:
                os.rmdir(junction)
            cases += 1

        protected = Path(__file__).resolve().parents[2] / "protected-release.zip"
        try:
            write_release_checksum(protected)
        except destinations.DestinationRefused as exc:
            assert exc.code == destinations.DEST_PROTECTED
        else:
            raise AssertionError("protected checksum destination accepted")
        cases += 1

    print(f"write_release_checksum_smoketest: PASS ({cases} focused cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
