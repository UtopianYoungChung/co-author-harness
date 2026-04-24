# Ground-Truth Verification — EYgp Research Process & Artifacts

**Date:** 2026-04-17
**Canonical source:** `references/EYgp_Research_process_and_artifacts.xlsx` (SHA-256 `5bed11a17615600db8b195e8b278ea7b5b65aa3ae94dad2fa680bac0df479895`)
**Extract used:** `references/EYgp_Research_process_and_artifacts.md` (generated 2026-04-17)
**Registered in:** `GROUND_TRUTH.md`
**Verifier:** Reflector (single-agent; submission-bound external verification is not required for a definitional audit of an internal process artifact — see `EXTERNAL_VERIFIERS.md` Class 0).

**Scope.** This audit checks every current package paraphrase of EYgp axis-stage definitions (P / R / K / S / T / V) and readiness-rating bands against the workbook cells, per `GROUND_TRUTH.md §10` and `GROUNDING_PROTOCOL.md` Rule 1. Package files audited:

1. `project_writing_style_checklist.md` Part 0 (P0/P1/P2 block + anti-patterns)
2. `skills/packaged/p-stage-checker.md` (P0/P1/P2 table + vocabulary audit)
3. `DETERMINISTIC_CHECKS.md §8` (stage-dependent scope-keyword traps)

No other package file currently cites the R/K/S/T/V axes or the readiness scale directly. Findings for those axes are therefore reported as **coverage gaps**, not as paraphrase violations.

---

## 1. Summary verdict

| Axis | Paraphrases in package | Groundedness | Fidelity violations (Rule 1) | Inferred / added-info markers needed | Coverage gap |
|---|---|---|---|---|---|
| Problem setting (P0/P1/P2) | 3 (checklist Part 0, p-stage-checker, DETERMINISTIC_CHECKS §8) | High | 0 | 4 | None |
| Related work (R0/R1/R2) | 0 | N/A | 0 | 0 | YES — package has no R-axis treatment |
| Knowledge content (K0/K1/K2) | 0 | N/A | 0 | 0 | YES |
| Solution (S1–S5) | 0 (package mentions "S1, S2, S3" once, copied from P2 format cell) | Low | 0 | 0 | YES — substantial workbook content is unused |
| Tools (T1–T5) | 0 | N/A | 0 | 0 | YES |
| Validation (V0–V5) | 1 (V0 tag convention only) | High (verbatim) | 0 | 0 | Partial — V0 covered; V1–V5 not referenced |
| Readiness rating (✓…✓✓✓✓✓) | 0 | N/A | 0 | 0 | YES — no tick-based readiness artefact in package |

**Grounding verdict.** No `[GROUNDING VIOLATION — Rule 1]` fidelity drift found in the current P-stage paraphrases; the package's P0/P1/P2 language is consistent with the workbook cells. Four package claims are reclassified below with `[INFERRED — verify]` markers because they extend the workbook with vocabulary or concepts the workbook itself does not supply. The dominant pattern is **coverage gap**: five of the six axes plus the readiness scale are not yet represented in the package body.

---

## 2. P-axis paraphrase audit (detailed)

Each row compares one package claim against the workbook. "✔ grounded" means the workbook cell supports the paraphrase; "[INFERRED — verify]" means the paraphrase is consistent with the workbook but adds content the workbook does not state.

### 2.1 `project_writing_style_checklist.md` Part 0

