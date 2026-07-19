# AGENT ORCHESTRATION — Four-Agent Architecture



## Wiki write deferral (Research Truth Phase 0/1)

Coupling C/D canonical Wiki mutation is **unavailable**
(`reason_code: WIKI_WRITE_TRANSACTION_UNAVAILABLE`).

- Block only the Wiki mutation.
- Do **not** block Research completion, approval, or release.
- Project-local REFERENCES, lessons, reports, manuscripts, and reflection
  outputs continue normally.
- On deferral record: `status: deferred`,
  `reason_code: WIKI_WRITE_TRANSACTION_UNAVAILABLE`, `wiki_page_key: null`.
- Do **not** write `m5_wiki_ingest` as a success trigger and do **not**
  fabricate `wiki_page_key` or `lessons_promoted_to_wiki` success values.
- Automatic callers treat the deferred result as a visible non-blocking
  downstream deferral. Phase 4 / G.4 completion does not depend on Wiki write
  availability.

**Purpose.** This file describes the four-agent system that operates on manuscripts governed by the Research and Academic Paper Writing Package. It defines roles, permissions, the dispatch loop, and user checkpoints.

**v0.8.0 framing — Lifecycle-Phase Ladder.** Agent engagement is phase-conditioned under the Lifecycle-Phase Ladder (`PHASE_PROTOCOL.md §1`): Ph1 Plan & Draft runs Planner + Generator + Reflector-lightweight (no Evaluator); Ph2 Review & Revise is the first rung that engages the Evaluator; Ph3 Iterate & Converge runs the full four-agent loop with Reflector-lightweight; Ph4 Finalize & Close runs the full four-agent loop with **Reflector-full** (Phase 2b aggregated confirmation-failed history audit, Phase 3 lessons, Phase 4 skill proposals, Phase 5 memory). The canonical agent-to-phase engagement matrix lives in `PHASE_PROTOCOL.md §2.3`; this file describes what each agent does when dispatched, not when it is dispatched.

**Relationship to `REVIEW_ORCHESTRATION.md`.** The review orchestration defines the *steps* (what to check, in what order, what to emit). This file defines the *agents* (who does what, who dispatches whom, where the user intervenes). The two files are complementary: the agents execute the steps.

---

## 1. The Four Agents

| Agent | Role | Primary output | Writes to manuscript? |
|---|---|---|---|
| **Planner** | Session initializer and dispatcher. Reads project state, classifies the piece, produces a revision plan, and dispatches other agents. Sole writer of `reviews/phase_state.json`. Keeps the user in the loop at every decision point. | `reviews/classification.md`, `reviews/revision_plan.md`, `reviews/phase_state.json`, `reviews/escalation_log.md`, `reviews/ph1_draft_completion.md`, `reviews/ph2_review_completion.md`, `reviews/manuscript_convergence_report.md` | **Never** |
| **Evaluator** | Independent reviewer. Engages at Ph2 and above. Runs the full package review pipeline at Ph2 local scope, Ph3 full scope with external verifiers optional, Ph4 full scope with external verifiers required. Produces findings. Catches what the Generator missed or introduced. **Does not engage at Ph1** — Confirmation Mode and Self-Ph1 Verdict are retired at v0.7.0. | All `reviews/` artifacts: deterministic checks, step findings, consolidated report, safeguard layer results, G4 signoff (mandatory at Ph4), DO_NOT_DISTURB updates | **Never** |
| **Generator** | Prose writer and editor. The only agent that writes to the manuscript. Executes the Planner's revision plan and (at Ph2 and above) the Evaluator's findings. At Ph1 writes under the declared P-stage register with no Self-Ph1 Verdict emission (retired at v0.7.0). | `manuscript/main.md` (edits and new content), `manuscript/revision_log.md` (append-only log) | **Yes — the only agent that does** |
| **Reflector — lightweight** | Engaged at Ph1, Ph2, and Ph3 close-out. Runs integrity probes on the just-closed cycle. **Does not write to `lessons_learned.md`** and does not propose skills. Emits `reviews/reflection_probe_*.md` only. | `reviews/reflection_probe_Ph<N>_<date>.md` | **Never** |
| **Reflector — full** | Engaged at Ph4 close-out (terminal sign-off) and at explicit user request. Runs the five-phase reflection: Phase 1 evidence, Phase 2a + Phase 2b aggregated confirmation-failed history audit (NEW-H-4), Phase 3 lessons → `lessons_learned.md`, Phase 4 skill proposals, Phase 5 memory → `DO_NOT_DISTURB.md`. Attempts Coupling C/D Wiki mutation via SK-14/SK-17; currently returns `status: deferred` / `reason_code: WIKI_WRITE_TRANSACTION_UNAVAILABLE` / `wiki_page_key: null` without blocking primary close-out. | `reviews/reflection_report.md`, `research_notes/lessons_learned.md` (append), `reviews/DO_NOT_DISTURB.md` (append), `research_notes/directives.md` (propose), `skills/*.md` (new skills, with user approval), `references/SKILL_REGISTRY.md` (append) | **Never** |

**The critical constraint:** The Generator never evaluates its own output, and the Evaluator never writes prose. This separation is what makes the system trustworthy. The Reflector-full audits both; the Reflector-lightweight runs an integrity probe only.

**The Planner's real scope (v0.7.3 clarification).** "Planner" is a historical name inherited from v0.5.x when the agent was principally a planner of revision work. At v0.7.3 the role has outgrown that name: the Planner carries seven orchestration responsibilities — (i) classification of the manuscript and P-stage lock-in; (ii) revision planning proper; (iii) dispatch of Evaluator / Generator / Reflector subagents; (iv) sole-writer ownership of `reviews/phase_state.json`, the 18-field per-section ledger; (v) model-capability arbitration under `MODEL_ALLOCATION.md` with the capability-inversion refusal gate (I-Planner-5); (vi) Manuscript Convergence Report compilation and Ph4 admission control; (vii) user-checkpoint gating at every `► PRESENTS TO USER ◄`. In orchestration terms the Planner is the *conductor* of the four-agent pipeline — the single choke-point through which every dispatch and every state transition flows. The package deliberately does not split these responsibilities into a fifth "Maestro" role: orchestration authority co-locates with state authority on a single dispatcher, and the Reflector's Phase 2f audit is the cross-cutting harmonization check that a separate orchestrator would otherwise duplicate. The human user remains the ultimate conductor — every blocking checkpoint routes the decision to a human — while the Planner is the conductor-within-the-loop. A rename to `Director` (or `Conductor`) is under consideration for the v0.7.4 major alongside the Tier → Phase rename; no rename ships in v0.7.3.

**v0.7.0 retirement notice.** Three surfaces retired at v0.7.0, replaced by the Lifecycle-Phase Ladder's phase-conditioned engagement matrix:

1. **Evaluator Confirmation Mode at Ph2 entry** — retired in full (all six steps). Every Ph2 entry runs a fresh Evaluator local-scope pass. Rationale: the shortcut path depended on Self-Ph1 Verdict continuity, which no longer exists.
2. **Generator Self-Ph1 Verdict (Phase 3.5)** — retired. No Self-Ph1 Verdict blocks may appear in v0.7.0 `revision_log.md` entries; emission is a scope-drift violation.
3. **`confirmation_failed` trigger** — retired from the active enum but read-only preserved for v0.6.0 → v0.7.0 migrated projects (see `scripts/migrate_v060_to_v070.py` *[retired from tree]*).

EG-2 (Self-Ph1 verdict mismatch) is retired under §8.2a v0.7.0 gate-semantics deltas because its referent no longer exists.

---

## 2. Agent Prompt Files

Each agent's full operating instructions are in `agents/`:

| File | Agent |
|---|---|
| `agents/planner.md` | Planner |
| `agents/evaluator.md` | Evaluator |
| `agents/generator.md` | Generator (Co-Author) |
| `agents/reflector.md` (compatibility router) → `agents/reflector-probe.md` / `agents/reflector-closeout.md` | Reflector (Lessons-Learned) |

When dispatching an agent (via the Agent tool, a skill, or a direct instruction), include the agent's prompt file content as context. The agent prompt file is the agent's complete operating manual; it references the package files the agent needs to read.

---

## 3. The Loop (with User Checkpoints)

### 3.0 Phase-conditioned engagement (v0.7.0)

The v0.7.0 Lifecycle-Phase Ladder conditions agent engagement on the current phase. The loop diagrams below are the Ph3/Ph4 canonical reference. For Ph1 and Ph2 the loop is **truncated**; the canonical table is in `PHASE_PROTOCOL.md §2.3`.

| Phase | Planner | Evaluator | Generator | Reflector |
|---|---|---|---|---|
| **Ph1 Plan & Draft** | Bootstraps state; drafts revision plan. | **Not engaged** | Drafts under P-stage register on diff scope (Rule 1 digest exception applies) | Lightweight integrity probe only |
| **Ph2 Review & Revise** | Dispatches; runs pre-phase-advance check | First engagement — full local-scope pass on changed sections | Applies findings under P-stage register | Lightweight integrity probe only |
| **Ph3 Iterate & Converge** | Dispatches; runs MCR admission check at close-out | Full-scope pass; external verifiers optional; Coupling E.2 at Step 0.2 | Applies findings under P-stage register | Lightweight integrity probe only |
| **Ph4 Finalize & Close** | Dispatches; runs MCR admission check; G.4 gate | Full-scope pass; external verifiers required; G.4 mandatory | Final edits under declared submission-bound register | **Reflector-full** five-phase close-out |

