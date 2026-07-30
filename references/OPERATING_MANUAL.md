# OPERATING_MANUAL — Full Runbook for the Research and Academic Paper Writing Package

**Typed output boundary.** Use `references/role_output_contract.json` 3.0.0 as the machine authority for the six fixed roles and nine triggered F1-F9 classes. The path lists in this manual are explanatory. File presence and legacy readability do not prove shipment-v2 application, acceptance, or terminal state.

*For the reader who is inheriting the package cold, or who wants the complete operational picture. If you just need to start using it, read `QUICKSTART.md` first.*

**Scope.** This manual describes how to run the package day-to-day: what to do before the first session, what to do on every session, how to invoke each of the seven phases, how to read the artifacts produced, how to recover when something goes wrong, and how to sustain the benefits over time. It is a *how* document — the *what* (rules, checks, agent prompts) lives in the component files and is referenced here rather than duplicated.

**Precedence.** This manual is a teaching surface. Its rulings lose to every component file and to every higher-precedence source in `CLAUDE.md §4`. Where a rule stated here appears to conflict with `AGENT_ORCHESTRATION.md`, `REVIEW_ORCHESTRATION.md`, `ROUTING_SPINE.md`, or `AGENT_CONTRACTS.md`, the component file wins.

---

## 1. What the package gives you

The package turns a generic AI coding/writing assistant into a research partner with four properties a generic assistant does not have: *phase discipline* (every request is routed to one of seven named phases with declared entry and exit gates), *agent separation* (the writer, the reviewer, the planner, and the learner are different actors with non-overlapping permissions), *integrity gating* (mechanical and coherence checks that must pass before submission), and *cross-round memory* (lessons accumulate in a project-scoped and package-scoped ledger). The four properties are load-bearing. Losing any one of them produces a familiar failure mode: prose edits that trace to nothing, reviews that bless what they wrote, plans that contradict themselves, and the same mistake three months later.

The operational goal of this manual is to help you preserve all four properties without having to memorise any single file.

---

## 2. Pre-requisites and one-time setup

### 2.1 Directory layout

The package is deployed at `Research/.paper-package/`. The Research root folder contains: (a) `CLAUDE.md` — the root-level harness entry point (`RESEARCH_ROOT_CLAUDE.md` in this package is the canonical template); (b) `conductor.md` — the live ledger of active projects; (c) one subfolder per research project, each following the standard project structure defined in `PROJECT_BOOTSTRAP.md §7`.

### 2.2 First-session checklist

Before your first real round, confirm:

*The harness is wired.* `Research/CLAUDE.md` exists and delegates to `.paper-package/`. Open it; it should mention the package location in its §2 and precedence rules in §5. If not, copy `RESEARCH_ROOT_CLAUDE.md` to `Research/CLAUDE.md`.

*The conductor is seeded.* `Research/conductor.md` exists. If not, ask Claude: *"Seed the conductor per `PARALLEL_CONDUCTOR.md §8`."* Claude will walk the tree, infer each project's current phase and round from its `reviews/` and `research_notes/` artifacts, draft the ledger, and present it for your approval. Do not edit the conductor by hand without telling Claude — it is Claude's primary means of knowing which project is in which phase at session start.

*External verifiers are registered.* If you maintain a Zotero library and want submission-bound rounds to pass `GROUNDING_PROTOCOL.md` Rule 7a, confirm the Zotero MCP is operational. `EXTERNAL_VERIFIERS.md` declares it as the default Class 1 verifier in Joseph's deployment. Without a verifier, submission-bound rounds will block at G.4.

*Skills are visible.* `.paper-package/skills/SKILL_REGISTRY.md` lists the skills available. The seed skills (`check-contradictions`, `check-abstract-body`, `quick-deterministic`, `suchman-register-audit`) should resolve. New skills created by the Reflector are appended here.

### 2.3 Knowing which CLAUDE.md Claude is reading

