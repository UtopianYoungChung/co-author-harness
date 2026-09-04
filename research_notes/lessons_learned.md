# Package-Level Lessons Learned

**Purpose.** Cross-project patterns extracted from review rounds and root cause analyses. These lessons inform package improvements and are binding on all projects using this package.

**Scope.** These lessons apply to all research projects in the Faculty of Information at submission-bound depth or higher. Project-specific lessons live in each project's `research_notes/lessons_learned.md`.

---

## L-P1: External Review Addresses Argumentative Rigor; Internal Pipeline Addresses Consistency

**Source.** Root cause analysis of INF3001H, 2026-04-13. Five logical gaps persisted through 8 internal review rounds and external review (1 pass) caught them all.

**The lesson.**

Internal review (automated pipeline + deterministic checks + safeguard layer) is optimized to catch:
- Mechanical errors (spelling, formatting, reference formatting)
- Voice/style regressions (register shifts, jargon drift, passive-voice creep)
- Logical inconsistency at sentence and paragraph level (contradictions, non-sequiturs)
- Edit traceability (what changed, whether cited rules support the change)

External review by a subject-matter expert catches:
- Argumentative rigor (are claims *demonstrated* or merely *asserted*?)
- Completeness (do the paper's premises create logical consequences that are left unresolved?)
- Epistemological transparency (do illustrations do evidence work? are frameworks justified when transferred?)
- Differentiation (does the paper sufficiently distinguish its argument from alternatives?)

**Why it matters.** A manuscript can be *well-formed* (passes all internal checks) while being *unconvincing* (fails external scrutiny). Neither review alone is sufficient. They are orthogonal.

**How to apply.** 
- Do not expect internal review to catch argumentative gaps — it is not designed for it.
- Do not skip external review under the assumption that internal review is sufficient.
- At submission-bound depth, require both internal and external review before accepting a manuscript as ready.
- Use the M1–M3 argumentative rigor checklist to move some external-review-type checks into the planning phase, reducing rework at M4–M5.

**Promotion.** This lesson has been operationalized in:
- AGENT_ORCHESTRATION.md §10 (M1–M3 criteria expanded)
- M1_M2_M3_ARGUMENTATIVE_RIGOR_CHECKLIST.md (planning-phase guidance)

---

## L-P2: Disciplinary Placement Claims Require Named Exemplars

**Source.** Root cause analysis of INF3001H, 2026-04-13. Gap 1: "Information is the right home" claim was asserted without naming existing research programs that perform the claimed integration.

**The lesson.**

When a paper argues "Problem X belongs in Discipline Y," support the claim by naming 2–4 *existing research programs* (not individual papers) that already perform the integration the paper claims is central to Discipline Y.

**What counts as an exemplar.**
- A named scholar or research group with a sustained body of work
- Citation to representative papers that show the scholar/group actually does the integration
- Brief description of *what* they integrate (not just "Orlikowski studies materiality," but "Orlikowski's sociomaterial practices research combines organizational ethnography with technical artifact analysis")

**What does NOT count.**
- Listing papers that address one component of the integration (e.g., "STS studies technology" or "organizational studies study organizations")
- Asserting that a discipline "could" do the integration (aspirational language)
- Citing individual papers without situating them in a research program

**Why it matters.** The claim "Discipline X is the home for this problem" is a meta-theoretical claim about the discipline itself. It requires empirical grounding: evidence that the discipline actually does what you claim. Named exemplars provide that grounding.

**How to apply.**
- At M1 planning phase, when a disciplinary placement claim emerges, identify 2–4 research programs that exemplify the integration (M1_M2_M3_ARGUMENTATIVE_RIGOR_CHECKLIST.md §M1, Check 1a).
- In M2 annotated references, cite those programs with annotations that specify their integration pattern.
- In M3 outline, ensure the disciplinary placement section references those exemplars.
- In M4 draft, introduce the exemplars early (§1 or §2) so the placement claim has immediate grounding.

**Scope.** This lesson applies to any paper making a disciplinary or sub-disciplinary placement argument (e.g., "This is an HCI issue," "This belongs in information science," "This is a requirements engineering problem").

---

## L-P3: Unresolved Logical Tensions Become Reviewer Questions

**Source.** Root cause analysis of INF3001H, 2026-04-13. Gap 2: Premises (actors are provisional; we model actors) were individually consistent but created an unresolved downstream question: "If actors are that fluid, what does the model capture?"

**The lesson.**

When a paper holds two or more premises simultaneously, check whether they create a logical consequence the paper doesn't resolve. If they do, external reviewers will notice.

**What counts as a tension.**
- Two premises that are individually true but create a downstream question when combined
- Example: A + B → (question Q that the paper doesn't answer)

**Distinction from contradiction.**
- Contradiction: A and NOT-A (both explicitly stated, directly incompatible)
- Tension: A and B → unresolved Q (both individually sound, but their combination requires addressing Q)

**Why it matters.** A contradiction is a fatal error. A tension is a live question: the paper can resolve it, or explicitly scope it out. But leaving it unaddressed makes reviewers question whether the author thought through the implications.

**How to apply.**
- At M1 planning phase, identify potential tensions between premises (M1_M2_M3_ARGUMENTATIVE_RIGOR_CHECKLIST.md §M1, Check 1b).
- For each tension, decide: Will this paper resolve it? Will this paper defer it (scope it out) as future work? If neither, it's a gap.
- In M3 outline, show where the resolution happens (or where the scope boundary is clearly marked).
- In M4 draft, when you state both premises, immediately address the tension they create.

**Scope.** This applies to all research that introduces multiple theoretical frameworks or premises. Common sites of tension: "actors are X yet we model them as Y," "the system is organic yet we treat it as designed," "data represents reality yet it's constructed."

---

## L-P4: Compound Claims Require Conjunct-Level Citation Verification

**Source.** Citation verification of INF3001H §1 ¶5 (bibliography of *Labor and Monopoly Capital*), 2026-04-13. The sentence "which are deemed tractable to system design and which are rendered invisible or exceptional (Braverman, 1974)" attached a single Braverman citation to a compound claim. Braverman's deskilling thesis supports the first conjunct (tractability/formalization of craft knowledge for managerial control) but does not advance an invisibility thesis; the canonical source for invisibility of work is Star \& Strauss (1999), *Layers of Silence, Arenas of Voice*. The citation passed the existing GROUNDING_PROTOCOL citation audit because (a) the source exists, (b) it was read, and (c) the first attributed claim was present. The second conjunct failed silently.

**The lesson.**

A citation placed at the end of a compound sentence implicitly claims that the cited source supports *every conjunct* in that sentence. Standard citation audits check whether the *sentence* is attributable to the source, but "attributable" is ambiguous when the sentence contains multiple claims. The correct question is: does the source support conjunct 1 AND conjunct 2 AND ... AND conjunct n?

**Failure patterns to watch for.**

- **Extended attribution**: A classic source (Braverman, Marx, Weber, Taylor) is cited for a claim its framework covers, and the sentence silently extends into adjacent territory the source does not theorize. The reader's familiarity with the classic fills the gap.
- **Halo transfer**: A modern concept (algorithmic accountability, articulation work, situated cognition, sociomateriality) is attached to an author whose framework is adjacent but not identical. The halo of the author lends credibility to claims the author did not make.
- **Genre smoothing**: An empirical-study citation is attached to a theoretical claim the study does not make (or vice versa). The citation is real; the attribution is the wrong *kind*.
- **Canonical conflation**: Two distinct scholarly lineages that travel together in practice (deskilling + invisibility; Foucault + Bourdieu; Suchman + Star) are compressed under one citation. Each lineage needs its own source.

**Why internal review misses this.** The existing citation audit checks existence, readability, and presence-of-attributed-claim. When the attributed claim is compound, the audit can pass if the source supports the most prominent conjunct. The reviewer's own background knowledge fills in the rest. This is the bootstrapping paradox at the sentence level: the reader's priors do the work of verification.

**How to apply.**

- During M4/M5 review, parse every cited sentence for compound claims (look for "and," "or," lists, parallel structures inside the sentence terminated by the citation).
- For each conjunct, ask: is this specifically what the cited source argues? If you cannot point to a passage in the source that supports *this conjunct*, the citation is under-extended.
- Remediation options: (a) split the citation so each conjunct is supported by its own source; (b) narrow the claim to the portion the source actually supports; (c) replace the citation with one that covers the full compound claim.
- At submission-bound depth, the Reflector must run a dedicated "conjunct-level attribution pass" on compound sentences containing citations. See GROUNDING_PROTOCOL.md §Audit Procedure, Rule 1, "Conjunct-level attribution check."

**Scope.** This applies to all manuscripts at M4 and above. It is especially important for papers that cite classic texts alongside modern ones, because classic texts are most likely to be extended silently beyond what they argue.

**Promotion.** This lesson has been operationalized in:
- GROUNDING_PROTOCOL.md §Audit Procedure, Rule 1 (Conjunct-level attribution check added 2026-04-13)
- DETERMINISTIC_CHECKS.md (recommended addition: regex pattern for compound-sentence citation detection — see §Recommended deterministic additions)

---

## L-P5: Route an External Source to the Layer Whose Contract It Extends, Not Uniformly to a Prose Pass

**Source.** Three-manuals integration (Turabian, Abbott *Digital Paper*, Blue Book), 2026-06-28, landed as v0.17.0. Reflection report: `reviews/reflection_report_2026-06-28_three-manuals.md`. Plan: `docs/superpowers/plans/2026-06-28-three-manuals-integration.md`.

**The lesson.**

The harness's five prior source absorptions (Bacon, Sexton, Baird, Suchman, Eubanks) were all prose-craft passes, which implicitly trained the pattern "external source → invocable prose pass + `references/<source>_guidelines.md`." Three new manuals falsified the generality of that pattern. Each belonged in a *different* substrate, and treating them uniformly as prose passes would have mis-filed two of the three:

- **Blue Book** (grammar/punctuation correctness) → the *mechanical/deterministic* layer (`DETERMINISTIC_CHECKS.md §3b` work queue) plus a judgment skill — not a rhetoric pass.
- **Turabian** (citation *form*) → the *citation* layer, orthogonal to `CITATION_DISCIPLINE.md`'s *whether-to-cite* judgment.
- **Abbott** (research *process*) → the *Planner/discovery* layer as a read-surface with **no skill at all** — process guidance is not a prose operation.

**How to apply.**

- Before absorbing a source, ask **which existing contract it extends** (mechanical-deterministic, citation-form, citation-judgment, sentence-craft, narrative-structure, research-process, accessibility), and wire it there. The `references/<source>_guidelines.md` read-surface is universal; the *operation-surface* (skill / SAFEGUARD hook / agent invariant / no-op) is chosen per layer.
- A source becomes an invocable skill **only** where it licenses a recurring, decidable operation. Process and read-only guidance stays a read-surface (Abbott: no skill), matching the precedent that overlay-internal checks need no `SKILL_REGISTRY` entry.
- When two absorbed sources legislate the same decidable item (Blue Book ↔ Turabian Part III mechanics), declare **one authority per item** via project-declared precedence and emit `[CONFLICT]` rather than silently choosing — the discipline-coherence rationale of `CITATION_DISCIPLINE.md §3`, generalized from citations to mechanics.

**Scope.** Applies to every future external-source absorption. Especially load-bearing when the source is a *manual* (process/format/mechanics) rather than a *style essay*, because manuals most often extend a non-prose contract.

**Promotion.** Operationalized this round in: `references/blue_book_grammar_guidelines.md §6`, `references/turabian_chicago_guidelines.md §5`, `references/abbott_2014_research_process_guidelines.md §4/§6`, `DETERMINISTIC_CHECKS.md §3b`, `AGENT_CONTRACTS.md I-Gen-9`.

---

## L-P6: A `style_lint` PASS Is Not a C-6 Pass — Hand-Edits Bypass the Only Layer That Enforces C-6

**Source.** Workspace/process root-cause analysis, 2026-07-03. Diagnosis note: `B:/Agents/reference/c6-gap-analysis-and-mitigation.md`. Recurring failure: two load-bearing vocabularies ("reciprocity", "ratifies", following an earlier "answerability leaks") entered live QE2026 prose and slipped past both D-STYLE and this harness.

**Scope.** Workspace/process lesson (D-STYLE `B:/Agents/reference/` + hand-edit workflow). The harness C-6 policy itself (`STYLE_COMMITMENTS.md §1.0a`) is correct and unchanged; the gap is in *when* it gets invoked. Recorded here because the invocation-timing failure mode is not project-specific and a cross-project deterministic backstop is proposed separately (see `reviews/plugin_update_proposals.md` P-R-6 / A10).

**The lesson.**

C-6 (rhetorical-vs-analytical separation and scoped metaphor, `STYLE_COMMITMENTS.md §1.0a`) is a **judgment** commitment, owned by the Generator at write-time and the Evaluator at review-time. No deterministic script enforces it: `DETERMINISTIC_CHECKS.md` measures jargon density and glossary-dump form, not term-definedness, single-sense use, or loaded/unscoped metaphor. The workspace's own mechanical gate, `style_lint.py`, was likewise structurally blind to C-6 (it checked em-dash density, long sentences, agented passive, nominalization, hedges — never term-definedness or metaphor scope).

The two misses entered through **direct hand-edits made after the last Generator and Evaluator passes**, in response to review comments, gated only by the mechanical lint. Because the one place C-6 lives is the Generator/Evaluator judgment, and that judgment was never invoked on those spans, the commitment could not fire. When the harness *was* invoked it worked — the Evaluator caught an undefined "standing" at an earlier version. The failure is specific to hand-edits gated only by a mechanical lint.

**The standing rule.**

A `style_lint.py` PASS is **not** sufficient for C-6. A prose edit that introduces or changes a load-bearing term or a metaphor is not complete on a mechanical PASS alone; it must receive a C-6 judgment pass on the changed span — route through the Generator, or run a targeted C-6 pass (`analytic-move-audit` / `definition-derivation-check`, or a local Evaluator pass). Trigger: an edit that adds an abstract noun or a figurative verb is C-6-checked. This process rule is primary; tooling is a backstop, not a substitute.

**How to apply.**

- Treat any hand-edit that adds/changes a load-bearing term or metaphor as C-6-triggering, regardless of whether it was made in response to review comments.
- Do not close such an edit on a mechanical-lint PASS; obtain a Generator or targeted-audit C-6 judgment on the changed span first.
- Workspace tooling now added (Layers 2–4, all in `B:/Agents/reference/`, primary rule is Layer 1 behavior): `style_lint.py` reads `c6_watchlist.txt` and emits a REVIEW per watchlisted evocative/loaded term or unscoped metaphor (forces a look, does not adjudicate); `terminology_register.md` holds approved load-bearing terms with their single agreed sense plus preferred plain replacements; the Layer-1 rule is registered in the "C-6 enforcement" section of `d-style-research-architecture.md`.
- Known limit: the tripwire is heuristic — it flags only watchlisted terms and will miss a novel loaded term, so the judgment rule remains primary.

**Promotion.** Operationalized in the workspace (`B:/Agents/reference/style_lint.py`, `c6_watchlist.txt`, `terminology_register.md`, `d-style-research-architecture.md`). A cross-project deterministic tripwire in the harness is proposed as an advisory, gatekept item (see `reviews/plugin_update_proposals.md` P-R-6 / A10); no active harness check was modified.

---

## L-P7: A Definition Is Not an Introduction, and Precision Outranks Vividness

**Source.** QE2026 First-Principles RE Essay Ph4 precision pass, 2026-07-12; landed as v0.26.0. The pass surfaced two defects that had cleared earlier clarity and predication review: (1) "The field's working unit is the *actor*" — a load-bearing construct arriving by fluent definition with no derivation from the *parties* introduced before it (the L21 failure), and (2) a hospital that "wants patient safety" — an anthropomorphic predication whose implication the next clause had to retract.

**The lesson.**

A sentence can define a term fluently, focus a concrete subject grammatically, and still fail on two axes the existing sentence-craft checks did not test: the *provenance* of a construct and the *truthful bearer* of a predicate.

- **Introduction ≠ definition.** Every newly introduced analytical term, category, unit, or field-level generalization must be *derived* from a preceding problem, entity, distinction, or modelling operation. A definition supplies the meaning; it does not supply the reason the construct appears here, now, connected to what came before. When the derivation is missing, a fluent definition reads as clean prose while leaving the reader asking "Where did that come from?"
- **Precision outranks vividness.** An image, analogy, or example earns its space only if it lowers the reader's inferential burden *without* temporarily misstating the claim. A figurative phrase that creates a misleading implication — an ascription/representation/model predicated of the world-level entity itself — is a finding *even when a following clause successfully repairs it*. The repair is evidence the debt was incurred.

**Failure patterns to watch for.**

- **Definition-as-introduction**: a term is defined but never derived; the fluency masks the missing bridge.
- **Scope overclaim without derivation**: a field-wide formulation ("the field's working unit is X") asserted as harmless style, carrying unsupported scope plus a missing derivation — MAJOR, not a stylistic nicety.
- **World/model level conflation**: predicating of a world-level *party* what is true only of the *actor* constructed to represent it, or vice versa (bearer-test failure). Keep the levels explicit: *party* is world-level; *actor* is constructed in a model; *agent* names a world-level role occupant.
- **Conceptual debt / repair-after-image**: an anthropomorphism or metaphor whose implication the surrounding prose must disclaim.

**How to apply.**

- At Step 4, run the **concept-introduction priority gate** *before* ordinary craft checks: apply the introduction-provenance, derivation-continuity, scope-authority, and reader-reconstruction tests to each new construct. A frame-changing failure is **MAJOR**.
- On every definitional, modelling, or ontological sentence, run **semantic-predication integrity (Check 10)**: bearer, contrast-set, domain-collocation, transformation-continuity, and conceptual-debt tests. Do not clear a sentence because its subject is concrete or well focused; a claim-changing bearer or conceptual-debt failure is **MAJOR**.
- Do not accept a disclaimer or later repair as a cure for a misleading image — state the distinction directly and remove the device.

**Scope.** Applies to all manuscripts reviewed at sentence-craft depth or higher, and is especially load-bearing for theory-building and modelling prose that introduces analytical vocabulary (agent/actor/party, goal/softgoal, and similar) where a fluent definition most easily substitutes for a derivation. Complements L-P6: L-P6 governs *when* the C-6 judgment fires on hand-edits; L-P7 governs *what* two of those judgments now test.

**Promotion.** Operationalized this cycle in: `references/bacon_2009_well_crafted_sentence_guidelines.md §§3.6–3.7`, `skills/sentence-level-pass/SKILL.md` (→ v1.4: priority-gate section + Check 10), `agents/evaluator.md` (both gates mandatory at every applicable review depth, Step 4), `references/REVIEW_ORCHESTRATION.md` (Step 4 routing + overlap map), and `references/project_writing_style_checklist.md` (Part 3). Regression-pinned by `scripts/concept_introduction_contract_smoketest.py` and `scripts/semantic_predication_contract_smoketest.py`, both enforced by `scripts/release-gate.sh`.

---

## L-P8: Five Enforcement Measures Are the Umbrella; C-n Instruments Sit Under Them

**Source.** Paper 2 v4 abstract calibration, 2026-08-31 through 2026-09-01; folded into the harness on Joseph's 2026-09-01 instruction after a verifier pass on the preview abstract. This entry is a package-level fold directed in conversation, not a Ph4 Reflector close-out. No manuscript bytes were changed.

**The lesson.**

The measures that distinguished the accepted-as-best abstract from prior drafts are the core guideline for the rest of the manuscript and for later papers. Everything else the harness already carries — C-1…C-8, Check 8, MASTER A.4.2, Bacon, Sexton, Baird — remains, and is classified under these five:

1. **Vocabulary audit.** Every technical term traces to a source byte or the professor's transcript; else earn it or drop it. Zero invented vocabulary.
2. **Novelty shape.** Name the prior practice before the strain ("X has always been done; this paper puts X under strain where Y").
3. **Ordering.** Familiar situation → felt gap → concrete case → contribution name. Project vocabulary must not appear before its referent.
4. **Gap-before-claim.** Each exclusion or finding is preceded by the gap it closes.
5. **One job per sentence.** The Ver03 choppiness report's A1–A5 are this rule's absence.

**Failure patterns to watch for.**

- Recording the five only in seat MEMORY.md or a writer skill, while the Evaluator and Generator still lead with C-n and Check 8.
- Numbering drift: a five-lesson commentary that folds EIBU into its own slot and leaves gap-before-claim implicit.
- Treating a C-n suspension as a suspension of the matching umbrella.
- Citing a stale preview hash as the live calibration object.

**How to apply.**

- Generator and Evaluator read `references/FIVE_ENFORCEMENT_MEASURES.md` before C-n craft and wording discussion.
- Findings name the umbrella (`U1`…`U5`) and may also name the C-n.
- Re-hash the calibration preview before citing it. As of 2026-09-01 the live file is `PREVIEW_paper2-v4_2026-08-31.md` at `a0fa9222…` / 42,504 B; seat notes that say `cde8ad63…` / 42,932 B are a prior identifier, not the live file.

**Scope.** Binding on all academic draft, revision, and evaluation work this package runs. Complements L-P7: L-P7 is the vocabulary/provenance test at sentence level; U1 is that test raised to the umbrella that other instruments serve.

**Promotion.** Operationalized in: `references/FIVE_ENFORCEMENT_MEASURES.md`; `references/MASTER_research_and_paper_guidelines.md` (A.0); `references/STYLE_COMMITMENTS.md` (purpose); `references/MANIFEST.md`; `agents/generator.md`, `agents/evaluator.md`, `agents/planner.md`.

---

*End of package-level lessons. This file is maintained by the Reflector and updated after every cross-project insight. L-P8 was appended under Joseph's 2026-09-01 fold instruction.*

*Last updated: 2026-09-01.*
