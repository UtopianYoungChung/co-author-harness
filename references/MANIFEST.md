# MANIFEST.md — references/ Routing Index

**Status.** This file is an **index, not an authority layer.** It indexes the principal reference files under `references/` (style-substrate guideline files, templates, resources, and examples may be unlisted; the index is not a completeness guarantee) plus the `agents/` and native `skills/` surfaces an invocation typically consults, and routes the reader by task to the correct file. The **rules themselves** live in those files; MANIFEST.md has no normative content of its own.

**Why this file exists.** Before v0.15.0-pre PR-4b, `references/CLAUDE.md §2` enumerated ~13 inline "Before X, read Y" routes that every agent loaded eagerly on every invocation. PR-4b moves that catalog here and slims CLAUDE.md to a small precedence + invocation surface. Agents consult MANIFEST when they need to know which reference applies; they do not read every file in this list.

**Authority precedence is unchanged** — see `CLAUDE.md §4`. The Grounding Protocol still wins over everything below user instruction. MANIFEST does not alter that ladder.

---

## 1. The always-loaded floor

Two files are read unconditionally on every invocation:

- `GROUNDING_PROTOCOL.md` — **binding** no-hallucination rules; cannot be overridden by any instruction. Always full-file read (the phase-gated digest exception was retired at v0.7.4).
- `CLAUDE.md` (this folder) — invocation rules, precedence ladder, do-not-skip reminders. ~70 lines after the PR-4b slim.

Everything else is on-demand per the routing table below.

Assignment writer transaction entry points are `scripts/assignment_process_gate.py` (READY emission and read-only verification), `scripts/assignment_dispatch_preflight.py` (Planner reservation), `scripts/assignment_writer_commit.py` (journaled live-path publication plus hash-chained mutation row), `scripts/assignment_mutation_check.py` (live postimage verification), `scripts/assignment_receipt_invalidate.py` (explicit cancellation), and `scripts/assignment_receipt_recover.py` (inspected stale-claim recovery). State and target coordination is centralized in `scripts/assignment_receipt_transaction.py`; Planner M1-M4 and public FINAL/M5 derivation, begin, record, approval/F9 acceptance, terminal close, and inspected recovery use the single public `scripts/assignment_milestone_checkpoint.py` surface backed by `scripts/assignment_milestone_transaction.py`.

---

## 2. Routing by task