Three `CLAUDE.md` files sit in the chain. Ordered from outermost to innermost: the user's home-folder CLAUDE.md if any, the Research root CLAUDE.md, and each project's own CLAUDE.md. Claude should read them in that order and apply the precedence rules in `CLAUDE.md §4`. If you suspect Claude is using stale rules, the quickest reset is *"List which CLAUDE.md files you have read this session and in what order."*

---

## 3. The session contract

Every session begins and ends the same way. The contract is short.

**Opening.** Claude reads, in order: the Research root `CLAUDE.md`, the package `CLAUDE.md`, `ROUTING_SPINE.md`, `Research/conductor.md`, the project's own `CLAUDE.md`, and the project's `research_notes/directives.md`. Claude then confirms to you (a) which project the session concerns, (b) which phase it is in per the conductor, and (c) what it expects to do first. Nothing else happens until you acknowledge.

**Mid-session.** Every user utterance is classified into one phase by `ROUTING_SPINE.md §2`. The Planner dispatches one agent at a time with a prompt that names the phase, the entry artifact, and the exit gate. The agent operates under the contract in `AGENT_CONTRACTS.md §§1–4`. At every `► PRESENTS TO USER ◄` checkpoint in `AGENT_ORCHESTRATION.md §3`, you approve, modify, dispute, or reject. The round advances only on approval.

**Closing.** Claude updates `conductor.md` with current phase, round number, and a one-sentence "resume here" note; checkpoints any in-progress artifacts; summarises in a single paragraph what was done and what is pending. If a round was completed, the Reflector has run and `reviews/reflection_report.md` exists.

If any of opening / mid / closing is skipped, the next session will cost you time to recover the state the skipped step was supposed to preserve.

---

## 4. The seven phases in operational detail

The dispatch table is in `ROUTING_SPINE.md §2`. This section elaborates the *doing* of each phase.

### 4.1 Think (M1 — Project Memo)

**Purpose.** Interrogate the problem before any argument is committed to paper. Define the phenomenon concretely, name one or more tensions in the literature, list the terms whose assumptions need unpacking, and surface candidate questions (q-α, q-β, q-γ) that the later drafts will sharpen into RQs.

