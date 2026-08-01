#!/usr/bin/env python3
"""Focused safe-extraction and isolated-runtime tests for archive_runtime_probe."""

from __future__ import annotations

import base64
import json
import os
import stat
import subprocess
import sys
import tempfile
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

RUNTIME_STUB_TEMPLATE = r'''#!/usr/bin/env python3
import argparse,hashlib,json,jsonschema,os,sys,zipfile
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument("--local-root",type=Path,required=True)
parser.add_argument("--baseline-root",type=Path,required=True)
parser.add_argument("--cleared-zip",type=Path,required=True)
parser.add_argument("--source-commit",required=True)
parser.add_argument("--plane-kind",choices=("unpacked","installed_cache"),required=True)
parser.add_argument("--topology-receipt",type=Path,required=True)
parser.add_argument("--stdout",action="store_true",required=True)
args=parser.parse_args()
allowed_python={"PYTHONPATH","PYTHONDONTWRITEBYTECODE","PYTHONNOUSERSITE"}
unexpected_python=sorted(key for key in os.environ if key.upper().startswith("PYTHON") and key.upper() not in allowed_python)
if "-I" not in sys.orig_argv or os.environ.get("PYTHONPATH") != "" or os.environ.get("PYTHONDONTWRITEBYTECODE") != "1" or os.environ.get("PYTHONNOUSERSITE") != "1" or unexpected_python:
    raise SystemExit(9)
if not args.cleared_zip.is_file() or len(args.source_commit) not in (40,64):
    raise SystemExit(10)
verdict="__VERDICT__"
zero="0"*64
archive_bytes=args.cleared_zip.read_bytes()
archive_sha256=hashlib.sha256(archive_bytes).hexdigest()
topology_sha256=hashlib.sha256(args.topology_receipt.read_bytes()).hexdigest()
with zipfile.ZipFile(args.cleared_zip,"r") as package:
    provenance_sha256=hashlib.sha256(package.read("PROVENANCE.json")).hexdigest()
manifest={"path":".claude-plugin/plugin.json","status":"valid","name":"fixture","version":"1.0.0","base_version":"1.0.0","host_suffix":None,"sha256":zero}
source_provenance={"kind":"source_git","path":None,"status":"valid","schema":None,"commit":args.source_commit,"sha256":zero}
embedded_provenance={"kind":"embedded_archive","path":"PROVENANCE.json","status":"valid","schema":"co-author-harness-build-provenance/1","commit":args.source_commit,"sha256":zero}
digest={"algorithm":"sha256(path-NUL-kind-NUL-content-sha256-LF)","sha256":zero,"file_count":0}
findings=[]
if verdict=="qualified_with_caveats":
    findings=[{"code":"RUNTIME-PLANE-EMBEDDED-PROVENANCE-MISSING","severity":"WARNING","message":"synthetic caveat"}]
elif verdict=="blocked":
    findings=[{"code":"RUNTIME-PLANE-SEMANTIC-DIFFERENCE","severity":"BLOCKER","message":"synthetic blocker"}]
payload={
 "schema_version":"1.1.0","receipt_type":"runtime_plane_probe","plane_kind":args.plane_kind,"topology_receipt":{"sha256":topology_sha256,"source_commit":args.source_commit,"plane_kind":args.plane_kind},"baseline_root":str(args.baseline_root),"local_root":str(args.local_root),
 "environment":{"pythondontwritebytecode":"1","isolated_python":True,"python_environment_policy":"scrub-all-restore-three-v1","ambient_pythonpath":"","suite_pythonpath":"","suite_pythonno_usersite":"1","suite_pythonhome":None,"dependency_paths":[]},
 "interpreter":{"executable":sys.executable,"implementation":"CPython","version":"3","version_info":[3,14,2],"platform":"test"},
 "tool_versions":{"python":"3","jsonschema":"test","referencing":"test","pyyaml":"test","git":"test"},
 "identity":{"source":{"manifest":manifest,"provenance":source_provenance},"embedded":{"manifest":manifest,"provenance":embedded_provenance},"version_match":True,"exact_version_match":True,"provenance_match":True,"canonical_archive_claim":verdict=="qualified"},
 "cleared_zip":{"path":str(args.cleared_zip),"sha256":archive_sha256,"byte_length":len(archive_bytes),"source_commit":args.source_commit,"provenance_sha256":provenance_sha256},
 "normalization_policy":{"policy_id":"runtime-plane-normalization-v1","crlf_mode":"forbid","semantic_differences_block":True,"blocking_extras_block":True},
 "cache_state":"CACHE_PROVENANCE_CONTAMINATED" if verdict=="blocked" else "CODEX_CACHE_QUALIFIED",
 "exact_files":[],"crlf_only":[],"semantic_differences":[],"missing_files":[],"foreign_extras":[],
 "package_digests":{"baseline":digest,"pre":digest,"post":digest,"stable":True},
 "suites":[
  {"name":"governed_product_gate_self_check","kind":"governed_product_gate_self_check","script":"scripts/run_product_gate_smoketest.py","argv":[sys.executable,"-I"],"cwd":str(args.local_root),"returncode":0,"status":"passed","stdout_sha256":zero,"stderr_sha256":zero},
  {"name":"schema_runtime_check","kind":"portable_core","script":"scripts/schema_runtime_check.py","argv":[sys.executable,"-I"],"cwd":str(args.local_root),"returncode":0,"status":"passed","stdout_sha256":zero,"stderr_sha256":zero},
  {"name":"version_check","kind":"portable_core","script":"scripts/version-check.py","argv":[sys.executable,"-I"],"cwd":str(args.local_root),"returncode":0,"status":"passed","stdout_sha256":zero,"stderr_sha256":zero},
  {"name":"skill_check","kind":"portable_core","script":"scripts/skill-check.py","argv":[sys.executable,"-I"],"cwd":str(args.local_root),"returncode":0,"status":"passed","stdout_sha256":zero,"stderr_sha256":zero},
  {"name":"shipment_manifest_v2_smoketest","kind":"portable_core","script":"scripts/shipment_manifest_smoketest.py","argv":[sys.executable,"-I"],"cwd":str(args.local_root),"returncode":0,"status":"passed","stdout_sha256":zero,"stderr_sha256":zero},
  {"name":"output_contract_v3_smoketest","kind":"portable_core","script":"scripts/output_contract_smoketest.py","argv":[sys.executable,"-I"],"cwd":str(args.local_root),"returncode":0,"status":"passed","stdout_sha256":zero,"stderr_sha256":zero},
 ],
 "findings":findings,"verdict":verdict,
}
__MUTATION__
if __MALFORMED__:
    print("not-json")
else:
    print(json.dumps(payload,sort_keys=True))
if __RETURN_CODE__:
    raise SystemExit(__RETURN_CODE__)
'''


