#!/usr/bin/env python3
"""Adversarial integration tests for the reader-accessibility policy boundary.

Domain-native pin-contract cases live in ``domain_native_register_smoketest.py``
(asymmetry, degeneracy, seed resolution); this suite covers cadence/profile/H
prefilter boundaries only.
"""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check8_h_prefilter as h
import reader_accessibility_policy as policy
from semantic_graph_fixture_support import semantic_graph_fixture_environment


def rejects(mutator, needle: str) -> None:
    profile = policy.load_profile()
    mutator(profile)
    try:
        policy.validate_profile(profile)
    except policy.PolicyError as exc:
        assert needle in str(exc), (needle, str(exc))
    else:
        raise AssertionError(f"malformed profile accepted: {needle}")


def run_runner(project: Path, text: str, *extra: str) -> subprocess.CompletedProcess[str]:
    manuscript = project / "manuscript.md"
    manuscript.write_text(text, encoding="utf-8")
    return subprocess.run(
        [sys.executable, "-I", "-S", str(ROOT / "scripts/audit/run_all.py"), str(manuscript),
         "--project-root", str(project), "--skip-d-style-profile", "--phase", "Ph2",
         "--cycle-id", "adversarial", "--out", str(project / "reviews/findings.json"), *extra],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def main() -> int:
    # Deep runtime invariants, not merely top-level shape checks.
    rejects(lambda p: p["thresholds"]["cadence"]["bands"][1].update(min_words=160), "ordered and contiguous")
    rejects(lambda p: p["thresholds"]["cadence"]["above_ceiling"].update(mandatory_split=False), "above_ceiling")
    rejects(lambda p: p["adjacent_advisory_checks"]["VE"].update(aggregate_member=True), "VE")
    rejects(lambda p: p["thresholds"].update(canonical_sha256="0" * 64), "canonical_sha256")
    rejects(lambda p: p["sub_checks"]["A"].update(deterministic_disposition="magic"), "deterministic_disposition")
    rejects(lambda p: p["thresholds"]["register"].update(extra=1), "additional properties forbidden")
    # The JSON Schema independently rejects the same nested mutations.
    import jsonschema
    schema = json.loads((ROOT / "references/schemas/reader_accessibility_profile.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    cadence_gap = policy.load_profile(); cadence_gap["thresholds"]["cadence"]["bands"][1]["min_words"] = 160
    assert not list(jsonschema.Draft202012Validator(schema).iter_errors(cadence_gap)), "schema duplicated cross-band cadence semantics"
    for mutate in (
        lambda p: p["adjacent_advisory_checks"]["VE"].update(aggregate_member=True),
        lambda p: p["thresholds"]["register"].update(extra=1),
    ):
        malformed = policy.load_profile(); mutate(malformed)
        assert list(jsonschema.Draft202012Validator(schema).iter_errors(malformed)), "schema accepted malformed nested policy"

    profile = policy.load_profile()
    approved = [{"sequence": 1, "event": "revision_approved", "approved": True, "content_sha256": "abc"}]
    no_approval = policy.update_persistence("abc", "abc", 1, "MINOR", [])
    with_approval = policy.update_persistence("abc", "abc", 1, "MINOR", approved)
    duplicate = policy.update_persistence("abc", "abc", 2, "MINOR", approved, previous_approval_sequence=1)
    edited = policy.update_persistence("abc", "def", 8, "MINOR", approved)
    assert no_approval["unchanged_rounds"] == 1 and not no_approval["planner_workflow_escalation_candidate"]
    assert with_approval["unchanged_rounds"] == 2 and with_approval["planner_workflow_escalation_candidate"]
    assert duplicate["unchanged_rounds"] == 2 and not duplicate["planner_workflow_escalation_candidate"]
    assert edited["unchanged_rounds"] == 0 and edited["current_severity"] == "MINOR"

    with tempfile.TemporaryDirectory() as td:
        project = Path(td)
        notes = project / "research_notes"
        notes.mkdir()
        (notes / "directives.md").write_text("register_class: mixed\nproject_id: unrelated\n", encoding="utf-8")
        (notes / "hedges.txt").write_text("foobar\n", encoding="utf-8")
        (notes / "terminology.txt").write_text("operationalization\n", encoding="utf-8")
        resolved = policy.resolve_policy(project)
        assert all(set(b) <= {"scope", "path", "sha256", "role", "polarity"} for b in resolved["source_bindings"])
        assert all(not Path(b["path"]).is_absolute() for b in resolved["source_bindings"])

        bundles = h.analyse(
            "This orienting clause says foobar foobar operationalization.",
            project / "manuscript.md", resolved["resolved_profile"],
            phase="Ph2", register_class="mixed", passage_roles=["orienting_clause"],
        )
        assert bundles[0].passage_role == "orienting_clause"
        assert bundles[0].hedging.fired, "resolved hedges.txt was ignored"
        assert bundles[0].nominalisation.raw_count == 0, "terminology exclusion was ignored"
        assert bundles[0].binding_status == "blocker_candidate"

        clean = run_runner(project, "# Opening\n\nThis section turns to an example. Foobar foobar.")
        assert clean.returncode == 0 and "Traceback" not in clean.stdout + clean.stderr, clean.stdout + clean.stderr
        artifact = json.loads((project / "reviews/reader_accessibility_candidates_adversarial.json").read_text(encoding="utf-8"))
        assert any(bundle["probes"]["hedging"]["fired"] for bundle in artifact["sub_checks"]["H"]["bundles"])
        assert all(bundle["passage_role"] for bundle in artifact["sub_checks"]["H"]["bundles"])
        for check in "ADEF":
            assert artifact["sub_checks"][check]["deterministic_disposition"] in {"candidate_probe", "judgment_only"}

        long_para = " ".join(["plain"] * 155) + " however contribution"
        probe_text = ("# Complete\n\nHaving established the baseline, this section shows the next result.\n\n" + long_para +
                      "\n\n*One* *Two* *Three* *Four*\n\nFirst, take one step. Second, take another step. Third, inspect the result.\n\n"
                      "# Incomplete\n\nThis section introduces material.\n\nOne question? Two statements.\n")
        probes = run_runner(project, probe_text)
        assert probes.returncode == 0, probes.stdout + probes.stderr
        probe_artifact = json.loads((project / "reviews/reader_accessibility_candidates_adversarial.json").read_text(encoding="utf-8"))
        a = probe_artifact["sub_checks"]["A"]["candidates"]
        assert any("however" in item["candidate_cues"] for item in a)
        assert all("but" not in item["candidate_cues"] for item in a), "cue token boundary matched contribution"
        d = probe_artifact["sub_checks"]["D"]["candidates"]
        assert any(item["heading"] == "Incomplete" for item in d) and all(item["heading"] != "Complete" for item in d)
        assert probe_artifact["sub_checks"]["E"]["candidates"], "E positive probe did not fire"
        assert any("triadic_enumerator" in item["markers"] for item in probe_artifact["sub_checks"]["F"]["candidates"])
        tex_manuscript=project/"manuscript.tex"; tex_manuscript.write_text("\\section{First}\nA bare opening without either signpost.\n\\subsection{Second}\nHaving established the baseline, this section shows the result.\n",encoding="utf-8")
        tex_out=project/"reviews/reader_accessibility_candidates_tex.json"
        tex_proc=subprocess.run([sys.executable,"-I","-S",str(ROOT/"scripts/audit/run_all.py"),str(tex_manuscript),"--project-root",str(project),"--skip-d-style-profile","--phase","Ph2","--cycle-id","tex","--accessibility-out",str(tex_out),"--out",str(project/"reviews/tex_findings.json")],capture_output=True,text=True,encoding="utf-8",errors="replace")
        assert tex_proc.returncode == 0, tex_proc.stdout+tex_proc.stderr
        tex_artifact=json.loads(tex_out.read_text(encoding="utf-8"))
        assert any(item["heading"] == "First" for item in tex_artifact["sub_checks"]["D"]["candidates"]), "compact TeX First opening borrowed Second cues"
        assert all(item["heading"] != "Second" for item in tex_artifact["sub_checks"]["D"]["candidates"]), "compact TeX Second opening was not evaluated independently"

        (notes / "directives.md").write_text("register_class: nonsense\n", encoding="utf-8")
        bad_register = run_runner(project, "Text.")
        assert bad_register.returncode == 4 and "RA-POLICY" in bad_register.stdout and "Traceback" not in bad_register.stdout + bad_register.stderr
        (notes / "directives.md").write_text("register_class: mixed\n", encoding="utf-8")
        (notes / "hedges.txt").write_text("# empty\n", encoding="utf-8")
        empty_replace = run_runner(project, "Text.")
        assert empty_replace.returncode == 4 and "Traceback" not in empty_replace.stdout + empty_replace.stderr

        bad_profile_path = ROOT / "scripts" / ".reader-accessibility-adversarial-profile.json"
        try:
            malformed = policy.load_profile(); malformed["phase_values"] = 7
            bad_profile_path.write_text(json.dumps(malformed), encoding="utf-8")
            nested = run_runner(project, "Text.", "--accessibility-profile", str(bad_profile_path))
            assert nested.returncode == 4 and "RA-POLICY" in nested.stdout and "Traceback" not in nested.stdout + nested.stderr
            escaping = policy.load_profile(); escaping["override_contract"]["hedges"]["path"] = "../outside.txt"
            bad_profile_path.write_text(json.dumps(escaping), encoding="utf-8")
            escaped = run_runner(project, "Text.", "--accessibility-profile", str(bad_profile_path))
            assert escaped.returncode == 4 and "RA-POLICY" in escaped.stdout and "Traceback" not in escaped.stdout + escaped.stderr
        finally:
            bad_profile_path.unlink(missing_ok=True)

    # F1 must reject internally forged Check 8 content even when its byte hash is current.
    import artefact_frontmatter_validate as frontmatter
    with tempfile.TemporaryDirectory() as td:
        project = Path(td); (project / "reviews").mkdir(); (project / "manuscript").mkdir()
        manuscript = project / "manuscript/main.md"; manuscript.write_text("current\n", encoding="utf-8")
        resolved = project / "reviews/resolved.json"; resolved.write_text("{}\n", encoding="utf-8")
        candidate = project / "reviews/candidates.json"; candidate.write_text("{}\n", encoding="utf-8")
        sidecar = {"profile_path": "reviews/resolved.json", "profile_sha256": hashlib.sha256(resolved.read_bytes()).hexdigest(), "manuscript_sha256": hashlib.sha256(manuscript.read_bytes()).hexdigest(), "phase": "Ph3", "subchecks": {key: ("BLOCKER" if key == "A" else "CLEAN") for key in "ABCDEFGH"}, "ve": {"gate_contribution": "none", "finding_count": 0}, "aggregate_verdict": "CLEAN"}
        check8 = project / "reviews/check8.json"; check8.write_text(json.dumps(sidecar), encoding="utf-8")
        fm = {"grounding_basis": ["manuscript/main.md"], "check_8_aggregate": "CLEAN", "check_8_adjacent_advisories": {"ve_finding_count": 0}, "reader_accessibility_policy": {"profile_path": "reviews/resolved.json", "profile_sha256": hashlib.sha256(resolved.read_bytes()).hexdigest(), "manuscript_sha256": hashlib.sha256(manuscript.read_bytes()).hexdigest(), "check8_evidence_path": "reviews/check8.json", "check8_evidence_sha256": hashlib.sha256(check8.read_bytes()).hexdigest(), "phase": "Ph3", "candidate_artifact_path": "reviews/candidates.json", "candidate_artifact_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest()}}
        assert frontmatter.validate_reader_accessibility_evidence(fm, project / "reviews/f1.md"), "forged F1 Check 8 content passed"

    print("OK reader_accessibility_adversarial_smoketest")
    return 0


if __name__ == "__main__":
    with semantic_graph_fixture_environment():
        raise SystemExit(main())
