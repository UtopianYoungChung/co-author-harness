---
name: accessibility-overlay
description: 'Overlay SAFEGUARD Check 8 reader-accessibility Sub-checks A–G on prose: section-scoped A–F (cadence, rhythm, first-use, signpost, jargon, worked-example) and manuscript-scoped G (cumulative cognitive load). Emits flag findings and aggregate verdict for §3.3.3 TerminalSignoffRow. Use when: Step 8.5, user requests overlay, T2 Check 8 subset, T3 re-read, Reflector 2g replay.'
trigger: when the Evaluator runs Step 8.5 (SAFEGUARD Check 8), when the user asks to run an accessibility overlay on a section or a full manuscript, when the T2 SAFEGUARD subset dispatches Check 8 (A–F only at that rung), when the T3 iterate-until-stable loop needs a re-read against the reader-accessibility criteria (A–G at that rung), or when the Reflector Phase 2g recurrence audit replays Check 8 findings across rounds.
created_by: Reflector (Reader-Experience defence, v0.7.2 pilot; Sub-check G extension v0.8.1)
created_from: >-
  Architectural gap 2026-04-20 — Ph.D.-root CLAUDE.md §13.3 specifies reader-
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
  DETERMINISTIC_CHECKS.md §9b (pre-filter feeder for A, D, E) and §9d
  (pre-filter feeder for G — added 2026-04-23, emits G-candidate boundary list
  from word-count / paragraph-count / consolidation-cue-density probes);
  Ph.D.-root CLAUDE.md §13.3 (operational criteria 1–7) and §13.4 (distinction
  from dumbing-down); Sweller's cognitive-load taxonomy (intrinsic /
  extraneous / germane — G audits the germane-load-across-the-manuscript scale)
version: 1.2
---

# Accessibility Overlay (SAFEGUARD Check 8)

You are executing the **Reader-Experience defence** overlay — the seven Sub-checks A–G of SAFEGUARD Check 8 in structured, Evaluator-native findings form. The overlay is **additive**: it does not replace any existing step, does not modify the manuscript, and does not mutate the DETERMINISTIC_CHECKS §9b pre-filter output it consumes. Every finding it produces carries a sub-check locator (A–G) and a line/span anchor (or, for Sub-check G, a structural-boundary locator) so that downstream Reflector Phase 2g recurrence accounting can trace it back to the text that generated it.

Sub-checks A–F audit **local accessibility** — paragraph cadence, sentence rhythm, first-use definition, section-opening signposting, jargon density per paragraph, worked examples at density spikes. Sub-check G audits **cumulative accessibility** — whether the manuscript carries one-sentence consolidation anchors at structural boundaries where construct accumulation has crossed a working-memory-tax threshold. The two scales have distinct dispatch geometries: A–F run at section scope on every invocation; G runs at full-manuscript scope only, which restricts its binding engagement to T3 and T4 (at T2 the overlay records an advisory note that G will run at T3). Under the v0.8.0+ `run-phase-3-stability` sub-mode, Sub-check G runs advisory-only and does not force escalation to a full Ph3 pass (per D-G-3 decision).

Accessibility here means **extraneous-load reduction** (Sub-checks A–F) and **germane-load consolidation across the manuscript** (Sub-check G): the prose surface should carry the argument without spending the reader's working memory on prose-bookkeeping within a paragraph, and the manuscript should consolidate accumulated material at structural boundaries so the reader's cumulative mental model stays navigable. The overlay does not judge the intellectual difficulty of the material (intrinsic load) and does not ask the Generator to dilute the argument; it judges the seven surface properties specified in Ph.D.-root CLAUDE.md §13.3 and returns findings the Generator can act on.

## Preconditions

Before invoking this skill, verify all of the following. Abort with a clear `accessibility-overlay: no-op (<reason>)` message and return without producing findings if any fails — this is graceful degradation, not error.

