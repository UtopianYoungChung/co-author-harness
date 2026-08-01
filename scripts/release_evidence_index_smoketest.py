#!/usr/bin/env python3
"""Focused synthetic checks for immutable release evidence indices."""

from __future__ import annotations

import copy
import hashlib
import json
import tempfile
from pathlib import Path

import release_evidence_index as indexer
import destination_capability as destinations


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def dump(path: Path, value: dict) -> None:
    write(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def refusal(fn, code: str) -> None:
    try:
        fn()
    except indexer.IndexRefusal as exc:
        assert exc.code == code, (exc.code, code)
    else:
        raise AssertionError(f"expected {code}")


def topology_receipt(commit: str) -> dict:
    records = []
    for name in ("source", "build", "archive", "unpacked", "installed_cache"):
        records.append({
            "plane_kind": name,
            "path": f"C:/fixture/{name}",
            "path_kind": "file" if name == "archive" else "directory",
            "digest_sha256": "a" * 64,
            "git_commit": commit if name in {"source", "build"} else None,
            "git_state": "source_main" if name == "source" else "detached_clean" if name == "build" else "absent",
            "provenance_commit": commit if name not in {"source", "build"} else None,
        })
    return {
        "schema_version": "1.0.0",
        "receipt_type": "qualification_plane_topology",
        "source_commit": commit,
        "planes": records,
        "source_stable": True,
        "findings": [],
        "verdict": "qualified",
    }


def archive_plane_receipt(commit: str, name: str, topology: dict) -> dict:
    topology_sha = hashlib.sha256(
        (json.dumps(topology, sort_keys=True, separators=(",", ":")) + "\n").encode()
    ).hexdigest()
    return {
        "schema_version": "1.2.0",
        "receipt_type": "archive_runtime_probe" if name == "archive" else "unpacked_zip_runtime",
        "plane_kind": name,
        "topology_receipt": {"sha256": "b" * 64, "source_commit": commit},
        "derived_topology_receipt": {"sha256": topology_sha, "payload": topology},
        "runtime_plane_receipt": {
            "payload": {"topology_receipt": {"sha256": topology_sha, "source_commit": commit, "plane_kind": "unpacked"}}
        },
        "findings": [],
        "verdict": "qualified",
    }


def cache_plane_receipt(commit: str) -> dict:
    return {
        "schema_version": "1.1.0",
        "receipt_type": "runtime_plane_probe",
        "plane_kind": "installed_cache",
        "topology_receipt": {"sha256": "c" * 64, "source_commit": commit, "plane_kind": "installed_cache"},
        "cache_state": "CODEX_CACHE_QUALIFIED",
        "suites": [
            {"name": f"suite-{index}", "status": "passed", "returncode": 0}
            for index in range(6)
        ],
        "findings": [],
        "verdict": "qualified",
    }


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="release-index-") as raw:
        root = Path(raw).resolve()
        artifact = root / "releases/candidate.zip"
        checksum = root / "releases/candidate.sha256"
        receipt = root / "verification/gate.log"
        for path, data in ((artifact, b"zip"), (checksum, b"sum"), (receipt, b"PASS\n")):
            write(path, data)
        source = {"commit": "1" * 40, "tree": "2" * 40, "branch": "main", "origin_main": "3" * 40, "remote_main": "3" * 40}
        topology_path = root / "verification/topology.json"
        archive_path = root / "verification/archive.json"
        unpacked_path = root / "verification/unpacked.json"
        cache_path = root / "verification/cache.json"
        topology = topology_receipt(source["commit"])
        dump(topology_path, topology)
        dump(archive_path, archive_plane_receipt(source["commit"], "archive", topology))
        dump(unpacked_path, archive_plane_receipt(source["commit"], "unpacked", topology))
        dump(cache_path, cache_plane_receipt(source["commit"]))
        plane_paths = {
            "source": topology_path,
            "build": topology_path,
            "archive": archive_path,
            "unpacked": unpacked_path,
            "installed_cache": cache_path,
        }
        package = {
            "schema_version": "1.0.0", "index_type": "package", "release_version": "0.39.0",
            "sequence": 1, "created_at": "2026-07-25T18:00:00Z", "prior_index": None,
            "source": source, "package_index": None,
            "artifacts": [{"id": "zip", "path": artifact.relative_to(root).as_posix(), "sha256": sha(artifact)}, {"id": "checksum", "path": checksum.relative_to(root).as_posix(), "sha256": sha(checksum)}],
            "evidence": [{"id": "gate", "path": receipt.relative_to(root).as_posix(), "sha256": sha(receipt), "result": "PASS"}],
            "planes": [
                {"name": name, "status": "qualified", "receipt": {"path": plane_paths[name].relative_to(root).as_posix(), "sha256": sha(plane_paths[name])}}
                for name in ("source", "build", "archive", "unpacked", "installed_cache")
            ],
            "warnings": [], "omissions": ["Cowork upload is a later host plane"],
            "no_claims": ["PACKAGE_CLEARED is not HOST_QUALIFIED"], "reviewer": None,
            "status": "IMPLEMENTED",
        }
        spec = root / "package-spec.json"; dump(spec, package)
        out = root / "package-index.json"; indexer.build(spec, out, root)
        first = out.read_bytes(); indexer.build(spec, out, root); assert out.read_bytes() == first
        forged_plane = copy.deepcopy(package)
        forged_plane["planes"][4]["receipt"] = {
            "path": receipt.relative_to(root).as_posix(), "sha256": sha(receipt),
        }
        forged_plane_spec = root / "forged-plane.json"; dump(forged_plane_spec, forged_plane)
        refusal(
            lambda: indexer.build(forged_plane_spec, root / "forged-plane-out.json", root),
            "RELEASE-INDEX-PLANE-RECEIPT",
        )
        false_host = copy.deepcopy(package)
        false_host["status"] = "HOST_QUALIFIED"
        false_host_spec = root / "false-host.json"; dump(false_host_spec, false_host)
        refusal(
            lambda: indexer.build(false_host_spec, root / "false-host-out.json", root),
            "RELEASE-INDEX-GLOBAL-STATE",
        )
        stale = copy.deepcopy(package); stale["artifacts"][0]["sha256"] = "0" * 64
        stale_spec = root / "stale.json"; dump(stale_spec, stale)
        refusal(lambda: indexer.build(stale_spec, root / "stale-out.json", root), "RELEASE-INDEX-STALE")
        unknown_plane = copy.deepcopy(package)
        unknown_plane["planes"][4]["name"] = "cowork_cache"
        unknown_plane_spec = root / "unknown-plane.json"; dump(unknown_plane_spec, unknown_plane)
        refusal(
            lambda: indexer.build(unknown_plane_spec, root / "unknown-plane-out.json", root),
            "RELEASE-INDEX-SCHEMA",
        )
        unbound_qualified = copy.deepcopy(package)
        unbound_qualified["planes"][4]["receipt"] = None
        unbound_qualified_spec = root / "unbound-qualified-plane.json"; dump(unbound_qualified_spec, unbound_qualified)
        refusal(
            lambda: indexer.build(unbound_qualified_spec, root / "unbound-qualified-plane-out.json", root),
            "RELEASE-INDEX-SCHEMA",
        )
        changed = copy.deepcopy(package); changed["warnings"] = ["changed"]
        changed_spec = root / "changed.json"; dump(changed_spec, changed)
        refusal(lambda: indexer.build(changed_spec, out, root), "RELEASE-INDEX-IMMUTABLE")
        release = copy.deepcopy(package)
        release.update({"index_type": "release", "sequence": 2, "package_index": {"path": out.relative_to(root).as_posix(), "sha256": sha(out)}, "status": "HOST_QUALIFICATION_PENDING"})
        release_spec = root / "release-spec.json"; dump(release_spec, release)
        release_out = root / "release-index.json"
        indexer.append_release(out, release_spec, release_out, root)
        bad = copy.deepcopy(release); bad["package_index"]["sha256"] = "f" * 64
        bad_spec = root / "bad-release.json"; dump(bad_spec, bad)
        refusal(lambda: indexer.append_release(out, bad_spec, root / "bad.json", root), "RELEASE-INDEX-CHAIN")
        report = root / "report.md"; indexer.render(release_out, report, root)
        text = report.read_text(encoding="utf-8")
        assert "HOST_QUALIFICATION_PENDING" in text and "PACKAGE_CLEARED is not HOST_QUALIFIED" in text
        protected = Path(__file__).resolve().parents[2] / "protected-release-index.json"
        try:
            indexer.build(spec, protected, root)
        except destinations.DestinationRefused as exc:
            assert exc.code == destinations.DEST_PROTECTED
        else:
            raise AssertionError("protected release-index destination accepted")
        link_target = root / "linked-receipt.log"
        link_target.write_bytes(receipt.read_bytes())
        linked = root / "verification/linked.log"
        linked.symlink_to(link_target)
        linked_package = copy.deepcopy(package)
        linked_package["evidence"][0].update({
            "path": linked.relative_to(root).as_posix(),
            "sha256": sha(link_target),
        })
        linked_spec = root / "linked.json"; dump(linked_spec, linked_package)
        refusal(
            lambda: indexer.build(linked_spec, root / "linked-out.json", root),
            "RELEASE-INDEX-PATH",
        )
    print("release_evidence_index_smoketest: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
