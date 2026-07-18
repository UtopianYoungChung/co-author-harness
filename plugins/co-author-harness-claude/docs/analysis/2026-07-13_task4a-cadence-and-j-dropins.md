# Task 4A drop-in drafts — cadence adjudication (>200 words) + Sub-check J disposition

*Prepared 2026-07-13 for the Milestone-Feedback-Framework implementation, Task 4A. These are ready-to-paste blocks. They resolve implementation-plan Step-1 cases `cadence_over_200_semantics_disagree` and `subcheck_set_disagrees_a_to_h_vs_j`, and architecture §4.1 repair requirements 2 and 6. Line targets were verified by direct read on 2026-07-13 against package v0.27.0. All numeric authority is centralized in the profile; prose surfaces reference profile keys per Step 5.*

---

## A. Architecture Decision Record (satisfies Step 2 — record the chosen meaning, do not infer from file age)

> **ADR-ACCESS-01 — Cadence semantics for paragraphs above 200 words**
> **Status: PROPOSED** — awaiting explicit adjudication by Joseph. (The earlier "Accepted 2026-07-13" was a drafting error; recording approval before it was given is the exact provenance failure this architecture exists to prevent.)
> **Superseded in part:** severity model, hard-ceiling, and C-8 carve-out details below are revised by `2026-07-13_supervisor-adjudication-v2.md`. Read that file as authoritative where the two differ.
> **Context.** Two live surfaces contradict. `sub_checks.md:13` and `DETERMINISTIC_CHECKS.md:344` treat >200 words as failing regardless of turn-points; `SAFEGUARD_LAYER.md:295` permits >200 words with two turn-points. The surfaces also use two different severity models (magnitude-based vs. recurrence-based).
> **Decision.** A paragraph **may exceed 200 words if it carries the turn-point count its band requires**, up to a hard ceiling above which it fails regardless:
> - ≤150 words: no turn-point required.
> - 151–200: ≥1 turn-point required.
> - 201–300: ≥2 turn-points required.
> - >300 (`hard_ceiling_words`): fails regardless of turn-point count; the paragraph must be split.
> The deterministic pre-filter continues to flag every paragraph >200 words, but as a **candidate for Evaluator judgment, not a verdict**. Severity is set by turn-point deficit magnitude and escalated by recurrence (see profile). This preserves the SAFEGUARD "two turn-points" intent, retains the sub-check hard ceiling, and eliminates the mechanical ">200 always MAJOR" clause that conflicted with the policy's positive-marker / anti-mechanical philosophy (§13.4) and with the C-7 / C-8 carve-outs.
> **Rationale.** Sub-check A targets *density without cadence* (§13.1); a turn-point is the cadence. A hard ceiling is retained because turn-point density stops being sufficient once a paragraph exceeds within-paragraph working-memory span. `hard_ceiling_words` is a tunable profile key (default 300) so the ceiling can be dialed without touching prose.
> **Consequences.** `sub_checks.md:13` "MAJOR if >200 words with or without turn-point" is removed. The magnitude and recurrence severity models are unified in `thresholds.cadence`. Contract-parity test asserts all four surfaces resolve to the profile.

---

## B. Policy profile — `references/policies/reader_accessibility.v1.json` (cadence block + Sub-check set + J disposition)

Paste these keys into the profile created in Step 4. Unrelated keys (rhythm, jargon, consolidation, lexicons, remediation ordering) are shown as stubs for placement only; fill them from architecture §4.1 requirements 1/3/4/5.