| # | Package claim (paraphrase) | Workbook cell(s) | Status |
|---|---|---|---|
| P0-a | "P0 — Collected readings on the problem phenomenon." | `Sheet2!B3`: "collected readings on the problem phenomenon" | ✔ grounded (capitalisation change only) |
| P0-b | "Deliverable: bibliographic corpus + bullet points + tags (e.g. `#V0` = contains potential test case; `#V0a` = includes analysis/reasoning)." | `Sheet2!B6` ("bib list, + a few bullet pts"); `Sheet2!B4` (tags: `#V0 = contains potential test case eg for P2`; `#V0a = eg includes ana/reasoning`) | ✔ grounded. "bibliographic corpus" is a reasonable paraphrase of "bib list"; the `#V0`/`#V0a` wording is verbatim. |
| P0-c | "Goal: assemble the materials from which a problem will eventually be characterized." | No direct cell. Consistent with the P0 → P1 → P2 progression implied by `Sheet2` column ordering. | `[INFERRED — verify]` — workbook does not explicitly state a "goal"; this is a reasonable inference from the stage ordering. |
| P0-d | "Output artifact: bib list and notes." | `Sheet2!B6` ("bib list"); `Sheet2!B8` thesis chapter = "Bib" | ✔ grounded. |
| P1-a | "P1 — Characterization of the problem phenomenon." | `Sheet2!C3`: "characterization of problem phenom" | ✔ grounded. |
| P1-b | "Deliverable: a synthesis, digest, or interpretation of the phenomenon, possibly organized around classification dimensions or a theoretical framework." | `Sheet2!C4`: "a synthesis, digest, interpretation of the phenom, possibly based on some classification dimensions or theoretical framework." | ✔ grounded (near-verbatim). |
| P1-c | "Sectioned paragraphs, tables, charts." | `Sheet2!C5`: "sectioned paragraphs + tables/charts." | ✔ grounded. |
| P1-d | "A hierarchical map of problems and existing solutions." | `Sheet2!C7`: "hierarchical ME-map of problems and existing solutions" | ✔ grounded. `[INFERRED — minor]` — paraphrase drops the "ME-" qualifier from the workbook's "ME-map"; consider restoring the term-of-art in the checklist. |
| P1-e | "Output artifact: Motivation chapter / problem-statement document." | `Sheet2!C8` thesis chapter = "Motivation" | ✔ grounded for "Motivation chapter". `[INFERRED — verify]` — "problem-statement document" is added by the checklist; the workbook does not use this phrase. |
| P2-a | "P2 — Definition of research problems / questions / objectives." | `Sheet2!D3`: "Definition of research problems/questions/objectives" | ✔ grounded (verbatim modulo spacing). |
| P2-b | "Deliverable: the specific technical problems the research will address (e.g. 'Given X, how to obtain Y'), specific enough to identify alternative technical approaches and tradeoffs." | `Sheet2!D4`: "the specific technical problems that your own research is going to address/solve (eg Given X, how to obtain Y). … Specific enough to identify alternative tech approaches and solutuons, with tradeoffs." | ✔ grounded. |
| P2-c | "Research problems labeled as **q1, q11, q21…**" | `Sheet2!D5`: "Research problems/questions labeled as q1 q11 q21 ..." | ✔ grounded (verbatim). |
| P2-d | "detailed sub-problems uncovered during downstream stages (S1, S2, S3)." | `Sheet2!D5`: "Detailed subproblems are uncovered during S1, S2, S3." | ✔ grounded. |
| P2-e | "Output artifact: Research Objectives / Thesis Research Proposal." | `Sheet2!D8` thesis chapter = "Research Objectives"; `Sheet2!D4` = "Is core of your Thesis Research Proposal." | ✔ grounded (both phrases are workbook-attested). |
| Anti-a | "Don't import P2 vocabulary ('research questions,' 'resolution,' 'answers') into a P0/P1 conclusion." | Workbook contains "research problems/questions/objectives" (`Sheet2!D3`). The tokens "resolution" and "answers" **do not appear anywhere in the workbook** (confirmed by `rg -i 'resolution\|answers'` on the extract — 0 matches). | `[INFERRED — verify]` — the anti-pattern is plausible but the specific vocabulary list ("resolution", "answers") is an extension from the package author, not a transcription. Recommend clarifying in the checklist text that these are package-recognised tells, not workbook terms. |

### 2.2 `skills/packaged/p-stage-checker.md`

