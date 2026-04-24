# EYgp Research Process and Artifacts — Verbatim Extract

**Source file:** `references/EYgp_Research_process_and_artifacts.xlsx`

**Size:** 74770 bytes  
**SHA-256:** `5bed11a17615600db8b195e8b278ea7b5b65aa3ae94dad2fa680bac0df479895`  
**Extract generated:** 2026-04-17  
**Sheets:** Sheet2, Sheet1, Sheet3

**Provenance note.** This Markdown file is a *mechanical* transcription of every non-empty cell in the source workbook. It is not a paraphrase or a summary. When the package or any agent cites the EYgp framework, the authoritative source is the `.xlsx` file; this `.md` exists for grep-ability, version control, and offline reading. If the two disagree, the `.xlsx` wins and the extract should be regenerated via `scratch/build_eygp_extract.py`.

---

## Sheet inventory

| Sheet | Data range (rows × cols) | Topic (from section headers) |
|---|---|---|
| `Sheet2` | 28 × 7 | Problem setting (P0–P2), Related work (R0–R2), Knowledge content (K0–K2), Tools (T1–T5), Validation (V0–V5) |
| `Sheet1` | 17 × 6 | Solution artifacts S1–S5 (technical sketch → outline → note → working paper → published paper) |
| `Sheet3` | 30 × 7 | Readiness rating (no tick … ✓✓✓✓✓ 5-tick) applied per artifact type + Formalization block |

---

## Sheet2

Data range: rows 1..28, columns A..G.

#### Grid view — Sheet2

| (row) | A | B | C | D | E | F | G |
|---|---|---|---|---|---|---|---|
| 1 |  | Problem setting |  |  |  |  |  |
| 2 |  | P0 | P1 | P2 |  |  |  |
| 3 | artifact genre | collected readings on the problem phenomenon | characterization of problem phenom | Definition of research problems/questions/objectives |  |  |  |
| 4 |  | tags:<br> #V0 = contains potential test case eg for P2<br> #V0a = eg includes ana/reasoning  | a synthesis, digest, interpretation of the phenom, possibly based on some classification dimensions or theoretical framework. Refer to egs from V0. | the specific technical problems that your own research is going to address/solve (eg Given X, how to obtain Y). Is core of your Thesis Research Proposal. Specific enough to identify alternative tech approaches and solutuons, with tradeoffs. Illustrate with egs from V0. |  |  |  |
| 5 | format |   | sectioned paragraphs + tables/charts.  | sectioned paragraphs + tables/charts. <br>Research problems/questions labeled as q1 q11 q21 ...<br>Detailed subproblems are uncovered during S1, S2, S3. |  |  |  |
| 6 | text style | bib list, + a few bullet pts | use outline mode (eg in Word) to organize hierachically. Later, can extract/rearrange points/paragraphs selectively for different target docs. | use outline mode (eg in Word) to organize hierachically. Later, can extract/rearrange points/paragraphs selectively for different target docs. |  |  |  |
| 7 | khmap |  | hierarchical ME-map of problems and existing solutions | portion of the khmap from P1 that you are contributing to. Nodes are labeled with q#. <br>Updated with each qxxxS3 release at node qxxx. |  |  |  |
| 8 | thesis chapter | Bib | Motivation | Research Objectives |  |  |  |
| 9 |  | Related work  |  |  |  |  |  |
| 10 |  | R0 | R1 | R2 |  |  |  |
| 11 | artifact genre | collected readings on existing approaches/solutions | analysis of existing technical (eg model-based) approaches/solutions | comparative analysis of proposed solution and existing or alternative approaches/solutions |  |  |  |
| 12 | format | bib DB; or lists - grouped/tagged by category | sectioned paragraphs + tables/charts. same khmap from P1 and P2. |  |  |  |  |
| 13 | text style |  | use outline mode (eg in Word) to organize hierachically. Later, can extract/rearrange points/paragraphs selectively for different target docs. |  |  |  |  |
| 14 | thesis chapter | Bib | Related work | Contributions |  |  |  |
| 15 |  | Knowledge content - that is to be modeled and reasoned about in your subject-matter area (eg openness, coopetition, capabilities, ...) |  |  |  |  |  |
| 16 |  | K0 | K1 | K2 |  |  |  |
| 17 | artifact genre | collected readings/resources that provide knowledge content for eventual encoding in your modeling framework | analysis of this body of knowledge, organized according to some structure, but not yet formalized in terms of metamodel or axioms. Intuitive semantics only.  | encodings of selected knowledge content according to your framewrok. ie a reusable KB, supportable by (semi-) automated tools (for retrieval, application, or reasoning), |  |  |  |
| 18 | format | bib DB; or lists - grouped/tagged by category | concept maps, tables, taxonomies, ... | knowledge structures as defined in your technical solution metamodels (from S1-S5) eg NFR catalogues, i* SD patterns |  |  |  |
| 19 | thesis chapter | Bib | Background on subject-matter area | Solution chapters |  |  |  |
| 20 |  | Tools |  |  |  |  |  |
| 21 |  | T1 | T2 | T3 | T4 | T5 |  |
| 22 | artifact genre | mock-ups, experimental implementations | requirements, design specification  | functional research prototype | for limited release | for public release |  |
| 23 |  |  |  | research demo | usable by other researchers | usable by non-researchers |  |
| 24 | thesis chapter | N/A | Tools chapter | Tools chapter | -- optional -- | -- optional -- |  |
| 25 |  | Validation |  |  |  |  |  |
| 26 |  | V0 | V1 | V2 | V3 | V4 | V5 |
| 27 | artifact genre | egs for illustrating the technical problem. Can be used as test cases. With xref to P0 items (sources) | tiny toy egs. Aim for exemplars to illustrate explain the probem, and to stimulate other reshrs | larger egs on paper, preferably based on literature. Larger eg to serve as exemplars to benchmark/compare alt soln approaches re expressiveness, ana power. | real-world case study | user feedback | empir user studies, experimental design |
| 28 | thesis chapter | no. | selectively include (1 or 2) as egs in Solution chapter. | can be in Solution chapter, or in separate Validation chapter if substantive. | Validation chapter | Validation chapter | Validation chapter |


