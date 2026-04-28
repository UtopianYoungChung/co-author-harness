# ROUTING_SPINE — Phase-Based Intent Dispatch

**Purpose.** This file is the *intent-to-phase-to-agent* dispatch table for the Research and Academic Paper Writing Package. It adapts the gstack workflow spine (**Think → Plan → Build → Review → Test → Ship → Reflect**) to the academic research lifecycle (M1–M5) and the four-agent architecture (Planner / Evaluator / Generator / Reflector). It exists because the package, prior to this file, carried its routing logic implicitly across three documents (`CLAUDE.md` §1, `AGENT_ORCHESTRATION.md` §§3 and 10, `REVIEW_ORCHESTRATION.md` classification table). Implicit routing invites drift. An explicit spine makes the *intentionality* of each user utterance operationalizable: every request lands on exactly one phase, and every phase has a declared agent owner, entry artifact, exit artifact, and downstream phase.

**Relationship to adjacent files.** The spine does not replace `AGENT_ORCHESTRATION.md` — it sits one level above it. Orchestration defines *how agents cooperate within a phase*; the spine defines *which phase the request belongs to and what feeds what*. Where the two appear to conflict, orchestration wins on agent mechanics, spine wins on phase boundaries. The MASTER remains authoritative on content rules.

**Design pedigree.** The seven-phase lexicon is borrowed from Garry Tan's `gstack` (MIT-licensed, https://github.com/garrytan/gstack). The choice is deliberate: `gstack` demonstrates that a *named, ordered, non-overlapping* phase sequence with per-phase skill ownership produces fewer handoff gaps than a bag of skills invoked ad hoc. The adaptation here preserves that property while replacing software-engineering artifacts (code, PRs, deploys) with academic artifacts (memos, outlines, manuscripts, sign-offs).

---

## 1. The seven phases, mapped

| # | Phase | gstack analogue | Academic analogue | Lifecycle milestone | Primary agent | Entry artifact | Exit artifact |
|---|-------|-----------------|-------------------|---------------------|---------------|----------------|---------------|
| 1 | **Think** | `/office-hours` — reframe the problem before coding | Problem interrogation: identify phenomenon, tension, terms, candidate questions | **M1** Project Memo | Planner (classify) → Generator (draft memo) | User utterance + prior project state | `research_notes/project_memo.md` |
| 2 | **Plan** | `/plan-*-review` — lock architecture and direction | Literature scaffold + structural skeleton: annotated references, outline, argument arc | **M2–M3** Annotated References + Outline | Planner → Generator → Evaluator | `project_memo.md` | `annotated_references.md`, `manuscript/outline.md`, `reviews/classification.md`, `reviews/revision_plan.md` |
| 3 | **Build** | `/design-*` — generate the thing | Draft authoring: first pass prose against the outline | **M4** Paper Draft (initial) | Generator | `outline.md` + `revision_plan.md` | `manuscript/main.md` (first complete pass) |
| 4 | **Review** | `/review`, `/investigate` — read the code, find defects | Seven-step findings pipeline (Steps 1–7 of `REVIEW_ORCHESTRATION.md`) | **M4** standard depth | Evaluator | `manuscript/main.md` | `reviews/step_findings/*.md`, `reviews/consolidated_findings_report.md` |
| 5 | **Test** | `/qa`, `/benchmark` — mechanical and regression testing | Deterministic checks + Safeguard Layer + Drift/Reflexivity checks + External Verifiers | **M4** re-check / **M5** pre-ship | Evaluator (test mode) | `consolidated_findings_report.md` + Generator's fixes | `reviews/step_0a_deterministic.md`, `reviews/safeguard_layer_results.md`, `reviews/drift_check.md`, `reviews/reflexivity_check.md` |
| 6 | **Ship** | `/ship`, `/land-and-deploy` — merge, deploy, monitor | G.4 sign-off + submission-bound depth + venue-ready artifact | **M5** Final Paper | Evaluator (G.4) | All green from Test phase | `reviews/G4_signoff.md` + submission-ready manuscript |
| 7 | **Reflect** | `/retro`, `/document-release` — extract lessons, update docs | Lessons-learned, memory update, skill proposal, package improvement | After every round | Reflector | Full round evidence | `reviews/reflection_report.md`, `research_notes/lessons_learned.md`, optional `skills/*.md` |

**Critical property.** Phases are *sequential within a round* and *cyclical across rounds*. A round is the atomic unit of forward motion; Review → Test → Ship may iterate (Review → Test → Generator-fix → Review → …) until Test is clean, then Ship runs exactly once per submission boundary, then Reflect closes the round.

---

## 2. Intent classification — the dispatch table

The Planner (or the parent session acting as Planner) classifies every user utterance into exactly one phase. Ambiguous utterances are resolved by asking the user; they are **not** silently assigned.

