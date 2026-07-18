# The Smell of the Writer: A Craft Analysis of Seven Manuals and the Case for a Voice-Fingerprint Commitment (C-7)

**Author-facing analysis + patch rationale**
**Date:** 2026-06-30
**Scope:** Deep read of four voice/craft books (Moran, Zinsser, Strunk, Abbott ×2), light pass on two reference manuals (Turabian, Penguin), audited against `references/STYLE_COMMITMENTS.md` (C-1…C-6), `references/SAFEGUARD_LAYER.md` Check 6, the D-STYLE profile check, and the prose-craft skills. Target package version at time of writing: 0.18.0.

> **Grounding note.** Every quotation below was verified character-for-character against the uploaded extracts, not reconstructed from memory. One correction is load-bearing: the uploaded *Elements of Style* is **Strunk's original (1918/1921), not Strunk & White**. White's "Approach to Style" essay — the source of the famous "Style is the writer… no two writers alike" and "Place yourself in the background" — **is not in the attached file** and is not attributed to it here.

---

## 1. Problem statement

The harness is, by design, a prescriptive instrument. Four of its six declared style commitments — C-1 (Suchman first-person register), C-2 (Bacon sentence craft), C-3 (Sexton narrative arc), C-4 (Baird IS-theory shape) — push a manuscript toward a *named, borrowed* register. C-5 (reader-accessibility) and C-6 (scoped metaphor) constrain the prose surface further. The architecture is internally honest about this: `STYLE_COMMITMENTS.md` already concedes the commitments are "methodological commitments, not universal hygiene… defensible, but not neutral."

The problem the author names — *every piece should follow the distinction (the smell of) the writer without interrupting the real context of what the writer writes about* — is the gap those six commitments do not close. They specify what good prose **should converge toward**; none of them specifies what the prose **must not lose**. A commitment that says "write in the Suchman register" can be fully satisfied by prose that is also voiceless, because "Suchman register" is a target fingerprint, not *this author's* fingerprint. The harness can therefore drive a manuscript to full C-1…C-6 compliance while sanding off the writer's idiolect — the very failure mode `SUCCESS_METRICS` and `REFLEXIVITY_CHECK` would call incoherent for a research program that studies how delegated agency reshapes professional identity.

The seven manuals were chosen, whether deliberately or not, to supply the missing half. Four of them are sustained arguments *against* exactly the homogenization the harness risks. This document extracts that argument, shows where it lands in the architecture, and specifies a seventh commitment — **C-7, authorial voice-fingerprint preservation** — that closes the gap without weakening the existing six.

---

## 2. Theoretical framework: what the four craft books actually argue

The deep read converges on a single distinction that the whole patch turns on. Call it the **mechanics/identity split**: there is a layer of prose where rules legitimately operate (clutter, error, vagueness, broken parallelism, dead metaphor — content-neutral correctness), and a layer where rules destroy what they touch (cadence, sentence-length signature, repetition tolerance, point of view, humor, evaluative stance — idiolect). All four authors endorse discipline on the first layer and resist it on the second. They differ only in emphasis.

### 2.1 Zinsser — the craft/attitude split, stated outright

Zinsser supplies the cleanest formulation of the split and the most usable list of voice markers. He divides writing into "two issues… One is craft, the other is attitude. The first is a question of mastering a precise skill. The second is a question of how you use that skill to express your personality" (*On Writing Well*, ch. 5). Craft is teachable and rule-governed; attitude is the self, and it cannot be added: "Trying to add style is like adding a toupee" (ch. 4). The writer is the product — "My commodity as a writer, whatever I'm writing about, is me. And your commodity is you. **Don't alter your voice to fit your subject**" (ch. 20).

Three of his claims bear directly on the harness:

- **Against per-subject re-registering.** "Don't alter your voice to fit your subject… Develop one voice that readers will recognize." This is a direct objection to a pipeline that selects a *different* borrowed register (Suchman vs. Bacon vs. Vidal) per piece and treats register-switching as neutral.
- **Against the impersonal academic default.** "If you aren't allowed to use 'I,' at least think 'I' while you write" (ch. 20). He names "one" and the impersonal "it is" as humanity-killers.
- **The first-paragraph test.** Editors should "start with the paragraph where the writer begins to sound like himself or herself" — voice is something a draft *arrives at*, and an over-eager early edit can amputate it before it appears.

Crucially, Zinsser is *not* anti-rule. He is fierce about pruning, simplicity, and clean syntax — he simply insists those are mechanical acts that **uncover** voice rather than impose register. This is the model the harness should adopt: mechanics serve identity; they do not overwrite it.

### 2.2 Moran — the anti-uniform-register argument, and the demolition of "readability"

Moran is the sharpest weapon against the harness's most dangerous reflex: optimizing prose toward a transparency/readability target. His central polemic ("Nothing Like a Windowpane") dismantles the Orwell doctrine that good prose is an invisible pane of glass: "Orwell, it turns out, is an outlier… To write in the plain style, you must learn its tricks. **The plain style is just that — a style.**" Plainness is not neutrality; it is one aesthetic among many, and mandating it conceals an argument.

