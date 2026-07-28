# REVIEW ORCHESTRATION — How to Run the Joint Review



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

**Purpose.** This file is the **runbook** for reviewing an academic piece with the full guidelines package. It tells you: what classification to assign, which files apply, what to read at each step, what to emit, and how to synthesize the findings into one prioritized action list.

**Precedence.** Read `CLAUDE.md` (this folder) first if you are not sure when to invoke the package; this file assumes the decision to invoke has been made.

**Relationship to MASTER.** `MASTER_research_and_paper_guidelines.md` is the **reference map** (principles, traceability, Parts A–J). This file is the **runbook** (procedure, gating, emission format). Both are needed; they do different jobs.

---

## 1. Before you start: classify the piece

Before opening the draft, record four inputs:

| Input | Options | Where used |
|---|---|---|
| **Paper type** | `theory` · `empirical` · `conceptual/survey` · `essay/positioning` · `response-letter` · `other` | Determines which component files apply (§3 gating table) |
| **P-stage** | `P0` (phenomenon collection) · `P1` (characterization) · `P2` (research-problem definition) | Filters checklist items in `project_writing_style_checklist.md` |
| **Venue** | e.g. CAiSE, RE, JAIS, MISQ, CHI, CSCW, course essay, thesis chapter | Sets precedence overrides for venue-specific template/stylesheet |
| **Review depth** | `quick` (one pass, ≤ 3 files) · `standard` (full package, routine) · `submission-bound` (full package + G.4 sign-off) | Controls whether the full seven-step pass is required |

**Default if unclear:** ask the user. If the user declines to classify, default to `essay/positioning · P1 · cross-venue · standard`.

**"Review depth" triggers:** The **submission-bound** pass is required (per MASTER §Policy) for: final draft for journal/conference submission; a course paper marked *final*; a thesis chapter sent to committee or deposited; any resubmission after reviews; a response letter plus revised manuscript. All other cases may use `standard` or `quick`.

**Future dimensions.** Additional gating dimensions can be added later (e.g. `domain` ∈ {IS, HCI, SE, AI, philosophy, critical studies}; `audience` ∈ {engineering, social, mixed}). When added, they should appear in this table and propagate to §3.

---

## 2. Run order at a glance

| Order | Step | File | What it does here |
|---|---|---|---|
| 0 | Pre-flight | `scripts/sk20_preflight_gate.py` | Deterministic Coupling E.2 gate check (`wiki_linked`, `coupling_e_on_review`, graph presence/freshness, classification, citations). Writes both readiness and no-op artifacts before SK-20 is attempted. |
| 0a | Pre-flight | `DETERMINISTIC_CHECKS.md` | Mechanical grep/count pass. Runs in minutes, catches the measurable tics before any judgment-based review. |
| 0b | Pre-flight | `MASTER_research_and_paper_guidelines.md` (Parts A–B, G.1 summary) | Establish the principles in working memory; skim the traceability matrix. |
| 1 | Lifecycle | `general_research_project_guidelines.md` | Is the piece at the right milestone? Is scope consistent with its stage? |
| 2 | Cross-venue playbook | `research_paper_writing_guidelines.md` | Claims, hedging, theory framing, audience, citations, response-letter craft, workflow. |
| 3 | IS shape (if applicable) | `baird_2021_writing_guidelines.md` | Five-element model, nine-step process, Who/What/Why/When/Where/How lenses. Skip if paper is not IS theory or empirical. |
| 4 | Sentence craft | `bacon_2009_well_crafted_sentence_guidelines.md` | **Concept-introduction priority gate** (provenance, derivation continuity, scope authority), then focus, semantic-predication integrity, balance, modification, variety, and revision heuristics §10. |
| 5 | Narrative craft | `Sexton_Fiction_to_Academic_Writing_Guide.md` | Arc, show/tell, cause–effect, openings, title, voice. |
| 6 | Project invocation rules | `CLAUDE.md` (this folder) | Confirm precedence; record any conflicts with venue/advisor rules. |
| 7 | Integrated checklist | `project_writing_style_checklist.md` | The deduplicating pass: every applicable checkbox for this stage and paper type, with severity. |
| 8 | Synthesis | *this file, §7 below* | Compose the consolidated findings report; prioritize; propose edits. |
| 8.5 | Safeguard | `SAFEGUARD_LAYER.md` | Post-report integrity checks: regression guard, drift detection, abstract-body consistency, contradiction audit, edit traceability, humanness voice audit. Run after the report, before the author approves edits. |
| 9 | Re-check | `DETERMINISTIC_CHECKS.md` (re-run) | After edits, re-run the mechanical pass to verify fixes landed and no new tics slipped in. |

