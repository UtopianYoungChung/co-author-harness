# Research Paper Writing Guidelines: One-Stop Playbook

**Purpose:** Single reference for tone, claims, theory positioning, audience, structure, citations, and process when drafting or revising academic papers (conference, journal, or course).

**Status within the package:** This file is **Step 2** of the seven-step full-package review prescribed by `MASTER_research_and_paper_guidelines.md`. It is the cross-venue argument-hygiene playbook. For the exact invocation order, see `REVIEW_ORCHESTRATION.md`.

**Historical provenance.** The content here was originally synthesized from several Year 2026 project files (`CLAUDE.md`, `CAiSE_Rev01/research_notes/review/lessons_caise_revision.md`, `CAiSE_Rev01/research_notes/writing_style_checklist.md`, `CAiSE_Rev01/research_notes/DIR-ACADEMIC-01.md`, `INF3130_HCI/Paper/resources_and_guides/project_writing_style_checklist.md`, `AIWare/CLAUDE.md`). Those files remain authoritative **within their projects** where venue-specific supplements still apply; the rules merged here are the cross-venue subset and are maintained in this package going forward.

For venue-specific rules (page limits, template packages), always follow the call for papers and publisher instructions; this document is **cross-venue style and argument hygiene**, not a substitute for those.

---

## 1. Tone and voice

- **Impersonal and evidence-driven** for claims about findings: prefer “This paper shows…,” “The analysis suggests…,” over “We believe…” when stating what the work establishes.
- **Formal but approachable:** clear academic English, slightly conversational where appropriate; avoid slang and melodrama (“revolutionary,” “completely changes”).
- **Concise and scannable:** short sentences where they help; one main idea per paragraph; visible logical links (“therefore,” “because,” “as a result”) between paragraphs when useful.
- **Consistent scholarly register:** no hyperbole; prefer precise understatement and earned credibility.
- **Fresh diction:** cut clichés and boilerplate (e.g. “in today’s rapidly evolving landscape”); prefer precise terms and strong verbs (“enables,” “constrains,” “demonstrates”) over weak fillers (“looks at”).
- **Reader-accessibility commitment (C-5, binding; new at v0.7.2):** every revision must be accessible to a careful human reader at first read. Six Sub-checks A–F operationalise this in `SAFEGUARD_LAYER.md` Check 8 and in `skills/accessibility-overlay/SKILL.md`: paragraph cadence (turn-points in paragraphs >150 words), sentence-length variation, first-use definition for every theoretical construct, section-transition signposting (orienting clause + contribution clause), jargon discipline (≤ 2 new domain terms per paragraph at P1; 1 at P2; 3 at P0), worked examples at density spikes. A Check 8 BLOCKER at T3 refuses TerminalSignoffRow writes (`TIER_PROTOCOL.md §3.3.3`). Accessibility here is **extraneous-load reduction**, not intrinsic-load collapse — the rule does not mandate dilution, only low prose-bookkeeping cost.

---

## 2. Claims, comparison language, and hedging

### 2.1 Never claim others “cannot” without evidence

- Say they **did not aim to**, **have not addressed**, or **lie outside the analytical focus of**; do not claim that they cannot without evidence.
- Vary phrasing by section so the paper does not sound templated.

### 2.2 Baseline comparison

- **Define the comparison set once** (e.g. in Related Work). Elsewhere refer to “the approaches reviewed in Section X” or “established approaches in [area].”

### 2.3 Avoid absolutes

- Steer clear of heavy absolutes: **must**, **cannot**, **comprehensively**, **anticipate** (when it implies predicting trajectories).
- Practical swaps: “must” → “should” where appropriate; “anticipate dynamics” → “surface or reveal”; “comprehensively” → remove or “systematically.”

### 2.4 Do not say what you do not do

- Avoid “We do not include a comparison table” or “We do not claim superiority.” That invites readers to ask why not and can sound defensive.
- **State contributions in positive terms.**

### 2.5 Scope and exploratory work

- If the contribution is **exploratory or analytical**, say so explicitly (e.g. exploratory mapping, analytical comparison, not a generalizable empirical claim).
- Add a **short hedge** in abstract or conclusions where a naive reader might over-read certainty.

### 2.6 Softening without robotic repetition

- Soften claims **in context** with varied phrasing: e.g. “lie outside the current analytical focus,” “were not aimed at addressing,” “not oriented toward surfacing,” “not systematically integrated.”

### 2.7 Research questions

- Prefer **one sharp, answerable RQ** over multiple RQs where the second drags in comparisons you cannot substantiate.

---

## 3. Theory, constructs, and attribution

### 3.1 External theories support the argument; they are not the contribution

