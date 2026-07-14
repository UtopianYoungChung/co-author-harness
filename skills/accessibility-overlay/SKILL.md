---
name: accessibility-overlay
description: 'Overlay SAFEGUARD Check 8 reader-accessibility Sub-checks A–H on prose: section-scoped A–F (cadence, rhythm, first-use, signpost, jargon, worked-example), manuscript-scoped G (cumulative cognitive load), and passage/manuscript-scoped H (register appropriateness, v0.10.1). Emits flag findings and aggregate verdict for §3.3.3 TerminalSignoffRow. Use when: Step 8.5, user requests overlay, T2 Check 8 subset, T3 re-read, Reflector 2g replay.'
trigger: when the Evaluator runs Step 8.5 (SAFEGUARD Check 8), when the user asks to run an accessibility overlay on a section or a full manuscript, when the T2 SAFEGUARD subset dispatches Check 8 (A–F plus H passage-subset at that rung), when the T3 iterate-until-stable loop needs a re-read against the reader-accessibility criteria (A–H at that rung), or when the Reflector Phase 2g recurrence audit replays Check 8 findings across rounds.
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
  bundles from nominalisation-density / prepositional-run / hedging-density probes
  for short-circuit on no-fired passages);
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

Sub-checks A–F audit **local accessibility** — paragraph cadence, sentence rhythm, first-use definition, section-opening signposting, jargon density per paragraph, worked examples at density spikes. Sub-check G audits **cumulative accessibility** — whether the manuscript carries one-sentence consolidation anchors at structural boundaries where construct accumulation has crossed a working-memory-tax threshold. Sub-check H audits **register accessibility** (added v0.10.1) — whether structurally-required non-technical passages (signpost orienting/contribution clauses, section framing, inter-section transitions, worked-example vignette bodies, consolidation anchor sentences) carry positive register markers (concrete-referent anchoring, agent-verb-object construction, plain-English connectives) rather than abstraction-stacked academic register. The three scales have distinct dispatch geometries: A–F run at section scope on every invocation; G runs at full-manuscript scope only, which restricts its binding engagement to T3 and T4 (at T2 the overlay records an advisory note that G will run at T3); H runs at passage scope under `register_class: technical`/`mixed` (subset of section scope, so resolvable at T2) or at manuscript scope under `register_class: non-technical` (T3+ only). Under the v0.8.0+ `run-phase-3-stability` sub-mode, both Sub-check G and Sub-check H run advisory-only and do not force escalation to a full Ph3 pass.

Accessibility here means **extraneous-load reduction** (A–F), **germane-load consolidation** (G), and **register construction** (H). The package-local profile and `READER_ACCESSIBILITY.md` own these operational criteria; portfolio-root material is provenance only. The overlay nominates evidence without diluting intellectual difficulty.

## Preconditions

Before invoking this skill, verify all of the following. Abort with a clear `accessibility-overlay: no-op (<reason>)` message and return without producing findings if any fails — this is graceful degradation, not error.

