# SAFEGUARD LAYER — Post-Review Integrity Checks

**Purpose.** This file prescribes eight structured checks that run **after** the consolidated findings report is drafted (Step 8) but **before** the author approves edits. It is Step 8.5 in `REVIEW_ORCHESTRATION.md`. Its job is to catch problems the seven-step review does not prescribe: regression from edits, drift between rounds, abstract-body inconsistency, unacknowledged theoretical contradictions, untraceable edits, voice degradation from AI-assisted revision, unwarranted inter-sentential logical connectives, and reader-experience / prose-architecture failure.

**When to run.** Always, at every review depth (`quick`, `standard`, `submission-bound`). For `quick` depth, run checks 1, 4, and 5 only. For `standard`, run checks 1, 2, 3, 4, 5, 6, and 8 (Check 7 is `submission-bound` only because it consumes the full §9a pre-filter). For `submission-bound`, run all eight. At the Lifecycle-Stage Ladder rungs: Evaluator dormant at **T1**; at **T2** run checks 1, 4, 5, and **8** (accessibility baseline); at **T3** run all eight; at **T4** run all eight. See `agents/evaluator.md §Step 8.5` for tier-conditioned dispatch.

**Relationship to other package files.**
- `DETERMINISTIC_CHECKS.md` catches mechanical tics **before** the judgment review.
- This file catches integrity failures **after** the judgment review and **after** edits are proposed or applied.
- `REVIEW_ORCHESTRATION.md` §7 (consolidated report) is the input; this file's output is appended as §10 of that report.