#### Raw cell dump — Sheet2

| Cell | Value |
|---|---|
| `B1` | Problem setting |
| `B2` | P0 |
| `C2` | P1 |
| `D2` | P2 |
| `A3` | artifact genre |
| `B3` | collected readings on the problem phenomenon |
| `C3` | characterization of problem phenom |
| `D3` | Definition of research problems/questions/objectives |
| `B4` | tags:<br> #V0 = contains potential test case eg for P2<br> #V0a = eg includes ana/reasoning  |
| `C4` | a synthesis, digest, interpretation of the phenom, possibly based on some classification dimensions or theoretical framework. Refer to egs from V0. |
| `D4` | the specific technical problems that your own research is going to address/solve (eg Given X, how to obtain Y). Is core of your Thesis Research Proposal. Specific enough to identify alternative tech approaches and solutuons, with tradeoffs. Illustrate with egs from V0. |
| `A5` | format |
| `C5` | sectioned paragraphs + tables/charts.  |
| `D5` | sectioned paragraphs + tables/charts. <br>Research problems/questions labeled as q1 q11 q21 ...<br>Detailed subproblems are uncovered during S1, S2, S3. |
| `A6` | text style |
| `B6` | bib list, + a few bullet pts |
| `C6` | use outline mode (eg in Word) to organize hierachically. Later, can extract/rearrange points/paragraphs selectively for different target docs. |
| `D6` | use outline mode (eg in Word) to organize hierachically. Later, can extract/rearrange points/paragraphs selectively for different target docs. |
| `A7` | khmap |
| `C7` | hierarchical ME-map of problems and existing solutions |
| `D7` | portion of the khmap from P1 that you are contributing to. Nodes are labeled with q#. <br>Updated with each qxxxS3 release at node qxxx. |
| `A8` | thesis chapter |
| `B8` | Bib |
| `C8` | Motivation |
| `D8` | Research Objectives |
| `B9` | Related work  |
| `B10` | R0 |
| `C10` | R1 |
| `D10` | R2 |
| `A11` | artifact genre |
| `B11` | collected readings on existing approaches/solutions |
| `C11` | analysis of existing technical (eg model-based) approaches/solutions |
| `D11` | comparative analysis of proposed solution and existing or alternative approaches/solutions |
| `A12` | format |
| `B12` | bib DB; or lists - grouped/tagged by category |
| `C12` | sectioned paragraphs + tables/charts. same khmap from P1 and P2. |
| `A13` | text style |
| `C13` | use outline mode (eg in Word) to organize hierachically. Later, can extract/rearrange points/paragraphs selectively for different target docs. |
| `A14` | thesis chapter |
| `B14` | Bib |
| `C14` | Related work |
| `D14` | Contributions |
| `B15` | Knowledge content - that is to be modeled and reasoned about in your subject-matter area (eg openness, coopetition, capabilities, ...) |
| `B16` | K0 |
| `C16` | K1 |
| `D16` | K2 |
| `A17` | artifact genre |
| `B17` | collected readings/resources that provide knowledge content for eventual encoding in your modeling framework |
| `C17` | analysis of this body of knowledge, organized according to some structure, but not yet formalized in terms of metamodel or axioms. Intuitive semantics only.  |
| `D17` | encodings of selected knowledge content according to your framewrok. ie a reusable KB, supportable by (semi-) automated tools (for retrieval, application, or reasoning), |
| `A18` | format |
| `B18` | bib DB; or lists - grouped/tagged by category |
| `C18` | concept maps, tables, taxonomies, ... |
| `D18` | knowledge structures as defined in your technical solution metamodels (from S1-S5) eg NFR catalogues, i* SD patterns |
| `A19` | thesis chapter |
| `B19` | Bib |
| `C19` | Background on subject-matter area |
| `D19` | Solution chapters |
| `B20` | Tools |
| `B21` | T1 |
| `C21` | T2 |
| `D21` | T3 |
| `E21` | T4 |
| `F21` | T5 |
| `A22` | artifact genre |
| `B22` | mock-ups, experimental implementations |
| `C22` | requirements, design specification  |
| `D22` | functional research prototype |
| `E22` | for limited release |
| `F22` | for public release |
| `D23` | research demo |
| `E23` | usable by other researchers |
| `F23` | usable by non-researchers |
| `A24` | thesis chapter |
| `B24` | N/A |
| `C24` | Tools chapter |
| `D24` | Tools chapter |
| `E24` | -- optional -- |
| `F24` | -- optional -- |
| `B25` | Validation |
| `B26` | V0 |
| `C26` | V1 |
| `D26` | V2 |
| `E26` | V3 |
| `F26` | V4 |
| `G26` | V5 |
| `A27` | artifact genre |
| `B27` | egs for illustrating the technical problem. Can be used as test cases. With xref to P0 items (sources) |
| `C27` | tiny toy egs. Aim for exemplars to illustrate explain the probem, and to stimulate other reshrs |
| `D27` | larger egs on paper, preferably based on literature. Larger eg to serve as exemplars to benchmark/compare alt soln approaches re expressiveness, ana power. |
| `E27` | real-world case study |
| `F27` | user feedback |
| `G27` | empir user studies, experimental design |
| `A28` | thesis chapter |
| `B28` | no. |
| `C28` | selectively include (1 or 2) as egs in Solution chapter. |
| `D28` | can be in Solution chapter, or in separate Validation chapter if substantive. |
| `E28` | Validation chapter |
| `F28` | Validation chapter |
| `G28` | Validation chapter |


