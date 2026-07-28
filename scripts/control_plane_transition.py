#!/usr/bin/env python3
"""Atomic, exact-byte control-plane transitions.

The transaction publishes exactly eight frozen control members, invalidates
superseded receipt/evaluation authority, and writes a commit marker last.  A
record without a current marker is never authoritative.  Recovery only rolls
forward when every observable byte is still either its recorded preimage or
its intended postimage; foreign bytes fail closed.
"""

from __future__ import annotations

import argparse
import copy
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import stat
from typing import Any, Iterable
import uuid

from jsonschema import Draft202012Validator

import destination_capability as destinations


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "references" / "schemas" / "control_plane_transition.schema.json"
MEMBERS = (
    "controlling_brief",
    "directives",
    "active_target",
    "round_program",
    "revision_plan",
    "assignment_source_binding",
    "reader_policy_binding",
    "affected_receipts_and_evaluations",
)
CAPABILITY_MAP = {
    "package": "package",
    "staging": "governed_staging",
    "shipment": "private_shipment",
}
AUTHORITY_LANES = (
    ("receipt", Path("reviews/.harness/assignment/ready")),
    ("evaluation", Path("reviews/.harness/assignment/evaluations/ready")),
    ("evaluation", Path("reviews/.harness/scholarly-evaluations/ready")),
)
CONTROL_ROOT_REL = Path("reviews/.harness/control-plane")
CLAIM_REL = CONTROL_ROOT_REL / "active_claim.json"
LOCK_REL = CONTROL_ROOT_REL / "authority.lock"
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class ControlPlaneRefusal(RuntimeError):
    """Typed, fail-closed control-plane refusal."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _binding(path: str, data: bytes) -> dict[str, Any]:
    return {"path": path, "sha256": _sha_bytes(data), "byte_length": len(data)}


def _image(data: bytes | None) -> dict[str, Any]:
    return {
        "exists": data is not None,
        "sha256": _sha_bytes(data) if data is not None else None,
        "byte_length": len(data) if data is not None else None,
    }


def _matches_image(path: Path, image: dict[str, Any]) -> bool:
    if not image.get("exists"):
        return not path.exists() and not path.is_symlink()
    if not path.is_file() or _is_link(path):
        return False
    data = path.read_bytes()
    return (
        _sha_bytes(data) == image.get("sha256")
        and len(data) == image.get("byte_length")
    )


def _is_link(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        attributes = getattr(os.lstat(path), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400))


def _safe_relative(raw: Any) -> PurePosixPath:
    if not isinstance(raw, str) or not raw:
        raise ControlPlaneRefusal(
            "CPT-DESTINATION-PROTECTED", f"unsafe project-relative path: {raw!r}"
        )
    win32_invalid = frozenset('<>:"\\|?*')
    if any(character in win32_invalid or ord(character) < 0x20 for character in raw):
        raise ControlPlaneRefusal(
            "CPT-DESTINATION-PROTECTED", f"unsafe project-relative path: {raw!r}"
        )
    raw_parts = raw.split("/")
    if any(part in {"", ".", ".."} for part in raw_parts):
        raise ControlPlaneRefusal(
            "CPT-DESTINATION-PROTECTED", f"unsafe project-relative path: {raw!r}"
        )
    reserved_devices = {"con", "prn", "aux", "nul"}
    for part in raw_parts:
        # Win32 removes trailing dots and spaces from each ordinary path
        # segment.  Refuse those spellings on every host so a record cannot be
        # validated on POSIX and later alias a different target on Windows.
        if part != part.rstrip(" ."):
            raise ControlPlaneRefusal(
                "CPT-DESTINATION-PROTECTED",
                f"Windows-ambiguous project-relative path: {raw!r}",
            )
        # DOS device names remain reserved when an extension is present and
        # are case-insensitive.  Stripping spaces/dots from the stem also
        # fails closed for ambiguous forms such as ``NUL .json``.
        device_stem = part.split(".", 1)[0].rstrip(" .").casefold()
        if (
            device_stem in reserved_devices
            or (
                len(device_stem) == 4
                and device_stem[:3] in {"com", "lpt"}
                and device_stem[3] in "123456789"
            )
        ):
            raise ControlPlaneRefusal(
                "CPT-DESTINATION-PROTECTED",
                f"reserved Windows device path: {raw!r}",
            )
    relative = PurePosixPath(raw)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise ControlPlaneRefusal(
            "CPT-DESTINATION-PROTECTED", f"unsafe project-relative path: {raw!r}"
        )
    return relative


def _inside(project: Path, raw: Any, *, allow_missing: bool = True) -> Path:
    relative = _safe_relative(raw)
    project_real = Path(os.path.realpath(project))
    cursor = project
    for part in relative.parts:
        cursor = cursor / part
        if cursor.exists() or cursor.is_symlink():
            if _is_link(cursor):
                raise ControlPlaneRefusal(
                    "CPT-DESTINATION-PROTECTED",
                    f"control path traverses a link or reparse point: {raw}",
                )
    resolved = Path(os.path.realpath(cursor))
    try:
        resolved.relative_to(project_real)
    except ValueError as exc:
        raise ControlPlaneRefusal(
            "CPT-DESTINATION-PROTECTED", f"control path escapes project root: {raw}"
        ) from exc
    if not allow_missing and not cursor.exists():
        raise ControlPlaneRefusal(
            "CPT-PREIMAGE-STALE", f"required control path is missing: {raw}"
        )
    return cursor


def _guard(project: Path) -> str:
    try:
        kind = destinations.guard_project_root(project)
    except destinations.DestinationRefused as exc:
        raise ControlPlaneRefusal(
            "CPT-DESTINATION-PROTECTED", f"{exc.code}: {exc}"
        ) from exc
    normalized = CAPABILITY_MAP.get(kind)
    if normalized is None:
        raise ControlPlaneRefusal(
            "CPT-DESTINATION-PROTECTED",
            f"destination capability {kind!r} cannot publish control state",
        )
    return normalized


def _guard_issuance(
    project: Path, *, allow_repin_container: bool = False,
) -> str:
    """Guard receipt/evaluation issuance without widening control publication.

    Existing hermetic receipt suites use OS-temporary external projects, which
    destination_capability explicitly permits.  Control publication itself
    remains limited by :func:`_guard` to package/staging/shipment.
    """
    try:
        guard = (
            destinations.guard_repin_project_root
            if allow_repin_container
            else destinations.guard_project_root
        )
        kind = guard(project)
    except destinations.DestinationRefused as exc:
        raise ControlPlaneRefusal(
            "CPT-DESTINATION-PROTECTED", f"{exc.code}: {exc}"
        ) from exc
    allowed = {"package", "staging", "shipment", "external"}
    if allow_repin_container:
        allowed.add("repin_container")
    if kind not in allowed:
        raise ControlPlaneRefusal(
            "CPT-DESTINATION-PROTECTED", f"destination capability {kind!r} forbids authority issuance"
        )
    return kind


def _claim_path(project: Path) -> Path:
    return _inside(project, CLAIM_REL.as_posix())


def _pid_alive(pid: Any) -> bool:
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        process_query_limited_information = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(
            process_query_limited_information, False, pid
        )
        if not handle:
            return False
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _claim_owner_description(claim: dict[str, Any]) -> str:
    owner = claim.get("owner") if isinstance(claim, dict) else None
    if not isinstance(owner, dict):
        return "malformed owner"
    host = owner.get("host")
    pid = owner.get("pid")
    if host != platform.node():
        return f"foreign host={host!r} pid={pid!r}"
    return f"host={host!r} pid={pid!r} live={_pid_alive(pid)}"


def _read_claim(project: Path) -> dict[str, Any] | None:
    path = _claim_path(project)
    if not path.exists() and not path.is_symlink():
        return None
    if not path.is_file() or _is_link(path):
        raise ControlPlaneRefusal(
            "CPT-DESTINATION-PROTECTED", "control transaction claim is not a plain file"
        )
    claim = _load_json(path, "CPT-RECOVERY-REQUIRED")
    required = {
        "schema_version", "claim_type", "transition_id", "nonce", "state",
        "owner", "authority_snapshot",
    }
    if set(claim) != required or claim.get("schema_version") != "1.0.0" or claim.get("claim_type") != "control_plane_transition":
        raise ControlPlaneRefusal("CPT-RECOVERY-REQUIRED", "control claim shape is invalid")
    owner = claim.get("owner")
    snapshot = claim.get("authority_snapshot")
    if (
        not ID_RE.fullmatch(str(claim.get("transition_id", "")))
        or not isinstance(claim.get("nonce"), str)
        or not claim["nonce"]
        or claim.get("state") not in {"preparing", "prepared", "publishing", "recovering"}
        or not isinstance(owner, dict)
        or set(owner) != {"host", "pid"}
        or not isinstance(owner.get("host"), str)
        or not isinstance(owner.get("pid"), int)
        or not isinstance(snapshot, dict)
        or set(snapshot) != {"epoch", "entries"}
        or not isinstance(snapshot.get("epoch"), str)
        or not isinstance(snapshot.get("entries"), list)
    ):
        raise ControlPlaneRefusal("CPT-RECOVERY-REQUIRED", "control claim fields are invalid")
    return claim


@contextmanager
def _authority_lock(project: Path, *, blocking: bool = False):
    """Per-project OS lock shared with receipt/evaluation issuance."""
    lock_path = _inside(project, LOCK_REL.as_posix())
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+b")
    try:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
            os.fsync(handle.fileno())
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                mode = msvcrt.LK_LOCK if blocking else msvcrt.LK_NBLCK
                msvcrt.locking(handle.fileno(), mode, 1)
            else:
                import fcntl

                flags = fcntl.LOCK_EX if blocking else fcntl.LOCK_EX | fcntl.LOCK_NB
                fcntl.flock(handle.fileno(), flags)
        except (OSError, BlockingIOError) as exc:
            raise ControlPlaneRefusal(
                "CPT-RECOVERY-REQUIRED", "another authority/control operation holds the OS lock"
            ) from exc
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()


def assert_no_active_control_transition(
    project_root: Path | str, *, allow_repin_container: bool = False,
) -> dict[str, Any]:
    """Read-only issuance preflight; the context-manager guard closes the race."""
    project = Path(project_root).absolute()
    _guard_issuance(project, allow_repin_container=allow_repin_container)
    claim = _read_claim(project)
    if claim is not None:
        raise ControlPlaneRefusal(
            "CPT-LIVE-RECEIPT",
            f"control transition {claim['transition_id']} owns authority issuance "
            f"({_claim_owner_description(claim)})",
        )
    return {"verdict": "clear", "findings": []}


@contextmanager
def authority_issuance_guard(
    project_root: Path | str, *, allow_repin_container: bool = False,
):
    """Hold the shared OS barrier across a receipt/evaluation durable write."""
    project = Path(project_root).absolute()
    _guard_issuance(project, allow_repin_container=allow_repin_container)
    with _authority_lock(project, blocking=True):
        assert_no_active_control_transition(
            project, allow_repin_container=allow_repin_container,
        )
        yield


def _load_json(path: Path, code: str = "CPT-PUBLICATION-INCOMPLETE") -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8", errors="strict"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ControlPlaneRefusal(code, f"cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ControlPlaneRefusal(code, f"JSON object required: {path}")
    return value


def _schema_validator() -> Draft202012Validator:
    schema = _load_json(SCHEMA)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _schema_check(candidate: dict[str, Any]) -> None:
    errors = sorted(_schema_validator().iter_errors(candidate), key=lambda error: list(error.path))
    if errors:
        raise ControlPlaneRefusal(
            "CPT-PUBLICATION-INCOMPLETE", f"schema violation: {errors[0].message}"
        )


def _normalized_relative(raw: Any) -> str:
    relative = _safe_relative(raw)
    return "/".join(part.casefold() for part in relative.parts)


def _require_unique_paths(paths: list[Any], label: str) -> list[str]:
    normalized = [_normalized_relative(path) for path in paths]
    if len(set(normalized)) != len(normalized):
        raise ControlPlaneRefusal(
            "CPT-DESTINATION-PROTECTED", f"normalized path alias in {label}"
        )
    return normalized


def _reconcile_manifest(candidate: dict[str, Any]) -> None:
    members = candidate.get("members", [])
    manifest = candidate.get("publication_manifest")
    if not isinstance(manifest, dict):
        raise ControlPlaneRefusal("CPT-PUBLICATION-INCOMPLETE", "publication_manifest must be an object")
    publications = manifest.get("member_publications")
    invalidations = manifest.get("invalidations")
    if not isinstance(publications, list) or not isinstance(invalidations, list):
        raise ControlPlaneRefusal(
            "CPT-PUBLICATION-INCOMPLETE", "manifest publications and invalidations must be arrays"
        )
    member_map = {
        row.get("member"): row for row in members if isinstance(row, dict)
    }
    publication_map = {
        row.get("member"): row for row in publications if isinstance(row, dict)
    }
    if (
        len(publications) != len(MEMBERS)
        or set(publication_map) != set(MEMBERS)
        or len(publication_map) != len(publications)
    ):
        raise ControlPlaneRefusal(
            "CPT-IDENTITY-SPLIT", "member_publications are not a bijection with public members"
        )
    target_paths: list[str] = []
    staged_paths: list[str] = []
    for name in MEMBERS:
        public = member_map[name]
        detail = publication_map[name]
        if (
            detail.get("path") != public.get("path")
            or detail.get("postimage") != public.get("postimage")
            or (public.get("postimage", {}).get("exists") and detail.get("staged_path") is None)
            or (not public.get("postimage", {}).get("exists") and detail.get("staged_path") is not None)
        ):
            raise ControlPlaneRefusal(
                "CPT-IDENTITY-SPLIT", f"manifest member publication split: {name}"
            )
        target_paths.append(public.get("path"))
        if detail.get("staged_path") is not None:
            staged_paths.append(detail["staged_path"])
    public_authority = candidate.get("superseded_authority")
    if not isinstance(public_authority, list):
        raise ControlPlaneRefusal(
            "CPT-PUBLICATION-INCOMPLETE", "superseded_authority must be an array"
        )
    public_keys = [
        (
            row.get("authority_kind"), row.get("receipt_id"),
            row.get("pre_state"), row.get("post_state"),
        )
        for row in public_authority if isinstance(row, dict)
    ]
    detail_keys = [
        (
            row.get("authority_kind"), row.get("receipt_id"),
            row.get("pre_state"), row.get("post_state"),
        )
        for row in invalidations if isinstance(row, dict)
    ]
    if (
        len(public_keys) != len(public_authority)
        or len(detail_keys) != len(invalidations)
        or len(set(public_keys)) != len(public_keys)
        or len(set(detail_keys)) != len(detail_keys)
        or set(public_keys) != set(detail_keys)
    ):
        raise ControlPlaneRefusal(
            "CPT-IDENTITY-SPLIT",
            "public superseded_authority and manifest invalidations are not an exact bijection",
        )
    invalidation_paths: list[str] = []
    for row in invalidations:
        if not isinstance(row, dict):
            raise ControlPlaneRefusal("CPT-PUBLICATION-INCOMPLETE", "invalidation must be an object")
        source = row.get("source")
        destination = row.get("destination")
        if not isinstance(source, dict) or not isinstance(destination, dict):
            raise ControlPlaneRefusal("CPT-PUBLICATION-INCOMPLETE", "invalidation sides are required")
        if (
            source.get("preimage", {}).get("exists") is not True
            or source.get("postimage") != _image(None)
            or destination.get("preimage") != _image(None)
            or destination.get("postimage") != source.get("preimage")
        ):
            raise ControlPlaneRefusal(
                "CPT-IDENTITY-SPLIT", f"invalidation images split: {row.get('receipt_id')}"
            )
        invalidation_paths.extend(
            [source.get("path"), destination.get("path"), row.get("staged_path")]
        )
    normalized_targets = _require_unique_paths(target_paths, "control targets")
    normalized_staged = _require_unique_paths(staged_paths, "member staged paths")
    normalized_invalidations = _require_unique_paths(
        invalidation_paths, "authority source/destination/staged paths"
    )
    if set(normalized_targets) & (set(normalized_staged) | set(normalized_invalidations)):
        raise ControlPlaneRefusal(
            "CPT-DESTINATION-PROTECTED", "control targets alias staged or authority paths"
        )
    if set(normalized_staged) & set(normalized_invalidations):
        raise ControlPlaneRefusal(
            "CPT-DESTINATION-PROTECTED", "member and authority staged paths alias"
        )
    active = candidate.get("active_target")
    if isinstance(active, dict):
        _normalized_relative(active.get("path"))
    marker = candidate.get("commit_marker")
    if marker is not None:
        if not isinstance(marker, dict):
            raise ControlPlaneRefusal("CPT-PUBLICATION-INCOMPLETE", "commit_marker must be a binding")
        marker_path = _normalized_relative(marker.get("path"))
        if marker_path in set(normalized_targets + normalized_staged + normalized_invalidations):
            raise ControlPlaneRefusal(
                "CPT-DESTINATION-PROTECTED", "commit marker aliases transaction inputs/effects"
            )


def validate_transition(candidate: dict[str, Any]) -> dict[str, Any]:
    """Validate the frozen in-memory interface and return zero findings.

    Attack-specific checks deliberately precede generic schema validation so
    callers receive the frozen semantic refusal instead of a schema side effect.
    Exact filesystem freshness is added by :func:`validate`.
    """
    if not isinstance(candidate, dict):
        raise ControlPlaneRefusal("CPT-PUBLICATION-INCOMPLETE", "transaction must be an object")
    rows = candidate.get("members")
    if not isinstance(rows, list):
        raise ControlPlaneRefusal("CPT-PUBLICATION-INCOMPLETE", "members must be an array")
    revisions = {
        row.get("control_revision") for row in rows
        if isinstance(row, dict) and isinstance(row.get("control_revision"), str)
    }
    if len(revisions) != 1:
        raise ControlPlaneRefusal(
            "CPT-CONTROL-REVISION-MIXED", "all control members must name one revision"
        )
    by_name = {
        row.get("member"): row for row in rows
        if isinstance(row, dict) and isinstance(row.get("member"), str)
    }
    if set(by_name) != set(MEMBERS) or len(rows) != len(MEMBERS):
        raise ControlPlaneRefusal(
            "CPT-PUBLICATION-INCOMPLETE", "the exact eight-member control set is required"
        )
    _require_unique_paths(
        [row.get("path") for row in rows if isinstance(row, dict)], "control members"
    )
    target = candidate.get("active_target")
    target_row = by_name["active_target"]
    post = target_row.get("postimage")
    if not isinstance(target, dict) or not isinstance(post, dict) or any(
        target.get(key) != expected
        for key, expected in (
            ("path", target_row.get("path")),
            ("sha256", post.get("sha256")),
            ("byte_length", post.get("byte_length")),
        )
    ):
        raise ControlPlaneRefusal(
            "CPT-IDENTITY-SPLIT", "active target path/hash/length split from its member postimage"
        )
    authority = candidate.get("superseded_authority")
    if not isinstance(authority, list):
        raise ControlPlaneRefusal(
            "CPT-PUBLICATION-INCOMPLETE", "superseded_authority must be an array"
        )
    authority_ids = [
        (row.get("authority_kind"), row.get("receipt_id"))
        for row in authority if isinstance(row, dict)
    ]
    if len(set(authority_ids)) != len(authority_ids):
        raise ControlPlaneRefusal(
            "CPT-IDENTITY-SPLIT", "superseded authority identities are duplicated"
        )
    live = [row for row in authority if not isinstance(row, dict) or row.get("post_state") != "invalidated"]
    if live:
        raise ControlPlaneRefusal(
            "CPT-LIVE-RECEIPT", "superseded receipt/evaluation authority remains live"
        )
    _reconcile_manifest(candidate)
    _schema_check(candidate)
    return {"verdict": "validated", "findings": []}


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _transaction_dir(project: Path, transition_id: str) -> Path:
    if not ID_RE.fullmatch(transition_id):
        raise ControlPlaneRefusal("CPT-PUBLICATION-INCOMPLETE", "unsafe transition_id")
    return project / "reviews" / ".harness" / "control-plane" / "transitions" / transition_id


def _paths(project: Path, transition_id: str) -> dict[str, Path]:
    root = _transaction_dir(project, transition_id)
    return {
        "root": root,
        "record": root / "transaction.json",
        "journal": root / "journal.json",
        "manifest": root / "publication_manifest.json",
        "marker": root / "commit_marker.json",
        "staged": root / "staged",
        "staged_authority": root / "staged_authority",
    }


def _digest_rows(rows: Iterable[dict[str, Any]]) -> str:
    return _sha_bytes(_canonical(list(rows)))


def _member_digest(record: dict[str, Any], image_name: str) -> str:
    rows = [
        {"member": row["member"], "path": row["path"], "image": row[image_name]}
        for row in sorted(record["members"], key=lambda item: item["member"])
    ]
    invalidations = record["publication_manifest"].get("invalidations", [])
    for row in sorted(
        record["superseded_authority"],
        key=lambda item: (item["authority_kind"], item["receipt_id"]),
    ):
        rows.append(
            {
                "member": f"authority-public:{row['authority_kind']}:{row['receipt_id']}",
                "pre_state": row["pre_state"],
                "post_state": row["post_state"],
            }
        )
    for row in sorted(invalidations, key=lambda item: item["receipt_id"]):
        for side in ("source", "destination"):
            rows.append(
                {
                    "member": f"authority:{row['authority_kind']}:{row['receipt_id']}:{side}",
                    "pre_state": row["pre_state"],
                    "post_state": row["post_state"],
                    "path": row[side]["path"],
                    "image": row[side][image_name],
                }
            )
    return _digest_rows(rows)


def _authority_digest(record: dict[str, Any]) -> str:
    return _sha_bytes(
        _canonical(
            {
                "public": sorted(
                    record["superseded_authority"],
                    key=lambda item: (item["authority_kind"], item["receipt_id"]),
                ),
                "invalidations": sorted(
                    record["publication_manifest"]["invalidations"],
                    key=lambda item: (item["authority_kind"], item["receipt_id"]),
                ),
            }
        )
    )


def _write_support(paths: dict[str, Path], record: dict[str, Any]) -> None:
    _atomic_write(paths["journal"], _canonical(record["journal"]))
    _atomic_write(paths["manifest"], _canonical(record["publication_manifest"]))
    _atomic_write(paths["record"], _canonical(record))


def _plan_member(project: Path, paths: dict[str, Path], row: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(row, dict):
        raise ControlPlaneRefusal("CPT-PUBLICATION-INCOMPLETE", "plan member must be an object")
    name = row.get("member")
    if name not in MEMBERS:
        raise ControlPlaneRefusal("CPT-PUBLICATION-INCOMPLETE", f"unknown control member: {name!r}")
    target_rel = _safe_relative(row.get("path")).as_posix()
    target = _inside(project, target_rel)
    if paths["root"] == target or paths["root"] in target.parents:
        raise ControlPlaneRefusal("CPT-DESTINATION-PROTECTED", "control target overlaps transaction state")
    before = target.read_bytes() if target.is_file() and not _is_link(target) else None
    mode = row.get("publication_mode")
    candidate_path = row.get("candidate_path")
    after: bytes | None
    if mode == "delete":
        after = None
        if candidate_path is not None:
            raise ControlPlaneRefusal("CPT-PUBLICATION-INCOMPLETE", "delete member cannot name candidate_path")
    else:
        candidate = _inside(project, candidate_path, allow_missing=False)
        if not candidate.is_file() or _is_link(candidate):
            raise ControlPlaneRefusal("CPT-PUBLICATION-INCOMPLETE", f"candidate is not a plain file: {candidate_path}")
        after = candidate.read_bytes()
    if mode == "create" and before is not None:
        raise ControlPlaneRefusal("CPT-PREIMAGE-STALE", f"create target already exists: {target_rel}")
    if mode in {"replace", "delete"} and before is None:
        raise ControlPlaneRefusal("CPT-PREIMAGE-STALE", f"{mode} target is absent: {target_rel}")
    if mode not in {"create", "replace", "delete"}:
        raise ControlPlaneRefusal("CPT-PUBLICATION-INCOMPLETE", f"invalid publication mode: {mode!r}")
    staged_rel: str | None = None
    if after is not None:
        staged_rel = (Path("reviews") / ".harness" / "control-plane" / "transitions" /
                      paths["root"].name / "staged" / f"{name}.bin").as_posix()
    member = {
        "member": name,
        "control_revision": row.get("control_revision"),
        "path": target_rel,
        "preimage": _image(before),
        "postimage": _image(after),
        "publication_mode": mode,
    }
    publication = {
        "member": name,
        "path": target_rel,
        "staged_path": staged_rel,
        "postimage": member["postimage"],
    }
    if after is not None:
        publication["_staged_bytes"] = after
    return member, publication


def _plan_authority(project: Path, paths: dict[str, Path], row: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(row, dict):
        raise ControlPlaneRefusal("CPT-PUBLICATION-INCOMPLETE", "authority row must be an object")
    receipt_id = row.get("receipt_id")
    if not isinstance(receipt_id, str) or not receipt_id:
        raise ControlPlaneRefusal("CPT-PUBLICATION-INCOMPLETE", "authority receipt_id is required")
    source_rel = _safe_relative(row.get("path")).as_posix()
    source = _inside(project, source_rel, allow_missing=False)
    value = _load_json(source, "CPT-LIVE-RECEIPT")
    pre_state = row.get("pre_state")
    if pre_state != "ready":
        raise ControlPlaneRefusal("CPT-LIVE-RECEIPT", f"authority pre-state mismatch: {receipt_id}")
    if value.get("receipt_id", value.get("evaluation_id")) != receipt_id:
        raise ControlPlaneRefusal("CPT-IDENTITY-SPLIT", f"authority identity mismatch: {receipt_id}")
    source_parts = PurePosixPath(source_rel).parts
    destination_rel: str | None = None
    for _, lane in AUTHORITY_LANES:
        lane_parts = tuple(PurePosixPath(lane.as_posix()).parts)
        if source_parts[:-1] == lane_parts:
            destination_rel = (
                PurePosixPath(*lane_parts[:-1]) / "invalidated" / source_parts[-1]
            ).as_posix()
            break
    if destination_rel is None:
        raise ControlPlaneRefusal(
            "CPT-DESTINATION-PROTECTED", f"authority is outside a frozen ready lane: {source_rel}"
        )
    destination = _inside(project, destination_rel)
    if destination.exists() or destination.is_symlink():
        raise ControlPlaneRefusal(
            "CPT-LIVE-RECEIPT", f"invalidated authority destination already exists: {receipt_id}"
        )
    after = source.read_bytes()
    staged_rel = (Path("reviews") / ".harness" / "control-plane" / "transitions" /
                  paths["root"].name / "staged_authority" / f"{receipt_id}.json").as_posix()
    public = {
        "receipt_id": receipt_id,
        "authority_kind": row.get("authority_kind", "receipt"),
        "pre_state": pre_state,
        "post_state": "invalidated",
    }
    detail = {
        **public,
        "source": {
            "path": source_rel,
            "preimage": _image(after),
            "postimage": _image(None),
        },
        "destination": {
            "path": destination_rel,
            "preimage": _image(None),
            "postimage": _image(after),
        },
        "staged_path": staged_rel,
        "_staged_bytes": after,
    }
    return public, detail


def _discover_live_authority(project: Path) -> dict[tuple[str, str, str], dict[str, Any]]:
    discovered: dict[tuple[str, str, str], dict[str, Any]] = {}
    for authority_kind, relative in AUTHORITY_LANES:
        lane = project / relative
        if not lane.exists():
            continue
        if not lane.is_dir() or _is_link(lane):
            raise ControlPlaneRefusal(
                "CPT-DESTINATION-PROTECTED", f"authority lane is not a plain directory: {relative.as_posix()}"
            )
        for path in sorted(lane.glob("*.json")):
            if not path.is_file() or _is_link(path):
                raise ControlPlaneRefusal(
                    "CPT-DESTINATION-PROTECTED", f"authority record is not a plain file: {path}"
                )
            value = _load_json(path, "CPT-LIVE-RECEIPT")
            receipt_id = value.get("receipt_id", value.get("evaluation_id"))
            if not isinstance(receipt_id, str) or not receipt_id:
                raise ControlPlaneRefusal(
                    "CPT-LIVE-RECEIPT", f"live authority lacks stable identity: {path}"
                )
            rel = path.relative_to(project).as_posix()
            key = (authority_kind, receipt_id, rel)
            discovered[key] = value
    return discovered


def _authority_snapshot(project: Path) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for (authority_kind, receipt_id, relative), value in sorted(
        _discover_live_authority(project).items()
    ):
        path = _inside(project, relative, allow_missing=False)
        data = path.read_bytes()
        entries.append(
            {
                "authority_kind": authority_kind,
                "receipt_id": receipt_id,
                "state": "ready",
                "path": relative,
                "image": _image(data),
            }
        )
    return {"epoch": _sha_bytes(_canonical(entries)), "entries": entries}


def _claim_event(record: dict[str, Any], prefix: str) -> str:
    values = [
        event[len(prefix):]
        for event in record.get("journal", {}).get("events", [])
        if isinstance(event, str) and event.startswith(prefix)
    ]
    if len(values) != 1 or not values[0]:
        raise ControlPlaneRefusal(
            "CPT-IDENTITY-SPLIT", f"transaction does not bind exactly one {prefix} event"
        )
    return values[0]


def _new_claim(transition_id: str) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "claim_type": "control_plane_transition",
        "transition_id": transition_id,
        "nonce": uuid.uuid4().hex,
        "state": "preparing",
        "owner": {"host": platform.node(), "pid": os.getpid()},
        "authority_snapshot": {"epoch": "0" * 64, "entries": []},
    }


def _create_claim(project: Path, transition_id: str) -> dict[str, Any]:
    if _read_claim(project) is not None:
        claim = _read_claim(project)
        assert claim is not None
        raise ControlPlaneRefusal(
            "CPT-RECOVERY-REQUIRED",
            f"control transition {claim['transition_id']} already owns the project "
            f"({_claim_owner_description(claim)})",
        )
    claim = _new_claim(transition_id)
    path = _claim_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(_canonical(claim))
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise ControlPlaneRefusal(
            "CPT-RECOVERY-REQUIRED", "control transaction claim appeared concurrently"
        ) from exc
    return claim


def _write_claim(project: Path, claim: dict[str, Any]) -> None:
    _atomic_write(_claim_path(project), _canonical(claim))


def _bound_claim(
    project: Path,
    record: dict[str, Any],
    *,
    state: str,
    allow_adopt_dead: bool,
) -> dict[str, Any]:
    claim = _read_claim(project)
    if claim is None:
        raise ControlPlaneRefusal("CPT-RECOVERY-REQUIRED", "bound control claim is missing")
    _assert_claim_binding(record, claim)
    owner = claim["owner"]
    same_host = owner.get("host") == platform.node()
    same_pid = owner.get("pid") == os.getpid()
    live = same_host and _pid_alive(owner.get("pid"))
    if not same_host:
        raise ControlPlaneRefusal(
            "CPT-RECOVERY-REQUIRED", f"foreign claim owner refuses adoption: {_claim_owner_description(claim)}"
        )
    if live and not same_pid:
        raise ControlPlaneRefusal(
            "CPT-RECOVERY-REQUIRED", f"live claim owner refuses adoption: {_claim_owner_description(claim)}"
        )
    if not same_pid and not allow_adopt_dead:
        raise ControlPlaneRefusal(
            "CPT-RECOVERY-REQUIRED", f"claim owner is not this process: {_claim_owner_description(claim)}"
        )
    claim["owner"] = {"host": platform.node(), "pid": os.getpid()}
    claim["state"] = state
    _write_claim(project, claim)
    return claim


def _assert_claim_binding(record: dict[str, Any], claim: dict[str, Any]) -> None:
    nonce = _claim_event(record, "claim_nonce:")
    epoch = _claim_event(record, "authority_epoch:")
    if (
        claim.get("transition_id") != record.get("transition_id")
        or claim.get("nonce") != nonce
        or claim.get("authority_snapshot", {}).get("epoch") != epoch
    ):
        raise ControlPlaneRefusal("CPT-IDENTITY-SPLIT", "control claim does not bind transaction")


def _release_claim(project: Path, nonce: str) -> None:
    claim = _read_claim(project)
    if claim is None:
        return
    if claim.get("nonce") != nonce:
        raise ControlPlaneRefusal("CPT-RECOVERY-REQUIRED", "refusing to release a foreign claim")
    _claim_path(project).unlink()


def _assert_pre_authority_epoch(
    project: Path, record: dict[str, Any], claim: dict[str, Any]
) -> None:
    current = _authority_snapshot(project)
    expected = claim["authority_snapshot"]
    if current != expected or current["epoch"] != _claim_event(record, "authority_epoch:"):
        raise ControlPlaneRefusal(
            "CPT-LIVE-RECEIPT",
            "receipt/evaluation authority changed after control prepare",
        )


def _assert_current_authority_epoch(
    project: Path,
    record: dict[str, Any],
    claim: dict[str, Any],
    classes: dict[str, str],
) -> None:
    expected_entries = []
    for entry in claim["authority_snapshot"]["entries"]:
        key = (
            f"authority:{entry['authority_kind']}:{entry['receipt_id']}:source"
        )
        if classes.get(key) == "preimage":
            expected_entries.append(entry)
    current = _authority_snapshot(project)
    expected_entries = sorted(
        expected_entries,
        key=lambda row: (row["authority_kind"], row["receipt_id"], row["path"]),
    )
    if current["entries"] != expected_entries:
        raise ControlPlaneRefusal(
            "CPT-LIVE-RECEIPT", "authority epoch changed during control publication"
        )


def _assert_post_authority_epoch(project: Path, record: dict[str, Any]) -> None:
    current = _authority_snapshot(project)
    if current["entries"]:
        identities = ", ".join(
            f"{row['authority_kind']}:{row['receipt_id']}" for row in current["entries"]
        )
        raise ControlPlaneRefusal(
            "CPT-LIVE-RECEIPT",
            f"live receipt/evaluation authority remains before marker: {identities}",
        )
    public = {
        (row["authority_kind"], row["receipt_id"])
        for row in record["superseded_authority"]
    }
    invalidated = {
        (row["authority_kind"], row["receipt_id"])
        for row in record["publication_manifest"]["invalidations"]
    }
    if public != invalidated:
        raise ControlPlaneRefusal(
            "CPT-IDENTITY-SPLIT", "authority bijection changed before marker"
        )


def _prepare_locked(
    project: Path,
    plan: dict[str, Any],
    transition_id: str,
    capability: str,
    claim: dict[str, Any],
) -> dict[str, Any]:
    paths = _paths(project, transition_id)
    if paths["root"].exists():
        raise ControlPlaneRefusal("CPT-RECOVERY-REQUIRED", "transition_id already has durable state")
    plan_rows = plan.get("members") if isinstance(plan, dict) else None
    if not isinstance(plan_rows, list):
        raise ControlPlaneRefusal("CPT-PUBLICATION-INCOMPLETE", "plan members must be an array")
    members: list[dict[str, Any]] = []
    publications: list[dict[str, Any]] = []
    staged: list[tuple[Path, bytes]] = []
    for row in plan_rows:
        member, publication = _plan_member(project, paths, row)
        payload = publication.pop("_staged_bytes", None)
        if payload is not None:
            staged_path = _inside(project, publication["staged_path"])
            staged.append((staged_path, payload))
        members.append(member)
        publications.append(publication)
    target_paths = [row["path"] for row in members]
    candidate_paths = [
        _safe_relative(row["candidate_path"]).as_posix()
        for row in plan_rows
        if isinstance(row, dict) and row.get("candidate_path") is not None
    ]
    if len(set(target_paths)) != len(target_paths) or len(set(candidate_paths)) != len(candidate_paths):
        raise ControlPlaneRefusal("CPT-IDENTITY-SPLIT", "control target/candidate paths are aliased")
    if set(target_paths) & set(candidate_paths):
        raise ControlPlaneRefusal("CPT-IDENTITY-SPLIT", "candidate bytes alias a live control target")
    authorities: list[dict[str, Any]] = []
    invalidations: list[dict[str, Any]] = []
    authority_plan = plan.get("superseded_authority", [])
    if not isinstance(authority_plan, list):
        raise ControlPlaneRefusal("CPT-PUBLICATION-INCOMPLETE", "superseded_authority must be an array")
    planned_authority = {
        (
            row.get("authority_kind", "receipt"),
            row.get("receipt_id"),
            _safe_relative(row.get("path")).as_posix(),
        )
        for row in authority_plan if isinstance(row, dict)
    }
    if len(planned_authority) != len(authority_plan):
        raise ControlPlaneRefusal("CPT-IDENTITY-SPLIT", "superseded authority plan is duplicated")
    snapshot = _authority_snapshot(project)
    discovered_authority = {
        (row["authority_kind"], row["receipt_id"], row["path"])
        for row in snapshot["entries"]
    }
    omitted = sorted(discovered_authority - planned_authority)
    if omitted:
        raise ControlPlaneRefusal(
            "CPT-LIVE-RECEIPT",
            "live receipt/evaluation omitted from atomic invalidation: "
            + ", ".join(item[1] for item in omitted),
        )
    for row in authority_plan:
        authority, detail = _plan_authority(project, paths, row)
        payload = detail.pop("_staged_bytes")
        staged.append((_inside(project, detail["staged_path"]), payload))
        authorities.append(authority)
        invalidations.append(detail)
    authority_paths = {
        side["path"] for row in invalidations
        for side in (row["source"], row["destination"])
    }
    if authority_paths & (set(target_paths) | set(candidate_paths)):
        raise ControlPlaneRefusal("CPT-IDENTITY-SPLIT", "authority record aliases control bytes")
    by_name = {row["member"]: row for row in members}
    if set(by_name) != set(MEMBERS) or len(members) != len(MEMBERS):
        raise ControlPlaneRefusal("CPT-PUBLICATION-INCOMPLETE", "plan must contain each control member once")
    active = by_name["active_target"]
    if not active["postimage"]["exists"]:
        raise ControlPlaneRefusal("CPT-IDENTITY-SPLIT", "active target cannot be deleted")
    record: dict[str, Any] = {
        "schema_version": "1.0.0",
        "transition_id": transition_id,
        "state": "prepared",
        "project_root": str(project),
        "destination_capability": capability,
        "active_target": {
            "path": active["path"],
            "sha256": active["postimage"]["sha256"],
            "byte_length": active["postimage"]["byte_length"],
        },
        "members": members,
        "superseded_authority": authorities,
        "preimage_digest": "0" * 64,
        "postimage_digest": "0" * 64,
        "journal": {
            "state": "prepared",
            "events": [
                "prepared",
                f"claim_nonce:{claim['nonce']}",
                f"authority_epoch:{snapshot['epoch']}",
            ],
        },
        "publication_manifest": {
            "state": "candidate",
            "member_publications": publications,
            "invalidations": invalidations,
            "completed_effects": [],
        },
        "commit_marker": None,
    }
    record["preimage_digest"] = _member_digest(record, "preimage")
    record["postimage_digest"] = _member_digest(record, "postimage")
    validate_transition(record)
    for path, data in staged:
        _atomic_write(path, data)
    _write_support(paths, record)
    claim["authority_snapshot"] = snapshot
    claim["state"] = "prepared"
    _write_claim(project, claim)
    return record


def prepare(project_root: Path | str, plan: dict[str, Any], transition_id: str) -> dict[str, Any]:
    project = Path(project_root).absolute()
    capability = _guard(project)
    paths = _paths(project, transition_id)
    with _authority_lock(project):
        claim = _create_claim(project, transition_id)
        try:
            return _prepare_locked(project, plan, transition_id, capability, claim)
        except Exception:
            if not paths["root"].exists():
                _release_claim(project, claim["nonce"])
            raise


def _load_record(project: Path, transition_id: str) -> tuple[dict[str, Path], dict[str, Any]]:
    paths = _paths(project, transition_id)
    record = _load_json(paths["record"])
    if record.get("project_root") != str(project) or record.get("transition_id") != transition_id:
        raise ControlPlaneRefusal("CPT-IDENTITY-SPLIT", "transaction identity does not bind invocation")
    validate_transition(record)
    return paths, record


def _verify_staged(project: Path, record: dict[str, Any]) -> None:
    for publication in record["publication_manifest"].get("member_publications", []):
        postimage = publication["postimage"]
        staged_rel = publication.get("staged_path")
        if postimage["exists"]:
            staged_path = _inside(project, staged_rel, allow_missing=False)
            if not _matches_image(staged_path, postimage):
                raise ControlPlaneRefusal("CPT-RECOVERY-REQUIRED", f"staged member bytes changed: {staged_rel}")
        elif staged_rel is not None:
            raise ControlPlaneRefusal("CPT-RECOVERY-REQUIRED", "delete member has staged bytes")
    for invalidation in record["publication_manifest"].get("invalidations", []):
        staged_path = _inside(project, invalidation["staged_path"], allow_missing=False)
        if not _matches_image(staged_path, invalidation["destination"]["postimage"]):
            raise ControlPlaneRefusal(
                "CPT-RECOVERY-REQUIRED", f"staged invalidation changed: {invalidation['receipt_id']}"
            )


def _current_class(path: Path, preimage: dict[str, Any], postimage: dict[str, Any]) -> str:
    if _matches_image(path, preimage):
        return "preimage"
    if _matches_image(path, postimage):
        return "postimage"
    return "foreign"


def _snapshot_classes(project: Path, record: dict[str, Any]) -> list[tuple[str, str, Path]]:
    rows: list[tuple[str, str, Path]] = []
    for member in record["members"]:
        target = _inside(project, member["path"])
        rows.append((member["member"], _current_class(target, member["preimage"], member["postimage"]), target))
    for row in record["publication_manifest"].get("invalidations", []):
        for side in ("source", "destination"):
            target = _inside(project, row[side]["path"])
            rows.append(
                (
                    f"authority:{row['authority_kind']}:{row['receipt_id']}:{side}",
                    _current_class(
                        target, row[side]["preimage"], row[side]["postimage"]
                    ),
                    target,
                )
            )
    return rows


def _marker_bytes(record: dict[str, Any], manifest_bytes: bytes) -> bytes:
    return _canonical(
        {
            "schema_version": "1.0.0",
            "transition_id": record["transition_id"],
            "postimage_digest": record["postimage_digest"],
            "authority_digest": _authority_digest(record),
            "authority_epoch": _claim_event(record, "authority_epoch:"),
            "claim_nonce": _claim_event(record, "claim_nonce:"),
            "publication_manifest_sha256": _sha_bytes(manifest_bytes),
            "journal_sha256": _sha_bytes(_canonical(record["journal"])),
            "invalidated_authority": sorted(
                f"{row['authority_kind']}:{row['receipt_id']}"
                for row in record["superseded_authority"]
            ),
        }
    )


def _verify_committed(project: Path, paths: dict[str, Path], record: dict[str, Any]) -> None:
    if not paths["marker"].is_file() or _is_link(paths["marker"]):
        raise ControlPlaneRefusal("CPT-PUBLICATION-INCOMPLETE", "commit marker is absent")
    marker_data = paths["marker"].read_bytes()
    marker_binding = record.get("commit_marker")
    expected_path = paths["marker"].relative_to(project).as_posix()
    if not isinstance(marker_binding, dict) or marker_binding != _binding(expected_path, marker_data):
        raise ControlPlaneRefusal("CPT-PUBLICATION-INCOMPLETE", "commit marker binding is stale")
    marker = _load_json(paths["marker"])
    manifest_data = paths["manifest"].read_bytes()
    journal_data = paths["journal"].read_bytes()
    if (
        marker.get("transition_id") != record["transition_id"]
        or marker.get("postimage_digest") != record["postimage_digest"]
        or marker.get("authority_digest") != _authority_digest(record)
        or marker.get("authority_epoch") != _claim_event(record, "authority_epoch:")
        or marker.get("claim_nonce") != _claim_event(record, "claim_nonce:")
        or marker.get("publication_manifest_sha256") != _sha_bytes(manifest_data)
        or manifest_data != _canonical(record["publication_manifest"])
        or marker.get("journal_sha256") != _sha_bytes(journal_data)
        or journal_data != _canonical(record["journal"])
    ):
        raise ControlPlaneRefusal("CPT-PUBLICATION-INCOMPLETE", "commit marker content is stale")
    if any(kind != "postimage" for _, kind, _ in _snapshot_classes(project, record)):
        raise ControlPlaneRefusal("CPT-PUBLICATION-INCOMPLETE", "committed postimage replay failed")
    if _member_digest(record, "postimage") != record["postimage_digest"]:
        raise ControlPlaneRefusal("CPT-PUBLICATION-INCOMPLETE", "postimage digest replay failed")


def _validate_locked(project: Path, transition_id: str) -> dict[str, Any]:
    capability = _guard(project)
    paths, record = _load_record(project, transition_id)
    if record["destination_capability"] != capability:
        raise ControlPlaneRefusal("CPT-IDENTITY-SPLIT", "destination capability changed")
    if _member_digest(record, "preimage") != record["preimage_digest"] or _member_digest(record, "postimage") != record["postimage_digest"]:
        raise ControlPlaneRefusal("CPT-IDENTITY-SPLIT", "transaction image digest is stale")
    _verify_staged(project, record)
    if record["state"] == "committed":
        _verify_committed(project, paths, record)
        return {"verdict": "committed", "findings": [], "record": record}
    claim = _read_claim(project)
    if claim is None:
        raise ControlPlaneRefusal("CPT-RECOVERY-REQUIRED", "noncommitted transition claim is absent")
    _assert_claim_binding(record, claim)
    if record["state"] in {"recovery_required", "invalidated"}:
        raise ControlPlaneRefusal(
            "CPT-RECOVERY-REQUIRED", f"transaction state requires recovery: {record['state']}"
        )
    classes = _snapshot_classes(project, record)
    foreign = [name for name, kind, _ in classes if kind == "foreign"]
    post = [name for name, kind, _ in classes if kind == "postimage"]
    if foreign:
        raise ControlPlaneRefusal("CPT-PREIMAGE-STALE", f"foreign current bytes: {', '.join(foreign)}")
    if post:
        raise ControlPlaneRefusal("CPT-PUBLICATION-INCOMPLETE", f"partial publication without marker: {', '.join(post)}")
    _assert_pre_authority_epoch(project, record, claim)
    return {"verdict": "validated", "findings": [], "record": record}


def validate(project_root: Path | str, transition_id: str) -> dict[str, Any]:
    project = Path(project_root).absolute()
    _guard(project)
    with _authority_lock(project):
        return _validate_locked(project, transition_id)


def _write_effect(target: Path, staged: Path | None, postimage: dict[str, Any]) -> None:
    if postimage["exists"]:
        if staged is None:
            raise ControlPlaneRefusal("CPT-RECOVERY-REQUIRED", "staged path is absent")
        _atomic_write(target, staged.read_bytes())
    elif target.exists() or target.is_symlink():
        if _is_link(target) or not target.is_file():
            raise ControlPlaneRefusal("CPT-DESTINATION-PROTECTED", f"delete target is not a plain file: {target}")
        target.unlink()


def _persist_progress(paths: dict[str, Path], record: dict[str, Any], effect: str) -> None:
    completed = record["publication_manifest"].setdefault("completed_effects", [])
    if effect not in completed:
        completed.append(effect)
    _write_support(paths, record)


def _publish_locked(
    project: Path,
    transition_id: str,
    *,
    recovery: bool,
    crash_after_effects: int | None,
    crash_before_marker: bool,
) -> dict[str, Any]:
    capability = _guard(project)
    paths, record = _load_record(project, transition_id)
    if record["destination_capability"] != capability:
        raise ControlPlaneRefusal("CPT-IDENTITY-SPLIT", "destination capability changed")
    if paths["marker"].is_file():
        _verify_committed(project, paths, record)
        claim = _read_claim(project)
        if claim is not None:
            claim = _bound_claim(
                project, record, state="publishing", allow_adopt_dead=True
            )
            _release_claim(project, claim["nonce"])
        return record
    if record["state"] == "invalidated":
        raise ControlPlaneRefusal("CPT-RECOVERY-REQUIRED", "invalidated transaction cannot publish")
    if record["state"] == "recovery_required" and not recovery:
        raise ControlPlaneRefusal("CPT-RECOVERY-REQUIRED", "explicit recover is required")
    if record["state"] == "committed" and not recovery:
        raise ControlPlaneRefusal("CPT-PUBLICATION-INCOMPLETE", "committed record lacks marker; recover required")
    claim = _bound_claim(
        project,
        record,
        state="recovering" if recovery else "publishing",
        allow_adopt_dead=True,
    )
    _verify_staged(project, record)
    classes = _snapshot_classes(project, record)
    foreign = [name for name, kind, _ in classes if kind == "foreign"]
    already_post = [name for name, kind, _ in classes if kind == "postimage"]
    if foreign:
        code = "CPT-RECOVERY-REQUIRED" if recovery or already_post else "CPT-PREIMAGE-STALE"
        raise ControlPlaneRefusal(code, f"foreign current bytes: {', '.join(foreign)}")
    if already_post and not recovery:
        raise ControlPlaneRefusal(
            "CPT-PUBLICATION-INCOMPLETE", "partial publication requires explicit recover"
        )
    current_classes = {name: kind for name, kind, _ in classes}
    _assert_current_authority_epoch(project, record, claim, current_classes)
    record["commit_marker"] = None
    record["state"] = "publishing"
    record["journal"]["state"] = "publishing"
    record["journal"].setdefault("events", []).append("recovery_started" if recovery else "publication_started")
    record["publication_manifest"]["state"] = "publishing"
    _write_support(paths, record)
    effects = 0
    publications = {
        row["member"]: row for row in record["publication_manifest"]["member_publications"]
    }
    current = {name: kind for name, kind, _ in _snapshot_classes(project, record)}
    _assert_current_authority_epoch(project, record, claim, current)
    for member in record["members"]:
        name = member["member"]
        if current[name] != "postimage":
            row = publications[name]
            target = _inside(project, member["path"])
            staged = _inside(project, row["staged_path"], allow_missing=False) if row.get("staged_path") else None
            _write_effect(target, staged, member["postimage"])
            _persist_progress(paths, record, f"member:{name}")
            effects += 1
            if crash_after_effects is not None and effects == crash_after_effects:
                raise ControlPlaneRefusal("CPT-PUBLICATION-INCOMPLETE", "synthetic crash before marker")
    current = {name: kind for name, kind, _ in _snapshot_classes(project, record)}
    for row in record["publication_manifest"].get("invalidations", []):
        source_name = f"authority:{row['authority_kind']}:{row['receipt_id']}:source"
        destination_name = f"authority:{row['authority_kind']}:{row['receipt_id']}:destination"
        if current[source_name] == "postimage" and current[destination_name] == "preimage":
            raise ControlPlaneRefusal(
                "CPT-RECOVERY-REQUIRED",
                f"authority source vanished before invalidated copy: {row['receipt_id']}",
            )
        if current[destination_name] != "postimage":
            destination = _inside(project, row["destination"]["path"])
            staged = _inside(project, row["staged_path"], allow_missing=False)
            _write_effect(destination, staged, row["destination"]["postimage"])
            _persist_progress(paths, record, destination_name)
            effects += 1
            if crash_after_effects is not None and effects == crash_after_effects:
                raise ControlPlaneRefusal("CPT-PUBLICATION-INCOMPLETE", "synthetic crash before marker")
        if current[source_name] != "postimage":
            source = _inside(project, row["source"]["path"])
            _write_effect(source, None, row["source"]["postimage"])
            _persist_progress(paths, record, source_name)
            effects += 1
            if crash_after_effects is not None and effects == crash_after_effects:
                raise ControlPlaneRefusal("CPT-PUBLICATION-INCOMPLETE", "synthetic crash before marker")
    if any(kind != "postimage" for _, kind, _ in _snapshot_classes(project, record)):
        raise ControlPlaneRefusal("CPT-RECOVERY-REQUIRED", "postimage replay incomplete")
    _assert_post_authority_epoch(project, record)
    record["publication_manifest"]["state"] = "published"
    record["journal"]["state"] = "committed"
    record["journal"].setdefault("events", []).append("all_effects_verified")
    manifest_bytes = _canonical(record["publication_manifest"])
    journal_bytes = _canonical(record["journal"])
    _atomic_write(paths["manifest"], manifest_bytes)
    _atomic_write(paths["journal"], journal_bytes)
    marker_bytes = _marker_bytes(record, manifest_bytes)
    marker_rel = paths["marker"].relative_to(project).as_posix()
    record["state"] = "committed"
    record["commit_marker"] = _binding(marker_rel, marker_bytes)
    _schema_check(record)
    _atomic_write(paths["record"], _canonical(record))
    if crash_before_marker:
        raise ControlPlaneRefusal("CPT-PUBLICATION-INCOMPLETE", "synthetic crash immediately before marker")
    _atomic_write(paths["marker"], marker_bytes)
    _verify_committed(project, paths, record)
    _release_claim(project, claim["nonce"])
    return record


def publish(
    project_root: Path | str,
    transition_id: str,
    *,
    crash_after_effects: int | None = None,
    crash_before_marker: bool = False,
) -> dict[str, Any]:
    project = Path(project_root).absolute()
    _guard(project)
    with _authority_lock(project):
        return _publish_locked(
            project, transition_id, recovery=False,
            crash_after_effects=crash_after_effects,
            crash_before_marker=crash_before_marker,
        )


def recover(project_root: Path | str, transition_id: str) -> dict[str, Any]:
    project = Path(project_root).absolute()
    _guard(project)
    with _authority_lock(project):
        try:
            return _publish_locked(
                project, transition_id, recovery=True,
                crash_after_effects=None, crash_before_marker=False,
            )
        except ControlPlaneRefusal as exc:
            if exc.code != "CPT-RECOVERY-REQUIRED":
                raise
            paths, record = _load_record(project, transition_id)
            record["state"] = "recovery_required"
            record["commit_marker"] = None
            record["journal"]["state"] = "recovery_required"
            record["journal"].setdefault("events", []).append("foreign_bytes_refused")
            record["publication_manifest"]["state"] = "recovery_required"
            _write_support(paths, record)
            raise


def verify_committed(project_root: Path | str, transition_id: str) -> dict[str, Any]:
    project = Path(project_root).absolute()
    _guard(project)
    paths, record = _load_record(project, transition_id)
    _verify_committed(project, paths, record)
    return {"verdict": "committed", "findings": [], "record": record}


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "validate", "publish", "recover"):
        command = sub.add_parser(name)
        command.add_argument("--project-root", type=Path, required=True)
        command.add_argument("--transition-id", required=True)
        if name == "prepare":
            command.add_argument("--plan", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            result = prepare(args.project_root, _load_json(args.plan), args.transition_id)
        elif args.command == "validate":
            result = validate(args.project_root, args.transition_id)
        elif args.command == "publish":
            result = publish(args.project_root, args.transition_id)
        else:
            result = recover(args.project_root, args.transition_id)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except ControlPlaneRefusal as exc:
        print(f"[BLOCKER] {exc.code}: {exc.message}")
        return 1


if __name__ == "__main__":
    raise SystemExit(_main())
