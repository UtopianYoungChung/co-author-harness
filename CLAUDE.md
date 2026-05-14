# CLAUDE.md — Co-Author-Harness Root

> Deploy to: the harness root folder (`co-author-harness/CLAUDE.md` in this workspace).

**Scope.** This file governs all Claude (or any agent) activity under the `co-author-harness/` root folder. It is the root-level authority for every research project in this tree and the canonical home of the Research and Academic Paper Writing Package. It sets the rules for package invocation, project discovery, lifecycle management, and cross-project consistency.

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
| User invokes a skill (illustrative — full catalog at `/plugin-commands`) | `/run-draft`, `/run-iterate`, `/run-finalize`, legacy `/run-phase-*` compatibility commands, `/run-reflection`, `/run-generator-session`, `/quick-deterministic`, `/check-contradictions` |
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

---

## Agent dispatch guardrail (binding)

Phase-work checks — Evaluator Steps 0a–8.5 and Planner Phase 0 preflight — **MUST** be dispatched as the corresponding `co-author-harness-claude:*` subagent:

| Role | Agent type | Scope |
|------|------------|-------|
| Planner | `co-author-harness-claude:planner` | Phase 0 preflight, F6 dispatch plan, `phase_state.json` updates |
| Evaluator | `co-author-harness-claude:evaluator` | Steps 0a–8.5, findings, `convergence_journal.jsonl` |
| Generator | `co-author-harness-claude:generator` | Fix application after BLOCKER/MAJOR findings |
| Reflector (probe) | `co-author-harness-claude:reflector-probe` | Ad-hoc mid-round integrity probe (Ph1–Ph3) |
| Reflector (close-out) | `co-author-harness-claude:reflector-closeout` | Full five-phase reflection at Ph4 close |

**The orchestrating agent in the main conversation loop does not execute phase steps directly.** Applying harness rules from training-data recall instead of reading the authoritative plugin files is a Grounding Protocol violation (see `references/GROUNDING_PROTOCOL.md` Rule 1) and produces findings that cannot be distinguished from confabulation.

**Required reads before any phase-work check (Grounding Protocol Rule 1).** Every subagent must read these files in-session before acting — not from memory:

- `references/GROUNDING_PROTOCOL.md` — Rules 1–7 (absolute, no override)
- `references/REVIEW_ORCHESTRATION.md` — Steps 0a/0.2/0b/1–8.5 sequence
- `references/PHASE_PROTOCOL.md` — phase ladder, convergence window, terminal gate
- `references/SAFEGUARD_LAYER.md` — Sub-check A–H definitions
- `agents/evaluator.md` — Evaluator role and Output Contract (full read required)

**Optional mechanical enforcement.** `scripts/phase_write_guard.py` is a PreToolUse hook that fires a grounding reminder whenever `phase_state.json`, `.harness/evidence/`, or `.harness/events.jsonl` are about to be written. To install it in a paper project, add to the project's `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{ "type": "command", "command": "python <path-to-harness>/scripts/phase_write_guard.py" }]
      }
    ]
  }
}
```
