<div align="center">

# co-author-harness

**A Claude Code plugin for PhD-level academic writing: four specialized agents, a climb-only phase ladder, and a rule stack that treats grounding as non-negotiable.**

[![Version](https://img.shields.io/badge/Version-0.10.2-0366D6?logo=semver&logoColor=white)](.claude-plugin/plugin.json)
[![Plugin](https://img.shields.io/badge/Plugin%20ID-co--author--harness--claude-8B5CF6)](.claude-plugin/plugin.json)
[![License](https://img.shields.io/badge/License-UNLICENSED-888888)](#license)

[Quick start](#quick-start) · [Documentation](#documentation) · [Repository layout](#repository-layout) · [Changelog](CHANGELOG.md)

</div>

---

## Why this project

**co-author-harness** ships the *Research and Academic Paper Writing Package* as a maintainable tree you can open as a **plugin root** or embed beside a research workspace. It coordinates **Planner → Evaluator → Generator → Reflector** work, tracks progress on a per-section **Lifecycle–Phase Ladder** (Ph1–Ph4) with a ledger at `reviews/phase_state.json`, and routes skills such as `run-phase-1` … `run-phase-4`, `run-phase-3-stability`, and `quick-deterministic` without abandoning the binding rules in `references/GROUNDING_PROTOCOL.md`.

The harness root is **canonical** (formerly `research-writing-harness/`; `paper-harness/` is retired). Consolidation, ownership, and history: [`docs/agent-instructions/harness-architecture.md`](docs/agent-instructions/harness-architecture.md) · [`docs/agent-instructions/harness-history.md`](docs/agent-instructions/harness-history.md). Workspace contract (parent tree): `ROOT_ARCHITECTURE_INDEX.md` (workspace root — lives outside this repo).

---

## Features

* **Multi-agent, phase-conditioned dispatch.** Agent prompts in [`agents/`](agents/) and orchestration in [`references/AGENT_ORCHESTRATION.md`](references/AGENT_ORCHESTRATION.md) define who runs when (e.g. Evaluator joins from Ph2 onward; full four-agent loop in Ph3/Ph4). Model allocation and obligations are written down—see [`references/MODEL_ALLOCATION.md`](references/MODEL_ALLOCATION.md) and [`references/AGENT_CONTRACTS.md`](references/AGENT_CONTRACTS.md).
* **A ladder, not a free-for-all.** Ph1 (Plan & Draft) → Ph2 (Review & Revise) → Ph3 (Iterate & Converge) → Ph4 (Finalize & Close) is specified in [`references/PHASE_PROTOCOL.md`](references/PHASE_PROTOCOL.md) (schema, triggers, MCR / convergence gates). M1–M5 milestones still describe the *project* arc; the phase ladder governs *review and revision*.
* **Grounding in front of cleverness.** [`references/GROUNDING_PROTOCOL.md`](references/GROUNDING_PROTOCOL.md) is absolute: no fabrication, no uncited numbers, no unverified citations. Precedence and cross-project rules: [`docs/agent-instructions/harness-governance.md`](docs/agent-instructions/harness-governance.md).
* **Slash-style skills, documented as files.** Slash commands under [`skills/`](skills/) (e.g. `check-contradictions`, `grounding-audit`, `narrative-structure-pass`, `run-generator-session`, `seed-snowball-discovery`, `claim-coverage-audit`, `extend-snowball-incremental`, `inherit-snowball-from-wiki`) with machine-checkable front matter—validated by the scripts below.

### Skill catalog

See [`skills/plugin-commands/SKILL.md`](skills/plugin-commands/SKILL.md) for the slash-command table; the count is derived by `scripts/catalog-check.py` from the contents of `skills/`.

---

## Documentation

| Read this first | Why |
| --- | --- |
| [`CLAUDE.md`](CLAUDE.md) (repo root) | **When the package is invoked**, precedence in one place, and maintainer check commands. |
| [`references/ROUTING_SPINE.md`](references/ROUTING_SPINE.md) | **Intent → phase** dispatch and exit gates—read before dispatching a round. |
| [`references/QUICKSTART.md`](references/QUICKSTART.md) | One-page operator primer (session open, failure modes, shortcuts). |
| [`references/OPERATING_MANUAL.md`](references/OPERATING_MANUAL.md) | Full runbook when you inherit the package cold. |
| [`references/REVIEW_ORCHESTRATION.md`](references/REVIEW_ORCHESTRATION.md) | Classification, per-step review protocol, findings format. |
| [`references/CLAUDE.md`](references/CLAUDE.md) | **Package-level** invocation rules and component map. |

**New project?** [`references/PROJECT_BOOTSTRAP.md`](references/PROJECT_BOOTSTRAP.md) seeds the standard directories (`manuscript/`, `reviews/`, `research_notes/`). **Discovery and lifecycle:** [`docs/agent-instructions/harness-discovery-lifecycle.md`](docs/agent-instructions/harness-discovery-lifecycle.md).

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

## Quick start

1. **Open this repository** in Cursor or Claude Code so `${CLAUDE_PLUGIN_ROOT}`-style resolution matches your actual layout (see [`references/CLAUDE.md`](references/CLAUDE.md) for embedded vs plugin-root deployment).
2. **Start every substantive session** by reading [`references/ROUTING_SPINE.md`](references/ROUTING_SPINE.md) and naming the phase you are in—same spirit as the operational “one rule” in [`references/QUICKSTART.md`](references/QUICKSTART.md).
3. **Wire a research project** using the standard tree and `reviews/phase_state.json` as the ledger; bootstrap details are in [`references/PROJECT_BOOTSTRAP.md`](references/PROJECT_BOOTSTRAP.md).

**Example (session open)** — what you can literally ask the agent:

```text
Read references/ROUTING_SPINE.md, then tell me which phase this session should
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
| [`releases/`](releases/) | Plugin archives — `.plugin` and legacy `.zip` builds from `scripts/build-plugin.py` and `scripts/build-release-zip.sh` |
| [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json) | Published plugin `name` / `version` / `description` |

---

## For maintainers

From the repo root, with **Python 3** and **PyYAML** installed:

```bash
python scripts/skill-check.py
python scripts/version-check.py
python scripts/catalog-check.py
python scripts/path-hygiene-check.py
```

Full release packaging: `scripts/release-gate.sh` (see script header). Release zip: `scripts/build-release-zip.sh`—artefact naming and notes in [`CHANGELOG.md`](CHANGELOG.md).

---

## Version

`0.12.3`

| Release | Highlights |
| --- | --- |
| **0.12.3** | Marketplace-schema alignment patch. `marketplace.json` restructured to clear the Cowork remote-marketplace upload validator: added `$schema` declaration, moved top-level `description` into `metadata.description`, namespaced top-level `name` to `joseph-chung-co-author-harness`, and changed `plugins[0].category` from `"research"` to `"productivity"` (the only documented and confirmed-accepted enum value). `plugin.json` unchanged except for the version bump. Diagnosed via Cowork `main.log` after v0.12.2 cleared the static `loader-compat-check.py` validator but was rejected by the remote `uploadAccountPlugin` endpoint within minutes — confirming the validator's scope limit (covers direct-install schema only, not marketplace-upload schema). No agent contract, skill, command, or governance-field change. |
| **0.12.2** | Pre-shipment quality patch. New `scripts/loader-compat-check.py` static loader-compatibility validator (10 axes — ZIP integrity, manifest schema, marketplace parity, path encoding, required-files presence, SKILL.md frontmatter, no-nested-archives, extract-rezip sanity, peer-plugin description-length distribution). Three over-margin SKILL.md descriptions trimmed to clear the 500-char safety margin enforced by `release-gate.sh` Phase 0.2: `claim-coverage-audit` (534 → 472), `run-phase-2` (534 → 327), `extend-snowball-incremental` (1029 → 477). All trims preserve triggering keywords; only metadata bloat, internal stage codes, and trigger-field duplication were cut. No agent contract, skill, command, or governance-field change. |
| **0.12.1** | Reader-accessibility calibration patch. `references/DETERMINISTIC_CHECKS.md §3` names the "H-motivated em-dash insertion" false-fix pattern (Generator's default Sub-check H marker 4 vehicle inflates the §3 count) and lists §3-neutral M4 alternatives (semicolon, colon, cue phrases). `references/lay_term_lexicons.md §4` (new) adds the INF3006Y verified-paraphrase corpus: five transformation entries with marker-gain attribution and draft-form notes, one kept-as-is exemplar, five generalisation notes including the em-dash-substitution rule that bridges to DETERMINISTIC_CHECKS §3. Both surfaces cross-reference each other; both are advisory-tier — no agent contract, skill, command, or governance-field change. |
| **0.12.0** | Reader-accessibility calibration corpus. New `references/examples/model_prose_corpus.md` carries 16 pre-verified passages (Vidal 2022 + Suchman 2007, two per SAFEGUARD Check 8 Sub-check A–H) with marker audits, annotations, and contrastive calibration notes. Wired into `accessibility-overlay/SKILL.md` as a MANDATORY load and cross-referenced from `sub_checks.md` (eight pointers, one per Sub-check) and `READER_ACCESSIBILITY.md §13.4`. Closes the zero-example gap for Sub-checks A–G and the INF3006Y-only domain-overfitting concern for Sub-check H. Corpus is package-tier (no per-project override per design §7); extension is gated to Reflector Phase 4 cross-project recurrence audit. No skill, command, agent, or governance-field changes. |
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

**UNLICENSED** (see [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json)). Author: **Young Jo(seph) Chung** — `jo.chung@utoronto.ca`.

---

## Related links

* [`references/GROUNDING_PROTOCOL.md`](references/GROUNDING_PROTOCOL.md) — binding grounding rules
* [`docs/agent-instructions/harness-governance.md`](docs/agent-instructions/harness-governance.md) — full precedence ladder
