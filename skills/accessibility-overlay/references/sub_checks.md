# Sub-checks A–H — judgment procedures

**Machine policy routing.** Load `references/policies/reader_accessibility.v1.json` through `scripts/reader_accessibility_policy.py`. The profile is the sole machine-readable authority for thresholds, floors, transition meanings, recurrence, and runtime-mode behavior. This file owns the human judgment procedure: it explains what evidence means without restating numeric policy.

Every finding carries identity, A–H member, constrained severity, independence group, locator, package-local rule citation, evidence, and suggested fix. Lexicon and deterministic probe hits are candidates only; the overlay supplies the functional verdict.

## Sub-check A — Paragraph cadence (Cadence-Flag)

Apply `thresholds.cadence`. Cue matches nominate possible turn points; functional confirmation credits one only when it actually performs a transition, counter-move, worked example, or thematic refocus. Sub-check B, not A, protects C-8/M-4 demonstrative anaphora and C-8/M-5 cadential verdicts from false rhythm findings.

> *Model examples → `references/examples/model_prose_corpus.md §Sub-check A`*

## Sub-check B — Sentence-length distribution (Rhythm-Flag)

Compute paragraph sentence-length distribution and apply `thresholds.rhythm`. The candidate remains a rhythm judgment: contrast and functional sentence shape matter more than a raw average. Read severity from `sub_checks.B`.

> *Model examples → `references/examples/model_prose_corpus.md §Sub-check B`*

## Sub-check C — First-use definition (First-Use-Flag)

Enumerate theoretical and domain constructs introduced in the section. A construct is an italicized term, a project-glossary entry, or a registered term. At first use, inspect the window owned by `thresholds.first_use` for a definition or worked illustration. Field familiarity does not excuse a construct that performs later conceptual work. Read severity from `sub_checks.C`.

> *Model examples → `references/examples/model_prose_corpus.md §Sub-check C`*

## Sub-check D — Section-transition signposting (Signpost-Flag)

At each heading, inspect only that section's opening, bounded at the next heading. Apply `thresholds.section_signpost` to the opening sentence window. Judge whether the opening contains both an orienting clause, which locates the reader in the argument, and a contribution clause, which says what follows. A cold open or either missing function is a candidate. Read severity from `sub_checks.D`.

Register quality inside either clause belongs to H; D checks structural presence. The checks remain orthogonal.

> *Model examples → `references/examples/model_prose_corpus.md §Sub-check D`*

## Sub-check E — Jargon discipline (Jargon-Density-Flag)

Track domain terms in introduction order and apply the resolved P-stage entry in `thresholds.jargon.new_domain_terms_per_paragraph`. A term is new only until its registered introduction. Read severity from `sub_checks.E`.

> *Model examples → `references/examples/model_prose_corpus.md §Sub-check E`*

## Sub-check F — Worked examples at density spikes (Worked-Example-Flag)

Nominate decompositions, multi-criteria evaluations, contested-claim clusters, rhetorical-question stacks, and extended theoretical derivations using `thresholds.worked_example`. The Evaluator then judges whether an example, vignette, or concrete instantiation actually carries the conceptual load. Read severity from `sub_checks.F`.

> *Model examples → `references/examples/model_prose_corpus.md §Sub-check F`*

## Sub-check G — Cumulative cognitive load (Consolidation-Anchor-Flag)

G runs only at full-manuscript scope. Enumerate structural boundaries and load-bearing constructs, positions, or tensions accumulated between them. Apply the construct, dependency, and proxy-envelope predicates in `thresholds.consolidation`. Deterministic word-and-cue gaps nominate boundaries only; they do not prove construct accumulation.

At a nominated boundary, judge whether adjacent prose names the accumulated material and signals the next move. Emit a structural-boundary locator and insertion guidance when that consolidation function is absent. D and G are additive: a local signpost can be present while the cumulative anchor is missing.

Read G's transition meaning from `transitions.G` and live state only from `phase_state.json.milestone_framework.policy_bindings.reader_accessibility.transitions.G`. Under stability, load `runtime_modes.stability`; byte reuse creates no independent advisory flag, membership exclusion, severity rewrite, or escalation exception.

> *Model examples → `references/examples/model_prose_corpus.md §Sub-check G`*

## Sub-check H — Register appropriateness (Register-Flag)

Resolve passage roles from the profile-owned `passage_roles` set and audience scope from `register_scope` plus the project's `register_class`. D, F, and G nominate structural passages; H judges register construction within them. Do not describe the role set by a hand-maintained count.

For each eligible passage, perform the functional-removability test in `thresholds.register`: substitute plain glosses for domain tokens and ask whether the proposition survives. If it does, the passage is eligible for the accessibility register audit. If it does not, technical density remains governed by E.

Always audit positive construction. Look for concrete anchoring, identifiable agent–verb–object clauses, transparent connectives loaded from the resolved lexicons, and explicit cues when register shifts. Also inspect the profile-driven negative probes for unnecessary nominalisation, stacked prepositional phrases, and hedge accumulation. A clear negative prefilter saves elaboration cost only; it never supplies a CLEAN verdict or suppresses the positive-marker audit.

For section signposts, keep orienting and contribution clauses distinct. The orienting clause locates the reader; the contribution clause states the section's action. A token may nominate either role, but grammatical function decides the verdict. For transitions, require a local cue span; prose merely appearing before the next heading is not automatically a transition role. TeX comments are excluded before role nomination.

When a finding closes around a cited shibboleth phrase, a deterministic twin grep may nominate structurally parallel passages. A hit is a review candidate, not a classification. Load all thresholds and severity behavior from `thresholds.register`, role overrides from `sub_checks.H`, and live transition state from the policy-binding Planner event projection.

Under stability, apply `runtime_modes.stability`. Stability may reuse bound evidence but does not change H severity, aggregate membership, or transition authority.

> *Model examples → `references/examples/model_prose_corpus.md §Sub-check H`*
