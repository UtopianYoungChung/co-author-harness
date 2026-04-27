# Sub-check H Positive-Marker Quantitative Thresholds

**Status:** PROPOSAL — captures candidate threshold definitions, trade-offs, and adjudication template; binding adoption is FUTURE (deferred until `advisory_until: H_two_revision_cycles` flag retirement closes per `2026-04-27-h-flag-retirement-decision.md`).
**Authoring date:** 2026-04-27
**Authoring context:** v0.10.2 forward-looking spec for v0.10.1's deferred item 3 (quantitative thresholds for H positive markers). v0.10.2 ships the candidate enumeration; binding adoption awaits empirical input from the advisory-period calibration logs.
**Reference plan:** `2026-04-27-accessibility-subcheck-h-amendment.md` §10.2 Default proposed (qualitative thresholds for advisory period; quantitative deferred to post-flag-retirement based on observed false-positive patterns).

---

## 1. Problem statement

Sub-check H ships at v0.10.1 with **qualitative thresholds** for the positive markers — the Evaluator judges whether a passage carries "at least one concrete referent" or "majority agent-verb-object sentences" without a per-marker numeric floor. The v0.10.2 S1.5 tightening expanded the marker count from three to four (adding register-shift signposting) but kept the qualitative-judgment frame for all four.

Quantitative thresholds were deferred at v0.10.1 on two grounds: (i) numeric thresholds set without empirical data risk over-firing or under-firing in ways that only manifest under real-project use; (ii) the H advisory period (`advisory_until: H_two_revision_cycles`) is precisely the calibration window where the qualitative judgments accumulate the data needed to set defensible quantitative floors.

This plan doc captures the candidate threshold definitions per marker so the eventual binding decision (post-flag-retirement) has a worked options table. The thresholds are **not binding at v0.10.2 ship**; the qualitative-judgment frame remains the operational rule until this plan doc is adopted.

## 2. Candidate threshold definitions per marker

### 2.1 Marker 1 — Concrete-referent anchoring

The v0.10.2 S1.5 tightening operationalises "concrete referent" as one of three classes (physical/material entity; named individual or group; specific scenario or worked vignette). The qualitative threshold is "at least one per paragraph." Quantitative candidates:

| Threshold | Definition | Rationale |
|---|---|---|
| ≥1 per 50 words | Strict floor; one concrete referent per ~3 short sentences | Catches abstraction-stacked passages early; over-fires on terse signpost orienting clauses (which may legitimately be 1–2 sentences and 30–40 words). |
| ≥1 per 100 words | Median floor; one concrete referent per typical short paragraph | Aligned with §9e nominalisation threshold (per-100-words frame). Matches the v0.10.1 plan doc §10.2 example. |
| ≥1 per 150 words | Tolerant floor; one concrete referent per substantial paragraph | Aligned with the §9b cadence threshold (paragraphs >150 words flagged); pairs the marker count to the cadence flag. Risk: under-fires on dense-construct paragraphs that cross 150 words without a concrete anchor. |

**Recommendation (provisional):** ≥1 per 100 words. The 100-word window aligns with the rest of H's per-100 conventions (§9e probes; hedge density), and the empirical-data-collection during the advisory period is most useful when measured against a stable denominator across markers.

### 2.2 Marker 2 — Agent-verb-object default

The qualitative threshold is "majority of sentences." Quantitative candidates:

| Threshold | Definition | Rationale |
|---|---|---|
| ≥40% agent-subject sentences | Tolerant floor | Acknowledges that academic prose legitimately runs higher abstraction-subject rates than narrative prose. Risk: under-fires on register-soft passages that hide nominalised subjects. |
| ≥50% agent-subject sentences | Median floor | Strict majority. Default arithmetic. |
| ≥60% agent-subject sentences | Strict floor | Plan doc §10.2 example. Matches the "agent-verb-object as register-default" framing — if 6 of 10 sentences ship the agent structure, the passage is meeting the marker; below that, the structure is not the default. |