```json
{
  "policy_id": "reader_accessibility",
  "profile_version": "1.0.0",
  "schema": "references/schemas/reader_accessibility_profile.schema.json",
  "authority": {
    "owner": "references/READER_ACCESSIBILITY.md",
    "commitment": "C-5",
    "suspendable": false,
    "provenance_note": "C-5 reader-accessibility is package-local. The former 'Hard Constraint #8, Ph.D.-root CLAUDE.md §9/§13' citation is retained as HISTORICAL PROVENANCE only; package operation never requires an external file to reconstruct policy meaning.",
    "canonical_sha256": "<computed-at-build>"
  },

  "check8_contract": {
    "name": "Check 8 — Reader-Experience / Prose Architecture Audit",
    "telos": "reader_accessibility_cognitive_load",
    "aggregate_members": ["A", "B", "C", "D", "E", "F", "G", "H"],
    "note": "Only A–H contribute to the Check 8 accessibility aggregate. J is NOT a member (see adjacent_advisory_checks)."
  },

  "sub_checks": {
    "A": {"name": "Paragraph cadence",            "scale": "local",      "scope": "section",    "binds_at": ["Ph3", "Ph4"], "advisory_at": ["Ph2"], "gate_contribution": "aggregate"},
    "B": {"name": "Sentence-length distribution", "scale": "local",      "scope": "section",    "binds_at": ["Ph3", "Ph4"], "advisory_at": ["Ph2"], "gate_contribution": "aggregate"},
    "C": {"name": "First-use definition",         "scale": "local",      "scope": "section",    "binds_at": ["Ph3", "Ph4"], "advisory_at": ["Ph2"], "gate_contribution": "aggregate"},
    "D": {"name": "Section-transition signposting","scale": "local",     "scope": "section",    "binds_at": ["Ph3", "Ph4"], "advisory_at": ["Ph2"], "gate_contribution": "aggregate"},
    "E": {"name": "Jargon discipline",            "scale": "local",      "scope": "section",    "binds_at": ["Ph3", "Ph4"], "advisory_at": ["Ph2"], "gate_contribution": "aggregate"},
    "F": {"name": "Worked examples at density spikes","scale": "local",  "scope": "section",    "binds_at": ["Ph3", "Ph4"], "advisory_at": ["Ph2"], "gate_contribution": "aggregate"},
    "G": {"name": "Cumulative load / consolidation anchors","scale": "cumulative","scope": "manuscript","binds_at": ["Ph3", "Ph4"], "advisory_at": ["Ph2"], "gate_contribution": "aggregate", "advisory_until_flag": "next_manuscript_at_ph3"},
    "H": {"name": "Register appropriateness",     "scale": "register",   "scope": "passage",    "binds_at": ["Ph2_orienting_clause", "Ph3", "Ph4"], "advisory_at": ["Ph2_other_roles"], "gate_contribution": "aggregate", "advisory_until_flag": "H_two_revision_cycles"}
  },

  "adjacent_advisory_checks": {
    "J": {
      "name": "Verdict-Edge Discipline",
      "contract": "outside_check8_a_to_h",
      "telos": "verdict_confidence_calibration",
      "aligned_commitment": "C-8/M-6",
      "gate_contribution": "none",
      "advisory_until_flag": "J_two_revision_cycles",
      "rationale": "J audits intensifier-stack / verdict overclaim (v0.13.0, INF3006Y Fugener finding), not extraneous cognitive load. It shares H's passage-scope and advisory machinery but not H's telos; folding it into the accessibility aggregate would let a verdict-overclaim fire E-Ph3-ACCESSIBILITY-BLOCKER-AT-SIGNOFF, a category error.",
      "proposed_relocation": "Dedicated verdict-calibration check aligned with C-8/M-6 (analytic-move-audit surface); tracked as a follow-up, not this release.",
      "letter_gap_note": "The A->H->J sequence intentionally skips 'I' (l/1/I ambiguity convention). There is no Sub-check I."
    }
  },

  "thresholds": {
    "cadence": {
      "bands": [
        {"max_words": 150,              "required_turnpoints": 0},
        {"min_words": 151, "max_words": 200, "required_turnpoints": 1},
        {"min_words": 201, "max_words": 300, "required_turnpoints": 2}
      ],
      "hard_ceiling_words": 300,
      "turnpoint_lexicon": ["however","but","yet","still","by contrast","conversely","suppose","for example","to illustrate","consider","take the case of","reframing","which is to say","put differently"],
      "prefilter_semantics": "candidate_only",
      "prefilter_flag_over_words": 200,
      "base_severity": {
        "turnpoint_deficit_1": "MINOR",
        "turnpoint_deficit_2plus": "MAJOR",
        "hard_ceiling_exceeded": "BLOCKER"
      },
      "recurrence_escalation": {"rule": "+1 severity level per consecutive round the same paragraph locator recurs unresolved", "cap": "BLOCKER"},
      "carve_outs": ["C-8/M-4 demonstrative anaphora counts as a turn-point", "C-8/M-5 cadential verdict is not penalized as low cadence", "C-7 idiolect long-paragraph signature does not override the hard ceiling but is weighed in deficit-1 discretion"]
    },

    "rhythm":        {"mean_words_gt": 28, "stddev_words_lt": 6, "shortest_sentence_warn_gt": 20, "min_paragraph_words_for_test": 100, "_comment": "propagate 20-word warning to all surfaces (arch req 1)"},
    "jargon":        {"new_terms_cap": {"P0": 3, "P1": 2, "P2": 1}, "_comment": "propagate P-stage adjustment to all surfaces (arch req 1)"},
    "consolidation": {"construct_threshold": 3, "prior_section_dependency_threshold": 2, "clean_default_under_words": 3000, "blocker_over_words": 5000, "proxy": {"probe_kind": "proxy", "para_count_gt": 6, "note": "proxy nominates candidates only; never the three-construct predicate (arch req 7)"}}
  },

  "aggregation": {
    "CLEAN": "no member Sub-check produced MAJOR or BLOCKER",
    "BORDERLINE": "exactly one member MAJOR; no BLOCKER",
    "MAJOR": "two or more member MAJORs; no BLOCKER",
    "BLOCKER": "any member BLOCKER",
    "advisory_until_excluded_from_aggregate": ["G:next_manuscript_at_ph3", "H:H_two_revision_cycles"],
    "note": "J is never in the aggregate regardless of its advisory_until state."
  },

  "transitional_flags_semantics": {
    "next_manuscript_at_ph3": "G defined here; live values in phase_state.json.milestone_framework.policy_bindings.reader_accessibility",
    "H_two_revision_cycles": "H defined here; live counters in phase_state, not prose",
    "J_two_revision_cycles": "J defined here; live counters in phase_state, not prose"
  },

  "lexicons": "<stub — arch req 3: hedge/connective replace-semantics; latinate additive-semantics; source paths>",
  "domain_token_exclusions": "<stub — arch req 5: i*/GORE/HCI seeds + project terminology_register/glossary sources>",
  "remediation_ordering_h_register_shift": "<stub — arch req 4: semicolon > colon > explicit signpost phrase > em-dash-only-if-style-profile-permits>"
}
```