**Step 7 is intentionally last** because `project_writing_style_checklist.md` integrates Sexton + Bacon + Baird in one place. Running it last catches overlaps in one pass and closes the loop.

**Step 8.5 is the safeguard layer.** It runs eight checks that the seven-step review does not prescribe: regression from edits, drift between rounds, abstract-body promise resolution, unacknowledged theoretical contradictions between co-invoked sources, edit traceability enforcement, humanness voice auditing, inter-sentential logical connective auditing, and reader-experience / prose architecture auditing. At `quick` depth, only checks 1, 4, and 5 run. At `standard` and `submission-bound`, all eight run (Check 8's submission-bound-only aloud-read pass aside). Output is appended to the consolidated report as §10. Check 7 receives its candidate-paragraph list from the pre-filter in `DETERMINISTIC_CHECKS.md §9a`; Check 8 receives its candidate-location list from the pre-filter in `DETERMINISTIC_CHECKS.md §9b` (both pre-filters added 2026-04-13).

---

## 3. Applicability gating (paper type × P-stage × review depth)

The goal of gating is to prevent the reviewer from mechanically applying rules that do not fit the piece. Cells below mark whether each component file applies: **Y** = fully apply; **P** = partially apply, use only the sub-sections named; **N/A** = skip (note it in the findings report).

### 3.1 By paper type

| Component file | theory | empirical | conceptual / survey | essay / positioning | response-letter |
|---|---|---|---|---|---|
| `general_research_project_guidelines.md` | Y | Y | Y | Y | P (§ Final Paper only) |
| `research_paper_writing_guidelines.md` | Y | Y | Y | Y | Y (esp. §8) |
| `baird_2021_writing_guidelines.md` | Y (theory track) | Y (empirical track) | P (§4 nine steps) | P (§2 five areas only) | N/A |
| `bacon_2009_well_crafted_sentence_guidelines.md` | Y | Y | Y | Y | Y |
| `Sexton_Fiction_to_Academic_Writing_Guide.md` | Y | P (§§1, 3, 6, 9, 10) | Y | Y | P (§§1, 3, 5, 6, 8) |
| `project_writing_style_checklist.md` | Y | Y | Y | Y | P (Parts 1–3 only; Part 4 §§11–15 mostly N/A) |

### 3.2 By P-stage (project_writing_style_checklist.md filtering)

| Section of checklist | P0 | P1 | P2 |
|---|---|---|---|
| Part 1 §1 Central need | **[P0]** problem phenomenon | **[P1]** characterization lens(es) | **[P2]** RQs q1/q11/q21 |
| Part 1 §3 Climax | **[P0]** refined problem statement + handoff | **[P1]** characterization map + tensions | **[P2]** RQ resolution + tradeoffs |
| Part 2 | All apply at all stages | — | — |
| Part 3 | All apply at all stages | — | — |
| Part 4 §11 Theoretical tension | Challenging assumptions (informal) | Challenging assumptions | Full Baird framing |
| Part 4 §11 Resolution | **Deferred** | **Deferred** | **Required** |
| Part 4 §11 Guidelines for application | **Deferred** (use forward-pointing handoff) | **Deferred** (use forward-pointing handoff) | **Required** |

**Anti-patterns by stage** (from `project_writing_style_checklist.md` Part 0):

- **P0/P1:** Do not pose numbered answer-demanding RQs. Do not use P2 vocabulary ("resolution," "answers"). Use refined problem statements and forward-pointing candidate q-items.
- **P2:** Do not stop at a problem statement. Convergence is expected.

### 3.3 By phase (v0.8.0 Lifecycle-Phase Ladder; vocabulary migrated 2026-07-07 — tier-era codes like `E-PSTAGE-REQUIRED-AT-T2` remain stable historical identifiers)

The Planner reads the classification record (`reviews/classification.md`) and the per-section state in `reviews/phase_state.json` to choose the dispatched rung. `current_phase` takes legal values from `{Ph1, Ph2, Ph3, Ph3_converged, Ph4, ceiling_locked}` (the `T0` state probe is retired since v0.5.5; the v0.6.0 `T4_ready` value was renamed `Ph3_converged` at v0.7.0 and is `Ph3_converged` under phase vocabulary). Response letters enter as a **manuscript-class within Ph3** via `/response-letter-review` (the former independent `T3R` sibling ladder was folded at v0.14.0; `T3R` survives only as the historical label of that entry point). The four lifecycle phases are: **Ph1 Plan & Draft**, **Ph2 Review & Revise**, **Ph3 Iterate & Converge**, **Ph4 Finalize & Close**. Each rung runs `plan → (review at Ph2+) → generate → human approval`; user approval auto-advances the section to the next rung (or locks its ceiling if the ceiling was set below the default). For the full ladder semantics — rung preconditions, the binary Approve / Reject gate, the Manuscript Convergence Report (MCR), and the 18-field `phase_state.json` SectionStateObject invariant — see `references/PHASE_PROTOCOL.md §§2–6`.

**All-drafts amendment (2026-07-22; capability clarification 2026-07-27).** At Ph1, the Evaluator performs the bounded complete applicable governing-policy pass after each Generator publication, including centroid review only when enabled by the authoritative reader binding. Ph2 remains the first *full revision-maturity* review. This controls over the older engagement wording retained in the table.

| Phase | Name | Required review steps at this rung | Agent engagement | Ceiling effect | G.4 sign-off |
|---|---|---|---|---|---|
| `Ph1` | **Plan & Draft** (entry rung) | Generator drafts under the declared P-stage register on full-file grounding, followed by the bounded independent current-byte Evaluator policy pass required by `policies/phase_engagement.v1.json`. **No Self-Ph1 Verdict is emitted** — Phase 3.5 retired at v0.7.0. Approval writes `ph1_draft_completion_signed` then `user_approval` and auto-advances section to **Ph2 entry**. | Planner + Generator + bounded independent Evaluator + Reflector-lightweight. | Approval bumps `current_phase → Ph2`; if `section_ceiling_override = Ph1` the section locks (`ceiling_locked`) and further lifecycle invocations refuse-to-escalate. | No |
| `Ph2` | **Review & Revise** (first Evaluator engagement) | 0a + Step 2 (playbook) or Step 3 (Baird, if IS) scoped to the section envelope + Step 7 (integrated checklist, local items only) + SAFEGUARD checks 1, 4, 5. **Confirmation Mode at Ph2 entry is retired at v0.7.0**: every Ph2 entry runs a fresh Evaluator local-scope pass. Pre-phase-advance check clauses (a)(b)(d)(g) always enforce: Ph1 exit artefact presence, 18-field section populated, non-null `ph1_pstage_declaration` (E-PSTAGE-REQUIRED-AT-T2; code spelling historical), row-shape conformance. (Clause (e) — i* SD/SR structural-completeness — retired at v0.11.0.) Emits `reviews/local_findings_<date>.md` tagged `scope: section`. EG-3 fires on any cross-scope reference ("the finding or fix references material outside the section's `heading_path`"). | Full four-agent loop with Reflector-lightweight. | Approval bumps `current_phase → Ph3` and sets `ph3_last_activity_at`; ceiling-locked if `section_ceiling_override ≤ Ph2`. | No |
| `Ph3` | **Iterate & Converge** (unbounded loop) | 0a (incl. §9a, §9b pre-filters) + 0b + Steps 1–7 + Step 8 (synthesis) + Step 8.5 (all eight SAFEGUARD checks, Coupling E.2 overlay optional). `convergence_metric = diff_lines_vs_previous_round / total_section_lines` computed per round; two consecutive rounds < 0.03 emits `[CONVERGENCE-STABLE]` (W-CONVERGENCE-STABLE) and flips `current_phase: Ph3 → Ph3_converged` via TerminalSignoffRow. `[Ph3-STALE]` is purely computed from `ph3_last_activity_at` against wall-clock (Option A, no persisted flag); null short-circuits to false. Drift exceedance under tolerant mode at Ph3 emits `W-T3-DRIFT-EXCEEDED-TOLERANT` (code spelling historical; warning only, not forced re-review — preserves Ph3's unbounded-loop contract). Linear-Accountability: ESCALATED findings require named owner; transfer requires `transfer_rationale` (E-OWNERSHIP-TRANSFER-WITHOUT-RATIONALE). | Full four-agent loop with Reflector-lightweight. | Two-round convergence flips `current_phase: Ph3 → Ph3_converged`; ceiling-locked if `section_ceiling_override ≤ Ph3`. | Optional |
| `T3R` *(historical label)* | **Response-letter manuscript-class** (enters Ph3 via `/response-letter-review`) | `response-letter-review` seven checks + SAFEGUARD 1/4/5 + Rule 7a when Class-1 verifiers cited. Emits `reviews/response_letter_findings_<date>.md`, `reviews/response_letter_reframe_brief_<date>.md`, `manuscript/response_letter.md`. Escalation-out rules per `PHASE_PROTOCOL.md §2.5` (historically `TIER_PROTOCOL.md §2.5`) (the `t3r_escalation_out` trigger repurposes `mcr_admission` under the LCR→MCR rename). | Full four-agent loop with Reflector-lightweight. | Runs inside Ph3 as a manuscript-class; approval closes the response-letter cycle. | Optional (required if paired with a Ph4 manuscript pass) |
| `Ph4` | **Finalize & Close** (submission-bound, terminal composition) | 0a (incl. §9a, §9b pre-filters) + 0b + Steps 1–7 + Step 8 + Step 8.5 (all eight checks, Coupling E.2 overlay at ≥15% echo+shallow threshold) + Step 9 (re-check). External verifiers REQUIRED (Zotero, Scholar Gateway). **Admission gated by the Manuscript Convergence Report (MCR)**: Ph4 cannot open unless every section in `phase_state.json` reports `current_phase = Ph3_converged` or `ceiling_locked` AND no computed `[Ph3-STALE]`. `[Ph3-STALE]` block → E-MCR-BLOCKED-Ph3-STALE; user clears through a Planner re-engagement intent. Legal Ph4→Ph3 demotions: EG-1 (`eg1_ph4_downgrade_to_ph3`) on Rule 1–7 grounding violation; EG-7 (`eg7_mcr_readmission_after_class_change`) on classification change. | Full four-agent loop with **Reflector-FULL** (five-phase close-out: Phase 2b NEW-H-4 aggregated confirmation-failed history audit, Phase 3 lessons, Phase 4 skill proposals, Phase 5 memory; attempts Coupling C/D Wiki mutation (deferred: `WIKI_WRITE_TRANSACTION_UNAVAILABLE`; non-blocking for Phase 4 completion)). | Approval sets `terminal_phase_reached = true`; final `user_approval` row has `new_phase: "Ph4"`. | **Required** (MASTER §G.4 table completed, including 8.5 row) |

**Diff-scoped vs. full-document reads.** At `Ph1` the Evaluator performs the bounded independent current-byte pass defined by `policies/phase_engagement.v1.json`. The Rule 1 phase-gated digest exception was **retired at v0.7.4** (`GROUNDING_PROTOCOL.md §Rule 1`) — full-file reads are the grounding floor at every phase, including Ph1 drafting. At `Ph2` the Evaluator reads the section envelope on full-file reads. At `Ph3` (including the response-letter manuscript-class) and `Ph4` the Evaluator reads the full manuscript.

**Migration from v0.6.0 (historical record; scripts since retired from the tree).** Classification records written under v0.6.0 that carried `tier: T4_ready` were remapped at first read: `T4_ready → T3_converged` (now `Ph3_converged`). The entry-log pipe-row and JSON column names changed from `from_tier` / `to_tier` to `prev_tier` / `new_tier` (now `prev_phase` / `new_phase` under the seven-field row shape). Records carrying the retired trigger `confirmation_failed` were preserved read-only by the (retired) `migrate_v060_to_v070.py` so the Reflector-full Phase 2b NEW-H-4 audit at Ph4 can still aggregate the historical Confirmation Mode dataset; the trigger does not fire natively. See `references/TIER_PROTOCOL.md §10` (retired/migration-only file) for the per-field migration map and `docs/release-notes/RELEASE_NOTES_v0.7.0.md` for the breaking-change register.

## 3a. Output modes (v0.14.0 output economy)

Evaluator outputs are split into three forms:

1. **`evidence_packet`:** machine-readable check evidence stored under `reviews/.harness/evidence/<event_id>.json` (F7), indexed in `reviews/.harness/events.jsonl`.
2. **`action_list`:** short human-facing list of BLOCKER and MAJOR actions needed for manuscript movement, plus a MINOR count; details live in the evidence packet unless the user escalates.
3. **`final_report`:** end-of-round synthesis assembled from evidence packets and revision logs (`reviews/final_round_report_<round_id>.md`, F8).

Routine per-step detail is written as evidence packets. A Markdown findings report in the legacy F1 shape is an **exception output**, used when a blocker requires user adjudication, a phase gate fails, or the user requests the full report. Normative rules: `references/OUTPUT_ECONOMY_PROTOCOL.md`.

---

## 4. What to emit at each step (per-step findings format)

At every step, produce a short block with this exact shape so synthesis in §7 is predictable:

```
### Step <N> — <file>
- Applies: [Y / Partial / N/A] · reason if Partial or N/A
- Stage gating: [P0 / P1 / P2 / all]
- Items checked: <count of checklist items / sections walked>
- Violations: 
  - [location in piece] → [rule, with §reference] → [severity] → [proposed fix]
  - ...
- Deferred to later stage: [items tagged for a stage above the current one]
- Notes / conflicts with other files: [...]
```

**Severity vocabulary (consistent across all steps):**

| Tag | Meaning | Examples |
|---|---|---|
| **[BLOCKER]** | Structural failure that undermines the argument or integrity. Must fix before submission. | Fabricated citation; surprise construct in Results; universal "cannot" without evidence; unresolved argument contradiction (e.g. Baumer vs. fixed-schema i\*); wrong register for stage (P2 RQs in a P0 paper). |
| **[MAJOR]** | Substantive weakness that readers will notice and that weakens credibility. Fix if time permits before submission; definitely fix in revision. | Defensive abstract; unused analytical apparatus; deficit framing of other fields; missing Haslam-style operationalization of a titled concept; citation supporting a different claim than the one it sits beside. |
| **[MINOR]** | Polish-level. Fix in the tightening pass; does not affect acceptance. | Em-dash count; sentence-length variety; parallel-structure tweaks; single "must" → "should" swap; minor parenthetical placement. |

When severity is ambiguous, default **up** one level (treat a possible BLOCKER as BLOCKER) and note the uncertainty.

---

## 5. Overlap map (which rule lives where)

Many rules appear in multiple files. Use this map to avoid re-processing the same rule seven times. When a rule is handled in its **authoritative** file, note it and move on; at later steps, only re-flag if the other file adds a distinct angle.

| Rule | Authoritative file | Also mentioned in | Review handling |
|---|---|---|---|
| "Cannot / must" absolutes | `research_paper_writing_guidelines.md` §2.3 | MASTER §B.1; `project_writing_style_checklist.md` (implicit) | Apply at Step 2. Don't re-check at Steps 3–6. Step 7 catches any survivors. |
| Em-dash minimization | MASTER §E.2 | Playbook §7; `project_writing_style_checklist.md` Part 3 §9 (implicit via "fresh diction") | Apply at `DETERMINISTIC_CHECKS.md` (Step 0a) as a count check. No judgment pass needed. |
| "Not X but Y" LLM tic + triadic lists + glossary dumps | MASTER §A.4.2 | (nowhere else) | Run as part of Step 0a deterministic count pass. |
| Red thread / hourglass | MASTER §A.1 | Baird §1; Playbook §5.5; `project_writing_style_checklist.md` Part 4 §10 | Apply at Step 3 (Baird) for IS papers; Step 5 (Sexton) for narrative; Step 7 catches universally. Don't re-read for each file. |
| "Don't say what you don't do" / defensive framing | Playbook §2.4, §8 | MASTER §B.2 | Apply at Step 2. Response-letter review adds Step 2 §8 on top. |
| Show-then-tell, concrete anchors | `Sexton_Fiction_to_Academic_Writing_Guide.md` §2 | Playbook §5.4; MASTER §D.2; checklist Part 2 §4 | Apply at Step 5. Step 7 catches any abstract runs missed. |
| External theories "drawn on," not extended | Playbook §3.1 | MASTER §B.4 | Apply at Step 2. Don't re-check. |
| Agency of models (models are instruments) | MASTER §B.4 row 3 | Playbook §3.4 | Apply at Step 2. |
| First-person navigation, asymmetric rhythm, lived-in detail | MASTER §A.4.2, §I, §J | Bacon §3.1–3.3, §9.5 | Apply at Step 4 (Bacon) for craft; Step 0a handles the LLM-tic counts. MASTER §I/J are the authoritative voice reference; Bacon provides the structural rules. |
| Semantic-predication integrity | Bacon §3.6; `sentence-level-pass` Check 10 | `project_writing_style_checklist.md` Part 3 §6 | Apply the five judgment tests at Step 4. Step 7 verifies coverage but does not duplicate a recorded finding. A claim-changing bearer mismatch is MAJOR. |
| Concept-introduction priority gate | Bacon §3.7; `sentence-level-pass` Phase 2 priority gate | `project_writing_style_checklist.md` Part 3 §6 | Run before ordinary sentence craft at Step 4 and verify at Step 7. An unintroduced construct or unsupported field-wide unit claim that changes the analytical frame is MAJOR even if its definition is grammatically clear. |
| Sentence length distribution (~15–20 tech / ~25 prestige / avoid 60+) | MASTER §F.5 | Bacon §9.5 | Apply at Step 0a deterministic pass. |
| "Synonyms are the enemy" / construct provenance | `project_writing_style_checklist.md` Part 4 §15 | Baird Step 6; Playbook §3.6 | Apply at Step 7. |
| P0/P1/P2 stage anti-patterns | `project_writing_style_checklist.md` Part 0 | MASTER §C.2 | Apply at classification (§1 of this file) and at Step 7. |
| Surprise constructs in Results | Baird §4 Step 5 | — | Apply at Step 3 for empirical papers. |
| Response letter: don't open with limitations | Playbook §8 | MASTER §B.2; `project_writing_style_checklist.md` (implicit) | Apply at Step 2 for response letters. |
| Currency claims with recent references | Playbook §6 | MASTER §A.2 | Apply at Step 2. |
| LaTeX preservation (\\label, \\ref, \\cite) | Playbook §7 | MASTER §E.3 | Apply whenever editing LaTeX. Not a review item per se. |

**Rule of thumb for adding new rows.** When a rule is added anywhere in the package, record its authoritative location in this map so subsequent reviews can skip duplicates.

---

## 6. The pre-flight deterministic pass (Step 0a)

Run the deterministic pre-flight checks before any judgment-based review.

### 6.1 Coupling readiness check (Step 0)

When a project is expected to run Coupling E.2, run:

```bash
python scripts/sk20_preflight_gate.py --project-root "<project-root>" --date "YYYY-MM-DD"
```

Interpretation:

- `should_run_sk20: true` → SK-20 is eligible to run.
- `should_run_sk20: false` → do not attempt SK-20; fix failed checks first.
- Artifacts are append-only evidence for why Coupling E fired or no-oped:
  - `reviews/coupling_readiness_YYYY-MM-DD.json`
  - `reviews/sk20_noop_YYYY-MM-DD.json` (only when not ready)

After Step 8 or round close, generate trend artifacts:

```bash
python scripts/coupling_health_report.py --project-root "<project-root>"
```

This writes `reviews/coupling_health.md` + `reviews/coupling_health.json` so repeated readiness failures and no-op reason codes are measurable across rounds.

### 6.2 Mechanical language checks (Step 0a)

Invoke the audit suite — **do not LLM-count the patterns yourself**. As of v0.15.0-pre, the runtime is `scripts/audit/run_all.py`; `DETERMINISTIC_CHECKS.md` is rule rationale, not the source of patterns.

```
python scripts/audit/run_all.py <manuscript> --project-root <project-root> --date YYYY-MM-DD --out reviews/findings.json
```

The script writes `reviews/findings.json` (schema in `scripts/audit/schema.py`) and,
when `--project-root` is supplied, `reviews/d_style_profile_YYYY-MM-DD.json`. Read the
JSON and emit a count block of this shape:

```
Deterministic check results
- em-dashes: <n> (threshold: 0 per paragraph for paragraphs > 1 pair; 0 nested)
- "not X but Y" / "not just X but Y": <n> (threshold: ≤ 2 per paper)
- triadic lists (three parallel items): <n> (threshold: reduce by half)
- trailing one-sentence add-ons after paragraph breaks: <n>
- sentences > 60 words: <n>
- absolutes (must|cannot|comprehensively|anticipate): <n> with locations
- there is / there are: <n>
- reveals / exposes / proves: <n>
- glossary dumps (≥ 4 consecutive italicized definitions): <y/n>
- hedged transitions (accordingly, likewise, therefore, in practical terms) at every paragraph break: <y/n>
```

Every number above a threshold becomes a **[MINOR]** in Step 0a's findings (or **[MAJOR]** for absolutes/unsupported cannot claims). This pre-flight output feeds into Step 8 synthesis.

---

## 7. Step 8: Synthesis (consolidated findings report)

After walking Steps 0–7, produce one **Consolidated Findings Report** using this template. This is the artifact that goes to the user and/or into the manuscript's revision log.

```markdown
# Consolidated Findings Report

**Piece:** <title or filename>
**Reviewed:** <date>
**Classification:** <type> · <stage> · <venue> · <depth>
**Reviewer:** <name or "Claude"> 

## 1. Summary (2–4 sentences)
<What the piece does well; the dominant structural concern; the estimated gap to submission-ready.>

## 2. Blockers (must fix)
- [location] → [rule, file §] → [proposed edit]
- ...

## 3. Major issues (fix if time permits)
- [location] → [rule, file §] → [proposed edit]
- ...

## 4. Minor issues (polish pass)
- [location] → [rule, file §] → [proposed edit]
- ...

## 5. Deterministic check summary
<paste the count report from Step 0a; note which counts are above threshold>

## 6. Items deferred or marked N/A
- [item] → [reason: wrong stage / wrong paper type / venue override / user instruction]
- ...

## 7. Conflicts encountered
- [two rules in tension] → [how it was resolved, or user question]
- ...

## 8. G.4 sign-off (submission-bound only)
| Step | Component file | Reviewed | Notes |
|---|---|---|---|
| 1 | general_research_project_guidelines.md | Y/N | |
| 2 | research_paper_writing_guidelines.md | Y/N | |
| 3 | baird_2021_writing_guidelines.md | Y/N | |
| 4 | bacon_2009_well_crafted_sentence_guidelines.md | Y/N | |
| 5 | Sexton_Fiction_to_Academic_Writing_Guide.md | Y/N | |
| 6 | CLAUDE.md (package) | Y/N | |
| 7 | project_writing_style_checklist.md | Y/N | |
```

**Prioritization rules inside the report:**

1. List BLOCKERs in order of dependency (fix the root; other issues often resolve downstream).
2. For each BLOCKER, identify whether it is structural (argument/claim/evidence) or integrity (citation/data/attribution). Structural issues usually unlock MAJORs; integrity issues are standalone.
3. MAJORs and MINORs are listed by file location (top-to-bottom of the piece) so the user can fix them in one pass.
4. If any BLOCKER invalidates whole sections, say so explicitly ("fixing this may require rewriting §3").

---

## 8. Re-check loop (Step 9, submission-bound only)

After the author applies fixes:

1. Re-run `DETERMINISTIC_CHECKS.md`. Confirm counts are within thresholds.
2. Spot-check the top three BLOCKERs to confirm the proposed edit was applied as specified.
3. If any new file-level change was made (new paragraph, new section, new citation), run the checks that apply to those changes — not a full re-review.
4. Update the G.4 sign-off table with dates.
5. If a new BLOCKER is introduced by the fixes (this happens more often than expected), loop back to Step 7.

---

## 9. Quick-review shortcut (when the user says "just a quick look")

For `quick` depth:

1. Run Step 0a (deterministic).
2. Read the piece once against `research_paper_writing_guidelines.md` (Step 2), focusing on §§1–4 (tone, claims, theory, audience).
3. Apply `project_writing_style_checklist.md` Parts 1–3 (Step 7, skip Part 4 unless IS).
4. Produce a **Short Findings** report: Summary + top 5 issues with severity.

Skip the full synthesis template unless the user asks for it. If anything in the quick pass looks like a BLOCKER, stop and escalate to `standard` depth.

---

## 10. When to ask the user

- **Classification ambiguity** (paper type, stage, venue unclear).
- **Severity ambiguity** where the rule appears to conflict with something the user did deliberately.
- **Rule conflict** between two component files that the precedence chain in Package CLAUDE.md §4 does not cleanly resolve.
- **Scope creep detected** (user asked for a review; the piece needs structural rewriting before review is useful).

In all other cases, proceed; note the decision in the report §7.

---

*This file is the runbook for the Research and Academic Paper Writing Package. For the principles themselves, consult the MASTER and the component files. For the invocation trigger, see Package CLAUDE.md. For worked examples, see `examples/`.*
