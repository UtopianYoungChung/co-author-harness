# GROUND_TRUTH.md — Canonical Definition Source for the EYgp Research-Process Framework

**Status.** This file registers a single external artifact — Prof. Eric Yu's group's *Research Process and Artifacts* workbook — as the **canonical definition source** for the problem-setting, related-work, knowledge, solution, tools, validation, and readiness axes referenced throughout the package. When any package file, skill, or agent cites one of these axes (P0/P1/P2, R0/R1/R2, K0/K1/K2, S1–S5, T1–T5, V0–V5, readiness tick bands), the authoritative definition is the workbook cell, not the paraphrase in the cite-ing file.

This file exists so that every derivative definition in the package has a traceable chain back to a single, mechanically-readable source — in the spirit of `GROUNDING_PROTOCOL.md` Rule 1 (read before cite) and Rule 7 (chain of verification).

---

## 1. The canonical source

| Field | Value |
|---|---|
| **Artifact name** | *Research Process and Artifacts* (EYgp internal reference table) |
| **File (canonical)** | `.paper-package/references/EYgp_Research_process_and_artifacts.xlsx` |
| **Size** | 74,770 bytes |
| **SHA-256** | `5bed11a17615600db8b195e8b278ea7b5b65aa3ae94dad2fa680bac0df479895` |
| **Verbatim Markdown extract** | `.paper-package/references/EYgp_Research_process_and_artifacts.md` (grep-able) |
| **Extract regenerator** | `scratch/build_eygp_extract.py` (read-only transcription of every non-empty cell) |
| **First ingested into package** | 2026-04-17 |
| **Sheets** | `Sheet1` (S-stages), `Sheet2` (P/R/K/T/V axes), `Sheet3` (readiness rating) |

When the workbook is updated, the owner of this file regenerates the extract and, if axis labels or stage bands changed, updates §3–§7 below and re-runs the verification procedure in §10.

---

## 2. Precedence

This file sits alongside the other component files under the package's ordinary precedence rules (`CLAUDE.md §4`). Specifically:

- On **definitions of axis stages** (what P0 means, what "20%–50% ready" refers to, what artefact genre belongs to T3, etc.), the **workbook cells win** over any paraphrase in `project_writing_style_checklist.md`, `p-stage-checker.md`, `DETERMINISTIC_CHECKS.md §8`, or any agent prompt. Paraphrases that contradict the workbook are corrected, not preserved.
- On **how those definitions are used** for review, drafting, and lifecycle governance (tone, register, severity, ordering), the ordinary component files win. The workbook is a glossary and a readiness grid; it does not prescribe review process.

If a future user instruction disagrees with the workbook on a definitional question, `CLAUDE.md §4` rule 1 still applies (user wins), but the agent flags the departure in the findings report so the provenance chain stays visible.

---

## 3. Axis inventory (from Sheet2 and Sheet1)

Six axes are defined. The stage labels and their artefact genres are transcribed verbatim from the workbook.

| Axis | Source sheet / header | Stages (workbook cell values) |
|---|---|---|
| Problem setting | `Sheet2!B1` | `P0`, `P1`, `P2` |
| Related work | `Sheet2!B9` | `R0`, `R1`, `R2` |
| Knowledge content | `Sheet2!B15` | `K0`, `K1`, `K2` |
| Solution | `Sheet1!B1..F1` | `S1`, `S2`, `S3`, `S4`, `S5` |
| Tools | `Sheet2!B20` | `T1`, `T2`, `T3`, `T4`, `T5` |
| Validation | `Sheet2!B25` | `V0`, `V1`, `V2`, `V3`, `V4`, `V5` |

Axis scope note from `Sheet2!B15` (Knowledge content): *"Knowledge content - that is to be modeled and reasoned about in your subject-matter area (eg openness, coopetition, capabilities, ...)"* — i.e. the K axis is subject-matter content, not research-process knowledge.

---

## 4. Problem-setting axis (P0 / P1 / P2) — verbatim

Source: `Sheet2` rows 1–8.

