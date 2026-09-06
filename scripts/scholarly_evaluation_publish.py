#!/usr/bin/env python3
"""Publish supplied scholarly-evaluation judgment as exact governed evidence."""

from __future__ import annotations

import copy
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

import assignment_dispatch_claim as dispatch
import scholarly_claim_register
import scholarly_evaluation
from destination_capability import DestinationRefused, assert_writable
from evidence_publication import publish_committed


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class ScholarlyPublicationError(RuntimeError):
    """Refuse an unsafe or unverifiable scholarly publication."""


def _assert_publication_writable(*paths: Path, purpose: str) -> None:
    for path in paths:
        assert_writable(path, purpose=purpose)


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _binding(project: Path, path: Path) -> dict[str, Any]:
    resolved = path.resolve(strict=True)
    return {
        "path": resolved.relative_to(project).as_posix(),
        "sha256": _file_digest(resolved),
        "byte_length": resolved.stat().st_size,
    }


def evaluation_output_path(project_root: Path, *, evaluation_id: str) -> Path:
    project = project_root.resolve()
    if not _SAFE_ID.fullmatch(evaluation_id):
        raise ScholarlyPublicationError("unsafe evaluation identity")
    path = (
        project
        / "reviews"
        / ".harness"
        / "evidence"
        / "scholarly-evaluation"
        / evaluation_id
        / "evaluation.json"
    ).resolve()
    if not path.is_relative_to(project):
        raise ScholarlyPublicationError("evaluation output escapes project root")
    return path


def _preflight_evaluation_value(
    profile: dict[str, Any], value: dict[str, Any]
) -> None:
    """Reject deterministic C6 defects before consuming Evaluator authority."""

    try:
        scholarly_evaluation._schema_validate(value)
        check_by_id, _, _, _ = scholarly_evaluation._profile_contract(profile)
    except scholarly_evaluation.EvaluationRefusal as exc:
        raise ScholarlyPublicationError(
            f"supplied C6 evidence fails structural preflight: {exc.code}: {exc}"
        ) from exc
    represented = [row["check_id"] for row in value["findings"]]
    omitted = [row["check_id"] for row in value["omitted_checks"]]
    passed = [row["check_id"] for row in value["verdict"]["check_results"]]
    observed = [*represented, *omitted, *passed]
    if (
        len(observed) != len(set(observed))
        or set(observed) != set(check_by_id)
    ):
        raise ScholarlyPublicationError(
            "supplied C6 evidence does not cover each profile check exactly once"
        )
    for row in value["omitted_checks"]:
        check = check_by_id.get(row["check_id"])
        if (
            check is None
            or row["omission_code"] not in check["allowed_omission_codes"]
        ):
            raise ScholarlyPublicationError(
                "supplied C6 evidence uses an unauthorized omission"
            )