| User utterance pattern | Phase | First action |
|---|---|---|
| "Start a new project on X," "bootstrap Y," "I want to study Z" | **Think (M1)** | Read `PROJECT_BOOTSTRAP.md`; dispatch Planner to seed project structure, then Generator for memo draft |
| "I have an idea but haven't written anything yet" | **Think (M1)** | Same as above |
| "What should I read?", "help me find sources," "build the bibliography" | **Plan (M2)** | Dispatch Planner for literature strategy, then Generator for annotated references |
| "Outline the paper," "what's the structure?", "organize my argument" | **Plan (M3)** | Dispatch Planner + Generator for outline; Evaluator reviews skeleton |
| "Write §X," "draft the introduction," "co-author this section" | **Build (M4)** | Dispatch Generator with revision_plan pointing at the target section |
| "Review this," "critique my draft," "what's wrong with §4?" | **Review (M4)** | Dispatch Evaluator through Steps 1–7 of `REVIEW_ORCHESTRATION.md` |
| "Run the checks," "deterministic pass," "run `/quick-deterministic`" | **Test** | Evaluator runs `DETERMINISTIC_CHECKS.md` only |
| "Safeguard layer," "check for regressions," "verify nothing drifted" | **Test** | Evaluator runs `SAFEGUARD_LAYER.md` |
| "Check citations," "verify references," "do the external verifier pass" | **Test** | Evaluator runs `EXTERNAL_VERIFIERS.md` against `GROUNDING_PROTOCOL.md` Rule 7a |
| "Is it ready?", "can I submit?", "do the G.4 sign-off" | **Ship (M5)** | Evaluator runs G.4 protocol at submission-bound depth; only runs if Test is CLEAN |
| "What did we learn?", "retro this round," "update memory" | **Reflect** | Dispatch Reflector |
| "Full loop," "comprehensive review," "do everything" | **Review → Test → (Ship if M5) → Reflect** | Planner orchestrates the full sequence with user checkpoints |

**Routing ambiguity resolution.** If the utterance could belong to two phases (e.g., "check my draft" — Review or Test?), the Planner presents a two-option prompt to the user. The default, when the user is silent or impatient, is the earlier phase (Review before Test, Think before Plan) because earlier phases surface upstream problems whose fix makes the later phase moot.

---

## 3. Phase gates — what must be true to exit each phase

A gstack-style spine is only useful if each phase has a *gate*: a declarative predicate that must evaluate to TRUE before the round advances. Without gates, phase names are cosmetic.

**Primary indicator.** Inspired by the autoresearch principle of *one metric per experiment* (Karpathy, 2025), each phase declares a single **primary indicator** — the one number or predicate the agent checks *first*. If the primary indicator fails, the full gate will also fail; checking it first avoids wasted effort on compound predicates. The remaining gate conditions are still mandatory, but the primary indicator is the fast-path check.

| Phase | Primary indicator (check first) | Exit gate (must all be TRUE) | Who certifies |
|---|---|---|---|
| Think (M1) | **Tension identified?** (boolean — at least one literature clash or contested definition is named concretely) | Phenomenon defined concretely; at least one tension identified; candidate q-items (q-α, q-β, q-γ) listed; snowball strategy declared | Evaluator (M1 criteria, `AGENT_ORCHESTRATION.md` §10.2) |
| Plan (M2) | **Track coverage balanced?** (boolean — no snowball track has zero sources) | Every source annotated with its contribution-to-tension; tracks assigned; coverage balanced | Evaluator (M2 criteria) |
| Plan (M3) | **SIS ≥ 3 on skeleton?** (Structural Integrity Score from `SUCCESS_METRICS.md` §3, applied to the outline) | Argument skeleton identifiable from outline alone; tension threaded intro-through-conclusion; framework critique slot present | Evaluator (M3 criteria) |
| Build (M4 initial) | **Zero TODO/TKTK/[?] markers?** (deterministic grep — pass/fail) | Every outline node has ≥1 paragraph of prose; no `TODO` / `TKTK` / `[?]` markers in final state; revision_log opened | Generator self-check |
| Review | **WFC computed?** (Weighted Finding Count from `SUCCESS_METRICS.md` §2 has been calculated and all findings dispositioned) | All seven step-findings files written; consolidated report emitted; severity counts tallied; no finding left without a proposed fix or explicit "accept as-is" | Evaluator |
| Test | **DCS = 100%?** (Deterministic Check Score — all nine categories within threshold) | `DETERMINISTIC_CHECKS.md` CLEAN; `SAFEGUARD_LAYER.md` CLEAN; `DRIFT_CHECK.md` CLEAN; `REFLEXIVITY_CHECK.md` resolved; (at submission-bound depth) `EXTERNAL_VERIFIERS.md` Rule 7a satisfied | Evaluator (test mode) |
| Ship (M5) | **G.4 sign-off written?** (file exists and is countersigned) | Test gate passed; G.4 sign-off written and countersigned by user; venue-specific formatting verified; DO_NOT_DISTURB frozen rules unchanged | Evaluator (G.4) + user |
| Reflect | **Reflection report written?** (file exists with all mandatory sections) | Reflection report written; lessons_learned appended; any proposed skills presented to user; directives (if any) proposed to `research_notes/directives.md` | Reflector |

