# Lay-term lexicons

**Purpose.** Canonical reference file for the lexicons consumed by SAFEGUARD Check 8 Sub-check H (Register Appropriateness) and `DETERMINISTIC_CHECKS.md §9e` (H pre-filter). The lexicons live here as a versioned, structured artefact rather than embedded in prose so future revisions can be tracked, per-entry rationale captured, and per-project override semantics implemented cleanly when v0.10.3 ships the override mechanism.

**Status (2026-04-27).** v0.10.2 introduces this file as the canonical home for three lexicons: the hedge list, the discourse-connective list, and the load-bearing-Latinate whitelist. Per-project override is documented but **not implemented** at v0.10.2 per Q4 adjudication 2026-04-27 (defer to v0.10.3).

**Status (2026-04-30, v0.13.0).** §5 added — verified lay-term paraphrase examples from the INF3006Y 2026-04-30 §2 / §5 twin-fix, anchored under a new drift-detection grep-cadence requirement (mandatory at every H-cycle, implemented as `_corpus_drift` probe in `DETERMINISTIC_CHECKS.md §9e`). The drift-detection mechanism is the operational fallback for live-manuscript projects where source-snapshot stability cannot be assumed; it converts the §4-retired-on-drift principle from post-hoc audit to active monitoring. See §5 below and source memo `docs/superpowers/plans/2026-04-30-voice-and-h-lessons.md` cluster 3.5.

**Override mechanism (forward-looking, deferred to v0.10.3+).** Each lexicon may be overridden per-project by a corresponding file under `research_notes/`: `research_notes/hedge_terms.md` for the hedge list; `research_notes/connective_terms.md` for the connective list; `research_notes/latinate_whitelist.md` for the Latinate whitelist. The override mechanism is: if the project file exists, it replaces the built-in default; if absent, the built-in default is used. This file's lists ARE the built-in defaults.

---

## 1. Hedge list (15 markers)

Consumed by: §9e probe 3 (hedging density); Sub-check H negative marker 3 (hedging pile-up).

| Marker | Class | Rationale |
|---|---|---|
| `may` | epistemic possibility | Standard hedge; appropriate when the claim is genuinely conditional. |
| `might` | epistemic possibility | Tighter than `may`; appropriate for hypothetical reasoning. |
| `could` | epistemic possibility | Often substitutable for `may`; flagged when stacked with other hedges. |
| `perhaps` | epistemic uncertainty | Adverbial hedge; flagged at high density (>2/100w) as register-soft. |
| `possibly` | epistemic uncertainty | Stronger than `perhaps`; flagged on stacking. |
| `likely` | probabilistic estimate | Less hedge-like in technical contexts (probabilistic claim) but counts toward density. |
| `suggests` | epistemic indirection | Verbal hedge; flagged when the data could support a stronger verb (`shows`, `demonstrates`). |
| `indicates` | epistemic indirection | Sister to `suggests`; same flag rule. |
| `appears` | epistemic indirection | Tighter than `suggests`; flagged on stacking. |
| `seems` | epistemic indirection | Conversational register; flagged at any density in formal academic prose. |
| `somewhat` | quantitative softening | Flagged when paired with another hedge in the same sentence. |
| `relatively` | quantitative softening | Same rule. |
| `generally` | scope-softening | Flagged when used to evade specifying a scope; CLEAN when used with an explicit scope qualifier. |
| `typically` | scope-softening | Same rule as `generally`. |

**Source.** Compiled from Hyland (2005) *Stance and Engagement* and Biber et al. (1999) *Longman Grammar* hedge-marker enumerations, narrowed to the 15 most-commonly-stacking markers in academic-prose corpora. The `-tion`/`-ment` nominalisation patterns and modal-verb categories not in this list are addressed at the negative-marker level rather than the lexicon level.

