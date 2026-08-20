# AGENTS.md — Co-Author-Harness Root

> Deploy to: the harness root folder (`co-author-harness/AGENTS.md` in this workspace).

**Scope.** This file governs activity of the executing agent under this package root. It is the canonical home of the Research and Academic Paper Writing Package. It sets the rules for package invocation, project discovery, lifecycle management of instrument behaviour, and cross-project consistency of instrument behaviour. Role and authority: `references/ROLE_AND_AUTHORITY.md` (binding).

**Single-branch policy (binding).** `main` is the repository's only permitted
branch. Commit all past, present, and future project work directly to `main`; do
not create or push feature, release, agent, patch, or distribution branches.
Clean-checkout verification may use a temporary **detached** worktree, which must
be removed after its receipts are copied back. Before deleting a legacy branch,
first prove its tip is reachable from `main` so no committed history is lost.

**Authoritative version.** `version.json` is the single source of truth for the package's **current** version, name, and license. `.claude-plugin/plugin.json` is a retired Claude host manifest and is not required. Descriptive prose must not manually mirror the current version — point readers at the manifest instead. Two things are *not* violations of this rule, because neither claims to be the current version: **historical release identifiers** (`CHANGELOG.md` headings, `docs/release-notes/`, release-history tables — records of what shipped), and **mechanical manifest parity** (`.claude-plugin/marketplace.json`, gated by `scripts/version-check.py`, because both manifests ship inside the `.plugin` ZIP and the loader rejects the install when they disagree). Enforced by `scripts/version-check.py`; pinned by `scripts/version_policy_smoketest.py`.

**Relationship to the package substrate.** This file decides *when* and *how* the package is invoked. The substrate lives in `agents/`, `skills/`, `references/`, and `scripts/` — **Harness Root → Package Substrate → Component Files.** This root file does not duplicate orchestration rules inside those trees.

**Producer boundary (binding, revised 2026-07-22).** The harness is a producer,
not a decision maker. It may write private Stage reports, evidence, and
manifests only inside an active research package's exact lane
`research\60_Workbench\<work-id>\reviews\.harness\shipments\<shipment-id>\`.
Those bytes remain scratch/private and imply no acceptance, registration,
promotion, or authoritative-state update. All other governed consumer paths
remain protected; research governance alone may apply a user-authorized,
path-and-hash-bounded change beyond the shipment lane (contract:
`research/10_Governance/HARNESS_SHIPMENT_BOUNDARY.md`; routing:
`governance/output-routing/`). Writable harness destinations are therefore
this package root, the governed staging lane
`<governed-workspace-root>\outputs\co-author-harness\staging\<work-id>\<run-id>\`, and the exact private
shipment lane above. Script writers resolve destinations through
`scripts/destination_capability.py` (`DEST-MISROUTED` for package-local project
output; `DEST-PROTECTED` refusal; `DEST-UNGOVERNED` fail-closed without
discoverable workspace governance).
The lookalike path `co-author-harness/outputs/co-author-harness/` is forbidden:
project output must never become package state or make one project a governing
body for the harness.

*Consolidation (Option C″, 2026-04-21):* this repo root (`co-author-harness/`; formerly `research-writing-harness/`) is canonical; former `paper-harness/` is retired. Full tree, ownership, and history: [docs/agent-instructions/harness-architecture.md](docs/agent-instructions/harness-architecture.md) and [docs/agent-instructions/harness-history.md](docs/agent-instructions/harness-history.md). Workspace contract: `../ROOT_ARCHITECTURE_INDEX.md`.

---

## Maintainer — structural checks (harness root)

From this directory, with Python 3, PyYAML, and jsonschema available:

```bash
python scripts/skill-check.py
python scripts/schema_runtime_check.py
python scripts/version-check.py
python scripts/distribution-rights-check.py
python scripts/catalog-check.py
python scripts/command_surface_check.py
python scripts/path-hygiene-check.py
python scripts/snippet-check.py
python scripts/output_economy_check.py
python scripts/version-planes-check.py
python scripts/commitment-interactions-check.py
python scripts/phase_engagement_check.py
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
| **User asks for a whole-lifecycle run or an academic deliverable** — read `references/FULL_RUN_CONTRACT.md` **first** | "Harness full run," "full harness run," "draft me a short essay," "draft the whole paper," "run the ladder," "ship this" |
| User asks for a review, edit, critique, or refinement of academic prose | "Review my draft," "Check this abstract," "Polish §4"                                                                                                        |
| User refers to the package by name or shorthand                         | "Run the master guidelines," "Use the style package," "Apply the writing rules"                                                                              |
| User pastes academic text and asks for feedback                         | (any draft + "what do you think?")                                                                                                                           |
| User asks to bootstrap a new research project                           | "Set up a new project for X," "Create the folder structure for Y"                                                                                            |
| User asks to build, extend, formalize, or audit a BFO-aligned ontology  | "Build this BFO domain ontology," "Audit these ontology definitions," "Formalize this taxonomy"                                                             |
| User invokes an agent role                                              | "Run the planner," "Evaluate the manuscript," "Reflect on this round"                                                                                        |
| User invokes a skill (illustrative — full catalog at `/plugin-commands`) | `/run-draft`, `/run-iterate`, `/run-finalize`, `/run-reflection`, `/quick-deterministic`, `/check-contradictions` |
| User asks about project lifecycle or milestones                         | "Where is this project?", "What milestone am I at?", "What's next?"                                                                                          |


