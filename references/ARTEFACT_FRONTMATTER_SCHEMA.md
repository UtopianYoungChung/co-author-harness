# ARTEFACT_FRONTMATTER_SCHEMA.md

*Canonical schema contract for `reviews/*.md` artefact frontmatter. Introduced at plugin v0.7.4 under proposal P-3 (Structured-data-first artefact authoring). Amended at v0.8.0 P2.1b per `proposals/v0.8.0_upgrade_architecture.md` — F1 register + routing, F4 `demoted_check_advisories`, F6 `check_profile` / stability-budget field trio + `threshold_version`. Read by `scripts/artefact_frontmatter_validate.py` and by the P-2 stability sub-mode as the hash-checkable inheritance substrate.*

## 0. Why this file exists

The v0.7.0–v0.7.2 artefact templates were prose-first: the Evaluator narrated the audit in paragraphs, and the verdicts, counters, and severity aggregates surfaced in-line. At v0.7.4, the proposal P-3 reshapes the artefact surface so the diff-able content lives in YAML frontmatter — machine-readable, hash-checkable, inheritable. The prose after the frontmatter narrates only *new signal*; carry-forward verdicts are cited by reference, not re-stated.

P-2's Ph3 stability sub-mode admits inheritance only when the prior round's frontmatter hash matches the current round's derived frontmatter hash. Without a fixed schema per artefact family, the hash-check compares inconsistent surfaces and stability-mode silently diverges round over round. This file closes that gap: every artefact family has a required-field set, an optional-field set, absent-means-default semantics, and a family-specific canonicalization rule used by the P-2 hash.

This file is NORMATIVE. The validator at `scripts/artefact_frontmatter_validate.py` is the enforcement surface. Reflector Phase 2f extends to invoke the validator against each artefact it audits; a frontmatter-schema violation is an `R-Refl-FM-*` finding class (R-Refl-FM-1 missing-required-field; R-Refl-FM-2 type-mismatch or format violation on documented string shapes; R-Refl-FM-3 unknown-field-in-strict-family).

## 1. Family taxonomy

Every **Markdown** artefact that lives under `reviews/` and is read by any agent under v0.7.4+ belongs to exactly one of **six legacy** frontmatter families (F1–F6). The family is declared by the `document_type` frontmatter field, which is required on every such artefact.

At **v0.14.0**, the output economy adds **F7** (JSON evidence packets under `reviews/.harness/evidence/`) and **F8** (Markdown final round reports under `reviews/`). F7 does not use YAML frontmatter; F8 does. Both are validated by `scripts/artefact_frontmatter_validate.py` on its JSON and Markdown lanes respectively (`references/OUTPUT_ECONOMY_PROTOCOL.md` is normative for semantics).

| Family | `document_type` value | Produced by | Read by | Hash-inherited under P-2? |
|---|---|---|---|---|
| F1 Evaluator findings | `evaluator_findings` | Evaluator (Step 7 / Step 8 / Step 8.5) | Planner (consolidated-findings), Reflector (Phase 2f) | Yes (primary substrate) |
| F2 Evaluator deterministic | `evaluator_deterministic` | Evaluator (Step 0a) | Evaluator (later steps), Planner, Reflector (Phase 2f) | Yes |
| F3 Reflector-lightweight | `reflector_lightweight_probe` | Reflector (T1/T2/T3 lightweight mode) | Planner, user | Yes |
| F4 Reflector-full | `reflector_full_report` | Reflector (T4 close-out only) | Planner (skill-proposal gatekeeping), user | No (written once, not inherited) |
| F5 Planner consolidated-findings | `planner_consolidated_findings` | Planner (per-round aggregation) | User, Reflector (Phase 2f) | Yes |
| F6 Planner dispatch plan | `planner_dispatch_plan` | Planner (Phase 0.6, P-1) | User (approval), Reflector (Phase 2f) | No (written once at round entry, not inherited) |
| F7 Output-economy evidence | `evidence_packet` | Evaluator (routine checks); other writers on exception paths | Planner (final assembly), Reflector audits | Yes (when re-run produces a new packet) |
| F8 Final round report | `final_round_report` | Planner (Ph4 / round close) | User | No |

