# Master Guidelines: Research and Academic Paper Writing

**Status:** Primary consolidated reference among the files in this folder (not a substitute for venue author guides, originals cited below, or advisor direction).  

**Scope:** Cross-venue **argument hygiene**, **process**, **structure**, **tone**, **sentence craft**, and **integrity**. Venue-specific rules (page limits, templates, CFP) still override where they conflict.

---

## Policy: mandatory full-package review

**Binding rule for this folder:** No manuscript, thesis chapter, or formal response letter governed by these guidelines is **complete** until the author (or agent) has **applied every actionable guideline** in **each component source file** below—not only this master. The master is the **map**; the **seven component files** are the **full statute**. Routine drafting may proceed from the master alone, but **completion** requires the ordered pass.

### When the full-package pass is required (before signing off)

1. **Submission-bound work:** final draft for journal or conference submission; course paper marked **final**; thesis chapter sent to committee or deposited.
2. **Major revision:** resubmission after reviews, or any rewrite that restructures argument, claims, or contributions.
3. **Response letter + revised manuscript:** cross-check rebuttal text against the same sources (especially `research_paper_writing_guidelines.md` §8 and `CLAUDE.md`).
4. **Maintaining this master:** whenever `MASTER_research_and_paper_guidelines.md` is edited, reconcile changes against the seven sources so the traceability matrix stays true.

### Prescribed order (do not skip files)

Work **top to bottom** within each file (every section, checklist item, and table that applies to your **stage**—P0/P1/P2 where relevant). If a passage is not applicable (e.g. IS-only Baird theory paper blocks on an empirical CS note), **mark it N/A in your sign-off** with a one-line reason—do not silently skip.

| Step | File | What “done” means |
|------|------|-------------------|
| 0 | `MASTER_research_and_paper_guidelines.md` | Parts A–H read; **G.4** (below) prepared for sign-off |
| 1 | `general_research_project_guidelines.md` | All five milestones’ guidance reviewed; manuscript aligned or deviation noted |
| 2 | `research_paper_writing_guidelines.md` | Entire playbook (§§1–10) applied; venue still wins on template conflicts |
| 3 | `baird_2021_writing_guidelines.md` | All sections applied where relevant to paper type (theory/empirical steps, lenses, tips table) |
| 4 | `bacon_2009_well_crafted_sentence_guidelines.md` | All chapters §1–11 + **§10 checklist** executed on the prose (or N/A with reason) |
| 5 | `Sexton_Fiction_to_Academic_Writing_Guide.md` | §§1–10 (including **§10** table) applied to narrative/opening/climax |
| 6 | `CLAUDE.md` | All bullets under Academic Writing Rules and project notes relevant to your task |
| 7 | `project_writing_style_checklist.md` | **Part 0** (stage) + **Parts 1–4**: every applicable checkbox for your **P-stage** and paper type |

**Note:** Step 7 is intentionally **last** so the integrated checklist catches overlaps from Sexton, Bacon, and Baird in one pass.

### Conflicts

- **Venue or advisor** vs this package → **venue/advisor** wins.
- **This master** vs a **component `.md`** → **component file** wins until the master is updated.

---

## Package folder, verification commands, and traceability

**Canonical folder (this package):**

This package lives at `.paper-package/` under the Research root. All file references below are **relative to this package folder**. When working in a Cowork or Claude Code session, the package is reachable at `<mounted-research-root>/.paper-package/`.

Every substantive rule in this master was **merged from the documents in this folder**. To **verify** wording, completeness, or updates, open the **source file(s)** in the matrix at the end of this section. If the master and a source **disagree**, treat the **source component file** (or the original publication) as authoritative for that topic until the master is edited.

### Commands to list and inspect package files

**In a Cowork/Claude Code session:** Use the Glob tool or `ls` on the package directory.

**In PowerShell (local Windows):**

```powershell
# Change to the package folder (adjust path to your local setup)
Set-Location -LiteralPath $env:PACKAGE_PATH   # or navigate manually
Get-ChildItem -LiteralPath . -File | Sort-Object Name | Format-Table Name, Length, LastWriteTime -AutoSize
```

**Quick line counts (sanity-check that files are present and non-empty):**

```powershell
Get-ChildItem -LiteralPath . -Filter '*.md' | ForEach-Object { '{0,6}  {1}' -f ((Get-Content -LiteralPath $_.FullName | Measure-Object -Line).Lines), $_.Name }
```

Use **Find in Files** / editor search on the **package folder** for keywords (e.g. `red thread`, `P0`, `cannot`) to jump to the exact passage in each source.

### Constitution: files in this package

| # | Component file | Role in this master |
|---|----------------|---------------------|
| 0 | `MASTER_research_and_paper_guidelines.md` | This file: synthesis + traceability |
| 1 | `baird_2021_writing_guidelines.md` | IS article structure, nine-step process, reviewer lenses |
| 2 | `bacon_2009_well_crafted_sentence_guidelines.md` | Sentence-level craft, syntax, revision heuristics |
| 3 | `research_paper_writing_guidelines.md` | Claims, theory framing, citations, punctuation, workflow |
| 4 | `general_research_project_guidelines.md` | Five-milestone project arc |
| 5 | `project_writing_style_checklist.md` | P0/P1/P2 stages; **full** integrated checklist (Sexton+Bacon+Baird) |
| 6 | `Sexton_Fiction_to_Academic_Writing_Guide.md` | Narrative arc, show/tell, cause–effect, openings |
| 7 | `CLAUDE.md` | Condensed project rules (paths inside that file may point outside this folder; **substantive rules are inlined below**) |
| 8 | `SAFEGUARD_LAYER.md` | Post-review integrity checks: regression, drift, consistency, contradictions, traceability, voice |
| 9 | `GROUNDING_PROTOCOL.md` | **Binding** no-hallucination rules; cannot be overridden; enforced by Reflector grounding audit every round |

**Policy reminder:** rows **1–7** are the **mandatory full-package pass** (see **Policy: mandatory full-package review** above) before any submission-final sign-off. Row **8** (`SAFEGUARD_LAYER.md`) runs at Step 8.5 in the orchestration; its eight checks (Checks 1–6 from v0.5.x; Check 7 Inter-Sentential Logical Connective Audit and Check 8 Reader-Experience / Prose Architecture Audit added at v0.7.2) are the integrity layer that catches problems the seven-step review does not prescribe. Check 8 is the T3 convergence gate authoritatively specified at `TIER_PROTOCOL.md §3.3.3`.

When a detail is needed (e.g. Baird appendices A–D, Bacon glossary), open the listed component file or the **original publication** named in Part H.

### Traceability matrix (master → sources)

Use this table to **follow** each block of the master back to the **section headings** (or equivalent) in the folder documents.

