# MODEL_ALLOCATION.md — Phase-Conditioned Model Dispatch

*Package reference. Introduced at v0.7.3 under tier vocabulary; phase-named per the v0.7.4 Tier → Phase rename (this file re-voiced 2026-07-13, audit C3 — model assignments carried forward unchanged). Single source of truth for the per-phase × per-agent Claude-model mapping the Planner resolves at dispatch time. Binds the **role-to-capability** mapping to the **Lifecycle-Phase Ladder** — Ph1 Plan & Draft / Ph2 Review & Revise / Ph3 Iterate & Converge / Ph4 Finalize & Close — so that model capability tracks adversarial load rather than paragraph volume. Read this file before any invocation that spawns a subagent; the Planner reads it unconditionally at every dispatch.*

---

## 1. The intentionality behind phase-conditioned dispatch

The four-agent pipeline was designed with a separation-of-duties guarantee: the Generator is the only writer, the Evaluator never writes prose, the Reflector audits both, and the Planner dispatches but never mutates the manuscript. That contract is about *role* — what an agent is allowed to do. What it did not, until v0.7.3, say anything about, is *capability* — what model a given role should be backed by, at a given lifecycle phase, to produce the adversarial pressure the pipeline is supposed to exert. v0.7.3 closes that gap by making model capability a phase-conditioned dispatch decision that the Planner resolves from this file.

The strategic-dependency framing is that the author depends on each agent for a specific softgoal — the Evaluator for *independent scholarly integrity*, the Generator for *fluent, constraint-honouring prose*, the Reflector for *lesson retention* and *grounding audit*, the Planner for *orchestration*. Evaluator engagement at every phase, including the bounded Ph1 pass, and lesson-retention at Ph4 close-out are the slots where weak capability is the fatal failure mode, because an under-powered Evaluator or Reflector silently passes work that a stronger model would have flagged. Those slots are the non-negotiable floor below. Every other slot is sized for the work actually in scope at that phase, and the default disposition is to downshift to Sonnet 4.6 unless the slot is on the floor. Engagement is resolved from `policies/phase_engagement.v1.json`; this file resolves model capability only.

## 2. The allocation table

| Agent | Ph1 Plan & Draft | Ph2 Review & Revise | Ph3 Iterate & Converge | Ph4 Finalize & Close |
|---|---|---|---|---|
| **Planner** | Sonnet 4.6 | Sonnet 4.6 | Sonnet 4.6 | Sonnet 4.6 ↓ |
| **Evaluator** | **Opus 4.7** ★ *(bounded policy pass)* | **Opus 4.7** ★ | **Opus 4.7** ★ | **Opus 4.7** ★ |
| **Generator** | Sonnet 4.6 ↓ | Sonnet 4.6 | Sonnet 4.6 | Sonnet 4.6 ↓ |
| **Reflector** | Haiku 4.5 *(lightweight)* | Haiku 4.5 *(lightweight)* | Haiku 4.5 *(lightweight)* | **Opus 4.7** *(full)* ★ |

**Legend.** ★ = non-negotiable Opus 4.7 floor (see §3). ↓ = downshift from the naive default of "match model to role-seniority"; rationale in §4. *(bounded policy pass)* = the Ph1 centroid and all-drafts governance evaluation, not the full Ph2 review. *(lightweight)* / *(full)* = Reflector dispatch mode.

The model strings the Planner passes to the Agent tool's `model` parameter are `claude-opus-4-7`, `claude-sonnet-4-6`, and `claude-haiku-4-5-20251001` respectively. The Planner does not accept per-agent overrides in `agents/*.md` frontmatter; dispatch is resolved exclusively from this file.

## 3. The non-negotiable Opus 4.7 floor

Five slots are on the floor and will not downshift without a package-level protocol change:

- **Evaluator at Ph1.** The bounded independent current-byte policy pass is mandatory after every Generator publication. It is narrower than revision-maturity review but retains the Opus floor because it controls milestone evidence and approval readiness.
- **Evaluator at Ph2.** Ph2 begins full revision-maturity evaluation, and the pass is a full local-scope review — `REVIEW_ORCHESTRATION.md` Steps 1–3 plus the integrated checklist plus the SAFEGUARD subset (Checks 1, 4, 5, 8 in advisory mode with BLOCKER-CANDIDATE tagging). The cost of a missed finding at Ph2 compounds through every Ph3 iteration; adversarial capability here is load-bearing.
- **Evaluator at Ph3.** Ph3 is the unbounded iterate-until-stable phase; the Evaluator runs the full seven-step judgment pass, the complete SAFEGUARD layer (all nine checks), and the Coupling E.2 graph-grounding overlay at Step 0.2 on every iteration. Convergence is defined as two consecutive rounds clearing the 0.03 threshold on the declared `convergence_metric`; false convergence from a weak Evaluator is the single largest integrity hazard in the pipeline.
- **Evaluator at Ph4.** Ph4 Finalize & Close is a strict superset of Ph3 with external verifiers REQUIRED and G.4 sign-off mandatory. The cost of a missed blocker at Ph4 is submission of a defective manuscript; there is no downstream phase to catch it.
- **Reflector-full at Ph4.** The Ph4 close-out Reflector runs all five phases plus the audit blocks (Ph3 convergence audit, `[Ph3-STALE]` / MCR volatility audit, migrated confirmation-failed historical audit, Phase 2g accessibility-recurrence audit at v0.7.2, Phase 2f tier-row contract audit, the Grounding-Protocol self-audit at Phase 2.6). Plugin-update proposals filed here shape the next version of the package; weak lesson extraction at this slot would propagate to every subsequent project. Lightweight Reflector at Ph1/Ph2/Ph3 is bounded to Phases 1, 2.5, 2.6, 2f, 3 and is explicitly a memory-only integrity probe — the capability requirement there is about a narrow grounding audit, not synthesis, which is why Haiku 4.5 is acceptable on a 30-day pilot (see §5).

## 4. The downshift rationale

Three slots downshift from the naive baseline of "match model to role-seniority":

- **Generator at Ph1.** Ph1 drafting is bounded-scope prose production against the Planner-issued revision plan under the declared voice register. The Generator's authority here is full, while the required bounded independent Evaluator pass uses the Opus-class floor. Sonnet 4.6 produces constraint-honouring prose at Ph1 drafting with observable fluency; the independent pass supplies the stronger review capability. Downshift accepted for the Generator only.
- **Generator at Ph4.** The Ph4 Generator is fix-only-no-new-prose — the contract explicitly forbids new drafting at Ph4. The work is surgical application of Evaluator-surfaced blockers, not authorship. Sonnet 4.6 executes bounded edits against a detailed findings report reliably; the Opus 4.7 uplift is not earned at this slot.
- **Planner at Ph4.** The Ph4 Planner runs admission gating (MCR verification), dispatch, and artefact assembly. The adversarial work at Ph4 is concentrated in the Evaluator and Reflector-full slots; the Planner's job is orchestration and ledger discipline. Sonnet 4.6 is sufficient.

Planner at Ph1/Ph2/Ph3 remains Sonnet 4.6 by default because the Planner's work at those phases — classification, revision-plan authorship, dispatch, user-facing checkpoint presentation — is bounded-scope structured output against this file and the orchestration references. The Planner's strength at being a good Planner is not improved by Opus capability at these phases; it is improved by having *this file* to resolve dispatch against.

## 5. Named hazards

Two hazards are called out explicitly and are the subject of ongoing audit.

**Hazard H-MA-1 (capability inversion).** A round in which a Sonnet-backed Evaluator confronts Opus-backed Generator output would invert the intended adversarial pressure — the reviewer would be weaker than the writer, and the pipeline's integrity guarantee would degrade from "adversarial" to "cosmetic". This configuration is prohibited. No package-level or project-level directive may produce a round in which the Evaluator's model capability is below the Generator's on the family ordering `{Haiku 4.5} ≺ {Sonnet 4.6} ≺ {Opus 4.7}`. The Planner checks the resolved allocation at dispatch and refuses the round with `E-MA-CAPABILITY-INVERSION` if the invariant would be violated; the Reflector re-audits the resolved allocation at Phase 2f and files a finding if the Planner allowed an inversion through.

**Hazard H-MA-2 (Reflector-floor pilot).** Haiku 4.5 at the Reflector-lightweight slot is on a **30-day pilot** from the v0.7.3 release date. The capability question under test is whether Haiku 4.5 can reliably execute the grounding-audit sub-phase (Phase 2.5/2.6 read-through of revision diffs against the Grounding Protocol) and the tier-row contract audit (Phase 2f) without false-negatives. If the pilot surfaces a false-negative pattern — a grounding violation that Haiku 4.5 passed and Opus 4.7 would have caught — the Reflector itself will propose `A6-reflector-floor-uplift` to the Planner's three-filter gatekeeper, and the allocation will lift to Sonnet 4.6 at the lightweight slot. Pilot telemetry is kept in `reviews/reflection_report.md` under a new `model_dispatch_audit` block the Reflector writes on every lightweight run.

