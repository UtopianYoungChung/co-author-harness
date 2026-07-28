#!/usr/bin/env python3
"""Adversarial smoke tests for the frozen product-assurance detector evaluation."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "scripts/fixtures/product_assurance_detector_v4"
FREEZE = FIXTURE_DIR / "freeze.json"
EVALUATOR_PATH = ROOT / "scripts/product_assurance_detector_evaluation.py"
DETECTOR_PATH = ROOT / "scripts/product_assurance.py"
CORPUS_SCHEMA_PATH = ROOT / "references/schemas/product_assurance_detector_corpus.schema.json"
SCORE_SCHEMA_PATH = ROOT / "references/schemas/product_assurance_detector_score.schema.json"
COMMON_SCHEMA_PATH = ROOT / "references/schemas/common_scholarly_primitives.schema.json"
PRE_CORPUS_SCHEMA_SHA256 = "e22b7ae404208a405cd1b9cb26fb60209a8bb5eb3d6dce03f0ade9365bd9c32d"
PRE_SCORE_SCHEMA_SHA256 = "813d0ef554b4ad8da34b030ce03c34114cadadc65464bf18bc50859fde4b50d5"
PRE_SCORE_OUTPUTS = {
    "development": {"sha256": "6b1899888c3fa04e4b8a73708e6c84979aefda2f88983fd4d7b53d676d4ccfa8", "byte_length": 11773},
    "held_out": {"sha256": "669f0787a17b5004de6d27d74ee5ecdccfa1a56fe6ea50a8f3e327c254479d4d", "byte_length": 11788},
}


def load_evaluator() -> Any:
    spec = importlib.util.spec_from_file_location("product_assurance_detector_evaluation_test", EVALUATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


evaluation = load_evaluator()


def raw_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def raw_hash_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def tree_snapshot() -> dict[str, str]:
    return {
        path.relative_to(FIXTURE_DIR).as_posix(): raw_hash(path)
        for path in sorted(FIXTURE_DIR.rglob("*"))
        if path.is_file() and not any(part.startswith(".detector-eval-") for part in path.relative_to(FIXTURE_DIR).parts)
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def report_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def schema_accepts(value: dict[str, Any], schema_path: Path) -> bool:
    try:
        evaluation._validate_schema(value, schema_path, "DETECTOR-EVAL-CORPUS-INVALID")
    except evaluation.EvaluationError:
        return False
    return True


def assert_pre_post_vectors(development_corpus: dict[str, Any], development_score: dict[str, Any]) -> int:
    corpus_vectors: list[tuple[str, dict[str, Any], bool]] = [("corpus-valid", development_corpus, True)]
    mutated = copy.deepcopy(development_corpus)
    mutated["items"][0]["artifact"]["sha256"] = "a" * 63
    corpus_vectors.append(("corpus-sha-short", mutated, False))
    mutated = copy.deepcopy(development_corpus)
    mutated["items"][0]["artifact"]["byte_length"] = 0
    corpus_vectors.append(("corpus-byte-zero", mutated, False))
    mutated = copy.deepcopy(development_corpus)
    mutated["items"][0]["artifact"]["extra"] = "closed"
    corpus_vectors.append(("corpus-extra-field", mutated, False))
    mutated = copy.deepcopy(development_corpus)
    mutated["items"][0]["artifact"]["text"] = ""
    corpus_vectors.append(("corpus-empty-text", mutated, False))

    score_vectors: list[tuple[str, dict[str, Any], bool]] = [("score-valid", development_score, True)]
    mutated = copy.deepcopy(development_score)
    mutated["corpus"]["sha256"] = "A" * 64
    score_vectors.append(("score-sha-uppercase", mutated, False))
    mutated = copy.deepcopy(development_score)
    mutated["corpus"]["byte_length"] = 0
    score_vectors.append(("score-file-zero", mutated, False))
    mutated = copy.deepcopy(development_score)
    mutated["corpus"]["path"] = ""
    score_vectors.append(("score-empty-path", mutated, False))
    mutated = copy.deepcopy(development_score)
    mutated["corpus"]["extra"] = "closed"
    score_vectors.append(("score-extra-file-field", mutated, False))
    mutated = copy.deepcopy(development_score)
    mutated["corpus"]["path"] = "C:\\legacy-accepted-path"
    score_vectors.append(("score-nonsafe-path-remains-accepted", mutated, True))
    mutated = copy.deepcopy(development_score)
    mutated["detector"]["sha256"] = "f" * 65
    score_vectors.append(("score-detector-sha-long", mutated, False))

    for name, value, pre_accepted in corpus_vectors:
        post_accepted = schema_accepts(value, CORPUS_SCHEMA_PATH)
        assert post_accepted == pre_accepted, f"corpus pre/post vector changed: {name}"
    for name, value, pre_accepted in score_vectors:
        post_accepted = schema_accepts(value, SCORE_SCHEMA_PATH)
        assert post_accepted == pre_accepted, f"score pre/post vector changed: {name}"
    return len(corpus_vectors) + len(score_vectors)


def copy_frozen_case(temp_dir: Path) -> tuple[Path, dict[str, Any]]:
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    for split in ("development", "held_out"):
        source = ROOT / freeze["splits"][split]["path"]
        target = temp_dir / f"{split}.json"
        shutil.copyfile(source, target)
        freeze["splits"][split]["path"] = target.relative_to(ROOT).as_posix()
        freeze["splits"][split]["sha256"] = raw_hash(target)
        freeze["splits"][split]["byte_length"] = target.stat().st_size
    freeze["held_out_freeze_sha256"] = evaluation.calculate_held_out_freeze_sha256(freeze)
    freeze_path = temp_dir / "freeze.json"
    write_json(freeze_path, freeze)
    return freeze_path, freeze


def rebind_split(temp_dir: Path, freeze: dict[str, Any], split: str, corpus: dict[str, Any]) -> Path:
    corpus_path = temp_dir / f"{split}.json"
    write_json(corpus_path, corpus)
    binding = freeze["splits"][split]
    binding["sha256"] = raw_hash(corpus_path)
    binding["byte_length"] = corpus_path.stat().st_size
    binding["item_count"] = len(corpus["items"])
    freeze["held_out_freeze_sha256"] = evaluation.calculate_held_out_freeze_sha256(freeze)
    freeze_path = temp_dir / "freeze.json"
    write_json(freeze_path, freeze)
    return freeze_path


def expect_refusal(code: str, action: Callable[[], Any]) -> None:
    try:
        action()
    except evaluation.EvaluationError as exc:
        assert exc.code == code, f"expected {code}, got {exc.code}: {exc}"
    else:
        raise AssertionError(f"expected refusal {code}")


def assert_matrix(report: dict[str, Any]) -> None:
    assert len(report["item_results"]) == 8
    assert report["aggregate"] == {
        "tp": 4, "fp": 0, "fn": 0, "tn": 28,
        "support": 4, "predicted_positive": 4,
        "precision": 1.0, "recall": 1.0,
    }
    for matrix in report["per_code"]:
        assert matrix == {
            "code": matrix["code"],
            "tp": 1, "fp": 0, "fn": 0, "tn": 7,
            "support": 1, "predicted_positive": 1,
            "precision": 1.0, "recall": 1.0,
        }


def main() -> int:
    before = tree_snapshot()
    detector_source = DETECTOR_PATH.read_text(encoding="utf-8")
    assert "product_assurance_detector_v4" not in detector_source
    assert "held_out.json" not in detector_source
    assert raw_hash(COMMON_SCHEMA_PATH) == evaluation.COMMON_SCHEMA_SHA256
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert freeze["held_out_freeze_sha256"] == evaluation.calculate_held_out_freeze_sha256(freeze)

    development = evaluation.score(FREEZE, "development", purpose="tuning")
    held_out = evaluation.score(FREEZE, "held_out", purpose="scoring")
    assert_matrix(development)
    assert_matrix(held_out)
    for split, report in (("development", development), ("held_out", held_out)):
        serialized = report_bytes(report)
        assert raw_hash_bytes(serialized) == PRE_SCORE_OUTPUTS[split]["sha256"]
        assert len(serialized) == PRE_SCORE_OUTPUTS[split]["byte_length"]
    development_corpus = json.loads((FIXTURE_DIR / "development.json").read_text(encoding="utf-8"))
    equivalence_vectors = assert_pre_post_vectors(development_corpus, development)
    expect_refusal(
        "DETECTOR-EVAL-SPLIT-MISUSE",
        lambda: evaluation.score(FREEZE, "held_out", purpose="tuning"),
    )

    with tempfile.TemporaryDirectory(prefix=".detector-eval-", dir=FIXTURE_DIR) as raw_temp:
        temp_dir = Path(raw_temp)

        freeze_path, copied_freeze = copy_frozen_case(temp_dir)
        held_path = temp_dir / "held_out.json"
        held_path.write_bytes(held_path.read_bytes() + b" ")
        expect_refusal("DETECTOR-EVAL-FREEZE-STALE", lambda: evaluation.score(freeze_path, "held_out"))

        freeze_path, copied_freeze = copy_frozen_case(temp_dir)
        held_corpus = json.loads((temp_dir / "held_out.json").read_text(encoding="utf-8"))
        held_corpus["items"][0]["labels"][0]["expected_candidate"] = not held_corpus["items"][0]["labels"][0]["expected_candidate"]
        write_json(temp_dir / "held_out.json", held_corpus)
        expect_refusal("DETECTOR-EVAL-FREEZE-STALE", lambda: evaluation.score(freeze_path, "held_out"))

        freeze_path, copied_freeze = copy_frozen_case(temp_dir)
        changed_detector = temp_dir / "product_assurance.py"
        changed_detector.write_bytes(DETECTOR_PATH.read_bytes() + b"\n# changed detector bytes\n")
        copied_freeze["detector"]["path"] = changed_detector.relative_to(ROOT).as_posix()
        copied_freeze["held_out_freeze_sha256"] = evaluation.calculate_held_out_freeze_sha256(copied_freeze)
        write_json(freeze_path, copied_freeze)
        expect_refusal("DETECTOR-EVAL-FREEZE-STALE", lambda: evaluation.score(freeze_path, "development"))

        freeze_path, copied_freeze = copy_frozen_case(temp_dir)
        development_corpus = json.loads((temp_dir / "development.json").read_text(encoding="utf-8"))
        development_corpus["codes"].append("UNKNOWN-CODE")
        development_corpus["items"][0]["labels"].append({
            "code": "UNKNOWN-CODE",
            "expected_candidate": False,
            "rationale": "Synthetic unsupported-code refusal probe.",
            "semantics": "candidate expectation only; not a factual or scholarly judgment",
        })
        freeze_path = rebind_split(temp_dir, copied_freeze, "development", development_corpus)
        expect_refusal("DETECTOR-EVAL-CODE-UNKNOWN", lambda: evaluation.score(freeze_path, "development"))

        freeze_path, copied_freeze = copy_frozen_case(temp_dir)
        development_corpus = json.loads((temp_dir / "development.json").read_text(encoding="utf-8"))
        development_corpus["items"].append(copy.deepcopy(development_corpus["items"][0]))
        freeze_path = rebind_split(temp_dir, copied_freeze, "development", development_corpus)
        expect_refusal("DETECTOR-EVAL-CORPUS-INVALID", lambda: evaluation.score(freeze_path, "development"))

        freeze_path, copied_freeze = copy_frozen_case(temp_dir)
        development_corpus = json.loads((temp_dir / "development.json").read_text(encoding="utf-8"))
        development_corpus["items"][0]["labels"].append(copy.deepcopy(development_corpus["items"][0]["labels"][0]))
        freeze_path = rebind_split(temp_dir, copied_freeze, "development", development_corpus)
        expect_refusal("DETECTOR-EVAL-CORPUS-INVALID", lambda: evaluation.score(freeze_path, "development"))

        freeze_path, copied_freeze = copy_frozen_case(temp_dir)
        development_corpus = json.loads((temp_dir / "development.json").read_text(encoding="utf-8"))
        held_corpus = json.loads((temp_dir / "held_out.json").read_text(encoding="utf-8"))
        held_corpus["items"][0]["artifact"] = copy.deepcopy(development_corpus["items"][0]["artifact"])
        freeze_path = rebind_split(temp_dir, copied_freeze, "held_out", held_corpus)
        expect_refusal("DETECTOR-EVAL-CONTAMINATION", lambda: evaluation.score(freeze_path, "held_out"))

        freeze_path, copied_freeze = copy_frozen_case(temp_dir)
        report = evaluation.score(freeze_path, "development")
        report_path = temp_dir / "score.json"
        write_json(report_path, report)
        evaluation.validate_score(report_path, freeze_path)
        report["aggregate"]["tn"] += 1
        write_json(report_path, report)
        expect_refusal("DETECTOR-EVAL-RESULT-INVALID", lambda: evaluation.validate_score(report_path, freeze_path))

        original_common_schema = evaluation.COMMON_SCHEMA
        try:
            evaluation.COMMON_SCHEMA = temp_dir / "missing-common.schema.json"
            expect_refusal("DETECTOR-EVAL-CORPUS-INVALID", lambda: evaluation.score(FREEZE, "development"))
            wrong_common = json.loads(COMMON_SCHEMA_PATH.read_text(encoding="utf-8"))
            wrong_common["$id"] = "https://co-author-harness.local/schemas/wrong-common.schema.json"
            wrong_common_path = temp_dir / "wrong-common.schema.json"
            write_json(wrong_common_path, wrong_common)
            evaluation.COMMON_SCHEMA = wrong_common_path
            expect_refusal("DETECTOR-EVAL-CORPUS-INVALID", lambda: evaluation.score(FREEZE, "development"))
            changed_common = json.loads(COMMON_SCHEMA_PATH.read_text(encoding="utf-8"))
            changed_common["$comment"] = "same identity with deliberately changed synthetic test bytes"
            changed_common_path = temp_dir / "changed-common.schema.json"
            write_json(changed_common_path, changed_common)
            evaluation.COMMON_SCHEMA = changed_common_path
            expect_refusal("DETECTOR-EVAL-CORPUS-INVALID", lambda: evaluation.score(FREEZE, "development"))
        finally:
            evaluation.COMMON_SCHEMA = original_common_schema

        original_corpus_schema = evaluation.CORPUS_SCHEMA
        try:
            unresolved_schema = json.loads(CORPUS_SCHEMA_PATH.read_text(encoding="utf-8"))
            unresolved_schema["$defs"]["textBinding"]["properties"]["sha256"]["$ref"] = (
                "https://co-author-harness.local/schemas/unresolved-resource.schema.json#/$defs/sha256"
            )
            unresolved_schema_path = temp_dir / "unresolved-corpus.schema.json"
            write_json(unresolved_schema_path, unresolved_schema)
            evaluation.CORPUS_SCHEMA = unresolved_schema_path
            expect_refusal("DETECTOR-EVAL-CORPUS-INVALID", lambda: evaluation.score(FREEZE, "development"))
        finally:
            evaluation.CORPUS_SCHEMA = original_corpus_schema

        forbidden = ROOT / "outputs/co-author-harness/detector-evaluation-smoketest.json"
        assert not forbidden.exists()
        assert evaluation.main([
            "score", "--freeze", str(FREEZE), "--split", "development",
            "--out", str(forbidden),
        ]) == 2
        assert not forbidden.exists(), "misrouted detector score was written"

    assert evaluation._metrics(tp=0, fp=0, fn=0, tn=1) == {
        "tp": 0, "fp": 0, "fn": 0, "tn": 1,
        "support": 0, "predicted_positive": 0,
        "precision": None, "recall": None,
    }
    assert tree_snapshot() == before, "smoketest left fixture residue or mutated frozen bytes"
    print(json.dumps({
        "status": "PASS",
        "development_items": len(development["item_results"]),
        "held_out_items": len(held_out["item_results"]),
        "per_code_matrix": {"tp": 1, "fp": 0, "fn": 0, "tn": 7},
        "aggregate_matrix": {"tp": 4, "fp": 0, "fn": 0, "tn": 28},
        "held_out_freeze_sha256": freeze["held_out_freeze_sha256"],
        "attack_cases": 13,
        "equivalence_vectors": equivalence_vectors,
        "pre_schema_sha256": {
            "corpus": PRE_CORPUS_SCHEMA_SHA256,
            "score": PRE_SCORE_SCHEMA_SHA256,
        },
        "post_schema_sha256": {
            "corpus": raw_hash(CORPUS_SCHEMA_PATH),
            "score": raw_hash(SCORE_SCHEMA_PATH),
        },
        "common_schema_sha256": raw_hash(COMMON_SCHEMA_PATH),
        "score_output_sha256": {split: value["sha256"] for split, value in PRE_SCORE_OUTPUTS.items()},
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
