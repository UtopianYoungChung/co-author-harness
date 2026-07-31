#!/usr/bin/env python3
"""Focused V40-02 host-state, linkage, immutability, and recovery tests."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
from copy import deepcopy

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = ROOT / "scripts" / "host_qualification_transaction.py"
SCHEMA_PATH = ROOT / "references" / "schemas" / "host_qualification_transaction.schema.json"
COMMON_SCHEMA_PATH = ROOT / "references" / "schemas" / "common_scholarly_primitives.schema.json"
NOW = "2026-07-27T12:00:00Z"
HOST = {
    "product": "Claude Cowork",
    "version": "fixture-host-1",
    "task_id": "fresh-task-001",
    "fresh_task": True,
    "observed_at": NOW,
}
HOST_VALIDATOR = None


def load_module():
    spec = importlib.util.spec_from_file_location("host_qualification_transaction", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write(path: Path, value: object | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value if isinstance(value, bytes) else canonical(value))


def validate(value: dict) -> None:
    assert HOST_VALIDATOR is not None
    errors = sorted(
        HOST_VALIDATOR.iter_errors(value), key=lambda error: list(error.path)
    )
    assert not errors, "; ".join(error.message for error in errors)


def evidence(base: Path, name: str, *, zip_bytes: bytes = b"cleared-zip-A\n") -> dict[str, Path]:
    root = base / name / "authority"
    cleared_zip = base / name / "cleared.zip"
    write(cleared_zip, zip_bytes)
    zip_sha = sha(zip_bytes)
    manifest = root / "installed-manifest.json"
    manifest_value = {"name": "fixture-plugin", "version": "0.40.0"}
    write(manifest, manifest_value)
    manifest_sha = sha(manifest.read_bytes())
    cache = root / "cache-receipt.json"
    manifest_identity = {
        "path": ".claude-plugin/plugin.json",
        "status": "valid",
        "name": manifest_value["name"],
        "version": manifest_value["version"],
        "base_version": manifest_value["version"],
        "host_suffix": None,
        "sha256": manifest_sha,
    }
    zip_claim = {
        "path": str(cleared_zip.resolve()),
        "sha256": zip_sha,
        "byte_length": len(zip_bytes),
        "source_commit": "a" * 40,
        "provenance_sha256": "b" * 64,
    }
    digest = {
        "algorithm": "sha256(path-NUL-kind-NUL-content-sha256-LF)",
        "sha256": "c" * 64,
        "file_count": 1,
    }
    suites = [
        {
            "name": name,
            "kind": kind,
            "script": script,
            "argv": ["python", script],
            "cwd": str(root),
            "returncode": 0,
            "status": "passed",
            "stdout_sha256": sha(b""),
            "stderr_sha256": sha(b""),
        }
        for name, kind, script in (
            (
                "governed_product_gate_self_check",
                "governed_product_gate_self_check",
                "scripts/run_product_gate_smoketest.py",
            ),
            ("schema_runtime_check", "portable_core", "scripts/schema_runtime_check.py"),
            ("version_check", "portable_core", "scripts/version-check.py"),
            ("skill_check", "portable_core", "scripts/skill-check.py"),
        )
    ]
    write(cache, {
        "schema_version": "1.1.0",
        "receipt_type": "runtime_plane_probe",
        "baseline_root": str(root),
        "local_root": str(root),
        "environment": {
            "pythondontwritebytecode": "1",
            "isolated_python": True,
            "python_environment_policy": "scrub-all-restore-three-v1",
            "ambient_pythonpath": "",
            "suite_pythonpath": "",
            "suite_pythonno_usersite": "1",
            "suite_pythonhome": None,
            "dependency_paths": [],
        },
        "interpreter": {
            "executable": "python",
            "implementation": "CPython",
            "version": "3.fixture",
            "version_info": [3, 14, 0],
            "platform": "fixture",
        },
        "tool_versions": {
            "python": "3.fixture",
            "jsonschema": "fixture",
            "referencing": "fixture",
            "pyyaml": "fixture",
            "git": "fixture",
        },
        "cache_state": "CODEX_CACHE_QUALIFIED",
        "verdict": "qualified",
        "cleared_zip": zip_claim,
        "normalization_policy": {
            "policy_id": "runtime-plane-normalization-v1",
            "crlf_mode": "forbid",
            "semantic_differences_block": True,
            "blocking_extras_block": True,
        },
        "identity": {
            "source": {
                "manifest": manifest_identity,
                "provenance": {
                    "kind": "source_git",
                    "path": str(root / ".git"),
                    "status": "valid",
                    "schema": "git-commit",
                    "commit": "a" * 40,
                    "sha256": None,
                },
            },
            "embedded": {
                "manifest": manifest_identity,
                "provenance": {
                    "kind": "embedded_archive",
                    "path": "PROVENANCE.json",
                    "status": "valid",
                    "schema": "coauthor-build-provenance/v1",
                    "commit": "a" * 40,
                    "sha256": "b" * 64,
                },
            },
            "version_match": True,
            "exact_version_match": True,
            "provenance_match": True,
            "canonical_archive_claim": True,
        },
        "exact_files": [],
        "crlf_only": [],
        "semantic_differences": [],
        "missing_files": [],
        "foreign_extras": [],
        "package_digests": {
            "baseline": digest,
            "pre": digest,
            "post": digest,
            "stable": True,
        },
        "suites": suites,
        "findings": [],
    })
    registry = root / "registry-row.json"
    write(registry, {
        "plugin_name": "fixture-plugin",
        "version": "0.40.0",
        "installed_manifest_sha256": manifest_sha,
        "cleared_zip_sha256": zip_sha,
    })
    core = root / "core-probe.json"
    write(core, {
        "status": "passed",
        "host": {
            "product": HOST["product"],
            "version": HOST["version"],
            "task_id": HOST["task_id"],
            "fresh_task": True,
        },
        "cleared_zip_sha256": zip_sha,
    })
    return {
        "authority": root,
        "zip": cleared_zip,
        "manifest": manifest,
        "cache": cache,
        "registry": registry,
        "core": core,
    }


def publish(module, paths: dict[str, Path], out: Path, **overrides) -> dict:
    arguments = {
        "authority_root": paths["authority"],
        "output_dir": out,
        "host": HOST,
        "package_clearance_state": "PACKAGE_CLEARED",
        "registry_row_path": paths["registry"],
        "installed_manifest_path": paths["manifest"],
        "cache_comparison_path": paths["cache"],
        "cleared_zip_path": paths["zip"],
        "core_probe_path": paths["core"],
        "created_at": NOW,
    }
    arguments.update(overrides)
    return module.publish_host_qualification(**arguments)


def expect_error(module, code: str, callback) -> None:
    try:
        callback()
    except module.HostQualificationError as exc:
        assert exc.code == code, exc
    else:
        raise AssertionError(f"expected {code}")


def pre_refactor_schema() -> dict:
    """Reconstruct the mechanically equivalent host schema before common refs."""

    current = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    common_prefix = (
        "https://co-author-harness.local/schemas/"
        "common_scholarly_primitives.schema.json#/$defs/"
    )

    def rewrite(value):
        if isinstance(value, list):
            return [rewrite(item) for item in value]
        if not isinstance(value, dict):
            return value
        reference = value.get("$ref")
        if reference == common_prefix + "fileBinding":
            return {"$ref": "#/$defs/binding"}
        if reference == common_prefix + "sha256":
            return {"$ref": "#/$defs/sha256"}
        if reference == common_prefix + "timestamp":
            return {"type": "string", "format": "date-time"}
        return {key: rewrite(item) for key, item in value.items()}

    old = rewrite(current)
    old["$defs"]["sha256"] = {
        "type": "string",
        "pattern": "^[0-9a-f]{64}$",
    }
    old["$defs"]["binding"] = {
        "type": "object",
        "additionalProperties": False,
        "required": ["path", "sha256", "byte_length"],
        "properties": {
            "path": {"type": "string", "minLength": 1},
            "sha256": {"$ref": "#/$defs/sha256"},
            "byte_length": {"type": "integer", "minimum": 0},
        },
    }
    return old


def validation_signature(validator, value: dict) -> tuple[tuple[tuple[object, ...], str], ...]:
    errors = sorted(validator.iter_errors(value), key=lambda error: list(error.path))
    return tuple((tuple(error.path), error.message) for error in errors)


def main() -> int:
    global HOST_VALIDATOR
    module = load_module()
    HOST_VALIDATOR = module._host_validator()
    cases: list[str] = []
    with tempfile.TemporaryDirectory(prefix="host-qualification-v40-", dir=ROOT) as td:
        base = Path(td)

        paths = evidence(base, "pending")
        pending = publish(
            module,
            paths,
            paths["authority"] / "releases/verification/pending",
            registry_row_path=None,
            installed_manifest_path=None,
            cache_comparison_path=None,
            cleared_zip_path=None,
            core_probe_path=None,
        )
        validate(pending)
        assert pending["state"] == "HOST_QUALIFICATION_PENDING"
        assert pending["commit_marker"] is None and pending["failure"] is None
        assert pending["package_clearance_state"] == "PACKAGE_CLEARED"
        assert pending["claims"]["cache_equality_implies_host_load"] is False
        cases.append("missing_host_evidence_pending")

        paths = evidence(base, "unbound")
        unbound = publish(
            module,
            paths,
            paths["authority"] / "releases/verification/unbound",
            registry_row_path=None,
            installed_manifest_path=None,
            cache_comparison_path=None,
            cleared_zip_path=None,
            package_clearance_state="NOT_EVALUATED",
        )
        validate(unbound)
        assert unbound["state"] == "HOST_FUNCTIONAL_UNBOUND"
        assert unbound["core_probe"] is not None and unbound["commit_marker"] is None
        assert unbound["package_clearance_state"] == "NOT_EVALUATED"
        cases.append("functional_without_zip_linkage_unbound")

        paths = evidence(base, "failed-core")
        write(paths["core"], {"status": "failed"})
        failed = publish(
            module, paths, paths["authority"] / "releases/verification/failed-core"
        )
        validate(failed)
        assert failed["state"] == "HOST_QUALIFICATION_FAILED"
        assert failed["failure"]["code"] == "HOST-CORE-PROBE-FAILED"
        cases.append("typed_core_failure")

        paths = evidence(base, "runtime-env-mismatch")
        mismatched_cache = json.loads(paths["cache"].read_text(encoding="utf-8"))
        mismatched_cache["environment"]["suite_pythonpath"] = "unrecorded-route"
        write(paths["cache"], mismatched_cache)
        mismatched = publish(
            module,
            paths,
            paths["authority"] / "releases/verification/runtime-env-mismatch",
        )
        validate(mismatched)
        assert mismatched["state"] == "HOST_QUALIFICATION_FAILED"
        assert mismatched["failure"]["code"] == "HOST-CACHE-COMPARISON-MISSING"
        cases.append("runtime_environment_semantic_mismatch_refused")

        paths = evidence(base, "runtime-env-wrong-type")
        wrong_type_cache = json.loads(paths["cache"].read_text(encoding="utf-8"))
        wrong_type_cache["environment"] = []
        write(paths["cache"], wrong_type_cache)
        wrong_type = publish(
            module,
            paths,
            paths["authority"] / "releases/verification/runtime-env-wrong-type",
        )
        validate(wrong_type)
        assert wrong_type["state"] == "HOST_QUALIFICATION_FAILED"
        assert wrong_type["failure"]["code"] == "HOST-CACHE-COMPARISON-MISSING"
        cases.append("runtime_environment_wrong_type_refused")

        paths = evidence(base, "runtime-suite-universe")
        wrong_suites = json.loads(paths["cache"].read_text(encoding="utf-8"))
        wrong_suites["suites"] = [dict(wrong_suites["suites"][0]) for _ in range(4)]
        wrong_suites["suites"][0]["returncode"] = 1
        write(paths["cache"], wrong_suites)
        suite_refusal = publish(
            module,
            paths,
            paths["authority"] / "releases/verification/runtime-suite-universe",
        )
        validate(suite_refusal)
        assert suite_refusal["state"] == "HOST_QUALIFICATION_FAILED"
        assert suite_refusal["failure"]["code"] == "HOST-CACHE-COMPARISON-MISSING"
        cases.append("runtime_suite_universe_and_returncode_refused")

        paths = evidence(base, "qualified")
        write_order: list[str] = []
        qualified = publish(
            module,
            paths,
            paths["authority"] / "releases/verification/qualified",
            publication_hook=lambda stage, _path: write_order.append(stage),
        )
        validate(qualified)
        assert qualified["state"] == "HOST_QUALIFIED"
        assert qualified["failure"] is None
        assert write_order == ["transaction", "publication_manifest", "commit_marker"]
        assert qualified["claims"]["host_state_changes_package_clearance"] is False
        cases.append("qualified_marker_last")

        replay = publish(
            module, paths, paths["authority"] / "releases/verification/qualified"
        )
        assert replay == qualified
        cases.append("qualified_idempotent_replay")

        paths = evidence(base, "concurrent-distinct")
        out = paths["authority"] / "releases/verification/concurrent-distinct"
        first_published = threading.Event()
        release_first = threading.Event()
        winner: dict[str, object] = {}

        def hold_after_transaction(stage: str, _path: Path) -> None:
            if stage == "transaction":
                first_published.set()
                assert release_first.wait(5), "concurrency barrier timed out"

        def publish_winner() -> None:
            try:
                winner["transaction"] = publish(
                    module, paths, out, publication_hook=hold_after_transaction
                )
            except BaseException as exc:
                winner["error"] = exc

        thread = threading.Thread(target=publish_winner, daemon=True)
        thread.start()
        assert first_published.wait(5), "winner did not reach publication barrier"
        winner_transaction_before = (out / module.TRANSACTION_NAME).read_bytes()
        host_b = dict(HOST)
        host_b["task_id"] = "fresh-task-002"
        core_b = paths["authority"] / "core-probe-b.json"
        core_b_value = json.loads(paths["core"].read_text(encoding="utf-8"))
        core_b_value["host"]["task_id"] = host_b["task_id"]
        write(core_b, core_b_value)
        try:
            expect_error(
                module,
                "HOST-PUBLICATION-INCOMPLETE",
                lambda: publish(
                    module, paths, out, host=host_b, core_probe_path=core_b
                ),
            )
            assert (out / module.TRANSACTION_NAME).read_bytes() == winner_transaction_before
            assert not (out / module.PUBLICATION_NAME).exists()
            assert not (out / module.MARKER_NAME).exists()
        finally:
            release_first.set()
            thread.join(5)
        assert not thread.is_alive() and "error" not in winner, winner.get("error")
        assert winner["transaction"]["state"] == "HOST_QUALIFIED"
        winner_bytes = {
            name: (out / name).read_bytes()
            for name in (
                module.TRANSACTION_NAME,
                module.PUBLICATION_NAME,
                module.MARKER_NAME,
            )
        }
        expect_error(
            module,
            "HOST-PUBLICATION-INCOMPLETE",
            lambda: publish(module, paths, out, host=host_b, core_probe_path=core_b),
        )
        assert winner_bytes == {
            name: (out / name).read_bytes() for name in winner_bytes
        }
        cases.append("concurrent_distinct_writer_loses_without_overwrite")

        paths = evidence(base, "concurrent-replay")
        out = paths["authority"] / "releases/verification/concurrent-replay"
        first_published = threading.Event()
        release_first = threading.Event()
        first: dict[str, object] = {}

        def hold_same_identity(stage: str, _path: Path) -> None:
            if stage == "transaction":
                first_published.set()
                assert release_first.wait(5), "same-identity barrier timed out"

        def publish_first_identity() -> None:
            try:
                first["transaction"] = publish(
                    module, paths, out, publication_hook=hold_same_identity
                )
            except BaseException as exc:
                first["error"] = exc

        thread = threading.Thread(target=publish_first_identity, daemon=True)
        thread.start()
        assert first_published.wait(5)
        second = publish(module, paths, out)
        release_first.set()
        thread.join(5)
        assert not thread.is_alive() and "error" not in first, first.get("error")
        assert first["transaction"] == second
        assert second["state"] == "HOST_QUALIFIED"
        cases.append("concurrent_same_identity_replay_idempotent")

        paths = evidence(base, "registry-pending")
        registry_pending = publish(
            module,
            paths,
            paths["authority"] / "releases/verification/registry-pending",
            registry_row_path=None,
        )
        validate(registry_pending)
        assert registry_pending["state"] == "HOST_QUALIFICATION_PENDING"
        assert registry_pending["cache_comparison"] is not None
        cases.append("missing_registry_observation_pending")

        paths = evidence(base, "fresh-task-pending")
        stale_host = dict(HOST)
        stale_host["fresh_task"] = False
        stale = publish(
            module,
            paths,
            paths["authority"] / "releases/verification/fresh-task-pending",
            host=stale_host,
        )
        validate(stale)
        assert stale["state"] == "HOST_QUALIFICATION_PENDING"
        assert stale["commit_marker"] is None
        cases.append("fresh_task_identity_required")

        paths = evidence(base, "missing-cache-claim")
        missing_cache = publish(
            module,
            paths,
            paths["authority"] / "releases/verification/missing-cache-claim",
            cache_comparison_path=paths["authority"] / "absent-cache.json",
        )
        validate(missing_cache)
        assert missing_cache["failure"]["code"] == "HOST-CACHE-COMPARISON-MISSING"
        cases.append("claimed_cache_evidence_missing_typed")

        paths = evidence(base, "missing-registry-claim")
        missing_registry = publish(
            module,
            paths,
            paths["authority"] / "releases/verification/missing-registry-claim",
            registry_row_path=paths["authority"] / "absent-registry.json",
        )
        validate(missing_registry)
        assert missing_registry["failure"]["code"] == "HOST-REGISTRY-MISSING"
        cases.append("claimed_registry_evidence_missing_typed")

        paths = evidence(base, "missing-manifest-claim")
        missing_manifest = publish(
            module,
            paths,
            paths["authority"] / "releases/verification/missing-manifest-claim",
            installed_manifest_path=paths["authority"] / "absent-manifest.json",
        )
        validate(missing_manifest)
        assert missing_manifest["failure"]["code"] == "HOST-INSTALLED-MANIFEST-MISSING"
        cases.append("claimed_manifest_evidence_missing_typed")

        paths_a = evidence(base, "cross-zip-a", zip_bytes=b"ZIP-A\n")
        paths_b = evidence(base, "cross-zip-b", zip_bytes=b"ZIP-B\n")
        cross_zip = publish(
            module,
            paths_a,
            paths_a["authority"] / "releases/verification/cross-zip",
            cleared_zip_path=paths_b["zip"],
        )
        validate(cross_zip)
        assert cross_zip["state"] == "HOST_QUALIFICATION_FAILED"
        assert cross_zip["failure"]["code"] == "HOST-CLEARED-ZIP-UNBOUND"
        cases.append("cache_cross_zip_contamination")

        paths = evidence(base, "probe-cross-zip")
        core_value = json.loads(paths["core"].read_text(encoding="utf-8"))
        core_value["cleared_zip_sha256"] = sha(b"another ZIP")
        write(paths["core"], core_value)
        probe_cross = publish(
            module,
            paths,
            paths["authority"] / "releases/verification/probe-cross-zip",
        )
        validate(probe_cross)
        assert probe_cross["failure"]["code"] == "HOST-CLEARED-ZIP-UNBOUND"
        cases.append("functional_probe_cross_zip_contamination")

        paths = evidence(base, "recovery")
        out = paths["authority"] / "releases/verification/recovery"

        def crash_after_manifest(stage: str, _path: Path) -> None:
            if stage == "publication_manifest":
                raise RuntimeError("synthetic crash")

        try:
            publish(module, paths, out, publication_hook=crash_after_manifest)
        except RuntimeError as exc:
            assert str(exc) == "synthetic crash"
        else:
            raise AssertionError("synthetic partial publication did not stop")
        assert (out / module.TRANSACTION_NAME).is_file()
        assert (out / module.PUBLICATION_NAME).is_file()
        assert not (out / module.MARKER_NAME).exists()
        recovered = publish(module, paths, out)
        validate(recovered)
        assert recovered["state"] == "HOST_QUALIFIED"
        assert (out / module.MARKER_NAME).is_file()
        cases.append("partial_publication_recovery")

        paths = evidence(base, "marker-appearance-race")
        out = paths["authority"] / "releases/verification/marker-appearance-race"
        foreign_marker = canonical({"foreign": "concurrent marker"})

        def inject_marker(stage: str, _path: Path) -> None:
            if stage == "publication_manifest":
                marker = out / module.MARKER_NAME
                descriptor = os.open(
                    marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
                )
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(foreign_marker)
                    stream.flush()
                    os.fsync(stream.fileno())

        expect_error(
            module,
            "HOST-PUBLICATION-INCOMPLETE",
            lambda: publish(module, paths, out, publication_hook=inject_marker),
        )
        assert (out / module.MARKER_NAME).read_bytes() == foreign_marker
        assert not list(out.glob("*.tmp"))
        cases.append("marker_appearance_race_never_overwritten")

        paths = evidence(base, "toctou")
        out = paths["authority"] / "releases/verification/toctou"

        def mutate_core() -> None:
            write(paths["core"], {"status": "failed-after-prepare"})

        expect_error(
            module,
            "HOST-PUBLICATION-INCOMPLETE",
            lambda: publish(module, paths, out, before_commit=mutate_core),
        )
        assert not (out / module.MARKER_NAME).exists()
        cases.append("toctou_input_mutation_refused")

        paths = evidence(base, "manifest-hook-toctou")
        out = paths["authority"] / "releases/verification/manifest-hook-toctou"

        def mutate_after_manifest(stage: str, _path: Path) -> None:
            if stage == "publication_manifest":
                value = json.loads(paths["core"].read_text(encoding="utf-8"))
                value["post_prepare_nonce"] = "changed-before-marker"
                write(paths["core"], value)

        expect_error(
            module,
            "HOST-PUBLICATION-INCOMPLETE",
            lambda: publish(
                module, paths, out, publication_hook=mutate_after_manifest
            ),
        )
        assert (out / module.TRANSACTION_NAME).is_file()
        assert (out / module.PUBLICATION_NAME).is_file()
        assert not (out / module.MARKER_NAME).exists()
        cases.append("manifest_hook_input_mutation_blocks_marker")

        paths = evidence(base, "post-marker-input-mutation")
        out = paths["authority"] / "releases/verification/post-marker-input-mutation"

        def mutate_after_marker(stage: str, _path: Path) -> None:
            if stage == "commit_marker":
                value = json.loads(paths["core"].read_text(encoding="utf-8"))
                value["post_marker_nonce"] = "stale-committed-input"
                write(paths["core"], value)

        expect_error(
            module,
            "HOST-PUBLICATION-INCOMPLETE",
            lambda: publish(module, paths, out, publication_hook=mutate_after_marker),
        )
        assert (out / module.MARKER_NAME).is_file()
        stale_chain = {
            name: (out / name).read_bytes()
            for name in (
                module.TRANSACTION_NAME,
                module.PUBLICATION_NAME,
                module.MARKER_NAME,
            )
        }
        expect_error(
            module,
            "HOST-PUBLICATION-INCOMPLETE",
            lambda: publish(module, paths, out),
        )
        assert stale_chain == {name: (out / name).read_bytes() for name in stale_chain}
        cases.append("post_marker_stale_input_fails_publisher_and_replay")

        paths = evidence(base, "partial-marker")
        out = paths["authority"] / "releases/verification/partial-marker"
        write(out / module.MARKER_NAME, {"foreign": True})
        expect_error(
            module,
            "HOST-PUBLICATION-INCOMPLETE",
            lambda: publish(module, paths, out),
        )
        cases.append("partial_marker_refused")

        paths = evidence(base, "immutable")
        out = paths["authority"] / "releases/verification/immutable"
        publish(module, paths, out)
        write(paths["core"], {"status": "failed"})
        expect_error(
            module,
            "HOST-PUBLICATION-INCOMPLETE",
            lambda: publish(module, paths, out),
        )
        cases.append("committed_transaction_immutable")

        paths = evidence(base, "destination")
        expect_error(
            module,
            "HOST-PUBLICATION-INCOMPLETE",
            lambda: publish(module, paths, paths["authority"] / "reviews/host"),
        )
        cases.append("destination_boundary")

        invalid_sha = deepcopy(qualified)
        invalid_sha["registry_row"]["sha256"] = "z" * 64
        invalid_timestamp = deepcopy(pending)
        invalid_timestamp["created_at"] = 7
        incomplete_qualified = deepcopy(qualified)
        incomplete_qualified["commit_marker"] = None
        invalid_failure = deepcopy(failed)
        invalid_failure["failure"]["code"] = "HOST-UNKNOWN"
        invalid_unbound = deepcopy(unbound)
        invalid_unbound["core_probe"]["byte_length"] = -1
        unexpected = deepcopy(pending)
        unexpected["unexpected"] = True
        equivalence_vectors = [
            pending,
            unbound,
            failed,
            qualified,
            invalid_sha,
            invalid_timestamp,
            incomplete_qualified,
            invalid_failure,
            invalid_unbound,
            unexpected,
        ]
        old_validator = Draft202012Validator(pre_refactor_schema())
        new_validator = module._host_validator()
        for vector in equivalence_vectors:
            old_result = validation_signature(old_validator, vector)
            new_result = validation_signature(new_validator, vector)
            assert old_result == new_result
            if not old_result:
                old_output = canonical(deepcopy(vector))
                new_output = canonical(vector)
                assert old_output == new_output

        schema_attack_root = base / "schema-attacks"
        common_value = json.loads(COMMON_SCHEMA_PATH.read_text(encoding="utf-8"))
        expect_error(
            module,
            "HOST-PUBLICATION-INCOMPLETE",
            lambda: module._host_validator(
                common_schema_path=schema_attack_root / "missing-common.json"
            ),
        )
        wrong_id = deepcopy(common_value)
        wrong_id["$id"] = "https://example.invalid/wrong-common-schema.json"
        wrong_id_path = schema_attack_root / "wrong-id.json"
        write(wrong_id_path, wrong_id)
        expect_error(
            module,
            "HOST-PUBLICATION-INCOMPLETE",
            lambda: module._host_validator(common_schema_path=wrong_id_path),
        )
        wrong_hash = deepcopy(common_value)
        wrong_hash["$comment"] = "synthetic hash contamination"
        wrong_hash_path = schema_attack_root / "wrong-hash.json"
        write(wrong_hash_path, wrong_hash)
        expect_error(
            module,
            "HOST-PUBLICATION-INCOMPLETE",
            lambda: module._host_validator(common_schema_path=wrong_hash_path),
        )
        unresolved = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        encoded = json.dumps(unresolved)
        encoded = encoded.replace(
            module.COMMON_SCHEMA_ID,
            "https://co-author-harness.local/schemas/unresolved-common.json",
            1,
        )
        unresolved_path = schema_attack_root / "unresolved-host.json"
        write(unresolved_path, json.loads(encoded))
        expect_error(
            module,
            "HOST-PUBLICATION-INCOMPLETE",
            lambda: module._validate(
                pending,
                schema_path=unresolved_path,
                common_schema_path=COMMON_SCHEMA_PATH,
            ),
        )

        assert not list(base.rglob("*.staged")), "exclusive publication left staged residue"
        assert not list(base.rglob("*.tmp")), "host transaction left shared-temp residue"

    required_startup_contract = {
        "startup_catalog_missing_refused", "startup_catalog_stale_refused",
        "catalog_cli_cache_mismatch_refused", "installed_root_mismatch_refused",
        "manifest_provenance_mismatch_refused", "loaded_path_mismatch_refused",
        "fresh_task_mismatch_refused", "startup_toctou_refused",
        "six_suite_runtime_receipt_supported",
    }
    advertised = set(getattr(module, "STARTUP_ATTESTATION_CONTRACT", ()))
    assert required_startup_contract <= advertised, (
        f"missing host startup contracts: {sorted(required_startup_contract-advertised)}"
    )
    print(
        "host_qualification_transaction_smoketest: PASS "
        f"({len(cases)} cases; {len(equivalence_vectors)} equivalence vectors; 4 schema attacks)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
