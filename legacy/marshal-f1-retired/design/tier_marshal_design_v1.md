---
title: "Tier Marshal — Design Specification v1"
status: "Proposal (Phase F candidate)"
created: 2026-04-19
author: Joseph Chung (with Claude Opus 4.7)
related:
  - references/TIER_PROTOCOL.md
  - references/AGENT_ORCHESTRATION.md §§8.2 / 8.2a / 8.2b
  - references/PARALLEL_CONDUCTOR.md
  - references/SAFEGUARD_LAYER.md §Check 5
  - references/tier_closeout_schema.md
  - agents/planner.md §§Phase 0 / 2.5 / 5.5
disambiguation: |
  The agent proposed here is named Tier Marshal. Conductor is already the
  name of the concurrency-ledger protocol (PARALLEL_CONDUCTOR.md); the
  Orchestration vocabulary is owned by AGENT_ORCHESTRATION.md and
  REVIEW_ORCHESTRATION.md. Marshal is the enforcement role — the agent
  that grants or refuses a round — and is the fifth agent in the system.
---

# Tier Marshal — Design Specification v1

## Abstract

This specification proposes a fifth agent — the **Tier Marshal** — positioned above the Planner in the research-writing harness. The Marshal's single responsibility is to make the Incremental Tier Protocol's execution *observable on disk* by refusing to open or close a round unless the artefacts that prove the tier ladder operated are present, well-formed, and internally consistent. The proposal responds to the evaluator finding of 2026-04-19 that the v0.5.4 package has shipped a protocol the runtime has never executed: across both active projects, zero tier-protocol artefacts have been written, and the most recent round (INF3006Y Round 9) closed in structural violation of TIER\_PROTOCOL §11.9. The Marshal is designed so that the same round cannot close again without either producing the required artefacts or logging an explicit, user-signed override. The contribution is not a new tier, a new gate, or a new rule; it is an *enforcement layer* that turns previously advisory protocol text into a hard-gating precondition on dispatch.

---

## 1. Problem Statement

The package, as of v0.5.4, specifies a six-rung tier ladder (T0·T1·T2·T3·T3R·T4) governed by three compositional channels: the Planner-exclusive `reviews/escalation_log.md` (the spine), the Planner-exclusive session-spanning `reviews/tier_decisions_log.md` (Phase 5.5 elections plus the `ascent_observed` ratchet), and the Generator self-T1 verdict block embedded in `manuscript/revision_log.md` (the intra-T1 Confirmation-Mode shortcut). Each of the four existing agents has a contract that assumes these channels are written. The Reflector's Phase 2b and Phase 2c audit paths assume non-empty decision logs. SAFEGUARD Check 5 assumes every T1-and-above round emits a `tier_closeout_<round>_<date>.md`.

The evaluator finding of 2026-04-19 established that none of this has occurred. Across INF3006Y\_AgencyDelegation and INF3001H\_Research, the count of `state_probe_*.md`, `_rule_digest_*.json`, `escalation_log.md`, `tier_decisions_log.md`, `tier_closeout_*.md`, `patch_report_*.md`, `local_findings_*.md`, and `round_program.md` is exactly zero. Both projects' `classification.md` still carries the retired `review_depth: standard` field without a `tier:` field — precisely the condition §1 of `TIER_PROTOCOL.md` specifies must trigger re-classification. One orphan artefact (`lightening_pass_2026-04-18_evaluator.md`) names no tier, no skill, and no documented artefact type.

Two claims follow. The first is architectural: the contract text is internally consistent, but consistency of text is not evidence of runtime behaviour. The second is empirical: the most informative single round (INF3006Y Round 9) closed with T3 artefacts (`step_0a_deterministic_2026-04-19.md`, `consolidated_findings_report_2026-04-19.md`) but emitted no `state_probe`, no `tier_closeout`, no row in `escalation_log.md` — the Planner that ran the round skipped Phase 0 and Phase 5.5 without visible consequence. The package described a runtime that, at the time of the finding, had never run.

