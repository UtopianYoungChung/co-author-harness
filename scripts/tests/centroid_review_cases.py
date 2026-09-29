"""Synthetic review-validation cases called by the registered centroid suite."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace


def run_cases(tmp: Path) -> None:
    import centroid_review as review
    import centroid_sentence_logic as check
    import centroid_service as binder

    lane = tmp / "completed-review"
    lane.mkdir(exist_ok=True)
    text = "Synthetic actors share a resource. That dependency requires coordination.\n"
    manuscript = lane / "manuscript.md"
    manuscript.write_bytes(text.encode())
    scoped, scope = binder._scope(text, None)
    packet = binder._general_packet(
        manuscript_path=manuscript, manuscript_bytes=text.encode(), scoped_text=scoped,
        scope=scope, prose=binder._prose_lines(text), mode="review",
        reason_code="GRAPH-SEMANTIC-INELIGIBLE", detail="Synthetic fixture only.",
    )

    def write(name, value):
        path = lane / name
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        return path

    packet_path = write("packet.json", packet)
    passage_path = write("passages.json", [{
        "source_key": check.YU_2011, "locator": "book p. 7",
        "quote": "Synthetic fixture, not a source quotation.",
        "warrant_layer": "surface", "admitted_by": "synthetic fixture author",
    }])
    args = SimpleNamespace(
        packet=str(packet_path), manuscript=str(manuscript), mode="review", heading=None,
        passages=str(passage_path), admitted_by=None, admit_pdf=None, pages=None,
        pdf_source_key=check.YU_2011, centroid_source=check.YU_2011, invoke_only=True,
        extract_receipt=None, evidence_root=None, project_root=None, wiki_root=None,
        workspace_root=None, harness_root=None,
    )
    prepared = check.build_receipt(args)
    prepared_path = write("prepared.json", prepared)
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    request = {
        "schema_version": "1.0.0", "request_type": "centroid_review_request",
        "prepared_sha256": digest(prepared_path),
        "reviewer": {"actor_id": "synthetic-evaluator", "dispatch_id": "synthetic-dispatch",
                     "model": "synthetic-highest", "effort": "synthetic-maximum"},
        "model_requirement": {"model": "synthetic-highest", "effort": "synthetic-maximum"},
        "generation_actor_id": "synthetic-generator",
    }
    request_path = write("request.json", request)
    pairs = [{
        "id": row["id"], "verdict": "CLEAN",
        "checks": {name: {"status": "satisfied", "rationale": "Synthetic positive control."}
                   for name in review.CHECKS},
        "attesting_passage_ids": [prepared["admitted_passages"][0]["id"]],
        "paragraph_purpose": "Explain the synthetic dependency.",
        "derivation": "The dependency motivates coordination in this synthetic example.",
        "warrant_limits": "Synthetic control only; no scholarly verdict.",
    } for row in prepared["pairs"]]
    completed = {
        "schema_version": "1.0.0", "receipt_type": "centroid_completed_review",
        "prepared_sha256": digest(prepared_path), "request_sha256": digest(request_path),
        "reviewer": copy.deepcopy(request["reviewer"]), "pairs": pairs,
        "summary": {"CLEAN": len(pairs), "ADVISORY": 0, "BLOCKER": 0},
        "overall_assessment": "Synthetic structural validation control.",
        "unresolved_source_gaps": [],
    }
    review_path = write("review.json", completed)
    valid = review.validate_review(prepared_path, review_path, request_path)
    assert valid["status"] == "review_validated"
    assert valid["native_execution_verified"] is False
    assert valid["research_acceptance"] is False

    # A missing attestation must be expressible as a blocked review, without
    # inventing a source reference solely to satisfy the output shape.
    blocked = copy.deepcopy(completed)
    blocked["pairs"][0]["verdict"] = "BLOCKER"
    blocked["pairs"][0]["checks"]["attestation"]["status"] = "issue"
    blocked["pairs"][0]["attesting_passage_ids"] = []
    blocked["summary"] = {"CLEAN": 0, "ADVISORY": 0, "BLOCKER": 1}
    blocked["unresolved_source_gaps"] = ["No admitted passage attests the synthetic join."]
    write("review.json", blocked)
    assert review.validate_review(prepared_path, review_path, request_path)["bound_scope_has_blockers"] is True

    def reject(value, label):
        write("review.json", value)
        try:
            review.validate_review(prepared_path, review_path, request_path)
        except review.ReviewError:
            return
        raise AssertionError("review validator accepted " + label)

    bad = copy.deepcopy(completed); bad["pairs"] = []; reject(bad, "missing pair")
    bad = copy.deepcopy(completed); bad["pairs"].append(bad["pairs"][0]); reject(bad, "duplicate pair")
    bad = copy.deepcopy(completed); bad["summary"]["CLEAN"] += 1; reject(bad, "wrong counts")
    bad = copy.deepcopy(completed); bad["pairs"][0]["attesting_passage_ids"] = ["missing"]; reject(bad, "unknown passage")
    bad = copy.deepcopy(completed); bad["reviewer"]["actor_id"] = "synthetic-generator"; reject(bad, "wrong reviewer")
    bad = copy.deepcopy(completed); bad["reviewer"]["model"] = "synthetic-lower"; reject(bad, "downshifted model")
    bad = copy.deepcopy(completed); bad["reviewer"]["effort"] = "synthetic-low"; reject(bad, "downshifted effort")
    bad = copy.deepcopy(completed); bad["pairs"][0]["checks"]["scope"]["status"] = "issue"; reject(bad, "CLEAN with issue")
    bad = copy.deepcopy(completed); bad["pairs"][0]["derivation"] = " "; reject(bad, "empty reasoning")
    bad = copy.deepcopy(completed); bad["pairs"][0]["checks"]["hinge"]["status"] = "not_applicable"; reject(bad, "suppressed hinge review")
    bad = copy.deepcopy(completed); bad["pairs"][0]["attesting_passage_ids"] = []; reject(bad, "unsupported CLEAN")
    bad = copy.deepcopy(blocked); bad["unresolved_source_gaps"] = []; reject(bad, "unexplained missing attestation")
    write("review.json", completed)
    manuscript.write_bytes((text + "Changed premise.\n").encode())
    reject(completed, "stale manuscript")
    manuscript.write_bytes(text.encode())
    stale_preparation = copy.deepcopy(prepared)
    stale_preparation["preparation_code_sha256"]["centroid_text.py"] = "0" * 64
    write("prepared.json", stale_preparation)
    stale_request = copy.deepcopy(request)
    stale_request["prepared_sha256"] = digest(prepared_path)
    write("request.json", stale_request)
    stale_review = copy.deepcopy(completed)
    stale_review["prepared_sha256"] = digest(prepared_path)
    stale_review["request_sha256"] = digest(request_path)
    reject(stale_review, "stale preparation code despite rehashed request")
    write("prepared.json", prepared)
    write("request.json", request)
    stale = json.loads(passage_path.read_text()); stale[0]["quote"] += " Changed."
    write("passages.json", stale)
    reject(completed, "changed source context")

    labels = {"schema_version": "1.0.0", "label_provenance": "synthetic",
              "labeler": "fixture", "cases": [{"id": "a", "text_sha256": "a" * 64, "expected": "BLOCKER"},
                                                {"id": "b", "text_sha256": "b" * 64, "expected": "CLEAN"}]}
    predictions = {"cases": [{"id": "a", "text_sha256": "a" * 64, "verdict": "CLEAN"},
                              {"id": "b", "text_sha256": "b" * 64, "verdict": "BLOCKER"}]}
    metrics = review.calibrate(labels, predictions)
    assert metrics["false_clearances"] == 1 and metrics["false_alarms"] == 1
    assert metrics["author_labelled_quality_evidence"] is False
    labels["cases"][0]["text"] = "Changed fixture text with stale declared digest."
    try:
        review.calibrate(labels, predictions)
    except review.ReviewError:
        pass
    else:
        raise AssertionError("calibration accepted text that differs from its digest")
    del labels["cases"][0]["text"]
    labels["cases"][0]["expected"] = None
    try:
        review.calibrate(labels, predictions)
    except review.ReviewError:
        pass
    else:
        raise AssertionError("unlabelled calibration case was scored")
