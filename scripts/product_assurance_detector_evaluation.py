#!/usr/bin/env python3
"""Evaluate product-assurance candidate detectors on frozen synthetic corpora.

The labels and scores produced here are candidate-detector test evidence only.
They do not certify scholarly truth, promote a finding, or affect research state.

Scope: `score()` exercises `product_assurance._semantic_findings` and nothing
else. It never enters `product_assurance.build()`, whose inputs a corpus item
cannot carry, so a change confined to `build()` moves no number here and only
DETECTOR-EVAL-FREEZE-STALE will see it. `build()` is covered by
`scripts/product_assurance_smoketest.py` instead. Details and the worked example:
`scripts/fixtures/product_assurance_detector_v4/README.md`.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

import destination_capability


ROOT = Path(__file__).resolve().parents[1]
CORPUS_SCHEMA = ROOT / "references/schemas/product_assurance_detector_corpus.schema.json"
SCORE_SCHEMA = ROOT / "references/schemas/product_assurance_detector_score.schema.json"
COMMON_SCHEMA = ROOT / "references/schemas/common_scholarly_primitives.schema.json"
COMMON_SCHEMA_ID = "https://co-author-harness.local/schemas/common_scholarly_primitives.schema.json"
COMMON_SCHEMA_SHA256 = "b5a397a4e90431c422a788414e40c1eed6ca5ba98191ed0aecaaa70aac3365e4"
SUPPORTED_CODES = (
    "EMPIRICAL-UNSUPPORTED",
    "INSIDER-NEGATION",
    "REGISTER-ABSENT",
    "TERM-COINAGE",
)
FREEZE_FIELDS = {
    "schema_version",
    "freeze_id",
    "frozen_at",
    "candidate_only",
    "judgment_truth_certified",
    "detector",
    "splits",
    "held_out_freeze_sha256",
}
DETECTOR_FIELDS = {"name", "version", "path", "sha256", "byte_length"}
SPLIT_FIELDS = {"path", "sha256", "byte_length", "item_count", "tuning_use"}


class EvaluationError(RuntimeError):
    """A fail-closed detector-evaluation refusal."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise EvaluationError("DETECTOR-EVAL-CORPUS-INVALID", f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _load_json(path: Path, *, result: bool = False) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        code = "DETECTOR-EVAL-RESULT-INVALID" if result else "DETECTOR-EVAL-FREEZE-STALE"
        raise EvaluationError(code, f"cannot read {path}: {exc}") from exc
    try:
        value = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_strict_pairs)
    except EvaluationError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        code = "DETECTOR-EVAL-RESULT-INVALID" if result else "DETECTOR-EVAL-CORPUS-INVALID"
        raise EvaluationError(code, f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise EvaluationError("DETECTOR-EVAL-CORPUS-INVALID", f"top level of {path} must be an object")
    return value, raw


def _schema(path: Path) -> dict[str, Any]:
    value, _ = _load_json(path)
    return value


def _validate_schema(instance: dict[str, Any], schema_path: Path, code: str) -> None:
    schema = _schema(schema_path)
    try:
        common, common_raw = _load_json(COMMON_SCHEMA)
    except EvaluationError as exc:
        raise EvaluationError(code, f"common schema is missing or unreadable: {exc}") from exc
    if common.get("$id") != COMMON_SCHEMA_ID:
        raise EvaluationError(code, f"common schema identity must be {COMMON_SCHEMA_ID}")
    if _sha256(common_raw) != COMMON_SCHEMA_SHA256:
        raise EvaluationError(code, f"common schema bytes must match {COMMON_SCHEMA_SHA256}")
    try:
        Draft202012Validator.check_schema(common)
        Draft202012Validator.check_schema(schema)
        registry = Registry().with_resource(COMMON_SCHEMA_ID, Resource.from_contents(common))
        validator = Draft202012Validator(schema, registry=registry)
        errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.absolute_path))
    except EvaluationError:
        raise
    except Exception as exc:
        raise EvaluationError(code, f"schema registration or resolution failed: {exc}") from exc
    if errors:
        error = errors[0]
        where = "/".join(str(part) for part in error.absolute_path) or "<root>"
        raise EvaluationError(code, f"{schema_path.name} rejection at {where}: {error.message}")


def _resolve_package_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise EvaluationError("DETECTOR-EVAL-FREEZE-STALE", f"freeze path must be package-relative: {value}")
    resolved = (ROOT / path).resolve()
    try:
        resolved.relative_to(ROOT)
    except ValueError as exc:
        raise EvaluationError("DETECTOR-EVAL-FREEZE-STALE", f"freeze path escapes package: {value}") from exc
    return resolved