**Override semantics (deferred to v0.10.3).** A project that operates in a sub-discipline with discipline-specific hedge conventions (e.g., legal scholarship's `arguably`, `colourable claim`; medical research's `is consistent with`, `non-significant trend toward`) will be able to author `research_notes/hedge_terms.md` with the discipline-specific list. The v0.10.3 override mechanism replaces — not supplements — the built-in list, so per-project lists must include any built-in entries the project wishes to retain.

---

## 2. Discourse-connective list

Consumed by: Sub-check H positive marker 3 (discourse-connective transparency).

### 2.1 Plain-English connectives (preferred in non-technical passages)

`but`, `so`, `because`, `this means`, `in other words`, `for example`, `consider`, `take the case of`, `to put it differently`, `which is to say`, `here too`, `again`, `yet`, `by contrast`.

These are the connectives the Evaluator looks for when auditing marker 3 in non-technical passages. Presence signals compliance.

### 2.2 Latinate connectives flagged outside the whitelist

`hitherto`, `heretofore`, `inasmuch as`, `albeit` (when not introducing a concession in a high-register passage), `prima facie` (outside its term-of-art usage in legal/philosophical contexts), `pursuant to`, `with respect to` (when `for` or `about` would carry the same content).

These are flagged as register-creep candidates in non-technical passages. The flag fires unless the passage is technical (functional removability test) or under `register_class: technical` exemption.

### 2.3 Load-bearing-Latinate whitelist (added v0.10.2; permitted in non-technical passages)

The v0.10.1 vague exemption ("unless the Latinate form is genuinely more precise and no plain-English equivalent suffices") is replaced with the following defined whitelist. Each entry is permitted in non-technical passages because no plain-English substitute carries the semantic-function load economically.

| Connective | Function | Why no plain-English substitute carries the load |
|---|---|---|
| `whereby` | introduces a manner or mechanism | "By which" loses the manner-specificity; `whereby` precisely indicates a description of how, not just an instrumental relation. |
| `hence` | establishes logical entailment | "So" is causally weaker (correlation or sequencing); `hence` signals strict entailment between premise and conclusion. |
| `notwithstanding` | introduces an acknowledged constraint that does not block the main claim | "Even with" or "despite" loses the formal-acknowledgment register that signals the constraint has been considered and judged not blocking. |
| `insofar as` | introduces a partial scope or qualification with a precise boundary | "To the extent that" is wordier and only equivalent when the scope boundary is fuzzy; `insofar as` carries the precision when the boundary is the load-bearing detail. |
| `qua` | introduces role-as-such (X qua Y = X considered in its capacity as Y) | No plain-English substitute carries the role-as-such precision economically. Substitutes ("considered as", "in its capacity as") are wordier and lose the philosophical-pragmatic precision. |
| `mutatis mutandis` | introduces an analogous case with the necessary changes made | No plain-English substitute carries the changes-as-needed precision. The phrase "with the necessary modifications" is wordier and reads as a translation rather than a register-native usage. |

**Whitelist closure rule (v0.10.2).** The whitelist is **closed-by-default**: entries are added only when a connective passes the no-plain-English-equivalent test. The test has three parts:

1. **Function specificity.** The connective performs a distinct semantic-function role (manner, entailment, qualification, etc.) that the candidate plain-English alternatives only approximate.
2. **Economy.** The plain-English alternatives are at least 30% wordier in typical usage.
3. **Register-coherence.** The Latinate form carries a register signal (formal-acknowledgment, philosophical-precision) that the plain-English alternatives cannot replicate without a separate register marker.

A candidate connective must satisfy all three parts to be added to the whitelist. Borderline cases (e.g., `vis-à-vis`, `per se`, `inter alia`) are kept off the whitelist by default; the v0.10.3 retirement-decision plan doc captures any whitelist expansion proposals that arise during the H advisory period.

**Override semantics (deferred to v0.10.3).** A project working in a sub-discipline where additional Latinate connectives are load-bearing (e.g., legal scholarship's expanded set, medical-research's Latinate-rich terminology) will be able to author `research_notes/latinate_whitelist.md` to add discipline-specific entries. The v0.10.3 override mechanism is additive on the whitelist (project entries supplement the built-in defaults rather than replace them) — opposite polarity to the hedge-list override, because the whitelist is exemption-bearing rather than violation-bearing.

