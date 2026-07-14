#!/usr/bin/env python3
"""Third-pass semantic adversarial tests for accessibility evidence."""
from __future__ import annotations
import copy, hashlib, json, shutil, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import jsonschema
import reader_accessibility_policy as policy
import check8_h_prefilter as h
import check8_g_prefilter as g
import milestone_framework_smoketest as fixture
import milestone_framework_validate as mf
import artefact_frontmatter_validate as frontmatter

def schema_const_paths(schema, root, path=()):
    paths=[]
    if "$ref" in schema:
        node=root
        for token in schema["$ref"][2:].split("/"): node=node[token]
        paths.extend(schema_const_paths(node,root,path))
    if "const" in schema: paths.append((path,schema["const"]))
    for key, child in schema.get("properties",{}).items(): paths.extend(schema_const_paths(child,root,(*path,key)))
    return paths

def changed(value):
    if isinstance(value,bool): return not value
    if isinstance(value,str): return value+"__forged"
    if isinstance(value,(int,float)): return value+1
    if isinstance(value,list): return [*value,"__forged"]
    return None

def assign(root,path,value):
    node=root
    for key in path[:-1]: node=node[key]
    node[path[-1]]=value

def rejected_by_both(mutate) -> None:
    profile = policy.load_profile(); mutate(profile)
    schema = json.loads((ROOT / "references/schemas/reader_accessibility_profile.schema.json").read_text(encoding="utf-8"))
    assert list(jsonschema.Draft202012Validator(schema).iter_errors(profile)), "schema accepted mutation"
    try: policy.validate_profile(profile)
    except policy.PolicyError: pass
    else: raise AssertionError("runtime accepted schema-invalid mutation")