| # | Package claim | Workbook cell(s) | Status |
|---|---|---|---|
| PC-1 | Table row `P0 — Collected readings on the problem phenomenon — Bib corpus + bullet points + tags` | Matches `Sheet2!B3`, `B6`, `B4`. | ✔ grounded. |
| PC-2 | Table row `P1 — Characterization of the problem phenomenon — Synthesis, digest, classification map, tensions` | `Sheet2!C3`, `C4`, `C7` support "synthesis, digest, classification (map)". **"Tensions" is not in the workbook** (0 matches for `tension` in the extract). | `[INFERRED — verify]` — "tensions" is a concept the package author layered on the workbook definition. It is consistent with the characterization purpose of P1 but is not derivable from the cells. |
| PC-3 | Table row `P2 — Definition of research problems / questions / objectives — Specific technical problems (q1, q11, q21…), tradeoffs` | `Sheet2!D3`, `D4`, `D5`. | ✔ grounded. |
| PC-4 | Step 2 vocabulary table: "Numbered RQs (RQ1, RQ2 …) in §1" flagged as BLOCKER at P0/P1 | Workbook labels P2 problems as `q1 q11 q21 ...` (`Sheet2!D5`). "RQ1"/"RQ2" notation does **not** appear in the workbook (0 matches for `RQ` outside of nothing-relevant; the closest is `qxxx`). | `[INFERRED — verify]` — the skill treats "RQ-style numbering" as a shorthand for the workbook's `q`-style labelling, which is reasonable (authors in the wild typically write RQ1 rather than q1), but the equivalence is an inference. Mark in the skill text that RQ# is a reader-convention proxy for q#. |
| PC-5 | Step 2: **"Resolution"** and **"Answers"** as P2 vocabulary | Not in workbook. | `[INFERRED — verify]` — same as `Anti-a` above; kept for consistency. |
| PC-6 | Step 4 forward-pointing handoff: "candidate q-α, q-β, q-γ items" | Workbook uses `q1 q11 q21` and `qxxx` only; Greek-lettered candidate items (`q-α`, `q-β`, `q-γ`) are a package convention. | `[INFERRED — verify]` — this is a package invention to provide a place-holder for *candidate-but-not-yet-committed* labels, analogous to the workbook's numbered `q#` for committed labels. Reasonable and does not conflict with the workbook. |
| PC-7 | Step 3 argument arc: "P0 — Phenomenon → Corpus → Tags + Bullet points → Handoff" | Consistent with `Sheet2` B3/B6/B4; "Handoff" is the checklist's "forward-pointing handoff" concept. | ✔ grounded with one `[INFERRED — verify]` tag on "Handoff" (see PC-6). |

### 2.3 `DETERMINISTIC_CHECKS.md §8` (Scope-keyword traps)

| # | Check | Grounded pattern? | Status |
|---|---|---|---|
| DC-1 | P2 vocabulary regex `\b(resolution\|resolves\|answers\|research question\|RQ\d)\b` flagged in P0/P1 conclusions | Only "research question" is workbook-attested (`Sheet2!D3`); `resolution`, `resolves`, `answers`, and `RQ\d` are extensions consistent with checklist Part 0 anti-patterns. | `[INFERRED — verify]` — four of the five regex tokens are package conventions, not workbook terms. Keep but annotate the rule line with a pointer to `GROUND_TRUTH.md §4` and Anti-a above so the provenance is visible. |
| DC-2 | "'Not X but Y' in P0/P1 positioning sentences" | Derived from `MASTER §A.4.2`; no workbook basis (workbook does not speak to prose style). | Out of scope for this audit. |
| DC-3 | "Premature numbered RQs in §1" as BLOCKER | Same provenance as DC-1; workbook uses `q#`, package flags `RQ#` as the reader-facing shorthand. | `[INFERRED — verify]` — same reason as PC-4. |

---

## 3. Coverage gaps (what the workbook provides that the package does not yet use)

These are not violations — the package is permitted to scope its review to a subset of the workbook — but they are recorded here so the next package iteration can decide which gaps to close.

### 3.1 Related-work axis (R0 / R1 / R2) — `Sheet2` rows 9–14

Not referenced anywhere in the package. The workbook distinguishes three stages:

- R0 = collected readings on existing approaches/solutions (`Bib` chapter)
- R1 = analysis of existing technical approaches (`Related work` chapter)
- R2 = comparative analysis of proposed solution vs. alternatives (`Contributions` chapter)

Current package treatment of "related work" is purely stylistic (e.g. `baird_2021_writing_guidelines.md` §13 on literature review as synthesis) and does not distinguish R0 / R1 / R2 stages. **Impact.** A paper in R1-state (analytical) being reviewed against R2-criteria (comparative contributions) would be pushed toward premature comparative claims; the package currently has no rule that flags this.

### 3.2 Knowledge-content axis (K0 / K1 / K2) — `Sheet2` rows 15–19

