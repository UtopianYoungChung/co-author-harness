# The Move Before the Sentence: How Abbott Builds an Argument, and the Case for an Analytic-Construction Commitment (C-8)

**Author-facing analysis + patch rationale**
**Date:** 2026-07-01
**Scope:** Deep read of Andrew Abbott, *The System of Professions: An Essay on the Division of Expert Labor* (Chicago: University of Chicago Press, 1988), across the Preface, Chapter 1 (definitional argument), Chapter 3 (jurisdiction / social structure), and the concluding chapter (theory of professions, historical discourse). Audited against `references/STYLE_COMMITMENTS.md` (C-1…C-7), the prose-craft skills (`sentence-level-pass`, `narrative-structure-pass`, `IS-theory-pass`), and the D-STYLE profile check. Target package version: 0.19.0 → 0.20.0.

> **Grounding note.** Every quotation below was verified character-for-character against the uploaded full-text extract of Abbott 1988, not reconstructed from memory. Because the source is a re-flowed digital edition (calibre-produced) without stable pagination, locators are given at chapter granularity. This memo absorbs a **different Abbott** from the one already in the package: C-7 (`voice_preservation_guidelines.md`) absorbed *Methods of Discovery* and *Digital Paper* — Abbott advising on craft. This memo absorbs the 1988 monograph — Abbott performing it.

---

## 1. Problem statement

The harness's declared commitments partition academic prose into layers, and each layer has an owner. C-2 (Bacon) owns the clause. C-3 (Sexton) owns the whole-piece arc. C-4 (Baird) owns the theory's static anatomy — the five-element model (phenomenon → artefact → mechanism → outcome → contribution). C-1 (Suchman) and C-7 own register and voice. One layer has no owner: **the individual analytic move — the unit of prose in which a single claim is won.**

The distinction is not cosmetic. C-4 audits whether a theory *has* the right parts; it is silent on whether those parts were *earned*. A manuscript can satisfy the five-element model completely while stipulating every key term by fiat, contradicting rather than dissolving every rival, asserting every claim at flat confidence, and rejecting rival categories on abstraction where a concrete counterexample was available. Such a manuscript is C-4-complete and argumentatively hollow. Nothing in the pipeline detects the hollowness, because the layer at which it lives — between the sentence and the theory-shape — is unclaimed.

Worse, the vacancy is not neutral. As the C-7 analysis already established for idiolect, *an unowned feature does not stay unowned; it gets optimized away by whatever adjacent check is nearest.* The nearest checks to the analytic-move layer are the mechanical craft skills, and they mis-handle what they reach into it: `sentence-level-pass` reads a deliberate anaphoric demonstration ("Thus… Thus… Thus…") as a monotony defect, and reads a cadential verdict as a candidate for concision-deletion. The harness can therefore *degrade* an argument in the name of polishing its prose. This memo names the vacancy, shows what fills it well, and specifies **C-8, analytic-construction discipline**, to claim it.

---

## 2. Theoretical framework: what Abbott's monograph demonstrates

The deep read converges on a claim about *where* Abbott's power lives. It is not primarily at the sentence (his sentences are excellent but not his signature) nor at the arc (the book's macro-structure is conventional social science). It is at the **move** — the two-to-ten-sentence unit in which he establishes one thing. Seven such moves recur, and together they constitute a reusable rhetoric of theory construction. Each is a *convergent* target: something well-argued prose moves toward.

**M-1 — Definitional deferral.** Abbott refuses to define his central term until the theory demands it, then derives the definition rather than stipulating it: "Definitions, then, must follow from theoretical questions… My central questions and my framework thus determine my definition of profession" (ch. 1). The move matters because a stipulated definition smuggles the conclusion into the premises; a derived one shows its work and stays falsifiable. The reader watches *abstraction* become the criterion because the competitive theory needs it, not because a dictionary supplied it.

**M-2 — Reconstruct → locate buried assumption → dissolve by moving up a level.** Abbott's signature dialectical move states a rival charitably, names the single unexamined assumption it rests on, and dissolves the dispute by relocating it — "The underlying problem is that for many writers, calling something a profession makes it one" (ch. 1); "The contradiction between defining professions by their claims or by their functions is resolved by recalling that the importance of professional social structure lies in its effect on professions' abilities to maintain themselves within a competing system" (ch. 3). Head-on contradiction produces a standoff; dissolution shows the dispute was ill-posed. The charity is load-bearing — a strawman cannot be dissolved, only knocked over.

**M-3 — Counterexample as demolition.** Abbott breaks rival definitions with stubborn concrete cases: "English barristers do not necessarily train in university but rather by apprenticeship and eating dinners 'in hall.' American clergy do not generally have ethics codes… Yet both groups are unmistakably professions" (ch. 1). One well-chosen case does the work of a paragraph of abstract objection, irreversibly.