| If your task is… | Read these before acting |
|---|---|
| **Any academic draft, review, edit, critique, or refinement** | Resolve `policies/draft_governance.v1.json`; run `scripts/draft_governance.py` and `/centroid-pass` for both generation and independent evaluation; invoke canonical `scripts/audit/run_all.py --project-root ... --phase PhN` for D-STYLE and deterministic evidence |
| **Per-section phase advancement (Ph1 → Ph4)** | `ASSIGNMENT_MILESTONE_PROCESS.md` (pre-draft source/function gate); `PHASE_PROTOCOL.md`; `phase_state_schema.md` (incl. §2.2 stage/profile shadow fields at PR-3b.1); `MILESTONE_FEEDBACK_HANDOFF_PROTOCOL.md` (pre-transition milestone gates) |
| **Project lifecycle, milestones, feedback, approval, or handoffs** | `ASSIGNMENT_MILESTONE_PROCESS.md`; bound profile under `policies/`; assignment receipt/checkpoint/approval/terminal-evidence schemas; `MILESTONE_FEEDBACK_HANDOFF_PROTOCOL.md`; `AGENT_ORCHESTRATION.md` §10; derive/begin/record/accept with `assignment_milestone_checkpoint.py` (public `FINAL` maps to M5), use the scoped writer transaction for deliverable bytes, and use the matching explicit recovery command when required |
| **Dispatching subagents** | `AGENT_ORCHESTRATION.md` (loop); `MODEL_ALLOCATION.md` (Opus-floor invariants); `AGENT_CONTRACTS.md` (per-agent obligations); `agents/<role>.md` (the role's full prompt) |
| **Authoring Evaluator / Reflector artefacts** | `ARTEFACT_FRONTMATTER_SCHEMA.md` (F1–F8 families); `OUTPUT_ECONOMY_PROTOCOL.md` (default outputs, evidence packets, escalations) |
| **Bootstrapping a new project** | `PROJECT_BOOTSTRAP.md`; `RESEARCH_ROOT_CLAUDE.md` (root-level governance); for assignment-bound projects, resolve the project-local assignment contract before first `/run-draft` |
| **Concurrent work across projects / phases** | `PARALLEL_CONDUCTOR.md` (L0–L3 concurrency, conductor.md ledger, handoff) |
| **Long manuscript (> 8,000 words)** | `TOKEN_BUDGET_PROTOCOL.md` (segmentation + state preservation) |
| **Assessing improvement / readiness** | `SUCCESS_METRICS.md` (D1–D6 quality framework) |
| **Submission-bound depth (cited claims must be externally verifiable)** | `EXTERNAL_VERIFIERS.md`; `ADVISOR_MCP.md` (EP-1/EP-2 escalation points) |
| **Applying / flagging a prose-craft or theory-shape rule** | `STYLE_COMMITMENTS.md` (C-1 Suchman / C-2 Bacon / C-3 Sexton / C-4 Baird in-force test; C-5 reader-accessibility always-on; C-6 rhetorical–analytical separation / scoped metaphor; C-7 voice-fingerprint preservation; C-8 analytic-construction discipline — `analytic_construction_guidelines.md`, standalone skill `analytic-move-audit`); the named source file for C-N |
| **Building, extending, formalizing, or auditing a BFO-aligned ontology** | `BFO_ONTOLOGY_DESIGN.md` (conditional trigger boundary, construction loop, terminology, definition, taxonomy, provenance, validation, BFO conformance profile, relation discipline, lifecycle/versioning, and blocking release gate) |
| **Generator writing prose** | `EMDASH_BUNDLE_DISCIPLINE.md` (binding B1/B2/B3 bundle); `CITATION_DISCIPLINE.md` (term-of-art two-question test) |
| **Reflector post-round** | `DRIFT_CHECK.md` (Phase 2.6 MASTER/component reconciliation); `REFLEXIVITY_CHECK.md` (Phase 2.7 authorship-identity audit) |
| **Skill-benchmark evidence** | `EVAL_METHODOLOGY.md` (disclosure standard; undisclosed scores reclassify as ICI) |
| **Research-process axis questions** | `GROUND_TRUTH.md` (package convention and exact-source boundary); project-local source when exact advisor-specific conformance is requested |
| **First-time orientation / cold inheritance / mid-session correction** | `QUICKSTART.md`; `OPERATING_MANUAL.md` (full runbook) |

---

## 3. Component inventory

Files in `references/`, grouped by role. The "When authoritative" column is the conditional under which the file is binding — outside that condition, treat the file as background reference.

### Meta-infrastructure

| File | Role | When authoritative |
|---|---|---|
| `MASTER_research_and_paper_guidelines.md` | Parts A–J reference + traceability matrix | When you need the consolidated cross-venue view |
| `REVIEW_ORCHESTRATION.md` | Review runbook: classification, per-step protocol, findings format | Always read first for review/edit work |
| `DETERMINISTIC_CHECKS.md` | Mechanical rule rationale (the runtime is `scripts/audit/`, not this file, since PR-2) | When you need to understand a finding's basis |
| `OPERATING_MANUAL.md` | Full runbook: pre-requisites, session contract, seven phases, recovery, sustainment | Cold inheritance or failure diagnosis |
| `QUICKSTART.md` | One-page operational primer | New user or mid-session correction |
| `ROUTING_SPINE.md` | Derived intent routing into canonical milestone and lifecycle contracts | Read when arbitrating user intent; never treat its seven labels as persisted state |

### Binding constraints (cannot be overridden by agent instructions)

| File | Role | When authoritative |
|---|---|---|
| `GROUNDING_PROTOCOL.md` | No-hallucination rules — read-before-cite, compute-before-report, verify-before-reference, quote-before-attribute, mark-uncertainty, no-gap-filling | Always; enforced by Reflector every round; stable `<a id="gp-N"></a>` anchors at every rule (PR-3a); deterministic citation resolver at `scripts/audit/audit_citations.py` (PR-4a) |
| `EMDASH_BUNDLE_DISCIPLINE.md` | AI-tell removal bundle B1/B2/B3 — em-dash overuse, negative parallelism, triadic-list repetition | Every Generator prose action; waiver requires explicit per-session user instruction |
| `CITATION_DISCIPLINE.md` | Two-question test at term-of-art invocations: engagement-cite vs. demarcation-no-cite | Every citation-bearing prose action; consulted by Evaluator at Step 4 and Sub-check H |
| `GROUND_TRUTH.md` | Package-authored operational interpretation of P/R/K/S/T/V labels; explicitly not exact EYgp conformance | Package routing by research-process stage; exact advisor-specific checks require a project-local source |

### Lifecycle and orchestration

| File | Role | When authoritative |
|---|---|---|
| `PHASE_PROTOCOL.md` (renamed from `TIER_PROTOCOL.md` at v0.7.4) | Lifecycle-Phase Ladder Ph1–Ph4; `§3.3.2` stability sub-mode; `§3.3.3` Check 8 accessibility gate; `§6.*` `phase_state.json` schema | Every phase-advance decision; v0.15.0-pre PR-3b.1 added optional `stage`/`profile` shadow fields |
| `ASSIGNMENT_MILESTONE_PROCESS.md` + `policies/course_essay_milestones.v1.json` + `schemas/assignment_gate_receipt.schema.json` + `templates/assignment_gate_receipt.json` + assignment checkpoint/approval/M4-acceptance/terminal-evidence schemas and templates | Source-bound assignment intake; executable native M1→M4→FINAL checkpoint walk; immutable scoped-writer receipt; exact path/mode reservations; recoverable publication; explicit approval; converged current-policy binding; state-last F9/lifecycle transactions; distinct final manuscript/export and transactional terminal close | Before every drafting dispatch and milestone decision; `scripts/assignment_process_gate.py`, `scripts/assignment_dispatch_preflight.py`, `scripts/assignment_writer_commit.py`, `scripts/assignment_receipt_invalidate.py`, and `scripts/assignment_receipt_recover.py` own scoped deliverable publication; `scripts/assignment_milestone_checkpoint.py` owns derive/begin/record/accept including FINAL/M5 close |
| `MILESTONE_FEEDBACK_HANDOFF_PROTOCOL.md` | Canonical M1-M5 deliverable, feedback, adjudication, lineage, approval, reopening, handoff, migration, and gate-outcome contract | Every project milestone decision and every M1-M5 handoff |
| `templates/milestone_event.json` | Authoring shape for one append-only milestone event inside `phase_state.json` | Planner milestone transaction writes and event-contract tests |
| `phase_state_schema.md` | Normative `phase_state.json` schema; §2.2 documents PR-3b.1 stage/profile + PR-3b.2 MCR convergence-evidence advisory | Planner writes; every other agent reads |
| `schemas/f7_evidence_packet.schema.json` | JSON Schema for F7 evidence packets (consumed by `ARTEFACT_FRONTMATTER_SCHEMA.md`, `OUTPUT_ECONOMY_PROTOCOL.md`) | Output-economy validation |
| `policies/reader_accessibility.v1.json` + `policies/repin_log.jsonl` / derived `policies/repin_log.md` + `generated/reader_accessibility_policy_view.md` + `schemas/reader_accessibility_profile.schema.json` + `schemas/reader_accessibility_candidates.schema.json` + `schemas/check8_evidence.schema.json` | Single machine-readable policy, deliberate `/repin-register` event ledger, exact generated human-readable views, and strict candidate/adjudicated-evidence contracts; semantic re-pins are package-snapshotted and binding epochs are Planner-applied | Every Ph2–Ph4 Check 8 dispatch, F1, MF-POLICY validation, and deliberate register re-pin |
| `policies/draft_governance.v1.json` + `scripts/draft_governance.py` + `scripts/centroid_service.py` + `scripts/source_extract.py` + `scripts/product_assurance.py` | Universal M1-M4/FINAL resolver and product verifier; separates binding resolution from passage execution; verifies canonical extracts, quotes, same-year title/label identity, grounding candidates, and corpus-relative register; binds independent current-byte evaluation to the complete policy bundle | Before and after every academic draft or revision; required by milestone `record` and terminal full-run validation |
| `VERDICT_CACHE_CONTRACT.md` | P-14 paragraph-hash verdict carryover cache contract | Ph3 verdict reuse; currently unwired — no live consumer routes here (2026-07-07 audit) |
| `schemas/version_planes.json` | Snapshot-mode registry of non-package version-plane assertions (lifecycle ladder, phase-state schema, evaluator envelope, stage x profile vocabulary); guarded by `scripts/version-planes-check.py` | Maintainer check surface; re-snapshot deliberately on any version-assertion change (plan 2026-07-06 WS-2) |
| `schemas/commitment_interactions.json` | Declare-or-fail registry of all C-x pairwise interaction classifications; guarded by `scripts/commitment-interactions-check.py`; STYLE_COMMITMENTS.md remains authoritative for tension content | Maintainer check surface; every new commitment requires full pair coverage (plan 2026-07-06 WS-3) |
| `MODEL_ALLOCATION.md` | Phase-conditioned Claude-model mapping; §3 Opus 4.7 floor (Evaluator-Ph2/Ph3/Ph4, Reflector-full-Ph4) | Planner at every dispatch; Reflector at Phase 2f |
| `AGENT_ORCHESTRATION.md` | Four-agent architecture (Planner, Evaluator, Generator, Reflector); §8.6 Coupling E.2 graph overlay | Dispatching agents or running the full loop |
| `AGENT_CONTRACTS.md` | Per-agent declarative contracts: preconditions, inputs, outputs, invariants, done criteria, failure modes | Read with `agents/<role>.md`; contracts win on obligations, prompts win on method |
| `PARALLEL_CONDUCTOR.md` | Concurrency model (L0–L3), `conductor.md` ledger, session-handoff protocol | Multi-project or session-ends-mid-round |
| `ARTEFACT_FRONTMATTER_SCHEMA.md` | F1–F8 artefact families; validator at `scripts/artefact_frontmatter_validate.py` | Evaluator/Reflector authoring artefacts; Planner reading frontmatter |
| `OUTPUT_ECONOMY_PROTOCOL.md` | Evidence packets, events log, final round report assembly, compatibility pointers | Default outputs per phase since v0.14.0 |
| `PHASE3_PHASE4_COMMON_ENVELOPE.md` | Shared Ph3/Ph4 semantics inherited by `run-phase-3-stability` | When implementing or auditing the common envelope |
| `phase_notifications.yaml` | Centralised notification templates for user-facing ledger transitions | Planner rendering checkpoint notifications |
| `ADVISOR_MCP.md` | Advisor MCP entry points EP-1 / EP-2; not a substitute for `EXTERNAL_VERIFIERS` | Scheduling external feedback or submission-defensibility consultations |

### Post-review integrity

| File | Role | When authoritative |
|---|---|---|
| `SAFEGUARD_LAYER.md` | Post-review integrity: regression, drift, consistency, contradictions, traceability, voice | Step 8.5 after consolidated report, before author approval |
| `DRIFT_CHECK.md` | MASTER/component reconciliation gate; Quote/Claim/Structural drift; hard gate before G.4 | Reflector at Phase 2.6 every round |
| `REFLEXIVITY_CHECK.md` | Authorship-identity instrumentation; substitution-vs-augmentation audit | Reflector at Phase 2.7; mandatory at submission-bound depth |
| `READER_ACCESSIBILITY.md` | Package-local semantic authority for Sub-check A–H; machine projection at `policies/reader_accessibility.v1.json`; VE is adjacent and non-gating | Step 8.5; SAFEGUARD Check 8 aggregation; MF-POLICY |

### Style and craft

| File | Role |
|---|---|
| `STYLE_COMMITMENTS.md` | Declares Suchman/Bacon/Sexton/Baird (C-1…C-4) plus C-5 reader-accessibility, C-6 rhetorical–analytical separation / scoped metaphor, C-7 voice-fingerprint preservation, and C-8 analytic-construction discipline as named commitments, with relaxation procedure |
| `analytic_construction_guidelines.md` | C-8 substrate — the seven analytic-move tests (M-1…M-7) grounded in Abbott, *The System of Professions* (1988); the analytic-move layer between C-2 (clause craft) and C-4 (theory anatomy); plus the reflexive agents-as-jurisdictions lens (§6) |
| `voice_preservation_guidelines.md` | C-7 substrate — mechanics/identity split, idiolect non-target list, baseline-before-register scoring (Moran, Zinsser, Strunk, Abbott ×2) |
| `Sexton_Fiction_to_Academic_Writing_Guide.md` | Narrative arc, openings, show-don't-tell, cause-effect |
| `MASTER_research_and_paper_guidelines.md` | Cross-venue playbook for tone, claims, theory, audience, structure |
| `M1_M2_M3_ARGUMENTATIVE_RIGOR_CHECKLIST.md` | Pre-drafting argumentative-rigor checklist |
| `M1_M2_M3_PLANNING_PHASE_README.md` | Ph1 orientation for M1-M3 Planner checks, feedback gates, and handoffs |
| `PARAGRAPH_DEFINITIONS.md` | Canonical paragraph-class definitions |

### Formal ontology design

| File | Role |
|---|---|
| `BFO_ONTOLOGY_DESIGN.md` | Canonical conditional, actor-neutral policy for BFO-aligned formal ontology construction and audit; includes BFO conformance profile, relation discipline, lifecycle/versioning, a blocking release gate, source map, and anti-drift trigger boundary. The policy is actor-neutral; its evaluation/generation/escalation duties are bound to agents in the harness role files (planner/generator/evaluator). |

### External verification and metrics

| File | Role |
|---|---|
| `EXTERNAL_VERIFIERS.md` | External verification requirement; Class 1/1.5/2/3 verifier registry; wiki-first ordering |
| `EVAL_METHODOLOGY.md` | Skill-benchmark disclosure standard; undisclosed scores ⇒ ICI |
| `SUCCESS_METRICS.md` | Six-dimension quality framework D1–D6 |
| `distribution_rights.json` + `../THIRD_PARTY_NOTICES.md` | Forward-looking distribution dispositions, forbidden hashes, replacements, and historical-scope caveat |

### Operational

| File | Role |
|---|---|
| `PROJECT_BOOTSTRAP.md` | Directory template, seed files, bootstrap procedure |
| `TOKEN_BUDGET_PROTOCOL.md` | Context/token management; size classes, segmentation, state preservation |
| `RESEARCH_ROOT_CLAUDE.md` | Root-level CLAUDE.md for the Research folder |
| `COWORK_SESSION_INSTRUCTIONS.md` | Cowork-session-specific operating notes |
| `SKILL_REGISTRY.md` | Per-skill registry (SK-N entries); PR-3b.3 added SK-37/38/39 alias entries |
| `policies/command_surface.v1.json` | Machine-readable public, legacy-hidden, maintainer-hidden, and unavailable-hidden skill classification; enforced by `scripts/command_surface_check.py` |
| `_snippets/` | Atomic policy fragments loaded by explicit plugin-root runtime bindings |

### Retired / migration-only

| File | Notes |
|---|---|
| `TIER_PROTOCOL.md` | Renamed to `PHASE_PROTOCOL.md` at v0.7.4; this file remains for legacy reads only |
| `ADVISORY_UNTIL_SCOPING.md` | Historical scoping notes |
| `DRIFT_LOG.md` | Historical drift-event ledger |

---

## 4. The `_snippets/` directory

Atomic policy fragments loaded at invocation time through explicit plugin-root paths. Each `_snippets/*.md` file is intended to be ≤ 60 lines and represent a single normative block reused across multiple skills or agents. Build-time include expansion is prohibited on live package surfaces because Git-source marketplace installs do not run the builder; source caches and the audited archive must carry identical policy bytes.

Current snippets: `_snippets/reflection-grounding.md` (shared reflector epistemic preamble, runtime-bound by both split reflector agents).
- `_snippets/output-profile.md` — the canonical routine `silent_evidence` block (PR-1). Runtime-bound by `run-iterate` and the phase compatibility skills (`run-phase-1`, `run-phase-2`, `run-phase-3`).

Anti-duplication and distribution parity: `scripts/snippet-check.py` verifies the exact runtime-consumer set, rejects build-only include sentinels, and ensures snippet content does not appear verbatim outside `_snippets/` at release-gate time.

---

## 5. Notes preserved from CLAUDE.md §3

- **Autoresearch-inspired concepts (2026-04-13).** Six enhancements adapted from Karpathy's autoresearch project distributed across existing files: (1) primary gate metrics per phase (`ROUTING_SPINE.md §3`); (2) scope budgets per agent (`AGENT_CONTRACTS.md §§1–4`); (3) `round_program.md` per round (`AGENT_ORCHESTRATION.md §8.2`); (4) Retain/Revert Protocol (`AGENT_ORCHESTRATION.md §7`); (5) structured experiment logging in `revision_log.md` (`AGENT_CONTRACTS.md §3`); (6) three-layer architecture immutable/experimental/control (`AGENT_ORCHESTRATION.md §8.1`).
- **Graphify Coupling E.2 (2026-04-16; unavailable).** SK-20 `graph-grounding-overlay` remains fail-closed with `GRAPH_GOVERNED_GENERATION_UNAVAILABLE`. `wiki_linked: true`, `coupling_e_on_review: true`, fresh files, and valid graph structure are necessary checks but cannot activate graph authority. Orchestration hook: `AGENT_ORCHESTRATION.md §8.6`.
- **Examples folder (`references/examples/`).** Three artefact genres — review walkthroughs (`CAiSE_Rev01_walkthrough.md`, `INF3001_walkthrough.md`), calibration corpora (`model_prose_corpus.md`, mandatory load for `skills/accessibility-overlay/SKILL.md`), and finished-manuscript exemplars (`milestone5_v3_paper_trimmed.md` — INF3130 HCI M5 layperson register variant).

---

## 6. What MANIFEST is NOT

- **Not** a new authority layer. Authority precedence is in `CLAUDE.md §4`; this file routes only.
- **Not** an excuse to skip files. The routing table tells you which files are relevant for your task; you still read those files in full when invoked.
- **Not** a substitute for the Grounding Protocol. `GROUNDING_PROTOCOL.md` is always-loaded and binding regardless of what MANIFEST says.
- **Not** a stable interface for cross-project references. Other projects should reference the canonical files directly (`PHASE_PROTOCOL.md`, etc.), not MANIFEST sections.
