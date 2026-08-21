# Package AGENTS.md — Invocation Rules

**Typed output boundary.** `references/role_output_contract.json` 3.0.0 is the sole machine authority for the six fixed roles and nine triggered F1-F9 classes. Resolve trigger occurrence, context, cardinality, ordering, path, and typed suppression there. Legacy artifacts remain readable but never become shipment-v2 transaction evidence, application proof, or acceptance authority by presence.

**Scope.** This file governs how the executing agent invokes the **Research and Academic Paper Writing Package** when asked to review, edit, or critique academic writing. It sits **inside** the package folder and describes how the package is used; the **content rules themselves** live in the component files indexed by `MANIFEST.md`.

**Deployment.** Two common layouts: (1) **Embedded** — this content lives under `.paper-package/` (or equivalent) inside a Research tree; the Research-root `AGENTS.md` delegates here. (2) **Plugin root** — this `references/` folder sits under the published plugin workspace (for example `co-author-harness/`); treat the package root as that plugin root and resolve paths from there. Use the layout you actually opened; do not assume `.paper-package/` exists if you are already at the plugin root.

**Lifecycle scope.** This package governs the **full research lifecycle** — from project bootstrapping (M1) through final submission (M5). Pre-drafting milestones (M1–M3) are dispatched via `AGENT_ORCHESTRATION.md §10`; drafting and revision (M4–M5) follow the standard four-agent loop in §3.

**Lifecycle axes.** Per-section advancement uses the **Lifecycle-Phase Ladder** — **Ph1 Plan & Draft → Ph2 Review & Revise → Ph3 Iterate & Converge → Ph4 Finalize & Close** — defined in `PHASE_PROTOCOL.md` and recorded in `reviews/phase_state.json`. The unsplit M1–M5 milestone axis is orthogonal: milestones govern accepted dependency-bearing deliverables and policy-correct handoff representations under `MILESTONE_FEEDBACK_HANDOFF_PROTOCOL.md`; phases govern revision/readiness. Neither axis is absorbed into or renamed by the other. Ph4 admission remains MCR-gated: every in-scope section must satisfy the convergence/ceiling clauses and no section may be stale. Agent engagement is governed only by `policies/phase_engagement.v1.json`: the Evaluator runs a bounded independent pass at Ph1 and progressively broader passes through Ph4. The four-agent contract and Grounding Protocol are unchanged.

**Run scopes.** Every invocation declares exactly `adhoc_review`,
`lab_iteration`, or `full_lifecycle` under `FULL_RUN_CONTRACT.md`.
`lab_iteration` is transient proposal-only work in governed staging/private
shipment space; it has no lifecycle, F9, terminal, promotion, release, or
dissemination authority.

---

## 1. When this package is invoked

The agent uses this package whenever:

- The user asks for a review, edit, critique, or refinement of a manuscript, response letter, thesis chapter, course essay, abstract, or any other academic prose.
- The user refers to "the master guidelines," "the style package," "the master writing rules," or uses a slash-style shorthand.
- The user pastes an academic draft and asks for feedback.
- The user asks for a "joint review" or "comprehensive review" of a piece.
- The user asks to **bootstrap a new research project** (set up folder, start a project, create the structure).
- The user asks about **project lifecycle or milestones** (where is this project, what milestone, what's next).
- The user asks to **assess improvement or readiness** (is it ready, how much better, show me the metrics).

The parent `AGENTS.md` files already require this package for all such work. This file picks up from there.

**Agent mode.** When the user asks to "run the planner," "evaluate the manuscript," "co-author §6," "reflect on this round," or otherwise invokes a specific agent role, read `AGENT_ORCHESTRATION.md` first. It defines the four-agent system (Planner, Evaluator, Generator, Reflector) and the dispatch loop. Each agent's full prompt is in `agents/<role>.md`.

---

## 2. First step on every invocation

Two things are always-loaded; everything else is consulted on demand via `MANIFEST.md`.

1. **`GROUNDING_PROTOCOL.md`** — binding no-hallucination rules. Read in full, every session, before any other action. Cannot be overridden. Enforced mechanically by `scripts/audit/audit_citations.py` (PR-4a) against the stable `<a id="gp-N"></a>` anchors above each rule heading (PR-3a).
2. **`MANIFEST.md`** — routing index. Consult it once per task to determine which other reference files apply, then read those files in full when invoked. The routing table covers the common cases (review/edit, phase advancement, agent dispatch, bootstrapping, submission-bound depth, style commitments, etc.) and points to the canonical file for each.

`MANIFEST.md` is an **index, not a new authority layer.** It does not change which file wins a conflict — see §4 below.

**Do not skip MANIFEST.** Even for "small" edits the routing table tells you which subset of files applies. Reading the MASTER is not a substitute — the MASTER is a reference map; orchestration is the runbook.

---

## 3. Components of this package

The per-file inventory and per-task routing table moved to `MANIFEST.md` at v0.15.0-pre PR-4b to slim the always-loaded prelude. The component count, role classification, and "when authoritative" semantics are unchanged; only the location moved.

If you are inheriting this package cold, the fastest path is: read `GROUNDING_PROTOCOL.md` → read `MANIFEST.md` → read the files MANIFEST routes you to for the task at hand.

---

## 4. Precedence rules (conflict resolution)

When two sources disagree:

1. **User's explicit instruction in the current conversation** wins over everything else in this list.
2. **Venue author guide / call for papers / publisher template** wins over the package.
3. **Advisor or instructor instruction** wins over the package.
4. **Project-specific supplements** (e.g. `CAiSE_Rev01/research_notes/review/lessons_caise_revision.md`) win **within their project** over the package's cross-venue rules.
5. **Component files** win over the MASTER until the MASTER is reconciled (per MASTER §Policy).
6. **MASTER** wins over the orchestration and deterministic-checks files when a rule is in dispute (since MASTER carries the traceability matrix).
7. Default behavior.

When in doubt, name the conflict in the findings report and ask the user.

**Note on `GROUNDING_PROTOCOL.md`.** The Grounding Protocol sits **above** this precedence ladder — no instruction at any level (including user instruction) authorises fabricating a citation, claiming a file contains something it does not, or skipping a required verification. See `GROUNDING_PROTOCOL.md` Status and Scope.

---

## 5. Do not skip steps

- **Even "small" revisions invoke the orchestration file.** Small revisions are where violations arrive most often (this is an observed pattern, not a theoretical worry).
- **Even if you remember the rules,** read the component file you're citing. Rules evolve; memory drifts.
- **Even if the piece looks "fine,"** invoke the deterministic audit (`scripts/audit/run_all.py`, per PR-2) once. It takes seconds and catches the measurable tics.

---

## 6. What this file is NOT

- **Not** a rule source. Rules live in the component files indexed by `MANIFEST.md`.
- **Not** project-specific. Project-specific guidance lives in the parent `AGENTS.md` files and in project `research_notes/` folders.
- **Not** a substitute for reading the orchestration file.
- **Not** a substitute for `MANIFEST.md`. AGENTS.md says *what this package is*; MANIFEST says *which files to read for your task*.
