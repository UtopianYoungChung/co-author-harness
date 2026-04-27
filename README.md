<div align="center">

# co-author-harness

**A Claude Code plugin for PhD-level academic writing: four specialized agents, a climb-only phase ladder, and a rule stack that treats grounding as non-negotiable.**

[![Version](https://img.shields.io/badge/Version-0.9.0-0366D6?logo=semver&logoColor=white)](.claude-plugin/plugin.json)
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
* **Slash-style skills, documented as files.** 32 skills under [`skills/`](skills/) (e.g. `check-contradictions`, `grounding-audit`, `narrative-structure-pass`, `run-generator-session`, `seed-snowball-discovery`, `claim-coverage-audit`, `extend-snowball-incremental`, `inherit-snowball-from-wiki`) with machine-checkable front matter—validated by the scripts below.

### Skills (32)

See [`skills/plugin-commands/SKILL.md`](skills/plugin-commands/SKILL.md) for the slash-command table.

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
| [`scripts/`](scripts/) | Validators, migration utilities, `release-gate.sh`, `build-release-zip.sh` |
| [`docs/agent-instructions/`](docs/agent-instructions/) | Architecture, governance, discovery, reference index |
| [`legacy/`](legacy/) | Retired in-tree material—frozen reference, not the editing surface |
| [`releases/`](releases/) | Plugin `.zip` builds from `scripts/build-release-zip.sh` (when committed) |
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

`0.9.0`

| Release | Highlights |
| --- | --- |
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
