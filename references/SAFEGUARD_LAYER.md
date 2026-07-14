# SAFEGUARD LAYER — Post-Review Integrity Checks

**Purpose.** This file prescribes eight structured checks that run **after** the consolidated findings report is drafted (Step 8) but **before** the author approves edits. It is Step 8.5 in `REVIEW_ORCHESTRATION.md`. Its job is to catch problems the seven-step review does not prescribe: regression from edits, drift between rounds, abstract-body inconsistency, unacknowledged theoretical contradictions, untraceable edits, voice degradation from AI-assisted revision, unwarranted inter-sentential logical connectives, and reader-experience / prose-architecture failure.

**When to run.** Always, at every phase at which the Evaluator engages, per the Lifecycle-Phase Ladder: Evaluator dormant at **Ph1**; at **Ph2** run checks 1, 4, 5, and **8** (accessibility baseline); at **Ph3** and **Ph4** run all eight. The full routing table is '### Which checks run at which phase rung' below. See `agents/evaluator.md §Step 8.5` for phase-conditioned dispatch. *(The v0.4.x review-depth vocabulary — `quick` / `standard` / `submission-bound` — is retired; Check 7's pre-filter coupling now binds to Ph4.)*

**Relationship to other package files.**
- `DETERMINISTIC_CHECKS.md` catches mechanical tics **before** the judgment review.
- This file catches integrity failures **after** the judgment review and **after** edits are proposed or applied.
- `REVIEW_ORCHESTRATION.md` §7 (consolidated report) is the input; this file's output is appended as §10 of that report.

**Provenance.** Checks 1–8 were developed through the INF3001/INF3006Y review applications and later package revisions. Historical portfolio rules motivated the work but are non-operational. Current authority is package-local: `READER_ACCESSIBILITY.md`, the resolved profile, and this safeguard procedure.

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

0. **Establish the author's idiolect baseline (C-7).** *Before* counting any register marker, sample the author's own signature so that drift is scored against the author, not only against a borrowed exemplar. Source the baseline in priority order: (a) prior accepted prose by this author/project — a **confident** baseline; (b) failing that, the least-revised passages of the current draft — a **provisional** baseline. Record the baseline's sentence-length distribution (mean and spread, not a maximum — Moran: "average sentence length, not some arbitrary maximum, is what counts"), repetition habits, point of view, contraction use, and any characteristic device or metaphor. See `voice_preservation_guidelines.md` §§2,5. This baseline reclasses the markers below: a pattern that matches the baseline, is not a comprehension defect, and is plausibly intentional is **idiolect**, reported as a strength, not a negative marker. **Two guards:** (i) a *confident* baseline gives full force (idiolect-flattening is [MAJOR], matching craft flags fully suppressed); a *provisional* baseline makes every C-7 claim [MINOR]/ADVISORY and craft flags are **noted, not suppressed** ("possible idiolect — baseline provisional; confirm with author"). (ii) Recurrence alone does not protect a feature — a recurring mechanical error or surviving LLM tic is a defect, not idiolect, and is still flagged.

1. **Count positive voice markers** (from MASTER §A.4.2 positive markers and §I.2–I.3):

   | Marker | Register | How to check | Count method |
   |---|---|---|---|
   | Lived-in concrete detail | Both | Spot-check: does each major claim have a named case, specific role, plausible incident, or cited numerical detail within one paragraph? | Count of sections with at least one concrete anchor |
   | Asymmetric rhythm | Both | Apply the profile-routed `thresholds.rhythm` procedure and then adjudicate rhetorical function. | Candidate pairs plus Evaluator verdict |
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

   **C-7 distinction (binding when C-7 is applicable).** A low ratio alone does not establish a C-7 defect. Decide *which* baseline the prose drifted from: drift away from the **author's own idiolect baseline** (Step 0) is a C-7 regression — flag `[MAJOR — C-7: idiolect flattened]` and restore the author's own signature, not the exemplar's; drift away only from the **borrowed register exemplar** while the author's baseline is intact is often acceptable and is at most a C-1 contest the author may dispute — do **not** "restore" by overwriting the author's voice with the exemplar's. If a style rewrite this round stripped an identity-layer feature (sentence-length signature, repetition tolerance, point of view, cadence, humor, evaluative stance, characteristic metaphor) without citing a correctness, clutter, or C-5 warrant, flag it as a C-7 violation regardless of the ratio.

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

**Trigger:** Run after Check 6 at submission-bound depth and the corresponding active lifecycle phases. Consumes the `DETERMINISTIC_CHECKS.md §9a` candidate queue.

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

**Trigger:** Run at each active Evaluator phase and configured review depth. The package-local resolved reader-accessibility profile owns Check 8 scope, severity, transitions, and aggregation; deterministic probes nominate evidence only.

**Scope.** Resolve each check's phase and passage/manuscript scope from `sub_checks` and `register_scope` in the active profile. Do not reconstruct legacy tier subsets here.

**Rationale for an Evaluator-owned surface.** Package policy requires fluency and low extraneous load across stages and registers. Check 8 gives that policy an evidence-bearing Evaluator surface.

**Three-scale architecture.** A–F audit local accessibility, G cumulative consolidation, and H register construction. The resolved profile defines their current scopes and dispositions; historical rollout counts are provenance only.

**Procedure — eight sub-checks, each with an explicit severity floor.**

### A. Paragraph cadence (§13.3 criterion 1)

1. Enumerate every paragraph in scope and apply `thresholds.cadence`. Candidate cues receive credit only after functional confirmation; this procedure does not restate the numeric bands.
2. Flag each cadence-violating paragraph with its word count and its turn-point count.
3. **Severity:** derive from `thresholds.cadence` and the current paragraph evidence. Prior observations affect workflow persistence and recurrence reporting only.

### B. Sentence-length distribution (§13.3 criterion 2)

1. Compute the sentence-distribution evidence required by `thresholds.rhythm`.
2. Nominate monotone-dense candidates under the resolved profile.
3. **Severity:** adjudicate the present text under the profile; recurrence creates workflow evidence only.

### C. First-use definition (§13.3 criterion 3)

1. Enumerate load-bearing theoretical and domain constructs in scope. Starting list: the §9b pre-filter's "Definition-after-first-use" matches and the §9b "Stranded definition blocks" matches. Extend manually with constructs the Evaluator judges load-bearing but which the pre-filter missed (constructs introduced without `\emph{X}` or `By X, I mean` markers fall outside §9b's regex coverage).
2. For each load-bearing term, verify a first-use definition or worked illustration exists before the term does conceptual work in a subsequent paragraph.
3. **Severity floor:** **MAJOR** by default (the §13.3 rule binds even on field-standard terms: `affordance`, `operationalization`, `socio-technical`, `intentionality`, `delegation`). **BLOCKER** if the undefined term is load-bearing for the manuscript's central argument.

