---
name: accessibility-overlay
description: 'Overlay SAFEGUARD Check 8 reader-accessibility Sub-checks A–H on prose using the resolved package profile. Emits structured findings and the canonical aggregate for the TerminalSignoffRow.'
trigger: when the Evaluator runs Step 8.5, when the user requests a reader-accessibility audit, or when the Reflector replays canonical Check 8 evidence.
created_by: Reflector (Reader-Experience defence, v0.7.2 pilot; Sub-check G extension v0.8.1; Sub-check H extension v0.10.1)
created_from: >-
  Architectural gap 2026-04-20 — package READER_ACCESSIBILITY.md specifies reader-
  accessibility criteria binding across all P-stages (P0/P1/P2), but no plugin
  surface operationalized them as a reusable overlay. The SAFEGUARD_LAYER.md
  Check 8 authored at v0.7.2 carried six Sub-checks A–F in prose; this
  skill is the overlay that converts them into Evaluator-native findings,
  mirroring the graph-grounding-overlay Coupling E.2 pattern. Sub-check G
  added 2026-04-23 in response to the INF3006Y Co Author Ph4 variant, which
  surfaced the gap between local (A–F) and cumulative (G) accessibility.
pattern_source: >-
  graph-grounding-overlay (structural precedent: Step 0.2 injection, additive
  findings in native format, severity-floor aggregation, source-tag inheritance);
  SAFEGUARD_LAYER.md Check 8 Sub-checks A–G (domain content);
  DETERMINISTIC_CHECKS.md §9b (pre-filter feeder for A, D, E), §9d
  (pre-filter feeder for G — added 2026-04-23, emits G-candidate boundary list
  from word-count / paragraph-count / consolidation-cue-density probes), and
  §9e (pre-filter feeder for H — added 2026-04-27, emits per-passage register
  bundles from nominalisation-density / prepositional-run / hedging-density probes);
  package READER_ACCESSIBILITY.md (operational criteria A–H and distinction
  from dumbing-down); Sweller's cognitive-load taxonomy (intrinsic /
  extraneous / germane — G audits the germane-load-across-the-manuscript scale);
  Williams' Style: Toward Clarity and Grace §6 (prepositional-stack threshold);
  Biber-Conrad register-research literature (nominalisation density 90th-percentile
  ~0.10 academic baseline)
version: 1.5
---

# Accessibility Overlay (SAFEGUARD Check 8)

You are executing the **Reader-Experience defence** overlay — the eight Sub-checks A–H of SAFEGUARD Check 8 in structured, Evaluator-native findings form. The overlay is **additive**: it does not replace any existing step, does not modify the manuscript, and does not mutate the DETERMINISTIC_CHECKS §9b pre-filter output it consumes. Every finding it produces carries a sub-check locator (A–H) and a line/span anchor (or, for Sub-check G, a structural-boundary locator; for Sub-check H, a passage-role + heading-path locator) so that downstream Reflector Phase 2g recurrence accounting can trace it back to the text that generated it.

**Machine authority and membership.** Before dispatch, resolve `references/policies/reader_accessibility.v1.json` with `scripts/reader_accessibility_policy.py` and bind the returned profile/source hashes. Numeric thresholds, override polarity, phase geometry, aggregate membership, and transition meanings come from that resolved profile. Live transition counters/events come only from `phase_state.json.milestone_framework.policy_bindings.reader_accessibility`. Check 8 is exactly A–H. Verdict-Edge (VE) is an adjacent Reflector advisory and never participates in this overlay aggregate or gate.

The resolved profile owns each check's scope, phase geometry, severity, and transition effect. This prose supplies rationale only; it does not create tier-specific membership or severity exceptions.

Accessibility here means **extraneous-load reduction** (A–F), **germane-load consolidation** (G), and **register construction** (H). The package-local profile and `READER_ACCESSIBILITY.md` own these operational criteria; portfolio-root material is provenance only. The overlay nominates evidence without diluting intellectual difficulty.

## Preconditions

Before invoking this skill, verify all of the following. Abort with a clear `accessibility-overlay: no-op (<reason>)` message and return without producing findings if any fails — this is graceful degradation, not error.