def _closed_keys(value: Any, expected: set[str], where: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        actual = sorted(value) if isinstance(value, dict) else type(value).__name__
        raise EvaluationError("DETECTOR-EVAL-FREEZE-STALE", f"{where} fields are {actual}, expected {sorted(expected)}")


def _file_binding(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": _sha256(raw), "byte_length": len(raw)}


def held_out_freeze_material(freeze: dict[str, Any]) -> dict[str, Any]:
    """Return the exact material whose canonical SHA-256 freezes held-out use."""
    return {
        "schema_version": freeze["schema_version"],
        "freeze_id": freeze["freeze_id"],
        "frozen_at": freeze["frozen_at"],
        "candidate_only": freeze["candidate_only"],
        "judgment_truth_certified": freeze["judgment_truth_certified"],
        "detector": freeze["detector"],
        "development": freeze["splits"]["development"],
        "held_out": freeze["splits"]["held_out"],
        "sequence": [
            "development_frozen",
            "detector_candidate_frozen",
            "held_out_labels_and_bytes_frozen",
            "scoring_authorized",
        ],
    }


def calculate_held_out_freeze_sha256(freeze: dict[str, Any]) -> str:
    return _sha256(_canonical_json(held_out_freeze_material(freeze)))


def _validate_freeze_shape(freeze: dict[str, Any]) -> None:
    _closed_keys(freeze, FREEZE_FIELDS, "freeze")
    if freeze["schema_version"] != "1.0.0" or freeze["candidate_only"] is not True:
        raise EvaluationError("DETECTOR-EVAL-FREEZE-STALE", "freeze must be candidate-only schema 1.0.0")
    if freeze["judgment_truth_certified"] is not False:
        raise EvaluationError("DETECTOR-EVAL-FREEZE-STALE", "freeze may not certify judgment truth")
    _closed_keys(freeze["detector"], DETECTOR_FIELDS, "freeze.detector")
    if not isinstance(freeze["splits"], dict) or set(freeze["splits"]) != {"development", "held_out"}:
        raise EvaluationError("DETECTOR-EVAL-FREEZE-STALE", "freeze must bind development and held_out exactly")
    for split in ("development", "held_out"):
        _closed_keys(freeze["splits"][split], SPLIT_FIELDS, f"freeze.splits.{split}")
    if freeze["splits"]["development"]["tuning_use"] != "permitted":
        raise EvaluationError("DETECTOR-EVAL-SPLIT-MISUSE", "development must be the sole tuning-permitted split")
    if freeze["splits"]["held_out"]["tuning_use"] != "prohibited":
        raise EvaluationError("DETECTOR-EVAL-SPLIT-MISUSE", "held-out tuning must be prohibited")
    expected = calculate_held_out_freeze_sha256(freeze)
    if freeze["held_out_freeze_sha256"] != expected:
        raise EvaluationError("DETECTOR-EVAL-FREEZE-STALE", "held-out freeze material hash changed")


def _validate_corpus(corpus: dict[str, Any], expected_split: str) -> None:
    _validate_schema(corpus, CORPUS_SCHEMA, "DETECTOR-EVAL-CORPUS-INVALID")
    if corpus["split"] != expected_split:
        raise EvaluationError("DETECTOR-EVAL-SPLIT-MISUSE", f"expected {expected_split}, found {corpus['split']}")
    if tuple(corpus["codes"]) != SUPPORTED_CODES:
        unknown = sorted(set(corpus["codes"]) - set(SUPPORTED_CODES))
        if unknown:
            raise EvaluationError("DETECTOR-EVAL-CODE-UNKNOWN", f"unsupported corpus codes: {unknown}")
        raise EvaluationError("DETECTOR-EVAL-CORPUS-INVALID", "corpus code order or coverage changed")
    ids: set[str] = set()
    for item in corpus["items"]:
        if item["id"] in ids:
            raise EvaluationError("DETECTOR-EVAL-CORPUS-INVALID", f"duplicate item id: {item['id']}")
        ids.add(item["id"])
        for field in ("artifact", "corpus"):
            raw = item[field]["text"].encode("utf-8")
            if _sha256(raw) != item[field]["sha256"] or len(raw) != item[field]["byte_length"]:
                raise EvaluationError("DETECTOR-EVAL-CORPUS-INVALID", f"{item['id']} {field} byte binding changed")
        codes = [label["code"] for label in item["labels"]]
        if len(codes) != len(set(codes)):
            raise EvaluationError("DETECTOR-EVAL-CORPUS-INVALID", f"duplicate label code in {item['id']}")
        unknown = sorted(set(codes) - set(SUPPORTED_CODES))
        if unknown:
            raise EvaluationError("DETECTOR-EVAL-CODE-UNKNOWN", f"unsupported item label codes: {unknown}")
        if tuple(codes) != SUPPORTED_CODES:
            raise EvaluationError("DETECTOR-EVAL-CORPUS-INVALID", f"{item['id']} must label every supported code in order")


def _load_and_bind_split(freeze: dict[str, Any], split: str) -> tuple[dict[str, Any], Path, bytes]:
    binding = freeze["splits"][split]
    path = _resolve_package_path(binding["path"])
    corpus, raw = _load_json(path)
    if _sha256(raw) != binding["sha256"] or len(raw) != binding["byte_length"]:
        raise EvaluationError("DETECTOR-EVAL-FREEZE-STALE", f"{split} corpus bytes changed after freeze")
    _validate_corpus(corpus, split)
    if len(corpus["items"]) != binding["item_count"]:
        raise EvaluationError("DETECTOR-EVAL-FREEZE-STALE", f"{split} item count changed after freeze")
    return corpus, path, raw


def _assert_no_contamination(development: dict[str, Any], held_out: dict[str, Any]) -> None:
    dev_ids = {item["id"] for item in development["items"]}
    held_ids = {item["id"] for item in held_out["items"]}
    duplicate_ids = sorted(dev_ids & held_ids)
    if duplicate_ids:
        raise EvaluationError("DETECTOR-EVAL-CONTAMINATION", f"cross-split duplicate ids: {duplicate_ids}")
    for field in ("artifact", "corpus"):
        dev_hashes = {item[field]["sha256"] for item in development["items"]}
        held_hashes = {item[field]["sha256"] for item in held_out["items"]}
        duplicates = sorted(dev_hashes & held_hashes)
        if duplicates:
            raise EvaluationError("DETECTOR-EVAL-CONTAMINATION", f"cross-split duplicate {field} text hashes: {duplicates}")


def _load_detector(freeze: dict[str, Any]) -> tuple[Any, Path, bytes]:
    binding = freeze["detector"]
    path = _resolve_package_path(binding["path"])
    try:
        before = path.read_bytes()
    except OSError as exc:
        raise EvaluationError("DETECTOR-EVAL-FREEZE-STALE", f"cannot read detector: {exc}") from exc
    if _sha256(before) != binding["sha256"] or len(before) != binding["byte_length"]:
        raise EvaluationError("DETECTOR-EVAL-FREEZE-STALE", "detector executable bytes changed after freeze")
    module_name = f"_product_assurance_frozen_{binding['sha256'][:12]}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise EvaluationError("DETECTOR-EVAL-FREEZE-STALE", "cannot load frozen detector executable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    inserted = str(path.parent) not in sys.path
    if inserted:
        sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        if inserted:
            sys.path.remove(str(path.parent))
        sys.modules.pop(module_name, None)
    after = path.read_bytes()
    if after != before:
        raise EvaluationError("DETECTOR-EVAL-FREEZE-STALE", "detector bytes changed while loading")
    if getattr(module, "DETECTOR_NAME", None) != binding["name"] or getattr(module, "DETECTOR_VERSION", None) != binding["version"]:
        raise EvaluationError("DETECTOR-EVAL-FREEZE-STALE", "detector identity/version does not match freeze")
    if not callable(getattr(module, "_semantic_findings", None)):
        raise EvaluationError("DETECTOR-EVAL-FREEZE-STALE", "frozen detector has no semantic finding callable")
    return module, path, before


def _metrics(*, tp: int, fp: int, fn: int, tn: int) -> dict[str, Any]:
    predicted_positive = tp + fp
    support = tp + fn
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "support": support,
        "predicted_positive": predicted_positive,
        "precision": tp / predicted_positive if predicted_positive else None,
        "recall": tp / support if support else None,
    }


def _matrix(outcomes: Iterable[str]) -> dict[str, Any]:
    counts = Counter(outcomes)
    return _metrics(tp=counts["TP"], fp=counts["FP"], fn=counts["FN"], tn=counts["TN"])


def _outcome(expected: bool, observed: bool) -> str:
    return { (True, True): "TP", (False, True): "FP", (True, False): "FN", (False, False): "TN" }[(expected, observed)]


def score(freeze_path: Path, split: str, *, purpose: str = "scoring") -> dict[str, Any]:
    if split not in {"development", "held_out"} or purpose not in {"scoring", "tuning"}:
        raise EvaluationError("DETECTOR-EVAL-SPLIT-MISUSE", f"invalid split/purpose: {split}/{purpose}")
    if split == "held_out" and purpose != "scoring":
        raise EvaluationError("DETECTOR-EVAL-SPLIT-MISUSE", "held-out labels and examples are read-only and may not tune the detector")
    freeze_path = freeze_path.resolve()
    freeze, freeze_raw = _load_json(freeze_path)
    _validate_freeze_shape(freeze)
    development, development_path, development_raw = _load_and_bind_split(freeze, "development")
    held_out, held_out_path, held_out_raw = _load_and_bind_split(freeze, "held_out")
    _assert_no_contamination(development, held_out)
    detector, detector_path, detector_raw = _load_detector(freeze)
    selected = development if split == "development" else held_out
    selected_path = development_path if split == "development" else held_out_path
    selected_raw = development_raw if split == "development" else held_out_raw
    item_results: list[dict[str, Any]] = []
    per_code_outcomes: dict[str, list[str]] = {code: [] for code in SUPPORTED_CODES}
    for item in selected["items"]:
        findings = detector._semantic_findings(
            Path("synthetic") / f"{item['id']}.md",
            item["artifact"]["text"],
            item["corpus"]["text"],
        )
        observed_codes = {finding.get("code") for finding in findings}
        unknown = sorted(str(code) for code in observed_codes if code not in SUPPORTED_CODES)
        if unknown:
            raise EvaluationError("DETECTOR-EVAL-CODE-UNKNOWN", f"detector emitted unsupported codes: {unknown}")
        label_results = []
        for label in item["labels"]:
            observed = label["code"] in observed_codes
            outcome = _outcome(label["expected_candidate"], observed)
            per_code_outcomes[label["code"]].append(outcome)
            label_results.append({
                "code": label["code"],
                "expected_candidate": label["expected_candidate"],
                "observed_candidate": observed,
                "outcome": outcome,
                "rationale": label["rationale"],
            })
        item_results.append({
            "id": item["id"],
            "artifact_sha256": item["artifact"]["sha256"],
            "corpus_sha256": item["corpus"]["sha256"],
            "labels": label_results,
        })
    if detector_path.read_bytes() != detector_raw:
        raise EvaluationError("DETECTOR-EVAL-FREEZE-STALE", "detector bytes changed during scoring")
    if development_path.read_bytes() != development_raw or held_out_path.read_bytes() != held_out_raw:
        raise EvaluationError("DETECTOR-EVAL-FREEZE-STALE", "corpus or labels changed during scoring")
    matrices = [{"code": code, **_matrix(per_code_outcomes[code])} for code in SUPPORTED_CODES]
    aggregate = _matrix(outcome for outcomes in per_code_outcomes.values() for outcome in outcomes)
    report = {
        "schema_version": "1.0.0",
        "report_type": "product_assurance_detector_score",
        "split": split,
        "candidate_only": True,
        "judgment_truth_certified": False,
        "promotion_effect": "none",
        "detector": freeze["detector"],
        "corpus": {"path": selected_path.relative_to(ROOT).as_posix(), "sha256": _sha256(selected_raw), "byte_length": len(selected_raw)},
        "freeze": {
            "path": freeze_path.relative_to(ROOT).as_posix() if freeze_path.is_relative_to(ROOT) else str(freeze_path),
            "sha256": _sha256(freeze_raw),
            "held_out_freeze_sha256": freeze["held_out_freeze_sha256"],
        },
        "item_results": item_results,
        "per_code": matrices,
        "aggregate": aggregate,
    }
    _validate_schema(report, SCORE_SCHEMA, "DETECTOR-EVAL-RESULT-INVALID")
    return report


def validate_score(score_path: Path, freeze_path: Path) -> dict[str, Any]:
    observed, _ = _load_json(score_path, result=True)
    _validate_schema(observed, SCORE_SCHEMA, "DETECTOR-EVAL-RESULT-INVALID")
    expected = score(freeze_path, observed.get("split", ""), purpose="scoring")
    if observed != expected:
        raise EvaluationError("DETECTOR-EVAL-RESULT-INVALID", "score report does not exactly match recomputation")
    return observed


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    score_parser = subparsers.add_parser("score")
    score_parser.add_argument("--freeze", type=Path, required=True)
    score_parser.add_argument("--split", choices=("development", "held_out"), required=True)
    score_parser.add_argument("--purpose", choices=("scoring", "tuning"), default="scoring")
    score_parser.add_argument("--out", type=Path, required=True)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--freeze", type=Path, required=True)
    validate_parser.add_argument("--score", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "score":
            destination_capability.assert_writable(
                args.out.resolve(), purpose="product assurance detector score"
            )
            report = score(args.freeze, args.split, purpose=args.purpose)
            _write_json(args.out, report)
            print(json.dumps({"status": "PASS", "split": args.split, "aggregate": report["aggregate"]}, sort_keys=True))
        else:
            report = validate_score(args.score, args.freeze)
            print(json.dumps({"status": "PASS", "split": report["split"], "aggregate": report["aggregate"]}, sort_keys=True))
    except (EvaluationError, destination_capability.DestinationRefused) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
