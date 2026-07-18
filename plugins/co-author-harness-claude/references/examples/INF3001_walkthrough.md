# Worked Walkthrough: Reviewing the INF3001 "Whose Humanness Is Encoded?" Essay

**Piece:** `D:\OneDrive - University of Toronto\Year 2026\INF3001H_Research\draft\inf3001_whose_humanness_encoded_v1.tex`
**Author:** Joseph Chung
**Venue:** INF3001 (PhD coursework, Faculty of Information, University of Toronto)
**Reviewed:** 2026-04-09 through 2026-04-13 (eight internal review rounds + external verification)
**Reviewer:** Claude (Opus 4.6), in conversation with the author

**Purpose of this walkthrough.** This file is a **reference example** of how the full Research and Academic Paper Writing Package is applied to a single piece. It is intentionally narrative: it shows the order of moves, what each step produced, what was surprising, and how the review composed into a final consolidated report. Future reviews can model their own walkthroughs on this one.

---

## Planning-Phase Context (Added 2026-04-13)

**Important note for future projects:** This walkthrough demonstrates a **review-first** workflow where the essay was drafted first, then reviewed intensively. The package has since been enhanced (as of 2026-04-13) to recommend a **planning-first** workflow using M1–M3 milestones before drafting.

### What Changed

Five logical gaps persisted through 8 internal review rounds on this essay and were caught by external review on the first pass:

1. **Disciplinary placement asserted, not exemplified** — "Information is the right home" was claimed but no existing research programs were named demonstrating the claimed integration.
2. **Logical tension unresolved** — "Actors are provisional yet we model them" created a consequence (what does the model capture?) the essay didn't resolve.
3. **Illustration doing evidential work** — The loan-officer case was presented without being flagged as constructed; empirical grounding was sparse.
4. **Alternative positions not addressed** — "Why Information, not STS or organizational studies?" was not differentiated in the outline.
5. **Framework transfer unjustified** — Haslam's interpersonal humanness framework applied to technical specs without explaining the transfer.

### Why It Matters

These gaps are **argumentative rigor** gaps — they fall outside the scope of the internal review pipeline, which checks **consistency and well-formedness**. External review catches argumentative rigor; internal review does not.

The package now includes **M1–M3 planning phase checks** that would have surfaced gaps 1–5 before drafting began. See `M1_M2_M3_ARGUMENTATIVE_RIGOR_CHECKLIST.md` and `AGENT_ORCHESTRATION.md §10` for the planning phase enhancements.

### How This Walkthrough Relates

This walkthrough shows the **M4–M5 review phase** (the old approach: draft first, review intensively, fix gaps discovered by review). The planning-phase checklist would have caught gaps 1–5 at M1–M3 *before* this review even started. For future projects, use the planning phase first; this review phase becomes refinement, not gap discovery.

---

---

## 1. Classification (per `REVIEW_ORCHESTRATION.md` §1)

| Input | Value | Reason |
|---|---|---|
| **Paper type** | `essay/positioning` | It is a PhD-course placement essay arguing that a project belongs in Information as a discipline. Not a theory paper; not empirical; not a survey. |
| **P-stage** | `P1` (with some P0 residue) | The piece characterizes a problem phenomenon using course readings and cross-talk; it does not yet commit to answerable RQs. |
| **Venue** | INF3001, course essay | iSchool audience. The MASTER's engineering-audience rules (§B.5) apply only softly. |
| **Review depth** | `standard` (became iterative as the author asked for revisions and then external-reviewer feedback) | Not submission-bound in the venue sense, but the author wanted a thorough pass. |

**Consequences of the classification.** Baird's 5-element theory-paper framework and 9-step empirical process do not fully apply; use only Baird §§2 (five areas) loosely and skip §4 (empirical steps). Sexton applies heavily (narrative shape, opening, cause-effect). Bacon applies universally. The project checklist Part 4 §§11–15 (IS theory paper items) apply in weakened form since this is an essay, not an IS theory submission.

---

## 2. Step 0a — Deterministic pre-flight (first pass, before any judgment review)

Ran the patterns in `DETERMINISTIC_CHECKS.md` against `inf3001_whose_humanness_encoded_v1.tex` (the original v1 file, before any edits).

### Counts (original v1)

- **em-dashes (`---`):** multiple pairs across the file, several in `§1` and `§3`.
- **absolutes:**
  - `must`: 2 hits (one in §1 "requirements practice must account," one in §5 "Evaluation must also extend")
  - `cannot`: 2 hits (§2 "requirements cannot be neutral"; §2 "The disciplinary question cannot be settled")
  - `comprehensiv*`: 0
  - `anticipat*`: 0