---

## 3. Domain-term-token exclusion list (Sub-check H functional removability test)

Consumed by: Sub-check H functional removability test (passage-scope eligibility); §9e nominalisation probe (suffix-pattern exclusion list, content-bearing nominal subset).

### 3.1 Content-bearing nominals (excluded from §9e nominalisation probe; 20-term default)

`introduction`, `conclusion`, `abstract`, `methodology`, `discussion`, `reference`, `definition`, `condition`, `relation`, `application`, `operation`, `representation`, `description`, `interpretation`, `specification`, `implementation`, `verification`, `evaluation`, `presentation`, `generation`, `orientation`.

These are content-bearing nominals whose removal would lose meaning, not register inflation. They are excluded from §9e probe 1 (nominalisation density) so the probe does not over-fire on legitimate academic-content nouns.

### 3.2 Domain-term-token classes (excluded from concrete-referent count under marker 1)

The following classes of token are domain terms for Sub-check H purposes — they are excluded from the concrete-referent count under positive marker 1 because referential-precision-without-anchoring does not satisfy the marker's reader-anchoring purpose:

- **Italicised terms** (`*term*` in Markdown; `\emph{term}` in LaTeX). Italicisation marks first-use definition or term-of-art status.
- **Terms in `references/terminology_register.md`** (project-tier glossary; load-bearing constructs the manuscript treats as defined).
- **Terms in `research_notes/glossary.md`** (project-tier glossary; user-curated).
- **i\* framework constructs** (`actor`, `softgoal`, `task`, `goal`, `dependency`, `Strategic Dependency model`, `Strategic Rationale model`, `intentional`, `rationale-bearing`).
- **GORE/AORE constructs** (`agent`, `protocol`, `belief`, `commitment`, `role`, `responsibility`).
- **HCI constructs** (`affordance`, `intentionality`, `operationalization`, `socio-technical`, `delegation`, `articulation work`).

The list is the harness's working baseline and is extended per-project via the project-tier glossaries above. The Sub-check H functional removability test substitutes plain-language glosses for tokens in these classes when classifying a passage as technical or non-technical.

---

## 4. Verified lay-term paraphrase examples (INF3006, 2026-04-27 — RETIRED 2026-04-28)

> **Status: RETIRED 2026-04-28.** The five paraphrase entries below were drawn from a snapshot of the INF3006Y Reconciled.md manuscript that the project owner subsequently treated as a live working file rather than as a terminal/archived snapshot. Three additional refinement passes on 2026-04-28 (architectural density re-pacing; sentence-level syntactic refactor; advisor-driven postscript) rewrote the §1 framing paragraph that supplied these paraphrases. Three of the five accepted-paraphrase entries no longer appear in the manuscript at all; two are present in modified form. The corpus is preserved here as a historical record of what passed H review at the snapshot it was extracted from, but **none of these entries is byte-current against the live manuscript**, and they should not be cited as if they were. New calibration entries should be drawn only from terminal/archived manuscript snapshots — see "Lessons for corpus authoring" below.

**Original purpose (preserved).** A reference set of confirmed successful lay-term transformations drawn from the INF3006Y manuscript. Each entry showed the original dense formulation alongside the paraphrase that passed Sub-check H marker review. The table was an *existence proof*, not a template: it demonstrated that propositional content survives the register shift, and anchored the Evaluator's calibration for similar formulations in other projects.

**Source passage context (at snapshot, retired).** The passage appeared in INF3006Y's survey-framing paragraph at L21 of the 2026-04-27 Reconciled.md snapshot. Classified `register_class: mixed` at the time; the framing sentences were non-technical passage-role (section framing) and therefore in H's scope.

**Snapshot-historical paraphrase table (DO NOT CITE AS CURRENT).**

