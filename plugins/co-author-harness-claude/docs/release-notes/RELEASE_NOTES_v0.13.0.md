<!-- scholar-gateway-contract: v0.1 -->

# Release Notes — co-author-harness-claude v0.13.0

**Release date:** 2026-04-30
**Theme:** **Voice / register / citation lessons batch** from the INF3006Y late-April 2026 sessions — six clusters surfaced from the 2026-04-29 reverse-engineering handoff continuing into the 2026-04-30 manuscript polish session, plus the in-session voice round 2 + lay-term twin-fix. The patch closes operational-specificity gaps on existing C-1 / H surfaces and adds three new surfaces (Sub-check J under SAFEGUARD; new `CITATION_DISCIPLINE.md`; new top-level `EMDASH_BUNDLE_DISCIPLINE.md` with Generator binding).
**Verdict:** CLEARED — 0 blockers, 0 warnings across all four validation scripts at RC gate (run 2026-04-30 via DC cmd.exe with absolute paths and `PYTHONUTF8=1`).
**Status:** RC — seven content patches applied locally; release-gate cleared; git ceremony pending (deferred to user via GitKraken MCP per memory note `feedback_git_op_tool_preference.md`).

---

## 1. One-paragraph summary

v0.13.0 ships the lessons batch from the INF3006Y late-April 2026 sessions. The source memo is `docs/superpowers/plans/2026-04-30-voice-and-h-lessons.md`. Six lesson clusters land in seven content patches across four reference files, two new files, one agent file, and one memory entry. Two clusters amplify existing harness commitments with operational specifications (cluster 3.1 voice/attribution under C-1; cluster 3.5 lay-term corpus under `lay_term_lexicons.md §4`). Three clusters add new surfaces (cluster 3.2 Sub-check J under SAFEGUARD; cluster 3.4 new `CITATION_DISCIPLINE.md`; cluster 3.6 new top-level `EMDASH_BUNDLE_DISCIPLINE.md` binding the Generator at every prose action with no exceptions). One cluster is procedural (cluster 3.6 cross-file mirror grep discipline as a memory entry). Per the Q5 versioning-policy answer, three new surfaces plus a Generator default-behavior change (em-dash bundle binding) put this batch firmly in MINOR territory. The em-dash bundle is the user-emphasized item: "this rule applies to every instance with no exception"; waiver requires explicit per-session instruction naming paragraph + rule + rationale; inherited waivers from prior sessions are invalid; Generator cannot self-waive.

## 2. Work items

### 2.1 Cluster 3.1 — Voice / attribution discipline (amplifies C-1)

`references/STYLE_COMMITMENTS.md` gains a new §1.1 sub-section. Eight first-person verbs codified as the canonical Suchman-inflected register verb-set: `I identify` (hidden assumptions), `I read [X] as [Y]ing` (inferential moves whose outcome the source author may not endorse), `I press [N] questions against [Z]` (questions-framing predications), `I find` (evaluative verdicts), `I trace` (genealogies), `I group` (category construction), `I mark` (stipulative gestures), `I characterize` (paraphrases that the source author may not endorse). Direct attribution (`Author et al. argue/concede/flag`) preferred when the author would endorse the characterization; the `I read [X] as [Y]ing` indirect pattern preferred when the assumption is implicit/contestable.

Parallelism discipline added: when the same speech-act recurs at structurally parallel sites (sibling subsections, position subsections, cited-finding judgment moments), those sites must ship in a single voice. **Practical rule:** when one sibling site is voice-corrected, the rest must be audited within the same revision round. Reflector Check 6 voice audit treats sibling-site drift as a higher severity than isolated drift.

### 2.2 Cluster 3.2 — Verdict-edge / intensifier-stack diagnosis (Sub-check J, novel)