### D. Section-transition signposting (§13.3 criterion 4)

1. For every section and major subsection, check that the opening span tells the reader where they have arrived in the argument and what the section will contribute.
2. Flag sections that open with an unqualified thematic claim, a bare definition, or a block quote (no directional signal).
3. **Severity:** derive from current textual evidence and `sub_checks.D`; repeated observations do not rewrite severity.

### E. Jargon discipline per paragraph (§13.3 criterion 5)

1. For each paragraph, count new domain terms — terms not used in any prior paragraph of the manuscript.
2. Apply `thresholds.jargon` to the current P-stage.
3. **Severity:** derive from the active profile's jargon contract.

### F. Worked examples at density spikes (§13.3 criterion 6)

1. Identify density-spike passages. Starting list: the §9b pre-filter's "Triadic enumerator (mechanized)" matches and the §9b "Rhetorical-question stacking" matches; extend by reading for tri-part decompositions, multi-criteria evaluations, and contested-claim clusters.
2. For each density spike, verify the surrounding prose turns to a worked example, vignette, or concrete instantiation before continuing in the abstract. The INF3001H loan-officer vignette is the template move.
3. **Severity:** derive from `sub_checks.F` for the current evidence and phase.

### G. Cumulative cognitive load / consolidation anchors (§13.3 criterion 7)

