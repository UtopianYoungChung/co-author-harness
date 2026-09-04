#!/usr/bin/env python3
"""Planner-owned, fail-closed assignment milestone transactions.

``reviews/phase_state.json`` remains the sole lifecycle authority.  F9 is
published before an accepting state update; every authoritative state write is
an atomic, state-last replacement guarded by a separate lifecycle claim.
"""

from __future__ import annotations

import copy
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
import platform
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Any, Callable, Iterator
import uuid

from assignment_process_gate import (
    derive_receipt_authority,
    derive_released_export_path,
    named_draft_permitted,
    verify_receipt,
)
from assignment_receipt_transaction import ReceiptTransactionError, validate_mutation_target
from destination_capability import (
    guard_lifecycle_project_root,
    guard_project_root,
    guard_repin_project_root,
)
from draft_evidence_verifier import VerifierError, validate_lifecycle_verifier_binding
from milestone_framework_validate import (
    validate_document,
    validate_gate,
    validate_scholarly_authority_chain,
)
from milestone_handoff_policy import (
    AUDITED_POLICY,
    DERIVED_POLICY,
    HandoffPolicyResolutionError,
    resolve_handoff_policy,
)
from milestone_path_contract import handoff_path, snapshot_path
from scholarly_evaluation_binding import (
    ScholarlyBindingError,
    validate_scholarly_binding,
)


ROOT = Path(__file__).resolve().parents[1]
MILESTONES = ("M1", "M2", "M3", "M4", "M5")
PUBLIC_TO_LEDGER = {"M1": "M1", "M2": "M2", "M3": "M3", "M4": "M4", "FINAL": "M5"}
LEDGER_TO_PUBLIC = {value: key for key, value in PUBLIC_TO_LEDGER.items()}
SUCCESSOR = {"M1": "M2", "M2": "M3", "M3": "M4", "M4": "M5", "M5": None}
PREDECESSOR = {"M2": "M1", "M3": "M2", "M4": "M3", "M5": "M4"}
ARTIFACT_KIND = {
    "M1": "project_memo",
    "M2": "annotated_references",
    "M3": "structured_outline",
    "M4": "manuscript",
    "M5": "manuscript",
}
STABLE_POLICY_KEYS = (
    "profile_path", "profile_sha256", "resolved_sha256",
    "attestation_view_pin", "exemplar_view_pin",
)
READER_PROFILE_POLICY_KEYS = (
    "profile_path", "profile_sha256", "resolved_sha256", "semantic_usage",
)
UTC_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z$")
CYCLE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
CHECKPOINT_FIELDS = {
    "schema_version", "milestone", "feedback_records", "inputs_consumed",
    "decisions_frozen", "open_debts", "next_milestone_instructions",
    "policy_evidence",
}
APPROVAL_FIELDS = {
    "schema_version", "status", "milestone", "authority", "approved_at",
    "deliverable",
}
M4_ACCEPTANCE_POLICY_FIELDS = {
    "schema_version", "milestone", "manuscript_sha256", "phase", "cycle_id",
    "check8_path", "check8_sha256", "aggregate_verdict",
}
M5_TERMINAL_POLICY_FIELDS = {
    "schema_version", "milestone", "terminal_round_id", "manuscript_sha256",
    "phase", "cycle_id", "check8_path", "check8_sha256",
    "aggregate_verdict", "bindings",
}
TERMINAL_BINDING_ROLES = {
    "g4_signoff", "ship_signoff", "final_round_report", "reflector_full",
    "f7_evidence", "events_log", "findings", "convergence_log",
}
FEEDBACK_FIELDS = {
    "feedback_id", "evidence_class", "source_path", "source_sha256",
    "source_actor", "source_authority", "source_milestone",
    "target_milestone", "received_at", "contemporaneity_evidence_path",
    "contemporaneity_evidence_sha256", "lineage_id", "blocking",
    "disposition", "rationale", "successor_effect",
}
AUTHORITIES = {"user", "venue", "advisor", "instructor", "committee", "project_local_contract"}
DISPOSITIONS = {"accepted", "partially_accepted", "rejected", "deferred", "informational"}


class MilestoneTransactionError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dependency_snapshot(project: Path, paths: list[Path]) -> dict[str, tuple[str, int]]:
    snapshot: dict[str, tuple[str, int]] = {}
    project_root = project.resolve()
    harness_root = ROOT.resolve()
    for supplied in paths:
        path = supplied.resolve()
        if path.is_relative_to(project_root):
            root = project_root
        elif path.is_relative_to(harness_root):
            root = harness_root
        else:
            raise MilestoneTransactionError(
                "AMC-DEPENDENCY",
                f"dependency escapes the governed project and harness roots: {path}",
            )
        relative = path.relative_to(root)
        current = root
        for part in relative.parts:
            current = current / part
            if _is_link(current):
                raise MilestoneTransactionError("AMC-DEPENDENCY", f"dependency traverses a symlink or junction: {relative.as_posix()}")
        if not path.is_file():
            raise MilestoneTransactionError("AMC-DEPENDENCY", f"dependency is not a plain file: {relative.as_posix()}")
        snapshot[str(path)] = (_sha256(path), path.stat().st_size)
    return snapshot


def _recheck_dependencies(project: Path, snapshot: dict[str, tuple[str, int]]) -> None:
    current = _dependency_snapshot(project, [Path(path) for path in snapshot])
    if current != snapshot:
        raise MilestoneTransactionError("AMC-DEPENDENCY-CHANGED", "a bound receipt, result, artifact, checkpoint, feedback, approval, or policy file changed during the transaction")


def _scholarly_dependency_expectations(
    scholarly: dict[str, Any],
) -> dict[str, tuple[str, int]]:
    expected: dict[str, tuple[str, int]] = {}
    for row in scholarly["dependencies"]:
        path = str(Path(row["path"]).resolve())
        value = (row["sha256"], row["byte_length"])
        prior = expected.get(path)
        if prior is not None and prior != value:
            raise MilestoneTransactionError(
                "AMC-SCHOLARLY-EVALUATION-STALE",
                f"scholarly dependency inventory splits one path: {path}",
            )
        expected[path] = value
    return expected


def _assert_scholarly_dependency_snapshot(
    snapshot: dict[str, tuple[str, int]], scholarly: dict[str, Any]
) -> None:
    expected = _scholarly_dependency_expectations(scholarly)
    if any(snapshot.get(path) != value for path, value in expected.items()):
        raise MilestoneTransactionError(
            "AMC-SCHOLARLY-EVALUATION-STALE",
            "a scholarly evaluation dependency is absent or differs from the qualified C6 read set",
        )


def _recheck_scholarly_dependencies(
    project: Path, scholarly: dict[str, Any]
) -> None:
    expected = _scholarly_dependency_expectations(scholarly)
    current = _dependency_snapshot(project, [Path(path) for path in expected])
    if current != expected:
        raise MilestoneTransactionError(
            "AMC-SCHOLARLY-EVALUATION-STALE",
            "a scholarly evaluation dependency changed during the milestone transaction",
        )


def _scholarly_core(scholarly: dict[str, Any]) -> dict[str, Any]:
    return {
        key: scholarly[key]
        for key in (
            "binding", "artifact", "evaluation_id", "status",
            "judgment_truth_certified", "dependencies",
        )
    }