- Use **“we draw on”** rather than **“we integrate”** or **“we extend”** unless the paper truly extends that discipline’s theory for that venue’s bar of evidence.
- Position external work as **consistent with** or **supportive of** the argument.
- **Asymmetric framing:** home discipline (e.g. RE, modeling, IS subfield) carries the contribution; imported theories (e.g. org identity, dynamic capabilities) are **resources**, not co-equal pillars.

### 3.2 Select theory on its merits, not only because a notation exists

- Justify the **theory** first, then show how the modeling or method serves it, not the reverse.

### 3.3 Scholars use theories; theories do not “speak” alone

- Prefer “Dynamic capabilities **have been used** to…” over “Dynamic capabilities theory provides…” when the move is actually attributed to named scholars.

### 3.4 Models are instruments; people act

- Do not attribute agency to models (“the model mitigates…”). **Analysts / practitioners** use models; subsequent actions address risks.

### 3.5 Conceptual and survey-oriented papers

- **Do not commit to one theoretical lens too early:** treat competing perspectives as a landscape; attribute positions to authors and schools.
- **Surface hidden assumptions** behind loaded or contested terms (e.g. agency, autonomous, agentic, hybridity, delegation).
- **Distance from hype labels** where the goal is durable conceptual contribution; technology categories shift quickly.
- **Neutralize premature judgment** in abstracts and introductions: avoid loaded evaluators (“erosion,” “disrupt,” “legacy” as sneer) unless quoting; prefer descriptive framing of phenomena.

### 3.6 Constructs and terminology

- **Synonyms are the enemy** for core constructs: one label per idea unless you explicitly define a distinction.
- **Every formal-looking term needs a home:** either traceable to a cited source or explicitly introduced as this paper’s coinage (“what we term X”).
- **“Standard” implies consensus**; use only when defensible. Otherwise prefer “existing,” “established,” or name specific approaches.

---

## 4. Audience awareness (especially engineering / IS-engineering)

### 4.1 Engineer’s-eye test

- Reread paragraphs as a **technical reviewer** would. If the reaction might be “what’s the concrete contribution?”, rewrite toward mechanism, artifact, or clear analytical move.

### 4.2 Disciplinary vocabulary

- **Borrowed-discipline jargon** (e.g. some critical-theory or iSchool phrasing) needs translation or removal for engineering-heavy venues.
- **Technical terms carry technical meaning:** e.g. “first-class” in modeling ≈ in the metamodel; do not use rhetorically if the paper does not support that reading.
- **“Binary”** in social science often means oversimplification; in engineering it may mean 0/1. Disambiguate or avoid.

### 4.3 Positioning the contribution (when a formal method or language is used)

- The **notation or tool is the vehicle**, not the contribution. The contribution is the **problem, concept, or guidance** the paper advances; the language illustrates suitability.
- **Hint at broader significance** when the paper uses one instance (e.g. a specific identity construct) to stand for a wider class of concerns, without blurring boundaries of what this submission actually shows.

### 4.4 Related work and comparisons

- **Complementarity, not dismissal:** prefer “does not currently provide guidance for…” over “was not designed for…” when the goal is to leave room for extension.
- **No false parallels** across fields (e.g. assuming “X theory” and “Y theory” are equally established labels in the target community).
- **Socio-technical** is broader than one modeling family: acknowledge wider HCI/CSCW/org design where relevant.

### 4.5 Describing the empirical setting honestly

- If the case uses **conventional ML** (not cutting-edge agentic stacks), avoid language that implies capabilities the data do not support. Prefer precise descriptions of the system and setting.

---

## 5. Narrative structure (macro and meso)

*Condensed from fiction-for-academia structure (Sexton) and IS theory-paper shape (Baird) as used in the HCI project checklist.*

### 5.1 Core arc

- **Clear central need / gap / RQ** early.
- **Problem (gap) → development (analysis / mapping / evidence) → resolution (answers / implications).**
- Contribution should **emerge through** argument and evidence, not only be declared once in the introduction.

### 5.2 Opening and title

- **Informative title**; opening with a **concrete hook** or gap before dense background.
- End introduction with a **short roadmap**.

### 5.3 Middle and climax

- **~80% of substance** in the core (theory, analysis, results): earned conclusions, not sudden fixes.
- Conclusions should **answer** the stated RQs / needs.

### 5.4 Show, then tell

- Ground abstractions with **examples**; break long abstract runs with illustrations.

### 5.5 “Red thread” and hourglass

- One continuous line of reasoning from start to finish.
- **Broad consensus → narrow tension and contribution → broader implications** (hourglass).

### 5.6 Theory papers in IS (when applicable)

- Specify **subcommunity** and why they should care.
- **Common ground** from what that audience already assumes.
- **Theoretical tension** as assumption-challenging, not only gap-spotting.
- **Boundary conditions** and **guidance for use** (how others apply or test the ideas).

### 5.7 Literature review

