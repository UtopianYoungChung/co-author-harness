# CLAUDE.md — Research Root
# Deploy to: the Research root folder (e.g., Research\CLAUDE.md)

**Scope.** This file governs all Claude (or any agent) activity under the Research root folder. It is the root-level authority for every research project in this tree. It delegates substantive academic writing work to the **Research and Academic Paper Writing Package** and sets the rules for project discovery, lifecycle management, and cross-project consistency.

**Relationship to Package CLAUDE.md.** This file decides *when* and *how* the package is invoked. The Package CLAUDE.md (`.paper-package/CLAUDE.md`) decides *what happens once inside the package*. The two files form a delegation chain: Research Root → Package → Component Files.

---

## 1. Package location

```
.paper-package/
```

(Relative to this Research root. The package lives inside the Research directory itself, so any session mounted at `Research/` or any of its subfolders can reach it.)

All academic writing rules, review orchestration, agent prompts, skills, safeguard checks, and grounding constraints live inside this package. This root file does **not** duplicate them.

---

## 2. When the package is invoked (binding triggers)

The agent **must** read the Package CLAUDE.md and follow the orchestration files whenever:

| Trigger | Example |
|---|---|
| User asks for a review, edit, critique, or refinement of academic prose | "Review my draft," "Check this abstract," "Polish §4" |
| User refers to the package by name or shorthand | "Run the master guidelines," "Use the style package," "Apply the writing rules" |
| User pastes academic text and asks for feedback | (any draft + "what do you think?") |
| User asks to bootstrap a new research project | "Set up a new project for X," "Create the folder structure for Y" |
| User invokes an agent role | "Run the planner," "Evaluate the manuscript," "Reflect on this round" |
| User invokes a skill | "/check-contradictions," "/quick-deterministic," "/run-tier-standard" |
| User asks about project lifecycle or milestones | "Where is this project?", "What milestone am I at?", "What's next?" |

**When not triggered:** If the user asks about non-writing tasks (data analysis, coding, general Q&A), do not invoke the package unless the task involves producing or reviewing academic prose.

---

## 3. Project discovery

Research projects live as immediate children of this Research root or in a structured subdirectory. The agent should recognize a research project by the presence of any of these markers:

| Marker | Meaning |
|---|---|
| `CLAUDE.md` in the project folder | Project-specific configuration exists |
| `manuscript/` directory | A draft is in progress |
| `reviews/` directory | A review round has been run |
| `research_notes/` directory | Project memory exists |
| A `.tex` or `.md` or `.docx` file matching a paper title | A manuscript exists even without full structure |

When a user names a project (e.g., "the agency delegation paper"), the agent should search for it under this root. If ambiguous, ask.

---

## 4. Lifecycle governance

Every research project under this root follows the **full lifecycle** defined in the package. The lifecycle has two phases:

### Phase A: Pre-drafting (Milestones 1–3)

Governed by `general_research_project_guidelines.md` and `AGENT_ORCHESTRATION.md §10` (Lifecycle Dispatch).

| Milestone | Artifact | Agent responsible |
|---|---|---|
| M1 — Project Memo | `research_notes/project_memo.md` | Planner (classify + plan) → Generator (draft memo) → Evaluator (review against M1 criteria) |
| M2 — Annotated References | `research_notes/annotated_references.md` | Planner (plan) → Generator (draft annotations) → Evaluator (check contribution-to-tension) |
| M3 — Structured Outline | `manuscript/outline.md` | Planner (plan) → Generator (draft outline) → Evaluator (review skeleton + arc) |

### Phase B: Drafting and revision (Milestones 4–5)

Governed by `REVIEW_ORCHESTRATION.md` and `AGENT_ORCHESTRATION.md §3` (The Loop).

| Milestone | Artifact | Agent responsible |
|---|---|---|
| M4 — Paper Draft | `manuscript/main.md` (or `main.tex`) | Full four-agent loop: Planner → Evaluator → Generator → Reflector |
| M5 — Final Paper | `manuscript/main.md` (submission-bound) | Full four-agent loop at `submission-bound` depth + G.4 sign-off |

The Planner determines the current milestone by reading the project state. The user can override.

---

## 5. Precedence rules (root level)

When sources disagree, this hierarchy applies (most authoritative first):