| Original formulation | Accepted paraphrase (snapshot form) | Marker gain | Drift status (2026-04-28) |
|---|---|---|---|
| "methodological, not polemical" | "not a political stance; it is a question of method" | M2 ("it is a question of") + M4 (semicolon bridges negation → positive claim) | **REMOVED** from current manuscript |
| "analytical distance from hype labels" | "deliberate distance from buzzwords" | M3 (`buzzwords` replaces Latinate `hype labels`) | **REMOVED** |
| "premature theoretical commitment" | "committing too early to any single theoretical lens" | M2 (gerund agent: `committing`) + M3 (`too early` vs abstract `premature`) | **REMOVED** |
| "actively contested framing whose built-in assumptions a theoretical survey ought to interrogate rather than defer to" | "a recent, still-debated label, and the assumptions it carries are part of what this survey needs to examine, not take for granted" | M2 (`this survey needs to examine`) + M3 (`not take for granted`) | **MODIFIED** — current manuscript reads "a recent, still-debated label whose built-in assumptions are part of what this survey needs to examine" (the "not take for granted" half cut) |
| "data points about how the field is currently carving its problem, not as maps I adopt" | "evidence of how the field is currently framing the problem, not as frameworks I follow" | M2 (`I follow`) + M3 (`not as frameworks I follow`) | **MODIFIED** — current manuscript reads "evidence of how the field is currently framing the problem" (the "not as frameworks I follow" half cut) |

**Sentence kept as-is at snapshot.** "The underlying question… will very likely outlast it." Current manuscript reads "is older than the label and will likely outlast it" — minor variation, same H verdict (CLEAN, no paraphrase needed) likely still holds; not re-adjudicated.

**Lessons for corpus authoring (added 2026-04-28).**

The drift surfaced here is the predictable consequence of drawing calibration corpus entries from a manuscript that the project owner has not closed. Two policy refinements follow:

1. **Source-snapshot stability requirement.** Calibration corpus entries should be drawn only from manuscript snapshots that satisfy at least one of: (a) Ph4-closed-and-acknowledged-as-final by the author; (b) accepted at a venue (DOI/preprint hash anchored); (c) committed to the harness `references/examples/` corpus (which does not change after addition). The 2026-04-27 INF3006Y snapshot satisfied (a) at the moment of corpus extraction but the author's working stance on the file shifted within 24 hours, retroactively invalidating (a). Future extractions must require explicit owner-confirmation that the snapshot will not be re-edited, OR draw from `references/examples/` corpus only.
2. **Drift-detection cadence.** When a corpus entry is anchored to a project file outside `references/examples/`, a follow-up grep on the source phrases at the next H-cycle on that project is mandatory. The 2026-04-28 standalone H verification round caught this drift on first pass; baking the grep into the H-cycle preconditions is a v0.12.4+ candidate.

**Generalisation notes (provisional; refine as calibration log grows).**

1. *Polemical / methodological opposition* → flip to first-person negation + plain declaration ("not X; it is Y") rather than noun-pair. The semicolon carries M4 as a contrast bridge without a separate signpost cue. (Em-dash also satisfies M4 but adds to the §3 count; see note 5 for the substitution rule that pins this down.)
2. *Abstract-quality adjective + Latinate noun* ("analytical distance", "premature commitment") → verb the quality ("deliberately distance", "committing too early"). The gerund form typically picks up M2.
3. *Relativised relative clause* ("whose built-in assumptions a survey ought to interrogate rather than defer to") → collapse to a plain subject-verb pair ("that this survey needs to examine, not take for granted"). One concrete agent + negation + plain verb = M2 + M3 in two tokens.
4. *Field-as-map metaphor* ("not as maps I adopt") → plain tool-use metaphor ("not as frameworks I follow"). Metaphor substitution preserves M3 and opens M2 via active first-person.
5. *Em-dash as draft M4, semicolon/colon in final*: The Generator's default M4 vehicle is the em-dash (least-resistance register-shift signal). Every em-dash used for M4 in a low-em-dash or zero-em-dash manuscript should be replaced with a semicolon (contrast pivot) or a colon (specification pivot) in the revision step. The substitution preserves M4 credit and eliminates the §3 count. Named as the 'H-motivated em-dash insertion' false-fix pattern in `DETERMINISTIC_CHECKS.md §3`. INF3006Y Reconciled baseline: zero em-dashes (all converted from Generator drafts).

