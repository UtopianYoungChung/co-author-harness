# co-author-harness

**Version:** 0.8.3 · **Plugin id:** `co-author-harness-claude`

A **Claude Code plugin** and document bundle for **PhD-level academic writing**: a four-agent workflow (Planner, Evaluator, Generator, Reflector), a **Lifecycle–Phase Ladder** (Ph1 Plan & Draft → Ph2 Review & Revise → Ph3 Iterate & Converge → Ph4 Finalize & Close), slash-command **skills**, and binding **grounding** rules (`references/GROUNDING_PROTOCOL.md`).

This repository is the **canonical harness root** (successor to the `research-writing-harness/` naming; `paper-harness/` is retired). Substance and history are documented in `[docs/agent-instructions/harness-architecture.md](docs/agent-instructions/harness-architecture.md)` and `[docs/agent-instructions/harness-history.md](docs/agent-instructions/harness-history.md)`.

---

## What you get


| Area                          | Location                                                                                                                                                                    |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Agent prompts                 | `[agents/](agents/)` — `planner`, `evaluator`, `generator`, `reflector`                                                                                                     |
| Skills (slash-style commands) | `[skills/](skills/)` — e.g. `run-phase-1` … `run-phase-4`, `run-phase-3-stability`, `run-reflection`, `quick-deterministic`, `check-contradictions`, and specialized passes |
| Rules and runbooks            | `[references/](references/)` — orchestration, phase protocol, review pipeline, templates, `MASTER_research_and_paper_guidelines.md`, etc.                                   |
| Validation and tooling        | `[scripts/](scripts/)` — phase state validation, artefact checks, migrations, release scripts                                                                               |
| Maintainer / agent docs       | `[docs/agent-instructions/](docs/agent-instructions/)` — architecture, discovery & lifecycle, governance, reference index                                                   |


Plugin metadata (name, version, description) lives in `[.claude-plugin/plugin.json](.claude-plugin/plugin.json)`.

---

## Quick start (using the package)

1. **Open the harness** in your editor or mount it as the plugin workspace so paths resolve (the package supports plugin-root layout; see `[references/CLAUDE.md](references/CLAUDE.md)` for deployment notes).
2. **Read the routing spine first** on each substantive session: `[references/ROUTING_SPINE.md](references/ROUTING_SPINE.md)` maps intent to phases and exit gates.
3. For a one-page operator primer, see `[references/QUICKSTART.md](references/QUICKSTART.md)`. For full orchestration, start with `[references/REVIEW_ORCHESTRATION.md](references/REVIEW_ORCHESTRATION.md)` and `[references/AGENT_ORCHESTRATION.md](references/AGENT_ORCHESTRATION.md)`. The full operational runbook is `[references/OPERATING_MANUAL.md](references/OPERATING_MANUAL.md)`.
4. **Harness root policy** (when the package is invoked, precedence, triggers) is in `[CLAUDE.md](CLAUDE.md)` at this repository root.

New research projects under this system use a standard tree (`manuscript/`, `reviews/` including `phase_state.json`, `research_notes/`, project `CLAUDE.md`). The bootstrap protocol is in `[references/PROJECT_BOOTSTRAP.md](references/PROJECT_BOOTSTRAP.md)`; lifecycle and discovery are summarized in `[docs/agent-instructions/harness-discovery-lifecycle.md](docs/agent-instructions/harness-discovery-lifecycle.md)`.

---

## Maintainer checks (from repo root)

With **Python 3** and **PyYAML** available:

```bash
python scripts/skill-check.py
python scripts/version-check.py
python scripts/catalog-check.py
python scripts/path-hygiene-check.py
```

Full release packaging (bash): `scripts/release-gate.sh` (see the script header for flags). Release zip builds use `scripts/build-release-zip.sh`; shipped zips are described in `[CHANGELOG.md](CHANGELOG.md)`.

---

## Version


| Release   | Notes                                                                                                                                                                                                      |
| --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **0.8.3** | Co-author rebrand: plugin id `co-author-harness-claude`, repo folder `co-author-harness/`, release zip naming `co-author-harness-claude-v*.zip`. No skill renames and no `phase_state.json` schema change. |


Older entries and meta-level changes: `[CHANGELOG.md](CHANGELOG.md)`.

---

## Authors and license

- **Author:** Young Jo(seph) Chung — `jo.chung@utoronto.ca` (from plugin manifest).
- **License:** `UNLICENSED` (see `[.claude-plugin/plugin.json](.claude-plugin/plugin.json)`).

---

## Related reading

- `[CLAUDE.md](CLAUDE.md)` — root instructions and package invocation triggers  
- `[docs/agent-instructions/harness-governance.md](docs/agent-instructions/harness-governance.md)` — precedence and cross-project rules  
- `[references/GROUNDING_PROTOCOL.md](references/GROUNDING_PROTOCOL.md)` — non-negotiable grounding rules for agents using this package

