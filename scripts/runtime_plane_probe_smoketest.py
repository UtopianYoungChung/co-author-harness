#!/usr/bin/env python3
"""Focused V40-01 cleared-ZIP/cache provenance and contamination tests."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import warnings
import zipfile
from pathlib import Path

if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1" or not sys.dont_write_bytecode:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [sys.executable, "-B", os.path.abspath(__file__)],
        env=environment,
        check=False,
    )
    raise SystemExit(completed.returncode)

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parent.parent
PROBE_PATH = ROOT / "scripts" / "runtime_plane_probe.py"
SCHEMA_PATH = ROOT / "references" / "schemas" / "runtime_plane_receipt.schema.json"


class RetryingTemporaryDirectory(tempfile.TemporaryDirectory):
    """Windows-safe cleanup for short-lived Git/subprocess fixture trees."""

    def cleanup(self) -> None:
        self._finalizer.detach()

        def repair_and_retry(function, path, _error) -> None:
            os.chmod(path, 0o700)
            function(path)

        for attempt in range(7):
            try:
                try:
                    shutil.rmtree(self.name, onexc=repair_and_retry)
                except TypeError:  # Python < 3.12 compatibility
                    shutil.rmtree(self.name, onerror=repair_and_retry)
                return
            except FileNotFoundError:
                return
            except (PermissionError, OSError):
                if attempt == 6:
                    raise
                time.sleep(0.05 * (2 ** attempt))


def load_probe():
    spec = importlib.util.spec_from_file_location("runtime_plane_probe", PROBE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {PROBE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def package(
    root: Path,
    *,
    mutating_suite: bool = False,
    failed_suite: str | None = None,
    missing_suite: str | None = None,
) -> None:
    write(
        root / ".claude-plugin" / "plugin.json",
        json.dumps({"name": "fixture-plugin", "version": "1.2.3"}).encode(),
    )
    write(root / "README.md", b"alpha\nbeta\n")
    write(root / "references" / "policies" / "base.json", b"{}\n")
    suites = {
        "run_product_gate_smoketest.py": (
            "from pathlib import Path\n"
            + (
                "Path('README.md').write_text('mutated\\n', encoding='utf-8')\n"
                if mutating_suite
                else ""
            )
            + "raise SystemExit(0)\n"
        ),
        "schema_runtime_check.py": "raise SystemExit(0)\n",
        "version-check.py": "raise SystemExit(0)\n",
        "skill-check.py": "raise SystemExit(0)\n",
    }
    for name, source in suites.items():
        if name == missing_suite:
            continue
        if name == failed_suite:
            source = "raise SystemExit(7)\n"
        write(root / "scripts" / name, source.encode())


def git_commit(root: Path) -> str:
    for argv in (
        ["git", "init", "--quiet"],
        ["git", "config", "user.email", "fixture@example.invalid"],
        ["git", "config", "user.name", "Fixture"],
        ["git", "add", "."],
        ["git", "commit", "--quiet", "-m", "fixture"],
    ):
        subprocess.run(argv, cwd=root, check=True, capture_output=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
    ).stdout.strip()


def tracked(root: Path, commit: str) -> list[str]:
    return subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", commit],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
    ).stdout.splitlines()


def provenance(commit: str, count: int) -> bytes:
    return (json.dumps({
        "schema": "coauthor-build-provenance/v1",
        "commit": commit,
        "enumerator": "scripts/package_enumeration.py::enumerate_package_files",
        "package_member_count": count,
        "archive_member_count": count + 1,
        "toolchain": {},
        "toolchain_is_commit": True,
        "runtime": {
            "python": "3.fixture",
            "python_full": "3.fixture synthetic",
            "zlib": "fixture",
            "compression": "ZIP_DEFLATED",
            "note": "synthetic provenance fixture",
        },
        "zip_date_time_stored": [2026, 7, 27, 0, 0, 0],
        "zip_date_time_commit": [2026, 7, 27, 0, 0, 0],
    }, sort_keys=True) + "\n").encode()


def build_zip(
    source: Path,
    archive: Path,
    commit: str,
    *,
    overrides: dict[str, bytes] | None = None,
    provenance_commit: str | None = None,
    extras: list[tuple[str, bytes]] | None = None,
) -> None:
    names = tracked(source, commit)
    overrides = overrides or {}
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as out:
        for name in names:
            out.writestr(name, overrides.get(name, (source / name).read_bytes()))
        out.writestr(PROVENANCE, provenance(provenance_commit or commit, len(names)))
        for name, data in extras or []:
            out.writestr(name, data)


PROVENANCE = "PROVENANCE.json"


def extract(archive: Path, target: Path) -> None:
    with zipfile.ZipFile(archive, "r") as source:
        source.extractall(target)


def validate(receipt: dict) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(receipt), key=lambda error: list(error.path)
    )
    assert not errors, "; ".join(error.message for error in errors)


def fixture(
    base: Path,
    name: str,
    *,
    package_options: dict | None = None,
    zip_options: dict | None = None,
) -> tuple[Path, Path, Path, str]:
    source = base / name / "source"
    local = base / name / "local"
    archive = base / name / "cleared.zip"
    package(source, **(package_options or {}))
    commit = git_commit(source)
    build_zip(source, archive, commit, **(zip_options or {}))
    extract(archive, local)
    return source, local, archive, commit


def probe_case(
    probe,
    source: Path,
    local: Path,
    archive: Path | None,
    commit: str | None,
    *,
    crlf_mode: str = "forbid",
) -> dict:
    out = source / "releases" / "verification" / "fixture" / "runtime-plane.json"
    receipt = probe.probe_plane(
        local_root=local,
        baseline_root=source,
        cleared_zip_path=archive,
        source_commit=commit,
        crlf_mode=crlf_mode,
        out_path=out,
    )
    assert json.loads(out.read_text(encoding="utf-8")) == receipt
    validate(receipt)
    return receipt


def contaminated(receipt: dict) -> None:
    assert receipt["cache_state"] == "CACHE_PROVENANCE_CONTAMINATED"
    assert receipt["verdict"] == "blocked"
    assert any(row["code"] == "CACHE-PROVENANCE-CONTAMINATED" for row in receipt["findings"])


def main() -> int:
    assert os.environ.get("PYTHONDONTWRITEBYTECODE") == "1"
    probe = load_probe()
    cases: list[str] = []
    with RetryingTemporaryDirectory(prefix="runtime-plane-v40-", dir=ROOT) as td:
        base = Path(td)

        source, local, archive, commit = fixture(base, "clean")
        clean = probe_case(probe, source, local, archive, commit)
        assert clean["cache_state"] == "CODEX_CACHE_QUALIFIED"
        assert clean["verdict"] == "qualified"
        assert clean["identity"]["canonical_archive_claim"] is True
        assert len(clean["suites"]) == 4 and all(row["status"] == "passed" for row in clean["suites"])
        cases.append("clean_qualification")

        source, local, archive, commit = fixture(base, "provenance-missing")
        shutil.rmtree(local)
        shutil.copytree(source, local, ignore=shutil.ignore_patterns(".git"))
        missing_provenance = probe_case(probe, source, local, None, None)
        assert missing_provenance["cache_state"] == "CACHE_PROVENANCE_MISSING"
        assert missing_provenance["verdict"] == "blocked"
        cases.append("cache_provenance_missing")

        source, local, archive, commit = fixture(
            base, "wrong-zip-bytes", zip_options={"overrides": {"README.md": b"wrong archive bytes\n"}}
        )
        wrong_zip = probe_case(probe, source, local, archive, commit)
        contaminated(wrong_zip)
        assert wrong_zip["identity"]["embedded"]["provenance"]["status"] == "valid"
        assert any(row["code"] == "RUNTIME-PLANE-ARCHIVE-SOURCE-DIFFERENCE" for row in wrong_zip["findings"])
        cases.append("zip_claim_without_member_equality")

        source, local, archive, commit = fixture(base, "dirty-same-head")
        write(source / "README.md", b"dirty worktree bytes\n")
        dirty_archive = archive.with_name("dirty-same-head.zip")
        build_zip(source, dirty_archive, commit)
        shutil.rmtree(local)
        extract(dirty_archive, local)
        dirty_same_head = probe_case(probe, source, local, dirty_archive, commit)
        contaminated(dirty_same_head)
        assert any(
            row["code"] == "RUNTIME-PLANE-ARCHIVE-SOURCE-DIFFERENCE"
            for row in dirty_same_head["findings"]
        )
        cases.append("source_commit_uses_git_object_bytes")

        source, local, archive, commit = fixture(
            base, "wrong-provenance", zip_options={"provenance_commit": "0" * 40}
        )
        wrong_provenance = probe_case(probe, source, local, archive, commit)
        contaminated(wrong_provenance)
        cases.append("wrong_zip_provenance")

        source, local, archive, commit = fixture(base, "semantic-edit")
        write(local / "README.md", b"different\n")
        semantic = probe_case(probe, source, local, archive, commit)
        contaminated(semantic)
        assert [row["path"] for row in semantic["semantic_differences"]] == ["README.md"]
        cases.append("semantic_edit")

        source, local, archive, commit = fixture(base, "missing-file")
        (local / "README.md").unlink()
        missing = probe_case(probe, source, local, archive, commit)
        contaminated(missing)
        assert [row["path"] for row in missing["missing_files"]] == ["README.md"]
        cases.append("missing_file")

        source, local, archive, commit = fixture(base, "blocking-extra")
        write(local / "rogue.py", b"VALUE = 1\n")
        blocking = probe_case(probe, source, local, archive, commit)
        contaminated(blocking)
        assert next(row for row in blocking["foreign_extras"] if row["path"] == "rogue.py")["blocking"]
        cases.append("blocking_extra")

        source, local, archive, commit = fixture(base, "duplicate-member")
        clean_archive = archive
        duplicate_archive = archive.with_name("duplicate.zip")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            build_zip(source, duplicate_archive, commit, extras=[("README.md", b"duplicate\n")])
        duplicate = probe_case(probe, source, local, duplicate_archive, commit)
        contaminated(duplicate)
        assert any("duplicate archive member" in row["message"] for row in duplicate["findings"])
        assert clean_archive.is_file()
        cases.append("duplicate_archive_member")

        source, local, archive, commit = fixture(base, "escape-member")
        escape_archive = archive.with_name("escape.zip")
        build_zip(source, escape_archive, commit, extras=[("../escape.py", b"bad\n")])
        escaped = probe_case(probe, source, local, escape_archive, commit)
        contaminated(escaped)
        assert any("unsafe archive member" in row["message"] for row in escaped["findings"])
        cases.append("path_escape_archive_member")

        source, local, archive, commit = fixture(
            base, "unstable", package_options={"mutating_suite": True}
        )
        unstable = probe_case(probe, source, local, archive, commit)
        contaminated(unstable)
        assert unstable["package_digests"]["stable"] is False
        cases.append("unstable_core_digest")

        source, local, archive, commit = fixture(
            base, "failed-suite", package_options={"failed_suite": "schema_runtime_check.py"}
        )
        failed = probe_case(probe, source, local, archive, commit)
        contaminated(failed)
        assert next(row for row in failed["suites"] if row["name"] == "schema_runtime_check")["status"] == "failed"
        cases.append("failed_core_suite")

        source, local, archive, commit = fixture(
            base, "missing-suite", package_options={"missing_suite": "skill-check.py"}
        )
        absent = probe_case(probe, source, local, archive, commit)
        contaminated(absent)
        assert next(row for row in absent["suites"] if row["name"] == "skill_check")["status"] == "missing"
        cases.append("missing_core_suite")

        source, local, archive, commit = fixture(base, "crlf-forbidden")
        write(local / "README.md", b"alpha\r\nbeta\r\n")
        forbidden = probe_case(probe, source, local, archive, commit)
        contaminated(forbidden)
        assert forbidden["normalization_policy"]["crlf_mode"] == "forbid"
        cases.append("crlf_forbidden")

        source, local, archive, commit = fixture(base, "crlf-allowed")
        write(local / "README.md", b"alpha\r\nbeta\r\n")
        allowed = probe_case(
            probe, source, local, archive, commit, crlf_mode="allow_utf8_crlf_only"
        )
        assert allowed["cache_state"] == "CODEX_CACHE_QUALIFIED"
        assert allowed["verdict"] == "qualified_with_caveats"
        assert allowed["identity"]["canonical_archive_claim"] is False
        cases.append("crlf_explicitly_allowed")

        source, local, archive, commit = fixture(base, "benign-extra")
        write(local / "host-note.txt", b"host metadata\n")
        benign = probe_case(probe, source, local, archive, commit)
        assert benign["cache_state"] == "CODEX_CACHE_QUALIFIED"
        assert benign["verdict"] == "qualified_with_caveats"
        assert not next(row for row in benign["foreign_extras"] if row["path"] == "host-note.txt")["blocking"]
        cases.append("benign_extra")

        try:
            probe.probe_plane(
                local_root=local,
                baseline_root=source,
                cleared_zip_path=archive,
                source_commit=commit,
                out_path=source / "reviews" / "runtime-plane.json",
            )
        except probe.ProbeRefusal as exc:
            assert exc.code == "RUNTIME-PLANE-OUTPUT"
        else:
            raise AssertionError("arbitrary in-package output was accepted")
        cases.append("destination_boundary")

    print(f"runtime_plane_probe_smoketest: PASS ({len(cases)} cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