---

## Sheet1

Data range: rows 1..17, columns A..F.

#### Grid view — Sheet1

| (row) | A | B | C | D | E | F |
|---|---|---|---|---|---|---|
| 1 |  | S1 | S2 | S3 | S4 | S5 |
| 2 | artifact genre | technical sketch | technical outline | technical note | working paper | published paper |
| 3 | stage | exploratory | experimental | consolidation + validation | consolidation + validation | dissemination |
| 4 | maturity of the idea | "inkling" | "kernel" | "nugget" | defensible | compelling |
| 5 | main purpose | for self, close collaborator | for self, close collaborator, supervisor | internal group feedback, critique. (Including possibly industry partner collaborators.) | detailed write-up as technical report. Can be refashioned into conf/journal paper(s), thesis chapter.  | submission for external review |
| 6 | style | rough sketches  | Bullet points/lists, full sentences. Q&A format may be helpful. | prose for internal audience | prose for "friendly" audience. Responses to potential critiques, reviewers' objections - as appendix.  | rhetorical prose targeted to a particular audience |
| 7 | format - Written | -- not required -- | -- not required -- | doc. <br>Version#: qxxxS3vx<br>qxxxS3vxrx for a stable "release" | doc | doc |
| 8 | length |  |  | 10-15p | 20-30p | 15-25p |
| 9 | format - Pres'n | hand sketches, or whiteboard+photo.  | Visio / Word ...-> ppt - Sequence of slides must tell a coherent story, offering a solution to a technical problem (defined in a P2 artifact). Early versions can be series of Visio tabs (each slide must have title, bullet text), transitioning eventually to ppt for S3 artifact. Ok to use Word (simulating a slide deck, typically each page has a figure/model with explanatory bullets.)  | ppt - detailed technical pres'n on single (small) research advance.  | internal technical pres'n, combining several research advances, allowing material to be extracted for one or more conference or journal papers. | polished public pres'n |
| 10 | length | 1-5 figs | 10-15s | 15-25s; 20'+20' | 25-50s; 40' + 20'Q&A | 20-25s; 20'+10' |
| 11 | content | small unit of technical advance | Concepts/terms, defs, propositions, conclusions (eg new capabilities offered by solution). <br>Usage guidelines/rules, rationales. <br>Assumptions, hypotheses.<br>Early versions can have long to-do lists.<br>Open tech issues identified should be added to P2 khmap, assigned q# | Motivation <1p; Related wk <1p (5-10 refs); Technical core 5-10p; Eg/case studies/empir data 3-5p; alt approaches 1p | Motivation >1p; Relwk compared >1p (20-50 refs); detailed rationales. Integrates relevant sections from P1, P2; R2; K2; V. |  |
| 12 | contextualized | no. Describes solution only.  | somewhat. Refers to tech problem/question defined in P2 artifact. | yes. Refers to tech problem qxxx in P2, related work in R2. Contains relevant pieces K2 and V1. | a full, complete self-contained paper. contributions justified in relation to RelWk. | engaging in "conversation" in a research community |
| 13 | revision cycle | daily | weekly. The tech outline (S2) should be the main vehicle for our weekly meeting - ie you should have iterated your S1 during the week so that the solution idea is mature enough for discussion in the form of an S2. | monthly. You should be concerned if your technical solution idea has not matured into a technical note after one month.  | semester | when ready |
| 14 | lead-time for feedback |  | 24 hrs | 24 hrs | 48 hrs | 4 weeks for paper outline; 3 weeks first draft assembled from S4 or S3; 1 week for complete draft. |
| 15 | validation level | V1 (toy egs) | >= V1 | >= V1 | >= V2 (larger egs) |  |
| 16 | figures |  | Prelim versions of S2 can have hand-drawn figs or white-broad photos | Complex models should be explained incrementally, by building them up through a series of figures. It may also be helpful to present highlights of graphical models using a different format, eg. as tables, for easier comprehension. |  |  |
| 17 | quality threshold needed to start drafting next stage artifact. Stages are overlapping. | promising solution explained w egs, for a clear, coherent technical question/problem (qxxx from P2) | Core idea of the solution coherent enough to be written up. Continue improving or fleshing out the S2, while updating the S3 from time to time.  | Defensible in front of colleagues (internal peer group). Scope of material could be enough for a workshop paper. |  | Defensible in public. Ready to submit. |


