# Tier Marshal Contract — AGENT_ORCHESTRATION §8.3 (Proposed)

**Status.** Proposal for Phase F.1 (v0.5.5) and Phase F.2 (v0.5.6). Freestanding file pending integration into `AGENT_ORCHESTRATION.md §8.3`; content is written in the style of §§8.2a and 8.2b so that integration is a straight paste without rewording. Paired with `research_notes/tier_marshal_design_v1.md`, which carries the prose design rationale. This file carries only the contract.

**Relationship to the four-agent system.** The Tier Marshal is the fifth agent. It brackets the existing four-agent loop at two points: immediately before the Planner's Phase 0 (preflight) and immediately after the Planner's Phase 5.5 (postflight). It never dispatches other agents, never writes to the manuscript, and never writes to any Planner-exclusive artefact. It writes exactly two file types, both of which it owns exclusively.

---

## 8.3 The Tier Marshal Agent

### 8.3.1 Why it exists

The Incremental Tier Protocol (see `TIER_PROTOCOL.md`) specifies a six-rung ladder, seven escalation gates, and three compositional channels (the escalation log, the tier-decisions log, and the Generator self-T1 verdict). Each channel depends on the Planner emitting the correct artefact at the correct phase. The 2026-04-19 evaluator finding established that the specification's artefacts were not emerging in practice: across two active projects, zero `state_probe_*.md`, zero `escalation_log.md`, zero `tier_decisions_log.md`, and zero `tier_closeout_*.md` had been written, and one round (INF3006Y Round 9) closed as a structural violation of `TIER_PROTOCOL.md §11.9` without any in-loop mechanism to surface the violation.

SAFEGUARD Check 5 (`SAFEGUARD_LAYER.md`) already declares that a round at T1 or above without a `tier_closeout_<round>_<date>.md` is a Check-5 violation, and the Reflector's Phase 2c declares the violation retrospectively. Neither surface is in-loop: both fire after the Planner has closed the round, accept it into `lessons_learned.md`, and moved on. The Tier Marshal is the in-loop counterpart — a pre-dispatch gate that refuses to let a round open in an invalid state and a post-close-out gate that refuses to let a round terminate without the artefacts the tier promised.

The Marshal is an **enforcement** agent, not an authorship agent. It adds no new rules, tiers, or gates. It verifies that the existing rules, tiers, and gates left their expected traces.

### 8.3.2 Who reads it

- The **Planner** reads `reviews/marshal_preflight_<round>_<date>.md` before Phase 0 and halts dispatch on `STATUS: BLOCK`.
- The **Planner** reads `reviews/marshal_postflight_<round>_<date>.md` after Phase 5.5 and halts Reflector dispatch on `STATUS: BLOCK`.
- The **Reflector** reads the `.json` sidecar of both artefacts during Phase 2c to compute Marshal-derived drift metrics (override-tag frequency, orphan-artefact rate, preflight-BLOCK frequency per check-ID).
- The **User** reads both artefacts when a `STATUS: BLOCK` surfaces; the artefact names the failed predicate and the remediation file.
- The Evaluator and the Generator do not read either artefact. The Marshal is invisible to them by design; the enforcement pressure lands on the Planner, and the other three agents see only the Planner's dispatch behaviour.

### 8.3.3 Who writes it

The Tier Marshal writes both files exclusively. Creation is strict: the preflight file is created by the Marshal on every round where the user's first utterance implies work at T1 or above; the postflight file is created by the Marshal after the Planner's Phase 5.5 has completed (or failed to complete). No other agent appends to or rewrites either file. The Marshal never writes to any other file in the `reviews/` tree.

A round at T0 emits only the preflight file; postflight is skipped at T0 because T0 emits no judgement artefact and has nothing to audit. A round where the preflight verdict is `BLOCK` still emits the preflight artefact (that is how the BLOCK is communicated); the postflight artefact is not written for a BLOCKed preflight.

### 8.3.4 Writer/Reader exclusivity matrix

Extension to `AGENT_ORCHESTRATION.md §4`:

| File / directory | Planner | Evaluator | Generator | Reflector | Tier Marshal |
|---|---|---|---|---|---|
| `reviews/marshal_preflight_*.md` | read | — | — | read | **read + write (exclusive)** |
| `reviews/marshal_preflight_*.json` | read | — | — | read | **read + write (exclusive)** |
| `reviews/marshal_postflight_*.md` | read | — | — | read | **read + write (exclusive)** |
| `reviews/marshal_postflight_*.json` | read | — | — | read | **read + write (exclusive)** |
| `reviews/escalation_log.md` | **read + write (exclusive)** | read | — | read | read |
| `reviews/tier_decisions_log.md` | **read + write (exclusive)** | — | — | read | read |
| `reviews/tier_closeout_*.md` | **read + write (exclusive)** | read (Phase 5.5 narrative) | — | read | read |
| `reviews/classification.md` | **read + write** | read | read | read | read |
| `reviews/round_program.md` | read + write | read | — | read | read |
| `manuscript/revision_log.md` | read | read | **read + append (exclusive append)** | read | read (head only) |

The Marshal is a **pure reader** of every Planner-exclusive artefact. The single-writer invariant established by §§8.2a and 8.2b on the escalation log and the tier-decisions log is preserved.

### 8.3.5 Lifecycle

**Preflight.** The Marshal runs at the start of every user request whose utterance implies work on a manuscript (review, edit, new section, re-check). It does not run on strictly informational queries ("what M-stage is this project at?"), which remain T0 and produce only the Planner's `state_probe_<date>.md`. On a T0 request the Marshal still runs a reduced preflight — checks P-1, P-12, and P-13 only — to catch the pathological cases (a stale BLOCK from the prior round, an illegal override-tag in the round program).

**Planner Phase 0 and Phases 1–5.5.** Unchanged in content. Amended only in their *opening sentence*: "Read `reviews/marshal_preflight_<round>_<date>.md` first. If `STATUS: BLOCK`, halt and surface the artefact to the user. If `STATUS: PASS` or `STATUS: WARN`, proceed as below." The Planner's existing contracts (§8.2, §8.2a, §8.2b) are otherwise untouched.

**Postflight.** The Marshal runs after the Planner's Phase 5.5 emits the `tier_closeout` artefact and the `tier_decisions_log` row, and before the Reflector is dispatched for the round-closing reflection. A `STATUS: BLOCK` postflight halts Reflector dispatch until the user remediates or signs an override. The Generator's edits and the Evaluator's findings for the round remain on disk — BLOCK does not unwind prior work — but the round is not considered closed for the purposes of `research_notes/lessons_learned.md` or `ascent_observed` updates.

**Cross-round archival.** Both the `*.md` and `*.json` Marshal artefacts are preserved across rounds under their round-qualified names. The Reflector's session-close audit aggregates them into the reflection report's new `§11 — marshal-trace` subsection.

### 8.3.6 Artefact signatures

**Preflight template.**

```markdown
---
round: 7
tier_requested: T3
date: 2026-04-19
plugin_version: 0.5.5
marshal_schema_version: 1
---

# Marshal Preflight — Round 7 (T3 requested)

STATUS: BLOCK

## Blocking checks

- P-2 — classification.md has `tier:` field: FAIL (file carries retired `review_depth: standard`)
  - Remediation: re-run /classify-manuscript and save the `tier:` field.
- P-4 — `_rule_digest_<plugin-version>.json` present: FAIL (no digest file in reviews/)
  - Remediation: run `python scripts/build_rule_digest.py --project-root <path>`.

## Advisory checks

- P-9 — T2 local-scope envelope computable: N/A (not T2)
- P-13 — round_program override-tags use legal enum: PASS (no override tags present)

## Override record

- Round program override-tags read: []
- Overrides applied this round: []
```

**Postflight template.**