def _runtime_stub(
    verdict: str = "qualified",
    *,
    return_code: int = 0,
    malformed: bool = False,
    mutation: str = "pass",
) -> bytes:
    return (
        RUNTIME_STUB_TEMPLATE
        .replace("__VERDICT__", verdict)
        .replace("__RETURN_CODE__", str(return_code))
        .replace("__MALFORMED__", "True" if malformed else "False")
        .replace("__MUTATION__", mutation)
        .encode("utf-8")
    )


RUNTIME_STUB = _runtime_stub()
QUALIFIED_WITH_CAVEATS_RUNTIME_STUB = _runtime_stub("qualified_with_caveats")
BLOCKED_RUNTIME_STUB = _runtime_stub("blocked", return_code=2)
BLOCKED_ZERO_RUNTIME_STUB = _runtime_stub("blocked")
QUALIFIED_TWO_RUNTIME_STUB = _runtime_stub("qualified", return_code=2)
MALFORMED_RUNTIME_STUB = _runtime_stub(malformed=True)
WRONG_ZIP_HASH_RUNTIME_STUB = _runtime_stub(
    mutation='payload["cleared_zip"]["sha256"]="0"*64'
)
WRONG_ZIP_SIZE_RUNTIME_STUB = _runtime_stub(
    mutation='payload["cleared_zip"]["byte_length"]+=1'
)
WRONG_COMMIT_RUNTIME_STUB = _runtime_stub(
    mutation='payload["cleared_zip"]["source_commit"]="f"*40'
)
MISSING_SUITE_RUNTIME_STUB = _runtime_stub(
    mutation='payload["suites"]=payload["suites"][:-1]'
)
SCHEMA_INVALID_RUNTIME_STUB = RUNTIME_STUB.replace(
    b"print(json.dumps(payload,sort_keys=True))",
    b'print(json.dumps({"verdict":"qualified","isolated":True},sort_keys=True))',
)
WRONG_TYPE_RUNTIME_STUB = RUNTIME_STUB.replace(
    b"print(json.dumps(payload,sort_keys=True))",
    b'payload["environment"]=[]\n    print(json.dumps(payload,sort_keys=True))',
)
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


