# Plugin-Update Proposals — Planner Three-Filter Gatekeeper Log

*This file is the user-facing, Planner-authored gatekeeper log for Reflector-full plugin-update proposals. Per `agents/planner.md` §§78, 335, the Planner is the **sole gatekeeper**: Reflector-full emits raw candidates into an internal buffer; the Planner applies three filters before any proposal reaches the user. Filters are: (a) proposal cites grounding evidence; (b) proposal names the skill or package affected; (c) proposal declares the R- or A-code it invokes. Failures route back to the Reflector with a remediation note.*

*File created 2026-04-23 during v0.8.1 release steps in response to the user directive "route all five proposals through the Planner three-filter gatekeeper." Source: `Ph.D. Research/INF3006Y_AgencyDelegation/reviews/ai-author/reflection_report_2026-04-23.md §Phase 4`.*

---

## Session: v0.8.4 close-out (2026-04-24)

**Closure.** Packaged work shipped as **v0.8.4** in response to the plugin-gap review. The v0.8.1-session items **A6–A9** (P-R-1..P-R-4) are treated as **IMPLEMENTED** with the paths below; user sign-off is this release’s merge.

| A-code / proposal | Shipped as |
|-------------------|------------|
| **A6** `A6-scale-coverage-metacheck` (P-R-1) | `agents/reflector.md` Phase 2g **§2g.1a** (§9d G-candidate scale PATTERN) |
| **A7** `A7-advisory-until-template` (P-R-2) | `references/ADVISORY_UNTIL_SCOPING.md` |
| **A8** `A8-provenance-prewrite-check` (P-R-3) | `scripts/provenance_prewrite_check.py` + `agents/planner.md` cache §3a |
| **A9** `A9-sub-check-g-prefilter-script` (P-R-4) | `scripts/check8_g_prefilter.py` + `scripts/release-gate.sh` `py_compile` list |

**Efficiency / docs.** `.plugin-efficiency.json` `role_overrides` completed for the eight skills that were previously unmapped. `references/CLAUDE.md` component #33 now names **`phase_notifications.yaml`** as authoritative.

---

## Session: v0.8.1 release (2026-04-23)

Five Reflector-full proposals filed from INF3006Y Co Author Ph4 close-out. Three-filter gatekeeper results below.

### P-R-1 — Promote L-v0.8.1-01 scale-coverage meta-check to Reflector Phase 2g

**Raw source:** `Ph.D. Research/INF3006Y_AgencyDelegation/reviews/ai-author/reflection_report_2026-04-23.md §Phase 4, Proposal P-R-1`.

**Filter results:**

| Filter | Verdict | Note |
|---|---|---|
| (a) cite grounding evidence | PASS | Cites this session's Sub-check G gap discovery (INF3006Y Co Author Ph4 meta-critique round). |
| (b) name skill/package affected | PASS | Names `agents/reflector.md` Phase 2g extension. |
| (c) declare R- or A-code | **FAIL** | Raw Reflector output omitted the code. Planner formalization below. |

**Planner formalization:** Assigned **A-code `A6-scale-coverage-metacheck`** (package-tier addition; Reflector Phase 2g scope). Re-evaluate under (c) with code attached: PASS.

**Aggregate verdict:** **ADVANCED with Planner code assignment.** Surface to user for sign-off on `A6-scale-coverage-metacheck`. Target release: v0.8.2. Evidence caveat: n=1 discovery; a second discovery in a later project strengthens the case but does not gate the proposal.

---

### P-R-2 — Advisory-until scoping pattern as a reusable template

**Raw source:** same reflection report, P-R-2.

**Filter results:**

| Filter | Verdict | Note |
|---|---|---|
| (a) cite grounding evidence | PASS | Cites D-G-4 advisory-until decision and its documented benefit (no retroactive Ph3 reopening on the Co Author manuscript under the flag). |
| (b) name skill/package affected | PASS | Names `references/PHASE_PROTOCOL.md §3.3.3` and `references/SAFEGUARD_LAYER.md`. |
| (c) declare R- or A-code | **FAIL** | No code declared. |

**Planner formalization:** Assigned **A-code `A7-advisory-until-template`** (package-tier pattern; future SAFEGUARD / Grounding Protocol additions).

**Aggregate verdict:** **ADVANCED with Planner code assignment.** Surface to user for sign-off on `A7-advisory-until-template`. Target release: v0.8.2. Generalizability is strong on first principles (any future BLOCKER-grade addition benefits); does not need a second observed instance to proceed.

