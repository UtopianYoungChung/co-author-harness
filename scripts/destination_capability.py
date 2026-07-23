#!/usr/bin/env python3
"""destination_capability - the single write-destination chokepoint (producer boundary).

Every harness writer resolves its destination through classify()/assert_writable()
before any byte lands. Policy (Phase C of the producer-boundary plan; constitutional
basis: research/AGENTS.md "Harness shipment boundary" and
research/10_Governance/HARNESS_SHIPMENT_BOUNDARY.md, binding 2026-07-22):

  package    harness package root                    -> writable (repo rules)
  staging    <governed-root>/outputs/co-author-harness/staging/  -> writable
  shipment   <governed-root>/research/60_Workbench/<work-id>/
             reviews/.harness/shipments/<shipment-id>/ -> writable (reports only)
  protected  anywhere else under a governed root     -> REFUSE
  external   outside every governed root             -> writable (OS temp, test
             sandboxes; not governed space)
  ungoverned no governed root discoverable at all    -> REFUSE all non-package
             destinations (fail closed: a distributed install without workspace
             governance has no basis to claim any write capability)

Governed-root discovery walks up from the harness root looking for
`governance/output-routing/output_routing.yaml` (the workspace routing manifest;
authority: OUTPUT_ROUTING_CONTRACT.md). `COAUTHOR_EXTRA_GOVERNED_ROOTS`
(os.pathsep-separated) ADDS governed roots -- used by hermetic tests to govern a
fake tree. It is additive only: it can never remove or replace the discovered
root, so pointing it elsewhere cannot un-protect the real workspace.

Alias handling: destinations are compared after os.path.realpath (resolves
junctions and symlinks on Windows) + os.path.normcase (case-folds and normalizes
separators), so `B:/agents/RESEARCH/x`, a junction into the research tree, and a
`..` traversal all classify identically to the canonical spelling.

Route rows in the routing manifest are NOT consulted for write capability:
route != write-enable (OUTPUT_ROUTING_CONTRACT.md sec.5). Governed writes are
limited to the staging lane and the exact private research shipment lane.
"""

from __future__ import annotations

import os
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent

_MANIFEST_REL = Path("governance") / "output-routing" / "output_routing.yaml"
_STAGING_REL = Path("outputs") / "co-author-harness" / "staging"
_SHIPMENT_PREFIX = tuple(os.path.normcase(p) for p in ("research", "60_Workbench"))
_SHIPMENT_SUFFIX = tuple(os.path.normcase(p) for p in ("reviews", ".harness", "shipments"))

# Re-pin lane: the exact semantic-register re-pin transition-control artifacts a
# Planner may write inside one Workbench work-id's reviews/ directory. Nothing
# else under reviews/ is opened by this lane.
_REVIEWS = os.path.normcase("reviews")
_REPIN_REQUEST_NAME = os.path.normcase("repin_rebind_request.json")
_REPIN_APPLIED_PREFIX = os.path.normcase("repin_rebind_request.")
_REPIN_APPLIED_SUFFIX = os.path.normcase(".applied.json")
_REPIN_STALE_SUFFIX = os.path.normcase(".stale.json")
_REPIN_SIDECAR_TAIL = tuple(
    os.path.normcase(p)
    for p in (".harness", "policies", "reader_accessibility.resolved.json")
)

# Error codes (stable contract for tests and callers)
DEST_PROTECTED = "DEST-PROTECTED"
DEST_UNGOVERNED = "DEST-UNGOVERNED"