def _revalidate_scholarly_binding(project: Path, scholarly: dict[str, Any]) -> None:
    try:
        current = validate_scholarly_binding(
            project_root=project,
            artifact=scholarly["artifact_path"],
            binding=scholarly["binding"],
        )
    except ScholarlyBindingError as exc:
        raise MilestoneTransactionError(
            "AMC-SCHOLARLY-EVALUATION-STALE",
            f"{exc.code}: {exc.message}",
        ) from exc
    if _scholarly_core(current) != _scholarly_core(scholarly):
        raise MilestoneTransactionError(
            "AMC-SCHOLARLY-EVALUATION-STALE",
            "scholarly evaluation result changed during the milestone transaction",
        )
    _assert_scholarly_authority_chain(
        project,
        scholarly["_draft_results"],
        current,
        scholarly["_authority_receipt_id"],
    )


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _load_object(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MilestoneTransactionError(code, f"cannot read valid JSON object from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise MilestoneTransactionError(code, f"JSON evidence must be an object: {path}")
    return value


def _is_link(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        attributes = getattr(os.lstat(path), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400))


def _control_root(project: Path) -> Path:
    return project / "reviews" / ".harness" / "milestones"


def _ensure_control_tree(project: Path) -> Path:
    root = _control_root(project)
    for directory in (
        project / "reviews", project / "reviews" / ".harness", root,
        root / "claims", root / "journal", root / "checkpoints",
    ):
        if directory.exists() and (not directory.is_dir() or _is_link(directory)):
            raise MilestoneTransactionError("AMC-PATH-INVALID", f"lifecycle control path is not a plain directory: {directory}")
        directory.mkdir(parents=True, exist_ok=True)
        if _is_link(directory):
            raise MilestoneTransactionError("AMC-PATH-INVALID", f"lifecycle control path is linked or junctioned: {directory}")
    return root


def _safe_project_file(project: Path, raw: Any, code: str) -> tuple[Path, str]:
    if not isinstance(raw, str) or not raw or "\\" in raw or ":" in raw:
        raise MilestoneTransactionError(code, f"unsafe project-relative path: {raw!r}")
    relative = PurePosixPath(raw)
    if relative.is_absolute() or any(part in {".", ".."} for part in relative.parts):
        raise MilestoneTransactionError(code, f"unsafe project-relative path: {raw!r}")
    current = project.resolve()
    for part in relative.parts:
        current = current / part
        if current.exists() and _is_link(current):
            raise MilestoneTransactionError(code, f"path traverses a symlink or junction: {raw}")
    resolved = (project / Path(*relative.parts)).resolve(strict=False)
    try:
        resolved.relative_to(project.resolve())
    except ValueError as exc:
        raise MilestoneTransactionError(code, f"path escapes project root: {raw}") from exc
    if not resolved.is_file() or _is_link(resolved):
        raise MilestoneTransactionError(code, f"required evidence is not a plain file: {raw}")
    return resolved, relative.as_posix()


def _supplied_project_file(project: Path, supplied: Path, code: str) -> tuple[Path, str]:
    try:
        relative = supplied.resolve().relative_to(project.resolve()).as_posix()
    except (OSError, ValueError) as exc:
        raise MilestoneTransactionError(code, "evidence path must be contained by the project root") from exc
    return _safe_project_file(project, relative, code)


def _atomic_replace(path: Path, payload: dict[str, Any]) -> None:
    if _is_link(path.parent):
        raise MilestoneTransactionError("AMC-PATH-INVALID", f"state parent is linked or junctioned: {path.parent}")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    original_mode: int | None = None
    target_unlocked = False
    if path.exists():
        original_mode = stat.S_IMODE(path.stat().st_mode)
    try:
        with temporary.open("xb") as handle:
            handle.write(_json_bytes(payload))
            handle.flush()
            os.fsync(handle.fileno())
        if original_mode is not None:
            os.chmod(temporary, original_mode)
            if not (original_mode & stat.S_IWRITE):
                os.chmod(path, original_mode | stat.S_IWRITE)
                target_unlocked = True
        try:
            os.replace(temporary, path)
        except BaseException:
            if target_unlocked and path.exists():
                os.chmod(path, original_mode)
            raise
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _exclusive_bytes(path: Path, data: bytes) -> bool:
    """Publish exact bytes without overwrite; return True only when created."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if not path.is_file() or _is_link(path) or path.read_bytes() != data:
            raise MilestoneTransactionError("AMC-F9-CONFLICT", f"existing F9 bytes conflict: {path}")
        return False
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if not path.is_file() or path.read_bytes() != data:
                raise MilestoneTransactionError("AMC-F9-CONFLICT", f"concurrent F9 bytes conflict: {path}")
            return False
        return True
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _timestamp(value: str | None = None) -> str:
    value = value or datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    if not isinstance(value, str) or UTC_RE.fullmatch(value) is None:
        raise MilestoneTransactionError("AMC-TIMESTAMP", "timestamp must be RFC3339 UTC ending in Z")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise MilestoneTransactionError("AMC-TIMESTAMP", f"invalid UTC timestamp: {value}") from exc
    return value


def _utc_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value[:-1] + "+00:00")


def _load_state(project: Path) -> tuple[Path, dict[str, Any], str]:
    path = project / "reviews" / "phase_state.json"
    if not path.is_file() or _is_link(path):
        raise MilestoneTransactionError("AMC-PHASE-STATE", f"phase state is missing, linked, or not a file: {path}")
    return path, _load_object(path, "AMC-PHASE-STATE"), _sha256(path)


def _framework(state: dict[str, Any]) -> dict[str, Any]:
    framework = state.get("milestone_framework")
    milestones = framework.get("milestones") if isinstance(framework, dict) else None
    if not isinstance(framework, dict) or not isinstance(milestones, dict):
        raise MilestoneTransactionError("AMC-PHASE-STATE", "native milestone framework is missing")
    return framework


def _effective_handoff_policy(framework: dict[str, Any]) -> str:
    """Resolve the authoritative handoff policy without rewriting the ledger."""

    try:
        return resolve_handoff_policy(framework)["effective_policy"]
    except HandoffPolicyResolutionError as exc:
        raise MilestoneTransactionError(
            exc.code, f"{exc.path}: {exc.message}"
        ) from exc


_ACTIVE_AUTHORITY_MODE = "direct_local"


def _authority_mode_for(project: Path) -> str:
    """shipment_only inside the governed staging lane; direct_local elsewhere.

    Producer-boundary Phase E: staging is production territory (freely
    revisable, proposal-only stamping); everywhere else keeps the historical
    direct-local transaction semantics unchanged. Assignment profile, run
    scope, and (reserved-empty) operating mode are separate dimensions.
    """
    from destination_capability import classify
    return "shipment_only" if classify(project) == "staging" else "direct_local"


def _enter_authority_mode(project: Path) -> str:
    global _ACTIVE_AUTHORITY_MODE
    _ACTIVE_AUTHORITY_MODE = _authority_mode_for(project)
    return _ACTIVE_AUTHORITY_MODE


def _append_event(
    framework: dict[str, Any], event_type: str, milestone: str, at: str, reason: str,
    *, authority: str | None = None, evidence_path: str | None = None,
    evidence_sha256: str | None = None, bindings: list[dict[str, str]] | None = None,
) -> None:
    events = framework.get("events")
    if not isinstance(events, list):
        raise MilestoneTransactionError("AMC-PHASE-STATE", "milestone event stream is invalid")
    if events and at < str(events[-1].get("timestamp", "")):
        raise MilestoneTransactionError("AMC-TIMESTAMP", "event time must not precede the latest milestone event")
    row = {
        "sequence": len(events) + 1,
        "event_type": event_type,
        "timestamp": at,
        "milestone": milestone,
        "lineage_id": framework.get("primary_lineage"),
        "actor": "planner",
        "authority": authority,
        "reason": reason,
        "evidence_path": evidence_path,
        "evidence_sha256": evidence_sha256,
        "caused_by_sequence": None,
        "bindings": bindings or [],
    }
    if _ACTIVE_AUTHORITY_MODE == "shipment_only":
        # Producer boundary: everything written from the staging lane is a
        # production proposal, never research authority.
        row["effect_scope"] = "proposal_only"
    events.append(row)


def _validate_prospective(project: Path, state: dict[str, Any]) -> None:
    result = validate_document(project, state)
    if not result.exit_permitted:
        detail = "; ".join(f"{row.code} at {row.path}: {row.message}" for row in result.findings[:6])
        raise MilestoneTransactionError("AMC-STATE-INVALID", detail or "prospective milestone state is invalid")


@contextmanager
def transaction_claim(project: Path, operation: str) -> Iterator[None]:
    try:
        from control_plane_transition import ControlPlaneRefusal, authority_issuance_guard

        with authority_issuance_guard(
            project, allow_repin_container=operation.startswith("rebind:"),
        ):
            root = _ensure_control_tree(project)
            claim = root / "claims" / "transaction.lock"
            payload = {
                "schema_version": "1.0.0", "pid": os.getpid(), "host": platform.node(),
                "operation": operation, "started_at": _timestamp(),
            }
            try:
                with claim.open("xb") as handle:
                    handle.write(_json_bytes(payload)); handle.flush(); os.fsync(handle.fileno())
            except FileExistsError as exc:
                raise MilestoneTransactionError("AMC-IN-USE", "another milestone transition is already in progress; inspect and recover explicitly") from exc
            try:
                yield
            finally:
                try:
                    claim.unlink()
                except FileNotFoundError:
                    pass
    except ControlPlaneRefusal as exc:
        raise MilestoneTransactionError(exc.code, exc.message) from exc


def _restore_exact_bytes(path: Path, payload: bytes) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.rollback.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _activate_unavailable_reader_accessibility(
    project: Path,
    state_path: Path,
    state: dict[str, Any],
    prehash: str,
    framework: dict[str, Any],
    old_binding: dict[str, Any],
    at: str,
    policy: Any,
) -> Path:
    """Explicitly migrate the legacy graph-coupled fallback to reader-profile v2."""
    milestones = framework.get("milestones")
    m1 = milestones.get("M1") if isinstance(milestones, dict) else None
    m1_approval = m1.get("approval") if isinstance(m1, dict) else None
    m1_handoff = m1.get("handoff") if isinstance(m1, dict) else None
    if (
        not isinstance(m1, dict)
        or m1.get("status") != "in_progress"
        or not isinstance(m1_approval, dict)
        or m1_approval.get("status") != "pending"
        or not isinstance(m1_handoff, dict)
        or m1_handoff.get("status") != "not_ready"
        or any(
            isinstance(milestones.get(name), dict)
            and milestones[name].get("status") not in {"not_started", "not_applicable"}
            for name in ("M2", "M3", "M4", "M5")
        )
    ):
        raise MilestoneTransactionError(
            "AMC-REPIN-UNAVAILABLE-STATE",
            "legacy unavailable reader policy can be migrated only during unaccepted M1 before successor work",
        )
    resolved_relative = old_binding.get("resolved_path")
    if not isinstance(resolved_relative, str):
        raise MilestoneTransactionError("AMC-REPIN-POLICY", "existing resolved policy path is invalid")
    resolved_path = (project / Path(*PurePosixPath(resolved_relative).parts)).resolve()
    try:
        resolved_path.relative_to(project)
    except ValueError as exc:
        raise MilestoneTransactionError("AMC-REPIN-POLICY", "resolved policy path escapes project root") from exc
    if not resolved_path.is_file() or _is_link(resolved_path) or _is_link(resolved_path.parent):
        raise MilestoneTransactionError("AMC-REPIN-POLICY", "resolved policy path is absent or linked")
    old_resolved = resolved_path.read_bytes()
    if hashlib.sha256(old_resolved).hexdigest() != old_binding.get("resolved_sha256"):
        raise MilestoneTransactionError("AMC-REPIN-POLICY", "unavailable resolver artifact hash is stale")
    try:
        old_payload = json.loads(old_resolved)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MilestoneTransactionError("AMC-REPIN-POLICY", f"unavailable resolver artifact is invalid: {exc}") from exc
    if (
        not isinstance(old_payload, dict)
        or old_payload.get("availability") != "semantic_graph_unavailable"
        or old_payload.get("blocker") != old_binding.get("blocker")
        or old_payload.get("source_bindings") != old_binding.get("source_bindings")
    ):
        raise MilestoneTransactionError("AMC-REPIN-POLICY", "unavailable resolver artifact and binding disagree")

    try:
        fresh = policy.resolve_reader_profile(project)
    except policy.PolicyError as exc:
        raise MilestoneTransactionError(
            "AMC-REPIN-POLICY", f"reader-profile migration cannot resolve policy sources: {exc}",
        ) from exc

    old_state_bytes = state_path.read_bytes()
    activation_id = f"reader-policy-activation-{uuid.uuid4()}"
    receipt = project / "reviews" / f"{activation_id}.applied.json"
    receipt_created = False
    try:
        _atomic_replace(resolved_path, fresh)
        binding = policy.reader_profile_phase_state_binding(fresh, resolved_path, project)
        binding["transitions"] = copy.deepcopy(old_binding["transitions"])
        proposed = copy.deepcopy(state)
        _framework(proposed)["policy_bindings"]["reader_accessibility"] = binding
        if _sha256(state_path) != prehash:
            raise MilestoneTransactionError("AMC-CONCURRENT-CHANGE", "phase state changed during reader-policy activation")
        validation = validate_document(project, proposed)
        if validation.findings:
            first = validation.findings[0]
            raise MilestoneTransactionError(
                "AMC-REPIN-VALIDATION",
                f"activated reader policy failed canonical validation: {first.code} {first.path}: {first.message}",
            )
        posthash = hashlib.sha256(_json_bytes(proposed)).hexdigest()
        activation = {
            "schema_version": "2.0.0",
            "activation_id": activation_id,
            "status": "applied",
            "applied_at": at,
            "applied_by": "planner",
            "prior": {
                "availability": old_binding["availability"],
                "resolved_sha256": old_binding["resolved_sha256"],
                "graph_sha256": old_binding["blocker"]["graph_sha256"],
            },
            "current": {
                "profile_sha256": binding["profile_sha256"],
                "resolved_sha256": binding["resolved_sha256"],
                "binding_version": binding["binding_version"],
                "semantic_usage": binding["semantic_usage"],
            },
            "phase_state": {"pre_sha256": prehash, "post_sha256": posthash},
        }
        _atomic_replace(state_path, proposed)
        receipt_created = _exclusive_bytes(receipt, _json_bytes(activation))
        if _sha256(state_path) != posthash or _sha256(resolved_path) != binding["resolved_sha256"]:
            raise MilestoneTransactionError("AMC-REPIN-READBACK", "reader-policy activation read-back failed")
        return receipt
    except Exception:
        if receipt_created:
            receipt.unlink(missing_ok=True)
        if state_path.read_bytes() != old_state_bytes:
            _restore_exact_bytes(state_path, old_state_bytes)
        if resolved_path.read_bytes() != old_resolved:
            _restore_exact_bytes(resolved_path, old_resolved)
        raise


def _refresh_reader_profile_v2(
    project: Path,
    state_path: Path,
    state: dict[str, Any],
    prehash: str,
    framework: dict[str, Any],
    old_binding: dict[str, Any],
    at: str,
    policy: Any,
) -> Path:
    """Refresh an already-v2 reader-profile binding whose bound sources moved.

    A v2 binding records the exact bytes of every policy source it resolved
    against. When one of those sources legitimately changes -- a package
    contributor document is edited, or the profile is re-versioned -- the
    binding goes stale and canonical validation refuses. Before this branch
    existed the only rebind routes were the legacy `semantic_graph_unavailable`
    migration and the semantic-v1 request-driven re-pin, so a correctly formed
    v2 binding had NO route back to validity: the request path demands
    `attestation_view_pin` and `exemplar_view_pin`, which a structural-only
    corpus cannot produce. Recorded 2026-08-07.

    This is a refresh, not a re-pin. No pin is read, computed, or written; the
    semantic graph is never consulted; the re-pin ledger is not appended to.
    `semantic_usage` stays `not_invoked` throughout, so the refreshed binding
    asserts exactly as much semantic warrant as the one it replaces: none.

    Round gating is the CALLER's responsibility and is deliberately not
    duplicated here -- see `rebind_reader_accessibility`, which refuses an open
    review round before dispatching. Accepted M3-M5 evidence is separately
    immutable and refused before mutation below.
    """
    # COMPLETE shape validation before the first write. Two fields were missing
    # from the first cut and both were reachable: a binding with no
    # `profile_path` was accepted and committed, and a binding whose
    # `transitions` carried an extra key `X` was accepted and carried `{G, H,
    # VE, X}` forward. `transitions` is deep-copied into the refreshed binding
    # verbatim, so an unvalidated key here is not a cosmetic defect -- it is a
    # write of unvalidated structure into authoritative phase state. Recorded
    # 2026-08-07 from executable probes during independent review.
    transitions = old_binding.get("transitions")
    if (
        old_binding.get("binding_version") != "2.0.0"
        or old_binding.get("binding_kind") != "reader_profile"
        or old_binding.get("semantic_usage") != "not_invoked"
        or not isinstance(old_binding.get("source_bindings"), list)
        or not isinstance(old_binding.get("profile_path"), str)
        or not old_binding.get("profile_path")
        or not isinstance(old_binding.get("profile_sha256"), str)
        or not isinstance(old_binding.get("resolved_sha256"), str)
        or not isinstance(transitions, dict)
        or set(transitions) != {"G", "H", "VE"}
    ):
        raise MilestoneTransactionError("AMC-REPIN-POLICY", "v2 reader-profile binding is malformed")
    if any(
        key in old_binding
        for key in ("attestation_view_pin", "exemplar_view_pin", "graph_sha256_provenance", "pin_epoch")
    ):
        raise MilestoneTransactionError(
            "AMC-REPIN-POLICY", "v2 reader-profile binding carries semantic pin fields",
        )
    resolved_relative = old_binding.get("resolved_path")
    if not isinstance(resolved_relative, str):
        raise MilestoneTransactionError("AMC-REPIN-POLICY", "existing resolved policy path is invalid")
    resolved_path = (project / Path(*PurePosixPath(resolved_relative).parts)).resolve()
    try:
        resolved_path.relative_to(project)
    except ValueError as exc:
        raise MilestoneTransactionError("AMC-REPIN-POLICY", "resolved policy path escapes project root") from exc
    if not resolved_path.is_file() or _is_link(resolved_path) or _is_link(resolved_path.parent):
        raise MilestoneTransactionError("AMC-REPIN-POLICY", "resolved policy path is absent or linked")
    old_resolved = resolved_path.read_bytes()
    if hashlib.sha256(old_resolved).hexdigest() != old_binding.get("resolved_sha256"):
        raise MilestoneTransactionError("AMC-REPIN-POLICY", "v2 resolver artifact hash is stale")
    try:
        old_payload = json.loads(old_resolved)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MilestoneTransactionError("AMC-REPIN-POLICY", f"v2 resolver artifact is invalid: {exc}") from exc
    if (
        not isinstance(old_payload, dict)
        or old_payload.get("contract_version") != "2.0.0"
        or old_payload.get("binding_kind") != "reader_profile"
        or old_payload.get("semantic_usage") != "not_invoked"
        or old_payload.get("source_bindings") != old_binding.get("source_bindings")
    ):
        raise MilestoneTransactionError("AMC-REPIN-POLICY", "v2 resolver artifact and binding disagree")

    old_state_bytes = state_path.read_bytes()
    if hashlib.sha256(old_state_bytes).hexdigest() != prehash:
        raise MilestoneTransactionError(
            "AMC-CONCURRENT-CHANGE", "phase state changed before reader-policy refresh resolution",
        )

    try:
        fresh = policy.resolve_reader_profile(project)
    except policy.PolicyError as exc:
        raise MilestoneTransactionError(
            "AMC-REPIN-POLICY", f"reader-profile refresh cannot resolve policy sources: {exc}",
        ) from exc

    # Fail closed on a no-op rather than writing a receipt for nothing. A
    # refresh that changes no byte is not an event worth recording, and an
    # empty receipt would dilute the audit trail it exists to carry.
    fresh_bytes = _json_bytes(fresh)
    if fresh == old_payload:
        raise MilestoneTransactionError(
            "AMC-REPIN-NO-DELTA",
            "reader-profile binding already matches the current policy sources; no refresh applied",
        )

    # Accepted reader-policy evidence and its optional F9 projection are
    # immutable historical evidence.  A source refresh may update live,
    # unaccepted policy evidence, but it must never rewrite an accepted
    # checkpoint (or its packet) to make history resemble the new profile.
    # The active R5a consumer is at M1, so this guard preserves the authorized
    # repair while failing closed on the separately-designed historical
    # migration problem.
    for milestone in ("M3", "M4", "M5"):
        record = framework.get("milestones", {}).get(milestone)
        if isinstance(record, dict) and record.get("status") in {"accepted", "superseded"}:
            raise MilestoneTransactionError(
                "AMC-REPIN-ACCEPTED-EVIDENCE",
                f"{milestone} has immutable accepted reader-policy evidence; "
                "a separately authorized historical-evidence migration is required",
            )

    prior_source_bindings_digest = hashlib.sha256(
        _json_bytes({"source_bindings": old_binding["source_bindings"]})
    ).hexdigest()
    refresh_id = f"reader-policy-refresh-{uuid.uuid4()}"
    receipt = project / "reviews" / f"{refresh_id}.applied.json"
    receipt_created = False
    receipt_bytes: bytes | None = None
    resolved_write_attempted = False
    resolved_written = False
    state_write_attempted = False
    state_written = False
    state_post_bytes: bytes | None = None

    # Rebind both mutable targets immediately before the first publication.
    # The transaction claim coordinates compliant writers, but these exact
    # byte checks also fail closed on an external writer that ignores it.
    if state_path.read_bytes() != old_state_bytes or resolved_path.read_bytes() != old_resolved:
        raise MilestoneTransactionError(
            "AMC-CONCURRENT-CHANGE",
            "phase state or resolved reader policy changed before refresh publication",
        )
    try:
        # Publish the same deterministic sorted-key UTF-8 representation used
        # by the transaction's other JSON artifacts. No-delta detection above
        # compares semantic objects, so formatting alone cannot create a
        # refresh receipt.
        resolved_write_attempted = True
        _restore_exact_bytes(resolved_path, fresh_bytes)
        resolved_written = True
        binding = policy.reader_profile_phase_state_binding(fresh, resolved_path, project)
        current_source_bindings_digest = hashlib.sha256(
            _json_bytes({"source_bindings": binding["source_bindings"]})
        ).hexdigest()
        # Transition history is carried, never reset: a source refresh is not a
        # lifecycle event and must not silently discard G/H/VE observation counts.
        binding["transitions"] = copy.deepcopy(old_binding["transitions"])
        proposed = copy.deepcopy(state)
        proposed_framework = _framework(proposed)
        proposed_framework["policy_bindings"]["reader_accessibility"] = binding
        refreshed_milestone_evidence: list[str] = []
        stable_policy = {
            "profile_path": binding["resolved_path"],
            "profile_sha256": binding["profile_sha256"],
            "resolved_sha256": binding["resolved_sha256"],
            "semantic_usage": "not_invoked",
        }
        for milestone in ("M3", "M4", "M5"):
            record = proposed_framework.get("milestones", {}).get(milestone)
            if not isinstance(record, dict) or record.get("status") in {
                "not_started", "not_applicable", "legacy_unverified",
            }:
                continue
            evidence = record.get("policy_evidence")
            if not isinstance(evidence, dict):
                continue
            evidence.update(stable_policy)
            refreshed_milestone_evidence.append(milestone)
        if state_path.read_bytes() != old_state_bytes or resolved_path.read_bytes() != fresh_bytes:
            raise MilestoneTransactionError(
                "AMC-CONCURRENT-CHANGE",
                "phase state or resolved reader policy changed during refresh preparation",
            )
        validation = validate_document(project, proposed)
        if validation.findings:
            first = validation.findings[0]
            raise MilestoneTransactionError(
                "AMC-REPIN-VALIDATION",
                f"refreshed reader policy failed canonical validation: {first.code} {first.path}: "
                f"{first.message}",
            )
        posthash = hashlib.sha256(_json_bytes(proposed)).hexdigest()
        refresh = {
            "schema_version": "2.0.0",
            "refresh_id": refresh_id,
            "status": "applied",
            "applied_at": at,
            "applied_by": "planner",
            "prior": {
                "profile_sha256": old_binding["profile_sha256"],
                "resolved_sha256": old_binding["resolved_sha256"],
                "source_bindings_digest": prior_source_bindings_digest,
                "source_bindings": copy.deepcopy(old_binding["source_bindings"]),
            },
            "current": {
                "profile_sha256": binding["profile_sha256"],
                "resolved_sha256": binding["resolved_sha256"],
                "source_bindings_digest": current_source_bindings_digest,
                "binding_version": binding["binding_version"],
                "semantic_usage": binding["semantic_usage"],
                "source_bindings": copy.deepcopy(binding["source_bindings"]),
                "milestone_policy_evidence_refreshed": refreshed_milestone_evidence,
            },
            "phase_state": {"pre_sha256": prehash, "post_sha256": posthash},
        }
        state_post_bytes = _json_bytes(proposed)
        # Rebind immediately beside the authoritative state publication.  The
        # earlier preparation check cannot protect work written while canonical
        # validation and receipt assembly run.
        if state_path.read_bytes() != old_state_bytes or resolved_path.read_bytes() != fresh_bytes:
            raise MilestoneTransactionError(
                "AMC-CONCURRENT-CHANGE",
                "phase state or resolved reader policy changed immediately before state publication",
            )
        state_write_attempted = True
        _atomic_replace(state_path, proposed)
        state_written = True
        if _sha256(state_path) != posthash or _sha256(resolved_path) != binding["resolved_sha256"]:
            raise MilestoneTransactionError("AMC-REPIN-READBACK", "reader-policy refresh read-back failed")
        try:
            post_resolved = policy.resolve_reader_profile(project)
        except policy.PolicyError as exc:
            raise MilestoneTransactionError(
                "AMC-CONCURRENT-CHANGE",
                f"reader-policy sources changed during refresh: {exc}",
            ) from exc
        post_source_bindings_digest = hashlib.sha256(
            _json_bytes({"source_bindings": post_resolved["source_bindings"]})
        ).hexdigest()
        if (
            state_post_bytes is None
            or state_path.read_bytes() != state_post_bytes
            or _json_bytes(post_resolved) != fresh_bytes
            or resolved_path.read_bytes() != fresh_bytes
            or post_source_bindings_digest != current_source_bindings_digest
        ):
            raise MilestoneTransactionError(
                "AMC-CONCURRENT-CHANGE",
                "reader-policy profile or contributor bytes changed during refresh",
            )
        receipt_bytes = _json_bytes(refresh)
        receipt_created = _exclusive_bytes(receipt, receipt_bytes)
        return receipt
    except Exception as original_exc:
        recovery_conflicts: list[str] = []
        if receipt_created:
            try:
                if receipt_bytes is not None and receipt.is_file() and receipt.read_bytes() == receipt_bytes:
                    receipt.unlink()
                else:
                    recovery_conflicts.append(str(receipt))
            except OSError:
                recovery_conflicts.append(str(receipt))

        # Roll back only bytes that are still either our exact postimage or the
        # untouched preimage. A third-party post-publication change is external
        # work: preserve it and require explicit recovery instead of erasing it.
        if state_write_attempted:
            try:
                live_state = state_path.read_bytes()
                if state_post_bytes is not None and live_state == state_post_bytes:
                    _restore_exact_bytes(state_path, old_state_bytes)
                elif live_state != old_state_bytes:
                    recovery_conflicts.append(str(state_path))
            except OSError:
                recovery_conflicts.append(str(state_path))
        if resolved_write_attempted:
            try:
                live_resolved = resolved_path.read_bytes()
                if live_resolved == fresh_bytes:
                    _restore_exact_bytes(resolved_path, old_resolved)
                elif live_resolved != old_resolved:
                    recovery_conflicts.append(str(resolved_path))
            except OSError:
                recovery_conflicts.append(str(resolved_path))
        if recovery_conflicts:
            raise MilestoneTransactionError(
                "AMC-REPIN-RECOVERY-CONFLICT",
                "reader-policy refresh found external post-publication bytes; "
                "preserved them and requires explicit recovery: "
                + ", ".join(sorted(set(recovery_conflicts))),
            ) from original_exc
        raise


def rebind_reader_accessibility(project: Path, at: str | None = None) -> Path:
    """Apply a reader-policy migration or pending legacy rebind transaction.

    A legacy unavailable binding migrates directly to graph-independent v2.
    Existing semantic v1 bindings retain the request-driven re-pin flow. The
    resolver artifact is written before authoritative state, exact preimages
    are restored on failure, and transition history is retained.
    """
    import reader_accessibility_policy as policy

    project = project.resolve()
    guard_repin_project_root(project)
    _enter_authority_mode(project)
    at = _timestamp(at)
    request_path = project / "reviews" / "repin_rebind_request.json"
    profile_path = policy.DEFAULT_PROFILE.resolve()
    ledger_path = policy.ROOT / "references" / "policies" / "repin_log.jsonl"
    with transaction_claim(project, "rebind:reader_accessibility"):
        state_path, state, prehash = _load_state(project)
        framework = _framework(state)
        old_binding = framework.get("policy_bindings", {}).get("reader_accessibility")
        if not isinstance(old_binding, dict) or not isinstance(old_binding.get("transitions"), dict):
            raise MilestoneTransactionError("AMC-REPIN-POLICY", "existing reader-policy binding is invalid")
        if old_binding.get("availability") == "semantic_graph_unavailable":
            return _activate_unavailable_reader_accessibility(
                project, state_path, state, prehash, framework, old_binding, at, policy,
            )
        if policy._open_project_round(project):
            raise MilestoneTransactionError(
                "AMC-REPIN-ROUND", "reader-policy rebind requires no open review round"
            )
        # Dispatched AFTER the open-round refusal, not beside the legacy branch
        # above, which returns at its own lifecycle gate and never reaches this
        # check. A v2 refresh is refused while a review round is open; a
        # mid-round refresh requires an explicit supersede-and-restart operation
        # that this transaction does not provide. The callee separately protects
        # immutable accepted M3-M5 evidence.
        if old_binding.get("binding_version") == "2.0.0":
            return _refresh_reader_profile_v2(
                project, state_path, state, prehash, framework, old_binding, at, policy,
            )
        if not request_path.is_file() or _is_link(request_path):
            raise MilestoneTransactionError(
                "AMC-REPIN-REQUEST", "pending reader-policy rebind request is missing or linked"
            )
        request = _load_object(request_path, "AMC-REPIN-REQUEST")
        request_hash = _sha256(request_path)
        required = {
            "request_id", "pin_epoch", "profile_sha256", "attestation_view_pin",
            "exemplar_view_pin", "delta_class", "repin_log_ref", "status",
        }
        if set(request) != required or request.get("status") != "pending":
            raise MilestoneTransactionError(
                "AMC-REPIN-REQUEST", "rebind request fields or pending status are invalid"
            )
        if not profile_path.is_file() or not ledger_path.is_file():
            raise MilestoneTransactionError(
                "AMC-REPIN-POLICY", "canonical reader profile or re-pin ledger is missing"
            )
        profile = policy.load_profile(profile_path)
        expected = profile["domain_native_register"]["expected_verification"]
        profile_hash = _sha256(profile_path)
        epoch = request.get("pin_epoch")
        expected_request = {
            "profile_sha256": profile_hash,
            "attestation_view_pin": expected.get("attestation_view_pin"),
            "exemplar_view_pin": expected.get("exemplar_view_pin"),
            "pin_epoch": expected.get("pin_epoch"),
            "repin_log_ref": f"references/policies/repin_log.jsonl#epoch-{epoch}",
        }
        for key, value in expected_request.items():
            if request.get(key) != value:
                raise MilestoneTransactionError(
                    "AMC-REPIN-REQUEST", f"pending request {key} does not match the current profile"
                )
        if not isinstance(expected.get("pinned_at"), str):
            raise MilestoneTransactionError(
                "AMC-REPIN-POLICY", "current profile lacks a valid pinned_at value"
            )
        rows = []
        try:
            for line in ledger_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    row = json.loads(line)
                    if isinstance(row, dict):
                        rows.append(row)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise MilestoneTransactionError(
                "AMC-REPIN-LEDGER", f"cannot read the re-pin ledger: {exc}"
            ) from exc
        row = next((item for item in rows if item.get("epoch") == epoch), None)
        if not isinstance(row, dict):
            raise MilestoneTransactionError("AMC-REPIN-LEDGER", "request epoch is absent from re-pin ledger")
        if (
            row.get("pinned_at") != expected.get("pinned_at")
            or row.get("delta_class") != request.get("delta_class")
            or row.get("profile_sha256", {}).get("new") != profile_hash
            or row.get("attestation_view_pin", {}).get("new") != request.get("attestation_view_pin")
            or row.get("exemplar_view_pin", {}).get("new") not in {None, request.get("exemplar_view_pin")}
        ):
            raise MilestoneTransactionError(
                "AMC-REPIN-LEDGER", "request, current profile, and re-pin ledger do not form one transaction"
            )

        resolved_relative = old_binding.get("resolved_path")
        if not isinstance(resolved_relative, str):
            raise MilestoneTransactionError("AMC-REPIN-POLICY", "existing resolved policy path is invalid")
        resolved_path = (project / Path(*PurePosixPath(resolved_relative).parts)).resolve()
        try:
            resolved_path.relative_to(project)
        except ValueError as exc:
            raise MilestoneTransactionError("AMC-REPIN-POLICY", "resolved policy path escapes project root") from exc
        if _is_link(resolved_path) or _is_link(resolved_path.parent):
            raise MilestoneTransactionError("AMC-REPIN-POLICY", "resolved policy path is linked")

        fresh = policy.resolve_policy(project)
        if (
            fresh.get("profile_sha256") != profile_hash
            or fresh.get("attestation_view_pin") != request.get("attestation_view_pin")
            or fresh.get("exemplar_view_pin") != request.get("exemplar_view_pin")
        ):
            raise MilestoneTransactionError(
                "AMC-REPIN-POLICY", "fresh resolver output differs from the pending request"
            )
        old_resolved = resolved_path.read_bytes() if resolved_path.is_file() else None
        try:
            old_resolved_payload = json.loads(old_resolved) if old_resolved is not None else None
        except (UnicodeDecodeError, json.JSONDecodeError):
            old_resolved_payload = None
        old_state_bytes = state_path.read_bytes()
        profile_pre = _sha256(profile_path)
        ledger_pre = _sha256(ledger_path)
        request_pre = request_hash
        try:
            if old_resolved_payload != fresh:
                _atomic_replace(resolved_path, fresh)
            binding = policy.phase_state_binding(fresh, resolved_path, project)
            binding["transitions"] = copy.deepcopy(old_binding["transitions"])
            proposed = copy.deepcopy(state)
            proposed_framework = _framework(proposed)
            proposed_framework["policy_bindings"]["reader_accessibility"] = binding
            if _sha256(state_path) != prehash or _sha256(request_path) != request_pre:
                raise MilestoneTransactionError("AMC-CONCURRENT-CHANGE", "phase state or rebind request changed")
            if _sha256(profile_path) != profile_pre or _sha256(ledger_path) != ledger_pre:
                raise MilestoneTransactionError("AMC-CONCURRENT-CHANGE", "profile or re-pin ledger changed")
            _atomic_replace(state_path, proposed)
            applied = copy.deepcopy(request)
            applied.update({"status": "applied", "applied_at": at, "applied_by": "planner"})
            archive = project / "reviews" / f"repin_rebind_request.{epoch}.applied.json"
            archive_bytes = _json_bytes(applied)
            _exclusive_bytes(archive, archive_bytes)
            if _sha256(state_path) != hashlib.sha256(_json_bytes(proposed)).hexdigest():
                raise MilestoneTransactionError("AMC-REPIN-READBACK", "phase-state read-back failed")
            request_path.unlink()
            return archive
        except Exception:
            # State-last publication makes the common failure path recoverable.
            # If state was not published, restore the prior resolver bytes so
            # the old binding never points at new, unbound content.
            if state_path.read_bytes() == old_state_bytes:
                if old_resolved is None:
                    resolved_path.unlink(missing_ok=True)
                else:
                    temporary = resolved_path.with_name(f".{resolved_path.name}.{os.getpid()}.rollback.tmp")
                    temporary.write_bytes(old_resolved)
                    os.replace(temporary, resolved_path)
            raise


def archive_stale_reader_accessibility_request(
    project: Path, expected_request_sha256: str, at: str | None = None,
) -> Path:
    """Archive an inert rebind request without changing lifecycle state.

    A request matching the current profile is live and must go through the
    ordinary rebind transaction. Only a hash-bound request that differs from
    the current profile may be archived by this explicit Planner recovery.
    """
    import reader_accessibility_policy as policy

    project = project.resolve()
    guard_repin_project_root(project)
    _enter_authority_mode(project)
    at = _timestamp(at)
    if not isinstance(expected_request_sha256, str) or SHA_RE.fullmatch(expected_request_sha256) is None:
        raise MilestoneTransactionError(
            "AMC-REPIN-REQUEST-HASH", "expected request sha256 must be 64 lowercase hex characters"
        )
    request_path = project / "reviews" / "repin_rebind_request.json"
    with transaction_claim(project, "archive-stale:reader_accessibility"):
        state_path, _, state_pre = _load_state(project)
        if policy._open_project_round(project):
            raise MilestoneTransactionError(
                "AMC-REPIN-ROUND", "stale reader-policy request archival requires no open review round"
            )
        if not request_path.is_file() or _is_link(request_path):
            raise MilestoneTransactionError(
                "AMC-REPIN-REQUEST", "pending reader-policy rebind request is missing or linked"
            )
        request_hash = _sha256(request_path)
        if request_hash != expected_request_sha256:
            raise MilestoneTransactionError(
                "AMC-REPIN-REQUEST-HASH", "pending request bytes differ from the explicitly supplied sha256"
            )
        request = _load_object(request_path, "AMC-REPIN-REQUEST")
        required = {
            "request_id", "pin_epoch", "profile_sha256", "attestation_view_pin",
            "exemplar_view_pin", "delta_class", "repin_log_ref", "status",
        }
        if set(request) != required or request.get("status") != "pending":
            raise MilestoneTransactionError(
                "AMC-REPIN-REQUEST", "rebind request fields or pending status are invalid"
            )
        profile_path = policy.DEFAULT_PROFILE.resolve()
        if not profile_path.is_file():
            raise MilestoneTransactionError("AMC-REPIN-POLICY", "canonical reader profile is missing")
        profile = policy.load_profile(profile_path)
        expected = profile["domain_native_register"]["expected_verification"]
        current_fields = {
            "profile_sha256": _sha256(profile_path),
            "attestation_view_pin": expected.get("attestation_view_pin"),
            "exemplar_view_pin": expected.get("exemplar_view_pin"),
            "pin_epoch": expected.get("pin_epoch"),
            "repin_log_ref": f"references/policies/repin_log.jsonl#epoch-{expected.get('pin_epoch')}",
        }
        if all(request.get(key) == value for key, value in current_fields.items()):
            raise MilestoneTransactionError(
                "AMC-REPIN-REQUEST-CURRENT",
                "pending request matches the current profile; apply rebind-reader-policy instead of archiving it",
            )
        epoch = request.get("pin_epoch")
        if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 1:
            raise MilestoneTransactionError("AMC-REPIN-REQUEST", "pending request pin_epoch is invalid")
        archive = (
            project / "reviews"
            / f"repin_rebind_request.{epoch}.{request_hash[:16]}.stale.json"
        )
        payload = {
            "schema_version": "1.0.0",
            "status": "archived_stale",
            "archived_at": at,
            "archived_by": "planner",
            "reason": "request_does_not_match_current_profile_after_package_rollback",
            "request_sha256": request_hash,
            "request": request,
        }
        archive_bytes = _json_bytes(payload)
        _exclusive_bytes(archive, archive_bytes)
        if _sha256(state_path) != state_pre or _sha256(request_path) != request_hash:
            raise MilestoneTransactionError(
                "AMC-CONCURRENT-CHANGE", "phase state or rebind request changed during stale-request archival"
            )
        if archive.read_bytes() != archive_bytes:
            raise MilestoneTransactionError("AMC-REPIN-READBACK", "stale-request archive read-back failed")
        request_path.unlink()
        return archive


def _action_for_open_milestone(project: Path, state: dict[str, Any], milestone: str) -> dict[str, Any]:
    record = _framework(state)["milestones"].get(milestone)
    if not isinstance(record, dict):
        raise MilestoneTransactionError("AMC-PHASE-STATE", f"missing milestone record: {milestone}")
    public = LEDGER_TO_PUBLIC[milestone]
    if record.get("status") == "not_started":
        action = "begin"
    elif not record.get("artifacts"):
        action = "finalize" if milestone == "M5" else "draft"
    elif milestone == "M4" and any(
        section.get("current_phase") != "Ph3_converged"
        for section in state.get("sections", {}).values()
        if isinstance(section, dict)
    ):
        action = "revise"
    else:
        action = "close" if milestone == "M5" else "accept"
    return {"status": "READY", "milestone": public, "action": action,
            "authority_mode": _authority_mode_for(project)}


def derive(
    project: Path, requested: str | None = None, purpose: str = "dispatch"
) -> dict[str, Any]:
    """Default target is the first non-accepted milestone (gather auto-walk).

    After materials are in play, ``requested`` may name any started M1-M4.
    First-start of a ``not_started`` successor still requires accepted
    predecessors. FINAL still requires four current accepted hashes.
    Evaluate of already-staged named M1-M4 bytes does not bind the gather hole.
    """
    resolved = project.resolve()
    _, state, _ = _load_state(resolved)
    framework = _framework(state)
    milestones = framework["milestones"]
    if purpose == "evaluate":
        if requested is None:
            raise MilestoneTransactionError("AMC-TARGET", "evaluate requires a named M1-M4")
        if requested not in {"M1", "M2", "M3", "M4"}:
            raise MilestoneTransactionError(
                "AMC-TARGET",
                "evaluate names M1-M4; FINAL apply stays on the final stage",
            )
        m5 = milestones.get("M5")
        if isinstance(m5, dict) and m5.get("status") == "accepted":
            raise MilestoneTransactionError("AMC-ORDER", "accepted M5 is the one-way door")
        return {
            "status": "READY",
            "milestone": requested,
            "action": "evaluate",
            "authority_mode": _authority_mode_for(project),
        }
    if purpose != "dispatch":
        raise MilestoneTransactionError("AMC-TARGET", "derive purpose must be dispatch or evaluate")
    if requested is not None:
        ledger = PUBLIC_TO_LEDGER.get(requested)
        if ledger is None:
            raise MilestoneTransactionError("AMC-TARGET", "derive target must be M1-M4 or FINAL")
        record = milestones.get(ledger)
        if isinstance(record, dict) and record.get("status") != "accepted":
            if named_draft_permitted(resolved, framework, requested):
                return _action_for_open_milestone(resolved, state, ledger)
            raise MilestoneTransactionError(
                "AMC-ORDER",
                f"named target {requested} is not permitted for first-start dispatch "
                "while gather order is in force. Evaluate already-staged bytes with "
                "--purpose evaluate. Do not bind another milestone.",
            )
    for milestone in MILESTONES:
        record = milestones.get(milestone)
        if not isinstance(record, dict):
            raise MilestoneTransactionError("AMC-PHASE-STATE", f"missing milestone record: {milestone}")
        if record.get("status") == "accepted":
            continue
        return _action_for_open_milestone(resolved, state, milestone)
    return {"status": "COMPLETE", "milestone": None, "action": None,
            "authority_mode": _authority_mode_for(project)}


def _stable_policy(framework: dict[str, Any]) -> dict[str, Any]:
    binding = framework.get("policy_bindings", {}).get("reader_accessibility")
    if not isinstance(binding, dict):
        raise MilestoneTransactionError("AMC-POLICY", "reader-accessibility policy binding is missing")
    if binding.get("binding_version") == "2.0.0":
        values = {
            "profile_path": binding.get("resolved_path"),
            "profile_sha256": binding.get("profile_sha256"),
            "resolved_sha256": binding.get("resolved_sha256"),
            "semantic_usage": binding.get("semantic_usage"),
        }
        if (
            values["semantic_usage"] != "not_invoked"
            or any(not isinstance(values[key], str) or not values[key] for key in READER_PROFILE_POLICY_KEYS[:-1])
        ):
            raise MilestoneTransactionError("AMC-POLICY", "v2 reader-profile binding is incomplete")
        return values
    values = {
        "profile_path": binding.get("resolved_path"),
        "profile_sha256": binding.get("profile_sha256"),
        "resolved_sha256": binding.get("resolved_sha256"),
        "attestation_view_pin": binding.get("attestation_view_pin"),
        "exemplar_view_pin": binding.get("exemplar_view_pin"),
    }
    if any(not isinstance(value, str) or not value for value in values.values()):
        raise MilestoneTransactionError("AMC-POLICY", "stable reader policy pins are incomplete")
    return values


def begin(project: Path, milestone: str, at: str | None = None) -> None:
    project = project.resolve(); guard_lifecycle_project_root(project); _enter_authority_mode(project); at = _timestamp(at)
    ledger_milestone = PUBLIC_TO_LEDGER.get(milestone)
    if ledger_milestone not in PREDECESSOR:
        raise MilestoneTransactionError("AMC-TARGET", "begin target must be M2, M3, M4, or FINAL")
    with transaction_claim(project, f"begin:{milestone}"):
        path, state, prehash = _load_state(project)
        derived = derive(project, requested=milestone)
        if (derived.get("status"), derived.get("milestone"), derived.get("action")) != ("READY", milestone, "begin"):
            raise MilestoneTransactionError("AMC-ORDER", f"{milestone} is not the derived begin action")
        proposed = copy.deepcopy(state); framework = _framework(proposed)
        handoff_policy = _effective_handoff_policy(framework)
        predecessor = PREDECESSOR[ledger_milestone]; prior = framework["milestones"][predecessor]
        target = framework["milestones"][ledger_milestone]
        if prior.get("status") != "accepted":
            raise MilestoneTransactionError("AMC-HANDOFF", f"{predecessor} must be accepted before {milestone} can begin")
        if prior.get("approval", {}).get("status") != "approved":
            raise MilestoneTransactionError("AMC-HANDOFF", f"{predecessor} must retain approval authority before {milestone} can begin")
        handoff_status = prior.get("handoff", {}).get("status")
        if handoff_policy == AUDITED_POLICY:
            if handoff_status != "ready":
                raise MilestoneTransactionError("AMC-HANDOFF", f"{predecessor} must be accepted with a ready F9 handoff")
            prior["handoff"]["status"] = "consumed"
            binding = {"binding_type": "handoff_packet", "path": prior["handoff"]["packet_path"], "sha256": prior["handoff"]["packet_sha256"]}
            _append_event(framework, "handoff_consumed", predecessor, at, f"Planner consumed {predecessor} F9 to begin {milestone}.", bindings=[binding])
        elif handoff_policy == DERIVED_POLICY:
            if handoff_status not in {"not_applicable", "ready", "consumed"}:
                raise MilestoneTransactionError(
                    "AMC-HANDOFF",
                    f"{predecessor} derived handoff must be not_applicable or retained exact evidence",
                )
            if handoff_status in {"ready", "consumed"}:
                current_validation = validate_document(project, state)
                if not current_validation.exit_permitted:
                    first = next(
                        (
                            finding
                            for finding in current_validation.findings
                            if finding.code in {"MF-HANDOFF", "MF-BINDING"}
                        ),
                        current_validation.findings[0],
                    )
                    raise MilestoneTransactionError(
                        first.code, f"{first.path}: {first.message}"
                    )
        else:  # pragma: no cover - the resolver is closed over known policies.
            raise MilestoneTransactionError("AMC-HANDOFF", "unsupported effective handoff policy")
        target["status"] = "in_progress"
        if ledger_milestone in {"M3", "M4", "M5"}:
            target["policy_evidence"] = _stable_policy(framework)
        _append_event(framework, "milestone_started", ledger_milestone, at, f"Planner began the derived {milestone} milestone.")
        _validate_prospective(project, proposed)
        if _sha256(path) != prehash:
            raise MilestoneTransactionError("AMC-CONCURRENT-CHANGE", "phase state changed during begin transaction")
        _atomic_replace(path, proposed)


def _validate_binding_list(project: Path, value: Any, code: str) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise MilestoneTransactionError(code, "binding list must be an array")
    output: list[dict[str, str]] = []
    for row in value:
        if not isinstance(row, dict) or set(row) != {"path", "sha256"}:
            raise MilestoneTransactionError(code, "binding must contain only path and sha256")
        path, relative = _safe_project_file(project, row.get("path"), code)
        if row.get("sha256") != _sha256(path):
            raise MilestoneTransactionError(code, f"stale binding hash: {relative}")
        output.append({"path": relative, "sha256": row["sha256"]})
    return output


def _validate_feedback(project: Path, milestone: str, value: Any, lineage: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise MilestoneTransactionError("AMC-CHECKPOINT", "checkpoint needs at least one feedback record")
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in value:
        if not isinstance(row, dict) or set(row) != FEEDBACK_FIELDS:
            raise MilestoneTransactionError("AMC-CHECKPOINT", "feedback record fields are invalid")
        if row.get("feedback_id") in seen or not isinstance(row.get("feedback_id"), str) or not row["feedback_id"]:
            raise MilestoneTransactionError("AMC-CHECKPOINT", "feedback IDs must be non-empty and unique")
        seen.add(row["feedback_id"])
        if row.get("source_authority") not in AUTHORITIES or row.get("disposition") not in DISPOSITIONS:
            raise MilestoneTransactionError("AMC-CHECKPOINT", "feedback authority or disposition is invalid/pending")
        if row.get("target_milestone") != milestone or row.get("source_milestone") != milestone or row.get("lineage_id") != lineage:
            raise MilestoneTransactionError("AMC-CHECKPOINT", "feedback milestone or lineage binding is wrong")
        _timestamp(row.get("received_at"))
        for path_key, sha_key in (("source_path", "source_sha256"), ("contemporaneity_evidence_path", "contemporaneity_evidence_sha256")):
            source, relative = _safe_project_file(project, row.get(path_key), "AMC-CHECKPOINT")
            if row.get(sha_key) != _sha256(source):
                raise MilestoneTransactionError("AMC-CHECKPOINT", f"feedback binding is stale: {relative}")
            row = dict(row); row[path_key] = relative
        output.append(row)
    return output


def _assert_scholarly_authority_chain(
    project: Path,
    draft_results: dict[str, dict[str, Any]],
    scholarly: dict[str, Any],
    expected_receipt_id: str,
) -> None:
    try:
        validate_scholarly_authority_chain(
            project, draft_results, scholarly, expected_receipt_id,
        )
    except (KeyError, TypeError, ValueError, OSError) as exc:
        raise MilestoneTransactionError(
            "AMC-SCHOLARLY-EVALUATION-STALE", str(exc),
        ) from exc


def _validate_checkpoint(
    project: Path, path: Path, milestone: str, lineage: str,
    expected_receipt_id: str,
) -> tuple[dict[str, Any], Path, str, str, int, dict[str, Any]]:
    checkpoint_file, checkpoint_relative = _supplied_project_file(project, path, "AMC-CHECKPOINT")
    try:
        checkpoint_bytes = checkpoint_file.read_bytes()
        checkpoint = json.loads(checkpoint_bytes)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MilestoneTransactionError("AMC-CHECKPOINT", f"cannot read valid checkpoint JSON: {exc}") from exc
    if not isinstance(checkpoint, dict):
        raise MilestoneTransactionError("AMC-CHECKPOINT", "checkpoint JSON must be an object")
    if set(checkpoint) != CHECKPOINT_FIELDS or checkpoint.get("schema_version") != "1.0.0" or checkpoint.get("milestone") != milestone:
        raise MilestoneTransactionError("AMC-CHECKPOINT", "checkpoint fields, version, or milestone are invalid")
    for key in ("decisions_frozen", "open_debts", "next_milestone_instructions"):
        if not isinstance(checkpoint.get(key), list) or any(not isinstance(item, str) or not item for item in checkpoint[key]):
            raise MilestoneTransactionError("AMC-CHECKPOINT", f"{key} must be an array of non-empty strings")
    checkpoint["inputs_consumed"] = _validate_binding_list(project, checkpoint.get("inputs_consumed"), "AMC-CHECKPOINT")
    checkpoint["feedback_records"] = _validate_feedback(project, milestone, checkpoint.get("feedback_records"), lineage)
    policy = checkpoint.get("policy_evidence")
    if not isinstance(policy, dict):
        raise MilestoneTransactionError("AMC-CHECKPOINT", "policy_evidence must be an object")
    draft_keys = {"draft_generation", "draft_evaluation", "scholarly_evaluation"}
    allowed = set(draft_keys)
    if milestone == "M3":
        allowed |= {"wiki_grounding", "wiki_grounding_opt_out"}
    if milestone in {"M4", "M5"}:
        allowed |= {"phase", "cycle_id"}
    if set(policy) - allowed:
        raise MilestoneTransactionError("AMC-CHECKPOINT", f"policy_evidence fields are invalid for {milestone}")
    if not draft_keys <= set(policy):
        missing = draft_keys - set(policy)
        if "scholarly_evaluation" in missing:
            raise MilestoneTransactionError(
                "AMC-SCHOLARLY-EVALUATION-MISSING",
                f"{milestone} requires a current independent scholarly evaluation",
            )
        raise MilestoneTransactionError(
            "AMC-DRAFT-POLICY-MISSING",
            f"{milestone} requires current generation and independent evaluation policy evidence",
        )
    public_target = LEDGER_TO_PUBLIC[milestone]
    _, _, deliverable_relative = derive_receipt_authority(public_target)
    deliverable, _ = _safe_project_file(project, deliverable_relative, "AMC-DRAFT-POLICY")
    deliverable_sha = _sha256(deliverable)
    phase_requirements = {
        "draft_generation": ("generation", "evaluation_ready"),
        "draft_evaluation": ("evaluation", "product_qualified"),
    }
    draft_results: dict[str, dict[str, Any]] = {}
    for key, (phase_name, disposition) in phase_requirements.items():
        binding = policy.get(key)
        if not isinstance(binding, dict) or set(binding) != {"evidence_path", "evidence_sha256"}:
            raise MilestoneTransactionError("AMC-DRAFT-POLICY", f"{key} must be a path/hash binding")
        evidence, relative = _safe_project_file(project, binding.get("evidence_path"), "AMC-DRAFT-POLICY")
        if binding.get("evidence_sha256") != _sha256(evidence):
            raise MilestoneTransactionError("AMC-DRAFT-POLICY-STALE", f"policy evidence is stale: {relative}")
        try:
            result = validate_lifecycle_verifier_binding(
                locator=evidence,
                artifact=deliverable,
                project_root=project,
                harness_root=ROOT,
                expected_phase=phase_name,
                expected_disposition=disposition,
            )
        except VerifierError as exc:
            code = "AMC-DRAFT-POLICY-STALE" if exc.code in {
                "LIFECYCLE-EVIDENCE-STALE", "EVIDENCE-TOCTOU",
                "VERIFIER-TRANSACTION-INCOMPLETE",
            } else "AMC-DRAFT-POLICY"
            raise MilestoneTransactionError(code, f"{exc.code}: {exc.message}") from exc
        if result["locator"].get("target") != deliverable_relative:
            raise MilestoneTransactionError(
                "AMC-DRAFT-POLICY", f"{key} target differs from {deliverable_relative}"
            )
        draft_results[key] = result
        binding["evidence_path"] = relative
    try:
        scholarly = validate_scholarly_binding(
            project_root=project,
            artifact=deliverable,
            binding=policy.get("scholarly_evaluation"),
        )
    except ScholarlyBindingError as exc:
        code = (
            "AMC-SCHOLARLY-EVALUATION-MISSING"
            if exc.code == "SCHOLARLY-EVIDENCE-MISSING"
            else "AMC-SCHOLARLY-EVALUATION-STALE"
        )
        raise MilestoneTransactionError(code, f"{exc.code}: {exc.message}") from exc
    policy["scholarly_evaluation"] = scholarly["binding"]
    _assert_scholarly_authority_chain(
        project, draft_results, scholarly, expected_receipt_id,
    )
    scholarly["_draft_results"] = draft_results
    scholarly["_authority_receipt_id"] = expected_receipt_id
    if milestone == "M3":
        grounding_keys = set(policy) - draft_keys
        if grounding_keys not in ({"wiki_grounding"}, {"wiki_grounding_opt_out"}):
            raise MilestoneTransactionError("AMC-CHECKPOINT", "M3 requires exactly one wiki-grounding binding or explicit opt-out")
        grounding = policy[next(iter(grounding_keys))]
        if not isinstance(grounding, dict):
            raise MilestoneTransactionError("AMC-CHECKPOINT", "M3 policy evidence must be an object")
        evidence, relative = _safe_project_file(project, grounding.get("evidence_path"), "AMC-CHECKPOINT")
        if grounding.get("evidence_sha256") != _sha256(evidence):
            raise MilestoneTransactionError("AMC-CHECKPOINT", f"wiki-grounding binding is stale: {relative}")
        grounding["evidence_path"] = relative
    elif milestone == "M4":
        if set(policy) != draft_keys | {"phase", "cycle_id"} or policy.get("phase") not in {"Ph1", "Ph2", "Ph3"} or not isinstance(policy.get("cycle_id"), str) or CYCLE_RE.fullmatch(policy["cycle_id"]) is None:
            raise MilestoneTransactionError("AMC-CHECKPOINT", "M4 first record requires phase and safe cycle_id atomically")
    elif milestone == "M5":
        if set(policy) != draft_keys | {"phase", "cycle_id"} or policy.get("phase") != "Ph4" or not isinstance(policy.get("cycle_id"), str) or CYCLE_RE.fullmatch(policy["cycle_id"]) is None:
            raise MilestoneTransactionError("AMC-CHECKPOINT", "M5 record requires Ph4 and a safe terminal cycle_id atomically")
    elif set(policy) != draft_keys:
        raise MilestoneTransactionError("AMC-CHECKPOINT", f"{milestone} accepts only draft governance policy evidence")
    return (
        checkpoint,
        checkpoint_file,
        checkpoint_relative,
        hashlib.sha256(checkpoint_bytes).hexdigest(),
        len(checkpoint_bytes),
        scholarly,
    )


def _receipt_result(
    project: Path, receipt_path: Path, milestone: str, receipt_target: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any], str, Path, str, dict[str, str]]:
    try:
        receipt_bytes = receipt_path.read_bytes(); receipt = json.loads(receipt_bytes)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MilestoneTransactionError("AMC-RECEIPT", f"cannot read valid consumed receipt JSON: {exc}") from exc
    if not isinstance(receipt, dict):
        raise MilestoneTransactionError("AMC-RECEIPT", "consumed receipt JSON must be an object")
    findings = verify_receipt(project, receipt_path, allow_consumed=True)
    if findings:
        code, message = findings[0]; raise MilestoneTransactionError(code, message)
    expected_target = receipt_target or milestone
    if receipt_path.parent.name != "consumed" or receipt.get("target_milestone") != expected_target or receipt.get("authorized_role") != "generator":
        raise MilestoneTransactionError("AMC-RECEIPT", "record requires the canonical consumed Generator receipt for this milestone")
    result_path = receipt_path.with_suffix(".result.json")
    try:
        result_bytes = result_path.read_bytes(); result = json.loads(result_bytes)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MilestoneTransactionError("AMC-RESULT", f"cannot read valid publication result JSON: {exc}") from exc
    if not isinstance(result, dict):
        raise MilestoneTransactionError("AMC-RESULT", "publication result JSON must be an object")
    if set(result) != {"schema_version", "receipt_id", "reservation_id", "outcome", "published"} or result.get("schema_version") != "1.0.0" or result.get("outcome") != "published" or result.get("receipt_id") != receipt.get("receipt_id") or result.get("reservation_id") != receipt.get("reservation_id"):
        raise MilestoneTransactionError("AMC-RESULT", "publication result does not bind the consumed receipt")
    primary = receipt.get("primary_deliverable_path")
    rows = [row for row in result.get("published", []) if isinstance(row, dict) and row.get("path") == primary]
    if len(rows) != 1:
        raise MilestoneTransactionError("AMC-RESULT", "publication result does not contain exactly one primary deliverable")
    deliverable, relative = _safe_project_file(project, primary, "AMC-RESULT")
    deliverable_sha = _sha256(deliverable)
    if rows[0].get("sha256") != deliverable_sha:
        raise MilestoneTransactionError("AMC-RESULT", "published primary deliverable hash is stale")
    try:
        mutation = validate_mutation_target(project, relative)
    except ReceiptTransactionError as exc:
        raise MilestoneTransactionError(exc.code, exc.message) from exc
    if rows[0].get("mutation_row_sha256") != mutation.get("row_sha256"):
        raise MilestoneTransactionError(
            "AMC-MUTATION-BINDING",
            "publication result does not bind the sanctioned primary-deliverable mutation row",
        )
    if milestone == "M5":
        export_path = derive_released_export_path("FINAL")
        if export_path is None:
            raise MilestoneTransactionError("AMC-RESULT", "live FINAL authority must name one released export")
        export_rows = [row for row in result.get("published", []) if isinstance(row, dict) and row.get("path") == export_path]
        if len(export_rows) != 1:
            raise MilestoneTransactionError("AMC-RESULT", "FINAL publication result must contain exactly one released export")
        export_file, export_relative = _safe_project_file(project, export_path, "AMC-RESULT")
        if export_rows[0].get("sha256") != _sha256(export_file):
            raise MilestoneTransactionError("AMC-RESULT", f"published released export hash is stale: {export_relative}")
        try:
            export_mutation = validate_mutation_target(project, export_relative)
        except ReceiptTransactionError as exc:
            raise MilestoneTransactionError(exc.code, exc.message) from exc
        if export_rows[0].get("mutation_row_sha256") != export_mutation.get("row_sha256"):
            raise MilestoneTransactionError(
                "AMC-MUTATION-BINDING",
                "publication result does not bind the sanctioned released-export mutation row",
            )
    source_expectations = {
        str(receipt_path.resolve()): hashlib.sha256(receipt_bytes).hexdigest(),
        str(result_path.resolve()): hashlib.sha256(result_bytes).hexdigest(),
    }
    if _sha256(receipt_path) != source_expectations[str(receipt_path.resolve())] or _sha256(result_path) != source_expectations[str(result_path.resolve())]:
        raise MilestoneTransactionError("AMC-DEPENDENCY-CHANGED", "receipt or publication result changed during validation")
    return receipt, result, relative, deliverable, deliverable_sha, source_expectations


def _recorded_assignment_receipt(
    project: Path, record: dict[str, Any]
) -> tuple[str, Path, str, str]:
    policy = record.get("policy_evidence")
    binding = policy.get("assignment_receipt") if isinstance(policy, dict) else None
    if (
        not isinstance(binding, dict)
        or set(binding) != {"receipt_id", "evidence_path", "evidence_sha256"}
        or not isinstance(binding.get("receipt_id"), str)
        or not binding["receipt_id"]
    ):
        raise MilestoneTransactionError(
            "AMC-SCHOLARLY-EVALUATION-STALE",
            "recorded milestone lacks its consumed assignment-receipt authority binding",
        )
    receipt, relative = _safe_project_file(
        project, binding.get("evidence_path"), "AMC-SCHOLARLY-EVALUATION-STALE"
    )
    digest = _sha256(receipt)
    if receipt.parent.name != "consumed" or binding.get("evidence_sha256") != digest:
        raise MilestoneTransactionError(
            "AMC-SCHOLARLY-EVALUATION-STALE",
            "recorded assignment-receipt authority is stale or outside the consumed lane",
        )
    try:
        value = json.loads(receipt.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MilestoneTransactionError(
            "AMC-SCHOLARLY-EVALUATION-STALE",
            f"recorded assignment receipt is unreadable: {exc}",
        ) from exc
    if not isinstance(value, dict) or value.get("receipt_id") != binding["receipt_id"]:
        raise MilestoneTransactionError(
            "AMC-SCHOLARLY-EVALUATION-STALE",
            "recorded assignment receipt identity differs from its policy binding",
        )
    return binding["receipt_id"], receipt, relative, digest


def _lifecycle_policy_dependencies(
    project: Path, checkpoint: dict[str, Any]
) -> dict[str, str]:
    milestone = checkpoint["milestone"]
    public_target = LEDGER_TO_PUBLIC[milestone]
    _, _, deliverable_relative = derive_receipt_authority(public_target)
    deliverable, _ = _safe_project_file(
        project, deliverable_relative, "AMC-DRAFT-POLICY"
    )
    expected: dict[str, str] = {}
    for key, phase, disposition in (
        ("draft_generation", "generation", "evaluation_ready"),
        ("draft_evaluation", "evaluation", "product_qualified"),
    ):
        locator, _ = _safe_project_file(
            project,
            checkpoint["policy_evidence"][key]["evidence_path"],
            "AMC-DRAFT-POLICY",
        )
        try:
            result = validate_lifecycle_verifier_binding(
                locator=locator,
                artifact=deliverable,
                project_root=project,
                harness_root=ROOT,
                expected_phase=phase,
                expected_disposition=disposition,
            )
        except VerifierError as exc:
            raise MilestoneTransactionError(
                "AMC-DRAFT-POLICY-STALE", f"{exc.code}: {exc.message}"
            ) from exc
        for row in result["dependencies"]:
            expected[row["path"]] = row["sha256"]
    return expected


def _checkpoint_dependencies(
    project: Path, checkpoint: dict[str, Any], scholarly: dict[str, Any]
) -> list[Path]:
    paths: list[Path] = []
    for row in checkpoint["feedback_records"]:
        for key in ("source_path", "contemporaneity_evidence_path"):
            paths.append(_safe_project_file(project, row[key], "AMC-DEPENDENCY")[0])
    for row in checkpoint["inputs_consumed"]:
        paths.append(_safe_project_file(project, row["path"], "AMC-DEPENDENCY")[0])
    policy = checkpoint.get("policy_evidence", {})
    grounding = policy.get("wiki_grounding") or policy.get("wiki_grounding_opt_out")
    if isinstance(grounding, dict) and isinstance(grounding.get("evidence_path"), str):
        paths.append(_safe_project_file(project, grounding["evidence_path"], "AMC-DEPENDENCY")[0])
    paths.extend(Path(path) for path in _lifecycle_policy_dependencies(project, checkpoint))
    paths.extend(Path(row["path"]) for row in scholarly["dependencies"])
    return paths


def _checkpoint_dependency_expectations(
    project: Path, checkpoint: dict[str, Any], scholarly: dict[str, Any]
) -> dict[str, str]:
    expected: dict[str, str] = {}
    for row in checkpoint["feedback_records"]:
        for path_key, sha_key in (("source_path", "source_sha256"), ("contemporaneity_evidence_path", "contemporaneity_evidence_sha256")):
            path = _safe_project_file(project, row[path_key], "AMC-DEPENDENCY")[0]
            expected[str(path.resolve())] = row[sha_key]
    for row in checkpoint["inputs_consumed"]:
        path = _safe_project_file(project, row["path"], "AMC-DEPENDENCY")[0]
        expected[str(path.resolve())] = row["sha256"]
    policy = checkpoint.get("policy_evidence", {})
    grounding = policy.get("wiki_grounding") or policy.get("wiki_grounding_opt_out")
    if isinstance(grounding, dict) and isinstance(grounding.get("evidence_path"), str):
        path = _safe_project_file(project, grounding["evidence_path"], "AMC-DEPENDENCY")[0]
        expected[str(path.resolve())] = grounding["evidence_sha256"]
    expected.update(_lifecycle_policy_dependencies(project, checkpoint))
    expected.update({
        path: value[0]
        for path, value in _scholarly_dependency_expectations(scholarly).items()
    })
    return expected


def record(
    project: Path, milestone: str, receipt: Path, checkpoint_path: Path,
    at: str | None = None, *, _before_state_publish: Callable[[], None] | None = None,
) -> None:
    project = project.resolve(); guard_lifecycle_project_root(project); _enter_authority_mode(project); at = _timestamp(at)
    public_milestone = milestone
    milestone = PUBLIC_TO_LEDGER.get(public_milestone, "")
    if milestone not in MILESTONES:
        raise MilestoneTransactionError("AMC-TARGET", "record target must be M1-M4 or FINAL")
    with transaction_claim(project, f"record:{milestone}"):
        state_path, state, prehash = _load_state(project); framework = _framework(state)
        expected = derive(project, requested=public_milestone)
        allowed_actions = {"draft", "revise"} if milestone == "M4" else ({"finalize"} if milestone == "M5" else {"draft"})
        supersedes_candidate = False
        if _ACTIVE_AUTHORITY_MODE == "shipment_only":
            # Producer-boundary Phase F: staging production is freely
            # revisable. A post-convergence M4 or recorded M5 candidate may be
            # re-recorded; the re-record supersedes the prior candidate with
            # proposal-only events. The harness reports that prior convergence
            # or handoff evidence would need research-master revalidation --
            # it never applies that revalidation or any phase regression.
            staging_extra = {"accept"} if milestone == "M4" else ({"close"} if milestone == "M5" else set())
            if expected.get("action") in staging_extra:
                supersedes_candidate = True
                allowed_actions = allowed_actions | staging_extra
        if expected.get("milestone") != public_milestone or expected.get("action") not in allowed_actions:
            raise MilestoneTransactionError("AMC-ORDER", f"{public_milestone} is not the derived record action")
        receipt_record, result_record, relative, deliverable_path, digest, source_expectations = _receipt_result(
            project, receipt.resolve(), milestone, public_milestone,
        )
        _, receipt_relative = _supplied_project_file(
            project, receipt.resolve(), "AMC-RECEIPT"
        )
        lineage = framework.get("primary_lineage")
        checkpoint, checkpoint_file, checkpoint_relative, checkpoint_sha, checkpoint_size, scholarly = _validate_checkpoint(
            project, checkpoint_path.resolve(), milestone, lineage,
            receipt_record["receipt_id"],
        )
        publication_dependencies: list[Path] = []
        publication_expectations: dict[str, str] = {}
        if milestone == "M5":
            export_path = derive_released_export_path("FINAL")
            if export_path is None:
                raise MilestoneTransactionError("AMC-RESULT", "live FINAL authority must name one released export")
            export_file = _safe_project_file(project, export_path, "AMC-RESULT")[0]
            publication_dependencies.append(export_file)
            publication_expectations[str(export_file.resolve())] = _sha256(export_file)
        dependencies = _dependency_snapshot(
            project,
            [receipt.resolve(), receipt.resolve().with_suffix(".result.json"), deliverable_path, checkpoint_file, *publication_dependencies, *_checkpoint_dependencies(project, checkpoint, scholarly)],
        )
        expected_dependencies = {**source_expectations, **publication_expectations, **_checkpoint_dependency_expectations(project, checkpoint, scholarly)}
        expected_dependencies[str(deliverable_path.resolve())] = digest
        expected_dependencies[str(checkpoint_file.resolve())] = checkpoint_sha
        if any(dependencies.get(path, (None, 0))[0] != expected_sha for path, expected_sha in expected_dependencies.items()):
            raise MilestoneTransactionError("AMC-DEPENDENCY-CHANGED", "a bound dependency changed between validation and snapshot capture")
        _assert_scholarly_dependency_snapshot(dependencies, scholarly)
        artifact_path = deliverable_path
        artifact_relative = relative
        snapshot_created = False
        snapshot_bytes: bytes | None = None
        if milestone == "M4" or (milestone == "M5" and _ACTIVE_AUTHORITY_MODE == "shipment_only"):
            # M4 always; M5 additionally in staging mode: content-addressed
            # snapshots keep every historical event binding byte-valid across
            # free staging re-records (the live FINAL path mutates; snapshots
            # never do).
            artifact_relative = snapshot_path(milestone, digest)
            artifact_path = project / Path(*PurePosixPath(artifact_relative).parts)
            snapshot_bytes = deliverable_path.read_bytes()
        proposed = copy.deepcopy(state); proposed_framework = _framework(proposed); target = proposed_framework["milestones"][milestone]
        artifact = {
            "role": "deliverable", "artifact_kind": ARTIFACT_KIND[milestone],
            "path": artifact_relative, "sha256": digest, "bytes": deliverable_path.stat().st_size,
            "verified_at": at, "lineage_id": lineage,
        }
        checkpoint_artifact = {
            "role": "evidence", "artifact_kind": "milestone_checkpoint",
            "path": checkpoint_relative, "sha256": checkpoint_sha,
            "bytes": checkpoint_size, "verified_at": at,
            "lineage_id": lineage,
        }
        artifacts = [artifact, checkpoint_artifact]
        if milestone == "M5":
            result_path = receipt.resolve().with_suffix(".result.json")
            receipt_file, receipt_relative = _supplied_project_file(project, receipt.resolve(), "AMC-RECEIPT")
            result_file, result_relative = _supplied_project_file(project, result_path, "AMC-RESULT")
            export_path = derive_released_export_path("FINAL")
            if export_path is None:
                raise MilestoneTransactionError("AMC-RESULT", "live FINAL authority must name one released export")
            export_file, export_relative = _safe_project_file(project, export_path, "AMC-RESULT")
            artifacts.extend([
                {
                    "role": "export", "artifact_kind": "released_manuscript",
                    "path": export_relative, "sha256": _sha256(export_file), "bytes": export_file.stat().st_size,
                    "verified_at": at, "lineage_id": lineage, "source_path": relative, "source_sha256": digest,
                },
                {
                    "role": "evidence", "artifact_kind": "consumed_final_receipt",
                    "path": receipt_relative, "sha256": _sha256(receipt_file), "bytes": receipt_file.stat().st_size,
                    "verified_at": at, "lineage_id": lineage,
                },
                {
                    "role": "evidence", "artifact_kind": "final_publication_result",
                    "path": result_relative, "sha256": _sha256(result_file), "bytes": result_file.stat().st_size,
                    "verified_at": at, "lineage_id": lineage,
                },
            ])
        target["artifacts"] = artifacts
        target["feedback_records"] = checkpoint["feedback_records"]
        target.setdefault("policy_evidence", {}).update({
            key: checkpoint["policy_evidence"][key]
            for key in ("draft_generation", "draft_evaluation", "scholarly_evaluation")
        })
        target["policy_evidence"]["assignment_receipt"] = {
            "receipt_id": receipt_record["receipt_id"],
            "evidence_path": receipt_relative,
            "evidence_sha256": source_expectations[str(receipt.resolve())],
        }
        if milestone == "M3":
            target["policy_evidence"].update(checkpoint["policy_evidence"])
        elif milestone == "M4":
            # Approved H1 boundary: these three manuscript-bound fields are
            # introduced in this same authoritative write as the first M4
            # artifact; begin() intentionally binds only the stable reader-policy fields
            # (four for reader-profile v2, five for legacy semantic v1).
            section_phases = {
                "Ph3" if row.get("current_phase") == "Ph3_converged" else row.get("current_phase")
                for row in state.get("sections", {}).values() if isinstance(row, dict)
            }
            if section_phases != {checkpoint["policy_evidence"]["phase"]}:
                raise MilestoneTransactionError("AMC-CHECKPOINT", "M4 checkpoint phase must match every current in-scope section phase")
            target["policy_evidence"].update({
                "manuscript_sha256": digest,
                "phase": checkpoint["policy_evidence"]["phase"],
                "cycle_id": checkpoint["policy_evidence"]["cycle_id"],
            })
        elif milestone == "M5":
            section_phases = {
                row.get("current_phase") for row in state.get("sections", {}).values()
                if isinstance(row, dict)
            }
            if section_phases != {"Ph4"}:
                raise MilestoneTransactionError("AMC-CHECKPOINT", "M5 checkpoint requires every current in-scope section at Ph4")
            target["policy_evidence"].update({
                "manuscript_sha256": digest,
                "phase": "Ph4",
                "cycle_id": checkpoint["policy_evidence"]["cycle_id"],
            })
        artifact_binding = {"binding_type": "artifact", "path": artifact_relative, "sha256": digest}
        deliverable_reason = f"Planner recorded the consumed scoped-writer {milestone} deliverable."
        deliverable_bindings = [artifact_binding]
        if supersedes_candidate:
            # The supersession record is this event itself: the prior candidate
            # rides along as a previous_content binding (the binding type that
            # exists for exactly this), and the reason discloses both the
            # candidate_superseded fact and the revalidation advisory. The
            # reserved reopening vocabulary (milestone_reopened /
            # downstream_stale) belongs to accepted-milestone lifecycles and is
            # deliberately NOT used for staging candidate supersession.
            prior = next((row for row in framework["milestones"][milestone].get("artifacts", [])
                          if isinstance(row, dict) and row.get("role") == "deliverable"), None)
            if isinstance(prior, dict):
                deliverable_bindings.append(
                    {"binding_type": "previous_content", "path": prior["path"], "sha256": prior["sha256"]})
            deliverable_reason += (
                f" Staging re-record: prior {public_milestone} candidate candidate_superseded;"
                " prior convergence or handoff evidence would require research-master"
                " revalidation, which the harness does not apply; proposal-only"
                " production bookkeeping with no research-master force."
            )
        _append_event(proposed_framework, "deliverable_recorded", milestone, at, deliverable_reason, bindings=deliverable_bindings)
        feedback_bindings = [{"binding_type": "feedback", "path": row["source_path"], "sha256": row["source_sha256"]} for row in checkpoint["feedback_records"]]
        _append_event(proposed_framework, "feedback_recorded", milestone, at, f"Planner recorded current {milestone} feedback provenance.", bindings=feedback_bindings)
        _append_event(proposed_framework, "feedback_adjudicated", milestone, at, f"Planner recorded non-pending {milestone} feedback dispositions.", bindings=feedback_bindings)
        try:
            if snapshot_bytes is not None:
                snapshot_created = _exclusive_bytes(artifact_path, snapshot_bytes)
            _validate_prospective(project, proposed)
            if _sha256(state_path) != prehash:
                raise MilestoneTransactionError("AMC-CONCURRENT-CHANGE", "phase state changed during record transaction")
            if _before_state_publish is not None:
                _before_state_publish()
            _revalidate_scholarly_binding(project, scholarly)
            _recheck_scholarly_dependencies(project, scholarly)
            _recheck_dependencies(project, dependencies)
            _atomic_replace(state_path, proposed)
        except Exception:
            if snapshot_created:
                try:
                    artifact_path.unlink()
                except OSError:
                    pass
            raise


def _validate_approval(project: Path, approval_path: Path, milestone: str, artifact: dict[str, Any]) -> tuple[dict[str, Any], str, str]:
    approval_file, relative = _supplied_project_file(project, approval_path, "AMC-APPROVAL")
    try:
        approval_bytes = approval_file.read_bytes(); approval = json.loads(approval_bytes)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MilestoneTransactionError("AMC-APPROVAL", f"cannot read valid approval JSON: {exc}") from exc
    if not isinstance(approval, dict):
        raise MilestoneTransactionError("AMC-APPROVAL", "approval JSON must be an object")
    if set(approval) != APPROVAL_FIELDS or approval.get("schema_version") != "1.0.0" or approval.get("status") != "approved" or approval.get("milestone") != milestone or approval.get("authority") not in AUTHORITIES:
        raise MilestoneTransactionError("AMC-APPROVAL", "approval evidence fields, status, authority, or milestone are invalid")
    _timestamp(approval.get("approved_at"))
    if approval.get("deliverable") != {"path": artifact.get("path"), "sha256": artifact.get("sha256")}:
        raise MilestoneTransactionError("AMC-APPROVAL", "approval does not bind the current deliverable bytes")
    return approval, relative, hashlib.sha256(approval_bytes).hexdigest()


def _validate_m4_acceptance_policy(
    project: Path, policy_path: Path, artifact: dict[str, Any]
) -> tuple[dict[str, Any], Path, Path, str]:
    policy_file, _ = _supplied_project_file(project, policy_path, "AMC-POLICY")
    try:
        policy_bytes = policy_file.read_bytes(); policy = json.loads(policy_bytes)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MilestoneTransactionError("AMC-POLICY", f"cannot read valid M4 policy JSON: {exc}") from exc
    if not isinstance(policy, dict):
        raise MilestoneTransactionError("AMC-POLICY", "M4 policy JSON must be an object")
    valid = (
        set(policy) == M4_ACCEPTANCE_POLICY_FIELDS
        and policy.get("schema_version") == "1.0.0"
        and policy.get("milestone") == "M4"
        and policy.get("phase") == "Ph3"
        and isinstance(policy.get("cycle_id"), str)
        and CYCLE_RE.fullmatch(policy["cycle_id"]) is not None
        and policy.get("manuscript_sha256") == artifact.get("sha256")
        and policy.get("aggregate_verdict") in {"CLEAN", "BORDERLINE"}
    )
    if not valid:
        raise MilestoneTransactionError("AMC-POLICY", "M4 acceptance policy must bind the current manuscript, Ph3 convergence cycle, and CLEAN or BORDERLINE Check 8 verdict")
    check8_file, check8_relative = _safe_project_file(project, policy.get("check8_path"), "AMC-POLICY")
    if policy.get("check8_sha256") != _sha256(check8_file):
        raise MilestoneTransactionError("AMC-POLICY", f"M4 Check 8 binding is stale: {check8_relative}")
    policy["check8_path"] = check8_relative
    return policy, policy_file, check8_file, hashlib.sha256(policy_bytes).hexdigest()


def _validate_m5_terminal_policy(
    project: Path, policy_path: Path, artifact: dict[str, Any]
) -> tuple[dict[str, Any], Path, list[Path], str]:
    policy_file, _ = _supplied_project_file(project, policy_path, "AMC-TERMINAL")
    try:
        policy_bytes = policy_file.read_bytes(); policy = json.loads(policy_bytes)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MilestoneTransactionError("AMC-TERMINAL", f"cannot read valid M5 terminal evidence JSON: {exc}") from exc
    terminal_round = policy.get("terminal_round_id") if isinstance(policy, dict) else None
    valid = (
        isinstance(policy, dict)
        and set(policy) == M5_TERMINAL_POLICY_FIELDS
        and policy.get("schema_version") == "1.0.0"
        and policy.get("milestone") == "M5"
        and isinstance(terminal_round, str)
        and re.fullmatch(r"round_[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{3}", terminal_round) is not None
        and policy.get("phase") == "Ph4"
        and policy.get("cycle_id") == terminal_round
        and policy.get("manuscript_sha256") == artifact.get("sha256")
        and policy.get("aggregate_verdict") in {"CLEAN", "BORDERLINE"}
    )
    if not valid:
        raise MilestoneTransactionError("AMC-TERMINAL", "M5 terminal evidence must bind the current manuscript, Ph4, one terminal round, and a CLEAN or BORDERLINE Check 8 verdict")
    check8_file, check8_relative = _safe_project_file(project, policy.get("check8_path"), "AMC-TERMINAL")
    if policy.get("check8_sha256") != _sha256(check8_file):
        raise MilestoneTransactionError("AMC-TERMINAL", f"M5 Check 8 binding is stale: {check8_relative}")
    policy["check8_path"] = check8_relative
    bindings = policy.get("bindings")
    if not isinstance(bindings, list) or not bindings:
        raise MilestoneTransactionError("AMC-TERMINAL", "terminal evidence bindings must be a non-empty array")
    seen: dict[str, int] = {}
    dependencies = [policy_file, check8_file]
    normalized: list[dict[str, str]] = []
    canonical = {
        "g4_signoff": "reviews/G4_signoff.md",
        "ship_signoff": "reviews/ph4_ship_signoff.md",
        "final_round_report": f"reviews/final_round_report_{terminal_round}.md",
        "reflector_full": "reviews/reflection_report.md",
        "events_log": "reviews/.harness/events.jsonl",
        "findings": "reviews/findings.json",
        "convergence_log": "reviews/convergence_log.md",
    }
    for row in bindings:
        if not isinstance(row, dict) or set(row) != {"role", "path", "sha256"} or row.get("role") not in TERMINAL_BINDING_ROLES:
            raise MilestoneTransactionError("AMC-TERMINAL", "terminal binding must contain only a recognized role, path, and sha256")
        role = row["role"]
        seen[role] = seen.get(role, 0) + 1
        if seen[role] > 1:
            raise MilestoneTransactionError("AMC-TERMINAL", f"terminal binding role must be unique: {role}")
        evidence, relative = _safe_project_file(project, row.get("path"), "AMC-TERMINAL")
        if row.get("sha256") != _sha256(evidence):
            raise MilestoneTransactionError("AMC-TERMINAL", f"terminal binding is stale: {relative}")
        if role in canonical and relative != canonical[role]:
            raise MilestoneTransactionError("AMC-TERMINAL", f"{role} must use canonical path {canonical[role]}")
        if role == "f7_evidence" and not relative.startswith("reviews/.harness/evidence/"):
            raise MilestoneTransactionError("AMC-TERMINAL", "F7 evidence must live under reviews/.harness/evidence/")
        dependencies.append(evidence)
        normalized.append({"role": role, "path": relative, "sha256": row["sha256"]})
    if set(seen) != TERMINAL_BINDING_ROLES:
        missing = sorted(TERMINAL_BINDING_ROLES - set(seen))
        raise MilestoneTransactionError("AMC-TERMINAL", f"terminal evidence roles are incomplete: {missing}")
    by_role = {row["role"]: row for row in normalized}
    f7_relative = by_role["f7_evidence"]["path"]
    f7_file = project / Path(*PurePosixPath(f7_relative).parts)
    events_file = project / Path(*PurePosixPath(by_role["events_log"]["path"]).parts)
    try:
        f7_payload = json.loads(f7_file.read_text(encoding="utf-8"))
        event_rows = [json.loads(line) for line in events_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MilestoneTransactionError("AMC-TERMINAL", f"cannot read bound F7 evidence and event index: {exc}") from exc
    event_id = f7_payload.get("event_id") if isinstance(f7_payload, dict) else None
    f7_valid = (
        isinstance(f7_payload, dict)
        and f7_payload.get("round_id") == terminal_round
        and f7_payload.get("evidence_status") == "complete"
        and isinstance(event_id, str)
        and any(
            isinstance(row, dict)
            and row.get("event_id") == event_id
            and row.get("round_id") == terminal_round
            and row.get("event") == "evidence_packet_written"
            and row.get("path") == f7_relative
            for row in event_rows
        )
    )
    if not f7_valid:
        raise MilestoneTransactionError("AMC-TERMINAL", "bound F7 evidence must be complete, terminal-round current, and indexed by the bound events log")
    policy["bindings"] = normalized
    return policy, policy_file, dependencies, hashlib.sha256(policy_bytes).hexdigest()


def _handoff_packet(state: dict[str, Any], milestone: str, checkpoint: dict[str, Any], approval: dict[str, Any], approval_path: str) -> dict[str, Any]:
    framework = _framework(state); record = framework["milestones"][milestone]
    artifact = next(row for row in record["artifacts"] if row.get("role") == "deliverable" and row.get("lineage_id") == framework["primary_lineage"])
    predecessor = None
    if milestone != "M1":
        prior = framework["milestones"][MILESTONES[MILESTONES.index(milestone) - 1]]["handoff"]
        if prior.get("status") in {"ready", "consumed"}:
            predecessor = {"path": prior["packet_path"], "sha256": prior["packet_sha256"]}
    released_export = None
    inputs_consumed = list(checkpoint["inputs_consumed"])
    if milestone == "M5":
        export = next(row for row in record["artifacts"] if row.get("role") == "export" and row.get("lineage_id") == framework["primary_lineage"])
        released_export = {key: export[key] for key in ("role", "path", "sha256", "bytes", "source_sha256")}
        if export.get("source_path") is not None:
            released_export["source_path"] = export["source_path"]
        for row in record.get("policy_evidence", {}).get("bindings", []):
            binding = {"path": row["path"], "sha256": row["sha256"]}
            if binding not in inputs_consumed:
                inputs_consumed.append(binding)
        for evidence in record["artifacts"]:
            if evidence.get("artifact_kind") in {"consumed_final_receipt", "final_publication_result"}:
                binding = {"path": evidence["path"], "sha256": evidence["sha256"]}
                if binding not in inputs_consumed:
                    inputs_consumed.append(binding)
    return {
        "artifact_family": "F9", "contract_version": "1.0.0",
        "project": state.get("manuscript_id"), "lineage_id": framework["primary_lineage"],
        "from_milestone": milestone, "to_milestone": SUCCESSOR[milestone],
        "predecessor_packet": predecessor,
        "deliverable": {key: artifact[key] for key in ("role", "path", "sha256", "bytes")},
        "released_export": released_export,
        "inputs_consumed": inputs_consumed,
        "decisions_frozen": checkpoint["decisions_frozen"],
        "feedback_dispositions": [{"feedback_id": row["feedback_id"], "disposition": row["disposition"], "rationale": row["rationale"]} for row in record["feedback_records"]],
        "open_debts": checkpoint["open_debts"],
        "next_milestone_instructions": checkpoint["next_milestone_instructions"],
        "policy_evidence": record.get("policy_evidence"),
        "approval": {"authority": approval["authority"], "evidence_path": approval_path, "approved_at": approval["approved_at"]},
    }


def accept(
    project: Path, milestone: str, checkpoint_path: Path, approval_path: Path,
    at: str | None = None, policy_path: Path | None = None,
    terminal_evidence_path: Path | None = None,
    *, emit_f9: bool = False,
    _before_state_publish: Callable[[], None] | None = None,
) -> None:
    project = project.resolve(); guard_lifecycle_project_root(project); _enter_authority_mode(project); at = _timestamp(at)
    public_milestone = milestone
    milestone = PUBLIC_TO_LEDGER.get(public_milestone, "")
    if milestone not in MILESTONES:
        raise MilestoneTransactionError("AMC-TARGET", "accept target must be M1-M4 or FINAL")
    with transaction_claim(project, f"accept:{public_milestone}"):
        state_path, state, prehash = _load_state(project); framework = _framework(state)
        handoff_policy = _effective_handoff_policy(framework)
        derived = derive(project, requested=public_milestone)
        permitted_actions = {"accept", "revise"} if milestone == "M4" else ({"close"} if milestone == "M5" else {"accept"})
        if derived.get("status") != "READY" or derived.get("milestone") != public_milestone or derived.get("action") not in permitted_actions:
            raise MilestoneTransactionError("AMC-ORDER", f"{public_milestone} is not the derived accept action")
        record_state = framework["milestones"][milestone]
        lineage = framework["primary_lineage"]
        recorded_receipt_id, recorded_receipt, _, recorded_receipt_sha = (
            _recorded_assignment_receipt(project, record_state)
        )
        checkpoint, checkpoint_file, checkpoint_relative, checkpoint_sha, checkpoint_size, scholarly = _validate_checkpoint(
            project, checkpoint_path.resolve(), milestone, lineage,
            recorded_receipt_id,
        )
        if checkpoint["feedback_records"] != record_state.get("feedback_records"):
            raise MilestoneTransactionError("AMC-CHECKPOINT", "accept checkpoint differs from the recorded feedback checkpoint")
        bound_checkpoint = next((
            row for row in record_state.get("artifacts", [])
            if isinstance(row, dict) and row.get("role") == "evidence"
            and row.get("artifact_kind") == "milestone_checkpoint"
            and row.get("lineage_id") == lineage
        ), None)
        if not isinstance(bound_checkpoint, dict) or bound_checkpoint.get("path") != checkpoint_relative or bound_checkpoint.get("sha256") != checkpoint_sha or bound_checkpoint.get("bytes") != checkpoint_size:
            raise MilestoneTransactionError("AMC-CHECKPOINT", "accept requires the exact checkpoint bytes recorded with the deliverable")
        if milestone == "M4" and any(section.get("current_phase") != "Ph3_converged" for section in state.get("sections", {}).values() if isinstance(section, dict)):
            raise MilestoneTransactionError("AMC-M4-NOT-CONVERGED", "M4 acceptance requires every in-scope section at Ph3_converged")
        artifact = next((row for row in record_state.get("artifacts", []) if isinstance(row, dict) and row.get("role") == "deliverable" and row.get("lineage_id") == lineage), None)
        if not isinstance(artifact, dict):
            raise MilestoneTransactionError("AMC-DELIVERABLE", "current primary-lineage deliverable is missing")
        if (
            artifact.get("sha256") != scholarly["artifact"]["sha256"]
            or artifact.get("bytes") != scholarly["artifact"]["byte_length"]
        ):
            raise MilestoneTransactionError(
                "AMC-SCHOLARLY-EVALUATION-STALE",
                "recorded deliverable bytes differ from the qualified scholarly evaluation artifact",
            )
        acceptance_policy: dict[str, Any] | None = None
        policy_dependencies: list[Path] = []
        policy_sha: str | None = None
        terminal_policy_sha: str | None = None
        if milestone == "M4":
            if policy_path is None:
                raise MilestoneTransactionError("AMC-POLICY", "M4 acceptance requires structured current-policy evidence")
            acceptance_policy, policy_file, check8_file, policy_sha = _validate_m4_acceptance_policy(project, policy_path.resolve(), artifact)
            policy_dependencies = [policy_file, check8_file]
            if terminal_evidence_path is not None:
                raise MilestoneTransactionError("AMC-TERMINAL", "terminal evidence is reserved for FINAL")
        elif milestone == "M5":
            if policy_path is not None:
                raise MilestoneTransactionError("AMC-POLICY", "FINAL uses --terminal-evidence, not --policy-evidence")
            if terminal_evidence_path is None:
                raise MilestoneTransactionError("AMC-TERMINAL", "FINAL acceptance requires structured terminal evidence")
            acceptance_policy, policy_file, policy_dependencies, terminal_policy_sha = _validate_m5_terminal_policy(
                project, terminal_evidence_path.resolve(), artifact,
            )
        elif policy_path is not None:
            raise MilestoneTransactionError("AMC-POLICY", "acceptance policy input is reserved for M4")
        elif terminal_evidence_path is not None:
            raise MilestoneTransactionError("AMC-TERMINAL", "terminal evidence is reserved for FINAL")
        approval, approval_relative, approval_sha = _validate_approval(project, approval_path.resolve(), milestone, artifact)
        latest_event_at = framework["events"][-1]["timestamp"]
        if _utc_datetime(approval["approved_at"]) < _utc_datetime(latest_event_at) or _utc_datetime(approval["approved_at"]) > _utc_datetime(at):
            raise MilestoneTransactionError("AMC-APPROVAL", "approval time must follow the recorded checkpoint and not postdate the acceptance event")
        deliverable_file = _safe_project_file(project, artifact["path"], "AMC-DELIVERABLE")[0]
        artifact_dependencies: list[Path] = []
        artifact_expectations: dict[str, str] = {}
        if milestone == "M5":
            for row in record_state.get("artifacts", []):
                if not isinstance(row, dict):
                    continue
                bound_file = _safe_project_file(project, row.get("path"), "AMC-TERMINAL")[0]
                artifact_dependencies.append(bound_file)
                artifact_expectations[str(bound_file.resolve())] = row.get("sha256")
        dependencies = _dependency_snapshot(
            project,
            [checkpoint_file, approval_path.resolve(), deliverable_file, recorded_receipt, *artifact_dependencies, *_checkpoint_dependencies(project, checkpoint, scholarly), *policy_dependencies],
        )
        expected_dependencies = {**artifact_expectations, **_checkpoint_dependency_expectations(project, checkpoint, scholarly)}
        expected_dependencies[str(checkpoint_file.resolve())] = checkpoint_sha
        expected_dependencies[str(approval_path.resolve())] = approval_sha
        expected_dependencies[str(deliverable_file.resolve())] = artifact["sha256"]
        expected_dependencies[str(recorded_receipt.resolve())] = recorded_receipt_sha
        if acceptance_policy is not None:
            expected_dependencies[str(policy_dependencies[0].resolve())] = terminal_policy_sha or policy_sha
            expected_dependencies[str(policy_dependencies[1].resolve())] = acceptance_policy["check8_sha256"]
            if milestone == "M5":
                for row in acceptance_policy["bindings"]:
                    expected_dependencies[str(_safe_project_file(project, row["path"], "AMC-TERMINAL")[0].resolve())] = row["sha256"]
        if any(dependencies.get(path, (None, 0))[0] != expected_sha for path, expected_sha in expected_dependencies.items()):
            raise MilestoneTransactionError("AMC-DEPENDENCY-CHANGED", "a bound dependency changed between validation and snapshot capture")
        _assert_scholarly_dependency_snapshot(dependencies, scholarly)
        proposed = copy.deepcopy(state); proposed_framework = _framework(proposed); target = proposed_framework["milestones"][milestone]
        if acceptance_policy is not None:
            keys = ("manuscript_sha256", "phase", "cycle_id", "check8_path", "check8_sha256", "aggregate_verdict")
            target["policy_evidence"].update({key: acceptance_policy[key] for key in keys})
            if milestone == "M5":
                target["policy_evidence"].update({
                    "terminal_round_id": acceptance_policy["terminal_round_id"],
                    "bindings": acceptance_policy["bindings"],
                })
        target["status"] = "accepted"
        target["approval"] = {"status": "approved", "authority": approval["authority"], "evidence_path": approval_relative, "approved_at": approval["approved_at"]}
        artifact_binding = {"binding_type": "artifact", "path": artifact["path"], "sha256": artifact["sha256"]}
        approval_binding = {"binding_type": "approval", "path": approval_relative, "sha256": approval_sha}
        _append_event(proposed_framework, "milestone_accepted", milestone, at, f"Planner accepted {milestone} after explicit current-byte approval.", authority=approval["authority"], evidence_path=approval_relative, evidence_sha256=approval_sha, bindings=[artifact_binding, approval_binding])
        publish_f9 = handoff_policy == AUDITED_POLICY or emit_f9
        packet_path: Path | None = None
        packet_bytes: bytes | None = None
        if publish_f9:
            packet = _handoff_packet(proposed, milestone, checkpoint, approval, approval_relative)
            if _ACTIVE_AUTHORITY_MODE == "shipment_only":
                # Staging F9 is a proposed handoff, never an authoritative
                # research-master handoff (HARNESS_SHIPMENT_BOUNDARY.md).
                packet["effect_scope"] = "proposal_only"
            packet_relative = handoff_path(LEDGER_TO_PUBLIC[milestone])
            packet_path = project / Path(*PurePosixPath(packet_relative).parts)
            packet_bytes = _json_bytes(packet); packet_sha = hashlib.sha256(packet_bytes).hexdigest()
            target["handoff"] = {"status": "ready", "packet_path": packet_relative, "packet_sha256": packet_sha}
            handoff_binding = {"binding_type": "handoff_packet", "path": packet_relative, "sha256": packet_sha}
            _append_event(proposed_framework, "handoff_ready", milestone, at, f"Planner finalized the accepted {milestone} F9 handoff.", authority=approval["authority"], evidence_path=approval_relative, evidence_sha256=approval_sha, bindings=[handoff_binding])
        else:
            target["handoff"] = {
                "status": "not_applicable",
                "packet_path": None,
                "packet_sha256": None,
            }
        if milestone == "M5":
            proposed["terminal_phase_reached"] = True
            proposed["terminal_round_id"] = acceptance_policy["terminal_round_id"]
        created = bool(packet_path is not None and packet_bytes is not None and _exclusive_bytes(packet_path, packet_bytes))
        try:
            _validate_prospective(project, proposed)
            if milestone == "M5":
                gate = validate_gate(project, proposed, "ph4_terminal_close")
                if not gate.exit_permitted:
                    detail = "; ".join(f"{row.code}: {row.message}" for row in gate.findings[:6])
                    raise MilestoneTransactionError("AMC-TERMINAL-GATE", detail or "Ph4 terminal milestone gate failed")
                from full_run_contract_check import check_terminal
                terminal_findings = check_terminal(project, state_override=proposed)
                if terminal_findings:
                    first = terminal_findings[0]
                    detail = first.get("unmet_findings") or []
                    raise MilestoneTransactionError(
                        "AMC-TERMINAL-CONTRACT",
                        f"{first.get('message', 'full-run terminal contract failed')} first_unmet={json.dumps(detail[:3], sort_keys=True)}",
                    )
            if _sha256(state_path) != prehash:
                raise MilestoneTransactionError("AMC-CONCURRENT-CHANGE", "phase state changed during accept transaction")
            if _before_state_publish is not None:
                _before_state_publish()
            _revalidate_scholarly_binding(project, scholarly)
            _recheck_scholarly_dependencies(project, scholarly)
            _recheck_dependencies(project, dependencies)
            _atomic_replace(state_path, proposed)
        except Exception:
            if created and packet_path is not None:
                try:
                    packet_path.unlink()
                except OSError:
                    pass
            raise


def recover_claim(project: Path, acknowledgement: str) -> Path:
    project = project.resolve(); guard_lifecycle_project_root(project); _enter_authority_mode(project); root = _ensure_control_tree(project)
    if acknowledgement != "inspected-milestone-state-and-journal":
        raise MilestoneTransactionError("AMC-RECOVERY-ACK", "exact acknowledgement is required after inspecting phase_state.json and lifecycle journal")
    claim = root / "claims" / "transaction.lock"
    if not claim.is_file() or _is_link(claim):
        raise MilestoneTransactionError("AMC-RECOVERY", "no plain stale milestone claim exists")
    record = _load_object(claim, "AMC-RECOVERY")
    if record.get("host") != platform.node():
        raise MilestoneTransactionError("AMC-RECOVERY-FOREIGN", "foreign-host claims fail closed; verify remote-owner termination through an administrative recovery path")
    if isinstance(record.get("pid"), int):
        pid = record["pid"]
        alive = False
        proven_dead = False
        if os.name == "nt":
            # os.kill(pid, 0) is not a side-effect-free liveness probe on
            # Windows. Query the process handle and exit code instead.
            import ctypes
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            handle = kernel32.OpenProcess(0x1000, False, pid)
            if pid in {os.getpid(), os.getppid()}:
                alive = True
            elif handle:
                exit_code = ctypes.c_ulong()
                queried = bool(kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)))
                if not queried:
                    kernel32.CloseHandle(handle)
                    raise MilestoneTransactionError("AMC-RECOVERY-LIVENESS", "could not prove whether the local claim owner is live")
                alive = exit_code.value == 259
                proven_dead = not alive
            if handle:
                kernel32.CloseHandle(handle)
            elif not alive:
                error = ctypes.get_last_error()
                proven_dead = error == 87  # ERROR_INVALID_PARAMETER: PID absent.
        else:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                proven_dead = True
            except PermissionError:
                alive = True
            except OSError as exc:
                raise MilestoneTransactionError("AMC-RECOVERY-LIVENESS", f"could not prove whether the local claim owner is live: {exc}") from exc
            else:
                alive = True
        if alive:
            raise MilestoneTransactionError("AMC-RECOVERY-LIVE", "claim owner process is still live")
        if not proven_dead:
            raise MilestoneTransactionError("AMC-RECOVERY-LIVENESS", "local claim owner could not be proven dead; recovery fails closed")
    else:
        raise MilestoneTransactionError("AMC-RECOVERY-LIVENESS", "claim PID is missing or invalid")
    recovery_stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    # F9 is evidence, never state authority. A crash after F9 publication but
    # before the state-last rename can leave an unbound packet. Archive that
    # residue so a retry with changed approval bytes does not dead-end.
    _, state, _ = _load_state(project)
    framework = _framework(state)
    bound_packets = {
        row.get("handoff", {}).get("packet_path")
        for row in framework["milestones"].values()
        if isinstance(row, dict)
        and isinstance(row.get("handoff"), dict)
        and row["handoff"].get("status") in {"ready", "consumed"}
    }
    for milestone in MILESTONES:
        relative = handoff_path(LEDGER_TO_PUBLIC[milestone])
        packet = project / Path(*PurePosixPath(relative).parts)
        if packet.exists() and relative not in bound_packets:
            if not packet.is_file() or _is_link(packet):
                raise MilestoneTransactionError("AMC-RECOVERY", f"unbound F9 residue is not a plain file: {packet}")
            orphan_archive = root / "journal" / f"orphan-{packet.stem}-{recovery_stamp}-{uuid.uuid4().hex}.json"
            _exclusive_bytes(orphan_archive, packet.read_bytes())
            packet.unlink()
    archive = root / "journal" / f"recovered-claim-{recovery_stamp}-{uuid.uuid4().hex}.json"
    _exclusive_bytes(archive, claim.read_bytes())
    claim.unlink()
    return archive
