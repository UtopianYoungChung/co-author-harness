#!/usr/bin/env python3
"""staging_run - governed staging-run lifecycle for the producer boundary.

Phase D of the producer-boundary plan. A staging run is the only place the
harness may produce for a governed consumer: it lives under the routing-
installed lane `<governed-root>/outputs/co-author-harness/staging/<work-id>/
<run-id>/` with the layout

    inputs/     immutable allowlisted snapshots (bytes + recorded path + hash)
    work/       mutable candidate artifacts
    state/      proposal-only production ledger
    evidence/   checks and reviews
    shipment/   immutable manifest and receipt echo, written exactly once

Everything a run emits is `effect_scope: proposal_only`
(references/schemas/shipment_manifest.schema.json). Application happens on
the CONSUMER's side under its own governance
(research/10_Governance/HARNESS_SHIPMENT_BOUNDARY.md); until
recognize_application_receipt() records the consumer's receipt, is_applied()
is False and nothing here may be treated as applied, accepted, or promoted.

Validation is handwritten against the schema contract (the package avoids a
jsonschema dependency; keep validate_manifest() aligned with the schema file).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import stat
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from destination_capability import (  # noqa: F401  (DestinationRefused re-exported for callers)
    DestinationRefused, assert_writable, discovered_workspace_root,
)

HARNESS = Path(__file__).resolve().parent.parent
_STAGING_REL = Path("outputs") / "co-author-harness" / "staging"
_ID_RE = re.compile(r"^(run|shp)-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_RUN_DIRS = ("inputs", "work", "state", "evidence", "shipment")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _fresh_id(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}-{stamp}-{secrets.token_hex(4)}"


def default_staging_root() -> Path:
    """The discovered governed root's staging lane; fail closed without one."""
    root = discovered_workspace_root()
    if root is None:
        raise DestinationRefused(
            "DEST-UNGOVERNED",
            "no workspace routing manifest was discovered, so no staging lane "
            "exists to create a run in. Failing closed.")
    return root / _STAGING_REL


def create_run(work_id: str, staging_root: Path | None = None) -> Path:
    """Create `<staging_root>/<work_id>/<run-id>/` with the five-dir layout.

    The destination must classify as `staging` -- create_run refuses to root a
    run anywhere else (route != write-enable applies to us too). Run ids are
    collision-resistant (UTC stamp + 8 hex of CSPRNG) and creation is
    exclusive: an id collision raises rather than reusing a directory.
    """
    if not work_id or "/" in work_id or "\\" in work_id:
        raise ValueError(f"work_id must be a single path segment: {work_id!r}")
    base = Path(staging_root) if staging_root is not None else default_staging_root()
    run_dir = base / work_id / _fresh_id("run")
    kind = assert_writable(run_dir, purpose="staging-run creation")
    if kind != "staging":
        raise DestinationRefused(
            "DEST-PROTECTED",
            f"staging-run root {run_dir} classifies as {kind!r}, not "
            "'staging'; runs may live only in the governed staging lane.")
    run_dir.parent.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=False, exist_ok=False)
    for name in _RUN_DIRS:
        (run_dir / name).mkdir()
    return run_dir


def snapshot_input(run_dir: Path, source: Path) -> dict:
    """Copy an allowlisted input into `inputs/` as an immutable snapshot.

    Records the exact source path and SHA-256, verifies the copied bytes, and
    marks the snapshot read-only so a later source mutation can never leak in.
    Read-allowlist enforcement is the caller's duty (the active work package);
    this function makes the provenance honest, not the read authorized.
    """
    run_dir = Path(run_dir)
    source = Path(source)
    if _manifest_path(run_dir).exists():
        raise FileExistsError("shipment already emitted; inputs are sealed")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    snap_name = f"{len(list((run_dir / 'inputs').glob('*'))):04d}_{source.name}"
    snap = run_dir / "inputs" / snap_name
    shutil.copyfile(source, snap)
    if sha256_file(snap) != digest:
        snap.unlink()
        raise OSError(f"snapshot read-back mismatch for {source}")
    snap.chmod(stat.S_IREAD)
    entry = {
        "source_path": str(source),
        "snapshot_path": f"inputs/{snap_name}",
        "sha256": digest,
    }
    ledger = run_dir / "state" / "input_snapshots.json"
    rows = json.loads(ledger.read_text(encoding="utf-8")) if ledger.exists() else []
    rows.append(entry)
    ledger.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    return entry


def _manifest_path(run_dir: Path) -> Path:
    return Path(run_dir) / "shipment" / "MANIFEST.json"


