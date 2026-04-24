# M1–M3 Argumentative Rigor Checklist

**Purpose.** This document operationalizes the second-order argumentative checks added to AGENT_ORCHESTRATION.md §10 (M1, M2, M3). It provides concrete prompts and decision trees for Planners and Generators to catch argumentative gaps *before* drafting, reducing the risk of rework at M4–M5.

**When to use.** Every project that makes disciplinary placements, theoretical transfers, or claims of methodological integration should run this checklist at M1, M2, and M3. It is not optional for "high-stakes" arguments (thesis placements, framework appropriations).

---

## M1 — Project Memo (Argumentative Framing)

### Check 1a: Disciplinary Placement Claims

**Question:** Does the memo claim "Problem X belongs in Discipline Y" or "Discipline Y is the right home for Topic Z"?

**If YES, proceed:**

1. **Name the integration.** What three or four things does the problem require?
   - Example: "Requirements reshape professional identity" requires (a) understanding how technical systems encode human attributes, (b) studying professional work in organizational context, (c) empirical or interpretive evidence that the mechanism is real.

2. **Name existing research programs that do ALL of these simultaneously.** Do not list papers that do one part. List research *programs* (teams, sustained bodies of work) where scholars habitually combine these elements.
   - Example (BAD): "Orlikowski studies materiality" — true but doesn't specify the integration. 
   - Example (GOOD): "Orlikowski's sociomaterial practices research combines organizational ethnography with technical artifact analysis to show how tools reshape work identities."

3. **Enumerate and record.** In the memo, add a section titled "Disciplinary Home: Existing Exemplars" that names 2–4 research programs (with authors/citations) and briefly notes what each exemplifies.

**If the memo cannot name existing programs, flag as M1 FINDING:**
- ► "Disciplinary placement claim lacks grounding in existing scholarship. Recommend: (1) Expand literature review in M2 to locate programs that perform this integration, OR (2) Reframe the placement as a contribution rather than an existing fact, and commit to demonstrating it through your own work."

---

### Check 1b: Theoretical Premises and Internal Tensions

**Question:** Does the memo introduce two or more theoretical premises that, when held together, create a logical consequence the memo doesn't resolve?

**If YES, list them:**

- Premise A: [state it]
- Premise B: [state it]
- Implied consequence: [what follows logically from A + B?]

**Examples:**
- A: "Actors in organizations are provisional, constantly shifting identities"
- B: "We model actors using i* framework"
- Consequence: "If actors are that fluid, what does a static model capture? When does it become stale?"

**Action:** For each tension pair:

1. **Name the tension explicitly** in the memo (e.g., "Provisionality Tension: actors are fluid yet modeled").
2. **Note whether it's resolved or deferred:**
   - Resolved: "This is resolved by treating models as snapshots of current dependencies, not stable entities."
   - Deferred: "This tension will be resolved in §3 of the draft by distinguishing what models capture vs. what they don't claim to represent."

**If tension is unaddressed (not resolved, not deferred), flag as M1 FINDING:**
- ► "Unresolved logical tension between [Premise A] and [Premise B]. Recommend: (1) Resolve the tension conceptually before drafting (add to memo), OR (2) Explicitly mark it as a deferred question for future work (outside the scope of this paper)."

---

## M2 — Annotated References (Framework Transfer & Epistemological Clarity)

### Check 2a: Framework Origin and Transfer Justification

**Question:** For each borrowed theoretical framework (i*, Haslam, Suchman, GORE, etc.), can you answer these three questions?

**For each framework:**

1. **What domain was it developed for?**
   - Haslam: social psychology (interpersonal and intergroup perception)
   - i*: software engineering requirements modeling
   - Suchman: organizational ethnography + HCI
   - GORE: software engineering goal modeling

