#!/usr/bin/env python3
"""Focused safe-extraction and isolated-runtime tests for archive_runtime_probe."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import uuid
import warnings
import zipfile
from pathlib import Path
from typing import Callable

from jsonschema import Draft202012Validator


if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1" or not sys.dont_write_bytecode:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [sys.executable, "-B", __file__, *sys.argv[1:]],
        env=environment,
        check=False,
    )
    raise SystemExit(completed.returncode)


import archive_runtime_probe as probe  # noqa: E402


ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "references" / "schemas" / "archive_runtime_receipt.schema.json"

RUNTIME_STUB = b'''#!/usr/bin/env python3
import argparse,json,jsonschema,os,sys
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument("--local-root",type=Path,required=True)
parser.add_argument("--baseline-root",type=Path,required=True)
parser.add_argument("--stdout",action="store_true",required=True)
args=parser.parse_args()
if "-I" not in sys.orig_argv or os.environ.get("PYTHONPATH") != "" or os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
    raise SystemExit(9)
print(json.dumps({"verdict":"qualified","isolated":True},sort_keys=True))
'''

MUTATING_RUNTIME_STUB = RUNTIME_STUB + b'''\n(args.local_root / "runtime-mutation.txt").write_text("mutated\\n",encoding="utf-8")\n'''


def _info(name: str, *, directory: bool = False, symlink: bool = False) -> zipfile.ZipInfo:
    value = zipfile.ZipInfo(name)
    # ZipInfo normalizes the host separator during construction on Windows.
    # Reset both fields so the fixture carries the unsafe archive bytes that a
    # non-Windows producer can place in a ZIP central directory.
    value.filename = name
    value.orig_filename = name
    value.create_system = 3
    if symlink:
        value.external_attr = (stat.S_IFLNK | 0o777) << 16
    elif directory:
        value.external_attr = (stat.S_IFDIR | 0o755) << 16
    else:
        value.external_attr = (stat.S_IFREG | 0o644) << 16
    return value


def _write_archive(path: Path, members: list[tuple[zipfile.ZipInfo | str, bytes]]) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as package:
            for name, content in members:
                package.writestr(name, content)


def _safe_members(runtime: bytes = RUNTIME_STUB) -> list[tuple[zipfile.ZipInfo | str, bytes]]:
    return [
        (_info(".claude-plugin/", directory=True), b""),
        (_info(".claude-plugin/plugin.json"), b'{"name":"fixture","version":"1.0.0"}\n'),
        (_info("scripts/", directory=True), b""),
        (_info("scripts/runtime_plane_probe.py"), runtime),
        (_info("PROVENANCE.json"), b'{"schema":"co-author-harness-build-provenance/1"}\n'),
        (_info("payload.txt"), b"safe payload\n"),
    ]


def _validate(value: dict) -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda error: list(error.path))
    assert not errors, "; ".join(f"{list(error.path)}: {error.message}" for error in errors)


def _expect_refusal(
    archive: Path,
    out_root: Path,
    expected_code: str,
) -> None:
    archive_receipt = out_root / f"{archive.stem}-archive.json"
    runtime_receipt = out_root / f"{archive.stem}-runtime.json"
    try:
        probe.probe_archive(
            archive=archive,
            source_root=ROOT,
            archive_receipt_path=archive_receipt,
            unpacked_runtime_path=runtime_receipt,
        )
    except probe.ArchiveProbeRefusal as exc:
        assert exc.code == expected_code, (expected_code, exc.code, exc.message)
    else:
        raise AssertionError(f"unsafe archive was accepted: {archive.name}")
    assert not archive_receipt.exists()
    assert not runtime_receipt.exists()


def main() -> int:
    assert os.environ.get("PYTHONDONTWRITEBYTECODE") == "1"
    evidence_parent = ROOT / "releases" / "verification"
    evidence_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="archive-runtime-smoke-") as td, tempfile.TemporaryDirectory(
        prefix=f".archive-runtime-smoke-{uuid.uuid4().hex}-", dir=evidence_parent
    ) as evidence_td:
        base = Path(td)
        outputs = Path(evidence_td)

        safe_archive = base / "safe.zip"
        _write_archive(safe_archive, _safe_members())
        archive_out = outputs / "archive_receipt.json"
        runtime_out = outputs / "unpacked_zip_runtime.json"
        archive_receipt, runtime_receipt = probe.probe_archive(
            archive=safe_archive,
            source_root=ROOT,
            archive_receipt_path=archive_out,
            unpacked_runtime_path=runtime_out,
        )
        _validate(archive_receipt)
        _validate(runtime_receipt)
        assert json.loads(archive_out.read_text(encoding="utf-8")) == archive_receipt
        assert json.loads(runtime_out.read_text(encoding="utf-8")) == runtime_receipt
        assert archive_receipt["verdict"] == "qualified"
        assert runtime_receipt["verdict"] == "qualified"
        assert archive_receipt["central_directory"]["inspected_before_write"] is True
        assert archive_receipt["member_digests"]["stable"] is True
        assert runtime_receipt["runtime_execution"]["argv"][1:3] == ["-I", "-B"]
        assert runtime_receipt["runtime_execution"]["environment"]["PYTHONPATH"] == ""
        assert runtime_receipt["runtime_execution"]["environment"]["dependency_paths"]
        assert runtime_receipt["source_isolation"]["source_root_absent_from_sys_path"] is True
        assert runtime_receipt["source_isolation"]["interpreter_sys_path_observed"] is True
        assert runtime_receipt["cleanup"] == {
            "temporary_root_removed": True,
            "cwd_removed": True,
            "temporary_root_exists_after": False,
            "cwd_exists_after": False,
            "runtime_plane_receipt_retained": False,
        }
        assert not Path(runtime_receipt["extraction"]["temporary_root"]).exists()
        assert not Path(runtime_receipt["runtime_execution"]["cwd"]).exists()
        assert archive_receipt["unpacked_runtime_receipt"]["sha256"] == probe._sha_path(runtime_out)

        cases: list[tuple[str, list[tuple[zipfile.ZipInfo | str, bytes]], str]] = [
            ("exact-duplicate", [(_info("same.txt"), b"a"), (_info("same.txt"), b"b")], "ARCHIVE-MEMBER-DUPLICATE"),
            ("casefold-duplicate", [(_info("Case.txt"), b"a"), (_info("case.TXT"), b"b")], "ARCHIVE-MEMBER-CASEFOLD-DUPLICATE"),
            ("absolute", [(_info("/absolute.txt"), b"x")], "ARCHIVE-MEMBER-ABSOLUTE"),
            ("drive", [(_info("C:/drive.txt"), b"x")], "ARCHIVE-MEMBER-ABSOLUTE"),
            ("unc", [(_info("//server/share.txt"), b"x")], "ARCHIVE-MEMBER-ABSOLUTE"),
            ("traversal", [(_info("../escape.txt"), b"x")], "ARCHIVE-MEMBER-TRAVERSAL"),
            ("separator", [(_info("unsafe\\name.txt"), b"x")], "ARCHIVE-MEMBER-SEPARATOR"),
            ("symlink", [(_info("link", symlink=True), b"payload.txt")], "ARCHIVE-MEMBER-SYMLINK"),
            ("nested", [(_info("payload.ZIP"), b"not a zip")], "ARCHIVE-MEMBER-NESTED"),
            ("kind-collision", [(_info("parent"), b"file"), (_info("parent/child.txt"), b"child")], "ARCHIVE-MEMBER-KIND-COLLISION"),
        ]
        for name, members, code in cases:
            archive = base / f"{name}.zip"
            _write_archive(archive, members)
            _expect_refusal(archive, outputs, code)

        mutating_archive = base / "mutating-runtime.zip"
        _write_archive(mutating_archive, _safe_members(MUTATING_RUNTIME_STUB))
        mutating_archive_out = outputs / "mutating-archive.json"
        mutating_runtime_out = outputs / "mutating-runtime.json"
        blocked_archive, blocked_runtime = probe.probe_archive(
            archive=mutating_archive,
            source_root=ROOT,
            archive_receipt_path=mutating_archive_out,
            unpacked_runtime_path=mutating_runtime_out,
        )
        _validate(blocked_archive)
        _validate(blocked_runtime)
        assert blocked_archive["verdict"] == "blocked"
        assert blocked_runtime["member_digests"]["stable"] is False
        assert any(row["code"] == "ARCHIVE-RUNTIME-MUTATED" for row in blocked_runtime["findings"])
        assert blocked_runtime["cleanup"]["temporary_root_removed"] is True

    print("archive_runtime_probe_smoketest: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