def main() -> int:
    mutations = [
        lambda p: p["thresholds"]["cadence"].update(unit="sentences"),
        lambda p: p["thresholds"]["cadence"].update(internal_sentence_break_signals=["comma"]),
        lambda p: p.update(policy_telos="x"),
        lambda p: p["adjacent_advisory_checks"]["VE"].update(name="wrong"),
        lambda p: p["transitions"]["H"].update(meaning=""),
        lambda p: p["register_scope"].update(**{"non-technical":["technical_body"]}),
        lambda p: p.update(remediation_order=["one"]),
        lambda p: p["sub_checks"]["A"].update(threshold_key=""),
        lambda p: p["sub_checks"]["H"].update(ph2_role_overrides={"orienting_clause":"wrong"}),
        lambda p: p["thresholds"]["cadence"]["bands"].__setitem__(slice(None), [{"min_words":0,"max_words":149,"required_functional_turn_points":0,"deficit_severity":"CLEAN"},{"min_words":150,"max_words":199,"required_functional_turn_points":1,"deficit_severity":"MINOR"},{"min_words":200,"max_words":300,"required_functional_turn_points":2,"deficit_severity":"MAJOR"}]),
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
    profile_schema=json.loads((ROOT/"references/schemas/reader_accessibility_profile.schema.json").read_text(encoding="utf-8"))
    for path,value in schema_const_paths(profile_schema,profile_schema):
        forged=copy.deepcopy(policy.load_profile()); assign(forged,path,changed(value))
        assert list(jsonschema.Draft202012Validator(profile_schema).iter_errors(forged)), f"oracle accepted forged const {path}"
        try: policy.validate_profile(forged)
        except policy.PolicyError: pass
        else: raise AssertionError(f"runtime accepted forged schema const {path}")

    profile = policy.load_profile()
    assert profile["runtime_modes"]["stability"] == {"aggregation_source":"resolved_profile_and_bound_transition_state","independent_member_exclusions":False,"negative_prefilter_short_circuit":False}
    assert "corpus_drift" not in profile, "synthetic corpus implementation claim remains"
    assert not hasattr(h, "_corpus_drift"), "synthetic corpus dispatch remains"

    md = "# Introduction\n\nHaving established the baseline, this section shows the result.\n\nFor example, consider the loan officer.\n\nIn summary, these constructs establish the boundary.\n\nTurning now, a final bridge.\n\n# Methods\n\nTechnical remainder."
    tex = "\\section{Introduction}\nHaving established the baseline, this section shows the result.\n% For example, this comment must disappear.\nFor example, consider the loan officer.\n\\subsection{Methods}\nTechnical remainder."
    md_roles = h.nominate_passage_roles(md, Path("paper.md"))
    tex_roles = h.nominate_passage_roles(tex, Path("paper.tex"))
    for roles in (md_roles, tex_roles):
        assert roles and all(item["role"] and item["confidence"] and item["reason"] for item in roles)
        assert all(not item["text"].lstrip().startswith(("#", "\\section", "\\subsection")) for item in roles), "heading emitted as passage"
        assert len({item["locator"] for item in roles}) == len(roles), "locators are not unique"
        assert any(item["text"] == "Having established the baseline," and item["role"] == "orienting_clause" for item in roles)
        assert any(item["text"] == "this section shows the result." and item["role"] == "contribution_clause" for item in roles)
        assert any(item["text"] == "For example," and item["role"] == "worked_example_vignette" for item in roles)
    assert any(item["text"] == "Turning now," and item["role"] == "inter_section_transition" for item in md_roles)
    assert all("comment must disappear" not in item["text"] for item in tex_roles)
    assert all(item["text"] != md.split("# Methods",1)[0].strip() for item in md_roles), "whole section duplicated as cue span"
    clear = h.analyse_passage("The model maps actors.", "line 1", False, profile, "orienting_clause", "binding")
    assert not clear.any_fired, "anti-dilution fixture unexpectedly fired a negative probe"
    g_text="# First\n\n"+("ordinary words "*30)+"\n\n# Second\n\nNext."
    low=copy.deepcopy(profile); high=copy.deepcopy(profile)
    low["thresholds"]["consolidation"]["candidate_gap_words"]["P1"]=1
    high["thresholds"]["consolidation"]["candidate_gap_words"]["P1"]=10000
    low_stats,*_=g.analyze(g_text,Path("paper.md"),"P1",low); high_stats,*_=g.analyze(g_text,Path("paper.md"),"P1",high)
    assert any(item.g_candidate for item in low_stats) and not any(item.g_candidate for item in high_stats), "G ignored explicit resolved-profile thresholds"

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

    with tempfile.TemporaryDirectory() as td:
        project=Path(td); ledger=fixture._materialize_native_project(project)
        state=ledger["policy_bindings"]["reader_accessibility"]["transitions"]["H"]
        event_hash,_=fixture._write_bound_file(project,"reviews/.harness/policy/h.md","evidence\n")
        common={"actor":"planner","authority":"user","approved":True,"evidence_path":"reviews/.harness/policy/h.md","evidence_sha256":event_hash,"cycle_id":"same-cycle"}
        observed=[
            {**common,"sequence":1,"event":"policy_transition_observed","observed_count":1,"manuscript_sha256":"0"*64,"content_sha256":"1"*64},
            {**common,"sequence":2,"event":"policy_transition_observed","observed_count":2,"manuscript_sha256":"2"*64,"content_sha256":"3"*64},
        ]
        approval={**common,"sequence":3,"event":"planner_transition_approved","observed_count":2,"manuscript_sha256":"2"*64,"content_sha256":"3"*64}
        state.update({"state":"retired","observed_count":2,"last_event_sequence":3,"events":[*observed,approval]})
        result=mf.validate_document(project,fixture._phase_document(ledger))
        assert any(f.code=="MF-POLICY" and "distinct cycle" in f.message for f in result.findings), "same-cycle H observations retired transition"

    with tempfile.TemporaryDirectory() as td:
        base=Path(td); project=base/"project"; ledger=fixture._materialize_native_project(project)
        outside=base/"outside.json"; outside.write_text("{ malformed outside",encoding="utf-8")
        binding=ledger["policy_bindings"]["reader_accessibility"]
        binding["resolved_path"]="../outside.json"; binding["resolved_sha256"]=hashlib.sha256(outside.read_bytes()).hexdigest()
        result=mf.validate_document(project,fixture._phase_document(ledger))
        messages=[f.message for f in result.findings]
        assert any("remain inside" in message for message in messages), "escaping resolved path was not rejected"
        assert all("valid JSON" not in message and "malformed" not in message for message in messages), "validator parsed an escaped malformed file"

    pass_fixture=ROOT/"scripts/fixtures/artefact_frontmatter_smoketest/pass"
    def forged_f1(mutator, expected_fragment):
        with tempfile.TemporaryDirectory() as td:
            project=Path(td)/"pass"; shutil.copytree(pass_fixture,project)
            f1=project/"reviews/ph3_findings_p21b_2026-04-22_iter0.md"
            fm,error=frontmatter.extract_frontmatter(f1); assert error is None and fm is not None
            assert not frontmatter.validate_reader_accessibility_evidence(fm,f1), "baseline F1 fixture is invalid"
            mutator(project,fm)
            findings=frontmatter.validate_reader_accessibility_evidence(fm,f1)
            assert findings and any(expected_fragment in finding.message for finding in findings), f"F1 forgery passed: {expected_fragment}"
    def mutate_candidate(project,fm,change):
        path=project/fm["reader_accessibility_policy"]["candidate_artifact_path"]
        payload=json.loads(path.read_text(encoding="utf-8")); change(payload)
        path.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
        fm["reader_accessibility_policy"]["candidate_artifact_sha256"]=hashlib.sha256(path.read_bytes()).hexdigest()
    forged_f1(lambda project,fm: mutate_candidate(project,fm,lambda payload: payload.update(phase="Ph2")),"does not match resolved policy")
    forged_f1(lambda project,fm: mutate_candidate(project,fm,lambda payload: (payload.pop("manuscript_path"),payload.pop("manuscript_sha256"))),"schema invalid")
    forged_f1(lambda project,fm: mutate_candidate(project,fm,lambda payload: payload.update(sub_checks={key:{} for key in "ABCDEFGH"})),"schema invalid")
    forged_f1(lambda project,fm: mutate_candidate(project,fm,lambda payload: payload["sub_checks"]["A"].update(applicable=False)),"canonical deterministic recomputation")
    forged_f1(lambda project,fm: mutate_candidate(project,fm,lambda payload: payload.update(register_class="mixed")),"canonical deterministic recomputation")
    forged_f1(lambda project,fm: mutate_candidate(project,fm,lambda payload: payload["sub_checks"]["A"]["candidates"].append({"paragraph":99,"word_count":999,"candidate_cues":["however"],"candidate_status":"overlay_functional_confirmation_required"})),"canonical deterministic recomputation")
    forged_f1(lambda project,fm: mutate_candidate(project,fm,lambda payload: payload["sub_checks"]["H"]["bundles"][0]["probes"]["nominalisation"].update(threshold=999)),"canonical deterministic recomputation")
    def forge_active_g(project,fm):
        state_path=project/"reviews/phase_state.json"; state=json.loads(state_path.read_text(encoding="utf-8")); state["milestone_framework"]["policy_bindings"]["reader_accessibility"]["transitions"]["G"]["state"]="retired"; state_path.write_text(json.dumps(state),encoding="utf-8")
        policy_fm=fm["reader_accessibility_policy"]; path=project/policy_fm["check8_evidence_path"]
        sidecar=json.loads(path.read_text(encoding="utf-8")); sidecar["subchecks"]["G"]["findings"]=[{"finding_id":"g1","severity":"BLOCKER","independence_group":"g"}]; sidecar["subcheck_verdicts"]["G"]="BLOCKER"
        path.write_text(json.dumps(sidecar,indent=2)+"\n",encoding="utf-8"); policy_fm["check8_evidence_sha256"]=hashlib.sha256(path.read_bytes()).hexdigest()
    forged_f1(forge_active_g,"do not match recomputed")

    print("OK reader_accessibility_semantics_smoketest")
    return 0
if __name__ == "__main__": raise SystemExit(main())