#### Raw cell dump — Sheet1

| Cell | Value |
|---|---|
| `B1` | S1 |
| `C1` | S2 |
| `D1` | S3 |
| `E1` | S4 |
| `F1` | S5 |
| `A2` | artifact genre |
| `B2` | technical sketch |
| `C2` | technical outline |
| `D2` | technical note |
| `E2` | working paper |
| `F2` | published paper |
| `A3` | stage |
| `B3` | exploratory |
| `C3` | experimental |
| `D3` | consolidation + validation |
| `E3` | consolidation + validation |
| `F3` | dissemination |
| `A4` | maturity of the idea |
| `B4` | "inkling" |
| `C4` | "kernel" |
| `D4` | "nugget" |
| `E4` | defensible |
| `F4` | compelling |
| `A5` | main purpose |
| `B5` | for self, close collaborator |
| `C5` | for self, close collaborator, supervisor |
| `D5` | internal group feedback, critique. (Including possibly industry partner collaborators.) |
| `E5` | detailed write-up as technical report. Can be refashioned into conf/journal paper(s), thesis chapter.  |
| `F5` | submission for external review |
| `A6` | style |
| `B6` | rough sketches  |
| `C6` | Bullet points/lists, full sentences. Q&A format may be helpful. |
| `D6` | prose for internal audience |
| `E6` | prose for "friendly" audience. Responses to potential critiques, reviewers' objections - as appendix.  |
| `F6` | rhetorical prose targeted to a particular audience |
| `A7` | format - Written |
| `B7` | -- not required -- |
| `C7` | -- not required -- |
| `D7` | doc. <br>Version#: qxxxS3vx<br>qxxxS3vxrx for a stable "release" |
| `E7` | doc |
| `F7` | doc |
| `A8` | length |
| `D8` | 10-15p |
| `E8` | 20-30p |
| `F8` | 15-25p |
| `A9` | format - Pres'n |
| `B9` | hand sketches, or whiteboard+photo.  |
| `C9` | Visio / Word ...-> ppt - Sequence of slides must tell a coherent story, offering a solution to a technical problem (defined in a P2 artifact). Early versions can be series of Visio tabs (each slide must have title, bullet text), transitioning eventually to ppt for S3 artifact. Ok to use Word (simulating a slide deck, typically each page has a figure/model with explanatory bullets.)  |
| `D9` | ppt - detailed technical pres'n on single (small) research advance.  |
| `E9` | internal technical pres'n, combining several research advances, allowing material to be extracted for one or more conference or journal papers. |
| `F9` | polished public pres'n |
| `A10` | length |
| `B10` | 1-5 figs |
| `C10` | 10-15s |
| `D10` | 15-25s; 20'+20' |
| `E10` | 25-50s; 40' + 20'Q&A |
| `F10` | 20-25s; 20'+10' |
| `A11` | content |
| `B11` | small unit of technical advance |
| `C11` | Concepts/terms, defs, propositions, conclusions (eg new capabilities offered by solution). <br>Usage guidelines/rules, rationales. <br>Assumptions, hypotheses.<br>Early versions can have long to-do lists.<br>Open tech issues identified should be added to P2 khmap, assigned q# |
| `D11` | Motivation <1p; Related wk <1p (5-10 refs); Technical core 5-10p; Eg/case studies/empir data 3-5p; alt approaches 1p |
| `E11` | Motivation >1p; Relwk compared >1p (20-50 refs); detailed rationales. Integrates relevant sections from P1, P2; R2; K2; V. |
| `A12` | contextualized |
| `B12` | no. Describes solution only.  |
| `C12` | somewhat. Refers to tech problem/question defined in P2 artifact. |
| `D12` | yes. Refers to tech problem qxxx in P2, related work in R2. Contains relevant pieces K2 and V1. |
| `E12` | a full, complete self-contained paper. contributions justified in relation to RelWk. |
| `F12` | engaging in "conversation" in a research community |
| `A13` | revision cycle |
| `B13` | daily |
| `C13` | weekly. The tech outline (S2) should be the main vehicle for our weekly meeting - ie you should have iterated your S1 during the week so that the solution idea is mature enough for discussion in the form of an S2. |
| `D13` | monthly. You should be concerned if your technical solution idea has not matured into a technical note after one month.  |
| `E13` | semester |
| `F13` | when ready |
| `A14` | lead-time for feedback |
| `C14` | 24 hrs |
| `D14` | 24 hrs |
| `E14` | 48 hrs |
| `F14` | 4 weeks for paper outline; 3 weeks first draft assembled from S4 or S3; 1 week for complete draft. |
| `A15` | validation level |
| `B15` | V1 (toy egs) |
| `C15` | >= V1 |
| `D15` | >= V1 |
| `E15` | >= V2 (larger egs) |
| `A16` | figures |
| `C16` | Prelim versions of S2 can have hand-drawn figs or white-broad photos |
| `D16` | Complex models should be explained incrementally, by building them up through a series of figures. It may also be helpful to present highlights of graphical models using a different format, eg. as tables, for easier comprehension. |
| `A17` | quality threshold needed to start drafting next stage artifact. Stages are overlapping. |
| `B17` | promising solution explained w egs, for a clear, coherent technical question/problem (qxxx from P2) |
| `C17` | Core idea of the solution coherent enough to be written up. Continue improving or fleshing out the S2, while updating the S3 from time to time.  |
| `D17` | Defensible in front of colleagues (internal peer group). Scope of material could be enough for a workshop paper. |
| `F17` | Defensible in public. Ready to submit. |


