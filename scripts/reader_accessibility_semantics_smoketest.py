#!/usr/bin/env python3
"""Third-pass semantic adversarial tests for accessibility evidence."""
from __future__ import annotations
import copy, hashlib, json, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import jsonschema
import reader_accessibility_policy as policy
import check8_h_prefilter as h
import milestone_framework_smoketest as fixture
import milestone_framework_validate as mf

def rejected_by_both(mutate) -> None:
    profile = policy.load_profile(); mutate(profile)
    schema = json.loads((ROOT / "references/schemas/reader_accessibility_profile.schema.json").read_text(encoding="utf-8"))
    assert list(jsonschema.Draft202012Validator(schema).iter_errors(profile)), "schema accepted mutation"
    try: policy.validate_profile(profile)
    except policy.PolicyError: pass
    else: raise AssertionError("runtime accepted schema-invalid mutation")

def main() -> int:
    mutations = [
        lambda p: p["thresholds"]["consolidation"]["candidate_gap_words"].update(P1="700"),
        lambda p: p["transitions"]["H"].update(state_owner="wrong"),
        lambda p: p["thresholds"]["cadence"].update(internal_sentence_break_signals=[]),
        lambda p: p["aggregate"].update(blocker=""),
        lambda p: p["sub_checks"]["A"].update(scope=""),
        lambda p: p["sub_checks"]["A"].update(binds_at=[]),
        lambda p: p["thresholds"]["cadence"]["bands"][1].update(min_words=160),
        lambda p: p["thresholds"]["cadence"].update(canonical_sha256="0"*64),
        lambda p: p["adjacent_advisory_checks"]["VE"].update(gate_contribution="aggregate"),
    ]
    for mutate in mutations: rejected_by_both(mutate)

    profile = policy.load_profile()
    assert "corpus_drift" not in profile, "synthetic corpus implementation claim remains"
    assert not hasattr(h, "_corpus_drift"), "synthetic corpus dispatch remains"

    md = "# Introduction\n\nHaving established the baseline, this section shows the result.\n\nFor example, consider the loan officer.\n\nIn summary, these constructs establish the boundary."
    tex = "\\section{Introduction}\nHaving established the baseline, this section shows the result.\n\\subsection{Example}\nFor example, consider the loan officer."
    md_roles = h.nominate_passage_roles(md, Path("paper.md"))
    tex_roles = h.nominate_passage_roles(tex, Path("paper.tex"))
    for roles in (md_roles, tex_roles):
        assert roles and all(item["role"] and item["confidence"] and item["reason"] for item in roles)
        assert any(item["role"] == "section_framing" for item in roles)
        assert any(item["role"] in {"orienting_clause", "worked_example_vignette"} for item in roles)

    clean = {letter: {"findings": []} for letter in "ABCDEFGH"}
    clean["A"]["findings"] = [
        {"finding_id":"a1","severity":"MAJOR","independence_group":"same"},
        {"finding_id":"a2","severity":"MAJOR","independence_group":"same"},
    ]
    active = {key:{"state":"active"} for key in ("G","H","VE")}
    retired = {key:{"state":"retired"} for key in ("G","H","VE")}
    evidence = {"subchecks": clean, "ve":{"aggregate_member":False,"gate_contribution":"none","findings":[]}}
    assert policy.recompute_check8(evidence, active)["aggregate_verdict"] == "BORDERLINE", "same-group MAJORs counted independently"
    clean["G"]["findings"] = [{"finding_id":"g1","severity":"BLOCKER","independence_group":"g"}]
    assert policy.recompute_check8(evidence, active)["aggregate_verdict"] == "BORDERLINE", "active G entered aggregate"
    assert policy.recompute_check8(evidence, retired)["aggregate_verdict"] == "BLOCKER", "retired G excluded"
    bad = copy.deepcopy(evidence); bad["subchecks"]["B"]["findings"]=[{"finding_id":"b","severity":"BANANA","independence_group":"b"}]
    try: policy.recompute_check8(bad, active)
    except policy.PolicyError: pass
    else: raise AssertionError("BANANA severity accepted")

    with tempfile.TemporaryDirectory() as td:
        project=Path(td); ledger=fixture._materialize_native_project(project)
        binding=ledger["policy_bindings"]["reader_accessibility"]
        # Contributor omission plus rehash is semantic forgery.
        resolved_path=project/binding["resolved_path"]
        resolved=json.loads(resolved_path.read_text(encoding="utf-8")); resolved["source_bindings"].pop()
        resolved_path.write_text(json.dumps(resolved),encoding="utf-8")
        binding["source_bindings"]=resolved["source_bindings"]
        binding["resolved_sha256"]=hashlib.sha256(resolved_path.read_bytes()).hexdigest()
        result=mf.validate_document(project,fixture._phase_document(ledger))
        assert any(f.code=="MF-POLICY" for f in result.findings), "omitted contributor and rehash passed"

    with tempfile.TemporaryDirectory() as td:
        project=Path(td); ledger=fixture._materialize_native_project(project)
        state=ledger["policy_bindings"]["reader_accessibility"]["transitions"]["H"]
        event_hash,_=fixture._write_bound_file(project,"reviews/.harness/policy/h.md","evidence\n")
        common={"actor":"planner","authority":"user","approved":True,"evidence_path":"reviews/.harness/policy/h.md","evidence_sha256":event_hash,"cycle_id":"same","manuscript_sha256":"0"*64,"content_sha256":"1"*64}
        state.update({"state":"retired","observed_count":2,"last_event_sequence":2,"events":[{**common,"sequence":1,"event":"policy_transition_observed","observed_count":2},{**common,"sequence":2,"event":"planner_transition_approved","observed_count":2}]})
        result=mf.validate_document(project,fixture._phase_document(ledger))
        assert any(f.code=="MF-POLICY" for f in result.findings), "jump-to-two retirement passed"

    print("OK reader_accessibility_semantics_smoketest")
    return 0
if __name__ == "__main__": raise SystemExit(main())