New **legacy** `document_type` values on Markdown under `reviews/*.md` introduced after v0.7.4 must either (a) extend one of the six F1–F6 families by adding optional fields in a subsequent SCHEMA minor, or (b) file a new family via a plugin-update proposal. Ad-hoc `document_type` values are rejected by the validator on the Markdown lane. F7/F8 are registered families with dedicated validation (JSON lane vs F8 frontmatter lane).

## 2. Fields common to all families

Every family carries these fields with identical semantics.

```yaml
document_type:          # required, string, enum per §1
schema_version:         # required, string, "1.0" at v0.7.4; "1.1" after v0.8.0 P2.1b field-adds on F1/F4/F6; "1.x" on other additive field adds; "2.0" on breaking change
produced_at:            # required, ISO 8601 timestamp "YYYY-MM-DDTHH:MM:SSZ"
produced_by:            # required, string, one of {planner, evaluator, generator, reflector}
model_used:             # required, string, one of {opus-4-7, sonnet-4-6, haiku-4-5}
cycle_id:               # required, string, references reviews/phase_state.json cycle identifier
iteration:              # required, integer, ≥ 0; iteration number within the cycle
section_heading_path:   # required, list of strings; slash-joined heading path, root-to-leaf; empty list for manuscript-scoped artefacts
current_phase:          # required, string, one of {Ph1, Ph2, Ph3, Ph3_converged, Ph4}; v0.7.4 dual-read accepts legacy {T1, T2, T3, T3_converged, T4} as well
grounding_basis:        # required, list of paths (relative to project root); files the artefact's claims are grounded in
```

Canonicalization (for P-2 hash): YAML keys ordered lexicographically; scalars normalized (trim trailing whitespace; LF line endings; no BOM); lists preserved in authored order (order IS significant for `grounding_basis` because it records read order); null values omitted.

## 3. Family F1 — Evaluator findings

Artefact names: `reviews/<phase>_findings_<YYYY-MM-DD>_iter<N>.md`, e.g. `reviews/ph3_findings_2026-04-21_iter7.md`.

### 3.1 Required fields (beyond §2 common)

```yaml
severity_aggregates:
  blocker_count:          # integer, ≥ 0
  major_count:            # integer, ≥ 0
  minor_count:            # integer, ≥ 0
  advisory_count:         # integer, ≥ 0
  total_count:            # integer, = sum of above

check_8_aggregate:        # required, string, one of {CLEAN, BORDERLINE, MAJOR, BLOCKER}
check_8_subcheck_counters:
  sub_a_cadence_flag_count:          # integer, ≥ 0
  sub_b_rhythm_flag_count:           # integer, ≥ 0
  sub_c_first_use_flag_count:        # integer, ≥ 0
  sub_d_signpost_flag_count:         # integer, ≥ 0
  sub_e_jargon_density_flag_count:   # integer, ≥ 0
  sub_f_worked_example_flag_count:   # integer, ≥ 0
  sub_g_consolidation_flag_count:     # integer, ≥ 0
  sub_h_register_flag_count:          # integer, ≥ 0

reader_accessibility_policy:
  profile_path:             # string; resolved profile evidence path
  profile_sha256:           # 64-char lowercase SHA-256
  manuscript_sha256:        # current manuscript SHA-256 audited by Check 8
  check8_evidence_path:     # current Check 8 evidence path
  check8_evidence_sha256:   # current Check 8 evidence SHA-256
  phase:                    # one of {Ph2, Ph3, Ph4}
  candidate_artifact_path:  # deterministic A/D/E/F/G/H candidate artifact
  candidate_artifact_sha256:# candidate artifact SHA-256

check_8_adjacent_advisories:
  ve_finding_count:         # integer, ≥ 0; recurrence only, never aggregate

dnd_byte_verification:
  anchors_verified:       # boolean
  anchor_count:           # integer, ≥ 0
  anchor_drift_count:     # integer, ≥ 0; number of anchors where bytes differ from prior round

coupling_e2_overlay:
  verdict:                # string, one of {CLEAN, FINDINGS, N/A}
  graph_stub_citation_count:          # integer, ≥ 0
  section_location_mismatch_count:    # integer, ≥ 0
  missing_citation_candidate_count:   # integer, ≥ 0

adversarial_register:     # string, one of {refinement, certification}; v0.8.0 P2.1b (β A-RG-1/2)
routing_rationale:      # string; MUST be of the form primary_evidence=<check_id> (Action A-RT-1 routing determinism)

reviewer_agreement_rate:  # float, [0.0, 1.0]; declared convergence metric when applicable
contradiction_density:    # float, ≥ 0.0; per-1000-word basis; declared when applicable
```

