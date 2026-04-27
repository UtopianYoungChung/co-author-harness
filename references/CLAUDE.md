# Package CLAUDE.md — Invocation Rules

**Scope.** This file governs how Claude (or any agent) invokes the **Research and Academic Paper Writing Package** when asked to review, edit, or critique a piece of academic writing. It sits **inside** the package folder and describes how the package is used; the **content rules themselves** live in the component files.

**Deployment.** Two common layouts: (1) **Embedded** — this content lives under `.paper-package/` (or equivalent) inside a Research tree; the Research-root `CLAUDE.md` delegates here. (2) **Plugin root** — this `references/` folder sits under the published plugin workspace (for example `co-author-harness/`); treat `${CLAUDE_PLUGIN_ROOT}` as that plugin root and resolve paths from there. Use the layout you actually opened; do not assume `.paper-package/` exists if you are already at the plugin root.

**Lifecycle scope.** This package governs the **full research lifecycle** — from project bootstrapping (M1) through final submission (M5). Pre-drafting milestones (M1–M3) are dispatched via `AGENT_ORCHESTRATION.md §10`; drafting and revision (M4–M5) follow the standard four-agent loop in §3.

**Lifecycle-Phase Ladder (v0.7.4).** From v0.6.0 onward, per-section advancement is arbitrated by the **Lifecycle-Phase Ladder** — **Ph1 Plan & Draft → Ph2 Review & Revise → Ph3 Iterate & Converge → Ph4 Finalize & Close** — defined in `PHASE_PROTOCOL.md` (renamed from `TIER_PROTOCOL.md` at v0.7.4) and governed by a per-section ledger at `reviews/phase_state.json` (15-field `SectionStateObject`, 7-field log row, 30-trigger enum). The M1–M5 narrative remains the lifecycle framing for project bootstrap and pre-drafting work; the Ph1–Ph4 ladder is the review-and-edit arbitration surface. The two are compatible (M1+M2+M3 absorbed at Ph1; M4a at Ph2; M4b at Ph3; M5 at Ph4). Ph4 admission is gated by the **Manuscript Convergence Report (MCR)**: every section must reach `current_phase: Ph3_converged` and no section may carry a computed `[Ph3-STALE]` flag. Agent engagement is phase-conditioned: Evaluator dormant at Ph1, joins at Ph2, full four-agent loop at Ph3/Ph4. The four-agent contract, the Grounding Protocol, and the SD/SR opt-in gate (`sd_sr_required: false` by default, v0.7.1) are unchanged.

---

## 1. When this package is invoked

The agent uses this package whenever:

- The user asks for a review, edit, critique, or refinement of a manuscript, response letter, thesis chapter, course essay, abstract, or any other academic prose.
- The user refers to "the master guidelines," "the style package," "the master writing rules," or uses a slash-style shorthand.
- The user pastes an academic draft and asks for feedback.
- The user asks for a "joint review" or "comprehensive review" of a piece.
- The user asks to **bootstrap a new research project** (set up folder, start a project, create the structure).
- The user asks about **project lifecycle or milestones** (where is this project, what milestone, what's next).
- The user asks to **assess improvement or readiness** (is it ready, how much better, show me the metrics).

The parent CLAUDE.md files already require this package for all such work. This file picks up from there.

**Agent mode.** When the user asks to "run the planner," "evaluate the manuscript," "co-author §6," "reflect on this round," or otherwise invokes a specific agent role, read `AGENT_ORCHESTRATION.md` first. It defines the four-agent system (Planner, Evaluator, Generator, Reflector) and the dispatch loop. Each agent's full prompt is in `agents/<role>.md`.

---

## 2. First step on every invocation: read the orchestration files

- **Before anything else (every invocation):** Read `ROUTING_SPINE.md`. It is the intent-to-phase dispatch table (Think → Plan → Build → Review → Test → Ship → Reflect) and defines the exit gates for each phase. Every user utterance is assigned to a phase here before any agent is dispatched.
- **For per-section ladder advancement (v0.6.0+):** Read `PHASE_PROTOCOL.md`. It defines the Ph1 → Ph2 → Ph3 → Ph4 ladder, the 15-field `SectionStateObject` schema at `reviews/phase_state.json`, the 30-trigger enum, the three monotonicity exemptions (`retraction`, `eg1_ph4_downgrade_to_ph3`, `eg7_mcr_readmission_after_class_change`), and the Ph3 stability sub-mode admission gate (`§3.3.2`, v0.7.4). Used by the Planner on every phase-advance decision.
- **For Planner-to-subagent dispatch capability (v0.7.3+):** Read `MODEL_ALLOCATION.md`. It defines the phase-conditioned Claude-model mapping (renamed from tier-conditioned at v0.7.4). Non-negotiable Opus 4.7 floor at Evaluator-Ph2/Ph3/Ph4 and Reflector-full-Ph4; Planner refuses capability inversion with `E-MA-CAPABILITY-INVERSION`.
- **For Evaluator / Reflector artefact authoring (v0.7.4+):** Read `ARTEFACT_FRONTMATTER_SCHEMA.md`. It defines the six artefact frontmatter families — **F1** `evaluator_findings`, **F2** `evaluator_deterministic`, **F3** `reflector_lightweight_probe`, **F4** `reflector_full_report`, **F5** `planner_consolidated_findings`, **F6** `planner_dispatch_plan` (P-1 round-scoped dispatch plan). Validator at `scripts/artefact_frontmatter_validate.py`.
- **For agent obligations (reference):** Read `AGENT_CONTRACTS.md` for the per-agent I/O contracts (preconditions, inputs, outputs, invariants, done criteria). The contracts sit alongside the prose prompts in `agents/<role>.md` and win on obligations. At v0.7.4 the file carries invariants I-Planner-5 through I-Planner-10, I-Eval-6, I-Gen-6, I-Refl-6, and I-SubAgent-1/2/3 (subagent verdicts authoritative-as-read; dispatching agent may not re-adjudicate).
- **For concurrent work (multi-project / parallel phases):** Read `PARALLEL_CONDUCTOR.md`. It defines the four concurrency levels (L0–L3), the `conductor.md` ledger at the Research root, and the session-handoff protocol.
- **For a review, edit, or critique:** Read `REVIEW_ORCHESTRATION.md`. It is the runbook for the review pipeline.
- **For an agent-dispatched task:** Read `AGENT_ORCHESTRATION.md`. It is the runbook for the four-agent loop.
- **For both:** Start with `AGENT_ORCHESTRATION.md` (which dispatches agents that then follow `REVIEW_ORCHESTRATION.md` for the review steps).
- **For bootstrapping a new project:** Read `PROJECT_BOOTSTRAP.md`. It defines the directory template and setup procedure.
- **For a long manuscript (> 8,000 words):** Read `TOKEN_BUDGET_PROTOCOL.md`. It defines segmentation and context management.
- **For assessing improvement or readiness:** Read `SUCCESS_METRICS.md`. It defines the six-dimension quality framework (D1–D6).
- **Before any cited claim is finalised at submission-bound depth:** Read `EXTERNAL_VERIFIERS.md`.
- **Before applying or flagging a prose-craft / narrative / theory-shape rule:** Read `STYLE_COMMITMENTS.md` to determine whether the relevant commitment (C-1…C-4) is in force for this piece.

`REVIEW_ORCHESTRATION.md` (in this folder) is the **entry point**. It defines:

- How to classify the piece (paper type + P-stage + review depth).
- Which component files apply at that classification.
- What to read and what to emit at each step.
- The findings report format used to synthesize the seven-step pass.
- When to run `DETERMINISTIC_CHECKS.md` vs. the full pass.

**Do not skip it.** Even for "small" edits the orchestration file tells you which subset of files to consult. Reading the MASTER is not a substitute — the MASTER is a reference map; orchestration is the runbook.

---

## 3. Components of this package

| # | File | Role | When it's authoritative |
|---|------|------|-------------------------|
| 0 | `MASTER_research_and_paper_guidelines.md` | Synthesis + traceability + Parts A–J reference | When you need the consolidated view or the traceability matrix |
| 1 | `REVIEW_ORCHESTRATION.md` | Runbook: classification, per-step protocol, findings format, overlap map | Always read first |
| 2 | `DETERMINISTIC_CHECKS.md` | Mechanical grep/count rules runnable before judgment-based review | Run first on any piece with prose; re-run after fixes |
| 3 | `general_research_project_guidelines.md` | Five-milestone project arc (pre-drafting lifecycle) | Early-stage work, memo-to-draft planning |
| 4 | `research_paper_writing_guidelines.md` | Cross-venue playbook for tone, claims, theory, audience, structure | Mid-draft review and revision |
| 5 | `baird_2021_writing_guidelines.md` | IS theory / empirical paper shape; 5-element model; 9-step process | IS-venue work (JAIS, MISQ, ISR, ICIS, ECIS, HICSS) |
| 6 | `bacon_2009_well_crafted_sentence_guidelines.md` | Sentence-level craft by chapter; revision checklist | Line-edit and prose-polish passes |
| 7 | `Sexton_Fiction_to_Academic_Writing_Guide.md` | Narrative arc, openings, show-don't-tell, cause-effect | Structural review and opening/closing work |
| 8 | `project_writing_style_checklist.md` | Integrated checklist with P0/P1/P2 stages and severity tags | The final synthesis pass catches overlaps |
| 9 | `SAFEGUARD_LAYER.md` | Post-review integrity: regression, drift, consistency, contradictions, traceability, voice | Step 8.5 — runs after the consolidated report, before author approval |
| 9a | `GROUNDING_PROTOCOL.md` | **Binding** no-hallucination rules: read-before-cite, compute-before-report, verify-before-reference, quote-before-attribute, mark-uncertainty, no-gap-filling | Cannot be overridden by any instruction; enforced by Reflector every round |
| 9b | `GROUND_TRUTH.md` | Canonical definition source registration: the EYgp *Research Process and Artifacts* workbook (`references/EYgp_Research_process_and_artifacts.xlsx`) is registered as ground truth for all P / R / K / S / T / V axis stages and the readiness-tick scale. Verbatim Markdown extract at `references/EYgp_Research_process_and_artifacts.md`. | Read whenever a package file, skill, or agent output cites an axis stage (P0/P1/P2, R0–R2, K0–K2, S1–S5, T1–T5, V0–V5) or a readiness band. Workbook wins on definitional questions. |
| 10 | `AGENT_ORCHESTRATION.md` | Four-agent architecture: Planner, Evaluator, Generator, Reflector | Read when dispatching agents or running the full loop |
| 11 | `agents/planner.md` | Planner agent prompt: classify, plan, dispatch, keep user in the loop | Read by the session or parent agent acting as Planner |
| 12 | `agents/evaluator.md` | Evaluator agent prompt: review pipeline, findings, safeguard checks | Read by the Evaluator subagent |
| 13 | `agents/generator.md` | Generator agent prompt: write prose, apply fixes, self-check | Read by the Generator subagent |
| 14 | `agents/reflector.md` | Reflector agent prompt: extract lessons, update memory, propose improvements | Read by the Reflector subagent |
| 15 | `examples/*.md` | Worked walkthroughs of past reviews | Reference for how to compose findings |
| 16 | `RESEARCH_ROOT_CLAUDE.md` | Root-level CLAUDE.md for the Research folder — delegation, lifecycle governance, cross-project rules | Deploy to Research root; read when setting up the harness |
| 17 | `PROJECT_BOOTSTRAP.md` | Directory template, seed files, bootstrap procedure for new projects | Read when starting a new project (M1) or importing an existing draft |
| 18 | `TOKEN_BUDGET_PROTOCOL.md` | Context/token management: size classes, segmentation, state preservation, rule-loading priority | Read when manuscript exceeds 8,000 words or context limits are hit |
| 19 | `SUCCESS_METRICS.md` | Six-dimension quality framework: D1 Defect Density, D2 Structural Integrity, D3 Prose Craft, D4 Theoretical Adequacy, D5 Lifecycle Progress, D6 Operating Cost | Read by Reflector for dashboard; by Planner/Evaluator for readiness assessment |
| 20 | `EXTERNAL_VERIFIERS.md` | External verification requirement and verifier classes; resolves the bootstrapping paradox (single-agent self-verification) at submission-bound depth | Read by Evaluator/Reflector before any cited claim is finalised at submission-bound depth |
| 21 | `EVAL_METHODOLOGY.md` | Skill-benchmark disclosure standard; reclassifies undisclosed scores as Internal-Confidence Indicators (ICI) until methodology is documented | Read whenever a `SKILL_REGISTRY.md` benchmark is cited as evidence |
| 22 | `DRIFT_CHECK.md` | MASTER / component reconciliation gate; categorises Quote / Claim / Structural drift; hard gate before G.4 sign-off | Run by Reflector at Phase 2.6 of every round |
| 23 | `REFLEXIVITY_CHECK.md` | Authorship identity instrumentation; per-round substitution-vs-augmentation audit; trajectory log | Run by Reflector at Phase 2.7; mandatory at submission-bound depth |
| 24 | `STYLE_COMMITMENTS.md` | Declares Suchman / Bacon / Sexton / Baird as named methodological commitments (C-1…C-4) rather than universal hygiene; defines relaxation procedure | Read by Planner at classification; cited by Generator/Evaluator when applying or flagging stylistic rules |
| 25 | `ROUTING_SPINE.md` | Phase-based intent dispatch (Think→Plan→Build→Review→Test→Ship→Reflect) mapped to M1–M5; per-phase exit gates; dispatch table for user utterances | **Read first on every invocation.** Sits above `AGENT_ORCHESTRATION.md` on phase boundaries; orchestration wins on agent mechanics |
| 26 | `AGENT_CONTRACTS.md` | Per-agent declarative contracts: preconditions, inputs, outputs, invariants, done criteria, failure modes | Read with `agents/<role>.md`; contracts win on obligations, prompts win on method |
| 27 | `PARALLEL_CONDUCTOR.md` | Concurrency model (L0–L3), `conductor.md` ledger format, session handoff protocol, multi-project isolation rules | Read when managing multiple projects or when the session ends mid-round |
| 28 | `QUICKSTART.md` | One-page operational primer: the one rule, session-opening ritual, seven-phase invocation table, three failure modes, power-user shortcuts | Read by a new user or when a corrective utterance is needed mid-session |
| 29 | `OPERATING_MANUAL.md` | Full runbook: pre-requisites, session contract, seven phases in operational detail, canonical round, recovery procedures, reading the artifacts, sustainment habits | Read when inheriting the package cold or when diagnosing a failure mode |
| 30 | `PHASE_PROTOCOL.md` *(renamed from `TIER_PROTOCOL.md` at v0.7.4)* | Lifecycle-Phase Ladder: Ph1 Plan & Draft → Ph2 Review & Revise → Ph3 Iterate & Converge → Ph4 Finalize & Close. `§3.3.2` Ph3 stability sub-mode admission gate (P-2); `§3.3.3` Check 8 accessibility convergence gate (Reader-Experience defence, v0.7.2); `§6.*` `reviews/phase_state.json` schema (15-field `SectionStateObject`, 7-field log row, 30-trigger enum). Optional **Advisor MCP** entry points EP-1 / EP-2: `ADVISOR_MCP.md`. | Read by Planner on every phase-advance decision; by Evaluator on scope-budget resolution; by Reflector Phase 2f on tier-row contract audit |
| 31 | `ADVISOR_MCP.md` | Advisor MCP: co-author-harness plugin exposes `/advisor-escalation`; host connects the **advisor** MCP server (`consult_advisor`). EP-1 = post-Ph2 pre-Ph3; EP-2 = post-Ph3_converged pre-MCR/Ph4. Auditable `reviews/advisor_consultation_*.md`; not a substitute for `EXTERNAL_VERIFIERS` or ladder approval. | Read when scheduling external feedback or submission-defensibility consultations |
| 32 | `ARTEFACT_FRONTMATTER_SCHEMA.md` *(new at v0.7.4, P-3a)* | Six artefact frontmatter families — F1 `evaluator_findings`, F2 `evaluator_deterministic`, F3 `reflector_lightweight_probe`, F4 `reflector_full_report`, F5 `planner_consolidated_findings`, F6 `planner_dispatch_plan` (P-1). F6 is not inherited under P-2 stability rounds. Family-aware validator at `scripts/artefact_frontmatter_validate.py` | Read by Evaluator and Reflector when authoring artefacts; by Planner when reading frontmatter (instead of re-parsing prose bodies); by Reflector Phase 2f for contract audit |
| 33 | `MODEL_ALLOCATION.md` *(new at v0.7.3; slot names renamed Ph1–Ph4 at v0.7.4)* | Phase-conditioned Claude-model mapping per agent × phase slot. `§2` the allocation table; `§3` the four-slot non-negotiable Opus 4.7 floor (Evaluator-Ph2/Ph3/Ph4, Reflector-full-Ph4); `§4` downshift rationales; `§5` hazards H-MA-1 (capability inversion) and H-MA-2 (Reflector-floor pilot); `§7` Reflector Phase 2f audit with invariants I-MA-1/2/3 | Read by Planner at every dispatch (Phase 4.5); by Reflector at Phase 2f close-out; authoritative source — `AGENT_ORCHESTRATION.md §3.0` is a read-only mirror |
| 34 | `phase_notifications.yaml` *(authoritative; `references/tier_notifications.yaml` is a v0.7.4–minor deprecated stub that forwards to this file)* | Centralised notification templates for user-facing ledger transitions; §9 carries the v0.7.4 P-2 stability sub-mode notification templates (`stability_mode_proposed`, `stability_mode_admitted`, `stability_mode_escalated`, `stability_mode_drop_through`, `stability_mode_refused_at_ph4_admission`) | Read by Planner when rendering checkpoint notifications |
| SK-30 | `skills/accessibility-overlay/SKILL.md` *(new at v0.7.2)* | Overlay skill producing SAFEGUARD Check 8 findings from the §13 reader-accessibility criteria (Cadence-Flag, Rhythm-Flag, First-Use-Flag, Signpost-Flag, Jargon-Density-Flag, Worked-Example-Flag). Gates Ph3 `TerminalSignoffRow` per `PHASE_PROTOCOL.md §3.3.3` | Dispatched by Evaluator at Ph2 (advisory subset), Ph3 (binding at signoff), Ph4 (CLEAN required) |
| SK-31 | `skills/run-phase-3-stability/SKILL.md` *(new at v0.7.4, P-2)* | Ph3 stability sub-mode: reduced-envelope pass on a byte-stable manuscript (S-0 SHA-256 hash-match admission gate on F1/F2/F3/F5 substrate). Runs grounding audit + Check 8 deterministic pre-filter only; skips Evaluator seven-step judgment and full SAFEGUARD; escalates to full Ph3 via trigger 30 on any finding | Dispatched by Planner at Phase 5.5 when S-0 precondition holds; downstream-excludes SK-30 under the reduced envelope |

Files 3–8 correspond to Steps 1–7 in MASTER's §Policy full-package pass. Files 0–2 and 9 are meta-infrastructure. Files 16–19 are harness infrastructure added to support full-lifecycle governance. Files 20–24 are the 2026-04-13 tightening-pass additions that close the gaps identified in `wiki/syntheses/paper-package-evaluation-2026-04-13.md`. Files 25–27 are the 2026-04-13 gstack-adaptation additions: an explicit phase spine (`ROUTING_SPINE.md`), per-agent obligation contracts (`AGENT_CONTRACTS.md`), and multi-project concurrency governance (`PARALLEL_CONDUCTOR.md`), adapting the `gstack` Think→Plan→Build→Review→Test→Ship→Reflect workflow to the academic-writing context. **Files 30–34 plus SK-30/SK-31** are the v0.6.0 → v0.7.4 ladder / allocation / frontmatter / accessibility / stability additions, plus `ADVISOR_MCP.md` (Advisor MCP entry points at file 31): the Lifecycle-Phase Ladder schema (`PHASE_PROTOCOL.md`), Advisor MCP external-feedback bridge (`ADVISOR_MCP.md`), the artefact-frontmatter contract (`ARTEFACT_FRONTMATTER_SCHEMA.md`, v0.7.4 P-3), the phase-conditioned model allocation (`MODEL_ALLOCATION.md`, v0.7.3), the centralised notification templates (`phase_notifications.yaml`), the Reader-Experience overlay (SK-30, v0.7.2), and the Ph3 stability sub-mode skill (SK-31, v0.7.4 P-2).

**Autoresearch-inspired concepts (2026-04-13).** Six enhancements adapted from Karpathy's autoresearch project (autonomous ML experimentation) are distributed across the existing files rather than creating new files: (1) **Primary gate metrics** — each phase has a single indicator checked first (`ROUTING_SPINE.md` §3); (2) **Scope budgets** — each agent has an explicit dispatch ceiling (`AGENT_CONTRACTS.md` §§1–4); (3) **Round program** — a user-authored `round_program.md` at the project level declares per-round focus, scope, and success criteria (`AGENT_ORCHESTRATION.md` §8.2, `PROJECT_BOOTSTRAP.md` §2.10); (4) **Retain/Revert Protocol** — per-edit keep/discard decision after Evaluator re-check (`AGENT_ORCHESTRATION.md` §7); (5) **Structured experiment logging** — hypothesis→change→result→verdict format for `revision_log.md` (`AGENT_CONTRACTS.md` §3, `PROJECT_BOOTSTRAP.md` §2.4); (6) **Three-layer architecture** — immutable/experimental/control layers named explicitly (`AGENT_ORCHESTRATION.md` §8.1). All four agent prompts (`agents/*.md`) updated to reference these concepts. `SUCCESS_METRICS.md` §8 added to acknowledge per-edit metric comparison.

**Graphify coupling (2026-04-16).** One enhancement — **Coupling E.2** — extends the package with a graph-overlay hook that fires in the Evaluator pre-flight (between Step 0a and Step 1). The hook is materialized by SK-20 `graph-grounding-overlay` (`skills/graph-grounding-overlay.md`), which reads the peer `LLM wiki/graphify-out/graph.json` + `GRAPH_REPORT.md` produced by the external graphify toolchain and emits up to three finding types (graph-stub citations, section-location mismatches, missing-citation candidates) into `reviews/graph_overlay_YYYY-MM-DD.md` as pre-flight input to the Evaluator's judgment pass. Uncertainty is preserved via graph-specific source tags (`[source: graph-extracted]` / `[source: graph-inferred]` / `[source: graph-stub]`) and audited by `grounding-audit` Category 8. Activation is opt-in: a project's CLAUDE.md must declare `coupling_e_on_review: true` alongside `wiki_linked: true` (see `PROJECT_BOOTSTRAP.md §3 Step 5`). Firing is conditional on graph freshness (Precondition 3 in SK-20); stale graphs no-op rather than feed outdated findings. Orchestration hook: `AGENT_ORCHESTRATION.md §8.6`. Sibling couplings: A-revised (SK-15), B (SK-16), C (SK-14), D (SK-17). Planned successors (not in v0.3.1): SK-19 `graph-read-at-planner` for Coupling E.1 (M1-timed) and SK-21 `graph-contradiction-sweep` for Coupling E.3 (contradiction-sweep extension).

---

## 4. Precedence rules (conflict resolution)

When two sources disagree:

1. **User's explicit instruction in the current conversation** wins over everything else in this list.
2. **Venue author guide / call for papers / publisher template** wins over the package.
3. **Advisor or instructor instruction** wins over the package.
4. **Project-specific supplements** (e.g. `CAiSE_Rev01/research_notes/review/lessons_caise_revision.md`) win **within their project** over the package's cross-venue rules.
5. **Component files** win over the MASTER until the MASTER is reconciled (per MASTER §Policy).
6. **MASTER** wins over the orchestration and deterministic-checks files when a rule is in dispute (since MASTER carries the traceability matrix).
7. Default behavior.

When in doubt, name the conflict in the findings report and ask the user.

---

## 5. Do not skip steps

- **Even "small" revisions invoke the orchestration file.** Small revisions are where violations arrive most often (this is an observed pattern, not a theoretical worry).
- **Even if you remember the rules,** read the component file you're citing. Rules evolve; memory drifts.
- **Even if the piece looks "fine,"** run `DETERMINISTIC_CHECKS.md` once. It takes a minute and catches the measurable tics.

---

## 6. What this file is NOT

- **Not** a rule source. Rules live in the component files.
- **Not** project-specific. Project-specific guidance lives in the parent CLAUDE.md files and in project `research_notes/` folders.
- **Not** a substitute for reading the orchestration file.