- **"not X but Y" stacking:** low, under threshold.
- **there is / there are / there remain:** 0.
- **reveals / exposes / proves:** 1 hit (§5 "demonstrates its force" — acceptable usage, not overclaiming).
- **glossary-dump opening:** no; the Haslam definition block is one paragraph, not 4+ italicized stacks.
- **trailing one-sentence add-ons:** not flagged.
- **hedged transitions at every paragraph break:** density is moderate, not abusive.

### Verdict from Step 0a
- **MAJORs from this pass:** 4 (two `must`, two `cannot` — per §2 of `DETERMINISTIC_CHECKS.md`, each requires human judgment; all four turned out to be prescriptive/comparative, so MAJOR).
- **MINORs from this pass:** em-dash density, flagged for the polish pass.
- **BLOCKERs from this pass:** 0.

Proceed to judgment-based review.

---

## 3. Steps 0b–2 — MASTER skim + playbook review

After skimming MASTER Parts A–B and G.1 to establish principles, the main findings from **Step 2** (`research_paper_writing_guidelines.md`) on the first read:

### Blockers identified in Step 2
1. **[BLOCKER] Defensive framing in the abstract** (playbook §2.4, §8; MASTER §B.2). The original abstract ended: *"The contribution is disciplinary and analytical; the scope is course-bounded and not a comparative empirical study."* This is a textbook "don't say what you don't do" violation that also opens with limitations.

2. **[BLOCKER] Unresolved theoretical contradiction** (playbook §3.1, §3.5; MASTER §B.4). The essay cites Baumer et al. (2024) on "algorithmic subjectivities" to argue that stakeholders are "provisional stabilizations rather than fixed referents" — then proposes i\* modeling, which fundamentally assumes stable agent nodes. The contradiction was nowhere acknowledged. A theoretically attentive reader would find the essay incoherent.

3. **[BLOCKER] Title promise not paid off** (Sexton §6; MASTER §D.1–D.2). Title asks "Whose Humanness Is Encoded?" The preamble defines Haslam's two senses (human uniqueness / human nature). The loan-officer vignette runs through the essay as a load-bearing example. **But the two senses are never mapped onto the loan-officer case**. The apparatus is built and not used.

### Majors identified in Step 2
4. **[MAJOR] Analytical apparatus cited but not operationalized** (playbook §3.6; MASTER §B.4 terminology row). Sluss & Ashforth (2007) is cited for "person-based, role-based, and relational" identity dimensions — but the dimensions vanish after the citation. Same pattern as the Haslam issue: named, not deployed.

5. **[MAJOR] i\* framework asserted, never demonstrated** (playbook §4.3; MASTER §B.4 row on notation-as-vehicle). The essay says "I map these dimensions to i\* constructs (agents, roles, dependencies)" without ever showing a single construct mapping on the running loan-officer example.

6. **[MAJOR] Deficit framing of other disciplines** (playbook §2.1, §2.3; MASTER §B.1). "Computer science … often under-specifies institutional power"; "Philosophy … less often specifies implementable governance mechanisms"; "Literary and cultural analysis … usually outside its scope." All three are soft versions of the "cannot" trap. Lesson A1 in `CAiSE_Rev01/research_notes/review/lessons_caise_revision.md` is exactly this rule.

7. **[MAJOR] "Agentic AI" used uncritically** (playbook §3.5; MASTER §G.3). The term is defined but the paper does not mark it as a contested framing whose referent changes rapidly.

### Minors identified in Step 2
8. **[MINOR] §2 "recurring structural pattern"** claim rests on three course readings. "Keeps appearing" is too strong for the evidence density; soften phrasing.
9. **[MINOR] The four governance checks in §5** (visible contestation, exception-as-signal, situated-judgment preservation, category-redefinition authority) appear *ex nihilo* — not grounded in the loan-officer case even though the loan-officer case could ground all four.

---

## 4. Step 3 — Baird (weakened, not primary)

Because this is an essay and not an IS theory paper, Baird's 5-element model is relaxed. Main finding from Step 3:

- **[MAJOR] Audience (Baird §1.1: target subcommunity).** The essay addresses "Information" as the discipline for the project but does not name the *subcommunity* within Information it is speaking to (HCI? STS? critical data studies? information policy?). Baird would flag this. In an essay this is MAJOR, not BLOCKER, because the venue (INF3001) is more forgiving than a journal.

Baird §4 (nine-step empirical process), §5 (tips/rookie mistakes for results tables) are N/A.

---

## 5. Step 4 — Bacon (sentence craft)

Walked the Bacon §10 checklist. Findings:

- **[MINOR] Sentence length distribution.** Mostly medium, occasional long (§3 opening sentence is ~55 words; §1 loan-officer paragraph contains a 60-word sentence). Not a blocker.
- **[MINOR] Subject-verb focus.** Strong: the loan officer is the grammatical subject through the vignette, which is exactly Bacon §3.2's advice (populated prose; human subjects pair with varied verbs).
- **[MINOR] Parallelism.** One place in §3 where a triadic list could be broken for rhythm, but not an LLM-tic density issue.
- **[MAJOR via MASTER §I.2] "Contradiction rather than dissolve"** — the essay gestures at contradiction (Baumer vs. modeling) but does not honor it. This is the Vidal move the essay needed and was missing. (Added during the revision pass as explicit acknowledgment of the tension, reframing i\* as "provisional snapshots.")

---

## 6. Step 5 — Sexton (narrative craft)

- **[CONFIRMED STRONG] Opening with impact.** §1 moves quickly to the loan-officer vignette rather than offering pages of background. Good Sexton §1 move.
- **[CONFIRMED STRONG] Show-then-tell.** The vignette is concrete before the abstract claims follow. Good §2.
- **[BLOCKER, already counted] Cause and effect / earned climax.** Sexton §4 says design choices should follow from preceding analysis. The i\* proposal drops in without being earned. Fixed in revision by adding an explicit construct sketch in §3.
- **[STRONG] Title and opening.** Informative title; scene-based opening; roadmap at end of §1. Good.

---

## 7. Step 6 — Package CLAUDE.md (precedence check)

No venue conflicts. No advisor instructions that override package rules. Note: CAiSE lessons learned (`lessons_caise_revision.md`) apply as a project-specific supplement to CAiSE_Rev01 but not to INF3001H_Research — however, since the author treats them as a cross-venue rule set, they *do* apply here by the author's explicit instruction in `D:\OneDrive - University of Toronto\Year 2026\CLAUDE.md`.

---

## 8. Step 7 — `project_writing_style_checklist.md` (integrated pass)

Walking the stage-tagged checklist at P1:

- **[BLOCKER] Part 1 §1 Clear Central Need [P1]:** The piece does state characterization lenses (the course-readings pattern, the disciplinary critique, the loan-officer illustration) but the lenses are not named as lenses. PASS with a note.
- **[BLOCKER] Part 1 §1 Forward Drive [P0/P1]:** Problem → characterization → refined problem statement is present but the forward handoff (§1 candidate q-items) is weak. The closing rhetorical question serves as the handoff move but does not use the "candidate qxxx" vocabulary. ACCEPTABLE for an essay.
- **[MAJOR] Part 1 §1 Hidden-Assumptions Audit [P0/P1]:** The term "agentic" is not held at arm's length. **Flagged.**
- **[BLOCKER] Part 1 §3 Earned Solutions:** The i\* proposal is not earned by the preceding analysis. **Flagged.**
- **[MAJOR] Part 4 §11 Theoretical Tension:** Assumption challenging is implicit (Baumer's claim that subjects are provisional challenges the fixed-schema modeling stance) but never made explicit. **Flagged.**
- **[BLOCKER] Part 4 §15 No Surprise Constructs:** The four governance checks in §5 are surprise constructs. **Flagged.**
- **[BLOCKER] Part 4 §15 Construct Provenance:** Sluss & Ashforth dimensions are named once and vanish; i\* constructs are named but not deployed. Terms are cited but do not have a "home" in the analytical work. **Flagged.**

The integrated checklist at Step 7 catches issues the earlier steps also caught (Gap G in the package review) and adds the **stage-specific anti-pattern** flag for "agentic."

---

## 9. Step 8 — Consolidated Findings Report (first cycle)

### Summary

The essay does several things well: the Haslam humanness framing, the recursive loan-officer vignette, and the scope self-awareness are all strong. Three BLOCKERs prevent the essay from being ready: a defensive abstract, an unacknowledged Baumer / i\* contradiction, and a title promise that is not paid off because the Haslam two-sense taxonomy is built and never applied. Four MAJORs concern unused analytical apparatus (Sluss & Ashforth, i\*), deficit framing of other disciplines, and uncritical use of "agentic." Polish items are minor.

### Blockers

1. Abstract reframe (defensive → positive).
2. Operationalize Haslam's two senses on the loan officer (pay off the title).
3. Acknowledge the Baumer / i\* contradiction and reframe i\* as "provisional snapshot" modeling.
4. Produce an i\* construct sketch on the loan-officer case (even a prose version).
5. Operationalize Sluss & Ashforth's three dimensions on the loan officer.
6. Ground the four governance checks in specific loan-officer moments (no more surprise constructs).

### Majors

7. Replace deficit framing of CS / philosophy / literary analysis with "oriented toward X rather than Y" construction.
8. Add critical distance on "agentic AI."
9. Reframe §5 limitations paragraph from defensive to positive.

### Minors

10. Soften "recurring structural pattern" in §2 to "appears with notable consistency."
11. Em-dash cleanup during the polish pass.
12. Four absolute-language swaps (two `must`, two `cannot`).

### Deferred / N/A

- Baird §4 empirical 9-step process (N/A — not empirical).
- Part 4 §11 Resolution / Guidelines (deferred — this is P1, not P2).

### Conflicts

- The author's explicit request to apply CAiSE lessons to non-CAiSE work overrides the project-specific scoping of `lessons_caise_revision.md`. Noted; followed.

---

## 10. Revision round 1 — nine edits

Applied all nine blocker and major fixes (details in the conversation log and in the final v1 of the file). Each edit was tied to the exact rule and file section above.

## 11. External verification (by a separate reviewer)

A different reviewer produced a verification report confirming all nine edits landed successfully, and raised three additional concerns:

- **§2 evidentiary thinness still underlies the softened claim** — flagged MINOR, no further action unless additional readings are introduced.
- **Governance checks ungrounded** — the previous revision had softened the language but not grounded the checks in the vignette. **Fixed in round 2.**
- **Sentence length in §1** — em-dash parenthetical + semicolon clause at ~70 words. Flagged MINOR; kept because the em-dash parenthetical is cleanly bounded.

## 12. Revision round 2 — governance-checks grounding

Added a single edit grounding each of the four governance checks in a concrete loan-officer moment (visible override button vs. no route to challenge weights; logged overrides vs. model review; cash-flow context vs. no field; no actor with authority to redefine categories). This also subtly reinforced the paper's broader argument that the absence of such an actor *is* the governance failure the paper is diagnosing.

## 13. Master-guidelines reconciliation pass

The author then asked for a pass against the `project_writing_style_checklist.md` em-dash rule. Six em-dashes from my revisions had been introduced. The linter had already cleaned five; the remaining two from the original author's prose were cleaned by me (one converted to commas + semicolon, one to a semicolon). Four absolute-language violations (two `must`, two `cannot`) from the original prose were then fixed.

## 14. Final state

After revision rounds 1, 2, and the guidelines reconciliation pass:

- Nine BLOCKERs and MAJORs addressed.
- Governance checks grounded.
- Em-dashes zero.
- Absolute-language violations zero.
- Title promise paid off.
- Baumer/i\* tension explicitly acknowledged and reframed.
- Analytical apparatus (Haslam, Sluss & Ashforth, i\*) all deployed on the loan-officer case.

The piece is now consistent with the package's rules at every checked point. Further improvements are possible but would be author-voice edits, not guideline violations.

---

## 15. Lessons extracted from this walkthrough (back into the package)

The experience of running this review exposed several gaps that were then closed in the package itself:

1. **I did the initial revisions without checking the style checklist first and introduced six em-dash violations.** → Added the explicit "Workflow expectation" to `D:\OneDrive - University of Toronto\Year 2026\CLAUDE.md` and `D:\OneDrive - University of Toronto\Research\CLAUDE.md` requiring a pre-read of the master guidelines on every revision task, however small.

2. **`CLAUDE.md` in the package was legacy content that violated its own rules.** → Replaced with a package-invocation file (this package's `CLAUDE.md`).

3. **No orchestration file told Claude how to run the seven-step pass.** → Created `REVIEW_ORCHESTRATION.md`.

4. **Deterministic counts were buried across multiple files.** → Consolidated into `DETERMINISTIC_CHECKS.md`.

5. **Severity was flat — every rule presented at the same weight.** → Added BLOCKER/MAJOR/MINOR tagging to `project_writing_style_checklist.md` Parts 1 and 4, and added MASTER §G.0.

6. **The essay needed a Vidal-style move (name the contradiction, don't dissolve it) and the package did not yet name it.** → Added Vidal (2022) as a third voice reference in MASTER Parts I and J alongside Braverman and Suchman.

7. **Parts I and J were not cross-referenced from Bacon / Part F, so a reviewer doing voice work read them in isolation.** → Added cross-references in MASTER Parts I and J to Bacon and Part F, and added `DETERMINISTIC_CHECKS.md` §4 as the mechanical counterpart to the humanness pass.

Each of these was a package-level improvement that came out of this single walkthrough. Future walkthroughs should be saved with the same "Lessons extracted" section so the package self-anneals as it is used.

---

*This walkthrough is saved as `examples/INF3001_walkthrough.md` so future reviews can see the package in action. The original INF3001 draft remains at `D:\OneDrive - University of Toronto\Year 2026\INF3001H_Research\draft\inf3001_whose_humanness_encoded_v1.tex`.*
