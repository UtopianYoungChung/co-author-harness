# Project Writing Style Checklist: Reconciling Narrative and Syntax

This checklist synthesizes macro-level structural principles derived from Adam Sexton's fiction techniques adapted for academia, alongside micro-level syntactical principles drawn from Nora Bacon's *The Well-Crafted Sentence*.

Use this guide systematically during the revision phases of the project.

---

## Part 0: Stage of Deliverable (P0 / P1 / P2)

**Before applying any item below, identify the stage of the deliverable.** Items in this checklist are calibrated to different stages of the research lifecycle. Applying P2 items to a P0 paper will pull the draft into the wrong register and force premature commitment; applying P0 items to a P2 paper will look uncommitted and unfocused.

The three stages, defined here as the package's operational problem-setting convention:

- **P0 — Collected readings on the problem phenomenon.** Deliverable: bibliographic corpus + bullet points + tags (e.g. *#V0* = contains potential test case; *#V0a* = includes analysis/reasoning). Goal: assemble the materials from which a problem will eventually be characterized. Output artifact: bib list and notes.
- **P1 — Characterization of the problem phenomenon.** Deliverable: a synthesis, digest, or interpretation of the phenomenon, possibly organized around classification dimensions or a theoretical framework. Sectioned paragraphs, tables, charts. A hierarchical map of problems and existing solutions. Output artifact: *Motivation* chapter / problem-statement document.
- **P2 — Definition of research problems / questions / objectives.** Deliverable: the *specific technical problems* the research will address (e.g. "Given X, how to obtain Y"), specific enough to identify alternative technical approaches and tradeoffs. Research problems labeled as **q1, q11, q21…**; detailed sub-problems uncovered during downstream stages (S1, S2, S3). Output artifact: Research Objectives / Thesis Research Proposal.

> `GROUND_TRUTH.md` records the package-owned, non-verbatim interpretation and its limits. These definitions support package routing only; exact advisor-specific or EYgp conformance requires a lawfully supplied project-local source. The "P2 vocabulary" list below is a package review heuristic, not attributed source wording.

**How to use the stage tags below.** Items in Parts 1–4 are now tagged **[P0]**, **[P1]**, **[P2]**, or **[all]**. Items tagged for a stage *above* yours are **deferred, not skipped** — they apply at a later stage of the same project. Items tagged for a stage *below* yours should already be satisfied by earlier work.

**Severity tagging.** High-impact items in Parts 1 and 4 carry a severity tag for joint-review prioritization (see `REVIEW_ORCHESTRATION.md` §4):

- **[BLOCKER]** — Structural failure or integrity failure. Must fix before submission.
- **[MAJOR]** — Substantive weakness readers will notice; weakens credibility.
- **[MINOR]** — Polish level; default for untagged items in Parts 2 (meso) and 3 (micro).

When an item's severity depends on context (e.g. a missing construct definition is BLOCKER in a theory paper but MAJOR in an essay), the tag reflects the most common case and the reviewer adjusts in the findings report.

### Anti-patterns surfaced in P0/P1 work

- **Don't pose answer-demanding RQs in a P0 or P1 paper.** Numbered RQs in §1 will pull the draft into a P2 register and force premature theoretical commitment. Use a **problem statement with characterization lenses** (or "facets," or "tensions") instead. Reserve labeled *q1, q11, q21…* RQs for P2.
- **Don't load §1 with three RQs when the paper is collecting and characterizing.** The introduction of a P0/P1 paper should articulate the *problem phenomenon*, not promise *answers*.
- **Don't hide thin support behind a section heading framed as a question.** If the corpus cannot answer it, name the gap as the finding and hand it forward to later P1/P2 work.
- **Don't import P2 vocabulary ("research questions," "resolution," "answers") into a P0/P1 conclusion.** Use *refined problem statement*, *open questions*, *candidate qxxx items for later stages*.

---

## Part 1: Macro-Structure & The "Story" of the Paper (Sexton)

### 1. The Core "Need" and Forward Drive

- [ ] **[BLOCKER] Clear Central Need.**
  - **[P0]** Does the paper state the *problem phenomenon* clearly and concretely, with the bibliographic corpus that motivates it?
  - **[P1]** Does the paper state the *characterization lens(es)* (classification dimensions, tensions, facets) it will use to organize the phenomenon?
  - **[P2]** Does the paper state one or more research questions (q1, q11, q21…) concretely, with enough specificity to identify alternative technical approaches?
- [ ] **[BLOCKER] Forward Drive.**
  - **[P0/P1]** Are arguments structured as *Phenomenon → Characterization → **Refined problem statement + open questions handed forward***?
  - **[P2]** Are arguments structured as *Problem → Analysis → **RQ answers with tradeoffs against alternatives***?
- [ ] **[MAJOR] [all] Theme Through Structure:** Does the main contribution emerge organically through the evidence and argument, rather than just being declared in the introduction?
- [ ] **[MAJOR] [P0] Phenomenon Collection Completeness:** Is the bibliographic corpus broad enough that the emerging characterization is not an artifact of one school, journal, or author?
- [ ] **[MAJOR] [P0/P1] Hidden-Assumptions Audit:** Are loaded terms (e.g. *autonomous*, *agentic*, *delegation*) surfaced and held at arm's length *before* any of them are adopted into the paper's own vocabulary?
- [ ] **[MAJOR] [P1] Classification Scheme Honesty:** If the characterization uses a classification dimension or taxonomy, is the carving attributed to a source (or marked as the paper's own) and its limits noted?
- [ ] **[BLOCKER] [P0/P1] Forward-Pointing Handoff:** Does the conclusion explicitly hand candidate questions forward toward later P1/P2 work (e.g. as *q-α, q-β …* or "candidate qxxx items"), in a register that does not preempt P2 commitments?

### 2. Title and Opening Hooks

- [ ] **Informative Title:** Is the title specific and informative, clearly signaling the core topic rather than being overly generic?
- [ ] **Opening with Impact:** Does the opening paragraph use a concrete scenario, striking gap, or strong hook before diving into heavy background exposition?
- [ ] **Roadmapping:** Does the introduction conclude with a short structural roadmap to guide the reader through the paper’s development?

### 3. Planning, Proof, and Resolution

- [ ] **[MAJOR] Sufficient Middle Development:** Is the core of the paper (the theory, mapping, or examples) deeply developed, accounting for ~80% of the narrative focus?
- [ ] **[BLOCKER] Earned Solutions:** Do the design choices and theoretical integrations follow logically from the preceding analysis (i.e., cause and effect), avoiding sudden, unmotivated "fixes"?
- [ ] **[BLOCKER] Solid Climax.**
  - **[P0]** Does the conclusion deliver a **refined problem statement** and explicitly hand open questions forward to later stages?
  - **[P1]** Does the conclusion deliver a **characterization map** of the problem phenomenon and surface its internal tensions, without committing to resolutions?
  - **[P2]** Do the conclusions actually resolve the central RQs with explicit tradeoffs against alternative approaches?

---

## Part 2: Meso-Structure & Rhetorical Delivery (Sexton + Bacon)

### 4. Show, Then Tell

- [ ] **Ground Abstractions:** Are major abstract claims immediately preceded or followed by specific, concrete illustrations or case examples?
- [ ] **Avoid Unsupported Runs:** Are long sequences of abstract theory broken up by concrete applications ("For example, in the Santander case...")?

### 5. Logical Linkages

- [ ] **Visible Argument Chains:** Are logical connectors ("therefore", "because", "as a result") used to explicitly motivate the transitions between paragraphs and sub-sections?

---

## Part 3: Micro-Structure & Syntactical Polish (Bacon + Sexton)

### 6. Subject-Verb Focus (Bacon)

- [ ] **[PRIORITY; MAJOR when frame-changing] Concept Introduction:** Apply the **introduction-provenance test** and **derivation-continuity test** to every new analytical term, unit, category, or field-level generalization. Does the preceding prose explain why the concept is needed and name the operation connecting it to what came before? Reject a fluent definition that makes the reader ask “Where did that come from?”
- [ ] **Populate the Prose:** Are the grammatical subjects of your sentences aligned with the actual "characters" or actors of your narrative (whether human, AI, or institutional components)?
- [ ] **[MAJOR when claim-changing] Semantic-Predication Integrity:** For each definitional, modelling, or ontological sentence, does the predicate truthfully apply to its grammatical subject? Apply the **bearer test**, **contrast-set test**, **domain-collocation test**, adjacent-sentence transformation-continuity test, and **conceptual-debt test**; do not confuse a world-level entity with the model, representation, or ascription made of it. Distinguish local rhetorical personification from analytical predication, but allow no rhetorical exemption where a definition or inference depends on the wording. Remove an illustration whose misleading implication requires immediate repair; precision and clarification outrank vividness.
- [ ] **Active Voice Priority:** Are verbs primarily in the active voice using strong action verbs (e.g., "enables," "constrains," "demonstrates" instead of "looks at" or passive constructings)?
- [ ] **Short Subject Phrases:** Are the subjects of the sentences kept relatively short, allowing the reader to reach the main verb quickly?
- [ ] **Avoid Buried Subjects:** Have long, heavy introductory phrases been trimmed or reconstructed so the subject isn't hidden?

### 7. Balance, Coordination, and Parallelism (Bacon)

- [ ] **Parallel Structure:** When using lists, correlative conjunctions (e.g., "either/or", "not only/but also"), or coordinated clauses, are the grammatical structures perfectly parallel?
- [ ] **Varying Coordinate Series:** Are series and lists varied strategically in length and rhythm to maintain reader engagement?

### 8. Sentence Modification and Complexity (Bacon)

- [ ] **Well-Developed Modifiers:** Are early, middle, and late modifiers (periodic and cumulative sentences) used to add texture and precise detail without tangling the core clause?
- [ ] **Noun & Verbal Phrases:** Are appositives, absolutes, and verbal phrases used effectively to pack in descriptions and context smoothly, reducing wordiness?

### 9. Voice and Variety (Sexton + Bacon)

- [ ] **Sentence Length Variation:** Is there a healthy mix of short, punchy sentences (for impact and clarity) and longer, qualified sentences (for nuance and development)?
- [ ] **Consistent Scholarly Voice:** Is the formality consistent? Is melodrama or hyperbole ("revolutionary", "completely changes") avoided in favor of precise understatement and earned credibility?
- [ ] **Fresh Diction:** Are clichés, boilerplate ("in today's rapidly evolving landscape"), and generic verbs eliminated in favor of original phrasing and precise terminology?

---

## Part 4: IS Paper Structure and “Red Thread” (Baird)

### 10. Red Thread and Hourglass Shape

- [ ] **[BLOCKER] Red Thread:** Does the paper follow a focused, continuously connected line of reasoning (“red thread”) from start to finish, without fraying into unrelated side-arguments?
- [ ] **[MAJOR] Hourglass Structure:** Does the overall narrative move from broad consensus (what the target audience already knows), to a narrow focus on the specific tension and theorizing, and then back out to broader applications, generalizations, and opportunities?
- [ ] **[MAJOR] Enjoyable but Not Taxing:** Would a reader find the article enjoyable to read and cognitively manageable, while still feeling that their knowledge has changed by the end?

### 11. Five Core Elements of an IS Theory Paper

- [ ] **Area of Theoretical Focus:** Is the target theoretical area and target *subcommunity* of IS clearly specified, with a short statement of why this audience should care?
- [ ] **Relevant Background (Common Ground):** Does the paper start from what this subcommunity already knows and assumes (their consensus and “common ground”) rather than re‑teaching general IS background?
- [ ] **[all] Theoretical Tension (Assumption Challenging):** Does the paper explain *why* new theory (or, at P0/P1, *new characterization*) is needed, emphasizing assumption‑challenging (e.g., revisiting taken‑for‑granted assumptions, looking for heterogeneity where homogeneity is assumed) rather than only gap‑spotting?
- [ ] **[P2] Resolution of Theoretical Tension:** Is it clear what the primary objective of the theorizing is, what theory‑building/extension approach is used, and under what conditions (unit of analysis, boundary assumptions) the theorizing holds? *(At P0/P1, this item is deferred — the equivalent deliverable is a refined problem statement, not a resolved tension.)*
- [ ] **[P2] Guidelines for Application:** Does the paper provide explicit, concrete guidance on how future researchers can apply the theorizing (steps, use cases, or research questions), rather than stopping at the framework itself? *(For P0/P1 papers, the analogue is the **Forward-Pointing Handoff** item in §1: candidate qxxx open questions handed forward, not application guidelines.)*

### 12. Target Audience, Message, and Boundary Conditions

- [ ] **Specific Subcommunity:** Is the paper written for a clearly defined IS subcommunity (e.g., IS use, HCI, sociomateriality) rather than “the entire IS field,” and is the message tailored to that group’s traditions and assumptions?
- [ ] **Who / What / Why / When / Where / How:** Are the core questions (“Who are we speaking to?”, “What is our message?”, “Why is this sufficiently new?”, “When and where does this theorizing apply or not apply?”, “How should it be used?”) answered explicitly in the text?
- [ ] **Boundary Conditions from Assumptions:** Are boundary conditions derived from, and explained in terms of, the assumptions being challenged (e.g., when human primacy or a particular unit of analysis no longer holds), so readers know where the theory should and should not be used?

### 13. Literature Review as Synthesis (Not Inventory)

- [ ] **Synthesis Table (Optional but Recommended):** For major research streams, has the author considered building a synthesis table (research area, description, key citations) to clarify how literatures cluster and relate to the paper’s objective?
- [ ] **Evidence‑Based Editorial:** Does the background section interpret and synthesize prior work as an evidence‑based editorial (how the literature relates to the objective and tensions), rather than listing study summaries or “what is out there”?
- [ ] **String Citations for Consensus:** Where appropriate, does the paper use “string” citations to compactly signal consensus (e.g., “we know a lot about X [citations], Y [citations], and Z [citations]”) without over‑explaining?
- [ ] **Classics and Recent Work:** Are both foundational “classic” pieces and more recent follow‑ups cited, instead of only very old or only very new work?
- [ ] **No Laundry Lists:** Has the author avoided listing everything they have read, instead citing only what is necessary to establish common ground and tension?
- [ ] **Tie Back to Focal Tension:** Do paragraphs in the literature review consistently tie the summarized work back to the focal problem phenomena and theoretical tension of this paper?

### 14. Guidelines, Future Research, and “Discarded Options”

- [ ] **Guidelines Section:** Does the paper include, or at least implicitly provide, guidelines that make it possible for a doctoral student or researcher to derive models or empirical studies from the framework?
- [ ] **Future Research from Design Choices:** Are future research opportunities explicitly linked to the design choices and boundary conditions of the current theorizing (i.e., do they arise from “discarded options” such as alternative units of analysis, agents, or configurations that were not modeled)?
- [ ] **Explicit Trade‑offs:** Where major choices were made (e.g., framework vs. explanatory model, dyadic vs. collective unit of analysis), are the trade‑offs and rationales briefly explained so readers see *why* this path was chosen?

### 15. Process and Revision Tips

- [ ] **Middle‑Out Drafting:** For substantial re‑writes, is the core middle of the paper (background, theory‑building approach, new theory development) drafted and stable before investing heavily in polishing the abstract and introduction?
- [ ] **Abstract and Introduction as Executive Summaries:** Do the abstract and introduction “get right to the point” about focus, tension, resolution, and contribution, rather than withholding the main contribution as a late surprise?
- [ ] **[BLOCKER] No Surprise Constructs or Terms:** Are all constructs, relationships, and key terms introduced and justified before they appear in results, implications, or late‑stage arguments (i.e., no “surprise” elements emerging only in the conclusion or discussion)?
- [ ] **[MAJOR] Terminology Consistency (“Synonyms Are the Enemy”):** Is the terminology for key constructs and concepts kept consistent throughout, avoiding new labels or near‑synonyms in later sections that could be mistaken for new ideas?
- [ ] **[BLOCKER] Construct Provenance (“Every Formal Term Needs a Home”):** Is every italicized, bolded, or quoted term that signals a formal construct either (a) directly traceable to a cited source, or (b) explicitly introduced as the paper's own coinage (e.g., “what this paper terms X”)? No formal‑looking construct should appear without clear attribution—uncited terms mislead readers about intellectual lineage and risk reviewers flagging unsupported terminology.
- [ ] **Tightening Passes:** Has the full paper been reread multiple times specifically to remove extraneous text, tighten the red thread, and clarify any areas the author themselves found boring or confusing?
- [ ] **Reader Effort:** Would a typical IS reader be able to follow the argument without expending excessive cognitive effort, given the current structure and prose?
