#!/usr/bin/env python3
"""output_lane - the single write-root rule for harness-authored package files.

Under Master Governance 1.0.15 (1.11b / Annex D; FINDING-20260929-001) the
harness is a registered agent platform. In a governed Workbench package
(``<governed-root>/research/60_Workbench/<work-id>/``) its writable footprint is
only the shipment lane ``reviews/harness/shipments/<shipment-id>/``, the tool
control plane ``reviews/.harness/``, the re-pin files, and staging. Every other
package path is protected (see ``destination_capability``).

Rule (defined once here; prose lives in ``references/_snippets/write-root.md``):

  write root = ``<project>/reviews/harness/shipments/<shipment-id>`` when the
               project root is exactly a governed Workbench work-id root;
               ``<project>`` everywhere else (non-governed projects unchanged).

A project-relative path a role or script writes (``reviews/revision_plan.md``,
``research_notes/lessons_learned.md`` ...) is written relative to the write
root. Reads of harness-authored files follow the same rule. A governed package
with no resolvable shipment id fails closed.

Shipment id resolution (governed package only), first hit wins:
  1. an explicit argument (``--shipment-id`` / ``shipment_id=``);
  2. environment ``COAUTHOR_SHIPMENT_ID``;
  3. the active-shipment pointer ``reviews/.harness/active_shipment.json`` at
     the package root (``{"schema": "active-shipment.v1", "shipment_id": ...,
     "set_at": ...}``), written by ``set-active`` at run start. Hooks and
     scripts that never see a Planner argument resolve through it.
An explicit argument or environment value that disagrees with the pointer wins
(explicit beats recorded). A malformed pointer is an error, never ignored.

Never redirected (``is_never_redirected``): ``reviews/phase_state.json``
(lifecycle state, written only by its canonical transaction), anything under
``reviews/.harness/`` (tool control plane) and the re-pin files
(``reviews/repin_rebind_request.json`` / ``.<epoch>.applied.json`` /
``.stale.json``).

CLI:
  ``python scripts/output_lane.py <project_root> [--shipment-id ID]`` prints the
  write root.
  ``python scripts/output_lane.py set-active --project-root P --shipment-id ID``
  records the active shipment (governed roots only) and creates the lane.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))

import destination_capability as _dc  # noqa: E402

SHIPMENT_ID_ENV = "COAUTHOR_SHIPMENT_ID"
ACTIVE_SHIPMENT_REL = "reviews/.harness/active_shipment.json"
ACTIVE_SHIPMENT_SCHEMA = "active-shipment.v1"
_SEGMENT_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
_WINDOWS_RESERVED = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{n}" for n in range(10)}
    | {f"LPT{n}" for n in range(10)}
)
_LANE_REL = ("reviews", "harness", "shipments")
_REPIN_REQUEST = "repin_rebind_request.json"
_REPIN_PREFIX = "repin_rebind_request."


class OutputLaneError(RuntimeError):
    """The write root cannot be resolved. Fail closed."""


def is_governed_workbench_root(project_root: os.PathLike | str) -> bool:
    """True only when project_root is exactly a governed Workbench work-id root."""
    dest = _dc._canon(project_root)
    return any(
        _dc._is_workbench_work_id_root(dest, root)
        for root in _dc._governing(_dc.governed_roots(project_root))
    )


def validate_shipment_id(shipment_id: str) -> str:
    """Return shipment_id if it is a single safe path segment, else raise."""
    if (
        not isinstance(shipment_id, str)
        or not _SEGMENT_RE.fullmatch(shipment_id)
        or shipment_id in {".", ".."}
        or ".." in shipment_id
        or shipment_id.endswith((".", " "))
    ):
        raise OutputLaneError(
            f"invalid shipment id {shipment_id!r}: must be one path segment "
            "of letters, digits, '.', '_' or '-' (no separators, no '..', "
            "no trailing '.' or space)"
        )
    if shipment_id.split(".", 1)[0].upper() in _WINDOWS_RESERVED:
        raise OutputLaneError(
            f"invalid shipment id {shipment_id!r}: Windows reserved device name"
        )
    return shipment_id


def read_active_shipment(project_root: os.PathLike | str) -> str | None:
    """The shipment id recorded in the active-shipment pointer, or None when
    no pointer file exists. A present but malformed pointer raises."""
    path = Path(project_root) / Path(ACTIVE_SHIPMENT_REL)
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise OutputLaneError(f"active-shipment pointer {path} unreadable: {exc}") from exc
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise OutputLaneError(f"active-shipment pointer {path} is not valid JSON: {exc}") from exc
    if (
        not isinstance(data, dict)
        or data.get("schema") != ACTIVE_SHIPMENT_SCHEMA
        or not isinstance(data.get("shipment_id"), str)
    ):
        raise OutputLaneError(
            f"active-shipment pointer {path} is malformed: expected schema "
            f"{ACTIVE_SHIPMENT_SCHEMA!r} and a string shipment_id"
        )
    return validate_shipment_id(data["shipment_id"])


def _lane_escapes_package(root: Path, lane: Path) -> bool:
    """True when the lane, or its nearest existing ancestor, resolves through a
    link to a place outside the package."""
    probe = lane
    while not os.path.lexists(probe) and probe != probe.parent:
        probe = probe.parent
    real_root = os.path.normcase(os.path.realpath(root))
    real_probe = os.path.normcase(os.path.realpath(probe))
    try:
        return os.path.commonpath([real_root, real_probe]) != real_root
    except ValueError:
        return True


def resolve_write_root(
    project_root: os.PathLike | str, shipment_id: str | None = None
) -> Path:
    """The directory harness-authored package files are written under."""
    root = Path(project_root)
    if not is_governed_workbench_root(root):
        return root
    sid = (shipment_id or os.environ.get(SHIPMENT_ID_ENV) or "").strip()
    if not sid:
        sid = read_active_shipment(root) or ""
    if not sid:
        raise OutputLaneError(
            "governed Workbench package: name the active shipment id "
            f"(--shipment-id, {SHIPMENT_ID_ENV}, or run `output_lane.py "
            "set-active` to record it)"
        )
    lane = root.joinpath(*_LANE_REL, validate_shipment_id(sid))
    if not root.is_dir():
        raise OutputLaneError(f"governed package does not exist: {root}")
    if _lane_escapes_package(root, lane):
        raise OutputLaneError(f"shipment lane resolves outside the package: {lane}")
    return lane


def set_active_shipment(project_root: os.PathLike | str, shipment_id: str) -> Path:
    """Record the active shipment for a governed package and create its lane.

    Returns the pointer path. Refuses a non-governed root and any destination
    the destination guard does not accept."""
    root = Path(project_root)
    if not is_governed_workbench_root(root):
        raise OutputLaneError(
            f"{root} is not a governed Workbench work-id root; "
            "set-active applies to governed packages only"
        )
    sid = validate_shipment_id(shipment_id.strip() if isinstance(shipment_id, str) else shipment_id)
    pointer = root / Path(ACTIVE_SHIPMENT_REL)
    lane = root.joinpath(*_LANE_REL, sid)
    try:
        _dc.assert_writable(pointer, purpose="active-shipment pointer")
        _dc.assert_writable(lane, purpose="shipment lane")
    except _dc.DestinationRefused as exc:
        raise OutputLaneError(str(exc)) from exc
    lane.mkdir(parents=True, exist_ok=True)
    pointer.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": ACTIVE_SHIPMENT_SCHEMA,
        "shipment_id": sid,
        "set_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    tmp = pointer.with_name(f"{pointer.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, pointer)
    return pointer


def is_never_redirected(rel: os.PathLike | str) -> bool:
    """True for project-relative paths that stay at the package path."""
    parts = tuple(p for p in PurePosixPath(str(rel).replace("\\", "/")).parts
                  if p not in {"", "."})
    if len(parts) < 2 or parts[0].lower() != "reviews":
        return False
    tail = parts[1:]
    name = tail[0].lower()
    if len(tail) == 1:
        if name == ".harness":
            return True
        if name == "phase_state.json":
            return True
        if name == _REPIN_REQUEST:
            return True
        return (
            name.startswith(_REPIN_PREFIX)
            and (name.endswith(".applied.json") or name.endswith(".stale.json"))
            and len(name) > len(_REPIN_PREFIX) + len(".stale.json")
        )
    return name == ".harness"


def resolve_path(
    project_root: os.PathLike | str,
    rel: os.PathLike | str,
    shipment_id: str | None = None,
) -> Path:
    """Project-relative ``rel`` under the write root, or under the project root
    for a never-redirected path."""
    if is_never_redirected(rel):
        return Path(project_root) / Path(rel)
    return resolve_write_root(project_root, shipment_id) / Path(rel)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "set-active":
        parser = argparse.ArgumentParser(prog="output_lane.py set-active")
        parser.add_argument("--project-root", required=True)
        parser.add_argument("--shipment-id", required=True)
        args = parser.parse_args(argv[1:])
        try:
            print(set_active_shipment(args.project_root, args.shipment_id))
        except OutputLaneError as exc:
            print(f"output_lane: {exc}", file=sys.stderr)
            return 2
        return 0
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("project_root")
    parser.add_argument("--shipment-id")
    args = parser.parse_args(argv)
    try:
        print(resolve_write_root(args.project_root, args.shipment_id))
    except OutputLaneError as exc:
        print(f"output_lane: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
