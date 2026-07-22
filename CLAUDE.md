# CLAUDE.md — Co-Author-Harness Root

> Deploy to: the harness root folder (`co-author-harness/CLAUDE.md` in this workspace).

**Scope.** This file governs all Claude (or any agent) activity under the `co-author-harness/` root folder. It is the root-level authority for every research project in this tree and the canonical home of the Research and Academic Paper Writing Package. It sets the rules for package invocation, project discovery, lifecycle management, and cross-project consistency.

**Authoritative version.** `.claude-plugin/plugin.json` is the single source of truth for the plugin's version, name, description, and keywords. No prose document in this tree asserts a version number; consult the manifest.

**Relationship to the package substrate.** This file decides *when* and *how* the package is invoked. The substrate lives in `agents/`, `skills/`, `references/`, and `scripts/` — **Harness Root → Package Substrate → Component Files.** This root file does not duplicate orchestration rules inside those trees.

*Consolidation (Option C″, 2026-04-21):* this repo root (`co-author-harness/`; formerly `research-writing-harness/`) is canonical; former `paper-harness/` is retired. Full tree, ownership, and history: [docs/agent-instructions/harness-architecture.md](docs/agent-instructions/harness-architecture.md) and [docs/agent-instructions/harness-history.md](docs/agent-instructions/harness-history.md). Workspace contract: `../ROOT_ARCHITECTURE_INDEX.md`.

---

## Producer boundary (binding, 2026-07-22)

The harness is a **producer, not a decision maker**. For any destination under a governed workspace root outside this package (in this workspace: `research/`, `knowledge/`, `governance/`, and every other governed surface), the harness reads only explicitly allowlisted inputs and returns path-and-hash-bounded shipments; it never writes, registers, promotes, adjudicates, or updates authoritative state there. Contract: `research/10_Governance/HARNESS_SHIPMENT_BOUNDARY.md`; routing: `governance/output-routing/`.

- Writable destinations are exactly: this package root (repo rules) and the governed staging lane `outputs/co-author-harness/staging/<work-id>/<run-id>/`.
- Every script writer resolves destinations through `scripts/destination_capability.py`: a protected destination refuses with `DEST-PROTECTED`; an install without discoverable workspace governance fails closed (`DEST-UNGOVERNED`) for all non-package writes.
- This binds agent-directed writes with general file tools exactly as it binds scripts: do not create, modify, move, rename, or delete any path under a protected root, and never infer authority from a harness verdict, phase label, terminal PASS, or artifact quality.

---

## Maintainer — structural checks (harness root)

From this directory, with Python 3 and PyYAML available:

```bash
python scripts/skill-check.py
python scripts/version-check.py
python scripts/distribution-rights-check.py
python scripts/catalog-check.py
python scripts/command_surface_check.py
python scripts/path-hygiene-check.py
python scripts/snippet-check.py
python scripts/output_economy_check.py
python scripts/version-planes-check.py
python scripts/commitment-interactions-check.py
python scripts/retirement-sweep-check.py
python scripts/destination-coverage-check.py
python scripts/analysis/fixture_infrastructure_check.py
python scripts/analysis/fixture_runner.py --no-write
```

The fixture registry is the single behavioral-test authority. Omit
`--no-write` only when intentionally regenerating the committed fixture
manifest after a fully green run.

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
| User asks to build, extend, formalize, or audit a BFO-aligned ontology  | "Build this BFO domain ontology," "Audit these ontology definitions," "Formalize this taxonomy"                                                             |
| User invokes an agent role                                              | "Run the planner," "Evaluate the manuscript," "Reflect on this round"                                                                                        |
| User invokes a skill (illustrative — full catalog at `/plugin-commands`) | `/run-draft`, `/run-iterate`, `/run-finalize`, `/run-reflection`, `/run-generator-session`, `/quick-deterministic`, `/check-contradictions` |
| User asks about project lifecycle or milestones                         | "Where is this project?", "What milestone am I at?", "What's next?"                                                                                          |


**When not triggered:** If the user asks about non-writing tasks (data analysis, coding, general Q&A), do not invoke the package unless the task involves producing or reviewing academic prose.

**Formal ontology trigger:** For the BFO-aligned ontology trigger, read `references/BFO_ONTOLOGY_DESIGN.md`. Its trigger boundary is binding: do not apply formal BFO construction rules merely because prose uses philosophical ontology, conceptual analysis, modeling vocabulary, or metaphor.

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