These generalisations feed the `aggregate_h_calibration.py` training corpus. Mark a generalisation `false_positive_candidate: true` in the calibration log if a later round produces a counterexample.

---

## 5. Verified lay-term paraphrase examples (INF3006Y, 2026-04-30 — DRIFT-MONITORED)

**Status (2026-04-30).** v0.13.0 introduces this section as an active (not retired) corpus drawn from the INF3006Y manuscript's §2 closing aside fix and the §5 closing-summary twin-paragraph fix. Per the §4 retirement-lessons, the INF3006Y manuscript is treated as live by the project owner; entries here are anchored to source phrases and **subject to drift-detection grep-cadence** rather than to source-snapshot stability. Each entry transitions to RETIRED status (with a banner matching §4) if the next H-cycle grep on the source phrase returns zero hits in the live manuscript.

**Drift-detection grep-cadence requirement (added v0.13.0).** At every H-cycle on a project that contributes corpus entries here, the source-phrase grep is mandatory before the H verdict closes. The grep is implemented as a deterministic probe in `DETERMINISTIC_CHECKS.md §9e` (suffix `_corpus_drift`). If the source phrase is absent: the entry's status flips to RETIRED with banner; the §4-style snapshot-historical paraphrase table preserves the entry for historical reference; new corpus extractions on that source resume only after explicit owner-confirmation.

**Source passage context.** Two passages contributed to this corpus: §2's closing aside ("A note on the register the survey does not enter") and §5's pre-§6 closing summary (originally "One register sits just outside the survey..."). Both classified as `register_class: technical` consolidation anchors / register-boundary asides; both functionally non-technical by H's removability test.

**Paraphrase table (drift-monitored, anchored 2026-04-30).**

| Original formulation | Accepted paraphrase | Marker gain | Source phrase (grep anchor) |
|---|---|---|---|
| "stipulated, operationalizable definition" | "precise, measurable definition" | M3 (Latinate-pair → plain-pair) | `stipulated, operationalizable` |
| "stipulates away the very phenomena" | "defines away the phenomena" | M3 (drop "the very" intensifier; verb-pair simplification) | `stipulates away the very` |
| "operational reductions that stabilize the same words" | "operational simplifications" | M3 (collapse relativised clause; §4 note 3 pattern) | `operational reductions that stabilize` |
| "in this register-boundary light, the cost the IS/HCI literature pays" | "the cost the IS/HCI literature pays" | M2 (drop noun-pile adverbial; restore direct predication) | `in this register-boundary light` |
| "delegation as task allocation under a coordination protocol" | "*delegation* is the auction-style assignment of tasks under fixed rules" | M1 (italicization signals term-of-art); M3 (verb-pair `task allocation` → `the assignment of tasks`) | `task allocation under a coordination protocol` |
| "decision authority over a defined choice space" | "the range of moves each robot's planner may choose" | M1 (concrete agent: `robot's planner`); M3 (`decision authority` → `the right to decide` → verb-active form) | `decision authority over a defined choice space` |
| "system-level behavior arising from local agent rules" | "the throughput pattern that arises when every unit follows local rules" | M1 (concrete-referent: `unit`); M3 (verb-active `that arises when` vs. participial `arising from`) | `behavior arising from local agent rules` |