**Recommendation (provisional):** ≥60% agent-subject sentences. The 60% threshold pairs the "default" framing in the marker name with a clear majority-plus-margin, consistent with the v0.10.1 plan doc example.

### 2.3 Marker 3 — Discourse-connective transparency

The qualitative threshold is "transition words drawn from common English connectives ... rather than Latinate academic connectives" with the v0.10.2 load-bearing-Latinate whitelist exempting six entries. Quantitative candidates:

| Threshold | Definition | Rationale |
|---|---|---|
| ≥3 plain-English connectives per page | Strict floor | Forces a per-page register-anchoring presence. Risk: over-fires on dense formal-proof sections of mixed-register manuscripts. |
| ≥5 plain-English connectives per page | Median floor | Plan doc §10.2 example. Distributes the connective expectation across the page without forcing high density. |
| Ratio >0.5 (plain : non-whitelist Latinate) | Ratio floor | Counts plain-English connectives against non-whitelist Latinate connectives in the same passage; passes if plain outnumber Latinate (excluding the six whitelist entries). |

**Recommendation (provisional):** Ratio >0.5 (plain : non-whitelist Latinate). The ratio framing handles the mixed-register case better than the per-page count: a dense theory passage may legitimately have few plain connectives but no non-whitelist Latinate connectives either, in which case the ratio is undefined/0/0 (treated as PASS); a register-creep passage with three Latinate connectives and one plain fails the ratio cleanly.

### 2.4 Marker 4 — Register-shift signposting (added v0.10.2)

This marker is presence/absence rather than density. The qualitative threshold is "shifts are announced via a signposting cue." Quantitative thresholds are not naturally meaningful for a presence/absence marker. Two adjacent candidate operationalisations:

| Operationalisation | Definition | Rationale |
|---|---|---|
| Strict — every detected shift must carry a signpost | Detect register shift via §9e probe-firing-pattern change between consecutive sentences (e.g., abstract→concrete = nominalisation drops + concrete-referent class fires); flag any unsignposted shift. | Most precise; relies on §9e to detect shifts. Risk: §9e shifts are noisy at the sentence level. |
| Tolerant — only "major" shifts (cross-paragraph or cross-sentence-pair) flagged | Detect shift across paragraph boundaries or across two consecutive sentences whose register signals reverse polarity. | Acknowledges that micro-register-fluctuations within a paragraph are normal academic prose; only sustained shifts need signposting. |
| Hybrid — strict within signpost passages, tolerant elsewhere | Within signpost orienting/contribution clauses, every detected shift must be signposted; in vignette bodies and consolidation anchors, only major shifts flagged. | Aligns with the v0.10.2 S1.5 signpost-role-split refinement: where reader orientation is most load-bearing, the marker is strictest. |

**Recommendation (provisional):** Hybrid (strict within signpost passages; tolerant elsewhere). This pairs marker 4's quantitative operationalisation with the S1.5 signpost-role-split tightening; both refinements concentrate strictness on the orienting work that most carries reader-anchoring load.

## 3. Trade-offs — false-positive vs. false-negative rate per threshold

The advisor's framing in `2026-04-27-accessibility-subcheck-h-amendment.md` §10.2 names false-positive rate and false-negative rate as the two failure modes the threshold-calibration must balance:

- **False-positive rate (over-firing).** The threshold catches more than it should — passages that read register-clean to a careful disciplinary reviewer get flagged anyway. The reviewer experience is frustration; the long-term effect is reviewer disengagement from H findings.
- **False-negative rate (under-firing).** The threshold misses passages that genuinely violate the spec. The reviewer experience is missed defects; the long-term effect is the spec failing to do the work it was authored for.

