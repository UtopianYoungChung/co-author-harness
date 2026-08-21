# PARALLEL_CONDUCTOR — Multi-Project and Multi-Phase Concurrency

**Purpose.** This file defines how the package handles *concurrent* work: multiple research projects in flight at once, multiple phases executing in parallel on a single project, and the isolation guarantees that keep these from corrupting each other. It is the academic-writing analogue of gstack's `conductor.json` and the Conductor tool for parallel Claude Code sessions.

**Why this matters.** A PhD student's real operating context is rarely serial. A typical week involves a conference revision (Ship phase on Project A), a new course paper in early ideation (Think phase on Project B), and a long-running thesis chapter (Build phase on Project C), *plus* teaching and research-assistant obligations. The package has, until now, assumed one project at a time. Concurrency was technically possible — the project-scoped directive rule in `RESEARCH_ROOT_CLAUDE.md` §6 explicitly forbids directive bleed — but the machinery for running multiple rounds safely in one calendar window was implicit. This file makes it explicit.

**Trade-off acknowledged up front.** Parallelism increases throughput but erodes the *coherent mental model* that a single-threaded serial workflow preserves. The operating point chosen here is: *parallelism at the project level is cheap and encouraged; parallelism within a single project is expensive and restricted.*

---

## 1. Concurrency levels

The package distinguishes four concurrency levels, each with different isolation requirements.

| Level | Description | Isolation surface | Permitted? |
|-------|-------------|-------------------|------------|
| **L0 — Serial** | One round, one project, one agent at a time. | None needed. | Always. |
| **L1 — Cross-project parallel** | Multiple projects, each at its own phase, one round each in flight. | Project directory + `research_notes/directives.md` per project. | Yes (default concurrency model). |
| **L2 — Intra-project cross-phase parallel** | One project, two phases running concurrently (e.g., Reflector on Round N while Planner begins Round N+1). | Phase-scoped file locks on `reviews/` subpaths. | Yes, with the constraints in §4. |
| **L3 — Intra-phase parallel** | One project, one phase, multiple agents running concurrently (e.g., two Evaluators on two different sections). | Section-scoped manuscript locks; findings-file namespace partitioning. | Experimental; see §5. |

L1 is the default and the most common real-world case. L2 is permitted at submission crunches. L3 is discouraged outside of clearly-segmentable large manuscripts.

---

## 2. The conductor file (`conductor.md` per root)

Each Research root maintains a live `conductor.md` at its root (e.g., `Research/conductor.md`). This file is the current-state ledger for all projects in the tree. It is *not* a rule file — it is a dashboard that the Planner reads at session start and updates at session end.

**Canonical structure.**

```markdown
# conductor.md — <root name> concurrency ledger

*Updated: YYYY-MM-DD HH:MM by <session-id>*

## Active projects

| Project | Current phase | Round # | Last agent | Next expected | Blocker? | Owner |
|---------|---------------|---------|------------|---------------|----------|-------|
| CAiSE_Rev01 | Ship (M5) | 7 | Evaluator (G.4 in progress) | User sign-off | — | Joseph |
| INF3001H_thesis_ch2 | Build (M4) | 2 | Generator | Evaluator review | — | Joseph |
| RE2026_agency_delegation | Think (M1) | 1 | Planner | Generator memo draft | — | Joseph |

## Frozen projects (do-not-touch)

| Project | Reason | Unfreeze condition |
|---------|--------|--------------------|
| INF2205_MLOps | Course complete; archival only | User directive |

## Directive scope declarations

| Directive | Project scope | Expires |
|-----------|---------------|---------|
| D-01 (CAiSE authority-pattern rule) | CAiSE_Rev01 only | End of revision |
| (package-level) GROUNDING_PROTOCOL Rule 7a | All projects | Permanent |

## Recent handoffs (last 7 days)

- 2026-04-12 — CAiSE_Rev01 Round 6 closed; Reflector produced reflection_report; 2 lessons added.
- 2026-04-11 — INF3001H_thesis_ch2 Round 1 closed; Evaluator findings merged.
- 2026-04-10 — RE2026_agency_delegation bootstrapped; M1 memo draft in progress.
```

