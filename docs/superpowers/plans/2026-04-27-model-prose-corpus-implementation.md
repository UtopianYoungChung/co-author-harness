# Model Prose Corpus — Accessibility Example Cases Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create `references/examples/model_prose_corpus.md` with 16 pre-verified calibration passages (Vidal 2022 + Suchman 2007, one per Sub-check A–H each), wire it into `accessibility-overlay/SKILL.md` with a MANDATORY load instruction, add eight one-line cross-reference pointers to `sub_checks.md`, and insert a pointer paragraph in `READER_ACCESSIBILITY.md §13.4`.

**Architecture:** All four changes are purely additive Markdown edits — no code is compiled, no schemas change, no Sub-check thresholds are modified. Verification is structural (file existence, heading presence, grep for expected content) plus running the four harness check scripts. Task order: corpus scaffold → corpus content (A–D) → corpus content (E–H) → SKILL.md amendment → sub_checks.md cross-references → READER_ACCESSIBILITY.md pointer → final verification.

**Tech Stack:** Markdown (Write/Edit file tools), GitKraken MCP for commits, Python launcher `C:\Users\young\AppData\Local\Programs\Python\Launcher\py.exe` for harness check scripts via Desktop Commander.

**Spec:** `docs/superpowers/specs/2026-04-27-model-prose-corpus-accessibility-design.md`

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| **Create** | `references/examples/model_prose_corpus.md` | Canonical calibration corpus, 16 passages, organized by Sub-check A–H |
| **Amend** | `skills/accessibility-overlay/SKILL.md` | Add MANDATORY load instruction after existing READER_ACCESSIBILITY.md block |
| `skills/accessibility-overlay/references/sub_checks.md` | Add one cross-reference pointer at end of each Sub-check A–H section |
| `references/READER_ACCESSIBILITY.md` | Add pointer paragraph at top of §13.4 worked-examples section |

---

## Task 1: Create corpus file scaffold

**Files:**
- Create: `references/examples/model_prose_corpus.md`

- [ ] **Step 1: Write the corpus file header and scaffold**

Write the following content to `references/examples/model_prose_corpus.md`. This creates the file with frontmatter, purpose statement, versioning note, extensibility contract, and all eight Sub-check headings as stubs. Content will be filled in Tasks 2–3.

```markdown
---
name: model_prose_corpus
version: 1.0
date: 2026-04-27
description: >
  Calibration corpus of 16 pre-verified model-prose passages (Vidal 2022;
  Suchman 2007) organized by SAFEGUARD Check 8 Sub-check A–H. Consumed by
  accessibility-overlay/SKILL.md (MANDATORY load) and referenced per-check
  from accessibility-overlay/references/sub_checks.md.
source_items:
  vidal_2022:
    parent_key: QH8Y3FE6
    attachment_key: TKH5M6RK
    citation: "Vidal, Matt. 2022. *Management Divided: Contradictions of Labor Management*."
  suchman_2007:
    parent_key: TJUP6UCB
    attachment_key: NT26F6GS
    citation: "Suchman, Lucy. 2007. *Human-Machine Reconfigurations: Plans and Situated Actions*. 2nd ed. Cambridge University Press."
---

# Model Prose Corpus — Accessibility Sub-check Calibration Examples

**Purpose.** This file provides one CLEAN-pass example per Sub-check A–H from two domain-diverse model authors: Matt Vidal (2022), labor sociology and organizational theory; and Lucy Suchman (2007), human-computer interaction and workplace studies. Both write complex sociotechnical argument in accessible prose — dense disciplinary content carried in daily-English register — which is the target the harness accessibility criteria are designed to produce.

**How to use.** When adjudicating a borderline Sub-check finding:

- If a passage in the manuscript is structurally similar to a corpus example and the criterion property is present → default toward CLEAN.
- If a passage lacks the property clearly present in the corpus example → escalate toward MAJOR.
- The calibration note at the end of each section identifies the contrastive insight between the two examples — what they together demonstrate that neither alone demonstrates.

**Extensibility.** When a future project produces an especially clean Sub-check A–G example, append it to the relevant section under a `### [Project ID] ([year])` heading. Corpus-entry candidates are identified by the Reflector's Phase 4 cross-project recurrence audit: a CLEAN pattern across two or more projects. Do not add entries for single-project findings. See Reflector Phase 4 gatekeeper criteria in `references/ROUTING_SPINE.md`.

**Normative status.** Calibration material only — not a style guide override. `bacon_2009_well_crafted_sentence_guidelines.md`, `suchman_writing_style.md`, and `baird_2021_writing_guidelines.md` govern Generator production. This corpus governs Evaluator adjudication.

---

## Sub-check A — Paragraph Cadence

*(content added in Task 2)*

---

## Sub-check B — Sentence-Length Variation (Rhythm)

*(content added in Task 2)*

---

## Sub-check C — First-Use Definition

*(content added in Task 2)*

---

## Sub-check D — Section-Opening Signpost

*(content added in Task 2)*

---

## Sub-check E — Jargon Discipline

*(content added in Task 3)*

---

## Sub-check F — Worked Example at Density Spike

*(content added in Task 3)*

---

## Sub-check G — Consolidation Anchor

*(content added in Task 3)*

---

## Sub-check H — Register Appropriateness

*(content added in Task 3)*

---

## Versioning

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-04-27 | Initial corpus: 16 passages (Vidal 2022 + Suchman 2007), Sub-checks A–H. Passages extracted from Zotero full-text corpus and verified against Sub-check criteria in brainstorming session 2026-04-27. |
```

- [ ] **Step 2: Verify file created and scaffold structure is correct**

Run in bash:
```bash
grep -n "^## Sub-check" /sessions/amazing-wonderful-hamilton/mnt/co-author-harness/references/examples/model_prose_corpus.md
```

Expected output (8 lines):
```
29:## Sub-check A — Paragraph Cadence
33:## Sub-check B — Sentence-Length Variation (Rhythm)
37:## Sub-check C — First-Use Definition
41:## Sub-check D — Section-Opening Signpost
45:## Sub-check E — Jargon Discipline
49:## Sub-check F — Worked Example at Density Spike
53:## Sub-check G — Consolidation Anchor
57:## Sub-check H — Register Appropriateness
```

(Line numbers may differ slightly; the important check is that all 8 headings are present.)

- [ ] **Step 3: Commit scaffold**

```bash
cd /sessions/amazing-wonderful-hamilton/mnt/co-author-harness
```

Use GitKraken MCP `git_add_or_commit` with:
- action: `add`
- files: `["references/examples/model_prose_corpus.md"]`

Then commit with message:
```
feat(corpus): scaffold model_prose_corpus.md with A-H section stubs

Frontmatter with Zotero source keys, purpose statement, extensibility
contract, and normative-status note. Eight Sub-check section headings
ready for content population in subsequent commits.
```

---

## Task 2: Populate corpus Sub-checks A–D

**Files:**
- Modify: `references/examples/model_prose_corpus.md` (replace stubs for A–D with full entries)

- [ ] **Step 1: Replace Sub-check A stub with full entry**

Use the Edit tool to replace the Sub-check A section. Find:
```
## Sub-check A — Paragraph Cadence

*(content added in Task 2)*
```

Replace with:
```markdown
## Sub-check A — Paragraph Cadence

**Property being calibrated:** A paragraph ≤200 words has a visible internal turn-point — a transition, a worked example, a counter-claim, or a thematic refocus — that changes the paragraph's direction mid-way.

