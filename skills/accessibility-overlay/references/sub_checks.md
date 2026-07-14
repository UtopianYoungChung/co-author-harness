# Sub-checks A–H — threshold values, severity floors, detection procedures

**Machine policy routing.** Load `references/policies/reader_accessibility.v1.json` through `scripts/reader_accessibility_policy.py`. In particular, `thresholds.cadence` owns the provisional bands and severity mapping. Lexicon matches are candidates only: a cadence credit requires overlay **functional confirmation** of a transition, counter-move, worked example, or thematic refocus. Sub-check B, not A, protects C-8/M-4 demonstrative anaphora and C-8/M-5 cadential verdicts from false rhythm findings.

> **Loaded by** `SKILL.md` at the Sub-check dispatch step. This file is the authoritative specification of the eight Sub-checks; the SKILL.md body routes and aggregates, this file defines. All threshold numerics (word counts, σ cut-offs, term caps, accumulation thresholds) and severity floors live here to keep the SKILL.md body routing-focused.

---

Each Sub-check maps to one finding class. Every finding carries identity, A–H member, constrained severity, independence group, locator, package-local rule citation (`SAFEGUARD_LAYER.md` plus the resolved profile key), evidence, and suggested fix. Portfolio-root rules are historical provenance only and never operational authority.

## Sub-check A — Paragraph cadence (Cadence-Flag)

Apply `thresholds.cadence` directly. Cue-lexicon matches nominate turn-point candidates; they count only after functional confirmation as a transition, counter-move, worked example, or thematic refocus. Do not restate the bands here.

Severity floors and above-ceiling behavior come from `thresholds.cadence.bands` and `thresholds.cadence.above_ceiling`; this procedure does not own numeric or recurrence semantics.

> *Model examples → `references/examples/model_prose_corpus.md §Sub-check A`*

## Sub-check B — Sentence-length distribution (Rhythm-Flag)

Compute per-paragraph sentence-length mean (μ) and standard deviation (σ), then apply `thresholds.rhythm` from the resolved profile. The candidate remains a rhythm judgment: contrast and functional sentence shape matter more than a raw average.

Severity comes from `sub_checks.B` and its referenced profile thresholds; this prose creates no floor.

> *Model examples → `references/examples/model_prose_corpus.md §Sub-check B`*

## Sub-check C — First-use definition (First-Use-Flag)