**Scope.** Resolve G scope and workflow effect from `sub_checks.G`, `transitions.G`, and the current dispatch envelope.

**Procedure.**

0. **Consume the §9d pre-filter (added 2026-04-23).** If the current cycle's `reviews/deterministic_<cycle_id>.md` file carries a §9d "Cumulative cognitive load pre-filter" block, open it first. The pre-filter's G-candidate boundary list (boundaries where preceding-span word count exceeds the P-stage gap envelope AND consolidation-cue density is zero in both the pre-heading window and the opening paragraph of the next section) is the seed for step 1. The Evaluator may extend the seed with any additional boundaries it judges threshold-crossing that the pre-filter missed (the pre-filter is intentionally coarse and keys on cue absence, not construct-accumulation judgment). If the pre-filter has not run this cycle, proceed from step 1 directly.
1. **Enumerate structural boundaries.** Use section endings, labelled argumentative pivots, and dependency-bearing openings under `thresholds.consolidation`. The Evaluator reads the manuscript geometry and dependency structure, starting from the §9d seed when available.
2. **Measure construct accumulation between boundaries.** For each span between two consecutive boundaries (or between the manuscript opening and the first boundary), count the distinct load-bearing constructs, positions, or tensions introduced. A construct is load-bearing if it (i) is named in the abstract, (ii) appears in the §13.3 first-use definition set audited by Sub-check C, or (iii) is cited as prior material by a later section. A position is load-bearing if the manuscript takes it seriously enough to treat it as a candidate to accept, reject, or reframe. A tension is load-bearing if the manuscript's closing argument depends on its unresolved status.
3. **Apply the profile threshold.** A qualifying boundary must carry a consolidation anchor that names accumulated material and signals how the next movement will use it.
4. **Flag boundary misses.** For each threshold-crossing boundary lacking an anchor, record the boundary locator, the construct count at that point, and the absence.
5. **Envelope check.** Apply the resolved profile's G envelope; this prose owns no numeric cutoff or severity rule.

**Severity.** Apply `sub_checks.G` and its referenced profile thresholds to the recorded boundary evidence.

**Interaction with Sub-check D (Section-transition signposting).** Sub-checks D and G are orthogonal and additive, not alternatives. Sub-check D audits the *local* orientation at each section opening: does the opening tell the reader where they have arrived and what the section will contribute? Sub-check G audits the *cumulative* consolidation at threshold-crossing boundaries: does the manuscript name what the reader has acquired and how the next movement will use it? A strong section opening can satisfy D while still omitting the G anchor (the opening orients forward but does not consolidate backward); a strong consolidation can satisfy G while still failing D (the anchor names the accumulated material but does not preamble the section). When a Generator is applying a fix, D-targeting preambles and G-targeting anchors can co-locate in the same paragraph, but the two sentences should do distinct work.

**Transition binding.** `transitions.G` defines the meaning. Live state is read only from `phase_state.json.milestone_framework.policy_bindings.reader_accessibility.transitions.G`; dates and classification prose are migration evidence, not gate inputs.

**Stability sub-mode interaction.** The stability pass reads `transitions.G` and its bound Planner event state. Byte stability is evidence, not a second transition or advisory authority.

### H. Register Appropriateness — Register-Flag (§13.3 criterion 8, added v0.10.1)

**Scope.** Load passage roles and audience-conditioned scope from `register_scope` and `sub_checks.H`; do not reconstruct the role set from prose.

**Signpost role split.** Nominate orienting and contribution clauses separately and apply `sub_checks.H.ph2_role_overrides`; this prose does not duplicate the override table.

**Procedure.**

