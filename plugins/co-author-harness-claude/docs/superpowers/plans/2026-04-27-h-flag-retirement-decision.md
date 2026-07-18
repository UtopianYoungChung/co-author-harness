# Sub-check H `advisory_until` Flag Retirement Decision

**Status:** PROPOSAL — captures the empirical-criterion table and adjudication template; binding decision is FUTURE (will land in a later patch when `aggregate_h_calibration.py` output materialises sufficient data).
**Authoring date:** 2026-04-27
**Authoring context:** v0.10.2 setup-stage deliverable for v0.10.1's deferred item 2 (Sub-check H `advisory_until: H_two_revision_cycles` flag retirement). v0.10.2 ships the aggregator infrastructure (`scripts/aggregate_h_calibration.py`) and this plan doc; the actual retirement decision adjudicates against this template once data exists.
**Reference plan:** `2026-04-27-accessibility-subcheck-h-amendment.md` §10.4 Default proposed (provisional retirement criterion: FPR < 30% across two revision cycles).

---

## 1. Problem statement

Sub-check H (Register Appropriateness) shipped at v0.10.1 under the transitional flag `advisory_until: H_two_revision_cycles`. Under the flag, H findings are recorded with severity but do not contribute to the §3.3.3 TerminalSignoffRow aggregate verdict. The flag retires after H has been observed across two complete revision cycles AND the false-positive rate falls below a defined threshold; at retirement, H findings join the aggregate identically to A–G.

The retirement decision is **empirically gated** — it cannot be made at v0.10.2 ship because no project has yet run two complete H cycles. v0.10.2 ships the empirical pipeline (`scripts/aggregate_h_calibration.py`) and this plan doc, then waits for projects to run H. When at least one project's `reviews/h_calibration_aggregate.md` shows the criterion met, the user adjudicates retirement against this plan doc's §4 template.

## 2. Provisional retirement criterion

Per `2026-04-27-accessibility-subcheck-h-amendment.md` §10.4 Default proposed (user adjudicated 2026-04-27):

- **Criterion 1 — Cycle count.** `cycles_observed >= 2`. The flag retires only after H has run at full procedure (post-grace-period) on at least two complete revision cycles within a single project. The cycle count is recorded in `reviews/classification.md` as `h_advisory_cycles_observed: <integer>`, incremented at every Ph3 close where the overlay ran with H in scope.
- **Criterion 2 — False-positive rate.** `aggregate_fpr < 0.30` across all eligible findings (eligible = total minus inherited-from-pre-h). The 30% threshold mirrors the noise-tolerance ceiling for advisory-grade findings used elsewhere in the harness; a higher rate suggests the spec is over-firing in ways that have not been corrected by the v0.10.2 tightenings.
- **Combined verdict.** Both criteria must be met. ELIGIBLE if both met; NOT_ELIGIBLE otherwise.

The criterion is **provisional** — the binding adoption is the verdict reached when the criterion is first applied to a real `aggregate.md`. If the criterion turns out to be wrong (e.g., 30% is too lenient and H ships at retirement with too many false positives still firing; or 30% is too strict and retirement never happens despite the spec being sound), the alternative criteria in §3 below become the candidates for re-adjudication.

## 3. Alternative criteria considered

