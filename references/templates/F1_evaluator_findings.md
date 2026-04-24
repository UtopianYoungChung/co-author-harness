---
# =========================================================================
# F1 Evaluator findings — v0.7.4 P-3 frontmatter contract; v0.8.0 P2.1b register + routing
# Canonical filename: reviews/ph{1,2,3,4}_findings_<YYYY-MM-DD>_iter<N>.md
# Schema: references/ARTEFACT_FRONTMATTER_SCHEMA.md §3
# Validator: scripts/artefact_frontmatter_validate.py
# Produced by: Evaluator (Step 7 / Step 8 / Step 8.5 of REVIEW_ORCHESTRATION.md)
# =========================================================================

document_type: evaluator_findings
schema_version: "1.1"               # v0.8.0 P2.1b — use 1.1 when carrying register + routing (below)
produced_at: "2026-04-21T00:00:00Z"
produced_by: evaluator
model_used: opus-4-7                 # Opus 4.7 is the non-negotiable floor at Evaluator-Ph2/Ph3/Ph4 (MODEL_ALLOCATION.md §2)
cycle_id: "TEMPLATE-PLACEHOLDER"     # inherited from reviews/phase_state.json
iteration: 0                         # iteration number within the cycle; strictly increasing per (cycle_id, section)
section_heading_path: []             # slash-joined heading path root-to-leaf, e.g. ["3", "3.2", "3.2.1"]; [] for manuscript-scoped
current_phase: Ph3                   # one of {Ph1, Ph2, Ph3, Ph3_converged, Ph4}; v0.7.4 dual-read also accepts {T1..T4}
grounding_basis: []                  # list of file paths read to ground this audit; order matters (captures read order)

# -------------------------------------------------------------------------
# Severity aggregates (required) — counts across all findings this iteration
# -------------------------------------------------------------------------
severity_aggregates:
  blocker_count: 0
  major_count: 0
  minor_count: 0
  advisory_count: 0
  total_count: 0                     # MUST equal sum of the four above (R-Refl-FM-4 on mismatch)

# -------------------------------------------------------------------------
# SAFEGUARD Check 8 (Reader-Experience / Prose Architecture) — required
# -------------------------------------------------------------------------
check_8_aggregate: CLEAN             # one of {CLEAN, BORDERLINE, MAJOR, BLOCKER}; derived per SAFEGUARD_LAYER.md Check 8
check_8_subcheck_counters:
  sub_a_cadence_flag_count: 0        # paragraphs > ~150 words without internal turn-point
  sub_b_rhythm_flag_count: 0         # monotone-dense passages (mean > 28 words, stddev < 6)
  sub_c_first_use_flag_count: 0      # constructs deployed before first-use definition
  sub_d_signpost_flag_count: 0       # sections opening without the preamble
  sub_e_jargon_density_flag_count: 0 # paragraphs introducing > 2 new domain terms
  sub_f_worked_example_flag_count: 0 # density spikes without worked-example turn

# -------------------------------------------------------------------------
# DO-NOT-DISTURB (DnD) byte-verification — required when DnD anchors declared
# -------------------------------------------------------------------------
dnd_byte_verification:
  anchors_verified: true             # true once the Evaluator has run the byte-identity check for every declared anchor
  anchor_count: 0                    # number of DnD anchors declared in research_notes/directives.md
  anchor_drift_count: 0              # number of anchors where bytes differ from prior round; > 0 is a BLOCKER

# -------------------------------------------------------------------------
# Coupling E.2 — graph-grounding overlay verdict (required)
# -------------------------------------------------------------------------
coupling_e2_overlay:
  verdict: "N/A"                     # one of {CLEAN, FINDINGS, N/A}; N/A when graphify artefacts are absent
  graph_stub_citation_count: 0       # wiki source-pages with grounding_status: stub that appear in citations
  section_location_mismatch_count: 0 # citations asserted at wrong section location per graph.json
  missing_citation_candidate_count: 0 # graph-known candidates absent from citation set

# -------------------------------------------------------------------------
# Adversarial register + routing (required at v0.8.0+) — ARTEFACT_FRONTMATTER_SCHEMA.md §3.1
# -------------------------------------------------------------------------
adversarial_register: refinement     # one of {refinement, certification}
routing_rationale: primary_evidence=sentence-level-pass   # MUST match primary_evidence=<check_id> (§8 rule 8)

# -------------------------------------------------------------------------
# Optional fields — include when applicable, omit otherwise
# -------------------------------------------------------------------------
# carry_forward_count: 0             # findings cited by reference (inherited from prior iteration)
# new_signal_count: 0                # defaults to severity_aggregates.total_count if omitted
# escalation_flags: []               # any of {stability_mode_escalation_fired, capability_inversion_refused, accessibility_blocker_surfaced}
# borderline_advisories: []          # any of {[CONVERGENCE-BORDERLINE-ACCESSIBILITY], ...}
# reviewer_agreement_rate: 0.0       # float in [0.0, 1.0]; include when declared convergence_metric is agreement-rate form
# contradiction_density: 0.0         # per-1000-word basis; include when declared convergence_metric is contradiction-density form
---

<!-- =====================================================================
     F1 Evaluator findings — prose body
     Narrate NEW signal only. Carry-forward findings are cited by reference,
     not re-stated. Use the seven-step structure prescribed by
     REVIEW_ORCHESTRATION.md when writing this section.
     ===================================================================== -->

# Evaluator findings — {{cycle_id}} iteration {{iteration}}

## 1. Scope of this iteration

<one-paragraph summary: which section was audited, which steps ran, what was deliberately out of scope>

## 2. Carry-forward findings (from prior iterations)

<cite by reference: "see ph3_findings_2026-04-18_iter6.md F-3, F-7">

## 3. New findings (this iteration)

### Finding F-N — <short title>

- **Severity:** <BLOCKER | MAJOR | MINOR | ADVISORY>
- **Class:** <e.g. E-PSTAGE-DRIFT, [P4-SPLIT-DRIFT], R-SCOPE-VIOLATION>
- **Location:** <section heading path + paragraph index>
- **Grounded in:** <files from `grounding_basis`>
- **Claim:** <one-sentence thematic claim>
- **Evidence:** <inspected quote or byte-verified state>
- **Recommended fix:** <one-sentence generator-actionable directive>

<repeat per new finding; number sequentially F-1, F-2, ... within this iteration>

## 4. SAFEGUARD layer (checks 1–8)

<narrate only the sub-checks that surfaced signal; cite the deterministic counters from the frontmatter>

## 5. Coupling E.2 overlay

<omit if coupling_e2_overlay.verdict == "N/A"; otherwise narrate graph-stub citations, section-location mismatches, and missing-citation candidates>

## 6. Verdict

<one-paragraph synthesis: CLEAN | FINDINGS | BLOCKING; cite severity_aggregates>