def _harness_commit() -> str:
    r = subprocess.run(["git", "-C", str(HARNESS), "rev-parse", "--short", "HEAD"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout.strip() if r.returncode == 0 else "unknown"


def _artifact_inventory(run_dir: Path) -> list[dict]:
    rows = []
    for top in ("work", "state", "evidence"):
        base = run_dir / top
        for path in sorted(p for p in base.rglob("*") if p.is_file()):
            rel = path.relative_to(run_dir).as_posix()
            rows.append({"path": rel, "sha256": sha256_file(path)})
    return rows


def emit_shipment(run_dir: Path, *, proposed_operations: list[dict],
                  limitations: list[str], unresolved_findings: list[str]) -> Path:
    """Write the immutable manifest exactly once, byte-verified.

    Each proposed operation names a run-relative `artifact`; its hash is
    computed here so the manifest is self-consistent by construction. The
    manifest file is created exclusively (`x` mode): a second emission raises
    FileExistsError instead of silently superseding evidence.
    """
    run_dir = Path(run_dir)
    inputs_ledger = run_dir / "state" / "input_snapshots.json"
    inputs = (json.loads(inputs_ledger.read_text(encoding="utf-8"))
              if inputs_ledger.exists() else [])
    ops = []
    for op in proposed_operations:
        artifact = run_dir / op["artifact"]
        ops.append({**op, "sha256": sha256_file(artifact)})
    doc = {
        "schema_version": "1.0.0",
        "shipment_id": _fresh_id("shp"),
        "run_id": run_dir.name,
        "work_id": run_dir.parent.name,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "producer": {"name": "co-author-harness", "harness_commit": _harness_commit()},
        "effect_scope": "proposal_only",
        "inputs": inputs,
        "proposed_operations": ops,
        "artifacts": _artifact_inventory(run_dir),
        "limitations": list(limitations),
        "unresolved_findings": list(unresolved_findings),
    }
    problems = validate_manifest(doc)
    if problems:
        raise ValueError(f"refusing to emit an invalid manifest: {problems[:3]}")
    payload = (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8")
    target = _manifest_path(run_dir)
    with open(target, "xb") as f:
        f.write(payload)
        f.flush()
        os.fsync(f.fileno())
    if target.read_bytes() != payload:
        raise OSError("manifest read-back mismatch; shipment VOID")
    return target


def validate_manifest(doc: dict) -> list[str]:
    """Structural validation mirroring shipment_manifest.schema.json."""
    problems: list[str] = []

    def need(key: str, ok: bool, why: str) -> None:
        if not ok:
            problems.append(f"{key}: {why}")

    need("schema_version", doc.get("schema_version") == "1.0.0", "must be 1.0.0")
    need("shipment_id", bool(_ID_RE.match(str(doc.get("shipment_id", "")))), "bad id")
    need("run_id", bool(_ID_RE.match(str(doc.get("run_id", "")))), "bad id")
    need("work_id", bool(str(doc.get("work_id", ""))), "required")
    need("created_at", len(str(doc.get("created_at", ""))) >= 20, "required")
    producer = doc.get("producer") or {}
    need("producer.name", producer.get("name") == "co-author-harness", "wrong producer")
    need("producer.harness_commit",
         len(str(producer.get("harness_commit", ""))) >= 7, "required")
    need("effect_scope", doc.get("effect_scope") == "proposal_only",
         "a shipment is a proposal, not authority")
    for i, row in enumerate(doc.get("inputs", [])):
        need(f"inputs[{i}]",
             bool(_SHA_RE.match(str(row.get("sha256", ""))))
             and str(row.get("snapshot_path", "")).startswith("inputs/")
             and bool(row.get("source_path")),
             "needs source_path, inputs/ snapshot_path, sha256")
    for i, row in enumerate(doc.get("proposed_operations", [])):
        need(f"proposed_operations[{i}]",
             row.get("op") in ("create", "modify")
             and bool(row.get("destination"))
             and str(row.get("artifact", "")).split("/", 1)[0] in ("work", "state", "evidence")
             and bool(_SHA_RE.match(str(row.get("sha256", "")))),
             "needs op, destination, run-relative artifact, sha256")
    for i, row in enumerate(doc.get("artifacts", [])):
        need(f"artifacts[{i}]",
             str(row.get("path", "")).split("/", 1)[0] in ("work", "state", "evidence")
             and bool(_SHA_RE.match(str(row.get("sha256", "")))),
             "needs run-relative path and sha256")
    for key in ("limitations", "unresolved_findings"):
        need(key, isinstance(doc.get(key), list), "required list")
    return problems


def verify_shipment(run_dir: Path) -> list[str]:
    """Re-hash every manifest-listed artifact; report mismatches."""
    run_dir = Path(run_dir)
    doc = json.loads(_manifest_path(run_dir).read_text(encoding="utf-8"))
    problems = validate_manifest(doc)
    for row in doc.get("artifacts", []):
        path = run_dir / row["path"]
        if not path.is_file():
            problems.append(f"{row['path']}: missing")
        elif sha256_file(path) != row["sha256"]:
            problems.append(f"{row['path']}: bytes diverge from the emitted manifest")
    return problems


def is_applied(run_dir: Path) -> bool:
    """True only when a consumer application receipt has been recognized."""
    return (Path(run_dir) / "shipment" / "APPLICATION_RECEIPT.json").is_file()


def recognize_application_receipt(run_dir: Path, receipt: Path) -> Path:
    """Echo the CONSUMER-written application receipt into the run.

    The receipt is produced by the consumer's governance after explicit user
    acceptance; the harness only records that it saw it. A missing receipt is
    an error, never a silent 'assume applied'.
    """
    receipt = Path(receipt)
    if not receipt.is_file():
        raise FileNotFoundError(f"application receipt not found: {receipt}")
    echo = {
        "receipt_path": str(receipt),
        "receipt_sha256": sha256_file(receipt),
        "recognized_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    target = Path(run_dir) / "shipment" / "APPLICATION_RECEIPT.json"
    payload = (json.dumps(echo, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with open(target, "xb") as f:
        f.write(payload)
        f.flush()
        os.fsync(f.fileno())
    return target
