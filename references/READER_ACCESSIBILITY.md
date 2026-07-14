# Reader Accessibility

## Purpose and authority

Reader accessibility reduces extraneous prose load while preserving intrinsic difficulty and supporting the reader's model-building work. The package-local machine authority is `references/policies/reader_accessibility.v1.json`, resolved through `scripts/reader_accessibility_policy.py`. Its exact human-readable numeric projection is `references/generated/reader_accessibility_policy_view.md`.

This document owns the semantic purpose of the policy. It does not own threshold values, severity arithmetic, transition counts, recurrence counts, or runtime exceptions. Operational prose cites profile keys; only the generated view may display their numeric projection.

The precedence ladder remains user → venue → project → package → root. A project may alter reader-accessibility behavior only through the profile's declared `override_contract`. Unregistered prose directives cannot rewrite package policy.

## Accessibility model

Accessibility operates at local and cumulative temporal scales. The local scale covers prose processed within a reading turn. The cumulative scale covers constructs, positions, and tensions carried across the manuscript. A manuscript can pass local cadence, rhythm, definition, signposting, jargon, and example checks while still imposing a cumulative tax when later argument depends on material that was never consolidated.

Sweller's cognitive-load distinction supplies the telos. Intrinsic load is the irreducible difficulty of the material. Extraneous load is friction added by the prose. Germane load is the effort spent building the mental model. Accessibility reduces extraneous load without flattening intrinsic difficulty and helps germane effort remain productive.

Register appropriateness is orthogonal to the local/cumulative distinction. The structural checks audit cadence, rhythm, definitions, signposting, jargon, worked examples, and consolidation. H audits register construction within structurally required passages. H is functional rather than a readability score and preserves the anti-dilution stance through positive construction, not mere absence of negative probes.

## 13.3 Operational criteria

This stable semantic anchor maps criterion labels A–H to profile-owned predicates. It intentionally contains no numeric threshold or verdict arithmetic.

- **A — cadence.** Apply `thresholds.cadence`. Deterministic cue hits nominate possible turn points; the overlay confirms whether they perform a transition, counter-move, worked example, or thematic refocus.
- **B — rhythm.** Apply `thresholds.rhythm` to sentence-shape evidence, then judge rhetorical function. Rhythm is not reducible to an average.
- **C — first use.** Apply `thresholds.first_use`. A construct must be defined or worked through before later conceptual use.
- **D — signposting.** Apply `thresholds.section_signpost` to the bounded opening and require orienting and contribution functions. D checks structural presence; H judges register construction.
- **E — jargon.** Apply the resolved P-stage entry under `thresholds.jargon`. Track terms in introduction order and treat deterministic counts as candidates.
- **F — worked examples.** Apply `thresholds.worked_example` to nominate density spikes, then judge whether an example carries the conceptual load.
- **G — consolidation.** Apply `thresholds.consolidation`. Word-and-cue gaps remain proxy candidates; the Evaluator decides whether construct accumulation crosses the policy predicate and whether an anchor performs the needed consolidation.
- **H — register.** Apply `thresholds.register`, `register_scope`, `sub_checks.H`, and `domain_native_register.warrant_layers.surface`. The M1 reader target comes from `domain_native_register.reader_model`; the separate `passage_scope_class` selects H geometry. A clear negative prefilter never substitutes for the positive-marker audit, and absence of attestation is advisory only.

Check 8 membership is exactly A–H. VE is an adjacent advisory under `adjacent_advisory_checks.VE`; it never joins the aggregate. Canonical Check 8 evidence stores structured findings and independence groups, derives subcheck verdicts, applies transition state from the authoritative policy binding, and routes recurrence separately from semantic severity.

## Functional judgment guards

### Cadence candidates are not verdicts

A cue token earns no credit by mere presence. The overlay must identify the function it performs in the paragraph. Likewise, punctuation may show internal structure without proving a thematic turn. Above-ceiling behavior, mandatory splitting, and severity floors come from `thresholds.cadence`.

### Signposts are bounded by geometry

The D procedure reads the section opening only until the next heading. Shared Markdown/TeX geometry preserves offsets, strips TeX comments before semantic nomination, and prevents a later section's prose from satisfying an earlier heading. The opening window comes from `thresholds.section_signpost`.