`references/SAFEGUARD_LAYER.md` gains Sub-check J — Verdict-Edge Discipline (sibling to A–H), advisory_until J_two_revision_cycles. Procedure audits three intensifier classes per sentence-clause: (a) emphatic determiners (`the very X`, `the same X`, `precisely the X`); (b) deontic-implicit phrasings (`supposed to`, `meant to`, `should X but doesn't`); (c) verdict verbs (`erodes`, `destroys`, `breaks down`, `is undermined by`). A cross-class stack of three or more across a single sentence-clause fires a J finding. Modal-distribution softening rule preserves diagnostic content while ceding the verdict claim: example transformation `is eroded by the very delegation patterns it is supposed to anchor` → `may not remain stable under the delegation patterns to which it is supposed to anchor accountability` (the INF3006Y Fügener-finding precedent).

Output format augmented with J line; aggregation rule updated to include J alongside G/H in the manuscript-wide MAJOR contribution and advisory_until exception list.

### 2.3 Cluster 3.3 — Twin-paragraph detection in H (novel probe)

`skills/accessibility-overlay/references/sub_checks.md §H` step 1 procedure augmented with a Twin-paragraph probe sub-section. When H closes a finding on a non-technical passage that ships specific shibboleth phrases (a Latinate construction such as `stipulating away`, a noun-pile compound such as `register-boundary light`, a four-times-repeated technical noun, or any phrase the H finding's evidence field cited as the violation locus), H emits a follow-on probe `twin_candidate_<finding_id>` performing a deterministic grep for those shibboleth phrases manuscript-wide. If grep returns >0 hits outside the original passage, H emits a `twin_candidate_<location>` finding for the next round at that location's passage role. Probe implemented as `_twin_paragraph` suffix in DETERMINISTIC_CHECKS §9e. Catches the §2 / §5 lay-term twin pattern documented in `lay_term_lexicons.md §5`.

### 2.4 Cluster 3.4 — Citation discipline at register-boundary asides (new file)

New file `references/CITATION_DISCIPLINE.md`. Two-question test for term-of-art invocations: (1) Engagement test — will the paper develop arguments specifically about the term's source-author's claims, or will the term recur substantively? If yes → engagement-cite. (2) Demarcation test — is the invocation's purpose to mark a register the paper does not enter, where the term is illustrative of a class? If yes → no cite (demarcation pattern).

INF3006Y precedents: `tool calls (Schick et al., 2023)` cited at engagement; `incentive-incompatibility` and `contract-net protocol coordinating a fleet of warehouse robots` un-cited at demarcation. Four edge cases documented: engaged-once-and-dropped (default engagement-cite); multiple terms in single sentence (cluster-cite acceptable); recurrence triggered by reviewer revision (retroactive engagement-cite); cross-reference-only invocations (use section-reference apparatus, no citation). Sub-check H interaction noted: register-boundary aside fixes default to demarcation-no-cite.

### 2.5 Cluster 3.5 — Lay-term protocol corpus addition (extends `lay_term_lexicons.md §4`)

`references/lay_term_lexicons.md` gains a new §5 "Verified lay-term paraphrase examples (INF3006Y, 2026-04-30 — DRIFT-MONITORED)." Seven paraphrase entries from the §2 closing aside fix and the §5 twin-paragraph fix:

| Original formulation | Accepted paraphrase | Marker gain |
|---|---|---|
| "stipulated, operationalizable definition" | "precise, measurable definition" | M3 |
| "stipulates away the very phenomena" | "defines away the phenomena" | M3 |
| "operational reductions that stabilize the same words" | "operational simplifications" | M3 |
| "in this register-boundary light, the cost..." | "the cost..." (drop noun-pile adverbial) | M2 |
| "delegation as task allocation under a coordination protocol" | "*delegation* is the auction-style assignment of tasks under fixed rules" | M1 + M3 |
| "decision authority over a defined choice space" | "the range of moves each robot's planner may choose" | M1 + M3 |
| "system-level behavior arising from local agent rules" | "the throughput pattern that arises when every unit follows local rules" | M1 + M3 |

Drift-detection grep-cadence requirement added: at every H-cycle on a contributing project, the source-phrase grep is mandatory before the H verdict closes. Implemented as `_corpus_drift` suffix in DETERMINISTIC_CHECKS §9e. Entry transitions to RETIRED status (with §4-style banner) if the source phrase returns zero hits in the live manuscript. The mechanism is the operational fallback for live-manuscript projects where source-snapshot stability cannot be assumed.

Worked-example signpost-as-M4-vehicle pattern added: `Take [a/an concrete-domain entity instance]: [italicised term-of-art] is [verb-active gloss]; ...` Italicization on the term-of-art signals §3.2 domain-token status; "Take X:" opener satisfies M4 directly; the concrete entity carries M1. **The recommended substitute** for M4-via-em-dash in technical-aside paragraphs at or below the §3 em-dash limit.

### 2.6 Cluster 3.6 — Em-dash bundle elevation (Q4 user-emphasized; top-level + Generator binding)

**This is the highest-emphasis cluster of v0.13.0.** Per user adjudication 2026-04-30: "this rule applies to every instance with no exception."

New file `references/EMDASH_BUNDLE_DISCIPLINE.md`. The bundle is three co-occurrent humanizer-style AI-tell rules: B1 em-dash overuse, B2 negative parallelism ("not just X but Y" stacks), B3 triadic-list / rule-of-three repetition. Mandatory at every Generator prose action with no exceptions; binding force parallel to GROUNDING_PROTOCOL.md (both override the §4 STYLE_COMMITMENTS.md relaxation procedure). Audit procedure: pre-action snapshot of all three rules' counts; apply the action; post-action snapshot; bundle delta check (post-count ≤ pre-count for each rule); cross-rule co-audit when any rule fires; commit only when all three are clear.

Fix procedure: when the Evaluator surfaces a finding under any of B1/B2/B3, the Generator co-audits the other two at the same site (mandatory), fixes all rules that fire in a single revision pass (multi-rule fixes commit as a single revision-log entry), and verifies post-fix.

Waiver process: requires explicit user instruction in the current session naming the paragraph, rule, and rationale; logged in `manuscript/revision_log.md` with `waiver_user_session: <session_id>` and the user's verbatim instruction. Inherited waivers from prior sessions are invalid; Generator cannot self-waive; Planner cannot waive on the user's behalf.

`agents/generator.md` gains a Second binding constraint paragraph after the GROUNDING_PROTOCOL paragraph at line 25.

`references/CLAUDE.md` §3 components table gains rows 9c (`EMDASH_BUNDLE_DISCIPLINE.md`, binding) and 9d (`CITATION_DISCIPLINE.md`).

### 2.7 Cluster 3.6 (procedural) — Cross-file mirror grep discipline

Memory entry `feedback_cross_file_mirror_grep_discipline.md`. After any cross-file edit touching paired canonical files (.md/.tex; .md/.docx; .ipynb/.py; etc.), run two verifying greps before declaring the round complete: (1) deprecated phrases must return zero across both files; (2) new phrases must return present in both files at corresponding line ranges. The discipline parallels but is distinct from `unified-superkit:verification-before-completion` — that skill is broader; this one specifically targets the cross-file mirror failure mode that surfaced repeatedly across the INF3006Y voice/attribution rounds (2026-04-30).

## 3. Validation

The harness's standard four-script gate ran 2026-04-30 via DC cmd.exe with `PYTHONUTF8=1` and absolute Python + script paths. All four scripts CLEARED with 0 blockers, 0 warnings:

- **skill-check.py** — 32 shipped skills discovered; 0 blockers; 0 warnings.
- **version-check.py** — manifest version 0.13.0 = README latest version 0.13.0 = CHANGELOG top version 0.13.0; marketplace self-referencing entry `co-author-harness-claude=0.13.0`; 0 blockers; 0 warnings.
- **catalog-check.py** — 32 discovered skills; 16 discovered commands; README skills count `<missing>` (informational only, not a blocker); 0 blockers; 0 warnings.
- **path-hygiene-check.py** — 0 blockers.

Cross-file content verification on the seven patches has been completed in-session (all new content present at expected line ranges across the seven affected files; no residual deprecated phrases in the four files containing pre-edit shibboleth language).

## 4. Files modified

| File | Type | Change |
|---|---|---|
| `references/STYLE_COMMITMENTS.md` | Amend | New §1.1 (C-1 verb-set + parallelism rules) |
| `references/lay_term_lexicons.md` | Amend | New §5 (DRIFT-MONITORED corpus) + v0.13.0 status header |
| `skills/accessibility-overlay/references/sub_checks.md` | Amend | New "Twin-paragraph probe" sub-section under H step 1 |
| `references/SAFEGUARD_LAYER.md` | Amend | New Sub-check J + output-format augmentation + aggregation rule update |
| `references/CITATION_DISCIPLINE.md` | New file | 6 sections, 1 versioning row |
| `references/EMDASH_BUNDLE_DISCIPLINE.md` | New file | 6 sections, 1 versioning row |
| `agents/generator.md` | Amend | Second binding constraint at line 27 |
| `references/CLAUDE.md` | Amend | Rows 9c and 9d added to §3 components table |
| `docs/superpowers/plans/2026-04-30-voice-and-h-lessons.md` | New file | Source memo (5 sections) |
| `.claude-plugin/plugin.json` | Amend | Version bump 0.12.3 → 0.13.0 |
| `.claude-plugin/marketplace.json` | Amend | Version bump 0.12.3 → 0.13.0 |
| `README.md` | Amend | Version bump + table row for v0.13.0 |
| `CHANGELOG.md` | Amend | New v0.13.0 entry at top |
| Memory `feedback_cross_file_mirror_grep_discipline.md` | New | Cross-file mirror grep discipline rule |

## 5. Lessons / Reflector feed-forward (recurrence-audit candidates)

Three recurrence-audit candidates surface from this batch:

1. **Operational-specificity gap closure validation.** Three of the six clusters were "discoverable from C-1 / H principles in place but not operationally caught." The recurrence audit at the next manuscript H-cycle should monitor whether the new operational rules (verb-set, twin-paragraph probe, intensifier-stack floor) emit findings at meaningfully higher detection rates than prior rounds. If yes → the operational specificity is closing real gaps. If no → the lessons may have been overfit to INF3006Y; surface as Reflector Phase 2g cross-project recurrence audit for adjudication.

2. **Drift-monitored corpus path validation.** The `lay_term_lexicons.md §5` entries are anchored to live-manuscript source phrases. The `_corpus_drift` probe must run at every H-cycle on INF3006Y. First drift-detection on a contributing source phrase will validate or falsify the path-(a) approach (drift-detection grep-cadence) vs. the deferred path-(b) approach (immutable `references/examples/` commit). If multiple §5 entries flip to RETIRED within two cycles, the immutable commit path becomes preferred for future corpora.

3. **Bundle-treatment economy claim.** The em-dash bundle treatment claims "single audit pass with three-rule coverage" reduces Generator overhead vs. three separate audits. Reflector Phase 2g should monitor whether bundle-flagged paragraphs in subsequent rounds show co-occurrence of all three rules (validating the cluster-signal premise) or fire independently (suggesting the bundle is a discipline-of-convenience rather than an empirical-cluster rule).

## 6. RC-to-FINAL transition

Status of the transition steps:

- ✅ **Four validation scripts cleared.** Run 2026-04-30 via DC cmd.exe; 0 blockers, 0 warnings across all four. Output preserved at `outputs/v013_validators_output.txt`.
- ✅ **Content-cross-references resolve.** `references/CLAUDE.md` row 9c → `references/EMDASH_BUNDLE_DISCIPLINE.md` exists; row 9d → `references/CITATION_DISCIPLINE.md` exists; both new files cross-reference back into MASTER and READER_ACCESSIBILITY (cross-reference verification by grep).
- ⏸ **Optional .plugin archive build.** Pending — `scripts/release-gate.sh --build` not yet run; deferred to user discretion.
- ⏸ **Git ceremony.** Deferred to user via GitKraken MCP per memory note `feedback_git_op_tool_preference.md`: commit on `release/v0.13.0` branch; annotated tag `v0.13.0`; merge to `main` via `--no-ff`; verify with `git diff main^1 main --stat` and `git ls-tree` before push (per memory note `feedback_merge_ceremony_checkpoint.md`); push to origin.

---

End of release notes.
