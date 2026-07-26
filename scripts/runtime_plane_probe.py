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
import json
import os
import platform
import re
import site
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator
import destination_capability as destinations


ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "references" / "schemas" / "runtime_plane_receipt.schema.json"
MANIFEST_REL = ".claude-plugin/plugin.json"
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
    return baseline_text.replace("\r\n", "\n") == local_text.replace("\r\n", "\n")


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
    child_env = dict(os.environ)
    child_env["PYTHONDONTWRITEBYTECODE"] = "1"
    child_env["PYTHONPATH"] = ""
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


def _finding(code: str, severity: str, message: str, path: str | None = None) -> dict[str, str]:
    value = {"code": code, "severity": severity, "message": message}
    if path:
        value["path"] = path
    return value


def _validate(receipt: Mapping[str, Any]) -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(receipt), key=lambda error: list(error.path))
    if errors:
        raise ProbeRefusal(
            "RUNTIME-PLANE-SCHEMA",
            "; ".join(f"{list(error.path)}: {error.message}" for error in errors),
        )


def probe_plane(
    *,
    local_root: Path,
    baseline_root: Path,
    out_path: Path | None,
    suites: Iterable[Mapping[str, str]] = DEFAULT_SUITES,
) -> dict[str, Any]:
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        raise ProbeRefusal(
            "RUNTIME-PLANE-ENV",
            "PYTHONDONTWRITEBYTECODE=1 is required for a stable runtime-plane probe",
        )
    local_root = local_root.resolve(strict=True)
    baseline_root = baseline_root.resolve(strict=True)
    if not local_root.is_dir() or not baseline_root.is_dir():
        raise ProbeRefusal("RUNTIME-PLANE-ROOT", "local and baseline roots must be directories")
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

    source_commit = _source_commit(baseline_root)
    baseline_members = _baseline_members(baseline_root, source_commit)
    baseline_inventory = _walk_inventory(baseline_root, baseline_members, baseline_excluded)
    local_pre = _walk_inventory(local_root, excluded=local_excluded)

    exact_files: list[dict[str, Any]] = []
    crlf_only: list[dict[str, Any]] = []
    semantic_differences: list[dict[str, Any]] = []
    missing_files: list[dict[str, Any]] = []
    for rel, baseline in baseline_inventory.items():
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
    for rel in sorted(set(local_pre) - set(baseline_inventory)):
        local = local_pre[rel]
        blocking, reason = _foreign_reason(rel, local["kind"])
        foreign_extras.append({**_public_file(local), "blocking": blocking, "reason": reason})

    source_manifest = _manifest(baseline_root)
    local_manifest = _manifest(local_root)
    source_provenance = _source_provenance(baseline_root, source_commit)
    embedded_provenance = _embedded_provenance(
        local_root, local_pre, len(baseline_inventory)
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
    allowed_host_suffix = _allowed_host_suffix(
        baseline_root, local_root, source_manifest, local_manifest
    )
    for difference in semantic_differences:
        if difference["path"] == MANIFEST_REL and allowed_host_suffix:
            difference.update(blocking=False, reason="host_version_suffix_only")
        else:
            difference.update(blocking=True, reason="semantic_or_file_kind_difference")
    provenance_match: bool | None = None
    if source_provenance["status"] == "valid" and embedded_provenance["status"] == "valid":
        provenance_match = source_provenance["commit"] == embedded_provenance["commit"]

    suites = tuple(dict(suite) for suite in suites)
    if not suites or any(
        suite.get("kind") not in {"governed_product_gate_self_check", "portable_core"}
        or not suite.get("name") or not suite.get("script")
        for suite in suites
    ):
        raise ProbeRefusal("RUNTIME-PLANE-SUITES", "suite definitions are empty or invalid")
    dependency_paths = _dependency_paths()
    suite_results = _run_suites(local_root, suites, dependency_paths)
    local_post = _walk_inventory(local_root, excluded=local_excluded)

    baseline_digest = _digest(baseline_inventory)
    governed_members = set(baseline_inventory)
    if PROVENANCE_REL in local_pre or PROVENANCE_REL in local_post:
        governed_members.add(PROVENANCE_REL)
    pre_digest = _digest({rel: local_pre[rel] for rel in governed_members if rel in local_pre})
    post_digest = _digest({rel: local_post[rel] for rel in governed_members if rel in local_post})
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
    elif exact_version_match is False and allowed_host_suffix:
        findings.append(_finding(
            "RUNTIME-PLANE-VERSION-SUFFIX", "WARNING",
            "local manifest preserves the source base version and carries a separately reported host suffix",
            MANIFEST_REL,
        ))
    if source_provenance["status"] == "missing":
        findings.append(_finding(
            "RUNTIME-PLANE-SOURCE-PROVENANCE-MISSING", "WARNING",
            "the baseline has no resolvable root Git commit; archive provenance cannot be verified",
        ))
    if embedded_provenance["status"] == "missing":
        findings.append(_finding(
            "RUNTIME-PLANE-EMBEDDED-PROVENANCE-MISSING", "WARNING",
            "the local plane has no embedded provenance and is not a canonical archive extraction",
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
            "RUNTIME-PLANE-CRLF-ONLY", "WARNING",
            f"{len(crlf_only)} file(s) differ only by CRLF/LF transformation",
        ))
    blocking_differences = [entry for entry in semantic_differences if entry["blocking"]]
    nonblocking_differences = [entry for entry in semantic_differences if not entry["blocking"]]
    if blocking_differences:
        findings.append(_finding(
            "RUNTIME-PLANE-SEMANTIC-DIFFERENCE", "BLOCKER",
            f"{len(blocking_differences)} file(s) differ semantically or by file kind",
        ))
    if nonblocking_differences and not allowed_host_suffix:
        findings.append(_finding(
            "RUNTIME-PLANE-SEMANTIC-DIFFERENCE-NONBLOCKING", "WARNING",
            f"{len(nonblocking_differences)} classified semantic difference(s) are explicitly nonblocking",
        ))
    if missing_files:
        findings.append(_finding(
            "RUNTIME-PLANE-MISSING-FILE", "BLOCKER",
            f"{len(missing_files)} baseline file(s) are missing from the local plane",
        ))
    blocking_extras = [entry for entry in foreign_extras if entry["blocking"]]
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
        if result["status"] != "passed":
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

    has_blocker = any(finding["severity"] == "BLOCKER" for finding in findings)
    has_warning = any(finding["severity"] == "WARNING" for finding in findings)
    verdict = "blocked" if has_blocker else "qualified_with_caveats" if has_warning else "qualified"
    canonical_archive_claim = (
        verdict == "qualified"
        and embedded_provenance["status"] == "valid"
        and provenance_match is True
        and version_match is True
        and exact_version_match is True
        and not crlf_only
        and not semantic_differences
        and not missing_files
        and all(entry["path"] == PROVENANCE_REL for entry in foreign_extras)
        and stable
    )

    receipt: dict[str, Any] = {
        "schema_version": "1.0.0",
        "receipt_type": "runtime_plane_probe",
        "baseline_root": str(baseline_root),
        "local_root": str(local_root),
        "environment": {
            "pythondontwritebytecode": "1",
            "isolated_python": True,
            "pythonpath": "",
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
