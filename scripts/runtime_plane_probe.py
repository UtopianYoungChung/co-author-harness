#!/usr/bin/env python3
"""Compare one runtime plane with an explicit source baseline and self-test it.

The receipt is diagnostic host evidence.  It never installs a plugin, mutates
governed project state, or turns a source/cache directory into a canonical
archive extraction merely because its executable checks pass.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import io
import json
import os
import platform
import re
import site
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator
import destination_capability as destinations
from qualification_environment import (
    QualificationEnvironmentRefusal,
    assert_ambient_clean,
    controlled_environment,
)
import qualification_plane_topology as topology


ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "references" / "schemas" / "runtime_plane_receipt.schema.json"
MANIFEST_REL = "version.json"
PROVENANCE_REL = "PROVENANCE.json"
DIGEST_ALGORITHM = "sha256(path-NUL-kind-NUL-content-sha256-LF)"
COMMIT_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
VERSION_RE = re.compile(r"^(\d+\.\d+\.\d+)(.*)$")

DEFAULT_SUITES: tuple[Mapping[str, str], ...] = (
    {
        "name": "governed_product_gate_self_check",
        "kind": "governed_product_gate_self_check",
        "script": "scripts/run_product_gate_smoketest.py",
    },
    {
        "name": "schema_runtime_check",
        "kind": "portable_core",
        "script": "scripts/schema_runtime_check.py",
    },
    {
        "name": "version_check",
        "kind": "portable_core",
        "script": "scripts/version-check.py",
    },
    {
        "name": "skill_check",
        "kind": "portable_core",
        "script": "scripts/skill-check.py",
    },
    {
        "name": "shipment_manifest_v2_smoketest",
        "kind": "portable_core",
        "script": "scripts/shipment_manifest_smoketest.py",
    },
    {
        "name": "output_contract_v3_smoketest",
        "kind": "portable_core",
        "script": "scripts/output_contract_smoketest.py",
    },
    {
        "name": "output_economy_static_check",
        "kind": "portable_core",
        "script": "scripts/output_economy_check.py",
    },
)


class ProbeRefusal(RuntimeError):
    """A pre-receipt failure for an unsafe or incomplete invocation."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        check=False,
    )


def _source_commit(root: Path) -> str | None:
    try:
        top = _git(root, "rev-parse", "--show-toplevel")
    except OSError:
        return None
    if top.returncode != 0:
        return None
    try:
        if Path(top.stdout.strip()).resolve() != root:
            return None
    except OSError:
        return None
    head = _git(root, "rev-parse", "HEAD")
    value = head.stdout.strip().lower() if head.returncode == 0 else ""
    return value if COMMIT_RE.fullmatch(value) else None


def _baseline_members(root: Path, commit: str | None) -> list[str] | None:
    if commit is None:
        return None
    result = _git(root, "ls-tree", "-r", "--name-only", "-z", commit)
    if result.returncode != 0:
        return None
    names = [name for name in result.stdout.split("\0") if name]
    return sorted(name.replace("\\", "/") for name in names if not name.lower().endswith((".zip", ".plugin")))


