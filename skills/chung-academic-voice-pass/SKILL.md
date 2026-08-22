---
name: chung-academic-voice-pass
description: 'Run the registered Chung academic-voice pass: join technical representations to institutional consequences for identity, authority, competence, and accountability. Use when: "chung voice", "my voice pass", "authorial voice pass", "institutional identity voice", or an explicit request to audit or draft in this register.'
trigger: when the user asks for the Chung academic voice pass, "my voice", an authorial-register audit, or to write or review in the identity-accountability register
created_by: Reflector
created_from: Author-supplied voice profile, 2026-08-21 — sampled from chung-2026-identity-req and chung-2026-inf3001-field-essay
pattern_source: references/chung_academic_voice_guidelines.md
version: 1.0
---
# Chung Academic Voice Pass

You are running an optional authorial-register pass. Read `chung_academic_voice_guidelines.md` in the package before acting. Do not rely on memory.

This pass is additive. It does not replace C-5, C-7, Bacon, Sexton, Baird, Abbott, or venue rules. It is not a STYLE_COMMITMENTS C-n. Evaluator evaluate fire tables now fire it on certified staging bytes; a user may still invoke it on demand.

## File resolution

Read style and orchestration files from the package `references/` tree.

## Activation

Run when the user invoked this skill, explicitly asked for this register, or the Evaluator fire table named this pass. Apply it to the manuscript, section, or pasted prose they named.

If no target text is available, stop and ask for a path or paste. Do not invent a manuscript. Do not require milestone, assignment, or phase state.

Default mode is **audit**. Switch to **draft** only when the user asks to write or revise in this voice. In draft mode, propose or apply edits as the user asked; do not silently rewrite unread sections.

If a venue template or advisor instruction conflicts with this register, name the conflict and follow the higher-precedence source.

## What to check

1. **Technical–institutional join**
   - Does a load-bearing technical object (requirement, interface, model, dependency, classification) connect to consequences for authority, identity, competence, discretion, contestability, or accountability?
   - Flag technology presented as an isolated artifact when the passage is making a design or organizational claim.

2. **Problem-first opening**
   - Does the opening start from a disciplinary or conceptual problem?
   - Flag generic “AI is transforming…”, promotional, or inevitability openings.

3. **Case → distinction → return**
   - Is a concrete situation, interface, decision, or rule used to earn the theory?
   - After two or three conceptual terms, does the prose return to a person, interface, decision, dependency, or institutional rule?

4. **Definition and contrast**
   - Are important terms defined operationally, especially at disciplinary crossings?
   - Are contrasts used to sharpen a claim (“not merely X but Y”, “the question is not X; it is Y”) without becoming a per-paragraph template?

5. **Citation jobs**
   - Does each cited source perform an identifiable job in the sentence?
   - Flag undifferentiated citation clusters. Do not invent missing sources. Do not treat this pass as citation verification.

6. **Ethical register**
   - Are authority, visibility, discretion, and accountability treated as properties of the design or arrangement?
   - Flag generic appended “ethical considerations” and moral grandstanding.

7. **Stance and limits**
   - Does the prose distinguish demonstration from validation, and conceptual parallel from empirical finding?
   - Do major analyses name specific implications, validation scope, and limits rather than “more research is needed”?

8. **Sentence habit (advisory)**
   - Target average roughly 20–30 words, with occasional longer layered sentences.
   - Use this as a signature check, not a per-sentence ceiling. C-7 still protects baseline idiolect.

9. **Prose-requirement overlay** (evaluate fire-table)
   - Varied sentence rhythm; purpose stated in ordinary language.
   - Abstract concepts followed by a concrete example or nuance.
   - Conceptual terms differentiated with operational definitions.
   - Theory embedded only where it changes the discussion.
   - Subsections opened with plain headings.
   - Analysis steps in a named logical sequence.
   - Modeling cuts stated so pre-modeling assumptions stay visible.
   - Literature connected to the present case without restating source language.
   - References contextualized for relevance, not stacked.
   - Main contributions summarized in plain enumerations.
   - Literature distinctions explained without jargon overload.
   - Open issues restated in accessible phrasing.
   - Analytical boundaries and limits restated concisely.
   - Prior work used critically to explain the paper’s assumptions.

## Severity

- **[MAJOR]** load-bearing design/organization claim with no institutional join; generic AI-importance opening; ethical grandstanding that replaces mechanism; unsupported “the literature has ignored X entirely.”
- **[MINOR]** theory introduced without returning to a concrete site; citation cluster with no job; missing operational definition at a disciplinary crossing; generic limits; a prose-requirement overlay item missing from a load-bearing section.
- **[INFO]** sentence-length or first-person pattern differs from the profile but matches the manuscript’s own baseline, or is required by venue compression.

Do not use **[BLOCKER]** for register mismatch. Grounding Protocol violations remain grounding findings, not voice findings.

## Output format

```markdown
## Chung Academic Voice Pass Results

**File:** <path or "pasted excerpt">
**Scope:** <full file | sections | pasted>
**Mode:** audit | draft
**Guide:** solo-essay primary / conference-paper secondary

### Applicability
- Invoked: yes
- Venue/advisor conflict: <none | named conflict and who wins>

### Findings
| # | Location | Check | Finding | Severity | Proposed fix |
|---|---|---|---|---|---|
| 1 | ... | technical–institutional join | ... | [MAJOR] | ... |

### Strengths
- <join, contrast, case-return, or limit-naming that already matches the register>

### Summary
- MAJORs: <n>
- MINORs: <n>
- INFOs: <n>
- Recommendation: <keep overlay / enough for this section / defer to venue>
```

In draft mode, add a short rewrite block only for the requested span. Preserve `\label`, `\ref`, `\cite`, math, and bibliography commands.

## Guardrails

- Do not validate the scholarly truth of the calibration papers or of the target manuscript’s citations.
- Do not mint scholarly CLEAN, C6, F9, or terminal language.
- Do not force first person into a venue that requires impersonal compression.
- Do not repeat the listed transition stems in every paragraph.
- Do not convert measured ethical analysis into advocacy.
- Do not treat C-7 idiolect as a defect. Report it as [INFO] unless an independent C-5 or grounding defect is also present.
- Sentence craft remains `/sentence-level-pass`. Analytic-move construction remains `/analytic-move-audit`. Public-interest mechanism tracing remains `/public-interest-accountability-pass`.