The question this specification answers is narrower than "how should the protocol be redesigned?" — the protocol is not at issue. The question is: *what mechanism would make the same round refuse to close the next time it is attempted?* The answer proposed below is a dedicated enforcement agent that executes deterministic preconditions before any Planner action and deterministic postconditions after any Planner close-out, and whose refusal to pass is hard-gating under the package's norm-compliance model.

## 2. Theoretical Framing

Two methodological frames shape the design.

The first is **Agent-Oriented Requirements Engineering (AORE)**. Treating each component as an autonomous agent bounded by an explicit protocol — rather than by implicit convention — is the move that `AGENT_CONTRACTS.md` already makes for Planner, Evaluator, Generator, and Reflector. The four contracts declare preconditions, inputs, outputs, invariants, and done criteria. What AORE exposes by absence is that there is no agent in the current system whose contract is *the enforcement of other agents' contracts*. SAFEGUARD Check 5 is a check, not an agent; the Reflector audits after the fact but does not prevent. The Tier Marshal is the AORE complement — an agent whose invariant is that every other agent's pre- and post-conditions have been externally witnessed.

The second is **Goal-Oriented Requirements Engineering (GORE)** in the i\* tradition. The Marshal's intentionality is captured by one hard-goal and two softgoals. The hard-goal is *"every tier-above-T0 round terminates with a schema-valid `tier_closeout_<round>_<date>.md`."* The first softgoal is *"every tier transition is auditable"* — which the Planner's escalation log partially satisfies and which the Marshal strengthens by refusing to pass a round whose claimed transitions are not logged. The second is *"no ad-hoc artefact enters the review tree"* — a direct response to the orphan-artefact finding, and a softgoal because total suppression is unrealistic but per-round inventory is tractable.

Three domain-specific commitments, lifted from the package's existing register, frame the design further. Usability heuristics apply to the agent architecture itself: a fifth agent adds cognitive load for the user, and the design must justify that cost against the defect surface the evaluator documented. Cognitive-load analysis suggests the Marshal should be as legible as a pre-commit hook — a single `STATUS: PASS | WARN | BLOCK` line at the top of each Marshal artefact, nothing the user has to parse unless it is `BLOCK`. Accessibility, narrowly construed here as *operator accessibility*, suggests that the Marshal's two artefact types (preflight, postflight) should be human-readable markdown with a machine-readable JSON sidecar so both the Reflector and a future headless CI can consume them.

## 3. Intentionality — The Core Research Problem

> *Make the specification runtime-observable by refusing to let a round open or close unless the artefacts that prove the tier ladder operated are present on disk, schema-valid, and internally consistent.*

This sentence is the Marshal's entire intentionality. It is deliberately narrower than "ensure the protocol is correct" (a rule-writing job, owned by the existing package authors) and narrower than "audit after the fact" (a Reflector job). The Marshal's contribution is *temporal*: it sits at the two moments — before Planner Phase 0 and after Planner Phase 5.5 — where protocol violations have the shortest blast radius if caught, and the widest if missed.

The design commits to three trade-offs up front. *First, enforcement over recommendation*: the Marshal issues a verdict, not a suggestion. `BLOCK` stops the round. *Second, mechanism over judgment*: the Marshal's checks are deterministic and do not read the manuscript. Every check is a question a shell script could answer in isolation. Judgment stays with the four existing agents. *Third, norm-compliance over filesystem locking*: consistent with `PARALLEL_CONDUCTOR.md §7`, the Marshal does not take file-system locks; it writes a verdict artefact and relies on the Planner's contract to honour it. This is the same trust model the rest of the package uses and keeps the Marshal auditable by the Reflector just like any other agent.

## 4. Strategic Dependency Model (i\* SD, narrated)

The five-agent socio-technical system, after the Marshal's introduction, carries six load-bearing dependencies.

The User *depends on* the Tier Marshal for the softgoal **"runtime matches specification,"** operationalised as the preflight and postflight artefacts being emitted and readable at every round. This dependency replaces the weaker dependency the User currently has on the Planner to self-enforce Phase 0 and Phase 5.5.

The Tier Marshal *depends on* the Planner for the resource **"classification, escalation\_log, tier\_decisions\_log, tier\_closeout\_<round>\_<date>.md"** — the four Planner-exclusive artefacts the Marshal reads. The Marshal cannot complete its postflight check if these are absent or malformed; absence is itself the finding.