He attacks automated readability scoring by name — the word processor that "scored your writing for 'readability' and told you, with blithe, uninformed confidence, that you are done." His empirical correction is precise and directly usable as a rule boundary: "there is nothing wrong with long sentences per se. **Average sentence length, not some arbitrary maximum, is what counts.** Long sentences and long words are fine so long as they bump up against short ones." And the positive claim that names the prize: "When you vary the length of your sentences… your writing will, as if by magic, fill with life and voice."

Moran also identifies a fingerprint feature the harness currently has no concept of: **repetition tolerance.** "How much a writer tolerates repetition comprises a key part of his voice." A skill that mechanically flags repeated words as monotony will flatten a writer (his example is David Peace) for whom repetition *is* the signature.

### 2.3 Strunk — the rulebook that grounds its rules in protecting individual thought

Strunk is the productive paradox. The uploaded original is a pure rulebook — Rule 13, "Omit needless words… make every word tell" — yet it frames the enemy not as the writer but as the *formula*: write to "express accurately **your own individual thought**, and… refuse to be satisfied with a **ready-made formula** that saves you the trouble of doing so" (ch. 5 head). Even the arch-prescriptivist positions his rules as defending idiolect against canned phrasing. The harness can cite Strunk *for* economy while honoring that Strunk's own target is the cliché and the cluttered clause — never the writer's stance, rhythm, or point of view. (The stronger "style transcends rules" payoff belongs to White's 1959 essay, which is *not* in the attached file and is therefore not relied on here.)

### 2.4 Abbott — heuristics over algorithms; intellectual personality as the instrument

Abbott supplies the epistemological backbone. *Methods of Discovery* opens "Science is a conversation between rigor and imagination" and insists the book is "not really about methods" but about heuristics — "gambits of imagination, mental moves" that no mechanical procedure can supply. His key construct for C-7 is **intellectual personality**: "getting a sense of your own strengths and weaknesses as a thinker… your intellectual personality… decisively influence[s]… everything about the way you think." Voice, for Abbott, is not ornament on top of thought; it *is* the shape of the thinking, and "**every aspect of your intellectual character… is both a strength and a weakness**" — so it cannot be normalized away without damaging the judgment it carries.

*Digital Paper* adds the decisive claim about wording itself: linearizing a nonlinear research process into prose "is an **arbitrary — even an aesthetic — decision.**" The final wording is a taste act, not a derivation — which means a rewrite pass that optimizes wording to a target register is overriding the analysis, not polishing it. Abbott embodies what he licenses: he calls himself "your cranky guide," admits he waxes "romantic about libraries," and notes his "unusual combination of expertises has inevitably produced a distinctive kind of book." The manual performs the idiolect it defends.

### 2.5 The two reference manuals (light pass)

Turabian and Penguin are mostly mechanics already covered by `citation-format-pass` and `grammar-mechanics-pass` — but each carries a thin, corroborating voice seam. Turabian ch. 11 (a port of Williams' *Style*) **explicitly rejects** the blanket bans the harness's borrowed registers can imply: choose active/passive "by considering which gives you the right kind of subject," and on first person, "opinions differ… others encourage using *I* as a way to make writing more lively and personal." Penguin's "Good style" chapter states the thesis the patch encodes: "**The rules of style are not intended as a means of stifling self-expression, but as a means of enhancing it… Style should not be separable from the individual's way of putting the message across.**" Neither introduces capability the four craft books don't already supply; both are useful as secondary authority inside the C-7 reference.

---

## 3. Methodology: how the architecture currently handles voice — and where it leaks

The audit traced voice handling through `STYLE_COMMITMENTS.md`, `SAFEGUARD_LAYER.md` Check 6, the D-STYLE profile check, and the two prose skills. Three structural leaks emerged.

**Leak 1 — Voice is measured against borrowed registers, not the author's baseline.** `SAFEGUARD_LAYER.md` Check 6 ("Humanness Voice Audit") is the only place the pipeline scores voice. But every positive marker it counts is register-specific: "first-person at hinges (Suchman)," "paired constructions with plain verdicts (Vidal)," "interlocutory opening (Suchman)." The audit therefore answers *"does this prose sound like the Suchman/Vidal exemplar?"* — not *"does this prose sound like its author?"* A manuscript can fail Check 6 for being insufficiently Suchman-like while being perfectly, recognizably its author. This is the precise mechanism by which the harness can flatten idiolect *in the name of* protecting voice. (Moran's diagnosis: measuring "the sameness of surface features… minds more about meticulousness than music.")

**Leak 2 — No commitment names idiolect as a non-target.** C-1…C-6 are all *convergent* — they say what to move toward. None is *protective* — none names a feature the pipeline must not strip absent a content defect. So sentence-length signature, repetition tolerance, point-of-view, humor, and evaluative stance have no defender in the commitment ladder. They are unowned, and unowned features get optimized away.

**Leak 3 — The craft skills can misread idiolect as defect.** `sentence-level-pass` flags "consecutive sentences of similar length" as monotony and "passive clusters" mechanically; `narrative-structure-pass` Check 7 ("Consistent voice") flags "melodrama" and sentence-length. Each is reasonable as written, but each can fire on a legitimate fingerprint (Moran's repetition-tolerant writer; an author whose deliberate flat affect reads as "melodrama"-adjacent under a coarse check). The skills disclaim genre-mechanical overreach but have **no idiolect carve-out**.

The D-STYLE profile check itself is *not* a leak — it is a routing/surface validator (argument, visual-evidence, assistance surfaces) and never judges register. C-7 should sit alongside it, not inside it.

---

## 4. Synthesis: the contribution — C-7, authorial voice-fingerprint preservation

The four craft books license a commitment with a shape none of C-1…C-6 has: **a protective, not convergent, rule.** C-7 does not tell the Generator what register to write in. It tells the whole pipeline which features are the author's signature and therefore off-limits to "improvement" unless a content or correctness defect independently justifies the change.

**C-7 in one line:** *Mechanical and grounding rules may touch correctness, clutter, and vagueness; no rule may flatten an idiolect-bearing feature — sentence-length signature, repetition tolerance, point of view, cadence, humor, evaluative stance — absent an independently established content or accessibility defect.*

Four design decisions follow from the books:

1. **C-7 is suspendable (like C-1…C-4), not absolute (unlike C-5).** It is a position, not a law — a venue may legitimately demand a house voice. It is recorded by the Planner at classification and relaxable via `directives.md`. (Zinsser's imitation-as-scaffolding point: borrowed registers are "skins" to be shed, so the commitment that protects the author's skin must yield when the author chooses a borrowed one.)
2. **C-7 reorients Check 6 rather than replacing it.** Check 6's machinery is sound; its *reference class* is wrong. The patch adds an **idiolect baseline** step: before counting register markers, sample the author's own prior accepted prose (or the least-revised passages of the current draft) to establish the writer's signature, and score drift **against that baseline**, only then against the declared register. A degradation finding must distinguish "drifted away from the Suchman exemplar" (often fine) from "drifted away from *this author*" (the real defect).
3. **C-7 gives the craft skills an idiolect carve-out.** `sentence-level-pass` monotony/passive flags and `narrative-structure-pass` Check 7 gain a one-line exception: a pattern that recurs in the author's baseline and is not a comprehension defect is idiolect, reported as **strength or [INFO]**, not [MINOR]. Moran's "average length, not maximum" rule replaces any implicit per-sentence ceiling.
4. **C-7 inverts the burden of proof on rewrites.** Under the Grounding Protocol the Generator already may not invent content. C-7 adds the parallel rule for *style*: the Generator may not strip a voice feature on taste alone — the edit must cite a correctness, clutter, or accessibility (C-5) warrant. Abbott's "arbitrary — even aesthetic" point becomes operational: wording is the author's decision, and the burden is on the rule to justify overriding it.

The result is reflexively coherent in the sense `STYLE_COMMITMENTS.md §2.3` demands: a harness that studies how delegated agency reshapes professional identity now has an explicit guard against erasing the author's identity in the prose it helps produce.

---

## 5. The patch set (companion to this analysis)

The accompanying changes implement C-7 with no breaking changes to C-1…C-6 or the agent contracts:

| Artefact | Change | Type |
|---|---|---|
| `references/voice_preservation_guidelines.md` | **New** reference grounding C-7 in Moran, Zinsser, Strunk, Abbott (×2), with the Turabian ch. 11 / Penguin corroboration. Follows the v0.17.0 source-absorption pattern. | additive |
| `references/STYLE_COMMITMENTS.md` | C-7 row in the §1 table; new §1.0c full text; interaction-table, relaxation, and prohibition updates. | additive |
| `references/SAFEGUARD_LAYER.md` Check 6 | Idiolect-baseline step + baseline-vs-register drift distinction. | refinement |
| `skills/sentence-level-pass/SKILL.md` | Idiolect carve-out on monotony/passive flags; Moran "average not maximum" note. | refinement |
| `skills/narrative-structure-pass/SKILL.md` | Check 7 "Consistent voice" carve-out for baseline idiolect. | refinement |
| `agents/generator.md`, `evaluator.md`, `planner.md` | C-7 read-list + burden-of-proof-on-rewrite wiring, mirroring the C-6 idiom. | additive |
| `CHANGELOG.md`, `.claude-plugin/plugin.json` | v0.19.0 entry + version bump. | housekeeping |

**Open fronts (recorded, not resolved):** (a) where to source the author's idiolect baseline when no prior accepted prose exists; (b) C-7 vs. C-1 conflict resolution when the author's natural voice is *not* first-person and the venue is Suchman-friendly — currently surfaced to the user, as §6 of `STYLE_COMMITMENTS.md` does for the C-2/C-3 tension; (c) whether C-7 eventually warrants its own deterministic baseline-extraction script (declined here per the "commitment + skill-tuning" scope).

---

*Prepared as the analysis half of the C-7 work. The patch half lands the changes above against package v0.18.0 → v0.19.0.*