class DestinationRefused(RuntimeError):
    """A write destination the producer boundary forbids. Fail closed."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


def _canon(p: os.PathLike | str) -> str:
    return os.path.normcase(os.path.realpath(os.fspath(p)))


def _is_under(child_canon: str, root: Path) -> bool:
    root_canon = _canon(root)
    return child_canon == root_canon or child_canon.startswith(root_canon + os.sep)


def _is_research_shipment(child_canon: str, root: Path) -> bool:
    """True only below one identified Workbench shipment directory.

    The work-id and shipment-id segments are required. The parent
    ``.../shipments`` directory is intentionally still protected.
    """
    root_canon = _canon(root)
    if not _is_under(child_canon, root):
        return False
    rel = os.path.relpath(child_canon, root_canon)
    parts = tuple(os.path.normcase(p) for p in Path(rel).parts)
    if len(parts) < 7:
        return False
    return (parts[:2] == _SHIPMENT_PREFIX
            and parts[3:6] == _SHIPMENT_SUFFIX
            and parts[2] not in {"", ".", ".."}
            and parts[6] not in {"", ".", ".."})


def _work_id_rel_parts(child_canon: str, root: Path) -> tuple[str, ...] | None:
    """Normcased path parts of child relative to root, or None if not under it."""
    if not _is_under(child_canon, root):
        return None
    rel = os.path.relpath(child_canon, _canon(root))
    return tuple(os.path.normcase(p) for p in Path(rel).parts)


def _is_workbench_work_id_root(child_canon: str, root: Path) -> bool:
    """True only for a Workbench package root: research/60_Workbench/<work-id>."""
    parts = _work_id_rel_parts(child_canon, root)
    if parts is None or len(parts) != 3:
        return False
    return parts[:2] == _SHIPMENT_PREFIX and parts[2] not in {"", ".", ".."}


def _is_repin_lane(child_canon: str, root: Path) -> bool:
    """True only for the three re-pin transition-control artifacts under a
    Workbench work-id's ``reviews/`` directory:

      research/60_Workbench/<work-id>/reviews/repin_rebind_request.json
      research/60_Workbench/<work-id>/reviews/repin_rebind_request.<epoch>.applied.json
      research/60_Workbench/<work-id>/reviews/.harness/policies/reader_accessibility.resolved.json

    Nothing else under ``reviews/`` is opened by this predicate.
    """
    parts = _work_id_rel_parts(child_canon, root)
    if parts is None or len(parts) < 5:
        return False
    if parts[:2] != _SHIPMENT_PREFIX or parts[2] in {"", ".", ".."}:
        return False
    if parts[3] != _REVIEWS:
        return False
    tail = parts[4:]
    if len(tail) == 1:
        name = tail[0]
        if name == _REPIN_REQUEST_NAME:
            return True
        return (
            name.startswith(_REPIN_APPLIED_PREFIX)
            and (
                name.endswith(_REPIN_APPLIED_SUFFIX)
                or name.endswith(_REPIN_STALE_SUFFIX)
            )
            and len(name) > len(_REPIN_APPLIED_PREFIX) + min(
                len(_REPIN_APPLIED_SUFFIX), len(_REPIN_STALE_SUFFIX)
            )
        )
    return tail == _REPIN_SIDECAR_TAIL


def discovered_workspace_root() -> Path | None:
    """Nearest ancestor of the harness root carrying the routing manifest."""
    node = HARNESS
    while True:
        if (node / _MANIFEST_REL).is_file():
            return node
        if node.parent == node:
            return None
        node = node.parent


def governed_roots() -> list[Path]:
    """Discovered root plus any extra roots from the environment (additive only)."""
    roots: list[Path] = []
    found = discovered_workspace_root()
    if found is not None:
        roots.append(found)
    extra = os.environ.get("COAUTHOR_EXTRA_GOVERNED_ROOTS", "")
    for item in filter(None, extra.split(os.pathsep)):
        roots.append(Path(item))
    return roots


def classify(destination: os.PathLike | str) -> str:
    """Classify a resolved write destination. Pure; raises nothing."""
    dest = _canon(destination)
    if _is_under(dest, HARNESS):
        return "package"
    roots = governed_roots()
    if not roots:
        return "ungoverned"
    for root in roots:
        if _is_under(dest, root / _STAGING_REL):
            return "staging"
        if _is_research_shipment(dest, root):
            return "shipment"
        if _is_repin_lane(dest, root):
            return "repin"
    for root in roots:
        if _is_under(dest, root):
            return "protected"
    return "external"


def assert_writable(destination: os.PathLike | str, purpose: str = "write") -> str:
    """Return the writable classification or raise DestinationRefused."""
    kind = classify(destination)
    if kind == "protected":
        raise DestinationRefused(
            DEST_PROTECTED,
            f"{purpose} destination {os.fspath(destination)!r} resolves inside a "
            "governed workspace root outside the harness staging or private "
            "shipment lanes. The harness has no write authority there "
            "(research/10_Governance/HARNESS_SHIPMENT_BOUNDARY.md).")
    if kind == "ungoverned":
        raise DestinationRefused(
            DEST_UNGOVERNED,
            f"{purpose} destination {os.fspath(destination)!r} refused: no "
            "workspace routing manifest was discovered, so no write capability "
            "outside the harness package can be established. Failing closed.")
    return kind


def guard_project_root(project_root: os.PathLike | str) -> str:
    """Writer entry-point guard: a mutable project root must be writable."""
    return assert_writable(project_root, purpose="project-root mutation")


def guard_repin_project_root(project_root: os.PathLike | str) -> str:
    """Re-pin / rebind entry guard.

    The semantic-register re-pin writer and its Planner rebind transaction write
    only the re-pin lane artifacts (see ``_is_repin_lane``) plus phase state,
    all confined to one Workbench work-id root. Those two flows may therefore
    treat that work-id root as a writable ``repin_container``. Every other
    transaction still resolves through ``guard_project_root`` and a governed
    project root stays ``protected``.
    """
    dest = _canon(project_root)
    for root in governed_roots():
        if _is_workbench_work_id_root(dest, root):
            return "repin_container"
    return guard_project_root(project_root)