1. **Manuscript is classified.** `reviews/classification.md` exists with a populated `t1_pstage_declaration` / `ph1_pstage_declaration` (P0 / P1 / P2). The overlay uses the P-stage to tune the jargon-discipline threshold (Sub-check E) and the worked-example expectation (Sub-check F). Sub-check G's construct-accumulation threshold is P-stage-invariant. Without a classification, the overlay runs at the strictest P1 defaults and marks every finding with `p_stage_adjustment: unknown`.
2. **Dispatch scope resolves.** The dispatching Evaluator or user supplies either a `section_heading_path` (for Sub-checks A–F) or a `scope: full_manuscript` directive (for Sub-check G, which requires the full manuscript to identify structural boundaries and measure construct accumulation). A heading path that resolves to an empty body no-ops with `accessibility-overlay: empty section body`. A Sub-check G invocation that is given a section path rather than a full-manuscript scope no-ops with reason code `G_REQUIRES_FULL_MANUSCRIPT`.
3. **Section has prose.** A section composed entirely of a figure, table, or bibliographic list has no prose surface to audit. No-op with `accessibility-overlay: no prose content`. Mixed sections (prose + table) are audited on the prose portion only. For full-manuscript scope, the overlay extracts prose content from all sections and treats an all-table / all-figure manuscript as `NO_PROSE`.
4. **DETERMINISTIC_CHECKS §9b, §9d, and §9e pre-filter output is readable.** The overlay reads `reviews/deterministic_<cycle_id>.md` for the §9b "reader cognitive load" pre-filter stub feeding Sub-checks A–F, the §9d "cumulative cognitive load" pre-filter stub feeding Sub-check G, and the §9e "register pre-filter" stub feeding Sub-check H (added v0.10.2). If §9b has not run this cycle, A–F run from scratch against the manuscript text (slower path, same findings). If §9d has not run this cycle, Sub-check G enumerates structural boundaries from scratch (slower path, same findings). If §9e has not run this cycle, Sub-check H runs the full register classification on every in-scope passage from scratch (slower path; the §9e short-circuit on no-probe-fired passages is unavailable). §9d is the authoritative deterministic seed for G; §9b does not feed G; §9e is the authoritative deterministic seed for H. §9e bundles are read per-passage when entering H step 1 (see `skills/accessibility-overlay/references/sub_checks.md` §H §6 procedure); a passage whose bundle reports `fired: false (all three probes)` short-circuits to NULL/CLEAN without invoking the full classification.
5. **Sub-check gating for T2 vs T3/T4.** Resolve phase scope, passage-role overrides, and transition effects from `sub_checks` and `transitions` in the active profile. G is scope-ineligible at section dispatch and emits `G_DEFERRED_TO_T3`. At T3 and T4 all A–H checks run at their profile-defined severity. Live G/H state is accepted only from the append-only Planner event evidence under the policy binding; no prose flag, date, or classification field can change gate membership.
6. **Stability sub-mode interaction (v0.8.0+).** Under `run-phase-3-stability` (byte-stable inheritance pass), the overlay runs in a reduced configuration: A–F severity findings are inherited by hash-reference from the prior iteration's F1 artefact; Sub-check G runs **advisory-only** and does not force escalation to a full Ph3 pass; Sub-check H runs **advisory-only** mirroring G's stability-sub-mode treatment. A G or H finding surfaced under stability mode is logged in the overlay output with `stability_advisory: true` and handed to the Planner for Reflector Phase 2g recurrence accounting without gating the TerminalSignoffRow.
7. **`register_class` resolution for Sub-check H.** Read `register_class` from `research_notes/directives.md`. Default `technical` if the field is absent (back-compat-safe path); record the resolved value in the output artefact. The field conditions H's scope: `technical` → H runs on the five non-technical passage roles only; `mixed` → H additionally runs on abstract / introduction / conclusion; `non-technical` → H runs manuscript-wide. The field is orthogonal to P-stage.

### Sub-check H back-compat grace period (v0.10.1)

First H run on a previously-non-H manuscript records `inherited_from_pre_h: true` and runs MINOR-only for that iteration. Detect the first observation from the bound H transition event/counter in `phase_state.json.milestone_framework.policy_bindings.reader_accessibility`, never from missing classification prose.

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

## The eight Sub-checks — finding classes and severity floors

Each Sub-check maps to one finding class. The Evaluator's native finding shape is preserved: every finding carries `id`, `sub_check` (A–H), `severity` (MINOR / MAJOR / BLOCKER), `location` (heading_path + line range for A–F and H passage-scope; structural-boundary locator such as `end_of_§3` or `pivot_§5.2` for G; manuscript-scope locator for H under `register_class: non-technical`), `rule_citation`, `evidence`, `suggested_fix` (a one-to-two-sentence action the Generator can act on), and `source_tag: accessibility-overlay@v1.5` so Reflector Phase 2g can trace recurrence. H findings additionally carry `false_positive_candidate: true|false` (default `false` at emission; user-settable during review; feeds `reviews/h_calibration_<cycle_id>.md`) and, on first H run for a previously-non-H manuscript, `inherited_from_pre_h: true`.

**MANDATORY — READ ENTIRE FILE.** Before producing findings, you MUST read [`references/READER_ACCESSIBILITY.md`](references/READER_ACCESSIBILITY.md) completely from start to finish. That file carries the threshold values, severity floors, and detection procedures for Sub-checks A through H (Cadence-Flag, Rhythm-Flag, First-Use-Flag, Signpost-Flag, Jargon-Density-Flag, Worked-Example-Flag, Consolidation-Anchor-Flag, Register-Flag). **NEVER set any range limits when reading this file.** The threshold numerics (150/200/300-word cadence cut-offs, σ<6, P-stage-adjusted term caps, construct-accumulation threshold of 3, the ~3,000 / ~5,000-word G envelope, the H functional-removability test scope, the H positive/negative marker definitions, etc.) are load-bearing — do not approximate them from memory.

**MANDATORY — LOAD MODEL PROSE CORPUS.** After loading `READER_ACCESSIBILITY.md`, load `references/examples/model_prose_corpus.md`. The corpus provides one CLEAN example per Sub-check A–H from Vidal (2022) and Suchman (2007). Use them as positive calibration anchors when adjudicating borderline findings: if a passage is structurally similar to a corpus example and the criterion property is present, default toward CLEAN; if a passage clearly lacks a property that is present in the corpus example, escalate toward MAJOR. The corpus calibration notes identify what pairs of examples together demonstrate that neither alone demonstrates — read them before adjudicating any Sub-check finding rated BORDERLINE or above.