**Update discipline.** The Planner updates `conductor.md` at three points per session: (1) on session entry, (2) at every user checkpoint, (3) at session exit. Missing updates are recoverable from `reviews/revision_plan.md` timestamps across projects but cost time.

---

## 3. L1 — Cross-project parallel operation

**Default concurrency model.** Each project is a logically isolated unit. The invariants:

- Every project has its own `AGENTS.md`, `manuscript/`, `reviews/`, `research_notes/`, and (optionally) `skills/`.
- Directives are project-scoped unless explicitly marked package-level (see `RESEARCH_ROOT_CLAUDE.md` §6).
- Lessons in a project's `research_notes/lessons_learned.md` stay in that project. Package-level lessons (recorded by the Reflector in the package repo) apply everywhere.
- Skills are tiered (Package / Project / Global per `SKILL_REGISTRY.md`). Project skills do not cross projects.
- `DO_NOT_DISTURB.md` is project-scoped by default; a user can declare a frozen rule package-level by filing it in `.paper-package/DO_NOT_DISTURB_PACKAGE.md` (create on first use).

**What the Planner does on every invocation.** Reads `conductor.md`; identifies which project the current utterance concerns (by explicit name, by recent activity, or by asking); loads that project's `AGENTS.md` and `research_notes/directives.md`; proceeds in L0 mode within that project.

**What is forbidden.** Silent cross-project directive application. If the Planner notices a pattern in Project A that seems to apply to Project B, it does not propagate it automatically; it files a Reflector-level note proposing a package-level directive for user approval.

---

## 4. L2 — Intra-project cross-phase parallel operation

**When to use.** A round's Reflect phase is long (Reflector is consolidating lessons, auditing drift, proposing skills) and the user is impatient to begin Round N+1's Plan phase. Under L2, the Reflector on Round N runs concurrently with the Planner on Round N+1.

**Isolation requirements.**
- The Reflector reads `reviews/` artifacts frozen at the end of Round N's Review/Test/Ship. The Planner of Round N+1 does **not** overwrite these until Reflector finishes.
- The Round N+1 Planner writes to *new* files: `reviews/classification.md` is updated (append-log style, not overwrite), and `reviews/revision_plan.md` is versioned as `revision_plan_roundN+1.md`.
- `reviews/reflection_report.md` from Round N is finalized before the Round N+1 Review phase begins. L2 permits Plan to start early, not Review to start early.

**Forbidden combinations under L2.**
- Reflector (Round N) + Evaluator (Round N+1) — because the Evaluator needs the Reflector's output to know what patterns were just identified.
- Generator (Round N fix) + Generator (Round N+1 section) — no concurrent writes to `milestones/M4_complete_paper_draft.md` under any circumstances.

**Conflict detection.** At session exit the Planner diffs `milestones/M4_complete_paper_draft.md` and all `reviews/` files against the session-entry snapshot. Any unexpected change (a file touched without a corresponding dispatch record) is flagged as a concurrency violation and recorded in `conductor.md`.

---

## 5. L3 — Intra-phase parallel operation (experimental)

**When to use.** A large manuscript (§8,000+ words, per `TOKEN_BUDGET_PROTOCOL.md`) admits natural section-level parallelism. Two Evaluator instances can review §3 and §6 concurrently if (a) the sections are topically independent and (b) the full-manuscript cross-section safeguard checks are deferred to a single consolidation pass.

**Constraints.**
- Only the Evaluator and Reflector may run in L3. Generator is **always** L0 within a project (one prose writer at a time).
- Each parallel Evaluator writes to a distinct `reviews/step_findings/step_N_<section>.md` file; no file contention.
- Safeguard Layer checks that require full-manuscript context (regression, drift, contradictions across sections) are run serially after all parallel Evaluators complete.
- The Planner must explicitly authorize L3 for the round and record it in `conductor.md`.

