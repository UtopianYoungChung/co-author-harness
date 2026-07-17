# AGENTS.md — Co-Author-Harness Root

> Deploy to: the harness root folder (`co-author-harness/AGENTS.md` in this workspace).

**Scope.** This file governs all Codex (or any agent) activity under the `co-author-harness/` root folder. It is the root-level authority for every research project in this tree and the canonical home of the Research and Academic Paper Writing Package. It sets the rules for package invocation, project discovery, lifecycle management, and cross-project consistency.

**Authoritative version.** `.claude-plugin/plugin.json` is the single source of truth for the plugin's version, name, description, and keywords. No prose document in this tree asserts a version number; consult the manifest.

**Relationship to the package substrate.** This file decides *when* and *how* the package is invoked. The substrate lives in `agents/`, `skills/`, `references/`, and `scripts/` — **Harness Root → Package Substrate → Component Files.** This root file does not duplicate orchestration rules inside those trees.

*Consolidation (Option C″, 2026-04-21):* this repo root (`co-author-harness/`; formerly `research-writing-harness/`) is canonical; former `paper-harness/` is retired. Full tree, ownership, and history: [docs/agent-instructions/harness-architecture.md](docs/agent-instructions/harness-architecture.md) and [docs/agent-instructions/harness-history.md](docs/agent-instructions/harness-history.md). Workspace contract: `../ROOT_ARCHITECTURE_INDEX.md`.

---

## Maintainer — structural checks (harness root)

From this directory, with Python 3 and PyYAML available:

```bash
python scripts/skill-check.py
python scripts/version-check.py
python scripts/catalog-check.py
python scripts/path-hygiene-check.py
python scripts/snippet-check.py
python scripts/output_economy_check.py
python scripts/output_economy_smoketest.py
python scripts/version-planes-check.py
python scripts/commitment-interactions-check.py
python scripts/retirement-sweep-check.py
```

For full release packaging (bash): `scripts/release-gate.sh` (see script header for flags).

---

## When the package is invoked (binding triggers)

The agent **must** read the package component files and follow the orchestration whenever:


| Trigger                                                                 | Example                                                                                                                                                      |
| ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **User asks for a whole-lifecycle run or an academic deliverable** — read `references/FULL_RUN_CONTRACT.md` **first** | "Harness full run," "full harness run," "draft me a short essay," "draft the whole paper," "run the ladder," "ship this" |
| User asks for a review, edit, critique, or refinement of academic prose | "Review my draft," "Check this abstract," "Polish §4"                                                                                                        |
| User refers to the package by name or shorthand                         | "Run the master guidelines," "Use the style package," "Apply the writing rules"                                                                              |
| User pastes academic text and asks for feedback                         | (any draft + "what do you think?")                                                                                                                           |
| User asks to bootstrap a new research project                           | "Set up a new project for X," "Create the folder structure for Y"                                                                                            |
| User asks to build, extend, formalize, or audit a BFO-aligned ontology  | "Build this BFO domain ontology," "Audit these ontology definitions," "Formalize this taxonomy"                                                             |
| User invokes an agent role                                              | "Run the planner," "Evaluate the manuscript," "Reflect on this round"                                                                                        |
| User invokes a skill (illustrative — full catalog at `/plugin-commands`) | `/run-draft`, `/run-iterate`, `/run-finalize`, legacy `/run-phase-*` compatibility commands, `/run-reflection`, `/run-generator-session`, `/quick-deterministic`, `/check-contradictions` |
| User asks about project lifecycle or milestones                         | "Where is this project?", "What milestone am I at?", "What's next?"                                                                                          |


**When not triggered:** If the user asks about non-writing tasks (data analysis, coding, general Q&A), do not invoke the package unless the task involves producing or reviewing academic prose.

**No project, no prose (binding).** A prose-producing request with no project root or no resolved `reviews/assignment_contract.json` **fails closed**: do not write academic prose (not in the project, not outside it, not as a "quick draft"), do not substitute a task checklist for milestone state, and do not treat a missing scaffold as licence to proceed informally. Respond with the bootstrap instruction. A full-lifecycle run may never be downgraded to a lightweight/response-only subpass, and terminal language ("Ph4," "G.4," "terminal PASS," "ladder complete," "converged," "shipped") requires `python scripts/full_run_contract_check.py terminal --project-root <p>` to exit 0. Rules and error codes: `references/FULL_RUN_CONTRACT.md` — normative there, not restated here.

**Formal ontology trigger:** For the BFO-aligned ontology trigger, read `references/BFO_ONTOLOGY_DESIGN.md`. Its trigger boundary is binding: do not apply formal BFO construction rules merely because prose uses philosophical ontology, conceptual analysis, modeling vocabulary, or metaphor.

---

## Precedence (summary)

Order: **user → venue/advisor → project `AGENTS.md` / `directives.md` → package files (`references/`, `agents/`, `skills/`) → package `references/CLAUDE.md` → this file.**  
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

## Imported Claude Cowork project instructions
