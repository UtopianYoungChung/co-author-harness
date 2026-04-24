---
# =========================================================================
# F2 Evaluator deterministic — v0.7.4 P-3 frontmatter contract
# Canonical filename: reviews/ph{1,2,3,4}_deterministic_<YYYY-MM-DD>_iter<N>.md
# Schema: references/ARTEFACT_FRONTMATTER_SCHEMA.md §4
# Validator: scripts/artefact_frontmatter_validate.py
# Produced by: Evaluator (Step 0a of REVIEW_ORCHESTRATION.md)
# =========================================================================

document_type: evaluator_deterministic
schema_version: "1.0"
produced_at: "2026-04-21T00:00:00Z"
produced_by: evaluator
model_used: sonnet-4-6               # Step 0a mechanical pass; Sonnet 4.6 default per MODEL_ALLOCATION.md §2
cycle_id: "TEMPLATE-PLACEHOLDER"
iteration: 0
section_heading_path: []
current_phase: Ph2                   # Step 0a runs at every phase ≥ Ph2; also at Ph1 when Generator self-audits
grounding_basis: []

# -------------------------------------------------------------------------
# DETERMINISTIC_CHECKS §9a — mechanical pre-flight counters (required)
# -------------------------------------------------------------------------
section_9a_counters:
  em_dash_count: 0                   # total em-dash occurrences in scope
  em_dash_functional_test_pass: true # true when every em-dash passes the functional-use test (not zero-tolerance)
  triadic_list_count: 0              # occurrences of three-item rhetorical lists
  absolute_count: 0                  # absolutist constructions (never, always, every, ...)
  llm_tic_count: 0                   # canonical LLM tics (delve, tapestry, nuanced, intricate, ...)
  sentence_length_violations:
    mean_words_per_sentence: 0.0
    stddev_words_per_sentence: 0.0
    monotone_flag: false             # true when mean > 28 AND stddev < 6

# -------------------------------------------------------------------------
# DETERMINISTIC_CHECKS §9b — accessibility pre-filter (v0.7.2+; required)
# -------------------------------------------------------------------------
section_9b_counters:
  cadence_flag_count: 0              # paragraphs > ~150 words without internal turn-point
  signpost_flag_count: 0             # sections opening without the one-to-three-sentence preamble
  jargon_density_flag_count: 0       # paragraphs introducing > 2 new domain terms

# -------------------------------------------------------------------------
# Verdict (required)
# -------------------------------------------------------------------------
verdict: PASS                        # one of {PASS, MINOR, MAJOR, BLOCKER}

# -------------------------------------------------------------------------
# Optional fields
# -------------------------------------------------------------------------
# section_breakdown: []              # per-section counter objects when the audit is manuscript-wide
# anti_pattern_a_count: 0            # paired em-dashes as parenthetical glosses
# anti_pattern_b_count: 0            # (project-specific; see research_notes/directives.md)
# anti_pattern_c_count: 0            # (project-specific)
---

<!-- =====================================================================
     F2 Evaluator deterministic — prose body
     Narrate only what the counters cannot express. When every counter
     is zero and the verdict is PASS, the body may be a single-line
     attestation.
     ===================================================================== -->

# Deterministic pre-flight — {{cycle_id}} iteration {{iteration}}

## 1. Counter snapshot

<tabulate the §9a and §9b counters when the reader benefit exceeds the redundancy with the frontmatter>

## 2. Anti-pattern notes

<narrate the anti-pattern-A / B / C counts when non-zero; cite the specific paragraph locations>

## 3. Verdict

<one-sentence attestation: "PASS. All §9a and §9b counters within limits; em-dash functional test passed.">