The Tier Marshal *depends on* the Generator for the resource **"manuscript/revision\_log.md head entry with optional self-T1 verdict block"**. This is the one Generator-written surface the Marshal reads. The dependency is optional at T0, read-only at T1 and above; the Marshal never writes to `manuscript/revision_log.md`.

The Planner *depends on* the Tier Marshal for the task **"PASS verdict before Phase 0"** and for the task **"PASS verdict after Phase 5.5"**. In the existing package this dependency does not exist; the Planner proceeds on its own authority. The proposal makes the dependency explicit and enforceable via the norm-compliance model — the Planner's contract is amended to read the Marshal's verdict before dispatch.

The Reflector *depends on* the Tier Marshal for the resource **"compliance\_audit evidence"** — the postflight JSON sidecar gives Phase 2c a pre-parsed drift and orphan-artefact tally without re-walking the `reviews/` folder. This is a strict performance dependency; the Reflector can still reconstruct the evidence from the Planner's artefacts alone, but the Marshal's sidecar is cheaper and less error-prone.

The Tier Marshal *depends on* the User for the softgoal **"override authority preserved"** — the design includes a `[MARSHAL-OVERRIDE-<reason>]` tag that only the user can sign into `round_program.md`, turning a `BLOCK` into a `WARN` for one round. This dependency is the ethical load-bearing hinge: the Marshal is an enforcement agent, and the design must preserve an escape hatch that is explicit, logged, and audited.

## 5. Strategic Rationale Model (i\* SR, narrated)

Inside the Tier Marshal, the hard-goal *"every T≥T1 round terminates with a schema-valid tier\_closeout"* decomposes into two tasks. The first is **Preflight** — executed before the Planner reads any project state, answering the question "may this round open at the requested tier?" The second is **Postflight** — executed after the Planner writes the Phase 5.5 artefacts, answering the question "did the round emit the artefacts the tier required?"

The two softgoals decompose differently. *Auditability* is satisfied by three beliefs: (a) every tier transition in `escalation_log.md` has a matching Planner-authored row; (b) every Phase 5.5 election has a matching `tier_decisions_log.md` row, and its `ascent_observed` delta is consistent with the stated choice; (c) the `tier_closeout` artefact's `tier_entered_via` provenance is reconstructible from the escalation log's terminal entry. The Marshal verifies each belief independently. *Orphan suppression* is satisfied by a single task: inventory the `reviews/` folder at postflight and match every `*_YYYY-MM-DD.md` file against the tier's registered emission set. Unmatched files surface as `[ORPHAN-ARTEFACT]` advisories — never a `BLOCK`, always a `WARN`, because the Marshal cannot distinguish ad-hoc experimentation from protocol drift by filename alone, but the Reflector can.

The contribution arc of the SR model is the **sandwich pattern**: preflight and postflight are symmetric — same file layout, same verdict grammar, same JSON sidecar schema — but asymmetric in responsibility. Preflight protects the round from opening in an invalid state; postflight protects the specification from accumulating silently-skipped rounds.

## 6. Agent Contract Summary

The full contract in `AGENT_CONTRACTS.md` style is in the companion file `TIER_MARSHAL_CONTRACT.md` (the §8.3 addendum to `AGENT_ORCHESTRATION.md`). The summary:

- *Role metaphor.* Pre-commit hook and post-commit auditor, in the shape of an agent. Does not write prose. Does not classify. Does not dispatch. Writes only its own two artefact types.
- *Reads.* `reviews/classification.md`, `reviews/escalation_log.md`, `reviews/tier_decisions_log.md`, `reviews/tier_closeout_*.md`, `reviews/round_program.md` if present, `manuscript/revision_log.md` (head entry only), `reviews/_rule_digest_<plugin-version>.json` if present, `.claude-plugin/plugin.json`.
- *Writes.* `reviews/marshal_preflight_<round>_<date>.md` (exclusive) and its `.json` sidecar; `reviews/marshal_postflight_<round>_<date>.md` (exclusive) and its `.json` sidecar. No other file is touched.
- *Invariants.* **I-Marshal-1** — never writes to `manuscript/*`. **I-Marshal-2** — never writes to any Planner-exclusive artefact; reads only. **I-Marshal-3** — never dispatches another agent. **I-Marshal-4** — every preflight/postflight report's top line is one of `STATUS: PASS`, `STATUS: WARN`, `STATUS: BLOCK`, with no fourth value. **I-Marshal-5** — no check is judgment-based; every check is expressible as a deterministic predicate over file contents.
- *Done criteria.* Preflight: a written artefact whose `STATUS:` line is set, whose per-check rows are populated, and whose JSON sidecar validates. Postflight: the same, plus the orphan-artefact inventory row is populated.

