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
from assignment_fixture_support import package_scratch

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
        root / "version.json",
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
        "shipment_manifest_smoketest.py": "raise SystemExit(0)\n",
        "output_contract_smoketest.py": "raise SystemExit(0)\n",
        "output_economy_check.py": "raise SystemExit(0)\n",
    }
    for name, source in suites.items():
        if name == missing_suite:
            continue
        if name == failed_suite:
            source = "raise SystemExit(7)\n"
        write(root / "scripts" / name, source.encode())


def git_commit(root: Path) -> str:
    for argv in (
        ["git", "init", "--quiet", "-b", "main"],
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


def topology_receipt(probe, source: Path, local: Path, archive: Path | None, commit: str | None, plane_kind: str) -> dict:
    bound_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=source, check=True,
        capture_output=True, text=True, encoding="utf-8", errors="strict",
    ).stdout.strip()
    archive_path = archive or source.parent / "cleared.zip"
    unpacked = local if plane_kind == "unpacked" else source.parent / "topology-unpacked"
    installed = local if plane_kind == "installed_cache" else source.parent / "topology-installed-cache"
    build = source.parent / "topology-build"
    if not build.exists():
        subprocess.run(
            ["git", "clone", "--quiet", "--no-local", str(source), str(build)], check=True,
        )
        subprocess.run(
            ["git", "checkout", "--quiet", "--detach", bound_commit], cwd=build, check=True,
        )
    for path in (unpacked, installed):
        path.mkdir(parents=True, exist_ok=True)
    paths = {
        "source": source, "build": build, "archive": archive_path,
        "unpacked": unpacked, "installed_cache": installed,
    }
    records = []
    for kind in probe.topology.PLANE_KINDS:
        records.append({
            "plane_kind": kind,
            "path": str(paths[kind].resolve()),
            "path_kind": "file" if kind == "archive" else "directory",
            "digest_sha256": probe.topology.plane_digest(kind, paths[kind]),
            "git_commit": bound_commit if kind in {"source", "build"} else None,
            "git_state": "source_main" if kind == "source" else "detached_clean" if kind == "build" else "absent",
            "provenance_commit": bound_commit if kind in {"archive", "unpacked", "installed_cache"} else None,
        })
    return {
        "schema_version": "1.0.0", "receipt_type": "qualification_plane_topology",
        "source_commit": bound_commit, "planes": records, "source_stable": True,
        "findings": [], "verdict": "qualified",
    }