**Do NOT load** `SAFEGUARD_LAYER.md` for per-Sub-check thresholds; that file carries the SAFEGUARD framing and the Ph3 gate contract. The per-Sub-check numerics are authoritative in `references/READER_ACCESSIBILITY.md`.

## Aggregate verdict (what the Planner consumes)

After running all Sub-checks in scope (A–F + H passage-subset at T2 section-dispatch; A–H at T3/T4 full-manuscript dispatch with H scoped per `register_class`), emit a single aggregate verdict:

- **CLEAN** — no Sub-check produced a MAJOR or BLOCKER. Zero or more MINOR findings permitted.
- **BORDERLINE** — exactly one Sub-check produced a MAJOR finding; no BLOCKERs.
- **MAJOR** — two or more Sub-checks produced MAJOR findings, or the same Sub-check produced two or more independent MAJORs; no BLOCKERs.
- **BLOCKER** — one or more Sub-checks produced a BLOCKER finding, regardless of MAJOR or MINOR counts.

**Sub-check G contribution to the aggregate.** Resolve the G transition from the policy binding. While active, record G severity but exclude it from the gate aggregate; after retirement, G contributes identically to A–F.

**Sub-check H contribution to the aggregate.** Resolve the H transition from the policy binding. While active, record H severity but exclude it from the gate aggregate; after retirement, H contributes identically to A–G. Stability sub-mode keeps both G and H advisory regardless of transition state.

The aggregate verdict is the canonical value the Planner reads from `reviews/safeguard_layer_results.md` §Check 8 when evaluating the TerminalSignoffRow accessibility gate (`PHASE_PROTOCOL.md §3.3.3`). On **BLOCKER**, the Planner refuses the terminal signoff write with `E-Ph3-ACCESSIBILITY-BLOCKER-AT-SIGNOFF`. On **BORDERLINE**, terminal signoff is permitted but the advisory `[CONVERGENCE-BORDERLINE-ACCESSIBILITY]` is surfaced and recorded in the TerminalSignoffRow `notes` for Reflector Phase 2g recurrence accounting.

## Output artefact

Write findings to `reviews/safeguard_check8_<YYYY-MM-DD>_<cycle_id>.md` in the following shape:

```markdown
# SAFEGUARD Check 8 — Reader-Experience / Prose Architecture
Scope: <heading_path | full_manuscript>
Cycle: <cycle_id>
P-stage: <P0|P1|P2|unknown>
Tier: <T2|T3|T4>
Stability sub-mode: <active|inactive>
Resolved policy SHA-256: <sha256>
Sub-check G transition state: <active|retired>  (from milestone_framework.policy_bindings.reader_accessibility.transitions.G)
Sub-check H transition state: <active|retired>  (from milestone_framework.policy_bindings.reader_accessibility.transitions.H)
register_class_resolved: <technical|mixed|non-technical>
h_observed_count: <integer from policy binding>
inherited_from_pre_h: <true|false>
Overlay version: accessibility-overlay@v1.5

## Aggregate verdict: <CLEAN|BORDERLINE|MAJOR|BLOCKER>
Aggregate computed over: <A–F | A–G | A–H>  (G/H contribution resolved from bound transition state; both excluded in stability sub-mode)

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
<per-finding blocks with structural-boundary locators, or "CLEAN", or "DEFERRED_TO_T3" at T2 dispatch, or "NOOP: G_REQUIRES_FULL_MANUSCRIPT" if the dispatch scope was a section path>
<g_transition_state: active|retired>
<stability_advisory: true|false>

## Sub-check H — Register Appropriateness
<per-finding blocks with passage_role + heading_path locators (e.g. signpost_§3, framing_§5, transition_§4_to_§5, vignette_§7_line_120, anchor_end_§3); for each finding: positive_markers_count, negative_markers_count, severity, false_positive_candidate (default false), inherited_from_pre_h (true on grace-period round)>
<h_transition_state: active|retired>
<stability_advisory: true|false>
<register_class_resolved: technical|mixed|non-technical>

## Recurrence hint for Reflector Phase 2g
<list of sub_check codes that fired this round; compare against the prior round's emission set>
```

The consolidated Evaluator findings report appends this file by reference as §10.8 (the Check 8 subsection of the SAFEGUARD layer output).

## Tier conditioning