## 7. Preflight / Postflight State Machine

The two Marshal actions bracket the existing four-agent loop:

```
USER REQUEST
   ↓
┌─────────────────────────────────────────┐
│ ⓪ TIER MARSHAL — PREFLIGHT              │   ← new
│   reads: classification, digest,        │
│   revision_log head, tier_decisions_log │
│   writes: marshal_preflight_<round>_    │
│           <date>.md + .json             │
│   emits: STATUS: PASS | WARN | BLOCK    │
└──────────┬──────────────────────────────┘
           │ PASS or WARN
           ▼
┌─────────────────────────────────────────┐
│ ① PLANNER  (Phase 0 → 5.5, unchanged)   │
└──────────┬──────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│ ⓪ TIER MARSHAL — POSTFLIGHT             │   ← new
│   reads: tier_closeout, escalation_log, │
│   tier_decisions_log, scoped artifact,  │
│   reviews/ folder inventory             │
│   writes: marshal_postflight_<round>_   │
│           <date>.md + .json             │
│   emits: STATUS: PASS | WARN | BLOCK    │
└──────────┬──────────────────────────────┘
           │ PASS or WARN
           ▼
┌─────────────────────────────────────────┐
│ ④ REFLECTOR (reads sidecar)             │
└─────────────────────────────────────────┘
```

Two details matter. First, **BLOCK on preflight halts the round** — the Planner's amended contract forbids dispatch until the BLOCK is resolved or a `[MARSHAL-OVERRIDE-<reason>]` tag is signed into `round_program.md`. Second, **BLOCK on postflight does not un-write the round** — the Generator's edits and the Evaluator's findings remain on disk — but it does prevent the Reflector from running, because a Reflector reflection over a round the Marshal judged structurally invalid would embed that invalidity into `research_notes/lessons_learned.md`. The escape-hatch is the same override tag, and the Reflector's Phase 2c is amended to read the override advisories before computing drift.

## 8. Hard-Gate Protocol — Refusal Semantics

The verdict grammar is three-valued:

- **`STATUS: PASS`** — every check returned true. The Planner may proceed (preflight) or the Reflector may run (postflight). This is the expected case in steady state.
- **`STATUS: WARN`** — every blocking check returned true, but one or more advisory checks surfaced a concern. The round proceeds; the concern is recorded in the reflection surface. Orphan artefacts, `[DECLARED-COMPLETION-BELOW-TIER]` after the fact, and narrative-truncation advisories are `WARN`-class.
- **`STATUS: BLOCK`** — one or more blocking checks returned false. The round does not proceed. The Marshal artefact lists exactly which predicate failed and which file to fix. The Planner's amended contract explicitly forbids dispatch until the user either remediates the file or signs the override.

The **override tag** is `[MARSHAL-OVERRIDE-<reason-code>]`, where `<reason-code>` is drawn from a closed enum: `DIGEST-UNAVAILABLE`, `CLASSIFICATION-PENDING`, `USER-TIME-CRITICAL`, `EXPERIMENTAL-SKIP`. Any other value is itself a BLOCK condition on the next preflight, because unknown reason-codes would let the Marshal's enforcement drift into free-form justification — the failure mode the override was designed to prevent. The override is signed by the user into `reviews/round_program.md`; the Marshal reads it on the next preflight, downgrades the matching BLOCK to WARN for that round only, and records the override in its JSON sidecar so the Reflector Phase 2c can tally override frequency per reason-code.

## 9. Writer / Reader Exclusivity Matrix

