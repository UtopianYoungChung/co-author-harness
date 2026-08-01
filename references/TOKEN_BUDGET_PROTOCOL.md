# TOKEN BUDGET PROTOCOL — Context Management for Long Manuscripts

**Purpose and trigger.** Use this protocol for manuscripts over 8,000 words,
multi-section work that does not fit beside its required rules, or any observed
context warning. It governs segmentation, state preservation, and continuity.

**Binding status.** Advisory. This protocol guides operational decisions; it does not override the Grounding Protocol or the Safeguard Layer. If a budget constraint forces a trade-off, the agent must declare the trade-off in the findings report — it must not silently skip checks.

**Package-surface ratchet.** The owned machine policy
`policies/token_budget.v1.json` pins the encoder, load graph, owners, and
immutable baseline. It blocks new or growing debt, floor growth, policy drift,
and invalid exceptions. Baseline debt remains unresolved.

---

## 1. Manuscript Size Classes

| Class | Word count | Token estimate (with package overhead) | Strategy |
|---|---|---|---|
| **Short** | < 4,000 words | < 10K tokens | Single-pass. No segmentation needed. All package rules fit in context. |
| **Standard** | 4,000–8,000 words | 10K–18K tokens | Single-pass feasible. Load rules selectively per gating table (REVIEW_ORCHESTRATION.md §3). |
| **Long** | 8,000–15,000 words | 18K–30K tokens | Section-by-section review (§2 below). Consolidated report assembled at the end. |
| **Extended** | > 15,000 words | > 30K tokens | Chapter segmentation (§3 below). Each segment reviewed independently; cross-segment consistency checked in a separate pass. |

The Planner determines the size class at classification time and records it in `reviews/classification.md`.

---

## 2. Section-by-Section Review (Long manuscripts)

### 2.1 Segmentation

The Planner divides the manuscript into segments at natural section boundaries (Introduction, Background, Methods, Results, Discussion, Conclusion). Each segment should be under 4,000 words. If a single section exceeds 4,000 words, subdivide at subsection boundaries.

### 2.2 Per-segment review

For each segment, the Evaluator:
1. Loads the segment text.
2. Loads only the package rules applicable to this segment type (e.g., for the Introduction, load Sexton §§1, 3, 6 and Bacon §§1, 5; for Results, load Baird Step 5).
3. Runs DETERMINISTIC_CHECKS.md on the segment.
4. Produces per-segment findings using the standard per-step format (REVIEW_ORCHESTRATION.md §4).

### 2.3 Cross-segment pass

After all segments are reviewed individually, the Evaluator runs a cross-segment consistency pass:
- **Red thread check:** Does the argument flow across segments without breaks?
- **Construct consistency:** Are the same terms used the same way throughout?
- **Abstract-body alignment:** Does the abstract match what the body delivers? (SAFEGUARD Check 3)
- **Contradiction audit:** Do different sections make incompatible claims? (SAFEGUARD Check 4)

This pass reads only the segment summaries (first and last paragraphs of each segment) plus the abstract, not the full text. It produces a cross-segment findings addendum.

### 2.4 Consolidated report assembly

The Evaluator merges per-segment findings and the cross-segment addendum into one Consolidated Findings Report. The report notes which findings are segment-local and which are cross-segment.

### 2.5 Report deferral for long manuscripts (v0.14.0 output economy)

For Long and Extended manuscripts, per-segment findings are stored as **evidence packets** by default (`references/OUTPUT_ECONOMY_PROTOCOL.md`). The Evaluator emits only segment-local action lists during the round. The final round report assembles the human-facing cross-segment synthesis after all in-scope segments finish or when the user explicitly closes the round.

If context limits interrupt a segment, write an evidence packet with `evidence_status: "partial"`, include the completed checks in `checks_run`, and add the skipped work to `final_report_inputs.checks_skipped`. The final report must show the partial status instead of treating the segment as clean.

---

## 3. Chapter Segmentation (Extended manuscripts)

For manuscripts over 15,000 words (thesis chapters, monograph chapters):

### 3.1 Treatment

Each chapter is treated as a separate review unit. The Planner creates a sub-classification for each chapter:
- Chapter-level paper type (e.g., "empirical" for a methods chapter, "conceptual" for a literature review chapter).
- Chapter-level gating (which rules apply to this chapter).

### 3.2 Inter-chapter consistency

After all chapters in scope are reviewed, the Evaluator runs an inter-chapter consistency pass analogous to the cross-segment pass in §2.3 but at a coarser grain: argument arc across chapters, construct provenance, notation consistency.

### 3.3 Scope discipline

The agent reviews only the chapters the user specifies. It does not unilaterally expand scope to the entire thesis. If a cross-chapter issue is detected (e.g., a construct introduced in Chapter 2 but undefined in Chapter 3), the agent flags it and asks the user whether to expand scope.

---

## 4. State Preservation Across Sessions

When a review round spans multiple sessions (e.g., the user starts a review, closes the session, and returns later):

### 4.1 What to persist (in project files)

| Artifact | Updated by | Contains |
|---|---|---|
| `reviews/classification.md` | Planner | Size class, segment map, current progress |
| `reviews/step_findings/*.md` | Evaluator | Per-segment findings for completed segments |
| `reviews/revision_plan.md` | Planner | Which segments remain, what actions are pending |
| `manuscript/revision_log.md` | Generator | Changes applied so far |

### 4.2 How to resume

When the agent starts a new session on an in-progress review:
1. Read `reviews/classification.md` for the size class and segment map.
2. Read `reviews/revision_plan.md` for progress state.
3. Scan `reviews/step_findings/` to see which segments have completed findings.
4. Resume from the first incomplete segment.
5. Do not re-review completed segments unless the user asks or the manuscript has changed (Drift Detection, SAFEGUARD Check 2).

### 4.3 Declaring incomplete passes

If context limits prevent completing a step, the agent must:
1. Record what was completed and what was skipped in the findings report.
2. Tag skipped items as `[CONTEXT-LIMITED]` (not `[N/A]`).
3. Propose a follow-up action: "Re-run Step 4 on §§3–5 in the next session."

The agent must **never** silently skip a step. The Grounding Protocol (Rule 6: No Gap-Filling) applies: if a check was not run, say so.

---

## 5. Rule-Loading Priority

When context is tight and not all package rules fit, the agent loads rules in this priority order:

| Priority | What to load | Why |
|---|---|---|
| 1 | GROUNDING_PROTOCOL.md | Non-negotiable integrity floor |
| 2 | DETERMINISTIC_CHECKS.md | Mechanical checks; low token cost, high signal |
| 3 | REVIEW_ORCHESTRATION.md §4 (findings format) | Structural consistency of output |
| 4 | The gated component file for the current step | Step-specific substance |
| 5 | SAFEGUARD_LAYER.md (the applicable checks) | Post-review integrity |
| 6 | Overlap map (REVIEW_ORCHESTRATION.md §5) | Deduplication guidance |
| 7 | MASTER (Parts relevant to the current step) | Traceability |

If priority 4 cannot fit, the agent runs the step at reduced depth and tags findings as `[REDUCED-CONTEXT]`.

---

## 6. Generator Budget Management

When the Generator is editing a long manuscript:
- Edit one segment at a time. Do not attempt to rewrite the entire manuscript in one pass.
- After each segment edit, run a self-check (deterministic patterns) on that segment before moving to the next.
- Log each segment's changes independently in `revision_log.md`.
- If the Generator runs out of context mid-segment, it stops, logs what was completed, and signals the Planner to schedule a continuation.
