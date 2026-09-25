#!/usr/bin/env python3
"""Render the disposable lifecycle view from the unified phase-state ledger."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from milestone_framework_validate import validate_document
from milestone_handoff_policy import resolve_handoff_policy
from phase_state_validate import _validate_doc as validate_phase_document


MILESTONES = ("M1", "M2", "M3", "M4", "M5")
SOURCE_RELATIVE = "reviews/phase_state.json"
VIEW_RELATIVE = "reviews/lifecycle_state.md"
DERIVED_FROM = SOURCE_RELATIVE
UTC_SHAPE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z$")
REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


class RenderError(ValueError):
    """A controlled lifecycle rendering failure."""

    def __init__(self, message: str, *, code: str = "MF-DERIVED", exit_code: int = 4) -> None:
        super().__init__(message)
        self.code = code
        self.exit_code = exit_code


def _valid_timestamp(value: str) -> bool:
    if UTC_SHAPE.fullmatch(value) is None:
        return False
    try:
        parsed = dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() == dt.timedelta(0)


def _is_reparse(path: Path) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    return path.is_symlink() or bool(getattr(info, "st_file_attributes", 0) & REPARSE_POINT)


def _safe_root(project_root: Path) -> Path:
    requested = project_root.expanduser().absolute()
    if not requested.is_dir() or _is_reparse(requested):
        raise RenderError("project root must be an existing non-reparse directory", exit_code=2)
    return requested.resolve()


def _contained(project_root: Path, relative: str, *, may_be_missing: bool = False) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise RenderError(f"path escapes project root: {relative}")
    candidate = project_root.joinpath(rel)
    cursor = project_root
    for part in rel.parts:
        cursor = cursor / part
        if cursor.exists() or cursor.is_symlink():
            if _is_reparse(cursor):
                raise RenderError(f"symlink or junction is forbidden on lifecycle path: {relative}")
        elif cursor != candidate or not may_be_missing:
            raise RenderError(f"required lifecycle path is missing: {relative}")
    anchor = candidate if candidate.exists() else candidate.parent
    try:
        anchor.resolve().relative_to(project_root)
    except (OSError, ValueError) as exc:
        raise RenderError(f"path escapes project root: {relative}") from exc
    return candidate


def _load_source(project_root: Path) -> tuple[bytes, dict[str, Any]]:
    source = _contained(project_root, SOURCE_RELATIVE)
    if not source.is_file():
        raise RenderError(f"authoritative ledger is not a regular file: {SOURCE_RELATIVE}")
    try:
        payload = source.read_bytes()
        text = payload.decode("utf-8", errors="strict")
        document = json.loads(text)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RenderError(f"could not read authoritative ledger as UTF-8 JSON: {exc}") from exc
    if not isinstance(document, dict):
        raise RenderError("authoritative ledger must be a JSON object")
    phase_findings: list[Any] = []
    validate_phase_document(document, phase_findings)
    if phase_findings:
        details = "; ".join(f"{item.code} @ {item.path}" for item in phase_findings[:8])
        raise RenderError(f"authoritative ledger failed canonical phase validation: {details}")
    result = validate_document(project_root, document)
    if not result.exit_permitted:
        details = "; ".join(f"{item.code} @ {item.path}" for item in result.findings[:8])
        raise RenderError(f"authoritative ledger failed canonical validation: {details}")
    return payload, document


def _accepted_packets(project_root: Path, framework: dict[str, Any]) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    milestones = framework["milestones"]
    for name in MILESTONES:
        record = milestones[name]
        approval = record.get("approval")
        handoff = record.get("handoff")
        if not (
            record.get("status") == "accepted"
            and record.get("dependency_state") == "current"
            and isinstance(approval, dict)
            and approval.get("status") == "approved"
            and isinstance(handoff, dict)
            and handoff.get("status") in {"ready", "consumed"}
        ):
            continue
        relative = handoff["packet_path"]
        packet_path = _contained(project_root, relative)
        try:
            packet_payload = packet_path.read_bytes()
            packet = json.loads(packet_payload.decode("utf-8", errors="strict"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise RenderError(f"could not read ledger-bound F9 packet {relative}: {exc}") from exc
        actual_hash = hashlib.sha256(packet_payload).hexdigest()
        if actual_hash != handoff["packet_sha256"]:
            raise RenderError(f"ledger-bound F9 packet changed after source validation: {relative}")
        packets.append({
            "milestone": name,
            "path": relative,
            "sha256": actual_hash,
            "to": packet.get("to_milestone"),
            "open_debts": len(packet.get("open_debts", [])),
        })
    return packets


def _cell(value: Any) -> str:
    """Render one untrusted ledger value as a single Markdown table cell."""
    return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def _feedback_state(record: dict[str, Any]) -> str:
    records = record.get("feedback_records", [])
    if not records:
        return "none"
    counts: dict[str, int] = {}
    for item in records:
        disposition = item.get("disposition", "unknown")
        counts[disposition] = counts.get(disposition, 0) + 1
    summary = ", ".join(f"{key}:{counts[key]}" for key in sorted(counts))
    return f"{len(records)} ({summary})"


def render_bytes(project_root: Path, generated_at: str) -> bytes:
    """Return the exact disposable view without writing any project file."""
    if not _valid_timestamp(generated_at):
        raise RenderError("generated-at must be a real strict ISO-8601 UTC timestamp ending in Z", exit_code=2)
    source_payload, document = _load_source(project_root)
    framework = document["milestone_framework"]
    handoff_policy = resolve_handoff_policy(framework)
    declared_handoff_policy = handoff_policy["declared_policy"] or "implicit"
    handoff_resolution = (
        "implicit audited (1.0.0 compatibility)"
        if handoff_policy["contract_version"] == "1.0.0"
        else f"explicit {handoff_policy['effective_policy']}"
    )
    packets = _accepted_packets(project_root, framework)
    sections = document.get("sections", {})
    source_hash = hashlib.sha256(source_payload).hexdigest()
    lines = [
        "---",
        "generated: true",
        f"derived_from: {DERIVED_FROM}",
        f"source_sha256: {source_hash}",
        f"generated_at: {generated_at}",
        "---",
        "",
        "DO NOT EDIT: generated lifecycle view",
        "",
        "# Lifecycle State",
        "",
        "> Disposable view. Edit `reviews/phase_state.json` through the Planner; do not edit this file.",
        "",
        f"- Contract: `{framework['contract_version']}`",
        f"- Declared handoff policy: `{declared_handoff_policy}`",
        f"- Effective handoff policy: `{handoff_policy['effective_policy']}`",
        f"- Handoff policy resolution: `{handoff_resolution}`",
        f"- Mode: `{framework['mode']}`",
        f"- Primary lineage: `{framework['primary_lineage']}`",
        "",
        "## Milestones",
        "",
        "| Milestone | Purpose | Status | Feedback | Applicability | Dependency | Approval | Handoff |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for name in MILESTONES:
        record = framework["milestones"][name]
        lines.append(
            f"| {name} | {_cell(record['purpose'])} | {record['status']} | {_feedback_state(record)} | {record['applicability']} | "
            f"{record['dependency_state']} | {record['approval']['status']} | {record['handoff']['status']} |"
        )
    lines.extend([
        "",
        "## Phase state",
        "",
        "| Section | Current phase | Last approved phase |",
        "|---|---|---|",
    ])
    for section_name in sorted(sections):
        section = sections[section_name]
        lines.append(
            f"| `{section_name}` | {section.get('current_phase', 'unknown')} | "
            f"{section.get('last_approved_phase') or 'none'} |"
        )
    lines.extend(["", "## Accepted current handoffs", ""])
    if packets:
        lines.extend([
            "| From | To | Packet | SHA-256 | Open debts |",
            "|---|---|---|---|---|",
        ])
        for packet in packets:
            lines.append(
                f"| {packet['milestone']} | {packet['to'] or 'terminal'} | `{packet['path']}` | "
                f"`{packet['sha256']}` | {packet['open_debts']} |"
            )
    else:
        lines.append("No accepted, current, ledger-bound F9 packet is active.")
    lines.append("")
    return "\n".join(lines).encode("utf-8")


def _publish(project_root: Path, payload: bytes) -> None:
    reviews = _contained(project_root, "reviews")
    target = _contained(project_root, VIEW_RELATIVE, may_be_missing=True)
    if target.exists() and (not target.is_file() or _is_reparse(target)):
        raise RenderError(f"derived view target is not a regular non-reparse file: {VIEW_RELATIVE}")
    descriptor, temp_name = tempfile.mkstemp(prefix=".lifecycle_state.", suffix=".tmp", dir=reviews)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        match = re.search(rb"(?m)^source_sha256: ([0-9a-f]{64})$", payload)
        if match is None:
            raise RenderError("rendered lifecycle payload lacks its source binding")
        source = _contained(project_root, SOURCE_RELATIVE)
        if hashlib.sha256(source.read_bytes()).hexdigest() != match.group(1).decode("ascii"):
            raise RenderError("authoritative ledger changed during lifecycle rendering")
        time_match = re.search(rb"(?m)^generated_at: ([^\r\n]+)$", payload)
        if time_match is None:
            raise RenderError("rendered lifecycle payload lacks its generation-time binding")
        regenerated = render_bytes(project_root, time_match.group(1).decode("utf-8", errors="strict"))
        if regenerated != payload:
            raise RenderError("lifecycle evidence changed during rendering")
        if target.exists() and _is_reparse(target):
            raise RenderError(f"derived view target became a reparse point: {VIEW_RELATIVE}")
        os.replace(temp_path, target)
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument(
        "--generated-at",
        default=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    )
    parser.add_argument("--check", action="store_true", help="Detect missing or stale output without writing.")
    args = parser.parse_args(argv)
    if not args.check:
        # --check only reads and compares, so it needs no write capability.
        from destination_capability import DestinationRefused, guard_project_root
        try:
            guard_project_root(args.project_root)
        except DestinationRefused as exc:
            print(f"[BLOCKER] {exc}")
            return 4
    try:
        project_root = _safe_root(args.project_root)
        expected = render_bytes(project_root, args.generated_at)
        if args.check:
            target = _contained(project_root, VIEW_RELATIVE, may_be_missing=True)
            try:
                actual = target.read_bytes() if target.is_file() and not _is_reparse(target) else None
            except OSError:
                actual = None
            if actual != expected:
                raise RenderError(f"{VIEW_RELATIVE} is missing, stale, or manually edited")
            print(f"PASS {VIEW_RELATIVE} is current")
            return 0
        _publish(project_root, expected)
        print(f"RENDERED {VIEW_RELATIVE}")
        return 0
    except RenderError as exc:
        stream = sys.stderr if exc.exit_code == 2 else sys.stdout
        stream.write(f"[MAJOR] {exc.code} @ {VIEW_RELATIVE}: {exc}\n")
        return exc.exit_code
    except OSError as exc:
        sys.stdout.write(f"[MAJOR] MF-DERIVED @ {VIEW_RELATIVE}: filesystem error: {exc}\n")
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
