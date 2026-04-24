# STYLE COMMITMENTS — Declared Methodological Position

**Purpose.** This file makes explicit a fact that the package's tone has elsewhere left implicit: the prose-craft, narrative, and theoretical-shape rules carried by `bacon_2009_well_crafted_sentence_guidelines.md`, `Sexton_Fiction_to_Academic_Writing_Guide.md`, `baird_2021_writing_guidelines.md`, and the Suchman-inflected register favoured throughout `MASTER_research_and_paper_guidelines.md` are **methodological commitments**, not universal hygiene. They reflect a stance the author has taken about what good academic writing looks like in this research program. They are *defensible*, but they are not *neutral*; treating them as neutral would conceal an argument and pre-empt legitimate disagreement from venues, reviewers, or co-authors who hold different positions.

**Status.** Read by the Planner at classification time, by the Generator before any prose-shaping action, and by the Reflector when assessing whether voice drift is a *violation* (against a declared commitment) or a *legitimate variation* (the commitment itself is what's contested). Cross-referenced from `.paper-package/CLAUDE.md` §3 and from MASTER §A.

---

## 1. The four commitments

| # | Commitment | Source(s) | What it commits us to | What it commits us against |
|---|---|---|---|---|
| **C-1** | **Suchman-inflected register** | MASTER §A.4; tacit across the package | First-person navigation; concrete situated examples; theoretical claims tied to an empirical instance; resistance to disembodied abstraction | The "view from nowhere" register common in mainstream IS and ML venues; impersonal passive voice as default |
| **C-2** | **Bacon sentence craft** | `bacon_2009_well_crafted_sentence_guidelines.md` | Sentence-length variety; asymmetric rhythm; concrete anchors; foregrounding the verb; avoidance of glossary-stack openings | Prose that optimises for "readability score" alone; uniform sentence patterns; nominalisation-heavy abstract registers |
| **C-3** | **Sexton narrative arc** | `Sexton_Fiction_to_Academic_Writing_Guide.md` | A red thread traceable through the piece; show-then-tell openings; cause-and-effect structuring of argument; resolution that closes promises made in the abstract | Section-as-silo structure; "data dump then discussion" patterns; openings that begin with definitions or literature reviews |
| **C-4** | **Baird IS-theory shape** | `baird_2021_writing_guidelines.md` | Five-element model satisfaction (phenomenon → IT artefact → mechanism → outcome → contribution); explicit "draws on vs extends" framing; provenance for every named construct | Theory-borrowing without limitation acknowledgement; contribution-claim inflation; constructs deployed without traceable origin |
| **C-5** | **Reader-accessibility meta-rule** (new at v0.7.2) | Ph.D.-root CLAUDE.md §13 (Hard Constraint #8); `SAFEGUARD_LAYER.md` Check 8; `skills/accessibility-overlay/SKILL.md`; Sweller's cognitive-load taxonomy | Extraneous-load reduction on the prose surface without collapsing intrinsic load: paragraph cadence with turn-points, sentence-length variation, first-use definition for every construct, section-transition signposting, jargon discipline at or below the P-stage cap, worked examples at density spikes | Monotone-dense paragraphs that exceed 150 words with no turn-point; cold-open sections that dive into theory without orienting or contribution clauses; constructs deployed before definition; paragraphs that introduce more than two new domain terms; density spikes followed by further abstract prose rather than a vignette; **also prohibits the opposite failure — dilution that collapses intrinsic load or substitutes lay-register paraphrase for disciplinary vocabulary** |

These commitments are mutually reinforcing but *separable*. A piece can satisfy C-1 and C-2 while genuinely needing to violate C-3 (e.g., a methods note that is structurally a list, not an arc). C-5 is the **meta-rule that operationalises** C-1…C-4: it is binding at every P-stage and every tier rung (T2 onward), and it is the only commitment that cannot be suspended via the §4 relaxation procedure — accessibility is Hard Constraint #8 of the Ph.D.-root CLAUDE.md and inherits the binding force of §9 (non-negotiable rules). The Planner names which of C-1…C-4 apply to the current piece at classification time; the Generator and Evaluator hold the piece against *those* plus C-5 always.

---

## 2. Why declare them

Three reasons, in increasing order of importance:

1. **Falsifiability.** A rule that is never named cannot be challenged. Declaring the commitments lets a reviewer, co-author, or the author themselves contest a specific commitment without having to contest the whole harness.

2. **Venue alignment.** Some target venues (e.g., MISQ Theory & Review, JAIS) are friendly to C-1 and C-4. Others (e.g., NeurIPS, parts of CHI) are not. Pretending the commitments are neutral leads to wasted rounds where the harness drives the manuscript away from venue fit. With the commitments declared, the Planner can decide at classification time which to relax.

3. **Reflexive coherence.** The research program this package serves studies *how delegated AI agency reshapes professional identity in knowledge work*. A package that imposes its own aesthetic position on the author without naming the position would itself be an instance of the failure mode the program is theorising. Declaring the commitments is therefore not a courtesy; it is a coherence requirement (parallel to `DRIFT_CHECK.md` §6 and `REFLEXIVITY_CHECK.md` §6).

---

## 3. How the commitments interact with the pipeline

| Pipeline stage | Behaviour change |
|---|---|
| **Planner classification** | The Planner records, in the revision plan, which of C-1…C-4 apply to this piece. Default: all four for a research paper at standard or submission-bound depth; C-2 only for short response letters; C-3 + C-4 for a thesis chapter; selective for course essays. |
| **Generator prose actions** | The Generator may invoke a commitment by reference ("applying C-1: rewriting in first-person navigation"). It may not silently apply a commitment that the Planner did not record as applicable. |
| **Evaluator findings** | A finding that cites a commitment must name it (e.g., `[MAJOR — C-2: sentence rhythm]`). The author can then dispute the *commitment* rather than only the *finding*. |
| **Reflector — voice audit** | When the voice audit (`SAFEGUARD_LAYER.md` Check 6) flags drift, the Reflector decides whether the drift is *toward the commitments* (a fix), *away from the commitments* (a regression), or *across the commitments themselves* (a contested point — surface to user). |
| **Reflector — accessibility recurrence audit** (new at v0.7.2) | Phase 2g of `agents/reflector.md` aggregates Check 8 (C-5) findings across rounds and across projects. Within-project recurrence becomes a project-scoped lesson candidate; cross-project recurrence becomes a plugin-update proposal filed through the Planner's three-filter gatekeeper. C-5 is also the one commitment whose audit produces structured findings directly consumable by the Planner's §3.3.3 TerminalSignoffRow accessibility gate. Phase 2g is the topical-audit slot between Phase 2f (tier-row contract) and Phase 2.5 (grounding audit); it is distinct from Phase 2.7 (reflexivity audit, `REFLEXIVITY_CHECK.md`). |

---

## 4. Relaxation procedure

Any commitment can be relaxed for a given project, paper type, or section, by:

1. The user issuing an explicit relaxation in `research_notes/directives.md` (e.g., `D-09: For the §4 methods of project X, suspend C-3 (narrative arc) — the section is intentionally a structured list per venue convention.`).
2. The Planner recording the suspension at the top of the revision plan.
3. The Evaluator and Generator treating the suspended commitment as not-applicable for the scoped portion of the piece. Other commitments remain in force.

Relaxation is a normal operation, not an exception. The commitments are positions, not laws — **with the exception of C-5**. C-5 (reader-accessibility) is the meta-rule that operationalises C-1…C-4; it is bound to Hard Constraint #8 of the Ph.D.-root CLAUDE.md and to the absolute binding force of that file's §9. C-5 cannot be suspended by directive, by venue convention, or by P-stage. A project that legitimately needs a denser register (e.g., a formal proofs section) may reduce the severity floor of specific C-5 Sub-checks via a project-scoped override recorded in `directives.md`, but may not disable C-5 wholesale.

---

## 5. What this prohibits

- **Tacit imposition.** The Generator may not apply prose patterns drawn from C-1…C-4 to a piece for which the Planner has not recorded the commitment as applicable.
- **Performative neutrality.** The Evaluator may not flag a violation of C-1…C-4 with language that implies the rule is neutral hygiene (e.g., "the prose is bad" rather than "C-2 sentence-rhythm violation"). The commitment must be named so the author can dispute it.
- **Cross-commitment over-claim.** A finding tied to one commitment may not be presented as evidence for the others. C-1 and C-3 are independent stances; satisfying one does not satisfy the other.

---

## 6. Open questions (unresolved at 2026-04-13)

These are recorded so future rounds know what is *not yet decided* about the commitments themselves:

- **C-1 in adversarial venues.** The Suchman register costs us with reviewers who read it as un-rigorous or essayistic. Should C-1 be downgraded to "preferred but suspendable" for top-tier ML venues even when the paper's content is identity-RE?
- **C-4 in non-IS publications.** The Baird shape is calibrated to IS venues. For an HCI or CSCW submission, does the five-element model still apply, or does CSCW's contribution structure (situated study → analytic move → implication) substitute?
- **Internal tension between C-2 and C-3.** Bacon's sentence-level rules sometimes pull against Sexton's arc-level rules (e.g., a Sexton-mandated cause-effect bridge may require a sentence pattern Bacon flags as monotonous). When they conflict, which wins? Currently undecided; surface to user when encountered.

The Reflector should propose updates to this section as evidence accumulates.

---

*Created 2026-04-13 as part of the package-tightening pass. Addresses recommendation #6 of `wiki/syntheses/paper-package-evaluation-2026-04-13.md` — the implicit-stance-as-universal-hygiene gap.*