**M-4 — Accumulated parallel instances (anaphoric demonstration).** Abbott converts a generalization into a demonstrated pattern by listing instances in one grammatical frame: "Thus medicine defeated nursing in the hospital administration area. Thus psychiatry dominated social work and psychology in child guidance. Thus teaching has effectively resisted the efforts of computer scientists to take over classroom teaching" (ch. 3). The anaphora *is* the evidence; the repetition is structural, not monotonous.

**M-5 — The cadential verdict.** Abbott builds a long qualifying period and resolves it with a short declarative that lands the point: "To say a profession exists is to make it one" (ch. 3); "Abstraction enables survival in the competitive system of professions" (ch. 1). The verdict reads as a conclusion *because* it follows accumulated qualification — the rhythm does the persuading.

**M-6 — Calibrated confidence.** Abbott grades his confidence on the record: "I am much more confident about my interpretation of professionalism around 1900 than about my interpretation of professionalism now; in principle, the present situation is less knowable" (concl.); "I have followed what I see as functional reality in calling it a profession here" (ch. 3). Graded confidence is an authority move, not a hedge — naming exactly where he is unsure earns trust for what he asserts flat.

**M-7 — Meta-analytic reflexivity.** Abbott interrogates his own apparatus inside the argument that uses it: "We must also confront the arbitrary character of our central subjects… essence endures, qualities change. This strategy… must be unmasked" (concl.). Naming the arbitrariness of one's own categories, while still using them, pre-empts the reviewer's objection by making it first.

**The phenomenon-first opening ties M-1 to C-3.** The Preface opens on the Manteno State Hospital ward and lets the phenomenon raise the question: "'In an official sense. . . .' What is it to possess and control expertise?" The theory is *driven by* the phenomenon, not announced and then illustrated — the inverse of the definition-first cold open C-3 already warns against.

---

## 3. Methodology: how the architecture currently handles the analytic move — and where it leaks

The audit traced the analytic-move layer through the four commitments nearest to it (C-2, C-3, C-4, C-7) and the three craft skills. Three leaks and one reflexive gap emerged.

**Leak 1 — C-4 audits anatomy, not derivation.** Baird's five-element model checks that a theory names a phenomenon, an artefact, a mechanism, an outcome, and a contribution, each with provenance. It does not check that the *central construct* was derived rather than stipulated (M-1), nor that rivals were dissolved rather than contradicted (M-2). A manuscript can pass `IS-theory-pass` with every load-bearing term declared by fiat. M-1 and M-2 have no defender in the ladder.

**Leak 2 — the craft skills mis-read two argumentative features as defects.** `sentence-level-pass` (Bacon, C-2) flags "consecutive sentences of similar length" as monotony and treats a short declarative as a candidate for concision. Both fire on legitimate Abbott moves: M-4 demonstrative anaphora reads as monotony; an M-5 cadential verdict reads as a sentence to be merged into its period "for economy." The skills disclaim genre-mechanical overreach and (post-C-7) carry an *idiolect* carve-out, but they have **no argument-structure carve-out.** The pipeline can thus delete the load-bearing verdict while every word around it survives.

**Leak 3 — no owner for confidence calibration or reflexivity.** M-6 (graded confidence) is adjacent to C-1 (which owns the *register* of the "I") and to C-4's "contribution-claim inflation" note (which flags over-claiming at the theory level), but nothing owns the sentence-level discipline of grading confidence to evidence. M-7 (reflexivity) is adjacent to `REFLEXIVITY_CHECK.md` (which audits the *research program's* reflexive coherence) but nothing asks whether a given theory-building *passage* examines its own apparatus. Both moves are unowned.

**Reflexive gap — the harness cannot describe its own jurisdictional overlaps.** When `sentence-level-pass` and the analytic-move layer both reach for the same anaphora, the harness has no vocabulary for the dispute; it resolves everything by fixed precedence (the ladder), which recognizes only subordination. Abbott's substantive theory — the book is *about* how a division of expert labor allocates contested jurisdiction — supplies exactly the missing vocabulary (§6).

The D-STYLE profile check is **not** a leak: it is a routing/surface validator (argument, visual-evidence, assistance surfaces) and never judges the analytic move. C-8 sits alongside it, as C-7 does — D-STYLE routes *whether* argument surfaces are visible; C-8 judges *how well* the move on those surfaces is built.

---

## 4. Synthesis: the contribution — C-8, analytic-construction discipline