---

## C. Prose replacements (Step 5 — surfaces cite profile keys, never redefine numerics)

### C1 — `references/SAFEGUARD_LAYER.md` §A, replace lines 293–297

```markdown
### A. Paragraph cadence (§13.3 criterion 1; thresholds in `policies/reader_accessibility.v1.json → thresholds.cadence`)

1. Enumerate every paragraph in scope. For each paragraph, resolve its word-band from `thresholds.cadence.bands` and count internal turn-points (a transition, a worked example, a counter-claim, a thematic refocus) using `thresholds.cadence.turnpoint_lexicon`. A paragraph must carry at least the `required_turnpoints` its band specifies. C-8/M-4 demonstrative anaphora counts as a turn-point and C-8/M-5 cadential verdicts are not penalized (`thresholds.cadence.carve_outs`).
2. A paragraph exceeding `thresholds.cadence.hard_ceiling_words` (default 300) is flagged regardless of turn-point count and must be split.
3. Flag each violating paragraph with its word count and turn-point count.
4. **Severity:** per `thresholds.cadence.base_severity` (turn-point deficit of 1 → MINOR; deficit of 2 or more → MAJOR; hard-ceiling breach → BLOCKER), escalated by `thresholds.cadence.recurrence_escalation` (+1 level per consecutive unresolved round, capped at BLOCKER).
```

### C2 — `skills/accessibility-overlay/references/sub_checks.md` §A, replace the Sub-check A body (the paragraph at line 11 and the severity-floor line at 13)

```markdown
## Sub-check A — Paragraph cadence (Cadence-Flag)

Scan every paragraph in the section. Resolve each paragraph's word-band and required turn-point count from `policies/reader_accessibility.v1.json → thresholds.cadence.bands`; detect turn-points via `thresholds.cadence.turnpoint_lexicon`. A paragraph is **flagged** when its turn-point count is below its band's `required_turnpoints`, or when its word count exceeds `thresholds.cadence.hard_ceiling_words` (flagged regardless of turn-points; must be split).

Severity floors: resolved from `thresholds.cadence.base_severity` — turn-point deficit of 1 → MINOR; deficit of 2+ → MAJOR; hard-ceiling breach → BLOCKER — then escalated by `thresholds.cadence.recurrence_escalation`. (Supersedes the pre-v1 "MAJOR if >200 words with or without turn-point" rule per ADR-ACCESS-01.)
```

### C3 — `references/READER_ACCESSIBILITY.md` §13.3, replace the cadence bullet at line 33