**When not triggered:** If the user asks about non-writing tasks (data analysis, coding, general Q&A), do not invoke the package unless the task involves producing or reviewing academic prose.

**No project, no prose (binding).** A prose-producing request with no project root or no resolved `reviews/assignment_contract.json` **fails closed**: do not write academic prose (not in the project, not outside it, not as a "quick draft"), do not substitute a task checklist for milestone state, and do not treat a missing scaffold as licence to proceed informally. Respond with the bootstrap instruction. A full-lifecycle run may never be downgraded to a lightweight/response-only subpass, and terminal language ("Ph4," "G.4," "terminal PASS," "ladder complete," "converged," "shipped") requires `python scripts/full_run_contract_check.py terminal --project-root <p>` to exit 0. Rules and error codes: `references/FULL_RUN_CONTRACT.md` — normative there, not restated here.

**Run scope (binding).** Declare exactly `adhoc_review`, `lab_iteration`, or
`full_lifecycle`; every child inherits the declaration exactly. A
`lab_iteration` is transient proposal-only work at a resolved governed
staging/private-shipment destination. It has no lifecycle, F9, terminal,
promotion, release, or dissemination authority and never writes authoritative
research. Mechanical authority and stable diagnostics live in
`references/FULL_RUN_CONTRACT.md` and `scripts/invocation_scope.py`.

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
| Role and authority (binding)                          | [ROLE_AND_AUTHORITY.md](references/ROLE_AND_AUTHORITY.md)                                |
| Directory layout, ownership, unpacked snapshots       | [harness-architecture.md](docs/agent-instructions/harness-architecture.md)               |
| Consolidation footnote / ancestry (historical)        | [harness-history.md](docs/agent-instructions/harness-history.md)                         |
| Project discovery, phase ladder, bootstrap template   | [harness-discovery-lifecycle.md](docs/agent-instructions/harness-discovery-lifecycle.md) |
| Precedence ladder, cross-project rules (full)         | [harness-governance.md](docs/agent-instructions/harness-governance.md)                   |
| Supplements, modeling opt-in, Year 2026 project index | [harness-supplements-legacy.md](docs/agent-instructions/harness-supplements-legacy.md)   |
| What this file is not + canonical file index          | [harness-reference-index.md](docs/agent-instructions/harness-reference-index.md)         |


**Package invocation rules** inside the bundle: `references/CLAUDE.md`.

## Imported Claude Cowork project instructions