1. **Resolve `register_class` from `directives.md`.** Default `technical` if the field is absent (back-compat-safe path). Record the resolved value in the output artefact as `register_class_resolved`.
2. **Identify passages in scope.** Apply the **functional removability test** and the resolved `register_scope`. If substituting plain-language glosses preserves propositional content, H evaluates the passage; otherwise routing follows the active register class and profile.
3. **Audit positive markers.** Apply the marker definitions and compliance frame under `thresholds.register`; project lexicon overrides resolve through the profile.
4. **Audit negative markers.** Apply the registered probes and lexicons from the resolved profile; prose does not restate their numeric thresholds.
5. **Apply the presence-of-positive-markers compliance frame.** Use `thresholds.register` for marker counts and present-text severity. A negative-clear pre-filter never implies CLEAN; the positive-marker audit always runs.
6. **Emit per-finding telemetry.** Each H finding may carry `false_positive_candidate` and `inherited_from_pre_h` as provenance. Neither field rewrites severity or transition state.

7. **Calibration aggregation.** `scripts/aggregate_h_calibration.py` materialises evidence for an H transition adjudication. The report never owns the counter or retirement state; the Planner records an approved transition event only in `phase_state.json.milestone_framework.policy_bindings.reader_accessibility.transitions.H`.

**Severity.** Apply `thresholds.register.severity_model` plus `sub_checks.H.ph2_role_overrides`. This prose owns no numeric floor, recurrence count, or passage fraction.

**Interaction with Sub-checks D, F, G (orthogonal-at-finding-level pattern).** D enforces section-opening structural presence; H enforces register quality within the orienting and contribution clauses. F locates density spikes; H audits the worked-example vignette body. G locates threshold-crossing structural boundaries; H audits the consolidation anchor sentence. The two-Sub-check pattern (structural-Sub-check + register-Sub-check) is deliberate — D/F/G can be CLEAN while H is MAJOR if the structurally-required passage is registered inappropriately, and vice versa. When a Generator is applying a fix, the structural Sub-check's `suggested_fix` and H's `suggested_fix` can co-locate in the same paragraph but the two sentences should do distinct work.

**Transition binding.** `transitions.H` defines meaning. Live state is the validated policy-binding Planner event projection; legacy reports own neither counters nor retirement.

**Stability sub-mode interaction.** Apply `runtime_modes.stability`. Persistence may reuse current-hash evidence, but does not rewrite severity or aggregate membership.

### Check-8-Adjacent — Verdict-Edge Discipline (VE; added v0.13.0)

**Scope and membership.** Sentence-scoped at all phase rungs, including technical passages. VE is an adjacent advisory, not a lettered Sub-check: Check 8 is exactly A–H. VE never contributes to the A–H aggregate, accessibility severity floor, TerminalSignoffRow gate, or trigger 28, before or after its observation transition. Its findings route only to Reflector Phase 2g recurrence. Machine contract: `adjacent_advisory_checks.VE` in `references/policies/reader_accessibility.v1.json`.

**Provenance.** Authored 2026-04-30 (v0.13.0) per `docs/superpowers/plans/2026-04-30-voice-and-h-lessons.md` cluster 3.2. Surfaced from the INF3006Y voice round 2 where the Fügener-finding diagnosis line shipped as "the endorsement dimension, far from being a stable attribute, is eroded by the very delegation patterns it is supposed to anchor" — three intensifiers stacked across a single clause that tipped the sentence from diagnostic into verdict register. Closes the gap diagnosed in §2 of the source memo: A–H measure prose-surface and structural quality, but none audit the modal-claim register at the sentence level.

**Procedure.**