| Master section | Primary source file(s) | Source location (heading / topic) |
|----------------|------------------------|-------------------------------------|
| **A.1** Reader, red thread, hourglass | `baird_2021_writing_guidelines.md`, `research_paper_writing_guidelines.md`, `project_writing_style_checklist.md` | Baird §1; Playbook §5.5; Checklist Part 4 §10 |
| **A.2** Evidence, integrity loop | `research_paper_writing_guidelines.md`, `CLAUDE.md` | Playbook §6, §9; CLAUDE “Academic Writing Rules” |
| **A.2** Ethics / reporting stub | *General research norms; align to venue/IRB* | Not duplicated in a single package file—follow CfP, publisher, IRB |
| **A.3** Tone, voice, diction | `research_paper_writing_guidelines.md`, `Sexton_Fiction_to_Academic_Writing_Guide.md`, `project_writing_style_checklist.md` | Playbook §1; Sexton §5–6; Checklist Part 3 §9 |
| **A.4** Humanness (concept + voice) | *In-master addendum (2026-04 revision)*; Haslam, Loughnan & Holland (2013); Baumer et al. (2024) | A.4.1 substantive concept; A.4.2 anti-LLM-tic discipline |
| **B.1–B.2** Claims, hedging, rebuttals | `research_paper_writing_guidelines.md`, `CLAUDE.md` | Playbook §2, §8; CLAUDE key principles |
| **B.3** Scope, RQs | `research_paper_writing_guidelines.md`, `project_writing_style_checklist.md` | Playbook §2.7; Checklist Part 0, Part 1 §1 |
| **B.4** Theory, constructs | `research_paper_writing_guidelines.md`, `baird_2021_writing_guidelines.md`, `project_writing_style_checklist.md` | Playbook §3; Baird §6 Step 6 / §5 table; Checklist Part 4 §§11–15 |
| **B.5** Audience, vocabulary | `research_paper_writing_guidelines.md` | Playbook §4 |
| **C.1** Five milestones | `general_research_project_guidelines.md` | All sections (Milestones 1–5) |
| **C.2** P0/P1/P2 | `project_writing_style_checklist.md` | Part 0 |
| **D.1–D.2** Core arc, openings | `Sexton_Fiction_to_Academic_Writing_Guide.md`, `research_paper_writing_guidelines.md` | Sexton §§1–2, 4, 6–8; Playbook §5.1–5.4 |
| **D.3–D.7** IS theory, nine steps, lenses, lit review, tips | `baird_2021_writing_guidelines.md`, `research_paper_writing_guidelines.md` | Baird §§2–5; Playbook §5.6–5.8 |
| **E** Citations, dashes, LaTeX | `research_paper_writing_guidelines.md` | Playbook §§6–7 |
| **F** Sentence craft | `bacon_2009_well_crafted_sentence_guidelines.md` | All numbered sections + checklist §10 |
| **G.1** Pre-submission | All of the above (condensed) | Cross-check against `project_writing_style_checklist.md` |
| **G.2** Stage-aware excerpt | `project_writing_style_checklist.md` | Part 0 + Part 1–4 (excerpt only in master) |
| **G.3** Sexton checklist | `Sexton_Fiction_to_Academic_Writing_Guide.md` | §10 table |
| **H** Deeper reading | Named originals + component `.md` files | — |

---

## Part A — Foundational principles

### A.1 Reader and cognitive load

- Aim for prose that is **enjoyable**, **changes what readers know**, and remains **easy to process** (not cognitively taxing).
- Maintain one **red thread**: a single, continuous line of reasoning from start to finish.
- Use an **hourglass** shape: **broad** opening (shared context) → **narrow** (your problem, method, contribution) → **broad** closing (implications, limits, future work).
- **Reader-accessibility constraint (binding, all P-stages; new at v0.7.2).** Every revision the harness produces must be accessible to a careful human reader at first read, regardless of the conceptual difficulty of the material on the page. Accessibility here is **extraneous-load reduction**, not intrinsic-load collapse — a dense Vidal contradiction-mapping passage is fully compliant if its sentences are paced, its constructs are defined, and its rhythm carries the reader. The constraint is operationalised by six Sub-checks A–F in `SAFEGUARD_LAYER.md` Check 8 (paragraph cadence, sentence-length distribution, first-use definition, section-transition signposting, jargon discipline, worked examples at density spikes) and audited by the `skills/accessibility-overlay/SKILL.md` overlay. At T3 Iterate & Converge, a Check 8 BLOCKER gates the TerminalSignoffRow per `TIER_PROTOCOL.md §3.3.3`. Cross-reference: commitment C-5 in `STYLE_COMMITMENTS.md` and Hard Constraint #8 of the Ph.D.-root CLAUDE.md.

### A.2 Evidence, integrity, and verification

- **No fabrication** of citations, numbers, or outcomes; use placeholders such as `[REF to be verified]` until confirmed.
- Each citation must **support the specific claim** it sits beside.
- **Currency:** “emerging field” / “immature area” claims need **recent** surveys or syntheses, not dated workshop papers alone.
- **Workflow (research integrity loop):** (1) Write down RQs, scope, and inclusion criteria before drafting drives scope creep. (2) Draft from sources and data. (3) **Reviewer 2 pass:** verify citations; claims vs artifacts; methodology vs protocol. (4) Deterministic checks (bib keys, number reconciliation, builds) where possible. (5) Fix after critique; update checklists when mistake types recur. **Motto:** trust, but verify.

**Ethics, participants, and reporting (venue + institution):** Follow **IRB / ethics review**, **consent**, and **data-handling** rules required by your institution and jurisdiction. For empirical papers, comply with the **venue’s** expectations on **reporting** (e.g. limitations, reproducibility statements, data/code availability when mandated). This package does not list those rules exhaustively—use the **call for papers** and **publisher checklist**.

### A.3 Tone and voice

- **Claims about what the work establishes** (findings, demonstrated properties): prefer **impersonal, evidence-driven** wording—“This paper shows…,” “The analysis suggests…,”—rather than “We believe…” for the same content.
- **Process and positioning** (what you did, how the paper is organized): **first-person plural (*we*)** is conventional in many IS / CS / HCI papers for methods and structure (“We analyze…,” “In §4 we…”). Match **venue** and **exemplar articles** from the target outlet.
- **Prior work:** keep an **attributive** voice (“Author X argues…,” “Prior work finds…”).
- **Formal but approachable** academic English; **concise and scannable**; one main idea per paragraph; visible links between paragraphs (“therefore,” “because,” “as a result”) when helpful.
- **No hyperbole**; prefer precise understatement and earned credibility.
- **Fresh diction:** cut clichés and boilerplate (“in today’s rapidly evolving landscape”); prefer strong verbs (“enables,” “constrains,” “demonstrates”) over weak fillers (“looks at”).

*Sentence-level focus, passives, and variety are developed in Part F; they coexist with discipline-specific norms (e.g. more passives in some empirical reporting).*

### A.4 Humanness: substantive concept and stylistic discipline

Two distinct but related uses of **humanness** govern this package. Treat them as a paired check: the first asks **whose** humanness the work encodes; the second asks whether the **prose itself** still sounds human after AI-assisted drafting.

**A.4.1 Humanness as analytical concept (Haslam, Loughnan & Holland, 2013).** Where a project models people, users, stakeholders, or subjects (especially in HCI, requirements engineering, AI governance, identity-sensitive design), do not treat *humanness* as a monolithic property. Distinguish:

- **Human uniqueness** — traits separating humans from other animals (civility, refinement, higher cognition).
- **Human nature** — traits separating humans from machines and inanimate objects (warmth, emotionality, vitality, flexibility).

