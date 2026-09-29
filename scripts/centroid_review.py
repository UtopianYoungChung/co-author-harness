#!/usr/bin/env python3
"""Check completed centroid reviews and score explicitly labelled calibration data.

This checks bindings, coverage, and supplied dispatch identity. It does not
authenticate a host execution, decide semantic correctness, or accept research.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "references/schemas/centroid_completed_review.schema.json"
CHECKS = ("carry", "hinge", "attestation", "scope", "voice", "role_split", "join_cadence")
VERDICTS = ("CLEAN", "ADVISORY", "BLOCKER")


class ReviewError(RuntimeError):
    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code, self.detail = code, detail


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ReviewError("CENTROID-REVIEW-JSON", f"duplicate key: {key}")
        value[key] = item
    return value


def _load(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        payload = path.read_bytes()
        value = json.loads(payload.decode("utf-8"), object_pairs_hook=_unique,
                           parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
        if not isinstance(value, dict):
            raise ValueError("JSON root must be an object")
        return value, payload
    except (OSError, UnicodeError, ValueError) as exc:
        raise ReviewError("CENTROID-REVIEW-INPUT", f"{path}: {exc}") from exc


def _require(condition: bool, code: str, detail: str) -> None:
    if not condition:
        raise ReviewError(code, detail)


def _nonblank(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_review(prepared_path: Path, review_path: Path, request_path: Path) -> dict[str, Any]:
    """Replay preparation and validate a role's completed pair record."""
    import centroid_sentence_logic as check
    from jsonschema import Draft202012Validator

    prepared_path, review_path, request_path = (Path(p).resolve(strict=True)
                                               for p in (prepared_path, review_path, request_path))
    prepared, prepared_bytes = _load(prepared_path)
    reviewed, review_bytes = _load(review_path)
    request, request_bytes = _load(request_path)
    schema, _ = _load(SCHEMA)
    errors = sorted(Draft202012Validator(schema).iter_errors(reviewed), key=lambda e: str(e.path))
    _require(not errors, "CENTROID-REVIEW-SCHEMA", str(errors[0].message) if errors else "")
    _require(prepared.get("schema_version") == "2.0.0" and prepared.get("status") == "ready_for_role"
             and prepared.get("mode") == "review", "CENTROID-REVIEW-PREPARED", "a v2 review preparation is required")
    required = {"schema_version", "request_type", "prepared_sha256", "reviewer", "model_requirement", "generation_actor_id"}
    _require(set(request) == required and request.get("schema_version") == "1.0.0"
             and request.get("request_type") == "centroid_review_request",
             "CENTROID-REVIEW-REQUEST", "invalid orchestrator request")
    digest = _sha(prepared_bytes)
    _require(request.get("prepared_sha256") == digest == reviewed["prepared_sha256"],
             "CENTROID-REVIEW-STALE", "prepared receipt hash differs from request/review")
    _require(reviewed["request_sha256"] == _sha(request_bytes),
             "CENTROID-REVIEW-STALE", "orchestrator request hash differs")
    reviewer = reviewed["reviewer"]
    _require(request["reviewer"] == reviewer, "CENTROID-REVIEW-ACTOR", "reviewer differs from assigned execution")
    requirement = request["model_requirement"]
    _require(isinstance(requirement, dict) and set(requirement) == {"model", "effort"}
             and all(_nonblank(requirement[k]) for k in requirement),
             "CENTROID-REVIEW-MODEL", "request must name its required model and effort")
    _require(all(reviewer[k] == requirement[k] for k in ("model", "effort")),
             "CENTROID-REVIEW-MODEL", "review model/effort differs from the orchestrator's required allocation")
    writer = request["generation_actor_id"]
    _require(writer is None or (_nonblank(writer) and writer != reviewer["actor_id"]),
             "CENTROID-REVIEW-ACTOR", "the generating actor cannot self-certify evaluation")
    inputs = prepared.get("inputs")
    _require(isinstance(inputs, dict), "CENTROID-REVIEW-PREPARED", "preparation lacks replayable inputs")
    try:
        fresh = check.build_receipt(SimpleNamespace(**inputs))
    except (RuntimeError, OSError, ValueError, TypeError, AttributeError) as exc:
        raise ReviewError("CENTROID-REVIEW-STALE", f"preparation no longer replays: {exc}") from exc
    # Timestamp, measured duration, and publication paths can change. The complete
    # prose/source/policy inventory must be identical; hashing a file alone is not enough.
    fields = ("instrument", "centroid_source", "mode", "packet_sha256", "manuscript_sha256",
              "manuscript_bytes", "scope_sha256", "scope", "graph_state", "binder_reason_code",
              "policy_sha256", "preparation_code_sha256", "admitted_passages", "sentences", "paragraphs", "pairs")
    for field in fields:
        _require(prepared.get(field) == fresh.get(field), "CENTROID-REVIEW-STALE", f"prepared {field} changed")
    pairs = prepared.get("pairs", [])
    ids = [row["id"] for row in pairs]
    actual = [row["id"] for row in reviewed["pairs"]]
    _require(bool(ids) and len(set(ids)) == len(ids) and len(set(actual)) == len(actual)
             and set(actual) == set(ids), "CENTROID-REVIEW-COVERAGE", "every prepared pair needs exactly one verdict")
    passage_ids = {row["id"] for row in prepared["admitted_passages"]}
    for row in reviewed["pairs"]:
        _require(set(row["attesting_passage_ids"]) <= passage_ids,
                 "CENTROID-REVIEW-PASSAGE", f"unknown passage in {row['id']}")
        statuses = {name: item["status"] for name, item in row["checks"].items()}
        if not row["attesting_passage_ids"]:
            _require(statuses["attestation"] == "issue" and row["verdict"] == "BLOCKER"
                     and bool(reviewed["unresolved_source_gaps"]),
                     "CENTROID-REVIEW-PASSAGE", "missing attestation requires a BLOCKER and a recorded source gap")
        _require(all(statuses[name] != "not_applicable" for name in CHECKS if name != "role_split"),
                 "CENTROID-REVIEW-CHECK", "required pair checks cannot be suppressed")
        issues = sum(value == "issue" for value in statuses.values())
        _require((row["verdict"] == "CLEAN" and issues == 0)
                 or (row["verdict"] != "CLEAN" and issues > 0),
                 "CENTROID-REVIEW-VERDICT", f"verdict and check dispositions disagree in {row['id']}")
    counts = Counter(row["verdict"] for row in reviewed["pairs"])
    expected = {name: counts[name] for name in VERDICTS}
    _require(reviewed["summary"] == expected, "CENTROID-REVIEW-COUNTS", "summary does not match pair verdicts")
    for path, payload in ((prepared_path, prepared_bytes), (review_path, review_bytes), (request_path, request_bytes)):
        _require(path.read_bytes() == payload, "CENTROID-REVIEW-STALE", f"input changed during validation: {path}")
    return {
        "status": "review_validated", "validation_scope": "structure_and_current_bindings",
        "prepared_sha256": digest, "review_sha256": _sha(review_bytes), "request_sha256": _sha(request_bytes),
        "summary": expected, "bound_scope_has_blockers": bool(counts["BLOCKER"] or reviewed["unresolved_source_gaps"]),
        "native_execution_verified": False, "semantic_correctness_verified": False, "research_acceptance": False,
        "limitations": ["Reviewer identity/model/effort are checked against the supplied orchestrator request; host execution is not authenticated.",
                        "Structural validation does not establish that semantic judgments are correct or authorize lifecycle qualification."],
    }


