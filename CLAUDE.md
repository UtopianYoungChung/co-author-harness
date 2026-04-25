# CLAUDE.md — Co-Author-Harness Root

> Deploy to: the harness root folder (`co-author-harness/CLAUDE.md` in this workspace).

**Scope.** This file governs all Claude (or any agent) activity under the `co-author-harness/` root folder. It is the root-level authority for every research project in this tree and the canonical home of the Research and Academic Paper Writing Package (harness substrate at **v0.8.6**). It sets the rules for package invocation, project discovery, lifecycle management, and cross-project consistency.

**Relationship to the package substrate.** This file decides *when* and *how* the package is invoked. The substrate lives in `agents/`, `skills/`, `references/`, and `scripts/` — **Harness Root → Package Substrate → Component Files.** This root file does not duplicate orchestration rules inside those trees.

*Consolidation (Option C″, 2026-04-21):* this repo root (`co-author-harness/`, v0.8.6+; formerly `research-writing-harness/`) is canonical; former `paper-harness/` is retired. Full tree, ownership, and history: [docs/agent-instructions/harness-architecture.md](docs/agent-instructions/harness-architecture.md) and [docs/agent-instructions/harness-history.md](docs/agent-instructions/harness-history.md). Workspace contract: `../ROOT_ARCHITECTURE_INDEX.md`.

---

## Maintainer — structural checks (harness root)

From this directory, with Python 3 and PyYAML available:

```bash
python scripts/skill-check.py
python scripts/version-check.py
python scripts/catalog-check.py
python scripts/path-hygiene-check.py
```

For full release packaging (bash): `scripts/release-gate.sh` (see script header for flags).

---

## When the package is invoked (binding triggers)

The agent **must** read the package component files and follow the orchestration whenever:


| Trigger                                                                 | Example                                                                                                                                                      |
| ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| User asks for a review, edit, critique, or refinement of academic prose | "Review my draft," "Check this abstract," "Polish §4"                                                                                                        |
| User refers to the package by name or shorthand                         | "Run the master guidelines," "Use the style package," "Apply the writing rules"                                                                              |
| User pastes academic text and asks for feedback                         | (any draft + "what do you think?")                                                                                                                           |
| User asks to bootstrap a new research project                           | "Set up a new project for X," "Create the folder structure for Y"                                                                                            |
| User invokes an agent role                                              | "Run the planner," "Evaluate the manuscript," "Reflect on this round"                                                                                        |
| User invokes a skill                                                    | `/run-phase-1`, `/run-phase-2`, `/run-phase-3`, `/run-phase-3-stability`, `/run-phase-4`, `/run-reflection`, `/quick-deterministic`, `/check-contradictions` |
| User asks about project lifecycle or milestones                         | "Where is this project?", "What milestone am I at?", "What's next?"                                                                                          |


**When not triggered:** If the user asks about non-writing tasks (data analysis, coding, general Q&A), do not invoke the package unless the task involves producing or reviewing academic prose.

---

## Precedence (summary)

Order: **user → venue/advisor → project `CLAUDE.md` / `directives.md` → package files (`references/`, `agents/`, `skills/`) → package `references/CLAUDE.md` → this file.**  
`references/GROUNDING_PROTOCOL.md` is **absolute** (no fabrication, no uncited numbers, no unverified citations).  
Full ladder and cross-project rules: [docs/agent-instructions/harness-governance.md](docs/agent-instructions/harness-governance.md).

---

## Detailed instructions (progressive disclosure)


| Topic                                                 | File                                                                                     |
| ----------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Directory layout, ownership, unpacked snapshots       | [harness-architecture.md](docs/agent-instructions/harness-architecture.md)               |
| Consolidation footnote / ancestry (historical)        | [harness-history.md](docs/agent-instructions/harness-history.md)                         |
| Project discovery, phase ladder, bootstrap template   | [harness-discovery-lifecycle.md](docs/agent-instructions/harness-discovery-lifecycle.md) |
| Precedence ladder, cross-project rules (full)         | [harness-governance.md](docs/agent-instructions/harness-governance.md)                   |
| Supplements, modeling opt-in, Year 2026 project index | [harness-supplements-legacy.md](docs/agent-instructions/harness-supplements-legacy.md)   |
| What this file is not + canonical file index          | [harness-reference-index.md](docs/agent-instructions/harness-reference-index.md)         |


**Package invocation rules** inside the bundle: `references/CLAUDE.md`.