def probe_case(
    probe,
    source: Path,
    local: Path,
    archive: Path | None,
    commit: str | None,
    *,
    crlf_mode: str = "forbid",
    plane_kind: str = "installed_cache",
) -> dict:
    out = source / "releases" / "verification" / "fixture" / "runtime-plane.json"
    receipt = probe.probe_plane(
        local_root=local,
        baseline_root=source,
        cleared_zip_path=archive,
        source_commit=commit,
        crlf_mode=crlf_mode,
        out_path=out,
        plane_kind=plane_kind,
        topology_receipt=topology_receipt(probe, source, local, archive, commit, plane_kind),
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
    with RetryingTemporaryDirectory(prefix="runtime-plane-v40-", dir=package_scratch(ROOT)) as td:
        base = Path(td)

        nested_root = base / "nested-dependency"
        package(nested_root)
        dependency_root = base / "qualified-dependency"
        write(
            dependency_root / "runtime_probe_nested_dependency.py",
            b"VALUE = 'qualified-dependency'\n",
        )
        write(
            nested_root / "scripts" / "run_product_gate_smoketest.py",
            (
                "import subprocess, sys\n"
                "completed = subprocess.run(\n"
                " [sys.executable, '-c', "
                "'import os; import runtime_probe_nested_dependency as d; "
                "bad=[k for k in (\"PYTHONOPTIMIZE\",\"PYTHONPLATLIBDIR\",\"PYTHONWARNINGS\",\"PYTHONHOME\") if os.environ.get(k)]; "
                "bad and (_ for _ in ()).throw(RuntimeError(str(bad))); "
                "os.environ.get(\"PYTHONNOUSERSITE\") == \"1\" or (_ for _ in ()).throw(RuntimeError(\"no-usersite\")); "
                "d.VALUE == \\\"qualified-dependency\\\" or (_ for _ in ()).throw(RuntimeError(\"dependency\"))'],\n"
                " capture_output=True, text=True, encoding='utf-8', errors='replace',\n"
                ")\n"
                "if completed.returncode != 0:\n"
                " raise AssertionError(completed.stdout + completed.stderr)\n"
            ).encode("utf-8"),
        )
        nested_results = probe._run_suites(
            nested_root,
            probe.DEFAULT_SUITES,
            [str(dependency_root)],
        )
        assert len(nested_results) == 7
        assert all(row["status"] == "passed" for row in nested_results)
        assert os.environ.get("PYTHONPATH", "") != str(dependency_root)
        cases.append("nested_subprocess_receives_only_qualified_dependencies")

        source, local, archive, commit = fixture(base, "clean")
        for value, code in (
            (None, "RUNTIME-PLANE-KIND-MISSING"),
            ("source", "RUNTIME-PLANE-KIND-UNKNOWN"),
        ):
            try:
                probe.probe_plane(
                    local_root=local, baseline_root=source, cleared_zip_path=archive,
                    source_commit=commit, out_path=None, plane_kind=value,
                )
            except probe.ProbeRefusal as exc:
                assert exc.code == code, (code, exc.code)
            else:
                raise AssertionError(f"plane kind {value!r} was accepted")
        cases.append("required_plane_kind_refusals")
        try:
            probe.probe_plane(
                local_root=local, baseline_root=source, cleared_zip_path=archive,
                source_commit=commit, out_path=None, plane_kind="installed_cache",
            )
        except probe.ProbeRefusal as exc:
            assert exc.code == "RUNTIME-PLANE-TOPOLOGY-MISSING", exc.code
        else:
            raise AssertionError("runtime plane ran without a five-plane topology receipt")
        cases.append("topology_receipt_required_before_suites")
        clean = probe_case(probe, source, local, archive, commit)
        assert clean["cache_state"] == "CODEX_CACHE_QUALIFIED"
        assert clean["verdict"] == "qualified"
        assert clean["identity"]["canonical_archive_claim"] is True
        assert clean["environment"]["ambient_pythonpath"] == ""
        assert clean["environment"]["python_environment_policy"] == "scrub-all-restore-three-v1"
        assert clean["environment"]["suite_pythonpath"].split(os.pathsep) == clean["environment"]["dependency_paths"]
        assert clean["environment"]["suite_pythonno_usersite"] == "1"
        assert clean["environment"]["suite_pythonhome"] is None
        assert len(clean["suites"]) == 7 and all(row["status"] == "passed" for row in clean["suites"])
        cases.append("clean_qualification")

        wrong_type = json.loads(json.dumps(clean))
        wrong_type["environment"] = []
        try:
            probe._validate(wrong_type)
        except probe.ProbeRefusal as exc:
            assert exc.code == "RUNTIME-PLANE-SCHEMA"
        else:
            raise AssertionError("wrong-type runtime environment was accepted")
        cases.append("runtime_environment_wrong_type_refused")

        for key, value in (
            ("PYTHONPATH", str(base / "ambient-route")),
            ("PYTHONOPTIMIZE", "2"),
            ("PYTHONWARNINGS", "error"),
            ("PYTHONHOME", str(base / "ambient-home")),
            ("PYTHONUTF8", "1"),
        ):
            previous = os.environ.get(key)
            os.environ[key] = value
            try:
                try:
                    probe_case(probe, source, local, archive, commit)
                except probe.ProbeRefusal as exc:
                    assert exc.code == "QUALIFICATION-ENV-AMBIENT"
                else:
                    raise AssertionError(f"ambient {key} was accepted")
            finally:
                if previous is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = previous
        cases.append("ambient_python_controls_refused")

        source, local, archive, commit = fixture(base, "source-installed-cache")
        (local / PROVENANCE).unlink()
        source_installed = probe_case(probe, source, local, archive, commit)
        assert source_installed["cache_state"] == "CODEX_CACHE_QUALIFIED"
        assert source_installed["verdict"] == "qualified_with_caveats"
        assert source_installed["identity"]["canonical_archive_claim"] is False
        assert source_installed["identity"]["embedded"]["provenance"]["status"] == "missing"
        assert any(
            row["code"] == "RUNTIME-PLANE-EMBEDDED-PROVENANCE-MISSING"
            and row["severity"] == "WARNING"
            for row in source_installed["findings"]
        )
        cases.append("source_installed_cache_without_archive_only_provenance")

        source, local, archive, commit = fixture(base, "source-install-wrong-zip")
        (local / PROVENANCE).unlink()
        wrong_archive = archive.with_name("source-install-wrong-zip-tampered.zip")
        build_zip(source, wrong_archive, commit, overrides={"README.md": b"wrong archive bytes\n"})
        wrong_source_install = probe_case(probe, source, local, wrong_archive, commit)
        contaminated(wrong_source_install)
        assert any(
            row["code"] == "RUNTIME-PLANE-ARCHIVE-SOURCE-DIFFERENCE"
            for row in wrong_source_install["findings"]
        )
        cases.append("source_installed_cache_wrong_archive_members")

        source, local, archive, commit = fixture(base, "source-install-wrong-provenance")
        (local / PROVENANCE).unlink()
        wrong_provenance_archive = archive.with_name("source-install-wrong-provenance-tampered.zip")
        build_zip(source, wrong_provenance_archive, commit, provenance_commit="0" * 40)
        wrong_source_provenance = probe_case(
            probe, source, local, wrong_provenance_archive, commit
        )
        contaminated(wrong_source_provenance)
        assert any(
            row["code"] == "RUNTIME-PLANE-ARCHIVE-COMMIT-MISMATCH"
            for row in wrong_source_provenance["findings"]
        )
        cases.append("source_installed_cache_wrong_archive_provenance")

        source, local, archive, commit = fixture(base, "source-install-wrong-commit")
        (local / PROVENANCE).unlink()
        try:
            probe_case(probe, source, local, archive, "0" * 40)
        except probe.ProbeRefusal as exc:
            assert exc.code == "RUNTIME-PLANE-TOPOLOGY-COMMIT", exc.code
        else:
            raise AssertionError("wrong explicit commit reached runtime comparison after topology")
        cases.append("source_installed_cache_wrong_explicit_commit")

        source, local, archive, commit = fixture(base, "archive-substitution")
        replacement = archive.with_name("archive-substitution-replacement.zip")
        build_zip(source, replacement, commit, overrides={"README.md": b"replacement archive bytes\n"})
        original_run_suites = probe._run_suites

        def substitute_then_run(*args, **kwargs):
            archive.write_bytes(replacement.read_bytes())
            return original_run_suites(*args, **kwargs)

        probe._run_suites = substitute_then_run
        try:
            substituted = probe_case(probe, source, local, archive, commit)
        finally:
            probe._run_suites = original_run_suites
        contaminated(substituted)
        assert any(
            row["code"] == "RUNTIME-PLANE-ARCHIVE-CHANGED"
            for row in substituted["findings"]
        )
        cases.append("archive_substitution_during_probe")

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
        try:
            probe_case(probe, source, local, dirty_archive, commit)
        except probe.ProbeRefusal as exc:
            assert exc.code == "RUNTIME-PLANE-SOURCE-DIRTY", exc.code
        else:
            raise AssertionError("dirty source reached runtime comparison after topology")
        cases.append("source_commit_uses_git_object_bytes")

        source, local, archive, commit = fixture(
            base, "wrong-provenance", zip_options={"provenance_commit": "0" * 40}
        )
        wrong_provenance = probe_case(probe, source, local, archive, commit)
        contaminated(wrong_provenance)
        cases.append("wrong_zip_provenance")

        source, local, archive, commit = fixture(base, "semantic-edit")
        write(local / "README.md", b"different\n")
        original_run_suites = probe._run_suites
        probe._run_suites = lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("semantic contamination executed child suites")
        )
        try:
            semantic = probe_case(probe, source, local, archive, commit)
        finally:
            probe._run_suites = original_run_suites
        contaminated(semantic)
        assert [row["path"] for row in semantic["semantic_differences"]] == ["README.md"]
        assert all(row["status"] == "not_run_preflight" for row in semantic["suites"])
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
                plane_kind="installed_cache",
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