| Row attribute | P0 (col B) | P1 (col C) | P2 (col D) |
|---|---|---|---|
| artifact genre | collected readings on the problem phenomenon | characterization of problem phenom | Definition of research problems/questions/objectives |
| (row 4 continuation of artifact genre) | tags: `#V0` = contains potential test case eg for P2; `#V0a` = eg includes ana/reasoning | a synthesis, digest, interpretation of the phenom, possibly based on some classification dimensions or theoretical framework. Refer to egs from V0. | the specific technical problems that your own research is going to address/solve (eg Given X, how to obtain Y). Is core of your Thesis Research Proposal. Specific enough to identify alternative tech approaches and solutuons, with tradeoffs. Illustrate with egs from V0. |
| format | *(empty)* | sectioned paragraphs + tables/charts. | sectioned paragraphs + tables/charts. Research problems/questions labeled as `q1 q11 q21 ...`. Detailed subproblems are uncovered during S1, S2, S3. |
| text style | bib list, + a few bullet pts | use outline mode (eg in Word) to organize hierachically. Later, can extract/rearrange points/paragraphs selectively for different target docs. | use outline mode (eg in Word) to organize hierachically. Later, can extract/rearrange points/paragraphs selectively for different target docs. |
| khmap | *(empty)* | hierarchical ME-map of problems and existing solutions | portion of the khmap from P1 that you are contributing to. Nodes are labeled with `q#`. Updated with each `qxxxS3` release at node `qxxx`. |
| thesis chapter | Bib | Motivation | Research Objectives |

**Original-spelling note.** The workbook contains the spellings "phenom", "hierachically", "solutuons", "probem", "empir", "reshrs", "rhetoric" where expected; the extract preserves them verbatim. Any package paraphrase that silently "corrects" these strings is still the paraphrase's responsibility to flag, not the workbook's.

---

## 5. Related-work axis (R0 / R1 / R2) — verbatim

Source: `Sheet2` rows 9–14.

| Row attribute | R0 (col B) | R1 (col C) | R2 (col D) |
|---|---|---|---|
| artifact genre | collected readings on existing approaches/solutions | analysis of existing technical (eg model-based) approaches/solutions | comparative analysis of proposed solution and existing or alternative approaches/solutions |
| format | bib DB; or lists - grouped/tagged by category | sectioned paragraphs + tables/charts. same khmap from P1 and P2. | *(empty)* |
| text style | *(empty)* | use outline mode (eg in Word) to organize hierachically. Later, can extract/rearrange points/paragraphs selectively for different target docs. | *(empty)* |
| thesis chapter | Bib | Related work | Contributions |

---

## 6. Knowledge-content axis (K0 / K1 / K2) — verbatim

Source: `Sheet2` rows 15–19.

| Row attribute | K0 (col B) | K1 (col C) | K2 (col D) |
|---|---|---|---|
| artifact genre | collected readings/resources that provide knowledge content for eventual encoding in your modeling framework | analysis of this body of knowledge, organized according to some structure, but not yet formalized in terms of metamodel or axioms. Intuitive semantics only. | encodings of selected knowledge content according to your framewrok. ie a reusable KB, supportable by (semi-) automated tools (for retrieval, application, or reasoning), |
| format | bib DB; or lists - grouped/tagged by category | concept maps, tables, taxonomies, ... | knowledge structures as defined in your technical solution metamodels (from S1-S5) eg NFR catalogues, `i*` SD patterns |
| thesis chapter | Bib | Background on subject-matter area | Solution chapters |

---

## 7. Solution axis (S1 / S2 / S3 / S4 / S5) — verbatim

Source: `Sheet1` rows 1–17 (the entirety of Sheet1). Stage column labels are in row 1.