- **Synthesis, not inventory:** editorial line on how streams relate to your objective.
- **String citations** for stable consensus where appropriate.
- **Classics and recent** work; tie each paragraph back to **your** focal tension.
- **Snowballing and surveys (Yu-style checks):** forward/backward from key refs; for broad or negative claims, anchor to **reviews or mapping studies**; rephrase “no method exists” to what **cited** surveys actually support; state **coverage limits** honestly.

### 5.8 Process

- **Middle-out drafting** for big rewrites: stabilize core before over-polishing abstract/intro.
- Abstract and intro as **executive summaries** of focus, tension, and resolution, not hiding the contribution.
- **No surprise constructs** late: define terms before they carry weight in results or discussion.

---

## 6. Citations and evidence

- **No fabrication:** mark `[REF to be verified]` rather than inventing references.
- **Each citation supports the specific claim** beside it.
- **Currency:** support “immature field” / “emerging area” claims with **recent** surveys or syntheses, not dated workshop papers alone.
- **Appearance-first bibliography order** when using numeric `\\bibitem` / first-citation ordering (e.g. Springer-style expectations): renumber after edits.
- **Numbers and tables:** when empirical claims exist, tie prose to **canonical artifacts** (scripts, JSON, reports) and reconcile before submission (see AIWare-style “source of truth” practice).

---

## 7. Punctuation: em-dash, en-dash, and alternatives

**Em-dash (—).** Use **sparingly**. In most prose, commas, colons, semicolons, parentheses, or a new sentence achieve the same clarity with **more variety** and less visual monotony. Reserve an em-dash only when it delivers **clearly more** than those alternatives (e.g. a single, sharp interruptive aside that would be awkward with parentheses). **Do not** stack multiple em-dashes in one paragraph or nest em-dash pairs. In **LaTeX**, `---` produces an em-dash; avoid overusing it in running text.

**En-dash (–).** Distinct from the em-dash. Conventional uses include **compound modifiers** where both parts carry equal weight (e.g. human–computer in some house styles), **ranges** (pages, years), and **connection** (author–date style in tables). Follow your venue’s typographic rules; do not treat en-dash as interchangeable with em-dash.

**Hyphen (-).** Use for **standard compounds** and line breaks as usual.

**LaTeX and manuscript hygiene**

- **Preserve** `\\label`, `\\ref`, `\\cite`, math environments, and bibliography structure unless explicitly changing them.
- **Avoid invasive template changes** (`\\documentclass`, packages) without instruction.
- Where a publisher template prescribes em-dashes, follow the template; otherwise prefer the restraint above.

---

## 8. Response letters and rebuttals

- **Do not open with limitations** (retrospective case, single site, etc.); open with **positive contribution**.
- **Name parent disciplines** for imported theories so reviewers understand provenance.
- **High ground, not defensive:** lead with what you contribute; **reframe** rather than bluntly contradict when possible.
- **Soften scrutiny-magnet words** (e.g. “adequacy”) if the evidence base is narrow; be precise about what is demonstrated **at this stage**.

---

## 9. Workflow: research integrity loop

*Adapted from the AIWare / CAiSE “four-layer” ethos.*

1. **Directive:** RQs, scope, inclusion criteria, and rubrics are written down before drafting drives scope creep.
2. **Draft** from sources and data; do not rely on uncited recall for citations or numbers.
3. **Self-critique (Reviewer 2 pass):** Did I verify each citation? Do claims match artifacts? Is methodology consistent with the protocol?
4. **Deterministic checks** where available: citation keys, number reconciliation, build logs.
5. **Fix and finalize** only after critique passes; update the directive/checklist when a mistake type recurs (**self-annealing**).

**Motto:** Trust, but verify.

---

## 10. Quick pre-submission checklist

Use as a final pass (tick mentally or in issue tracker):

- [ ] No unsupported “cannot” / “must” / “comprehensively” / over-strong “anticipate.”
- [ ] Comparison baseline defined once; later references are short pointers.
- [ ] Contributions stated **positively**; no apology list of what we omit.
- [ ] External theories **drawn on**; home-discipline contribution clear; tool/language is **vehicle** unless the paper truly is about the notation.
- [ ] Models don’t “act”; people and organizations do.
- [ ] Audience vocabulary checked (engineering vs critical/social phrasing).
- [ ] Abstract hedged if scope is exploratory or evidence is narrow.
- [ ] Lit review synthetic; negative universal claims match cited evidence.
- [ ] Key terms consistent; formal terms attributed or coined explicitly.
- [ ] Em-dashes minimal (see §7); punctuation varied (commas, colons, semicolons, parentheses).
- [ ] Citations verified; numeric order / bib order correct if required.
- [ ] Response letter opens strong; disciplines named; tone collaborative.

---

*Document generated to consolidate recurring rules across Year 2026 projects. Update this file when new venue-specific or advisor-specific lessons accumulate.*