---

## Sheet3

Data range: rows 1..30, columns A..G.

#### Grid view — Sheet3

| (row) | A | B | C | D | E | F | G |
|---|---|---|---|---|---|---|---|
| 1 |  | "Readiness %" is a combined assessment of quality and completeness of the artifact (or sub-section).<br>Quality includes technical substance, rigor, presentation flow & understandability. |  |  |  |  |  |
| 2 | Readiness rating  | no tick | ✓ 1-tick  | ✓✓ 2-tick  | ✓✓✓ 3-tick  | ✓✓✓✓ 4-tick  | ✓✓✓✓✓ 5-tick  |
| 3 | Problem characterization |  |  |  |  |  |  |
| 4 | P0 refs |  | 5-20% ready | 20%-50% | 50-80%. Start P1 | 80%-99% | complete, ready for release |
| 5 | P1 non-tech prob formulation |  | 5-20% ready | 20%-50% | 50-80%. Start P2 | 80%-99% | complete, ready for release |
| 6 | P2 technical research prob defn |  | 5-20% ready | 20%-50%. Start S1 | 50-80%.  | 80%-99% | complete, ready for release |
| 7 | Related work |  |  |  |  |  |  |
| 8 | R0 refs |  | 5-20% ready. Start R1 | 20%-50% | 50-80% | 80%-99% | complete, ready for release |
| 9 | R1 analysis of related work, alt approaches |  | 5-20% ready | 20%-50% | 50-80% | 80%-99% | complete, ready for release |
| 10 | R2 contributions of proposed solution, compared to related work |  | 5-20% ready | 20%-50% | 50-80% | 80%-99% | complete, ready for release |
| 11 | Solution |  |  |  |  |  |  |
| 12 | S1 sketch | 0-5% or unrated | 5-20% ready | 20%-50% | 50-80%. Start S2 | n/a. Work on S2 instead |  |
| 13 | S2 outline | 0-5% or unrated | 5-20% ready | 20%-50% | 50-80%. Start S3 | 80%-99% | n/a. Work on S3 instead |
| 14 | S3 note | 0-5% or unrated | 5-20% ready | 20%-50% | 50-80% | 80%-99%. Start S5 or S4 | complete, ready for internal release  |
| 15 | S4 report | 0-5% or unrated | 5-20% ready | 20%-50% | 50-80%. Start S5 | 80%-99% | complete, ready for release to friendly audience |
| 16 | S5 pub | 0-5% or unrated | 5-20% ready | 20%-50% | 50-80% | 80%-95% | complete, ready to submit |
| 17 | Domain knowledge |  |  |  |  |  |  |
| 18 | K0 |  |  |  |  |  |  |
| 19 | K1 |  |  |  |  |  |  |
| 20 | K2 |  |  |  |  |  |  |
| 21 | Validation |  |  |  |  |  |  |
| 22 | V0 source material for egs |  | 5-20% ready. Start V1 for S1 or S2 | 20%-50% | 50-80% | 80%-99%.  | n/a |
| 23 | V1 toy egs |  | 5-20% ready | 20%-50% | 50-80%. Start V2 | 80%-99%.  | complete, ready for release  |
| 24 | V2 larger eg, from lit, prefer benchmark |  | 5-20% ready | 20%-50% | 50-80% | 80%-99%.  | complete, ready for release  |
| 25 | V3 real-world case study |  | 5-20% ready | 20%-50% | 50-80% | 80%-99%.  | complete, ready for release  |
| 26 | V4 user feedback |  | 5-20% ready | 20%-50% | 50-80% | 80%-99%.  | complete, ready for release  |
| 27 | V5 empir study |  | 5-20% ready | 20%-50% | 50-80% | 80%-99%.  | complete, ready for release  |
| 28 | Formalization |  |  |  |  |  |  |
| 29 | abstract formulation of problem and solution - eg math or logical formalism. |  |  |  |  |  |  |
| 30 | example with no reliance on domain knowledge from a familiar domain |  |  |  |  |  |  |