| Row attribute | S1 (col B) | S2 (col C) | S3 (col D) | S4 (col E) | S5 (col F) |
|---|---|---|---|---|---|
| artifact genre | technical sketch | technical outline | technical note | working paper | published paper |
| stage | exploratory | experimental | consolidation + validation | consolidation + validation | dissemination |
| maturity of the idea | "inkling" | "kernel" | "nugget" | defensible | compelling |
| main purpose | for self, close collaborator | for self, close collaborator, supervisor | internal group feedback, critique. (Including possibly industry partner collaborators.) | detailed write-up as technical report. Can be refashioned into conf/journal paper(s), thesis chapter. | submission for external review |
| style | rough sketches | Bullet points/lists, full sentences. Q&A format may be helpful. | prose for internal audience | prose for "friendly" audience. Responses to potential critiques, reviewers' objections - as appendix. | rhetorical prose targeted to a particular audience |
| format – Written | -- not required -- | -- not required -- | doc. / Version#: `qxxxS3vx` / `qxxxS3vxrx` for a stable "release" | doc | doc |
| length (written) | *(empty)* | *(empty)* | 10-15p | 20-30p | 15-25p |
| format – Pres'n | hand sketches, or whiteboard+photo. | Visio / Word …-> ppt - Sequence of slides must tell a coherent story, offering a solution to a technical problem (defined in a P2 artifact). Early versions can be series of Visio tabs (each slide must have title, bullet text), transitioning eventually to ppt for S3 artifact. Ok to use Word (simulating a slide deck, typically each page has a figure/model with explanatory bullets.) | ppt - detailed technical pres'n on single (small) research advance. | internal technical pres'n, combining several research advances, allowing material to be extracted for one or more conference or journal papers. | polished public pres'n |
| length (pres'n) | 1-5 figs | 10-15s | 15-25s; 20'+20' | 25-50s; 40' + 20'Q&A | 20-25s; 20'+10' |
| content | small unit of technical advance | Concepts/terms, defs, propositions, conclusions (eg new capabilities offered by solution). Usage guidelines/rules, rationales. Assumptions, hypotheses. Early versions can have long to-do lists. Open tech issues identified should be added to P2 khmap, assigned `q#`. | Motivation <1p; Related wk <1p (5-10 refs); Technical core 5-10p; Eg/case studies/empir data 3-5p; alt approaches 1p | Motivation >1p; Relwk compared >1p (20-50 refs); detailed rationales. Integrates relevant sections from P1, P2; R2; K2; V. | *(F11 empty in workbook)* |
| contextualized | no. Describes solution only. | somewhat. Refers to tech problem/question defined in P2 artifact. | yes. Refers to tech problem `qxxx` in P2, related work in R2. Contains relevant pieces K2 and V1. | a full, complete self-contained paper. contributions justified in relation to RelWk. | engaging in "conversation" in a research community |
| revision cycle | daily | weekly. The tech outline (S2) should be the main vehicle for our weekly meeting - ie you should have iterated your S1 during the week so that the solution idea is mature enough for discussion in the form of an S2. | monthly. You should be concerned if your technical solution idea has not matured into a technical note after one month. | semester | when ready |
| lead-time for feedback | *(empty)* | 24 hrs | 24 hrs | 48 hrs | 4 weeks for paper outline; 3 weeks first draft assembled from S4 or S3; 1 week for complete draft. |
| validation level | V1 (toy egs) | >= V1 | >= V1 | >= V2 (larger egs) | *(empty)* |
| figures | *(empty)* | Prelim versions of S2 can have hand-drawn figs or white-broad photos | Complex models should be explained incrementally, by building them up through a series of figures. It may also be helpful to present highlights of graphical models using a different format, eg. as tables, for easier comprehension. | *(empty)* | *(empty)* |
| quality threshold needed to start drafting next stage artifact. Stages are overlapping. | promising solution explained w egs, for a clear, coherent technical question/problem (`qxxx` from P2) | Core idea of the solution coherent enough to be written up. Continue improving or fleshing out the S2, while updating the S3 from time to time. | Defensible in front of colleagues (internal peer group). Scope of material could be enough for a workshop paper. | *(empty)* | Defensible in public. Ready to submit. |

---

## 8. Tools and Validation axes — verbatim

### 8.1 Tools (T1 / T2 / T3 / T4 / T5) — Sheet2 rows 20–24

| Row attribute | T1 | T2 | T3 | T4 | T5 |
|---|---|---|---|---|---|
| artifact genre | mock-ups, experimental implementations | requirements, design specification | functional research prototype | for limited release | for public release |
| (row 23 artifact-genre continuation) | *(empty)* | *(empty)* | research demo | usable by other researchers | usable by non-researchers |
| thesis chapter | N/A | Tools chapter | Tools chapter | -- optional -- | -- optional -- |

### 8.2 Validation (V0 / V1 / V2 / V3 / V4 / V5) — Sheet2 rows 25–28

| Row attribute | V0 | V1 | V2 | V3 | V4 | V5 |
|---|---|---|---|---|---|---|
| artifact genre | egs for illustrating the technical problem. Can be used as test cases. With xref to P0 items (sources) | tiny toy egs. Aim for exemplars to illustrate explain the probem, and to stimulate other reshrs | larger egs on paper, preferably based on literature. Larger eg to serve as exemplars to benchmark/compare alt soln approaches re expressiveness, ana power. | real-world case study | user feedback | empir user studies, experimental design |
| thesis chapter | no. | selectively include (1 or 2) as egs in Solution chapter. | can be in Solution chapter, or in separate Validation chapter if substantive. | Validation chapter | Validation chapter | Validation chapter |

---

## 9. Readiness scale (Sheet3) — verbatim

Source: `Sheet3` rows 1–30. `Sheet3!B1`: *"'Readiness %' is a combined assessment of quality and completeness of the artifact (or sub-section). Quality includes technical substance, rigor, presentation flow & understandability."*

### 9.1 Tick scale (row 2)

| Col | Label |
|---|---|
| B | no tick |
| C | ✓ 1-tick |
| D | ✓✓ 2-tick |
| E | ✓✓✓ 3-tick |
| F | ✓✓✓✓ 4-tick |
| G | ✓✓✓✓✓ 5-tick |

### 9.2 Artifact-level readiness bands (verbatim transcription of Sheet3)

The workbook records a readiness-band table per artifact type. The table below reproduces the populated cells; empty cells are marked `—`. "Start Sx" markers are the workbook's own forward-pointers.

| Artifact | no tick | ✓ 1-tick | ✓✓ 2-tick | ✓✓✓ 3-tick | ✓✓✓✓ 4-tick | ✓✓✓✓✓ 5-tick |
|---|---|---|---|---|---|---|
| P0 refs | — | 5-20% ready | 20%-50% | 50-80%. Start P1 | 80%-99% | complete, ready for release |
| P1 non-tech prob formulation | — | 5-20% ready | 20%-50% | 50-80%. Start P2 | 80%-99% | complete, ready for release |
| P2 technical research prob defn | — | 5-20% ready | 20%-50%. Start S1 | 50-80%. | 80%-99% | complete, ready for release |
| R0 refs | — | 5-20% ready. Start R1 | 20%-50% | 50-80% | 80%-99% | complete, ready for release |
| R1 analysis of related work, alt approaches | — | 5-20% ready | 20%-50% | 50-80% | 80%-99% | complete, ready for release |
| R2 contributions of proposed solution, compared to related work | — | 5-20% ready | 20%-50% | 50-80% | 80%-99% | complete, ready for release |
| S1 sketch | 0-5% or unrated | 5-20% ready | 20%-50% | 50-80%. Start S2 | n/a. Work on S2 instead | — |
| S2 outline | 0-5% or unrated | 5-20% ready | 20%-50% | 50-80%. Start S3 | 80%-99% | n/a. Work on S3 instead |
| S3 note | 0-5% or unrated | 5-20% ready | 20%-50% | 50-80% | 80%-99%. Start S5 or S4 | complete, ready for internal release |
| S4 report | 0-5% or unrated | 5-20% ready | 20%-50% | 50-80%. Start S5 | 80%-99% | complete, ready for release to friendly audience |
| S5 pub | 0-5% or unrated | 5-20% ready | 20%-50% | 50-80% | 80%-95% | complete, ready to submit |
| V0 source material for egs | — | 5-20% ready. Start V1 for S1 or S2 | 20%-50% | 50-80% | 80%-99%. | n/a |
| V1 toy egs | — | 5-20% ready | 20%-50% | 50-80%. Start V2 | 80%-99%. | complete, ready for release |
| V2 larger eg, from lit, prefer benchmark | — | 5-20% ready | 20%-50% | 50-80% | 80%-99%. | complete, ready for release |
| V3 real-world case study | — | 5-20% ready | 20%-50% | 50-80% | 80%-99%. | complete, ready for release |
| V4 user feedback | — | 5-20% ready | 20%-50% | 50-80% | 80%-99%. | complete, ready for release |
| V5 empir study | — | 5-20% ready | 20%-50% | 50-80% | 80%-99%. | complete, ready for release |

Domain Knowledge rows (`K0`, `K1`, `K2` at Sheet3 rows 18–20) and the Formalization block (Sheet3 rows 28–30: *"abstract formulation of problem and solution - eg math or logical formalism."* and *"example with no reliance on domain knowledge from a familiar domain"*) appear in the workbook without readiness bands populated. They are listed here for completeness so that callers know the workbook mentions them but does not define their band thresholds.

---

## 10. Verification procedure (for agents)

When any package file or skill cites an axis stage (P0/P1/P2, R0–R2, K0–K2, S1–S5, T1–T5, V0–V5) or a readiness tick band, the agent runs the following sequence before treating the paraphrase as authoritative:

1. **Open** `.paper-package/references/EYgp_Research_process_and_artifacts.md` (or the `.xlsx` directly) and locate the corresponding sheet row.
2. **Compare** the paraphrase against the workbook cell. Only substantive divergences are flagged — word-for-word identity is not required.
3. **Classify** divergences by `GROUNDING_PROTOCOL.md` Rule 1:
   - *Fidelity drift* (the paraphrase's wording shifts meaning, e.g. adds a requirement the workbook does not state): `[GROUNDING VIOLATION — Rule 1]`.
   - *Scope drift* (the paraphrase applies an axis-stage definition to a case the workbook does not cover): `[GROUNDING VIOLATION — Rule 1 — scope]`.
   - *Added-information* (the paraphrase introduces an interpretation not in the workbook but consistent with it): `[INFERRED — verify]` marker added; not a violation but must be traceable.
4. **Report** findings in `reviews/ground_truth_verification_<date>.md` (one row per divergence). The first verification run is recorded at `reviews/ground_truth_verification_2026-04-17.md` and serves as the baseline.
5. **Update** the paraphrasing file only when the user approves. The workbook is immutable from the package's side; changes to it come from the EYgp source.

The `eygp-framework-checker` skill (SK-28) automated steps 1–4 for a given manuscript or draft; it was retired at v0.7.0 with its stubs removed (see `references/SKILL_REGISTRY.md` Retired Skills). SK-10 `p-stage-checker` covers the P-axis subset.

---

## 11. Relationship to existing package files

| Package file | What it paraphrases from the workbook | Relationship |
|---|---|---|
| `project_writing_style_checklist.md` Part 0 | P0 / P1 / P2 definitions and anti-patterns | Paraphrase; verified in `reviews/ground_truth_verification_2026-04-17.md` §P. Workbook wins on definitional questions. |
| `skills/p-stage-checker/SKILL.md` | P0 / P1 / P2 vocabulary, arc, contribution framing | Paraphrase; same verification entry. Paraphrase extends the workbook with review-process heuristics that are out of scope for the workbook and therefore not ground-truth-conflicts. |
| `DETERMINISTIC_CHECKS.md §8` | P2 vocabulary patterns in P0/P1 conclusions; premature numbered RQs | Derived pattern set, not a paraphrase. Verified that the workbook's P2 row (`q1 q11 q21 ...`) supports the "labeled q-items" pattern the check relies on. |
| `project_writing_style_checklist.md` Part 0 V0 tag note | V0 tag conventions (`#V0`, `#V0a`) | Direct transcription of `Sheet2!B4` tag bullet; ground-truth match. |

Other axes (R, K, S, T, V, readiness bands) are not yet explicitly cited in the package body; their first in-package consumer will pull definitions via this file.

---

## 12. Maintenance

| Trigger | Action |
|---|---|
| Workbook updated on author's side | Re-copy xlsx into `references/`; re-run `scratch/build_eygp_extract.py`; diff §§3–9 of this file against the new extract; record a GROUND_TRUTH changelog entry below. |
| Paraphrase added to package body | Verification entry added to `reviews/ground_truth_verification_<date>.md`; this file's §11 updated. |
| SHA-256 mismatch at session start | Treat as a possible silent workbook edit; halt verification, regenerate extract, re-run `reviews/ground_truth_verification_<date>.md`. |

### Changelog

- **2026-04-17.** Initial registration. Source file ingested at `references/EYgp_Research_process_and_artifacts.xlsx` (SHA-256 `5bed11a1...79895`). Verbatim extract generated at `references/EYgp_Research_process_and_artifacts.md`. Baseline verification recorded in `reviews/ground_truth_verification_2026-04-17.md`.

---

*This file is part of the package's integrity floor. Alongside `GROUNDING_PROTOCOL.md`, it closes the loop: the protocol says "cite only what you have read"; this file says "when you read a stage definition, read this workbook".*
