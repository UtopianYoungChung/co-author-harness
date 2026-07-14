"""Canonical deterministic builder for reader-accessibility candidate artifacts."""
from __future__ import annotations
import hashlib, re
from pathlib import Path
from typing import Any
import check8_g_prefilter, check8_h_prefilter
from manuscript_geometry import heading_sections
from reader_accessibility_policy import validate_candidate_artifact

def build_candidate_artifact(project_root: Path, manuscript_path: Path, phase: str, cycle_id: str, resolved: dict[str,Any]) -> dict[str,Any]:
    profile=resolved["resolved_profile"]; text=manuscript_path.read_text(encoding="utf-8")
    paragraphs=[part.strip() for part in text.split("\n\n") if part.strip()]
    cues=profile["thresholds"]["cadence"]["turn_point_candidates"]; a=[]
    for index,paragraph in enumerate(paragraphs,1):
        words=len(re.findall(r"[\w']+",paragraph)); hits=[cue for cue in cues if re.search(r"(?<!\w)"+re.escape(cue)+r"(?!\w)",paragraph,re.I)]
        if words>profile["thresholds"]["cadence"]["bands"][0]["max_words"]: a.append({"paragraph":index,"word_count":words,"candidate_cues":hits,"candidate_status":"overlay_functional_confirmation_required"})
    p_stage=check8_g_prefilter._parse_pstage(project_root); d=[]
    clean,sections=heading_sections(text,manuscript_path)
    for section in sections:
        body=clean[section["body_start"]:section["body_end"]].lstrip("\n")
        opening=re.split(r"\n\s*\n",body,1)[0] if body else ""
        sentence_count=len([part for part in re.split(r"(?<=[.!?])\s+",opening.strip()) if part.strip()]) if opening.strip() else 0
        sentence_range=profile["thresholds"]["section_signpost"]
        orienting=bool(re.search(r"\b(having established|after|so far|in the preceding|the previous section|up to this point)\b",opening,re.I))
        contribution=bool(re.search(r"\b(this section (?:shows|argues|develops|examines)|what follows|I now|I turn to|the next move|we will|I will show|the contribution here)\b",opening,re.I))
        in_range=sentence_range["opening_sentences_min"] <= sentence_count <= sentence_range["opening_sentences_max"]
        if not (orienting and contribution and in_range): d.append({"heading":section["title"],"opening_sentence_count":sentence_count,"missing":[name for name,present in (("orienting_clause",orienting),("contribution_clause",contribution),("opening_sentence_count_in_range",in_range)) if not present],"candidate_status":"overlay_required"})
    seen=set(); e=[]; cap=profile["thresholds"]["jargon"]["new_domain_terms_per_paragraph"][p_stage]+1
    for index,paragraph in enumerate(paragraphs,1):
        terms=[term.strip() for pair in re.findall(r"\\emph\{([^}]+)\}|(?<!\*)\*([^*\n]+)\*(?!\*)",paragraph) for term in pair if term.strip()]; new=[term for term in terms if term.casefold() not in seen]; seen.update(term.casefold() for term in terms)
        if len(new)>=cap: e.append({"paragraph":index,"new_terms":new,"candidate_cap":cap,"candidate_status":"overlay_required"})
    f=[]; qfloor=profile["thresholds"]["worked_example"]["rhetorical_question_stack_min"]
    for index,paragraph in enumerate(paragraphs,1):
        tri=bool(re.search(r"\bFirst,[\s\S]{5,400}?\bSecond,[\s\S]{5,400}?\bThird,",paragraph,re.I)); questions=paragraph.count("?")
        if tri or questions>=qfloor: f.append({"paragraph":index,"markers":[name for name,present in (("triadic_enumerator",tri),("rhetorical_question_stack",questions>=qfloor)) if present],"candidate_status":"worked_example_judgment_required"})
    g,total,headings,long_proxy=check8_g_prefilter.analyze(text,manuscript_path,p_stage,profile)
    h=check8_h_prefilter.analyse(text,manuscript_path,profile,phase=phase,register_class=resolved["passage_scope_class"])
    try: manuscript_binding=manuscript_path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError: manuscript_binding=manuscript_path.resolve().as_posix()
    artifact={"schema_version":"reader_accessibility_candidates.v1","phase":phase,"cycle_id":cycle_id,"manuscript_path":manuscript_binding,"manuscript_sha256":hashlib.sha256(manuscript_path.read_bytes()).hexdigest(),"profile_path":resolved["profile_path"],"profile_sha256":resolved["profile_sha256"],"source_bindings":resolved["source_bindings"],"register_class":resolved["register_class"],"passage_scope_class":resolved["passage_scope_class"],"attestation_view_pin":resolved["attestation_view_pin"],"exemplar_view_pin":resolved["exemplar_view_pin"],"candidate_only":True,"evaluator_judgment_required":True,"sub_checks":{
      "A":{"applicable":phase in {"Ph2","Ph3","Ph4"},"deterministic_disposition":"candidate_probe","candidates":a},
      "B":{"applicable":phase in {"Ph2","Ph3","Ph4"},"deterministic_disposition":"judgment_only","reason":"rhythm and C-8 functional guards require Evaluator judgment"},
      "C":{"applicable":phase in {"Ph2","Ph3","Ph4"},"deterministic_disposition":"judgment_only","reason":"first-use conceptual work cannot be established by token order alone"},
      "D":{"applicable":phase in {"Ph2","Ph3","Ph4"},"deterministic_disposition":"candidate_probe","candidates":d},
      "E":{"applicable":phase in {"Ph2","Ph3","Ph4"},"deterministic_disposition":"candidate_probe","candidates":e},
      "F":{"applicable":phase in {"Ph2","Ph3","Ph4"},"deterministic_disposition":"candidate_probe","candidates":f},
      "G":{"applicable":phase in {"Ph3","Ph4"},"deterministic_disposition":"candidate_probe","proxy_label":"word-and-cue gap proxy candidate; not the construct-accumulation predicate","total_words":total,"headings":headings,"long_manuscript_proxy":long_proxy,"candidates":[s.__dict__ for s in g if s.g_candidate]},
      "H":{"applicable":phase in {"Ph2","Ph3","Ph4"},"deterministic_disposition":"candidate_probe","ph2_scope":"orienting_clause blocker-candidate plus advisory passage roles" if phase=="Ph2" else None,"positive_marker_audit_required":True,"bundles":[{"locator":b.locator,"passage_role":b.passage_role,"role_confidence":b.role_confidence,"role_reason":b.role_reason,"binding_status":b.binding_status,"word_count":b.word_count,"candidate_status":"overlay_positive_marker_audit_required","negative_prefilter_fired":b.any_fired,"probes":{"nominalisation":b.nominalisation.__dict__,"prep_run":b.prep_run.__dict__,"hedging":b.hedging.__dict__}} for b in h]}}}
    validate_candidate_artifact(artifact); return artifact