---

### P-R-3 — Planner provenance-metadata pre-write sanity check

**Raw source:** same reflection report, P-R-3.

**Filter results:**

| Filter | Verdict | Note |
|---|---|---|
| (a) cite grounding evidence | PASS | Cites the Round 17 Post-round Integrity Addendum in `manuscript/revision_log.md` (wrong-file provenance hash; caught on author challenge rather than by automation). |
| (b) name skill/package affected | PASS | Names `scripts/pre_phase_advance_check.py` and `agents/planner.md` pre-write checklist. |
| (c) declare R- or A-code | **FAIL** | No code declared. |

**Planner formalization:** Assigned **A-code `A8-provenance-prewrite-check`** (script + Planner-contract extension; runs before ledger writes).

**Aggregate verdict:** **ADVANCED with Planner code assignment.** Surface to user for sign-off on `A8-provenance-prewrite-check`. Target release: v0.8.1.1 (patch) or v0.8.2. Risk class (ledger integrity under wrong-file provenance) is high-leverage; single-round evidence does not block advancement when the failure mode is catastrophic-if-recurrent.

---

### P-R-4 — §9d pre-filter executable script (`scripts/check8_g_prefilter.py`)

**Raw source:** same reflection report, P-R-4.

**Filter results:**

| Filter | Verdict | Note |
|---|---|---|
| (a) cite grounding evidence | PASS | Cites the §9d spec in `references/DETERMINISTIC_CHECKS.md` (this session) and the `accessibility-overlay/SKILL.md` v1.1 Integration paragraph naming §9d as G's deterministic feeder. |
| (b) name skill/package affected | PASS | Names `scripts/check8_g_prefilter.py` (new) and the `scripts/release-gate.sh` skill-check integration point. |
| (c) declare R- or A-code | **FAIL** | No code declared. |

**Planner formalization:** Assigned **A-code `A9-sub-check-g-prefilter-script`** (script addition; architectural completeness follow-on).

**Aggregate verdict:** **ADVANCED with Planner code assignment.** Surface to user for sign-off on `A9-sub-check-g-prefilter-script`. Target release: v0.8.1.1 (patch) — v0.8.1 shipped the §9d prose spec but not the executable script; closing this gap is an architectural-completeness follow-on rather than novel work. Note: the v0.8.1 README entry explicitly flags this as a deferred follow-on ("executable `scripts/check8_g_prefilter.py` deferred per P-R-4").

---

### P-R-5 — `skills/run-phase-3-stability/SKILL.md §3.2a` Sub-check G advisory rule

**Raw source:** same reflection report, P-R-5.

**Filter results:**

| Filter | Verdict | Note |
|---|---|---|
| (a) cite grounding evidence | PASS | Cites D-G-3 decision and the `SAFEGUARD_LAYER.md` Check 8 Sub-check G "Stability sub-mode interaction" subsection pointer. |
| (b) name skill/package affected | PASS | Names `skills/run-phase-3-stability/SKILL.md §3.2a` (in the v0.8.1 unpacked tree). |
| (c) declare R- or A-code | N/A — **IMPLEMENTED this session.** |

**Planner formalization:** No code assigned; the rule shipped in the v0.8.1 unpacked tree at `unpacked/research-writing-harness-claude-v0.8.1/skills/run-phase-3-stability/SKILL.md §3.2a` during the pre-cut session documented in `Ph.D. Research/.claude/handoffs/2026-04-24-v081-rollout-steps-1-4-complete.md`. The `SAFEGUARD_LAYER.md` Sub-check G "Stability sub-mode interaction" paragraph now correctly defers to §3.2a.

**Aggregate verdict:** **IMPLEMENTED — no user sign-off required.** Status in `proposals/check8_subcheck_g_consolidation_anchors_proposal.md` implementation log already reflects the shipped state; this entry records the gatekeeper closure.

---

## Summary table

| ID | Status | A-code | Target release |
|---|---|---|---|
| P-R-1 | ADVANCED — awaiting user sign-off | `A6-scale-coverage-metacheck` | v0.8.2 |
| P-R-2 | ADVANCED — awaiting user sign-off | `A7-advisory-until-template` | v0.8.2 |
| P-R-3 | ADVANCED — awaiting user sign-off | `A8-provenance-prewrite-check` | v0.8.1.1 or v0.8.2 |
| P-R-4 | ADVANCED — awaiting user sign-off | `A9-sub-check-g-prefilter-script` | v0.8.1.1 (architectural-completeness) |
| P-R-5 | IMPLEMENTED (this session) | — | v0.8.1 (shipped) |