Enumerate theoretical and domain constructs introduced in the section (a construct is any italicized term, any term tagged in the project's `research_notes/glossary.md` if present, or any term appearing in `references/terminology_register.md`). For each construct, locate its first occurrence in the section and verify a definition or worked illustration appears within the same paragraph or the immediately preceding paragraph. This is binding even for terms the author considers field-standard: `affordance`, `operationalization`, `socio-technical`, `intentionality`, `delegation`, `situated action`, `contradiction-mapping`.

Severity comes from `sub_checks.C`; evidence records whether the construct performs later conceptual work.

> *Model examples → `references/examples/model_prose_corpus.md §Sub-check C`*

## Sub-check D — Section-transition signposting (Signpost-Flag)

Every section in the manuscript opens with a one-to-three-sentence preamble that (a) tells the reader where they have arrived in the argument and (b) tells the reader what the section will contribute. This is not a chapter summary and not a prose abstract; it is a map fragment. The overlay checks the section's opening paragraph against a minimal signpost schema: an orienting clause (claim about position in the argument) AND a contribution clause (claim about what follows). A section lacking either clause is flagged.

Severity comes from `sub_checks.D`; the evidence distinguishes weak, absent, and cold-open structures.

> *Register quality within the orienting and contribution clauses is delegated to Sub-check H. D enforces structural presence; H enforces register construction.* (Added v0.10.1 with Sub-check H. The two checks remain orthogonal at the finding level — a signpost can be D-CLEAN with both clauses present and H-MAJOR if the clauses are register-inappropriate, and vice versa.)

> *Model examples → `references/examples/model_prose_corpus.md §Sub-check D`*

## Sub-check E — Jargon discipline within paragraphs (Jargon-Density-Flag)

Count new domain terms introduced per paragraph. A paragraph may introduce at most two new domain terms (a term is "new" if it has not been introduced earlier in the section or in a preceding section marked as its entry point in `references/terminology_register.md`). P-stage adjustment: P0 permits three (exploratory register); P2 permits one only (resolution register tolerates no ambiguity).

Severity comes from `sub_checks.E` and the profile's P-stage-adjusted cap.

> *Model examples → `references/examples/model_prose_corpus.md §Sub-check E`*

## Sub-check F — Worked examples at density spikes (Worked-Example-Flag)

Detect density spikes such as decompositions, multi-criteria evaluations, contested-claim clusters, or extended theoretical derivations. Apply `thresholds.worked_example` to candidate nomination and its local evidence window; the Evaluator judges whether an example, vignette, or concrete instantiation actually carries the conceptual load.

Severity comes from `sub_checks.F`; evidence distinguishes gestural, worked, and absent instantiation.

> *Model examples → `references/examples/model_prose_corpus.md §Sub-check F`*

## Sub-check G — Cumulative cognitive load / consolidation anchors (Consolidation-Anchor-Flag)

**Scope.** Full manuscript only. If the overlay is invoked with a section `heading_path` rather than a `scope: full_manuscript` directive, Sub-check G does not run and the overlay emits the `G_REQUIRES_FULL_MANUSCRIPT` noop reason code (per Precondition 2).

**Procedure.**

1. **Enumerate structural boundaries.** Read the manuscript outline, labelled pivots, and dependency structure, then apply the resolved `thresholds.consolidation` predicates. Project-local named boundaries may extend the inventory but cannot rewrite the package thresholds.
2. **Measure construct accumulation between boundaries.** For each span between consecutive boundaries (or between the manuscript opening and the first boundary), count distinct load-bearing constructs, positions, or tensions introduced — where load-bearing is defined as in `SAFEGUARD_LAYER.md` Check 8 Sub-check G procedure step 2.
3. **Apply the construct-accumulation threshold.** Read the candidate and dependency predicates from `thresholds.consolidation`.
4. **Check for consolidation anchors.** For each threshold-crossing boundary, read the paragraph preceding the boundary, the paragraph opening the next section, and any labelled transition between them. Verify a one-sentence consolidation anchor exists. The canonical anchor form is "At this point in the paper, [the reader holds X, Y, Z]; the next movement [does W with them]," but any sentence performing both the naming-of-accumulated-material and the signalling-of-next-move functions qualifies.
5. **Flag missed boundaries.** For each threshold-crossing boundary lacking an anchor, emit a Sub-check G finding with a structural-boundary locator (e.g., `end_§3`, `pivot_§5.2`, `opening_§6`), the construct count at that point, and the absence description. The `suggested_fix` field names the canonical anchor form and points to any adjacent paragraphs where insertion would least disrupt the surrounding register (per project directives, e.g., D-06's Vidal-cartographer register for INF3006Y).
6. **Word-count envelope.** Apply `thresholds.consolidation`; the profile owns its numeric envelope and verdict mapping.

**Severity.** Apply `sub_checks.G` and the referenced consolidation thresholds to structured boundary evidence.

**Interaction with Sub-check D.** D and G are orthogonal and additive. D audits local section-opening preambles; G audits cumulative anchor placement at structural boundaries. A section opening can satisfy D while omitting the G anchor, and vice versa. When a Generator is applying a fix, D-targeting preambles and G-targeting anchors can co-locate in the same paragraph, but the two sentences should do distinct work.

**Transition binding.** Read G's transition meaning from `transitions.G` and its live state only from `phase_state.json.milestone_framework.policy_bindings.reader_accessibility.transitions.G`. When active, severity is recorded while G is excluded from the gate aggregate. Do not infer state from dates or classification prose.

**Stability sub-mode.** `run-phase-3-stability` reads G's profile transition meaning and bound live state. Byte stability does not create a second advisory flag or retirement authority.

> *Model examples → `references/examples/model_prose_corpus.md §Sub-check G`*

## Sub-check H — Register Appropriateness (Register-Flag, added v0.10.1)

**Provenance.** Authored 2026-04-27 per advisor consultation captured in `docs/superpowers/plans/2026-04-27-accessibility-subcheck-h-amendment.md`. Operationalises the user's daily-language directive at two integration points: a passage-scoped overlay rule that applies to non-technical passages within a manuscript, and a manuscript-scoped `register_class` field in `directives.md` that conditions the rule's whole-manuscript variant for non-technical-audience manuscripts. Closes the gap diagnosed in §2 of the plan doc — Sub-checks A–G measure surface quality dimensions but none govern register tone.

**Scope (passage-scoped variant).** H runs over the five non-technical passage roles already named elsewhere in the protocol: section signposts (orienting + contribution clauses; D enforces structural presence, H enforces register construction); section framing / introduction prose; inter-section transitions; worked-example vignettes at density spikes (F locates the spike, H audits the vignette body); cumulative consolidation anchors at structural boundaries (G locates the boundary, H audits the anchor sentence). The overlap with D, F, and G is deliberate — those Sub-checks audit structural presence; H audits register construction within the structurally-required passage. A passage can be D-CLEAN / F-CLEAN / G-CLEAN and H-MAJOR, and vice versa.

**Signpost role split — orienting clause vs. contribution clause (added v0.10.2).** Section signposts decompose into two clause types with different register obligations: the **orienting clause** answers the reader's "where am I in the argument?" question and is binding at Ph2 with **stricter lay-term register** (BLOCKER-CANDIDATE at Ph2 if zero positive markers fire); the **contribution clause** answers "what does this section do?" and is binding at Ph3 with **technical density permitted** (advisory only at Ph2). Holding both clause types to the same lay-term standard under-fires on weak orientation prose and over-fires on legitimate technical-contribution prose; the v0.10.2 split closes both gaps. Detection: the orienting clause is the first clause whose grammatical subject is a backward-reference token (`having`, `after`, `so far`, `in the preceding`, `up to this point`, `this section`, `the previous section`); the contribution clause is the first clause whose grammatical subject is a forward-reference token (`this section`, `what follows`, `I now`, `I turn to`, `the next move`, `I will show`, `the contribution here`). When the same `this section` token appears in both roles, the **clause containing the verb of action** (`does`, `argues`, `shows`, `operationalises`, `develops`) is the contribution clause; the other is the orienting clause. The two clause types may co-locate in a single sentence; the H finding splits accordingly with locators `signpost_orienting_§X_line_Y` and `signpost_contribution_§X_line_Y`.

**Functional removability test (passage-scope eligibility).** A passage is classified as non-technical and subject to H iff removing every domain-term token from the passage and substituting plain-language glosses preserves the paragraph's propositional content. If propositional content is destroyed by gloss-substitution → the passage is technical, H does not apply, the paragraph is left to E's term-density discipline alone. The "domain-term token" scope mirrors Sub-check C's "construct" definition: italicised terms, terms in `references/terminology_register.md`, and project-glossary entries from `research_notes/glossary.md` if present. The test is **fuzzy by design** — the alternative is hard scoring, which the protocol's anti-dilution stance forbids. Misclassifications self-correct across iterations: a paragraph mis-flagged as non-technical fires H findings the user can downgrade to MINOR; a paragraph mis-classified as technical escapes H but is caught at the next round if its register remains poor.

**Positive markers (presence signals compliance).** Within a non-technical passage, H emits findings against four positive markers (raised from three at v0.10.2; the fourth captures the register-consistency / tone-shift-signposting principle):

1. **Concrete-referent anchoring (operationalised at v0.10.2).** At least one concrete referent per paragraph, where a *concrete referent* is one of three explicitly enumerated classes:
   - **(i) Physical or material entity.** A building, a tool, a body, a document, a piece of code, a physical artefact — referents whose existence is observable independent of theoretical commitment.
   - **(ii) Named individual or group.** A stakeholder named in the case (e.g., "the loan officer Maria"), a community of practice, a specific actor, an identifiable institutional role-holder. Generic role nouns ("the user", "the analyst") count only when the role is attached to a specific scenario in the same paragraph.
   - **(iii) Specific scenario or worked vignette.** A documented case, a worked example, a hypothetical with named participants and concrete stakes (e.g., "a Q4 product-recall decision in which the operations lead must reconcile..."). The vignette must carry sufficient particularity that the reader can visualise it.

   **Defined constructs are explicitly excluded** from the concrete-referent count: a Sub-check C term (italicised; in `references/terminology_register.md`; or in `research_notes/glossary.md`), an i\* construct (`actor`, `softgoal`, `task`, `Strategic Dependency model`), a domain-formal definition — these are referentially precise but abstract for H purposes; treating them as concrete reopens the dilution back-door (a paragraph trivially passes the concrete-referent marker on construct count alone). The exclusion mirrors §9e's domain-term-token treatment in the functional removability test.

   *Advisory-period default*: qualitative judgment by the Evaluator using the three-class definition above; quantitative thresholds (e.g., ≥1 concrete referent per 100 words) deferred to `docs/superpowers/plans/2026-04-27-h-quantitative-thresholds.md` for post-flag-retirement adjudication.
2. **Agent-verb-object default.** Majority of sentences in the passage take a human or identifiable agent as grammatical subject. Nominalised constructions and passives that obscure agency are tracked. The "identifiable agent" includes the same three concrete-referent classes (physical/material entity if the entity has agency; named individual or group; named participant in a scenario). A sentence whose subject is an abstraction ("the analysis", "the framework", "the contribution") fails this marker. *Advisory-period default*: qualitative majority judgment; quantitative threshold (e.g., ≥60% agent-subject sentences) deferred per the same retirement-decision rationale.
3. **Discourse-connective transparency (whitelist-defined at v0.10.2).** Transition words drawn from common English connectives (`but`, `so`, `because`, `this means`, `in other words`) rather than Latinate academic connectives. The v0.10.1 vague exemption ("unless the Latinate form is genuinely more precise") is replaced with a defined **load-bearing-Latinate whitelist** of academic-precision connectives that ARE permitted in non-technical passages because no plain-English equivalent carries their semantic-function load:
   - `whereby` — introduces a manner or mechanism. The substitute "by which" loses the manner-specificity (a mechanism description, not just an instrumental relation).
   - `hence` — establishes logical entailment. The substitute "so" is causally weaker (correlation or sequencing, not strict entailment).
   - `notwithstanding` — introduces an acknowledged constraint that does not block the main claim. The substitute "even with" loses the formal-acknowledgment register that signals the constraint has been considered.
   - `insofar as` — introduces a partial scope or qualification with a precise boundary. "To the extent that" is wordier and functionally equivalent only when the scope boundary is fuzzy; `insofar as` carries the precision when it matters.
   - `qua` — introduces role-as-such (X qua Y = X considered in its capacity as Y). No plain-English substitute carries the role-as-such precision.
   - `mutatis mutandis` — introduces an analogous case with the necessary changes made. No plain-English substitute carries the changes-as-needed precision economically.

   The whitelist is canonical at `references/lay_term_lexicons.md` (added v0.10.2; per-project override deferred to v0.10.3 per Q4 2026-04-27 adjudication). Other Latinate connectives (`hitherto`, `heretofore`, `inasmuch as`, `prima facie` outside its term-of-art usage) remain on the flag list. The whitelist is closed-by-default — entries are added only when a connective passes the no-plain-English-equivalent test.
4. **Register-shift signposting (added v0.10.2).** When register intentionally shifts within a passage — abstract-to-concrete, technical-to-narrative, or vice versa — the shift is announced via a signposting cue: `consider concretely:`, `in plain terms:`, `to put this technically:`, `taking a concrete case:`, `at the methodological level:`, or any equivalent that flags the tone change for the reader. Implicit register shifts (a sentence drops a methods-section label into narrative prose with no announcement; a vignette pivots into formal-academic register without warning) are flagged as register-discontinuity findings. Register *consistency* across adjacent passages of the same role is enforced implicitly: two consecutive signpost orienting clauses should hold the same register, and an unannounced shift between them fails this marker on the second clause. The marker captures the user's directive 2026-04-27: "Being consistent is also important. And, a proper signpost at every tone shift."

   **M4 vehicle preference and §3 interaction (added post-v0.10.2).** Preferred M4 vehicles, in order: (1) **semicolon** for contrast-bridge pivots ("not a political stance; it is a question of method"); (2) **colon** for specification pivots ("the design implication: the framework must surface trade-offs, not collapse them"); (3) explicit signposting phrases from the list above. **Em-dash is last-resort**: it is a valid M4 signal but is counted by `references/DETERMINISTIC_CHECKS.md §3` (≤1 em-dash pair per paragraph; ≤0 under zero-em-dash discipline). A Generator that satisfies M4 via em-dash on a manuscript at its §3 em-dash limit has opened a §3 regression to close an H finding — the opposite of a fix. Preferred substitution: replace the em-dash with a semicolon or colon; same M4 credit, zero §3 cost. The INF3006Y Reconciled manuscript demonstrates this at scale: every em-dash in the Generator drafts was substituted with semicolons/commas in the final manuscript, landing zero em-dashes with H-CLEAN across all orienting clauses. This pattern is named in DETERMINISTIC_CHECKS §3 as the 'H-motivated em-dash insertion' false-fix pattern and documented with transformation examples at `references/lay_term_lexicons.md §4`.

**Negative markers (presence flags violation).** Three counted patterns:

1. **Unnecessary nominalisation.** Verbs converted to abstract nouns where the verb form would carry the same content (`the operationalisation of` instead of `how we operationalise`). Counted per paragraph.
2. **Stacked prepositional phrases.** Three or more consecutive prepositional phrases in a single clause. A hallmark of academic register creep where the structure is not doing conceptual work.
3. **Hedging pile-up.** More than two epistemic hedges per sentence (`it might perhaps be suggested that there could potentially be...`).

**Pre-filter integration (§9e).** Profile-routed negative-marker probes emit structured passage candidates. Threshold values are loaded from `thresholds.register`, not this prose.

**H step 1 procedure.** Read the passage's §9e negative-marker bundle, then always run the positive-marker presence audit. A bundle with every negative probe clear may skip negative-marker elaboration, but it cannot emit `NULL/CLEAN` or suppress a positive-marker finding. When the bundle is absent, run the same semantic procedure from scratch; only runtime cost changes.

**Twin-paragraph probe (added v0.13.0).** When H closes a finding on a non-technical passage that ships specific shibboleth phrases (a Latinate construction such as `stipulating away`, a noun-pile compound such as `register-boundary light`, a four-times-repeated technical noun, or any phrase that the H finding's evidence field cited as the violation locus), H emits a follow-on probe `twin_candidate_<finding_id>` that performs a deterministic grep over the manuscript for those shibboleth phrases. If the grep returns >0 hits outside the passage that triggered the finding, H emits a `twin_candidate_<location>` finding for the next round at that location's passage role. Probe is implemented in `DETERMINISTIC_CHECKS.md §9e` as suffix `_twin_paragraph`.

**Rationale.** Manuscripts often return to the same conceptual debt at structurally parallel sites (a §1 / §2 register-boundary aside and a §5 / §6 closing summary; a §3 sibling-subsection diagnosis and its §4 mirror). Fixing one without scanning for the other leaves a conspicuous asymmetry in the published manuscript. The probe catches the structural twin before the next H-cycle finds it. Surface lift: low (one grep per finding-close); precision lift: high (catches the §2 / §5 lay-term twin pattern documented in `lay_term_lexicons.md §5`).

**Probe behavior.** The shibboleth phrases are extracted from the H finding's evidence field automatically; no manual phrase-list maintenance is required. A clear twin grep emits no twin candidate, but it does not classify the underlying passage. A fired grep emits `twin_candidate_<location>` referenced to the original finding's `evidence_id` for adjudication continuity. **Provenance:** source memo `docs/superpowers/plans/2026-04-30-voice-and-h-lessons.md` cluster 3.3.

**Compliance frame: presence of positive markers, not absence of negative markers.** This inversion rewards register craft rather than treating a quiet negative pre-filter as proof of accessibility. Load marker counts and severity semantics from `thresholds.register`; this prose does not restate them.

**Manuscript-scoped variant (audience-conditioned, via `directives.md` `register_class` field).** A new field is added to `research_notes/directives.md`: `register_class: technical | mixed | non-technical`. Default `technical` for any manuscript whose P-stage classification places it in a peer-reviewed scholarly venue (the harness's primary use case). The user sets `mixed` for hybrid documents (a thesis chapter aimed partly at committee, partly at an applied audience) or `non-technical` for a public-interest write-up, policy memo, or trade-press article. The field is **orthogonal to P-stage**: P-stages govern depth/scope of engagement; `register_class` governs target-audience register requirements. A P0 manuscript for a specialised journal and a P0 manuscript for a policy audience have the same depth but different register requirements.

`register_class` composes with H's passage scope:

- **`register_class: technical`** → H applies only to the five enumerated non-technical passage roles. Technical paragraphs are exempt.
- **`register_class: mixed`** → H applies to non-technical passage roles plus the abstract, introduction, and conclusion (the four-section list — abstract / introduction / conclusion / non-technical passages). Theory / methodology / results sections remain exempt.
- **`register_class: non-technical`** → H applies manuscript-wide. Technical paragraphs (those that fail the functional removability test) still retain their domain terms but are also held to the positive-marker construction requirements at the sentence level.

**Severity floors.** Apply `thresholds.register.severity_model` and `sub_checks.H.ph2_role_overrides` directly. Do not restate their numbers here.

**Transition binding.** Read H's meaning from `transitions.H` and live state only from the policy-binding Planner event projection. Legacy reports are evidence, not counters.

**Per-finding telemetry.** H may emit `false_positive_candidate` for calibration, but calibration files do not own retirement criteria or state. Transition requirements come from `transitions.H`; only matching append-only Planner observation and approval events under the policy binding can retire H.

**Back-compatibility evidence.** `inherited_from_pre_h` may be retained as provenance, but it cannot rewrite severity or transition state. Only the profile meaning plus bound Planner events control workflow effect.

**Stability sub-mode.** Apply `runtime_modes.stability` from the resolved profile. Stability controls workflow reuse only; it does not rewrite H severity or remove H from the canonical aggregate.

**Interaction with Sub-checks D, F, G.** D enforces section-opening structural presence; H enforces register quality within the orienting and contribution clauses (cross-reference at D's entry above). F locates density spikes; H audits the worked-example vignette's register quality. G locates threshold-crossing structural boundaries; H audits the consolidation anchor sentence's register quality. The two-Sub-check pattern (structural-Sub-check + register-Sub-check) is deliberate — D/F/G can be CLEAN while H is MAJOR if the structurally-required passage is registered inappropriately, and vice versa. When a Generator is applying a fix, the structural Sub-check's suggested_fix and H's suggested_fix can co-locate in the same paragraph but the two sentences should do distinct work.

> *Model examples → `references/examples/model_prose_corpus.md §Sub-check H`*