**Invocation.** *"Bootstrap a new project on X, targeting venue V, paper type T."* Claude reads `PROJECT_BOOTSTRAP.md`, gathers missing inputs (your advisor, the submission deadline, the paper's expected length, the empirical corpus if any), creates the standard directory tree, and seeds the project `CLAUDE.md`. Then the Planner classifies the project (paper type + P-stage per `project_writing_style_checklist.md`), and the Generator drafts `milestones/M1_project_memo.md`.

**What you will be asked to decide.** The paper type (conceptual / empirical / position / methodological / tool / case-study), the P-stage (P0 problem-finding / P1 problem-framing / P2 problem-solving), the venue, and whether any style commitments (C-1…C-4 per `STYLE_COMMITMENTS.md`) are in force.

**Exit gate.** `ROUTING_SPINE.md §3` row 1 must pass: phenomenon concrete, tension named, q-items listed, snowball strategy declared. The Evaluator certifies.

**Common mistake.** Starting to write the introduction during M1. Resist. The memo is not the intro; it is the argument that the intro will eventually need to carry. An intro written before the memo clears its gate routinely requires a full rewrite after M3.

### 4.2 Plan (M2 — Annotated References, and M3 — Structured Outline)

**Purpose.** Build the scaffolding. M2 lays down the literature that will carry the argument; M3 lays down the argument that the literature will serve.

**M2 invocation.** *"Build annotated references for the memo, following the snowball strategy."* Generator drafts `milestones/M2_annotated_references.md`; Evaluator checks each annotation for contribution-to-tension, track assignment, and coverage balance. The output is not a summary of papers but a working catalogue of who-says-what-and-what-does-that-do-for-us.

**M3 invocation.** *"Outline the paper against the annotated references."* Generator drafts `milestones/M3_argument_evidence_outline.md`; Evaluator checks for argument skeleton visible from outline alone, tension threaded intro-through-conclusion, framework critique slot present, synthesis slot for unresolved questions. The outline is the moment to make structural decisions you do not want to make later.

**Exit gates.** `ROUTING_SPINE.md §3` rows 2 and 3.

**Common mistake.** Treating M2 and M3 as bookkeeping and rushing them. The Evaluator criteria here are the ones that, violated, will produce the "blinding glimpse of the obvious" failures in M4 — missing theoretical grounding, missing framework critique, argument that does not pay off the introduction's promise. Every hour spent on M2/M3 saves several in M4 rewrites.

### 4.3 Build (M4 initial — Paper Draft)

**Purpose.** Produce a full manuscript pass from outline to prose. Every outline node gets at least one paragraph. No `TODO` / `TKTK` / `[?]` markers at the end.

**Invocation.** *"Co-author §N"* (targeted) or *"Draft the paper against the outline"* (full pass). The Generator writes to `milestones/M4_complete_paper_draft.md`; the revision log is opened. The Generator is the **only** agent that writes prose. At this phase the Generator also honors `GROUNDING_PROTOCOL.md` on every claim — no citation enters the draft without the source being readable from the project or from a registered verifier.

**Exit gate.** `ROUTING_SPINE.md §3` row 4.

**Common mistake.** Letting the Generator improvise beyond the plan. Discretionary edits above ~20% of round changes are a signal that the outline (M3) was insufficient; the Planner should flag this and ask whether the scope has shifted.

### 4.4 Review

**Purpose.** Subject the draft to the seven-step pipeline in `REVIEW_ORCHESTRATION.md`. Step 1 (reader, red thread), Step 2 (claims, hedging, positioning), Step 3 (project lifecycle fit), Step 4 (structure, narrative), Step 5 (citations, typography), Step 6 (sentence craft), Step 7 (integrated checklist). Step 0a is a mechanical pre-flight in the Test phase; Step 8 is the synthesis (consolidated report); Step 8.5 is the Safeguard Layer.

**Invocation.** *"Run a full review"* or *"Critique §N at depth D"*. The Evaluator dispatches. Each step writes its findings to `reviews/step_findings/step_N_*.md`. Step 8 is the consolidated report you will actually read.

**Gate-first default.** Before dispatching the Evaluator, run `scripts/run-evaluator-preflight.ps1` from the project root. This emits `reviews/coupling_readiness_YYYY-MM-DD.json` every round and `reviews/sk20_noop_YYYY-MM-DD.json` whenever Coupling E.2 preconditions fail.

**What you see.** The consolidated report has severity-tagged findings (BLOCKER / MAJOR / MINOR), each with (a) a location in the artifact, (b) the rule source (file + section), (c) a proposed fix. You approve, dispute, or defer each finding. The Planner then merges approved findings into `revision_plan.md` as actions for the Generator.

**Exit gate.** `ROUTING_SPINE.md §3` row 5.

**Common mistake.** Disputing findings without citing an authority. If you disagree with a finding, either cite a higher-precedence source (venue guide, advisor instruction, prior user directive) or ask the Reflector to consider adding it to `research_notes/directives.md`. Un-reasoned disputes are a drift vector.

### 4.5 Test

**Purpose.** Certify that the manuscript survives mechanical and coherence checks before it attempts to ship. Test is not Review; Review is judgment-based, Test is adversarial and mostly automated.

**Invocation.** *"Run the deterministic pass"* / *"Run the safeguard layer"* / *"Check citations"* / *"Run the drift check"* / *"Run the reflexivity check"*. Each runs the corresponding component file's procedure.

**What gets checked.**
- `DETERMINISTIC_CHECKS.md` — grep/count patterns (anti-LLM-tic sweep, triadic-list density, em-dash rules, bibliography key integrity, number reconciliation).
- `SAFEGUARD_LAYER.md` — six integrity checks (regression, drift, consistency, contradictions, traceability, voice).
- `DRIFT_CHECK.md` — MASTER / component reconciliation (Reflector Phase 2.6).
- `REFLEXIVITY_CHECK.md` — substitution-vs-augmentation audit (Reflector Phase 2.7).
- `EXTERNAL_VERIFIERS.md` — cited-claim verification at submission-bound depth (`GROUNDING_PROTOCOL.md` Rule 7a).

**Exit gate.** `ROUTING_SPINE.md §3` row 6. Every gate must be CLEAN or RESOLVED.

**Common mistake.** Running Test before Review is done. Test without Review catches syntactic drift but not argumentative drift; Review without Test catches argumentative drift but not the mechanical tics that advisors and reviewers notice first. Run Review, then Test, then generate fixes, then re-Test, then ship.

### 4.6 Ship (M5 — Final Paper)

**Purpose.** One-shot submission-ready certification. Runs exactly once per submission boundary.

**Invocation.** *"Is it ready?"* (Evaluator reads the state and answers yes/no with reasons) then *"Do the G.4 sign-off"* (Evaluator runs the full G.4 protocol from `MASTER_research_and_paper_guidelines.md` Part G.4).

**What the G.4 protocol checks.** Every Constitution row's sign-off condition; every submission-readiness criterion from `SUCCESS_METRICS.md §7.1` including the 2026-04-13 additions (Drift CLEAN; External verification complete; Reflexivity resolved); venue-specific formatting per the call for papers; `DO_NOT_DISTURB.md` frozen rules unchanged.

**Exit gate.** `ROUTING_SPINE.md §3` row 7. G.4 signoff file written, countersigned by you.

**Common mistake.** Asking for G.4 on a draft that has not cleared Test. G.4 will refuse and tell you which gate is blocking; this is correct behaviour. Fix the upstream gate and try again.

### 4.7 Reflect

**Purpose.** Close the round. Extract lessons. Update memory. Propose improvements.

**Invocation.** *"Retro this round"* or (automatic at the end of a full loop). The Reflector reads every artifact the round produced, cross-references prior lessons in `research_notes/lessons_learned.md`, runs Drift and Reflexivity checks (Phases 2.6 and 2.7), and writes `reviews/reflection_report.md`.

**What you see.** The reflection report has: round summary, patterns observed, proposed directives, proposed skills, drift verdict, reflexivity verdict, contract-audit results. Proposed directives arrive marked `[PROPOSED]` and do not become binding until you approve.

**Exit gate.** `ROUTING_SPINE.md §3` row 8.

**Common mistake.** Treating the reflection report as a formality. Over a year of rounds, the lessons in `research_notes/lessons_learned.md` become the most valuable document in the project. Read them. The patterns the Reflector surfaces are the ones most likely to recur on the next paper.

---

## 5. Canonical round — the standard sequence

A full round for an M4/M5 manuscript proceeds:

1. Planner reads state, classifies, produces `reviews/revision_plan.md`. **Present to user.**
2. Run `scripts/run-evaluator-preflight.ps1` (gate + coupling health update).
3. Evaluator runs Steps 0a–8, records routine check evidence under `reviews/.harness/evidence/<event_id>.json`, and returns a short action list; the Planner may still assemble `reviews/consolidated_findings_report.md` on **exception paths** (blocker, verifier failure, or explicit user request). **Present to user** at decision checkpoints.
4. Planner merges approved findings into the revision plan. **Present to user.**
5. Generator applies edits, logs in `manuscript/revision_log.md`, self-checks. **Present to user.**
6. Evaluator re-checks (regression, drift, spot-check of top fixes). **Present to user.**
7. If clean: Reflector runs. Else: back to step 5.
8. Reflector writes `reviews/reflection_report.md`. **Present to user.** Round complete.

Shortened paths are permitted and named in `AGENT_ORCHESTRATION.md §3`. The only step that is non-negotiable is the Reflector pass at the end.

---

## 6. Invoking by agent role

For cases where you know exactly which agent you need:

| Utterance | Agent | Reads | Writes |
|---|---|---|---|
| *"Run the planner"* | Planner | user utterance, classification, directives, prior reflection | `classification.md`, `revision_plan.md` |
| *"Evaluate the manuscript"* | Evaluator | manuscript, review-orchestration, integrity-gate files | F7 evidence packets, short action list; legacy Markdown findings on exception paths |
| *"Co-author §N"* / *"Write the intro"* | Generator | revision plan, findings, rule files, grounding protocol | `main.md`, `revision_log.md` |
| *"Reflect on this round"* | Reflector | every round artifact, prior lessons, skill registry | `reflection_report.md`, `lessons_learned.md` |

Each dispatch loads the agent's full prompt from `agents/<role>.md` and honors the contract in `AGENT_CONTRACTS.md`.

---

## 7. Skill invocations

Skills are targeted shortcuts. Available in the current deployment:

- `/quick-deterministic` — invoke `scripts/audit/run_all.py` and summarize `reviews/findings.json`, no Review. (The script is the runtime; `DETERMINISTIC_CHECKS.md` is rule rationale, not a runtime artifact.)
- `/check-contradictions` — run SAFEGUARD Check 4 (theoretical contradictions between co-invoked sources) in isolation.
- `/check-abstract-body` — run the abstract-vs-body promise audit.
- `/suchman-register-audit` — check C-1 (Suchman commitment) register consistency.

`/quick-deterministic` is a mechanics diagnostic, not governed product or
lifecycle evidence. From a source checkout, the one-command governed route is:

`python scripts/run_product_gate.py --mode governed-product --project-root "<project-root>" --artifact "<manuscript>" --out-dir "<shipment>/product-gate" --wiki-root "<wiki-root>" --semantic-receipt "<evaluation-semantic-receipt>" --verifier-transaction "<evaluation-verifier-transaction>" --verifier-publication-manifest "<evaluation-verifier-publication-manifest>" --verifier-commit-marker "<evaluation-verifier-commit-marker>"`

It fails closed unless the exact evaluation-verifier publication and claim
consumption bind the artifact, semantics, wiki root, and transitive inputs.

Use a skill when you want a fast, targeted check without dispatching a full agent. If a skill surfaces a BLOCKER, escalate to a full Evaluator round to understand the broader implications. The Reflector proposes new skills when a pattern recurs across rounds or projects; they appear in `references/SKILL_REGISTRY.md` with their phase, input, output, and quality tier.

---

## 7.5 Wiki-facing couplings (SK-14 / SK-15 / SK-16 / SK-17)

If you maintain a peer `LLM wiki/` store alongside `Research/`, four skills connect them. These materialize the four couplings codified in the 2026-04-13 Synergy Program M0; the authoritative summary lives in `LLM wiki/wiki/syntheses/synergy-program-m0-completion-2026-04-13.md`, and this subsection is an operator's summary — consult the synthesis page for design rationale and the individual skill files for the full protocol.

**What each skill does and when it fires.**

| Skill | Coupling | Direction | Trigger |
|---|---|---|---|
| `/promote-lessons-to-wiki` (SK-14) | C | Research → Wiki (lessons → syntheses) | **Automatic.** Reflector Phase 3.5, every round, if the round produced lesson changes and at least one is G/P-classifiable |
| `/backfill-source-stubs-from-references` (SK-15) | A-revised | Research → Wiki (REFERENCES → source stubs) | **On demand.** Invoke when a project's REFERENCES outgrows the wiki's source corpus |
| `/retrofit-concept-grounding` (SK-16) | B | Within Wiki (sources → concept-page citations) | **On demand.** Invoke after SK-15 populates new stubs, or when a concept page is asserting ungrounded claims |
| `/ingest-m5-to-wiki` (SK-17) | D | Research → Wiki (final paper → source, full read) | **Milestone-triggered.** Fires at M5 close-out after G.4 sign-off; expects project CLAUDE.md to declare `wiki_linked: true` and `coupling_d_on_m5: true` |

**How to control what fires.** Every project's CLAUDE.md declares its wiki-facing interface via the fields registered by `PROJECT_BOOTSTRAP.md §3 Step 5`:

- `wiki_linked: true | false` — master switch. If false, no coupling fires.
- `coupling_c_active: true | false` — per-round SK-14 promotion (default: same as `wiki_linked`).
- `coupling_d_on_m5: true | false` — M5 SK-17 self-ingestion (default: same as `wiki_linked`).

You can suppress per-round promotion while keeping M5 ingestion, or vice versa. Changing the flags after bootstrap is supported — just edit the project CLAUDE.md and the next Reflector round honors the new settings.

**The chain composes.** SK-15 populates stub sources. SK-16 consumes those stubs (and any full-read sources) to ground concept pages. SK-14 uses the now-grounded concepts and sources as wikilink targets when it writes syntheses. SK-17 replaces stubs with full-read source pages at M5 and queues further concept-page retrofits for a subsequent SK-16 sweep. Each skill has an explicit "do not do" list naming the others' work; if you see one skill doing another's job, file it as a lesson.

**Preserved invariants.** Project files (`lessons_learned.md`, `milestones/M4_complete_paper_draft.md`, `references/REFERENCES.md`) remain authoritative and append-only. Wiki pages are regenerable views — if a wiki page and a project file disagree, the project file wins. Source pages carry `grounding_status` frontmatter (`stub` | `retrofit <date>` | `full`) so the audit trail survives.

**When things go wrong.** Recovery patterns: if SK-14 writes a synthesis that misrepresents a lesson, fix the lesson in the project file and re-invoke SK-14 — regeneration behavior is a no-op when the lesson range hasn't changed, and an overwrite when it has. If SK-16 fabricates a citation or invents a source, that is a grounding-protocol violation and should be escalated to a full Evaluator round. If SK-17 fails at M5, the manuscript is not blocked — it is already signed off via G.4; SK-17's failure means the wiki source page has to be manually written from the `LLM wiki/CLAUDE.md §Operations / Ingest` protocol, and the failure should be filed as a lesson for the next Reflector round.

---

## 8. Multi-project operation

Most PhD weeks are multi-project. The conductor makes this safe.

**Default model — L1 cross-project parallel** (`PARALLEL_CONDUCTOR.md §3`). Every project is isolated: its own directory, its own `CLAUDE.md`, its own directives, its own lessons. Package-level directives and the `GROUNDING_PROTOCOL.md` apply everywhere; project directives stay in their project.

**When to use L2 (intra-project cross-phase).** Only when a Round-N Reflector pass is long and you need to start Round-N+1 Planning concurrently. The Reflector's reads are frozen; the Planner's writes go to new files. Forbidden: two concurrent Generators on the same manuscript.

**When to use L3 (intra-phase parallel).** Only for large manuscripts with genuinely decoupled sections, and only for Evaluator or Reflector (never Generator). The Planner must authorize and log it in the conductor.

**Switching projects mid-session.** Name the project explicitly: *"Switching to RE2026_agency_delegation."* Claude writes a handoff note on the exiting project, updates the conductor, then opens the new project's `CLAUDE.md` and directives. Do not switch implicitly; it is the single most common source of directive bleed.

---

## 9. Recovery — when things go wrong

### 9.1 The agent wrote to the wrong file

The Evaluator wrote to `milestones/M4_complete_paper_draft.md`. The Generator wrote to `reviews/`. Either is a contract violation. Run *"Contract audit per `AGENT_CONTRACTS.md §6`"*. The audit reads the round's file writes and names every invariant violation. Revert the violating writes from git (or from `DO_NOT_DISTURB.md`-style snapshots if git is not available) and re-dispatch the correct agent.

### 9.2 A phase advanced without its gate

The Planner moved from Review to Ship without Test certifying CLEAN. Run *"Run the exit gate for the current phase"*. The gate either clears (in which case the advance was fine, and you should record the evidence) or fails (in which case the advance must be rolled back and the gate remediated).

### 9.3 Directives are bleeding across projects

A CAiSE-specific rule is being applied to an RE 2026 draft. Run *"Check directive scope per `RESEARCH_ROOT_CLAUDE.md §6`"*. Reflector should flag the bleed; Planner should cease applying the out-of-scope directive; the Reflector may propose promoting it to package-level on user approval, or restrict it to its origin project.

### 9.4 The Generator introduced regressions

The Evaluator's re-check catches them. The Planner re-dispatches the Generator with a narrowed plan targeting only the regressions. The Reflector records why the Generator's self-check missed them and proposes a deterministic pattern or skill to catch the class.

### 9.5 The Evaluator missed a defect

The Reflector catches it on round close by comparing what the Evaluator found against what is in the text. The Reflector proposes a new check or skill. The user approves.

### 9.6 Context window is exhausted on a long manuscript

Invoke `TOKEN_BUDGET_PROTOCOL.md`. It defines manuscript size classes, segmentation rules, and the state-preservation protocol that lets a review resume from a cold session. Do not just paste more and hope.

### 9.7 Two agents disagree

The Planner mediates. You make the final call. The disagreement is recorded in the next reflection report so the pattern can be studied.

### 9.8 A cited source cannot be verified

`GROUNDING_PROTOCOL.md` Rule 7a forces the issue: at submission-bound depth, every cited claim must verify through `EXTERNAL_VERIFIERS.md` (Zotero MCP, registered scholarly-search tools, or local `.bib` resolver). If a claim cannot verify, the Generator retracts the claim or replaces it with a verifiable one; the Evaluator will not sign G.4 until this is resolved.

---

## 10. Reading the artifacts

The package produces many files per round. In order of importance to you as a reader:

1. `reviews/final_round_report_<round_id>.md` — normal reader-facing synthesis after round close (F8). Assembled from evidence packets and the revision log.
2. `reviews/.harness/evidence/<event_id>.json` plus `reviews/.harness/events.jsonl` — machine-readable audit trail for routine checks (F7). Read when you need drill-down beyond the final report.
3. `reviews/reflection_report.md` — what the Reflector learned, plus any proposed directives or skills awaiting your approval.
4. `manuscript/revision_log.md` — per-round append-only log of what the Generator changed and why.
5. `reviews/revision_plan.md` — the current action list.
6. `research_notes/lessons_learned.md` — the accumulated cross-round memory for this project.
7. `reviews/G4_signoff.md` — submission-bound sign-off, when it exists.

Routine review evidence is recorded in `reviews/.harness/evidence/<event_id>.json` and indexed by `reviews/.harness/events.jsonl`. The normal reader-facing artifact for a closed round is the round-close report at `reviews/final_round_report_<round_id>.md`.

Do not write `reviews/consolidated_findings_report.md` as a routine per-review output for new rounds. Use that path only as a **backward-compatibility pointer** for in-progress projects that already expect it, or as an **exception report** when a blocker, unsafe edit condition, verifier failure, or explicit user request requires a human-facing Markdown report before round close.

The other artefacts (legacy per-step findings, deterministic pass results, safeguard layer results, drift and reflexivity check outputs) are supporting evidence; read them when you are disputing a finding or diagnosing a failure.

---

## 11. Sustaining the package over time

The package gets better the more rounds it runs, but only if the Reflector's output is absorbed. Three maintenance habits make the difference.

**Read every reflection report.** Not all of it; skim the Patterns section. Patterns that recur across three rounds are near-certain skill candidates. Patterns that recur across two projects are package-level directive candidates.

**Keep `research_notes/directives.md` clean.** When a directive is approved, state (a) the rule, (b) the rationale, (c) the scope (project / venue / package), and (d) an expiry or review date. Expired directives should be removed, not left in place.

**Run `DRIFT_CHECK.md` at least once per submission cycle.** Even if the gate is not triggered automatically, running the check surfaces MASTER/component drift that has accumulated in the background. A recent drift pass is visible in `DRIFT_LOG.md`.

---

## 12. When to deviate from this manual

Three cases where the manual should yield.

*When a venue requires something the manual does not cover.* The venue author guide wins (precedence 2 in `CLAUDE.md §4`). File the requirement in the project's `research_notes/directives.md` with `[venue-override]` scope.

*When the advisor says something the manual does not cover.* The advisor wins (precedence 3). File in `research_notes/directives.md` with `[advisor-override]` scope, citing the source (email, meeting note, comment on draft).

*When you — the user — want to override for a reason the system cannot know.* You win (precedence 1). State the override in the conversation, and the Planner files it in `directives.md` so future sessions respect it. Do not rely on verbal overrides that live only in conversation memory; they will not survive a session boundary.

Everywhere else, trust the manual and the component files. They are the condensed product of many rounds.

---

## 13. Glossary of essential files (where to look when in doubt)

| File | When to open it |
|---|---|
| `ROUTING_SPINE.md` | First, always. Phase dispatch + exit gates. |
| `AGENT_ORCHESTRATION.md` | Four-agent architecture, loop, shortened paths, lifecycle dispatch. |
| `REVIEW_ORCHESTRATION.md` | Review pipeline: classification, per-step protocol, findings format. |
| `AGENT_CONTRACTS.md` | Per-agent I/O contracts (preconditions, invariants, done criteria). |
| `PARALLEL_CONDUCTOR.md` | Multi-project concurrency, conductor ledger, session handoff. |
| `PROJECT_BOOTSTRAP.md` | Starting a new project; directory template. |
| `GROUNDING_PROTOCOL.md` | No-hallucination rules including Rule 7a external verification. |
| `SAFEGUARD_LAYER.md` | Post-review integrity: eight checks including contradictions, drift, inter-sentential logical connectives (Check 7), and reader-experience / prose architecture (Check 8, convergence-gating at T3 per `TIER_PROTOCOL.md §3.3.3`). |
| `DETERMINISTIC_CHECKS.md` | Mechanical grep/count rules. |
| `DRIFT_CHECK.md` | MASTER/component drift gate; Reflector Phase 2.6. |
| `REFLEXIVITY_CHECK.md` | Authorship substitution-vs-augmentation; Reflector Phase 2.7. |
| `EXTERNAL_VERIFIERS.md` | Verifier classes for submission-bound citation checks. |
| `STYLE_COMMITMENTS.md` | Which named style commitments (C-1…C-4) are in force. |
| `SUCCESS_METRICS.md` | Six-dimension quality dashboard; submission-readiness criteria. |
| `TOKEN_BUDGET_PROTOCOL.md` | Long-manuscript context management. |
| `MASTER_research_and_paper_guidelines.md` | Consolidated content reference (Parts A–J). |

Everything else in the package is either a content-source file (Baird, Bacon, Sexton, Suchman), an agent prompt (`agents/`), a skill (`skills/`), an example walkthrough (`examples/`), or a log (`DRIFT_LOG.md`).

---

## 14. Final note

The package is not a tool. It is a discipline that a tool can enforce. Running it well means treating the phase spine, the agent separation, the integrity gates, and the cross-round memory as non-negotiable — not because the rules are sacred but because the failure modes they prevent are expensive and recurrent. The first three rounds of disciplined use will feel slower than an unstructured back-and-forth. By the sixth round, the disciplined mode is faster, because the failures that would have surfaced at submission have been caught at the exit gates.

When in doubt, read `QUICKSTART.md`.

---

*Created 2026-04-13 at user direction, paired with `QUICKSTART.md`. Loses to every component file on rule conflicts per `CLAUDE.md §4`.*