These bindings are part of the F1 inheritance substrate. VE remains outside `check_8_subcheck_counters` and the A–H aggregate.

### 3.2 Optional fields

```yaml
carry_forward_count:      # integer, ≥ 0; number of prior-round findings cited by reference in the prose
new_signal_count:         # integer, ≥ 0; number of novel findings first surfaced this iteration
escalation_flags:         # list of strings; any of {stability_mode_escalation_fired, capability_inversion_refused, accessibility_blocker_surfaced}
borderline_advisories:    # list of strings; any of {[CONVERGENCE-BORDERLINE-ACCESSIBILITY], ...}
```

### 3.3 Absent-means-default semantics

- `adversarial_register` / `routing_rationale` absent → **not permitted** on artefacts produced at v0.8.0+; both are required fields on F1 at v0.8.0 P2.1b. Legacy v0.7.4 F1 artefacts without these fields are outside the v0.8.0 validator’s forward path; migration is organic (new rounds carry the full shape).
- `carry_forward_count` absent → 0 (prose is assumed to contain all novel findings).
- `new_signal_count` absent → `severity_aggregates.total_count` (assumed all-novel).
- `escalation_flags` absent → `[]`.
- `borderline_advisories` absent → `[]`.
- `reviewer_agreement_rate` absent → permitted only when the section's declared `convergence_metric` is not the reviewer-agreement-rate form; validator cross-checks against `classification.md`.

### 3.4 Inheritance hash

P-2 computes `hash_F1 = SHA-256(canonical_yaml(frontmatter_F1_substrate))` where `frontmatter_F1_substrate` is the subset `{severity_aggregates, check_8_aggregate, check_8_subcheck_counters, dnd_byte_verification, coupling_e2_overlay, reviewer_agreement_rate, contradiction_density}`. The `section_heading_path` and `iteration` are captured by the filename, not the hash; the `grounding_basis` is tracked separately for the Phase 1 grounding audit.

A byte-identical `hash_F1` round-over-round plus a byte-identical manuscript hash is the precondition that lets P-2's Step S-2 inherit without re-running the full seven-step pass.

## 4. Family F2 — Evaluator deterministic

Artefact names: `reviews/<phase>_deterministic_<YYYY-MM-DD>_iter<N>.md`, e.g. `reviews/ph3_deterministic_2026-04-21_iter7.md`.

### 4.1 Required fields

```yaml
# DETERMINISTIC_CHECKS §9a — mechanical pre-flight counters
section_9a_counters:
  em_dash_count:                       # integer, ≥ 0
  em_dash_functional_test_pass:        # boolean
  triadic_list_count:                  # integer, ≥ 0
  absolute_count:                      # integer, ≥ 0; occurrences of absolutist constructions
  llm_tic_count:                       # integer, ≥ 0; "delve", "tapestry", etc.
  sentence_length_violations:
    mean_words_per_sentence:           # float
    stddev_words_per_sentence:         # float
    monotone_flag:                     # boolean; mean > 28 AND stddev < 6

# DETERMINISTIC_CHECKS §9b — accessibility pre-filter (v0.7.2+)
section_9b_counters:
  cadence_flag_count:                  # integer, ≥ 0; candidates under thresholds.cadence
  signpost_flag_count:                 # integer, ≥ 0; sections opening without the preamble
  jargon_density_flag_count:           # integer, ≥ 0; paragraphs introducing > 2 new domain terms

verdict:                 # string, one of {PASS, MINOR, MAJOR, BLOCKER}
```