| File | Planner | Evaluator | Generator | Reflector | **Tier Marshal** |
|---|---|---|---|---|---|
| `manuscript/main.md` | read | read | read + write | read | — |
| `manuscript/revision_log.md` | read | read | read + append | read | **read (head only)** |
| `reviews/classification.md` | read + write | read | read | read | **read** |
| `reviews/escalation_log.md` | read + write (exclusive) | read | — | read | **read** |
| `reviews/tier_decisions_log.md` | read + write (exclusive) | — | — | read | **read** |
| `reviews/tier_closeout_*.md` | read + write (exclusive) | read (Phase 5.5 narrative) | — | read | **read** |
| `reviews/round_program.md` | read + write | read | — | read | **read** |
| `reviews/state_probe_*.md` | write | read | — | read | **read** |
| `reviews/patch_report_*.md` | read | write | — | read | **read** |
| `reviews/local_findings_*.md` | write (header) | write (body) | — | read | **read** |
| `reviews/marshal_preflight_*.md` | read | — | — | read | **write (exclusive)** |
| `reviews/marshal_postflight_*.md` | read | — | — | read | **write (exclusive)** |

The critical invariant: the Marshal is a **pure reader** of every Planner-exclusive artefact. This preserves `TIER_PROTOCOL.md §4`'s single-writer invariant on the escalation log (the design choice that avoids three-way merges) and extends it to the tier-decisions log. The Marshal contributes no new write contention — it adds only two new files, both of which it owns exclusively.

## 10. Per-Tier Pre- and Post-Condition Tables

### 10.1 Preflight preconditions (blocking unless noted)

| Check ID | T0 | T1 | T2 | T3 | T3R | T4 |
|---|---|---|---|---|---|---|
| **P-1** classification.md exists | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **P-2** classification.md has `tier:` field (not `review_depth:`) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **P-3** classification.md `tier:` matches requested tier | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **P-4** `_rule_digest_<plugin-version>.json` present | — | ✓ | ✓ | — | — | — |
| **P-5** digest plugin-version matches `plugin.json` | — | ✓ | ✓ | — | — | — |
| **P-6** `manuscript/revision_log.md` readable | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| **P-7** tier-decisions ratchet readable (or legitimately absent) | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| **P-8** requested tier legal under ratchet (Down-legality check) | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| **P-9** T2 local-scope envelope computable | — | — | ✓ | — | — | — |
| **P-10** response\_letter.md present at T3R | — | — | — | — | ✓ | — |
| **P-11** Class-1 verifier reachable at T4 | — | — | — | — | — | ✓ |
| **P-12** No unresolved prior-round `STATUS: BLOCK` postflight | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **P-13** `round_program.md` override tags (if present) use legal enum | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

A `✓` is blocking. Advisory-only checks surface `WARN` and are written in italics in the artefact rendering but do not change the verdict line.

### 10.2 Postflight postconditions (blocking unless noted)

| Check ID | T0 | T1 | T2 | T3 | T3R | T4 |
|---|---|---|---|---|---|---|
| **Q-1** `state_probe_<date>.md` emitted | ✓ | — | — | — | — | — |
| **Q-2** `tier_closeout_<round>_<date>.md` emitted | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Q-3** `tier_closeout` passes `tier_closeout_schema.md` | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Q-4** `escalation_log.md` has row(s) for the round | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Q-5** `tier_decisions_log.md` has row for this round's Phase 5.5 | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Q-6** tier-scoped artefact present (patch\_report / local\_findings / consolidated / letter\_findings) | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Q-7** `tier_entered_via` in closeout consistent with escalation\_log terminal entry | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Q-8** `ascent_observed` in closeout consistent with decisions-log header update | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Q-9** No orphan artefacts in `reviews/` folder (advisory WARN) | — | ○ | ○ | ○ | ○ | ○ |
| **Q-10** G.4 sign-off emitted at T4 | — | — | — | — | — | ✓ |
| **Q-11** Manuscript diff absent at T0; non-empty at T1+ if any edit was made | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

`○` denotes an advisory-only check (returns WARN, not BLOCK).

## 11. Failure Modes and Trade-offs