**Worked-example signpost as M4 vehicle (added v0.13.0).** The §2 fix introduced "Take a contract-net protocol coordinating a fleet of warehouse robots: ..." as the M4 register-shift signposting cue for technical-aside paragraphs. The pattern: `Take [a/an concrete-domain entity instance]: [italicised term-of-art] is [verb-active gloss]; ...` Italicization on the term-of-art signals §3.2 domain-token status (excludes from concrete-referent count). The "Take X:" opener satisfies M4 directly. The concrete entity (warehouse robots, drones, autonomous-vehicle fleets, etc.) carries M1. The pattern is **the recommended substitute** for M4-via-em-dash in technical-aside paragraphs at or below the §3 em-dash limit.

**Lessons for corpus authoring (carried forward from §4).**

1. **Source-snapshot stability requirement (still in force).** The drift-detection grep-cadence is a partial substitute for source-snapshot stability — it converts a static stability assumption into an active monitoring requirement. Where snapshot stability is feasible (project closure, venue acceptance, `references/examples/` commit), it is preferred; where the project is actively edited, drift-detection is the operational fallback.
2. **Drift-detection cadence (now mandatory at every H-cycle).** Originally a v0.12.4+ candidate per §4. Now elevated to mandatory at v0.13.0 via §9e probe `_corpus_drift`.

**Provenance.** Source memo: `docs/superpowers/plans/2026-04-30-voice-and-h-lessons.md` cluster 3.5.

---

## Versioning

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-04-27 (v0.10.2) | Initial extraction from prose-embedded lists in §9e, sub_checks.md, and READER_ACCESSIBILITY.md. Three lexicons (hedge / connective / domain-term) consolidated. Six-entry load-bearing-Latinate whitelist added (closure rule defined). Per-project override semantics documented; implementation deferred to v0.10.3 per Q4 adjudication 2026-04-27. |
| 1.1 | 2026-04-28 (v0.12.1) | Added §4 (verified lay-term paraphrase examples) from INF3006Y successful H pass. Five transformation entries + one keep-as-is example + five provisional generalisation notes (including the H-motivated em-dash insertion / semicolon-substitution rule cross-referenced from `DETERMINISTIC_CHECKS.md §3`). Feeds `aggregate_h_calibration.py` corpus. |
| 1.1.1 | 2026-04-28 (v0.12.3, post-Reconciled audit) | Verification pass on §4 note 5's "INF3006Y Reconciled baseline: zero em-dashes" claim. Audit found 8 em-dash occurrences across 5 lines (61, 168, 178, 187, 189) at the time of the standalone H verification run; substitutions applied (3 specification-colons, 1 semicolon, 2 parenthetical-pairs) preserving M4 credit at zero §3 cost. The §4 note 5 claim is now byte-accurate. Procedure documented for replication on next-project H-CLEAN baseline assertions: assert claim, then verify-by-grep, then patch on drift. No new corpus entries; no schema change. |
| 1.2 | 2026-04-28 (v0.12.3, post-locator-round) | §4 paraphrase corpus **retired** following discovery that the source manuscript (INF3006Y Reconciled.md) was treated as a live working file by the project owner; three further refinement passes on 2026-04-28 rewrote the §1 framing paragraph that supplied the corpus entries. Three of five accepted-paraphrase rows now have no current-manuscript counterpart; two have modified counterparts (truncated). Corpus preserved as historical record under explicit "RETIRED" status banner. Two policy lessons added under "Lessons for corpus authoring": source-snapshot stability requirement (only Ph4-closed-and-acknowledged-final, venue-accepted, or `references/examples/`-committed snapshots qualify); drift-detection cadence (grep source phrases at next H-cycle, mandatory). The em-dash baseline claim in §4 note 5 ("INF3006Y Reconciled baseline: zero em-dashes") **remains byte-accurate** post-retirement — the Sub-pass-2 locator round of 2026-04-28 introduced no em-dashes; em-dash count = 0 verified by grep. |

**Note.** This file is the canonical lexicon source; cross-references in `references/DETERMINISTIC_CHECKS.md §9e`, `skills/accessibility-overlay/references/sub_checks.md §H`, and `references/SAFEGUARD_LAYER.md §H` should resolve here rather than re-state the lists in prose. Single-source-of-truth discipline per architecture §6.0 row 4.