### 4.2 Optional fields

```yaml
section_breakdown:       # list of per-section counter objects; each has the same shape as section_9a/9b but scoped to one heading_path
anti_pattern_a_count:    # integer, ≥ 0; paired em-dashes as parenthetical glosses
anti_pattern_b_count:    # integer, ≥ 0
anti_pattern_c_count:    # integer, ≥ 0
```

### 4.3 Absent-means-default semantics

- `section_breakdown` absent → counters apply manuscript-wide; no per-section detail available.
- `anti_pattern_a/b/c_count` absent → not audited this round (validator emits an advisory, not a violation).

### 4.4 Inheritance hash

`hash_F2 = SHA-256(canonical_yaml({section_9a_counters, section_9b_counters, verdict}))`. Anti-pattern counts are NOT in the hash because they are advisory and may be absent.

## 5. Family F3 — Reflector-lightweight probe

Artefact names: `reviews/reflector_lightweight_<YYYY-MM-DD>_iter<N>.md`.

### 5.1 Required fields

```yaml
grounding_audit:
  verdict:                 # string, one of {GROUNDING-PASS, GROUNDING-FINDINGS}
  findings_count:          # integer, ≥ 0
  files_audited:           # list of paths (inherited from grounding_basis)

phase_2f_audit:
  rows_checked:            # integer, ≥ 0
  violations_by_class:
    R-Refl-2f-1_notes_length_nonconformance:   # integer, ≥ 0
    R-Refl-2f-2_missing_actor:                 # integer, ≥ 0
    R-Refl-2f-3_nonmonotonic_transition:       # integer, ≥ 0
    R-Refl-2f-4_unknown_trigger:               # integer, ≥ 0
  verdict:                 # string, one of {CLEAN, ADVISORY, MAJOR}

artefacts_inspected:       # required, list of paths (relative to project root)
```

### 5.2 Optional fields

```yaml
dispatch_envelope_recorded:  # boolean; true if the probe was dispatched via Task with subagent_type
  # per I-SubAgent-1 (v0.7.4+, AGENT_CONTRACTS.md); when true, parent agents treat the probe verdict as authoritative-as-read

r_refl_ma_audit:             # optional; only present when P-1 model-allocation audit ran this round
  dispatch_plan_violation_count:  # integer, ≥ 0; R-Refl-MA-4 occurrences
  capability_inversion_refused:   # boolean; true if the plan itself was rejected at dispatch
```

### 5.3 Absent-means-default semantics

- `dispatch_envelope_recorded` absent → `false`; parent agents must re-verify.
- `r_refl_ma_audit` absent → no model-allocation audit ran this round (Phase 2f saw no new rows or round pre-dates v0.7.4 P-1).

### 5.4 Inheritance hash

`hash_F3 = SHA-256(canonical_yaml({grounding_audit.verdict, phase_2f_audit.verdict, phase_2f_audit.violations_by_class}))`. Counts other than the violation breakdown are not in the hash (they are metadata, not contractual state).

## 6. Family F4 — Reflector-full report

Artefact names: `reviews/reflector_full_<YYYY-MM-DD>.md`. Written once per T4/Ph4 close-out; not inherited.

### 6.1 Required fields

```yaml
phase_aggregates:
  phase_1_evidence_gathering:   {artefacts_read: integer, verdict: string}
  phase_2_a_grounding:          {verdict: string, findings_count: integer}
  phase_2_d_t3_convergence:     {sections_audited: integer, stale_sections: integer, verdict: string}
  phase_2_e_mcr_volatility:     {volatility_score: float, verdict: string}
  phase_2_f_row_contract:       {rows_audited: integer, violations: integer, verdict: string}
  phase_2_g_accessibility:      # v0.7.2+
    recurring_flags: list
    cross_project_patterns: list
    verdict: string
  phase_2_5_self_audit:         {verdict: string}
  phase_2_5_1_hallucination:    {instances: integer, verdict: string}
  phase_2_6_protocol_self:      {verdict: string}
  phase_3_memory_update:        {lessons_added: integer, lessons_merged: integer}
  phase_4_skill_proposals:      {new_proposals: integer, filed_at: path}
  phase_5_wiki_ingest:          {status: string, wiki_page_key: string}  # Coupling D
  phase_6_session_close:        {verdict: string}

overall_verdict:        # string, one of {CLEAN, ADVISORY, MAJOR, BLOCKER}
```