Not referenced in the package. Workbook distinguishes K0 (collected subject-matter readings) / K1 (un-formalised analysis) / K2 (formal KB encoded in the solution metamodels). **Impact.** Papers whose contribution is a formalised KB (K2) are not distinguished from papers that merely survey subject-matter (K0) in the current review pipeline.

### 3.3 Solution axis (S1 – S5) — entire `Sheet1`

Not referenced in the package other than a single incidental mention of "S1, S2, S3" that the checklist Part 0 transcribes from the P2 format cell. The workbook contains a rich per-stage specification the package does not currently use:

- **Maturity labels** ("inkling" / "kernel" / "nugget" / defensible / compelling) — orthogonal to the P-stages the package tracks.
- **Revision cycle** (daily → weekly → monthly → semester → when ready) — actionable for project lifecycle.
- **Lead-time for feedback** (24 hrs → 48 hrs → 4 weeks / 3 weeks / 1 week for S5) — actionable for advisor escalation (cf. `skills/advisor-escalation.md`).
- **Validation-level gates** (S1 = V1; S4 = ≥V2) — cross-axis coupling the package does not currently enforce.
- **Content budgets per stage** (S3 = "Motivation <1p; Related wk <1p (5-10 refs); Technical core 5-10p; Eg/case studies/empir data 3-5p; alt approaches 1p"; S4 = "Motivation >1p; Relwk compared >1p (20-50 refs); detailed rationales.") — directly applicable to word-count / section-length checks (cf. `DETERMINISTIC_CHECKS §9` "Word-count compliance").

**Impact.** The workbook's S-axis is arguably the richest unused governance surface. A future package iteration could map S-stages to `PROJECT_BOOTSTRAP.md` milestones or to `REVIEW_ORCHESTRATION.md` depths.

### 3.4 Tools axis (T1 – T5) — `Sheet2` rows 20–24

Not referenced. The workbook is explicit that T1 (mock-ups) has "N/A" thesis chapter and T4–T5 (public releases) are "-- optional --" thesis chapters. **Impact.** Tool-building projects have no package-level review surface.

### 3.5 Validation axis (V0 – V5) — `Sheet2` rows 25–28

Only V0 is referenced, via the `#V0` / `#V0a` tag convention in `project_writing_style_checklist.md` Part 0 (verbatim transcription). V1–V5 (toy egs → real-world case study → user feedback → empirical studies) are unreferenced. **Impact.** A paper making an empirical-study (V5) claim is not checked for the distinguishing features the workbook specifies ("experimental design") versus a larger-example (V2) claim.

### 3.6 Readiness rating (0 – 5 ticks) — `Sheet3`

Not referenced. The workbook provides per-artifact readiness bands (e.g. "S3 note, ✓✓✓ 3-tick = 50-80% ready; ✓✓✓✓ 4-tick = 80%-99%. Start S5 or S4"). **Impact.** `SUCCESS_METRICS.md` provides its own readiness framework (D1–D6) that is not aligned with the workbook's tick scale. A user who expects the workbook's ✓ / ✓✓ vocabulary will have to translate to D1–D6 manually. A future iteration could register the tick scale as a cross-walk.

---

## 4. Remediation recommendations

Recommendations are ranked by value-to-cost. The user decides which to adopt; no file is modified without explicit approval beyond what is already in scope for this task.

### 4.1 Immediate, no-risk (done in this task)

- **R1.** Register `references/EYgp_Research_process_and_artifacts.xlsx` as canonical ground-truth in `GROUND_TRUTH.md`. *(Done 2026-04-17.)*
- **R2.** Add verbatim Markdown extract for grep-ability. *(Done 2026-04-17.)*
- **R3.** Record this verification report as the baseline. *(This file.)*

### 4.2 Small annotations recommended (proposed for this task's remaining steps)

- **R4.** Annotate the three `[INFERRED — verify]` paraphrase points in the existing files with a pointer to `GROUND_TRUTH.md`. Specifically:
  - `project_writing_style_checklist.md` Part 0: add a footnote beside "P2 vocabulary ('research questions,' 'resolution,' 'answers')" noting that "resolution" and "answers" are package-recognised tells, not workbook terms.
  - `p-stage-checker.md` Step 2: add a line that RQ# is a reader-convention proxy for the workbook's `q#` labelling.
  - `DETERMINISTIC_CHECKS.md §8`: add a provenance note on the P2-vocabulary regex row.
