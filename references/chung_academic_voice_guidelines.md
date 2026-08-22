# Chung academic voice — registered authorial profile

**Status.** Overlay. Invoke through `/chung-academic-voice-pass`, an explicit request to audit or draft in this register, or the Evaluator evaluate fire table. This file is not a `STYLE_COMMITMENTS.md` C-n.

**Source of the profile.** The author supplied the profile after reviewing the co-authored technical paper `knowledge/LLM wiki/raw/corpus/chung-2026-identity-req.pdf` and the solo field essay `knowledge/LLM wiki/raw/corpus/chung-2026-inf3001-field-essay.pdf`. The profile describes writing; it does not independently validate those papers’ scholarly claims or citations.

**Complement.** C-7 (`voice_preservation_guidelines.md`) protects idiolect from being stripped. This file names a target register the author may request. Venue, advisor, and project directives still outrank it. Grounding Protocol still outranks it.

**Primary guide.** The solo field essay is the stronger guide to the individual voice. The co-authored paper is the secondary guide for technical precision, venue compression, and conventional research-paper structure.

---

## Core voice

The voice is formal, analytical, interdisciplinary, and ethically attentive. Its distinguishing move is to connect a technical representation—requirements, interfaces, models, dependencies, classifications—to its institutional consequences for authority, identity, competence, and accountability.

The writing rarely presents technology as an isolated artifact. It asks what a technical arrangement makes visible, leaves out, redistributes, or reconstitutes.

| Dimension | Voice characteristics |
|---|---|
| Tone | Serious, diagnostic, measured, and constructively critical. Ethically concerned without becoming polemical. |
| Formality | High academic formality. The solo essay permits occasional direct address, first-person positioning, and rhetorical questions; the conference paper is more compressed and impersonal. |
| Authorial stance | Assertive about the central argument, careful about evidentiary scope. Distinguishes demonstration from validation and conceptual parallels from empirical findings. |
| Intended audience | Interdisciplinary academic readers spanning Information, IS, requirements engineering, HCI, CSCW, and STS. Assumes intellectual sophistication but explains concepts when crossing disciplinary boundaries. |
| Argument structure | Thesis early; definitions and distinctions next; concrete case or model; theoretical interpretation; disciplinary or practical implications; explicit limits. |
| Paragraph movement | Claim → distinction or contrast → evidence/example → interpretation → consequence for the larger argument. |
| Sentence style | Layered sentences using colons, semicolons, and carefully controlled subordinate clauses. The solo essay averages roughly 25 words per sentence; the conference paper roughly 33. |
| Conceptual style | Definition-driven and relational. Concepts are explained by showing how they differ and how they interact within a configuration. |
| Evidence style | Citations are woven into argumentative sentences. Sources perform identifiable jobs rather than appearing as undifferentiated citation clusters. |
| Ethical register | Questions of authority, contestability, discretion, visibility, and accountability are treated as analytical properties of system design—not appended as generic “ethical considerations.” |

## Most characteristic rhetorical habits

The strongest and most reusable habits are:

- Beginning with a disciplinary or conceptual problem rather than a broad claim about AI’s importance.
- Moving from a concrete professional situation to a theoretical distinction, then returning to the situation with greater analytical precision.
- Using contrast to sharpen the claim: “not merely X but Y,” “rather than,” “what this framing does not accommodate,” and “the question is not X; it is Y.”
- Framing key transitions as questions: “What is at stake…?” “The question becomes…?” and “Who has authority to revise the model?”
- Using verbs such as *encodes*, *reconstitutes*, *surfaces*, *makes visible*, *formalizes*, *redistributes*, and *presupposes*.
- Treating categories and models as provisional rather than naturally given.
- Naming limits directly and specifically instead of ending with generic calls for “more research.”

## Drafting specification for AI agents

Write in a formal interdisciplinary academic register. State the central claim early and make each section advance it. Define important terms operationally, especially when moving across disciplinary boundaries. Connect technical design choices to institutional consequences for professional identity, authority, discretion, contestability, or accountability. Use a concrete organizational case to anchor theoretical claims, then return to that case after introducing the theory. Prefer analytical contrasts and precise distinctions over broad declarations. Integrate citations into the reasoning and identify what each source contributes. Use first person sparingly for argument ownership or methodological positioning. End major analyses by naming implications, validation scope, and specific limitations.

Favor sentences of approximately 20–30 words, with occasional longer sentences when several relationships must be held together. Use colons and semicolons purposefully. Preserve conceptual continuity across the introduction, headings, body, and conclusion.

Do not use conversational filler, promotional language, technological inevitability, generic “AI is transforming everything” openings, or unsupported claims that prior literature has ignored a topic entirely. Do not intensify the ethical register into moral grandstanding. Avoid excessive abstraction: after introducing two or three conceptual terms, return to a person, interface, decision, dependency, or institutional rule.