**Fast-path protocol.** Before evaluating the full exit gate, the certifying agent checks the primary indicator. If it returns FALSE, the agent immediately reports the failure and proposes a targeted fix — it does not evaluate the remaining conditions. This saves time and focuses attention on the most likely blocker. If the primary indicator returns TRUE, the agent proceeds to the full gate evaluation.

**Gate failure handling.** If a gate fails, the round does not advance. The Planner records the failure in `reviews/revision_plan.md` as an open action and re-dispatches the phase owner. Repeated gate failures (> 2 on the same phase) trigger a Reflector consultation.

---

## 4. Skill-to-phase ownership

The existing seed skills and the `SKILL_REGISTRY.md` entries are retro-assigned to phases for dispatch clarity. New skills proposed by the Reflector should declare their phase in frontmatter.

| Skill | Phase | Invokable shortcut for |
|-------|-------|------------------------|
| `quick-deterministic` | Test | Running `DETERMINISTIC_CHECKS.md` without a full Review |
| `check-contradictions` | Review | SAFEGUARD_LAYER Check 4 in isolation |
| `check-abstract-body` | Review | Abstract-vs-body promise audit |
| `suchman-register-audit` | Review | C-1 (Suchman commitment) register consistency |
| (future) `/bootstrap-project` | Think | One-shot M1 seeding |
| (future) `/build-references` | Plan | M2 annotated reference generation |
| (future) `/outline-argument` | Plan | M3 outline construction |
| (future) `/g4-signoff` | Ship | Submission-bound G.4 protocol |
| (future) `/round-retro` | Reflect | Reflector's full post-round pass |

Skills without a phase tag should be treated as Review-phase utilities by default and retagged at the next Reflector round.

---

## 5. Trade-offs and known limits

A PhD-level reader should note three architectural trade-offs encoded in this spine.

*The first is **phase rigidity versus emergent work**.* Academic writing is not strictly linear — a Review finding can force a return to Plan (restructure the outline) or even Think (the tension was miscast). The spine handles this via the "phase re-entry" rule: any phase can be re-opened at any time, but re-opening invalidates downstream exit gates, forcing re-certification. This preserves the gate discipline without pretending the process is waterfall.

*The second is **agent autonomy versus system predictability**.* Each agent is an autonomous actor with its own protocols; but an explicit spine constrains their dispatch surface. The chosen operating point — Planner as sole dispatcher, other agents as phase-scoped executors — sacrifices some generative serendipity (a Generator "going off script" with a better idea) for predictability (the user knows which artifact will appear next). The Reflector is the pressure-release valve: a Generator's off-script insight can be captured as a reflection-report note and routed into the next Plan phase.

*The third is **cross-round memory versus phase purity**.* The spine is round-scoped; lessons learned live in `research_notes/lessons_learned.md` and bleed across rounds by design. This means a nominally-new Think phase is always conditioned by prior Reflect outputs — which is the point, but it also means a truly fresh problem framing may require an explicit memory-suspension directive from the user.

---

## 6. Operationalization — how the Planner uses this file

On every user utterance, the Planner:

1. Reads this file's §2 dispatch table and assigns the utterance to a phase. If ambiguous, asks the user with two labeled options (earlier phase as default).
2. Confirms the phase's entry artifact exists. If it does not, the Planner routes *backward* to the phase that produces it and informs the user of the detour.
3. Dispatches the phase's primary agent with a prompt that includes (a) the phase name, (b) the exit gate predicate, (c) the artifact paths, (d) the relevant package files from `AGENT_ORCHESTRATION.md` and `REVIEW_ORCHESTRATION.md`.
4. On agent completion, runs the exit gate. If TRUE, advances; if FALSE, re-dispatches or escalates.
5. At every `► PRESENTS TO USER ◄` checkpoint (see `AGENT_ORCHESTRATION.md` §3), the Planner names the current phase and the next phase so the user can redirect.

This procedure is mechanical. Its purpose is not to remove the Planner's judgment but to ensure that judgment is exercised *at the right moment* (phase assignment, gate evaluation, user checkpoint) rather than dispersed across every small decision.

---

## 7. What this file is NOT

- Not a replacement for `AGENT_ORCHESTRATION.md`. It sits above it.
- Not a rule source. The rules live in the component files; the spine only routes to them.
- Not a guarantee of quality. Phase gates certify *completion*, not *excellence*; the latter remains the Reflector's charge and the user's final call.

---

*Created 2026-04-13. Authored under user directive to adapt the gstack Think→Plan→Build→Review→Test→Ship→Reflect spine to the academic-writing package. Pairs with `PARALLEL_CONDUCTOR.md` (parallel-session orchestration) and `AGENT_CONTRACTS.md` (per-agent I/O contracts). Updated 2026-04-13: §3 extended with primary indicators per phase (autoresearch-inspired fast-path protocol — one metric checked first before evaluating compound exit gates).*
