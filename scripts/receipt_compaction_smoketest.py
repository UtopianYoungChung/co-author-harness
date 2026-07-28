#!/usr/bin/env python3
"""Focused contract, losslessness, alias, refusal, and atomicity tests."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
import unicodedata
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/receipt_compaction.py"
FIXTURE = ROOT / "scripts/fixtures/receipt_compaction/cases.json"
COMMON_SCHEMA = ROOT / "references/schemas/common_scholarly_primitives.schema.json"
INDEX_SCHEMA = ROOT / "references/schemas/compact_receipt_index.schema.json"


def load_compaction() -> Any:
    sys.path.insert(0, str(SCRIPT.parent))
    try:
        spec = importlib.util.spec_from_file_location("receipt_compaction_test", SCRIPT)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPT.parent))


compaction = load_compaction()


def pretty(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pretty(value))


def materialize_source(source: Path) -> tuple[dict[str, bytes], dict[str, dict[str, Any]]]:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert fixture["provenance"] == {
        "origin": "self-authored synthetic", "author_role": "Evidence Builder", "external_sources": [],
    }
    source.mkdir()
    expected: dict[str, bytes] = {}
    documents: dict[str, dict[str, Any]] = {}
    inventories: dict[str, dict[str, Any]] = {}
    for name, template in fixture["inventory_templates"].items():
        inventories[name] = {
            "inventory_template": name,
            "purpose": template["purpose"],
            "files": [
                {
                    "path": f"{template['path_prefix']}{number + 1:03d}.json",
                    "fingerprint": sha(f"{name}:{number + 1}".encode("utf-8")),
                    "byte_length": 1000 + number,
                }
                for number in range(template["entry_count"])
            ],
        }
    for row in fixture["receipts"]:
        document = copy.deepcopy(row["document"])
        document["file_inventory"] = copy.deepcopy(inventories[row["inventory_template"]])
        relative = row["relative_path"]
        payload = pretty(document)
        path = source / Path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        expected[relative] = payload
        documents[relative] = document
    return expected, documents


def expect(code: str, action: Callable[[], Any]) -> None:
    try:
        action()
    except (compaction.ReceiptCompactionError, compaction.destination_capability.DestinationRefused) as exc:
        assert exc.code == code, f"expected {code}, got {exc.code}: {exc}"
    else:
        raise AssertionError(f"expected refusal {code}")


def copy_archive(source: Path, target: Path) -> Path:
    shutil.copytree(source, target)
    return target


def index_paths(archive: Path) -> list[Path]:
    return sorted((archive / "indices").glob("*.json"))


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def restored_files(root: Path) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*.json")}


def pointer_value(document: Any, pointer: str) -> Any:
    value = document
    for token in pointer.split("/")[1:]:
        token = token.replace("~1", "/").replace("~0", "~")
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def descriptor_for(archive: Path, index: dict[str, Any]) -> dict[str, Any]:
    return read_json(archive / index["detail_blob"]["path"])


def first_blob_path(archive: Path, index: dict[str, Any]) -> Path:
    descriptor = descriptor_for(archive, index)
    return archive / descriptor["fields"][0]["blob"]["path"]


def main() -> int:
    fixture_hash_before = sha(FIXTURE.read_bytes())
    assert sha(COMMON_SCHEMA.read_bytes()) == compaction.COMMON_SCHEMA_SHA256
    codes_tested: set[str] = set()
    alias_attacks = 0
    with tempfile.TemporaryDirectory(prefix="receipt-compaction-") as raw_temp:
        base = Path(raw_temp)
        source = base / "source"
        expected, documents = materialize_source(source)
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        metrics_runs: list[dict[str, Any]] = []
        archives: list[Path] = []
        for run_number in (1, 2):
            archive = base / f"archive-{run_number}"
            metrics = compaction.compact(source, archive, fixture["fixture_id"], fixture["compacted_at"])
            assert metrics == compaction.validate(archive)
            assert metrics["receipt_count"] == 6
            assert metrics["reduction_bytes"] > 0 and metrics["reduction_ratio"] > 0
            restored = base / f"restored-{run_number}"
            result = compaction.restore(archive, restored)
            assert result["receipt_count"] == 6
            assert restored_files(restored) == expected
            metrics_runs.append(metrics)
            archives.append(archive)
        assert metrics_runs[0] == metrics_runs[1]

        archive = archives[0]
        indices = [read_json(path) for path in index_paths(archive)]
        assert all(set(index) == compaction.INDEX_FIELDS for index in indices)
        assert all(list(index) == [
            "schema_version", "index_id", "source_receipt", "detail_blob", "verdict",
            "counts", "warnings", "recovery_commands", "hashes",
            "compression_measurement", "created_at",
        ] for index in indices)
        by_source = {index["source_receipt"]["path"]: index for index in indices}
        field_references = 0
        all_projection_rows = 0
        for relative, document in documents.items():
            index = by_source[relative]
            descriptor = descriptor_for(archive, index)
            assert descriptor["top_level_keys"] == list(document)
            assert [field["key"] for field in descriptor["fields"]] == list(document)
            field_references += len(descriptor["fields"])
            projections = compaction._project_facts(document)
            for category in compaction.ALIASES:
                assert index[category] == projections[category]
                for row in index[category]:
                    assert pointer_value(document, row["pointer"]) == row["value"]
                    assert sha(pretty(row["value"])) == row["value_sha256"]
                    all_projection_rows += 1
        nested = by_source["source/source-receipt.json"]
        required_nested = {
            "verdict": ("/nested_assurance/outcome", "outcome"),
            "counts": ("/nested_assurance/metrics", "metrics"),
            "warnings": ("/nested_assurance/alerts", "alerts"),
            "recovery_commands": ("/nested_assurance/commands", "commands"),
            "hashes": ("/nested_assurance/digests", "digests"),
        }
        for category, (pointer, alias) in required_nested.items():
            rows = [row for row in nested[category] if row["pointer"] == pointer and row["alias"] == alias]
            assert len(rows) == 1 and rows[0]["value"] == pointer_value(documents["source/source-receipt.json"], pointer)
        assert all(nested[category] for category in compaction.ALIASES)
        assert metrics_runs[0]["field_blob_count"] < field_references

        attacked = copy_archive(archive, base / "attack-missing")
        first_index = read_json(index_paths(attacked)[0])
        (attacked / first_index["detail_blob"]["path"]).unlink()
        expect(compaction.RC_DETAIL_MISSING, lambda: compaction.validate(attacked))
        codes_tested.add(compaction.RC_DETAIL_MISSING)

        attacked = copy_archive(archive, base / "attack-unknown")
        (attacked / "blobs/unknown.json").write_bytes(b"{}\n")
        expect(compaction.RC_DETAIL_UNKNOWN, lambda: compaction.validate(attacked))
        codes_tested.add(compaction.RC_DETAIL_UNKNOWN)

        attacked = copy_archive(archive, base / "attack-blob-tamper")
        first_index = read_json(index_paths(attacked)[0])
        blob_path = first_blob_path(attacked, first_index)
        blob_path.write_bytes(blob_path.read_bytes() + b" ")
        expect(compaction.RC_DETAIL_TAMPERED, lambda: compaction.validate(attacked))
        codes_tested.add(compaction.RC_DETAIL_TAMPERED)

        attacked = copy_archive(archive, base / "attack-original-binding")
        path = next(
            path for path in index_paths(attacked)
            if read_json(path)["source_receipt"]["path"] == "source/source-receipt.json"
        )
        index = read_json(path)
        old_descriptor_path = attacked / index["detail_blob"]["path"]
        descriptor = read_json(old_descriptor_path)
        inventory_field = next(field for field in descriptor["fields"] if field["key"] == "file_inventory")
        inventory = read_json(attacked / inventory_field["blob"]["path"])
        inventory["unclassified_mutation"] = "changes reconstruction without changing projected facts"
        inventory_raw = pretty(inventory)
        inventory_relative = f"blobs/{sha(inventory_raw)}.json"
        (attacked / inventory_relative).write_bytes(inventory_raw)
        inventory_field["blob"] = {
            "path": inventory_relative, "sha256": sha(inventory_raw), "byte_length": len(inventory_raw),
        }
        descriptor_raw = pretty(descriptor)
        descriptor_relative = f"details/{sha(descriptor_raw)}.json"
        (attacked / descriptor_relative).write_bytes(descriptor_raw)
        old_descriptor_path.unlink()
        index["detail_blob"] = {
            "path": descriptor_relative, "sha256": sha(descriptor_raw), "byte_length": len(descriptor_raw),
        }
        write_json(path, index)
        expect(compaction.RC_ORIGINAL_MISMATCH, lambda: compaction.validate(attacked))
        codes_tested.add(compaction.RC_ORIGINAL_MISMATCH)

        attacked = copy_archive(archive, base / "attack-fact")
        path = index_paths(attacked)[0]
        index = read_json(path)
        category = next(category for category in compaction.ALIASES if index[category])
        index[category].pop()
        write_json(path, index)
        expect(compaction.RC_INDEX_TAMPERED, lambda: compaction.validate(attacked))
        codes_tested.add(compaction.RC_INDEX_TAMPERED)

        attacked = copy_archive(archive, base / "attack-schema")
        path = index_paths(attacked)[0]
        index = read_json(path)
        del index["detail_blob"]
        write_json(path, index)
        expect(compaction.RC_INDEX_SCHEMA, lambda: compaction.validate(attacked))
        codes_tested.add(compaction.RC_INDEX_SCHEMA)

        attacked = copy_archive(archive, base / "attack-measurement")
        path = index_paths(attacked)[0]
        index = read_json(path)
        index["compression_measurement"]["archive_compact_bytes"] += 1
        write_json(path, index)
        expect(compaction.RC_INDEX_TAMPERED, lambda: compaction.validate(attacked))

        attacked = copy_archive(archive, base / "attack-reference")
        path = index_paths(attacked)[0]
        index = read_json(path)
        index["detail_blob"]["path"] = "details/not-content-addressed.json"
        write_json(path, index)
        expect(compaction.RC_DETAIL_UNKNOWN, lambda: compaction.validate(attacked))

        # A controlling index must be read from its exact archive-contained
        # path, never through a symlink/reparse escape to identical bytes.
        attacked = copy_archive(archive, base / "attack-index-symlink")
        path = index_paths(attacked)[0]
        external_index = base / "external-identical-index.json"
        external_index.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(external_index)
        expect(compaction.RC_PATH_ALIAS, lambda: compaction.validate(attacked))
        escaped_restore = base / "escaped-index-restore"
        expect(compaction.RC_PATH_ALIAS, lambda: compaction.restore(attacked, escaped_restore))
        assert not escaped_restore.exists()
        alias_attacks += 2

        # Exact reviewer alias pairs and Windows/path canonicalization attacks.
        for values in (
            ["a/one.json", "a/./one.json"],
            ["a/One.json", "a/one.json"],
            ["a/one.json", "a/one.json."],
            ["a/one.json", "a/one.json "],
            ["a//one.json"], ["a\\one.json"], ["C:/a/one.json"], ["/a/one.json"],
            ["a/../one.json"], ["a/CON.json"],
            ["a/" + unicodedata.normalize("NFD", "café") + ".json"],
        ):
            expect(compaction.RC_PATH_ALIAS, lambda values=values: compaction._assert_unique_paths(values))
            alias_attacks += 1
        codes_tested.add(compaction.RC_PATH_ALIAS)

        for pair, name in ((["a/one.json", "a/./one.json"], "dot"), (["a/One.json", "a/one.json"], "case")):
            attacked = copy_archive(archive, base / f"attack-validate-{name}")
            paths = index_paths(attacked)[:2]
            for path, source_path in zip(paths, pair):
                index = read_json(path)
                index["source_receipt"]["path"] = source_path
                write_json(path, index)
            expect(compaction.RC_PATH_ALIAS, lambda attacked=attacked: compaction.validate(attacked))
            alias_attacks += 1
        for suffix, name in ((".", "trailing-dot"), (" ", "trailing-space")):
            attacked = copy_archive(archive, base / f"attack-validate-{name}")
            path = index_paths(attacked)[0]
            index = read_json(path)
            index["source_receipt"]["path"] = "a/one.json" + suffix
            write_json(path, index)
            expect(compaction.RC_PATH_ALIAS, lambda attacked=attacked: compaction.validate(attacked))
            alias_attacks += 1

        original_loader = compaction._load_and_validate
        collision_output = base / "collision-restore"
        try:
            compaction._load_and_validate = lambda _root: (
                [], {}, [("a/one.json", b"first\n"), ("a/one.json", b"second\n")]
            )
            expect(compaction.RC_PATH_ALIAS, lambda: compaction.restore(archive, collision_output))
            alias_attacks += 1
        finally:
            compaction._load_and_validate = original_loader
        assert not collision_output.exists(), "restore collision preflight wrote partial output"

        original_common = compaction.COMMON_SCHEMA
        try:
            compaction.COMMON_SCHEMA = base / "missing-common.schema.json"
            expect(compaction.RC_COMMON_SCHEMA, lambda: compaction.validate(archive))
            wrong = read_json(COMMON_SCHEMA)
            wrong["$id"] = "https://co-author-harness.local/schemas/wrong.schema.json"
            wrong_path = base / "wrong-common.schema.json"
            write_json(wrong_path, wrong)
            compaction.COMMON_SCHEMA = wrong_path
            expect(compaction.RC_COMMON_SCHEMA, lambda: compaction.validate(archive))
            changed = read_json(COMMON_SCHEMA)
            changed["$comment"] = "same identity different bytes"
            changed_path = base / "changed-common.schema.json"
            write_json(changed_path, changed)
            compaction.COMMON_SCHEMA = changed_path
            expect(compaction.RC_COMMON_SCHEMA, lambda: compaction.validate(archive))
            codes_tested.add(compaction.RC_COMMON_SCHEMA)
        finally:
            compaction.COMMON_SCHEMA = original_common

        original_registry = compaction.Registry
        real_registry = compaction.Registry
        try:
            class DroppingRegistry:
                def with_resource(self, *_args: Any, **_kwargs: Any) -> Any:
                    return real_registry()
            compaction.Registry = DroppingRegistry
            expect(compaction.RC_COMMON_SCHEMA, lambda: compaction.validate(archive))
        finally:
            compaction.Registry = original_registry

        original_index_schema = compaction.INDEX_SCHEMA
        try:
            wrong_schema = read_json(INDEX_SCHEMA)
            wrong_schema["$id"] = "https://co-author-harness.local/schemas/wrong-index.schema.json"
            wrong_path = base / "wrong-index.schema.json"
            write_json(wrong_path, wrong_schema)
            compaction.INDEX_SCHEMA = wrong_path
            expect(compaction.RC_INDEX_SCHEMA, lambda: compaction.validate(archive))
        finally:
            compaction.INDEX_SCHEMA = original_index_schema

        bad_source = base / "bad-source"
        bad_source.mkdir()
        (bad_source / "empty.json").write_bytes(b"{}\n")
        expect(compaction.RC_INPUT_INVALID, lambda: compaction.compact(
            bad_source, base / "bad-output", "bad", fixture["compacted_at"]
        ))
        codes_tested.add(compaction.RC_INPUT_INVALID)
        assert not (base / "bad-output").exists()

        noncanonical = base / "noncanonical"
        materialize_source(noncanonical)
        first = sorted(noncanonical.rglob("*.json"))[0]
        first.write_bytes(first.read_bytes() + b" ")
        expect(compaction.RC_NONCANONICAL, lambda: compaction.compact(
            noncanonical, base / "noncanonical-output", "bad", fixture["compacted_at"]
        ))
        codes_tested.add(compaction.RC_NONCANONICAL)

        original_write = compaction._write_bytes
        write_count = 0
        def failing_write(path: Path, payload: bytes) -> None:
            nonlocal write_count
            write_count += 1
            if write_count == 2:
                raise OSError("synthetic interruption")
            original_write(path, payload)
        atomic_output = base / "atomic-output"
        try:
            compaction._write_bytes = failing_write
            expect(compaction.RC_ATOMIC_WRITE, lambda: compaction.compact(
                source, atomic_output, fixture["fixture_id"], fixture["compacted_at"]
            ))
        finally:
            compaction._write_bytes = original_write
        assert not atomic_output.exists() and not list(base.glob(".atomic-output.tmp-*"))
        atomic_restore = base / "atomic-restore"
        write_count = 0
        try:
            compaction._write_bytes = failing_write
            expect(compaction.RC_ATOMIC_WRITE, lambda: compaction.restore(archive, atomic_restore))
        finally:
            compaction._write_bytes = original_write
        assert not atomic_restore.exists() and not list(base.glob(".atomic-restore.tmp-*"))
        codes_tested.add(compaction.RC_ATOMIC_WRITE)

        existing = base / "existing"
        existing.mkdir()
        expect(compaction.RC_OUTPUT_EXISTS, lambda: compaction.compact(
            source, existing, fixture["fixture_id"], fixture["compacted_at"]
        ))
        codes_tested.add(compaction.RC_OUTPUT_EXISTS)

        forbidden = ROOT / "outputs/co-author-harness/receipt-compaction-smoketest"
        expect(compaction.destination_capability.DEST_MISROUTED, lambda: compaction.compact(
            source, forbidden, fixture["fixture_id"], fixture["compacted_at"]
        ))
        codes_tested.add(compaction.destination_capability.DEST_MISROUTED)
        assert not forbidden.exists()

        metrics = metrics_runs[0]
        assert fixture_hash_before == sha(FIXTURE.read_bytes())
        print(json.dumps({
            "status": "PASS", "focused_runs": 2,
            "receipt_count": metrics["receipt_count"],
            "field_references": field_references,
            "field_blob_count": metrics["field_blob_count"],
            "detail_blob_count": metrics["detail_blob_count"],
            "projection_rows": all_projection_rows,
            "alias_attacks": alias_attacks,
            "schema_dependency_attacks": 4,
            "original_bytes": metrics["original_bytes"],
            "compact_bytes": metrics["compact_bytes"],
            "reduction_bytes": metrics["reduction_bytes"],
            "reduction_ratio": metrics["reduction_ratio"],
            "index_set_sha256": metrics["index_set_sha256"],
            "exact_reconstructions": len(expected) * 2,
            "refusal_codes": sorted(codes_tested),
            "fixture_sha256": fixture_hash_before,
        }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