The Marshal is a deliberately narrow agent. Its failure modes deserve naming.

*The first is **false blocking on schema edge cases**.* A freshly classified project with no prior rounds has no `tier_decisions_log.md`; Q-5 would block every first round. The Marshal's first-round exemption — "if this is the session's first Phase-5.5 election, Q-5 passes iff the Planner creates the log header in this round" — addresses this. The cost is a softer check; the benefit is that legitimate first rounds are not rejected.

*The second is **override drift**.* Any escape hatch creates a pressure gradient: if `BLOCK` is frequent enough that the user learns to override by reflex, the Marshal becomes surface decoration. The closed enum of four reason-codes is the mitigation — and the Reflector's Phase 2c is amended to surface an override-frequency advisory when any single reason-code appears in more than three consecutive rounds. Override frequency is the drift signal the Reflector tunes against.

*The third is **script brittleness versus runtime liveness**.* The Marshal is specified as a deterministic predicate over file contents. The scripts ship in `scripts/marshal_preflight.py` and `scripts/marshal_postflight.py`. If the scripts fall behind the schema (e.g., `tier_closeout_schema.md` adds a field at v0.5.5), a stale Marshal could produce a false PASS. The mitigation is the same pattern used for `verify_rule_digest.py`: version-pinning at the `plugin.json` file plus a release-gate re-run. This is an explicit acceptance of the brittleness in exchange for auditability.

*The fourth is **concurrency with PARALLEL\_CONDUCTOR.md**.* Under L2 (intra-project cross-phase parallel operation), the Reflector on Round N runs concurrently with the Planner on Round N+1. The Marshal's postflight for Round N must complete before Round N+1's preflight runs, because Round N+1's preflight check P-12 (no unresolved prior `BLOCK`) depends on Round N's postflight verdict being written. The design choice: the Marshal postflight is **L0** (serial) within a project and blocks Round N+1 preflight until it writes. This narrows L2 slightly but preserves the Marshal's enforcement guarantee.

*The fifth and most important is what the Marshal **cannot** detect.* The Marshal is a *structural* auditor: it cannot verify that the Evaluator's narrative in the `tier_closeout` actually corresponds to the round's deltas, cannot detect a Generator self-T1 verdict that is dishonestly `CLEAN`, and cannot verify that a revision plan addresses the right findings. All three are judgment-level defects, owned by the Reflector. The Marshal's PASS is a structural PASS, not a semantic one — and the specification must name this limit plainly so it is not mistaken for correctness guarantees.

## 12. Relation to Existing Package Files

*To `TIER_PROTOCOL.md §11.9` (the three Phase-5.5 invariants).* The Marshal operationalises invariant 1 ("non-skippable at T1 and above") by refusing to pass postflight when `tier_closeout_<round>_<date>.md` is absent. Invariant 2 ("no auto-advance") is unchanged; the Marshal never elects on the user's behalf. Invariant 3 ("decisions log is append-only") gains a structural verifier: Marshal postflight check Q-8 compares `ascent_observed` in the closeout artefact against the tier-decisions log header update and blocks on inconsistency.

*To `SAFEGUARD_LAYER.md Check 5` (Edit Traceability).* The Marshal is to Check 5 as `DETERMINISTIC_CHECKS.md` is to the judgment-based review — a pre-judgment mechanical counterpart. Check 5 verifies that every proposed edit cites a rule; the Marshal verifies that every round emits the artefacts the tier commits to. Both are traceability checks; they apply at different scopes. The proposal does not weaken Check 5; it complements it.

*To `AGENT_ORCHESTRATION.md §§8.2 / 8.2a / 8.2b`.* The Marshal adds a §8.3 without modifying §§8.2–8.2b. The existing single-writer invariants on `escalation_log.md` and `tier_decisions_log.md` are preserved because the Marshal is read-only on both files.

*To `PARALLEL_CONDUCTOR.md`.* The files do not overlap in function. The Conductor is the multi-project concurrency ledger — a dashboard. The Marshal is the per-round protocol-compliance gate. In the single-user, L1 (cross-project parallel) default, the Conductor picks which project's round runs next, and the Marshal gates whether that round may open. The naming disambiguation in this document's frontmatter is normative.