Abbott's monograph licenses a commitment with a shape the ladder was missing: a **convergent** commitment (like C-1…C-4) that owns the analytic-move layer, carrying **protective carve-outs** (like C-7) for the two moves the craft skills mis-read.

**C-8 in one line:** *A theory-building passage should earn its claims by the moves that win them — derive contested terms rather than stipulate them, dissolve rivals rather than contradict them, demolish with counterexamples, demonstrate with parallel instances, close on verdicts, grade confidence to evidence, and examine its own apparatus — and no craft rule may flatten a demonstrative anaphora or delete a cadential verdict absent an independent evidential or accessibility warrant.*

Five design decisions follow from the read:

1. **C-8 is convergent and suspendable (like C-1…C-4), not protective-by-default (unlike C-7).** It is a position, not a law — a systems or formal-methods venue may legitimately want flat assertion and stipulated definitions. It is recorded by the Planner at classification and relaxable via `directives.md`, with the added grain of **per-move suspension** (suspend M-1 alone for a venue that wants a definitions table).
2. **C-8 is P-stage-gated by construction.** M-1, M-2, and M-7 presuppose a research problem sharp enough to argue; firing them against a P0/P1 phenomenon-collection piece is itself a stage error. At P0/P1 only the stage-neutral moves (M-3, M-5, M-6) apply. This makes C-8 cohere with `p-stage-checker` rather than fight it, and prevents C-8 from pushing an early-stage paper to over-claim.
3. **C-8 gives the craft skills an argument-structure carve-out — the mirror of C-7's idiolect carve-out.** Before `sentence-level-pass` flags monotony on parallel-framed instances, or concision on a short declarative that resolves a period, it must check the argumentative function: demonstrative anaphora (M-4) and cadential verdicts (M-5) are protected, and a prior flag on them is *overturned*, recorded as a strength. The burden of proof sits on the rule that would strip the feature.
4. **C-8 inverts the burden of proof on argument-flattening rewrites.** As the Grounding Protocol forbids inventing content and C-7 forbids stripping voice on taste, C-8 forbids the Generator from deleting a verdict or flattening an anaphora on "concision" alone — the edit must cite an independent evidential or C-5 warrant. Abbott's own point (via *Digital Paper*, already in the package) generalizes: wording is the author's decision, and the burden is on the rule to justify overriding it.
5. **C-8 ships as one skill now, a set by design.** The full seven-move pass ships as SK-42 `analytic-move-audit`. Two narrower single-purpose skills are *designed but deferred* (recorded as open fronts): a `definition-derivation-check` (M-1 alone — a near-deterministic stipulated-vs-derived scan keyed on "we define / by X we mean" against a derivation cue) and a `dissolution-move-check` (M-2 charity + dissolution). They are held back until there is evidence the bundled pass under-serves them, per the harness's "commitment + skill-tuning first, new deterministic surface later" discipline.

The result is reflexively coherent in the sense `STYLE_COMMITMENTS.md §2.3` demands: a harness that studies expert labor now audits whether its *own* prose builds its claims by the moves that win them, and stops its craft skills from sanding those moves away.

---

## 5. The patch set (companion to this analysis)

Landed against v0.19.0 → v0.20.0, additive, no breaking change to C-1…C-7:

| Artefact | Change | Type |
|---|---|---|
| `references/analytic_construction_guidelines.md` | **New** substrate grounding C-8 in Abbott 1988 (M-1…M-7 with verified quotes + operational tests, P-stage gating, carve-outs, §6 reflexive coda). Follows the source-absorption pattern. | additive |
| `skills/analytic-move-audit/SKILL.md` (**new**, SK-42) + `commands/analytic-move-audit.md` shim + `/plugin-commands` row + `SKILL_REGISTRY.md` entry | Standalone seven-move Abbott pass; P-stage-gated; M-4/M-5 carve-outs. | additive |
| `references/STYLE_COMMITMENTS.md` | C-8 row in §1 table; new §1.0d full text; summary-para, §3 interaction-table, §4 relaxation, §5 prohibition, §6 open-front updates. | additive |
| `agents/generator.md`, `evaluator.md`, `planner.md` | C-8 read-list + P-stage gate + carve-out + burden-of-proof wiring, mirroring the C-6/C-7 idiom. | additive |
| `references/MANIFEST.md` | Indexes the C-8 (and, retroactively, C-7) substrate. | additive |
| `CHANGELOG.md`, `.claude-plugin/plugin.json` | v0.20.0 entry + version bump. | housekeeping |

**Deferred, designed, recorded (the rest of the "set"):** `definition-derivation-check` (M-1) and `dissolution-move-check` (M-2) as single-purpose skills; a possible deterministic M-1 pre-filter (stipulation-cue scan) analogous to the D-STYLE surface validators; and the reflexive jurisdiction audit of §6.