## 6. Absent-means-inherit migration semantics

Projects that predate v0.7.3 have no `model_dispatch` marker in `reviews/phase_state.json` and no entries in their `reviews/classification.md` that speak to model selection. Such projects inherit the allocation in §2 unconditionally at first Planner invocation under v0.7.3+; no migration script is required, and no user-visible ledger field is added. If a project wants to opt out of a specific slot's default — for example, to force Opus 4.7 at the Generator-Ph3 slot during a contested revision round — the opt-out is declared in `research_notes/directives.md` as a project directive, which sits at precedence level 4 in `AGENTS.md §4` and outranks this file (precedence level 5, package component). The directive syntax is:

```
D-NN: Model dispatch override — Generator-Ph3 := Opus 4.7
Justification: [project-specific reason, one paragraph]
Scope: [per-round | per-section | for duration of project]
```

The Planner reads the directive at dispatch, logs the override to `reviews/phase_state.json` in the `phase_entry_log[].notes` field as `model_override:{agent}-{phase}:={model}`, and proceeds. The Reflector Phase 2f audit verifies that every override was justified by an active directive; orphan overrides are flagged as `R-Refl-MA-3` findings.

## 7. Reflector Phase 2f audit extension

Phase 2f of the Reflector-full run (tier-row contract audit) is extended at v0.7.3 to audit model-selection consistency across the round. The three invariants checked are:

- **I-MA-1 (allocation concordance).** Every dispatch in the round's `phase_state.json` `phase_entry_log` array resolves to an `actor` and trigger consistent with §2. A Ph1 Evaluator row is valid only for the bounded all-drafts policy pass and must bind the target and current artifact hash; broader Ph1 Evaluator work remains scope drift.
- **I-MA-2 (capability non-inversion).** No round in the log shows the Evaluator downshifted below the Generator on the family ordering `{Haiku 4.5} ≺ {Sonnet 4.6} ≺ {Opus 4.7}`. Violations are `R-Refl-MA-1` with BLOCKER severity.
- **I-MA-3 (override provenance).** Every `model_override:...` notes-field entry corresponds to an active directive in `research_notes/directives.md`. Orphan overrides are `R-Refl-MA-3` with MAJOR severity.

Findings from the Phase 2f model-selection audit are appended to the same `reviews/reflection_report.md` block the pilot telemetry lives in (§5), under a `model_dispatch_audit` heading, and feed the three-filter gatekeeper for any `A6-reflector-floor-uplift` or related plugin-update proposals.

## 8. Deprecation and forward compatibility

Opus 4.6 is deprecating and is not in the allocation. Any project directive that hard-codes `claude-opus-4-6` will be rejected at dispatch with `E-MA-DEPRECATED-MODEL`; the Planner will prompt the user to choose between Opus 4.7 (capability-equivalent forward) and Sonnet 4.6 (cost-efficient alternative). The model strings the Planner passes are documented in §2; these strings are the contract surface, and any future model family release (e.g., a Fable/Mythos-class model) will require a package version bump with updated allocation and updated capability-ordering in §5. *(Known deferred item, recorded at v0.25.0: the advisor plane moved to `claude-fable-5`; this subagent-dispatch plane deliberately did not — migrating it requires re-validating the capability ordering and the `E-MA-DEPRECATED-MODEL` list in its own cycle.)*

**Rename history.** The v0.7.4 Tier → Phase rename applied to this file: the identifiers in §2 are phase-named (T1–T4 → Ph1–Ph4), and model assignments carried forward unchanged, as the v0.7.3 edition anticipated. The ledger-side rename was handled by `migrate_v073_to_v074_tier_to_phase.py` *(script retired from the tree)*.

---

*Normative status.* This file is at precedence level 5 (package component) per `AGENTS.md §4`. Project directives (level 4) override this file; venue and advisor instructions (levels 2 and 3) override both; the user's explicit instruction in the current conversation (level 1) is supreme. `GROUNDING_PROTOCOL.md` sits outside the ladder and is absolute — no model dispatch decision licenses a grounding violation.