### 6.2 Optional fields

```yaml
plugin_update_proposals_filed:  # list of proposal-file paths, if any were generated
lessons_promoted_to_wiki:       # list of wiki page keys (Coupling C)
historical_audits:              # object; historical rounds retroactively audited this session
  confirmation_failed_migration: {rows_retouched: integer, verdict: string}

demoted_check_advisories:       # v0.8.0 P2.1b — append-only across Ph3 iterations (Action A-RT-1 routing to F4)
  - check_id:                   # string; demoted check class identifier
    finding_summary:            # string; one-line summary
    severity:                   # string, one of {MINOR, MAJOR, ADVISORY, BLOCKER}
    source_iteration:           # integer, ≥ 0
    routing_rationale:          # string; same primary_evidence=<check_id> shape as F1 when applicable
```

### 6.3 Absent-means-default semantics

- F4 is TOO consequential to tolerate absent-means-default on required fields. The validator emits `R-Refl-FM-1` on any required-field absence. Only the optional fields default to empty/unset.
- `demoted_check_advisories` absent → no demoted-class advisories filed this close-out; append-only list when present.

### 6.4 Inheritance hash

F4 is not inherited. No hash is computed.

## 7. Family F5 — Planner consolidated-findings

Artefact names: `reviews/consolidated_findings_report_<YYYY-MM-DD>_iter<N>.md`.

### 7.1 Required fields

```yaml
scope_declared:          # string, one of {local, cross_scope}; v0.7.0+ EG-3 fires on cross_scope at Ph2
aggregated_severity:
  blocker_count:         # integer, ≥ 0; sum across F1 artefacts this round
  major_count:           # integer, ≥ 0
  minor_count:           # integer, ≥ 0
  advisory_count:        # integer, ≥ 0

aggregated_check_8:      # string, one of {CLEAN, BORDERLINE, MAJOR, BLOCKER}; worst-case of F1 per-section aggregates

decision_surface:
  menu_items_presented:  # list of strings; e.g. [/run-phase-3, /run-phase-3-stability, /ph3-terminate, /ph3-reject]
  recommended_first:     # string; the first-ranked menu item
  ceiling_lock_detected: # boolean; v0.7.4 P-8 ceiling-lock marker

outgoing_markers:        # list of strings; e.g. [[CONVERGENCE-STABLE], [CEILING-LOCK-STABLE]]
```

### 7.2 Optional fields

```yaml
dispatch_plan_reference:  # path; reviews/dispatch_plan_<cycle_id>.md when P-1 Phase 0.6 ran this round
mcr_state:                # object; present only when preparing MCR admission
  lagging_sections: list
  total_iteration_budget: integer
  mcr_admission_granted: boolean
```

### 7.3 Absent-means-default semantics

- `dispatch_plan_reference` absent → Phase 0.6 did not run (round pre-dates v0.7.4 P-1 or was explicitly skipped per project directive).
- `mcr_state` absent → round is not an MCR admission round.
- `ceiling_lock_detected` absent → `false`.

### 7.4 Inheritance hash

`hash_F5 = SHA-256(canonical_yaml({scope_declared, aggregated_severity, aggregated_check_8, outgoing_markers}))`. The `decision_surface` is not in the hash because the menu ordering depends on detected state that the hash already captures (ceiling-lock, aggregated Check 8); a menu re-order that changes `recommended_first` without changing any of the hashed fields is a Planner-logic bug, not an inheritance-breaking state change.

## 7a. Family F6 — Planner dispatch plan (v0.7.4, P-1)

Artefact names: `reviews/dispatch_plan_<cycle_id>.md`, one per round, written once at Phase 0.6 by the Planner and user-approved before any downstream dispatch fires. The artefact is the round-scoped user-gated checkpoint introduced by proposal P-1 to replace inferred dispatch with a declared dispatch envelope.

