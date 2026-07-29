#!/usr/bin/env python3
"""Publish immutable, marker-last host qualification transactions.

This transaction records host evidence only.  It neither installs a plugin nor
changes package clearance.  Cache equality is necessary package evidence, not a
claim that Cowork loaded those bytes.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any
import uuid

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.exceptions import Unresolvable

import destination_capability as destinations


ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "references" / "schemas" / "host_qualification_transaction.schema.json"
COMMON_SCHEMA = ROOT / "references" / "schemas" / "common_scholarly_primitives.schema.json"
RUNTIME_SCHEMA = ROOT / "references" / "schemas" / "runtime_plane_receipt.schema.json"
COMMON_SCHEMA_ID = "https://co-author-harness.local/schemas/common_scholarly_primitives.schema.json"
COMMON_SCHEMA_SHA256 = "b5a397a4e90431c422a788414e40c1eed6ca5ba98191ed0aecaaa70aac3365e4"
TRANSACTION_NAME = "host-qualification.json"
PUBLICATION_NAME = "publication-manifest.json"
MARKER_NAME = "commit-marker.json"
PACKAGE_STATES = {"NOT_EVALUATED", "PACKAGE_CLEARED", "PACKAGE_NOT_CLEARED"}
EXPECTED_RUNTIME_SUITES = (
    ("governed_product_gate_self_check", "governed_product_gate_self_check", "scripts/run_product_gate_smoketest.py"),
    ("schema_runtime_check", "portable_core", "scripts/schema_runtime_check.py"),
    ("version_check", "portable_core", "scripts/version-check.py"),
    ("skill_check", "portable_core", "scripts/skill-check.py"),
)


class HostQualificationError(RuntimeError):
    """Typed refusal before an immutable host transaction can be committed."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _binding(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {"path": str(path.resolve()), "sha256": _sha(raw), "byte_length": len(raw)}


def _binding_for_bytes(path: Path, raw: bytes) -> dict[str, Any]:
    return {"path": str(path.resolve()), "sha256": _sha(raw), "byte_length": len(raw)}


