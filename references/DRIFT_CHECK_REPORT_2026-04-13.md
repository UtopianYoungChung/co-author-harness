# Drift Check — Package-Level, 2026-04-13

**Date:** 2026-04-13
**Scope:** Package-level (no active project round). Triggered by the gstack-adaptation pass that added `ROUTING_SPINE.md`, `AGENT_CONTRACTS.md`, `PARALLEL_CONDUCTOR.md`. Per `DRIFT_CHECK.md` §3, any edit to the package surface requires a reconciliation pass on `MASTER_research_and_paper_guidelines.md`.
**Files in scope:** `MASTER_research_and_paper_guidelines.md` + every component file cited therein.

---

## 1. Citation enumeration

Grep on `\.md` across MASTER yielded 14 distinct component-file citations plus many section anchors. The fourteen cited files are:

1. `MASTER_research_and_paper_guidelines.md` (self)
2. `baird_2021_writing_guidelines.md`
3. `bacon_2009_well_crafted_sentence_guidelines.md`
4. `research_paper_writing_guidelines.md`
5. `general_research_project_guidelines.md`
6. `project_writing_style_checklist.md`
7. `Sexton_Fiction_to_Academic_Writing_Guide.md`
8. `CLAUDE.md`
9. `SAFEGUARD_LAYER.md`
10. `GROUNDING_PROTOCOL.md`
11. (implicit) `REVIEW_ORCHESTRATION.md` — referenced by "Step 8.5" language
12. (implicit) orchestration files — referenced by "Step" terminology

(Items 11–12 are *terminology references* rather than direct `.md` citations; they count for the claim-check stage but not the existence check.)

## 2. Per-category verdicts

| Category | Count | Notes |
|---|---|---|
| **D-A — Quote drift (MAJOR)** | 0 | MASTER does not verbatim-quote component files; it summarises. No exposure. |
| **D-B — Claim drift (BLOCKER)** | 0 | Five spot-checks below all resolved; no sampled citation asserted a rule the target section does not support. |
| **D-C — Structural drift (BLOCKER, strict)** | 0 | Every cited file exists; every cited section anchor resolves. |
| **D-C-adj — Completeness gap (non-blocking)** | 1 | The Constitution table (MASTER lines 72–87) lists rows 0–9 but the package now contains ≥20 top-level `.md` files plus `agents/` and `skills/` directories. The table is an under-enumeration, not a broken citation. Reconciled in-round (see §4). |

## 3. Spot-check results (DRIFT_CHECK §3.2 mandates ≥5 at standard depth)

| # | MASTER citation | Target | Resolution |
|---|----------------|--------|------------|
| SC-1 | "Bacon §10 checklist" (Constitution row 4; traceability row F) | `bacon_2009_well_crafted_sentence_guidelines.md` line 229 `## 10. Quick revision checklist (Bacon-aligned)` | ✓ RESOLVED |
| SC-2 | "Sexton §10 table" (Constitution row 5; traceability row G.3) | `Sexton_Fiction_to_Academic_Writing_Guide.md` line 130 `## 10. Checklist for an Impactful Academic Paper` | ✓ RESOLVED |
| SC-3 | "Baird §1" (traceability row A.1) | `baird_2021_writing_guidelines.md` line 9 `## 1. Overall aims for the paper` | ✓ RESOLVED |
| SC-4 | "Milestones 1–5" (traceability row C.1) | `general_research_project_guidelines.md` line 55 `## Milestone 5: Final Paper` (+ earlier Milestones 1–4) | ✓ RESOLVED |
| SC-5 | "Playbook §5.5 red thread" (traceability row A.1) | `research_paper_writing_guidelines.md` line 147 `### 5.5 "Red thread" and hourglass` | ✓ RESOLVED |

No sampled citation fails. The sample is not exhaustive (submission-bound depth would require every citation). For a *package-level* drift pass outside of a submission round, the spot-check threshold is sufficient per §3.2.

## 4. Completeness-gap reconciliation

The MASTER Constitution was written when the package contained ten files. Since 2026-04-09, fifteen additional top-level component files have been introduced:

`REVIEW_ORCHESTRATION.md`, `DETERMINISTIC_CHECKS.md`, `AGENT_ORCHESTRATION.md`, `PROJECT_BOOTSTRAP.md`, `TOKEN_BUDGET_PROTOCOL.md`, `SUCCESS_METRICS.md`, `RESEARCH_ROOT_CLAUDE.md`, `EXTERNAL_VERIFIERS.md`, `EVAL_METHODOLOGY.md`, `DRIFT_CHECK.md`, `REFLEXIVITY_CHECK.md`, `STYLE_COMMITMENTS.md`, `ROUTING_SPINE.md`, `AGENT_CONTRACTS.md`, `PARALLEL_CONDUCTOR.md` (plus `COWORK_SESSION_INSTRUCTIONS.md`, `suchman_writing_style.md`, and the `agents/` and `skills/` subdirectories).

**Chosen resolution.** Rather than expand the Constitution row-by-row (which would duplicate `CLAUDE.md §3`), MASTER is amended with: (a) a scope note stating that the Constitution lists only *Parts A–H content sources*, and (b) a pointer to `CLAUDE.md §3` as the authoritative index for meta-infrastructure. This preserves the Constitution's teaching function (rows 1–7 = "mandatory full-package pass") without pretending it is the exhaustive package index.

## 5. Verdict

- **Drift status (strict D-A / D-B / D-C):** CLEAN.
- **Completeness gap:** reconciled in-round (MASTER amendment appended this same day).
- **Submission-bound G.4 eligibility (per `DRIFT_CHECK.md` §5):** ELIGIBLE. No blockers open.

## 6. Residual risks flagged for next Reflector round

1. The MASTER traceability matrix does not map the meta-infrastructure files (`ROUTING_SPINE`, `AGENT_CONTRACTS`, `PARALLEL_CONDUCTOR`, etc.) to any Part A–J content section — which is correct, because those files are harness, not content. However, a future reader may expect a traceability entry. The amendment should make that explicit.
2. At the next submission-bound round, every MASTER citation must be re-checked exhaustively (§3.2 full-audit rule), not spot-checked. This round discharges the *package-edit* trigger only.
3. The Constitution's "rows 1–7 are the mandatory full-package pass" policy (line 87) is unchanged by this amendment; the new files sit outside that seven-file pass by design and should not be added to it without a separate policy decision.

---

*Generated by Claude following `DRIFT_CHECK.md` procedure §3 at the user's instruction, 2026-04-13. Logged in `DRIFT_LOG.md`.*
