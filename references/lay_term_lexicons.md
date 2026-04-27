# Lay-term lexicons

**Purpose.** Canonical reference file for the lexicons consumed by SAFEGUARD Check 8 Sub-check H (Register Appropriateness) and `DETERMINISTIC_CHECKS.md §9e` (H pre-filter). The lexicons live here as a versioned, structured artefact rather than embedded in prose so future revisions can be tracked, per-entry rationale captured, and per-project override semantics implemented cleanly when v0.10.3 ships the override mechanism.

**Status (2026-04-27).** v0.10.2 introduces this file as the canonical home for three lexicons: the hedge list, the discourse-connective list, and the load-bearing-Latinate whitelist. Per-project override is documented but **not implemented** at v0.10.2 per Q4 adjudication 2026-04-27 (defer to v0.10.3).

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

## Versioning

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-04-27 (v0.10.2) | Initial extraction from prose-embedded lists in §9e, sub_checks.md, and READER_ACCESSIBILITY.md. Three lexicons (hedge / connective / domain-term) consolidated. Six-entry load-bearing-Latinate whitelist added (closure rule defined). Per-project override semantics documented; implementation deferred to v0.10.3 per Q4 adjudication 2026-04-27. |

**Note.** This file is the canonical lexicon source; cross-references in `references/DETERMINISTIC_CHECKS.md §9e`, `skills/accessibility-overlay/references/sub_checks.md §H`, and `references/SAFEGUARD_LAYER.md §H` should resolve here rather than re-state the lists in prose. Single-source-of-truth discipline per architecture §6.0 row 4.