def _source_commit(root: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        check=True,
    )
    return completed.stdout.strip()


def _clean_source_fixture(base: Path) -> Path:
    source = base / "source"
    schema = source / "references/schemas/runtime_plane_receipt.schema.json"
    schema.parent.mkdir(parents=True)
    schema.write_bytes((ROOT / "references/schemas/runtime_plane_receipt.schema.json").read_bytes())
    subprocess.run(["git", "init", "--quiet", "-b", "main"], cwd=source, check=True)
    subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=source, check=True)
    subprocess.run(["git", "config", "user.name", "Fixture"], cwd=source, check=True)
    subprocess.run(["git", "add", "."], cwd=source, check=True)
    subprocess.run(["git", "commit", "--quiet", "-m", "source"], cwd=source, check=True)
    return source


def _topology_receipt(archive: Path, source_root: Path, source_commit: str) -> dict:
    base = archive.parent / f"topology-{archive.stem}"
    paths = {
        "source": source_root,
        "build": base / "build",
        "archive": archive,
        "unpacked": base / "unpacked",
        "installed_cache": base / "installed-cache",
    }
    build = paths["build"]
    subprocess.run(
        ["git", "clone", "--quiet", "--no-local", str(source_root), str(build)], check=True,
    )
    subprocess.run(["git", "checkout", "--quiet", "--detach", source_commit], cwd=build, check=True)
    for kind in ("unpacked", "installed_cache"):
        paths[kind].mkdir(parents=True, exist_ok=True)
    records = []
    for kind in probe.topology.PLANE_KINDS:
        records.append({
            "plane_kind": kind,
            "path": str(paths[kind].resolve()),
            "path_kind": "file" if kind == "archive" else "directory",
            "digest_sha256": probe.topology.plane_digest(kind, paths[kind]),
            "git_commit": source_commit if kind in {"source", "build"} else None,
            "git_state": "source_main" if kind == "source" else "detached_clean" if kind == "build" else "absent",
            "provenance_commit": source_commit if kind in {"archive", "unpacked", "installed_cache"} else None,
        })
    return {
        "schema_version": "1.0.0", "receipt_type": "qualification_plane_topology",
        "source_commit": source_commit, "planes": records, "source_stable": True,
        "findings": [], "verdict": "qualified",
    }


