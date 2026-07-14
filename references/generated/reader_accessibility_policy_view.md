# Reader Accessibility Policy View (Generated)

Do not edit. Generated from `references/policies/reader_accessibility.v1.json`; operational prose cites profile keys.

```json
{
  "decision_status": "provisional",
  "recurrence": {
    "package_lesson_distinct_projects": 2,
    "project_lesson_consecutive_rounds": 2,
    "semantic_severity_effect": "none",
    "state_owner": "Reflector evidence plus Planner approval"
  },
  "runtime_modes": {
    "stability": {
      "aggregation_source": "resolved_profile_and_bound_transition_state",
      "independent_member_exclusions": false,
      "negative_prefilter_short_circuit": false
    }
  },
  "thresholds": {
    "cadence": {
      "above_ceiling": {
        "blocker_when": "zero functional turn-points AND zero internal sentence-break signals",
        "current_severity_floor": "MAJOR",
        "mandatory_split": true
      },
      "bands": [
        {
          "deficit_severity": "CLEAN",
          "max_words": 150,
          "min_words": 0,
          "required_functional_turn_points": 0
        },
        {
          "deficit_severity": "MINOR",
          "max_words": 200,
          "min_words": 151,
          "required_functional_turn_points": 1
        },
        {
          "deficit_severity": "MAJOR",
          "max_words": 300,
          "min_words": 201,
          "required_functional_turn_points": 2
        }
      ],
      "candidate_semantics": "nomination_only",
      "functional_classes": [
        "transition",
        "counter_move",
        "worked_example",
        "thematic_refocus"
      ],
      "functional_confirmation_required": true,
      "hard_ceiling_words": 300,
      "internal_sentence_break_signals": [
        "em_dash",
        "colon",
        "semicolon"
      ],
      "persistence": {
        "changes_current_severity": false,
        "identity_key": "paragraph_content_sha256",
        "planner_workflow_trigger_after_unchanged_rounds": 2,
        "reset_on_content_hash_change": true
      },
      "turn_point_candidates": [
        "however",
        "but",
        "by contrast",
        "on the other hand",
        "for example",
        "to illustrate",
        "consider",
        "yet",
        "instead",
        "rather",
        "at this point",
        "the key shift",
        "the counterpoint"
      ],
      "unit": "paragraph_words"
    },
    "consolidation": {
      "candidate_gap_paragraphs": 6,
      "candidate_gap_words": {
        "P0": 800,
        "P1": 700,
        "P2": 600
      },
      "construct_accumulation": 3,
      "deterministic_gap_is_proxy_only": true,
      "long_manuscript_candidate_words": 5000,
      "pre_heading_scan_paragraphs": 2,
      "prior_sections_dependency": 2,
      "short_manuscript_guidance_words": 3000
    },
    "first_use": {
      "definition_window_paragraphs": 1,
      "manuscript_major_section_failures_min": 2
    },
    "jargon": {
      "new_domain_terms_per_paragraph": {
        "P0": 3,
        "P1": 2,
        "P2": 1
      }
    },
    "register": {
      "functional_removability_required": true,
      "hedges_per_100_words_candidate": 2.0,
      "minimum_positive_markers": 2,
      "nominalisation_density_candidate": 0.08,
      "positive_marker_count": 4,
      "prepositional_run_candidate": 3,
      "severity_model": {
        "major_consecutive_passages": 3,
        "minor_negative_markers_max": 2,
        "minor_negative_markers_min": 1,
        "nontechnical_blocker_major_fraction_above": 0.5,
        "ph2_orienting_zero_positive": "blocker_candidate",
        "weighted_roles": [
          "orienting_clause",
          "consolidation_anchor",
          "inter_section_transition"
        ]
      }
    },
    "rhythm": {
      "long_sentence_words_at_least": 25,
      "mean_words_above": 28,
      "minimum_sentence_count": 4,
      "short_sentence_words_at_most": 12,
      "standard_deviation_below": 6
    },
    "section_signpost": {
      "opening_sentences_max": 3,
      "opening_sentences_min": 1
    },
    "verdict_edge": {
      "intensifier_classes_min": 2,
      "intensifier_tokens_min": 3
    },
    "worked_example": {
      "example_window_paragraphs": 1,
      "rhetorical_question_stack_min": 3
    }
  },
  "transitions": {
    "G": {
      "meaning": "new manuscript reaches Ph3",
      "required_observed_count": 1,
      "stability_mode_effect": "aggregation follows runtime_modes.stability plus bound transition state",
      "workflow_effect_after_retirement": null,
      "workflow_effect_while_active": "findings recorded but excluded from aggregate"
    },
    "H": {
      "meaning": "two complete revision cycles with H in scope",
      "required_observed_count": 2,
      "stability_mode_effect": "aggregation follows runtime_modes.stability plus bound transition state",
      "workflow_effect_after_retirement": null,
      "workflow_effect_while_active": "findings recorded but excluded from aggregate"
    },
    "VE": {
      "meaning": "two complete observed advisory cycles",
      "required_observed_count": 2,
      "stability_mode_effect": "recurrence telemetry only",
      "workflow_effect_after_retirement": "recurrence telemetry only",
      "workflow_effect_while_active": "recurrence telemetry only"
    }
  }
}
```