1. **Manuscript is classified.** `reviews/classification.md` exists with a populated `t1_pstage_declaration` / `ph1_pstage_declaration` (P0 / P1 / P2). The overlay uses the P-stage to tune the jargon-discipline threshold (Sub-check E) and the worked-example expectation (Sub-check F). Sub-check G's construct-accumulation threshold is P-stage-invariant. Without a classification, the overlay runs at the strictest P1 defaults and marks every finding with `p_stage_adjustment: unknown`.
2. **Dispatch scope resolves.** The dispatching Evaluator or user supplies either a `section_heading_path` (for Sub-checks A–F) or a `scope: full_manuscript` directive (for Sub-check G, which requires the full manuscript to identify structural boundaries and measure construct accumulation). A heading path that resolves to an empty body no-ops with `accessibility-overlay: empty section body`. A Sub-check G invocation that is given a section path rather than a full-manuscript scope no-ops with reason code `G_REQUIRES_FULL_MANUSCRIPT`.
3. **Section has prose.** A section composed entirely of a figure, table, or bibliographic list has no prose surface to audit. No-op with `accessibility-overlay: no prose content`. Mixed sections (prose + table) are audited on the prose portion only. For full-manuscript scope, the overlay extracts prose content from all sections and treats an all-table / all-figure manuscript as `NO_PROSE`.
4. **DETERMINISTIC_CHECKS §9b and §9d pre-filter output is readable.** The overlay reads `reviews/deterministic_<cycle_id>.md` for the §9b "reader cognitive load" pre-filter stub feeding Sub-checks A–F and the §9d "cumulative cognitive load" pre-filter stub feeding Sub-check G. If §9b has not run this cycle, A–F run from scratch against the manuscript text (slower path, same findings). If §9d has not run this cycle, Sub-check G enumerates structural boundaries from scratch (slower path, same findings). §9d is the authoritative deterministic seed for G; §9b does not feed G.
5. **Sub-check gating for T2 vs T3/T4.** At T2 the overlay runs Sub-checks A–F only (G is scope-ineligible at section dispatch) and reports with the T2 severity floor (no BLOCKER escalation on first pass; BLOCKERs from Sub-checks A, D, F are emitted as advisory BLOCKER-CANDIDATE tags). At T2 the overlay additionally emits a single informational note `G_DEFERRED_TO_T3` recording that Sub-check G will run at T3 full-manuscript scope. At T3 and T4 the overlay runs all seven Sub-checks at full severity, subject to the `advisory_until: next_manuscript_at_ph3` transitional flag on Sub-check G (see `READER_ACCESSIBILITY.md §13.5` and `SAFEGUARD_LAYER.md` Check 8 Sub-check G).
6. **Stability sub-mode interaction (v0.8.0+).** Under `run-phase-3-stability` (byte-stable inheritance pass), the overlay runs in a reduced configuration: A–F severity findings are inherited by hash-reference from the prior iteration's F1 artefact; Sub-check G runs **advisory-only** and does not force escalation to a full Ph3 pass. A G finding surfaced under stability mode is logged in the overlay output with `stability_advisory: true` and handed to the Planner for Reflector Phase 2g recurrence accounting without gating the TerminalSignoffRow.

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

## The seven Sub-checks — finding classes and severity floors

Each Sub-check maps to one finding class. The Evaluator's native finding shape is preserved: every finding carries `id`, `sub_check` (A–G), `severity` (MINOR / MAJOR / BLOCKER), `location` (heading_path + line range for A–F; structural-boundary locator such as `end_of_§3` or `pivot_§5.2` for G), `rule_citation`, `evidence`, `suggested_fix` (a one-to-two-sentence action the Generator can act on), and `source_tag: accessibility-overlay@v1.1` so Reflector Phase 2g can trace recurrence.

**MANDATORY — READ ENTIRE FILE.** Before producing findings, you MUST read [`references/sub_checks.md`](references/sub_checks.md) completely from start to finish. That file carries the threshold values, severity floors, and detection procedures for Sub-checks A through G (Cadence-Flag, Rhythm-Flag, First-Use-Flag, Signpost-Flag, Jargon-Density-Flag, Worked-Example-Flag, Consolidation-Anchor-Flag). **NEVER set any range limits when reading this file.** The threshold numerics (150/200/300-word cadence cut-offs, σ<6, P-stage-adjusted term caps, construct-accumulation threshold of 3, the ~3,000 / ~5,000-word G envelope, etc.) are load-bearing — do not approximate them from memory.