| Criterion | Definition | Trade-off vs. default | Would adoption change v0.10.2 substrate? |
|---|---|---|---|
| Stricter FPR (<0.20) | aggregate_fpr below 0.20 across two cycles | Higher confidence in spec quality at retirement; but may delay retirement on borderline-OK specs. Risk: retirement never triggers if the spec ships permanently in the 20–30% FPR band, which is not unusual for register-judgment work. | No — substrate already supports this threshold; just a parameter change in the aggregator's verdict computation. |
| Per-marker FPR | aggregate_fpr per marker (not just overall) below 0.30 | Catches the case where one marker (e.g., concrete-referent anchoring) over-fires while the other three are clean. More diagnostic but requires per-marker telemetry which v0.10.2 does not yet emit. | Yes — would require extending per-finding telemetry to track which marker(s) fired the finding. v0.10.3+ work. |
| Cycle count >2 | cycles_observed >= 3 | More confidence in the cycle-mean FPR estimate; reduces variance from cycle-to-cycle noise. But also delays retirement by one cycle in the typical project trajectory. | No — substrate supports any cycle count; just a parameter change. |
| Reviewer-agreement criterion | aggregate_fpr below 0.30 AND inter-reviewer agreement on false-positive flagging > 0.80 | Adds a robustness check: the FPR estimate is meaningful only if reviewers consistently flag the same findings as false positives. Requires multiple reviewers per project. | Partially — substrate would need to track reviewer identity per row; current calibration-log format does not. |
| Combined criterion (default + per-marker floor) | aggregate_fpr < 0.30 AND no single marker exceeds 0.50 | Catches both the over-firing-overall case and the one-marker-broken case. Most robust but most data-hungry — requires per-marker telemetry. | Yes — same as per-marker FPR row. |

The default criterion (overall aggregate_fpr < 0.30 across >=2 cycles) is the simplest threshold that captures the v0.10.1 advisor's spec-sanity concern. The alternatives are available for re-adjudication if the simple threshold proves insufficient.

## 4. Adjudication template (filled in once data exists)

When `reviews/h_calibration_aggregate.md` is run on a project with `cycles_observed >= 2`, the user copies the following template into a new commit on a `patch/v0.10.X-h-retirement` branch and fills in the rows.

| Field | Value |
|---|---|
| Project | <project name> |
| Aggregate report file | `<project_root>/reviews/h_calibration_aggregate.md` |
| Aggregate report date | YYYY-MM-DD |
| Cycles observed | <integer> |
| Cumulative eligible findings | <integer> |
| Cumulative false positives | <integer> |
| Aggregate FPR | <decimal, four sig figs> |
| Default-criterion verdict | ELIGIBLE / NOT_ELIGIBLE |
| Reviewer's qualitative assessment | <free text — does the spec feel right? are the false positives concentrated in one marker? are they scattered?> |
| Adjudication | RETIRE (default criterion met) / RETIRE-WITH-MARKER-RE-TUNE (default criterion met but marker-level pattern suggests re-tune) / DEFER (default criterion not met; reasons named) / RE-ADJUDICATE-CRITERION (default criterion as-stated turns out to be wrong; recommend §3 alternative) |
| Patch version landing the adjudication | `v0.10.X` |

The reviewer's qualitative assessment is load-bearing — it tells the future maintainer whether the criterion-as-stated did or did not match the user's intent. A spec that retires under the default criterion but feels wrong should land RETIRE-WITH-MARKER-RE-TUNE, with a follow-up plan doc capturing the marker re-tune work.

## 5. Binding decision is FUTURE

This plan doc is **not yet adopted**. v0.10.2 lands the plan doc as a forward-looking specification (mirroring the v0.10.1 plan-doc-only pattern). The binding decision happens in whichever patch version first applies the §4 template to a real aggregator output. At that point, the plan doc's Status frontmatter changes from PROPOSAL to ADOPTED; the §4 template's filled-in row becomes the historical record.

## 6. Governance note

This plan doc is the v0.10.2 equivalent of `2026-04-26-snowball-implementation-strategy.md` for the H flag retirement decision specifically. It is referenced from `RELEASE_NOTES_v0.10.2.md §2.S2` per release-pattern. The aggregator script `scripts/aggregate_h_calibration.py` is the canonical empirical-input consumer; running it is the precondition for §4 adjudication. Per architecture §6.0 row 4, the SOT for retirement-decision criteria is this plan doc; cross-references in `references/SAFEGUARD_LAYER.md §H` step 7 and `references/READER_ACCESSIBILITY.md §13.5` resolve here rather than restate the criteria.

---

**End of plan.** Ready for empirical input materialisation; binding adjudication awaits.