When formal categories, requirements, interfaces, or classifications define roles and exceptions, ask **which traits along these two dimensions are presupposed**, and **whose** humanness is rendered invisible. This is the productive form of the question "whose humanness is encoded?" and it generalizes beyond any one paper: any artifact that operationalizes subjects (stakeholder models, personas, eligibility rules, evaluation rubrics) makes such a commitment whether or not the authors notice. Surface it.

**A.4.2 Humanness of voice (anti-LLM-tic discipline).** AI-assisted drafts pass surface fluency checks while still reading as machine output. The following patterns are the most reliable tells; sweep for them on every revision pass:

| Tic | Why it reads machine | Counter-move |
|-----|----------------------|--------------|
| **"Not X but Y" / "Not just X but Y"** stacked across paragraphs | Signature LLM rhetorical scaffold | Allow ≤ 2 per paper; rewrite the rest as direct assertions |
| **Triadic lists** ("create, organize, and govern"; "person-based, role-based, and relational") | Generated parallelism — predictable cadence | Break at least half into asymmetric pairs or singletons; vary length |
| **Symmetric three-field comparisons** ("X can optimize… Y can clarify… Z can interpret…") | Reads as template fill | Vary sentence length and verb across the three; refuse parallel grammar |
| **Trailing one-sentence add-ons** appended to finished paragraphs | "Polishing" residue — afterthought rhythm | Fold into the paragraph or cut |
| **Hedged transitions at every paragraph break** ("accordingly," "likewise," "therefore," "in practical terms") | Mechanical scaffolding signal | Drop ~40 %; logic survives |
| **Abstract-noun stacking** ("contestability, accountability distribution, deskilling risk") | Flattens voice | Insert a concrete verb or image every few sentences |
| **Glossary-dump openings** (4+ italicized definitions back-to-back) | Reads as parachuted reference, not argument | Defer each term to the paragraph where it first does analytical work |
| **Semicolon-chained triads** ("X infers; Y entangles; Z co-constitutes") | Classic LLM list-as-sentence | Recompose as cause-and-effect prose |

**Positive markers of human voice** (cultivate, do not strip):
- Lived-in concrete detail in examples (specific roles, named processes, plausible incidents).
- Asymmetric rhythm — long sentence next to short; varied openings.
- Idiomatic verbs and images among the abstractions.
- First-person framing where the venue permits, used consistently rather than sprinkled.
- Earned callbacks: a concept introduced early reappears in the middle (not only at the close), so the closing return feels remembered, not retrieved.

**Process rule.** After any AI-assisted draft or revision, run a dedicated **humanness pass**: search for each tic in the table above, count occurrences, and reduce by at least half unless the count is already ≤ 2. Pair this with a **callback audit** — every concept named in the opening frame should have at least one substantive mid-paper use before it returns in the conclusion.

---

## Part B — Claims, hedging, and positioning

### B.1 Comparison and limits of criticism

- **Never** claim others “**cannot**” without evidence. Prefer **did not aim to**, **have not addressed**, or **lie outside the analytical focus of**.
- **Define the comparison set once** (e.g. in Related Work); later use short pointers (“the approaches reviewed in Section X”).
- Avoid heavy absolutes: **must**, **cannot**, **comprehensively**, and over-strong **anticipate** (when it implies predicting trajectories). Practical swaps: **must** → **should** where appropriate; **anticipate dynamics** → **surface or reveal**; **comprehensively** → remove or **systematically**.

### B.2 Positive, non-defensive contributions

- **Do not** catalogue what you omit (“We do not include a comparison table”). That invites avoidable attacks. **State contributions positively.**
- In **response letters / rebuttals:** do **not** open with limitations; open with **positive contribution**. Name **parent disciplines** for imported theories. Prefer high-ground **reframing** over blunt contradiction. Soften scrutiny-magnet words (e.g. “adequacy”) when evidence is narrow; state what is demonstrated **at this stage**.

### B.3 Scope and research questions

- If work is **exploratory or analytical**, say so; **hedge** in abstract/conclusion where readers might over-read certainty.
- Soften with **varied** phrasing in context (not robotic repetition).
- For the **final submission**, prefer **one sharp, answerable primary RQ** when extra RQs would imply comparisons or evidence you do not provide.
- **Stage caveat (see Part C):** in **P0/P1** deliverables, avoid numbered, answer-demanding RQs that belong in **P2**; use problem characterization and forward-pointing open questions instead.

### B.4 Theory, constructs, and attribution (reconciled)

| Principle | Guidance |
|-----------|----------|
| External theory | Use **“we draw on”** unless the paper truly **extends** that discipline’s theory to the venue’s bar. Position as **consistent with** / **supportive of** your argument. **Asymmetric framing:** home discipline carries the **contribution**; imported theories are **resources**, not co-equal pillars. |
| Theory vs notation | Select theory on **merits**; then show how method/notation serves it—not the reverse. **Notation or tool = vehicle**; contribution = **problem, concept, or guidance** advanced. |
| Agency | **Scholars** use theories; theories do not “speak” alone. **Models are instruments:** do not attribute agency to models (“the model mitigates…”); **people / analysts / organizations** act. |
| Conceptual / survey papers | Do not commit to one lens too early; map competing perspectives; **surface hidden assumptions** behind loaded terms (**autonomous**, **agentic**, **delegation**, **hybridity**, etc.). Distance from **hype labels** when the goal is durable conceptual contribution. **Neutralize premature judgment** in abstract/intro unless quoting. |
| Terminology | **Synonyms are the enemy** for core constructs (**Rivard**, in Baird workshop context): one label per idea unless a distinction is defined. **Every formal term needs a home:** cited source **or** explicit coinage (“what we term X”). **“Standard”** implies consensus—use only when defensible; else **existing**, **established**, or name specific approaches. |

### B.5 Audience and vocabulary

- **Engineer’s-eye test:** if a reviewer might ask “what is the concrete contribution?”, foreground **mechanism**, **artifact**, or **clear analytical move**.
- **Borrowed jargon** needs translation or trimming for engineering-heavy venues.
- Disambiguate terms that mean different things across fields (e.g. **binary**, **first-class**).
- **Related work:** prefer **complementarity** (“does not currently provide guidance for…”) over dismissal when leaving room for extension. **No false parallels** across fields. **Socio-technical** is broader than one modeling family—acknowledge wider HCI/CSCW where relevant.
- **Empirical honesty:** if the setting uses **conventional** methods, avoid implying cutting-edge capabilities the data do not support.

---

## Part C — Project lifecycle: milestones and P0 / P1 / P2

### C.1 Five milestones (general research paper development)

1. **Project memo** — Phenomenon, core tension, assumptions to interrogate, **early analytical questions** (often 2–3) to guide reading and snowballing, and snowball strategy for literature. Distance from buzzwords; focus **underlying** problem.
2. **Annotated references** — Each core source: strategic summary + **how it informs your tension/questions**; organize by tracks (Zotero, etc.).
3. **Structured outline** — Phenomenon, contested definitions, historical arc (continuity vs novelty), comparative axes, critique of borrowed frameworks, synthesis of open questions, conclusion (**survey papers** may stop short of a forced unified verdict).
4. **Paper draft** — Full argument; **attributive** voice (“Author X argues…”); **synthesis**, not serial book reports.
5. **Final paper** — Elaborate weak sections; tone and scope check; formatting and presentation.