**Model-capability overlay (v0.7.3).** The Planner resolves each dispatched agent's Claude model from `MODEL_ALLOCATION.md §2`; the table below is a read-only mirror for orientation. Authoritative source remains `MODEL_ALLOCATION.md`.

| Phase | Planner | Evaluator | Generator | Reflector |
|---|---|---|---|---|
| **Ph1** | Sonnet 4.6 | — (dormant) | Sonnet 4.6 ↓ | Haiku 4.5 (lightweight) |
| **Ph2** | Sonnet 4.6 | **Opus 4.7** ★ | Sonnet 4.6 | Haiku 4.5 (lightweight) |
| **Ph3** | Sonnet 4.6 | **Opus 4.7** ★ | Sonnet 4.6 | Haiku 4.5 (lightweight) |
| **Ph4** | Sonnet 4.6 ↓ | **Opus 4.7** ★ | Sonnet 4.6 ↓ | **Opus 4.7** (full) ★ |

★ non-negotiable Opus 4.7 floor (`MODEL_ALLOCATION.md §3`). ↓ downshift from naive role-seniority default (`§4`). The Planner refuses any round that places Evaluator below Generator on `{Haiku 4.5} ≺ {Sonnet 4.6} ≺ {Opus 4.7}` with `E-MA-CAPABILITY-INVERSION`.

### 3.1 The Ph3/Ph4 canonical loop

The standard workflow for a revision round at Ph3 or Ph4:

```
┌─────────────────────────────────────────────────────────────┐
│                     USER REQUEST                            │
│  "Review this manuscript" / "Fix these issues" /            │
│  "Write a new §6" / "Is the piece ready?"                   │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  ① PLANNER                                                  │
│  • Reads project state                                      │
│  • Classifies (or re-confirms classification)               │
│  • Determines what work is needed                           │
│  • Produces revision plan                                   │
│  • ► PRESENTS PLAN TO USER ◄                                │
└─────────────────────┬───────────────────────────────────────┘
                      │ user approves
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  ② EVALUATOR (Ph2 and above only)                            │
│  • Runs Steps 0a–8.5 of REVIEW_ORCHESTRATION.md             │
│  • Produces consolidated findings report                    │
│  • ► PRESENTS FINDINGS TO USER ◄                            │
└─────────────────────┬───────────────────────────────────────┘
                      │ user approves findings
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  ① PLANNER (merges findings into revision plan if needed)   │
│  • Updates revision_plan.md with approved findings          │
│  • ► PRESENTS UPDATED PLAN TO USER ◄                        │
└─────────────────────┬───────────────────────────────────────┘
                      │ user approves
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  ③ GENERATOR                                                │
│  • Reads revision plan + findings                           │
│  • Applies edits / writes new content                       │
│  • Self-checks (deterministic patterns)                     │
│  • Logs in revision_log.md (NO Self-Ph1 Verdict block)       │
│  • ► PRESENTS CHANGES TO USER ◄                             │
└─────────────────────┬───────────────────────────────────────┘
                      │ user approves changes
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  ② EVALUATOR (re-check mode — full local pass)              │
│  • Regression Guard (SAFEGUARD_LAYER Check 1)               │
│  • Drift Detection (Check 2) — W-Ph3-DRIFT-EXCEEDED-TOLERANT │
│    on exceedance at Ph3 under tolerant (warning only)        │
│  • Spot-checks top fixes                                    │
│  • ► PRESENTS RE-CHECK TO USER ◄                            │
└─────────────────────┬───────────────────────────────────────┘
                      │
              ┌───────┴───────┐
              │               │
         if clean        if regressions
              │               │
              ▼               ▼
┌──────────────────┐  ┌──────────────────────────┐
│  ④ REFLECTOR     │  │  ③ GENERATOR (fix round)  │
│  (lightweight    │  │  • Fixes regressions      │
│   at Ph1/Ph2/Ph3,│  │  • Re-signals             │
│   full at Ph4)   │  │  → back to Evaluator      │
│  • Extracts      │  │    re-check               │
│    lessons       │  └──────────────────────────┘
│    (full only)   │
│  • Updates       │
│    memory        │
│    (full only)   │
│  • Proposes      │
│    improvements  │
│    (full only)   │
│  • ► PRESENTS    │
│    REFLECTION    │
│    TO USER ◄     │
└──────────────────┘
         │
         ▼
      ROUND COMPLETE
```

### 3.2 The Ph1 truncated loop (no Evaluator)

```
USER REQUEST
  ↓
① PLANNER — bootstraps 18-field section state; reads classification.md
   for P-stage; populates ph1_pstage_declaration.
  ↓ ► PRESENTS PLAN TO USER ◄
③ GENERATOR — drafts under P-stage register on diff scope
   (Rule 1 digest exception applies at Ph1 only). NO Self-Ph1 Verdict.
  ↓ ► PRESENTS DRAFT TO USER ◄
④ REFLECTOR-LIGHTWEIGHT — optional integrity probe only
   (no lessons_learned.md write).
  ↓
Exit artefact: reviews/ph1_draft_completion.md.
Triggers written on approval: ph1_draft_completion_signed (trigger 12)
then user_approval (trigger 2).
```

At Ph1 the Evaluator is **not engaged**. Attempts to dispatch the Evaluator at Ph1 are a scope-drift violation; the Planner must reject the dispatch and escalate to Ph2 first.

### User checkpoints (mandatory)

Every `► PRESENTS TO USER ◄` in the diagram above is a mandatory checkpoint. The user must approve (or modify, or reject) before the loop advances. Specifically:

| Checkpoint | What the user sees | What the user can do |
|---|---|---|
| After Planner produces plan | The revision plan with prioritized actions | Approve, modify (add/remove/reorder actions), reject (end the round) |
| After Evaluator produces findings | The consolidated findings report with severity counts | Approve, dispute a finding, ask for deeper analysis on a specific item, skip to generation |
| After Planner updates plan with findings | The merged plan (findings → actions) | Approve, modify, reject |
| After Generator applies changes | Summary of what changed + revision log entries | Approve, ask for revisions to specific changes, reject a change |
| After Evaluator re-check | Re-check results (clean or regressions) | Acknowledge if clean; direct Generator to fix if regressions |
| After Reflector presents reflection | The reflection report + proposed memory updates | Acknowledge, approve/reject proposed directives or package improvements |

### Shortened paths

Not every round requires all four agents. The user can shortcut:

| User request | Agents dispatched |
|---|---|
| "Just evaluate this" | Planner (classify only) → Evaluator → Reflector |
| "Just fix M-2" | Planner (targeted plan) → Generator → Evaluator (re-check) → Reflector |
| "Write a new §6 on topic X" | Planner (writing plan) → Generator → Evaluator → Reflector |
| "Is the piece ready?" | Planner (reads state) → answers directly (no dispatch needed if evaluation is current) |
| "What went wrong last round?" | Reflector only (reads prior artifacts) |
| "Run the full loop" | Planner → Evaluator → Planner (merge) → Generator → Evaluator (re-check) → Reflector |

---

## 4. Read/Write Permissions (binding)

| File / directory | Planner | Evaluator | Generator | Reflector |
|---|---|---|---|---|
| `manuscript/main.md` | read | read | **read + write** | read |
| `manuscript/revision_log.md` | read | read | **read + append** | read |
| `reviews/classification.md` | **read + write** | read | read | read |
| `reviews/revision_plan.md` | **read + write** | read | read | read |
| `reviews/step_0a_*.md` | read | **write** | read | read |
| `reviews/step_findings/*.md` | read | **write** | read | read |
| `reviews/consolidated_findings_report.md` | read | **write** | read | read |
| `reviews/safeguard_layer_results.md` | read | **write** | read | read |
| `reviews/G4_signoff.md` | read | **read + write** | read | read |
| `reviews/DO_NOT_DISTURB.md` | read | **read + append** | read | **read + append** |
| `reviews/reflection_report.md` | read | read | read | **write** |
| `research_notes/directives.md` | read | read | read | **read + append (PROPOSED only)** |
| `research_notes/lessons_learned.md` | read | read | read | **read + append** |
| `references/SKILL_REGISTRY.md` | read | read | read | **read + append** |
| `skills/*.md` (skill files) | read | read | read | **write (new skills, with user approval)** |
| Package files (`research-writing-harness/*` except skills/) | read | read | read | read (propose changes via reflection report) |

**Enforcement.** These permissions are encoded in each agent's prompt file as binding instructions. They are not structurally enforced by the filesystem. If an agent violates its permissions, the Reflector should flag it as an avoidable error in the next reflection.

---

## 5. How to Invoke Each Agent

### Via the Agent tool (in Claude Code)

When dispatching an agent, use the Agent tool with a prompt that includes:
1. The agent's role description (from this file §1)
2. The agent's full prompt (read the appropriate file from `agents/`)
3. The project path and the specific task
4. **The `model` parameter**, resolved by the Planner from `MODEL_ALLOCATION.md §2` at dispatch time (v0.7.3 onward). The Planner looks up the section's `current_phase` × the dispatched agent in the allocation table and passes the resolved string (`claude-opus-4-7`, `claude-sonnet-4-6`, or `claude-haiku-4-5-20251001`) as the Agent tool's `model` argument. No per-agent frontmatter `model:` field is authoritative; the allocation table is the single source of truth.

Example dispatch pattern:

```
Agent tool invocation for Evaluator at Ph3:
  subagent_type: co-author-harness-claude:evaluator
  model:         claude-opus-4-7   ← resolved from MODEL_ALLOCATION.md §2 (Evaluator × Ph3 = Opus 4.7, non-negotiable floor)
  prompt:        "You are the Evaluator agent. Read and follow the instructions in
                 agents/evaluator.md (in the package folder) exactly.

                 Project: <project path>
                 Task: Full review of manuscript/main.md at Ph3 (Iterate & Converge) depth.

                 Read the project CLAUDE.md first, then follow the Evaluator procedure."
```

**Capability-inversion refusal.** Before dispatching, the Planner checks that the round's resolved allocation does not place the Evaluator below the Generator on the family ordering `{Haiku 4.5} ≺ {Sonnet 4.6} ≺ {Opus 4.7}`. If it would, the Planner refuses the round with `E-MA-CAPABILITY-INVERSION` and presents the resolved allocation to the user for override or correction. See `MODEL_ALLOCATION.md §5 Hazard H-MA-1`.

**Audit trail.** Every dispatch writes one row to `phase_state.json phase_entry_log` with the `notes` field carrying `model_dispatch:{agent}:={model}` (or `model_override:{agent}-{phase}:={model}` for directive-based overrides from `research_notes/directives.md`). The Reflector's Phase 2f audit reads these rows to verify model-selection consistency against `MODEL_ALLOCATION.md §2`.

### Via the parent session

The Planner can be the parent session itself (the session the user is interacting with) rather than a dispatched subagent. In this mode:
1. The parent session reads `agents/planner.md` and acts as the Planner.
2. It dispatches the Evaluator and Generator as subagents via the Agent tool.
3. The Reflector runs as the final subagent or in the parent session.

This mode keeps the user in the parent session's context and uses subagents for the evaluation and generation work.

### Via skills (future)

If skills are defined (e.g. `/plan-manuscript`, `/evaluate-manuscript`, `/generate-manuscript`, `/reflect-on-round`), each skill's prompt should read the corresponding agent file from `agents/` and execute its procedure. Skills provide a user-friendly invocation surface.

---

## 6. Agent Communication

Agents communicate **through files**, not through shared memory or context. The handoff protocol:

| From | To | Handoff artifact | What it contains |
|---|---|---|---|
| Planner → Evaluator | `reviews/classification.md` + `reviews/revision_plan.md` | Classification fields + prioritized actions |
| Evaluator → Planner | `reviews/consolidated_findings_report.md` | Findings with severity, proposed fixes, confirmed strengths |
| Planner → Generator | `reviews/revision_plan.md` (updated with findings) | Merged action list with rule citations |
| Generator → Evaluator | `manuscript/revision_log.md` (new round entry) | What changed, rules cited, self-check status |
| Evaluator → Reflector | `reviews/consolidated_findings_report.md` + `reviews/safeguard_layer_results.md` | Full round evidence |
| Reflector → everyone | `research_notes/lessons_learned.md` + `reviews/reflection_report.md` | Extracted lessons, proposed improvements |

**No agent should assume another agent's context.** Each agent reads from files, not from the prior agent's memory. This is what makes the system work across sessions: a Generator in session N can read the Evaluator's findings from session N-1 because the findings are in files, not in a conversation history.

---

## 7. When Things Go Wrong

### The Generator introduces regressions — Retain/Revert Protocol

When the Evaluator's re-check detects regressions, the system applies the **Retain/Revert Protocol** (inspired by autoresearch's keep-or-discard decision after each experiment):

```
Evaluator re-check finds regression
    ↓
Planner categorizes each Generator change as:
    ├── RETAIN — no regression, improvement confirmed
    ├── REVERT — this specific change caused a regression
    └── PARTIAL — the change improved one dimension but regressed another
    ↓
For REVERT changes:
    Generator rolls back the specific edit (not the entire round)
    Generator logs the revert in revision_log.md with verdict = REVERT
    ↓
For PARTIAL changes:
    Planner presents the trade-off to the user
    User decides: keep, revert, or modify
    ↓
Evaluator re-checks ONLY the reverted/modified sections (not the full manuscript)
    ↓
Reflector records: what was tried, why it failed, what to avoid next round
```

**Key principle from autoresearch:** Every change is an experiment. The system compares the post-change state to the pre-change state on a defined metric (WFC for defect density, SIS for structure, PQP for prose craft — see `SUCCESS_METRICS.md`). If the metric worsened, the change is a candidate for revert. This prevents the accumulation of well-intentioned edits that collectively degrade the manuscript.

**Revert granularity.** Reverts are per-edit, not per-round. A round that produced five edits may retain three, revert one, and flag one as partial. This granularity is feasible because the Generator's structured experiment log (see `AGENT_CONTRACTS.md` §3) tracks each change individually.

### The Evaluator misses a problem
The Reflector catches it (by comparing what the Evaluator found to what was actually in the text). The Reflector proposes a new check or pattern to the package.

### The Planner produces a bad plan
The Evaluator's findings will diverge from the plan. The Reflector notes the divergence and records a lesson about plan quality.

### Two agents disagree
The Planner mediates. The user makes the final call. The disagreement is recorded in the reflection report.

### The user overrides a finding
The Planner records the override in `research_notes/directives.md` so future agents respect it. The Reflector notes it as a project-specific constraint.

---

## 8. Three-Layer Architecture and the Round Program

### 8.1 The Three Layers

The autoresearch project (Karpathy, 2025) makes a productive architectural move: it names three layers explicitly — **immutable** (infrastructure that agents must not modify), **experimental** (the artifact agents iterate on), and **control** (human-authored directives that guide each iteration). This package adopts the same taxonomy.

| Layer | Autoresearch analogue | Package equivalent | Who modifies |
|-------|----------------------|-------------------|-------------|
| **Immutable** | `prepare.py` — data prep, evaluation harness | Package infrastructure: `GROUNDING_PROTOCOL.md`, `REVIEW_ORCHESTRATION.md`, `DETERMINISTIC_CHECKS.md`, `SAFEGUARD_LAYER.md`, `AGENT_CONTRACTS.md`, `ROUTING_SPINE.md`, `DO_NOT_DISTURB.md` | Human only (Reflector may *propose* changes via reflection report, but never writes directly) |
| **Experimental** | `train.py` — the model and training loop | The manuscript: `manuscript/main.md`, `manuscript/outline.md`, and their supporting artifacts (`revision_log.md`, `revision_plan.md`, findings files) | Agents within their declared permissions (`AGENT_CONTRACTS.md`) |
| **Control** | `program.md` — human-authored research direction | `round_program.md` (project-level, user-authored) + `research_notes/directives.md` (persistent) + user conversation | Human only |

**Why naming matters.** When the layers are unnamed, agents make boundary errors: a Generator edits a package file, an Evaluator improvises a new check not in the immutable layer, a Planner overrides a user directive. Naming the layers makes the boundaries auditable. The Reflector's contract verification (§6 in `AGENT_CONTRACTS.md`) now includes a layer-violation check.

### 8.2 The Round Program (`round_program.md`)

The round program is a lightweight, user-authored markdown file that lives at the **project root** (alongside the project `CLAUDE.md`). It declares the user's intent for the current round — what to focus on, what to ignore, and what "success" looks like for *this specific iteration*. It is the academic-writing analogue of autoresearch's `program.md`.

**Why it exists.** The revision plan (`reviews/revision_plan.md`) is agent-generated. The directives file (`research_notes/directives.md`) is persistent across rounds. Neither captures the ephemeral, round-specific intent of the user. The round program fills this gap.

**Who reads it.** The Planner reads it first on every dispatch (per `AGENT_CONTRACTS.md` §1). If present, the Planner uses it to constrain scope, prioritize actions, and set the round's success criteria. If absent, the Planner proceeds as before (the round program is optional).

**Who writes it.** The user, before requesting a round. The Planner may also *draft* a round program and present it for user approval (e.g., "Based on the last reflection report, I suggest this focus for the next round…"). But the user always has final say.

**Lifecycle.** The round program is overwritten each round (it is not append-only). Prior round programs are archived by the Reflector into the reflection report's §round-context section.

**Seed template:** See `PROJECT_BOOTSTRAP.md` §2.10.

### 8.2a The Escalation Log (`reviews/escalation_log.md`)

The escalation log is a Planner-written, append-only markdown file that records every phase transition made within a round. Where `round_program.md` (§8.2) is the human-authored declaration of intent, the escalation log is the pipeline-authored trace of how the Lifecycle-Phase Ladder (see `PHASE_PROTOCOL.md`) responded to that intent at run time. It is the audit surface for "why did this edit jump from Ph1 to Ph3?" and "which gate fired at this cycle?"

**Why it exists.** The phase protocol's value depends on its escalations and advances being *visible* — silent phase changes defeat the gating contract. A Generator whose work triggers EG-1 (Grounding threat) and auto-demotes from Ph4 back to Ph3, or a classification change at Ph4 that fires EG-7 and re-admits the manuscript to Ph3 for re-convergence, must leave a traceable record so the Reflector can audit whether the transition was proportional, and so the user can see at cycle close exactly what the pipeline did. Without the log, transitions become private Planner state, which voids both the ladder contract and §8.2b's ledger audit trail.

**Who reads it.** The Reflector-full reads it at Ph4 close (see `PHASE_PROTOCOL.md §9.2`) to aggregate gate-fire statistics and (for v0.6.0 → v0.7.0 migrated projects) the archived `confirmation_failed` history (NEW-H-4). The user may read it between cycles as the pipeline's counterpart to the round program: a declaration of what the pipeline did when the user's declared focus met the gate register. Note: at v0.7.0 the Evaluator no longer reads the log at Ph2 entry — Confirmation Mode is retired, and every Ph2 entry runs a fresh Evaluator local-scope pass.

