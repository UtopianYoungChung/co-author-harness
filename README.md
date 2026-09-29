<div align="center">

# co-author-harness

**A plugin for drafting, reviewing, and revising academic writing in Codex and Claude.**

[![Version](https://img.shields.io/badge/Version-manifest-0366D6?logo=semver&logoColor=white)](version.json)
[![License](https://img.shields.io/badge/License-MIT-2ea44f)](#license)

[Install](#install) · [Quick start](#quick-start) · [Documentation](#documentation) · [Changelog](CHANGELOG.md)

</div>

Co-Author Harness coordinates planning, drafting, evaluation, and reflection under explicit rules for source grounding. Start with a focused review of a passage, develop a draft from supplied materials, or use the governed workflow for an established research project. Ordinary drafting and revision do not require a pre-existing project.

## What it does

- **Review a passage.** Run a focused grammar, sentence-craft, contradiction, or grounding check on pasted text or a file.
- **Draft from a brief.** Use `/run-draft` to develop a draft through generation, review, corrections, and reflection.
- **Revise a manuscript.** Use `/run-iterate` for a bounded revision, with a diagnosis and plan before editing and review afterward.
- **Work through a governed project.** Track planning, deliverables, revision, and finalization against the project's assignment and lifecycle state. `/run-finalize` retains the prerequisites for governed finalization.

The [command catalog](skills/plugin-commands/SKILL.md) lists the supported commands and their availability.

## Install

All installs need **Python 3 with PyYAML and jsonschema** for the package scripts and hook checks:

```text
python -m pip install pyyaml jsonschema
```

### Codex

```text
codex plugin marketplace add UtopianYoungChung/co-author-harness
codex plugin add co-author-harness@joseph-chung-co-author-harness
```

Follow the [Codex host setup](docs/agent-instructions/codex-host.md) to configure named native agents and review hook discovery and trust. That guide also covers updates and how to inspect the installed commit.

### Claude Code

```text
/plugin marketplace add UtopianYoungChung/co-author-harness
/plugin install co-author-harness@joseph-chung-co-author-harness
```

Claude Code hooks also require **Bash on `PATH`**; on Windows, use Git Bash. See the [Claude host guide](references/CLAUDE_CODE_HOST.md#installation-and-updates) for interpreter selection, automatic updates, and session reloads.

### Claude Desktop / Cowork

Download the latest [co-author-harness.plugin](https://github.com/UtopianYoungChung/co-author-harness/releases/latest/download/co-author-harness.plugin) and upload it through the host's plugin interface. Upload the newer file when you want to update. The [Releases page](https://github.com/UtopianYoungChung/co-author-harness/releases) also provides an identical `.zip`.

Drafting and revision require a host session that can spawn real child agents and retain inspectable original traces. The registered adapters cover Codex and Claude Code / Desktop / Cowork; read-only passes can run without native children. See the host guides for setup and verification.

## Quick start

Open a session with the plugin available, then supply the text, file, or source materials for your task. These are example requests you can send to the agent. The agent declares the appropriate run scope before dispatch.

### Review a passage

Scope: `adhoc_review` — findings and proposed corrections for the supplied text.

```text
Use grammar-mechanics-pass to review the paragraph below. Report the
problems and proposed corrections, leaving the original text unchanged.

[paste paragraph]
```

### Draft from supplied sources

Scope: `project_independent` — drafting, review, corrections, and reflection.

```text
Use /run-draft to write a short research memo from the excerpts below.
Explain the research problem and the open question, and deliver the
reviewed memo with any unresolved source-support gaps identified.

[paste brief and excerpts]
```

### Revise an existing manuscript

Scope: `project_independent` — diagnosis, a bounded plan, revision, and review.

```text
Use /run-iterate to improve the introduction in this manuscript.
Preserve its argument and citations, focus on clarity and flow,
and review the revised passage before delivery.

[attach manuscript or provide its path]
```

The [ordinary-task workflow](references/PROJECT_INDEPENDENT_WORKFLOW.md) defines these routes. For an explicit governed lifecycle run, start with the [full-run contract](references/FULL_RUN_CONTRACT.md) and [project routing guide](references/ROUTING_SPINE.md).

## How the workflow works

For ordinary drafting and revision, the **Planner** coordinates the task, the **Generator** produces proposed text, the **Evaluator** reviews it in a separate agent context, and the **Reflector** examines the round before delivery. Corrections return through the workflow as needed. A focused read-only pass uses its selected skill directly.

The [Grounding Protocol](references/GROUNDING_PROTOCOL.md) requires source support: no fabrication, no uncited numbers, and no unverified citations. The binding [role and authority statement](references/ROLE_AND_AUTHORITY.md) defines the harness's relationship to research governance and the status of its outputs.

Governed projects additionally use a section-level phase ladder: **Plan & Draft → Review & Revise → Iterate & Converge → Finalize & Close**. Project deliverables and revision phases are separate axes; the [phase protocol](references/PHASE_PROTOCOL.md) defines progression and its gates.

## Specialized capabilities and requirements

| Task | Additional requirement | Details |
| --- | --- | --- |
| Extract canonical PDF evidence or run scholarly evaluation | A conforming Poppler `pdftotext` installation | [PDF evidence requirements](references/DETERMINISTIC_CHECKS.md) |
| Discover references or audit claim coverage | A reachable Class 1 scholarly verifier; these operations no-op with `NO_REACHABLE_VERIFIER` when none is available | [External verifiers](references/EXTERNAL_VERIFIERS.md) |
| Finalize at Ph4 | A successful external-verifier probe | [Finalization requirements](skills/run-phase-4/SKILL.md) |
| Bind or check a reader policy's source corpus | Access to the policy's external corpus; these skills run only when invoked | [Centroid binding](skills/centroid-pass/SKILL.md) and [sentence checks](skills/centroid-sentence-logic/SKILL.md) |
| Bootstrap a governed project or write governed reports | A governed workspace and an authorized output destination | [Project bootstrap](references/PROJECT_BOOTSTRAP.md) |

### Set up a governed project

From the package root, initialize a new governed workspace at an explicitly named directory:

```text
python scripts/init_governed_workspace.py <workspace-dir>
```

Keep projects in its `outputs/co-author-harness/staging/<work-id>/<run-id>/` lane. Then follow [PROJECT_BOOTSTRAP.md](references/PROJECT_BOOTSTRAP.md): `scripts/native_project_bootstrap.py` creates the standard directories and mandatory graph-independent **reader-profile v2** binding. Use that bootstrap for native lifecycle ledgers. Governed writes without discoverable workspace governance are refused with `DEST-UNGOVERNED`.

Ordinary drafting outside a governed workspace and read-only checks need no governed workspace. Protected destinations inside an existing governed workspace retain their write restrictions under every run scope.

### Use an external reader corpus

The centroid skills require the corpus named by the [reader-accessibility policy](references/policies/reader_accessibility.v1.json). A dormant reader profile can receive its general binding packet without that corpus. Other bindings require the applicable source access.

When the corpus is mounted elsewhere, set `AGENT_WIKI_ROOT`, `AGENT_WORKSPACE_ROOT`, and, for a relocated package, `AGENT_HARNESS_ROOT`. Explicit `--wiki-root`, `--workspace-root`, and `--harness-root` arguments take precedence. See the [reader-policy architecture](docs/architecture/reader-policy-decoupling-c4.md) for the separation between reader binding and semantic-graph eligibility.

## Documentation

| I want to… | Start here |
| --- | --- |
| Find a supported command | [Command catalog](skills/plugin-commands/SKILL.md) |
| Draft or revise without setting up a project | [Ordinary-task workflow](references/PROJECT_INDEPENDENT_WORKFLOW.md) |
| Configure my host | [Codex](docs/agent-instructions/codex-host.md) · [Claude Code / Desktop / Cowork](references/CLAUDE_CODE_HOST.md) |
| Start or continue governed project work | [Operational primer](references/QUICKSTART.md) · [Routing guide](references/ROUTING_SPINE.md) |
| Understand the complete operation | [Operating manual](references/OPERATING_MANUAL.md) |
| Understand review findings and procedure | [Review orchestration](references/REVIEW_ORCHESTRATION.md) |
| Check invocation rules and precedence | [Root instructions](AGENTS.md) · [Package instructions](references/AGENTS.md) · [Governance guide](docs/agent-instructions/harness-governance.md) |
| Understand the package layout and history | [Architecture](docs/agent-instructions/harness-architecture.md) · [Consolidation history](docs/agent-instructions/harness-history.md) |

## Development and maintenance

Work from the repository root. For a scoped change, use the focused validators and direct smoketests in the [change-to-check map](docs/agent-instructions/change-to-check-map.md). The canonical structural checklist is in [AGENTS.md](AGENTS.md#maintainer--structural-checks-harness-root).

The fixture registry is the behavioral-test authority. Run the full corpus at release/qualification gates and after fixture-runner, census, cache, or registry-membership changes:

```text
python scripts/analysis/fixture_runner.py --no-write
```

Omit `--no-write` only when intentionally regenerating the committed fixture manifest after a fully green run. The [check guide](docs/agent-instructions/change-to-check-map.md#fixture-runtime-and-hosted-ci) covers partial suite runs, unavailable cases, and Linux runtime setup. For release packaging, use `scripts/release-gate.sh` with the flags documented in its header.

## Version and releases

[version.json](version.json) is the sole authority for the package's current name, version, and license. See the [changelog](CHANGELOG.md) for release history, [release notes](docs/release-notes/README.md) for packaging records, and [GitHub Releases](https://github.com/UtopianYoungChung/co-author-harness/releases) for downloads.

## License

Licensed under the **MIT License** (see [LICENSE](LICENSE)). Author: **Young Jo(seph) Chung** — `jo.chung@utoronto.ca`.