### 7a.1 Required fields (beyond §2 common)

```yaml
round_id:                 # string; equal to cycle_id on the entry-iteration row of reviews/phase_state.json
sections_in_scope:        # list of strings; slash-joined section_heading_path values for every section the round will touch; [] iff the round is a Phase-only orchestration (e.g., MCR assembly)
dispatched_agents:        # list of objects; one entry per agent expected to engage during the round
  - agent:                # string, one of {planner, evaluator, generator, reflector}
    phase:                # string, one of {Ph1, Ph2, Ph3, Ph3_converged, Ph4}; phase at which the dispatch fires
    model_allocation:     # string, one of {opus-4-7, sonnet-4-6, haiku-4-5}; the resolved model per references/MODEL_ALLOCATION.md §2
    scope:                # string, one of {per_section, manuscript_level, cycle_level}; per-section is the default, manuscript_level applies under P-7 batching, cycle_level is Planner-only orchestration
    purpose:              # string (≤ 140 chars); one-line rationale the user can skim
checks_scheduled:         # list of strings; the deterministic and judgment checks planned to run this round; drawn from {safeguard_1..8, grounding_audit, d_style_profile_check, deterministic_step_0a, coupling_e2_overlay, accessibility_overlay, contract_verification}
user_approval_required:   # boolean; MUST be true at v0.7.4 (the field is present to future-proof against v0.7.5+ relaxation proposals)
```

### 7a.2 Optional fields

```yaml
subagent_envelope:        # list of objects; present iff any dispatched_agents entry delegates to a subagent under I-SubAgent-1/2/3
  - dispatching_agent:    # string; the agent issuing the delegation
    subagent_type:        # string; the delegated role (e.g., check8_aggregator, grounding_auditor, deterministic_counter)
    verdict_authoritative_as_read:  # boolean; MUST be true under I-SubAgent-1
stability_sub_mode_anticipated:  # boolean; Phase 0.6 declares that the round is expected to run under P-2's reduced envelope
ceiling_lock_anticipated: # boolean; Phase 0.6 declares that a P-8 ceiling-lock proposal is the expected Ph3 exit
mcr_admission_anticipated: # boolean; Phase 0.6 declares that this round is the MCR assembly round
notes:                    # string (≤ 500 chars); free-text Planner rationale visible to the user
user_approval_signature:  # object; populated only after user approval
  approved_at:            # ISO 8601 timestamp
  approved_by:            # string; user identifier or "user" for the local session
  modifications_recorded: # boolean; true iff the approved plan differs from the initially-emitted plan

check_profile:            # string, one of {refine, structural, deep}; v0.8.0 P2.1b — Ph3 iteration profile (maps β P-11 naming to short tokens; see proposals/v0.8.0_upgrade_architecture.md §3.2)
structural_delta_flag:    # boolean; true when section-level structural edit expected this round
parallel_dispatch:        # boolean; false opts into sequential dispatch (default true under refine per v0.7.5 A-OT-3)
threshold_version:        # string; RC tag, e.g. v0.7.5-provisional (budget/threshold calibration; v0.7.5 proposal)
```

### 7a.3 Absent-means-default semantics

- `subagent_envelope` absent → no subagent delegation anticipated for the round.
- `stability_sub_mode_anticipated` absent → `false`; the round is planned as a full pass.
- `ceiling_lock_anticipated` absent → `false`.
- `mcr_admission_anticipated` absent → `false`.
- `user_approval_signature` absent → plan has not yet been approved and the Planner MUST NOT dispatch downstream; validator raises `R-Refl-DP-3` if any downstream artefact produced in this cycle cites this plan by `dispatch_plan_reference` without a populated signature.
- `notes` absent → no free-text rationale; the `purpose` per-dispatch entry carries the justification.
- `check_profile` absent → `refine` (full Ph3-refine envelope unless escalated elsewhere).
- `structural_delta_flag` absent → `false`.
- `parallel_dispatch` absent → `true`.
- `threshold_version` absent → no RC tag (not an error; ship without provisional threshold binding).

### 7a.4 Inheritance hash