def calibrate(labels: dict[str, Any], predictions: dict[str, Any]) -> dict[str, Any]:
    """Measure supplied labels; never manufacture author labels from predictions."""
    _require(labels.get("schema_version") == "1.0.0" and _nonblank(labels.get("labeler")),
             "CENTROID-CALIBRATION-LABELS", "named labeler and schema version are required")
    provenance = labels.get("label_provenance")
    _require(provenance in {"synthetic", "author_supplied"}, "CENTROID-CALIBRATION-LABELS", "labels must declare their provenance")
    if provenance == "author_supplied":
        evidence = labels.get("label_evidence")
        _require(isinstance(evidence, dict) and _nonblank(evidence.get("path")),
                 "CENTROID-CALIBRATION-LABELS", "author labels need their recorded evidence")
        _require(_sha(Path(evidence["path"]).read_bytes()) == evidence.get("sha256"),
                 "CENTROID-CALIBRATION-LABELS", "author-label evidence hash differs")
    expected, observed = {}, {}
    for records, target, verdict_key in ((labels.get("cases"), expected, "expected"),
                                          (predictions.get("cases"), observed, "verdict")):
        _require(isinstance(records, list) and bool(records), "CENTROID-CALIBRATION-EMPTY", "cases are required")
        for row in records:
            _require(isinstance(row, dict) and _nonblank(row.get("id")) and row["id"] not in target
                     and row.get(verdict_key) in VERDICTS and isinstance(row.get("text_sha256"), str)
                     and len(row["text_sha256"]) == 64 and all(c in "0123456789abcdef" for c in row["text_sha256"]),
                     "CENTROID-CALIBRATION-CASE", "case ids, labels and text hashes must be complete and unique")
            if "text" in row:
                _require(isinstance(row["text"], str) and _sha(row["text"].encode("utf-8")) == row["text_sha256"],
                         "CENTROID-CALIBRATION-STALE", f"case text differs from its declared digest: {row['id']}")
            target[row["id"]] = row
    _require(set(expected) == set(observed), "CENTROID-CALIBRATION-COVERAGE", "label/prediction inventories differ")
    matrix = {truth: {predicted: 0 for predicted in VERDICTS} for truth in VERDICTS}
    costs = {name: [] for name in ("latency_ms", "input_tokens", "output_tokens")}
    for key, truth in expected.items():
        prediction = observed[key]
        _require(truth["text_sha256"] == prediction["text_sha256"], "CENTROID-CALIBRATION-STALE", f"text differs: {key}")
        matrix[truth["expected"]][prediction["verdict"]] += 1
        for name in costs:
            if name in prediction:
                value = prediction[name]
                _require(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
                         and value >= 0, "CENTROID-CALIBRATION-METRIC", f"invalid {name}")
                costs[name].append(value)
    total = len(expected)
    return {
        "status": "calibration_scored", "cases": total, "confusion_matrix": matrix,
        "false_clearances": sum(matrix[t]["CLEAN"] for t in ("ADVISORY", "BLOCKER")),
        "missed_blockers": matrix["BLOCKER"]["CLEAN"] + matrix["BLOCKER"]["ADVISORY"],
        "false_alarms": matrix["CLEAN"]["ADVISORY"] + matrix["CLEAN"]["BLOCKER"],
        "exact_agreement": sum(matrix[v][v] for v in VERDICTS) / total,
        "label_provenance": provenance, "author_labelled_quality_evidence": provenance == "author_supplied",
        "metrics": {name: {"reported_cases": len(values), "mean": sum(values)/len(values) if values else None}
                    for name, values in costs.items()},
        "limitations": ["Label provenance is supplied by the caller; synthetic labels do not measure author agreement.",
                        "Missing timing/token observations remain unmeasured, not zero."],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate")
    for name in ("prepared", "review", "request"):
        validate.add_argument("--" + name, type=Path, required=True)
    score = commands.add_parser("calibrate")
    score.add_argument("--labels", type=Path, required=True)
    score.add_argument("--predictions", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            result = validate_review(args.prepared, args.review, args.request)
        else:
            result = calibrate(_load(args.labels)[0], _load(args.predictions)[0])
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (ReviewError, OSError, ValueError, TypeError, KeyError, ImportError) as exc:
        print(json.dumps({"status": "blocked", "reason_code": getattr(exc, "code", "CENTROID-REVIEW-INPUT"), "detail": str(exc)}))
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