def publish_evaluation(
    *,
    project_root: Path,
    artifact: Path,
    evaluation_claim: Path,
    evaluation_id: str,
    milestone: str,
    criteria: list[str],
    scholarly_profile: dict[str, Any],
    claim_register: dict[str, Any],
    judgment: dict[str, Any],
    created_at: str,
) -> dict[str, Any]:
    """Publish an externally supplied judgment without certifying its truth."""

    project = project_root.resolve(strict=True)
    artifact_path = artifact.resolve(strict=True)
    claim_path = evaluation_claim.resolve(strict=True)
    if any(
        not path.is_relative_to(project)
        for path in (artifact_path, claim_path)
    ):
        raise ScholarlyPublicationError("C6 inputs escape the project root")
    evaluation_path = evaluation_output_path(
        project, evaluation_id=evaluation_id
    )
    lane = evaluation_path.parent
    registry_path = lane / "obligation-registry.json"
    generator_envelope_path = lane / "generator-envelope.json"
    criteria_path = lane / "milestone-criteria.json"
    profile_path = lane / "scholarly-profile.json"
    register_path = lane / "claim-register.json"
    support_marker = lane / "support-commit-marker.json"
    _assert_publication_writable(
        evaluation_path,
        registry_path,
        generator_envelope_path,
        criteria_path,
        profile_path,
        register_path,
        support_marker,
        lane / "evaluation-commit-marker.json",
        purpose="scholarly evaluation publication",
    )
    try:
        claim = json.loads(claim_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ScholarlyPublicationError(f"Evaluator claim is unreadable: {exc}") from exc
    artifact_binding = _binding(project, artifact_path)
    if (
        claim.get("claim_kind") != "evaluation"
        or claim.get("role") != "evaluator"
        or claim.get("target_milestone") != milestone
        or claim.get("target_path") != artifact_binding["path"]
        or claim.get("artifact", {}).get("sha256") != artifact_binding["sha256"]
    ):
        raise ScholarlyPublicationError(
            "Evaluator claim, milestone, or artifact binding is split"
        )
    generation_binding = claim.get("generation_claim")
    if not isinstance(generation_binding, dict):
        raise ScholarlyPublicationError("Evaluator claim lacks Generation authority")
    try:
        generation_path = (
            project / generation_binding["path"]
        ).resolve(strict=True)
        generation_claim = json.loads(generation_path.read_text(encoding="utf-8"))
    except (KeyError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ScholarlyPublicationError(f"Generation claim is unreadable: {exc}") from exc
    if (
        not isinstance(criteria, list)
        or not criteria
        or any(not isinstance(item, str) or not item.strip() for item in criteria)
    ):
        raise ScholarlyPublicationError("milestone criteria are empty or malformed")
    registry_data = (
        scholarly_evaluation.ROOT
        / "references"
        / "policies"
        / "obligation_result_registry.v1.json"
    ).read_bytes()
    generator_envelope = {
        "schema_version": "1.0.0",
        "envelope_type": "generator_envelope",
        "dispatch_id": generation_claim["claim_id"],
        "role": "generator",
        "artifact": artifact_binding,
    }
    criteria_value = {
        "schema_version": "1.0.0",
        "milestone": milestone,
        "criteria": criteria,
    }
    profile_value = copy.deepcopy(scholarly_profile)
    profile_value["obligation_registry"] = {
        "path": registry_path.relative_to(project).as_posix(),
        "sha256": _digest(registry_data),
        "byte_length": len(registry_data),
    }
    register_value = copy.deepcopy(claim_register)
    register_value["artifact"] = {
        "path": os.path.relpath(
            artifact_path, register_path.parent
        ).replace("\\", "/"),
        "sha256": artifact_binding["sha256"],
        "byte_length": artifact_binding["byte_length"],
    }
    register_value["review_dispatch"] = {
        "dispatch_id": claim["claim_id"],
        "role": "evaluator",
    }
    support_outputs = [
        (registry_path, registry_data),
        (generator_envelope_path, _canonical(generator_envelope)),
        (criteria_path, _canonical(criteria_value)),
        (profile_path, _canonical(profile_value)),
        (register_path, _canonical(register_value)),
    ]
    support_tx = "scholarly-support-" + _digest(
        b"".join(data for _, data in support_outputs)
    )[:16]
    support_marker_data = _canonical(
        {
            "schema_version": "1.0.0",
            "publication_type": "scholarly_evaluation_support",
            "state": "committed",
            "transaction_id": support_tx,
            "evaluation_id": evaluation_id,
        }
    )
    publish_committed(
        project_root=project,
        transaction_id=support_tx,
        preconditions=[
            (artifact_path, artifact_binding["sha256"]),
            (claim_path, _file_digest(claim_path)),
            (generation_path, _file_digest(generation_path)),
        ],
        inventory_preconditions=[],
        outputs=support_outputs,
        marker=(support_marker, support_marker_data),
    )
    register_result = scholarly_claim_register.validate_register(
        artifact_path, register_path
    )
    if register_result.get("status") != "qualified":
        raise ScholarlyPublicationError(
            f"supplied claim register is not qualified: {register_result}"
        )
    required_judgment = {
        "findings",
        "omitted_checks",
        "obligation_results",
        "independence_level",
        "verdict",
    }
    if not isinstance(judgment, dict) or set(judgment) != required_judgment:
        raise ScholarlyPublicationError(
            "supplied judgment fields are incomplete or include publisher assertions"
        )
    evaluation_value = {
        "schema_version": "1.0.0",
        "evaluation_id": evaluation_id,
        "artifact": artifact_binding,
        "generator_envelope": _binding(project, generator_envelope_path),
        "evaluation_dispatch": {
            "claim": _binding(project, claim_path),
            "consumer_transaction_id": f"scholarly-evaluation:{evaluation_id}",
        },
        "claim_register": _binding(project, register_path),
        "milestone_criteria": _binding(project, criteria_path),
        "scholarly_profile": _binding(project, profile_path),
        "findings": copy.deepcopy(judgment["findings"]),
        "omitted_checks": copy.deepcopy(judgment["omitted_checks"]),
        "obligation_results": copy.deepcopy(judgment["obligation_results"]),
        "dispatch_separation": {
            "generator_claim_id": generation_claim["claim_id"],
            "evaluator_claim_id": claim["claim_id"],
            "separate": True,
            "independence_level": judgment["independence_level"],
        },
        "verdict": copy.deepcopy(judgment["verdict"]),
        "created_at": created_at,
    }
    evaluation_data = _canonical(evaluation_value)
    _preflight_evaluation_value(profile_value, evaluation_value)
    try:
        preflight = scholarly_evaluation.preflight_evaluation(
            project,
            artifact_path,
            register_path,
            evaluation_path,
            evaluation_data,
            claim_path,
        )
    except Exception as exc:
        raise ScholarlyPublicationError(
            f"supplied C6 evidence fails substantive preflight: {exc}"
        ) from exc
    if preflight.get("status") not in {"qualified", "blocked"}:
        raise ScholarlyPublicationError(
            "supplied C6 evidence has no valid preflight disposition"
        )
    dependency_rows = preflight.get("dependencies")
    if not isinstance(dependency_rows, list):
        raise ScholarlyPublicationError(
            "substantive C6 preflight returned no exact dependency inventory"
        )
    dependency_preconditions: list[tuple[Path, str]] = []
    consumption_root = (
        project / "reviews/.harness/assignment/dispatch/consumptions"
    ).resolve()
    for index, row in enumerate(dependency_rows):
        if (
            not isinstance(row, dict)
            or set(row) != {"path", "sha256", "byte_length"}
            or not isinstance(row.get("path"), str)
            or not isinstance(row.get("sha256"), str)
        ):
            raise ScholarlyPublicationError(
                f"substantive C6 dependency {index} is malformed"
            )
        dependency_path = Path(row["path"]).resolve(strict=True)
        if (
            dependency_path == evaluation_path
            or dependency_path.is_relative_to(consumption_root)
        ):
            continue
        if not (
            dependency_path.is_relative_to(project)
            or dependency_path.is_relative_to(scholarly_evaluation.ROOT)
        ):
            raise ScholarlyPublicationError(
                f"substantive C6 dependency {index} escapes project and harness roots"
            )
        dependency_preconditions.append((dependency_path, row["sha256"]))
    evaluation_tx = "scholarly-evaluation-" + _digest(evaluation_data)[:16]
    evaluation_marker = lane / "evaluation-commit-marker.json"
    evaluation_marker_data = _canonical(
        {
            "schema_version": "1.0.0",
            "publication_type": "scholarly_evaluation",
            "state": "committed",
            "transaction_id": evaluation_tx,
            "evaluation_id": evaluation_id,
        }
    )
    publish_committed(
        project_root=project,
        transaction_id=evaluation_tx,
        preconditions=[
            (artifact_path, artifact_binding["sha256"]),
            (claim_path, _file_digest(claim_path)),
            *[(path, _file_digest(path)) for path, _ in support_outputs],
        ],
        inventory_preconditions=[],
        outputs=[(evaluation_path, evaluation_data)],
        marker=(evaluation_marker, evaluation_marker_data),
    )
    _, consumption_path, _ = dispatch.consume_evidence_dispatch_claim(
        project,
        claim_path,
        role="evaluator",
        consumer_transaction_id=f"scholarly-evaluation:{evaluation_id}",
        artifact=artifact_path,
        publication_transaction_id=evaluation_tx,
        product_paths=[evaluation_path],
        commit_marker=evaluation_marker,
        dependency_preconditions=dependency_preconditions,
        consumed_at=created_at,
        recover_exact=True,
    )
    try:
        verified = scholarly_evaluation.verify_evaluation(
            project, artifact_path, register_path, evaluation_path
        )
    except Exception as exc:
        raise ScholarlyPublicationError(
            f"published scholarly evaluation does not verify: {exc}"
        ) from exc
    return {
        "evaluation": evaluation_path,
        "claim_register": register_path,
        "consumption": consumption_path,
        "commit_marker": evaluation_marker,
        "verified": verified,
        "binding": {
            "evidence_path": evaluation_path.relative_to(project).as_posix(),
            "evidence_sha256": _file_digest(evaluation_path),
        },
        "judgment_truth_certified": False,
    }


__all__ = [
    "ScholarlyPublicationError",
    "evaluation_output_path",
    "publish_evaluation",
]


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ScholarlyPublicationError(f"{label} is unreadable: {exc}") from exc
    if not isinstance(value, dict):
        raise ScholarlyPublicationError(f"{label} root is not an object")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--evaluation-claim", type=Path, required=True)
    parser.add_argument("--evaluation-id", required=True)
    parser.add_argument("--milestone", required=True)
    parser.add_argument("--criterion", action="append", required=True)
    parser.add_argument("--scholarly-profile", type=Path, required=True)
    parser.add_argument("--claim-register", type=Path, required=True)
    parser.add_argument("--judgment", type=Path, required=True)
    parser.add_argument("--created-at", required=True)
    args = parser.parse_args(argv)
    try:
        result = publish_evaluation(
            project_root=args.project_root,
            artifact=args.artifact,
            evaluation_claim=args.evaluation_claim,
            evaluation_id=args.evaluation_id,
            milestone=args.milestone,
            criteria=args.criterion,
            scholarly_profile=_load_json(args.scholarly_profile, "scholarly profile"),
            claim_register=_load_json(args.claim_register, "claim register"),
            judgment=_load_json(args.judgment, "Evaluator judgment"),
            created_at=args.created_at,
        )
    except (ScholarlyPublicationError, DestinationRefused, OSError, ValueError, KeyError) as exc:
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "reason_code": "SCHOLARLY-PUBLICATION-REFUSED",
                    "detail": str(exc),
                },
                ensure_ascii=False,
            )
        )
        return 4
    print(
        json.dumps(
            {
                "status": result["verified"]["status"],
                "evaluation": str(result["evaluation"]),
                "consumption": str(result["consumption"]),
                "commit_marker": str(result["commit_marker"]),
                "binding": result["binding"],
                "judgment_truth_certified": False,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