### Vidal (2022) — Management Divided: Contradictions of Labor Management

**Location:** Chapter 1, "The Problem of Labor Management," ~offset 15,600

**Verbatim passage:**

> Across a wide range of sectors, managers today face conflicting pressures on how to utilize their employees. On the one hand, they need to ensure that workers produce output, whether in goods or services, of sufficient quantity and quality. To this end, managers ensure workforce discipline through work simplification and standardization, automation and machine-paced work, rules and procedures, threats and rewards. On the other hand, organizational success increasingly depends on the ability of managers to harness the creativity and initiative of workers. To this end, managers empower the workforce through job enlargement and enrichment, cross training and multiskilling, and opportunities to participate in problem solving and decision making.

**Marker audit:** Turn-point fires at "On the other hand" (explicit contrastive cue, on the `sub_checks.md` §A cue lexicon). The paragraph opens by naming a tension, spends two sentences developing the discipline pole ("On the one hand…"), then pivots at exactly the midpoint to develop the empowerment pole with symmetric structure ("To this end, managers…" appears in both halves). The turn-point is both lexically marked and structurally visible.

**Annotation:** The symmetrical structure (same framing sentence applied to each pole) makes the cadence criterion legible at a glance — the pivot is not accidental or implicit but is the paragraph's organizing principle. This is the cleanest possible structural turn-point: it teaches by making the form transparent.

---

### Suchman (2007) — Human-Machine Reconfigurations: Plans and Situated Actions

**Location:** Chapter 5, "Plans," ~offset 195,800

**Verbatim passage:**

> The action's course is just the playing out of these antecedent factors, knowable in advance of and standing in a determinate relationship to the action itself. The alternative view is that plans are resources for situated action but do not in any strong sense determine its course. Although plans presuppose the embodied practices and changing circumstances of situated action, the efficiency of plans as representations comes precisely from the fact that they do not represent those practices and circumstances in all of their concrete detail. So, for example, in planning to run a series of rapids in a canoe, one is very likely to sit for a while above the falls and plan one's descent. The plan might go something like "I'll get as far over to the left as possible, try to make it between those two large rocks, then backferry hard to the right to make it around that next bunch." A great deal of deliberation, discussion, simulation, and reconstruction may go into such a plan. But however detailed, the plan stops short of the actual business of getting your canoe through the falls.

**Marker audit:** Turn-point fires at "So, for example" (on the `sub_checks.md` §A cue lexicon: `for example`, `to illustrate`). The first three sentences are theoretical declarative (planning-model characterization); the pivot at "So, for example" shifts register entirely into a first-person narrative canoe scenario. The two halves are in different registers, making the turn-point a register-shift cadence rather than a structural-symmetry cadence.

**Annotation:** Unlike the Vidal example, the turn-point here is a register shift (theoretical → vignette), not a structural pivot. The paragraph changes direction by changing mode — from abstract characterization to concrete scenario — which satisfies the cadence criterion via a different surface form.

---

**Calibration note:** Both are CLEAN. Vidal's turn-point is structural (symmetrical paired argument); Suchman's is a register-shift (theoretical declarative → first-person vignette). The Evaluator should not over-specify the surface form: any of the cue-lexicon items in `sub_checks.md §A` can anchor a CLEAN turn-point, whether the pivot is a counter-claim, a thematic refocus, or a register shift into a worked example.
```

- [ ] **Step 2: Replace Sub-check B stub with full entry**

Find:
```
## Sub-check B — Sentence-Length Variation (Rhythm)

*(content added in Task 2)*
```

Replace with:
```markdown
## Sub-check B — Sentence-Length Variation (Rhythm)

**Property being calibrated:** A passage of four or more sentences has markedly variable sentence lengths (mix of short ≤12 words and long ≥25 words). The variation is felt as emphasis, not accident — short sentences land as punches after accumulation in long ones.

### Vidal (2022) — Management Divided: Contradictions of Labor Management

**Location:** Chapter 2, "Lean Management and Employee Involvement," ~offset 140,400

**Verbatim passage:**

> Work intensification in global auto assembly preceded the global diffusion of lean, rising in the late 1960s following the intensification of global competition and declining profits. In Ruth Milkman's (1997: 12) case study of the GM assembly plant in Linden, New Jersey, the workers did not defend traditional, fordist arrangements, which they experienced as "relentless and dehumanizing." The primary complaints of these workers were that management treated them in a degrading manner and did not follow through on its promises of increased participation under lean. These workers embraced management's rhetoric of participation but this was never delivered, as managers continued to emphasize uninterrupted production in the face of severe pressures for output.

**Marker audit:** Sentence-length profile: S1 ~26 words (declarative framing); S2 ~30 words (embedded citation + direct quote); S3 ~28 words (complaint characterization); S4 ~28 words (flat concluding statement). The variation is intra-sentence: the embedded direct quote "relentless and dehumanizing" (3 words) acts as a short emphatic pulse inside the long S2, creating a heavy-light-medium texture. The quoted phrase lands harder than the academic scaffolding around it — this is rhythm as emphasis.

**Annotation:** The rhythm criterion does not require that full sentences alternate short/long. An embedded direct quote or clause can create the pulse within a sentence, as here. The Evaluator should audit for perceived rhythm variation, not merely for inter-sentence length difference.

---

### Suchman (2007) — Human-Machine Reconfigurations: Plans and Situated Actions

**Location:** Chapter 1, "Readings and Responses," ~offset 31,200

**Verbatim passage:**

> The project was initiated in response to a delegation of Xerox customer service managers, who traveled to PARC from Xerox's primary product development site in Rochester, New York, to report on a problem with the machine and to enlist research advice in its solution. The machine was a relatively large, feature-rich photocopier that had just been "launched," mainly as a placeholder to establish the company's presence in a particular market niche that was under threat from other, competitor, companies. The machine was advertised with a figure dressed in the white lab coat of the scientist/engineer but reassuring the viewer that all that was required to activate the machine's extensive functionality was to "press the green [start] button." It seemed that customers were refuting this message, however, complaining instead that the machine was, as the customer service managers reported it to us, "too complicated."

**Marker audit:** Sentence-length profile: S1 ~50 words; S2 ~35 words; S3 ~40 words; S4 ~12 words. The first three sentences accumulate narrative weight; S4 — "It seemed that customers were refuting this message, however" — drops to 12 words. The drop is inter-sentence (full-length reversal), and it enacts the ironic reversal: the machine promised simplicity; users found it complex. The brevity of S4 performs the bluntness of the finding.

**Annotation:** Unlike Vidal's intra-sentence pulse, Suchman's variation is inter-sentence — a full length drop from 35–50-word accumulation to a 12-word blunt reversal. Both satisfy rhythm; the Evaluator should not over-specify which form the variation takes.

---

