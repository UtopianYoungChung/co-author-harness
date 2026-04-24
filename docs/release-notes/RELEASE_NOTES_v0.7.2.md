# Release Notes — research-writing-harness-claude v0.7.2

**Release date:** 2026-04-20
**Theme:** the **Reader-Experience defence** — closing a three-file contract bug where `agents/evaluator.md`, `skills/run-tier-3/SKILL.md`, and `references/DETERMINISTIC_CHECKS.md §9b` referenced eight SAFEGUARD checks while `SAFEGUARD_LAYER.md` contained only six, and at the same time lifting Ph.D.-root CLAUDE.md §13 (binding reader-accessibility, Hard Constraint #8) from a policy statement to an enforced convergence gate at T3 Iterate & Converge.
**Verdict:** CLEARED (point release; two net-new SAFEGUARD checks, one net-new skill, one net-new Reflector phase, one net-new style commitment; no agent retirements, no ladder restructuring).

---

## One-paragraph summary

v0.7.2 is a bug-fix-plus-policy-enforcement point release over v0.7.1. v0.7.1 preserved the four-agent contract and the Lifecycle-Stage Ladder but shipped with a cross-file inconsistency: `agents/evaluator.md §Step 8.5` and `skills/run-tier-3/SKILL.md §5` both referenced "all eight checks," while `SAFEGUARD_LAYER.md` contained only Checks 1–6, and the `DETERMINISTIC_CHECKS §9b` pre-filter fed a "Check 8 work queue" that had no judgment-layer consumer. v0.7.2 closes this gap by authoring **Check 7 (Inter-Sentential Logical Connective Audit)** and **Check 8 (Reader-Experience / Prose Architecture Audit)** in `SAFEGUARD_LAYER.md`. Check 8 operationalises the six reader-accessibility criteria of Ph.D.-root CLAUDE.md §13.3 — paragraph cadence, sentence-length distribution, first-use definition, section-transition signposting, jargon discipline, worked examples at density spikes — via Sub-checks A–F, each with a deterministic pre-filter in §9b and a judgment-layer finding class in the new `skills/accessibility-overlay` skill. Check 8 is wired into the T3 Iterate & Converge convergence gate as the **Reader-Experience defence** at `TIER_PROTOCOL.md §3.3.3`: a Check 8 BLOCKER at T3 terminal signoff causes the Planner to refuse the TerminalSignoffRow write with `E-T3-ACCESSIBILITY-BLOCKER-AT-SIGNOFF` (new failure code) and emit trigger 28 `t3_accessibility_blocker_surfaced` (enum extended from 27 to 28); a BORDERLINE verdict permits signoff with the `[CONVERGENCE-BORDERLINE-ACCESSIBILITY]` advisory carried forward to Reflector Phase 2g for recurrence accounting. The Reflector gains **Phase 2g** (Reflector-full only) executing the Ph.D.-root §13.4 mandate — within-project consecutive-round recurrence becomes a project-scoped lesson candidate; cross-project recurrence becomes a package-tier plugin-update proposal (`A5-accessibility-recurrence`). `STYLE_COMMITMENTS.md` gains commitment **C-5** — the reader-accessibility meta-rule that operationalises C-1…C-4 and is the only commitment that cannot be suspended via the §4 relaxation procedure. Absent-means-passes migration — existing v0.7.1 projects without `reviews/safeguard_check8_*.md` artefacts continue to work unchanged; the §3.3.3 gate becomes binding the first time the Evaluator runs Check 8.

## Headline change — the Reader-Experience defence

```
  reviews/safeguard_layer_results.md
  ┌──────────────────────────────────────────────────────┐
  │  Check 8 aggregate verdict (CLEAN / BORDERLINE / ...  │
  │                              MAJOR / BLOCKER)        │
  └──────────────────────────────────────────────────────┘
           │
           ▼  read by Planner at TerminalSignoffRow write
              and by pre_tier_advance_check.check_clause_h
           │
   ┌───────┴────────────────────────────────────────────────┐
   │                                                         │
   ▼ (BLOCKER)                                               ▼ (CLEAN / BORDERLINE)
   - Planner refuses TerminalSignoffRow                      - Planner accepts TerminalSignoffRow
   - Emits E-T3-ACCESSIBILITY-BLOCKER-AT-SIGNOFF             - On BORDERLINE: records
   - Appends trigger 28 t3_accessibility_blocker_surfaced      [CONVERGENCE-BORDERLINE-ACCESSIBILITY]
   - Refused write does NOT consume iteration budget           advisory in notes
   - [CONVERGENCE-BLOCKED-ACCESSIBILITY] advisory surfaced   - Section flips T3 → T3_converged
   - Section stays at T3 pending clearance                   - Reflector Phase 2g audits
                                                               recurrence across rounds
```

- The gate is **T3-only** — Check 8 runs at T2 (advisory subset) and T4 (full severity), but only binds the TerminalSignoffRow at T3. T2 MAJORs on Sub-checks A, D, F emit as BLOCKER-CANDIDATE to flag forward without terminal emission.
- The gate is **independent of line-diff stability** — a section with zero BLOCKER/MAJOR content findings but a BLOCKER on Check 8 does not converge. Reader-experience is treated as a structural property of the prose, co-equal with argumentative adequacy.
- The gate's **clearance mechanism is prose revision by the Generator**, not a T2/T3 round reset. A Check 8 BLOCKER is cleared when the next Evaluator dispatch returns CLEAN or BORDERLINE; no ledger gymnastics required.
- **Refused TerminalSignoffRow writes do not consume iteration budget** (NEW-H-7 is preserved). A project attempting to close T3 three times over a single accessibility BLOCKER still has the full MCR iteration reserve intact.
- **Absent-means-passes migration semantics.** Projects that have never run Check 8 (no `reviews/safeguard_check8_*.md` file) see the §3.3.3 gate treat the verdict as CLEAN. The gate becomes binding the first time Check 8 runs; no migration script needed.

## What changes at the file level

### Canonical SAFEGUARD spec

- `references/SAFEGUARD_LAYER.md` — **Check 7** (Inter-Sentential Logical Connective Audit) and **Check 8** (Reader-Experience / Prose Architecture Audit) authored. Check 8 contains six Sub-checks A–F with cue lexicons, severity floors, P-stage adjustments, aggregation rule (single MAJOR → BORDERLINE; two MAJORs → MAJOR; any BLOCKER → BLOCKER), output-artefact format (`reviews/safeguard_check8_<section>_<date>_<cycle>.md`), and tier conditioning (T1 dormant / T2 subset / T3 full / T4 full).

### Convergence gate spec

- `references/TIER_PROTOCOL.md §3.3.3` — net-new subsection "Reader-Experience defence (v0.7.2 — Check 8 convergence gate)." Documents gate trigger, gate scope (BLOCKER blocks, MAJOR produces BORDERLINE advisory, MINOR no effect), clearance mechanism, iteration accounting (refused write does not consume budget), logging (trigger 28), and independence from line-diff stability. Cross-references added in §3.3.1 (convergence_metric), §3.3.2 (TerminalSignoffRow schema), §6.1 (MCR admission — Check 8 is binding only on T3→T3_converged, advisory at T2, required-CLEAN at T4).

### Trigger enum and failure codes

- `references/tier_state_schema.md §3 (trigger enum)` — extended from 27 to 28. New trigger 28 `t3_accessibility_blocker_surfaced` records each Planner refusal of a TerminalSignoffRow on accessibility grounds. Trigger enum validators accept both the v0.7.1 27-value set (back-compat) and the v0.7.2 28-value set.
- `references/tier_state_schema.md §6.1 (failure codes)` — net-new code `E-T3-ACCESSIBILITY-BLOCKER-AT-SIGNOFF` with recovery procedure (Evaluator re-runs Check 8 → Generator applies prose revision → next terminal attempt).
- `references/tier_state_schema.md §6.2 (pre-advance check)` — extended from seven-clause to eight-clause guardrail. Clause (h) is the Check 8 accessibility gate, binding only on TerminalSignoffRow writes at T3. Clauses (a)–(g) unchanged.

### Pre-filter (DETERMINISTIC_CHECKS)

- `references/DETERMINISTIC_CHECKS.md §9b` — three new pre-filter marker classes feed Check 8 Sub-checks A, D, and E.
    - **Paragraph cadence** (feeds Sub-check A): paragraphs >150 words without a turn-point cue (transition, worked-example, counter-claim, thematic refocus) from the cue lexicon.
    - **Section-transition preamble absence** (feeds Sub-check D): section opens without both an orienting clause (regex on "where we are in the argument") and a contribution clause (regex on "what this section will do").
    - **Jargon density per paragraph** (feeds Sub-check E): P-stage-scaled cap — P0 flags at ≥4 new domain terms per paragraph, P1 at ≥3, P2 at ≥2.
- Output stub updated with three new counters (`cadence_flag_count`, `signpost_flag_count`, `jargon_density_flag_count`) and three new candidate-location buckets.

### Agent prompts

- `agents/evaluator.md §Step 8.5` — "checks 1, 4, 5" → "checks 1, 4, 5, and 8" with Hard Constraint #8 rationale citation.
- `agents/evaluator.md §T2 item 1 scope budget` — added "and 8."
- `agents/evaluator.md §T2 item 4 outputs` — "SAFEGUARD subset (1, 4, 5, 8)" with T2 advisory carry-forward note (BLOCKER-CANDIDATE tags on A, D, F).
- `agents/planner.md §T3 — Sign terminal row` — rewritten to describe the §3.3.3 gate: Planner reads the most recent `reviews/safeguard_check8_*.md` Check 8 aggregate verdict before accepting TerminalSignoffRow; refuses on BLOCKER with `E-T3-ACCESSIBILITY-BLOCKER-AT-SIGNOFF`; emits trigger 28; permits on CLEAN or BORDERLINE with advisory in `notes`; refused write does not consume iteration budget.
- `agents/reflector.md §Phase 1` — evidence-gathering list extended with `reviews/safeguard_check8_*.md` glob and `reviews/t3_convergence_signoff.md` references.
- `agents/reflector.md §Phase 2g` — net-new phase (Reflector-full only) with six sub-steps: Check 8 corpus assembly, within-project recurrence (consecutive-round = lesson candidate), cross-project recurrence via wiki register (`A5-accessibility-recurrence` proposal code), BORDERLINE-permitted signoff audit, BLOCKER clearance-cost distribution, §10e emission.
- `agents/reflector.md §Phase 5 §10e` — new reflection-report subsection template.

### Tier entry skills

- `skills/run-tier-2/SKILL.md §3 table` — Evaluator row extended with SAFEGUARD subset (1, 4, 5, 8) responsibility; added output path `reviews/t2_safeguard_<date>_<cycle>.md`.
- `skills/run-tier-2/SKILL.md §4 step 5a` — net-new step "Evaluator SAFEGUARD subset at T2" covering Check 8 Sub-checks A–F with advisory semantics and BLOCKER-CANDIDATE tagging.
- `skills/run-tier-2/SKILL.md §4 step 11` — "Seven-clause" → "Eight-clause" with clarification that clause (h) does not fire at T2 (binds only on TerminalSignoffRow at T3).
- `skills/run-tier-3/SKILL.md` — existing "all eight checks" references now resolve (were dangling at v0.7.1).

### New skill

- `skills/accessibility-overlay/SKILL.md` — net-new reusable overlay at v0.7.2. Converts a section's prose into a structured Check 8 findings report consumable by the Evaluator at T2, T3, and T4. Six finding classes (Cadence-Flag, Rhythm-Flag, First-Use-Flag, Signpost-Flag, Jargon-Density-Flag, Worked-Example-Flag) with severity floors matched to the SAFEGUARD_LAYER Check 8 aggregation rule. Preconditions with no-op reason codes (UNCLASSIFIED, EMPTY_BODY, NO_PROSE, HEADING_NOT_RESOLVED). Tier conditioning (T1 dormant / T2 subset / T3 full / T4 full). Structural precedent: `skills/graph-grounding-overlay` (Coupling E.2).

### Notifications catalogue

- `references/tier_notifications.yaml` — header comment updated from "27-trigger" to "28-trigger" enum. `convergence_stable` template coupled to Check 8 verdict. Net-new notification blocks:
    - `convergence_blocked_accessibility` (full `user_template` with gate semantics and iteration-budget preservation note)
    - `convergence_borderline_accessibility` (advisory-only, notes Phase 2g recurrence)
    - `t3_accessibility_blocker_surfaced` (trigger 28, `presented_to_user: false` — ledger-only)

### Style-commitment extension

- `references/STYLE_COMMITMENTS.md §1 table` — added commitment **C-5** row (reader-accessibility meta-rule; sources: Ph.D.-root §13, SAFEGUARD Check 8, accessibility-overlay skill, Sweller taxonomy).
- `references/STYLE_COMMITMENTS.md §3 table` — added Reflector Phase 2g row for cross-round accessibility recurrence.
- `references/STYLE_COMMITMENTS.md §4 relaxation procedure` — explicit carve-out: C-5 cannot be suspended wholesale. Project-scoped severity-floor overrides permitted via `research_notes/directives.md`.

### Non-binding reference surfaces

- `references/MASTER_research_and_paper_guidelines.md §A.1` — new reader-accessibility constraint bullet with cross-references to C-5, Check 8, accessibility-overlay, Hard Constraint #8.
- `references/research_paper_writing_guidelines.md §1 Tone and voice` — new C-5 bullet with six Sub-checks summary and §3.3.3 gate reference.

## What is unchanged

- The **four-agent pipeline** (Planner, Evaluator, Generator, Reflector) is unchanged. No agent retirements, no new agents.
- The **Lifecycle-Stage Ladder** topology (T1 Plan & Draft → T2 Review & Revise → T3 Iterate & Converge → T4 Finalize & Close) is unchanged.
- The **15-field `SectionStateObject`** is unchanged. Check 8 artefacts live in `reviews/safeguard_check8_*.md`, not in the ledger.
- **MCR admission** (every section at `T3_converged`; +50% iteration reserve; climb target capped at `default_final_tier`) is unchanged in structure; Check 8 at T3 is now a terminal-row precondition but does not alter the iteration budget.
- **Monotonicity invariants** (with the three documented exemptions: `retraction`, `eg1_t4_downgrade_to_t3`, `eg7_mcr_readmission_after_class_change`) are unchanged. Trigger 28 (`t3_accessibility_blocker_surfaced`) is not a tier transition — it is a ledger-only refusal record.
- **Full-file reads at every rung** remain the universal grounding floor.
- **SD/SR opt-in gate** (`sd_sr_required` field in `reviews/classification.md`; default `false`) from v0.7.1 is unchanged.
- **Reflector dispatch split** (lightweight for T1/T2/T3 integrity probes; full for T4 close-out) is unchanged. Phase 2g runs only in full mode.
- **Grounding Protocol** rules and the Coupling E.2 graph-grounding overlay are unchanged. The new accessibility-overlay skill mirrors its structural pattern but does not replace it.
- **Release-gate phases** are unchanged.

## Migration — v0.7.1 → v0.7.2

**Absent-means-passes migration.** No migration script is required. Existing v0.7.1 projects without `reviews/safeguard_check8_*.md` artefacts see the Planner's §3.3.3 gate treat the Check 8 verdict as CLEAN — the conservative default. The gate becomes binding the first time the Evaluator runs Check 8 (via the `accessibility-overlay` skill, or directly under Step 8.5) on a given section.

**27 → 28 trigger enum.** Existing `reviews/tier_state.json` files remain valid. The new trigger 28 (`t3_accessibility_blocker_surfaced`) appears only on newly written rows after v0.7.2 lands. Trigger enum validators accept both the v0.7.1 27-value set and the v0.7.2 28-value set for back-compat.

**Evaluator T2 contract change.** Projects mid-round at T2 when v0.7.2 lands will see Check 8 enter the T2 SAFEGUARD subset on the next Evaluator dispatch. No ledger action required; the T2 Check 8 verdict is advisory on T2 admission and carries forward to T3 where it binds the §3.3.3 gate.

**Projects that want to pre-declare accessibility discipline.** A project may opt in to Check 8 enforcement earlier by appending a directive to `research_notes/directives.md`:

```markdown
- D-NN: Accessibility gate enabled from T2 (Check 8 BLOCKERs block T2 exit, not just T3 terminal).
```

This is an opt-in strictening beyond the v0.7.2 default; it is recorded as a project-scoped directive and the Planner honours it at T2 admission. The reverse (opt-out of Check 8 wholesale) is **not permitted** — C-5 cannot be suspended wholesale per `STYLE_COMMITMENTS.md §4`.

## Verification

- `scripts/release-gate.sh --probe-only` — clean (no regressions over the v0.7.1 probe-only baseline). Check 8 pre-filter output integrates cleanly with the existing `DETERMINISTIC_CHECKS §9b` consumer chain.
- Skill-count reconciliation — +1 (new `accessibility-overlay` skill). `references/SKILL_REGISTRY.md` updated.
- Contract-referent audit — `rg -n "all eight checks"` now resolves to existing Checks 1–8 across `agents/evaluator.md`, `skills/run-tier-3/SKILL.md`, and `references/DETERMINISTIC_CHECKS.md §9b`. Zero dangling "Check 7" or "Check 8" references.
- Severity-floor reconciliation — Check 8 Sub-check severity floors in `SAFEGUARD_LAYER.md` match the floors in `skills/accessibility-overlay/SKILL.md` exactly; both are consumed by the §3.3.3 gate via the same aggregation rule.
- Migration smoketest — a v0.7.1 project without any Check 8 artefacts runs `run-tier-3` end-to-end; Planner treats Check 8 verdict as CLEAN; TerminalSignoffRow writes succeed; no false refusals.

## Lessons

**A contract referenced in three places must exist at the third place.** v0.7.1 shipped `evaluator.md §Step 8.5` and `run-tier-3/SKILL.md §5` both saying "all eight checks," but `SAFEGUARD_LAYER.md` contained only six. The `DETERMINISTIC_CHECKS §9b` pre-filter fed a "Check 8 work queue" that had no consumer. Lesson: when extending a referenced count ("all N checks"), grep for every use of the count string and the referenced item across the whole package before shipping. The Reflector's Phase 2f tier-row contract audit is the template; apply it to cross-file contracts, not only to ledger rows.

**Accessibility is extraneous-load reduction, not intrinsic-load collapse.** The six Sub-checks A–F enforce prose surface properties — cadence, rhythm, definition, signposting, jargon density, worked examples. They do not enforce a reading-level ceiling or a grade-level proxy. Ph.D.-register argument in sentences averaging 28 words with high variance and clean first-use definitions is compliant. The same argument in 240-word paragraphs with nested parentheticals and undefined neologisms is not. The distinction is binding and is recorded in commitment C-5, Hard Constraint #8, and the v0.7.2 CHANGELOG so future rounds do not re-open it.

**Gate wiring costs more than check authoring.** Writing Check 7 and Check 8 in `SAFEGUARD_LAYER.md` was a single file edit. Wiring Check 8 into the T3 convergence gate required edits to `TIER_PROTOCOL.md §3.3.3`, `tier_state_schema.md` trigger enum + §6.1 + §6.2, `tier_notifications.yaml`, `agents/planner.md`, `skills/run-tier-3/SKILL.md`, and `agents/evaluator.md` — seven files for one gate. Lesson: treat any gate that couples to the TerminalSignoffRow or MCR as a cross-cutting change; plan the wiring sequence before the first edit.