**Who writes it.** The Planner writes every escalation entry. Agents other than the Planner (Evaluator findings, Reflector audit remarks, user overrides) surface escalation triggers through their normal outputs; the Planner is the single point of truth that translates a triggered gate into a logged escalation. This preserves the single-writer invariant established for the round program and avoids three-way merge conflicts on a shared append-only file. (At v0.7.0 the Generator no longer surfaces self-Ph1 verdicts — Phase 3.5 is retired.)

**Lifecycle.** The log is created empty when a round opens (on Planner dispatch at Ph1 or above — the Ph1 Plan & Draft lifecycle stage still produces logged transitions for `initial_dispatch`, `ph1_draft_completion_signed`, and `user_approval`), appended to as escalations fire, and archived by the Reflector-full into the reflection report's `§escalation-trace` section at Ph4 close-out. Unlike the round program, the log is **not overwritten between rounds**; it is preserved in `reviews/escalation_log.md.<round-id>` so that cross-round escalation-pattern analysis remains possible. Gate-threshold calibration (`scripts/gate_threshold_tuner.py`) consumes this preserved history at Ph4 close per `PHASE_PROTOCOL.md §9.2`.

**Gate definitions — canonical source.** The six v0.7.0 gates (EG-1, EG-3, EG-4, EG-5, EG-6, EG-7 — EG-2 retired) — firing conditions, target phases, phase activation — are defined canonically in `PHASE_PROTOCOL.md §4`. That section is the *single* normative register. This section does **not** redefine gates; it specifies only the log schema, the read/write roles, and the append semantics. If the two files ever diverge, `PHASE_PROTOCOL.md §4` wins.

**v0.7.0 gate-semantics deltas.** EG-2 (Self-Ph1 verdict mismatch) is **retired** at v0.7.0 because its referent — the Generator Self-Ph1 Verdict emitted in Phase 3.5 of the v0.6.0 Generator contract — no longer exists. Any `phase_entry_log` row with `trigger: "confirmation_failed"` is a v0.6.0 → v0.7.0 migration artefact, preserved read-only for audit continuity by `scripts/migrate_v060_to_v070.py`. EG-1 is **repurposed** as the Ph4 → Ph3 downgrade gate: a Rule 1–7 grounding violation detected at Ph4 (e.g. by Step 0.2 Coupling E.2 overlay, by the Reflector-full grounding audit in Phase 1, or by a manual user flag) demotes the offending section back to Ph3 for re-convergence via the `eg1_ph4_downgrade_to_ph3` trigger (trigger 23 in `phase_state_schema.md §3.1`). EG-3 (Cross-scope reference) fires at Ph2 entry when a finding cites a `location:` outside the containing section. EG-7 (MCR re-admission after classification change) is **new at v0.7.0**: when `reviews/classification.md` changes after the MCR has admitted a section to Ph4, the section is demoted to Ph3 for re-convergence via the `eg7_mcr_readmission_after_class_change` trigger (trigger 22). EG-6 (user override) remains a **non-blocking warning** — the log records the override but the Planner does not halt. EG-4 and EG-5 preserve v0.6.0 semantics.

**Entry schema (canonical).** Each entry is a single pipe-delimited row, machine-parseable by `scripts/gate_threshold_tuner.py` (regex at `GATE_ROW_RE`, lines 62–65 of that script):

```
| timestamp | prev_phase -> new_phase | gate | reason | round_id |
```

Field semantics:

- **`timestamp`** — ISO-8601 timestamp of the *triggering* event (Evaluator finding timestamp, MCR admission timestamp, user-override receipt timestamp), not the logging event. This preserves chronological order across concurrent triggers.
- **`prev_phase`** and **`new_phase`** — one of `Ph1 | Ph2 | Ph3 | Ph3_converged | Ph4 | T4R`. The pair appears as `Phx -> Phy` with the ASCII arrow (not `→`) so the tuner's regex matches. The pipe-row field names changed from v0.6.0 (`from_tier` / `to_tier`) to v0.7.0 (`prev_tier` / `new_tier`) to v0.8.0 (`prev_phase` / `new_phase`) to align with the JSON `phase_entry_log` schema in `phase_state_schema.md §3.1`. The `gate_threshold_tuner.py` regex anchors on column position, not on header text, so the rename is parser-compatible.
- **`gate`** — one of `EG-1 | EG-3 | EG-4 | EG-5 | EG-6 | EG-7` (six gates at v0.7.0; EG-2 retired). See `PHASE_PROTOCOL.md §4` for firing conditions.
- **`reason`** — one sentence, must cite either a manuscript line range (`manuscript.tex:214-221`) or a finding ID (`[F-2026-04-19-03]`). A reason that cites neither is itself a grounding flag and the Reflector-full treats it as an audit blocker under Rule 1.
- **`round_id`** — `round-<N>` or any short identifier that matches the round-program ID for the round (so that `gate_threshold_tuner.py` can pair the firing with the corresponding cycle in `manuscript/revision_log.md` for that round).

**Optional human-readable context block.** After the pipe row, the Planner may append an indented block with additional context that is useful to human readers but ignored by the tuner:

```
| 2026-04-19T15:04:22 | Ph2 -> Ph3 | EG-3 | Finding [F-2026-04-19-03] cites paragraph outside local envelope | round-07 |
    - Trigger artifact: reviews/local_findings_2026-04-19.md
    - Triggering agent: evaluator
    - Digest used at trigger: reviews/_rule_digest_0.7.0.json
    - Next expected artifact: reviews/findings_2026-04-19.md
```

The indented block is parsed by the Reflector-full Phase 2b trajectory collector (`agents/reflector-closeout.md §Phase 2b step 1`) for richer divergence-audit reporting, and is safely skipped by `gate_threshold_tuner.py` (the regex matches only lines beginning with `|` at column 0). Neither consumer requires the block; it is optional provenance, not contract.

**Header.** The first line of the file is always a single `# Escalation Log — <round-id>` heading; the Planner writes this on round open and never rewrites it. The second line is a pipe-table header and separator so that the body reads as a valid markdown table:

```
| timestamp | prev_phase -> new_phase | gate | reason | round_id |
|---|---|---|---|---|
```

The tuner's regex anchors on the column shape, not on the header, so the header is decorative for human readers and tolerated by the parser.

**Append semantics.** Entries are appended in chronological order of the triggering event (not the logging event). Out-of-order writes are prohibited; if two triggers fire concurrently, the Planner serializes them by the timestamp on the underlying artifact.

**Phase status (v0.7.0).** The write path is live on the Planner only. The Planner creates the log on first dispatch at Ph1 (or the user-selected explicit phase when `/run-phase-N` is used) and appends on every subsequent transition under the 31-value trigger enum (`phase_state_schema.md §3.1`): Ph1 lifecycle triggers (`initial_dispatch`, `ph1_draft_completion_signed`), Ph2/Ph3/Ph4 lifecycle triggers (`ph2_review_completion_signed`, `ph3_iteration_round`, `convergence_metric_stable`, `mcr_admission`, `ph3_convergence_signoff_terminal`, `ph3_stale_reengagement_signoff`), gate firings (EG-1, EG-3, EG-4, EG-5, EG-6, EG-7 — including the `eg1_ph4_downgrade_to_ph3` and `eg7_mcr_readmission_after_class_change`), drift-tolerance warnings (`ph3_drift_exceeded_tolerant`), staleness (`ph3_stale_detected`), user overrides (EG-6 via `/run-phase-N`), fingerprint demotions (`fingerprint_reset`), MCR cycle transitions, M5 wiki ingest (`m5_wiki_ingest`), and explicit user phase-downs (§6.4 of `PHASE_PROTOCOL.md`). The Reflector-full's Phase 2b at Ph4 reads the log to compute aggregated confirmation-failed history patterns (NEW-H-4) — at v0.7.0 this audit aggregates `confirmation_failed` rows imported from v0.6.0 → v0.7.0 migrated projects since the trigger no longer fires natively. Cross-round preservation (`reviews/escalation_log.md.<round-id>`) remains in effect.

**Calibration (v0.7.0).** Scheduled Reflector-full runs are scoped to Ph4 at v0.7.0 (`PHASE_PROTOCOL.md §9.2`). Gate-calibration signals therefore surface at Ph4 close rather than every round. Persistent single-gate skew across Ph4 rounds surfaces a `[GATE CALIBRATION SIGNAL]` entry in §9 of the reflection report proposing an adjustment. The proposal is advisory — the user must accept before any threshold is rewritten. The `scripts/gate_threshold_tuner.py` multi-project aggregator continues to consume the same pipe-row schema.

**Seed template:** The Planner writes the following header on first Ph3 entry (or copies it when archiving a prior round into `escalation_log.md.<round-id>`):

```markdown
# Escalation Log — <round-id>

**Round:** <N>
**Opened:** <ISO-8601 timestamp>
**Planner:** <agent-instance-id>

<!-- Append-only. One pipe-delimited row per escalation per §8.2a entry schema.
     Archived by the Reflector at Ph4 close into reviews/escalation_log.md.<round-id>. -->
```

### 8.2b The Phase State Ledger (`reviews/phase_state.json`)