**Do NOT load** `SAFEGUARD_LAYER.md` for per-Sub-check thresholds; that file carries the SAFEGUARD framing and the Ph3 gate contract. The per-Sub-check numerics are authoritative in `references/sub_checks.md`.

## Aggregate verdict (what the Planner consumes)

After running all Sub-checks in scope (A–F at T2 section-dispatch; A–G at T3/T4 full-manuscript dispatch), emit a single aggregate verdict:

- **CLEAN** — no Sub-check produced a MAJOR or BLOCKER. Zero or more MINOR findings permitted.
- **BORDERLINE** — exactly one Sub-check produced a MAJOR finding; no BLOCKERs.
- **MAJOR** — two or more Sub-checks produced MAJOR findings, or the same Sub-check produced two or more independent MAJORs; no BLOCKERs.
- **BLOCKER** — one or more Sub-checks produced a BLOCKER finding, regardless of MAJOR or MINOR counts.

**Sub-check G contribution to the aggregate.** When the `advisory_until_flag_active: true` output field is set (manuscript's Ph1 classification predates 2026-04-23), Sub-check G findings are recorded with their severities but do **not** contribute to the A–G aggregate verdict the Planner reads for the TerminalSignoffRow decision; the Planner computes on the A–F aggregate alone while the flag is active. When the flag has retired (manuscript's Ph1 classification postdates 2026-04-23), G findings contribute to the aggregate identically to A–F. Under the `run-phase-3-stability` sub-mode, Sub-check G findings are emitted with `stability_advisory: true` and do not contribute to the aggregate regardless of the `advisory_until` flag state.

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
Sub-check G advisory_until flag: <active:next_manuscript_at_ph3|retired>
Overlay version: accessibility-overlay@v1.1

## Aggregate verdict: <CLEAN|BORDERLINE|MAJOR|BLOCKER>
Aggregate computed over: <A–F | A–G>  (G excluded if advisory_until active or stability sub-mode active)

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
<advisory_until_flag_active: true|false>
<stability_advisory: true|false>