#### Raw cell dump — Sheet3

| Cell | Value |
|---|---|
| `B1` | "Readiness %" is a combined assessment of quality and completeness of the artifact (or sub-section).<br>Quality includes technical substance, rigor, presentation flow & understandability. |
| `A2` | Readiness rating  |
| `B2` | no tick |
| `C2` | ✓ 1-tick  |
| `D2` | ✓✓ 2-tick  |
| `E2` | ✓✓✓ 3-tick  |
| `F2` | ✓✓✓✓ 4-tick  |
| `G2` | ✓✓✓✓✓ 5-tick  |
| `A3` | Problem characterization |
| `A4` | P0 refs |
| `C4` | 5-20% ready |
| `D4` | 20%-50% |
| `E4` | 50-80%. Start P1 |
| `F4` | 80%-99% |
| `G4` | complete, ready for release |
| `A5` | P1 non-tech prob formulation |
| `C5` | 5-20% ready |
| `D5` | 20%-50% |
| `E5` | 50-80%. Start P2 |
| `F5` | 80%-99% |
| `G5` | complete, ready for release |
| `A6` | P2 technical research prob defn |
| `C6` | 5-20% ready |
| `D6` | 20%-50%. Start S1 |
| `E6` | 50-80%.  |
| `F6` | 80%-99% |
| `G6` | complete, ready for release |
| `A7` | Related work |
| `A8` | R0 refs |
| `C8` | 5-20% ready. Start R1 |
| `D8` | 20%-50% |
| `E8` | 50-80% |
| `F8` | 80%-99% |
| `G8` | complete, ready for release |
| `A9` | R1 analysis of related work, alt approaches |
| `C9` | 5-20% ready |
| `D9` | 20%-50% |
| `E9` | 50-80% |
| `F9` | 80%-99% |
| `G9` | complete, ready for release |
| `A10` | R2 contributions of proposed solution, compared to related work |
| `C10` | 5-20% ready |
| `D10` | 20%-50% |
| `E10` | 50-80% |
| `F10` | 80%-99% |
| `G10` | complete, ready for release |
| `A11` | Solution |
| `A12` | S1 sketch |
| `B12` | 0-5% or unrated |
| `C12` | 5-20% ready |
| `D12` | 20%-50% |
| `E12` | 50-80%. Start S2 |
| `F12` | n/a. Work on S2 instead |
| `A13` | S2 outline |
| `B13` | 0-5% or unrated |
| `C13` | 5-20% ready |
| `D13` | 20%-50% |
| `E13` | 50-80%. Start S3 |
| `F13` | 80%-99% |
| `G13` | n/a. Work on S3 instead |
| `A14` | S3 note |
| `B14` | 0-5% or unrated |
| `C14` | 5-20% ready |
| `D14` | 20%-50% |
| `E14` | 50-80% |
| `F14` | 80%-99%. Start S5 or S4 |
| `G14` | complete, ready for internal release  |
| `A15` | S4 report |
| `B15` | 0-5% or unrated |
| `C15` | 5-20% ready |
| `D15` | 20%-50% |
| `E15` | 50-80%. Start S5 |
| `F15` | 80%-99% |
| `G15` | complete, ready for release to friendly audience |
| `A16` | S5 pub |
| `B16` | 0-5% or unrated |
| `C16` | 5-20% ready |
| `D16` | 20%-50% |
| `E16` | 50-80% |
| `F16` | 80%-95% |
| `G16` | complete, ready to submit |
| `A17` | Domain knowledge |
| `A18` | K0 |
| `A19` | K1 |
| `A20` | K2 |
| `A21` | Validation |
| `A22` | V0 source material for egs |
| `C22` | 5-20% ready. Start V1 for S1 or S2 |
| `D22` | 20%-50% |
| `E22` | 50-80% |
| `F22` | 80%-99%.  |
| `G22` | n/a |
| `A23` | V1 toy egs |
| `C23` | 5-20% ready |
| `D23` | 20%-50% |
| `E23` | 50-80%. Start V2 |
| `F23` | 80%-99%.  |
| `G23` | complete, ready for release  |
| `A24` | V2 larger eg, from lit, prefer benchmark |
| `C24` | 5-20% ready |
| `D24` | 20%-50% |
| `E24` | 50-80% |
| `F24` | 80%-99%.  |
| `G24` | complete, ready for release  |
| `A25` | V3 real-world case study |
| `C25` | 5-20% ready |
| `D25` | 20%-50% |
| `E25` | 50-80% |
| `F25` | 80%-99%.  |
| `G25` | complete, ready for release  |
| `A26` | V4 user feedback |
| `C26` | 5-20% ready |
| `D26` | 20%-50% |
| `E26` | 50-80% |
| `F26` | 80%-99%.  |
| `G26` | complete, ready for release  |
| `A27` | V5 empir study |
| `C27` | 5-20% ready |
| `D27` | 20%-50% |
| `E27` | 50-80% |
| `F27` | 80%-99%.  |
| `G27` | complete, ready for release  |
| `A28` | Formalization |
| `A29` | abstract formulation of problem and solution - eg math or logical formalism. |
| `A30` | example with no reliance on domain knowledge from a familiar domain |


---
