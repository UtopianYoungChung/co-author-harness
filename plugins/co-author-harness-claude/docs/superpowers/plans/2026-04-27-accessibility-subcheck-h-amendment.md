# Accessibility Sub-check H — Register Appropriateness — Amendment Proposal

**Status:** PROPOSAL — not yet adopted; awaiting Planner three-filter gate review and user adjudication on staging.
**Date:** 2026-04-27
**Authored:** Cowork session, post-S2-close, mid-S3-open. Captured in this plan doc per the user's direction not to bundle the amendment inside the v0.10.0 snowball rollout.
**Provenance:** User-initiated consultation with `advisor:advisor` (Opus 4.6) on 2026-04-27 to refine the Phase 3 accessibility protocol with a daily-language rule. User clarified the rule's scope as dual: (1) within-manuscript non-technical passages, (2) audience-conditioned whole-manuscript register. The advisor returned a structured 1817-token amendment proposal; this document captures and operationalises it for governance review.
**Bound to:** SAFEGUARD_LAYER.md Check 8; `accessibility-overlay/SKILL.md` overlay v1.1; PHASE_PROTOCOL.md §3.3.3; Ph.D.-root CLAUDE.md §13.3 (criteria 1-7) and §13.4 (distinction from dumbing-down).
**NOT bound to:** v0.10.0 snowball rollout — orthogonal concern; suggested staging is v0.10.x patch after v0.10.0 RC.

---

## 1. Summary

Add a new **Sub-check H — Register Appropriateness** to the Phase 3 accessibility-overlay protocol, sibling to the existing Sub-checks A–G, sitting advisory-only initially under the `advisory_until` precedent Sub-check G already uses. The rule operationalises the user's daily-language directive at two integration points: a passage-scoped overlay rule that applies to non-technical passages within a manuscript (signposts, framing, transitions, worked-example vignettes, consolidation anchors), and a manuscript-scoped `register_class` field in `directives.md` that conditions the rule's whole-manuscript variant for non-technical-audience manuscripts. The detection procedure is functional, not metric — it cannot collapse into a Flesch-Kincaid back-door — and the rule preserves the protocol's load-bearing anti-dilution stance.

## 2. Problem Statement

The existing Phase 3 accessibility protocol — Sub-checks A–G in `accessibility-overlay/SKILL.md` overlay v1.1 — measures seven distinct dimensions of reader-experience surface quality, but **none of them governs register tone**. Sub-check E constrains domain-term density (≤2 new terms per paragraph at P1; P-stage adjusted), but term density and register tone are categorically different. A paragraph can be E-compliant (zero new terms) and still register-inappropriate for its passage role: a signposting paragraph in a manuscript's introduction can use no domain jargon and still read as cold, abstraction-stacked academic prose where the user's reader-accessibility intent calls for daily, agent-verb-object construction.

The gap is real. The user's directive to introduce daily-language for non-technical settings names this exact unfilled niche: register quality in passage roles where the argumentative function is connective rather than technical. The protocol has a structural-role vocabulary (signpost, framing, transition, worked-example, consolidation-anchor — already defined by Sub-checks A, D, F, G) but no rule that governs *how* those passages should be written at the sentence-construction level beyond their structural presence.

The risk in adding such a rule is the **dilution back-door**. The protocol explicitly rejects readability scoring (Flesch-Kincaid, Dale-Chall) as inappropriate for PhD-register academic argument and rejects "dilution instruments" that would force technical paragraphs into lay register. Any new rule must clear this bar. The advisor's framing — functional test rather than scalar metric — is the load-bearing design choice that closes the back-door.

## 3. Recommended Integration

**Sub-check H — Register Appropriateness**, sibling to A–G in `skills/accessibility-overlay/SKILL.md` and `skills/accessibility-overlay/references/sub_checks.md`. Two integration points operationalise the dual scope.

### 3.1 Passage-scoped variant (within-manuscript)

H runs over the five non-technical passage roles already defined elsewhere in the protocol:

| Passage role | Source Sub-check | What H adds |
|---|---|---|
| Section signpost (orienting + contribution clauses) | D | Register quality of the two clauses |
| Section framing / introduction | (implicit in A's section-opening cadence) | Register quality of framing prose |
| Inter-section transition | (implicit; not currently covered) | Register quality of transition prose |
| Worked-example vignette at density spike | F | Register quality of the vignette body |
| Cumulative consolidation anchor at structural boundary | G | Register quality of the anchor sentence |

A passage is classified as non-technical and subject to H if and only if the **functional removability test** holds: removing every domain-term token from the passage and substituting plain-language glosses preserves the paragraph's propositional content. If propositional content is destroyed by gloss-substitution → the passage is technical, H does not apply, the paragraph is left to E's term-density discipline alone. This is the load-bearing test that prevents H from misfiring on a Vidal contradiction-mapping move that uses no new terms but is dense with technical reasoning.

Within a non-technical passage, H emits findings against three positive markers (presence signals compliance) and three negative markers (presence flags violation):

**Positive markers.**
1. **Concrete-referent anchoring.** At least one concrete noun, analogy, or scenario per paragraph. Abstract nominalisation chains without an anchor are flagged.
2. **Agent-verb-object default.** Majority of sentences in the passage take a human or identifiable agent as grammatical subject. Nominalised constructions and passives that obscure agency are tracked.
3. **Discourse-connective transparency.** Transition words drawn from common English connectives (`but`, `so`, `because`, `this means`, `in other words`) rather than Latinate academic connectives (`notwithstanding`, `hitherto`, `whereby`) — unless the Latinate form is genuinely more precise and no plain-English equivalent suffices.

**Negative markers.**
1. **Unnecessary nominalisation.** Verbs converted to abstract nouns where the verb form would carry the same content (`the operationalisation of` instead of `how we operationalise`). Counted per paragraph.
2. **Stacked prepositional phrases.** Three or more consecutive prepositional phrases in a single clause. A hallmark of academic register creep where the structure is not doing conceptual work.
3. **Hedging pile-up.** More than two epistemic hedges per sentence (`it might perhaps be suggested that there could potentially be...`).

The compliance frame is **presence of positive markers**, not absence of negative markers. This is a deliberate inversion of the usual flag-on-violation grammar — it mitigates the risk of false-positive frustration the advisor flagged. A passage with one negative marker but two positive markers is CLEAN; a passage with zero positive markers and zero negative markers is MINOR (suggests the passage is doing nothing distinctively reader-accessible).

### 3.2 Manuscript-scoped variant (audience-conditioned)

A new field is added to `directives.md`:

```yaml
register_class: technical | mixed | non-technical
```

Default: `technical` for any manuscript whose P-stage classification places it in a peer-reviewed scholarly venue (the current default for the harness's primary use case). The user sets `mixed` for hybrid documents (a thesis chapter aimed partly at committee, partly at an applied audience) or `non-technical` for a public-interest write-up, policy memo, or trade-press article.

`register_class` composes with H's passage scope as follows:

- `register_class: technical` → H applies only to the five enumerated non-technical passage roles. Technical paragraphs are exempt.
- `register_class: mixed` → H applies to non-technical passage roles plus the abstract, introduction, and conclusion. Theory / methodology / results sections remain exempt.
- `register_class: non-technical` → H applies manuscript-wide. Technical paragraphs (those that fail the functional removability test) still retain their domain terms but are also held to the positive-marker construction requirements at the sentence level.

`register_class` is **orthogonal to P-stage**. P-stages (P0/P1/P2) govern depth and scope of engagement; register class governs target-audience register requirements. A P0 manuscript for a specialised journal and a P0 manuscript for a policy audience have the same depth but different register requirements — the two axes compose without conflict.

### 3.3 Severity floors and aggregate contribution

Mirroring A–G grammar:

- **MINOR.** One or two negative markers in a non-technical passage; or zero positive markers in a passage that ships at least one structural-role assignment.
- **MAJOR.** Sustained negative-marker density across three or more consecutive non-technical passages; or zero positive markers in a consolidation anchor or section transition (these two passage roles are weighted because they bear cumulative-load mitigation).
- **BLOCKER.** Reserved for `register_class: non-technical` manuscript-wide variant when more than 50% of non-technical passages emit MAJOR findings. BLOCKER is gated by the `advisory_until: H_two_revision_cycles` flag — even on a `register_class: non-technical` manuscript, the BLOCKER does not gate the §3.3.3 TerminalSignoffRow until the advisory period clears.

The advisory period mirrors Sub-check G's `advisory_until: next_manuscript_at_ph3` precedent. H findings are recorded with severity and contribute to the Reflector Phase 2g recurrence trail from day one, but the aggregate verdict computation excludes H findings while the flag is active. After two complete revision cycles in which H has been available and the user has had opportunity to act on findings, the flag retires and H findings join the aggregate.

## 4. Architectural Tension Resolution

One overlap requires explicit division of labour: **Sub-check D (section-transition signposting) and Sub-check H both touch the section-opening signpost paragraph.** D requires the structural presence of an orienting clause and a contribution clause; H requires register quality within those clauses. The resolution is a single sentence in D's spec in `references/READER_ACCESSIBILITY.md` and `accessibility-overlay/references/sub_checks.md`:

> *Register quality within the orienting and contribution clauses is delegated to Sub-check H. D enforces structural presence; H enforces register construction.*

This is a clarification, not a contradiction. The two Sub-checks remain orthogonal at the finding level — a signpost can be D-CLEAN (both clauses present) and H-MAJOR (clauses present but register-inappropriate), and vice versa.

No other Sub-check requires amendment beyond the H additions.

## 5. Alternative Integration (and trade-off)

**Alternative.** Extend Sub-check E into "E+ Jargon and Register Discipline" — a single Sub-check governing both term density and register tone, with the register dimension bolted on as an annex.

**Trade-off.** Loses E's currently crisp single-metric audit trail. E becomes a two-dimensional Sub-check (term-count + register), and the Evaluator's findings against E lose their unambiguous mapping back to a single threshold violation. The aggregate-verdict computation also becomes harder to reason about, because a single E finding could now be either a term-density violation or a register violation, and downstream consumers (Reflector Phase 2g recurrence audit; the Planner's TerminalSignoffRow gate) would need to disambiguate. The advisor explicitly recommends against this; the alternative is documented for completeness only.

## 6. Downstream Amendments Required (file enumeration)

When this proposal is adopted, the following harness files require edits. File paths verified by direct inspection 2026-04-27.

| File | Edit summary | Risk |
|---|---|---|
| `skills/accessibility-overlay/SKILL.md` | Add Sub-check H to the seven-Sub-check enumeration (becoming eight); update the `description` and `trigger` frontmatter to reflect A–H scope; add the H section to the per-Sub-check finding-class table; add the `advisory_until: H_two_revision_cycles` flag handling to the aggregate-verdict logic; add a "What this overlay is not" item clarifying H is not a register-classifier-as-style-judge | medium |
| `skills/accessibility-overlay/references/sub_checks.md` | Add the full Sub-check H specification (functional removability test, positive markers, negative markers, severity floors, P-stage interactions); add the D→H delegation note to the existing Sub-check D entry | medium |
| `references/READER_ACCESSIBILITY.md` | Mirror the Sub-check H threshold values, severity floors, and detection procedure (this file is the authoritative threshold source per `accessibility-overlay/SKILL.md` "MANDATORY READ ENTIRE FILE" directive); add the D delegation clarification | medium |
| `references/SAFEGUARD_LAYER.md` | Update Check 8 framing to enumerate eight Sub-checks A–H rather than seven; document the `register_class` axis and its interaction with the existing P-stage axis | low |
| `references/PHASE_PROTOCOL.md §3.3.3` | Update the TerminalSignoffRow accessibility gate to note that H findings are advisory while the `advisory_until` flag is active; document the BLOCKER condition for `register_class: non-technical` manuscripts post-flag-retirement | low |
| `skills/run-phase-3/SKILL.md` | Update §4 (Agent composition at Ph3) Evaluator row to note Sub-check H runs at Step 8.5 alongside A–G; update §5 step 9 to enumerate eight Sub-checks; verify §3.1 [CONVERGENCE-BLOCKED-ACCESSIBILITY] surface still composes correctly | low |
| `references/PROJECT_BOOTSTRAP.md` (or wherever `directives.md` template lives) | Add `register_class` field to the directives template with default `technical` and the three permitted values | low |
| `references/SKILL_REGISTRY.md` | If H is implemented as a standalone skill rather than overlay-internal, register a new SK-NN entry; if it remains overlay-internal, no registry change required (recommended path) | none |
| `agents/evaluator.md §Step 8.5` | Add Sub-check H dispatch to the Step 8.5 enumeration | low |
| `agents/planner.md` | Update §3.3.3 gate logic to read the H aggregate alongside A–G | low |
| `references/DETERMINISTIC_CHECKS.md §9b` | Optional pre-filter for H's negative-marker detection (nominalisation count, prepositional-phrase stack count, hedge count); cheap to add but not required for v1 | low |

Estimated edit-time effort, single-session: ~4–6 hours (similar to S2's document layer + co-mutation surfaces, but with no new orchestration ladder edits, no new triggers, no schema bumps, no migration script). The §6.0 coupling-checklist in `2026-04-26-snowball-reference-architecture.md` does **not** apply (no phase-runner Step edits).

## 7. Risks and Mitigations

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-H1 | Register judgment is subjective; H emits false-positive MAJOR flags that frustrate authors | Medium | Medium (author trust in the protocol erodes; section-level overrides accumulate) | The compliance frame inverts the usual grammar — H rewards positive-marker presence rather than punishing negative-marker presence. The `advisory_until: H_two_revision_cycles` flag delays binding the §3.3.3 BLOCKER gate. The `directives.md` `register_class` field gives the author explicit control. The Evaluator's Independent-reasoning note can override any individual finding. |
| R-H2 | The functional removability test ("does removing domain terms destroy propositional content?") is fuzzy at the boundary; classifications drift | Medium | Low (occasional misclassification of a borderline paragraph) | The test is fuzzy by design — the alternative is hard scoring (forbidden by the anti-dilution stance). The fuzziness is bounded: a misclassification means H either fires on a paragraph it shouldn't (downgraded to MINOR by the user) or fails to fire on a paragraph it should (caught at the next iteration). Reflector Phase 2g recurrence accounting will surface persistent misclassifications. |
| R-H3 | Sub-check D and H drift apart over time despite the explicit delegation note | Low | Low | The delegation note is a single sentence pinned to D; future edits to D require re-reading H, and vice versa, by the existing Rule 1 full-file-read floor. |
| R-H4 | `register_class` field is forgotten by users who bootstrap new projects from old templates | Medium | Low (manuscript silently runs as `register_class: technical` default; H still fires on non-technical passages, so accessibility still improves) | Default `technical` is the safe default; the field is non-blocking when absent. `PROJECT_BOOTSTRAP.md` template adds the field; existing `directives.md` files inherit the default by silent absence. |
| R-H5 | Performance cost: H's per-passage detection adds an extra pass over the manuscript at Step 8.5 | Low | Low | H runs only on the five enumerated passage roles, not all paragraphs. The detection procedure is line-oriented (count nominalisations, count prepositional-phrase chains, count hedges) and matches the cost profile of E. Negligible additional time. |
| R-H6 | The advisory-only period creates a window where H findings are visible but not actionable, leading to user confusion ("why is this a MAJOR if it doesn't block?") | Medium | Low | The `advisory_until` precedent is already established by Sub-check G; users familiar with G will recognise the pattern. The H output artefact will carry an explicit `advisory_until_active: true` flag and a note explaining the binding-pending status. |

## 8. Governance Note (Planner Three-Filter Gate)

This proposal is not adopted by virtue of being written. Per the Planner agent's three-filter gatekeeper role (`references/SKILL_REGISTRY.md` v0.7.0 surfaces; `Ph.D.-root CLAUDE.md` §13.4):

1. **Evidence-adequacy filter.** The advisor consultation provides the structural argument; the user's clarified dual-scope confirms the operational requirement. Evidence-adequacy: PASS pending user adjudication on whether the gap is real (the advisor's argument that E is term-count and not register-tone is the load-bearing claim; the user can confirm or contest).

2. **Non-duplication filter.** No existing Sub-check governs register tone. E (jargon density), F (worked examples at density spikes), and G (consolidation anchors) cover adjacent territory but not the proposed niche. Non-duplication: PASS.

3. **Tier-appropriateness filter.** The proposal is package-tier (applies to all manuscripts using the harness substrate), not project-tier or global. Tier: package. Appropriate.

The proposal becomes governance-eligible after the user reviews this document and either approves, requests revision, or rejects. If approved, staging is the next decision (suggested below).

## 9. Suggested Staging

This amendment is **orthogonal to v0.10.0's snowball rollout**. The cleanest staging is:

- **v0.10.0 RC** ships with the snowball machinery (S1 + S1.5 + S2 + S3 + S4 + S4.5 + S5 + S6) without H.
- **v0.10.1 patch** lands the H amendment as a single document-layer hardening pass. Estimated effort 4-6 hours. No phase-runner Step edits, so the §6.0 coupling checklist does not apply. Single semantic-review round expected (md-reviewer over the eight amended files; promise-reviewer over the four amended frontmatter blocks; orchestrator-critic exempt — no dispatch graph edit).
- **v0.10.1 ships H with the `advisory_until` flag active.** Two full revision cycles in real-project use are required before the flag retires.
- **v0.10.2 (or v0.11.0)** retires the `advisory_until` flag once the empirical recurrence trail confirms H's false-positive rate is within tolerance.

Alternative staging (if user prefers): land H as a v0.10.0-S6.5 hardening sub-stage between S6 and the v0.10.0 RC. This bundles the rollout but bloats v0.10.0's scope; not recommended given the recent S2 scope-explosion lesson.

## 10. Open Questions for User Adjudication

1. **Functional removability test wording.** The test is "does removing every domain-term token and substituting plain-language glosses preserve propositional content?" The user may want to specify what "domain-term token" means more precisely (any italicised term? any term in `references/terminology_register.md`? glossary-tagged terms only?). Default proposed: same scope as Sub-check C's "construct" definition.

2. **Positive-marker thresholds.** The proposal says "at least one concrete noun per paragraph" and "majority of sentences agent-verb-object." The user may want explicit numerical thresholds (e.g., ≥1 concrete noun per 100 words; ≥60% agent-subject sentences). Default proposed: qualitative judgment for the advisory period; quantitative thresholds added post-flag-retirement based on observed false-positive patterns.

3. **`register_class: mixed` scope.** The proposal says H applies to non-technical passages plus abstract, introduction, conclusion. The user may want this list extended (discussion section?) or contracted (introduction only?). Default proposed: the four-section list (abstract / introduction / conclusion / non-technical passages) as a starting point.

4. **Failure-mode telemetry.** Should H emit a per-finding `false_positive_candidate: true` flag that the user can set during review, feeding a project-side calibration log that informs the v0.10.2 flag-retirement decision? Default proposed: yes; cheap to add and the data is load-bearing for the binding decision.

5. **Back-compatibility.** Existing manuscripts in flight (any project currently mid-Ph3) will inherit the H Sub-check on the next iteration. Do they get a one-iteration grace period? Default proposed: yes; the first H run on a previously-non-H manuscript records `inherited_from_pre_h: true` and runs MINOR-only regardless of detected severity for that one iteration.

## 11. Cross-References

- `skills/accessibility-overlay/SKILL.md` — current overlay v1.1; the Sub-checks A–G this amendment extends.
- `skills/accessibility-overlay/references/sub_checks.md` — current threshold authority for A–G.
- `references/READER_ACCESSIBILITY.md` — current threshold authority (mirrored from sub_checks.md).
- `references/SAFEGUARD_LAYER.md` — Check 8 framing.
- `references/PHASE_PROTOCOL.md §3.3.3` — TerminalSignoffRow accessibility gate this amendment touches.
- Ph.D.-root `CLAUDE.md` §13.3 (criteria 1-7) and §13.4 (distinction from dumbing-down) — the user-level constitution this amendment must remain compatible with.
- Advisor consultation transcript: in-session, advisor:advisor, 2026-04-27, 1817 output tokens, contract v1.3.0. Not committed to repo — captured here.

---

**End of proposal.** Awaiting user review and adjudication on staging.
