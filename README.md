<div align="center">

# co-author-harness

**A Claude Code plugin for PhD-level academic writing: four specialized agents, a climb-only phase ladder, and a rule stack that treats grounding as non-negotiable.**

[![Version](https://img.shields.io/badge/Version-manifest-0366D6?logo=semver&logoColor=white)](.claude-plugin/plugin.json)
[![Plugin](https://img.shields.io/badge/Plugin%20ID-co--author--harness--claude-8B5CF6)](.claude-plugin/plugin.json)
[![License](https://img.shields.io/badge/License-MIT-2ea44f)](#license)

[Quick start](#quick-start) · [Documentation](#documentation) · [Repository layout](#repository-layout) · [Changelog](CHANGELOG.md)

</div>

---

## Why this project

**co-author-harness** ships the *Research and Academic Paper Writing Package* as a maintainable tree you can open as a **plugin root** or embed beside a research workspace. It coordinates **Planner → Evaluator → Generator → Reflector** work, tracks progress on a per-section lifecycle ledger at `reviews/phase_state.json`, and routes the public stage commands `/run-draft`, `/run-iterate`, and `/run-finalize` without abandoning the binding rules in `references/GROUNDING_PROTOCOL.md`. Legacy `run-phase-*` skills remain hidden compatibility bodies for internal routing.

The harness root is **canonical** (formerly `research-writing-harness/`; `paper-harness/` is retired). Consolidation, ownership, and history: [`docs/agent-instructions/harness-architecture.md`](docs/agent-instructions/harness-architecture.md) · [`docs/agent-instructions/harness-history.md`](docs/agent-instructions/harness-history.md). Workspace contract (parent tree): `ROOT_ARCHITECTURE_INDEX.md` (workspace root — lives outside this repo).

---

## Features

* **Multi-agent, phase-conditioned dispatch.** Every M1-M4/FINAL draft receives centroid-conditioned Generator work and an independent current-byte Evaluator policy pass, including at Ph1; the full revision-maturity review begins at Ph2. Role engagement is governed by [`references/policies/phase_engagement.v1.json`](references/policies/phase_engagement.v1.json); model allocation and obligations are in [`references/MODEL_ALLOCATION.md`](references/MODEL_ALLOCATION.md) and [`references/AGENT_CONTRACTS.md`](references/AGENT_CONTRACTS.md).
* **Artifact presence is not compliance.** [`references/policies/draft_governance.v1.json`](references/policies/draft_governance.v1.json) binds centroid, D-STYLE, retained grammar/style rules, grounding, deterministic checks, SAFEGUARD, and applicable overlays before generation and after evaluation. Milestone record and terminal close require exact-byte evidence from both roles.
* **Two orthogonal axes.** Ph1 (Plan & Draft) → Ph2 (Review & Revise) → Ph3 (Iterate & Converge) → Ph4 (Finalize & Close) is specified in [`references/PHASE_PROTOCOL.md`](references/PHASE_PROTOCOL.md) (schema, triggers, MCR / convergence gates). Assignment-derived deliverables describe the *project* arc; the phase ladder governs *review and revision*. The backward-compatible M5 machine slot may represent a final paper that the assignment treats separately from its named milestones.
* **Grounding in front of cleverness.** [`references/GROUNDING_PROTOCOL.md`](references/GROUNDING_PROTOCOL.md) is absolute: no fabrication, no uncited numbers, no unverified citations. Precedence and cross-project rules: [`docs/agent-instructions/harness-governance.md`](docs/agent-instructions/harness-governance.md).
* **Slash-style skills, documented as files.** Slash commands under [`skills/`](skills/) (e.g. `check-contradictions`, `grounding-audit`, `narrative-structure-pass`, `run-generator-session`, `seed-snowball-discovery`, `claim-coverage-audit`, `extend-snowball-incremental`, `inherit-snowball-from-wiki`) with machine-checkable front matter—validated by the scripts below.

### Skill catalog

See [`skills/plugin-commands/SKILL.md`](skills/plugin-commands/SKILL.md) for the supported slash-command table. Visibility is governed by [`references/policies/command_surface.v1.json`](references/policies/command_surface.v1.json) and checked against native skill frontmatter by `scripts/command_surface_check.py`.

---

## Documentation

| Read this first | Why |
| --- | --- |
| [`CLAUDE.md`](CLAUDE.md) (repo root) | **When the package is invoked**, precedence in one place, and maintainer check commands. |
| [`references/ROUTING_SPINE.md`](references/ROUTING_SPINE.md) | **Intent → canonical milestone/state** routing; its seven labels are derived and never persisted. |
| [`references/QUICKSTART.md`](references/QUICKSTART.md) | One-page operator primer (session open, failure modes, shortcuts). |
| [`references/OPERATING_MANUAL.md`](references/OPERATING_MANUAL.md) | Full runbook when you inherit the package cold. |
| [`references/REVIEW_ORCHESTRATION.md`](references/REVIEW_ORCHESTRATION.md) | Classification, per-step review protocol, findings format. |
| [`references/CLAUDE.md`](references/CLAUDE.md) | **Package-level** invocation rules and component map. |

**New project?** Use `scripts/native_project_bootstrap.py` exactly as specified in [`references/PROJECT_BOOTSTRAP.md`](references/PROJECT_BOOTSTRAP.md); it atomically seeds the standard directories and the mandatory graph-independent reader-profile v2 binding. Hand-built native ledgers are not supported. **Discovery and lifecycle:** [`docs/agent-instructions/harness-discovery-lifecycle.md`](docs/agent-instructions/harness-discovery-lifecycle.md).

---

## Prerequisites

The harness's review surface depends on two external connectors. Both are
optional; the harness degrades gracefully when neither is connected, but
several SAFEGUARD checks and the snowball-discovery skill require at
least one of them to do useful work.

- **Zotero MCP** — used by the snowball-discovery skill to look up
  bibliographic metadata for cited sources and to admit new sources to
  the project's reference pool. Without Zotero, snowball discovery
  no-ops with `NO_REACHABLE_VERIFIER` per `skills/seed-snowball-discovery/SKILL.md §2`.
- **Scholarly-search MCP** (or any Class 1 verifier MCP that exposes
  Google Scholar, OpenAlex, or Crossref) — used by the snowball
  discovery loop's verifier fall-through path. Same no-op behaviour
  applies when the connector is absent.

Sessions that do not invoke `/seed-snowball-discovery`,
`/extend-snowball-incremental`, or the Ph2 claim-coverage audit can
proceed without either connector.

On hosts where the corpus is not mounted at the profile's recorded Windows
paths, set `AGENT_WIKI_ROOT`, `AGENT_WORKSPACE_ROOT`, and (when the package is
relocated) `AGENT_HARNESS_ROOT`. Explicit `--wiki-root`, `--workspace-root`, and
`--harness-root` arguments take precedence. The resolved reader-accessibility
binding records each effective path; override-mode bindings also record whether
each root came from an explicit argument, the environment, or the running
package root. Profile-mode output remains byte-compatible with existing binds.

## Quick start

1. **Open this repository** in Cursor or Claude Code so `${CLAUDE_PLUGIN_ROOT}`-style resolution matches your actual layout (see [`references/CLAUDE.md`](references/CLAUDE.md) for embedded vs plugin-root deployment).
2. **Start every substantive session** by resolving the project’s active milestone and canonical lifecycle state through [`references/ROUTING_SPINE.md`](references/ROUTING_SPINE.md); do not persist a derived intent label as state.
3. **Wire a research project** using the standard tree and `reviews/phase_state.json` as the ledger; bootstrap details are in [`references/PROJECT_BOOTSTRAP.md`](references/PROJECT_BOOTSTRAP.md).

**Example (session open)** — what you can literally ask the agent:

```text
Read references/ROUTING_SPINE.md, then tell me which milestone and lifecycle state this session should
run under and which artefact you will touch first.
```

Plugin identity and version are authoritative in [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json).

---

## Repository layout

| Path | What lives there |
| --- | --- |
| [`agents/`](agents/) | Planner, Evaluator, Generator, Reflector prompts |
| [`skills/`](skills/) | Slash-style skills (Ph rounds, checks, overlays, audits) |
| [`references/`](references/) | Orchestration, protocols, style packages, templates, registries |
| [`scripts/`](scripts/) | Validators, migration utilities, `release-gate.sh`, `build-plugin.py`, `build-release-zip.sh` |
| [`docs/agent-instructions/`](docs/agent-instructions/) | Architecture, governance, discovery, reference index |
| [`docs/historical/`](docs/historical/) | Archived audit reports and integration summaries (read-only history) |
| [`docs/release-notes/`](docs/release-notes/) | Release notes and packaging records for `.plugin` and legacy `.zip` builds |
| [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json) | Published plugin `name` / `version` / `description` |

---

## For maintainers

From the repo root, with **Python 3**, **PyYAML**, and **jsonschema** installed:

```bash
python scripts/skill-check.py
python scripts/schema_runtime_check.py
python scripts/version-check.py
python scripts/catalog-check.py
python scripts/command_surface_check.py
python scripts/path-hygiene-check.py
python scripts/snippet-check.py
python scripts/output_economy_check.py
python scripts/version-planes-check.py
python scripts/commitment-interactions-check.py
python scripts/phase_engagement_check.py
python scripts/retirement-sweep-check.py
python scripts/analysis/fixture_infrastructure_check.py
python scripts/analysis/fixture_runner.py --no-write
```

The fixture registry is the single behavioral-test authority. Omit
`--no-write` only to regenerate the committed manifest after the full corpus
passes.

Full release packaging: `scripts/release-gate.sh` (see script header). Release zip: `scripts/build-release-zip.sh`—artefact naming and notes in [`CHANGELOG.md`](CHANGELOG.md).

---

## Version

The current version is recorded in [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json), which is its sole authority. This section is release **history**; it does not restate the current version.

| Release | Highlights |
| --- | --- |
| **0.39.0** | Closes assurance-provenance gaps with kernel-issued one-time dispatch authority, shared current-byte verifier transactions across milestone and terminal consumers, a recorded synthetic M1-to-FINAL qualification, governed product-gate and runtime-plane probes, safe archive extraction, canonical checksums, and immutable package/release evidence indices. Package-cleared, shipped, and host-qualified remain distinct. |
| **0.38.0** | Introduces the product-assurance kernel: `binding_resolved` replaces ambiguous centroid `ready`; canonical `pdftotext` evidence and v2 passage receipts gate quotes and same-year citation identity; corpus-relative coinage/register, insider-negation, and empirical-claim candidates require independent adjudication; assignment writes form a terminally verified mutation hash-chain; routine rebinds return the exact Planner command. |
| **0.37.5** | Requires passage-level centroid semantic receipts, exact write/review derivations, current-byte generation/evaluation envelopes, and independent Evaluator identity before milestone or terminal acceptance. |
| **0.37.2** | Repairs the promoted centroid execution contract: the documented `prepare --role` CLI is now real and phase-checked, while a structural-only corpus returns the specific `GRAPH-SEMANTIC-INELIGIBLE` refusal instead of being flattened into `PROFILE_UNRESOLVED`. |
| **0.35.0** | Hardens the semantic-register re-pin boundary: governed graph writers fail closed, Codex and Claude semantic audits share one provenance-checked contract, attestation/exemplar projections are stable under real graph serialization, and a production Planner transaction verifies and applies pending project rebind requests without letting the re-pin writer mutate lifecycle state. |
| **0.34.0** | Replaces the duplicated skill-plus-command-shim inventory with one native-skill surface; exposes only supported user commands, hides legacy/maintainer/unavailable contracts without deleting them, and machine-checks the menu against a command-surface policy. Phantom slash names are reclassified as real public skills or Planner intents. |
| **0.33.2** | Makes Git-source Claude/Codex installs byte-equivalent to the audited release policy: six packaged snippet expansions become explicit runtime file bindings, and a release source-parity gate refuses any missing, extra, duplicate, or rewritten source member beyond generated provenance. |
| **0.33.1** | Repairs Codex discovery of the repository-root plugin without duplicating the package or creating a distribution branch: the marketplace uses a dual-loader remote URL source, while shared validators keep manifest identity, version/license/description parity, source/repository agreement, and archive checks connected across source shapes. |
| **0.33.0** | Systematic package repair: machine-readable Contract Kernel, canonical lifecycle and role contracts, transactional scoped-writer receipts and M1–M5 close, truthful capability dispositions, unified entrypoints, one behavioral fixture authority, Windows-portable commit-bound packaging, and forward-looking distribution-rights enforcement with package-authored replacements. Deferred graph/Wiki authority and public `/centroid-pass` execution remain explicitly unavailable. |
| **0.32.0** | Adds the SK-47 `/centroid-pass` catalog surface, then corrects it after a live-interface audit: the public command is unavailable with deterministic reason `IMPLEMENTATION_MISSING` and performs no writes. A maintainer-only script prepares a read-only, hash- and policy-bound analysis packet with no semantic verdict; public promotion remains separately governed. Graph authority remains unconditionally unavailable, and behavioral fixtures prove that structural graph validity cannot unlock it or Wiki mutation. |
| **0.31.1** | Wires the full-run contract into explicitly scoped Claude Code PreToolUse and Stop hooks; supports the observed `Task` and compatibility `Agent` subagent names; adds a post-hoc completeness detector that preserves UNVERIFIABLE outcomes and mixed-tree expected roots; release-gates the full-run bypass suites with safe nonzero capture; records the confirmed epoch-5 exemplar-view re-pin; and reconciles SK20 smoke expectations with the intentional graph-authority refusal. Shell writes and unverified Cowork prevention remain outside the claim. |
| **0.31.0** | Reproducible release packaging bound to a single commit (neutral enumeration module, clean-worktree builder re-exec, one committed builder, digest-exact writer-bound manifests, repo-global sandbox/lock, honest 5/6/7 exit contract); and Research Truth Phase 0/1 — canonical Coupling C/D Wiki mutation deferred (`WIKI_WRITE_TRANSACTION_UNAVAILABLE`, non-blocking) plus an unconditional `GRAPH_GOVERNED_GENERATION_UNAVAILABLE` graph-authority gate. Additive — no four-agent-contract change. |
| **0.30.0** | Requires exact event bindings when a primary-lineage deliverable is recorded before acceptance; adds provenance-recorded environment fallbacks for portable register roots; clarifies that native milestone mode does not authorize assignment-gate N/A. |
| **0.29.0** | Extends `/repin-register` with exact-key exemplar add/drop inside the existing confirmed re-pin transaction; singleton centroid/intentional-root locks; defaulted `warrant_scope`; warn-only PDF/coherence advisories; scope-aware resolver projections for Check 8 surface warrant versus C-8/C-3/IS-theory argument warrant; and the ninth fixture-only acceptance case. No live corpus or project mutation. |
| **0.28.1** | Adds `/repin-register`: one authoritative, single-snapshot compute path for deliberate domain-native register re-pins; append-only package ledger plus derived view; atomic, confirmed profile patching; binding-level epochs with old-round softening; Planner-owned project rebind requests; scoped-dirt and lock refusal gates; and an eight-case release-gated smoke suite. |
| **0.28.0** | Milestone feedback and handoff framework. M1–M5 now share a machine-readable contract for deliverables, feedback, adjudication, bindings, and downstream handoffs; `lifecycle_state.md` is rendered from that single authority instead of becoming a second ledger. Native bootstrap and deterministic validators distinguish clean lifecycle exemplars from legacy migration exemplars, preserve project-level override precedence, and report preflight as READY, authorized NOT_APPLICABLE, or MISCONFIGURED. Reader-accessibility policy gains a domain-native register model and deterministic cadence/Check 8 semantics without treating paragraph length as a universal quality proxy. Read-only RE-essay and INF3130 pilots supplied regression shapes for current-hash continuity, stale approval, reopened milestones, divergent lineage, retrospective feedback, and Ph3-sibling blocking; neither live project was migrated or edited. |
| **0.27.0** | Audit-remediation cycle (report: `reviews/harness_audit_2026-07-13.md`). The 2026-07-13 full audit found the deterministic layer green while semantic drift survived on live surfaces; this cycle closes it: `pre_phase_advance_check.py` tier_state→phase_state migration completed (phase-named ledger, restored schema constant, canonical triggers 28/30 added, Ph-named CLI, new gate-wired regression smoketest); `MODEL_ALLOCATION.md` re-voiced to the phase surface (model pins unchanged — v0.25.0 deferral now recorded in-file); stale 15/16-field and 30-trigger counterclaims swept to the 18-field/31-trigger canon across references/CLAUDE.md, planner, AGENT_ORCHESTRATION, docs/agent-instructions, F3 template, phase_notifications.yaml; ghost/retired citations fixed (skills/SKILL_REGISTRY.md path ×6, eygp-framework-checker, run-tier-* dispatch table in classify-manuscript, phantom legacy/ archive claims, unannotated retired migration scripts); SAFEGUARD_LAYER routing re-keyed from retired review-depth vocabulary to phases; `retirement-sweep-check.py` extended with registry-driven **retired_phrases** negative assertions so stale counterclaims and retired ladder vocabulary now block at the gate. Additive — no schema or four-agent-contract change. |
| **0.26.0** | Precision-gate cycle (surfaced by the QE2026 First-Principles RE Essay Ph4 pass). Adds two mandatory Step-4 judgment gates to the sentence-craft layer: a **concept-introduction priority gate** (Bacon §3.7 — introduction-provenance, derivation-continuity, scope-authority, reader-reconstruction tests; a fluent definition of an unintroduced construct is MAJOR when frame-changing) and **semantic-predication integrity** as `sentence-level-pass` Check 10 (Bacon §3.6 — bearer, contrast-set, domain-collocation, transformation-continuity, and conceptual-debt tests; *precision and clarification outrank vividness*, so an image whose implication a later clause must repair is a finding). Wired through `agents/evaluator.md`, `references/REVIEW_ORCHESTRATION.md` (Step 4 + overlap map), `references/project_writing_style_checklist.md`, and `references/bacon_2009_well_crafted_sentence_guidelines.md §§3.6–3.7`; `sentence-level-pass` → v1.4. Two new regression smoketests (`concept_introduction_contract_smoketest.py`, `semantic_predication_contract_smoketest.py`) encode the live QE2026 fixtures and are enforced by `release-gate.sh`. Additive — no schema or four-agent-contract change. |
| **0.25.0** | Advisor-surface alignment with advisor plugin v0.4.0 — the advisor MCP server's model baseline moved `claude-opus-4-7` → `claude-fable-5` (US$10/US$50 per MTok list pricing, verified 2026-07-07). `advisor-escalation` SKILL cost-gate text and pricing updated; SK-18 registry entry re-worded frontier-class with dated model pin. No procedure, schema, or gate change. |
| **0.24.0** | Deferred-register closure (report: `docs/analysis/2026-07-07_deferred-register-closure.md`) — the nine open items from the coherence audit, executed as one program: tier→phase migration completed on the last three tier-speaking surfaces (REVIEW_ORCHESTRATION §3.3 rewritten phase-native; AGENT_CONTRACTS §2 Evaluator contract reconciled to F7/check_profile envelopes; T3R settled as a retired sibling — response letters are a Ph3 manuscript-class); migration made enforceable (`retirement-sweep-check.py` + `schemas/retired_surfaces.json`, closing the gate header's oldest deferred gap; 18-field/31-trigger count planes registered); MCP UUID namespaces made symbolic; orphans disposed (GROUND_TRUTH routed from classify-manuscript, notifications smoketest created + wired, packaging canonicalized to the gate). 23/23 checks green. Sole remaining vocabulary fork: the recorded agent-file ladder fork, deferred pending a dispatch-surface test. |
| **0.23.0** | Full-links coherence audit (report: `docs/analysis/2026-07-07_full-links-coherence-audit.md`). Four-lane dependency-graph audit; ~45 anchor-verified fixes: schema-count drift healed everywhere (18-field SectionStateObject, 31-trigger enum, 7-field log row), planner Ph1 digest-exception leak removed, reflector-split pointer fallout repaired, run-iterate canonicality reconciled with its shim+catalog, v0.7.0 ladder assertions lifted to v0.8.0 on non-agent surfaces, stage×profile 0.15.1 fork recorded in the version-planes registry, SKILL_REGISTRY tier-era dependency rows migrated, MANIFEST honesty + missing rows, `terminology_register.md` created (was cited-but-absent), committed check dumps quarantined, CI expanded 9→21 checks including two previously-orphaned smoketests that caught two live regressions during the cycle. Open judgment items in report §4. |
| **0.22.0** | Registry-over-prose hardening cycle (plan: `docs/analysis/2026-07-06_systematic-improvement-plan.md`). Two new declare-or-fail registries + checks: **`references/schemas/version_planes.json`** + `scripts/version-planes-check.py` (snapshot-mode guard for the non-package version planes — silent assertion drift and fork-widening are blockers) and **`references/schemas/commitment_interactions.json`** + `scripts/commitment-interactions-check.py` (all 28 C-x pair classifications explicit; a new commitment without full pair coverage is a blocker). **Golden-manuscript eval scaffold** at `scripts/fixtures/golden/` (P2 detection fixture + P1 false-positive control + findings schema + deterministic scorer `scripts/eval/golden_eval_score.py`) for judgment-layer regression measurement. **CI** at `.github/workflows/structural-checks.yml` running the full nine-check set; checks wired simultaneously into `release-gate.sh`, root `CLAUDE.md`, and `AGENTS.md`. Root hygiene: runbook → `docs/release-notes/`, tooling → `scripts/`; `agents/reflector.md` retirement condition made explicit. Additive; no agent-contract changes. |
| **0.21.0** | C-8 companion skills + the C-6↔M-1 interaction. Completes the C-8 skill set with two P2-gated single-move passes — **SK-43 `definition-derivation-check`** (M-1: is each contested term derived or stipulated, with a C-6 keys-only-glossary carve-in) and **SK-44 `dissolution-move-check`** (M-2: charitable reconstruction / named assumption / dissolve-vs-contradict; strawman → MAJOR). Encodes the **C-6↔C-8/M-1 interaction** (an upfront glossary is M-1-compatible if keys-only; a glossary that pre-states a derived construct's payoff is `[MINOR — C-6↔C-8/M-1]`) in `analytic_construction_guidelines.md §2 M-1` and `STYLE_COMMITMENTS.md §1.0a/§1.0d`, and tightens the `analytic-move-audit` applicability gate to admit conceptual briefs/working drafts by rule rather than reviewer judgment. Both findings were surfaced by two live-runs against QE2026 advisor artifacts (a P1 brief and a P2 draft) that also confirmed the P-stage gate. Additive — no change to C-1…C-8. Rationale: `docs/analysis/2026-07-01_abbott-system-of-professions-analytic-construction-and-C8-rationale.md`. |
| **0.20.0** | Analytic-construction discipline. New style commitment **C-8 (analytic-construction discipline)** — a *convergent* commitment claiming the analytic-move layer between C-2 (clause craft) and C-4 (static theory anatomy): C-4 audits whether a theory *has* the right parts, C-8 audits whether they were *earned*. New `references/analytic_construction_guidelines.md` absorbs Abbott's *The System of Professions* (1988) under the source-absorption pattern, encoding seven analytic moves (M-1 definitional deferral … M-7 meta-reflexivity) with verified quotes + operational tests, P-stage gating (M-1/M-2/M-7 are P2-only), and M-4/M-5 protective carve-outs that overturn a `sentence-level-pass` monotony/concision flag on demonstrative anaphora and cadential verdicts. New skill **SK-42 `analytic-move-audit`** (+ command shim, catalog, registry). A §6 reflexive coda maps Abbott's *jurisdiction* theory onto the harness's own division of expert labor (recorded, not ratified). Planner/Generator/Evaluator wired. Additive — no change to C-1…C-7. Distinct from the C-7 Abbott (*Methods of Discovery*/*Digital Paper*): C-7 protects the writer's voice, C-8 governs the writer's argumentative moves. Rationale: `docs/analysis/2026-07-01_abbott-system-of-professions-analytic-construction-and-C8-rationale.md`. |
| **0.19.0** | Voice-fingerprint preservation. New style commitment **C-7 (authorial voice-fingerprint preservation)** — the first *protective* commitment (names what prose must not lose, where C-1…C-6 are convergent). New `references/voice_preservation_guidelines.md` absorbs Moran, Zinsser, Strunk, and Abbott (×2) under the source-absorption pattern, grounding the mechanics/identity split, the idiolect non-target list, and baseline-before-register scoring. `SAFEGUARD_LAYER.md` Check 6 gains an idiolect-baseline Step 0; `sentence-level-pass` (→v1.2) and `narrative-structure-pass` (→v1.1) gain a C-7 carve-out so monotony/passive/"consistent voice" flags yield to baseline idiolect; Planner/Generator/Evaluator wired. Additive — no change to C-1…C-6. Rationale: `docs/analysis/2026-06-30_voice-fingerprint-analysis-and-C7-rationale.md`. |
| **0.18.0** | D-STYLE consumption layer. New `scripts/d_style_profile_check.py` (schema 1.1.0) validates the `research_notes/directives.md` `d_style_profile` block (enum + inherit-by-absence), emits active D-STYLE obligations, and runs surface-floor validators (argument / visual-evidence / assistance cues). `scripts/audit/run_all.py` gains `--project-root` as the canonical pre-flight emitting both `reviews/findings.json` and `reviews/d_style_profile_*.json`; legacy positional API preserved. Wired into evaluator / planner / MANIFEST / DETERMINISTIC_CHECKS section 0 / ARTEFACT_FRONTMATTER_SCHEMA / PROJECT_BOOTSTRAP. Surface checks are a floor only; warrant / visual-evidence / argument adequacy remains Evaluator judgment. |
| **0.16.0** | Lifecycle ladder + ontology guideline. **PR-3b.4:** public lifecycle surface becomes the three-stage ladder `/run-draft` → `/run-iterate` → `/run-finalize` (former `/run-phase-2` → `/run-iterate --profile refine`; former `/run-phase-3-stability` → `/run-iterate --profile stability`); legacy commands ship as compatibility routers (`scripts/alias_parity_smoketest.py` pins the routing contract). **Ontology guideline:** new `references/BFO_ONTOLOGY_DESIGN.md` (BFO-aligned ontology-design policy paraphrasing Arp, Smith & Spear 2015, ch. 3–4; formal-ontology artifacts only) and new style commitment **C-6 “rhetorical–analytical separation & scoped metaphor”** (`STYLE_COMMITMENTS.md §1.0a`, from the INF3006Y supervisor meetings 2026-06-18/06-25), with MANIFEST routing and Planner/Evaluator/Generator + AGENTS/CLAUDE bindings. Also migrates wiki paths to `knowledge/LLM wiki/` across the affected skills. |
| **0.15.0** | Strict-Layers architecture (nine-commit stack on `main`). PR-1+2: snippet-include mechanism under `references/_snippets/` + scripts-first audit suite under `scripts/audit/` — promotes regex catalogue from markdown-resident to executable, emits canonical `reviews/findings.json`, ships 13-check `audit_style.py` plus deterministic citation resolver `audit_citations.py` (PR-4a) that closes the v0.14.0 LLM-self-attestation loop by mechanically resolving `[GP §N]` / `GROUNDING_PROTOCOL.md §Rule N` citations against the stable `<a id="gp-N"></a>` anchors landed at PR-3a. PR-3b.1–3: additive `stage` / `profile` shadow fields on every `SectionStateObject` (validator accepts both legacy `current_phase` and new axis), MCR `W-MCR-CONVERGENCE-EVIDENCE` advisory (non-blocking; non-refine two-round stability), and `/run-draft` / `/run-iterate` / `/run-finalize` skill aliases with `run-phase-N` canonical preserved. PR-4b: `references/MANIFEST.md` routing index + slim `references/CLAUDE.md` (150 → 83 lines). PR-4c: Reflector split into `agents/reflector-probe.md` (lightweight Ph1–Ph3 integrity) and `agents/reflector-closeout.md` (full Ph4 reflection) sharing `_snippets/reflection-grounding.md`; legacy `agents/reflector.md` retained as compatibility router; total Reflector surface 20,113 → 11,736 tokens. PR-4d: warn-only `scripts/token_budget_check.py` with `tiktoken` cl100k_base; release-gate measurement informs but never blocks. Ph2 → Ph3-refine merge (PR-3b.4) deliberately deferred to a later minor as a high-risk lifecycle migration. |
| **0.14.0** | Output economy (Option C architecture): F7 JSON evidence packets under `reviews/.harness/evidence/`, append-only `reviews/.harness/events.jsonl`, F8 `final_round_report_<round_id>.md` assembled by the Planner, protocol at `references/OUTPUT_ECONOMY_PROTOCOL.md`, JSON schema `references/schemas/f7_evidence_packet.schema.json`, template `references/templates/final_round_report.md`. Phase skills and agents updated for default evidence-first outputs; `scripts/output_economy_check.py` + `scripts/output_economy_smoketest.py` wired into `release-gate.sh` and maintainer checks in root `CLAUDE.md`. `artefact_frontmatter_validate.py` gains F7/F8 lanes. |
| **0.13.0** | Voice / register / citation lessons batch from the INF3006Y late-April 2026 sessions. Six-cluster patch lands in three new files (`references/EMDASH_BUNDLE_DISCIPLINE.md` — top-level discipline note binding the Generator at every prose action with no exceptions; `references/CITATION_DISCIPLINE.md` — engagement-cite vs. demarcation-no-cite two-question test; `docs/superpowers/plans/2026-04-30-voice-and-h-lessons.md` — source memo) plus four targeted file amendments (`STYLE_COMMITMENTS.md §1.1` C-1 verb-set + parallelism rules; `lay_term_lexicons.md §5` drift-monitored corpus with `_corpus_drift` §9e probe and the worked-example signpost-as-M4-vehicle pattern; `skills/accessibility-overlay/references/sub_checks.md §H` twin-paragraph probe under H step 1 with `_twin_paragraph` §9e suffix; `references/SAFEGUARD_LAYER.md` Sub-check J — Verdict-Edge Discipline with intensifier-stack-floor diagnosis and modal-distribution softening rule, advisory_until J_two_revision_cycles). Generator binding clause added to `agents/generator.md` second binding constraint. Memory entry for cross-file mirror grep discipline. Source memo: `docs/superpowers/plans/2026-04-30-voice-and-h-lessons.md`. No agent contract retirements; no skill count change; no governance-field change. |
| **0.12.3** | Marketplace-schema alignment patch. `marketplace.json` restructured to clear the Cowork remote-marketplace upload validator: added `$schema` declaration, moved top-level `description` into `metadata.description`, namespaced top-level `name` to `joseph-chung-co-author-harness`, and changed `plugins[0].category` from `"research"` to `"productivity"` (the only documented and confirmed-accepted enum value). `plugin.json` unchanged except for the version bump. Diagnosed via Cowork `main.log` after v0.12.2 cleared the static `loader-compat-check.py` validator but was rejected by the remote `uploadAccountPlugin` endpoint within minutes — confirming the validator's scope limit (covers direct-install schema only, not marketplace-upload schema). No agent contract, skill, command, or governance-field change. |
| **0.12.2** | Pre-shipment quality patch. New `scripts/loader-compat-check.py` static loader-compatibility validator (10 axes — ZIP integrity, manifest schema, marketplace parity, path encoding, required-files presence, SKILL.md frontmatter, no-nested-archives, extract-rezip sanity, peer-plugin description-length distribution). Three over-margin SKILL.md descriptions trimmed to clear the 500-char safety margin enforced by `release-gate.sh` Phase 0.2: `claim-coverage-audit` (534 → 472), `run-phase-2` (534 → 327), `extend-snowball-incremental` (1029 → 477). All trims preserve triggering keywords; only metadata bloat, internal stage codes, and trigger-field duplication were cut. No agent contract, skill, command, or governance-field change. |
| **0.12.1** | Reader-accessibility calibration patch. `references/DETERMINISTIC_CHECKS.md §3` names the "H-motivated em-dash insertion" false-fix pattern (Generator's default Sub-check H marker 4 vehicle inflates the §3 count) and lists §3-neutral M4 alternatives (semicolon, colon, cue phrases). `references/lay_term_lexicons.md §4` (new) adds the INF3006Y verified-paraphrase corpus: five transformation entries with marker-gain attribution and draft-form notes, one kept-as-is exemplar, five generalisation notes including the em-dash-substitution rule that bridges to DETERMINISTIC_CHECKS §3. Both surfaces cross-reference each other; both are advisory-tier — no agent contract, skill, command, or governance-field change. |
| **0.12.0** | Reader-accessibility calibration corpus originally introduced with 16 source passages and per-check notes. Historical record only: later forward-looking rights remediation replaced those passages with package-authored synthetic A–H illustrations while preserving the operational path. |
| **0.11.0** | Architectural cut + structural anti-drift posture. SD/SR machinery retired across substrate (c1a/c1b/c1c with v0.10.0->v0.11.0 migration script). SK-21 phantom roadmap stripped (c4). Pre-v0.9.0 migration scripts and tier_state_*.py deleted (c5). New maintainer validators: manifest-coherence-check (description ≤300 chars, keywords ≤12, substrate-resolution, asserted-count BLOCKER, plugin.json/marketplace.json description parity), version-check trailer-strip enforcement, path-hygiene README-orphan + untracked-files-in-tracked-dirs rules (c8). SSOT registry .claude-plugin/ssot.yaml + ssot-check.py (c9). End-to-end ladder smoketest fixture + assertion harness (c10). pre_phase_advance_check.py clause (d) extended with classification.md presence check; README Prerequisites section names Zotero MCP and scholarly-search MCP (c11). |
| **0.10.2** | DETERMINISTIC_CHECKS §9e H pre-filter substrate (three counter probes for nominalisation / prepositional run length / hedging density; literature-anchored thresholds; reference Python at `scripts/check8_h_prefilter.py`); H lay-term policy tightening (load-bearing-Latinate whitelist with six entries; concrete-referent operationalisation across three classes with construct exclusion; signpost orienting/contribution clause split with orienting-clause Ph2 binding; register-shift signposting added as fourth positive marker per user directive 2026-04-27); accessibility-overlay v1.4 → v1.5; new `references/lay_term_lexicons.md` canonical lexicon file; H telemetry/aggregator (`scripts/aggregate_h_calibration.py`) + retirement-decision plan doc; quantitative-thresholds plan doc + v0.10.0 pilot replay protocol plan doc. §6.0 coupling-checklist EXEMPT throughout; skill count invariant 32 holds. |
| **0.10.1** | Hardening patch: architecture- and strategy-doc mirrors for the four S4 binding decisions anchored at `agents/planner.md §Phase 3.8` (four-outcome handler / inline parallel cap of 8 / S4.5-delivered regression hook / halt-vs-continue asymmetry rationale); SAFEGUARD Check 8 expanded from seven to eight Sub-checks (A–H) with the new Sub-check H (Register Appropriateness) operationalising the user's daily-language directive at two scopes (passage-scoped via the five non-technical passage roles; manuscript-scoped via the new `register_class` field in `directives.md`); H ships under `advisory_until: H_two_revision_cycles`; two `marketplace.json` slips closed at validator level (`scripts/version-check.py` extended) — version-skew rejecting the `.plugin` loader install (RC), and source-format slip rejecting `"."` against the marketplace loader's schema (post-RC; tag re-anchored to `7a53c02`). |
| **0.10.0** | Snowball-driven reference scaffolding (SK-33/34/35/36): wiki-first seed discovery, claim-coverage audit, incremental snowball extension, cross-project pre-seed inheritance; Ph1/Ph2 auto-dispatch wired; §6.0 Coupling Checklist; phase_state schema 16 → 18 fields; 8 new classification.md governance fields. |
| **0.9.0** | UI loadability via `.claude-plugin/plugin.json` + 12 `commands/<name>.md` shims; model allocation calibrator pin restored to `MODEL_ALLOCATION.md §2` (7 artefacts downshifted, 1 added; net orchestrator pool 14 → 7). |
| **0.8.7** | New `/run-generator-session` (SK-32): session-sourced Generator pass; `plugin-commands` and `SKILL_REGISTRY` updated. |
| **0.8.6** | Advisor MCP EP-1/EP-2, em-dash fix-round discipline, in-tree `plugin_calibrator_audit.py` for release-gate, accessibility `description` trim, `plugin-commands` routing. |
| **0.8.5** | Wiki-first read loop (`EXTERNAL_VERIFIERS.md` §1.5, `wiki_first_resources`, I-Gen-8, Planner wiki paths / revision-plan trace). |
| **0.8.4** | §9d `check8_g_prefilter.py`, A8 `provenance_prewrite_check.py`, `phase_notifications` doc fix, efficiency `role_overrides` completion, A6–A7 reflector/ADVISORY_UNTIL follow-through. |
| **0.8.3** | Co-author rebrand: plugin id `co-author-harness-claude`, folder name `co-author-harness/`, release zip `co-author-harness-claude-v*.zip`. No `phase_state.json` or skill renames. |

Full history: [`CHANGELOG.md`](CHANGELOG.md).

---

## License

Licensed under the **MIT License** (see [`LICENSE`](LICENSE)). Author: **Young Jo(seph) Chung** — `jo.chung@utoronto.ca`.

---

## Related links

* [`references/GROUNDING_PROTOCOL.md`](references/GROUNDING_PROTOCOL.md) — binding grounding rules
* [`docs/agent-instructions/harness-governance.md`](docs/agent-instructions/harness-governance.md) — full precedence ladder