1. **User's explicit instruction in the current conversation.**
2. **Venue author guide / call for papers / publisher template.**
3. **Advisor or instructor instruction.**
4. **Project-specific CLAUDE.md or `research_notes/directives.md`** — wins within that project over the package's cross-venue rules.
5. **Package component files** — win over the MASTER until reconciled (per MASTER §Policy).
6. **Package MASTER** — wins over orchestration and meta-infrastructure when a rule is in dispute.
7. **This file** — wins over default behavior but loses to everything above.

This hierarchy is identical to Package CLAUDE.md §4 with one addition: this root file explicitly positions itself at level 7.

---

## 6. Cross-project consistency rules

When the agent works on multiple projects in one session or across sessions:

| Rule | Rationale |
|---|---|
| **Do not bleed directives.** A directive recorded in Project A's `research_notes/directives.md` does not apply to Project B unless explicitly stated. | Projects may have conflicting venue requirements. |
| **Package-level lessons apply everywhere.** Lessons recorded in `Package/research_notes/lessons_learned.md` (if it exists) or in the Reflector's package-level outputs apply to all projects. | Package lessons are cross-project by definition. |
| **Skills are scoped by tier.** Package-level skills apply everywhere; project-level skills apply only to their project. The Reflector decides the tier at creation time. | See `SKILL_REGISTRY.md` for the three tiers. |
| **Grounding Protocol is universal.** `GROUNDING_PROTOCOL.md` applies to every project, every session, every agent, no exceptions. | Integrity is not project-specific. |

---

## 7. Bootstrapping a new project

When the user asks to start a new research project, the agent reads `PROJECT_BOOTSTRAP.md` (in the package) and follows its protocol. The bootstrapping protocol creates the standard directory structure, seeds the project CLAUDE.md, and dispatches the Planner for initial classification.

**Quick reference — the standard project structure:**

```
<project-name>/
├── CLAUDE.md                     # Project-specific config
├── manuscript/
│   ├── main.md (or main.tex)     # The manuscript
│   ├── outline.md                # Structural outline (M3)
│   └── revision_log.md           # Append-only change log
├── reviews/
│   ├── classification.md         # Paper type, P-stage, venue, depth
│   ├── revision_plan.md          # Current action list
│   ├── step_0a_deterministic.md  # Mechanical pre-flight results
│   ├── step_findings/            # Per-step findings (Steps 1–7)
│   ├── consolidated_findings_report.md
│   ├── safeguard_layer_results.md
│   ├── G4_signoff.md             # Submission-bound only
│   ├── reflection_report.md      # Reflector output
│   └── DO_NOT_DISTURB.md         # Frozen rules (append-only)
├── research_notes/
│   ├── project_memo.md           # M1 artifact
│   ├── annotated_references.md   # M2 artifact
│   ├── directives.md             # User overrides + advisor instructions
│   └── lessons_learned.md        # Reflector-maintained project memory
└── skills/                       # Project-level skills (if any)
```

---

## 8. What this file is NOT

- **Not** a rule source. Rules live in the package component files.
- **Not** a substitute for reading the package orchestration files. This file delegates; it does not replicate.
- **Not** project-specific. Project-specific guidance lives in each project's own CLAUDE.md and `research_notes/` folder.

---

## 9. Related files

| File | Location | Role |
|---|---|---|
| Package CLAUDE.md | `.paper-package/CLAUDE.md` | Package invocation rules |
| AGENT_ORCHESTRATION.md | `.paper-package/AGENT_ORCHESTRATION.md` | Four-agent architecture + lifecycle dispatch |
| REVIEW_ORCHESTRATION.md | `.paper-package/REVIEW_ORCHESTRATION.md` | Review pipeline runbook |
| PROJECT_BOOTSTRAP.md | `.paper-package/PROJECT_BOOTSTRAP.md` | New project setup protocol |
| GROUNDING_PROTOCOL.md | `.paper-package/GROUNDING_PROTOCOL.md` | Binding no-hallucination rules |
| Year 2026 CLAUDE.md | Year 2026 root `CLAUDE.md` (peer folder, not under this Research root) | Year-level project notes (peer file, not parent) |

---

*Last updated: 2026-04-12. Package location updated to `.paper-package/` (Option B deployment inside Research root). Created as the Research-root harness entry point. Delegates all academic writing work to the Package.*