def _expect_refusal(
    archive: Path,
    out_root: Path,
    expected_code: str,
    source_root: Path,
    source_commit: str,
) -> None:
    archive_receipt = out_root / f"{archive.stem}-archive.json"
    runtime_receipt = out_root / f"{archive.stem}-runtime.json"
    try:
        probe.probe_archive(
            archive=archive,
            source_root=source_root,
            source_commit=source_commit,
            archive_receipt_path=archive_receipt,
            unpacked_runtime_path=runtime_receipt,
            topology_receipt=_topology_receipt(archive, source_root, source_commit),
        )
    except probe.ArchiveProbeRefusal as exc:
        assert exc.code == expected_code, (expected_code, exc.code, exc.message)
    else:
        raise AssertionError(f"unsafe archive was accepted: {archive.name}")
    assert not archive_receipt.exists()
    assert not runtime_receipt.exists()


def main() -> int:
    assert os.environ.get("PYTHONDONTWRITEBYTECODE") == "1"
    with tempfile.TemporaryDirectory(prefix="archive-runtime-smoke-") as td:
        base = Path(td)
        source_root = _clean_source_fixture(base)
        source_commit = _source_commit(source_root)
        outputs = base / "outputs"
        outputs.mkdir()

        safe_archive = base / "safe.zip"
        _write_archive(safe_archive, _safe_members())
        try:
            probe.probe_archive(
                archive=safe_archive,
                source_root=source_root,
                source_commit=source_commit,
                archive_receipt_path=outputs / "missing-topology-archive.json",
                unpacked_runtime_path=outputs / "missing-topology-runtime.json",
                topology_receipt=None,
            )
        except probe.ArchiveProbeRefusal as exc:
            assert exc.code == "ARCHIVE-TOPOLOGY-MISSING", exc.code
        else:
            raise AssertionError("archive probe ran without a five-plane topology receipt")
        archive_out = outputs / "archive_receipt.json"
        runtime_out = outputs / "unpacked_zip_runtime.json"
        archive_receipt, runtime_receipt = probe.probe_archive(
            archive=safe_archive,
            source_root=source_root,
            source_commit=source_commit,
            archive_receipt_path=archive_out,
            unpacked_runtime_path=runtime_out,
            topology_receipt=_topology_receipt(safe_archive, source_root, source_commit),
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
        runtime_argv = runtime_receipt["runtime_execution"]["argv"]
        zip_index = runtime_argv.index("--cleared-zip")
        commit_index = runtime_argv.index("--source-commit")
        kind_index = runtime_argv.index("--plane-kind")
        assert Path(runtime_argv[zip_index + 1]).name == "cleared.zip"
        assert not Path(runtime_argv[zip_index + 1]).exists()
        assert runtime_argv[commit_index + 1] == source_commit
        assert runtime_argv[kind_index + 1] == "unpacked"
        assert runtime_receipt["runtime_execution"]["environment"]["PYTHONPATH"] == ""
        assert runtime_receipt["runtime_execution"]["environment"]["python_environment_policy"] == "scrub-all-restore-three-v1"
        assert runtime_receipt["runtime_execution"]["environment"]["dependency_paths"]
        assert runtime_receipt["source_isolation"]["source_root_absent_from_sys_path"] is True
        assert runtime_receipt["source_isolation"]["interpreter_sys_path_observed"] is True
        assert runtime_receipt["cleanup"] == {
            "temporary_root_removed": True,
            "cwd_removed": True,
            "temporary_root_exists_after": False,
            "cwd_exists_after": False,
            "runtime_plane_receipt_retained": True,
        }
        retained_stdout = base64.b64decode(
            runtime_receipt["runtime_plane_receipt"]["stdout_base64"],
            validate=True,
        )
        assert probe._sha_bytes(retained_stdout) == runtime_receipt["runtime_plane_receipt"]["sha256"]
        assert json.loads(retained_stdout) == runtime_receipt["runtime_plane_receipt"]["payload"]
        for outer in (archive_receipt, runtime_receipt):
            retained_topology = outer["derived_topology_receipt"]
            retained_topology_bytes = probe.topology.canonical_receipt_bytes(
                retained_topology["payload"]
            )
            assert probe._sha_bytes(retained_topology_bytes) == retained_topology["sha256"]
            assert (
                runtime_receipt["runtime_plane_receipt"]["payload"]["topology_receipt"]["sha256"]
                == retained_topology["sha256"]
            )
            assert retained_topology["payload"]["verdict"] == "qualified"
        assert not Path(runtime_receipt["extraction"]["temporary_root"]).exists()
        assert not Path(runtime_receipt["runtime_execution"]["cwd"]).exists()
        assert archive_receipt["unpacked_runtime_receipt"]["sha256"] == probe._sha_path(runtime_out)

        builder_archive = base / "builder-shaped.zip"
        builder_members = [
            (member, content)
            for member, content in _safe_members()
            if not isinstance(member, zipfile.ZipInfo) or not member.is_dir()
        ]
        _write_archive(builder_archive, builder_members)
        builder_archive_out = outputs / "builder-shaped-archive.json"
        builder_runtime_out = outputs / "builder-shaped-runtime.json"
        builder_receipt, builder_runtime = probe.probe_archive(
            archive=builder_archive,
            source_root=source_root,
            source_commit=source_commit,
            archive_receipt_path=builder_archive_out,
            unpacked_runtime_path=builder_runtime_out,
            topology_receipt=_topology_receipt(builder_archive, source_root, source_commit),
        )
        assert builder_receipt["verdict"] == "qualified"
        assert builder_runtime["verdict"] == "qualified"

        runtime_cases = [
            (
                "qualified-with-caveats-zero",
                QUALIFIED_WITH_CAVEATS_RUNTIME_STUB,
                "blocked",
                "ARCHIVE-RUNTIME-PLANE-CAVEATED",
                "failed",
            ),
            (
                "blocked-two",
                BLOCKED_RUNTIME_STUB,
                "blocked",
                "ARCHIVE-RUNTIME-PLANE-BLOCKED",
                "failed",
            ),
            (
                "blocked-zero",
                BLOCKED_ZERO_RUNTIME_STUB,
                "blocked",
                "ARCHIVE-RUNTIME-PROBE-FAILED",
                "failed",
            ),
            (
                "qualified-two",
                QUALIFIED_TWO_RUNTIME_STUB,
                "blocked",
                "ARCHIVE-RUNTIME-PROBE-FAILED",
                "failed",
            ),
            (
                "malformed-zero",
                MALFORMED_RUNTIME_STUB,
                "blocked",
                "ARCHIVE-RUNTIME-PROBE-FAILED",
                "failed",
            ),
            (
                "schema-invalid-zero",
                SCHEMA_INVALID_RUNTIME_STUB,
                "blocked",
                "ARCHIVE-RUNTIME-RECEIPT-SCHEMA",
                "failed",
            ),
            (
                "wrong-type-zero",
                WRONG_TYPE_RUNTIME_STUB,
                "blocked",
                "ARCHIVE-RUNTIME-RECEIPT-SCHEMA",
                "failed",
            ),
            (
                "wrong-zip-hash-zero",
                WRONG_ZIP_HASH_RUNTIME_STUB,
                "blocked",
                "ARCHIVE-RUNTIME-RECEIPT-BINDING",
                "failed",
            ),
            (
                "wrong-zip-size-zero",
                WRONG_ZIP_SIZE_RUNTIME_STUB,
                "blocked",
                "ARCHIVE-RUNTIME-RECEIPT-BINDING",
                "failed",
            ),
            (
                "wrong-commit-zero",
                WRONG_COMMIT_RUNTIME_STUB,
                "blocked",
                "ARCHIVE-RUNTIME-RECEIPT-BINDING",
                "failed",
            ),
            (
                "missing-suite-zero",
                MISSING_SUITE_RUNTIME_STUB,
                "blocked",
                "ARCHIVE-RUNTIME-RECEIPT-BINDING",
                "failed",
            ),
        ]
        for name, runtime_stub, expected_verdict, expected_code, expected_status in runtime_cases:
            runtime_archive = base / f"{name}.zip"
            _write_archive(runtime_archive, _safe_members(runtime_stub))
            runtime_archive_out = outputs / f"{name}-archive.json"
            runtime_receipt_out = outputs / f"{name}-runtime.json"
            case_archive, case_runtime = probe.probe_archive(
                archive=runtime_archive,
                source_root=source_root,
                source_commit=source_commit,
                archive_receipt_path=runtime_archive_out,
                unpacked_runtime_path=runtime_receipt_out,
                topology_receipt=_topology_receipt(runtime_archive, source_root, source_commit),
            )
            _validate(case_archive)
            _validate(case_runtime)
            assert case_archive["verdict"] == expected_verdict
            assert case_runtime["runtime_execution"]["status"] == expected_status
            codes = {row["code"] for row in case_runtime["findings"]}
            if expected_code is None:
                assert not codes
            else:
                assert expected_code in codes
            retained_stdout = base64.b64decode(
                case_runtime["runtime_plane_receipt"]["stdout_base64"],
                validate=True,
            )
            assert probe._sha_bytes(retained_stdout) == case_runtime["runtime_plane_receipt"]["sha256"]
            if case_runtime["runtime_plane_receipt"]["payload"] is not None:
                assert json.loads(retained_stdout) == case_runtime["runtime_plane_receipt"]["payload"]
            if name == "blocked-two":
                assert "ARCHIVE-RUNTIME-PROBE-FAILED" not in codes
                assert case_runtime["runtime_plane_receipt"]["verdict"] == "blocked"
                assert case_runtime["runtime_plane_receipt"]["sha256"]

        substitution_archive = base / "substitution.zip"
        substitution_replacement = base / "substitution-replacement.zip"
        _write_archive(substitution_archive, _safe_members())
        replacement_members = _safe_members()
        replacement_members[-1] = (_info("payload.txt"), b"replacement payload\n")
        _write_archive(substitution_replacement, replacement_members)
        substitution_archive_out = outputs / "substitution-archive.json"
        substitution_runtime_out = outputs / "substitution-runtime.json"
        original_extract = probe._extract_members

        def substitute_then_extract(archive_snapshot, selected, root):
            substitution_archive.write_bytes(substitution_replacement.read_bytes())
            return original_extract(archive_snapshot, selected, root)

        probe._extract_members = substitute_then_extract
        try:
            substituted_archive, substituted_runtime = probe.probe_archive(
                archive=substitution_archive,
                source_root=source_root,
                source_commit=source_commit,
                archive_receipt_path=substitution_archive_out,
                unpacked_runtime_path=substitution_runtime_out,
                topology_receipt=_topology_receipt(substitution_archive, source_root, source_commit),
            )
        finally:
            probe._extract_members = original_extract
        assert substituted_archive["verdict"] == "blocked"
        assert substituted_runtime["verdict"] == "blocked"
        assert any(
            row["code"] == "ARCHIVE-CHANGED-DURING-PROBE"
            for row in substituted_archive["findings"]
        )

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
            _expect_refusal(archive, outputs, code, source_root, source_commit)

        mutating_archive = base / "mutating-runtime.zip"
        _write_archive(mutating_archive, _safe_members(MUTATING_RUNTIME_STUB))
        mutating_archive_out = outputs / "mutating-archive.json"
        mutating_runtime_out = outputs / "mutating-runtime.json"
        blocked_archive, blocked_runtime = probe.probe_archive(
            archive=mutating_archive,
            source_root=source_root,
            source_commit=source_commit,
            archive_receipt_path=mutating_archive_out,
            unpacked_runtime_path=mutating_runtime_out,
            topology_receipt=_topology_receipt(mutating_archive, source_root, source_commit),
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
