# Package CLAUDE.md — Invocation Rules

**Scope.** This file governs how Claude (or any agent) invokes the **Research and Academic Paper Writing Package** when asked to review, edit, or critique academic writing. It sits **inside** the package folder and describes how the package is used; the **content rules themselves** live in the component files indexed by `MANIFEST.md`.

**Deployment.** Two common layouts: (1) **Embedded** — this content lives under `.paper-package/` (or equivalent) inside a Research tree; the Research-root `CLAUDE.md` delegates here. (2) **Plugin root** — this `references/` folder sits under the published plugin workspace (for example `co-author-harness/`); treat `${CLAUDE_PLUGIN_ROOT}` as that plugin root and resolve paths from there. Use the layout you actually opened; do not assume `.paper-package/` exists if you are already at the plugin root.

**Lifecycle scope.** This package governs the **full research lifecycle** — from project bootstrapping (M1) through final submission (M5). Pre-drafting milestones (M1–M3) are dispatched via `AGENT_ORCHESTRATION.md §10`; drafting and revision (M4–M5) follow the standard four-agent loop in §3.

**Lifecycle-Phase Ladder (v0.7.4).** From v0.6.0 onward, per-section advancement is arbitrated by the **Lifecycle-Phase Ladder** — **Ph1 Plan & Draft → Ph2 Review & Revise → Ph3 Iterate & Converge → Ph4 Finalize & Close** — defined in `PHASE_PROTOCOL.md` (renamed from `TIER_PROTOCOL.md` at v0.7.4) and governed by a per-section ledger at `reviews/phase_state.json` (18-field `SectionStateObject`, 7-field log row, 31-trigger enum). The M1–M5 narrative remains the lifecycle framing for project bootstrap and pre-drafting work; the Ph1–Ph4 ladder is the review-and-edit arbitration surface. The two are compatible (M1+M2+M3 absorbed at Ph1; M4a at Ph2; M4b at Ph3; M5 at Ph4). Ph4 admission is gated by the **Manuscript Convergence Report (MCR)**: every section must reach `current_phase: Ph3_converged` and no section may carry a computed `[Ph3-STALE]` flag. Agent engagement is phase-conditioned: Evaluator dormant at Ph1, joins at Ph2, full four-agent loop at Ph3/Ph4. The four-agent contract and the Grounding Protocol are unchanged. (The v0.7.1 SD/SR opt-in gate was retired at v0.11.0.)

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

The parent CLAUDE.md files already require this package for all such work. This file picks up from there.

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
- **Not** project-specific. Project-specific guidance lives in the parent CLAUDE.md files and in project `research_notes/` folders.
- **Not** a substitute for reading the orchestration file.
- **Not** a substitute for `MANIFEST.md`. CLAUDE.md says *what this package is*; MANIFEST says *which files to read for your task*.
