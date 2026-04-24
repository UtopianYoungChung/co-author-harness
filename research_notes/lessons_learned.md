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

*End of package-level lessons. This file is maintained by the Reflector and updated after every cross-project insight.*

*Last updated: 2026-04-13.*