**Open fronts (recorded, not resolved):** (a) M-6↔C-1 co-location — both govern the first-person "I" (register vs. epistemic grading); currently surfaced as independent findings. (b) Whether M-7 (passage reflexivity) should fold into `REFLEXIVITY_CHECK.md` (program reflexivity) or stay a distinct C-8 move; kept distinct for now. (c) Whether C-8's P-stage gate should read the P-stage from `classification.md` or re-derive it — currently reads, to avoid a second source of truth.

---

## 6. Reflexive contribution: the harness as a system of professions

This section is the "craft + reflexive architecture" half the author requested. It is a **diagnostic lens and one proposed audit, recorded not ratified** — Abbott's own M-7 warning applies to it, and it is offered as a way of *seeing* the architecture, not a mandate to rebuild it.

Abbott's substantive theory is that expert work is organized as a *system* of professions competing for **jurisdiction** — the link between a profession and its tasks — and that jurisdiction is claimed and defended in three arenas: the **legal** (formal rules), the **public** (professional rhetoric), and the **workplace** (what practitioners actually do). The harness is itself a division of expert labor: Planner, Evaluator, Generator, Reflector, and ~40 skills, each with a claimed competence over the manuscript. The mapping is exact enough to be useful:

- **Three arenas → three harness surfaces.** The **legal** claim is `AGENT_CONTRACTS.md` and the invariants; the **public** claim is `README.md` / `SKILL_REGISTRY.md` / the `/plugin-commands` catalog; the **workplace** is runtime dispatch. Abbott's central empirical finding is that *workplace jurisdiction routinely drifts from legal claims* — practitioners do, on the job, what their formal charter does not describe. Mapped onto the harness, this predicts a specific, diagnosable pathology: **an agent or skill whose runtime behavior has quietly drifted from its contract.** *Proposed audit (deferred):* a reflection-time check that samples recent agent outputs and flags where an agent exercised a competence its contract does not grant, or failed to exercise one it claims. This is the reflexive analogue of the grounding audit — grounding checks the manuscript against reality; this would check the agents against their charter.

- **Settlements beyond conquest.** Abbott catalogues the forms a jurisdictional settlement can take: full jurisdiction, subordination, an advisory relation, a division of labor, and division by client. The harness currently recognizes **only subordination** — inter-skill disputes resolve by fixed precedence (the ladder). Abbott's catalogue names the settlements the harness is *implicitly* using without vocabulary: the M-4 anaphora case is a **division of labor** (the anaphora's form is C-8's jurisdiction; its evidential adequacy is the Evaluator's), and a craft skill's relation to the Generator is **advisory** (it proposes, it does not bind). Naming these makes today's ad-hoc overlaps legible and reviewable. The C-8 patch already encodes one such settlement explicitly: the M-4/M-5 carve-out is a jurisdictional ruling that C-8 outranks `sentence-level-pass` on argumentative features, recorded in the §3 interaction table's new Reflector row.

- **Vacancies pull in claimants.** Abbott: a jurisdiction opens when a task is left unclaimed, and adjacent professions move in — often imperfectly. C-8 exists because exactly this happened: the analytic-move task sat vacant between C-2 and C-4, and the nearest claimant (mechanical Bacon craft) moved in and mis-handled it. The reflexive lesson is general: **the harness should expect its own coverage vacancies to be annexed by the nearest adjacent check, usually to the detriment of the vacated task.** *Standing reflection task (recorded):* periodically scan for layers that are asserted in the commitments but owned by no skill, on the theory that they are already being mis-served by a neighbor.

The lens is deliberately bounded. It licenses a vocabulary (arenas, settlements, vacancies), one diagnostic (contract↔runtime drift), and one already-shipped settlement (the C-8 carve-out). It does not rearchitect the agent loop, and it keeps its own modeling choice visible per M-7 — "jurisdiction" is a productive metaphor for the harness's division of labor, not a claim that agents are professions.

---

## 7. Grounding manifest

All Abbott 1988 quotations in this memo and in `analytic_construction_guidelines.md` were verified character-for-character against the uploaded full-text extract on 2026-07-01. Chapter-level locators are used in place of print pages because the source is a re-flowed digital edition without stable pagination. No claim rests on a quotation absent from the verified extract. The reflexive §6 mapping is grounded in Abbott's three-arena / settlement / vacancy apparatus as presented across chs. 1–3 and the concluding chapter; it is offered as an interpretive lens and is labeled throughout as recorded-not-ratified.

*Prepared as the analysis half of the C-8 work. The patch half lands the changes in §5 against package v0.19.0 → v0.20.0.*