**How memo questions relate to submission RQs:** The memo may hold **several exploratory questions** to structure literature work. The **submitted** paper should **converge**—see **§B.3**—so you do not promise more than you answer. **P0/P1** manuscripts use **characterization** and **handoff** language rather than final **P2** research problem labels (**§C.2**).

### C.2 P0 / P1 / P2 (problem-setting stages)

Apply checklist items **at the right stage**; the **authoritative long form** is `project_writing_style_checklist.md` (**Part 0** through **Part 4**).

| Stage | Deliverable (typical) | Introduction emphasis |
|-------|------------------------|------------------------|
| **P0** | Corpus + bullets/tags on problem phenomenon | Problem **phenomenon** + corpus; **no** demanding numbered RQs |
| **P1** | Characterization (dimensions, tensions, maps) | **Lenses/facets** organizing the phenomenon; still no premature P2 “resolution” |
| **P2** | Research problems **q1, q11, q21…** with technical alternatives | Explicit **RQs** and answerable commitments |

**Anti-patterns**

- Posing **answer-demanding RQs** in P0/P1 pulls the draft into the wrong register.
- **Three RQs in §1** when the paper is still **collecting/characterizing**.
- **Question-shaped section headings** that the corpus cannot answer—name the **gap** as finding and hand off to later work.
- P2 vocabulary (**resolution**, definitive **answers**) in a P0/P1 **conclusion**—use **refined problem statement**, **open questions**, **candidate q-items**.

**Forward-pointing handoff:** conclusions at P0/P1 should hand **candidate questions** to later stages without preempting P2 commitments.

---

## Part D — Paper structure and narrative (Sexton + Baird)

### D.1 Core arc

- **Need / gap / RQ** early (when at P2; at P0/P1, **phenomenon + characterization**).
- **Problem → development (analysis / evidence) → resolution** (answers at P2; refined problem + tensions at P1).
- Contribution should **emerge through** argument and evidence, not only be **declared** in the introduction.
- **~80%** of substance in the core (theory, analysis, results); **earned** conclusions; climax **answers** what was set up.

### D.2 Opening, title, roadmap

- **Informative title**; **concrete hook** or gap before dense background; short **roadmap** at end of introduction.
- **Show, then tell:** ground abstractions in **examples**; break long abstract runs with illustrations.
- **Cause and effect visible:** “therefore,” “because,” “as a result”; design choices **follow** from analysis—no unmotivated fixes.

### D.3 IS theory papers (when applicable) — five communicative goals

Draft **a couple of sentences per area** first (Baird worksheets in original JAIS appendices). Areas **need not** map 1:1 to sections.

| # | Area | Communicate |
|---|------|-------------|
| 1 | Area of theoretical focus | Target **IS subcommunity**; why topic is **helpful and interesting** |
| 2 | Relevant background | **Common ground**; current consensus / what is known |
| 3 | Theoretical tension | Why new theory is needed; prefer **assumption challenging** over **gap spotting** alone (e.g. heterogeneity where homogeneity assumed) |
| 4 | Resolution of tension | How theorizing resolves tension; **objective**; theory-building approach; **boundary conditions** |
| 5 | Guidelines for application | Steps for applying the work; **future RQs**; extensions (link to **discarded options**, not disconnected lists) |

**Theory paper drafting order (first draft):** middle out—**Background → Theory building → New theory**; then **Guidelines**, **Conclusion**, **Abstract**, **Introduction** last (quick intro stub OK early).

### D.4 Nine-step process (Baird, empirical & generalized)

1. **Core message** — Five areas (parallel to theory): focus, background, **tension** (most important for pull), resolution (objective, theory, methods highlights), **contribution** (second most important: moves consensus how?).
2. **Outline** mirroring **target journal** structure and limits.
3. **Intro bullets** — One per area; 2–3 sub-bullets → one paragraph each later.
4. **Literature synthesis table(s)** — Columns: **Research area | Description | Citations**; one synthesizing paragraph per row; **evidence-based editorial**, not fact list; **string citations** for stable consensus; **classics and recent**.
5. **Primary results** — Tables/figures (often ≤ ~5) **before** full narrative when possible; emulate **structure** of model papers, not text; theory/design/data/methods **aligned**; Results **factual** (interpretation mainly Discussion); **no surprise constructs** first appearing in Results.
6. **Discussion outline** — Contributions, limitations, future work; revisit analyses if needed; **no new near-synonym labels** late.
7. **Draft body** — Middle out; **agile** co-author iteration preferred.
8. **Abstract, Introduction, Discussion** — After core stable; **executive summaries**; **shorter sentences**; no **mystery** hiding contribution; align outline.
9. **Full tightening pass** — Cut extraneous; strengthen red thread; reread **multiple** times (Zinsser-style discipline); perfection not required in early passes.

### D.5 Reviewer-facing lenses (who / what / why / when / where / how)

- **Who / what:** Subcommunity and **message** to them—avoid “the entire IS field.”
- **Why:** Major choices (framework vs explanatory model, constructs vs alternatives, novelty); **trade-offs** at big decision points.
- **When / where:** **Boundary conditions** tied to assumptions challenged.
- **How:** **Application** guidance; future research linked to **paths not taken**.

### D.6 Literature review (synthesis norms)

- **Snowballing / surveys:** for broad or negative claims, anchor to **reviews or mapping studies**; replace “no method exists” with what **cited** evidence supports; state **coverage limits** honestly.
- **Rookie mistakes:** unrelated laundry lists; summaries **untied** to your tension/objective.

### D.7 Tips vs rookie mistakes (Baird quick reference)

| Tips | Rookie mistakes |
|------|-----------------|
| String citations for efficient background | Lit review = unrelated list |
| Tie summaries to purpose/tension | Study summaries orphaned from objective |
| Primary results stable before full draft | Surprise constructs in Results |
| Future research from guidelines & discarded options | Disconnected future-work list |
| Shorter sentences; early point in intro | Long chains; cliffhanger intro |

---

## Part E — Citations, typography, LaTeX

### E.1 Citations and numbers

- Numeric / first-citation bibliography order: **renumber** after edits when required by venue.
- Tie empirical prose to **canonical artifacts** (scripts, logs, reports) and reconcile before submission.

### E.2 Dashes and alternatives

- **Em-dash (—):** **sparingly**; prefer commas, colons, semicolons, parentheses, or new sentences. No stacked or nested em-dash pairs in one paragraph. In LaTeX, `---` is em-dash.
- **En-dash (–):** ranges, some compounds, author–date tables—per **house style**; not interchangeable with em-dash.
- **Hyphen (-):** standard compounds.

### E.3 LaTeX safety

- Preserve `\label`, `\ref`, `\cite`, math environments, and bibliography commands unless deliberately changing them.
- Avoid invasive `\documentclass` / package changes without instruction.

---

## Part F — Sentence and paragraph craft (Bacon synthesis)

### F.1 Stance

- Effectiveness **depends on context** (purpose, audience, neighboring sentences). Generate **options**, then **evaluate**.
- Academic prose often uses **abstract subjects**, **be**, and **passive** more than memoir—but **focus, balance, modification, variety** still matter.

### F.2 Focus and voice