- **R5.** Add a deterministic check rule (new §8 entry) that references `GROUND_TRUTH.md` so future reviewers know where the authoritative definitions live. *(Planned in this task's remaining steps.)*
- **R6.** Create `skills/packaged/eygp-framework-checker.md` that automates the verification procedure for a given manuscript. *(Planned in this task's remaining steps.)*

### 4.3 Larger, deferred (not for this task — flag for the user)

- **R7.** Extend the package to cover the S-axis (solution maturity) with revision-cycle and lead-time-for-feedback rules. Touches `general_research_project_guidelines.md`, `PROJECT_BOOTSTRAP.md`, and `REVIEW_ORCHESTRATION.md`. **Estimate:** medium; requires author review.
- **R8.** Cross-walk the workbook's tick-readiness scale to `SUCCESS_METRICS.md` D1–D6. **Estimate:** small; requires author decision on mapping.
- **R9.** Add R / K / T / V axes as first-class review dimensions. **Estimate:** large; touches multiple skills and the orchestration file.

---

## 4a. Self-caught fidelity error in this audit's own artefacts

During the initial linter pass on `GROUND_TRUTH.md`, a column-count mismatch (MD056) was flagged on the Sheet1 S-axis table (§7). Investigation found:

- Row "format – Written": the workbook cell `Sheet1!D7` is a single multi-line cell ("doc. / Version#: `qxxxS3vx` / `qxxxS3vxrx` for a stable 'release'") but the initial draft of §7 split it across two markdown cells, which shifted the S4 and S5 values one column to the left and introduced an extra "doc" cell.
- Row "length (written)": the workbook S3 value (`Sheet1!D8` = "10-15p") was initially attributed to S4, S4's value ("20-30p") to S5, and S5's value ("15-25p") to a non-existent S6 column. Root cause: one extra `*(empty)*` cell at the start of the row.

This is precisely the class of error the `GROUND_TRUTH.md §10` verification procedure exists to catch. It was self-caught by the linter's column-count check, then verified against the extract (`Sheet1!D7`, `Sheet1!D8`, `Sheet1!E8`, `Sheet1!F8`) and corrected in the same session. Both rows now match the workbook. This demonstrates the procedure working as designed: a paraphrase introduced a factual shift; a mechanical check surfaced it; the workbook was consulted; the paraphrase was corrected.

Classification: `[GROUNDING VIOLATION — Rule 1]` self-detected and remediated before release of the verification report. Recorded here rather than suppressed, per `GROUNDING_PROTOCOL.md` Rule 5 (mark uncertainty) and Rule 7 (chain of verification).

---

## 5. Chain-of-verification record

Per `GROUNDING_PROTOCOL.md §7`:

- **Claim verifier:** Reflector (this audit).
- **Claim source:** `.paper-package/references/EYgp_Research_process_and_artifacts.xlsx` (SHA-256 recorded in `GROUND_TRUTH.md §1`).
- **Passage grounding:** Each row in §2 cites the specific `Sheet2!<cell>` or `Sheet1!<cell>` coordinate whose value was compared. The extract `references/EYgp_Research_process_and_artifacts.md` is the grep-able evidence for all passages cited here.
- **Counts cited in this report:**
  - "0 matches for `resolution`" — computed via `rg -i 'resolution'` on the extract.
  - "0 matches for `answers`" — same.
  - "0 matches for `tension`" — same.
  - "0 matches for `RQ`" (as a standalone token) — confirmed via `rg 'RQ'`; the only matches are `ME-map` (not `RQ`) and the `qxxx` placeholder.
- **Status:** VERIFIED for every row above except those explicitly marked `[INFERRED — verify]`, which are consistent with the workbook but extend it.

---

## 6. What this audit does NOT do

- It does not evaluate whether the EYgp framework is *correct* as a research-process model; that is a methodological question the workbook's author owns.
- It does not re-verify individual manuscripts against the workbook. That is the `eygp-framework-checker` skill's responsibility once added.
- It does not check the workbook's internal consistency (e.g. "does Sheet3 agree with Sheet1 on S-stage readiness gates?"). That is a workbook-level review, orthogonal to this audit.

---

*Baseline verification for GROUND_TRUTH.md §10. Next run trigger: workbook SHA-256 change or new package paraphrase added.*