**Why discouraged.** Two Evaluators miss cross-section problems by construction. The time saved is often consumed by the subsequent cross-section consolidation pass. L3 is therefore reserved for cases where the sections are genuinely decoupled (e.g., an anthology chapter versus its introduction) or where wall-clock time is the binding constraint (conference submission in <48h).

---

## 6. Session handoff protocol

A session ends either because the user closes it or because the Agent tool's session boundary terminates. Clean handoff requires:

1. **Exit snapshot.** Planner writes the current state of all in-flight projects to `conductor.md`, including: current phase, current agent, what the next invocation should do.
2. **Frozen artifacts.** Any `reviews/` file written during the session is checkpointed (no in-progress writes left open).
3. **Pending-dispatch queue.** If the session ended mid-dispatch (e.g., Planner dispatched Evaluator but Evaluator did not complete), the dispatch is recorded in `conductor.md` under "Resume here" with the exact prompt.
4. **User handoff note.** A one-paragraph summary in the user-visible response at session close: what was done, what is pending, what the next session should pick up.

**Session entry.** The next Planner reads `conductor.md` first, then the project's `AGENTS.md`, then the "Resume here" note if any, then proceeds.

---

## 7. Trade-off discussion

Three architectural tensions are encoded in this file and deserve naming.

*The first is **concurrency versus auditability**.* Every parallel thread is a potential seam where contract invariants (see `AGENT_CONTRACTS.md`) can be violated without anyone noticing. The mitigation — per-session diff-based concurrency-violation detection — catches the observable corruptions but cannot catch *semantic* ones (two Evaluators reviewing adjacent sections who reach inconsistent verdicts on a shared passage). The system therefore deliberately trades a small amount of parallelism (L3 discouraged) for large gains in auditability.

*The second is **project isolation versus cross-project learning**.* Strict project scoping (L1 default) prevents directive bleed but also suppresses a real phenomenon: lessons from a CAiSE revision *do* often apply to the next RE submission. The package handles this via the Reflector's escalation path — project-level lessons can be promoted to package-level on user approval — but the escalation is deliberately slow. This is a feature: it forces a human check before a one-venue convention becomes a cross-venue rule.

*The third is **conductor-as-ledger versus conductor-as-enforcer**.* `conductor.md` is a state file, not a locking mechanism. Nothing physically prevents a session from writing to a project marked as frozen in the conductor. The package operates on *norm-compliance*, not enforcement — the agent reads the conductor and chooses to comply. For a single user this is sufficient; for collaborative use with multiple human authors invoking Claude in the same repo, a stronger locking primitive (file-system advisory locks or a dedicated state service) would be needed. This is acknowledged as out-of-scope.

---

## 8. Seeding a conductor for an existing Research root

If no `conductor.md` exists at the Research root when this file is first invoked:

1. The Planner walks immediate subdirectories looking for project markers per `RESEARCH_ROOT_CLAUDE.md` §3.
2. For each project found, the Planner reads the project's `reviews/` and `research_notes/` to infer current phase and round number.
3. The Planner drafts the conductor, presents it to the user, and asks for corrections before committing.

Legacy projects still housed under `D:\OneDrive - University of Toronto\Year 2026\` (see `RESEARCH_ROOT_CLAUDE.md` §10) are *not* added to the Research-root conductor. They belong to the Year 2026 conductor, which is a peer file at that folder's root. On migration, the entry moves.

---

## 9. What this file is NOT

- Not a locking primitive. It is a normative protocol.
- Not a scheduler. The user (or the Planner at the user's direction) decides what runs when.
- Not a replacement for project-level `AGENTS.md` files. The conductor points at projects; the per-project files govern the work.

---

*Created 2026-04-13. Pairs with `ROUTING_SPINE.md` (phase dispatch) and `AGENT_CONTRACTS.md` (agent obligations). Adapts the gstack `conductor.json` pattern (multi-session orchestration) to the academic-research context where parallelism is project-dominant rather than branch-dominant.*