- **T1 Plan & Draft.** Overlay is dormant. The Evaluator does not run at T1 (`PHASE_PROTOCOL.md §5.2`); this overlay is Evaluator-scoped and does not run ahead of engagement.
- **T2 Review & Revise.** Overlay runs Sub-checks A–F plus the H passage-scope subset (the five non-technical passage roles are section-resolvable so H runs at T2 under `register_class: technical` and `mixed`) with T2 severity floor (BLOCKERs on A, D, F are emitted as BLOCKER-CANDIDATE tags, not terminal; H BLOCKER under `register_class: non-technical` is also BLOCKER-CANDIDATE at T2). Sub-check G is scope-ineligible at T2 (section dispatch) and the overlay emits a single informational `G_DEFERRED_TO_T3` note. Findings are advisory on T2 admission but carry forward to T3 binding the §3.3.3 gate.
- **T3 Iterate & Converge.** Overlay runs the profile-scoped A–H checks. The canonical sidecar aggregate gates TerminalSignoffRow writes after applying validated G/H transition events; stability mode creates no independent gate rule.
- **T4 Finalize & Close.** Overlay runs profile-scoped A–H and feeds Reflector-full. Any G/H workflow exception must be derived from the bound transition event stream. VE remains a separate recurrence advisory.

## Interaction with DETERMINISTIC_CHECKS §9b, §9d, §9e

DETERMINISTIC_CHECKS §9b is the pre-filter for Sub-checks A / D / E / F: fast, deterministic, line-oriented. It flags candidate locations where a local-scale violation is likely and populates `reviews/deterministic_<cycle_id>.md` with a structured stub. §9d (added 2026-04-23) is the parallel pre-filter for Sub-check G: it operates at manuscript scope, emitting G-candidate boundaries where preceding-span word count exceeds the P-stage gap envelope AND consolidation-cue density is zero in the pre-heading and post-heading windows. §9e (added 2026-04-27 at v0.10.2) is the parallel pre-filter for Sub-check H: it operates at passage scope, emitting per-passage register bundles `(probe_name, raw_count, normalised_value, threshold, fired: bool)` for the three H negative markers (nominalisation density / prepositional-phrase run length / hedging density). H's step 1 reads the §9e bundle for each in-scope passage; passages whose bundle reports `fired: false` across all three probes short-circuit to NULL/CLEAN without invoking the full register classification, capturing the cost reduction the pre-filter is designed to deliver. This overlay is the judgment layer for all three pre-filters: it reads the stubs, runs the full eight Sub-checks (A–H), and emits findings with severity. When any pre-filter is absent (e.g., on a `/quick-deterministic` skip), the overlay runs the corresponding Sub-checks from scratch against the manuscript text — same findings, slower path; the §9e short-circuit is unavailable.

The three surfaces are **idempotent**: re-running the overlay against the same manuscript snapshot produces byte-identical findings modulo timestamp. This diff-stability is required for the T3 convergence metric — a fluctuating accessibility verdict would break the two-consecutive-round stability condition.

## Retention and recurrence accounting

Every overlay run writes its findings file to `reviews/`. Reflector recurrence uses profile keys `recurrence.project_lesson_consecutive_rounds` and `recurrence.package_lesson_distinct_projects`; Planner approval owns promotion. This skill owns no independent recurrence number.

## What this overlay is not

- **Not a style linter.** It does not enforce sentence-craft rules (those live in `bacon_2009_well_crafted_sentence_guidelines.md`), narrative-arc rules (`Sexton_Fiction_to_Academic_Writing_Guide.md`), or register-specific rules (`suchman_writing_style.md`). Those sit alongside; this overlay is the meta-rule that makes them operational.
- **Not a readability score.** It does not emit Flesch-Kincaid, Dale-Chall, or any grade-level proxy. Those scores are optimized for lay prose and produce misleading verdicts on PhD-register academic argument.
- **Not a dilution instrument.** The constraint is extraneous-load reduction, not intrinsic-load collapse. A paragraph sustaining a difficult Vidal contradiction-mapping move is fully compliant if its sentences are paced, its constructs defined, and its rhythm carries the reader.
- **Not a substitute for the Evaluator's judgment.** When a finding's evidence is genuinely contested (e.g., the Sub-check C construct "intentionality" is used without an in-section definition because the author argues it is defined by reference to the project's i* SD model), the Evaluator's Independent-reasoning note overrides the overlay's raw emission. The overlay produces findings; the Evaluator adjudicates.
- **Not a register-classifier-as-style-judge** (added v0.10.1). Sub-check H audits register *construction* within passages whose structural function the protocol has already named (signposts, framing, transitions, vignettes, anchors), not register *choice* across the manuscript. A technical paragraph that fails the functional removability test is exempt from H under `register_class: technical` and `mixed`; under `register_class: non-technical` the technical paragraph retains its domain terms and is held only to positive-marker construction at the sentence level. H cannot demand that a propositional-content-bearing technical paragraph become "lay register". The presence-of-positive-markers compliance grammar (rather than absence-of-negative-markers punishment) is the load-bearing design choice that closes the dilution back-door.

---

*Normative status.* This skill implements the exact A–H membership declared by `reader_accessibility.v1.json`. Historical rollout notes are provenance only. Current numeric thresholds, phase geometry, transition meanings, and retirement requirements are profile-owned; live state is policy-binding-owned. VE is never an overlay member.