**Provenance.** Checks 1–6 below were identified during the INF3001 and INF3006Y review applications (2026-04-09) as gaps the existing package did not close. Checks 7 (Inter-Sentential Logical Connective Audit) and 8 (Reader-Experience / Prose Architecture Audit) were authored at v0.7.2 to close the cross-file contract gap where `agents/evaluator.md §Step 8.5` and `skills/run-tier-3/SKILL.md §5` referenced "all eight checks" and the `DETERMINISTIC_CHECKS §9b` pre-filter fed a "Check 8 work queue" that had no judgment-layer consumer; Check 8 additionally operationalises Ph.D.-root CLAUDE.md §13.3 (Hard Constraint #8) as an enforced T3 convergence gate. Check 8 was extended on 2026-04-23 from six Sub-checks (A–F, all local-scale) to seven (A–G, adding the cumulative-scale Sub-check G) in response to the INF3006Y Co Author Ph4 test variant, which surfaced a case where every local Sub-check passed yet the manuscript accumulated six framings and three positions across twenty pages with no consolidation summary — the reader-experience gap Sub-check G now audits. See `examples/INF3001_walkthrough.md` §15 and the package-effectiveness evaluation for the reasoning behind Checks 1–6; see `RELEASE_NOTES_v0.7.2.md` for the reasoning behind Checks 7 and 8 at introduction, and `READER_ACCESSIBILITY.md §13.1–§13.2` and §13.5 for the reasoning behind the 2026-04-23 two-scale expansion.

---

## Check 1 — Regression Guard

**Trigger:** Run after every edit round (not just at submission-bound depth).

**Procedure:**

1. **Re-run `DETERMINISTIC_CHECKS.md`** on the edited file. Save as `step_0a_deterministic_<date>.md`.
2. **Compare the new counts to the prior round's counts.** For each pattern:
   - If the count **increased**, flag the increase as a regression. Example: em-dash count went from 0 to 3 after a revision round → the revision introduced em-dashes.
   - If the count **decreased or stayed the same**, mark as PASS.
3. **Re-verify each previously fixed BLOCKER and MAJOR.** For each item that was fixed in a prior round:
   - Read the specific passage that was fixed. Confirm the fix is still in place.
   - If the fix was overwritten, reverted, or weakened by a subsequent edit, flag as BLOCKER (regression).
4. **Voice-register spot-check.** If the original review confirmed a specific voice register (e.g. "Vidal-cartographer with Suchman first-person at hinges"), read the three passages most central to that register. Confirm they still exhibit the markers. If first-person hinges were replaced with impersonal constructions, or if a Vidal-style refusal-to-synthesize was softened into a false synthesis, flag as MAJOR (voice regression).

**Output format:**

```
### Check 1 — Regression Guard
- Deterministic re-run: [date, saved as ...]
- Count changes: [list any increases with the pattern name]
- Previously fixed items re-verified: [n of n confirmed in place]
- Regressions found: [0 / list with locations and severity]
- Voice register: [confirmed / regressed at <location>]
```

---

## Check 2 — Drift Detection

**Trigger:** Run at the start of every review round (before reading the piece for judgment).

**Procedure:**

1. **Identify the last-reviewed version.** Check `manuscript/revision_log.md` for the most recent Round entry. Note the date and the file state at that point.
2. **Diff the current file against the last-reviewed state.** If the project uses version control, `git diff`. If not, compare line counts, checksums, or a manual scan of the file for changes not recorded in the revision log.
3. **Flag any unrecorded changes.** If changes appear in the file that are not logged in `revision_log.md`:
   - List each changed passage with its location.
   - Ask the author: "These changes are not recorded in the revision log. Were they authorized?" Wait for confirmation before proceeding with the review.
4. **If no unrecorded changes:** Mark as PASS and proceed.

**Output format:**

```
### Check 2 — Drift Detection
- Last reviewed version: [Round N, date]
- Current file state: [line count, word count, or checksum]
- Unrecorded changes: [0 / list with locations]
- Author confirmation: [received / pending / not needed]
```

**Why this matters.** Between review rounds, files may be edited by the author, by a co-author, by a linter, or by another AI session. If the reviewer proceeds without detecting these changes, the review's findings may be based on a text the reviewer thinks is stable but isn't. The INF3001 review exposed this: line 92 had changed between rounds without being logged.

---

## Check 3 — Abstract ↔ Body Consistency

**Trigger:** Run after any structural edit (new sections, rewritten abstract, changed contribution statement).

**Procedure:**

1. **Extract the key claims from the abstract.** Read the abstract and list 3–5 specific commitments it makes. Examples of commitments:
   - "I develop the placement argument through course materials, a loan-officer illustration, and i\* modeling."
   - "The contribution is disciplinary and analytical."
   - Names a specific concept (e.g. "humanness," "identity-sensitive requirements").

2. **For each commitment, verify resolution in the body.**
   - Does the body **deliver** what the abstract promises? (E.g., if the abstract says "i\* modeling," does the body contain an actual i\* construct mapping?)
   - Does the body **use** every concept the abstract names? (E.g., if the abstract names "humanness," does the body deploy the Haslam two-sense taxonomy on a specific case, or does it stop at the definition?)
   - If the abstract promises X and the body does not deliver X, flag as **BLOCKER** ("title/abstract promise not paid off").

3. **Extract key constructs from the opening sections (§§1–2).** List every italicized, bolded, or formally defined term. For each:
   - Does it reappear in the analytical sections (§§3–5 or equivalent)?
   - If a construct is defined in §1 but vanishes before it does analytical work, flag as **MAJOR** ("unused apparatus").

4. **Check the roadmap (if present).** Compare the section roadmap in §1 to the actual section headings. If the roadmap says "§3 develops the modeling apparatus" but §3 is titled "Implications," flag as **MINOR** (roadmap ↔ heading mismatch).

**Output format:**

```
### Check 3 — Abstract ↔ Body Consistency
- Abstract commitments extracted: [list]
- Commitment resolution:
  - [commitment 1] → [resolved at §X / NOT resolved → severity]
  - [commitment 2] → [resolved at §X / NOT resolved → severity]
  - ...
- Constructs defined in §§1–2: [list]
- Construct deployment:
  - [construct 1] → [deployed at §X / UNUSED → severity]
  - [construct 2] → [deployed at §X / UNUSED → severity]
  - ...
- Roadmap ↔ headings: [aligned / mismatched at ...]
```

**Why this matters.** The Haslam-taxonomy-not-operationalized problem on INF3001 was the single most consequential BLOCKER found during the review — and the package's existing rules did not prescribe this check. The BLOCKER was caught by judgment, not by structure. This check makes it structural.

---

## Check 4 — Contradiction Audit

**Trigger:** Run whenever the piece draws on two or more theoretical sources to support different parts of the argument.

**Procedure:**

1. **List the theoretical sources the paper draws on simultaneously.** Include any source whose concepts do load-bearing work in the argument (not merely cited for context).

2. **For each pair of co-invoked sources, ask:** Do their foundational commitments conflict?
   - If Source A assumes entities are **stable and bounded** (e.g., i\* assumes stable agent nodes) and Source B assumes entities are **constituted through interaction** (e.g., Baumer et al.'s algorithmic subjectivities), the commitments conflict.
   - If Source A defines agency as a **property of entities** and Source B defines agency as a **relation**, the commitments conflict.
   - If Source A requires **intentionality** as a condition on agency and Source B dissolves intentionality into **situated practice**, the commitments conflict.

3. **For each detected conflict, check whether the paper:**
   - **(a) Acknowledges the tension.** Does the paper explicitly name the contradiction? (E.g., "This view poses a challenge for any fixed-schema modeling approach, including i\*...")
   - **(b) Resolves the tension.** Does the paper offer a principled reconciliation? (E.g., "The response is to treat i\* models as provisional snapshots...")
   - **(c) Explains why it does not apply in this context.** Does the paper argue that the conflict does not bite for the specific use being made? (E.g., "We use Source A only for X, not for the Y that conflicts with Source B.")

4. **If none of (a), (b), or (c) is done, flag as BLOCKER** ("unacknowledged theoretical contradiction"). This is the highest-severity finding this check produces, because it undermines the paper's intellectual integrity in the eyes of a theoretically attentive reviewer.

5. **If (a) is done but neither (b) nor (c):** Flag as **MAJOR** ("tension named but unresolved"). The paper has acknowledged the problem but left it open; whether this is acceptable depends on the paper's stage and type.

**Output format:**

```
### Check 4 — Contradiction Audit
- Co-invoked source pairs examined: [list]
- Contradictions detected:
  - [Source A] × [Source B]: [nature of conflict]
    - Acknowledged: [yes at §X / no]
    - Resolved or scoped: [yes at §X / no]
    - Verdict: [PASS / BLOCKER / MAJOR]
  - ...
- No contradictions detected: [if applicable]
```

**Why this is the highest-leverage check in the safeguard layer.** The Baumer/i\* contradiction on INF3001 was the defining BLOCKER of that review. The package's existing rules (MASTER §B.4, checklist Part 4 §11) point in this direction but are not specific enough to prescribe "check whether the paper's two theoretical commitments are compatible." This check makes that prescription explicit.

---

## Check 5 — Edit Traceability

**Trigger:** Run before any edit is applied (not after).

**Procedure:**

1. **For every proposed edit in the consolidated findings report**, verify that it cites:
   - **(a) The rule** that authorizes the edit, in `<file>#<section>` format (e.g. `MASTER §E.2`, `playbook §2.3`, `checklist Part 1 §1`).
   - **(b) The severity** of the finding (`[BLOCKER]`, `[MAJOR]`, `[MINOR]`).
   - **(c) The proposed replacement text** (exact, not a paraphrase of what should change).

2. **If an edit cannot cite a rule:** The edit is a **judgment call**, not a rule-grounded fix. It must be:
   - Separated from rule-grounded edits in the report.
   - Presented to the author with the label "judgment call — not authorized by a package rule."
   - Not applied without explicit author approval, even if the reviewer believes it is correct.

3. **If a rule is cited but the edit contradicts a project directive** (e.g., the edit would remove first-person hinges despite a directive saying "do not replace first person at argumentative hinges"), flag as **CONFLICT** and present both the rule and the directive to the author for resolution.

**Output format:**

```
### Check 5 — Edit Traceability
- Proposed edits in consolidated report: [n]
- Edits with rule citations: [n of n]
- Judgment calls (no rule): [n — listed separately below]
  - [edit description] → [reason it is a judgment call, not a rule]
- Directive conflicts: [0 / list with the conflicting rule and directive]
```

**Why this matters.** During the INF3001 review, the reviewer (Claude) introduced six em-dash violations because the edits were applied without first checking the style checklist. This check prevents that class of error: if the reviewer cannot cite the rule authorizing the edit, the edit is suspect. It also prevents taste-based "improvements" from being smuggled in as rule-grounded fixes.

---

## Check 6 — Humanness Voice Audit

**Trigger:** Run after any AI-assisted draft or revision pass. This includes any round where Claude (or another LLM) produced or substantially rewrote prose.

**Procedure:**

1. **Count positive voice markers** (from MASTER §A.4.2 positive markers and §I.2–I.3):

   | Marker | Register | How to check | Count method |
   |---|---|---|---|
   | Lived-in concrete detail | Both | Spot-check: does each major claim have a named case, specific role, plausible incident, or cited numerical detail within one paragraph? | Count of sections with at least one concrete anchor |
   | Asymmetric rhythm | Both | Read three consecutive paragraphs aloud. Do sentence lengths vary? Is there at least one short sentence (≤ 10 words) after a long one (≥ 25 words)? | Count of paragraph-pairs where the pattern appears |
   | Idiomatic verbs and images | Both | Scan for non-generic verbs and metaphorical images among the abstractions ("smuggle in," "tunable parameter," "provisional snapshot," "residual friction") | Count of idiomatic expressions |
   | First-person at hinges | Suchman | Check whether first person ("I want to argue/suggest") appears at the argumentative turning points — not sprinkled everywhere, not absent. See `suchman_writing_style.md` Move 2. | Count of hinge paragraphs using first person |
   | Earned callbacks | Suchman | Does a concept introduced in the opening frame reappear substantively in the middle (not only at the close)? | Count of concepts with mid-paper reuse |
   | Interlocutory opening | Suchman | Does each section open by naming a position being refined, rather than announcing what the section will do? See `suchman_writing_style.md` Move 1. | Count of sections with interlocutory opening / total |
   | Paired constructions with plain verdicts | Vidal | Are major claims stated as balanced two-part constructions with a clear, short verdict sentence following? | Count of verdict sentences following paired constructions |
   | Plans/situated action distinction deployed | Suchman (RE/design papers) | When Suchman (2007) is cited, verify that the plans-as-resources-not-programs distinction is invoked in the argument, not merely that Suchman is cited for situated action generally. | Present or absent (binary) |

2. **Count negative voice markers** (from MASTER §A.4.2 LLM-tic table — extend the deterministic check results):

   | Marker | Deterministic check result |
   |---|---|
   | "Not X but Y" stacking | From Step 0a |
   | Triadic list density | From Step 0a |
   | Trailing one-sentence add-ons | From Step 0a |
   | Hedged transitions at every paragraph break | From Step 0a |
   | Abstract-noun stacking | From Step 0a |
   | Glossary-dump openings | From Step 0a |
   | Semicolon-chained triads | From Step 0a |

3. **Compute a rough ratio.** positive markers ÷ (positive + negative). This is not a score — it is a signal:
   - **Ratio > 0.7:** Voice is human-sounding. No action needed.
   - **Ratio 0.4–0.7:** Voice is borderline. Read the three most-revised paragraphs aloud; propose specific fixes if they feel machine-generated.
   - **Ratio < 0.4:** Voice has degraded. Flag as MAJOR ("AI-assisted revision has flattened the voice"). Propose specific restorations calibrated to the declared register: for a **Suchman-interlocutor** paper, restore a first-person hinge, add an interlocutory section opening, or replace a synthesis close with a forward-opening reframing (see `suchman_writing_style.md` Moves 1, 2, 7); for a **Vidal-cartographer** paper, restore a plain-verdict sentence following a paired construction.

4. **Read one paragraph aloud.** Pick the paragraph that was most heavily revised in this round. Read it aloud (or simulate the experience by attending to rhythm, stress, and breath). If you stumble or lose the thread, flag the paragraph for sentence-variety or modification-load review.

**Output format:**

```
### Check 6 — Humanness Voice Audit
- Positive markers: [count per category]
  - Concrete detail: [n sections with anchors / total sections]
  - Asymmetric rhythm: [n paragraph-pairs / total]
  - Idiomatic expressions: [n]
  - First-person at hinges: [n hinges with 1st person / total hinges]
  - Earned callbacks: [n concepts with mid-paper reuse / total opening concepts]
- Negative markers: [counts from Step 0a deterministic pass]
- Rough ratio: [positive / (positive + negative)]
- Read-aloud paragraph: [location] → [stumbled: yes/no] → [action: none / flag]
- Verdict: [voice intact / borderline / degraded → severity]
```

**Why this matters.** MASTER §A.4.2 warns that AI-assisted drafts pass surface fluency checks while reading as machine output. The deterministic checks catch the mechanical tells (the negative markers), but they do not verify that the positive markers are present. On the INF3001 essay, the positive markers were strong (the loan-officer vignette, the Haslam callback, the "I am not embarrassed to say so" moment on the INF3006Y survey). On a weaker draft, the positive markers might be absent while the negative markers are clean — producing prose that is technically correct and humanly empty. This check closes that gap.

---

## Check 7 — Inter-Sentential Logical Connective Audit

**Trigger:** Run after Check 6 at `submission-bound` depth and at tier rungs T3 and T4. Consumes the `DETERMINISTIC_CHECKS.md §9a` pre-filter work queue produced during Step 0a.

**Rationale for a judgment layer.** The §9a pre-filter mechanizes detection of five connective classes: explicit application phrase, template invocation, attributional inversion (If-Then followed by application), following-X pivot, and descriptive-to-normative jump. Individually none of these is a violation; each is a candidate. Violations are found at the *co-presence* level — a paragraph carrying two or three of these markers simultaneously is smuggling a logical chain past the reader. The pre-filter's job is to surface candidates cheaply; this check judges whether the chain is warranted.

**Procedure:**

1. **Open the §9a pre-filter block** from the current round's `step_0a_deterministic.md`. Read the "Candidate paragraphs for Check 7" queue.
2. **For each candidate paragraph, read the full paragraph in context** (preceding and following paragraph included). Classify the connective chain:
   - **Attributional inversion chains.** If an `If-Then` conditional is followed within two sentences by `I apply X's template` or equivalent, verify that the conditional's scope is actually established by the cited author. If the conditional frames a claim the cited author does not make (a common smuggling pattern), flag as **MAJOR** (`unwarranted attributional inversion`).
   - **Template invocations.** For each `I apply X's template` or `X's analytic framework` phrase, verify that the template is *operationalized* — its criteria are enumerated, the material is mapped to the criteria, and the mapping is visible on the page. A template *asserted* but not *operationalized* flags as **MAJOR** (`template invoked, not applied`).
   - **Descriptive-to-normative jumps.** For each `..., so X should ...` or `..., so X must ...` within a single sentence, verify that an intervening argumentative step justifies the normative conclusion. A bare descriptive-to-normative collapse within one sentence flags as **BLOCKER** at `submission-bound` depth, **MAJOR** otherwise.
   - **Following-X pivots.** For each `Following X, ...` or `In X's terms, ...` pivot, decide whether the pivot is load-bearing (the subsequent argument depends on X's authority, and a specific passage should be cited) or ornamental (X is invoked for register but not for content). A load-bearing pivot without a specific passage citation flags as **MAJOR**; an ornamental pivot that reads as load-bearing flags as **MINOR**.
3. **Cross-reference with the manuscript's declared register.** In the Suchman register, a `Following X` pivot at the opening of a section is an interlocutory move and is warranted by register. In the Vidal cartographer register, a `I apply X's template` phrase is an explicit positioning move and is warranted. The register does not license the underlying chain — an unwarranted chain is still a violation — but it does calibrate the severity floor: a register-appropriate pivot with a missing citation is **MINOR**, not MAJOR.

**Output format:**

```
### Check 7 — Inter-Sentential Logical Connective Audit
- Candidates audited: <n> (from §9a pre-filter)
- Warranted chains: <n>
- Flagged:
  - <§X, line Y>: <connective type> — <severity> — <one-sentence reason>
  - ...
- Verdict: <all warranted / N flagged / contains BLOCKER>
```

**Why this matters.** The INF3001H "Whose Humanness Is Encoded?" draft passed five review rounds carrying a Khovanskaya paragraph with three co-present markers (an If-Then conditional, "I apply Khovanskaya's analytic template," a descriptive→normative `so…should` close). No individual rule in the package caught it because no existing rule treats co-presence as the signal. This check mechanizes co-presence detection (via the §9a pre-filter) and then applies judgment to the chain — the two-layer pattern the package already uses for reader cognitive load (§9b → Check 8) and for contradiction auditing (§6.4 reading → Check 4).

---

## Check 8 — Reader-Experience / Prose Architecture Audit

**Trigger:** Run at every tier rung where the Evaluator is active — **T2**, **T3**, and **T4** — and at `standard` and `submission-bound` depths. Operationalizes the six reader-accessibility criteria of the Ph.D. Research-root `CLAUDE.md §13.3` as a pass/fail audit with severity floors. Consumes the `DETERMINISTIC_CHECKS.md §9b` pre-filter work queue produced during Step 0a.

**Scope.** At T2, the audit runs on the section under review (`heading_path`) — Sub-checks A–F only, because Sub-check G is manuscript-scoped and cannot be evaluated on a section in isolation. At T3 and T4, the audit runs on the full manuscript and exercises all seven Sub-checks (A–G).

**Rationale for an Evaluator-owned surface.** The Ph.D.-root §13 constraint binds the Generator to fluency and low extraneous load across all P-stages (P0, P1, P2) and registers (Suchman, Vidal, Baird). Without a dedicated SAFEGUARD check, the constraint lives only as a drafting heuristic the Generator is expected to self-enforce — and the INF3001H Round 7 external readability review demonstrated that self-enforcement alone leaves measurable reader-ergonomics defects in a piece the harness has already marked READY. Check 8 closes that gap by giving the Evaluator a tier-active audit whose findings feed the T3 convergence gate.

**Two-scale architecture (2026-04-23 revision).** Sub-checks A–F audit accessibility at the **local scale** — paragraph cadence, sentence rhythm, first-use definition, section-transition signposting, jargon discipline within a paragraph, worked examples at a density spike. Sub-check G audits accessibility at the **cumulative scale** — does the manuscript, read in one sitting, impose a working-memory tax that is invisible to the local checks? The INF3006Y Co Author Ph4 round surfaced the gap: the manuscript passed all six local Sub-checks yet accumulated six framings, three positions, and two tensions across twenty pages with no consolidation summary before Sec. 6's accountability-gap argument depended on them all. Sub-check G, authored on 2026-04-23 and scoped to full-manuscript review only, closes that gap. The Ph.D.-root §13.3 criterion list (amended the same day from six to seven operational criteria) provides the rule citation; `READER_ACCESSIBILITY.md §13.1–§13.2` develops the local/cumulative distinction and explains why the two scales require distinct operational criteria.

**Procedure — seven sub-checks, each with an explicit severity floor.**

### A. Paragraph cadence (§13.3 criterion 1)

1. Enumerate every paragraph in scope. For each paragraph > 150 words, read the paragraph and identify internal turn-points (a transition, a worked example, a counter-claim, a thematic refocus). Paragraphs > 150 words must have at least one turn-point; paragraphs > 200 words must have at least two.
2. Flag each cadence-violating paragraph with its word count and its turn-point count.
3. **Severity floor:** **MINOR** on first detection; **MAJOR** if the same paragraph was flagged in a prior round; **BLOCKER** on the third consecutive round at the same severity.

### B. Sentence-length distribution (§13.3 criterion 2)

1. For each paragraph > 100 words, compute mean and standard deviation of sentence length.
2. Flag paragraphs where mean > 28 words **and** SD < 6 (monotone-dense).
3. **Severity floor:** **MINOR** per paragraph; **MAJOR** if three or more consecutive paragraphs are monotone-dense (sustained cadence failure).

### C. First-use definition (§13.3 criterion 3)

1. Enumerate load-bearing theoretical and domain constructs in scope. Starting list: the §9b pre-filter's "Definition-after-first-use" matches and the §9b "Stranded definition blocks" matches. Extend manually with constructs the Evaluator judges load-bearing but which the pre-filter missed (constructs introduced without `\emph{X}` or `By X, I mean` markers fall outside §9b's regex coverage).
2. For each load-bearing term, verify a first-use definition or worked illustration exists before the term does conceptual work in a subsequent paragraph.
3. **Severity floor:** **MAJOR** by default (the §13.3 rule binds even on field-standard terms: `affordance`, `operationalization`, `socio-technical`, `intentionality`, `delegation`). **BLOCKER** if the undefined term is load-bearing for the manuscript's central argument.

### D. Section-transition signposting (§13.3 criterion 4)

1. For every section and major subsection, check that the opening one-to-three sentences preamble tells the reader where they have arrived in the argument and what the section will contribute.
2. Flag sections that open with an unqualified thematic claim, a bare definition, or a block quote (no directional signal).
3. **Severity floor:** **MINOR** on first detection; **MAJOR** if two or more sections fail in a single manuscript.

### E. Jargon discipline per paragraph (§13.3 criterion 5)

1. For each paragraph, count new domain terms — terms not used in any prior paragraph of the manuscript.
2. Flag paragraphs introducing more than two new domain terms.
3. **Severity floor:** **MAJOR** (the §13.3 threshold is structural, not advisory: a paragraph carrying three or more new terms should be split).

### F. Worked examples at density spikes (§13.3 criterion 6)

1. Identify density-spike passages. Starting list: the §9b pre-filter's "Triadic enumerator (mechanized)" matches and the §9b "Rhetorical-question stacking" matches; extend by reading for tri-part decompositions, multi-criteria evaluations, and contested-claim clusters.
2. For each density spike, verify the surrounding prose turns to a worked example, vignette, or concrete instantiation before continuing in the abstract. The INF3001H loan-officer vignette is the template move.
3. **Severity floor:** **MINOR** at T2; **MAJOR** at T3 and T4.

### G. Cumulative cognitive load / consolidation anchors (§13.3 criterion 7)

**Scope.** Full manuscript only. Sub-check G does not run at T2 as a binding audit; at T2 the Evaluator records an advisory note that the check will run at T3. At T3 and T4, Sub-check G runs against the manuscript in one read.

**Procedure.**

0. **Consume the §9d pre-filter (added 2026-04-23).** If the current cycle's `reviews/deterministic_<cycle_id>.md` file carries a §9d "Cumulative cognitive load pre-filter" block, open it first. The pre-filter's G-candidate boundary list (boundaries where preceding-span word count exceeds the P-stage gap envelope AND consolidation-cue density is zero in both the pre-heading window and the opening paragraph of the next section) is the seed for step 1. The Evaluator may extend the seed with any additional boundaries it judges threshold-crossing that the pre-filter missed (the pre-filter is intentionally coarse and keys on cue absence, not construct-accumulation judgment). If the pre-filter has not run this cycle, proceed from step 1 directly.
1. **Enumerate structural boundaries.** A structural boundary is any of: (a) the closing paragraph of a major section followed by a new major section; (b) a labelled pivot within a section (for example a subsection that relocates the argument from description to stance, or from tension-mapping to accountability); (c) the opening of any section whose argument depends on constructs introduced in two or more prior sections without which the argument does not land. The Evaluator reads the manuscript's table of contents and the first sentence of each section to build the boundary inventory, starting from the §9d seed when available.
2. **Measure construct accumulation between boundaries.** For each span between two consecutive boundaries (or between the manuscript opening and the first boundary), count the distinct load-bearing constructs, positions, or tensions introduced. A construct is load-bearing if it (i) is named in the abstract, (ii) appears in the §13.3 first-use definition set audited by Sub-check C, or (iii) is cited as prior material by a later section. A position is load-bearing if the manuscript takes it seriously enough to treat it as a candidate to accept, reject, or reframe. A tension is load-bearing if the manuscript's closing argument depends on its unresolved status.
3. **Apply the construct-accumulation threshold.** A boundary crosses the threshold when the prior spans have introduced **three or more** load-bearing constructs (cumulative, not per-span), or when the next section's argument depends on **two or more** prior sections' material. A boundary that crosses the threshold must carry a consolidation anchor in the paragraph preceding it, in the paragraph opening the next section, or in a labelled transition between them. A consolidation anchor is a one-sentence restatement that (a) names the distinct constructs, positions, or tensions the reader has acquired up to that point and (b) signals how the next movement will build on them. Canonical form: "At this point in the paper, [the reader holds X, Y, Z]; the next movement [does W with them]." Any sentence performing both functions qualifies.
4. **Flag boundary misses.** For each threshold-crossing boundary lacking an anchor, record the boundary locator, the construct count at that point, and the absence.
5. **Word-count envelope check.** Manuscripts under roughly 3,000 words rarely cross the threshold and a CLEAN Sub-check G verdict is the expected default. Manuscripts beyond roughly 5,000 words with no consolidation anchors at any threshold-crossing boundary fall into the absence-of-anchors BLOCKER condition regardless of per-boundary construct counts, on the empirical finding that a sustained twenty-page argument without consolidation is the reliable indicator of cumulative-load failure the sub-check most directly targets.

**Severity floor.**

- **MINOR** — exactly one threshold-crossing boundary lacks an anchor and the manuscript word count is under 5,000.
- **MAJOR** — two or more threshold-crossing boundaries lack anchors, or a single missed boundary is located at the transition into the manuscript's closing argumentative move (where cumulative load is highest).
- **BLOCKER** — a manuscript beyond roughly 5,000 words contains no consolidation anchors at any threshold-crossing boundary, or a missed boundary directly precedes a section whose argument is specified in the abstract and depends on three or more prior-section constructs.

**Interaction with Sub-check D (Section-transition signposting).** Sub-checks D and G are orthogonal and additive, not alternatives. Sub-check D audits the *local* orientation at each section opening: does the opening tell the reader where they have arrived and what the section will contribute? Sub-check G audits the *cumulative* consolidation at threshold-crossing boundaries: does the manuscript name what the reader has acquired and how the next movement will use it? A strong section opening can satisfy D while still omitting the G anchor (the opening orients forward but does not consolidate backward); a strong consolidation can satisfy G while still failing D (the anchor names the accumulated material but does not preamble the section). When a Generator is applying a fix, D-targeting preambles and G-targeting anchors can co-locate in the same paragraph, but the two sentences should do distinct work.

**Advisory-until scoping.** Per `READER_ACCESSIBILITY.md §13.5`, Sub-check G carries an `advisory_until: next_manuscript_at_ph3` transitional flag on any section whose ledger row was advanced past Ph2 before 2026-04-23. Under the flag, Sub-check G findings are recorded with their severities and locators, but the Planner's §3.3.3 accessibility gate reads only the A–F aggregate for the TerminalSignoffRow decision; a Sub-check G BLOCKER on a flagged section does not fire `E-Ph3-ACCESSIBILITY-BLOCKER-AT-SIGNOFF`. The flag retires automatically when a manuscript whose Ph1 classification postdates 2026-04-23 enters Ph3, at which point Sub-check G joins A–F at full severity without further action.

**Stability sub-mode interaction (v0.8.0+).** Under the `run-phase-3-stability` sub-mode (byte-stable inheritance pass), Sub-check G runs **advisory-only** regardless of the `advisory_until` transitional flag state (D-G-3 decision, 2026-04-23). A G finding surfaced under stability mode is logged with `stability_advisory: true`, does not contribute to the §3.3.3 aggregate verdict, and does not force escalation to a full Ph3 pass; it is routed to Reflector Phase 2g for recurrence accounting. The authoritative statement of the rule — including the inheritance-by-hash rationale, the `advisory_until` interaction, and the escalation (trigger 30) semantics — lives at `skills/run-phase-3-stability/SKILL.md §3.2a`.

**Output format:**

```
### Check 8 — Reader-Experience / Prose Architecture Audit
- Scope: <section heading_path | full manuscript>
- A. Paragraph cadence: <n compliant> / <n paragraphs > 150 words>
  - Violations:
    - <§X, line Y>: word count <n>, turn-points <k>, severity <MINOR/MAJOR/BLOCKER>
- B. Sentence-length distribution: <n monotone-dense paragraphs>
  - Violations:
    - <§X, line Y>: mean=<m>, SD=<s>, severity <MINOR/MAJOR>
- C. First-use definitions: <n confirmed> / <n load-bearing terms>
  - Violations:
    - <term>: first occurrence <§X, line Y>; conceptual work begins <§Z, line W>; severity <MAJOR/BLOCKER>
- D. Section-transition signposting: <n sections with preamble> / <n sections>
  - Violations:
    - <section heading>: severity <MINOR/MAJOR>
- E. Jargon density: <n paragraphs compliant> / <n total>
  - Violations:
    - <§X, line Y>: new terms: <term1, term2, term3, ...>; severity MAJOR
- F. Worked examples at density spikes: <n compliant> / <n density spikes>
  - Violations:
    - <§X, line Y>: <density-spike type>; severity <MINOR/MAJOR>
- G. Consolidation anchors at structural boundaries: <n anchored> / <n threshold-crossing boundaries>  [manuscript-scope; T3/T4 only unless advisory_until flag active]
  - Violations:
    - <boundary locator, e.g. "end §3 → §4 opening">: construct accumulation <k>; anchor <present/absent>; severity <MINOR/MAJOR/BLOCKER>
  - Advisory-until flag: <active: next_manuscript_at_ph3 | retired>
- Aggregate verdict: <PASS / BORDERLINE / MAJOR / BLOCKER>
  - Rule: A single MAJOR = BORDERLINE. Two or more MAJORs in one section (or across the manuscript when Sub-check G contributes) = MAJOR aggregate. Any BLOCKER = BLOCKER aggregate. Any live BLOCKER at T3 blocks the `T3 → T3_converged` flip per `PHASE_PROTOCOL.md §3.3.3`, except that a Sub-check G BLOCKER under an active `advisory_until: next_manuscript_at_ph3` flag is recorded as advisory and does not block the flip.
```

**Severity aggregation and convergence contribution.** Check 8 feeds the T3 convergence gate directly. A live BLOCKER-grade Check 8 finding blocks the `T3 → T3_converged` flip regardless of line-diff stability; the Planner cannot close the `TerminalSignoffRow` while the finding is open (`PHASE_PROTOCOL.md §3.3.3`; `run-phase-3` SKILL.md §6). This is the architecture that makes T3 a genuine locus for reader-accessibility: a section can stop producing line diffs while still failing accessibility, and without this gate the convergence metric would issue `[CONVERGENCE-STABLE]` for a non-compliant section. Sub-checks A–F run per iteration at T3 at section scope; Sub-check G runs at T3 at full-manuscript scope, typically once per iteration round rather than per section. The accessibility-finding trajectory (BLOCKER count, MAJOR count, and the A–F vs. G scale of each) is logged in `convergence_log.md` alongside the line-diff metric, making the reader-experience dimension visible to the iteration record at both the local and the cumulative scale. A Sub-check G BLOCKER under an active `advisory_until: next_manuscript_at_ph3` flag is logged with its severity and locators but does not block the flip; the advisory is surfaced to the Reflector Phase 2g recurrence audit and to the eventual Ph4 close-out so the gap remains visible even though it is not enforced on the flagged manuscript.

**Why this matters.** Section §13 of the Ph.D. Research-root CLAUDE.md is a binding precedence-level-7 constraint applicable across all P-stages and all registers in the portfolio. The constraint operationalizes Sweller's cognitive-load distinction: extraneous load (the friction prose adds without carrying the argument) must be minimized; intrinsic load (the irreducible difficulty of the ideas) is preserved; germane load (the mental model the reader is building) is preserved *and must still be in place when the argument's closing move arrives*. Check 8 turns the constraint from a drafting heuristic into an Evaluator-owned surface with severity floors and a convergence contribution — the architecture that makes accessibility a property of the manuscript's convergence record rather than an afterthought at T4 copy-edit. The 2026-04-23 expansion from six to seven Sub-checks (the addition of Sub-check G on the cumulative scale) closes a gap the INF3006Y Co Author Ph4 test variant exposed: a manuscript can pass every local check and still impose a prohibitive working-memory tax on a reader who has been asked to carry six framings and three positions across twenty pages. See `skills/accessibility-overlay/SKILL.md` for the Step 0.2 overlay companion that pre-stages A–F findings for the Evaluator's judgment pass; a Sub-check G overlay extension is on the v0.7.5 roadmap and in the interim Sub-check G is evaluated directly by the Evaluator without a pre-filter stage.

---

## Integration with the package

### Where this file sits in the run order

| Step | File | Before or after |
|---|---|---|
| 8 | Consolidated findings report | **Before** this file |
| **8.5** | **`SAFEGUARD_LAYER.md` (this file)** | **After the report, before author approval** |
| 9 | Re-check (`DETERMINISTIC_CHECKS.md` re-run) | **After** edits are applied |

### How the output is used

- The output of all eight checks is appended to the consolidated findings report as **§10 (Safeguard Layer Results)**.
- Any new BLOCKERs or MAJORs found by the safeguard layer are added to the report's §2 (Blockers) or §3 (Majors) with the prefix `[SL-n]` (Safeguard Layer check number).
- The G.4 sign-off table includes a row for Step 8.5 listing all eight sub-results.
- Check 8 BLOCKERs feed the T3 convergence gate: the Planner refuses to flip `T3 → T3_converged` while any live Check 8 BLOCKER (Sub-checks A–F, or Sub-check G once its `advisory_until: next_manuscript_at_ph3` transitional flag has retired) exists, regardless of the line-diff convergence metric (`PHASE_PROTOCOL.md §3.3.3`). A Sub-check G BLOCKER under the active transitional flag is recorded as advisory and surfaced to Reflector Phase 2g but does not block the flip.

### Which checks run at which depth

| Check | Quick | Standard | Submission-bound |
|---|---|---|---|
| 1 — Regression Guard | **Yes** | **Yes** | **Yes** |
| 2 — Drift Detection | No | **Yes** | **Yes** |
| 3 — Abstract ↔ Body Consistency | No | **Yes** | **Yes** |
| 4 — Contradiction Audit | **Yes** | **Yes** | **Yes** |
| 5 — Edit Traceability | **Yes** | **Yes** | **Yes** |
| 6 — Humanness Voice Audit | No | **Yes** | **Yes** |
| 7 — Inter-Sentential Logical Connective Audit | No | No | **Yes** |
| 8 — Reader-Experience / Prose Architecture Audit | No | **Yes** | **Yes** |

Checks 1, 4, and 5 run at all depths because they catch the highest-severity problems (regression, contradiction, untraceable edits) with the lowest time cost. Checks 2, 3, 6, and 8 are deferred at `quick` depth because they require reading the full piece. Check 7 runs only at `submission-bound` because its judgment pass over the §9a pre-filter queue is expensive and its violations are rarely BLOCKER-level below submission.

### Which checks run at which tier rung (v0.7.2 Lifecycle-Stage Ladder)

| Check | T1 (dormant) | T2 | T3 | T4 |
|---|---|---|---|---|
| 1 — Regression Guard | — | **Yes** | **Yes** | **Yes** |
| 2 — Drift Detection | — | No | **Yes** | **Yes** |
| 3 — Abstract ↔ Body Consistency | — | No | **Yes** | **Yes** |
| 4 — Contradiction Audit | — | **Yes** | **Yes** | **Yes** |
| 5 — Edit Traceability | — | **Yes** | **Yes** | **Yes** |
| 6 — Humanness Voice Audit | — | No | **Yes** | **Yes** |
| 7 — Inter-Sentential Logical Connective Audit | — | No | **Yes** | **Yes** |
| 8 — Reader-Experience / Prose Architecture Audit | — | **Yes** (Sub-checks A–F, section-scoped, baseline) | **Yes** (Sub-checks A–G, manuscript-scoped, convergence-gating) | **Yes** (Sub-checks A–G, strict superset) |

**T2 adds Check 8 to the subset.** The v0.7.2 change from the prior (1, 4, 5) subset reflects the architectural shift that makes accessibility a T2-entry audit at the rung where prose is still plastic. At T2 the audit runs Sub-checks A–F only; Sub-check G is manuscript-scoped and cannot be evaluated on a section in isolation, so at T2 it emits only an advisory note that the check will run at T3. **T3 adds Checks 2, 3, 6, and 7 over the T2 subset, promotes Check 8's scope from section to full manuscript, and activates Sub-check G at full severity** (subject to the `advisory_until: next_manuscript_at_ph3` transitional flag per Sub-check G's procedure and `READER_ACCESSIBILITY.md §13.5`). Check 8 is convergence-gating at T3 rather than advisory. **T4 is the strict superset and is identical to the `submission-bound` depth column, with Sub-check G CLEAN required once the transitional flag has retired.**

---

## Maintenance

When a new integrity check is identified through a review application, add it to this file with:
- A number (Check 7, Check 8, etc.)
- A trigger condition
- A procedure
- An output format
- A depth-gating row

Update `REVIEW_ORCHESTRATION.md` §2 (run order) and §3.3 (depth table) to reflect the new check. Update the G.4 sign-off table in MASTER to include the new check. Follow the self-annealing pattern: the lesson that surfaced the need for the check should be recorded in the project's `lessons_learned.md` or in the package's `examples/` walkthrough that exposed the gap. A check that feeds a tier gate (as Check 8 feeds T3 convergence) must additionally cite the gate in `TIER_PROTOCOL.md` and the corresponding `run-tier-N/SKILL.md` termination step.

---

*This file is the integrity counterpart to `DETERMINISTIC_CHECKS.md`. The deterministic file catches mechanical tics before the review; this file catches structural failures after the review. Together, they bracket the judgment-based review with two layers of automated verification.*
