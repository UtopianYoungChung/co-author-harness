#!/usr/bin/env python3
"""Focused C2 red boundary for PDF extractor provenance and failure atomicity."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator

import evidence_publication
from c2_evidence_fixture_support import ASSET_ROOT, build_activation_fixture
from c2_evidence_validation import validate_extract_receipt
from evidence_publication import (
    EvidencePublicationError,
    publish_committed,
    recover_committed,
)


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "source_extract.py"
EXTRACT_VALIDATOR = Draft202012Validator(json.loads(
    (ROOT / "references" / "schemas" / "canonical_extract_receipt.schema.json").read_text(
        encoding="utf-8"
    )
))
BLOCKER_VALIDATOR = Draft202012Validator(json.loads(
    (ROOT / "references" / "schemas" / "source_extract_blocker.schema.json").read_text(
        encoding="utf-8"
    )
))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_state(root: Path) -> list[tuple[str, str, str | None]]:
    if not root.exists():
        return []
    rows: list[tuple[str, str, str | None]] = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        rows.append((rel, "file", sha(path)) if path.is_file() else (rel, "dir", None))
    return rows


def run_extract(
    source: Path,
    text_out: Path,
    receipt_out: Path,
    *,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--source",
            str(source),
            "--text-out",
            str(text_out),
            "--receipt-out",
            str(receipt_out),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def run_future_extract(
    source: Path,
    *,
    project_root: Path,
    project_manifest: Path,
    text_out: Path,
    receipt_out: Path,
    raw_out: Path,
    page_map_out: Path,
    page_map_seed: Path | None = None,
    manifest_out: Path,
    marker_out: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [
            sys.executable,
            str(SCRIPT),
            "--source",
            str(source),
            "--text-out",
            str(text_out),
            "--receipt-out",
            str(receipt_out),
            "--project-root",
            str(project_root),
            "--project-manifest",
            str(project_manifest),
            "--source-key",
            "fixture-centroid-evidence",
            "--raw-out",
            str(raw_out),
            "--page-map-out",
            str(page_map_out),
            "--manifest-out",
            str(manifest_out),
            "--commit-marker-out",
            str(marker_out),
        ]
    if page_map_seed is not None:
        command.extend(["--page-map-seed", str(page_map_seed)])
    return subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="coauthor-source-extract-c2-") as td:
        root = Path(td)
        retry_target = root / "transient-replace" / "journal.json"
        real_replace = evidence_publication.os.replace
        replace_attempts = 0

        def transient_replace(source: Path, destination: Path) -> None:
            nonlocal replace_attempts
            replace_attempts += 1
            if replace_attempts < 3:
                raise PermissionError("injected transient sharing denial")
            real_replace(source, destination)

        evidence_publication.os.replace = transient_replace
        try:
            evidence_publication._durable_write(retry_target, b"durable\n")
        finally:
            evidence_publication.os.replace = real_replace
        assert replace_attempts == 3
        assert retry_target.read_bytes() == b"durable\n"

        persistent_target = root / "persistent-replace" / "journal.json"
        persistent_attempts = 0
        real_sleep = evidence_publication.time.sleep

        def persistent_denial(source: Path, destination: Path) -> None:
            nonlocal persistent_attempts
            persistent_attempts += 1
            raise PermissionError("injected persistent sharing denial")

        evidence_publication.os.replace = persistent_denial
        evidence_publication.time.sleep = lambda _delay: None
        try:
            try:
                evidence_publication._durable_write(
                    persistent_target, b"must-not-publish\n"
                )
            except PermissionError:
                pass
            else:
                raise AssertionError("persistent replacement denial was ignored")
        finally:
            evidence_publication.os.replace = real_replace
            evidence_publication.time.sleep = real_sleep
        assert persistent_attempts == 8
        assert not persistent_target.exists()

        activation = build_activation_fixture(root / "future-control")
        future_extract = json.loads(
            activation.extract_receipt.read_text(encoding="utf-8")
        )

        tool_value = shutil.which("pdftotext")
        assert tool_value is not None, "C2 fixture host requires pinned pdftotext"
        tool = Path(tool_value)
        pinned = future_extract["extraction"]["executable"]
        assert tool.name.casefold() == pinned["name"].casefold()
        assert sha(tool) == pinned["sha256"]
        assert tool.stat().st_size == pinned["size"]
        version = subprocess.run(
            [str(tool), "-v"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert pinned["version"] in version.stderr + version.stdout

        generated_root = activation.root / "generated"
        generated_text = generated_root / "normalized.txt"
        generated_receipt = generated_root / "receipt.json"
        generated_raw = generated_root / "raw.txt"
        generated_map = generated_root / "page-map.json"
        generated_manifest = generated_root / "publication-manifest.json"
        generated_marker = generated_root / "publication-marker.json"
        future = run_future_extract(
            activation.root / "miniature.pdf",
            project_root=activation.root,
            project_manifest=activation.project_manifest,
            text_out=generated_text,
            receipt_out=generated_receipt,
            raw_out=generated_raw,
            page_map_out=generated_map,
            page_map_seed=ASSET_ROOT / "expected_page_span_map.json",
            manifest_out=generated_manifest,
            marker_out=generated_marker,
        )
        assert future.returncode == 0, future.stdout + future.stderr
        EXTRACT_VALIDATOR.validate(json.loads(
            generated_receipt.read_text(encoding="utf-8")
        ))
        extract_manifest = json.loads(generated_manifest.read_text(encoding="utf-8"))
        extract_marker = json.loads(generated_marker.read_text(encoding="utf-8"))
        assert extract_marker["state"] == "committed"
        assert (
            extract_marker["final_output_hashes"]
            == extract_manifest["intended_outputs"]
        )
        assert generated_marker.stat().st_mtime_ns >= max(
            generated_receipt.stat().st_mtime_ns,
            generated_manifest.stat().st_mtime_ns,
            generated_raw.stat().st_mtime_ns,
            generated_text.stat().st_mtime_ns,
            generated_map.stat().st_mtime_ns,
        )
        validated = validate_extract_receipt(
            generated_receipt,
            project_root=activation.root,
            wiki_root=activation.wiki_root,
        )
        assert validated["value"]["schema_version"] == "2.0.0"
        assert generated_text.read_bytes() == (
            ASSET_ROOT / "expected_utf8_lf_v1.txt"
        ).read_bytes()
        transaction_id = validated["value"]["publication"]["transaction_id"]
        transaction_lane = (
            activation.root / ".harness-evidence-transactions" / transaction_id
        )
        generated_marker.unlink()
        journal_path = transaction_lane / "journal.json"
        claim_path = transaction_lane / "claim.json"
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
        claim = json.loads(claim_path.read_text(encoding="utf-8"))
        journal["state"] = "publishing"
        claim["state"] = "active"
        for path, value in ((journal_path, journal), (claim_path, claim)):
            path.write_text(
                json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="utf-8",
                newline="\n",
            )
        assert recover_committed(
            project_root=activation.root,
            transaction_id=transaction_id,
            acknowledgement="inspected-evidence-state-and-journal",
        ) == "committed"
        assert generated_marker.is_file()
        assert list((transaction_lane / "recovery").glob("*.json"))
        validate_extract_receipt(
            generated_receipt,
            project_root=activation.root,
            wiki_root=activation.wiki_root,
        )
        marker_bytes_before = generated_marker.read_bytes()
        marker_mtime_before = generated_marker.stat().st_mtime_ns
        idempotent = run_future_extract(
            activation.root / "miniature.pdf",
            project_root=activation.root,
            project_manifest=activation.project_manifest,
            text_out=generated_text,
            receipt_out=generated_receipt,
            raw_out=generated_raw,
            page_map_out=generated_map,
            page_map_seed=ASSET_ROOT / "expected_page_span_map.json",
            manifest_out=generated_manifest,
            marker_out=generated_marker,
        )
        assert idempotent.returncode == 0, idempotent.stdout + idempotent.stderr
        assert generated_marker.read_bytes() == marker_bytes_before
        assert generated_marker.stat().st_mtime_ns == marker_mtime_before

        stale_seed = root / "stale-page-map.json"
        stale_value = json.loads(
            (ASSET_ROOT / "expected_page_span_map.json").read_text(
                encoding="utf-8"
            )
        )
        stale_value["normalized_sha256"] = "0" * 64
        stale_seed.write_text(
            json.dumps(stale_value, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        atomic_root = activation.root / "atomic-refusal"
        atomic_paths = {
            "text": atomic_root / "normalized.txt",
            "receipt": atomic_root / "receipt.json",
            "raw": atomic_root / "raw.txt",
            "map": atomic_root / "page-map.json",
            "manifest": atomic_root / "publication-manifest.json",
            "marker": atomic_root / "publication-marker.json",
        }
        atomic_root.mkdir(parents=True, exist_ok=True)
        for key, path in atomic_paths.items():
            path.write_bytes(f"sentinel-{key}\n".encode("utf-8"))
        before_atomic = tree_state(activation.root)
        refused_atomic = run_future_extract(
            activation.root / "miniature.pdf",
            project_root=activation.root,
            project_manifest=activation.project_manifest,
            text_out=atomic_paths["text"],
            receipt_out=atomic_paths["receipt"],
            raw_out=atomic_paths["raw"],
            page_map_out=atomic_paths["map"],
            page_map_seed=stale_seed,
            manifest_out=atomic_paths["manifest"],
            marker_out=atomic_paths["marker"],
        )
        assert refused_atomic.returncode == 4
        atomic_blocker = json.loads(refused_atomic.stderr)
        BLOCKER_VALIDATOR.validate(atomic_blocker)
        assert atomic_blocker["reason_code"] == "EXTRACT-LOCATOR-MISMATCH"
        assert tree_state(activation.root) == before_atomic
        for key, path in atomic_paths.items():
            assert path.read_bytes() == f"sentinel-{key}\n".encode("utf-8")

        precondition_output = activation.root / "precondition-output.txt"
        precondition_marker = activation.root / "precondition-marker.json"
        precondition_output.write_bytes(b"prior-output\n")
        try:
            publish_committed(
                project_root=activation.root,
                transaction_id="precondition-refusal",
                preconditions=[(activation.root / "miniature.pdf", "0" * 64)],
                inventory_preconditions=[],
                outputs=[(precondition_output, b"new-output\n")],
                marker=(precondition_marker, b"marker\n"),
            )
        except EvidencePublicationError as exc:
            assert "dependency changed under claim" in str(exc)
        else:
            raise AssertionError("under-claim dependency drift was accepted")
        assert precondition_output.read_bytes() == b"prior-output\n"
        assert not precondition_marker.exists()
        refused_lane = (
            activation.root
            / ".harness-evidence-transactions"
            / "precondition-refusal"
        )
        assert not (refused_lane / "claim.json").exists()
        assert not (refused_lane / "journal.json").exists()

        for transaction_id, marker_bytes in (
            ("foreign-marker-refusal", b"foreign-marker\n"),
            ("prefix-marker-refusal", b"intended-marker\n"),
        ):
            prefix_output = activation.root / f"{transaction_id}-output.txt"
            prefix_marker = activation.root / f"{transaction_id}-marker.json"
            prefix_output.write_bytes(b"prior-output\n")
            prefix_marker.write_bytes(marker_bytes)
            intended_marker = b"intended-marker\n"
            try:
                publish_committed(
                    project_root=activation.root,
                    transaction_id=transaction_id,
                    preconditions=[(
                        activation.root / "miniature.pdf",
                        sha(activation.root / "miniature.pdf"),
                    )],
                    inventory_preconditions=[],
                    outputs=[(prefix_output, b"intended-output\n")],
                    marker=(prefix_marker, intended_marker),
                )
            except EvidencePublicationError as exc:
                assert (
                    "commit marker conflicts" in str(exc)
                    or "non-matching output prefix" in str(exc)
                )
            else:
                raise AssertionError("visible marker admitted a changed output prefix")
            assert prefix_output.read_bytes() == b"prior-output\n"
            assert prefix_marker.read_bytes() == marker_bytes

        benign_text = root / "benign" / "extract.txt"
        benign_receipt = root / "benign" / "receipt.json"
        benign = run_extract(
            ASSET_ROOT / "miniature.pdf", benign_text, benign_receipt
        )
        assert benign.returncode == 0, benign.stdout + benign.stderr
        assert benign_text.read_bytes() == (
            ASSET_ROOT / "expected_pdftotext_raw.txt"
        ).read_bytes()

        attack_text = root / "unavailable" / "extract.txt"
        attack_receipt = root / "unavailable" / "receipt.json"
        before = tree_state(root)
        unavailable_env = dict(os.environ)
        unavailable_env["PATH"] = ""
        unavailable = run_future_extract(
            activation.root / "miniature.pdf",
            project_root=activation.root,
            project_manifest=activation.project_manifest,
            text_out=attack_text,
            receipt_out=attack_receipt,
            raw_out=root / "unavailable" / "raw.txt",
            page_map_out=root / "unavailable" / "page-map.json",
            manifest_out=root / "unavailable" / "publication-manifest.json",
            marker_out=root / "unavailable" / "publication-marker.json",
            env=unavailable_env,
        )
        after = tree_state(root)
        if unavailable.stderr.strip():
            BLOCKER_VALIDATOR.validate(json.loads(unavailable.stderr))
        if unavailable.returncode != 4 or "EXTRACTOR-UNAVAILABLE" not in unavailable.stderr:
            failures.append(
                "extractor unavailable: expected rc=4/EXTRACTOR-UNAVAILABLE, "
                f"actual rc={unavailable.returncode} stderr={unavailable.stderr.strip()!r}"
            )
        if after != before:
            failures.append(
                "extractor unavailable: refusal changed filesystem state"
            )

    if failures:
        raise AssertionError(
            "C2 intended-red source-extract regressions:\n- "
            + "\n- ".join(failures)
        )
    print("source_extract_smoketest: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