def _read_json(path: Path, code: str, label: str) -> tuple[dict[str, Any], dict[str, Any]]:
    if not path.is_file():
        raise HostQualificationError(code, f"{label} is missing: {path}")
    raw = path.read_bytes()
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HostQualificationError(code, f"{label} is not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise HostQualificationError(code, f"{label} must be a JSON object")
    return value, {"path": str(path.resolve()), "sha256": _sha(raw), "byte_length": len(raw)}


def _same_zip(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    keys = {"sha256", "byte_length", "source_commit", "provenance_sha256"}
    return all(left.get(key) == right.get(key) for key in keys)


def _host_validator(
    *,
    schema_path: Path = SCHEMA,
    common_schema_path: Path = COMMON_SCHEMA,
) -> Draft202012Validator:
    """Resolve the mechanically shared schema through one exact local resource."""

    try:
        common_raw = common_schema_path.read_bytes()
        common = json.loads(common_raw)
        schema = json.loads(schema_path.read_bytes())
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise HostQualificationError(
            "HOST-PUBLICATION-INCOMPLETE",
            f"host qualification schema resource is unavailable or invalid: {exc}",
        ) from exc
    if not isinstance(common, dict) or common.get("$id") != COMMON_SCHEMA_ID:
        raise HostQualificationError(
            "HOST-PUBLICATION-INCOMPLETE",
            "common scholarly primitive schema has the wrong canonical $id",
        )
    if _sha(common_raw) != COMMON_SCHEMA_SHA256:
        raise HostQualificationError(
            "HOST-PUBLICATION-INCOMPLETE",
            "common scholarly primitive schema hash differs from the frozen consolidation resource",
        )
    try:
        registry = Registry().with_resource(
            COMMON_SCHEMA_ID, Resource.from_contents(common)
        )
        return Draft202012Validator(schema, registry=registry)
    except Exception as exc:
        raise HostQualificationError(
            "HOST-PUBLICATION-INCOMPLETE",
            f"common scholarly primitive schema cannot be registered: {exc}",
        ) from exc


def _validate(
    transaction: Mapping[str, Any],
    *,
    schema_path: Path = SCHEMA,
    common_schema_path: Path = COMMON_SCHEMA,
) -> None:
    validator = _host_validator(
        schema_path=schema_path, common_schema_path=common_schema_path
    )
    try:
        errors = sorted(
            validator.iter_errors(transaction),
            key=lambda error: list(error.path),
        )
    except Unresolvable as exc:
        raise HostQualificationError(
            "HOST-PUBLICATION-INCOMPLETE",
            f"host qualification schema reference is unresolved: {exc}",
        ) from exc
    if errors:
        raise HostQualificationError(
            "HOST-PUBLICATION-INCOMPLETE",
            "; ".join(f"{list(error.path)}: {error.message}" for error in errors),
        )


def _valid_runtime_receipt(receipt: Mapping[str, Any]) -> bool:
    schema = json.loads(RUNTIME_SCHEMA.read_text(encoding="utf-8"))
    if any(Draft202012Validator(schema).iter_errors(receipt)):
        return False
    environment = receipt.get("environment", {})
    dependencies = environment.get("dependency_paths", []) if isinstance(environment, Mapping) else None
    suites = receipt.get("suites", [])
    observed_suites = [
        (row.get("name"), row.get("kind"), row.get("script"))
        for row in suites
        if isinstance(row, Mapping)
    ] if isinstance(suites, list) else []
    return (
        isinstance(environment, Mapping)
        and isinstance(dependencies, list)
        and all(isinstance(path, str) for path in dependencies)
        and environment.get("suite_pythonpath") == os.pathsep.join(dependencies)
        and observed_suites == list(EXPECTED_RUNTIME_SUITES)
        and all(
            isinstance(row, Mapping)
            and row.get("status") == "passed"
            and row.get("returncode") == 0
            for row in suites
        )
    )


def _failure(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def _claims() -> dict[str, bool]:
    return {
        "cache_equality_implies_host_load": False,
        "host_state_changes_package_clearance": False,
        "fresh_task_required": True,
        "marker_last": True,
    }


def _authorize_output(authority_root: Path, output_dir: Path) -> tuple[Path, Path]:
    authority_root = authority_root.resolve(strict=True)
    output_dir = output_dir.resolve()
    evidence_root = (authority_root / "releases" / "verification").resolve()
    try:
        output_dir.relative_to(evidence_root)
    except ValueError as exc:
        raise HostQualificationError(
            "HOST-PUBLICATION-INCOMPLETE",
            "host qualification output must be inside the explicit authority root's releases/verification lane",
        ) from exc
    for name in (TRANSACTION_NAME, PUBLICATION_NAME, MARKER_NAME):
        try:
            destinations.assert_writable(
                output_dir / name, purpose="host qualification transaction"
            )
        except destinations.DestinationRefused as exc:
            raise HostQualificationError(exc.code, str(exc)) from exc
    return authority_root, output_dir


def _assert_current(binding: Mapping[str, Any], code: str, label: str) -> None:
    path = Path(str(binding["path"]))
    if not path.is_file():
        raise HostQualificationError(code, f"{label} disappeared before publication")
    raw = path.read_bytes()
    if len(raw) != binding["byte_length"] or _sha(raw) != binding["sha256"]:
        raise HostQualificationError(code, f"{label} changed before publication")


def _write_exclusive(path: Path, raw: bytes) -> bool:
    """Publish complete bytes atomically without replacing an existing path."""

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    staged = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.staged")
    try:
        descriptor = os.open(staged, flags, 0o600)
    except OSError as exc:
        raise HostQualificationError(
            "HOST-PUBLICATION-INCOMPLETE",
            f"cannot create exclusive staged publication for {path.name}: {exc}",
        ) from exc
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(staged, path, follow_symlinks=False)
            return True
        except FileExistsError:
            return False
        except OSError as exc:
            raise HostQualificationError(
                "HOST-PUBLICATION-INCOMPLETE",
                f"cannot atomically publish {path.name} without replacement: {exc}",
            ) from exc
    finally:
        try:
            staged.unlink()
        except FileNotFoundError:
            pass


def _publish_exact(path: Path, raw: bytes, label: str) -> bool:
    """Publish exclusively or accept only an already-identical file."""

    created = _write_exclusive(path, raw)
    if created:
        return True
    if path.is_symlink():
        raise HostQualificationError(
            "HOST-PUBLICATION-INCOMPLETE", f"{label} is a foreign symlink"
        )
    try:
        existing = path.read_bytes()
    except OSError as exc:
        raise HostQualificationError(
            "HOST-PUBLICATION-INCOMPLETE",
            f"{label} appeared concurrently but cannot be verified: {exc}",
        ) from exc
    if existing != raw:
        raise HostQualificationError(
            "HOST-PUBLICATION-INCOMPLETE",
            f"{label} appeared concurrently with foreign bytes",
        )
    return False


def _assert_committed_chain(
    *,
    transaction_path: Path,
    transaction_raw: bytes,
    publication_path: Path,
    publication_raw: bytes,
    marker_path: Path,
    marker_raw: bytes,
) -> None:
    """Read back the exact marker-last chain and all public hash bindings."""

    expected = (
        (transaction_path, transaction_raw, "host transaction"),
        (publication_path, publication_raw, "publication manifest"),
        (marker_path, marker_raw, "commit marker"),
    )
    observed: dict[Path, bytes] = {}
    for path, raw, label in expected:
        if path.is_symlink() or not path.is_file():
            raise HostQualificationError(
                "HOST-PUBLICATION-INCOMPLETE", f"{label} is unavailable at final read-back"
            )
        current = path.read_bytes()
        if current != raw:
            raise HostQualificationError(
                "HOST-PUBLICATION-INCOMPLETE", f"{label} differs at final read-back"
            )
        observed[path] = current
    try:
        transaction = json.loads(observed[transaction_path])
        marker = json.loads(observed[marker_path])
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HostQualificationError(
            "HOST-PUBLICATION-INCOMPLETE", f"committed chain is not valid UTF-8 JSON: {exc}"
        ) from exc
    if not isinstance(transaction, dict) or not isinstance(marker, dict):
        raise HostQualificationError(
            "HOST-PUBLICATION-INCOMPLETE",
            "committed transaction and marker must be JSON objects",
        )
    _validate(transaction)
    publication_binding = _binding_for_bytes(
        publication_path, observed[publication_path]
    )
    marker_binding = _binding_for_bytes(marker_path, observed[marker_path])
    if (
        transaction.get("publication_manifest") != publication_binding
        or transaction.get("commit_marker") != marker_binding
        or marker.get("transaction_id") != transaction.get("transaction_id")
        or marker.get("state") != "HOST_QUALIFIED"
        or marker.get("publication_manifest_sha256")
        != publication_binding["sha256"]
    ):
        raise HostQualificationError(
            "HOST-PUBLICATION-INCOMPLETE",
            "final transaction, publication manifest, and marker hashes do not cross-bind",
        )
    for key in (
        "registry_row",
        "installed_manifest",
        "cache_comparison",
        "cleared_zip",
        "core_probe",
    ):
        binding = transaction.get(key)
        if not isinstance(binding, dict):
            raise HostQualificationError(
                "HOST-PUBLICATION-INCOMPLETE",
                f"committed HOST_QUALIFIED transaction lacks its {key} input binding",
            )
        _assert_current(
            binding,
            "HOST-PUBLICATION-INCOMPLETE",
            f"committed qualification input {key}",
        )


def _host_matches_probe(host: Mapping[str, Any], probe: Mapping[str, Any]) -> bool:
    observed = probe.get("host")
    return (
        isinstance(observed, dict)
        and observed.get("product") == host.get("product")
        and observed.get("version") == host.get("version")
        and observed.get("task_id") == host.get("task_id")
        and observed.get("fresh_task") is True
        and probe.get("status") == "passed"
    )


def _classify(
    *,
    host: Mapping[str, Any],
    package_clearance_state: str,
    registry_row_path: Path | None,
    installed_manifest_path: Path | None,
    cache_comparison_path: Path | None,
    cleared_zip_path: Path | None,
    core_probe_path: Path | None,
) -> tuple[
    str,
    dict[str, Any] | None,
    dict[str, Any] | None,
    dict[str, Any] | None,
    dict[str, Any] | None,
    dict[str, Any] | None,
    dict[str, str] | None,
    list[dict[str, Any]],
]:
    """Return state, bindings, typed failure, and every TOCTOU input binding."""

    if package_clearance_state not in PACKAGE_STATES:
        raise HostQualificationError(
            "HOST-CLEARED-ZIP-UNBOUND", f"unknown package clearance state: {package_clearance_state}"
        )
    input_bindings: list[dict[str, Any]] = []

    if core_probe_path is None:
        return (
            "HOST_QUALIFICATION_PENDING", None, None, None, None, None, None, input_bindings
        )
    try:
        core_probe, core_binding = _read_json(
            core_probe_path, "HOST-CORE-PROBE-FAILED", "host core probe"
        )
    except HostQualificationError as exc:
        return (
            "HOST_QUALIFICATION_FAILED", None, None, None, None, None,
            _failure(exc.code, exc.message), input_bindings,
        )
    input_bindings.append(core_binding)
    if core_probe.get("status") != "passed":
        return (
            "HOST_QUALIFICATION_FAILED", None, None, None, None, core_binding,
            _failure("HOST-CORE-PROBE-FAILED", "the fresh-task host functional probe did not pass"),
            input_bindings,
        )

    if (
        cache_comparison_path is None
        or cleared_zip_path is None
        or package_clearance_state != "PACKAGE_CLEARED"
    ):
        return (
            "HOST_FUNCTIONAL_UNBOUND", None, None, None, None, core_binding, None, input_bindings
        )

    try:
        cache, cache_binding = _read_json(
            cache_comparison_path,
            "HOST-CACHE-COMPARISON-MISSING",
            "cache comparison receipt",
        )
    except HostQualificationError as exc:
        return (
            "HOST_QUALIFICATION_FAILED", None, None, None, None, core_binding,
            _failure(exc.code, exc.message), input_bindings,
        )
    input_bindings.append(cache_binding)
    zip_claim = cache.get("cleared_zip")
    if (
        not _valid_runtime_receipt(cache)
        or cache.get("cache_state") != "CODEX_CACHE_QUALIFIED"
        or cache.get("verdict") not in {"qualified", "qualified_with_caveats"}
        or not isinstance(zip_claim, dict)
        or cache.get("package_digests", {}).get("stable") is not True
        or len(cache.get("suites", [])) != 4
        or any(row.get("status") != "passed" for row in cache.get("suites", []))
        or any(row.get("severity") == "BLOCKER" for row in cache.get("findings", []))
    ):
        return (
            "HOST_QUALIFICATION_FAILED", None, None, cache_binding, None, core_binding,
            _failure("HOST-CACHE-COMPARISON-MISSING", "cache receipt is not a qualified cleared-ZIP comparison"),
            input_bindings,
        )

    if not cleared_zip_path.is_file():
        return (
            "HOST_QUALIFICATION_FAILED", None, None, cache_binding, None, core_binding,
            _failure("HOST-CLEARED-ZIP-UNBOUND", "the cleared ZIP is missing"), input_bindings,
        )
    zip_raw = cleared_zip_path.read_bytes()
    cleared_binding = {
        "path": str(cleared_zip_path.resolve()),
        "sha256": _sha(zip_raw),
        "byte_length": len(zip_raw),
        "source_commit": zip_claim.get("source_commit"),
        "provenance_sha256": zip_claim.get("provenance_sha256"),
    }
    input_bindings.append(_binding(cleared_zip_path))
    try:
        same_zip_path = Path(str(zip_claim.get("path"))).resolve() == cleared_zip_path.resolve()
    except (OSError, TypeError, ValueError):
        same_zip_path = False
    if not same_zip_path or not _same_zip(cleared_binding, zip_claim):
        return (
            "HOST_QUALIFICATION_FAILED", None, None, cache_binding, cleared_binding, core_binding,
            _failure("HOST-CLEARED-ZIP-UNBOUND", "cache comparison binds another cleared ZIP"),
            input_bindings,
        )

    probe_zip_sha = core_probe.get("cleared_zip_sha256")
    if not _host_matches_probe(host, core_probe):
        return (
            "HOST_QUALIFICATION_FAILED", None, None, cache_binding, cleared_binding, core_binding,
            _failure("HOST-CORE-PROBE-FAILED", "core probe does not bind the declared fresh host task"),
            input_bindings,
        )
    if probe_zip_sha != cleared_binding["sha256"]:
        return (
            "HOST_QUALIFICATION_FAILED", None, None, cache_binding, cleared_binding, core_binding,
            _failure("HOST-CLEARED-ZIP-UNBOUND", "functional probe does not bind the cleared ZIP"),
            input_bindings,
        )

    if registry_row_path is None or installed_manifest_path is None or not host.get("fresh_task") or not host.get("task_id"):
        return (
            "HOST_QUALIFICATION_PENDING", None, None, cache_binding, cleared_binding, core_binding,
            None, input_bindings,
        )
    try:
        registry, registry_binding = _read_json(
            registry_row_path, "HOST-REGISTRY-MISSING", "host registry row"
        )
    except HostQualificationError as exc:
        return (
            "HOST_QUALIFICATION_FAILED", None, None, cache_binding, cleared_binding, core_binding,
            _failure(exc.code, exc.message), input_bindings,
        )
    input_bindings.append(registry_binding)
    try:
        installed, installed_binding = _read_json(
            installed_manifest_path,
            "HOST-INSTALLED-MANIFEST-MISSING",
            "installed plugin manifest",
        )
    except HostQualificationError as exc:
        return (
            "HOST_QUALIFICATION_FAILED", registry_binding, None, cache_binding,
            cleared_binding, core_binding, _failure(exc.code, exc.message), input_bindings,
        )
    input_bindings.append(installed_binding)

    cache_manifest = (
        cache.get("identity", {}).get("embedded", {}).get("manifest", {})
        if isinstance(cache.get("identity"), dict)
        else {}
    )
    if (
        registry.get("installed_manifest_sha256") != installed_binding["sha256"]
        or registry.get("cleared_zip_sha256") != cleared_binding["sha256"]
    ):
        return (
            "HOST_QUALIFICATION_FAILED", registry_binding, installed_binding, cache_binding,
            cleared_binding, core_binding,
            _failure("HOST-REGISTRY-MISSING", "registry row does not bind the installed manifest and cleared ZIP"),
            input_bindings,
        )
    if (
        cache_manifest.get("sha256") != installed_binding["sha256"]
        or cache_manifest.get("name") != installed.get("name")
        or cache_manifest.get("version") != installed.get("version")
    ):
        return (
            "HOST_QUALIFICATION_FAILED", registry_binding, installed_binding, cache_binding,
            cleared_binding, core_binding,
            _failure("HOST-INSTALLED-MANIFEST-MISSING", "installed manifest is not the manifest qualified by the cache receipt"),
            input_bindings,
        )
    return (
        "HOST_QUALIFIED", registry_binding, installed_binding, cache_binding,
        cleared_binding, core_binding, None, input_bindings,
    )


def publish_host_qualification(
    *,
    authority_root: Path,
    output_dir: Path,
    host: Mapping[str, Any],
    package_clearance_state: str,
    registry_row_path: Path | None = None,
    installed_manifest_path: Path | None = None,
    cache_comparison_path: Path | None = None,
    cleared_zip_path: Path | None = None,
    core_probe_path: Path | None = None,
    created_at: str | None = None,
    before_commit: Callable[[], None] | None = None,
    publication_hook: Callable[[str, Path], None] | None = None,
) -> dict[str, Any]:
    """Classify and publish one immutable host observation transaction."""

    authority_root, output_dir = _authorize_output(authority_root, output_dir)
    host_value = dict(host)
    created_at = created_at or str(host_value.get("observed_at") or "")
    (
        state,
        registry_binding,
        installed_binding,
        cache_binding,
        cleared_binding,
        core_binding,
        failure,
        input_bindings,
    ) = _classify(
        host=host_value,
        package_clearance_state=package_clearance_state,
        registry_row_path=registry_row_path,
        installed_manifest_path=installed_manifest_path,
        cache_comparison_path=cache_comparison_path,
        cleared_zip_path=cleared_zip_path,
        core_probe_path=core_probe_path,
    )
    identity_material = {
        "host": host_value,
        "package_clearance_state": package_clearance_state,
        "registry_row": registry_binding,
        "installed_manifest": installed_binding,
        "cache_comparison": cache_binding,
        "cleared_zip": cleared_binding,
        "core_probe": core_binding,
        "created_at": created_at,
    }
    transaction_id = "host-qualification:" + _sha(_canonical(identity_material))[:32]
    transaction_path = output_dir / TRANSACTION_NAME
    publication_path = output_dir / PUBLICATION_NAME
    marker_path = output_dir / MARKER_NAME

    publication_binding: dict[str, Any] | None = None
    marker_binding: dict[str, Any] | None = None
    publication_raw: bytes | None = None
    marker_raw: bytes | None = None
    if state == "HOST_QUALIFIED":
        publication = {
            "schema_version": "host-qualification-publication/1",
            "transaction_id": transaction_id,
            "state": state,
            "package_clearance_state": package_clearance_state,
            "inputs": {
                "registry_row": registry_binding,
                "installed_manifest": installed_binding,
                "cache_comparison": cache_binding,
                "cleared_zip": cleared_binding,
                "core_probe": core_binding,
            },
        }
        publication_raw = _canonical(publication)
        publication_binding = _binding_for_bytes(publication_path, publication_raw)
        marker_raw = _canonical({
            "schema_version": "host-qualification-commit/1",
            "transaction_id": transaction_id,
            "state": state,
            "publication_manifest_sha256": publication_binding["sha256"],
        })
        marker_binding = _binding_for_bytes(marker_path, marker_raw)

    transaction = {
        "schema_version": "1.0.0",
        "transaction_id": transaction_id,
        "state": state,
        "host": host_value,
        "registry_row": registry_binding,
        "installed_manifest": installed_binding,
        "cache_comparison": cache_binding,
        "cleared_zip": cleared_binding,
        "core_probe": core_binding,
        "package_clearance_state": package_clearance_state,
        "publication_manifest": publication_binding,
        "commit_marker": marker_binding,
        "failure": failure,
        "claims": _claims(),
        "created_at": created_at,
    }
    _validate(transaction)
    transaction_raw = _canonical(transaction)

    output_dir.mkdir(parents=True, exist_ok=True)
    if marker_path.exists():
        if state != "HOST_QUALIFIED" or publication_raw is None or marker_raw is None:
            raise HostQualificationError(
                "HOST-PUBLICATION-INCOMPLETE",
                "a committed host qualification already occupies this output lane",
            )
        _assert_committed_chain(
            transaction_path=transaction_path,
            transaction_raw=transaction_raw,
            publication_path=publication_path,
            publication_raw=publication_raw,
            marker_path=marker_path,
            marker_raw=marker_raw,
        )
        return transaction

    if state != "HOST_QUALIFIED":
        if publication_path.exists():
            raise HostQualificationError(
                "HOST-PUBLICATION-INCOMPLETE", "nonqualified host state cannot carry a publication manifest"
            )
        _publish_exact(transaction_path, transaction_raw, "host transaction")
        if transaction_path.read_bytes() != transaction_raw:
            raise HostQualificationError(
                "HOST-PUBLICATION-INCOMPLETE",
                "nonqualified host transaction differs at final read-back",
            )
        return transaction

    assert publication_raw is not None and marker_raw is not None
    # Revalidate every publication file after preparation.  A file that appears
    # later is handled again by _publish_exact's O_EXCL/read-back predicate.
    for path, raw in (
        (transaction_path, transaction_raw),
        (publication_path, publication_raw),
        (marker_path, marker_raw),
    ):
        if path.exists() and path.read_bytes() != raw:
            raise HostQualificationError(
                "HOST-PUBLICATION-INCOMPLETE", f"partial publication contains foreign bytes: {path.name}"
            )
    if before_commit is not None:
        before_commit()
    for binding in input_bindings:
        _assert_current(binding, "HOST-PUBLICATION-INCOMPLETE", "qualification input")
    _publish_exact(transaction_path, transaction_raw, "host transaction")
    if publication_hook is not None:
        publication_hook("transaction", transaction_path)
    _publish_exact(publication_path, publication_raw, "publication manifest")
    if publication_hook is not None:
        publication_hook("publication_manifest", publication_path)
    # This is the final authority-boundary check: hooks and concurrent host
    # activity may have changed an input after the earlier preparation check.
    # No marker may become visible until every captured byte is current again.
    for binding in input_bindings:
        _assert_current(
            binding,
            "HOST-PUBLICATION-INCOMPLETE",
            "qualification input immediately before commit marker",
        )
    _publish_exact(marker_path, marker_raw, "commit marker")
    if publication_hook is not None:
        publication_hook("commit_marker", marker_path)
    _assert_committed_chain(
        transaction_path=transaction_path,
        transaction_raw=transaction_raw,
        publication_path=publication_path,
        publication_raw=publication_raw,
        marker_path=marker_path,
        marker_raw=marker_raw,
    )
    return transaction


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("publish", "recover"))
    parser.add_argument("--authority-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--host-json", type=Path, required=True)
    parser.add_argument("--package-clearance-state", choices=sorted(PACKAGE_STATES), required=True)
    parser.add_argument("--registry-row", type=Path)
    parser.add_argument("--installed-manifest", type=Path)
    parser.add_argument("--cache-comparison", type=Path)
    parser.add_argument("--cleared-zip", type=Path)
    parser.add_argument("--core-probe", type=Path)
    parser.add_argument("--created-at")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        host = json.loads(args.host_json.read_text(encoding="utf-8"))
        if not isinstance(host, dict):
            raise HostQualificationError("HOST-CORE-PROBE-FAILED", "host JSON must be an object")
        transaction = publish_host_qualification(
            authority_root=args.authority_root,
            output_dir=args.output_dir,
            host=host,
            package_clearance_state=args.package_clearance_state,
            registry_row_path=args.registry_row,
            installed_manifest_path=args.installed_manifest,
            cache_comparison_path=args.cache_comparison,
            cleared_zip_path=args.cleared_zip,
            core_probe_path=args.core_probe,
            created_at=args.created_at,
        )
    except (HostQualificationError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        code = exc.code if isinstance(exc, HostQualificationError) else "HOST-PUBLICATION-INCOMPLETE"
        message = exc.message if isinstance(exc, HostQualificationError) else str(exc)
        print(f"[BLOCKER] {code}: {message}", file=sys.stderr)
        return 4
    print(json.dumps({"state": transaction["state"], "transaction_id": transaction["transaction_id"]}))
    return 0 if transaction["state"] != "HOST_QUALIFICATION_FAILED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