*To `agents/planner.md`.* The Planner's Phase 0 and Phase 5.5 descriptions are amended in the companion §8.3 contract file to read "run after the Tier Marshal has issued a PASS (or WARN) verdict." No change to Phase 1–5 semantics. The Planner's writer/reader exclusivity on the two logs is unchanged.

*To `ROUTING_SPINE.md`.* The routing spine's phase dispatch is the authoritative map of which agent runs when in the pre-drafting milestones (M1–M3). The Marshal is added as a bracketing element around every phase dispatch at M4–M5. M1–M3 dispatch is outside the Marshal's scope in v1, and the §8.3 contract file states this explicitly.

## 13. Rollout Plan — Phase F

The proposal maps onto the package's existing phase vocabulary. A Phase F release would:

*Land in two sub-phases.* **Phase F.1 (v0.5.5)** ships the two scripts (`marshal_preflight.py`, `marshal_postflight.py`) in advisory-only mode — no BLOCK semantics, every predicate failure reported as WARN. This lets the Reflector collect two rounds of calibration evidence without changing runtime behaviour. **Phase F.2 (v0.5.6)** flips the BLOCK semantics on and adds the §8.3 contract to `AGENT_ORCHESTRATION.md` and the amended Phase-0/Phase-5.5 language to `agents/planner.md`. The split is designed to avoid the v0.4.18→v0.5.4 pattern the evaluator criticised — seven version bumps in a day shipping downstream phases before the upstream phases had field data.

*Calibrate against live runs.* The first fix recommended in the 2026-04-19 evaluator finding — re-classify INF3006Y to add a `tier:` field, build the rule digest at v0.5.4, dispatch a real Generator round with a self-T1 verdict block — is the calibration event for Phase F.1. The first preflight in the portfolio will BLOCK on P-2 (missing `tier:` field), which is the correct outcome. The second preflight after re-classification will PASS. This is the observable-runtime test the package has not yet passed.

*Ship an optional Reflector amendment.* The Reflector's Phase 2c at v0.5.4 computes three drift metrics (systematic-down-drift, premature-completion, ratchet-suppression). The Marshal's JSON sidecars let Phase 2c compute three additional metrics cheaply: override-tag frequency per reason-code, orphan-artefact rate per round, and preflight-BLOCK frequency per check-ID. These are logged but not acted on — Phase 2c remains advisory.

*Retire the orphan experiment.* The `lightening_pass_2026-04-18_evaluator.md` orphan is the observable instance of the failure mode the Marshal is designed to surface. Phase F.1 includes a one-time audit of both active projects' `reviews/` folders, flagging every file matching `*_YYYY-MM-DD*.md` that does not correspond to a documented artefact type. The audit is informational; the user decides whether to rename, formalise as a new artefact type, or delete each orphan.

*Document non-goals explicitly.* What Phase F does not do, by design: does not add a new tier, a new escalation gate, a new rule file, or a new skill. Does not modify any existing agent's prompt body beyond the Planner's Phase 0/5.5 bracketing amendment. Does not modify `tier_closeout_schema.md`. Does not change the digest contract. The Marshal is additive.

## 14. Contribution

The specification's contribution is a single architectural move: the separation of *protocol authorship* from *protocol enforcement*. In the current package, authorship and enforcement are conflated in the Planner — the same agent that decides what tier a round runs at is also responsible for emitting the artefacts that prove it ran at that tier. The evaluator finding of 2026-04-19 is the empirical signal that this conflation is load-bearing: when the Planner skips Phase 5.5, there is no second party in the system to observe the skip until the Reflector reads the empty decisions log three phases later. Separating the two roles — Planner dispatches, Marshal witnesses — is the cheapest available mechanism for making the specification runtime-observable, and it reuses every existing channel in the package without modifying any of them.

Whether the mechanism is *sufficient* is an empirical question the Phase F rollout is designed to answer. The specification does not claim sufficiency; it claims that sufficiency is now testable.

---

*End of specification v1. Companion files: `TIER_MARSHAL_CONTRACT.md` (the §8.3 agent contract), `scripts/marshal_preflight.py`, `scripts/marshal_postflight.py`.*