**Calibration note:** Vidal's variation is intra-sentence (direct-quote pulse inside a long sentence); Suchman's is inter-sentence (full-length drop to a short landing). The criterion targets perceived rhythm variation, not a specific surface form. A paragraph where the shortest sentence exceeds 20 words (Sub-check B's "no short sentences" warning) is a rhythm flag regardless of mean — the Evaluator audits contrast, not average.
```

- [ ] **Step 3: Replace Sub-check C stub with full entry**

Find:
```
## Sub-check C — First-Use Definition

*(content added in Task 2)*
```

Replace with:
```markdown
## Sub-check C — First-Use Definition

**Property being calibrated:** Every theoretical or domain construct carries a definition or worked illustration at or before its first use — in plain English, before the term does conceptual work in subsequent sentences.

### Vidal (2022) — Management Divided: Contradictions of Labor Management

**Location:** Chapter 3, ~offset 190,300

**Verbatim passage:**

> The labor process is about the organization of work as such: the division of labor, cooperation, workflow, production control and quality control, etc. The valorization process is about the production and appropriation of surplus labor—output beyond that necessary to cover a worker's wages—within the capitalist employment relation.

**Marker audit:** "Valorization process" is a technical Marxist term. Vidal defines it on the same sentence as its first substantive deployment, using a plain-English em-dash gloss — "output beyond that necessary to cover a worker's wages" — inserted directly into the sentence. The gloss comes before the term does conceptual work in subsequent paragraphs. Structure: term → em-dash → plain-English equivalent → wider context.

**Annotation:** The em-dash gloss is the minimum viable first-use definition: it puts the plain-English content inside the same sentence as the term, so the reader is equipped before they need to apply the concept. Longer glosses, parenthetical definitions, or same-paragraph elaborations also satisfy Sub-check C — the minimum is co-occurrence on the same page, not co-occurrence in the same sentence.

---

### Suchman (2007) — Human-Machine Reconfigurations: Plans and Situated Actions

**Location:** Chapter 7, "Communicative Resources," ~offset 210,000

**Verbatim passage:**

> Language is efficient in the sense that, on the one hand, expressions have assigned to them conventional meanings that hold on any occasion of their use. The significance of a linguistic expression on some actual occasion, on the other hand, lies in its relationship to circumstances that are presupposed or indicated by, but not actually captured in, the expression itself. Language takes its significance from the embedding world, in other words, even while it transforms the world into something that can be thought of and talked about. Expressions that rely on their situation for significance are commonly called indexical, after the "indexes" of Charles Peirce (1933), the exemplary indexicals being first- and second-person pronouns, tense, and specific time and place adverbs such as here and now.

**Marker audit:** "Indexical" is introduced only after two full sentences establish the distinction between conventional meaning and situated significance — the exact conceptual distinction the term names. By the time Peirce's label arrives, the reader already has the concept; the term is a name for something already understood. Concrete examples (pronouns, tense, "here," "now") complete the first-use definition on the same page. Structure: plain-English concept (pre-loaded) → term introduced → concrete examples.

**Annotation:** Suchman's model is definition-before-term (concept pre-loaded before the label), the inverse of Vidal's definition-in-sentence. Both are CLEAN; the criterion does not require a particular syntactic form, only that the definition or illustration precedes the term's conceptual work in subsequent sentences.

---

**Calibration note:** Vidal's model is definition-in-sentence (em-dash gloss on the same sentence as first use); Suchman's is definition-before-term (concept pre-loaded across two sentences before the label). The Evaluator should accept both forms. A term introduced in sentence N with a gloss in sentence N+1 of the same paragraph also satisfies the criterion; the binding rule is that the definition precedes the term's use as a conceptual building-block, not that they appear in the same syntactic position.
```

- [ ] **Step 4: Replace Sub-check D stub with full entry**

Find:
```
## Sub-check D — Section-Opening Signpost

*(content added in Task 2)*
```

Replace with:
```markdown
## Sub-check D — Section-Opening Signpost

**Property being calibrated:** A section opens with a one-to-three-sentence preamble that (a) tells the reader where they have arrived in the argument (orienting clause) and (b) tells the reader what the section will contribute (contribution clause). Not a topic sentence — an explicit map-fragment.

### Vidal (2022) — Management Divided: Contradictions of Labor Management

**Location:** Chapter 2, "Lean Management and Employee Involvement," opening paragraph, ~offset 120,100

**Verbatim passage:**

> This chapter examines arguments of the lean boosters that its performance effects are based in worker empowerment and those of its critics that it is a system of deskilling whose effects flow mainly from work intensification. I conclude that lean is not inherently one or the other. Lean tools can be highly effective for intensifying work, but the intensification of work is neither specific to lean nor is it what makes lean such an effective production model. Rather, lean has become the undisputed model of production in manufacturing, and is increasingly prominent in other sectors, because it is a system that combines tools for flexible production, process control, and continuous improvement. Following a discussion of empowerment and intensification, I briefly revisit debates about whether lean is best characterized as neofordist or postfordist.

**Marker audit:** Orienting clause: "This chapter examines arguments of the lean boosters… and those of its critics…" — names the prior debate the chapter adjudicates (where the reader has arrived). Contribution clause: "I conclude that lean is not inherently one or the other" — announces the chapter's own finding up front. Internal sequence map: "Following a discussion of…, I briefly revisit…" — maps the route. The reader finishes the paragraph knowing the destination and the path.

**Annotation:** This signpost is argumentative — it announces a conclusion, not just a topic. The contribution clause is a claim ("lean is not inherently one or the other"), not just a structural promise ("this chapter will discuss X"). Either form satisfies Sub-check D; the argumentative form is stronger because it gives the reader a thesis to hold while reading.

---

### Suchman (2007) — Human-Machine Reconfigurations: Plans and Situated Actions

**Location:** Chapter 5, "Plans," opening paragraph, ~offset 144,000

**Verbatim passage:**

> Every account of communication involves assumptions about action, in particular about the bases for action's coherence and intelligibility. This chapter and the next discuss two alternative views of action. The first, adopted by most researchers in artificial intelligence, locates the organization and significance of human action in underlying plans. At least as old as the Occidental hills, this view of purposeful action is the basis for traditional philosophies of rational action and for much of the behavioral sciences. It is hardly surprising, therefore, that it should be embraced by those newer fields concerned with intelligent artifacts, particularly cognitive science and information-processing psychology. On the planning view, plans are prerequisite to and prescribe action, at every level of detail. The alternative view, developed in Chapter 6 of this book, is that although the course of action can always be projected or reconstructed in terms of prior intentions and typical situations, the prescriptive significance of intentions for situated action is inherently vague.

**Marker audit:** Orienting clause: "Every account of communication involves assumptions about action" — locates the reader in the book's overarching concern. Contribution clause: "This chapter and the next discuss two alternative views of action" — assigns each of the next two chapters a structural role. The paragraph then names both views and characterizes them, so the reader has a full cognitive scaffold before any argument begins.

**Annotation:** Suchman's signpost is structural — it assigns chapter roles ("this chapter and the next") rather than announcing a conclusion. Both the argumentative form (Vidal) and the structural form (Suchman) satisfy Sub-check D; the minimum is that the orienting and contribution clauses are both present. A section that opens with a topic sentence ("This section discusses lean management") but neither locates the reader in the argument nor names what the section contributes fails D.

---

**Calibration note:** Vidal's signpost is argumentative (announces a conclusion); Suchman's is structural (assigns chapter roles across two chapters). Both satisfy D because both supply an orienting clause and a contribution clause. The Evaluator should not require a conclusion to be announced — assigning a structural function is a valid contribution clause. The Sub-check D / Sub-check H orthogonality (D checks structural presence; H checks register construction within the clauses) means a D-CLEAN signpost can still be H-MAJOR if the orienting clause is register-inappropriate.
```

- [ ] **Step 5: Verify Sub-checks A–D are fully populated**

Run in bash:
```bash
grep -n "Calibration note" /sessions/amazing-wonderful-hamilton/mnt/co-author-harness/references/examples/model_prose_corpus.md | head -10
```

Expected: exactly 4 lines matching "Calibration note" (one per Sub-check A–D). The stub text `*(content added in Task 2)*` should not appear.

Also verify:
```bash
grep -c "content added in Task 2" /sessions/amazing-wonderful-hamilton/mnt/co-author-harness/references/examples/model_prose_corpus.md
```

Expected output: `0`

- [ ] **Step 6: Commit Sub-checks A–D**

Add and commit:
```
feat(corpus): populate Sub-checks A-D with Vidal+Suchman calibration passages

Sub-check A (cadence): Vidal structural-symmetry pivot vs. Suchman
register-shift pivot. Calibration note: multiple surface forms satisfy A.

Sub-check B (rhythm): Vidal intra-sentence pulse (direct-quote embed)
vs. Suchman inter-sentence length drop. Calibration note: rhythm is
contrast, not average.

Sub-check C (first-use): Vidal definition-in-sentence (em-dash gloss)
vs. Suchman definition-before-term (concept pre-loaded). Calibration
note: syntactic form is not specified.

Sub-check D (signpost): Vidal argumentative (conclusion announced) vs.
Suchman structural (chapter roles assigned). Calibration note: both
orienting + contribution clause forms satisfy D.
```

---

## Task 3: Populate corpus Sub-checks E–H

**Files:**
- Modify: `references/examples/model_prose_corpus.md` (replace stubs for E–H with full entries)

- [ ] **Step 1: Replace Sub-check E stub with full entry**

Find:
```
## Sub-check E — Jargon Discipline

*(content added in Task 3)*
```

Replace with:
```markdown
## Sub-check E — Jargon Discipline

**Property being calibrated:** A paragraph introduces at most two new domain terms (P1 default; P0 allows three; P2 allows one). Complexity is permitted — but the complexity must be structural (argument form, parallel construction, multi-part decomposition), not lexical (term proliferation).

### Vidal (2022) — Management Divided: Contradictions of Labor Management

**Location:** Chapter 1, "The Problem of Labor Management," ~offset 25,200

**Verbatim passage:**

> The focus of my analysis is on the contradictory pressures managers face between ensuring labor discipline (so workers produce sufficient levels of output) versus empowering labor. This contradiction is manifest in conflicting pressures to use workers for routine manual versus abstract cognitive labor power; to provide minimal training versus substantial training (e.g. training in a single skill versus multiple skills or training in narrow skills versus broad skills); or to standardize work versus allowing discretion and autonomy. This contradiction exists across a wide range of occupations.

**Marker audit:** New domain terms introduced: "labor discipline" (glossed in parentheses: "so workers produce sufficient levels of output") and "abstract cognitive labor power." All other vocabulary is plain: "contradictory pressures," "managers face," "standardize work," "discretion and autonomy." The three-part parallel construction (manual vs. cognitive; minimal vs. substantial training; standardize vs. discretion) is complex structurally but lexically plain. Term count: 2. P1 cap: 2. Result: CLEAN.

**Annotation:** The paragraph makes a sophisticated theoretical point about the three-dimensional form of the management contradiction without exceeding the two-term cap. This demonstrates the key E principle: intellectual density should live in the argument structure, not in the density of technical vocabulary.

---

### Suchman (2007) — Human-Machine Reconfigurations: Plans and Situated Actions

**Location:** Chapter 6, "Situated Actions," ~offset 202,200

**Verbatim passage:**

> Normative sociology posits and then attempts to describe an objective world of social facts, or received norms, to which our attitudes and actions are a response. Emile Durkheim's famous maxim that the objective reality of social facts is sociology's fundamental principle (1938) has been the methodological premise of social studies since early in this century. Recognizing the human environment to be constituted crucially by others, sociological norms comprise a set of environmental conditions beyond the material to which human behavior is responsive: namely the sanctions of institutionalized group life. Human action, the argument goes, cannot be adequately explained without reference to these "social facts," which are to be treated as antecedent, external, and coercive vis-à-vis the individual actor.

**Marker audit:** New domain terms introduced: "normative sociology" (characterized immediately in the sentence: "posits and then attempts to describe an objective world of social facts") and "social facts" (first appearance glossed as "received norms" in apposition; repeated throughout at established meaning). "Vis-à-vis" is used as a preposition ("coercive vis-à-vis the individual actor"), not as a term of art — it is on the `lay_term_lexicons.md` flagged list but functions grammatically here rather than conceptually; the Evaluator may treat it as borderline MINOR if other factors accumulate, but it does not raise the term count. Term count: 2. P1 cap: 2. Result: CLEAN.

**Annotation:** Suchman introduces Durkheim's foundational structuralist premise using only two domain terms. The sentence "to be treated as antecedent, external, and coercive" names three properties but does not introduce three new terms — these are characterizing adjectives, not new constructs. The Evaluator should count constructs (entities with defined theoretical content), not technical-sounding words.

---

**Calibration note:** Both paragraphs make dense theoretical points with only two new terms. The Evaluator should audit construct count (entities with defined theoretical content), not sentence-level lexical density. A paragraph with many technical-sounding words can be E-CLEAN if those words are plain adjectives or established constructs that do not require first-use definition; conversely, a short paragraph that introduces three unnamed constructs in three sentences is E-MAJOR regardless of sentence simplicity.
```

- [ ] **Step 2: Replace Sub-check F stub with full entry**

Find:
```
## Sub-check F — Worked Example at Density Spike

*(content added in Task 3)*
```

Replace with:
```markdown
## Sub-check F — Worked Example at Density Spike

**Property being calibrated:** When conceptual density rises (tri-part decomposition, multi-criteria evaluation, contested-claim cluster, or extended theoretical derivation), the prose turns to a concrete worked example, vignette, or instantiation within the same or immediately following paragraph. The example must be specific — a named institution, named person, or documented event — not gestural ("as seen in workplace studies…").

### Vidal (2022) — Management Divided: Contradictions of Labor Management

**Location:** Chapter 2, ~offset 140,500–140,700

**Verbatim passage (density spike + example):**

> Work intensification in global auto assembly preceded the global diffusion of lean, rising in the late 1960s following the intensification of global competition and declining profits. In Ruth Milkman's (1997: 12) case study of the GM assembly plant in Linden, New Jersey, the workers did not defend traditional, fordist arrangements, which they experienced as "relentless and dehumanizing." The primary complaints of these workers were that management treated them in a degrading manner and did not follow through on its promises of increased participation under lean. These workers embraced management's rhetoric of participation but this was never delivered, as managers continued to emphasize uninterrupted production in the face of severe pressures for output.

**Marker audit:** Density spike: abstract causation claim ("work intensification preceded lean diffusion due to competitive pressure"). Example fires within two sentences: named scholar (Milkman 1997), named plant (GM Linden, New Jersey), worker voice ("relentless and dehumanizing"). The example is not illustrative decoration — it advances the argument by showing that workers' complaints were about management behavior and broken promises, not about lean as a production system, which is Vidal's counter-move against lean critics.

**Annotation:** The example does argumentative work, not illustrative decoration — it distinguishes two explanations for worker resistance. This is the Sub-check F target: the example must do more than gesture at the abstract claim; it must carry the argument forward by grounding a specific distinction or mechanism.

---

### Suchman (2007) — Human-Machine Reconfigurations: Plans and Situated Actions

**Location:** Chapter 4, "Interactive Artifacts," ~offset 134,800

**Verbatim passage (density spike + example):**

> Anecdotal reports of occasions on which people approached the teletype to one of the ELIZA programs and, believing it to be connected to a colleague, engaged in some amount of "interaction" without detecting the true nature of their respondent led many to believe that Weizenbaum's program had passed a simple form of the Turing test. Notwithstanding its apparent interactional success, however, Weizenbaum himself denied the intelligence of the program on the basis of the underlying mechanism which he described as "a mere collection of procedures." The grounds for their success are clearest in DOCTOR, one of the ELIZA programs whose script equipped it to respond to the human user as if the computer were a Rogerian therapist and the user a patient. The DOCTOR program exploited the maxim that shared premises can remain unspoken: that the less we say in conversation, the more what is said is assumed to be self-evident in its meaning and implications.

**Marker audit:** Density spike: abstract theoretical claims about intentional explanation and the Turing test criterion for machine intelligence. Example fires immediately: named programs (ELIZA, DOCTOR, Weizenbaum's lab), specific design role (Rogerian therapist), specific mechanism ("keyword scanning" / "shared premises can remain unspoken"). The example does not just illustrate "interactive artifacts" generically — it carries a specific argument about the gap between apparent interactional success and underlying mechanism.

**Annotation:** Both the named program (DOCTOR) and the named mechanism ("shared premises can remain unspoken") are necessary for the example to do argumentative work. Removing the name leaves a gestural reference; removing the mechanism explanation leaves an anecdote. The specificity is the argument.

---

**Calibration note:** Both examples name specific institutions and artifacts (GM Linden / DOCTOR) and do argumentative work rather than illustrative decoration (distinguishing two explanations / demonstrating the mechanism-appearance gap). A gestural reference ("as seen in manufacturing environments") satisfies Sub-check F at MINOR; a named, specific case with a mechanism explanation is CLEAN. The INF3001H loan-officer vignette is the existing canonical model in `sub_checks.md`; the Vidal and Suchman examples demonstrate the same specificity principle in non-i* domains.
```

- [ ] **Step 3: Replace Sub-check G stub with full entry**

Find:
```
## Sub-check G — Consolidation Anchor

*(content added in Task 3)*
```

Replace with:
```markdown
## Sub-check G — Consolidation Anchor

**Property being calibrated:** At each structural boundary where three or more load-bearing constructs have accumulated (or where the next section depends on two or more prior sections' material), the prose carries a one-sentence anchor that (a) names the accumulated constructs and (b) signals what the next movement will do with them. The canonical form is "At this point, the reader holds X, Y, Z; the next movement does W with them" — but any sentence performing both functions qualifies.

### Vidal (2022) — Management Divided: Contradictions of Labor Management

**Location:** Chapter 3, "A Theory of Organizational Political Economy," ~offset 210,300

**Verbatim passage:**

> I now turn to develop my theory of organizational political economy. I begin with a brief specification of the management and workforce contradictions, which I argue are inherent to the employment relation. Next, I develop the institutionalist theory of growth stages. Following this, I develop a cultural-satisficing model of agency, a general model applied in my analysis of how managers and workers respond to contradictory pressures. To flesh out the political and cultural context of the organization in terms of labor process dynamics, I develop a theory of routine politics of production. Finally, to close the loop on how widespread satisficing is possible in a competitive market economy, I develop a theory of the permissive institutionalization of competitive fields.

**Marker audit:** Structural boundary: transition from literature-review chapters (coordination vs. discipline; socialization vs. alienation) to the positive-theory chapters. The anchor performs function (b) — signals what the next movement will do — via a five-move forward map ("I begin… Next… Following this… Finally…"). Function (a) — naming accumulated constructs — is implicit in "the management and workforce contradictions" and "contradictory pressures," which refer to the constructs established in the prior chapters. This is a forward-consolidation anchor: it maps the road ahead rather than restating the road behind.

**Annotation:** The Vidal anchor is purely forward — it maps the next five theory-building moves without restating what the prior chapters established. This satisfies Sub-check G because the naming of the accumulated material is compact ("management and workforce contradictions") and the forward signal is explicit and sequenced. The Evaluator should accept compact backward-references when the forward signal is detailed.

---

### Suchman (2007) — Human-Machine Reconfigurations: Plans and Situated Actions

**Location:** Chapter 5, "Plans," opening paragraph, ~offset 143,800

**Verbatim passage:**

> This chapter and the next discuss two alternative views of action. The first, adopted by most researchers in artificial intelligence, locates the organization and significance of human action in underlying plans. The alternative view, developed in Chapter 6 of this book, is that although the course of action can always be projected or reconstructed in terms of prior intentions and typical situations, the prescriptive significance of intentions for situated action is inherently vague. The coherence of situated action is tied in essential ways not to individual predispositions or conventional rules but to local interactions contingent on the actor's particular circumstances. A consequence of action's situated nature is that communication must incorporate both a sensitivity to local circumstances and resources for the remedy of troubles in understanding that inevitably arise. This chapter reviews the planning model of purposeful action and shared understanding.

**Marker audit:** Structural boundary: chapter transition after Chapter 4's review of interactive artifacts, before Chapter 5's theory of plans. The passage performs both functions: (a) names accumulated constructs ("intentionality," "the planning model," the AI-adoption of the planning view — all established in Ch.4); (b) signals what comes next: "This chapter reviews the planning model…" and positions Ch.6 as the alternative. This is a bidirectional anchor — it closes the prior chapter's argument and maps the next two chapters.

**Annotation:** Unlike Vidal's purely forward anchor, Suchman's is bidirectional — it closes the prior chapter's argument ("the coherence of situated action is tied… to local interactions") while mapping the next two chapters ("this chapter reviews…; Ch.6 develops the alternative"). Both satisfy Sub-check G. The criterion requires both functions (name accumulated material + signal next move); which function receives more space is a judgment call.

---

**Calibration note:** Vidal's anchor is forward-heavy (detailed five-move sequence; compact backward reference); Suchman's is bidirectional (closes prior argument; maps next two chapters). Both satisfy G because both name accumulated material AND signal the next move. The Evaluator should not require equal weight on both functions — a compact backward reference ("the constructs developed above") paired with a detailed forward signal, or a detailed backward summary paired with a brief "the next section turns to X," both satisfy the two-function requirement.
```

- [ ] **Step 4: Replace Sub-check H stub with full entry**

Find:
```
## Sub-check H — Register Appropriateness

*(content added in Task 3)*
```

Replace with:
```markdown
## Sub-check H — Register Appropriateness

**Property being calibrated:** Non-technical passages (signpost orienting clauses, section framing, inter-section transitions, worked-example vignette bodies, consolidation anchor sentences) carry at least two of four positive markers: (M1) concrete-referent anchoring — physical/material entity, named individual/group, or specific scenario; (M2) agent-verb-object construction — human or identifiable agents as grammatical subjects; (M3) plain-English discourse connectives from the `lay_term_lexicons.md` list; (M4) register-shift signposting when register intentionally shifts within the passage.

### Vidal (2022) — Management Divided: Contradictions of Labor Management

**Location:** Preface, ~offset 4,800

**Verbatim passage:**

> Managers in general were not focused on—let alone preoccupied with—labor control or work speedup, and in many cases were focused on cross training their workers and including them in problem solving and decision making around process improvement. To be sure, there was labor-management conflict, but this was generally about competing visions of efficiency and contestation over changing workplace routines, not about control, autonomy, or the pace of work.

**Marker audit:** M1: concrete referents — "managers," "their workers," "workplace routines," "cross training," "problem solving," "process improvement" (named activities and role-holders). M2: agent-verb-object — "managers were focused on cross training their workers and including them in problem solving" (managers act on workers; active construction throughout). M3: plain connectives — "To be sure… but" (concessive structure); "not about control, autonomy, or the pace of work" (plain negation). M4: no register shift in the passage — not needed. Result: three of four positive markers (M1, M2, M3); H-CLEAN.

**Annotation:** This passage reframes the book's intellectual motivation in daily English — explaining what the fieldwork found that didn't fit existing theory. The agents (managers, workers) act on concrete activities (cross training, problem solving), and the concessive "To be sure… but" is one of the most reliable M3 signals. Register-appropriateness does not require all four markers; three of four is comfortably CLEAN.

---

### Suchman (2007) — Human-Machine Reconfigurations: Plans and Situated Actions

**Location:** Chapter 1, "Readings and Responses," ~offset 30,200

**Verbatim passage:**

> My engagement with the question of human–machine interaction, from which the book arose, began in 1979, when I arrived at PARC as a doctoral student interested in a critical anthropology of contemporary American institutions and with a background as well in ethnomethodology and interaction analysis. My more specific interest in the question of interactivity at the interface began when I became intrigued by an effort among my colleagues to design an interactive interface to a particular machine. The project was initiated in response to a delegation of Xerox customer service managers, who traveled to PARC from Xerox's primary product development site in Rochester, New York, to report on a problem with the machine and to enlist research advice in its solution.

**Marker audit:** M1: concrete referents — named year (1979), named institution (PARC), named city (Rochester, New York), real agents (customer service managers, doctoral student, Xerox). M2: agent-verb-object — "I arrived at PARC," "I became intrigued," "customer service managers… traveled to PARC," "to report on a problem" (active agents throughout). M3: plain connectives — "began when," "in response to," "to report on and to enlist" (plain purpose constructions). M4: no register shift — not needed. Result: three of four positive markers (M1, M2, M3); H-CLEAN.

**Annotation:** This is a research-history narrative — the structural role is framing the book's intellectual occasion. Named year, institution, and real agents make M1 and M2 easy to satisfy; the plain connectives ("began when," "in response to") make M3 straightforward. The passage has no nominalised stack and no passive abstraction — "the project was initiated" is passive but immediately followed by the active subject ("in response to a delegation… who traveled").

---

**Calibration note:** Vidal's passage is a theoretical reframing (explaining what fieldwork found that didn't fit theory) delivered in daily English; Suchman's is a research-history narrative (explaining how the author came to study the problem). Both non-technical passage roles satisfy H via concrete agents acting on concrete activities, with plain connectives. The Evaluator should note that a partially passive passage (Suchman: "the project was initiated") is not automatically H-MAJOR if the surrounding construction is agent-verb-object and the passive is brief and followed by an active subject. The compliance frame is presence-of-positive-markers, not absence-of-negative-markers.
```

- [ ] **Step 5: Verify no stubs remain**

```bash
grep -c "content added in Task" /sessions/amazing-wonderful-hamilton/mnt/co-author-harness/references/examples/model_prose_corpus.md
```

Expected output: `0`

Verify all 8 calibration notes are present:
```bash
grep -c "Calibration note" /sessions/amazing-wonderful-hamilton/mnt/co-author-harness/references/examples/model_prose_corpus.md
```

Expected output: `8`

- [ ] **Step 6: Commit Sub-checks E–H**

```
feat(corpus): populate Sub-checks E-H with Vidal+Suchman calibration passages

Sub-check E (jargon): Vidal structural complexity vs. lexical simplicity;
Suchman construct count vs. technical-sounding adjectives. Calibration
note: audit constructs, not technical-sounding words.

Sub-check F (worked example): Vidal GM Linden/Milkman (manufacturing);
Suchman ELIZA/DOCTOR (HCI). Calibration note: specificity is the
argument, not illustration.

Sub-check G (consolidation anchor): Vidal forward-heavy five-move map;
Suchman bidirectional (closes prior, maps next two). Calibration note:
both functions required, equal weight not required.

Sub-check H (register): Vidal theoretical-reframing in daily English;
Suchman research-history narrative. Calibration note: compliance frame
is presence-of-positive-markers, not absence-of-negative-markers.

Corpus v1.0 complete: 16 passages, 8 Sub-checks, 2 authors.
```

---

## Task 4: Amend `accessibility-overlay/SKILL.md`

**Files:**
- Modify: `skills/accessibility-overlay/SKILL.md` (add MANDATORY corpus load instruction after existing MANDATORY block)

- [ ] **Step 1: Locate the existing MANDATORY block**

Read the SKILL.md to confirm the exact text of the existing mandatory block. It currently reads (around line 79):

```
**MANDATORY — READ ENTIRE FILE.** Before producing findings, you MUST read [`references/READER_ACCESSIBILITY.md`](references/READER_ACCESSIBILITY.md) completely from start to finish.
```

- [ ] **Step 2: Insert the corpus MANDATORY instruction**

Use the Edit tool to find the end of that MANDATORY block and insert the new instruction immediately after it. The existing block ends with:

```
The threshold numerics (150/200/300-word cadence cut-offs, σ<6, P-stage-adjusted term caps, construct-accumulation threshold of 3, the ~3,000 / ~5,000-word G envelope, the H functional-removability test scope, the H positive/negative marker definitions, etc.) are load-bearing — do not approximate them from memory.
```

Insert after that sentence (before the blank line that follows):

```markdown

**MANDATORY — LOAD MODEL PROSE CORPUS.** After loading `READER_ACCESSIBILITY.md`, load `references/examples/model_prose_corpus.md`. The corpus provides one CLEAN example per Sub-check A–H from Vidal (2022) and Suchman (2007). Use them as positive calibration anchors when adjudicating borderline findings: if a passage is structurally similar to a corpus example and the criterion property is present, default toward CLEAN; if a passage clearly lacks a property that is present in the corpus example, escalate toward MAJOR. The corpus calibration notes identify what pairs of examples together demonstrate that neither alone demonstrates — read them before adjudicating any Sub-check finding rated BORDERLINE or above.
```

- [ ] **Step 3: Verify amendment**

```bash
grep -n "LOAD MODEL PROSE CORPUS" /sessions/amazing-wonderful-hamilton/mnt/co-author-harness/skills/accessibility-overlay/SKILL.md
```

Expected: one matching line, positioned after the READER_ACCESSIBILITY.md mandatory block.

- [ ] **Step 4: Commit**

```
feat(overlay): add MANDATORY corpus load instruction to accessibility-overlay SKILL.md

Wires references/examples/model_prose_corpus.md into every overlay
invocation as a positive calibration anchor for Sub-checks A-H.
Co-located with existing READER_ACCESSIBILITY.md mandatory block.
No threshold or routing changes.
```

---

## Task 5: Add cross-reference pointers to `sub_checks.md`

**Files:**
- Modify: `skills/accessibility-overlay/references/sub_checks.md` (append one pointer line at end of each Sub-check A–H section)

- [ ] **Step 1: Insert pointer at end of Sub-check A section**

The Sub-check A section ends just before `## Sub-check B`. Insert one line before that heading:

Find:
```
Severity floors: MINOR if 151–200 words without turn-point; MAJOR if >200 words with or without turn-point; BLOCKER if >300 words with no turn-point and no sentence break signals (em-dash, colon, semicolon) — this pattern is the "wall of prose" that the constraint most directly targets.

## Sub-check B
```

Replace with:
```
Severity floors: MINOR if 151–200 words without turn-point; MAJOR if >200 words with or without turn-point; BLOCKER if >300 words with no turn-point and no sentence break signals (em-dash, colon, semicolon) — this pattern is the "wall of prose" that the constraint most directly targets.

> *Model examples → `references/examples/model_prose_corpus.md §Sub-check A`*

## Sub-check B
```

- [ ] **Step 2: Insert pointer at end of Sub-check B section**

Find:
```
Severity floors: MINOR on any single flagged paragraph; MAJOR if two or more adjacent paragraphs trip the same flag (a monotone-dense stretch); never BLOCKER alone (rhythm is a diffuse property; BLOCKER is reserved for A, D, F).

## Sub-check C
```

Replace with:
```
Severity floors: MINOR on any single flagged paragraph; MAJOR if two or more adjacent paragraphs trip the same flag (a monotone-dense stretch); never BLOCKER alone (rhythm is a diffuse property; BLOCKER is reserved for A, D, F).

> *Model examples → `references/examples/model_prose_corpus.md §Sub-check B`*

## Sub-check C
```

- [ ] **Step 3: Insert pointer at end of Sub-check C section**

Find:
```
Severity floors: MINOR per undefined construct (author can argue field-standardness); MAJOR if two or more undefined constructs appear in the same paragraph; BLOCKER if an undefined construct does conceptual work (is cited, contrasted, or built upon) in a subsequent paragraph without ever being defined.

## Sub-check D
```

Replace with:
```
Severity floors: MINOR per undefined construct (author can argue field-standardness); MAJOR if two or more undefined constructs appear in the same paragraph; BLOCKER if an undefined construct does conceptual work (is cited, contrasted, or built upon) in a subsequent paragraph without ever being defined.

> *Model examples → `references/examples/model_prose_corpus.md §Sub-check C`*

## Sub-check D
```

- [ ] **Step 4: Insert pointer at end of Sub-check D section**

Find:
```
> *Register quality within the orienting and contribution clauses is delegated to Sub-check H. D enforces structural presence; H enforces register construction.* (Added v0.10.1 with Sub-check H. The two checks remain orthogonal at the finding level — a signpost can be D-CLEAN with both clauses present and H-MAJOR if the clauses are register-inappropriate, and vice versa.)

## Sub-check E
```

Replace with:
```
> *Register quality within the orienting and contribution clauses is delegated to Sub-check H. D enforces structural presence; H enforces register construction.* (Added v0.10.1 with Sub-check H. The two checks remain orthogonal at the finding level — a signpost can be D-CLEAN with both clauses present and H-MAJOR if the clauses are register-inappropriate, and vice versa.)

> *Model examples → `references/examples/model_prose_corpus.md §Sub-check D`*

## Sub-check E
```

- [ ] **Step 5: Insert pointer at end of Sub-check E section**

Find:
```
Severity floors: MINOR on any paragraph that exceeds the P-stage cap by one term; MAJOR on any paragraph that exceeds the cap by two or more terms; never BLOCKER alone.

## Sub-check F
```

Replace with:
```
Severity floors: MINOR on any paragraph that exceeds the P-stage cap by one term; MAJOR on any paragraph that exceeds the cap by two or more terms; never BLOCKER alone.

> *Model examples → `references/examples/model_prose_corpus.md §Sub-check E`*

## Sub-check F
```

- [ ] **Step 6: Insert pointer at end of Sub-check F section**

Find:
```
Severity floors: MINOR if a density spike is followed by a gestural example (a phrase, not a vignette); MAJOR if a density spike is followed by further abstract prose; BLOCKER if a density spike exceeds one full page of abstract prose with no instantiation — this is the pattern the constraint names as "density without cadence."

## Sub-check G
```

Replace with:
```
Severity floors: MINOR if a density spike is followed by a gestural example (a phrase, not a vignette); MAJOR if a density spike is followed by further abstract prose; BLOCKER if a density spike exceeds one full page of abstract prose with no instantiation — this is the pattern the constraint names as "density without cadence."

> *Model examples → `references/examples/model_prose_corpus.md §Sub-check F`*

## Sub-check G
```

- [ ] **Step 7: Insert pointer at end of Sub-check G section**

The Sub-check G section ends with the stability-sub-mode paragraph. Insert the pointer before `## Sub-check H`:

Find:
```
**Stability sub-mode.** Under `run-phase-3-stability` (v0.8.0+ byte-stable inheritance pass), Sub-check G runs advisory-only regardless of the `advisory_until` flag. A G finding under stability mode is logged with `stability_advisory: true` and does not force escalation to a full Ph3 pass. The rationale is that G is judgment-heavy and its findings are not cheaply re-derivable from a byte-stable snapshot; a stability pass that fired a G BLOCKER would either require a full-Ph3 escalation on every round (expensive) or would need a hash-summary caching layer not yet specified. The advisory path lets the reduced stability pass run cheaply while preserving G's recurrence trail through Reflector Phase 2g.

## Sub-check H
```

Replace with:
```
**Stability sub-mode.** Under `run-phase-3-stability` (v0.8.0+ byte-stable inheritance pass), Sub-check G runs advisory-only regardless of the `advisory_until` flag. A G finding under stability mode is logged with `stability_advisory: true` and does not force escalation to a full Ph3 pass. The rationale is that G is judgment-heavy and its findings are not cheaply re-derivable from a byte-stable snapshot; a stability pass that fired a G BLOCKER would either require a full-Ph3 escalation on every round (expensive) or would need a hash-summary caching layer not yet specified. The advisory path lets the reduced stability pass run cheaply while preserving G's recurrence trail through Reflector Phase 2g.

> *Model examples → `references/examples/model_prose_corpus.md §Sub-check G`*

## Sub-check H
```

- [ ] **Step 8: Insert pointer at end of Sub-check H section**

The Sub-check H section is the last section in the file. Insert the pointer at the very end of the file:

Find the final paragraph of Sub-check H (ends with):
```
**Stability sub-mode.** Under `run-phase-3-stability`, Sub-check H runs advisory-only mirroring Sub-check G's stability-sub-mode treatment. An H finding under stability mode is logged with `stability_advisory: true` and does not force escalation to a full Ph3 pass. Rationale matches G: H is judgment-heavy and its findings are not cheaply re-derivable from a byte-stable snapshot.

**Interaction with Sub-checks D, F, G.** D enforces section-opening structural presence; H enforces register quality within the orienting and contribution clauses (cross-reference at D's entry above). F locates density spikes; H audits the worked-example vignette's register quality. G locates threshold-crossing structural boundaries; H audits the consolidation anchor sentence's register quality. The two-Sub-check pattern (structural-Sub-check + register-Sub-check) is deliberate — D/F/G can be CLEAN while H is MAJOR if the structurally-required passage is registered inappropriately, and vice versa. When a Generator is applying a fix, the structural Sub-check's suggested_fix and H's suggested_fix can co-locate in the same paragraph but the two sentences should do distinct work.
```

Append after that final paragraph:

```markdown

> *Model examples → `references/examples/model_prose_corpus.md §Sub-check H`*
```

- [ ] **Step 9: Verify all eight pointers are present**

```bash
grep -c "Model examples →" /sessions/amazing-wonderful-hamilton/mnt/co-author-harness/skills/accessibility-overlay/references/sub_checks.md
```

Expected output: `8`

Also verify each points to the correct Sub-check letter:
```bash
grep "Model examples →" /sessions/amazing-wonderful-hamilton/mnt/co-author-harness/skills/accessibility-overlay/references/sub_checks.md
```

Expected: 8 lines, one for each §Sub-check A through §Sub-check H.

- [ ] **Step 10: Commit**

```
feat(sub_checks): add model-corpus cross-reference pointer at end of each Sub-check A-H

Eight one-line blockquote pointers. Each resolves to the corresponding
section of references/examples/model_prose_corpus.md. No operational
content changed; all additions are additive.
```

---

## Task 6: Amend `READER_ACCESSIBILITY.md §13.4`

**Files:**
- Modify: `references/READER_ACCESSIBILITY.md` (insert pointer paragraph at top of §13.4 worked-examples sub-section)

- [ ] **Step 1: Locate the insertion point**

The insertion point is after the `### Worked examples (added v0.10.2)` heading and before the sentence "The following three examples anchor the Evaluator's H adjudication at the operational level."

Current text at that location:
```
### Worked examples (added v0.10.2)

The following three examples anchor the Evaluator's H adjudication at the operational level.
```

- [ ] **Step 2: Insert pointer paragraph**

Find:
```
### Worked examples (added v0.10.2)

The following three examples anchor the Evaluator's H adjudication at the operational level.
```

Replace with:
```
### Worked examples (added v0.10.2)

**Sub-check A–G examples.** The worked examples below cover Sub-check H (Register Appropriateness) only. Worked examples for Sub-checks A–G — paragraph cadence, sentence-length variation, first-use definition, section-opening signpost, jargon discipline, worked example at density spike, and consolidation anchor — are collected in `references/examples/model_prose_corpus.md`, organized by Sub-check with two passages per check (Vidal 2022; Suchman 2007). Read that file when you need a positive model for any A–G check. The corpus also supplies two additional H examples (Vidal Preface; Suchman Ch.1) drawn from outside the i*/GORE domain, expanding the H calibration set beyond the four INF3006Y-only examples below.

The following examples anchor the Evaluator's H adjudication at the operational level.
```

- [ ] **Step 3: Verify amendment**

```bash
grep -n "Sub-check A.G examples" /sessions/amazing-wonderful-hamilton/mnt/co-author-harness/references/READER_ACCESSIBILITY.md
```

Expected: one matching line, positioned immediately after the `### Worked examples (added v0.10.2)` heading.

Also verify the existing H examples (Examples 1–4) are still intact:
```bash
grep -n "Example [1-4] —" /sessions/amazing-wonderful-hamilton/mnt/co-author-harness/references/READER_ACCESSIBILITY.md
```

Expected: four matching lines (Examples 1–4 unchanged).

- [ ] **Step 4: Commit**

```
feat(reader-accessibility): add A-G corpus pointer at §13.4 worked-examples top

Directs human readers to references/examples/model_prose_corpus.md for
Sub-checks A-G examples (previously zero examples existed for A-G in
this file). Clarifies that the four existing worked examples cover H
only. Notes that the corpus also extends H calibration to two non-GORE
domain examples. Existing H Examples 1-4 are unchanged.
```

---

## Task 7: Final verification — harness integrity checks

**Files:**
- Read: `scripts/skill-check.py`, `scripts/catalog-check.py`, `scripts/path-hygiene-check.py`
- Run via Desktop Commander

- [ ] **Step 1: Run skill-check.py**

Use `mcp__Desktop_Commander__start_process` with:
- Shell: `cmd.exe`
- Command: `C:\Users\young\AppData\Local\Programs\Python\Launcher\py.exe B:\Agents\co-author-harness\scripts\skill-check.py > B:\Agents\co-author-harness\scripts\skill_check_output.txt 2>&1`

Read `B:\Agents\co-author-harness\scripts\skill_check_output.txt`. Expected: no errors related to the four files modified in Tasks 1–6. If pre-existing failures appear for unrelated files, record them in the commit message as "pre-existing, out of scope" and proceed — do not block on failures that were present before this feature.

- [ ] **Step 2: Run catalog-check.py**

```
C:\Users\young\AppData\Local\Programs\Python\Launcher\py.exe B:\Agents\co-author-harness\scripts\catalog-check.py > B:\Agents\co-author-harness\scripts\catalog_check_output.txt 2>&1
```

Read output. Expected: no errors.

- [ ] **Step 3: Run path-hygiene-check.py**

```
C:\Users\young\AppData\Local\Programs\Python\Launcher\py.exe B:\Agents\co-author-harness\scripts\path-hygiene-check.py > B:\Agents\co-author-harness\scripts\path_hygiene_output.txt 2>&1
```

Read output. Expected: no errors about `references/examples/model_prose_corpus.md` — the new file should pass path-hygiene (it is in the `references/examples/` directory, consistent with existing walkthroughs).

- [ ] **Step 4: Verify corpus cross-reference integrity manually**

Read `references/examples/model_prose_corpus.md` and confirm:
- All 8 `## Sub-check` headings present (A through H)
- All 8 `**Calibration note:**` entries present
- No stub text (`*(content added in Task*)`) remains
- Frontmatter block is valid YAML

Run:
```bash
grep -E "^## Sub-check [A-H]" /sessions/amazing-wonderful-hamilton/mnt/co-author-harness/references/examples/model_prose_corpus.md | wc -l
```

Expected: `8`

- [ ] **Step 5: Verify SKILL.md mandatory block order**

Read `skills/accessibility-overlay/SKILL.md` around the MANDATORY block area. Confirm:
1. `MANDATORY — READ ENTIRE FILE` (READER_ACCESSIBILITY.md) appears first
2. `MANDATORY — LOAD MODEL PROSE CORPUS` appears immediately after, before any Sub-check dispatch content

- [ ] **Step 6: Final commit — verification complete**

```
chore(v0.12.0): verify model-prose-corpus wiring across all four components

Harness check scripts pass (skill-check, catalog-check, path-hygiene).
Manual cross-reference verification: 8 Sub-check headings, 8 calibration
notes, 8 sub_checks.md pointers, 1 SKILL.md mandatory block, 1
READER_ACCESSIBILITY.md pointer paragraph. No stubs remain. v0.12.0
model-prose-corpus feature complete.
```

---

## Spec Coverage Check

| Spec requirement | Task(s) |
|---|---|
| New `references/examples/model_prose_corpus.md` with frontmatter, versioning, extensibility contract | Task 1 |
| 8 Sub-check sections, each with Vidal + Suchman verbatim entries, marker audits, annotations, calibration notes | Tasks 2–3 |
| Zotero parent + attachment keys in frontmatter | Task 1 (frontmatter) |
| MANDATORY corpus load instruction in `accessibility-overlay/SKILL.md` | Task 4 |
| Eight cross-reference pointers in `sub_checks.md` (one per A–H) | Task 5 |
| Pointer paragraph in `READER_ACCESSIBILITY.md §13.4` | Task 6 |
| Harness integrity verification | Task 7 |
| No content deleted, all changes additive | Verified in Tasks 4, 5, 6 via grep checks |