F6 is not inherited. No hash is computed. Rationale: the dispatch plan is round-scoped by construction; a subsequent round that carries forward dispatch identical to the prior round is still a distinct round whose consent trail requires its own plan artefact. P-2 stability sub-mode does NOT admit F6 inheritance; the stability-mode round authors a new, short-form F6 that records the stability envelope explicitly (`stability_sub_mode_anticipated: true` and the reduced `checks_scheduled` list).

## 7b. Family F7 — evidence_packet (JSON)

Artefact path: `reviews/.harness/evidence/<event_id>.json` (JSON file; **not** YAML-frontmatter Markdown).

Machine-readable JSON Schema mirror: `references/schemas/f7_evidence_packet.schema.json`.

### 7b.1 Required fields

```yaml
artifact_family: F7          # required, string, exactly F7
document_type: evidence_packet # required, string, exactly evidence_packet
round_id: round_YYYY-MM-DD_NNN
event_id: <round_id>__<kind>__NNN   # must start with round_id + "__"
phase: Ph1|Ph2|Ph3|Ph3_converged|Ph4|round_close
target: manuscript/main.md     # non-empty string; section anchor allowed
evidence_status: complete|partial|incomplete
created_at: ISO-8601           # UTC Z preferred
```

### 7b.2 Optional payload fields

```yaml
checks_run: []
blockers: []
major_actions: []
minor_actions_count: 0
manuscript_delta_summary: ""
state_updates: {}
source_reads: []
final_report_inputs:
  checks_skipped: []
  baseline_metrics: {}
  notes: []
```

F7 uses **strict** unknown-field rejection at the top level (same spirit as F1). F7 deliberately omits legacy common fields (`cycle_id`, `model_used`, `schema_version`, …).

## 7c. Family F8 — final_round_report (Markdown + YAML frontmatter)

Artefact path: `reviews/final_round_report_<round_id>.md`.

### 7c.1 Required frontmatter fields

```yaml
artifact_family: F8
document_type: final_round_report
round_id: round_YYYY-MM-DD_NNN
evidence_status: complete|partial|incomplete
created_at: ISO-8601
```

F8 uses **strict** unknown-field rejection in frontmatter only. Body prose is unconstrained by this schema. Section order for the body is normative in `references/templates/final_round_report.md`.

## 8. Validation rules (enforced by `scripts/artefact_frontmatter_validate.py`)

The validator runs against `reviews/*.md` artefacts on the Markdown lane and against `*.json` files passed explicitly or via `--dir` on the JSON lane. Legacy F1–F6 dispatch is by `document_type` in YAML frontmatter. F7 is validated only on `.json` inputs. F8 is validated when `document_type: final_round_report` appears in YAML frontmatter. Rules:

1. **Required-field presence.** Every required field per family must be present; absence is `R-Refl-FM-1`.
2. **Type conformance.** Every field must match its declared type; mismatch is `R-Refl-FM-2`.
3. **Strict-family unknown-field rejection.** Families F1, F2, F3, F5, F6 are strict — unknown fields are `R-Refl-FM-3`. Family F4 is non-strict (extensibility for historical audits).
4. **Enum conformance.** Every string field with a declared enum must match; violation is `R-Refl-FM-2`.
5. **Cross-field consistency.**
   - `severity_aggregates.total_count == blocker + major + minor + advisory`; mismatch is `R-Refl-FM-4`.
   - `check_8_aggregate` derivation rule: `BLOCKER` if any sub-check is BLOCKER; `MAJOR` if ≥ 2 sub-checks are MAJOR; `BORDERLINE` if exactly 1 sub-check is MAJOR; else `CLEAN`. Violation is `R-Refl-FM-5`.
   - `model_used` must be consistent with the round's `reviews/dispatch_plan_<cycle_id>.md` when present; mismatch is `R-Refl-MA-4` (not an FM finding, routed to the model-allocation audit channel).
