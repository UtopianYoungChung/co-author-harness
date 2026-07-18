# Voice / Register / Citation Lessons from INF3006Y Late-April 2026 Sessions — Patch Proposal

**Status:** PROPOSAL — not yet adopted; awaiting user adjudication on patch placement and version-bump expectations.
**Date:** 2026-04-30
**Authored:** Cowork session, post-INF3006Y manuscript polish (the §2 / §5 lay-term twin-fix landing in both `Finalized.md` and `INF3006_redistributing_initiative_YJC.tex`).
**Provenance:** Lessons consolidated from two consecutive INF3006Y sessions (handoff `2026-04-29-204048-inf3006y-reverse-engineering.md` continuing into `2026-04-30-180606-inf3006-paper-polish-and-figma-atlas.md`, then this session's voice round 2 + lay-term twin-fix). Each lesson surfaced as a recurrent failure pattern that the harness's existing protocols either did not cover, partially covered, or covered but did not apply consistently.
**Bound to:** STYLE_COMMITMENTS.md C-1 (Suchman-inflected register); SAFEGUARD_LAYER.md Check 8 + Sub-check H; `skills/accessibility-overlay/references/sub_checks.md §H`; `references/lay_term_lexicons.md §4` corpus; `references/DETERMINISTIC_CHECKS.md §3` (em-dash false-fix pattern); the D-02 / P0 register diagnostic codes (existing).
**NOT bound to:** Figma Plugin API discipline, draw.io retirement, or atlas migration mechanics — those are project-execution lessons captured separately in memory notes (`feedback_figma_plugin_api_pattern.md`, `project_inf3006y_atlas_figma.md`) and out of scope here.

---

## 1. Summary

Six lesson clusters surfaced across the two-session arc. Two amplify existing harness commitments with concrete verb-sets and parallelism rules (cluster 1: voice/attribution; cluster 5: lay-term corpus). Three are novel and require new sections in existing files (cluster 2: intensifier-stack diagnosis; cluster 3: twin-paragraph detection in H; cluster 4: citation discipline at register-boundary asides). One is procedural and lives at the workflow layer (cluster 6: cross-file lockstep verification).

The memo proposes patch targets but defers per-file diffs to the next stage. It also flags a corpus-entry drift-risk: the INF3006Y manuscript remained live throughout both sessions, so any new `lay_term_lexicons.md §4`-style corpus entries drawn from these edits face the same retirement-risk that retired the 2026-04-27 entries on 2026-04-28. The recommended path is path (b) from the prior conversation: author entries with explicit drift-detection grep-cadence, accepting the risk rather than waiting for indefinite manuscript closure.

## 2. Problem Statement

The two sessions produced 11 voice/attribution edits, 1 verdict-edge softening, 2 lay-term protocol fixes (the §2 closing aside and the §5 twin), 1 em-dash protocol pass, and 1 keywords refinement. Each round of edits surfaced a pattern where:

- The **same failure recurred at multiple sites** within the manuscript (e.g., the hidden-assumption diagnoses across §3's six framings — three sibling sites had drifted into passive voice while one had been first-person-corrected; the §2 / §5 lay-term twin where identical Latinate constructions appeared in structurally parallel paragraphs).
- The **fix was discoverable from harness principles already in place** (C-1's "first-person navigation; resistance to disembodied abstraction" already names the discipline) **but the harness lacked the operational specificity** that would have caught the failure during the manuscript's earlier rounds. C-1 is a commitment, not a verb-set; H is a marker frame, not a twin-paragraph detector.
- A **few lessons were genuinely novel** and pointed to gaps the existing protocols had not surfaced. Citation discipline at register-boundary asides (the contrast between `(Schick et al., 2023)` cited at engagement and `incentive-incompatibility` un-cited at register-boundary) is one example; intensifier-stack as a verdict-edge signal (the "the very" + "supposed to" + "is eroded" stack on the Fügener-finding line) is another.

The patches below close the operational-specificity gap on what's already a commitment and add new sections where the gap is genuine.

## 3. Lesson Clusters and Recommended Patch Targets

### 3.1 Voice and attribution discipline (amplifies C-1)

**Pattern.** Convert impersonal/passive constructions that smuggle in authorial judgment into either first-person verbs or named attribution. Three classes of conversion recurred:

(a) **Hidden-assumption identification** across sibling sections. Where one §3 framing had been corrected to "I identify a hidden assumption: [X]" (Structural-emergence), three sibling framings retained "The hidden assumption is that [X]" / "The assumption shared across these framings is [X]" / "The project assumes [X]" passive constructions. Same speech-act, different voices — a parallelism failure. **Discipline:** when one sibling site is voice-corrected, the rest must be audited within the same round.

(b) **Questions-framing predications** ("[N] questions against [it/this position]") had drifted across §4.1, §4.2, §4.3 between three different voices: passive-infinitival ("are worth pressing"), active-no-agent ("Two questions press"), passive-modal ("should be pressed"). **Discipline:** structurally repeated predications should ship in a single voice — uniform "I press [N] questions against [X]" or whatever the chosen frame.

(c) **Judgment-attribution moments** ("The finding suggests..." / "Haslam's folk-concept data suggests...") where the inferential work was author-supplied but the predication smuggled it through the data as agent. **Discipline:** "I read this finding as suggesting" / "I read [Author]'s data as suggesting" makes the inference visible.

The verb set that surfaced as canonical: `I identify`, `I read [X] as`, `I press`, `I find`, `I trace`, `I group`, `I mark`, `I characterize`. Use direct attribution (`Author et al. argue/concede/flag`) when the author would endorse the characterization; use `I read [X] as [Y]ing` when the assumption is implicit/contestable and the author might not endorse.

**Patch target.** STYLE_COMMITMENTS.md C-1 is the canonical home, but the operational specificity belongs as a sub-section under C-1 or as a new appendix to that file: "C-1 verb-set and parallelism rules." The §H sub-checks file could also reference this, since the discipline manifests at the prose surface H audits.

### 3.2 Verdict-edge / intensifier-stack diagnosis (novel)

**Pattern.** Three intensifiers stacked in close succession ("the very" + "supposed to" + "is eroded") signal a drift from diagnostic to verdict register. Each on its own is acceptable; the stack tips the sentence into evaluative territory the surveyed-literature diagnostic register should not occupy. The user's protocol output classified this as a D-02 / P0 register WARN with optional softening.

**Diagnostic.** When auditing a sentence, count intensifiers of three classes: (a) emphatic determiners (`the very X`, `the same X`, `precisely the X`), (b) deontic-implicit phrasings (`supposed to`, `meant to`, `should X but doesn't`), (c) verdict verbs (`erodes`, `destroys`, `breaks down`, `is undermined by`). A stack of three or more across a single sentence-clause warrants softening to modal/equivocal phrasing (`may not remain stable`, `is challenged by`, `does not always hold`).

**Recommended softening pattern.** Distribute the modal load: "is eroded by the very X it is supposed to anchor" → "may not remain stable under the X to which it is supposed to anchor." This preserves the diagnostic content while ceding the verdict claim.

**Patch target.** New sub-section in `SAFEGUARD_LAYER.md` Check 8 sub-checks (or as a new sub-check, sibling to H). Could also live as a new section in `READER_ACCESSIBILITY.md` or as a discipline note in `STYLE_COMMITMENTS.md` C-1 (since verdict register conflicts with C-1's diagnostic stance). Recommendation: new sub-check sibling to H with the working name "Sub-check J — Verdict-Edge Discipline" and an `advisory_until` flag.

### 3.3 Twin-paragraph detection in H (novel)

**Pattern.** The §2 closing aside ("A note on the register the survey does not enter") and the §5 closing summary (originally "One register sits just outside the survey...") were a structural twin pair. Both function as register-boundary asides. Both used the identical phrases "stipulating away" and "operational reductions that stabilize." Both shared the same parenthetical (`intentionality, endorsement, situated practice`). Both had zero positive marker 1 (concrete referent) and zero positive marker 4 (signposting). Fixing one without scanning for the other would have left a conspicuous asymmetry in the published manuscript.

**Discipline.** When Sub-check H closes a finding on a non-technical passage that ships specific shibboleth phrases (the `stipulating away` Latinate, the noun-pile compound, the four-times-repeated technical noun), H step 1 should flag a **twin-scan probe**: grep for the same shibboleth phrases manuscript-wide before declaring the fix complete. The sister paragraph is almost always a §5/§6 mirror of a §1/§2 aside (or a §3/§4 mirror of a §2/§3 aside) because the manuscript's argumentative arc returns to the same conceptual debt at the closing.

**Patch target.** Augment `skills/accessibility-overlay/references/sub_checks.md §H` with a "Twin-paragraph probe (added v0.10.x+)" sub-section under "H step 1 procedure." Probe is implemented as a deterministic grep over the manuscript for shibboleth phrases isolated at the fix site, post-finding-close. If matches return >0 hits outside the fixed passage, H emits a `twin_candidate_<location>` finding for the next round.

### 3.4 Citation discipline at register-boundary asides (novel)

**Pattern.** The harness has implicit but unstated citation-discipline at register-boundary asides. The §1 line invoking `tool calls (Schick et al., 2023)` cites because the term-of-art anchors a specific argument the paper engages. The §3 line invoking *incentive-incompatibility* (a formal-MAS term-of-art) does not cite because the invocation is illustrative — the paper is naming the not-this register, not engaging Smith 1980's specific construction. The §2 closing-aside revision adopting "contract-net protocol coordinating a fleet of warehouse robots" was held to the §3 standard rather than the §1 standard: no Smith 1980 citation, on discipline-coherence grounds.

**Discipline.** A two-question test for any term-of-art invocation:

1. **Engagement test.** Will the paper develop arguments specifically about this term's source-author's claims, or will the term recur substantively in the paper? If yes → cite (engagement-cite pattern, e.g., Schick).
2. **Demarcation test.** Is the invocation's purpose to mark a register the paper does not enter, where the term is illustrative of a class rather than a specific construction the paper engages? If yes → no cite (demarcation pattern, e.g., incentive-incompatibility, contract-net).

The two tests should be mutually exclusive in practice. Borderline cases (the term is engaged once and dropped) lean toward engagement-cite to preserve the principle of "name → cite." Pure illustrative invocations at register-boundary asides should remain un-cited to avoid citation bloat and engagement-overstatement.

**Patch target.** New section in `references/MASTER_research_and_paper_guidelines.md` or new file `references/CITATION_DISCIPLINE.md`. Recommendation: new file, since this is a discrete rule that may grow as more patterns surface (e.g., epigraph citations, footnote-only citations). Cross-reference from `MASTER` and `READER_ACCESSIBILITY.md`.

### 3.5 Lay-term protocol corpus additions (extends `lay_term_lexicons.md §4`)

**Pattern.** The §2 closing aside fix and the §5 twin-paragraph fix produced two new paraphrase patterns worth memorializing:

- **Latinate-construction → plain-verb pair.** "stipulates away" → "defines away"; "operational reductions that stabilize" → "operational simplifications that would stabilize"; "in this register-boundary light" (noun-pile) → drop, restructure as direct predication.
- **Worked-example signpost as M4 vehicle.** "Take a contract-net protocol coordinating a fleet of warehouse robots: *delegation* is..., *autonomy* is..., *emergence* is..." pattern. Three formal-MAS term-of-art definitions verb-ified within a "Take X:" introductory frame. Italicization on the three terms (per §3.2) signals term-of-art status without forcing them through the H concrete-referent count. The "Take X:" opener satisfies marker 4 (register-shift signposting) and the worked-example carries marker 1 (concrete referent: warehouse robots) where the original abstract paragraph had neither.

**Drift-risk caveat.** The 2026-04-27 INF3006Y corpus entries (§4 of `lay_term_lexicons.md`) were retired on 2026-04-28 because the project owner kept editing the source manuscript. The current edits face the same risk: the INF3006Y manuscript is live by the same standard. Two compatible mitigations:

1. **Drift-detection grep-cadence.** Each new corpus entry is anchored to its source phrase. A grep-cadence requirement is added to `lay_term_lexicons.md §4`: at the next H-cycle on the source project, the source phrase is grepped; if absent, the entry transitions to RETIRED status with the same banner pattern as the 2026-04-27 entries.
2. **`references/examples/` commit option.** If the user wants to commit excerpts of the §2 / §5 revisions as immutable corpus material, the relevant paragraph snippets land in `references/examples/INF3006_voice_corpus_2026-04-30.md` (or similar) with a content-hash anchor. This is the v0.10.2 stability path.

**Patch target.** Two patches to `lay_term_lexicons.md`:
(a) Add a new §5 "Verified lay-term paraphrase examples (INF3006Y, 2026-04-30 — DRIFT-MONITORED)" with the §2 / §5 fixes and the drift-detection grep-cadence requirement.
(b) Update §1.0 status header to reflect the new corpus addition and the drift-monitored status.

### 3.6 Cross-file lockstep verification (procedural)

**Pattern.** Every multi-file edit in this session paired (a) Edit-tool fix on .md, (b) Edit-tool fix on .tex, (c) grep for old phrases (must return zero), (d) grep for new phrases (must return present). The discipline catches a class of failures where the second-file mirror diverges silently — typically when the LaTeX form requires a citation-macro adjustment or character-escape that .md doesn't.

**Discipline.** After any cross-file edit that touches both .md and .tex (or any sibling pair), run two verifying greps before declaring the round complete: one on the deprecated phrases (must return empty), one on the new phrases (must return on both files). The discipline parallels but is distinct from `verification-before-completion` (which is broader); it specifically targets the .md/.tex sync failure mode.

**Patch target.** Brief addition to `unified-superkit:finishing-a-development-branch` SKILL.md or `unified-superkit:verification-before-completion` SKILL.md as a "cross-file mirror discipline" note. Could also be captured as a memory entry under `feedback_*` since it's a small recurrent procedural rule.

## 4. Recommended Patch Sequence

Patches should land in a single v0.12.x patch release (no major version bump, since none of the lessons require a protocol-breaking change). Suggested patch ordering:

1. **`STYLE_COMMITMENTS.md` C-1 amplification** (cluster 3.1). Smallest patch surface; lowest regression risk.
2. **`lay_term_lexicons.md` §5 corpus addition with drift-detection grep-cadence** (cluster 3.5). Self-contained; opt-in via the §4-style RETIRED-banner pattern.
3. **`skills/accessibility-overlay/references/sub_checks.md §H` twin-paragraph probe** (cluster 3.3). Augments existing H step 1 procedure; backward-compatible if the probe is `advisory_until` flagged.
4. **`SAFEGUARD_LAYER.md` Sub-check J — Verdict-Edge Discipline** (cluster 3.2). Adds a new sibling sub-check; `advisory_until` flag preserves existing severity calculus.
5. **`references/CITATION_DISCIPLINE.md` new file** (cluster 3.4). Pure addition; cross-references from MASTER and READER_ACCESSIBILITY.
6. **`unified-superkit:verification-before-completion` cross-file mirror note** (cluster 3.6). Smallest patch; could be inlined as a memory entry instead.

Patches 1, 2, 5 are pure additions with no governance risk and could be batched as a v0.12.4 content-update release. Patches 3, 4 augment audit-emitting protocols and warrant an `advisory_until` two-cycle period before they enter the §3.3.3 TerminalSignoffRow gate. Patch 6 is procedural and version-bump-optional.

## 5. Open Questions for User Adjudication

1. **Patch placement for cluster 3.2 (intensifier-stack).** Sub-check J sibling to H, OR new section in C-1 of STYLE_COMMITMENTS, OR new section in READER_ACCESSIBILITY? My recommendation is Sub-check J, but the verdict-register concern is also a stylistic-commitment concern.

2. **Corpus path for cluster 3.5.** Path (a) — drift-detection grep-cadence within `lay_term_lexicons.md §5` — OR path (b) — commit excerpts to `references/examples/INF3006_voice_corpus_2026-04-30.md` for stability? My recommendation is path (a) since the INF3006Y manuscript may continue evolving and immutability would lose touch with the live state. But if you anticipate additional projects extracting from this corpus, path (b) is sounder.

3. **CITATION_DISCIPLINE.md as new file vs. section in MASTER.** New file is cleaner if more citation rules surface over time; MASTER section is lighter-weight if this is the only rule in the file. My recommendation is new file with intent to grow.

4. **Em-dash bundle (humanizer rule 13 + rule 9 + rule 11).** Already partly in DETERMINISTIC_CHECKS §3 line 63 (the H-motivated em-dash insertion pattern). Should the BUNDLE-treatment discipline (audit all three rules together) be promoted to a top-level discipline note, or is the line-63 pattern sufficient?

5. **Version bump expectation.** Patches batched as v0.12.4 (content additions, advisory-only protocol additions) — does this match your release-cadence expectations, or do you want the patches deferred to v0.13.0 alongside other architectural changes?

---

End of memo.
