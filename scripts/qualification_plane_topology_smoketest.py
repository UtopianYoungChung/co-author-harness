#!/usr/bin/env python3
"""Red-first contract for five-plane release qualification topology."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parent.parent
MODULE = ROOT / "scripts" / "qualification_plane_topology.py"
SCHEMA = ROOT / "references" / "schemas" / "qualification_plane_topology_receipt.schema.json"


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True,
        encoding="utf-8", errors="strict", check=True,
    )
    return completed.stdout.strip()


def _expect(module, code: str, call) -> None:
    try:
        call()
    except module.PlaneTopologyRefusal as exc:
        assert exc.code == code, (code, exc.code, exc.message)
    else:
        raise AssertionError(f"expected {code}")


def _fixture(base: Path) -> tuple[list[dict[str, str]], str]:
    source = base / "source"
    source.mkdir()
    subprocess.run(["git", "init", "--quiet", "-b", "main"], cwd=source, check=True)
    _git(source, "config", "user.email", "fixture@example.invalid")
    _git(source, "config", "user.name", "Fixture")
    (source / "README.md").write_text("source\n", encoding="utf-8")
    _git(source, "add", ".")
    _git(source, "commit", "--quiet", "-m", "source")
    commit = _git(source, "rev-parse", "HEAD")

    build = base / "build"
    subprocess.run(["git", "clone", "--quiet", "--no-local", str(source), str(build)], check=True)
    _git(build, "checkout", "--quiet", "--detach", commit)
    provenance = (json.dumps({"schema": "coauthor-build-provenance/v1", "commit": commit}) + "\n").encode()
    archive = base / "artifact.zip"
    with zipfile.ZipFile(archive, "w") as package:
        package.writestr("PROVENANCE.json", provenance)
        package.writestr("payload.txt", b"payload\n")
    unpacked = base / "unpacked"
    cache = base / "installed-cache"
    unpacked.mkdir()
    cache.mkdir()
    (unpacked / "PROVENANCE.json").write_bytes(provenance)
    (cache / "PROVENANCE.json").write_bytes(provenance)
    planes = [
        {"plane_kind": "source", "path": str(source)},
        {"plane_kind": "build", "path": str(build)},
        {"plane_kind": "archive", "path": str(archive)},
        {"plane_kind": "unpacked", "path": str(unpacked)},
        {"plane_kind": "installed_cache", "path": str(cache)},
    ]
    return planes, commit


def main() -> int:
    assert MODULE.is_file(), f"RED: missing {MODULE.relative_to(ROOT)}"
    spec = importlib.util.spec_from_file_location("qualification_plane_topology", MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert hasattr(module, "validate_topology")
    required = {
        "missing_plane_kind", "unknown_plane_kind", "five_planes_required",
        "attached_build_refused", "dirty_build_refused", "wrong_commit_refused",
        "overlap_refused", "casefold_alias_refused", "nfc_alias_refused",
        "reparse_refused", "archive_provenance_mismatch_refused",
        "git_metadata_outside_source_build_refused",
        "post_build_source_residue_refused_before_suites",
        "source_preflight_refuses_dirty_before_product_suites",
        "live_git_state_rechecked_before_suites",
        "receipt_path_reparse_rechecked_before_suites",
        "final_source_stability_rechecked_before_receipt",
    }
    advertised = set(getattr(module, "REGRESSION_CONTRACT", ()))
    assert required <= advertised, f"missing topology contracts: {sorted(required-advertised)}"
    with tempfile.TemporaryDirectory(prefix="qualification-topology-") as td:
        planes, commit = _fixture(Path(td))
        preimage = module.capture_source_snapshot(Path(planes[0]["path"]))

        source_preflight = subprocess.run(
            [sys.executable, "-B", str(MODULE), "snapshot-source", "--source-root", planes[0]["path"]],
            capture_output=True, check=False,
        )
        assert source_preflight.returncode == 0, source_preflight.stderr.decode("utf-8", errors="strict")
        assert json.loads(source_preflight.stdout) == preimage
        preflight_residue = Path(planes[0]["path"]) / "preflight-residue.txt"
        preflight_residue.write_text("residue\n", encoding="utf-8")
        dirty_preflight = subprocess.run(
            [sys.executable, "-B", str(MODULE), "snapshot-source", "--source-root", planes[0]["path"]],
            capture_output=True, check=False,
        )
        assert dirty_preflight.returncode == 4
        assert "PLANE-SOURCE-DIRTY" in dirty_preflight.stderr.decode("utf-8", errors="strict")
        preflight_residue.unlink()

        def validate_current(candidate):
            return module.validate_topology(
                candidate, source_commit=commit, source_preimage=preimage,
            )

        result = validate_current(planes)
        assert result["verdict"] == "qualified"
        assert [row["plane_kind"] for row in result["planes"]] == list(module.PLANE_KINDS)
        validator = jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))
        validator.validate(result)
        verified, verified_sha = module.verify_topology_receipt_binding(
            result,
            source_commit=commit,
            bindings={
                "source": Path(planes[0]["path"]),
                "archive": Path(planes[2]["path"]),
                "installed_cache": Path(planes[4]["path"]),
            },
        )
        assert verified == result and len(verified_sha) == 64

        build = Path(planes[1]["path"])
        _git(build, "switch", "--quiet", "-c", "receipt-became-attached")
        _expect(
            module,
            "PLANE-BUILD-ATTACHED",
            lambda: module.verify_topology_receipt_binding(
                result, source_commit=commit, bindings={"build": build},
            ),
        )
        _git(build, "checkout", "--quiet", "--detach", commit)

        cache = Path(planes[4]["path"])
        cache_target = cache.with_name("installed-cache-target")
        cache.rename(cache_target)
        try:
            try:
                os.symlink(cache_target, cache, target_is_directory=True)
            except OSError:
                created = subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(cache), str(cache_target)],
                    capture_output=True, check=False,
                ).returncode == 0
                assert created, "could not construct receipt-path reparse fixture"
            _expect(
                module,
                "PLANE-REPARSE",
                lambda: module.verify_topology_receipt_binding(
                    result, source_commit=commit, bindings={"installed_cache": cache},
                ),
            )
        finally:
            if cache.exists() or cache.is_symlink():
                cache.unlink() if cache.is_symlink() else os.rmdir(cache)
            cache_target.rename(cache)

        original_git_facts = module._git_facts
        late_residue = Path(planes[0]["path"]) / "late-source-residue.txt"
        mutated = False

        def mutate_after_source_git_check(root, kind, expected_commit):
            nonlocal mutated
            facts = original_git_facts(root, kind, expected_commit)
            if kind == "source" and not mutated:
                late_residue.write_text("late mutation\n", encoding="utf-8")
                mutated = True
            return facts

        module._git_facts = mutate_after_source_git_check
        try:
            _expect(module, "PLANE-SOURCE-DIRTY", lambda: validate_current(planes))
        finally:
            module._git_facts = original_git_facts
            late_residue.unlink(missing_ok=True)

        cache_drift = Path(planes[4]["path"]) / "drift.txt"
        cache_drift.write_text("drift\n", encoding="utf-8")
        _expect(
            module,
            "PLANE-TOPOLOGY-DRIFT",
            lambda: module.verify_topology_receipt_binding(
                result,
                source_commit=commit,
                bindings={"installed_cache": Path(planes[4]["path"])},
            ),
        )
        cache_drift.unlink()

        spec_path = Path(td) / "topology-spec.json"
        preimage_path = Path(td) / "source-preimage.json"
        spec_path.write_text(json.dumps({"source_commit": commit, "planes": planes}), encoding="utf-8")
        preimage_path.write_text(json.dumps(preimage), encoding="utf-8")
        cli = subprocess.run(
            [sys.executable, "-B", str(MODULE), "validate", "--spec", str(spec_path),
             "--source-preimage", str(preimage_path)],
            capture_output=True, check=False,
        )
        assert cli.returncode == 0, cli.stderr.decode("utf-8", errors="strict")
        assert json.loads(cli.stdout) == result
        forged = json.loads(json.dumps(result))
        forged["planes"][4]["plane_kind"] = "unpacked"
        try:
            validator.validate(forged)
        except jsonschema.ValidationError:
            pass
        else:
            raise AssertionError("receipt schema accepted a duplicate-kind five-plane receipt")

        forged_shape = json.loads(json.dumps(result))
        forged_shape["planes"][0]["path_kind"] = "file"
        forged_shape["planes"][0]["git_state"] = "absent"
        try:
            validator.validate(forged_shape)
        except jsonschema.ValidationError:
            pass
        else:
            raise AssertionError("receipt schema accepted an impossible source-plane shape")

        _expect(
            module,
            "PLANE-SOURCE-PREIMAGE-MISSING",
            lambda: module.validate_topology(planes, source_commit=commit),
        )

        missing_kind = [dict(row) for row in planes]
        missing_kind[0].pop("plane_kind")
        _expect(module, "PLANE-KIND-MISSING", lambda: validate_current(missing_kind))
        unknown_kind = [dict(row) for row in planes]
        unknown_kind[0]["plane_kind"] = "mystery"
        _expect(module, "PLANE-KIND-UNKNOWN", lambda: validate_current(unknown_kind))
        _expect(module, "PLANE-FIVE-REQUIRED", lambda: validate_current(planes[:-1]))

        build = Path(planes[1]["path"])
        _git(build, "switch", "--quiet", "-c", "attached")
        _expect(module, "PLANE-BUILD-ATTACHED", lambda: validate_current(planes))
        _git(build, "checkout", "--quiet", "--detach", commit)
        (build / "dirty.txt").write_text("dirty\n", encoding="utf-8")
        _expect(module, "PLANE-BUILD-DIRTY", lambda: validate_current(planes))
        (build / "dirty.txt").unlink()
        _git(build, "commit", "--quiet", "--allow-empty", "-m", "wrong commit")
        _expect(module, "PLANE-BUILD-COMMIT", lambda: validate_current(planes))
        _git(build, "checkout", "--quiet", "--detach", commit)

        overlap = [dict(row) for row in planes]
        overlap_root = Path(planes[3]["path"]) / "cache-child"
        overlap_root.mkdir()
        shutil.copy2(Path(planes[3]["path"]) / "PROVENANCE.json", overlap_root / "PROVENANCE.json")
        overlap[4]["path"] = str(overlap_root)
        _expect(module, "PLANE-PATH-OVERLAP", lambda: validate_current(overlap))

        casefold = [dict(row) for row in planes]
        casefold[4]["path"] = str(Path(planes[3]["path"])).upper()
        _expect(module, "PLANE-PATH-ALIAS", lambda: validate_current(casefold))

        nfc = [dict(row) for row in planes]
        nfc[3]["path"] = str(Path(td) / "caf\u00e9")
        nfc[4]["path"] = str(Path(td) / "cafe\u0301")
        _expect(module, "PLANE-PATH-ALIAS", lambda: validate_current(nfc))

        archive_path = Path(planes[2]["path"])
        with zipfile.ZipFile(archive_path, "w") as package:
            package.writestr("PROVENANCE.json", json.dumps({"schema": "coauthor-build-provenance/v1", "commit": "0" * 40}))
        _expect(module, "PLANE-PROVENANCE-MISMATCH", lambda: validate_current(planes))
        with zipfile.ZipFile(archive_path, "w") as package:
            package.writestr("PROVENANCE.json", json.dumps({"schema": "coauthor-build-provenance/v1", "commit": commit}))
            package.writestr(".git/config", b"contamination\n")
        _expect(module, "PLANE-GIT-CONTAMINATION", lambda: validate_current(planes))
        with zipfile.ZipFile(archive_path, "w") as package:
            package.writestr("PROVENANCE.json", json.dumps({"schema": "coauthor-build-provenance/v1", "commit": commit}))

        cache = Path(planes[4]["path"])
        (cache / ".git").mkdir()
        _expect(module, "PLANE-GIT-CONTAMINATION", lambda: validate_current(planes))
        shutil.rmtree(cache / ".git")

        descendant_alias = cache / "source-alias"
        try:
            os.symlink(Path(planes[0]["path"]), descendant_alias, target_is_directory=True)
        except OSError:
            created = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(descendant_alias), str(Path(planes[0]["path"]))],
                capture_output=True, check=False,
            ).returncode == 0
            assert created, "could not construct descendant reparse fixture"
        _expect(
            module,
            "PLANE-REPARSE",
            lambda: module.validate_topology(
                planes,
                source_commit=commit,
                source_preimage=module.capture_source_snapshot(Path(planes[0]["path"])),
            ),
        )
        if descendant_alias.exists() or descendant_alias.is_symlink():
            descendant_alias.unlink() if descendant_alias.is_symlink() else os.rmdir(descendant_alias)

        source = Path(planes[0]["path"])
        preimage = module.capture_source_snapshot(source)
        (source / "post-build.plugin").write_bytes(b"residue")
        suite_started = False
        try:
            module.validate_topology(planes, source_commit=commit, source_preimage=preimage)
            suite_started = True
        except module.PlaneTopologyRefusal as exc:
            assert exc.code == "PLANE-SOURCE-RESIDUE"
        assert suite_started is False
        (source / "post-build.plugin").unlink()

        alias = Path(td) / "cache-alias"
        try:
            os.symlink(cache, alias, target_is_directory=True)
        except OSError:
            created = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(alias), str(cache)],
                capture_output=True, check=False,
            ).returncode == 0
            assert created, "could not construct reparse fixture"
        reparse = [dict(row) for row in planes]
        reparse[4]["path"] = str(alias)
        _expect(module, "PLANE-REPARSE", lambda: validate_current(reparse))
        if alias.exists() or alias.is_symlink():
            alias.unlink() if alias.is_symlink() else os.rmdir(alias)

    print(f"qualification_plane_topology_smoketest: PASS {len(required)} contracts + 27 behavioral cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