1. **Policy binding resolves.** Resolve the package profile and project overrides before reading candidate evidence. Classification prose is context, never policy state.
2. **Dispatch scope resolves.** The dispatching Evaluator or user supplies either a `section_heading_path` (for Sub-checks A–F) or a `scope: full_manuscript` directive (for Sub-check G, which requires the full manuscript to identify structural boundaries and measure construct accumulation). A heading path that resolves to an empty body no-ops with `accessibility-overlay: empty section body`. A Sub-check G invocation that is given a section path rather than a full-manuscript scope no-ops with reason code `G_REQUIRES_FULL_MANUSCRIPT`.
3. **Section has prose.** A section composed entirely of a figure, table, or bibliographic list has no prose surface to audit. No-op with `accessibility-overlay: no prose content`. Mixed sections (prose + table) are audited on the prose portion only. For full-manuscript scope, the overlay extracts prose content from all sections and treats an all-table / all-figure manuscript as `NO_PROSE`.
4. **DETERMINISTIC_CHECKS §9b, §9d, and §9e pre-filter output is readable.** The overlay reads `reviews/deterministic_<cycle_id>.md` for candidate evidence feeding A–H. Missing pre-filter evidence takes the slower from-scratch path without changing findings. For H, negative-marker bundles are telemetry and elaboration aids only: regardless of their `fired` values, the overlay performs the positive-marker audit. A negative-clear bundle never implies `NULL/CLEAN`.
5. **Phase and transition projection.** Resolve scope and workflow effects from `sub_checks`, `transitions`, and `runtime_modes` in the active profile. Live state is accepted only from validated Planner event evidence; prose flags, dates, and classification fields cannot change severity or aggregate membership.
6. **Stability sub-mode.** Apply only the workflow effect declared by `runtime_modes.stability` in the resolved profile. Persistence reuses current-hash evidence to avoid redundant work; it never rewrites recorded severity, excludes an aggregate member, or creates a compatibility severity exception.
7. **Register-model and passage-scope resolution for Sub-check H.** The M1 reader target is profile-owned at `domain_native_register.reader_model` (`register_class: domain-native`). Resolve H geometry separately from project `passage_scope_class`; legacy `register_class` directives containing passage-scope values remain an alias. Apply `register_scope` and `passage_roles`. For course-essay assignment targets M1-M3, exemplar retrieval conditioning and exemplar-warrant review are out of scope: do not load near-neighbor exemplar passages and emit neither a finding nor an advisory for missing exemplar warrant. From M4 onward, surface-warrant absence follows `domain_native_register.derivations.review`: advisory candidate only, never an automatic finding. Argument warrant routes through `domain_native_register.warrant_layers.argument`, never the Check 8 aggregate; Dennett remains `argument-only` and is never a surface-register target.

### No-op reason codes (machine-readable)

When the overlay no-ops, write:

```json
{
  "skill": "accessibility-overlay",
  "status": "noop",
  "reason_code": "<code>",
  "message": "<human readable>",
  "failed_checks": ["<check-key>"],
  "timestamp": "YYYY-MM-DD"
}
```

to `reviews/accessibility_overlay_noop_<YYYY-MM-DD>.json`. Reason codes: `UNCLASSIFIED`, `EMPTY_BODY`, `NO_PROSE`, `HEADING_NOT_RESOLVED`, `G_REQUIRES_FULL_MANUSCRIPT` (Sub-check G invoked with section scope). The no-op file is authoritative; downstream pipelines consume it instead of the absent findings report.

## The A–H Sub-checks — finding classes and severity floors

Each Sub-check emits the exact finding structure required by the Check 8 evidence schema. Severity and aggregate behavior are recomputed from the resolved profile; telemetry fields cannot rewrite either.

**MANDATORY — LOAD MACHINE AUTHORITY.** Resolve and validate `references/policies/reader_accessibility.v1.json` before producing findings. Read `references/READER_ACCESSIBILITY.md` for explanatory procedure, but never recover numeric or severity policy from prose.

**MANDATORY — LOAD MODEL PROSE CORPUS.** After loading `READER_ACCESSIBILITY.md`, load `references/examples/model_prose_corpus.md`. The corpus provides one CLEAN example per Sub-check A–H from Vidal (2022) and Suchman (2007). Use them as positive calibration anchors when adjudicating borderline findings: if a passage is structurally similar to a corpus example and the criterion property is present, default toward CLEAN; if a passage clearly lacks a property that is present in the corpus example, escalate toward MAJOR. The corpus calibration notes identify what pairs of examples together demonstrate that neither alone demonstrates — read them before adjudicating any Sub-check finding rated BORDERLINE or above.

`SAFEGUARD_LAYER.md`, `READER_ACCESSIBILITY.md`, and this skill cite profile keys; none is an independent numeric authority.

## Aggregate verdict (what the Planner consumes)

After running the profile-scoped A–H checks, emit the aggregate returned by the canonical Check 8 recomputation. Do not restate its arithmetic or invent phase/stability exclusions in prose.

The aggregate verdict is the canonical value the Planner reads from `reviews/safeguard_layer_results.md` §Check 8 when evaluating the TerminalSignoffRow accessibility gate (`PHASE_PROTOCOL.md §3.3.3`). On **BLOCKER**, the Planner refuses the terminal signoff write with `E-Ph3-ACCESSIBILITY-BLOCKER-AT-SIGNOFF`. On **BORDERLINE**, terminal signoff is permitted but the advisory `[CONVERGENCE-BORDERLINE-ACCESSIBILITY]` is surfaced and recorded in the TerminalSignoffRow `notes` for Reflector Phase 2g recurrence accounting.

## Output artefact

Write findings to `reviews/safeguard_check8_<YYYY-MM-DD>_<cycle_id>.md` in the following shape:

