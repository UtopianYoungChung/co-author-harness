---
name: public-interest-accountability-pass
description: 'Run an optional Eubanks-style pass for policy-critical writing: human-impact anchoring, mechanism traceability, and evidence-disciplined normative framing — for inequality, public-service, or accountability manuscripts. Use when: "policy-critical framing", "Eubanks pass", automated-decision critique.'
trigger: when the user asks for policy-critical framing, inequality/public-service accountability writing, or human-impact plus mechanism-driven critique
version: 1.0
---

# Public-Interest Accountability Pass (Eubanks-style overlay)

You are running an optional policy-critical style pass based on `eubanks_2018_automating_inequality_style_guidelines.md`.

This pass is additive. It does not replace Baird, Sexton, Bacon, or P-stage gating.

## File resolution

Read style and orchestration files from the package `references/` directory (`${CLAUDE_PLUGIN_ROOT}` on Claude hosts; otherwise the installed package root containing `version.json`).

## Activation gate

Run this pass only if at least one is true:

- The manuscript is policy-critical, inequality-focused, or public-service accountability focused.
- The user explicitly requests human-impact framing plus system-level mechanism analysis.
- The section under review is implications/discussion where institutional harms/rights effects are central.

If not applicable, return:

`Public-interest accountability pass: not applicable for this manuscript scope.`

## What to check

1. **Human anchor + analytic bridge**
   - Does each major section include a concrete human-impact anchor or near-anchor?
   - Is there an explicit bridge from scene/case to systemic mechanism?

2. **Mechanism traceability**
   - For each major critique, can you point to a concrete mechanism (rule, workflow, metric, contract term, process design, legal/procedural rule)?
   - Flag critiques that are purely rhetorical without mechanism evidence.

3. **Normative clarity**
   - If value terms are used (for example liberty, equity, inclusion, fairness, dignity), are they defined in-context?
   - Are claims about those values tied to observable effects?

4. **Evidence pairing**
   - Are narrative claims paired with documentary/process/quantitative support where available?
   - Are inferences clearly separated from directly observed facts?

5. **Methods transparency in argument**
   - Is evidence provenance clear (interview, document, record, model output, policy text)?
   - Are uncertainty and limits disclosed where needed?

## Severity guidance

- **[MAJOR]** missing mechanism for a major normative claim.
- **[MAJOR]** narrative claim driving conclusions without any supporting evidence path.
- **[MINOR]** weak analytic bridge after a human-impact anchor.
- **[MINOR]** undefined value term where meaning is recoverable from context.

Use **[BLOCKER]** only when a high-stakes normative claim is materially unsupported and likely to mislead readers.

## Output format

```markdown
## Public-Interest Accountability Pass Results

**File:** <path>
**Scope:** <full file | sections>
**Mode:** Eubanks-style optional overlay

### Applicability
- Applicable: <yes/no>
- Reason: <why>

### Findings
| # | Location | Finding | Severity | Proposed fix |
|---|---|---|---|---|
| 1 | ... | ... | [MAJOR/MINOR/BLOCKER] | ... |

### Summary
- Strengths: <narrative-mechanism pair quality, evidence clarity, normative precision>
- Risks: <top 1-3 issues>
- Recommendation: <keep overlay / not needed>
```

## Guardrails

- Do not force this style into sections where venue norms require impersonal, technical exposition.
- Do not convert analytic text into advocacy rhetoric.
- Do not invent harms, mechanisms, or value conflicts not present in the manuscript.
- Keep this pass complementary to `narrative-structure-pass` and `sentence-level-pass`.