The phase-state ledger is a Planner-written, single-writer JSON file that carries the **per-section lifecycle-phase state** for the manuscript across sessions. It replaces the v0.6.0 ledger at schema bump `0.6.0` → `0.7.0`; the v0.6.0 ten-field SectionStateObject is widened to fifteen fields (sixteen at v0.8.0, eighteen at v0.10.0) and the `tier_entry_log` row schema is renamed from `from_tier` / `to_tier` to `prev_tier` / `new_tier` to `prev_phase` / `new_phase` to match the §3a row schemas in `phase_state_schema.md`. This section specifies the normative shape, read/write roles, persistence contract, and concurrency contract. **The canonical field-by-field JSON schema lives in `references/phase_state_schema.md §2`; this section defines what the ledger is *for* and how the agent-contract binds to it.**

**Why it exists.** v0.7.0 replaces v0.6.0's Progressive Approval Staircase with the Lifecycle-Phase Ladder (Ph1 Plan & Draft, Ph2 Review & Revise, Ph3 Iterate & Converge, Ph4 Finalize & Close). The ledger is per-section because lifecycle phases advance sections individually: §3 reaches Ph3_converged; §4 stays at Ph1 awaiting outline approval; §5 stalls at Ph2. A single manuscript-wide `phase:` field cannot represent that state. The v0.7.0 ledger closes four loopholes simultaneously: (a) drift accumulation between approvals (`cumulative_drift_lines_since_approval`); (b) premature completion (every section must reach `Ph3_converged` or `ceiling_locked` before Ph4 admission — enforced by the Manuscript Convergence Report, `PHASE_PROTOCOL.md §7`); (c) silent fingerprint re-basings (mode-parameterized, §4 of PHASE_PROTOCOL); and (d) **stale Ph3 sections** (no activity for ≥ `ph3_stale_budget_days`, computed from `ph3_last_activity_at` against wall-clock — Option A, no persisted staleness flag).

**Who writes it.** The **Planner is the sole writer**. No other agent mutates `phase_state.json`. The Evaluator, Generator, and Reflector read the ledger at session bootstrap and at every agent dispatch; they never write to it. This single-writer invariant is load-bearing for the concurrency contract (see "Persistence and concurrency" below) and for the Reflector-full's audit that every `user_approval` row traces to an explicit user action (success metric M3 in `PHASE_PROTOCOL.md §11`).

**Who reads it.** Every agent, every dispatch. The Reflector-full reads the aggregated `phase_entry_log` array at Ph4 close for Phase 2b's aggregated confirmation-failed history audit (`PHASE_PROTOCOL.md §9.2`, NEW-H-4) — at v0.7.0 this audit walks `confirmation_failed` rows imported from migrated v0.6.0 projects, since the trigger does not fire natively. The migration script `scripts/migrate_v060_to_v070.py [retired from tree]` reads v0.6.0 `tier_state.json` and writes the v0.7.0 schema per `PHASE_PROTOCOL.md §10.1`, preserving `confirmation_failed` rows read-only.

**Lifecycle.** Created once per project at first `/review` (fresh project) or at migration (v0.6.0 → v0.7.0 project). Lives across the project's lifetime. Never overwritten between sessions. Never archived to a round-suffixed copy (unlike `escalation_log.md.<round-id>`) — the ledger itself is cross-round state, and the `phase_entry_log` array inside it is the audit trail.

**Structural overview.** The ledger is a JSON object with:

- **Top-level metadata.** `schema_version: "0.7.4"`, `manuscript_id` (opaque identifier, placeholder in examples), `default_final_phase` (mirrors classification.md, capped per R-02 in `PHASE_PROTOCOL.md §6.4`), `fingerprint_mode` (`strict` / `tolerant` / `off`), `terminal_phase_reached` (boolean), `ph3_stale_budget_days` (integer, default 14), `last_updated` (ISO-8601 wall-clock of the most recent mutation).
- **`sections` object.** One object per top-level manuscript section (keyed by heading-path slug), each carrying the **eighteen canonical fields** enumerated in `phase_state_schema.md §2.1` — the v0.6.0 ten (`heading_path`, `current_phase`, `last_approved_phase`, `ceiling_locked`, `section_ceiling_override`, `iteration_count_at_current_phase`, `last_scope_fingerprint`, `fingerprint_computed_at`, `cumulative_drift_lines_since_approval`, `phase_entry_log`) plus the **eight v0.7.0+ additions**: `phase_goal_declared` (string, the user-declared goal for the current phase), `phase_deliverable_path` (string, path to the phase exit artefact), `convergence_metric` (float, Ph3 only — `diff_lines_vs_previous_round / total_section_lines`), `ph1_pstage_declaration` (string, one of `P0` / `P1` / `P2` declared at Ph1, required at Ph2 admission, enforced by `pre_phase_advance_check.py` clause (e)), `ph3_last_activity_at` (ISO-8601, set on Ph3 advance and refreshed on every Ph3 cycle and on `[Ph3-STALE]` re-engagement), `pre_mcr_deep_pass_completed` (boolean, v0.8.0 addition per β-P-9a), `references_initialized` (boolean, v0.10.0 S2 — snowball reference seeding complete), and `last_coverage_score` (float | null, v0.10.0 S4 — most recent Ph2 claim-coverage audit score). The `current_phase` enum at v0.7.4 is `{Ph1, Ph2, Ph3, Ph3_converged, Ph4, ceiling_locked}` (the v0.6.0 `T4_ready` value is renamed to `Ph3_converged`).
- **`phase_entry_log` (per section).** Append-only array of transition rows under three row schemas — PhaseEntryLogRow (the standard row), TerminalSignoffRow (`is_terminal: true`, mutually exclusive with `is_reengagement`), and ReengagementSignoffRow (`is_reengagement: true`, mutually exclusive with `is_terminal`). Each row: `{timestamp, trigger, prev_phase, new_phase, actor, notes, model_used}`. The `trigger` enum has **31 legal values** (see `phase_state_schema.md §3.1` for the canonical table). The v0.6.0 thirteenth value `confirmation_failed` is migrated read-only and is not in the active enum.

**Persistence and concurrency contract.** Every mutation follows the atomic `phase_state.json.tmp` → `rename` pattern (`PHASE_PROTOCOL.md §8.7`). The Planner stamps `last_updated` with the current wall-clock time on every mutation; the NEW-H-5 invariant requires `last_updated ≥ max(phase_entry_log[*].timestamp)` across all sections and rows written in the same session. Before any write, the Planner performs an mtime + sha256 concurrency check against the in-memory copy read at session bootstrap; a mismatch fires the `[CONCURRENCY-DETECTED]` prompt (`PHASE_PROTOCOL.md §8.7`) and the write halts until the user resolves the divergence. An advisory lockfile `reviews/.phase_state.lock` is best-effort; it does not substitute for the mtime+hash check.

**Cross-reference with §8.2a.** The escalation log (§8.2a) records transitions as pipe-row append-only markdown for human readability and for `gate_threshold_tuner.py`; the `phase_entry_log` array in §8.2b records the same transitions as structured JSON for agent consumption. The two representations must not disagree. A transition that appears in the escalation log but is missing from `phase_entry_log` (or vice versa) is a Planner-contract violation the Reflector-full flags as a BLOCKER (grounding violation: Rule 2 — compute before report). The `prev_phase` / `new_phase` JSON field names match the pipe-row column names — the rename from v0.6.0's `from_tier` / `to_tier` to v0.7.0's `prev_tier` / `new_tier` to v0.7.4's `prev_phase` / `new_phase` was global to keep escalation-log parsers and JSON consumers in lockstep.

**Audit envelope.** The Reflector-full's success-metric M3 audit (`PHASE_PROTOCOL.md §11`) walks the `phase_entry_log` at Ph4 close and verifies that every `user_approval` row is preceded within the same session by one of: `initial_dispatch`, a prior `user_approval`, a `user_rejection` followed by a meaningful Generator write, an `mcr_admission` row covering the section, a `ph3_iteration_completion_signed` row at Ph3, a `ph2_review_completion_signed` row at Ph2, or an `override_applied` row with user concurrence logged. Any `user_approval` whose predecessor does not satisfy these cases surfaces as a Category 6 violation (approve-through-inertia).

**Legacy compatibility.** v0.6.0 projects migrate via `scripts/migrate_v060_to_v070.py`, which: (a) bumps `schema_version` to `0.7.4`; (b) renames each `phase_entry_log` row's `from_tier` / `to_tier` → `prev_tier` / `new_tier` → `prev_phase` / `new_phase` (two-step rename); (c) renames `current_phase: "T4_ready"` to `"Ph3_converged"`; (d) injects null defaults for the six new SectionStateObject fields (including `pre_mcr_deep_pass_completed: false`), with an attached `migration_report_hold` warning that the Planner must resolve before any Ph2 dispatch; (e) preserves `confirmation_failed` rows read-only; (f) renames the trigger `laggard_clearance_approved` to `mcr_admission` and `laggard_clearance_cancelled` to `mcr_admission_revoked`. Post-migration, the v0.6.0 `tier_state.json` is archived as `phase_state_v0.6.0.archive.json` and is **not read** by v0.7.4 runtime code — only the migrated `phase_state.json` is authoritative.

**Seed template (fresh v0.7.0 project).**

