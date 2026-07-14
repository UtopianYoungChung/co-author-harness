#!/usr/bin/env python3
"""Portable contract tests for the domain-native register semantic pin.

AUTHORITATIVE HOME for pin-contract coverage (asymmetry, degeneracy_guard,
seed_resolution / multi-hit disambiguation, MF pin-stale vs graph non-gating).
``reader_accessibility_contract_smoketest.py`` invokes this suite; semantics
and adversarial accessibility smoketests do not duplicate these cases.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import reader_accessibility_policy as policy
import milestone_framework_smoketest as milestone_fixture
import milestone_framework_validate as milestone_validator


def write_fixture(root: Path) -> tuple[Path, Path]:
    wiki = root / "wiki"; workspace = root / "workspace"; (wiki / "wiki/sources").mkdir(parents=True, exist_ok=True); (wiki / "raw/corpus").mkdir(parents=True, exist_ok=True); (workspace / "knowledge/LLM wiki/graphify-out").mkdir(parents=True, exist_ok=True)
    members = [m for m in policy.load_profile()["domain_native_register"]["exemplar_members"]
               if m.get("warrant_scope", "both") == "both"]  # hermetic baseline: exclude post-release ingestions
    for index, member in enumerate(members):
        tier = "full-read — annotation" if index == 0 else member["grounding"]
        (wiki / f"wiki/sources/{member['source_key']}.md").write_text(f"---\ngrounding_status: {tier}\n---\n", encoding="utf-8")
    pdf = wiki / "raw/corpus/yu-1995-istar.pdf"; pdf.write_bytes(b"synthetic yu")
    graph = {"nodes":[
        {"id":"yu-1995-istar","community":5,"file_type":"document","source_file":"wiki/sources/yu-1995-istar.md"},
        {"id":"yu-mylopoulos-1994-modelling-strategic-actor-relationships-bpr-8p_concept","community":10,"file_type":"concept","source_file":"wiki/sources/yu-mylopoulos-1994-modelling-strategic-actor-relationships-bpr-8p.md"},
        {"id":"yu-mylopoulos-1994-modelling-strategic-actor-relationships-bpr-8p_document","community":10,"file_type":"document","source_file":"wiki/sources/yu-mylopoulos-1994-modelling-strategic-actor-relationships-bpr-8p.md"},
        {"id":"yu-mylopoulos-1994-modelling-strategic-actor-relationships-bpr-8p_source","community":10,"file_type":"source","source_file":"wiki/sources/yu-mylopoulos-1994-modelling-strategic-actor-relationships-bpr-8p.md"},
        {"id":"icse-zeta","community":10,"file_type":"concept","source_file":"wiki/sources/yu-mylopoulos-1994-understanding-why-software-process-modelling.md"},
        {"id":"icse-alpha","community":10,"file_type":"concept","source_file":"wiki/sources/yu-mylopoulos-1994-understanding-why-software-process-modelling.md"},
        {"id":"import","community":11,"file_type":"document","source_file":"wiki/sources/import.md"}],
        "links":[{"source":"yu-1995-istar","target":"import","_src":"yu-1995-istar","_tgt":"import"}]}
    graph_path = workspace / "knowledge/LLM wiki/graphify-out/graph.json"; graph_path.write_text(json.dumps(graph), encoding="utf-8")
    return wiki, workspace


def main() -> int:
    profile = policy.load_profile()
    # Hermetic baseline for the FIXTURE-resolve block only: exclude post-release
    # ingestions (argument-only members) so counts/scopes match the frozen fixture.
    # The live-resolve block below uses the unfiltered profile.
    baseline = copy.deepcopy(profile)
    baseline["domain_native_register"]["exemplar_members"] = [
        m for m in baseline["domain_native_register"]["exemplar_members"]
        if m.get("warrant_scope", "both") == "both"
    ]
    model = profile["domain_native_register"]
    assert {"path_roots","graph","pin","related_to_RE_predicate","hash_recipe","views"} <= set(model["corpus_binding"])
    assert model["reader_model"]["register_class"] == "domain-native"
    assert set(model["warrant_layers"]) == {"surface", "argument", "role_scoping"}
    assert model["warrant_layers"]["role_scoping"]["surface_selector"] == "both"
    assert model["warrant_layers"]["role_scoping"]["argument_selector"] == ["both", "argument-only"]
    assert "advisory only" in model["derivations"]["review"]["discipline"]
    protected = model["c7_fence"]["protected_identity_layer"]
    remediation = json.dumps({"remediation_order":profile["remediation_order"],"derivations":model["derivations"]}).lower()
    assert all(key.lower() not in remediation for key in protected)
    def rejected(mutator):
        malformed=copy.deepcopy(profile); mutator(malformed)
        try: policy.validate_profile(malformed)
        except policy.PolicyError: return
        raise AssertionError("closed domain-native semantics mutation passed")
    rejected(lambda p: p["domain_native_register"]["corpus_binding"].update(hash_recipe={}))
    rejected(lambda p: p["domain_native_register"]["corpus_binding"]["related_to_RE_predicate"].update(membership="anything"))
    rejected(lambda p: p["domain_native_register"]["c7_fence"].update(protected_identity_layer=["foo"]))
    rejected(lambda p: p["domain_native_register"]["warrant_layers"].update(argument=copy.deepcopy(p["domain_native_register"]["warrant_layers"]["surface"])))
    rejected(lambda p: p["domain_native_register"]["derivations"]["review"].update(discipline="absence automatically blocks"))
    rejected(lambda p: p["domain_native_register"]["derivations"]["revise"].update(profile_keys=["domain_native_register.warrant_layers.surface"]))
    rejected(lambda p: p["domain_native_register"].update(honesty_constraints=["retrieval guarantees deterministic native prose"]))
    rejected(lambda p: p["sub_checks"]["H"].update(threshold_key="thresholds.cadence"))
    rejected(lambda p: p["sub_checks"]["H"].update(register_model_key="anything"))
    rejected(lambda p: p["domain_native_register"]["exemplar_members"][0].update(source_key="forged"))
    rejected(lambda p: p["domain_native_register"]["exemplar_members"][0].update(role="forged"))
    rejected(lambda p: p["domain_native_register"]["exemplar_members"][0].update(grounding="stub"))
    assert policy.normalize_tier("full-read — 201/201 pages") == "full-read"
    assert policy.normalize_tier("full-text-pass") == "full-read"
    assert policy.normalize_tier("section-read-verified") == "section-read"
    assert not policy.grounding_admitted("stub — awaiting read") and not policy.grounding_admitted("unresolved - missing source")
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); wiki,workspace=write_fixture(root)
        resolved=policy.resolve_domain_native_register(baseline, wiki_root=wiki, workspace_root=workspace, harness_root=ROOT)
        assert resolved["surface_exemplar_members"] == resolved["argument_exemplar_members"]
        assert all(item["warrant_scope"] == "both" for item in resolved["exemplar_members"])
        assert resolved["path_roots"]["path_roots_mode"] == "override"
        assert len(resolved["seed_resolution_map"]) == 3 and len(resolved["unresolved_seed_ids"]) == 9
        assert resolved["seed_resolution_map"]["yu-mylopoulos-1994-modelling-strategic-actor-relationships-bpr-8p"].endswith("_source")
        assert resolved["seed_resolution_map"]["yu-mylopoulos-1994-understanding-why-software-process-modelling"] == "icse-alpha"
        assert set(resolved["seed_resolution_ties"]["yu-mylopoulos-1994-modelling-strategic-actor-relationships-bpr-8p"]) == {"yu-mylopoulos-1994-modelling-strategic-actor-relationships-bpr-8p_concept","yu-mylopoulos-1994-modelling-strategic-actor-relationships-bpr-8p_document"}
        assert resolved["warnings"] and resolved["warnings"][0]["code"] == "RA-DNR-DEGENERATE"
        malformed_graphs = [b"\xff", b"[]", b'{"nodes":{},"links":[]}', b'{"nodes":[],"links":{}}', b'{"nodes":[1],"links":[]}', b'{"nodes":[],"links":[1]}']
        graph_path=workspace/"knowledge/LLM wiki/graphify-out/graph.json"
        valid_graph_bytes=graph_path.read_bytes()
        for payload in malformed_graphs:
            graph_path.write_bytes(payload)
            try: policy.resolve_domain_native_register(baseline,wiki_root=wiki,workspace_root=workspace,harness_root=ROOT)
            except policy.PolicyError: pass
            else: raise AssertionError(f"malformed graph escaped controlled policy error: {payload!r}")
            proc=subprocess.run([sys.executable,str(ROOT/"scripts/reader_accessibility_policy.py"),"--wiki-root",str(wiki),"--workspace-root",str(workspace),"--harness-root",str(ROOT)],capture_output=True,text=True,encoding="utf-8",errors="replace")
            payload_out=json.loads(proc.stdout)
            assert proc.returncode==4 and payload_out["status"]=="MISCONFIGURED" and payload_out["code"]=="RA-POLICY" and "Traceback" not in proc.stdout+proc.stderr
        graph_path.write_bytes(valid_graph_bytes)
        source_page=wiki/"wiki/sources/yu-1995-istar.md"; valid_source_bytes=source_page.read_bytes(); source_page.write_bytes(b"\xff")
        try: policy.resolve_domain_native_register(baseline,wiki_root=wiki,workspace_root=workspace,harness_root=ROOT)
        except policy.PolicyError as exc: assert "not UTF-8" in str(exc)
        else: raise AssertionError("invalid UTF-8 source page escaped controlled policy error")
        proc=subprocess.run([sys.executable,str(ROOT/"scripts/reader_accessibility_policy.py"),"--wiki-root",str(wiki),"--workspace-root",str(workspace),"--harness-root",str(ROOT)],capture_output=True,text=True,encoding="utf-8",errors="replace")
        assert proc.returncode==4 and json.loads(proc.stdout)["code"]=="RA-POLICY" and "Traceback" not in proc.stdout+proc.stderr
        source_page.write_bytes(valid_source_bytes)
        absent_key=profile["domain_native_register"]["exemplar_members"][1]["source_key"]
        absent_page=wiki/f"wiki/sources/{absent_key}.md"
        absent_page.write_text("---\ngrounding_status: full-read\nsource_loc: raw/future/not-yet-staged.pdf\n---\n",encoding="utf-8")
        (wiki/"raw/future").mkdir(parents=True,exist_ok=True)
        stable_absence=policy.resolve_domain_native_register(baseline,wiki_root=wiki,workspace_root=workspace,harness_root=ROOT)
        assert f"{absent_key}\tfull-read\t-" in stable_absence["exemplar_hash_lines"]
        staged=False
        def stage_after_absence(stage: str, role: str, path: Path | None):
            nonlocal staged
            if not staged and stage == "after_absence" and role == "surface_warrant_pdf" and path is not None:
                path.write_bytes(b"late staged bytes"); staged=True
        try: policy.resolve_domain_native_register(baseline,wiki_root=wiki,workspace_root=workspace,harness_root=ROOT,_snapshot_hook=stage_after_absence)
        except policy.PolicyError as exc: assert "changed during resolution" in str(exc)
        else: raise AssertionError("PDF staged after the absence decision was accepted as '-' tuple")
        (wiki/"raw/future/not-yet-staged.pdf").unlink()
        wiki,workspace=write_fixture(root)
        absent_page=wiki/f"wiki/sources/{absent_key}.md"
        absent_page.write_text("---\ngrounding_status: full-read\nsource_loc: raw/future/not-yet-staged.pdf\n---\n",encoding="utf-8")
        replaced_parent=False
        def replace_absent_parent(stage: str, role: str, path: Path | None):
            nonlocal replaced_parent
            if not replaced_parent and stage == "after_absence" and path is not None and path.name == "not-yet-staged.pdf":
                parent=path.parent; old=parent.with_name("future-replaced"); os.replace(parent,old); parent.mkdir(); replaced_parent=True
        try: policy.resolve_domain_native_register(baseline,wiki_root=wiki,workspace_root=workspace,harness_root=ROOT,_snapshot_hook=replace_absent_parent)
        except policy.PolicyError as exc: assert "changed during resolution" in str(exc)
        else: raise AssertionError("absent-PDF parent replacement was not rejected")
        wiki,workspace=write_fixture(root)
        absent_page=wiki/f"wiki/sources/{absent_key}.md"
        absent_page.write_text("---\ngrounding_status: full-read\nsource_loc: raw/future/not-yet-staged.pdf\n---\n",encoding="utf-8")
        removed_anchor=False
        def remove_anchor_during_acquisition(stage: str, role: str, path: Path | None):
            nonlocal removed_anchor
            if not removed_anchor and stage == "before_absence_anchor" and path is not None and path.name == "not-yet-staged.pdf":
                path.parent.rmdir(); removed_anchor=True
        try: policy.resolve_domain_native_register(baseline,wiki_root=wiki,workspace_root=workspace,harness_root=ROOT,_snapshot_hook=remove_anchor_during_acquisition)
        except policy.PolicyError: pass
        else: raise AssertionError("absence-anchor deletion during acquisition escaped controlled rejection")
        wiki,workspace=write_fixture(root)
        def churn(role: str):
            fired=False
            def hook(stage: str, captured_role: str, path: Path | None):
                nonlocal fired
                if not fired and stage == "after_capture" and captured_role == role and path is not None:
                    path.write_bytes(path.read_bytes()+b" "); fired=True
            return hook
        for role in ("graph_provenance_only", "exemplar_source_page", "surface_warrant_pdf"):
            try: policy.resolve_domain_native_register(baseline,wiki_root=wiki,workspace_root=workspace,harness_root=ROOT,_snapshot_hook=churn(role))
            except policy.PolicyError as exc: assert "changed during resolution" in str(exc)
            else: raise AssertionError(f"{role} churn was not rejected")
            wiki,workspace=write_fixture(root)
        replaced=False
        def replace_graph(stage: str, role: str, path: Path | None):
            nonlocal replaced
            if not replaced and stage == "after_capture" and role == "graph_provenance_only" and path is not None:
                replacement=path.with_suffix(".replacement"); replacement.write_bytes(path.read_bytes()); os.replace(replacement,path); replaced=True
        try: policy.resolve_domain_native_register(baseline,wiki_root=wiki,workspace_root=workspace,harness_root=ROOT,_snapshot_hook=replace_graph)
        except policy.PolicyError as exc: assert "changed during resolution" in str(exc)
        else: raise AssertionError("atomic graph path replacement was not rejected")
        wiki,workspace=write_fixture(root)
        final_churn=False
        def churn_before_final(stage: str, role: str, path: Path | None):
            nonlocal final_churn
            if not final_churn and stage == "before_final_verify":
                source=wiki/"wiki/sources/yu-1995-istar.md"; source.write_bytes(source.read_bytes()+b" "); final_churn=True
        try: policy.resolve_domain_native_register(baseline,wiki_root=wiki,workspace_root=workspace,harness_root=ROOT,_snapshot_hook=churn_before_final)
        except policy.PolicyError as exc: assert "changed during resolution" in str(exc)
        else: raise AssertionError("cross-file churn before final verification was not rejected")
        wiki,workspace=write_fixture(root)
        pins=(resolved["attestation_view_pin"],resolved["exemplar_view_pin"])
        graph_path=workspace/"knowledge/LLM wiki/graphify-out/graph.json"; graph=json.loads(graph_path.read_text()); graph["generated_at"]="churn"; graph_path.write_text(json.dumps(graph),encoding="utf-8")
        churn=policy.resolve_domain_native_register(baseline,wiki_root=wiki,workspace_root=workspace,harness_root=ROOT)
        assert (churn["attestation_view_pin"],churn["exemplar_view_pin"]) == pins
        graph["nodes"].append({"id":"new-primary-member","community":5,"file_type":"concept","source_file":"wiki/sources/new.md"}); graph_path.write_text(json.dumps(graph),encoding="utf-8")
        assert policy.resolve_domain_native_register(baseline,wiki_root=wiki,workspace_root=workspace,harness_root=ROOT)["attestation_view_pin"] != pins[0]
        page=wiki/"wiki/sources/yu-1995-istar.md"; page.write_text("---\ngrounding_status: full-read - changed note\n---\n",encoding="utf-8")
        annotation=policy.resolve_domain_native_register(baseline,wiki_root=wiki,workspace_root=workspace,harness_root=ROOT)
        assert annotation["exemplar_view_pin"] == pins[1]
        pdf=wiki/"raw/corpus/yu-1995-istar.pdf"; pdf.write_bytes(b"changed")
        assert policy.resolve_domain_native_register(baseline,wiki_root=wiki,workspace_root=workspace,harness_root=ROOT)["exemplar_view_pin"] != pins[1]
        graph["links"][0]["_tgt"]="divergent"; graph_path.write_text(json.dumps(graph),encoding="utf-8")
        try: policy.resolve_domain_native_register(baseline,wiki_root=wiki,workspace_root=workspace,harness_root=ROOT)
        except policy.PolicyError as exc: assert "link endpoint divergence" in str(exc)
        else: raise AssertionError("link divergence passed")
    live = policy.resolve_domain_native_register(profile)
    expected = model["expected_verification"]
    assert live["path_roots"]["path_roots_mode"] == "profile"
    assert live["path_roots"]["effective"]["wiki_root"] == model["corpus_binding"]["path_roots"]["wiki_root"]
    assert live["path_roots"]["effective"]["workspace_root"] == model["corpus_binding"]["path_roots"]["workspace_root"]
    drifted = copy.deepcopy(profile)
    drifted["domain_native_register"]["corpus_binding"]["path_roots"]["wiki_root"] = "B:/Agents/knowledge/LLM wiki-DRIFT"
    try:
        policy.resolve_domain_native_register(drifted, wiki_root=policy.DEFAULT_WIKI_ROOT)
    except policy.PolicyError as exc:
        assert "wiki_root module default diverges" in str(exc)
    else:
        raise AssertionError("profile/default wiki_root divergence passed")
    assert live["attestation_view_pin"] == expected["attestation_view_pin"]
    assert live["exemplar_view_pin"] == expected["exemplar_view_pin"]
    assert live["graph_sha256_provenance"] == hashlib.sha256((Path("B:/Agents")/model["corpus_binding"]["graph"]["path"]).read_bytes()).hexdigest()
    assert len(live["seed_resolution_map"]) == 3 and len(live["unresolved_seed_ids"]) == len(model["exemplar_members"]) - 3 and live["warnings"]
    assert {entry["role"] for entry in live["provenance"]} >= {"exemplar_source_page","surface_warrant_pdf","graph_provenance_only","register_profile"}
    bad_expected=copy.deepcopy(profile); bad_expected["domain_native_register"]["exemplar_members"][0]["pdf_sha256"]="0"*64
    try: policy.resolve_domain_native_register(bad_expected)
    except policy.PolicyError as exc: assert "expected exemplar PDF hash mismatch" in str(exc)
    else: raise AssertionError("declared exemplar PDF mismatch passed")
    with tempfile.TemporaryDirectory() as td:
        project=Path(td); ledger=milestone_fixture._materialize_native_project(project)
        reader=profile["domain_native_register"]["reader_model"]
        assert ledger["milestones"]["M1"]["policy_evidence"]["reader_model"] == reader
        binding=ledger["policy_bindings"]["reader_accessibility"]
        binding["register_provenance"]["seed_resolution_map"]={}
        result=milestone_validator.validate_document(project,milestone_fixture._phase_document(ledger))
        assert any(f.code=="MF-POLICY-PROVENANCE" for f in result.findings)
        for key in ("seed_resolution_ties","unresolved_seed_ids","primary_communities","attestation_member_ids","exemplar_hash_lines","warnings"):
            ledger=milestone_fixture._materialize_native_project(project); binding=ledger["policy_bindings"]["reader_accessibility"]
            binding["register_provenance"][key]={} if isinstance(binding["register_provenance"][key],dict) else []
            result=milestone_validator.validate_document(project,milestone_fixture._phase_document(ledger))
            assert any(f.code=="MF-POLICY-PROVENANCE" for f in result.findings), key
        for field in ("path", "sha256"):
            ledger=milestone_fixture._materialize_native_project(project); binding=ledger["policy_bindings"]["reader_accessibility"]
            entry=next(entry for entry in binding["register_provenance"]["provenance"] if entry["role"] != "graph_provenance_only")
            entry[field]="forged-path" if field == "path" else "0"*64
            result=milestone_validator.validate_document(project,milestone_fixture._phase_document(ledger))
            assert any(f.code=="MF-POLICY-PROVENANCE" for f in result.findings), field
        ledger=milestone_fixture._materialize_native_project(project); binding=ledger["policy_bindings"]["reader_accessibility"]
        binding["attestation_view_pin"]="0"*64
        result=milestone_validator.validate_document(project,milestone_fixture._phase_document(ledger))
        assert any(f.code=="MF-POLICY-ATTESTATION-PIN-STALE" for f in result.findings)
        ledger=milestone_fixture._materialize_native_project(project)
        ledger["policy_bindings"]["reader_accessibility"]["exemplar_view_pin"]="0"*64
        result=milestone_validator.validate_document(project,milestone_fixture._phase_document(ledger))
        assert any(f.code=="MF-POLICY-EXEMPLAR-PIN-STALE" for f in result.findings)
        ledger=milestone_fixture._materialize_native_project(project)
        ledger["policy_bindings"]["reader_accessibility"]["profile_sha256"]="0"*64
        result=milestone_validator.validate_document(project,milestone_fixture._phase_document(ledger))
        assert any(f.code=="MF-POLICY-PROFILE-STALE" for f in result.findings)
        ledger=milestone_fixture._materialize_native_project(project)
        ledger["policy_bindings"]["reader_accessibility"]["graph_sha256_provenance"]="0"*64
        result=milestone_validator.validate_document(project,milestone_fixture._phase_document(ledger))
        assert not any(f.code in {"MF-POLICY-ATTESTATION-PIN-STALE","MF-POLICY-EXEMPLAR-PIN-STALE"} for f in result.findings)
        ledger=milestone_fixture._materialize_native_project(project); binding=ledger["policy_bindings"]["reader_accessibility"]
        binding["register_provenance"]["warnings"]=[{}]
        result=milestone_validator.validate_document(project,milestone_fixture._phase_document(ledger))
        assert any(f.code=="MF-STRUCTURE" for f in result.findings)
        ledger=milestone_fixture._materialize_native_project(project); binding=ledger["policy_bindings"]["reader_accessibility"]
        projection=binding["register_provenance"]; projection["graph_sha256_provenance"]="0"*64; projection["graph_mtime_utc_provenance"]="changed"
        graph_entry=next(entry for entry in projection["provenance"] if entry["role"]=="graph_provenance_only"); graph_entry.update(path="ignored",sha256="0"*64)
        result=milestone_validator.validate_document(project,milestone_fixture._phase_document(ledger))
        assert not any(f.code=="MF-POLICY-PROVENANCE" for f in result.findings)
    with tempfile.TemporaryDirectory() as td:
        project=Path(td); (project/"reviews").mkdir(); resolved=policy.resolve_policy(None)
        resolved["attestation_view_pin"]="0"*64
        path=project/"reviews/resolved.json"; path.write_text(json.dumps(resolved),encoding="utf-8")
        try: policy.phase_state_binding(resolved,path,project)
        except policy.PolicyError as exc: assert "initial semantic pin mismatch" in str(exc)
        else: raise AssertionError("bootstrap accepted a declared/current semantic pin mismatch")
    with tempfile.TemporaryDirectory() as td:
        manuscript=Path(td)/"scope.md"; manuscript.write_text("# Abstract\n\nThis abstract frames the contribution.\n\n# Methods\n\nFirst framing sentence.\n\nA second technical sentence follows.",encoding="utf-8")
        counts=[]
        for flag in ("--passage-scope-class","--register-class"):
            mode="mixed" if flag=="--passage-scope-class" else "non-technical"
            proc=subprocess.run([sys.executable,str(ROOT/"scripts/check8_h_prefilter.py"),str(manuscript),flag,mode],capture_output=True,text=True,check=True)
            counts.append(int(next(line.rsplit(" ",1)[1] for line in proc.stdout.splitlines() if line.startswith("- Passages in scope:"))))
        assert counts[0] < counts[1], counts
    print("OK domain_native_register_smoketest")
    return 0
if __name__ == "__main__": raise SystemExit(main())
