#!/usr/bin/env python3
"""Focused C6 boundary tests for typed runtime-plane parity receipts."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1" or not sys.dont_write_bytecode:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [sys.executable, "-B", os.path.abspath(__file__)], env=environment,
        check=False,
    )
    raise SystemExit(completed.returncode)

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parent.parent
PROBE_PATH = ROOT / "scripts" / "runtime_plane_probe.py"
SCHEMA_PATH = ROOT / "references" / "schemas" / "runtime_plane_receipt.schema.json"


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


def package(root: Path, *, mutating_suite: bool = False) -> None:
    manifest = {"name": "fixture-plugin", "version": "1.2.3"}
    write(root / ".claude-plugin" / "plugin.json", json.dumps(manifest).encode())
    write(root / "README.md", b"alpha\nbeta\n")
    write(root / "references" / "policies" / "base.json", b"{}\n")
    suites = {
        "run_product_gate_smoketest.py": (
            "from pathlib import Path\n"
            + ("Path('README.md').write_text('mutated\\n', encoding='utf-8')\n" if mutating_suite else "")
            + "raise SystemExit(0)\n"
        ),
        "schema_runtime_check.py": "raise SystemExit(0)\n",
        "version-check.py": "raise SystemExit(0)\n",
        "skill-check.py": "raise SystemExit(0)\n",
    }
    for name, source in suites.items():
        write(root / "scripts" / name, source.encode())


def copy_package(source: Path, target: Path) -> None:
    shutil.copytree(source, target, ignore=shutil.ignore_patterns(".git"))


def validate(receipt: dict) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(receipt), key=lambda e: list(e.path))
    assert not errors, "; ".join(error.message for error in errors)


def run_case(probe, base: Path, name: str, mutate=None) -> dict:
    source = base / name / "source"
    local = base / name / "local"
    out = source / "releases" / "verification" / "fixture" / "runtime-plane.json"
    package(source)
    copy_package(source, local)
    if mutate:
        mutate(source, local)
    receipt = probe.probe_plane(local_root=local, baseline_root=source, out_path=out)
    assert json.loads(out.read_text(encoding="utf-8")) == receipt
    validate(receipt)
    return receipt


def git_commit(root: Path) -> str:
    commands = (
        ["git", "init", "--quiet"],
        ["git", "config", "user.email", "fixture@example.invalid"],
        ["git", "config", "user.name", "Fixture"],
        ["git", "add", "."],
        ["git", "commit", "--quiet", "-m", "fixture"],
    )
    for argv in commands:
        subprocess.run(argv, cwd=root, check=True, capture_output=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True,
        capture_output=True, text=True, encoding="utf-8", errors="strict",
    ).stdout.strip()


def provenance_record(root: Path, commit: str) -> dict:
    source_head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True,
        capture_output=True, text=True, encoding="utf-8", errors="strict",
    ).stdout.strip()
    tracked = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", source_head], cwd=root,
        check=True, capture_output=True, text=True, encoding="utf-8", errors="strict",
    ).stdout.splitlines()
    package_count = len([
        path for path in tracked
        if not path.lower().endswith((".zip", ".plugin"))
    ])
    return {
        "schema": "coauthor-build-provenance/v1",
        "commit": commit,
        "enumerator": "scripts/package_enumeration.py::enumerate_package_files",
        "package_member_count": package_count,
        "archive_member_count": package_count + 1,
        "toolchain": {},
        "toolchain_is_commit": True,
        "runtime": {
            "python": "3.fixture",
            "python_full": "3.fixture synthetic",
            "zlib": "fixture",
            "compression": "ZIP_DEFLATED",
            "note": "synthetic provenance fixture",
        },
        "zip_date_time_stored": [2026, 7, 25, 0, 0, 0],
        "zip_date_time_commit": [2026, 7, 25, 0, 0, 0],
    }


def main() -> int:
    assert os.environ.get("PYTHONDONTWRITEBYTECODE") == "1"
    probe = load_probe()
    with tempfile.TemporaryDirectory(prefix="runtime-plane-c6-") as td:
        base = Path(td)

        exact = run_case(probe, base, "exact")
        assert exact["verdict"] == "qualified_with_caveats"
        assert exact["identity"]["embedded"]["provenance"]["status"] == "missing"
        assert exact["identity"]["canonical_archive_claim"] is False
        assert not exact["crlf_only"] and not exact["semantic_differences"]

        crlf = run_case(
            probe, base, "crlf",
            lambda _source, local: write(local / "README.md", b"alpha\r\nbeta\r\n"),
        )
        assert [entry["path"] for entry in crlf["crlf_only"]] == ["README.md"]
        assert crlf["verdict"] == "qualified_with_caveats"

        semantic = run_case(
            probe, base, "semantic",
            lambda _source, local: write(local / "README.md", b"different\n"),
        )
        assert [entry["path"] for entry in semantic["semantic_differences"]] == ["README.md"]
        assert semantic["verdict"] == "blocked"

        missing = run_case(
            probe, base, "missing",
            lambda _source, local: (local / "README.md").unlink(),
        )
        assert [entry["path"] for entry in missing["missing_files"]] == ["README.md"]
        assert missing["verdict"] == "blocked"

        benign = run_case(
            probe, base, "benign-extra",
            lambda _source, local: write(local / "host-note.txt", b"host metadata\n"),
        )
        extra = next(entry for entry in benign["foreign_extras"] if entry["path"] == "host-note.txt")
        assert extra["blocking"] is False
        assert benign["verdict"] == "qualified_with_caveats"

        py_extra = run_case(
            probe, base, "python-extra",
            lambda _source, local: write(local / "rogue.py", b"VALUE = 1\n"),
        )
        extra = next(entry for entry in py_extra["foreign_extras"] if entry["path"] == "rogue.py")
        assert extra["blocking"] is True and py_extra["verdict"] == "blocked"

        policy_extra = run_case(
            probe, base, "policy-extra",
            lambda _source, local: write(local / "references" / "policies" / "rogue.json", b"{}\n"),
        )
        extra = next(entry for entry in policy_extra["foreign_extras"] if entry["path"].endswith("rogue.json"))
        assert extra["blocking"] is True and policy_extra["verdict"] == "blocked"

        version = run_case(
            probe, base, "version-mismatch",
            lambda _source, local: write(
                local / ".claude-plugin" / "plugin.json",
                json.dumps({"name": "fixture-plugin", "version": "9.9.9"}).encode(),
            ),
        )
        assert version["identity"]["version_match"] is False
        assert version["verdict"] == "blocked"

        suffix = run_case(
            probe, base, "host-suffix",
            lambda _source, local: write(
                local / ".claude-plugin" / "plugin.json",
                json.dumps({"name": "fixture-plugin", "version": "1.2.3+codex.fixture"}).encode(),
            ),
        )
        assert suffix["identity"]["version_match"] is True
        assert suffix["identity"]["exact_version_match"] is False
        assert suffix["identity"]["embedded"]["manifest"]["host_suffix"] == "+codex.fixture"
        assert suffix["verdict"] == "qualified_with_caveats"

        prov_source = base / "provenance-mismatch" / "source"
        prov_local = base / "provenance-mismatch" / "local"
        package(prov_source)
        head = git_commit(prov_source)
        assert len(head) == 40
        copy_package(prov_source, prov_local)
        write(
            prov_local / "PROVENANCE.json",
            json.dumps(provenance_record(prov_source, "0" * 40)).encode(),
        )
        prov_out = prov_source / "releases" / "verification" / "fixture" / "runtime-plane.json"
        provenance = probe.probe_plane(
            local_root=prov_local, baseline_root=prov_source, out_path=prov_out
        )
        validate(provenance)
        assert provenance["identity"]["provenance_match"] is False
        assert provenance["verdict"] == "blocked"

        canonical_source = base / "provenance-match" / "source"
        canonical_local = base / "provenance-match" / "local"
        package(canonical_source)
        canonical_head = git_commit(canonical_source)
        canonical_out = canonical_source / "releases" / "verification" / "fixture" / "runtime-plane.json"
        copy_package(canonical_source, canonical_local)
        write(
            canonical_local / "PROVENANCE.json",
            json.dumps(provenance_record(canonical_source, canonical_head)).encode(),
        )
        canonical = probe.probe_plane(
            local_root=canonical_local, baseline_root=canonical_source, out_path=canonical_out
        )
        validate(canonical)
        assert canonical["identity"]["provenance_match"] is True
        assert canonical["identity"]["canonical_archive_claim"] is True
        assert canonical["verdict"] == "qualified"

        source_plane = base / "source-output-lane"
        package(source_plane)
        emitted_receipt = probe.probe_plane(
            local_root=source_plane, baseline_root=source_plane, out_path=None
        )
        validate(emitted_receipt)
        assert not (source_plane / "releases").exists()
        governed_out = source_plane / "releases" / "verification" / "fixture" / "runtime-plane.json"
        source_receipt = probe.probe_plane(
            local_root=source_plane, baseline_root=source_plane, out_path=governed_out
        )
        validate(source_receipt)
        assert governed_out.is_file()
        try:
            probe.probe_plane(
                local_root=source_plane,
                baseline_root=source_plane,
                out_path=source_plane / "reviews" / "runtime-plane.json",
            )
        except probe.ProbeRefusal as exc:
            assert exc.code == "RUNTIME-PLANE-OUTPUT"
        else:
            raise AssertionError("arbitrary in-root receipt path was accepted")
        try:
            probe.probe_plane(
                local_root=source_plane,
                baseline_root=source_plane,
                out_path=base / "outside" / "runtime-plane.json",
            )
        except probe.ProbeRefusal as exc:
            assert exc.code == "RUNTIME-PLANE-OUTPUT"
        else:
            raise AssertionError("receipt path outside the package evidence lane was accepted")

        governed = base / "governed-workspace"
        write(
            governed / "governance" / "output-routing" / "output_routing.yaml",
            b"schema_version: 1\n",
        )
        protected_source = governed / "protected" / "runtime-source"
        package(protected_source)
        prior_extra = os.environ.get("COAUTHOR_EXTRA_GOVERNED_ROOTS")
        os.environ["COAUTHOR_EXTRA_GOVERNED_ROOTS"] = str(governed)
        try:
            probe.probe_plane(
                local_root=protected_source,
                baseline_root=protected_source,
                out_path=(
                    protected_source / "releases" / "verification"
                    / "fixture" / "runtime-plane.json"
                ),
            )
        except probe.ProbeRefusal as exc:
            assert exc.code == "DEST-PROTECTED"
        else:
            raise AssertionError("protected governed baseline accepted a receipt")
        finally:
            if prior_extra is None:
                os.environ.pop("COAUTHOR_EXTRA_GOVERNED_ROOTS", None)
            else:
                os.environ["COAUTHOR_EXTRA_GOVERNED_ROOTS"] = prior_extra

        ungoverned_harness = base / "ungoverned-harness"
        ungoverned_source = base / "ungoverned-source"
        package(ungoverned_harness)
        package(ungoverned_source)
        original_harness = probe.destinations.HARNESS
        probe.destinations.HARNESS = ungoverned_harness
        try:
            probe.probe_plane(
                local_root=ungoverned_source,
                baseline_root=ungoverned_source,
                out_path=(
                    ungoverned_source / "releases" / "verification"
                    / "fixture" / "runtime-plane.json"
                ),
            )
        except probe.ProbeRefusal as exc:
            assert exc.code == "DEST-UNGOVERNED"
        else:
            raise AssertionError("ungoverned baseline accepted a receipt")
        finally:
            probe.destinations.HARNESS = original_harness

        mutation_source = base / "pre-post-mutation" / "source"
        mutation_local = base / "pre-post-mutation" / "local"
        mutation_out = mutation_source / "releases" / "verification" / "fixture" / "runtime-plane.json"
        package(mutation_source, mutating_suite=True)
        copy_package(mutation_source, mutation_local)
        mutation = probe.probe_plane(
            local_root=mutation_local, baseline_root=mutation_source, out_path=mutation_out
        )
        validate(mutation)
        assert mutation["package_digests"]["stable"] is False
        assert mutation["verdict"] == "blocked"
        assert any(f["code"] == "RUNTIME-PLANE-MUTATED" for f in mutation["findings"])

    print("PASS: runtime-plane parity, authority, and stability boundaries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