- Readers expect **SVO**; first noun phrase gets attention—align with the **key player** when possible.
- **Dummy subjects** (*it*, *there*) often weaken verbs; **concrete subjects** often beat “there is/are” expletives.
- **Active default** when actor matters and clarity benefits; **passive** when actor is unknown/unimportant, **topic continuity** favors the patient, or **agency** of the subject should be stressed as absent.
- **Sharpening tips:** shorten **long subjects** or **invert**; uncover subjects **buried** after introductory phrases; replace **nominalizations** with verbs where it helps (*emphasis is placed* → *X emphasizes*). Discard a tip if it **harms** clarity or precision.

### F.3 Coordination and parallelism

- Coordinators: *and, or, nor, but, for, yet, so*—join **like** units; **parallel** grammar and **slot**.
- **Correlatives** (*both/and*, *not/but*, *either/or*, *not only/but also*): parallel branches; *not/but* stresses the second fork.
- Series length: 2–3 feels complete; 4+ long; 5+ can signal abundance/excess; omitting final conjunction can intensify list effects.
- **Repetition** of function words (e.g. repeated *about*, *no*) can aid **parsing** and **emphasis**.

### F.4 Modification

- **Periodic** (modifiers before main clause): suspense, logical stage-setting.
- **Cumulative** (main clause + trailing modifiers): **explicate and qualify** (Christensen); room to elaborate **before and after** the main clause.
- **Post-noun relatives:** mind **restrictive** vs **nonrestrictive** punctuation—commas **change meaning**. *That* / *which* / Ø per formality; preposition + relative → *which*. Reduce *who is / which is* when redundant.
- **Verbals:** *-ing*, *-ed*, *to-* phrases for simultaneity, state, purpose; watch **dangling** modifiers and **comma** attachment. **Appositives** and **absolutes** for definition, lists, scene-breaking.

### F.5 Special devices (use sparingly in academic prose)

- **Clefts** (*It was X who…*, *What X did was…*) for **targeted** emphasis.
- **Inversion** when fronting a **long subject** would blunt the verb.
- **Fragments** rare in academic writing; more allowable in narrative **quotes** or stylized passages if venue permits.
- **Variety:** mix length and structure; avoid monotonous **all-short** or **unbroken long** (risk of choppy vs dense). Rough benchmarks from craft guides: **~15–20** words average in some technical prose; **~25** in some academic/long-form; beware **60+** word sentences without relief.

**Full sentence checklist:** see `bacon_2009_well_crafted_sentence_guidelines.md` §10 and `project_writing_style_checklist.md` Part 3.

---

## Part G — Master checklists

### G.0 Severity tiers for joint-review prioritization

When reviewing with the full package, every violation found is tagged with a severity to guide remediation order. The tags are used consistently across the integrated checklist (`project_writing_style_checklist.md`), the orchestration runbook (`REVIEW_ORCHESTRATION.md`), and the deterministic pre-flight (`DETERMINISTIC_CHECKS.md`):

- **[BLOCKER]** — Structural or integrity failure. Must fix before submission. Examples: fabricated citation; surprise construct in Results; unsupported universal "cannot"; wrong register for stage (P2 RQs in a P0 paper); unresolved contradiction between two load-bearing theoretical commitments; title promise not paid off; untied construct provenance.
- **[MAJOR]** — Substantive weakness readers will notice. Fix if time permits before submission; definitely fix in revision. Examples: defensive abstract/limitations framing; unused analytical apparatus; deficit framing of other disciplines; citation supporting a different claim than the one beside it; missing hourglass shape.
- **[MINOR]** — Polish-level. Fix in the tightening pass; does not affect acceptance. Examples: em-dash count; sentence-length variety; parallel-structure tweaks; single `must` → `should` swap.

When severity is ambiguous, default **up** one level and note the uncertainty in the findings report.

### G.1 One-page pre-submission (cross-venue)

- [ ] No unsupported **cannot** / **must** / **comprehensively** / overstated **anticipate**.
- [ ] Comparison baseline **defined once**; later references are short pointers.
- [ ] Contributions **positive**; no apology list of omissions.
- [ ] External theories **drawn on**; home contribution clear; tool/language is **vehicle** unless the paper is **about** the notation.
- [ ] Models don’t **act**; people/organizations do.
- [ ] Audience vocabulary checked (engineering vs critical/social phrasing).
- [ ] Abstract hedged if exploratory or evidence narrow.
- [ ] Lit review **synthetic**; universal negatives match **cited** evidence.
- [ ] Key terms **consistent**; formal terms **attributed** or **coined**.
- [ ] Em-dashes **minimal**; punctuation **varied**.
- [ ] Citations **verified**; bib order correct if numeric.
- [ ] Response letter **opens strong**; disciplines named; collaborative tone.
- [ ] **Red thread** + **hourglass** clear; intro/discussion **executive**, not mystery novel.
- [ ] **No surprise constructs** in late sections; terminology stable (**synonyms enemy**).
- [ ] Sentence focus checked (**who does what**); passives purposeful; **parallelism** sound.
- [ ] **Ethics / data / availability** requirements for venue and institution met.
- [ ] **Humanness pass (A.4.2):** LLM-tic table swept; "not X but Y" ≤ 2; triadic-list density reduced; trailing add-on sentences cut or absorbed; glossary dumps deferred to point of use.
- [ ] **Humanness concept check (A.4.1) — conditional:** *applies only if* the work produces a formal artifact (persona, stakeholder model, eligibility rule, rubric, requirements diagram, training schema) that operationalizes human subjects **and** is used to justify decisions about them. When it applies, the question of *whose* humanness the formal categories encode is surfaced rather than naturalized. Otherwise mark **N/A**.
- [ ] **Full-package policy:** **§ Policy** completed—**G.4** sign-off (all seven component files, prescribed order) for this deliverable.

### G.4 Full-package completion sign-off

Use this table to certify that **every component source** was worked through before **final** submission (per **Policy**). Retain with the manuscript version ID or ticket.

| Step | Component file | Reviewed (Y/N) | N/A / notes |
|------|----------------|----------------|-------------|
| 1 | `general_research_project_guidelines.md` | | |
| 2 | `research_paper_writing_guidelines.md` | | |
| 3 | `baird_2021_writing_guidelines.md` | | |
| 4 | `bacon_2009_well_crafted_sentence_guidelines.md` | | |
| 5 | `Sexton_Fiction_to_Academic_Writing_Guide.md` | | |
| 6 | `CLAUDE.md` | | |
| 7 | `project_writing_style_checklist.md` (Parts 0–4) | | |
| 8.5 | `SAFEGUARD_LAYER.md` (Checks 1–6) | | |

**Reviewer / author:** _________________ **Date:** _________________

### G.2 Stage-aware checklist (excerpt)

**Authoritative expanded checklist:** `project_writing_style_checklist.md` — use **Parts 1–4** for section-by-section items (macro, meso, micro, Baird/IS). This master only summarizes.

**P0:** Phenomenon + corpus breadth; hidden-assumptions audit; **no** premature RQs; conclusion **hands forward**.  

**P1:** Characterization **honest** (sources vs own taxonomy); tensions surfaced; **no** false P2 **resolution**.  

**P2:** RQs **answerable**; tradeoffs vs alternatives explicit; guidelines/future work tied to **design choices**; Baird five elements satisfied where theory paper.