### Consolidation is cumulative judgment

G asks what the reader must still carry at a structural boundary. A valid anchor names the accumulated material and signals how the next movement will use it. D and G may co-locate, but they perform different work: D orients locally; G consolidates backward before the argument moves on.

### Register construction is not register choice

H audits register construction within passages selected by `register_scope` and the project's `passage_scope_class` (legacy passage-scope `register_class` is an alias). The canonical M1 target remains `domain_native_register.reader_model.register_class: domain-native`, not lay simplification. Technical prose retains necessary domain terms. The functional-removability test asks whether plain glosses preserve the proposition; if they do not, E governs technical density while H respects the conceptual requirement.

Surface warrant and argument-architecture warrant stay separate under `domain_native_register.warrant_layers`. H hosts surface warrant; the argument layer routes to the checks listed in the profile and never contributes to Check 8 merely because the same exemplar was consulted. Writing, review, and revision follow `domain_native_register.derivations`. Retrieval conditions drafting without determining it, warrant absence stays advisory, and revision preserves propositional content under `domain_native_register.c7_fence` rather than auto-rewriting the identity layer.

For eligible passages, inspect concrete anchoring, identifiable agents and actions, transparent connectives, and explicit cues when register shifts. Negative probes nominate unnecessary nominalisation, stacked prepositional phrases, and hedge accumulation. Load marker thresholds and verdict semantics only from `thresholds.register`.

## Qualitative examples

### Passing orienting clause

> Having traced how Maria reconciles the product-recall evidence, this section turns to the design implication: the framework must surface trade-offs rather than collapse them.

The clause uses a named participant and concrete situation, keeps the participant's action visible, uses a transparent connective, and announces the shift into a design claim. The overlay records those functions and applies the resolved register policy; this example does not compute a verdict.

### Cold methods label

> The empirical grounding of the subsequent argumentation is methodologically anchored.

The sentence labels a method but does not orient the reader in the argument. A better clause should preserve the surrounding voice and state the relationship directly, such as: *This is not a speculative argument.* D judges the orienting function; H judges register construction.

### Precise but unanchored construct prose

> The Strategic Dependency and Strategic Rationale models jointly operationalise the intentional and rationale-bearing dimensions of actor relations.

The sentence is technically precise, but defined constructs do not themselves supply a concrete anchor. The overlay distinguishes disciplinary precision from reader anchoring and asks whether the passage needs a scenario or an explicit register cue. Threshold aggregation remains profile-owned.

### Revised positioning prose

> I keep a deliberate distance from those labels. This is not a political stance; it is a question of method. The survey needs to examine the frameworks as objects of inquiry, not as positions it already accepts.

The revision uses active first person, transparent connectives, and an explicit bridge into the methodological claim. Those are functional observations. `thresholds.register` owns their aggregation and verdict.

Historical and positive-model calibration passages live in `references/examples/model_prose_corpus.md`. Calibration examples may support judgment but cannot become an independent threshold authority.

## Runtime and provenance

Resolve the profile at the project boundary and record its package and project source bindings. Candidate artifacts bind the manuscript hash, phase, cycle, resolved profile, source bindings, and register class. F1 recomputes candidates from trusted frontmatter cycle provenance and requires exact equality.

Check 8 evidence binds the same cycle, manuscript, phase, and resolved profile. Its G/H transition snapshot must match the authoritative phase-state binding. Rehashing a candidate or Check 8 sidecar from another round does not make it current.

Stability loads `runtime_modes.stability` plus bound transition state. It may govern workflow reuse but creates no independent member exclusion, severity rewrite, retirement authority, or escalation exception.

Persistence keys on content hash and approved revision evidence. It may produce workflow escalation evidence while leaving recorded semantic severity unchanged. Recurrence routes through `recurrence`; it does not silently rewrite a finding's verdict.

## Calibration status

The cadence architecture decision is accepted by the user with the approval date recorded under `decision_approval`. Acceptance governs the banded cadence rule and its profile-owned semantics; the numeric calibration remains provisional. In particular, `thresholds.cadence.calibration_status` marks the current `thresholds.cadence.hard_ceiling_words` default as tunable pending real-manuscript calibration. The generated policy view records both statuses exactly. Examples and historical reports remain calibration evidence, not approval provenance.