```markdown
- **Paragraph cadence.** Paragraphs must carry the turn-point count their word-band requires (thresholds in `policies/reader_accessibility.v1.json → thresholds.cadence`): none up to 150 words, one from 151–200, two from 201–300. Beyond the `hard_ceiling_words` bound a paragraph is flagged regardless of turn-points and should be split — turn-point density stops being sufficient once a paragraph exceeds a reader's within-paragraph working-memory span. Density without cadence is the failure mode this criterion targets; a well-paced long paragraph is not.
```

### C4 — `references/DETERMINISTIC_CHECKS.md` §9b, replace the cadence row at line 344 (label it candidate-not-verdict)

```markdown
| **Paragraph cadence: turn-point absence** (feeds Check 8 Sub-check A; **candidate generation only, not a verdict** per ADR-ACCESS-01) | Paragraph with word count > 150 AND no turn-point cue from `thresholds.cadence.turnpoint_lexicon`; additionally, every paragraph > `thresholds.cadence.prefilter_flag_over_words` (200) is surfaced regardless of cue presence so the Evaluator applies the band rule. The pre-filter nominates paragraphs; the overlay assigns the verdict from `thresholds.cadence.bands`. | paragraph locator + word count + cue-absence flag |
```

---

## D. Sub-check J disposition (satisfies §4.1 req 6 — "explicitly classified as a separate advisory outside the A–H contract")

### D1 — `references/SAFEGUARD_LAYER.md`, append after the Sub-check H block (after line 380)

```markdown
### J. Verdict-Edge Discipline — adjacent advisory, NOT a Check 8 aggregate member

Sub-check J (Verdict-Edge Discipline, v0.13.0) audits intensifier-stack / verdict overclaim, whose telos is **verdict-confidence calibration (C-8/M-6)**, not reader cognitive load. Per `policies/reader_accessibility.v1.json → adjacent_advisory_checks.J`, J runs alongside Check 8 but is **outside the A–H accessibility contract**: it does not contribute to the Check 8 aggregate verdict, does not gate the §3.3.3 TerminalSignoffRow, and its `gate_contribution` is `none`. It carries `advisory_until: J_two_revision_cycles`. J findings are logged and routed to Reflector Phase 2g for recurrence accounting only. A follow-up will relocate J to a dedicated verdict-calibration surface aligned with C-8/M-6; until then it lives here as an adjacent advisory. (The A→H→J lettering skips "I" by the l/1/I-ambiguity convention; there is no Sub-check I.)
```

### D2 — `skills/accessibility-overlay/SKILL.md` and `agents/evaluator.md`, one-line reconciliation (paste where Check 8 membership is described)

```markdown
Check 8 comprises Sub-checks **A–H** (the reader-accessibility aggregate). Sub-check **J** (Verdict-Edge Discipline) is an **adjacent advisory** recorded in the same pass but excluded from the A–H aggregate and from the accessibility gate, per `policies/reader_accessibility.v1.json → adjacent_advisory_checks.J`.
```

### D3 — Planner trigger 28 text (`agents/planner.md` / `PHASE_PROTOCOL.md §3.3.3`) — resolves case `planner_trigger_28_names_only_a_to_f`

```markdown
On a Check 8 BLOCKER, the Planner refuses the TerminalSignoffRow write with `E-Ph3-ACCESSIBILITY-BLOCKER-AT-SIGNOFF` and logs trigger 28 `ph3_accessibility_blocker_surfaced`, naming **every profile-active failing Sub-check among A–H** (not only A–F). Sub-check J never contributes to this trigger.
```

---

## E. Which Step-1 smoke-test cases these close

| Case (implementation plan Step 1) | Closed by |
|---|---|
| `cadence_over_200_semantics_disagree` | §A ADR + §B `thresholds.cadence` + §C1–C4 (one rule, four surfaces cite it) |
| `subcheck_set_disagrees_a_to_h_vs_j` | §B `check8_contract.aggregate_members` + `adjacent_advisory_checks.J` + §D1–D2 |
| `planner_trigger_28_names_only_a_to_f` | §D3 |
| `g_proxy_mislabeled_as_construct_threshold` | §B `thresholds.consolidation.proxy.probe_kind: "proxy"` |
| `threshold_repeated_outside_profile` | §C surfaces cite profile keys; contract-parity test (Step 5) enforces |

*Open tuning knob for the user: `hard_ceiling_words` default is 300 (unconditional BLOCKER above it). Raise to 350 if you want a longer tolerance before a forced split — one profile edit, no prose change.*