1. **Resolve scope.** VE runs over every sentence in every in-scope passage (the same passage scope H operates over for its register-class-conditioned variant; the unioned set across A–H scopes for the manuscript-wide variant). Technical passages are in scope.
2. **Audit intensifier classes per sentence-clause.** Count tokens of three classes within each clause:
   - **Class (a) — emphatic determiners.** `the very X`, `the same X`, `precisely the X`, `exactly the X`, `the very same X`. Marker for emphatic foregrounding of a referent.
   - **Class (b) — deontic-implicit phrasings.** `supposed to X`, `meant to X`, `should X but doesn't`, `was designed to X`, `is intended to X`. Marker for an implied normative gap between a system's design intent and its observed behavior.
   - **Class (c) — verdict verbs.** `erodes`, `destroys`, `breaks down`, `is undermined by`, `collapses`, `fails`, `is corrupted by`, `is gutted by`. Marker for terminal/evaluative outcome assertion.
3. **Apply the intensifier-stack advisory.** Use `thresholds.verdict_edge` for token and class minima. VE remains non-aggregate regardless of the result.
4. **Emit advisory telemetry with softening suggestion.** Each VE finding carries (a) the offending sentence-clause as `evidence_text`, (b) the matched intensifier tokens with their classes, (c) a `suggested_softening` field constructed by the modal-distribution rule, and (d) `false_positive_candidate: true|false` (default `false`).

**Modal-distribution softening rule.** The default softening converts the verdict claim into a modal/equivocal claim while preserving the diagnostic content. The rule has three steps: (i) replace the class-(c) verdict verb with a modal-equivocal predicate (`is eroded by` → `may not remain stable under`; `destroys` → `is challenged by`; `is undermined by` → `is contested under`); (ii) drop or weaken the class-(a) emphatic determiner (`the very X` → `the X`; `precisely the X` → `the X`); (iii) preserve the class-(b) deontic-implicit phrasing if needed for the diagnostic content, or rephrase to recover the implicit-norm content without the deontic register. Example transformation: `is eroded by the very delegation patterns it is supposed to anchor` → `may not remain stable under the delegation patterns to which it is supposed to anchor accountability`. The "to which" rephrasing recovers the deontic content (the delegation-anchoring relationship) without the modal-claim escalation.

**Advisory priority.** VE records `notice`, `priority`, and `recurrence_state`, not Check 8 severity. Repeated or co-located findings may raise remediation priority, but cannot become an accessibility MAJOR/BLOCKER or alter the A–H aggregate.

**Interaction with Sub-check H.** H audits register tone at passage level; VE advises on modal-claim register at sentence-clause level. The findings remain separately evidenced, but only H can affect Check 8 severity or aggregation. Co-located fixes may be applied in one revision pass.

**Observation transition.** The transition meaning is `transitions.VE` in the profile. Its live counter/event belongs only to `phase_state.json.milestone_framework.policy_bindings.reader_accessibility.transitions.VE`. Retirement changes recurrence reporting maturity only; gate contribution remains `none`.

**Stability sub-mode interaction.** VE is always advisory and never contributes to the §3.3.3 aggregate verdict.

**Output format:**

```
### Check 8 — Reader-Experience / Prose Architecture Audit
- Scope: <section heading_path | full manuscript>
- A. Paragraph cadence (`thresholds.cadence`): <n compliant> / <n candidate paragraphs>
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
- G. Consolidation anchors at structural boundaries: <n anchored> / <n threshold-crossing boundaries>  [scope and workflow effect from profile + bound transition]
  - Violations:
    - <boundary locator, e.g. "end §3 → §4 opening">: construct accumulation <k>; anchor <present/absent>; severity <MINOR/MAJOR/BLOCKER>
  - Transition binding: <phase_state milestone_framework.policy_bindings.reader_accessibility.transitions.G>
- H. Register Appropriateness: <n compliant> / <n non-technical passages in scope>  [passage-scope under register_class:technical and mixed; manuscript-scope under register_class:non-technical]
  - register_class_resolved: <technical | mixed | non-technical>
  - Violations:
    - <passage role + heading_path, e.g. "signpost_§3 line 12-15">: positive markers <count>; negative markers <count>; severity <MINOR/MAJOR/BLOCKER>; false_positive_candidate <true/false>; inherited_from_pre_h <true/false>
  - Transition binding: <phase_state milestone_framework.policy_bindings.reader_accessibility.transitions.H>
- Aggregate verdict: <PASS / BORDERLINE / MAJOR / BLOCKER>
  - Rule: The A-H aggregate follows `aggregate` in the reader-accessibility profile. VE is excluded regardless of observation-transition state.

### Check-8-Adjacent output — Verdict-Edge Discipline (VE)
- Findings: <n sentence-clauses>
- <locator>: intensifier classes <a|b|c|combination>; tokens <list>; suggested_softening <text>; recurrence_state <new|repeated>
- Route: Reflector Phase 2g only (`adjacent_advisory_checks.VE`); no A-H aggregate or gate contribution.
```

