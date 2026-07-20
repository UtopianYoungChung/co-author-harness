#!/usr/bin/env python3
"""Contract smoke tests for the package-local reader-accessibility policy."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "references" / "policies" / "reader_accessibility.v1.json"
SCHEMA = ROOT / "references" / "schemas" / "reader_accessibility_profile.schema.json"
LOADER = ROOT / "scripts" / "reader_accessibility_policy.py"

ACCESSIBILITY_CASES = (
    "dangling_external_hard_constraint_authority",
    "threshold_repeated_outside_profile",
    "cadence_over_200_semantics_disagree",
    "documented_override_is_not_loaded",
    "h_prefilter_not_dispatched_by_canonical_runner",
    "g_proxy_mislabeled_as_construct_threshold",
    "corpus_drift_claim_matches_implementation",
    "transition_state_owned_by_normative_prose",
    "planner_trigger_28_names_only_a_to_f",
    "subcheck_set_disagrees_a_to_h_vs_j",
    "m4_em_dash_fix_violates_resolved_style_profile",
    "m4_or_m5_evidence_missing_policy_hash",
    "hard_ceiling_major_vs_deterministic_blocker",
    "persistence_hash_reset_does_not_rewrite_severity",
    "candidate_requires_functional_confirmation",
    "c8_m4_m5_guard_is_rhythm_not_cadence",
    "ve_excluded_before_and_after_advisory_retirement",
    "profile_has_no_self_hash",
    "phase_enum_has_no_passage_roles",
    "profile_has_no_stubs",
    "override_polarity",
    "policy_hash_drift_is_mf_policy",
    "malformed_input_is_controlled",
)


def check(condition: bool, case: str, message: str) -> None:
    if not condition:
        raise AssertionError(f"{case}: {message}")


_POLICY_NUMBER = re.compile(r"(?i)(?:\b\d+(?:\.\d+)?\b|\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)(?:-(?:to|of)-(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve))?\b)")
_POLICY_CONCEPT = re.compile(r"(?i)(?:\bcadence\b|functional\s+turn[ -]?points?|hard\s+ceiling|accumulated?\s+constructs?|construct\s+accumulation|\bsignpost(?:ing)?\b|\bpreamble\b|jargon\s+(?:terms?|density)|register\s+(?:markers?|fraction|verdict)|positive\s+markers?|negative\s+markers?|sentence\s+(?:count|words?|window|range|length)|paragraphs?\s+(?:count|words?|window|range|length|before)|\b\w+-word\b|\b\w+-paragraph\b|pre-heading\s+window|nested\s+parentheticals?|passage\s+roles?|section\s+list|\bseverity\b|\bverdict\b|(?:blocker|major|minor|clean)\s+(?:fraction|verdict|severity|floor))")


def has_numeric_policy_semantics(line: str) -> bool:
    """Detect threshold/verdict math outside the generated policy projection."""
    normalized = re.sub(r"(?i)\bv\d+(?:\.\d+)+\b|\b\d{4}-\d{2}-\d{2}\b|§[A-Za-z0-9.\-–]+", "", line)
    normalized = re.sub(r"(?i)\bCheck[ -]?8\b|\bSub-check\s+[A-H]\b|\bC-8\b|\bM-\d+\b", "", normalized)
    normalized = re.sub(r"(?i)\btrigger\s+\d+\b|\bPhase\s+\d+[a-z]?\b|\bPh\d\b|\bstep\s+\d+\b|\bline\s+\d+(?:-\d+)?\b", "", normalized)
    normalized = re.sub(r"(?i)\b(?:positive\s+|negative\s+)?marker\s+\d+\b|\bprobe\s+\d+\b|\bfirst[ -]use\b|\bfirst person\b|\bfirst occurrence\b", "", normalized)
    normalized = re.sub(r"^\s*\d+[.)]\s+", "", normalized)
    return bool(_POLICY_NUMBER.search(normalized) and _POLICY_CONCEPT.search(normalized))


def main() -> int:
    detector_mutations = (
        "Require 4 functional turn-points.", "Set the hard ceiling to 350.",
        "Flag after 5 accumulated constructs.", "Use blocker fraction 0.75.",
        "Require a one-to-three sentence preamble.", "Two-of-four register markers is borderline.",
        "Three-of-four register markers is clean.", "Four-of-four register markers is clean.",
        "Scan the two paragraphs before each heading.", "Apply the six-paragraph ceiling.",
        "Use a two-paragraph pre-heading window.",
    )
    for mutation in detector_mutations:
        check(has_numeric_policy_semantics(mutation), "threshold_repeated_outside_profile", f"numeric policy detector missed {mutation!r}")
    check(PROFILE.is_file(), ACCESSIBILITY_CASES[0], f"missing {PROFILE}")
    check(SCHEMA.is_file(), ACCESSIBILITY_CASES[0], f"missing {SCHEMA}")
    check(LOADER.is_file(), ACCESSIBILITY_CASES[0], f"missing {LOADER}")
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    check("canonical_sha256" not in json.dumps(profile), "profile_has_no_self_hash", "self hash present")
    check(set(profile["sub_checks"]) == set("ABCDEFGH"), "subcheck_set_disagrees_a_to_h_vs_j", "aggregate sub-check set is not A-H")
    check(profile["aggregate"]["members"] == list("ABCDEFGH"), "subcheck_set_disagrees_a_to_h_vs_j", "aggregate membership drift")
    check(profile["adjacent_advisory_checks"]["VE"]["gate_contribution"] == "none", "ve_excluded_before_and_after_advisory_retirement", "VE contributes to gate")
    check(set(profile["phase_values"]) == {"Ph1", "Ph2", "Ph3", "Ph4"}, "phase_enum_has_no_passage_roles", "phase enum polluted")
    forbidden = ("todo", "tbd", "placeholder", "fill me")
    lowered = json.dumps(profile).lower()
    check(not any(word in lowered for word in forbidden), "profile_has_no_stubs", "profile contains unfinished data")

    sys.path.insert(0, str(ROOT / "scripts"))
    import reader_accessibility_policy as policy
    import milestone_framework_smoketest as milestone_fixture
    import milestone_framework_validate as milestone_validator

    policy.validate_profile(profile)
    ceiling_major = policy.evaluate_cadence(301, 1, 0, profile)
    wall_blocker = policy.evaluate_cadence(301, 0, 0, profile)
    check(ceiling_major["current_severity"] == "MAJOR" and ceiling_major["mandatory_split"], "hard_ceiling_major_vs_deterministic_blocker", "structured ceiling paragraph is not MAJOR/split")
    check(wall_blocker["current_severity"] == "BLOCKER", "hard_ceiling_major_vs_deterministic_blocker", "wall paragraph is not BLOCKER")
    check(policy.evaluate_cadence(230, 2, 0, profile)["current_severity"] == "CLEAN", "cadence_over_200_semantics_disagree", "two functionally confirmed turns must pass 201-300")
    check(policy.evaluate_cadence(230, 0, 1, profile)["current_severity"] == "MAJOR", "candidate_requires_functional_confirmation", "break signal or candidate was auto-credited")
    approval = [{"sequence": 3, "event": "revision_approved", "approved": True, "content_sha256": "abc"}]
    persistence = policy.update_persistence("abc", "abc", 2, "MINOR", approval)
    reset = policy.update_persistence("abc", "def", 2, "MINOR", approval)
    check(persistence["unchanged_rounds"] == 3 and persistence["current_severity"] == "MINOR", "persistence_hash_reset_does_not_rewrite_severity", "persistence rewrote severity")
    check(reset["unchanged_rounds"] == 0, "persistence_hash_reset_does_not_rewrite_severity", "edit did not reset persistence")

    with tempfile.TemporaryDirectory() as td:
        project = Path(td)
        notes = project / "research_notes"
        notes.mkdir()
        (notes / "directives.md").write_text("register_class: mixed\n", encoding="utf-8")
        (notes / "plain_connectives.txt").write_text("because\ntherefore\n", encoding="utf-8")
        (notes / "hedges.txt").write_text("may\nmight\n", encoding="utf-8")
        (notes / "latinate_whitelist.txt").write_text("therewith\n", encoding="utf-8")
        (notes / "terminology.txt").write_text("actor dependency\n", encoding="utf-8")
        resolved = policy.resolve_policy(project, profile_path=PROFILE)
        lex = resolved["resolved_profile"]["lexicons"]
        check(lex["plain_connectives"] == ["because", "therefore"], "override_polarity", "plain connectives did not replace")
        check(lex["hedges"] == ["may", "might"], "override_polarity", "hedges did not replace")
        check("therewith" in lex["latinate_whitelist"] and len(lex["latinate_whitelist"]) > 1, "override_polarity", "Latinate file did not supplement")
        check("actor dependency" in resolved["resolved_profile"]["domain_token_exclusions"], "override_polarity", "terminology did not extend")
        check(resolved["register_class"] == "domain-native" and resolved["passage_scope_class"] == "mixed", "documented_override_is_not_loaded", "directives override not loaded")
        manuscript = project / "manuscript.md"
        manuscript.write_text("# Opening\n\nThis section turns to an example because the reader needs a map.\n", encoding="utf-8")
        audit_proc = subprocess.run([sys.executable, str(ROOT / "scripts/audit/run_all.py"), str(manuscript), "--project-root", str(project), "--phase", "Ph2", "--cycle-id", "contract", "--skip-d-style-profile", "--out", str(project / "reviews/findings.json")], capture_output=True, text=True, encoding="utf-8", errors="replace")
        check(audit_proc.returncode == 0 and "Traceback" not in audit_proc.stderr + audit_proc.stdout, "h_prefilter_not_dispatched_by_canonical_runner", "canonical runner failed accessibility dispatch")
        candidates = json.loads((project / "reviews/reader_accessibility_candidates_contract.json").read_text(encoding="utf-8"))
        check(candidates["sub_checks"]["H"]["applicable"] and "orienting_clause" in candidates["sub_checks"]["H"]["ph2_scope"], "h_prefilter_not_dispatched_by_canonical_runner", "H Ph2 orienting role not dispatched")
        check(candidates["sub_checks"]["B"]["deterministic_disposition"] == "judgment_only" and candidates["sub_checks"]["D"]["deterministic_disposition"] == "candidate_probe", "h_prefilter_not_dispatched_by_canonical_runner", "deterministic disposition missing")
        check(any(binding["path"].endswith("model_prose_corpus.md") for binding in candidates["source_bindings"]), "corpus_drift_claim_matches_implementation", "mandatory calibration corpus hash absent")
        resolved_sidecar = project / "reviews" / "reader_accessibility_resolved_contract.json"
        resolved_sidecar.write_text(json.dumps(resolved, indent=2) + "\n", encoding="utf-8")
        recursive = subprocess.run([sys.executable, str(ROOT / "scripts/artefact_frontmatter_validate.py"), "--dir", str(project / "reviews"), "--recursive", "--quiet"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        check(recursive.returncode == 0 and "F7" not in recursive.stdout + recursive.stderr, "malformed_input_is_controlled", "policy/audit sidecar was misclassified as F7")

        (notes / "hedges.txt").write_text("# empty replacement\n", encoding="utf-8")
        malformed_override = subprocess.run([sys.executable, str(LOADER), "--project-root", str(project)], capture_output=True, text=True, encoding="utf-8", errors="replace")
        check(malformed_override.returncode == 4 and "Traceback" not in malformed_override.stderr + malformed_override.stdout, "malformed_input_is_controlled", "malformed override escaped controlled contract")

        bad = project / "bad.json"
        bad.write_text("{not-json", encoding="utf-8")
        proc = subprocess.run([sys.executable, str(LOADER), "--profile", str(bad), "--project-root", str(project)], capture_output=True, text=True, encoding="utf-8", errors="replace")
        check(proc.returncode == 4 and "Traceback" not in proc.stderr + proc.stdout, "malformed_input_is_controlled", "malformed profile escaped controlled contract")

    with tempfile.TemporaryDirectory() as td:
        project = Path(td)
        ledger = milestone_fixture._materialize_native_project(project)
        clean = milestone_validator.validate_document(project, milestone_fixture._phase_document(ledger))
        check(not any(finding.code == "MF-POLICY" for finding in clean.findings), "policy_hash_drift_is_mf_policy", "real resolver output did not round-trip into phase state")
        ledger["policy_bindings"]["reader_accessibility"]["profile_sha256"] = "0" * 64
        result = milestone_validator.validate_document(project, milestone_fixture._phase_document(ledger))
        check(any(finding.code == "MF-POLICY" for finding in result.findings), "policy_hash_drift_is_mf_policy", "stale package policy hash did not produce MF-POLICY")

    milestone_schema_text = (ROOT / "references/schemas/milestone_framework.schema.json").read_text(encoding="utf-8")
    f9_schema_text = (ROOT / "references/schemas/f9_milestone_handoff.schema.json").read_text(encoding="utf-8")
    check("policy_bindings" in milestone_schema_text and "policy_evidence" in f9_schema_text, "m4_or_m5_evidence_missing_policy_hash", "milestone/F9 policy evidence schema missing")

    required_text = {
        "references/READER_ACCESSIBILITY.md": ("references/policies/reader_accessibility.v1.json",),
        "references/DETERMINISTIC_CHECKS.md": ("thresholds.cadence", "proxy candidate"),
        "references/SAFEGUARD_LAYER.md": ("Check-8-Adjacent", "A-H aggregate", "adjacent_advisory_checks.VE"),
        "skills/accessibility-overlay/references/sub_checks.md": ("thresholds.cadence", "functional confirmation"),
        "agents/planner.md": ("profile-active", "trigger 28"),
        "scripts/audit/run_all.py": ("build_candidate_artifact",),
        "scripts/reader_accessibility_candidates.py": ("check8_g_prefilter", "check8_h_prefilter"),
    }
    for rel, needles in required_text.items():
        text = (ROOT / rel).read_text(encoding="utf-8")
        for needle in needles:
            check(needle in text, "threshold_repeated_outside_profile", f"{rel} lacks routed contract marker {needle!r}")
    parity_surfaces = [
        "references/PHASE_PROTOCOL.md", "references/SAFEGUARD_LAYER.md",
        "references/DETERMINISTIC_CHECKS.md", "references/ARTEFACT_FRONTMATTER_SCHEMA.md",
        "references/READER_ACCESSIBILITY.md", "references/ADVISORY_UNTIL_SCOPING.md",
        "references/templates/F1_evaluator_findings.md", "skills/accessibility-overlay/SKILL.md",
        "skills/accessibility-overlay/references/sub_checks.md", "skills/run-phase-3/SKILL.md", "skills/run-phase-3-stability/SKILL.md",
        "agents/evaluator.md", "agents/planner.md", "references/research_paper_writing_guidelines.md",
        "references/MASTER_research_and_paper_guidelines.md", "references/lay_term_lexicons.md",
        "scripts/aggregate_h_calibration.py",
    ]
    forbidden_semantics = ("advisory_until", "H_two_revision", "next_manuscript_at_ph3", "h_advisory_cycles", "Sub-check J", "G/H/J", "Ph.D.-root", "short-circuit to NULL/CLEAN", "grace cycle", "corpus_drift", "no independent exclusion")
    for rel in parity_surfaces:
        prose = (ROOT / rel).read_text(encoding="utf-8")
        for phrase in forbidden_semantics:
            check(phrase not in prose, "threshold_repeated_outside_profile", f"{rel} repeats retired/numeric authority {phrase!r}")
    generated_view = ROOT / "references/generated/reader_accessibility_policy_view.md"
    check(generated_view.read_text(encoding="utf-8") == policy.render_policy_view(profile), "threshold_repeated_outside_profile", "generated numeric policy view is stale")
    for rel in parity_surfaces:
        policy_section = False
        for line_number, line in enumerate((ROOT / rel).read_text(encoding="utf-8").splitlines(), start=1):
            if line.startswith("## "):
                if rel == "references/DETERMINISTIC_CHECKS.md":
                    policy_section = bool(re.match(r"## 9[bde]\.", line))
                elif rel == "references/SAFEGUARD_LAYER.md":
                    policy_section = line.startswith("## Check 8 ")
            accessibility_scoped = rel in {"references/READER_ACCESSIBILITY.md", "skills/accessibility-overlay/references/sub_checks.md"} or policy_section or any(marker in line for marker in ("Sub-check", "reader_accessibility", "thresholds.", "runtime_modes.stability"))
            if not accessibility_scoped:
                continue
            if not has_numeric_policy_semantics(line):
                continue
            structural_schema = (rel == "references/ARTEFACT_FRONTMATTER_SCHEMA.md" and "# integer, ≥ 0" in line) or (rel == "references/templates/F1_evaluator_findings.md" and "_flag_count: 0" in line)
            historical_or_calibration = rel == "references/lay_term_lexicons.md" and any(marker in line for marker in ("RETIRED", "historical", "snapshot", "calibration"))
            check(structural_schema or historical_or_calibration, "threshold_repeated_outside_profile", f"{rel}:{line_number} contains independent numeric accessibility policy")
    sentence = (ROOT / "skills" / "sentence-level-pass" / "SKILL.md").read_text(encoding="utf-8")
    check("M-4" in sentence and "M-5" in sentence and "rhythm" in sentence, "c8_m4_m5_guard_is_rhythm_not_cadence", "C-8 guard not relocated")
    hsrc = (ROOT / "scripts" / "check8_h_prefilter.py").read_text(encoding="utf-8")
    check("_corpus_drift" not in hsrc and "corpus_drift" not in profile, "corpus_drift_claim_matches_implementation", "unverified corpus drift implementation claim remains")
    dnr = ROOT / "scripts/domain_native_register_smoketest.py"
    # Pin-contract coverage (asymmetry, degeneracy, seed resolution, MF graph
    # non-gating) lives ONLY in domain_native_register_smoketest.py — invoked
    # here; not re-stated in semantics/adversarial accessibility suites.
    for isolated in (False, True):
        command = [sys.executable] + (["-I", "-S"] if isolated else []) + [str(dnr)]
        proc = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
        check(proc.returncode == 0 and "OK domain_native_register_smoketest" in proc.stdout, "malformed_input_is_controlled", f"domain-native register suite failed (isolated={isolated}): {proc.stdout}{proc.stderr}")
    print(f"OK reader_accessibility_contract_smoketest ({len(ACCESSIBILITY_CASES)} cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