```markdown
---
round: 7
tier_entered: T3
tier_entered_via: initial-dispatch
date: 2026-04-19
plugin_version: 0.5.5
marshal_schema_version: 1
---

# Marshal Postflight — Round 7 (T3, standard)

STATUS: PASS

## Blocking checks

- Q-2 — tier_closeout emitted: PASS (reviews/tier_closeout_07_2026-04-19.md)
- Q-3 — tier_closeout schema valid: PASS
- Q-4 — escalation_log has row for round: PASS (2 rows)
- Q-5 — tier_decisions_log has row for Phase 5.5: PASS
- Q-6 — tier-scoped artefact present: PASS (consolidated_findings_report_2026-04-19.md)
- Q-7 — tier_entered_via consistent with escalation_log terminal: PASS
- Q-8 — ascent_observed consistent with decisions-log header: PASS
- Q-11 — manuscript diff non-empty (edit round): PASS

## Advisory checks

- Q-9 — orphan artefacts in reviews/: WARN (1 file flagged)
  - `reviews/lightening_pass_2026-04-18_evaluator.md` — no registered artefact type matches.
  - Recommendation: formalize as a new artefact type in TIER_PROTOCOL.md, rename to match an existing type, or delete after review.

## Gate-firing digest (for Reflector Phase 2b)

- EG-4 fired at 2026-04-19T15:04:22 (T3 → T3, logged-but-non-escalating): Baumer/i* contradiction surface in §3.

## Override record

- Overrides applied this round: []
```

Both artefacts have a companion `.json` sidecar with the same content in structured form, keyed by check ID. The schema version is pinned at the top of the artefact; the loader script (`scripts/marshal_preflight.py` / `scripts/marshal_postflight.py`) refuses to emit an artefact whose schema version does not match the running plugin version.

### 8.3.7 Hard-gate refusal protocol

**Three verdicts.** The `STATUS:` line admits three values and no fourth.

- `STATUS: PASS` — every blocking check returned true; no advisory checks raised concerns.
- `STATUS: WARN` — every blocking check returned true; one or more advisory checks surfaced a concern. The round proceeds; the Reflector Phase 2c logs the warn.
- `STATUS: BLOCK` — one or more blocking checks returned false. The round does not proceed (preflight) or the Reflector does not run (postflight).

**Refusal semantics.** The Planner's amended Phase 0 and post-Phase-5.5 contracts read the Marshal artefact and halt on `STATUS: BLOCK`. Halting means: the Planner presents the Marshal artefact to the user, names the failed checks and their remediations, and does not advance until either (a) the user remediates the underlying files and the Marshal re-runs to produce a `STATUS: PASS` or (b) the user signs a legal override.

**Override vocabulary.** The user may sign a `[MARSHAL-OVERRIDE-<reason>]` tag into `reviews/round_program.md`. The reason-code is drawn from this closed enum:

- `[MARSHAL-OVERRIDE-DIGEST-UNAVAILABLE]` — P-4 or P-5 cannot pass because the rule digest has not been built for this plugin version. Legitimate in the first round after a plugin upgrade.
- `[MARSHAL-OVERRIDE-CLASSIFICATION-PENDING]` — P-2 cannot pass because classification is being re-written in-session. Legitimate in the first round after migrating from a v0.4.x `review_depth` record.
- `[MARSHAL-OVERRIDE-USER-TIME-CRITICAL]` — the user has declared a submission deadline and elects to run the round under structural advisories. Logged; audited by Phase 2c override-frequency check.
- `[MARSHAL-OVERRIDE-EXPERIMENTAL-SKIP]` — the round is deliberately outside the tier protocol (for example, a one-off ad-hoc pass). Logged as an orphan-artefact candidate in the following postflight.

Any override tag whose reason-code is not in this enum is itself a BLOCK condition on the next preflight, preventing override-drift via free-form justification. Override tags are scoped to a single round; they do not carry across rounds.

### 8.3.8 Interaction with Planner Phase 0 and Phase 5.5

**Phase 0.** The Planner's Phase 0 (T0 state-probe) still runs at the start of every session. The Marshal's preflight runs *before* Phase 0 — preflight is the cheapest available check and does not read the manuscript. If preflight is `PASS` or `WARN`, Phase 0 proceeds and emits `state_probe_<date>.md`. If preflight is `BLOCK`, Phase 0 does not run; the only artefact produced is the Marshal preflight.