**Severity aggregation and convergence contribution.** Check 8 feeds the Ph3 convergence gate through canonical JSON evidence. The Planner recomputes the exact A–H aggregate and applies workflow effects from validated policy-binding transition states. Prose metadata cannot change membership. VE remains separate with no gate contribution.

**Why this matters.** Package-local `READER_ACCESSIBILITY.md` operationalizes extraneous-load reduction while preserving intrinsic difficulty and supporting germane model-building load. Check 8 makes that constraint an Evaluator-owned, current-hash-bound convergence surface. A–F cover local prose, G cumulative consolidation, and H register construction; all are implemented in the overlay. Portfolio-root §13 and the earlier roadmap are provenance, not live runtime dependencies.

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
- Check 8 BLOCKERs feed the Ph3 convergence gate according to canonical recomputation and validated transition events (`PHASE_PROTOCOL.md §3.3.3`). VE never changes this gate.

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

### Which checks run at which phase rung (introduced v0.7.2 under the stage vocabulary; phase-named per the v0.7.4 rename)

| Check | Ph1 (dormant) | Ph2 | Ph3 | Ph4 |
|---|---|---|---|---|
| 1 — Regression Guard | — | **Yes** | **Yes** | **Yes** |
| 2 — Drift Detection | — | No | **Yes** | **Yes** |
| 3 — Abstract ↔ Body Consistency | — | No | **Yes** | **Yes** |
| 4 — Contradiction Audit | — | **Yes** | **Yes** | **Yes** |
| 5 — Edit Traceability | — | **Yes** | **Yes** | **Yes** |
| 6 — Humanness Voice Audit | — | No | **Yes** | **Yes** |
| 7 — Inter-Sentential Logical Connective Audit | — | No | **Yes** | **Yes** |
| 8 — Reader-Experience / Prose Architecture Audit | — | **Profile-routed** | **Profile-routed** | **Profile-routed** |

**Phase scope.** Resolve Ph2/Ph3/Ph4 applicability from `sub_checks.*.advisory_at`, `binds_at`, passage-role overrides, and validated G/H transition states. Check 8 becomes convergence-gating only through those machine contracts; historical rollout prose is not executable authority.

---

## Maintenance

When a new integrity check is identified through a review application, add it to this file with:
- A number (Check 7, Check 8, etc.)
- A trigger condition
- A procedure
- An output format
- A depth-gating row

Update `REVIEW_ORCHESTRATION.md` §2 (run order) and §3.3 (phase table) to reflect the new check. Update the G.4 sign-off table in MASTER to include the new check. Follow the self-annealing pattern: the lesson that surfaced the need for the check should be recorded in the project's `lessons_learned.md` or in the package's `examples/` walkthrough that exposed the gap. A check that feeds a phase gate (as Check 8 feeds Ph3 convergence) must additionally cite the gate in `PHASE_PROTOCOL.md` and the corresponding `skills/run-phase-N/SKILL.md` termination step.

---

*This file is the integrity counterpart to `DETERMINISTIC_CHECKS.md`. The deterministic file catches mechanical tics before the review; this file catches structural failures after the review. Together, they bracket the judgment-based review with two layers of automated verification.*