def _commit_inventory(root: Path, commit: str) -> dict[str, dict[str, Any]]:
    """Read baseline bytes from the named Git tree, never from a dirty worktree."""

    try:
        tree = subprocess.run(
            ["git", "-C", str(root), "ls-tree", "-r", "-z", commit],
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise ProbeRefusal("RUNTIME-PLANE-SOURCE-COMMIT", f"cannot inspect source commit: {exc}") from exc
    if tree.returncode != 0:
        raise ProbeRefusal("RUNTIME-PLANE-SOURCE-COMMIT", "cannot enumerate the exact source commit")
    inventory: dict[str, dict[str, Any]] = {}
    for entry in filter(None, tree.stdout.split(b"\0")):
        try:
            header, raw_name = entry.split(b"\t", 1)
            mode, object_type, object_id = header.decode("ascii").split()
            rel = raw_name.decode("utf-8", errors="strict").replace("\\", "/")
        except (ValueError, UnicodeDecodeError) as exc:
            raise ProbeRefusal(
                "RUNTIME-PLANE-SOURCE-COMMIT", "source commit contains an undecodable tree entry"
            ) from exc
        if rel.lower().endswith((".zip", ".plugin")):
            continue
        if object_type != "blob":
            raise ProbeRefusal(
                "RUNTIME-PLANE-SOURCE-COMMIT", f"unsupported non-blob package member: {rel}"
            )
        blob = subprocess.run(
            ["git", "-C", str(root), "cat-file", "blob", object_id],
            capture_output=True,
            check=False,
        )
        if blob.returncode != 0:
            raise ProbeRefusal(
                "RUNTIME-PLANE-SOURCE-COMMIT", f"cannot read source-commit blob: {rel}"
            )
        inventory[rel] = {
            "path": rel,
            "kind": "symlink" if mode == "120000" else "file",
            "sha256": _sha(blob.stdout),
            "_bytes": blob.stdout,
        }
    return dict(sorted(inventory.items()))


def _entry(path: Path, rel: str) -> dict[str, Any]:
    if path.is_symlink():
        data = os.readlink(path).encode("utf-8", errors="surrogatepass")
        kind = "symlink"
    else:
        data = path.read_bytes()
        kind = "file"
    return {"path": rel, "kind": kind, "sha256": _sha(data), "_bytes": data}


def _walk_inventory(
    root: Path,
    members: Iterable[str] | None = None,
    excluded: Iterable[str] = (),
) -> dict[str, dict[str, Any]]:
    inventory: dict[str, dict[str, Any]] = {}
    excluded_set = set(excluded)
    if members is not None:
        for rel in members:
            if rel in excluded_set:
                continue
            path = root / Path(rel)
            if path.is_file() or path.is_symlink():
                inventory[rel] = _entry(path, rel)
            else:
                raise ProbeRefusal(
                    "RUNTIME-PLANE-BASELINE-MISSING",
                    f"tracked baseline member is absent from the explicit source root: {rel}",
                )
        return inventory

    for current, dirs, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        dirs[:] = sorted(name for name in dirs if name != ".git")
        for name in list(dirs):
            path = current_path / name
            if path.is_symlink():
                rel = path.relative_to(root).as_posix()
                inventory[rel] = _entry(path, rel)
                dirs.remove(name)
        for name in sorted(files):
            path = current_path / name
            rel = path.relative_to(root).as_posix()
            if rel in excluded_set:
                continue
            inventory[rel] = _entry(path, rel)
    return dict(sorted(inventory.items()))


def _digest(inventory: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    material = bytearray()
    for rel, record in sorted(inventory.items()):
        material.extend(rel.encode("utf-8"))
        material.extend(b"\0")
        material.extend(str(record["kind"]).encode("ascii"))
        material.extend(b"\0")
        material.extend(str(record["sha256"]).encode("ascii"))
        material.extend(b"\n")
    return {"algorithm": DIGEST_ALGORITHM, "sha256": _sha(bytes(material)), "file_count": len(inventory)}


def _public_file(record: Mapping[str, Any]) -> dict[str, Any]:
    return {key: record[key] for key in ("path", "kind", "sha256")}


def _comparison(baseline: Mapping[str, Any], local: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "path": baseline["path"],
        "baseline_kind": baseline["kind"],
        "local_kind": local["kind"],
        "baseline_sha256": baseline["sha256"],
        "local_sha256": local["sha256"],
    }


def _is_crlf_only(baseline: Mapping[str, Any], local: Mapping[str, Any]) -> bool:
    if baseline["kind"] != "file" or local["kind"] != "file":
        return False
    try:
        baseline_text = baseline["_bytes"].decode("utf-8", errors="strict")
        local_text = local["_bytes"].decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return False
    baseline_lf = baseline_text.replace("\r\n", "\n")
    local_lf = local_text.replace("\r\n", "\n")
    return (
        "\r" not in baseline_lf
        and "\r" not in local_lf
        and baseline_lf == local_lf
    )


def _safe_archive_name(name: str) -> bool:
    """Accept only one portable, relative file spelling per ZIP member."""

    if not name or "\\" in name or name.startswith(("/", "\\")):
        return False
    if re.match(r"^[A-Za-z]:", name):
        return False
    parts = PurePosixPath(name).parts
    return (
        not name.endswith("/")
        and bool(parts)
        and all(part not in {"", ".", ".."} for part in parts)
        and PurePosixPath(name).as_posix() == name
    )


def _archive_inventory(snapshot: bytes) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Read a ZIP without extraction and report every unsafe/ambiguous member."""

    inventory: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    seen_portable: set[str] = set()
    try:
        with zipfile.ZipFile(io.BytesIO(snapshot), "r") as archive:
            for info in archive.infolist():
                name = info.filename
                portable = name.casefold()
                if not _safe_archive_name(name):
                    errors.append(f"unsafe archive member: {name!r}")
                    continue
                if portable in seen_portable:
                    errors.append(f"duplicate archive member: {name!r}")
                    continue
                seen_portable.add(portable)
                mode = (info.external_attr >> 16) & 0o170000
                if mode == 0o120000:
                    errors.append(f"archive symlink is forbidden: {name!r}")
                    continue
                try:
                    data = archive.read(info)
                except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
                    errors.append(f"unreadable archive member {name!r}: {exc}")
                    continue
                inventory[name] = {
                    "path": name,
                    "kind": "file",
                    "sha256": _sha(data),
                    "_bytes": data,
                }
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        errors.append(f"cleared ZIP is unreadable: {exc}")
    return dict(sorted(inventory.items())), errors


def _archive_provenance(
    inventory: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Any], bool]:
    """Validate the builder provenance against the archive it actually inhabits."""

    record = inventory.get(PROVENANCE_REL)
    result: dict[str, Any] = {
        "kind": "embedded_archive",
        "path": PROVENANCE_REL,
        "status": "missing",
        "schema": None,
        "commit": None,
        "sha256": None,
    }
    if record is None:
        return result, False
    raw = record["_bytes"]
    result["sha256"] = record["sha256"]
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        result["status"] = "invalid"
        return result, False
    schema = value.get("schema") if isinstance(value, dict) else None
    commit = value.get("commit") if isinstance(value, dict) else None
    result["schema"] = schema if isinstance(schema, str) else None
    result["commit"] = (
        commit.lower()
        if isinstance(commit, str) and COMMIT_RE.fullmatch(commit.lower())
        else None
    )
    package_members = {key: row for key, row in inventory.items() if key != PROVENANCE_REL}
    valid = (
        isinstance(value, dict)
        and schema == "coauthor-build-provenance/v1"
        and result["commit"] is not None
        and value.get("enumerator")
        == "scripts/package_enumeration.py::enumerate_package_files"
        and value.get("package_member_count") == len(package_members)
        and not isinstance(value.get("package_member_count"), bool)
        and value.get("archive_member_count") == len(inventory)
        and not isinstance(value.get("archive_member_count"), bool)
        and value.get("toolchain_is_commit") is True
        and isinstance(value.get("toolchain"), dict)
        and isinstance(value.get("runtime"), dict)
        and set(value.get("runtime", {}))
        == {"python", "python_full", "zlib", "compression", "note"}
        and all(isinstance(item, str) and item for item in value.get("runtime", {}).values())
        and value.get("runtime", {}).get("compression") == "ZIP_DEFLATED"
        and isinstance(value.get("zip_date_time_stored"), list)
        and len(value.get("zip_date_time_stored")) == 6
        and all(
            isinstance(item, int) and not isinstance(item, bool)
            for item in value.get("zip_date_time_stored", [])
        )
        and isinstance(value.get("zip_date_time_commit"), list)
        and len(value.get("zip_date_time_commit")) == 6
        and all(
            isinstance(item, int) and not isinstance(item, bool)
            for item in value.get("zip_date_time_commit", [])
        )
    )
    if valid:
        for rel, expected_sha in value["toolchain"].items():
            if (
                not isinstance(rel, str)
                or not isinstance(expected_sha, str)
                or not re.fullmatch(r"[0-9a-f]{64}", expected_sha)
                or rel not in package_members
                or package_members[rel]["sha256"] != expected_sha
            ):
                valid = False
                break
    result["status"] = "valid" if valid else "invalid"
    return result, valid


def _inventories_equal(
    left: Mapping[str, Mapping[str, Any]],
    right: Mapping[str, Mapping[str, Any]],
) -> bool:
    return set(left) == set(right) and all(
        left[rel]["kind"] == right[rel]["kind"]
        and left[rel]["sha256"] == right[rel]["sha256"]
        for rel in left
    )


def _foreign_reason(rel: str, kind: str) -> tuple[bool, str]:
    lower = rel.lower()
    suffix = Path(lower).suffix
    if rel == PROVENANCE_REL:
        return False, "embedded_provenance_metadata"
    if kind == "symlink":
        return True, "foreign_symlink_can_redirect_runtime_loading"
    if suffix in {".py", ".pyi", ".pyc", ".pyo", ".pth", ".pyd", ".so", ".dll", ".dylib"}:
        return True, "foreign_import_participant"
    if lower.startswith((".claude-plugin/", ".codex-plugin/", ".cursor-plugin/")):
        return True, "foreign_host_manifest_surface"
    if lower.startswith(("agents/", "skills/")):
        return True, "foreign_instruction_loading_surface"
    if lower in {"agents.md", "claude.md"}:
        return True, "foreign_instruction_loading_surface"
    if lower.startswith("references/policies/") or (
        lower.startswith("references/") and suffix in {".json", ".yaml", ".yml"}
    ):
        return True, "foreign_policy_loading_surface"
    return False, "foreign_nonparticipating_file"


def _manifest(root: Path) -> dict[str, Any]:
    path = root / MANIFEST_REL
    result: dict[str, Any] = {
        "path": MANIFEST_REL,
        "status": "missing",
        "name": None,
        "version": None,
        "base_version": None,
        "host_suffix": None,
        "sha256": None,
    }
    if not path.is_file():
        return result
    raw = path.read_bytes()
    result["sha256"] = _sha(raw)
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        result["status"] = "invalid"
        return result
    name = value.get("name") if isinstance(value, dict) else None
    version = value.get("version") if isinstance(value, dict) else None
    version_match = VERSION_RE.fullmatch(version) if isinstance(version, str) else None
    if isinstance(name, str) and name and version_match:
        suffix = version_match.group(2)
        result.update(
            status="valid",
            name=name,
            version=version,
            base_version=version_match.group(1),
            host_suffix=suffix or None,
        )
    else:
        result["status"] = "invalid"
    return result


def _source_provenance(root: Path, commit: str | None) -> dict[str, Any]:
    return {
        "kind": "source_git",
        "path": str(root / ".git") if commit else None,
        "status": "valid" if commit else "missing",
        "schema": "git-commit" if commit else None,
        "commit": commit,
        "sha256": None,
    }


def _embedded_provenance(
    root: Path,
    local_inventory: Mapping[str, Mapping[str, Any]],
    expected_package_count: int,
) -> dict[str, Any]:
    path = root / PROVENANCE_REL
    result: dict[str, Any] = {
        "kind": "embedded_archive",
        "path": PROVENANCE_REL,
        "status": "missing",
        "schema": None,
        "commit": None,
        "sha256": None,
    }
    if not path.is_file():
        return result
    raw = path.read_bytes()
    result["sha256"] = _sha(raw)
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        result["status"] = "invalid"
        return result
    schema = value.get("schema") if isinstance(value, dict) else None
    commit = value.get("commit") if isinstance(value, dict) else None
    result["schema"] = schema if isinstance(schema, str) else None
    result["commit"] = commit.lower() if isinstance(commit, str) and COMMIT_RE.fullmatch(commit.lower()) else None
    structurally_valid = (
        isinstance(value, dict)
        and value.get("schema") == "coauthor-build-provenance/v1"
        and result["commit"] is not None
        and value.get("enumerator") == "scripts/package_enumeration.py::enumerate_package_files"
        and isinstance(value.get("package_member_count"), int)
        and not isinstance(value.get("package_member_count"), bool)
        and value.get("package_member_count") == expected_package_count
        and isinstance(value.get("archive_member_count"), int)
        and not isinstance(value.get("archive_member_count"), bool)
        and value.get("archive_member_count") == value.get("package_member_count") + 1
        and value.get("toolchain_is_commit") is True
        and isinstance(value.get("toolchain"), dict)
        and isinstance(value.get("runtime"), dict)
        and set(value.get("runtime", {})) == {"python", "python_full", "zlib", "compression", "note"}
        and all(isinstance(item, str) and item for item in value.get("runtime", {}).values())
        and value.get("runtime", {}).get("compression") == "ZIP_DEFLATED"
        and isinstance(value.get("zip_date_time_stored"), list)
        and len(value.get("zip_date_time_stored")) == 6
        and all(isinstance(item, int) and not isinstance(item, bool) for item in value.get("zip_date_time_stored", []))
        and isinstance(value.get("zip_date_time_commit"), list)
        and len(value.get("zip_date_time_commit")) == 6
        and all(isinstance(item, int) and not isinstance(item, bool) for item in value.get("zip_date_time_commit", []))
    )
    if structurally_valid:
        for rel, expected_sha in value["toolchain"].items():
            if (
                not isinstance(rel, str)
                or not isinstance(expected_sha, str)
                or not re.fullmatch(r"[0-9a-f]{64}", expected_sha)
                or rel not in local_inventory
                or local_inventory[rel]["sha256"] != expected_sha
            ):
                structurally_valid = False
                break
    if structurally_valid:
        result["status"] = "valid"
    else:
        result["status"] = "invalid"
    return result


def _allowed_host_suffix(baseline_root: Path, local_root: Path, source: Mapping[str, Any], local: Mapping[str, Any]) -> bool:
    if (
        source.get("status") != "valid"
        or local.get("status") != "valid"
        or source.get("name") != local.get("name")
        or source.get("base_version") != local.get("base_version")
        or not local.get("host_suffix")
    ):
        return False
    try:
        source_value = json.loads((baseline_root / MANIFEST_REL).read_text(encoding="utf-8"))
        local_value = json.loads((local_root / MANIFEST_REL).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    if not isinstance(source_value, dict) or not isinstance(local_value, dict):
        return False
    adjusted = dict(local_value)
    adjusted["version"] = source_value.get("version")
    return adjusted == source_value


def _tool_versions() -> dict[str, str | None]:
    def installed(name: str) -> str | None:
        try:
            return importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            return None
    try:
        git_result = subprocess.run(
            ["git", "--version"], capture_output=True, text=True,
            encoding="utf-8", errors="replace", check=False,
        )
        git_version: str | None = git_result.stdout.strip() if git_result.returncode == 0 else None
    except OSError:
        git_version = None
    return {
        "python": platform.python_version(),
        "jsonschema": installed("jsonschema"),
        "referencing": installed("referencing"),
        "pyyaml": installed("PyYAML"),
        "git": git_version,
    }


def _dependency_paths() -> tuple[str, ...]:
    candidates = [*site.getsitepackages(), site.getusersitepackages()]
    return tuple(sorted({str(Path(path).resolve()) for path in candidates if path and Path(path).is_dir()}))


def _run_suites(
    local_root: Path,
    suites: Iterable[Mapping[str, str]],
    dependency_paths: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    dependencies = tuple(dependency_paths if dependency_paths is not None else _dependency_paths())
    child_env, _ = controlled_environment()
    # The suite interpreter remains isolated by ``-I`` and receives these
    # directories explicitly through ``site.addsitedir`` below.  A governed
    # suite can itself launch ``sys.executable`` without ``-I`` (the product
    # gate smoke test does this); that nested interpreter must inherit the
    # same qualified dependency set or it cannot import jsonschema/PyYAML.
    # Do not inherit an ambient PYTHONPATH: expose only the paths already
    # resolved and recorded by this probe.
    child_env["PYTHONPATH"] = os.pathsep.join(dependencies)
    for suite in suites:
        script = local_root / suite["script"]
        isolated_runner = (
            "import runpy,site,sys;"
            f"[site.addsitedir(path) for path in {dependencies!r}];"
            f"sys.path.insert(0,{str(script.parent)!r});"
            f"runpy.run_path({str(script)!r},run_name='__main__')"
        )
        argv = [sys.executable, "-I", "-B", "-c", isolated_runner]
        if not script.is_file():
            results.append({
                "name": suite["name"],
                "kind": suite["kind"],
                "script": suite["script"],
                "argv": argv,
                "cwd": str(local_root),
                "returncode": None,
                "status": "missing",
                "stdout_sha256": _sha(b""),
                "stderr_sha256": _sha(b""),
            })
            continue
        completed = subprocess.run(
            argv,
            cwd=local_root,
            env=child_env,
            capture_output=True,
            check=False,
        )
        results.append({
            "name": suite["name"],
            "kind": suite["kind"],
            "script": suite["script"],
            "argv": argv,
            "cwd": str(local_root),
            "returncode": completed.returncode,
            "status": "passed" if completed.returncode == 0 else "failed",
            "stdout_sha256": _sha(completed.stdout),
            "stderr_sha256": _sha(completed.stderr),
        })
    return results


def _not_run_suites(local_root: Path, suites: Iterable[Mapping[str, str]]) -> list[dict[str, Any]]:
    empty_sha = _sha(b"")
    return [
        {
            "name": suite["name"], "kind": suite["kind"], "script": suite["script"],
            "argv": [], "cwd": str(local_root), "returncode": None,
            "status": "not_run_preflight", "stdout_sha256": empty_sha,
            "stderr_sha256": empty_sha,
        }
        for suite in suites
    ]


def _finding(code: str, severity: str, message: str, path: str | None = None) -> dict[str, str]:
    value = {"code": code, "severity": severity, "message": message}
    if path:
        value["path"] = path
    return value


def _validate(receipt: Mapping[str, Any]) -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(receipt), key=lambda error: list(error.path))
    environment = receipt.get("environment", {})
    dependencies = environment.get("dependency_paths", []) if isinstance(environment, Mapping) else None
    if (
        isinstance(environment, Mapping)
        and isinstance(dependencies, list)
        and all(isinstance(path, str) for path in dependencies)
        and environment.get("suite_pythonpath") != os.pathsep.join(dependencies)
    ):
        errors.append("environment.suite_pythonpath does not equal the recorded dependency-path join")
    if errors:
        raise ProbeRefusal(
            "RUNTIME-PLANE-SCHEMA",
            "; ".join(
                error
                if isinstance(error, str)
                else f"{list(error.path)}: {error.message}"
                for error in errors
            ),
        )


def probe_plane(
    *,
    local_root: Path,
    baseline_root: Path,
    out_path: Path | None,
    cleared_zip_path: Path | None = None,
    source_commit: str | None = None,
    crlf_mode: str = "forbid",
    suites: Iterable[Mapping[str, str]] = DEFAULT_SUITES,
    plane_kind: str | None = None,
    topology_receipt: Path | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        assert_ambient_clean()
    except QualificationEnvironmentRefusal as exc:
        raise ProbeRefusal(exc.code, exc.message) from exc
    if plane_kind is None:
        raise ProbeRefusal("RUNTIME-PLANE-KIND-MISSING", "plane_kind is required")
    if plane_kind not in {"unpacked", "installed_cache"}:
        raise ProbeRefusal("RUNTIME-PLANE-KIND-UNKNOWN", f"unsupported plane_kind: {plane_kind}")
    local_root = local_root.resolve(strict=True)
    baseline_root = baseline_root.resolve(strict=True)
    if not local_root.is_dir() or not baseline_root.is_dir():
        raise ProbeRefusal("RUNTIME-PLANE-ROOT", "local and baseline roots must be directories")
    if crlf_mode not in {"forbid", "allow_utf8_crlf_only"}:
        raise ProbeRefusal("RUNTIME-PLANE-NORMALIZATION", f"unsupported CRLF mode: {crlf_mode}")
    if source_commit is not None:
        source_commit = source_commit.lower()
        if not COMMIT_RE.fullmatch(source_commit):
            raise ProbeRefusal("RUNTIME-PLANE-SOURCE-COMMIT", "source commit must be a full Git object id")
    resolved_zip: Path | None = None
    if cleared_zip_path is not None:
        try:
            resolved_zip = cleared_zip_path.resolve(strict=True)
        except FileNotFoundError:
            resolved_zip = cleared_zip_path.resolve()
    if out_path is not None:
        out_path = out_path.resolve()
        authorized_evidence_root = (baseline_root / "releases" / "verification").resolve()
        if not _inside(out_path, authorized_evidence_root):
            raise ProbeRefusal(
                "RUNTIME-PLANE-OUTPUT",
                "receipt output must be under the explicit baseline's "
                "releases/verification evidence lane",
            )
        try:
            destinations.assert_writable(
                out_path, purpose="runtime-plane qualification receipt"
            )
        except destinations.DestinationRefused as exc:
            raise ProbeRefusal(exc.code, str(exc)) from exc

    baseline_excluded: set[str] = set()
    local_excluded: set[str] = set()
    if out_path is not None:
        for candidate in (out_path, out_path.with_name(out_path.name + ".tmp")):
            if _inside(candidate, baseline_root):
                baseline_excluded.add(candidate.relative_to(baseline_root).as_posix())
            if _inside(candidate, local_root):
                local_excluded.add(candidate.relative_to(local_root).as_posix())
        evidence_dir = out_path.parent
        if _inside(evidence_dir, baseline_root):
            baseline_excluded.add(evidence_dir.relative_to(baseline_root).as_posix())

    actual_source_commit = _source_commit(baseline_root)
    baseline_inventory = (
        _commit_inventory(baseline_root, actual_source_commit)
        if actual_source_commit is not None
        else _walk_inventory(baseline_root, excluded=baseline_excluded)
    )
    local_pre = _walk_inventory(local_root, excluded=local_excluded)

    archive_inventory: dict[str, dict[str, Any]] = {}
    archive_errors: list[str] = []
    archive_snapshot: bytes | None = None
    if resolved_zip is not None:
        if resolved_zip.is_file():
            try:
                archive_snapshot = resolved_zip.read_bytes()
            except OSError as exc:
                archive_errors.append(f"cleared ZIP is unreadable: {exc}")
            else:
                archive_inventory, archive_errors = _archive_inventory(archive_snapshot)
        else:
            archive_errors.append("cleared ZIP path does not name a file")
    archive_provenance, archive_provenance_valid = _archive_provenance(archive_inventory)
    archive_package = {
        rel: row for rel, row in archive_inventory.items() if rel != PROVENANCE_REL
    }
    source_archive_equal = bool(archive_inventory) and _inventories_equal(
        baseline_inventory, archive_package,
    )
    local_embeds_provenance = PROVENANCE_REL in local_pre
    comparison_inventory = (
        archive_inventory
        if archive_inventory and local_embeds_provenance
        else archive_package
        if archive_inventory
        else baseline_inventory
    )

    cleared_zip: dict[str, Any] | None = None
    if (
        resolved_zip is not None
        and resolved_zip.is_file()
        and archive_snapshot is not None
        and source_commit is not None
        and archive_provenance.get("sha256") is not None
    ):
        cleared_zip = {
            "path": str(resolved_zip),
            "sha256": _sha(archive_snapshot),
            "byte_length": len(archive_snapshot),
            "source_commit": source_commit,
            "provenance_sha256": archive_provenance["sha256"],
        }

    exact_files: list[dict[str, Any]] = []
    crlf_only: list[dict[str, Any]] = []
    semantic_differences: list[dict[str, Any]] = []
    missing_files: list[dict[str, Any]] = []
    for rel, baseline in comparison_inventory.items():
        local = local_pre.get(rel)
        if local is None:
            missing_files.append(_public_file(baseline))
        elif baseline["kind"] == local["kind"] and baseline["sha256"] == local["sha256"]:
            exact_files.append(_comparison(baseline, local))
        elif baseline["kind"] == local["kind"] and _is_crlf_only(baseline, local):
            crlf_only.append(_comparison(baseline, local))
        else:
            semantic_differences.append(_comparison(baseline, local))

    foreign_extras: list[dict[str, Any]] = []
    for rel in sorted(set(local_pre) - set(comparison_inventory)):
        local = local_pre[rel]
        blocking, reason = _foreign_reason(rel, local["kind"])
        foreign_extras.append({**_public_file(local), "blocking": blocking, "reason": reason})

    source_manifest = _manifest(baseline_root)
    local_manifest = _manifest(local_root)
    source_provenance = _source_provenance(baseline_root, actual_source_commit)
    embedded_provenance = _embedded_provenance(
        local_root, local_pre, len(archive_package) if archive_inventory else len(baseline_inventory)
    )
    version_match: bool | None = None
    exact_version_match: bool | None = None
    if source_manifest["status"] == "valid" and local_manifest["status"] == "valid":
        version_match = (
            source_manifest["name"] == local_manifest["name"]
            and source_manifest["base_version"] == local_manifest["base_version"]
        )
        exact_version_match = (
            source_manifest["name"] == local_manifest["name"]
            and source_manifest["version"] == local_manifest["version"]
        )
    for difference in semantic_differences:
        difference.update(blocking=True, reason="semantic_or_file_kind_difference")
    provenance_match: bool | None = None
    provenance_binding = (
        embedded_provenance
        if embedded_provenance["status"] != "missing"
        else archive_provenance
    )
    if source_provenance["status"] == "valid" and provenance_binding["status"] == "valid":
        provenance_match = source_provenance["commit"] == provenance_binding["commit"]

    binding_commit = source_commit or actual_source_commit or ""
    topology_bindings = {"source": baseline_root, plane_kind: local_root}
    if resolved_zip is not None:
        topology_bindings["archive"] = resolved_zip
    try:
        topology_value, topology_sha256 = topology.verify_topology_receipt_binding(
            topology_receipt,
            source_commit=binding_commit,
            bindings=topology_bindings,
        )
    except topology.PlaneTopologyRefusal as exc:
        code = exc.code.replace("PLANE-", "RUNTIME-PLANE-", 1)
        raise ProbeRefusal(code, exc.message) from exc

    suites = tuple(dict(suite) for suite in suites)
    suite_signature = tuple(
        (suite.get("name"), suite.get("kind"), suite.get("script")) for suite in suites
    )
    required_signature = tuple(
        (suite["name"], suite["kind"], suite["script"]) for suite in DEFAULT_SUITES
    )
    if suite_signature != required_signature:
        raise ProbeRefusal(
            "RUNTIME-PLANE-SUITES",
            "the runtime qualification must run all seven frozen core suites exactly once",
        )
    externally_bound_without_local_provenance = (
        embedded_provenance["status"] == "missing"
        and archive_provenance_valid
        and source_archive_equal
        and source_commit is not None
        and actual_source_commit == source_commit
        and provenance_match is True
    )
    blocking_extras = [entry for entry in foreign_extras if entry["blocking"]]
    preflight_blocked = any((
        source_manifest["status"] != "valid",
        local_manifest["status"] != "valid",
        version_match is False,
        source_commit is None,
        resolved_zip is None,
        archive_provenance["status"] in {"missing", "invalid"},
        source_provenance["status"] == "missing",
        source_commit is not None and actual_source_commit != source_commit,
        bool(archive_errors),
        archive_provenance["status"] == "valid" and source_commit is not None
        and archive_provenance["commit"] != source_commit,
        bool(archive_inventory) and not source_archive_equal,
        embedded_provenance["status"] == "missing" and not externally_bound_without_local_provenance,
        embedded_provenance["status"] == "invalid",
        provenance_match is False,
        bool(crlf_only) and crlf_mode == "forbid",
        bool(semantic_differences),
        bool(missing_files),
        bool(blocking_extras),
    ))
    dependency_paths = _dependency_paths()
    suite_results = (
        _not_run_suites(local_root, suites)
        if preflight_blocked
        else _run_suites(local_root, suites, dependency_paths)
    )
    local_post = _walk_inventory(local_root, excluded=local_excluded)
    archive_changed = False
    if resolved_zip is not None and archive_snapshot is not None:
        try:
            archive_changed = resolved_zip.read_bytes() != archive_snapshot
        except OSError:
            archive_changed = True

    baseline_digest = _digest(comparison_inventory)
    pre_digest = _digest(local_pre)
    post_digest = _digest(local_post)
    stable = pre_digest == post_digest

    findings: list[dict[str, str]] = []
    for label, manifest in (("source", source_manifest), ("local", local_manifest)):
        if manifest["status"] != "valid":
            findings.append(_finding(
                "RUNTIME-PLANE-MANIFEST-" + manifest["status"].upper(),
                "BLOCKER",
                f"{label} plugin manifest is {manifest['status']}",
                manifest["path"],
            ))
    if version_match is False:
        findings.append(_finding(
            "RUNTIME-PLANE-VERSION-MISMATCH", "BLOCKER",
            "local manifest name/version differs from the explicit source baseline", MANIFEST_REL,
        ))
    if source_commit is None or resolved_zip is None or archive_provenance["status"] == "missing":
        findings.append(_finding(
            "CACHE-PROVENANCE-MISSING", "BLOCKER",
            "an exact cleared ZIP, explicit source commit, and embedded PROVENANCE.json are required",
            PROVENANCE_REL,
        ))
    if source_provenance["status"] == "missing":
        findings.append(_finding(
            "RUNTIME-PLANE-SOURCE-PROVENANCE-MISSING", "BLOCKER",
            "the baseline has no resolvable root Git commit",
        ))
    elif source_commit is not None and actual_source_commit != source_commit:
        findings.append(_finding(
            "RUNTIME-PLANE-SOURCE-COMMIT-MISMATCH", "BLOCKER",
            "the explicit cleared source commit differs from the baseline HEAD",
        ))
    for archive_error in archive_errors:
        findings.append(_finding(
            "RUNTIME-PLANE-ARCHIVE-UNSAFE", "BLOCKER", archive_error,
        ))
    if archive_changed:
        findings.append(_finding(
            "RUNTIME-PLANE-ARCHIVE-CHANGED", "BLOCKER",
            "the cleared ZIP path changed after its immutable qualification snapshot was captured",
        ))
    if archive_provenance["status"] == "invalid":
        findings.append(_finding(
            "RUNTIME-PLANE-ARCHIVE-PROVENANCE-INVALID", "BLOCKER",
            "PROVENANCE.json does not describe the exact cleared ZIP members",
            PROVENANCE_REL,
        ))
    elif (
        archive_provenance["status"] == "valid"
        and source_commit is not None
        and archive_provenance["commit"] != source_commit
    ):
        findings.append(_finding(
            "RUNTIME-PLANE-ARCHIVE-COMMIT-MISMATCH", "BLOCKER",
            "the cleared ZIP provenance commit differs from the explicit source commit",
            PROVENANCE_REL,
        ))
    if archive_inventory and not source_archive_equal:
        findings.append(_finding(
            "RUNTIME-PLANE-ARCHIVE-SOURCE-DIFFERENCE", "BLOCKER",
            "the cleared ZIP package members are not byte-identical to the exact source commit checkout",
        ))
    if embedded_provenance["status"] == "missing":
        findings.append(_finding(
            "RUNTIME-PLANE-EMBEDDED-PROVENANCE-MISSING",
            "WARNING" if externally_bound_without_local_provenance else "BLOCKER",
            (
                "the source-installed local plane omits archive-only provenance; "
                "the receipt remains externally bound to the validated cleared ZIP"
                if externally_bound_without_local_provenance
                else "the local plane has no embedded provenance from the cleared ZIP"
            ),
            PROVENANCE_REL,
        ))
    elif embedded_provenance["status"] == "invalid":
        findings.append(_finding(
            "RUNTIME-PLANE-EMBEDDED-PROVENANCE-INVALID", "BLOCKER",
            "the local embedded provenance is malformed or incomplete", PROVENANCE_REL,
        ))
    elif provenance_match is False:
        findings.append(_finding(
            "RUNTIME-PLANE-PROVENANCE-MISMATCH", "BLOCKER",
            "embedded archive commit differs from the explicit source baseline commit", PROVENANCE_REL,
        ))
    elif provenance_match is None:
        findings.append(_finding(
            "RUNTIME-PLANE-PROVENANCE-UNVERIFIED", "WARNING",
            "embedded provenance is present but the baseline source commit is unavailable",
            PROVENANCE_REL,
        ))
    if crlf_only:
        findings.append(_finding(
            "RUNTIME-PLANE-CRLF-ONLY",
            "WARNING" if crlf_mode == "allow_utf8_crlf_only" else "BLOCKER",
            f"{len(crlf_only)} UTF-8 file(s) differ only by CRLF/LF transformation; policy={crlf_mode}",
        ))
    blocking_differences = [entry for entry in semantic_differences if entry["blocking"]]
    if blocking_differences:
        findings.append(_finding(
            "RUNTIME-PLANE-SEMANTIC-DIFFERENCE", "BLOCKER",
            f"{len(blocking_differences)} file(s) differ semantically or by file kind",
        ))
    if missing_files:
        findings.append(_finding(
            "RUNTIME-PLANE-MISSING-FILE", "BLOCKER",
            f"{len(missing_files)} baseline file(s) are missing from the local plane",
        ))
    benign_extras = [
        entry for entry in foreign_extras
        if not entry["blocking"] and entry["path"] != PROVENANCE_REL
    ]
    if blocking_extras:
        findings.append(_finding(
            "RUNTIME-PLANE-FOREIGN-BLOCKING", "BLOCKER",
            f"{len(blocking_extras)} foreign file(s) can participate in imports or policy/instruction loading",
        ))
    if benign_extras:
        findings.append(_finding(
            "RUNTIME-PLANE-FOREIGN-BENIGN", "WARNING",
            f"{len(benign_extras)} nonparticipating foreign file(s) remain visible",
        ))
    for result in suite_results:
        if result["status"] not in {"passed", "not_run_preflight"}:
            findings.append(_finding(
                "RUNTIME-PLANE-SUITE-" + result["status"].upper(),
                "BLOCKER",
                f"required {result['kind']} suite {result['name']} is {result['status']}",
                result["script"],
            ))
    if not stable:
        findings.append(_finding(
            "RUNTIME-PLANE-MUTATED", "BLOCKER",
            "the local package digest changed while its self-check suites ran",
        ))

    provenance_missing = (
        source_commit is None
        or resolved_zip is None
        or not resolved_zip.is_file()
        or archive_provenance["status"] == "missing"
        or source_provenance["status"] == "missing"
    )
    has_blocker = any(finding["severity"] == "BLOCKER" for finding in findings)
    if provenance_missing:
        cache_state = "CACHE_PROVENANCE_MISSING"
    elif has_blocker:
        cache_state = "CACHE_PROVENANCE_CONTAMINATED"
        findings.append(_finding(
            "CACHE-PROVENANCE-CONTAMINATED", "BLOCKER",
            "cleared-ZIP/source/cache equality or a required stability/core-suite predicate failed",
        ))
    else:
        cache_state = "CODEX_CACHE_QUALIFIED"
    has_warning = any(finding["severity"] == "WARNING" for finding in findings)
    verdict = (
        "blocked" if cache_state != "CODEX_CACHE_QUALIFIED"
        else "qualified_with_caveats" if has_warning
        else "qualified"
    )
    canonical_archive_claim = (
        verdict == "qualified"
        and cache_state == "CODEX_CACHE_QUALIFIED"
        and archive_provenance_valid
        and source_archive_equal
        and embedded_provenance["status"] == "valid"
        and provenance_match is True
        and version_match is True
        and exact_version_match is True
        and not crlf_only
        and not semantic_differences
        and not missing_files
        and not foreign_extras
        and stable
    )

    receipt: dict[str, Any] = {
        "schema_version": "1.1.0",
        "receipt_type": "runtime_plane_probe",
        "plane_kind": plane_kind,
        "topology_receipt": {
            "sha256": topology_sha256,
            "source_commit": topology_value["source_commit"],
            "plane_kind": plane_kind,
        },
        "baseline_root": str(baseline_root),
        "local_root": str(local_root),
        "environment": {
            "pythondontwritebytecode": "1",
            "isolated_python": True,
            "python_environment_policy": "scrub-all-restore-three-v1",
            "ambient_pythonpath": "",
            "suite_pythonpath": os.pathsep.join(dependency_paths),
            "suite_pythonno_usersite": "1",
            "suite_pythonhome": None,
            "dependency_paths": list(dependency_paths),
        },
        "interpreter": {
            "executable": sys.executable,
            "implementation": platform.python_implementation(),
            "version": sys.version.replace("\n", " "),
            "version_info": list(sys.version_info[:3]),
            "platform": platform.platform(),
        },
        "tool_versions": _tool_versions(),
        "identity": {
            "source": {"manifest": source_manifest, "provenance": source_provenance},
            "embedded": {"manifest": local_manifest, "provenance": embedded_provenance},
            "version_match": version_match,
            "exact_version_match": exact_version_match,
            "provenance_match": provenance_match,
            "canonical_archive_claim": canonical_archive_claim,
        },
        "cleared_zip": cleared_zip,
        "normalization_policy": {
            "policy_id": "runtime-plane-normalization-v1",
            "crlf_mode": crlf_mode,
            "semantic_differences_block": True,
            "blocking_extras_block": True,
        },
        "cache_state": cache_state,
        "exact_files": exact_files,
        "crlf_only": crlf_only,
        "semantic_differences": semantic_differences,
        "missing_files": missing_files,
        "foreign_extras": foreign_extras,
        "package_digests": {
            "baseline": baseline_digest,
            "pre": pre_digest,
            "post": post_digest,
            "stable": stable,
        },
        "suites": suite_results,
        "findings": findings,
        "verdict": verdict,
    }
    _validate(receipt)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = out_path.with_name(out_path.name + ".tmp")
        temporary.write_bytes(_canonical(receipt))
        os.replace(temporary, out_path)
    return receipt


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local-root", type=Path, required=True)
    parser.add_argument("--baseline-root", type=Path, required=True)
    parser.add_argument("--cleared-zip", type=Path)
    parser.add_argument("--source-commit")
    parser.add_argument("--plane-kind", choices=("unpacked", "installed_cache"), required=True)
    parser.add_argument("--topology-receipt", type=Path, required=True)
    parser.add_argument(
        "--crlf-mode",
        choices=("forbid", "allow_utf8_crlf_only"),
        default="forbid",
    )
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument("--out", type=Path)
    destination.add_argument("--stdout", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        receipt = probe_plane(
            local_root=args.local_root,
            baseline_root=args.baseline_root,
            out_path=args.out,
            cleared_zip_path=args.cleared_zip,
            source_commit=args.source_commit,
            crlf_mode=args.crlf_mode,
            plane_kind=args.plane_kind,
            topology_receipt=args.topology_receipt,
        )
    except (ProbeRefusal, OSError, UnicodeError, json.JSONDecodeError) as exc:
        code = exc.code if isinstance(exc, ProbeRefusal) else "RUNTIME-PLANE-IO"
        message = exc.message if isinstance(exc, ProbeRefusal) else str(exc)
        print(f"[BLOCKER] {code}: {message}", file=sys.stderr)
        return 4
    if args.stdout:
        sys.stdout.buffer.write(_canonical(receipt))
    else:
        print(json.dumps({"verdict": receipt["verdict"], "receipt": str(args.out.resolve())}))
    return 0 if receipt["verdict"] != "blocked" else 2


if __name__ == "__main__":
    raise SystemExit(main())