**Phase 5.5.** The Planner's Phase 5.5 (tier close-out) is unchanged in semantics. It still emits `tier_closeout_<round>_<date>.md`, appends to `tier_decisions_log.md`, and presents the four-way election to the user. After the user's election is recorded, the Marshal postflight runs. If postflight is `PASS` or `WARN`, the Reflector is dispatched. If postflight is `BLOCK`, the Reflector is not dispatched; the round's lessons are held back from `research_notes/lessons_learned.md` until the user remediates or signs an override.

**Down-legality cross-check.** The Marshal preflight check P-8 reads `ascent_observed` from `tier_decisions_log.md` and confirms that the requested tier is either (a) reachable via the ratchet or (b) an Up election. This is a *second* witness of the check the Planner's Phase 2.5 already runs. The two witnesses exist because the specification's most subtle failure mode is ratchet-violation that the Planner silently permits; having both the authoring agent and the enforcing agent compute the same check independently is the price of the enforcement guarantee.

### 8.3.9 Interaction with SAFEGUARD Check 5

`SAFEGUARD_LAYER.md Check 5` (Edit Traceability) declares that a round at T1 or above that does not emit `tier_closeout_<round>_<date>.md` is a Check-5 structural violation. The Marshal operationalises this declaration at write time: postflight check Q-2 is a synonym for Check 5's structural clause, evaluated before the round closes rather than at the next Reflector audit. The two surfaces are complementary, not redundant — Check 5 also verifies edit traceability at the finding level, which the Marshal does not. The Marshal's Q-2 is a narrower, earlier counterpart that catches the structural half of Check 5 before the Reflector sees the round.

### 8.3.10 Interaction with Reflector Phase 2c

The Reflector's Phase 2c (tier-decision drift audit) at v0.5.4 computes three metrics over `tier_decisions_log.md`: systematic-down-drift, premature-completion, and ratchet-suppression. Phase F.1 adds three Marshal-derived metrics, each computed from the JSON sidecars:

- *Override-tag frequency per reason-code.* Counts each of the four reason-codes over a rolling three-round window. A single code appearing in more than three consecutive rounds surfaces a `[MARSHAL-OVERRIDE-DRIFT: <reason-code>]` advisory in §9 of the reflection report. The advisory is specific — "digest-unavailable has been invoked four rounds in a row" — and names the remediation (build the digest).
- *Orphan-artefact rate per round.* Counts `WARN`-class Q-9 firings. A rate above zero for two consecutive rounds surfaces `[ORPHAN-ARTEFACT-PATTERN]` in §9 with the filenames and recommends formalisation via a `TIER_PROTOCOL.md §2.x` addendum.
- *Preflight-BLOCK frequency per check-ID.* Counts `STATUS: BLOCK` verdicts grouped by which P-check failed. Useful for identifying systemic misconfiguration — a classification migration that has not caught up, a plugin-upgrade cadence that repeatedly outruns digest rebuilds.

All three metrics are advisory. Phase 2c does not modify any rule or tier; it reports and records.

### 8.3.11 Bootstrap procedure

On a project that has never run the Marshal, the first invocation proceeds as follows:

1. The Marshal checks for the presence of `reviews/marshal_preflight_*.md` with a date equal to or later than the last `reviews/revision_log.md` entry. Absence is not an error; it triggers first-run initialisation.
2. First-run initialisation runs a reduced preflight (checks P-1, P-2, P-12, P-13 only), emits the artefact, and writes a sidecar noting `first_run: true`.
3. Subsequent rounds run the full preflight set appropriate to the requested tier.
4. On the project's first Phase 5.5 election, Q-5 (tier-decisions log has row for Phase 5.5) is satisfied iff the Planner creates the log header in this round; the first-row check is exempt from the "pre-existing row" interpretation that applies from Round 2 onward.

The bootstrap exemption is narrow, one-round-only, and recorded in the preflight sidecar so the Reflector can distinguish legitimate first-round bootstraps from systemic Phase-5.5 skipping.

### 8.3.12 Concurrency interaction