```json
{
  "schema_version": "0.7.4",
  "manuscript_id": "<project-slug>",
  "default_final_phase": "Ph3",
  "fingerprint_mode": "tolerant",
  "terminal_phase_reached": false,
  "ph3_stale_budget_days": 14,
  "last_updated": "2026-04-19T14:05:22Z",
  "sections": [
    {
      "heading_path": ["1. Introduction"],
      "current_phase": "Ph1",
      "last_approved_phase": null,
      "ceiling_locked": false,
      "section_ceiling_override": null,
      "iteration_count_at_current_phase": 0,
      "last_scope_fingerprint": "<sha256>",
      "fingerprint_computed_at": "2026-04-19T14:05:22Z",
      "cumulative_drift_lines_since_approval": 0,
      "phase_goal_declared": null,
      "phase_deliverable_path": null,
      "convergence_metric": null,
      "ph1_pstage_declaration": null,
      "ph3_last_activity_at": null,
      "pre_mcr_deep_pass_completed": false,
      "phase_entry_log": [
        {
          "timestamp": "2026-04-19T14:05:22Z",
          "trigger": "initial_dispatch",
          "prev_phase": null,
          "new_phase": "Ph1",
          "actor": "planner",
          "notes": "Section initialized on fresh v0.7.4 project.",
          "model_used": null
        }
      ]
    }
  ]
}
```

The migration script produces an analogous seed for v0.6.0 → v0.7.4 projects, performing the field rename and default-injection as described above and emitting a `migration_report_hold` row in `phase_entry_log` that the Planner must resolve before any Ph2 dispatch.

---

### 8.3 The Tier Marshal — retired at v0.6.0 (note carried at v0.7.0)

**Status: retired since v0.6.0.** The **Tier Marshal**, introduced at v0.5.5 (Phase F.1 advisory rollout) as the package's fifth agent, was retired at v0.6.0 and remains retired at v0.7.0. The 24 predicates that constituted its preflight/postflight battery (P-1…P-13 and Q-1…Q-11) were bound to machinery that the v0.6.0 rewrite removed — the Phase 5.5 Tier Close-Out election (`Down / Stay / Up / Done`), the asymmetric-Down ratchet (`ascent_observed` array), the per-round `reviews/tier_closeout_<round>_<date>.md` benefit-delta artefact, and the `choice`-column `reviews/tier_decisions_log.md`. Under the v0.7.0 Lifecycle-Stage Ladder these objects do not exist; the predicates that guarded them have no referents and cannot fire.

**Per-predicate retirement rationale.** See `PHASE_PROTOCOL.md §9.1` for the binding-by-binding audit (which predicate referenced which retired object, and why no v0.7.0 analog is required). In brief: P-7 and P-8 referenced the ratchet header and `ascent_observed` — both gone under the monotonicity invariant (current_phase never moves below last_approved_phase except via explicit EG-1 / EG-7 demotion or user retraction); Q-1 through Q-5 referenced the close-out artefact and decisions-log `choice` column — both gone under the binary Approve/Reject gate of `PHASE_PROTOCOL.md §6`; the remaining predicates either collapse into well-formedness checks on `phase_state.json` (now absorbed into the Planner's Phase 0 bootstrap) or into the pre-phase-advance check (absorbed into `scripts/pre_phase_advance_check.py` per `PHASE_PROTOCOL.md §7.3`). Confirmation Mode at Ph2 entry — itself retired at v0.7.0 — no longer absorbs any of these predicates.

**Archived artefacts.** The v0.5.5 contract document `references/TIER_MARSHAL_CONTRACT.md`, the runners `scripts/marshal_preflight.py` / `scripts/marshal_postflight.py` / `scripts/_marshal_common.py`, and the F.1 report-template fixtures are archived under `legacy/marshal-f1-retired/` with a README enumerating their historical role and the replacement path *(the archive directory has since been removed from the tree; recover from git history)*. The v0.5.5 migration helper `scripts/migrate_classification_to_tier.py` was superseded by `scripts/migrate_v055_to_v060.py`, which is itself superseded at v0.7.0 by `scripts/migrate_v060_to_v070.py` (Phase 7 of the v0.7.0 rollout).

**Function absorption.** The Marshal's two structural duties migrate into the Planner:

- **Preflight (was P-1…P-13)** → Planner Phase 0 session-bootstrap routine (`agents/planner.md §Phase 0`), which reads `reviews/classification.md` and `reviews/phase_state.json`, validates ledger well-formedness, verifies the NEW-H-5 `last_updated` invariant, checks fingerprint freshness, handles concurrency via the mtime+sha256 check, and halts with a [STATE-CORRUPT] or [CONCURRENCY-DETECTED] prompt if invariants fail.
- **Postflight (was Q-1…Q-11)** → Planner Phase 5.5 post-approval log-write routine, which appends the `phase_entry_log` row under the 31-trigger active enum and updates `current_phase` / `last_approved_phase` / `iteration_count_at_current_phase` / `cumulative_drift_lines_since_approval` / `last_updated` atomically.

Under the v0.6.0 monotonicity invariant the ratchet audit is **vacuous** — there is no asymmetric-Down path left to police — so the predicates that enforced it (P-7, P-8, Q-6) have no work to do and are not replaced. SAFEGUARD Check 5 (Edit Traceability) continues to enforce the edit → finding linkage it always did; Q-2's "every round closes on a signed close-out" duty is supplanted by the binary approval gate and its `tier_entry_log` row.

**Scope of this note.** This §8.3 is preserved as a migration marker only. Agents that previously dispatched or consulted the Marshal (no active agent does at v0.6.0) should treat references to `TIER_MARSHAL_CONTRACT.md` as dangling and route to `PHASE_PROTOCOL.md §9.1` and the archived `legacy/marshal-f1-retired/README.md` for historical context.

---

## 8a. Bootstrapping a New Project

When starting a new project under the four-agent system, read `PROJECT_BOOTSTRAP.md` (in this package). It defines the standard directory structure, seed file templates, and the bootstrap procedure. Summary:

1. **Gather inputs** from the user (project name, venue, paper type, P-stage).
2. **Create the directory tree** using the standard template in `PROJECT_BOOTSTRAP.md §2`.
3. **Dispatch the Planner** to classify the project and propose a first action.
4. **Confirm to the user** with the created structure and proposed next step.

For bootstrapping from an existing draft or a course assignment, see `PROJECT_BOOTSTRAP.md §§4–5`.

---

## 8.5 Wiki Synthesis Promotion (Coupling C)

After every round's Phase 3 (Update Project Memory), the Reflector invokes **SK-14 `promote-lessons-to-wiki`**, which currently returns a deferred structured result (`WIKI_WRITE_TRANSACTION_UNAVAILABLE`) and must not create a Wiki synthesis page. This is the Research → Wiki feedback loop codified in the 2026-04-13 synergy audit. The full protocol lives in `agents/reflector-closeout.md` Phase 3 (Update Project Memory); the skill file is `skills/promote-lessons-to-wiki/SKILL.md`. Authoritative asymmetry is preserved: the project's `lessons_learned.md` is append-only source of truth, the wiki synthesis is a regenerable view. Firing is conditional (wiki must be reachable; lesson set must have changed; at least one lesson must be G/P-classifiable), and the outcome is recorded in reflection report §10.

## 8.6 Graphify Grounding Couplings (E.1 and E.2)

### Coupling E.1 — Graph-substrate snowball seeding (SK-33 `seed-snowball-discovery`)

At Ph1, the Planner dispatches **SK-33 `seed-snowball-discovery`** in two phases. The **seed phase** first follows the §1.5 wiki-first order (peer LLM wiki → Zotero → Scholar Gateway fall-through). The **iterate phase** then adds the graph-substrate variant: it traverses `${wiki_path}/graphify-out/graph.json` as the primary substrate before falling through to Scholar Gateway only for graph-stub seeds. Together the two phases materialise Coupling E.1 — previously roadmapped as the `graph-read-at-planner` placeholder in SK-20's §Dependencies (now retired; E.1 is implemented via SK-33's graph-substrate iterate phase as of v0.10.0-S1.5).

**SK-33 firing and fallback.** SK-33 fires at Ph1 when `wiki_linked: true`. The graph-substrate iterate path additionally requires `graph.json` to exist and its `captured_at` to be fresh per SK-20 Precondition 3. When the graph is absent or stale, SK-33 logs `[graph-stale]` in `reviews/snowball_log.md` and continues in external-verifier-only mode for that pass — a graceful degradation, not a full skill no-op (contrast: SK-20 performs a full-skill no-op and emits `sk20_noop_YYYY-MM-DD.json`). Additionally, if `inherit_snowball: true` in `reviews/classification.md` (default for wiki-linked projects), SK-33 auto-invokes **SK-36 `inherit-snowball-from-wiki`** at Phase 0 as a pre-seed step before its seed phase. SK-36 is Active as of v0.10.0-S6. The §6.0 coupling checklist exemption for S6 holds: Phase 0 is intra-SK-33 (not a new Step in `run-phase-1`); `run-phase-1` Step 4.5 already dispatches SK-33 as a unit — S6 does not edit any Step number in a phase-runner.