2. **Why does it apply to this problem?** (This is the transfer justification.)
   - BAD: "Haslam is useful for understanding humanness." (Restates domain, doesn't justify transfer.)
   - GOOD: "Haslam's framework models how traits of humanness (human uniqueness vs. human nature) are attributed in social contexts. The transfer here is that if software systems encode presuppositions about user humanness traits (e.g., 'users are economically rational' vs. 'users have discretionary judgment'), those presuppositions can strip away the same humanness traits Haslam identifies in social perception."

3. **What is the mechanism of transfer?** (Analogy? Direct application? Reframing?)
   - Analogy: "Just as humans attribute humanness in social perception, systems encode humanness attributes in design choices."
   - Direct application: "GORE's goal hierarchies directly model the decomposition of organizational objectives."
   - Reframing: "We reframe i*'s 'actor' from a requirements-modeling construct to a 'provisional instantiation of organizational role.'"

**Action:** For each framework in your annotated references, write a paragraph (to yourself, not for the paper) answering these three questions. If you cannot write clear answers to all three, flag for M2 review.

**M2 FINDING criterion:**
- ► "Framework [Name] has no documented transfer justification. Either: (1) Add a paragraph to the annotation explaining the transfer, OR (2) Defer to M3/M4 and note that the transfer justification must be explicit in the draft."

---

### Check 2b: Epistemological Clarity — Evidence vs. Illustration

**Question:** For each source, which of these three roles will it play?

1. **Empirical evidence** — primary research (study, experiment, dataset) that demonstrates a mechanism or phenomenon.
   - Example: "Seeber et al. (2020) studied algorithmic management in platform work and found that systems encode assumptions about worker competence."

2. **Illustrative example** — constructed scenario or secondary example that makes a concept concrete but is not itself the evidence.
   - Example: "The loan-officer case illustrates how credit-scoring systems presuppose certain professional identities."

3. **Conceptual framing** — theoretical lens (framework, definition, typology) that structures how you analyze the problem.
   - Example: "Haslam's humanness framework provides vocabulary for analyzing identity presuppositions."

**Action:** For each source in your annotated references, assign it one role and record it in the annotation. Example:

> **Seeber et al. 2020** (Evidence) — Empirical study showing that algorithmic management encodes assumptions about worker competence and autonomy. Primary grounding for the claim that "systems reshape professional identity."

> **Ahmad 2023, Habiba 2024** (Evidence — complementary) — Mapping studies showing identity-sensitive requirements are underdeveloped in RE literature, establishing the gap this work addresses.

> **Haslam et al. 2013** (Framing) — Two-sense humanness framework (human uniqueness vs. human nature). Provides vocabulary for analyzing which human traits are presupposed or stripped away by system designs.

> **Constructed loan-officer case** (Illustration) — Plausible professional scenario that makes concrete how requirements can reshape identity. Not itself evidence, but makes abstract mechanisms vivid. Will be paired with empirical grounding from platform work, clinical systems, policing studies.

**M2 FINDING criterion:**
- ► "One or more sources have unclear epistemological role. Clarify whether [Source] is providing evidence, framing, or illustration. If a claim will rest on illustration alone (no empirical backing), flag this for explicit labeling in the draft."

---

## M3 — Structured Outline (Argumentative Completeness)

### Check 3a: Alternative Positions and Differentiation

**Question:** For any claim that positions the argument relative to a discipline or alternative approach (e.g., "Why Information, not STS?" or "Why actor-oriented, not process-oriented?"), does the outline show where the paper differentiates from alternatives?

**For each such claim:**

1. **Name the alternative positions** the argument must differentiate from.
   - Example: Information is not the only discipline studying requirements and identity. Alternatives: STS, organizational studies, HCI.

2. **Specify where in the outline** the paper addresses each alternative.
   - Example: §4 "Information's Methodological Advantage" compares Information's three-part approach (requirements modeling + situated practice + interpretive scholarship) to what STS and organizational studies typically do.

3. **Verify the outline shows the differentiation**, not just assertion.
   - BAD outline: "§4 Information is the right home" (no differentiation shown).
   - GOOD outline: "§4 Information vs. alternatives — three methodological components: (a) requirements modeling (Engineering, not STS); (b) situated practice analysis (HCI, not organizational studies); (c) interpretive scholarship on what escapes formalization (Information Science unique contribution). Why Information? It routinely combines all three; alternatives combine 1–2."

**M3 FINDING criterion:**
- ► "Placement argument present but not differentiated from alternatives. The outline must show where the paper anticipates and addresses the objection 'Why not [Alternative]?' Add to §[X]: explicit comparison of methodological components across disciplines."

---

### Check 3b: Tension Resolution

**Question:** For each logical tension identified in M1, does the outline show how it will be resolved?

**For each tension:**

1. **State the tension** (reference M1 memo).
   - Example: "Provisionality Tension — actors are fluid yet modeled."

2. **Show where the outline addresses it.**
   - Resolved before drafting: "§2 'Modeling Provisional Actors' explains that models capture current dependencies, not static entities. Staleness occurs when [X]. Governance of updates is [Y]."
   - Deferred to draft: "§2 'Provisional Actors and Models' will resolve this by clarifying what the model captures and when it becomes invalid. Specific resolution strategy: TBD."
   - Deferred to future work: "This tension is acknowledged but outside scope; §5 Conclusion notes it for future work."

3. **Distinguish "deferred within this paper" from "deferred to future work."**
   - Within-paper deferred still means the paper resolves it (just in a later section).
   - Future work deferred means the paper acknowledges it but explicitly scopes it out.

**M3 FINDING criterion:**
- ► "Tension [Name] from M1 is not addressed in outline. Either: (1) Add a section to the outline that resolves it, OR (2) If it's out of scope, make that explicit in Conclusion; do not leave tensions unaddressed and unscoped."

---

### Check 3c: Illustration vs. Evidence Separation

**Question:** Where will the draft use illustrations or constructed examples to carry argumentative weight?

**For each illustration:**

1. **Identify it in the outline** (e.g., "§2 Loan-Officer Case Study").

2. **Flag it explicitly as "Illustrative Case" or "Constructed Scenario"** in the outline.

3. **Specify where empirical grounding will be added** — which studies or evidence will support the mechanism the case illustrates.
   - Example outline: "§2.3 Loan-Officer Case [Illustrative]. What makes this realistic? Grounded in empirical literature on: (a) algorithmic management in platform work (Seeber et al.), (b) clinical decision support (Herrmann & Pfeiffer), (c) predictive policing."

4. **Verify the outline does NOT claim the illustration is evidence.**
   - BAD: "§2 The Loan Officer — evidence that systems reshape identity."
   - GOOD: "§2 The Loan Officer [Illustrative scenario] — illustrates the mechanism. Empirical support from: [list studies]."

**M3 FINDING criterion:**
- ► "Illustration [Name] in outline is not explicitly flagged as such, or empirical grounding is not specified. Add to outline: (a) 'Illustrative case' label, (b) list of empirical studies that ground the mechanism."

---

## Checklist for Evaluator at M1, M2, M3

**When running M1 review, verify:**
- [ ] If the memo makes a disciplinary placement claim, exemplars are named.
- [ ] Logical tensions between premises are identified and marked as resolved or deferred.

**When running M2 review, verify:**
- [ ] Every borrowed framework has a documented transfer justification in the annotations.
- [ ] Every source has an assigned epistemological role (evidence, framing, or illustration).

**When running M3 review, verify:**
- [ ] For placement/differentiation claims, the outline shows comparison to alternatives.
- [ ] Every M1 tension appears in the outline with a resolution strategy (within-paper or scoped out).
- [ ] Illustrations are flagged as such and paired with empirical grounding.

---

## For Package Maintainers

**Lesson absorbed:** The root cause analysis of INF3001H (2026-04-13) identified five argumentative gaps that internal review missed because the package checked *consistency* and *well-formedness* but not *argumentative rigor*. This checklist operationalizes the five second-order requirements needed at M1–M3:

1. **Gap 1 prevention (M1):** Exemplar enumeration requirement.
2. **Gap 2 prevention (M1):** Tension identification and resolution tracking.
3. **Gap 3 prevention (M2):** Epistemological clarity (evidence vs. illustration).
4. **Gap 5 prevention (M2):** Framework transfer justification requirement.
5. **Gap 4 prevention (M3):** Alternative position comparison requirement.
6. **All gaps (M3):** Explicit outline mapping so M4 draft can follow the plan.

The argument is: if these checks pass at M1–M3, M4–M5 drafting and review will be execution against an explicit argumentative skeleton, not discovery of argumentative gaps.

**Future integration:** Consider promoting this checklist to M1–M3 Evaluator dispatch, so the Evaluator automatically runs it (or guides the Generator to run it) at each planning milestone.

---

*Created 2026-04-13 as part of root cause analysis integration. Operationalizes AGENT_ORCHESTRATION.md §10 enhancements.*