Under `PARALLEL_CONDUCTOR.md` L1 (cross-project parallel), Marshal invocations are independent across projects — each project's `reviews/` tree is its own scope. Under L2 (intra-project cross-phase parallel), Marshal postflight for Round N must complete before Round N+1's Marshal preflight runs, because preflight check P-12 (no unresolved prior-round BLOCK) reads Round N's postflight verdict. The Marshal is **L0-serial within a project** by design; the cost is at most a single Marshal wall-clock (tens of seconds) in the Round N+1 open. Under L3 (experimental intra-phase parallel), the Marshal runs once per round, not once per parallel Evaluator; the postflight's Q-6 check accepts the union of parallel findings files as the scoped artefact set.

### 8.3.13 Non-goals (binding)

The Tier Marshal is additive and narrow. The following are out of scope for Phase F:

- No new tier.
- No new escalation gate.
- No modification to `TIER_PROTOCOL.md §§1–11`.
- No modification to `tier_closeout_schema.md`.
- No modification to the rule digest contract (`GROUNDING_PROTOCOL.md Rule 1`).
- No modification to any existing agent's prompt body, beyond the single bracketing amendment on `agents/planner.md`.
- No reading of `manuscript/main.md` (the Marshal reads `manuscript/revision_log.md` head only, for edit-nonemptiness check Q-11).
- No writing to `manuscript/*`, to any Planner-exclusive artefact, or to any Reflector-exclusive artefact.
- No dispatching of other agents.
- No judgment-level verification (semantic correctness, narrative alignment, voice register — all remain with the Reflector).

### 8.3.14 Seed templates

Preflight and postflight templates are reproduced in §8.3.6 above. A minimal first-run preflight, emitted at project-bootstrap time, has this shape:

```markdown
---
round: 0
tier_requested: T0
date: 2026-04-19
plugin_version: 0.5.5
marshal_schema_version: 1
first_run: true
---

# Marshal Preflight — Bootstrap (first run)

STATUS: PASS

## Blocking checks (reduced set)

- P-1 — classification.md exists: PASS
- P-2 — classification.md has `tier:` field: PASS (tier: T0)
- P-12 — no unresolved prior-round BLOCK: PASS (no prior rounds)
- P-13 — round_program override-tags use legal enum: N/A (no round_program.md)

## Notes

- First-run exemption applied: full preflight set activates from Round 2 onward.
```

### 8.3.15 Integration checklist for Phase F.2

When integrating this file into `AGENT_ORCHESTRATION.md §8.3`:

1. Paste §§8.3.1 through 8.3.14 verbatim under a new §8.3 header in `AGENT_ORCHESTRATION.md`, immediately after §8.2b.
2. Extend the writer/reader matrix in `AGENT_ORCHESTRATION.md §4` with the four Marshal artefact rows from §8.3.4 above.
3. Amend `agents/planner.md §Phase 0` opening to reference `reviews/marshal_preflight_<round>_<date>.md` per §8.3.8.
4. Amend `agents/planner.md §Phase 5` (after Phase 5.5 completes, before Reflector dispatch) to reference `reviews/marshal_postflight_<round>_<date>.md` per §8.3.8.
5. Amend `agents/reflector.md §Phase 2c` to add the three Marshal-derived metrics per §8.3.10.
6. Add a `marshal:` section to `references/tier_notifications.yaml` carrying three messages: preflight-BLOCK, postflight-BLOCK, and override-recorded.
7. Land `scripts/marshal_preflight.py` and `scripts/marshal_postflight.py`; add both to `scripts/release-gate.sh` as mandatory pre-release runs over `examples/`.
8. Update `SAFEGUARD_LAYER.md §Check 5` with a cross-reference to §8.3.9.
9. Update `CHANGELOG.md` with the two-phase rollout (Phase F.1 advisory-only, Phase F.2 BLOCK-active).
10. Update `TIER_PROTOCOL.md §9 — Relationship to Existing Files` to include a row for the Marshal.

Steps 1–10 are the full integration surface; each is additive and each preserves the existing single-writer invariants.

---

*File created 2026-04-19. Pairs with `research_notes/tier_marshal_design_v1.md` (prose rationale) and `scripts/marshal_preflight.py` / `scripts/marshal_postflight.py` (runtime). Targeted for Phase F.1 (v0.5.5, advisory-only) and Phase F.2 (v0.5.6, BLOCK-active).*