**Directionality.** Coupling E.1 and E.2 are both read-couplings (the pipeline reads from graphify's output) but fire at different agents and phases: E.1 fires at the Planner's Ph1 seed stage; E.2 fires at the Evaluator's pre-flight before every Ph2+ round. Together they close the graphify → pipeline feedback loop at both ends of the pipeline.

### Coupling E.2 — Graphify grounding overlay (SK-20)

Before every Evaluator round's Step 1 (Classification Gating), the Evaluator pre-flight invokes **SK-20 `graph-grounding-overlay`** to overlay graphify's knowledge-graph output (`knowledge/LLM wiki/graphify-out/graph.json` + `GRAPH_REPORT.md`) onto the manuscript's citation set. This is the Graphify → Pipeline feedback loop codified in the 2026-04-16 synergy analysis; it fires in the reverse direction from Couplings C and D (which write into the wiki) — SK-20 reads graphify's output and injects findings into the review. The full protocol lives in `skills/graph-grounding-overlay/SKILL.md`; the output is written to `reviews/graph_overlay_YYYY-MM-DD.md`.

**Deterministic gate first.** Before attempting SK-20, run:

`python scripts/sk20_preflight_gate.py --project-root "<project-root>" --date "YYYY-MM-DD"`

If `should_run_sk20` is false, SK-20 should not run. The gate script already emits:

- `reviews/coupling_readiness_YYYY-MM-DD.json`
- `reviews/sk20_noop_YYYY-MM-DD.json` (reason code + failed checks)

**Firing conditions (all must be true, else SK-20 no-ops cleanly):**

1. Project CLAUDE.md declares `wiki_linked: true` and `coupling_e_on_review: true`.
2. `knowledge/LLM wiki/graphify-out/graph.json` and `GRAPH_REPORT.md` exist.
3. The graph's `captured_at` timestamp is no older than the most recent `Last updated:` timestamp on the project's `references/REFERENCES.md` or `manuscript/main.md`.
4. `reviews/classification.md` exists (SK-20 uses it to tune P-stage severity adjustments).
5. The manuscript has at least one in-text citation.

**What the overlay produces.** Three finding types (all capped at MAJOR severity; BLOCKER escalation is the Evaluator's judgment call, not the overlay's): graph-stub citations (cited sources absent from the graph), section-location mismatches (manuscript cites §X; graphify locates the claim at §Y), and missing-citation candidates (graphify edges between cited and uncited sources). Every finding carries a graph-specific source tag (`[source: graph-extracted]` / `[source: graph-inferred]` / `[source: graph-stub]`) so downstream grounding-audit Category 8 can trace it back to the graph artefact.

**How the Evaluator consumes the overlay.** Step 1 reads `reviews/graph_overlay_YYYY-MM-DD.md` and folds each finding into its candidate list with the overlay's suggested severity as the starting point. The Evaluator may escalate (based on Step 2–7 judgment) or demote (if it disagrees with the overlay) — the overlay surfaces candidates; the Evaluator decides. Findings the Evaluator overrides must cite the reason in the consolidated findings report so the override is auditable.

When SK-20 no-ops, the Evaluator references `reviews/sk20_noop_YYYY-MM-DD.json` in the consolidated report to avoid silent Coupling E.2 dropouts.

**Authoritative asymmetry.** Graphify's graph is the source of truth for *what the graph contains*; the Evaluator's judgment is the source of truth for *what the review concludes*. SK-20 is the courier, not the judge.

**Relationship to Coupling D.** When SK-17 ingests an M5 paper into the wiki, it invalidates graphify's graph (the new source is not yet a node). The bootstrap-time coupling table in `PROJECT_BOOTSTRAP.md §4` records this as an implicit dependency: SK-17 fire → graphify re-run needed → SK-20 picks up the refreshed graph on the next review round.

---

## 9. Skill Development (Reflector capability)

The Reflector can create new reusable skills when it identifies recurring patterns across review rounds or projects. Skills are user-invocable shortcuts that encode a specific check, workflow, or fix pattern.

### Skill lifecycle

```
Pattern identified in Reflector Phase 2
    ↓
Reflector checks: recurrence? self-containment? invocability? distinctness?
    ↓ (all four criteria met)
Reflector drafts skill file using template in skills/SKILL_REGISTRY.md
    ↓
Reflector presents skill in reflection report §8
    ↓
User approves / defers / rejects
    ↓
If approved: Reflector writes skill file + updates SKILL_REGISTRY.md
If deferred: recorded for later re-evaluation
If rejected: recorded in "Considered but not created" (no re-proposal)
```

### Skill tiers

| Tier | Location | Scope |
|---|---|---|
| Package | `.paper-package/skills/` | Any project using this package |
| Project | `<project>/skills/` | One specific project |
| Global | `~/.claude/skills/` | All Claude Code sessions |

Default is package-level. The Reflector escalates to global only when the pattern is clearly not academic-writing-specific. It narrows to project-level when the pattern depends on project-specific constructs.

### Seed skills (created 2026-04-09)

Three skills were created during the package build, based on patterns identified in the INF3001 and INF3006Y reviews:

| Skill | Pattern | Source |
|---|---|---|
| `check-contradictions` | Theoretical contradiction between co-invoked sources | INF3001 Baumer/i* BLOCKER |
| `check-abstract-body` | Abstract promises not paid off in the body | INF3001 Haslam-not-operationalized BLOCKER |
| `quick-deterministic` | Running mechanical checks without a full review | Most common first action on any piece |

### How skills relate to the review pipeline

Skills are **shortcuts**, not **replacements**. Running `/check-contradictions` does not substitute for a full Evaluator review — it runs one specific check (SAFEGUARD_LAYER Check 4) in isolation. The user might invoke a skill when:

- They want a fast, targeted check before committing to a full review round
- They want to re-run a specific check after a Generator edit without re-running everything
- They want to verify a specific concern raised by a collaborator or reviewer

If a skill's output reveals a BLOCKER, the user should escalate to a full Evaluator review to assess the broader implications.

### Skill quality gate

Before the Reflector creates a skill, it must verify:

1. **The pattern is real** (appeared in actual review evidence, not hypothesized).
2. **The skill prompt is self-contained** (can execute without reading the user's prior conversation).
3. **The skill output format is consistent** with the package's findings format (severity tags, location references, verdict).
4. **The skill does not duplicate an existing skill** (check the registry).
5. **The skill does not override a package rule** (skills execute rules; they do not modify them).

If any gate fails, the Reflector records the pattern as a lesson instead of a skill.

---

---

## 10. Lifecycle Dispatch — Coordinating Milestones and Phases

Milestones and phases are orthogonal. Milestones name project deliverables and accepted handoffs. Phases name the revision/readiness state of the active artifact or sections. M1-M3 normally execute within Ph1; M4 spans Ph2-Ph3; M5 closes at Ph4. Neither vocabulary supersedes the other.

This section specifies their normal coordination and phase-conditioned agent dispatch. The canonical project-level deliverable, feedback, lineage, acceptance, and handoff contract is `MILESTONE_FEEDBACK_HANDOFF_PROTOCOL.md`; `PHASE_PROTOCOL.md` remains canonical for section revision/readiness.

### 10.1 Axis coordination

| Milestone | Artifact | Normal phase binding | Dispatch notes |
|---|---|---|---|
| **M1 — Project Memo** | `research_notes/project_memo.md` | **Ph1 Plan & Draft** | Generator writes the deliverable; Planner dispatches and records approval; no Evaluator engagement |
| **M2 — Annotated References** | `research_notes/annotated_references.md` | **Ph1 Plan & Draft** | Generator writes the deliverable; Planner dispatches and records approval; no Evaluator engagement |
| **M3 — Structured Outline** | `manuscript/outline.md` | **Ph1 Plan & Draft** | Generator writes a structured outline only; prose stubs belong to M4. |
| **M4 — Paper Draft** | `manuscript/main.md` | **Ph1 initial assembly → Ph2 Review & Revise → Ph3 Iterate & Converge** | Generator assembles the first complete draft in Ph1; Ph2 is the first Evaluator engagement; Ph3 is the converging dispatch stage with the unbounded loop, `convergence_metric` stability test, and Coupling E.2 graph-grounding overlay at Step 0.2 |
| **M5 — Final Paper** | `manuscript/main.md` (submission-bound depth) | **Ph4 Finalize & Close** | External verifiers required; G.4 mandatory; Reflector-full close-out; Coupling D wiki ingest via SK-16 |

The mapping coordinates two contracts rather than collapsing them. M1-M3 retain separate deliverable and handoff gates inside Ph1, where each approval advances only the milestone chain and does not exit Ph1. The Generator writes the exact M1-M4 deliverable bytes; the Planner records user/advisor feedback, approval, state, and F9 handoffs. M4 remains the manuscript deliverable from Ph1 initial assembly through Ph2-Ph3 review and convergence. M5 certifies the exact final manuscript bytes at Ph4. Machine-readable authority: `role_output_contract.v1.json`.

#### Native course-essay auto-walk

For the native `course-essay-four-milestones-v1` profile, `/run-draft` derives the first non-`accepted` milestone from `reviews/phase_state.json`. The Planner dispatches one deliverable at a time through a single-use receipt:

1. M1-M3: run the target gate without exemplar conditioning and with `--emit-receipt reviews/.harness/assignment/ready/gate_receipt_<target>_<utc>.json`. M4 and FINAL use the same mechanism after their additional predicates pass.
2. Planner runs `python scripts/assignment_dispatch_preflight.py --project-root <project-root> --receipt <ready-path> --expected-target <T> --consumer planner --write-path <primary-deliverable> [--write-path manuscript/revision_log.md]`. Exit 0 atomically reserves the receipt. Put the returned reserved path in `assignment_gate_receipt: <reserved-path>` and the target in `assignment_gate_target: <T>`; a non-zero result emits `APG-DISPATCH-REFUSED` and forbids dispatch.
3. Generator authors only receipt-scoped staged bytes, then invokes `assignment_writer_commit.py` with a target/role/token/path/hash-bound plan. The wrapper journals and publishes the exact reserved set, writes its result sidecar, and only then consumes the receipt; handled partial failure rolls back, while interrupted work resumes only from the exact journaled plan. Cancellation or a pre-commit abort invokes `assignment_receipt_invalidate.py`; receipts are never edited or reused. Record and adjudicate feedback through `MILESTONE_FEEDBACK_HANDOFF_PROTOCOL.md`, then stop at a user approval checkpoint.
4. After explicit approval only: finalize the existing F9 packet, atomically write the milestone event/status through the Planner's sole-writer transaction, validate with `milestone_framework_validate.py`, and end the invocation. The next invocation derives the successor and emits a new receipt.
5. At M3→M4: before F9 finalization, write `reviews/.harness/assignment/wiki_grounding_<round>.json` after the wiki-first pass and bind its exact path/hash in M3 `policy_evidence`, or bind an explicit user/advisor/instructor opt-out.
6. M4: require accepted M1-M3 plus current wiki evidence; exemplar conditioning may now use Yu for surface register and admitted Dennett for argument architecture only.
7. FINAL: run the final gate, requiring accepted M1-M4 and still-current wiki evidence; emit and preflight a FINAL receipt. The M4-onward exemplar envelope remains available.

The loop is checkpoint-driven orchestration, not unattended acceptance. A request for a complete paper cannot jump to M4 while M1-M3 are open. Producing a complete essay or `reviews/ph1_draft_completion.md` while any of M1-M3 is non-`accepted` is an explicit refuse condition and protocol violation. Legacy mode emits `APG-SEQUENCE-LEGACY` and names required migration/acceptance work; it never infers acceptance from files. Ph1-Ph4 continue to govern revision maturity independently of this assignment sequence.

### 10.2 Dispatch per milestone

#### M1 deliverable — Project Memo (at Ph1 sub-phase 1)

```
Planner (Ph1 bootstrap; reads classification.md for P-stage; populates ph1_pstage_declaration)
  → Generator (drafts memo under P-stage register; diff-scoped, full-file grounding applies)
  → Reflector-lightweight (optional integrity probe; no lessons_learned.md write)
```

**Planner Ph1 criteria for the memo** (derived from `general_research_project_guidelines.md` Milestone 1, applied at Ph1 sub-phase 1):

| Check | What it verifies |
|---|---|
| Focus specificity | Is the phenomenon defined concretely, not as a buzzword? |
| Tension identification | Is there a literature clash or contested definition? |
| Terms interrogated | Are problematic terms listed and their assumptions unpacked? |
| Forward-pointing questions | Are candidate q-items (q-α, q-β, q-γ) present? (Not numbered RQs at P0/P1.) |
| Snowball strategy | Are core sources identified with tracks for expansion? |
| Argumentative framing | When the memo claims a disciplinary placement or integration (e.g., "Problem X belongs in Discipline Y"), are existing research programs named that demonstrate the claimed integration? Presence of claim ≠ demonstration of claim. |
| Premise mapping | When the memo introduces theoretical premises (e.g., "Actors are provisional stabilizations" + "We use models"), are potential internal tensions between premises identified and noted for resolution at Ph2? |

**Deterministic checks at Ph1:** Run the mandatory DETERMINISTIC_CHECKS.md subset on the memo text under the unconditional Grounding Protocol. The Evaluator does not engage at Ph1, so the deterministic checks are run by the Planner as part of the pre-phase-advance check (clause (g) of `pre_phase_advance_check.py`).

#### M2 deliverable — Annotated References (at Ph1 sub-phase 2)

```
Planner (Ph1; coordinates with M1 deliverable)
  → Generator (drafts annotations under P-stage register)
  → Reflector-lightweight (optional)
```

**Planner Ph1 criteria for the annotated references** (derived from `general_research_project_guidelines.md` Milestone 2, applied at Ph1 sub-phase 2):

| Check | What it verifies |
|---|---|
| Contribution to tension | Does each annotation state how the source informs the research questions? |
| Track assignment | Is each source assigned to a snowball track? |
| Quotation discipline | Are direct quotes flagged with page numbers and never paraphrased silently? |
| Coverage of core sources | Are the core sources identified at M1 actually annotated? |
| P-stage discipline | Does the annotation set match the declared `ph1_pstage_declaration`? (P0: exploratory; P1: candidate-bounded; P2: claim-bounded.) |

#### M3 deliverable — Structured Outline (at Ph1 sub-phase 3)

```
Planner (Ph1 — orchestrates outline sub-phase)
  → Generator (writes the structured outline; no prose stubs)
  → Reflector-lightweight (optional)
```

**Planner Ph1 criteria for the outline:**

| Check | What it verifies |
|---|---|
| Section coverage | Does the outline have one entry per top-level section that will be drafted during M4 initial assembly in Ph1 and reviewed across Ph2-Ph3? |
| Deliverable path | Is `phase_deliverable_path` populated with the outline file's path? |

#### M4 dispatch stage — Initial manuscript assembly at Ph1

```
Planner (requires accepted M1-M3 and a preflighted M4 receipt)
  → Generator (assembles the first complete manuscript at manuscript/main.md)
  → Planner (runs deterministic and grounding gates; presents M4 draft checkpoint)
```

M4 initial assembly completes Ph1 drafting maturity; it does not engage the
Evaluator. Only after the Ph1 exit gate and explicit phase approval may the
project advance to Ph2.

#### M4 dispatch stage — Review-ready draft at Ph2

```
Planner (runs pre_phase_advance_check.py clauses (a)(b)(d)(e)(g) for Ph2 entry)
  → Evaluator (FIRST ENGAGEMENT — full local-scope pass on changed sections; Confirmation Mode RETIRED)
  → Planner (merges findings into revision_plan.md)
  → Generator (applies findings under declared P-stage register)
  → Evaluator (re-check mode — full local pass; EG-3 cross-scope reference scan)
  → Reflector-lightweight (optional integrity probe)
```

Ph2 is the first rung that engages the Evaluator. The Rule 1 phase-gated digest exception **does not apply** at Ph2; full-file reads are mandatory.

#### M4 dispatch stage — Converging draft at Ph3

```
Planner (runs pre_phase_advance_check.py clauses (a)(b)(c)(d)(e)(g) for Ph3 entry; sets ph3_last_activity_at on advance)
  → Evaluator (full-scope pass; external verifiers OPTIONAL; Coupling E.2 SK-20 overlay at Step 0.2)
  → Planner (merges; updates convergence_metric)
  → Generator (applies findings; Linear-Accountability defence — ESCALATED findings require named owner)
  → Evaluator (re-check; W-Ph3-DRIFT-EXCEEDED-TOLERANT on tolerant-mode exceedance — warning, not forced re-review)
  → Reflector-lightweight
```

Ph3 is unbounded. Convergence is signalled when `convergence_metric < 0.03` for two consecutive rounds → `[CONVERGENCE-STABLE]` warning emitted and TerminalSignoffRow flips `current_phase: Ph3 → Ph3_converged`. The `[Ph3-STALE]` flag is computed from `ph3_last_activity_at` against wall-clock and the `ph3_stale_budget_days` budget; null `ph3_last_activity_at` short-circuits to false (Option A — no persisted staleness field).

#### M5 deliverable — Final Paper at Ph4

```
Planner (runs MCR admission check; rejects with [MCR-FIRST-RESPONSE] if any section is below Ph3_converged or [Ph3-STALE])
  → Evaluator (full-scope pass; external verifiers REQUIRED — Zotero, Scholar Gateway, Coupling E.2 ≥15% threshold;
              register-specific passes conditional; G.4 MANDATORY — Row 8.5 must be CLEAN)
  → Planner (merges)
  → Generator (final edits under submission-bound register)
  → Evaluator (re-check)
  → Reflector-FULL (five-phase close-out: Phase 1 evidence, Phase 2a + Phase 2b NEW-H-4 aggregated
                   confirmation-failed history audit, Phase 3 lessons → lessons_learned.md,
                   Phase 4 skill proposals, Phase 5 memory → DO_NOT_DISTURB.md;
                   attempts Coupling C/D Wiki mutation (deferred: `WIKI_WRITE_TRANSACTION_UNAVAILABLE`; non-blocking for Phase 4 completion) →
                   m5_wiki_ingest success trigger only after future governed ingestion; on deferral do not write the success trigger)
  → Planner (writes terminal user_approval row with new_phase: "Ph4", terminal_phase_reached: true)
```

Ph4 is the strict superset of Ph3. **Legal Ph4 → Ph3 demotions** at v0.8.0: EG-1 (`eg1_ph4_downgrade_to_ph3`, trigger 23) on Rule 1–7 grounding violation; EG-7 (`eg7_mcr_readmission_after_class_change`, trigger 22) when `reviews/classification.md` changes after MCR admission. Both demotions emit a TerminalSignoffRow → ReengagementSignoffRow pair and refresh `ph3_last_activity_at`.

### 10.3 Historical phase-ledger migration

Projects that originated under the v0.6.0 milestone framing migrate via `scripts/migrate_v060_to_v070.py [retired from tree]`. The script:

- Maps the project's most recent milestone tag (in `reviews/round_program.md` or in the v0.6.0 `tier_state.json`) onto the v0.7.4 phase per the §10.1 coordination table.
- Injects `phase_goal_declared` defaulted to the milestone deliverable name (e.g. "M3 deliverable — Structured Outline").
- Injects `phase_deliverable_path` defaulted to the canonical artifact path from §10.1.
- Sets `ph3_last_activity_at` to the migration timestamp for sections at `Ph3` (so the staleness clock starts at migration, not at the unknown v0.6.0 last-activity).
- Emits a `migration_report_hold` row in `phase_entry_log` that the Planner must resolve before the next Ph2 dispatch — typically by user confirmation that the inferred phase and goal are correct.

That retired script migrated the historical phase ledger only. It does not establish current milestone deliverable, feedback, approval, or lineage evidence. Native and legacy milestone state now follow `MILESTONE_FEEDBACK_HANDOFF_PROTOCOL.md`; migration never infers acceptance from the historical phase mapping.