### G.3 Sexton-inspired narrative checklist

| Principle | Check |
|-----------|--------|
| One clear **need** | RQs or problem phenomenon stated appropriately for stage |
| Open with **impact** | Hook before dense background |
| **Show then tell** | Examples adjacent to major claims |
| **Concrete** | Named methods, cases, constructs |
| **Cause and effect** | Links explicit; choices motivated |
| **Voice** | Consistent register; varied length |
| **Title + roadmap** | Informative; reader oriented |
| **Middle ~80%** | Core developed; climax **earned** |
| **Theme through structure** | Takeaway clear in one sentence |

---

## Part H — Where to go deeper

- **Baird (2021) JAIS** — Appendices A–D (worksheets, outlines): see `baird_2021_writing_guidelines.md` and DOI **10.17705/1jais.00711**.
- **Bacon (2009)** — Full chapters, model texts, glossary; see `bacon_2009_well_crafted_sentence_guidelines.md`.
- **Sexton** — `Sexton_Fiction_to_Academic_Writing_Guide.md` (fiction source: McGraw-Hill).
- **Braverman (1974)** — *Labor and Monopoly Capital: The Degradation of Work in the Twentieth Century*. Monthly Review Press. Voice reference for Parts I and J (scholar-militant archetype).
- **Suchman (2007)** — *Human–Machine Reconfigurations: Plans and Situated Actions* (2nd ed.). Cambridge University Press. Voice reference for Parts I and J (scholar-interlocutor archetype).
- **Vidal (2022)** — *Management Divided: Contradictions of Labor Management*. Oxford University Press. DOI: `10.1093/oso/9780198795278.001.0001`. ISBN: 978-0-19-879527-8. Voice reference for Parts I and J (scholar-cartographer archetype; balanced paired construction; contradiction-mapping as conclusion).
- **Course / revision specifics** — Venue-specific supplements live in project folders (e.g. `CAiSE_Rev01/research_notes/`); migrate cross-venue lessons into this package.
- **Traceability** — Start from the **traceability matrix** at the top of this file whenever you update or audit the guide against the package.

---

## Part I — Writing with Humanness (lessons from Braverman, Suchman & Vidal)

Extracted from three model texts: **Harry Braverman**, *Labor and Monopoly Capital* (1974); **Lucy Suchman**, *Human–Machine Reconfigurations* (2007); and **Matt Vidal**, *Management Divided: Contradictions of Labor Management* (Oxford University Press, 2022). They embody three distinct "human" scholarly voices that together cover the useful range: militant verdict (Braverman), situated dialogue (Suchman), and contradiction-mapping (Vidal). The goal is not to imitate any one wholesale but to learn the moves that make academic prose sound like a person thinking, not a template being filled.

**Cross-reference.** Part I establishes the *stance* and *moves*; Part J handles the *sentence architecture* that makes each stance readable. Both parts complement **Part F** (Bacon synthesis — focus, balance, modification, variety) and **§A.4.2** (the LLM-tic table). Use them together: Bacon gives the structural rules for sentences; §A.4.2 catches the mechanical tells of machine prose; Parts I–J show what a human voice actually does with those rules. For the mechanical counts that enforce §A.4.2, run `DETERMINISTIC_CHECKS.md` §4 before any judgment pass.

### I.0 Rule of thumb — interlocutor voice for situated case papers *(unless stated otherwise)*

**When this applies:** Manuscripts that are **practitioner-informed**, **organizationally situated**, or **first-person reflective** within HCI, CSCW, IS-adjacent work, and comparable critical/STS-friendly venues—**unless** the call for papers, venue stylesheet, IRB template, or your advisor/instructor explicitly requires a different register (e.g. strictly anonymous third-person methods, legalistic consent boilerplate you must paste verbatim).

**Default:** Write in **Lucy Suchman–style scholar-interlocutor** prose as spelled out in **I.1–I.6** below: **first person** as a navigational handrail, **episodes** that show *how you know*, **dialogic** engagement with sources (their words in the room with yours), **scope-naming hedges** (“in the sense that…,” “for this site…”), and a visible **standpoint** (what you care about, what you cannot see, what would change your mind).

**Ethics and confidentiality through story, not contract:** When you must protect employers and participants, **say what you did in plain, situated language** (how you paraphrased, why names drop out, what you refused to ship into print). Do **not** default to dense legal-disclaimer sentences where a reader-oriented narration carries the same safeguards—unless a compliance office requires exact wording.

**If instructions conflict:** **Venue / advisor / instructor** wins over this rule of thumb.

### I.1 Three archetypes to keep in mind
- **The scholar-militant (Braverman).** Periodic sentences, moral seriousness, classical erudition, controlled indignation. Judgments are stated plainly; irony is dry and infrequent; footnotes lend weight to conviction. Use when the argument needs gravity and a clear verdict.
- **The scholar-interlocutor (Suchman).** First-person, reflexively situated, generous to opponents, hedges used as precision (not evasion), narrative framing of concepts through lived episodes. Use when the argument depends on *how* one knows, or when reconfiguring rather than denouncing.
- **The scholar-cartographer (Vidal).** First-person navigational; balanced paired construction ("On the one hand… on the other"); thesis stated plainly but framed as the *mapping* of an irreducible contradiction rather than its resolution. Quotes boosters and critics in their own words, then positions *beyond* both camps. Grounded in concrete institutional detail — named companies, dated episodes, specific workers — but refuses to pretend the tensions dissolve. Use when the argument needs a clear position **and** must honor a contradiction that cannot be synthesized away.

Most CAiSE/RE/IS papers should lean **Suchman or Vidal** — dialogic, situated, precise — while borrowing Braverman's willingness to state a thesis without flinching. Vidal is the right default when the piece concerns a structural tension that the author does not mean to resolve (e.g. autonomy vs. standardization, human oversight vs. AI initiative, discipline vs. empowerment); Suchman is the right default when the piece concerns how knowledge of a system was produced through situated engagement with it.

### I.2 Narrative techniques that signal a human author
1. **Tell the origin of the idea, not just the idea.** Suchman introduces "situated action" via the Xerox copier project: a delegation arrived, users struggled, she watched videotapes, and the concept emerged from the trouble. Vidal opens *Management Divided* by telling the reader he did not set out to study lean — he set out to study labor management and lean imposed itself on the field. Ground key constructs in the episode that made them necessary.
2. **Stage a dialogue, not a verdict.** Quote interlocutors in their own words, then reposition rather than refute. Vidal's "Boosters, Critics, and Beyond" section quotes Ohno, Liker, and Dennis (boosters) in their own language, then quotes Stewart and colleagues (critics), then says *"But my research demonstrates that lean is a management model which can be implemented in distinct ways"* — positioning beyond both camps without dismissing either. Disagreement as clarification of premises.
3. **Let worked examples carry theory.** Braverman's pin factory, Suchman's canoe through the rapids, Vidal's Metalfab Plus and his 52 interviewed workers — a single concrete image does more argumentative work than a paragraph of abstraction. Pair every major claim with a named case.
4. **Name the genealogy.** Smith → Babbage → Ure → Marx → Taylor (Braverman); Garfinkel → Agre → Brooks (Suchman); Taylor → Gilbreth → Ohno → Liker (Vidal). Situating a claim inside a lineage signals that the author has read, chosen, and positioned — not merely cited.
5. **Use asides and footnotes as a second voice.** Both Braverman and Suchman use footnotes for wry correction, concession, or digression. The main text stays disciplined; the margin allows humanity.
6. **Reflexive self-location.** "My project then became…" (Suchman); "I admit that the phrase was unfortunate." Vidal: *"When I entered the field in 2002 to study these questions, the received wisdom among sociologists… was — and perhaps still is — that there is no one best way."* Owning the trajectory of one's thinking, including wrong turns and dated premises, is the single most human move in academic prose.
7. **Name the contradiction rather than dissolve it.** Vidal's signature move: state the thesis as the *mapping* of an irreducible tension rather than its resolution. *"The thesis of this book is that the tension between ensuring worker discipline and harnessing worker creativity is one of the central dynamics shaping organizations today. This tension is the inevitable expression of a material contradiction inherent to the labor-management relation."* The author commits to a position **and** commits to the irreducibility. Use this when a paper's honest contribution is "here are the dimensions of a real tension that does not go away," not "here is the solution." It is the move that allows a conceptual paper to take a position without pretending to resolve what it cannot.