6. **Schema-version tolerance.** Validator accepts any `schema_version` in the `1.x` family. `2.x` bumps require validator update.
7. **F6 dispatch-plan consent.** `user_approval_required` MUST be `true` at v0.7.4; violation is `R-Refl-FM-2` (type/enum mismatch). A downstream artefact carrying `dispatch_plan_reference` whose target F6 lacks a populated `user_approval_signature` raises `R-Refl-DP-3` (routed to the dispatch-plan audit channel). An F6 whose `dispatched_agents[].agent` or `dispatched_agents[].phase` disagrees with the actors observed in `phase_state.json` for that cycle raises `R-Refl-DP-1` (plan-drift MAJOR). A round with downstream F1/F2/F3/F5 artefacts but no F6 present raises `R-Refl-DP-2` (missing-plan BLOCKER).
8. **F1 routing string (v0.8.0 P2.1b).** `routing_rationale` MUST match the machine shape `primary_evidence=<check_id>` (no surrounding quotes in the field value; `<check_id>` is a non-empty token using `[A-Za-z0-9_.-]+`). Violation is `R-Refl-FM-2`.
9. **F6 profile + budget tags (v0.8.0 P2.1b).** When present, `check_profile` MUST be one of `{refine, structural, deep}`; `structural_delta_flag` and `parallel_dispatch` MUST be booleans; `threshold_version` MUST be a known RC tag (at v0.8.0 the legal values are `v0.7.5-provisional` and `v0.8.0-provisional`). Violations are `R-Refl-FM-2`.
10. **F4 demoted rows (v0.8.0 P2.1b).** When `demoted_check_advisories` is present, each row MUST carry all five keys and `severity` MUST be one of `{MINOR, MAJOR, ADVISORY, BLOCKER}`. Violations are `R-Refl-FM-1` / `R-Refl-FM-2` as applicable. F4 remains non-strict on unknown top-level keys; `demoted_check_advisories` is a first-class optional block, not a free-form extension.

## 9. Migration from v0.7.3 artefacts

Existing v0.7.3 artefacts do not carry the full frontmatter contract. Migration is **absent-means-advisory**: the validator emits an advisory (`R-Refl-FM-6-legacy`) but does not block, on the theory that v0.7.3 artefacts are read-only carriers of historical state and re-writing them retroactively would mutate the audit trail.

The `scripts/migrate_v073_to_v074_tier_to_phase.py` *[retired from tree]* migration (Task #3) does NOT extend artefact frontmatter. That extension happens organically — new artefacts produced at v0.7.4+ carry the full schema; legacy artefacts keep their reduced shape.

## 10. Interaction with P-2 stability sub-mode

P-2's Step S-0 manuscript-hash check is the first gate; the frontmatter-hash check is the second. The full gate sequence is:

1. Compute `manuscript_hash` per decision 9 (SHA-256 + canonicalization). If differs from prior iteration's recorded `manuscript_hash` → drop through to full `run-phase-3`.
2. Compute `hash_F1` from the current round's F1 substrate; compare against the prior iteration's F1 substrate. Byte-identical → inheritance admitted for F1.
3. Same for `hash_F2`, `hash_F3`, `hash_F5`.
4. On any hash divergence, drop through to full `run-phase-3` for the affected family. Partial inheritance is NOT admitted; either all inherited, or full pass.

This design is stricter than strictly necessary (partial inheritance would be efficiency-positive) but the strict form is defensible on audit-integrity grounds: a round that inherits some families and re-runs others has ambiguous provenance.

## 11. Forward-compatibility notes

v0.7.5 planned changes that this file anticipates:

- New optional field on F1: `convergence_metric_raw` (float, declared-metric raw value) — currently implicit in `reviewer_agreement_rate` / `contradiction_density`; may be lifted to a first-class field.
- New family F6: `generator_self_diagnostic` — post-retirement of Self-T1 Verdict at v0.7.0, there is no Generator-produced audit artefact; a P-stage-adherence self-diagnostic may be proposed at v0.7.5+.

Neither is committed at v0.7.4.

---

*Normative status.* Canonical schema contract for v0.7.4+ artefact frontmatter. Referenced by `co-author-harness/references/PHASE_PROTOCOL.md §3.3` (P-2 inheritance gate) and by `scripts/artefact_frontmatter_validate.py`. Any artefact family added after v0.7.4 must be specified here before its validator dispatch is written.