The §3 of the v0.10.1 plan doc names a 30% FPR cap as the provisional retirement criterion (per Q1 2026-04-27 adjudication). For the threshold calibration, the per-marker-FPR target is the same 30% cap applied at the marker level: when the advisory-period data shows that a candidate threshold for Marker N produces FPR >0.30, that threshold is rejected; the next-tighter or next-tolerant candidate is the fallback. Per-marker FPR data is not yet emitted by the v0.10.2 calibration logs (the per-finding telemetry tracks `false_positive_candidate` overall, not per-marker); a v0.10.3 enhancement would extend the per-finding telemetry to track which marker(s) fired the finding, which is the precondition for per-marker threshold adjudication.

The fall-back position if per-marker telemetry is not implemented: stay with qualitative thresholds permanently, and treat the candidate enumerations in §2 as a reviewer's worked-thinking prompt rather than a binding rule.

## 4. Binding precondition

Adoption of any quantitative threshold from §2 is gated on:

- **Precondition 1 — Flag retirement closes.** `2026-04-27-h-flag-retirement-decision.md` reaches ELIGIBLE verdict on at least one project's calibration logs and the user adjudicates retirement.
- **Precondition 2 — Per-marker telemetry available.** Either v0.10.3 implements the per-marker-FPR telemetry extension, or the user explicitly adopts the qualitative thresholds permanently (stays with the recommendations in §2 as default but keeps them advisory).
- **Precondition 3 — Empirical data sufficient.** At least three projects have run H on their full lifecycle (Ph2 + Ph3) so the thresholds can be calibrated against more than one project's data — single-project FPRs are confounded by project-specific register conventions and reviewer idiosyncrasies.

If preconditions 1–3 are not met, the qualitative-judgment frame stays binding and §2's candidate enumeration remains a reference reservoir.

## 5. Adjudication template (filled in once data exists)

When the three preconditions are met, the user copies the following template into a commit on a `patch/v0.10.X-h-thresholds` branch and fills in the rows.

| Field | Value |
|---|---|
| Adjudication date | YYYY-MM-DD |
| Projects observed | <project names> |
| Cycles per project | <list> |
| Per-marker FPR data available | yes / no |
| Marker 1 (concrete referent) — adopted threshold | ≥1 per 50 / ≥1 per 100 / ≥1 per 150 / qualitative permanent |
| Marker 2 (agent-verb-object) — adopted threshold | ≥40% / ≥50% / ≥60% / qualitative permanent |
| Marker 3 (discourse connective) — adopted threshold | ≥3 / ≥5 per page / ratio >0.5 / qualitative permanent |
| Marker 4 (register-shift signposting) — adopted operationalisation | strict / tolerant / hybrid / qualitative permanent |
| Per-marker FPR (where data available) | <table> |
| Reviewer's qualitative assessment | <free text — does each threshold feel right? are over-firings concentrated in one marker?> |
| Adjudication | ADOPT-DEFAULTS / ADOPT-ALTERNATIVES (per marker) / KEEP-QUALITATIVE / RE-CALIBRATE-PRECONDITIONS |
| Patch version landing the adjudication | `v0.10.X` |

## 6. Binding decision is FUTURE

This plan doc is **not yet adopted**. v0.10.2 lands it as a forward-looking specification. The qualitative-judgment frame remains the operational rule until preconditions §4.1–§4.3 are met and the §5 template is filled in. At that point, the plan doc's Status frontmatter changes from PROPOSAL to ADOPTED and the §5 template's filled-in rows become the historical record.

## 7. Governance note

This plan doc is the v0.10.2 forward-looking-spec sibling of `2026-04-27-h-flag-retirement-decision.md` (the two plan docs are co-dependent: thresholds adoption is gated on flag retirement). It is referenced from `RELEASE_NOTES_v0.10.2.md §2.S3` per release-pattern. Per architecture §6.0 row 4, this plan doc is the SOT for quantitative-threshold candidate definitions; cross-references in `references/SAFEGUARD_LAYER.md §H` (procedure step 3 Advisory-period default note) resolve here rather than restate the candidate enumerations.

---

**End of plan.** Ready for empirical input materialisation; binding adjudication awaits.