### I.3 Tone and voice moves
- **Vary sentence architecture.** Long periodic sentences for cumulative argument; short declarative ones for the verdict. Braverman: *"This might even be called the general law of the capitalist division of labor."* The short sentence lands *because* the preceding ones were long. See Bacon §§9.5 and F.5 (MASTER) for the distribution targets that make this rhythm achievable.
- **Balanced paired construction, then the pivot.** Vidal's most common opening move: *"On the one hand, they need to ensure that workers produce output… On the other hand, organizational success increasingly depends on the ability of managers to harness the creativity and initiative of workers."* The parallelism sets up the reader; the next sentence refuses to let the balance settle (*"But establishing a balance that includes some degree of both does not eliminate the underlying conflict…"*). The move is: symmetric setup → asymmetric verdict. Use it when you need the reader to feel the tension before you name it.
- **Hedge as precision, not timidity.** "At least with respect to," "in the sense that," "to my understanding." Hedges mark the *scope* of a claim, not retreat from it.
- **Refuse the god's-eye view.** Name your standpoint, disciplines, audience, and the limits of your access. Suchman: *"Inevitably, both my discussion… is partial at best, drawing selectively from those projects I have found most compelling."* Vidal: *"While my empirical case is the manufacturing sector in the US Midwest, my argument is not limited to manufacturing or to lean production."* Both moves own the empirical floor and the conceptual ceiling in the same sentence.
- **Moral seriousness without sentimentality.** Braverman defends workers without romanticizing them. Vidal notes matter-of-factly that some managers take "the easier path" and settle "to the detriment of organizational performance and worker well-being" — the ethical stake is visible but the sentence does not moralize. Critique should have a clear stake and refuse melodrama.
- **Wry understatement over heat.** "Herskovits here performs the customary economic miracle of transforming 'houses, canoes, or fish-weirs' into 'capital goods.'" Irony lands hardest when the surrounding prose is restrained.
- **Scare-quote with intent.** "Situated," "interactive," "free" labor (Suchman); *"settling for good enough"*, "no one best way" (Vidal). Quotation marks signal that a term is under interrogation, not merely in use. Do not overuse; each one should do work.

### I.4 Moves to avoid (the anti-human tells)
- Template openings ("In recent years, X has attracted growing attention…"). No human would begin a story this way.
- Uniform sentence length and shape across a section — a hallmark of machine prose.
- Synonymy drift (replacing "plan" with "strategy" with "scheme" purely to avoid repetition). Use the same word when you mean the same thing; variation should carry meaning.
- Hedging without scope ("somewhat," "rather," "arguably" sprinkled ornamentally). Each hedge must name *what* is limited.
- Passive agency when the author is present ("it was observed that…" when you mean "I found that…"). Suchman owns; Braverman owns. Own.
- Summary-only prose. Every major claim needs either a worked example, a quoted interlocutor, or a named case. Abstraction unaccompanied by friction reads as synthetic.
- Defensive responses to critique. Reframe instead — take the high ground, as both authors do with their misreaders.

### I.5 A working checklist before any paragraph is "done"
- Does the paragraph have a **concrete anchor** (a case, quote, episode, or named construct)?
- Is there at least **one sentence a person would actually say aloud**?
- Have I **located myself** (where needed) rather than writing from nowhere?
- Is my disagreement with others **dialogic**, not dismissive?
- Do sentences **vary** in length and shape, with at least one short declarative landing the point?
- Have I removed hedges that don't name their scope, and synonyms that don't carry meaning?
- Could a reader identify the **author's stake** — what I care about and why?

### I.6 Can I (Claude) actually write this way?
Yes, with discipline. The failure mode of machine-generated academic prose is fluency without friction: every sentence grammatical, every paragraph balanced, no anchor, no standpoint, no episode. The antidote is to borrow these authors' habits deliberately — lead with a case, name the lineage, own the first person, let footnotes carry the second voice, and refuse the neutral view from nowhere. Humanness in writing is not a style; it is the visible trace of someone having thought, chosen, and cared.

---

## Part J — Sentence Architecture (lessons from Braverman, Suchman & Vidal)

Braverman and Suchman are "difficult" in reputation but for different reasons. Vidal is *not* difficult — and that is itself instructive. The point is not that all three are hard to read, but that each *matches a sentence architecture to a reading mode*, and none of them lives in the gray middle zone where machine prose tends to drift.

**Cross-reference.** The structural rules behind these three architectures are in Bacon Ch 2 (well-focused sentences), Ch 3 (coordination and parallelism), Ch 4 (modification), and Ch 9 (sentence variety), summarized in MASTER **Part F**. Bacon tells you *what* the parts are and *how* they combine; Part J shows *which* combinations produce readable prose and *which* signal a person thinking.

### J.1 Braverman — long sentences, low parse complexity

**Shape.** Long (30–60 words), but linearly additive. Subject and verb arrive in the first seven words; every subsequent clause elaborates what the reader already knows. The reader is never holding a bracket open.

**Devices.**
- Early subject–verb anchoring.
- Parallel grammar as scaffolding ("to disregard… and to buy…").
- Colons and dashes as promise-keeping devices — the long run leads to a concrete payoff.
- Block quotations to offload other voices so his own remains unbroken.
- Short verdict sentences after long expository runs: "It is not 'pure technique' that concerns us, but rather the marriage of technique with the special needs of capital."

**Difficulty profile.** *High vocabulary, low parse complexity.* A reader may need a dictionary for "refractory" or "juridical," but the sentences themselves are oratorical — written to be read aloud. Difficulty is lexical and historical, not grammatical.

**Reading mode.** Forward momentum. Trust the parallelism; don't stop mid-clause.

### J.2 Suchman — shorter sentences, higher parse complexity

**Shape.** Often shorter than Braverman's, but structurally denser. The reader must hold multiple qualifications open at once. Example:

> "I take the boundaries between persons and machines to be discursively and materially enacted rather than naturally effected and to be available, for better and worse and with greater and lesser resistances, for refiguring."

The verb "to be" spans two complements; a three-part parenthetical interrupts before the final word "refiguring" — which is the sentence's actual point.