Useful transition patterns include:

- “What this framing does not accommodate is…”
- “The distinction matters because…”
- “The mapping makes this pressure visible as…”
- “Taken together, these moves change…”
- “What is in question is not X, but Y.”
- “The scope is illustrative, not comparative.”
- “The practical effect is similar, but the mechanism differs.”

These should remain occasional moves, not become templates repeated in every paragraph.

## Prose-requirement overlay

The following checks ride with this pass on evaluate fire-table runs. They do not become C-n commitments. Venue and advisor still outrank them.

- Use varied sentence rhythm and state purpose in ordinary language.
- Clarify abstract concepts with a concrete example and a stated nuance.
- Differentiate conceptual terms with operational definitions.
- Embed theory only where it changes the discussion.
- Open subsections with plain headings.
- Explain analysis steps in a named sequence.
- Specify modeling cuts so pre-modeling assumptions stay visible.
- Connect literature to the present case without restating the source’s language.
- Contextualize each academic reference for relevance.
- Summarize main contributions in a plain enumeration.
- Explain literature distinctions without jargon overload.
- Restate open issues in accessible phrasing.
- Restate analytical boundaries and limitations concisely.
- Use prior work critically to explain the paper’s assumptions.

## Representative examples

The excerpts were supplied with the profile and are lightly dehyphenated to remove PDF line-break artifacts. Each exceeds 200 words. They are calibration material for register, not independent citation verification.

### Example 1: Concrete case joined to institutional analysis

*Solo field essay, pp. 2–3; approximately 265 words.*

> To ground the argument, I draw on an illustrative, constructed scenario. Consider a mid-career loan officer at a bank that introduces an AI credit-scoring system. When the dashboard flags a long-standing client as high-risk, she already knows the context: a temporary cash-flow gap after a family emergency, not a change in creditworthiness. The interface provides no field for that judgment. She can override the flag, yet every override is logged as an exception, and exceptions accumulate against her quarterly review. The system has reorganized the meaning of her competence: the situated knowledge that once defined her value now registers as institutional deviance. Empirical studies of algorithmic management in platform work (Seeber et al., 2020), clinical decision support (Herrmann & Pfeiffer, 2023), and predictive policing (Eubanks, 2018) confirm this pattern: system design encodes assumptions about workers’ competence and discretion that strip away both the judgment workers depend on and the responsibility they hold for outcomes.
>
> To name what the dashboard strips away, I draw on Haslam et al. (2013), who distinguish human uniqueness (civility, refinement, cognitive capacity: what differentiates humans from other animals) from human nature (warmth, emotionality, vitality, flexibility: what differentiates humans from machines). The distinction extends from interpersonal perception to classification: when a system assigns a person to a category, it operationalizes some traits as legible and leaves others outside the model, stripping them the same way a perceiver does when denying humanness. The credit-scoring dashboard omits the loan officer’s discretionary reasoning (human uniqueness) and contextual responsiveness (human nature), reshaping how her competence is institutionally valued.

Characteristic sequence: human situation → interface constraint → institutional consequence → theoretical vocabulary → reinterpretation of the case.

### Example 2: Technical-theoretical synthesis

*Co-authored conference paper, p. 6; approximately 245 words.*

> Carter and Grover’s [6] construct of IT Identity establishes that the relationship between people and technology is not merely instrumental but constitutive of identity. When AI is viewed as having agency within the organization, this dynamic intensifies: the technology itself assumes professional tasks and organizational responsibilities, shifting the identity question from “how does this tool relate to who I am?” to “who am I when this agent can do what I do?”
>
> Identity theory explains what professional identities are and how they respond to change, but identities do not form in a vacuum. They are constructed within organizational structures that shape whether identity responses lead to growth or to threat. Dynamic capabilities theory has been used to provide this organizational-level explanation.
>
> Teece [15] characterizes organizational adaptation through sensing opportunities, seizing them via resource mobilization, and transforming through asset reconfiguration. Salvato and Vassolo [16] locate the source of this dynamism at the meso level—the intermediate level of teams, routines, and cross-role interactions that connects individual (micro-level) actions to organization-wide (macro-level) patterns. Simón et al. [8] showed that this mechanism operated in a bank’s AI implementation: sensing-seizing-reconfiguration cycles enabled the hiring team to move from resistance to role expansion. Herrmann and Pfeiffer [5] argue that AI adoption requires understanding the distribution of agency between human and machine at this organizational level, underscoring the need to analyze identity dynamics within structures, not merely at the individual level.

Compressed version of the same voice: a memorable identity question, a conceptual distinction, a theoretical bridge, and an organizational-level implication.