```markdown
# SAFEGUARD Check 8 — Reader-Experience / Prose Architecture
Scope: <heading_path | full_manuscript>
Cycle: <cycle_id>
P-stage: <P0|P1|P2|unknown>
Phase: <Ph2|Ph3|Ph4>
Stability sub-mode: <active|inactive>
Resolved policy SHA-256: <sha256>
Sub-check G transition state: <active|retired>  (from milestone_framework.policy_bindings.reader_accessibility.transitions.G)
Sub-check H transition state: <active|retired>  (from milestone_framework.policy_bindings.reader_accessibility.transitions.H)
register_class_resolved: domain-native
passage_scope_class_resolved: <technical|mixed|non-technical>
h_observed_count: <integer from policy binding>
inherited_from_pre_h: <true|false>
Overlay version: accessibility-overlay@v1.5

## Aggregate verdict: <CLEAN|BORDERLINE|MAJOR|BLOCKER>
Aggregate members and workflow effects: <resolved profile keys and validated transition projection>

## Sub-check A — Paragraph cadence
<per-finding blocks, or "CLEAN">

## Sub-check B — Sentence-length distribution
...

## Sub-check C — First-use definition
...

## Sub-check D — Section-transition signposting
...

## Sub-check E — Jargon discipline
...

## Sub-check F — Worked examples at density spikes
...

## Sub-check G — Consolidation anchors at structural boundaries
<per-finding blocks with structural-boundary locators, or "CLEAN", or the profile-defined scope-ineligible result>
<g_transition_state: active|retired>
<runtime_mode_effect: value resolved from runtime_modes>

## Sub-check H — Register Appropriateness
<per-finding blocks with passage_role + heading_path locators and schema-valid evidence>
<h_transition_state: active|retired>
<runtime_mode_effect: value resolved from runtime_modes>
<register_class_resolved: domain-native; passage_scope_class_resolved: technical|mixed|non-technical>

## Recurrence hint for Reflector Phase 2g
<list of sub_check codes that fired this round; compare against the prior round's emission set>
```

The consolidated Evaluator findings report appends this file by reference as §10.8 (the Check 8 subsection of the SAFEGUARD layer output).

## Phase conditioning

- **Ph1 Plan & Draft.** Overlay follows the profile's phase geometry and the Evaluator engagement contract.
- **Ph2 Review & Revise.** Run the checks and candidate scopes enabled by the resolved profile. Preserve observed severity in canonical evidence.
- **Ph3 Iterate & Converge.** Overlay runs the profile-scoped A–H checks. The canonical sidecar aggregate gates TerminalSignoffRow writes after applying validated transition events; stability mode creates no independent gate rule.
- **Ph4 Finalize & Close.** Run profile-scoped A–H and feed Reflector-full. Workflow effects derive only from the bound transition event stream.

## Interaction with DETERMINISTIC_CHECKS §9b, §9d, §9e

The deterministic checks nominate candidate evidence using profile keys; the overlay adjudicates function and emits schema-valid A–H findings. Missing pre-filter evidence invokes the profile-defined fallback procedure and cannot change severity semantics.

The three surfaces are **idempotent**: re-running against the same manuscript snapshot and resolved policy produces byte-identical findings modulo timestamp. Current-hash reuse is a workflow optimization, not severity escalation or grace.

## Retention and recurrence accounting

Every overlay run writes its findings file to `reviews/`. Reflector recurrence uses profile keys `recurrence.project_lesson_consecutive_rounds` and `recurrence.package_lesson_distinct_projects`; Planner approval owns promotion. This skill owns no independent recurrence number.

## What this overlay is not

- **Not a style linter.** It does not enforce sentence-craft rules (those live in `bacon_2009_well_crafted_sentence_guidelines.md`), narrative-arc rules (`Sexton_Fiction_to_Academic_Writing_Guide.md`), or register-specific rules (`suchman_writing_style.md`). Those sit alongside; this overlay is the meta-rule that makes them operational.
- **Not a readability score.** It does not emit Flesch-Kincaid, Dale-Chall, or any grade-level proxy. Those scores are optimized for lay prose and produce misleading verdicts on PhD-register academic argument.
- **Not a dilution instrument.** The constraint is extraneous-load reduction, not intrinsic-load collapse. A paragraph sustaining a difficult Vidal contradiction-mapping move is fully compliant if its sentences are paced, its constructs defined, and its rhythm carries the reader.
- **Not a substitute for the Evaluator's judgment.** When a finding's evidence is genuinely contested (e.g., the Sub-check C construct "intentionality" is used without an in-section definition because the author argues it is defined by reference to the project's i* SD model), the Evaluator's Independent-reasoning note overrides the overlay's raw emission. The overlay produces findings; the Evaluator adjudicates.
- **Not a register-classifier-as-style-judge** (added v0.10.1). Sub-check H audits register *construction* within passages whose structural function the protocol has already named, not the canonical domain-native register choice. A technical paragraph that fails the functional removability test is exempt under `passage_scope_class: technical` and `mixed`; under `passage_scope_class: non-technical` it retains necessary domain terms and is held only to positive-marker construction. H cannot demand lay simplification.

---

*Normative status.* This skill implements the exact A–H membership declared by `reader_accessibility.v1.json`. Historical rollout notes are provenance only. Current numeric thresholds, phase geometry, transition meanings, and retirement requirements are profile-owned; live state is policy-binding-owned. VE is never an overlay member.