## Recurrence hint for Reflector Phase 2g
<list of sub_check codes that fired this round; compare against the prior round's emission set>
```

The consolidated Evaluator findings report appends this file by reference as §10.8 (the Check 8 subsection of the SAFEGUARD layer output).

## Tier conditioning

- **T1 Plan & Draft.** Overlay is dormant. The Evaluator does not run at T1 (`PHASE_PROTOCOL.md §5.2`); this overlay is Evaluator-scoped and does not run ahead of engagement.
- **T2 Review & Revise.** Overlay runs Sub-checks A–F with T2 severity floor (BLOCKERs on A, D, F are emitted as BLOCKER-CANDIDATE tags, not terminal). Sub-check G is scope-ineligible at T2 (section dispatch) and the overlay emits a single informational `G_DEFERRED_TO_T3` note. Findings are advisory on T2 admission but carry forward to T3 binding the §3.3.3 gate.
- **T3 Iterate & Converge.** Overlay runs Sub-checks A–G at full severity at full-manuscript scope (unless under `run-phase-3-stability`, in which case A–F are hash-inherited from the prior F1 and G runs advisory-only). Aggregate verdict gates TerminalSignoffRow writes via the §3.3.3 accessibility gate. A BLOCKER (on any Sub-check in the aggregate — A–F always, G when the `advisory_until` flag has retired and stability mode is not active) forces another T3 iteration; a BORDERLINE permits signoff with the advisory recorded.
- **T4 Finalize & Close.** Overlay runs Sub-checks A–G at full severity at full-manuscript scope. Findings at T4 feed the Reflector-full aggregated audit; a BLOCKER at T4 fires EG-1-equivalent demotion only if the BLOCKER is bound to a Grounding Protocol violation (e.g., an undefined theoretical construct that is also a fabricated citation). A Sub-check G BLOCKER at T4 under an active `advisory_until` flag surfaces in the Reflector-full aggregate but does not fire demotion for the current manuscript.

## Interaction with DETERMINISTIC_CHECKS §9b

DETERMINISTIC_CHECKS §9b is the pre-filter for Sub-checks A / D / E / F: fast, deterministic, line-oriented. It flags candidate locations where a local-scale violation is likely and populates `reviews/deterministic_<cycle_id>.md` with a structured stub. §9d (added 2026-04-23) is the parallel pre-filter for Sub-check G: it operates at manuscript scope, emitting G-candidate boundaries where preceding-span word count exceeds the P-stage gap envelope AND consolidation-cue density is zero in the pre-heading and post-heading windows. This overlay is the judgment layer for both: it reads the stubs, runs the full seven Sub-checks, and emits findings with severity. When either pre-filter is absent (e.g., on a `/quick-deterministic` skip), the overlay runs the corresponding Sub-checks from scratch against the manuscript text — same findings, slower path.

The two surfaces are **idempotent**: re-running the overlay against the same manuscript snapshot produces byte-identical findings modulo timestamp. This diff-stability is required for the T3 convergence metric — a fluctuating accessibility verdict would break the two-consecutive-round stability condition.

## Retention and recurrence accounting

Every overlay run writes its findings file to `reviews/`. The files are **not** pruned across rounds — they accumulate so that the Reflector Phase 2g recurrence audit can compare the current round's emission set against prior rounds. A Sub-check that fires in two or more consecutive rounds within a single project becomes a Phase 4 project-scoped lesson candidate; a Sub-check that fires in two or more projects becomes a Phase 4 package-tier skill-revision candidate (routed through the Planner's three-filter gatekeeper per Ph.D.-root CLAUDE.md §13.4).

## What this overlay is not

- **Not a style linter.** It does not enforce sentence-craft rules (those live in `bacon_2009_well_crafted_sentence_guidelines.md`), narrative-arc rules (`Sexton_Fiction_to_Academic_Writing_Guide.md`), or register-specific rules (`suchman_writing_style.md`). Those sit alongside; this overlay is the meta-rule that makes them operational.
- **Not a readability score.** It does not emit Flesch-Kincaid, Dale-Chall, or any grade-level proxy. Those scores are optimized for lay prose and produce misleading verdicts on PhD-register academic argument.
- **Not a dilution instrument.** The constraint is extraneous-load reduction, not intrinsic-load collapse. A paragraph sustaining a difficult Vidal contradiction-mapping move is fully compliant if its sentences are paced, its constructs defined, and its rhythm carries the reader.
- **Not a substitute for the Evaluator's judgment.** When a finding's evidence is genuinely contested (e.g., the Sub-check C construct "intentionality" is used without an in-section definition because the author argues it is defined by reference to the project's i* SD model), the Evaluator's Independent-reasoning note overrides the overlay's raw emission. The overlay produces findings; the Evaluator adjudicates.

---

*Normative status.* This skill is bound to SAFEGUARD_LAYER.md Check 8 and implements the seven Sub-checks A–G of Ph.D.-root CLAUDE.md §13.3 (criteria 1–7). It is consumed by the Evaluator at Step 8.5 (T2: A–F section subset; T3 and T4: A–G full-manuscript subset) and by the Planner's §3.3.3 accessibility convergence gate. Plugin version: v0.7.2 introduced A–F at overlay v1.0; v0.8.1 extends to A–G at overlay v1.1 with the D-G-2 option-A decision (single skill with a G branch rather than a sibling skill). Sub-check G's advisory-until transitional flag and stability-sub-mode advisory rule are specified in `READER_ACCESSIBILITY.md §13.5` and `SAFEGUARD_LAYER.md` Check 8 Sub-check G respectively; the skill honours both without requiring a SectionStateObject schema change.