**Devices.**
- Nominalizations that carry theoretical work ("enactment," "refiguring," "configurations").
- Appositives and parentheticals mid-sentence, embedding a second claim inside the first.
- Scare quotes as silent footnotes — "situated," "interactive," "plans" — each signaling a term under interrogation.
- Scope-naming hedges ("at least," "to my understanding") that delay the predicate to specify exactly what is claimed.
- First person as navigational handrail: "I argued," "my concern was," "I admit that." Without it, her density would be opaque.

**Difficulty profile.** *Moderate vocabulary, high parse complexity.* Individual words are not obscure; syntactic density is. Her prose rewards rereading — not because it was written badly, but because each sentence is designed to survive multiple passes.

**Reading mode.** Patient recursion. Read one sentence at a time; follow the first person; notice the scare quotes.

### J.3 Vidal — medium sentences, low parse complexity, navigated by first person

**Shape.** Medium length (20–35 words), linearly additive like Braverman, but punctuated by short first-person interventions ("In my analysis," "my research demonstrates," "To be sure") that navigate the reader through the argument. Example:

> "In my analysis, lean reflects and intensifies a material contradiction that is inherent to the capitalist employment relation: the need to ensure discipline versus the need to harness the creativity of workers. The core argument of this book is that in facing the conflicting pressures generated by this contradiction, managers often satisfice—settle for good enough—rather than maximize profit, efficiency, labor control, or anything else."

The thesis is stated plainly ("The core argument of this book is that…"). The reader is never asked to hold a bracket open. The contradiction is named, not smuggled in.

**Devices.**
- Balanced paired construction as scaffolding ("On the one hand… On the other hand…"; "discipline (via standards…) and empowerment (via multiskilling…)"; "Boosters, Critics, and Beyond").
- Concessive turn: set up the symmetric balance, then pivot with "But" to name the irreducible remainder.
- First person as navigational handrail at key argumentative pivots: *"The thesis of this book is…," "In my analysis…," "To be sure…," "By contrast…"*. First person appears often but not everywhere — it marks the pivots, not every sentence.
- Named companies and dated episodes as concrete anchors (Toyota, AT&T, Xerox, IBM, HP, Kaiser Permanente; the 1970s, the Uddevalla factory, the 2002 fieldwork). Every abstract claim is paired with specific institutional detail within a paragraph or two.
- Quoted interlocutors followed by repositioning: quotes boosters (Ohno, Liker, Dennis), quotes critics (Stewart et al.), then places his own position beyond both camps.
- Short verdict sentences after balanced paragraphs: *"The present chapter presents key theoretical concepts and a brief historical sketch of labor management in American manufacturing, followed by an overview of my argument."* The short sentence is the handrail.

**Difficulty profile.** *Low vocabulary, low parse complexity.* Neither lexical difficulty nor syntactic density. Difficulty is entirely at the level of the **argument** — the reader must hold a contradiction open without hoping for synthesis. The sentences themselves are transparent; the conceptual work is what asks for care.

**Reading mode.** Forward walking. The first person tells you where you are in the argument; the paired construction tells you what the next pivot will be.

### J.4 Direct comparison

| Dimension | Braverman | Suchman | Vidal |
|---|---|---|---|
| Sentence length | Long (30–60 w) | Medium (20–40 w) | Medium (20–35 w) |
| Subject–verb distance | Short | Short, then embedded qualifications | Short |
| Parallelism | Structural | Paired with interruption | Structural (paired, symmetric, then pivot) |
| Nominalization density | Low — prefers verbs and agents | High — processes as nouns | Low — concrete institutional nouns and verbs |
| Parentheticals | Rare | Frequent | Moderate — mostly inline citations |
| Hedging | Minimal; verdicts stated plainly | Dense; hedges mark scope | Scope-naming hedges at transitions ("To be sure," "More commonly") |
| Scare quotes | Rare, pointed | Frequent, diagnostic | Moderate, pointed |
| First person | Almost absent | Pervasive, navigational | Periodic, navigational at pivots |
| Contradiction handling | Names it and takes a side | Reconfigures the terms | Names it and refuses to resolve |
| Reading mode | Oratorical (read aloud) | Recursive (read twice) | Forward walking (read once, slowly) |
| Primary difficulty | Lexical / historical | Syntactic / conceptual | Conceptual only (argument holds a tension open) |

### J.5 Why all three are readable

Each writer matches a reading mode to a prose architecture, and none of them occupies the gray zone of sentences that are long without being musical and qualified without being precise. Braverman achieves readability through **linear architecture and early anchoring**. Suchman achieves it through **first-person navigation and precise qualification**. Vidal achieves it through **balanced paired construction, plain verdicts, and concrete institutional anchors**. The gray middle — fluent, balanced, anchorless, standpoint-free — is where machine-generated text tends to live and is the thing to avoid.

**When to borrow which.** If the argument is a verdict that deserves gravity: Braverman. If the argument depends on how one came to know: Suchman. If the argument needs to name a real tension that does not dissolve: Vidal. Most working papers should borrow from two or three at once. The INF3001 essay in `examples/` uses Vidal's contradiction-mapping move with Suchman-style first-person navigation at the hinges.

### J.6 Practical rules for our own sentences

1. **Subject and verb by word 10.** If the main clause hasn't arrived, restructure. (Braverman's rule.)
2. **Parallelism as scaffolding, not ornament.** A list of three must be grammatically identical. (Vidal's balanced paired construction depends on this.)
3. **Earn every parenthetical.** Embedded qualifications must be load-bearing; no throat-clearing. (Suchman's rule.)
4. **Follow a long expository sentence with a short verdict.** Rhythm teaches the reader. (All three authors do this.)
5. **Nominalize only when the noun is doing conceptual work.** "Refiguring" earns its place; "the utilization of" does not.
6. **Let the first person navigate.** When density rises, "I argued" or "my concern is" is a free gift to the reader. (Suchman and Vidal, at different densities.)
7. **Scare-quote surgically.** Roughly one per paragraph, only for terms under interrogation.
8. **Trust the colon and the semicolon.** They are promise-keeping devices: used well, they tell the reader "the payoff is arriving now." (Prefer colons, semicolons, commas, or parentheses over em-dashes, per MASTER §E.2 and `DETERMINISTIC_CHECKS.md` §3.)
9. **Match difficulty to mode.** If the sentence is lexically hard, keep it grammatically simple; if it is grammatically dense, keep the vocabulary plain. Never stack both kinds of difficulty in the same sentence.
10. **If you are mapping a contradiction, honor it.** Don't close with false synthesis. A Vidal-style paper earns its conclusion by refusing to resolve the tension it has just traced.
11. **Read the paragraph aloud.** If you stumble, the reader will too; none of the three archetypes would let that stand.

---

*This file subordinates the eight Markdown files in this folder to a single hierarchy **for discovery**, but **completion** requires the **mandatory full-package review** (Policy + **G.4**). If a conflict arises between this master and a **venue** author guide, follow the venue. If this master conflicts with an **advisor’s** explicit instruction, follow the advisor. If this master conflicts with a **component `.md`**, the component file is authoritative until the master is reconciled. For a single rule’s exact provenance, open the **source file** named in the traceability matrix.*