**Reflector remediation note (filed in memory for next Reflector-full run):** Future Reflector-full proposals MUST declare an R- or A-code in the raw buffer. When the code is absent, the Planner must formalize by assigning one; this adds a handoff round that could be avoided if the Reflector proposes a code with the candidate. Reference: `agents/planner.md §78` and `agents/reflector.md §86`. Propose codes in the nominal `A<next-free-integer>-<slug>` or `R<next-free-integer>-<slug>` form; the Planner reserves the right to re-assign on formalization.

**Next steps (after user sign-off on A6–A9):**
1. File each advanced proposal into its target release's architecture document.
2. For A8 and A9 targeted at v0.8.1.1, open a patch-release branch or follow-on work item.
3. For A6 and A7 targeted at v0.8.2, add to `proposals/v0.8.2_upgrade_architecture.md` (new file) when that release opens.

---

## Session: workspace C-6 gap close-out (2026-07-03)

One Reflector proposal filed from a workspace/process root-cause analysis (not a manuscript close-out). Advisory and gatekept; **PROPOSAL only, not an applied change.** No active harness check was modified in filing this.

### P-R-6 — Upstream the deterministic C-6 term/metaphor tripwire into the harness

**Raw source:** `B:/Agents/reference/c6-gap-analysis-and-mitigation.md` (workspace diagnosis, 2026-07-03) and workspace lesson `research_notes/lessons_learned.md` L-P6.

**Proposal (advisory).** Add a deterministic C-6 term/metaphor tripwire to the harness itself — a check in `references/DETERMINISTIC_CHECKS.md` (and/or a small companion script) that reads a maintained watchlist and flags watchlisted evocative/loaded terms and unscoped metaphors as a **REVIEW** (forces a look; does not adjudicate). The intent is to place the backstop in *every* project rather than only in the workspace `style_lint.py`, mirroring the workspace mitigation now proven in QE2026.

**Motivation.** C-6 (`STYLE_COMMITMENTS.md §1.0a`) is a judgment commitment owned by the Generator (write-time) and Evaluator (review-time); `DETERMINISTIC_CHECKS.md` measures jargon density and glossary-dump form, not term-definedness / single-sense / loaded-metaphor, so no deterministic C-6 backstop exists. Two load-bearing terms ("reciprocity", "ratifies") reached live prose via hand-edits gated only by a mechanical lint that never triggered the C-6 judgment. A watchlist-driven REVIEW tripwire converts a silent pass into a forced look at the one moment C-6 is otherwise bypassed.

**Filter results (Reflector self-assessment; Planner adjudicates):**

| Filter | Verdict | Note |
|---|---|---|
| (a) cite grounding evidence | PASS | Cites `c6-gap-analysis-and-mitigation.md` and the implemented workspace artifacts (`style_lint.py` watchlist read, `c6_watchlist.txt`, `terminology_register.md`). |
| (b) name skill/package affected | PASS | Names `references/DETERMINISTIC_CHECKS.md` (new C-6 term/metaphor check) and an optional companion script; relates to `STYLE_COMMITMENTS.md §1.0a` (policy unchanged). |
| (c) declare R- or A-code | PROPOSED — **A10** `A10-c6-term-metaphor-tripwire` | Reflector proposes the code per the standing remediation note; Planner reserves the right to re-assign on formalization. |

**Known limit (stated up front).** The tripwire is **heuristic**. It flags only watchlisted terms and will miss a novel loaded term or a metaphor not on the list; it forces a look but does **not** adjudicate C-6. The process rule — a `style_lint`/mechanical PASS is not a C-6 pass; term/metaphor edits get a Generator or targeted-audit C-6 judgment (L-P6) — remains **primary**. The check is a backstop, not a substitute for the judgment.

**Evidence caveat.** n=2 within one workspace (the "answerability leaks" precedent plus this round's "reciprocity"/"ratifies"); cross-project recurrence is plausible on first principles (any project hand-editing load-bearing terms after the last agent pass is exposed) but not yet observed in a second project. Does not gate the proposal; strengthens it if a second project surfaces the same miss.

**Aggregate verdict (Reflector):** ADVANCED to the Planner gatekeeper for the three-filter pass and user sign-off. **No `DETERMINISTIC_CHECKS.md` or any active check was modified in filing this.**

---

*File maintained by the Planner per `agents/planner.md §§78, 335`. The Reflector writes into an internal buffer; this file is the user-facing view.*
